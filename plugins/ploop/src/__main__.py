"""python -m src <entry> [args] — run a bundled entry with no install, so no
virtualenv is ever written into the ephemeral plugin cache."""

import sys

from . import docent, main

ENTRIES = {
    "stop": main.stop,
    "pre-tool-use": main.pre_tool_use,
    "subagent-stop": main.subagent_stop,
    "mark-compaction": main.mark_compaction,
    "launch": main.launch,
    "off-command": main.off_command,
    "on-command": main.on_command,
    "docent": docent.resolve,
}

sys.argv = sys.argv[1:]
ENTRIES[sys.argv[0]]()
