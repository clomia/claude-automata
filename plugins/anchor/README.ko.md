# Anchor

[English](README.md) | 한국어

**길고 복잡한 미션을 끝까지 완수하는 자율 루프 — parallax의 진화형.**

Anchor는 사용자 대신 클로드가 놓친 영역을 매 라운드 찾아 제시하고, 미션이 완전히
다뤄질 때까지 작업을 이어갑니다. [parallax](../parallax/)의 메커니즘을 Claude Code의
nested subagent 위에서 재구현해 **구독 요금제에서 안전하게** 동작합니다.

- 클로드와 미션을 정의한 뒤 `/anchor:init`으로 핸드오프하세요.
  - 핸드오프는 의도적 게이트입니다: 미션 명세를 디스크에 기록하고 parallax 루프를
    띄웁니다. 사소한 단발 수정이 아니라 대규모 미션에 사용하세요.
- 진행 상황은 `/anchor:log`로 확인하세요.

### parallax와의 관계 — 무엇이 바뀌었나

parallax는 Stop 훅에서 `claude -p`를 외부 스폰합니다. 이는 별도 세션을 만드는 자동화
패턴이라 **Claude Pro/Max 구독에서 계정 차단 위험**을 안았고, 그래서 Anthropic API
요금제 전용으로 묶였습니다 — 무서워서 아무도 쓰지 못했습니다.

Anchor는 같은 parallax 메커니즘 — 격리된 advisor가 매 라운드 미고려 영역을 surface하는
자율 루프 — 를 정식 `Agent` 툴(nested subagent)로 재구현합니다. subagent는 모든
요금제에서 지원되는 정식 기능이고 메인 세션과 같은 quota를 공유하므로, **구독에서 약관
위반 없이** 동작합니다. parallax 개발 당시에는 nested agent가 없어 `claude -p`뿐이었지만,
이제는 그렇지 않습니다.

### 동작 원리 — [**아키텍처 (ARCHITECTURE.md)**](ARCHITECTURE.md)

4단계 에이전트 트리(main→anchor→advisor→narrator), parallax 루프, compaction 저항,
그리고 그 설계 결정들을 설명합니다.

### 사전 요구사항

Anchor의 내구성 훅은 **uv**로 실행됩니다.
<https://docs.astral.sh/uv/getting-started/installation/> 에서 설치하세요.

uv가 없어도 트리는 프롬프트 기반 규율로 계속 동작합니다 — 훅 기반의 advisor 호출
강제만 비활성화됩니다.

### 비용

anchor·advisor는 **1M 컨텍스트의 Opus**로, narrator는 Sonnet으로 실행됩니다. 미션은
깊은 트리로 펼쳐지며, 이는 추론 최대화를 위한 의도적 선택입니다 — 토큰 소모가 큽니다.
일관된 트리를 위해 `main`도 `opus[1m]`로 실행하길 권장합니다. Anchor가 미션 단위
opt-in인 이유가 이것입니다 — 사소한 요청은 `main`이 핸드오프 없이 직접 처리합니다.

### 플러그인 설치

```
claude plugin marketplace add clomia/claude-automata
claude plugin install anchor@claude-automata
```

### 플러그인 업데이트

```
claude plugin marketplace update claude-automata
claude plugin update anchor@claude-automata
```
