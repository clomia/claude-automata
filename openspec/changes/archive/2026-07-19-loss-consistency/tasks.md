## 1. Mobile drain

- [x] 1.1 `.drain` mobile 배치 — display:none 제거, working-memory box 측면 접지(absolute,
      주 흐름과 횡 분리), pulse choreography 유지
- [x] 1.2 mobile 390 render 실측 + drain 포함 graphic-only mobile 이미지의 vision probe
      재판정 — "loss가 shown인가"
- [x] 1.3 mobile refine riser — c2 병행 상행 dashed line(+pulse)으로 재접지 순환을 그림으로
      복원, vision probe가 shown 기준 충족을 확인

## 2. Share card 정합

- [x] 2.1 og card에 discard 접지 추가 — lossy 속성이 첫인상 surface에 실림
- [x] 2.2 card source를 `site/assets/og-card.html`로 commit (머리 주석에 재생성 command),
      og.png를 그 source에서 재생성 — 치수 1200×630 유지

## 3. 검증

- [x] 3.1 desktop·mobile fold 재실측 — drain 변경이 기존 성립을 깨지 않는지
- [x] 3.2 세 rendering 의미 정합 확인 — canon 산문(MEMORY) ↔ site schematic ↔ og card:
      구성요소(loop·gate·LTM·refine·discard) 대응표로 대조

## 실측 기록

- 1.2·1.3: vision probe 판정 — mobile drain "Shown"(off-axis·terminal·copper·label 4중 단서),
  refine riser 추가 후 "YES — both halves now meet the standard". 잔여 glance 위험(riser
  무표기)은 판정이 제안한 대로 riser 지점에 ↺ 표기를 추가해 해소.
- 2.2: og.png를 committed source(og-card.html)에서 재생성, 1200×630 유지. 재생성 command는
  source 머리 주석.
- 3.1: desktop 1440×900 fold 불변(DOM 이동 후 동일 render), mobile 390×844 fold에 rail+WM+
  drain이 섬.
- 3.2: 대응표 — loop·gate·LTM·refine·discard 5요소가 canon(MEMORY.md 기억 model)·site
  schematic·og card 세 rendering에서 일치. og card의 events rail 생략은 압축 요약으로 수용.
