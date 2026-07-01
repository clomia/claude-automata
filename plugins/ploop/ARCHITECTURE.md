# ploop — 아키텍처

ploop은 **parallax 루프** — 격리된 advisor가 매 라운드 main이 고려하지 못한
영역을 surface해 결과 신뢰도를 극한까지 끌어올리는 자율 루프 — 를 Claude Code의
**nested subagent** 위에서 구현한 플러그인이다. parallax가 Stop 훅에서 `claude -p`를
외부 스폰하느라 구독 요금제에서 계정 차단 위험을 안았던 자리를, advisor·narrator를
정식 `Agent` 툴 호출로 대체해 그 위협을 **본질적으로 제거**한다. parallax의 통합
지점(Stop 훅)과 main 역할(세션 에이전트)은 그대로 보존한다.

---

## 용어

- **parallax loop** — 훅·advisor·narrator로 매 라운드 미고려 영역을 surface해 main에
  주입하는 자율 루프. 이 플러그인(`ploop`)이 그것을 구현한다.
- **main** — parallax main 역할을 하는 세션 에이전트(depth 0). 미션을 직접 실행하고
  매 라운드 advisor를 호출한다. parallax의 메인 에이전트와 같은 위상이다.
- **original-mission** — main을 미션에 붙들어 매는 SSoT. 트랜스크립트 바깥 외부
  파일(`{session}_mission.md`)에 보존된다.

main은 parallax 루프와 original-mission 재정박으로 미션에 **붙들어 매인다(anchor)** —
자기 확신으로 표류(drift)하지도, compaction으로 미션을 잃지도 않는다.

---

## 문제 — parallax가 구식이 된 이유

parallax는 Stop 훅 안에서 advisor·narrator를 `claude -p` 서브프로세스로 스폰한다.
이는 `--no-session-persistence`로 **별도의 임시 세션**을 생성하는 자동화 패턴이고,
Claude Pro/Max 구독 약관상 계정 정지 위험을 부른다(실제 차단 이력 존재). 그래서
parallax는 Anthropic API 요금제 전용으로 묶였고, 구독 사용자는 손대지 못했다.

parallax 개발 당시에는 nested subagent가 불가능해 이 방법뿐이었다. 그러나 `Agent` 툴
subagent는 **모든 요금제에서 지원되는 정식 기능**이고(메인 세션과 동일 quota 공유),
서브에이전트는 다시 서브에이전트를 spawn할 수 있다(v2.1.172+, depth 5 cap).
ploop은 같은 루프를 이 정식 경로 위에서 재구현해 요금제 위협을 없앤다 — main이
advisor를 `Agent` 툴로 호출하고, advisor가 narrator를 호출한다.

| | parallax | ploop |
|---|---|---|
| advisor/narrator 실행 | 훅이 `claude -p` 스폰 | main·advisor가 **Agent 툴** 호출 |
| 격리 | 별도 프로세스 | 별도 subagent (동일 격리) |
| 요금제 | API 전용 · **구독 차단 위험** | **구독 정식** (nested agent) |
| 트리거 | `parallaxthink` 키워드 | `/ploop:launch` (미션 핸드오프) |
| parallax main 역할 | 세션 메인 에이전트 | 세션 메인 에이전트 (**동일**) |

마지막 행이 핵심이다. ploop은 advisor/narrator의 실행 경로만 nested로 바꾸고,
parallax main 역할은 parallax와 똑같이 세션 에이전트에 둔다. (초기 버전은 그 역할을
`operator` subagent(depth 1)에 두어 트리가 한 단계 깊었으나, operator는 격리 이점을
주지 않으면서 부채만 떠안겨 제거했다 — git history.)

---

## Agent Tree

`main`은 사용자와 대화하는 세션(depth 0)이자 parallax 루프의 수행자다. advisor·narrator는
그 아래 봉인된 서브에이전트 tier에서 돈다. 각 tier는 아래로 위임하고 위로는 요약만
반환하므로, 방대한 컨텍스트가 상위로 갈수록 압축된다.

