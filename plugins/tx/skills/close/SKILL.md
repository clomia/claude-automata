---
name: close
description: 트랜잭션을 닫는다 — 무결성을 검증하고, 열린 OpenSpec 변경을 아카이브한 뒤, base 브랜치로 squash merge · 정리한다.
effort: max
---

## 개요

`/tx:close`는 `/tx:open`으로 시작된 트랜잭션을 종결한다. 현재 `tx-*` 브랜치를 base 브랜치에 squash merge까지 수렴시킨다. 전 과정은 idempotent하다.

**tx close는 "현재 구현과 내용이 모두 무결하다"는 선언이다.** 무결하지 않으면 닫지 마라 — 필요한 수정을 트랜잭션 안에서 마친 뒤 진행한다.

base 브랜치는 **레포지토리의 GitHub 기본 브랜치**다. open과 같은 코드로 해석하고, 실패하면 stderr의 지시를 전하고 거부한다:

```bash
BASE=$(uv run --project "${CLAUDE_PLUGIN_ROOT}" base)
```

## 요구사항

`/tx:close`가 도달시켜야 할 최종 상태:

- 이 트랜잭션에 열린 OpenSpec 변경이 있으면, merge 전에 `openspec-archive-change` 스킬로 **아카이브**한다. archive는 delta spec을 main spec에 sync(delta가 있을 때)하고 변경 디렉토리를 `openspec/changes/** → openspec/changes/archive/**`로 옮긴다 — 이 파일 변경들이 트랜잭션에 포함되어야 한다. (`openspec list`로 활성 변경 유무를 확인한다. 없으면 이 단계는 건너뛴다.)
- 트랜잭션의 모든 변경이 base에 **squash merge**되어 base 히스토리에 단일 commit으로 남는다.
- 병합은 최신 `origin/<base>`가 rebase되고 **CI required check를 통과한 뒤에만** 일어난다.
- 병합 후 이 트랜잭션 브랜치는 local·remote 어디에도 남지 않고, 로컬은 최신 base에 동기화된다.
- 작업 트리에 트랜잭션이 남긴 stray 산출물이나 빈 디렉토리가 없다.
  ```bash
  find . -type d -empty -not -path './.git/*' -delete
  ```

## GitFlow prefix 계약 (conventional commits)

| prefix     | 의미 경계                                          |
| ---------- | -------------------------------------------------- |
| `feat`     | 관찰 가능한 behavior가 늘어남                      |
| `fix`      | 기존 behavior의 결함 수정                          |
| `refactor` | behavior 불변, 구조·이름·내부 구현만 변경          |
| `chore`    | 빌드·CI·의존성·설정·훅·툴링 등 repo-wide 인프라     |
| `docs`     | 문서만 변경                                        |

- 병합 직전 브랜치를 `<prefix>/<scope>/<slug>`로 rename한다. `scope`는 변경이 속한 도메인·모듈이다. `chore`·`docs`는 scope를 생략한다.
- squash commit message는 conventional-commit 형식(`<prefix>(<scope>): <요약>`)으로 트랜잭션 전체를 요약한다.

## 규칙

- PR을 열기 전에 트랜잭션의 모든 변경을 commit한다 — archive가 만든 spec 편집·디렉토리 이동을 포함해 working tree에 uncommitted 변경이 남지 않아야 한다.
- rebase conflict는 양쪽 변경의 의도를 심층 분석해 주도적으로 해결하라. 그리고 결과의 무결성을 책임지고 검증하라.
- push 전에 최종 이름으로 rename한다. 이미 `tx-*`로 push된 stale remote가 있으면 삭제하고 다시 push한다.
- PR은 `gh`로 연다. base가 되는 브랜치를 target으로 지정한다.
- CI 종료를 `gh pr checks <PR#> --watch --fail-fast`로 대기하고 exit code로 통과를 판정하라.
- 이미 병합된 트랜잭션을 다시 close하면 (idempotent) 남은 정리만 수행한다.
