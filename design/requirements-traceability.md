# 요구사항 추적성 매트릭스

이 문서는 [claude-automata 요구사항](../docs/claude-automata-requirements.md)의 모든 항목이 설계에서 어떻게 만족되는지 추적한다.

---

## 1. 목적 (Purpose)

### P-1: Purpose 자율 구성

> 시스템은 Owner의 초기 입력으로부터 Purpose를 스스로 구성해야 한다. 유한한 요청이 주어져도 이를 영속적 방향으로 확장한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | Initialization Session에서 Claude Code가 Owner 입력을 분석하여 종료 조건 없는 영속적 방향으로 변환 |
| **구현 위치** | Purpose Engine ([purpose-engine.md](components/purpose-engine.md) §2) |
| **데이터** | `state/purpose.json` — `raw_input`(원문) → `purpose`(영속적 방향) 변환 ([data-model.md](data-model.md) §1) |
| **흐름** | Bootstrap Flow ([flows.md](flows.md) §1) — 단계 6-8 |
| **검증 방법** | `purpose.json`의 `purpose` 필드에 종료 조건이 없는 방향성 문장이 존재함을 확인 |

### P-2: 도메인 구성 자동 생성

> 시스템은 구성한 Purpose에 맞는 도메인 구성(전략, 스킬, 규칙, 초기 Mission)을 스스로 생성해야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | Initialization Session이 Purpose로부터 전략, CLAUDE.md, .claude/rules/, 초기 Mission을 자동 생성 |
| **구현 위치** | Purpose Engine ([purpose-engine.md](components/purpose-engine.md) §3) |
| **데이터** | `state/strategy.json`, `CLAUDE.md`, `.claude/rules/*.md`, `state/missions.json` 초기값 |
| **흐름** | Bootstrap Flow ([flows.md](flows.md) §1) — 단계 9-12 |
| **검증 방법** | Initialization Session 완료 후 전략/규칙/미션 파일이 모두 존재하고 Purpose와 일관됨을 확인 |

### P-3: 빈 큐 시 자율 결정

> Mission 큐가 비면 시스템은 Purpose에 따라 스스로 할 일을 결정해야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | Stop Hook이 빈 큐를 감지하면 Purpose + 현재 상태를 additionalContext로 주입하고, Claude Code에 미션 생성을 위임 |
| **구현 위치** | Hook System ([hook-system.md](components/hook-system.md) §3, Stop Hook 단계 5) |
| **데이터** | `state/missions.json`에 새 미션 추가. `config.toml.mission_idle_generation_count`(기본 3)개 생성 |
| **흐름** | Stop Hook Decision Flow ([flows.md](flows.md) §3) — 빈 큐 분기 |
| **검증 방법** | 큐가 비었을 때 Claude Code가 Purpose에 부합하는 새 미션을 생성함을 확인 |

---

## 2. 영속적 실행 (Perpetual Execution)

### 2.1 실행 연속성

#### E-1: 설정 격리

> 시스템의 AI 실행은 Owner의 개인 설정(글로벌 Claude Code 설정 등)에 영향받지 않아야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 4중 방어 전략: (1) `--setting-sources project,local` — User 설정 로딩 차단, (2) `claudeMdExcludes` — 상위 CLAUDE.md 차단, (3) 격리된 환경 변수(`os.environ.copy()` 기반, 핵심 변수 덮어쓰기 및 오염 변수 제거) — Thinking/Effort 고정, (4) 프로젝트 `.claude/settings.json` — 시스템 전용 설정 |
| **구현 위치** | Session Manager ([session-manager.md](components/session-manager.md) §4.2-4.3) — 명령 구성 + 격리 환경, 캡슐화 설계 ([encapsulation.md](encapsulation.md)) — 전체 격리 전략 |
| **위협 모델** | 12개 위협 식별: User settings(T-1~T-6), CLAUDE.md 오염(T-7~T-9), 격리 불가(T-10~T-12). 9개 완전 차단, 3개 감지+경고 |
| **검증 방법** | (1) Owner가 `/config`에서 Thinking off → 시스템 무영향 확인, (2) `~/dev/CLAUDE.md` 생성 → 시스템 무영향 확인, (3) `acc status`에서 격리 상태 표시 확인 |