```
main      depth 0  session     full tools    parallax main: runs the mission
   |  Agent(advisor)  <- "invoke advisor" injected by Stop hook
   v
advisor   depth 1  Agent ro    surface region   analyzes blind spots; returns region
   |  Agent(narrator)  Grep Glob Web*
   v
narrator  depth 2  Read(leaf)  narrate          action records -> markdown
```

| Tier | 도구 (allowlist) | 모델 | effort | parallax 대응 |
|---|---|---|---|---|
| **main** | 전체 (세션) | `opus[1m]` 권장 | inherit | 메인 에이전트 |
| **advisor** | 전체 − `Bash·Write·Edit·NotebookEdit·Artifact` | `opus[1m]` | max | Advisor (`claude -p`, max) |
| **narrator** | `Read` | `sonnet` | low | Narrator (`claude -p`, low) |

- **advisor는 부작용 도구가 막혀 있다(`disallowedTools: Bash, Write, Edit, NotebookEdit, Artifact`)** —
  아무것도 쓰지 않는다. `Bash`까지 막는 것은 parallax(`DISALLOWED_TOOLS="Bash,Write,Edit,NotebookEdit"`)와
  일치하며, Write/Edit만 막으면 `Bash`로 `echo > file`·`rm`·테스트 실행 등 부작용이 가능해
  "advisor는 state를 쓰지 않는다"가 무너지기 때문이다. 남은 read-only 조사 도구(`Read·Glob·Grep·Web*`)로
  영역을 사실에 근거 짓고(parallax의 CRITIC 근거), `Agent`로 narrator를 호출하며, 결과는 region 한
  문단으로 **반환**한다 — 그것을 state에 기록하는 것은 hook의 몫이다.
- **narrator는 `Read`뿐인 leaf** — `Agent`가 없어 트리가 그 아래로 자라지 않는다. 단순 변환이라
  `sonnet`/`low`로 충분(parallax 그대로).
- depth 2에서 트리를 닫아 depth-5 cap에 3단계 여유를 남긴다.

---

## 핵심 루프

```
main round N work ── stops
   |
   |  <-- Stop hook
   |        record last advisor verdict (parallax's rule):
   |          empty output or termination token -> done + deactivate
   |          region -> append
   |        round >= ROUND_LIMIT  ->  exit 0 (allow stop) + deactivate
   |        else:  parse round actions (advisor calls stripped) -> {session}_action.json
   |               write {session}_regions.md (parallax-region-history XML)
   |               round++,  exit 2 + stderr: advisor trigger (+ mission text if compacted)
   v
main ─ Agent(advisor) ───────────> advisor (depth 1)
   |                                  ├ read original-mission   ({session}_mission.md)
   |                                  ├ Agent(narrator) -> action-history
   |                                  ├ read parallax-region-history ({session}_regions.md)
   |                                  ├ read instructions, then analyze
   |                                  └ return region / termination token
   |  <─────────── region (one paragraph) ─┘
   v
main ─ work on the surfaced region (round N+1) ── stops ── (loop)
```

종료는 parallax와 동일하게 결정된다: advisor가 빈 출력을 내거나 전용 종료 토큰을 내면 `done`
플래그가 서고 active 마커가 정리되어 다음 정지가 허용되며(`if not verdict or TERMINATION_TOKEN
in verdict`), 그 전이라도 `ROUND_LIMIT`(30)이 무한 루프를 막는다. 고지능 모델 advisor가 빈
출력이나 async를 내는 것은 Claude Code 보장 범위 밖이라 별도 대응(stall·미호출 감지)을 두지
않는다 — 원본 parallax가 그랬듯 단순하게 처리한다(고지능 순응 가정).

