## Context

agent-delegated 설치(2026-07-21-agent-install)와 prompt-only 관문(gateway-prompt-only)을
배포한 뒤, 설치 흐름의 부트스트랩 제약 하나와 표면 교정 둘이 남았다. proposal의 Why가 실측을
담는다. init의 재시작 note는 이미 존재한다(cli.py) — 문제는 INSTALL.md가 그것을 사전 술어로
못 박지 않아, INSTALL.md만 읽는 agent가 init 직후 `/tx:open`을 찾다 막힌다는 점이다.

## Goals / Non-Goals

**Goals:**

- 재시작이 init과 첫 transaction 사이의 필수 관문임을, agent가 자기 세션을 못 고친다는
  사실과 함께 INSTALL.md에 못 박고 spec으로 잠근다.
- 위임 prompt를 agent가 fetch하기 좋은 raw로, 존재 결박을 유지한 채 바꾼다.
- 이번에 쓴 방문자 산문의 AI 티(em-dash 삽입구)를 제거한다.

**Non-Goals:**

- 내부 canon(MEMORY.md·openspec 산문)의 em-dash 하우스 스타일 변경 — owner voice다.
- init CLI 변경 — 재시작 note는 이미 출력된다.
- 산문 속 클릭용 링크의 raw화 — 사람이 브라우저에서 읽는 링크는 blob가 낫다.

## Decisions

- **D1: 재시작은 독립 술어 + 후행 명시.** init-수렴 술어에서 재시작을 분리한다. 근거:
  묻힌 부속절은 goal-state의 검증 대상으로 약하다. transaction 술어가 재시작에 후행함을
  명시해 "init 직후 /tx:open" 막다른 길을 차단한다. agent가 자기 세션 재시작 불가라는 사실을
  술어에 담아 "사용자에게 표면화"라는 행위 계약을 만든다(host-harness 존중의 "사용자 결정
  귀속" scenario와 같은 계열 — 사람이 해야 하는 행위).
- **D2: spec scenario로 잠금.** 재시작 누락은 install-blocking이라 ROI가 높다. Agent install
  canon에 술어 문구 + `재시작 관문` scenario를 더한다. scenario 추가는 superset이라 archive
  drop-guard에 걸리지 않는다.
- **D3: prompt만 raw, 산문 링크는 blob.** prompt의 소비자는 WebFetch, 산문 링크의 소비자는
  사람이다. 소비자별로 URL 형식을 나눈다. raw는 `refs/heads/main` 형식(GitHub Raw 버튼의
  현행 canonical)을 쓴다.
- **D4: canon-links가 raw 두 형식을 결박.** 정규식에 `(?:refs/heads/)?main`을 넣어 `main`·
  `refs/heads/main` raw 형식을 모두 매칭한다. `refs/heads/main`만 넣으면 짧은 형식이 빠지고,
  짧은 형식만 두면 이번 prompt가 빠진다 — 둘 다 결박이 robust하다. spec은 이미 "raw 경로"를
  상정하므로 delta 불요.
- **D5: em-dash slop 제거는 방문자 표면 한정.** INSTALL.md·README 쌍·site 쌍의 이번 세션
  산문에서 `— … —` 삽입구를 쉼표·문장 분리로 자연화한다. 내부 canon은 불변.

## Risks / Trade-offs

- [재시작 후 설치 재개는 새 세션] → INSTALL.md는 goal-state라 절차가 아닌 도달 상태만
  서술한다. "재시작된 세션에서 transaction이 돌아 adoption이 병합됨"이 그 상태다.
- [raw 두 형식 결박으로 정규식 복잡도 소폭 증가] → 한 optional 그룹뿐. 결박 누락 위험보다
  싸다.

## Migration Plan

단일 tx. site는 main 병합 시 pages workflow가 자동 발행한다.

## Open Questions

없음.
