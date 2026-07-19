## MODIFIED Requirements

### Requirement: Zero-install entrypoint
repo 루트는 Python package `claude-automata`여야 하며, `claude-automata` 실행 파일과 `init` 커맨드를 노출해야 한다(SHALL). package는 PyPI에 `claude-automata`로 발행되어야 하며(SHALL), uv만 설치된 머신에서 `uvx claude-automata init`으로 사전 설치 없이 실행되어야 한다(SHALL). git source 실행(`uvx --from git+https://github.com/clomia/claude-automata claude-automata init`)도 유효해야 한다(MUST).

#### Scenario: uvx 단축형 실행
- **WHEN** uv만 설치된 머신에서 `uvx claude-automata init`을 실행하면
- **THEN** PyPI의 최신 발행 버전이 격리 환경에 resolve되고 `init` 커맨드가 실행된다

#### Scenario: uvx로 실행
- **WHEN** `uvx --from git+<repo-url> claude-automata init`을 실행하면
- **THEN** package가 격리 환경에 resolve되고 `init` 커맨드가 실행된다

## ADDED Requirements

### Requirement: Release publishing
main에 병합된 `pyproject.toml`의 version이 PyPI에 없으면, release workflow가 `uv build`로 산출물을 만들고 PyPI에 발행해야 한다(SHALL). 이미 발행된 버전은 재발행을 시도하지 않아야 한다(MUST NOT). 인증은 GitHub Actions OIDC 기반 Trusted Publishing이어야 하며(SHALL) 장기 토큰을 repo에 보관하지 않는다(MUST NOT).

#### Scenario: 새 버전 병합
- **WHEN** PyPI에 없는 version의 pyproject.toml이 main에 병합되면
- **THEN** workflow가 build·publish를 수행해 해당 버전이 PyPI에 존재하게 된다

#### Scenario: 기존 버전 재실행
- **WHEN** 이미 PyPI에 존재하는 version으로 workflow가 실행되면
- **THEN** publish를 건너뛰고 성공으로 종료한다