Stop 훅은 메인 세션 정지마다 발화하므로 active 마커가 게이트한다(아래 상태). advisor·narrator의
정지는 `SubagentStop`이라 이 Stop 훅에 잡히지 않는다 — parallax의 `PARALLAX_INSIDE_RECURSION`
재귀 가드가 구조적으로 불필요하다.

---

## 컨텍스트 경제 — nested가 `claude -p`보다 우월한 지점

main의 컨텍스트에 더해지는 것은 **① 짧은 stderr 트리거 + ② advisor가 반환한 region 한
문단**뿐이다. narrator 호출, region-history 누적 읽기, 5-section 분석은 모두 **advisor(depth 1)의
컨텍스트에서** 소비되어 main에 닿지 않는다. region을 "한 문단으로만 출력"하는 parallax
instruction이 이 경계를 지킨다. advisor가 main의 사각을 보되, 그 탐색 비용을 main에 전가하지
않는다 — 원본 parallax가 narrator·advisor를 hook 코드로 실행해 메인 컨텍스트를 보호한 것과
정확히 같은 효과다.

---

## 상태와 미션 보존

모든 상태는 사용자 레포 바깥, `CLAUDE_PLUGIN_DATA`에 둔다(레포 비오염, parallax 일관). 한
세션에 하나의 미션을 가정해 `session_id`로 키잉한다.

| 파일 | 작성자 | 내용 |
|---|---|---|
| `{session}_mission.md` | main (launch skill) | original-mission 정의 (외부 보존 anchor) |
| `{session}_active` | main 생성 · hook 삭제 | 활성화 마커 (Stop 게이트) |
| `{session}_loop.json` | hook | `round` · `regions` · `done` |
| `{session}_action.json` | hook | 이번 라운드 action 기록 (narrator가 읽음) |
| `{session}_regions.md` | hook | advisor 입력의 parallax-region-history (XML) |
| `{session}_loop.log` | hook | 라운드별 사후 로그 (region) |
| `{session}_advisor_token` | hook | advisor 1회 호출 인가 토큰 (Stop set · PreToolUse 소비) |
| `{session}_advisor_running` | hook | advisor in-flight 마커 (PreToolUse set · SubagentStop clear · Stop 가드) |
| `{session}_compacted` | hook (PostCompact) | compaction 발생 마커 (Stop이 메커니즘 2로 소비) |

**loop 상태(round·regions·done)는 hook이 단독 소유한다.** advisor는 분석만 하고 region 한
문단(또는 종료 토큰)을 **반환**할 뿐 state를 쓰지 않는다. hook이 다음 라운드 시작에 직전
advisor 반환값을 트랜스크립트에서 추출(`extract_advisor_output`)해 `regions`에 append하거나,
종료 토큰이면 `done`을 세운다. `round`도 hook이 증가시키는 안전망이다. 단일 작성자라 race가
없고, advisor 프롬프트는 순수 분석으로 남는다 — parallax advisor도 텍스트만 반환하고 hook이
region을 기록했으므로, 이 방향이 parallax에 충실하다. (`mission.md`·`active` 마커는 활성화
신호라 main이 만든다 — parallax도 미션·활성화는 사용자 입력/UserPromptSubmit이, loop state는
hook이 소유했다.)

**활성화 lifecycle.** Stop 훅은 메인 세션 정지마다 발화하므로 active 마커가 루프를 게이트한다.

1. `/ploop:launch`가 `mission.md`와 `active` 마커를 쓰고, main이 미션을 직접 수행하기
   시작한다.
2. `UserPromptSubmit`이 매 새 사용자 턴마다 `active`·`loop.json`·`advisor_token`·`compacted`를
   지운다(turn-boundary cleanup). 명시적 launch만 (재)활성화하므로, ESC로 끊긴 미션이 다음 사용자
   입력에 조용히 재개되지 않고, stale 토큰이 다음 미션의 라운드 0 자발 호출을 인가하지도 못한다.
   `mission.md`는 anchor로 보존된다.
3. Stop 훅이 종료(done/limit) 시 `active` 마커를 지운다.

