## Why

claude-automata의 정체 — 인간 기억 구조를 사상한 24시간 자율 agent 환경 — 를 처음 방문자가
알려면 repo 전체를 정독해야 한다. README는 plugin 4개를 나열할 뿐 세계관을 운반하지 못하고
(상단 인벤토리 부재, init 실동작 미공개, install 서사 이원화, heading 위계 붕괴), markdown에는
기억 system을 직관적으로 보여줄 표현력이 없다. 시각적 관문(landing page)과 그리로 유도하는
간결한 README가 이해 비용을 "repo 정독"에서 "수 분"으로 줄인다.

## What Changes

- **landing page 신설** (`site/`, English 단일, 정적 — framework 0): 기억 system 시각화를
  핵심 산출물로 하는 단일 page 서사. 정체·가치, plugin 4종 한 단락씩 + 정본 link,
  `uvx claude-automata init` 단일 설치 경로(bypassPermissions·model 고정 포함 실동작 공개),
  Anthropic 비공식(unaffiliated) 고지, mobile 반응형. 정본 내용은 복제하지 않는다 —
  요약과 link만.
- **GitHub Pages 배포**: `.github/workflows/pages.yml` 신설 — `site/`를 GitHub 공식
  actions(upload-pages-artifact·deploy-pages)로 발행. site source로 `docs/`를 쓰지 않는다
  (`docs/research/`는 조사 기록의 home) — branch 배포는 root/`docs/`만 지원하므로
  workflow 배포가 유일한 경로다. Pages 활성화(`build_type=workflow`)는 `gh api`로 수행.
- **README 간결화** (한·영 쌍): 정체 한 줄 + 상단 plugin 인벤토리 + init 단일 설치 경로
  (실동작 공개) + 사이트 link 중심. plugin별 Install·Update 블록 제거, plugin 섹션 h1→h2
  위계 복구.
- **root package 0.1.1**: README가 PyPI long_description이므로 version bump로 재발행을
  유도해 PyPI 표면도 새 관문과 정합시킨다.

## Capabilities

### New Capabilities

- `landing-page`: 방문자 관문의 지속 계약 — site source의 위치와 정적성, Pages 배포
  workflow, 사이트가 항구적으로 실어야 할 내용(기억 시각화·plugin 4종·init 실동작 공개·
  unaffiliated 고지·반응형), README 쌍의 사이트 유도.

### Modified Capabilities

<!-- 없음 — init-cli 등 기존 capability의 요구사항 불변 -->

## Impact

- 신규: `site/` (index.html·css·assets), `.github/workflows/pages.yml`,
  `openspec/specs/landing-page/` (archive 시)
- 수정: `README.md`·`README.ko.md`, root `pyproject.toml`(version만)
- server-side: GitHub Pages 활성화 (repo 설정, `gh api`)
- plugin 구현·behavior 불변 — plugin version bump 없음
