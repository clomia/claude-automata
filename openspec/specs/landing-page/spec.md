# landing-page Specification

## Purpose
TBD - created by archiving change landing-page. Update Purpose after archive.
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

### Requirement: Site 내용 계약
사이트는 English 단일 page여야 하며(SHALL) 다음을 실어야 한다(SHALL): 기억 system 시각화
(작업기억 → 응고 gate → 장기기억 → 재접지 주기), plugin 4종(ploop·refine·tx·version-up-alert)
각각의 소개와 정본 link, `uvx claude-automata init` 단일 설치 경로와 init이 실제로 쓰는
settings의 공개(`permissions.defaultMode="bypassPermissions"`·`model="opus[1m]"` 포함),
Anthropic 비공식(unaffiliated) 고지. 반응형이어야 하고(MUST — viewport meta + 소형 화면
대응), 정본 본문을 복제해서는 안 된다(MUST NOT) — 요약과 link만.

#### Scenario: init 실동작 공개
- **WHEN** 방문자가 getting-started 절을 읽으면
- **THEN** init이 기록하는 settings 전제조건(bypassPermissions·model 고정 포함)이 명시되어 있다

#### Scenario: 비공식 고지
- **WHEN** page를 열면
- **THEN** Anthropic과 무관한(unaffiliated) project임이 명시되어 있다

### Requirement: README 관문화
`README.md`·`README.ko.md`는 쌍으로 유지되어야 하며(MUST), 각각 정체 한 줄 + plugin
인벤토리 + 설치(init 단일 경로, 실동작 공개) + 사이트 link로 열어야 한다(SHALL). plugin
섹션 heading은 문서 title(h1) 아래 h2여야 하고(MUST), plugin별 개별 Install·Update 안내를
포함해서는 안 된다(MUST NOT).

#### Scenario: 관문 구조
- **WHEN** 방문자가 README 상단만 읽으면
- **THEN** 무엇인지(정체), 무엇이 들었는지(인벤토리), 어떻게 시작하는지(init), 어디서 더
  보는지(사이트 link)를 얻는다

