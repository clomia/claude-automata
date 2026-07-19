## Why

소유자가 ploop 프롬프트 5종을 직접 전수 개선했다(advisor 정체성·representation space 근거,
instruction의 Local Optimum 감지 지침, define-mission/purpose 정의 정밀화, launch CONSTITUTION
다듬기). 여기에 앞서 위임된 보고 항목 2건(anomaly 사유 정직화, refine:code axiom 복원)과
정합 동기화가 같은 트랜잭션에 실린다.

## What Changes

- **소유자 프롬프트 개선(불가침 탑재)**: advisor.md·instruction.md·define-mission·
  define-purpose·launch SKILL.md — 소유자 저작 그대로.
- **anomaly failsafe 사유 정직화**: 혼합 streak에서 종류를 단정하던 종료 문자열 2개를
  "연속 anomaly 사실 + 이번 라운드의 사실"만 말하는 형태로 교체(ledger 스키마 순증 없음),
  종료 사유 테스트 1건 동기화(RETRY 노티스 단정은 보존).
- **refine:code axiom 복원**: principles.md에 1행 — 최적해의 정상동작 전제와 결함 수리·문서
  정합 관심사를 axiom으로(#9의 omission-first 정신, integrity와 동형).
- **정합 동기화**: README 한·영의 mission 라우팅 안내를 새 정의 어휘("완료 조건이 명확한
  목표")로.
- **verify 필요조건 재설계(소유자 지시)**: verify spawn은 spec delta를 가진 change에만 —
  판정 3축은 Requirement·Scenario 증거에 정박하므로 delta-less에선 산문 재검토로 퇴화한다
  (세션 실측: delta-less verify ~10회의 발견 전부 아티팩트 정밀도 minor, 구현 결함 0).
  delta-less의 관문은 태스크 게이트·CI·docs 게이트. close·apply·tx README 동기 개정.
- 버전: ploop 0.46.0 · refine 0.9.0 · tx 0.12.0.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- plugins/ploop 프롬프트 5종·src 문자열·테스트 1단정, plugins/refine principles, README 한·영,
  버전 2쌍. spec delta 없음 — archive는 --skip-specs.
