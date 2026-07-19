## MODIFIED Requirements

### Requirement: Site 내용 계약
사이트는 English 단일 page여야 하며(SHALL) 다음을 실어야 한다(SHALL): 기억 system 시각화
(작업기억 → 응고 gate → 장기기억 → 재접지 주기), plugin 4종(ploop·refine·tx·version-up-alert)
각각의 소개와 정본 link, `uvx claude-automata init` 단일 설치 경로와 init이 실제로 쓰는
settings의 공개(`permissions.defaultMode="bypassPermissions"`·`model="opus[1m]"` 포함),
Anthropic 비공식(unaffiliated) 고지. 기억 시각화는 hero의 서술 산문(thesis)에 선행해야
한다(MUST) — text는 그래픽을 뒤따르는 보조다. 공유 link unfurl을 위한 Open Graph·Twitter
Card metadata와 share image를 실어야 한다(SHALL). init 공개의 값은 `claude_automata/settings.py`의
실값과 CI로 결속되어야 하며(SHALL — 값 표류 시 PR이 실패한다), share image(og.png)는 그
source(og-card.html)의 변경과 동반이 강제되어야 한다(MUST). 방문자 표면(site·README 쌍)의
repo-내부 정본 link(blob·tree 경로)는 대상 경로의 존재가 CI로 검증되어야 한다(SHALL —
외부 link는 network 비결정성으로 결속하지 않는다). 반응형이어야 하고(MUST —
viewport meta + 소형 화면 대응), 정본 본문을 복제해서는 안 된다(MUST NOT) — 요약과 link만.

#### Scenario: init 실동작 공개
- **WHEN** 방문자가 getting-started 절을 읽으면
- **THEN** init이 기록하는 settings 전제조건(bypassPermissions·model 고정 포함)이 명시되어 있다

#### Scenario: 비공식 고지
- **WHEN** page를 열면
- **THEN** Anthropic과 무관한(unaffiliated) project임이 명시되어 있다

#### Scenario: 그래픽 우선
- **WHEN** page가 열리면
- **THEN** 기억 시각화가 문서 순서상 thesis 산문보다 앞에 있다

#### Scenario: 공유 unfurl
- **WHEN** page URL이 OG를 소비하는 채널에 공유되면
- **THEN** og:title·og:description·og:image가 해석 가능한 절대 URL로 존재한다

#### Scenario: init 공개 값 표류 차단
- **WHEN** `settings.py`의 전제조건 값이 바뀌고 방문자 표면(site·README 쌍)이 그대로인 PR이 열리면
- **THEN** CI가 실패해 관문이 거짓 공개를 게시하기 전에 차단한다

#### Scenario: share image 결속
- **WHEN** og-card.html을 수정하고 og.png를 재생성하지 않은 PR이 열리면
- **THEN** CI가 실패한다

#### Scenario: 정본 link 존재 결속
- **WHEN** 방문자 표면이 가리키는 repo-내부 경로가 tree에서 사라진 PR이 열리면
- **THEN** CI가 실패해 관문이 404를 안내하기 전에 차단한다
