# 프로젝트 디렉토리 구조 상세

> claude-automata의 모든 파일과 디렉토리에 대한 상세 설명.

---

## 전체 구조 개요

```
claude-automata/
├── pyproject.toml
├── CLAUDE.md
├── .env
├── .gitignore
├── .python-version
├── .claude/
│   ├── settings.json
│   └── rules/
│       ├── purpose.md
│       ├── mission-protocol.md
│       └── self-improvement.md
├── system/
│   ├── __init__.py
│   ├── supervisor.py
│   ├── session_manager.py
│   ├── state_manager.py
│   ├── slack_client.py
│   ├── error_classifier.py
│   ├── cognitive_load.py        # 인지 부하 트리거 + StreamAnalyzer
│   ├── watchdog.py
│   └── hooks/
│       ├── on_stop.py
│       ├── on_session_start.py
│       └── on_notification.py
├── tui/
│   ├── __init__.py
│   └── app.py
├── cli/
│   ├── __init__.py
│   └── main.py
├── state/
│   ├── purpose.json
│   ├── strategy.json
│   ├── missions.json
│   ├── friction.json
│   ├── requests.json
│   ├── sessions.json
│   ├── config.toml
│   ├── trigger-effectiveness.jsonl  # 인지 부하 트리거 효과 이력
│   ├── session-summary.md           # 세션 가중 요약 (4단계 프로토콜 출력)
│   └── archive/
│       ├── missions.jsonl
│       ├── friction.jsonl
│       └── sessions.jsonl
├── run/
│   ├── supervisor.pid
│   ├── supervisor.heartbeat
│   ├── supervisor.state           # Supervisor 크래시 복구용 상태
│   ├── current_session.json
│   ├── session-analysis.json      # StreamAnalyzer 작업 패턴 기록
│   └── hook_state.json            # Hook 실행 상태 (호출 카운터 등)
├── logs/
│   ├── supervisor.log
│   ├── session.log
│   └── slack.log
├── setup/
│   ├── launchd/
│   │   ├── com.clomia.automata.supervisor.plist
│   │   └── com.clomia.automata.watchdog.plist
│   └── slack_manifest.yaml
├── design/
│   ├── root.md
│   ├── directory-structure.md
│   ├── data-model.md
│   ├── flows.md
│   ├── requirements-traceability.md
│   ├── file-format-decisions.md
│   ├── encapsulation.md
│   └── components/
│       ├── supervisor.md
│       ├── session-manager.md
│       ├── state-manager.md
│       ├── slack-client.md
│       ├── hook-system.md
│       ├── tui.md
│       ├── error-classifier.md
│       ├── purpose-engine.md
│       ├── self-improvement.md
│       └── cognitive-load-trigger.md
├── tests/
├── poc/
└── docs/
```

---

## 1. Root Level 파일

### `pyproject.toml`

uv 네이티브 프로젝트 설정 파일. Python 3.14를 사용하며, 모든 의존성과 빌드 설정을 정의한다.

```toml
[project]
name = "claude-automata"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "textual>=8.0",
    "slack-bolt>=1.27",
    "slack-sdk>=3.41",
    "aiohttp>=3.11",
]

[project.scripts]
automata = "cli.main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**의존성 설명**:
| 패키지 | 용도 |
|--------|------|
| `textual>=8.0` | TUI 대시보드 프레임워크. Owner가 시스템 상태를 실시간 모니터링 (O-7, O-8) |
| `slack-bolt>=1.27` | Slack Socket Mode 앱 프레임워크. Owner와 비동기 통신 (O-2) |
| `slack-sdk>=3.41` | Slack API 클라이언트. 메시지 발송, 스레드 관리 |
| `aiohttp>=3.11` | 비동기 HTTP 클라이언트. Supervisor의 async 기반 네트워크 통신 |

**스크립트**:
- `automata = "cli.main:main"` — `uv run automata` 또는 설치 후 `automata`로 실행. 모든 CLI 명령의 엔트리포인트.

**빌드 시스템**: hatchling을 사용한다. `uv sync`로 의존성 설치, `uv run automata`로 실행.

### `CLAUDE.md`

Claude Code의 기본 지시문(instructions) 파일. Claude Code가 이 프로젝트 디렉토리에서 실행될 때 자동으로 읽는다.

**특성**:
- 200줄 미만을 유지한다. 상세 규칙은 `.claude/rules/`로 분리하고 `@import`로 참조.
- **자기개선 대상** (S-4): Claude Code가 자신의 지시문을 수정하여 더 효과적으로 동작할 수 있다.
- Purpose, 전략, 미션 실행 방법, 상태 파일 사용법, 품질 기준 등 핵심 행동 규범을 정의.
- 모든 에이전트/서브에이전트에 opus model, max effort 사용을 지시 (Q-1, Q-2).
- Owner 통신은 한국어로 수행하도록 지시 (O-6).

**`@import` 참조 구조**:
```markdown
# CLAUDE.md (요약)
시스템 개요, 핵심 원칙

