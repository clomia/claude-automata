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

- [CAUTION] **질문이나 요청이 발생하면 멈추지 말고 `AskUserQuestion`를 사용**하세요.
- [IMPORTANT] 먼저 폭 넓게 탐색해서 암묵적 False Assumption을 모두 찾으세요.
  - 탐색 영역별로 백그라운드 `Agent`를 전개.
  - 방대한 자료 조사에는 `deep-research` 스킬 사용.
  - 필요에 따라 `Workflow`를 직접 구성해서 실행.
- 미션은 대규모 장기 작업입니다. 전략적으로 접근하세요.

</rules>

<MISSION>

$ARGUMENTS

</MISSION>
