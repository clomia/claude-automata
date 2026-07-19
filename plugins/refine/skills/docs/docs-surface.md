출처: https://github.com/clomia/claude-automata — 배포 사본이다. 사본이 표류하면 출처가 이긴다.

# docs 표면 규약 — 자유 산문 장기기억의 쓰기 규칙

장기기억은 git 추적되는 실행 불가능한 모든 text다. 그중 openspec 밖 자유 산문이 docs
표면이다 — 문법도 validate도 없어 이 규약이 전부다. 회상은 grep이므로 이름이 검색성을
결정한다.

## routing — 문장 단위로 "이 주장의 verifier가 누구인가"

| verifier | home |
|---|---|
| 구현 증거 탐색이 검증한다 (SHALL+Scenario로 무손실 번역 가능) | spec 표면 — `openspec/` scaffold가 있을 때. 없으면 소유 정본 |
| 코드 구조와의 재접지가 검증한다 (형태·topology의 현재) | 설계 정본 |
| 소속 결정의 현존이 생사를 정한다 (이유·의도·배제) | 설계 정본, 그 결정 옆 |
| 동반한 provenance header가 검증을 대체한다 (과거의 측정) | `docs/research/` |
| 없음 | 쓰지 않는다 |

litmus: **spec은 제품이 무엇을 하는가, 정본은 단위가 왜 이 모양인가.** behavior와 이유를
겸한 문장은 분리한다(behavior→spec, 이유→정본, 상호 link). 특정 변경 하나의 사유는 change
proposal로. 쓰기 전 기존 home을 grep해 있으면 그 자리에서 갱신한다. 추적 text는 어디서든 gitignored·
미추적(system temp 포함) 경로를 지시하지 않는다.

## 설계 정본 (living — 제자리 재접지)

소유 단위(repo root / 필요를 입증한 하위 단위 / 자기 불변식을 가진 횡단 domain)당 하나,
고정 이름 — 구조 단위는 `ARCHITECTURE.md`(storefront 의무 단위는 README 겸용), 횡단 domain은 domain 이름 — 이름이 회상 key다. hub는 위성에 link 위임하고 어느 방향도 재서술하지 않는다. 배제 기록은
별도 문서 없이 정본의 section이다. 정본은 코드를 앞설 수 있되 **앞서는 주장은 미구현 표기가
의무다**(구현 상태 범례). 신생 repo의 정본은 첫 구조적 결정과 함께 생성한다 — 빈 scaffold는
부채다. 생성 시 CLAUDE.md에 정본 pointer 1행(진입점)을 함께 둔다.

## 용어

소유 정본의 `## 용어` section, 용어당 home 하나(단위 용어는 단위 정본, 횡단 용어는 root 정본).
형식: `**term** — 1~2문장 정의 + referent`. 입장(모두 충족): 이름만으로 오독된다 / 산문이
아직 정의를 운반하지 않는다 / referent가 이미 일한다. 퇴거(하나면): referent home 소멸 /
산문이 정의를 흡수.

## 조사 기록 (dated — 의미 동결·축적)

`docs/research/<topic>-<yyyy>.md`, 동년 재측정은 `-<yyyy>-<mm>`. header 의무: 작성일·질문·방법
+ 신뢰도 4등급(✅ 검증됨 · 🔶 판단 · ❓ 미검증 · ❌ 반박됨). **자기완결 의무**: gitignored·
미추적 경로를 provenance로 지시하지 않는다 — 산출 session이 죽으면 사슬이 끊긴다. 본문 의미는 동결
— 산출 mission의 재승격만 제자리 개정 가능, 그 외 같은 질문의 새 측정은 새 문서, 구 문서에는
banner `[ARCHIVE YYYY-MM]` + 정본/계승 pointer.
삭제 전이 2종: 질문의 사망(정박한 결정이 정본에서 전부 소멸) / 대체·무참조. 반복 재측정
stream은 dated가 아니라 정본의 위성 living 검증 기록이다.

## 상주 (CLAUDE.md·rules — 가장 비싼 home)

입장 class 둘 — **A 진입점**: grep 회상을 bootstrap하는 최소 지도·정본 pointer·핵심 command.
**B 매 turn 규약**(전부 충족): 매 session 참 / 위반이 회상보다 먼저 온다 / 기계 강제 불가 /
irreducible(정본 재서술 금지). 퇴거(하나면): 국소화 / 이름이 생겨 grep 가능 / 기계화(hook·CI
이관) / 재서술 판명.

## 주석

소비 지점 1곳이면 주석, 2곳 이상이거나 구조를 구속하면 정본(주석은 link만). 측정-사실
주석은 재검증 근거를 문장 안에 담고, 설계-결정 주석은 정본 § pointer 또는 자립.
