#!/usr/bin/env python3
"""Ensure handoff file is written before ending session with incomplete work."""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta


def main():
    transcript = os.environ.get("CLAUDE_TRANSCRIPT", "")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")

    # Check for incomplete work indicators
    transcript_lower = transcript.lower()

    incomplete_indicators = [
        "todo" in transcript_lower and "in_progress" in transcript_lower,
        "will continue" in transcript_lower,
        "next step" in transcript_lower and "later" in transcript_lower,
        "not finished" in transcript_lower,
    ]

    has_incomplete_work = any(incomplete_indicators)

    if not has_incomplete_work:
        return {"decision": "allow"}

    # Check if handoff file exists and is recent (within last 5 minutes)
    handoff_path = Path(project_dir) / ".claude" / "handoff.md"
    if handoff_path.exists():
        mtime = datetime.fromtimestamp(handoff_path.stat().st_mtime)
        if datetime.now() - mtime < timedelta(minutes=5):
            return {"decision": "allow"}

    return {
        "decision": "block",
        "reason": "Incomplete work detected. Write .claude/handoff.md before ending session.",
    }


if __name__ == "__main__":
    print(json.dumps(main()))
