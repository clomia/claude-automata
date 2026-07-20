## Context

기억 canon(MEMORY.md → docs-surface.md 배포 사본 2개)은 사용자 repo에 만들어지는
아티팩트의 형식을 의무화한다: research header 토큰, 신뢰도 등급 라벨, 정본의 glossary
section 이름. seed되는 `memory-check.yml`이 그중 header 토큰을 CI로 강제한다. 이 형식
어휘가 한국어라 사용자 repo의 아티팩트와 CI 로그에 한국어가 기본값으로 노출된다.
플러그인의 다른 사용자 표면(src·hooks·metadata·CLI·workflow UI·frontmatter)은 감사
결과 이미 English-only다.

## Goals / Non-Goals

**Goals:**

- canon이 의무화하는 form 토큰을 English-only로 — 내용 언어는 자유 (openspec 모델).
- seed CI의 검사·메시지 English-only.
- 이 repo의 토큰 인스턴스를 같은 transaction에서 이행해 CI green 유지.

**Non-Goals:**

- 내부 프롬프트(스킬 본문·references 산문·agent 정의)의 한국어 제거 — 소유자의 유지관리
  언어로 수용된 한계다.
- openspec archive 소급 수정 — 동결 기억이다.
- research 문서 본문·제목의 언어 변경 — 내용이지 형식이 아니다.
- README.md의 `한국어` 링크 — 언어명을 해당 언어로 쓰는 endonym 관행이다.

## Decisions

- **English-only 정규식, 한국어 alternation 미유지.** `(작성일|Date)`를 유지하면 아티팩트
  자체에 한국어 토큰이 남는다 — 사용자 대면 파일의 English-only 원칙과 충돌. 이행 비용은
  이 repo의 research 2건 (동일 transaction에서 처리).
- **등급 라벨 대응** — 검증됨→verified, 판단→judgment(측정이 아닌 저자 판단), 미검증→
  unverified, 반박됨→refuted. emoji가 1차 marker, 라벨은 legend와 인라인 `🔶 Judgment:`
  형태의 form 토큰.
- **`## Glossary`.** grep 회상 key가 바뀐다 — canon 정의처(MEMORY.md ×3 언급)와 실존
  인스턴스(plugins/ploop/ARCHITECTURE.md)를 함께 이행해 회상 경로 단절을 막는다.
  docs-surface.md 자신의 `## 용어` section heading도 같은 이름으로 이행 (문서가 자기
  규약의 예시가 된다).
- **research 파일의 header 이행은 의미 동결 위반이 아니다** — canon 주도의 기계적 형식
  이행이며 본문 의미는 불변. 미이행 시 새 CI가 실패하므로 동일 transaction이 강제된다.
- **seed 사본 수동 동기화.** `pin_drifted`는 openspec pin만 비교한다 — template 내용
  변경은 재배포를 트리거하지 않는다. 이 repo의 `.github/workflows/memory-check.yml`은
  수동 동기화. 외부 repo는 다음 pin drift에서 새 template을 받는다 (그 시점에 한국어
  header 문서가 있으면 CI가 지적 — 그 repo의 이행 신호로 동작).
- **byte-identical 유지** — refine 사본은 tx 원본을 `cp`로 복제 (테스트가 결속을 강제).
- **version pair bump: tx·refine·ploop** — 배포 디렉토리 내용이 변한 플러그인만.
  root/PyPI는 불변 (claude_automata 패키지 미접촉, marketplace는 version 비고정).

## Risks / Trade-offs

- [외부 repo에 구 검사 잔존] → seed의 pin drift 재배포가 자연 해소 경로; 그 전까지
  한국어 수용 alternation이 남지만 새 문서는 canon(사본 배포)이 English 토큰으로 이끈다.
- [grep 회상 key 변경 (`## 용어` → `## Glossary`)] → 정의처·인스턴스 동시 이행으로 단절
  방지; 구 key 검색은 archive에서만 잔존 (동결이라 무해).
