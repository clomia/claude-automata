---
name: define-mission
description: Write a mission for ploop
argument-hint: "[mission file path]"
disable-model-invocation: false
---

Mission file path: $ARGUMENTS or MISSION.md

ploop(parallax loop)은 에이전트가 미션을 오랜 시간 수행하게 만듭니다.  
긴 루프 속에서 컨텍스트가 유실되어도 미션은 항상 원문 그대로 보존됩니다.  
따라서 미션을 명확히 정의하고 체계적으로 작성하는게 가장 중요합니다.

사용자를 추궁해서 사용자의 생각과 의도를 수집하세요.
수집된 정보를 종합해서 판단 기준으로 사용 가능한 축을 만드세요.

그리고 Mission file path에 마크다운 형식으로 미션을 작성하세요.
완료 후 작성된 미션을 복사해서 별도 세션에 `/ploop:launch` 하라고 안내하세요.

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
