# 인지 부하 트리거 컴포넌트 설계

> **목적**: 모델에게 최대한의 유의미한 인지적 부하를 주어 추론 품질을 극대화한다 (Q-3).

---

## 1. 개요

모델은 지시된 범위 내에서 최소한의 부하로 완료를 선언하는 경향이 있다. 인간 시니어 개발자는 작업물을 보면서 자신이 생각하는 최적과의 차이, 그리고 작업에서 보이는 의문점을 기반으로 "이런 방향도 생각해봐"라는 추상적 피드백을 준다. 이 컴포넌트는 그 기능을 시스템적으로 구현한다.

### 인지 부하 트리거의 본질

인지 부하 트리거는 **AI가 고려하지 못한 방향을 찾아 언급하는 것**이다.

- **검수가 아니다**: "이거 안 했잖아"가 아니라 "이 방향도 생각해봐"이다.
- **추상적이다**: 구체적 파일이나 시나리오를 지목하지 않는다. 실제 작업은 수행자가 더 잘 알기 때문에 구체적 지적은 역효과를 낳는다.
- **방향이다**: 해법이나 결론이 아니라 탐색할 방향을 제시한다.

### 두 계층

| 계층 | 메커니즘 | 원칙 준수 | 시점 |
|------|---------|----------|------|
| **자기 주도** | 미션 프롬프트의 다단계 프로토콜 | Q-4a, Q-4b, Q-4c, Q-4d | 세션 내 연속 |
| **외부 주입** | Stop hook agent가 독립 사고 후 미탐색 방향 제시 | Q-4a~Q-4e 전체 | 세션 종료 시도 시 |

자기 주도 계층은 모든 세션에서 기본 수준의 인지 부하를 보장한다. 외부 주입 계층은 별도 컨텍스트의 독립적 사고로 수행자의 맹점을 보완한다.

---

## 2. 자기 주도 계층: 미션 프롬프트 프로토콜

### 2.1 구조

Supervisor가 미션 프롬프트를 생성할 때, 다단계 실행 프로토콜을 포함한다:

```
## 미션: {mission.id} {mission.title}

### 목표
{mission.description}

### 성공 기준
{mission.success_criteria — 항목별}

### 실행 프로토콜

이 미션을 다음 단계로 실행하라. 각 단계를 건너뛰지 마라.

**1단계 — 실행**: 성공 기준을 달성하라.

**2단계 — 검증**: 성공 기준 각 항목을 개별적으로 대조 확인하라.
  달성 여부가 불확실한 항목이 있으면 추가 작업하라.
  {인지 부하 모듈이 생성한 미션 특화 검증 지시}

**3단계 — 미탐색 영역**: 이 접근법의 약점 3가지를 식별하고 대응하라.
  {인지 부하 모듈이 생성한 미션 특화 확장 지시}

**4단계 — 요약**: state/session-summary.md에 다음을 기록하라:
  - 이 미션에서 취한 접근법과 그 이유
  - 가장 불확실했던 결정 3가지와 근거
  - 검토했지만 채택하지 않은 대안과 기각 이유
  - 타협한 부분과 이유
```

4단계의 session-summary.md는 두 가지 역할을 한다:
1. 다음 세션에서 이전 작업 맥락을 복원하는 컨텍스트 보존 수단 (C-1)
2. 외부 주입 계층(Stop Hook Agent)의 핵심 입력 — 수행자가 이미 탐색한 영역을 알려주는 필터

### 2.2 미션 특화 지시 생성

인지 부하 모듈(`system/cognitive_load.py`)이 2~3단계의 미션 특화 내용을 생성한다. Python 기반 결정론적 생성이다:

