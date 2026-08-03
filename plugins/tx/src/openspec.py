"""Pinned openspec CLI — the version pin's single home.

PIN is the canon: every consumer calls this wrapper (skills via
`"${CLAUDE_PLUGIN_ROOT}/bin/tx-hook" openspec …`), so the version appears in no
skill body.  The one unavoidable copy — the seeded workflow in references/ — is
locked to this constant by tests/test_openspec.py.  The coupling to openspec
is invocation, not installation: npx fetches and runs the pinned dist on
demand, leaving nothing behind in the target repository.

Anchored at the git toplevel with a scaffold check — a stray cwd inside
another scaffolded repository still resolves there (no session-repo
reference exists in the Bash env); every other stray class fails loud.
"""

import datetime
import os
import sys
from pathlib import Path
from typing import NoReturn

from src.repo import git

PIN = "1.7.0"
NPX_MISSING = "npx not found — openspec requires Node.js >= 22."


def main() -> NoReturn:
    root = git("rev-parse", "--show-toplevel")
    if root is None:
        print(
            "openspec commands run inside a git repository — the cwd is outside one.",
            file=sys.stderr,
        )
        sys.exit(1)
    os.chdir(root)
    if not Path("openspec/config.yaml").exists():
        print(
            f"no openspec scaffold at {root} — seed it via /tx:open, "
            "or cd back to the project repository.",
            file=sys.stderr,
        )
        sys.exit(1)
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "archive" and not args[1].startswith("-"):
        clash = (
            Path("openspec/changes/archive")
            / f"{datetime.date.today().isoformat()}-{args[1]}"
        )
        if clash.exists():
            print(
                f"archive '{clash.name}' already exists — the CLI would merge specs "
                "then fail midway. Rename the change to a fresh id "
                f"(mv openspec/changes/{args[1]} …) and retry.",
                file=sys.stderr,
            )
            sys.exit(1)
    try:
        os.execvp("npx", ["npx", "--yes", f"@fission-ai/openspec@{PIN}", *sys.argv[1:]])
    except FileNotFoundError:
        print(NPX_MISSING, file=sys.stderr)
        sys.exit(1)
