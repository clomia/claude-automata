# ploop — 아키텍처

ploop은 **advisor loop** — 격리된 advisor가 매 라운드 main이 고려하지 못한 영역을 surface해
결과 신뢰도를 극한까지 끌어올리는 자율 루프 — 를 Claude Code의 **nested subagent** 위에서 구현한
플러그인이다. 통합 지점은 Stop 훅이고, 루프의 main 역할은 세션 에이전트 자신이다.

---

## 용어

- **advisor loop** — 훅·advisor·narrator로 매 라운드 advice를 main에 주입하는 자율 루프. 이
  플러그인(`ploop`)이 그것을 구현한다.
- **main** — advisor loop의 main 역할을 하는 세션 에이전트(depth 0). anchor를 소유하는
  orchestrator로서 작업을 에이전트에 위임·검증하고 매 라운드 advisor를 호출한다.
- **candidates** — main이 승격 대기 사실·용어 후보를 측정 방법과 함께 축적하는 작업기억
  파일(승격 대기열). 승격 아니면 폐기가 대기열의 존재 이유다.
- **anchor** — main을 anchor에 붙들어 매는 SSoT. 트랜스크립트 바깥 외부 파일(`{session}_anchor.md`)에
  보존된다.
- **advice** — advisor가 라운드마다 main에게 건네는 **미고려 영역들의 리스트**. action-history 요약을
  앞머리에 포함해, main이 스스로 떠올린 영역까지 advice-history에 남아 이미 고려된 영역이 재제시되지
  않는다(history 무결성).

main은 advisor loop와 anchor 재주입으로 anchor에 **정박한다(anchored)** — 자기 확신으로
표류(drift)하지도, compaction으로 anchor를 잃지도 않는다.

---

## 왜 nested subagent인가

Stop 훅 안에서 `claude -p`를 스폰하는 가장 단순한 방법은 `--no-session-persistence`로 **별도의 임시
세션**을 만드는 자동화 패턴이라, Claude Pro/Max 구독 약관상 계정 정지 위험을 부른다(실제 차단 이력) —
API 요금제 전용이 된다. 반면 `Agent` 툴 subagent는 **모든 요금제에서 지원되는 정식 기능**이고(메인
세션과 quota 공유), 서브에이전트가 다시 서브에이전트를 spawn할 수 있다(v2.1.172+, depth 5 cap). ploop은
이 정식 경로 위에서 돈다 — main이 advisor를, advisor가 narrator를 `Agent` 툴로 호출한다.

---

## Agent Tree

`main`은 사용자와 대화하는 세션(depth 0)이자 advisor loop의 수행자다. advisor·narrator는 그 아래 봉인된
서브에이전트 tier에서 돈다. 각 tier는 아래로 위임하고 위로는 요약만 반환하므로, 방대한 컨텍스트가
상위로 갈수록 압축된다.

