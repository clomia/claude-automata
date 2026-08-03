# 기억 architecture

**이 문서는 기억 system의 설계 정본이다**: 무엇이 기억되고, 어디에 있고, 어떻게 검증되며,
OpenSpec 의존의 경계와 docs 표면의 규약이 무엇인지. 생태계의 합성 — 세 plugin의 역할과 접면,
횡단 정책 — 은 [ARCHITECTURE.md](ARCHITECTURE.md)가 정본이다.

---

## 기억 model

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
                                                      glossary sections      lexical
                                                      comments, docstrings   in-code constraints
                                                      .claude/skills         procedural
                                      ^                         ^
                                      |                         |
                               refine workflows (via tx): re-ground docs against
                               code, prune stale claims, dedup (maintenance cycle)
```

장기기억의 외연은 refine:docs의 domain 정의와 일치한다 — **git 추적되는, 실행시킬 수 없는 모든
text**. 쉬운 구분으로 **docs + openspec**이고, 엄밀히는 주석·docstring·설정의 설명 text까지다.
기계가 값으로 소비하는 설정 text(settings·CI yml의 값)는 실행 표면이지 기억이 아니다 —
불변식 1의 관할도 기억 표면까지다. openspec은 그중
문법과 validate를 가진 구조화된 부분집합으로, 구조화가 이득인 기억 — 요구사항의 현재 상태와
변경의 역사 — 만 담는다. 나머지 semantic(설계 정본·조사 기록)은 자유 산문인 docs가 담는다.
openspec을 써도 docs는 반드시 생긴다.

장기기억은 두 표면으로 나뉜다. **spec 표면**(구조화)은 **raw openspec**(`init --tools none`
scaffold + pin version CLI, upstream prompt 0) 위에 tx 소유 skill — OpenSpec 채택 경계 section이
확정한다. **docs 표면**(자유 산문)은 docs 표면 규약 section이 확정한다. 표면은 비대칭이다: spec
표면이 도구를 요구하는 이유는 문법·validate·상태기계이고, docs 표면은 회상(grep)·유지보수
(refine:docs)·승격(tx)이 이미 있어 도구가 아니라 규약이 전부다 — 전용 도구 0.

장기기억은 **repo 단위**다. repo를 횡단하는 지식은 그것을 소유한 repo의 장기기억에 속한다.
회상은 grep이다 — capability·파일 이름이 곧 검색 key이므로 이름이 검색성을 결정한다.

### 승격 routing

작업기억의 항목은 아래 표를 따라 **기존 home**으로 승격되거나 폐기된다. 새 bucket을 만들지 않는다 —
자유 성장하는 사실 저장소는 refine이 청소해야 할 부채를 양산한다(refine:docs 원칙: 최소 문서).
모든 승격은 tx를 통과한다(불변식 1).

| 작업기억 항목 | 장기기억 home |
|---|---|
| 제품 behavior 결정 | delta spec → `openspec/specs/` |
| 변경의 의도·설계 | change의 proposal·design (archive에 동결) |
| repo 전반 구조·설계의 현재 상태 | 설계 정본 — 소유 단위당 하나·고정 이름 (§docs 표면 규약) |
| 코드를 구속하는 측정 사실 | 소비 지점 1곳=주석 · 2곳+/구조 구속=설계 정본 (§docs 표면 규약) |
| 외부 세계의 측정 사실 | 조사 문서 (`docs/research/` 류) |
| session마다 참이어야 할 운영 규칙 | CLAUDE.md·rules — 비싼 home, 최소로 |
| 채택된 용어 | 소유 정본의 `## Glossary` — 용어당 home 하나, 횡단 용어는 root 정본 |
| 반복이 입증된 절차 | `.claude/skills` — skill 문서, 이름이 호출 key |
| loop 상태·막다른 길·시행착오 | 폐기 — 망각이 기능이다 |

glossary는 장기기억 소속이다. ubiquitous language는 모든 agent와 미래 기여자가 공유해야
하므로 loop와 함께 죽는 곳에 둘 수 없다 — 작업기억에는 **후보 용어**만 둔다. facts도 같다:
작업기억의 사실은 승격 대기열이고, 대기열의 존재 이유는 승격 아니면 폐기다.

