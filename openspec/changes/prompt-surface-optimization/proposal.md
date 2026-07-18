## Why

claude-automata의 정책층은 프롬프트다 — 에이전트에 주입되는 모든 텍스트 표면이 시스템의 실질 행동을 결정한다. 이 표면들은 여러 트랜잭션에 걸쳐 증분 작성되어 llm-prompt 규칙(irreducible, ROI 최대, 생략 우선) 기준의 전역 검토를 받은 적이 없다. 추가는 국소 연산이라 쉽게 쌓였고, 삭제는 수신자의 총 맥락을 알아야 하는 전역 연산이라 일어나지 않았다. 지불 빈도가 높은 표면(advisor 매 라운드, synod 매 spawn, launch 재주입)일수록 낭비가 복리로 쌓인다.

## What Changes

- 도메인 5개(ploop, refine:code, refine:docs, refine:integrity, tx)의 에이전트 접지 표면 전수 조사 — 정적 파일과 코드 조립 문자열 모두.
- 수신자 관점 시뮬레이션 기반 최적화: 동거 맥락에서 재구성 가능한 정보 삭제, deterministic 부분의 코드 이관, AI slop 형식 제거.
- 계약 행(훅·코드·정본과 짝지어진 문장)은 짝 개정 없이 문면 보존.
- 공유 표면(synod.md, docs-surface.md 2벌 byte-identical)은 단일 작성자로 정합 유지.
- 표면 문구를 단정하는 테스트의 동반 갱신, 정본 인용 정합, 플러그인 3종 버전 상향.
- 프로덕션 도입 게이트로 무결성 패스 동반: 공식 문서(클로드 코드 tools·hooks·plugins,
  openspec CLI) 대비 프롬프트·동작의 경계 밖 도달 가능 상태를 수색해 4분기 판정으로 흡수한다.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- plugins/{ploop,tx,refine,version-up-alert}의 skills, agents, prompts, references, hooks와 표면을 조립하는 src 코드·bin 래퍼·테스트.
- `.claude/rules/language.md`(어조·번역투 규약 영속화)와 README 한·영(표면 문구 인용 동기화).
- 요구사항(behavior) 변화 없음 — spec delta 없는 change로, archive는 --skip-specs.
