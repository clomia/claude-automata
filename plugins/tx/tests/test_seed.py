import json

import pytest
from conftest import mirror_origin_head, run

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


def test_seed_workflow_lifecycle(tmp_path, monkeypatch, capsys):
    """Absent -> seeded; identical -> untouched; any byte drift -> overwritten whole."""
    monkeypatch.chdir(tmp_path)
    seed.seed_workflow()
    deployed = tmp_path / ".github" / "workflows" / "memory-check.yml"
    assert deployed.read_bytes() == seed.workflow_source().read_bytes()
    assert "seeded memory-check workflow" in capsys.readouterr().out

    seed.seed_workflow()
    assert "workflow present" in capsys.readouterr().out

    deployed.write_bytes(
        deployed.read_bytes().replace(b"docs form: clean", b"docs form: ok")
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


def test_workflow_on_base_probe(gitrepo):
    assert seed.workflow_on_base() is False
    deployed = gitrepo / ".github" / "workflows" / "memory-check.yml"
    deployed.parent.mkdir(parents=True)
    deployed.write_text("name: memory-check\n")
    run(gitrepo, "add", "-A")
    run(gitrepo, "commit", "-q", "-m", "wf")
    mirror_origin_head(gitrepo, "main")
    assert seed.workflow_on_base() is True


def test_workflow_on_base_unresolvable(tmp_path, monkeypatch):
    run(tmp_path, "init", "-q", "-b", "main")
    monkeypatch.chdir(tmp_path)
    assert seed.workflow_on_base() is None


def fake_gh(state: dict):
    """run_gh stand-in over `state`: `rules` is the installed ruleset's rule
    types (None = no ruleset); POST/PUT payloads are recorded."""

    def run_gh(args: list[str], payload: str | None = None) -> tuple[str | None, str]:
        if args[0] == "repo":
            return "owner/repo\n", ""
        endpoint = args[1]
        if "actions/permissions" in endpoint:
            return state["permissions"]
        if "--method" in args:
            state.setdefault("posted" if "POST" in args else "put", []).append(payload)
            return "{}", ""
        if endpoint.endswith("/rulesets"):
            return ("1\n", "") if state["rules"] is not None else ("", "")
        return json.dumps(state["rules"]), ""

    return run_gh


def test_protection_defers_checks_rule_before_workflow_on_base(monkeypatch):
    state = {"rules": None, "permissions": ("true\n", "")}
    monkeypatch.setattr(seed, "run_gh", fake_gh(state))
    monkeypatch.setattr(seed, "workflow_on_base", lambda: False)
    report = seed.protection_report()
    rules = json.loads(state["posted"][0])["rules"]
    assert seed.CHECKS_RULE not in [r["type"] for r in rules]
    assert "checks rule deferred" in report


def test_protection_skips_checks_rule_when_actions_disabled(monkeypatch):
    state = {"rules": None, "permissions": ("false\n", "")}
    monkeypatch.setattr(seed, "run_gh", fake_gh(state))
    monkeypatch.setattr(seed, "workflow_on_base", lambda: True)
    report = seed.protection_report()
    rules = json.loads(state["posted"][0])["rules"]
    assert seed.CHECKS_RULE not in [r["type"] for r in rules]
    assert "checks rule skipped" in report


def test_protection_posts_full_ruleset_when_probes_fail(monkeypatch):
    state = {"rules": None, "permissions": (None, "HTTP 403")}
    monkeypatch.setattr(seed, "run_gh", fake_gh(state))
    monkeypatch.setattr(seed, "workflow_on_base", lambda: None)
    assert seed.protection_report() == "branch protection: attempted"
    assert json.loads(state["posted"][0]) == seed.RULESET


def test_protection_upgrades_reduced_ruleset_when_conditions_hold(monkeypatch):
    state = {
        "rules": ["pull_request", "non_fast_forward", "deletion"],
        "permissions": ("true\n", ""),
    }
    monkeypatch.setattr(seed, "run_gh", fake_gh(state))
    monkeypatch.setattr(seed, "workflow_on_base", lambda: True)
    report = seed.protection_report()
    assert json.loads(state["put"][0]) == seed.RULESET
    assert "upgraded" in report


def test_protection_never_downgrades_full_ruleset(monkeypatch):
    state = {
        "rules": ["pull_request", "non_fast_forward", "deletion", seed.CHECKS_RULE],
        "permissions": ("false\n", ""),
    }
    monkeypatch.setattr(seed, "run_gh", fake_gh(state))
    monkeypatch.setattr(seed, "workflow_on_base", lambda: False)
    assert seed.protection_report() == "branch protection: present"
    assert "put" not in state


def test_protection_reduced_stays_while_conditions_unmet(monkeypatch):
    state = {"rules": ["pull_request"], "permissions": ("true\n", "")}
    monkeypatch.setattr(seed, "run_gh", fake_gh(state))
    monkeypatch.setattr(seed, "workflow_on_base", lambda: False)
    assert "deferred" in seed.protection_report()
    assert "put" not in state
