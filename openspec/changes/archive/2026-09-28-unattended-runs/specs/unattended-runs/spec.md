## Purpose

claude-automata의 자율 run(ploop loop·refine workflow)이 사람 없이 끝까지 도는 계약 — 시작 조건,
무인 session의 범위, 사람을 기다릴 뻔한 모든 dialog에 plugin이 스스로 답하는 방식.

## ADDED Requirements

### Requirement: Bypass-only start

ploop loop의 arm(`/ploop:launch`·`/ploop:on`)과 refine workflow의 발사는 session의 effective
permission mode가 `bypassPermissions`일 때만 일어나야 한다(SHALL). mode는 hook이 받는 session의
현재 값으로 판정해야 하며(MUST) settings 파일의 선언을 읽어서는 안 된다(MUST NOT) — harness는
project·local settings의 `bypassPermissions`를 무시한다. 조건이 맞지 않으면 run은 시작하지 않고,
session을 `bypassPermissions`로 여는 방법(`claude --permission-mode bypassPermissions`)과 repository
settings로는 부여할 수 없다는 사실을 사유로 내야 한다(SHALL). 거부는 run 상태를 바꾸지 않는다(MUST).

#### Scenario: bypass 아닌 session의 launch

- **WHEN** `auto` mode session에서 `/ploop:launch <anchor>`를 실행하면
- **THEN** 확장이 차단되고, 사유에 `claude --permission-mode bypassPermissions`가 있으며, loop는
  arm되지 않는다

#### Scenario: bypass 아닌 session의 refine

- **WHEN** Manual mode session에서 refine workflow가 발사되려 하면
- **THEN** Workflow 호출이 거부되고 같은 사유가 전달되며, session은 무인으로 표시되지 않는다

#### Scenario: resume도 같은 문

- **WHEN** 일시정지된 loop를 bypass가 아닌 mode에서 `/ploop:on`으로 재개하려 하면
- **THEN** 재개가 차단되고 loop는 멈춘 상태로 남는다

### Requirement: Unattended session span

run을 시작한 session은 그 순간부터 session이 끝날 때까지 무인 session이어야 한다(SHALL) — loop의
일시정지·종료 뒤, workflow 완료 뒤에도 풀리지 않는다. ploop은 loop를 launch한 적이 있는 session,
refine은 자기 workflow를 발사한 적이 있는 session을 무인으로 본다. run을 시작한 적이 없는 session
(define·docent session, 일반 대화)은 무인이 아니어야 하며(MUST), 그 session의 dialog에 plugin은
관여하지 않는다(MUST NOT). 무인 session의 subagent·workflow agent 안에서 생긴 요청도 그
session의 것이다(SHALL).

#### Scenario: 일시정지 뒤에도 무인

- **WHEN** loop를 `/ploop:off`로 멈춘 session에서 이어진 turn이 권한 요청을 만들면
- **THEN** plugin이 그 요청에 답해 dialog가 뜨지 않는다

#### Scenario: run 없는 session

- **WHEN** run을 시작한 적 없는 session에서 권한 요청이 생기면
- **THEN** plugin은 답하지 않고 harness의 평소 흐름대로 dialog가 뜬다

#### Scenario: subagent의 요청

- **WHEN** 무인 session의 background subagent가 critical-path 삭제를 시도하면
- **THEN** 그 요청은 main session의 무인 판정을 따라 거부된다

### Requirement: Dialog answers

무인 session에서 plugin은 hook이 받는 dialog에 다음처럼 답해야 한다(SHALL) — 사람을 기다리지 않도록:

- permission 요청(critical-path 삭제·ask rule·`AskUserQuestion`·plan 승인 등 hook이 받는 전부)은
  **deny**하되(MUST), 사유는 에이전트가 행동을 바꿀 수 있어야 한다 — 질문이면 스스로 결정하고
  가정을 밝혀 계속하라, 그 밖이면 같은 형태로 재시도하지 말고 승인이 필요 없게 고치거나 미완으로
  남기되 이유를 기록하고 계속하라, 삭제라면 정확한 절대 경로를 쓰라. 두 plugin은 같은 요청에 같은
  답을 낸다(SHALL).
- plan mode 진입은 **진입 전에 deny**해야 한다(MUST) — 진입은 승인 없이 통과하지만 이탈(plan
  승인)은 사람만 풀 수 있어, 진입하면 session이 plan mode에 갇힌다.
- MCP elicitation은 **decline**해야 한다(MUST).

plugin은 어떤 요청도 allow해서는 안 된다(MUST NOT) — 무인 계약은 승인을 대신하지 않고 기다림만
없앤다.

#### Scenario: critical-path 삭제

- **WHEN** 무인 session이 bypass 모드에서 `rmdir /some-top-level-dir`를 시도하면
- **THEN** countdown dialog 없이 즉시 거부되고, 에이전트는 정확한 절대 경로 규칙을 담은 사유를
  받는다

#### Scenario: 질문

- **WHEN** 무인 session의 main이 `AskUserQuestion`을 호출하면
- **THEN** 질문 창이 뜨지 않고, 에이전트는 스스로 결정해 가정을 밝히고 계속하라는 사유를 받는다

#### Scenario: plan mode

- **WHEN** 무인 session의 main이 `EnterPlanMode`를 호출하면
- **THEN** 호출이 거부되고 session의 permission mode는 그대로다

### Requirement: Stall record

ploop 무인 session에서 plugin이 답하지 못한 dialog가 사람을 기다리기 시작하면 — 권한 prompt·
elicitation이 약 6초 대기했거나, usage-limit 자동 재개가 사람을 기다리거나 포기하면 — ploop은
그 사실(종류·harness message·시각)을 loop.log에 `Stall` entry로 남겨야 한다(SHALL). 기록은
대기를 풀지 않으며, 사후 판독(docent·advisor)의 증거다.

#### Scenario: 답하지 못한 prompt

- **WHEN** 무인 loop session에서 sandbox network 요청 prompt가 6초 넘게 대기하면
- **THEN** loop.log에 `[[ Stall - <시각> ]]` entry가 그 종류와 message로 추가된다

### Requirement: No human-participation path

ploop의 anchor 정의(define-mission·define-purpose)는 사람 개입 허용 여부를 묻거나 anchor에
무인 선언을 넣지 않아야 한다(MUST NOT) — 무인은 ploop의 전제다. launch rules는 사용자가
부재하며 결정은 에이전트가 스스로 내린다는 것을 세워야 한다(SHALL). anchor 정의가 끝나면 사용자에게
bypassPermissions로 연 별도 session에서 launch하라고 안내해야 한다(SHALL).

#### Scenario: mission 정의

- **WHEN** 사용자가 `/ploop:define-mission`으로 anchor를 작성하면
- **THEN** 무인 운행 여부를 묻는 단계가 없고, 핸드오프 안내에 bypassPermissions session이 있다
