"""python -m src <entry> [args] — run a bundled entry with no install, so no
virtualenv is ever written into the ephemeral plugin cache."""

import sys

from . import updater

ENTRIES = {
    "update-check": updater.check_for_update,
}

sys.argv = sys.argv[1:]
ENTRIES[sys.argv[0]]()
