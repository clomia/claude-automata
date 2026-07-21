## 1. 공개 이전 — INSTALL.md

- [x] 1.1 INSTALL.md — installed state에 settings 공개 술어 추가: init이 쓰는 값
  (`permissions.defaultMode="bypassPermissions"`·`model="opus[1m]"`·alwaysThinkingEnabled·
  autoCompactEnabled·autoMemoryEnabled·marketplace) 명시. init-disclosure CI regex 충족
  (각 key와 값이 60자 이내 인접, marketplace repo 문자열 포함)

## 2. init-disclosure CI 재결박

- [x] 2.1 .github/workflows/site-truth-check.yml — init-disclosure job의 `surfaces`를
  `["INSTALL.md"]`로, 주석을 새 결박 대상으로 갱신

## 3. 관문에서 init 맥락 제거

- [x] 3.1 README.md — Getting started에서 `uvx claude-automata init` 블록·공개 목록 제거,
  위임 prompt + INSTALL.md link + 최소 전제만
- [x] 3.2 README.ko.md — 같은 제거
- [x] 3.3 site/index.html — getting-started에서 init code block·init-disclosure div 제거,
  prompt 블록만 (두 번째 prereq 라인 포함 정리)
- [x] 3.4 site/ko/index.html — 같은 제거

## 4. Verification

- [x] 4.1 site-truth-check 3종 로컬 재현 green (init-disclosure — INSTALL.md 결박 ·
  canon-links · og-coupling) + validate --strict green + 관문 4표면에 `uvx` 문자열 부재 확인
