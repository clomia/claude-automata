# Anchor — 아키텍처

Anchor는 **parallax 메커니즘** — 격리된 advisor가 매 라운드 메인 에이전트가
고려하지 못한 영역을 surface해 결과 신뢰도를 극한까지 끌어올리는 자율 루프 — 를
Claude Code의 **nested subagent** 위에서 구현한다. parallax가 Stop 훅에서
`claude -p`를 외부 스폰하느라 구독 요금제에서 계정 차단 위험을 안았던 자리를,
정식 `Agent` 툴 호출로 대체해 그 위협을 **본질적으로 제거**한다.

---

## 용어

- **parallax** — 훅·narrator·advisor를 거쳐 미고려 영역을 주입하는 *메커니즘*.
- **anchor** — 그 메커니즘에 귀속된 메인 *에이전트*(depth 1). 세션 `main`과 구별된다.

이름이 곧 메커니즘이다: parallax 루프와 mission 재정박이 메인 에이전트를 미션에
**붙들어 맨다(anchor)**. 자기 확신으로 표류(drift)하지도, compaction으로 미션을
잃지도 않는다.

---

## 문제 — parallax가 구식이 된 이유

parallax는 Stop 훅 안에서 advisor·narrator를 `claude -p` 서브프로세스로 스폰한다.
이는 `--no-session-persistence`로 **별도의 임시 세션**을 생성하는 자동화 패턴이고,
Claude Pro/Max 구독 약관상 계정 정지 위험을 부른다(실제 차단 이력 존재). 그래서
parallax는 Anthropic API 요금제 전용으로 묶였고, 구독 사용자는 손대지 못했다.

parallax 개발 당시에는 nested subagent가 불가능해 이 방법뿐이었다. 그러나
`Agent` 툴 subagent는 **모든 요금제에서 지원되는 정식 기능**이고(메인 세션과 동일
quota 공유), 서브에이전트는 다시 서브에이전트를 spawn할 수 있다(v2.1.172+, depth 5
cap). Anchor는 같은 메커니즘을 이 정식 경로 위에서 재구현해 요금제 위협을 없앤다.

| | parallax | anchor |
|---|---|---|
| advisor/narrator 실행 | 훅이 `claude -p` 스폰 | anchor가 **Agent 툴** 호출 |
| 격리 | 별도 프로세스 | 별도 subagent (동일 격리) |
| 요금제 | API 전용 · **구독 차단 위험** | **구독 정식** (nested agent) |
| 트리거 | `parallaxthink` 키워드 | `main`의 미션 위임 (에이전트 기반) |

---

## Agent Tree

`main`은 사용자와 대화하는 세션(depth 0)이고, parallax 루프는 그 아래 봉인된
서브에이전트 tier에서 돈다. 각 tier는 아래로 위임하고 위로는 요약만 반환하므로,
방대한 컨텍스트가 상위로 갈수록 압축된다.

```
main       depth 0  session       full tools              유저와 대화; 미션을 정의
   |  /anchor:init  ->  writes {session}_mission.md, then Agent(anchor, background)
   v
anchor     depth 1  Agent +full   수행자(parallax main)   미션을 직접 실행
   |  Agent(advisor)   <- "invoke advisor" injected by SubagentStop hook
   v
advisor    depth 2  Agent Read    영역 surface            미고려 영역 분석; region 반환
   |  Agent(narrator)  Grep Glob Web*
   v
narrator   depth 3  Read (leaf)   서사 작성               action 기록을 markdown으로
```

| Tier | 도구 (allowlist) | 모델 | effort | parallax 대응 |
|---|---|---|---|---|
| **anchor** | 전체 (미설정 — 모든 도구 상속) | `opus[1m]` | inherit | 메인 에이전트 |
| **advisor** | 전체 − `Write` (`disallowedTools`) | `opus[1m]` | max | Advisor (`claude -p`, max) |
| **narrator** | `Read` | `sonnet` | low | Narrator (`claude -p`, low) |

- **advisor는 `Write`만 막혀 있다(`disallowedTools: Write`)** — 새 파일을 만들지 않는다.
  조사 도구로 영역을 사실에 근거 짓고(parallax의 CRITIC 근거: advisor가 외부 도구로
  확인한 뒤 surface), 결과는 region 한 문단으로 **반환**한다 — 그것을 state에 기록하는
  것은 hook의 몫이다(아래 상태 권위).
