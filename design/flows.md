# claude-automata 핵심 흐름 설계서

> 이 문서는 claude-automata 시스템의 **모든 핵심 운영 흐름**을 시퀀스 다이어그램과 단계별 설명으로 기술한다.

---

## 목차

1. [Bootstrap Flow (최초 설정 및 시작)](#1-bootstrap-flow-최초-설정-및-시작)
2. [Normal Operation Cycle (정상 운영 루프)](#2-normal-operation-cycle-정상-운영-루프)
3. [Stop Hook Decision Flow (Stop Hook 결정 흐름)](#3-stop-hook-decision-flow-stop-hook-결정-흐름)
4. [Error Recovery Flow (에러 복구 흐름)](#4-error-recovery-flow-에러-복구-흐름)
5. [Owner Interaction Flow (Owner 상호작용 흐름)](#5-owner-interaction-flow-owner-상호작용-흐름)
6. [Self-Improvement Flow (자기개선 흐름)](#6-self-improvement-flow-자기개선-흐름)
7. [Proactive Improvement Flow (사전적 자기개선 흐름)](#7-proactive-improvement-flow-사전적-자기개선-흐름)
8. [Session Crash Recovery Flow (세션 크래시 복구 흐름)](#8-session-crash-recovery-flow-세션-크래시-복구-흐름)
9. [Watchdog Recovery Flow (Watchdog 복구 흐름)](#9-watchdog-recovery-flow-watchdog-복구-흐름)
10. [TUI Interaction Flow (TUI 상호작용 흐름)](#10-tui-interaction-flow-tui-상호작용-흐름)
11. [Goal Drift Prevention Flow (목표 드리프트 방지 흐름)](#11-goal-drift-prevention-flow-목표-드리프트-방지-흐름)
12. [Context Refresh Flow (컨텍스트 갱신 흐름)](#12-context-refresh-flow-컨텍스트-갱신-흐름)

---

## 액터 정의

| 액터 | 레이어 | 설명 |
|------|--------|------|
| **Owner** | 외부 | 시스템 소유자인 인간. Slack 또는 TUI로 상호작용 |
| **Supervisor** | Deterministic Core | Python 데몬. 전체 시스템 오케스트레이션 |
| **Session Manager** | Deterministic Core | Claude Code 프로세스 생명주기 관리 |
| **State Manager** | Deterministic Core | 파일 기반 상태 영속화, 원자적 쓰기, Git 체크포인트 |
| **Slack Client** | Deterministic Core | Socket Mode WebSocket 통신 |
| **Stop Hook** | Hook System | Claude Code Stop 이벤트 처리 (`system/hooks/on_stop.py`) |
| **SessionStart Hook** | Hook System | 세션 시작 시 컨텍스트 주입 (`system/hooks/on_session_start.py`) |
| **Claude Code** | Agentic Shell | `claude -p` 프로세스. 미션 실행, 의사결정, 자기개선 |
| **Watchdog** | Deterministic Core | 독립 프로세스. Supervisor 생존 감시 |
| **TUI** | UI | Textual 기반 대시보드. 상태 파일 읽기 + 입력 쓰기 |
| **launchd** | OS | macOS LaunchAgent. KeepAlive로 프로세스 부활 |

---

## 1. Bootstrap Flow (최초 설정 및 시작)

### 트리거 조건
Owner가 GitHub Template Repository를 clone하고 최초 설정을 실행할 때.

### 시퀀스 다이어그램

```
Owner              CLI(acc)           Supervisor       Claude Code       State Manager
  |                   |                   |                |                   |
  |  git clone        |                   |                |                   |
  |  cd project       |                   |                |                   |
  |  uv sync          |                   |                |                   |
  |                   |                   |                |                   |
  |  acc configure    |                   |                |                   |
  |------------------>|                   |                |                   |
  |                   |                   |                |                   |
  |  Slack Bot Token  |                   |                |                   |
  |  입력 프롬프트    |                   |                |                   |
  |<------------------|                   |                |                   |
  |  토큰 + 목적 입력 |                   |                |                   |
  |------------------>|                   |                |                   |
  |                   |                   |                |                   |
  |                   | [1] Slack 연결 검증|                |                   |
  |                   | [2] .env 생성     |                |                   |
  |                   | [3] 설정 검증 완료 |                |                   |
  |                   |                   |                |                   |
  |  "설정 완료" 출력 |                   |                |                   |
  |<------------------|                   |                |                   |
  |                   |                   |                |                   |
  |  acc start        |                   |                |                   |
  |------------------>|                   |                |                   |
  |                   |                   |                |                   |
  |                   | [4] LaunchAgent   |                |                   |
  |                   |     plist 설치    |                |                   |
  |                   |     (Supervisor + |                |                   |
  |                   |      Watchdog)    |                |                   |
  |                   |                   |                |                   |
  |                   | [5] launchctl bootstrap|                |                   |
  |                   |---(launchd가 Supervisor 시작)----->|                   |
  |                   |                   |                |                   |
  |                   |                   | [6] PID 잠금   |                   |
  |                   |                   |     run/supervisor.pid 생성        |
  |                   |                   |                |                   |
  |                   |                   | [7] Heartbeat  |                   |
  |                   |                   |     시작       |                   |
  |                   |                   |                |                   |
  |                   |                   | [8] Slack Client 시작              |
  |                   |                   |     Socket Mode 연결               |
  |                   |                   |                |                   |
  |                   |                   | [9] 초기화 감지|                   |
  |                   |                   |    state/purpose.json 없음         |
  |                   |                   |                |                   |
  |                   |                   | [10] Initialization Session 시작   |
  |                   |                   |                |                   |
  |                   |                   | claude -p      |                   |
  |                   |                   | "<init_prompt>"|                   |
  |                   |                   |--------------->|                   |
  |                   |                   |                |                   |
  |                   |                   |                | [P-1] Purpose 구성|
  |                   |                   |                | Owner 원문 입력 → |
  |                   |                   |                | 영속적 방향 추출  |
  |                   |                   |                |------------------>|
  |                   |                   |                |  purpose.json 쓰기|
  |                   |                   |                |                   |
  |                   |                   |                | [P-2] 도메인 구성 |
  |                   |                   |                | - strategy.json   |
  |                   |                   |                | - missions.json   |
  |                   |                   |                | - config.toml     |
  |                   |                   |                | - CLAUDE.md 생성  |
  |                   |                   |                | - .claude/rules/  |
  |                   |                   |                |------------------>|
  |                   |                   |                |  state 파일 일괄  |
  |                   |                   |                |  원자적 쓰기      |
  |                   |                   |                |                   |
  |                   |                   |<---------------|                   |
  |                   |                   | 세션 정상 종료 |                   |
  |                   |                   |                |                   |
  |                   |                   | [11] Git 체크포인트 생성            |
  |                   |                   |      tag: checkpoint-init          |
  |                   |                   |                |                   |
  |                   |                   | [12] Slack 알림|                   |
  |                   |                   |     "시스템 초기화 완료"            |
  |                   |                   |                |                   |
  |                   |                   | [13] 정상 운영 루프 진입            |
  |                   |                   |     (Flow #2로 전환)               |
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | CLI | Slack 연결 검증 | Bot Token + App Token으로 `auth.test` API 호출. 실패 시 재입력 요청 |
| 2 | CLI | `.env` 생성 | `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `ACC_RAW_PURPOSE` 저장 |
| 3 | CLI | 설정 검증 | `.env` 파일 존재 + 토큰 유효성 + 목적 입력 비어있지 않음 확인 |
| 4 | CLI | LaunchAgent 설치 | `setup/launchd/com.acc.supervisor.plist` + `com.acc.watchdog.plist`를 `~/Library/LaunchAgents/`에 복사. `KeepAlive=true` 설정 |
| 5 | CLI | launchctl bootstrap | `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.acc.supervisor.plist` 실행 |
| 6 | Supervisor | PID 잠금 | `run/supervisor.pid`에 현재 PID 기록. 이미 실행 중이면 종료 |
| 7 | Supervisor | Heartbeat 시작 | `run/supervisor.heartbeat`에 주기적 타임스탬프 갱신 (5초 간격) |
| 8 | Supervisor | Slack Client 초기화 | `slack-bolt` async Socket Mode 연결. 이벤트 리스너 등록 |
| 9 | Supervisor | 초기화 감지 | `state/purpose.json` 부재 확인 → Initialization Session 모드 |
| 10 | Session Manager | Initialization Session | 특수 프롬프트로 Claude Code 실행. Owner 원문 + 초기화 지시 포함 |
| P-1 | Claude Code | Purpose 구성 | Owner 입력을 분석하여 종료 조건 없는 영속적 방향으로 확장. `purpose.json` 생성 |
| P-2 | Claude Code | 도메인 구성 생성 | Purpose에 맞는 전략, 규칙, 스킬, 초기 Mission 큐, CLAUDE.md를 자동 생성 |
| 11 | State Manager | Git 체크포인트 | `git add state/ CLAUDE.md .claude/` → `git tag checkpoint-init` |
| 12 | Slack Client | 알림 전송 | Owner에게 "시스템 초기화 완료" 메시지 + Purpose 요약 전송 |
| 13 | Supervisor | 루프 진입 | Normal Operation Cycle (Flow #2)로 전환 |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `.env` | 신규 생성: Slack 토큰, 원문 목적 |
| `~/Library/LaunchAgents/com.acc.supervisor.plist` | 신규 설치 |
| `~/Library/LaunchAgents/com.acc.watchdog.plist` | 신규 설치 |
| `run/supervisor.pid` | 신규 생성: Supervisor PID |
| `run/supervisor.heartbeat` | 신규 생성: 최초 heartbeat 타임스탬프 |
| `state/purpose.json` | 신규 생성: Purpose 정의 (raw_input, purpose, domain) |
| `state/strategy.json` | 신규 생성: 초기 전략 |
| `state/missions.json` | 신규 생성: 초기 Mission 큐 |
| `state/config.toml` | 신규 생성: 기본 임계값 (friction_threshold=3, proactive_improvement_interval=10 등) |
| `state/friction.json` | 신규 생성: 빈 Friction 로그 |
| `state/requests.json` | 신규 생성: 빈 요청 목록 |
| `state/sessions.json` | 신규 생성: Initialization Session 기록 |
| `CLAUDE.md` | 신규 생성 또는 갱신: Claude Code에 대한 시스템 전용 지시문 |
| `.claude/rules/` | 신규 생성: purpose.md, mission-protocol.md, self-improvement.md |

### 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| Slack 토큰 무효 | CLI가 에러 메시지 출력 후 재입력 요청 |
| launchctl bootstrap 실패 | CLI가 에러 출력. 수동 설치 가이드 안내 |
| PID 잠금 충돌 | 기존 프로세스 확인 → 좀비면 PID 파일 삭제 후 재시작 |
| Initialization Session 크래시 | Supervisor가 재시도 (최대 3회). 3회 실패 시 Slack으로 Owner 알림 |
| Purpose 구성 실패 | Claude Code 출력 파싱 실패 시 재시도. 반복 실패 시 원문 그대로 저장 |

### 종료 조건
Initialization Session이 성공적으로 완료되고 정상 운영 루프(Flow #2)에 진입하면 Bootstrap Flow 종료.

---

## 2. Normal Operation Cycle (정상 운영 루프)

### 트리거 조건
Bootstrap 완료 후 또는 Supervisor 재시작 후 진입하는 메인 루프.

### 시퀀스 다이어그램

```
Supervisor          State Manager       Session Manager     Claude Code        Stop Hook
  |                      |                   |                  |                  |
  | [LOOP START]         |                   |                  |                  |
  |                      |                   |                  |                  |
  | [1] Git checkpoint   |                   |                  |                  |
  |--------------------->|                   |                  |                  |
  |                      | git add state/    |                  |                  |
  |                      | git tag           |                  |                  |
  |                      | checkpoint-{ts}   |                  |                  |
  |<---------------------|                   |                  |                  |
  |                      |                   |                  |                  |
  | [2] 다음 미션 선택   |                   |                  |                  |
  |--------------------->|                   |                  |                  |
  |                      | missions.json     |                  |                  |
  |                      | 에서 priority     |                  |                  |
  |                      | 최고 + status=    |                  |                  |
  |                      | pending 선택      |                  |                  |
  |                      | (blocker 없는 것) |                  |                  |
  |<---------------------|                   |                  |                  |
  |   mission 반환       |                   |                  |                  |
  |                      |                   |                  |                  |
  | [3] 세션 프롬프트 구성|                  |                  |                  |
  |--------------------->|                   |                  |                  |
  |                      | create_session_   |                  |                  |
  |                      | context() 호출    |                  |                  |
  |                      | - 이전 세션 요약  |                  |                  |
  |                      | - 현재 미션 정보  |                  |                  |
  |                      | - Friction 요약   |                  |                  |
  |                      | - 대기 중 요청    |                  |                  |
  |<---------------------|                   |                  |                  |
  |   prompt 반환        |                   |                  |                  |
  |                      |                   |                  |                  |
  | [4] 세션 시작        |                   |                  |                  |
  |------------------------------------->|                  |                  |
  |                      |                   | claude -p        |                  |
  |                      |                   | "<prompt>"       |                  |
  |                      |                   | --dangerously-   |                  |
  |                      |                   |   skip-perms     |                  |
  |                      |                   | --model opus     |                  |
  |                      |                   | --effort max     |                  |
  |                      |                   | --output-format  |                  |
  |                      |                   |   stream-json    |                  |
  |                      |                   |----------------->|                  |
  |                      |                   |                  |                  |
  |                      |                   |  SessionStart    |                  |
  |                      |                   |  Hook 발동       |                  |
  |                      |                   |  → 컨텍스트 주입 |                  |
  |                      |                   |                  |                  |
  | [5] stream-json 모니터링                 |                  |                  |
  |<-------------------------------------|                  |                  |
  |   system/init 이벤트  |                  | session_id 수신  |                  |
  |                      |                   |                  |                  |
  |   ┌──────────────────────────────────────────────────────────────────────┐
  |   │ MONITORING LOOP (stream-json 이벤트 실시간 처리)                     │
  |   │                                                                      │
  |   │  assistant 이벤트 → TUI 상태 갱신, 로그 기록                         │
  |   │  tool_use 이벤트 → 도구 사용 추적                                    │
  |   │  tool_result 이벤트 → 결과 기록                                      │
  |   │  system/api_retry 이벤트 → rate limit 감지 (Flow #4)                │
  |   │                                                                      │
  |   │  Heartbeat 갱신 (5초 간격)                                           │
  |   │  run/current_session.json 갱신                                       │
  |   └──────────────────────────────────────────────────────────────────────┘
  |                      |                   |                  |                  |
  |                      |                   |                  | [6] Claude Code  |
  |                      |                   |                  | 작업 완료 시도   |
  |                      |                   |                  | (stop 시도)      |
  |                      |                   |                  |----------------->|
  |                      |                   |                  |  Stop Hook 발동  |
  |                      |                   |                  |  (Flow #3으로)   |
  |                      |                   |                  |<-----------------|
  |                      |                   |                  | block/allow 결정 |
  |                      |                   |                  |                  |
  |   ... (Stop Hook이 block하면 Claude Code가 계속 실행) ...                 |
  |                      |                   |                  |                  |
  | [7] 세션 종료 감지   |                   |                  |                  |
  |<-------------------------------------|                  |                  |
  |   result 이벤트 수신  |                  |                  |                  |
  |   또는 프로세스 종료  |                  |                  |                  |
  |                      |                   |                  |                  |
  | [8] 결과 기록        |                   |                  |                  |
  |--------------------->|                   |                  |                  |
  |                      | sessions.json     |                  |                  |
  |                      | 갱신              |                  |                  |
  |                      | missions.json     |                  |                  |
  |                      | 상태 갱신         |                  |                  |
  |                      | friction.json     |                  |                  |
  |                      | 갱신 (있으면)     |                  |                  |
  |<---------------------|                   |                  |                  |
  |                      |                   |                  |                  |
  | [9] 후처리          |                   |                  |                  |
  |   - Slack 상태 알림  |                   |                  |                  |
  |   - TUI 갱신         |                   |                  |                  |
  |   - 자기개선 체크    |                   |                  |                  |
  |     (Flow #6 조건)   |                   |                  |                  |
  |   - 드리프트 체크    |                   |                  |                  |
  |     (Flow #11 조건)  |                   |                  |                  |
  |   - 컨텍스트 갱신    |                   |                  |                  |
  |     체크             |                   |                  |                  |
  |     (Flow #12 조건)  |                   |                  |                  |
  |                      |                   |                  |                  |
  | [LOOP START로 복귀]  |                   |                  |                  |
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | State Manager | Git 체크포인트 | `git add state/` → `git commit` → `git tag checkpoint-{timestamp}`. 실패해도 루프 계속 (best-effort) |
| 2 | State Manager | 미션 선택 | `missions.json`에서 `status=pending`, `blockers=[]`, 최고 `priority` 미션 선택. 없으면 Stop Hook에서 생성 위임 |
| 3 | State Manager | 프롬프트 구성 | `create_session_context()`: 이전 세션 요약, 현재 미션, Friction 요약, 대기 요청 결합. 세션 프롬프트 템플릿에 주입 |
| 4 | Session Manager | Claude Code 시작 | `claude -p "<prompt>" --dangerously-skip-permissions --model opus --effort max --output-format stream-json --strict-mcp-config --mcp-config '{}'`. 환경변수: `CLAUDE_CODE_EFFORT_LEVEL=max`, `CLAUDE_CODE_SUBAGENT_MODEL=opus`. `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` 제거(기본값 95%) |
| 5 | Supervisor | stream-json 모니터링 | stdout에서 NDJSON 이벤트를 한 줄씩 파싱. 이벤트 유형별 처리. `system/init`에서 `session_id` 추출하여 `run/current_session.json`에 기록 |
| 6 | Stop Hook | 정지 판단 | Claude Code가 응답 완료 시 Stop 이벤트 발생. Stop Hook이 missions.json 확인하여 block/allow 결정 (Flow #3 상세) |
| 7 | Session Manager | 종료 감지 | `result` 이벤트 수신 또는 프로세스 exit 감지. exit code 분석 |
| 8 | State Manager | 결과 기록 | `sessions.json`에 세션 기록 추가. `missions.json`에서 미션 상태 갱신. Claude Code가 기록한 `friction.json` 변경 반영 |
| 9 | Supervisor | 후처리 | Slack 상태 알림, TUI 데이터 갱신, 자기개선/드리프트/컨텍스트 갱신 조건 평가, 주기적 아카이브 순환 (완료된 미션/해소된 friction을 `state/archive/*.jsonl`로 이동) |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `state/sessions.json` | 세션 기록 추가 (session_id, mission, outcome, summary, duration, cost) |
| `state/missions.json` | 현재 미션 status 변경 (pending → in_progress → completed/failed) |
| `state/friction.json` | Claude Code가 작업 중 기록한 마찰 항목 추가 |
| `state/archive/*.jsonl` | 주기적으로 완료된 미션, 해소된 friction, 종료된 세션을 JSONL 아카이브로 이동 |
| `run/current_session.json` | 현재 세션 정보 갱신 (session_id, start_time, mission_id) |
| `run/supervisor.heartbeat` | 주기적 타임스탬프 갱신 |
| Git tag | `checkpoint-{timestamp}` 태그 생성 |

### 에러 처리
Normal Operation Cycle 내에서 발생하는 에러는 에러 유형에 따라 Error Recovery Flow (Flow #4)로 위임된다. 이 루프 자체는 어떤 에러가 발생해도 중단되지 않는다.

### 종료 조건
이 루프는 종료되지 않는다. Supervisor 프로세스가 살아있는 한 무한 반복한다. Supervisor가 죽으면 launchd KeepAlive가 재시작하고, Watchdog가 보조 감시한다.

---

## 3. Stop Hook Decision Flow (Stop Hook 결정 흐름)

### 트리거 조건
Claude Code가 응답을 완료하고 정지(stop)하려 할 때 `Stop` 이벤트가 발생한다. `.claude/settings.json`에 등록된 Stop Hook (`system/hooks/on_stop.py`)이 호출된다.

### 시퀀스 다이어그램

```
Claude Code          Stop Hook              State Manager         Supervisor
    |                    |                       |                     |
    | stop 시도          |                       |                     |
    | (응답 완료)        |                       |                     |
    |------------------->|                       |                     |
    | stdin: {           |                       |                     |
    |   session_id,      |                       |                     |
    |   stop_hook_active,|                       |                     |
    |   last_assistant_  |                       |                     |
    |   message,         |                       |                     |
    |   transcript_path  |                       |                     |
    | }                  |                       |                     |
    |                    |                       |                     |
    |                    | [1] stop_hook_active  |                     |
    |                    |     확인              |                     |
    |                    |                       |                     |
    |                    |  ┌─ false ───────────────────────────────┐  |
    |                    |  │ (첫 번째 stop이 아님 = 이미 block    │  |
    |                    |  │  되었다가 재시도. 항상 allow)         │  |
    |                    |  │ → ALLOW (exit 0)                     │  |
    |                    |  └──────────────────────────────────────┘  |
    |                    |                       |                     |
    |                    |  ┌─ true (정상 경로) ─┐|                     |
    |                    |  │                    │|                     |
    |                    |  │ [2] max_iterations |                     |
    |                    |  │     도달 확인      │|                     |
    |                    |  │                    │|                     |
    |                    |  │ config.toml의      │|                     |
    |                    |  │ max_iterations_    │|                     |
    |                    |  │ per_session 확인   │|                     |
    |                    |  │                    │|                     |
    |                    |  │  ┌─ 도달 ──────────┘|                     |
    |                    |  │  │ → ALLOW (exit 0) |                     |
    |                    |  │  │   "최대 반복 도달"|                     |
    |                    |  │  └──────────────────┘|                     |
    |                    |  │                    │|                     |
    |                    |  │  ┌─ 미도달 ────────┘|                     |
    |                    |  │  │                  |                     |
    |                    |  │  │ [3] 컨텍스트    │|                     |
    |                    |  │  │     갱신 필요?  │|                     |
    |                    |  │  │                  |                     |
    |                    |  │  │ compaction 횟수 │|                     |
    |                    |  │  │ >= threshold    │|                     |
    |                    |  │  │                  |                     |
    |                    |  │  │  ┌─ 필요 ───────┘|                     |
    |                    |  │  │  │ → ALLOW (exit 0)                   |
    |                    |  │  │  │   "컨텍스트 갱신 필요"              |
    |                    |  │  │  └──────────────┘|                     |
    |                    |  │  │                  |                     |
    |                    |  │  │  ┌─ 불필요 ─────┘|                     |
    |                    |  │  │  │               |                     |
    |                    |  │  │  │ [4] missions  |                     |
    |                    |  │  │  │     .json 읽기|                     |
    |                    |  │  │  |-------------->|                     |
    |                    |  │  │  |               |                     |
    |                    |  │  │  |<--------------|                     |
    |                    |  │  │  │ pending 미션  |                     |
    |                    |  │  │  │ 목록 반환     |                     |
    |                    |  │  │  │               |                     |
    |                    |  │  │  │  ┌─ pending 미션 있음 ────────────┐|
    |                    |  │  │  │  │                                │|
    |                    |  │  │  │  │ [5] BLOCK (exit 2)            │|
    |                    |  │  │  │  │     다음 미션 컨텍스트 주입   │|
    |                    |  │  │  │  │     reason: "다음 미션:       │|
    |                    |  │  │  │  │     {title}. {description}"   │|
    |                    |  │  │  │  │                                │|
    |                    |  │  │  │  └────────────────────────────────┘|
    |                    |  │  │  │               |                     |
    |                    |  │  │  │  ┌─ pending 미션 없음 ───────────┐|
    |                    |  │  │  │  │                                │|
    |                    |  │  │  │  │ [6] BLOCK (exit 2)            │|
    |                    |  │  │  │  │     미션 생성 위임            │|
    |                    |  │  │  │  │     reason: "Mission 큐 비었음│|
    |                    |  │  │  │  │     Purpose에 따라 다음 할 일 │|
    |                    |  │  │  │  │     을 스스로 결정하고        │|
    |                    |  │  │  │  │     missions.json에 추가한 후 │|
    |                    |  │  │  │  │     실행하라."                │|
    |                    |  │  │  │  │                                │|
    |                    |  │  │  │  └────────────────────────────────┘|
    |                    |                       |                     |
    |<-------------------|                       |                     |
    | BLOCK: reason 주입 |                       |                     |
    | → Claude Code 계속 |                       |                     |
    |   실행 (새 미션)   |                       |                     |
    |                    |                       |                     |
    | 또는               |                       |                     |
    |                    |                       |                     |
    |<-------------------|                       |                     |
    | ALLOW: 세션 종료   |                       |                     |
    | → Supervisor가     |                       |                     |
    |   새 세션 시작     |                       |                     |
```

### 결정 로직 요약

```
stop_hook_active가 false?
  └─ YES → ALLOW (안전 장치: 무한 루프 방지)

max_iterations 도달?
  └─ YES → ALLOW (세션 교체 필요)

compaction 횟수 >= context_refresh_after_compactions?
  └─ YES → ALLOW (컨텍스트 갱신 필요, Flow #12)

missions.json에 pending 미션 있음?
  └─ YES → BLOCK + 다음 미션 컨텍스트 주입

missions.json에 pending 미션 없음?
  └─ BLOCK + 미션 자율 생성 위임 (P-3)
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | Stop Hook | `stop_hook_active` 확인 | stdin JSON의 `stop_hook_active` 필드. `false`면 이미 한 번 block된 후 재시도이므로 무조건 allow. 무한 block 방지 안전장치 |
| 2 | Stop Hook | Max iterations 확인 | `state/config.toml`의 `max_iterations_per_session` (기본: 20)과 현재 세션 iteration 카운트 비교 |
| 3 | Stop Hook | 컨텍스트 갱신 필요 확인 | `run/current_session.json`의 `compaction_count`와 `config.toml`의 `context_refresh_after_compactions` (기본: 5) 비교 |
| 4 | Stop Hook | 미션 큐 읽기 | `state/missions.json`에서 `status=pending`, `blockers=[]`인 미션 필터링 |
| 5 | Stop Hook | BLOCK + 미션 주입 | stdout JSON으로 `decision: "block"` + `reason`에 다음 미션의 title, description, success_criteria 포함 |
| 6 | Stop Hook | BLOCK + 생성 위임 | stdout JSON으로 `decision: "block"` + `reason`에 "Purpose에 따라 스스로 미션을 생성하고 실행하라" 지시 포함 |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `state/missions.json` | 현재 미션 status 갱신 (Claude Code가 완료 표시한 경우) |
| `run/current_session.json` | iteration_count 증가 |

### 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| Stop Hook 스크립트 자체 크래시 | Claude Code가 기본 동작(allow) 수행. Supervisor가 감지하여 friction 기록 |
| `missions.json` 읽기 실패 | ALLOW 반환 (안전 방향). Supervisor가 다음 루프에서 복구 |
| Stop Hook timeout (10초) | Claude Code가 기본 동작(allow) 수행 |
| `stop_hook_active=false`인데 여전히 미션 잔여 | ALLOW. Supervisor가 새 세션에서 처리 |

### 종료 조건
ALLOW 반환 시 Claude Code 프로세스가 종료되고 Supervisor의 Normal Operation Cycle로 복귀. BLOCK 반환 시 Claude Code가 계속 실행.

---

## 4. Error Recovery Flow (에러 복구 흐름)

### 트리거 조건
Claude Code 세션 실행 중 또는 Supervisor 운영 중 에러 발생 시.

### 시퀀스 다이어그램

```
Supervisor          Error Classifier     State Manager      Session Manager    Slack Client
  |                      |                   |                   |                  |
  | [에러 감지]          |                   |                   |                  |
  | stream-json에서      |                   |                   |                  |
  | 에러 이벤트 또는     |                   |                   |                  |
  | 프로세스 비정상 종료 |                   |                   |                  |
  |                      |                   |                   |                  |
  | [1] 에러 분류 요청   |                   |                   |                  |
  |--------------------->|                   |                   |                  |
  |                      |                   |                   |                  |
  |                      | [2] 에러 유형     |                   |                  |
  |                      |     판별          |                   |                  |
  |                      |                   |                   |                  |
  |                      | ┌─────────────────────────────────────────────────────┐ |
  |                      | │ 분류 기준:                                          │ |
  |                      | │                                                     │ |
  |                      | │ exit_code + stderr + stream-json 이벤트 분석       │ |
  |                      | │                                                     │ |
  |                      | │ TRANSIENT   : 일시적 API 에러 (500, 502, 503)      │ |
  |                      | │ RATE_LIMIT  : 429 또는 system/api_retry rate_limit │ |
  |                      | │ AUTH        : 401, 403, authentication_failed      │ |
  |                      | │ CORRUPTION  : state 파일 파싱 실패, JSON 손상       │ |
  |                      | │ CRASH       : 프로세스 비정상 종료 (SIGSEGV 등)    │ |
  |                      | │ NETWORK     : DNS 실패, connection refused         │ |
  |                      | │ STUCK       : heartbeat 정상이나 출력 없음 (N분)   │ |
  |                      | └─────────────────────────────────────────────────────┘ |
  |                      |                   |                   |                  |
  |<---------------------|                   |                   |                  |
  |  에러 유형 + 복구    |                   |                   |                  |
  |  전략 반환           |                   |                   |                  |
  |                      |                   |                   |                  |
  | [3] Friction 기록    |                   |                   |                  |
  |------------------------------------->|                   |                  |
  |                      |                   | friction.json에   |                  |
  |                      |                   | 에러 기록         |                  |
  |                      |                   | {type, message,   |                  |
  |                      |                   |  timestamp,       |                  |
  |                      |                   |  recovery_action} |                  |
  |                      |                   |                   |                  |
  | [4] 복구 전략 실행   |                   |                   |                  |
  |                      |                   |                   |                  |
  |  ┌─ TRANSIENT ───────────────────────────────────────────────────────────────┐
  |  │ 즉시 재시도. exponential backoff (2s → 4s → 8s → 16s → 32s)             │
  |  │ 최대 5회. 실패 시 NETWORK로 재분류                                       │
  |  └──────────────────────────────────────────────────────────────────────────┘
  |                      |                   |                   |                  |
  |  ┌─ RATE_LIMIT ──────────────────────────────────────────────────────────────┐
  |  │ [4a] stream-json에서 retry_delay_ms 추출                                 │
  |  │ [4b] 해당 시간만큼 대기                                                  │
  |  │ [4c] --resume {session_id} 로 세션 재개 시도                             │
  |  │ [4d] 재개 실패 시 fresh session (Flow #12 변형)                          │
  |  │                                                                           │
  |  │  Supervisor ──────────────────────> Session Manager                       │
  |  │      | retry_delay 대기 후         |                                     │
  |  │      |----------------------------->| claude --resume {id} -p "continue"  │
  |  │      |                              |----> Claude Code                    │
  |  │      |<-----------------------------|                                     │
  |  └──────────────────────────────────────────────────────────────────────────┘
  |                      |                   |                   |                  |
  |  ┌─ AUTH ────────────────────────────────────────────────────────────────────┐
  |  │ [4e] 재인증 불가능 (Claude Max는 OAuth 기반)                             │
  |  │ [4f] Slack으로 Owner에게 즉시 알림                                       │
  |  │      "인증 오류 발생. claude login 실행 필요"                            │
  |  │ [4g] 30분 간격으로 재시도 (무한)                                        │
  |  │                                                                           │
  |  │  Supervisor ──────────────────────> Slack Client                          │
  |  │      |----------------------------->| Owner 알림 전송                     │
  |  │      |                              |                                     │
  |  │      | 30분 대기 후 재시도          |                                     │
  |  └──────────────────────────────────────────────────────────────────────────┘
  |                      |                   |                   |                  |
  |  ┌─ CORRUPTION ──────────────────────────────────────────────────────────────┐
  |  │ [4h] 손상된 파일 식별                                                    │
  |  │ [4i] 마지막 Git checkpoint에서 해당 파일 복구                            │
  |  │      git checkout checkpoint-{latest} -- state/{file}                    │
  |  │ [4j] 복구 실패 시 기본값으로 재생성                                     │
  |  │ [4k] Slack으로 Owner 알림                                                │
  |  │                                                                           │
  |  │  Supervisor ──────────────────────> State Manager                         │
  |  │      |----------------------------->| git checkout로 파일 복구            │
  |  │      |<-----------------------------|                                     │
  |  └──────────────────────────────────────────────────────────────────────────┘
  |                      |                   |                   |                  |
  |  ┌─ CRASH ──────────────────────────────────────────────────────────────────┐
  |  │ (Flow #8 Session Crash Recovery로 위임)                                  │
  |  └──────────────────────────────────────────────────────────────────────────┘
  |                      |                   |                   |                  |
  |  ┌─ NETWORK ─────────────────────────────────────────────────────────────────┐
  |  │ [4l] 네트워크 연결 확인 (DNS + HTTP 테스트)                              │
  |  │ [4m] 연결 불가: 1분 간격 재시도 (무한)                                  │
  |  │ [4n] 연결 복구 시 fresh session 시작                                     │
  |  │ [4o] 5분 이상 지속 시 Slack 알림 (Slack 자체가 안 되면 로컬 로그만)     │
  |  └──────────────────────────────────────────────────────────────────────────┘
  |                      |                   |                   |                  |
  |  ┌─ STUCK ──────────────────────────────────────────────────────────────────┐
  |  │ [4p] SIGTERM 전송 (10초 대기)                                            │
  |  │ [4q] 응답 없으면 SIGKILL                                                 │
  |  │ [4r] friction 기록 + fresh session 시작                                  │
  |  │                                                                           │
  |  │  Supervisor ──────────────────────> Session Manager                       │
  |  │      |----------------------------->| proc.terminate()                    │
  |  │      | 10s timeout                  |                                     │
  |  │      |----------------------------->| proc.kill() (필요시)                │
  |  │      |<-----------------------------|                                     │
  |  └──────────────────────────────────────────────────────────────────────────┘
  |                      |                   |                   |                  |
  | [5] 복구 결과 기록   |                   |                   |                  |
  |------------------------------------->|                   |                  |
  |                      |                   | friction.json     |                  |
  |                      |                   | recovery_result   |                  |
  |                      |                   | 추가              |                  |
  |                      |                   |                   |                  |
  | [6] 정상 루프 복귀   |                   |                   |                  |
  |   (Flow #2로)        |                   |                   |                  |
```

### 에러 분류표

| 유형 | 감지 방법 | 복구 전략 | 재시도 간격 | 최대 재시도 | 에스컬레이션 |
|------|-----------|-----------|-------------|-------------|-------------|
| `TRANSIENT` | exit_code != 0 + 일시적 패턴 | 즉시 재시도 | 2s exponential | 5회 | NETWORK로 재분류 |
| `RATE_LIMIT` | stream-json `api_retry` `rate_limit` | 대기 후 resume | `retry_delay_ms` | 무한 | 없음 (항상 복구) |
| `AUTH` | `authentication_failed` / 401 / 403 | Owner 알림 + 주기적 재시도 | 30분 | 무한 | Slack 알림 |
| `CORRUPTION` | JSON 파싱 실패 | Git 체크포인트 복구 | 즉시 | 1회 | 기본값 재생성 |
| `CRASH` | 비정상 exit (SIGSEGV 등) | Flow #8로 위임 | - | - | - |
| `NETWORK` | DNS/연결 실패 | 주기적 재시도 | 1분 | 무한 | 5분 후 Slack 알림 |
| `STUCK` | 출력 없음 N분 | SIGTERM → SIGKILL | 즉시 | 1회 | fresh session |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `state/friction.json` | 에러 기록 추가 (type, message, recovery_action, recovery_result) |
| `state/sessions.json` | 세션 outcome을 "error" 또는 "recovered"로 기록 |
| `state/*` (CORRUPTION 시) | Git 체크포인트에서 복구된 파일 |

### 종료 조건
복구 전략이 성공하면 Normal Operation Cycle (Flow #2)로 복귀. AUTH 에러의 경우 Owner가 `claude login`을 실행할 때까지 재시도 루프 유지.

---

## 5. Owner Interaction Flow (Owner 상호작용 흐름)

### 트리거 조건
Claude Code가 미션 실행 중 AI가 해결할 수 없는 Blocker를 만났을 때 (API 토큰 필요, 계정 생성 필요, 외부 승인 필요 등).

### 시퀀스 다이어그램

```
Claude Code        State Manager       Supervisor        Slack Client         Owner
    |                   |                  |                  |                  |
    | [1] Blocker 감지  |                  |                  |                  |
    | "GitHub API 토큰  |                  |                  |                  |
    |  필요"            |                  |                  |                  |
    |                   |                  |                  |                  |
    | [2] 요청 생성     |                  |                  |                  |
    |------------------>|                  |                  |                  |
    |  requests.json에  |                  |                  |                  |
    |  새 요청 추가     |                  |                  |                  |
    |  {                |                  |                  |                  |
    |    id: "R-001",   |                  |                  |                  |
    |    type: "token", |                  |                  |                  |
    |    question: "...",|                 |                  |                  |
    |    mission_id:    |                  |                  |                  |
    |      "M-005",     |                  |                  |                  |
    |    status:        |                  |                  |                  |
    |      "pending",   |                  |                  |                  |
    |    created_at     |                  |                  |                  |
    |  }                |                  |                  |                  |
    |                   |                  |                  |                  |
    | [3] 미션에 blocker|                  |                  |                  |
    |     추가          |                  |                  |                  |
    |------------------>|                  |                  |                  |
    |  missions.json    |                  |                  |                  |
    |  M-005.blockers = |                  |                  |                  |
    |    ["R-001"]      |                  |                  |                  |
    |  M-005.status =   |                  |                  |                  |
    |    "blocked"      |                  |                  |                  |
    |                   |                  |                  |                  |
    | [4] 다음 미션으로 |                  |                  |                  |
    |     전환          |                  |                  |                  |
    | (Stop Hook이      |                  |                  |                  |
    |  block되지 않은   |                  |                  |                  |
    |  다른 pending     |                  |                  |                  |
    |  미션 주입)       |                  |                  |                  |
    |                   |                  |                  |                  |
    |                   |                  | [5] Slack 전송   |                  |
    |                   |                  |  (requests.json  |                  |
    |                   |                  |   변경 감지)     |                  |
    |                   |                  |----------------->|                  |
    |                   |                  |                  | [6] 새 Slack     |
    |                   |                  |                  | 스레드 생성      |
    |                   |                  |                  |                  |
    |                   |                  |                  | 메시지:          |
    |                   |                  |                  | "[요청 R-001]    |
    |                   |                  |                  |  미션 M-005 진행 |
    |                   |                  |                  |  중 GitHub API   |
    |                   |                  |                  |  토큰이          |
    |                   |                  |                  |  필요합니다.     |
    |                   |                  |                  |  ..."            |
    |                   |                  |                  |----------------->|
    |                   |                  |                  |                  |
    |                   |                  |                  |  thread_ts 저장  |
    |                   |                  |                  |                  |
    |   ... (시간 경과 — 시스템은 다른 미션을 계속 실행) ...                    |
    |                   |                  |                  |                  |
    |                   |                  |                  |                  | [7] Owner
    |                   |                  |                  |                  | 스레드에
    |                   |                  |                  |                  | 응답
    |                   |                  |                  |<-----------------|
    |                   |                  |                  | Socket Mode      |
    |                   |                  |                  | 이벤트 수신      |
    |                   |                  |                  |                  |
    |                   |                  | [8] 응답 처리    |                  |
    |                   |                  |<-----------------|                  |
    |                   |                  |  thread_ts →     |                  |
    |                   |                  |  request_id      |                  |
    |                   |                  |  매핑            |                  |
    |                   |                  |                  |                  |
    |                   | [9] 요청 갱신    |                  |                  |
    |                   |<-----------------|                  |                  |
    |                   | requests.json    |                  |                  |
    |                   | R-001.status =   |                  |                  |
    |                   |   "answered"     |                  |                  |
    |                   | R-001.answer =   |                  |                  |
    |                   |   Owner 응답 내용|                  |                  |
    |                   |                  |                  |                  |
    |                   | [10] Blocker 해제|                  |                  |
    |                   |<-----------------|                  |                  |
    |                   | missions.json    |                  |                  |
    |                   | M-005.blockers = |                  |                  |
    |                   |   []             |                  |                  |
    |                   | M-005.status =   |                  |                  |
    |                   |   "pending"      |                  |                  |
    |                   |                  |                  |                  |
    |                   |                  | [11] Slack 확인  |                  |
    |                   |                  |----------------->|                  |
    |                   |                  |                  | 스레드에         |
    |                   |                  |                  | "응답 수신.      |
    |                   |                  |                  |  미션 재개       |
    |                   |                  |                  |  예정입니다."    |
    |                   |                  |                  |                  |
    | [12] 다음 루프에서 |                 |                  |                  |
    |      M-005가      |                  |                  |                  |
    |      pending으로   |                 |                  |                  |
    |      다시 선택됨   |                 |                  |                  |
    |      (Owner 응답   |                 |                  |                  |
    |       포함하여     |                 |                  |                  |
    |       프롬프트에   |                 |                  |                  |
    |       주입)        |                 |                  |                  |
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | Claude Code | Blocker 감지 | 미션 실행 중 AI가 해결 불가능한 장애 식별. CLAUDE.md의 프로토콜에 따라 Blocker 처리 |
| 2 | Claude Code → State Manager | 요청 생성 | `state/requests.json`에 새 요청 항목 추가. 고유 ID (R-NNN), 질문 내용, 관련 미션 ID, 상태=pending |
| 3 | Claude Code → State Manager | Blocker 등록 | `state/missions.json`에서 해당 미션의 `blockers` 배열에 요청 ID 추가, `status`를 "blocked"로 변경 |
| 4 | Claude Code / Stop Hook | 미션 전환 | 현재 미션이 blocked되므로 Stop Hook이 다음 block되지 않은 pending 미션을 주입 |
| 5 | Supervisor | Slack 전송 트리거 | `requests.json` 변경을 감지 (파일 감시 또는 루프 내 확인) |
| 6 | Slack Client | 스레드 생성 | 새 Slack 스레드로 요청 메시지 전송. `thread_ts`를 `requests.json`에 기록 |
| 7 | Owner | 응답 | Slack 스레드에 자연어로 응답 (예: "ghp_xxxx... 여기 토큰이야") |
| 8 | Slack Client | Socket Mode 이벤트 | `message` 이벤트 수신. `thread_ts`로 해당 요청 식별 |
| 9 | Supervisor → State Manager | 요청 갱신 | `requests.json`에서 해당 요청의 `status`를 "answered"로, `answer`에 Owner 응답 내용 기록 |
| 10 | Supervisor → State Manager | Blocker 해제 | `missions.json`에서 해당 미션의 `blockers`에서 요청 ID 제거. `blockers`가 비면 `status`를 "pending"으로 변경 |
| 11 | Slack Client | 확인 메시지 | 같은 스레드에 "응답 수신. 미션 재개 예정입니다." 메시지 전송 |
| 12 | Supervisor | 미션 재개 | 다음 루프에서 unblocked된 미션이 선택 대상에 포함. Owner 응답이 세션 프롬프트에 주입 |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `state/requests.json` | 새 요청 추가 → status: pending → answered. thread_ts 기록 |
| `state/missions.json` | 미션 status: in_progress → blocked → pending. blockers 배열 변경 |

### 동시 요청 처리 (O-3)
여러 요청이 동시에 존재할 수 있다. 각 요청은 독립 Slack 스레드를 가지므로 Owner는 아무 순서로 응답할 수 있다. Supervisor는 각 `thread_ts`를 `request_id`에 매핑하여 어떤 스레드 응답이 어떤 요청에 해당하는지 식별한다.

### 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| Slack 메시지 전송 실패 | 재시도 3회. 실패 시 로컬 로그에 기록, 다음 루프에서 재전송 시도 |
| Owner 응답 파싱 불가 | 원문 그대로 `answer`에 저장. Claude Code가 해석 |
| 같은 스레드에 Owner가 여러 번 응답 | 마지막 응답으로 갱신 (이전 응답도 기록 유지) |
| Socket Mode 연결 끊김 | `slack-bolt` 자동 재연결. 재연결 실패 시 Supervisor가 Slack Client 재초기화 |

### 종료 조건
Owner 응답이 수신되어 Blocker가 해제되고, 해당 미션이 다시 pending 상태로 돌아가면 이 흐름 종료.

---

## 6. Self-Improvement Flow (자기개선 흐름)

### 트리거 조건
`state/friction.json`에 동일 `pattern_key`의 Friction이 임계값(`config.toml`의 `friction_threshold`, 기본: 3)에 도달할 때.

### 시퀀스 다이어그램

```
Supervisor          State Manager       Session Manager     Claude Code
  |                      |                   |                  |
  | [1] 후처리 단계에서  |                   |                  |
  |     friction 확인    |                   |                  |
  |--------------------->|                   |                  |
  |                      | friction.json     |                  |
  |                      | 읽기              |                  |
  |                      |                   |                  |
  |                      | [2] pattern_key별 |                  |
  |                      |     집계          |                  |
  |                      |                   |                  |
  |                      | ┌───────────────────────────────────────────────┐
  |                      | │ pattern_key 예시:                             │
  |                      | │   error:json_parse  — 3회 (임계값 도달)      │
  |                      | │   error:timeout     — 1회                    │
  |                      | │   quality:test_fail — 2회                    │
  |                      | └───────────────────────────────────────────────┘
  |                      |                   |                  |
  |<---------------------|                   |                  |
  |  임계값 도달 pattern_key|                   |                  |
  |  목록 반환           |                   |                  |
  |                      |                   |                  |
  |  ┌─ 임계값 미도달 ─────────────────────────────────────┐  |
  |  │ → 아무 동작 없음. Flow #2로 복귀                    │  |
  |  └─────────────────────────────────────────────────────┘  |
  |                      |                   |                  |
  |  ┌─ 임계값 도달 ──────────────────────────────────────┐   |
  |  │                                                     │   |
  | [3] 자기개선 Mission |                   |                  |
  |     자동 생성        |                   |                  |
  |--------------------->|                   |                  |
  |                      | missions.json에   |                  |
  |                      | 추가:             |                  |
  |                      | {                 |                  |
  |                      |   id: "M-SI-001", |                  |
  |                      |   title: "자기개선:|                  |
  |                      |     JSON 파싱 에러|                  |
  |                      |     반복 해결",   |                  |
  |                      |   priority: 0,    |                  |
  |                      |   source: "friction",               |
  |                      |   friction_refs:  |                  |
  |                      |     ["F-012",     |                  |
  |                      |      "F-015",     |                  |
  |                      |      "F-018"]     |                  |
  |                      | }                 |                  |
  |                      |                   |                  |
  | [4] priority=0이므로 |                   |                  |
  |     다음 루프에서    |                   |                  |
  |     즉시 선택됨      |                   |                  |
  |                      |                   |                  |
  | [5] 자기개선 세션    |                   |                  |
  |------------------------------------->|                  |
  |                      |                   | claude -p        |
  |                      |                   | "<self_improve   |
  |                      |                   |   _prompt>"      |
  |                      |                   |----------------->|
  |                      |                   |                  |
  |                      |                   |                  | [6] Friction 분석
  |                      |                   |                  |   - friction.json
  |                      |                   |                  |     참조된 항목 읽기
  |                      |                   |                  |   - 패턴 식별
  |                      |                   |                  |   - 근본 원인 추론
  |                      |                   |                  |
  |                      |                   |                  | [7] 개선 대상 결정
  |                      |                   |                  |   (제한 없음 — S-4)
  |                      |                   |                  |
  |                      |                   |                  |   개선 가능 대상:
  |                      |                   |                  |   ├── CLAUDE.md
  |                      |                   |                  |   ├── .claude/rules/
  |                      |                   |                  |   ├── state/strategy.json
  |                      |                   |                  |   ├── state/config.toml
  |                      |                   |                  |   │   (임계값 자체도
  |                      |                   |                  |   │    개선 대상 — S-5)
  |                      |                   |                  |   ├── system/hooks/
  |                      |                   |                  |   ├── system/*.py
  |                      |                   |                  |   └── tui/*.py
  |                      |                   |                  |
  |                      |                   |                  | [8] 개선 실행
  |                      |                   |                  |   - 파일 수정
  |                      |                   |                  |   - 테스트 실행
  |                      |                   |                  |   - 테스트 통과 확인
  |                      |                   |                  |
  |                      |                   |                  | [9] Git commit
  |                      |                   |                  |   "self-improvement:
  |                      |                   |                  |    {개선 요약}"
  |                      |                   |                  |
  |                      |                   |                  | [10] Friction 해소
  |                      |                   |                  |      기록
  |                      |                   |                  |----> State Manager
  |                      |                   |                  |      friction.json에
  |                      |                   |                  |      resolved_at 기록
  |                      |                   |                  |
  |                      |                   |                  | [11] 개선 결과 보고
  |                      |                   |                  |      missions.json에
  |                      |                   |                  |      M-SI-001 완료
  |                      |                   |                  |
  |<-----------------------------------------------------|
  |  세션 종료           |                   |                  |
  |                      |                   |                  |
  | [12] Slack 알림      |                   |                  |
  |  "자기개선 완료:     |                   |                  |
  |   {개선 요약}"       |                   |                  |
  |                      |                   |                  |
  | [LOOP 복귀]          |                   |                  |
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | Supervisor | Friction 확인 | 매 루프 후처리에서 `friction.json`의 미해결 항목 확인 |
| 2 | State Manager | pattern_key별 집계 | `friction.json`에서 `resolved_at`이 없는 항목을 `pattern_key`별로 그룹화. 각 그룹의 개수를 `friction_threshold`와 비교 |
| 3 | Supervisor | 자기개선 Mission 생성 | `priority: 0` (최고). `source: "friction"`. 관련 friction 항목의 ID 배열을 `friction_refs`에 포함 |
| 4 | Supervisor | 즉시 선택 | `priority: 0`은 모든 일반 미션(priority >= 1)보다 우선 |
| 5 | Session Manager | 자기개선 세션 시작 | 특수 프롬프트 사용. Friction 상세 + 개선 범위 + 테스트 요구사항 포함 |
| 6 | Claude Code | Friction 분석 | 참조된 friction 항목을 읽고 패턴 식별. "같은 JSON 파싱 에러가 3회 → state_manager.py의 파싱 로직 문제" 등 |
| 7 | Claude Code | 개선 대상 결정 | 근본 원인에 따라 수정 대상 파일 결정. 범위 제한 없음 (S-4) |
| 8 | Claude Code | 개선 실행 | 코드 수정 → `uv run pytest` 등 테스트 실행 → 통과 확인. 테스트 실패 시 수정 반복 |
| 9 | Claude Code | Git commit | 개선 사항을 독립 커밋으로 기록 |
| 10 | Claude Code | Friction 해소 | `friction.json`에서 해당 항목들의 `resolved_at` 필드에 타임스탬프 기록, `resolved_by` 필드에 미션 ID 기록 |
| 11 | Claude Code | 완료 보고 | `missions.json`에서 자기개선 미션 status를 "completed"로 변경 |
| 12 | Supervisor | Slack 알림 | Owner에게 자기개선 결과 요약 전송 |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `state/missions.json` | 자기개선 Mission 추가 (priority: 0) → 완료 |
| `state/friction.json` | 관련 항목에 resolved_at, resolved_by 추가 |
| `state/sessions.json` | 자기개선 세션 기록 추가 |
| 개선 대상 파일들 | 코드 수정 (CLAUDE.md, hooks, system/, tui/ 등) |
| `state/config.toml` | 임계값 자체 수정 가능 (S-5) |
| Git | 자기개선 커밋 생성 |

### 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| 자기개선으로 시스템 파손 | Git checkpoint에서 롤백 가능. 파손 자체가 새 friction으로 기록 |
| 테스트 실패 | Claude Code가 수정 반복. 최종 실패 시 변경 사항 revert |
| 자기개선 세션 크래시 | Flow #8로 위임. 자기개선 미션은 pending으로 남아 재시도 |
| 동일 friction 반복 해결 실패 | friction_threshold를 자동 증가시켜 다음 축적까지 대기 (config.toml 수정) |

### 종료 조건
자기개선 세션이 완료되고 friction이 해소 기록되면 종료. Normal Operation Cycle로 복귀.

---

## 7. Proactive Improvement Flow (사전적 자기개선 흐름)

### 트리거 조건
완료된 미션 수가 `config.toml`의 `proactive_improvement_interval` (기본: 10)의 배수에 도달할 때. Friction 없이도 주기적으로 실행.

### 시퀀스 다이어그램

```
Supervisor          State Manager       Session Manager     Claude Code
  |                      |                   |                  |
  | [1] 후처리에서       |                   |                  |
  |     미션 카운트 확인 |                   |                  |
  |--------------------->|                   |                  |
  |                      | sessions.json     |                  |
  |                      | 완료 미션 수 =    |                  |
  |                      | 30 (10의 배수)    |                  |
  |<---------------------|                   |                  |
  |                      |                   |                  |
  | [2] 사전 개선        |                   |                  |
  |     Mission 생성     |                   |                  |
  |--------------------->|                   |                  |
  |                      | missions.json:    |                  |
  |                      | {                 |                  |
  |                      |   id: "M-PI-003", |                  |
  |                      |   title: "사전적  |                  |
  |                      |     시스템 검토   |                  |
  |                      |     #3",          |                  |
  |                      |   priority: 0,    |                  |
  |                      |   source:         |                  |
  |                      |     "proactive"   |                  |
  |                      | }                 |                  |
  |                      |                   |                  |
  | [3] 시스템 검토 세션 |                   |                  |
  |------------------------------------->|                  |
  |                      |                   |----------------->|
  |                      |                   |                  |
  |                      |                   |                  | [4] 전반적 검토
  |                      |                   |                  |
  |                      |                   |                  | ┌──────────────────────┐
  |                      |                   |                  | │ 검토 영역:           │
  |                      |                   |                  | │                      │
  |                      |                   |                  | │ A. Purpose 정렬도    │
  |                      |                   |                  | │    purpose.json과    │
  |                      |                   |                  | │    최근 미션 비교    │
  |                      |                   |                  | │                      │
  |                      |                   |                  | │ B. 전략 효과성       │
  |                      |                   |                  | │    strategy.json과   │
  |                      |                   |                  | │    성공률 분석       │
  |                      |                   |                  | │                      │
  |                      |                   |                  | │ C. 도구 사용 패턴   │
  |                      |                   |                  | │    sessions.json에서 │
  |                      |                   |                  | │    도구 활용 분석    │
  |                      |                   |                  | │                      │
  |                      |                   |                  | │ D. Friction 트렌드  │
  |                      |                   |                  | │    friction.json에서 │
  |                      |                   |                  | │    장기 패턴 분석    │
  |                      |                   |                  | │                      │
  |                      |                   |                  | │ E. 코드 품질        │
  |                      |                   |                  | │    system/, hooks/   │
  |                      |                   |                  | │    코드 리뷰         │
  |                      |                   |                  | │                      │
  |                      |                   |                  | │ F. 설정 최적화      │
  |                      |                   |                  | │    config.toml       │
  |                      |                   |                  | │    임계값 적절성     │
  |                      |                   |                  | └──────────────────────┘
  |                      |                   |                  |
  |                      |                   |                  | [5] 개선점 발견?
  |                      |                   |                  |
  |                      |                   |                  |  ┌─ 없음 ─────────────┐
  |                      |                   |                  |  │ "시스템 양호" 보고  │
  |                      |                   |                  |  │ 미션 완료            │
  |                      |                   |                  |  └──────────────────────┘
  |                      |                   |                  |
  |                      |                   |                  |  ┌─ 있음 ─────────────┐
  |                      |                   |                  |  │                      │
  |                      |                   |                  |  │ [6] 즉시 실행 가능한│
  |                      |                   |                  |  │     개선 → 실행     │
  |                      |                   |                  |  │                      │
  |                      |                   |                  |  │ [7] 별도 미션 필요한│
  |                      |                   |                  |  │     개선 →          │
  |                      |                   |                  |  │     missions.json에 │
  |                      |                   |                  |  │     추가            │
  |                      |                   |                  |  │                      │
  |                      |                   |                  |  │ [8] Git commit      │
  |                      |                   |                  |  │     (즉시 실행분)   │
  |                      |                   |                  |  │                      │
  |                      |                   |                  |  │ [9] 검토 보고서     │
  |                      |                   |                  |  │     sessions.json에 │
  |                      |                   |                  |  │     기록             │
  |                      |                   |                  |  └──────────────────────┘
  |                      |                   |                  |
  |<-----------------------------------------------------|
  |                      |                   |                  |
  | [10] Slack 알림      |                   |                  |
  |  "시스템 검토 #3 완료|                   |                  |
  |   개선점 N건 발견,   |                   |                  |
  |   M건 즉시 적용"     |                   |                  |
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | Supervisor | 미션 카운트 확인 | `sessions.json`에서 완료 미션 수가 `proactive_improvement_interval`의 배수인지 확인 |
| 2 | Supervisor | Mission 생성 | `priority: 0`, `source: "proactive"`. 이전 검토 이후 변경된 파일 목록을 `context`에 포함 |
| 3 | Session Manager | 검토 세션 시작 | 시스템 검토 전용 프롬프트. 전체 state 파일 + 코드 접근 권한 |
| 4 | Claude Code | 전반적 검토 | 6개 영역 (A~F) 순서대로 검토. 각 영역의 현재 상태 분석 |
| 5 | Claude Code | 개선점 판단 | 검토 결과에서 개선 가능 항목 도출 |
| 6 | Claude Code | 즉시 실행 | 작은 개선 (typo 수정, 설정 조정 등)은 현재 세션에서 즉시 실행 |
| 7 | Claude Code | 미션 생성 | 큰 개선 (리팩토링, 새 기능 등)은 별도 미션으로 `missions.json`에 추가 |
| 8 | Claude Code | Git commit | 즉시 실행한 개선에 대해 커밋 |
| 9 | Claude Code | 검토 보고서 | `sessions.json`에 검토 결과 요약 기록 |
| 10 | Supervisor | Slack 알림 | Owner에게 검토 결과 전송 |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `state/missions.json` | 사전 검토 Mission 추가 + 완료. 추가 개선 Mission 생성 (있을 경우) |
| `state/sessions.json` | 검토 세션 기록 (검토 결과 요약 포함) |
| `state/strategy.json` | 전략 수정 (검토 결과에 따라) |
| `state/config.toml` | 임계값 조정 (검토 결과에 따라) |
| 개선 대상 파일들 | 즉시 실행 가능한 개선 적용 |

### 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| 검토 세션 크래시 | Flow #8로 위임. 사전 검토 미션은 pending으로 남아 재시도 |
| 개선으로 인한 파손 | Git checkpoint로 롤백. friction 기록 |
| 검토 시간 초과 | max_iterations로 세션 종료. 검토 결과 일부만 기록 |

### 종료 조건
검토 세션이 완료되고 결과가 기록되면 종료. Normal Operation Cycle로 복귀.

---

## 8. Session Crash Recovery Flow (세션 크래시 복구 흐름)

### 트리거 조건
Claude Code 프로세스가 비정상 종료될 때 (SIGSEGV, SIGABRT, 예기치 못한 exit code, 프로세스 사라짐 등).

### 시퀀스 다이어그램

```
Session Manager     Error Classifier     State Manager      Supervisor       Slack Client
    |                    |                   |                  |                  |
    | [프로세스 종료 감지]|                   |                  |                  |
    | exit_code != 0     |                   |                  |                  |
    | 또는 SIGKILL/      |                   |                  |                  |
    | SIGSEGV 수신       |                   |                  |                  |
    |                    |                   |                  |                  |
    | [1] 종료 정보 수집 |                   |                  |                  |
    |   - exit_code      |                   |                  |                  |
    |   - signal (있으면)|                   |                  |                  |
    |   - stderr 내용    |                   |                  |                  |
    |   - 마지막 stream  |                   |                  |                  |
    |     -json 이벤트   |                   |                  |                  |
    |   - session_id     |                   |                  |                  |
    |                    |                   |                  |                  |
    | [2] 종료 분류      |                   |                  |                  |
    |------------------->|                   |                  |                  |
    |                    | 분류:             |                  |                  |
    |                    |                   |                  |                  |
    |                    | ┌──────────────────────────────────────────────────┐   |
    |                    | │ RESUMABLE (재개 가능):                           │   |
    |                    | │   - rate_limit (429, api_retry 이벤트 있음)      │   |
    |                    | │   - 일시적 네트워크 오류                          │   |
    |                    | │   - 정상 종료인데 exit_code만 비정상              │   |
    |                    | │                                                  │   |
    |                    | │ NON_RESUMABLE (재개 불가):                        │   |
    |                    | │   - SIGSEGV, SIGABRT (프로세스 메모리 손상)       │   |
    |                    | │   - 인증 실패                                     │   |
    |                    | │   - state 파일 손상 감지                          │   |
    |                    | │   - 원인 불명 크래시 (stderr에 정보 없음)         │   |
    |                    | └──────────────────────────────────────────────────┘   |
    |                    |                   |                  |                  |
    |<-------------------|                   |                  |                  |
    |  분류 결과 반환    |                   |                  |                  |
    |                    |                   |                  |                  |
    | [3] Friction 기록  |                   |                  |                  |
    |--------------------------------------->|                  |                  |
    |                    |                   | friction.json:   |                  |
    |                    |                   | {                |                  |
    |                    |                   |   type:          |                  |
    |                    |                   |     "crash",     |                  |
    |                    |                   |   type: 분류결과,|                  |
    |                    |                   |   exit_code,     |                  |
    |                    |                   |   session_id,    |                  |
    |                    |                   |   mission_id     |                  |
    |                    |                   | }                |                  |
    |                    |                   |                  |                  |
    |  ┌─ RESUMABLE ────────────────────────────────────────────────────────────┐
    |  │                                                                         │
    |  │ [4a] 대기                                                               │
    |  │      rate_limit → retry_delay_ms 만큼                                  │
    |  │      network   → 30초                                                  │
    |  │      기타      → 5초                                                   │
    |  │                                                                         │
    |  │ [4b] 세션 재개 시도                                                     │
    |  │      claude --resume {session_id} -p "이전 세션이 중단되었습니다.      │
    |  │        현재 미션을 계속 진행하세요."                                    │
    |  │      --output-format stream-json                                       │
    |  │      --dangerously-skip-permissions                                    │
    |  │      --strict-mcp-config --mcp-config '{}'                             │
    |  │      --setting-sources project,local                                   │
    |  │      --model opus --effort max                                         │
    |  │                                                                         │
    |  │ [4c] 재개 성공 → 정상 모니터링으로 복귀                                │
    |  │      재개 실패 → NON_RESUMABLE로 전환                                  │
    |  │                                                                         │
    |  └─────────────────────────────────────────────────────────────────────────┘
    |                    |                   |                  |                  |
    |  ┌─ NON_RESUMABLE ────────────────────────────────────────────────────────┐
    |  │                                                                         │
    |  │ [5a] State 복구 확인                                                    │
    |  │      state 파일 무결성 검증                                             │
    |  │      손상 시 Git checkpoint 복구                                        │
    |  │                                                                         │
    |  │ [5b] 세션 이력 기록                                                     │
    |  │      sessions.json에 크래시 세션 기록                                  │
    |  │      outcome: "crashed"                                                │
    |  │      crash_info: {exit_code, signal, stderr_excerpt}                   │
    |  │                                                                         │
    |  │ [5c] Fresh session 시작                                                 │
    |  │      새 claude -p 호출                                                 │
    |  │      프롬프트에 "이전 세션이 크래시로 중단됨" 정보 포함                │
    |  │      미션이 in_progress였으면 해당 미션 계속                            │
    |  │      미션이 상태 불명이면 pending으로 리셋                             │
    |  │                                                                         │
    |  └─────────────────────────────────────────────────────────────────────────┘
    |                    |                   |                  |                  |
    | [6] 심각도 판단    |                   |                  |                  |
    |                    |                   |                  |                  |
    |  ┌─ 일반 크래시 (1회성) ──────────────────────────────────────────────────┐
    |  │ 로그 기록만. Slack 알림 없음                                            │
    |  └─────────────────────────────────────────────────────────────────────────┘
    |                    |                   |                  |                  |
    |  ┌─ 반복 크래시 (같은 미션에서 N회) ──────────────────────────────────────┐
    |  │ [6a] 해당 미션 status = "failed"로 변경                                │
    |  │ [6b] Slack으로 Owner 알림                                              │
    |  │      "미션 M-xxx가 반복 크래시로 실패했습니다"                         │
    |  │ [6c] 다음 미션으로 진행                                                │
    |  └─────────────────────────────────────────────────────────────────────────┘
    |                    |                   |                  |                  |
    |  ┌─ 시스템 수준 크래시 (모든 미션에서 크래시) ────────────────────────────┐
    |  │ [6d] Slack으로 Owner 긴급 알림                                         │
    |  │      "시스템 수준 장애 감지. 확인 필요"                                │
    |  │ [6e] cooldown 진입 (5분 대기 후 재시도)                                │
    |  └─────────────────────────────────────────────────────────────────────────┘
    |                    |                   |                  |                  |
    | [7] 정상 루프 복귀 |                   |                  |                  |
    |    (Flow #2로)     |                   |                  |                  |
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | Session Manager | 종료 정보 수집 | 프로세스 exit_code, signal, stderr, 마지막 stream-json 이벤트, session_id를 수집하여 구조화 |
| 2 | Error Classifier | 종료 분류 | RESUMABLE / NON_RESUMABLE 판별. rate_limit은 항상 RESUMABLE |
| 3 | State Manager | Friction 기록 | `friction.json`에 크래시 정보 기록. type="error" |
| 4a | Session Manager | 대기 | 에러 유형에 따른 대기 시간 적용 |
| 4b | Session Manager | 세션 재개 | `--resume {session_id}`로 이전 세션 재개 시도. 이전 컨텍스트 유지 |
| 4c | Session Manager | 재개 결과 | 성공하면 정상 모니터링. 실패하면 NON_RESUMABLE 경로로 전환 |
| 5a | State Manager | State 무결성 검증 | 모든 state/*.json 파일을 JSON 파싱 시도. 실패 시 Git checkpoint 복구 |
| 5b | State Manager | 세션 이력 기록 | `sessions.json`에 크래시 세션 기록. outcome="crashed" |
| 5c | Session Manager | Fresh session | 새 `claude -p` 호출. 크래시 정보를 프롬프트에 포함하여 이전 작업 컨텍스트 전달 |
| 6 | Supervisor | 심각도 판단 | 최근 N개 세션에서 같은 미션의 크래시 횟수 확인. 반복 크래시면 미션 실패 처리 |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `state/friction.json` | 크래시 기록 추가 |
| `state/sessions.json` | 크래시 세션 기록 (outcome: "crashed") |
| `state/missions.json` | 반복 크래시 시 미션 status: "failed" |
| `run/current_session.json` | 새 세션 정보로 갱신 |
| `state/*` (손상 시) | Git checkpoint에서 복구 |

### 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| resume 실패 | NON_RESUMABLE 경로로 전환. fresh session 시작 |
| state 파일 복구 실패 | 기본값으로 재생성 + 기존 Git 이력에서 가능한 데이터 복원 |
| 연속 크래시 (3회 이상) | cooldown (5분) 후 재시도. Slack 긴급 알림 |

### 종료 조건
세션이 성공적으로 재개되거나 fresh session이 시작되면 Normal Operation Cycle (Flow #2)로 복귀.

---

## 9. Watchdog Recovery Flow (Watchdog 복구 흐름)

### 트리거 조건
Watchdog 프로세스가 주기적 heartbeat 확인에서 Supervisor 이상을 감지할 때. Watchdog는 별도 LaunchAgent (`com.acc.watchdog.plist`)로 실행된다.

### 시퀀스 다이어그램

```
launchd             Watchdog                            Supervisor
  |                    |                                    |
  | [LaunchAgent로     |                                    |
  |  Watchdog 시작]    |                                    |
  |------------------->|                                    |
  |                    |                                    |
  |                    | [HEARTBEAT CHECK LOOP: 30초 간격]  |
  |                    |                                    |
  |                    | [1] heartbeat 파일 읽기            |
  |                    |     run/supervisor.heartbeat       |
  |                    |                                    |
  |                    | ┌──────────────────────────────────────────────────┐
  |                    | │ 판별 기준:                                       │
  |                    | │                                                  │
  |                    | │ HEALTHY:                                         │
  |                    | │   heartbeat 타임스탬프 < 60초 전                 │
  |                    | │   → 아무 동작 없음, 다음 체크까지 대기           │
  |                    | │                                                  │
  |                    | │ STALE:                                           │
  |                    | │   heartbeat 타임스탬프 >= 60초 전                │
  |                    | │   → 복구 시도                                    │
  |                    | │                                                  │
  |                    | │ MISSING:                                         │
  |                    | │   heartbeat 파일 자체가 없음                     │
  |                    | │   → clean state에서 재시작                       │
  |                    | └──────────────────────────────────────────────────┘
  |                    |                                    |
  |                    |  ┌─ HEALTHY ─────────────────────────────────────┐
  |                    |  │ 정상. 30초 후 재확인.                         │
  |                    |  └───────────────────────────────────────────────┘
  |                    |                                    |
  |                    |  ┌─ STALE ───────────────────────────────────────┐
  |                    |  │                                               │
  |                    |  │ [2] PID 파일 확인                             │
  |                    |  │     run/supervisor.pid                        │
  |                    |  │                                               │
  |                    |  │  ┌─ PID 파일 있고 프로세스 존재 ───────────┐  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [3a] 프로세스가 살아있지만 응답 없음    │  │
  |                    |  │  │      (zombie 또는 stuck 상태)            │  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [3b] SIGTERM 전송                       │  │
  |                    |  │  │      kill -TERM {pid}                   │  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [3c] 10초 대기                          │  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [3d] 프로세스 여전히 존재?               │  │
  |                    |  │  │      → SIGKILL 전송                     │  │
  |                    |  │  │      kill -KILL {pid}                   │  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [3e] PID 파일 삭제                      │  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [3f] launchctl kickstart                │  │
  |                    |  │  │      -k com.acc.supervisor              │  │
  |                    |  │  │      (launchd가 재시작)                 │  │
  |                    |  │  │                                          │  │
  |                    |  │  └──────────────────────────────────────────┘  │
  |                    |  │                                               │
  |                    |  │  ┌─ PID 파일 있지만 프로세스 없음 ─────────┐  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [4a] Stale PID 파일 (프로세스 이미 사망)│  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [4b] PID 파일 삭제                      │  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [4c] launchctl kickstart                │  │
  |                    |  │  │      -k com.acc.supervisor              │  │
  |                    |  │  │                                          │  │
  |                    |  │  └──────────────────────────────────────────┘  │
  |                    |  │                                               │
  |                    |  │  ┌─ PID 파일 없음 ─────────────────────────┐  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [5a] Supervisor가 시작도 안 된 상태     │  │
  |                    |  │  │                                          │  │
  |                    |  │  │ [5b] launchctl kickstart                │  │
  |                    |  │  │      -k com.acc.supervisor              │  │
  |                    |  │  │                                          │  │
  |                    |  │  └──────────────────────────────────────────┘  │
  |                    |  │                                               │
  |                    |  └───────────────────────────────────────────────┘
  |                    |                                    |
  |                    |  ┌─ MISSING ─────────────────────────────────────┐
  |                    |  │                                               │
  |                    |  │ [6a] heartbeat 파일 자체가 없음               │
  |                    |  │      Supervisor가 한 번도 시작 안 했거나     │
  |                    |  │      심각한 오류로 파일 삭제됨               │
  |                    |  │                                               │
  |                    |  │ [6b] PID 파일도 확인                         │
  |                    |  │      있으면 프로세스 kill 후 삭제            │
  |                    |  │                                               │
  |                    |  │ [6c] launchctl kickstart                     │
  |                    |  │      -k com.acc.supervisor                   │
  |                    |  │                                               │
  |                    |  └───────────────────────────────────────────────┘
  |                    |                                    |
  |                    | [7] 복구 결과 로그 기록            |
  |                    |     logs/watchdog.log              |
  |                    |                                    |
  |                    | [30초 대기 후 LOOP 복귀]           |
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | Watchdog | Heartbeat 확인 | `run/supervisor.heartbeat` 파일의 타임스탬프를 현재 시각과 비교. 60초 이상 차이면 STALE |
| 2 | Watchdog | PID 확인 | `run/supervisor.pid` 파일 읽기 → `os.kill(pid, 0)`으로 프로세스 존재 확인 |
| 3a-3f | Watchdog | Stuck 프로세스 처리 | SIGTERM → 10초 대기 → SIGKILL (필요시) → PID 파일 삭제 → launchctl kickstart |
| 4a-4c | Watchdog | Stale PID 처리 | PID 파일만 남은 경우 (프로세스 이미 사망). PID 파일 삭제 → launchctl kickstart |
| 5a-5b | Watchdog | PID 없음 처리 | Supervisor가 시작도 안 된 상태. launchctl kickstart로 시작 |
| 6a-6c | Watchdog | 파일 누락 처리 | heartbeat 파일 자체 부재. 모든 런타임 파일 정리 후 launchctl kickstart |
| 7 | Watchdog | 로그 기록 | `logs/watchdog.log`에 복구 동작 기록 |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `run/supervisor.pid` | 삭제 (stale 시) → Supervisor 재시작 후 재생성 |
| `logs/watchdog.log` | 복구 동작 기록 추가 |

### 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| launchctl kickstart 실패 | 10초 후 재시도. 3회 실패 시 watchdog.log에 CRITICAL 기록 |
| kill 권한 없음 | watchdog.log에 기록. 다음 체크에서 재시도 |
| heartbeat 파일 읽기 실패 (권한 문제) | MISSING으로 처리 |
| Watchdog 자체 크래시 | launchd KeepAlive가 Watchdog 재시작 |

### 종료 조건
Watchdog는 종료되지 않는다. launchd가 관리하며 영구 실행. 각 복구 시도 후 30초 대기하고 다음 heartbeat 체크.

---

## 10. TUI Interaction Flow (TUI 상호작용 흐름)

### 트리거 조건
Owner가 `acc tui` 명령을 실행할 때.

### 시퀀스 다이어그램

```
Owner               TUI (Textual)        State Files           State Manager      Supervisor
  |                    |                     |                      |                  |
  | acc tui            |                     |                      |                  |
  |                    |                     |                      |                  |
  |------------------->|                     |                      |                  |
  |                    | [1] 앱 시작         |                      |                  |
  |                    |     Textual app     |                      |                  |
  |                    |     mount            |                      |                  |
  |                    |                     |                      |                  |
  |                    | [2] 상태 파일 읽기  |                      |                  |
  |                    |-------------------->|                      |                  |
  |                    |  purpose.json       |                      |                  |
  |                    |  missions.json      |                      |                  |
  |                    |  sessions.json      |                      |                  |
  |                    |  friction.json      |                      |                  |
  |                    |  requests.json      |                      |                  |
  |                    |  config.toml        |                      |                  |
  |                    |  run/current_       |                      |                  |
  |                    |    session.json     |                      |                  |
  |                    |<--------------------|                      |                  |
  |                    |                     |                      |                  |
  |  ┌──────────────────────────────────────────────────────────────────────────────┐
  |  │ [3] 대시보드 렌더링                                                          │
  |  │                                                                               │
  |  │  ┌─────────────────────────────────────────────────────────────────────────┐  │
  |  │  │  claude-automata Dashboard                          [Q]uit      │  │
  |  │  │                                                                         │  │
  |  │  │  ┌─ Status ──────────────┐  ┌─ Current Mission ──────────────────────┐ │  │
  |  │  │  │ State: RUNNING        │  │ M-023: API 인증 모듈 구현             │ │  │
  |  │  │  │ Session: abc123       │  │ Priority: 1                            │ │  │
  |  │  │  │ Uptime: 3d 14h 22m   │  │ Status: in_progress                   │ │  │
  |  │  │  │ Missions: 23/45      │  │ Started: 2026-03-25T10:30:00Z         │ │  │
  |  │  │  └──────────────────────┘  └────────────────────────────────────────┘ │  │
  |  │  │                                                                         │  │
  |  │  │  ┌─ Mission Queue ─────────────────────────────────────────────────┐   │  │
  |  │  │  │ 1. [P0] 자기개선: JSON 파싱 에러 해결          pending        │   │  │
  |  │  │  │ 2. [P1] 사용자 인증 테스트 작성                 pending        │   │  │
  |  │  │  │ 3. [P2] README 문서화                           blocked (R-01)│   │  │
  |  │  │  └─────────────────────────────────────────────────────────────────┘   │  │
  |  │  │                                                                         │  │
  |  │  │  ┌─ Recent Logs ───────────────────────────────────────────────────┐   │  │
  |  │  │  │ [10:31:02] tool_use: Edit /src/auth.py                         │   │  │
  |  │  │  │ [10:31:05] tool_result: success                                │   │  │
  |  │  │  │ [10:31:08] tool_use: Bash(uv run pytest)                       │   │  │
  |  │  │  └─────────────────────────────────────────────────────────────────┘   │  │
  |  │  │                                                                         │  │
  |  │  │  ┌─ Pending Requests ──────────────────────────────────────────────┐   │  │
  |  │  │  │ R-001: GitHub API 토큰 필요 [pending]            [Reply]       │   │  │
  |  │  │  └─────────────────────────────────────────────────────────────────┘   │  │
  |  │  │                                                                         │  │
  |  │  │  [I]nject Mission    [R]eply to Request    [L]ogs    [H]elp            │  │
  |  │  └─────────────────────────────────────────────────────────────────────────┘  │
  |  └──────────────────────────────────────────────────────────────────────────────┘
  |                    |                     |                      |                  |
  |                    | [4] 주기적 갱신     |                      |                  |
  |                    |     (1초 간격 파일  |                      |                  |
  |                    |      재읽기)        |                      |                  |
  |                    |                     |                      |                  |
  |  ───────── Owner 상호작용: Mission 주입 ─────────────────────────────────────────
  |                    |                     |                      |                  |
  | [I] 키 입력        |                     |                      |                  |
  |                    | [5] 미션 입력       |                      |                  |
  |                    |     다이얼로그 표시 |                      |                  |
  |                    |                     |                      |                  |
  | 미션 제목 +        |                     |                      |                  |
  | 설명 입력          |                     |                      |                  |
  |                    |                     |                      |                  |
  |                    | [6] missions.json   |                      |                  |
  |                    |     에 직접 쓰기    |                      |                  |
  |                    |-------------------->|                      |                  |
  |                    |                     | (원자적 쓰기)        |                  |
  |                    |                     |                      |                  |
  |                    |                     |                      | [7] 다음 루프에서|
  |                    |                     |                      |     새 미션 감지 |
  |                    |                     |                      |     → 선택 대상  |
  |                    |                     |                      |     에 포함      |
  |                    |                     |                      |                  |
  |  ───────── Owner 상호작용: 요청 응답 ──────────────────────────────────────────
  |                    |                     |                      |                  |
  | [R] 키 입력        |                     |                      |                  |
  | (또는 요청 선택)   |                     |                      |                  |
  |                    | [8] 응답 입력       |                      |                  |
  |                    |     다이얼로그 표시 |                      |                  |
  |                    |                     |                      |                  |
  | 응답 텍스트 입력   |                     |                      |                  |
  |                    |                     |                      |                  |
  |                    | [9] requests.json   |                      |                  |
  |                    |     에 응답 쓰기    |                      |                  |
  |                    |-------------------->|                      |                  |
  |                    |                     | R-001.status =       |                  |
  |                    |                     |   "answered"         |                  |
  |                    |                     | R-001.answer =       |                  |
  |                    |                     |   Owner 입력         |                  |
  |                    |                     |                      |                  |
  |                    |                     |                      | [10] Blocker    |
  |                    |                     |                      |      해제 감지  |
  |                    |                     |                      |      (Flow #5   |
  |                    |                     |                      |       와 동일)  |
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | TUI | 앱 시작 | Textual `App` 인스턴스 생성. CSS 로드, 위젯 마운트 |
| 2 | TUI | 상태 읽기 | `state/` 디렉토리의 모든 JSON 파일 + `run/current_session.json` 읽기 |
| 3 | TUI | 대시보드 렌더링 | 상태 정보를 패널별로 렌더링 (Status, Current Mission, Queue, Logs, Requests) |
| 4 | TUI | 주기적 갱신 | Textual `set_interval(1.0)` 타이머로 상태 파일 재읽기 → UI 갱신 |
| 5 | TUI | Mission 입력 | 모달 다이얼로그 표시. title, description, priority 입력 |
| 6 | TUI → State Files | Mission 쓰기 | `missions.json`에 새 미션 추가. 원자적 쓰기 (temp + replace). source="owner" |
| 7 | Supervisor | 미션 감지 | 다음 루프에서 `missions.json` 읽을 때 새 미션이 선택 대상에 포함 |
| 8 | TUI | 응답 입력 | pending 요청 목록에서 선택 → 응답 텍스트 입력 |
| 9 | TUI → State Files | 응답 쓰기 | `requests.json`에서 해당 요청의 status, answer 갱신 |
| 10 | Supervisor | Blocker 해제 | 응답이 기록된 것을 감지하고 Blocker 해제 (Flow #5의 단계 10과 동일) |

### TUI와 Supervisor의 동시 접근

TUI와 Supervisor는 동일한 state 파일을 동시에 접근한다. 충돌 방지:

1. **모든 쓰기는 원자적**: temp 파일에 쓰고 `os.replace()`로 교체
2. **TUI는 읽기 우선**: 대부분 읽기 전용. 쓰기는 Mission 주입과 요청 응답만
3. **Supervisor가 권위**: state 파일의 최종 권위는 Supervisor. TUI 쓰기 후 Supervisor가 다음 루프에서 읽으면 반영
4. **파일 감시**: TUI는 `stat()` 기반으로 파일 변경 감지. inotify가 아니라 폴링

### 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| state 파일 파싱 실패 | TUI가 "파일 읽기 오류" 표시. 다음 갱신에서 재시도 |
| missions.json 쓰기 충돌 | 원자적 쓰기로 충돌 없음. 최악의 경우 Supervisor가 다음 읽기에서 반영 |
| Supervisor 미실행 상태에서 TUI 사용 | "Supervisor 미실행" 경고 표시. 읽기/쓰기는 가능 |

### 종료 조건
Owner가 `Q` 키를 누르거나 `Ctrl+C`로 TUI를 종료.

---

## 11. Goal Drift Prevention Flow (목표 드리프트 방지 흐름)

### 트리거 조건
완료된 미션 수가 `config.toml`의 `goal_drift_check_interval` (기본: 20)의 배수에 도달할 때.

### 시퀀스 다이어그램

```
Supervisor          State Manager       Session Manager     Claude Code
  |                      |                   |                  |
  | [1] 드리프트 체크    |                   |                  |
  |     시점 도달        |                   |                  |
  |     (매 N 미션)      |                   |                  |
  |                      |                   |                  |
  | [2] 드리프트 분석    |                   |                  |
  |     데이터 수집      |                   |                  |
  |--------------------->|                   |                  |
  |                      | purpose.json 읽기 |                  |
  |                      | missions.json 읽기|                  |
  |                      | sessions.json에서 |                  |
  |                      |   최근 N개 세션   |                  |
  |                      |   요약 추출       |                  |
  |<---------------------|                   |                  |
  |                      |                   |                  |
  | [3] 드리프트 판별    |                   |                  |
  |     세션 시작        |                   |                  |
  |------------------------------------->|                  |
  |                      |                   |----------------->|
  |                      |                   |                  |
  |                      |                   |                  | [4] 정렬도 분석
  |                      |                   |                  |
  |                      |                   |                  | purpose.json의
  |                      |                   |                  | purpose와 최근
  |                      |                   |                  | 미션 topic 비교
  |                      |                   |                  |
  |                      |                   |                  | 분석 기준:
  |                      |                   |                  | - 의미적 유사도
  |                      |                   |                  | - 미션 소스 분포
  |                      |                   |                  |   (purpose vs
  |                      |                   |                  |    friction vs
  |                      |                   |                  |    self)
  |                      |                   |                  | - 전략 정렬도
  |                      |                   |                  |
  |                      |                   |                  | [5] 드리프트 수준
  |                      |                   |                  |     판정
  |                      |                   |                  |
  |                      |                   |                  | ┌────────────────┐
  |                      |                   |                  | │ NONE:          │
  |                      |                   |                  | │  정렬 양호     │
  |                      |                   |                  | │                │
  |                      |                   |                  | │ MILD:          │
  |                      |                   |                  | │  약간의 편향   │
  |                      |                   |                  | │  감지          │
  |                      |                   |                  | │                │
  |                      |                   |                  | │ SEVERE:        │
  |                      |                   |                  | │  명확한 이탈   │
  |                      |                   |                  | │  감지          │
  |                      |                   |                  | └────────────────┘
  |                      |                   |                  |
  |<-----------------------------------------------------|
  |   판정 결과 반환     |                   |                  |
  |                      |                   |                  |
  |  ┌─ NONE ─────────────────────────────────────────────────────────────────┐
  |  │ 아무 동작 없음. 정상 루프 계속.                                        │
  |  └────────────────────────────────────────────────────────────────────────┘
  |                      |                   |                  |
  |  ┌─ MILD ─────────────────────────────────────────────────────────────────┐
  |  │                                                                         │
  |  │ [6a] 다음 세션 프롬프트에 Purpose 재강조 주입                          │
  |  │      "주의: 최근 미션이 Purpose에서 벗어나는 경향이 감지되었습니다.    │
  |  │       Purpose를 다시 확인하고 정렬된 미션을 우선하세요."               │
  |  │                                                                         │
  |  │ [6b] friction.json에 기록                                               │
  |  │      type: "drift", severity: "mild"                                     │
  |  │                                                                         │
  |  └────────────────────────────────────────────────────────────────────────┘
  |                      |                   |                  |
  |  ┌─ SEVERE ───────────────────────────────────────────────────────────────┐
  |  │                                                                         │
  |  │ [7a] 현재 세션 종료 허용 (Stop Hook에서 allow)                         │
  |  │                                                                         │
  |  │ [7b] Fresh session 시작 (Flow #12 변형)                                │
  |  │      Purpose re-injection 포함 프롬프트                                │
  |  │      "시스템의 Purpose는 {purpose}입니다.                              │
  |  │       최근 미션이 이 Purpose에서 크게 벗어났습니다.                    │
  |  │       Purpose에 정렬된 미션을 재생성하고 실행하세요."                  │
  |  │                                                                         │
  |  │ [7c] missions.json에서 Purpose와 무관한 pending 미션 재검토            │
  |  │      Claude Code가 각 미션의 Purpose 관련성 평가                       │
  |  │      무관한 미션은 priority 하향 또는 제거                              │
  |  │                                                                         │
  |  │ [7d] friction.json에 기록                                               │
  |  │      type: "drift", severity: "severe"                                   │
  |  │                                                                         │
  |  │ [7e] Slack으로 Owner 알림                                               │
  |  │      "목표 드리프트 감지. Purpose 재정렬 실행 중."                      │
  |  │                                                                         │
  |  └────────────────────────────────────────────────────────────────────────┘
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | Supervisor | 체크 시점 판단 | 완료 미션 수 % `goal_drift_check_interval` == 0 확인 |
| 2 | State Manager | 데이터 수집 | purpose.json + 최근 미션 이력 + 세션 요약 수집 |
| 3 | Session Manager | 분석 세션 시작 | 경량 세션으로 Claude Code에 드리프트 분석 요청 |
| 4 | Claude Code | 정렬도 분석 | Purpose와 최근 미션 주제의 의미적 유사도 평가. 미션 소스 분포 분석 |
| 5 | Claude Code | 수준 판정 | NONE / MILD / SEVERE 중 하나 반환 |
| 6a | Supervisor | MILD 처리 | 다음 세션 프롬프트에 Purpose 재강조 문구 주입 |
| 7a-7e | Supervisor | SEVERE 처리 | Fresh session + Purpose re-injection + 미션 큐 재검토 + Slack 알림 |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `state/friction.json` | 드리프트 기록 추가 (type: "drift", severity) |
| `state/missions.json` | SEVERE 시 미션 priority 조정 또는 제거 |
| `run/current_session.json` | SEVERE 시 새 세션 정보로 갱신 |

### 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| 드리프트 분석 세션 크래시 | 스킵하고 다음 interval에서 재시도 |
| Claude Code가 판정 불가 | NONE으로 처리 (안전 방향) |
| SEVERE 처리 중 에러 | friction 기록 후 정상 루프 계속. 다음 체크에서 재감지 |

### 종료 조건
드리프트 수준 판정 및 해당 조치가 완료되면 Normal Operation Cycle로 복귀.

---

## 12. Context Refresh Flow (컨텍스트 갱신 흐름)

### 트리거 조건
현재 세션의 compaction 횟수가 `config.toml`의 `context_refresh_after_compactions` (기본: 5)에 도달하거나, Stop Hook이 컨텍스트 갱신 필요를 판단할 때.

### 시퀀스 다이어그램

```
Stop Hook           Supervisor        State Manager      Session Manager     Claude Code (Old)   Claude Code (New)
  |                    |                  |                   |                    |                    |
  | [1] compaction     |                  |                   |                    |                    |
  |     횟수 >=        |                  |                   |                    |                    |
  |     threshold      |                  |                   |                    |                    |
  |                    |                  |                   |                    |                    |
  | [2] ALLOW 반환     |                  |                   |                    |                    |
  |     reason:        |                  |                   |                    |                    |
  |     "컨텍스트 갱신 |                  |                   |                    |                    |
  |      필요"         |                  |                   |                    |                    |
  |                    |                  |                   |                    |                    |
  |                    |                  |                   |                    | [3] Claude Code   |
  |                    |                  |                   |                    | 현재 작업 완료    |
  |                    |                  |                   |                    | (allow 수신)      |
  |                    |                  |                   |                    |                    |
  |                    |                  |                   |                    | [4] 현재 미션     |
  |                    |                  |                   |                    | 진행 상황 기록    |
  |                    |                  |                   |                    | missions.json     |
  |                    |                  |                   |                    | 갱신              |
  |                    |                  |                   |                    |                    |
  |                    |                  |                   |                    | [5] 세션 종료     |
  |                    |                  |                   |                    | (정상 exit)       |
  |                    |                  |                   |                    |                    |
  |                    | [6] 세션 종료    |                   |                    |                    |
  |                    |     감지         |                   |                    |                    |
  |                    |                  |                   |                    |                    |
  |                    | [7] 결과 기록    |                   |                    |                    |
  |                    |----------------->|                   |                    |                    |
  |                    |                  | sessions.json     |                    |                    |
  |                    |                  | 갱신              |                    |                    |
  |                    |                  | (reason:          |                    |                    |
  |                    |                  |  context_refresh) |                    |                    |
  |                    |                  |                   |                    |                    |
  |                    | [8] Git 체크포인트|                  |                    |                    |
  |                    |----------------->|                   |                    |                    |
  |                    |                  | tag: checkpoint-  |                    |                    |
  |                    |                  |   {timestamp}     |                    |                    |
  |                    |                  |                   |                    |                    |
  |                    | [9] 새 세션      |                   |                    |                    |
  |                    |     프롬프트 구성 |                  |                    |                    |
  |                    |----------------->|                   |                    |                    |
  |                    |                  | create_session_   |                    |                    |
  |                    |                  | context() 호출    |                    |                    |
  |                    |                  |                   |                    |                    |
  |                    |                  | 포함 내용:        |                    |                    |
  |                    |                  | - 이전 세션 요약  |                    |                    |
  |                    |                  | - 현재 미션 상태  |                    |                    |
  |                    |                  |   (진행 중이면    |                    |                    |
  |                    |                  |    중단 지점 포함)|                    |                    |
  |                    |                  | - Friction 요약   |                    |                    |
  |                    |                  | - 대기 중 요청    |                    |                    |
  |                    |                  |                   |                    |                    |
  |                    |<-----------------|                   |                    |                    |
  |                    |   prompt 반환    |                   |                    |                    |
  |                    |                  |                   |                    |                    |
  |                    | [10] 새 세션 시작|                   |                    |                    |
  |                    |------------------------------>|                    |                    |
  |                    |                  |                   |                    |                    |
  |                    |                  |                   | claude -p          |                    |
  |                    |                  |                   | "<fresh_prompt>"   |                    |
  |                    |                  |                   | --model opus       |                    |
  |                    |                  |                   | --effort max       |                    |
  |                    |                  |                   | --output-format    |                    |
  |                    |                  |                   |   stream-json      |                    |
  |                    |                  |                   | --dangerously-     |                    |
  |                    |                  |                   |   skip-perms       |                    |
  |                    |                  |                   |----------------------------------->|
  |                    |                  |                   |                    |                    |
  |                    |                  |                   |                    |              [11] SessionStart
  |                    |                  |                   |                    |                   Hook 발동
  |                    |                  |                   |                    |                    |
  |                    |                  |                   |                    |              on_session_start.py
  |                    |                  |                   |                    |                    |
  |                    |                  |                   |                    |              additionalContext
  |                    |                  |                   |                    |              주입:
  |                    |                  |                   |                    |              - state 요약
  |                    |                  |                   |                    |              - 이전 세션 이력
  |                    |                  |                   |                    |                    |
  |                    |                  |                   |                    |              [12] CLAUDE.md
  |                    |                  |                   |                    |                   재로드
  |                    |                  |                   |                    |              (디스크에서 최신
  |                    |                  |                   |                    |               버전 읽기)
  |                    |                  |                   |                    |                    |
  |                    |                  |                   |                    |              [13] state 파일
  |                    |                  |                   |                    |                   읽기
  |                    |                  |                   |                    |              missions.json
  |                    |                  |                   |                    |              friction.json
  |                    |                  |                   |                    |              requests.json
  |                    |                  |                   |                    |              등
  |                    |                  |                   |                    |                    |
  |                    |                  |                   |                    |              [14] 미션 실행
  |                    |                  |                   |                    |                   시작
  |                    |                  |                   |                    |              (깨끗한 컨텍스트
  |                    |                  |                   |                    |               + 최신 state)
  |                    |                  |                   |                    |                    |
  |                    | [정상 모니터링으로 복귀 (Flow #2)]  |                    |                    |
```

### 단계별 상세

| 단계 | 액터 | 동작 | 상세 |
|------|------|------|------|
| 1 | Stop Hook | Compaction 횟수 확인 | `run/current_session.json`의 `compaction_count`를 `config.toml`의 `context_refresh_after_compactions`와 비교 |
| 2 | Stop Hook | ALLOW 반환 | `decision: "allow"`, `reason: "context_refresh"` 반환 |
| 3-4 | Claude Code (Old) | 현재 작업 정리 | allow 수신 후 현재 진행 상황을 state 파일에 기록. 미완료 미션은 진행 상태 보존 |
| 5 | Claude Code (Old) | 세션 종료 | 정상 exit. 프로세스 종료 |
| 6 | Supervisor | 종료 감지 | stream-json의 `result` 이벤트 또는 프로세스 exit 감지 |
| 7 | State Manager | 결과 기록 | `sessions.json`에 세션 기록. `end_reason: "context_refresh"` |
| 8 | State Manager | Git 체크포인트 | `git add state/ && git tag checkpoint-{ts}` |
| 9 | State Manager | 프롬프트 구성 | `create_session_context()`로 최신 state 기반 프롬프트 생성. 이전 세션 중단 지점 정보 포함 |
| 10 | Session Manager | 새 세션 시작 | 새 `claude -p` 프로세스 시작. 이전 session_id와 무관한 새 세션 |
| 11 | SessionStart Hook | 컨텍스트 주입 | `on_session_start.py`가 `additionalContext`로 state 요약 주입 |
| 12 | Claude Code (New) | CLAUDE.md 재로드 | 새 세션이므로 디스크에서 CLAUDE.md 최신 버전 읽기. 자기개선으로 수정된 내용 반영 |
| 13 | Claude Code (New) | State 파일 읽기 | `state/` 디렉토리의 JSON 파일 읽기. 최신 상태 확인 |
| 14 | Claude Code (New) | 미션 실행 | 깨끗한 컨텍스트에서 미션 실행 시작. compaction에 의한 정보 손실 없음 |

### 상태 변경

| 파일 | 변경 내용 |
|------|-----------|
| `state/sessions.json` | 이전 세션 기록 (end_reason: "context_refresh") + 새 세션 시작 기록 |
| `run/current_session.json` | 새 session_id, compaction_count=0 으로 리셋 |
| Git tag | 새 checkpoint 생성 |

### 에러 처리

| 에러 상황 | 처리 |
|-----------|------|
| 이전 세션이 정리 없이 종료 | Supervisor가 state 파일에서 현재 미션 상태 확인. in_progress 미션은 그대로 유지 |
| 새 세션 시작 실패 | Flow #4 (Error Recovery)로 위임 |
| SessionStart Hook 실패 | Claude Code가 CLAUDE.md + state 파일에서 직접 컨텍스트 확인. 프롬프트에 충분한 정보 포함 |

### 종료 조건
새 Claude Code 세션이 성공적으로 시작되고 미션 실행이 시작되면 Normal Operation Cycle (Flow #2)로 복귀.

---

## 흐름 간 상호 참조

아래 표는 각 흐름이 다른 흐름을 호출하거나 참조하는 관계를 보여준다.

| 흐름 | 호출하는 흐름 | 호출되는 흐름 |
|------|-------------|-------------|
| #1 Bootstrap | #2 Normal Operation | - |
| #2 Normal Operation | #3, #4, #6, #7, #11, #12 | #1 |
| #3 Stop Hook | - | #2 |
| #4 Error Recovery | #8, #12 | #2 |
| #5 Owner Interaction | - | #2, #3 |
| #6 Self-Improvement | - | #2 |
| #7 Proactive Improvement | - | #2 |
| #8 Session Crash Recovery | #4 | #4 |
| #9 Watchdog Recovery | - | - (독립) |
| #10 TUI Interaction | - | - (독립, state 파일 공유) |
| #11 Goal Drift Prevention | #12 | #2 |
| #12 Context Refresh | - | #2, #3 |

---

## 전체 시스템 상태 머신

시스템의 거시적 상태 전이:

```
                    ┌─────────────┐
                    │  UNCONFIGURED│
                    └──────┬──────┘
                           │ acc configure
                           ▼
                    ┌─────────────┐
                    │  CONFIGURED  │
                    └──────┬──────┘
                           │ acc start
                           ▼
                    ┌─────────────┐
                    │ INITIALIZING │ ← Flow #1
                    └──────┬──────┘
                           │ Purpose 구성 완료
                           ▼
              ┌────────────────────────┐
         ┌───>│       RUNNING          │ ← Flow #2 (메인 루프)
         │    │  ┌─────────────────┐   │
         │    │  │ 미션 실행 중    │   │
         │    │  │ Stop Hook 활성  │   │
         │    │  │ Heartbeat 갱신  │   │
         │    │  └─────────────────┘   │
         │    └───┬──┬──┬──┬──┬──┬────┘
         │        │  │  │  │  │  │
         │        │  │  │  │  │  └── Flow #3 (Stop Hook)
         │        │  │  │  │  └───── Flow #5 (Owner Interaction)
         │        │  │  │  └──────── Flow #6 (Self-Improvement)
         │        │  │  └─────────── Flow #7 (Proactive Improvement)
         │        │  └────────────── Flow #11 (Drift Prevention)
         │        └───────────────── Flow #12 (Context Refresh)
         │                │
         │                │ 에러 발생
         │                ▼
         │    ┌─────────────────────┐
         │    │     RECOVERING      │ ← Flow #4, #8
         │    │  분류 → 복구 실행   │
         │    └──────────┬──────────┘
         │               │ 복구 성공
         └───────────────┘
                         │ 복구 불가 (AUTH)
                         ▼
              ┌─────────────────────┐
              │  WAITING_FOR_OWNER  │
              │  (30분 재시도 루프)  │
              └──────────┬──────────┘
                         │ 인증 복구
                         │
                         └──> RUNNING
```

이 상태 머신에서 시스템은 **RUNNING**과 **RECOVERING** 사이를 오가며 영속적으로 동작한다. 유일하게 장기 대기 상태에 빠지는 경우는 인증 실패(AUTH)뿐이며, 이 경우에도 주기적 재시도를 계속한다.
