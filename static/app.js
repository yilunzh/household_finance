/**
 * JavaScript for Lucky Ledger
 * Warm & Friendly Theme
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
            showMessage('Transaction added! ✨', 'success');
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

// Delete transaction with custom confirm modal if available
async function deleteTransaction(transactionId) {
    // Use custom confirm if available, otherwise fallback to native
    let confirmed = false;

    if (typeof showConfirm === 'function') {
        confirmed = await showConfirm(
            'Delete Transaction?',
            'Are you sure? This action cannot be undone.',
            'danger'
        );
    } else {
        confirmed = confirm('Are you sure you want to delete this transaction?');
    }

    if (!confirmed) return;

    try {
        const response = await fetch(`/transaction/${transactionId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });

        const result = await response.json();

        if (result.success) {
            // Animate element removal (table row or mobile card)
            const row = document.querySelector(`tr[data-id="${transactionId}"]`);
            const card = document.querySelector(`div[data-id="${transactionId}"]`);

            [row, card].forEach(el => {
                if (el) {
                    el.style.transition = 'opacity 0.3s, transform 0.3s';
                    el.style.opacity = '0';
                    el.style.transform = 'translateX(-10px)';
                    setTimeout(() => el.remove(), 300);
                }
            });

            // Use toast if available
            if (typeof showToast === 'function') {
                showToast('Deleted!', 'Transaction removed', 'success');
            } else {
                showMessage('Transaction deleted! 🗑️', 'success');
            }

            // Reload page after a short delay to update summary
            setTimeout(() => {
                window.location.reload();
            }, 800);
        } else {
            if (typeof showToast === 'function') {
                showToast('Oops!', result.error, 'error');
            } else {
                showMessage('Error: ' + result.error, 'error');
            }
        }
    } catch (error) {
        showMessage('Error deleting transaction: ' + error.message, 'error');
    }
}

// Open edit modal and populate with transaction data
function openEditModal(transactionId) {
    // Try table row first (desktop), then card div (mobile)
    let element = document.querySelector(`tr[data-id="${transactionId}"]`);
    if (!element) {
        element = document.querySelector(`div[data-id="${transactionId}"]`);
    }
    if (!element) {
        console.error('Transaction element not found');
        return;
    }

    // Populate form fields from data attributes
    document.getElementById('edit-transaction-id').value = transactionId;
    document.getElementById('edit-date').value = element.dataset.date;
    document.getElementById('edit-merchant').value = element.dataset.merchant;
    document.getElementById('edit-amount').value = element.dataset.amount;
    document.getElementById('edit-currency').value = element.dataset.currency;
    document.getElementById('edit-paid-by').value = element.dataset.paidBy;
    document.getElementById('edit-category').value = element.dataset.category;
    document.getElementById('edit-notes').value = element.dataset.notes || '';

    // Show modal with animation
    const modal = document.getElementById('edit-modal');
    modal.classList.remove('hidden');

    // Focus merchant field for quick editing
    setTimeout(() => {
        document.getElementById('edit-merchant').focus();
        document.getElementById('edit-merchant').select();
    }, 100);
}

// Close edit modal
function closeEditModal() {
    const modal = document.getElementById('edit-modal');
    modal.classList.add('hidden');

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
            showEditMessage('Updated! ✓', 'success');
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

// Show message in edit modal - warm theme
function showEditMessage(message, type) {
    const messageDiv = document.getElementById('edit-form-message');
    if (!messageDiv) return;

    // Warm theme classes
    const classes = type === 'success'
        ? 'bg-sage-50 text-sage-700 border border-sage-200'
        : 'bg-rose-50 text-rose-600 border border-rose-200';

    const icon = type === 'success' ? '✅' : '😟';

    messageDiv.className = `mt-4 p-4 rounded-2xl flex items-center gap-2 animate-fade-in ${classes}`;
    messageDiv.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    messageDiv.classList.remove('hidden');

    setTimeout(() => {
        messageDiv.classList.add('hidden');
    }, 5000);
}

// Show status message - warm theme
function showMessage(message, type) {
    const messageDiv = document.getElementById('form-message');
    if (!messageDiv) return;

    // Warm theme classes
    const classes = type === 'success'
        ? 'bg-sage-50 text-sage-700 border border-sage-200'
        : 'bg-rose-50 text-rose-600 border border-rose-200';

    const icon = type === 'success' ? '✅' : '😟';

    messageDiv.className = `mt-4 p-4 rounded-2xl flex items-center gap-2 animate-slide-up ${classes}`;
    messageDiv.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    messageDiv.classList.remove('hidden');

    // Auto-hide after 5 seconds
    setTimeout(() => {
        messageDiv.classList.add('hidden');
    }, 5000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Lucky Ledger loaded 🏠');

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
            const editModal = document.getElementById('edit-modal');
            if (editModal && !editModal.classList.contains('hidden')) {
                closeEditModal();
            }

            const confirmModal = document.getElementById('confirm-modal');
            if (confirmModal && !confirmModal.classList.contains('hidden')) {
                confirmModal.classList.add('hidden');
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

    // Close confirm modal when clicking backdrop
    const confirmModal = document.getElementById('confirm-modal');
    if (confirmModal) {
        confirmModal.addEventListener('click', function(e) {
            if (e.target === confirmModal) {
                confirmModal.classList.add('hidden');
            }
        });
    }
});
