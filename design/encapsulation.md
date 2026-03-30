# 시스템 캡슐화 설계서

---

## 1. 현실 인식

**완전한 설정 격리는 Claude Code 자체적으로 불가능하다.**

Claude Code는 개발자가 대화형으로 사용하는 도구이며, 격리 실행을 위해 설계되지 않았다. 유일한 완전 격리 메커니즘(`--bare`)은 `ANTHROPIC_API_KEY`를 요구하므로 Claude Max 구독(D-6)과 양립할 수 없다.

이 설계는 "완전 격리"를 추구하지 않는다. 대신 **실질적으로 영향이 큰 항목을 공식 메커니즘으로 고정**하고, 나머지는 수용하는 실용적 전략을 채택한다.

---

## 2. 격리 대상 분류

### 2.1 격리가 필수인 항목 (시스템 동작에 직접 영향)

| 항목 | 위험 | 심각도 |
|------|------|--------|
| Model (opus 외 모델 사용) | 추론 품질 저하 | **치명적** |
| Effort/Thinking (비활성화) | 추론 깊이 저하 | **치명적** |
| Auto-compact 임계값 | 컨텍스트 관리 불안정 | **높음** |
| 서브에이전트 모델 | Q-1 위반 | **높음** |

### 2.2 격리가 바람직한 항목 (간접 영향)

| 항목 | 위험 | 심각도 |
|------|------|--------|
| User auto-memory | 무관한 메모리 주입 | **중간** |
| 상위 디렉토리 CLAUDE.md | 의도하지 않은 지시 주입 | **중간** |
| User 훅 | 예기치 않은 동작 | **중간** |
| User MCP 서버 | 컨텍스트 소모, 도구 혼란 | **낮음-중간** |

### 2.3 격리를 포기하는 항목 (비용 대비 효과 낮음)

| 항목 | 이유 |
|------|------|
| `~/.claude.json` 전체 | Claude Code가 OAuth 인증, 세션 상태에 이 파일을 필요로 함. 격리 불가 |
| Managed settings | OS 레벨 정책. 개인 Mac에는 보통 없음. 차단 메커니즘 자체가 없음 |
| Claude Code 버전 | 버전 고정 메커니즘 없음 |
| `~/.claude.json`의 MCP 서버 | `--setting-sources`가 차단하는 범위가 불명확. 환경 변수 차단 불가 |

---

## 3. 격리 전략: 신뢰도 기준 계층화

### 3.1 Tier 1: CLI 플래그 + 환경 변수 (신뢰도: 높음)

**근거**: 공식 문서에 우선순위가 명시되어 있고, 동작이 결정적이다.

| 메커니즘 | 공식 문서 근거 | 고정하는 값 |
|----------|-------------|-----------|
| `--model opus` | CLI Reference: model 플래그 | 모델을 opus로 강제 |
| `--effort max` | CLI Reference: effort 플래그 | Effort를 max로 강제 |
| `CLAUDE_CODE_EFFORT_LEVEL=max` | Env Vars 문서: "Takes precedence over /effort and the effortLevel setting" | `/config` 변경 무시 |
| `CLAUDE_CODE_SUBAGENT_MODEL=opus` | Env Vars 문서 | 서브에이전트 모델 고정 |
| `env.pop("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")` | Env Vars 문서 | 기본값 95% 보장 |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` | Env Vars 문서 | User auto-memory 비활성화 |
| `--dangerously-skip-permissions` | CLI Reference | 권한 프롬프트 제거 |

추가로, `--strict-mcp-config`가 MCP 격리를 제공한다 (아래 참조).

**세션 시작 명령**:
```bash
claude -p "<prompt>" \
  --dangerously-skip-permissions \
  --model opus \
  --effort max \
  --output-format stream-json \
  --strict-mcp-config \
  --mcp-config '{}' \
  2>&1
