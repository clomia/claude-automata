## 1. Canon token flip

- [x] 1.1 MEMORY.md — `## 용어` 언급 3곳을 `## Glossary`로, research header 의무 토큰을
  `Date:`·`Question:`·`Method:`로, 등급 라벨을 `✅ verified · 🔶 judgment · ❓ unverified · ❌ refuted`로
- [x] 1.2 plugins/tx/references/docs-surface.md — 같은 토큰 교체 (자신의 `## 용어` heading 포함)
- [x] 1.3 plugins/refine/skills/docs/docs-surface.md — tx 원본을 그대로 복제 (byte-identical)

## 2. Seeded CI English-only

- [x] 2.1 plugins/tx/references/memory-check.yml — header 정규식 `Date`/`Method`만 수용,
  에러 메시지 English-only
- [x] 2.2 .github/workflows/memory-check.yml — template과 동일하게 수동 동기화

## 3. Instance migration in this repo

- [x] 3.1 docs/research/github-pushevent-gap-2026.md — header 토큰 `Date:`·`Question:`·`Method:`,
  인라인 `🔶 판단:` → `🔶 Judgment:`
- [x] 3.2 docs/research/subagent-context-isolation-2026.md — 같은 이행
- [x] 3.3 plugins/ploop/ARCHITECTURE.md — `## 용어` → `## Glossary`

## 4. Version pairs

- [x] 4.1 tx 0.12.10 → 0.12.11, refine 0.9.8 → 0.9.9, ploop 0.47.3 → 0.47.4
  (각 plugin.json + pyproject.toml)

## 5. Verification

- [x] 5.1 한국어 form 토큰 잔존 0 확인 (`git grep`: 작성일·질문:·방법:·`## 용어`·등급 라벨 —
  openspec archive·내부 산문 제외), refine byte-identical 테스트 및 plugin 테스트 통과