### 불변식

1. **tx가 유일한 응고 gate다.** git 추적 기억으로 들어가는 모든 쓰기는 transaction을
   통과한다 — 장기기억의 모든 항목은 CI green이라는 실측 검증을 통과한 기억이다. 쓰기는
   방향을 가리지 않는다: refine의 재접지·강등·삭제도 같은 문을 지난다. (client 강제는
   tx의 guard hook들이 진다.)
2. **provenance 없는 사실은 승격 금지.** 장기기억에 들어가는 사실은 측정 방법을 동반한다.
   사용자 발화는 사실이 아니라 의도로 기록된다(define-mission의 CRITICAL 규칙을 기억 전체로
   확장) — 의도의 home은 proposal이다.
3. **spec의 권위는 방향이 있다.** 경계는 transaction이 아니라 활동이다 — 재접지도 transaction 안에서
   일어난다(불변식 1). 구현에서는 spec이 구현을 구속하고(close의 verify gate), 재접지에서는
   코드가 ground truth다(refine:docs — 단 코드 결함이 드러나면 보고 대상이지 정합 대상이
   아니다). 이 두 방향이 있어야 spec이 changelog로 전락하지 않는다.
4. **재접지는 주기이지 event가 아니다.** 장기기억은 유지되는 동안 부패한다. refine:docs가
   그 주기다. 코드로도 재측정으로도 검증 불가능해진 주장은 삭제한다. 이 불변식의 "주장"은
   현재 시제의 living 주장이다 — 자기완결 header·banner를 갖춘 dated 문서의 본문은 인용된 과거라
   재접지 대상이 아니고, 검증 대상은 그 형식(header·banner·자기완결)이며 삭제는 전이 2종(§docs
   표면 규약)으로만 일어난다.
5. **응고는 mission 종료에만 걸지 않는다.** loop는 비정상 종료할 수 있다 — purpose loop는
   주기적으로 승격하고, advisor가 미승격 잔량을 영역으로 표면화한다.

---

## OpenSpec 채택 경계 — 3층 소유

| 층 | 내용 | 소유 | 정책 |
|---|---|---|---|
| 기억 (data) | `openspec/**` markdown — 장기기억의 구조화 부분집합 | 이미 각 repo | — |
| engine | CLI: validate·status·instructions·archive… | Fission-AI (MIT) | 채택 · version pin · seam 뒤 |
| 정책 (policy) | skill prompt | tx plugin | 전량 자작 — upstream prompt 설치 금지 |

**근거.**

- **정책 층은 어느 길이든 자작해야 한다.** upstream prompt는 질문을 상시 gate로
  만든다(ploop launch는 질문을 상시 gate로 두지 않는다 — 정면 충돌). 방치된 loop에서 mid-turn
  질문은 어떤 Stop에도 닿지 않는 교착이다. engine을 자작해도 이 prompt 작업은 그대로
  남으므로, engine 자작은 동일한 작업에 engine 구현·유지보수를 더할 뿐이다.
- **engine의 어려운 20%는 validate다** — agent가 반박할 수 없는 결정론적 gate(주장이 아닌
  실측). upstream은 그 edge case(fenced example·nested delta·stale MODIFIED 보호 등)를
  release를 거듭하며 다듬고 있고, 그 성숙을 재구현하는 것은 오배분이다.
- **외부 규약이라는 사실 자체가 drift 방어다.** automata의 plugin은 agent가
  유지보수한다. 기억의 문법까지 agent 소유면 자율성이 높아질수록 agent가 자기 기억의
  형식을 "개선"할 수 있다. 기억 문법은 agent가 조용히 못 바꾸는 외부 고정점이어야 한다 —
  anchor가 loop를 정박시키듯, format이 기억을 정박시킨다.
- **tx의 squash merge와 상호보완이다.** squash는 branch history를 파괴한다 —
  `changes/archive/`가 squash가 지우는 과정 기록(의도·설계·task)의 유일한 생존자다.

**수용한 trade-off.**

