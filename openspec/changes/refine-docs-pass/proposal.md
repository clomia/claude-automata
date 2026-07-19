## Why

refine:docs 워크플로우가 census·검증·비판까지 완주한 뒤(발견 40건, 영역 5) 소유자 판단으로
중단됐다 — 전체 워크플로우는 과하고, 산출을 종합해 직접 최적화한다. 코드는 수정하지 않고
결함은 보고한다(문서 정합 규약). docstring은 도메인 안이라 stale 열거 1건만 수리.

## What Changes

- **루트 ARCHITECTURE 7건**: 언어 절이 실태의 영어 레인 3클래스(상태 고지·description
  메타데이터·훅 발신 메시지)를 흡수하고 tx README의 지위(정본 겸 storefront, 영어 단일본)를
  명시. 인트로 gloss의 위임 용어 재정의 삭제(응고 관문·anchor), Stop 계약 괄호를 루트 소유로
  정정, refine×tx 불릿을 헤더+포인터로, close 정합·운반 괄호 재서술 축약.
- **MEMORY 5건**: npm pack 미구현 서술 삭제, launch 질문 제한 문구를 현행으로(상시 게이트
  아님), 불변식 1 괄호의 가드 훅 재서술을 소유 위임으로, dangling δ 기호 삭제, 고정 이름
  규칙을 충족 가능하게 보정(구조 단위=ARCHITECTURE.md·storefront 겸용 허용·횡단 도메인=도메인
  이름) — mirror 2벌 동기.
- **tx README 3건**: workflow scope "once per repository" 부정확 수정(pin drift 재커밋 명시),
  씨앗 CI의 "test greenness" 허위 제거, pause 비면제 문서 내 이중 서술 축약.
- **ploop 정본 7건**: temp 파일 "advice.md만"→3파일, transient 열거에 gated_shells, 기술
  리스크 4의 degrade 서술을 실동작으로 정정(미발동=2라운드 failsafe 종료), 언어 절의 루트
  재서술 축약+trigger 영어 명시, 절↔결정 재서술 3건(활성화 lifecycle 전제·recap 괄호·depth-0
  coda) 삭제. main.py docstring의 stale 4항 열거 1건 수리.
- **루트 README 한·영**: refine:code의 결함 수리·문서 정합 주장 삭제(#9가 메커니즘을 의도
  제거 — 실행 표면에 부재), tx 절을 정체+스킬 흐름 2불릿으로 축약(플러그인 README 위임 강화).
- 버전: ploop 0.45.1 · tx 0.11.1 · refine 0.8.3.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- 캐논 4종·README 3종·docs-surface mirror 2벌·main.py docstring 1행·버전 3쌍. behavior
  요구사항 변화 없음 — delta-less, archive는 --skip-specs.