@rules/purpose.md
@rules/mission-protocol.md
@rules/self-improvement.md

상태 파일 경로, 품질 기준, 기타 지시
```

### `.env`

환경 변수 파일. Slack 연결 정보를 저장한다.

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_CHANNEL_ID=C0123456789
```

**보안**: `.gitignore`에 포함되어 Git에 커밋되지 않는다. `automata configure` 명령으로 생성된다.

### `.gitignore`

Git 추적에서 제외할 파일/디렉토리를 정의한다.

```gitignore
# 런타임 임시 파일
run/

# 로그
logs/

# 환경 변수 (시크릿)
.env

# Python 캐시
__pycache__/
*.pyc

# 가상환경
.venv/
```

**설계 의도**: `state/` 디렉토리는 Git 추적 대상이다 (C-2). `run/`과 `logs/`는 ephemeral 데이터로 Git에서 제외한다.

### `.python-version`

uv가 사용할 Python 버전을 지정한다.

```
3.14
```

uv는 이 파일을 읽어 Python 3.14를 자동으로 설치하고 사용한다 (D-5).

---

## 2. `.claude/` 디렉토리

Claude Code 프로젝트 설정 디렉토리. Claude Code가 이 프로젝트에서 실행될 때 참조하는 설정과 규칙을 저장한다.

### `settings.json`

Claude Code 프로젝트 레벨 설정 파일. hooks 구성과 권한(permission) 설정을 정의한다.

**주요 설정 내용**:
- **Hooks**: Stop Hook (`system/hooks/on_stop.py`), SessionStart Hook (`system/hooks/on_session_start.py`), Notification Hook (`system/hooks/on_notification.py`)의 경로와 실행 조건
- **Permissions**: `--dangerously-skip-permissions`와 함께 사용되는 프로젝트 레벨 허용 설정
- **Model preferences**: opus model, max effort 강제 설정

**자기개선 대상**: Claude Code가 hook 구성을 추가/변경하거나 새로운 hook을 등록할 수 있다 (S-4).

**격리 목적 (E-1)**: 이 파일이 프로젝트 레벨 설정을 정의함으로써 Owner의 글로벌 Claude Code 설정에 영향받지 않는다.

### `rules/purpose.md`

Purpose(목적) 정의와 Purpose 관련 행동 규칙을 기술하는 modular rule 파일.

**내용**:
- Purpose의 정의 (state/purpose.json에서 읽어야 함)
- Purpose 정렬 확인 방법 — 미션이 Purpose에 부합하는지 검증하는 기준
- 목표 드리프트(goal drift) 감지 기준 — Purpose에서 벗어나는 행동 패턴 식별
- 빈 큐 시 미션 생성 지침 — Purpose를 기반으로 새로운 미션을 자율 생성하는 방법 (P-3)

CLAUDE.md에서 `@rules/purpose.md`로 참조된다.

### `rules/mission-protocol.md`

미션 실행 프로토콜을 기술하는 modular rule 파일.

**내용**:
- 미션 시작 절차: state 파일 읽기, 미션 확인, status 갱신
- 미션 실행 중 행동 규범: friction 기록, 진행 상태 갱신, 품질 기준 준수
- Blocker 처리: requests.json에 Owner 요청 생성, 다른 미션으로 전환
- 미션 완료 절차: success_criteria 확인, status 갱신, 결과 기록
- 상태 파일 읽기/쓰기 규칙: 원자적 갱신, JSON 형식 준수

CLAUDE.md에서 `@rules/mission-protocol.md`로 참조된다.

### `rules/self-improvement.md`

자기개선 규칙과 가이드라인을 기술하는 modular rule 파일.

**내용**:
- Friction 기록 방법: pattern_key 네이밍 규칙, 적절한 type 선택
- 자기개선 미션 실행 절차: 분석 → 설계 → checkpoint → 구현 → 테스트 → commit/rollback
- 개선 대상 목록과 수정 시 주의사항
- 안전장치: Git checkpoint, 테스트 실행, Owner 알림 조건
- Meta-improvement 가이드: 이 규칙 파일 자체를 수정하는 방법과 기준

**자기개선 대상 (S-4)**: 이 파일 자체가 개선 대상이다. Claude Code가 자기개선 규칙을 더 효과적으로 만들 수 있다.

CLAUDE.md에서 `@rules/self-improvement.md`로 참조된다.

---

## 3. `system/` 디렉토리

Deterministic Core 계층. Python으로 작성된 시스템 인프라 코드. 예측 가능하고 테스트 가능한 동작을 보장한다.

