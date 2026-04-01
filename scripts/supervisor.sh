#!/usr/bin/env bash
# clomata — Stop hook 기반 감독관
#
# 수행자가 완료를 선언할 때마다:
# 1) 라운드 카운터 관리 (종료 조건)
# 2) 별도 claude -p 호출로 감독관 실행 (컨텍스트 분리)
# 3) 감독관 판단에 따라 block(exit 2) 또는 allow(exit 0)
#
# 환경변수:
#   CLOMATA_MAX_ROUNDS  — 최대 평가 라운드 (기본: 3)
#   CLOMATA_MODEL       — 감독관 모델 (기본: opus)

# ── 재귀 방지: 감독관 내부 claude 호출에서 이 hook이 다시 실행되면 무시 ──
if [ "$CLOMATA_SUPERVISOR_ACTIVE" = "1" ]; then
  exit 0
fi

INPUT=$(cat)
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active')
LAST_MSG=$(echo "$INPUT" | jq -r '.last_assistant_message // empty')

STATE_FILE="$CLAUDE_PROJECT_DIR/.clomata-state.json"
LOG_FILE="$CLAUDE_PROJECT_DIR/.clomata-debug.log"
PROMPT_FILE="${CLAUDE_PLUGIN_ROOT:-$(dirname "$0")/..}/scripts/supervisor-prompt.md"
MAX_ROUNDS=${CLOMATA_MAX_ROUNDS:-3}
MODEL=${CLOMATA_MODEL:-opus}

log() { echo "[clomata] $(date +%H:%M:%S) $*" >> "$LOG_FILE"; }

# ── 1. 라운드 관리 ──

# 새 작업(stop_hook_active=false) → 상태 초기화
if [ "$STOP_HOOK_ACTIVE" = "false" ]; then
  printf '{"round":0,"terminate":false}' > "$STATE_FILE"
fi

if [ ! -f "$STATE_FILE" ]; then
  printf '{"round":0,"terminate":false}' > "$STATE_FILE"
fi

ROUND=$(jq -r '.round' < "$STATE_FILE")
ROUND=$((ROUND + 1))

# 최대 라운드 초과 → 강제 종료
if [ "$ROUND" -gt "$MAX_ROUNDS" ]; then
  printf '{"round":%d,"terminate":true}' "$ROUND" > "$STATE_FILE"
  log "TERMINATE round=$ROUND > max=$MAX_ROUNDS"
  exit 0
fi

printf '{"round":%d,"terminate":false}' "$ROUND" > "$STATE_FILE"
log "round=$ROUND/$MAX_ROUNDS stop_hook_active=$STOP_HOOK_ACTIVE"

# ── 2. 감독관 에이전트 호출 (별도 컨텍스트) ──

TRUNCATED_MSG=$(echo "$LAST_MSG" | head -c 2000)

SUPERVISOR_INPUT=$(cat <<ENDOFPROMPT
$(cat "$PROMPT_FILE")

---
## 수행자의 마지막 응답 (평가 대상):
$TRUNCATED_MSG
---
위 프로토콜에 따라 JSON으로만 응답하라. 다른 텍스트를 출력하지 마라.
ENDOFPROMPT
)

SUPERVISOR_RESULT=$(CLOMATA_SUPERVISOR_ACTIVE=1 claude -p "$SUPERVISOR_INPUT" --model "$MODEL" 2>/dev/null || echo "ERROR")

log "supervisor raw: $(echo "$SUPERVISOR_RESULT" | head -c 500)"

# ── 3. 감독관 판단 파싱 ──

JSON_PART=$(echo "$SUPERVISOR_RESULT" | tr -d '\n' | grep -oE '\{[^}]+\}' | head -1)
log "parsed json: $JSON_PART"
OK_VALUE=$(echo "$JSON_PART" | jq -r 'if .ok == true then "true" elif .ok == false then "false" else "null" end' 2>/dev/null)
REASON=$(echo "$JSON_PART" | jq -r '.reason // ""' 2>/dev/null)

if [ "$OK_VALUE" = "null" ] || [ -z "$OK_VALUE" ]; then
  log "WARN: parse failed, allowing stop"
  exit 0
fi

if [ "$OK_VALUE" = "true" ]; then
  log "ALLOW: supervisor ok"
  exit 0
fi

log "BLOCK round=$ROUND: reason=$REASON"
echo "$REASON" >&2
exit 2
