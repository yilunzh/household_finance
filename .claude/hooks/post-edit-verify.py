#!/usr/bin/env python3
"""After editing, remind to run related tests. Advisory only - doesn't block."""
import json
import os


def get_related_tests(file_path):
    """Map source files to their test files."""
    mappings = {
        "app.py": ["tests/test_models.py", "tests/test_utils.py"],
        "models.py": ["tests/test_models.py"],
        "utils.py": ["tests/test_utils.py"],
        "budget": ["tests/test_budget.py"],
        "decorators.py": ["tests/test_models.py"],
        "household_context.py": ["tests/test_models.py"],
        "auth.py": ["tests/test_models.py"],
        "email_service.py": ["tests/test_models.py"],
    }
    for pattern, tests in mappings.items():
        if pattern in file_path:
            return tests
    return ["tests/"]


def main():
    file_path = os.environ.get("CLAUDE_FILE_PATH", "")
    if file_path.endswith(".py") and "test" not in file_path:
        tests = get_related_tests(file_path)
        # Advisory message - doesn't block
        return {
            "continue": True,
            "message": f"Remember to verify: pytest {' '.join(tests)} -v --tb=short",
        }
    return {"continue": True}


if __name__ == "__main__":
    print(json.dumps(main()))
