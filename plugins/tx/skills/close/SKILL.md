---
name: close
description: Close the transaction — verify, archive, docs gate, then squash merge into base after CI passes
effort: max
---

**tx close는 "상태가 모두 무결하다"는 선언이다.** 무결하지 않으면 닫지 마라 —
필요한 수정을 transaction 안에서 마친 뒤 닫는다.

base는 repository의 GitHub default branch다. 해석이 실패하면 stderr의 지시를 전하고 거부한다:

```bash
BASE=$("${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" base)
```

# 닫힌 상태 — 아래가 전부 참이면 transaction은 닫힌 것이다

- transaction의 change 중 spec delta를 가진 것마다 verify stage의 pass가 있고, 그 pass는
  마지막 코드 변경 이후의 것이다 — delta 없는 change의 gate는 task gate와 CI다. verifier에게는 change-id
  외에 아무것도 전달하지 않는다:

  ```
  Agent(subagent_type="tx:verify", prompt="change-id: <change-id>")
  ```

- 활성 change는 `tx:archive`(Skill 도구)로 archive되어 있다. task 부재·미완료는
  close 불가 사유다 — fix는 `tx:plan`·`tx:apply`.
- branch는 최신 `origin/<base>` 위에 rebase되어 있다. git-sync pause는 이를 면제하지 않는다.
- diff에 장기기억 표면(추적 `.md`·`openspec/**`)이 있으면, 최종 tree에 대해
  `${CLAUDE_PLUGIN_ROOT}/references/docs-surface.md` 규약 판정과 diff 신·구 어휘의 추적
  text 전체 상충 scan이 수행되었고, 발견은 이 transaction에서 해소되어 있다.
- transaction 전체가 remote branch `<prefix>/<scope>/<slug>`의 PR로 base에 squash merge되어
  있다 — CI green이 merge 조건이고 check 부재도 차단이다(PR 직후의 부재는 scheduling 지연일 수
  있다). local branch는 merge까지 tx-*로 남는다. squash message는
  conventional-commit(`<prefix>(<scope>): <요약>`)으로 transaction 전체를 요약한다.
- transaction이 존재시킨 것은 base에 실렸거나 소멸했다 — 남아 있으면 잔여다. transaction
  밖의 것은 건드리지 마라. 출처가 불확실하거나 merge에 실리지 않은 변경을 품었으면 삭제도
  무결성 위반이다 — 사용자에게 표면화하고, 해소 전에는 닫지 마라.
- local은 merge된 base에 동기화되어 있고, transaction branch가 남아 있지 않다.

이미 닫힌 transaction의 close는 부족한 상태만 채운다 (idempotent).

## GitFlow prefix 계약 (conventional commits)

| prefix     | 의미 경계                                          |
| ---------- | -------------------------------------------------- |
| `feat`     | 관찰 가능한 behavior가 늘어남                      |
| `fix`      | 기존 behavior의 결함 수정                          |
| `refactor` | behavior 불변, 구조·이름·내부 구현만 변경          |
| `chore`    | build·CI·dependency·config·hook·tooling 등 repo-wide infra |
| `docs`     | 문서만 변경                                        |

`scope`는 변경이 속한 domain·module이다. `chore`·`docs`는 scope를 생략한다.
