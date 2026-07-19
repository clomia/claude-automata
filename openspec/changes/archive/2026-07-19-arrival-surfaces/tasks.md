## 1. Graphic-first hero

- [x] 1.1 `site/index.html` hero 재배치 — schematic figure를 h1 직후로, thesis를 figure 뒤로
- [x] 1.2 spacing 조정(`site/style.css`) 및 desktop 1440·mobile 390 first-viewport 실측 —
      도형이 fold 안에 서는지 판정, 근거 screenshot

## 2. Share metadata

- [x] 2.1 1200×630 share image 자가 생성 → `site/assets/og.png` (token 일치, schematic 축약)
- [x] 2.2 `<head>`에 og:title·og:description·og:url·og:image(절대 URL)·twitter:card 추가

## 3. 도착 표면

- [x] 3.1 pyproject `[project.urls]` Homepage → landing page URL, version 0.1.2
- [x] 3.2 GitHub About 설정 — `gh repo edit`으로 website=landing page, description=정체 한 줄

## 4. 검증

- [x] 4.1 그래픽 단독 판독 probe — 주변 산문 없는 rendered schematic 이미지만으로 vision
      agent가 구조(흐름·gate·영속 대비·user의 동렬성)를 판독하는지 판정
- [x] 4.2 검증자 오염 한계 기록 — @README 미확장·pointer 누출 실측을 검증 기록에 명시,
      probe는 인용-정박으로 운용
- [x] 4.3 OG tag 정합 실측 — meta가 절대 URL로 해석되고 og.png가 정적 serve되는지 확인

## 실측 기록

- 1.2: 재배치 후 desktop 1440×900 first viewport에 회로 전체(rail·3 station·discard 접지·
  refine 궤도·FIG caption), mobile 390×844에 rail+working memory 전체가 선다.
- 4.1: vision probe 판정 YES — 도형만으로 흐름·gate 의미·영속 대비·refine의 gate 재진입까지
  판독. 유일 약점("소실이 글자로만 서술")은 ground(접지) 기호 추가로 해소 — 후속 판정
  "loss is now shown, not merely told" (YES).
- 4.2: 오염 실측 — subagent는 CLAUDE.md·rules를 받되 @README.ko.md는 미확장. 세계관 어휘가
  정본 pointer·skill 목록으로 누출되므로 완전한 zero-context 검증자는 이 repo의 공식
  subagent 경로에서 불가능. probe는 인용-정박(사실마다 artifact 절 인용)으로 운용했다.
- 4.3: og meta 9종이 절대 URL로 존재, og.png(1200×630) 정적 serve 200 확인.
- 3.2: gh repo edit 성공 — homepageUrl=landing page, description=정체 한 줄 (실측 확인).
