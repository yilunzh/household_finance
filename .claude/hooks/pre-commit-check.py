#!/usr/bin/env python3
"""Block commits if tests/lint fail OR committing to main with non-trivial changes."""
import subprocess
import json


def get_current_branch():
    result = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True
    )
    return result.stdout.strip()


def get_staged_python_files():
    """Get list of staged .py files (excluding tests)."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
    )
    return [
        f
        for f in result.stdout.strip().split("\n")
        if f.endswith(".py") and f and "test" not in f
    ]


def get_staged_file_count():
    """Count total staged files."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True
    )
    files = [f for f in result.stdout.strip().split("\n") if f]
    return len(files)


def run_command(cmd, name):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "name": name,
        "passed": result.returncode == 0,
        "output": (result.stdout + result.stderr)[-1500:],
    }


def main():
    checks = []

    # Check branch policy: block ALL commits to main
    branch = get_current_branch()
    file_count = get_staged_file_count()
    if branch == "main" and file_count > 0:
        return {
            "decision": "block",
            "reason": f"Cannot commit directly to main.\n"
            f"Create a feature branch: git checkout -b feature/<name>\n"
            f"Then open a PR to merge into main.",
        }

    # Lint only changed files (skip if no Python files staged)
    staged_files = get_staged_python_files()
    if staged_files:
        checks.append(
            run_command(
                ["python", "-m", "flake8"]
                + staged_files
                + ["--max-line-length=120", "--ignore=E501,W503"],
                "Lint (changed files)",
            )
        )

    # Always run unit tests
    checks.append(
        run_command(["pytest", "tests/", "-v", "--tb=short", "-q"], "Unit Tests")
    )

    failed = [c for c in checks if not c["passed"]]
    if failed:
        reasons = [f"{c['name']}:\n{c['output']}" for c in failed]
        return {
            "decision": "block",
            "reason": f"Pre-commit checks failed:\n\n" + "\n---\n".join(reasons),
        }
    return {"decision": "allow"}


if __name__ == "__main__":
    print(json.dumps(main()))
