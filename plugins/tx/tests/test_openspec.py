import datetime
import os
import re
import sys
from pathlib import Path

import pytest

from src import openspec

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SEED_WORKFLOW = PLUGIN_ROOT / "references" / "memory-check.yml"
PIN_RE = re.compile(r"@fission-ai/openspec@(\d+\.\d+\.\d+)")


def test_seed_workflow_pin_matches_src_pin():
    """The one unavoidable pin copy (the seeded workflow) cannot drift from PIN."""
    pins = set(PIN_RE.findall(SEED_WORKFLOW.read_text(encoding="utf-8")))
    assert pins == {openspec.PIN}


def test_repo_workflow_is_byte_identical_to_seed_copy():
    deployed = PLUGIN_ROOT.parents[1] / ".github" / "workflows" / "memory-check.yml"
    if not deployed.exists():
        pytest.skip("repo-root workflow not deployed yet")
    assert deployed.read_bytes() == SEED_WORKFLOW.read_bytes()


def test_main_outside_git_repo_exits_loud(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        openspec.main()
    assert excinfo.value.code == 1
    assert "git repository" in capsys.readouterr().err


def test_main_without_scaffold_exits_loud_with_toplevel(gitrepo, capsys):
    with pytest.raises(SystemExit) as excinfo:
        openspec.main()
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "no openspec scaffold" in err
    assert str(gitrepo.resolve()) in err


def test_main_anchors_exec_at_toplevel(gitrepo, monkeypatch):
    (gitrepo / "openspec").mkdir()
    (gitrepo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
    subdir = gitrepo / "sub"
    subdir.mkdir()
    monkeypatch.chdir(subdir)
    seen = {}

    def capture(file, args):
        seen["cwd"] = os.getcwd()

    monkeypatch.setattr(os, "execvp", capture)
    openspec.main()
    assert seen["cwd"] == str(gitrepo.resolve())


def scaffold_with_todays_archive(gitrepo, change_id):
    (gitrepo / "openspec").mkdir()
    (gitrepo / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
    archived = f"{datetime.date.today().isoformat()}-{change_id}"
    (gitrepo / "openspec" / "changes" / "archive" / archived).mkdir(parents=True)


def test_main_archive_clash_exits_before_exec(gitrepo, monkeypatch, capsys):
    """A same-day re-archive is cut before the CLI's non-atomic merge-then-move."""
    scaffold_with_todays_archive(gitrepo, "x")
    monkeypatch.setattr(sys, "argv", ["openspec", "archive", "x", "--yes"])
    with pytest.raises(SystemExit) as excinfo:
        openspec.main()
    assert excinfo.value.code == 1
    assert "already exists" in capsys.readouterr().err


def test_main_archive_without_clash_reaches_exec(gitrepo, monkeypatch):
    scaffold_with_todays_archive(gitrepo, "x")
    monkeypatch.setattr(sys, "argv", ["openspec", "archive", "y", "--yes"])
    seen = {}

    def capture(file, args):
        seen["args"] = args

    monkeypatch.setattr(os, "execvp", capture)
    openspec.main()
    assert seen["args"][-3:] == ["archive", "y", "--yes"]
