# Tasks — ploop-completion-gate

## 1. Measurement (gate)

- [x] 1.1 Official-docs + 2.1.233 bundle audit: background_tasks, asyncRewake,
      run_in_background, spawn-depth default drift, stop-block cap, opus[1m]
- [x] 1.2 Stop-turn line footprint measured; T=15 recorded in
      `docs/research/stop-turn-line-footprint-2026.md`

## 2. Core

- [x] 2.1 `prompt.py`: `format_directive` (narrator call + judge branches + advisor
      call verbatim, deadline dual delivery + expired variant, candidates lines),
      audit-history `<audit-N>` blocks
- [x] 2.2 `main.py`: stop() re-judged — narration append, verdict lanes
      (report/token/malfunction/working/bare), anomaly reset on working stops, no
      round freeze; `MISSION_COMPLETE_ENDING_THE_TURN`; `BARE_STOP_LINE_THRESHOLD`;
      `write_round_entry`/`write_audit_entry`; decline notice with disclosure;
      pre_tool_use deny message
- [x] 2.3 `state.py`: 5-field ledger (`round`), phase semantics re-worded
- [x] 2.4 `docent.py`: `round=`/`audits=` output

## 3. Prompts

- [x] 3.1 `agents/advisor.md`: independent auditor role, `Agent` disallowed,
      log-then-narration reading order
- [x] 3.2 `prompts/instruction.md`: coordinate-mandatory verdict, state over
      narrative, gate-passed evidence, rebuttal respect, completion token
- [x] 3.3 `skills/launch/SKILL.md`: completion-gate notice, AskUserQuestion rule
      deferring to the anchor's operating directive
- [x] 3.4 `skills/define-purpose/SKILL.md`: honest advisor sentence (purpose loops
      end only by /ploop:off); `skills/docent/SKILL.md`: record-surface vocabulary

## 4. Canon & exposure

- [x] 4.1 `plugins/ploop/ARCHITECTURE.md`: glossary, core loop, agent tree, state
      table, decisions 2/3/4/5/6/7/9/10/11/14/16/18/20 revised + 22/23/24 added,
      risks and accepted limits updated, depth-pin section re-grounded
- [x] 4.2 Root `ARCHITECTURE.md`: subagent-path wording
- [x] 4.3 README ko/en, site en/ko: completion-claim audit wording, token line
- [x] 4.4 Version 0.54.0 → 0.55.0; pyproject 0.3.1 → 0.3.2

## 5. Final-inspection fixes

- [x] 5.1 Verdict provenance: a report with the audit token unconsumed is no
      verdict (guard restored; forged self-certification blocked)
- [x] 5.2 Honest expiry closure: `DEADLINE_EXPIRED_ENDING_THE_TURN` token, its
      end cause, instruction 기한 종결 section, canon and spec-delta alignment
- [x] 5.3 Meta-review round: dual-source provenance (`advisor_stopped`),
      own-line token matching (expiry first), ending report persisted to the
      log, vacuous purpose-completion guard, honest mixed-streak cause,
      heartbeat waiting re-laned, version-pair lockstep, exposure/canon
      alignments (see design.md)

## 6. Tests

- [x] 5.1 `test_prompt.py`: directive shape, dual deadline, expired variant,
      disclosure absence, candidates lanes, decline-notice disclosure
- [x] 5.2 `test_main.py`: working/bare/malfunction/token lanes, streak resets,
      fresh-phase guard, resume e2e, log entries, unchanged gates
- [x] 5.3 `test_state.py` / `test_docent.py`: 5-field ledger, resolver output
