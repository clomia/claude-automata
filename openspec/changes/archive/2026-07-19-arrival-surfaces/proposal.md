## Why

landing page는 live지만 advisor round 1이 세 결함을 표면화했다. (1) anchor의 명시 우선순위
— "접속 즉시, 읽기 전에 그래픽으로; text는 그래픽을 뒤따르는 보조" — 가 hero에서 뒤집혀
있다: eyebrow + h1 + 4줄 thesis가 schematic을 앞서고, mobile(390)에서는 first viewport가
거의 text다. (2) 방문자가 실제로 도착하는 두 문이 관문으로 라우팅되지 않는다: GitHub repo
About의 website 필드가 비어 있고 PyPI Homepage가 repo를 가리킨다 — 설치 경로가 PyPI
중심인데도. (3) 공유 link unfurl에 OG/Twitter metadata와 share image가 없어, 발견 채널
(Slack·Discord·X)에서의 첫인상이 anchor가 배제한 "템플릿 landing 인상"으로 렌더된다.

## What Changes

- **hero 재배치 (graphic-first)**: schematic figure를 h1 직후로 올리고 thesis 산문을 그
  뒤로 내린다. desktop·mobile fold에서 도형이 first viewport에 서는지 실측으로 판정한다.
- **share metadata**: `og:title`·`og:description`·`og:url`·`og:image`·`twitter:card` 추가,
  on-brand 1200×630 share image(`site/assets/og.png`)를 headless Chrome으로 자가 생성.
- **도착 표면 라우팅**: pyproject `[project.urls]`에 `Homepage` = landing page URL
  (Repository는 repo 유지), version 0.1.2로 PyPI 재발행 유도. GitHub About website·
  description은 `gh repo edit`으로 직접 설정(server-side, git 산출물 아님).
- **검증 보강 (advisor 지적 반영)**: 그래픽 단독 판독 probe — 주변 산문 없이 rendered
  schematic 이미지만으로 구조(흐름·gate·영속 대비)가 읽히는지 vision agent가 판정.
  fresh-context probe의 오염 한계 실측(README @-import 미확장, 세계관 어휘는 pointer로
  누출)을 검증 기록에 남긴다.

## Capabilities

### New Capabilities

<!-- 없음 -->

### Modified Capabilities

- `landing-page`: Site 내용 계약 요구사항에 두 계약 추가 — 기억 시각화가 본문 산문에
  선행한다(그래픽 우선), 공유 unfurl용 OG metadata·share image를 싣는다.

## Impact

- `site/index.html`(hero 순서 + meta), `site/style.css`(간격 조정), `site/assets/og.png`(신규)
- `pyproject.toml`(urls.Homepage + version 0.1.2)
- server-side: GitHub About website·description (`gh repo edit`)
- `openspec/specs/landing-page/spec.md` (archive 시 R3 MODIFIED sync)
