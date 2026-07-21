# landing-page Specification

## Purpose
방문자 관문의 지속 계약 — 처음 방문자가 수 분 안에 "무엇인지 → 왜 가치 있는지 → 어떻게 시작하는지"를 얻도록, landing page(site/ 정적 산출물과 Pages 배포)와 README 쌍이 항구적으로 실어야 할 내용과 형태를 고정한다.
## Requirements
### Requirement: Site source — static, in `site/`
landing page의 source는 `site/`에 있어야 하며(SHALL), build step 없이 그대로 serve 가능한
정적 파일(html·css·js·assets)이어야 한다(MUST). 외부 framework·라이브러리에 의존해서는
안 된다(MUST NOT). `docs/`를 site source로 사용해서는 안 된다(MUST NOT) — `docs/research/`는
조사 기록의 home이다.

#### Scenario: 정적 무의존 serve
- **WHEN** `site/`를 임의의 정적 file server로 그대로 serve하면
- **THEN** build 도구·package 설치 없이 page가 완전히 rendering된다

### Requirement: GitHub Pages 배포 workflow
`.github/workflows/pages.yml`은 main push 시 `site/`를 GitHub 공식 Pages actions로 발행해야
하며(SHALL), 수동 trigger(`workflow_dispatch`)를 지원해야 한다(MUST). site 외 경로만 바뀐
push에는 발행이 불필요하므로 `site/`·workflow 자신으로 path filter해야 한다(SHOULD).

#### Scenario: main 병합 후 자동 발행
- **WHEN** `site/` 변경이 main에 병합되면
- **THEN** workflow가 `site/`를 artifact로 올려 GitHub Pages에 배포한다

### Requirement: README 관문화
`README.md`·`README.ko.md`는 쌍으로 유지되어야 하며(MUST), 각각 banner image + 한 줄
tagline + plugin 인벤토리 + 설치 + 사이트로의 초대 hook으로 열어야 한다(SHALL). 설치 절은
agent 위임 prompt만 실어야 한다(SHALL) — `INSTALL.md`를 읽고 이 repository에 설치하라는
복사형 한 줄 prompt와 그 문서로의 link. `uvx claude-automata init` 명령·init 실동작 공개를
방문자 표면에 실어서는 안 된다(MUST NOT — 설치는 agent가 INSTALL.md로 수행하며, 공개의
home은 INSTALL.md다). 사이트 hook은 "Landing page" 같은 일반 명칭이 아니라 내용을 예고하는
초대 문구여야 한다(MUST). README는 내부 개발 정본(ARCHITECTURE.md·MEMORY.md)을 참조해서는
안 된다(MUST NOT) — 방문자의 이해 경로는 README·사이트·INSTALL.md로 완결된다. 섹션 heading은 h2
이하여야 하고(MUST — 문서 최상위 자리는 banner·tagline이 대신하며 h1을 두지 않는다),
plugin별 개별 Install·Update 안내를 포함해서는 안 되며(MUST NOT), 상세 사용법은
접힘(`<details>`)으로 점진 공개한다(SHOULD).

#### Scenario: 관문 구조
- **WHEN** 방문자가 README 상단만 읽으면
- **THEN** 무엇인지(banner·tagline), 무엇이 들었는지(인벤토리), 어떻게 시작하는지(agent에게
  건넬 prompt), 어디서 더 보는지(사이트 초대 hook)를 얻는다

#### Scenario: 내부 정본 비참조
- **WHEN** README 어디에서든 link를 따라가면
- **THEN** ARCHITECTURE.md·MEMORY.md로 이동하는 경로가 없다

#### Scenario: init 명령 부재
- **WHEN** 방문자가 README의 설치 절을 읽으면
- **THEN** 위임 prompt만 있고 `uvx claude-automata init` 명령·settings 공개 표가 없다

### Requirement: Site 서사 계약

사이트의 default page(`/`)는 English 단일 서사여야 하며(SHALL) 다음을 실어야 한다(SHALL):
기억 system 시각화(작업기억 → 응고 gate → 장기기억 → 재접지 주기), advisor의
정지-차단·재소집 기제를 보여주는 show-don't-tell 표현, plugin 3종(ploop·tx·refine)
각각의 소개, getting-started의 단일 설치 경로 — agent 위임(`INSTALL.md`를 지시하는 복사형
prompt)만 실어야 하며(SHALL), `uvx claude-automata init` 명령·init settings 공개 표를
방문자 표면에 실어서는 안 된다(MUST NOT — 공개의 home은 INSTALL.md이고 getting-started는
그 문서로 link한다) — 그리고 모든
기여가 이 환경을 돌리는 Claude Code agent에 의해 작성된다는 자기개발(재귀적 자기개선)
표기. version-up-alert는 기억 이론 밖의 add-on이므로 방문자 표면에서 다루지 않는다(MUST
NOT). **사이트의 이해는 자체 완결이어야 한다(MUST)** — page를 떠나지 않고 스크롤만으로
정체·기제·가치·시작법이 전달되며, module 소개는 정본 link를 두지 않는다(MUST NOT — page의 repo
link들은 전부 repo root와 INSTALL.md 두 곳으로만 수렴한다). 기억 시각화는 hero의 서술 산문에
선행해야 한다(MUST). 한국어 변형이 `/ko/` 경로에 존재해야 하며(SHALL — default는 English, 언어
toggle 상호 연결, 한국어 기반 + native 영어 어휘), link 결속 검증의 표면에
포함되어야 한다(MUST). 공유 link unfurl을 위한 Open Graph·Twitter Card metadata와 share
image를 실어야 한다(SHALL). init settings 공개의 값은 `claude_automata/settings.py`의 실값과
CI로 결속되어야 하며(SHALL — 결박 표면은 방문자 표면이 아니라 `INSTALL.md`다),
생성 image(og.png·banner.png)는 각자의 committed
source(og-card.html·banner-card.html) 변경과 동반이 강제되어야 한다(MUST). 방문자
표면(site en·ko, README 쌍)의 repo-내부 link(blob·tree·raw 경로)는 대상 경로의 존재가
CI로 검증되어야 한다(SHALL — 외부 link는 network 비결정성으로 결속하지 않는다).
반응형이어야 하고(MUST), 정본 본문을 복제해서는 안 된다(MUST NOT) — 자체 완결은 이해의
완결이지 정본 전문의 이식이 아니다.

