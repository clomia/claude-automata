## Why

소유자 지시(고도화): 오픈소스 생태계의 첫 방문자에게 "무엇인지·어떤 가치인지"가 한눈에
읽혀야 하는데 README 품질이 부족하고, 사이트도 후킹과 직관 설명의 밀도가 모자라며 이해가
한국어 내부 문서(ARCHITECTURE·MEMORY) 참조에 기대고 있다. 참고 기준: caveman README
(banner→tagline→show-don't-tell→단일 install→`<details>` 점진 공개)와 caveman.so
(거대 활자의 단일 주장 + 즉시 증명하는 그래픽 하나).

## What Changes

- **사이트 자체 완결화 + hero 재구성**: 정체 서술을 eyebrow로 내리고 H1을 본능적 주장으로
  ("Runs for days. Remembers only what's verified."). 신설 §—advisor를 인간 메타인지로
  설명하는 terminal 풍 exchange panel(agent가 "done" 선언 → hook이 정지 차단 → advisor가
  놓친 것 제시 → 조언이 마를 때까지) — show-don't-tell의 핵심. 각 절의 산문을 스크롤만으로
  전체 이해가 완결되도록 보강하고, KO 정본 link는 이해 필수 경로에서 SOURCE pointer로 강등.
- **README 재작성 (caveman 문법, 한·영 쌍)**: banner 이미지 + 한 방 tagline + 사이트 hook을
  "Landing page"가 아닌 초대 문구("Watch the memory circuit run")로 + plugin 표 + 단일
  install(공개 유지 — CI 결속) + usage는 `<details>`로 접기. **ARCHITECTURE.md·MEMORY.md
  참조 전면 제거**(내부 개발 문서, 한국어 기반 — 방문자 표면의 이해 경로에서 배제).
- **README banner 이미지**: og-card 선례대로 committed source(`site/assets/banner-card.html`)
  에서 생성한 `site/assets/banner.png`, og-coupling CI를 banner 쌍까지 확장.
- **root 0.1.5** — README 재발행.

## Capabilities

### New Capabilities

<!-- 없음 -->

### Modified Capabilities

- `landing-page`: (1) 사이트는 정본 참조 없이 자체 완결로 이해를 제공해야 한다 — 정본
  link는 보조 pointer다. (2) README 관문화 요구 개정 — 정체 한 줄 대신 banner+tagline,
  내부 정본(ARCHITECTURE·MEMORY) 참조 금지, 사이트 hook은 초대 문구. (3) share/banner
  image의 source-산출물 결합이 banner 쌍까지 확장.

## Impact

- `site/index.html`·`site/style.css` (hero·신설 절·산문 보강), `site/assets/banner-card.html`·
  `site/assets/banner.png` (신규), `.github/workflows/site-truth-check.yml` (og-coupling 확장),
  `README.md`·`README.ko.md` (재작성), `pyproject.toml` (0.1.5),
  `openspec/specs/landing-page/spec.md` (archive 시 sync)
