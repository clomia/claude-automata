# parallax-loop — 아키텍처

parallax-loop은 **parallax 루프** — 격리된 advisor가 매 라운드 operator가
고려하지 못한 영역을 surface해 결과 신뢰도를 극한까지 끌어올리는 자율 루프 — 를
Claude Code의 **nested subagent** 위에서 구현한 플러그인이다. parallax가 Stop 훅에서
`claude -p`를 외부 스폰하느라 구독 요금제에서 계정 차단 위험을 안았던 자리를,
정식 `Agent` 툴 호출로 대체해 그 위협을 **본질적으로 제거**한다.

---

## 용어

- **parallax loop** — 훅·operator·advisor·narrator로 매 라운드 미고려 영역을
  surface해 주입하는 자율 루프. 이 플러그인(`parallax-loop`)이 그것을 구현한다.
- **operator** — 루프에 귀속된 메인 *에이전트*(depth 1). 미션을 직접 실행한다.
  세션 `main`과 구별된다.
- **original-mission** — operator를 미션에 붙들어 매는 SSoT. 트랜스크립트 바깥
  외부 파일(`{session}_mission.md`)에 보존된다.

operator는 parallax 루프와 original-mission 재정박으로 미션에 **붙들어 매인다(anchor)**
— 자기 확신으로 표류(drift)하지도, compaction으로 미션을 잃지도 않는다. (`anchor`는
이 정박 작용을 가리키는 동사로만 남고, 주요 명사 용어에서는 폐기된다.)

---

## 문제 — parallax가 구식이 된 이유

parallax는 Stop 훅 안에서 advisor·narrator를 `claude -p` 서브프로세스로 스폰한다.
이는 `--no-session-persistence`로 **별도의 임시 세션**을 생성하는 자동화 패턴이고,
Claude Pro/Max 구독 약관상 계정 정지 위험을 부른다(실제 차단 이력 존재). 그래서
parallax는 Anthropic API 요금제 전용으로 묶였고, 구독 사용자는 손대지 못했다.

parallax 개발 당시에는 nested subagent가 불가능해 이 방법뿐이었다. 그러나
`Agent` 툴 subagent는 **모든 요금제에서 지원되는 정식 기능**이고(메인 세션과 동일
quota 공유), 서브에이전트는 다시 서브에이전트를 spawn할 수 있다(v2.1.172+, depth 5
cap). parallax-loop은 같은 루프를 이 정식 경로 위에서 재구현해 요금제 위협을 없앤다.

| | parallax | parallax-loop |
|---|---|---|
| advisor/narrator 실행 | 훅이 `claude -p` 스폰 | operator가 **Agent 툴** 호출 |
| 격리 | 별도 프로세스 | 별도 subagent (동일 격리) |
| 요금제 | API 전용 · **구독 차단 위험** | **구독 정식** (nested agent) |
| 트리거 | `parallaxthink` 키워드 | `/parallax-loop:run` (`main`의 미션 위임) |

---

## Agent Tree

`main`은 사용자와 대화하는 세션(depth 0)이고, parallax 루프는 그 아래 봉인된
서브에이전트 tier에서 돈다. 각 tier는 아래로 위임하고 위로는 요약만 반환하므로,
방대한 컨텍스트가 상위로 갈수록 압축된다.

```
main       depth 0  session       full tools              유저와 대화; 미션을 정의
   |  /parallax-loop:run  ->  writes {session}_mission.md, then Agent(operator, background)
   v
operator   depth 1  Agent +full   수행자(parallax main)   미션을 직접 실행
   |  Agent(advisor)   <- "invoke advisor" injected by SubagentStop hook
   v
advisor    depth 2  Agent Read    영역 surface            미고려 영역 분석; region 반환
   |  Agent(narrator)  Grep Glob Web*
   v
narrator   depth 3  Read (leaf)   서사 작성               action 기록을 markdown으로
```

| Tier | 도구 (allowlist) | 모델 | effort | parallax 대응 |
|---|---|---|---|---|
| **operator** | 전체 (미설정 — 모든 도구 상속) | `opus[1m]` | inherit | 메인 에이전트 |
| **advisor** | 전체 − `Bash·Write·Edit·NotebookEdit·Artifact` | `opus[1m]` | max | Advisor (`claude -p`, max) |
| **narrator** | `Read` | `sonnet` | low | Narrator (`claude -p`, low) |

