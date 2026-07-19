## MODIFIED Requirements

### Requirement: Site 내용 계약
사이트는 English 단일 page여야 하며(SHALL) 다음을 실어야 한다(SHALL): 기억 system 시각화
(작업기억 → 응고 gate → 장기기억 → 재접지 주기), advisor의 정지-차단·재소집 기제를 보여주는
show-don't-tell 표현, plugin 4종(ploop·refine·tx·version-up-alert) 각각의 소개, `uvx
claude-automata init` 단일 설치 경로와 init이 실제로 쓰는 settings의 공개
(`permissions.defaultMode="bypassPermissions"`·`model="opus[1m]"` 포함), Anthropic
비공식(unaffiliated) 고지. **사이트의 이해는 자체 완결이어야 한다(MUST)** — page를 떠나지
않고 스크롤만으로 정체·기제·가치·시작법이 전달되며, repo 문서 link는 보조 SOURCE
pointer로만 존재한다. 기억 시각화는 hero의 서술 산문에 선행해야 한다(MUST). 공유 link
unfurl을 위한 Open Graph·Twitter Card metadata와 share image를 실어야 한다(SHALL). 한국어 변형이 `/ko/` 경로에 존재해야 하며(SHALL — default는 English, 언어 toggle
상호 연결, 한국어 기반 + native 영어 어휘), init 공개·link 결속 검증의 표면에
포함되어야 한다(MUST). init
공개의 값은 `claude_automata/settings.py`의 실값과 CI로 결속되어야 하며(SHALL), 생성
image(og.png·banner.png)는 각자의 committed source(og-card.html·banner-card.html) 변경과
동반이 강제되어야 한다(MUST). 방문자 표면(site·README 쌍)의 repo-내부 link(blob·tree
경로)는 대상 경로의 존재가 CI로 검증되어야 한다(SHALL — 외부 link는 network 비결정성으로
결속하지 않는다). 반응형이어야 하고(MUST), 정본 본문을 복제해서는 안 된다(MUST NOT) —
자체 완결은 이해의 완결이지 정본 전문의 이식이 아니다.

#### Scenario: init 실동작 공개
- **WHEN** 방문자가 getting-started 절을 읽으면
- **THEN** init이 기록하는 settings 전제조건(bypassPermissions·model 고정 포함)이 명시되어 있다

#### Scenario: 비공식 고지
- **WHEN** page를 열면
- **THEN** Anthropic과 무관한(unaffiliated) project임이 명시되어 있다

#### Scenario: 그래픽 우선
- **WHEN** page가 열리면
- **THEN** 기억 시각화가 문서 순서상 hero 서술 산문보다 앞에 있다

#### Scenario: 자체 완결 이해
- **WHEN** 방문자가 외부 link를 하나도 열지 않고 page를 끝까지 스크롤하면
- **THEN** 무엇인지·advisor 기제·기억 구조·시작법이 전부 전달된다

#### Scenario: 한국어 page
- **WHEN** 방문자가 `/ko/` 경로에 접속하거나 언어 toggle로 KO를 선택하면
- **THEN** 같은 구조의 한국어 기반 page가 표시되고, default 경로(`/`)는 English로
  유지되며, 두 page가 hreflang으로 상호 선언된다

#### Scenario: 공유 unfurl
- **WHEN** page URL이 OG를 소비하는 채널에 공유되면
- **THEN** og:title·og:description·og:image가 해석 가능한 절대 URL로 존재한다

#### Scenario: init 공개 값 표류 차단
- **WHEN** `settings.py`의 전제조건 값이 바뀌고 방문자 표면(site·README 쌍)이 그대로인 PR이 열리면
- **THEN** CI가 실패해 관문이 거짓 공개를 게시하기 전에 차단한다

#### Scenario: 생성 image 결속
- **WHEN** og-card.html 또는 banner-card.html을 수정하고 대응 PNG를 재생성하지 않은 PR이 열리면
- **THEN** CI가 실패한다

#### Scenario: 정본 link 존재 결속
- **WHEN** 방문자 표면이 가리키는 repo-내부 경로가 tree에서 사라진 PR이 열리면
- **THEN** CI가 실패해 관문이 404를 안내하기 전에 차단한다

### Requirement: README 관문화
`README.md`·`README.ko.md`는 쌍으로 유지되어야 하며(MUST), 각각 banner image + 한 줄
tagline + plugin 인벤토리 + 설치(init 단일 경로, 실동작 공개) + 사이트로의 초대 hook으로
열어야 한다(SHALL). 사이트 hook은 "Landing page" 같은 일반 명칭이 아니라 내용을 예고하는
초대 문구여야 한다(MUST). README는 내부 개발 정본(ARCHITECTURE.md·MEMORY.md)을 참조해서는
안 된다(MUST NOT) — 방문자의 이해 경로는 README와 사이트로 완결된다. 섹션 heading은 h2
이하여야 하고(MUST — 문서 최상위 자리는 banner·tagline이 대신하며 h1을 두지 않는다),
plugin별 개별 Install·Update 안내를 포함해서는 안 되며(MUST NOT), 상세 사용법은
접힘(`<details>`)으로 점진 공개한다(SHOULD).

#### Scenario: 관문 구조
- **WHEN** 방문자가 README 상단만 읽으면
- **THEN** 무엇인지(banner·tagline), 무엇이 들었는지(인벤토리), 어떻게 시작하는지(init),
  어디서 더 보는지(사이트 초대 hook)를 얻는다

#### Scenario: 내부 정본 비참조
- **WHEN** README 어디에서든 link를 따라가면
- **THEN** ARCHITECTURE.md·MEMORY.md로 이동하는 경로가 없다
