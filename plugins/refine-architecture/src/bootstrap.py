"""CLI — print the fully resolved Workflow tool call for a refine-architecture run.

The skill body runs this and executes the printed Workflow(...) call verbatim, so a
single CLI covers both entry paths: a user typing /refine-architecture:refine-architecture
and the model invoking the skill as a tool. (A UserPromptExpansion hook would catch only
the first — it fires on user-typed commands alone; the model's tool call fires PreToolUse
instead, so one skill-run CLI is simpler than two hooks.)

It resolves a repomix runner that works on this machine, opens a private Agora workspace
under the system temp directory, and prints the call — scriptPath and args fully filled
in — to stdout. Diagnostics go to stderr so stdout stays exactly the call to run.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "skills" / "refine-architecture"


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
    focus = " ".join(sys.argv[1:]).strip()
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
    agora = Path(tempfile.mkdtemp(prefix="refine-architecture-agora-"))

    script = str(SKILL_DIR / "workflows" / "refine-architecture.js")
    args = {
        "focusArea": focus,
        "projectDir": str(project),
        "agoraPath": str(agora),
        "repomixCmd": resolve_repomix(),
        "principlesPath": str(SKILL_DIR / "design-principles.md"),
    }
    args_block = json.dumps(args, ensure_ascii=False, indent=2).replace("\n", "\n  ")
    print(
        f"Workflow({{\n  scriptPath: {json.dumps(script)},\n  args: {args_block}\n}})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
