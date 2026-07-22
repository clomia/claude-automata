## MODIFIED Requirements

### Requirement: Resolver session 열거

`docent` console script는 data dir의 `{session}_anchor.md` glob으로 loop들을 발견하되, 호출
project directory에서 launch된 것으로 판정된 session(Project scope 판정 requirement)만
출력해야 한다(MUST). 그 밖 — 타 directory launch·판정 불가 — 은 출력해서는 안 되며(MUST
NOT), 숨긴 개수를 내용 없는 1행으로 고지해야 한다(SHALL — 무언의 절삭 금지).
`--exclude-converged` flag가 주어지면 phase가 converged인 session을 추가로 제외하고 제외
개수를 1행 고지해야 한다(SHALL). session마다 active 여부(`{session}_active` marker),
ledger의 phase·round ordinal(advice_history 길이)·round_start_line, 최근 활동 시각(기록과
transcript 통산 최신 mtime — loop 상태 파일은 정지에만 움직이므로 transcript가 생존
신호다), anchor 첫 줄, 기록 파일 경로(anchor·loop.log·advice history·round slice·ledger·
candidates)를 출력해야 한다(SHALL). 정렬은 active 우선, 그 안에서 최근 활동 순이어야
하며(MUST), 출력은 English여야 한다(MUST).

#### Scenario: active와 converged loop 병렬 열거

- **WHEN** 이 directory에서 launch된 active loop 하나와 converged loop 하나가 data dir에 있을 때 resolver를 실행하면
- **THEN** 두 session이 모두 출력되고 active가 먼저 오며, 각각 phase와 round ordinal이 표기된다

#### Scenario: loop 없음

- **WHEN** data dir에 anchor가 하나도 없을 때 resolver를 실행하면
- **THEN** loop가 없다는 English 메시지와 함께 정상 종료한다(exit 0)

#### Scenario: 타 directory에서 launch된 loop은 노출되지 않는다

- **WHEN** 타 directory에서 launch된 session만 data dir에 있을 때 resolver를 실행하면
- **THEN** 그 session의 anchor 내용·기록 경로는 출력에 없고, 이 project에 loop이 없다는 메시지와 숨김 개수만 출력된다

#### Scenario: 완료 loop 제외 flag

- **WHEN** 이 directory의 advising loop과 converged loop이 있는 상태에서 `--exclude-converged`로 실행하면
- **THEN** converged loop은 출력에서 빠지고 제외 개수가 1행 고지된다

## ADDED Requirements

### Requirement: Project scope 판정

resolver는 호출 project directory를 `--project-dir` flag → `CLAUDE_PROJECT_DIR` env →
process cwd 순으로 해석해야 하며(SHALL), 빈 문자열 flag·env는 미설정으로 취급해야 한다
(MUST). docent skill은 resolver 호출에 `--project-dir "${CLAUDE_PROJECT_DIR}"`를 관통시켜야
한다(SHALL) — Bash 환경에는 CLAUDE_* 변수가 주입되지 않으므로(실측 2026-07, v2.1.216) skill
본문 placeholder 치환이 유일한 전달 lane이다. session의 launch directory 판정은 launch
provenance 기록(`{session}_project`)이 있으면 그 값과 해석된 path의 일치이고(SHALL — 기록이
transcript보다 우선한다(MUST)), 기록이 없으면 transcript 부모 directory 이름과 해석된
path의 관측 encoding 대응이 fallback이다(SHALL — 대응은 encoding 규칙의 변형을 관용해야
한다(MUST — ASCII 영숫자는 대소문자 무시 동일성, 그 외 문자는 `-` 또는 동일성, 길이 일치)).
기록도 transcript도 없어 판정이 불가능한 session은 노출해서는 안 된다(MUST NOT — 기록
파일은 data dir에 남으며 숨김 개수로만 고지된다). 손상되어 읽을 수 없는 provenance 기록은
기록 부재로 강등되어야 한다(MUST — 한 session의 손상이 목록 전체를 죽여서는 안 된다).

#### Scenario: 기록이 transcript보다 우선한다

- **WHEN** session의 provenance 기록이 타 directory를 가리키고 transcript는 이 directory 이름 아래 있으면
- **THEN** 그 session은 노출되지 않는다

#### Scenario: 기록 없는 legacy는 transcript로 판정된다

- **WHEN** provenance 기록이 없는 session의 transcript가 이 directory 이름 아래 있으면
- **THEN** 그 session은 나열된다

#### Scenario: encoding 변형 관용

- **WHEN** project path가 비영숫자 문자를 포함하고 transcript 부모 이름이 그 문자를 `-`로 치환한 형태이면
- **THEN** 그 session은 이 directory에 귀속 판정된다

#### Scenario: 판정 불가는 노출되지 않는다

- **WHEN** provenance 기록도 transcript도 없는 session이 있으면
- **THEN** 그 session은 출력에 없고 숨김 개수에 계수된다

### Requirement: Launch provenance 기록

launch hook은 loop을 arm할 때 launch project directory(`CLAUDE_PROJECT_DIR` env → event
cwd → process cwd)를 `{session}_project`에 기록해야 한다(SHALL). Stop hook은 active
loop에 기록이 없으면 같은 규칙의 값으로 backfill해야 한다(SHALL — 기록 도입 이전에 launch된
fleet의 수렴 경로). round state 정리는 이 기록을 지워서는 안 된다(MUST NOT).

#### Scenario: launch가 출처를 기록한다

- **WHEN** `/ploop:launch`가 loop을 arm하면
- **THEN** `{session}_project`에 launch directory가 기록된다

#### Scenario: 기존 loop은 다음 정지에서 수렴한다

- **WHEN** 기록 없는 active loop의 session에서 Stop hook이 실행되면
- **THEN** gate 통과 여부와 무관하게 기록이 생성된다
