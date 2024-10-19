function showLoading() {
    document.getElementById('loading').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showNotification(message, type) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.add('show');
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

async function getCsrfToken() {
    const response = await fetch('/get-csrf-token');
    const data = await response.json();
    console.log('CSRF Token:', data.csrf_token);  // Log the CSRF token
    return data.csrf_token;
}

document.getElementById('status-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    const csrfToken = await getCsrfToken();
    
    showLoading();
    
    fetch('/check_status', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        hideLoading();
        console.log('Received data:', data);  // Log the received data
        let resultHtml = '';
        if (data.status === 'Not Found') {
            resultHtml = `<p>${data.message}</p>`;
            showNotification(data.message, 'error');
        } else {
            resultHtml = `
                <h2>Visa Application Status: ${data.status}</h2>
                <p>Working days since application: ${data.working_days}</p>
                <p>${data.message}</p>
                <p>Email notification: ${data.email_sent ? 'Sent successfully' : 'Failed to send'}</p>
            `;
            if (data.email_error) {
                resultHtml += `<p class="error">${data.email_error}</p>`;
                showNotification(data.email_error, 'error');
            } else {
                showNotification('Status checked successfully', 'success');
            }
        }
        document.getElementById('result').innerHTML = resultHtml;
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        document.getElementById('result').innerHTML = '<p>An error occurred. Please try again later.</p>';
        showNotification('An error occurred. Please try again later.', 'error');
    });
});

function sendEmail() {
    // ... (existing code to prepare email data)

    fetch('/send_email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(emailData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
        } else {
            showNotification(data.message, 'error');
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        showNotification('An error occurred while sending the email. Please try again.', 'error');
    });
}
