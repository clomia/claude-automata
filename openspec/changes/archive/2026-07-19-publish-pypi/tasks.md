## 1. Metadata

- [x] 1.1 pyproject.toml [project] metadata 완성 — readme·license(SPDX)·license-files·authors·keywords·classifiers·urls
- [x] 1.2 README.md·README.ko.md 언어 토글 링크 절대 URL화
- [x] 1.3 main spec(init-cli)의 Purpose TBD를 실문장으로 교체

## 2. Release workflow

- [x] 2.1 `.github/workflows/publish.yml` 작성 — main push(pyproject paths)+dispatch, PyPI 버전 게이트(fail-closed), `uv build`+`uv publish`(OIDC, `id-token: write`)

## 3. 배포 전 검토

- [x] 3.1 `uv build` 산출물 검증 — `twine check`, wheel·sdist 내용 검사(marketplace.json 동봉·잡파일 부재)
- [x] 3.2 built wheel로 E2E — 임시 repo에서 wheel 설치 실행으로 init 동작 확인
- [x] 3.3 workflow 문법·게이트 로직 검증 — YAML 파싱, 게이트 스크립트를 로컬에서 기존 버전(skip)·신규 버전(publish 필요) 양 분기 실행
