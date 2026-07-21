"""CLI — `claude-automata init` converges a repository to the ecosystem's prerequisites."""

import argparse
import json
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from claude_automata import plugins, provision, settings


def git_root() -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def own_version() -> str:
    try:
        return version("claude-automata")
    except PackageNotFoundError:
        return "source"


def init() -> int:
    print(f"claude-automata {own_version()}")
    root = git_root()
    if root is None:
        print(
            "error: not inside a git repository — run init at your project root",
            file=sys.stderr,
        )
        return 1

    path = root / ".claude" / "settings.json"
    try:
        current = read_json(path)
    except json.JSONDecodeError as error:
        print(
            f"error: {path} is not valid JSON ({error}) — fix it and rerun",
            file=sys.stderr,
        )
        return 1
    desired = settings.merged(current)
    notes = []
    if desired == current:
        print(f"{'settings':<10} ok {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(desired, indent=2) + "\n")
        print(f"{'settings':<10} written {path}")
        notes.append("restart running Claude Code sessions to pick up the new settings")

    local_path = root / ".claude" / "settings.local.json"
    try:
        local = read_json(local_path)
    except json.JSONDecodeError:
        local = {}
        notes.append(
            f"{local_path} is not valid JSON — could not check it for overrides"
        )
    if conflicts := settings.overridden(local):
        notes.append(
            f"settings.local.json overrides {', '.join(conflicts)} — remove them there, or init's values will not apply"
        )

    outcomes = provision.ensure_all()
    outcomes.append(plugins.ensure_plugins(root))
    for outcome in outcomes:
        print(f"{outcome.tool:<10} {outcome.status} {outcome.note}".rstrip())
    notes += [
        note
        for note in (provision.gh_auth_note(), provision.path_note(outcomes))
        if note
    ]
    for note in notes:
        print(f"{'note':<10} {note}")
    return 1 if any(outcome.status == "failed" for outcome in outcomes) else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="claude-automata",
        description="Setup CLI for the claude-automata ecosystem",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "init",
        help="configure Claude Code settings and install external CLI dependencies",
    )
    parser.parse_args()
    sys.exit(init())