이는 parallax의 `_active` 마커 + UserPromptSubmit turn-boundary cleanup 패턴을 그대로 옮긴
것이다(operator subagent 시절에는 SubagentStop이 미션 전용 subagent에만 발화해 이 게이트가
불필요했으나, main 승격으로 Stop이 일반 대화에도 발화하면서 parallax의 활성화 관리로 회귀한다).

**미션 정박은 네 겹이며, 마지막이 parallax 메커니즘을 그대로 보존한다.**

1. **외부 보존(메커니즘 1)** — launch가 original-mission을 `mission.md`에 기록한다. 트랜스크립트와
   독립이라 main 내부가 어떻게 compaction되든 원본은 보존된다.
2. **self-anchoring(launch 스킬 본문)** — launch 스킬의 본문이 "mission.md를 닻으로, 흐려지면 다시
   읽으라"고 지시한다. 호출된 스킬 본문은 auto-compact 후에도 re-inject되어(스킬당 앞 5,000토큰·
   합산 25,000토큰 예산) 보존되므로 이 지시는 compaction을 견딘다(메인 세션은 커스텀 시스템
   프롬프트를 못 받지만 스킬 re-inject가 그 자리를 메운다 — 초기 operator subagent 시스템 프롬프트의 역할).
3. **라운드 경계 트리거 재정박** — 매 라운드 Stop 트리거가 recency 위치에 `mission.md` 경로 +
   "흐려졌으면 다시 읽어라"를 박는다.

위 세 겹은 모두 *포인터*다 — "mission.md를 읽어라"라는 지시이지 미션 텍스트 자체가 아니며, agent가
드리프트를 자각해 다시 읽기로 선택해야 작동한다. 그런데 goal drift는 점진적이라 agent가 스스로
감지하지 못한다(theory §4.2). 그래서 네 번째 겹이 필요하다.

4. **메커니즘 2(PostCompact + 미션 텍스트 inline)** — `PostCompact` 훅이 `_compacted` 마커를
   touch하고, 다음 Stop이 그 마커를 소비하며 **그 라운드 트리거에 original-mission 원문 텍스트를
   recency 위치에 inline**한다(`format_advisor_trigger`의 `mission_text`). 포인터·자가감지에 의존하는
   1–3과 달리, 이것은 **discrete한 compaction 이벤트에 미션 텍스트 자체를 무조건** 박는다 — 원본
   parallax 메커니즘 2와 정확히 같다. 메인 세션은 `PostCompact`가 확실히 발화하므로(초기 nested
   버전의 미확정 리스크가 해소됨) 이 복원이 가능하다.

---

## Hooks

| Hook | Matcher | 시점 | 동작 |
|---|---|---|---|
| **UserPromptSubmit** | (전체) | 새 사용자 턴 | `active`·`loop.json`·`advisor_token`·`advisor_running`·`compacted` 삭제 (turn cleanup → ESC 후 무단 재개·토큰 누출 차단) |
| **PostCompact** | `auto` | auto-compaction 후 | `compacted` 마커 touch (Stop이 메커니즘 2로 미션 텍스트 재주입) |
| **PreToolUse** | `Agent` | main이 Agent 호출 | `advisor` 호출이면 1회용 토큰 검사 → 허용(소비 + `advisor_running` 마커 set) 또는 `exit 2` deny(자발 호출 차단) |
| **Stop** | (전체) | main이 종료 시도 | active 게이트 → **in-flight 가드** → 종료 판정 → `exit 0`(허용) 또는 `exit 2`+stderr(advisor 호출 지시) |
| **SubagentStop** | (전체) | subagent 종료 | `advisor` 종료면 `advisor_running` 마커 clear (in-flight 추적) |
| **SessionStart** | `startup\|clear` | 세션 시작 | 신규 릴리스 알림 (parallax updater 이식) |

