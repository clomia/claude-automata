# narrator safeguard 오탐 — Sonnet 5.5 거부, Sonnet 5 통과

- Date: 2026-10-07
- Question: ploop narrator가 alias `sonnet`(→ Sonnet 5.5)으로 돌 때의 거부는 입력 slice 탓인가
  모델 탓인가 — `claude-sonnet-5[1m]` pin이 이를 피하는가.
- Method: (1) 실제 ploop run(Claude Code 2.1.291, 다른 repo)의 subagent transcript에서 narrator
  호출 전수의 assistant record를 분석. (2) Claude Code 2.1.292에서 같은 repo·같은 round slice
  사본으로 `claude -p --plugin-dir`(main haiku)가 narrator를 arm별 3회 호출 — 대조군은 Agent
  `model="sonnet"`(호출 인자가 frontmatter를 이긴다), 실험군은 frontmatter pin. 판정은 subagent
  transcript의 `message.model`·`stop_reason`·`stop_details.category`.

## 발견

- ✅ **실 run의 narrator 호출 3/3이 첫 API 요청에서 거부됐다** — `model: "<synthetic>"`,
  `stop_reason: "refusal"`, `stop_details.category: "reasoning_extraction"`, input token 0. round
  파일을 읽기 전이므로 trigger는 slice가 아니라 narrator 지시문 자체다. TUI에는 "Sonnet 5.5's
  safeguards flagged this message"와 오탐 report 알림이 뜬다(사용자 관측).
- ✅ **A/B: Sonnet 5.5 3/3 거부, `claude-sonnet-5` 3/3 통과** — 대조군은 실 run과 같은 category로
  첫 요청에서 거부, 실험군은 거부 0·각 5 turn·narration 작성.
- 🔶 **Sonnet 5에는 해당 classifier가 없다** — Claude API 문서(Sonnet 5.5 migration의 refusal
  categories)는 `reasoning_extraction`을 Sonnet 5.5에서 추가된 category로 기술한다. narrator의
  "모든 생각·시도·결과를 나열"이 내부 추론 재현 요청으로 오분류된 것으로 본다.

재측정은 대조군 arm만 다시 돌리면 된다 — 통과하면 pin을 alias로 되돌린다.
