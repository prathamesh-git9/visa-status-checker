import os
import sys
import logging
from flask import Flask, render_template

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    try:
        logger.info("Index route accessed")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return "An error occurred", 500

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {str(error)}")
    return "Internal Server Error", 500

if __name__ == '__main__':
    logger.info("Starting application")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
