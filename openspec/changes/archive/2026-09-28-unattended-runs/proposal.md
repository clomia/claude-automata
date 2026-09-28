# unattended-runs

## Why

ploop loop과 refine workflow는 실사용 전부가 무인이다 — 사람의 개입이 필요한 작업은 애초에 바닐라
Claude Code로 한다(owner, 2026-09-28, 반년 운용 관측). 그런데 무인 run을 멈춰 세우는 dialog가 남아
있다: bypass 모드에서도 harness는 critical-path `rm`·`AskUserQuestion`·plan 승인·MCP elicitation을
사람에게 묻고, plan 승인은 idle로 절대 풀리지 않는다. lora worker는 이 틈을 자체 hook 네 개와
settings로 메워 왔다 — 같은 보장이 plugin 밖에 중복돼 있고, lora 밖의 사용자는 무방비다.

동시에 `claude-automata init`이 project `.claude/settings.json`에 쓰는
`permissions.defaultMode="bypassPermissions"`는 harness가 project scope에서 무시한다 — 무효일 뿐
아니라 user scope의 mode를 가려 session을 Manual로 떨어뜨린다(실측 2026-09-28, 2.1.283).

## What Changes

- **무인 전용 계약** — ploop loop·refine workflow는 bypassPermissions session에서만 시작하고, 시작한
  session은 그때부터 무인 session이다. 무인 session에서 남은 dialog는 plugin이 스스로 답한다:
  permission 요청(`AskUserQuestion`·plan 승인 포함)은 행동 가능한 사유와 함께 deny, plan mode
  진입은 사전 deny, MCP elicitation은 decline. ploop은 그래도 사람을 기다린 dialog를 loop.log에
  `Stall` entry로 남긴다.
- **ploop** — launch·on이 effective permission mode를 prerequisite로 검사한다(bypassPermissions만).
  define-mission의 무인 운행 확인 단계와 launch rules의 `AskUserQuestion` 소통 경로를 걷는다 —
  무인은 anchor가 선언할 선택이 아니라 ploop의 전제다.
- **refine** — Workflow 발사 시점에 같은 mode 검사·무인 arm을 한다(hook 신설).
- **init** — **BREAKING**: `permissions.defaultMode`를 더 이상 쓰지 않는다. INSTALL.md 공개와 CI
  결속에서 빠지고, 무인 run의 bypass 요건이 그 자리에 공개된다.
- README·site·root/ploop ARCHITECTURE가 무인 전제와 bypass launch를 서술한다.

## Capabilities

### New Capabilities

- `unattended-runs`: 무인 run의 시작 조건(bypass 전용), 무인 session의 범위, dialog 응답 계약과
  멈춤 기록.

### Modified Capabilities

- `init-cli`: Settings prerequisites에서 `permissions.defaultMode` 제거, 쓰지 않음을 요구.
- `landing-page`: INSTALL.md 공개 목록에서 defaultMode 제거, 무인 run의 bypass 요건 공개.

## Impact

- `plugins/ploop/`: `hooks/hooks.json`(PreToolUse `EnterPlanMode`·PermissionRequest·Elicitation·
  Notification → `guard`), `src/main.py`(`guard`, mode prerequisite, on의 prerequisite 검사),
  `src/state.py`(`Workspace.unattended`), `src/__main__.py`, skills(launch·define-mission·
  define-purpose), ARCHITECTURE.md, tests. Version 0.56.0 → 0.57.0.
- `plugins/refine/`: `hooks/hooks.json` 신설, `src/guard.py`, `src/__main__.py`, tests.
  Version 0.14.0 → 0.15.0.
- `claude_automata/settings.py`, `tests/test_settings.py`·`test_cli.py`, INSTALL.md,
  `.github/workflows/site-truth-check.yml`, root `pyproject.toml` 0.3.4 → 0.4.0.
- README.md·README.ko.md·site(en·ko)·root ARCHITECTURE.md, 이 repo의 `.claude/settings.json`.
- `docs/research/unattended-dialogs-2026.md` — 실측 기록.
- 하류(follow-up, 이 transaction 밖): lora가 중복 장치(hook 네 개·EnterPlanMode deny·AFK timeout·
  askUserQuestionTimeout)를 걷고 plugin pin을 올린다.
