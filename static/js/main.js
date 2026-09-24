function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.setAttribute('role', 'alert');
    alertDiv.innerHTML = `
        <button type="button" class="btn-close" data-dismiss="alert" aria-label="Close"></button>
        ${message}
    `;
    
    const container = document.querySelector('.container') || document.body;
    container.insertBefore(alertDiv, container.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function validateEmail(email) {
    const re = /^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$/;
    return re.test(String(email).toLowerCase());
}

function validatePhone(phone) {
    const re = /^[\d+\-\s()]{10,}$/;
    return re.test(phone);
}

function validatePassword(password) {
    return password.length >= 6;
}

async function submitForm(formId, endpoint, method = 'POST') {
    const form = document.getElementById(formId);
    if (!form) {
        console.error('Form not found');
        return;
    }
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData);
    
    try {
        const response = await fetch(endpoint, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(result.message || 'Success!', 'success');
            if (result.redirect) {
                setTimeout(() => window.location.href = result.redirect, 1500);
            }
        } else {
            const errors = result.errors || ['An error occurred'];
            errors.forEach(error => showAlert(error, 'danger'));
        }
        
        return result;
    } catch (error) {
        console.error('Error:', error);
        showAlert('An error occurred. Please try again.', 'danger');
    }
}

// Close alert
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('btn-close')) {
        e.target.closest('.alert').remove();
    }
});
