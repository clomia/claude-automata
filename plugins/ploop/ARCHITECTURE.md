# ploop — 아키텍처

ploop은 **parallax loop** — 격리된 advisor가 매 라운드 main이 고려하지 못한
영역을 surface해 결과 신뢰도를 극한까지 끌어올리는 자율 루프 —
를 Claude Code의 **nested subagent** 위에서 구현한 플러그인이다. 통합 지점은 Stop
훅이고, 루프의 main 역할은 세션 에이전트 자신이다.

---

## 용어

- **parallax loop** — 훅·advisor·narrator로 매 라운드 advice를 main에 주입하는 자율
  루프. 이 플러그인(`ploop`)이 그것을 구현한다.
- **main** — parallax loop의 main 역할을 하는 세션 에이전트(depth 0). 미션을 직접
  실행하고 매 라운드 advisor를 호출한다.
- **original-mission** — main을 미션에 붙들어 매는 SSoT. 트랜스크립트 바깥 외부
  파일(`{session}_mission.md`)에 보존된다.
- **advice** — advisor가 라운드마다 main에게 건네는 **미고려 영역들의 리스트**.
  action-history 요약을 앞머리에 포함한다 — advisor가 surface한 영역뿐 아니라 main이
  스스로 떠올린 영역까지 advice-history에 남아, 이미 고려된 영역이 재제시되지 않는다
  (history 무결성).

main은 parallax loop와 original-mission 재정박으로 미션에 **붙들어 매인다(anchor)** —
자기 확신으로 표류(drift)하지도, compaction으로 미션을 잃지도 않는다.

---

## 왜 nested subagent인가

이런 루프를 훅이 직접 구동하는 가장 단순한 방법은 Stop 훅 안에서 `claude -p`를
스폰하는 것이다. 그러나 그것은 `--no-session-persistence`로 **별도의 임시 세션**을
생성하는 자동화 패턴이고, Claude Pro/Max 구독 약관상 계정 정지 위험을 부른다(실제
차단 이력 존재) — API 요금제 전용이 된다.

`Agent` 툴 subagent는 **모든 요금제에서 지원되는 정식 기능**이고(메인 세션과 동일
quota 공유), 서브에이전트는 다시 서브에이전트를 spawn할 수 있다(v2.1.172+, depth 5
cap). ploop은 루프를 이 정식 경로 위에서 돈다 — main이 advisor를 `Agent` 툴로
호출하고, advisor가 narrator를 호출한다. (초기 버전은 main 역할을 `operator`
subagent(depth 1)에 두어 트리가 한 단계 깊었으나, operator는 격리 이점을 주지
않으면서 부채만 떠안겨 제거했다 — git history.)

---

## Agent Tree

`main`은 사용자와 대화하는 세션(depth 0)이자 parallax loop의 수행자다. advisor·narrator는
그 아래 봉인된 서브에이전트 tier에서 돈다. 각 tier는 아래로 위임하고 위로는 요약만
반환하므로, 방대한 컨텍스트가 상위로 갈수록 압축된다.

```
main      depth 0  session     full tools    loop main: runs the mission
   |  Agent(advisor)  <- "invoke advisor" injected by Stop hook
   v
advisor   depth 1  Agent ro    advise           analyzes blind spots; writes advice
   |  Agent(narrator)  Grep Glob Web*
   v
narrator  depth 2  Read Write  narrate          action records -> narration.md
```

| Tier | 도구 (allowlist) | 모델 | effort |
|---|---|---|---|
| **main** | 전체 (세션) | `opus[1m]` 권장 | inherit |
| **advisor** | 전체 − `Bash·Edit·NotebookEdit·Artifact` (`Write`는 advice 출력용) | `opus[1m]` | max |
| **narrator** | `Read` · `Write` (narration 출력용) | `sonnet` | low |

- **advisor는 `Write`로 advice(또는 종료 토큰)만 파일에 쓰고, 나머지 부작용 도구는 막혀 있다(`disallowedTools: Bash, Edit, NotebookEdit, Artifact`)** —
  subagent의 최종 메시지는 커스터마이징 불가라 max-effort 추론 prose가 섞인다(하네스 한계). 그래서 advice를
  `advice.md`(비보호 시스템 temp — `CLAUDE_PLUGIN_DATA`는 보호된 `~/.claude` 하위라 auto 모드 Write가 classifier에 막힌다)에 Write해 채팅 채널의 오염과 격리한다 — hook은 그 파일을 읽는다. `Bash`를 막는 것은
  임의 부작용(`rm`·테스트 실행 등) 차단 취지고, `Write`만 좁게 열어 advice 출력 채널로 삼은 의식적 완화다(사용 전제는 auto/bypass
  권한 모드). 남은 read-only 도구(`Read·Glob·Grep·Web*`)로 영역을 근거 짓고 `Agent`로 narrator를 호출하며,
  advice를 ledger에 기록하는 것은 여전히 hook의 몫이다.
