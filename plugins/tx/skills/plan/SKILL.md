---
name: plan
description: Plan the change as OpenSpec artifacts — proposal, delta specs, design, tasks
argument-hint: "[change intent]"
effort: max
---

변경의 의도·설계를 change 아티팩트로 기록한다. squash merge는 브랜치 히스토리를 지운다 —
이 아티팩트의 archive만이 그 과정 기록을 보존한다.

# 절차

1. change-id를 정한다 — 의도를 나타내는 kebab-case. 보통 tx 브랜치의 slug와 같다.

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec new change <change-id>
   ```

2. 아티팩트를 의존 순서(proposal → specs·design → tasks)로 작성한다. 각 아티팩트마다
   지시·형식·템플릿을 엔진에서 받는다 — 형식의 정본은 엔진이다:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec instructions <artifact> --change <change-id> --json
   ```

   design은 그 지시가 명시한 포함 조건에 해당할 때만 작성한다. 태스크는 이 트랜잭션 안에서
   완결된다 — merge 이후의 행동(배포·운영 검증)은 태스크가 아니라 후속 change다.

3. 검증한다:

   ```bash
   uv run --project "${CLAUDE_PLUGIN_ROOT}" openspec validate <change-id> --strict --no-interactive --json
   ```

   delta 없는 change(도구·인프라·문서 변경)에서는 validate가 클래스 전체로 `no deltas`
   ERROR를 낸다 — 이 ERROR는 수리 대상이 아니고, 그 클래스의 관문은 태스크 완료와
   archive의 `--skip-specs`, 사후 CI다. 그 외의 지적은 전부 green까지 수정한다.

4. 즉시 `tx:apply`로 이어간다 — 계획은 구현의 시작이지 정지점이 아니다.

# 미지의 번역

계획 중 만나는 모든 미지는 셋 중 하나로 번역한다:

- **측정 가능하면** — 측정하고 결과를 기록한다.
- **가역적이면** — 가정을 채택하고 design에 명기한다.
- **둘 다 아니면** — 변경을 중단·연기하고 사유를 proposal에 기록한다.
