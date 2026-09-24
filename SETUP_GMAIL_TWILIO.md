 # SETUP GUIDE FOR GMAIL AND TWILIO

## Step 1: Gmail Setup (Email Verification)

### Generate Gmail App Password

1. **Visit Google Account Settings**
   - Go to: https://myaccount.google.com/

2. **Enable 2-Step Verification (if not already enabled)**
   - Click "Security" in the left sidebar
   - Find "2-Step Verification" 
   - Follow the prompts to set it up

3. **Generate App Password**
   - Go back to Security settings
   - Find "App Passwords" (appears after 2-Step is enabled)
   - Select "Mail" and "Windows Computer" (or your setup)
   - Click "Generate"
   - Copy the 16-character password

4. **Add to .env File**
   ```
   GMAIL_EMAIL=your-email@gmail.com
   GMAIL_PASSWORD=xxxx xxxx xxxx xxxx
   ```

### Example Configuration:
```
GMAIL_EMAIL=farmer.commerce@gmail.com
GMAIL_PASSWORD=abcd efgh ijkl mnop
```

## Step 2: Twilio Setup (SMS Verification)

### Create Twilio Account

1. **Sign Up**
   - Go to: https://www.twilio.com/try-twilio
   - Create an account with your email

2. **Verify Phone Number**
   - During signup, verify your own phone number with SMS code

3. **Get Credentials from Dashboard**
   - Go to: https://console.twilio.com/
   - Find "Account SID" - copy it
   - Find "Auth Token" - click eye icon and copy it
   - Find "Phone Numbers" section - get your assigned number

4. **Add to .env File**
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_PHONE_NUMBER=+1234567890
   ```

### Buy a Twilio Phone Number (if not provided)

1. In Twilio Console, go to "Phone Numbers"
2. Click "Get Started"
3. Click "Get your first Twilio phone number"
4. Select a number
5. Copy the number to TWILIO_PHONE_NUMBER in .env

### Example Configuration:
```
TWILIO_ACCOUNT_SID=AC1234567890abcdefg
TWILIO_AUTH_TOKEN=auth_token_here_1234567890abcdefg
TWILIO_PHONE_NUMBER=+13334445555
```

## Complete .env File Template

```
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-in-production
DATABASE_URL=sqlite:///farm_ecommerce.db

# Mail Configuration (Gmail)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
GMAIL_EMAIL=your-email@gmail.com
GMAIL_PASSWORD=xxxx xxxx xxxx xxxx

# Twilio Configuration (SMS)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890

# Optional Settings
PORT=5000
```

## Troubleshooting Email Issues

### Error: "Authentication failed"
- ✓ Double-check Gmail app password (16 characters)
- ✓ Make sure 2-Step Verification is enabled
- ✓ Don't use your main Gmail password, use generated app password

### Error: "Connection refused"
- ✓ Check internet connection
- ✓ Make sure SMTP port 587 is not blocked
- ✓ The email might be in Spam folder - check there

### Email not arriving
- ✓ Check spam/junk folder
- ✓ Allow Gmail to "Less secure app access" (optional check in Google Account)
- ✓ Make sure GMAIL_EMAIL matches the account being used

## Troubleshooting SMS Issues

### Error: "Invalid phone number"
- ✓ Phone number must include country code (+1 for US)
- ✓ Format example: +1 234 567 8900

### Error: "Authentication failed"
- ✓ Verify TWILIO_ACCOUNT_SID is correct
- ✓ Verify TWILIO_AUTH_TOKEN is correct
- ✓ Copy from console without extra spaces

### SMS not arriving
- ✓ Check phone network connection
- ✓ Make sure phone number format is correct with country code
- ✓ Twilio account must have sufficient credits/balance
- ✓ Number might be on blocklist (check Twilio dashboard)

## Verify Configuration Works

Test your email setup:
```python
from flask_mail import Message
from app import create_app
from app.services import mail

app = create_app()
with app.app_context():
    msg = Message(
        'Test Email',
        recipients=['your-email@example.com'],
        body='This is a test email'
    )
    mail.send(msg)
    print("Email sent successfully!")
```

Test your SMS setup:
```python
from app import create_app
from app.services import SMSService

app = create_app()
with app.app_context():
    result = SMSService.send_otp('+1234567890', '123456')
    print(f"SMS sent: {result}")
```

## Security Notes

⚠️ **Important Security Tips:**

1. **Never commit .env to version control**
   - .env file should be in .gitignore
   - Keep credentials private

2. **Rotate credentials regularly**
   - Change passwords periodically
   - Regenerate app passwords after deployment

3. **Use environment variables in production**
   - Set env vars via hosting provider
   - Example platforms: Heroku, AWS, Azure

4. **Keep secrets in vault**
   - For enterprise: Use HashiCorp Vault
   - Store credentials securely

5. **Monitor usage**
   - Check Gmail security activity
   - Monitor Twilio usage and costs

## Production Considerations

For production deployment:

1. **Use PostgreSQL instead of SQLite**
   ```
   DATABASE_URL=postgresql://user:password@localhost/farmer_db
   ```

2. **Use SendGrid or AWS SES for email**
   - More reliable for production
   - Better deliverability

3. **Use dedicated Twilio number**
   - More reliable for SMS
   - Professional appearance

4. **Enable HTTPS**
   - Get SSL certificate
   - Use secure cookies

5. **Set proper session timeout**
   - Reduce SESSION_COOKIE_LIFETIME for security
   - Require re-authentication for sensitive operations

## Support Resources

- **Gmail Help:** https://support.google.com/mail
- **Twilio Documentation:** https://www.twilio.com/docs
- **Flask-Mail Docs:** https://packages.python.org/Flask-Mail/
- **Twilio Python SDK:** https://github.com/twilio/twilio-python

---

Once configured, your application will be ready to send emails and SMS! 🎉
