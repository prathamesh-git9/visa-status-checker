document.getElementById('status-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    fetch('/check_status', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        let resultHtml = '';
        if (data.status === 'Not Found') {
            resultHtml = `<p>${data.message}</p>`;
        } else {
            resultHtml = `
                <h2>Visa Application Status: ${data.status}</h2>
                <p>Working days since application: ${data.working_days}</p>
                <p>${data.message}</p>
                <p>Email notification: ${data.email_sent ? 'Sent' : 'Failed to send'}</p>
            `;
        }
        document.getElementById('result').innerHTML = resultHtml;
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('result').innerHTML = '<p>An error occurred. Please try again later.</p>';
    });
});
