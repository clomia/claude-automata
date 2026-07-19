## Context

advisor round 1의 5개 지적 중 산출물 변경이 필요한 3건(그래픽 우선 역전, 도착 표면 미연결,
공유 preview 부재)을 한 transaction으로 처리한다. 검증 protocol 보강 2건(그래픽 단독 판독,
검증자 오염)은 이 change의 검증 단계에 편입한다.

## Decisions

- **hero 순서**: eyebrow + h1(정체 한 줄) → schematic → thesis → CTA. h1까지는 그래픽에
  선행을 허용한다 — 제목 없는 도형은 방향 상실이고, anchor가 배제한 것은 "읽기"이지
  "제목"이 아니다. thesis 산문만 도형 뒤로 이동한다.
- **share image는 자가 생성**: 외부 도구 없이 1200×630 HTML card를 headless Chrome으로
  render — 사이트와 같은 token(paper·ink·copper·verdigris)과 schematic 축약을 담는다.
  산출물은 정적 PNG로 `site/assets/og.png`에 commit된다(생성 스크립트는 산출물이 아니라
  과정이므로 commit하지 않는다 — 재생성은 같은 방법으로 가능하고 방법은 이 design에 기록).
- **PyPI Homepage → landing page, Repository → repo 유지**: 두 url의 의미 분리가 정확하다.
  version 0.1.2는 재발행 유도용 순수 bump다.
- **GitHub About은 `gh repo edit`**: git 산출물이 아닌 server-side 설정 — Pages 활성화와
  같은 class로, transaction 안에서 직접 수행하고 결과를 tasks에 기록한다.
- **검증자 오염의 처리**: 실측 결과(@README 미확장·세계관 어휘 pointer 누출)에 따라
  "완전한 zero-context는 이 repo의 공식 subagent 경로에서 불가능"을 한계로 명시하고,
  probe는 인용-정박(모든 사실에 artifact 절 인용 요구)으로 운용한다. 그래픽 단독 probe는
  project명을 숨긴 구조 판독 질문으로 설계해 어휘 누출의 이득을 최소화한다.

## Risks / Trade-offs

- [og.png가 정적 산출물이라 사이트 개편 시 낡는다] → R층 산물이 아니라 홍보 표면 —
  refine:docs의 재접지 domain 밖(이미지). 사이트 대개편 시 재생성이 관례가 되도록 이
  design에 방법을 남긴다.
- [gh repo edit은 merge 전에 효력이 생긴다] → About이 가리키는 URL은 이미 live인 현행
  사이트다 — 선행 적용이 무해하다.

## Open Questions

없음.
