"""Deterministic preflight and branch cut for /tx:open.

The open skill states the opened-branch fact; this entry point owns reaching
it.  Fail-closed on a failed fetch: the integrity boundary must
not open on a stale base.
"""

import re
import subprocess
import sys

from src.repo import current_branch, fetch_base, resolve_base_or_exit

# subset of the openspec change-name grammar — keeps slug ≒ change-id satisfiable
SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def main() -> None:
    if len(sys.argv) != 2 or not SLUG_RE.fullmatch(sys.argv[1]):
        print(
            "usage: open-tx <slug> (short kebab-case, starts with a letter)",
            file=sys.stderr,
        )
        raise SystemExit(1)
    slug = sys.argv[1]

    base = resolve_base_or_exit()

    branch = current_branch()
    if branch != base:
        print(
            f"On '{branch}', not the base '{base}' — switch to it "
            "(or close the open transaction) first.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    status = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True
    )
    if status.returncode != 0 or status.stdout.strip():
        print(
            "Working tree is not clean: stash the changes (git stash -u) or drop them first.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    if not fetch_base(base):
        print(
            f"git fetch origin {base} failed — check the remote and retry.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    switch = subprocess.run(
        ["git", "switch", "-c", f"tx-{slug}", f"origin/{base}"],
        capture_output=True,
        text=True,
    )
    if switch.returncode != 0:
        sys.stderr.write(switch.stderr)
        raise SystemExit(1)

    print(f"tx-{slug} cut from origin/{base}")
