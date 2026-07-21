"""Idempotent seed — germinate the memory substrate in a target repository.

Every path is repository-root-relative: main() anchors itself at
`git rev-parse --show-toplevel` before the first step, so a seed run from a
subdirectory can never nest a second scaffold — and outside a repository it
refuses (exit 1) instead of planting into the void.  Three steps, each
converging on its final shape and reporting one line on stdout:

- openspec scaffold: absent -> `init --tools none` under the pinned version.
  Plan cannot run without the scaffold (the openspec wrapper refuses
  un-scaffolded roots — the bare CLI would silently self-scaffold an implicit
  root), so a failed init aborts the seed (exit 1) with the CLI's stderr
  relayed for the open skill to surface.
- memory-check workflow: seed-owned whole — absent, or differing from the
  plugin's copy in any byte -> written whole from it, so a content change
  never waits on a pin drift to propagate.
- server-side branch protection: one idempotent convergence attempt.  The
  required-status-checks rule binds only where it can report — Actions
  enabled and the memory-check workflow already on `origin/<base>` —
  otherwise the ruleset lands (or stays) active without it, keeping PRs,
  non-fast-forward, and deletion enforced, and a later seed run converges it
  upward once both hold.  Convergence is upward only — a full ruleset is
  never reduced — and the ruleset, like the workflow, is seed-owned: the
  upgrade writes the canonical shape whole.  An attempt, not a guarantee:
  any failure — no gh, no permission, API refusal — is one reported line and
  the seed continues.  Where GitHub itself withholds rulesets — a private
  repo on a free plan — the refusal is not a failure but a terminal state,
  reported as unsupported; the same stateless attempt converges upward if
  visibility or plan ever changes.  What the ruleset buys is not immutability
  but making bypass an explicit, auditable API call.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from src.openspec import NPX_MISSING, PIN
from src.repo import base_branch, git

WORKFLOW_TARGET = Path(".github/workflows/memory-check.yml")
RULESET_NAME = "tx-base-protection"
CHECKS_RULE = "required_status_checks"

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
            "type": CHECKS_RULE,
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
    # A store-pointer root (config.yaml `store:`) also counts as present: tx assumes a
    # repo-local openspec root — store-externalized repos are out of scope (loud-fail).
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


def seed_workflow() -> None:
    source = workflow_source()
    if not WORKFLOW_TARGET.exists():
        WORKFLOW_TARGET.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, WORKFLOW_TARGET)
        print("seeded memory-check workflow")
        return
    if WORKFLOW_TARGET.read_bytes() != source.read_bytes():
        shutil.copyfile(source, WORKFLOW_TARGET)
        print("refreshed memory-check workflow")
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


def failure_report(reason: str) -> str:
    """The report line for a failed gh call — GitHub's plan-gate refusal
    (rulesets withheld from free-plan private repos) is a terminal satisfied
    state, not a failure to converge later."""
    if "Upgrade to GitHub Pro" in reason:
        return "branch protection: unsupported (private repo on a free plan)"
    return f"branch protection: unavailable ({reason})"


def actions_enabled(slug: str) -> bool | None:
    """None when the probe fails — fall through to the full ruleset (no new failure mode)."""
    out, _ = run_gh(["api", f"repos/{slug}/actions/permissions", "--jq", ".enabled"])
    return None if out is None else out.strip() == "true"


def workflow_on_base() -> bool | None:
    """Whether the seeded workflow is on `origin/<base>` — the required checks
    can only report once it is.  None when the base is unresolvable — fall
    through to the full ruleset (no new failure mode)."""
    base = base_branch()
    if base is None:
        return None
    return (
        git("cat-file", "-e", f"origin/{base}:{WORKFLOW_TARGET.as_posix()}") is not None
    )


def reduced(ruleset: dict) -> dict:
    return {
        **ruleset,
        "rules": [r for r in ruleset["rules"] if r["type"] != CHECKS_RULE],
    }


def desired_shape(slug: str) -> tuple[dict, str]:
    """The ruleset shape to write and its deferral note — empty note means full."""
    if workflow_on_base() is False:
        return reduced(RULESET), "checks rule deferred — workflow not on base yet"
    if actions_enabled(slug) is False:
        return reduced(RULESET), "checks rule skipped — Actions disabled"
    return RULESET, ""


def protection_report() -> str:
    """One idempotent server-side convergence attempt; the one-line outcome to print."""
    slug, reason = run_gh(
        ["repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]
    )
    if slug is None:
        return failure_report(reason)
    slug = slug.strip()
    found, reason = run_gh(
        [
            "api",
            f"repos/{slug}/rulesets",
            "--jq",
            f'.[] | select(.name == "{RULESET_NAME}") | .id',
        ]
    )
    if found is None:
        return failure_report(reason)
    if not found.strip():
        shape, note = desired_shape(slug)
        created, reason = run_gh(
            ["api", f"repos/{slug}/rulesets", "--method", "POST", "--input", "-"],
            payload=json.dumps(shape),
        )
        if created is None:
            return failure_report(reason)
        return (
            f"branch protection: attempted ({note})"
            if note
            else "branch protection: attempted"
        )
    ruleset_id = found.strip().splitlines()[0]
    rule_types, reason = run_gh(
        ["api", f"repos/{slug}/rulesets/{ruleset_id}", "--jq", "[.rules[].type]"]
    )
    if rule_types is None:
        return failure_report(reason)
    if CHECKS_RULE in rule_types:
        return "branch protection: present"
    shape, note = desired_shape(slug)
    if note:
        return f"branch protection: present ({note})"
    upgraded, reason = run_gh(
        [
            "api",
            f"repos/{slug}/rulesets/{ruleset_id}",
            "--method",
            "PUT",
            "--input",
            "-",
        ],
        payload=json.dumps(shape),
    )
    if upgraded is None:
        return failure_report(reason)
    return "branch protection: upgraded (required checks added)"


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
