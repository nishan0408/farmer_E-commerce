import os
from app import create_app
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Create app
app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    debug_mode = app.config.get('DEBUG', False)
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=debug_mode
    )
