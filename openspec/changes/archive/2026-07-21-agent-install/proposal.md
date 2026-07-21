## Why

claude-automata의 대상은 Claude Code로 유지관리되는 repository다 — 설계 전제상 기여 주체가
전부 agent인 환경에서, 설치만 사람이 명령을 실행하는 현행 관문은 비대칭이다. 특히 대부분의
도입은 자체 harness·문서 체계를 가진 기 구축 repo이고, 그 환경에서의 편입 판단(기존 CI와의
중복, form 위반의 수선, 기존 spec 체계의 처분)은 그 repo를 아는 agent가 가장 잘 내린다.
설치를 agent에 위임하는 관문이 필요하다: 사람은 prompt 한 줄을 건네고, agent가 `uvx
claude-automata init` 실행부터 첫 transaction까지 수렴시킨다.

지침의 형식이 핵심이다: **방법이 아니라 성공 상태를 서술한다.** 도달해야 할 installed
state를 검증 가능한 술어로 고정하고 경로는 각 환경의 agent에게 맡긴다 — 상세 절차 지침은
환경 다양성 앞에서 틀리거나 사고를 제한한다. 이 형식은 tx skill의 goal-state 관례
(2026-07-18-goal-state-prompts)의 연장이다.

## What Changes

- **INSTALL.md 신설** (repo root, English 단일본) — 설치 수행 agent 대상의 goal-state
  지침: installed state 술어 집합 + 상태 oracle 지정(init 출력·seed 보고·validate·CI) +
  host harness 존중 경계(동결 이력 불가침·소급 재구성 금지·repo 소유 결정의 사용자 귀속).
  방법 절차·명령 시퀀스를 싣지 않는다.
- **README 쌍의 설치 절** — agent 위임을 1차 경로로: INSTALL.md를 읽고 설치하라는 복사형
  한 줄 prompt를 앞세우고, `uvx claude-automata init` 직접 경로와 init 실동작 공개는
  유지한다(init-disclosure CI 결박 유지).
- **site en·ko의 getting-started** — 같은 재배치: 위임 prompt code-copy 블록을 1차로,
  init command 블록과 공개 표는 그대로.
- **landing-page spec delta** — README 관문화·Site 서사 계약의 설치 절 계약 갱신 +
  INSTALL.md의 지속 계약 ADDED.
- **ARCHITECTURE 갱신** — 진입점 지도에 INSTALL.md, 언어 정책에 영어 단일본 사유 등재.
- version bump 없음 — plugin·root package 구현 불변, 관문 문서·site만 변한다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `landing-page`: README 관문화 requirement의 설치 절 — agent 위임 prompt 1차 + init 공개
  유지. Site 서사 계약 requirement의 getting-started — 같은 계약. INSTALL.md 지속 계약을
  ADDED requirement로 신설(같은 capability — 방문자 관문의 "어떻게 시작" 연장).

## Impact

- `INSTALL.md` (신설) · `README.md` · `README.ko.md`
- `site/index.html` · `site/ko/index.html` (getting-started 절)
- `openspec/specs/landing-page/spec.md` (archive 시 sync)
- `ARCHITECTURE.md` (진입점 지도 · 언어 정책 1문장)
- CI 결박은 기존 그대로 동작: canon-links가 새 blob link의 대상 존재를, init-disclosure가
  공개 표의 실값 결속을 검증한다.
