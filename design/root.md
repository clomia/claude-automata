# claude-automata 설계서

> **AI Automata System** — 목적을 가지고 AI를 영속적으로 실행시키는 재귀적 자기개선 시스템

이 문서는 claude-automata의 전체 설계를 기술한다. 에이전트가 이 문서와 하위 문서를 읽고 구현할 수 있는 수준으로 작성되었다.

---

## 1. 시스템 개요

claude-automata는 Claude Code CLI를 AI 엔진으로 사용하는 자율 시스템이다. Supervisor(Python 데몬)가 Claude Code 세션을 영속적으로 관리하고, Owner와는 Slack으로 비동기 통신하며, 시스템 스스로가 자신을 개선한다.

### 1.1 핵심 아키텍처 패턴: Deterministic Core + Agentic Shell

| 레이어 | 구현체 | 책임 |
|--------|--------|------|
| **Deterministic Core** | Python Supervisor | 세션 생명주기, 상태 관리, Slack 통신, 에러 복구, 프로세스 감시 |
| **Agentic Shell** | Claude Code 세션 | 미션 실행, 코드 생성, 의사결정, 자기 개선, 미션 생성 |

Deterministic Core는 예측 가능하고 테스트 가능한 인프라를 제공한다. Agentic Shell은 그 위에서 지능적 작업을 수행한다.

### 1.2 시스템 토폴로지

```
┌──────────────────────────────────────────────────────────┐
│                        macOS                             │
│                                                          │
│  ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │   launchd    │    │         TUI (Textual)           │  │
│  │ LaunchAgent  │    │  ┌─────┬──────┬─────┬───────┐  │  │
│  │  KeepAlive   │    │  │Dash │Queue │Logs │ Slack │  │  │
│  └──────┬───┬──┘    │  └─────┴──────┴─────┴───────┘  │  │
│         │   │        └──────────────┬──────────────────┘  │
│         │   │                       │ (reads state files) │
│         │   │                       │                     │
│  ┌──────▼───┼───────────────────────┼──────────┐         │
│  │          │     Supervisor        │          │         │
│  │  ┌───────▼─────┐  ┌─────────────▼───────┐  │         │
│  │  │   Watchdog   │  │   Session Manager   │  │         │
│  │  │  (heartbeat) │  │  (start/stop/resume)│  │         │
│  │  └──────────────┘  └─────────┬───────────┘  │         │
│  │                              │               │         │
│  │  ┌──────────────┐  ┌────────▼────────────┐  │         │
│  │  │ Slack Client │  │   State Manager     │  │         │
│  │  │ (Socket Mode)│  │  (atomic file I/O)  │  │         │
│  │  └──────────────┘  └─────────────────────┘  │         │
│  └──────────────────────┬──────────────────────┘         │
│                         │                                 │
│                    ┌────▼─────────────────────┐           │
│                    │    Claude Code CLI        │           │
│                    │  ┌─────────────────────┐ │           │
│                    │  │ opus[1m] max effort │ │           │
│                    │  │ Stop Hook (loop)    │ │           │
│                    │  │ CLAUDE.md (purpose) │ │           │
│                    │  │ State Files (memory)│ │           │
│                    │  └─────────────────────┘ │           │
│                    └──────────────────────────┘           │
│                                                          │
│                    ┌──────────────────────────┐           │
│                    │      Git Repository      │           │
│                    │  state/ logs/ code/      │           │
│                    │  checkpoints (tags)      │           │
│                    └──────────────────────────┘           │
└──────────────────────────────────────────────────────────┘
                          │
                          │ Slack Socket Mode (WebSocket)
                          ▼
                   ┌──────────────┐
                   │    Slack     │
                   │  Workspace   │
                   └──────────────┘
```

### 1.3 핵심 설계 결정