- **narrator는 `Read`뿐인 leaf** — `Agent`가 없어 트리가 그 아래로 자라지 않는다.
  단순 변환이라 `sonnet`/`low`로 충분(parallax 그대로).
- depth 3에서 트리를 닫아 depth-5 cap에 2단계 여유를 남긴다.

---

## 핵심 루프

```
anchor round N work ── stops
   |
   |  <-- SubagentStop hook (matcher: anchor:anchor)
   |        record last advisor verdict: termination -> done, else append region
   |        done set, or round >= ROUND_LIMIT  ->  exit 0 (allow stop)
   |        else:  parse round actions (advisor calls stripped) -> {session}_action.json
   |               assemble {session}_analysis.md (mission + region-history XML)
   |               round++,  exit 2 + stderr: "invoke advisor (analysis, action)"
   v
anchor ── Agent(advisor) ─────────────> advisor (depth 2)
   |                                       ├ read analysis input (hook-assembled XML: mission + region)
   |                                       ├ Agent(narrator) -> action narrative
   |                                       ├ run instruction.ko workflow
   |                                       └ return region / termination token
   |  <─────────── region (one paragraph) ─┘
   v
anchor ── work on the surfaced region (round N+1) ── stops ── (loop)
```

종료는 두 신호로 결정된다(parallax와 동일): advisor가 전용 종료 토큰을 내면
`done` 플래그가 서고 다음 훅이 정지를 허용하며, 그 전이라도 `ROUND_LIMIT`(30)이
무한 루프를 막는다.

---

## 컨텍스트 경제 — nested가 `claude -p`보다 우월한 지점

anchor의 컨텍스트에 더해지는 것은 **① 짧은 stderr 트리거 + ② advisor가 반환한
region 한 문단**뿐이다. narrator 호출, region-history 누적 읽기, 5-section 분석은
모두 **advisor(depth 2)의 컨텍스트에서** 소비되어 anchor에 닿지 않는다. region을
"한 문단으로만 출력"하는 parallax instruction이 이 경계를 지킨다. 즉 "nested로
방대한 컨텍스트를 소화한다"는 원리가 parallax의 격리 advisor와 정확히 같은
지점에서 작동한다 — advisor가 anchor의 사각을 보되, 그 탐색 비용을 anchor에게
전가하지 않는다.

---

## 상태와 미션 보존

모든 상태는 사용자 레포 바깥, `CLAUDE_PLUGIN_DATA`에 둔다(레포 비오염, parallax
일관). 한 세션에 하나의 미션을 가정해 `session_id`로 키잉한다(agentId 불요).

| 파일 | 작성자 | 내용 |
|---|---|---|
| `{session}_mission.md` | `main` | 미션 정의 (트랜스크립트 독립 외부 보존) |
| `{session}_anchor.json` | hook | `round` · `regions` · `done` (모두 hook이 기록) |
| `{session}_action.json` | hook | 이번 라운드 action 기록 (narrator가 읽음) |
| `{session}_analysis.md` | hook | advisor 입력: original-mission + region-history XML 봉투 |
| `{session}_anchor.log` | hook | 라운드별 분석 로그 (`/anchor-log`로 조회) |
| `{session}_advisor_token` | hook | advisor 1회 호출 인가 토큰 (SubagentStop set · PreToolUse 소비) |

**상태는 hook이 단독 소유한다.** advisor는 분석만 하고 region 한 문단(또는 종료
토큰)을 **반환**할 뿐 state를 쓰지 않는다. hook이 다음 라운드 시작에 직전 advisor
반환값을 트랜스크립트에서 추출(`extract_advisor_output`)해 `regions`에 append하거나,
종료 토큰이면 `done`을 세운다. `round`도 hook이 증가시키는 안전망이다(anchor가
advisor를 무시해도 ROUND_LIMIT이 보장된다). 단일 작성자라 race가 없고, advisor
프롬프트는 운영 부담 없이 순수 분석으로 남는다 — parallax advisor도 텍스트만 반환하고
hook이 region을 기록했으므로, 이 방향이 parallax에 더 충실하다.

