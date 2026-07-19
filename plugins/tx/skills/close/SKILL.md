---
name: close
description: Close the transaction — verify, archive, docs gate, then squash merge into base after CI passes
effort: max
---

**tx close는 "현재 구현과 내용이 모두 무결하다"는 선언이다.** 무결하지 않으면 닫지 마라 —
필요한 수정을 트랜잭션 안에서 마친 뒤 닫는다.

base는 레포지토리의 GitHub 기본 브랜치다. 해석이 실패하면 stderr의 지시를 전하고 거부한다:

```bash
BASE=$(uv run --project "${CLAUDE_PLUGIN_ROOT}" base)
```

# 닫힌 상태 — 아래가 전부 참이면 트랜잭션은 닫힌 것이다

- 트랜잭션의 change 중 spec delta를 가진 것마다 verify 스테이지의 pass가 있고, 그 pass는
  마지막 코드 변경 이후의 것이다 — delta 없는 change의 관문은 태스크 게이트와 CI다. 검증자에게는 change-id
  외에 아무것도 전달하지 않는다:

  ```
  Agent(subagent_type="tx:verify", prompt="change-id: <change-id>")
  ```

- 활성 change는 `tx:archive` 스킬(Skill 도구)로 아카이브되어 있다. 태스크 부재·미완료는
  close 불가 사유다 — 수리는 `tx:plan`·`tx:apply`.
- 브랜치는 최신 `origin/<base>` 위에 rebase되어 있다. git-sync pause는 이를 면제하지 않는다.
- diff에 장기기억 표면(추적 `.md`·`openspec/**`)이 있으면, 최종 트리에 대해
  `${CLAUDE_PLUGIN_ROOT}/references/docs-surface.md` 규약 판정과 diff 신·구 어휘의 추적
  텍스트 전체 상충 스캔이 수행되었고, 발견은 이 트랜잭션에서 해소되어 있다.
- 트랜잭션 전체가 원격 브랜치 `<prefix>/<scope>/<slug>`의 PR로 base에 squash merge되어
  있다 — CI green이 병합 조건이고 체크 부재도 차단이다(PR 직후의 부재는 스케줄링 지연일 수
  있다). 로컬 브랜치는 병합까지 tx-*로 남는다. squash 메시지는
  conventional-commit(`<prefix>(<scope>): <요약>`)으로 트랜잭션 전체를 요약한다.
- 로컬은 병합된 base에 동기화되어 있고, 트랜잭션 브랜치·stray 산출물·빈 디렉토리가 남아
  있지 않다.

이미 닫힌 트랜잭션의 close는 부족한 상태만 채운다 (idempotent).

## GitFlow prefix 계약 (conventional commits)

| prefix     | 의미 경계                                          |
| ---------- | -------------------------------------------------- |
| `feat`     | 관찰 가능한 behavior가 늘어남                      |
| `fix`      | 기존 behavior의 결함 수정                          |
| `refactor` | behavior 불변, 구조·이름·내부 구현만 변경          |
| `chore`    | 빌드·CI·의존성·설정·훅·툴링 등 repo-wide 인프라     |
| `docs`     | 문서만 변경                                        |

`scope`는 변경이 속한 도메인·모듈이다. `chore`·`docs`는 scope를 생략한다.