- format 채택은 문법 채택이다(SHALL 요구사항·Scenario 구조). 이 구조가 validate와
  verify(요구사항→구현 증거 탐색)를 가능하게 하는 대가다.
- Node.js >= 22 runtime 의존이 추가된다 (uv·gh에 더해).
- upstream은 활발히 재설계 중이다(store·workset·initiatives 진행형) — HEAD를 쫓지 않는다.

### seam 계약

tx의 OpenSpec 의존은 다음이 전부다:

- **파일 format** — pin version 기준으로 동결: `specs/`·`changes/`·`changes/archive/` layout,
  delta 대수(ADDED/MODIFIED/REMOVED/RENAMED), 요구사항 문법.
- **CLI command** — 판정 입력은 `--json`으로, action(init·new·archive)은 exit code로만 소비한다.
  사용 command는 tx skill 본문에 열거된 것이 전부여야 한다. `instructions apply`는 **change가
  미완인 상태로 소비하지 않는다** — 미완 분기의 출력만 upstream skill 참조 문자열을 싣고(pin 실측:
  ready 상태 출력은 청정), 그 문자열은 CLI 소유라 schema fork로도 지워지지 않는다. apply skill의
  gate(artifacts 전부 done 후 소비)가 오염 분기를 차단한다. **schema fork 기각**이 이 실측의
  배제 기록이다: artifact instructions 4종에 개입 유도 0, 유일한 오염 문자열은 gate 순서로
  회피된다.
- **validate의 1차 소비자는 CI다** — 각 repo의 required check로 실행해 tx:close의 CI 대기가
  문서 무결성까지 지키게 한다. agent 측 CLI 표면은 최소로 유지한다.
- **결합은 `npx --yes @fission-ai/openspec@<pin>` 호출이다** — 설치가 아니다. pin의 정본은 tx이고
  tx release와 함께 version된다(global 설치·repo별 package.json 없음). 업그레이드는 release note 검토 +
  skill 표면 재감사를 거친 의도적 tx release다(audit-harness-deps pattern).
- **scaffold는 `openspec init --tools none`이다** — 산출물은 `specs/`·`changes/archive/`·
  `config.yaml`뿐이다(1.7.0 실측, 비대화식). upstream prompt는 어떤 repo에도 배포되지 않는다.
- **fork하지 않는다** — fork는 validate 유지보수를 떠안아 채택의 이유를 소멸시키고, 기억 문법을
  agent의 수정 권한 안으로 들여 외부 고정점을 파괴한다. npm version 불변성으로 pin이 동결을 이미
  보장한다.
- **exit plan** — format은 plain text라 기억은 도구와 독립이다. 소멸 시에는 같은 seam
  뒤에서 사용 command를 재구현하거나 MIT fork한다.

---

## docs 표면 규약 — 자유 산문의 정본

spec 표면과 달리 docs 표면에는 문법·validate·상태기계가 없다 — 규약과 그 운반이 전부이고
전용 도구는 0이다.

### geometry — living/dated는 유지보수 mode다

home은 session마다 지불하는 비용의 사다리를 이룬다: 폐기 < dated 기록 < 사용 지점 주석 < living 정본 < 상주.
위로 갈수록 회상 비용이 0에 가까워지고 유지 비용이 커지므로 입장 시험이 엄격해진다. living은
재접지 대상(수렴하며 권위를 보유), dated는 동결 대상(축적하며 권위를 banner로 양도) — directory도
기억 유형도 아닌 **유지보수 mode**의 이분이며, spec 표면(`specs/` ↔ `changes/archive/`)과
대칭이다. dated 지위는 흡수 시점이 아니라 **탄생 시점**에 파일명·header로 획득하고, banner는 강등
event가 아니라 **권위 양도 선언**이다. 흐름: dated(측정) → living(결정 증류) → banner의 정본
pointer.

| | living (제자리 재접지) | dated (의미 동결·축적) |
|---|---|---|
| auto-load | CLAUDE.md·rules (진입점 + 매 turn 규약) | ∅ — 금지 cell |
| grep 회상 | 설계 정본(hub+위성) · `## Glossary` · constraint 주석 · 위성 검증 기록 | `docs/research/<topic>-<yyyy>.md` |