- **advisor는 부작용 도구가 막혀 있다(`disallowedTools: Bash, Write, Edit, NotebookEdit, Artifact`)** — 아무것도
  쓰지 않는다. `Bash`까지 막는 것은 parallax(`DISALLOWED_TOOLS="Bash,Write,Edit,NotebookEdit"`)와 일치하며,
  Write/Edit를 막아도 `Bash`로 `echo > file`·`rm`·테스트 실행 등 부작용이 가능해 "advisor는 state를
  쓰지 않는다"(아래 상태 권위)가 무너지기 때문이다. 남은 read-only 조사 도구(`Read·Glob·Grep·Web*`)로
  영역을 사실에 근거 짓고(parallax의 CRITIC 근거: advisor가 외부 도구로 확인한 뒤 surface), `Agent`로
  narrator를 호출하며, 결과는 region 한 문단으로 **반환**한다 — 그것을 state에 기록하는 것은 hook의 몫이다.
- **narrator는 `Read`뿐인 leaf** — `Agent`가 없어 트리가 그 아래로 자라지 않는다.
  단순 변환이라 `sonnet`/`low`로 충분(parallax 그대로).
- depth 3에서 트리를 닫아 depth-5 cap에 2단계 여유를 남긴다.

---

## 핵심 루프

```
operator round N work ── stops
   |
   |  <-- SubagentStop hook (matcher: parallax-loop:operator)
   |        record last advisor verdict: termination -> done, else append region
   |        done set, or round >= ROUND_LIMIT  ->  exit 0 (allow stop)
   |        else:  parse round actions (advisor calls stripped) -> {session}_action.json
   |               write {session}_regions.md (parallax-region-history XML)
   |               round++,  exit 2 + stderr: five-section advisor trigger
   v
operator ─ Agent(advisor) ────────────> advisor (depth 2)
   |                                       ├ read original-mission  ({session}_mission.md)
   |                                       ├ Agent(narrator) -> action-history
   |                                       ├ read parallax-region-history ({session}_regions.md)
   |                                       ├ read instructions, then analyze
   |                                       └ return region / termination token
   |  <─────────── region (one paragraph) ─┘
   v
operator ─ work on the surfaced region (round N+1) ── stops ── (loop)
```

종료는 두 신호로 결정된다(parallax와 동일): advisor가 전용 종료 토큰을 내면
`done` 플래그가 서고 다음 훅이 정지를 허용하며, 그 전이라도 `ROUND_LIMIT`(30)이
무한 루프를 막는다.

---

## 컨텍스트 경제 — nested가 `claude -p`보다 우월한 지점

operator의 컨텍스트에 더해지는 것은 **① 짧은 stderr 트리거 + ② advisor가 반환한
region 한 문단**뿐이다. narrator 호출, region-history 누적 읽기, 5-section 분석은
모두 **advisor(depth 2)의 컨텍스트에서** 소비되어 operator에 닿지 않는다. region을
"한 문단으로만 출력"하는 parallax instruction이 이 경계를 지킨다. 즉 "nested로
방대한 컨텍스트를 소화한다"는 원리가 parallax의 격리 advisor와 정확히 같은
지점에서 작동한다 — advisor가 operator의 사각을 보되, 그 탐색 비용을 operator에게
전가하지 않는다.

---

## 상태와 미션 보존

모든 상태는 사용자 레포 바깥, `CLAUDE_PLUGIN_DATA`에 둔다(레포 비오염, parallax
일관). 한 세션에 하나의 미션을 가정해 `session_id`로 키잉한다(agentId 불요).

| 파일 | 작성자 | 내용 |
|---|---|---|
| `{session}_mission.md` | `main` | original-mission 정의 (트랜스크립트 독립 외부 보존) |
| `{session}_loop.json` | hook | `round` · `regions` · `done` (모두 hook이 기록) |
| `{session}_action.json` | hook | 이번 라운드 action 기록 (narrator가 읽음) |
| `{session}_regions.md` | hook | advisor 입력의 parallax-region-history (XML) |
| `{session}_loop.log` | hook | 라운드별 region·트리거 로그 (`/parallax-loop:log` 조회) |
| `{session}_advisor_token` | hook | advisor 1회 호출 인가 토큰 (SubagentStop set · PreToolUse 소비) |

