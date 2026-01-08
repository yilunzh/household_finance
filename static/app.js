/**
 * JavaScript for Lucky Ledger
 * Warm & Friendly Theme
 */

// Cat-themed SVG icons for JavaScript usage (matching _icons.html)
const CAT_ICONS = {
    sparkle: `<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="8" r="5"/><path d="M7 5L5 2M17 5l2-3"/><ellipse cx="10" cy="7" rx="0.5" ry="1"/><ellipse cx="14" cy="7" rx="0.5" ry="1"/><ellipse cx="12" cy="9" rx="0.7" ry="0.5"/><path d="M10 10.5q2 1.5 4 0"/><line x1="7" y1="8" x2="4" y2="7"/><line x1="17" y1="8" x2="20" y2="7"/><path d="M6 16l2-2M18 16l-2-2M8 20l1-3M16 20l-1-3"/><circle cx="6" cy="16" r="1.5" fill="currentColor" opacity="0.3"/><circle cx="18" cy="16" r="1.5" fill="currentColor" opacity="0.3"/><circle cx="8" cy="20" r="1" fill="currentColor" opacity="0.3"/><circle cx="16" cy="20" r="1" fill="currentColor" opacity="0.3"/>
    </svg>`,
    happy: `<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="13" r="8"/><path d="M6 8L4 4M18 8l2-4"/><path d="M9 11q1.5-1 3 0"/><path d="M12 11q1.5-1 3 0"/><ellipse cx="12" cy="14" rx="1" ry="0.7"/><path d="M9 16q3 3 6 0"/><line x1="5" y1="12" x2="2" y2="11"/><line x1="19" y1="12" x2="22" y2="11"/>
    </svg>`,
    worried: `<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="13" r="8"/><path d="M6 8L4 4M18 8l2-4"/><circle cx="9" cy="11" r="1.5"/><circle cx="15" cy="11" r="1.5"/><circle cx="9.5" cy="10.5" r="0.5" fill="currentColor"/><circle cx="15.5" cy="10.5" r="0.5" fill="currentColor"/><ellipse cx="12" cy="14" rx="1" ry="0.7"/><path d="M9 17q3-2 6 0"/><line x1="5" y1="13" x2="2" y2="14"/><line x1="19" y1="13" x2="22" y2="14"/><path d="M8 8l2 1M16 8l-2 1" stroke-width="1"/>
    </svg>`,
    trash: `<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="8" r="5"/><path d="M7 5L5 2M17 5l2-3"/><ellipse cx="10" cy="7" rx="0.5" ry="1"/><ellipse cx="14" cy="7" rx="0.5" ry="1"/><ellipse cx="12" cy="9" rx="0.7" ry="0.5"/><line x1="7" y1="8" x2="4" y2="7"/><line x1="17" y1="8" x2="20" y2="7"/><path d="M8 14h8M7 16h10l-1 6H8l-1-6M10 16v4M14 16v4"/>
    </svg>`,
    house: `<svg class="w-4 h-4 inline-block" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 10L12 3l9 7v11H3V10z"/><circle cx="12" cy="9" r="3"/><path d="M10 7.5l-1-2M14 7.5l1-2"/><circle cx="11" cy="8.5" r="0.3" fill="currentColor"/><circle cx="13" cy="8.5" r="0.3" fill="currentColor"/><ellipse cx="12" cy="9.5" rx="0.4" ry="0.3"/><rect x="9" y="14" width="6" height="7"/>
    </svg>`
};

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
            showMessage('Transaction added!', 'success');
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
                showMessage('Transaction deleted!', 'success');
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

    const icon = type === 'success' ? CAT_ICONS.happy : CAT_ICONS.worried;

    messageDiv.className = `mt-4 p-4 rounded-2xl flex items-center gap-2 animate-fade-in ${classes}`;
    messageDiv.innerHTML = `${icon}<span>${message}</span>`;
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

    const icon = type === 'success' ? CAT_ICONS.happy : CAT_ICONS.worried;

    messageDiv.className = `mt-4 p-4 rounded-2xl flex items-center gap-2 animate-slide-up ${classes}`;
    messageDiv.innerHTML = `${icon}<span>${message}</span>`;
    messageDiv.classList.remove('hidden');

    // Auto-hide after 5 seconds
    setTimeout(() => {
        messageDiv.classList.add('hidden');
    }, 5000);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Lucky Ledger loaded');

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
