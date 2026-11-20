# ploop-own-end — design

## Context

See proposal.md — Why; 요구는 specs. 0.57.3의 hook이 anchor에서 읽는 것은 frontmatter `deadline:` 하나다
(결정 20). armed 정지를 되돌리는 길은 standing directive 하나이고(결정 2), launch skill 본문의 `<notice>`는
"loop는 advisor의 판정으로만 끝난다"고 말한다. 제약: key 없는 anchor — 소유자의 mission — 의 Stop·gate·
heartbeat·guard 출력과 state 파일은 byte 그대로여야 한다.

## Goals / Non-Goals

**Goals:** 제 끝을 선언한 anchor의 loop에서 narrator·advisor 실행이 0이다 — hold의 문구가 아니라 코드의
사실로. 멈춤 방지 장치는 하나도 잃지 않는다.

**Non-Goals:** advisor loop의 비용(첫 directive의 narrator가 launch 이후 전부를 읽는다 — 결정 4·23의 몫).
hold의 계측(읽을 자가 먼저다). define-mission의 제안.

## Decisions

1. **선언은 frontmatter key다 — `deadline:`과 같은 block, 같은 reader.** key는 anchor의 사실이라 launch·
   정지·재정박·gate가 같은 원문에서 읽는다. 값은 `own` 하나다: run(`done(run)` 뒤 daemon이 session을 접음)과
   purpose(`/ploop:off`만이 끝)의 기계는 같고, 다른 것은 끝이 무엇인가뿐이며 그것은 anchor가 말한다.
   기각: 둘째 command(`/ploop:hold`) — 그것을 모르는 구버전 plugin에서 launch가 실패한다; key는 구버전에서
   오늘의 loop로 퇴행할 뿐이다. 기각: launch 인자 flag — anchor 밖의 사실이라 재정박이 잃는다. 기각: 두 값
   (`own`·`never`) — 셋째 줄 한 줄의 차이를 위해 기계에 분기를 둔다.
2. **종류는 쓰일 때마다 `anchor.md`에서 읽는다 — 새 파일·marker가 없다.** launch만 그 파일을 쓰고 다시
   쓰지 않으므로 main이 도중에 종류를 바꿀 수 없다.
3. **hold는 standing directive에서 narrator·advisor에 속한 것을 걷어낸 나머지다** — 새 개념이 없다.
   - 자기감사 두 줄은 directive step 2와 한 상수를 공유해 표류하지 않는다(directive의 byte는 그대로다).
   - 셋째 줄 `Nothing remains -> do what your anchor says comes next.`는 끝을 말하지 않는다: 이 loop에서
     어떤 정지도 끝이 아니므로, "end"라는 낱말은 hold의 교착을 부르고 purpose의 agent를 멈춤으로 민다.
   - candidates 주소 줄은 남는다 — 결정 21의 매 정지 재안내다. own-end loop에는 advisor의 잔량 표면화도
     종료 notice의 drain도 없어(MEMORY 불변식 5), 이 줄이 남는 유일한 기계의 상기다.
   - deadline은 header로만 싣는다 — 조용한 무장 해제는 거짓 안심이고(결정 20), 만료를 집행할 advisor가
     없어 분기는 닫히지 않는다.
4. **정지는 armed marker·`background_tasks`·anchor frontmatter의 순수 함수다.** hold 분기는 background
   gate 바로 뒤, in-flight guard·ledger 앞에 선다 — slice·ledger·token·삭제가 없다. bare 정지 규칙(결정
   14·24)은 두지 않는다: 그 규칙은 main이 부르지 않을 권위로 교착을 끝내는데 여기엔 그 권위가 없고, 그
   종료는 session이 막힌 바로 그때 heartbeat를 무장 해제한다. 침묵하는 main의 상한은 harness의 연속
   continuation cap(8, tool 호출마다 reset — 공식 hooks 문서)이고, 그 뒤의 잠은 heartbeat가 깨운다(결정 19).