- **narrator는 `Read`·`Write`만 가진 leaf** — `Agent`가 없어 트리가 그 아래로 자라지 않는다. `Write`는
  advisor와 동일한 채널이다: narration을 temp `narration.md`에 쓰고, advisor가 분석 입력으로·hook이 라운드
  로그로 같은 파일을 읽는다. 단순 변환이라 `sonnet`/`low`로 충분하다.
- depth 2에서 트리를 닫아 depth-5 cap에 3단계 여유를 남긴다.

---

## 핵심 루프

```
main round N work ── stops
   |
   |  <-- Stop hook
   |        log completed round: narration + the advice it answered
   |        record last advisor verdict from advice.md (parallax's rule):
   |          absent file or termination token -> done + deactivate
   |            -> exit 2: "summarize {session}_loop.log" (if any advice surfaced)
   |          advice -> append   (no round cap; /ploop:stop also deactivates)
   |        else:  parse round actions (advisor calls stripped) -> {session}_action.json
   |               write {session}_advice_history.md (advice-history XML)
   |               round++,  exit 2 + stderr: advisor trigger (+ mission text if compacted)
   v
main ─ Agent(advisor) ───────────> advisor (depth 1)
   |                                  ├ read original-mission   ({session}_mission.md)
   |                                  ├ Agent(narrator) -> narration.md -> read it
   |                                  ├ read advice-history ({session}_advice_history.md)
   |                                  ├ read instructions, then analyze
   |                                  └ Write advice / termination token to advice.md
   |  <── advice (uncovered-region list) ─┘
   v
main ─ work on the advice (round N+1) ── stops ── (loop)
```

종료는 parallax loop의 규칙대로 결정된다: advisor가 `advice.md`에 아무것도 쓰지 않거나 전용 종료 토큰을 쓰면 `done`
플래그가 서고 active 마커가 정리된다(`if not advice or TERMINATION_TOKEN in advice`). **숫자 라운드 상한은 두지
않는다** — advice-history는 파일이라 컨텍스트를 잠식하지 않고 advisor는 매 라운드 stateless하게 리셋되므로,
종료는 "더 제공할 advice가 있는가"라는 의미론적 판단(advisor 종료 토큰)에 맡긴다. 그 판단이 안 나오면
사용자가 `/ploop:stop`으로 언제든 끝낸다(아래 Hooks). **모든 종료 경로는 main에게 종료 노티스를 보낸다**
(`format_end_notice`) — 노티스는 종료 사실과 사유를 사용자에게 명확히 보고하게 하고, advice를 하나라도
surface한 턴이면 `loop.log` recap 지시를 덧붙인다 — 장기 미션에서 main 컨텍스트는 여러 번 auto-compaction되므로
로그가 턴의 유일한 완전 기록이다. 자연 종료는 종료 정지를 한 번 더 막아(exit 2) 노티스를 주입하고, 그 다음
정지는 active 마커가 없어 통과한다. 고지능 모델 advisor가 빈
출력이나 async를 내는 것은 Claude Code 보장 범위 밖이라 별도 대응(stall·미호출 감지)을 두지
않는다 — 루프의 단순 규칙으로 처리한다(고지능 순응 가정).

Stop 훅은 메인 세션 정지마다 발화하므로 active 마커가 게이트한다(아래 상태). advisor·narrator의
정지는 `SubagentStop`이라 이 Stop 훅에 잡히지 않는다 — 재귀 가드가 필요 없다.

---

## 컨텍스트 경제 — nested가 `claude -p`보다 우월한 지점

main의 컨텍스트에 더해지는 것은 **① 짧은 stderr 트리거 + ② main이 트리거 지시로 읽는
`advice.md`의 advice + ③ 종료 시 1회의 로그 요약 턴**뿐이다. narrator 호출, advice-history 누적 읽기,
5-section 분석은 모두 **advisor(depth 1)의 컨텍스트에서** 소비되어 main에 닿지 않는다. 영역을 "짧고 명확하게
정의(irreducible)"하게 하는 instruction이 이 경계를 지킨다. advisor가 main의 사각을 보되, 그 탐색 비용을 main에 전가하지
않는다.

---

## 상태와 미션 보존