### `__init__.py`

system 패키지 초기화 파일. 버전 정보와 공용 import를 정의한다.

### `supervisor.py`

**클래스**: `Supervisor`
**역할**: 시스템 최상위 오케스트레이터. 모든 하위 컴포넌트를 관리하고 시스템 생명주기를 제어한다.

**핵심 메서드**:
| 메서드 | 설명 |
|--------|------|
| `async run()` | 메인 이벤트 루프. Supervisor의 진입점. 모든 비동기 태스크 관리 |
| `async _main_loop()` | 세션 반복 실행 루프. 세션 종료 → 상태 확인 → 다음 세션 시작 |
| `async _handle_session_end(result)` | 세션 종료 처리. 에러 분류, 복구 전략 실행 |
| `_create_git_checkpoint()` | 세션 시작 전 Git checkpoint 생성 (C-3) |
| `async _shutdown()` | 정상 종료 처리. 리소스 해제, 상태 저장 |

**의존성**: SessionManager, StateManager, SlackClient, ErrorClassifier

**프로세스 모델**: `asyncio` 기반 단일 프로세스. launchd LaunchAgent로 관리된다 (E-4).

**환경 변수 설정**: `ANTHROPIC_API_KEY` 제거, `CLAUDE_CODE_EFFORT_LEVEL=max`, `CLAUDE_CODE_SUBAGENT_MODEL=opus` 설정. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 제거(기본값 95% 사용).

상세 설계: [components/supervisor.md](components/supervisor.md)

### `session_manager.py`

**클래스**: `SessionManager`
**역할**: Claude Code CLI 프로세스의 생명주기를 관리한다. 세션 시작, 모니터링, 종료, 재개를 담당.

**핵심 메서드**:
| 메서드 | 설명 |
|--------|------|
| `async start_session(prompt)` | `claude -p` 프로세스 시작. stream-json 출력 파싱 시작 |
| `async monitor_session()` | 실시간 stream-json 파싱. heartbeat 갱신, 에러 감지, 진행 상태 추적 |
| `async resume_session(session_id)` | `claude --resume` 으로 기존 세션 재개 (rate limit 복구) |
| `async stop_session()` | 진행 중 세션 정상 종료 |
| `_build_session_prompt(mission)` | 미션 정보 + 상태 컨텍스트를 세션 프롬프트로 변환 |
| `_parse_stream_event(event)` | stream-json 이벤트 파싱. 에러, 결과, 도구 사용 추출 |

**의존성**: StateManager (상태 읽기/쓰기), asyncio.subprocess (프로세스 관리)

**Friction 감지**: stream-json 파싱 중 에러를 감지하여 StateManager에 friction 기록. 미션 실행 시간을 추적하여 `slow` friction 감지.

상세 설계: [components/session-manager.md](components/session-manager.md)

### `state_manager.py`

**클래스**: `StateManager`
**역할**: `state/` 디렉토리의 모든 JSON 파일을 원자적으로 읽고 쓴다. Git 체크포인트 생성. Friction 축적 및 임계값 판단.

**핵심 메서드**:
| 메서드 | 설명 |
|--------|------|
| `read_state(filename)` | state/ 파일을 읽어 dict로 반환. 파일 잠금(lock) 사용 |
| `write_state(filename, data)` | 원자적 쓰기 (write-to-temp → rename). 파일 잠금 사용 |
| `add_friction(friction)` | friction.json에 추가. 임계값 확인. 도달 시 개선 미션 반환 |
| `resolve_friction(friction_id)` | friction의 resolved_at 설정 |
| `get_next_mission()` | missions.json에서 priority 순서로 다음 pending 미션 반환 |
| `complete_mission(mission_id, result)` | 미션 완료 처리. proactive interval 확인 |
| `create_session_context()` | 모든 state 파일을 종합하여 세션 컨텍스트 문자열 생성 |
| `create_git_checkpoint(tag_prefix)` | `git add + commit + tag` 실행 |

**원자적 쓰기 패턴**:
```python
# 1. 임시 파일에 쓰기
# 2. fsync로 디스크 반영 보장
# 3. os.rename()으로 원자적 교체
```

**의존성**: 없음 (파일 시스템 직접 접근). `json`, `os`, `fcntl` 표준 라이브러리 사용.

상세 설계: [components/state-manager.md](components/state-manager.md)

### `slack_client.py`

**클래스**: `SlackClient`
**역할**: Slack Socket Mode를 통한 Owner 비동기 통신. 요청 전송, 응답 수신, 알림 발송.

