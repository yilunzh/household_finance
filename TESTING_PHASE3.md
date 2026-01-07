# Phase 3 Testing Guide

## ✅ Automated Tests (PASSED)

Run: `python test_phase3_isolation.py`

**All tests passed:**
- ✅ Transaction isolation between households
- ✅ Settlement isolation between households
- ✅ Ownership verification (404 for wrong household)
- ✅ Reconciliation calculation with dynamic members
- ✅ Month filtering per household

---

## 🌐 Manual Browser Testing

### Test Setup

The automated test created 4 users and 2 households:

**Household 1: Alice & Bob**
- Alice (Owner): `testalice@example.com` / `password123`
- Bob (Member): `testbob@example.com` / `password123`
- Transactions: Grocery Store ($150), Restaurant ($80)

**Household 2: Charlie & Diana**
- Charlie (Owner): `testcharlie@example.com` / `password123`
- Diana (Member): `testdiana@example.com` / `password123`
- Transactions: Electronics Store ($500), Gas Station ($60)

### Manual Test Steps

#### 1. Login as Alice and verify data isolation

```bash
# 1. Open browser to http://localhost:5001/login
# 2. Login with: testalice@example.com / password123
```

**Expected behavior:**
- ✅ Login successful
- ✅ Redirected to `/` (main page)
- ✅ Should see **only** Household 1's transactions:
  - Grocery Store: $150
  - Restaurant: $80
- ✅ Should NOT see Household 2's transactions (Electronics Store, Gas Station)

**Verify reconciliation:**
```bash
# Navigate to http://localhost:5001/reconciliation/2026-01
```

**Expected:**
- ✅ Settlement shows: "Bob owes Alice $35.00"
- ✅ Alice paid: $150
- ✅ Bob paid: $80
- ✅ Uses member display names ("Alice", "Bob")

---

#### 2. Logout and login as Charlie

```bash
# 1. Navigate to http://localhost:5001/logout
# 2. Login with: testcharlie@example.com / password123
```

**Expected behavior:**
- ✅ Should see **only** Household 2's transactions:
  - Electronics Store: $500
  - Gas Station: $60
- ✅ Should NOT see Household 1's transactions (Grocery Store, Restaurant)

**Verify reconciliation:**
```bash
# Navigate to http://localhost:5001/reconciliation/2026-01
```

**Expected:**
- ✅ Settlement shows: "Diana owes Charlie $220.00"
- ✅ Charlie paid: $500
- ✅ Diana paid: $60
- ✅ Uses member display names ("Charlie", "Diana")

---

#### 3. Test Data Isolation via Direct URL Access

While logged in as Charlie, try to access Alice's transaction directly:

```bash
# Get Alice's transaction ID from database:
# Transaction ID 1 belongs to Household 1 (Alice & Bob)

# Try to edit it via browser dev console:
fetch('/transaction/1', {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({merchant: 'HACKED'})
})
```

**Expected:**
- ✅ Should return **404 Not Found** (not 403, to avoid leaking existence)
- ✅ Transaction should NOT be modified

---

## ⚠️ Known Limitations (Will be fixed in Phase 4)

### What DOESN'T work yet:

1. **Transaction form dropdowns are hardcoded**
   - "Paid By" dropdown still shows "ME" and "WIFE" (not dynamic member names)
   - This will be fixed in Phase 4 when we update templates

2. **Cannot add new transactions via UI yet**
   - Form expects user IDs but shows hardcoded strings
   - Backend is ready, just needs UI update

3. **Category names are generic**
   - Shows "Member 1 pays for Member 2" instead of "Alice pays for Bob"
   - Phase 4 will make these dynamic

4. **No household selector in UI**
   - If a user belongs to multiple households, can't switch yet
   - Phase 6 will add household management UI

### What DOES work:

- ✅ Backend data isolation (fully tested)
- ✅ Route protection (@household_required)
- ✅ Ownership verification on edit/delete
- ✅ Reconciliation calculation with dynamic members
- ✅ Settlement locking per household
- ✅ CSV export with dynamic names

---

## 🔍 Database Inspection

You can also verify data isolation by inspecting the database directly:

```bash
# Open SQLite database
sqlite3 instance/database.db

# Check transactions are household-scoped
SELECT id, household_id, merchant, amount_in_usd, paid_by_user_id
FROM transactions;

# Expected output:
# 1|1|Grocery Store|150.00|1        <- Household 1
# 2|1|Restaurant|80.00|2             <- Household 1
# 3|2|Electronics Store|500.00|3     <- Household 2
# 4|2|Gas Station|60.00|4            <- Household 2

# Check settlements are household-scoped
SELECT id, household_id, month_year, from_user_id, to_user_id, settlement_message
FROM settlements;

# Expected: Only Household 1's settlement (created by test)
# 1|1|2026-01|2|1|Bob owes Alice $35.00
```

---

## 📊 Test Results Summary

**Phase 3 Validation Status:**

| Test | Status | Notes |
|------|--------|-------|
| Transaction isolation | ✅ PASS | Each household sees only their transactions |
| Settlement isolation | ✅ PASS | Settlements are household-scoped |
| Ownership verification | ✅ PASS | Returns 404 for wrong household |
| Reconciliation logic | ✅ PASS | Uses dynamic member names |
| Month filtering | ✅ PASS | Months filtered per household |
| Route protection | ✅ PASS | @household_required on all routes |
| Dynamic UI | ⚠️ PENDING | Phase 4 will update templates |

**Conclusion:** Phase 3 backend is **fully functional and secure**. Phase 4 will update the UI to match.

---

## 🐛 If you find issues:

1. Check Flask server logs at `/tmp/claude/-Users-yilunzhang-side-project/tasks/baed26f.output`
2. Check browser console for JavaScript errors
3. Verify you're logged in as the correct user
4. Confirm household context is set (session has household_id)
5. Re-run automated tests: `python test_phase3_isolation.py`
