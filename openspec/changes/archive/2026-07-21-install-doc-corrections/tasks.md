## 1. INSTALL.md 교정

- [x] 1.1 재시작 술어에 재개 핸드오프: agent가 자기 세션 재시작·context 계승 불가라, 재시작
  후 같은 요청을 다시 보내라고 사용자에게 안내 → 돌아온 세션이 문서를 다시 읽어 마저 수렴
- [x] 1.2 predicate 1: uv 전제 명시 + 재시작 note는 아래 술어 소관임을 밝혀 "미해결 없음"과 화해
- [x] 1.3 openspec-validate 공개 술어: seed의 memory-check workflow가 그 context를 운반함을 명시
- [x] 1.4 em-dash 잔존 0 유지, init-disclosure 값·키 인접(CI 결박) 유지

## 2. 관문 서두 제거

- [x] 2.1 README.md·README.ko.md — getting-started에서 "Installation is agent work / 설치도
  agent의 일입니다" 서두 제거, 실행 지시 + prompt + INSTALL.md link 유지
- [x] 2.2 site/index.html·site/ko/index.html — sec-lede의 같은 서두 제거

## 3. Verification

- [x] 3.1 site-truth-check 3종 로컬 green(init-disclosure INSTALL.md 결박 · canon-links ·
  og-coupling) + validate --strict green + 방문자 표면 em-dash 0 + INSTALL.md em-dash 0
