#!/usr/bin/env python3
"""
Check if implementation plan needs updating when working on features with ideation docs.

Triggers:
- Pre-commit: Advisory reminder if feature code changed but plan didn't
- Stop: Advisory reminder to update plan before ending session

Advisory only - doesn't block commits.
"""
import json
import os
import subprocess
from pathlib import Path


def get_current_branch():
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            cwd=os.environ.get("CLAUDE_PROJECT_DIR", "."),
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_feature_name_from_branch(branch):
    """Extract feature name from branch like 'feature/bank-import'."""
    if branch.startswith("feature/"):
        return branch.replace("feature/", "")
    if branch.startswith("fix/"):
        return branch.replace("fix/", "")
    return None


def has_ideation_folder(feature_name, project_dir):
    """Check if feature has an ideation folder with implementation plan."""
    ideation_path = Path(project_dir) / ".claude" / "ideation" / feature_name
    plan_path = ideation_path / "implementation-plan.md"
    return plan_path.exists()


def get_staged_files():
    """Get list of staged files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=os.environ.get("CLAUDE_PROJECT_DIR", "."),
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except Exception:
        return []


def get_modified_files():
    """Get list of all modified files (staged + unstaged)."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=os.environ.get("CLAUDE_PROJECT_DIR", "."),
        )
        files = []
        for line in result.stdout.strip().split("\n"):
            if line:
                # Format: XY filename (XY is status, filename starts at position 3)
                files.append(line[3:].strip())
        return files
    except Exception:
        return []


def is_feature_code(file_path, feature_name):
    """Check if file is related to the feature (not tests, not ideation docs)."""
    # Skip ideation docs themselves
    if ".claude/ideation" in file_path:
        return False
    # Skip test files
    if "test" in file_path.lower():
        return False
    # Skip docs
    if file_path.endswith(".md") and "CLAUDE" not in file_path:
        return False

    # Check if file path contains feature name or is general code
    feature_keywords = feature_name.replace("-", "_").split("_")

    # For bank-import: check for bank, import in path
    for keyword in feature_keywords:
        if keyword in file_path.lower():
            return True

    # Also consider general code files that might be part of feature
    code_extensions = [".py", ".swift", ".ts", ".js", ".yaml", ".yml"]
    return any(file_path.endswith(ext) for ext in code_extensions)


def check_implementation_plan_updated(feature_name, files):
    """Check if implementation plan was updated along with feature code."""
    plan_path = f".claude/ideation/{feature_name}/implementation-plan.md"

    has_feature_code_changes = any(is_feature_code(f, feature_name) for f in files)
    has_plan_changes = plan_path in files

    return has_feature_code_changes, has_plan_changes


def main():
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    hook_type = os.environ.get("CLAUDE_HOOK_TYPE", "")

    branch = get_current_branch()
    feature_name = get_feature_name_from_branch(branch)

    # Not on a feature branch
    if not feature_name:
        return {"continue": True}

    # No ideation folder for this feature
    if not has_ideation_folder(feature_name, project_dir):
        return {"continue": True}

    # Determine which files to check based on hook type
    if hook_type == "PreToolUse":
        # Pre-commit: check staged files
        files = get_staged_files()
    else:
        # Stop hook: check all modified files
        files = get_modified_files()

    if not files:
        return {"continue": True}

    has_code_changes, has_plan_changes = check_implementation_plan_updated(feature_name, files)

    if has_code_changes and not has_plan_changes:
        plan_path = f".claude/ideation/{feature_name}/implementation-plan.md"
        return {
            "continue": True,  # Advisory - don't block
            "message": f"Feature '{feature_name}' has an implementation plan. "
                       f"Consider updating {plan_path} to reflect progress:\n"
                       f"  - Mark completed stories with [x]\n"
                       f"  - Update Progress Summary table\n"
                       f"  - Update 'Last Updated' date"
        }

    return {"continue": True}


if __name__ == "__main__":
    print(json.dumps(main()))
