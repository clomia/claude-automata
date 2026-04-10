# claude-automata

English | [한국어](README.ko.md)

Plugins that amplify Claude Code's autonomy.

## Getting Started

**[`uv` is required. Install it if you don't have it.](https://docs.astral.sh/uv/getting-started/installation/)**

Add this repository to the marketplace: `claude plugin marketplace add clomia/claude-automata`

# Parallax

[**View Architecture Diagram**](https://mermaid.ai/live/view#pako:eNp1VV1v4joQ_SuWn1otRSGUpeRhpYjVqrvadtHNpaqueDHJELwkdtZ2gG7V_35nnED5Kg98xGeOz8w5Nq881RnwiFv4U4NK4asUuRHlTDF8idppVZdzMDPVPkmdNmzKhGVTS4_pYSWMk6mshHLsfkxr91qv7PniQ0yLD0IqNtbKwdY1mLneMpPPxVUYBB3WG-BbOBh0WNAN7q7ZRBhRFGJ7zjd5Jr5fJl2CdUagtHNMkhAmccIBvmsD55DxE0EehfEUx9IOcbGXH2draU9hoLLdiKY3X77cjyM2MbqsHEsRhg1LlROXb8QtpVrt4AZS1zZPLYchTYDGEHR74XWDedQoXq_B4Hg7SRL52Tf8ST0vpfMDb7D3Y9yfMIlYAzNiw2oEs6pRI1RGHsq1cFIrVgqz2rl40ILn-PQQR-ybNhthskOOBvIQ3yDmhhr9tzYK2yyrAhzsKAqtK5p35aWxq1JsWT9gRtcqs21b-60mz1GTCpEDztliWQXZO2jy3Pb0U4uMWbCWxFvy9B2UJDctFU2HSVXVTb8GcoIvJfKal-YRyUDNNVq4z_aJG6dR3Ltx7MjkuTN-itr0QNvBRpsVZcWAyMS8AJbptC5x5UJP3qe0NoYKG2HkkFaWGByUFVvIAk4qPx1t6vEkXpvMl5Gxmd4cdDZ-avf7BzVdom3mR7Sx7-GE9OpH8uvx-oiPAtBY12zGlNcj13Chza9A8bi08UHwLh2I4MKBOLMgpqxKHF2tYFsVeMx3vtvTwRE0VqJ4sdIeRZpecbzv6hE2u-jgaVd1UXwo-SCfOear5TZg68LZQ6AoHOo-F4kfJeb_QGtL294lcVHoTZstp_0BORBTWGDTM8oFRemMsNE5AYMK3Q6KlO3p-EjAd_Xb29LgMWALgGwu0tVxwfvFgXZL8sbWZiHSvapjuLfQyHzpmF4wKmsvVVY1Aq0_rbnRm5PRfHz9HFl0fq9h1dRHRRStQSxrpNKFwzs8NzLjkTM1dHgJBm3Bn_yVCGbcLaGEGY_wawYLgdUzPlNvWIZ_EP9pXe4q8RznSx4tBHrT4XWV4TFt_1r3EBQGZkx3EI8GQ0_Bo1e-5VE4-Ny9C4f9Xhj0RmFwG-LqC49Go-6wNxiFt2E_uB30e_23Dv_rN-11w-FdMLxF7PDzaHg3GLz9D9smZh4)

> **Intelligence booster for complex tasks**  
> This plugin keeps Claude Code from stopping short and drives it to finish the job.

LLMs generate tokens starting from the representation space activated by their input, and the further generation proceeds, the more prior outputs tend to constrain subsequent exploration, narrowing its scope. Therefore, to explore regions the model struggles to reach on its own, input that activates new regions is needed.

This tendency is one of the factors that leave people unsatisfied with single-turn results in Claude Code and lead them to iterate across multiple turns.

parallax generates and injects input that activates new regions, enabling the model to reach regions it struggles to reach on its own — improving single-turn result quality.

### Installation

```
claude plugin install parallax@claude-automata
```

### Usage

**Automatically activates when the prompt ends with the `parallaxthink` keyword**

> Example: Make a tic-tac-toe game in HTML. parallaxthink

Use the `/parallax-log` command to view the most recent parallax log.

# Appendix: Plugin Management Commands

> To use in local scope, add the `--scope local` option to the command.

- Install plugin: `claude plugin install {plugin}@claude-automata`
- Uninstall plugin: `claude plugin uninstall {plugin}@claude-automata`
- Enable plugin: `claude plugin enable {plugin}@claude-automata`
- Disable plugin: `claude plugin disable {plugin}@claude-automata`

### Updating plugins to the latest version

```
claude plugin marketplace update claude-automata
claude plugin update {plugin}@claude-automata
```
