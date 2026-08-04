# ploop — architecture

ploop은 **advisor loop** — 격리된 advisor가 매 round main이 고려하지 못한 영역을 surface해
결과 신뢰도를 극한까지 끌어올리는 자율 loop — 를 Claude Code의 **nested subagent** 위에서 구현한
plugin이다. 통합 지점은 Stop hook이고, loop의 main 역할은 session agent 자신이다.

---

## Glossary

- **advisor loop** — hook·advisor·narrator로 매 round advice를 main에 주입하는 자율 loop. 이
  plugin(`ploop`)이 그것을 구현한다.
- **main** — advisor loop의 main 역할을 하는 session agent(depth 0). anchor를 소유하는
  orchestrator로서 작업을 agent에 위임·검증하고 매 round advisor를 호출한다.
- **candidates** — main이 승격 대기 사실·용어 후보를 측정 방법과 함께 축적하는 작업기억
  파일(승격 대기열). 승격 아니면 폐기가 대기열의 존재 이유다.
- **anchor** — main을 anchor에 붙들어 매는 SSoT. transcript 바깥 외부 파일(`{session}_anchor.md`)에
  보존된다.
- **advice** — advisor가 round마다 main에게 건네는 **미고려 영역들의 list**. action-history 요약을
  앞머리에 포함해, main이 스스로 떠올린 영역까지 advice-history에 남아 이미 고려된 영역이 재제시되지
  않는다(history 무결성).
- **docent** — loop 기록을 소유자에게 해설하는 read-only 질의 표면. loop와 별도 session에서 돌며
  loop 기계와 접점이 없다(세 표면 절).

main은 advisor loop와 anchor 재주입으로 anchor에 **정박한다(anchored)** — 자기 확신으로
표류(drift)하지도, compaction으로 anchor를 잃지도 않는다.

---

## 세 표면

ploop의 사용자 대면은 세 표면으로 격리된다. 각 표면은 다른 session에서 돌고, loop 상태의 변이는
loop 표면만 소유한다.

| 표면 | 구성 | loop 상태 |
|---|---|---|
| **define** | define-mission·define-purpose — anchor를 정의하는 사용자 대화 | 접점 없음 — 산출물은 repo의 anchor 초안(수동 핸드오프) |
| **loop** | launch·off·on + hooks + advisor·narrator — 작업 본선 | 단독 소유 (hook이 쓴다) |
| **docent** | docent skill + resolver — launch 이후 사용자 질의 응답 | read-only (hook 0개·쓰기 0개) |

격리의 근거는 두 갈래로 수렴한다. **context 순수성**: launch 후 사용자 개입의 다수는 질의인데,
질의가 loop session에 들어가면 지휘와 Q&A가 섞이고 그 오염이 narration→advisor 입력→loop.log까지
전파된다. 정작 main은 지난 round를 잊으므로(작업기억) 질의의 정답은 main이 아니라 기록에 있다 —
기록의 독자는 hook(log)·advisor(입력)에 이어 docent(질의 응답)가 세 번째다. **보안**: docent
session이 오염되어도 loop로의 쓰기 경로가 존재하지 않는다 — 개입은 인간 전용 경로(loop session
직접 지시·`/ploop:off`)로만 들어간다.

---

## 왜 nested subagent인가

Stop hook 안에서 `claude -p`를 spawn하는 가장 단순한 방법은 `--no-session-persistence`로 **별도의 임시
session**을 만드는 자동화 pattern이라, Claude Pro/Max 구독 약관상 계정 정지 위험을 부른다(실제 차단 이력) —
API 요금제 전용이 된다. 반면 `Agent` tool subagent는 **모든 요금제에서 지원되는 정식 기능**이고(main
session과 quota 공유), subagent가 다시 subagent를 spawn할 수 있다. ploop은
이 정식 경로 위에서 돈다 — main이 advisor를, advisor가 narrator를 `Agent` tool로 호출한다.

