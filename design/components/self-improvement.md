# Self-Improvement 컴포넌트 설계

> 요구사항 S-1 ~ S-5 구현. 재귀적 자기개선(Recursive Self-Improvement) 시스템.

Self-Improvement는 단일 컴포넌트가 아니라 **여러 컴포넌트에 걸친 행동 패턴**이다. CLAUDE.md와 `.claude/rules/self-improvement.md`에 정의된 행동 규칙, Stop Hook의 개선 미션 주입 로직, StateManager의 friction 축적/임계값 판단 로직이 협력하여 동작한다.

---

## 1. Friction Detection (S-1)

Friction은 시스템이 Purpose를 추구하는 것을 방해하는 모든 마찰이다. 다양한 원천에서 감지되어 `state/friction.json`에 누적 기록된다.

### 1.1 감지 원천 및 메커니즘

| Source | Detection Method | Friction Type | 감지 주체 |
|--------|-----------------|---------------|-----------|
| Tool execution 에러 | Claude Code가 stream-json으로 에러 보고 | `error` | SessionManager |
| 동일 에러 패턴 3회 이상 | StateManager가 `pattern_key` 기준으로 friction.json 집계 | `repeated_failure` | StateManager |
| N분간 진전 없음 | Supervisor timeout detection (heartbeat 미갱신) | `stuck` | Supervisor |
| 테스트 실패 | Claude Code가 테스트 결과 보고 | `quality` | Claude Code (자체 기록) |
| Owner 수동 개입 | Owner가 미션 주입 또는 예상치 못한 요청에 응답 | `owner_intervention` | SlackClient |
| 미션 예상 시간 2배 초과 | SessionManager가 미션 시작 시간 대비 경과 추적 | `slow` | SessionManager |
| Compaction 후 중요 컨텍스트 손실 | Claude Code가 이전 작업 결과를 찾지 못함 | `context_loss` | Claude Code (자체 기록) |

### 1.2 pattern_key

`pattern_key`는 유사한 friction을 그룹화하는 정규화된 문자열이다. 같은 근본 원인을 가진 friction이 흩어지지 않고 축적될 수 있도록 한다.

**형식**: `{category}_{subcategory}_{identifier}`

**예시**:
| pattern_key | 설명 |
|-------------|------|
| `api_timeout` | API 호출 타임아웃 |
| `test_failure_auth` | 인증 관련 테스트 실패 |
| `import_error_module_x` | 특정 모듈 임포트 에러 |
| `stuck_file_write` | 파일 쓰기에서 반복적으로 멈춤 |
| `context_loss_mission_result` | 미션 결과가 compaction 후 유실 |
| `slow_test_suite` | 테스트 스위트 실행이 반복적으로 느림 |

**생성 규칙**:
1. **자동 감지 friction**: SessionManager/Supervisor가 에러 메시지를 정규화하여 생성. 구체적 파일명, 줄번호, 타임스탬프 등은 제거하고 패턴만 추출.
2. **Claude Code 자체 기록 friction**: Claude Code가 friction 기록 시 직접 pattern_key를 지정. CLAUDE.md의 friction 기록 규칙에 따라 일관된 네이밍.
3. **Owner 개입 friction**: SlackClient가 요청 유형을 기반으로 생성.

### 1.3 Friction 레코드 구조

```json
{
  "id": "F-042",
  "type": "repeated_failure",
  "pattern_key": "test_failure_auth",
  "description": "auth 모듈 테스트가 3회 연속 실패. OAuth token refresh 로직 문제 추정",
  "context": {
    "mission_id": "M-015",
    "session_id": "session-20260325-143000",
    "error_messages": ["AssertionError: expected 200, got 401", "..."],
    "occurrences": 3
  },
  "resolution": null,
  "created_at": "2026-03-25T14:35:00Z",
  "resolved_at": null
}
```

### 1.4 감지 흐름

```
[에러/이상 발생]
    │
    ▼
[감지 주체가 friction 판별]
  SessionManager: stream-json 파싱 중 에러 감지
  Supervisor: heartbeat 타임아웃 감지
  Claude Code: 작업 중 품질/컨텍스트 이슈 자체 감지
  SlackClient: Owner 개입 패턴 감지
    │
    ▼
[StateManager.add_friction()]
  1. pattern_key 생성/매칭
  2. friction.json에 원자적 추가
  3. 동일 pattern_key의 미해결 friction 수 집계
  4. 임계값 확인 → 도달 시 개선 미션 트리거
    │
    ▼
[friction.json 갱신 완료]
```