### routing — 문장 단위로 "이 주장의 verifier가 누구인가"

| verifier | home |
|---|---|
| tx verify가 구현 증거를 탐색한다 (SHALL+Scenario로 무손실 번역 가능) | openspec spec |
| refine:docs가 코드 구조와 재접지한다 (형태·topology의 현재) | 설계 정본 |
| 소속 결정의 현존이 생사를 정한다 (이유·의도·배제) | 설계 정본, 그 결정 옆 |
| 동반한 provenance header가 검증을 대체한다 (과거의 측정) | `docs/research/` |
| 없음 | 쓰지 않는다 |

litmus: **spec은 제품이 무엇을 하는가, 정본은 단위가 왜 이 모양인가.** behavior와 이유를 겸한
문장은 분리한다(behavior→spec, 이유→정본, 상호 link). 특정 변경 하나의 사유는 change
proposal로 — 정본의 결정 기록과 탄생 시 같은 text일 수 있으나 권위가 즉시 분화한다(정본
사본은 living으로 개정·삭제되고 archive 사본은 동결·권위 0 — 중복이 아니라 설계다).
추적 text는 어디서든 gitignored·미추적(system temp 포함) 경로를 지시하지 않는다 — 자기완결은
조사 기록만의 의무가 아니고, CI docs-form-check가 형식 검사한다: living 표면은 전 추적 `.md`
전량, 동결 표면(`changes/archive/`)은 해당 PR로 유입되는 파일만 — 유입 시점에 gate를 지났고
동결 뒤에는 현재 규칙으로 재심판하지 않는다(불변식 4의 "인용된 과거").

### home 규약

**설계 정본** — 소유 단위(repo root / 필요를 입증한 하위 단위 / 자기 불변식을 가진 횡단
domain)당 하나, 고정 이름 — 구조 단위는 `ARCHITECTURE.md`(storefront 의무 단위는 README 겸용),
횡단 domain은 domain 이름 — 이름이 회상 key다. hub는 위성에 link 위임하고 어느 방향도
재서술하지 않는다. 범위: 구조·경계·도구 결정·비용·roadmap·**배제 기록**(별도 ADR 없이 정본의
section) + 구현 상태 범례. 정본은 코드를 앞설 수 있되 **앞서는 주장은 미구현 표기가 의무다** —
무표기 선행 주장은 mismatch다. 신생 repo의 정본은 scaffold하지 않는다 — 첫 구조적 결정과 함께
생성한다(빈 문서는 부채).

**용어** — 소유 정본의 `## Glossary` section, **용어당 home 하나**(단위 용어는 단위 정본, 횡단 용어는
root 정본). 산문이 정의를 이미 운반하면 section을 만들지 않는다. 형식: `**term** — 1~2문장 정의 +
referent`. 용어는 사실이 아니라 규약이다 — 참의 조건이 측정이 아니라 채택이므로 불변식 2가
이렇게 사상된다: provenance = referent의 home, 검증 = 사용 실재 grep. 정의 속 behavior
주장은 금지가 아니라 living 주장이다. 입장(모두 충족): 이름만으로 오독된다 / 산문이 아직
정의를 운반하지 않는다 / referent가 이미 일한다. 퇴거(하나면): referent home 소멸 / 산문이
정의를 흡수. 기각 용어의 재상정 방지는 배제 기록이 맡는다.

