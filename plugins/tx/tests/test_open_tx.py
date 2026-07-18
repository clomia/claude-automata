import sys

import pytest
from conftest import run

from src import open_tx


def invoke(monkeypatch, slug: str) -> None:
    monkeypatch.setattr(sys, "argv", ["open-tx", slug])
    open_tx.main()


def test_cuts_branch_from_origin_base(gitrepo, tmp_path, monkeypatch, capsys):
    origin = tmp_path / "origin.git"
    run(gitrepo, "clone", "-q", "--bare", ".", str(origin))
    run(gitrepo, "remote", "add", "origin", str(origin))
    invoke(monkeypatch, "my-slug")
    assert "tx-my-slug cut from origin/" in capsys.readouterr().out
    assert run(gitrepo, "rev-parse", "--abbrev-ref", "HEAD") == "tx-my-slug"


def test_refuses_off_base_branch(gitrepo, monkeypatch, capsys):
    run(gitrepo, "checkout", "-q", "-b", "tx-other")
    with pytest.raises(SystemExit) as exc:
        invoke(monkeypatch, "my-slug")
    assert exc.value.code == 1
    assert "not the base" in capsys.readouterr().err


def test_refuses_dirty_tree(gitrepo, monkeypatch, capsys):
    (gitrepo / "tracked.txt").write_text("dirty")
    with pytest.raises(SystemExit) as exc:
        invoke(monkeypatch, "my-slug")
    assert exc.value.code == 1
    assert "not clean" in capsys.readouterr().err


@pytest.mark.parametrize("slug", ["Bad_Slug", "2fa-support"])
def test_rejects_bad_slug(slug, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        invoke(monkeypatch, slug)
    assert exc.value.code == 1
    assert "usage: open-tx" in capsys.readouterr().err
