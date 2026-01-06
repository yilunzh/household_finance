"""
Main Flask application for household expense tracker.
"""
import os
import csv
from io import StringIO
from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime
from decimal import Decimal

from models import db, Transaction
from utils import get_exchange_rate, calculate_reconciliation

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)


@app.route('/')
def index():
    """Main page with transaction form and list."""
    # Get month from query params, default to current month
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))

    # Get all transactions for the month
    transactions = Transaction.query.filter_by(
        month_year=month
    ).order_by(Transaction.date.desc()).all()

    # Calculate quick summary
    summary = calculate_reconciliation(transactions) if transactions else None

    # Get list of available months for dropdown
    all_months = db.session.query(Transaction.month_year).distinct().order_by(
        Transaction.month_year.desc()
    ).all()
    months = [m[0] for m in all_months]

    return render_template(
        'index.html',
        transactions=transactions,
        current_month=month,
        months=months,
        summary=summary
    )


@app.route('/transaction', methods=['POST'])
def add_transaction():
    """Add a new transaction."""
    try:
        data = request.json

        # Parse date
        txn_date = datetime.strptime(data['date'], '%Y-%m-%d').date()

        # Get exchange rate if needed
        amount = Decimal(str(data['amount']))
        currency = data['currency']

        if currency == 'CAD':
            rate = get_exchange_rate('CAD', 'USD', txn_date)
            amount_in_usd = amount * Decimal(str(rate))
        else:
            amount_in_usd = amount

        # Create transaction
        transaction = Transaction(
            date=txn_date,
            merchant=data['merchant'],
            amount=amount,
            currency=currency,
            amount_in_usd=amount_in_usd,
            paid_by=data['paid_by'],
            category=data['category'],
            notes=data.get('notes', ''),
            month_year=txn_date.strftime('%Y-%m')
        )

        db.session.add(transaction)
        db.session.commit()

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/transaction/<int:transaction_id>', methods=['PUT'])
def update_transaction(transaction_id):
    """Update an existing transaction."""
    try:
        transaction = Transaction.query.get_or_404(transaction_id)
        data = request.json

        # Update fields
        if 'date' in data:
            transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            transaction.month_year = transaction.date.strftime('%Y-%m')

        if 'merchant' in data:
            transaction.merchant = data['merchant']

        if 'amount' in data or 'currency' in data:
            amount = Decimal(str(data.get('amount', transaction.amount)))
            currency = data.get('currency', transaction.currency)

            transaction.amount = amount
            transaction.currency = currency

            # Recalculate amount_in_usd
            if currency == 'CAD':
                rate = get_exchange_rate('CAD', 'USD', transaction.date)
                transaction.amount_in_usd = amount * Decimal(str(rate))
            else:
                transaction.amount_in_usd = amount

        if 'paid_by' in data:
            transaction.paid_by = data['paid_by']

        if 'category' in data:
            transaction.category = data['category']

        if 'notes' in data:
            transaction.notes = data['notes']

        db.session.commit()

        return jsonify({
            'success': True,
            'transaction': transaction.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/transaction/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    """Delete a transaction."""
    try:
        transaction = Transaction.query.get_or_404(transaction_id)
        db.session.delete(transaction)
        db.session.commit()

        return jsonify({
            'success': True
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/reconciliation')
@app.route('/reconciliation/<month>')
def reconciliation(month=None):
    """Show monthly reconciliation summary."""
    if month is None:
        month = datetime.now().strftime('%Y-%m')

    # Get all transactions for the month
    transactions = Transaction.query.filter_by(month_year=month).all()

    # Calculate reconciliation
    summary = calculate_reconciliation(transactions)

    # Get list of available months
    all_months = db.session.query(Transaction.month_year).distinct().order_by(
        Transaction.month_year.desc()
    ).all()
    months = [m[0] for m in all_months]

    return render_template(
        'reconciliation.html',
        summary=summary,
        month=month,
        months=months,
        transactions=transactions
    )


@app.route('/export/<month>')
def export_csv(month):
    """Export transactions for a month as CSV."""
    transactions = Transaction.query.filter_by(
        month_year=month
    ).order_by(Transaction.date).all()

    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Date', 'Merchant', 'Amount', 'Currency', 'Amount (CAD)',
        'Paid By', 'Category', 'Notes'
    ])

    # Write transactions
    for txn in transactions:
        writer.writerow([
            txn.date.strftime('%Y-%m-%d'),
            txn.merchant,
            f'{float(txn.amount):.2f}',
            txn.currency,
            f'{float(txn.amount_in_cad):.2f}',
            txn.paid_by,
            Transaction.get_category_display_name(txn.category),
            txn.notes or ''
        ])

    # Add summary
    summary = calculate_reconciliation(transactions)
    writer.writerow([])
    writer.writerow(['SUMMARY'])
    writer.writerow(['I paid', f"${summary['me_paid']:.2f}"])
    writer.writerow(['Wife paid', f"${summary['wife_paid']:.2f}"])
    writer.writerow(['My share', f"${summary['me_share']:.2f}"])
    writer.writerow(['Wife\'s share', f"${summary['wife_share']:.2f}"])
    writer.writerow([])
    writer.writerow(['Settlement', summary['settlement']])

    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=expenses_{month}.csv'
        }
    )


@app.cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    print('Database initialized!')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Use port 5001 to avoid conflict with macOS AirPlay Receiver
    app.run(debug=True, host='0.0.0.0', port=5001)
