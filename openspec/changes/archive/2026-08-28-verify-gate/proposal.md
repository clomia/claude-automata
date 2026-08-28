# verify-gate

## Why

tx를 쓰는 에이전트가 `tx:verify`를 과하게 소환한다. 실측 3종: spec 변경이 없는 change에
verify, verify pass 뒤 작은 수정마다 재-verify, 미세 변경에 verify. 원인은 prompt다 —
apply의 "spawn … until it passes"와 close의 "pass newer than the last **code** change"가
모든 편집을 pass 무효화로 읽히게 했고, delta 유무만이 게이트라 behavior가 움직이지
않은 delta도 소환됐다.

## What Changes

- 소환 조건이 "delta가 있다"에서 **"delta가 관찰 가능한 behavior를 움직였다"**로 좁아진다.
  그 밖의 change(delta 없음, behavior 보존)는 구현자가 그 자리에서 판정한다.
- close의 pass 유효 기준이 마지막 **code** 변경에서 마지막 **behavior** 변경으로 바뀐다 —
  behavior 보존 편집은 pass를 무효화하지 않는다. 재소환도 같은 기준이다.
- 소환 조건이 verify agent의 description에도 실린다 — apply·close가 로드되지 않은 직접
  spawn 경로의 유일한 게이트.
- 코드 강제 없음. "behavior가 움직였는가"는 기계가 판정할 수 없는 표면이다.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — verify stage에는 spec'd capability가 없다; `skip_specs`)

## Impact

- `plugins/tx/skills/apply/SKILL.md`: step 4와 description.
- `plugins/tx/skills/close/SKILL.md`: 닫힌 상태의 verify 불릿.
- `plugins/tx/agents/verify.md`: description; 보고 절의 중복 PASS 문장 제거.
- `plugins/tx/README.md`: apply 절.
- Version 0.17.2 → 0.18.0 (`pyproject.toml`의 0.17.0 표류 정렬 포함).
