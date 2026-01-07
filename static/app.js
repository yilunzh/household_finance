/**
 * JavaScript for Zhang Estate Expense Tracker
 */

// Helper function to get CSRF token
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

// Handle transaction form submission
async function handleTransactionSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    // Build JSON payload
    const data = {
        date: formData.get('date'),
        merchant: formData.get('merchant'),
        amount: parseFloat(formData.get('amount')),
        currency: formData.get('currency'),
        paid_by: formData.get('paid_by'),
        category: formData.get('category'),
        notes: document.getElementById('notes').value
    };

    try {
        const response = await fetch('/transaction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            // Show success message
            showMessage('Transaction added successfully!', 'success');

            // Reload page to show new transaction
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            showMessage('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showMessage('Error adding transaction: ' + error.message, 'error');
    }
}

// Delete transaction
async function deleteTransaction(transactionId) {
    if (!confirm('Are you sure you want to delete this transaction?')) {
        return;
    }

    try {
        const response = await fetch(`/transaction/${transactionId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        const result = await response.json();

        if (result.success) {
            // Remove row from table
            const row = document.querySelector(`tr[data-id="${transactionId}"]`);
            if (row) {
                row.remove();
            }

            showMessage('Transaction deleted successfully!', 'success');

            // Reload page after a short delay to update summary
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            showMessage('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showMessage('Error deleting transaction: ' + error.message, 'error');
    }
}

// Open edit modal and populate with transaction data
function openEditModal(transactionId) {
    const row = document.querySelector(`tr[data-id="${transactionId}"]`);
    if (!row) {
        console.error('Transaction row not found');
        return;
    }

    // Populate form fields from data attributes
    document.getElementById('edit-transaction-id').value = transactionId;
    document.getElementById('edit-date').value = row.dataset.date;
    document.getElementById('edit-merchant').value = row.dataset.merchant;
    document.getElementById('edit-amount').value = row.dataset.amount;
    document.getElementById('edit-currency').value = row.dataset.currency;
    document.getElementById('edit-paid-by').value = row.dataset.paidBy;
    document.getElementById('edit-category').value = row.dataset.category;
    document.getElementById('edit-notes').value = row.dataset.notes || '';

    // Show modal
    document.getElementById('edit-modal').classList.remove('hidden');

    // Focus merchant field for quick editing
    setTimeout(() => {
        document.getElementById('edit-merchant').focus();
        document.getElementById('edit-merchant').select();
    }, 100);
}

// Close edit modal
function closeEditModal() {
    document.getElementById('edit-modal').classList.add('hidden');

    const messageDiv = document.getElementById('edit-form-message');
    if (messageDiv) {
        messageDiv.classList.add('hidden');
    }
}

// Handle edit form submission
async function handleEditSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const transactionId = document.getElementById('edit-transaction-id').value;

    const data = {
        date: formData.get('date'),
        merchant: formData.get('merchant'),
        amount: parseFloat(formData.get('amount')),
        currency: formData.get('currency'),
        paid_by: formData.get('paid_by'),
        category: formData.get('category'),
        notes: document.getElementById('edit-notes').value
    };

    try {
        const response = await fetch(`/transaction/${transactionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            showEditMessage('Transaction updated successfully!', 'success');
            setTimeout(() => {
                closeEditModal();
                window.location.reload();
            }, 500);
        } else {
            showEditMessage('Error: ' + result.error, 'error');
        }
    } catch (error) {
        showEditMessage('Error updating transaction: ' + error.message, 'error');
    }
}

// Show message in edit modal
function showEditMessage(message, type) {
    const messageDiv = document.getElementById('edit-form-message');
    if (!messageDiv) return;

    messageDiv.className = `mt-4 p-4 rounded-lg ${
        type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
    }`;
    messageDiv.textContent = message;
    messageDiv.classList.remove('hidden');

    setTimeout(() => {
        messageDiv.classList.add('hidden');
    }, 5000);
}

// Show status message
function showMessage(message, type) {
    const messageDiv = document.getElementById('form-message');
    if (!messageDiv) return;

    messageDiv.className = `mt-4 p-4 rounded-lg ${
        type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
    }`;
    messageDiv.textContent = message;
    messageDiv.classList.remove('hidden');

    // Auto-hide after 5 seconds
    setTimeout(() => {
        messageDiv.classList.add('hidden');
    }, 5000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Zhang Estate Expense Tracker loaded');

    // Auto-focus merchant field for quick entry
    const merchantField = document.getElementById('merchant');
    if (merchantField) {
        merchantField.focus();
    }

    // Add keyboard shortcut for quick entry (Ctrl/Cmd + Enter to submit)
    const form = document.getElementById('add-transaction-form');
    if (form) {
        form.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                form.dispatchEvent(new Event('submit'));
            }
        });
    }

    // Register edit form submit handler
    const editForm = document.getElementById('edit-transaction-form');
    if (editForm) {
        editForm.addEventListener('submit', handleEditSubmit);
    }

    // Close modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('edit-modal');
            if (modal && !modal.classList.contains('hidden')) {
                closeEditModal();
            }
        }
    });

    // Close modal when clicking backdrop
    const modal = document.getElementById('edit-modal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeEditModal();
            }
        });
    }
});
