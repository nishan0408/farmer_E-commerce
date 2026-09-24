from flask_mail import Mail, Message
from flask import render_template_string, current_app
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)

mail = Mail()

class EmailService:
    """Service for sending emails"""
    last_error = None
    
    @staticmethod
    def send_email(recipient, subject, html_body):
        """Send email"""
        try:
            EmailService.last_error = None
            msg = Message(
                subject=subject,
                recipients=[recipient] if isinstance(recipient, str) else recipient,
                html=html_body
            )
            mail.send(msg)
            logger.info(f"Email sent to {recipient}")
            return True
        except Exception as e:
            EmailService.last_error = str(e)
            logger.error(f"Failed to send email: {str(e)}")
            return False

    @staticmethod
    def get_last_error():
        """Return last email error string for troubleshooting"""
        return EmailService.last_error
    
    @staticmethod
    def send_verification_email(email, token, user_type):
        """Send email verification link"""
        verification_link = f"http://localhost:5000/auth/verify-email/{token}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="background-color: #f4f4f4; padding: 20px;">
                    <div style="background-color: white; padding: 20px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #2c3e50; text-align: center;">Verify Your Email</h2>
                        <p>Hello,</p>
                        <p>Thank you for registering as a <strong>{user_type}</strong> on Farmer E-Commerce Platform.</p>
                        <p>Please click the button below to verify your email address:</p>
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{verification_link}" style="background-color: #27ae60; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                                Verify Email
                            </a>
                        </p>
                        <p>Or copy and paste this link in your browser:</p>
                        <p style="background-color: #f9f9f9; padding: 10px; word-break: break-all;">
                            {verification_link}
                        </p>
                        <p style="color: #7f8c8d; font-size: 12px;">This link will expire in 24 hours.</p>
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        <p style="text-align: center; color: #7f8c8d; font-size: 12px;">
                            If you did not create this account, please ignore this email.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return EmailService.send_email(email, "Verify Your Email - Farmer E-Commerce", html_body)

    @staticmethod
    def send_verification_email_with_retry(email, token, user_type, retries=2):
        """Send verification email with retry for transient SMTP issues"""
        attempts = max(1, retries)
        for _ in range(attempts):
            if EmailService.send_verification_email(email, token, user_type):
                return True
        return False
    
    @staticmethod
    def send_password_reset_email(email, token):
        """Send password reset link"""
        reset_link = f"http://localhost:5000/auth/reset-password/{token}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="background-color: #f4f4f4; padding: 20px;">
                    <div style="background-color: white; padding: 20px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #2c3e50; text-align: center;">Reset Your Password</h2>
                        <p>Hello,</p>
                        <p>We received a request to reset your password. Click the button below to create a new password:</p>
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{reset_link}" style="background-color: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                                Reset Password
                            </a>
                        </p>
                        <p>Or copy and paste this link:</p>
                        <p style="background-color: #f9f9f9; padding: 10px; word-break: break-all;">
                            {reset_link}
                        </p>
                        <p style="color: #7f8c8d; font-size: 12px;">This link will expire in 1 hour.</p>
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        <p style="text-align: center; color: #7f8c8d; font-size: 12px;">
                            If you did not request this, please ignore this email and your password will remain unchanged.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return EmailService.send_email(email, "Reset Your Password - Farmer E-Commerce", html_body)

    @staticmethod
    def send_otp_email(email, otp):
        """Send OTP code via email"""
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="background-color: #f4f4f4; padding: 20px;">
                    <div style="background-color: white; padding: 20px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #2c3e50; text-align: center;">Your Verification Code</h2>
                        <p>Hello,</p>
                        <p>Use the following One-Time Password (OTP) to complete your verification:</p>
                        <p style="text-align: center; margin: 30px 0;">
                            <span style="display: inline-block; background-color: #27ae60; color: white; font-size: 28px; letter-spacing: 6px; padding: 10px 20px; border-radius: 6px; font-weight: bold;">
                                {otp}
                            </span>
                        </p>
                        <p style="text-align: center; color: #7f8c8d;">This code is valid for 10 minutes.</p>
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        <p style="text-align: center; color: #7f8c8d; font-size: 12px;">
                            If you did not request this code, please ignore this email.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

        return EmailService.send_email(email, "Your OTP Code - Farmer E-Commerce", html_body)

    @staticmethod
    def send_otp_email_with_retry(email, otp, retries=2):
        """Send OTP email with simple retry for transient SMTP issues"""
        attempts = max(1, retries)
        for _ in range(attempts):
            if EmailService.send_otp_email(email, otp):
                return True
        return False


