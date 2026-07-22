## 1. Launch provenance

- [x] 1.1 `state.py` `project_path` + `main.py` — launch가 launch directory를 기록하고 Stop hook이 기록 없는 active loop에 backfill; round 정리는 기록 불변; 테스트(launch 기록·backfill)

## 2. Resolver 범위 강제

- [x] 2.1 `docent.py` — project dir 해석 체인(`--project-dir`→env→cwd), launch 기록 우선 판정 + legacy transcript fallback(encoding 관용 matcher) + 판정 불가 미노출, 숨김 개수 1행 고지, `--exclude-converged` flag; docstring 반영
- [x] 2.2 `skills/docent/SKILL.md` — `--project-dir "${CLAUDE_PROJECT_DIR}"` 관통, flag 안내, 수동 선별 괄호 지침 제거
- [x] 2.3 `tests/test_docent.py` — launch-here만 노출·기록 우선·legacy fallback·판정 불가 미노출·converged 제외 flag·encoding 관용·해석 체인 고정; 기존 테스트를 최종 signature·규칙에 맞춰 갱신

## 3. Canon 재접지

- [x] 3.1 `plugins/ploop/ARCHITECTURE.md` — 결정 17을 launch-provenance 기반 코드 강제로 갱신, 수용한 한계의 열거 성장 문구 정합화

## 4. Release

- [x] 4.1 ploop 0.47.5 → 0.48.0 — `plugin.json`·`pyproject.toml`·`uv.lock` 일관 갱신