상태는 사용자 레포 바깥에 둔다(레포 비오염) — 대부분 `CLAUDE_PLUGIN_DATA`, 단
`advice.md`만 비보호 시스템 temp(아래 근거). 한 세션에 하나의 미션을 가정해 `session_id`로 키잉한다.

| 파일 | 작성자 | 내용 |
|---|---|---|
| `{session}_mission.md` | launch 훅 (UserPromptExpansion) | original-mission 정의 (외부 보존 anchor) |
| `{session}_active` | launch 훅 생성 · hook 삭제 | 활성화 마커 (Stop 게이트) |
| `{session}_loop.json` | hook | `round` · `advice_history` · `done` |
| `{session}_action.json` | hook | 이번 라운드 action 기록 (narrator가 읽음) |
| `{session}_advice_history.md` | hook | advisor 입력의 advice-history (XML) |
| `advice.md` (temp) | advisor (`Write`) | advice 또는 종료 토큰 (유일 채널) — 비보호 temp라 auto 모드 Write 승인 · main·hook이 읽음 · prose 격리 |
| `narration.md` (temp) | narrator (`Write`) | action-history 서사 (advice와 동일 채널) — advisor가 분석 입력으로 · hook이 라운드 로그로 읽음 |
| `{session}_loop.log` | hook | 완결 라운드 로그 (서사 + 그 라운드의 advice) — 미션 전체 흐름의 완전 기록 · launch가 `[[ MISSION ]]` 원문으로 새로 시작 · 종료 요약의 소스 |
| `{session}_advisor_token` | hook | advisor 1회 호출 인가 토큰 (Stop set · PreToolUse 소비) |
| `{session}_advisor_running` | hook | advisor in-flight 마커 (PreToolUse set · SubagentStop이 유일 clearer · Stop·UserPromptSubmit이 존재로 in-flight 판정) |
| `{session}_compacted` | hook (PostCompact) | compaction 발생 마커 (Stop이 메커니즘 2로 소비) |
| `{session}_launching` | launch 훅 | launch 턴 sentinel — 확장이 제출보다 먼저라 UserPromptSubmit이 `active`를 보존하게 함 |

**loop 상태(round·advice_history·done)는 hook이 단독 소유한다.** advisor는 분석 후 advice를
`advice.md`에 Write(종료 시엔 같은 파일에 종료 토큰을 Write)할 뿐 loop ledger는 건드리지 않는다. hook이 다음
라운드 시작에 직전 advisor의 `advice.md`를 읽어 `advice_history`에 append하거나, 종료 토큰이면 `done`을 세운다 —
advice-history의 한 블록은 한 라운드의 advice 전문이다(action-history 요약 포함, 위 용어의 history 무결성).
in-flight 가드(`advisor_running` 마커)를 통과한 시점이라 advisor는 이미 종료했으므로, `advice.md`가 없으면
아무것도 안 쓴 것 = 종료다(parallax loop의 empty=terminate 규칙). main도 트리거 지시대로 같은 `advice.md`를
읽어 그 조언에 따라 작업하므로 `advice.md`는 advice/종료의 유일 채널이자 main·hook 양쪽의 깨끗한 단일 소스다. `round`도 hook이 증가시키는 안전망이다.
단일 작성자(hook)가 ledger를 소유해 race가 없고, advisor는 자기 advice payload만 파일로 넘긴다.
(`mission.md`·`active` 마커는 활성화 신호라 launch 훅(UserPromptExpansion)이 만든다.)

**활성화 lifecycle.** Stop 훅은 메인 세션 정지마다 발화하므로 active 마커가 루프를 게이트한다.

1. `/ploop:launch`의 UserPromptExpansion 훅이 `mission.md`·`active` 마커와 `launching` sentinel을
   쓴다(슬래시 커맨드 턴은 **확장이 제출보다 먼저**다). main이 미션을 직접 수행하기 시작한다.
   `active`가 이미 있거나(중복 launch — 진행 중인 미션의 기록을 덮어쓰고 in-flight advisor를 고아로
   만든다) 미션이 비어 있으면(스킬 본문이 arm되지 않은 활성화를 알리는 유령 루프) 확장을
   **차단**한다(`decision: block`) — 턴이 지워져 스킬 본문이 컨텍스트에 들어가지 않고, 사유는
   사용자에게만 보이며, 차단 경로는 상태를 건드리지 않아 돌던 루프가 무사하다.