```

`--strict-mcp-config --mcp-config '{}'`는 CLI Reference에 문서화된 공식 플래그이다: "Only use MCP servers from `--mcp-config`, ignoring all other MCP configurations." 이를 통해 User/Cloud의 모든 MCP 서버가 차단된다. 시스템이 MCP 서버를 필요로 하면 `--mcp-config ./system-mcp.json`으로 명시적으로 지정한다.

**환경 변수** (Supervisor가 설정):
```bash
CLAUDE_CODE_EFFORT_LEVEL=max                 # /config 변경 무시 (공식: "Takes precedence over /effort")
CLAUDE_CODE_SUBAGENT_MODEL=opus              # 서브에이전트 모델 고정
                                              # CLAUDE_AUTOCOMPACT_PCT_OVERRIDE는 설정하지 않음 (기본값 95% 사용)
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1            # User auto-memory 비활성화
DISABLE_AUTOUPDATER=1                        # 자율 운영 중 자동 업데이트 방지
```

**환경 상속 방식**: `os.environ.copy()`를 기반으로 위 변수를 추가/덮어쓰기한다. `os.environ`을 상속하지 않는 "깨끗한 환경" 방식은 채택하지 않는다 — Claude Code(Node.js)가 예측하지 못한 환경 변수에 의존할 위험이 너무 크다.

```python
def _build_session_env(self) -> dict[str, str]:
    env = os.environ.copy()

    # 핵심 동작 고정 (Tier 1: 높은 신뢰도)
    env["CLAUDE_CODE_EFFORT_LEVEL"] = "max"
    env["CLAUDE_CODE_SUBAGENT_MODEL"] = "opus"
    # CLAUDE_AUTOCOMPACT_PCT_OVERRIDE 미설정 — 기본값 95% 사용
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"

    # Claude Max 강제: API 키가 있으면 제거 (구독 대신 API 과금 방지)
    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_MODEL", None)

    # Python
    env["PYTHONUNBUFFERED"] = "1"

    return env
```

**`ANTHROPIC_API_KEY`와 `ANTHROPIC_MODEL`만 명시적으로 제거**한다. 이 두 변수는 Claude Code 동작을 근본적으로 바꾸므로 제거가 필수이고, 제거의 영향이 명확하다.

### 3.2 Tier 2: `--setting-sources` + `claudeMdExcludes` (신뢰도: 중간)

이 메커니즘들은 공식 문서에 기재되어 있지만, 동작의 완전성이 보장되지 않는다.

#### `--setting-sources project,local`

**공식 문서**: CLI Reference에 기재됨.
**알려진 한계**: 차단 범위가 완전하지 않을 수 있다. `~/.claude.json`(OAuth, MCP 일부)은 차단 대상이 아니다.
**차단 범위**: `~/.claude/settings.json`의 hooks, permissions, effortLevel 등. `~/.claude.json`(OAuth, MCP 일부)은 차단 범위가 불명확.

**결정**: 사용한다. 불완전할 수 있지만, Tier 1의 환경 변수가 핵심 항목을 이미 고정하므로 `--setting-sources`는 **보조적 방어선**이다. User 훅이나 permission deny 규칙 같은 부수 설정의 차단에 유용하다.

```bash
claude -p "<prompt>" \
  --setting-sources project,local \
  ...
```

#### `claudeMdExcludes`

**공식 문서**: Memory 문서에 기재됨. "Patterns matched against absolute file paths using glob syntax."
**한계**:
- 경로를 하드코딩해야 함. 프로젝트 이동 시 무효화.
- Managed CLAUDE.md는 제외 불가 (문서에 명시).
- 글로브 매칭의 에지 케이스가 미확인.

**결정**: 사용한다. `automata configure` 시 조상 경로를 자동 생성하고, `automata status`에서 유효성을 검증한다. 프로젝트 이동 시 `automata configure`를 재실행하도록 안내한다.

```python
def generate_claude_md_excludes(project_dir: str) -> list[str]:
    """프로젝트 조상 디렉토리의 CLAUDE.md를 제외 패턴으로 생성"""
    excludes = []
    project = Path(project_dir).resolve()
    home = Path.home()

    # ~/.claude/CLAUDE.md
    excludes.append(str(home / ".claude" / "CLAUDE.md"))
    excludes.append(str(home / ".claude" / "rules" / "**"))

    # 조상 디렉토리 순회
    parent = project.parent
    while parent != parent.parent:
        excludes.append(str(parent / "CLAUDE.md"))
        excludes.append(str(parent / ".claude" / "CLAUDE.md"))
        excludes.append(str(parent / ".claude" / "rules" / "**"))
        parent = parent.parent

    return excludes
