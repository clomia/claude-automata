"""Plugins — converge the marketplace and plugin cache via the claude CLI.

Settings declare the adoption and carry it to collaborators through the
repository; this module converges the current machine deterministically, so a
single restart loads every component — skills included — from an
already-populated cache.  Without the claude CLI the declaration alone remains:
the next session start installs lazily, and a missing-skills session heals with
one /reload-plugins — the deferred note says so.  `claude plugin update` is
deliberately unused: it does not auto-detect scope and exits 0 on failure.
"""

import json
import shutil
import subprocess
from pathlib import Path

from claude_automata.provision import Outcome
from claude_automata.settings import MARKETPLACE, MARKETPLACE_REPO, plugin_names

DEFERRED_NOTE = (
    "claude CLI not on PATH — plugins install at the next session start; "
    "if skills are missing after restarting, run /reload-plugins once"
)


def run_claude(args: list[str], cwd: Path) -> tuple[str | None, str]:
    """claude runner — (stdout, "") on success, (None, one-line reason) on failure."""
    try:
        result = subprocess.run(
            ["claude", *args], cwd=cwd, capture_output=True, text=True, check=False
        )
    except OSError:
        return None, "claude not found"
    if result.returncode != 0:
        lines = (result.stderr.strip() or result.stdout.strip()).splitlines()
        return None, lines[-1] if lines else f"claude exited {result.returncode}"
    return result.stdout, ""


def installed_here(root: Path) -> set[str] | None:
    """Plugin names already installed for `root` at project scope.  None when the
    probe fails — fall through to installing everything (install is idempotent)."""
    out, _ = run_claude(["plugin", "list", "--json"], cwd=root)
    if out is None:
        return None
    try:
        return {
            entry["id"].removesuffix(f"@{MARKETPLACE}")
            for entry in json.loads(out)
            if entry.get("id", "").endswith(f"@{MARKETPLACE}")
            and entry.get("scope") == "project"
            and Path(entry.get("projectPath", "")) == root
        }
    except json.JSONDecodeError, TypeError, AttributeError:
        return None


def ensure_plugins(root: Path) -> Outcome:
    """One idempotent convergence of the plugin cache for the repo at `root`."""
    if shutil.which("claude") is None:
        return Outcome("plugins", "deferred", DEFERRED_NOTE)
    _, reason = run_claude(["plugin", "marketplace", "add", MARKETPLACE_REPO], cwd=root)
    if reason:
        return Outcome("plugins", "failed", f"marketplace add: {reason}")
    _, reason = run_claude(["plugin", "marketplace", "update", MARKETPLACE], cwd=root)
    if reason:
        return Outcome("plugins", "failed", f"marketplace update: {reason}")
    present = installed_here(root)
    missing = [
        name for name in plugin_names() if present is None or name not in present
    ]
    if not missing:
        return Outcome("plugins", "ok", "all installed (project scope)")
    installed, failures = [], []
    for name in missing:
        _, reason = run_claude(
            ["plugin", "install", f"{name}@{MARKETPLACE}", "--scope", "project"],
            cwd=root,
        )
        if reason:
            failures.append(f"{name}: {reason}")
        else:
            installed.append(name)
    if failures:
        return Outcome("plugins", "failed", "; ".join(failures))
    return Outcome("plugins", "installed", f"{', '.join(installed)} (project scope)")
