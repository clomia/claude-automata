# ploop

[English](README.md) | 한국어

**길고 복잡한 미션을 끝까지 완수하는 자율 루프.**

ploop은 **parallax loop** — 격리된 advisor가 매 라운드 클로드가 놓친 영역을 찾아
제시하고, 미션이 완전히 다뤄질 때까지 작업을 이어가게 하는 자율 루프 — 를 Claude
Code의 nested subagent 위에 구현합니다. **구독 요금제에서 안전하게** 동작합니다.

- 클로드와 미션을 정의한 뒤 `/ploop:launch`로 핸드오프하세요.
  - 핸드오프는 의도적 게이트입니다: 미션 명세를 디스크에 기록하고 parallax loop를
    띄웁니다. 사소한 단발 수정이 아니라 대규모 미션에 사용하세요.

### 왜 nested subagent인가

이런 루프를 훅에서 `claude -p`로 스폰하는 자동화 패턴은 별도 세션을 만들어
**Claude Pro/Max 구독에서 계정 차단 위험**이 있습니다. ploop은 advisor를 정식
`Agent` 툴(nested subagent)로 실행합니다 — 모든 요금제에서 지원되는 정식 기능이고
메인 세션과 같은 quota를 공유하므로, **구독에서 약관 위반 없이** 동작합니다.

### 동작 원리

- [**아키텍처 (ARCHITECTURE.md)**](ARCHITECTURE.md) — 3단계 에이전트
  트리(main→advisor→narrator), parallax loop, compaction 저항, 그리고 그 설계 결정들.

### 사전 요구사항

ploop의 내구성 훅은 **uv**로 실행됩니다.
<https://docs.astral.sh/uv/getting-started/installation/> 에서 설치하세요.

uv가 없어도 트리는 프롬프트 기반 규율로 계속 동작합니다 — 훅 기반의 advisor 호출
강제만 비활성화됩니다.

### 비용

advisor는 **1M 컨텍스트의 Opus**로, narrator는 Sonnet으로 실행됩니다. `main`이 미션을
직접 수행하고 매 라운드 advisor를 호출하며, 이는 추론 최대화를 위한 의도적 선택입니다 —
토큰 소모가 큽니다.

### 플러그인 설치

```
claude plugin marketplace add clomia/claude-automata
claude plugin install ploop@claude-automata
```

### 플러그인 업데이트

```
claude plugin marketplace update claude-automata
claude plugin update ploop@claude-automata
```