플러그인 에이전트는 `ploop:<agent>`로 scoped 등록되므로, Agent 호출의 subagent_type이
그 scoped 이름을 쓴다. Stop 훅은 본질적으로 메인 세션 정지에만 발화하고 advisor·narrator의
정지는 `SubagentStop`이라, ploop:operator만 잡던 matcher 정규식이 더는 필요 없다. 훅은
`bin/ploop-hook` 셸 래퍼를 거쳐 `uv`를 호출한다 — 래퍼가 uv 가용성을 먼저 확인하므로,
uv 미설치 시 graceful degrade와 SessionStart 안내를 한 지점에서 일원화한다.

**Graceful degradation.** `uv`가 없으면 훅 spawn은 무해하게 실패한다. main은 parallax 루프를
모르므로(루프는 전적으로 훅이 구동) advisor 없이 미션만 수행하고 종료한다 — 루프는 돌지 않지만
세션은 깨지지 않으며, SessionStart가 uv 설치를 안내한다.

---

## 핵심 설계 결정

1. **parallax main = 세션 메인 에이전트.** parallax 루프의 main 역할을 세션 에이전트(depth 0)가
   직접 한다 — 원본 parallax와 같은 위상이고, 트리거는 Stop 훅이다. advisor·narrator만 nested
   subagent로 격리해 구독 안전성을 얻는다. (초기 버전은 main 역할을 `operator` subagent(depth 1)에
   두어 트리가 4-tier였으나, operator는 어떤 격리 이점도 주지 않으면서 — 미션 작업은 원래 main
   컨텍스트에서 일어나고 parallax도 격리하지 않았다 — `find_operator_transcript` 해소,
   background-nested 동기 호출, subagent `PostCompact` 불확실성을 떠안겼다. 제거가 순수 이득이다.)
2. **훅은 코드라 툴을 호출할 수 없다 → 훅은 트리거, 실행은 Agent 툴.** Claude Code 훅은
   stdout/stderr/exit code로만 통신하며 tool call을 발화하지 못한다. 그래서 `claude -p`를 Agent
   툴로 *직접 치환*하는 것은 불가능하다. 대신 Stop이 `exit 2`+stderr로 main에게 advisor 호출을
   **지시**하고, main(LLM)이 Agent 툴로 실행한다. 이 한 단계가 parallax→ploop 전환의
   본질이다. main의 컨텍스트(launch 스킬·트리거)는 parallax 루프 메커니즘을 advisor라는 단어로
   **언급하지 않는다** — 자발적으로 부르면 경로 대신 자기 의견을 advisor에 전달하거나 narrator를
   건너뛰기 때문이다. advisor의 존재는 stderr 지시가 처음 알린다.
3. **loop 상태는 hook이 단독 소유.** advisor는 region/종료토큰을 반환만 하고, hook이 트랜스크립트에서
   추출해 round·regions·done을 모두 기록한다. 단일 작성자라 동시성 문제가 없고, advisor 프롬프트가
   순수 분석으로 남는다. Agent tool_result 끝에 붙는 subagent 메타(`agentId`·`usage`)는 추출 시
   strip해 region-history 오염을 막는다.
4. **작업 transcript = 메인 transcript.** Stop 훅은 메인 세션 transcript를 직접 건넨다. main이
   미션을 직접 수행하므로 action과 advisor 호출(tool_use/tool_result)이 모두 거기 있다 — operator의
   별도 transcript를 `subagents/meta.json`으로 해소하던 단계가 통째로 사라진다.
5. **활성화 게이트 + UserPromptSubmit turn cleanup.** `/ploop:launch`가 `mission.md`·`active`
   마커를 쓰고 main을 미션 모드로 진입시킨다. Stop은 `active`가 있을 때만 루프를 돌고, 종료 시
   마커를 지운다. UserPromptSubmit이 매 사용자 턴 마커·`loop.json`을 지워, ESC로 끊긴 미션이
   무단 재개되지 않는다. parallax의 활성화 패턴을 그대로 옮긴 것.