```python
class CognitiveLoadTrigger:
    """미션 프롬프트의 인지 부하 내용을 생성한다."""

    def generate_mission_protocol(
        self,
        mission: dict,
        health_metrics: dict,
        friction_history: list[dict],
    ) -> dict[str, list[str]]:
        """미션 특화 검증/확장 지시를 생성한다."""
        phase2 = []
        phase3 = []

        # 유사 미션의 friction 이력 기반
        related = [f for f in friction_history
                   if self._is_related(f, mission)]
        if related:
            types = set(f["type"] for f in related)
            phase2.append(
                f"유사 미션에서 {', '.join(types)} friction이 발생한 이력이 있다. "
                f"이 영역을 특히 주의하여 검증하라."
            )

        # 건강 메트릭 기반
        if health_metrics.get("friction_trend") == "increasing":
            phase3.append(
                "시스템 friction이 증가 추세이다. "
                "이 미션의 결과가 friction을 줄이는 방향인지 확인하라."
            )

        stalled = health_metrics.get("stalled_mission_id")
        if stalled == mission.get("id"):
            phase2.append(
                "이 미션이 이전 세션에서 정체되었다. "
                "이전과 다른 접근법을 시도하라."
            )

        return {"phase2": phase2, "phase3": phase3}
```

### 2.3 원칙 준수

자기 주도 계층은 Q-4e(컨텍스트 분리)를 충족하지 않는다 — 수행자 자신이 지시를 수행하므로 같은 컨텍스트이다. Q-4a(작업 기반 — friction 이력), Q-4b(미탐색 — 약점 식별 지시), Q-4c(비처방 — 방향 제시), Q-4d(컨텍스트 내)는 충족한다. Q-4e는 외부 주입 계층이 담당한다.

---

## 3. 외부 주입 계층: Stop Hook Agent

### 3.1 설계 원칙: 입력 추상도 = 출력 추상도

인지 부하 트리거의 출력은 추상적 방향이어야 한다. 그런데 **출력의 추상도는 입력의 추상도에 의해 결정된다.** 구체적 입력(코드 파일, tool call 로그)을 주면 에이전트는 구체적 사고(코드 리뷰, 프로세스 감사)를 하게 되고, 출력 규칙에 "추상적으로 쓰라"고 아무리 지시해도 입력의 자연적 경향을 이기지 못한다.

따라서 Stop Hook Agent의 입력은 **방향 수준의 추상도**로 제한한다.

### 3.2 입력 설계

| 입력 | 추상도 | 역할 | 읽는 시점 |
|------|--------|------|----------|
| 미션 description | 추상적 | 독립 사고의 출발점 | Phase 1 |
| state/session-summary.md | 추상적 | 이미 탐색한 영역 필터 | Phase 2 |
| 변경된 파일 경로 목록 | 추상적 | 작업 범위의 윤곽 | Phase 2 |

**의도적으로 제외하는 입력:**

| 제외 입력 | 제외 이유 |
|-----------|----------|
| 변경된 파일의 실제 내용 | 코드 수준 사고를 유발. 수행자가 코드를 더 잘 안다. |
| run/session-analysis.json | tool call 횟수, 에러 목록 등 운영 메타데이터가 프로세스 감사를 유발 |
| success_criteria | 체크리스트 대조(검수)를 유발 |
| trigger-effectiveness.jsonl | 자동 가중 강화 루프 제거 (§4 참조) |
| $ARGUMENTS.last_assistant_message | 수행자의 raw 추론. session-summary.md가 구조화된 버전을 제공 |
| $ARGUMENTS.transcript_summary | 동일 이유 |

**변경된 파일 경로 목록 획득**: Supervisor가 Stop hook 발동 전에 `run/session-analysis.json`의 `files_written` 필드에서 경로 목록만 추출하여 `run/trigger-context.json`에 기록한다. Stop Hook Agent는 이 파일에서 경로 목록만 읽는다.

```json
{
  "mission_description": "API 인증 모듈을 구현한다...",
  "mission_id": "M-042",
  "files_changed": [
    "system/auth_handler.py",
    "system/middleware.py",
    "tests/test_auth.py"
  ]
}
```

이 파일은 Supervisor(Python)가 생성하므로 내용이 결정론적이다. Stop Hook Agent가 임의 파일을 읽을 유혹을 줄인다.

### 3.3 2단계 프로세스

```
Phase 1: 문제 독립 사고
    │ 입력: 미션 description만
    │ "이 문제에 대해 자유롭게 생각하라"
    │ → 독립적 관점 형성
    │
Phase 2: 미탐색 방향 식별
    │ 입력: session-summary.md + 파일 경로 목록
    │ Phase 1의 사고 ∩ session-summary.md = 이미 탐색된 영역
    │ Phase 1의 사고 - session-summary.md = 미탐색 방향
    │ → 출력
```

