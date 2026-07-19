---
name: define-purpose
description: Write a purpose anchor for ploop — an ongoing direction to advance
argument-hint: "[anchor file save path]"
disable-model-invocation: false
---

Anchor file save path: $ARGUMENTS or ANCHOR.md

ploop(advisor loop)은 에이전트가 오랜 시간 자율적으로 작업하는 루프다.
anchor는 그 루프를 붙들어 매는 기준 파일로, 컨텍스트가 유실되어도 항상 원문 그대로 보존된다.

**Purpose는 완료 조건 없이 방향만 가진다.** 
에이전트는 Purpose로부터 **스스로 요구사항을 만들며 나아가야 한다.**
advisor는 에이전트가 생각하지 못한 요구사항을 찾아준다.

# Instructions

1. 사용자를 추궁해 생각과 의도를 최대한 수집하라 — 열린 질문으로 시작해 여러 번의 질의응답을 거쳐라.
   - [CRITICAL] 사용자의 주장을 사실로 수용하지 마라. **False assumption이 가장 위험하다.** 사용자의 말은 생각이나 의도로 해석하라.
2. 수집한 정보를 판단 기준으로 쓸 수 있는 축으로 종합하고, Anchor file save path에 마크다운 형식으로 purpose를 작성하라.
3. 사용자가 anchor를 최종 검수하게 하라 — 내용을 모두 출력하지 말고 파일 확인을 요청하라.
4. 완료 후 anchor 텍스트를 복사해 별도 세션에 `/ploop:launch [anchor 내용 텍스트]` 하라고 안내하라.
   - `/ploop:launch`는 파일 경로가 아닌 내용을 copy & paste해야 한다.

# Purpose 규칙

- [IMPORTANT] **Acceptable boundaries**와 **나아갈 방향**이 명확히 정의되어야 한다.
   - 에이전트의 역할, **존재 이유**를 정의하라. 
   - 에이전트가 스스로 할 일을 찾고 판단할 수 있는 기준을 서술하라.
- 하네스(CLAUDE.md, rules 등)가 제공하는 내용은 중복이니 anchor에 넣지 마라.
- ROI(분량 대비 정보)가 높은 문서를 작성하라 — 중요한 단어만 남기고, 작성 후 더 irreducible하게 줄일 수 있는지 재검토하라.
- 구조는 Background → Purpose → Constraint → Reference 순이다. `# Purpose`(나아갈 방향)와 `# Constraint`(허용 범위)는 필수, `# Background`(방향의 배경)와 `# Reference`(관련 링크 — URL·파일 경로)는 선택이며, 섹션은 자유롭게 추가할 수 있다.