6. **미션 정박 — 메커니즘 1 + 2 (parallax 그대로).** 외부 보존(`mission.md`, 메커니즘 1)으로
   미션 원문은 디스크에 영속하고, `PostCompact`가 `_compacted`를 touch하면 compacted 라운드의
   Stop이 트리거에 미션 원문 텍스트를 inline한다(메커니즘 2 — discrete compaction 이벤트에 무조건
   텍스트 주입). 메인 세션 `PostCompact`는 공식 문서로 보장된다. advisor가 매 라운드 original-mission을
   읽고 미션-grounded region을 surface하므로 main은 advisor 경유로도 간접 정박된다. launch 스킬 본문의
   self-anchoring은 main이 mission.md를 닻으로 삼게 부트스트랩한다. parallax에 없던 "매 라운드
   포인터"는 메커니즘 2·advisor·스킬과 중복이라 두지 않는다(irreducible).
7. **프롬프트는 parallax 원본 충실.** advisor·narrator·instruction은 parallax의
   `role`·`conversion`·`instruction`을 이식하며, 분석 대상을 원본과 같은 **"main agent"**로 부른다
   (operator subagent 시절에는 "operator"로 멀어졌던 것을 원복). parallax `prompt.py`는 5-section
   (role·original-mission·action-history·parallax-region-history·instructions)을 한 XML로 조립해
   advisor에 넘겼다. ploop은 hook이 advisor를 직접 못 부르므로 같은 **순서**를 trigger로
   재현한다 — role은 advisor 시스템 프롬프트, original-mission·region-history·instructions는 파일,
   action-history는 advisor가 트리거에 inline된 narrator Agent 호출을 실행해 조립한다. **트리거는
   advisor의 Agent 호출을 — 그 안에 narrator Agent 호출을 inline해 — 축자로 작성해 넘긴다. hook이
   정확한 호출을 작성하고(parallax가 `subprocess.run`으로 했듯) main·advisor는 그대로 relay한다.**
   리터럴 호출을 그대로 건네는 것이 가장 단순·결정론적이다 — LLM이 구성할 것이 없다. advisor는 네
   경로를 위에서 아래로 읽어 parallax와 동일 순서로 맥락을 쌓는다(advisor.md). nested 구조상 두 가지가
   어긋난다. **(a)** action narrative만
   런타임 수집(narrating은 LLM이라 hook이 못 부른다). **(b)** 정박 미션이 parallax의 *사용자 원문*에서
   ploop의 *main 작성 명세*(`mission.md`)로 바뀌었고 advisor에도 전파된다 — main이 미션을
   정의하는 설계의 의도된 결과이나 source of truth가 한 단계 멀어진 트레이드다. action-history는 advisor
   호출을 strip해 region-history와 분리를 지킨다.
8. **단일 모델 `opus[1m]`(main·advisor).** 추론 최대화와 compaction 빈도 감소가 같은 선택으로
   수렴. narrator만 단순 변환이라 `sonnet`/`low`로 parallax를 충실히 보존. main은 세션 모델이라
   사용자가 `opus[1m]`로 실행하길 권장한다.
9. **자발 advisor 호출 차단(PreToolUse 게이팅).** main이 hook 지시 없이 스스로 advisor를 부르면
   결정론적 사이클이 깨진다 — 라운드 0 자발 호출의 출력은 누락되고, 한 정지에 여러 호출이 섞이면
   `extract_advisor_output`이 일부만 잡으며, hook이 지정한 5-section 입력 대신 main 자기 말이
   입력으로 간다. Stop이 호출을 지시할 때만 1회용 토큰을 세우고, PreToolUse(matcher `Agent`)가
   advisor 호출을 토큰이 있을 때만 통과시킨다(없으면 deny). deny된 호출은 error tool_result로
   남으므로 `extract_advisor_output`은 `is_error`를 걸러 성공한 호출만 기록한다. narrator는 read-only
   leaf이자 hook 사이클 밖이라 게이팅하지 않는다. UserPromptSubmit이 토큰을 turn-boundary에서 지워
   stale 토큰이 다음 미션의 라운드 0 자발 호출을 인가하지 못하게 한다. (고지능 모델은 트리거에 순응해
   매 라운드 advisor를 호출한다고 가정하나, 만일 미호출로 정지하면 — 토큰이 소비되지 않고 남는다 —
   Stop은 stale region 추출을 건너뛰어 직전 region이 중복 기록되지 않게 한다.)
