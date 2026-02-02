# Bank Import - Technical Architecture

## Overview

This document defines the technical approach for implementing the bank import feature. It covers data models, APIs, external service integration, async processing, and implementation order.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              iOS App / Web                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Capture Screen  →  Select Screen  →  Categorize Screen  →  Import         │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Flask Backend API                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  POST /import/sessions     - Create session, upload files                   │
│  GET  /import/sessions/:id - Get session status + transactions              │
│  PUT  /import/transactions/:id - Update categorization                      │
│  POST /import/sessions/:id/import - Finalize import                         │
│  CRUD /import/rules        - Manage auto-categorization rules               │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Background Job Queue                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Process uploaded files → OCR/AI extraction → Rule matching → Notification  │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          External Services                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Document AI (Google/AWS/OpenAI)  │  Push Notifications (APNs)              │
│  File Storage (S3/Local)          │  SQLite/PostgreSQL Database             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### New Models

#### ImportSession

Tracks a batch import from upload through completion.

```python
class ImportSession(db.Model):
    __tablename__ = 'import_sessions'

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Status workflow: pending → processing → ready → completed | failed
    status = db.Column(db.String(20), nullable=False, default='pending')

    # File references (JSON array of paths/URLs)
    source_files = db.Column(db.Text, nullable=False)  # JSON: [{"path": "...", "type": "pdf|image"}]

    # Processing metadata
    error_message = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processing_started_at = db.Column(db.DateTime, nullable=True)
    processing_completed_at = db.Column(db.DateTime, nullable=True)
    imported_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    household = db.relationship('Household')
    user = db.relationship('User')
    extracted_transactions = db.relationship('ExtractedTransaction', back_populates='session', cascade='all, delete-orphan')
```

**Status Values:**
| Status | Description |
|--------|-------------|
| `pending` | Files uploaded, waiting to process |
| `processing` | OCR/AI extraction in progress |
| `ready` | Extraction complete, awaiting user review |
| `completed` | User imported selected transactions |
| `failed` | Processing failed (see error_message) |

---

#### ExtractedTransaction

Individual transaction extracted from a bank statement.

```python
class ExtractedTransaction(db.Model):
    __tablename__ = 'extracted_transactions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('import_sessions.id'), nullable=False, index=True)

    # Raw extraction
    raw_text = db.Column(db.Text, nullable=True)  # Original OCR text
    source_file_index = db.Column(db.Integer, nullable=True)  # Which file this came from

    # Parsed fields
    merchant = db.Column(db.String(200), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=True)
    currency = db.Column(db.String(3), nullable=False, default='USD')  # USD or CAD, user can change
    date = db.Column(db.Date, nullable=True)

    # AI suggestions
    suggested_expense_type_id = db.Column(db.Integer, db.ForeignKey('expense_types.id'), nullable=True)
    suggested_split = db.Column(db.String(20), nullable=True)  # SHARED, PERSONAL_ME, PERSONAL_PARTNER
    confidence_score = db.Column(db.Float, nullable=True)  # 0.0 - 1.0

    # User-selected values (set during categorization)
    final_expense_type_id = db.Column(db.Integer, db.ForeignKey('expense_types.id'), nullable=True)
    final_split = db.Column(db.String(20), nullable=True)
    final_merchant = db.Column(db.String(200), nullable=True)  # For OCR corrections

    # Status: ready | needs_attention | skipped | imported | duplicate
    status = db.Column(db.String(20), nullable=False, default='ready')

    # If imported, reference to created transaction
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)

    # Duplicate detection
    duplicate_of_transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    session = db.relationship('ImportSession', back_populates='extracted_transactions')
    suggested_expense_type = db.relationship('ExpenseType', foreign_keys=[suggested_expense_type_id])
    final_expense_type = db.relationship('ExpenseType', foreign_keys=[final_expense_type_id])
    created_transaction = db.relationship('Transaction', foreign_keys=[transaction_id])
```

**Status Values:**
| Status | Description | Tab in UI |
|--------|-------------|-----------|
| `ready` | Confident categorization, selected for import | Ready |
| `needs_attention` | Low confidence or OCR failure | Needs Attention |
| `skipped` | User deselected | Skipped |
| `imported` | Successfully created as Transaction | - |
| `duplicate` | Matches existing transaction | Already Imported |

---

#### SplitRule (New)

Rules for auto-assigning split category by merchant.