| 결정 | 선택 | 근거 |
|------|------|------|
| 세션 관리 | 하이브리드 (Stop Hook Loop + Fresh Session) | 단일 세션 내 컨텍스트 유지 + 크래시 복구 |
| 상태 저장 | 파일 시스템 + Git | 요구사항 C-2 (파일 관리), C-3 (복구 지점) |
| 프로세스 감시 | launchd LaunchAgent + Watchdog | 요구사항 E-4 (독립적 감시) |
| Owner 통신 | Slack Socket Mode (slack-bolt async) | 요구사항 O-2 (Slack), 방화벽 내부 동작 |
| TUI | Textual v8+ | 요구사항 O-7, O-8 (Textual 지정) |
| 패키지 관리 | uv + Python 3.14 | 요구사항 D-5 |
| 인증 | Claude Max 구독 (OAuth) | 요구사항 D-6 |
| 모델 | opus[1m] max effort 전용 | 요구사항 Q-1 |
| 파일 형식 | 용도별 최적 형식: JSON(운영 상태) + TOML(설정) + Markdown(지시) + JSONL(아카이브) | 각 형식의 강점을 활용 |

---

## 2. 디렉토리 구조

상세: [directory-structure.md](directory-structure.md)

```
claude-automata/
├── pyproject.toml                 # uv 프로젝트 설정
├── CLAUDE.md                      # Claude Code 지시문 (시스템이 자기개선)
├── .claude/
│   ├── settings.json              # 시스템 전용 Claude Code 설정
│   └── rules/                     # 모듈별 지시 파일
│       ├── purpose.md             # Purpose 정의
│       ├── mission-protocol.md    # Mission 실행 프로토콜
│       └── self-improvement.md    # 자기개선 규칙
├── system/                        # Deterministic Core
│   ├── __init__.py
│   ├── supervisor.py              # Supervisor 메인 데몬
│   ├── session_manager.py         # Claude Code 세션 관리
│   ├── state_manager.py           # 상태 파일 관리
│   ├── slack_client.py            # Slack 통신
│   ├── error_classifier.py        # 에러 분류 및 복구 전략
│   ├── cognitive_load.py          # 인지 부하 트리거 + StreamAnalyzer
│   ├── watchdog.py                # Watchdog 데몬
│   └── hooks/                     # Hook 스크립트
│       ├── on_stop.py             # Stop Hook
│       ├── on_session_start.py    # SessionStart Hook
│       └── on_notification.py     # Notification Hook
├── tui/                           # TUI 애플리케이션
│   ├── __init__.py
│   └── app.py                     # Textual 대시보드
├── cli/                           # CLI 인터페이스
│   ├── __init__.py
│   └── main.py                    # `automata` 명령어
├── state/                         # 런타임 상태 (Git 추적)
│   ├── purpose.json               # 구성된 Purpose
│   ├── strategy.json              # 현재 전략
│   ├── missions.json              # Mission 큐
│   ├── friction.json              # Friction 로그
│   ├── requests.json              # Owner 요청 추적
│   ├── sessions.json              # 세션 이력
│   ├── config.toml                # 동적 설정 (임계값 등)
│   ├── trigger-effectiveness.jsonl # 인지 부하 트리거 효과 이력
│   └── session-summary.md         # 세션 가중 요약 (4단계 프로토콜 출력)
├── state/archive/                 # 아카이브 (JSONL, Git 추적)
│   ├── missions-YYYY-QN.jsonl     # 완료 미션 아카이브 (분기별)
│   ├── friction-YYYY-QN.jsonl     # 해소 friction 아카이브 (분기별)
│   └── sessions-YYYY-MM.jsonl     # 세션 이력 아카이브 (월별)
├── run/                           # 런타임 임시 파일 (Git 무시)
│   ├── supervisor.pid             # PID 잠금 파일
│   ├── supervisor.heartbeat       # Heartbeat 파일
│   ├── supervisor.state           # Supervisor 크래시 복구용 상태
│   ├── current_session.json       # 현재 세션 정보
│   ├── session-analysis.json      # StreamAnalyzer 작업 패턴 기록
│   └── hook_state.json            # Hook 실행 상태 (호출 카운터 등)
├── logs/                          # 로그 (Git 무시)
│   ├── supervisor.log
│   ├── session.log
│   └── slack.log
├── setup/                         # 셋업
│   ├── launchd/                   # LaunchAgent plist 템플릿
│   │   ├── com.clomia.automata.supervisor.plist
│   │   └── com.clomia.automata.watchdog.plist
│   └── slack_manifest.yaml        # Slack 앱 매니페스트
├── design/                        # 설계 문서 (이 디렉토리)
├── poc/                           # PoC 코드
└── tests/                         # 테스트
```

