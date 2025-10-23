#!/usr/bin/env bash
set -euo pipefail

# ==============================
# NeoLight Phase 10300–11000
# Monitoring + AI Self-Healing
# - Installs Helm if needed
# - Deploys kube-prometheus-stack (Prometheus+Grafana+Alertmanager)
# - Deploys Loki + Promtail for logs
# - Adds a simple Anomaly Detector
# - Adds an AI Daily Log Summarizer (optional OpenAI &/or Pushover)
# ==============================

# ---------- helpers ----------
banner(){ printf "\n\033[1;96m%s\033[0m\n" "$1"; }
need_cmd(){ command -v "$1" >/dev/null 2>&1 || return 1; }
ns=neolight-observability

# ---------- secrets sanity ----------
banner "🔐 Checking environment/secrets"

# These are optional but recommended
: "${OPENAI_API_KEY:=}"            # optional: for AI daily summary
: "${PUSHOVER_TOKEN:=}"            # optional: Pushover notify
: "${PUSHOVER_USER:=}"             # optional: Pushover to user/device
: "${GRAFANA_ADMIN_PASSWORD:=admin123}"  # will be used if Grafana admin secret not present

# ---------- kubectl context ----------
banner "☸️  Verifying kubectl context"
need_cmd kubectl || { echo "kubectl not found. Install kubectl first."; exit 1; }
kubectl cluster-info >/dev/null

# ---------- Helm ----------
banner "🛠️ Ensuring Helm"
if ! need_cmd helm; then
  curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

# ---------- Namespaces ----------
banner "📦 Creating namespaces (idempotent)"
kubectl get ns "$ns" >/dev/null 2>&1 || kubectl create ns "$ns"

# ---------- Repos ----------
banner "📚 Adding Helm repos"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo add grafana https://grafana.github.io/helm-charts >/dev/null
helm repo update >/dev/null

# ---------- Grafana admin secret ----------
banner "🔑 Preparing Grafana admin secret"
if ! kubectl -n "$ns" get secret grafana-admin >/dev/null 2>&1; then
  kubectl -n "$ns" create secret generic grafana-admin \
    --from-literal=admin-user=admin \
    --from-literal=admin-password="$GRAFANA_ADMIN_PASSWORD" >/dev/null
fi

# ---------- Values files ----------
banner "📝 Writing values files"
mkdir -p k8s/monitoring

cat > k8s/monitoring/kube-prom-stack.values.yaml <<'YAML'
grafana:
  enabled: true
  admin:
    existingSecret: grafana-admin
    userKey: admin-user
    passwordKey: admin-password
  service:
    type: NodePort
    nodePort: 30000
  serviceMonitor:
    selfMonitor: true
prometheus:
  service:
    type: NodePort
    nodePort: 30090
  prometheusSpec:
    retention: 15d
alertmanager:
  enabled: true
  service:
    type: NodePort
    nodePort: 30093
YAML

cat > k8s/monitoring/loki.values.yaml <<'YAML'
loki:
  auth_enabled: false
  commonConfig:
    replication_factor: 1
singleBinary:
  replicas: 1
  persistence:
    enabled: true
    size: 5Gi
gateway:
  enabled: false
read:
  replicas: 0
write:
  replicas: 0
backend:
  replicas: 0
YAML