**미션 정박은 이중이다.**

1. **외부 보존** — `main`이 미션을 `{session}_mission.md`에 기록한다. 트랜스크립트와
   독립이므로 anchor 내부가 어떻게 compaction되든 원본은 보존된다(parallax 메커니즘 1).
2. **self-anchoring** — anchor·advisor의 **시스템 프롬프트**가 "맥락이 불명확하거나
   compaction되면 mission 파일을 다시 읽으라"고 지시한다. 시스템 프롬프트는
   compaction 후에도 그대로 reload되므로 훅보다 강한 보장이다(부트스트랩의 통찰).

훅 기반 mission 재주입(parallax 메커니즘 2)에 **의존하지 않는** 이유: subagent
내부 compaction에서 `PostCompact` 훅이 발화하는지 미확정이기 때문(아래 리스크 §2).
self-anchoring은 compaction 감지 자체가 불필요해 더 강건하다.

---

## Hooks

| Hook | Matcher | 시점 | 동작 |
|---|---|---|---|
| **PreToolUse** | `Agent` | anchor가 Agent 호출 | `anchor:advisor` 호출이면 1회용 토큰 검사 → 허용(소비) 또는 `exit 2` deny(자발 호출 차단) |
| **SubagentStop** | `anchor:anchor` | anchor가 종료 시도 | 종료 판정 → `exit 0`(허용) 또는 `exit 2`+stderr(advisor 호출 지시) |
| **SessionStart** | `startup\|clear` | 세션 시작 | 신규 릴리스 알림 (parallax updater 이식) |

플러그인 에이전트는 `anchor:<agent>`로 scoped 등록되므로, Agent 호출의
subagent_type도 이 matcher도 그 scoped 이름을 쓴다(`anchor`만으로는 매칭되지
않는다). matcher의 `:`는 정규식으로 평가되어 `anchor:anchor`만 잡고
`anchor:advisor`·`anchor:narrator`는 제외하므로, advisor·narrator는 정상 종료해
결과를 호출자에게 반환한다 — parallax의 `PARALLAX_INSIDE_RECURSION` 재귀 가드가
구조적으로 불필요해진다. 훅은 `bin/anchor-hook` 셸 래퍼를 거쳐 `uv`를
호출한다 — 래퍼가 uv 가용성을 먼저 확인하므로(parallax에서 상속), uv 미설치 시
graceful degrade와 SessionStart 안내를 한 지점에서 일원화한다.

**Graceful degradation.** `uv`가 없으면 훅 spawn은 무해하게 실패한다. anchor는
parallax를 모르므로(루프는 전적으로 훅이 구동) advisor 없이 미션만 수행하고
종료한다 — 트리는 돌지 않지만 세션은 깨지지 않으며, SessionStart가 uv 설치를
안내한다.

---

## 핵심 설계 결정

1. **훅은 코드라 툴을 호출할 수 없다 → 훅은 트리거, 실행은 Agent 툴.** Claude Code
   훅은 stdout/stderr/exit code로만 통신하며 tool call을 발화하지 못한다. 그래서
   `claude -p`를 Agent 툴로 *직접 치환*하는 것은 불가능하다. 대신 SubagentStop이
   `exit 2`+stderr로 anchor에게 advisor 호출을 **지시**하고, anchor(LLM)가 Agent
   툴로 실행한다. 이 한 단계가 parallax→anchor 전환의 본질이다. anchor의 시스템
   프롬프트는 parallax·advisor를 **언급하지 않는다** — 자발적으로 부르면 경로 대신
   자기 의견을 advisor에 전달하거나 narrator를 건너뛰어 정해진 사용법을 무시하기
   때문이다. advisor의 존재는 stderr 지시가 처음 알린다.
2. **상태는 hook이 단독 소유.** advisor는 region/종료토큰을 반환만 하고, hook이
   트랜스크립트에서 추출해 round·regions·done을 모두 기록한다. 단일 작성자라 동시성
   문제가 없고, advisor 프롬프트가 순수 분석으로 남는다(parallax도 hook이 region 기록).
3. **미션 정박 이중화 + self-anchoring 우선.** 외부 파일 보존 + 시스템 프롬프트
   재독. PostCompact 불확실성을 우회.
