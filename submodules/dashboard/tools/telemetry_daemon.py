import os, psutil, time, json, datetime
LOG = "logs/performance/telemetry.csv"
os.makedirs(os.path.dirname(LOG), exist_ok=True)

header = "timestamp,cpu_percent,mem_percent\n"
if not os.path.exists(LOG):
    open(LOG,"w").write(header)

while True:
    cpu, mem = psutil.cpu_percent(), psutil.virtual_memory().percent
    line = f"{datetime.datetime.now()},{cpu},{mem}\n"
    open(LOG,"a").write(line)
    time.sleep(60)
