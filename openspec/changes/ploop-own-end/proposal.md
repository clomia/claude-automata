# ploop-own-end

## Why

ploop의 멈춤 방지 장치(launch 검사·dialog guard·background gate·heartbeat·re-anchor)는 advisor loop와 한
기계다: armed 정지를 되돌리는 길은 standing directive 하나이고, 그것은 narrator 호출(무조건)과 advisor
호출을 싣는다. 어떤 switch도 장치만 arm하지 않는다. 그래서 끝이 loop 밖에 있는 anchor도 감사를 산다.

- **끝이 운영 도구의 완료 command인 무인 session** — Lora worker의 run은 `done(run)`으로 끝나고 daemon이
  session을 접는다. anchor가 "아무도 인증하지 않는다"고 말해도 launch notice와 매 directive가 그 반대를
  말한다. 완료 command 앞에서 멈춘 session이 loop를 돌았다(Lora 실측 2026-11, transcript census·청구
  기록): 짧은 run 셋에서 각 $10–18·6–10분, 긴 run 하나에서 narrator 482 요청·37분.
- **purpose anchor** — 완수가 없어 advisor의 completion verdict가 대상이 아니고(advisor instruction),
  결정 22는 purpose의 cadence 설계를 선행 과제로 남겼다. narrator·advisor는 purpose loop에서 멈춤 방지
  역할만 하고 조언가로서의 ROI는 매우 낮다(owner, 2026-11-20).

anchor가 제 끝을 선언할 기반의 관용구가 없다.

## What Changes

- anchor frontmatter의 `end: own`으로 anchor가 제 끝을 선언한다 — 끝은 anchor 자신의 것이고 어떤 loop
  agent도 인증하지 않는다. 그 loop는 background gate를 지난 매 정지를 **hold**로 되돌린다: standing
  directive에서 narrator·advisor에 속한 것을 모두 걷어낸 나머지(anchor 대조 자기감사·끝은 anchor가 말하는
  대로·candidates 주소). narration·감사·round 상태·bare 정지 규칙·자동 종료가 없다 — `/ploop:off`나
  session의 끝으로만 끝난다. guard·background gate·heartbeat·re-anchor·launch 검사는 그대로다.
- PreToolUse(`Agent`)가 그 loop에서 narrator·advisor 호출을 모두 거부한다.
- `end:`의 다른 값은 launch를 차단한다.
- loop notice가 launch skill 본문을 떠나 launch hook의 배달로 간다: loop 종류의 notice, 그다음 candidates
  주소. compaction 재정박이 anchor 뒤에 같은 것을 싣는다. key 없는 anchor에서 notice의 뜻은 그대로고,
  channel이 skill 본문에서 hook 배달로 옮기며 hook lane의 언어(영어)를 따른다.
- define-purpose가 key를 쓰고 anchor가 제 끝을 스스로 말하게 한다. define-mission은 그대로다 — mission은
  자신을 인증할 advisor를 지킨다. 이미 쓰인 anchor는 notice의 channel 말고는 오늘과 같다.

## Capabilities

### New Capabilities

- `ploop-own-end`: anchor의 끝 선언, launch가 알리는 loop 종류, hold, loop agent 거부.

### Modified Capabilities

- `ploop-completion-gate`: standing directive와 per-stop narration이 advisor loop(끝을 선언하지 않은
  anchor의 loop)의 것으로 한정된다.
- `ploop-candidates`: 차단된 launch는 차단 사유와 무관하게 주소를 배달하지 않는다(사유가 넷이 된다);
  매 정지의 주소 재배달은 directive와 hold 둘 다의 것이다.

## Impact

- `plugins/ploop/src/prompt.py`: frontmatter reader(`deadline_status`에서 분리해 공유), loop 종류 판정,
  종류별 loop notice, hold.
- `plugins/ploop/src/main.py`: launch(`end:` 검사·종류별 배달), stop(hold 분기), pre_tool_use(거부).
- `plugins/ploop/skills/launch/SKILL.md`(`<notice>` 삭제), `skills/define-purpose/SKILL.md`,
  `skills/docent/SKILL.md`(own-end loop의 행로는 transcript에 있다).
- `plugins/ploop/ARCHITECTURE.md`(결정 26 신설과 접점), `MEMORY.md` 불변식 5, root `ARCHITECTURE.md`의
  ploop × tx 계약(주입되는 것이 directive만이 아니다), tests.
- Version 0.57.3 → 0.58.0 (`plugin.json`·`pyproject.toml`·`uv.lock`).
- 하류(이 transaction 밖): Lora worker anchor가 frontmatter `end: own`을 얻고 worker plugin이 갱신된다.
  구버전 plugin은 `end:`를 모른 채 그 anchor로 오늘의 advisor loop를 돈다.
