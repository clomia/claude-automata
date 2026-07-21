## Context

직전 change(agent-install)가 관문에 위임 prompt를 1차로 얹되 `uvx claude-automata init`
직접 경로와 settings 공개 표를 유지했다. 사용자 결정: 설치를 agent 전용으로 확정하고 관문을
prompt만으로 단순화한다. 남은 긴장은 `init-disclosure` CI가 결박하는 보안 투명성
공개(`bypassPermissions` 등)의 처분이다.

## Goals / Non-Goals

**Goals:**

- 관문(README·site) 설치 절 = 위임 prompt 하나. init 명령·공개 표 제거.
- settings 투명성 공개를 잃지 않는다 — home을 INSTALL.md로 이전, CI 결박 유지.

**Non-Goals:**

- init CLI·plugin 구현 변경 — 배포물 불변, version bump 없음.
- INSTALL.md의 goal-state 형식 훼손 — 공개는 절차가 아니라 installed state의 일부다.
- 공개의 완전 삭제 — 권한 프롬프트를 끄는 설정을 사람이 읽을 수 있는 어디에도 사전
  공개하지 않는 것은 dark-pattern이다.

## Decisions

- **D1: 공개는 삭제가 아니라 이전.** 관문에서 제거하되 INSTALL.md로 옮긴다. 근거: 위임
  prompt가 명시적으로 INSTALL.md를 읽으라 지시하므로, 신중한 사용자의 감사 경로가 곧
  INSTALL.md다. 이는 직전 change의 D3("gateway가 이미 공개하므로 INSTALL.md는 재서술
  금지")의 전제를 이 change가 제거함에 따른 자연스러운 반전이다 — 공개 의무가 gateway에서
  INSTALL.md로 이동한다.
- **D2: 공개는 installed state의 술어다.** "설치되면 settings.json이 이 값들을 담는다"는
  method가 아니라 state다. goal-state 형식과 정합하며 문서에 술어 하나로 얹는다.
- **D3: init-disclosure CI 표면 재결박.** 스캔 대상을 4개 방문자 표면에서 `INSTALL.md`
  단일로 바꾼다. 결박 로직·settings.py source는 불변 — anti-staleness 보증이 새 home으로
  그대로 이동한다. 이 값이 있어야 CI가 green이므로 INSTALL.md는 전 pair를 담아야 한다.
- **D4: init 명령은 INSTALL.md에 잔존.** agent가 읽는 oracle이므로 INSTALL.md의 `uvx
  claude-automata init` 언급은 유지된다 — 관문에서만 사라진다. 명령의 home은 그것을
  실행하는 주체(agent)가 읽는 문서다.
- **D5: 재배치는 spec delta로.** 관문은 spec이 계약으로 고정하는 표면이라 문서만 고치면
  다음 refine이 drift로 판정한다. README 관문화·Site 서사 계약·Agent install canon 3개를
  MODIFIED로 갱신한다.

## Risks / Trade-offs

- [사전 공개가 한 click 뒤로 물러남] → prompt가 URL을 명시하고 INSTALL.md가 감사 대상이다.
  제품 서사(24/7 자율)가 bypassPermissions를 이미 함의하므로 관문 표면의 표는 잉여였다.
- [INSTALL.md에 settings 표가 생겨 goal-state 순수성 약화] → 공개는 state의 일부라 형식과
  충돌하지 않는다. 값은 CI로 결박되어 canon으로 유지된다.

## Migration Plan

단일 tx. site는 main 병합 시 pages workflow가 자동 발행한다.

## Open Questions

없음.
