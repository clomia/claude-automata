# verify-warrant

## Why

Opus 5.5가 텍스트 변경, 단순하고 자명한 fix까지 `tx:verify`를 소환해 비용과 시간을 낭비한다.
모델의 보수성 탓만이 아니다. `2026-08-28-verify-gate`의 소환 조건 "a delta that moved observable
behavior"는 이런 경우를 문자 그대로 포함한다: 모든 `fix`는 behavior를 움직이고, 사용자에게 보이는
문구도 observable behavior다. 이전 모델은 조건을 의도대로 넓게 해석했지만 Opus 5.5는 문자 그대로
따른다. 그래서 소환 조건을 의도 자체로 바꾼다.

## What Changes

- 소환 조건이 "behavior를 움직인 delta"에서 **"복잡한 변경, 또는 복잡한 구조의 비자명한 수정"**으로
  바뀐다. 기본값은 구현자 자신의 판정이다. 수정도 편집이므로 재소환은 같은 조건을 따른다.
- close의 불변식이 "pass가 마지막 behavior 변경보다 새롭다"에서 "verify가 필요했던(warranted)
  편집은 모두 verify를 거쳤다"로 바뀐다. close의 description에서는 `verify` 단계를 뺀다.
- 소환 조건과 spawn 계약(change-id만 넘긴다)은 agent description 한 곳에만 둔다. apply와 close는
  `warranted` 한 단어로 조건을 참조하고, 호출 code block은 삭제한다.
- 에이전트에 주입되는 텍스트는 순감소한다.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — verify stage에는 spec으로 정의된 capability가 없다; `skip_specs`)

## Impact

- `plugins/tx/agents/verify.md`: description
- `plugins/tx/skills/apply/SKILL.md`: step 4
- `plugins/tx/skills/close/SKILL.md`: description, verify 불릿
- `plugins/tx/skills/open/SKILL.md`: lifecycle 줄
- `plugins/tx/README.md`: usage, apply 절
- Version 0.18.0 → 0.18.1
