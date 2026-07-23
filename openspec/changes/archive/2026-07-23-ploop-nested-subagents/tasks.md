## 1. init provisioning (claude_automata)

- [x] 1.1 `claude_automata/settings.py` `merged()`에 `env` 병합 추가 — `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH="5"`를 `setdefault("env", {})`로 세팅해 기존 `env` 하위 key를 보존한다 (compaction·thinking은 기존 PREREQUISITES가 이미 provision)
- [x] 1.2 `tests/test_settings.py`에 계약 검증 추가 — `merged()` 산출물에 `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH == "5"`가 있고, 기존 `env` 항목이 보존되며, 재적용이 idempotent함을 확인

## 2. dogfooding settings (이 repo)

- [x] 2.1 이 repo의 커밋된 `.claude/settings.json`에 `"env": {"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "5"}`와 `"autoCompactEnabled": true` 수동 추가 (self-init하지 않으므로 — `alwaysThinkingEnabled`는 이미 있다). assertion이 이 repo에서도 통과해야 함

## 3. ploop launch prerequisite assertion 레이어

- [x] 3.1 `plugins/ploop/src/main.py`에 상수·helper 추가 — `SPAWN_DEPTH_ENV`/`SPAWN_DEPTH_MIN=5`, 세 요구의 fix 문구, `project_settings(event)`(project `.claude/settings.json` READ→dict, 실패 시 `{}`), `unmet_prerequisites(event)`(effective 우선: nesting은 `os.environ>=5`, compaction/thinking은 settings.json `==true`; 확장 가능한 tuple)
- [x] 3.2 `launch()`에서 blank-anchor 뒤에 assertion 배치 — `unmet := unmet_prerequisites(event)`면 미충족 목록·교정·재시작·relaunch를 한 `block_expansion`으로 안내. settings.json은 읽기만(결정 12 no-write)
- [x] 3.3 `plugins/ploop/tests/test_main.py` — 기존 launch 성공 테스트에 유효 prereq(env`5`+project settings.json) 세팅 helper 적용, 그리고 각 요구 미충족(nesting 미설정·`<5`, compaction false, thinking false) block·다중 미충족 목록·전부 충족 arm을 stdin/stdout/disk 구동으로 검증

## 4. 문서 (nesting 의존의 설계 정본 home = ploop ARCHITECTURE.md 하나)

- [x] 4.1 `plugins/ploop/ARCHITECTURE.md` — 「왜 nested subagent인가」의 공식 타임라인 정정(유지)에 더해, 결정 18을 spawn-depth guard에서 **prerequisite assertion 레이어(3요구·effective 우선·READ-only)**로 확장하고 Hooks 표 launch 행을 반영한다. MEMORY.md·audit-harness-deps에는 넣지 않는다

## 5. version bump (rules/update.md)

- [x] 5.1 `pyproject.toml`(claude-automata) version bump — settings.py 변경 반영
- [x] 5.2 `plugins/ploop/pyproject.toml`·`plugins/ploop/.claude-plugin/plugin.json` version 일관 bump — launch() 변경 반영

## 6. 검증

- [x] 6.1 전체 test 통과 확인 — root(`tests/`)와 `plugins/ploop/tests/` 양쪽, ruff lint clean
