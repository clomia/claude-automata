## Why

`init`의 결정론적 plugin 설치는 claude CLI 탐지를 `shutil.which("claude")` 하나에 의존한다. 그런데 claude는 `~/.local/bin/claude`에 설치되고, `provision.py`는 스스로 `~/.local/bin`이 PATH에 없을 수 있음을 전제한다(`path_note`). 그래서 claude를 방금 설치한 셸에서 `~/.local/bin`이 export되기 전에 `uvx claude-automata init`을 돌리면, claude가 실재해도 탐지에 실패해 plugin 단계가 false-deferral로 빠지고 결정론적 설치가 통째로 건너뛰어진다. 이것이 이 setup 경로에서 가장 비싼 실패다 — deferred 경로는 self-heal되지 않기 때문이다.

deferred note는 그 실패를 더 악화시킨다. "plugins install at the next session start; run /reload-plugins once"라고 안내하지만, deferred 경로는 settings 선언만 남길 뿐이고 settings 선언은 install 레지스트리(`installed_plugins.json`)를 populate하지 않는다(실측 확정 — 선언만 한 repo는 레지스트리에 부재, CLI로 설치된 repo는 존재). 즉 note는 미검증 동작을 약속하며, 실제로 유효한 결정론적 remedy를 가리키지 않는다.

## What Changes

- claude CLI 탐지를 PATH에 국한하지 않고 표준 설치 위치(`~/.local/bin/claude`, `~/.claude/local/claude`)까지 probe한다. 찾으면 그 절대경로로 `claude` 관리 명령을 실행한다. 어디에서도 못 찾을 때만 유예한다.
- deferred note를 결정론적 remedy로 교정한다: claude를 PATH에 올린 뒤 `init`을 재실행(또는 `claude plugin install <plugin>@claude-automata --scope project`). 미검증 lazy-install·reload 약속은 제거한다.
- 구현 모듈 docstring에서 미검증 lazy-install 서술을 제거하고 확정된 동작만 기술한다.

behavior 축소·oracle 변경 없음: 설치 판별은 여전히 `claude plugin list --json`이 oracle이고, `claude plugin update` 미사용 원칙도 유지된다. 사용자 대면 출력은 English 유지.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `init-cli`: "Deterministic plugin installation" requirement의 claude CLI 탐지 범위(PATH → PATH+표준 위치)와 유예 시 note 문구(lazy-install 약속 → 결정론적 재실행 remedy)가 바뀐다.

## Impact

- `claude_automata/plugins.py` — 탐지 함수 추가, `run_claude`/`ensure_plugins`가 이를 사용, `DEFERRED_NOTE`·module docstring 교정.
- `tests/test_plugins.py` — 유예 테스트 갱신, 표준 위치 resolve 테스트 추가.
- `openspec/specs/init-cli/spec.md` — 델타로 갱신.
- `INSTALL.md` — 사용자 대면 deferred 경로 서술을 교정된 동작에 맞게 갱신.
- `pyproject.toml` — version 0.2.0 → 0.2.1 (Release publishing이 PyPI 발행을 트리거).