**상태는 hook이 단독 소유한다.** advisor는 분석만 하고 region 한 문단(또는 종료
토큰)을 **반환**할 뿐 state를 쓰지 않는다. hook이 다음 라운드 시작에 직전 advisor
반환값을 트랜스크립트에서 추출(`extract_advisor_output`)해 `regions`에 append하거나,
종료 토큰이면 `done`을 세운다. `round`도 hook이 증가시키는 안전망이다(operator가
advisor를 무시해도 ROUND_LIMIT이 보장된다). 단일 작성자라 race가 없고, advisor
프롬프트는 운영 부담 없이 순수 분석으로 남는다 — parallax advisor도 텍스트만 반환하고
hook이 region을 기록했으므로, 이 방향이 parallax에 더 충실하다.

**미션 정박은 이중이다.**

1. **외부 보존** — `main`이 original-mission을 `{session}_mission.md`에 기록한다.
   트랜스크립트와 독립이므로 operator 내부가 어떻게 compaction되든 원본은 보존된다
   (parallax 메커니즘 1).
2. **self-anchoring** — operator·advisor의 **시스템 프롬프트**가 "맥락이 불명확하거나
   compaction되면 original-mission 파일을 다시 읽으라"고 지시한다. 시스템 프롬프트는
   compaction 후에도 그대로 reload되므로 훅보다 강한 보장이다(부트스트랩의 통찰).

훅 기반 mission 재주입(parallax 메커니즘 2)을 **그대로 옮기지 못하는** 이유: subagent
내부 compaction에서 `PostCompact` 훅이 발화하는지 미확정이기 때문(아래 리스크 §2) — 컴팩션
감지에 의존하는 mechanism 2는 재현 불가다. 대신 SubagentStop 트리거가 **매 라운드 한 줄
재정박 리마인더**(mission 경로 + "흐려졌으면 다시 읽어라")를 recency 위치에 주입해(theory §2.8),
비결정적인 self-anchoring(시스템 프롬프트)을 결정적 nudge로 보강한다 — 컴팩션 감지 없이
mechanism 2의 정신(미션을 다시 박음)을 재현한다.

---

## Hooks

| Hook | Matcher | 시점 | 동작 |
|---|---|---|---|
| **PreToolUse** | `Agent` | operator가 Agent 호출 | `advisor` 호출이면 1회용 토큰 검사 → 허용(소비) 또는 `exit 2` deny(자발 호출 차단) |
| **SubagentStop** | `parallax-loop:operator` | operator가 종료 시도 | 종료 판정 → `exit 0`(허용) 또는 `exit 2`+stderr(advisor 호출 지시) |
| **SessionStart** | `startup\|clear` | 세션 시작 | 신규 릴리스 알림 (parallax updater 이식) |

플러그인 에이전트는 `parallax-loop:<agent>`로 scoped 등록되므로, Agent 호출의
subagent_type도 이 matcher도 그 scoped 이름을 쓴다. matcher의 `:`는 정규식으로
평가되어 `parallax-loop:operator`만 잡고 `parallax-loop:advisor`·
`parallax-loop:narrator`는 제외하므로, advisor·narrator는 정상 종료해 결과를
호출자에게 반환한다 — parallax의 `PARALLAX_INSIDE_RECURSION` 재귀 가드가 구조적으로
불필요해진다. 훅은 `bin/parallax-loop-hook` 셸 래퍼를 거쳐 `uv`를 호출한다 — 래퍼가
uv 가용성을 먼저 확인하므로(parallax에서 상속), uv 미설치 시 graceful degrade와
SessionStart 안내를 한 지점에서 일원화한다.

**Graceful degradation.** `uv`가 없으면 훅 spawn은 무해하게 실패한다. operator는
parallax 루프를 모르므로(루프는 전적으로 훅이 구동) advisor 없이 미션만 수행하고
종료한다 — 트리는 돌지 않지만 세션은 깨지지 않으며, SessionStart가 uv 설치를
안내한다.

---

## 핵심 설계 결정