**조사 기록** — `docs/research/<topic>-<yyyy>.md`, 동년 재측정은 `-<yyyy>-<mm>`. 파일명 연도가
1차 in-band 시효 신호다(grep이 모든 hit에 경로를 인쇄한다). header는 불변식 2의 산문 구현:
`Date:`·`Question:`·`Method:` 의무 + 신뢰도 4등급(✅ verified · 🔶 judgment · ❓ unverified · ❌ refuted). **자기완결
의무**: gitignored·미추적 경로를 provenance로 지시하면 불변식 2 위반이다 — loop가 죽으면
사슬이 끊긴다. 본문 의미는 동결이고 판정식은 판정자별로 결정 가능하다: 산출 mission만 tx
재승격으로 제자리 개정 가능 / 제3자·후속 agent에게 dated는 항상 동결 — 새 측정은 새 문서
(직렬 계승은 자매 인용 + 구 banner에 계승 표기) / refine의 판정식은 파일명뿐 — 날짜 파일명이면
주장 수정 금지, 허용 동작은 banner 부착·갱신과 삭제 제안. 반복 재측정 stream은 dated가 아니라
정본의 위성 living 검증 기록이다. banner: `[ARCHIVE YYYY-MM]` + 정본/계승 pointer + "재접지 대상
아님 — 질문이 소멸하거나 대체되면 삭제". **삭제 전이 2종**: 질문의 사망(header 질문이 정박한
결정·방향이 정본에서 전부 소멸) / 대체·무참조(같은 질문의 새 기록 승격 + living 유입 참조 0).
그 밖의 축적은 수용한다 — 망각은 기능이되 살아있는 질문의 기록은 기억이다.

**상주(CLAUDE.md·rules)** — 가장 비싼 slot: 모든 session × 모든 turn × 모든 tier가 지불한다. 입장
class 둘 — **A 진입점**: grep 회상을 bootstrap하는 최소 지도·정본 pointer·핵심 command(모르면
어디를 grep할지 모른다). **B 매 turn 규약**(전부 충족): 매 session 참(domain 국소면 하위 harness로) /
위반이 회상보다 먼저 온다(존재를 모르는 규칙은 grep하지 않는다) / 기계 강제 불가(hook·CI로
가능하면 그리로) / irreducible(정본 재서술 금지). 퇴거(하나면): 국소화 → 하위 harness / 이름이
생겨 grep 가능 → 정본 / 기계화 → hook·CI 이관 후 삭제 / 재서술 판명 → 참조 1줄.

**주석** — 소비 지점 1곳이면 주석, 2곳 이상이거나 구조를 구속하면 정본(주석은 link만).
측정-사실 주석은 재검증 근거를 문장 안에 담고, 설계-결정 주석은 정본 § pointer 또는 자립.
쓰기 전 기존 home을 grep해 있으면 그 자리에서 갱신한다. tag system은 도입하지 않는다.

### 승격 경로와 close gate

openspec 생략은 둘뿐이다: **변경이 docs 표면(장기기억 중 openspec 밖의 자유 산문)에 갇힐 때**,
또는 구조·세계관에 영향 없는 trivial한 변경일 때. 구조에 영향을 주는 코드 변경은 behavior
불변(refactor)이라도 propose 소관이다 — 그 의도·설계의 유일한 생존자는 archive다.

close의 docs gate(diff에 장기기억 표면 — 추적 `.md`·`openspec/**` — 이 있으면): header·banner·
provenance 자기완결 / 정본 선행 주장 표기 / 상주 diff의 class 판정 / 첫 구조적 승격이면 설계
정본·상주 진입점 1행 생성(신생 repo의 정본은 scaffold가 아니라 여기서 태어난다) / **상충 scan**
— 순서 불변식: scan은 최신 `origin/<base>` rebase에 **후행**하고 rebase가 재발생하면 재실행한다.
diff 핵심 어휘로 장기기억 표면 전체(추적 text 전부)를 grep해 교차 파일·교차 표면 상충을
해소한다. git-sync-off는 close를 면제하지 않는다 — close는 pause와 무관하게 fetch·rebase를
선행한다. 상충 검출의 3단 분업: 쓰기 시점(기존 home grep) / 병합 시점(post-rebase scan) /
주기(refine:docs).

### 운반 — 규약은 세 층으로 도달해야 작동한다

| 층 | 실리는 곳 | 소비 시점 | 상태 |
|---|---|---|---|
| W (쓰기) | tx open/close 본문 + `references/docs-surface.md` | 승격 순간 — close 시점 load라 compaction에 면역 | 발효 |
| M (유지보수) | refine:docs reference(`docs-surface.md`) + `convention` finding | refine 주기, 전 agent | 발효 |
| R (산물) | banner·파일명 연도·정본 범례·진입점 label | 회상 시점 — fork·부분 읽기에서도 살아남는 유일한 층 | 발효 |
| 기계 backstop | CI docs-form-check(seed) + base-commit 차단 hook | 병합·commit — CI는 repo 동반이라 fork에 도달, hook은 plugin 동반이라 미도달 | 발효 |

