## Why

advisor round 5의 발견: 관문(site)은 git 추적 비실행 text이면서 repo의 재접지 면역계
밖에 홀로 있다. settings.py의 init 값이 바뀌면 spec은 재접지되어도 site·README의 init
공개는 옛 값을 계속 게시한다 — 관문이 anchor가 "숨기지 마라"고 명시한 바로 그 disclosure에
대해 **거짓**을 말하게 되는데 어떤 check도 발화하지 않는다. og.png도 committed source
(og-card.html)와 결속이 없어 source가 바뀌어도 배포 image는 옛 story로 남는다.

## What Changes

- **`.github/workflows/site-truth-check.yml` 신설** (repo-side — seed 소유물인
  memory-check.yml 불가침): (1) `settings.py`의 PREREQUISITES + defaultMode +
  marketplace repo 값이 site/index.html·README.md·README.ko.md의 init 공개에 실값으로
  존재하는지 결정론 검사 — 값이 코드에서 바뀌면 방문자 표면이 함께 바뀌기 전에는 PR이
  red다. (2) PR diff에 og-card.html이 있으면 og.png 동반을 강제 — source·산출물 결합.
- **갈림길 판정 기록** (anchor: 스스로 판정하고 근거를 기록하라):
  - 기계 결속 가능한 주장(init 값·image 산출물)은 CI로 지금 결속한다 — 채택.
  - 산문 의미의 주기 재접지: site 산문은 MEMORY.md 정의상 장기기억(refine:docs domain)에
    속하나, refine:docs 운용 표면의 문서 home 열거에 site/·HTML이 명시되지 않아
    cartographer가 건너뛸 수 있다 — **이는 refine plugin의 결함 보고이며, 수리는 plugin
    behavior 변경이라 이 mission의 anchor 제약 밖이다(후속 change 후보).** 쓰기 시점
    방어는 close gate의 전 추적 text 상충 scan(HTML 포함)이 이미 소유한다.
  - 검증 불가능한 결속(배포된 HTML runtime 상태 등)은 두지 않는다.

## Capabilities

### New Capabilities

<!-- 없음 -->

### Modified Capabilities

- `landing-page`: Site 내용 계약에 진실 결속 요구 추가 — init 공개 값은 settings.py
  실값과 CI로 결속되고, share image는 source 변경과 동반이 강제된다.

## Impact

- 신규: `.github/workflows/site-truth-check.yml`
- 수정: `openspec/specs/landing-page/spec.md` (archive 시 delta sync)
- 보고(무변경): plugins/refine의 doc-home 열거에 site 부재 — 후속 change 후보