**핵심 메서드**:
| 메서드 | 설명 |
|--------|------|
| `async start()` | Socket Mode 연결 시작. 이벤트 리스너 등록 |
| `async send_request(request)` | Owner에게 요청 전송. 독립 Slack 스레드 생성 (O-2) |
| `async send_notification(message, level)` | 알림 발송. level에 따라 필터링 (O-4) |
| `async _handle_message(event)` | Owner 응답 수신 처리. requests.json 갱신 |
| `async _handle_command(event)` | Owner의 명시적 명령 처리 (미션 주입 등) |

**의존성**: `slack-bolt` (Socket Mode), `slack-sdk` (API 클라이언트), StateManager

**환경 변수**: `.env`에서 `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_CHANNEL_ID` 읽기.

**Owner 개입 감지**: Owner가 예상치 못한 요청에 응답하거나 미션을 수동 주입하면 `owner_intervention` friction 생성.

상세 설계: [components/slack-client.md](components/slack-client.md)

### `error_classifier.py`

**클래스**: `ErrorClassifier`
**역할**: 세션 에러를 유형별로 분류하고 각 유형에 적합한 복구 전략을 반환한다 (E-3).

**에러 유형과 복구 전략**:
| 유형 | 패턴 | 복구 전략 |
|------|------|-----------|
| `transient` | 일시적 네트워크/API 에러 | 지수 백오프 재시도 |
| `rate_limit` | Claude API rate limit | 대기 시간 후 `--resume`으로 재개 |
| `auth` | 인증 만료/실패 | Owner에게 Slack 알림, 대기 |
| `corruption` | 상태 파일 손상 | Git checkpoint에서 복구 |
| `crash` | Claude Code 프로세스 크래시 | 새 세션 시작 |
| `network` | 네트워크 연결 끊김 | 연결 복구 대기 후 재시도 |
| `stuck` | 세션 응답 없음 (timeout) | 프로세스 kill 후 새 세션 |

**핵심 메서드**:
| 메서드 | 설명 |
|--------|------|
| `classify(error_data)` | 에러 데이터를 분석하여 에러 유형 반환 |
| `get_recovery_strategy(error_type)` | 에러 유형에 맞는 복구 전략 객체 반환 |

**의존성**: 없음 (순수 분류 로직).

상세 설계: [components/error-classifier.md](components/error-classifier.md)

### `watchdog.py`

**클래스**: `Watchdog`
**역할**: Supervisor 프로세스를 독립적으로 감시한다 (E-4). Supervisor가 죽으면 재시작한다.

**동작 방식**:
1. 별도 launchd LaunchAgent로 실행된다 (`com.clomia.automata.watchdog.plist`)
2. 주기적으로 `run/supervisor.heartbeat` 파일의 타임스탬프를 확인
3. heartbeat가 일정 시간 이상 갱신되지 않으면 Supervisor가 죽은 것으로 판단
4. `run/supervisor.pid`의 PID로 프로세스 존재 확인
5. Supervisor가 죽었으면 재시작

**핵심 메서드**:
| 메서드 | 설명 |
|--------|------|
| `run()` | 메인 감시 루프 |
| `_check_heartbeat()` | heartbeat 파일 타임스탬프 확인 |
| `_check_process(pid)` | PID의 프로세스 존재 여부 확인 |
| `_restart_supervisor()` | Supervisor 프로세스 재시작 |

**의존성**: 없음 (독립 프로세스). 표준 라이브러리만 사용.

### `hooks/` 서브디렉토리

Claude Code Hook 스크립트. `.claude/settings.json`에 등록되어 Claude Code 이벤트 시 실행된다.

#### `hooks/on_stop.py`

**역할**: Claude Code Stop Hook. 세션 종료를 가로채어 영속적 실행을 구현하는 핵심 메커니즘.

**동작 흐름**:
1. Claude Code가 종료하려 할 때 호출됨
2. `state/missions.json` 확인
3. 미완료 미션 존재 → `block` + 다음 미션 주입 (Stop Hook Loop)
4. 미션 큐 비었음 → Claude Code에 미션 생성 위임 (P-3)
5. 컨텍스트 리프레시 필요 → `allow` (새 세션으로 전환)

**입력**: stdin으로 Claude Code 세션 정보 (JSON)
**출력**: stdout으로 `{"decision": "block"|"allow", "reason": "..."}` + 미션 주입 메시지

**의존성**: StateManager (state 파일 읽기)

#### `hooks/on_session_start.py`

**역할**: Claude Code SessionStart Hook. 새 세션 시작 시 컨텍스트를 주입한다 (C-1).

**동작 흐름**:
1. 새 세션이 시작될 때 호출됨
2. `state/` 디렉토리에서 현재 상태 종합
3. 이전 세션의 결과, 현재 미션, 전략, 미해결 friction 등을 컨텍스트로 주입

**의존성**: StateManager

#### `hooks/on_notification.py`

