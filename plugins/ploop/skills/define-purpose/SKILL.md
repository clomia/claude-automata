---
name: define-purpose
description: Write a purpose anchor for ploop — an ongoing direction to advance
argument-hint: "[anchor file save path]"
disable-model-invocation: false
---

Anchor file save path: $ARGUMENTS or ANCHOR.md

ploop(advisor loop)은 에이전트가 오랜 시간 자율적으로 작업하는 루프입니다.  
anchor는 그 루프를 붙들어 매는 기준 파일로, 컨텍스트가 유실되어도 항상 원문 그대로 보존됩니다.  
따라서 anchor를 명확히 정의하고 체계적으로 작성하는게 가장 중요합니다.

**Purpose는 지속적으로 나아갈 방향입니다.** 요구사항을 만들며 나아가고, 정해진 끝이 없습니다.  
체크리스트는 미리 주어지지 않고 나아가며 만들어집니다 — advisor는 방향에 부합하는 다음 영역을 계속 표면화합니다.

사용자를 추궁해서 사용자의 생각과 의도를 수집하세요.  
수집된 정보를 종합해서 판단 기준으로 사용 가능한 축을 만드세요.

그리고 Anchor file save path에 마크다운 형식으로 purpose를 작성하세요.  
완료 후 작성된 anchor 텍스트를 복사해서 별도 세션에 `/ploop:launch` 하라고 안내하세요.

# Purpose 규칙

## Fundamentals

[IMPORTANT] **허용 범위**와 **나아갈 방향**이 명확히 정의되어야 합니다.

허용 범위가 명확하지 않으면 에이전트가 방향을 좇아 안전 반경을 벗어나는 위험한 행동을 할 수 있습니다.  
나아갈 방향이 명확하지 않으면 에이전트가 만들어내는 요구사항이 발산하여 예측 불가능해집니다.

목표와 달리 방향은 완료 조건이 아니라 **판단 기준**입니다. 무엇을 향하고 무엇을 피할지를 서술해서, 에이전트가 스스로 다음 요구사항을 옳게 생성하도록 만드세요.

## 명확하게 서술하기

> 중요한 단어만 남기세요.

단어가 차지하는 길이는 손실이며 단어가 주는 정보는 이득입니다.  
정보이론 관점에서 ROI(길이 대비 정보)가 높은 문서를 작성하세요.

파일을 생성한 후 글 전체에 담긴 정보를 더 irreducible하게 표현할 수 있을지 다시 한번 검토하세요.

## 문서 구조 설계하기

> 섹션은 제시된 4가지 말고도 자유롭게 추가할 수 있습니다.

Section Order: Background → Purpose → Constraint → Reference  
Mandatory Section: `# Purpose`(나아갈 방향), `# Constraint`(허용 범위)  
Optional Section: `# Background`(방향의 배경), `# Reference`(관련 링크들(URL or File Path))

# Instructions

- 사용자의 생각과 의도를 최대한 많이 수집해야 합니다. 열린 질문으로 시작하고 여러번의 질의응답을 거치며 사용자가 원하는 것을 파악하세요.
- 사용자가 anchor 내용을 최종 검수해야 합니다. 내용을 모두 출력하는것보다 사용자에게 파일을 읽도록 요청하는게 효율적입니다.
- [CRITICAL] 사용자의 주장을 사실로 수용하지 마십시오. **False assumption이 가장 위험합니다.** 사용자의 말은 생각이나 의도로 해석하세요.

## Details

- `/ploop:launch`는 `/ploop:launch [anchor 파일 경로]`가 아닌 `/ploop:launch [anchor 내용 텍스트]`로 실행되어야 합니다. 사용자가 오해하지 않도록 anchor 텍스트 copy & paste 부분을 명확히 안내하세요.
- 하네스(CLAUDE.md, rules 등)가 제공하는 내용은 anchor에 추가하지 마세요. 중복입니다.
