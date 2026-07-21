## 1. INSTALL.md

- [x] 1.1 repo root에 INSTALL.md 신설 — English, goal-state 형식: installed state 술어
  (init 수렴·default branch·첫 transaction의 편입 완결·동결 이력 불가침·harness 원형·
  사용자 귀속 결정·수렴 확인) + oracle 지정. 절차·명령 시퀀스 없음, 내부 정본 비참조

## 2. 관문 재배치

- [x] 2.1 README.md — Getting started에 English 위임 prompt(code block, blob/main URL)를
  1차로, init 직접 경로·공개 목록 유지
- [x] 2.2 README.ko.md — 같은 재배치, 한국어 prompt
- [x] 2.3 site/index.html — getting-started lede 갱신 + prompt code-copy 블록을 init 블록
  앞에 추가 (copy.js는 무변경 — .code-copy 일반 처리)
- [x] 2.4 site/ko/index.html — 같은 재배치, 한국어 prompt

## 3. Canon

- [x] 3.1 ARCHITECTURE.md — 진입점 지도에 INSTALL.md row, 언어 정책에 영어 단일본 등재

## 4. Verification

- [x] 4.1 site-truth-check 3종 로컬 재현 green (init-disclosure 4표면 · canon-links —
  INSTALL.md link 대상 존재 · og-coupling 무관) + validate --strict green + INSTALL.md
  form 토큰 검사 clean