**역할**: Claude Code Notification Hook. Claude Code의 알림 이벤트를 처리한다 (O-4).

**동작 흐름**:
1. Claude Code가 알림을 생성할 때 호출됨
2. 알림 내용을 분석하여 Slack 전송 여부 판단
3. `state/config.toml`의 `slack_notification_level`에 따라 필터링
4. 조건 충족 시 Slack으로 전달

**의존성**: SlackClient (Slack 전송), StateManager (설정 읽기)

상세 설계: [components/hook-system.md](components/hook-system.md)

---

## 4. `state/` 디렉토리

런타임 상태 파일. **Git으로 추적된다** (C-2). Claude Code와 Supervisor가 공유하는 시스템의 "메모리"이다.

모든 파일은 JSON 형식이며, StateManager를 통해 원자적으로 읽고 쓴다.

### `purpose.json`

시스템이 추구하는 영속적 방향. Owner의 초기 입력으로부터 시스템이 스스로 구성한다 (P-1).

**스키마 참조**: [data-model.md](data-model.md) — Purpose 스키마

**Git 추적**: O — Purpose는 영속적 데이터. 변경 이력이 중요하다.

**수정 주체**: Claude Code (Initialization Session에서 생성, 이후 진화 가능)

**수정 빈도**: 극히 드묾. Purpose는 본질적으로 안정적이다.

### `strategy.json`

Purpose를 추구하기 위한 현재 전략. 구체적인 접근 방식, 우선순위, 기술적 결정을 포함한다.

**스키마 참조**: [data-model.md](data-model.md) — Strategy 스키마

**Git 추적**: O — 전략 변경 이력이 자기개선의 중요한 입력이다.

**수정 주체**: Claude Code (자율 진화, 자기개선에 의한 수정)

**수정 빈도**: 가끔. 전략은 미션보다 느리게 진화한다.

**자기개선 대상 (S-4)**: Claude Code가 전략의 효과성을 분석하고 수정할 수 있다. 전략 변경 시 Owner Slack 알림 (High 영향도).

### `missions.json`

미션 큐. 실행 가능한 작업 단위의 목록. priority 기반 정렬.

**스키마 참조**: [data-model.md](data-model.md) — Mission 스키마

**Git 추적**: O — 미션 이력이 시스템 활동의 기록이다.

**수정 주체**: Claude Code (미션 생성, 상태 갱신), StateManager (자기개선 미션 자동 생성), Stop Hook (미션 선택)

**수정 빈도**: 매 미션 시작/완료 시. 가장 빈번하게 갱신되는 state 파일.

**주요 필드**: id, title, description, success_criteria, priority, status (`pending`/`in_progress`/`completed`/`blocked`), blockers, dependencies, source (`purpose`/`friction`/`owner`/`self`/`proactive`)

### `friction.json`

Friction(마찰) 누적 기록. 자기개선 시스템의 핵심 입력 데이터 (S-1).

**스키마 참조**: [data-model.md](data-model.md) — Friction 스키마

**Git 추적**: O — Friction 이력은 시스템 건전성의 시계열 기록이다.

**수정 주체**: Claude Code (자체 감지 friction), SessionManager (에러 friction), Supervisor (stuck friction), SlackClient (개입 friction), StateManager (자기개선 기록)

**수정 빈도**: friction 발생 시 추가, 해소 시 갱신. 누적 전용 — 삭제하지 않는다.

**핵심 역할**: 동일 `pattern_key`의 미해결 friction이 `friction_threshold` 이상 축적되면 자기개선 미션이 자동 생성된다 (S-2).

### `requests.json`

Owner에게 보낸 요청과 응답을 추적한다. 각 요청은 Slack 스레드와 1:1 매핑 (O-2).

**스키마 참조**: [data-model.md](data-model.md) — Request 스키마

**Git 추적**: O — 요청/응답 이력이 시스템-Owner 상호작용의 기록이다.

**수정 주체**: Claude Code (요청 생성), SlackClient (응답 수신 시 갱신)

**수정 빈도**: Blocker 발생/해소 시.

**주요 필드**: id, mission_id (관련 미션), question (Owner에게 보낸 질문), response (Owner 응답), slack_thread_ts (Slack 스레드 ID), status (`pending`/`answered`/`expired`)

### `sessions.json`

세션 실행 이력. 각 Claude Code 세션의 시작/종료 시간, 실행한 미션, 결과를 기록한다.

**스키마 참조**: [data-model.md](data-model.md) — Session 스키마

**Git 추적**: O — 세션 이력은 시스템 가동 기록이자 성능 분석 입력이다.

**수정 주체**: SessionManager (세션 시작/종료 시 기록)

**수정 빈도**: 매 세션 시작/종료 시.

