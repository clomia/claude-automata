## Context

소유자 프롬프트 개선은 저작 그대로 탑재한다(불가침 — 수정 필요 시 허락 선행). 이 문서는
동승 항목 2건의 판정과 정합 스캔 결과만 기록한다.

## Goals / Non-Goals

**Goals:** 보고 항목 2건 처리, 소유자 개선의 정합 흡수. **Non-Goals:** 소유자 프롬프트 재수정,
advisor.md의 턴·라운드 정의 이동에 대한 정본 개정(정본이 용어를 소유하므로 프롬프트 내
자기 정의는 불요 — 무개정이 정합).

## Decisions

- **사유 문자열은 상태 추가 없이 정직화한다**: 이전 anomaly 종류를 ledger에 기록하는 방안은
  스키마 순증이라 기각 — "two consecutive anomalous rounds (in this one …)" 형태가 혼합·순수
  streak 모두에서 참이고, 설계 의도("거부를 고장으로 위장하지 않음")를 충족한다.
- **refine:code의 결함 관심사는 axiom이 거처다**: README 주장(#21에서 삭제)이 아니라
  principles가 모든 worker에 주입되는 판단 기준이므로, 워크플로우 기계 재도입 없이 1행으로
  복원한다(integrity의 동형 패턴).
- **verify는 delta가 소환한다**: 기억 정본의 이론(라우팅 표 — verify는 SHALL+Scenario 증거
  탐색자, 불변식 3 — spec이 구현을 구속)과 실측이 일치 — delta 없는 change의 verify는
  정박점 없는 재검토였다. 수용한 트레이드오프: 아티팩트 정밀도 결함은 이제 저자·CI 형식
  검사만이 관문이다.
- 정합 스캔 실측: 계약 결합(트리거 라벨 action-history·종료 토큰) 무손상, 구 문면 인용
  잔향은 README 라우팅 안내 1건뿐 — 새 정의 어휘로 동기화.

## Risks / Trade-offs

- [소유자 문면과 정본 서술의 미세 간극(예: advisor 소환 시점의 단순화)] → 정본이 메커니즘의
  정본이고 프롬프트는 수신자용 압축 — 간극은 설계된 역할 분담으로 수용.
