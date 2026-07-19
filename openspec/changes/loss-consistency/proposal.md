## Why

advisor round 2가 round 1이 만든 자기 불일치 2건을 표면화했다. (1) "loss는 shown이어야
한다"는 round 1의 핵심 성취가 mobile에서 회귀했다 — `.drain{display:none}`이 접지 기호를
숨겨 loss가 다시 props text로만 전달되는데, anchor는 mobile 시각화를 first-class로
규정한다. (2) share card(og.png)는 memory model의 두 번째 rendering인데 가장 변별적인
속성(lossy/discard)을 빠뜨렸고, 생성 source가 미commit이라 site schematic과의 divergence를
diff할 수도 재생성할 수도 없다 — "복제는 표류를 낳는다"의 실체화.

## What Changes

- **mobile drain 표시**: 세로 main flow와 시각 충돌 없도록 drain을 working-memory box의
  측면 접지로 배치(absolute, 좌하단 — 주 흐름은 중앙 하강, 폐기는 측면 방전). drain 포함
  mobile render를 vision probe로 재판정.
- **mobile refine riser**: 같은 기준("shown, not told")의 잔여 위반 — mobile에서 refine
  궤도가 text 한 줄로 붕괴해 있었다(vision probe가 표면화). gate↔LTM의 고정 간극(c2)에
  상행 dashed riser를 병설해 재접지 순환을 그림으로 복원한다 — 중앙 하강은 승격, 우측
  상행은 재접지, joint는 구조상 양 box에 정확히 닿는다.
- **share card에 lossy 요소 추가**: og card에 discard 접지를 그려 세 rendering(canon 산문·
  site schematic·og card)의 의미 정합을 복원.
- **card source commit**: `site/assets/og-card.html`로 생성 source를 commit — 재생성
  command를 파일 머리 주석에 기록. round 1 design의 "script 미commit" 결정의 명시적
  번복이다: 그 결정은 og를 일회 산출물로 봤으나, og는 model의 지속 rendering이라 diff
  가능성이 표류 방어의 전제다.

## Capabilities

### New Capabilities

<!-- 없음 -->

### Modified Capabilities

<!-- 없음 — 기존 요구사항(반응형 성립·share image 존재)의 구현 정합; spec-level behavior 불변 -->

## Impact

- `site/style.css` (mobile drain 배치), `site/assets/og-card.html` (신규, source),
  `site/assets/og.png` (재생성)
- delta-less — archive는 `--skip-specs`, gate는 task 완료·CI
