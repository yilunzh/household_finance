# Phase 4 Testing Guide - Dynamic UI

## Quick Start

The test data from Phase 3 is already set up. Just open your browser and test!

---

## 🌐 Browser Testing

### Test 1: Login as Alice and verify dynamic names

1. **Open browser**: http://localhost:5001/login

2. **Login with**:
   - Email: `testalice@example.com`
   - Password: `password123`

3. **✅ Check these dynamic elements**:

**Navigation Bar:**
- [ ] Top right should show "Alice Smith" (not "Bibi")
- [ ] "Logout" link visible
- [ ] Title says "Household Expense Tracker" (not "Zhang Estate")

**Month Summary Card:**
- [ ] Should show "Alice paid: $150.00 USD"
- [ ] Should show "Bob paid: $80.00 USD"
- [ ] Settlement: "Bob owes Alice $35.00"

**Add Transaction Form:**
- [ ] "Paid By" dropdown shows:
  - Alice
  - Bob
  (NOT "ME" or "WIFE" or "Bibi" or "Pi")

- [ ] "Category" dropdown shows:
  - Shared 50/50
  - Alice pays for Bob
  - Bob pays for Alice
  - Personal (Alice)
  - Personal (Bob)
  (NOT "Bibi pays for Pi")

**Transaction Table:**
- [ ] "Paid By" column shows "Alice" or "Bob"
- [ ] Category badges show actual names (e.g., "Shared 50/50")

---

### Test 2: Add a new transaction with dynamic form

While logged in as Alice:

1. **Fill out the form**:
   - Date: Today's date
   - Merchant: "Coffee Shop"
   - Amount: 25.00
   - Currency: USD
   - **Paid By**: Select "Alice" from dropdown
   - **Category**: Select "Shared 50/50"
   - Notes: "Morning coffee"

2. **Click "Add Transaction"**

3. **✅ Verify**:
   - [ ] Transaction appears in table
   - [ ] "Paid By" column shows "Alice"
   - [ ] Category shows "Shared 50/50"
   - [ ] Summary updates automatically

---

### Test 3: Check reconciliation page

1. **Navigate to**: http://localhost:5001/reconciliation/2026-01

2. **✅ Check "What We Paid" card**:
   - [ ] Shows "Alice paid: $XXX.XX USD"
   - [ ] Shows "Bob paid: $XXX.XX USD"
   - [ ] NO hardcoded "Bibi" or "Pi" names

3. **✅ Check "What We Should Pay" card**:
   - [ ] Shows "Alice's share: $XXX.XX USD"
   - [ ] Shows "Bob's share: $XXX.XX USD"

4. **✅ Check Settlement**:
   - [ ] Shows "Bob owes Alice $XX.XX" (with actual names)

---

### Test 4: Test with Charlie & Diana household

1. **Logout**: Click "Logout" in top right

2. **Login with**:
   - Email: `testcharlie@example.com`
   - Password: `password123`

3. **✅ Verify different household**:
   - [ ] Nav shows "Charlie Davis" (different user!)
   - [ ] Summary shows "Charlie paid" and "Diana paid"
   - [ ] Dropdowns show "Charlie" and "Diana"
   - [ ] Settlement mentions "Diana owes Charlie $220.00"

4. **✅ Verify data isolation**:
   - [ ] Should see Electronics Store ($500) and Gas Station ($60)
   - [ ] Should NOT see Alice & Bob's transactions (Grocery Store, Restaurant)

---

### Test 5: Edit existing transaction

1. **While logged in as Charlie**, click "Edit" on any transaction

2. **✅ Check edit modal**:
   - [ ] "Paid By" dropdown shows Charlie and Diana
   - [ ] Category dropdown shows:
     - Shared 50/50
     - Charlie pays for Diana
     - Diana pays for Charlie
     - Personal (Charlie)
     - Personal (Diana)

3. **Make changes**:
   - Change "Paid By" from Charlie to Diana
   - Click "Save Changes"

4. **✅ Verify**:
   - [ ] Table updates to show "Diana" in "Paid By" column
   - [ ] Summary recalculates automatically

