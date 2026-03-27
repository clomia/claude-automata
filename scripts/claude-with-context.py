#!/usr/bin/env python3
# /// script
# requires-python = ">=3.14"
# ///
"""
claude-with-context — 디렉토리의 파일을 Claude Code 컨텍스트에 주입하고 TUI를 연다.

Usage:
    uv run scripts/claude-with-context.py <dir> [dir ...]
    uv run scripts/claude-with-context.py design/ docs/
    uv run scripts/claude-with-context.py --dry-run design/
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def discover(directories: list[str]) -> list[tuple[Path, str]]:
    """디렉토리를 재귀 탐색하여 UTF-8 텍스트 파일의 경로와 내용을 반환한다."""
    entries: list[tuple[Path, str]] = []
    for arg in directories:
        root = Path(arg)
        if not root.is_dir():
            print(f"오류: '{arg}'는 디렉토리가 아닙니다.", file=sys.stderr)
            sys.exit(1)
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, ValueError, PermissionError, OSError):
                continue
            entries.append((path, text))
    return entries


def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    if dry_run:
        args.remove("--dry-run")

    if not args:
        print(__doc__.strip())
        sys.exit(0)

    entries = discover(args)
    if not entries:
        print("UTF-8 텍스트 파일을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    total_bytes = sum(len(text.encode("utf-8")) for _, text in entries)

    print(f"파일: {len(entries)}개  크기: {total_bytes:,} bytes (~{total_bytes // 3:,} tokens)")

    if dry_run:
        for path, text in entries:
            print(f"  {path}  ({len(text.encode('utf-8')):,}B)")
        return

    content = "\n\n".join(f"=== FILE: {path} ===\n{text}" for path, text in entries)

    print("로드 중...")
    proc = subprocess.run(
        [
            "claude", "-p", "확인.",
            "--append-system-prompt", "'확인.'만 출력하라. 다른 출력 일절 금지.",
            "--output-format", "json",
            "--max-turns", "1",
        ],
        input=content,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"claude 실패:\n{proc.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"JSON 파싱 실패:\n{proc.stdout[:500]}", file=sys.stderr)
        sys.exit(1)
    if data.get("is_error"):
        print(f"claude 에러: {data.get('result', '')[:500]}", file=sys.stderr)
        sys.exit(1)
    session_id = data.get("session_id")
    if not session_id:
        print(f"session_id 없음:\n{proc.stdout[:500]}", file=sys.stderr)
        sys.exit(1)

    print(f"세션: {session_id}")
    os.execvp("claude", ["claude", "--resume", session_id])


if __name__ == "__main__":
    main()