---

## 2. Friction Accumulation and Threshold (S-2)

### 2.1 축적 메커니즘

각 friction은 `pattern_key`로 그룹화된다. StateManager는 friction 추가 시 동일 `pattern_key`를 가진 **미해결(`resolution == null`)** friction의 수를 집계한다.

```python
# StateManager 내부 로직 (의사 코드)
def add_friction(self, friction: dict) -> Optional[dict]:
    """friction 추가. 임계값 도달 시 개선 미션 반환."""
    # 1. friction.json에 추가
    self._append_friction(friction)

    # 2. 동일 pattern_key 미해결 friction 집계
    pattern_key = friction["pattern_key"]
    unresolved_count = self._count_unresolved_by_pattern(pattern_key)

    # 3. 임계값 확인
    threshold = self.get_config("friction_threshold")  # 기본값: 3
    if unresolved_count >= threshold:
        return self._generate_improvement_mission(pattern_key)

    return None
```

### 2.2 임계값 설정

| 설정 | 위치 | 기본값 | 설명 |
|------|------|--------|------|
| `friction_threshold` | `state/config.toml` | `3` | 동일 pattern_key friction이 이 값 이상 축적되면 자동 트리거 |

이 임계값 자체도 자기개선 대상이다 (S-5). Claude Code가 패턴 분석을 통해 값을 조정할 수 있다.

### 2.3 자동 트리거: 개선 미션 생성

임계값 도달 시 StateManager가 자동으로 개선 미션을 생성한다.

```json
{
  "id": "M-099",
  "title": "자기개선: test_failure_auth 패턴 해결",
  "description": "## Friction 분석\n\n### 패턴: test_failure_auth\n- 미해결 friction 3건 축적\n- 최초 발생: 2026-03-25T14:00:00Z\n- 최근 발생: 2026-03-25T14:35:00Z\n\n### 관련 Friction 기록\n- F-038: auth 모듈 테스트 실패 (OAuth token 만료)\n- F-040: auth 모듈 테스트 실패 (token refresh 타이밍)\n- F-042: auth 모듈 테스트 3회 연속 실패\n\n### 개선 방향\n1. 근본 원인 분석\n2. 코드 수정 또는 테스트 수정\n3. 재발 방지 메커니즘 구현",
  "success_criteria": [
    "test_failure_auth 패턴의 근본 원인이 식별되었다",
    "수정 후 관련 테스트가 통과한다",
    "재발 방지 대책이 구현되었다"
  ],
  "priority": 0,
  "status": "pending",
  "blockers": [],
  "dependencies": [],
  "created_at": "2026-03-25T14:35:00Z",
  "source": "friction"
}
```

**핵심 속성**:
- `priority: 0` — 최고 우선순위. 다른 모든 미션보다 먼저 실행
- `source: "friction"` — friction 축적에 의한 자동 생성임을 표시
- `description`에 모든 관련 friction 기록과 분석 프롬프트 포함

### 2.4 미션 큐 내 우선순위

Stop Hook이 다음 미션을 선택할 때 priority 기준으로 정렬한다. `priority: 0`인 개선 미션은 항상 최우선 실행된다.

```
Priority 0: 자기개선 미션 (friction 축적 / proactive)
Priority 1: Owner 요청 미션
Priority 2: Purpose 기반 일반 미션 (기본값)
Priority 3+: 낮은 우선순위 미션
```

---

## 3. Proactive Self-Improvement (S-3)

friction이 없는 정상 운영에서도 주기적으로 시스템 전반을 검토하는 사전적 자기개선이다.

### 3.1 트리거 조건

| 설정 | 위치 | 기본값 | 설명 |
|------|------|--------|------|
| `proactive_improvement_interval` | `state/config.toml` | `10` | 이 값만큼의 미션이 완료될 때마다 시스템 검토 미션 자동 생성 |

StateManager가 미션 완료를 기록할 때 완료된 미션 수를 카운트한다. `completed_count % proactive_improvement_interval == 0`일 때 트리거된다.

