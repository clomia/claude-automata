from conftest import make_origin_ahead, run, set_origin_head

from src import repo


def test_is_tx_branch():
    assert repo.is_tx_branch("tx-foo")
    assert not repo.is_tx_branch("main")
    assert not repo.is_tx_branch("feature/tx-thing")


def test_base_branch_prefers_origin_head(gitrepo):
    run(gitrepo, "branch", "integration")
    set_origin_head(gitrepo, "integration")
    assert repo.base_branch() == "integration"


def test_base_branch_env_beats_origin_head(gitrepo, monkeypatch):
    set_origin_head(gitrepo, "main")
    monkeypatch.setenv("TXGIT_BASE_BRANCH", "release")
    assert repo.base_branch() == "release"


def test_base_branch_falls_back_to_existing_local(gitrepo):
    # no origin/HEAD; only `main` exists among the fallbacks
    assert repo.base_branch() == "main"


def test_current_branch_tracks_checkout(gitrepo):
    assert repo.current_branch() == "main"
    run(gitrepo, "checkout", "-q", "-b", "tx-demo")
    assert repo.current_branch() == "tx-demo"


def test_base_ahead_count(gitrepo):
    assert repo.base_ahead_count("main") is None  # no remote-tracking ref yet
    make_origin_ahead(gitrepo, "main", 2)
    assert repo.base_ahead_count("main") == 2


def test_pause_marker_gates_sync(gitrepo):
    assert not repo.sync_paused()
    marker = repo.pause_marker()
    assert marker is not None
    marker.touch()
    assert repo.sync_paused()
