# 기억 아키텍처

**이 문서는 기억 시스템의 설계 정본이다**: 무엇이 기억되고, 어디에 살고, 어떻게 검증되며,
OpenSpec 의존의 경계와 docs 표면의 규약이 무엇인지. 생태계의 합성 — 세 플러그인의 역할과 접면,
횡단 정책 — 은 [ARCHITECTURE.md](ARCHITECTURE.md)가 정본이다.

---

## 기억 모델

```
WORKING MEMORY                CONSOLIDATION           LONG-TERM MEMORY
(untracked, lossy,            (the only gate)         (git-tracked, non-executable
 dies with the loop)                                   text; the refine:docs domain)
--------------------          ----------------        ---------------------------------
ploop workspace               tx transaction
  anchor: loop intent           change artifacts      openspec/specs/        semantic: requirements
  state: loop-local     --->    (proposal/design/ --> openspec/changes/      episodic
  facts: candidates             tasks/delta)            archive/
  terms: candidates             + CI + verify         docs, ARCHITECTURE     semantic: design, research
  rounds: discard               + squash merge        CLAUDE.md, rules       operating rules
                                                      glossary               lexical
                                                      comments, docstrings   in-code constraints
                                                      .claude/skills         procedural
                                      ^                         ^
                                      |                         |
                               refine workflows: re-ground docs against code,
                               prune stale claims, dedup (maintenance cycle)
```

장기기억의 외연은 refine:docs의 도메인 정의와 일치한다 — **git 추적되는, 실행시킬 수 없는 모든
텍스트**. 쉬운 구분으로 **docs + openspec**이고, 엄밀히는 주석·docstring까지다. openspec은 그중
문법과 validate를 가진 구조화된 부분집합으로, 구조화가 이득인 기억 — 요구사항의 현재 상태와
변경의 역사 — 만 담는다. 나머지 semantic(설계 정본·조사 기록)은 자유 산문인 docs가 담는다.
openspec을 써도 docs는 반드시 생긴다.

장기기억은 두 표면으로 나뉜다. **spec 표면**(구조화)은 **raw openspec**(`init --tools none`
스캐폴드 + 핀 버전 CLI, 업스트림 프롬프트 0) 위에 tx 소유 스킬 — OpenSpec 채택 경계 섹션이
확정한다. **docs 표면**(자유 산문)은 docs 표면 규약 섹션이 확정한다. 표면은 비대칭이다: spec
표면이 도구를 요구하는 이유는 문법·validate·상태기계이고, docs 표면은 회상(grep)·유지보수
(refine:docs)·승격(tx)이 이미 있어 도구가 아니라 규약이 전부다 — 전용 도구 0.

장기기억은 **레포 단위**다. 레포를 횡단하는 지식은 그것을 소유한 레포의 장기기억에 속한다.
회상은 grep이다 — capability·파일 이름이 곧 검색 키이므로 이름이 검색성을 결정한다.

### 승격 라우팅

작업기억의 항목은 아래 표를 따라 **기존 자리**로 승격되거나 폐기된다. 새 버킷을 만들지 않는다 —
자유 성장하는 사실 저장소는 refine이 청소해야 할 부채를 양산한다(refine:docs 원칙: 최소 문서).
모든 승격은 tx를 통과한다(불변식 1).

| 작업기억 항목 | 장기기억 자리 |
|---|---|
| 제품 behavior 결정 | delta spec → `openspec/specs/` |
| 변경의 의도·설계 | change의 proposal·design (archive에 동결) |
| 레포 전반 구조·설계의 현재 상태 | 설계 정본 — 소유 단위당 하나·고정 이름 (§docs 표면 규약) |
| 코드를 구속하는 측정 사실 | 소비 지점 1곳=주석 · 2곳+/구조 구속=설계 정본 (§docs 표면 규약) |
| 외부 세계의 측정 사실 | 조사 문서 (`docs/research/` 류) |
| 세션마다 참이어야 할 운영 규칙 | CLAUDE.md·rules — 비싼 자리, 최소로 |
| 채택된 용어 | 소유 정본의 `## 용어` — 용어당 거처 하나, 횡단 용어는 루트 정본 |
| 루프 상태·막다른 길·시행착오 | 폐기 — 망각이 기능이다 |

