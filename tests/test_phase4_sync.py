#!/usr/bin/env python3
"""
Phase 4 Dynamic UI Testing with Playwright (Synchronous version)
More stable than async version on some systems.
"""
from playwright.sync_api import sync_playwright
import sys

BASE_URL = "http://127.0.0.1:5001"


def run_all_tests():
    """Run all Phase 4 dynamic UI tests."""
    print("\n" + "🧪" * 35)
    print("PHASE 4 DYNAMIC UI TEST SUITE (SYNC)")
    print("🧪" * 35)

    passed = 0
    total = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        try:
            # ================================================================
            # Test 1: Login as Alice and verify dynamic UI
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 1: Alice Login and Dynamic Navigation")
            print("=" * 70)

            page = context.new_page()
            page.goto(f"{BASE_URL}/login")
            page.wait_for_load_state('networkidle')

            page.fill('#email', 'testalice@example.com')
            page.fill('#password', 'password123')
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle')

            print("✓ Logged in as Alice")

            # Check navigation
            nav_text = page.locator('nav').inner_text()
            total += 1
            if 'Alice Smith' in nav_text:
                print("✅ Navigation shows 'Alice Smith' (dynamic name)")
                passed += 1
            else:
                print(f"❌ Navigation doesn't show 'Alice Smith'. Got: {nav_text}")

            # Check no hardcoded names
            page_content = page.content()
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

            summary_text = page.locator('body').inner_text()
            total += 1
            if 'Alice paid' in summary_text and 'Bob paid' in summary_text:
                print("✅ Summary shows 'Alice paid' and 'Bob paid' (dynamic)")
                passed += 1
            else:
                print("❌ Summary doesn't show dynamic names")

            # ================================================================
            # Test 3: Dynamic Form Dropdowns
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 3: Dynamic Form Dropdowns")
            print("=" * 70)

            paid_by_options = page.locator('#paid_by option').all_inner_texts()
            print(f"   'Paid By' dropdown options: {paid_by_options}")

            total += 1
            if 'Alice' in paid_by_options and 'Bob' in paid_by_options:
                print("✅ 'Paid By' dropdown has Alice and Bob")
                passed += 1
            else:
                print("❌ 'Paid By' dropdown incorrect")

            total += 1
            if 'ME' not in paid_by_options and 'WIFE' not in paid_by_options:
                print("✅ No hardcoded ME/WIFE in dropdown")
                passed += 1
            else:
                print("❌ Found hardcoded ME/WIFE")

            category_options = page.locator('#category option').all_inner_texts()
            category_text = ' '.join(category_options)

            total += 1
            if 'Alice pays for Bob' in category_text and 'Bob pays for Alice' in category_text:
                print("✅ Category dropdown has dynamic names")
                passed += 1
            else:
                print("❌ Category dropdown doesn't have dynamic names")

            # ================================================================
            # Test 4: Reconciliation Page
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 4: Reconciliation Page Dynamic Names")
            print("=" * 70)

            page.goto(f"{BASE_URL}/reconciliation/2026-01")
            page.wait_for_load_state('networkidle')

            recon_content = page.content()

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

            # Logout before switching to Charlie
            page.goto(f"{BASE_URL}/logout")
            page.wait_for_load_state('networkidle')
            page.close()

            # ================================================================
            # Test 5: Switch to Charlie's Household
            # ================================================================
            print("\n" + "=" * 70)
            print("TEST 5: Switch to Charlie's Household")
            print("=" * 70)

            page2 = context.new_page()
            page2.goto(f"{BASE_URL}/login")
            page2.wait_for_load_state('networkidle')

            page2.fill('#email', 'testcharlie@example.com')
            page2.fill('#password', 'password123')
            page2.click('button[type="submit"]')
            page2.wait_for_load_state('networkidle')

            print("✓ Logged in as Charlie")

            nav_text2 = page2.locator('nav').inner_text()
            total += 1
            if 'Charlie Davis' in nav_text2:
                print("✅ Navigation shows 'Charlie Davis'")
                passed += 1
            else:
                print("❌ Navigation doesn't show Charlie's name")

            charlie_content = page2.content()
            total += 1
            if 'Charlie paid' in charlie_content and 'Diana paid' in charlie_content:
                print("✅ Summary shows Charlie and Diana")
                passed += 1
            else:
                print("❌ Summary doesn't show Charlie and Diana")

            paid_by_options2 = page2.locator('#paid_by option').all_inner_texts()
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

            table_content = page2.locator('#transactions-table').inner_text()

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

            page2.close()

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
            context.close()
            browser.close()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
