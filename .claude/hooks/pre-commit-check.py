#!/usr/bin/env python3
"""Block commits if tests/lint fail, committing to main, or UI changes without Playwright verification."""
import subprocess
import json
from pathlib import Path


# Patterns that indicate UI-affecting files
UI_PATTERNS = [
    "app.py",
    "blueprints/",
    "templates/",
]


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


def get_staged_ui_files():
    """Get staged files that affect UI (routes, templates, blueprints)."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
    )
    staged = [f for f in result.stdout.strip().split("\n") if f]

    ui_files = []
    for f in staged:
        # Skip hook files (they may contain route patterns in detection code)
        if ".claude/hooks/" in f:
            continue
        # Check against known UI patterns
        if any(pattern in f for pattern in UI_PATTERNS):
            ui_files.append(f)
        # Also check Python files for route decorators
        elif f.endswith(".py") and file_contains_routes(f):
            ui_files.append(f)
    return ui_files


def file_contains_routes(filepath):
    """Check if a Python file contains route definitions."""
    try:
        content = Path(filepath).read_text()
        return "@app.route" in content or "@bp.route" in content or "Blueprint(" in content
    except Exception:
        return False


def is_playwright_verification_current(ui_files):
    """Check if .playwright-verified marker is newer than all UI files."""
    marker = Path(".playwright-verified")
    if not marker.exists():
        return False

    marker_time = marker.stat().st_mtime
    for f in ui_files:
        file_path = Path(f)
        if file_path.exists() and file_path.stat().st_mtime > marker_time:
            return False
    return True


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
            "reason": "Cannot commit directly to main.\n"
            "Create a feature branch: git checkout -b feature/<name>\n"
            "Then open a PR to merge into main.",
        }

    # Check Playwright verification for UI-affecting files
    ui_files = get_staged_ui_files()
    if ui_files and not is_playwright_verification_current(ui_files):
        file_list = "\n".join(f"  - {f}" for f in ui_files)
        return {
            "decision": "block",
            "reason": f"""UI-affecting files detected. Playwright verification required.

Files needing verification:
{file_list}

Steps:
1. Ensure app running: lsof -i :5001 || python app.py
2. Use browser_navigate to visit affected pages
3. Use browser_snapshot to verify pages load correctly
4. Mark verified: touch .playwright-verified
5. Retry commit
""",
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
            "reason": "Pre-commit checks failed:\n\n" + "\n---\n".join(reasons),
        }
    return {"decision": "allow"}


if __name__ == "__main__":
    print(json.dumps(main()))