```python
class SplitRule(db.Model):
    __tablename__ = 'split_rules'
    __table_args__ = (
        db.Index('idx_household_split_keyword', 'household_id', 'keyword'),
    )

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False, index=True)
    keyword = db.Column(db.String(100), nullable=False)  # Case-insensitive match
    split_category = db.Column(db.String(20), nullable=False)  # SHARED, PERSONAL_ME, PERSONAL_PARTNER
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    household = db.relationship('Household', back_populates='split_rules')
```

> **Note:** `SplitRule` already exists in models.py with a many-to-many relationship to ExpenseType. We may need to add a simpler keyword-based rule or extend the existing model.

---

#### ImportSettings (New)

Per-household import preferences.

```python
class ImportSettings(db.Model):
    __tablename__ = 'import_settings'

    id = db.Column(db.Integer, primary_key=True)
    household_id = db.Column(db.Integer, db.ForeignKey('households.id'), nullable=False, unique=True)

    default_split = db.Column(db.String(20), nullable=False, default='SHARED')
    default_paid_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    household = db.relationship('Household')
```

---

### Existing Models to Extend

#### AutoCategoryRule (Extend)

Add split category support:

```python
# Add to existing AutoCategoryRule model:
split_category = db.Column(db.String(20), nullable=True)  # Optional: if set, also assigns split
```

---

## API Endpoints

All endpoints under `/api/v1/import/` require JWT authentication.

### Sessions

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| `POST` | `/sessions` | Create import session | `multipart/form-data` with files | `{ id, status }` |
| `GET` | `/sessions` | List user's sessions | - | `[{ id, status, created_at, transaction_count }]` |
| `GET` | `/sessions/:id` | Get session details | - | `{ id, status, transactions: [...] }` |
| `DELETE` | `/sessions/:id` | Cancel/delete session | - | `204 No Content` |

### Transactions (within session)

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| `GET` | `/sessions/:id/transactions` | List extracted transactions | `?status=ready,needs_attention` | `[{ id, merchant, amount, ... }]` |
| `PUT` | `/sessions/:id/transactions/:tid` | Update categorization | `{ expense_type_id, split, merchant }` | `{ id, ... }` |
| `POST` | `/sessions/:id/transactions/:tid/skip` | Mark as skipped | - | `{ status: 'skipped' }` |
| `POST` | `/sessions/:id/import` | Import selected transactions | `{ transaction_ids: [...] }` | `{ imported_count, transaction_ids }` |

### Rules

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| `GET` | `/rules` | List all rules | `?type=expense|split` | `[{ id, keyword, maps_to }]` |
| `POST` | `/rules` | Create rule | `{ keyword, expense_type_id?, split? }` | `{ id, ... }` |
| `PUT` | `/rules/:id` | Update rule | `{ keyword?, expense_type_id?, split? }` | `{ id, ... }` |
| `DELETE` | `/rules/:id` | Delete rule | - | `204 No Content` |

### Settings

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| `GET` | `/settings` | Get import settings | - | `{ default_split, default_paid_by }` |
| `PUT` | `/settings` | Update settings | `{ default_split?, default_paid_by? }` | `{ ... }` |

---

## External Service Integration

### Document AI Options

| Service | Pros | Cons | Cost |
|---------|------|------|------|
| **Google Document AI** | High accuracy, handles tables well | Requires GCP setup | ~$1.50/1000 pages |
| **AWS Textract** | Good for structured docs | AWS dependency | ~$1.50/1000 pages |
| **OpenAI GPT-4V** | Flexible, understands context | May need prompt tuning | ~$0.01-0.03/image |
| **Claude Vision** | High accuracy, good reasoning | API access needed | ~$0.01-0.03/image |

**Recommendation:** Start with **OpenAI GPT-4V** or **Claude Vision** for flexibility. Can switch to dedicated Document AI later if volume increases.

### Integration Approach

```python
# services/document_extraction_service.py

class DocumentExtractionService:
    def extract_transactions(self, file_path: str, file_type: str) -> list[dict]:
        """
        Extract transactions from a bank statement file.

        Returns list of:
        {
            "raw_text": "WHOLE FOODS MARKET #123",
            "merchant": "Whole Foods Market",
            "amount": 87.34,
            "date": "2025-01-15",
            "confidence": 0.95
        }
        """
        if file_type == 'pdf':
            return self._extract_from_pdf(file_path)
        else:
            return self._extract_from_image(file_path)

    def _extract_from_image(self, file_path: str) -> list[dict]:
        # Use GPT-4V or Claude Vision
        prompt = """
        Extract all transactions from this bank statement image.
        For each transaction, provide:
        - raw_text: The exact text as shown
        - merchant: Cleaned merchant name
        - amount: Transaction amount (positive number)
        - date: Date in YYYY-MM-DD format
        - confidence: Your confidence 0.0-1.0

        Return as JSON array.
        """
        # ... API call implementation
```