```
main      depth 0  session     full tools    loop main: runs the anchor
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

- **advisor는 `Write`로 advice(또는 종료 토큰)만 쓰고 나머지 부작용 도구는 막혀 있다(`disallowedTools:
  Bash, Edit, NotebookEdit, Artifact`).** subagent의 최종 메시지는 커스터마이징 불가라 추론 prose가
  섞이므로(하네스 한계), advice를 `advice.md`(비보호 시스템 temp — 보호된 `~/.claude` 하위인
  `CLAUDE_PLUGIN_DATA`는 auto 모드 Write가 classifier에 막힌다)에 Write해 채팅 채널과 격리한다. `Bash`
  차단은 임의 부작용(`rm`·테스트 실행) 방지고, `Write`만 좁게 연 것은 advice 출력 채널을 위한 의식적
  완화다(전제: auto/bypass 권한 모드). 남은 read-only 도구(`Read·Glob·Grep·Web*`)로 영역을 근거 짓고
  `Agent`로 narrator를 호출한다.
- **narrator는 `Read`·`Write`만 가진 leaf** — `Agent`가 없어 트리가 그 아래로 자라지 않는다. hook이 잘라
  준 라운드 슬라이스(`round.jsonl`)를 통째로 읽어 해석하고(hook 측 파싱 없음), narration을
  `narration.md`(advisor와 동일 temp 채널)에 쓴다 — advisor가 분석 입력으로, hook이 라운드 로그로 읽는다.
  원본 슬라이스를 해석하므로 `sonnet[1m]`/`medium`이다.
- depth 2에서 트리를 닫아 depth-5 cap에 3단계 여유를 남긴다.

---

## 핵심 루프

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

종료는 의미론적 판단만 인정한다: advisor가 `advice.md`에 **종료 토큰을 Write할 때만** 수렴
종료다(`phase`→`converged` + `active` 정리). 파일 부재/빈 파일은 종료가 아니라 **오작동**이다 — 정상
advisor는 종료조차 토큰 Write로 표현하므로 안 쓴 것은 판정이 아니다(입력 동결로 재시도). 트리거가
응답되지 않은 정지(토큰 잔존 — main의 거부 또는 사용자가 끊은 턴)는 **권한 분할**로 처리한다: "루프 종료
권한은 advisor에게만 있다"를 고지하며 재주입하면, 거부의 근거 발언이 라운드 슬라이스→narrator를 타고
advisor에 닿아 타당한 거부는 advisor 종료 토큰으로 관철된다(합의 경로). 오작동·거부 모두 **연속 2회**면
정직한 사유로 종료한다(anomaly cap — 결정 14). **숫자 라운드 상한은 없다** — advice-history는 파일이라
컨텍스트를 안 잠식하고 advisor는 매 라운드 stateless하게 리셋되므로, 종료는 "더 제공할 advice가
있는가"라는 의미론적 판단에 맡긴다.

**모든 자동 종료 경로(advisor 종료 토큰 + malfunction·decline failsafe)는 main에게 정직한 사유와 함께
종료 노티스를 보낸다**(`format_end_notice`) — advice를 하나라도 surface한 턴이면 `loop.log` recap 지시를
덧붙인다(장기 anchor에서 main 컨텍스트는 여러 번 compaction되므로 로그가 턴의 유일한 완전 기록이다).
자연 종료는 종료 정지를 한 번 더 막아(exit 2) 노티스를 주입하고, 그 다음 정지는 `active`가 없어
통과한다. **이 자동 종료 동작은 노출 계약이라 불변이다.** 끝내기와 별개로 사용자는 `/ploop:off`로
일시정지·`/ploop:on`으로 재개하며(아래 활성화 lifecycle), off는 종료가 아니라 종료 노티스를 보내지
않는다.

Stop 훅은 메인 세션 정지마다 발화하므로 `active` 마커가 게이트한다. advisor·narrator의 정지는
`SubagentStop`이라 이 Stop 훅에 잡히지 않는다 — 재귀 가드가 필요 없다.

---

## 컨텍스트 경제 — nested가 `claude -p`보다 우월한 지점

main의 컨텍스트에 더해지는 것은 **① 짧은 stderr 트리거 + ② main이 읽는 `advice.md` + ③ 종료 시 1회의
로그 요약 턴**뿐이다. narrator 호출, 라운드 슬라이스·advice-history 읽기, 5-section 분석은 모두
**advisor·narrator(depth 1·2)의 컨텍스트에서** 소비돼 main에 닿지 않는다 — 슬라이스가 커도(대량 작업
라운드) 그 비용은 depth-2 narrator에 격리되고 요약된 narration만 위로 흐른다. 영역을 "짧고 명확하게
정의(irreducible)"하게 하는 instruction이 이 경계를 지킨다. advisor가 main의 사각을 보되 그 탐색 비용을
main에 전가하지 않는다.

---

## 상태와 anchor 보존

상태는 사용자 레포 바깥에 둔다(레포 비오염) — 대부분 `CLAUDE_PLUGIN_DATA`, 단 `advice.md`만 비보호
시스템 temp(위 근거). 한 세션에 하나의 anchor를 가정해 `session_id`로 키잉한다.

| 파일 | 작성자 | 내용 |
|---|---|---|
| `{session}_anchor.md` | launch 훅 (UserPromptExpansion) | anchor 정의 (외부 보존 anchor) |
| `{session}_active` | launch 훅 생성 · hook 삭제 | 활성화 마커 (Stop 게이트) |
| `{session}_loop.json` | hook | 4필드 — `advice_history`(라운드 기록, 길이=라운드 ordinal) · `round_start_line`(슬라이스 컷 오프셋) · `anomalies`(연속 이상 카운터, clean 라운드에 0 리셋) · `phase`(`fresh` 갓 launch/resume·record 스킵 → `advising` 라운드 진행·record → `converged` 수렴 완료·`/ploop:on` 거부). `{**ledger, ...}` 병합이라 미언급 필드 보존(preserve-by-default) |
| `{session}_round.jsonl` | hook | 이번 라운드 트랜스크립트 슬라이스 `[round_start..end]` (narrator가 통째로 분석) — 라인 컷이라 메시지 파싱 없음 |
| `{session}_advice_history.md` | hook | advisor 입력의 advice-history (XML) |
| `advice.md` (temp) | advisor (`Write`) | advice 또는 종료 토큰 (유일 채널) — 비보호 temp라 auto 모드 Write 승인 · main·hook이 읽음 · prose 격리 |
| `narration.md` (temp) | narrator (`Write`) | action-history 서사 (advice와 동일 채널) — advisor가 분석 입력으로 · hook이 라운드 로그로 읽음 |
| `candidates.md` (temp) | main | 승격 대기열 (자유 형식) — 트리거가 경로를 상시 안내 · 비어있지 않으면 advisor 입력에 조건부 1행 · launch만 소거(off·on·종료는 보존) · 종료 노티스가 잔량 drain을 지시 |
| `{session}_loop.log` | hook | 완결 라운드 로그 (서사 + 그 라운드의 advice) · launch가 `[[ ANCHOR ]]` 원문으로 새로 시작 · 종료 요약의 소스 |
| `{session}_advisor_token` | hook | advisor 1회 호출 인가 토큰 (Stop set · PreToolUse 소비) |
| `{session}_advisor_running` | hook | advisor in-flight 마커 (PreToolUse set · SubagentStop clear) |
| `{session}_compacted` | hook (PostCompact) | compaction 발생 마커 (Stop이 메커니즘 2로 소비) |
| `{session}_gated_shells` | hook | 교정 지시를 이미 보낸 background shell id 집합 — 같은 집합의 정지는 조용히 대기 (라운드 arm·`/ploop:on`·launch가 소거) |

**loop 상태(advice_history·phase·anomalies·round_start_line)는 hook이 단독 소유한다.** advisor는
advice(또는 종료 토큰)를 `advice.md`에 Write만 하고, hook이 다음 라운드 시작에 그 파일을 읽어
`advice_history`에 append하거나 종료 토큰이면 `phase`를 `converged`로 옮긴다. in-flight 가드를 통과한
시점이라 advisor는 이미 종료했으므로 `advice.md` 부재 = 오작동이다(종료도 토큰 Write를 요구). main도 같은
`advice.md`를 읽어 그 advice로 작업하므로 이 파일이 advice/종료의 유일 채널이자 main·hook 공통 소스다 —
단일 작성자(hook)가 ledger를 소유해 race가 없다.

**활성화 lifecycle.** Stop 훅은 메인 세션 정지마다 발화하므로 `active` 마커가 루프를 게이트한다.

1. **`/ploop:launch`** (UserPromptExpansion) — 직전 anchor의 라운드 상태를 리셋하고 `anchor.md`·`active`를
   쓴다. main이 anchor의 지휘(위임·검증)를 시작한다. `active`가 이미 있거나(중복 launch — 진행 중인 anchor를
   덮어쓰고 in-flight advisor를 고아로 만든다) `anchor`가 비어 있으면(arm되지 않은 유령 루프) 확장을
   **차단**한다(`decision: block`) — 상태를 건드리지 않아 돌던 루프가 무사하다.
2. **프롬프트 제출은 무이벤트** — 프롬프트 경로에 훅이 없다(결정 15). 타이핑된 사용자 턴·AskUserQuestion
   응답·task-notification·scheduled wakeup·ESC 어느 것도 루프 상태를 건드리지 않고, armed 루프는 다음
   정지에서 재개된다.
3. **Stop 자동 종료** — advisor 종료 판정·anomaly failsafe 시 `active`를 지운다(위 핵심 루프).
4. **`/ploop:off`** (off_command) — 루프를 **일시정지**한다: `active`만 지우고 라운드
   상태(ledger·advice-history·round_start_line)는 보존해 `/ploop:on`이 이어받게 한다. background advisor
   in-flight 중에도 무조건 멈추도록 `advisor_running`도 지운다. 종료가 아니라 종료 노티스는 없다. `active`가
   없으면(미실행·이미 off) **차단**한다.
5. **`/ploop:on`** (on_command) — **범용 wake 버튼**이다: stale handoff/gate transient(token·running·
   advice·narration)를 지우고 `phase`를 `fresh`로 정규화(다음 정지가 advisor 미실행 라운드를 record하지
   않게)하고 이상 카운터를 리셋하되 advice-history·round_start_line은 병합이 보존한 뒤 `active`를 다시
   쓴다. off·anomaly failsafe·예외(ESC·API 에러·세션 리밋)로 멈춘 stuck 루프까지 무엇이든 깨운다(active여도
   차단하지 않는다). 재개 불가는 딱 둘 — `anchor.md`/`loop.log` 부재(재개할 루프 없음)와 `phase ==
   converged`(advisor 수렴 종료 = 진짜 완료; 새 anchor를 launch) — 이때만 **차단**한다.

**anchor 정박은 세 겹이다.** 셋 다 anchor *텍스트*의 보존·주입이다 — "흐려지면 anchor.md를 다시 읽어라"류
포인터는 두지 않는다(agent가 드리프트를 자각해야 작동하는데 goal drift는 점진적이라 자가감지되지 않는다).

1. **외부 보존(메커니즘 1)** — launch 훅이 anchor를 `anchor.md`에 기록한다. 트랜스크립트와 독립이라 main이
   어떻게 compaction되든 원본이 보존된다. advisor가 매 라운드 읽고, 메커니즘 2가 재주입 소스로 쓴다.
2. **launch 스킬 본문 re-inject** — `/ploop:launch` 스킬 본문은 루프 notice와 `<ANCHOR>` 원문을 담고, 스킬
   본문은 auto-compact 후에도 re-inject되므로(스킬당 앞 5,000토큰·합산 25,000토큰 예산) anchor 핸드오프
   텍스트가 main 컨텍스트에 남는다(메인 세션은 커스텀 시스템 프롬프트를 못 받지만 스킬 re-inject가 그
   자리를 메운다).
3. **메커니즘 2(PostCompact + anchor 텍스트 inline)** — `PostCompact`가 `_compacted`를 touch하면 다음
   Stop이 그 라운드 트리거에 **anchor 원문을 recency 위치에 inline**한다(`format_advisor_trigger`의
   `anchor_text`). re-inject(2)는 5,000토큰 cap에 잘리고 원래 깊이에 남는 반면, 이것은 discrete한
   compaction 이벤트마다 anchor 전문을 무조건 recency에 박는다. 메인 세션 `PostCompact`는 확실히 발화한다.

---

## Hooks

| Hook | Matcher | 시점 | 동작 |
|---|---|---|---|
| **UserPromptExpansion** | `ploop:launch` · `ploop:off` · `ploop:on` | 슬래시 커맨드 확장(제출 전) | launch: 라운드 리셋 + `anchor`·`active` 기록 — `active` 존재·빈 `anchor`면 차단 · off: `active` 삭제(라운드 상태 보존, in-flight 무관) — 비활성이면 차단 · on: `phase`→`fresh` 정규화·카운터 리셋(history 보존) + `active` 기록(stuck·active도 wake) — `anchor`/`loop.log` 부재·`converged`면 차단 |
| **PostCompact** | `auto` | auto-compaction 후 | `compacted` 마커 touch (Stop이 메커니즘 2로 anchor 텍스트 재주입) |
| **PreToolUse** | `Agent` | main이 Agent 호출 | `advisor` 호출이면 1회용 토큰 검사 → 허용(소비 + `advisor_running` set) 또는 `exit 2` deny(자발 호출 차단) |
| **Stop** | (전체) | main이 종료 시도 | active 게이트 → **background 게이트**(`background_tasks`: subagent·workflow 조용히 대기, shell은 집합당 1회 교정 지시 후 대기, monitor·그 외 통과) → **in-flight 가드** → 종료 판정 → `exit 2`+stderr(advisor 호출 지시, 종료 시엔 종료 노티스+로그 recap) 또는 `exit 0`(허용) |
| **SubagentStop** | (전체) | subagent 종료 | `advisor` 종료면 `advisor_running` clear (in-flight 추적) |

플러그인 에이전트는 `ploop:<agent>`로 scoped 등록돼 Agent 호출의 subagent_type이 그 이름을 쓴다. 훅은
`bin/ploop-hook` 셸 래퍼를 거쳐 `uv`를 호출하고, 래퍼가 uv 가용성을 먼저 확인해 미설치 시 graceful
degrade를 한 지점에서 일원화한다. hooks.json은 exec form(`command`+`args`)으로
래퍼를 호출한다 — 경로 placeholder가 셸 토큰화를 거치지 않아 설치 경로에 공백이 있어도 훅이 죽지 않는다.

**Graceful degradation.** `uv`가 없으면 훅 spawn은 무해하게 실패한다. main은 advisor loop를 모르므로(루프는
전적으로 훅이 구동) advisor 없이 anchor만 수행하고 종료한다 — 루프는 안 돌지만 세션은 깨지지 않고, uv
설치 안내는 모든 claude-automata 플러그인이 의존하는 version-up-alert가 세션 시작에 맡는다.

---

## 핵심 설계 결정

1. **loop main = 세션 메인 에이전트.** advisor loop의 main 역할을 세션 에이전트(depth 0)가 맡고
   트리거는 Stop 훅이다. advisor·narrator만 nested subagent로 격리해 구독 안전성을 얻는다 — anchor의
   지휘(orchestration)는 원래 main 컨텍스트에서 일어나므로 별도 operator subagent는 격리 이점 없이
   부채만 남겨 제거했다. main은 orchestrator다(launch rules가 세운다): 작업은 위임한 에이전트에서
   소비되고 main 컨텍스트에는 전략·조율·검증·응고가 산다 — depth 0의 보장(PostCompact 확실 발화·동기
   Agent 호출·전체 훅 수명주기)이 작업이 아니라 지휘에 필요한 전부라 배치가 정확히 맞는다.
2. **훅은 트리거, 실행은 Agent 툴.** Claude Code 훅은 stdout/stderr/exit code로만 통신해 tool call을
   발화하지 못하므로, Stop이 `exit 2`+stderr로 main에게 advisor 호출을 **지시**하고 main(LLM)이 Agent 툴로
   실행한다. 이 간접 한 단계가 ploop 훅 설계의 본질이다. 자발 호출(경로 이탈)은 launch 스킬의 규칙 고지 + PreToolUse 토큰 게이팅(결정 9)으로 막는다.
3. **loop 상태는 hook 단독 소유.** advisor는 advice(또는 종료 토큰)를 `advice.md`에 Write만 하고 hook이 그
   파일을 읽어 4필드 ledger를 기록한다(`{**ledger, ...}` 병합, 미언급 필드 보존). `advice.md`가 유일 채널이라
   트랜스크립트를 스크레이프하지 않는다 — 단일 작성자라 동시성 문제가 없고 Agent tool_result 형식(메타
   엔벨로프·prose) 의존이 통째로 사라진다.
4. **작업 transcript = 메인 transcript, action-history는 narrator 위임.** main이 anchor를 소유·지휘하므로
   action(위임·검증 포함)과 advisor 호출이 모두 메인 트랜스크립트에 있다. **hook은 트랜스크립트를 파싱하지 않는다** —
   `round_start_line`(ledger 소유)부터 정지 시점까지를 순수 라인 컷으로 잘라 `round.jsonl`에 저장하고,
   narrator가 그 파일 전체를 스스로 해석해 main의 생각·시도·결과를 서술한다. 이 정지 시점엔 다음 라운드의
   advisor 호출이 아직 append되지 않았으므로 `[round_start..end]`가 정확히 이번 라운드다. **이 위임이 메시지
   형식 의존(`isCompactSummary` 필터·`queued_command` 승격·라운드 경계 휴리스틱·advisor-strip)을 통째로
   없앤다** — 슬라이스가 연속 구간이라 compaction 요약·steering이 그대로 담기고 경계 오인 잘림이 구조적으로
   불가능하다(실패 방향은 "넓게"). 사용자 지시는 anchor보다 상위 권위이므로 narrator가 그대로 서술해
   advisor에 전달하며, steering은 라운드를 리셋하지 않는다.
5. **활성화 게이트 + 의미론적 종료(숫자 상한 없음) + 수동 pause/resume.** `/ploop:launch`가 `active`를 써야
   Stop이 루프를 돌고, 종료는 라운드 상한 없이 advisor 종료 토큰·anomaly failsafe로만 일어난다(advice-history가
   파일이라 컨텍스트를 안 잠식 — `/goal`도 동일). 이 자동 종료와 별개로 사용자는 `/ploop:off`로
   일시정지·`/ploop:on`으로 재개한다(위 활성화 lifecycle).
6. **anchor 정박 — 메커니즘 1 + 2.** 외부 보존(`anchor.md`)으로 원문이 디스크에 영속하고, `PostCompact`
   마커를 소비한 Stop이 compacted 라운드의 트리거에 anchor 원문을 inline한다(메커니즘 2 — discrete
   compaction 이벤트에 무조건 텍스트 주입). advisor도 매 라운드 anchor를 읽어 anchor-grounded advice를
   surface하므로 main은 간접 정박되고, launch 스킬 re-inject가 핸드오프 텍스트를 보존한다. "매 라운드
   포인터"는 이들과 중복이라 두지 않는다(irreducible).
7. **advisor 분석 입력은 5-section 순서.** advisor는 role·anchor·action-history·advice-history·instructions
   순서로 맥락을 쌓는다(분석 대상은 **"main agent"**). candidates 파일이 비어있지 않으면 advice-history
   다음에 그 경로 1행이 조건부로 붙는다 — 비어있음 판정은 훅 코드의 결정론이라 standalone ploop(응고
   계약 없는 사용)의 advisor 입력은 기억 도메인을 모른 채로 남는다. hook이 advisor를 직접 못 부르므로 같은 순서를 trigger로
   재현한다 — role은 시스템 프롬프트, anchor·advice-history·instructions는 파일, action-history는 advisor가
   inline된 narrator 호출을 실행해 얻은 `narration.md`다. **트리거는 advisor의 Agent 호출을(그 안에 narrator
   호출을 inline해) 축자로 작성해 넘기고 main·advisor는 relay만 한다** — LLM이 구성할 게 없어 가장
   결정론적이다. 정박 대상은 세션 최초 프롬프트가 아닌 `/ploop:launch` 핸드오프(`anchor.md`)다 — launch 훅이
   인자를 축자 캡처하므로 원문과 정확히 일치한다.
8. **단일 모델 `opus[1m]`(main·advisor).** 추론 최대화와 compaction 빈도 감소가 같은 선택으로 수렴한다.
   narrator는 원본 슬라이스를 해석해 서술하므로 `sonnet[1m]`/`medium`이다(`[1m]`은 대형 라운드 슬라이스
   수용). main은 세션 모델이라 사용자가 `opus[1m]` 실행을 권장한다.
9. **자발 advisor 호출 차단(PreToolUse 게이팅).** main이 hook 지시 없이 advisor를 부르면 지정된 5-section
   입력 대신 main 자기 말이 가고 `advice.md`를 엉뚱한 시점에 덮어써 채널을 오염시킨다. Stop이 호출을 지시할
   때만 1회용 토큰을 세우고 PreToolUse(matcher `Agent`)가 토큰이 있을 때만 통과시킨다(narrator는 read-only
   leaf라 게이팅 안 한다). stale 토큰은 launch 리셋·`/ploop:on` 정규화가 지운다. 미호출로 정지하면 토큰이
   남아 그 라운드 advice 기록을 건너뛰고(중복 방지) decline으로 처리한다(결정 14).
10. **advisor·narrator 호출은 동기(`run_in_background=false`).** Agent 툴은 기본 async라 백그라운드 호출은
    advice 없이 acknowledgement만 돌려준다. main은 foreground이고 trigger가 두 호출을 모두
    `run_in_background=false`로 작성해 동기 실행을 지시한다 — 그래야 advisor가 정지 전에 `advice.md`를 남기고
    narration이 advisor 입력이 된다. 빈 출력·background 전환은 결정 14·13이 처리한다.
11. **로깅: 완결 라운드 단위 — 서사 + 그 라운드의 advice.** `_loop.log`의 한 엔트리는 라운드 작업의
    서사(advice 도착·반응) 뒤에 그 advice 전문이 `/ Advice`로 붙는다(라운드 0은 anchor 초기 작업이라 advice
    없음, 종료 토큰 같은 기계 신호도 로그에 안 남는다). nested 구조상 narration은 다음 advisor 호출에서
    생성되므로 엔트리는 한 정지 늦게 완결되고, 번호는 advice ordinal이라 skip 라운드에도 `advice_history.md`와
    어긋나지 않는다. advisor도 같은 서사를 입력으로 받아 자기 직전 advice에 대한 main의 반응을 그대로 본다.
    이 로그가 턴의 유일한 완전 기록이라 launch가 anchor 원문(`[[ ANCHOR ]]` 헤더)으로 새로 시작해 한 anchor가
    로그 하나를 소유한다.
12. **플러그인 영역만, `settings.json` 불간섭.** 활성화는 `/ploop:launch` 핸드오프이고 anchor 없이는 아무것도
    발화하지 않는다. 프로젝트 CLAUDE.md·rules는 main·advisor·narrator가 모두 상속한다(차단이 all-or-nothing이라
    코드 작업에 규칙이 필요한 main을 우선; advisor·narrator 상속은 약한 오염 여지).
13. **advisor in-flight 가드(background 전환 cascade 차단).** advisor를 `run_in_background=false`로 지시해도
    사용자가 실행 중 advisor를 background로 보낼 수 있고, 그때 그대로 재주입하면 advisor가 매 정지 **증식**한다.
    PreToolUse가 `advisor_running`을 set하고 사이클 안에서는 SubagentStop만 이를 clear하며, Stop은 마커가
    있으면 in-flight로 보고 `exit 0` 대기한다. background 전환된 advice는 유실될 수 있으나 cascade는 확실히
    차단된다. **수용한 트레이드오프**: SubagentStop 누락 시 마커 leak로 stuck-active가 되나 `/ploop:on`이
    정리·정규화해 복구한다.
14. **이상 신호는 1회 교정 후 재발 시 정직한 사유로 종료(anomaly cap = 2).** 루프의 두
    참여자(advisor·main)는 신뢰할 수 없는 LLM이라, 첫 이상엔 1회 교정 기회를 주고 **연속 2회면**(종류 무관)
    실제 사유로 종료한다. **단일 `anomalies` 카운터**가 어떤 이상이든 증가시키고 clean 라운드(advice가 쓰인
    라운드)에 0으로 리셋된다 — malfunction·decline이 교대해도 누적돼 캡에 닿는다. (a) advisor가 advice를 안 쓰면(오작동) 라운드를 입력 동결로 재시도(RETRY 노티스),
    2회면 오작동 종료. (b) 트리거가 미응답이면(main 거부 또는 사용자가 끊은 턴) **권한 분할**(종료권=advisor·
    작업권=main)을 고지하며 재주입(DECLINE 노티스) — 거부 근거는 슬라이스→narrator로 advisor에 닿아 타당한
    거부는 advisor 종료 판정으로 관철되고(in-band 사용자 종결 지시도 이 경로), 2회면 합의 채널 붕괴로 failsafe
    종료한다(노티스는 광고하지 않는다). 미소비 토큰은 ESC로 끊은 턴에서도 남으므로, main에 노출되는 두
    문구(재주입 노티스·failsafe 사유)는 주체를 특정하지 않는 중의적 표현을 쓴다. 종료는 항상 실제 사유로
    보고한다(오작동을 수렴으로, 거부를 고장으로 위장하지 않음) — 이제 종료가 `/ploop:on`으로 재개 가능하므로
    이르게 끝내도 손실이 없다. **수용한 한계**: decline은 라운드를 전진시켜 `round.jsonl`을 거부 슬라이스로
    덮어써 직전 라운드 narration 1건이 유실될 수 있으나 advice-history(파일)는 무손실이다.
15. **종료·일시정지는 명시적 신호만 — 프롬프트 경로에 훅이 없다.** 루프를 끝내는 신호는 advisor 종료
    토큰과 결정 14 failsafe뿐이고(자동 종료), 사용자는 이와 별개로 `/ploop:off`·`/ploop:on`으로
    pause/resume한다(상태 보존). UserPromptSubmit 경로는 task-notification·scheduled wakeup 같은 시스템
    프롬프트(`promptSource: system`)도 타고 launch가 background Agent 전개를 권장하므로, 프롬프트를 개입으로
    취급하면 루프가 자기가 권장한 패턴에 죽는다 — 타이핑된 사용자 턴도 개입이 아니다(AskUserQuestion 응답·
    미드턴 지시는 참여, in-band 종결은 결정 14 합의 경로로 advisor에 닿음). ESC 감지도 두지 않는다: interrupt는
    훅 이벤트가 없어 트랜스크립트 sentinel 판독이 필요한데 형식 의존을 하나 더 심는다 — ESC는 턴만 끊고
    armed 루프는 다음 정지에서 재개되며 공식 일시정지는 ESC 후 `/ploop:off`다. 이 정책으로 UserPromptSubmit
    훅이 통째로 사라졌다.
16. **advisor는 foreground·background가 모두 빈 정지에만 소집 — `background_tasks` 게이팅.** advisor 판정은
    main이 라운드 작업을 완료한 뒤라야 유효하다. foreground가 비었다는 것은 Stop 발화 그 자체이고, background는
    Stop 입력의 공식 배열 **`background_tasks`**(v2.1.145+)로 읽는다 — 하네스는 background가 남아 있어도 세션을
    정지시키고 완료 이벤트로 다시 깨우므로, 게이트가 삼킨 정지는 반드시 되돌아온다. 게이트는 **완료가 세션을
    깨운다고 명세가 보장하는 타입**에만 건다: `subagent`·`workflow`(완료 알림)는 조용히 대기(exit 0),
    `shell`(exit 시 재호출)은 **집합당 1회 교정 지시** 후 조용히 대기 — 완료가 없는 ambient 프로세스(서버·워처)는
    shell 차선에 속하지 않으니 정리하거나 세션 수명 차선인 `Monitor`로 옮기라는 지시다(`gated_shells` 마커가
    지시 중복을 막고 라운드 arm이 소거). `monitor`는 명세상 세션 수명 프로세스라 게이트하면 영구 교착 — 통과가
    정당한 라운드 종료다. 그 외 타입·미지 타입·필드 부재(task registry 도달 불가 — 명세상 이때만 배열이
    빠진다)는 게이팅하지 않는다: 실패 방향은 이른 advisor이지 루프 정지가 아니다. 완료를 기다려야 하는
    background는 게이팅 유형(shell·subagent·workflow)으로 두고, 서버 같은 ambient 프로세스는 `Monitor`(세션
    수명 차선)로 돌린다.

---

## 기술 리스크

설계는 성립하나 라이브 트리 없이 유닛 테스트할 수 없던 항목들이다. 모두 **graceful degrade**한다.

1. **Stop block cap.** Claude Code는 Stop 훅이 **연속** N회 종료를 막으면 강제 종료하나
   (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`, 기본 8), 이 카운터는 생산적 작업(tool-use) 턴마다 0으로 리셋된다.
   ploop은 매 라운드 advisor 호출·advice 작업을 하므로 걸리지 않고, main이 트리거를 무시하는 무진전 정지는
   decline failsafe(결정 14)가 앞서 끝낸다 — cap은 백스톱으로만 남는다. advisor가 종료를 안 내고 main이
   무한히 **일하는** 생산적 무한 루프만 이 cap도 못 막으므로(작업이 리셋) 그땐 `/ploop:off`가 수단이다.
