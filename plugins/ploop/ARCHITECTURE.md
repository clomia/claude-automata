# ploop — architecture

ploop은 **advisor loop** — main이 anchor를 향해 자율 항해하고, 독립 advisor가 mission 완수를
판정하는 자율 loop — 를 Claude Code의 subagent 위에서 구현한 plugin이다. 통합 지점은 Stop
hook이고, loop의 main 역할은 session agent 자신이다. advisor는 **완수 gate**다: loop는
advisor의 완수 인증으로만 수렴 종료하며, 매 정지의 안전 기계(directive 주입·flight
recorder·heartbeat·background gate)는 상시 무료로 돌고 advisor는 소집될 때만 과금된다.

---

## Glossary

- **advisor loop** — hook이 매 정지에 directive를 주입하고, main이 판단한 시점에 advisor가
  완수를 감사하는 자율 loop. 이 plugin(`ploop`)이 그것을 구현한다.
- **main** — advisor loop의 main 역할을 하는 session agent(depth 0). anchor를 소유하는
  orchestrator로서 작업을 agent에 위임·검증하고, 완수 판단 시(또는 독립 감사가 필요할 때)
  advisor를 소집한다.
- **directive** — 매 armed 정지에 주입되는 상비 지침: 끝난 round의 narrator 호출(무조건) +
  anchor 대조 자기감사 + advisor 호출 구문(조건부 — 소집은 main의 판단). 호출 구문은 hook이
  verbatim으로 조립한다.
- **round** — 정지와 정지 사이의 시간 구간. advisor 호출과 무관하게 매 정지 전진하며,
  narrator가 각 round의 slice를 서사화해 loop.log(flight recorder)에 쌓는다.
- **candidates** — main이 승격 대기 사실·용어 후보를 측정 방법과 함께 축적하는 작업기억
  파일(승격 대기열). 승격 아니면 폐기가 대기열의 존재 이유다.
- **anchor** — main을 anchor에 붙들어 매는 SSoT. transcript 바깥 외부 파일(`{session}_anchor.md`)에
  보존된다.
- **advice** — advisor의 **완수 감사 보고**: anchor 좌표를 인용한 미달·누락·미검증의 list,
  또는 종결 token(완수 인증·기한 종결 — 각자의 정직한 사유를 나른다). audit-history
  (advice_history)에 누적되어 반박된 항목이 재지적되지 않는다.
- **docent** — loop 기록을 소유자에게 해설하는 read-only 질의 표면. loop와 별도 session에서 돌며
  loop 기계와 접점이 없다(세 표면 절).

main은 advisor loop와 anchor 재주입으로 anchor에 **정박한다(anchored)** — 자기 확신으로
표류(drift)하지도, compaction으로 anchor를 잃지도 않는다. 종료 권한은 3분할이다: **완수
인증은 advisor 독점, 비상 정지는 main의 침묵 2회(인증 없음 — 결정 14), pause는 인간의
`/ploop:off`**.

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

## 왜 subagent인가 — 그리고 depth pin

Stop hook 안에서 `claude -p`를 spawn하는 가장 단순한 방법은 `--no-session-persistence`로 **별도의 임시
session**을 만드는 자동화 pattern이라, Claude Pro/Max 구독 약관상 계정 정지 위험을 부른다(실제 차단 이력) —
API 요금제 전용이 된다. 반면 `Agent` tool subagent는 **모든 요금제에서 지원되는 정식 기능**이다(main
session과 quota 공유). ploop은 이 정식 경로 위에서 돈다 — main이 narrator와 advisor를 각각 depth 1로
직접 호출하고, advisor는 아무도 spawn하지 않아 **loop 기계 자체는 nesting을 요구하지 않는다.**

**nested subagent depth pin은 loop 기계가 아니라 orchestration 환경 계약이다.** launch rules는 작업의
Agent 위임을 세우고, mission worker들은 검증 sub-agent를 다시 spawn하는 tree로 돈다 — 그 깊이가
harness default에 좌우되면 mission 도중의 auto-update가 위임 구조를 조용히 바꾼다. 실제로 default는
세 release에서 세 번 바뀌었다: 5(2.1.172 도입) → **1**(2.1.217 기본 차단) → **3**(2.1.219 상향, 공식
문서 확인 2026-08). `claude-automata init`이 `.claude/settings.json`의 `env`에
`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH="5"`를 provision해 표류를 pin하고(init 소관 — ploop은
settings.json을 건드리지 않는다, 결정 12), `/ploop:launch`의 prerequisite assertion이 그 값 `<5`면
(다른 요구와 함께) loop을 arm하지 않고 교정을 안내한다(결정 18).

---

## Agent Tree

`main`은 사용자와 대화하는 session(depth 0)이자 advisor loop의 수행자다. narrator·advisor는 둘 다
main이 직접 호출하는 depth-1 subagent다 — narrator는 매 round의 flight recorder, advisor는 소집될
때만 도는 완수 auditor. 방대한 round transcript는 narrator에서 소비·압축되고, advisor는 축적된
narration(loop.log)을 읽는다.

```
main      depth 0  session     full tools    loop main: runs the anchor
   |  Agent(narrator)  every round   <- directive step 1
   |------> narrator  depth 1  Read Write   round slice file -> narration.md
   |  Agent(advisor)   on demand     <- directive step 3 (main's judgment)
   '------> advisor   depth 1  read-only+Write   audits state vs anchor -> advice.md
```

| Tier | 도구 (allowlist) | model | effort |
|---|---|---|---|
| **main** | 전체 (session) | `opus[1m]` 권장 | inherit |
| **advisor** | 전체 − `Bash·Edit·NotebookEdit·Artifact·Agent` (`Write`는 보고 출력용) | `opus[1m]` | max |
| **narrator** | `Read` · `Write` (narration 출력용) | `sonnet[1m]` | medium |

- **advisor는 `Write`로 감사 보고(또는 완수 token)만 쓰고 나머지 부작용 도구는 막혀 있다
  (`disallowedTools: Bash, Edit, NotebookEdit, Artifact, Agent`).** subagent의 최종 message는
  customizing 불가라 추론 prose가 섞이므로(harness 한계), 보고를 `advice.md`(비보호 system temp —
  보호된 `~/.claude` 하위인 `CLAUDE_PLUGIN_DATA`는 auto mode Write가 classifier에 막힌다)에 Write해
  chat channel과 격리한다. `Bash` 차단은 임의 부작용(`rm`·test 실행) 방지고, `Agent` 차단은 그 금지의
  proxy 우회(Bash 가진 worker 위임)를 막는 봉인이다 — **감사는 증거를 요구하지 생산하지 않는다.**
  `Write`만 좁게 연 것은 보고 channel을 위한 의식적 완화다(전제: auto/bypass 권한 mode). 남은
  read-only 도구(`Read·Glob·Grep·Web*`)로 상태를 실측한다.
