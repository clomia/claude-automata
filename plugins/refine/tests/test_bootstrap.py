import pytest

from src import bootstrap


@pytest.fixture
def env(monkeypatch, tmp_path):
    """CLI environment with repomix resolution pinned.

    tempfile.tempdir is pointed into tmp_path so the Agora that main() opens is
    cleaned up with the test (the env-var route is dead — tempfile caches its
    directory before the fixture runs); resolve_repomix is pinned to a bare
    repomix so no network or install is touched.
    """
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "project"))
    monkeypatch.setattr(bootstrap.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: "/usr/bin/repomix" if name == "repomix" else None,
    )


@pytest.mark.parametrize("skill", bootstrap.SKILLS)
def test_resolves_per_skill_paths(monkeypatch, env, capsys, skill):
    """Each skill maps to its own workflow.js, principles.md, and Agora prefix."""
    monkeypatch.setattr("sys.argv", ["bootstrap", skill])
    assert bootstrap.main() == 0
    out = capsys.readouterr().out
    assert f"skills/{skill}/workflow.js" in out
    assert f"skills/{skill}/principles.md" in out
    assert f"refine-{skill}-agora-" in out


@pytest.mark.parametrize("argv", [["bootstrap"], ["bootstrap", "nonsense"]])
def test_invalid_skill_fails_fast(monkeypatch, env, capsys, argv):
    monkeypatch.setattr("sys.argv", argv)
    assert bootstrap.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage:" in captured.err


def test_focus_from_argv(monkeypatch, env, capsys):
    """Focus words after the skill join into a single focusArea."""
    monkeypatch.setattr("sys.argv", ["bootstrap", "code", "auth", "module"])
    bootstrap.main()
    assert '"focusArea": "auth module"' in capsys.readouterr().out


def test_no_focus_is_whole_codebase(monkeypatch, env, capsys):
    """No focus args → empty focusArea (the workflow reads it as whole-codebase)."""
    monkeypatch.setattr("sys.argv", ["bootstrap", "docs"])
    bootstrap.main()
    assert '"focusArea": ""' in capsys.readouterr().out


def test_workflow_call_contract(monkeypatch, env, capsys):
    """The CLI prints a fully resolved Workflow call — scriptPath fixed, args
    carrying every workflow input."""
    monkeypatch.setattr("sys.argv", ["bootstrap", "code", "focus"])
    bootstrap.main()
    out = capsys.readouterr().out
    assert out.strip().startswith("Workflow(")
    assert "scriptPath:" in out
    for key in (
        "focusArea",
        "projectDir",
        "agoraPath",
        "repomixCmd",
        "principlesPath",
        "conventionPath",
    ):
        assert f'"{key}"' in out
    assert "/usr/bin/repomix" in out


@pytest.mark.parametrize(
    ("skill", "expected"),
    [
        (
            "docs",
            f'"conventionPath": "{bootstrap.SKILLS_DIR / "docs" / "docs-surface.md"}"',
        ),
        ("code", '"conventionPath": ""'),
    ],
)
def test_convention_path_follows_file_presence(
    monkeypatch, env, capsys, skill, expected
):
    """File presence decides the convention channel: docs ships docs-surface.md,
    skills without it get an empty string."""
    monkeypatch.setattr("sys.argv", ["bootstrap", skill])
    bootstrap.main()
    assert expected in capsys.readouterr().out
