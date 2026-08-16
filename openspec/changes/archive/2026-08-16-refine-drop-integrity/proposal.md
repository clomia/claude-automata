# refine-drop-integrity

## Why

Field use (2026-08, a production backend repository) showed the integrity workflow
diverging: a 3-day run broke ~40% of the integration test coverage and cost two more
days to repair. The mechanism is structural, not incidental. First, the pipeline is
additive by construction — hunt sweeps run until findings dry up, the deliberation
critics are charged to *add* hazards the regions missed, and every applied plan adds
code plus a pinning test — so even a perfect run grows the surface the next run hunts.
Second, reachable-state analysis cannot distinguish a defect from an unspecified but
load-bearing behavior (a de-facto contract in Hyrum's-law terms); absorbing such states
into the boundary renegotiates contracts the agents cannot see. A "behavior-preserving"
guardrail would forbid every absorption verdict and dissolve the workflow's purpose, so
the workflow cannot be saved by constraints — it is removed.

## What Changes

- **`refine:integrity` removed** — the skill directory (`SKILL.md`, `principles.md`,
  `workflow.js`) is deleted; the bootstrap CLI's skill set derives from the directory
  listing, so it converges without a code change.
- **refine re-scoped to the representation layer** — the plugin description drops
  integrity; the root canon records the exclusion and the entry test for future
  workflows (the verifier contract: refine touches information efficiency only, never
  behavior — boundary hardening belongs to a mission through tx).
- Exposure surfaces (README ko/en, site pages, keywords, tests) drop the workflow.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — refine has no spec'd capability; retroactive spec transcription is excluded by
the root canon, so the removal carries no delta)

## Impact

- `plugins/refine/skills/integrity/` deleted (`SKILL.md`, `principles.md`,
  `workflow.js`).
- `plugins/refine/.claude-plugin/plugin.json`: description, keywords, version
  0.13.2 → 0.14.0.
- `plugins/refine/tests/test_bootstrap.py`: integrity cases retargeted/removed.
- `ARCHITECTURE.md` (root): verifier contract added to the interface contracts;
  exclusion recorded in 결정 기록.
- `README.ko.md`, `README.md`, `site/index.html`, `site/ko/index.html`: command and
  description rows updated.
