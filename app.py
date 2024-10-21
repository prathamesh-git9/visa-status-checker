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
import pandas as pd
import numpy as np

# Set up logging
logging.basicConfig(filename='visa_debug.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for static files
csrf = CSRFProtect(app)
limiter = Limiter(app, key_func=get_remote_address)

# Email configuration
os.environ['EMAIL_USERNAME'] = 'prathamesh8459ie@gmail.com'
os.environ['EMAIL_PASSWORD'] = 'mdib irmc jwve cibt'
os.environ['MAIL_DEFAULT_SENDER'] = 'prathamesh8459ie@gmail.com'

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

mail = Mail(app)

def process_row(row):
    if len(row) >= 2:
        application_number = row[0].value  # Access the cell value directly
        decision = row[1].value  # Access the cell value directly
        if application_number and decision:
            application_number = str(application_number).strip()
            decision = str(decision).strip()
            print(f"Processing application: {application_number}, decision: {decision}")
            if decision.lower() == "approved":
                return application_number, {"status": "Approved", "application_date": "2024-01-01"}
    return None, None

def read_ods_file(file_path):
    logging.debug("Reading visa_status.ods file...")
    df = pd.read_excel(file_path, engine="odf", header=None)
    logging.debug(f"Total rows in sheet: {len(df)}")
    return df

def process_visa_row(row):
    if pd.notna(row[2]) and pd.notna(row[3]):
        application_number = str(row[2]).strip()
        decision = str(row[3]).strip().lower()
        if decision in ["approved", "refused"]:
            return application_number, {"status": decision.capitalize(), "application_date": "2024-01-01"}
    return None, None

def process_dataframe(df):
    visa_database = {}
    for index in range(len(df) - 1, -1, -1):
        row = df.iloc[index]
        application_number, visa_info = process_visa_row(row)
        
        if application_number == "Application Number":
            break
        
        if application_number and visa_info:
            visa_database[application_number] = visa_info
    return visa_database

def load_visa_database():
    if not os.path.exists('visa_status.ods'):
        print("visa_status.ods file not found. Using empty database.")
        return {}

    try:
        df = read_ods_file('visa_status.ods')
        visa_database = process_dataframe(df)
        print_database_summary(visa_database)
        return visa_database
    except Exception as e:
        print(f"Error loading visa database: {str(e)}")
        return {}

def print_database_summary(visa_database):
    print(f"Loaded {len(visa_database)} visa records from visa_status.ods")
    print(f"First 10 entries: {dict(list(visa_database.items())[:10])}")
    print(f"Last 10 entries: {dict(list(visa_database.items())[-10:])}")
    print(f"Is 68728912 in database? {visa_database.get('68728912', 'Not found')}")

# Make sure to reload the visa database after making changes
visa_database = load_visa_database()

def calculate_working_days(start_date, end_date):
    working_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5: 
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
    print("check_status route accessed")
    try:
        print(f"Received form data: {request.form}")
        
        application_number = request.form.get("application_number").split('.')[0]  # Remove decimal point if present
        application_date = request.form.get("application_date")
        email = request.form.get("email")
        
        print(f"Parsed data - Application Number: {application_number}, Date: {application_date}, Email: {email}")
        print(f"Is {application_number} in visa_database? {application_number in visa_database}")
        print(f"Visa database entry for {application_number}: {visa_database.get(application_number, 'Not found')}")
        
        if not application_number or not application_date or not email:
            missing_fields = []
            if not application_number:
                missing_fields.append("application_number")
            if not application_date:
                missing_fields.append("application_date")
            if not email:
                missing_fields.append("email")
            error_message = f"Missing required fields: {', '.join(missing_fields)}"
            print(error_message)
            return jsonify({"error": error_message}), 400
        
        print(f"Checking if {application_number} is in visa_database")
        if application_number in visa_database:
            visa_info = visa_database[application_number]
            status = visa_info["status"]
            print(f"Application {application_number} found in database. Status: {status}")
        else:
            status = "Not Found"
            print(f"Application {application_number} not found in database.")
        
        app_date = datetime.strptime(application_date, "%Y-%m-%d")
        current_date = datetime.now()
        working_days = calculate_working_days(app_date, current_date)
        
        print(f"Visa status found: {status}, Working days: {working_days}")
        
        if status == "Not Found":
            message = f"Your visa application (number {application_number}) was not found in our database. Please check your application number and try again."
        else:
            message = f"Your visa application is {status}. It has been {working_days} working days since your application."
        
        subject = f"Visa Application Status Update - {status}"
        body = message
        email_sent = send_email_notification(email, subject, body)
        
        response_data = {
            "status": status,
            "working_days": working_days,
            "message": message,
            "email_sent": email_sent,
            "email_error": "" if email_sent else "Failed to send email notification. Please check your email address."
        }
        print(f"Sending response: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        print(f"Error in check_status route: {str(e)}")
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
