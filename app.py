import os
import sys
import logging
from flask import Flask, render_template, request, jsonify, send_from_directory
from datetime import datetime, timedelta
from flask_mail import Mail, Message
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import json
import ezodf

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for static files
csrf = CSRFProtect(app)
limiter = Limiter(app, key_func=get_remote_address)

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_USERNAME')

mail = Mail(app)

# Temporary mock database
visa_database = {
    "IRL123456": {"status": "Approved", "application_date": "2023-01-01"},
    "IRL789012": {"status": "Rejected", "application_date": "2023-01-01"},
    "IRL345678": {"status": "Pending", "application_date": "2023-01-01"}
}

def calculate_working_days(start_date, end_date):
    working_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            working_days += 1
        current_date += timedelta(days=1)
    return working_days

def send_email_notification(recipient, subject, body):
    try:
        msg = Message(subject, recipients=[recipient])
        msg.body = body
        mail.send(msg)
        logger.info(f"Email sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}", exc_info=True)
        return False

@app.route('/')
def index():
    try:
        logger.info("Index route accessed")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return f"An error occurred: {str(e)}", 500

# Add this new route to get CSRF token
@app.route('/get-csrf-token')
def get_csrf_token():
    try:
        csrf_token = generate_csrf()
        logger.info(f"Generated CSRF token: {csrf_token}")
        return jsonify({'csrf_token': csrf_token})
    except Exception as e:
        logger.error(f"Error generating CSRF token: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to generate CSRF token'}), 500

@app.route("/check_status", methods=["POST"])
@limiter.limit("10 per minute")
def check_status():
    logger.info("check_status route accessed")
    try:
        logger.info(f"Received form data: {request.form}")
        
        irl_number = request.form.get("irl_number")
        application_date = request.form.get("application_date")
        email = request.form.get("email")
        
        logger.info(f"Parsed data - IRL: {irl_number}, Date: {application_date}, Email: {email}")
        
        if not all([irl_number, application_date, email]):
            logger.error("Missing required fields")
            return jsonify({"error": "Missing required fields"}), 400
        
        if irl_number in visa_database:
            visa_info = visa_database[irl_number]
            status = visa_info["status"]
            app_date = datetime.strptime(application_date, "%Y-%m-%d")
            current_date = datetime.now()
            working_days = calculate_working_days(app_date, current_date)
            
            logger.info(f"Visa status found: {status}, Working days: {working_days}")
            
            subject = f"Visa Application Status Update - {status}"
            body = f"Your visa application is {status}. It has been {working_days} working days since your application."
            email_sent = send_email_notification(email, subject, body)
            
            response_data = {
                "status": status,
                "working_days": working_days,
                "message": f"Your visa application is {status}. It has been {working_days} working days since your application.",
                "email_sent": email_sent,
                "email_error": "" if email_sent else "Failed to send email notification. Please check your email address."
            }
        else:
            status = "Pending"
            app_date = datetime.strptime(application_date, "%Y-%m-%d")
            current_date = datetime.now()
            working_days = calculate_working_days(app_date, current_date)
            
            logger.info(f"Visa status not found, assuming Pending. Working days: {working_days}")
            
            subject = "Visa Application Status Update - Pending"
            body = f"Your visa application is still Pending. It has been {working_days} working days since your application."
            email_sent = send_email_notification(email, subject, body)
            
            response_data = {
                "status": status,
                "working_days": working_days,
                "message": f"Your visa application is still Pending. It has been {working_days} working days since your application.",
                "email_sent": email_sent,
                "email_error": "" if email_sent else "Failed to send email notification. Please check your email address."
            }
        
        logger.info(f"Sending response: {json.dumps(response_data)}")
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error in check_status route: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {str(error)}", exc_info=True)
    return jsonify({"error": "Internal Server Error", "message": str(error)}), 500

@app.route('/send_email', methods=['POST'])
@limiter.limit("3 per minute")
def send_email_route():
    try:
        data = request.get_json()
        recipient = data["recipient"]
        subject = data["subject"]
        body = data["body"]

        if send_email_notification(recipient, subject, body):
            return jsonify({"success": True, "message": "Email sent successfully!"})
        else:
            return jsonify({"success": False, "message": "Error sending email"})
    except Exception as e:
        logger.error(f"Error in send_email route: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": f"Error sending email: {str(e)}"}), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    logger.info(f"Serving static file: {filename}")
    return send_from_directory(app.static_folder, filename, cache_timeout=0)

if __name__ == '__main__':
    logger.info("Starting application")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