glossary는 장기기억 소속이다. ubiquitous language는 모든 에이전트와 미래 기여자가 공유해야
하므로 루프와 함께 죽는 곳에 둘 수 없다 — 작업기억에는 **후보 용어**만 둔다. facts도 같다:
작업기억의 사실은 승격 대기열이고, 대기열의 존재 이유는 승격 아니면 폐기다.

### 불변식

1. **tx가 유일한 응고 관문이다.** git 추적 기억으로 들어가는 모든 쓰기는 transaction을
   통과한다 — 장기기억의 모든 항목은 CI green이라는 실측 검증을 통과한 기억이다. 쓰기는
   방향을 가리지 않는다: refine의 재접지·강등·삭제도 같은 문을 지난다. (branch-protect 훅이
   이 불변식의 절반을 강제한다 — 나머지 절반(신규 파일·Bash 커밋 경로)은 base 브랜치
   git commit 차단 훅이 완성한다. ⬜ 작업 목록 7.)
2. **provenance 없는 사실은 승격 금지.** 장기기억에 들어가는 사실은 측정 방법을 동반한다.
   사용자 발화는 사실이 아니라 의도로 기록된다(define-mission의 CRITICAL 규칙을 기억 전체로
   확장) — 의도의 자리는 proposal이다.
3. **spec의 권위는 방향이 있다.** 트랜잭션 안에서는 spec이 구현을 구속하고(close의 verify
   게이트), 트랜잭션 밖에서는 코드가 ground truth다(refine:docs — 단 코드 결함이 드러나면
   보고 대상이지 정합 대상이 아니다). 이 두 방향이 있어야 spec이 changelog로 전락하지 않는다.
4. **재접지는 주기이지 이벤트가 아니다.** 장기기억은 유지되는 동안 부패한다. refine:docs가
   그 주기다. 코드로도 재측정으로도 검증 불가능해진 주장은 삭제한다. 이 불변식의 "주장"은
   현재 시제의 living 주장이다 — 자기완결 헤더·배너를 갖춘 dated 문서의 본문은 인용된 과거라
   재접지 대상이 아니고, 검증 대상은 그 형식(헤더·배너·자기완결)이며 삭제는 전이 2종(§docs
   표면 규약)으로만 일어난다.
5. **응고는 mission 종료에만 걸지 않는다.** 루프는 비정상 종료할 수 있다 — purpose 루프는
   주기적으로 승격하고, advisor가 미승격 잔량을 영역으로 표면화한다.

---

## OpenSpec 채택 경계 — 3층 소유

| 층 | 내용 | 소유 | 정책 |
|---|---|---|---|
| 기억 (data) | `openspec/**` 마크다운 — 장기기억의 구조화 부분집합 | 이미 각 레포 | — |
| 엔진 (engine) | CLI: validate·status·instructions·archive… | Fission-AI (MIT) | 채택 · 버전 핀 · seam 뒤 |
| 정책 (policy) | 스킬 프롬프트 | tx 플러그인 | 전량 자작 — 업스트림 프롬프트 설치 금지 |

**근거.**

- **정책 층은 어느 길이든 자작해야 한다.** 업스트림 프롬프트는 질문을 상시 게이트로
  만든다(ploop launch는 질문을 비상 채널로만 허용한다 — 정면 충돌). 방치된 루프에서 미드턴
  질문은 어떤 Stop에도 닿지 않는 교착이다. 엔진을 자작해도 이 프롬프트 작업은 그대로
  남으므로, 엔진 자작은 동일한 작업에 엔진 구현·유지보수를 더할 뿐이다.
