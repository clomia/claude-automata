import pytest

from claude_automata import provision


def test_present_tools_are_ok(monkeypatch):
    monkeypatch.setattr(provision.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(provision, "node_major", lambda node: 22)
    assert provision.ensure_gh().status == "ok"
    assert provision.ensure_node().status == "ok"
    assert provision.ensure_repomix().status == "ok"


def test_node_below_20_is_replaced(monkeypatch, tmp_path):
    monkeypatch.setattr(provision.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(provision, "node_major", lambda node: 18)
    monkeypatch.setattr(provision, "latest_node_lts", lambda: "v22.11.0")
    monkeypatch.setattr(provision, "extract", lambda url, into: tmp_path)
    monkeypatch.setattr(provision, "link", lambda binary, name: None)
    outcome = provision.ensure_node()
    assert outcome.status == "installed"
    assert "below 20" in outcome.note


def test_npm_env_prefers_local_bin():
    assert provision.npm_env()["PATH"].startswith(str(provision.LOCAL_BIN))


def test_repomix_installs_into_user_area_prefix(monkeypatch):
    monkeypatch.setattr(
        provision.shutil,
        "which",
        lambda name: None if name == "repomix" else f"/usr/bin/{name}",
    )
    commands = []

    def record(cmd, **kwargs):
        commands.append(cmd)

        class Done:
            stdout = ""

        return Done()

    monkeypatch.setattr(provision.subprocess, "run", record)
    monkeypatch.setattr(provision, "link", lambda binary, name: None)
    outcome = provision.ensure_repomix()
    assert outcome.status == "installed"
    install = commands[0]
    assert "--prefix" in install
    assert install[install.index("--prefix") + 1] == str(provision.SHARE / "npm")


def test_asset_names_match_official_distributions():
    assert (
        provision.gh_asset("linux", "x64", "2.62.0") == "gh_2.62.0_linux_amd64.tar.gz"
    )
    assert (
        provision.gh_asset("darwin", "arm64", "2.62.0") == "gh_2.62.0_macOS_arm64.zip"
    )
    assert (
        provision.node_asset("linux", "x64", "v22.17.0")
        == "node-v22.17.0-linux-x64.tar.gz"
    )
    assert (
        provision.node_asset("darwin", "arm64", "v22.17.0")
        == "node-v22.17.0-darwin-arm64.tar.gz"
    )


def test_unsupported_platform_fails_with_guidance(monkeypatch):
    monkeypatch.setattr(provision.shutil, "which", lambda name: None)
    monkeypatch.setattr(provision, "target", lambda: None)
    for outcome in (provision.ensure_gh(), provision.ensure_node()):
        assert outcome.status == "failed"
        assert "manually" in outcome.note


def test_pick_lts_takes_newest_lts_at_or_above_20():
    releases = [
        {"version": "v23.1.0", "lts": False},
        {"version": "v22.11.0", "lts": "Jod"},
        {"version": "v20.18.0", "lts": "Iron"},
    ]
    assert provision.pick_lts(releases) == "v22.11.0"
    with pytest.raises(LookupError):
        provision.pick_lts([{"version": "v18.20.0", "lts": "Hydrogen"}])
