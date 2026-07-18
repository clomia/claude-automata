## Context

수신자 시뮬레이션 리뷰 3기 + 통합 1기(전원 max)가 재작성을 공격했다: close 시나리오 7종
(활성 change 없음·conflict가 코드 접촉·CI 후 base 전진·stale 원격·재rebase 후 게이트·재close·
PR 직후 체크 부재), open 시나리오 6종, 계약 7종 보존 감사, 엔진 핀 1.6.0 재실측.

## Goals / Non-Goals

**Goals:** 목표-상태 형식으로 절차 재구성을 지능에 위임, verify 오유도 소멸.
**Non-Goals:** 재절차화(리뷰의 명시적 실패 모드), 계약 의미 개정, plan·apply의 엔진 구동
시퀀스 해체(진짜 순차 도구 소비는 절차가 정당).

## Decisions

- **목표-상태가 절차를 대체한다.** 시나리오 13종 전부에서 삭제된 절차가 사실 재조합으로
  재구성됨을 시뮬레이션으로 입증했다. 유일 구멍은 수량화였다: "활성 change마다"는 archive
  후 세션이 죽고 재개된 close에서 공진리가 되어 stale pass를 통과시킨다 — "트랜잭션의
  change마다"로 재표현(verify.md가 archive/를 이미 읽으므로 검증 가능, base 쪽 archive는
  diff가 구분).
- **엔진이 가르치는 것은 스킬이 재언하지 않는다.** blocked 상태의 instructions apply는
  소비할 태스크 자체가 없고(실측), 아티팩트 순서는 nextSteps가 안내하며, kebab-case는 위반
  시 에러가 가르치고, 체크박스 규칙은 apply payload가 나른다. 단 게이트 실패 시 엔진의
  오라우팅(존재하지 않는 업스트림 스킬 권고)은 apply의 tx:plan 복귀 문장이 상시 오버라이드다
  — 삭제 금지 기록.
- "잠시 후 재시도해 구분한다"(CI 부재)는 유지 — 체크 부재의 두 독해가 모두 차단인 시점에
  시간만이 구분자라는 실측 합의.

## Risks / Trade-offs

- [목표-상태 형식이 미숙한 실행자에게 순서 모호] → 상태 간 의존이 사실 문장 안에 내재
  (rebase가 최신이어야 CI green이 의미를 갖는 식)하고, 시뮬레이션 13종이 수렴을 입증했다.
