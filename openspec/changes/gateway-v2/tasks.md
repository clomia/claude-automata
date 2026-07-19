## 1. Site v2

- [x] 1.1 hero 재구성 — eyebrow=정체, H1=주장(5rem lockup), 회로는 그래픽 우선 유지
- [x] 1.2 advisor exchange panel 신설 — terminal 풍, illustrative label, 기제 사실만
- [x] 1.3 절 산문 자체 완결 보강 + KO 정본 link를 SOURCE 행으로 강등
- [x] 1.4 title·meta·og description을 새 주장과 정합

## 2. README v2 (한·영 쌍)

- [x] 2.1 banner-card.html + banner.png 생성 (committed source, 1280×400)
- [x] 2.2 README.md 재작성 — banner·tagline·인벤토리·install(공개 유지)·초대 hook·
      `<details>` 접기·내부 정본 참조 0
- [x] 2.3 README.ko.md 동기 재작성
- [x] 2.4 root pyproject 0.1.5

## 3. CI

- [x] 3.1 og-coupling job을 (og-card,og)·(banner-card,banner) 쌍 순회로 일반화 + red 실증

## 4. 검증

- [x] 4.1 fold·mobile 실측 (1440·390) — 새 hero·panel 성립
- [x] 4.2 자체 완결 probe — 외부 link 접근 금지 조건으로 사이트 단독 재구성(무엇/기제/가치/시작)
- [x] 4.3 README 신규 쌍의 fresh probe + 내부 정본 참조 0 확인 (기계 grep)

## 실측 기록

- 4.1: fold 1440×900 — 주장 3줄 lockup + 회로 전체(접지·refine 궤도 포함)가 first viewport에
  섬. mobile 390 — 주장·rail·working memory가 fold를 이끎.
- 4.2: link-dead 조건의 self-containment probe — 1차 NO(운영 명령 on-page 부재: 조종·중단·
  docent·refine 호출·tx 중간 단계) → §04/§05 보강 후 재판정 **YES** ("the page now carries
  the complete surface from concept to operation"). 판정자가 가장 기억에 남는 요소로
  §01 exchange panel을 지목. 부기: §02 통제 문장 추가는 replace no-op으로 미적용 —
  §05 operate block이 통제를 운반하므로 중복 없이 수용.
- 4.3: README probe YES — hook 유효("would click"), 1분 내 what/why 판단 가능. 지적 반영:
  badge 2종(PyPI·license)·exchange 인라인·anchor 용어 정의·version-up-alert H2를 table로
  흡수. 내부 정본(ARCHITECTURE·MEMORY) 참조 0을 기계 grep으로 확인.
- 3.1: 쌍 결합 shell 논리 4-case 실증(card-only red·pair green·og-only red·무관 green),
  init-disclosure·canon-links 재실행 GREEN(link 대상 10, raw banner 포함).

## 5. 소유자 추가 지시 (mid-transaction)

- [x] 5.1 디자인 심층 재고찰 — 7개 폭(344·390·600·704·768·1280·1440) 실측 전 안정,
      PREMISE→OPERATING PRINCIPLES, eyebrow 이름 중복 제거, exchange panel mobile 여백
- [x] 5.2 `site/ko/index.html` — /ko/ 즉시 접속, titleblock EN·KO toggle(default en),
      hreflang 상호 선언, 한글 keep-all·tracking 조정(자체 한글 font 기각 — per-glyph fallback)
- [x] 5.3 CI 표면 4종 확장(init-disclosure·canon-links에 ko page 편입) — GREEN 실측(14 link)
- [x] 5.4 억지 번역 감사 — native 한국어 개발자 probe가 명백 결함 16건 + 경계선 5건 판정,
      16건 전부와 경계선 3건(돌아갑니다·발동·기록하는) 반영, 수사 2건은 판정대로 유지