### 3.2 시스템 검토 미션

자동 생성되는 검토 미션의 description:

```
시스템 전반을 검토하고 개선점을 찾아라.
검토 대상:
1. Purpose 정렬: 최근 미션들이 Purpose에 부합하는가?
2. 전략 효과성: 현재 전략이 효과적인가?
3. 도구 사용 패턴: 비효율적인 패턴이 있는가?
4. Friction 경향: 반복되는 마찰 패턴이 있는가?
5. 코드 품질: 시스템 코드에 개선점이 있는가?
6. 성능: 미션 실행 시간이 적절한가?
```

```json
{
  "id": "M-100",
  "title": "사전 시스템 검토 (미션 #100 도달)",
  "description": "시스템 전반을 검토하고 개선점을 찾아라.\n검토 대상:\n1. Purpose 정렬: 최근 미션들이 Purpose에 부합하는가?\n2. 전략 효과성: 현재 전략이 효과적인가?\n3. 도구 사용 패턴: 비효율적인 패턴이 있는가?\n4. Friction 경향: 반복되는 마찰 패턴이 있는가?\n5. 코드 품질: 시스템 코드에 개선점이 있는가?\n6. 성능: 미션 실행 시간이 적절한가?",
  "success_criteria": [
    "6개 검토 영역 모두 분석 완료",
    "발견된 개선점에 대한 구체적 개선 미션이 생성되었다",
    "개선점이 없다면 그 근거가 friction.json에 기록되었다"
  ],
  "priority": 0,
  "status": "pending",
  "blockers": [],
  "dependencies": [],
  "created_at": "2026-03-25T20:00:00Z",
  "source": "proactive"
}
```

### 3.3 검토 결과 처리

Claude Code가 검토 미션을 실행한 결과:

1. **개선점 발견 시**: 각 개선점에 대해 구체적인 개선 미션을 missions.json에 추가. priority는 개선의 긴급도에 따라 0~2.
2. **개선점 없음**: friction.json에 `type: "proactive_review"`, `resolution: "no_issues_found"` 기록. 이 자체가 시스템 건전성의 증거.
3. **자기개선 규칙 개선 필요**: `.claude/rules/self-improvement.md` 또는 검토 프롬프트 자체를 수정 (meta-improvement).

---

## 4. Unlimited Improvement Scope (S-4)

자기개선의 범위에는 **일체의 제한이 없다**. 시스템의 모든 구성 요소가 개선 대상이다.

### 4.1 개선 가능 대상 목록

| # | 대상 | 파일 경로 | 개선 예시 |
|---|------|-----------|-----------|
| 1 | AI 에이전트 지시문 | `CLAUDE.md` | 미션 실행 효율을 높이는 지시 추가, 불필요한 지시 제거 |
| 2 | 모듈별 규칙 | `.claude/rules/*.md` | 규칙 세분화, 새로운 규칙 파일 추가, 기존 규칙 정교화 |
| 3 | 전략 | `state/strategy.json` | 전략 방향 수정, 새로운 전략 축 추가, 전략 우선순위 변경 |
| 4 | 동적 설정 | `state/config.toml` | 임계값 조정, 새로운 설정 항목 추가 |
| 5 | Hook 스크립트 | `system/hooks/*.py` | Stop Hook 미션 선택 로직 개선, SessionStart Hook 컨텍스트 주입 최적화 |
| 6 | 시스템 코드 | `system/*.py` | Supervisor, SessionManager, StateManager, SlackClient, ErrorClassifier 로직 개선 |
| 7 | TUI 코드 | `tui/*.py` | 대시보드 레이아웃 개선, 새로운 위젯 추가, 성능 최적화 |
| 8 | CLI 코드 | `cli/*.py` | 새로운 커맨드 추가, 기존 커맨드 개선 |
| 9 | 의존성 | `pyproject.toml` | 새로운 라이브러리 추가, 버전 업그레이드 |
| 10 | 테스트 코드 | `tests/*.py` | 테스트 커버리지 확대, 테스트 효율 개선 |
| 11 | 자기개선 규칙 자체 | `.claude/rules/self-improvement.md` | 개선 트리거 조건 정교화, 분석 프롬프트 개선, 안전장치 추가/수정 |