- **narrator는 `Read`·`Write`만 가진 leaf.** hook이 잘라 준 round slice(`round.jsonl`)를 통째로 읽어
  해석하고(hook 측 parsing 없음), narration을 `narration.md`(advisor와 동일 temp channel)에 쓴다 —
  hook이 loop.log에 append하고, advisor가 최신분을 분석 입력으로 읽는다. 원본 slice를 해석하므로
  `sonnet[1m]`/`medium`이다.
- tree가 depth 1에서 닫히므로 depth pin(§왜 subagent인가)은 전량 mission worker들의 몫이다.

---

## 핵심 loop

```
main round N work ── stops
   |
   |  <-- Stop hook (active gate, background empty, not in-flight)
   |        read narration.md (round N-1)  -> append [[ Round N-1 ]] to loop.log
   |        read advice.md (a verdict only if the audit token was consumed):
   |          report                    -> append [[ Audit K ]], history += report
   |          completion/deadline token -> END converged (its honest cause)
   |          token consumed, no report -> MALFUNCTION: anomalies++, RETRY notice
   |          token left (any file here is not the advisor's -> ignored):
   |            line delta >  T -> WORKING stop: anomalies = 0 (normal)
   |            line delta <= T -> BARE stop: anomalies++, DECLINE notice
   |        anomalies >= 2 -> END with honest cause (resumable via /ploop:on)
   |        cut slice [round_start..end] -> round.jsonl, round++, re-arm token
   |        exit 2 + stderr: standing directive
   v
main round N+1:
   1. Agent(narrator)  round.jsonl -> narration.md      [flight recorder]
   2. re-read anchor; work remains -> keep working
   3. mission complete, or audit wanted -> Agent(advisor)
        advisor reads: anchor + loop.log + narration.md
                       + audit-history + instructions -> measures the state
        -> Write to advice.md: findings report | completion token
   4. read advice.md: observations, not orders
      -> judge each against the anchor; act or rebut
   ── stops (loop)
```

수렴 종료는 의미론적 판단만 인정한다: advisor가 `advice.md`에 **종결 token을 Write할 때만** 수렴
종료다(`phase`→`converged` + `active` 정리) — 완수 인증과 deadline 경과의 기한 종결은 별도
token이라 종료 사유가 위장되지 않는다(결정 20). advisor가 돌고도 파일이 없으면 **오작동**이다 — 정상
advisor는 완수조차 token Write로 표현하므로 안 쓴 것은 판정이 아니다(RETRY notice로 재소집).
directive가 응답되지 않은 **bare 정지**(token 잔존 + tool 활동 없는 transcript — main의 침묵 또는
사용자가 끊은 turn)는 **권한 분할**을 고지하며 재주입한다: 완수 인증권은 advisor에게 있고, **이
notice가 침묵 비상구를 공개하는 유일한 지점이다** — 한 번 무시된 뒤의 두 번째 침묵은 정보를 가진
신호여야 하기 때문이며, 평시 directive는 감사만을 보이는 출구로 유지해 과신 main의 우회를 광고하지
않는다. **working 정지(작업하고 멈춤)는 anomaly가 아니다** — 완수 gate 아래의 정상 항해이며
directive가 다시 설 뿐이다. 오작동·bare 모두 **연속 2회**면 정직한 사유 — 완수 인증 없는 비상
종료 — 로 닫는다(anomaly cap — 결정 14). **숫자 round 상한은 없다** — audit-history·loop.log는
파일이라 context를 차지하지 않고 advisor는 매 소집 stateless하게 reset되므로, 수렴은 "모든
요구사항이 충족됐는가"라는 anchor 좌표 판정에 맡긴다.

**모든 자동 종료 경로(advisor 완수 token + malfunction·bare failsafe)는 main에게 정직한 사유와 함께
종료 notice를 보낸다**(`format_end_notice`) — loop.log가 존재하면(launch부터 존재한다) recap 지시를
덧붙인다. 자연 종료는 종료 정지를 한 번 더 막아(exit 2) notice를 주입하고, 그 다음 정지는 `active`가
없어 통과한다. **이 자동 종료 동작은 노출 계약이라 불변이다.** 끝내기와 별개로 사용자는 `/ploop:off`로
일시정지·`/ploop:on`으로 재개하며(아래 활성화 lifecycle), off는 종료가 아니라 종료 notice를 보내지
않는다.

Stop hook은 main session 정지마다 fire하므로 `active` marker가 gate한다. advisor·narrator의 정지는
`SubagentStop`이라 이 Stop hook에 잡히지 않는다 — 재귀 guard가 필요 없다.

---

## context 경제 — 상시 안전, 호출제 메타인지

main의 context에 더해지는 것은 **① 짧은 stderr directive + ② round당 narrator relay 1회 + ③ 소집
round의 `advice.md` 읽기 + ④ 종료 시 1회의 log 요약 turn**뿐이다. round slice 해석은 narrator(depth
1)의 context에서, 상태 실측·log·audit-history 읽기는 advisor(depth 1)의 context에서 소비돼 main에
닿지 않는다 — slice가 커도(대량 작업 round) 그 비용은 narrator에 격리되고 요약된 narration만
loop.log로 흐른다. **narration의 축적이 감사 입력을 bound한다**: 며칠짜리 mission도 advisor는 원본
transcript가 아니라 압축된 flight record를 읽는다. per-round advisor 구독(매 정지 opus-max)은
한계효용이 체감하며 정액을 물리던 구조라 폐지됐다 — 감사는 필요할 때와 완수 심사에만 과금된다.

---

## 상태와 anchor 보존

상태는 사용자 repo 바깥에 둔다(repo 비오염) — 대부분 `CLAUDE_PLUGIN_DATA`, advice·narration·candidates 셋만 비보호
system temp(위 근거). 한 session에 하나의 anchor를 가정해 `session_id`로 keying한다.