2. **트랜스크립트 형식 가정.** hook은 트랜스크립트를 파싱하지 않는다(결정 4). 유일한 의존은
   **트랜스크립트가 라인 단위 append-only라 라인 번호가 안정적**이라는 것 하나다(compaction도 append) —
   형식 필드가 아니라 파일 구조이고 어긋나도 슬라이스가 "넓게"로 degrade한다.
3. **main의 지시 순응도 — 리스크로 취급.** main이 stderr "advisor 호출"에 매 라운드 응하지 않을 수 있다
   (in-band 사용자 지시를 근거로 정당하게 거부하는 사건 관측). 미호출 1회는 권한 고지로 합의 채널에
   재유도되고 2연속이면 failsafe가 무결하게 닫는다(결정 14).
4. **PreToolUse 발동·session 일치** — 자발 호출 게이팅은 PreToolUse가 main의 Agent 호출에 발동하고
   session_id가 Stop과 같아야 성립한다. 미발동 시 게이팅만 무효화되고 루프는 현행대로(graceful).
5. **SubagentStop `agent_type` 필드 형식은 관측 기반이다** — 실측이 bare(`advisor`)를 기록해
   scoped(`ploop:advisor`)와 2형 매칭한다(PreToolUse의 `subagent_type`은 scoped 정확 일치).
   표류하면 in-flight 마커가 leak해 stuck-active가 되고 `/ploop:on`이 복구한다(결정 13의 수용
   트레이드오프와 동일 경로).

