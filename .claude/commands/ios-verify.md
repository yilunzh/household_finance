# iOS Verification

Run the iOS test suite to verify changes work correctly.

## Steps

1. Run the iOS test script:
   ```bash
   ./scripts/ios-test.sh --all
   ```

2. The script automatically:
   - Checks/starts backend server on port 5001
   - Seeds test data if demo user is missing
   - Sets up Java/Maestro environment
   - Boots iPhone 16 simulator if not running
   - Builds and installs app if needed
   - Runs all Maestro tests

3. If tests pass:
   - Report success
   - Note that `.ios-verified` marker was created

4. If tests fail:
   - Parse failure output (logs, screenshots in `~/.maestro/tests/`)
   - Diagnose: outdated test selector vs real bug vs flaky test
   - Offer to fix the appropriate file (test YAML or Swift code)

## For Specific Tests

To run only one test during iteration:
```bash
./scripts/ios-test.sh --test <test-name>
```

Available tests:
- login-flow
- logout
- add-transaction
- reconciliation
- receipt-flow
- design-review

## After UI Changes

Remember: regression tests alone don't verify visual correctness.
Take a screenshot to verify the intended change:
```bash
./scripts/ios-test.sh --test design-review
```
