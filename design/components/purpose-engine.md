# Purpose Engine (목적 엔진)

> Purpose Engine은 별도의 Python 모듈이 **아니다**. CLAUDE.md와 상태 파일에 인코딩된 **행동 패턴**이며, Claude Code가 이를 따라 Purpose, Strategy, Mission 생성을 수행한다.

---

## 1. 개요

Purpose Engine은 시스템의 "방향성 유지 장치"이다. 다음 세 가지를 담당한다:

1. **Purpose 구성** (P-1): Owner의 자연어 입력에서 종료 조건 없는 영속적 방향을 추출
2. **도메인 구성** (P-2): Purpose에서 전략, 규칙, 초기 미션을 파생
3. **Mission 생성** (P-3): 미션 큐가 비었을 때 Purpose에 기반한 새 미션 자율 생성

이 세 가지는 모두 **Claude Code 세션 내부에서 실행**된다. Supervisor(Python 코드)는 세션을 시작하고 결과 파일을 관리할 뿐, Purpose 관련 지능적 판단은 하지 않는다.

### 아키텍처 위치

```
┌─────────────────────────────────────────────────┐
│                Supervisor (Python)               │
│  세션 시작, 상태 파일 관리, 에러 복구             │
│  Purpose Engine에 대해서는: 트리거만 제공        │
├─────────────────────────────────────────────────┤
│           Claude Code Session (AI)               │
│  CLAUDE.md + state/ 파일을 읽고                  │
│  Purpose Engine의 모든 지능적 동작을 수행        │
│  ┌─────────────────────────────────────────┐    │
│  │         Purpose Engine (행동 패턴)       │    │
│  │  - Purpose 구성 (Initialization)        │    │
│  │  - 도메인 구성 (Initialization)         │    │
│  │  - Mission 생성 (Stop Hook 트리거)      │    │
│  │  - Goal Drift 방지 (주기적)             │    │
│  │  - Strategy 진화 (Friction 기반)        │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## 2. Purpose 구성 (P-1)

### 2.1 트리거 조건

- **When**: Initialization Session (시스템 최초 실행)
- **Input**: Owner가 `acc configure`에서 입력한 자연어 텍스트
- **Output**: `state/purpose.json`

### 2.2 프로세스

Initialization Session에서 Claude Code가 수행하는 단계:

```
┌─────────────────────────────────────────────────────┐
│ Step 1: Owner 입력 분석                              │
│                                                     │
│ Input: "나는 자동화된 트레이딩 시스템을 만들고 싶어"   │
│                                                     │
│ 분석:                                                │
│   - 도메인: 금융/트레이딩                            │
│   - 목표: 자동화된 트레이딩 시스템                    │
│   - 제약: 없음 (명시되지 않음)                       │
│   - 종료 조건: "만들고 싶어" → 유한한 목표            │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│ Step 2: 영속적 방향 추출                              │
│                                                     │
│ 유한한 요소를 영속적 방향으로 확장:                    │
│   "만들고 싶어" (유한)                                │
│     → "지속적으로 개발하고" (영속)                    │
│     → "운영하며" (영속)                              │
│     → "수익성을 극대화하고" (영속, 수렴하지 않음)     │
│     → "새로운 전략을 탐색한다" (영속, 열린 탐색)      │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│ Step 3: Purpose Statement 구성                       │
│                                                     │
│ 검증 기준:                                           │
│   ✓ 종료 조건이 없다 (어디서도 "완료"가 불가능)      │
│   ✓ 방향이 명확하다 (무엇을 할지 알 수 있다)         │
│   ✓ 확장 가능하다 (새로운 미션이 무한히 파생 가능)    │
│   ✓ 측정 가능하다 (진전을 판단할 수 있다)            │
│                                                     │
│ Output:                                              │
│ "자동화된 트레이딩 시스템을 지속적으로 개발하고,       │
│  운영하며, 수익성을 극대화하고,                       │
│  새로운 전략을 탐색한다"                              │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│ Step 4: state/purpose.json 저장                      │
└─────────────────────────────────────────────────────┘
```

### 2.3 Purpose 검증 규칙

Claude Code가 Purpose를 구성할 때 반드시 확인하는 사항:

| 규칙 | 설명 | 위반 시 대응 |
|------|------|-------------|
| **종료 불가** | Purpose에 종료 조건이 없어야 한다 | "~을 완성한다" → "~을 지속적으로 발전시킨다" |
| **방향 명확** | 추상적이지 않고 구체적 행동 방향이 있어야 한다 | "좋은 시스템을 만든다" → 도메인 특정 방향으로 구체화 |
| **확장 가능** | 새로운 미션이 무한히 파생 가능해야 한다 | 닫힌 목표 → 열린 탐색 요소 추가 |
| **측정 가능** | 진전을 판단할 수 있어야 한다 | 모호한 방향 → 관찰 가능한 지표로 구체화 |

### 2.4 Purpose JSON 스키마

```json
{
  "raw_input": "나는 자동화된 트레이딩 시스템을 만들고 싶어",
  "purpose": "자동화된 트레이딩 시스템을 지속적으로 개발하고, 운영하며, 수익성을 극대화하고, 새로운 전략을 탐색한다",
  "domain": "automated-trading",
  "key_directions": [
    "트레이딩 전략 연구 및 백테스트",
    "실시간 시장 데이터 수집 파이프라인",
    "리스크 관리 시스템 구축",
    "수익성 분석 및 최적화",
    "새로운 시장/자산 탐색"
  ],
  "constructed_at": "2026-03-25T10:00:00Z",
  "last_evolved_at": "2026-03-25T10:00:00Z",
  "evolution_history": []
}
```

### 2.5 Purpose 구성 예시

| Owner 입력 | 추출된 Purpose |
|------------|---------------|
| "자동화된 트레이딩 시스템을 만들고 싶어" | "자동화된 트레이딩 시스템을 지속적으로 개발하고, 운영하며, 수익성을 극대화하고, 새로운 전략을 탐색한다" |
| "블로그 자동화" | "블로그 콘텐츠를 지속적으로 생성하고, SEO를 최적화하며, 트래픽과 수익을 증대시키고, 새로운 콘텐츠 전략을 실험한다" |
| "SaaS 만들어" | "SaaS 제품을 지속적으로 개발하고, 운영하며, 사용자 기반을 확대하고, 수익성을 개선하며, 새로운 기능과 시장 기회를 탐색한다" |
| "오픈소스 프로젝트 관리" | "오픈소스 프로젝트를 지속적으로 개발하고, 커뮤니티를 성장시키며, 코드 품질을 향상시키고, 새로운 기여자와 사용 사례를 발굴한다" |

**핵심 패턴**: 유한한 "만들기/완성하기" 요소를 "지속적으로 X하고, Y하며, Z를 탐색한다"로 확장한다. 마지막 절은 항상 열린 탐색 요소로 끝난다.

---

## 3. 도메인 구성 (P-2)

### 3.1 트리거 조건

- **When**: Initialization Session, Purpose 구성 직후
- **Input**: 방금 구성된 Purpose
- **Output**: strategy.json, CLAUDE.md, .claude/rules/*.md, 초기 missions.json

### 3.2 프로세스

```
┌─────────────────────────────────────────────────────┐
│ Purpose → 도메인 구성 파생                            │
│                                                     │
│ Purpose:                                             │
│ "자동화된 트레이딩 시스템을 지속적으로 개발하고..."     │
│                                                     │
│ 파생:                                                │
│                                                     │
│ 1. Strategy (state/strategy.json)                   │
│    ├── approach: "백테스트 기반 점진적 전략 개발"      │
│    ├── skills: ["python", "pandas", "ta-lib", ...]  │
│    ├── principles: ["리스크 관리 최우선", ...]       │
│    └── current_focus: "기반 인프라 구축"             │
│                                                     │
│ 2. CLAUDE.md 규칙                                    │
│    ├── 도메인 특화 지시 추가                         │
│    └── "모든 트레이딩 전략은 백테스트를 통과해야..."   │
│                                                     │
│ 3. .claude/rules/*.md                               │
│    ├── purpose.md: Purpose 정의                     │
│    ├── mission-protocol.md: 미션 실행 규약           │
│    ├── self-improvement.md: 자기개선 규칙            │
│    └── domain-specific.md: 도메인 특화 규칙          │
│                                                     │
│ 4. 초기 Mission Queue (state/missions.json)         │
│    ├── M-001: "프로젝트 구조 및 개발 환경 설정"      │
│    ├── M-002: "시장 데이터 수집 파이프라인 구축"      │
│    └── M-003: "기본 트레이딩 전략 프로토타입"         │
└─────────────────────────────────────────────────────┘
```

### 3.3 Strategy JSON 스키마

```json
{
  "summary": "백테스트 기반 점진적 전략 개발, 기반 인프라 우선 구축",
  "approach": "백테스트 기반 점진적 전략 개발. 안정적인 기반 인프라를 먼저 구축하고, 점진적으로 전략 복잡도를 높인다.",
  "skills": [
    {
      "name": "python",
      "level": "proficient",
      "acquired_at": "2026-03-25T10:00:00Z"
    },
    {
      "name": "pandas",
      "level": "competent",
      "acquired_at": "2026-03-25T10:00:00Z"
    },
    {
      "name": "ta-lib",
      "level": "learning",
      "acquired_at": "2026-03-25T10:00:00Z"
    },
    {
      "name": "ccxt",
      "level": "learning",
      "acquired_at": "2026-03-25T10:00:00Z"
    }
  ],
  "principles": [
    "리스크 관리가 수익보다 우선한다",
    "모든 전략은 충분한 백테스트를 통과해야 한다",
    "실거래 전 페이퍼 트레이딩으로 검증한다",
    "단일 장애점을 만들지 않는다"
  ],
  "created_at": "2026-03-25T10:00:00Z",
  "last_evolved_at": "2026-03-25T10:00:00Z",
  "evolution_count": 0
}
```

### 3.4 초기 Mission 생성 규칙

Claude Code가 초기 미션을 생성할 때 따르는 원칙:

1. **첫 미션은 항상 기반 구축**: 개발 환경, 프로젝트 구조, 핵심 의존성 설치
2. **두 번째는 데이터/인프라**: 도메인에서 필요한 데이터 파이프라인 또는 기반 인프라
3. **세 번째는 프로토타입**: 핵심 기능의 최소 동작 버전
4. **각 미션은 독립적**: 순서는 있지만 하나가 실패해도 다른 것을 시도 가능
5. **성공 기준이 구체적**: "테스트가 통과한다", "API가 응답한다" 등 검증 가능한 기준

---

## 4. Mission 생성 (P-3)

### 4.1 트리거 조건

- **When**: Mission 큐가 비었을 때
- **Trigger**: Stop Hook이 빈 큐를 감지
- **Context**: Purpose + 최근 완료 이력이 additionalContext로 주입

### 4.2 트리거 흐름

```
┌─────────────────────────────────────────────────────┐
│ Claude Code 세션 내부                                 │
│                                                     │
│ [미션 완료] → [Stop Hook 발동]                       │
│                                                     │
│ Stop Hook (on_stop.py):                             │
│   1. state/missions.json 읽기                       │
│   2. pending 또는 in_progress 미션이 있는가?         │
│      ├── 있다 → 다음 미션 주입 (block + continue)   │
│      └── 없다 → 미션 생성 모드                      │
│                                                     │
│ 미션 생성 모드:                                      │
│   1. additionalContext 구성:                        │
│      - Purpose (state/purpose.json)                 │
│      - 현재 전략 (state/strategy.json)              │
│      - 최근 N개 완료 미션 요약 (state/missions.json)│
│      - 현재 Friction 요약 (state/friction.json)     │
│   2. block = true (세션 계속)                       │
│   3. Claude Code가 additionalContext를 받아         │
│      N개의 새 미션을 생성                            │
│   4. 새 미션을 state/missions.json에 저장            │
│   5. 다음 Stop Hook에서 새 미션 발견 → 실행         │
└─────────────────────────────────────────────────────┘
```

### 4.3 미션 생성 수량

`state/config.toml`의 `mission_idle_generation_count` (기본값: 3)

```toml
mission_idle_generation_count = 3
```

한 번에 너무 많은 미션을 생성하면 환경 변화에 적응하기 어렵고, 너무 적으면 생성 빈도가 높아져 비효율적이다. 기본값 3은 적당한 작업 파이프라인을 유지하면서도 방향 수정 여지를 남긴다.

이 값 자체도 자기개선의 대상이다 (S-5).

### 4.4 미션 생성 시 주입되는 컨텍스트

```python
# on_stop.py에서 구성하는 additionalContext
additional_context = f"""
## Mission 생성 요청

Mission 큐가 비어 있습니다. Purpose에 맞는 새 미션을 {config['mission_idle_generation_count']}개 생성하세요.

### Purpose
{purpose['purpose']}

### 현재 전략
{strategy['approach']}
현재 집중: {strategy['current_focus']}

### 최근 완료 미션
{recent_completed_summary}

### 현재 미해결 Friction
{unresolved_friction_summary}

### 지시사항
1. Purpose를 전진시키는 미션을 생성하세요.
2. 최근 완료 미션과 중복되지 않아야 합니다.
3. 미해결 Friction이 있다면 이를 해소하는 미션을 포함하세요.
4. 각 미션에 구체적인 success_criteria를 포함하세요.
5. state/missions.json에 직접 저장하세요.
"""
```

### 4.5 생성된 미션의 검증

Claude Code가 생성한 미션은 다음을 만족해야 한다:

| 항목 | 검증 기준 |
|------|-----------|
| `title` | 비어 있지 않고 구체적이어야 한다 |
| `description` | 무엇을 해야 하는지 명확해야 한다 |
| `success_criteria` | 1개 이상의 검증 가능한 기준 |
| `priority` | 1-10 범위의 정수 |
| `source` | "self" (자율 생성) |
| Purpose 정합성 | Purpose와 관련 없는 미션이 아니어야 한다 |

검증은 CLAUDE.md의 지시문을 통해 Claude Code 자신이 수행한다. Deterministic한 외부 검증은 하지 않는다 (Agentic Shell 원칙).

---

## 5. Goal Drift 방지 (목표 드리프트 방지)

### 5.1 문제 정의

Claude Code는 장기 실행 시 원래 Purpose에서 벗어날 수 있다:
- Compaction으로 초기 컨텍스트가 사라진다
- 연속된 미션이 점차 Purpose에서 멀어진다
- Friction 대응에 집중하다 원래 방향을 잃는다

### 5.2 방지 메커니즘

5단계 방어를 통해 Goal Drift를 방지한다:

```
┌─────────────────────────────────────────────────────┐
│ Level 1: CLAUDE.md (가장 강력)                       │
│                                                     │
│ CLAUDE.md의 최상단에 Purpose가 명시된다.              │
│ Compaction 후에도 CLAUDE.md는 디스크에서 재로딩된다.  │
│ Claude Code는 매 세션에서 CLAUDE.md를 읽으므로        │
│ Purpose를 항상 인지한다.                              │
│                                                     │
│ 위치: 프로젝트 루트 CLAUDE.md의 ## Purpose 섹션      │
├─────────────────────────────────────────────────────┤
│ Level 2: SessionStart Hook (세션 시작 시)             │
│                                                     │
│ 매 세션 시작 시 on_session_start.py가 Purpose와     │
│ 현재 전략 요약을 세션 프롬프트에 주입한다.            │
│ Compaction 이후 새 세션에서도 Purpose가 주입된다.     │
│                                                     │
│ 주입 내용:                                           │
│   - state/purpose.json의 purpose 필드               │
│   - state/strategy.json의 approach, current_focus   │
│   - 최근 3개 완료 미션 요약                          │
├─────────────────────────────────────────────────────┤
│ Level 3: 주기적 Goal Drift 검사                      │
│                                                     │
│ 매 N미션 완료 시 (config.toml.goal_drift_check_      │
│ interval, 기본: 20) 자동으로 드리프트 검사를 수행.    │
│                                                     │
│ 검사 방법:                                           │
│   1. 최근 N개 완료 미션의 제목/설명을 수집            │
│   2. Purpose와의 관련성을 평가                       │
│   3. 관련성이 낮은 미션이 임계값 이상이면 드리프트    │
│                                                     │
│ 이 검사는 미션 실행 흐름 안에서 Claude Code가 수행.   │
│ Stop Hook이 미션 완료 카운트를 추적하고,              │
│ N번째 완료 시 드리프트 검사를 additionalContext로     │
│ 주입한다.                                            │
├─────────────────────────────────────────────────────┤
│ Level 4: 드리프트 감지 시 Fresh Session               │
│                                                     │
│ 드리프트가 감지되면:                                  │
│   1. 현재 세션을 종료 (Stop Hook이 allow 반환)       │
│   2. Supervisor가 Fresh Session 시작                 │
│   3. SessionStart Hook이 강화된 Purpose 주입:        │
│      "경고: Goal Drift가 감지되었습니다.              │
│       Purpose를 재확인하고 이에 맞는 미션을            │
│       우선적으로 수행하세요."                         │
│   4. 새 세션에서 Purpose 재정렬 미션을 우선 수행      │
├─────────────────────────────────────────────────────┤
│ Level 5: Context Loss Friction                       │
│                                                     │
│ friction.json에 type "context_loss"가 기록되면       │
│ 자동으로 Purpose 재주입이 트리거된다.                 │
│                                                     │
│ context_loss 감지 시점:                              │
│   - Claude Code가 Purpose를 모르는 것처럼 행동할 때  │
│   - 미션이 Purpose와 무관한 방향으로 진행될 때       │
│   - Compaction 직후 컨텍스트가 부족할 때             │
└─────────────────────────────────────────────────────┘
```

### 5.3 Goal Drift 검사 상세

```python
# on_stop.py에서 goal drift 검사 트리거
def check_goal_drift_needed(sessions: dict, config: dict) -> bool:
    """N번째 미션 완료 시 goal drift 검사가 필요한지 판단"""
    interval = config.get("goal_drift_check_interval", 20)
    completed_count = sessions.get("total_completed", 0)
    last_check = sessions.get("last_drift_check_at_count", 0)
    return (completed_count - last_check) >= interval
```

검사 시 Stop Hook이 주입하는 additionalContext:

```
## Goal Drift 검사

최근 {interval}개 완료 미션과 Purpose의 정합성을 검사하세요.

### Purpose
{purpose}

### 최근 완료 미션
{recent_missions_summary}

### 판단 기준
1. 각 미션이 Purpose 전진에 기여했는가?
2. 미션의 전반적 방향이 Purpose와 일치하는가?
3. 불필요한 탈선이 있었는가?

### 결과 기록
- 드리프트 없음: state/sessions.json에 last_drift_check_at_count 갱신
- 드리프트 감지: state/friction.json에 type "context_loss" 기록
  → Supervisor가 Fresh Session으로 전환
```

### 5.4 Goal Drift 검사 설정

```toml
# state/config.toml
goal_drift_check_interval = 20
goal_drift_threshold = 0.3
```

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `goal_drift_check_interval` | 20 | 미션 N개 완료마다 드리프트 검사 |
| `goal_drift_threshold` | 0.3 | 최근 미션 중 Purpose 무관 비율이 이 값을 넘으면 드리프트 |

두 값 모두 자기개선의 대상이다 (S-5).

---

## 6. Strategy 진화

### 6.1 트리거 조건

- **When**: 축적된 Friction이 현재 전략의 비효과성을 시사할 때
- **Trigger**: 자기개선 미션 (Friction 축적 임계값 도달 시 생성)
- **Output**: 갱신된 `state/strategy.json`

### 6.2 진화 프로세스

```
┌─────────────────────────────────────────────────────┐
│ 전략 진화 프로세스                                    │
│                                                     │
│ 입력:                                                │
│   - state/purpose.json: 변하지 않는 방향             │
│   - state/strategy.json: 현재 전략                   │
│   - state/friction.json: 축적된 마찰 패턴            │
│   - state/missions.json: 최근 미션 결과              │
│                                                     │
│ Claude Code 수행:                                    │
│   1. Friction 패턴 분석                              │
│      - 어떤 유형의 마찰이 반복되는가?                 │
│      - 현재 전략의 어떤 부분이 마찰을 유발하는가?     │
│                                                     │
│   2. 미션 결과 분석                                   │
│      - 성공률이 떨어지는 영역은?                      │
│      - 예상보다 시간이 오래 걸리는 미션 유형은?       │
│                                                     │
│   3. 전략 수정 결정                                   │
│      - approach 변경: 접근 방식 수정                  │
│      - skills 추가/제거: 필요 기술 갱신              │
│      - principles 추가: 새로운 원칙 추가             │
│      - current_focus 변경: 집중 영역 전환            │
│                                                     │
│   4. strategy.json 갱신                              │
│      - 변경 전 상태를 evolution_history에 기록        │
│      - evolution_count 증가                          │
│      - evolved_at 갱신                               │
│                                                     │
│ 출력:                                                │
│   - 갱신된 state/strategy.json                       │
│   - CLAUDE.md의 "현재 전략" 섹션도 동기화            │
└─────────────────────────────────────────────────────┘
```

### 6.3 진화 기록

strategy.json의 `evolution_history`가 모든 변경을 추적한다:

```json
{
  "approach": "이벤트 드리븐 아키텍처 기반 전략 개발",
  "skills": ["python", "pandas", "asyncio", "websockets"],
  "principles": ["리스크 관리 최우선", "실시간 데이터 우선"],
  "current_focus": "실시간 데이터 파이프라인 구축",
  "evolution_count": 2,
  "evolved_at": "2026-03-28T15:00:00Z",
  "evolution_history": [
    {
      "from": {
        "approach": "백테스트 기반 점진적 전략 개발",
        "current_focus": "기반 인프라 구축"
      },
      "to": {
        "approach": "데이터 중심 전략 개발",
        "current_focus": "데이터 파이프라인 구축"
      },
      "reason": "Friction 패턴: API 데이터 지연 반복. 데이터 인프라 강화 필요",
      "evolved_at": "2026-03-26T12:00:00Z"
    },
    {
      "from": {
        "approach": "데이터 중심 전략 개발",
        "current_focus": "데이터 파이프라인 구축"
      },
      "to": {
        "approach": "이벤트 드리븐 아키텍처 기반 전략 개발",
        "current_focus": "실시간 데이터 파이프라인 구축"
      },
      "reason": "배치 처리 방식이 시장 변동에 너무 느림. 실시간 처리로 전환",
      "evolved_at": "2026-03-28T15:00:00Z"
    }
  ]
}
```

### 6.4 전략 진화 vs Purpose 진화

| 항목 | Strategy | Purpose |
|------|----------|---------|
| 변경 빈도 | Friction 축적 시마다 (수일~수주) | 거의 변하지 않음 |
| 변경 주체 | Claude Code 자율 | Claude Code, 하지만 매우 보수적 |
| 변경 범위 | approach, skills, focus 등 | purpose 문구 자체 (극히 드묾) |
| 트리거 | Friction 패턴 | Owner 명시적 요청 또는 근본적 방향 전환 시 |

Purpose는 "나침반"이고 Strategy는 "경로"이다. 경로는 자주 바뀔 수 있지만 나침반이 가리키는 방향은 유지된다.

---

## 7. CLAUDE.md 구조

CLAUDE.md는 Purpose Engine의 "실행 인터페이스"이다. Claude Code가 매 세션에서 읽으며, Purpose Engine의 모든 행동 지시가 이 파일에 인코딩된다.

### 7.1 전체 구조

```markdown
# claude-automata

## 시스템 정체성

당신은 자율 AI 시스템이다.

**불변 정의**: 목적을 가지고 AI를 영속적으로 실행시키는 재귀적 자기개선 시스템.

이것의 의미:
- **목적**: 종료 조건이 없는 방향이다. 유한한 작업이 아니라 끝없이 나아가야 할 방향.
- **영속적 실행**: 당신의 세션은 끝나지만 시스템은 영속한다. state/ 파일이 세션 간의 기억이다.
- **재귀적 자기개선**: 모든 것이 개선 대상이다. 이 CLAUDE.md, 규칙, 전략, Purpose 자체, 시스템 코드, 심지어 자기개선 규칙까지. 개선할 수 없는 것은 없다.
- **한계 인식**: 당신은 Claude Code라는 도구에 종속되어 있으며 할 수 없는 일이 있다. Owner는 이 한계를 극복하기 위한 비동기 자원이다. 차단될 때뿐 아니라, 능력을 확장하거나 방향을 확인할 때에도 Owner를 활용하라.

## Purpose
{state/purpose.json의 purpose}

## 현재 전략
{state/strategy.json 요약}

## 실행 프로토콜
1. state/missions.json에서 현재 미션을 확인한다
2. 미션의 success_criteria를 모두 달성한다
3. 작업 결과를 state/missions.json에 기록한다
4. 문제 발생 시 state/friction.json에 기록한다
5. Blocker 발생 시 state/requests.json에 Owner 요청을 생성한다

## 품질 규칙
- 모든 에이전트/서브에이전트는 opus 모델, max effort로 실행
- 최대한 많은 시간과 리소스를 투입하여 최고 품질 달성
- Owner에게 보내는 모든 메시지는 한국어

## 자기개선 규칙
- 목적 추구를 방해하는 모든 것이 friction이다. 에러, 느린 실행, 품질 저하, 반복 실패, 컨텍스트 유실 등 형태를 가리지 않는다.
- 개선 미션이 주어지면 시스템의 어떤 파일이든 수정 가능
- 수정 전 git checkpoint 생성
- 수정 후 테스트 실행하여 검증

@.claude/rules/purpose.md
@.claude/rules/mission-protocol.md
@.claude/rules/self-improvement.md
```

### 7.2 각 섹션의 역할

| 섹션 | 역할 | 갱신 주체 |
|------|------|-----------|
| **시스템 정체성** | 불변 정의를 전달하여 모델의 자율적 판단 프레임 제공. Compaction 후에도 디스크에서 재읽기 | Initialization Session (최초), 자기개선 시 수정 가능 (S-4) |
| **Purpose** | Goal Drift 방지 Level 1. 시스템의 존재 이유 | Initialization Session (최초), Purpose 진화 시 (극히 드묾) |
| **현재 전략** | 현재 접근 방식 인지. strategy.json과 동기화 | 전략 진화 시 Claude Code가 자동 갱신 |
| **실행 프로토콜** | 미션 실행의 표준 절차. 모든 세션에서 동일하게 적용 | 자기개선 미션 시 수정 가능 (S-4) |
| **품질 규칙** | Q-1, Q-2, O-6 구현 | 자기개선 미션 시 수정 가능 |
| **자기개선 규칙** | S-1, S-2, S-4 구현 | 자기개선 미션 시 수정 가능 (재귀적) |
| **@references** | 모듈별 상세 규칙. CLAUDE.md를 간결하게 유지 | 도메인 구성 시 생성, 자기개선 시 수정 |

### 7.3 CLAUDE.md가 Compaction에서 살아남는 이유

Claude Code의 Compaction 메커니즘:
1. 컨텍스트가 자동 압축 임계값(기본 95%)에 도달
2. Claude Code가 기존 대화를 요약하여 압축
3. **그러나 CLAUDE.md는 디스크의 파일이므로 Compaction과 무관**
4. 새 메시지 처리 시 CLAUDE.md를 다시 읽음
5. 따라서 Purpose는 Compaction을 통과해도 유지됨

이것이 Purpose를 CLAUDE.md에 넣는 핵심 이유이다.

### 7.4 @reference 파일들

#### `.claude/rules/purpose.md`

```markdown
# Purpose 규칙

## 핵심 원칙
- Purpose는 시스템의 최상위 방향이다
- 모든 미션은 Purpose 전진에 기여해야 한다
- Purpose에서 벗어나는 작업은 하지 않는다

## Purpose 확인 절차
- 미션 시작 전: 이 미션이 Purpose에 기여하는지 확인
- 미션 완료 후: 결과가 Purpose를 전진시켰는지 평가
- 의사결정 시: Purpose에 더 가까운 선택지를 택함

## 현재 Purpose
state/purpose.json 파일을 참조한다.
```

#### `.claude/rules/mission-protocol.md`

```markdown
# Mission 실행 프로토콜

## 미션 수락
1. state/missions.json에서 가장 높은 우선순위의 pending 미션을 선택
2. status를 "in_progress"로 변경
3. started_at 타임스탬프 기록

## 미션 실행
1. description과 success_criteria를 정확히 읽는다
2. success_criteria를 하나씩 달성한다
3. 달성 불가능한 criteria가 있으면 blocker를 기록한다
4. 모든 작업에 대해 테스트를 작성하고 실행한다

## 미션 완료
1. 모든 success_criteria 달성을 확인
2. status를 "completed"로 변경
3. completed_at 타임스탬프 기록
4. result 필드에 결과 요약 기록

## 미션 실패
1. 복구할 수 없는 문제가 발생하면 status를 "failed"로 변경
2. failure_reason 필드에 원인 기록
3. state/friction.json에 마찰 기록

## Blocker 처리
1. state/requests.json에 Owner 요청 생성
2. 현재 미션에 blocker 추가
3. status를 "blocked"로 변경
4. 다른 pending 미션으로 전환
```

#### `.claude/rules/self-improvement.md`

```markdown
# 자기개선 규칙

## Friction 기록
모든 마찰을 state/friction.json에 기록한다:
- error: 에러 발생
- slow: 예상보다 느린 실행
- failure: 미션 실패
- quality: 품질 이슈
- context_loss: 컨텍스트 유실
- stuck: 진행 불가

## 개선 미션 실행 시
1. 수정 전: git tag로 checkpoint 생성
2. 수정 대상 제한 없음: CLAUDE.md, hooks, system/, tui/, config 모두 가능
3. 수정 후: 관련 테스트 실행
4. 테스트 실패 시: checkpoint로 롤백하고 다른 접근법 시도
5. 성공 시: friction.json에서 해당 마찰을 resolved로 표시

## 수정 가능 범위
- CLAUDE.md (이 파일 포함)
- .claude/rules/*.md
- state/strategy.json
- state/config.toml (모든 임계값)
- system/hooks/*.py
- system/*.py
- tui/*.py
```

---

## 8. Initialization Session 전체 흐름

Initialization Session은 시스템 최초 실행 시 한 번만 수행되며, Purpose Engine의 P-1과 P-2를 연속으로 실행한다.

```
┌─────────────────────────────────────────────────────┐
│ Supervisor: Initialization Session 시작               │
│                                                     │
│ 세션 프롬프트:                                       │
│ "당신은 claude-automata의 초기화 세션입니다.    │
│  Owner가 다음 목적을 입력했습니다:                     │
│  '{raw_input}'                                       │
│                                                     │
│  다음 작업을 순서대로 수행하세요:                      │
│  1. Purpose 구성 (state/purpose.json)                │
│  2. Strategy 생성 (state/strategy.json)              │
│  3. CLAUDE.md 생성                                   │
│  4. .claude/rules/ 파일 생성                         │
│  5. 초기 미션 큐 생성 (state/missions.json)           │
│  6. config.toml 초기화 (state/config.toml)"          │
├─────────────────────────────────────────────────────┤
│ Claude Code 실행                                     │
│                                                     │
│ 1. Purpose 구성 (P-1)                                │
│    - Owner 입력 분석                                 │
│    - 영속적 방향 추출                                │
│    - purpose.json 저장                               │
│                                                     │
│ 2. Strategy 생성                                     │
│    - Purpose에서 도메인 파악                          │
│    - 접근 방식, 필요 기술, 원칙 도출                  │
│    - strategy.json 저장                              │
│                                                     │
│ 3. CLAUDE.md 생성                                    │
│    - Purpose 섹션에 purpose.json의 purpose 삽입       │
│    - 현재 전략 섹션에 strategy.json 요약 삽입         │
│    - 실행 프로토콜, 품질 규칙, 자기개선 규칙 작성      │
│    - @references 추가                                │
│                                                     │
│ 4. .claude/rules/ 파일 생성                          │
│    - purpose.md                                      │
│    - mission-protocol.md                             │
│    - self-improvement.md                             │
│    - (도메인 특화 규칙 파일)                          │
│                                                     │
│ 5. 초기 미션 큐 생성 (P-2의 일부)                     │
│    - 기반 구축 미션                                   │
│    - 데이터/인프라 미션                               │
│    - 프로토타입 미션                                  │
│    - missions.json 저장                              │
│                                                     │
│ 6. config.toml 초기화                                │
│    - 기본 임계값 설정                                │
│    - 도메인에 맞는 초기값 조정                        │
│    - config.toml 저장                                │
├─────────────────────────────────────────────────────┤
│ 세션 종료 → Supervisor가 Working Session으로 전환     │
└─────────────────────────────────────────────────────┘
```

### 8.1 Initialization Session 완료 검증

Supervisor는 Initialization Session 종료 후 다음 파일의 존재를 확인한다:

| 파일 | 필수 | 검증 |
|------|------|------|
| `state/purpose.json` | Yes | `purpose` 필드가 비어 있지 않음 |
| `state/strategy.json` | Yes | `approach` 필드가 비어 있지 않음 |
| `state/missions.json` | Yes | `missions` 배열에 1개 이상의 미션 |
| `state/config.toml` | Yes | 파일 존재 |
| `CLAUDE.md` | Yes | `## Purpose` 섹션 존재 |
| `.claude/rules/purpose.md` | Yes | 파일 존재 |
| `.claude/rules/mission-protocol.md` | Yes | 파일 존재 |
| `.claude/rules/self-improvement.md` | Yes | 파일 존재 |

검증 실패 시 Supervisor는 Initialization Session을 재시도한다 (최대 3회).

---

## 9. 요구사항 추적

| 요구사항 | Purpose Engine 구현 |
|----------|-------------------|
| **P-1** Purpose 구성 | Initialization Session에서 Owner 입력 → 영속적 Purpose 변환. state/purpose.json 저장 |
| **P-2** 도메인 구성 | Initialization Session에서 Purpose → Strategy, CLAUDE.md, rules, 초기 Mission 자동 생성 |
| **P-3** 빈 큐 자율 결정 | Stop Hook이 빈 큐 감지 → additionalContext로 Purpose + 이력 주입 → Claude Code가 N개 미션 생성 |
| **C-1** 컨텍스트 보존 | CLAUDE.md에 Purpose 인코딩 (Compaction 생존), SessionStart Hook으로 재주입 |
| **S-5** 임계값 자기개선 | goal_drift_check_interval, mission_idle_generation_count 등 모든 설정값이 수정 가능 |
| **O-6** 한국어 | CLAUDE.md에 "Owner에게 보내는 모든 메시지는 한국어" 지시 |
