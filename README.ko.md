# claude-automata

[English](https://github.com/clomia/claude-automata/blob/main/README.md) | 한국어

**인간 기억 구조를 사상한 Claude Code 자율 agent 환경.** loop는 24시간 주도권을 갖고, 사용자는 event type 중 하나이며, 기억은 검증을 통과한 git 추적 text로만 남습니다. 며칠짜리 무인 작업이 의도를 잃지 않고, 검증되지 않은 변경이 repo를 오염시키지 않게 하기 위한 구조입니다.

**[Landing page](https://clomia.github.io/claude-automata/)** — 기억 system 시각화와 전체 그림을 수 분 안에 볼 수 있습니다. 설계 정본은 [ARCHITECTURE.md](https://github.com/clomia/claude-automata/blob/main/ARCHITECTURE.md)(생태계)와 [MEMORY.md](https://github.com/clomia/claude-automata/blob/main/MEMORY.md)(기억 system)입니다.

| Plugin | 역할 |
|---|---|
| **ploop** | advisor loop — 며칠씩 걸리는 장기 작업의 자율 loop (작업기억) |
| **tx** | Git transaction workflow — 장기기억으로 들어가는 유일한 응고 gate |
| **refine** | repo 부채를 없애는 수 시간짜리 대규모 workflow 모음 (재접지 주기) |
| **version-up-alert** | 새 version 알림 — 모든 plugin의 공통 의존성 |

## Getting Started

**[Claude Code](https://claude.com/claude-code)와 [`uv`](https://docs.astral.sh/uv/getting-started/installation/)가 필요합니다.**
**POSIX 환경(macOS / Linux / WSL)에서 동작합니다.**

project root에서:

```
uvx claude-automata init
```

한 command가 전부를 수렴시킵니다 — settings 전제조건, marketplace·plugin 4종 등록, 외부 CLI 의존성(gh · Node.js ≥ 20 · repomix)의 사용자 영역 설치(sudo 불필요, 이미 있으면 건너뜀). 재실행해도 안전합니다(idempotent). 최신 version을 강제하려면 `uvx claude-automata@latest init`.

**init이 실제로 쓰는 설정** — 이 환경은 무인 운용을 전제하며, init은 `.claude/settings.json`에 다음을 merge-write합니다(무관한 key는 보존). commit 전에 diff를 확인하세요:

- `permissions.defaultMode: "bypassPermissions"` — 승인 prompt 없음. agent가 묻지 않고 파일을 수정하고 command를 실행합니다 — 그 방식을 수용할 repo에 도입하세요.
- `model: "opus[1m]"` — model 고정, 1M context
- `alwaysThinkingEnabled: true` · `autoCompactEnabled: true` · `autoMemoryEnabled: false`
- claude-automata marketplace 등록 + plugin 4종 활성화

`gh` 인증은 자동화하지 않습니다 — 미인증이면 `gh auth login` 안내가 출력됩니다.

## ploop — Advisor Loop

며칠씩 걸리는 장기 작업을 위한 advisor loop입니다.

- 독립된 advisor가 사용자를 대신해 매 round main agent가 놓친 영역을 찾아줍니다.
- main agent는 orchestrator입니다 — 작업을 agent들에 위임하고 지휘합니다.
- 여러 번의 auto compaction에도 맥락을 잃지 않습니다 — anchor가 재주입되고, 전체 맥락은 advisor가 파일로 관리합니다.
- 별도 session을 만들지 않고 정식 subagent 경로만 사용합니다 — 구독 요금제에 안전합니다.

**anchor**는 loop를 붙들어 매는 기준 파일입니다. 두 종류가 있습니다.

- **Mission** (목표) — 요구사항을 받아서 처리하고, 목표를 모두 달성하면 끝납니다. `/ploop:define-mission`으로 작성하세요.
- **Purpose** (목적) — 요구사항을 만들며 계속 나아가고, 정해진 끝이 없습니다. `/ploop:define-purpose`로 작성하세요.

### 사용 방법

> Auto-Compact가 True로 설정되어 있어야 합니다.
> 무인 운용에는 `askUserQuestionTimeout` 설정을 권장합니다 — 응답 없는 질문에서 loop가 영구 대기하지 않습니다.

1. anchor를 작성하세요 — `/ploop:define-mission` 또는 `/ploop:define-purpose`.
2. 새로운 session에서 `/ploop:launch [anchor 내용]`을 실행하세요. loop는 Stop hook을 탑니다 — agent가 멈출 때마다 hook이 정지를 막고 advisor를 소집시킵니다.
3. loop는 advisor가 더 이상 조언할 것이 없다고 판단하면 자동으로 끝나며, agent가 전체 round를 요약합니다.
   잠시 멈추려면 `/ploop:off`, 이어가려면 `/ploop:on` (turn이 돌고 있으면 ESC로 끊은 뒤 실행). `on`은 실수로 누른 ESC·API error·구독 session limit로 멈춘 loop까지 깨우는 범용 wake button입니다 — advisor가 스스로 종료한 경우만 빼고 언제나 재개합니다. 그 밖의 어떤 것도 — 중간 지시, 질문 응답, background 작업 알림 — loop를 멈추지 않습니다.
4. 진행 상황이 궁금하면 **같은 directory의 별도 session**에서 `/ploop:docent`를 실행하세요 — loop의 기록을 읽어 답하는 read-only 해설자로, loop에는 어떤 영향도 주지 않습니다. 질문은 docent에게, 개입(지시·중단)은 loop session에 직접 하세요.

자세한 설계: [plugins/ploop/ARCHITECTURE.md](https://github.com/clomia/claude-automata/blob/main/plugins/ploop/ARCHITECTURE.md)

## refine

repo에 쌓이는 부채를 없애는 대규모 workflow 모음입니다.

세 skill은 같은 방식으로 동작합니다 — 영역을 나눠 병렬 분석하고, 발견을 교차검증 회의로 합의시키고, ROI가 높은 계획만 실행합니다. 한 번의 실행이 수 시간(3–12시간) 걸리는 heavyweight workflow입니다.

- `/refine:code [영역]` — 코드 architecture 최적화. antipattern을 합의로 걸러내고 최고 ROI refactoring만 적용합니다.
- `/refine:docs [영역]` — 문서 architecture 최적화. 실행시킬 수 없는 text의 모든 주장을 코드와 대조해 바로잡습니다. 코드는 수정하지 않습니다 — 코드 결함은 보고합니다.
- `/refine:integrity [영역]` — 무결성 경계 최적화. 경계가 포함하지 못하는 도달 가능한 상태를 **"이걸 error로 정의할 것인가?"** 부터 파고들어 흡수하고, test와 문서로 고정합니다.

영역을 비우면 codebase 전체가 대상입니다. 진행 상황은 `/workflows`에서 확인할 수 있습니다.

## tx — Git Transaction Workflow

변경을 transaction 단위로 관리하는 Git workflow입니다.

transaction은 **무결성 경계**입니다 — open부터 close까지가 하나로 묶이고, 무결성이 검증되어야만 닫힙니다. 그 사이의 base branch는 guard hook들이 지킵니다.

```
/tx:open  [변경 설명]   # base에서 tx-* 분기 + seed + 경로 선택
...작업...              # tx:plan → tx:apply → tx:verify
/tx:close               # verify·archive·docs gate 후 base로 squash merge
```

transaction 정의·guard hook·base branch 해석 등 자세한 내용은 [plugin README](https://github.com/clomia/claude-automata/blob/main/plugins/tx/README.md)를 참고하세요.

## version-up-alert

설치된 claude-automata plugin에 새 version이 배포되면 session 시작 시 한 줄로 알립니다. 알림만 합니다 — 실행 중인 session 밑에서 plugin을 갈아끼우지 않으며, 적용 시점은 사용자가 정합니다. 모든 claude-automata plugin이 의존성으로 함께 설치하므로 따로 설치할 것이 없습니다.

---

MIT License · Anthropic과 무관한 독립 open-source project입니다.
