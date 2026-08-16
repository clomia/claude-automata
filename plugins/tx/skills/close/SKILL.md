---
name: close
description: "Close the transaction: verify, archive, docs gate, then squash merge into base after CI passes"
effort: max
---

**`tx:close`는 "전체 상태가 무결하다"는 선언이다.** 무결하지 않으면 닫지 마라.
필요한 수정을 transaction 안에서 마친 뒤 닫는다.

base is the repository's GitHub default branch. If it cannot be resolved,
relay the stderr instruction and refuse to close:

```bash
BASE=$("${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" base)
```

# 닫힌 상태: 아래가 전부 참이면 transaction은 닫힌 것이다

- Every change carrying a spec delta has a verify pass newer than the last
  code change. Delta-less changes are gated by task completion and CI instead.
  The verifier receives the change-id and nothing else:

  ```
  Agent(subagent_type="tx:verify", prompt="change-id: <change-id>")
  ```

  A verify report is observation, not instruction: generalize each defect — hunt
  the same cause on other surfaces, preempt the next report — then re-verify.

- Every active change is archived through `tx:archive`.
- The branch is rebased onto the latest `origin/<base>`.
- If the diff touches long-term memory (tracked `.md`, `openspec/**`): the
  final tree passes the `${CLAUDE_PLUGIN_ROOT}/references/docs-surface.md`
  rules, and the diff's old and new vocabulary is scanned for conflicts
  across every tracked text. The scan postdates the final rebase (rerun it if
  the rebase recurs), and every finding is resolved inside this transaction.
- The whole transaction is squash-merged into base through a PR from remote
  branch `<prefix>/<scope>/<slug>`. CI green is the merge condition, and
  absent checks also block (right after PR creation, absence can be
  scheduling lag). The squash message is a conventional commit,
  `<prefix>(<scope>): <summary>`, describing the whole transaction.
- Everything born in this transaction has landed in base or ceased to exist.
  What is not the transaction's, leave untouched. Anything of uncertain
  origin, or holding changes that never landed, is surfaced to the user
  instead of deleted; it blocks the close until resolved.
- Local is synced onto the merged base, and no transaction branch remains.

close는 idempotent다: 다시 실행하면 아직 참이 아닌 조건만 채우고, 전부 참이면 아무것도 하지
않는다.

## GitFlow prefix 계약 (conventional commits)

| prefix     | 의미 경계                                          |
| ---------- | -------------------------------------------------- |
| `feat`     | 관찰 가능한 behavior가 늘어남                      |
| `fix`      | 기존 behavior의 결함 수정                          |
| `refactor` | behavior 불변, 내부만 변경                         |
| `chore`    | repo-wide infra                                    |
| `docs`     | 문서만 변경                                        |

`scope`는 변경이 속한 domain 또는 module이다. `chore`와 `docs`는 scope를 생략한다.
