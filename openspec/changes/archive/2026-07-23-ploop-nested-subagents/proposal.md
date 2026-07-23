## Why

ploop의 advisor loop은 nested subagent에 의존한다 — main(depth 0)이 `Agent(ploop:advisor)`(depth 1)를, advisor가 `Agent(ploop:narrator)`(depth 2)를 spawn한다. Claude Code 2.1.217이 이 동작을 기본 차단했다(공식 CHANGELOG: *"Changed subagents to no longer spawn nested subagents by default; set `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` to allow deeper nesting"*). 그 결과 advisor가 narrator를 spawn하지 못해 loop이 조용히 degrade한다 — advisor가 `round.jsonl`을 raw로 읽으며 이를 "subagent 격리"로 오진한다. nesting은 ploop의 hard requirement이므로, Anthropic이 안내한 공식 remedy(env var)로 capability를 복원한다.

이 사건은 일반적 위험을 드러낸다: **ploop은 비자명한 Claude Code 설정에 mechanism이 걸려 있고, Claude Code 변경이 그 default를 뒤집어 loop을 silent하게 깨뜨릴 수 있다**(tx·refine은 이런 의존이 없거나 자명하다). 그래서 `/ploop:launch`에 **prerequisite assertion 레이어**를 둔다 — 요구 설정이 미충족이면 arm하지 않고 교정 목록을 알린다. 기존 사용자가 Claude Code 업데이트 후 겪을 파손을 fail-fast로 전환하고, 향후 유사 변경의 모범 선례가 된다.

## What Changes

- **init이 `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH="5"`를 provision한다** — `claude_automata/settings.py`의 `merged()`가 target repo `.claude/settings.json`의 `env` 블록에 merge-write한다. 커밋되어 기여 machine 전체에 전파된다(repo-unit model). 값 `5`는 nesting 도입 시(2.1.172, "up to 5 levels deep")의 원래 공식 cap 복원이다. ploop 트리의 함수적 최소치는 `2`(main0→advisor1→narrator2).
- **이 repo 자체의 커밋된 `.claude/settings.json`에 `env`(nesting)와 `autoCompactEnabled`를 수동 추가** — dogfooding(ploop을 `--plugin-dir`로 로드하며 self-init하지 않음). `alwaysThinkingEnabled`는 이미 있다.
- **ploop launch prerequisite assertion 레이어(READ-only) 추가** — `plugins/ploop/src/main.py`의 `launch()`가 세 요구를 검사해 하나라도 미충족이면 expansion을 block하고 미충족 목록·교정·재시작을 한 알람으로 안내한다: ① nested subagent — `os.environ`의 `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH >= 5`(effective — settings.json 편집만 하고 재시작 안 하면 미반영이라 os.environ으로 봐야 재시작을 강제한다), ② auto compaction — project `.claude/settings.json`의 `autoCompactEnabled == true`, ③ thinking — 같은 파일의 `alwaysThinkingEnabled == true`. permission mode·autoMemory·model은 강제하지 않는다. settings.json은 **읽기만** 하고 쓰지 않는다(결정 12 "불간섭"=무변이 보존). check는 확장 가능한 tuple이라 향후 Claude Code 변경의 새 요구를 한 줄로 추가한다(템플릿).
- **ARCHITECTURE.md 정정** — `plugins/ploop/ARCHITECTURE.md`「왜 nested subagent」의 `(v2.1.172+, depth 5 cap)`를 공식 2.1.172(도입)→2.1.217(기본 off + env var toggle) 타임라인·env var 요구·guard로 수정한다. 이 파일이 nesting 의존의 설계 정본 home이다(MEMORY.md 승격 routing: 코드를 구속하는 측정 사실·2곳+ 소비 → 설계 정본). 이제 CHANGELOG로 공식화된 의존이라 `audit-harness-deps`(비공식 관측 의존) 대상이 아니고, MEMORY.md(기억 system 설계 정본, fact 저장소 아님)에도 넣지 않는다.
- **version bump** — `claude-automata`(settings.py 변경)·`ploop`(launch() 변경), rules/update.md.

## Capabilities

### New Capabilities

(없음 — ploop launch guard는 ploop-core 동작이라 openspec spec 대상이 아니다. ploop core canon은 `plugins/ploop/ARCHITECTURE.md`이며, 유사 Stop-guard 변경(archive `monitor-wait-guard`)도 no-delta였다.)

### Modified Capabilities

- `init-cli`: **Settings prerequisites** requirement가 `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH="5"`를 추가로 merge-write한다 — 기존 `env` key는 보존하며, 재실행은 idempotent하다.

## Impact

- **코드**: `claude_automata/settings.py`(`merged()` env provision), `plugins/ploop/src/main.py`(`launch()` prerequisite assertion 레이어 — os.environ + project settings.json READ).
- **설정**: `.claude/settings.json`(이 repo 수동: `env`+`autoCompactEnabled` · adopting repo는 init). init은 이미 `autoCompactEnabled`·`alwaysThinkingEnabled`를 provision한다(PREREQUISITES) — assertion 3요구가 모두 init provision과 대응한다.
- **문서**: `plugins/ploop/ARCHITECTURE.md`(nesting 의존의 설계 정본 home).
- **version**: `pyproject.toml`(claude-automata), `plugins/ploop/pyproject.toml` + `plugins/ploop/.claude-plugin/plugin.json`.
- **test**: `tests/test_settings.py`, `plugins/ploop/tests/test_main.py`.
- **의존**: Claude Code ≥ 2.1.217 (공식 CHANGELOG). reference 문서(sub-agents.md·env-vars.md)는 아직 이 변경을 반영하지 못한 lag 상태이며 CHANGELOG가 shipped 동작의 정본이다.