---

## Background Processing

### Option A: Simple Threading (MVP)

For initial implementation, use Python's `concurrent.futures`:

```python
from concurrent.futures import ThreadPoolExecutor
import threading

executor = ThreadPoolExecutor(max_workers=2)

def process_import_session(session_id: int):
    """Background task to process an import session."""
    with app.app_context():
        session = ImportSession.query.get(session_id)
        session.status = 'processing'
        session.processing_started_at = datetime.utcnow()
        db.session.commit()

        try:
            # 1. Extract transactions from files
            transactions = extraction_service.extract_from_session(session)

            # 2. Apply rules and detect duplicates
            for txn in transactions:
                apply_rules(txn, session.household_id)
                check_duplicate(txn, session.household_id)

            # 3. Save extracted transactions
            db.session.add_all(transactions)
            session.status = 'ready'
            session.processing_completed_at = datetime.utcnow()
            db.session.commit()

            # 4. Send push notification
            send_push_notification(session.user_id, "Bank import ready for review")

        except Exception as e:
            session.status = 'failed'
            session.error_message = str(e)
            db.session.commit()

# In API endpoint:
@bp.route('/sessions', methods=['POST'])
def create_session():
    # ... save files and create session ...
    executor.submit(process_import_session, session.id)
    return jsonify({'id': session.id, 'status': 'pending'})
```

### Option B: Celery (Production Scale)

For production with high volume, use Celery:

```python
# tasks.py
from celery import Celery

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
def process_import_session(session_id: int):
    # Same implementation as above
    pass
```

**Recommendation:** Start with Option A (threading) for MVP. Migrate to Celery if processing queue becomes a bottleneck.

---

## Rule Matching Algorithm

```python
def apply_rules(extracted_txn: ExtractedTransaction, household_id: int):
    """Apply auto-categorization rules to an extracted transaction."""
    merchant = extracted_txn.merchant or ''
    merchant_lower = merchant.lower()

    # 1. Match expense type rules
    expense_rule = AutoCategoryRule.query.filter(
        AutoCategoryRule.household_id == household_id,
        func.lower(AutoCategoryRule.keyword).in_(
            # Check if keyword is substring of merchant
            db.session.query(AutoCategoryRule.keyword).filter(
                merchant_lower.contains(func.lower(AutoCategoryRule.keyword))
            )
        )
    ).first()

    if expense_rule:
        extracted_txn.suggested_expense_type_id = expense_rule.expense_type_id
        if expense_rule.split_category:
            extracted_txn.suggested_split = expense_rule.split_category

    # 2. Match split rules (if not already set)
    if not extracted_txn.suggested_split:
        split_rule = SplitRule.query.filter(
            SplitRule.household_id == household_id,
            merchant_lower.contains(func.lower(SplitRule.keyword))
        ).first()

        if split_rule:
            extracted_txn.suggested_split = split_rule.split_category

    # 3. Apply defaults
    if not extracted_txn.suggested_split:
        settings = ImportSettings.query.filter_by(household_id=household_id).first()
        extracted_txn.suggested_split = settings.default_split if settings else 'SHARED'

    # 4. Determine status based on confidence
    if not extracted_txn.suggested_expense_type_id or extracted_txn.confidence_score < 0.7:
        extracted_txn.status = 'needs_attention'
    else:
        extracted_txn.status = 'ready'
```

---

## Duplicate Detection

```python
def check_duplicate(extracted_txn: ExtractedTransaction, household_id: int):
    """Check if transaction already exists in the household."""
    if not extracted_txn.merchant or not extracted_txn.amount or not extracted_txn.date:
        return

    # Fuzzy merchant matching: normalize and compare
    normalized_merchant = normalize_merchant(extracted_txn.merchant)

    existing = Transaction.query.filter(
        Transaction.household_id == household_id,
        Transaction.date == extracted_txn.date,
        Transaction.amount == extracted_txn.amount,
        func.lower(Transaction.merchant).contains(normalized_merchant[:20])  # First 20 chars
    ).first()

    if existing:
        extracted_txn.status = 'duplicate'
        extracted_txn.duplicate_of_transaction_id = existing.id

def normalize_merchant(merchant: str) -> str:
    """Normalize merchant name for comparison."""
    # Remove common prefixes/suffixes
    merchant = merchant.lower()
    merchant = re.sub(r'^(sq \*|tst \*|paypal \*)', '', merchant)
    merchant = re.sub(r'#\d+$', '', merchant)
    merchant = re.sub(r'\s+', ' ', merchant).strip()
    return merchant
```

