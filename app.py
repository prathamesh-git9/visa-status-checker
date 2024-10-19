from flask import Flask, render_template, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_caching import Cache
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import logging

load_dotenv()

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///visa_applications.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class VisaApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    irl_number = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    application_date = db.Column(db.Date, nullable=False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.send_message(message)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/check_status", methods=["POST"])
@cache.memoize(timeout=300)  # Cache results for 5 minutes
def check_status():
    irl_number = request.form["irl_number"]
    application_date = request.form["application_date"]

    visa_application = VisaApplication.query.filter_by(irl_number=irl_number).first()

    if visa_application:
        status = visa_application.status
        app_date = visa_application.application_date
        current_date = datetime.now().date()
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

        email_sent = send_email(recipient_email, subject, body)

        return jsonify({
            "status": status,
            "working_days": working_days,
            "message": f"An email has been sent to {recipient_email} with more information." if email_sent else "There was an issue sending the email, but your status has been updated."
        })
    else:
        return jsonify({
            "status": "Not Found",
            "message": "No visa application found with the provided IRL number."
        }), 404

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/admin")
@login_required
def admin():
    applications = VisaApplication.query.all()
    return render_template("admin.html", applications=applications)

@app.route("/admin/add", methods=["POST"])
@login_required
def add_application():
    irl_number = request.form["irl_number"]
    status = request.form["status"]
    application_date = datetime.strptime(request.form["application_date"], "%Y-%m-%d").date()

    new_application = VisaApplication(irl_number=irl_number, status=status, application_date=application_date)
    db.session.add(new_application)
    db.session.commit()

    return jsonify({"message": "Application added successfully"}), 201

@app.route("/admin/update", methods=["POST"])
@login_required
def update_application():
    irl_number = request.form["irl_number"]
    new_status = request.form["status"]

    application = VisaApplication.query.filter_by(irl_number=irl_number).first()
    if application:
        application.status = new_status
        db.session.commit()
        return jsonify({"message": "Application updated successfully"}), 200
    else:
        return jsonify({"message": "Application not found"}), 404

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin"))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/create_admin", methods=["GET", "POST"])
def create_admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "Admin user already exists"
        new_admin = User(username=username)
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()
        return "Admin user created successfully"
    return render_template("create_admin.html")

@app.route('/')
def hello():
    return "Hello, World!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
