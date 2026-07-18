---
name: open
description: Open a transaction — cut a tx-* branch off base, seed the repo, and route the change
argument-hint: "[change description]"
effort: high
---

트랜잭션은 작업 단위가 아니라 **무결성 경계**다.
**`/tx:open`은 "지금부터 구현·내용을 무결하지 않은 상태로 만들겠다"는 선언이다.**  
`/tx:open`부터 `/tx:close`까지가 하나의 트랜잭션이다.

# 1. preflight

```bash
BASE=$(uv run --project "${CLAUDE_PLUGIN_ROOT}" base)
```

- 현재 브랜치가 `$BASE`이어야 한다.
- working tree가 clean이어야 한다.

# 2. tx branch 생성

- `git fetch origin "$BASE"` 후 최신 `origin/$BASE`에서 `tx-<slug>`로 분기한다.
- `slug`는 의도를 나타내는 짧은 kebab-case다.

# 3. 씨앗

```bash
uv run --project "${CLAUDE_PLUGIN_ROOT}" seed
```

openspec 스캐폴드와 CI workflow가 없으면 심는다 — 멱등이라 있으면 무해하고, 심긴 파일은 이
트랜잭션에 실려 함께 병합된다. 실패하면 stderr를 전하고 openspec 생략 경로로 진행한다.

# 4. 경로 선택

변경의 성격에 따라 두 경로 중 하나를 즉시 트리거한다:

- **`tx:plan`** (Skill 도구) — 구조·세계관에 영향을 주는 변경. behavior 불변인 refactor도
  구조에 영향을 주면 여기다.
- **openspec 생략** — 구조·세계관에 영향 없는 trivial한 변경일 때, 또는 변경이 docs 표면
  (장기기억 중 openspec 밖 자유 산문)에 갇힐 때.

경로 선택은 요청의 무결성과 optimality를 검토한 결과여야 한다.
