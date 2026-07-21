## Why

방금 배포한 agent-delegated 설치 흐름에 실측 결함 하나와 표면 교정 둘이 남았다.

1. **재시작 관문이 미명세다.** init은 `enabledPlugins`·`model`·`bypassPermissions`를
   settings.json에 쓰지만 plugin은 세션 시작 시에만 로드된다. 따라서 init 직후의 세션에는
   tx plugin이 없어 `/tx:open`(seed·transaction)이 존재하지 않는다 — 재시작은 편의가 아니라
   init과 첫 transaction 사이의 필수 관문이다. 설치 agent는 자기 세션을 재시작할 수 없으므로
   그 재시작을 사용자에게 표면화해야 한다. INSTALL.md는 이를 첫 술어의 부속절로만 묻어놨다.
2. **prompt URL이 blob이다.** 위임 prompt의 소비자는 Claude Code(WebFetch로 fetch)다. blob은
   GitHub HTML 페이지라, raw 마크다운을 직접 주는 편이 fetch에 확실하다.
3. **방문자 산문에 em-dash slop.** 이번에 쓴 getting-started 산문이 `— … —` 삽입구를 써
   AI 티가 난다. 내부 canon의 em-dash 하우스 스타일과 달리 방문자 표면은 사람이 읽고 제품을
   판단하는 곳이라 자연스러운 산문이어야 한다.

## What Changes

- **INSTALL.md 재시작 술어** — init-수렴 술어에서 재시작을 분리해 독립 installed-state
  술어로: init 이후 재시작되어 plugin·settings가 live이며, agent가 스스로 재시작 못 하므로
  그 재시작을 사용자에게 표면화한다. transaction 술어가 이 재시작에 후행함을 명시한다.
- **위임 prompt를 raw URL로** — 4개 방문자 표면의 prompt URL을
  `raw.githubusercontent.com/clomia/claude-automata/refs/heads/main/INSTALL.md`로. 산문 속
  클릭용 `INSTALL.md` 링크는 blob 유지(사람이 브라우저에서 읽는다).
- **canon-links 정규식 확장** — raw 형식을 `main`과 `refs/heads/main` 둘 다 매칭하도록 해
  raw prompt URL의 존재 결박을 유지한다.
- **em-dash slop 제거** — INSTALL.md·README 쌍·site 쌍에서 이번에 쓴 산문의 `— … —`
  삽입구를 쉼표·괄호·문장 분리로 자연화한다.
- version bump 없음 — plugin·package 구현 불변.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `landing-page`: Agent install canon requirement에 재시작 관문 술어를 추가하고 그 scenario를
  잠근다. raw URL·slop 제거는 기존 계약 안이라 문구 변경뿐(spec은 이미 raw 경로를 상정).

## Impact

- `INSTALL.md` (재시작 술어 + slop 제거)
- `README.md` · `README.ko.md` · `site/index.html` · `site/ko/index.html` (raw URL + slop 제거)
- `.github/workflows/site-truth-check.yml` (canon-links 정규식)
- `openspec/specs/landing-page/spec.md` (archive 시 sync)
- init-cli는 불변 — init은 이미 재시작 note를 출력한다(cli.py). INSTALL.md는 그것을 사전
  술어로 못 박을 뿐이다.
