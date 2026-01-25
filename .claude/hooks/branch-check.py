#!/usr/bin/env python3
"""Block code edits when on main branch - must create feature branch first."""
import subprocess
import json
import sys
import os

# File extensions that are considered "code" and require a feature branch
CODE_EXTENSIONS = {
    # Python
    ".py",
    # Swift/iOS
    ".swift",
    # Web
    ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".scss",
    # Templates
    ".jinja", ".jinja2",
}

# Paths that are always allowed on main (config, docs, etc.)
ALLOWED_PATHS = [
    ".claude/",
    ".github/",
    "docs/",
    ".gitignore",
    ".env",
    "README.md",
    "CLAUDE.md",
    "requirements",
    "package.json",
    "package-lock.json",
    "Podfile",
    "Podfile.lock",
    ".xcodeproj/",
    "maestro/",  # Test files
]


def get_current_branch():
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=os.environ.get("CLAUDE_PROJECT_DIR", ".")
        )
        return result.stdout.strip()
    except Exception:
        return None


def is_code_file(file_path):
    """Check if the file is a code file that requires a feature branch."""
    if not file_path:
        return False

    # Check if path is in allowed list
    for allowed in ALLOWED_PATHS:
        if allowed in file_path:
            return False

    # Check extension
    for ext in CODE_EXTENSIONS:
        if file_path.endswith(ext):
            return True

    return False


def main():
    # Read tool input from stdin
    try:
        input_data = json.loads(sys.stdin.read())
        tool_input = input_data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")
    except (json.JSONDecodeError, KeyError):
        # If we can't parse input, allow (fail open)
        return {"decision": "allow"}

    # Check if this is a code file
    if not is_code_file(file_path):
        return {"decision": "allow"}

    # Check current branch
    branch = get_current_branch()

    if branch == "main":
        # Extract just the filename for cleaner message
        filename = file_path.split("/")[-1] if "/" in file_path else file_path

        return {
            "decision": "block",
            "reason": f"""Cannot edit code files on main branch.

File: {filename}

Create a feature branch first:
  git checkout -b feature/<descriptive-name>

Then proceed with your changes. When done, create a PR to merge into main.
"""
        }

    return {"decision": "allow"}


if __name__ == "__main__":
    print(json.dumps(main()))