loop main이 메인 세션(depth 0)이라 `PostCompact`는 확실히 발화하고, main이 foreground라 advisor·narrator
동기 호출이 보장된다 — subagent tier에서라면 불확실했을 두 가정을 main 위치가 보장으로 만든다.

---

## 수용한 한계

- **advice-history·loop.log는 무상한 성장한다** — advisor가 매 라운드 advice-history 전문을 읽으므로
  월 단위 purpose 루프에서 비용이 누적된다. 윈도잉은 관측 후 별도 작업이다.
- **세션 hard-death에는 drain 노티스가 닿지 않는다** — candidates의 종료 프로토콜 운반체는 종료
  노티스뿐이라, 프로세스 사망 시 잔량은 유실된다. "수시로 비우세요"(launch rules)가 손실 창을
  bound한다 — 작업기억은 lossy가 정의다.
- **orchestrator 정체성의 재주입은 launch 본문 re-inject 1겹이다** — anchor의 3겹 정박과 비대칭.
  compaction 후 정체성 표류는 관측 항목이다.
- **background가 상시 점유되면 advisor가 소집되지 않는다**(결정 16의 뒷면) — 위임 파도가 영원히
  비지 않는 운용에는 기계 보장이 없다. rules의 파도-정지 리듬이 자연 유도하는 것으로 수용한다.
