# Bank Import Feature - Decision Log

## Key Decisions

| # | Decision | Choice | Rationale | Date |
|---|----------|--------|-----------|------|
| 1 | Input format | Screenshot, camera, PDF | Maximum flexibility for users | Jan 2025 |
| 2 | Processing model | Async | Don't block user from using app | Jan 2025 |
| 3 | Selection vs categorization | Separate steps | Reduces cognitive load per screen | Jan 2025 |
| 4 | Category navigation | Horizontal tabs | Cleaner than vertical scroll, familiar pattern | Jan 2025 |
| 5 | Transaction display | Dense table | Information density important for bulk review | Jan 2025 |
| 6 | Table columns | Merchant, Type, Split, Date, Amount | Need both expense type AND split visible | Jan 2025 |
| 7 | Uncertain categories | Best guess + flag | Balance automation with user control | Jan 2025 |
| 8 | Default split | Shared (unless rule exists) | Safe default for household expenses | Jan 2025 |
| 9 | Duplicate detection | Merchant + amount + date | Catches most re-imports without false positives | Jan 2025 |
| 10 | Rules management | Full CRUD (view/edit/delete) | Give users full control over automation | Jan 2025 |

---

## Decision Details

### D1: Input Format

**Question:** How should users get bank statement data into the app?

**Options Considered:**
- A) Screenshot only - Simple but limited
- B) Camera + photo library - More flexible
- C) Camera + photo library + PDF - Maximum flexibility
- D) Direct bank API (Plaid) - Most automated but complex

**Decision:** Option C - Camera + photo library + PDF

**Rationale:**
- Most banks provide PDF statements
- Screenshots work for mobile banking apps
- Camera for paper statements (edge case)
- Direct API integration too complex for v1

---

### D2: Processing Model

**Question:** How should extraction processing work?

**Options Considered:**
- A) Synchronous - User waits for results
- B) Async with polling - User can navigate away
- C) Async with push notification - Best UX

**Decision:** Option C - Async with push notification

**Rationale:**
- OCR/AI extraction can take 10-30 seconds
- Users shouldn't stare at a loading screen
- Push notification brings them back when ready

---

### D3: Selection vs Categorization Flow

**Question:** Should users select AND categorize in one step or separate steps?

**Options Considered:**
- A) Combined - Edit everything in one list
- B) Separate - First select, then fix flagged items
- C) Card-based - Review each transaction individually

**Decision:** Option B - Separate steps

**Rationale:**
- Selection is quick (checkboxes)
- Categorization requires thought
- Most transactions won't need categorization (rules handle them)
- Separating reduces cognitive load per screen

---

### D4: Category Display

**Question:** How to show Ready/Needs Attention/Skipped/Imported categories?

**Options Considered:**
- A) Vertical tabs (sidebar)
- B) Horizontal tabs (top)
- C) Dropdown filter
- D) Separate screens

**Decision:** Option B - Horizontal tabs

**Rationale:**
- Familiar mobile pattern
- Shows counts at a glance
- Easy one-tap switching
- Works well on mobile width

---

### D5: Transaction Display Density

**Question:** How dense should the transaction list be?

**Options Considered:**
- A) Card-based - More spacing, fewer visible
- B) Dense table - Compact, more visible at once
- C) Mixed - Cards for editing, table for selection

**Decision:** Option B - Dense table for selection screen

**Rationale:**
- Users reviewing 20+ transactions
- Need to scan quickly
- Every row needs: checkbox, merchant, type, split, date, amount
- Cards waste too much vertical space

---

### D6: Visible Columns

**Question:** What columns to show in the transaction table?

**Options Considered:**
- A) Merchant, Amount, Date (minimal)
- B) Merchant, Type, Date, Amount
- C) Merchant, Type, Split, Date, Amount (full)

**Decision:** Option C - Full columns

**Rationale:**
- Users need to see BOTH expense type and split category
- These are the two things rules control
- Flagged items show "?" in these columns
- Amount and date for identification

---

### D7: Uncertain Category Handling

**Question:** What to do when AI is uncertain about categorization?

**Options Considered:**
- A) Leave blank - User must fill in
- B) Best guess shown - User can change
- C) Best guess + visual flag - Draws attention

**Decision:** Option C - Best guess + visual flag

**Rationale:**
- Often the guess is right
- Flag draws user attention without blocking
- Moves uncertain items to "Needs Attention" tab
- User can accept guess or change it

---

### D8: Default Split Category

**Question:** What split to assign when no rule matches?

**Options Considered:**
- A) Always "Mine" - Conservative
- B) Always "Shared" - Household-oriented
- C) User configurable default

**Decision:** Option B (with C available in settings)

**Rationale:**
- This is a household expense tracker
- Most imported transactions are shared expenses
- User can change default in settings
- Individual rules override default

---

### D9: Duplicate Detection

**Question:** How to detect if a transaction was already imported?

**Options Considered:**
- A) Exact merchant match only
- B) Merchant + amount
- C) Merchant + amount + date
- D) AI similarity scoring

**Decision:** Option C - Merchant + amount + date

**Rationale:**
- Catches the same transaction from re-uploaded statements
- Low false positive rate (different amounts/dates pass through)
- Simpler than AI scoring
- Can use fuzzy merchant matching for variations

---

### D10: Rules Management

**Question:** How much control should users have over categorization rules?

**Options Considered:**
- A) Automatic only - System learns, no manual control
- B) View + delete - Can see and remove rules
- C) Full CRUD - View, create, edit, delete

**Decision:** Option C - Full CRUD

**Rationale:**
- Users want control over automation
- Mistakes need to be correctable
- Power users want to pre-configure rules
- Transparency builds trust in the system

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| Where do rules live in nav? | Settings → Import Rules |
| What's the "already imported" experience? | Shows in separate tab, can't re-select |
| How to handle OCR failures? | Manual entry form with original text shown |
