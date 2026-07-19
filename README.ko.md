<p align="center">
  <a href="https://clomia.github.io/claude-automata/"><img src="https://raw.githubusercontent.com/clomia/claude-automata/main/site/assets/banner.png" alt="claude-automata — runs for days, remembers only what's verified" width="840"></a>
</p>

<p align="center"><strong>agent는 끝났다고 <em>생각하는</em> 순간 멈춥니다. 이것은 정말로 끝났을 때 멈춥니다.</strong></p>

<p align="center">
  인간 기억 구조를 사상한 Claude Code 자율 agent 환경.<br>
  advisor가 모든 정지를 감사하고, 검증된 gate 하나가 무엇을 기억할지 정합니다.
</p>

<p align="center"><a href="https://clomia.github.io/claude-automata/"><strong>▶ 기억 회로가 도는 것을 보세요</strong></a></p>

<p align="center">
  <a href="https://pypi.org/project/claude-automata/"><img src="https://img.shields.io/pypi/v/claude-automata?style=flat&color=b25c28" alt="PyPI"></a>
  <a href="https://github.com/clomia/claude-automata/blob/main/LICENSE"><img src="https://img.shields.io/github/license/clomia/claude-automata?style=flat&color=3e6f5e" alt="MIT"></a>
</p>

[English](https://github.com/clomia/claude-automata/blob/main/README.md) | 한국어

---

Claude Code는 끝났다고 믿는 순간 turn을 끝내고, 다음 compaction에서 전부 잊습니다. claude-automata는 그것을 기억이 실제로 작동하는 방식으로 재구성합니다:

| Plugin | 기억 역할 |
|---|---|
| **ploop** | 작업기억 — 며칠짜리 작업의 loop; 모든 정지를 독립 advisor가 감사하며, 더 표면화할 것이 없을 때까지 계속됩니다 |
| **tx** | consolidation — 기억으로 들어가는 유일한 gate: plan, 독립 verify, CI, squash merge |
| **refine** | 재접지 — 오래된 기억을 코드와 재대조하는 수 시간짜리 workflow |
| **version-up-alert** | update 알림 — 뒤처진 plugin이 있으면 session 시작 시 한 줄; 알림만 하고 실행 중인 plugin을 갈아끼우지 않으며, 다른 plugin과 함께 설치됩니다 |

장기기억은 database가 아닙니다. repository의 git 추적 text 그 자체입니다 — 회상은 grep입니다. gate를 통과하지 못한 것은 loop와 함께 죽습니다, 의도적으로.

## Install

[Claude Code](https://claude.com/claude-code)와 [uv](https://docs.astral.sh/uv/getting-started/installation/)가 필요합니다. POSIX(macOS / Linux / WSL). project root에서 한 command:

```
uvx claude-automata init
```

재실행해도 안전합니다(idempotent). 최신 version 강제는 `uvx claude-automata@latest init`.

**init이 실제로 기록하는 설정** — 이 환경은 무인 운용을 전제합니다. commit 전에 diff를 확인하세요:

- `permissions.defaultMode: "bypassPermissions"` — 승인 prompt 없음. agent가 묻지 않고 이 machine에서 shell command를 실행합니다 — 신뢰의 범위는 repo가 아니라 host입니다.
- `model: "opus[1m]"` — model 고정, 1M context
- `alwaysThinkingEnabled: true` · `autoCompactEnabled: true` · `autoMemoryEnabled: false`
- `clomia/claude-automata` marketplace 등록 + plugin 4종 활성화
- 없는 `gh`·Node.js ≥ 20·`repomix`를 사용자 영역에 설치 — sudo 불필요, 있으면 건너뜀, `gh auth login`은 사용자 몫

## Loop 돌리기

```
/ploop:define-mission          # anchor 작성 — interview로 뽑아낸 당신의 의도
/ploop:launch [anchor 내용]    # 새 session에서 loop에 전달
```

loop는 Stop hook을 탑니다: agent가 멈출 때마다 clean context의 독립 advisor가 round를 검사하고 놓친 것을 표면화합니다. loop는 agent가 끝났다고 느낄 때가 아니라 **advisor가 더 말할 것이 없을 때** 끝납니다.

```
agent   › Mission accomplished. Stopping.
hook    › Stop blocked — summoning the advisor.
advisor › Not yet. The mobile layout was never measured. Two claims cite no source.
agent   › …resuming.
        ⟲ six rounds later
advisor › I have no further advice. Ending the turn.
```

*연출된 대화입니다 — 기제는 실제입니다.* anchor는 모든 auto-compaction에서 살아남습니다. 구독 요금제에서도 안전하게 쓸 수 있습니다 — 여기서 '안전'은 동작 기제 이야기지 비용이 들지 않는다는 뜻이 아닙니다: loop는 요금제 quota를 공유하며, 며칠짜리 실행은 quota를 그만큼 소모합니다.

<details>
<summary><strong>일시정지 · 재개 · 관찰</strong></summary>

<br>

- Auto-Compact가 True여야 합니다. 무인 운용에는 `askUserQuestionTimeout` 설정을 권장합니다 — 응답 없는 질문에서 loop가 무한정 기다리는 일이 없습니다.
- `/ploop:off`로 일시정지, `/ploop:on`으로 재개 — `on`은 실수로 누른 ESC·API error·session limit로 멈춘 loop까지 깨우는 범용 wake button입니다 (turn이 돌고 있으면 ESC로 끊은 뒤). 그 밖의 어떤 것도 loop를 멈추지 않습니다.
- **같은 directory의 별도 session**에서 `/ploop:docent`가 loop 기록을 읽어 질문에 답합니다 — loop에는 어떤 영향도 없습니다. 질문은 docent에게, 개입은 loop session에 직접.

</details>

## 변경을 transaction으로

```
/tx:open  [변경 설명]   # base에서 tx-* 분기
...작업...              # tx:plan → tx:apply → tx:verify
/tx:close               # verify·docs gate·CI 후 squash merge
```

transaction은 무결성 경계입니다 — 구현과 기록된 의도가 모두 검증되어야만 닫힙니다. 그동안 base branch는 guard hook들이 지킵니다. 위의 모든 것이 이 gate를 통과합니다.

## 기억을 참인 상태로 유지하기

```
/refine:code [영역] · /refine:docs [영역] · /refine:integrity [영역]
```

쌓인 부채를 없애는 heavyweight multi-agent workflow(한 번에 수 시간, 3–12h): 코드 architecture, 문서의 참, 무결성 경계. 발견은 교차검증 회의에서 합의를 거치고 최고 ROI 계획만 실행됩니다. docs pass는 코드를 수정하지 않습니다 — 결함은 보고됩니다. 영역을 비우면 codebase 전체가 대상, 진행은 `/workflows`에서.

---

<p align="center"><a href="https://clomia.github.io/claude-automata/"><strong>▶ 기억 회로가 도는 것을 보세요</strong></a></p>

MIT License · Anthropic과 무관한 독립 open-source project입니다. 설계상 이 repository의 모든 기여는 Claude Code agent가 작성합니다.
