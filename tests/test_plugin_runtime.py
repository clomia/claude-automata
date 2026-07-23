"""Cross-plugin runtime invariants — the plugin install cache is execute-only.

Every bin runner must be hermetic: launched from a pristine copy of the plugin
(as Claude Code launches it from the cache), with no CLAUDE_* variable in the
environment, a hostile PYTHONPATH, and a cwd holding a decoy `src` package,
the plugin's own entry must run, the decoy must never be reached, and the
plugin tree must be byte-for-byte untouched afterwards.  And no plugin may
require an install step — no dependencies, no `uv sync`, no `uv run --project`
anywhere in the tree.
"""

import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

CASES = {
    "ploop": (
        "bin/ploop-hook",
        lambda tmp: ["docent", "--data-dir", str(tmp), "--project-dir", str(tmp)],
        "No loops",
    ),
    "refine": (
        "bin/refine",
        lambda tmp: ["bootstrap", "__probe__"],
        "usage: bootstrap",
    ),
    "tx": ("bin/tx-hook", lambda tmp: ["base"], "origin"),
    "version-up-alert": (
        "bin/version-up-alert-hook",
        lambda tmp: ["update-check"],
        "",
    ),
}


@pytest.mark.parametrize("plugin", sorted(CASES))
def test_runner_is_hermetic(plugin, tmp_path):
    runner, args, marker = CASES[plugin]
    plugin_copy = tmp_path / "cache-copy"
    shutil.copytree(
        REPO / "plugins" / plugin,
        plugin_copy,
        ignore=shutil.ignore_patterns(
            ".venv", ".pytest_cache", ".ruff_cache", "__pycache__"
        ),
    )
    decoy = tmp_path / "src"
    decoy.mkdir()
    (decoy / "__init__.py").write_text("")
    (decoy / "__main__.py").write_text("print('DECOY'); raise SystemExit(7)\n")

    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env["PYTHONPATH"] = str(tmp_path)

    def tree():
        return sorted(p.relative_to(plugin_copy) for p in plugin_copy.rglob("*"))

    before = tree()
    result = subprocess.run(
        [str(plugin_copy / runner), *args(tmp_path)],
        cwd=tmp_path,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=180,
    )

    output = result.stdout + result.stderr
    assert "DECOY" not in output, output
    if marker:
        assert marker in output, output
    else:
        assert result.returncode == 0 and result.stdout == "", output
    assert tree() == before, "runner wrote into the plugin tree"


def test_plugins_carry_no_install_step():
    tracked = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "plugins"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    for name in tracked:
        text = (REPO / name).read_text(errors="ignore")
        assert "uv sync" not in text, name
        assert "uv run --project" not in text, name
    for pyproject in sorted(REPO.glob("plugins/*/pyproject.toml")):
        project = tomllib.loads(pyproject.read_text())["project"]
        assert project["dependencies"] == [], pyproject
