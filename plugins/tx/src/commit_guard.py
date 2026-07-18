"""PreToolUse(Bash) guard — block `git commit` on the base branch.

Invariant: the base branch holds only what merged through a transaction.
branch-protect (protect.py) covers Edit/Write on tracked files; the route
still open is a commit forged through Bash — new files, `sed -i`, `git add`
are all harmless until committed, so the commit is the choke point.

Two-stage failure direction.  Detection first: Bash targets are unbounded,
so nothing is blocked until some shell segment is a `git … commit`
invocation — a missed exotic spelling is accepted (string parsing has
limits).  Separators inside quoted spans and heredoc bodies are neutralized
before segmentation, so a commit spelled inside a string or a written
document stays inside its host segment and never anchors a match.
Detection is a linear token scan — env-assignment prefixes, `git`, dash
options (the value-taking globals consume their value), then the first bare
token must be `commit` — no regex backtracking, so a hostile option string
cannot stall the hook into its timeout.

Once detected, resolution is fail-closed.  The target is the segment's `-C`
path, else the payload `cwd` (a documented hook input field), else
CLAUDE_PROJECT_DIR.  A `cd`/`pushd` segment earlier in the same
command makes those fallbacks meaningless for the commit's real directory,
so a detected commit after one blocks unless it names its own `-C`.
Repository identity is `--git-common-dir` equality, so a linked worktree of
the session repository cannot slip through, while `git -C <elsewhere>`
passes — scratch repositories are working memory; the invariant governs only
this repository.  A session outside a repository, or an unresolvable base
(no origin/HEAD mirror), disables the guard entirely — the shared degrade
contract.
"""

import json
import os
import re
import sys
from typing import NoReturn

from src.repo import base_branch, git

SEPARATORS = "&|;\n"
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
VALUE_OPTIONS = {
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--exec-path",
    "--config-env",
}
CD_HEADS = {"cd", "pushd"}


def read_event() -> tuple[str | None, str | None]:
    """(command, payload cwd) from the hook event — (None, None) when unreadable."""
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError, OSError:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    cwd = payload.get("cwd")
    return (
        command if isinstance(command, str) else None,
        cwd if isinstance(cwd, str) else None,
    )


def neutralize_quotes(command: str) -> str:
    """Replace separator characters inside quoted spans with spaces.

    Every other character stays (a quoted `-C` path still resolves), and a
    backslash outside quotes escapes the next character.  An unclosed quote
    neutralizes to the end — the fail direction is fewer segments, never a
    bogus split.
    """
    chars = list(command)
    quote = None
    i = 0
    while i < len(chars):
        char = chars[i]
        if quote:
            if char == quote:
                quote = None
            elif char in SEPARATORS:
                chars[i] = " "
        elif char in ("'", '"'):
            quote = char
        elif char == "\\":
            i += 1
        i += 1
    return "".join(chars)


def neutralize_heredocs(command: str) -> str:
    """Fold each heredoc into its host segment.

    From the newline that opens the body through the terminator line, every
    separator and newline becomes a space, so document lines never become
    segments of their own.  An unterminated heredoc folds to the end.
    """
    out = command
    pos = 0
    while match := HEREDOC_RE.search(out, pos):
        body_start = out.find("\n", match.end())
        if body_start == -1:
            break
        span_end = len(out)
        offset = body_start + 1
        for line in out[body_start + 1 :].split("\n"):
            if line.strip() == match.group(2):
                span_end = offset + len(line)
                break
            offset += len(line) + 1
        folded = "".join(
            " " if c in SEPARATORS else c for c in out[body_start:span_end]
        )
        out = out[:body_start] + folded + out[span_end:]
        pos = span_end
    return out


def commit_targets(command: str) -> list[tuple[str | None, bool]]:
    """One (-C path, cd-came-before) pair per detected `git … commit` segment."""
    found: list[tuple[str | None, bool]] = []
    cd_seen = False
    prepared = neutralize_heredocs(neutralize_quotes(command))
    for segment in re.split(r"[&|;\n]", prepared):
        tokens = segment.split()
        i = 0
        while i < len(tokens) and ENV_ASSIGN_RE.match(tokens[i]):
            i += 1
        if i >= len(tokens):
            continue
        head = tokens[i]
        if head in CD_HEADS:
            cd_seen = True
            continue
        if head != "git":
            continue
        i += 1
        c_path: str | None = None
        while i < len(tokens):
            token = tokens[i]
            if token in VALUE_OPTIONS:
                if token == "-C" and i + 1 < len(tokens):
                    c_path = tokens[i + 1].strip("\"'")
                i += 2
                continue
            if token.startswith("-"):
                i += 1
                continue
            if token == "commit":
                found.append((c_path, cd_seen))
            break
    return found


def resolve_dir(c_path: str | None, payload_cwd: str | None) -> str:
    return c_path or payload_cwd or os.environ.get("CLAUDE_PROJECT_DIR") or "."


def common_dir(directory: str | None = None) -> str | None:
    prefix = ("-C", directory) if directory else ()
    return git(*prefix, "rev-parse", "--path-format=absolute", "--git-common-dir")


def deny(base: str) -> NoReturn:
    print(
        f"[base-commit-block] '{base}' is protected — commit inside a transaction "
        "(/tx:open). For a repository outside this one, use git -C <path>.",
        file=sys.stderr,
    )
    sys.exit(2)


def main() -> None:
    command, payload_cwd = read_event()
    if command is None:
        return
    targets = commit_targets(command)
    if not targets:
        return

    base = base_branch()
    session_common = common_dir()
    if base is None or session_common is None:
        return

    for c_path, cd_before in targets:
        if c_path is None and cd_before:
            deny(base)
        target = resolve_dir(c_path, payload_cwd)
        target_common = common_dir(target)
        if target_common is None:
            deny(base)
        if target_common != session_common:
            continue
        branch = git("-C", target, "rev-parse", "--abbrev-ref", "HEAD")
        if branch is None or branch == base:
            deny(base)


if __name__ == "__main__":
    main()
