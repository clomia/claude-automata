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
- [CRITICAL!] 5분 이상 걸리는 Bash 실행은 `Agent(run_in_background)`에 위임하세요.

</rules>

<MISSION>

$ARGUMENTS

</MISSION>
