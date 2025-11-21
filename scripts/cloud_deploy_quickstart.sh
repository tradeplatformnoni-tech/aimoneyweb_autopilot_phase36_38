#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║ NeoLight 24-Hour Cloud Deployment - Quick Start Script          ║
# ║ Automates Google Cloud setup and initial deployment              ║
# ╚══════════════════════════════════════════════════════════════════╝

set -euo pipefail

# ── Colors ─────────────────────────────────────────────────────────
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
RED=$'\033[0;31m'
CYAN=$'\033[0;36m'
RESET=$'\033[0m'

# ── Configuration ───────────────────────────────────────────────────
PROJECT_NAME="${GCP_PROJECT_NAME:-neolight-production}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="neolight-failover"

echo "${CYAN}╔══════════════════════════════════════════════════════════════════╗${RESET}"
echo "${CYAN}║  NeoLight 24-Hour Cloud Deployment - Quick Start               ║${RESET}"
echo "${CYAN}╚══════════════════════════════════════════════════════════════════╝${RESET}"
echo ""

# ── Step 1: Check Prerequisites ───────────────────────────────────
echo "${YELLOW}📋 Step 1: Checking prerequisites...${RESET}"

check_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "${RED}❌ $1 not found${RESET}"
        echo "   Install with: $2"
        return 1
    else
        echo "${GREEN}✅ $1 installed${RESET}"
        return 0
    fi
}

MISSING=0
check_command "gcloud" "brew install --cask google-cloud-sdk" || MISSING=1
check_command "gsutil" "brew install --cask google-cloud-sdk" || MISSING=1
check_command "jq" "brew install jq" || MISSING=1

if [[ $MISSING -eq 1 ]]; then
    echo "${RED}❌ Please install missing tools and run again${RESET}"
    exit 1
fi

# ── Step 2: Authenticate ───────────────────────────────────────────
echo ""
echo "${YELLOW}🔐 Step 2: Authenticating with Google Cloud...${RESET}"

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "   Opening browser for authentication..."
    gcloud auth login
else
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
    echo "${GREEN}✅ Already authenticated as: $ACTIVE_ACCOUNT${RESET}"
fi

# ── Step 3: Set Project ────────────────────────────────────────────
echo ""
echo "${YELLOW}📦 Step 3: Setting up Google Cloud project...${RESET}"

# Check if project exists
if ! gcloud projects describe "$PROJECT_NAME" &>/dev/null; then
    echo "   Creating project: $PROJECT_NAME"
    gcloud projects create "$PROJECT_NAME" --name="NeoLight Production" || {
        echo "${RED}❌ Failed to create project. It may already exist or name is taken.${RESET}"
        read -p "   Enter existing project name (or press Enter to use '$PROJECT_NAME'): " CUSTOM_PROJECT
        if [[ -n "$CUSTOM_PROJECT" ]]; then
            PROJECT_NAME="$CUSTOM_PROJECT"
        fi
    }
fi

gcloud config set project "$PROJECT_NAME"
gcloud config set run/region "$REGION"
echo "${GREEN}✅ Project set to: $PROJECT_NAME${RESET}"
echo "${GREEN}✅ Region set to: $REGION${RESET}"

# ── Step 4: Enable Services ────────────────────────────────────────
echo ""
echo "${YELLOW}⚙️  Step 4: Enabling required Google Cloud services...${RESET}"

gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    storage.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com \
    compute.googleapis.com 2>&1 | grep -v "already enabled" || true

echo "${GREEN}✅ Services enabled${RESET}"

# ── Step 5: Create State Bucket ────────────────────────────────────
echo ""
echo "${YELLOW}☁️  Step 5: Creating state storage bucket...${RESET}"

BUCKET_NAME="neolight-state-$(date +%s)"
export NL_BUCKET="gs://$BUCKET_NAME"

if gsutil ls "$NL_BUCKET" &>/dev/null; then
    echo "${GREEN}✅ Bucket already exists: $NL_BUCKET${RESET}"
else
    gsutil mb -l "$REGION" -b on "$NL_BUCKET"
    echo "${GREEN}✅ Bucket created: $NL_BUCKET${RESET}"
fi

# Persist to shell
echo "export NL_BUCKET=$NL_BUCKET" >> ~/.zshrc
echo "${GREEN}✅ Bucket saved to ~/.zshrc${RESET}"

# ── Step 6: Generate API Key ───────────────────────────────────────
echo ""
echo "${YELLOW}🔑 Step 6: Generating API key...${RESET}"

