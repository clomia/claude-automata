# Tasks — refine-drop-integrity

## 1. Removal

- [x] 1.1 Delete `plugins/refine/skills/integrity/` (SKILL.md, principles.md,
      workflow.js) — bootstrap's SKILLS tuple converges automatically
- [x] 1.2 `plugin.json`: drop integrity from description and keywords; version
      0.13.2 → 0.14.0
- [x] 1.3 `tests/test_bootstrap.py`: retarget the workflow-contract case to `code`,
      drop the integrity conventionPath row

## 2. Canon

- [x] 2.1 Root `ARCHITECTURE.md`: add the verifier contract (cross-cutting) to the
      plugin interface contracts
- [x] 2.2 Root `ARCHITECTURE.md`: record the exclusion (divergence mechanism, Hyrum
      surface, why no guardrail can save it) in 결정 기록

## 3. Exposure

- [x] 3.1 `README.ko.md` / `README.md`: drop the command, re-scope the description
- [x] 3.2 `site/index.html` / `site/ko/index.html`: module card and code block updated
