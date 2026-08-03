## 1. Deadline parsing and rendering

- [x] 1.1 `prompt.py`: `deadline_status(anchor, now)` — frontmatter parse, aware-datetime
      요구, remaining/expired/unreadable/무선언 4상태 렌더링
- [x] 1.2 `format_advisor_trigger`가 status를 advisor prompt block의 한 줄로 싣는다
      (미선언 시 무출력)

## 2. Loop wiring

- [x] 2.1 `main.py` `arm_advisor`: anchor를 한 번 읽어 compaction 재주입과 deadline
      status 계산에 공용, trigger에 전달

## 3. Prompt and skill surfaces

- [x] 3.1 `prompts/instruction.md` 판단 절에 deadline semantics 한 줄
- [x] 3.2 `skills/define-mission/SKILL.md`에 스팩 정보성 한 문장 (define-purpose 제외)

## 4. Canon and release

- [x] 4.1 `ARCHITECTURE.md` 결정 20: 시계는 정보·집행은 advisor, 자동 off 기각 근거
- [x] 4.2 tests: `deadline_status` 상태 4종·경계, trigger 삽입, arm 경유 end-to-end
- [x] 4.3 version 0.52.0 -> 0.53.0 (plugin.json·pyproject·uv.lock)
