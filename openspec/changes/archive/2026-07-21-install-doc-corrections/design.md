## Context

INSTALL.md(agent-delegated 설치의 goal-state 지침)를 fresh-context agent에게 raw URL로
읽혀 brownfield 설치를 시뮬레이션했다. WebFetch는 clean했고(raw URL 실측 통과), 대부분의
술어는 따라갈 수 있었으나 재시작 경계에서 연속성이 끊겼다. 공식 plugins reference로 근거를
확정했다: 마켓플레이스 plugin은 캐시로 복사되어 "installed for future sessions"이고, init이
쓰는 project-scope settings는 다음 세션에 로드된다 — 재시작 주장은 정확하다.

## Goals / Non-Goals

**Goals:**

- 재시작 너머로 설치가 스스로 이어지도록 재개 핸드오프를 각본화한다.
- INSTALL.md를 유일 지침원으로 표방하는 만큼 uv 전제·context 연결을 자립시킨다.
- 관문 서두를 걷어 실행 지시만 남긴다.

**Non-Goals:**

- 시뮬레이션이 꼽은 도입 고유 비용(호스트 spec의 1.6.0 strict 수리, 2차 tx 수렴)을 INSTALL.md에
   미리 적재 — 부담은 repo마다 다르고 이미 술어로 라우팅돼 있다.
- living-doc 술어를 CI 범위에 맞춰 축소 — 술어는 docs-surface 규약을 서술하고 CI는 부분
   backstop이다. agent 판단이 그 차를 메운다.
- INSTALL.md 전면 재작성 — 시뮬레이션 권고대로 surgical 수정만.

## Decisions

- **D1: 재개 핸드오프를 술어에 각본화 + spec으로 잠금.** blocker라 ROI가 최고다. 세션 1이
   "재시작하라"만 넘기면 세션 2(fresh)가 무엇을 할지 모른다. goal-state 문서는 resumable하므로,
   "재시작 후 같은 요청을 다시 보내라"는 재개 지시만 사용자에게 넘기면 돌아온 세션이 문서를
   다시 읽어 남은 술어를 수렴한다. 이 한 줄이 luck-dependent 핸드오프를 닫힌 loop로 바꾼다.
   host-harness 존중의 "사용자 결정 귀속" scenario와 같은 계열(사람이 해야 하는 행위)이라
   `재시작 관문` scenario에 못 박는다.
- **D2: uv 전제를 predicate 1에 인라인.** 방문자 표면(README)만 uv를 적어, INSTALL.md만 읽는
   agent는 못 본다. init이 전제조건 oracle인데 uv 없이는 못 도는 순환을 짧게 해소한다.
- **D3: memory-check ↔ openspec-validate context 연결 명시.** seed의 workflow 이름을 술어에
   넣어 호스트 CI dedup 대상을 추론 없이 지목하게 한다.
- **D4: predicate 1의 "미해결 없음"을 재시작 note와 화해.** predicate 1은 재시작 note를
   "아래 술어 소관"으로 넘기고, 세션 내 해소를 요구하지 않는다.
- **D5: 관문 서두 제거는 docs 표면.** spec은 서두를 요구하지 않으므로 문구만 걷는다. 실행
   지시(prompt)와 INSTALL.md link는 유지 — 관문 scenario 불변.

## Risks / Trade-offs

- [재개가 새 세션이라 자동화 루프가 끊김] → 이것이 goal-state의 본질이자 강점이다. 사용자
   재전송이 유일한 인간 개입점이고, 문서가 그 지시를 명시하면 닫힌다.
- [uv 문구 추가로 goal-state 순수성 소폭 희석] → 전제 사실 한 줄일 뿐, 절차가 아니다.

## Migration Plan

단일 tx. site는 main 병합 시 pages workflow가 자동 발행한다.

## Open Questions

없음.