1. **훅은 코드라 툴을 호출할 수 없다 → 훅은 트리거, 실행은 Agent 툴.** Claude Code
   훅은 stdout/stderr/exit code로만 통신하며 tool call을 발화하지 못한다. 그래서
   `claude -p`를 Agent 툴로 *직접 치환*하는 것은 불가능하다. 대신 SubagentStop이
   `exit 2`+stderr로 operator에게 advisor 호출을 **지시**하고, operator(LLM)가 Agent
   툴로 실행한다. 이 한 단계가 parallax→parallax-loop 전환의 본질이다. operator의
   시스템 프롬프트는 parallax 루프·advisor를 **언급하지 않는다** — 자발적으로 부르면
   경로 대신 자기 의견을 advisor에 전달하거나 narrator를 건너뛰어 정해진 사용법을
   무시하기 때문이다. advisor의 존재는 stderr 지시가 처음 알린다.
2. **상태는 hook이 단독 소유.** advisor는 region/종료토큰을 반환만 하고, hook이
   트랜스크립트에서 추출해 round·regions·done을 모두 기록한다. 단일 작성자라 동시성
   문제가 없고, advisor 프롬프트가 순수 분석으로 남는다(parallax도 hook이 region 기록).
   Agent tool_result 끝에 붙는 subagent 메타(`agentId`·`usage`)는 추출 시 strip해
   region-history 오염을 막는다 — `claude -p` stdout엔 없던 nested 부산물이다.
3. **미션 정박 이중화 + self-anchoring 우선.** 외부 파일 보존 + 시스템 프롬프트
   재독. PostCompact 불확실성을 우회.
4. **session 기반 단일 미션.** 한 세션 한 미션으로 agentId 키잉을 제거(단순성).
   다중 동시 미션은 비목표.
5. **프롬프트 보존과 5-section 순서 재현.** parallax의 `role`·`instruction`·`conversion`
   전문을 이식한다. parallax `prompt.py`는 5-section(role·original-mission·action-history·
   parallax-region-history·instructions)을 한 XML로 조립해 advisor에 한 번에 넘겼다.
   parallax-loop은 hook이 advisor를 직접 못 부르므로 같은 **순서**를 trigger로 재현한다 —
   role은 advisor 시스템 프롬프트, instructions는 정적 파일(`prompts/instruction.md`),
   original-mission·parallax-region-history는 파일(`mission.md`·`regions.md`),
   action-history는 inline narrator 호출. trigger가 이들을 parallax 순서로 나열하고,
   advisor가 위에서 아래로 읽거나 실행해 동일한 순서로 맥락을 쌓는다(`prompt.py`).
   다만 nested 구조상 두 가지가 어긋난다. **(a)** action narrative만 런타임 수집으로
   남는다(narrating은 LLM이라 hook이 못 부른다). **(b)** 정박 미션이 parallax의
   *사용자 원문*에서 parallax-loop의 *main 작성 명세*(`mission.md`)로 바뀌었고 이는
   advisor에도 전파된다 — `main`이 미션을 정의하는 설계의 의도된 결과이나, source of
   truth가 사용자 발화에서 한 단계 멀어진 트레이드다. action-history는 advisor 호출을
   strip해 region-history와 분리를 지킨다(parallax는 advisor가 외부 프로세스라 애초에
   섞이지 않았다).
6. **단일 모델 `opus[1m]`(operator·advisor).** 추론 최대화와 compaction 빈도 감소가
   같은 선택으로 수렴(부트스트랩 정신). narrator만 단순 변환이라 `sonnet`/`low`로
   parallax를 충실히 보존.
7. **플러그인 영역만, `settings.json` 불간섭.** 활성화는 `main`→`operator` 핸드오프.
   미션 없이는 아무것도 발화하지 않는다.
8. **프로젝트 CLAUDE.md 상속 수용.** custom subagent는 사용 프로젝트의 CLAUDE.md·rules를
   상속하며 차단 옵션이 없다(Explore·Plan만 예외, frontmatter/setting 부재). 이를 수용한다
   — operator는 코드 작업에 프로젝트 코딩 규칙이 *필요*하기 때문. advisor·narrator도 함께
   상속받아 약한 오염 여지가 있으나(narrator의 "원문 보존" vs 프로젝트 "간결" 등), 차단이
   all-or-nothing이라 operator의 필요를 우선한다. 선택적 차단 옵션이 생기면 advisor·narrator에
   적용한다.
