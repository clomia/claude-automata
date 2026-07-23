## Context

ploop은 nested subagent 위에 구현된다(ARCHITECTURE.md 「왜 nested subagent인가」): main(depth 0)→advisor(depth 1)→narrator(depth 2). Claude Code 2.1.217이 nested subagent를 기본 차단했다(공식 CHANGELOG). shipping 바이너리의 depth resolver는

```
FZ() = env(CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH) ?? featureFlag(default 1)
gate: if (spawner_depth >= FZ()) throw "nesting limit"
```

기본 cap 1에서 advisor(depth 1)는 `1 >= 1`로 spawn이 막혀 narrator를 띄우지 못한다. 실측(이 머신 2.1.218) A/B로 확정: env 미설정 → depth-1 subagent가 Agent tool 없음(`NO_AGENT`), `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=2` → 있음(`HAS_AGENT`). reference 문서(sub-agents.md "depth 5·fixed·not configurable", env-vars.md 해당 var 없음)는 2.1.217 이전 상태로 lag됐고, CHANGELOG가 shipped 동작의 정본이다.

## Goals / Non-Goals

**Goals:**
- ploop의 nested subagent 경로를 **공식 remedy**(`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`)로 복원한다.
- 기여하는 모든 machine에서 동일하게 동작하게 한다(repo-unit propagation).
- ploop의 비자명한 Claude Code 설정 요구(nested subagent·auto compaction·thinking)를 `/ploop:launch`에서 assert해, Claude Code 변경으로 인한 파손을 조용한 degrade 대신 fail-fast + 교정 안내로 전환한다. 향후 유사 변경의 모범 선례 템플릿.

**Non-Goals:**
- 구조 평탄화(main이 narrator·advisor를 형제로 소환) — nesting은 owner가 hard requirement로 확정.
- ploop이 settings.json을 **쓰지(변이)** 않는다 — 결정 12 위반이라 배제. assertion은 settings.json을 **읽기만** 한다.
- permission mode·autoMemory·model 강제 — owner가 assertion 대상에서 제외.
- reference 문서(Anthropic 소유)의 수정 — 우리 소유 밖. CHANGELOG를 근거로 삼는다.

## Decisions

- **provision = init, 값 `5`.** `claude_automata/settings.py`의 `merged()`가 target repo `.claude/settings.json`의 `env`에 `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH="5"`를 병합한다. 공식 메커니즘(env-vars.md: settings.json `env`는 startup에 프로세스 env로 기록됨 → `FZ()`가 읽음). settings.json은 커밋되므로 clone·기여 machine 전체에 전파된다. **대안 기각**: user-level `~/.claude/settings.json`은 repo와 함께 이동하지 않아 "동일 환경" 모델을 깬다. 값 `5`는 nesting 도입 시(2.1.172 "up to 5 levels deep")의 공식 cap 복원 — ploop 함수적 최소치는 `2`(main0→advisor1→narrator2)지만 설계 baseline과 공식 default에 맞춰 `5`.
- **enforcement = ploop launch의 prerequisite assertion 레이어(READ-only).** `launch()`가 세 요구를 검사해 미충족을 모아 한 `block_expansion`으로 알린다(각 fix + settings.json 교정 + Claude Code 재시작 + relaunch). 요구·소스: ① nested subagent `os.environ["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] >= 5`, ② auto compaction project `.claude/settings.json`의 `autoCompactEnabled == true`, ③ thinking 같은 파일의 `alwaysThinkingEnabled == true`. **소스 = effective 우선.** nesting은 env라 `os.environ`(effective)으로 본다 — settings.json만 고치고 재시작 안 한 상태는 declared돼 있어도 미반영이라, settings.json read로는 "설정 있는데 안 먹는" silent 실패가 재발한다; os.environ은 재시작을 강제해 막는다. compaction·thinking은 runtime 신호가 없어 project settings.json declared를 읽는다(차선). 임계치 `5`는 provision·2.1.172 원래 cap과 일치(함수 최소치 2지만 표준 config 강제 — owner "최소 5 depth"). **결정 12는 no-write로 보존** — settings.json을 읽기만 한다. **auto-write 기각**은 결정 18과 동일(env는 startup 반영이라 재시작 불가피, self-provision=결정 12 write 위반). check는 확장 가능한 tuple(향후 Claude Code 변경의 새 요구를 한 줄로).
- **책임 분리.** provision(설정 쓰기)은 init의 본업, enforcement(요구 검증)는 ploop의 guard. ploop은 자기 requirement를 선언·검증하되 settings는 안 쓴다.
- **관측이 아닌 공식 의존으로 기술, home 하나.** nesting 의존의 설계 정본 home은 `plugins/ploop/ARCHITECTURE.md`(「왜 nested subagent」) 하나다 — CHANGELOG(2.1.172 도입 → 2.1.217 기본 off + env toggle)를 근거로 인용한다. **MEMORY.md에 넣지 않는다**: MEMORY.md는 기억 system의 설계 정본이지 fact 저장소가 아니며, 그 승격 routing이 "코드를 구속하는 측정 사실(2곳+ 소비·구조 구속) → 설계 정본"으로 이미 이 home을 지정한다(새 bucket 금지). `audit-harness-deps`는 **비공식** 관측 의존을 다루는데 이 의존은 CHANGELOG로 공식화되어 그 대상이 아니다. provisioning 사실은 init-cli spec이 소유한다.

## Risks / Trade-offs

- **reference 문서가 CHANGELOG와 모순(sub-agents "fixed·not configurable")** → CHANGELOG가 shipped 동작 정본. 의존은 `plugins/ploop/ARCHITECTURE.md`(설계 정본)에 CHANGELOG 근거로 기술하고, version-up-alert가 후속 버전의 재변경을 감시한다.
- **feature flag가 후일 기본값을 `>=2`로 되돌리면**, env 미설정이어도 nesting이 살아있는데 guard가 오차단할 수 있다 → 현재 flag 기본 `1`(실측). 발생 시 guard 문구가 그대로 actionable하고, default 복귀는 저확률이며 env는 owner의 공식 provision 경로라 그대로 유효.
- **env는 startup에 반영** → 이미 도는 loop은 재시작 전까지 미반영. env-vars.md상 settings 저장 시 running 세션 env에 재적용되어 다음 round에 self-heal되며, 확실히 하려면 `/ploop:off`→갱신→`/ploop:on`(또는 relaunch). loop 상태(session_id-keyed data dir)는 무손상.
- **standalone ploop(init 미실행)** → guard가 fail-fast + 정확한 한 줄 교정 안내. 조용한 degrade보다 안전.

## Migration Plan

- **적용**: change 병합 → 기여 machine은 커밋된 settings를 pull(또는 `uvx claude-automata@latest init`)하고 Claude Code 재시작. 도는 loop은 `/ploop:off`→갱신→`/ploop:on`.
- **rollback**: revert 시 nesting은 다시 차단 상태로 복귀(loop은 이전처럼 degrade, 상태 손상 없음).
