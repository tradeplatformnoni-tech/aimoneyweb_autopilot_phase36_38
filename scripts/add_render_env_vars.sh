#!/bin/bash
# Script to help add environment variables to Render service
# Note: Render API doesn't support adding env vars programmatically
# This script provides the values to paste into the dashboard

SERVICE_ID="srv-d4fl5s0gjchc73e5hfrg"
SERVICE_URL="https://neolight-autopilot.onrender.com"

echo "════════════════════════════════════════════════════════════"
echo "🔑 Render Environment Variables - Ready to Paste"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Service ID: $SERVICE_ID"
echo "Service URL: $SERVICE_URL"
echo ""
echo "Go to: https://dashboard.render.com/web/$SERVICE_ID/environment"
echo ""
echo "Add these environment variables:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. ALPACA_API_KEY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PKFMRWR2GQKENN4ARPHYMCGIBH"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. ALPACA_SECRET_KEY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5VNKFg2aiaECmjsUDZseBkbq8WH8Ancmd3nKMiXzDTh1"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. RCLONE_REMOTE (optional)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "neo_remote"
echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
echo "After adding, choose: 'Save, rebuild, and deploy'"
echo ""