**Phase 1이 Phase 2보다 먼저인 이유**: 작업물을 먼저 보면 그 내용에 앵커링된다. 문제를 먼저 독립적으로 생각해야 수행자와 다른 관점이 형성된다. 이것이 인간 시니어 개발자가 코드를 보기 전에 "이 문제라면..."하고 먼저 생각하는 것과 같다.

### 3.4 Stop Hook Agent Prompt

`.claude/settings.json`에 등록한다:

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "agent",
          "model": "opus",
          "timeout": 300,
          "tools": ["Read"],
          "prompt": "당신은 인지 부하 트리거 생성자이다.\n\n메인 에이전트가 미션을 수행하고 완료를 선언했다. 당신의 역할은 수행자가 탐색하지 않은 방향을 식별하는 것이다.\n\n검수하지 마라. 품질을 평가하지 마라. 빠진 항목을 찾지 마라.\n코드 파일을 읽지 마라. 수행자가 코드를 너보다 잘 안다.\n\n## Phase 1: 문제 독립 사고\n\nrun/trigger-context.json을 읽어서 mission_description만 확인하라.\n다른 파일은 아직 읽지 마라.\n\n이 문제에 대해 자유롭게 생각하라.\n무엇이 중요한가? 무엇이 까다로운가?\n어떤 관점들이 존재하는가? 무엇을 놓치기 쉬운가?\n\n## Phase 2: 미탐색 방향 식별\n\n이제 state/session-summary.md를 읽어라.\n수행자가 어떤 접근법을 취했고, 무엇을 고민했고, 무엇을 기각했는지 파악하라.\nrun/trigger-context.json의 files_changed로 작업 범위를 파악하라.\n\nPhase 1에서 당신이 생각한 것 중,\nsession-summary.md에 나타나지 않는 것을 찾아라.\n이것이 수행자가 탐색하지 않은 방향이다.\n\n다음은 제외하라:\n- session-summary.md에 '기각한 대안'으로 나열된 것 (이미 고려하고 의도적으로 제외한 것)\n- 수행자가 이미 충분히 다룬 영역\n\n## 출력 규칙\n\n- 최대 2개 방향. 미탐색 방향이 없으면 0개.\n- 구체적 파일, 코드 위치, 시나리오를 언급하지 마라.\n- '~의 관점에서 탐색해봐라' 수준의 추상도로 작성하라.\n- 수행자가 자기 지식으로 구체화할 수 있어야 한다.\n- 해법을 제시하지 마라. 방향만 제시하라.\n\n## 무시할 것\n\n$ARGUMENTS의 last_assistant_message와 transcript_summary는 수행자의 해석이다. 무시하라. session-summary.md가 구조화된 버전을 제공한다."
        }
      ]
    }
  ]
}
```

### 3.5 도구 제한

Stop Hook Agent에는 `Read` 도구만 제공한다.

| 도구 | 제공 | 이유 |
|------|:----:|------|
| Read | O | trigger-context.json, session-summary.md 읽기에 필요 |
| Glob | X | 파일 탐색은 코드 읽기로 이어짐 |
| Grep | X | 코드 검색은 구체적 사고를 유발 |
| Bash | X | 임의 명령 실행 불필요 |

도구를 최소화하면 에이전트가 프롬프트의 의도대로 동작할 확률이 높아진다. Read만 있으면 지정된 2개 파일만 읽고 사고에 집중하게 된다.

### 3.6 작동 흐름

```
수행자: 4단계 프로토콜 완료
    │ session-summary.md 작성됨 (4단계 산출물)
    │
    ▼
수행자: 작업 완료, 종료 시도
    │
    ▼
Supervisor: run/trigger-context.json 생성
    │ (mission description + 변경 파일 경로 목록)
    │
    ▼
Stop hook agent (별도 컨텍스트, opus, 300s):
    │
    │ Phase 1: trigger-context.json에서 mission_description 읽기
    │          문제에 대해 독립적으로 사고
    │
    │ Phase 2: session-summary.md 읽기
    │          trigger-context.json에서 files_changed 읽기
    │          Phase 1 사고 - summary = 미탐색 방향 식별
    │
    ▼