- **엔진의 어려운 20%는 validate다** — 에이전트가 반박할 수 없는 결정론적 게이트(주장이 아닌
  실측). 업스트림은 그 edge case(fenced example·nested delta·stale MODIFIED 보호 등)를
  릴리스를 거듭하며 다듬고 있고, 그 성숙을 재구현하는 것은 오배분이다.
- **외부 규약이라는 사실 자체가 드리프트 방어다.** automata의 플러그인은 에이전트가
  유지보수한다. 기억의 문법까지 에이전트 소유면 자율성이 높아질수록 에이전트가 자기 기억의
  형식을 "개선"할 수 있다. 기억 문법은 에이전트가 조용히 못 바꾸는 외부 고정점이어야 한다 —
  anchor가 루프를 정박시키듯, 포맷이 기억을 정박시킨다.
- **tx의 squash merge와 상호보완이다.** squash는 브랜치 히스토리를 파괴한다 —
  `changes/archive/`가 squash가 지우는 과정 기록(의도·설계·태스크)의 유일한 생존자다.

**수용한 트레이드오프.**

- 포맷 채택은 문법 채택이다(SHALL 요구사항·Scenario 구조). 이 구조가 validate와
  verify(요구사항→구현 증거 탐색)를 가능하게 하는 대가다.
- Node.js >= 20 런타임 의존이 추가된다 (uv·gh에 더해).
- 업스트림은 활발히 재설계 중이다(store·workset·initiatives 진행형) — HEAD를 쫓지 않는다.

### seam 계약

tx의 OpenSpec 의존은 다음이 전부다:

- **파일 포맷** — 핀 버전 기준으로 동결: `specs/`·`changes/`·`changes/archive/` 레이아웃,
  delta 대수(ADDED/MODIFIED/REMOVED/RENAMED), 요구사항 문법.
- **CLI 커맨드** — 스킬은 JSON 출력만 소비한다. 사용 커맨드는 tx 스킬 본문에 열거된 것이
  전부여야 한다.
- **validate의 1차 소비자는 CI다** — 각 레포의 required check로 실행해 tx:close의 CI 대기가
  문서 무결성까지 지키게 한다. 에이전트 측 CLI 표면은 최소로 유지한다.
- **결합은 `npx --yes @fission-ai/openspec@<pin>` 호출이다** — 설치가 아니다. 핀의 정본은 tx이고
  tx 릴리스와 함께 버전된다(글로벌 설치·레포별 package.json 없음). 업그레이드는 릴리스 노트 검토 +
  스킬 표면 재감사를 거친 의도적 tx 릴리스다(audit-harness-deps 패턴).
- **스캐폴드는 `openspec init --tools none`이다** — 산출물은 `specs/`·`changes/archive/`·
  `config.yaml`뿐이다(1.6.0 실측, 비대화식). 업스트림 프롬프트는 어떤 레포에도 배포되지 않는다.
- **fork하지 않는다** — fork는 validate 유지보수를 떠안아 채택의 이유를 소멸시키고, 기억 문법을
  에이전트의 수정 권한 안으로 들여 외부 고정점을 파괴한다. npm 버전 불변성으로 핀이 동결을 이미
  보장한다.
- **exit plan** — 포맷은 플레인 텍스트라 기억은 도구와 독립이다. `npm pack` 타르볼 보관으로 소멸
  리스크를 헤지하고, 필요 시에만 같은 seam 뒤에서 사용 커맨드를 재구현하거나 MIT 포크한다.

---

## docs 표면 규약 — 자유 산문의 정본

spec 표면과 달리 docs 표면에는 문법·validate·상태기계가 없다 — 규약과 그 운반이 전부이고
전용 도구는 0이다. 필요한 것은 기존 표면의 확장뿐이다(작업 목록 5–8).

