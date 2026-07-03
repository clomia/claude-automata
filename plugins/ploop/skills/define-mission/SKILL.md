---
name: define-mission
description: Write MISSION.md — a ploop mission defined by its direction and boundary
argument-hint: "[goal]"
disable-model-invocation: false
---

ploop 미션을 `MISSION.md` 파일로 작성합니다.

# 미션의 두 요소

ploop의 advisor는 매 라운드 미션으로부터 미고려 영역들을 도출해 advice로 제공하고, 더 제공할 advice가 없을 때 루프를 끝냅니다. 그래서 미션이 제공할 것은 두 가지뿐입니다.

1. **Direction** — 향해야 하는 목표.
2. **Boundary** — 목표의 끝. 완료 기준, 범위 밖, 제약.

Direction이 모호하면 advice가 목표를 벗어나고, Boundary가 없으면 advisor가 멈출 근거를 찾지 못해 루프가 불필요하게 길어집니다.

# 규칙

- Direction은 달성 여부를 판정할 수 있는 결과로 서술한다.
- **Boundary 판정 테스트**: 임의의 작업 영역을 떠올렸을 때, 미션 텍스트만으로 범위 안/밖을 답할 수 있어야 한다. 답할 수 없으면 Boundary를 보강한다.
- 미션은 self-contained여야 한다. advisor는 이 대화를 보지 못한다 — Direction 이해에 필요한 맥락(경로·용어·현재 상태)을 미션 안에 담는다.
- 강조문·미사여구·'철저히, 빠짐없이' 류 문구를 쓰지 않는다. 철저함은 루프가 만든다.
- 방법을 지시하지 않는다. 방법을 제한해야 한다면 Boundary의 제약으로 쓴다.
- Direction과 Boundary에 기여하지 않는 문장은 지운다.

# 작성하기

1. 인수와 대화 맥락에서 Direction과 Boundary를 도출합니다.
2. 목표의 끝을 스스로 정할 수 없으면 사용자에게 질문합니다.
3. 규칙으로 검증한 뒤 작업 디렉토리의 `MISSION.md`에 작성합니다:

```
# Direction

{목표와 그 이해에 필요한 맥락}

# Boundary

- {완료 기준 — 무엇이 충족되면 끝인가}
- {범위 밖 — 고려하지 않는 것}
- {제약 — 지켜야 하는 것}
```

MISSION.md는 ploop에 자동 연결되지 않습니다. 내용을 `/ploop:launch`에 붙여넣어 시작하라고 사용자에게 안내하세요.

인수: $ARGUMENTS