---

## 3. 데이터 모델

상세: [data-model.md](data-model.md)

### 3.1 핵심 데이터 엔티티

| 엔티티 | 파일 | 설명 |
|--------|------|------|
| Purpose | `state/purpose.json` | 시스템의 영속적 방향 |
| Strategy | `state/strategy.json` | Purpose를 추구하는 현재 전략 |
| Mission | `state/missions.json` | 실행 가능한 작업 단위 큐 |
| Friction | `state/friction.json` | 마찰 기록 (자기개선 입력) |
| Request | `state/requests.json` | Owner 요청/응답 추적 |
| Session | `state/sessions.json` | 세션 실행 이력 |
| Config | `state/config.toml` | 동적 설정 (임계값, 파라미터) |

### 3.2 핵심 스키마 요약

**Purpose** (`state/purpose.json`):
```json
{
  "raw_input": "Owner의 원문 입력",
  "purpose": "추출된 영속적 방향",
  "domain": "도메인 영역",
  "constructed_at": "2026-03-25T10:00:00Z",
  "last_evolved_at": "2026-03-25T10:00:00Z"
}
```

**Mission** (`state/missions.json`):
```json
{
  "missions": [
    {
      "id": "M-001",
      "title": "미션 제목",
      "description": "상세 설명",
      "success_criteria": ["기준1", "기준2"],
      "priority": 1,
      "status": "pending",
      "blockers": [],
      "dependencies": [],
      "created_at": "2026-03-25T10:00:00Z",
      "source": "purpose|friction|owner|self"
    }
  ],
  "next_id": 2
}
```

---

## 4. 컴포넌트 설계

각 컴포넌트의 상세 설계는 `components/` 디렉토리에 있다.

| 컴포넌트 | 문서 | 핵심 책임 |
|----------|------|-----------|
| Supervisor | [supervisor.md](components/supervisor.md) | 시스템 최상위 오케스트레이터. 모든 컴포넌트 관리 |
| Session Manager | [session-manager.md](components/session-manager.md) | Claude Code 프로세스 생명주기 관리 |
| State Manager | [state-manager.md](components/state-manager.md) | 파일 기반 상태 영속화, 원자적 쓰기, Git 체크포인트 |
| Slack Client | [slack-client.md](components/slack-client.md) | Owner 비동기 통신, 스레드 관리, 알림 |
| Hook System | [hook-system.md](components/hook-system.md) | Stop/SessionStart/Notification Hook |
| TUI | [tui.md](components/tui.md) | Textual 기반 실시간 모니터링 대시보드 |
| Error Classifier | [error-classifier.md](components/error-classifier.md) | 에러 분류 및 복구 전략 선택 |
| Purpose Engine | [purpose-engine.md](components/purpose-engine.md) | Purpose 구성, 전략/미션 생성, 목표 드리프트 방지 |
| Self-Improvement | [self-improvement.md](components/self-improvement.md) | Friction 감지, 축적, 자기개선 트리거 |
| Cognitive Load Trigger | [cognitive-load-trigger.md](components/cognitive-load-trigger.md) | 인지 부하 극대화. 다단계 프로토콜 + Stop hook agent 외부 트리거 (Q-3, Q-4) |

---

## 5. 핵심 흐름

상세: [flows.md](flows.md)

### 5.1 부트스트랩 (최초 실행)