---

## File Storage

### Local Development
```python
UPLOAD_FOLDER = 'instance/uploads/imports'

def save_upload(file, session_id: int) -> str:
    filename = secure_filename(f"{session_id}_{uuid4().hex}_{file.filename}")
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    return path
```

### Production (S3)
```python
import boto3

s3 = boto3.client('s3')

def save_upload_s3(file, session_id: int) -> str:
    key = f"imports/{session_id}/{uuid4().hex}_{file.filename}"
    s3.upload_fileobj(file, BUCKET_NAME, key)
    return f"s3://{BUCKET_NAME}/{key}"
```

---

## Push Notifications

Use existing `DeviceToken` model for APNs:

```python
from apns2.client import APNsClient
from apns2.payload import Payload

def send_import_ready_notification(user_id: int, session_id: int):
    tokens = DeviceToken.query.filter_by(user_id=user_id).all()

    payload = Payload(
        alert={
            "title": "Bank Import Ready",
            "body": "Your transactions are ready to review"
        },
        badge=1,
        custom={"session_id": session_id}
    )

    for token in tokens:
        client.send_notification(token.token, payload, BUNDLE_ID)
```

---

## Security

Bank statements are **highly sensitive documents** containing account numbers, balances, transaction history, and PII. Security is critical for this feature.

### Data Classification

| Data Type | Sensitivity | Retention |
|-----------|-------------|-----------|
| Source files (PDF/images) | **Critical** | Delete immediately after import |
| ExtractedTransaction records | Medium | Permanent (no sensitive data) |
| Audit logs | Low | 90 days |

### Retention Policy

**Principle:** Don't keep what you don't need.

```
Upload → Processing → Review → Import → DELETE FILES IMMEDIATELY
                ↓
            Failed/Abandoned → DELETE AFTER 7 DAYS
```

**Implementation:**

```python
def import_transactions(session: ImportSession, transaction_ids: list[int]):
    """Import selected transactions and delete source files."""
    # ... create Transaction records ...

    # Delete source files immediately after successful import
    delete_session_files(session)

    session.source_files = '[]'
    session.status = 'completed'
    session.imported_at = datetime.utcnow()
    db.session.commit()

def delete_session_files(session: ImportSession):
    """Securely delete all files associated with a session."""
    for file_info in json.loads(session.source_files or '[]'):
        secure_delete(file_info['path'])

# Nightly cleanup job
def cleanup_stale_sessions():
    """Delete files from incomplete sessions older than 7 days."""
    cutoff = datetime.utcnow() - timedelta(days=7)
    stale = ImportSession.query.filter(
        ImportSession.created_at < cutoff,
        ImportSession.status.in_(['pending', 'ready', 'failed'])
    ).all()

    for session in stale:
        delete_session_files(session)
        session.source_files = '[]'
        session.status = 'expired'

    db.session.commit()
```

**Why this approach:**
- After import, data lives in `ExtractedTransaction` (merchant, amount, date, raw text of transaction line)
- Original statement not needed for verification (raw_text field preserved)
- Re-processing requires re-upload (acceptable trade-off for security)
- 7-day buffer handles user starting import then getting distracted

### Secure Deletion

Standard file deletion doesn't erase data. Overwrite before deleting:

```python
import os

def secure_delete(file_path: str):
    """Overwrite file with random data before deletion."""
    if not os.path.exists(file_path):
        return

    try:
        size = os.path.getsize(file_path)
        with open(file_path, 'wb') as f:
            f.write(os.urandom(size))
        os.remove(file_path)
    except Exception as e:
        # Log error but don't fail the import
        logger.error(f"Failed to securely delete {file_path}: {e}")
        # Attempt regular deletion as fallback
        try:
            os.remove(file_path)
        except:
            pass
```

### Encryption at Rest

For files during the active review window:

