import re
from pathlib import Path

import pytest

from src import openspec

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SEED_WORKFLOW = PLUGIN_ROOT / "references" / "memory-check.yml"
PIN_RE = re.compile(r"@fission-ai/openspec@(\d+\.\d+\.\d+)")


def test_seed_workflow_pin_matches_src_pin():
    """The one unavoidable pin copy (the seeded workflow) cannot drift from PIN."""
    pins = set(PIN_RE.findall(SEED_WORKFLOW.read_text(encoding="utf-8")))
    assert pins == {openspec.PIN}


def test_repo_workflow_is_byte_identical_to_seed_copy():
    deployed = PLUGIN_ROOT.parents[1] / ".github" / "workflows" / "memory-check.yml"
    if not deployed.exists():
        pytest.skip("repo-root workflow not deployed yet")
    assert deployed.read_bytes() == SEED_WORKFLOW.read_bytes()
