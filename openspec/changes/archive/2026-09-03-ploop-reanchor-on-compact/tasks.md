# Tasks — ploop-reanchor-on-compact

## 1. Core swap

- [x] 1.1 `hooks/hooks.json`: `PostCompact` 항목 → `SessionStart` matcher `compact` (`reanchor`)
- [x] 1.2 `main.py`: `reanchor` entry(armed면 anchor + candidates 주소를 additionalContext로);
      `deliver_context(hook_event, text)`; `arm_round` marker 소비 삭제; `mark_compaction` 삭제
- [x] 1.3 `prompt.py`: `format_anchor_notice`; `format_directive(anchor_text)` 삭제
- [x] 1.4 `state.py`: `compacted_path` 삭제; `__main__.py` entry 교체

## 2. Docs

- [x] 2.1 `ARCHITECTURE.md`: anchor 정박 3겹, hook·file table, 결정 1·6·21, file map

## 3. Verification & release

- [x] 3.1 Tests: reanchor 2건 추가, marker·inline test 3건 삭제; `pytest` + `ruff` green
- [x] 3.2 Version 0.55.1 → 0.56.0 (`pyproject.toml`, `plugin.json`)