#### Scenario: init 실동작 공개
- **WHEN** 방문자가 getting-started 절을 읽으면
- **THEN** `INSTALL.md`를 지시하는 복사형 위임 prompt와 그 문서로의 link가 있고,
  `uvx claude-automata init` 명령·init settings 공개 표는 이 표면에 없다 — init 실동작
  공개의 home은 INSTALL.md다

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
- **WHEN** `settings.py`의 전제조건 값이 바뀌고 `INSTALL.md`가 그대로인 PR이 열리면
- **THEN** CI가 실패해 공개가 거짓이 되기 전에 차단한다

#### Scenario: share image 결속
- **WHEN** og-card.html 또는 banner-card.html을 수정하고 대응 PNG를 재생성하지 않은 PR이 열리면
- **THEN** CI가 실패한다

#### Scenario: 정본 link 존재 결속
- **WHEN** 방문자 표면이 가리키는 repo-내부 경로가 tree에서 사라진 PR이 열리면
- **THEN** CI가 실패해 관문이 404를 안내하기 전에 차단한다

### Requirement: Agent install canon — INSTALL.md
repo root의 `INSTALL.md`는 설치를 수행할 agent 대상의 English 단일본이어야 하며(SHALL),
방법 절차가 아니라 **installed state** — 전부 참이면 설치된 것인 검증 가능한 술어 집합 —
를 서술해야 한다(SHALL). 상태 oracle(init 출력·seed 보고·openspec validate·CI)을 지정해야
하고(MUST), host repository의 기존 harness를 존중하는 경계 — 동결 이력 불가침, 소급 재구성
금지, repo 소유 결정의 사용자 귀속 — 를 installed state의 술어로 포함해야 한다(MUST).
init이 기록하는 settings 전제조건(`permissions.defaultMode="bypassPermissions"`·
`model="opus[1m]"`·flag 3종·marketplace 등록)을 installed state의 일부로 공개해야 하며(SHALL —
방문자 표면이 아니라 여기가 공개의 home이다), 그 값은 `claude_automata/settings.py`의 실값과
CI로 결속되어야 한다(MUST). init이 기록하는 settings가 세션 재시작으로만 발효하고 plugin이
세션 시작 시 로드되므로, installed state는 **init 이후의 세션 재시작을 별도 술어로 요구해야
하며(SHALL)** — 재시작 전에는 tx skill이 없어 transaction 술어가 성립 불가다 — 설치 agent가
자기 세션을 재시작할 수 없다는 사실과 그 재시작을 사용자에게 표면화해야 한다는 것을
술어에 담아야 한다(MUST). 명령 시퀀스·단계 절차를 강제해서는 안 되며(MUST NOT — 경로는
대상 repo의 agent가 도출한다), 내부 개발 정본(ARCHITECTURE.md·MEMORY.md)을 참조해서는 안
된다(MUST NOT).

#### Scenario: 성공 상태 서술
- **WHEN** agent가 INSTALL.md만 읽고 임의의 기 구축 repository에서 설치를 수행하면
- **THEN** 도달할 상태와 각 술어의 검증 oracle이 전부 주어지고, 경로·순서는 문서가
  강제하지 않는다

#### Scenario: host harness 존중
- **WHEN** 대상 repository에 자체 CLAUDE.md·rules·CI·문서 체계가 있으면
- **THEN** installed state의 술어가 그 보존을 요구하고, 충돌 시 사용자 결정 귀속을 요구한다

#### Scenario: settings 공개의 home
- **WHEN** 신중한 사용자가 위임 prompt를 건네기 전에 INSTALL.md를 읽으면
- **THEN** init이 기록하는 settings(bypassPermissions·model 고정 포함)가 명시되어 있고,
  그 값은 settings.py와 CI로 결박되어 표류하지 않는다

#### Scenario: 재시작 관문
- **WHEN** 설치 agent가 init을 실행한 세션에서 곧바로 다음 단계로 나아가려 하면
- **THEN** installed state가 init 이후의 세션 재시작을 요구하고(재시작 전에는 plugin·tx
  skill이 없다), agent는 스스로 재시작할 수 없으므로 그 재시작을 사용자에게 표면화한다