### 4.2 개선 대상별 영향도 분류

| 영향도 | 대상 | Owner 알림 |
|--------|------|------------|
| **High** | `system/*.py`, `system/hooks/*.py`, `state/config.toml` (임계값 >50% 변경), `state/strategy.json` | Slack 알림 필수 |
| **Medium** | `CLAUDE.md`, `.claude/rules/*.md`, `pyproject.toml` | Slack 알림 권장 |
| **Low** | `tui/*.py`, `cli/*.py`, `tests/*.py` | 알림 불필요 |

### 4.3 개선 대상 접근 방식

Claude Code는 일반적인 코드 편집과 동일한 방식으로 모든 파일을 수정한다. 특별한 API나 인터페이스가 필요하지 않다. 이것이 "범위 무제한"의 핵심이다 -- Claude Code가 읽고 쓸 수 있는 모든 파일이 개선 대상이다.

---

## 5. All Thresholds Modifiable (S-5)

`state/config.toml`의 모든 필드는 Claude Code에 의해 자기개선의 일환으로 수정될 수 있다. TOML 형식은 인라인 주석(`#`)을 지원하므로, Claude Code가 임계값을 수정할 때 변경 근거를 주석으로 남길 수 있다. 이를 통해 별도의 변경 로그 없이도 config 파일 자체에서 수정 이력과 근거를 파악할 수 있다.

**규칙**: Claude Code가 `config.toml`의 값을 수정할 때, 반드시 해당 줄에 변경 근거를 인라인 주석으로 추가해야 한다.

```toml
# 예시: 수정 근거가 포함된 config.toml
friction_threshold = 2  # 3→2 (2026-03-25): 2회째에서 이미 패턴 확정되는 경우 다수
proactive_improvement_interval = 20  # 10→20 (2026-03-26): 최근 5회 검토에서 개선점 미발견
session_timeout_minutes = 150  # 120→150 (2026-03-26): 복잡한 미션이 120분 timeout에 빈번히 도달
```

### 5.1 자기개선 가능한 config.toml 필드

| 필드 | 기본값 | 타입 | 설명 |
|------|--------|------|------|
| `friction_threshold` | `3` | int | 동일 pattern_key friction 축적 시 개선 트리거 임계값 |
| `proactive_improvement_interval` | `10` | int | N개 미션 완료마다 사전 검토 미션 생성 |
| `context_refresh_after_compactions` | `5` | int | N회 compaction 후 새 세션으로 컨텍스트 리프레시 |
| `goal_drift_check_interval` | `20` | int | N개 미션마다 Purpose 정렬 확인 |
| `session_timeout_minutes` | `120` | int | 세션 타임아웃 (분) |
| `max_consecutive_failures` | `3` | int | 연속 실패 시 에스컬레이션 임계값 |
| `slack_notification_level` | `"warning"` | string | Slack 알림 수준 (`"info"`, `"warning"`, `"error"`, `"critical"`) |
| `mission_idle_generation_count` | `3` | int | 미션 큐 비었을 때 한 번에 생성할 미션 수 |
| `owner_feedback_interval` | `20` | int | N미션 동안 Owner 상호작용 없으면 방향 확인 요청 |

### 5.2 임계값 수정 시나리오

**예시 1: friction_threshold 하향 조정**
```
관찰: friction_threshold=3인데, 2번째 반복에서 이미 문제가 명확한 경우가 많음
판단: 임계값을 2로 낮추면 더 빨리 개선에 착수 가능
수정: config.toml의 friction_threshold를 3→2로 변경
기록: friction.json에 type "self_improvement" 기록
```

**예시 2: proactive_improvement_interval 상향 조정**
```
관찰: 10미션마다 검토하는데, 최근 5회 검토에서 개선점이 발견되지 않음
판단: 시스템이 안정적이므로 검토 주기를 늘려도 됨
수정: config.toml의 proactive_improvement_interval을 10→20으로 변경
기록: friction.json에 type "self_improvement" 기록
```

**예시 3: session_timeout_minutes 상향 조정**
```
관찰: 복잡한 미션이 120분 timeout에 자주 걸림 → slow friction 발생
판단: 타임아웃을 150분으로 늘려 불필요한 friction 감소
수정: config.toml의 session_timeout_minutes를 120→150으로 변경
기록: friction.json에 type "self_improvement" 기록
```

