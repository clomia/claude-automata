# Proposal — install-reliability

## Why

다양한 기기·repo에서의 설치 시나리오 실측에서 서로 다른 결함 3건이 발화했다.

1. **stale uvx 환경.** PyPI `claude-automata`에는 현 project와 무관한 구 prototype
   version `0`(2026-03-27, copier 기반 scaffolder — argv를 directory 이름으로 취급)이
   존재한다. uvx는 tool 환경을 캐시하고 재해석하지 않으므로, 과거에
   `uvx claude-automata`를 실행한 기기는 오늘도 v0을 재사용한다 — 실측된 이상동작
   (`init` directory 생성)과 정확히 일치한다. 현 spec의 "PyPI의 최신 발행 version이
   resolve된다"는 가정은 warm cache에서 거짓이다.
2. **lazy install의 skills 유실.** init은 settings(`extraKnownMarketplaces`·
   `enabledPlugins`)만 선언하고 실제 설치는 다음 session 시작의 lazy 경로에 맡긴다.
   실측: 설치가 일어나는 그 session은 skills를 등록하지 못한다 — restart 후 skills
   부재 → `/reload-plugins`로 복구, 혹은 restart 없이 `/reload-plugins` 시 skills만
   부재. 공식 문서도 mid-session reload가 전환하는 대상을 hooks·MCP·LSP로만 열거한다.
   또한 실측상 project settings의 marketplace 선언은 `claude plugin` CLI에 보이지
   않는다(user-level 등록 필요).
3. **stale 판별 불가.** init 출력에 자기 version이 없어, stale 환경이 실행돼도
   산출물로는 구분되지 않는다.

## What Changes

- **entrypoint 강화** — 안내되는 실행형을 `uvx claude-automata@latest init`으로
  변경한다. `@latest`는 uvx가 캐시 환경을 재사용하지 않고 최신 발행 version을
  재해석하게 한다. init은 첫 줄에 자기 version을 보고한다.
- **결정론적 plugin 설치** — init이 `claude` CLI로 수렴을 직접 수행한다:
  `plugin marketplace add`(idempotent, user-level 등록) → `plugin marketplace update`
  (listing 최신화) → manifest의 각 plugin에 `plugin install <name>@claude-automata
  --scope project`(idempotent, cache 설치 + 의존성 자동 해결). 이후 restart는 이미
  채워진 cache에서 skills를 포함한 전 component를 로드한다 — 공식 문서의 정상 경로다.
  settings 선언(`extraKnownMarketplaces`·`enabledPlugins`)은 유지한다 — repo를
  clone하는 collaborator의 lazy 설치 경로다.
- **graceful degrade** — `claude` CLI 부재 시 실패가 아니라 lazy 경로로 유예하고,
  restart 후 skills 부재 시 `/reload-plugins` 1회로 복구하라는 note를 남긴다.
- **INSTALL.md 재설계** — installed state에 위 수렴을 반영: 단일 restart로 skills가
  로드되는 것이 정상 경로이고, 그래도 tx skills가 부재하면 `/reload-plugins` 1회가
  heal이다. `claude plugin update`는 채택하지 않는다(scope 자동 감지 부재, 실패에도
  exit 0 — 실측).
- **version bump** — claude-automata 0.1.15 → 0.2.0 (publish.yml이 merge 시 자동 발행).

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `init-cli`: Zero-install entrypoint에 `@latest` 형식과 version 자기 보고를 반영,
  plugin 설치를 settings 선언에서 "선언 + 결정론적 cache 수렴"으로 강화하는
  requirement 추가.

## Impact

- `claude_automata/plugins.py`(신규) · `claude_automata/cli.py` · `tests/test_plugins.py`(신규)
- `INSTALL.md` · `openspec/specs/init-cli/spec.md`
- `pyproject.toml` (0.2.0 — publish.yml 자동 발행 경로)
- PyPI v0 yank는 소유자 계정 소관으로 이 change 밖이다 — `@latest`가 코드 측 방어를
  완결한다.
