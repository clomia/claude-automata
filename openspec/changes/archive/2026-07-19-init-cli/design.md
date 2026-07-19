## Context

claude-automata는 marketplace(플러그인 4개)로 소비되지만, 안정 동작의 전제조건은 셋업 문서가 아니라 사용자 손에 흩어져 있다: settings.json 키 5개, marketplace·plugin 등록, 외부 CLI(gh, Node/npx, repomix). tx는 `npx --yes @fission-ai/openspec@<pin>`으로 openspec을 fetch하고(Node ≥ 20 필요), refine은 repomix를 기존 설치 → npx → bunx → bun 신규 설치 순으로 해석한다. 이 change는 전제조건 충족을 한 커맨드로 응고한다.

공식 문서 조사 결과 (2026-07-19):

- settings 키: `alwaysThinkingEnabled`·`autoMemoryEnabled`·`autoCompactEnabled`·`model`·`permissions.defaultMode`(값 `bypassPermissions`) 전부 project scope(`.claude/settings.json`) 유효 — code.claude.com/docs/en/settings.
- `enabledPlugins`·`extraKnownMarketplaces`의 형태는 **map**이다: `{"<plugin>@<marketplace>": true}`, `{"<name>": {"source": {"source": "github", "repo": "<owner>/<repo>"}}}`. 근거: plugins-reference의 "the marketplace entry name is what `enabledPlugins` keys … use" + 실동작 중인 머신 설정 실측. (settings 문서 요약이 제시한 array-of-objects 형태는 실측과 상충하여 기각.)
- uvx: `uvx --from git+https://github.com/<owner>/<repo> <executable>`이 repo 루트 package의 `[project.scripts]` 실행 파일을 격리 환경에서 실행한다 — docs.astral.sh/uv/guides/tools. PyPI 발행 없이 배포 가능.
- uv package: 루트 `pyproject.toml` + build backend(hatchling)로 빌드 가능해야 uvx가 소비한다 — docs.astral.sh/uv/guides/package.

## Goals / Non-Goals

**Goals**

- `uvx --from git+https://github.com/clomia/claude-automata claude-automata init` — uv만으로 실행.
- target repo `.claude/settings.json`: 전제조건 5키 + marketplace/plugin 등록, 비파괴 merge, idempotent.
- gh·node·npm·npx·repomix를 sudo 없이 사용자 영역에 provisioning.

**Non-Goals**

- PyPI 발행(name `claude-automata`로 후일 `uv publish` 가능하게만 유지), Windows provisioning, `gh auth login` 자동화, shell rc 수정, Claude Code 설치 검사, 플러그인 측 단순화(refine bun fallback 제거 등 — 후속 change).

## Decisions

1. **배포 = 루트 package + uvx git source.** 대안 PyPI(발행 인프라·토큰 필요), PEP 723 단일 스크립트(`uv run <url>` — 데이터 동봉·테스트·모듈 분리 불가) 대비, 루트 pyproject.toml이 무발행·무설치 실행과 후일 PyPI 발행을 동시에 연다. repo가 marketplace이자 package가 된다. layout은 루트 flat `claude_automata/`다 — plugins의 src-flat(import name `src`)은 자기 전용 env에서만 살아 무해하지만, 이 package는 배포되므로 import name이 `claude_automata`여야 하고(발행 시 site-packages 오염 방지), `src/claude_automata/` 중첩은 불필요한 계층이다.
2. **plugin 목록의 single home은 `.claude-plugin/marketplace.json`.** hatchling `force-include`로 wheel에 동봉하고 `importlib.resources`로 읽는다. 코드에 목록을 중복하면 plugin 추가 시 표류한다.
3. **settings는 owned-key 단위 deep-merge.** 소유 키(5개 전제조건 + 두 map의 claude-automata 항목)만 쓰고 나머지는 보존. `permissions`는 `defaultMode`만 설정하고 `allow`·`deny` 등 형제 키 보존. map들은 key 단위 병합.
4. **provisioning은 공식 배포 바이너리를 사용자 영역에 설치.** sudo·패키지 매니저 의존 배제:
   - gh: `https://github.com/cli/cli/releases/latest`의 redirect Location에서 버전 해석(API quota 무관) → 플랫폼별 asset(tar.gz/zip) 다운로드 → `~/.local/share/claude-automata/` 전개 → `~/.local/bin/gh` symlink.
   - Node: `https://nodejs.org/dist/index.json`에서 최신 LTS(≥ 20) 해석 → 공식 tarball 전개 → `node`·`npm`·`npx` symlink. tx의 npx 요구를 실제 Node로 충족한다(bun 불가 — tx는 `npx`를 exec한다). 기존 node가 있어도 `node --version` < 20이면 LTS를 사용자 영역에 병설하고 PATH 우선순위를 안내한다.
   - repomix: 확보된 npm으로 `npm install -g --prefix ~/.local/share/claude-automata/npm repomix` — prefix를 사용자 영역에 명시해 시스템 Node의 root-소유 전역 prefix에서도 무sudo다. npm 호출은 `~/.local/bin`을 앞세운 PATH로 실행한다 — npm launcher의 `#!/usr/bin/env node`가 방금 설치된 node를 해석해야 한다. refine의 해석 순서 1순위(`which repomix`)에 안착.
   - openspec: **설치하지 않는다.** pin의 single home은 `plugins/tx/src/openspec.py` — 여기서 설치하면 이중 pin.
   - `~/.local/bin`이 PATH에 없으면 안내만 출력(수정하지 않음).
5. **구현은 stdlib only, Python ≥ 3.14.** argparse·urllib·tarfile·zipfile·json·shutil. 외부 의존성 0 — uvx 해석이 빠르고 공급망이 없다. uvx가 3.14 인터프리터를 자동 provisioning한다.
6. **사용자 대면 출력은 English only** (repo 언어 규칙). 항목별 `ok/installed/failed` 요약을 출력하고, 실패 항목이 있어도 나머지는 계속 진행 후 비정상 종료 코드로 보고한다.
7. **active repo 안전성.** merge는 비파괴·idempotent이고, invalid JSON은 파일을 건드리지 않고 중단한다. 더 높은 우선순위의 `.claude/settings.local.json`이 전제조건을 override하면 경고를 출력한다 — local 파일은 개인 영역이므로 수정하지 않는다. settings 변경 시 실행 중인 세션의 재시작 안내를 출력한다.

## Risks / Trade-offs

- [nodejs.org `index.json`·gh release asset 명명 변경] → 해석 실패 시 해당 항목만 failed + 수동 설치 안내, 나머지 진행.
- [uvx git source 캐시로 구버전 실행] → README에 `uvx --refresh` 힌트 명기.
- [network 필요] → provisioning은 본질적으로 online 작업. settings 단계는 offline에서도 완결.
- [동봉 marketplace.json이 실행 시점 커밋 기준] → uvx가 HEAD를 resolve하므로 사실상 최신. Claude Code의 marketplace fetch(main)와 동일 소스.

## Migration Plan

신규 추가 외의 기존 파일 변경은 `.github/workflows/test.yml`(job 추가)과 README.md·README.ko.md(Setup 섹션)뿐이다. rollback = 루트 package 제거.

## Open Questions

없음 — 미지는 전부 측정(공식 문서 + 실측)으로 해소했다.