미탐색 방향 0~2개 출력
    │
    ├── 0개 → ok: true (수행자가 충분히 탐색함)
    │         세션 종료 허용
    │
    └── 1~2개 → ok: false, reason: 방향 주입
                  │
                  ▼
        수행자: 같은 컨텍스트에서 방향을 받고 추가 탐색
            │ (1~4단계의 전체 작업 기억 보존)
            │
            ▼
        수행자: 추가 완료 → stop_hook_active: true → 세션 종료
```

### 3.7 trigger-context.json 생성

Supervisor가 Stop hook 발동 직전에 생성한다:

```python
def prepare_trigger_context(
    self,
    mission: dict,
    session_analysis: dict,
) -> None:
    """Stop Hook Agent를 위한 최소 컨텍스트를 생성한다."""
    context = {
        "mission_id": mission["id"],
        "mission_description": mission["description"],
        "files_changed": sorted(
            set(session_analysis.get("files_read", []))
            | set(session_analysis.get("files_written", []))
        ),
    }
    atomic_write(
        self.run_dir / "trigger-context.json",
        json.dumps(context, ensure_ascii=False, indent=2),
    )
```

이 함수는 session-analysis.json에서 파일 경로만 추출하여 별도 파일로 기록한다. Stop Hook Agent가 session-analysis.json 전체를 읽을 이유를 제거한다.

### 3.8 출력 예시

**좋은 트리거 (추상적 방향):**

```
미션: "API 인증 모듈 구현"

방향 1: 이 인증 설계가 암묵적으로 가정하는 시간 조건들의 관점에서 탐색해봐라.