#### E-2: 장애 불멸

> 어떤 장애(API 에러, 네트워크 오류, 인증 만료, 프로세스 크래시)도 시스템을 영구적으로 멈추게 해서는 안 된다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 3중 보호: (1) launchd KeepAlive — Supervisor 크래시 시 자동 재시작, (2) Watchdog — Supervisor hang 감지 및 복구, (3) ErrorClassifier — 에러별 복구 전략 |
| **구현 위치** | Supervisor ([supervisor.md](components/supervisor.md) §4-5), Error Classifier ([error-classifier.md](components/error-classifier.md)), Session Manager ([session-manager.md](components/session-manager.md) §7) |
| **흐름** | Error Recovery Flow ([flows.md](flows.md) §4), Watchdog Recovery Flow ([flows.md](flows.md) §9), Session Crash Recovery Flow ([flows.md](flows.md) §8) |
| **검증 방법** | API 에러, 네트워크 오류, 인증 만료, 프로세스 kill 각각에 대해 시스템이 자동 복구됨을 확인 |

#### E-3: 장애 유형 분류

> 장애 유형을 분류하고 각 유형에 적절한 복구 전략을 적용해야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 8가지 에러 유형(TRANSIENT_API, RATE_LIMITED, AUTH_FAILURE, CONTEXT_CORRUPTION, PROCESS_CRASH, NETWORK_ERROR, STUCK, UNKNOWN) 각각에 고유 복구 전략 |
| **구현 위치** | Error Classifier ([error-classifier.md](components/error-classifier.md) §2-4) |
| **복구 전략** | retry_resume, retry_fresh, wait_and_resume, notify_owner, checkpoint_restore — 각 에러 유형별 매핑 |
| **검증 방법** | 각 에러 유형이 올바르게 분류되고 적절한 전략이 선택됨을 단위 테스트로 확인 |

#### E-4: Supervisor 독립 감시

> Supervisor는 독립적 감시 메커니즘에 의해 보호되어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | (1) launchd LaunchAgent — OS 레벨 프로세스 감시, (2) 별도 Watchdog LaunchAgent — heartbeat 기반 응용 레벨 감시 |
| **구현 위치** | Supervisor ([supervisor.md](components/supervisor.md) §4-5) — launchd plist + Watchdog 구현 |
| **감시 메커니즘** | launchd: KeepAlive=true, ThrottleInterval=10. Watchdog: 60초 주기 heartbeat 확인, 120초 stale 임계값, launchctl kickstart 복구 |
| **흐름** | Watchdog Recovery Flow ([flows.md](flows.md) §9) |
| **검증 방법** | Supervisor 프로세스를 kill -9 한 후 자동 재시작됨을 확인. Heartbeat 쓰기를 중단한 후 Watchdog가 복구함을 확인 |

### 2.2 추론 품질

#### Q-1: opus[1m] max effort 전용

> 모든 AI 추론은 반드시 opus[1m] max effort 모델로 수행해야 한다. 시스템이 전개하는 에이전트와 그 하위 에이전트 모두 이 모델을 사용해야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | CLI 플래그 `--model opus --effort max` + 환경변수 `CLAUDE_CODE_EFFORT_LEVEL=max`, `CLAUDE_CODE_SUBAGENT_MODEL=opus` |
| **구현 위치** | Session Manager ([session-manager.md](components/session-manager.md) §4) — 실행 명령 구성 |
| **CLAUDE.md 지시** | "모든 에이전트/서브에이전트는 반드시 opus 모델, max effort로 실행" ([purpose-engine.md](components/purpose-engine.md) §7) |
| **검증 방법** | 세션 로그에서 모든 API 호출이 opus 모델을 사용함을 확인 |

#### Q-2: 최고 품질 집중

