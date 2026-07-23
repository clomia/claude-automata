"""python -m src <entry> [args] — run a bundled entry with no install, so no
virtualenv is ever written into the ephemeral plugin cache."""

import sys

from . import commit_guard, open_tx, openspec, pause, protect, repo, seed, state, sync

ENTRIES = {
    "base": repo.print_base,
    "base-commit-block": commit_guard.main,
    "branch-protect-block": protect.main,
    "branch-state-warn": state.main,
    "git-sync": sync.main,
    "git-sync-off": pause.off,
    "git-sync-on": pause.on,
    "open-tx": open_tx.main,
    "openspec": openspec.main,
    "seed": seed.main,
}

sys.argv = sys.argv[1:]
ENTRIES[sys.argv[0]]()
