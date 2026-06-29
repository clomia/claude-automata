---
name: init
description: 정의된 미션을 anchor에 핸드오프한다 — 미션 명세를 외부 파일에 기록하고 anchor 에이전트를 spawn해 parallax 루프를 시작한다
argument-hint: "[미션 이름 또는 짧은 설명]"
disable-model-invocation: true
---

정의된 미션을 anchor에 핸드오프합니다. 다음 순서로 직접 수행하세요.

## 1. 미션이 완전히 명세되었는지 확인

이 대화와 `$ARGUMENTS`로부터 미션을 조합합니다. 미션은 목표·맥락·제약·성공 기준이 모두 명확할 때에만 준비된 것입니다. 본질적인 것이 빠졌다면 진행 **전에** `AskUserQuestion`으로 사용자에게 물으세요 — 불완전한 명세로 무거운 트리를 시작해서는 안 됩니다. 미션을 irreducible하게, 군더더기 없이 빚으세요.

## 2. 미션 파일 경로 확인

`Bash`로 anchor가 읽을 미션 파일의 절대경로를 확인하세요(환경변수는 셸이 확장합니다):

```
echo "${CLAUDE_PLUGIN_DATA}/${CLAUDE_SESSION_ID}_mission.md"
```

anchor가 여기서 미션을 찾으므로 반드시 이 경로여야 합니다. 출력이 비면(환경변수 미설정) 핸드오프를 멈추고 사용자에게 알리세요.

## 3. 미션 명세 기록

확인한 절대경로에 완전한 미션 명세를 `Write` 도구로 기록하세요. 다음 구조를 사용하세요:

```markdown
# Mission

## 목표
<완료가 어떤 모습인지 한두 문장으로>

## 맥락
<트리가 필요로 하는 배경: 무엇이 어디 있는지, 왜 중요한지>

## 제약
<하드 리밋: 보존할 인터페이스, 건드리지 말 것, 따를 표준>

## 성공 기준
<미션 완료를 뜻하는 구체적이고 검증 가능한 조건>
```

## 4. anchor에게 핸드오프

`Agent(subagent_type="anchor:anchor", description="run mission", prompt="<2에서 확인한 절대경로>", run_in_background=true)`로 spawn하세요. **반드시 background로** — 그래야 메인이 자유로워 사용자가 `/anchor:log`로 진행을 볼 수 있습니다. prompt에는 미션 경로만 넣고, 당신의 해석·의견 등 다른 텍스트는 넣지 마세요.

## 5. 핸드오프 이후

이제 미션은 anchor 아래에서 parallax 루프로 진행됩니다. 당신의 역할은 사용자와 상호작용하고 조타하는 것이지 미션을 직접 실행하는 것이 아닙니다. 이 미션의 추가 대규모 작업은 여기서 직접 하지 말고 anchor를 재-spawn하거나 이어가도록 위임하세요. 진행 상황은 `/anchor:log`로 확인할 수 있습니다.
