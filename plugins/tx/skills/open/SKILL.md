---
name: open
description: Open a transaction — cut a tx-* branch off base, seed the repo, and route the change
argument-hint: "[change description]"
effort: high
---

transaction은 작업 단위가 아니라 **무결성 경계**다.
**`/tx:open`은 "지금부터 전체 상태를 무결하지 않게 만들겠다"는 선언이다.**

# 열린 상태 — 아래가 전부 참이면 transaction은 열린 것이다

- 새 branch `tx-<slug>`가 최신 `origin/<base>`에서 cut되어 checkout되어 있다 — slug는
  의도를 나타내는 짧은 kebab-case:

  ```bash
  "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" open-tx <slug>
  ```

- seed가 완료되어 있다 (idempotent) — 산출물은 이 transaction에 실려 함께 merge된다:

  ```bash
  "${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" seed
  ```

- 변경이 route되어 있다: 구조·세계관에 영향을 주는 변경은 `tx:plan`(Skill 도구) —
  behavior 불변인 refactor도 구조에 닿으면 여기다. 그 밖의 trivial·docs 표면 변경은
  openspec 생략.

command 실패는 stderr가 fix 경로다 — seed 실패만은 openspec 생략 경로로 진행한다.
