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

ploop is a loop built for long-running work that spans days.

- An independent advisor manages your progress on your behalf.
  - The advisor finds what the main agent missed.
- It never loses context across repeated auto-compactions.
  - When a compaction occurs, the mission is re-injected.
  - The advisor keeps the full context in files.

## Prerequisites

- Auto-Compact must be set to True.

## Install

```
claude plugin install ploop@claude-automata
```

Update: `claude plugin update ploop@claude-automata`

## Usage

1. Write your mission. Use `/ploop:define-mission` for this.
2. In a fresh session, run `/ploop:launch [mission]`.

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