cat > k8s/monitoring/promtail.values.yaml <<'YAML'
config:
  clients:
    - url: http://loki:3100/loki/api/v1/push
  snippets:
    pipelineStages:
      - cri: {}
      - labels:
          app: "neolight"
      - match:
          selector: '{app="neolight"}'
          stages:
            - timestamp:
                source: time
                format: RFC3339
    extraScrapeConfigs: |
      - job_name: containers
        static_configs:
          - targets:
              - localhost
            labels:
              job: varlogs
              __path__: /var/log/*log
      - job_name: pods
        kubernetes_sd_configs:
          - role: pod
        pipeline_stages:
          - cri: {}
YAML

# ---------- Install/Upgrade charts ----------
banner "📈 Installing kube-prometheus-stack"
helm upgrade --install neolight-obsv \
  prometheus-community/kube-prometheus-stack \
  -n "$ns" -f k8s/monitoring/kube-prom-stack.values.yaml >/dev/null

banner "📜 Installing Loki"
helm upgrade --install loki grafana/loki \
  -n "$ns" -f k8s/monitoring/loki.values.yaml >/dev/null

banner "🪵 Installing Promtail"
helm upgrade --install promtail grafana/promtail \
  -n "$ns" -f k8s/monitoring/promtail.values.yaml >/dev/null

# ---------- Anomaly Detector (Deployment + Config) ----------
banner "🧠 Deploying Anomaly Detector"
mkdir -p monitoring
cat > monitoring/anomaly_detector.py <<'PY'
import os, time, requests, statistics, math, json
PROM = os.environ.get("PROM_URL", "http://neolight-obsv-kube-prometheus-sta-prometheus:9090")
INTERVAL = int(os.environ.get("INTERVAL_SEC", "60"))
PUSHOVER_TOKEN = os.environ.get("PUSHOVER_TOKEN")
PUSHOVER_USER = os.environ.get("PUSHOVER_USER")

def q(query):
    r = requests.get(f"{PROM}/api/v1/query", params={"query": query}, timeout=15)
    r.raise_for_status()
    data = r.json().get("data", {}).get("result", [])
    return data

def notify(msg):
    print(f"[ANOMALY] {msg}")
    if PUSHOVER_TOKEN and PUSHOVER_USER:
        try:
            requests.post("https://api.pushover.net/1/messages.json", data={
                "token": PUSHOVER_TOKEN,
                "user": PUSHOVER_USER,
                "message": msg[:1024],
                "title": "NeoLight Anomaly"
            }, timeout=10)
        except Exception as e:
            print("pushover error:", e)

def zscore(values):
    if len(values) < 4: return 0
    mu = statistics.mean(values)
    sd = statistics.pstdev(values) or 1.0
    return abs((values[-1]-mu)/sd)

def sample_timeseries(expr, lookback="5m"):
    # instant vector hacking: take rate over last 5m then split values from matrix range
    r = requests.get(f"{PROM}/api/v1/query", params={"query": f"{expr}"}, timeout=15)
    r.raise_for_status()
    res = r.json().get("data", {}).get("result", [])
    vals=[]
    for s in res:
        try:
            vals.append(float(s["value"][1]))
        except:
            pass
    return vals

def loop():
    while True:
        try:
            # Pod restarts (any > 0 in last 10m)
            restarts = q('increase(kube_pod_container_status_restarts_total[10m])')
            bad = [m for m in restarts if float(m["value"][1]) > 0]
            if bad:
                for b in bad:
                    pod = b["metric"].get("pod","?")
                    notify(f"Pod restart detected: {pod}")

            # HTTP 5xx (if you expose metrics; example placeholder)
            # http5xx = sample_timeseries('sum(rate(http_requests_total{status=~"5.."}[5m]))')
            # if http5xx and http5xx[-1] > 0:
            #     notify(f"HTTP 5xx detected: {http5xx[-1]}")

            # CPU anomaly (z-score) across all pods
            cpu = sample_timeseries('sum(rate(container_cpu_usage_seconds_total{image!=""}[5m]))')
            if cpu and zscore(cpu) > 3.0:
                notify(f"CPU anomaly z>3: latest={cpu[-1]:.4f}")

        except Exception as e:
            print("loop error:", e)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    loop()
PY

cat > k8s/monitoring/anomaly-detector.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: neolight-anomaly-config
  namespace: neolight-observability
data:
  INTERVAL_SEC: "60"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neolight-anomaly-detector
  namespace: neolight-observability
spec:
  replicas: 1
  selector:
    matchLabels: {app: anomaly-detector}
  template:
    metadata:
      labels: {app: anomaly-detector}
    spec:
      containers:
        - name: detector
          image: python:3.12-slim
          args: ["python","/app/anomaly_detector.py"]
          env:
            - name: PROM_URL
              value: "http://neolight-obsv-kube-prometheus-sta-prometheus:9090"
            - name: INTERVAL_SEC
              valueFrom:
                configMapKeyRef:
                  name: neolight-anomaly-config
                  key: INTERVAL_SEC
            - name: PUSHOVER_TOKEN
              valueFrom:
                secretKeyRef:
                  name: pushover-keys
                  key: token
                  optional: true
            - name: PUSHOVER_USER
              valueFrom:
                secretKeyRef:
                  name: pushover-keys
                  key: user
                  optional: true
          volumeMounts:
            - name: app
              mountPath: /app
      volumes:
        - name: app
          configMap:
            name: neolight-anomaly-code
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: neolight-anomaly-code
  namespace: neolight-observability
data:
  anomaly_detector.py: |
$(sed 's/^/    /' monitoring/anomaly_detector.py)
---
apiVersion: v1
kind: Secret
metadata:
  name: pushover-keys
  namespace: neolight-observability
type: Opaque
stringData:
  token: "${PUSHOVER_TOKEN}"
  user: "${PUSHOVER_USER}"
YAML

kubectl apply -f k8s/monitoring/anomaly-detector.yaml >/dev/null

# ---------- AI Daily Summarizer (CronJob) ----------
banner "🧾 Deploying AI Daily Log Summarizer"
cat > monitoring/ai_summarizer.py <<'PY'
import os, datetime, requests, json, sys
OPENAI = os.getenv("OPENAI_API_KEY")
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN")
PUSHOVER_USER = os.getenv("PUSHOVER_USER")
LOKI = os.getenv("LOKI_URL","http://loki:3100")
QUERY = '{app="neolight"}'

def loki_query_range(q, start_ns, end_ns, step="5m"):
    params = {"query": q, "start": start_ns, "end": end_ns, "step": step}
    r = requests.get(f"{LOKI}/loki/api/v1/query_range", params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def simple_summary(lines, max_chars=1600):
    text = "\n".join(lines)[-max_chars:]
    return f"NeoLight Daily Summary:\n{ text[:max_chars] }"

def ai_summary(text):
    if not OPENAI:
        return simple_summary(text.splitlines())
    try:
        # Minimal OpenAI Chat Completions: model name is user-provided via env MODEL or default.
        import openai  # requires 'openai' installed in container if you enable this
        client = openai.OpenAI(api_key=OPENAI)
        model = os.getenv("OPENAI_MODEL","gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":"Summarize NeoLight logs into a crisp executive report with bullet points and any anomalies."},
                      {"role":"user","content":text[-12000:]}],
            max_tokens=500
        )
        return resp.choices[0].message.content
    except Exception as e:
        return simple_summary(text.splitlines())

def pushover(msg):
    if not (PUSHOVER_TOKEN and PUSHOVER_USER):
        return
    try:
        requests.post("https://api.pushover.net/1/messages.json", data={
            "token": PUSHOVER_TOKEN, "user": PUSHOVER_USER,
            "message": msg[:1024], "title": "NeoLight Daily Report"
        }, timeout=10)
    except Exception as e:
        print("pushover error:", e)

def main():
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(hours=24)
    start_ns = int(start.timestamp()*1e9)
    end_ns   = int(end.timestamp()*1e9)
    data = loki_query_range(QUERY, start_ns, end_ns)
    lines=[]
    for s in data.get("data",{}).get("result",[]):
        for ts,val in s.get("values",[]):
            lines.append(val)
    if not lines:
        print("No logs found; skipping.")
        return
    text="\n".join(lines)
    report = ai_summary(text)
    print(report)
    pushover(report)

if __name__ == "__main__":
    main()
PY

cat > k8s/monitoring/ai-summarizer.yaml <<'YAML'
apiVersion: v1
kind: ConfigMap
metadata:
  name: neolight-ai-summarizer
  namespace: neolight-observability
data:
  ai_summarizer.py: |
$(sed 's/^/    /' monitoring/ai_summarizer.py)
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: neolight-daily-summary
  namespace: neolight-observability
spec:
  schedule: "0 1 * * *" # daily 1:00 UTC
  jobTemplate:
    spec:
      backoffLimit: 0
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: summarizer
              image: python:3.12-slim
              command: ["python","/app/ai_summarizer.py"]
              env:
                - name: LOKI_URL
                  value: "http://loki:3100"
                - name: OPENAI_API_KEY
                  valueFrom:
                    secretKeyRef:
                      name: openai-key
                      key: api_key
                      optional: true
                - name: PUSHOVER_TOKEN
                  valueFrom:
                    secretKeyRef:
                      name: pushover-keys
                      key: token
                      optional: true
                - name: PUSHOVER_USER
                  valueFrom:
                    secretKeyRef:
                      name: pushover-keys
                      key: user
                      optional: true
              volumeMounts:
                - name: app
                  mountPath: /app
          volumes:
            - name: app
              configMap:
                name: neolight-ai-summarizer
---
apiVersion: v1
kind: Secret
metadata:
  name: openai-key
  namespace: neolight-observability
type: Opaque
stringData:
  api_key: "${OPENAI_API_KEY}"
YAML

kubectl apply -f k8s/monitoring/ai-summarizer.yaml >/dev/null

# ---------- output ----------
banner "✅ Phase 10300–11000 complete"
echo "Grafana     : NodePort 30000  (kubectl port-forward svc/neolight-obsv-grafana -n $ns 3000:80)"
echo "Prometheus  : NodePort 30090"
echo "Alertmanager: NodePort 30093"
echo "Tip (local):  kubectl -n $ns port-forward svc/neolight-obsv-grafana 3000:80"
echo "Login       : admin / \$GRAFANA_ADMIN_PASSWORD"
