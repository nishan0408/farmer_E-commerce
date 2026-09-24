# =============================================
# QUICK START GUIDE - Farmer E-Commerce
# =============================================

## Windows Setup

1. **Open PowerShell in the project folder**

2. **Create Virtual Environment**
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```
   pip install -r requirements.txt
   ```

4. **Setup Environment Variables**
   - Copy `.env.example` to `.env`
   - Edit `.env` with your Gmail and Twilio credentials
   
5. **Initialize Database**
   ```
   python init_db.py
   ```

6. **Run Application**
   ```
   python run.py
   ```

7. **Access Application**
   Open browser and go to: http://localhost:5000

## Important Credentials to Setup

### Gmail (for Email Verification)
1. Visit: https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to App Passwords
4. Generate password for Gmail
5. Copy to GMAIL_PASSWORD in .env

### Twilio (for SMS)
1. Sign up at: https://www.twilio.com
2. Get Account SID and Auth Token
3. Get a phone number
4. Add to .env file

## Testing the App

### Register as Farmer
- URL: http://localhost:5000/auth/login-choice
- Click "Register as Farmer"
- Fill in all details
- Check emails for verification link
- Complete phone OTP verification
- Access farmer dashboard

### Register as Buyer
- URL: http://localhost:5000/auth/login-choice
- Click "Register as Buyer"
- Fill in all details
- Check email for verification link
- Complete phone OTP verification
- Access buyer dashboard

## Default Routes

- Home: http://localhost:5000/
- Login Choice: http://localhost:5000/auth/login-choice
- Farmer Login: http://localhost:5000/auth/login/farmer
- Farmer Register: http://localhost:5000/auth/register/farmer
- Buyer Login: http://localhost:5000/auth/login/buyer
- Buyer Register: http://localhost:5000/auth/register/buyer
- Farmer Dashboard: http://localhost:5000/farmer/dashboard
- Buyer Dashboard: http://localhost:5000/buyer/dashboard

## Troubleshooting

If Email/SMS not working:
1. Check if credentials are correct in .env
2. Restart the application (python run.py)
3. Check email spam folder
4. Verify Gmail app password format

If database error:
1. Delete farm_ecommerce.db file
2. Run: python init_db.py

If port 5000 is busy:
1. Edit run.py and change port to 5001
2. Or stop other application using port 5000

## File Structure Created

farmer_NP/
├── app/                    # Flask application
├── templates/              # HTML templates
├── static/                # CSS and JavaScript
├── instance/              # Instance folder (auto-created)
├── config.py             # Configuration
├── run.py                # Run application
├── init_db.py            # Database initialization
├── requirements.txt      # Dependencies
├── README.md             # Full documentation
└── .env                  # Environment variables

## Next Steps After Setup

1. ✅ Test user registration (farmer)
2. ✅ Test email verification
3. ✅ Test phone OTP verification
4. ✅ Test login functionality
5. ✅ Add more features (products, orders, etc.)
6. ✅ Configure payment gateway
7. ✅ Deploy to production

Good luck! 🌾
