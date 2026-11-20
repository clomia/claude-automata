# Tasks — ploop-own-end

## 1. Code

- [x] 1.1 `prompt.py`: frontmatter reader lifted out of `deadline_status` and shared; the loop's kind; the
      loop notice by kind, delivered at launch and carried by the re-anchoring after the anchor; the hold,
      sharing the directive's self-audit lines and deadline header (the directive's bytes unchanged)
- [x] 1.2 `main.py`: launch (the `end:` check, the delivery by kind), stop (the hold right after the
      background gate), pre_tool_use (both loop agents refused under the key)
- [x] 1.3 `skills/launch/SKILL.md`: the `<notice>` block out; `skills/define-purpose/SKILL.md`: the key and the
      anchor's own end; `skills/docent/SKILL.md`: an own-end loop's record is its transcript

## 2. Tests

- [x] 2.1 New tests through the hook entry points, each watched red on 0.57.3's code: the hold at empty
      stops writes nothing and never ends the loop, where the same stops without the key arm and then end it;
      a background stop of an own-end loop is silent; both agents refused under the key; a bad `end:` blocks
      and touches no state; the launch and re-anchor deliveries by kind; the launch skill body carries no
      notice of the kind; the hold's deadline header
- [x] 2.2 The existing tests pass unedited but the one that pinned the launch delivery to the queue line
      alone; `pytest` and `ruff` green for the plugin and the root; `openspec validate --all --strict`

## 3. Evidence

- [x] 3.1 Byte comparison against 0.57.3 for anchors without the key: the same events through every hook
      entry of both versions, exit codes, stdout, stderr and state trees diffed; inputs and outputs kept

## 4. Canon and release

- [x] 4.1 `plugins/ploop/ARCHITECTURE.md`: decision 26 and its touch points (intro, glossary, end authority,
      core loop, state table, activation lifecycle, anchoring layers, Hooks table, decisions 20·21·22,
      technical risk 1, accepted limits, file map); `MEMORY.md` invariant 5; root `ARCHITECTURE.md`'s
      ploop × tx contract, which named only the round directive
- [x] 4.2 Version 0.57.3 → 0.58.0 (`plugin.json`, `pyproject.toml`, `uv.lock`)
- [x] 4.3 `tx:verify` on the change, its findings judged

## 5. Review before the merge

- [x] 5.1 The re-anchoring carries the kind's notice and the queue address ahead of the anchor; a test with an
      anchor past the harness's 10,000-character cap asserts both within the first 2,000 characters
- [x] 5.2 Orderings pinned by tests, each mutation shown red: the hold ahead of the in-flight guard (a stray
      in-flight marker in the own-end half of the hold test); the bad-`end:` block and the prerequisite block
      ahead of any state reset (a prior ledger and queue that survive)
- [x] 5.3 docent's anchor head skips a leading frontmatter block, through the hook's reader, with a test
- [x] 5.4 Canon: decision 26 and 21 (the re-anchor order), the anchoring layer 3 and an accepted limit (the
      cap's band); the kind holds because nothing in the loop rewrites `anchor.md`
- [ ] 5.5 The suite, ruff and `openspec validate --all --strict`; the byte comparison again, with the new
      expected re-anchor diff stated; `tx:verify` on the change