9. **자발 advisor 호출 차단(PreToolUse 게이팅).** operator가 hook 지시 없이 스스로 advisor를
   부르면 결정론적 사이클이 깨진다 — 라운드 0 자발 호출의 출력은 누락되고, 한 정지에 여러
   호출이 섞이면 `extract_advisor_output`이 일부만 잡으며, hook이 지정한 5-section 입력 대신
   operator 자기 말이 입력으로 간다. SubagentStop이 호출을 지시할 때만 1회용 토큰을 세우고,
   PreToolUse(matcher `Agent`)가 advisor 호출을 토큰이 있을 때만 통과시킨다(없으면
   deny → operator는 작업을 계속하다 멈추고 정식 지시를 받는다). deny된 호출은 트랜스크립트에
   error tool_result로 남으므로 `extract_advisor_output`은 `is_error`를 걸러 성공한 호출만
   기록한다. narrator는 read-only leaf이자 hook 사이클 밖이라 게이팅하지 않는다.
10. **메인 transcript에서 operator transcript 해소.** SubagentStop은 hook에 정지한 subagent가
   아니라 **메인 세션 transcript**를 넘긴다(실측 확정). operator의 작업은
   `{session}/subagents/agent-{agentId}.jsonl`에 따로 있으므로, hook은 메인 transcript에서
   **마지막** `parallax-loop:operator` spawn의 tool_use id를 찾아 subagent `meta.json`의
   `toolUseId`와 매칭해 그 operator transcript를 해소한 뒤 action·advisor 출력을 읽는다(메인이
   operator를 여러 번 spawn해도 마지막=현재를 집는다). 해소 실패 시 정지를 허용한다(graceful).
   이 경로·메타 형식은 비공개 구조이나 실세션 로그로 확인됐다.
11. **로깅: 사후 조회 + 원본 패리티.** 메인에 실시간 표시하지 않는다 — hook의 systemMessage는
   exit 2에서 stdout이 버려져 안 떴고, exit 0+JSON `decision:block`은 SubagentStop 연속이 미검증이라
   루프를 위험에 빠뜨린다. 대신 `_loop.log`에 적어 `/parallax-loop:log`로 사후 조회한다. 라운드마다
   기록하는 것은 **action-history 서사 + region** 두 가지로, 원본 parallax 로그(`analysis_prompt`의
   서사 + `new_advice`)와 같은 substance다. 서사는 advisor가 동기 실행한 narrator의 출력인데,
   nested 구조상 operator가 아니라 advisor 컨텍스트에만 들어가므로(§컨텍스트 경제), hook이
   advisor 서브에이전트 transcript에서 그 narrator tool_result를 회수한다(`extract_action_narrative` —
   operator transcript에서 마지막 advisor 호출 → advisor transcript → narrator 출력, 한 단계 하강).
   트리거 자체는 정적 경로 pointer라 진행 파악에 무의미해 로그에 남기지 않는다(원본의 `analysis_prompt`
   중 mission·region-history는 파일·라운드별 region으로 이미 보임).
12. **advisor 호출은 동기다(`run_in_background=false`).** Agent 툴은 이 빌드에서 기본 async라,
   백그라운드로 뜬 호출의 tool_result는 region이 아니라 "Async agent launched..." launch acknowledgement다 —
   그것을 region으로 기록하면 region·종료토큰·라운드가 한 채널에서 한꺼번에 desync한다(첫 실세션
   실측: round 30·done=false·region 전부 acknowledgement). 원본 parallax는 훅이 `subprocess.run(claude -p)`로
   advisor를 동기 실행해 stdout을 곧 region으로 받았다. nested 경로에선 훅이 호출자가 될 수 없어
   operator를 경유하지만, 그 relay는 호출이 **블로킹**일 때만 region을 tool_result로 운반한다. 그래서
   trigger가 호출을 **동기로(`run_in_background=false`)·축자로(프롬프트에 아무것도 더하지 말 것)**
   실행하라 지시하고(`prompt.py`), `extract_advisor_output`은 launch acknowledgement를 region으로 인정하지 않는
   가드를 둔다(`transcript.py`) — 동기가 어떤 이유로 깨져도 region-history는 오염 대신 graceful
   stall한다. 축자 지시는 operator가 advisor 입력에 자기 해석을 끼워 넣는 것도 막는다(5-section이
   유일한 맥락). 이 동기·축자 relay가 원본의 in-hook 동기 실행을 nested 위에서 재현한다.
   **advisor가 도는 inlined narrator 호출도 같은 이유로 `run_in_background=false`다** — async면
   advisor가 narration(action-history)을 받지 못한 채 분석하게 되어(theory §2.9 narrator 계층 무력화)
   원본과 어긋나고, 로그용 narration 회수(결정 11)도 불가능해진다. 동기여야 narration이 advisor의
   narrator tool_result로 남아 분석 입력이자 로그 소스가 된다.

