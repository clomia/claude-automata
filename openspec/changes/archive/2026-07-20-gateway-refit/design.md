## Context

소유자 4건 지시의 응고. license 선택과 copy 방향이 결정 사항이고, 나머지는 제거·생략의
집행이다. 카피라이팅은 Ogilvy 계열 원칙을 조사해 근거로 삼았다: headline이 투자 대부분을
운반한다(본문의 5배 읽힘), 구체가 수사를 이긴다(Rolls-Royce 시계 headline), 모든 문장이
독자 benefit을 실어야 한다, 사실 기반 long copy는 유효하다.

## Decisions

- **Apache-2.0 + NOTICE** — "재가공·재배포 시 기반 명시" 요구에 대한 표준 해. §4(d)가
  NOTICE의 attribution을 파생물·재배포 전체에 전파하고 §4(b)가 변경 고지를 강제한다.
  대안 기각: CC BY(코드 부적합 — CC 공식 권고), BSD-4-Clause(폐기·GPL 비호환),
  custom license(도입 마찰, badge·GitHub·PyPI tooling 파손). 법적 경계를 proposal에
  기록: 순수 "영감"은 저작권의 결속 범위 밖 — 실제 재사용은 전부 결속된다.
- **NOTICE 문안**: project 명·copyright·repo URL·기반 명시 요구 한 줄. license 본문과
  중복 없이 attribution payload만.
- **자기개발 copy가 unaffiliated 자리를 승계**: footer lead(en/ko)·og/banner head 우측
  배지("BUILT BY ITS OWN AGENTS"). 검증 가능한 사실(모든 기여 = Claude Code agent 작성 —
  git 이력으로 실증 가능)이므로 과장 아님.
- **version-up-alert**: 방문자 표면에서 전면 생략하되 init 공개의 정직성은 유지 —
  "plugin 4종 활성화" 같은 계수 표현을 "plugin 활성화"로 바꿔 거짓 없이 생략한다
  (init은 실제로 4종을 켠다; 계수를 지우면 표는 3종 소개와 모순 없이 성립).
- **SOURCE 행 제거**: .canon-link·.lang-tag CSS까지 제거. canon-links CI job은 유지 —
  README의 raw banner link 등 잔여 내부 link를 계속 결속한다.
- **R3 재작성은 REMOVED+ADDED**: archive 엔진이 MODIFIED에서 scenario 삭제를 차단하므로
  (gateway-v2에서 실측), scenario 집합이 재편되는 이번 변경은 요구 자체를
  "Site 내용 계약"→"Site 서사 계약"으로 교체한다.
- **카피 수선 3건**(원칙 근거): §05 lede "converges onto prerequisites"→평이한 동사
  (Ogilvy: 독자의 언어), refine "hours per run"→"3–12h"(구체>수사), thesis 한 절 압축
  (문장당 benefit 밀도). headline·tagline·exchange·fig caption은 원칙 부합으로 유지.

## Risks / Trade-offs

- [MIT→Apache-2.0은 기존 배포본에 소급 불가] → 0.1.6부터 적용, 과거 wheel은 MIT로 남는다.
  수용 — 소급은 어떤 license 변경도 불가능하다.
- [unaffiliated 제거로 상표 혼동 우려] → 소유자 명시 판정. "Claude"는 제품명 언급으로만
  등장하고 제휴 주장 문구는 없으므로 잔여 위험은 낮다.
- [shields license badge가 GitHub 감지 갱신까지 MIT로 표시될 수 있음] → badge는 실시간
  API 반영, LICENSE 교체 commit이 merge되면 따라온다. 잔여 지연은 수용.

## Open Questions

없음.
