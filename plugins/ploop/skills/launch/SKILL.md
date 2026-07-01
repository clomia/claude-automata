---
name: launch
description: 정의된 미션을 ploop에 핸드오프한다 — 미션 명세를 외부 파일에 기록하고 메인 에이전트가 직접 parallax 루프로 미션을 끝까지 수행한다
argument-hint: "[미션 이름 또는 짧은 설명]"
disable-model-invocation: true
---

정의된 미션을 ploop에 핸드오프합니다. 다음 순서로 직접 수행하세요.

## 1. 미션이 완전히 명세되었는지 확인

이 대화와 `$ARGUMENTS`로부터 미션을 조합합니다. 미션은 목표·맥락·제약·성공 기준이 모두 명확할 때에만 준비된 것입니다. 본질적인 것이 빠졌다면 진행 **전에** `AskUserQuestion`으로 사용자에게 물으세요 — 불완전한 명세로 무거운 루프를 시작해서는 안 됩니다. 미션을 irreducible하게, 군더더기 없이 빚으세요.

## 2. 경로 확인

`Bash`로 절대경로를 확인하세요(환경변수는 셸이 확장합니다):

```
echo "mission: ${CLAUDE_PLUGIN_DATA}/${CLAUDE_SESSION_ID}_mission.md"
echo "active:  ${CLAUDE_PLUGIN_DATA}/${CLAUDE_SESSION_ID}_active"
```

당신이 여기서 미션을 찾습니다. 출력이 비면(환경변수 미설정) 핸드오프를 멈추고 사용자에게 알리세요.

## 3. original-mission 명세 기록

확인한 mission 절대경로에 완전한 미션 명세를 `Write`로 기록하세요. 다음 구조를 사용하세요:

```markdown
# Mission

## 목표
<완료가 어떤 모습인지 한두 문장으로>

## 맥락
<미션이 필요로 하는 배경: 무엇이 어디 있는지, 왜 중요한지>

## 제약
<하드 리밋: 보존할 인터페이스, 건드리지 말 것, 따를 표준>

## 성공 기준
<미션 완료를 뜻하는 구체적이고 검증 가능한 조건>
```

## 4. 루프 켜기

확인한 active 절대경로에 빈 파일을 만드세요(`Write`로 빈 내용, 또는 `Bash`의 `touch`). 이 마커가 ploop을 이 세션에 활성화합니다 — 마커가 없으면 아무것도 발화하지 않습니다.

## 5. 미션 수행 — 당신의 닻은 original-mission

이제 당신이 이 미션을 처음부터 끝까지, 놓친 것 없이 직접 수행합니다.

먼저 mission 파일을 `Read`해 미션을 내재화하세요. 이 파일은 컨텍스트 바깥에 영속하는 source of truth이니, compaction되거나 맥락이 흐려지면 언제든 다시 `Read`해 재정박(anchor)하세요.

mission의 언어와 동일한 언어로 작업하세요. 이 미션은 매우 오래 걸릴 수 있습니다 — 도중에 멈추지 말고 끝까지 완수하세요.
