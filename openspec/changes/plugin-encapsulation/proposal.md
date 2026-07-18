## Why

소유자가 확정한 캡슐화 독트린: ploop·tx·refine은 선택 장착을 위해 분리된 플러그인이고,
각각은 형제의 존재를 몰라야 단독 설치 레포에서 죽은 텍스트 없이 동작한다. 전수조사 결과
런타임 표면 5곳·플러그인 정본 1곳이 형제를 명명하고 있었다.

## What Changes

- **HARD 5**: launch rules의 "승격은 tx 트랜잭션으로" → "승격은 레포의 응고 관문으로"(역할만
  지시, 도구 무명명 — 관문의 정체는 tx 가드가 쓰기 순간에 스스로 가르침). 공유 docs-surface의
  형제명 3건("tx verify"→"구현 증거 탐색이 검증한다", "refine:docs"→"코드 구조와의 재접지가
  검증한다", "tx 재승격"→"재승격") + ploop 전용 개념 1건("루프가 죽으면"→"산출 세션이 죽으면").
- **SOFT 1**: ploop 정본의 관문 예시에서 tx 탈명명(독립 검증·CI가 일반 주장 운반).
- **동반**: 루트 ARCHITECTURE 접면 절 재서술 — 삭제된 launch 응고 포인터 메커니즘 대신 라이브
  인터페이스(tx 가드 표면의 just-in-time 교육) 기술. 루트 정본의 플러그인 명명 자체는 정당.
- 소유자 재작성 launch(CONSTITUTION/rule 구조)·instruction 탑재 + instruction 어조를
  language.md 규약(해라체)으로 정규화(의미 무변). stale `/goal` 참조 → anchor.
- 버전: ploop 0.44.0 · tx 0.9.1 · refine 0.8.2.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- plugins/{ploop,tx,refine}의 스킬·정본·references(공유 docs-surface 2벌 byte-identity 유지),
  루트 ARCHITECTURE, 버전 3쌍. 요구사항(behavior) 변화 없음 — delta-less, archive는 --skip-specs.
