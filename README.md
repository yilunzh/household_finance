# Zhang Estate Expense Tracker

A simple web application for tracking and reconciling household expenses between two people.

## Features

- Quick transaction entry
- Multi-currency support (USD/CAD)
- Automatic currency conversion
- Monthly reconciliation calculations
- CSV export

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
3. Click "Add Transaction"

### Viewing Reconciliation

1. Click "View Reconciliation" to see who owes what
2. See breakdown by category
3. Export to CSV if needed

### Categories

- **Shared 50/50**: Expenses split equally
- **I pay for wife**: Wife owes 100%
- **Wife pays for me**: I owe 100%
- **Personal (Me)**: My personal expense
- **Personal (Wife)**: Wife's personal expense

## Development

See `SPEC.md` for detailed technical specification.

## Deployment

Recommended options:
- Railway: $5/month
- PythonAnywhere: $5/month
- DigitalOcean: $6/month

See `SPEC.md` for deployment instructions.
