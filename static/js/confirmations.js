// Confirmation dialogs using Bootstrap modals

let currentAction = null;

function showModal(title, message, confirmCallback, btnText = 'Confirm', btnClass = 'btn-danger') {
    document.getElementById('confirmModalLabel').textContent = title;
    document.getElementById('confirmModalBody').textContent = message;
    
    currentAction = confirmCallback;
    
    // Configure Action Button
    const actionBtn = document.getElementById('confirmModalActionBtn');
    actionBtn.textContent = btnText;
    actionBtn.className = `btn ${btnClass}`;
    actionBtn.style.display = 'inline-block';

    // Show Cancel Button
    document.getElementById('confirmModalCancelBtn').style.display = 'inline-block';
    
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    modal.show();
}

function showAlert(title, message) {
    document.getElementById('confirmModalLabel').textContent = title;
    document.getElementById('confirmModalBody').textContent = message;
    
    currentAction = null;
    
    // Configure Action Button (OK)
    const actionBtn = document.getElementById('confirmModalActionBtn');
    actionBtn.textContent = 'OK';
    actionBtn.className = 'btn btn-primary';
    actionBtn.style.display = 'inline-block';

    // Hide Cancel Button
    document.getElementById('confirmModalCancelBtn').style.display = 'none';
    
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    modal.show();
}

function confirmAction() {
    if (currentAction) {
        currentAction();
        currentAction = null;
    }
    bootstrap.Modal.getInstance(document.getElementById('confirmModal')).hide();
}

function confirmDeleteEmployee(employeeId, employeeName) {
    showModal(
        'Delete Employee',
        `Are you sure you want to delete ${employeeName}?\n\nThis action cannot be undone.`,
        () => {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/delete_employee/${employeeId}`;
            document.body.appendChild(form);
            form.submit();
        }
    );
}

function confirmCancelLeave(leaveId) {
    showModal(
        'Cancel Leave',
        'Are you sure you want to cancel this leave application?\n\nThis will refund your leave days.',
        () => {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/cancel_leave/${leaveId}`;
            document.body.appendChild(form);
            form.submit();
        }
    );
}

function confirmRejectLeave(leaveId, employeeName) {
    // For reject, we'll use a custom modal with input
    document.getElementById('rejectModalLabel').textContent = `Reject Leave - ${employeeName}`;
    document.getElementById('rejectLeaveId').value = leaveId;
    document.getElementById('rejectReason').value = '';
    
    const modal = new bootstrap.Modal(document.getElementById('rejectModal'));
    modal.show();
}

function submitRejectLeave() {
    const leaveId = document.getElementById('rejectLeaveId').value;
    const reason = document.getElementById('rejectReason').value;
    
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/admin/reject_leave/${leaveId}`;
    
    if (reason.trim()) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'reason';
        input.value = reason;
        form.appendChild(input);
    }
    
    document.body.appendChild(form);
    form.submit();
}
