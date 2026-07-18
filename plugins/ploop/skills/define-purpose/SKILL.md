---
name: define-purpose
description: Write a purpose anchor for ploop — an ongoing direction to advance
argument-hint: "[anchor file save path]"
disable-model-invocation: false
---

Anchor file save path: $ARGUMENTS or ANCHOR.md

ploop(advisor loop)은 에이전트가 오랜 시간 자율적으로 작업하는 루프다.
anchor는 그 루프를 붙들어 매는 기준 파일로, 컨텍스트가 유실되어도 항상 원문 그대로 보존된다.

**Purpose는 지속적으로 나아갈 방향이다.** 요구사항을 만들며 나아가고, 정해진 끝이 없다.
체크리스트는 미리 주어지지 않고 나아가며 만들어진다 — advisor는 방향에 부합하는 다음 영역을 계속 표면화한다.

# Instructions

1. 사용자를 추궁해 생각과 의도를 최대한 수집하라 — 열린 질문으로 시작해 여러 번의 질의응답을 거쳐라.
   - [CRITICAL] 사용자의 주장을 사실로 수용하지 마라. **False assumption이 가장 위험하다.** 사용자의 말은 생각이나 의도로 해석하라.
2. 수집한 정보를 판단 기준으로 쓸 수 있는 축으로 종합하고, Anchor file save path에 마크다운 형식으로 purpose를 작성하라.
3. 사용자가 anchor를 최종 검수하게 하라 — 내용을 모두 출력하기보다 파일을 읽도록 요청하는 편이 효율적이다.
4. 완료 후 anchor 텍스트를 복사해 별도 세션에 `/ploop:launch` 하라고 안내하라.
   - `/ploop:launch`는 [anchor 파일 경로]가 아니라 [anchor 내용 텍스트]로 실행된다. copy & paste 부분을 명확히 안내하라.

# Purpose 규칙

- [IMPORTANT] **허용 범위**와 **나아갈 방향**이 명확히 정의되어야 한다.
  - 방향은 완료 조건이 아니라 **판단 기준**이다. 무엇을 향하고 무엇을 피할지를 서술해서, 에이전트가 스스로 다음 요구사항을 옳게 생성하게 하라.
- 하네스(CLAUDE.md, rules 등)가 제공하는 내용은 중복이니 anchor에 넣지 마라.
- ROI(길이 대비 정보)가 높은 문서를 작성하라 — 중요한 단어만 남기고, 작성 후 더 irreducible하게 줄일 수 있는지 재검토하라.
- 구조는 Background → Purpose → Constraint → Reference 순이다. `# Purpose`(나아갈 방향)와 `# Constraint`(허용 범위)는 필수, `# Background`(방향의 배경)와 `# Reference`(관련 링크 — URL·파일 경로)는 선택이며, 섹션은 자유롭게 추가할 수 있다.