방향 2: 인증 실패를 소비하는 쪽의 관점에서 현재 에러 응답 설계를 탐색해봐라.
```

수행자는 이 추상적 방향을 받고, 자기가 작성한 코드에 대한 깊은 지식을 바탕으로 구체적으로 탐색한다. "시간 조건"이라는 방향에서 토큰 만료, 세션 타임아웃, rate limit 윈도우 등을 스스로 도출한다.

**나쁜 트리거 (구체적 지적 — 이 설계에서 생성되지 않아야 하는 것):**

```
auth_handler.py:45에서 토큰 검증을 동기적으로 수행한다.
장시간 요청 도중 토큰이 만료되면 어떻게 되는가?
```

이것은 짧은 시간 동안 생각한 외부 에이전트의 피상적 코드 리뷰이다. 수행자가 수 시간 동안 작업한 코드에 대해 더 정확한 판단을 가지고 있으므로 역효과를 낳는다.

### 3.9 0개 출력의 의미

Stop Hook Agent가 미탐색 방향을 0개 출력하는 것은 정상이다. 이는 수행자가 충분히 다양한 방향을 탐색했음을 의미한다. 강제로 방향을 생성하면 무의미한 트리거가 되므로, 0개 출력을 허용하고 이 경우 세션 종료를 허용한다.

### 3.10 원칙 준수

| 원칙 | 충족 방식 |
|------|----------|
| Q-4a 작업 기반 | session-summary.md(수행자의 구조화된 자기 평가)와 파일 경로 목록(작업 범위)을 읽음 |
| Q-4b 미탐색 지향 | Phase 1의 독립 사고와 Phase 2의 session-summary.md 대조로 미탐색 영역을 구조적으로 식별 |
| Q-4c 비처방 | "해법을 제시하지 마라. 방향만 제시하라" 명시. 추상적 출력 규칙이 처방을 방지 |
| Q-4d 컨텍스트 내 전달 | Stop hook reason이 메인 세션에 주입. 수행자의 전체 작업 기억 보존 |
| Q-4e 컨텍스트 분리 | 별도 컨텍스트에서 실행. session-summary.md(구조화된 자기 평가)를 입력으로 사용하되, 수행자의 전체 추론 과정은 제외. 코드 파일 미제공으로 앵커링 방지 |

**Q-4e에 대한 보충**: session-summary.md는 수행자의 "무엇을 고민했는가"를 알려주지만, "어떻게 추론했는가"는 포함하지 않는다. 이것은 PR description이 코드 리뷰어에게 의도를 알려주는 것과 같다. 의도를 알아야 맹점을 정확히 찾을 수 있고, 전체 추론을 공유하지 않으므로 컨텍스트 분리는 유지된다.

---

## 4. 트리거 이력 기록

### 4.1 목적

트리거가 어떤 방향을 제시했는지 기록한다. 이 기록은 Proactive Review 미션(S-3)에서 트리거 시스템의 전반적 효과를 종합 판단하는 데 사용된다.

### 4.2 설계 결정: 자동 효과 측정을 하지 않는다

이전 설계에서는 트리거 전후의 변경량(새 파일 수, 새 영역 수)으로 효과를 자동 측정하고, 효과가 높은 분석 유형을 강화하는 피드백 루프를 가지고 있었다. 이 접근은 두 가지 문제가 있다:

1. **변경량은 품질의 프록시가 아니다.** "많이 수정함 = 좋은 트리거"로 측정하면 복잡성 증가를 강화하는 방향으로 진화한다.
2. **트리거 효과는 자동 측정이 근본적으로 어렵다.** "코드가 더 좋아졌는가?"를 결정론적으로 판단할 수 없다.

따라서 자동 점수화와 자동 가중을 제거하고, **사실만 기록**한다.

### 4.3 기록 형식

`state/trigger-log.jsonl` (append-only, Git 추적):

```jsonl
{"mission_id":"M-042","directions":["시간 조건 관점 탐색","에러 소비자 관점 탐색"],"direction_count":2,"phase1_thoughts_summary":"보안, 분산환경, 시간의존성, 에러분류","already_explored_in_summary":["에러분류 — session-summary에서 기각됨"],"timestamp":"2026-03-27T10:00:00Z"}
```

| 필드 | 설명 |
|------|------|
| `mission_id` | 대상 미션 |
| `directions` | 제시된 방향 (0~2개) |
| `direction_count` | 제시된 방향 수 |
| `phase1_thoughts_summary` | Phase 1에서 에이전트가 생각한 키워드 요약 |
| `already_explored_in_summary` | session-summary.md와 겹쳐서 제외된 방향 |
| `timestamp` | 기록 시각 |

### 4.4 이력 활용

trigger-log.jsonl은 Stop Hook Agent에 직접 제공되지 않는다. 대신:

- **Proactive Review 미션** (S-3, 매 N미션마다)에서 이 이력을 읽고 트리거 시스템의 전반적 효과를 판단한다.
- Proactive Review가 "트리거 방향이 반복적이다", "Phase 1 사고가 피상적이다" 등을 발견하면 Stop Hook Agent 프롬프트 개선 미션을 생성한다.
- 이것이 자동 피드백 루프가 아닌 **자기개선 루프를 통한 간접 개선**이다.

---

## 5. StreamAnalyzer의 역할

StreamAnalyzer는 인지 부하 트리거의 입력에서 제거되었지만, 시스템에서 여전히 중요한 역할을 한다.

### 5.1 유지되는 역할

| 소비자 | 사용 목적 |
|--------|----------|
| Supervisor | 세션 모니터링 — 에러 감지, stuck 감지, rate limit 감지 |
| ErrorClassifier | 에러 분류의 입력 데이터 |
| SessionStart Hook | 세션 재개 시 이전 작업 패턴 요약 주입 |
| Friction 기록 | 에러/느린 실행 등 friction 원천 데이터 |
| trigger-context.json 생성 | files_written에서 파일 경로 목록 추출 |
| Proactive Review | 시스템 전반 분석 시 작업 패턴 데이터 |

### 5.2 제거된 역할

| 이전 역할 | 제거 이유 |
|-----------|----------|
| Stop Hook Agent의 주 입력 | 구체적 운영 메타데이터가 프로세스 감사를 유발 |

StreamAnalyzer 클래스와 session-analysis.json의 구조는 변경 없이 유지한다. 인지 부하 트리거와의 직접 연결만 끊는다.

---

## 6. 컨텍스트 흐름

```
세션 시작 (미션 프롬프트 + 4단계 프로토콜)
    │
    ├── 1단계: 실행 (turns 1~N)
    │     Supervisor: stream-json → session-analysis.json 실시간 갱신
    │
    ├── 2단계: 검증 (1단계 컨텍스트 위에서)
    │
    ├── 3단계: 미탐색 영역 (1+2단계 컨텍스트 위에서)
    │
    ├── 4단계: 요약 → state/session-summary.md 작성
    │     (접근법, 불확실한 결정, 기각한 대안, 타협)
    │
    ▼
