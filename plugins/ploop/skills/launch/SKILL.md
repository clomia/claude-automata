---
name: launch
description: launch parallax loop
argument-hint: "[mission]"
disable-model-invocation: true
---

<MISSION>
$ARGUMENTS
</MISSION>

<launch>

## 준비

1. `uv run --project "${CLAUDE_PLUGIN_ROOT}" mission-path "${CLAUDE_PLUGIN_DATA}"` 를 실행하여 출력된 경로에 미션을 저장(`Write`)하세요.
2. `uv run --project "${CLAUDE_PLUGIN_ROOT}" activation "${CLAUDE_PLUGIN_DATA}"` 를 실행하여 parallax loop를 활성화 하세요.

## 시작

이 미션은 대규모 장기 작업입니다. 멈추지 말고 끝까지 완수하세요. 저장된 미션 파일이 source of truth입니다.

</launch>

<parallax-loop>
- parallax loop는 당신이 놓친 영역을 advisor가 찾아주는 유한 루프입니다.  
- advisor는 시스템이 advisor invoke 구문을 제시할때만 invoke할 수 있습니다.
</parallax-loop>
