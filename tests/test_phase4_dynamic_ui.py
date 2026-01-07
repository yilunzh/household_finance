#!/usr/bin/env python3
"""
Phase 4 Dynamic UI Testing with Playwright
Automates the test plan from TESTING_PHASE4.md

Run Flask without auto-reload for stability:
    FLASK_DEBUG=0 python app.py
    OR
    python -c "from app import app; app.run(host='0.0.0.0', port=5001, debug=False)"
"""
import asyncio
from playwright.async_api import async_playwright
import sys

BASE_URL = "http://127.0.0.1:5001"

# Browser launch args for stability
BROWSER_ARGS = [
    '--disable-dev-shm-usage',
    '--disable-gpu',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-extensions',
]


async def run_all_tests():
    """Run all Phase 4 dynamic UI tests."""
    print("\n" + "🧪" * 35)
    print("PHASE 4 DYNAMIC UI TEST SUITE")
    print("🧪" * 35)
    print("\nTIP: For best results, run Flask without auto-reload:")
    print("     FLASK_DEBUG=0 python app.py\n")

    passed = 0
    total = 0

    async with async_playwright() as p:
        # Try Firefox first (more stable on macOS), fall back to Chromium
        try:
            browser = await p.firefox.launch(headless=True, slow_mo=100)
            print("Using Firefox browser")
        except Exception:
            browser = await p.chromium.launch(
                headless=True,
                args=BROWSER_ARGS,
                slow_mo=100
            )
            print("Using Chromium browser")

        try:
            # Create a single browser context for all tests (more stable)
            context = await browser.new_context()

            # ================================================================
            # Test 1: Login as Alice and verify dynamic UI
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 1: Alice Login and Dynamic Navigation")
            print("=" * 70)

            page = await context.new_page()
            await page.goto(f"{BASE_URL}/login")
            await page.wait_for_load_state('networkidle')

            await page.fill('#email', 'testalice@example.com')
            await page.fill('#password', 'password123')
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')

            print("✓ Logged in as Alice")

            # Check navigation
            nav_text = await page.locator('nav').inner_text()
            total += 1
            if 'Alice Smith' in nav_text:
                print("✅ Navigation shows 'Alice Smith' (dynamic name)")
                passed += 1
            else:
                print(f"❌ Navigation doesn't show 'Alice Smith'. Got: {nav_text}")

            # Check no hardcoded names
            page_content = await page.content()
            total += 1
            if 'Bibi' not in page_content and 'Pi' not in page_content:
                print("✅ No hardcoded 'Bibi' or 'Pi' found")
                passed += 1
            else:
                print("❌ Found hardcoded 'Bibi' or 'Pi'")

            total += 1
            if 'Zhang Estate' not in page_content:
                print("✅ No 'Zhang Estate' found")
                passed += 1
            else:
                print("❌ Found 'Zhang Estate'")

            # ================================================================
            # Test 2: Dynamic Month Summary
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 2: Dynamic Month Summary")
            print("=" * 70)

            summary_text = await page.locator('body').inner_text()
            total += 1
            if 'Alice paid' in summary_text and 'Bob paid' in summary_text:
                print("✅ Summary shows 'Alice paid' and 'Bob paid' (dynamic)")
                passed += 1
            else:
                print(f"❌ Summary doesn't show dynamic names")

            # ================================================================
            # Test 3: Dynamic Form Dropdowns
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 3: Dynamic Form Dropdowns")
            print("=" * 70)

            # Check Paid By dropdown
            paid_by_options = await page.locator('#paid_by option').all_inner_texts()
            print(f"   'Paid By' dropdown options: {paid_by_options}")

            total += 1
            if 'Alice' in paid_by_options and 'Bob' in paid_by_options:
                print("✅ 'Paid By' dropdown has Alice and Bob")
                passed += 1
            else:
                print(f"❌ 'Paid By' dropdown incorrect")

            total += 1
            if 'ME' not in paid_by_options and 'WIFE' not in paid_by_options:
                print("✅ No hardcoded ME/WIFE in dropdown")
                passed += 1
            else:
                print("❌ Found hardcoded ME/WIFE")

            # Check Category dropdown
            category_options = await page.locator('#category option').all_inner_texts()
            category_text = ' '.join(category_options)

            total += 1
            if 'Alice pays for Bob' in category_text and 'Bob pays for Alice' in category_text:
                print("✅ Category dropdown has dynamic names")
                passed += 1
            else:
                print(f"❌ Category dropdown doesn't have dynamic names")

            # ================================================================
            # Test 4: Reconciliation Page
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 4: Reconciliation Page Dynamic Names")
            print("=" * 70)

            await page.goto(f"{BASE_URL}/reconciliation/2026-01")
            await page.wait_for_load_state('networkidle')

            recon_content = await page.content()

            total += 1
            if 'Alice paid:' in recon_content and 'Bob paid:' in recon_content:
                print("✅ Reconciliation shows 'Alice paid' and 'Bob paid'")
                passed += 1
            else:
                print("❌ Reconciliation doesn't show dynamic names")

            total += 1
            if 'Bibi' not in recon_content and 'Pi' not in recon_content:
                print("✅ No hardcoded names in reconciliation")
                passed += 1
            else:
                print("❌ Found hardcoded names in reconciliation")

            # Close page and wait a bit before opening new one
            await page.close()
            await asyncio.sleep(0.5)

            # ================================================================
            # Test 5: Switch to Charlie's Household
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 5: Switch to Charlie's Household")
            print("=" * 70)

            # Reuse same context with new page (more stable)
            page2 = await context.new_page()
            await page2.goto(f"{BASE_URL}/login")
            await page2.wait_for_load_state('networkidle')

            await page2.fill('#email', 'testcharlie@example.com')
            await page2.fill('#password', 'password123')
            await page2.click('button[type="submit"]')
            await page2.wait_for_load_state('networkidle')

            print("✓ Logged in as Charlie")

            # Check navigation
            nav_text2 = await page2.locator('nav').inner_text()
            total += 1
            if 'Charlie Davis' in nav_text2:
                print("✅ Navigation shows 'Charlie Davis'")
                passed += 1
            else:
                print(f"❌ Navigation doesn't show Charlie's name")

            # Check summary
            charlie_content = await page2.content()
            total += 1
            if 'Charlie paid' in charlie_content and 'Diana paid' in charlie_content:
                print("✅ Summary shows Charlie and Diana")
                passed += 1
            else:
                print("❌ Summary doesn't show Charlie and Diana")

            # Check dropdowns
            paid_by_options2 = await page2.locator('#paid_by option').all_inner_texts()
            total += 1
            if 'Charlie' in paid_by_options2 and 'Diana' in paid_by_options2:
                print("✅ Dropdowns show Charlie and Diana")
                passed += 1
            else:
                print(f"❌ Dropdowns incorrect: {paid_by_options2}")

            # ================================================================
            # Test 6: Data Isolation
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 6: Data Isolation Between Households")
            print("=" * 70)

            table_content = await page2.locator('#transactions-table').inner_text()

            total += 1
            if 'Electronics Store' in table_content and 'Gas Station' in table_content:
                print("✅ Charlie can see his transactions")
                passed += 1
            else:
                print("❌ Charlie's transactions not found")

            total += 1
            if 'Grocery Store' not in table_content and 'Restaurant' not in table_content:
                print("✅ Charlie cannot see Alice's transactions (data isolated)")
                passed += 1
            else:
                print("❌ SECURITY ISSUE: Charlie can see Alice's transactions!")

            # Close page
            await page2.close()
            await asyncio.sleep(0.5)

            # ================================================================
            # Test 7: Add Transaction with CSRF
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 7: Add Transaction (CSRF Protection)")
            print("=" * 70)

            # Reuse same context with new page (more stable)
            page3 = await context.new_page()
            await page3.goto(f"{BASE_URL}/login")
            await page3.wait_for_load_state('networkidle')

            await page3.fill('#email', 'testalice@example.com')
            await page3.fill('#password', 'password123')
            await page3.click('button[type="submit"]')
            await page3.wait_for_load_state('networkidle')

            print("✓ Logged in as Alice")

            # Fill and submit transaction form
            await page3.fill('#date', '2026-01-15')
            await page3.fill('#merchant', 'CSRF Test Merchant')
            await page3.fill('#amount', '99.99')
            await page3.select_option('#currency', 'USD')

            # Get first user_id value from dropdown and select it
            first_user_value = await page3.locator('#paid_by option').first.get_attribute('value')
            await page3.select_option('#paid_by', value=first_user_value)
            await page3.select_option('#category', 'SHARED')

            print("✓ Filled transaction form")

            # Submit form and wait for page reload
            async with page3.expect_navigation(wait_until='networkidle'):
                await page3.click('button:has-text("Add Transaction")')

            await page3.wait_for_timeout(1000)

            # Verify transaction was added (page should reload with new transaction)
            await page3.wait_for_load_state('networkidle')
            table_content = await page3.locator('#transactions-table').inner_text()

            total += 1
            if 'CSRF Test Merchant' in table_content:
                print("✅ Transaction successfully added (CSRF token working)")
                passed += 1
            else:
                print("❌ Transaction not added - CSRF token may be missing")

            # ================================================================
            # Test 8: Edit Transaction with CSRF
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 8: Edit Transaction (CSRF Protection)")
            print("=" * 70)

            # Find and click edit button for the transaction we just added
            edit_buttons = await page3.locator('button:has-text("Edit")').all()

            if len(edit_buttons) > 0:
                await edit_buttons[0].click()
                await page3.wait_for_timeout(1000)

                # Modify merchant name
                await page3.fill('#edit-merchant', 'CSRF Test Merchant EDITED')
                print("✓ Modified merchant name in edit modal")

                # Submit edit form and wait for navigation
                async with page3.expect_navigation(wait_until='networkidle'):
                    await page3.click('button:has-text("Save Changes")')

                await page3.wait_for_timeout(1000)

                # Verify update
                updated_content = await page3.locator('#transactions-table').inner_text()

                total += 1
                if 'CSRF Test Merchant EDITED' in updated_content:
                    print("✅ Transaction successfully updated (CSRF token working)")
                    passed += 1
                else:
                    print("❌ Transaction not updated - CSRF token may be missing")
            else:
                print("⚠️  No edit buttons found, skipping edit test")
                total += 1

            # ================================================================
            # Test 9: Delete Transaction with CSRF
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 9: Delete Transaction (CSRF Protection)")
            print("=" * 70)

            # Find delete button for our test transaction
            delete_buttons = await page3.locator('button:has-text("Delete")').all()

            if len(delete_buttons) > 0:
                # Set up dialog handler before clicking delete
                page3.on("dialog", lambda dialog: dialog.accept())

                # Click delete and wait for navigation
                async with page3.expect_navigation(wait_until='networkidle'):
                    await delete_buttons[0].click()

                await page3.wait_for_timeout(1000)

                # Verify deletion
                deleted_content = await page3.locator('#transactions-table').inner_text()

                total += 1
                if 'CSRF Test Merchant EDITED' not in deleted_content:
                    print("✅ Transaction successfully deleted (CSRF token working)")
                    passed += 1
                else:
                    print("❌ Transaction not deleted - CSRF token may be missing")
            else:
                print("⚠️  No delete buttons found, skipping delete test")
                total += 1

            # ================================================================
            # Test 10: Unsettle Month with CSRF
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 10: Unsettle Month (CSRF Protection)")
            print("=" * 70)

            # First, add a transaction to February (clean month) so we have something to settle
            await page3.goto(f"{BASE_URL}/")
            await page3.wait_for_load_state('networkidle')

            # Add a transaction for settlement (February - no existing data)
            await page3.fill('#date', '2026-02-15')
            await page3.fill('#merchant', 'Settlement Test')
            await page3.fill('#amount', '100.00')
            first_user_value = await page3.locator('#paid_by option').first.get_attribute('value')
            await page3.select_option('#paid_by', value=first_user_value)
            await page3.select_option('#category', 'SHARED')

            async with page3.expect_navigation(wait_until='networkidle'):
                await page3.click('button:has-text("Add Transaction")')

            await page3.wait_for_timeout(1000)
            print("✓ Added transaction for settlement test (Feb 2026)")

            # Now go to February reconciliation page
            await page3.goto(f"{BASE_URL}/reconciliation/2026-02")
            await page3.wait_for_load_state('networkidle')

            # Check if there's a settle button (month is not settled)
            settle_button = await page3.locator('button:has-text("Mark as Settled")').count()

            if settle_button > 0:
                print(f"✓ Found settle button ({settle_button} instances)")

                # Click settle button to open custom confirm modal
                await page3.click('button:has-text("Mark as Settled")')
                await page3.wait_for_timeout(1000)

                # Check if confirm modal appeared
                modal_visible = await page3.locator('#confirm-modal').is_visible()
                print(f"  Confirm modal visible: {modal_visible}")

                if modal_visible:
                    # Click OK button in the custom confirm modal
                    ok_button_count = await page3.locator('button#confirm-ok').count()
                    print(f"  OK button count: {ok_button_count}")

                    if ok_button_count > 0:
                        await page3.click('button#confirm-ok')
                        await page3.wait_for_timeout(3000)
                        await page3.wait_for_load_state('networkidle')
                        print("✓ Month marked as settled")
                    else:
                        print("  ERROR: OK button not found")
                else:
                    print("  ERROR: Modal not visible")
            else:
                print("  No settle button found - month may already be settled or have no transactions")

            # Now try to unsettle
            await page3.wait_for_timeout(1000)  # Give time for button to appear
            unsettle_button = await page3.locator('button:has-text("Unsettle Month")').count()

            if unsettle_button > 0:
                # Click unsettle button to open custom confirm modal
                await page3.click('button:has-text("Unsettle Month")')
                await page3.wait_for_timeout(500)

                # Click OK button in the custom confirm modal
                await page3.click('button#confirm-ok')
                await page3.wait_for_timeout(2000)
                await page3.wait_for_load_state('networkidle')

                # Verify month is unsettled (settle button should be visible again)
                settle_visible = await page3.locator('button:has-text("Mark as Settled")').count()

                total += 1
                if settle_visible > 0:
                    print("✅ Month successfully unsettled (CSRF token working)")
                    passed += 1
                else:
                    print("❌ Month not unsettled - CSRF token may be missing")
            else:
                print("⚠️  No unsettle button found, month may not be settled")
                total += 1

            # Close page
            await page3.close()

            # ================================================================
            # Print Summary
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST SUMMARY")
            print("=" * 70)
            print(f"Passed: {passed}/{total} checks")
            print("=" * 70)

            if passed == total:
                print(f"✅ ALL {total} TESTS PASSED!")
                print("\n🎉 Phase 4 Dynamic UI + CSRF Protection working perfectly!")
                print("   - All hardcoded names removed")
                print("   - Dynamic dropdowns functioning")
                print("   - Data isolation maintained")
                print("   - Multiple households work correctly")
                print("   - CSRF tokens working on all AJAX operations")
                print("   - Add/Edit/Delete transactions working")
                print("   - Month settlement/unsettlement working")
                return True
            else:
                print(f"❌ {total - passed} of {total} tests FAILED")
                return False

        except Exception as e:
            print(f"\n❌ TEST SUITE FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await browser.close()


if __name__ == '__main__':
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
