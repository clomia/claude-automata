## Context

격리 조사(2026-07-19) 실측: MEMORY.md는 플러그인 이름을 38회 참조하는 세계관 허브다. docs-surface.md 사본은 그 MEMORY.md를 "충돌 시 이긴다"는 권위로 머리에 싣고, 라우팅 표가 openspec spec을 무조건 지시한다. ploop launch는 MEMORY 어휘 "응고"를 싣는다. 코드 층은 깨끗하다 — ploop·tx·refine 상호 코드 참조 0, Stop 훅 동거는 harness 필드 매개(접면 계약 기록 존재).

단독 설치 실용 영향: refine-only는 죽은 openspec 라우팅 + 외부 권위(실질 파손), tx-only는 권위 외부화(tx가 openspec을 스스로 seed하므로 라우팅은 자립), ploop-only는 미해결 어휘 1개(경미).

## Goals / Non-Goals

**Goals** — 단독 설치에서 실용 문제가 발생하는 지점만 제거. 이 repo와 tx 동반 repo의 기존 동작 보존. 사본 byte-identity와 운반 4중 방어의 기능 보존.

**Non-Goals** — docs-surface 규약 내용의 전면 재설계(설계 정본·상주·조사 기록 규약은 플러그인-중립 처방으로 어느 repo에서나 actionable), version-up-alert 구조 변경, MEMORY.md의 허브 성격 변경(repo 문서는 전체를 알아도 된다 — 위반은 플러그인 표면이 허브를 역참조하는 방향이었다).

## Decisions

1. **권위 → provenance.** 사본 머리를 "출처: <repo URL> — 배포 사본, 표류 시 출처 우선"으로. 방향 방어의 실기능(야생 사본의 추적·개정 단일화)은 유지되고, 잃는 것은 "타 repo 판단에 대한 MEMORY.md 권위"뿐 — 그것이 제거 대상이다. 정본↔운반체 대조는 나머지 방어(동거·refine:docs 주기 대조·버전 경계)가 이 레포 안에서 수행한다. 사본에 플러그인 이름도 싣지 않는다(사본 자체가 격리 표면).
2. **openspec 라우팅의 조건부화.** "spec 표면 — `openspec/` 스캐폴드가 있을 때, 없으면 소유 정본". openspec이 있는 repo(이 repo, tx-seed repo)는 행동 불변, 없는 repo는 죽은 라우팅 대신 소유 정본으로 수렴 — 어느 환경에서도 actionable. MEMORY.md의 원본 라우팅 표는 무조건 유지(이 레포는 항상 openspec 보유) — 사본과의 차이는 운반 절이 정의한 "번역"의 범위다.
3. **CI 강제 언급 삭제.** "CI가 전 추적 .md에서 형식 검사한다"는 tx-seed CI의 존재 주장이라 refine-only에서 거짓 — 규칙 문장은 강제 수단 없이 자립한다.
4. **ploop launch 어휘 자기완결화.** "승격은 repo에 남기는 쓰기고, 나머지는 폐기" — 접면 계약의 원 취지(역할만 지시, 도구 무명명)를 어휘까지 확장. 관문 존재의 힌트도 싣지 않는다 — 관문의 정체는 tx 가드 표면이 쓰기 순간에 스스로 가르친다(기존 계약 문언 그대로). 루트 ARCHITECTURE 접면 계약 조항을 같은 tx에서 lockstep 갱신.
5. **선별 제외의 근거 기록.** version-up-alert: RAW_ROOT의 marketplace 결합은 "marketplace 전속 updater"라는 플러그인 정의 자체이고 공식 dependencies로 선언되어 단독 설치에서도 정상 동작 — 실용 문제 0. refine principles.md "(openspec 등)": 일반 예시 나열. ploop-로컬 정본의 "응고 계약 없는 사용": standalone 전제를 기술하는 문서 층으로, 이번 변경이 정합시키는 바로 그 전제다.

## Risks / Trade-offs

- [사본 개정으로 정본(MEMORY)과 운반체의 번역 거리 증가] → 운반 절이 번역임을 이미 규정, 대조는 동거·주기 대조가 수행.
- [출처 우선 문구의 오독(내용 전체가 아니라 사본 표류에 한정)] → 문구를 "사본이 표류하면"으로 한정 명시.

## Migration Plan

문서·프롬프트 표면만 변경, 코드 불변. rollback = revert.

## Open Questions

없음.
