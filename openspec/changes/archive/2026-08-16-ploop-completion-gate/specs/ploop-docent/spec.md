# ploop-docent — delta

round는 advisor 호출 ordinal이 아니라 정지 간 시간 구간이 되었다(completion-gate 재설계).
resolver는 round ordinal을 ledger의 `round` field에서 읽고, 감사 수를 별도로 표기한다.

## MODIFIED Requirements

### Requirement: Resolver session 열거

`docent` console script는 data dir의 `{session}_anchor.md` glob으로 loop들을 발견하되, 호출
project directory에서 launch된 것으로 판정된 session(Project scope 판정 requirement)만
출력해야 한다(MUST). 그 밖 — 타 directory launch·판정 불가 — 은 출력해서는 안 되며(MUST
NOT), 숨긴 개수를 내용 없는 1행으로 고지해야 한다(SHALL — 무언의 절삭 금지).
`--exclude-converged` flag가 주어지면 phase가 converged인 session을 추가로 제외하고 제외
개수를 1행 고지해야 한다(SHALL). session마다 active 여부(`{session}_active` marker),
ledger의 phase·round ordinal(`round` field)·감사 수(advice_history 길이)·round_start_line,
최근 활동 시각(기록과 transcript 통산 최신 mtime — loop 상태 파일은 정지에만 움직이므로
transcript가 생존 신호다), anchor 첫 줄, 기록 파일 경로(anchor·loop.log·audit history·round
slice·ledger·candidates)를 출력해야 한다(SHALL). 정렬은 active 우선, 그 안에서 최근 활동
순이어야 하며(MUST), 출력은 English여야 한다(MUST).

#### Scenario: active와 converged loop 병렬 열거

- **WHEN** 이 directory에서 launch된 active loop 하나와 converged loop 하나가 data dir에 있을 때 resolver를 실행하면
- **THEN** 두 session이 모두 출력되고 active가 먼저 오며, 각각 phase·round ordinal·감사 수가 표기된다

#### Scenario: loop 없음

- **WHEN** data dir에 anchor가 하나도 없을 때 resolver를 실행하면
- **THEN** loop가 없다는 English 메시지와 함께 정상 종료한다(exit 0)

#### Scenario: 타 directory에서 launch된 loop은 노출되지 않는다

- **WHEN** 타 directory에서 launch된 session만 data dir에 있을 때 resolver를 실행하면
- **THEN** 그 session의 anchor 내용·기록 경로는 출력에 없고, 이 project에 loop이 없다는 메시지와 숨김 개수만 출력된다

#### Scenario: 완료 loop 제외 flag

- **WHEN** 이 directory의 advising loop과 converged loop이 있는 상태에서 `--exclude-converged`로 실행하면
- **THEN** converged loop은 출력에서 빠지고 제외 개수가 1행 고지된다
