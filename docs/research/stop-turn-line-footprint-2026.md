# Stop turn line footprint — bare 정지 판정 threshold의 실측 근거

- Date: 2026-08-16
- Question: main transcript에서 tool 활동이 없는 turn(bare stop)과 tool을 쓴 turn이
  line 반입량으로 분리되는가 — ploop bare-stop 판정(결정 24)의 threshold T 근거.
- Method: 이 machine의 Claude Code 2.1.233(`alwaysThinkingEnabled` on) 최근 세션
  transcript 6개(`~/.claude/projects/<dir>/*.jsonl`)를 스크립트로 전수 분석. turn =
  비-tool_result user message에서 다음 user message 직전까지의 모든 transcript line.
  assistant content에 `tool_use` block이 하나라도 있으면 tool turn, 없으면 bare turn으로
  분류해 line 수 분포를 수집.

## 발견

- ✅ **bare turn(text-only)은 1–9 line이다** — n=22, p50=1, p90=7, max=9. thinking
  block이 켜져 있어도 한 자릿수를 넘지 않았다.
- ✅ **tool turn의 최소 관측치는 23 line이다** — n=5, min=23(단일 tool 호출 turn),
  p50=44. 두 대역은 겹치지 않는다(9 < 23).
- 🔶 **T=15 채택** — 두 대역의 사이값, 양쪽 margin 확보. 판정 의미는 "이번 round에
  tool 활동이 전혀 없었다"이며, narrator relay만 한 turn(≈23 line)은 tool turn
  대역이라 working으로 읽힌다 — 1-tool 작업 round와 line 수로 구분 불능이므로 건강한
  소규모 round의 오판 종료를 피하는 방향을 택했다(결정 24의 수용).
- 🔶 오판의 양방향이 무해함이 채택의 전제다: 작업→bare 오판은 DECLINE nudge 1회
  (다음 working 정지에 counter reset), bare→작업 오판은 failsafe 1 round 지연.

## 표류 감시

transcript의 line 단위 구성(message/thinking/tool_use/tool_result가 각각 line을
차지하는 granularity)이 바뀌면 대역이 이동한다. 재측정 절차는 Method의 스크립트
분류를 재실행하는 것이며, `BARE_STOP_LINE_THRESHOLD`(`plugins/ploop/src/main.py`)가
소비 지점이다 — audit-harness-deps 순환의 대상.
