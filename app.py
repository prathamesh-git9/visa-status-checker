import os
import sys
import logging
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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

@app.route('/')
def index():
    try:
        logger.info("Index route accessed")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}", exc_info=True)
        return f"An error occurred: {str(e)}", 500

@app.route("/check_status", methods=["POST"])
def check_status():
    try:
        irl_number = request.form["irl_number"]
        application_date = request.form["application_date"]

        if irl_number in visa_database:
            visa_info = visa_database[irl_number]
            status = visa_info["status"]
            app_date = datetime.strptime(visa_info["application_date"], "%Y-%m-%d")
            current_date = datetime.now()
            working_days = calculate_working_days(app_date, current_date)

            return jsonify({
                "status": status,
                "working_days": working_days,
                "message": f"Your visa application is {status}. It has been {working_days} working days since your application."
            })
        else:
            return jsonify({
                "status": "Not Found",
                "message": "No visa application found with the provided IRL number."
            }), 404
    except Exception as e:
        logger.error(f"Error in check_status route: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {str(error)}", exc_info=True)
    return f"Internal Server Error: {str(error)}", 500

if __name__ == '__main__':
    logger.info("Starting application")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
