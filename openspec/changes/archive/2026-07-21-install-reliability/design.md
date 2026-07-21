# Design — install-reliability

## Context

설치 실패 3건이 실측됐고 각각의 기전이 확정됐다:

- uvx는 무지정 요청(`uvx claude-automata`)의 캐시 환경을 재해석 없이 재사용한다.
  PyPI에는 무관한 구 prototype v0이 존재하며, v0의 entrypoint는 argv를 directory
  이름으로 취급한다 — 실측된 "`init` directory 생성"과 일치.
- settings 선언만으로는 설치가 다음 session 시작으로 유예되고, 그 lazy 설치가 일어난
  session은 skills를 등록하지 못한다(공식 문서의 mid-session reload 대상 열거에도
  skills가 없다). project settings의 marketplace 선언은 `claude plugin` CLI에 보이지
  않는다 — CLI의 known 목록은 user-level이다(실측).
- claude CLI 실측(v2.1.216): `marketplace add` idempotent(재실행 exit 0) ·
  `marketplace update`는 add 이후에만 성립 · `install --scope project` idempotent +
  의존성 자동 해결 · `update`는 scope 자동 감지가 없고 실패에도 exit 0.

## Goals / Non-Goals

- Goal: 신규 기기·신규 repo에서 "init → restart 1회"가 skills를 포함한 전 component를
  로드하는 결정론적 경로가 되게 한다.
- Goal: stale 환경 실행을 산출물(version 첫 줄)에서 판별 가능하게 한다.
- Non-Goal: 기설치 plugin의 version 상향 — `claude plugin update`가 신뢰 불가
  (exit code 거짓)라 채택하지 않는다. version 수렴은 Claude Code 자체 update 경로와
  version-up-alert plugin의 기존 소관이다.
- Non-Goal: PyPI v0 제거 — yank는 소유자 계정 소관. `@latest`가 코드 측 방어를 완결한다.

## Decisions

- **`@latest`를 안내 실행형에 고정** — `uv cache clean` 안내(기기별 수동 heal)나
  version pin(재발행마다 문서 갱신) 대신, uv가 문서화한 "캐시 무시 최신 재해석"
  suffix를 쓴다. 어떤 기기 상태에서도 동일 명령이 동일 결과를 낸다.
- **설치는 `claude` CLI, 판별은 `list --json`** — 설치 여부를 CLI 산문 파싱으로
  판별하지 않고 구조화 출력(`id`·`scope`·`projectPath`)으로 판별한다. install 자체는
  idempotent이므로 판별 실패 시 전 plugin install로 fall through해도 안전하다.
- **settings 선언 유지** — `extraKnownMarketplaces`·`enabledPlugins`는 repo를 clone한
  collaborator의 lazy 설치 경로이자 인간이 읽는 채택 계약이다. init의 직접 설치는
  첫 기기의 결정론 경로, 선언은 전파 경로 — 둘은 대체가 아니라 상보다.
- **degrade는 유예(deferred), 실패 아님** — claude CLI 부재는 이 기기에서 지금 수렴할
  수 없다는 뜻일 뿐, lazy 경로가 남아 있다. plan-gate(unsupported)와 같은 원리로
  "converge 불가"와 "later converge"를 어휘로 구분한다. note에 `/reload-plugins` 1회
  heal을 실어 관측된 잔존 결함의 복구를 결정론화한다.
- **marketplace add → update 순서 고정** — update는 미등록 시 실패하므로 add(idempotent)
  를 먼저 둔다. update는 기기에 남은 stale listing을 최신화해 신규 install이 최신
  plugin version을 받게 한다.
- **landing-page spec의 bare-form 인용은 그대로 둔다** — 그곳의
  `uvx claude-automata init` literal은 방문자 표면에서 배제되는 대상의 식별자이지 안내
  실행형이 아니고, 배제는 명령의 모든 형태에 적용된다. 형태의 정본은 init-cli spec과
  INSTALL.md다. 대형 requirement 2건의 MODIFIED 전문 복사 비용이 정보 이득을 초과한다.

## Risks / Trade-offs

- [claude CLI 산문·JSON schema가 version에 따라 변할 수 있다] → 파싱은 `list --json`의
  안정 field 3개(`id`·`scope`·`projectPath`)만 소비한다. 그마저 실패하면 전 plugin
  install fall through — install의 idempotency가 오동작을 막는다.
- [세 CLI 호출 모두 네트워크 의존] → 각 단계 실패는 사유와 함께 보고하고 init은
  비정상 종료 code를 반환한다 — 사유 해소 후 재실행이 복구 경로다. settings 선언은
  이미 기록되어 있어 lazy 경로도 잔존한다. note 유예는 claude CLI 부재에만 결부한다.
- [`install --scope project`가 target repo의 `.claude/settings.json`을 재기록] →
  init의 settings write 이후에 실행해 최종 내용이 양쪽 key의 합집합으로 수렴함을
  테스트로 고정한다.

## Migration Plan

merge 시 publish.yml이 0.2.0을 자동 발행한다. 기존 문서(`README` Getting started)는
INSTALL.md를 가리키므로 INSTALL.md 갱신으로 전파가 완결된다. rollback은 version 재발행
없이 INSTALL.md의 실행형만 되돌리면 구 경로(선언 + lazy)로 복귀한다 — 직접 설치는
additive라 구 경로를 깨지 않는다.

## Open Questions

없음.
