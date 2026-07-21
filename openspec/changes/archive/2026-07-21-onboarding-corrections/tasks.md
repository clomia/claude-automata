## 1. 재시작 관문 — INSTALL.md

- [x] 1.1 INSTALL.md — init-수렴 술어에서 재시작을 분리해 독립 installed-state 술어로:
  init 이후 재시작되어 plugin·settings live, agent는 자기 세션 재시작 불가라 사용자에게
  표면화. transaction 술어에 "재시작된 세션에서" 후행 명시

## 2. raw prompt URL + 결박

- [x] 2.1 README.md·README.ko.md·site/index.html·site/ko/index.html — prompt URL을
  `raw.githubusercontent.com/clomia/claude-automata/refs/heads/main/INSTALL.md`로 (산문
  클릭 링크는 blob 유지)
- [x] 2.2 .github/workflows/site-truth-check.yml — canon-links 정규식에 raw `(?:refs/heads/)?main`

## 3. em-dash slop 제거 (방문자 표면)

- [x] 3.1 INSTALL.md — 이번 세션 산문의 `— … —` 삽입구를 쉼표·문장 분리로 (disclosure
  값·키 인접은 CI 결박 유지)
- [x] 3.2 README.md·README.ko.md·site/index.html·site/ko/index.html — getting-started
  산문의 em-dash 삽입구 자연화

## 4. Verification

- [x] 4.1 site-truth-check 3종 로컬 green (init-disclosure INSTALL.md 결박 · canon-links
  raw URL 포함 · og-coupling) + raw URL HTTP 200 + validate --strict green + 방문자 표면
  `— ` 삽입구 부재 확인
