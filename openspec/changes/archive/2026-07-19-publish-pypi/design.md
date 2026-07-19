## Context

실측 (2026-07-19):

- PyPI `claude-automata`는 **이미 사용자 소유다** — 2026-03-27 업로드된 placeholder release "0"(실행 파일 없는 wheel), `project_urls.Repository`가 이 repo를 가리킨다. 발행 = 기존 프로젝트에 새 버전(0.1.0 > 0, PEP 440) 업로드.
- 발행 자격증명은 어디에도 없다 — repo secret 0개(`gh secret list`), 로컬 env·`~/.pypirc` 부재.
- 현재 `uvx claude-automata init`은 placeholder v0가 해석되어 실행 파일 부재로 실패한다.
- uv publish는 GitHub Actions의 Trusted Publisher(OIDC) 인증을 지원한다 (docs.astral.sh/uv/guides/package — "Trusted Publisher authentication from CI/CD platforms").

## Goals / Non-Goals

**Goals** — `uvx claude-automata init` 성립, 발행의 버전 게이트 자동화, 토큰 무보관.

**Non-Goals** — README 커맨드 전환(발행 성립 후 후속 docs 변경), placeholder v0의 yank(계정 작업, 선택적 정리), TestPyPI 경유(placeholder로 이름·소유가 이미 확정이라 리허설 가치가 낮다).

## Decisions

1. **인증 = Trusted Publishing(OIDC), 토큰 무보관.** 장기 토큰은 유출 표면이고 secret 순환 관리가 생긴다. OIDC는 workflow 실행 시점에만 유효한 신원 교환이다. **1회 전제(계정 소유자만 가능)**: PyPI → claude-automata → Settings → Publishing에 GitHub publisher 등록 — owner `clomia` / repository `claude-automata` / workflow `publish.yml` / environment 공란. 등록 전 publish 실행은 인증 단계에서 가시적으로 실패하며, 등록 후 재실행(workflow_dispatch)으로 완결된다.
2. **트리거 = main push의 `pyproject.toml` paths filter + workflow_dispatch. 게이트 = PyPI 버전 존재 조회.** version의 single home은 pyproject.toml이다(rules/update.md와 동일 원리) — git tag 방식은 태그 규율이라는 인간 절차를 추가해 기각. dev-dependency 변경 같은 비릴리즈 pyproject 변경은 게이트가 skip으로 흡수한다. 게이트는 `https://pypi.org/pypi/<name>/<version>/json`의 200/404로 판정한다.
3. **metadata는 [project]에 완성.** `readme = "README.md"`, `license = "MIT"`(SPDX) + `license-files`, authors, keywords, classifiers, `[project.urls]`. README의 상대 링크(언어 토글)는 PyPI 렌더에서 깨지므로 GitHub 절대 URL로 바꾼다 — repo 뷰에서도 동작이 동일하다.
4. **README 전환은 발행 성립 이후.** 미발행 상태의 단축형 문서화는 placeholder 해석이라는 깨진 안내다. 이 change는 인프라만 싣고, 첫 발행 확인 후 단축형을 1차 경로로 올리는 docs 변경을 후속한다.
5. **버전관리 절차(발행 후 정상 상태).** 루트 package 변경 시 pyproject version bump → main 병합 → workflow 자동 발행. 절차의 정본은 이 change가 sync하는 spec(Release publishing)이다.

## Risks / Trade-offs

- [Trusted Publisher 등록 전 병합] → 첫 publish 실행이 인증 실패로 빨간불 — 의도된 가시성이며, 등록 후 workflow_dispatch 재실행으로 해소.
- [PyPI JSON API 일시 장애 시 게이트 오판] → 404 외 오류는 실패로 처리해 재발행 시도를 막는다(fail-closed).
- [placeholder v0 잔존] → 0.1.0 발행 시 latest가 교체되어 실사용 영향 없음. yank는 선택적 계정 작업으로 안내만 한다.

## Migration Plan

기존 파일 변경은 pyproject.toml·README 링크 2건뿐, workflow는 순수 신규. rollback = workflow 삭제(발행된 버전은 불가역이나 무해).

## Open Questions

없음 — 소유·자격증명·해석 동작 전부 실측으로 해소했다.
