# init-cli Specification

## Purpose
TBD - created by archiving change init-cli. Update Purpose after archive.
## Requirements
### Requirement: Zero-install entrypoint
repo 루트는 Python package `claude-automata`여야 하며, `claude-automata` 실행 파일과 `init` 커맨드를 노출해야 한다(SHALL). uv만 설치된 머신에서 `uvx --from git+https://github.com/clomia/claude-automata claude-automata init`으로 사전 설치 없이 실행되어야 한다(SHALL).

#### Scenario: uvx로 실행
- **WHEN** uv만 설치된 머신에서 `uvx --from git+<repo-url> claude-automata init`을 실행하면
- **THEN** package가 격리 환경에 resolve되고 `init` 커맨드가 실행된다

### Requirement: Settings prerequisites
`init`은 target repo의 `.claude/settings.json`에 다음 전제조건을 merge-write해야 한다(SHALL): `alwaysThinkingEnabled=true`, `autoMemoryEnabled=false`, `autoCompactEnabled=true`, `model="opus[1m]"`, `permissions.defaultMode="bypassPermissions"`. 기존 파일의 다른 키와 `permissions`의 다른 하위 키는 보존해야 한다(MUST). 재실행은 idempotent해야 한다(MUST).

#### Scenario: settings 파일 부재
- **WHEN** `.claude/settings.json`이 없는 repo에서 init을 실행하면
- **THEN** 전제조건 키 전부를 담은 파일이 생성된다

#### Scenario: 기존 settings 보존
- **WHEN** 무관한 키(`statusLine` 등)와 `permissions.allow`를 가진 settings가 이미 있으면
- **THEN** 무관한 키와 `permissions.allow`는 그대로 남고 전제조건 키만 설정된다

#### Scenario: 재실행 수렴
- **WHEN** init을 두 번 실행하면
- **THEN** 두 번째 실행 후 파일 내용이 첫 실행 결과와 동일하다

### Requirement: Marketplace and plugin registration
`init`은 `extraKnownMarketplaces`에 claude-automata marketplace를 map 형식(`{"claude-automata": {"source": {"source": "github", "repo": "clomia/claude-automata"}}}`)으로 등록하고, marketplace manifest(`.claude-plugin/marketplace.json`)에 열거된 모든 plugin을 `enabledPlugins`에 `"<plugin>@claude-automata": true` 키로 활성화해야 한다(SHALL). plugin 목록의 single home은 marketplace.json이며, CLI는 package에 동봉된 사본을 읽어야 한다(MUST) — 목록을 코드에 중복하지 않는다.

#### Scenario: 등록 완료
- **WHEN** init이 완료되면
- **THEN** settings에 marketplace 항목과 manifest의 모든 plugin(`ploop`·`refine`·`tx`·`version-up-alert`)의 enabled 키가 존재한다

### Requirement: External CLI provisioning
`init`은 `gh`, Node.js ≥ 20(`node`·`npm`·`npx`), `repomix`가 PATH에 있는지 검사하고, 없는 것은 sudo 없이 사용자 영역에 설치해야 한다(SHALL). 이미 있는 도구는 건너뛰어야 한다(MUST). `openspec`은 설치하지 않는다(MUST NOT) — tx plugin이 pin된 버전을 npx로 fetch하며 pin의 single home은 tx다. `gh` 인증은 자동화하지 않고, 미인증이면 `gh auth login` 안내를 출력해야 한다(SHALL).

#### Scenario: 도구가 이미 있음
- **WHEN** `gh`가 PATH에 있으면
- **THEN** 설치를 건너뛰고 satisfied로 보고한다

#### Scenario: 도구 부재 시 사용자 영역 설치
- **WHEN** `node`가 PATH에 없으면
- **THEN** sudo 없이 사용자 영역에 설치되고 이후 `npx`가 동작한다

#### Scenario: 미지원 플랫폼
- **WHEN** 지원하지 않는 플랫폼(예: Windows)에서 실행하면
- **THEN** 실패한 항목과 수동 설치 안내를 출력하고 나머지 항목은 계속 진행한다

### Requirement: Target resolution
`init`은 cwd의 git 최상위를 target repo로 해석해 그곳의 `.claude/settings.json`에 기록해야 한다(SHALL). git repo 밖에서 실행되면 아무것도 쓰지 않고 명확한 오류로 실패해야 한다(MUST). 모든 사용자 대면 출력은 English여야 한다(MUST).

#### Scenario: git repo 밖 실행
- **WHEN** git repo가 아닌 디렉토리에서 init을 실행하면
- **THEN** 파일 변경 없이 오류 메시지와 함께 비정상 종료한다