> 구현 상태: 규약은 이 문서로 발효된다. 운반과 게이트(작업 목록 5–8)는 ⬜ 미구현 — 그때까지
> 이 문서가 유일한 운반체다.

### 기하 — living/dated는 유지보수 모드다

자리는 세션당 지불 비용의 사다리다: 폐기 < dated 기록 < 사용 지점 주석 < living 정본 < 상주.
위로 갈수록 회상 비용이 0에 가까워지고 유지 비용이 커지므로 입장 시험이 엄격해진다. living은
재접지 대상(수렴하며 권위를 보유), dated는 동결 대상(축적하며 권위를 배너로 양도) — 디렉토리도
기억 유형도 아닌 **유지보수 모드**의 이분이며, spec 표면(`specs/` ↔ `changes/archive/`)과
대칭이다. dated 지위는 흡수 시점이 아니라 **탄생 시점**에 파일명·헤더로 획득하고, 배너는 강등
이벤트가 아니라 **권위 양도 선언**이다. 흐름: dated(측정) → living(결정 증류) → 배너의 정본
포인터.

| | living (제자리 재접지) | dated (의미 동결·축적) |
|---|---|---|
| auto-load | CLAUDE.md·rules (진입점 + 매 턴 규약) | ∅ — 금지 셀 |
| grep 회상 | 설계 정본(허브+위성) · `## 용어` · constraint 주석 · 위성 검증 기록 | `docs/research/<topic>-<yyyy>.md` |

### 라우팅 — 문장 단위로 "이 주장의 검증자가 누구인가"

| 검증자 | 자리 |
|---|---|
| tx verify가 구현 증거를 탐색한다 (SHALL+Scenario로 무손실 번역 가능) | openspec spec |
| refine:docs가 코드 구조와 재접지한다 (형태·토폴로지의 현재) | 설계 정본 |
| 소속 결정의 현존이 생사를 정한다 (이유·의도·배제) | 설계 정본, 그 결정 옆 |
| 동반한 provenance 헤더가 검증을 대체한다 (과거의 측정) | `docs/research/` |
| 없음 | 쓰지 않는다 |

litmus: **spec은 제품이 무엇을 하는가, 정본은 단위가 왜 이 모양인가.** behavior와 이유를 겸한
문장은 분리한다(behavior→spec, 이유→정본, 상호 링크). 특정 변경 하나의 사유는 change
proposal로 — 정본의 결정 기록과 탄생 시 같은 텍스트일 수 있으나 권위가 즉시 분화한다(정본
사본은 living으로 개정·삭제되고 archive 사본은 동결·권위 0 — 중복이 아니라 설계다).

### 자리 규약

**설계 정본** — 소유 단위(레포 루트 / 필요를 입증한 하위 단위 / 자기 불변식을 가진 횡단
도메인)당 하나, 고정 이름 — 이름이 회상 키다. 허브는 위성에 링크 위임하고 어느 방향도
재서술하지 않는다. 범위: 구조·경계·도구 결정·비용·로드맵·**배제 기록**(별도 ADR 없이 정본의
섹션) + 구현 상태 범례. 정본은 코드를 앞설 수 있되 **앞서는 주장은 미구현 표기가 의무다** —
무표기 선행 주장은 mismatch다. 신생 레포의 정본은 스캐폴드하지 않는다 — 첫 구조적 결정과 함께
생성한다(빈 문서는 부채).

**용어** — 소유 정본의 `## 용어` 섹션, **용어당 거처 하나**(단위 용어는 단위 정본, 횡단 용어는
루트 정본). 산문이 정의를 이미 운반하면 섹션을 만들지 않는다. 형식: `**term** — 1~2문장 정의 +
referent`. 용어는 사실이 아니라 규약이다 — 참의 조건이 측정이 아니라 채택이므로 불변식 2는
사상되어 적용된다: provenance = referent의 거처, 검증 = 사용 실재 grep. 정의 속 behavior
주장은 금지가 아니라 living 주장이다. 입장(모두 충족): 이름만으로 오독된다 / 산문이 아직
정의를 운반하지 않는다 / referent가 이미 일한다. 퇴거(하나면): referent 거처 소멸 / 산문이
정의를 흡수. 기각 용어의 재상정 방지는 배제 기록이 맡는다.

