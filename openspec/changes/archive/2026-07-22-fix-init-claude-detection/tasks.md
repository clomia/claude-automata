## 1. Detection

- [x] 1.1 `plugins.py`에 `provision.LOCAL_BIN`을 import하고 표준 위치 상수(`~/.local/bin/claude`, `~/.claude/local/claude`)와 `claude_bin()` 탐지 함수를 추가한다 (PATH 우선, 없으면 표준 위치 stat)
- [x] 1.2 `run_claude`가 `claude_bin()`이 반환한 절대경로로 subprocess를 실행하고, 미해결 시 `(None, "claude not found")`를 반환하도록 바꾼다
- [x] 1.3 `ensure_plugins`의 유예 게이트를 `claude_bin() is None`으로 바꾼다

## 2. Deferred guidance

- [x] 2.1 `DEFERRED_NOTE`를 결정론적 remedy(claude를 PATH에 올린 뒤 init 재실행 / 명시적 `claude plugin install --scope project`)로 교정하고 lazy-install·reload 약속을 제거한다 (English 유지)
- [x] 2.2 모듈 docstring에서 미검증 lazy-install 서술을 제거하고 탐지 범위·레지스트리 분리·유예 remedy만 남긴다
- [x] 2.3 `INSTALL.md`의 사용자 대면 deferred 서술을 교정된 동작(표준 위치 탐지 + 결정론적 재실행 remedy)에 맞게 갱신한다

## 3. Tests

- [x] 3.1 `test_missing_claude_cli_defers`를 갱신한다: PATH와 표준 위치 모두 부재일 때만 유예됨을 검증
- [x] 3.2 PATH 밖 표준 위치에 claude가 있으면 유예되지 않고 설치가 진행됨을 검증하는 테스트를 추가한다
- [x] 3.3 `uv run pytest -q`와 `uv run ruff check` green

## 4. Release

- [x] 4.1 `pyproject.toml` version 0.2.0 → 0.2.1
