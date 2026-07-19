## Why

claude-automata를 새 repo에 도입하려면 settings.json 전제조건(thinking·memory·permissions·model·compaction), marketplace·plugin 등록, 외부 CLI(gh·Node/npx 계열) 준비를 전부 손으로 맞춰야 한다. 이 수동 셋업이 진입 장벽이자 설정 표류의 원천이다 — uv만 설치되어 있으면 한 커맨드로 끝나는 init CLI로 응고한다.

## What Changes

- repo 루트가 Python package `claude-automata`가 된다 (루트 pyproject.toml + flat `claude_automata/`). `uvx --from git+https://github.com/clomia/claude-automata claude-automata init`으로 설치 없이 실행된다.
- `claude-automata init`은 target repo의 `.claude/settings.json`에 전제 설정과 marketplace·plugin 등록을 merge-write한다 — 기존 키는 보존하고, 재실행은 idempotent하다.
- init이 외부 CLI 의존성(gh, Node.js ≥ 20의 node·npm·npx, repomix)을 검사하고, 없으면 sudo 없이 사용자 영역(`~/.local`)에 설치한다. openspec은 설치 대상이 아니다 — tx plugin이 npx로 pin-fetch하며 pin의 single home은 tx에 남는다.
- CI test workflow에 루트 package test job이 추가된다.

## Capabilities

### New Capabilities

- `init-cli`: 한 커맨드로 claude-automata의 전제조건 전부를 충족시키는 셋업 CLI — Claude Code settings 구성, marketplace·plugin 등록, 외부 CLI 의존성 설치.

### Modified Capabilities

<!-- 기존 스펙 없음 -->

## Impact

- 신규 코드: 루트 `pyproject.toml`, `claude_automata/`, `tests/`
- `.github/workflows/test.yml`: 루트 package test job 추가
- 플러그인들은 이후 "의존성이 이미 존재한다"고 가정할 수 있게 된다 — 실제 단순화(refine의 bun fallback 제거 등)는 후속 change다.