**nested subagent는 ploop의 hard requirement이자 harness 의존이다.** nesting은 2.1.172에 도입됐고(공식
CHANGELOG: "Sub-agents can now spawn their own sub-agents (up to 5 levels deep)"), **2.1.217이 이를 기본
차단**했다(CHANGELOG: "Changed subagents to no longer spawn nested subagents by default; set
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` to allow deeper nesting"). Claude Code는 `spawner_depth >= cap`이면
`Agent` tool을 미부여하므로 기본 cap 1에서 depth-1 advisor는 narrator(depth 2)를 못 띄운다. 복원은 그 공식
env var 하나다 — `claude-automata init`이 `.claude/settings.json`의 `env`에
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH="5"`(2.1.172의 원래 cap)를 provision해 기여 machine 전체에 전파하고
(init 소관 — ploop은 settings.json을 건드리지 않는다, 결정 12), `/ploop:launch`의 prerequisite assertion이 그 값
`<5`면(다른 요구와 함께) loop을 arm하지 않고 교정을 안내한다(결정 18). reference 문서(sub-agents.md의 "fixed·not configurable", env-vars.md의 var
부재)는 이 변경을 아직 반영하지 못했고 CHANGELOG가 shipped 동작의 정본이다.

---

## Agent Tree

`main`은 사용자와 대화하는 session(depth 0)이자 advisor loop의 수행자다. advisor·narrator는 그 아래 봉인된
subagent tier에서 돈다. 각 tier는 아래로 위임하고 위로는 요약만 반환하므로, 방대한 context가
상위로 갈수록 압축된다.

```
main      depth 0  session     full tools    loop main: runs the anchor
   |  Agent(advisor)  <- advisor trigger injected by Stop hook
   v
advisor   depth 1  Agent ro    advise           analyzes blind spots; writes advice
   |  Agent(narrator)  Grep Glob Web*
   v
narrator  depth 2  Read Write  narrate          round slice file -> narration.md
```

| Tier | 도구 (allowlist) | model | effort |
|---|---|---|---|
| **main** | 전체 (session) | `opus[1m]` 권장 | inherit |
| **advisor** | 전체 − `Bash·Edit·NotebookEdit·Artifact` (`Write`는 advice 출력용) | `opus[1m]` | max |
| **narrator** | `Read` · `Write` (narration 출력용) | `sonnet[1m]` | medium |

- **advisor는 `Write`로 advice(또는 종료 token)만 쓰고 나머지 부작용 도구는 막혀 있다(`disallowedTools:
  Bash, Edit, NotebookEdit, Artifact`).** subagent의 최종 message는 customizing 불가라 추론 prose가
  섞이므로(harness 한계), advice를 `advice.md`(비보호 system temp — 보호된 `~/.claude` 하위인
  `CLAUDE_PLUGIN_DATA`는 auto mode Write가 classifier에 막힌다)에 Write해 chat channel과 격리한다. `Bash`
  차단은 임의 부작용(`rm`·test 실행) 방지고, `Write`만 좁게 연 것은 advice 출력 channel을 위한 의식적
  완화다(전제: auto/bypass 권한 mode). 남은 read-only 도구(`Read·Glob·Grep·Web*`)로 영역을 근거 짓고
  `Agent`로 narrator를 호출한다.
- **narrator는 `Read`·`Write`만 가진 leaf** — `Agent`가 없어 tree가 그 아래로 자라지 않는다. hook이 잘라
  준 round slice(`round.jsonl`)를 통째로 읽어 해석하고(hook 측 parsing 없음), narration을
  `narration.md`(advisor와 동일 temp channel)에 쓴다 — advisor가 분석 입력으로, hook이 round log로 읽는다.
  원본 slice를 해석하므로 `sonnet[1m]`/`medium`이다.
- depth 2에서 tree를 닫아 provision된 depth-5 cap(§왜 nested subagent)에 3단계 여유를 남긴다.

---

## 핵심 loop

```
main round N work ── stops
   |
   |  <-- Stop hook
   |        leftover token (trigger unanswered) -> re-arm with authority notice
   |          (refusal reasons ride the round's transcript slice to the verdict)
   |          2nd consecutive decline -> failsafe: done + deactivate
   |        record last advisor verdict from advice.md (the loop's rule):
   |          absent/empty file -> malfunction: re-arm same round, inputs frozen
   |            2nd consecutive failure -> done + deactivate
   |          advice -> log completed round (narration + the advice it answered)
   |          termination token -> done + deactivate
   |            -> exit 2: "summarize {session}_loop.log" (if any advice surfaced)
   |          else append advice   (no round cap; /ploop:off pauses, /ploop:on resumes)
   |        then:  cut transcript [round_start..end] -> {session}_round.jsonl
   |               next round_start = transcript line count + 1
   |               write {session}_advice_history.md (advice-history XML)
   |               round++,  exit 2 + stderr: advisor trigger — narrator
   |                 analyzes the whole round.jsonl (+ anchor text if compacted)
   v
main ─ Agent(advisor) ───────────> advisor (depth 1)
   |                                  ├ read anchor ({session}_anchor.md)
   |                                  ├ Agent(narrator) -> reads round.jsonl slice -> narration.md -> read it
   |                                  ├ read advice-history ({session}_advice_history.md)
   |                                  ├ read instructions, then analyze
   |                                  └ Write advice / termination token to advice.md
   |  <── advice (uncovered-region list) ─┘
   v
main ─ work on the advice (round N+1) ── stops ── (loop)
```

종료는 의미론적 판단만 인정한다: advisor가 `advice.md`에 **종료 token을 Write할 때만** 수렴
종료다(`phase`→`converged` + `active` 정리). 파일 부재/빈 파일은 종료가 아니라 **오작동**이다 — 정상
advisor는 종료조차 token Write로 표현하므로 안 쓴 것은 판정이 아니다(입력 동결로 재시도). trigger가
응답되지 않은 정지(token 잔존 — main의 거부 또는 사용자가 끊은 turn)는 **권한 분할**로 처리한다: "loop 종료
권한은 advisor에게만 있다"를 고지하며 재주입하면, 거부의 근거 발언이 round slice→narrator를 타고
advisor에 닿아 타당한 거부는 advisor 종료 token으로 관철된다(합의 경로). 오작동·거부 모두 **연속 2회**면
정직한 사유로 종료한다(anomaly cap — 결정 14). **숫자 round 상한은 없다** — advice-history는 파일이라
context를 차지하지 않고 advisor는 매 round stateless하게 reset되므로, 종료는 "더 제공할 advice가
있는가"라는 의미론적 판단에 맡긴다.

**모든 자동 종료 경로(advisor 종료 token + malfunction·decline failsafe)는 main에게 정직한 사유와 함께
종료 notice를 보낸다**(`format_end_notice`) — advice를 하나라도 surface한 turn이면 `loop.log` recap 지시를
덧붙인다.
자연 종료는 종료 정지를 한 번 더 막아(exit 2) notice를 주입하고, 그 다음 정지는 `active`가 없어
통과한다. **이 자동 종료 동작은 노출 계약이라 불변이다.** 끝내기와 별개로 사용자는 `/ploop:off`로
일시정지·`/ploop:on`으로 재개하며(아래 활성화 lifecycle), off는 종료가 아니라 종료 notice를 보내지
않는다.

Stop hook은 main session 정지마다 fire하므로 `active` marker가 gate한다. advisor·narrator의 정지는
`SubagentStop`이라 이 Stop hook에 잡히지 않는다 — 재귀 guard가 필요 없다.

---

## context 경제 — nested가 `claude -p`보다 우월한 지점

main의 context에 더해지는 것은 **① 짧은 stderr trigger + ② main이 읽는 `advice.md` + ③ 종료 시 1회의
log 요약 turn**뿐이다. narrator 호출, round slice·advice-history 읽기, 5-section 분석은 모두
**advisor·narrator(depth 1·2)의 context에서** 소비돼 main에 닿지 않는다 — slice가 커도(대량 작업
round) 그 비용은 depth-2 narrator에 격리되고 요약된 narration만 위로 흐른다. 영역을 "짧고 명확하게
정의(irreducible)"하게 하는 instruction이 이 경계를 지킨다. advisor가 main의 사각을 보되 그 탐색 비용을
main에 전가하지 않는다.

---

## 상태와 anchor 보존

상태는 사용자 repo 바깥에 둔다(repo 비오염) — 대부분 `CLAUDE_PLUGIN_DATA`, advice·narration·candidates 셋만 비보호
system temp(위 근거). 한 session에 하나의 anchor를 가정해 `session_id`로 keying한다.

| 파일 | 작성자 | 내용 |
|---|---|---|
| `{session}_anchor.md` | launch hook (UserPromptExpansion) | anchor 정의 (외부 보존 anchor) |
| `{session}_active` | launch hook 생성 · hook 삭제 | 활성화 marker (Stop gate) |
| `{session}_loop.json` | hook | 4field — `advice_history`(round 기록, 길이=round ordinal) · `round_start_line`(slice cut offset) · `anomalies`(연속 이상 counter, clean round에 0 reset) · `phase`(`fresh` 갓 launch/resume·record 스킵 → `advising` round 진행·record → `converged` 수렴 완료·`/ploop:on` 거부). `{**ledger, ...}` 병합이라 미언급 field 보존(preserve-by-default) |
| `{session}_round.jsonl` | hook | 이번 round transcript slice `[round_start..end]` (narrator가 통째로 분석) — line cut이라 message parsing 없음 |
| `{session}_advice_history.md` | hook | advisor 입력의 advice-history (XML) |
| `advice.md` (temp) | advisor (`Write`) | advice 또는 종료 token (유일 channel) — 비보호 temp라 auto mode Write 승인 · main·hook이 읽음 · prose 격리 |
| `narration.md` (temp) | narrator (`Write`) | action-history 서사 (advice와 동일 channel) — advisor가 분석 입력으로 · hook이 round log로 읽음 |
| `candidates.md` (temp) | main | 승격 대기열 (자유 형식) — trigger가 경로를 상시 안내 · 비어있지 않으면 advisor 입력에 조건부 1행 · launch만 지움(off·on·종료는 보존) · 종료 notice가 잔량 drain을 지시 |
| `{session}_loop.log` | hook | 완결 round log (서사 + 그 round의 advice) · launch가 `[[ ANCHOR ]]` 원문으로 새로 시작 · 종료 요약의 소스 |
| `{session}_advisor_token` | hook | advisor 1회 호출 인가 token (Stop set · PreToolUse 소비) |
| `{session}_advisor_running` | hook | advisor in-flight marker (PreToolUse set · SubagentStop clear) |
| `{session}_compacted` | hook (PostCompact) | compaction 발생 marker (Stop이 mechanism 2로 소비) |
| `{session}_heartbeat_nonce` | hook (heartbeat) | 마지막 armed stop의 heartbeat nonce — fire 시점에 이 값과 다르면 timer가 자멸(더 새 stop이 감시를 소유), 같으면 3h 침묵이므로 wake (launch가 지움) |

**loop 상태(advice_history·phase·anomalies·round_start_line)는 hook이 단독 소유한다.** advisor는
advice(또는 종료 token)를 `advice.md`에 Write만 하고, hook이 다음 round 시작에 그 파일을 읽어
`advice_history`에 append하거나 종료 token이면 `phase`를 `converged`로 옮긴다. in-flight guard를 통과한
시점이라 advisor는 이미 종료했으므로 `advice.md` 부재 = 오작동이다(종료도 token Write를 요구). main도 같은
`advice.md`를 읽어 그 advice로 작업하므로 이 파일이 advice/종료의 유일 channel이자 main·hook 공통 소스다 —
단일 작성자(hook)가 ledger를 소유해 race가 없다.

**활성화 lifecycle.** `active` marker가 loop를 gate한다.

1. **`/ploop:launch`** (UserPromptExpansion) — 직전 anchor의 round 상태를 reset하고 `anchor.md`·`active`를
   쓴다. main이 anchor의 지휘(위임·검증)를 시작한다. `active`가 이미 있거나(중복 launch — 진행 중인 anchor를
   덮어쓰고 in-flight advisor를 고아로 만든다) `anchor`가 비어 있으면(arm되지 않은 유령 loop) 확장을
   **차단**한다(`decision: block`) — 상태를 건드리지 않아 돌던 loop가 무사하다.
2. **prompt 제출은 event가 아니다** — prompt 경로에 hook이 없다(결정 15). 타이핑된 사용자 turn·AskUserQuestion
   응답·task-notification·scheduled wakeup·ESC 어느 것도 loop 상태를 건드리지 않고, armed loop는 다음
   정지에서 재개된다.
3. **Stop 자동 종료** — advisor 종료 판정·anomaly failsafe 시 `active`를 지운다(위 핵심 loop).
4. **`/ploop:off`** (off_command) — loop를 **일시정지**한다: `active`만 지우고 round
   상태(ledger·advice-history·round_start_line)는 보존해 `/ploop:on`이 이어받게 한다. background advisor
   in-flight 중에도 무조건 멈추도록 `advisor_running`도 지운다. 종료가 아니라 종료 notice는 없다. `active`가
   없으면(미실행·이미 off) **차단**한다.
5. **`/ploop:on`** (on_command) — **범용 wake button**이다: stale handoff/gate transient(token·running·
   advice·narration)를 지우고 `phase`를 `fresh`로 정규화(다음 정지가 advisor 미실행 round를 record하지
   않게)하고 이상 counter를 reset하되 advice-history·round_start_line은 병합이 보존한 뒤 `active`를 다시
   쓴다. off·anomaly failsafe·예외(ESC·API error·session limit)로 멈춘 stuck loop까지 무엇이든 깨운다(active여도
   차단하지 않는다). 재개 불가는 딱 둘 — `anchor.md`/`loop.log` 부재(재개할 loop 없음)와 `phase ==
   converged`(advisor 수렴 종료 = 진짜 완료; 새 anchor를 launch) — 이때만 **차단**한다.

**anchor 정박은 세 겹이다.** 셋 다 anchor *text*의 보존·주입이다 — "흐려지면 anchor.md를 다시 읽어라"류
pointer는 두지 않는다(agent가 drift를 자각해야 작동하는데 goal drift는 점진적이라 자가감지되지 않는다).

1. **외부 보존(mechanism 1)** — launch hook이 anchor를 `anchor.md`에 기록한다. transcript와 독립이라 main이
   어떻게 compaction되든 원본이 보존된다. advisor가 매 round 읽고, mechanism 2가 재주입 소스로 쓴다.
2. **launch skill 본문 re-inject** — `/ploop:launch` skill 본문은 loop notice와 `<ANCHOR>` 원문을 담고, skill
   본문은 auto-compact 후에도 re-inject되므로(skill당 앞 5,000token·합산 25,000token 예산) anchor handoff
   text가 main context에 남는다(main session은 custom system prompt를 못 받지만 skill re-inject가 그
   자리를 메운다).
3. **mechanism 2(PostCompact + anchor text inline)** — `PostCompact`가 `_compacted`를 touch하면 다음
   Stop이 그 round trigger에 **anchor 원문을 recency 위치에 inline**한다(`format_advisor_trigger`의
   `anchor_text`). re-inject(2)는 5,000token cap에 잘리고 원래 깊이에 남는 반면, 이것은 discrete한
   compaction event마다 anchor 전문을 무조건 recency에 박는다. main session `PostCompact`는 확실히 fire한다.

---

## Hooks

| Hook | Matcher | 시점 | 동작 |
|---|---|---|---|
| **UserPromptExpansion** | `ploop:launch` · `ploop:off` · `ploop:on` | slash command 확장(제출 전) | launch: round reset + `anchor`·`active` 기록 — `active` 존재·빈 `anchor`·prerequisite(nested cap `<5`·`autoCompactEnabled`·`alwaysThinkingEnabled`) 미충족이면 차단 · off: `active` 삭제(round 상태 보존, in-flight 무관) — 비활성이면 차단 · on: `phase`→`fresh` 정규화·counter reset(history 보존) + `active` 기록(stuck·active도 wake) — `anchor`/`loop.log` 부재·`converged`면 차단 |
| **PostCompact** | (전체) | compaction 후 | `compacted` marker touch (Stop이 mechanism 2로 anchor text 재주입) |
| **PreToolUse** | `Agent` | main이 Agent 호출 | `advisor` 호출이면 1회용 token 검사 → 허용(소비 + `advisor_running` set) 또는 `exit 2` deny(자발 호출 차단) |
| **Stop** | (전체) | main이 종료 시도 | active gate → **background gate**(`background_tasks`: subagent·workflow·running shell 조용히 대기, monitor·비running·그 외 통과) → **in-flight guard** → 종료 판정 → `exit 2`+stderr(advisor 호출 지시, 종료 시엔 종료 notice+log recap) 또는 `exit 0`(허용) |
| **Stop** | (전체, `asyncRewake`) | main이 종료 시도 | **heartbeat**(결정 19): armed loop면 arm이 nonce를 기록·handoff하고 wrapper sh 자신이 3h를 잔다 — fire 시 nonce 최신·armed면 `exit 2`로 잠든 session을 깨워 background audit 지시, 아니면 무음 자멸. 비활성 session은 즉시 exit 0 |
| **SubagentStop** | (전체) | subagent 종료 | `advisor` 종료면 `advisor_running` clear (in-flight 추적) |

plugin agent는 `ploop:<agent>`로 scoped 등록돼 Agent 호출의 subagent_type이 그 이름을 쓴다. hook은
`bin/ploop-hook` shell wrapper를 거쳐 `uv`를 호출하고, wrapper가 uv 가용성을 먼저 확인해 실행 불가 시 graceful
degrade를 한 지점에서 일원화한다. hooks.json은 exec form(`command`+`args`)으로
wrapper를 호출한다 — 경로 placeholder가 shell tokenization을 거치지 않아 설치 경로에 공백이 있어도 hook이 죽지 않는다.

**Graceful degradation.** uv가 없거나 환경을 provision하지 못하면 wrapper가 launch·off·on expansion을
사유와 함께 차단하고(선언 없는 상태 변화 방지) 그 외 hook은 무음 exit 0이다 — session은 깨지지 않고, 안내는
모든 claude-automata plugin이 의존하는 version-up-alert가 session 시작에 맡는다.

---

## 핵심 설계 결정

1. **loop main = session main agent.** advisor loop의 main 역할을 session agent(depth 0)가 맡고
   trigger는 Stop hook이다. advisor·narrator만 nested subagent로 격리해 구독 안전성을 얻는다 — anchor의
   지휘(orchestration)는 원래 main context에서 일어나므로 별도 operator subagent는 격리 이점 없이
   부채만 남겨 제거했다. main은 orchestrator다(launch rules가 세운다): 작업은 위임한 agent에서
   소비되고 main context에는 지휘만 남는다 — depth 0의 보장(PostCompact 확실 fire·동기
   Agent 호출·전체 hook 수명주기)이 작업이 아니라 지휘에 필요한 전부라 배치가 정확히 맞는다.
2. **hook은 trigger, 실행은 Agent tool.** Claude Code hook은 stdout/stderr/exit code로만 통신해 tool call을
   fire하지 못하므로, Stop이 `exit 2`+stderr로 main에게 advisor 호출을 **지시**하고 main(LLM)이 Agent tool로
   실행한다. 이 간접 한 단계가 ploop hook 설계의 본질이다. 자발 호출(경로 이탈)은 launch skill의 규칙 고지 + PreToolUse token gating(결정 9)으로 막는다.
3. **loop 상태는 hook 단독 소유.** advisor는 advice(또는 종료 token)를 `advice.md`에 Write만 하고 hook이 그
   파일을 읽어 4field ledger를 기록한다(`{**ledger, ...}` 병합, 미언급 field 보존). `advice.md`가 유일 channel이라
   transcript를 scrape하지 않는다 — 단일 작성자라 동시성 문제가 없고 Agent tool_result 형식(메타
   envelope·prose) 의존이 통째로 사라진다.
4. **작업 transcript = main transcript, action-history는 narrator 위임.** main이 anchor를 소유·지휘하므로
   action(위임·검증 포함)과 advisor 호출이 모두 main transcript에 있다. **hook은 transcript를 parsing하지 않는다** —
   `round_start_line`(ledger 소유)부터 정지 시점까지를 순수 line cut으로 잘라 `round.jsonl`에 저장하고,
   narrator가 그 파일 전체를 스스로 해석해 main의 생각·시도·결과를 서술한다. 이 정지 시점엔 다음 round의
   advisor 호출이 아직 append되지 않았으므로 `[round_start..end]`가 정확히 이번 round다. **이 위임이 message
   형식 의존(`isCompactSummary` filter·`queued_command` 승격·round 경계 heuristic·advisor-strip)을 통째로
   없앤다** — slice가 연속 구간이라 compaction 요약·steering이 그대로 담기고 경계 오인 잘림이 구조적으로
   불가능하다(실패 방향은 "넓게"). 사용자 지시는 anchor보다 상위 권위이므로 narrator가 그대로 서술해
   advisor에 전달하며, steering은 round를 reset하지 않는다.
5. **활성화 gate + 의미론적 종료(숫자 상한 없음) + 수동 pause/resume.** `/ploop:launch`가 `active`를 써야
   Stop이 loop를 돌고, 종료는 round 상한 없이 advisor 종료 token·anomaly failsafe로만 일어난다(advice-history가
   파일이라 context를 안 차지 — anchor도 동일). 이 자동 종료와 별개로 사용자는 `/ploop:off`로
   일시정지·`/ploop:on`으로 재개한다(위 활성화 lifecycle).
6. **anchor 정박 — mechanism 1 + 2.** 외부 보존(`anchor.md`)으로 원문이 디스크에 영속하고, `PostCompact`
   marker를 소비한 Stop이 compacted round의 trigger에 anchor 원문을 inline한다(mechanism 2 — discrete
   compaction event에 무조건 text 주입). advisor도 매 round anchor를 읽어 anchor-grounded advice를
   surface하므로 main은 간접 정박되고, launch skill re-inject가 handoff text를 보존한다. "매 round
   pointer"는 이들과 중복이라 두지 않는다(irreducible).
7. **advisor 분석 입력은 5-section 순서.** advisor는 role·anchor·action-history·advice-history·instructions
   순서로 맥락을 쌓는다(분석 대상은 **"main agent"**). candidates 파일이 비어있지 않으면 advice-history
   다음에 그 경로 1행이 조건부로 붙는다 — 비어있음 판정은 hook 코드의 결정론이라 standalone ploop(응고
   계약 없는 사용)의 advisor 입력은 기억 domain을 모른 채로 남는다. hook이 advisor를 직접 못 부르므로 같은 순서를 trigger로
   재현한다 — role은 system prompt, anchor·advice-history·instructions는 파일, action-history는 advisor가
   inline된 narrator 호출을 실행해 얻은 `narration.md`다. **trigger는 advisor의 Agent 호출을(그 안에 narrator
   호출을 inline해) verbatim으로 작성해 넘기고 main·advisor는 relay만 한다** — LLM이 구성할 게 없어 가장
   결정론적이다. 정박 대상은 session 최초 prompt가 아닌 `/ploop:launch` handoff(`anchor.md`)다 — launch hook이
   인자를 verbatim capture하므로 원문과 정확히 일치한다.
8. **단일 model `opus[1m]`(main·advisor).** 추론 최대화와 compaction 빈도 감소가 같은 선택으로 수렴한다.
   narrator는 원본 slice를 해석해 서술하므로 `sonnet[1m]`/`medium`이다(`[1m]`은 대형 round slice
   수용). main은 session model이라 사용자가 `opus[1m]` 실행을 권장한다.
9. **자발 advisor 호출 차단(PreToolUse gating).** main이 hook 지시 없이 advisor를 부르면 지정된 5-section
   입력 대신 main 자기 말이 가고 `advice.md`를 엉뚱한 시점에 덮어써 channel을 오염시킨다. Stop이 호출을 지시할
   때만 1회용 token을 세우고 PreToolUse(matcher `Agent`)가 token이 있을 때만 통과시킨다(narrator는 read-only
   leaf라 gating 안 한다). stale token은 launch reset·`/ploop:on` 정규화가 지운다. 미호출로 정지하면 token이
   남아 그 round advice 기록을 건너뛰고(중복 방지) decline으로 처리한다(결정 14).
10. **advisor·narrator 호출은 동기(`run_in_background=false`).** Agent tool은 기본 async라 background 호출은
    advice 없이 acknowledgement만 돌려준다. main은 foreground이고 trigger가 두 호출을 모두
    `run_in_background=false`로 작성해 동기 실행을 지시한다 — 그래야 advisor가 정지 전에 `advice.md`를 남기고
    narration이 advisor 입력이 된다. 빈 출력·background 전환은 결정 14·13이 처리한다.
11. **logging: 완결 round 단위 — 서사 + 그 round의 advice.** `_loop.log`의 한 entry는 round 작업의
    서사(advice 도착·반응) 뒤에 그 advice 전문이 `/ Advice`로 붙는다(round 0은 anchor 초기 작업이라 advice
    없음, 종료 token 같은 기계 신호도 log에 안 남는다). nested 구조상 narration은 다음 advisor 호출에서
    생성되므로 entry는 한 정지 늦게 완결되고, 번호는 advice ordinal이라 skip round에도 `advice_history.md`와
    어긋나지 않는다. advisor도 같은 서사를 입력으로 받아 자기 직전 advice에 대한 main의 반응을 그대로 본다.
    이 log가 turn의 유일한 완전 기록이라 launch가 anchor 원문(`[[ ANCHOR ]]` header)으로 새로 시작해 한 anchor가
    log 하나를 소유한다.
12. **plugin 영역만, `settings.json` 불간섭.** 활성화는 `/ploop:launch` handoff이고 anchor 없이는 아무것도
    fire하지 않는다. 프로젝트 CLAUDE.md·rules는 main·advisor·narrator가 모두 상속한다(차단이 all-or-nothing이라
    코드 작업에 규칙이 필요한 main을 우선; advisor·narrator 상속은 약한 오염 여지).
13. **advisor in-flight guard(background 전환 cascade 차단).** advisor를 `run_in_background=false`로 지시해도
    사용자가 실행 중 advisor를 background로 보낼 수 있고, 그때 그대로 재주입하면 advisor가 매 정지 **증식**한다.
    PreToolUse가 `advisor_running`을 set하고 cycle 안에서는 SubagentStop만 이를 clear하며, Stop은 marker가
    있으면 in-flight로 보고 `exit 0` 대기한다. background 전환된 advice는 유실될 수 있으나 cascade는 확실히
    차단된다. **수용한 trade-off**: SubagentStop 누락 시 marker leak로 stuck-active가 되나 `/ploop:on`이
    정리·정규화해 복구한다.
14. **이상 신호는 1회 교정 후 재발 시 정직한 사유로 종료(anomaly cap = 2).** loop의 두
    참여자(advisor·main)는 신뢰할 수 없는 LLM이라, 첫 이상엔 1회 교정 기회를 주고 **연속 2회면**(종류 무관)
    실제 사유로 종료한다. **단일 `anomalies` counter**가 어떤 이상이든 증가시키고 clean round(advice가 쓰인
    round)에 0으로 reset된다 — malfunction·decline이 교대해도 누적돼 cap에 닿는다. (a) advisor가 advice를 안 쓰면(오작동) round를 입력 동결로 재시도(RETRY notice),
    2회면 오작동 종료. (b) trigger가 미응답이면(main 거부 또는 사용자가 끊은 turn) **권한 분할**(종료권=advisor·
    작업권=main)을 고지하며 재주입(DECLINE notice) — 거부 근거는 slice→narrator로 advisor에 닿아 타당한
    거부는 advisor 종료 판정으로 관철되고(in-band 사용자 종결 지시도 이 경로), 2회면 합의 channel 붕괴로 failsafe
    종료한다(notice는 광고하지 않는다). 미소비 token은 ESC로 끊은 turn에서도 남으므로, main에 노출되는 두
    문구(재주입 notice·failsafe 사유)는 주체를 특정하지 않는 중의적 표현을 쓴다. 종료는 항상 실제 사유로
    보고한다(오작동을 수렴으로, 거부를 고장으로 위장하지 않음) — 이제 종료가 `/ploop:on`으로 재개 가능하므로
    이르게 끝내도 손실이 없다. **수용한 한계**: decline은 round를 전진시켜 `round.jsonl`을 거부 slice로
    덮어써 직전 round narration 1건이 유실될 수 있으나 advice-history(파일)는 무손실이다.
15. **종료·일시정지는 명시적 신호만 — prompt 경로에 hook이 없다.** loop를 끝내는 신호는 advisor 종료
    token과 결정 14 failsafe뿐이고(자동 종료), 사용자는 이와 별개로 `/ploop:off`·`/ploop:on`으로
    pause/resume한다(상태 보존). UserPromptSubmit 경로는 task-notification·scheduled wakeup 같은 system
    prompt(`promptSource: system`)도 타고 launch가 background Agent 전개를 권장하므로, prompt를 개입으로
    취급하면 loop가 자기가 권장한 pattern에 죽는다 — 타이핑된 사용자 turn도 개입이 아니다(AskUserQuestion 응답·
    mid-turn 지시는 참여, in-band 종결은 결정 14 합의 경로로 advisor에 닿음). ESC 감지도 두지 않는다: interrupt는
    hook event가 없어 transcript sentinel 판독이 필요한데 형식 의존을 하나 더 심는다 — ESC는 turn만 끊고
    armed loop는 다음 정지에서 재개되며 공식 일시정지는 ESC 후 `/ploop:off`다. 이 정책으로 UserPromptSubmit
    hook이 통째로 사라졌다.
16. **advisor는 foreground·background가 모두 빈 정지에만 소집 — `background_tasks` gating.** advisor 판정은
    main이 round 작업을 완료한 뒤라야 유효하다. foreground가 비었다는 것은 Stop이 fire한 것 그 자체이고, background는
    Stop 입력의 공식 배열 **`background_tasks`**(v2.1.145+)로 읽는다 — harness는 background가 남아 있어도 session을
    정지시키고 완료 event로 다시 깨우므로, gate가 삼킨 정지는 반드시 되돌아온다 — **단, gate된 background 중
    적어도 하나가 실제로 완료할 때만**(그 전제조건이 깨져도 잠은 heartbeat가 3h로 상한한다 — 결정 19). gate는
    **완료가 session을 깨운다고 명세가 보장하는 타입**에만 걸고, 셋 모두 **조용히 대기**한다(exit 0):
    `subagent`·`workflow`(완료 알림), **running** `shell`(exit 시 재호출). heartbeat 이전에는 shell에만 집합당
    1회 "영원히 잠들 수 있다"는 교정 지시를 냈으나(`gated_shells` marker로 중복 방지), 잠이 3h로 상한된 뒤 그
    경고의 위협 주장은 거짓이 되고 교정 내용은 heartbeat audit이 실제 발생 시점에 나르므로 지시와 marker를
    철거했다(archive `2026-07-30-ploop-silent-shell-gate`) — stop 시점의 gate는 이제 할 말이 없다.
    `monitor`는 명세상 session 수명 process라 gate하면 영구 교착 — 통과가 정당한 round 종료다. 그 외 타입·미지
    타입·**running이 아닌 status의 shell**(list에 잔류한 terminal shell이 advisor를 영구 유예하는 구멍)·field
    부재(task registry 도달 불가 — 명세상 이때만 배열이 빠진다)는 gating하지 않는다: 실패 방향은 이른
    advisor이지 loop 정지가 아니다(status 부재만은 running으로 간주 — schema 표류 안전). 완료를 기다려야 하는
    background는 gating 유형(shell·subagent·workflow)으로 두고, server 같은 ambient process는
    `Monitor`(session 수명 차선)로 돌린다 — ambient가 shell 차선에 살아 있는 한 advisor 소집이 유예되는 문제는
    heartbeat가 고치지 못하며(잠만 상한한다), 그 예방선은 launch rules의 Monitor 규칙이다.
17. **docent 표면 — hook 0·쓰기 0, query-time 해석.** docent는 skill 본문(교리)과 read-only
    resolver(`docent` console script)가 전부다: hooks.json에 등록하지 않아 loop 기계와 접점이 없고,
    `disable-model-invocation: true`라 loop main이 스스로 교리를 주입해 orchestrator 정체성과
    충돌할 수 없다(launch·off·on과 같은 explicit-only class — define 둘만 model-invocable로 남는다).
    session 식별은 skill 인자가 아니라 resolver 해석이다 — 새 launch는 새 loop라 주입된 식별은 낡은
    subject를 가리키게 된다. data dir는 machine 전역이지만 목록은 resolver가 launch directory
    기준으로 강제한다: launch hook이 `{session}_project`에 기록한 launch directory(기록 없는
    active loop은 Stop hook이 backfill — 기록 도입 이전 fleet의 수렴 경로)가 호출 project dir
    (`--project-dir`, skill이 `"${CLAUDE_PROJECT_DIR}"`를 관통시킨다 — Bash env에는 CLAUDE_*
    주입이 없다, 실측 2026-07 — →env→cwd)와 일치하는 session만 나온다. 기록 없는 legacy는
    transcript 부모 이름의 관용 대응(오판은 과포함 방향)이 fallback이고, 둘 다 없으면 노출하지
    않는다 — 타 directory·판정 불가의 숨김은 내용 없는 개수 1행로만 고지된다(loop 기계는
    session_id 밖을 읽지 않으므로 stale loop의 유일한 교차 세션 표면이 이 열거였다). 판정을
    launch 기록에 두는 이유는 loop 수명이 transcript 보존기간(활동 기준 정리)을 넘기 때문이다 —
    장기 pause가 자기 directory에서 은닉되지 않고, 타 directory loop은 transcript 소멸 후에도
    재노출되지 않는다. `--exclude-converged`는 완료 anchor를 제외한다(기본 포함 — 끝난 loop
    회고는 1급 용례). docent의 subject는 그 목록의
    loop 하나다. data dir는 `--data-dir`(skill이 `"${CLAUDE_PLUGIN_DATA}"`를
    관통시킨다)→env→`~/.claude/plugins/data/ploop-*` glob 순으로 해석한다 — placeholder의 skill 본문
    치환과 data dir layout(`~/.claude/plugins/data/{id}/`)은 공식 문서화되어 있다. 관측 기반 의존은
    transcript 쪽이다: `~/.claude/projects/*/{session}.jsonl` 위치와 `{session}/subagents/agent-*.jsonl`
    worker 기록은 미문서 layout이라(실측 2026-07) 표류 시 "not found"/"(absent)"로 degrade한다.
    resolver는 이 경로들을 출력해 worker 내부의 사후 판독을 연다 — advisor에 비가시인 worker 내부가
    docent에는 보이되, 산출의 판정은 여전히 gate가 소유한다(신뢰 model 불변).
18. **launch prerequisite assertion 레이어 — init provision + READ-only 검사.** ploop은 비자명한 Claude
    Code 설정에 mechanism이 걸려 있고 Claude Code 변경이 그 default를 뒤집어 loop을 silent하게 깨뜨릴 수
    있다(2.1.217 nested subagent 기본 off). `/ploop:launch`가 세 요구를 검사해 미충족을 모아 block하고 각
    settings.json fix·재시작·relaunch를 한 알람으로 안내한다: ① nested subagent
    `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH >= 5`, ② `autoCompactEnabled`, ③ `alwaysThinkingEnabled`
    (permission mode·autoMemory·model은 강제 안 함 — owner 결정). **provision↔enforcement 분리**: settings
    쓰기는 `claude-automata init`의 본업(PREREQUISITES + env `"5"` = 2.1.172 원래 cap)이라 거기서 심어 커밋된
    `.claude/settings.json`으로 기여 machine 전체에 전파하고, ploop은 **읽기만** 한다(결정 12 no-write 보존).
    **소스 = effective 우선**: nesting은 env라 `os.environ`(effective)으로 봐 settings.json만 고치고 재시작
    안 한 미반영 상태를 잡아 재시작을 강제한다 — declared read라면 "설정 있는데 안 먹는" silent 실패가
    재발한다; compaction·thinking은 runtime 신호가 없어 project settings.json declared를 읽는다(차선).
    **auto-write 기각**: env는 startup 반영이라 재시작이 어차피 필요하므로 self-provision(=settings.json
    write=결정 12 위반)의 실익이 "한 줄 절약"뿐이다. 검사는 확장 가능한 tuple이라 향후 Claude Code 변경의 새
    요구를 한 줄로 더한다(모범 선례 템플릿).
19. **wake integrity — heartbeat: 침묵 3시간이 armed loop를 깨운다 (사람 감독 패턴의 기계화).** 결정 16의
    전제("exit이 깨운다")는 exit할 수 있는 background에만 성립한다. 종료 불가능한 background shell(실측
    2026-07: producer가 죽은 `until [ -s f ]; do sleep 60; done` — 32.8시간 손실)이 마지막으로 남으면 gate는
    wake 근거 0으로 exit 0을 반복하고, hook은 stop에만 돌므로 **정지 후에는 loop 자신의 어떤 코드도 구제할 수
    없다**. 사람 감독자가 이를 막는 방식은 단속이 아니라 관찰이다 — 몇 시간의 침묵을 보면 "뭐 하고 있나"를
    묻는다. heartbeat가 그 trigger를 그대로 재현한다: **모든 armed-loop stop이 `asyncRewake` Stop hook으로 3h
    timer를 남기고**(fresh nonce가 이전 timer 전부를 대체; 3h 잠은 wrapper sh 자신(~1MB)이 잔다 — `exec uv`는
    python으로 exec하지 않고 ~26MB로 상주하므로(실측 2026-07) python은 arm(nonce 기록·handoff 출력)과 fire 두
    순간만 돌며, fire의 exit code·stderr는 wrapper의 것으로 전파돼 harness가 관측한다), fire 시점에
    nonce가 여전히 최신이고 loop가 armed면 — 즉 **3h 동안 stop이 없었으면** — exit 2로 잠든 session을 깨워
    background audit을 지시한다(HEARTBEAT_NOTICE는 범주어를 쓰지 않는다 — `task`는 잔여 monitor·shell을
    audit 밖으로 밀어냈다(관측 2026-08)). 나중 stop이 있었거나 loop가 끝났으면 조용히 자멸한다:
    활발히 round를 도는 loop는 heartbeat를 듣지 않고, `/ploop:off`·수렴은 즉시 전 timer를 무장 해제한다.
    **왜 이 형태인가**: 잠드는 *이유*를 몰라도 된다 — 파일 대기·불투명 script·멈춘 subagent를 균일하게 3h로
    상한한다(0.50의 문자열 classifier는 결정 불가 판정·allowlist 쳇바퀴·양 소비처 공유 맹점으로 철회 —
    코드 단속은 agent 책임의 침범이었다. archive `2026-07-30-ploop-heartbeat` 참조). session cron(7일 만료로
    장기 mission에서 wake source가 소리 없이 소멸)·plugin monitor(experimental + Monitor 불가 host에서 무음
    skip)도 같은 이유로 기각. timer는 OS process라 compaction과 무관하고, payload는 fire마다 새로 생성된다.
    timeout 11100s는 2.1.220 번들 정적 분석(command hook timeout 무clamp)과 live canary(idle session이
    stderr payload로 깨어남 — `docs/research/asyncrewake-stop-hook-2026.md`)로 실측했다. wake가 어느 날
    조용히 죽으면 pre-heartbeat 현상 유지로 퇴행할 뿐 새 피해는 없고, 하위 harness 우려는 root canon의
    auto-update 전제가 배제한다. advisor는 결코 arm하지 않아 결정 16의 소집 계약은 불변이다 — 유예의 길이
    자체는 결함이 아니며, heartbeat wake가 잦아지는 것이 아니라 잠이 유한해지는 것이다.
20. **deadline — 시계는 정보, 집행은 advisor.** anchor 최상단 frontmatter `deadline:`(ISO 8601, timezone
    필수)을 Stop hook이 trigger 조립 시점에 읽어 advisor prompt에 status 한 줄(`deadline: 2h 13m remaining`·
    `expired 23m ago`·parse 불가 시 unreadable로 원문 표면화 — 조용한 무장 해제는 거짓 안심이다)로 실어준다.
    미선언 anchor는 비용 0. advisor는 Bash가 없어 시계를 못 읽는 관측 공백을 이 줄이 메우고, 마감 판단 —
    잔여 내 wrap-up 조율, 경과 시 종료(instruction 판단 절이 명시) — 은 종결 권위의 기존 mandate가 흡수한다.
    threshold 자동 off는 기각했다: off는 무통보 인간 전용 pause라 마지막 시간(정확히 wrap-up 창)을 절단하고,
    인간 pause와 기계 만료를 같은 상태로 접어 구별 불능을 만들며, 결정 19가 폐기한 코드 단속을 재도입해
    종결 권위를 이원화한다. 마감을 넘긴 기절은 heartbeat(결정 19)가 깨워 다음 stop에서 advisor가 경과를
    본다 — 잠은 heartbeat가, mission은 deadline이 상한하고, 집행은 둘 다 advisor다.

---

## 기술 risk

설계는 성립하나 live tree 없이 unit test할 수 없던 항목들이다. 모두 **graceful degrade**한다.

1. **Stop block cap.** Claude Code는 Stop hook이 **연속** N회 종료를 막으면 강제 종료하나
   (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, 기본 8), 이 counter는 생산적 작업(tool-use) turn마다 0으로 reset된다.
   ploop은 매 round advisor 호출·advice 작업을 하므로 걸리지 않고, main이 trigger를 무시하는 무진전 정지는
   decline failsafe(결정 14)가 앞서 끝낸다 — cap은 backstop으로만 남는다. advisor가 종료를 안 내고 main이
   무한히 **일하는** 생산적 무한 loop만 이 cap도 못 막으므로(작업이 reset) 그땐 `/ploop:off`가 수단이다.
2. **transcript 형식 가정.** hook은 transcript를 parsing하지 않는다(결정 4). 유일한 의존은
   **transcript가 line 단위 append-only라 line 번호가 안정적**이라는 것 하나다(compaction도 append) —
   형식 field가 아니라 파일 구조이고 어긋나도 slice가 "넓게"로 degrade한다.
3. **main의 지시 순응도 — risk로 취급.** main이 stderr "advisor 호출"에 매 round 응하지 않을 수 있다
   (in-band 사용자 지시를 근거로 정당하게 거부하는 사건 관측). 미호출 1회는 권한 고지로 합의 channel에
   재유도되고 2연속이면 failsafe가 무결하게 닫는다(결정 14).
4. **PreToolUse 발동·session 일치** — 자발 호출 gating은 PreToolUse가 main의 Agent 호출에 발동하고
   session_id가 Stop과 같아야 성립한다. 미발동이면 token이 소비되지 않아 매 정지가 decline으로
   오판되고 2round failsafe로 닫힌다 — session은 무손상, `/ploop:on`으로 재개 가능(graceful).
5. **SubagentStop `agent_type`은 공식 문서상 plugin agent에 scoped(`ploop:advisor`)다** —
   이 repo의 실측은 bare(`advisor`)도 기록한 바 있어 2형 matching으로 관용한다(PreToolUse의
   `subagent_type`은 scoped 정확 일치). 표류하면 in-flight marker가 leak해 stuck-active가 되고
   `/ploop:on`이 복구한다(결정 13의 수용 trade-off와 동일 경로).


---

## 수용한 한계

- **advice-history·loop.log는 무상한 성장한다** — advisor가 매 round advice-history 전문을 읽으므로
  월 단위 purpose loop에서 비용이 누적된다. windowing은 관측 후 별도 작업이다.
- **session hard-death에는 drain notice가 닿지 않는다** — candidates의 종료 protocol 운반체는 종료
  notice뿐이라, process 사망 시 잔량은 유실된다. "수시로 비워라"(launch rules)가 손실 창을
  bound한다 — 작업기억은 lossy가 정의다.
- **orchestrator 정체성의 재주입은 launch 본문 re-inject 1겹이다** — anchor의 3겹 정박과 비대칭.
  compaction 후 정체성 표류는 관측 항목이다.
- **background가 상시 점유되면 advisor가 소집되지 않는다**(결정 16의 뒷면) — 위임 파도가 영원히
  비지 않는 운용에는 기계 보장이 없다. rules의 파도-정지 rhythm이 자연 유도하는 것으로 수용한다.
- **round 0에는 candidates 경로가 전달되지 않는다** — 경로의 유일 결정론 channel이 Stop trigger라 첫
  정지 전의 후보는 context에만 존재한다. 첫 trigger에서 파일로 이동하는 self-healing으로 수용한다.
- **candidates label의 stale/growing 판정은 round 단면 snapshot이다** — advisor는 queue의 추이를 갖지
  않는다. 표면화의 근거는 "쌓여 있고 처리되지 않았다"뿐이고 그 이상의 판단은 main 몫이다.
- **worker 내부 행위는 advisor에 비가시다** — narrator는 main transcript(지휘·주장)만 서술한다.
  결함이 아니라 신뢰 model의 이동이다: 산출의 판정은 관측이 아니라 gate(독립 검증·CI)가 소유한다.
- **docent의 해설은 기록 기반 추론이다** — 기록에 없는 "왜"의 재구성은 오귀속할 수 있다. 교리의
  관측/추론 구분·round 인용이 그 경계를 표시하고, compaction 이후에는 main도 그 기억을 갖지 않으므로
  기록이 최선의 증인이라는 전제는 advisor loop와 공유한다.
- **지난 session 기록은 GC 없이 축적된다** — disk의 기록은 무상한 성장한다. 열거는 launch
  directory 범위로 좁아졌고 완료 anchor는 flag로 제외 가능하지만, 기록 자체의 windowing·정리는
  관측 후 별도 작업으로, advice-history·loop.log와 같은 계열의 한계다.

---

## 언어와 prompt

언어 정책은 repo 전역 규약이다 — 정본은 root [ARCHITECTURE.md](../../ARCHITECTURE.md)의
언어·prompt 정책 절. ploop 특이사항만 남는다: agent·skill prompt와 advisor instruction은
단일 `.md`이고, hook 주입 message(advisor trigger)는 `prompt.py`가 조립한다(영어 — 코드 발신 lane).
worker 위임 prompt의 영어 규칙은 launch rules가 세운다. advice·narration은 한국어로 남는다:
main·소유자가 `loop.log`로 읽고 narration은 사용자 발화를 원문 보존한다.

---

## 파일 map

```
ploop/
├── .claude-plugin/plugin.json        # manifest
├── agents/                           # loop tier(advisor·narrator)
│   ├── advisor.md                    # advisor 역할 + 5-section 읽기 순서 (Write: advice→advice.md)
│   └── narrator.md                   # round slice 파일 → action-history 서사 (Read: round.jsonl · Write: narration→narration.md)
├── prompts/instruction.md            # advisor 분석·출력 지침
├── skills/define-mission/SKILL.md    # /ploop:define-mission — 목표(goal) anchor 작성 (loop와 비연결, 수동 handoff)
├── skills/define-purpose/SKILL.md    # /ploop:define-purpose — 목적(purpose) anchor 작성 (loop와 비연결, 수동 handoff)
├── skills/docent/SKILL.md            # /ploop:docent — 기록 해설 교리 (read-only 질의 표면, 별도 session)
├── skills/launch/SKILL.md            # /ploop:launch — loop notice + orchestrator rules + 응고 계약 + anchor handoff (anchor 저장·활성화는 launch hook)
├── skills/off/SKILL.md               # /ploop:off — 일시정지 조용한 고지 (일시정지는 off_command hook)
├── skills/on/SKILL.md                # /ploop:on — 재개 확인 고지 (재개·정규화는 on_command hook)
├── hooks/hooks.json                  # UserPromptExpansion(launch·off·on) + PostCompact + PreToolUse(Agent) + Stop(gate + asyncRewake heartbeat) + SubagentStop
├── bin/ploop-hook                    # uv 가용성 check wrapper + heartbeat의 3h 상주(sh가 잔다 — uv는 exec돼도 상주)
├── src/                              # hook 구현 (runtime 의존성 없음)
│   ├── main.py                       # hook entrypoint(stop·pre_tool_use·heartbeat_arm·heartbeat_fire·subagent_stop·mark_compaction·launch·off_command·on_command)
│   ├── docent.py                     # docent resolver — session 열거·기록 경로 해석 (read-only, `docent` console script)
│   ├── state.py                      # Workspace(session 파일 경로의 단일 창구) + 4field ledger(advice_history·round_start_line·anomalies·phase) + phase 상수 · preserve-by-default load/저장
│   └── prompt.py                     # advice-history format + 5-section advisor trigger 조립(narrator slice 파일 경로 포함)
└── tests/                            # 구현 독립 (stdin/stdout/disk 구동)
```
