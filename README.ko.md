# claude-automata

[English](README.md) | 한국어

클로드 코드의 자율성을 증폭시키는 플러그인들

## Getting Started

**[`uv`가 필요합니다. 없다면 설치하세요.](https://docs.astral.sh/uv/getting-started/installation/)**

이 레포지토리를 마켓플레이스에 추가하세요: `claude plugin marketplace add clomia/claude-automata`

# Parallax

[**아키텍처 다이어그램 보기**](https://mermaid.ai/live/view#pako:eNp1VV1v4joQ_SuWn1otRSGUpeRhpYjVqrvadtHNpaqueDHJELwkdtZ2gG7V_35nnED5Kg98xGeOz8w5Nq881RnwiFv4U4NK4asUuRHlTDF8idppVZdzMDPVPkmdNmzKhGVTS4_pYSWMk6mshHLsfkxr91qv7PniQ0yLD0IqNtbKwdY1mLneMpPPxVUYBB3WG-BbOBh0WNAN7q7ZRBhRFGJ7zjd5Jr5fJl2CdUagtHNMkhAmccIBvmsD55DxE0EehfEUx9IOcbGXH2draU9hoLLdiKY3X77cjyM2MbqsHEsRhg1LlROXb8QtpVrt4AZS1zZPLYchTYDGEHR74XWDedQoXq_B4Hg7SRL52Tf8ST0vpfMDb7D3Y9yfMIlYAzNiw2oEs6pRI1RGHsq1cFIrVgqz2rl40ILn-PQQR-ybNhthskOOBvIQ3yDmhhr9tzYK2yyrAhzsKAqtK5p35aWxq1JsWT9gRtcqs21b-60mz1GTCpEDztliWQXZO2jy3Pb0U4uMWbCWxFvy9B2UJDctFU2HSVXVTb8GcoIvJfKal-YRyUDNNVq4z_aJG6dR3Ltx7MjkuTN-itr0QNvBRpsVZcWAyMS8AJbptC5x5UJP3qe0NoYKG2HkkFaWGByUFVvIAk4qPx1t6vEkXpvMl5Gxmd4cdDZ-avf7BzVdom3mR7Sx7-GE9OpH8uvx-oiPAtBY12zGlNcj13Chza9A8bi08UHwLh2I4MKBOLMgpqxKHF2tYFsVeMx3vtvTwRE0VqJ4sdIeRZpecbzv6hE2u-jgaVd1UXwo-SCfOear5TZg68LZQ6AoHOo-F4kfJeb_QGtL294lcVHoTZstp_0BORBTWGDTM8oFRemMsNE5AYMK3Q6KlO3p-EjAd_Xb29LgMWALgGwu0tVxwfvFgXZL8sbWZiHSvapjuLfQyHzpmF4wKmsvVVY1Aq0_rbnRm5PRfHz9HFl0fq9h1dRHRRStQSxrpNKFwzs8NzLjkTM1dHgJBm3Bn_yVCGbcLaGEGY_wawYLgdUzPlNvWIZ_EP9pXe4q8RznSx4tBHrT4XWV4TFt_1r3EBQGZkx3EI8GQ0_Bo1e-5VE4-Ny9C4f9Xhj0RmFwG-LqC49Go-6wNxiFt2E_uB30e_23Dv_rN-11w-FdMLxF7PDzaHg3GLz9D9smZh4)

> **복잡한 작업을 위한 지능 부스터**  
> 이 플러그인은 클로드 코드가 멈추지 않고 완벽히 끝내도록 만듭니다.

LLM은 입력이 활성화한 representation space를 기점으로 토큰을 생성하며, 토큰을 생성할수록 이전 출력이 이후 탐색을 제약하여 탐색 범위가 축소되는 경향이 있습니다. 따라서 모델이 자발적으로 도달하기 어려운 영역을 탐색하려면, 새로운 영역을 활성화하는 입력이 필요합니다.

이런 특성은 사람이 클로드 코드를 사용할 때 단일 턴의 결과에 만족하지 못하고 여러 턴을 반복하게 되는 요인 중 하나입니다.

parallax는 모델이 자발적으로 도달하기 어려운 영역에 도달할 수 있도록 새로운 영역을 활성화 하는 입력을 생성하고 주입해서 단일 턴의 결과 품질을 높입니다.

### Installation

```
claude plugin install parallax@claude-automata
```

### Usage

**프롬프트에 `parallaxthink` 키워드가 있으면 자동으로 활성화됩니다.**

> 예시: HTML로 틱택토 게임 만들어줘. parallaxthink

`/parallax-log` 커멘드로 직전에 실행된 로그를 확인할 수 있습니다.

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