2. `UserPromptSubmit`이 매 새 사용자 턴마다 `loop.json`·`advisor_token`·`compacted`·`advice.md`·
   `narration.md`를 지운다(turn-boundary cleanup). `active`도 지우되 **launch 턴에선 `launching` sentinel을 소비하며
   `active`를 보존**한다 — 확장(launch)이 제출보다 먼저라 방금 만든 마커를 자기 cleanup이 지우는 것을
   막는 장치다. 그 외 턴은 `active`도 지우므로 ESC로 끊긴 미션이 조용히 재개되지 않고, stale 토큰이
   다음 미션의 라운드 0 자발 호출을 인가하지도 못한다. `mission.md`는 anchor로 보존된다.
   이 cleanup이 실제로 살아있는 루프를 비활성화할 때는 **additionalContext**로 main에게 종료
   노티스를 보낸다 — 노티스가 종료 사실과 사유를 사용자에게 보고하게 하므로 개입 종료가 조용히
   묻히지 않는다(자연 종료·`/ploop:stop`도 같은 노티스를 보낸다).
3. Stop 훅이 종료(advisor 종료 판정) 시 `active` 마커를 지운다.
4. `/ploop:stop`의 UserPromptExpansion 훅(`stop_command`)이 사용자 요청으로 언제든 루프를
   비활성화한다 — `active`와 라운드 상태를 지운다. background advisor in-flight 중에도 무조건 멈추도록
   `advisor_running`을 UserPromptSubmit이 읽기 전에 지운다(그래서 우연한 turn의 in-flight 보존과 달리
   확정 종료다). 그리고 자연 종료와 같은 종료 노티스(사유: 사용자의 stop)에 라운드 로그 recap 지시를
   실어 **additionalContext**로 main에 건넨다 — 세션별 실제 로그 경로를 담을 수 있는 유일한
   채널이다(정적 스킬 본문은 못 담는다). `active`가 없으면(미실행·자연 종료 후·중복 stop) launch 가드와
   같은 방식으로 확장을 차단해, 스킬 본문이 일어나지 않은 종료를 알리는 것을 막는다.

(operator subagent 시절에는 SubagentStop이 미션 전용 subagent에만 발화해 이 게이트가
불필요했으나, main 승격으로 Stop이 일반 대화에도 발화하면서 활성화 게이트가 필요해졌다 — git history.)

**미션 정박은 네 겹이다.**

1. **외부 보존(메커니즘 1)** — launch 훅이 original-mission을 `mission.md`에 기록한다. 트랜스크립트와
   독립이라 main 내부가 어떻게 compaction되든 원본은 보존된다.
2. **self-anchoring(launch 스킬 본문)** — launch 스킬의 본문이 "mission.md를 닻으로, 흐려지면 다시
   읽으라"고 지시한다. 호출된 스킬 본문은 auto-compact 후에도 re-inject되어(스킬당 앞 5,000토큰·
   합산 25,000토큰 예산) 보존되므로 이 지시는 compaction을 견딘다(메인 세션은 커스텀 시스템
   프롬프트를 못 받지만 스킬 re-inject가 그 자리를 메운다 — 초기 operator subagent 시스템 프롬프트의 역할).
3. **라운드 경계 트리거 재정박** — 매 라운드 Stop 트리거가 recency 위치에 `mission.md` 경로 +
   "흐려졌으면 다시 읽어라"를 박는다.

위 세 겹은 모두 *포인터*다 — "mission.md를 읽어라"라는 지시이지 미션 텍스트 자체가 아니며, agent가
드리프트를 자각해 다시 읽기로 선택해야 작동한다. 그런데 goal drift는 점진적이라 agent가 스스로
감지하지 못한다. 그래서 네 번째 겹이 필요하다.

4. **메커니즘 2(PostCompact + 미션 텍스트 inline)** — `PostCompact` 훅이 `_compacted` 마커를
   touch하고, 다음 Stop이 그 마커를 소비하며 **그 라운드 트리거에 original-mission 원문 텍스트를
   recency 위치에 inline**한다(`format_advisor_trigger`의 `mission_text`). 포인터·자가감지에 의존하는
   1–3과 달리, 이것은 **discrete한 compaction 이벤트에 미션 텍스트 자체를 무조건** 박는다.
   메인 세션은 `PostCompact`가 확실히 발화하므로(초기 nested
   버전의 미확정 리스크가 해소됨) 이 복원이 가능하다.

---

## Hooks

