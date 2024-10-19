import os
import sys
import logging
from flask import Flask

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def hello():
    logger.info("Hello route accessed")
    return "Hello, World!"

if __name__ == '__main__':
    logger.info("Starting application")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
