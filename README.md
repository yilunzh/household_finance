# Household Expense Tracker

A web application for tracking and reconciling shared expenses between household members.

## Features

- **Multi-user authentication** with secure login
- **Multi-household support** - users can belong to multiple households
- **Quick transaction entry** with receipt photo uploads
- **Multi-currency support** (USD/CAD) with automatic conversion
- **Monthly reconciliation** with settlement locking
- **Budget tracking** with custom expense types and split rules
- **Transaction search/filter** with collapsible sidebar
- **Email invitations** for adding household members
- **REST API** for mobile app integration
- **CSV export** for external analysis

## Setup

### Prerequisites

- Python 3.9 or higher
- pip

### Installation

1. Clone or navigate to the repository:
```bash
cd household_tracker
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Mac/Linux
# or
venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy environment file:
```bash
cp .env.example .env
```

5. Generate a secret key and update `.env`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Running the Application

```bash
python app.py
```

Then open your browser to `http://localhost:5001`

**Note**: Using port 5001 to avoid conflict with macOS AirPlay Receiver which uses port 5000 by default.

## Usage

### Adding Transactions

1. Fill in the quick add form at the top of the page
2. Select the date, merchant, amount, currency, who paid, and category
3. Optionally attach a receipt photo
4. Click "Add Transaction"

### Viewing Reconciliation

1. Click "View Reconciliation" to see monthly summaries
2. See breakdown by category and who owes whom
3. Lock months as settled when payments are made
4. Export to CSV if needed

### Split Categories

- **Shared**: Expenses split according to household split rules (default 50/50)
- **Member A pays for Member B**: Member B owes 100%
- **Personal**: Individual expenses, not shared

## Development

See `docs/SPEC.md` for detailed technical specification.

### Running Tests

```bash
pytest tests/
```

## Deployment

See `docs/DEPLOYMENT.md` for step-by-step deployment instructions.

## License

MIT
