import io
import json
import sys

import pytest
from conftest import run

from src import protect


def feed(monkeypatch, payload: str | dict) -> None:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr(sys, "stdin", io.StringIO(raw))


def test_target_path_reads_file_path(monkeypatch):
    feed(monkeypatch, {"tool_input": {"file_path": "/a.py"}})
    assert protect.target_path() == "/a.py"


def test_target_path_notebook_fallback(monkeypatch):
    feed(monkeypatch, {"tool_input": {"notebook_path": "/nb.ipynb"}})
    assert protect.target_path() == "/nb.ipynb"


def test_target_path_bad_json(monkeypatch):
    feed(monkeypatch, "}{ not json")
    assert protect.target_path() is None


def test_block_tracked_edit_on_base(gitrepo, monkeypatch):
    feed(monkeypatch, {"tool_input": {"file_path": str(gitrepo / "tracked.txt")}})
    with pytest.raises(SystemExit) as exc:
        protect.main()
    assert exc.value.code == 2


def test_allow_on_tx_branch(gitrepo, monkeypatch):
    run(gitrepo, "checkout", "-q", "-b", "tx-work")
    feed(monkeypatch, {"tool_input": {"file_path": str(gitrepo / "tracked.txt")}})
    assert protect.main() is None


def test_allow_untracked_target_on_base(gitrepo, monkeypatch):
    feed(monkeypatch, {"tool_input": {"file_path": str(gitrepo / "brand-new.py")}})
    assert protect.main() is None


def test_fail_closed_on_base_without_path(gitrepo, monkeypatch):
    feed(monkeypatch, {})  # no target -> cannot prove untracked -> block stands
    with pytest.raises(SystemExit) as exc:
        protect.main()
    assert exc.value.code == 2