### 5.3 임계값 수정 제약

임계값 수정에 기술적 제약은 없지만, 안전장치가 적용된다 (섹션 6 참조):
- 50% 이상 변경 시 Owner Slack 알림
- Git checkpoint가 수정 전에 생성되어 롤백 가능
- 수정 이력이 friction.json에 기록되어 추적 가능

---

## 6. Safety Guardrails

자기개선은 강력하지만 위험할 수 있다. 다음 안전장치가 시스템을 보호한다.

### 6.1 Git Checkpoint

**모든 자기 수정 전에 Git checkpoint를 생성한다.**

```bash
git add -A
git commit -m "checkpoint before self-improvement: {pattern_key}"
git tag checkpoint-si-{timestamp}
```

이 checkpoint는 개선이 실패할 경우 즉시 롤백할 수 있는 복구 지점이다.

### 6.2 변경 기록

모든 자기 수정은 friction.json에 `type: "self_improvement"` 레코드로 기록된다.

```json
{
  "id": "F-050",
  "type": "self_improvement",
  "pattern_key": "self_improvement_config_change",
  "description": "friction_threshold를 3→2로 하향 조정. 근거: 2번째 반복에서 이미 문제 명확",
  "context": {
    "target_file": "state/config.toml",
    "field": "friction_threshold",
    "old_value": 3,
    "new_value": 2,
    "rationale": "최근 10건의 friction 중 8건이 2회째에서 이미 패턴 확정",
    "checkpoint_tag": "checkpoint-si-20260325-150000"
  },
  "resolution": "applied",
  "created_at": "2026-03-25T15:00:00Z",
  "resolved_at": "2026-03-25T15:00:00Z"
}
```

### 6.3 자동 롤백

테스트가 존재하는 경우, 자기 수정 후 테스트를 실행한다. 테스트 실패 시 자동으로 checkpoint로 롤백한다.

```
[자기 수정 완료]
    │
    ▼
[tests/ 디렉토리에 테스트 존재?]
    │
    ├── Yes → [pytest 실행]
    │           │
    │           ├── 통과 → [commit + 계속]
    │           │
    │           └── 실패 → [git checkout checkpoint-si-{ts}]
    │                       [friction.json에 롤백 기록]
    │                       [원래 friction은 미해결 상태 유지]
    │
    └── No → [commit + 계속]
```

### 6.4 Owner 알림

**High 영향도 변경** 시 Slack으로 Owner에게 알린다.

알림 대상:
- `state/strategy.json` 변경 (전략 진화)
- `state/config.toml` 임계값 50% 이상 변경
- `system/*.py` 또는 `system/hooks/*.py` 코드 수정
- 연속 자기개선 미션 3회 도달

알림 메시지 형식:
```
🔧 자기개선 알림

변경 대상: state/config.toml
변경 내용: friction_threshold 3 → 2
근거: 최근 10건 friction 중 8건이 2회째에서 패턴 확정
Git 태그: checkpoint-si-20260325-150000

롤백 필요 시: `automata reset checkpoint-si-20260325-150000`
```

### 6.5 무한 개선 루프 방지

연속 자기개선 미션이 3회를 초과하면 일반 미션으로 복귀한다.

```python
# Stop Hook 내부 로직 (의사 코드)
MAX_CONSECUTIVE_IMPROVEMENTS = 3

def select_next_mission(missions):
    recent_completed = get_recent_completed_missions(3)
    consecutive_improvements = count_consecutive_source(
        recent_completed, sources=["friction", "proactive"]
    )

    if consecutive_improvements >= MAX_CONSECUTIVE_IMPROVEMENTS:
        # 개선 미션 스킵, 일반 미션 선택
        return select_first_non_improvement_mission(missions)

    # 정상: priority 순서대로 선택
    return select_by_priority(missions)
```

이 제한은 "개선이 또 다른 개선을 낳고, 그것이 또 다른 개선을 낳는" 무한 루프를 방지한다. 3회 연속 개선 후에는 반드시 일반 미션을 실행하여 실제 작업 진전을 보장한다.

---

## 7. Self-Improvement Flow (상세)

### 7.1 전체 흐름

