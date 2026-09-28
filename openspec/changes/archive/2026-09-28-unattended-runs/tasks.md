# Tasks — unattended-runs

## 1. ploop

- [x] 1.1 `state.py`: `Workspace.unattended`(anchor 존재)
- [x] 1.2 `main.py`: `guard` entry(PreToolUse `EnterPlanMode` deny · PermissionRequest deny · Elicitation
      decline · Notification 멈춤 → loop.log `Stall`); mode prerequisite; `on_command`도 prerequisite 검사
- [x] 1.3 `hooks.json`·`__main__.py`: guard 등록(PreToolUse `EnterPlanMode`, PermissionRequest,
      Elicitation, Notification 멈춤 matcher)
- [x] 1.4 skills: launch rule(사용자 부재), define-mission 무인 확인 단계 삭제, define-mission·
      define-purpose 핸드오프에 bypass session
- [x] 1.5 `ARCHITECTURE.md`: 무인 전제·결정 11·15·18 개정·결정 25(무인 guard)·Hooks·상태 표·file map
- [x] 1.6 Tests + version 0.56.0 → 0.57.0

## 2. refine

- [x] 2.1 `src/guard.py`: `arm`(자기 workflow 발사 시 mode 검사 → 거부 또는 `{session}_unattended`),
      `guard`(PreToolUse `EnterPlanMode` · PermissionRequest · Elicitation); `__main__.py`
- [x] 2.2 `hooks/hooks.json` 신설
- [x] 2.3 Tests + version 0.14.0 → 0.15.0

## 3. init

- [x] 3.1 `settings.py`: defaultMode 쓰기 제거, `bypassPermissions`·`auto` 제거, `overridden`의 mode 검사 제거
- [x] 3.2 `test_settings.py`·`test_cli.py`
- [x] 3.3 INSTALL.md 공개·`site-truth-check.yml` 결속 갱신
- [x] 3.4 root `pyproject.toml` 0.3.4 → 0.4.0

## 4. Canon & surfaces

- [x] 4.1 root `ARCHITECTURE.md`: 무인 계약(접면 계약), init mode 결정 기록
- [x] 4.2 README.md·README.ko.md·site(en·ko): bypass launch, askUserQuestionTimeout 안내 제거
- [x] 4.3 이 repo `.claude/settings.json`의 defaultMode 제거
- [x] 4.4 repo 수준 test: ploop·refine guard의 등록 형태와, 실제 runner가 같은 event에 내는 답의 동일성 결속

## 5. Verification

- [x] 5.1 전체 `pytest` + `ruff` green
- [x] 5.2 live 실측: `--plugin-dir`로 두 plugin을 실은 session에서 launch 거부(auto)·critical 삭제·질문·
      EnterPlanMode·off 뒤 무인 유지 확인. refine arm은 실제 runner(`bin/refine-hook`)로 확인 — live 발사는
      실제 run(수 시간)이 시작되므로 제외
