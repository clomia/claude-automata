## Context

brownfield 도입 리포트(dronesquare-backend)가 프릭션 4건을 보고했고, 검토 결과 2건이
플러그인 결함(F1 동결 표면 소급 재심판·F4 ruleset 부트스트랩), 검토 중 1건이 추가
발견됐다(G1 pin-only 전파). 셋 다 이 repo 단독으로 재현·정당화된다 — proposal의 Why가
실측을 담는다. 제약: dronesquare 특수화 금지, 기능(gate 강도) 희생 금지, seed의 "idempotent
converge + 1행 보고 + best-effort" 철학 유지.

관찰 근거(2026-07 실측): openspec 1.6.0 `validate --all`은 archive를 검사하지 않는다(active
spec만) — 채택 engine 자신이 "동결분 재검증 제외"의 선례다. close의 CI gate는 `gh pr checks`로
required 지정과 무관하게 보고된 전 check를 감시한다(MEMORY) — server-side checks rule은
감사 강화이지 1차 gate가 아니다.

## Goals / Non-Goals

**Goals:**

- 장기기억 유입 gate 강도 불변 — 유입되는 모든 바이트는 동일 검사를 통과한다.
- brownfield 도입이 기 archive 재작성(이력 falsify) 없이 성립한다.
- seed 소유 산출물(workflow·ruleset)이 어느 시점에 심었든 최종 형상으로 수렴한다.

**Non-Goals:**

- 기존 archive의 소급 수정 — 동결 기억이다.
- repo별 설정 표면 신설 — 설정 0을 유지한다 (제외 목록·baseline 파일 없음).
- ruleset에 대한 admin 편집 보존 — ruleset은 seed-owned 형상이다 (workflow와 동일 계약).
- `docs/research/` dated 문서의 scan 면제 — 규약 내 구제책(banner·삭제 전이)이 있다.

## Decisions

- **D1: archive는 전체 제외가 아니라 diff-scoping.** PR 생성·CI는 close 시점 — `tx:archive`
  이후다. change 산출물이 CI form check를 받는 유일한 순간에 이미 archive 안에 있으므로, 전체
  제외는 episodic 유입 스트림을 gate에서 영영 빼버린다. diff-scoping은 greenfield에서 현행과
  동치이고(모든 archive 유입분이 자기 PR diff에서 검사됨), adoption에서 기 archive를
  grandfather하며, `.gitignore` 진화의 소급 wedge를 소멸시킨다. baseline 파일 대안은 상태
  부채라 기각.
- **D2: diff 기준은 merge ref의 first parent.** workflow는 `on: pull_request` 전용이고
  checkout은 merge commit이므로 `git diff --name-only --no-renames --diff-filter=AM HEAD^1
  HEAD`가 곧 PR의 유효 diff다 — token·API 불요, checkout `fetch-depth: 2`만 추가.
  `--no-renames`로 archive 이동(rename)을 신규 경로의 Add로 강제 검출한다. diff 실패는
  exit 1 (fail-open은 gate hole, full-scan fallback은 wedge 재도입이라 둘 다 기각).
- **D3: workflow 수렴은 byte equality.** header가 이미 "overwrites this file whole"을
  선언한다 — pin 비교는 그 계약의 부분 구현이었다. english-form-tokens change가 수용했던
  "수동 동기화 + 다음 pin drift 대기" 경로는 이 결정으로 대체된다. plugin 갱신 후 첫 seed가
  기 시드 repo를 자동 수렴시킨다.
- **D4: ruleset은 rule 단위 조건부 + 상향만 수렴.** ruleset 전체 disabled/evaluate 부트스트랩
  기각 — PR 강제·non-fast-forward·deletion은 workflow와 무관하므로 창 구간에도 active여야
  한다. downgrade 금지 — point-in-time probe로 보호를 제거하지 않는다(full이면 항상 그대로).
  상향 PUT은 canonical full 형상 전체다 — GET-merge 대안은 admin 편집 보존이라는 비계약
  표면을 만들 뿐이다(seed-owned, D3와 동일 계약). 승격의 자연 cadence는 "seed는 매 /tx:open마다
  실행"이다 — 첫 tx merge로 workflow가 base에 닿은 뒤 다음 open이 수렴시킨다.
- **D5: probe 정책 — 실패는 full로.** 기존 Actions probe의 "no new failure mode" 정책을
  유지·확장한다. workflow-on-base probe는 local `git cat-file -e origin/<base>:<path>`다
  (open-tx가 방금 fetch했으므로 신선; API 왕복 0). base 미해석은 probe 실패로 full,
  cat-file 비존재는 부재로 reduced — "origin/<base> ref 자체가 없는" 경우가 부재로 합류하는
  것은 수용한다(그 상태의 repo에는 tx가 적용되지 않고, reduced-active도 안전한 형상이며 이후
  수렴된다). reversible assumption으로 기록한다.
- **D6: version 0.13.0.** seed behavior·배포물이 변한다. root package·타 plugin 불변.

## Risks / Trade-offs

- [동결분 소급 재심판 포기 — `.gitignore` 변경이 archive 참조와 어긋나도 침묵] → 의도된
  의미론이다: 동결 기록은 현재 규칙의 심판 대상이 아니다(MEMORY 불변식 4의 "인용된 과거").
  living 표면의 rot detection은 전량 스캔으로 유지된다.
- [최초 tx 1건의 merge에 server-side required 부재] → close의 client gate(전 check 감시)가
  동일 조건을 강제한다. 2번째 tx부터 full. 창 구간에 non-tx lane이 merge하는 것은 도입 전
  status quo와 동일하다.
- [상향 PUT이 ruleset의 admin 커스텀을 덮음] → seed-owned 형상으로 수용, docstring에 명시.
- [fetch-depth 2 전제: HEAD가 merge commit] → `on: pull_request` 전용 트리거라 항상 성립.
  전제가 깨지는 실행(수동 재사용)은 diff 실패 → loud fail로 수렴한다.

## Migration Plan

단일 tx. 기 시드 repo는 plugin 갱신 후 첫 `/tx:open`의 seed가 workflow byte 수렴 + ruleset
상향 수렴으로 처리한다 — repo 측 행동 불요. rollback은 tx revert (server ruleset은 상향만
하므로 revert 후에도 안전).

## Open Questions

없음.
