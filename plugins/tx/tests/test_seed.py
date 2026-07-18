import json

import pytest
from conftest import run

from src import seed


def test_repo_root_from_subdir(tmp_path, monkeypatch):
    run(tmp_path, "init", "-q", "-b", "main")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    assert seed.repo_root() == tmp_path


def test_repo_root_refuses_outside_repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        seed.repo_root()
    assert exc.value.code == 1


def test_pin_drifted():
    current = f"npx --yes @fission-ai/openspec@{seed.PIN} validate"
    assert not seed.pin_drifted(current)
    assert seed.pin_drifted("npx --yes @fission-ai/openspec@0.0.1 validate")
    assert seed.pin_drifted("no pin at all")
    assert seed.pin_drifted(f"{current}\nnpx --yes @fission-ai/openspec@9.9.9 x")


def test_seed_workflow_lifecycle(tmp_path, monkeypatch, capsys):
    """Absent -> seeded; present -> untouched; drifted pin -> overwritten whole."""
    monkeypatch.chdir(tmp_path)
    seed.seed_workflow()
    deployed = tmp_path / ".github" / "workflows" / "memory-check.yml"
    assert deployed.read_bytes() == seed.workflow_source().read_bytes()
    assert "seeded memory-check workflow" in capsys.readouterr().out

    seed.seed_workflow()
    assert "workflow present" in capsys.readouterr().out

    deployed.write_text(
        deployed.read_text(encoding="utf-8").replace(seed.PIN, "0.0.1"),
        encoding="utf-8",
    )
    seed.seed_workflow()
    assert "refreshed memory-check workflow" in capsys.readouterr().out
    assert deployed.read_bytes() == seed.workflow_source().read_bytes()


def test_seed_scaffold_skips_when_present(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "openspec").mkdir()
    (tmp_path / "openspec" / "config.yaml").write_text("schema: spec-driven\n")
    seed.seed_scaffold()
    assert "scaffold present" in capsys.readouterr().out


def fake_gh(permissions: tuple[str | None, str], posted: list[str]):
    """run_gh stand-in: no ruleset installed yet; records the POST payload."""

    def run_gh(args: list[str], payload: str | None = None) -> tuple[str | None, str]:
        if args[0] == "repo":
            return "owner/repo\n", ""
        if "actions/permissions" in args[1]:
            return permissions
        if "--method" in args:
            posted.append(payload)
            return "{}", ""
        return "", ""

    return run_gh


def test_protection_skips_checks_rule_when_actions_disabled(monkeypatch):
    posted: list[str] = []
    monkeypatch.setattr(seed, "run_gh", fake_gh(("false\n", ""), posted))
    report = seed.protection_report()
    rules = json.loads(posted[0])["rules"]
    assert "required_status_checks" not in [r["type"] for r in rules]
    assert "checks rule skipped" in report


def test_protection_posts_full_ruleset_when_probe_fails(monkeypatch):
    posted: list[str] = []
    monkeypatch.setattr(seed, "run_gh", fake_gh((None, "HTTP 403"), posted))
    assert seed.protection_report() == "branch protection: attempted"
    assert json.loads(posted[0]) == seed.RULESET
