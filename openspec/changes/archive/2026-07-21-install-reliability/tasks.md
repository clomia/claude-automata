## 1. init 수렴 강화

- [x] 1.1 `claude_automata/plugins.py` — claude CLI 기반 marketplace·plugin cache 수렴: add → update → `list --json` oracle로 미설치 판별 → 각 plugin `install --scope project`; claude 부재·단계 실패는 유예/실패 Outcome으로 보고
- [x] 1.2 `claude_automata/cli.py` — 첫 줄 version 자기 보고, plugins 단계를 outcome 표에 통합, 실패 시 비정상 종료 code 유지
- [x] 1.3 `tests/test_plugins.py` — 결정론적 설치·기설치 재실행·claude 부재 유예·부분 실패 계속 진행을 mock subprocess로 고정; cli 출력에 version 첫 줄 검증 추가

## 2. 문서 재설계

- [x] 2.1 `INSTALL.md` — 실행형을 `uvx claude-automata@latest init`으로, installed state를 "단일 restart로 skills 포함 전 component 로드"로 재설계, 잔존 시 `/reload-plugins` 1회 heal 명시

## 3. Release

- [x] 3.1 `pyproject.toml` 0.1.15 → 0.2.0
