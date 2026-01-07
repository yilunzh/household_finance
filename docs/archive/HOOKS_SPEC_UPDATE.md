# SPEC.md Auto-Update Hook

**Status**: Implemented
**Date**: January 2026

## Overview

A Claude Code **Stop hook** that prompts for SPEC.md documentation updates at the end of feature implementations. The hook uses intentional triggers (user commands or todo completion) rather than automatic file-based detection.

## Design Decision: Stop Hook

**Why Stop hook (not PostToolUse)?**
- Fires at end of Claude's turn = logical completion point
- Can analyze cumulative changes, not per-file
- Supports user signals like "feature complete" or `/spec-update`
- PostToolUse would fire too frequently (every Write/Edit)

## Files Created

```
.claude/
├── settings.json              # Hooks configuration added
└── hooks/
    ├── spec-update-check.py   # Main Stop hook script
    └── sync-structure.py      # Project tree generator utility
```

## How to Use

### Trigger the Hook

Say any of these to trigger a SPEC.md update:

| Trigger | Example |
|---------|---------|
| `/spec-update` | "Please /spec-update" |
| "update spec" | "Feature is done, update spec" |
| "update documentation" | "Update documentation please" |
| "feature complete" | "Feature complete, let's document this" |

The hook also auto-triggers when all todos are marked complete.

### What Happens

1. Hook detects trigger phrase in your message
2. Hook gathers context:
   - Git changes (what files were modified)
   - Session transcript (conversation history)
   - Active plan file (if exists)
3. Hook outputs prompt to Claude with instructions to:
   - Read changed files
   - Read current SPEC.md
   - Compare and update documentation
   - Add new sections if needed
   - Update version history and metadata

## Hook Logic

```
1. Read hook input from stdin (JSON with session_id, transcript_path, cwd)
2. Read transcript to check for trigger signals
3. If trigger detected:
   - Get git changes (staged + unstaged + untracked)
   - Output JSON with `additionalContext` prompting Claude to update SPEC.md
4. Otherwise exit silently (no output)
```

## Documentation Update Scope

### Always Update
| Section | Location | Update Type |
|---------|----------|-------------|
| Version History | Section 12 | Add new row to table |
| Project Structure | Section 7 | Sync file tree |
| Implementation Status | Section 10.2 | Check completed items |
| Document Footer | End of file | Version + "Last Updated" date |

### Update If Changed
| Section | When to Update |
|---------|----------------|
| API Routes (Section 4) | New/modified routes in app.py |
| Data Model (Section 3) | Schema changes in models.py |
| Business Logic (Section 5) | Algorithm changes in utils.py |
| UI Design (Section 6) | New templates or UI flows |
| Security (Section 9) | Auth/security changes |
| Dependencies (Section 8) | requirements.txt changes |

### Add New Sections
- **New major feature**: Add subsection under relevant parent
- **New integration**: Add to External Dependencies
- **New workflow**: Document in appropriate section

## Utility: sync-structure.py

Generate current project tree for SPEC.md Section 7:

```bash
python3 .claude/hooks/sync-structure.py
```

Output can be copied into docs/SPEC.md Section 7 (Project Structure).

## Configuration

In `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/spec-update-check.py\"",
            "timeout": 30000
          }
        ]
      }
    ]
  }
}
```

## Testing

1. **No trigger test**: Make code changes without trigger phrase, verify hook stays silent
2. **Manual trigger test**: Say "/spec-update", verify prompt appears and Claude updates SPEC.md
3. **Phrase trigger test**: Say "feature complete, update spec", verify prompt appears
4. **Todo completion test**: Complete all todos in a plan, verify prompt appears
5. **Structure sync test**: Run `python3 .claude/hooks/sync-structure.py`, compare to SPEC.md

## Troubleshooting

**Hook not triggering?**
- Check that `.claude/settings.json` has the hooks configuration
- Verify the hook script is executable: `chmod +x .claude/hooks/spec-update-check.py`
- Use exact trigger phrases

**Hook errors?**
- Check Claude Code logs for hook output
- Run hook manually: `echo '{}' | python3 .claude/hooks/spec-update-check.py`
