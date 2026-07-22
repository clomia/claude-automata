#!/usr/bin/env bash
# Run a command with claude-automata's plugin/config writes isolated from the
# machine-global ~/.claude.
#
# Dev/test that mutates plugin state (`claude plugin install|uninstall|update`,
# `uvx claude-automata init`) otherwise rewrites the shared
# ~/.claude/plugins/installed_plugins.json and races with concurrent sessions,
# clobbering sibling projects' install records. Everything run through here
# writes under a gitignored, repo-local config dir instead.
#
# Usage:
#   scripts/dev-sandbox.sh claude plugin install ploop@claude-automata --scope project
#   scripts/dev-sandbox.sh uvx --from . claude-automata init
#
# Override the sandbox location with CLAUDE_AUTOMATA_SANDBOX.
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "usage: scripts/dev-sandbox.sh <command> [args...]" >&2
  exit 2
fi

root=$(git rev-parse --show-toplevel)
export CLAUDE_CONFIG_DIR="${CLAUDE_AUTOMATA_SANDBOX:-$root/.dev-sandbox}"
mkdir -p "$CLAUDE_CONFIG_DIR"
echo "[dev-sandbox] CLAUDE_CONFIG_DIR=$CLAUDE_CONFIG_DIR" >&2
exec "$@"