```
[Owner] clone 템플릿 → uv sync → uv run automata configure
                                      │
                          ┌────────────▼─────────────┐
                          │ 1. Slack 토큰 입력        │
                          │ 2. 초기 목적 입력 (자연어) │
                          │ 3. Slack 연결 검증         │
                          │ 4. .env 생성              │
                          └────────────┬─────────────┘
                                       │
                          uv run automata start
                                       │
                          ┌────────────▼─────────────┐
                          │ LaunchAgent 설치          │
                          │ Supervisor 시작           │
                          └────────────┬─────────────┘
                                       │
                          ┌────────────▼─────────────┐
                          │ Initialization Session    │
                          │ (Claude Code 첫 세션)     │
                          │                          │
                          │ 1. Owner 입력 읽기        │
                          │ 2. Purpose 구성 (P-1)     │
                          │ 3. 도메인 구성 생성 (P-2) │
                          │    - 전략, 규칙, 스킬     │
                          │    - 초기 Mission 큐      │
                          │    - CLAUDE.md 생성       │
                          │ 4. 결과를 state/ 에 저장  │
                          └────────────┬─────────────┘
                                       │
                          ┌────────────▼─────────────┐
                          │ Working Session 시작      │
                          │ (정상 운영 루프 진입)     │
                          └──────────────────────────┘
```

### 5.2 정상 운영 루프

```
┌─────────────────────────────────────────────────────┐
│                  Supervisor Loop                     │
│                                                     │
│  [Git Checkpoint] → tag: checkpoint-{timestamp}     │
│        │                                            │
│        ▼                                            │
│  [Prepare Session]                                  │
│    - state/ 파일에서 다음 미션 선택                  │
│    - 세션 프롬프트 생성                             │
│        │                                            │
│        ▼                                            │
│  [Launch Claude Code]                               │
│    claude -p "<prompt>"                             │
│      --dangerously-skip-permissions                 │
│      --model opus                                   │
│      --effort max                                   │
│      --output-format stream-json                    │
│        │                                            │
│        ▼                                            │
│  [Monitor Session] ← stream-json 실시간 파싱        │
│    │                                                │
│    ├── 정상 실행 중                                  │
│    │   - heartbeat 갱신                             │
│    │   - TUI 상태 갱신                              │
│    │   - Slack 상태 알림 (필요시)                    │
│    │                                                │
│    ├── Stop Hook 발동                               │
│    │   - missions.json 확인                         │
│    │   - 미완료 미션 있음 → block + 다음 미션 주입  │
│    │   - 미션 큐 비었음 → Claude에 미션 생성 위임   │
│    │   - 컨텍스트 리프레시 필요 → allow (새 세션)   │
│    │                                                │
│    ├── 세션 정상 종료                                │
│    │   → 결과 기록, 다음 세션 시작                  │
│    │                                                │
│    ├── Rate Limit                                   │
│    │   → 대기 후 --resume으로 재개                  │
│    │                                                │
│    ├── 프로세스 크래시                               │
│    │   → 에러 분류 → 복구 전략 실행                 │
│    │                                                │
│    └── Slack 요청 수신 (Owner 응답)                  │
│        → Blocker 해제, 미션 재개                    │
│                                                     │
│  [Loop continues...]                                │
└─────────────────────────────────────────────────────┘
```

### 5.3 자기개선 루프

```
[Friction 감지]
  ├── 에러 반복 (같은 패턴 N회)
  ├── 미션 실패 (성공 기준 미달)
  ├── 품질 이슈 (테스트 실패)
  ├── 성능 이슈 (미션 소요 시간 초과)
  └── Owner 개입 (비정상적 수동 조치)
      │
      ▼
[Friction 기록] → state/friction.json
      │
      ▼
[축적 임계값 확인]
  config.toml.friction_threshold (기본: 3)
      │
      ├── 임계값 미달 → 계속 운영
      │
      └── 임계값 도달 →
          │
          ▼
    [자기개선 Mission 자동 생성]
      priority: 0 (최고 우선순위)
      │
      ▼
    [Claude Code가 개선 실행]
      개선 대상 (제한 없음):
      ├── CLAUDE.md (지시문)
      ├── .claude/rules/ (규칙)
      ├── state/strategy.json (전략)
      ├── state/config.toml (임계값)
      ├── system/hooks/ (훅 스크립트)
      ├── system/ (Supervisor 코드)
      └── tui/ (TUI 코드)
      │
      ▼
    [Git Commit + Friction 해소 기록]

[주기적 사전 개선] (friction 없어도)
  config.toml.proactive_improvement_interval (기본: 매 10미션)
      │
      ▼
    [Claude Code가 시스템 전반 검토]
      → 개선점 발견 시 개선 Mission 생성
```