**조사 기록** — `docs/research/<topic>-<yyyy>.md`, 동년 재측정은 `-<yyyy>-<mm>`. 파일명 연도가
1차 in-band 시효 신호다(grep이 모든 히트에 경로를 인쇄한다). 헤더는 불변식 2의 산문 구현:
작성일·질문·방법 의무 + 신뢰도 4등급(✅ 검증됨 · 🔶 판단 · ❓ 미검증 · ❌ 반박됨). **자기완결
의무**: gitignored·미추적 경로를 provenance로 지시하면 불변식 2 위반이다 — 루프가 죽으면
사슬이 끊긴다. 본문 의미는 동결이고 판정식은 판정자별로 결정 가능하다: 산출 미션만 tx
재승격으로 제자리 개정 가능 / 제3자·후속 에이전트에게 dated는 항상 동결 — 새 측정은 새 문서
(직렬 계승은 자매 인용 + 구 배너에 계승 표기) / refine의 판정식은 파일명뿐 — 날짜 파일명이면
주장 수정 금지, 허용 동작은 배너 부착·갱신과 삭제 제안. 반복 재측정 스트림은 dated가 아니라
정본의 위성 living 검증 기록이다. 배너: `[ARCHIVE YYYY-MM]` + 정본/계승 포인터 + "재접지 대상
아님 — 질문이 소멸하거나 대체되면 삭제". **삭제 전이 2종**: 질문의 사망(헤더 질문이 정박한
결정·방향이 정본에서 전부 소멸) / 대체·무참조(같은 질문의 새 기록 승격 + living 유입 참조 0).
그 밖의 축적은 수용한다 — 망각은 기능이되 살아있는 질문의 기록은 기억이다.

**상주(CLAUDE.md·rules)** — 가장 비싼 슬롯: 모든 세션 × 모든 턴 × 모든 tier가 지불한다. 입장
클래스 둘 — **A 진입점**: grep 회상을 부트스트랩하는 최소 지도·정본 포인터·핵심 커맨드(모르면
어디를 grep할지 모른다). **B 매 턴 규약**(전부 충족): 매 세션 참(도메인 국소면 하위 하네스로) /
위반이 회상보다 먼저 온다(존재를 모르는 규칙은 grep하지 않는다) / 기계 강제 불가(훅·CI로
가능하면 그리로) / irreducible(정본 재서술 금지). 퇴거(하나면): 국소화 → 하위 하네스 / 이름이
생겨 grep 가능 → 정본 / 기계화 → 훅·CI 이관 후 삭제 / 재서술 판명 → 참조 1줄.

**주석** — 소비 지점 1곳이면 주석, 2곳 이상이거나 구조를 구속하면 정본(주석은 링크만).
측정-사실 주석은 재검증 근거를 문장 안에 담고, 설계-결정 주석은 정본 § 포인터 또는 자립.
쓰기 전 기존 거처를 grep해 있으면 그 자리에서 갱신한다. 태그 시스템은 도입하지 않는다.

### 승격 경로와 close 게이트

openspec 생략은 둘뿐이다: **변경이 docs 표면(장기기억 중 openspec 밖의 자유 산문)에 갇힐 때**,
또는 구조·세계관에 영향 없는 trivial한 변경일 때. 구조에 영향을 주는 코드 변경은 behavior
불변(refactor)이라도 propose 소관이다 — 그 의도·설계는 archive만이 squash를 생존한다.

