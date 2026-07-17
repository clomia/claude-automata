---
name: open
description: open transection
argument-hint: "[변경 설명]"
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

---

- **`/openspec-explore`** — 경계·책임·요구사항·용어가 흐릿할 때. 코드를 쓰지 않고 먼저 사고해 흐릿함을 해소한다. 정리되면 자연히 propose로 이어진다.

트랜잭션 경계 안(tx 브랜치)에서, 변경의 성격에 따라 세 경로 중 하나를 즉시 트리거한다. 트리거는 **Skill 도구로 OpenSpec 공식 스킬을 호출**한다:

- **`openspec-explore`** — 경계·책임·요구사항·용어가 흐릿할 때. 코드를 쓰지 않고 먼저 사고해 흐릿함을 해소한다. 정리되면 자연히 propose로 이어진다.
- **`openspec-propose`** — 흐릿함은 없으나 구조에 영향을 주는 non-trivial한 변경일 때. 계획 아티팩트(proposal·design·tasks)를 스캐폴딩해 기록으로 남긴다. 구현은 이어지는 `openspec-apply-change`가 수행한다.
- **openspec 생략** — 구조·세계관에 영향 없는 trivial한 변경일 때.

경로 선택은 요청의 무결성과 optimality를 검토한 결과여야 한다. 애매하면 explore로 시작하는 편이 안전하다.

OpenSpec CLI가 없거나 `openspec/`가 초기화돼 있지 않으면 (`openspec list` 실패), 이를 알리고 openspec 생략 경로로 진행한다.