---

## 6. 세션 관리 상세

### 6.1 하이브리드 세션 패턴

시스템은 두 가지 세션 패턴을 상황에 따라 사용한다:

**Pattern A: Stop Hook Loop (기본)**
- 단일 `claude -p` 호출 내에서 Stop Hook이 종료를 방지하며 연속 실행
- 동일 컨텍스트 내에서 관련 미션을 연속 처리
- 컨텍스트 효율이 높음 (이전 작업 결과가 컨텍스트에 존재)

**Pattern B: Fresh Session (복구/갱신)**
- 새로운 `claude -p` 호출. CLAUDE.md + SessionStart Hook이 컨텍스트 주입
- 사용 시점:
  - 세션 크래시 후 복구
  - Rate limit 후 세션 재개 불가 시
  - N회 compaction 후 컨텍스트 리프레시
  - 목표 드리프트 감지 시
  - 미션 유형이 크게 달라질 때

### 6.2 세션 시작 명령

```bash
claude -p "<session_prompt>" \
  --dangerously-skip-permissions \
  --model opus \
  --effort max \
  --output-format stream-json \
  --setting-sources project,local \
  --strict-mcp-config \
  --mcp-config '{}' \
  2>&1
```

**환경 변수** (Supervisor가 설정):
```bash
CLAUDE_CODE_EFFORT_LEVEL=max                   # Thinking/Effort 고정 (User /config 무시)
CLAUDE_CODE_SUBAGENT_MODEL=opus                # 서브에이전트 모델 고정
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1              # User auto-memory 비활성화
DISABLE_AUTOUPDATER=1                          # 자동 업데이트 방지
# CLAUDE_AUTOCOMPACT_PCT_OVERRIDE 미설정 (기본값 95%)
# ANTHROPIC_API_KEY 제거 (Claude Max 구독 사용)
```

### 6.3 세션 프롬프트 구조

Supervisor가 미션 프롬프트를 생성할 때, 인지 부하 극대화를 위한 4단계 실행 프로토콜을 포함한다. 상세: [cognitive-load-trigger.md](components/cognitive-load-trigger.md) §2.

```text
당신은 claude-automata 시스템의 AI 에이전트입니다.

## 현재 상태
{state_manager.create_session_context() 출력}

## 미션: {mission.id} {mission.title}
{mission.description}
{mission.success_criteria}

## 실행 프로토콜 (각 단계를 건너뛰지 마라)

**1단계 — 실행**: 성공 기준을 달성하라.

**2단계 — 검증**: 성공 기준 각 항목을 개별적으로 대조 확인하라.
{인지 부하 모듈이 생성한 미션 특화 검증 지시}

**3단계 — 미탐색 영역**: 이 접근법의 약점 3가지를 식별하고 대응하라.
{인지 부하 모듈이 생성한 미션 특화 확장 지시}

**4단계 — 요약**: state/session-summary.md에 기록하라:
  불확실했던 결정, 기각한 대안, 타협한 부분
```

---

## 7. 인증 및 격리

### 7.1 Claude Max 인증

요구사항 D-6에 따라 Claude Max 구독을 사용한다.

- Supervisor는 `ANTHROPIC_API_KEY`를 환경에서 **제거**한다
- Claude Code는 OAuth 기반 Claude Max 구독을 사용한다
- `claude login`이 사전에 완료되어 있어야 한다 (D-6)
- Rate limit 시 Claude Code 내부 retry + Supervisor 외부 감시

### 7.2 실행 격리 (E-1)

상세: [encapsulation.md](encapsulation.md)

