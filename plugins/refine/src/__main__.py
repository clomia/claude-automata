"""python -m src <entry> [args] — run a bundled entry with no install, so no
virtualenv is ever written into the ephemeral plugin cache."""

import sys

from . import bootstrap, guard

ENTRIES = {
    "bootstrap": bootstrap.main,
    "arm": guard.arm,
    "guard": guard.guard,
}

sys.argv = sys.argv[1:]
ENTRIES[sys.argv[0]]()
