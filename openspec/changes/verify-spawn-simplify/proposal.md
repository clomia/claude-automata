## Why

소유자 판정: verify spawn의 `run_in_background=false` 파라미터는 불필요하다. 실측이 뒷받침한다
— 하네스는 이 파라미터를 advisory로 취급해 bg로 승격시키기도 했고, 그 상태에서도 흐름은
무결했다(완료 알림이 실행자를 깨우고 다음 단계는 verdict를 대기). 실제 계약은 파라미터가
아니라 "verdict가 다음 단계를 게이트한다"는 순서다.

## What Changes

- tx:apply·tx:close의 verify spawn 구문에서 파라미터 제거 —
  `Agent(subagent_type="tx:verify", prompt="change-id: <change-id>")`. close만 지시받았으나
  같은 spawn 계약이 apply에도 있어 두 형태로 갈라지지 않게 양쪽 제거.
- tx README의 "The spawn is foreground" 문장 재서술 — 순서 계약(verdict가 모든 다음 단계를
  게이트, 수리는 구현 컨텍스트가 살아있을 때)만 남기고 foreground 메커니즘 주장 삭제.
- ploop 트리거의 run_in_background=false 3곳은 무접촉 — advice가 stop 전에 존재해야 하는
  별개 계약(ploop 결정 10).
- tx 0.10.0.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- plugins/tx의 스킬 2종·README·버전 쌍. behavior 요구사항 변화 없음 — delta-less,
  archive는 --skip-specs.