close의 docs 게이트(diff에 docs 표면 파일이 있으면): 헤더·배너·provenance 자기완결 / 정본 선행
주장 표기 / 상주 diff의 클래스 판정 / **상충 스캔** — 순서 불변식: 스캔은 최신 `origin/<base>`
rebase에 **후행**하고 rebase가 재발생하면 재실행한다. diff 핵심 어휘로 장기기억 표면
전체(추적 텍스트 전부)를 grep해 교차 파일·교차 표면 상충을 해소한다. git-sync-off는 close를
면제하지 않는다 — close는 pause와 무관하게 fetch·rebase를 선행한다. 상충 검출의 3단 분업:
쓰기 시점(기존 거처 grep) / 병합 시점(post-rebase 스캔) / 주기(refine:docs).

### 운반 — 규약은 세 층으로 도달해야 작동한다

| 층 | 실리는 곳 | 소비 시점 | 상태 |
|---|---|---|---|
| W (쓰기) | tx open/close 본문 + `references/docs-surface.md` | 승격 순간 — close 시점 로드라 compaction에 면역 | ⬜ 작업 5 |
| M (유지보수) | refine:docs reference + convention 발견종 | refine 주기, 전 에이전트 | ⬜ 작업 6 |
| R (산물) | 배너·파일명 연도·정본 범례·진입점 라벨 | 회상 시점 — 포크·부분 읽기를 생존하는 유일 층 | 발효 |
| 기계 백스톱 | CI docs-form-check + base-commit 차단 훅 | 병합·커밋 — 포크 레포에도 도달 | ⬜ 작업 7·8 |

정본→운반체는 번역이라 기계 대조가 불가능하다 — 사본을 은폐하지 않고 4중 방어를 둔다:
**동거**(정본과 운반층 원본이 이 레포에 살아 같은 tx로 개정되고, 이 레포의 refine:docs가 주기
대조) / **방향**(배포본 머리에 정본 좌표 1행 — `clomia/claude-automata`의 MEMORY.md — 충돌 시
정본이 이긴다) / **버전 경계**(배포는 플러그인 릴리스 단위, 릴리스 감사가 정합을 점검) /
**fork 경계**(포크는 W층 단절이며 표류를 스스로 소유한다 — 시스템이 보증하는 것은 R층과 기계
백스톱뿐).

외부 고정점 비대칭: spec 문법은 에이전트가 못 바꾸는 외부 고정점이지만 **docs 규약은 tx 하나로
자기 개정이 가능하다**. 수용 근거: 문법이 아니라 배치·형식 관례라 파급이 결정론 게이트에 닿지
않고, 개정은 반드시 이 문서의 diff로 가시화되며, 릴리스 감사가 검토 지점이다.

### 수용한 한계

- 산문 의미에 대한 기계 검증력은 0이다 — CI는 형식만 결정론이고, 의미의 게이트는 close 판단과
  refine 주기다. 그럴듯하지만 틀린 산문이 응고되면 다음 루프의 오염 입력이 된다.
- 병렬 close의 분 단위 경합 창 — post-rebase 스캔 이후·병합 이전에 상대가 병합하는 창은
  클라이언트측에서 제거 불가다. 서버측 "require branches to be up to date"가 있으면 재rebase →
  재스캔이 강제되어 사실상 닫히나, 이는 레포 설정이지 tx의 보증이 아니다.
- refine 주기에는 소유자가 없다 — 주기적 백스톱은 상위 주체(purpose 루프)가 돌린다는 운영 가정
  위에 있다.
- 설계가 보증하는 것은 규약의 도달이지 준수가 아니다 — 준수는 LLM 전제이고, dated의 오염은
  소급 복구가 불가능하다.

---

## 작업 목록