> 시스템은 오직 최고의 품질에만 집중한다. 실행 시간이나 비용은 고려하지 않는다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | CLAUDE.md에 "최대한 많은 시간과 리소스를 투입하여 최고 품질 달성" 지시. 비용/시간 제한 없음. `--max-budget-usd` 미설정 |
| **구현 위치** | Purpose Engine ([purpose-engine.md](components/purpose-engine.md) §7) — CLAUDE.md 구조의 "품질 규칙" 섹션 |
| **검증 방법** | 시스템이 비용/시간 제약 없이 최선의 결과를 추구함을 미션 결과 품질로 확인 |

#### Q-3: 인지 부하 최대화

> 시스템은 모델에게 최대한의 유의미한 인지적 부하를 주어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 자기 주도 계층(미션 프롬프트 4단계 프로토콜) + 외부 주입 계층(Stop hook agent가 패턴 분석 후 방향 주입). 두 계층으로 5회 이상 인지 전환 |
| **구현 위치** | Cognitive Load Trigger ([cognitive-load-trigger.md](components/cognitive-load-trigger.md)) |
| **검증 방법** | trigger-effectiveness.jsonl의 효과 추적 데이터로 트리거 후 행동 변화 측정 |

#### Q-4: 인지 부하 트리거 5원칙

> 인지 부하 트리거는 5개 원칙(Q-4a~Q-4e)을 준수해야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | Q-4a: session-analysis.json 기반. Q-4b: 부재/다양성/에러무시/비대칭/수렴 분석으로 미탐색 겨냥. Q-4c: prompt에 "방향만 제시" 명시. Q-4d: Stop hook reason이 동일 세션에 주입. Q-4e: agent hook 별도 컨텍스트, 사실만 입력 |
| **구현 위치** | Cognitive Load Trigger ([cognitive-load-trigger.md](components/cognitive-load-trigger.md) §3) |
| **검증 방법** | 각 원칙별 구조적 보장: Q-4a(StreamAnalyzer), Q-4b(분석 렌즈), Q-4c(prompt 제약), Q-4d(Stop hook 메커니즘), Q-4e(별도 컨텍스트 + 사실만 입력) |

### 2.3 컨텍스트 보존

#### C-1: 세션 간 맥락 보존

> Session이 끝나고 새 Session이 시작되어도 이전 작업의 맥락이 보존되어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 3중 보존: (1) State 파일 — 모든 상태 JSON으로 영속화, (2) SessionStart Hook — 새 세션에 상태 요약 주입, (3) CLAUDE.md — 영구 지시문 (compaction 후에도 디스크에서 재읽기) |
| **구현 위치** | State Manager ([state-manager.md](components/state-manager.md) §5 `create_session_context()`), Hook System ([hook-system.md](components/hook-system.md) §4 SessionStart Hook) |
| **흐름** | Context Refresh Flow ([flows.md](flows.md) §12) |
| **검증 방법** | 세션 1에서 작업한 내용을 세션 2에서 인지하고 이어서 작업함을 확인 |

#### C-2: 파일 기반 상태

> 모든 상태는 파일로 관리해야 한다. 파일은 AI가 직접 읽고 쓸 수 있고 Git으로 복구할 수 있다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 모든 상태를 `state/` 디렉토리의 JSON 파일로 관리. Git 추적. 원자적 쓰기 (tempfile + os.replace) |
| **구현 위치** | State Manager ([state-manager.md](components/state-manager.md) §2-3), Data Model ([data-model.md](data-model.md)) |
| **검증 방법** | `state/` 디렉토리에 모든 상태가 JSON으로 존재. `git log -- state/`로 변경 이력 확인 가능 |

#### C-3: 복구 지점

