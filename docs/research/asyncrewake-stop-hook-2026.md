# asyncRewake Stop hook — 3h heartbeat의 운반체로 성립하는가

- Date: 2026-07-30
- Question: `asyncRewake: true` command Stop hook이 (1) 수 시간짜리 `timeout`을
  clamp 없이 허용하고 (2) idle interactive session을 exit 2로 실제로 깨우며 stderr
  payload를 모델에 전달하는가 — ploop heartbeat(결정 19)의 전제.
- Method: ① 설치된 Claude Code 번들(2.1.218/2.1.219/2.1.220, bun-compiled ELF)을
  binary grep + context dump로 정적 분석. ② 격리 tmux 세션에서 live canary: scratch
  project의 `.claude/settings.json`에 asyncRewake Stop hook(`timeout: 700`)을 걸고,
  hook script는 production heartbeat와 동일한 exec-chain 형태(`cat > /dev/null` 후
  `exec /bin/sh -c 'sleep 75; printf … >&2; exit 2'`)로 구성. 1-turn 대화 후 idle
  방치, pane capture로 wake 관측.

## 발견

- ✅ **`asyncRewake`는 2.1.218·2.1.219·2.1.220 번들에 hook schema field로 실재한다**
  (`asyncRewake:v.boolean().optional().describe("If true, hook runs in background and
  wakes the model on exit code 2 (blocking error). Implies async.")`).
- ✅ **command hook `timeout`은 무clamp다** — 실행 경로는 `P=e.timeout?e.timeout*1000:Hm`
  (설정값 초 × 1000, 기본값만 상수), async 등록은 `asyncTimeout:P`를 그대로 소비
  (`let c=r.asyncTimeout||15000`). 번들 전수 검색에서 hook timeout에 대한 `Math.min`
  상한은 SessionEnd 예산 함수 하나뿐 — 일반 Stop hook의 11100s는 원값으로 전달된다.
- ✅ **idle session이 실제로 깨어난다** — canary에서 마지막 turn 종료 75초 뒤 pane에
  `● Stop hook feedback` 라인과 함께 payload가 지시한 응답(`● CANARY-ACK`)이 출현.
  exec-chain을 거쳐도 PID가 보존되어 최종 exit 2가 관측됨을 함께 증명한다.
- ✅ **wake 게이트는 interactive 한정** — 번들의 `(e.async||e.asyncRewake&&K)` 분기
  (`K=!yn()||rNr()`). headless(`claude -p`)에서 armed session을 resume하면 이 hook이
  동기 실행될 수 있으나, headless resume은 ploop 보장 범위 밖이다(결정 19).
- ✅ **`exec uv run`은 python으로 exec하지 않는다** — uv(0.11.21)가 ~26MB RSS 부모로
  상주하고 python은 자식이다(process tree 실측 2026-07-30). 따라서 장기 sleep을
  python(또는 python이 exec한 자식)에 두면 timer당 uv 한 개가 3h 상주한다 — 상주는
  uv 호출 이전의 wrapper sh(~1MB)가 맡아야 slim하다. ploop heartbeat가 이 형태다.
- 🔶 Judgment: 75s canary + 무clamp 정적 증거로 3h(10800s)를 외삽한다. 전 구간 live
  3h 측정은 하지 않았다 — 이 외삽이 틀리는 방향의 실패는 "wake 미발화 = heartbeat
  이전 현상 유지"라 새 피해가 없어, 측정 비용 대비 실익이 없다.
- ❓ 번들에 `rewakeMessage`/`rewakeSummary` field가 존재하나 `@internal` 표기 —
  의존하지 않는다(stderr payload만 사용).

재측정 방법: 이 문서의 Method 그대로 — canary hook·driver는 5분 내 재구성 가능한
수준의 형태라 파일 보존이 불필요하다(자기완결).
