# claude-automata

English | [한국어](README.ko.md)

Plugins that amplify Claude Code's autonomy.

## Getting Started

**[`uv` is required. If you don't have it, install it first.](https://docs.astral.sh/uv/getting-started/installation/)**

Add this repository to the marketplace:

```
claude plugin marketplace add clomia/claude-automata
```

## Plugins

- **[Parallax](plugins/parallax/README.md)** — Autopilot for long, complex tasks

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