**주요 필드**: id, started_at, ended_at, mission_ids (실행한 미션 목록), result (`success`/`error`/`timeout`/`rate_limit`), error_type, compaction_count

### `config.toml`

동적 설정. 모든 임계값과 파라미터를 저장한다. 자기개선의 대상 (S-5).

**스키마 참조**: [data-model.md](data-model.md) — Config 스키마

**Git 추적**: O — 설정 변경 이력이 자기개선 활동의 기록이다.

**수정 주체**: Claude Code (자기개선에 의한 수정), `automata configure` (초기 설정)

**수정 빈도**: 드묾. 자기개선 시에만 변경된다.

**필드 목록**:
| 필드 | 기본값 | 설명 |
|------|--------|------|
| `friction_threshold` | `3` | Friction 축적 임계값 (S-2) |
| `proactive_improvement_interval` | `10` | 사전 검토 주기 (S-3) |
| `context_refresh_after_compactions` | `5` | 컨텍스트 리프레시 조건 |
| `goal_drift_check_interval` | `20` | Purpose 정렬 확인 주기 |
| `session_timeout_minutes` | `120` | 세션 타임아웃 |
| `max_consecutive_failures` | `3` | 연속 실패 에스컬레이션 임계값 |
| `slack_notification_level` | `"warning"` | Slack 알림 수준 |
| `mission_idle_generation_count` | `3` | 빈 큐 시 미션 생성 수 |

### `archive/` 디렉토리

완료/해소된 레코드를 JSONL(JSON Lines) 형식으로 보관하는 아카이브 디렉토리. 활성 state 파일이 무한히 커지는 것을 방지하면서 전체 이력을 보존한다.

**Git 추적**: O -- 시스템 이력의 영구 기록.

**파일 목록**:
| 파일 | 내용 | 아카이브 조건 |
|------|------|---------------|
| `missions.jsonl` | 완료된 미션 (`status: "completed"` 또는 `"failed"`) | 미션 완료 시 활성 파일에서 이동 |
| `friction.jsonl` | 해소된 friction (`resolved_at` 존재) | friction 해소 시 활성 파일에서 이동 |
| `sessions.jsonl` | 종료된 세션 기록 | 세션 종료 후 일정 기간 경과 시 이동 |

**형식**: 각 줄이 하나의 독립된 JSON 객체인 JSONL. append-only로 기록하여 원자적 쓰기가 간단하고 파일 손상 시에도 손실을 최소화한다.

**순환 관리**: Supervisor가 주기적으로 아카이브 파일 크기를 확인하고, 임계값 초과 시 오래된 레코드를 별도 파일(`{name}.{timestamp}.jsonl`)로 회전시킨다.

---

## 5. `run/` 디렉토리

런타임 임시 파일. **`.gitignore`에 포함되어 Git에서 제외된다.** Supervisor가 실행 중에 생성하고 관리한다.

### `supervisor.pid`

Supervisor 프로세스의 PID를 저장하는 잠금 파일. 중복 실행을 방지한다.

**생성**: Supervisor 시작 시 생성. PID를 기록하고 파일 잠금 획득.
**삭제**: Supervisor 종료 시 삭제.
**사용**: Watchdog이 Supervisor 생존 여부 확인에 사용. `automata status`가 실행 상태 확인에 사용.

### `supervisor.heartbeat`

Supervisor의 heartbeat 타임스탬프 파일. Watchdog이 Supervisor 생존 확인에 사용한다 (E-4).

**갱신 주기**: Supervisor 메인 루프에서 주기적으로 갱신 (수 초 간격).
**감시**: Watchdog이 이 파일의 mtime을 확인하여 Supervisor 정상 동작 판단.

### `current_session.json`

현재 실행 중인 Claude Code 세션의 정보. TUI가 실시간 상태를 표시하는 데 사용한다.

**내용**: 세션 ID, 시작 시간, 현재 미션, 진행 상태, 마지막 활동 시간.
**갱신**: SessionManager가 stream-json 이벤트를 처리할 때마다 갱신.
**소비자**: TUI (실시간 대시보드), `automata status` (상태 출력).

---

## 6. `logs/` 디렉토리

로그 파일. **`.gitignore`에 포함되어 Git에서 제외된다.** Python의 `logging` 모듈과 `RotatingFileHandler`로 관리된다.

### `supervisor.log`

Supervisor 데몬의 주요 로그. 시스템 수준 이벤트, 에러 복구, 세션 관리, 상태 변경을 기록한다.

**로그 레벨**: DEBUG 이상 모든 로그.
**로테이션**: `RotatingFileHandler`로 파일 크기 제한. 일정 크기 초과 시 자동 로테이션.

### `session.log`