**완전한 설정 격리는 Claude Code 자체적으로 불가능하다.** Claude Code는 격리 실행을 위해 설계되지 않았으며, 유일한 완전 격리 메커니즘(`--bare`)은 Claude Max 구독(D-6)과 양립 불가하다. 따라서 **실질적으로 영향이 큰 항목을 공식 메커니즘으로 고정**하고, 나머지는 수용하는 실용적 전략을 채택한다.

#### Tier 1: CLI 플래그 + 환경 변수 (신뢰도 높음, 핵심 보장)

공식 문서에 우선순위가 명시된 메커니즘으로 핵심 동작을 고정한다:

```bash
# CLI 플래그 (최고 우선순위)
claude -p "<prompt>" \
  --model opus --effort max \
  --dangerously-skip-permissions \
  --output-format stream-json \
  --strict-mcp-config --mcp-config '{}'
```

```bash
# 환경 변수 (settings.json보다 우선)
CLAUDE_CODE_EFFORT_LEVEL=max          # /config 변경 무시
CLAUDE_CODE_SUBAGENT_MODEL=opus       # 서브에이전트 모델 고정
                                      # CLAUDE_AUTOCOMPACT_PCT_OVERRIDE 미설정 (기본값 95% 사용)
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1     # User auto-memory 차단
DISABLE_AUTOUPDATER=1                 # 자동 업데이트 방지
```

환경 상속: `os.environ.copy()` 기반으로 위 변수를 덮어쓰고, `ANTHROPIC_API_KEY`와 `ANTHROPIC_MODEL`만 제거한다.

#### Tier 2: 보조 방어 (신뢰도 중간)

| 메커니즘 | 목적 | 한계 |
|----------|------|------|
| `--setting-sources project,local` | User settings 차단 | 차단 범위 불완전할 수 있음. `~/.claude.json` 미차단 |
| `claudeMdExcludes` | 상위 CLAUDE.md 차단 | 경로 하드코딩. 프로젝트 이동 시 재설정 필요 |

#### 격리 포기 항목

| 항목 | 이유 |
|------|------|
| `~/.claude.json` | OAuth 인증에 필수. 격리 불가 |
| User MCP 서버 | `--setting-sources` 차단 범위 불명확. 무리한 차단 시 부작용 |
| Managed settings | 차단 메커니즘 자체가 존재하지 않음 |

---

## 8. CLI 인터페이스

엔트리포인트: `automata` (pyproject.toml의 `[project.scripts]`로 등록)

```bash
automata configure          # 초기 설정 (Slack 토큰, 목적 입력)
automata start              # LaunchAgent 설치 + 시스템 시작
automata stop               # 시스템 중지 + LaunchAgent 제거
automata restart            # 재시작
automata status             # 현재 상태 출력
automata tui                # Textual TUI 실행
automata logs [--follow]    # 로그 출력
automata inject "<mission>" # 미션 큐에 수동 주입
automata reset              # 마지막 체크포인트로 롤백
automata purpose            # 현재 Purpose 출력
```

---

## 9. 요구사항 추적성

상세: [requirements-traceability.md](requirements-traceability.md)

