## Why

ploop launch 이후 사용자 개입의 대부분은 진행 상황과 판단 근거를 묻는 질의다. 이 질의가 loop
session으로 들어가면 orchestration과 Q&A가 섞여 main의 context를 오염시키고, 그 오염은
narration→advisor 입력과 loop.log 영구 기록까지 전파된다. 정작 main은 작업기억 설계상 지난
round를 잊으므로(rounds: discard) 질의의 정답은 main의 context가 아니라 외부화된 기록에 있다 —
기록을 읽어 답하는 표면이 없어, 관찰자(사용자)가 매번 쓰기 경로(loop session)로 들어오고 있다.

## What Changes

- ploop에 세 번째 표면 **docent**를 추가한다. ploop의 표면은 세 격리로 완성된다:
  1. **define** — anchor를 정의하는 사용자 대화 표면 (기존: define-mission·define-purpose)
  2. **loop** — launch로 시작하고 on·off로 상태를 조작하는 작업 표면 (기존: launch·off·on +
     hooks + advisor·narrator)
  3. **docent** — launch 이후 사용자 질의를 처리하는 read-only 표면 (신규)
- `/ploop:docent` skill 신규: 별도 session을 docent로 세우는 교리 — read-only 경계, 기록 표면
  의미론, fresh read·round 인용·관측/추론 구분의 응답 규율.
- `docent` console script(resolver) 신규: loop session들의 기록 파일 경로를 결정론으로
  열거·해석한다 (session 식별은 주입이 아니라 query-time 해석).
- ploop ARCHITECTURE.md에 3표면 구조와 docent 설계 결정 기록, README에 사용법 추가.
- ploop version 0.46.5 → 0.47.0.

## Capabilities

### New Capabilities

- `ploop-docent`: loop 기록의 read-only 질의 표면 — resolver의 session 열거·경로 해석 계약과
  docent skill의 격리 속성.

### Modified Capabilities

(없음)

## Impact

- plugins/ploop: `skills/docent/SKILL.md` 신규, `src/docent.py` 신규, pyproject
  `[project.scripts]` 1건 추가, `tests/test_docent.py` 신규, ARCHITECTURE.md·plugin.json 갱신
- README.ko.md·README.md — ploop 절 확장
- **loop·define 표면은 불변** — docent는 hook 0개, loop 상태 쓰기 0개로 기존 기계에 접점이 없다
