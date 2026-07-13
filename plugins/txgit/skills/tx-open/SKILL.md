---
name: tx-open
description: 트랜잭션을 연다 — base 브랜치에서 tx-* 작업 분기를 만들고, 필요하면 OpenSpec으로 변경을 계획한다.
argument-hint: "[변경 설명]"
effort: high
---

**tx-open은 "지금부터 구현·내용을 무결하지 않은 상태로 만들겠다"는 선언이다.**
트랜잭션은 작업 단위가 아니라 **무결성 경계**다. 여는 순간부터 `/txgit:tx-close`까지가 하나의 트랜잭션으로 묶인다.

# 1. Preflight

base 브랜치를 먼저 확정한다 — 저장소의 기본 통합 브랜치이며, 훅과 동일한 규칙으로 해석한다: `TXGIT_BASE_BRANCH` → `origin/HEAD`의 기본 브랜치 → `main`·`master`·`dev` 중 존재하는 것 → `main`.

```bash
BASE="${TXGIT_BASE_BRANCH:-$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null)}"
BASE="${BASE#origin/}"; BASE="${BASE:-main}"
```

`origin/HEAD`가 로컬에 없어 자동 감지가 안 되면 실제 통합 브랜치(`master`·`dev` 등)를 base로 삼고, 필요하면 `TXGIT_BASE_BRANCH`로 고정한다.

- 현재 브랜치가 `$BASE`가 아니면 거부한다. 트랜잭션은 base에서만 연다.
- working tree가 clean이 아니면 거부하고 정리(commit·stash)를 먼저 요청한다.
- argument(변경 설명)가 없으면 무엇을 하려는지 설명을 요청한다.

# 2. Git Branch 생성

base를 먼저 떠나 트랜잭션 경계를 연다 — 이후의 계획·구현이 base가 아닌 tx 브랜치에 쌓이도록.

- `git fetch origin "$BASE"` 후 최신 `origin/$BASE`에서 `tx-<slug>`로 분기한다.
- `slug`는 의도를 나타내는 짧은 kebab-case다. **scope(도메인·모듈)는 넣지 않는다** — scope는 `/txgit:tx-close`에서 사후 확정한다.
- 이름 충돌은 접미사로 해결한다.
- 같은 의도의 open PR이나 stale `tx-*` 브랜치가 이미 있으면 새로 만들지 말고 그것을 이어간다.

# 3. OpenSpec 경로 선택

트랜잭션 경계 안(tx 브랜치)에서, 변경의 성격에 따라 세 경로 중 하나를 즉시 트리거한다. 트리거는 **Skill 도구로 스킬 이름을 호출**한다 (OpenSpec 공식 스킬이 준비돼 있다고 가정 — 슬래시로는 `/opsx:*`):

- **`openspec-explore`** (`/opsx:explore`) — 경계·책임·요구사항·용어가 흐릿할 때. 코드를 쓰지 않고 먼저 사고해 흐릿함을 해소한다. 정리되면 자연히 propose로 이어진다.
- **`openspec-propose`** (`/opsx:propose`) — 흐릿함은 없으나 구조에 영향을 주는 non-trivial한 변경일 때. 계획 아티팩트(proposal·design·tasks)를 스캐폴딩해 기록으로 남긴다. 구현은 이어지는 `openspec-apply-change`(`/opsx:apply`)가 수행한다.
- **openspec 생략** — 구조·세계관에 영향 없는 trivial한 변경일 때.

경로 선택은 요청의 무결성과 optimality를 검토한 결과여야 한다. 애매하면 explore로 시작하는 편이 안전하다.

OpenSpec CLI가 없거나 `openspec/`가 초기화돼 있지 않으면 (`openspec list` 실패), 이를 알리고 openspec 생략 경로로 진행한다.

# 참고

`/txgit:tx-close` 전에 이 트랜잭션에서 연 OpenSpec 변경을 `openspec-archive-change`(`/opsx:archive`)로 아카이브해야 한다. 그래야 delta spec이 main spec에 sync되고 변경이 트랜잭션에 깔끔하게 포함된다. tx-close가 이를 확인·수행한다.
