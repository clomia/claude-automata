## 1. License

- [x] 1.1 LICENSE를 Apache-2.0 전문으로 교체 + NOTICE 신규 (copyright clomia, 기반 명시)
- [x] 1.2 pyproject: license = "Apache-2.0", license-files에 NOTICE, version 0.1.6

## 2. 표면 개편 (en·ko 쌍 + image 쌍)

- [x] 2.1 unaffiliated 제거: titleblock STATUS·footer 문단·meta 꼬리 (site en/ko),
      README footer 문구, og/banner head 배지
- [x] 2.2 자기개발 copy 승격: footer lead(en/ko)·README footer·og/banner head
      "BUILT BY ITS OWN AGENTS", og lic 행 APACHE-2.0
- [x] 2.3 version-up-alert 생략: README 표 3행, 사이트 §04 3 card, 계수 표현 중립화
- [x] 2.4 SOURCE 행 4개 제거(en/ko) + .canon-link·.lang-tag CSS 제거
- [x] 2.5 og.png·banner.png 재생성 (쌍 결속)

## 3. 카피라이팅

- [x] 3.1 조사(Ogilvy 계열) 근거 기록 + 전 표면 핵심 copy 감사
- [x] 3.2 수선 3건: §05 lede 평이화, refine 3–12h 구체화, thesis 압축 (en/ko)

## 4. 검증

- [x] 4.1 CI checker(4표면) 로컬 GREEN + og-coupling 쌍 동반 확인
- [x] 4.2 render 실측: fold(1440)·mobile(390) en/ko — 제거 후 layout 성립
- [x] 4.3 기계 grep: 방문자 표면에 version-up-alert·unaffiliated·MIT 잔재 0

## 실측 기록

- 3.1 카피 감사(원칙: headline 지배·구체>수사·문장당 benefit — Ogilvy 계열 조사 근거):
  유지 판정 — H1 claim(구체·병렬), tagline(pain 대조), "DONE" GETS AUDITED, exchange
  panel("the mechanics are real"), FIG caption(WORK IS LOSSY, MEMORY IS VERIFIED),
  "recall is grep", "Forgetting is a feature". 수선 3건 — §05 lede 평이화("sets a
  repository up to run"), refine 3–12h 구체화, thesis 압축(consolidation 중복 제거).
  승격 1건 — footer 자기개선 lead(git 이력으로 검증 가능한 사실 기반 marketing).
- 4.1 checker GREEN: init-disclosure 5쌍+marketplace × 4표면, canon-links 6 target
  (SOURCE 행 제거로 14→6). og·banner 쌍 동반 재생성.
- 4.2 render: §04 3-col 균형(1440), footer lead, ko mobile titleblock(STATUS 제거 후),
  banner "BUILT BY ITS OWN AGENTS" — 전부 실측.
- 4.3 기계 grep: 4표면에서 version-up-alert·NOT AFFILIATED·unaffiliated·무관·\bMIT\b
  잔재 0 (badge alt는 License로 중립화).
- replace no-op 2건(en refine 시간·§05 lede — 원문 불일치)을 render 실측으로 검출해
  정정 — 화면 검증이 문자열 치환의 gate였다.
- verify 1차가 en §05 표의 "enables all four plugins" 잔존을 검출(치환 원문 오추정
  no-op 3번째 — 4.3 grep이 계수 어휘 미포함이 원인). 정정 후 계수 어휘(all four·
  the four·4종·네 개)까지 포함한 재grep으로 6표면 0건 확인.