> 매 Session 시작 전 복구 지점을 생성하여 AI가 시스템을 망가뜨려도 롤백할 수 있어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 세션 시작 전 `git tag checkpoint-{timestamp}-{label}` 생성. 롤백: `git checkout {tag} -- state/` |
| **구현 위치** | State Manager ([state-manager.md](components/state-manager.md) §4), Supervisor ([supervisor.md](components/supervisor.md) §2 메인 루프) |
| **CLI** | `acc reset` — 마지막 체크포인트로 롤백 |
| **검증 방법** | 세션 시작 시마다 Git 태그가 생성됨. `acc reset` 후 이전 상태로 복원됨을 확인 |

---

## 3. 재귀적 자기개선 (Recursive Self-Improvement)

### S-1: Friction 다양한 원천 감지

> 시스템은 Friction을 다양한 원천에서 감지하고 누적 기록해야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 7가지 원천(error, repeated_failure, stuck, quality, owner_intervention, slow, context_loss)에서 감지. `pattern_key`로 그룹화 |
| **구현 위치** | Self-Improvement ([self-improvement.md](components/self-improvement.md) §1) |
| **데이터** | `state/friction.json` ([data-model.md](data-model.md) §4) |
| **검증 방법** | 각 원천에서 마찰이 감지되고 friction.json에 기록됨을 확인 |

### S-2: 자동 자기개선 트리거

> Friction이 축적되면 자가 개선이 자동으로 트리거되어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 동일 `pattern_key`의 미해소 Friction이 `config.toml.friction_threshold`(기본 3) 이상 → priority 0 개선 Mission 자동 생성 |
| **구현 위치** | Self-Improvement ([self-improvement.md](components/self-improvement.md) §2), Hook System ([hook-system.md](components/hook-system.md) §3 Stop Hook) |
| **흐름** | Self-Improvement Flow ([flows.md](flows.md) §6) |
| **검증 방법** | 같은 유형의 Friction 3회 축적 시 개선 Mission이 자동 생성됨을 확인 |

### S-3: 사전적 자기개선

> Friction이 없는 정상 운영에서도 주기적으로 사전적 자가 개선이 실행되어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 매 `config.toml.proactive_improvement_interval`(기본 10) 미션마다 시스템 전반 검토 Mission 자동 생성 |
| **구현 위치** | Self-Improvement ([self-improvement.md](components/self-improvement.md) §3), Hook System ([hook-system.md](components/hook-system.md) §3 Stop Hook) |
| **흐름** | Proactive Improvement Flow ([flows.md](flows.md) §7) |
| **검토 대상** | Purpose 정렬, 전략 효과성, 도구 사용 패턴, Friction 경향, 코드 품질, 성능 |
| **검증 방법** | 10개 미션 완료 후 사전 개선 Mission이 생성됨을 확인 |

### S-4: 무제한 개선 범위

> 자가 개선의 범위에 제한이 없어야 한다. 개선 동작 자체도 개선 대상이다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 11개 개선 대상에 제한 없음: CLAUDE.md, .claude/rules/, strategy.json, config.toml, hooks, supervisor, session_manager, state_manager, slack_client, tui, cli, tests, 자기개선 규칙 자체 |
| **구현 위치** | Self-Improvement ([self-improvement.md](components/self-improvement.md) §4) |
| **안전장치** | Git 체크포인트, 테스트 실패 시 자동 롤백, Owner 알림, 연속 3회 개선 루프 제한 |
| **검증 방법** | Claude Code가 system/ 하위 Python 코드를 수정하고, .claude/rules/self-improvement.md 자체를 수정할 수 있음을 확인 |

### S-5: 임계값 자기개선

> 모든 임계값은 자가 개선의 대상이어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | `config.toml`의 모든 값(8개)이 Claude Code에 의해 수정 가능: friction_threshold, proactive_improvement_interval, context_refresh_after_compactions, goal_drift_check_interval, session_timeout_minutes, max_consecutive_failures, slack_notification_level, mission_idle_generation_count. TOML 형식의 인라인 주석(`#`)을 활용하여 변경 근거를 config 파일 자체에 기록 |
| **구현 위치** | Self-Improvement ([self-improvement.md](components/self-improvement.md) §5), Data Model ([data-model.md](data-model.md) §7) |
| **검증 방법** | Claude Code가 config.toml의 임계값을 수정하고, 변경 근거가 인라인 주석으로 기록되며, 변경된 값이 이후 동작에 반영됨을 확인 |

