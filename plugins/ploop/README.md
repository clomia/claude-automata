# Ploop - Effort Overclock Loop

English | [한국어](README.ko.md)

ploop is a loop built for long-running work that spans days.

- An independent advisor manages your progress on your behalf.
  - The advisor finds what the main agent missed.
- It never loses context across repeated auto-compactions.
  - When a compaction occurs, the mission is re-injected.
  - The advisor keeps the full context in files.

## Prerequisites

- `uv` must be installed.
- Auto-Compact must be set to True.

## Install

```
claude plugin marketplace add clomia/claude-automata
claude plugin install ploop@claude-automata
```

Update: `claude plugin update ploop@claude-automata`

## Usage

1. Write your mission. Use `/ploop:define-mission` for this.
2. In a fresh session, run `/ploop:launch [mission]`.