```
[Trigger: friction 임계값 도달 OR proactive interval 도달]
    │
    ▼
[개선 미션 생성]
  priority: 0 (최고)
  source: "friction" 또는 "proactive"
  description: friction 데이터 + 분석 프롬프트 포함
    │
    ▼
[missions.json에 추가]
  StateManager가 원자적으로 기록
    │
    ▼
[Stop Hook이 개선 미션 선택]
  현재 세션의 Stop Hook 발동 시
  priority: 0 미션이 최우선 선택됨
  Claude Code 컨텍스트에 미션 주입
    │
    ▼
[Claude Code가 개선 실행]
  ┌─────────────────────────────────────────────┐
  │ 1. Friction 패턴 분석 / 시스템 상태 분석     │
  │    - friction.json에서 관련 기록 읽기        │
  │    - 패턴의 근본 원인 추론                   │
  │                                              │
  │ 2. 근본 원인 식별                            │
  │    - 코드 문제? 설정 문제? 전략 문제?        │
  │    - 어떤 파일을 수정해야 하는가?            │
  │                                              │
  │ 3. 개선 설계                                 │
  │    - 구체적 변경 계획 수립                   │
  │    - 부작용 예측                             │
  │                                              │
  │ 4. Git checkpoint 생성                       │
  │    git add -A && git commit                  │
  │    git tag checkpoint-si-{timestamp}         │
  │                                              │
  │ 5. 변경 구현                                 │
  │    - 대상 파일 수정                          │
  │    - 필요 시 새 파일 생성                    │
  │                                              │
  │ 6. 테스트 실행 (해당되는 경우)               │
  │    - pytest 실행                             │
  │    - 관련 테스트만 또는 전체 테스트          │
  │                                              │
  │ 7-a. 테스트 통과 시                          │
  │    - git commit으로 변경 확정                │
  │    - friction.json에 성공 기록               │
  │                                              │
  │ 7-b. 테스트 실패 시                          │
  │    - checkpoint로 롤백                       │
  │    - friction.json에 롤백 기록               │
  │    - 원래 friction은 미해결 상태 유지        │
  │                                              │
  │ 8. 결과 기록                                 │
  │    - friction.json에 self_improvement 기록   │
  │    - 관련 friction records 해소 처리         │
  │    - missions.json에서 status 완료 처리      │
  └─────────────────────────────────────────────┘
    │
    ▼
[개선 미션 완료]
  관련 friction records의 resolved_at 설정
  sessions.json에 세션 결과 기록
  다음 미션으로 진행
```

### 7.2 컴포넌트 간 상호작용

```
StateManager                     Stop Hook                    Claude Code
    │                                │                            │
    │  [friction 추가]               │                            │
    │  add_friction()                │                            │
    │──count unresolved──►           │                            │
    │  threshold 도달!               │                            │
    │──generate mission──►           │                            │
    │  missions.json 갱신            │                            │
    │                                │                            │
    │                                │  [세션 종료 시점]          │
    │                                │  missions.json 확인        │
    │                                │──priority 0 미션 발견──►   │
    │                                │  block + 미션 주입         │
    │                                │                            │
    │                                │                   [개선 실행]
    │                                │                   분석→설계→구현
    │                                │                            │
    │  [결과 기록]                   │                            │
    │◄──────────────────────────────────friction.json 갱신────────│
    │◄──────────────────────────────────missions.json 갱신────────│
    │                                │                            │
```

---

## 8. Meta-Improvement (자기개선의 자기개선)

시스템의 가장 강력한 특성은 **개선 로직 자체가 개선 대상**이라는 것이다. 이것이 "재귀적" 자기개선의 핵심이다.

### 8.1 Meta-Improvement 시나리오

**시나리오 1: 자기개선 규칙 개선**
```
1. Friction 패턴: "self-improvement 미션이 유용한 변경을 거의 만들지 못함"
   - 최근 5회 개선 미션 중 4회가 의미 없는 변경
   - pattern_key: "ineffective_self_improvement"

2. friction_threshold 도달 → 개선 미션 생성
   title: "자기개선 프로세스의 효과성 개선"

3. Claude Code가 분석:
   - .claude/rules/self-improvement.md의 분석 프롬프트가 너무 일반적
   - 구체적인 분석 가이드라인이 부족

4. Claude Code가 .claude/rules/self-improvement.md를 수정:
   - 더 구체적인 분석 프롬프트 추가
   - "변경 전후 메트릭 비교" 단계 추가
   - "최소 변경 원칙" 가이드라인 추가

5. 결과: 이후 자기개선 미션의 효과가 향상됨
```

