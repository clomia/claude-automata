# init-cli Specification

## Purpose
claude-automata 도입의 전제조건 전부를 한 command로 수렴시키는 setup CLI — Claude Code settings, marketplace·plugin 등록, 외부 CLI provisioning.
## Requirements
### Requirement: Zero-install entrypoint
repo root는 Python package `claude-automata`여야 하며, `claude-automata` 실행 파일과 `init` command를 노출해야 한다(SHALL). package는 PyPI에 `claude-automata`로 발행되어야 하며(SHALL), uv만 설치된 machine에서 `uvx claude-automata@latest init`으로 사전 설치 없이 실행되어야 한다(SHALL). 안내되는 실행형은 `@latest`를 포함해야 한다(MUST) — 무지정 `uvx claude-automata`는 캐시된 tool 환경을 재해석 없이 재사용하므로 stale version이 실행될 수 있다. `init`은 첫 줄에 자기 package version을 보고해야 한다(SHALL) — stale 환경의 실행을 산출물에서 판별 가능하게 한다. git source 실행(`uvx --from git+https://github.com/clomia/claude-automata claude-automata init`)도 유효해야 한다(MUST).

#### Scenario: uvx 단축형 실행
- **WHEN** uv만 설치된 machine에서 `uvx claude-automata@latest init`을 실행하면
- **THEN** 캐시 환경 존재 여부와 무관하게 PyPI의 최신 발행 version이 resolve되고 `init` command가 실행된다

#### Scenario: version 자기 보고
- **WHEN** init이 실행되면
- **THEN** 출력 첫 줄에 실행 중인 package version이 나타난다

#### Scenario: uvx로 실행
- **WHEN** `uvx --from git+<repo-url> claude-automata init`을 실행하면
- **THEN** package가 격리 환경에 resolve되고 `init` command가 실행된다

### Requirement: Settings prerequisites
`init`은 target repo의 `.claude/settings.json`에 다음 전제조건을 merge-write해야 한다(SHALL): `alwaysThinkingEnabled=true`, `autoMemoryEnabled=false`, `autoCompactEnabled=true`, `model="opus[1m]"`, `permissions.defaultMode="bypassPermissions"`. 기존 파일의 다른 key와 `permissions`의 다른 하위 key는 보존해야 한다(MUST). 재실행은 idempotent해야 한다(MUST).

#### Scenario: settings 파일 부재
- **WHEN** `.claude/settings.json`이 없는 repo에서 init을 실행하면
- **THEN** 전제조건 key 전부를 담은 파일이 생성된다

#### Scenario: 기존 settings 보존
- **WHEN** 무관한 key(`statusLine` 등)와 `permissions.allow`를 가진 settings가 이미 있으면
- **THEN** 무관한 key와 `permissions.allow`는 그대로 남고 전제조건 key만 설정된다

#### Scenario: 재실행 수렴
- **WHEN** init을 두 번 실행하면
- **THEN** 두 번째 실행 후 파일 내용이 첫 실행 결과와 동일하다

### Requirement: Marketplace and plugin registration
`init`은 `extraKnownMarketplaces`에 claude-automata marketplace를 map 형식(`{"claude-automata": {"source": {"source": "github", "repo": "clomia/claude-automata"}}}`)으로 등록하고, marketplace manifest(`.claude-plugin/marketplace.json`)에 열거된 모든 plugin을 `enabledPlugins`에 `"<plugin>@claude-automata": true` key로 활성화해야 한다(SHALL). plugin 목록의 single home은 marketplace.json이며, CLI는 package에 동봉된 사본을 읽어야 한다(MUST) — 목록을 코드에 중복하지 않는다.

#### Scenario: 등록 완료
- **WHEN** init이 완료되면
- **THEN** settings에 marketplace 항목과 manifest의 모든 plugin(`ploop`·`refine`·`tx`·`version-up-alert`)의 enabled key가 존재한다

### Requirement: External CLI provisioning
`init`은 `gh`, Node.js ≥ 20(`node`·`npm`·`npx`), `repomix`가 PATH에 있는지 검사하고, 없는 것은 sudo 없이 사용자 영역에 설치해야 한다(SHALL). 이미 있는 도구는 건너뛰어야 한다(MUST). `openspec`은 설치하지 않는다(MUST NOT) — tx plugin이 pin된 version을 npx로 fetch하며 pin의 single home은 tx다. `gh` 인증은 자동화하지 않고, 미인증이면 `gh auth login` 안내를 출력해야 한다(SHALL).

#### Scenario: 도구가 이미 있음
- **WHEN** `gh`가 PATH에 있으면
- **THEN** 설치를 건너뛰고 satisfied로 보고한다

#### Scenario: 도구 부재 시 사용자 영역 설치
- **WHEN** `node`가 PATH에 없으면
- **THEN** sudo 없이 사용자 영역에 설치되고 이후 `npx`가 동작한다

