# Autonomous AI System

**목적을 가지고 AI를 영속적으로 실행시키는 재귀적 자기개선 시스템**

## 목적을 가지고

목적이란 종료 조건이 없으며 나아가야 하는 방향을 뜻한다.
시스템은 스스로 소유자로부터 목적을 구성한다.

## AI를 영속적으로 실행시키는

여기서 AI란 Foundation Model을 내포한 도구를 총칭한다.
시스템은 컨텍스트 보존 메커니즘을 가지며 이를 통해 AI를 계속 실행시킨다.

## 재귀적 자기개선 시스템

시스템은 AI가 목적을 위해 시스템을 계속 개선하도록 유도한다.
개선 동작 자체를 포함한 모든 구성 요소가 개선 대상이다.

# Claude Automata

claude-automata는 위 자율 AI 시스템의 구현체이다. Claude Code를 AI 엔진으로 사용하며, macOS에서 영속적으로 동작한다. 소유자는 Slack을 통해 시스템과 비동기로 소통한다.

## 사용

**Prerequisites**: [uv](https://docs.astral.sh/uv/)

시스템을 설치할 디렉토리 경로를 지정하여 실행한다. 이 디렉토리가 자율 시스템의 작업 공간이 된다.

```bash
# 원하는 경로에 프로젝트 생성
uvx claude-automata ~/my-agent

# 생성된 디렉토리로 이동 후 설정 및 시작
cd ~/my-agent
uv sync
uv run automata configure
uv run automata start
```

`automata configure`에서 Slack 토큰과 시스템의 목적을 입력하면 자율 운영이 시작된다.
