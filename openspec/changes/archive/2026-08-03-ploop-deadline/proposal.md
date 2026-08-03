## Why

ploop의 종결 권위인 advisor는 Bash가 없어 시계를 읽지 못하고, narrator는 timestamp를
버린다 — 시간이 유한한 mission에서 advisor가 마감을 알 수 없는 관측 공백이 있다.
threshold 기반 자동 off는 기각됐다(무통보 pause가 wrap-up 창을 절단하고 종결 권위를
이원화한다): 코드는 시각 사실만 나르고, 마감 판단은 advisor의 기존 mandate가 흡수한다.

## What Changes

- anchor 최상단 frontmatter에 `deadline:`(ISO 8601, timezone 필수) 스팩을 공식화한다.
- Stop hook이 advisor 소집 지침을 조립할 때 deadline을 parse해 advisor prompt에 잔여
  시간 status 한 줄(`deadline: 2h 13m remaining` / `expired 23m ago` / unreadable 시
  원문 표면화)을 실어준다. 미선언 anchor는 비용 0.
- advisor instruction의 판단 절이 deadline semantics를 명시한다: 잔여 시간 내 정리를
  조율하고, expired는 그 자체로 종료 사유다.
- define-mission skill에 스팩 정보 한 문장을 추가한다 (지시가 아닌 정보).

## Capabilities

### New Capabilities

- `ploop-deadline`: anchor frontmatter deadline 선언과 advisor round별 잔여 시간 관측.

### Modified Capabilities

(없음)

## Impact

- `plugins/ploop/src/prompt.py` — deadline parse·status 렌더링, trigger 조립.
- `plugins/ploop/src/main.py` — arm 시점 anchor frontmatter 읽기와 status 주입.
- `plugins/ploop/prompts/instruction.md` — 판단 절 deadline semantics 한 줄.
- `plugins/ploop/skills/define-mission/SKILL.md` — 정보성 한 문장.
- `plugins/ploop/ARCHITECTURE.md` — 결정 20 기록 (자동 off 기각 근거 포함).