#### Scenario: 미지원 platform
- **WHEN** 지원하지 않는 platform(예: Windows)에서 실행하면
- **THEN** 실패한 항목과 수동 설치 안내를 출력하고 나머지 항목은 계속 진행한다

### Requirement: Target resolution
`init`은 cwd의 git 최상위를 target repo로 해석해 그곳의 `.claude/settings.json`에 기록해야 한다(SHALL). git repo 밖에서 실행되면 아무것도 쓰지 않고 명확한 오류로 실패해야 한다(MUST). 모든 사용자 대면 출력은 English여야 한다(MUST).

#### Scenario: git repo 밖 실행
- **WHEN** git repo가 아닌 directory에서 init을 실행하면
- **THEN** 파일 변경 없이 오류 message와 함께 비정상 종료한다

### Requirement: Release publishing
main에 병합된 `pyproject.toml`의 version이 PyPI에 없으면, release workflow가 `uv build`로 산출물을 만들고 PyPI에 발행해야 한다(SHALL). 이미 발행된 version은 재발행을 시도하지 않아야 한다(MUST NOT). 인증은 GitHub Actions OIDC 기반 Trusted Publishing이어야 하며(SHALL) 장기 token을 repo에 보관하지 않는다(MUST NOT).

#### Scenario: 새 version 병합
- **WHEN** PyPI에 없는 version의 pyproject.toml이 main에 병합되면
- **THEN** workflow가 build·publish를 수행해 해당 version이 PyPI에 존재하게 된다

#### Scenario: 기존 version 재실행
- **WHEN** 이미 PyPI에 존재하는 version으로 workflow가 실행되면
- **THEN** publish를 건너뛰고 성공으로 종료한다

### Requirement: Deterministic plugin installation
`init`은 settings 선언에 더해 `claude` CLI로 plugin cache를 직접 수렴해야 한다(SHALL): `claude plugin marketplace add clomia/claude-automata`(idempotent) 후 `claude plugin marketplace update claude-automata`로 listing을 최신화하고, marketplace manifest의 각 plugin 중 target repo에 project scope로 미설치인 것을 `claude plugin install <name>@claude-automata --scope project`로 설치한다. 설치 여부 판별은 `claude plugin list --json`을 oracle로 해야 한다(MUST) — CLI 출력 산문을 파싱하지 않는다. `claude plugin update`는 사용해서는 안 된다(MUST NOT) — scope 자동 감지가 없고 실패에도 exit 0이다(실측). `claude` CLI는 실행 셸의 PATH뿐 아니라 표준 설치 위치(`~/.local/bin/claude`, `~/.claude/local/claude`)에서도 탐지해야 하며(SHALL) — `~/.local/bin`이 PATH에 없는 셸에서 실행돼도 설치된 claude를 놓쳐 false-deferral로 빠지지 않기 위함 —, 찾으면 그 경로로 claude 관리 명령을 실행해야 한다(MUST). 어디에서도 찾지 못할 때만 실패가 아니라 유예로 보고하고(SHALL), 유예 note는 결정론적 remedy(claude를 PATH에 올린 뒤 init 재실행, 또는 `claude plugin install <plugin>@claude-automata --scope project`)를 안내해야 한다(SHALL) — settings 선언은 install 레지스트리(`installed_plugins.json`)를 populate하지 않으므로(실측) 다음 session의 lazy 설치를 약속하지 않는다. 재실행은 idempotent해야 한다(MUST).

#### Scenario: 미설치 repo에서 결정론적 설치
- **WHEN** plugin이 없는 repo에서 claude CLI가 있는 상태로 init이 실행되면
- **THEN** marketplace가 등록·최신화되고 manifest의 전 plugin이 project scope로 cache에 설치되며, 설치된 목록이 보고된다

#### Scenario: 기설치 repo의 재실행
- **WHEN** 전 plugin이 이미 project scope로 설치된 repo에서 init이 재실행되면
- **THEN** 설치 시도 없이 satisfied로 보고된다

#### Scenario: PATH 밖 표준 위치의 claude로 설치
- **WHEN** `claude`가 실행 셸의 PATH에는 없지만 표준 설치 위치에 존재하는 환경에서 init이 실행되면
- **THEN** 유예되지 않고 그 경로의 claude로 marketplace·plugin이 수렴되며, 설치된 목록이 보고된다

#### Scenario: claude CLI 부재 시 유예
- **WHEN** `claude`가 PATH에도 표준 설치 위치에도 없는 환경에서 init이 실행되면
- **THEN** plugin 단계는 유예로 보고되고, claude를 PATH에 올린 뒤 init 재실행(또는 명시적 `claude plugin install --scope project`)을 안내하는 note가 출력된다

#### Scenario: 부분 실패는 계속 진행한다
- **WHEN** 일부 plugin의 install이 실패하면
- **THEN** 나머지 plugin 설치는 계속되고 실패 항목과 사유가 보고되며 init은 비정상 종료 code를 반환한다

