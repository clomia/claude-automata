---
name: open
description: Open a transaction — cut a tx-* branch off base, seed the repo, and route the change
argument-hint: "[change description]"
effort: high
---

트랜잭션은 작업 단위가 아니라 **무결성 경계**다.
**`/tx:open`은 "지금부터 구현 또는 내용을 무결하지 않은 상태로 만들겠다"는 선언이다.**

# 열린 상태 — 아래가 전부 참이면 트랜잭션은 열린 것이다

- 새 브랜치 `tx-<slug>`가 최신 `origin/<base>`에서 절단되어 체크아웃되어 있다 — slug는
  의도를 나타내는 짧은 kebab-case:

  ```bash
  uv run --project "${CLAUDE_PLUGIN_ROOT}" open-tx <slug>
  ```

- seed가 완료되어 있다 (멱등) — 산출물은 이 트랜잭션에 실려 함께 병합된다:

  ```bash
  uv run --project "${CLAUDE_PLUGIN_ROOT}" seed
  ```

- 변경이 라우팅되어 있다: 구조·세계관에 영향을 주는 변경은 `tx:plan`(Skill 도구) —
  behavior 불변인 refactor도 구조에 닿으면 여기다. 그 밖의 trivial·docs 표면 변경은
  openspec 생략.

커맨드 실패는 stderr가 수리 경로다 — seed 실패만은 openspec 생략 경로로 진행한다.