class SMSService:
    """Service for sending SMS via Twilio"""
    last_error = None

    @staticmethod
    def _is_placeholder_value(value):
        """Check whether a config value looks like a default placeholder."""
        if not value:
            return True

        value = str(value).strip()
        placeholders = {
            'your-account-sid',
            'your-auth-token',
            'test123',
            '+1234567890',
        }

        lowered = value.lower()
        return (
            value in placeholders
            or lowered.startswith('your-')
            or 'xxxx' in lowered
        )
    
    @staticmethod
    def get_client():
        """Get Twilio client"""
        try:
            account_sid = current_app.config.get('TWILIO_ACCOUNT_SID', '').strip()
            auth_token = current_app.config.get('TWILIO_AUTH_TOKEN', '').strip()

            if SMSService._is_placeholder_value(account_sid) or not account_sid.startswith('AC'):
                SMSService.last_error = 'Invalid Twilio Account SID in .env (must start with AC...)'
                return None

            if SMSService._is_placeholder_value(auth_token):
                SMSService.last_error = 'Invalid Twilio Auth Token in .env'
                return None

            client = Client(
                account_sid,
                auth_token
            )
            return client
        except Exception as e:
            SMSService.last_error = str(e)
            logger.error(f"Failed to initialize Twilio client: {str(e)}")
            return None
    
    @staticmethod
    def send_otp(phone_number, otp):
        """Send OTP via SMS"""
        try:
            SMSService.last_error = None
            client = SMSService.get_client()
            if not client:
                if not SMSService.last_error:
                    SMSService.last_error = 'Failed to initialize Twilio client'
                return False

            twilio_from = current_app.config.get('TWILIO_PHONE_NUMBER', '').strip()
            if SMSService._is_placeholder_value(twilio_from) or not twilio_from.startswith('+'):
                SMSService.last_error = 'Invalid Twilio phone number in .env (use E.164 format, e.g., +15551234567)'
                return False

            phone_number = str(phone_number).strip()
            if not phone_number.startswith('+'):
                SMSService.last_error = 'Recipient phone must include country code in E.164 format (e.g., +97798...)'
                return False
            
            message_body = f"Your Farmer E-Commerce verification code is: {otp}. Valid for 10 minutes."
            
            message = client.messages.create(
                body=message_body,
                from_=twilio_from,
                to=phone_number
            )
            
            logger.info(f"SMS sent to {phone_number}")
            return True
        except Exception as e:
            SMSService.last_error = str(e)
            logger.error(f"Failed to send SMS: {str(e)}")
            return False

    @staticmethod
    def get_last_error():
        """Return last SMS error string for troubleshooting"""
        return SMSService.last_error


class OTPDeliveryService:
    """Service that delivers OTP through both email and SMS"""

    @staticmethod
    def send_otp_via_email_and_sms(email, phone_number, otp, retries=2):
        """Send OTP on both channels with retries and return per-channel status"""
        attempts = max(1, retries)
        email_sent = False
        sms_sent = False

        for _ in range(attempts):
            if not email_sent:
                email_sent = EmailService.send_otp_email(email, otp)
            if not sms_sent:
                sms_sent = SMSService.send_otp(phone_number, otp)
            if email_sent and sms_sent:
                break

        result = {
            'email_sent': email_sent,
            'sms_sent': sms_sent,
            'any_sent': email_sent or sms_sent,
            'both_sent': email_sent and sms_sent,
            'email_error': None if email_sent else EmailService.get_last_error(),
            'sms_error': None if sms_sent else SMSService.get_last_error(),
        }
        return result
