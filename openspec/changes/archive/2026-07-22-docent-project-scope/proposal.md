# Proposal — docent-project-scope

## Why

docent resolver는 data dir(`~/.claude/plugins/data/ploop-*` — plugin 단위, machine 전역)의
전 loop를 무조건 나열한다. 실측: 이 repo에서 resolver를 실행하자 타 repo(darwin/tx-a)의
active loop가 anchor 원문(사업 계획 첫 줄)째로 출력됐다 — 무관한 repo의 작업기억이 docent
session의 context에 선노출된다. canon(plugin ARCHITECTURE 결정 17)은 선별 술어를 이미
규정하지만("docent의 subject는 이 directory의 loop 하나다") 실행이 agent 판단에 맡겨져
있어, "deterministic한 부분은 모두 코드로 옮겨라"(llm-prompt rule)를 위반하고 노출은 판단
이전에 발생한다.

동반 조사(stale loop이 새 작업을 간섭하는가): loop 기계의 전 진입점(stop·launch·off·on)은
현재 session_id로만 상태를 찾으므로 과거 세션의 loop 파일은 기계에 불활성이다 —
`/ploop:on`은 타 세션 loop을 부활시킬 수 없다(anchor 부재로 거부). 교차 세션 읽기 표면은
docent 열거가 유일하며, 이 change가 그 표면을 닫는다.

소유자 확정 요구: **해당 directory에서 launch된 loop만 최신순으로 보여주고, 다른
directory에서 launch된 loop는 노출하지 않는다.** 추가로 완료된 loop를 제외하는 option.

## What Changes

- **launch provenance 기록** — launch hook이 loop을 arm할 때 launch directory
  (`CLAUDE_PROJECT_DIR` env → event cwd → process cwd)를 `{session}_project`에 기록한다.
  Stop hook은 기록 없는 active loop에 backfill한다 — 기록 도입 이전 fleet의 수렴 경로.
  loop 수명이 transcript 보존기간에 결박되지 않는 유일한 판정 기준이다.
- **resolver의 양성 포함 열거** — launch 기록이 호출 project directory
  (`--project-dir` flag → `CLAUDE_PROJECT_DIR` env → cwd; skill이
  `--project-dir "${CLAUDE_PROJECT_DIR}"`를 관통 — Bash env에 CLAUDE_* 부재 실측)와
  일치하는 session만 나열한다. 기록 없는 legacy는 transcript 부모 이름의 관용 대응이
  fallback이고, 둘 다 없으면 노출하지 않는다. 숨김은 내용 없는 개수 1행으로 고지한다.
- **`--exclude-converged` flag** — phase가 converged인 완료 loop를 제외하고 제외 개수를
  고지한다. 기본값은 포함 — 끝난 loop 회고는 docent의 1급 용례다.
- **skill 교리 정리** — 수동 선별 지침 제거, flag 안내 추가. 선별은 resolver 소관이 된다.
- **canon 재접지** — plugin ARCHITECTURE 결정 17을 launch-provenance 기반 코드 강제로 갱신.
- **version bump** — ploop 0.47.5 → 0.48.0.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `ploop-docent`: Resolver session 열거를 launch-directory 양성 포함으로 한정(MODIFIED),
  project scope 판정·launch provenance 기록 requirement 추가(ADDED).

## Impact

- `plugins/ploop/src/{docent,main,state}.py` · `plugins/ploop/skills/docent/SKILL.md` ·
  `plugins/ploop/tests/{test_docent,test_main}.py`
- `plugins/ploop/ARCHITECTURE.md` (결정 17·수용한 한계)
- version pair: `plugins/ploop/{.claude-plugin/plugin.json,pyproject.toml,uv.lock}`
- 기 배포 기기: plugin 갱신 후 active loop은 첫 정지에서 provenance를 얻고, docent는 첫
  실행부터 launch directory 기준으로 좁아진다. 기록 파일은 불변(read-only 보증 유지) —
  열거만 좁아진다.
