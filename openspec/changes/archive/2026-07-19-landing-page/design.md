## Context

정본(ARCHITECTURE·MEMORY·plugin 정본)은 완결적이지만 진입 비용이 "repo 정독"이다. 관문이
필요하다: 시각 표현력이 있는 landing page와, 그리로 유도하는 간결한 README. 사이트는 정본의
재배열이 아니라 이해의 압축이며, 판단 기준은 "처음 방문자의 이해 비용 최소화"다(무인 운용 —
갈림길은 이 기준으로 자체 판정하고 여기 기록한다).

## Goals / Non-Goals

**Goals**: 수 분 안에 "무엇인지 → 왜 가치 있는지 → 어떻게 시작하는지" 전달. 기억 system
시각화가 핵심 산출물 — 읽기 전에 그래픽만으로 구조가 이해되어야 한다. 모든 주장은
코드·정본으로 검증 가능. mobile 성립.

**Non-Goals**: 정본 복제(요약+link만 — 복제는 표류를 낳는다), plugin 개별 설치 안내(가능하나
고급 사용법 — 방문자 표면은 init 단일 경로, 이 생략은 설계다), plugin behavior·init 동작 변경,
다국어 사이트(English 단일 — Claude Code 사용자층의 공통 언어, README.ko가 한국어 수요를 감당).

## Decisions

- **site source는 `site/`** — `docs/`는 조사 기록의 home(배제, anchor 제약), repo root 배치는
  root를 오염시킨다. branch 기반 Pages는 root·`/docs`만 지원하므로 **workflow 배포가 유일한
  경로**이고, 이는 GitHub 공식 actions(configure-pages·upload-pages-artifact·deploy-pages)
  사용을 의미한다 — 새 외부 의존 gate: platform 소유자(GitHub)가 유지보수하는 공식 actions로,
  이미 repo가 쓰는 actions/checkout과 같은 신뢰 class. Jekyll 기본 build는 build step과 theme
  의존을 더해 기각.
- **framework 0, 수작성 정적 파일** — 단일 page에 build chain(Astro·Hugo 등)은 순수 부채.
  시각화는 inline SVG + CSS animation으로 구현한다: JS 없이 rendering되고(점진적 향상),
  반응형 scale이 자연스럽고, "정밀하게 맞물린 기계" 인상을 vector 정밀도로 운반한다.
  JS는 보조(scroll reveal 류)로 최소화하고 없어도 내용이 성립해야 한다.
- **시각 방향은 frontend-design skill로 개발** — 인상 축: 정밀 기계(automata)·기술적
  신뢰·절제된 밀도. 과장 마케팅 톤·템플릿 landing 인상 배제.
- **Pages 활성화는 `gh api`** (`build_type=workflow`). 권한이 막으면 그 지점을 기록하고
  나머지를 완결한다(anchor 제약).
- **live 검증 시점** — reversible assumption: `workflow_dispatch`를 tx branch ref로 호출해
  merge 전에 live URL을 검증한다. github-pages environment 보호 규칙이 branch 배포를 막으면
  deployment branch policy를 API로 조정하고, 그것도 막히면 live 검증은 merge 직후로 미룬다
  (mission 완료 조건은 loop가 merge 후에도 검증을 소유한다 — openspec task는 close 전
  완결 가능한 형태로만 적는다).
- **README 압축의 경계** — 4결함(인벤토리 부재·init 실동작 미공개·install 이원화·heading
  위계)을 해소하되, plugin 사용 절차의 핵심(ploop의 define→launch→docent 흐름 등)은 유지한다:
  사이트는 요약이고 정본은 설계 문서라, 사용 절차의 home은 여전히 README다. 한국어판을
  원본으로 작성하고 영어판을 번역 정합시킨다(translate skill 규율). marketplace 단독 추가
  안내도 제거한다 — install 서사 이원화의 일부다.
- **root package 0.1.1** — README.md가 PyPI long_description이므로 version bump로 재발행을
  유도한다. plugin 구현 불변이라 plugin version은 bump하지 않는다(update rule의 관할 밖).
- **사이트 산문도 장기기억이다** — git 추적되는 비실행 text이므로 refine:docs의 재접지
  domain에 들어간다. 탄생 시 정합은 claim audit(아래)이, 이후 부패는 refine 주기가 잡는다.
- **fresh-context 검증 protocol** — 검증자는 사전 맥락 0의 독립 agent 3계열: (1) live
  사이트만 보고 "무엇/왜/어떻게" 재구성 → 내가 보유한 ground-truth 사실 목록과 대조,
  (2) README만 보고 동일 재구성, (3) claim audit — 사이트·README의 모든 사실 주장을 추출해
  코드·정본과 대조(과장은 결함). 반응형은 실측 우선(headless browser 가용성은 apply에서
  측정), 불가 시 media query·layout 정밀 감사로 대체한다.

## Risks / Trade-offs

- [Pages API 권한 부족] → 차단 지점을 기록하고 수동 단계를 종료 요약에 남긴다(anchor 제약).
- [environment 보호로 branch 배포 불가] → policy 조정 시도 → 실패 시 live 검증만 merge
  직후로 이동. workflow 자체는 main push에서 무조건 성립.
- [사이트-정본 표류] → 복제 금지(요약+link) + refine:docs domain 편입으로 완화. 잔여 위험
  수용: 사이트는 정본이 아니며 충돌 시 정본이 이긴다.
- [uvx 단축형 안내와 PyPI placeholder] → 기발행 확인됨: README가 이미 `uvx claude-automata
  init`을 안내하고 publish workflow·spec(Release publishing)이 발행을 소유한다. 사이트는
  같은 command를 인용만 한다.

## Open Questions

없음 — unknown은 전부 measurable(headless 가용성, dispatch 가부, API 권한)이라 apply에서
측정해 위 fallback으로 흡수한다.