5. **gate는 narrator도 거부한다.** advisor는 token이 없어 이미 거부되지만 그 사유는 오지 않을 round
   directive를 말하고, narrator는 통과한다. agent listing은 모든 session에서 advisor를 종결 권위로 소개하므로
   (`agents/advisor.md` description) session이 시도할 수 있다 — 두 호출의 거부가 하나의 사유를 든다.
6. **loop notice는 skill 본문을 떠난다.** 본문은 정적 text라 anchor에 따라 갈릴 수 없고, 그 첫 문장은
   own-end loop에서 거짓이다. 기각: 본문에 두고 own-end에서 교정 — 모순이 매 session의 context에 남는다.
   기각: 조건부 문구("anchor가 끝을 선언하지 않으면") — 모든 mission에게 자기 것이 아닌 출구를 알린다.
   기각: skill 본문의 shell 전처리로 종류를 계산 — anchor text가 shell을 거치고, hook과 전처리의 순서라는
   비공식 의존을 심는다. launch가 같은 turn에 말해야 할 사실은 기계가 배달한다(결정 21) — loop의 종류가 그런
   사실이다. 재정박이 launch의 배달을 되싣으므로 notice도 anchor 뒤에 싣는다: 종전에 notice를 compaction
   너머로 나르던 것은 skill 본문 re-attach였다. key 없는 anchor의 notice는 종전 본문의 번역이다 — hook이
   조립하는 발신 message는 영어다(root 언어 정책).
7. **`end:`의 다른 값은 launch를 차단한다** — 빈 anchor와 같은 차단. 읽지 못하는 선언이 다른 종류를 며칠
   arm해서는 안 된다.
8. **define-purpose가 key를 쓴다 — 결정 22의 미결에 대한 답이다.** 22는 purpose anchor를 completion
   instruction 밖에 두고 그 cadence 설계를 선행 과제로 남겼다. purpose에는 인증할 완수가 없으니 cadence는
   hold다. anchor는 제 끝을 스스로 말한다(`/ploop:off` 외에는 끝나지 않고, 남은 일이 없으면 Purpose에서 다음
   요구사항을 도출한다) — hold의 셋째 줄이 가리키는 곳이다. define-mission은 쓰지 않는다.
9. **바꾸지 않는 것.** off·on·launch 문구와 description의 "advisor loop"(제품 이름 — 바꾸면 key 없는
   anchor의 byte가 더 움직인다). `/ploop:on`의 ledger 정규화(own-end loop에도 `loop.json`을 쓰지만 정지가
   읽지 않는다 — 불변식 하나를 위해 on에 분기를 두지 않는다). advisor instruction의 purpose 문장(key 없이 이미
   쓰인 purpose anchor는 오늘의 advisor loop로 돈다).

## Risks / Trade-offs

- [감사와 그 포착이 사라진다] → 끝이 loop 밖에 있다는 anchor 작성자의 선언이 그 대가를 진다. 감사가 필요한
  anchor는 key를 쓰지 않는다.
- [key가 launch 경로에서 깨지면 key 없는 anchor로 읽힌다] → 오늘의 advisor loop로 퇴행할 뿐이고, 그
  session에 `loop.json`이 생겨 보인다.
- [key 없는 anchor의 notice가 Korean skill 본문에서 English hook 배달로 옮긴다] → 같은 뜻이 같은 turn에
  실린다. 0.57.3과의 byte 비교가 바뀐 곳을 정확히 기록한다.
- [이미 쓰인 anchor의 frontmatter에 `own` 아닌 `end:`가 있으면 launch가 차단된다] → define-mission은
  `deadline:`만 제안한다. 차단은 launch 시점에 일어나고 fix를 말한다.
- [hold 8회 뒤 harness가 정지를 통과시키면 session은 heartbeat까지 잔다] → own-end loop는 스스로 끝나지
  않는다는 뜻 그대로다. 잠은 3h로 상한된다.

## Migration Plan

key 없는 anchor는 할 일이 없다. own-end를 원하는 anchor는 머리에 frontmatter 세 줄(`---` / `end: own` /
`---`)을 둔다 — 구버전 plugin은 그 anchor로 오늘의 loop를 돈다. 되돌림은 그 세 줄을 걷는 것이다.
