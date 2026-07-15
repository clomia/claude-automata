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
   `on`은 실수로 누른 ESC·API 에러·구독 세션 리밋 등으로 멈춘 장기 루프까지 되살리는 유일한 수단입니다 — advisor가 스스로 루프를 종료한 경우만 빼고 언제나 정상 재개합니다.
   그 밖의 어떤 것도 — 중간 지시, 질문 응답, 백그라운드 작업 알림, ESC 자체 — 루프를 멈추지 않습니다.

# Refine Architecture

> Install: `claude plugin install refine-architecture@claude-automata`  
> Update: `claude plugin update refine-architecture@claude-automata`  

refine-architecture는 코드 아키텍처를 최적화하는 대규모 워크플로우입니다.

사용 방법:
```
/refine-architecture:refine-architecture [집중 분석 영역]
```

집중 분석 영역을 비우면 코드베이스 전체가 대상입니다.  
진행 상황은 `/workflows`에서 확인할 수 있습니다.

# txgit - Git Transaction Workflow

> Install: `claude plugin install txgit@claude-automata`  
> Update: `claude plugin update txgit@claude-automata`  

txgit은 변경을 트랜잭션 단위로 관리하는 Git 워크플로우입니다.

- 트랜잭션은 작업 단위가 아니라 **무결성 경계**입니다. tx-open부터 tx-close까지가 하나로 묶입니다.
- `/txgit:tx-open`으로 base 브랜치에서 `tx-*` 분기를 열고 [OpenSpec](https://github.com/Fission-AI/OpenSpec)으로 변경을 계획합니다.
- `/txgit:tx-close`로 OpenSpec 변경을 아카이브하고 CI 통과 후 base 브랜치로 squash merge합니다.
- 세 개의 가드 훅이 보호 브랜치 편집·오래 열린 트랜잭션·동기화 이탈을 막습니다.

사전 요구: uv, [OpenSpec](https://github.com/Fission-AI/OpenSpec) (설치 후 `openspec init` 완료), GitHub CLI(`gh`).

### 사용 방법

```
/txgit:tx-open  [변경 설명]   # base에서 tx-* 분기 생성 + OpenSpec 계획
...작업...                    # 구현 (예: /opsx:apply)
/txgit:tx-close               # 변경 아카이브 후 base로 squash merge
```

트랜잭션 정의·가드 훅·base 브랜치 설정·sync 일시정지 등 자세한 내용은 [플러그인 README](plugins/txgit/README.md)를 참고하세요.