| Hook | Matcher | 시점 | 동작 |
|---|---|---|---|
| **UserPromptExpansion** | `ploop:launch` · `ploop:stop` | 슬래시 커맨드 확장(제출 전) | launch: 미션·`active`·`launching` 기록(활성화) — `active` 존재·빈 미션이면 차단 · stop: `active`+라운드 상태 삭제(비활성화, in-flight 무관) — 비활성이면 차단 |
| **UserPromptSubmit** | (전체) | 새 사용자 턴 | `loop.json`·토큰·running·compacted·advice·narration·`active` 삭제 (turn cleanup). 단 launch 턴엔 `active` 보존(launching sentinel), background advisor in-flight 중엔 전체 보존 · 살아있는 루프를 끄면 main에게 종료 노티스(`additionalContext`) |
| **PostCompact** | `auto` | auto-compaction 후 | `compacted` 마커 touch (Stop이 메커니즘 2로 미션 텍스트 재주입) |
| **PreToolUse** | `Agent` | main이 Agent 호출 | `advisor` 호출이면 1회용 토큰 검사 → 허용(소비 + `advisor_running` 마커 set) 또는 `exit 2` deny(자발 호출 차단) |
| **Stop** | (전체) | main이 종료 시도 | active 게이트 → **in-flight 가드** → 종료 판정 → `exit 2`+stderr(advisor 호출 지시, 종료 시엔 종료 노티스+로그 recap 지시) 또는 `exit 0`(허용) |
| **SubagentStop** | (전체) | subagent 종료 | `advisor` 종료면 `advisor_running` 마커 clear (in-flight 추적) |
| **SessionStart** | `startup\|clear` | 세션 시작 | 신규 릴리스 알림 |

플러그인 에이전트는 `ploop:<agent>`로 scoped 등록되므로, Agent 호출의 subagent_type이
그 scoped 이름을 쓴다. Stop 훅은 본질적으로 메인 세션 정지에만 발화하고 advisor·narrator의
정지는 `SubagentStop`이라, ploop:operator만 잡던 matcher 정규식이 더는 필요 없다. 훅은
`bin/ploop-hook` 셸 래퍼를 거쳐 `uv`를 호출한다 — 래퍼가 uv 가용성을 먼저 확인하므로,
uv 미설치 시 graceful degrade와 SessionStart 안내를 한 지점에서 일원화한다.

**Graceful degradation.** `uv`가 없으면 훅 spawn은 무해하게 실패한다. main은 parallax loop를
모르므로(루프는 전적으로 훅이 구동) advisor 없이 미션만 수행하고 종료한다 — 루프는 돌지 않지만
세션은 깨지지 않으며, SessionStart가 uv 설치를 안내한다.

---

## 핵심 설계 결정

1. **loop main = 세션 메인 에이전트.** parallax loop의 main 역할을 세션 에이전트(depth 0)가
   직접 한다 — 트리거는 Stop 훅이다. advisor·narrator만 nested
   subagent로 격리해 구독 안전성을 얻는다. (초기 버전은 main 역할을 `operator` subagent(depth 1)에
   두어 트리가 4-tier였으나, operator는 어떤 격리 이점도 주지 않으면서 — 미션 작업은 원래 main
   컨텍스트에서 일어난다 — `find_operator_transcript` 해소,
   background-nested 동기 호출, subagent `PostCompact` 불확실성을 떠안겼다. 제거가 순수 이득이다.)
2. **훅은 코드라 툴을 호출할 수 없다 → 훅은 트리거, 실행은 Agent 툴.** Claude Code 훅은
   stdout/stderr/exit code로만 통신하며 tool call을 발화하지 못한다. 그래서 훅이 advisor를
   직접 실행할 수 없다. 대신 Stop이 `exit 2`+stderr로 main에게 advisor 호출을
   **지시**하고, main(LLM)이 Agent 툴로 실행한다. 이 간접 한 단계가 ploop 훅 설계의
   본질이다. main의 컨텍스트(launch 스킬·트리거)는 루프 메커니즘을 advisor라는 단어로
   **언급하지 않는다** — 자발적으로 부르면 경로 대신 자기 의견을 advisor에 전달하거나 narrator를
   건너뛰기 때문이다. advisor의 존재는 stderr 지시가 처음 알린다.
3. **loop 상태는 hook이 단독 소유.** advisor는 advice(또는 종료 토큰)를 `advice.md`에 Write만 하고,
   hook이 그 파일을 읽어 round·advice_history·done을 모두 기록한다. `advice.md`가 advice/종료의 **유일 채널**이라
   트랜스크립트를 스크레이프하지 않는다 — 단일 작성자라 동시성 문제가 없고, advisor 프롬프트가 순수 분석으로
   남으며, Agent tool_result 형식(메타 엔벨로프·prose)에 대한 의존이 통째로 사라진다.
4. **작업 transcript = 메인 transcript.** Stop 훅은 메인 세션 transcript를 직접 건넨다. main이
   미션을 직접 수행하므로 action과 advisor 호출(tool_use/tool_result)이 모두 거기 있다 — operator의
   별도 transcript를 `subagents/meta.json`으로 해소하던 단계가 통째로 사라진다.
