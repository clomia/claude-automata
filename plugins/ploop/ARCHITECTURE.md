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
narrator  depth 2  Read Write  narrate          round slice file -> narration.md
```

| Tier | 도구 (allowlist) | 모델 | effort |
|---|---|---|---|
| **main** | 전체 (세션) | `opus[1m]` 권장 | inherit |
| **advisor** | 전체 − `Bash·Edit·NotebookEdit·Artifact` (`Write`는 advice 출력용) | `opus[1m]` | max |
| **narrator** | `Read` · `Write` (narration 출력용) | `sonnet[1m]` | medium |

- **advisor는 `Write`로 advice(또는 종료 토큰)만 파일에 쓰고, 나머지 부작용 도구는 막혀 있다(`disallowedTools: Bash, Edit, NotebookEdit, Artifact`)** —
  subagent의 최종 메시지는 커스터마이징 불가라 max-effort 추론 prose가 섞인다(하네스 한계). 그래서 advice를
  `advice.md`(비보호 시스템 temp — `CLAUDE_PLUGIN_DATA`는 보호된 `~/.claude` 하위라 auto 모드 Write가 classifier에 막힌다)에 Write해 채팅 채널의 오염과 격리한다 — hook은 그 파일을 읽는다. `Bash`를 막는 것은
  임의 부작용(`rm`·테스트 실행 등) 차단 취지고, `Write`만 좁게 열어 advice 출력 채널로 삼은 의식적 완화다(사용 전제는 auto/bypass
  권한 모드). 남은 read-only 도구(`Read·Glob·Grep·Web*`)로 영역을 근거 짓고 `Agent`로 narrator를 호출하며,
  advice를 ledger에 기록하는 것은 여전히 hook의 몫이다.
- **narrator는 `Read`·`Write`만 가진 leaf** — `Agent`가 없어 트리가 그 아래로 자라지 않는다. `Read`로
  hook이 라운드 슬라이스를 잘라 준 파일(`round.jsonl`)을 통째로 읽어 해석한다(hook 측 메시지 파싱 없음).
  `Write`는 advisor와 동일한 채널이다: narration을 temp `narration.md`에 쓰고, advisor가 분석 입력으로·hook이
  라운드 로그로 같은 파일을 읽는다. 원본 슬라이스를 스스로 해석해야 하므로 `sonnet[1m]`/`medium`이다.
- depth 2에서 트리를 닫아 depth-5 cap에 3단계 여유를 남긴다.
- **waiter는 이 loop 트리 밖의 main-side leaf**(`Bash`만·`sonnet`/`high`) — main이 background 대기를 위임하는
  별개 서브에이전트라 위 트리·표엔 없다(main→waiter, depth 1; 결정 17).

---

## 핵심 루프

```
main round N work ── stops
   |
   |  <-- Stop hook
   |        leftover token (trigger unanswered) -> re-arm with authority notice
   |          (refusal reasons ride the round's transcript slice to the verdict)
   |          2nd consecutive decline -> failsafe: done + deactivate
   |        record last advisor verdict from advice.md (parallax's rule):
   |          absent/empty file -> malfunction: re-arm same round, inputs frozen
   |            2nd consecutive failure -> done + deactivate
   |          advice -> log completed round (narration + the advice it answered)
   |          termination token -> done + deactivate
   |            -> exit 2: "summarize {session}_loop.log" (if any advice surfaced)
   |          else append advice   (no round cap; /ploop:stop also deactivates)
   |        then:  cut transcript [round_start..end] -> {session}_round.jsonl
   |               next round_start = transcript line count + 1
   |               write {session}_advice_history.md (advice-history XML)
   |               round++,  exit 2 + stderr: advisor trigger — narrator
   |                 analyzes the whole round.jsonl (+ mission text if compacted)
   v
main ─ Agent(advisor) ───────────> advisor (depth 1)
   |                                  ├ read original-mission   ({session}_mission.md)
   |                                  ├ Agent(narrator) -> reads round.jsonl slice -> narration.md -> read it
   |                                  ├ read advice-history ({session}_advice_history.md)
   |                                  ├ read instructions, then analyze
   |                                  └ Write advice / termination token to advice.md
   |  <── advice (uncovered-region list) ─┘
   v
main ─ work on the advice (round N+1) ── stops ── (loop)
```

종료는 의미론적 판단만 인정한다: advisor가 `advice.md`에 **전용 종료 토큰을 Write할 때만** 수렴 종료다
(`TERMINATION_TOKEN in advice` → `done` 플래그 + active 마커 정리). 파일 부재/빈 파일은 종료가 아니라
**오작동**이다 — 규약상 정상 advisor는 종료조차 토큰 Write로 표현하므로, 안 쓴 것은 판정이 아니다. 이때
라운드를 입력 동결 상태로(같은 round·round_start_line·advice_history.md) 재시도하고, **연속 2회** 실패하면
오작동 사유로 종료한다(수렴으로 위장하지 않는다 — 핵심 설계 결정 14). 트리거가 응답되지 않은
정지(토큰 잔존 — main의 거부, 또는 사용자가 끊은 턴)는 **권한 분할**로 처리한다: 1회는 "루프 종료
권한은 advisor에게만 있다"를 고지하며 재주입한다 — 거부의 근거 발언은 라운드 트랜스크립트 슬라이스→narrator를 타고
advisor에게 닿으므로, 타당한 거부는 advisor의
종료 토큰으로 관철된다(main-advisor 합의 경로). 연속 2회면 합의 채널 자체가 붕괴된 것으로 보고 failsafe로
종료한다 — 노티스는 이를 광고하지 않는다(main-side 출구가 아니다). **숫자 라운드 상한은 두지 않는다** — advice-history는 파일이라 컨텍스트를 잠식하지
않고 advisor는 매 라운드 stateless하게 리셋되므로, 종료는 "더 제공할 advice가 있는가"라는 의미론적
판단(advisor 종료 토큰)에 맡긴다. 그 판단이 안 나오면 사용자가 `/ploop:stop`으로 언제든 끝낸다(아래
Hooks) — 이 둘이 종료 신호의 전부다. ESC는 턴만 끊을 뿐 armed 루프는 다음 정지에서 재개되므로,
실행 중인 미션의 중단 절차는 ESC 후 `/ploop:stop`이다(결정 15).
**모든 종료 경로는 main에게 정직한 사유와 함께 종료 노티스를 보낸다**
(`format_end_notice`) — 노티스는 종료 사실과 사유를 사용자에게 명확히 보고하게 하고, advice를 하나라도
surface한 턴이면 `loop.log` recap 지시를 덧붙인다 — 장기 미션에서 main 컨텍스트는 여러 번 auto-compaction되므로
로그가 턴의 유일한 완전 기록이다. 자연 종료는 종료 정지를 한 번 더 막아(exit 2) 노티스를 주입하고, 그 다음
정지는 active 마커가 없어 통과한다.

Stop 훅은 메인 세션 정지마다 발화하므로 active 마커가 게이트한다(아래 상태). advisor·narrator의
정지는 `SubagentStop`이라 이 Stop 훅에 잡히지 않는다 — 재귀 가드가 필요 없다.

---

## 컨텍스트 경제 — nested가 `claude -p`보다 우월한 지점

main의 컨텍스트에 더해지는 것은 **① 짧은 stderr 트리거 + ② main이 트리거 지시로 읽는
`advice.md`의 advice + ③ 종료 시 1회의 로그 요약 턴**뿐이다. narrator 호출, 라운드 트랜스크립트 슬라이스
읽기, advice-history 누적 읽기, 5-section 분석은 모두 **advisor·narrator(depth 1·2)의 컨텍스트에서**
소비되어 main에 닿지 않는다. 라운드 슬라이스가 커도(대량 작업 라운드) 그 읽기 비용은 depth-2 narrator에
격리되며 — main은 그 슬라이스를 보지 않는다 — 요약된 narration만 위로 흐른다. 영역을 "짧고 명확하게
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
| `{session}_loop.json` | hook | `round` · `advice_history` · `done` · `advisor_failures`/`declines` (연속 이상 카운터, 정상 라운드에 0으로 리셋) · `round_start_line` (이번 라운드가 시작되는 트랜스크립트 라인 — 슬라이스 컷의 시작 오프셋) |
| `{session}_round.jsonl` | hook | 이번 라운드의 트랜스크립트 슬라이스 `[round_start..end]` (narrator가 통째로 분석) — 라인 컷이라 메시지 파싱 없음 |
| `{session}_advice_history.md` | hook | advisor 입력의 advice-history (XML) |
| `advice.md` (temp) | advisor (`Write`) | advice 또는 종료 토큰 (유일 채널) — 비보호 temp라 auto 모드 Write 승인 · main·hook이 읽음 · prose 격리 |
| `narration.md` (temp) | narrator (`Write`) | action-history 서사 (advice와 동일 채널) — narrator가 라운드 트랜스크립트 슬라이스를 읽어 작성 · advisor가 분석 입력으로 · hook이 라운드 로그로 읽음 |
| `{session}_loop.log` | hook | 완결 라운드 로그 (서사 + 그 라운드의 advice) — 미션 전체 흐름의 완전 기록 · launch가 `[[ MISSION ]]` 원문으로 새로 시작 · 종료 요약의 소스 |
| `{session}_advisor_token` | hook | advisor 1회 호출 인가 토큰 (Stop set · PreToolUse 소비) |
| `{session}_advisor_running` | hook | advisor in-flight 마커 (PreToolUse set · 루프 사이클 내 clearer는 SubagentStop뿐 — launch 리셋·`/ploop:stop`의 teardown은 예외 · Stop이 존재로 in-flight 판정) |
| `{session}_compacted` | hook (PostCompact) | compaction 발생 마커 (Stop이 메커니즘 2로 소비) |

**loop 상태(round·advice_history·done)는 hook이 단독 소유한다.** advisor는 분석 후 advice를
`advice.md`에 Write(종료 시엔 같은 파일에 종료 토큰을 Write)할 뿐 loop ledger는 건드리지 않는다. hook이 다음
라운드 시작에 직전 advisor의 `advice.md`를 읽어 `advice_history`에 append하거나, 종료 토큰이면 `done`을 세운다 —
advice-history의 한 블록은 한 라운드의 advice 전문이다(action-history 요약 포함, 위 용어의 history 무결성).
in-flight 가드(`advisor_running` 마커)를 통과한 시점이라 advisor는 이미 종료했으므로, `advice.md`가 없으면
아무것도 안 쓴 것 = 오작동이다(규약상 종료도 토큰 Write를 요구) — 라운드를 재시도하고 연속 2회면 오작동
사유로 종료한다(핵심 설계 결정 14). main도 트리거 지시대로 같은 `advice.md`를
읽어 그 조언에 따라 작업하므로 `advice.md`는 advice/종료의 유일 채널이자 main·hook 양쪽의 깨끗한 단일 소스다. `round`도 hook이 증가시키는 안전망이다.
단일 작성자(hook)가 ledger를 소유해 race가 없고, advisor는 자기 advice payload만 파일로 넘긴다.
(`mission.md`·`active` 마커는 활성화 신호라 launch 훅(UserPromptExpansion)이 만든다.)

**활성화 lifecycle.** Stop 훅은 메인 세션 정지마다 발화하므로 active 마커가 루프를 게이트한다.

1. `/ploop:launch`의 UserPromptExpansion 훅이 직전 미션의 라운드 상태를 리셋하고
   `mission.md`·`active` 마커를 쓴다. main이 미션을 직접 수행하기 시작한다.
   `active`가 이미 있거나(중복 launch — 진행 중인 미션의 기록을 덮어쓰고 in-flight advisor를 고아로
   만든다) 미션이 비어 있으면(스킬 본문이 arm되지 않은 활성화를 알리는 유령 루프) 확장을
   **차단**한다(`decision: block`) — 턴이 지워져 스킬 본문이 컨텍스트에 들어가지 않고, 사유는
   사용자에게만 보이며, 차단 경로는 상태를 건드리지 않아 돌던 루프가 무사하다.
2. **프롬프트 제출은 ploop에게 무이벤트다** — 프롬프트 경로에 훅이 없다(결정 15). 타이핑된 사용자
   턴·AskUserQuestion 응답·task-notification·scheduled wakeup 어느 것도 루프 상태를 건드리지 않고,
   ESC도 턴만 끊는다(interrupt에는 어떤 훅도 발화하지 않는다). armed 루프는 다음 정지의 Stop
   훅에서 재개된다 — 끊긴 라운드의 미소비 토큰은 decline 경로(결정 14)가 한 정지 안에 자연
   회복시킨다. 실행 중인 미션의 공식 중단 절차는 (턴이 돌고 있으면 ESC로 끊고) `/ploop:stop`이다.
3. Stop 훅이 종료(advisor 종료 판정) 시 `active` 마커를 지운다.
4. `/ploop:stop`의 UserPromptExpansion 훅(`stop_command`)이 사용자 요청으로 언제든 루프를
   비활성화한다 — `active`와 라운드 상태를 지운다. background advisor in-flight 중에도 무조건
   멈추도록 `advisor_running`도 함께 지운다(확정 종료). 그리고 자연 종료와 같은 종료 노티스(사유:
   사용자의 stop)에 라운드 로그 recap 지시를 실어 **additionalContext**로 main에 건넨다 — 세션별
   실제 로그 경로를 담을 수 있는 유일한 채널이다(정적 스킬 본문은 못 담는다). `active`가
   없으면(미실행·자연 종료 후·중복 stop) launch 가드와 같은 방식으로 확장을 차단해, 스킬 본문이
   일어나지 않은 종료를 알리는 것을 막는다.

(operator subagent 시절에는 SubagentStop이 미션 전용 subagent에만 발화해 이 게이트가
불필요했으나, main 승격으로 Stop이 일반 대화에도 발화하면서 활성화 게이트가 필요해졌다 — git history.)

**미션 정박은 세 겹이다.** 셋 다 미션 *텍스트*의 보존·주입이다 — "흐려지면 mission.md를 다시
읽어라"류 포인터는 어디에도 두지 않는다. 포인터는 agent가 드리프트를 자각해 읽기로 선택해야
작동하는데, goal drift는 점진적이라 자가감지되지 않는다.

1. **외부 보존(메커니즘 1)** — launch 훅이 original-mission을 `mission.md`에 기록한다. 트랜스크립트와
   독립이라 main 내부가 어떻게 compaction되든 원본은 보존된다. advisor가 매 라운드 이 파일을 읽고,
   메커니즘 2가 이 파일을 재주입 소스로 쓴다.
2. **launch 스킬 본문 re-inject** — `/ploop:launch` 스킬 본문은 루프 notice와 `<MISSION>` 원문을
   담고, 호출된 스킬 본문은 auto-compact 후에도 re-inject되므로(스킬당 앞 5,000토큰·합산
   25,000토큰 예산) 미션 핸드오프 텍스트가 main 컨텍스트에 남는다(메인 세션은 커스텀 시스템
   프롬프트를 못 받지만 스킬 re-inject가 그 자리를 메운다 — 초기 operator subagent 시스템 프롬프트의 역할).
3. **메커니즘 2(PostCompact + 미션 텍스트 inline)** — `PostCompact` 훅이 `_compacted` 마커를
   touch하고, 다음 Stop이 그 마커를 소비하며 **그 라운드 트리거에 original-mission 원문 텍스트를
   recency 위치에 inline**한다(`format_advisor_trigger`의 `mission_text`). re-inject(2)는 5,000토큰
   cap에 잘리고 oldest-first 퇴출로 유실될 수 있으며 원래 깊이에 남는 반면, 이것은 discrete한
   compaction 이벤트마다 **미션 전문을 무조건 recency에** 박는다. 메인 세션은 `PostCompact`가
   확실히 발화하므로(초기 nested 버전의 미확정 리스크가 해소됨) 이 복원이 가능하다.

---

## Hooks

| Hook | Matcher | 시점 | 동작 |
|---|---|---|---|
| **UserPromptExpansion** | `ploop:launch` · `ploop:stop` | 슬래시 커맨드 확장(제출 전) | launch: 라운드 상태 리셋 + 미션·`active` 기록(활성화) — `active` 존재·빈 미션이면 차단 · stop: `active`+라운드 상태 삭제(비활성화, in-flight 무관) — 비활성이면 차단 |
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
   본질이다. 자발 호출 — hook이 작성한 5-section 입력 대신 main 자기 의견이 advisor로 가고
   narrator가 건너뛰어지는 경로 이탈 — 은 숨김이 아니라 명시와 게이팅으로 막는다: launch 스킬이
   "advisor는 시스템이 invoke 구문을 제시할 때만 invoke할 수 있다"를 규칙으로 고지하고,
   PreToolUse 토큰 게이팅(결정 9)이 이를 결정론적으로 강제한다. (초기엔 main 컨텍스트에서
   advisor라는 단어 자체를 숨겼으나, 규칙 고지 + 게이팅이 대체했다 — git history.)
3. **loop 상태는 hook이 단독 소유.** advisor는 advice(또는 종료 토큰)를 `advice.md`에 Write만 하고,
   hook이 그 파일을 읽어 round·advice_history·done을 모두 기록한다. `advice.md`가 advice/종료의 **유일 채널**이라
   트랜스크립트를 스크레이프하지 않는다 — 단일 작성자라 동시성 문제가 없고, advisor 프롬프트가 순수 분석으로
   남으며, Agent tool_result 형식(메타 엔벨로프·prose)에 대한 의존이 통째로 사라진다.
4. **작업 transcript = 메인 transcript, action-history는 narrator에게 위임(hook 측 메시지 파싱 없음).**
   Stop 훅은 메인 세션 transcript를 직접 건넨다. main이 미션을 직접 수행하므로 action과 advisor
   호출(tool_use/tool_result)이 모두 거기 있다 — operator의 별도 transcript를 `subagents/meta.json`으로
   해소하던 단계가 통째로 사라진다. **hook은 트랜스크립트를 파싱하지 않는다.** 대신 라운드가 시작되는
   **라인 오프셋**(`round_start_line`, ledger 소유)부터 정지 시점 트랜스크립트 끝까지를 순수 라인 컷으로
   잘라 `round.jsonl`에 저장하고, narrator에게 "이 파일 전체를 분석해 main의 작업을 서술하라"를 지시한다.
   슬라이스가 곧 라운드다: 이 정지 시점엔 다음 핸드오프(다음 라운드의 advisor 호출)가 아직 append되지
   않았으므로 `[round_start..end]`가 정확히 이번 라운드다 — hook은 advisor 호출을 찾을 필요조차 없다(라인
   컷만). narrator(지능 에이전트)가 원본 JSONL 레코드를 스스로 해석해 main의 생각·시도·결과를 시간순으로
   서술한다 — 과업이 main의 작업 서술이므로 슬라이스에 함께 담긴 advice·트리거는 main이 반응한 맥락으로만
   들어간다(루프 관여는 숨기지 않는다). **이 위임이 트랜스크립트
   내부 메시지 형식에 대한 hook의 의존을 통째로 없앤다** — `isCompactSummary` 필터·`queued_command`
   승격·라운드 경계 휴리스틱·advisor-strip 코드가 전부 사라졌다(이들은 형식 표류에 취약했다;
   harness-deps 감사). 슬라이스가 `[round_start..end]` 연속 구간이라 라운드 도중의 auto-compaction 요약이나
   사용자 steering·notification이 그 안에 그대로 담기고 — 코드 경계가 없으니 가짜 경계로 인한 잘림이
   구조적으로 불가능하다(실패 방향은 "넓게"). 구 `parse_round_actions`는 string-content 사용자 턴을 경계로
   오인해 라운드를 잘랐다 — 실측: 라이브 미션에서 574개 중 388개 소실, harness-deps 감사가 포착. 사용자
   지시는 미션보다 상위 권위인데 main만 보고 흡수하면 advisor와 main의 목표가 갈라지므로, 슬라이스에 담긴
   steering을 narrator가 그대로 서술해 advisor에 전달한다 — steering은 라운드를 리셋하지 않는다.
5. **활성화 게이트 + 의미론적 종료(숫자 상한 없음).** `/ploop:launch`의 UserPromptExpansion 훅이
   `mission.md`·`active` 마커를 쓰고 main을 미션 모드로 진입시킨다. Stop은 `active`가 있을 때만 루프를 돈다.
   루프는 라운드 상한 없이 **의미론적으로만** 끝난다 — advisor가 종료 판정을 내면 Stop이 `active`를 지우거나,
   사용자가 `/ploop:stop`(UserPromptExpansion `stop_command`)으로 언제든
   비활성화한다(advice-history가 파일이라 컨텍스트를 안 잠식하므로 숫자 캡이 불필요 — `/goal`도 동일 설계).
   ESC는 종료가 아니다 — 턴만 끊고 armed 루프는 다음 정지에서 재개되므로, 사용자 측 종료는
   `/ploop:stop` 하나다(결정 15).
6. **미션 정박 — 메커니즘 1 + 2.** 외부 보존(`mission.md`, 메커니즘 1)으로
   미션 원문은 디스크에 영속하고, `PostCompact`가 `_compacted`를 touch하면 compacted 라운드의
   Stop이 트리거에 미션 원문 텍스트를 inline한다(메커니즘 2 — discrete compaction 이벤트에 무조건
   텍스트 주입). 메인 세션 `PostCompact`는 공식 문서로 보장된다. advisor가 매 라운드 original-mission을
   읽고 미션-grounded advice를 surface하므로 main은 advisor 경유로도 간접 정박된다. launch 스킬 본문
   re-inject는 미션 핸드오프 텍스트를 main 컨텍스트에 보존한다. "매 라운드 포인터"는
   메커니즘 2·advisor·스킬과 중복이라 두지 않는다(irreducible).
7. **advisor 분석 입력은 5-section 순서.** parallax loop의 캐논대로 advisor는
   role·original-mission·action-history·advice-history·instructions 순서로 맥락을 쌓는다
   (advisor.md — 분석 대상은 **"main agent"**로 부른다). hook이 advisor를 직접 못 부르므로 같은
   **순서**를 trigger로 재현한다 — role은 advisor 시스템 프롬프트,
   original-mission·advice-history·instructions는 파일, action-history는 advisor가 트리거에 inline된
   narrator Agent 호출을 실행하고 narrator가 쓴 `narration.md`를 읽어 조립한다. narrator 호출에는
   hook이 잘라 준 라운드 슬라이스 파일 경로(`round`)를 넘겨, narrator가 그 파일 전체를 Read해 서술한다. **트리거는 advisor의 Agent 호출을 — 그 안에 narrator Agent 호출을 inline해 —
   축자로 작성해 넘긴다. hook이 정확한 호출을 작성하고 main·advisor는 그대로 relay한다.** 리터럴
   호출을 그대로 건네는 것이 가장 단순·결정론적이다 — LLM이 구성할 것이 없다. 두 가지 주의점:
   **(a)** action narrative만 런타임 수집이다(narrating은 LLM이라 hook이 못 부른다). **(b)** 정박
   대상은 세션 최초 프롬프트가 아닌 `/ploop:launch` 핸드오프 텍스트(`mission.md`)다 — launch 훅이
   인자를 축자 캡처하므로(모델 전사 단계 없음) mission.md는 핸드오프 원문과 정확히 일치한다.
   action-history와 advice-history의 분리는 narrator의 과업 프레이밍이 지킨다 — narrator는 "main의
   생각·시도·결과"를 서술하므로, 슬라이스에 함께 담긴 advisor advice는 main이 반응한 맥락으로 참조될 뿐
   그 자체가 서술 내용이 되지 않는다(구 hook 측 코드 strip을 대체). main의 루프 관여는 숨기지 않는다 —
   main·advisor 모두 ploop을 인지·활용한다.
8. **단일 모델 `opus[1m]`(main·advisor).** 추론 최대화와 compaction 빈도 감소가 같은 선택으로
   수렴. narrator는 원본 슬라이스를 해석해 서술하므로 `sonnet[1m]`/`medium`이다(`[1m]`은 대형 라운드의 트랜스크립트
   슬라이스 수용). main은 세션 모델이라 사용자가 `opus[1m]`로 실행하길 권장한다.
9. **자발 advisor 호출 차단(PreToolUse 게이팅).** main이 hook 지시 없이 스스로 advisor를 부르면
   결정론적 사이클이 깨진다 — hook이 지정한 5-section 입력 대신 main 자기 말이 입력으로 가고, 그 호출이
   `advice.md`를 엉뚱한 시점에 덮어써 advice 채널을 오염시킨다. Stop이 호출을 지시할 때만 1회용 토큰을
   세우고, PreToolUse(matcher `Agent`)가 advisor 호출을 토큰이 있을 때만 통과시킨다(없으면 deny).
   narrator는 read-only leaf이자 hook 사이클 밖이라 게이팅하지 않는다. stale 토큰이 다음 미션의
   라운드 0 자발 호출을 인가하지 못하는 것은 launch의 라운드 상태 리셋이 보장하고, `/ploop:stop`도
   같은 리셋으로 지운다 — 살아있는 루프의 토큰은 그 밖의 무엇도 건드리지 않는다(armed 라운드는
   프롬프트에 죽지 않는다, 결정 15). (미호출로
   정지하면 — 토큰이 소비되지 않고 남는다 — Stop은 그 라운드의 advice 기록을 건너뛰어 직전 advice가
   중복 기록되지 않게 하고, 미호출 자체는 거부 신호로 처리한다 — 아래 14.)
10. **advisor·narrator 호출은 동기다(`run_in_background=false`).** Agent 툴은 이 빌드에서 기본 async라,
    백그라운드 호출은 advice를 남기지 않고 launch acknowledgement만 돌려준다. main은 **foreground**이고,
    trigger가 advisor·narrator 호출을 모두 `run_in_background=false`로 작성해(narrator는 advisor 프롬프트에
    inline) 동기 실행을 지시하며, 고지능 모델이 이를 따른다. 동기여야 advisor가 정지 전에 `advice.md`를
    남기고(hook이 다음 Stop에 읽는다), narrator narration이 advisor의 분석 입력이 된다. 빈 출력은
    오작동 재시도 규칙(아래 14)이, background 전환은 in-flight 가드(아래 13)가 처리한다.
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
    PreToolUse가 advisor 인가 시 `advisor_running` 마커를 set하고, 루프 사이클 안에서는
    **SubagentStop이 그 마커의 유일한 clearer**다 — launch의 라운드 상태 리셋과 `/ploop:stop`의
    teardown만이 사이클 밖에서 지운다. Stop은 마커가 있으면 in-flight로 보고 재주입하지 않고
    `exit 0`으로 대기한다.
    background로 보낸 advisor의 advice는 유실될 수 있으나 cascade는 확실히 차단된다. **수용한 트레이드오프**: SubagentStop이 누락되면 마커가 leak해
    루프가 멈출 수 있다(복구는 `/ploop:stop` — `active`가 남아 있어 launch는 차단되고, 그 차단 사유가
    stop으로 안내한다). settled 기반 self-heal은 트랜스크립트 형식 의존을
    낳아 제거했다 — advice.md 단일 채널로 전환하며 맞바꾼 단순화다.
14. **이상 신호는 1회 교정 후, 재발 시 정직한 사유로 종료한다(anomaly caps).** 루프의 두
    참여자(advisor·main)는 신뢰할 수 없는 LLM이다 — 발생을 막을 수 없으니 루프가 견디게 설계한다. 이상
    신호마다 1회의 교정 기회를 주고, 2회면 지속 상태로 보고 실제 사유로 종료한다. 각 카운터는 **clean
    라운드(advice가 쓰인 라운드)로만 리셋**되고 상대 이상 신호로는 리셋되지 않는다 — 그래서
    malfunction과 decline이 교대해도 어느 한쪽이 2에 닿아 종료한다(둘이 서로를 리셋해 영영 캡을 피하는
    좀비 루프를 막는다; 실측: 교대 3회째에 종료). (a) advisor가
    advice를 안 쓰면(규약 위반 = 오작동) 라운드를 입력 동결로 재시도하고 2회면 오작동 사유로
    종료(`advisor_failures`). 실측 근거(2026-07): opus 4.8 advisor가 동일 입력에서 시스템 프롬프트 suffix를
    축자 echo하고 3.5초에 end_turn한 확률적 degenerate 출력 — 당시의 empty=terminate 규칙이 이를 수렴으로
    위장해 미션을 조용히 끝냈다. 일회성 샘플링 이상이라 재시도 1회로 사실상 소멸한다. (b) 트리거가
    응답되지 않은 채 멈추면(main의 거부, 또는 사용자가 끊은 턴) ploop의 기저 규칙인 **권한 분할**(루프
    종료 권한 = advisor, 작업 수행 권한 = main)을 고지하며 재주입한다(`declines`). 거부의 근거 발언은 라운드 트랜스크립트 슬라이스→narrator를 타고 advisor에게 닿으므로,
    타당한 거부는 advisor의 종료 판정으로 관철된다 — main이 합리적 종료 근거를 출력하면 advisor가 읽고
    종료하는 합의 경로는 실측됐고, in-band 사용자 종결 지시도 이 경로로 advisor에 닿는다. 실측
    근거(2026-07): main이 in-band 사용자 지시(AskUserQuestion 답변 "작업 종결")를 근거로 호출을 정당하게
    거부 — 당시의 무한 재주입이 하네스 stop-block cap(9회)까지 스테일메이트를 끌다 강제 종료됐고 루프는
    armed 좀비로 남았다. 2연속 거부는 합의 채널 자체의 붕괴라 failsafe로 종료하되, 노티스는 이를
    광고하지 않는다(main-side 출구가 아니다). 미소비 토큰은 거부 외에 사용자가 끊은 턴(ESC)에서도
    남으므로(결정 15), main에게 노출되는 두 문구 — 재주입 노티스와 failsafe 종료 사유 — 는 주체를
    특정하지 않는 중의적 표현을 쓴다. 종료는 항상 실제 사유로 보고된다: 오작동을 수렴으로,
    거부를 고장으로 위장하지 않는다. **수용한 한계**: decline은 라운드를 전진시키며 `round.jsonl`을
    거부 슬라이스로 덮어쓰므로, 그 정지에서 아직 서술되지 않은 **직전 라운드의 narration이 유실**된다
    (advisor는 대신 거부를 본다 — decline의 우선순위는 거부를 종료 판정으로 라우팅하는 것이므로 의도에
    부합). 라운드당 1건의 로그 항목이 어긋날 뿐 advice-history(파일)는 무손실이고, 이는 anomaly 경로에
    국한된다.
15. **종료는 명시적 신호만 — 프롬프트 경로에는 훅 자체가 없다.** 루프는 정확히 두 신호로만 끝난다:
    advisor의 종료 토큰과 `/ploop:stop` — 여기에 결정 14의 이상 신호 failsafe가 더해진다.
    UserPromptSubmit 경로는 타이핑된 사용자 턴 외에 task-notification·scheduled wakeup 같은 시스템
    프롬프트(`promptSource: system`)도 타고, launch 스킬 스스로 background Agent 전개를 권장하므로
    자율 미션일수록 이 경로가 반드시 발화한다 — 프롬프트를 개입으로 취급하면 루프가 자기가 권장한
    패턴에 죽는다. 실측 근거(2026-07): main이 background 에이전트들을 기다리며 턴을 yield하자
    (하네스는 yield 턴에서 Stop의 exit 2 재주입을 무시한다 — armed 토큰은 남고, decline 경로가 다음
    정지에서 자연 회복하므로 Stop 측 대응은 불필요) 6분 뒤 도착한 완료 notification이 당시의 "직접
    사용자 턴 개입 = 종료" 규칙에 걸려 진행 중인 미션을 죽였다. 타이핑된 사용자 턴도 개입이 아니다 —
    사용자는 AskUserQuestion 응답·미드턴 지시로 미션에 *참여*하며, in-band 종결 지시는 결정 14의
    합의 경로로 advisor에 닿는다. ESC 감지도 두지 않는다: interrupt는 훅 이벤트가 없어 트랜스크립트
    sentinel 판독이 필요한데, 그것은 하네스 내부 형식 의존을 하나 더 심는 것이다(한 차례 구현 후
    제거 — git history). ESC는 턴만 끊고 armed 루프는 다음 정지에서 재개되며, 공식 중단 절차는 ESC
    후 `/ploop:stop`이다 — 명시적 단일 kill switch가 형식 휴리스틱보다 견고하다. 이 정책으로
    UserPromptSubmit 훅이 통째로 사라졌고, 그 훅의 cleanup에서 launch 턴의 `active`를 보호하던
    launching sentinel도 함께 사라졌다 — 프롬프트 경로는 ploop과 완전히 분리된다.
16. **advisor는 완전 종결 시점에 소집된다 — 코드가 아닌 스킬 규약으로.** Stop 훅은 포그라운드
    종언만 알 뿐, 백그라운드(shell·agent·workflow·monitor)의 상태를 조회할 공식 수단이
    없다(전용 훅·Stop 입력 필드·CLI 모두 부재 — 2026-07 공식 문서 조사; `TaskCreated`/
    `TaskCompleted` 훅은 TODO 태스크 전용). 훅이 트랜스크립트에서 launch−완료를 재구성하는 안은
    기각했다: 완료 알림 형식이 표류하면 pending이 영원히 안 빠져 루프가 소리 없이 기아한다 — 실패
    방향이 degrade가 아니라 정지다. 대신 그 지식을 원래 가진 주체에게 규약을 부여한다: launch
    스킬이 main에게 "미션이 종료되기 전까지 background만 남은 채 foreground를 비우지 마라"를
    지시한다 — 그 foreground 대기는 결정 17에서 waiter가 흡수한다(스킬 본문은 auto-compaction
    후에도 re-inject된다 — 미션 정박 2와 같은 채널). main과 advisor는 협력 관계고 ploop은 둘을 적절히
    신뢰한다 — 규약 위반의 대가는 미완 라운드의 조기 심사(기능 저하)이지 고장이 아니며, 하네스
    포맷 의존을 하나도 추가하지 않는다. 실측 근거(2026-07): background GPU Job이 도는 미션에서
    같은 지시를 사용자 조향으로 주입해 검증 — 조기 심사가 멈추고 라운드가 작업 완결 단위로
    정렬됐다.
17. **재발행 루프는 waiter 서브에이전트가 흡수한다 — main 컨텍스트 경제.** 결정 16의 포그라운드
    대기는 하네스의 10분 Bash 상한 때문에 재발행을 반복하는데(실측: 3시간 작업 ≈ 18회), 그 기록이
    main의 영속 컨텍스트에 쌓여 compaction을 앞당긴다. `ploop:waiter`가 그 재발행 루프를 일회용
    서브에이전트 컨텍스트에서 소각하고, main에는 "가장 먼저 끝난 작업"당 `Agent` 1쌍만 남긴다 —
    advisor·narrator의 nesting 컨텍스트 경제와 같은 패턴. 동기 호출(`run_in_background=false`)이라
    main 포그라운드를 붙잡는다(동기 블록을 끊는 하네스 상한은 미발견 — 기술 리스크 5). 계약은 **시간
    소유의 분리**다. main의 wait-command는 하네스를 모른 채 조건만 담는다: 원하는 상태까지 무한 블록,
    도달 시 `WAIT-DONE`+근거를 출력하며 종료. 모든 시간 상한은 waiter가 소유한다: 매 실행에 Bash
    `timeout` 파라미터를 최대로 주고, 시간 상한 kill을 "아직 WAIT-DONE 전"으로 읽어 재실행한다
    (DONE→반환 / 시간 상한 kill→재실행 / 그 외 종료→출력 원본과 함께 보고 반환 — 잘못 구성된
    wait-command는 main에게 교정 신호로 돌아간다). kill 인식은 코드가 아닌 waiter(지능)의 의미
    판독이라 메시지 형식 표류에 강하고(결정 4와 같은 원리), 실측에서도 waiter들은 지시 없이 kill을
    3/3회 재실행으로 처리했다(자연 prior와 계약의 일치). main은 waiter에게 **wait-command만** 넘긴다 —
    반환 시점·실행 방식 지시는 유일 반환 조건(DONE)을 오염시킨다. 수용한 한계: WAIT-DONE 미도래와 probe
    자체의 hang이 같은 kill로 보여 구분되지 않는다 — 정체 감지가 필요하면 main이 그것을 WAIT-DONE
    조건에 넣는다(조건 논리는 main 소유). 실측 근거(2026-07, 첫 라이브 미션): 초기의 유한 probe 계약(main이 조각
    데드라인 ≤540s와 하트비트 토큰을 소유)에서 관측된 실패 전부가 main·waiter에 분산된 시간 소유에서
    나왔다 — (a) 조각 토큰(`WAIT-TIMEOUT`)의 종결 함의 오독(깨끗한 조각 종료에서 waiter가 반환),
    (b) main의 시간예산 표류(반환 지시 "~9분 뒤"→조각 확장 D=1500→무한 블록형), (c) waiter의 상한
    회피 backgrounding("완료 알림을 기다린다"며 즉시 반환 — 서브에이전트는 반환 즉시 소멸해 알림을
    받을 수 없다). 시간을 waiter로 응집한 이 계약이 세 실패의 뿌리를 제거한다.
    waiter는 **루프 기계장치 밖**의 main 미션-측 헬퍼다 — advisor 게이트들이 "advisor"
    부분문자열로 자연히 배제하므로(PreToolUse·SubagentStop·strip) 마커도 전용 훅도 필요 없다.
    backgrounding cascade 위험도 없다: waiter를 백그라운드로 보내도 Stop은 advisor를 재주입할 뿐
    또 다른 waiter를 낳지 않아 최악이 조기 라운드 1회(결정 16의 degrade)다 — advisor의 파국적
    cascade(결정 13)와 달라 in-flight 가드가 불필요하다. 실패는 항상 조기 심사로 degrade하지
    정지하지 않는다.

---

## 기술 리스크

설계는 성립하나 라이브 트리 없이 유닛 테스트할 수 없던 항목들이다. 모두 **graceful degrade**하도록
설계했다.

1. **Stop block cap — 확인됨(resolved).** Claude Code는 Stop 훅이 **연속** N회 턴 종료를 막으면 강제
   종료한다(`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, **기본 8**). 바이너리 실측 결과 이 카운터는 **생산적
   작업(tool-use) 턴마다 0으로 리셋**된다(`transition: next_turn` → count 0) — "작업 없이 연속으로 멈추려는"
   무진전 루프만 잡는다. ploop은 매 라운드 advisor 호출·advice 작업(= tool call)을 하므로 카운터가 매번
   리셋되어 이 cap에 걸리지 않는다. main이 트리거를 무시하는 무진전 정지는 ploop 자신의 decline
   failsafe(핵심 설계 결정 14)가 2회에서 무결하게 끝내므로 이 cap에 앞서 처리된다 — cap은 백스톱으로만 남는다(cap
   강제 종료는 턴만 끊고 루프를 armed 좀비로 남기는 것이 실측됐다). 단 advisor가 종료 토큰을 안 내고
   main이 무한히 **일하는** "생산적 무한 루프"는 이 cap도 못 막으므로(작업이 리셋), 그 경우엔 `/ploop:stop`이
   종료 수단이다 — `/goal`도 동일 트레이드오프를 수용한다.
2. **트랜스크립트 형식 가정 — 대부분 해소됨(resolved).** hook은 더 이상 트랜스크립트를 파싱하지
   않는다. 라운드 경계·`isCompactSummary` 필터·`queued_command` 승격·advisor-strip을 하던
   `parse_round_actions`(구 `transcript.py`)를 제거하고, hook은 라운드 라인 구간만 잘라 파일에 저장하며
   narrator가 그 raw 슬라이스를 스스로 해석한다(핵심 설계 결정 4) — 형식 표류에 브리틀 코드가 아닌
   지능이 대응하므로 표류가 곧 고장이 되지 않는다. 남은 의존은 **트랜스크립트가 라인 단위 append-only라
   라인 번호가 안정적**이라는 것 하나로 축소됐다(compaction도 append — 결정 4). 형식 필드가 아니라 파일
   구조이고, 어긋나도 슬라이스 범위가 "넓게"(wider)로 graceful하게 degrade한다. narrator는 hook이 쓴
   슬라이스 파일을 Read할 뿐이고(공식 Read 툴), advice 캡처도 이 의존 밖이다 — advice.md 단일 채널이라
   스크레이프하지 않는다. (구 리스크: `parse_round_actions`가 string-content 사용자 턴을 경계로 오인해
   라운드 narration을 잘랐다 — harness-deps 감사가 라이브 미션에서 실측 포착, 이 리팩터로 소멸.)
3. **main의 지시 순응도 — 반증됨(resolved).** stderr "advisor 호출"에 main이 실제로 응하는가. 초기 실측에선
   매 라운드 순응했으나, 이후 main이 in-band 사용자 지시를 근거로 **정당하게 거부**하는 사건이 관측됐다
   (2026-07). 순응은 더 이상 전제가 아니라 리스크로 취급된다 — 미호출 1회는 권한 고지로 합의 채널에
   재유도되고(타당한 거부는 advisor 판정으로 관철), 2연속이면 failsafe가 루프를 무결하게 닫는다(핵심
   설계 결정 14).
4. **PreToolUse 발동·session 일치** — 자발 호출 게이팅은 PreToolUse가 main의 Agent 호출에 발동하고 그
   session_id가 Stop과 같아야 성립한다. 미발동 시 게이팅만 무효화되고 루프는 현행대로(graceful).
5. **waiter의 동기 Agent 블록 시간 — 상한 미발견(no cap found).** waiter는 main을 동기 `Agent` 호출로
   붙잡는다(결정 17). 2026-07 3중 조사 결과 그 호출을 끊는 메커니즘이 확인되지 않는다: 공식 문서에
   동기 호출의 wall-clock 제한도 `timeout` 파라미터도 없고(서브에이전트 정의엔 `maxTurns`뿐), 유일한
   시간 장치 `CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS`(기본 10분)는 background 전용 stall 타임아웃이다
   (진행 이벤트마다 리셋). 바이너리(v2.1.207) 식별자 전수 grep에도 동기 에이전트용 타이머가 없다.
   실측은 동기 호출 86건 · 최장 27.9분 · 타임아웃 kill 0건(waiter 유휴 대기 25.6분 포함), background
   스팬 최장 95.6분 — **~28분은 상한이 아니라 관측 최댓값**이다. 수 시간 단일 블록의 직접 관측만
   남았고, 끊겨도 safe-degrade한다: waiter 반환 → main이 launch 스킬의 [CRITICAL] "foreground 비우지
   마라" 불변식대로 재호출 → 최악이 결정 16의 조기 심사(정지·오종료 아님).

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
├── agents/                           # 루프 tier(advisor·narrator) + waiter(main-side 대기 헬퍼)
│   ├── advisor.md                    # advisor 역할 + 5-section 읽기 순서 (Write: advice→advice.md)
│   ├── narrator.md                   # 라운드 슬라이스 파일 → action-history 서사 (Read: round.jsonl · Write: narration→narration.md)
│   └── waiter.md                     # 포그라운드 대기 위임 — wait-command 재발행 루프 (Bash · 루프 밖 leaf)
├── prompts/instruction.md            # advisor 분석·출력 지침
├── skills/define-mission/SKILL.md    # /ploop:define-mission — Direction·Boundary 규칙으로 MISSION.md 작성 (루프와 비연결, 수동 핸드오프)
├── skills/launch/SKILL.md            # /ploop:launch — 루프 notice + 대기 규약 + 미션 핸드오프 (미션 저장·활성화는 launch 훅)
├── skills/stop/SKILL.md              # /ploop:stop — 루프 종료 알림 (비활성화는 stop_command 훅)
├── hooks/hooks.json                  # UserPromptExpansion(launch·stop) + PostCompact + PreToolUse(Agent) + Stop + SubagentStop + SessionStart
├── bin/ploop-hook                    # uv 가용성 체크 래퍼
├── src/                              # 훅 구현 (런타임 의존성 없음)
│   ├── main.py                       # 훅 엔트리포인트(stop·pre_tool_use·subagent_stop·mark_compaction·launch·stop_command)
│   ├── state.py                      # Workspace(세션 파일 경로의 단일 창구) + ledger 영속화(round_start_line 포함)
│   ├── prompt.py                     # advice-history 포맷 + 5-section advisor trigger 조립(narrator 슬라이스 파일 경로 포함)
│   └── updater.py                    # SessionStart 업데이트 알림
└── tests/                            # 구현 독립 (stdin/stdout/disk 구동)
```