---

## 기술 리스크 — 첫 실제 실행으로 검증

설계는 성립하나 라이브 트리 없이 유닛 테스트할 수 없던 항목들이다. 모두
**graceful degrade**하도록 설계했고, 첫 실세션 로그로 3·4·5는 확인됐다.

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
4. **operator의 지시 순응도** — stderr "advisor 호출"에 operator가 실제로 응하는가.
   시스템 프롬프트로 강제하고, round 안전망이 미응답 시에도 종료를 보장한다.
5. **PreToolUse 발동·session 일치** — 자발 호출 게이팅은 PreToolUse가 depth-1 operator의
   Agent 호출에 발동하고 그 session_id가 SubagentStop(토큰 set)과 같아야 성립한다.
   SubagentStop 발동이 강한 전례다(미발동 시 게이팅만 무효화되고 루프는 현행대로 —
   graceful). 실세션 로그에서 PreToolUse가 advisor·narrator 호출에 발동하고 session_id가
   SubagentStop과 일치함을 확인했다.
6. **background operator의 nested 동기 호출** — operator는 run skill에서 background로 spawn되는데
   (메인을 자유롭게 두어 `/parallax-loop:log` 실시간 조회를 위함), 그 안에서 `run_in_background=false`가
   honor되어 advisor가 동기로 도는지는 nested-from-background 케이스라 실세션으로만 확정된다
   (foreground 부모에선 동기 확정). honor되지 않으면 §핵심 설계 결정 12의 가드로 graceful stall하며,
   fallback은 run skill에서 operator를 foreground로 돌리는 것이다(fg·bg 모두 ban-safe; 잃는 것은
   실시간 로그뿐, `_loop.log` 사후 조회는 유지). 첫 async 기본값은 이 리스크 목록이 예상 못 한 항목으로,
   첫 실세션에서 드러나 결정 12로 대응했다.

---

## 언어와 프롬프트

모든 프롬프트는 **단일 "한국어 기반, 영어 활용"**으로 통일한다(이중 언어 쌍 없음).
식별자·경로·도구 이름과 `orchestrator` 같은 기술 용어는 영어, 산문은 한국어,
ASCII 다이어그램은 정렬을 위해 영어. 에이전트·스킬 프롬프트와 advisor instruction은
단일 `.md`이고, 훅 주입 메시지(advisor trigger)는 `prompt.py`가 조립한다.

---

## 파일 맵

```
parallax-loop/
├── .claude-plugin/plugin.json        # manifest
├── agents/                           # 3개 tier 정의 (frontmatter 봉인 + 프롬프트 본문)
│   ├── operator.md                   # 미션 수행자 + self-anchoring (parallax 루프 비노출)
│   ├── advisor.md                    # parallax role 이식 + 5-section 순서 지침 (Write 없음)
│   └── narrator.md                   # parallax conversion 이식
├── prompts/instruction.md           # advisor 분석·출력 지침 (parallax instruction 이식)
├── skills/
│   ├── run/SKILL.md                  # /parallax-loop:run — main->operator 핸드오프 게이트
│   └── log/SKILL.md                  # /parallax-loop:log — 분석 로그 조회
├── hooks/hooks.json                  # PreToolUse(Agent) + SubagentStop(parallax-loop:operator) + SessionStart(update)
├── bin/parallax-loop-hook           # uv 가용성 체크 래퍼 (parallax 상속)
├── src/                              # 훅 구현 (런타임 의존성: pydantic)
│   ├── main.py                       # subagent_stop · pre_tool_use 엔트리포인트
│   ├── state.py                      # 상태 조립 + 영속화 (round/regions/done)
│   ├── transcript.py                 # action 추출(advisor 호출 strip) + advisor 출력 추출(meta strip)
│   ├── prompt.py                     # region-history 포맷 + 5-section advisor trigger 조립
│   └── updater.py                    # SessionStart 업데이트 알림 (parallax 이식)
└── tests/                            # 구현 독립 (stdin/stdout/disk 구동)
```