- **round 0에는 candidates 경로가 전달되지 않는다** — 경로의 유일 결정론 채널이 Stop 트리거라 첫
  정지 전의 후보는 컨텍스트에만 산다. 첫 트리거에서 파일로 이동하는 self-healing으로 수용한다.
- **candidates 라벨의 stale/growing 판정은 라운드 단면 스냅숏이다** — advisor는 큐의 추이를 갖지
  않는다. 표면화의 근거는 "쌓여 있고 처리되지 않았다"뿐이고 그 이상의 판단은 main 몫이다.
- **worker 내부 행위는 advisor에 비가시다** — narrator는 메인 트랜스크립트(지휘·주장)만 서술한다.
  결함이 아니라 신뢰 모델의 이동이다: 산출의 판정은 관측이 아니라 관문(독립 검증·tx·CI)이 소유한다.

---

## 언어와 프롬프트

언어 정책은 레포 전역 규약이다 — 정본은 루트 [ARCHITECTURE.md](../../ARCHITECTURE.md)의
언어·프롬프트 정책 절. ploop 특이사항만 남는다: 에이전트·스킬 프롬프트와 advisor instruction은
단일 `.md`이고, 훅 주입 메시지(advisor trigger)는 `prompt.py`가 조립한다.

---

## 파일 맵

