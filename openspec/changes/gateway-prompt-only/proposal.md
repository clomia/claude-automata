## Why

설치는 오직 agent가 한다 — 이 전제를 관문에서 끝까지 밀면, 사람 대면 표면에 `uvx
claude-automata init` 명령과 그 settings 공개 표가 남을 이유가 없다. 명령의 소비자는 agent
이고 agent는 INSTALL.md로 그것을 읽는다. 관문(README·site)은 위임 prompt 한 줄로 단순화한다 —
방문자가 할 일은 그 prompt를 자기 Claude Code에 건네는 것뿐이다.

단, init이 `permissions.defaultMode="bypassPermissions"`를 쓴다는 사실은 보안 관련 투명성
공개다. 관문에서 지우되 **삭제하지 않고 INSTALL.md로 이전한다** — 위임 prompt가 명시적으로
읽으라 지시하는 문서이자, 신중한 사용자가 붙여넣기 전에 감사하는 곳이다. init-disclosure CI는
방문자 표면 대신 INSTALL.md에 재결박해 공개가 settings.py와 표류하지 않도록 유지한다.

## What Changes

- **관문에서 init 맥락 제거** — README 쌍과 site en·ko의 getting-started에서 `uvx
  claude-automata init` 명령 블록과 settings 공개 표/목록을 제거한다. 남는 것은 위임 prompt
  code block 하나 + 최소 전제(Claude Code·uv·POSIX) + INSTALL.md link.
- **공개를 INSTALL.md로 이전** — init이 쓰는 settings(bypassPermissions·opus[1m]·flag 3종·
  marketplace)를 INSTALL.md의 installed-state 술어로 명시한다. init 명령 자체는 INSTALL.md에
  이미 oracle로 존재한다(agent가 읽는다).
- **init-disclosure CI 재결박** — `site-truth-check.yml`의 스캔 표면을 4개 방문자 표면에서
  `INSTALL.md` 단일로 바꾼다. 결박 대상(settings.py 실값)은 불변.
- **landing-page spec delta** — README 관문화·Site 서사 계약·Agent install canon 3개
  requirement의 공개 계약을 갱신한다.
- version bump 없음 — plugin·package 구현 불변. 관문 문서·site·repo CI만 변한다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `landing-page`: README 관문화(설치 절 = 위임 prompt만), Site 서사 계약(getting-started =
  prompt만, init 공개의 home을 INSTALL.md로), Agent install canon(INSTALL.md가 settings
  공개를 지고 CI 결박).

## Impact

- `README.md` · `README.ko.md` · `site/index.html` · `site/ko/index.html`
- `INSTALL.md` (settings 공개 술어 추가)
- `.github/workflows/site-truth-check.yml` (init-disclosure 표면 재결박)
- `openspec/specs/landing-page/spec.md` (archive 시 sync)
- canon-links는 그대로 동작: 관문의 INSTALL.md·repo root link는 유지된다.
