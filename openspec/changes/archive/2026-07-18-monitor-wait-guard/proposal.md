## Why

소유자가 실전에서 반복 관측한 오용: 에이전트가 Monitor를 "무언가를 기다리는" 용도로 걸고
라운드를 끝낸다. 그러나 ploop Stop 게이트는 monitor를 통과시킨다(결정 16 — 세션 수명
프로세스를 게이트하면 영구 교착) — advisor가 소집되어 대기 의도가 붕괴한다. 공식 문서가
Monitor 용례로 poll PR/CI를 들어 루프 밖의 정당한 패턴이 루프 안의 함정이 된다. 현행 launch
행은 Monitor를 ambient의 거처로 소개만 하고 금지 방향이 없다.

## What Changes

- launch rules의 Monitor 행 재작성: "~에만 사용하라"(라이브 ambient 전용) + 완료 대기 금지 +
  근거 1구("advisor 소집을 막지 않으므로"). "라운드 안에서 정리하라"는 삭제 — shell 차선의
  1회 교정 지시(결정 16, 코드)가 위반 순간에 같은 내용을 기계로 전달한다.
- ploop 0.45.0.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- plugins/ploop/skills/launch/SKILL.md 1행 + 버전 쌍. behavior 요구사항 변화 없음 —
  delta-less, archive는 --skip-specs.
