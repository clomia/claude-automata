---
name: open
description: "Open a transaction: cut a tx-* branch off base, seed the repo, and route the change"
argument-hint: "[change description]"
effort: high
---

transaction(tx:open ~ tx:close)은 작업 단위가 아니라 **무결성 경계**다.
**`tx:open`은 "지금부터 전체 상태를 무결하지 않게 만들겠다"는 선언이다.**

# Lifecycle

`tx:open` → `tx:plan` → `tx:apply` → `tx:archive` → `tx:close`. 모두 Skill 도구다.

- `tx:plan`: 변경의 intent와 design을 change artifact로 기록한다. route가 openspec을 생략하면
  건너뛴다.
- `tx:apply`: task 순서대로 구현한다. spec delta가 있으면 독립 verify stage를 pass까지 돌린다.
- `tx:archive`: 완료된 change를 동결한다. close의 조건이다.
- `tx:close`: "전체 상태가 무결하다"를 선언한다. transaction 전체가 CI green인 하나의 PR
  squash merge로 base에 안착하고, transaction에서 생겨난 모든 것은 base에 실리거나 소멸한다.
  이 gate는 close 시점이 아니라 작업 내내의 규율이다.

# 열린 상태: 아래가 전부 참이면 transaction은 열린 것이다

- A new branch `tx-<slug>` is cut from the latest `origin/<base>` and checked
  out. The slug is a short kebab-case name for the intent:

  ```bash
  "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" open-tx <slug>
  ```

- The seed has run (idempotent). Its artifacts ride this transaction and merge
  with it:

  ```bash
  "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" seed
  ```

- The change is routed. `tx:plan` takes anything that touches structure or
  worldview; a behavior-preserving refactor that touches structure is still
  `tx:plan`'s. Only two kinds of change skip openspec: one confined to the
  docs surface, and one trivial enough to touch neither.

When a command fails, stderr carries the fix. Only a seed failure proceeds
anyway, on the openspec-skip route.
