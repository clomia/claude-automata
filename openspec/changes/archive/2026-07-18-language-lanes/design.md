## Context

세 max-effort 분석(openspec-usage · language-lanes · vocab-sweep)이 선행했고, 이 문서는 그
합의 판정의 증류다. 근거 실측: 업스트림 스킬 프롬프트 정독(`init --tools claude` 스크래치),
전 한국어 표면 문장 단위 전수 정독, 캐논 어휘 출현 전수 grep.

## Goals / Non-Goals

**Goals:** 언어 레인의 결정 기록화, 잔존 trip 어휘·calque 제거, plan의 태스크 경계 가드.

**Non-Goals:** refine 미션·advice/narration의 영어 전환(감사 표면·loop.log 독자 존재로 기각),
컨텍스트→context 표기 통일(자연 외래어 — trip 아님), 캐논 용어(응고·승격·재접지·정박) 개명.

## Decisions

- **언어는 독자가 정한다.** "영어로 생각하라"류 메타 지시는 지렛대가 아니다 — 입력 언어가
  추론 언어를 정한다. 전환 대상은 정확히 한 레인: main의 런타임 위임 prompt(사람이 읽지 않고,
  worker는 사용자를 대면하지 않으며, 매 루프 생성되는 일회성이라 감사 표면이 아님). 규칙의
  거처는 shipped 표면인 launch rules다 — `.claude/rules/`는 이 레포의 저작 에이전트를 지배할
  뿐 다운스트림 런타임에 도달하지 않는다.
- **빈 `openspec/specs/`는 설계상 정답이다.** 소급 전사는 불변식 3의 changelog 퇴화 +
  provenance 조작이라 기각(배제 기록). 업스트림 스킬 6종 정독 결과 채택 후보 0 — 질문 게이트·
  store 지향·부분 spec-merge 패러다임은 캐논이 이미 반대로 결정한 것들이고, 캐논의 오염
  방화벽(미완 상태 instructions apply 비소비)은 실측 재확인됐다.
- **태스크는 트랜잭션 안에서 완결된다.** merge 이후 행동이 태스크에 실리면 archive 게이트와
  순환 데드락이 되고 발견이 close까지 늦는다 — plan에 authoring-time 가드 1행.
- 어휘 판정: trip 기준은 native 독자의 걸림. 발화(hooks fire)→fire, 축자→verbatim, 거처→home
  (자리(slot)와의 중의성 해소 부수 효과), 잠식→차지, 소거→지움, 드리프트→drift,
  산다-locative→존재한다/있다/남는다. 반면 양도·흡수·동결·표류·표면화·서사는 자연 한국어로
  보존 — 과잉 정화는 그 자체가 churn이다. MEMORY:75 "사용자 발화"는 utterance 의미라 보존.
- 거처 스윕은 mirror 2벌과 MEMORY를 한 커밋에 함께 움직인다(mirror가 "충돌 시 정본이 이긴다"를
  선언하므로 정본 단독 잔존은 즉시 드리프트).

## Risks / Trade-offs

- [위임 prompt 영어화로 loop.log의 위임 구간이 영어 혼입] → narration이 원문 보존하므로
  소유자 감사는 유지되고, recap은 사용자 언어로 재서술된다(하네스 규칙).
- [캐논 어휘 치환의 누락 잔존] → 전수 grep으로 0 확인, 아카이브 산물은 동결이라 제외.
