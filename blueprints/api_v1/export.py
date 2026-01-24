"""
Export API routes for mobile app.

Endpoints:
- GET /api/v1/export/transactions - Export transactions as CSV
- GET /api/v1/export/transactions/<month> - Export transactions for specific month
"""
import csv
from io import StringIO
from flask import g, Response, request

from models import Transaction, HouseholdMember
from api_decorators import jwt_required, api_household_required
from blueprints.api_v1 import api_v1_bp
from utils import calculate_reconciliation


@api_v1_bp.route('/export/transactions', methods=['GET'])
@jwt_required
@api_household_required
def api_export_all_transactions():
    """Export all transactions as CSV.

    Query params (all optional):
        - start_date: YYYY-MM-DD
        - end_date: YYYY-MM-DD
        - category: filter by category code

    Returns:
        CSV file download
    """
    household_id = g.household_id

    # Get household members
    members = HouseholdMember.query.filter_by(household_id=household_id).all()

    # Build query
    query = Transaction.query.filter_by(household_id=household_id)

    # Apply filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if category:
        query = query.filter(Transaction.category == category)

    transactions = query.order_by(Transaction.date.desc()).all()

    # Generate CSV
    csv_content = _generate_transactions_csv(transactions, members)

    filename = 'transactions'
    if start_date or end_date:
        filename = f'transactions_{start_date or "start"}_{end_date or "end"}'

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={filename}.csv'
        }
    )


@api_v1_bp.route('/export/transactions/<month>', methods=['GET'])
@jwt_required
@api_household_required
def api_export_monthly_transactions(month):
    """Export transactions for a specific month as CSV.

    Args:
        month: YYYY-MM format

    Returns:
        CSV file with transactions and summary
    """
    household_id = g.household_id

    # Validate month format
    if not month or len(month) != 7 or month[4] != '-':
        return Response(
            'Invalid month format. Use YYYY-MM',
            status=400
        )

    # Get household members
    members = HouseholdMember.query.filter_by(household_id=household_id).all()

    # Get transactions for this month
    transactions = Transaction.query.filter_by(
        household_id=household_id,
        month_year=month
    ).order_by(Transaction.date).all()

    # Generate CSV with summary
    csv_content = _generate_monthly_csv(transactions, members, month)

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=expenses_{month}.csv'
        }
    )


def _generate_transactions_csv(transactions, members):
    """Generate CSV content for transactions."""
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Date', 'Merchant', 'Amount', 'Currency', 'Amount (USD)',
        'Paid By', 'Category', 'Expense Type', 'Notes'
    ])

    # Data rows
    for txn in transactions:
        writer.writerow([
            txn.date.strftime('%Y-%m-%d'),
            txn.merchant,
            f'{float(txn.amount):.2f}',
            txn.currency,
            f'{float(txn.amount_in_usd):.2f}',
            txn.get_paid_by_display_name(),
            Transaction.get_category_display_name(txn.category, members),
            txn.expense_type.name if txn.expense_type else '',
            txn.notes or ''
        ])

    output.seek(0)
    return output.getvalue()


def _generate_monthly_csv(transactions, members, month):
    """Generate CSV content for monthly export with summary."""
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Date', 'Merchant', 'Amount', 'Currency', 'Amount (USD)',
        'Paid By', 'Category', 'Expense Type', 'Notes'
    ])

    # Data rows
    for txn in transactions:
        writer.writerow([
            txn.date.strftime('%Y-%m-%d'),
            txn.merchant,
            f'{float(txn.amount):.2f}',
            txn.currency,
            f'{float(txn.amount_in_usd):.2f}',
            txn.get_paid_by_display_name(),
            Transaction.get_category_display_name(txn.category, members),
            txn.expense_type.name if txn.expense_type else '',
            txn.notes or ''
        ])

    # Add summary section
    summary = calculate_reconciliation(transactions, members)
    writer.writerow([])
    writer.writerow(['SUMMARY'])
    writer.writerow([f'Month: {month}'])
    writer.writerow([])

    # Member payment totals
    for member in members:
        user_id = member.user_id
        if user_id in summary.get('user_payments', {}):
            paid_amount = summary['user_payments'][user_id]
            writer.writerow([f'{member.display_name} paid', f'${paid_amount:.2f}'])

    writer.writerow([])
    writer.writerow(['Settlement', summary['settlement']])

    output.seek(0)
    return output.getvalue()