---

## ✅ What to Look For

### ✅ GOOD - Dynamic behavior:
- Member names match the actual users in the household
- Alice/Bob household shows "Alice" and "Bob"
- Charlie/Diana household shows "Charlie" and "Diana"
- Dropdowns populate from database, not hardcoded
- Navigation shows current user's name

### ❌ BAD - If you see these, something broke:
- Any mention of "Bibi" or "Pi" (old hardcoded names)
- Any mention of "ME" or "WIFE" in dropdowns
- "Zhang Estate" in the title
- Generic "Member 1" or "Member 2" labels
- Same household data when switching between Alice and Charlie

---

## 🔍 Visual Checklist

Here's what a correct screen should look like:

**Navigation:**
```
Household Expense Tracker     Transactions  Reconciliation  |  Alice Smith  Logout
```

**"Paid By" Dropdown:**
```
┌──────────────────┐
│ Alice            │ ← Real name from database
│ Bob              │ ← Real name from database
└──────────────────┘
```

**Category Dropdown:**
```
┌────────────────────────────┐
│ Shared 50/50               │
│ Alice pays for Bob         │ ← Dynamic names!
│ Bob pays for Alice         │
│ Personal (Alice)           │
│ Personal (Bob)             │
└────────────────────────────┘
```

**Month Summary:**
```
┌─────────────────────────────────────────────┐
│ Month Summary                                │
│                                              │
│ Alice paid        Bob paid       Settlement │
│ $150.00 USD      $80.00 USD    Bob owes     │
│                                 Alice $35.00 │
└─────────────────────────────────────────────┘
```

---

## 🐛 Common Issues

**Issue**: Dropdowns still show "ME" or "WIFE"
- **Cause**: Flask didn't reload templates
- **Fix**: Restart Flask server (`kill` and restart `python app.py`)

**Issue**: See "Member 1" or "Member 2" instead of names
- **Cause**: household_members not passed to template
- **Fix**: This shouldn't happen - all routes now pass household_members

**Issue**: No transactions showing
- **Cause**: User has no household yet
- **Fix**: Use test accounts (testalice@example.com or testcharlie@example.com)

**Issue**: Error when adding transaction
- **Cause**: Backend expecting user_id but receiving old format
- **Fix**: Should work now - report if you see this

---

## 📊 Expected Test Results

If everything works correctly:

| Test | Expected Result |
|------|----------------|
| Login as Alice | ✅ Shows "Alice Smith" in nav |
| View transactions | ✅ Shows Alice/Bob names, no Bibi/Pi |
| Add transaction | ✅ Dropdown has Alice/Bob options |
| View reconciliation | ✅ Dynamic names in all cards |
| Switch to Charlie | ✅ Shows Charlie/Diana data only |
| Edit transaction | ✅ Modal dropdowns show Charlie/Diana |

---

## 🎯 Success Criteria

Phase 4 is successful if:
- ✅ NO hardcoded "Bibi" or "Pi" anywhere
- ✅ NO "ME" or "WIFE" in any dropdown
- ✅ Names match actual household members
- ✅ Forms work correctly with user IDs
- ✅ Different households show different member names
- ✅ Navigation shows current user
- ✅ Can add/edit transactions with new dynamic dropdowns

---

## 💡 Quick Test Commands

```bash
# 1. Make sure Flask is running
# Check if server is running on http://localhost:5001

# 2. Open browser and test these URLs:
http://localhost:5001/login
http://localhost:5001/
http://localhost:5001/reconciliation/2026-01

# 3. Test accounts:
# Alice & Bob Household:
#   testalice@example.com / password123
#   testbob@example.com / password123

# Charlie & Diana Household:
#   testcharlie@example.com / password123
#   testdiana@example.com / password123
```

---

## 🆘 Need to Reset Test Data?

If you want fresh test data:

```bash
# Re-run Phase 3 isolation tests to recreate test households
python test_phase3_isolation.py
```

This will:
- Clean up old test data
- Create Alice & Bob household with 2 transactions
- Create Charlie & Diana household with 2 transactions
- You can then test the dynamic UI with clean data