4. **session 기반 단일 미션.** 한 세션 한 미션으로 agentId 키잉을 제거(단순성).
   다중 동시 미션은 비목표.
5. **프롬프트 보존과 그 한계.** parallax의 `role`·`instruction`·`conversion` 전문을
   이식한다. 다만 nested 구조상 두 가지가 어긋난다. **(a)** parallax `prompt.py`가
   조립하던 5-section 중 deterministic한 부분은 코드로 보장한다 — role·instructions는
   시스템 프롬프트, original-mission·region-history는 hook이 `prompt.py`로 XML 조립해
   `analysis.md`에 쓴다. 런타임 수집으로 남는 것은 narrator가 만드는 action-history
   하나뿐이다(narrating은 LLM이라 hook이 못 부른다) — "코드가 입력을 보장"을 최대한
   회복했다. **(b)** 정박 미션이 parallax의 *사용자 원문*에서 anchor의
   *main 작성 명세*(`mission.md`)로 바뀌었고 이는 advisor에도 전파된다 — `main`이
   미션을 정의하는 anchor 설계의 의도된 결과이나, source of truth가 사용자 발화에서
   한 단계 멀어진 트레이드다. action-history는 advisor 호출을 strip해 region-history와
   분리를 지킨다(parallax는 advisor가 외부 프로세스라 애초에 섞이지 않았다).
6. **단일 모델 `opus[1m]`(anchor·advisor).** 추론 최대화와 compaction 빈도 감소가
   같은 선택으로 수렴(부트스트랩 정신). narrator만 단순 변환이라 `sonnet`/`low`로
   parallax를 충실히 보존.
7. **플러그인 영역만, `settings.json` 불간섭.** 활성화는 `main`→`anchor` 핸드오프.
   미션 없이는 아무것도 발화하지 않는다.
8. **프로젝트 CLAUDE.md 상속 수용.** custom subagent는 사용 프로젝트의 CLAUDE.md·rules를
   상속하며 차단 옵션이 없다(Explore·Plan만 예외, frontmatter/setting 부재). 이를 수용한다
   — anchor는 코드 작업에 프로젝트 코딩 규칙이 *필요*하기 때문. advisor·narrator도 함께
   상속받아 약한 오염 여지가 있으나(narrator의 "원문 보존" vs 프로젝트 "간결" 등), 차단이
   all-or-nothing이라 anchor의 필요를 우선한다. 선택적 차단 옵션이 생기면 advisor·narrator에
   적용한다.
9. **자발 advisor 호출 차단(PreToolUse 게이팅).** anchor가 hook 지시 없이 스스로 advisor를
   부르면 결정론적 사이클이 깨진다 — 라운드 0 자발 호출의 출력은 누락되고, 한 정지에 여러
   호출이 섞이면 `extract_advisor_output`이 일부만 잡으며, hook이 조립한 `analysis.md` 대신
   anchor 자기 말이 입력으로 간다. SubagentStop이 호출을 지시할 때만 1회용 토큰을 세우고,
   PreToolUse(matcher `Agent`)가 `anchor:advisor` 호출을 토큰이 있을 때만 통과시킨다(없으면
   deny → anchor는 작업을 계속하다 멈추고 정식 지시를 받는다). deny된 호출은 트랜스크립트에
   error tool_result로 남으므로 `extract_advisor_output`은 `is_error`를 걸러 성공한 호출만
   기록한다. narrator는 read-only leaf이자 hook 사이클 밖이라 게이팅하지 않는다.
10. **메인 transcript에서 anchor transcript 해소.** SubagentStop은 hook에 정지한 subagent가
   아니라 **메인 세션 transcript**를 넘긴다(실측 확정). anchor의 작업은
   `{session}/subagents/agent-{agentId}.jsonl`에 따로 있으므로, hook은 메인 transcript에서
   **마지막** `anchor:anchor` spawn의 tool_use id를 찾아 subagent `meta.json`의 `toolUseId`와
   매칭해 그 anchor transcript를 해소한 뒤 action·advisor 출력을 읽는다(메인이 anchor를 여러
   번 spawn해도 마지막=현재를 집는다). 해소 실패 시 정지를 허용한다(graceful). 이 경로·메타
   형식은 비공개 구조라 `_hook_trace.log`의 `anchor_transcript=` 줄로 실측·검증한다.