| 파일 | 작성자 | 내용 |
|---|---|---|
| `{session}_anchor.md` | launch hook (UserPromptExpansion) | anchor 정의 (외부 보존 anchor) |
| `{session}_active` | launch hook 생성 · hook 삭제 | 활성화 marker (Stop gate) |
| `{session}_loop.json` | hook | 5field — `advice_history`(감사 기록, 길이=audit ordinal) · `round_start_line`(slice cut offset) · `anomalies`(연속 이상 counter — audit·working 정지에 0 reset) · `phase`(`fresh` 갓 launch/resume·판정 스킵 → `advising` round 진행 → `converged` 완수 인증·`/ploop:on` 거부) · `round`(진행 중 round ordinal — 매 arm 전진). `{**ledger, ...}` 병합이라 미언급 field 보존(preserve-by-default) |
| `{session}_round.jsonl` | hook | 이번 round transcript slice `[round_start..end]` (narrator가 통째로 분석) — line cut이라 message parsing 없음 |
| `{session}_advice_history.md` | hook | advisor 입력의 audit-history (XML `<audit-N>`) |
| `advice.md` (temp) | advisor (`Write`) | 감사 보고 또는 완수 token (유일 channel) — 비보호 temp라 auto mode Write 승인 · main·hook이 읽음 · prose 격리 |
| `narration.md` (temp) | narrator (`Write`) | round 서사 (advice와 동일 channel) — main이 매 round 직접 생산 지시 · hook이 loop.log로 append · advisor가 최신분을 분석 입력으로 읽음 |
| `candidates.md` (temp) | main | 승격 대기열 (자유 형식) — launch가 경로를 최초 배달·directive가 매 round 재안내 · 비어있지 않으면 advisor 입력에 조건부 1행 · launch만 지움(off·on·종료는 보존) · 종료 notice가 잔량 drain을 지시 |
| `{session}_loop.log` | hook | flight recorder — `[[ Round N ]]` 서사(한 정지 지연)와 `[[ Audit K ]]` 보고 전문의 시간순 append · launch가 `[[ ANCHOR ]]` 원문으로 새로 시작 · advisor의 action-history 입력이자 종료 요약·docent의 소스 |
| `{session}_advisor_token` | hook | round당 audit 1회 인가 token (Stop set · PreToolUse 소비) |
| `{session}_advisor_running` | hook | advisor in-flight marker (PreToolUse set · SubagentStop clear) |
| `{session}_compacted` | hook (PostCompact) | compaction 발생 marker (Stop이 mechanism 2로 소비) |
| `{session}_heartbeat_nonce` | hook (heartbeat) | 마지막 armed stop의 heartbeat nonce — fire 시점에 이 값과 다르면 timer가 자멸(더 새 stop이 감시를 소유), 같으면 3h 침묵이므로 wake (launch가 지움) |

**loop 상태(advice_history·phase·anomalies·round_start_line·round)는 hook이 단독 소유한다.** advisor는
보고(또는 완수 token)를 `advice.md`에 Write만 하고, hook이 다음 정지에 그 파일을 읽어
`advice_history`에 append하거나 완수 token이면 `phase`를 `converged`로 옮긴다. in-flight guard를 통과한
시점이라 advisor는 이미 종료했으므로 **token 소비 + `advice.md` 부재 = 오작동**이다(종결도 token
Write를 요구). **verdict는 audit token 소비를 전제한다** — directive가 report 경로를 노출하므로
미소비 round의 `advice.md`는 advisor의 것이 아니고(자기인증·위조 차단) 무시된 채 다음 arm이
지운다. token 미소비의 부재는 소집이 없던 정상 round다(working/bare 판정은 핵심 loop 절).
main도 같은 `advice.md`를 읽어 그 보고를 판단하므로 이 파일이 보고/완수의 유일 channel이자 main·hook
공통 소스다 — 단일 작성자(hook)가 ledger를 소유해 race가 없다.

**활성화 lifecycle.** `active` marker가 loop를 gate한다.

1. **`/ploop:launch`** (UserPromptExpansion) — 직전 anchor의 round 상태를 reset하고 `anchor.md`·`active`를
   쓴다. main이 anchor의 지휘(위임·검증)를 시작한다. `active`가 이미 있거나(중복 launch — 진행 중인 anchor를
   덮어쓰고 in-flight advisor를 고아로 만든다) `anchor`가 비어 있으면(arm되지 않은 유령 loop) 확장을
   **차단**한다(`decision: block`) — 상태를 건드리지 않아 돌던 loop가 무사하다.
2. **prompt 제출은 event가 아니다** — prompt 경로에 hook이 없다(결정 15). 타이핑된 사용자 turn·AskUserQuestion
   응답·task-notification·scheduled wakeup·ESC 어느 것도 loop 상태를 건드리지 않고, armed loop는 다음
   정지에서 재개된다.
3. **Stop 자동 종료** — advisor 완수 판정·anomaly failsafe 시 `active`를 지운다(위 핵심 loop).
4. **`/ploop:off`** (off_command) — loop를 **일시정지**한다: `active`만 지우고 round
   상태(ledger·audit-history·round_start_line)는 보존해 `/ploop:on`이 이어받게 한다. background advisor
   in-flight 중에도 무조건 멈추도록 `advisor_running`도 지운다. 종료가 아니라 종료 notice는 없다. `active`가
   없으면(미실행·이미 off) **차단**한다.
5. **`/ploop:on`** (on_command) — **범용 wake button**이다: stale handoff/gate transient(token·running·
   advice·narration)를 지우고 `phase`를 `fresh`로 정규화(token이 arm된 적 없는 round를 다음 정지가
   판정하지 않게)하고 이상 counter를 reset하되 audit-history·round_start_line·round는 병합이 보존한 뒤 `active`를 다시
   쓴다. off·anomaly failsafe·예외(ESC·API error·session limit)로 멈춘 stuck loop까지 무엇이든 깨운다(active여도
   차단하지 않는다). 재개 불가는 딱 둘 — `anchor.md`/`loop.log` 부재(재개할 loop 없음)와 `phase ==
   converged`(advisor 완수 인증 = 진짜 완료; 새 anchor를 launch) — 이때만 **차단**한다.

**anchor 정박은 세 겹이다.** 셋 다 anchor *text*의 보존·주입이다 — "흐려지면 anchor.md를 다시 읽어라"류
pointer는 두지 않는다(agent가 drift를 자각해야 작동하는데 goal drift는 점진적이라 자가감지되지 않는다).

1. **외부 보존(mechanism 1)** — launch hook이 anchor를 `anchor.md`에 기록한다. transcript와 독립이라 main이
   어떻게 compaction되든 원본이 보존된다. advisor가 감사마다 읽고, mechanism 2가 재주입 소스로 쓴다.
2. **launch skill 본문 re-inject** — `/ploop:launch` skill 본문은 loop notice와 `<ANCHOR>` 원문을 담고, skill
   본문은 auto-compact 후에도 re-inject되므로(skill당 앞 5,000token·합산 25,000token 예산) anchor handoff
   text가 main context에 남는다(main session은 custom system prompt를 못 받지만 skill re-inject가 그
   자리를 메운다).
