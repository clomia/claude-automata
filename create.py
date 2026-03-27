# /// script
# dependencies = ["copier>=9.0"]
# requires-python = ">=3.10"
# ///
"""
claude-automata 프로젝트 생성.

사용법:
  uv run create.py [디렉토리]
  uv run https://raw.githubusercontent.com/clomia/claude-automata/main/create.py [디렉토리]
"""
import sys
from pathlib import Path

def main():
    dest = Path.cwd() / (sys.argv[1] if len(sys.argv) > 1 else "claude-automata")

    if dest.exists():
        print(f"오류: '{dest}' 디렉토리가 이미 존재합니다.")
        sys.exit(1)

    from copier import run_copy

    run_copy(
        src_path="https://github.com/clomia/claude-automata.git",
        dst_path=str(dest),
        defaults=True,
        unsafe=True,
    )

    print()
    print(f"'{dest.name}' 프로젝트가 생성되었습니다.")
    print()
    print("다음 단계:")
    print(f"  cd {dest.name}")
    print(f"  uv sync")
    print(f"  uv run acc configure")
    print(f"  uv run acc start")

if __name__ == "__main__":
    main()
