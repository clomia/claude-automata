from datetime import datetime

from conftest import make_origin_ahead, run

from src import state


def test_protected_branch_message_is_standalone():
    messages = state.build_messages("main", "main")
    assert len(messages) == 1
    assert "protected" in messages[0] and "/txgit:tx-open" in messages[0]


def test_clean_tx_branch_has_no_messages(gitrepo):
    run(gitrepo, "checkout", "-q", "-b", "tx-solo")
    assert state.build_messages("tx-solo", "main") == []


def test_base_ahead_message_on_tx_branch(gitrepo):
    run(gitrepo, "checkout", "-q", "-b", "tx-work")
    make_origin_ahead(gitrepo, "main", 2)
    joined = "\n".join(state.build_messages("tx-work", "main"))
    assert "2 PR(s) ahead" in joined


def test_tx_open_time_parses_reflog(gitrepo):
    assert isinstance(state.tx_open_time("main"), datetime)
