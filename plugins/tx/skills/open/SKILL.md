---
name: open
description: "Open a transaction: cut a tx-* branch off base, seed the repo, and route the change"
argument-hint: "[change description]"
effort: high
---

transaction(tx:open ~ tx:close)은 작업 단위가 아니라 **무결성 경계**다.
**`tx:open`은 "지금부터 전체 상태를 무결하지 않게 만들겠다"는 선언이다.**

# Lifecycle

`tx:open` → `tx:plan`(변경 기록) → `tx:apply`(구현과 verify) → `tx:archive`(동결) →
`tx:close`(무결 선언, base로 squash merge). 모두 Skill 도구다.
close의 닫힌 상태 gate는 close 시점이 아니라 작업 내내의 규율이다.

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

A failed command's stderr carries the fix; only a failed seed proceeds anyway,
on the openspec-skip route.
