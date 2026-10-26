# verify-warrant — design

## Context

See proposal.md — Why. 이 change는 `2026-08-28-verify-gate` design의 Decision 1·2·3을 뒤집는다.
제약은 같다: 에이전트에 주입되는 텍스트는 irreducible해야 하고, 소환 조건은 기계로 강제하지 않는다.

## Decisions

1. **조건은 proxy가 아니라 의도 그대로 쓴다.** behavior 이동은 위험의 proxy였고, 문자 그대로 읽으면
   자명한 fix까지 포함한다. verify의 가치는 clean context다. 그래서 조건은 구현자 자신의 context가
   판정을 흐릴 수 있는 경우, 곧 복잡한 변경이나 복잡한 구조의 비자명한 수정이다.
2. **조건은 description 한 곳에 두고, apply와 close는 `warranted`로 참조한다.** description은 Agent
   도구 목록에 늘 올라 있어서 직접 spawn 경로, apply, close만 로드된 세션 모두에서 읽힌다.
   "Costly"는 경계 사례에서 비용을 저울질하게 한다. spawn 계약(change-id alone)도 description이
   소유한다. 그동안 이 계약은 apply와 close의 lead-in과 code block에 중복돼 있었고, 절차 step 안의
   code block은 "실행하라"는 신호로 읽혀 소환을 부추겼다.
3. **판정의 기본값은 구현자 자신이다.** 기존 Decision 2는 둘 다 하는 독해(자기 판정 후 verify)가
   무해하다고 봤지만, 보수적인 모델에서는 그 독해가 기본 동작이 되어 비용이 된다. apply는
   "judge the implementation yourself"로 기본값을 명시한다. 의심의 실측은 apply의 Unknown 처리
   절이 이미 지시한다.
4. **close의 불변식은 pass가 아니라 warrant를 본다.** 기존 Decision 3의 "pass newer than the last
   behavior change"는 FAIL 뒤 자명한 수정에도 pass를 다시 요구하고, apply의 "respawn until"이
   그 고리를 만들었다. 둘을 지우면 수정도 편집의 하나로 같은 warrant 조건을 따른다. defect 해결은
   close 머리말의 무결 선언에서 파생되므로 따로 적지 않는다. 불변식의 술어는 "has been verified"가
   아니라 "has been through it"이다. "verified"는 PASS로 읽혀 지운 고리를 close에서 되살린다.

기각한 대안:

- diff 크기 같은 기계 게이트: 복잡한 구조의 작은 수정이 빠진다. 복잡도는 코드로 판정할 수 없는
  표면이다.
- verify의 `effort`를 낮추기: 정말 필요한 소환에서 깊이를 잃는다. 비용은 소환 빈도로 줄인다.

## Risks / Trade-offs

- [과소 소환: 복잡한 변경을 자명하다고 판단해 건너뜀] → close의 warrant 불변식이 한 번 더
  묻는다. 사후 실측으로 재평가한다.