10. **advisor·narrator 호출은 동기다(`run_in_background=false`).** Agent 툴은 이 빌드에서 기본 async라,
    백그라운드 호출의 tool_result는 region이 아니라 launch acknowledgement다. main은 **foreground**이고,
    trigger가 advisor·narrator 호출을 모두 `run_in_background=false`로 작성해(narrator는 advisor 프롬프트에
    inline) 동기 실행을 지시하며, 고지능 모델이 이를 따른다. 동기여야 region이 advisor 호출의 tool_result로
    돌아오고, narrator narration이 advisor의 분석 입력이 된다. 빈 출력·async처럼 Claude Code 보장 밖
    케이스는 별도 가드 없이 parallax의 단순 규칙(빈 출력=종료)으로 처리한다.
11. **로깅: region 사후 기록.** `_loop.log`에 라운드마다 advisor가 surface한 **region**을 적어
    파일로 사후 조회할 수 있게 한다 — 원본 parallax 로그의 load-bearing 콘텐츠(`new_advice`, 추론 trace)와
    같다. action-history 서사는 로그하지 않는다: parallax에선 hook 로컬변수라 로깅이 공짜였지만 nested에선
    narration이 advisor 컨텍스트에 갇혀 cross-transcript 하강이 필요한데, 그 내용(main 작업)은 사용자가
    세션에서 이미 본 것이라 비용 대비 가치가 없다(narrator는 advisor의 분석 입력으로는 계속 돈다).
12. **플러그인 영역만, `settings.json` 불간섭.** 활성화는 `/ploop:launch` 핸드오프. 미션 없이는
    아무것도 발화하지 않는다. 프로젝트 CLAUDE.md·rules는 main·advisor·narrator가 모두 상속한다(custom
    subagent 차단 옵션 부재) — main은 코드 작업에 프로젝트 코딩 규칙이 *필요*하므로 이를 수용한다.
    advisor·narrator도 함께 상속받아 약한 오염 여지가 있으나, 차단이 all-or-nothing이라 main의 필요를
    우선한다.
13. **advisor in-flight 가드(background 전환 cascade 차단).** advisor 호출을 `run_in_background=false`로
    지시해도 사용자가 단축키로 실행 중인 advisor를 background로 보낼 수 있다. 그 순간 main 세션 Stop이
    발화하는데, 그대로 재주입하면 advisor가 하나 더 spawn되고 다음 정지에 또 spawn되어 **무한 증식**한다
    (nested 전환이 낳은 신규 리스크 — parallax는 advisor를 hook 안에서 동기 실행해 이 틈이 없었다).
    PreToolUse가 advisor 인가 시 `advisor_running` 마커를 set하고 SubagentStop이 종료 시 clear한다. Stop은
    마커가 있으면 재주입하지 않고 `exit 0`으로 대기한다 — 단 마커가 남았어도 transcript에 완료 결과
    (`</usage>` 엔벨로프)가 보이면(SubagentStop 누락) 마커를 정리하고 진행해 stall을 피한다. background로
    보낸 advisor의 region은 유실될 수 있으나 cascade는 확실히 차단된다.

---

## 기술 리스크

설계는 성립하나 라이브 트리 없이 유닛 테스트할 수 없던 항목들이다. 모두 **graceful degrade**하도록
설계했다.