if [[ -z "${CLOUD_RUN_API_KEY:-}" ]]; then
    export CLOUD_RUN_API_KEY=$(openssl rand -hex 32)
    echo "export CLOUD_RUN_API_KEY=$CLOUD_RUN_API_KEY" >> ~/.zshrc
    echo "${GREEN}✅ API key generated and saved${RESET}"
    echo "${YELLOW}⚠️  IMPORTANT: Save this API key securely!${RESET}"
    echo "${CYAN}   API Key: $CLOUD_RUN_API_KEY${RESET}"
else
    echo "${GREEN}✅ Using existing API key${RESET}"
fi

# ── Step 7: Store Secrets ───────────────────────────────────────────
echo ""
echo "${YELLOW}🔒 Step 7: Setting up Secret Manager...${RESET}"

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_NAME" --format="value(projectNumber)")

# Store API key in Secret Manager
if ! gcloud secrets describe neolight-api-key &>/dev/null; then
    echo -n "$CLOUD_RUN_API_KEY" | \
        gcloud secrets create neolight-api-key \
            --replication-policy="automatic" \
            --data-file=- 2>&1 | grep -v "already exists" || true
    
    gcloud secrets add-iam-policy-binding neolight-api-key \
        --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor" 2>&1 | grep -v "already bound" || true
    
    echo "${GREEN}✅ API key stored in Secret Manager${RESET}"
else
    echo "${GREEN}✅ Secret already exists${RESET}"
fi

# ── Step 8: Prompt for Alpaca Keys ─────────────────────────────────
echo ""
echo "${YELLOW}💼 Step 8: Alpaca API keys setup...${RESET}"

# Check .env file for keys (supports both ALPACA_SECRET_KEY and ALPACA_API_SECRET)
if [[ -f "$HOME/neolight/.env" ]]; then
    source "$HOME/neolight/.env"
    # Handle both naming conventions
    if [[ -n "${ALPACA_API_SECRET:-}" ]] && [[ -z "${ALPACA_SECRET_KEY:-}" ]]; then
        export ALPACA_SECRET_KEY="$ALPACA_API_SECRET"
    fi
fi

if [[ -z "${ALPACA_API_KEY:-}" ]] || [[ -z "${ALPACA_SECRET_KEY:-}" ]]; then
    echo "   Please enter your Alpaca API keys (or press Enter to skip):"
    read -p "   Alpaca API Key: " ALPACA_KEY
    read -sp "   Alpaca Secret Key: " ALPACA_SECRET
    echo ""
    
    if [[ -n "$ALPACA_KEY" ]] && [[ -n "$ALPACA_SECRET" ]]; then
        echo -n "$ALPACA_KEY" | \
            gcloud secrets create alpaca-api-key \
                --replication-policy="automatic" \
                --data-file=- 2>&1 | grep -v "already exists" || true
        
        echo -n "$ALPACA_SECRET" | \
            gcloud secrets create alpaca-secret-key \
                --replication-policy="automatic" \
                --data-file=- 2>&1 | grep -v "already exists" || true
        
        gcloud secrets add-iam-policy-binding alpaca-api-key \
            --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
            --role="roles/secretmanager.secretAccessor" 2>&1 | grep -v "already bound" || true
        
        gcloud secrets add-iam-policy-binding alpaca-secret-key \
            --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
            --role="roles/secretmanager.secretAccessor" 2>&1 | grep -v "already bound" || true
        
        echo "${GREEN}✅ Alpaca keys stored in Secret Manager${RESET}"
    else
        echo "${YELLOW}⚠️  Skipped Alpaca keys (you can add them later)${RESET}"
    fi
else
    echo "${GREEN}✅ Alpaca keys found in environment or .env file${RESET}"
    ALPACA_KEY="$ALPACA_API_KEY"
    ALPACA_SECRET="$ALPACA_SECRET_KEY"
    
    if [[ -n "$ALPACA_KEY" ]] && [[ -n "$ALPACA_SECRET" ]]; then
        echo -n "$ALPACA_KEY" | \
            gcloud secrets create alpaca-api-key \
                --replication-policy="automatic" \
                --data-file=- 2>&1 | grep -v "already exists" || true
        
        echo -n "$ALPACA_SECRET" | \
            gcloud secrets create alpaca-secret-key \
                --replication-policy="automatic" \
                --data-file=- 2>&1 | grep -v "already exists" || true
        
        gcloud secrets add-iam-policy-binding alpaca-api-key \
            --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
            --role="roles/secretmanager.secretAccessor" 2>&1 | grep -v "already bound" || true
        
        gcloud secrets add-iam-policy-binding alpaca-secret-key \
            --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
            --role="roles/secretmanager.secretAccessor" 2>&1 | grep -v "already bound" || true
        
        echo "${GREEN}✅ Alpaca keys stored in Secret Manager${RESET}"
    fi