5. **활성화 게이트 + 의미론적 종료(숫자 상한 없음).** `/ploop:launch`의 UserPromptExpansion 훅이
   `mission.md`·`active` 마커를 쓰고 main을 미션 모드로 진입시킨다. Stop은 `active`가 있을 때만 루프를 돈다.
   루프는 라운드 상한 없이 **의미론적으로만** 끝난다 — advisor가 종료 판정을 내면 Stop이 `active`를 지우거나,
   사용자가 `/ploop:stop`(UserPromptExpansion `stop_command`)으로 언제든 비활성화한다(advice-history가 파일이라
   컨텍스트를 안 잠식하므로 숫자 캡이 불필요 — `/goal`도 동일 설계). 더해 UserPromptSubmit이 매 사용자 턴
   `active`·`loop.json`을 지우되, **확장이 제출보다 먼저인 launch 턴에선 `launching` sentinel로 `active`를
   보존**한다 — 그 외 턴은 지우므로 ESC로 끊긴 미션이 무단 재개되지 않는다. (`/ploop:stop`은 그 암묵적
   정리와 달리 background advisor in-flight 중에도 확정 종료한다.)
6. **미션 정박 — 메커니즘 1 + 2.** 외부 보존(`mission.md`, 메커니즘 1)으로
   미션 원문은 디스크에 영속하고, `PostCompact`가 `_compacted`를 touch하면 compacted 라운드의
   Stop이 트리거에 미션 원문 텍스트를 inline한다(메커니즘 2 — discrete compaction 이벤트에 무조건
   텍스트 주입). 메인 세션 `PostCompact`는 공식 문서로 보장된다. advisor가 매 라운드 original-mission을
   읽고 미션-grounded advice를 surface하므로 main은 advisor 경유로도 간접 정박된다. launch 스킬 본문의
   self-anchoring은 main이 mission.md를 닻으로 삼게 부트스트랩한다. "매 라운드 포인터"는
   메커니즘 2·advisor·스킬과 중복이라 두지 않는다(irreducible).
7. **advisor 분석 입력은 5-section 순서.** parallax loop의 캐논대로 advisor는
   role·original-mission·action-history·advice-history·instructions 순서로 맥락을 쌓는다
   (advisor.md — 분석 대상은 **"main agent"**로 부른다). hook이 advisor를 직접 못 부르므로 같은
   **순서**를 trigger로 재현한다 — role은 advisor 시스템 프롬프트,
   original-mission·advice-history·instructions는 파일, action-history는 advisor가 트리거에 inline된
   narrator Agent 호출을 실행하고 narrator가 쓴 `narration.md`를 읽어 조립한다. **트리거는
   advisor의 Agent 호출을 — 그 안에 narrator Agent 호출을 inline해 — 축자로 작성해 넘긴다. hook이
   정확한 호출을 작성하고 main·advisor는 그대로 relay한다.** 리터럴 호출을 그대로 건네는 것이
   가장 단순·결정론적이다 — LLM이 구성할 것이 없다. 두 가지 주의점: **(a)** action narrative만
   런타임 수집이다(narrating은 LLM이라 hook이 못 부른다). **(b)** 정박 대상은 세션 최초 프롬프트가
   아닌 `/ploop:launch` 핸드오프 텍스트(`mission.md`)다 — launch 훅이 인자를 축자 캡처하므로(모델
   전사 단계 없음) mission.md는 핸드오프 원문과 정확히 일치한다. action-history는 advisor
   호출을 strip해 advice-history와 분리를 지킨다.
8. **단일 모델 `opus[1m]`(main·advisor).** 추론 최대화와 compaction 빈도 감소가 같은 선택으로
   수렴. narrator만 단순 변환이라 `sonnet`/`low`면 충분하다. main은 세션 모델이라
   사용자가 `opus[1m]`로 실행하길 권장한다.
9. **자발 advisor 호출 차단(PreToolUse 게이팅).** main이 hook 지시 없이 스스로 advisor를 부르면
   결정론적 사이클이 깨진다 — hook이 지정한 5-section 입력 대신 main 자기 말이 입력으로 가고, 그 호출이
   `advice.md`를 엉뚱한 시점에 덮어써 advice 채널을 오염시킨다. Stop이 호출을 지시할 때만 1회용 토큰을
   세우고, PreToolUse(matcher `Agent`)가 advisor 호출을 토큰이 있을 때만 통과시킨다(없으면 deny).
   narrator는 read-only leaf이자 hook 사이클 밖이라 게이팅하지 않는다. UserPromptSubmit이 토큰을
   turn-boundary에서 지워 stale 토큰이 다음 미션의 라운드 0 자발 호출을 인가하지 못하게 한다. (고지능
   모델은 트리거에 순응해 매 라운드 advisor를 호출한다고 가정하나, 만일 미호출로 정지하면 — 토큰이
   소비되지 않고 남는다 — Stop은 그 라운드의 advice 기록을 건너뛰어 직전 advice가 중복 기록되지 않게 한다.)
