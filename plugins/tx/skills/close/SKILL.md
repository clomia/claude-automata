---
name: close
description: Close the transaction — verify, archive, docs gate, then squash merge into base after CI passes
effort: max
---

## 개요

`/tx:close`는 `/tx:open`으로 시작된 트랜잭션을 종결한다. 현재 `tx-*` 브랜치를 base 브랜치에 squash merge까지 수렴시킨다. 전 과정은 idempotent하다.

**tx close는 "현재 구현과 내용이 모두 무결하다"는 선언이다.** 무결하지 않으면 닫지 마라 — 필요한 수정을 트랜잭션 안에서 마친 뒤 진행한다.

base 브랜치는 **레포지토리의 GitHub 기본 브랜치**다. open과 같은 코드로 해석하고, 실패하면 stderr의 지시를 전하고 거부한다:

```bash
BASE=$(uv run --project "${CLAUDE_PLUGIN_ROOT}" base)
```

## 시퀀스

1. **verify** — 활성 change가 있으면(`uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec list --json`) 각각에 대해, 마지막 verify 이후 코드가 변했거나 이력이 불명하면 verify 스테이지를 실행한다 — 불명은 재실행이다:

   ```
   Agent(subagent_type="tx:verify", run_in_background=false, prompt="change-id: <change-id>")
   ```

   change-id 외에는 아무것도 전달하지 않는다. 결함이 보고되면 수리 후 재spawn한다 — pass 전에는 닫지 않는다.

2. **archive** — 활성 change가 있으면 `tx:archive` 스킬(Skill 도구)로 아카이브한다. 미완료 태스크는 close 차단 사유다 — 수리(`tx:apply`) 후 재개한다. archive가 만든 spec 편집·디렉토리 이동은 이 트랜잭션에 포함된다.

3. **commit** — 트랜잭션의 모든 변경을 commit한다. working tree에 uncommitted 변경이 남지 않아야 한다.

4. **rebase** — `git fetch origin "$BASE" && git rebase "origin/$BASE"`. git-sync-off는 close를 면제하지 않는다 — pause와 무관하게 수행한다. conflict는 양쪽 변경의 의도를 심층 분석해 주도적으로 해결하고 결과의 무결성을 검증하라. 해소가 코드를 만졌으면 1의 verify를 재실행한다.

5. **docs 게이트** — diff에 장기기억 표면 파일(추적 `.md` · `openspec/**`)이 있으면 `${CLAUDE_PLUGIN_ROOT}/references/docs-surface.md`를 읽고 판정한다:

   - 새 산문이 규약(자리·형식·헤더·배너·자기완결)에 맞는가. 정본의 선행 주장에 미구현 표기가 있는가. 상주(CLAUDE.md·rules) diff는 입장 클래스를 충족하는가.
   - **상충 스캔** — diff의 핵심 어휘(신·구 이름, 소멸한 개념)로 추적 텍스트 전체를 `git grep`해 교차 파일·교차 표면 상충을 이 트랜잭션에서 해소한다.
   - 이 레포에 설계 정본이 없는데 이 트랜잭션이 구조적 결정을 담으면, 정본(`ARCHITECTURE.md`)과 CLAUDE.md 진입점 1행을 함께 생성한다.
   - 게이트가 파일을 만졌으면 commit한다. **스캔은 rebase에 후행한다 — rebase가 재발생하면 게이트를 재실행한다.**

6. **rename·push·PR** — 브랜치를 `<prefix>/<scope>/<slug>`로 rename하고 push한 뒤, `gh`로 base를 target으로 PR을 연다. 이미 push된 stale remote 브랜치는 그 브랜치의 열린 PR이 없음을 확인한 뒤 삭제하고 다시 push한다.

7. **CI** — `gh pr checks <PR#> --watch --fail-fast`로 대기하고 exit code로 판정한다. 체크 실패와 체크 부재는 구분해 보고하되, 둘 다 병합 차단이다.

8. **merge** — base가 다시 전진했으면 4·5를 반복하고, 4·5가 로컬을 바꿨으면 `git push --force-with-lease` 후 7(CI 대기)을 재수행한 뒤 진행한다: `gh pr merge <PR#> --squash --delete-branch`. squash commit message는 conventional-commit 형식(`<prefix>(<scope>): <요약>`)으로 트랜잭션 전체를 요약한다.

9. **정리** — 로컬을 최신 base로 동기화하고 로컬 트랜잭션 브랜치를 지운다. 작업 트리에 트랜잭션이 남긴 stray 산출물이나 빈 디렉토리가 없어야 한다:

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

`scope`는 변경이 속한 도메인·모듈이다. `chore`·`docs`는 scope를 생략한다.

## 규칙

- 이미 병합된 트랜잭션을 다시 close하면 (idempotent) 남은 정리만 수행한다.