---

## 4. Owner 인터페이스 (Owner Interface)

### 4.1 비동기 위임

#### O-1: Owner는 비동기 자원

> Owner는 AI의 한계를 극복하기 위한 비동기 자원이다. Blocker가 발생하면 시스템은 다른 Mission을 수행한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | Blocker 발생 → `requests.json`에 요청 생성 → Slack 스레드로 전송 → 미션을 `blocked` 상태로 변경 → 다음 미션 수행 |
| **구현 위치** | Slack Client ([slack-client.md](components/slack-client.md) §3-5), State Manager ([state-manager.md](components/state-manager.md) §3 Mission 메서드) |
| **흐름** | Owner Interaction Flow ([flows.md](flows.md) §5) |
| **검증 방법** | Blocker 발생 시 Slack 알림이 전송되고, 시스템이 다른 미션을 수행함을 확인 |

#### O-2: Slack 채널

> Channel은 Slack을 사용한다. 각 요청은 독립적인 Slack 스레드에서 관리되어 Owner가 자연어로 응답할 수 있어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | slack-bolt AsyncApp + Socket Mode. 각 요청 = 독립 Slack 스레드 (`thread_ts` 추적) |
| **구현 위치** | Slack Client ([slack-client.md](components/slack-client.md) §2-4) |
| **검증 방법** | 각 요청이 별도 스레드로 생성되고, Owner가 자연어로 응답할 수 있음을 확인 |

#### O-3: 동시 요청

> 여러 요청이 동시에 진행될 수 있어야 하며 Owner는 아무 순서로 응답할 수 있어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | `requests.json`에 복수 pending 요청 동시 관리. Socket Mode 이벤트로 `thread_ts` 매칭. 순서 무관 응답 처리 |
| **구현 위치** | Slack Client ([slack-client.md](components/slack-client.md) §4 Thread Management) |
| **검증 방법** | 3개 동시 요청 생성 후 역순으로 응답해도 각각 올바르게 처리됨을 확인 |

#### O-4: 이상 상태 알림

> 시스템의 이상 상태는 Owner에게 알림으로 전달되어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | Notification Hook → Slack 알림 전송. 알림 레벨: `config.toml.slack_notification_level` (info/warning/error/critical) |
| **구현 위치** | Hook System ([hook-system.md](components/hook-system.md) §5 Notification Hook), Slack Client ([slack-client.md](components/slack-client.md) §3 `send_alert()`) |
| **검증 방법** | 시스템 이상(크래시, 인증 만료 등) 발생 시 Slack 알림이 전송됨을 확인 |

### 4.2 사용 경험

#### O-5: 운영 불필요

> Owner는 시스템을 "운영"하지 않으므로 일상적 운영에 Owner 개입이 필요하지 않아야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 완전 자율 운영: 자동 미션 생성(P-3), 자동 에러 복구(E-2/E-3), 자동 자기개선(S-2/S-3), launchd 자동 재시작 |
| **구현 위치** | 전체 시스템 설계가 이 요구사항을 충족 |
| **검증 방법** | 48시간 동안 Owner 개입 없이 시스템이 자율 운영됨을 확인 |

#### O-6: 한국어

> Owner에게 전달되는 모든 메시지는 한국어여야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | CLAUDE.md에 "Owner에게 보내는 모든 메시지는 한국어" 지시. Slack Client가 모든 메시지를 한국어로 포맷 |
| **구현 위치** | Purpose Engine ([purpose-engine.md](components/purpose-engine.md) §7 CLAUDE.md 구조), Slack Client ([slack-client.md](components/slack-client.md) §5 Message Formatting) |
| **검증 방법** | Slack으로 전송되는 모든 메시지가 한국어임을 확인 |

#### O-7: 실시간 TUI

