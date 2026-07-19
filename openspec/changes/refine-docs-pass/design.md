## Context

refine:docs의 영역 5 검증(2,844행 기록: 발견 ecosystem 13·ploop 10·tx 9·memory 6·storefront 2,
기각 기록 40+건)이 입력이다. 합의 라운드는 미완주 — 이 문서의 판정이 그 자리를 대신한다.

## Goals / Non-Goals

**Goals:** 허위·낡음 제거(mismatch 전건), 소유 위임 수렴(고ROI duplication), 규칙의 충족
가능화. **Non-Goals:** 코드 수정(결함은 보고 — F2 사유 문자열), 프롬프트 표면(실행되는
텍스트), 저ROI docstring 수렴(T6·T7·T8·F4 — 상보 목적의 안정 앵커로 수용), F3 b·c·d(결정
엔트리 재구성 — 후속 refine 패스로 이연), F5 provenance 스탬프(관측 기록 관행=코드·테스트
docstring, 검증자=audit-harness-deps로 해소), 컨텍스트→context류 표기 통일.

## Decisions

- **언어 절은 레인 클래스로 서술한다.** "유일 사례" 단정이 반례 3클래스(상태 고지 4건·
  description 23건·훅 발신 전수)를 낳았다 — 원리(독자가 정한다)는 유지하되 기계·UI 레인을
  열거로 흡수. tx README는 정본 겸 storefront 영어 단일본으로 지위를 명시(E2·T9 해소).
- **고정 이름 규칙은 실태에 정합.** 규칙의 제3 클래스(횡단 도메인)는 유일 인스턴스(MEMORY.md
  자신)가 충족 불가능했다 — 도메인 이름 허용 + storefront 겸용 명시. mirror 2벌 한 커밋 동기.
- **재서술은 소유가 좁은 쪽을 축약한다**: 루트↔MEMORY(운반·불변식 1·refine×tx), 루트↔ploop
  (위임 prompt), ploop 절↔결정(전제·괄호·coda), 루트 README↔tx README(storefront 최소 요약).
- refine:code의 결함 수리 문장은 실행 표면 부재(#9 의도 제거)로 삭제 — 관심사의 axiom 이관
  누락 여부는 프롬프트 표면 결정으로 보고에 이월.

## Risks / Trade-offs

- [합의 라운드 생략으로 과잉 판정 위험] → 각 검증 기록의 다중 패스(2~6차)와 형제 비판
  intake가 이미 교차검증을 수행했고, 채택은 mismatch 전건+CONFIRMED duplication의 고ROI
  부분집합으로 한정했다.