10. **advisor·narrator 호출은 동기다(`run_in_background=false`).** Agent 툴은 이 빌드에서 기본 async라,
    백그라운드 호출은 advice를 남기지 않고 launch acknowledgement만 돌려준다. main은 **foreground**이고,
    trigger가 advisor·narrator 호출을 모두 `run_in_background=false`로 작성해(narrator는 advisor 프롬프트에
    inline) 동기 실행을 지시하며, 고지능 모델이 이를 따른다. 동기여야 advisor가 정지 전에 `advice.md`를
    남기고(hook이 다음 Stop에 읽는다), narrator narration이 advisor의 분석 입력이 된다. 빈 출력·async처럼
    Claude Code 보장 밖 케이스는 별도 가드 없이 루프의 단순 규칙(빈 출력=종료)으로 처리한다.
11. **로깅: 완결된 라운드 단위 — 서사 + 그 라운드의 advice.** `_loop.log`의 한 엔트리는 라운드 하나의
    완결이다: 라운드 작업의 서사(advice가 도착해 읽히는 장면으로 시작해 반응 작업으로 이어진다) 뒤에 그
    advice 전문이 `/ Advice`로 붙는다(라운드 0은 미션 초기 작업이라 advice 섹션이 없다). 서사가 advice
    요약을 품고 전문이 뒤따르는 중복은 의도된 것이며, advisor도 같은 서사를 분석 입력으로 받아 자신의
    직전 advice에 main이 어떻게 반응했는지 그대로 본다. nested 구조상 라운드 N의 narration은 다음 advisor
    호출에서 생성되므로 엔트리는 한 정지 늦게 완결 기록되고, 번호는 advice ordinal이라 skip 라운드에도
    `advice_history.md`와 어긋나지 않으며, 종료 토큰 같은 기계 신호는 로그에 남지 않는다. 쌍은
    production-pairing(작업→그 작업이 낳은 판정)이 아닌 response-pairing(advice→그에 대한
    반응)이다 — 인과 순서가 파일에서 그대로 읽힌다. 장기 미션에서 main 컨텍스트는 여러 번 auto-compaction
    되므로 이 로그가 턴 전체의 유일한 완전 기록이다. launch가 미션 원문(`[[ MISSION ]]` 헤더)으로 로그를
    새로 시작해 한 미션이 로그 하나를 소유하며 종료 후에도 남고, 종료 시(단 advice를 하나라도 받은 턴)
    마지막 stderr 주입이 main에게 로그를 읽어 사용자에게 전체 라운드를 요약하게 한다 — 요약자는 미션을
    먼저 읽고 라운드를 읽는다. narration이 advisor 컨텍스트에 갇히는 nested 문제는 narrator가
    `narration.md`(advice와 동일한 temp 채널)에 Write해 해소한다 — advisor는 분석 입력으로, hook은 로그로
    같은 파일을 읽는다.
12. **플러그인 영역만, `settings.json` 불간섭.** 활성화는 `/ploop:launch` 핸드오프. 미션 없이는
    아무것도 발화하지 않는다. 프로젝트 CLAUDE.md·rules는 main·advisor·narrator가 모두 상속한다(custom
    subagent 차단 옵션 부재) — main은 코드 작업에 프로젝트 코딩 규칙이 *필요*하므로 이를 수용한다.
    advisor·narrator도 함께 상속받아 약한 오염 여지가 있으나, 차단이 all-or-nothing이라 main의 필요를
    우선한다.
13. **advisor in-flight 가드(background 전환 cascade 차단).** advisor 호출을 `run_in_background=false`로
    지시해도 사용자가 단축키로 실행 중인 advisor를 background로 보낼 수 있다. 그 순간 main 세션 Stop이
    발화하는데, 그대로 재주입하면 advisor가 하나 더 spawn되고 다음 정지에 또 spawn되어 **무한 증식**한다
    (훅 바깥에서 advisor가 도는 nested 구조 고유의 리스크다).
    PreToolUse가 advisor 인가 시 `advisor_running` 마커를 set하고 **SubagentStop이 그 마커의 유일한
    clearer**다. Stop·UserPromptSubmit은 마커가 있으면 in-flight로 보고 재주입/정리를 하지 않는다(Stop은
    `exit 0` 대기, UserPromptSubmit은 loop state 보존). background로 보낸 advisor의 advice는 유실될 수
    있으나 cascade는 확실히 차단된다. **수용한 트레이드오프**: SubagentStop이 누락되면 마커가 leak해
    루프가 멈출 수 있다(복구는 `/ploop:stop` — `active`가 남아 있어 launch는 차단되고, 그 차단 사유가
    stop으로 안내한다). settled 기반 self-heal은 트랜스크립트 형식 의존을
    낳아 제거했다 — advice.md 단일 채널로 전환하며 맞바꾼 단순화다.

