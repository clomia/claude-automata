"""PoC: Verify UserPromptSubmit hook captures raw user input."""

import json
import os
import sys


def main():
    data = json.loads(sys.stdin.read())
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA", "/tmp/parallax-poc")
    os.makedirs(data_dir, exist_ok=True)
    session_id = data.get("session_id", "unknown")
    prompt = data.get("prompt", "")

    log_path = os.path.join(data_dir, f"{session_id}_poc.json")
    with open(log_path, "w") as f:
        json.dump(
            {"prompt": prompt, "all_keys": list(data.keys())},
            f,
            ensure_ascii=False,
            indent=2,
        )


if __name__ == "__main__":
    main()
