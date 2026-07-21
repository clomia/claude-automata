# Design — protection-plan-gate

## Context

GitHub는 rulesets를 public repo 전 plan·private repo 유료 plan에만 제공한다. free-plan
private repo에서 rulesets endpoint는 일괄 `HTTP 403` + "Upgrade to GitHub Pro or make
this repository public"으로 거부된다 — 설치 시나리오에서 실측된 signal이다. seed의
protection은 canon(MEMORY.md·tx README)상 이미 best-effort지만, 보고 어휘에 terminal
state가 없어 영구 조건이 일시 장애(`unavailable`)로 표기되고, INSTALL.md가 그 어휘를
설치 완료 판정에 소비한다.

## Goals / Non-Goals

- Goal: plan-gate를 코드가 결정론적으로 판별해 satisfied state로 보고 — 설치 agent가
  추론·재시도·escalation 없이 안착한다.
- Goal: 조건 해소(공개 전환·plan 업그레이드) 시 무상태 자동 상향 — 기존 수렴 의미론 보존.
- Non-Goal: server-side protection의 대체 수단(client-side는 기존 hook이 이미 담당).
- Non-Goal: org plan 세분화 — GitHub의 거부 메시지 하나로 충분하다.

## Decisions

- **판별은 거부 메시지 marker로 한다** — 실패 사유에 "Upgrade to GitHub Pro"가 있으면
  plan-gate. 대안이던 사전 probe(`gh api user` plan 조회 + visibility 조합)는 org 소유
  repo에서 plan 조회 권한이 불확실하고 API 호출·실패 mode를 늘린다. GitHub가 거부
  응답으로 직접 말해주는 것이 가장 정확한 oracle이다. 메시지는 GitHub API의 영어 고정
  문자열이라 locale 표류가 없다.
- **분류기는 protection_report의 전 실패 지점에 일괄 적용한다** — marker는 rulesets
  endpoint에서만 발생 가능하므로(list·create·update 어디서 먼저 발화하든) 지점별 분기가
  불필요하다. 실패 문자열 조립을 한 함수로 모으는 부수 효과가 있다.
- **보고 문구는 자체 요약** `unsupported (private repo on a free plan)` — gh 메시지
  relay는 "upgrade하라"는 지시가 실려 소비 agent가 다시 문제삼을 수 있다. 원인 요약만
  남긴다.

## Risks / Trade-offs

- [GitHub가 거부 메시지 문구를 바꾸면 판별 실패] → 안전한 방향으로 퇴행한다: 기존
  `unavailable` 보고로 떨어질 뿐 차단·오동작이 없다. INSTALL.md도 unavailable을
  "converge 대상"으로만 다루므로 설치가 깨지지는 않는다.
- [403이지만 plan-gate가 아닌 경우를 unsupported로 오분류] → marker가 메시지 전문
  일부이므로 SAML·권한 403과 충돌하지 않는다 — 그 메시지들에는 해당 문구가 없다.

## Migration Plan

배포는 plugin release로 나간다. 기 시드 repo는 다음 seed 실행에서 새 분류를 얻는다 —
상태 저장이 없으므로 rollback도 plugin 버전 복귀만으로 완결된다.

## Open Questions

없음.