1. **Stop block cap.** 조사상 "연속 차단 N회 후 강제 종료"(`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`).
   parallax는 30라운드를 도는데 메인 세션 Stop의 cap이 같은지, 라운드 사이 실제 작업이 카운터를
   리셋하는지 미확정. 30라운드가 잘리면 그때 설정한다. **parallax가 같은 Stop 훅 위에서 30라운드를
   돌았다는 점이 강한 전례다.**
2. **트랜스크립트 형식 가정.** `parse_round_actions`가 "마지막 훅 주입 이후"를 라운드 action으로 잡고,
   `extract_advisor_output`이 `Agent(advisor)` tool_result에서 advisor 반환을 읽는다 — 둘 다 트랜스크립트
   메시지·블록 형식에 의존한다. 어긋나면 action 범위가 넓어지거나 region 기록이 누락될 수 있다(graceful,
   치명적이지 않음).
3. **main의 지시 순응도** — stderr "advisor 호출"에 main이 실제로 응하는가. round 안전망이 미응답 시에도
   종료를 보장한다. **parallax 전체 설계가 메인 에이전트의 stderr 순응 위에 섰고 작동했고, 고지능 모델
   가정상 순응은 전제된다 — 강한 전례.**
4. **PreToolUse 발동·session 일치** — 자발 호출 게이팅은 PreToolUse가 main의 Agent 호출에 발동하고 그
   session_id가 Stop과 같아야 성립한다. 미발동 시 게이팅만 무효화되고 루프는 현행대로(graceful).

초기 nested(operator) 버전의 리스크였던 **subagent 내부 `PostCompact` 발화 여부**와 **background-operator의
nested 동기 호출 honor**는 main 승격으로 **소멸**했다 — 메인 세션은 `PostCompact`가 확실히 발화하고,
foreground라 동기 호출이 보장된다.

---

## 언어와 프롬프트

모든 프롬프트는 **단일 "한국어 기반, 영어 활용"**으로 통일한다(이중 언어 쌍 없음). 식별자·경로·도구
이름과 `main agent` 같은 역할 명칭은 영어, 산문은 한국어, ASCII 다이어그램은 정렬을 위해 영어.
에이전트·스킬 프롬프트와 advisor instruction은 단일 `.md`이고, 훅 주입 메시지(advisor trigger)는
`prompt.py`가 조립한다. 프롬프트는 parallax 원본(`role`·`conversion`·`instruction`)을 충실히 이식하며,
분석 대상을 원본과 같은 "main agent"로 부른다.

---

## 파일 맵

```
ploop/
├── .claude-plugin/plugin.json        # manifest
├── agents/                           # 2개 tier 정의 (frontmatter 봉인 + 프롬프트 본문)
│   ├── advisor.md                    # parallax role 이식 + 5-section 순서 지침 (Write 없음)
│   └── narrator.md                   # parallax conversion 이식
├── prompts/instruction.md            # advisor 분석·출력 지침 (parallax instruction 이식)
├── skills/launch/SKILL.md            # /ploop:launch — 미션 핸드오프 + main 직접 수행 + self-anchoring
├── hooks/hooks.json                  # UserPromptSubmit + PostCompact + PreToolUse(Agent) + Stop + SubagentStop + SessionStart
├── bin/ploop-hook                    # uv 가용성 체크 래퍼 (parallax 상속)
├── src/                              # 훅 구현 (런타임 의존성: pydantic)
│   ├── main.py                       # 훅 엔트리포인트(stop·pre_tool_use·subagent_stop·user_prompt_submit·mark_compaction) + launch CLI(mission_path·activate)
│   ├── state.py                      # 상태 조립 + 영속화 (active 게이트 · round/regions/done)
│   ├── transcript.py                 # action 추출(advisor 호출 strip) + advisor 출력 추출(meta strip)
│   ├── prompt.py                     # region-history 포맷 + 5-section advisor trigger 조립
│   └── updater.py                    # SessionStart 업데이트 알림 (parallax 이식)
└── tests/                            # 구현 독립 (stdin/stdout/disk 구동)
```
