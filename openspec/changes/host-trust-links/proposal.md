## Why

advisor round 6의 두 발견. (1) 방문자 표면의 유일한 bypassPermissions 안전 설명("adopt
this in a repository where you accept that mode")이 위험을 repo 범위로 축소한다 — 실제
신뢰 결정은 host-level(무승인 shell = network·repo 밖 filesystem·secrets)이고, canon
자신이 bypass shell을 임의 host 실행으로 전제한다(ploop 정본이 advisor Bash를 막는 근거:
"임의 부작용 방지"). 단순 누락이 아니라 mis-scoping이다. (2) 관문의 핵심 기능인 정본
link가 표류 감지 밖이다 — repo에 link checker가 없고 docs-form-check는 scheme URL을
제외하며, canon file rename 시 관문이 조용히 404를 안내해도 어떤 check도 red가 되지
않고 pages 재배포도 발화하지 않는다(`paths: [site/**]`).

## What Changes

- **host-level trust 문구 교정** (site + README 한·영): "repo에서 수용" → "이 machine에서
  무승인 shell 실행 — 신뢰의 범위는 repo가 아니라 host". 검증 불가한 mitigation 처방은
  넣지 않는다(canon에 isolation 가이드 부재 — site는 canon을 앞서지 않는다).
- **canon-link binding**: site-truth-check.yml에 `canon-links` job 추가 — 표면 3종의
  `github.com/clomia/claude-automata/(blob|tree)/main/<path>` link 전수를 checkout tree의
  경로 존재로 검증(결정론·offline). canon rename PR은 관문 link 수정 전까지 red가 되고,
  그 수정이 `site/**`를 건드려 pages 재배포도 함께 발화한다. **외부 link(claude.com·uv
  docs 등)는 결속하지 않는다** — network 검사는 CI 비결정성(flake)을 들여오고, 대상이
  이 repo의 쓰기 권한 밖이라 red가 행동 가능하지 않다. 이 배제는 설계다.
- **root 0.1.4** — README 변경의 PyPI 재발행 (기존 원칙의 일관 적용).

## Capabilities

### New Capabilities

<!-- 없음 -->

### Modified Capabilities

- `landing-page`: Site 내용 계약에 link 결속 요구 추가 — 표면의 repo-내부 정본 link는
  대상 경로의 존재가 CI로 검증된다.

## Impact

- `site/index.html`·`README.md`·`README.ko.md` (bypass 문구), `.github/workflows/site-truth-check.yml`
  (job 추가), `pyproject.toml`(0.1.4), `openspec/specs/landing-page/spec.md` (archive 시 sync)
