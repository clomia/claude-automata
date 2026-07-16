# 기억 아키텍처

claude-automata의 세 플러그인은 하나의 기억 시스템을 이룬다 — **ploop이 작업기억**(루프 스코프,
git 미추적, advisor는 메타인지), **tx가 응고 관문**(작업기억 → 장기기억의 유일한 문), **refine이
재접지**(장기기억을 실측과 재대조). 이 문서는 장기기억의 설계 정본이다: 무엇이 기억되고, 어디에
살고, 어떻게 검증되며, OpenSpec 의존의 경계가 어디인지.

---

## 기억 모델

```
WORKING MEMORY                 CONSOLIDATION            LONG-TERM MEMORY
(untracked, lossy,             (the only gate)          (git-tracked, verified,
 dies with the loop)                                     shared across agents/time)
--------------------           ----------------         --------------------------
ploop workspace                tx transaction
  anchor: loop intent            change artifacts       openspec/specs/     semantic
  state: loop-local      --->    (proposal/design/ ---> openspec/changes/   episodic
  facts: candidates              tasks/delta)             archive/
  terms: candidates              + CI + verify           docs, CLAUDE.md    operational
  rounds: discard                + squash merge          glossary           lexical
                                                         .claude/skills     procedural
                                       ^                          ^
                                       |                          |
                                refine workflows: re-ground docs against code,
                                prune stale claims, dedup (maintenance cycle)
```

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
| 코드를 구속하는 측정 사실 | 사용 지점의 constraint 주석 또는 아키텍처 문서 |
| 외부 세계의 측정 사실 | 조사 문서 (`docs/research/` 류) |
| 세션마다 참이어야 할 운영 규칙 | CLAUDE.md·rules — 비싼 자리, 최소로 |
| 채택된 용어 | 레포당 하나의 glossary |
| 루프 상태·막다른 길·시행착오 | 폐기 — 망각이 기능이다 |

glossary는 장기기억 소속이다. ubiquitous language는 모든 에이전트와 미래 기여자가 공유해야
하므로 루프와 함께 죽는 곳에 둘 수 없다 — 작업기억에는 **후보 용어**만 둔다. facts도 같다:
작업기억의 사실은 승격 대기열이고, 대기열의 존재 이유는 승격 아니면 폐기다.

### 불변식

1. **tx가 유일한 응고 관문이다.** git 추적 기억으로 들어가는 모든 쓰기는 transaction을
   통과한다 — 장기기억의 모든 항목은 CI green이라는 실측 검증을 통과한 기억이다.
   (branch-protect 훅이 이 불변식의 절반을 이미 강제한다.)
2. **provenance 없는 사실은 승격 금지.** 장기기억에 들어가는 사실은 측정 방법을 동반한다.
   사용자 발화는 사실이 아니라 의도로 기록된다(define-mission의 CRITICAL 규칙을 기억 전체로
   확장) — 의도의 자리는 proposal이다.
3. **spec의 권위는 방향이 있다.** 트랜잭션 안에서는 spec이 구현을 구속하고(close의 verify
   게이트), 트랜잭션 밖에서는 코드가 ground truth다(refine:docs — 단 코드 결함이 드러나면
   보고 대상이지 정합 대상이 아니다). 이 두 방향이 있어야 spec이 changelog로 전락하지 않는다.
4. **재접지는 주기이지 이벤트가 아니다.** 장기기억은 유지되는 동안 부패한다. refine:docs가
   그 주기다. 코드로도 재측정으로도 검증 불가능해진 주장은 삭제한다.
5. **응고는 mission 종료에만 걸지 않는다.** 루프는 비정상 종료할 수 있다 — purpose 루프는
   주기적으로 승격하고, advisor가 미승격 잔량을 영역으로 표면화한다.

---

## OpenSpec 채택 경계 — 3층 소유

| 층 | 내용 | 소유 | 정책 |
|---|---|---|---|
| 기억 (data) | `openspec/**` 마크다운 | 이미 각 레포 | — |
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
- **설치는 핀 버전이다** (`@latest` 금지). 업그레이드는 릴리스 노트 검토 + 스킬 표면
  재감사를 거친 의도적 행위다(audit-harness-deps 패턴).
- **exit plan** — 포맷은 플레인 텍스트라 기억은 도구와 독립이다. 필요 시 같은 seam 뒤에서
  사용 커맨드만 재구현하거나 MIT 포크한다.

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
2. **설치 절차 정리** — README에서 `@latest` → 핀 버전, "skills-only 설치" 요구 삭제.
3. **schema 감사** — `openspec instructions <id> --json` 출력 전수 검사. 사용자 호출 유도가
   있으면 `openspec schema fork spec-driven automata`로 schema.yaml·templates를 소유한다.
   없으면 fork하지 않는다.
4. **ploop 워크스페이스에 응고 계약 내장** — 워크스페이스 설계(state·facts·용어 후보)에 종료
   프로토콜을 포함: 승격 라우팅에 따라 tx로 커밋하고 나머지는 폐기. 불변식 2(provenance)·
   5(주기 승격)를 강제한다.
5. **ploop×tx Stop 훅 동거를 계약으로 문서화** — git-sync가 `stop_hook_active`에서 조기
   반환해 ploop 라운드 체인에 rebase nudge가 끼어들지 않는 현행 동작은 옳지만 창발적이다.
   tx가 루프의 응고 관문이 되는 순간 이 접면은 심장부다 — 의도된 계약으로 명문화한다.

## 검증 대기 — 실측 전까지 가정

- `openspec init`이 프롬프트 산출물 0개로 스캐폴드만 만들 수 있는지 (profile에 무배포 옵션이
  있는지, 없다면 생성-후-삭제 또는 update 미실행으로 충분한지).
- schema fork가 `instructions` 출력의 모든 텍스트를 커버하는지 (업스트림
  `schemas/spec-driven/`에 schema.yaml과 templates가 함께 있어 파일 구조상 그래 보이나,
  fork 산출물로 확인 필요).
- 완전 무인(headless) 환경에서 AskUserQuestion의 실제 동작 (대기·타임아웃·실패 중 무엇인지).
