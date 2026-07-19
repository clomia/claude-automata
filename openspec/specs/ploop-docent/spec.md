# ploop-docent Specification

## Purpose
TBD - created by archiving change ploop-docent. Update Purpose after archive.
## Requirements
### Requirement: Resolver session 열거

`docent` console script는 data dir의 `{session}_anchor.md` glob으로 loop들을 열거하고, session마다
active 여부(`{session}_active` marker), ledger의 phase·round ordinal(advice_history 길이)·
round_start_line, 최근 활동 시각(기록과 transcript 통산 최신 mtime — loop 상태 파일은 정지에만
움직이므로 transcript가 생존 신호다), anchor 첫 줄, 기록 파일 경로(anchor·loop.log·advice
history·round slice·ledger·candidates)를 출력해야 한다(SHALL). 정렬은 active 우선, 그 안에서 최근 활동 순이어야 하며(MUST),
출력은 English여야 한다(MUST).

#### Scenario: active와 converged loop 병렬 열거

- **WHEN** data dir에 active loop 하나와 converged loop 하나가 있을 때 resolver를 실행하면
- **THEN** 두 session이 모두 출력되고 active가 먼저 오며, 각각 phase와 round ordinal이 표기된다

#### Scenario: loop 없음

- **WHEN** data dir에 anchor가 하나도 없을 때 resolver를 실행하면
- **THEN** loop가 없다는 English 메시지와 함께 정상 종료한다(exit 0)

### Requirement: Data dir 해석 체인

resolver는 data dir를 `--data-dir` flag → `CLAUDE_PLUGIN_DATA` env → `~/.claude/plugins/data/ploop-*`
glob 순으로 해석해야 한다(SHALL). 빈 문자열 flag·env는 미설정으로 취급해야 한다(MUST).

#### Scenario: 빈 flag는 env로 fallback

- **WHEN** `--data-dir ""`와 유효한 `CLAUDE_PLUGIN_DATA` env로 resolver를 실행하면
- **THEN** env가 가리키는 data dir가 사용된다

### Requirement: Transcript 해석

resolver는 session마다 main transcript를 `~/.claude/projects/*/{session}.jsonl` glob으로 찾아 그
절대 경로와 worker 기록 위치(`{project dir}/{session}/subagents/agent-*.jsonl`)를 출력해야
한다(SHALL). transcript를 찾지 못하면 그 사실을, subagents dir가 없으면 부재를 명시해야
한다(MUST).

#### Scenario: transcript 존재

- **WHEN** session의 transcript가 `~/.claude/projects/` 아래에 존재하면
- **THEN** 그 절대 경로와 `{session}/subagents` worker 기록 경로(부재 시 absent 표기)가 출력된다

### Requirement: Read-only 보증

resolver는 어떤 파일도 생성·수정·삭제해서는 안 된다(MUST NOT).

#### Scenario: 실행 전후 무변화

- **WHEN** 기록이 있는 data dir에 resolver를 실행하면
- **THEN** 실행 전후 data dir의 파일 목록과 내용이 동일하다

### Requirement: Docent skill 표면

`/ploop:docent` skill이 존재해야 하며(SHALL), resolver 호출 지시를 포함해야 한다(MUST). skill은
hook 등록 없이 동작해야 하고(MUST — hooks.json에 docent 항목이 없다), loop 상태를 변이하는 지시를
포함해서는 안 되며(MUST NOT), `disable-model-invocation: true`여야 한다(MUST) — loop session이
스스로 docent 교리를 주입해 orchestrator 정체성과 충돌하는 것을 막는다.

#### Scenario: 교리 주입

- **WHEN** 사용자가 별도 session에서 `/ploop:docent`를 호출하면
- **THEN** docent 교리와 resolver 사용법이 주입되고 ploop의 어떤 hook도 fire하지 않는다