```

### 3.3 Tier 3: 포기 (격리 비용 > 효과)

| 항목 | 포기 이유 |
|------|----------|
| `os.environ` 미상속 | Claude Code(Node.js)가 예측 불가 환경 변수에 의존. 깨끗한 환경 = 알 수 없는 장애 |
| `~/.claude.json` 격리 | OAuth 인증에 필수. 격리하면 로그인 자체가 불가 |
| `CLAUDE_CONFIG_DIR` | GitHub Issues #3833, #28808에서 동작 불명확 보고. 프로덕션 사용 부적합 |
| Managed settings 차단 | 메커니즘 자체가 존재하지 않음 |


---

## 4. 프로젝트 `.claude/settings.json`

Tier 2 설정들을 포함한 프로젝트 설정 파일:

```json
{
  "claudeMdExcludes": [
    "...automata configure가 자동 생성..."
  ],
  "permissions": {
    "allow": [
      "Bash(*)",
      "Read",
      "Edit",
      "Write",
      "Glob",
      "Grep",
      "Agent",
      "WebFetch",
      "WebSearch"
    ]
  },
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run python system/hooks/on_stop.py"
          }
        ]
      },
      {
        "hooks": [
          {
            "type": "agent",
            "model": "opus",
            "timeout": 300,
            "tools": ["Read"],
            "prompt": "인지 부하 트리거 생성자. 상세: cognitive-load-trigger.md §3.4"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup|resume|compact",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python system/hooks/on_session_start.py"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "idle_prompt|permission_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python system/hooks/on_notification.py"
          }
        ]
      }
    ]
  }
}
```

---

## 5. 최종 격리 매트릭스

Claude Code v2.1.83 기준.

| 항목 | 방어 메커니즘 | Tier | 판정 | 공식 문서 근거 |
|------|-------------|------|------|--------------|
| Model 고정 | `--model opus` | 1 | ✅ 검증됨 | CLI Reference |
| Effort 고정 | `CLAUDE_CODE_EFFORT_LEVEL=max` | 1 | ✅ 검증됨 | Env Vars: "Takes precedence over /effort and the effortLevel setting" |
| Auto-compact 기본값 보장 | `env.pop("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")` | 1 | ✅ 검증됨 | 기본값 95% 사용 |
| 서브에이전트 모델 | `CLAUDE_CODE_SUBAGENT_MODEL=opus` | 1 | ✅ 검증됨 | Env Vars |
| Auto-memory 차단 | `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` | 1 | ✅ 검증됨 | Env Vars + Memory 문서: "does not create or load auto memory files" |
| MCP 격리 | `--strict-mcp-config --mcp-config '{}'` | 1 | ✅ 검증됨 | CLI Reference: "Only use MCP servers from --mcp-config, ignoring all other MCP configurations" |
| 권한 프롬프트 제거 | `--dangerously-skip-permissions` | 1 | ✅ 검증됨 | CLI Reference |
| API 키 오염 방지 | `env.pop("ANTHROPIC_API_KEY")` | 1 | ✅ 검증됨 | Env Vars: "-p 모드에서 키가 있으면 항상 사용됨" |
| 자동 업데이트 방지 | `DISABLE_AUTOUPDATER=1` | 1 | ✅ 검증됨 | Env Vars |
| User settings 차단 | `--setting-sources project,local` | 2 | ⚠️ 부분 검증 | CLI Reference. 차단 범위 불완전할 수 있음. `~/.claude.json` 미차단 |
| 상위 CLAUDE.md 차단 | `claudeMdExcludes` | 2 | ⚠️ 부분 검증 | Memory 문서. 경로 하드코딩 필요. Managed 차단 불가 |
| `~/.claude.json` | — | 3 | — | 포기 (OAuth 필수) |
| Managed settings | — | 3 | — | 포기 (메커니즘 없음) |

---

## 6. `automata status` 격리 진단

```
=== 격리 상태 ===
[Tier 1] Model 고정:      ✅ --model opus
[Tier 1] Effort 고정:      ✅ CLAUDE_CODE_EFFORT_LEVEL=max
[Tier 1] Compact 기본값:    ✅ 기본값 95%
[Tier 1] MCP 격리:         ✅ --strict-mcp-config
[Tier 1] Auto-memory 차단: ✅ CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
[Tier 1] Auto-update 차단: ✅ DISABLE_AUTOUPDATER=1
[Tier 2] User settings:    ⚠️  --setting-sources project,local (보조 방어)
[Tier 2] CLAUDE.md 차단:   ⚠️  claudeMdExcludes {N}개 패턴
[Tier 3] Managed settings:  ℹ️  {감지 안 됨 | 감지됨}
```

---

## 7. 요약

**원칙**: 공식 문서에 우선순위와 동작이 명시된 메커니즘만 핵심 방어에 사용한다(Tier 1). 동작이 완전하지 않은 메커니즘은 보조 방어로 활용한다(Tier 2). 격리가 불가능하거나 비용이 효과를 초과하는 항목은 포기한다(Tier 3).

**Tier 1 보장 (9개, 모두 공식 문서 검증)**:
model, effort, compact, subagent model, auto-memory, MCP, permissions, API key, auto-update

**Tier 2 보조 방어 (2개)**:
User settings (`--setting-sources`), 상위 CLAUDE.md (`claudeMdExcludes`)

**수용하는 위험**: `~/.claude.json`의 일부 설정(테마, UI 선호)이 영향을 줄 수 있으나, Tier 1이 시스템의 핵심 동작을 모두 고정하므로 운영에 치명적 영향을 주지 않는다.
