# /// script
# dependencies = ["copier>=9.0"]
# requires-python = ">=3.10"
# ///
"""
autonomous-claude-code 프로젝트 스캐폴드.

사용법:
  uv run create.py <프로젝트-이름>
  uv run https://raw.githubusercontent.com/<owner>/autonomous-claude-code/main/create.py <프로젝트-이름>
"""
import sys
from pathlib import Path

def main():
    project_name = sys.argv[1] if len(sys.argv) > 1 else "autonomous-claude-code"
    dest = Path.cwd() / project_name

    if dest.exists():
        print(f"오류: '{dest}' 디렉토리가 이미 존재합니다.")
        sys.exit(1)

    from copier import run_copy

    run_copy(
        src_path="https://github.com/clomia/autonomous-claude-code.git",
        dst_path=str(dest),
        data={"project_name": project_name},
        unsafe=True,
        defaults=False,
    )

    print()
    print(f"'{project_name}' 프로젝트가 생성되었습니다.")
    print()
    print("다음 단계:")
    print(f"  cd {project_name}")
    print(f"  uv sync")
    print(f"  uv run acc configure")
    print(f"  uv run acc start")

if __name__ == "__main__":
    main()