---

## 기술 리스크 — 첫 실제 실행으로 검증

설계는 성립하나 라이브 트리 없이 유닛 테스트할 수 없는 항목들이다. 모두
**graceful degrade**하도록 설계에 반영했다.

1. **SubagentStop block cap.** 조사상 "연속 차단 8회 후 강제 종료"
   (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`). parallax는 30라운드를 도는데 depth-1
   subagent의 cap이 같은지, 라운드 사이 실제 작업이 카운터를 리셋하는지 미확정.
   **현재 우회는 설정하지 않았다** — 환경변수가 어느 프로세스(메인/subagent)에
   적용되는지부터 실측해야 하기 때문. 30라운드가 ~8에서 잘리면 그때 설정한다.
2. **subagent 내부 PostCompact 발화 여부 미확정** → self-anchoring으로 비의존(§미션).
3. **트랜스크립트 형식 가정** → `parse_round_actions`가 "마지막 훅 주입 이후"를 라운드
   action으로 잡고, `extract_advisor_output`이 `Agent(advisor)` tool_result에서 advisor
   반환을 읽는다 — 둘 다 트랜스크립트 메시지·블록 형식에 의존한다. 어긋나면 action
   범위가 넓어지거나 region 기록이 누락될 수 있다(graceful, 치명적이지 않음).
4. **anchor의 지시 순응도** — stderr "advisor 호출"에 anchor가 실제로 응하는가.
   시스템 프롬프트로 강제하고, round 안전망이 미응답 시에도 종료를 보장한다.
5. **PreToolUse 발동·session 일치** — 자발 호출 게이팅은 PreToolUse가 depth-1 anchor의
   Agent 호출에 발동하고 그 session_id가 SubagentStop(토큰 set)과 같아야 성립한다.
   SubagentStop 발동이 강한 전례지만 라이브 확인 항목이다(미발동 시 게이팅만 무효화되고
   루프는 현행대로 — graceful). `_pretooluse_trace.log`가 발동과 stdin 구조를 실측한다.

---

## 언어와 프롬프트

모든 프롬프트는 **단일 "한국어 기반, 영어 활용"**으로 통일한다(이중 언어 쌍 없음).
식별자·경로·도구 이름과 `orchestrator` 같은 기술 용어는 영어, 산문은 한국어,
ASCII 다이어그램은 정렬을 위해 영어. 에이전트·스킬 프롬프트는 단일 `.md`이고,
훅 주입 메시지(advisor 호출 한 줄)는 짧아 `messages.py`가 인라인 조립한다.

---

## 파일 맵

```
anchor/
├── .claude-plugin/plugin.json        # manifest
├── agents/                           # 3개 tier 정의 (frontmatter 봉인 + 프롬프트 본문)
│   ├── anchor.md                     # 미션 수행자 + self-anchoring (parallax 비노출)
│   ├── advisor.md                    # parallax role+instruction 이식 (순수 분석, Write 없음)
│   └── narrator.md                   # parallax conversion 이식
├── skills/
│   ├── init/SKILL.md                 # /anchor:init — main->anchor 핸드오프 게이트
│   └── log/SKILL.md                  # /anchor:log — 분석 로그 조회
├── hooks/hooks.json                  # PreToolUse(Agent) + SubagentStop(anchor:anchor) + SessionStart(update)
├── bin/anchor-hook                   # uv 가용성 체크 래퍼 (parallax 상속)
├── src/                              # 훅 구현 (런타임 의존성: pydantic)
│   ├── state.py                      # 상태 조립 + 영속화 (round/regions/done)
│   ├── transcript.py                 # action 추출(advisor 호출 strip) + advisor 출력 추출
│   ├── prompt.py                     # deterministic advisor 입력 조립 (mission + region XML)
│   ├── messages.py                   # stderr 주입 메시지 조립
│   ├── hooks.py                      # subagent_stop · pre_tool_use 엔트리포인트
│   └── updater.py                    # SessionStart 업데이트 알림 (parallax 이식)
└── tests/                            # 구현 독립 (stdin/stdout/disk 구동)
```
