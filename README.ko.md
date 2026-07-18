# claude-automata

[English](README.md) | 한국어

클로드 코드의 자율성을 증폭시키는 플러그인들

## Getting Started

**[`uv`가 필요합니다. 없다면 먼저 설치하세요.](https://docs.astral.sh/uv/getting-started/installation/)**

이 레포지토리를 마켓플레이스에 추가하세요

```
claude plugin marketplace add clomia/claude-automata
```

# Ploop - Advisor Loop

> Install: `claude plugin install ploop@claude-automata`  
> Update: `claude plugin update ploop@claude-automata`  

ploop은 며칠씩 걸리는 장기 작업을 위해 설계된 advisor loop입니다.

- 독립된 advisor가 사용자를 대신하여 진행 상황을 관리합니다.
  - advisor는 메인 에이전트가 놓친 부분을 찾아줍니다.
- 메인 에이전트는 orchestrator입니다 — 작업을 에이전트들에 위임하고 전략·검증·응고를 소유합니다.
- 여러번의 auto compaction에도 맥락을 잃지 않습니다.
  - compaction이 발생하면 anchor가 재주입됩니다.
  - advisor가 전체 맥락을 파일로 관리합니다.
- 별도 세션을 만들지 않고 정식 서브에이전트 경로만 사용합니다 — 구독 요금제에 안전합니다.

**anchor**는 루프를 붙들어 매는 기준 파일입니다. 두 종류가 있습니다.

- **Mission** (목표) — 요구사항을 받아서 처리하고, 목표를 모두 달성하면 끝납니다. `/ploop:define-mission`으로 작성하세요.
- **Purpose** (목적) — 요구사항을 만들며 계속 나아가고, 정해진 끝이 없습니다. `/ploop:define-purpose`로 작성하세요.

### 사용 방법

> Auto-Compact가 True로 설정되어 있어야 합니다.

1. anchor를 작성하세요. 명백한 목표면 `/ploop:define-mission`, 지속적으로 나아갈 방향이면 `/ploop:define-purpose`를 활용하세요.
2. 새로운 세션에서 `/ploop:launch [anchor 내용]`을 실행하세요.
   루프는 Stop hook의 error 동작을 활용합니다 — 에이전트가 멈출 때마다 훅이 정지를 막고 advisor 호출을 지시합니다.
3. 루프는 advisor가 더 이상 조언할 것이 없다고 판단하면 자동으로 끝나며, 이때 에이전트가 로그를 읽어 전체 라운드를 요약합니다.
   잠시 멈추려면 `/ploop:off`, 멈춘 지점부터 다시 이어가려면 `/ploop:on`을 실행하세요 (턴이 돌고 있으면 ESC로 끊은 뒤 실행).
   `off`는 조용히 루프를 멈추고 상태를 보존하며, `on`은 그 상태에서 루프를 재개합니다.
   `on`은 실수로 누른 ESC·API 에러·구독 세션 리밋 등으로 멈춘 장기 루프까지 깨우는 범용 wake 버튼입니다 — advisor가 스스로 루프를 종료한 경우만 빼고 언제나 정상 재개합니다.
   그 밖의 어떤 것도 — 중간 지시, 질문 응답, 백그라운드 작업 알림, ESC 자체 — 루프를 멈추지 않습니다.

# Refine

> Install: `claude plugin install refine@claude-automata`  
> Update: `claude plugin update refine@claude-automata`  

refine은 레포지토리에 쌓이는 부채를 없애는 대규모 워크플로우 모음입니다.

세 스킬은 같은 방식으로 동작합니다 — 영역을 나눠 병렬 분석하고, 발견을 교차검증 회의로 합의시키고, ROI가 높은 계획만 실행합니다. 한 번의 실행이 수 시간(3–12시간) 걸리는 heavyweight 워크플로우입니다.

- `/refine:code [영역]` — 코드 아키텍처 최적화. 안티패턴을 합의로 걸러내고 최고 ROI 리팩토링만 적용합니다. 최적해는 정상동작을 전제하므로, 탐색이 드러낸 결함의 수리와 변경이 낡게 만든 문서의 정합을 포함합니다.
- `/refine:docs [영역]` — 문서 아키텍처 최적화. 실행시킬 수 없는 텍스트(마크다운, openspec 같은 문서 시스템, 주석·docstring)의 모든 주장을 코드와 대조해 바로잡습니다. 정합은 전제이고, 중복 수렴·죽은 문서 삭제·최소 문서가 최적해의 형태입니다. 코드는 수정하지 않습니다 — 코드 결함은 보고합니다.
- `/refine:integrity [영역]` — 무결성 경계 최적화. 기존 경계(타입·불변식·에러 정의·테스트)가 포함하지 못하는 도달 가능한 상태를 찾아 **"이걸 에러로 정의할 것인가?"** 부터 파고들어 경계 안으로 흡수하고, 정의된 behavior를 테스트로, 그 이유를 문서·주석으로 고정합니다.

영역을 비우면 코드베이스 전체가 대상입니다. 진행 상황은 `/workflows`에서 확인할 수 있습니다.

# tx - Git Transaction Workflow

> Install: `claude plugin install tx@claude-automata`  
> Update: `claude plugin update tx@claude-automata`  

tx는 변경을 트랜잭션 단위로 관리하는 Git 워크플로우입니다.

- 트랜잭션은 작업 단위가 아니라 **무결성 경계**입니다. open부터 close까지가 하나로 묶입니다.
- base 브랜치는 **레포지토리의 GitHub 기본 브랜치**입니다. 설정할 것이 없습니다 — `origin/HEAD`에서 자동으로 읽습니다.
- `/tx:open`이 base에서 `tx-*` 분기를 열고, 필요하면 씨앗(OpenSpec 스캐폴드 + CI workflow)을 심은 뒤 변경을 라우팅합니다.
- 계획·구현은 tx 내장 스킬이 수행합니다 — `tx:plan`(OpenSpec 아티팩트), `tx:apply`(구현), 그리고 깨끗한 컨텍스트에서 구현을 실측 대조하는 독립 `tx:verify` 스테이지.
- `/tx:close`가 변경을 아카이브하고 docs 게이트와 CI 통과 후 base로 squash merge합니다.
- 네 개의 가드 훅이 보호 브랜치 편집과 base 커밋을 막고, 오래 열린 트랜잭션을 표면화하며, 동기화 이탈을 막습니다.

사전 요구: uv, Node.js >= 20 (핀 버전 [OpenSpec](https://github.com/Fission-AI/OpenSpec) CLI를 npx로 구동 — 설치할 것 없음), GitHub CLI(`gh`).

### 사용 방법

```
/tx:open  [변경 설명]   # base에서 tx-* 분기 + 씨앗 + 경로 선택
...작업...              # tx:plan → tx:apply → tx:verify
/tx:close               # verify·archive·docs 게이트 후 base로 squash merge
```

트랜잭션 정의·가드 훅·base 브랜치 해석·sync 일시정지 등 자세한 내용은 [플러그인 README](plugins/tx/README.md)를 참고하세요.

# version-up-alert

> 별도 설치가 필요 없습니다 — 모든 claude-automata 플러그인이 의존성으로 함께 설치합니다.

설치된 claude-automata 플러그인에 새 버전이 배포되면 세션 시작 시 한 줄로 알립니다.

- 설치된 버전과 이 레포지토리가 배포한 버전을 비교해, 뒤처진 플러그인을 모두 담은 알림 하나를 띄웁니다. 업데이트는 `/plugin`에서 하세요.
- 알림만 합니다 — 실행 중인 세션 밑에서 플러그인을 갈아끼우지 않습니다. 적용 시점은 사용자가 정합니다.