| 요구사항 | 설계 결정 |
|----------|-----------|
| **P-1** Purpose 구성 | Initialization Session이 Owner 입력→Purpose 변환. `state/purpose.json` |
| **P-2** 도메인 구성 | Initialization Session이 전략/규칙/미션 자동 생성 |
| **P-3** 빈 큐 자율 결정 | Stop Hook이 빈 큐 감지 → Claude에 미션 생성 위임 |
| **E-1** 설정 격리 | 4중 방어: `--setting-sources` + `claudeMdExcludes` + 격리된 환경 변수 + 프로젝트 설정. [상세](encapsulation.md) |
| **E-2** 장애 불멸 | launchd KeepAlive + Watchdog + 에러 분류 복구 |
| **E-3** 장애 분류 | ErrorClassifier: transient/rate_limit/auth/corruption/crash/network/stuck |
| **E-4** Supervisor 보호 | launchd LaunchAgent + 별도 Watchdog LaunchAgent |
| **Q-1** opus[1m] max | `--model opus --effort max` + `CLAUDE_CODE_SUBAGENT_MODEL=opus` |
| **Q-2** 최고 품질 | CLAUDE.md에 "최대 시간/리소스 투입" 지시. 비용/시간 제한 없음 |
| **Q-3** 인지 부하 최대화 | 미션 프롬프트 4단계 프로토콜 + Stop hook agent 외부 트리거. [상세](components/cognitive-load-trigger.md) |
| **Q-4** 트리거 5원칙 | Q-4a~Q-4e 준수. session-analysis.json(패턴) → 별도 컨텍스트 agent → 메인 세션 주입 |
| **C-1** 컨텍스트 보존 | State 파일 + SessionStart Hook 주입 + CLAUDE.md |
| **C-2** 파일 기반 | 모든 state/ 파일이 JSON. Git 추적 |
| **C-3** 복구 지점 | 세션 시작 전 `git tag checkpoint-{ts}` |
| **S-1** Friction 감지 | friction.json에 다양한 원천의 마찰 기록 |
| **S-2** 자동 개선 | Friction 축적 임계값 도달 시 개선 Mission 자동 생성 |
| **S-3** 사전 개선 | 주기적 시스템 검토 Mission (proactive_improvement_interval) |
| **S-4** 무제한 범위 | CLAUDE.md, hooks, Supervisor, TUI 모두 개선 대상 |
| **S-5** 임계값 개선 | config.toml의 모든 값이 Claude Code에 의해 수정 가능 |
| **O-1** 비동기 위임 | Slack 스레드로 Owner에 요청, Blocker 시 다른 미션 수행 |
| **O-2** Slack 채널 | slack-bolt async Socket Mode |
| **O-3** 동시 요청 | 각 요청이 독립 Slack 스레드. requests.json으로 추적 |
| **O-4** 이상 알림 | Notification Hook → Slack 알림 |
| **O-5** 운영 불필요 | 자율 운영. Owner 개입 없이 동작 |
| **O-6** 한국어 | CLAUDE.md에 "모든 Owner 메시지는 한국어" 지시 |
| **O-7** 실시간 TUI | Textual 기반 대시보드 |
| **O-8** TUI 상호작용 | Mission 주입, 요청 응답 기능 |
| **D-1** Template Repo | GitHub Template Repository 구조 |
| **D-2** 즉시 동작 | `automata configure` → `automata start`로 부팅 |
| **D-3** 업데이트 없음 | 자기개선이 업데이트 대체 |
| **D-4** macOS | launchd LaunchAgent, Darwin 호환 |
| **D-5** uv + Python 3.14 | pyproject.toml, uv run, uv sync |
| **D-6** Claude Max | OAuth 인증, ANTHROPIC_API_KEY 미설정 |

---

## 10. 하위 설계 문서 목차

1. [directory-structure.md](directory-structure.md) — 프로젝트 디렉토리 구조 상세
2. [data-model.md](data-model.md) — 모든 데이터 스키마 (JSON Schema 수준)
3. [flows.md](flows.md) — 핵심 흐름 시퀀스 다이어그램
4. [requirements-traceability.md](requirements-traceability.md) — 요구사항 ↔ 설계 매핑
5. [file-format-decisions.md](file-format-decisions.md) — 파일 형식 결정 (JSON/TOML/Markdown/JSONL 용도별 선택 근거)
6. [encapsulation.md](encapsulation.md) — 시스템 캡슐화 설계 (User 설정 완전 격리)
7. **컴포넌트 설계:**
   - [components/supervisor.md](components/supervisor.md)
   - [components/session-manager.md](components/session-manager.md)
   - [components/state-manager.md](components/state-manager.md)
   - [components/slack-client.md](components/slack-client.md)
   - [components/hook-system.md](components/hook-system.md)
   - [components/tui.md](components/tui.md)
   - [components/error-classifier.md](components/error-classifier.md)
   - [components/purpose-engine.md](components/purpose-engine.md)
   - [components/self-improvement.md](components/self-improvement.md)
   - [components/cognitive-load-trigger.md](components/cognitive-load-trigger.md)
