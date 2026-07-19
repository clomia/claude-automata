## Why

init CLI의 유일한 실행 경로가 `uvx --from git+…` 장문 커맨드다. PyPI에는 사용자가 선점해 둔 placeholder(version "0", Repository가 이 repo)가 있어, 지금 `uvx claude-automata init`을 치면 실행 파일 없는 wheel이 해석되어 실패한다. 정식 발행으로 단축형을 열고, 이후의 발행을 버전 게이트 자동화로 응고한다.

## What Changes

- 루트 `pyproject.toml`의 PyPI metadata 완성 — readme·license(SPDX MIT)·authors·keywords·classifiers·urls. README의 언어 토글 링크는 절대 URL로 바꿔 PyPI 렌더에서도 무결하게 한다.
- `.github/workflows/publish.yml` 신설 — main push(pyproject.toml paths) + workflow_dispatch 트리거, PyPI 버전 게이트(이미 발행된 버전은 skip), `uv build` + `uv publish`(Trusted Publishing/OIDC, 토큰 무보관).
- 발행 인증의 1회 전제: PyPI 프로젝트 설정에 GitHub Trusted Publisher 등록 — 계정 소유자만 가능하며, 등록 파라미터는 design에 명시한다. 등록 전까지 publish 실행은 인증 단계에서 실패한다(가시적).
- README의 커맨드 단축형 전환은 **발행 성립 후 후속 변경**이다 — 미발행 상태에서 단축형을 문서화하면 placeholder가 해석되는 깨진 안내가 된다.
- archive가 남긴 main spec의 Purpose TBD를 실문장으로 채운다.

## Capabilities

### New Capabilities

<!-- 없음 -->

### Modified Capabilities

- `init-cli`: Zero-install entrypoint 요구가 PyPI 발행 단축형(`uvx claude-automata init`)을 포함하도록 확장되고, 버전 게이트 자동 발행(Release publishing) 요구가 추가된다.

## Impact

- `pyproject.toml`(metadata), `.github/workflows/publish.yml`(신규), `README.md`·`README.ko.md`(링크 절대화), `openspec/specs/init-cli/spec.md`(delta sync)
- 발행 후 버전관리 절차: pyproject version bump → main 병합 → workflow가 자동 발행 (spec이 정본으로 보존)