1. **tx의 OpenSpec 스킬 내장화** — tx가 스킬 4종을 싣고 open/close가 업스트림 스킬 대신
   그것을 부른다. 대상 레포에는 `openspec/` 스캐폴드만 남는다.
   - **plan** (propose 대체): 모멘텀 유지. 미지(未知)의 3분기 번역 — 측정 가능하면 측정하고
     기록 / 가역적이면 가정을 채택하고 design에 명기 / 둘 다 아니면 변경을 중단·연기하고
     사유를 기록. 질문 채널은 지정하지 않는다 — 사용 여부는 맥락의 정책(ploop launch 또는
     대화 세션)이 결정한다.
   - **apply** (apply-change 대체): "불명확하면 멈추고 물어라"를 같은 3분기로 교체.
   - **verify** (신설): 구현을 change 아티팩트와 실측 대조(완전성·정확성·정합성), close의
     게이트로 편입. CI가 기계적 무결성이면 verify는 의도 무결성이다.
   - **archive** (archive-change 대체): 확인 다이얼로그 전부 제거 — change는 tx 브랜치에서
     결정되고, 미완료 태스크는 close 차단 사유이며, delta sync는 무조건 수행한다.
2. **결합 절차 교체 + 씨앗** — README의 설치 절차(글로벌 `@latest` + config profile +
   skills-only)를 npx 핀 + `init --tools none`으로 통째로 대체한다. 스캐폴드 부재 시 tx:open이
   직접 초기화하고(비대화식), 씨앗에 CI workflow(required check — docs-form-check 포함)를
   동봉하며, 첫 승격 시 설계 정본(고정 이름·범례)과 상주 진입점 1행을 함께 생성한다.
3. **schema 감사** — `openspec instructions <id> --json` 출력 전수 검사. 사용자 호출 유도가
   있으면 `openspec schema fork spec-driven automata`로 schema.yaml·templates를 소유한다.
   없으면 fork하지 않는다.
4. **ploop 워크스페이스에 응고 계약 내장** — 워크스페이스 설계(state·facts·용어 후보)에 종료
   프로토콜을 포함: 승격 라우팅에 따라 tx로 커밋하고 나머지는 폐기. 불변식 2(provenance)·
   5(주기 승격)를 강제한다. 계약은 라우팅 표의 사본이 아니라 포인터 1행만 나른다 — 규약은
   tx가 운반한다.
5. **tx open/close의 docs 표면 개정** — open: openspec 생략 조건에 "docs 표면에 갇힌 변경"을
   추가한다(trivial 문면 존치·합집합, propose 조건 무개정 — 구조에 영향을 주는 코드 변경은
   behavior 불변이라도 propose 소관). close: docs 게이트 + post-rebase 상충 스캔(순서
   불변식·sync-off 비면제) + `references/docs-surface.md`(W층 배포본, 머리에 정본 좌표 1행).
6. **refine:docs에 표면 규약 reference 주입** — `principlesPath`와 나란히(기성 채널), 발견종
   enum에 convention 추가. principles.md는 불변 — reference는 원칙의 해석이지 개정이 아니다.
7. **base 브랜치 git commit 차단 훅** — 불변식 1의 나머지 절반(신규 파일·Bash 커밋 경로).
8. **CI docs-form-check** — ① research 파일명 `-[0-9]{4}(-[0-9]{2})?.md` 패턴 ② docs 표면
   파일의 gitignored 경로 참조 0 ③ research 헤더의 작성일·방법 행 존재. 2의 씨앗에 동봉한다.
   이름을 form으로 한정한다 — 의미를 축복하지 않는다.

## 검증 대기 — 실측 전까지 가정

- schema fork가 `instructions` 출력의 모든 텍스트를 커버하는지 — 작업 목록 3의 감사가 fork를
  요구하는 경우에만 확인한다 (업스트림 `schemas/spec-driven/`에 schema.yaml과 templates가 함께
  있어 파일 구조상 그래 보인다).
- 완전 무인(headless) 환경에서 AskUserQuestion의 실제 동작 (대기·타임아웃·실패 중 무엇인지).
