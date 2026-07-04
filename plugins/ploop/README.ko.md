# Ploop - Effort Overclock Loop

[English](README.md) | 한국어

ploop은 며칠씩 걸리는 장기 작업을 위해 설계된 루프입니다.

- 독립된 advisor가 당신을 대신하여 진행 상황을 관리합니다.
  - advisor는 메인 에이전트가 놓친 부분을 찾아줍니다.
- 여러번의 auto compaction에도 맥락을 잃지 않습니다.
  - compaction이 발생하면 미션이 재주입됩니다.
  - advisor가 전체 맥락을 파일로 관리합니다.

## 사전 요구사항

- `uv`가 설치되어 있어야 합니다.
- Auto-Compact가 True로 설정되어 있어야 합니다.

## Install

```
claude plugin marketplace add clomia/claude-automata
claude plugin install ploop@claude-automata
```

Update: `claude plugin update ploop@claude-automata`

## 사용 방법

1. 미션을 작성하세요. `/ploop:define-mission`을 활용하세요.
2. 새로운 세션에서 `/ploop:launch [미션 내용]`을 실행하세요.