3. **mechanism 2(PostCompact + anchor text inline)** — `PostCompact`가 `_compacted`를 touch하면 다음
   Stop이 그 round directive에 **anchor 원문을 recency 위치에 inline**한다(`format_directive`의
   `anchor_text`). re-inject(2)는 5,000token cap에 잘리고 원래 깊이에 남는 반면, 이것은 discrete한
   compaction event마다 anchor 전문을 무조건 recency에 박는다. main session `PostCompact`는 확실히 fire한다.

---

## Hooks

| Hook | Matcher | 시점 | 동작 |
|---|---|---|---|
| **UserPromptExpansion** | `ploop:launch` · `ploop:off` · `ploop:on` | slash command 확장(제출 전) | launch: round reset + `anchor`·`active` 기록 + candidates 경로를 `additionalContext`로 배달(결정 21) — `active` 존재·빈 `anchor`·prerequisite(nested cap `<5`·`autoCompactEnabled`·`alwaysThinkingEnabled`) 미충족이면 차단(배달 없음) · off: `active` 삭제(round 상태 보존, in-flight 무관) — 비활성이면 차단 · on: `phase`→`fresh` 정규화·counter reset(history 보존) + `active` 기록(stuck·active도 wake) — `anchor`/`loop.log` 부재·`converged`면 차단 |
| **PostCompact** | (전체) | compaction 후 | `compacted` marker touch (Stop이 mechanism 2로 anchor text 재주입) |
| **PreToolUse** | `Agent` | main이 Agent 호출 | `advisor` 호출이면 1회용 token 검사 → 허용(소비 + `advisor_running` set) 또는 `exit 2` deny(round당 audit 1회 rate limit) |
| **Stop** | (전체) | main이 종료 시도 | active gate → **background gate**(`background_tasks`: subagent·workflow·running shell 조용히 대기, monitor·비running·그 외 통과) → **in-flight guard** → narration append → 판정(보고/token/오작동/working/bare) → `exit 2`+stderr(standing directive, 종료 시엔 종료 notice+log recap) 또는 `exit 0`(허용) |
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
   trigger는 Stop hook이다. advisor·narrator만 subagent로 격리해 구독 안전성을 얻는다 — anchor의
   지휘(orchestration)는 원래 main context에서 일어나므로 별도 operator subagent는 격리 이점 없이
   부채만 남겨 제거했다. main은 orchestrator다(launch rules가 세운다): 작업은 위임한 agent에서
   소비되고 main context에는 지휘만 남는다 — depth 0의 보장(PostCompact 확실 fire·동기
   Agent 호출·전체 hook 수명주기)이 작업이 아니라 지휘에 필요한 전부라 배치가 정확히 맞는다.
2. **hook은 directive, 실행은 Agent tool.** Claude Code hook은 stdout/stderr/exit code로만 통신해 tool call을
   fire하지 못하므로, Stop이 `exit 2`+stderr로 main에게 standing directive — narrator 호출(무조건)과
   advisor 호출(main의 판단) — 를 주입하고 main(LLM)이 Agent tool로 실행한다. 이 간접 한 단계가 ploop
   hook 설계의 본질이다. 호출 구문은 hook이 verbatim으로 조립하고, advisor 호출의 남용은 PreToolUse
   token gating(결정 9)이 round당 1회로 제한한다.
3. **loop 상태는 hook 단독 소유.** advisor는 보고(또는 완수 token)를 `advice.md`에 Write만 하고 hook이 그
   파일을 읽어 5field ledger를 기록한다(`{**ledger, ...}` 병합, 미언급 field 보존). `advice.md`가 유일 channel이라
   transcript를 scrape하지 않는다 — 단일 작성자라 동시성 문제가 없고 Agent tool_result 형식(메타
   envelope·prose) 의존이 통째로 사라진다.
4. **작업 transcript = main transcript, action-history는 narrator 위임 — cadence는 per-stop.** main이
   anchor를 소유·지휘하므로 action(위임·검증 포함)과 소집이 모두 main transcript에 있다. **hook은
   transcript를 parsing하지 않는다** — `round_start_line`(ledger 소유)부터 정지 시점까지를 순수 line
   cut으로 잘라 `round.jsonl`에 저장하고, main이 매 round narrator를 relay해 그 파일 전체를 해석·서술
   시킨다(directive step 1). 이 정지 시점엔 이번 정지의 directive가 아직 append되지 않았으므로
   `[round_start..end]`가 정확히 이번 round다. **per-stop cadence가 세 가지를 동시에 산다**: slice가
   항상 한 round라 거대-slice chunking 기계가 원천 불필요하고, loop.log가 실시간 flight recorder로
   유지되어 docent·종료 recap·감사 입력이 한 파일로 수렴하며, 사용자 steering·main의 반박이 narration을
   타고 다음 감사에 닿는 합의 지연이 종전과 동일한 1-stop이다. message 형식 의존이 없다는 성질은
   그대로다 — slice가 연속 구간이라 compaction 요약·steering이 그대로 담기고 경계 오인 잘림이
   구조적으로 불가능하다(실패 방향은 "넓게"). 사용자 지시는 anchor보다 상위 권위이므로 narrator가
   그대로 서술해 advisor에 전달하며, steering은 round를 reset하지 않는다. narrator relay 누락은
   anomaly가 아니라 degrade다("무서사 round" — 수용한 한계).
5. **활성화 gate + 의미론적 수렴(숫자 상한 없음) + 수동 pause/resume.** `/ploop:launch`가 `active`를 써야
   Stop이 loop를 돌고, 종료는 round 상한 없이 advisor 완수 token·anomaly failsafe로만 일어난다(audit-history가
   파일이라 context를 안 차지 — anchor도 동일). 이 자동 종료와 별개로 사용자는 `/ploop:off`로
   일시정지·`/ploop:on`으로 재개한다(위 활성화 lifecycle).
6. **anchor 정박 — mechanism 1 + 2.** 외부 보존(`anchor.md`)으로 원문이 디스크에 영속하고, `PostCompact`
   marker를 소비한 Stop이 compacted round의 directive에 anchor 원문을 inline한다(mechanism 2 — discrete
   compaction event에 무조건 text 주입). advisor도 감사마다 anchor를 읽어 anchor 좌표 판정을 내리므로
   main은 간접 정박되고, launch skill re-inject가 handoff text를 보존한다. "매 round
   pointer"는 이들과 중복이라 두지 않는다(irreducible).
