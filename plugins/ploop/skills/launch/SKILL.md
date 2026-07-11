---
name: launch
description: launch parallax loop
argument-hint: "[mission]"
disable-model-invocation: true
---

<notice>

- parallax loop가 활성화되었습니다.
- parallax loop는 당신이 놓친 영역을 advisor가 찾아주는 유한 루프입니다.
- advisor는 시스템이 advisor invoke 구문을 제시할때만 invoke할 수 있습니다.

<notice>

<rules>

- [CAUTION] 사용자의 도움이 필요한 질문이나 요청이 발생하면 멈추지 말고 `AskUserQuestion`를 사용하세요.
  - `AskUserQuestion`은 루프 안에서 사용자와 소통할 수 있는 유일한 도구입니다. 창의적으로 활용하세요.
  - 반드시 사용자의 도움이 꼭 필요할때만 사용하고 가급적 스스로 판단하세요.
- [IMPORTANT] 먼저 폭 넓게 탐색해서 암묵적 False Assumption을 모두 찾으세요.
  - 탐색 영역별로 백그라운드 `Agent`를 전개.
  - 방대한 자료 조사에는 `deep-research` 스킬 사용.
  - 필요에 따라 `Workflow`를 직접 구성해서 실행.
- [IMPORTANT] background 작업(shell·agent·workflow 등)이 도는 동안 foreground를 비우지 마세요(비면 미완 라운드가 조기 심사됨). 대기는 `ploop:waiter`에 위임하세요:
  - **wait-command**를 준비하세요 — background 작업이 남기는 종결 신호(예: 로그의 `=== DONE`/`=== FAIL`)를 감지해, foreground에서 ~9분 self-bound하며 새 종결이 있으면 `WAIT-EVENT`(+증거)를, 없으면 `WAIT-TIMEOUT`을 출력. 예시(`$1`=현재 종결 개수):
    ```
    LOG=<로그 경로>; D=$((SECONDS+540))
    while [ $SECONDS -lt $D ]; do
      N=$(grep -cE '=== (DONE|FAIL)' "$LOG"); N=${N:-0}
      [ "$N" -gt "$1" ] && { echo WAIT-EVENT; tail -4 "$LOG"; exit 0; }
      sleep 15
    done; echo WAIT-TIMEOUT
    ```
  - 이 wait-command를 담아 `ploop:waiter`를 **foreground로** 호출하세요: `Agent(subagent_type="ploop:waiter", run_in_background=false)`(Agent 기본값이 background라 명시 필수). `WAIT-EVENT` 반환 시 처리하고, 남은 작업이 있으면 다시 호출.
- **당신이 미션의 Owner**입니다. Ownership을 가지고 자율적으로 진행하세요.
  - 미션은 대규모 장기 작업입니다. 전략적으로 접근하세요.
  - 당신에게는 미션을 위한 모든 권한과 책임이 있습니다.

</rules>

<MISSION>

$ARGUMENTS

</MISSION>
