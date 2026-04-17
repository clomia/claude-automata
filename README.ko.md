# claude-automata

[English](README.md) | 한국어

클로드 코드의 자율성을 증폭시키는 플러그인들

## Getting Started

**[`uv`가 필요합니다. 없다면 먼저 설치하세요.](https://docs.astral.sh/uv/getting-started/installation/)**

이 레포지토리를 마켓플레이스에 추가하세요

```
claude plugin marketplace add clomia/claude-automata
```

## 플러그인들

- **[Parallax](plugins/parallax/README.ko.md)** — 길고 복잡한 작업을 위한 자율 주행 시스템

# Appendix: Plugin Management Commands

> 커멘드에 `--scope local` 옵션을 추가하면 로컬 스코프로 동작합니다.

- 플러그인 설치: `claude plugin install {plugin}@claude-automata`
- 플러그인 삭제: `claude plugin uninstall {plugin}@claude-automata`
- 플러그인 활성화: `claude plugin enable {plugin}@claude-automata`
- 플러그인 비활성화: `claude plugin disable {plugin}@claude-automata`

### 플러그인을 최신 버전으로 업데이트하기

```
claude plugin marketplace update claude-automata
claude plugin update {plugin}@claude-automata
```