7. **advisor 분석 입력은 5-section 순서.** advisor는 role·anchor·action-history·audit-history·instructions
   순서로 맥락을 쌓는다(판정 대상은 **"main agent"의 상태 vs anchor**). candidates 파일이 비어있지
   않으면 audit-history 다음에 그 경로 1행이 조건부로 붙는다 — 비어있음 판정은 hook 코드의 결정론이라
   standalone ploop(응고 계약 없는 사용)의 advisor 입력은 기억 domain을 모른 채로 남는다. hook이
   advisor를 직접 못 부르므로 같은 순서를 directive의 advisor 호출로 재현한다 — role은 system prompt,
   anchor·audit-history·instructions는 파일, action-history는 **loop.log(축적 서사) 다음 narration.md
   (직전 round의 신선분)**다. narrator는 더 이상 advisor 호출에 inline되지 않는다 — main이 매 round
   직접 돌리고(결정 4) advisor는 파일만 읽으므로 tree가 depth 1에서 닫힌다. **directive는 두 Agent
   호출을 verbatim으로 작성해 넘기고 main은 relay만 한다** — LLM이 구성할 게 없어 가장 결정론적이다.
   정박 대상은 session 최초 prompt가 아닌 `/ploop:launch` handoff(`anchor.md`)다 — launch hook이
   인자를 verbatim capture하므로 원문과 정확히 일치한다.
8. **단일 model `opus[1m]`(main·advisor).** 추론 최대화와 compaction 빈도 감소가 같은 선택으로 수렴한다.
   narrator는 원본 slice를 해석해 서술하므로 `sonnet[1m]`/`medium`이다(`[1m]`은 대형 round slice
   수용). main은 session model이라 사용자가 `opus[1m]` 실행을 권장한다.
9. **advisor 호출은 round당 1회(PreToolUse token gating).** 소집 시점은 main의 판단이지만, 구문을
   벗어난 호출 — directive의 5-section verbatim 대신 main 자기 말이 가거나 한 round에 감사가 중복되는
   것 — 은 `advice.md` channel을 오염시킨다. 매 armed 정지가 1회용 token을 세우고 PreToolUse(matcher
   `Agent`)가 token이 있을 때만 통과시킨다(narrator는 read-only leaf라 gating 안 한다) — 소비 후 재호출은
   다음 정지가 재인가할 때까지 거부되므로, 보고에 대한 반응이 서사화된 뒤에야 재감사되는 순서가
   부수적으로 강제된다. stale token은 launch reset·`/ploop:on` 정규화가 지운다. **verdict의
   provenance도 이 token이 보증한다**: 미소비 round의 report 파일은 gate를 지난 advisor의 것이
   아니므로 판정에서 제외된다 — main이 token 문자열을 알아내 자기인증하는 우회로가 구조적으로
   닫힌다. token 미소비 정지의 판정(working/bare)은 결정 14·24가 소유한다.
