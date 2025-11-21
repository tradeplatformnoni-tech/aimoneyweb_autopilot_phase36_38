#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-$HOME/neolight}"
LOG="$ROOT/logs/code_fix_hook.log"
mkdir -p "$ROOT/logs"

# Extract failed agent name and log path from environment or arguments
AGENT_NAME="${1:-unknown_agent}"
AGENT_LOG="${2:-$ROOT/logs/${AGENT_NAME}.log}"
ERROR_CONTEXT="${3:-}"

echo "[code_fix_hook] Starting repair for $AGENT_NAME @ $(date -Is)" >> "$LOG"

# Extract last error from log
LAST_ERROR=$(tail -n 50 "$AGENT_LOG" 2>/dev/null | grep -iE "error|exception|traceback|failed" | tail -n 10 || echo "No error found in log")
RELEVANT_CODE=$(tail -n 100 "$AGENT_LOG" 2>/dev/null || echo "No code context available")

# Prepare repair prompt
PROMPT="NeoLight agent '$AGENT_NAME' crashed 3 times. Last error:\n\n$LAST_ERROR\n\nCode context:\n$RELEVANT_CODE\n\nProvide a Python fix that:\n1. Addresses the root cause\n2. Maintains idempotency\n3. Logs errors to logs/*.log\n4. Uses Optional[T] not type|None\n\nReturn only the fixed code block."

# Try Cursor API first (if CURSOR_API_KEY is set)
if [ -n "${CURSOR_API_KEY:-}" ]; then
  echo "[code_fix_hook] Attempting Cursor API repair..." >> "$LOG"
  RESPONSE=$(curl -s -X POST "https://api.cursor.sh/v1/chat/completions" \
    -H "Authorization: Bearer $CURSOR_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"gpt-4\",
      \"messages\": [
        {\"role\": \"system\", \"content\": \"You are a Python expert fixing NeoLight trading system code. Follow .cursorrules standards.\"},
        {\"role\": \"user\", \"content\": $(echo "$PROMPT" | jq -Rs .)}
      ],
      \"temperature\": 0.1,
      \"max_tokens\": 2000
    }" 2>>"$LOG")
  
  if [ $? -eq 0 ] && echo "$RESPONSE" | grep -q "choices"; then
    FIXED_CODE=$(echo "$RESPONSE" | jq -r '.choices[0].message.content' 2>/dev/null || echo "")
    if [ -n "$FIXED_CODE" ] && [ "$FIXED_CODE" != "null" ]; then
      echo "[code_fix_hook] Cursor repair successful" >> "$LOG"
      echo "$FIXED_CODE" >> "$LOG"
      # Save fix to file for review
      echo "$FIXED_CODE" > "$ROOT/logs/${AGENT_NAME}_fix_$(date +%Y%m%d_%H%M%S).py"
      exit 0
    fi
  fi
fi

# Fallback to DeepSeek API (if DEEPSEEK_API_KEY is set)
if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
  echo "[code_fix_hook] Attempting DeepSeek API repair..." >> "$LOG"
  RESPONSE=$(curl -s -X POST "https://api.deepseek.com/v1/chat/completions" \
    -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"deepseek-chat\",
      \"messages\": [
        {\"role\": \"system\", \"content\": \"You are a Python expert fixing NeoLight trading system code. Follow .cursorrules standards.\"},
        {\"role\": \"user\", \"content\": $(echo "$PROMPT" | jq -Rs .)}
      ],
      \"temperature\": 0.1,
      \"max_tokens\": 2000
    }" 2>>"$LOG")
  
  if [ $? -eq 0 ] && echo "$RESPONSE" | grep -q "choices"; then
    FIXED_CODE=$(echo "$RESPONSE" | jq -r '.choices[0].message.content' 2>/dev/null || echo "")
    if [ -n "$FIXED_CODE" ] && [ "$FIXED_CODE" != "null" ]; then
      echo "[code_fix_hook] DeepSeek repair successful" >> "$LOG"
      echo "$FIXED_CODE" >> "$LOG"
      echo "$FIXED_CODE" > "$ROOT/logs/${AGENT_NAME}_fix_$(date +%Y%m%d_%H%M%S).py"
      exit 0
    fi
  fi
fi

# If no API keys or both failed, log and exit gracefully
if [ -z "${CURSOR_API_KEY:-}" ] && [ -z "${DEEPSEEK_API_KEY:-}" ]; then
  echo "[code_fix_hook] No API keys set (CURSOR_API_KEY or DEEPSEEK_API_KEY). Manual review required." >> "$LOG"
else
  echo "[code_fix_hook] Both APIs failed. Manual review required." >> "$LOG"
fi

exit 1