Claude Code 세션 관련 로그. 세션 시작/종료, stream-json 이벤트, 에러, Claude Code의 도구 사용 이력을 기록한다.

**로그 레벨**: INFO 이상.
**로테이션**: 크기 기반 자동 로테이션.

### `slack.log`

Slack 통신 로그. 메시지 발송/수신, Socket Mode 연결 상태, API 에러를 기록한다.

**로그 레벨**: INFO 이상.
**로테이션**: 크기 기반 자동 로테이션.

---

## 7. `setup/` 디렉토리

시스템 설정 및 설치 관련 파일. `automata configure`와 `automata start` 명령에서 사용된다.

### `launchd/com.clomia.automata.supervisor.plist`

Supervisor LaunchAgent 템플릿. `automata start` 명령이 이 템플릿을 복사하여 `~/Library/LaunchAgents/`에 설치한다.

**주요 설정**:
- `KeepAlive: true` — Supervisor 프로세스가 죽으면 launchd가 자동 재시작 (E-2)
- `WorkingDirectory` — 프로젝트 루트 디렉토리
- `ProgramArguments` — `uv run python -m system.supervisor` 실행
- `StandardOutPath` / `StandardErrorPath` — `logs/` 디렉토리
- `EnvironmentVariables` — `.env`에서 읽은 환경 변수

### `launchd/com.clomia.automata.watchdog.plist`

Watchdog LaunchAgent 템플릿. Supervisor와 독립적으로 실행되는 감시 프로세스 (E-4).

**주요 설정**:
- `KeepAlive: true` — Watchdog 자체도 launchd가 보호
- `StartInterval` — 감시 주기 (초)
- `ProgramArguments` — `uv run python -m system.watchdog` 실행

**이중 보호 구조**: launchd가 Supervisor를 보호하고, Watchdog이 Supervisor의 heartbeat를 감시한다. 두 메커니즘이 독립적으로 동작하여 신뢰성을 높인다.

### `slack_manifest.yaml`

Slack 앱 매니페스트. Owner가 Slack 앱을 쉽게 생성할 수 있도록 사전 구성된 설정 파일.

**내용**:
- 앱 이름, 설명
- Socket Mode 활성화
- 필요한 OAuth scopes: `chat:write`, `channels:history`, `channels:read` 등
- 이벤트 구독: `message.channels` 등

**사용법**: `automata configure` 시 이 매니페스트를 참조하여 Slack 앱 설정을 안내하거나, Slack API로 앱을 자동 생성.

---

## 8. `tui/` 디렉토리

Textual 기반 TUI(Terminal User Interface) 애플리케이션. Owner가 시스템 상태를 실시간으로 모니터링하고 상호작용한다 (O-7, O-8).

### `__init__.py`

tui 패키지 초기화 파일.

### `app.py`

**클래스**: `AutomataApp(textual.app.App)`
**역할**: Textual 대시보드 메인 애플리케이션.

**화면 구성**:
| 패널 | 내용 |
|------|------|
| Dashboard | 시스템 상태 요약 — 현재 미션, 세션 상태, Purpose |
| Queue | 미션 큐 목록. 각 미션의 priority, status, title 표시 |
| Logs | 실시간 로그 스트림. supervisor.log + session.log 테일링 |
| Slack | 미해결 Owner 요청 목록. TUI에서 직접 응답 가능 |

**상호작용 기능 (O-8)**:
- 미션 수동 주입 (텍스트 입력)
- Owner 요청에 직접 응답
- 시스템 일시 정지/재개

**데이터 소스**: `state/` 디렉토리 파일과 `run/current_session.json`을 주기적으로 읽어 화면 갱신.

**실행**: `uv run automata tui` 또는 `automata tui`

상세 설계: [components/tui.md](components/tui.md)

---

## 9. `cli/` 디렉토리

CLI 인터페이스. `automata` 명령어의 엔트리포인트와 서브커맨드를 정의한다.

### `__init__.py`

cli 패키지 초기화 파일.

### `main.py`

**함수**: `main()`
**역할**: `automata` 명령어 엔트리포인트. `pyproject.toml`의 `[project.scripts]`에서 `automata = "cli.main:main"`으로 등록.

**서브커맨드**:
| 커맨드 | 설명 |
|--------|------|
| `automata configure` | 초기 설정. Slack 토큰 입력, 목적 입력, `.env` 생성, Slack 연결 검증 |
| `automata start` | LaunchAgent 설치 + Supervisor 시작. 시스템 가동 |
| `automata stop` | 시스템 중지 + LaunchAgent 제거 |
| `automata restart` | stop → start 순차 실행 |
| `automata status` | 현재 상태 출력. Supervisor 실행 여부, 현재 미션, 세션 상태 |
| `automata tui` | Textual TUI 실행 |
| `automata logs [--follow]` | 로그 출력. `--follow`로 실시간 테일링 |
| `automata inject "<mission>"` | 미션 큐에 수동 주입. missions.json에 추가 |
| `automata reset [checkpoint]` | 지정 체크포인트로 롤백. 기본: 마지막 체크포인트 |
| `automata purpose` | 현재 Purpose 출력 |

