## Context

관문(README 쌍·site)은 landing-page spec이 계약으로 고정하고 site-truth-check CI
(init-disclosure·canon-links·og-coupling)가 결박한다. 현행 설치 안내는 사람이 `uvx
claude-automata init`을 실행하는 단일 경로다. 도입 현장의 실측(brownfield 편입 리포트와
그 처분, 2026-07)은 설치가 명령 실행이 아니라 **편입 판단의 연속**임을 보여줬다 — 기존
CI와의 중복 해소, living form 위반의 수선 방식, 기존 spec 체계의 처분, 보호 정책의 교차.
이 판단은 대상 repo의 맥락을 가진 agent의 것이다.

## Goals / Non-Goals

**Goals:**

- 설치 주체를 agent로: 사람은 복사형 prompt 한 줄만 건넨다.
- 지침은 goal-state — installed state 술어와 oracle만. 경로 도출은 대상 agent의 몫.
- 기존 관문 계약(init 단일 경로 공개, CI 결박)은 형태만 재배치하고 전부 유지.

**Non-Goals:**

- init CLI·plugin 구현 변경 — 배포물 불변, version bump 없음.
- 기존 harness를 가진 repo를 위한 특수 경로·설정 표면 — installed state 술어가 존중
  경계를 운반하고, 구체 판단은 위임한다.
- INSTALL.md의 한국어 쌍 — 관문 연장은 English 단일본이다(아래 결정).

## Decisions

- **D1: goal-state 형식.** installed state 술어 집합 + oracle 지정만 싣고 절차를 강제하지
  않는다. 근거: 절차 지침은 환경 다양성 앞에서 틀리거나(false assumption) 사고를 제한한다
  (llm-prompt 규칙). tx skill의 열린/닫힌 상태 관례(goal-state-prompts)의 연장이라 생태계
  안에서 형식이 일관된다. oracle 우선 원칙을 문서 말미에 명시해 문서 자신도 oracle 아래 둔다.
- **D2: English 단일본.** INSTALL.md의 독자는 임의 사용자 repo의 agent + 평가 중인
  방문자(복사할 prompt가 가리키는 대상을 감사한다)다 — 관문의 연장이므로 방문자 표면
  언어 정책(English 1순위)을 따른다. tx README(정본 겸 marketplace 대면, 영어 단일본)와
  같은 class. ARCHITECTURE 언어 정책에 등재한다.
- **D3: init 재서술 금지, oracle 지정.** INSTALL.md는 init이 무엇을 쓰는지 나열하지
  않는다 — init 출력이 그 정본이고, 공개 의무는 README·site가 이미 진다(init-disclosure
  결박). 문서는 "출력의 note가 전부 해소된 상태"를 술어로 요구할 뿐이다.
- **D4: 존중 경계를 술어로 인코딩.** "host harness 존중"을 지시가 아니라 상태로 쓴다:
  동결 이력 byte-identical / harness 원형 유지 / repo 소유 결정의 사용자 귀속. 위반이
  아니라 미도달로 판정되게 하는 것이 goal-state의 이점이다.
- **D5: 관문 재배치는 spec delta로.** README 관문화·Site 서사 계약의 설치 절 문구를
  MODIFIED로 갱신하고 INSTALL.md 지속 계약을 ADDED로 신설 — 관문은 spec이 계약으로
  고정하는 표면이므로 문서만 고치고 spec을 두면 다음 refine이 drift로 판정한다. site의
  "repo link는 root 한 곳 수렴" 조항은 INSTALL.md를 두 번째 수렴점으로 확장한다.
- **D6: prompt 문구는 표면 언어를 따른다.** English 표면(README.md·site `/`)은 English
  prompt, 한국어 표면(README.ko.md·`/ko/`)은 한국어 prompt — prompt는 사용자가 자기
  agent에게 건네는 발화라 표면 언어가 곧 사용자 언어다. URL은 blob/main 고정
  (사람 clickable + agent fetch 겸용, canon-links가 대상 존재를 결박).

## Risks / Trade-offs

- [위임 prompt를 받은 agent가 INSTALL.md 없이 임의 설치를 시도] → prompt가 URL을
  명시하므로 문서 도달이 1단계다; 도달 실패 환경(offline)에서는 어차피 init도 불가.
- [installed state가 미래 seed behavior와 표류] → 술어를 seed 보고 문자열·CI 이름 같은
  안정 표면에 정박하고 세부는 oracle에 위임 — 표류 시 refine:docs의 재접지 대상이며,
  INSTALL.md는 living 문서다.
- [README·site의 설치 절이 길어져 관문 밀도 하락] → prompt 블록 1개 + 기존 블록 유지로
  증분을 한 블록으로 제한한다.

## Migration Plan

단일 tx. site는 main 병합 시 pages workflow가 자동 발행한다.

## Open Questions

없음.
