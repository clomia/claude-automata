<p align="center">
  <a href="https://claude-automata.clomia.com/"><img src="https://raw.githubusercontent.com/clomia/claude-automata/main/site/assets/banner.png" alt="claude-automata: 24/7 full self-driving for Claude Code" width="840"></a>
</p>

<p align="center"><strong>agent는 끝났다고 생각하는 순간 멈춥니다. claude-automata는 정말로 끝났을 때 멈춥니다.</strong></p>

<p align="center">
  인간 기억 구조를 본뜬 Claude Code agent 환경.<br>
  몇 달짜리 작업을 맡기고 쉬세요. 며칠에 걸쳐 완료합니다.
</p>

<p align="center"><a href="https://claude-automata.clomia.com/"><strong>▶ 기억 회로가 도는 모습을 보세요</strong></a></p>

<p align="center">
  <a href="https://pypi.org/project/claude-automata/"><img src="https://img.shields.io/pypi/v/claude-automata?style=flat&color=f54e00" alt="PyPI"></a>
  <a href="https://github.com/clomia/claude-automata/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/claude-automata?style=flat&color=447e48" alt="License"></a>
</p>

[English](https://github.com/clomia/claude-automata/blob/main/README.md) | 한국어

---

Claude Code는 끝났다고 믿는 순간 turn을 끝내고, 다음 compaction에서 세부를 잊습니다. claude-automata는 Claude Code를 인간 기억이 작동하는 방식으로 재구성합니다:

| Plugin | 기억 역할 |
|---|---|
| **ploop** | 작업기억: 단일 세션이 며칠에 걸쳐 자율 항해합니다. 독립 advisor가 모든 정지를 감사합니다 |
| **tx** | consolidation: 장기기억으로 가는 심사 관문(독립 verify, CI, squash merge) |
| **refine** | 재접지: 기술 부채를 제거하는 대규모 워크플로우 |

장기기억은 database가 아니라 repository의 git 추적 text 그 자체입니다. 회상은 grep입니다. gate를 통과하지 못한 것은 의도적으로 loop와 함께 죽습니다.

## 시작하기

도입할 repository 안에서 Claude Code에 이 한 줄을 붙여넣으세요:

```
https://raw.githubusercontent.com/clomia/claude-automata/refs/heads/main/INSTALL.md 을 읽고 이 레포지토리에 claude-automata를 설치해주세요.
```

agent가 [INSTALL.md](https://github.com/clomia/claude-automata/blob/main/INSTALL.md)를 읽고 repository를 그 문서가 정의한 상태로 수렴시킵니다. init이 settings에 무엇을 기록하는지도 그 문서에 적혀 있습니다. [Claude Code](https://claude.com/claude-code)와 [uv](https://docs.astral.sh/uv/getting-started/installation/)가 필요합니다. POSIX(macOS / Linux / WSL).

## 루프 운용 방법

```
/ploop:define-mission          # agent가 당신을 interview하여 의도를 해석하고 anchor를 작성합니다
/ploop:launch [anchor 내용]    # 새 session에서 loop에 전달
```

agent가 끝났다고 선언하는 순간 hook이 정지를 막고 advisor를 소집합니다. advisor는 전체 스토리에 접근할 수 있는 독립 메타인지입니다. loop는 **advisor가 더 말할 것이 없을 때** 끝납니다.

```
agent   › Mission accomplished. Stopping.
hook    › Stop blocked. Summoning the advisor.
advisor › Not yet. The mobile layout was never measured. Two claims cite no source.
agent   › …resuming.
        ⟲ six rounds later
advisor › I have no further advice. Ending the turn.
```

*연출된 대화입니다. ploop이 제공하는 기능입니다. loop를 종료할 권한은 advisor에게 있습니다.* anchor는 모든 auto-compaction에서 살아남습니다. 구독 요금제에서도 안전하게 쓸 수 있습니다. 여기서 '안전'은 동작 기제 이야기지 비용이 들지 않는다는 뜻이 아닙니다. loop는 요금제 quota를 공유하며, 며칠짜리 실행은 quota를 그만큼 소모합니다.

<details>
<summary><strong>일시정지 · 재개 · 관찰</strong></summary>

<br>

- init이 Auto-Compact를 켭니다; 그대로 두세요. 무인 운용에는 `askUserQuestionTimeout` 설정을 권장합니다. 그러면 응답 없는 질문에서 loop가 무한정 기다리는 일이 없습니다.
- `/ploop:off`는 루프 일시정지. `/ploop:on`은 루프 재개(복원)로, 실수로 누른 ESC·API error·session limit로 멈춘 loop도 깨웁니다 (turn이 돌고 있으면 ESC로 끊은 뒤). 그 밖의 어떤 것도 loop를 멈추지 않습니다.
- `/ploop:docent`는 루프의 진행 상황을 보고합니다. **동일한 디렉토리의 별도 session**에서 실행하세요: 질문은 docent에게, 개입은 loop session에 직접.

</details>

## 변경을 transaction으로

tx는 에이전트가 알아서 사용합니다. 모든 변경은 무결성 경계 뒤에서 검증과 CI를 통과한 하나의 squash merge로 안착하고, 그동안 tx가 base branch 쓰기를 차단합니다. 당신은 진행 중인 작업이 아니라 merge된 결과를 봅니다.

## Repository 정비

```
/refine:code [영역] · /refine:docs [영역] · /refine:integrity [영역]
```

기술 부채를 제거하는 대규모 워크플로우입니다. `/refine:code`는 코드 architecture를 최적화하고, `/refine:docs`는 문서를 코드에 정합하고, `/refine:integrity`는 논리적 무결성을 검증합니다. 레포지토리 전체를 탐색하고 해결하므로 10시간 이상 걸릴 수 있습니다. 영역을 비우면 codebase 전체가 대상, 진행은 `/workflows`에서.

---

<p align="center"><a href="https://claude-automata.clomia.com/"><strong>▶ 기억 회로가 도는 모습을 보세요</strong></a></p>

Apache-2.0 · 재귀적 자기개선: claude-automata는 claude-automata에서 개발됩니다. 이 repository의 모든 기여는 이 환경을 돌리는 Claude Code agent가 작성했습니다.
