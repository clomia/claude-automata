## Why

launch skill 본문은 "제시된 candidates 경로에 축적하라"고 지시하는데, 그 경로를 제시하는
유일한 channel이 Stop trigger라 round 0에는 주소가 없다 — 지시만 도착하고 지시대상이 없는
dangling reference다. main agent는 이를 자기 방식으로 해소한다(자체 경로 생성). 그러면
경로를 소유한 hook의 기계 전부가 그 파일을 보지 못한 채 조용히 죽는다: advisor 입력의
조건부 candidates 라인은 영원히 점화되지 않고, 종료 notice의 drain 지시도 발화되지 않으며,
다음 launch의 round reset도 그 파일을 지우지 못한다. 관측 신호가 없는 silent failure다.
자체 경로가 repo 안에 생기면 "상태는 사용자 repo 바깥" 원칙까지 깨진다.

기존 canon은 이를 "첫 trigger에서 파일로 이동하는 self-healing"으로 수용했으나, 그 이주는
main agent의 자발적 병합을 전제할 뿐 기계 보장이 없다. UserPromptExpansion hook은
`hookSpecificOutput.additionalContext`를 공식 지원하므로(공식 hooks 문서: additionalContext는
UserPromptSubmit·UserPromptExpansion에서 제출된 prompt와 나란히 실린다), 주소를 지시와 같은
턴에 결정론으로 배달할 수 있다.

## What Changes

- launch hook이 성공적으로 loop를 arm할 때, 이 세션의 candidates 경로를 확장된 skill body와
  같은 턴에 main agent에게 전달한다(`hookSpecificOutput.additionalContext`).
- 차단된 확장(active loop·빈 anchor·미충족 prerequisite)은 경로를 전달하지 않는다 — 차단과
  주소 배달은 배타적이다.
- trigger의 상시 candidates 라인은 유지된다. launch는 최초 공급, trigger는 compaction 이후의
  재공급으로 역할이 갈린다 — anchor의 다겹 정박과 같은 구조다.
- `/ploop:on`·`/ploop:off`는 candidates를 지시하지 않으므로 대상 밖이다.

## Capabilities

### New Capabilities

- `ploop-candidates`: main agent의 승격 대기열 주소가 loop 참여자에게 도달하는 규약.

### Modified Capabilities

(없음)

## Impact

- `plugins/ploop/src/prompt.py` — candidates 경로 안내 문구의 단일 소스, launch용 context 조립.
- `plugins/ploop/src/main.py` — launch 성공 경로의 additionalContext emit.
- `plugins/ploop/ARCHITECTURE.md` — 파일 표·hook 표 갱신, 알려진 한계("round 0에는 candidates
  경로가 전달되지 않는다") 제거.
- `plugins/ploop/tests/test_main.py` — 성공 시 배달·차단 시 미배달.
- (편승) `plugins/ploop/skills/launch/SKILL.md` — owner가 이 transaction 밖에서 낸 문장부호
  정리. 이 변경의 산물이 아니며 squash에 함께 실린다. 이 변경이 의존하는 skill 본문 문구
  ("제시된 candidates 경로")는 그 이전 commit `1a7d0d7`에서 이미 착지했다.
