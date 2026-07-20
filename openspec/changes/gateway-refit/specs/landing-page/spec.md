## REMOVED Requirements

### Requirement: Site 내용 계약

**Reason**: 소유자 지시로 계약의 세 축이 바뀐다 — version-up-alert는 이론 밖 add-on이라
방문자 표면에서 다루지 않고, module 정본 link는 자체 완결을 해치므로 금지되며,
unaffiliated 고지는 불필요 판정으로 폐기되고 그 자리를 자기개발 표기가 대신한다.
scenario 집합이 함께 재편되므로 요구를 재작성한다.

**Migration**: 후속 "Site 서사 계약"이 나머지 결속(init 공개·image 쌍·내부 link 존재·
반응형·한국어 변형·정본 비복제)을 그대로 승계한다.

## ADDED Requirements

### Requirement: Site 서사 계약

사이트의 default page(`/`)는 English 단일 서사여야 하며(SHALL) 다음을 실어야 한다(SHALL):
기억 system 시각화(작업기억 → 응고 gate → 장기기억 → 재접지 주기), advisor의
정지-차단·재소집 기제를 보여주는 show-don't-tell 표현, plugin 3종(ploop·tx·refine)
각각의 소개, `uvx claude-automata init` 단일 설치 경로와 init이 실제로 쓰는 settings의
공개(`permissions.defaultMode="bypassPermissions"`·`model="opus[1m]"` 포함), 그리고 모든
기여가 이 환경을 돌리는 Claude Code agent에 의해 작성된다는 자기개발(재귀적 자기개선)
표기. version-up-alert는 기억 이론 밖의 add-on이므로 방문자 표면에서 다루지 않는다(MUST
NOT). **사이트의 이해는 자체 완결이어야 한다(MUST)** — page를 떠나지 않고 스크롤만으로
정체·기제·가치·시작법이 전달되며, module 소개는 정본 link를 두지 않는다(MUST NOT — repo
진입점은 titleblock의 GitHub link 하나다). 기억 시각화는 hero의 서술 산문에 선행해야
한다(MUST). 한국어 변형이 `/ko/` 경로에 존재해야 하며(SHALL — default는 English, 언어
toggle 상호 연결, 한국어 기반 + native 영어 어휘), init 공개·link 결속 검증의 표면에
포함되어야 한다(MUST). 공유 link unfurl을 위한 Open Graph·Twitter Card metadata와 share
image를 실어야 한다(SHALL). init 공개의 값은 `claude_automata/settings.py`의 실값과 CI로
결속되어야 하며(SHALL), 생성 image(og.png·banner.png)는 각자의 committed
source(og-card.html·banner-card.html) 변경과 동반이 강제되어야 한다(MUST). 방문자
표면(site en·ko, README 쌍)의 repo-내부 link(blob·tree·raw 경로)는 대상 경로의 존재가
CI로 검증되어야 한다(SHALL — 외부 link는 network 비결정성으로 결속하지 않는다).
반응형이어야 하고(MUST), 정본 본문을 복제해서는 안 된다(MUST NOT) — 자체 완결은 이해의
완결이지 정본 전문의 이식이 아니다.

#### Scenario: init 실동작 공개
- **WHEN** 방문자가 getting-started 절을 읽으면
- **THEN** init이 기록하는 settings 전제조건(bypassPermissions·model 고정 포함)이 명시되어 있다

#### Scenario: 그래픽 우선
- **WHEN** page가 열리면
- **THEN** 기억 시각화가 문서 순서상 hero 서술 산문보다 앞에 있다

#### Scenario: 자체 완결 이해
- **WHEN** 방문자가 외부 link를 하나도 열지 않고 page를 끝까지 스크롤하면
- **THEN** 무엇인지·advisor 기제·기억 구조·시작법이 전부 전달되고, module 절에 정본
  link가 없으며, version-up-alert가 등장하지 않는다

#### Scenario: 자기개발 표기
- **WHEN** 방문자가 page를 끝까지 읽으면
- **THEN** 모든 기여가 Claude Code agent 작성이라는 사실이 명시되어 있다

#### Scenario: 한국어 page
- **WHEN** 방문자가 `/ko/` 경로에 접속하거나 언어 toggle로 KO를 선택하면
- **THEN** 같은 구조의 한국어 기반 page가 표시되고, default 경로(`/`)는 English로
  유지되며, 두 page가 hreflang으로 상호 선언된다

#### Scenario: 공유 unfurl
- **WHEN** page URL이 OG를 소비하는 채널에 공유되면
- **THEN** og:title·og:description·og:image가 해석 가능한 절대 URL로 존재한다

#### Scenario: init 공개 값 표류 차단
- **WHEN** `settings.py`의 전제조건 값이 바뀌고 방문자 표면이 그대로인 PR이 열리면
- **THEN** CI가 실패해 관문이 거짓 공개를 게시하기 전에 차단한다

#### Scenario: share image 결속
- **WHEN** og-card.html 또는 banner-card.html을 수정하고 대응 PNG를 재생성하지 않은 PR이 열리면
- **THEN** CI가 실패한다

#### Scenario: 정본 link 존재 결속
- **WHEN** 방문자 표면이 가리키는 repo-내부 경로가 tree에서 사라진 PR이 열리면
- **THEN** CI가 실패해 관문이 404를 안내하기 전에 차단한다
