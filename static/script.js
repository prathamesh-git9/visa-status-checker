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
    try {
        const response = await fetch('/get-csrf-token');
        const data = await response.json();
        console.log('CSRF Token:', data.csrf_token);
        return data.csrf_token;
    } catch (error) {
        console.error('Error fetching CSRF token:', error);
        throw error;
    }
}

document.getElementById('status-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    console.log('Form submitted');
    
    const formData = new FormData(this);
    console.log('Form data:', Object.fromEntries(formData));
    
    try {
        const csrfToken = await getCsrfToken();
        console.log('CSRF token obtained');
        
        showLoading();
        console.log('Sending request to /check_status');
        
        const response = await fetch('/check_status', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        });
        
        console.log('Response received:', response.status);
        
        if (response.status === 429) {
            throw new Error('Too many requests. Please wait a moment before trying again.');
        }
        
        const data = await response.json();
        console.log('Parsed response data:', data);
        
        hideLoading();
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}, message: ${data.error || data.message || 'Unknown error'}`);
        }
        
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
    } catch (error) {
        console.error('Error in form submission:', error);
        hideLoading();
        let errorMessage = error.message || 'An error occurred. Please try again later.';
        document.getElementById('result').innerHTML = `<p>${errorMessage}</p>`;
        showNotification(errorMessage, 'error');
    }
});

function sendEmail(recipient, subject, body) {
    const emailData = {
        recipient: recipient,
        subject: subject,
        body: body
    };

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