```
ploop/
├── .claude-plugin/plugin.json        # manifest
├── agents/                           # 루프 tier(advisor·narrator)
│   ├── advisor.md                    # advisor 역할 + 5-section 읽기 순서 (Write: advice→advice.md)
│   └── narrator.md                   # 라운드 슬라이스 파일 → action-history 서사 (Read: round.jsonl · Write: narration→narration.md)
├── prompts/instruction.md            # advisor 분석·출력 지침
├── skills/define-mission/SKILL.md    # /ploop:define-mission — 목표(goal) anchor 작성 (루프와 비연결, 수동 핸드오프)
├── skills/define-purpose/SKILL.md    # /ploop:define-purpose — 목적(purpose) anchor 작성 (루프와 비연결, 수동 핸드오프)
├── skills/launch/SKILL.md            # /ploop:launch — 루프 notice + orchestrator rules + 응고 계약 + anchor 핸드오프 (anchor 저장·활성화는 launch 훅)
├── skills/off/SKILL.md               # /ploop:off — 일시정지 조용한 고지 (일시정지는 off_command 훅)
├── skills/on/SKILL.md                # /ploop:on — 재개 확인 고지 (재개·정규화는 on_command 훅)
├── hooks/hooks.json                  # UserPromptExpansion(launch·off·on) + PostCompact + PreToolUse(Agent) + Stop + SubagentStop
├── bin/ploop-hook                    # uv 가용성 체크 래퍼
├── src/                              # 훅 구현 (런타임 의존성 없음)
│   ├── main.py                       # 훅 엔트리포인트(stop·pre_tool_use·subagent_stop·mark_compaction·launch·off_command·on_command)
│   ├── state.py                      # Workspace(세션 파일 경로의 단일 창구) + 4필드 ledger(advice_history·round_start_line·anomalies·phase) + phase 상수 · preserve-by-default 로드/저장
│   └── prompt.py                     # advice-history 포맷 + 5-section advisor trigger 조립(narrator 슬라이스 파일 경로 포함)
└── tests/                            # 구현 독립 (stdin/stdout/disk 구동)
```
