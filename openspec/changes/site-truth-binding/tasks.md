## 1. CI 결속

- [x] 1.1 `.github/workflows/site-truth-check.yml` — settings.py 실값(PREREQUISITES·
      defaultMode·marketplace repo)의 방문자 표면 3종(site·README 한·영) 존재를 결정론
      검사, PR trigger
- [x] 1.2 og 결합 job — PR diff에 og-card.html 포함 시 og.png 동반 강제
- [x] 1.3 red 실증 — 값 하나를 임시로 어긋나게 해 check가 실제로 fail하는지 local 실측
      후 원복 (거짓 green 방지)

## 2. 판정 기록

- [x] 2.1 proposal에 갈림길 판정(기계 결속 채택 / refine 열거 gap은 plugin 결함 보고·
      후속 change 후보 / 산문 주기 재접지의 현 방어선) 기록 — proposal 작성으로 완료

## 실측 기록

- 1.3: checker를 현행 tree에 실행 → GREEN(값쌍 6종 + marketplace, 표면 3종). settings.py
  사본의 model pin을 sonnet[1m]으로 변조 후 실행 → 표면 3종 전부 model 불일치로 RED —
  결속이 실제로 문다.