fi

# ── Step 9: Sync State ─────────────────────────────────────────────
echo ""
echo "${YELLOW}📤 Step 9: Syncing local state to cloud...${RESET}"

if [[ -d "$HOME/neolight/state" ]]; then
    if [[ -f "$HOME/neolight/scripts/sync_state_to_cloud.sh" ]]; then
        "$HOME/neolight/scripts/sync_state_to_cloud.sh" || {
            echo "${YELLOW}⚠️  State sync had issues, but continuing...${RESET}"
        }
    else
        echo "   Syncing manually..."
        gsutil -m rsync -r "$HOME/neolight/state" "$NL_BUCKET/state" || {
            echo "${YELLOW}⚠️  State sync had issues, but continuing...${RESET}"
        }
    fi
    echo "${GREEN}✅ State synced${RESET}"
else
    echo "${YELLOW}⚠️  No local state directory found, skipping sync${RESET}"
fi

# ── Step 10: Deploy to Cloud Run ───────────────────────────────────
echo ""
echo "${YELLOW}🚀 Step 10: Deploying to Cloud Run...${RESET}"
echo "   This will take 10-15 minutes..."
echo ""

cd "$HOME/neolight" || exit 1

gcloud builds submit \
    --config cloud-run/cloudbuild.yaml \
    --substitutions _NL_BUCKET="$NL_BUCKET" || {
    echo "${RED}❌ Deployment failed. Check logs above.${RESET}"
    exit 1
}

# ── Step 11: Get Service URL ──────────────────────────────────────
echo ""
echo "${YELLOW}🌐 Step 11: Getting service URL...${RESET}"

export CLOUD_RUN_SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --format 'value(status.url)')

echo "export CLOUD_RUN_SERVICE_URL=$CLOUD_RUN_SERVICE_URL" >> ~/.zshrc

echo "${GREEN}✅ Service URL: $CLOUD_RUN_SERVICE_URL${RESET}"

# ── Step 12: Test Deployment ──────────────────────────────────────
echo ""
echo "${YELLOW}🧪 Step 12: Testing deployment...${RESET}"

sleep 5  # Wait for service to be ready

if curl -s "$CLOUD_RUN_SERVICE_URL/health" | jq -e '.status == "healthy"' >/dev/null 2>&1; then
    echo "${GREEN}✅ Health check passed!${RESET}"
    curl -s "$CLOUD_RUN_SERVICE_URL/health" | jq .
else
    echo "${YELLOW}⚠️  Health check returned unexpected result${RESET}"
    curl -s "$CLOUD_RUN_SERVICE_URL/health" || echo "   Service may still be starting..."
fi

# ── Summary ────────────────────────────────────────────────────────
echo ""
echo "${CYAN}╔══════════════════════════════════════════════════════════════════╗${RESET}"
echo "${CYAN}║  ✅ Google Cloud Setup Complete!                                ║${RESET}"
echo "${CYAN}╚══════════════════════════════════════════════════════════════════╝${RESET}"
echo ""
echo "${GREEN}📋 Summary:${RESET}"
echo "   Project: $PROJECT_NAME"
echo "   Region: $REGION"
echo "   Service: $SERVICE_NAME"
echo "   URL: $CLOUD_RUN_SERVICE_URL"
echo "   Bucket: $NL_BUCKET"
echo ""
echo "${YELLOW}📝 Next Steps:${RESET}"
echo "   1. Configure Cloudflare (see 24HOUR_CLOUD_DEPLOYMENT_PLAN.md)"
echo "   2. Clean up Render (optional)"
echo "   3. Test failover: curl -X POST \"$CLOUD_RUN_SERVICE_URL/activate\" \\"
echo "      -H \"X-API-Key: $CLOUD_RUN_API_KEY\""
echo "   4. Monitor logs: gcloud logging tail \"resource.type=cloud_run_revision\""
echo ""
echo "${CYAN}📚 Full guide: 24HOUR_CLOUD_DEPLOYMENT_PLAN.md${RESET}"
echo ""

