---
name: refine-architecture
description: "Long-running code-architecture workflow — cross-examine antipatterns into consensus, then apply the highest-ROI refactors"
argument-hint: "[focus area]"
effort: max
disable-model-invocation: true
---

**MISSION: 최대한의 리소스를 투입해서 코드 아키텍처를 최적화한다.**

이 스킬은 결정론적 멀티 에이전트 워크플로우의 얇은 진입점이다.  
오케스트레이션은 전부 워크플로우 엔진이 수행한다. 너는 부트스트랩하고, 워크플로우를 띄우고, 결과를 보고한다.  
사용자 개입 없이 자율적으로 진행하라.

# 1. Bootstrap

다음을 실행하라. 출력은 워크플로우에 넘길 설정 JSON이다:

```bash
CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR}" uv run --script "${CLAUDE_SKILL_DIR}/bootstrap.py" "$ARGUMENTS"
```

# 2. Launch

부트스트랩 JSON의 `workflowScript`를 `scriptPath`로, **JSON 전체**를 `args`로 넘겨 `Workflow`를 실행하라.  
`args`는 JSON 객체 그대로 전달한다 — 문자열로 감싸지 마라.

`Workflow({ scriptPath: <workflowScript>, args: <부트스트랩 JSON 객체> })`

워크플로우는 백그라운드에서 7단계를 수행한다:  
**Map**(분석 영역 분할) → **Identify**(안티패턴 식별) → **Deliberate**(변호·비판·합의) → **Plan**(계획 수립) → **Review**(계획 검수) → **Refine**(개선·실행순서) → **Apply**(순차 적용·테스트).

실패하거나 중단되면 같은 `scriptPath`에 `resumeFromRunId`를 더해 재실행하라 — 완료된 단계는 캐시에서 즉시 복원된다.

# 3. Report

워크플로우가 반환한 요약(합의된 안티패턴, 적용된 계획, 최종 검수 결과)을 사용자에게 보고하라.  
분석·비평·합의·계획·변경 근거의 전체 감사 추적은 `agoraPath`(임시 디렉토리)에 남는다. 보고에 경로를 포함하라.