---

## 기술 리스크

설계는 성립하나 라이브 트리 없이 유닛 테스트할 수 없던 항목들이다. 모두 **graceful degrade**하도록
설계했다.

1. **Stop block cap — 확인됨(resolved).** Claude Code는 Stop 훅이 **연속** N회 턴 종료를 막으면 강제
   종료한다(`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, **기본 8**). 바이너리 실측 결과 이 카운터는 **생산적
   작업(tool-use) 턴마다 0으로 리셋**된다(`transition: next_turn` → count 0) — "작업 없이 연속으로 멈추려는"
   무진전 루프만 잡는다. ploop은 매 라운드 advisor 호출·advice 작업(= tool call)을 하므로 카운터가 매번
   리셋되어 이 cap에 걸리지 않는다. 숫자 라운드 상한을 제거한 뒤 이 백스톱이 유일한 자동 안전망이다:
   main이 트리거를 무시하고 작업 없이 계속 멈추면 8회에서 하네스가 끝낸다. 단 advisor가 종료 토큰을 안 내고
   main이 무한히 **일하는** "생산적 무한 루프"는 이 cap도 못 막으므로(작업이 리셋), 그 경우엔 `/ploop:stop`이
   종료 수단이다 — `/goal`도 동일 트레이드오프를 수용한다.
2. **트랜스크립트 형식 가정.** `parse_round_actions`가 "마지막 훅 주입 이후"를 라운드 action으로 잡아
   narrator 입력을 만든다 — 트랜스크립트 메시지·블록 형식에 의존한다. 어긋나면 action 범위가 넓어질 수
   있다(graceful, 치명적이지 않음). advice 캡처는 이 의존에서 빠졌다 — advice.md 단일 채널로 전환하며
   `extract_advisor_output` 트랜스크립트 스크레이프를 제거했다(이전 리스크 해소).
3. **main의 지시 순응도** — stderr "advisor 호출"에 main이 실제로 응하는가. round 안전망이 미응답 시에도
   종료를 보장한다. **실측에서 main은 매 라운드 트리거에 순응했고, 고지능 모델 가정상 순응은
   전제된다.**
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
`prompt.py`가 조립한다. 프롬프트는 한국어 원문 단일본만 관리하고, 사람이 읽는 문서(README)는
한·영 쌍으로 관리한다.

---

## 파일 맵

```
ploop/
├── .claude-plugin/plugin.json        # manifest
├── agents/                           # 2개 tier 정의 (frontmatter 봉인 + 프롬프트 본문)
│   ├── advisor.md                    # advisor 역할 + 5-section 읽기 순서 (Write: advice→advice.md)
│   └── narrator.md                   # action-history 서사 변환 (Write: narration→narration.md)
├── prompts/instruction.md            # advisor 분석·출력 지침
├── skills/launch/SKILL.md            # /ploop:launch — main 직접 수행 + self-anchoring (미션 저장·활성화는 launch 훅)
├── skills/stop/SKILL.md              # /ploop:stop — 루프 종료 알림 (비활성화는 stop_command 훅)
├── hooks/hooks.json                  # UserPromptSubmit + UserPromptExpansion(launch·stop) + PostCompact + PreToolUse(Agent) + Stop + SubagentStop + SessionStart
├── bin/ploop-hook                    # uv 가용성 체크 래퍼
├── src/                              # 훅 구현 (런타임 의존성 없음)
│   ├── main.py                       # 훅 엔트리포인트(stop·pre_tool_use·subagent_stop·user_prompt_submit·mark_compaction·launch·stop_command)
│   ├── state.py                      # Workspace(세션 파일 경로의 단일 창구) + ledger 영속화
│   ├── transcript.py                 # action 추출(advisor 호출 strip) — narrator 입력용
│   ├── prompt.py                     # advice-history 포맷 + 5-section advisor trigger 조립
│   └── updater.py                    # SessionStart 업데이트 알림
└── tests/                            # 구현 독립 (stdin/stdout/disk 구동)
```
