import pytest

from src import bootstrap


@pytest.fixture
def env(monkeypatch, tmp_path):
    """CLI environment with repomix resolution pinned.

    TMPDIR is redirected into tmp_path so the Agora that main() opens is cleaned
    up with the test; resolve_repomix is pinned to a bare repomix so no network
    or install is touched.
    """
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "project"))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: "/usr/bin/repomix" if name == "repomix" else None,
    )


def test_focus_from_argv(monkeypatch, env, capsys):
    """Focus words join into a single focusArea."""
    monkeypatch.setattr("sys.argv", ["bootstrap", "auth", "module"])
    bootstrap.main()
    assert '"focusArea": "auth module"' in capsys.readouterr().out


def test_no_focus_is_whole_codebase(monkeypatch, env, capsys):
    """No args → empty focusArea (the workflow reads it as whole-codebase)."""
    monkeypatch.setattr("sys.argv", ["bootstrap"])
    bootstrap.main()
    assert '"focusArea": ""' in capsys.readouterr().out


def test_workflow_call_contract(monkeypatch, env, capsys):
    """The CLI prints a fully resolved Workflow call — scriptPath fixed, args
    carrying every workflow input — with no leftover workflowScript key."""
    monkeypatch.setattr("sys.argv", ["bootstrap", "focus"])
    bootstrap.main()
    out = capsys.readouterr().out
    assert out.strip().startswith("Workflow(")
    assert "scriptPath:" in out
    assert "refine-architecture.js" in out
    for key in ("focusArea", "projectDir", "agoraPath", "repomixCmd", "principlesPath"):
        assert f'"{key}"' in out
    assert "/usr/bin/repomix" in out
    assert '"workflowScript"' not in out
