# claude-automata

English | [한국어](README.ko.md)

Plugins that amplify Claude Code's autonomy.

## Getting Started

**[`uv` is required. If you don't have it, install it first.](https://docs.astral.sh/uv/getting-started/installation/)**

Add this repository to the marketplace:

```
claude plugin marketplace add clomia/claude-automata
```

# Ploop - Overclock Loop

> Install: `claude plugin install ploop@claude-automata`  
> Update: `claude plugin update ploop@claude-automata`  

ploop is a loop built for long-running work that spans days.

- An independent advisor manages progress on the user's behalf.
  - The advisor finds what the main agent missed.
- It never loses context across repeated auto-compactions.
  - When a compaction occurs, the mission is re-injected.
  - The advisor keeps the full context in files.

### Usage

> Auto-Compact must be set to True.

1. Write your mission. Use `/ploop:define-mission` for this.
2. In a fresh session, run `/ploop:launch [mission]`.
