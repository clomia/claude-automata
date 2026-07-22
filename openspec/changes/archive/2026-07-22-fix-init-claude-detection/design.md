## Context

`plugins.ensure_plugins`는 `shutil.which("claude") is None`으로 claude CLI 유무를 판별하고, 없으면 `DEFERRED_NOTE`와 함께 유예한다. 이 판별과 note는 두 가지 관측 기반 가정에 의존하는데, 실측 결과 둘 다 무결하지 않았다. 실측은 전부 `claude` 관리 명령(`plugin list/marketplace/install`)으로 수행했다 — headless 세션(`claude -p`)은 구독 약관 문제로 배제했다.

**실측 사실**
- claude 바이너리는 `~/.local/bin/claude`(심링크)에 산다. `provision.py`는 스스로 gh/node/repomix를 `~/.local/bin`에 깔면서 그 경로가 PATH에 없을 수 있음을 `path_note()`로 인정한다. 두 사실이 합쳐지면, `~/.local/bin`이 PATH에 없는 셸에서 init을 돌릴 때 `shutil.which`가 실재하는 claude를 놓친다.
- `claude plugin list --json`은 install 레지스트리 `~/.claude/plugins/installed_plugins.json`(필드: id/version/scope/enabled/installPath/installedAt/projectPath)을 반영한다. 이 레지스트리는 `claude plugin install`이 populate하며, settings.json의 `enabledPlugins` 선언으로는 채워지지 않는다. 근거: 선언만 한 repo는 레지스트리에 부재, CLI로 설치된 repo(lebit, `hasTrustDialogAccepted=False`)는 존재 → trust와도 무관.
- `claude plugin marketplace add <repo>`는 이미 존재 시 exit 0(idempotent), `claude plugin install <bogus>`는 실패 시 exit 1 → 현행 `run_claude`의 실패 감지와 `cli.py`의 write-settings-then-probe 순서는 무결하다(선언이 레지스트리를 안 만드니 probe가 속지 않음).

## Goals / Non-Goals

**Goals**
- claude가 실재하는데 유예로 빠지는 false-deferral을 제거한다.
- 유예가 진짜로 필요한 경우(claude 부재)의 note를 결정론적이고 검증된 remedy로 만든다.

**Non-Goals**
- session 시작 시 lazy 설치 여부의 규명(cold-cache headless 실측이 필요 — 약관상 배제). 대신 그 동작에 의존하지 않는 remedy로 설계한다.
- `~/.local/bin`을 PATH에 자동 등록(별개 관심사 — `provision.path_note`가 이미 안내).
- 설치 scope(project) 변경 — 스펙 확정 사항.

## Decisions

**D1. claude 탐지: PATH → PATH + 표준 위치.** `claude_bin()`이 `shutil.which("claude")`를 먼저 보고, 실패 시 `~/.local/bin/claude`, `~/.claude/local/claude`를 순서대로 stat해 첫 존재 경로를 절대경로로 반환한다. `run_claude`는 이 절대경로로 subprocess를 띄우고, `ensure_plugins`의 유예 게이트는 `claude_bin() is None`으로 바뀐다.
- 대안 A(note만 개선하고 탐지는 유지): false-deferral 자체가 남아 가장 비싼 실패를 방치. 기각.
- 대안 B(`~/.local/bin`을 PATH에 강제 주입): 부작용 범위가 넓고 provision의 관심사와 중복. 기각.
- `~/.local/bin`의 single home은 `provision.LOCAL_BIN` — plugins는 이를 import해 경로를 중복 정의하지 않는다.

**D2. 유예 note: lazy-install 약속 제거, 결정론적 remedy 제시.** deferred 경로는 settings 선언만 남기고 레지스트리를 안 채운다(실측). 따라서 "다음 session 시작에 설치된다"는 미검증 약속을 지우고, 검증된 유일 remedy — claude를 PATH에 올린 뒤 init 재실행(또는 명시적 `claude plugin install --scope project`) — 를 안내한다. init 재실행이 결정론적으로 수렴함은 실측된 사실(install 관리 명령이 레지스트리를 채움)에 근거한다.

**D3. docstring: 확정 동작만 기술.** 모듈 docstring의 "next session start installs lazily / heals with /reload-plugins" 서술을 제거하고, 탐지 범위·레지스트리 분리·유예 remedy만 남긴다.

## Risks / Trade-offs

- [표준 위치의 claude가 깨졌거나 구버전] → `run_claude`가 실패를 사유와 함께 반환하므로 크래시 없이 failed로 보고된다. 탐지 확장이 실패 경로를 악화시키지 않는다.
- [표준 위치 목록이 향후 claude 배포에서 바뀔 수 있음] → 관측 기반 의존. PATH 탐지를 1순위로 두어 목록은 보조 안전망에 머문다. 목록 표류는 `audit-harness-deps`의 관측 대상.
- [lazy-install이 실제로는 동작할 수도 있음] → note는 그것을 부정하지 않고 결정론적 remedy만 제시하므로, 동작 여부와 무관하게 옳다.

## Migration Plan

`pyproject.toml` 0.2.0 → 0.2.1 병합 시 `publish.yml`이 PyPI에 0.2.1을 발행한다. 안내형 `uvx claude-automata@latest init`이 이후 새 탐지를 사용한다. 롤백은 버전 재범프로 후속 change 처리(PyPI는 재발행 불가).
