## Context

3면 실측이 선행했다: 공식 훅 코퍼스(background_tasks 타입 집합에 monitor 별도 차선, Monitor
도구 정의 = "변화에 반응하는 감시" — 완료 개념 없음), ploop 게이트 코드·정본 결정 16(monitor
통과가 유일한 무모순 선택), 현행 launch 문면(금지 방향 부재).

## Goals / Non-Goals

**Goals:** Monitor 오용(대기 목적)의 authoring-time 차단. **Non-Goals:** 게이트 동작 변경
(통과가 정당 — 설계 유지), 결정 16 문면 개정(현행 서술이 이미 정확), Monitor의 루프 밖
용례 제약.

## Decisions

- **금지 방향을 skill이 나른다.** 게이트는 monitor를 막을 수 없으므로(교착) 이 오용은
  기계로 차단 불가 — 남는 지렛대는 authoring-time 규칙뿐이다. 근거 1구를 인라인한다:
  "advisor 소집을 막지 않으므로"가 없으면 규칙이 자의적으로 읽혀 위반된다.
- **"라운드 안에서 정리하라" 삭제.** ambient가 shell 차선에 앉는 실제 위반 순간, 게이트의
  집합당 1회 교정 지시가 정리·Monitor 이전을 지시한다 — 동거 기계가 가르치는 내용의 사전
  사본은 캡슐화 트랜잭션과 같은 판정으로 삭제한다.
- 대기 차선(shell·Agent·Workflow)은 두 행 위에 동거하므로 재언하지 않는다.

## Risks / Trade-offs

- [금지가 루프 밖 Monitor 활용까지 위축] → 행의 주어가 launch rules(루프 컨텍스트)로
  한정되고, "라이브로 돌리는 데만"이 정당 용례를 적극 명명한다.