**시나리오 2: Friction 감지 메커니즘 개선**
```
1. Friction 패턴: "중요한 문제가 friction으로 감지되지 않음"
   - Owner가 수동으로 개입하는 빈도가 높음
   - pattern_key: "undetected_issues"

2. 개선 미션 생성 → Claude Code 실행

3. Claude Code가 분석:
   - system/hooks/on_stop.py의 에러 감지 범위가 좁음
   - 특정 유형의 경고가 무시되고 있음

4. Claude Code가 system/hooks/on_stop.py를 수정:
   - 새로운 friction type 추가
   - 경고 패턴 감지 로직 추가

5. 결과: 이전에 감지되지 않던 문제가 이제 friction으로 기록됨
```

**시나리오 3: 임계값 자동 조정 로직 추가**
```
1. Proactive review에서 발견:
   - friction_threshold=3이 모든 패턴에 동일하게 적용됨
   - 긴급한 패턴(crash 등)은 1회에서 즉시 대응해야 함

2. Claude Code가 state_manager.py를 수정:
   - friction type별 가중치 시스템 도입
   - crash type은 가중치 3 (1회 발생 = 임계값 즉시 도달)
   - slow type은 가중치 1 (기존과 동일)

3. 결과: friction 대응이 유형별로 차별화됨
```

### 8.2 재귀의 한계

이론적으로 무한 재귀가 가능하지만, 실용적 한계가 있다:

1. **무한 루프 방지 (섹션 6.5)**: 연속 3회 개선 후 일반 미션 복귀
2. **테스트 기반 안전망 (섹션 6.3)**: 나쁜 변경은 테스트로 걸러짐
3. **Git checkpoint (섹션 6.1)**: 어떤 변경이든 롤백 가능
4. **Owner 알림 (섹션 6.4)**: 큰 변경은 Owner가 인지

이 안전장치들 자체도 개선 대상이지만, 모든 안전장치를 한 번에 제거하는 것은 실질적으로 불가능하다 (각각 독립적으로 동작하므로).

---

## 9. 구현 분포

Self-Improvement 관련 로직이 분포하는 위치:

| 위치 | 역할 |
|------|------|
| `CLAUDE.md` | 자기개선 행동 규범. "friction을 기록하라", "개선 미션을 실행하라" |
| `.claude/rules/self-improvement.md` | 상세 자기개선 규칙. 분석 방법, 수정 절차, 안전장치 |
| `system/state_manager.py` | `add_friction()`, 임계값 판단, 개선 미션 자동 생성, friction 집계 |
| `system/hooks/on_stop.py` | 개선 미션 우선 선택, 연속 개선 제한 (MAX_CONSECUTIVE_IMPROVEMENTS) |
| `system/session_manager.py` | 미션 실행 시간 추적 (slow friction 감지), stream-json 에러 파싱 |
| `system/supervisor.py` | heartbeat 타임아웃 감지 (stuck friction), proactive interval 카운트 |
| `system/slack_client.py` | Owner 개입 감지, 자기개선 알림 발송 |
| `state/friction.json` | Friction 기록 저장소. 모든 감지/축적/해소 데이터 |
| `state/config.toml` | 모든 임계값. 자기개선으로 수정 가능 |

---

## 10. 요구사항 추적성

| 요구사항 | 구현 |
|----------|------|
| **S-1** Friction 감지 | 7가지 원천에서 감지 (섹션 1). 각 원천마다 전담 감지 주체. pattern_key로 그룹화 |
| **S-2** 자동 트리거 | friction_threshold 임계값 도달 시 priority 0 개선 미션 자동 생성 (섹션 2) |
| **S-3** 사전 개선 | proactive_improvement_interval마다 시스템 검토 미션 생성 (섹션 3) |
| **S-4** 무제한 범위 | 11가지 개선 대상. 자기개선 규칙 자체 포함 (섹션 4) |
| **S-5** 임계값 개선 | config.toml의 8개 필드 모두 수정 가능 (섹션 5) |