10. **advisor·narrator 호출은 동기(`run_in_background=false`).** Agent tool은 background가 기본이라
    (2.1.233 실측: param 존속, "Agents run in the background by default … pass false only when your
    very next action depends on the result" — 정확히 이 두 호출의 경우다) background 호출은 산출 없이
    acknowledgement만 돌려준다. directive가 두 호출을 모두 `run_in_background=false`로 작성해 동기
    실행을 지시한다 — 그래야 advisor가 정지 전에 `advice.md`를 남기고 narration이 같은 round에 축적된다.
    일부 실행 context는 이 param 자체를 omit한다(번들 실측 2026-08: "run_in_background … are
    unavailable here") — 그 환경에서 호출이 실패하면 main이 param 없이 재시도해 background로 돌고,
    in-flight guard(결정 13)·background gate(결정 16)·완료 알림이 순서를 흡수한다(graceful). 빈
    출력·background 전환은 결정 14·13이 처리한다.
11. **logging: entry 2형 — `[[ Round N ]]` 서사와 `[[ Audit K ]]` 보고.** round 서사는 그 round를
    narrator가 서술한 다음 정지에 append되고(한 정지 지연 — narration은 다음 round 초입에 생산된다),
    감사 보고는 읽힌 정지에 전문 그대로 append된다(완수 token 같은 기계 신호는 log에 안 남는다).
    보고가 소집 round의 서사보다 한 위치 앞서는 시간 skew는 buffering 없이 수용한다 — 보고는 자기
    내용으로 열리고 다음 서사가 반응을 설명하므로 독해가 무결하다. 번호는 각각 ledger의 `round`
    counter와 `advice_history` 길이다. advisor도 같은 log를 입력으로 받아 자기 직전 보고에 대한 main의
    반응·반박을 그대로 본다. 이 log가 turn의 유일한 완전 기록이라 launch가 anchor 원문(`[[ ANCHOR ]]`
    header)으로 새로 시작해 한 anchor가 log 하나를 소유한다.
12. **plugin 영역만, `settings.json` 불간섭.** 활성화는 `/ploop:launch` handoff이고 anchor 없이는 아무것도
    fire하지 않는다. 프로젝트 CLAUDE.md·rules는 main·advisor·narrator가 모두 상속한다(차단이 all-or-nothing이라
    코드 작업에 규칙이 필요한 main을 우선; advisor·narrator 상속은 약한 오염 여지).
13. **advisor in-flight guard(background 전환 cascade 차단).** advisor를 `run_in_background=false`로 지시해도
    사용자가 실행 중 advisor를 background로 보낼 수 있고, 그때 그대로 재주입하면 advisor가 매 정지 **증식**한다.
    PreToolUse가 `advisor_running`을 set하고 cycle 안에서는 SubagentStop만 이를 clear하며, Stop은 marker가
    있으면 in-flight로 보고 `exit 0` 대기한다. background 전환된 advice는 유실될 수 있으나 cascade는 확실히
    차단된다. **수용한 trade-off**: SubagentStop 누락 시 marker leak로 stuck-active가 되나 `/ploop:on`이
    정리·정규화해 복구한다.
14. **이상 신호는 1회 교정 후 재발 시 정직한 사유로 종료(anomaly cap = 2) — 침묵 2회는 main의 비상
    종료권이다.** loop의 두 참여자(advisor·main)는 신뢰할 수 없는 LLM이라, 첫 이상엔 1회 교정 기회를
    주고 **연속 2회면**(종류 무관) 실제 사유로 종료한다. **단일 `anomalies` counter**가 어떤 이상이든
    증가시키고 **audit round와 working 정지에 0으로 reset**된다 — malfunction·bare가 교대해도 누적돼
    cap에 닿고, 며칠 간격의 무관한 ESC 2회는 절대 합산되지 않는다. (a) advisor가 돌고도 보고를 안
    쓰면(오작동) RETRY notice로 재소집을 지시한다 — round는 시간 구간이라 동결 없이 전진한다. 2회면
    오작동 종료. (b) directive가 bare 정지로 미응답이면(main의 침묵 또는 사용자가 끊은 turn) **권한
    분할**(완수 인증권=advisor·작업권=main)을 고지하며 재주입한다(DECLINE notice) — **이 notice가 침묵
    비상구("한 번 더 무응답이면 인증 없이 종료, `/ploop:on` 재개 가능")를 공개하는 유일한 지점이다**:
    평시 directive에 실으면 과신 main의 우회를 상시 광고하고, 영영 숨기면 두 번째 침묵이 informed
    choice인지 사고인지 구분 불능이 된다 — 결정의 순간에만 공개한다. 거부 근거는 slice→narrator로
    advisor에 닿아 타당한 거부는 advisor 완수 판정으로 관철되고(in-band 사용자 종결 지시도 이 경로),
    2회면 **완수 인증 없는 비상 종료**다 — 무한 루프 방지가 이 경로의 존재 이유이며, 완수로 위장하지
    않는다. 미소비 token은 ESC로 끊은 turn에서도 남으므로, main에 노출되는 문구는 주체를 특정하지
    않는 중의적 표현을 쓴다. 종료는 항상 실제 사유로 보고하고 `/ploop:on`으로 재개 가능하다.
    **수용한 한계**: bare 정지는 round를 전진시켜 `round.jsonl`을 침묵 slice로 덮어써 직전 round
    narration 1건이 유실될 수 있으나 audit-history(파일)는 무손실이다.
15. **종료·일시정지는 명시적 신호만 — prompt 경로에 hook이 없다.** loop를 끝내는 신호는 advisor 종료
    token과 결정 14 failsafe뿐이고(자동 종료), 사용자는 이와 별개로 `/ploop:off`·`/ploop:on`으로
    pause/resume한다(상태 보존). UserPromptSubmit 경로는 task-notification·scheduled wakeup 같은 system
    prompt(`promptSource: system`)도 타고 launch가 background Agent 전개를 권장하므로, prompt를 개입으로
    취급하면 loop가 자기가 권장한 pattern에 죽는다 — 타이핑된 사용자 turn도 개입이 아니다(AskUserQuestion 응답·
    mid-turn 지시는 참여, in-band 종결은 결정 14 합의 경로로 advisor에 닿음). ESC 감지도 두지 않는다: interrupt는
    hook event가 없어 transcript sentinel 판독이 필요한데 형식 의존을 하나 더 심는다 — ESC는 turn만 끊고
    armed loop는 다음 정지에서 재개되며 공식 일시정지는 ESC 후 `/ploop:off`다. 이 정책으로 UserPromptSubmit
    hook이 통째로 사라졌다.
16. **directive는 foreground·background가 모두 빈 정지에만 주입 — `background_tasks` gating.** round의
    판정과 다음 지침은 main이 위임 파도를 회수한 뒤라야 유효하다. foreground가 비었다는 것은 Stop이 fire한 것 그 자체이고, background는
    Stop 입력의 공식 배열 **`background_tasks`**(v2.1.145+; docs 페이지에서는 빠졌으나 2.1.233 번들에 생존 —
    실측 2026-08)로 읽는다 — harness는 background가 남아 있어도 session을
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
    `Monitor`(session 수명 차선)로 돌린다 — ambient가 shell 차선에 살아 있는 한 round 판정이 유예되는 문제는
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
    Code 설정에 mechanism이 걸려 있고 Claude Code 변경이 그 default를 뒤집어 환경을 silent하게 바꿀 수
    있다(nested subagent default 표류 5→1→3 — §왜 subagent인가). `/ploop:launch`가 세 요구를 검사해 미충족을 모아 block하고 각
    settings.json fix·재시작·relaunch를 한 알람으로 안내한다: ① nested subagent depth pin
    `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH >= 5`(orchestration 환경 계약 — loop 기계는 depth 1로 닫힌다),
    ② `autoCompactEnabled`, ③ `alwaysThinkingEnabled`
    (permission mode·autoMemory·model은 강제 안 함 — owner 결정). **provision↔enforcement 분리**: settings
    쓰기는 `claude-automata init`의 본업(PREREQUISITES + env `"5"`)이라 거기서 심어 커밋된
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
20. **deadline — 시계는 정보(양 참여자 배달), 집행은 advisor.** anchor 최상단 frontmatter
    `deadline:`(ISO 8601, timezone 필수)을 Stop hook이 directive 조립 시점에 한 번 읽어 status 한 줄
    (`deadline: 2h 13m remaining`·`expired 23m ago`·parse 불가 시 unreadable로 원문 표면화 — 조용한
    무장 해제는 거짓 안심이다)을 **두 위치에** 싣는다: directive header(소집 시점을 정하는 main의 결정
    변수)와 advisor prompt(관측 공백 보전 — advisor는 Bash가 없어 시계를 못 읽는다). 미선언 anchor는
    비용 0. **expired는 directive의 "계속 작업" 분기를 닫고 소집 자체를 지시로 만든다** — 마감 판단
    (잔여 내 wrap-up 조율, 경과 시 종료 — instruction 판단 절이 명시)은 여전히 advisor의 mandate다.
    기한 종결은 전용 token(`DEADLINE_EXPIRED_…`)으로 닫혀 완수 인증과 사유가 분리된다 — 종료를
    위장하지 않는다는 결정 14의 원칙이 hook의 cause 문자열까지 관통한다.
    threshold 자동 off는 기각했다: off는 무통보 인간 전용 pause라 마지막 시간(정확히 wrap-up 창)을 절단하고,
    인간 pause와 기계 만료를 같은 상태로 접어 구별 불능을 만들며, 결정 19가 폐기한 코드 단속을 재도입해
    종결 권위를 이원화한다. 마감을 넘긴 기절은 heartbeat(결정 19)가 깨워 다음 stop에서 advisor가 경과를
    본다 — 잠은 heartbeat가, mission은 deadline이 상한하고, 집행은 둘 다 advisor다.
21. **queue 주소는 기계가 배달한다 — 지시와 같은 turn에.** launch skill 본문은 candidates 축적을
    지시하므로, launch hook이 arm 성공 경로에서 `UserPromptExpansion`의 `additionalContext`(공식
    hook 계약 — 확장된 prompt와 나란히 실린다)로 경로를 함께 배달한다. 차단 3종과는 배타다. 주소가
    첫 Stop에야 도착하면 round 0의 지시는 지시대상 없는 dangling reference가 되고, main은 그것을
    자기 경로로 해소한다 — 그러면 경로를 소유한 기계 전부(advisor 입력의 조건부 라인, 종료 notice의
    drain, 다음 launch의 reset)가 빈 파일을 읽는 채로 정상처럼 보인다. 관측 신호가 없는 divergence라
    "첫 directive에서의 self-healing"(main의 자발적 이주에 의존)으로는 bound되지 않는다. directive의 상시
    라인은 유지 — launch는 최초 공급, directive는 compaction 이후의 재공급으로 역할이 갈린다.
    `/ploop:on`·`/ploop:off`는 배제한다: 두 skill 본문은 candidates를 지시하지 않아 해소할 참조가
    없고, 배달 없는 배달은 text의 단조 증가다.
22. **advisor는 완수 gate다 — per-round 소집 폐지 (2026-08 재설계).** 종전 advisor는 매 round "미고려
    영역"을 도출하는 ideation engine이었다 — 완료 조건 없는 purpose anchor에 맞는 형태인데 실사용
    100%가 mission이라, 주 산출물이 "지난 round 작업의 결함 찾기"가 되는 복잡도 재귀와, 며칠짜리
    mission에서 과거 판단 재고의 실효성 소멸을 실측했다. 재정의: advisor는 anchor 좌표를 인용한
    판정만 하는 verifier이고(root 검증자 계약의 시행 — 좌표 없는 지적 금지·상태가 서사를 이김·독립
    gate 통과 증거는 재검증 대상이 아님), 소집은 main의 판단이며(완수 주장 또는 자발 감사 — 같은
    instruction이 두 용례를 덮는다: 미완이면 미달 목록, 완수면 token), main은 보고를 지시가 아닌
    관찰로 소비한다(채택·반박은 main의 판단, 반박은 narration을 타고 다음 감사에 닿는다). **침묵 종료
    (B안 — main 자기인증)는 기각했다**: 감사 여부를 main의 확신이 정하면 과신 표본일수록 gate를
    우회하는 역선택이고, C(advisor 서명)와의 비용 차이는 mission당 호출 1회다. 침묵 2회는 비상
    종료권으로 보존된다(결정 14). purpose anchor는 이 instruction 밖이다 — 부활 시 자기 cadence
    설계가 선행 과제다(define-purpose는 인간 종결 반영구 loop로 동작).
23. **narration은 per-stop, narrator는 main이 직접 호출한다.** 감사가 드물어지면 "마지막 감사 이후
    전체"가 한 slice가 되어 narrator context를 넘을 수 있다 — per-stop cadence는 slice를 구조적으로
    한 round로 bound하고, loop.log를 실시간 flight recorder로 유지하며(docent·recap·감사 입력의 단일
    소스), 합의 지연(steering·반박 1-stop)을 보존한다(결정 4). narrator가 advisor 호출에서 빠지면서
    advisor는 아무도 spawn하지 않는다 — loop 기계의 nesting 의존이 소멸하고(§왜 subagent인가) advisor
    toolset에서 `Agent`를 disallow해 봉인한다. 비용은 stop당 sonnet 1회 — 폐지된 stop당 opus-max
    구독보다 한 자릿수 작다.
24. **bare 정지는 transcript line delta로 판정한다.** failsafe의 과녁은 침묵(tool 활동 없는 무응답
    정지)이지 소규모 작업이 아니다. 정지 간 line 증가가 threshold(T=15) 이하이고 transcript가 읽혔을
    때만 bare다 — round_start_line을 ledger가 이미 소유하므로 신규 의존이 0이고, 결정 4의 금지선
    (message 형식 parsing)이 아니라 slicer와 같은 "line 단위 append-only" 구조 의존이다. T는 실측이다
    (2026-08, 2.1.233·thinking on: text-only turn 1–9 line, 최소 tool turn 23 line — 두 대역 사이):
    `docs/research/stop-turn-line-footprint-2026.md`, 표류 시 재측정(audit-harness-deps). 오판은
    양방향 무해다 — 작업→bare는 DECLINE nudge 1회(다음 working 정지에 reset), bare→작업은 failsafe
    1 round 지연, 판독 불가 transcript는 working으로(인내 방향). **수용**: narrator relay만 하고 멈추는
    정지는 tool turn이라 working으로 읽힌다 — 1-tool 작업 round와 line 수로 구분 불능이며, 건강한
    소규모 round의 오판 종료가 정체 zombie의 지연 검출보다 큰 해악이라 이쪽을 택했다.

---

## 기술 risk

설계는 성립하나 live tree 없이 unit test할 수 없던 항목들이다. 모두 **graceful degrade**한다.

1. **Stop block cap.** Claude Code는 Stop hook이 **연속** N회 종료를 막으면 강제 종료하나
   (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, 기본 8 — docs 미기재, 2.1.233 번들 생존 실측 2026-08), 이
   counter는 생산적 작업(tool-use) turn마다 0으로 reset된다.
   ploop은 매 round narrator relay·작업을 하므로 걸리지 않고, 무진전 bare 정지는
   failsafe(결정 14)가 cap보다 먼저(2회) 끝낸다 — cap은 backstop으로만 남는다. advisor가 완수를 안 내고 main이
   무한히 **일하는** 생산적 무한 loop만 이 cap도 못 막으므로(작업이 reset) 그땐 deadline과 `/ploop:off`가 수단이다.
2. **transcript 형식 가정.** hook은 transcript를 parsing하지 않는다(결정 4). 유일한 의존은
   **transcript가 line 단위 append-only라 line 번호가 안정적**이라는 것 하나다(compaction도 append) —
   형식 field가 아니라 파일 구조이고, slice cut과 bare 판정(결정 24)이 같은 구조 하나를 딛는다.
   어긋나면 slice는 "넓게"로, bare 판정은 T 재측정으로 degrade한다.
3. **main의 지시 순응도 — risk로 취급.** main이 directive의 narrator relay를 빼먹거나(무서사 round로
   degrade) 완수 없이 소집을 영영 미룰 수 있다(생산적 무한 loop — risk 1과 동일 상한: deadline·off).
   bare 무응답 1회는 권한 고지 + 비상구 공개로 재유도되고 2연속이면 failsafe가 무결하게 닫는다(결정 14).
4. **PreToolUse 발동·session 일치** — 자발 호출 gating은 PreToolUse가 main의 Agent 호출에 발동하고
   session_id가 Stop과 같아야 성립한다. 미발동이면 token이 소비되지 않아 매 정지가 decline으로
   오판되고 2round failsafe로 닫힌다 — session은 무손상, `/ploop:on`으로 재개 가능(graceful).
5. **SubagentStop `agent_type`은 공식 문서상 plugin agent에 scoped(`ploop:advisor`)다** —
   이 repo의 실측은 bare(`advisor`)도 기록한 바 있어 2형 matching으로 관용한다(PreToolUse의
   `subagent_type`은 scoped 정확 일치). 표류하면 in-flight marker가 leak해 stuck-active가 되고
   `/ploop:on`이 복구한다(결정 13의 수용 trade-off와 동일 경로).


---

## 수용한 한계

- **loop.log는 무상한 성장한다** — advisor가 감사마다 log 전문을 action-history로 읽으므로 월 단위
  loop에서 비용이 누적된다(narration이 이미 압축본이라 원본 transcript보다 한 자릿수 작지만 무상한은
  같다). windowing은 관측 후 별도 작업이다.
- **중간 과정의 외부 감사는 자발 소집에 의존한다** — per-round 소집 폐지(결정 22)로 요구사항 오독은
  완수 주장 시점에야 확실히 걸리고 그때의 수정 비용이 최대다. per-round 감사의 순가치가 실측 음수라
  수용했고, 완화는 자발 중간 감사와 deadline이다.
- **flight recorder의 완전성은 main의 narrator 순응에 의존한다** — relay 누락 round는 무서사로
  남는다(log에 구멍, anomaly 아님).
- **session hard-death에는 drain notice가 닿지 않는다** — candidates의 종료 protocol 운반체는 종료
  notice뿐이라, process 사망 시 잔량은 유실된다. "수시로 비워라"(launch rules)가 손실 창을
  bound한다 — 작업기억은 lossy가 정의다.
- **orchestrator 정체성의 재주입은 launch 본문 re-inject 1겹이다** — anchor의 3겹 정박과 비대칭.
  compaction 후 정체성 표류는 관측 항목이다.
- **background가 상시 점유되면 advisor가 소집되지 않는다**(결정 16의 뒷면) — 위임 파도가 영원히
  비지 않는 운용에는 기계 보장이 없다. rules의 파도-정지 rhythm이 자연 유도하는 것으로 수용한다.
- **candidates 잔량 판정은 감사 시점 단면 snapshot이다** — advisor는 queue의 추이를 갖지
  않는다. 표면화의 근거는 "쌓여 있고 처리되지 않았다"뿐이고 그 이상의 판단은 main 몫이다.
- **worker 내부 행위는 advisor에 비가시다** — narrator는 main transcript(지휘·주장)만 서술한다.
  결함이 아니라 신뢰 model의 이동이다: 산출의 판정은 관측이 아니라 gate(독립 검증·CI)가 소유한다.
- **docent의 해설은 기록 기반 추론이다** — 기록에 없는 "왜"의 재구성은 오귀속할 수 있다. 교리의
  관측/추론 구분·round 인용이 그 경계를 표시하고, compaction 이후에는 main도 그 기억을 갖지 않으므로
  기록이 최선의 증인이라는 전제는 advisor loop와 공유한다.
- **지난 session 기록은 GC 없이 축적된다** — disk의 기록은 무상한 성장한다. 열거는 launch
  directory 범위로 좁아졌고 완료 anchor는 flag로 제외 가능하지만, 기록 자체의 windowing·정리는
  관측 후 별도 작업으로, loop.log 성장과 같은 계열의 한계다.

---

## 언어와 prompt

언어 정책은 repo 전역 규약이다 — 정본은 root [ARCHITECTURE.md](../../ARCHITECTURE.md)의
언어·prompt 정책 절. ploop 특이사항만 남는다: agent·skill prompt와 advisor instruction은
단일 `.md`이고, hook 주입 message(round directive)는 `prompt.py`가 조립한다(영어 — 코드 발신 lane).
worker 위임 prompt의 영어 규칙은 launch rules가 세운다. 감사 보고·narration은 한국어로 남는다:
main·소유자가 `loop.log`로 읽고 narration은 사용자 발화를 원문 보존한다.

---

## 파일 map

```
ploop/
├── .claude-plugin/plugin.json        # manifest
├── agents/                           # loop tier(advisor·narrator — 둘 다 main이 depth 1로 직접 호출)
│   ├── advisor.md                    # 완수 auditor 역할 + 5-section 읽기 순서 (Write: 보고→advice.md)
│   └── narrator.md                   # round slice 파일 → round 서사 (Read: round.jsonl · Write: narration→narration.md)
├── prompts/instruction.md            # advisor 완수 판정·보고 지침 (anchor 좌표 의무·완수 token)
├── skills/define-mission/SKILL.md    # /ploop:define-mission — 목표(goal) anchor 작성 (loop와 비연결, 수동 handoff)
├── skills/define-purpose/SKILL.md    # /ploop:define-purpose — 목적(purpose) anchor 작성 (loop와 비연결, 수동 handoff)
├── skills/docent/SKILL.md            # /ploop:docent — 기록 해설 교리 (read-only 질의 표면, 별도 session)
├── skills/launch/SKILL.md            # /ploop:launch — 완수 gate notice + orchestrator rules + 응고 계약 + anchor handoff (anchor 저장·활성화는 launch hook)
├── skills/off/SKILL.md               # /ploop:off — 일시정지 조용한 고지 (일시정지는 off_command hook)
├── skills/on/SKILL.md                # /ploop:on — 재개 확인 고지 (재개·정규화는 on_command hook)
├── hooks/hooks.json                  # UserPromptExpansion(launch·off·on) + PostCompact + PreToolUse(Agent) + Stop(gate + asyncRewake heartbeat) + SubagentStop
├── bin/ploop-hook                    # uv 가용성 check wrapper + heartbeat의 3h 상주(sh가 잔다 — uv는 exec돼도 상주)
├── src/                              # hook 구현 (runtime 의존성 없음)
│   ├── main.py                       # hook entrypoint(stop·pre_tool_use·heartbeat_arm·heartbeat_fire·subagent_stop·mark_compaction·launch·off_command·on_command)
│   ├── docent.py                     # docent resolver — session 열거·기록 경로 해석 (read-only, `docent` console script)
│   ├── state.py                      # Workspace(session 파일 경로의 단일 창구) + 5field ledger(advice_history·round_start_line·anomalies·phase·round) + phase 상수 · preserve-by-default load/저장
│   └── prompt.py                     # audit-history format + standing directive 조립(narrator·advisor verbatim 호출·deadline 양방 배달)
└── tests/                            # 구현 독립 (stdin/stdout/disk 구동)
```
