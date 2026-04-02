# claude-automata

LLM의 좁아진 인지 범위를 확장하는 Claude Code 플러그인 마켓플레이스.

## booster 플러그인

LLM은 토큰을 생성하면서 확률 분포가 좁아진다. 숲에서 나무, 나무에서 나뭇잎으로 시야가 좁아지면 다른 나무나 숲을 고려할 수 없게 된다. 그래서 인간이 출력을 훑어보고 미탐색 방향을 제시하는 패턴이 반복된다.

booster는 이 인간의 역할을 재현한다:

```
에이전트 출력 종료 → Stop hook 발동
  → 부스터(별도 컨텍스트)가 출력을 훑어봄
  → 미탐색 방향이 있으면 block + 방향 주입 → 에이전트 계속 작업
  → 없거나 최대 라운드 도달 → 종료 허용
```

기존 Stop hook 구현들(ralph loop 등)과의 차이:
- **컨텍스트 분리**: 에이전트의 좁아진 확률 분포에 오염되지 않은 별도 컨텍스트에서 훑어봄
- **방향 주입**: 단순 반복 프롬프트가 아니라 미탐색 방향을 추상적으로 제시
- **반복 부스트**: 1회가 아닌 N회 라운드

## 설치

Claude Code 안에서:

```
/plugin marketplace add clomia/claude-automata
/plugin install booster@claude-automata
```

## 전제 조건

[uv](https://docs.astral.sh/uv/) 설치 필요:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 설정

| 환경변수 | 기본값 | 설명 |
|----------|--------|------|
| `BOOSTER_MAX_ROUNDS` | `3` | 최대 부스트 라운드 수 |
| `BOOSTER_MODEL` | `opus` | 부스터가 사용할 모델 |

예: 5라운드로 실행

```bash
BOOSTER_MAX_ROUNDS=5 claude
```

## 제거

```
/plugin uninstall booster@claude-automata
/plugin marketplace remove claude-automata
```

## 런타임 파일

`~/.claude/plugins/data/` 하위에 세션별 상태와 디버그 로그가 저장된다.
`CLAUDE_PLUGIN_DATA`가 없는 환경에서는 프로젝트 디렉토리에 폴백:

```
.booster-state.json
.booster-debug.log
```