```python
from cryptography.fernet import Fernet

# Master key from environment variable
ENCRYPTION_KEY = os.environ.get('IMPORT_ENCRYPTION_KEY')

def save_upload_encrypted(file, session_id: int) -> dict:
    """Encrypt and save uploaded file."""
    cipher = Fernet(ENCRYPTION_KEY)
    encrypted_data = cipher.encrypt(file.read())

    filename = f"{session_id}_{uuid4().hex}.enc"
    path = os.path.join(UPLOAD_FOLDER, filename)

    with open(path, 'wb') as f:
        f.write(encrypted_data)

    return {'path': path, 'encrypted': True}

def read_upload_decrypted(file_info: dict) -> bytes:
    """Read and decrypt uploaded file for processing."""
    cipher = Fernet(ENCRYPTION_KEY)

    with open(file_info['path'], 'rb') as f:
        encrypted_data = f.read()

    return cipher.decrypt(encrypted_data)
```

**Note:** Encryption adds complexity. For MVP, may defer to Phase 5 (Polish). The short retention window (delete after import) provides significant protection.

### Access Control

**Principle:** Only the user who created the session can access it.

```python
def verify_session_access(session: ImportSession, user_id: int):
    """Verify user has access to this import session."""
    if session.user_id != user_id:
        abort(403, "Access denied")

    # Belt and suspenders: verify household membership
    if not is_household_member(user_id, session.household_id):
        abort(403, "Access denied")

@bp.route('/sessions/<int:session_id>', methods=['GET'])
@jwt_required
def get_session(session_id):
    session = ImportSession.query.get_or_404(session_id)
    verify_session_access(session, g.current_user.id)
    return jsonify(session.to_dict())
```

**File access:**
- Never expose direct file URLs
- Serve files through authenticated endpoints only
- Or use signed URLs with short expiry (5 minutes) for S3

### Data Minimization

**What we extract and store:**
- `merchant` - Needed for categorization and display
- `amount` - Needed for transaction creation
- `date` - Needed for transaction creation
- `raw_text` - Just the transaction line, not full statement

**What we explicitly DO NOT store:**
- Account numbers
- Account balances
- Routing numbers
- Full statement text
- SSN or other PII that might appear

**AI prompt instructs this explicitly:**
```
Extract ONLY transaction data from this bank statement.
DO NOT include in your response: account numbers, balances,
routing numbers, SSN, or any personally identifiable information.

For each transaction, return ONLY:
- The transaction line text
- Merchant name (cleaned)
- Amount
- Date
```

### File Validation

Prevent malicious uploads:

```python
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'heic'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILES_PER_SESSION = 10

# Magic bytes for file type verification
FILE_SIGNATURES = {
    'pdf': b'%PDF',
    'png': b'\x89PNG',
    'jpg': b'\xff\xd8\xff',
    'jpeg': b'\xff\xd8\xff',
}

def validate_upload(file) -> None:
    """Validate uploaded file for security."""
    # Check extension
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type not allowed: {ext}")

    # Check file size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {size / 1024 / 1024:.1f}MB (max 10MB)")

    # Verify magic bytes match extension (prevent extension spoofing)
    header = file.read(8)
    file.seek(0)

    if ext in FILE_SIGNATURES:
        expected = FILE_SIGNATURES[ext]
        if not header.startswith(expected):
            raise ValueError("File content doesn't match extension")
```

### Rate Limiting

Prevent abuse:

```python
from flask_limiter import Limiter

# 5 import sessions per hour per user
@bp.route('/sessions', methods=['POST'])
@jwt_required
@limiter.limit("5 per hour")
def create_session():
    ...

# 100 file uploads per day per user
@bp.route('/sessions/<int:id>/files', methods=['POST'])
@jwt_required
@limiter.limit("100 per day")
def upload_file(id):
    ...
```

### Audit Logging

Track sensitive operations for security review:

```python
class ImportAuditLog(db.Model):
    """Audit trail for import operations."""
    __tablename__ = 'import_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('import_sessions.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(200), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

def log_import_action(session_id: int, user_id: int, action: str, details: dict = None):
    """Log an import-related action."""
    log = ImportAuditLog(
        session_id=session_id,
        user_id=user_id,
        action=action,
        details=json.dumps(details) if details else None,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:200]
    )
    db.session.add(log)
    # Don't commit here - let calling code handle transaction
```

