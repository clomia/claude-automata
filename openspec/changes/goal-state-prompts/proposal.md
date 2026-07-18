## Why

소유자가 관측한 결함: close가 "활성 change가 있으면"이라 명시하고도 무관한 변경에서 매번
verify를 유도했다. 근본 원인은 절차 명령의 과잉 — "이력이 불명하면 재실행"이 의례적
재검증을 낳았다. 소유자 독트린: 구체적 지시는 임기응변 능력을 떨어뜨린다 — 특히 open·close는
목표하는 최종 상태만 서술하고, 도달은 에이전트의 지능이 한다.

## What Changes

- **open·close를 목표-상태 서술로 재설계**: "열린 상태 / 닫힌 상태 — 아래가 전부 참이면"
  형식. 절차(재시도 루프, force-with-lease 역학, 게이트 재실행 시점, conflict 해소법, stale
  브랜치 처리, 정리 커맨드)는 삭제 — 목표 상태에서 재구성된다. 계약 7종(verify spawn 형태·
  change-id-only·BASE 커맨드·refspec 형태·tx-* 잔존·CI 부재 차단·prefix 표)은 의미 동결 보존.
- **verify 오유도 수리**: "트랜잭션의 change마다 pass가 있고, 그 pass는 마지막 코드 변경
  이후의 것이다" — change 없는 트랜잭션에서 공진리로 소멸, archive 후 재개된 close의 재진입
  구멍(수신자 시뮬레이션이 발견)까지 커버.
- **plan·apply 독트린 정리 5건**: 엔진이 위반·소비 시점에 스스로 가르치는 지시 삭제
  (아티팩트 순서 열거, kebab-case 술어, 체크박스 갱신 절차, 게이트 전 비소비 — 전부 핀
  1.6.0 재실측 근거), 태스크 경계 가드는 보존.
- open_tx.py docstring 재정박, tx 0.11.0.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- plugins/tx의 스킬 4종(open·close·plan·apply)·src docstring 1행·버전 쌍. behavior 요구사항
  변화 없음 — delta-less, archive는 --skip-specs.
