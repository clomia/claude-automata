## Why

소유자가 제기한 3건 — openspec 사용 방향 검증(빈 `specs/`의 적정성), 추론 언어 아키텍처(한국어
프롬프트는 감사용인데 에이전트 추론까지 한국어일 이유가 없음), 어색한 한국어의 전수 제거 —
과 openspec 태스크에 merge 이후 행동이 실리는 갭. 프롬프트 표면이 방금 프로덕션 게이트를
통과했으므로 언어 아키텍처의 결정과 잔존 trip 제거는 지금이 적기다.

## What Changes

- **언어 레인 원칙 확립**: 언어는 독자가 정한다 — 사람이 읽는 표면은 한국어/사용자 언어,
  순수 추론 에이전트만 읽는 표면은 영어. 유일한 전환 레인 = main이 런타임에 조립하는 위임
  prompt(launch rules 1행). advice·narration·refine 미션은 의도적으로 한국어 잔존.
- **어휘·calque 스윕**: 사용자 예문("전체를 사는") 포함 calque 2문장, 문면→wording,
  거처→home(mirror 2벌+MEMORY 동반), 캐논의 발화→fire·축자→verbatim·잠식·소거·드리프트·
  산다-locative 자연화. 양도·컨텍스트·흡수·동결·표류는 자연 한국어로 판정해 보존.
- **tx:plan 가드 1행**: 태스크는 트랜잭션 안에서 완결된다 — merge 이후 행동은 후속 change.
  (미완료 태스크 데드락의 발견 시점을 close에서 plan으로 앞당김.)
- **배제 기록**: 소급 capability spec 전사 기각(루트 ARCHITECTURE 결정 기록) — 빈 `specs/`는
  설계상 정답, 첫 진짜 behavior delta의 ADDED에서 유기적으로 탄생.
- 이 레포 스킬(translate·commit) 해라체 전환, 소유자 명명 반영(Agent Orchestrator).

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- plugins/{ploop,tx,refine}의 스킬·에이전트·references 표면과 캐논(MEMORY, ARCHITECTURE,
  ploop ARCHITECTURE), .claude/skills 2종, 버전 3쌍(ploop 0.43.0 · tx 0.9.0 · refine 0.8.1).
- 요구사항(behavior) 변화 없음 — spec delta 없는 change, archive는 --skip-specs.