> 시스템의 현재 상태를 Owner가 실시간으로 파악할 수 있는 로컬 인터페이스(TUI)가 있어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | Textual v8+ 기반 대시보드. 5개 탭: Dashboard, Mission Queue, Logs, Slack, Friction. 5초 주기 상태 파일 폴링, 실시간 로그 테일링 |
| **구현 위치** | TUI ([tui.md](components/tui.md)) |
| **실행** | `acc tui` → 독립 프로세스로 실행 |
| **검증 방법** | TUI에서 시스템 상태, 현재 미션, 로그, Slack 요청이 실시간으로 표시됨을 확인 |

#### O-8: TUI 상호작용

> TUI는 관찰뿐 아니라 Mission 주입, 요청 응답 등의 상호작용을 지원해야 한다. TUI는 Textual 라이브러리로 개발한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | Mission Queue 탭에서 미션 주입 (Input + Submit), Slack 탭에서 요청 응답 (Input + Send). State 파일 기반 통신 (IPC 불필요) |
| **구현 위치** | TUI ([tui.md](components/tui.md) §4 Tab 2, §6 Tab 4) |
| **라이브러리** | Textual v8+ (요구사항에서 지정) |
| **검증 방법** | TUI에서 미션을 주입하면 missions.json에 추가되고 시스템이 이를 실행함을 확인 |

---

## 5. 배포 및 실행 환경 (Deployment & Runtime)

#### D-1: Template Repository

> 시스템은 GitHub Template Repository로 배포된다. Clone하여 사용한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 프로젝트 구조가 Template Repository로 배포 가능. Clone 후 `acc configure`로 설정 |
| **구현 위치** | Directory Structure ([directory-structure.md](directory-structure.md)) |
| **검증 방법** | GitHub에서 "Use this template"으로 새 레포 생성 후 정상 동작 확인 |

#### D-2: 즉시 동작

> Clone 후 Owner가 초기 입력을 제공하고 시스템을 시작하면 동작해야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | `git clone` → `uv sync` → `uv run acc configure` (토큰, 목적 입력) → `uv run acc start` |
| **구현 위치** | CLI ([directory-structure.md](directory-structure.md) §7), Bootstrap Flow ([flows.md](flows.md) §1) |
| **검증 방법** | 깨끗한 환경에서 4단계로 시스템이 완전히 동작함을 확인 |

#### D-3: 업데이트 없음

> 업데이트 메커니즘이 없다. 재귀적 자기개선(섹션 3)이 업데이트를 대체한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | 외부 업데이트 메커니즘 없음. S-1~S-5의 자기개선이 시스템 진화를 담당 |
| **구현 위치** | Self-Improvement ([self-improvement.md](components/self-improvement.md)) |
| **검증 방법** | Template repo의 업데이트가 이미 실행 중인 시스템에 영향을 주지 않음을 확인 |

#### D-4: macOS 실행 환경

> 실행 환경은 Claude Code가 설치된 macOS이다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | launchd LaunchAgent (macOS 전용), Darwin 시그널 핸들링, ~/Library/LaunchAgents/ 경로 |
| **구현 위치** | Supervisor ([supervisor.md](components/supervisor.md) §4-6) |
| **검증 방법** | macOS 환경에서 정상 동작 확인 |

#### D-5: uv + Python 3.14

> uv 네이티브로 python 3.14를 사용한다. uv를 적극 도입한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | `pyproject.toml`에 `requires-python = ">=3.14"`. `uv sync`로 의존성 설치. `uv run acc`로 실행. `.python-version` 파일에 "3.14" |
| **구현 위치** | Directory Structure ([directory-structure.md](directory-structure.md) §1 pyproject.toml) |
| **검증 방법** | `uv sync` + `uv run acc start`로 정상 동작 확인 |

#### D-6: Claude Max 구독

> Claude Max 구독 요금제로 사용한다. 로그인이 완료된 Claude Code가 있으면 즉시 사용할 수 있어야 한다.

