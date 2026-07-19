# claude-automata

[English](https://github.com/clomia/claude-automata/blob/main/README.md) | 한국어

Claude Code의 자율성을 증폭시키는 plugin들

## Getting Started

**[`uv`가 필요합니다. 없다면 먼저 설치하세요.](https://docs.astral.sh/uv/getting-started/installation/)**
**POSIX 환경(macOS / Linux / WSL)에서 동작합니다.**

project root에서 한 번에 setup하세요 — settings 전제조건, marketplace·plugin 등록, 외부 CLI 의존성(gh · Node.js · repomix)까지:

```
uvx claude-automata init
```

재실행해도 안전합니다(idempotent). 최신 version을 강제하려면 `uvx claude-automata@latest init`을 사용하세요.

plugin 등록 없이 marketplace만 추가하려면:

```
claude plugin marketplace add clomia/claude-automata
```

# Ploop - Advisor Loop

> Install: `claude plugin install ploop@claude-automata`  
> Update: `claude plugin update ploop@claude-automata`  

ploop은 며칠씩 걸리는 장기 작업을 위해 설계된 advisor loop입니다.

- 독립된 advisor가 사용자를 대신하여 진행 상황을 관리합니다.
  - advisor는 main agent가 놓친 부분을 찾아줍니다.
- main agent는 orchestrator입니다 — 작업을 agent들에 위임하고 지휘합니다.
- 여러번의 auto compaction에도 맥락을 잃지 않습니다.
  - compaction이 발생하면 anchor가 재주입됩니다.
  - advisor가 전체 맥락을 파일로 관리합니다.
- 별도 session을 만들지 않고 정식 subagent 경로만 사용합니다 — 구독 요금제에 안전합니다.

**anchor**는 loop를 붙들어 매는 기준 파일입니다. 두 종류가 있습니다.

- **Mission** (목표) — 요구사항을 받아서 처리하고, 목표를 모두 달성하면 끝납니다. `/ploop:define-mission`으로 작성하세요.
- **Purpose** (목적) — 요구사항을 만들며 계속 나아가고, 정해진 끝이 없습니다. `/ploop:define-purpose`로 작성하세요.

### 사용 방법

> Auto-Compact가 True로 설정되어 있어야 합니다.  
> 무인 운용에는 `askUserQuestionTimeout` 설정을 권장합니다 — 응답 없는 질문에서 loop가 영구 대기하지 않습니다.

1. anchor를 작성하세요. 완료 조건이 명확한 목표면 `/ploop:define-mission`, 지속적으로 나아갈 방향이면 `/ploop:define-purpose`를 활용하세요.
2. 새로운 session에서 `/ploop:launch [anchor 내용]`을 실행하세요.
   loop는 Stop hook의 error 동작을 활용합니다 — agent가 멈출 때마다 hook이 정지를 막고 advisor 호출을 지시합니다.
3. loop는 advisor가 더 이상 조언할 것이 없다고 판단하면 자동으로 끝나며, 이때 agent가 log를 읽어 전체 round를 요약합니다.
   잠시 멈추려면 `/ploop:off`, 멈춘 지점부터 다시 이어가려면 `/ploop:on`을 실행하세요 (turn이 돌고 있으면 ESC로 끊은 뒤 실행).
   `off`는 조용히 loop를 멈추고 상태를 보존하며, `on`은 그 상태에서 loop를 재개합니다.
   `on`은 실수로 누른 ESC·API error·구독 session limit 등으로 멈춘 장기 loop까지 깨우는 범용 wake button입니다 — advisor가 스스로 loop를 종료한 경우만 빼고 언제나 정상 재개합니다.
   그 밖의 어떤 것도 — 중간 지시, 질문 응답, background 작업 알림, ESC 자체 — loop를 멈추지 않습니다.
4. 진행 상황이 궁금하면 **같은 directory의 별도 session**에서 `/ploop:docent`를 실행하세요.
   docent는 loop의 기록(anchor·round log·advice history·worker 기록)을 읽어 질문에 답하는 read-only session입니다 — loop에는 어떤 영향도 주지 않습니다.
   질의를 loop session에 던지면 지휘 context가 오염되므로, 질문은 docent에게 하세요 (mobile에서는 docent session에 remote-control로 접속).
   지시·중단 같은 개입은 반대로 docent가 아니라 loop session에 직접 하세요.

# Refine

> Install: `claude plugin install refine@claude-automata`  
> Update: `claude plugin update refine@claude-automata`  

refine은 repository에 쌓이는 부채를 없애는 대규모 workflow 모음입니다.

세 skill은 같은 방식으로 동작합니다 — 영역을 나눠 병렬 분석하고, 발견을 교차검증 회의로 합의시키고, ROI가 높은 계획만 실행합니다. 한 번의 실행이 수 시간(3–12시간) 걸리는 heavyweight workflow입니다.

- `/refine:code [영역]` — 코드 architecture 최적화. antipattern을 합의로 걸러내고 최고 ROI refactoring만 적용합니다.
- `/refine:docs [영역]` — 문서 architecture 최적화. 실행시킬 수 없는 text(markdown, openspec 같은 문서 system, 주석·docstring)의 모든 주장을 코드와 대조해 바로잡습니다. 정합은 전제이고, 중복 수렴·죽은 문서 삭제·최소 문서가 최적해의 형태입니다. 코드는 수정하지 않습니다 — 코드 결함은 보고합니다.
- `/refine:integrity [영역]` — 무결성 경계 최적화. 기존 경계(type·불변식·error 정의·test)가 포함하지 못하는 도달 가능한 상태를 찾아 **"이걸 error로 정의할 것인가?"** 부터 파고들어 경계 안으로 흡수하고, 정의된 behavior를 test로, 그 이유를 문서·주석으로 고정합니다.

영역을 비우면 codebase 전체가 대상입니다. 진행 상황은 `/workflows`에서 확인할 수 있습니다.

# tx - Git Transaction Workflow

> Install: `claude plugin install tx@claude-automata`  
> Update: `claude plugin update tx@claude-automata`  

tx는 변경을 transaction 단위로 관리하는 Git workflow입니다.

- transaction은 **무결성 경계**입니다 — open부터 close까지가 하나로 묶이고, 무결성이 검증되어야만 닫힙니다.
- 전 과정이 tx 내장 skill로 돕니다: `/tx:open`이 base branch에서 `tx-*` 분기를 열고 seed를 심으며, `tx:plan`·`tx:apply`·`tx:verify`가 변경을 이끌고, `/tx:close`가 docs gate와 CI 통과 후 base로 squash merge합니다. 그 사이의 base branch는 guard hook들이 지킵니다.

사전 요구: uv, Node.js >= 20 (pin version [OpenSpec](https://github.com/Fission-AI/OpenSpec) CLI를 npx로 구동 — 설치할 것 없음), GitHub CLI(`gh`).

### 사용 방법

```
/tx:open  [변경 설명]   # base에서 tx-* 분기 + seed + 경로 선택
...작업...              # tx:plan → tx:apply → tx:verify
/tx:close               # verify·archive·docs gate 후 base로 squash merge
```

transaction 정의·guard hook·base branch 해석·sync 일시정지 등 자세한 내용은 [plugin README](https://github.com/clomia/claude-automata/blob/main/plugins/tx/README.md)를 참고하세요.

# version-up-alert

> 별도 설치가 필요 없습니다 — 모든 claude-automata plugin이 의존성으로 함께 설치합니다.

설치된 claude-automata plugin에 새 version이 배포되면 session 시작 시 한 줄로 알립니다.

- 설치된 version과 이 repository가 배포한 version을 비교해, 뒤처진 plugin을 모두 담은 알림 하나를 띄웁니다. update는 `/plugin`에서 하세요.
- 알림만 합니다 — 실행 중인 session 밑에서 plugin을 갈아끼우지 않습니다. 적용 시점은 사용자가 정합니다.
