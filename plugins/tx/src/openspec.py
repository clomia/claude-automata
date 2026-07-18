"""Pinned openspec CLI — the version pin's single home.

PIN is the canon: every consumer calls this wrapper (skills via
`uv run --project <plugin> openspec …`), so the version appears in no skill
body.  The one unavoidable copy — the seeded workflow in references/ — is
locked to this constant by tests/test_openspec.py.  The coupling to openspec
is invocation, not installation: npx fetches and runs the pinned dist on
demand, leaving nothing behind in the target repository.
"""

import os
import sys
from typing import NoReturn

PIN = "1.6.0"


def main() -> NoReturn:
    try:
        os.execvp("npx", ["npx", "--yes", f"@fission-ai/openspec@{PIN}", *sys.argv[1:]])
    except FileNotFoundError:
        print("npx not found — openspec requires Node.js >= 20.", file=sys.stderr)
        sys.exit(1)
