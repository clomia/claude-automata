## 1. Package skeleton

- [x] 1.1 루트 `pyproject.toml` 작성 — name `claude-automata`, `[project.scripts] claude-automata`, hatchling, `force-include`로 `.claude-plugin/marketplace.json` 동봉, requires-python ≥ 3.14
- [x] 1.2 루트 flat `claude_automata/` 모듈 구조 생성 (`cli.py`·`settings.py`·`provision.py`)

## 2. Settings

- [x] 2.1 settings merge 로직 구현 — 전제조건 5키, `permissions.defaultMode` 형제 키 보존, 두 map의 key 단위 병합, 동봉 marketplace.json에서 plugin 목록 해석
- [x] 2.2 settings 테스트 — 파일 부재 생성 / 기존 키 보존 / 재실행 수렴

## 3. Provisioning

- [x] 3.1 도구 검사·설치 로직 구현 — gh(release redirect 해석)·Node LTS(dist/index.json)·repomix(npm -g), 사용자 영역 설치, PATH 안내, openspec 제외, gh auth 안내
- [x] 3.2 provisioning 테스트 — 존재 시 skip / 플랫폼 asset 명명 해석 / 미지원 플랫폼 계속 진행

## 4. CLI

- [x] 4.1 `init` 커맨드 조립 — git root 해석(밖이면 무변경 실패), 항목별 요약 출력(English), 실패 시 비정상 종료 코드
- [x] 4.2 CLI 테스트 — git repo 밖 실패 / end-to-end(임시 git repo에 settings 기록)

## 5. Integration

- [x] 5.1 `.github/workflows/test.yml`에 루트 package test job 추가
- [x] 5.2 README.ko.md·README.md에 Setup 섹션 추가 (`uvx --from git+…` 사용법, `--refresh` 힌트)
- [x] 5.3 로컬 검증 — `uv run pytest` green, 임시 repo에서 `uvx --from <local-path> claude-automata init` 실행해 settings 산출 확인
