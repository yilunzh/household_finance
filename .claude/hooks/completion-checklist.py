#!/usr/bin/env python3
"""Prompt agent to verify work before ending session.

This hook runs at Stop and checks if tests were run during the session.
If no test execution is detected, it blocks completion.
"""
import json
import os


def main():
    # Get transcript from environment (if available)
    transcript = os.environ.get("CLAUDE_TRANSCRIPT", "")

    # If no transcript available, allow but remind
    if not transcript:
        return {
            "decision": "allow",
            "message": "Reminder: Ensure you ran `pytest` before finishing.",
        }

    transcript_lower = transcript.lower()

    # Check if tests were run
    if "pytest" not in transcript_lower:
        return {
            "decision": "block",
            "reason": "You haven't run tests this session. "
            "Run `pytest tests/ -v --tb=short` before finishing.",
        }

    # Check for unresolved test failures
    # Look for FAILED without a subsequent "passed" or "PASSED"
    if "failed" in transcript_lower:
        # Find the last occurrence of test results
        last_failed_idx = transcript_lower.rfind("failed")
        remaining = transcript_lower[last_failed_idx:]
        # If there's no "passed" after the last "failed", tests might still be failing
        if "passed" not in remaining and "0 failed" not in remaining:
            return {
                "decision": "block",
                "reason": "Tests appear to be failing. "
                "Fix failing tests before finishing.",
            }

    return {"decision": "allow"}


if __name__ == "__main__":
    print(json.dumps(main()))
