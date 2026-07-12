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

- 행동하기 전에 폭 넓게 탐색해서 암묵적 False Assumption을 모두 찾으세요.
  - 탐색 영역별로 백그라운드 `Agent`를 전개.
  - 방대한 자료 조사에는 `deep-research` 스킬 사용.
  - 필요에 따라 `Workflow`를 직접 구성해서 실행.
- **당신이 미션의 Owner**입니다. Ownership을 가지고 자율적으로 진행하세요.
  - 미션은 대규모 장기 작업입니다. 전략적으로 접근하세요.
  - 당신에게는 미션을 위한 모든 권한과 책임이 있습니다.
- [CAUTION] 사용자의 도움이 필요한 질문이나 요청이 발생하면 멈추지 말고 `AskUserQuestion`를 사용하세요.
  - `AskUserQuestion`은 루프 안에서 사용자와 소통할 수 있는 유일한 도구입니다. 창의적으로 활용하세요.
  - 반드시 사용자의 도움이 꼭 필요할때만 사용하고 가급적 스스로 판단하세요.
- [CRITICAL!] ploop 안에서는 미션이 종료되기 전까지 절대 foreground를 비우면 안됩니다! waiter를 사용해서 background(shell·agent·workflow 등)만 있는 상태로 foreground가 비어버리는 상황을 막으세요.
  - waiter는 반드시 foreground로 실행: `Agent(..., subagent_type="ploop:waiter", run_in_background=false)`
  - background 작업 중 하나라도 끝나면 `WAIT-DONE`을 출력하며 종료되는 wait-command를 작성해서 waiter에게 전달하세요.
    ```
    LOG=<로그 경로>; BASE=<종결개수>  # BASE: snapshot the count right before invoking the waiter
    while :; do
      N=$(grep -cE '=== (DONE|FAIL)' "$LOG"); N=${N:-0}
      [ "$N" -gt "$BASE" ] && { echo WAIT-DONE; tail -4 "$LOG"; exit 0; }
      sleep 15
    done
    ```
  - waiter는 WAIT-DONE이 나올 때까지 foreground를 잡아주는 전문 에이전트입니다. waiter에게는 **오직 wait-command만 전달**하세요.

</rules>

<MISSION>

$ARGUMENTS

</MISSION>
