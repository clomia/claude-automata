@README.ko.md

# Principles

## Take ownership of the product

사용자는 틀릴 수 있다. 요청의 무결성을 검토하라.  
사용자는 최적해를 모른다. 요청의 Optimality를 검토하라.

## Ireducible

코드와 문서를 통틀어 모든 표현은 중복과 불일치 없이 irreducible해야 한다.  
이 지침은 귀하의 `design-principles.md`과도 align된다.

## CLI Tools

- **gh (github cli)** 를 사용해서 GitHub에 접근하라.

## Rules

- **ASCII 다이어그램에는 영어만 사용한다.** (한국어는 정렬이 깨진다)
- **주석 최소화. 코드가 설명하는 내용을 주석으로 재언 금지.**
- **새로운 라이브러리를 도입하기 전에 반드시 대안을 탐색한다.**
  - 웹 조사 후 `gh`로 레포지토리를 확인한다. 유지보수 상태, 신뢰도 등을 철저히 평가한다.
  - 한번 도입된 외부 의존성은 계속 남는다. 최적의 선택지를 찾기 위해 심혈을 기울여라.
- `_`로 시작하는 비공개 변수명 금지. 잘 설계된 인터페이스에는 비공개 변수명 불필요.
- 구현과 테스트는 독립적이어야 한다.

## Python

**uv로 python 3.14를 사용해라. 3.14버전은 PEP 749, 750, 758, 765, 768가 적용되어 있다.**

- PEP 758: except 구문 괄호 생략 `except TimeoutError, ConnectionError:`
- PEP 749: 이제 `from __future__ import annotations` 필요 없음
