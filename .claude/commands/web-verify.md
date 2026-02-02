# Web Route Verification

Verify web routes and templates work correctly using Playwright.

## Prerequisites

- App must be running on port 5001
- Check with: `lsof -i :5001`
- Start if needed: `source venv/bin/activate && python app.py`

## Steps

1. Check if app is running on port 5001
2. For each affected route:
   - Use `browser_navigate` to visit the page
   - Use `browser_snapshot` to capture accessibility tree
   - Verify page loads without errors
   - Check key elements are present

3. After successful verification:
   ```bash
   touch .playwright-verified
   ```

## Common Routes to Verify

| Route | What to Check |
|-------|---------------|
| `/` | Transaction list loads, filter sidebar present |
| `/login` | Login form renders |
| `/register` | Registration form renders |
| `/reconciliation/<month>` | Summary table loads |
| `/budget` | Budget rules display |
| `/household/settings` | Settings form loads |
| `/profile` | Profile page with stats |

## For Route Changes

When modifying routes in `app.py` or `blueprints/`:
1. Identify all affected URLs
2. Navigate to each one
3. Verify no 500 errors
4. Check key content is present

## Verification Marker

The pre-commit hook checks for `.playwright-verified` when committing route/template changes. Run this command to create the marker:
```bash
touch .playwright-verified
```
