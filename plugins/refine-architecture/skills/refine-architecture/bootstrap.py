# /// script
# requires-python = ">=3.14"
# ///
"""Bootstrap a refine-architecture run.

Resolve a repomix runner that works on this machine, create a private Agora
workspace under the system temp directory, and emit (as JSON on stdout) the
paths the workflow engine needs. Diagnostics go to stderr so stdout stays a
parseable JSON document.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


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

    config = {
        "focusArea": focus,
        "projectDir": str(project),
        "agoraPath": str(agora),
        "repomixCmd": resolve_repomix(),
        "principlesPath": str(HERE / "design-principles.md"),
        "workflowScript": str(HERE / "workflows" / "refine-architecture.js"),
    }
    print(json.dumps(config, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
