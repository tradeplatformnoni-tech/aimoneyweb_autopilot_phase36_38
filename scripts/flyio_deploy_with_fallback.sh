#!/usr/bin/env bash
# NeoLight Fly.io Deployment with Fallback
# =========================================
# Tries remote build first, falls back to local build if needed
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="${FLY_APP:-neolight-cloud}"

red(){ printf "\033[0;31m%s\033[0m\n" "$*"; }
green(){ printf "\033[0;32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
cyan(){ printf "\033[0;36m%s\033[0m\n" "$*"; }

green "🚀 NeoLight Fly.io Deployment (with fallback)"
echo ""

# Try remote build first
green "Attempting remote build..."
if flyctl deploy --app "$APP_NAME" --config fly.toml 2>&1 | tee /tmp/fly_deploy.log; then
    green "✅ Deployment successful with remote build!"
    exit 0
fi

# Check if error is about remote builder
if grep -q "remote builder\|builder.*failed\|dial tcp.*builder" /tmp/fly_deploy.log; then
    yellow "⚠️  Remote builder issue detected. Trying local build..."
    echo ""
    
    # Try local build
    green "Attempting local Docker build..."
    if flyctl deploy --app "$APP_NAME" --config fly.toml --local-only 2>&1; then
        green "✅ Deployment successful with local build!"
        exit 0
    else
        red "❌ Local build also failed. Trying Docker build directly..."
        echo ""
        
        # Build Docker image locally first
        green "Building Docker image locally..."
        docker build -t neolight-cloud:latest -f Dockerfile . || {
            red "❌ Docker build failed. Please check Docker is running."
            exit 1
        }
        
        # Deploy with pre-built image
        green "Deploying pre-built image..."
        flyctl deploy --app "$APP_NAME" --config fly.toml --image neolight-cloud:latest || {
            red "❌ Deployment failed even with pre-built image."
            yellow "Please check the error messages above."
            exit 1
        }
    fi
else
    red "❌ Deployment failed for unknown reason. Check logs above."
    exit 1
fi

green "✅ Deployment complete!"