**Actions to log:**
| Action | When |
|--------|------|
| `session_created` | New import session created |
| `file_uploaded` | File uploaded to session |
| `processing_started` | Background extraction began |
| `processing_completed` | Extraction finished |
| `processing_failed` | Extraction failed |
| `transactions_imported` | User imported transactions |
| `session_deleted` | Session manually deleted |
| `files_cleaned` | Files deleted (manual or automatic) |

### Security Checklist

Before launch, verify:

- [ ] HTTPS enforced for all API endpoints
- [ ] JWT tokens validated on every request
- [ ] Session ownership checked before any access
- [ ] Files encrypted at rest (or deferred with documented risk)
- [ ] Secure deletion implemented
- [ ] File validation prevents malicious uploads
- [ ] Rate limiting active
- [ ] Audit logging captures all sensitive operations
- [ ] Nightly cleanup job scheduled
- [ ] AI prompt excludes sensitive data extraction
- [ ] No direct file URL exposure

---

## Implementation Order

### Phase 1: Backend Foundation (Week 1)

1. **Database migrations**
   - Create `ImportSession` model
   - Create `ExtractedTransaction` model
   - Create `ImportSettings` model
   - Extend `AutoCategoryRule` with optional `split_category`

2. **File upload API**
   - `POST /api/v1/import/sessions` - Upload files, create session
   - Local file storage

3. **Basic extraction (mock)**
   - Hardcoded extraction for testing
   - Rule matching logic
   - Duplicate detection

### Phase 2: AI Integration (Week 2)

4. **Document AI integration**
   - GPT-4V or Claude Vision setup
   - Extraction prompt engineering
   - Confidence scoring

5. **Background processing**
   - ThreadPoolExecutor implementation
   - Status tracking
   - Error handling

### Phase 3: Review APIs (Week 3)

6. **Session/transaction APIs**
   - `GET /sessions/:id/transactions`
   - `PUT /sessions/:id/transactions/:tid`
   - `POST /sessions/:id/import`

7. **Rules APIs**
   - Full CRUD for rules
   - Settings endpoint

### Phase 4: iOS Integration (Week 4)

8. **iOS Capture Screen**
   - Camera/photo library/PDF picker
   - File upload to backend
   - Processing status polling

9. **iOS Select/Categorize Screens**
   - Transaction list with tabs
   - Categorization forms
   - Import confirmation

10. **Push notifications**
    - APNs integration for "ready" notification
    - Deep link to review screen

### Phase 5: Polish (Week 5)

11. **Rules Management Screen** (iOS)
12. **Error handling & edge cases**
13. **Performance optimization**
14. **Testing & bug fixes**

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| OCR accuracy issues | Poor extraction quality | Medium | Show raw text, allow manual correction, learn from corrections |
| AI API costs | Budget overrun | Low | Set rate limits, cache similar documents, batch processing |
| Processing timeouts | Failed imports | Medium | Chunked processing, retry logic, timeout handling |
| Duplicate false positives | User frustration | Medium | Allow manual override, fuzzy matching threshold tuning |
| Large file uploads | Memory/storage issues | Medium | File size limits, streaming upload, cleanup old sessions |

---

## Testing Strategy

### Unit Tests
- Rule matching logic
- Duplicate detection
- Merchant normalization

### Integration Tests
- File upload → extraction → import flow
- API endpoint responses
- Database transactions

### E2E Tests (Maestro)
- Capture flow
- Select/categorize flow
- Rules management

---

## Resolved Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Which AI service? | OpenAI GPT-4V | Flexibility, easy setup, good with varied formats |
| File retention | Delete immediately after import | Security - bank statements are highly sensitive |
| Incomplete session cleanup | 7 days | Balance usability with security |
| Max files per session | 10 files, 10MB each | Reasonable limits for household use |
| Rate limiting | 5 sessions/hour, 100 uploads/day | Prevent abuse |
| Encryption at rest | Implement for production, defer for MVP | Short retention window provides protection |
| Who pays for imported transactions? | Always the user who imports | Simplest approach |
| Household member visibility | User-only | Privacy - only importer sees their sessions |
| Currency handling | Default USD, changeable per-transaction | Keeps capture simple, flexibility in review |
| Push notifications | Yes, implement for MVP | Better UX, brings user back when ready |

## Open Questions

1. **Failed extraction retry** - Should users be able to retry failed extractions, or must re-upload?
   - Recommendation: Re-upload (simpler, files may have been cleaned up)

---

## Next Steps

1. ~~Review this architecture document~~ ✓
2. Approve or request changes
3. Begin Phase 1 implementation