정본→운반체는 번역이라 기계 대조가 불가능하다 — 사본을 은폐하지 않고 4중 방어를 둔다:
**동거**(정본과 운반층 원본이 이 repo에 있어 같은 tx로 개정되고, 이 repo의 refine:docs가 주기
대조) / **방향**(배포본 머리에 출처 1행 — 원본 repo의 자기완결 URL, 사본 표류 시 출처 우선.
배포본은 타 repo에서 읽히므로 MEMORY.md를 권위로 노출하지 않는다 — 세계관 결박은 plugin
격리 위반이고, 정본↔운반체 대조는 동거·주기 대조 소관이다) / **version 경계**(배포는 plugin release 단위, release 감사가 정합을 점검) /
**fork 경계**(fork는 W층 단절이며 표류를 스스로 소유한다 — system이 보증하는 것은 R층과 기계
backstop뿐).

외부 고정점 비대칭: spec 문법은 agent가 못 바꾸는 외부 고정점이지만 **docs 규약은 tx 하나로
자기 개정이 가능하다**. 수용 근거: 문법이 아니라 배치·형식 관례라 파급이 결정론 gate에 닿지
않고, 개정은 반드시 이 문서의 diff로 가시화되며, release 감사가 검토 지점이다.

### 수용한 한계

- 산문 의미에 대한 기계 검증력은 0이다 — CI는 형식만 결정론이고, 의미의 gate는 close 판단과
  refine 주기다. 그럴듯하지만 틀린 산문이 응고되면 다음 loop의 오염 입력이 된다.
- seed CI는 코드의 의미도 검증하지 않는다 — validate와 형식 check뿐이다. 코드 의미의 gate는
  verify stage와 대상 repo 자신의 test다.
- 병렬 close의 분 단위 경합 창 — post-rebase scan 이후·병합 이전에 상대가 병합하는 창은
  client측에서 제거 불가다. seed의 ruleset은 checks rule에 up-to-date 강제를 실으므로 **시도가
  성공한 repo에서는 재rebase→재scan이 강제되어 창이 닫힌다**(checks rule은 workflow가 base에
  도달한 뒤부터 결합한다) — 단 tx는 server측을 보증하지 못한다
  (실패는 1행 고지 후 진행), 성공해도 admin token은 gate를 우회·철거할 수 있다. server측이 주는
  것은 불변 보증이 아니라 **우회를 감사 가능하게 만드는 것**이다. `gh pr checks`는 required 지정과 무관하게
  보고된 전 check를 감시하므로 close 경로의 gate는 server 설정 없이도 성립한다 — 기여 주체는
  전부 Claude Code agent라는 설계 전제(ARCHITECTURE) 아래 tx 밖 병합 경로는 고려 대상이
  아니다.
- hook은 local git 경로만 지배한다 — agent가 원격 쓰기 도구(gh api·MCP push 류)나 push
  refspec으로 base에 직접 쓰는 lane은 client가 막지 못한다. server측 보호가 성립한
  repo에서만 닫힌다.
- origin 없는 repo에서는 tx가 적용되지 않는다(guard 침묵 계약) — gate 없는 장기기억 쓰기가
  열린다. 표면화 지점은 첫 승격 시도에서 base 해석이 실패하는 tx:open의 거부다.
- refine 주기에는 소유자가 없다 — 주기적 backstop은 상위 주체(purpose loop)가 돌린다는 운영 가정
  위에 있다.
- 설계가 보증하는 것은 규약의 도달이지 준수가 아니다 — 준수는 LLM 전제이고, dated의 오염은
  소급 복구가 불가능하다.

---

## 검증 대기 — 실측 전까지 가정

- cron 류 외부 ping이 죽은 process의 loop를 부활시키는지 — process 사망은 인간 몫으로
  남는 마지막 예외 class다.
