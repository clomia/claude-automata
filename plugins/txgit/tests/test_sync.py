from src import sync
from src.sync import DEDUPE_TTL_SECONDS


def test_parse_state_valid():
    state = sync.parse_state(
        '{"last_fetch_ts": 1.5, "last_announced_origin_sha": "abc", "last_announced_ts": 2.0}'
    )
    assert state == {
        "last_fetch_ts": 1.5,
        "last_announced_origin_sha": "abc",
        "last_announced_ts": 2.0,
    }


def test_parse_state_rejects_malformed_and_nonfinite():
    assert sync.parse_state("") == {}
    assert sync.parse_state("not json") == {}
    assert sync.parse_state("[1, 2]") == {}  # not a dict
    assert sync.parse_state('{"last_fetch_ts": true}') == {}  # bool is not a timestamp
    assert sync.parse_state('{"last_fetch_ts": NaN}') == {}  # non-finite rejected


def test_should_announce_none_when_not_ahead():
    state = sync.SyncState()
    assert sync.should_announce(state, 0, "sha", "main", 1000.0) is None
    assert state == {}


def test_should_announce_fresh_updates_state():
    state = sync.SyncState()
    reason = sync.should_announce(state, 2, "sha1", "main", 1000.0)
    assert reason is not None and "2" in reason and "main" in reason
    assert state["last_announced_origin_sha"] == "sha1"
    assert state["last_announced_ts"] == 1000.0


def test_should_announce_dedupes_same_sha_within_window():
    state = sync.SyncState(last_announced_origin_sha="sha1", last_announced_ts=1000.0)
    assert (
        sync.should_announce(state, 1, "sha1", "main", 1000.0 + DEDUPE_TTL_SECONDS - 1)
        is None
    )


def test_should_announce_reannounces_after_window():
    state = sync.SyncState(last_announced_origin_sha="sha1", last_announced_ts=1000.0)
    assert (
        sync.should_announce(state, 1, "sha1", "main", 1000.0 + DEDUPE_TTL_SECONDS + 1)
        is not None
    )


def test_should_announce_new_sha_announces_immediately():
    state = sync.SyncState(last_announced_origin_sha="sha1", last_announced_ts=1000.0)
    assert sync.should_announce(state, 1, "sha2", "main", 1000.0 + 1) is not None


def test_is_stop_hook_active():
    assert sync.is_stop_hook_active('{"stop_hook_active": true}')
    assert not sync.is_stop_hook_active("{}")
    assert not sync.is_stop_hook_active("garbage")


def test_build_reason_mentions_base_and_count():
    reason = sync.build_reason(3, "develop")
    assert "3" in reason and "develop" in reason