수행자 "완료" → Stop hook 발동
    │
    │ Supervisor: run/trigger-context.json 생성
    │   (mission description + 변경 파일 경로 목록)
    │
    ▼
Stop hook agent (opus, 300s, 별도 컨텍스트)
    │
    │ Phase 1: trigger-context.json의 mission_description만 읽기
    │          문제에 대해 독립 사고
    │
    │ Phase 2: session-summary.md 읽기
    │          trigger-context.json의 files_changed 읽기
    │          독립 사고 - summary = 미탐색 방향
    │
    ▼
0~2개 방향 출력
    │
    ├── 0개 → ok: true → 세션 종료 허용
    │
    └── 1~2개 → ok: false, reason: [방향]
        │
        ▼
    수행자: 추가 탐색 (전체 컨텍스트 보존)
        │
        ▼
    stop_hook_active: true → 세션 종료
        │
        ▼
    Supervisor: trigger-log.jsonl에 사실 기록
```

---

## 7. 구성 요소

| 구성 요소 | 위치 | 역할 |
|----------|------|------|
| CognitiveLoadTrigger | `system/cognitive_load.py` | 미션 특화 지시 생성 (자기 주도 계층) |
| StreamAnalyzer | `system/cognitive_load.py` | stream-json → session-analysis.json (Supervisor 모니터링 + trigger-context 원천) |
| Stop hook agent | `.claude/settings.json` | 별도 컨텍스트에서 독립 사고 → 미탐색 방향 생성 |
| trigger-context.json | `run/` | Stop Hook Agent 전용 최소 입력 (mission description + 파일 경로) |
| session-summary.md | `state/` | 수행자의 구조화된 자기 평가 (4단계 프로토콜 산출물) |
| trigger-log.jsonl | `state/` | 트리거 이력 사실 기록 (Proactive Review 입력) |
| session-analysis.json | `run/` | 작업 패턴 기록 (Supervisor 모니터링용, Stop Hook Agent에는 미제공) |

---

## 8. 자기개선 경로

이 컴포넌트의 모든 부분은 자기개선 대상이다 (S-4):

| 대상 | 방법 |
|------|------|
| Stop hook agent prompt | `.claude/settings.json` 수정. Phase 구조, 출력 규칙 변경 |
| 미션 프로토콜 | `system/cognitive_load.py`의 generate_mission_protocol() 수정 |
| 4단계 프로토콜 구조 | 단계 추가/변경, session-summary.md 형식 변경 |
| trigger-context.json 내용 | Supervisor의 prepare_trigger_context() 수정 |
| StreamAnalyzer | 새 패턴 추출 로직 추가 (Supervisor 모니터링 개선) |

**자기개선 데이터 기반**: trigger-log.jsonl이 Proactive Review 미션의 입력이 된다. Proactive Review가 트리거 이력을 분석하여 "방향이 반복적이다", "Phase 1 사고가 특정 패턴에 치우쳐 있다" 등을 발견하면 트리거 시스템 개선 미션을 생성한다. 자동 피드백 루프가 아닌 자기개선 루프를 통한 간접 개선이므로, "변경량 = 효과"와 같은 잘못된 프록시에 의한 퇴화를 방지한다.

---

## 9. Q-3/Q-4 준수 검증

| 요구사항 | 충족 |
|----------|------|
| Q-3 최대 인지 부하 | 자기 주도(4단계 프로토콜) + 외부 주입(Stop hook agent의 독립 사고 기반 방향 제시). 같은 컨텍스트에서 축적 |
| Q-4a 작업 기반 | session-summary.md(수행자의 자기 평가) + 파일 경로 목록(작업 범위). 작업의 관찰에 기반 |
| Q-4b 미탐색 지향 | Phase 1(독립 사고) - Phase 2(이미 탐색한 영역) = 미탐색 방향. 구조적으로 미탐색을 겨냥 |
| Q-4c 비처방 | "해법을 제시하지 마라. 방향만 제시하라" + 추상적 출력 규칙으로 이중 보장 |
| Q-4d 컨텍스트 내 전달 | Stop hook reason이 동일 세션에 주입. 수행자의 전체 작업 기억 보존 |
| Q-4e 컨텍스트 분리 | 별도 컨텍스트에서 실행. session-summary.md(구조화된 자기 평가)만 입력. 전체 추론 과정 및 코드 파일 미제공 |
