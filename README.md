# claude-automata

목적을 가지고 AI를 영속적으로 실행시키는 재귀적 자기개선 시스템.

## 사용

**Prerequisites**: [uv](https://docs.astral.sh/uv/)

```bash
uv run https://raw.githubusercontent.com/clomia/claude-automata/main/create.py my-agent
cd my-agent
uv sync
uv run automata configure
uv run automata start
```

## 개발

이 프로젝트는 Claude Code로 개발한다. `src/` 디렉토리가 제품 코드이며, copier가 사용자에게 `src/` 내용만 배포한다.

### 개발 환경 격리

`src/` 안에는 제품용 Claude Code 설정(`.claude/settings.json`, `CLAUDE.md`)이 포함된다. 개발 세션이 이 설정에 오염되지 않도록 `.claude/settings.local.json`에 `claudeMdExcludes`가 설정되어 있다.

주의사항:

- `src/CLAUDE.md`는 gitignore되어 있고, 제품의 Initialization Session이 런타임에 생성한다. 개발 중에는 존재하지 않는 것이 정상이다.
- `src/.claude/settings.json`은 프로젝트 루트가 아닌 하위 디렉토리이므로 개발 세션에 로드되지 않는다.
- `src/.claude/skills/`는 Claude Code가 하위 디렉토리에서도 on-demand 탐색하므로, `claudeMdExcludes`로 차단한다.

### 설계 문서

설계 문서는 `design/` 디렉토리에 있다. `design/DESIGN.md`가 루트 문서이다.