| 항목 | 내용 |
|------|------|
| **설계 결정** | OAuth 기반 Claude Max 구독 사용. `ANTHROPIC_API_KEY` 환경변수 미설정 (설정 시 API 과금으로 전환되는 버그 방지). `claude login` 사전 완료 전제 |
| **구현 위치** | Session Manager ([session-manager.md](components/session-manager.md) §4), DESIGN.md §7 |
| **검증 방법** | `claude login`이 완료된 환경에서 API 키 없이 시스템이 동작함을 확인 |

---

## 요약 매트릭스

| ID | 요구사항 | 상태 | 설계 문서 |
|----|----------|------|-----------|
| P-1 | Purpose 자율 구성 | ✅ 설계됨 | purpose-engine.md, flows.md §1 |
| P-2 | 도메인 구성 생성 | ✅ 설계됨 | purpose-engine.md, flows.md §1 |
| P-3 | 빈 큐 자율 결정 | ✅ 설계됨 | hook-system.md, flows.md §3 |
| E-1 | 설정 격리 | ✅ 설계됨 | supervisor.md, session-manager.md |
| E-2 | 장애 불멸 | ✅ 설계됨 | supervisor.md, error-classifier.md |
| E-3 | 장애 분류 | ✅ 설계됨 | error-classifier.md |
| E-4 | Supervisor 보호 | ✅ 설계됨 | supervisor.md §4-5 |
| Q-1 | opus[1m] max | ✅ 설계됨 | session-manager.md §4 |
| Q-2 | 최고 품질 | ✅ 설계됨 | purpose-engine.md §7 |
| Q-3 | 인지 부하 최대화 | ✅ 설계됨 | cognitive-load-trigger.md |
| Q-4 | 트리거 5원칙 | ✅ 설계됨 | cognitive-load-trigger.md §3 |
| C-1 | 컨텍스트 보존 | ✅ 설계됨 | state-manager.md, hook-system.md |
| C-2 | 파일 기반 상태 | ✅ 설계됨 | data-model.md, state-manager.md |
| C-3 | 복구 지점 | ✅ 설계됨 | state-manager.md §4 |
| S-1 | Friction 감지 | ✅ 설계됨 | self-improvement.md §1 |
| S-2 | 자동 개선 | ✅ 설계됨 | self-improvement.md §2 |
| S-3 | 사전 개선 | ✅ 설계됨 | self-improvement.md §3 |
| S-4 | 무제한 범위 | ✅ 설계됨 | self-improvement.md §4 |
| S-5 | 임계값 개선 | ✅ 설계됨 | self-improvement.md §5, data-model.md §7 |
| O-1 | 비동기 위임 | ✅ 설계됨 | slack-client.md, flows.md §5 |
| O-2 | Slack 채널 | ✅ 설계됨 | slack-client.md |
| O-3 | 동시 요청 | ✅ 설계됨 | slack-client.md §4 |
| O-4 | 이상 알림 | ✅ 설계됨 | hook-system.md §5, slack-client.md |
| O-5 | 운영 불필요 | ✅ 설계됨 | 전체 자율 아키텍처 |
| O-6 | 한국어 | ✅ 설계됨 | purpose-engine.md §7, slack-client.md |
| O-7 | 실시간 TUI | ✅ 설계됨 | tui.md |
| O-8 | TUI 상호작용 | ✅ 설계됨 | tui.md §4, §6 |
| D-1 | Template Repo | ✅ 설계됨 | directory-structure.md |
| D-2 | 즉시 동작 | ✅ 설계됨 | flows.md §1 |
| D-3 | 업데이트 없음 | ✅ 설계됨 | self-improvement.md |
| D-4 | macOS | ✅ 설계됨 | supervisor.md §4-6 |
| D-5 | uv + Python 3.14 | ✅ 설계됨 | directory-structure.md §1 |
| D-6 | Claude Max | ✅ 설계됨 | session-manager.md §4, DESIGN.md §7 |

**전체 33개 요구사항 중 33개 설계됨 (100%)**
