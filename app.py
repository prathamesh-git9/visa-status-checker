from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_caching import Cache
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Mock database (replace with actual database in production)
visa_database = {
    "IRL123456": {"status": "Approved", "application_date": "2023-03-01"},
    "IRL789012": {"status": "Rejected", "application_date": "2023-03-15"},
    "IRL345678": {"status": "Pending", "application_date": "2023-04-01"},
}

def calculate_working_days(start_date, end_date):
    working_days = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:  # Monday = 0, Friday = 4
            working_days += 1
        current_date += timedelta(days=1)
    return working_days

def send_email(recipient, subject, body):
    sender_email = os.getenv('EMAIL_USERNAME')
    sender_password = os.getenv('EMAIL_PASSWORD')

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(message)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/check_status", methods=["POST"])
@cache.memoize(timeout=300)  # Cache results for 5 minutes
def check_status():
    irl_number = request.form["irl_number"]
    application_date = request.form["application_date"]

    if irl_number in visa_database:
        visa_info = visa_database[irl_number]
        status = visa_info["status"]
        app_date = datetime.strptime(visa_info["application_date"], "%Y-%m-%d")
        current_date = datetime.now()
        working_days = calculate_working_days(app_date, current_date)

        # Send email based on status
        recipient_email = "applicant@example.com"  # Replace with actual applicant email
        if status == "Approved":
            subject = "Congratulations! Your Visa Has Been Approved"
            body = "We are pleased to inform you that your visa application has been approved."
        elif status == "Rejected":
            subject = "Update on Your Visa Application"
            body = "We regret to inform you that your visa application has been rejected. Please contact our office for more information and next steps."
        else:
            subject = "Your Visa Application Status"
            body = f"Your visa application is still pending. It has been {working_days} working days since your application date."

        send_email(recipient_email, subject, body)

        return jsonify({
            "status": status,
            "working_days": working_days,
            "message": f"An email has been sent to {recipient_email} with more information."
        })
    else:
        return jsonify({
            "status": "Not Found",
            "message": "No visa application found with the provided IRL number."
        })

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)
