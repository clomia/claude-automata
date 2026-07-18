"""Idempotent seed — germinate the memory substrate in a target repository.

Every path is repository-root-relative: main() anchors itself at
`git rev-parse --show-toplevel` before the first step, so a seed run from a
subdirectory can never nest a second scaffold — and outside a repository it
refuses (exit 1) instead of planting into the void.  Three steps, each
converging on presence and reporting one line on stdout:

- openspec scaffold: absent -> `init --tools none` under the pinned version.
  Plan cannot run without the scaffold, so a failed init aborts the seed
  (exit 1) with the CLI's stderr relayed for the open skill to surface.
- memory-check workflow: absent -> copied whole from this plugin's
  references/; present with a drifted pin -> overwritten whole, so a stale
  seed never propagates its pin.
- server-side branch protection: one idempotent attempt (skipped when the
  `tx-base-protection` ruleset already exists).  An attempt, not a guarantee:
  any failure — no gh, no permission, API refusal — is one reported line and
  the seed continues.  What the ruleset buys is not immutability but making
  bypass an explicit, auditable API call.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from src.openspec import NPX_MISSING, PIN
from src.repo import git

WORKFLOW_TARGET = Path(".github/workflows/memory-check.yml")
OPENSPEC_PIN_RE = re.compile(r"@fission-ai/openspec@(\d+\.\d+\.\d+)")
RULESET_NAME = "tx-base-protection"

RULESET = {
    "name": RULESET_NAME,
    "target": "branch",
    "enforcement": "active",
    "bypass_actors": [],
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
    "rules": [
        {
            "type": "pull_request",
            "parameters": {
                "required_approving_review_count": 0,
                "dismiss_stale_reviews_on_push": False,
                "require_code_owner_review": False,
                "require_last_push_approval": False,
                "required_review_thread_resolution": False,
            },
        },
        {"type": "non_fast_forward"},
        {"type": "deletion"},
        {
            "type": "required_status_checks",
            "parameters": {
                # strict up-to-date closes the post-rebase-scan race server-side by
                # forcing a re-rebase (and so a re-scan); close rebases anyway.
                "strict_required_status_checks_policy": True,
                "required_status_checks": [
                    {"context": "openspec-validate"},
                    {"context": "docs-form-check"},
                ],
            },
        },
    ],
}


def seed_scaffold() -> None:
    if Path("openspec/config.yaml").exists():
        print("scaffold present")
        return
    try:
        result = subprocess.run(
            ["npx", "--yes", f"@fission-ai/openspec@{PIN}", "init", "--tools", "none"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        print(NPX_MISSING, file=sys.stderr)
        raise SystemExit(1)
    if result.returncode != 0:
        print(f"openspec init failed (exit {result.returncode})", file=sys.stderr)
        sys.stderr.write(result.stderr or result.stdout)
        raise SystemExit(1)
    print("seeded openspec scaffold")


def workflow_source() -> Path:
    """The seed copy shipped with the plugin."""
    return Path(__file__).resolve().parents[1] / "references" / "memory-check.yml"


def pin_drifted(workflow_text: str, pin: str = PIN) -> bool:
    """Whether a deployed workflow must be overwritten with the seed copy.

    The workflow is seed-owned: every openspec pin in it must equal `pin`.
    A different pin, an extra one, or none at all is drift — overwriting whole
    keeps one converged artifact instead of patching versions in place.
    """
    return set(OPENSPEC_PIN_RE.findall(workflow_text)) != {pin}


def seed_workflow() -> None:
    if not WORKFLOW_TARGET.exists():
        WORKFLOW_TARGET.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(workflow_source(), WORKFLOW_TARGET)
        print("seeded memory-check workflow")
        return
    if pin_drifted(WORKFLOW_TARGET.read_text(encoding="utf-8")):
        shutil.copyfile(workflow_source(), WORKFLOW_TARGET)
        print("refreshed memory-check workflow (pin drift)")
        return
    print("workflow present")


def run_gh(args: list[str], payload: str | None = None) -> tuple[str | None, str]:
    """gh runner — (stdout, "") on success, (None, one-line reason) on failure."""
    try:
        result = subprocess.run(
            ["gh", *args], input=payload, capture_output=True, text=True, check=False
        )
    except OSError:
        return None, "gh not found"
    if result.returncode != 0:
        stderr_lines = result.stderr.strip().splitlines()
        return None, stderr_lines[
            0
        ] if stderr_lines else f"gh exited {result.returncode}"
    return result.stdout, ""


def protection_report() -> str:
    """One idempotent server-side attempt; the one-line outcome to print."""
    slug, reason = run_gh(
        ["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]
    )
    if slug is None:
        return f"branch protection: unavailable ({reason})"
    names, reason = run_gh(
        ["api", f"repos/{slug.strip()}/rulesets", "--jq", ".[].name"]
    )
    if names is None:
        return f"branch protection: unavailable ({reason})"
    if RULESET_NAME in names.splitlines():
        return "branch protection: present"
    created, reason = run_gh(
        ["api", f"repos/{slug.strip()}/rulesets", "--method", "POST", "--input", "-"],
        payload=json.dumps(RULESET),
    )
    if created is None:
        return f"branch protection: unavailable ({reason})"
    return "branch protection: attempted"


def repo_root() -> Path:
    out = git("rev-parse", "--show-toplevel")
    if out is None:
        print("seed requires a git repository.", file=sys.stderr)
        raise SystemExit(1)
    return Path(out)


def main() -> None:
    os.chdir(repo_root())
    seed_scaffold()
    seed_workflow()
    print(protection_report())


if __name__ == "__main__":
    main()