**의존성**: `argparse` (CLI 파싱), StateManager (상태 접근), 각 서브커맨드별 시스템 모듈

---

## 10. `tests/` 디렉토리

pytest 기반 테스트 코드. `uv run pytest`로 실행.

**구조**:
```
tests/
├── conftest.py                # 공용 fixtures
├── test_state_manager.py      # StateManager 단위 테스트
├── test_error_classifier.py   # ErrorClassifier 단위 테스트
├── test_session_manager.py    # SessionManager 단위 테스트
├── test_hooks.py              # Hook 스크립트 테스트
├── test_slack_client.py       # SlackClient 테스트 (모킹)
└── test_integration.py        # 통합 테스트
```

**테스트 대상**: 주로 Deterministic Core (`system/`) 코드. 결정론적 로직은 테스트 가능하다.

**자기개선과의 관계**: 자기개선 시 테스트가 존재하면 변경 후 자동 실행. 테스트 실패 시 롤백 (안전장치). 테스트 코드 자체도 자기개선 대상 (S-4).

---

## 11. `poc/` 디렉토리

Proof of Concept 코드. 설계 검증을 위한 실험 코드. **프로덕션 시스템의 일부가 아니다.**

**현재 PoC**:
- `stop_hook/` — Stop Hook Loop 패턴 검증
- `state_persistence/` — 상태 파일 기반 컨텍스트 보존 검증

각 PoC는 독립적으로 실행 가능하며, 자체 `CLAUDE.md`를 가질 수 있다.

---

## 12. `design/` 디렉토리

설계 문서 모음. 시스템의 아키텍처, 컴포넌트, 데이터 모델, 흐름을 기술한다.

**구조**:
```
design/
├── root.md                          # 전체 설계 개요 (루트 문서)
├── directory-structure.md             # 디렉토리 구조 상세 (이 문서)
├── data-model.md                      # 모든 데이터 스키마
├── flows.md                           # 핵심 흐름 시퀀스 다이어그램
├── requirements-traceability.md       # 요구사항 ↔ 설계 매핑
├── encapsulation.md                  # 격리 설계
├── file-format-decisions.md          # 파일 형식 결정
└── components/                        # 컴포넌트별 상세 설계
    ├── supervisor.md
    ├── session-manager.md
    ├── state-manager.md
    ├── slack-client.md
    ├── hook-system.md
    ├── tui.md
    ├── error-classifier.md
    ├── cognitive-load-trigger.md
    ├── purpose-engine.md
    └── self-improvement.md
```

**문서 관계**:
- `root.md`가 루트 문서. 시스템 개요와 각 하위 문서 링크.
- 하위 문서들은 독립적으로 읽을 수 있으나, root.md에서 전체 맥락을 먼저 파악하는 것을 권장.
- 설계 문서는 "에이전트가 읽고 구현할 수 있는 수준"으로 작성.

---

## 13. `docs/` 디렉토리

참고 문서 모음. 요구사항, 조사 결과, 기술 참고 자료를 저장한다.

**현재 문서**:
- `ai-automata-definition.md` — AI Automata 정의
- `claude-automata-requirements.md` — 요구사항 명세
- `llm-persistent-agent-research.md` — LLM 영속 에이전트 관련 조사
- `uv-and-claude-max-research.md` — uv, Claude Max 기술 조사
- `claude-code-automation-patterns.md` — Claude Code 자동화 패턴 조사

---

## 14. 파일 관리 정책 요약

| 디렉토리 | Git 추적 | 수정 주체 | 성격 |
|----------|----------|-----------|------|
| `.claude/` | O | Claude Code, 시스템 | 프로젝트 설정 |
| `system/` | O | Claude Code (자기개선) | 시스템 코드 |
| `state/` | O | Claude Code, StateManager | 런타임 상태 (영속) |
| `run/` | X | Supervisor | 런타임 임시 |
| `logs/` | X | Python logging | 로그 |
| `setup/` | O | 초기 설정 시 | 설정 템플릿 |
| `tui/` | O | Claude Code (자기개선) | TUI 코드 |
| `cli/` | O | Claude Code (자기개선) | CLI 코드 |
| `tests/` | O | Claude Code (자기개선) | 테스트 코드 |
| `design/` | O | 설계 시 | 설계 문서 |
| `docs/` | O | 조사 시 | 참고 문서 |
| `poc/` | O | 실험 시 | PoC 코드 |
