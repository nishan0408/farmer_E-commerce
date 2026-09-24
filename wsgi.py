"""
Farmer E-Commerce Application

This module initializes the Flask application and loads all configurations.
"""

from app import create_app
from flask_mail import Mail

# Create Flask app instance
app = create_app()

if __name__ == '__main__':
    # Run development server
    app.run(debug=True)
