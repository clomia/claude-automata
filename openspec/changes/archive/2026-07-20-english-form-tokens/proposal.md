## Why

claude-automata는 영어권 사용자를 1순위로 지원한다 — 사용자 대면 표면과 생성 아티팩트는
English가 기본값이어야 한다. 전수 감사 결과 플러그인 src·hooks·metadata·CLI 출력·workflow
UI는 이미 English-only지만, **기억 canon이 사용자 repo 아티팩트에 강제하는 form 토큰**이
한국어로 남아 있다: seed되는 CI(`memory-check.yml`)의 header 검사 정규식·에러 메시지
(`작성일|Date`, 한국어 우선), canon이 의무화하는 research header 토큰(작성일·질문·방법)과
신뢰도 등급 라벨(✅ 검증됨 …), 정본의 glossary section 이름(`## 용어`). openspec이 다국어
내용을 English form 토큰으로 담듯, form은 English-only여야 한다 — 내용 언어는 자유다.

## What Changes

- **canon form 토큰 English화** — MEMORY.md와 docs-surface.md 사본 2개(tx references ·
  refine skills/docs, byte-identical 테스트로 결속)가 의무화하는 토큰을 교체:
  - research header: `작성일:`·`질문:`·`방법:` → `Date:`·`Question:`·`Method:`
  - 신뢰도 4등급 라벨: `✅ 검증됨 · 🔶 판단 · ❓ 미검증 · ❌ 반박됨` →
    `✅ verified · 🔶 judgment · ❓ unverified · ❌ refuted`
  - glossary section: `## 용어` → `## Glossary`
- **seed되는 CI를 English-only로** — `plugins/tx/references/memory-check.yml`의 header
  정규식에서 한국어 alternation 제거(`(작성일|Date)` → `Date`), 에러 메시지 English-only.
  **BREAKING**: 한국어 header(`작성일:`)를 쓰는 기존 research 문서는 새 검사에서 실패한다
  — 이 repo의 인스턴스는 본 change에서 함께 이행한다.
- **이 repo의 인스턴스 이행** — `docs/research/*.md` 2건의 header·등급 토큰,
  `plugins/ploop/ARCHITECTURE.md`의 `## 용어` heading, seed 사본
  `.github/workflows/memory-check.yml`(seed는 pin drift에서만 재배포하므로 수동 동기화).
- **version pair bump** — 배포물이 변한 tx·refine·ploop의 plugin.json + pyproject.toml.
- openspec archive는 동결 기억이므로 소급 수정하지 않는다.

## Capabilities

### New Capabilities

없음 — 기억 canon(MEMORY.md)과 seed 아티팩트의 형식 규약 변경으로, spec 체계가 소유하는
capability가 아니다 (delta 없는 change; gate는 task 완료·`--skip-specs` archive·CI).

### Modified Capabilities

없음.

## Impact

- `MEMORY.md` · `plugins/tx/references/docs-surface.md` ≡ `plugins/refine/skills/docs/docs-surface.md`
- `plugins/tx/references/memory-check.yml` · `.github/workflows/memory-check.yml`
- `docs/research/github-pushevent-gap-2026.md` · `docs/research/subagent-context-isolation-2026.md`
- `plugins/ploop/ARCHITECTURE.md`
- version pairs: `plugins/{tx,refine,ploop}/{.claude-plugin/plugin.json,pyproject.toml}`
- 외부 사용자 repo: 기존 seed 사본은 openspec pin drift 전까지 구 검사를 유지(한국어 수용
  경로 잔존은 각 repo의 pin 갱신 시점에 해소); 새로 seed되는 repo는 English-only 검사를 받는다.
