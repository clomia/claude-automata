---
name: define-mission
description: Write a mission for ploop
argument-hint: "[mission file save path]"
disable-model-invocation: false
---

Mission file save path: $ARGUMENTS or MISSION.md

ploop(parallax loop)은 에이전트가 미션을 오랜 시간 수행하게 만듭니다.  
긴 루프 속에서 컨텍스트가 유실되어도 미션은 항상 원문 그대로 보존됩니다.  
따라서 미션을 명확히 정의하고 체계적으로 작성하는게 가장 중요합니다.

사용자를 추궁해서 사용자의 생각과 의도를 수집하세요.
수집된 정보를 종합해서 판단 기준으로 사용 가능한 축을 만드세요.

그리고 Mission file save path에 마크다운 형식으로 미션을 작성하세요.
완료 후 작성된 미션 텍스트를 복사해서 별도 세션에 `/ploop:launch` 하라고 안내하세요.

# 미션 규칙

## Fundamentals

[IMPORTANT] **허용 범위**와 **추구할 목적**이 명확히 정의되어야 합니다.

허용 범위가 명확하지 않으면 에이전트가 미션을 위해 안전 반경을 벗어나는 위험한 행동을 할 수 있습니다.
추구할 목적이 명확하지 않으면 에이전트의 행동이 무한히 발산하여 예측 불가능하게 됩니다.

## 명확하게 서술하기

> 중요한 단어만 남기세요.

단어가 차지하는 길이는 손실이며 단어가 주는 정보는 이득입니다.  
정보이론 관점에서 ROI(길이 대비 정보)가 높은 문서를 작성하세요.

파일을 생성한 후 글 전체에 담긴 정보를 더 irreducible한게 표현할 수 있을지 다시 한번 검토하세요.

## 문서 구조 설계하기

> 섹션은 제시된 4가지 말고도 자유롭게 추가할 수 있습니다.

Section Order: Background → Purpose → Constraint → Reference  
Mandatory Section: `# Purpose`(추구할 목적), `# Constraint`(허용 범위)  
Optional Section: `# Background`(목적의 배경), `# Reference`(관련 링크들(URL or File Path))

# Instructions

- 사용자의 생각과 의도를 최대한 많이 수집해야 합니다. 열린 질문으로 시작하고 여러번의 질의응답을 거치며 사용자가 원하는 것을 파악하세요.
- 사용자가 미션 내용을 최종 검수해야 합니다. 내용을 모두 출력하는것보다 사용자에게 파일을 읽도록 요청하는게 효율적입니다.
- [CRITICAL] 사용자의 주장을 사실로 수용하지 마십시오. **False assumption이 가장 위험합니다.** 사용자의 말은 생각이나 의도로 해석하세요.

## Details

- `/ploop:launch`는 `/ploop:launch [미션 파일 경로]`가 아닌 `/ploop:launch [미션 내용 텍스트]`로 실행되어야 합니다. 사용자가 오해하지 않도록 미션 텍스트 copy & paste 부분을 명확히 안내하세요.
- 하네스(CLAUDE.md, rules 등)가 제공하는 내용은 미션에 추가하지 마세요. 중복입니다.
