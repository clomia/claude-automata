## Why

플러그인 단독 설치 환경에서 실용 문제가 실측된 격리 위반이 두 곳 있다. (1) tx·refine이 배포하는 docs-surface.md 사본이 MEMORY.md를 정본 권위로 노출하고, 라우팅 표가 openspec spec으로 주장을 보낸다 — refine 단독 repo에는 openspec scaffold가 없어 죽은 라우팅이 되고, 타 repo 에이전트가 이 생태계 세계관 문서에 결박된다. (2) ploop launch의 "승격은 repo의 응고 gate로"는 MEMORY.md 정의 어휘라 ploop 단독 독자에게 미해결 지시어다 — ploop 정본 스스로 "standalone ploop의 advisor 입력은 기억 도메인을 모른 채로 남는다"를 설계 전제로 두고 있어, 런타임 표면이 그 전제를 어기고 있다.

## What Changes

- docs-surface.md 사본(tx·refine, byte-identical 유지): 머리 행을 MEMORY.md 권위에서 **출처 provenance**(원본 repo URL, 사본 표류 시 출처 우선)로 교체, openspec 라우팅 행을 **scaffold 존재 조건부**(없으면 소유 정본)로, CI 강제 언급 삭제(규칙은 자립).
- MEMORY.md 운반 4중 방어의 "방향" 조항 재정의 — 배포본 머리는 출처 1행이며 MEMORY.md를 권위로 노출하지 않는다. 정본 대조는 이 레포의 동거·주기 대조 소관.
- ploop launch: "승격은 repo의 응고 gate로" → "승격은 repo에 남기는 쓰기고" — 역할만 지시, 세계관 어휘 제거. 루트 ARCHITECTURE.md 접면 계약의 해당 조항을 lockstep 갱신.
- 버전: tx 0.12.5, refine 0.9.3, ploop 0.46.2.

선별에서 제외(실용 문제 없음): version-up-alert의 marketplace 결합(그 플러그인의 정의이자 공식 dependencies 메커니즘), refine principles.md의 "(openspec 등)" 일반 예시, ploop-로컬 정본의 응고 언급(standalone 전제를 기술하는 문서 층).

## Capabilities

### New Capabilities

<!-- 없음 -->

### Modified Capabilities

<!-- 없음 — 프롬프트·규약 표면 변경, spec-level behavior 불변 -->

## Impact

- `plugins/tx/references/docs-surface.md` · `plugins/refine/skills/docs/docs-surface.md` (byte-identical), `plugins/ploop/skills/launch/SKILL.md`, `MEMORY.md`, `ARCHITECTURE.md`, 플러그인 버전 파일 6개
- 이 repo의 기존 동작 보존: openspec이 있는 repo(이 repo 포함, tx가 seed)에서는 라우팅이 기존과 동일하게 spec 표면으로 간다
