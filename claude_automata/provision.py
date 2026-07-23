"""Provision — put the external CLIs the plugins assume on PATH, without sudo.

Official distribution binaries land under ~/.local/share/claude-automata and are
symlinked into ~/.local/bin. openspec is deliberately absent: the tx plugin
fetches its pinned version via npx, and the pin's single home stays there.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

LOCAL_BIN = Path.home() / ".local" / "bin"
SHARE = Path.home() / ".local" / "share" / "claude-automata"
NODE_TOOLS = ("node", "npm", "npx")


@dataclass
class Outcome:
    tool: str
    status: str  # "ok" | "installed" | "deferred" | "failed"
    note: str = ""


def target() -> tuple[str, str] | None:
    """(os, arch) for supported platforms; None otherwise."""
    arches = {"x86_64": "x64", "amd64": "x64", "arm64": "arm64", "aarch64": "arm64"}
    arch = arches.get(platform.machine().lower())
    if sys.platform not in ("linux", "darwin") or arch is None:
        return None
    return sys.platform, arch


def gh_asset(os_name: str, arch: str, version: str) -> str:
    gh_arch = {"x64": "amd64", "arm64": "arm64"}[arch]
    if os_name == "darwin":
        return f"gh_{version}_macOS_{gh_arch}.zip"
    return f"gh_{version}_linux_{gh_arch}.tar.gz"


def node_asset(os_name: str, arch: str, version: str) -> str:
    return f"node-{version}-{os_name}-{arch}.tar.gz"


def latest_gh_version() -> str:
    # The /releases/latest redirect ends at .../releases/tag/v<version> — no API quota.
    with urllib.request.urlopen("https://github.com/cli/cli/releases/latest") as resp:
        return resp.url.rstrip("/").rsplit("/v", 1)[1]


def pick_lts(releases: list[dict]) -> str:
    for release in releases:  # newest first
        if release.get("lts"):
            version = release["version"]
            if int(version.lstrip("v").split(".", 1)[0]) >= 22:
                return version
            break
    raise LookupError("no Node.js LTS >= 22 in the release index")


def latest_node_lts() -> str:
    with urllib.request.urlopen("https://nodejs.org/dist/index.json") as resp:
        return pick_lts(json.load(resp))


def node_major(node: str) -> int:
    out = subprocess.run(
        [node, "--version"], capture_output=True, text=True, check=True
    ).stdout
    return int(out.strip().lstrip("v").split(".", 1)[0])


def npm_env() -> dict[str, str]:
    """PATH with LOCAL_BIN first, so a just-installed node resolves for npm's launcher."""
    return {
        **os.environ,
        "PATH": f"{LOCAL_BIN}{os.pathsep}{os.environ.get('PATH', '')}",
    }


def extract(url: str, into: Path) -> Path:
    """Download an archive and extract it under `into`; return the extracted root."""
    name = url.rsplit("/", 1)[1]
    root = into / name.removesuffix(".tar.gz").removesuffix(".zip")
    if root.exists():
        return root
    into.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / name
        urllib.request.urlretrieve(url, archive)
        if name.endswith(".zip"):
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(into)
        else:
            with tarfile.open(archive) as bundle:
                bundle.extractall(into, filter="data")
    return root


def link(binary: Path, name: str) -> None:
    binary.chmod(0o755)  # zipfile drops exec bits
    LOCAL_BIN.mkdir(parents=True, exist_ok=True)
    dest = LOCAL_BIN / name
    if dest.is_symlink() or dest.exists():
        dest.unlink()
    dest.symlink_to(binary)


def ensure_gh() -> Outcome:
    if path := shutil.which("gh"):
        return Outcome("gh", "ok", path)
    plat = target()
    if plat is None:
        return Outcome(
            "gh",
            "failed",
            "unsupported platform — install GitHub CLI manually: https://github.com/cli/cli#installation",
        )
    try:
        version = latest_gh_version()
        url = f"https://github.com/cli/cli/releases/download/v{version}/{gh_asset(*plat, version)}"
        root = extract(url, SHARE)
        link(root / "bin" / "gh", "gh")
        return Outcome("gh", "installed", f"v{version} -> {LOCAL_BIN / 'gh'}")
    except Exception as error:
        return Outcome(
            "gh",
            "failed",
            f"{error} — install GitHub CLI manually: https://github.com/cli/cli#installation",
        )


def ensure_node() -> Outcome:
    replaced = ""
    node = shutil.which("node")
    if node and all(shutil.which(tool) for tool in NODE_TOOLS):
        try:
            major = node_major(node)
        except subprocess.CalledProcessError, OSError, ValueError:
            major = 0
        if major >= 22:
            return Outcome("node", "ok", node)
        replaced = f"node v{major} on PATH is below 22; "
    plat = target()
    if plat is None:
        return Outcome(
            "node",
            "failed",
            "unsupported platform — install Node.js >= 22 manually: https://nodejs.org",
        )
    try:
        version = latest_node_lts()
        url = f"https://nodejs.org/dist/{version}/{node_asset(*plat, version)}"
        root = extract(url, SHARE)
        for tool in NODE_TOOLS:
            link(root / "bin" / tool, tool)
        note = f"{replaced}{version} -> {LOCAL_BIN}"
        if replaced:
            note += f" — ensure {LOCAL_BIN} precedes the old node on PATH"
        return Outcome("node", "installed", note)
    except Exception as error:
        return Outcome(
            "node",
            "failed",
            f"{error} — install Node.js >= 22 manually: https://nodejs.org",
        )


def ensure_repomix() -> Outcome:
    if path := shutil.which("repomix"):
        return Outcome("repomix", "ok", path)
    npm = shutil.which("npm") or str(LOCAL_BIN / "npm")
    if not Path(npm).exists():
        return Outcome(
            "repomix",
            "failed",
            "npm unavailable — install Node.js, then `npm install -g repomix`",
        )
    try:
        # An explicit user-area prefix keeps the install sudo-free even when npm
        # is a system Node whose global prefix is root-owned.
        prefix = SHARE / "npm"
        run = {"check": True, "capture_output": True, "text": True, "env": npm_env()}
        subprocess.run(
            [npm, "install", "-g", "--prefix", str(prefix), "repomix"], **run
        )
        link(prefix / "bin" / "repomix", "repomix")
        return Outcome("repomix", "installed", str(LOCAL_BIN / "repomix"))
    except (subprocess.CalledProcessError, OSError) as error:
        detail = getattr(error, "stderr", "") or str(error)
        return Outcome(
            "repomix",
            "failed",
            f"npm install -g repomix failed: {detail.strip()[:200]}",
        )


def ensure_all() -> list[Outcome]:
    outcomes = [ensure_gh(), ensure_node()]
    outcomes.append(ensure_repomix())  # needs npm — after node
    return outcomes


def gh_auth_note() -> str | None:
    gh = shutil.which("gh") or str(LOCAL_BIN / "gh")
    if not Path(gh).exists():
        return None
    if subprocess.run([gh, "auth", "status"], capture_output=True).returncode != 0:
        return "GitHub CLI is not authenticated — run `gh auth login`"
    return None


def path_note(outcomes: list[Outcome]) -> str | None:
    installed = any(outcome.status == "installed" for outcome in outcomes)
    on_path = str(LOCAL_BIN) in os.environ.get("PATH", "").split(os.pathsep)
    if installed and not on_path:
        return f'{LOCAL_BIN} is not on PATH — add `export PATH="{LOCAL_BIN}:$PATH"` to your shell profile'
    return None
