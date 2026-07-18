"""CLI — print the fully resolved Workflow tool call for a refine run.

Every refine skill body runs `bootstrap <skill>` and executes the printed
Workflow(...) call verbatim, so a single CLI covers both entry paths: a user
typing /refine:<skill> and the model invoking the skill as a tool. (A
UserPromptExpansion hook would catch only the first — it fires on user-typed
commands alone; the model's tool call fires PreToolUse instead, so one
skill-run CLI is simpler than two hooks.)

It resolves a repomix runner that works on this machine, opens a private Agora
workspace under the system temp directory, and prints the call — scriptPath
and args fully filled in — to stdout. Diagnostics go to stderr so stdout stays
exactly the call to run. conventionPath carries the skill's docs-surface.md
when the file exists and stays empty otherwise — file presence decides, not
the skill name.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
SKILLS = tuple(
    sorted(p.name for p in SKILLS_DIR.iterdir() if (p / "workflow.js").is_file())
)


def resolve_repomix() -> str:
    """Pick a repomix invocation that works here without a permanent install.

    Preference order: an existing repomix, then npx, then bunx. Absolute paths
    are returned so downstream agents run it regardless of their shell's PATH.
    """
    if path := shutil.which("repomix"):
        return path
    if path := shutil.which("npx"):
        return f"{path} --yes repomix"
    if path := shutil.which("bunx"):
        return f"{path} repomix"
    return install_bun_bunx()


def install_bun_bunx() -> str:
    """No JS runtime present. Provision bun — a single self-contained binary
    that installs without root — and return an absolute bunx invocation."""
    print("no JS runtime found; installing bun to run repomix", file=sys.stderr)
    subprocess.run("curl -fsSL https://bun.sh/install | bash", shell=True, check=True)
    bunx = Path.home() / ".bun" / "bin" / "bunx"
    if not bunx.exists():
        raise RuntimeError("bun install did not produce bunx")
    return f"{bunx} repomix"


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in SKILLS:
        print(f"usage: bootstrap {{{'|'.join(SKILLS)}}} [focus ...]", file=sys.stderr)
        return 1
    skill = sys.argv[1]
    focus = " ".join(sys.argv[2:]).strip()
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
    agora = Path(tempfile.mkdtemp(prefix=f"refine-{skill}-agora-"))

    skill_dir = SKILLS_DIR / skill
    script = str(skill_dir / "workflow.js")
    convention = skill_dir / "docs-surface.md"
    args = {
        "focusArea": focus,
        "projectDir": str(project),
        "agoraPath": str(agora),
        "repomixCmd": resolve_repomix(),
        "principlesPath": str(skill_dir / "principles.md"),
        "conventionPath": str(convention) if convention.exists() else "",
    }
    args_block = json.dumps(args, ensure_ascii=False, indent=2).replace("\n", "\n  ")
    print(
        f"Workflow({{\n  scriptPath: {json.dumps(script)},\n  args: {args_block}\n}})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
