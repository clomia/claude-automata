# claude-automata

[English](README.md) | 한국어

클로드 코드의 자율성을 증폭시키는 플러그인들

## Getting Started

**[`uv`가 필요합니다. 없다면 먼저 설치하세요.](https://docs.astral.sh/uv/getting-started/installation/)**

이 레포지토리를 마켓플레이스에 추가하세요

```
claude plugin marketplace add clomia/claude-automata
```

# Ploop - Overclock Loop

> Install: `claude plugin install ploop@claude-automata`  
> Update: `claude plugin update ploop@claude-automata`  

ploop은 며칠씩 걸리는 장기 작업을 위해 설계된 루프입니다.

- 독립된 advisor가 사용자를 대신하여 진행 상황을 관리합니다.
  - advisor는 메인 에이전트가 놓친 부분을 찾아줍니다.
- 여러번의 auto compaction에도 맥락을 잃지 않습니다.
  - compaction이 발생하면 미션이 재주입됩니다.
  - advisor가 전체 맥락을 파일로 관리합니다.
- 별도 세션을 만들지 않고 정식 서브에이전트 경로만 사용합니다 — 구독 요금제에 안전합니다.

### 사용 방법

> Auto-Compact가 True로 설정되어 있어야 합니다.

1. 미션을 작성하세요. `/ploop:define-mission`을 활용하세요.
2. 새로운 세션에서 `/ploop:launch [미션 내용]`을 실행하세요.
   루프는 Stop hook의 error 동작을 활용합니다 — 에이전트가 멈출 때마다 훅이 정지를 막고 advisor 호출을 지시합니다.
3. 루프는 advisor가 더 이상 조언할 것이 없다고 판단하면 끝납니다.
   직접 끝내려면 `/ploop:stop`을 실행하세요 — 유일한 수동 중단 방법입니다 (턴이 돌고 있으면 ESC로 끊은 뒤 실행).
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
