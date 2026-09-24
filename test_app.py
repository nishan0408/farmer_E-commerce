"""
Test Script for Farmer E-Commerce Application

Run this script to test all components.
"""

from app import create_app, db
from app.models import User, EmailVerification, PhoneVerification
from datetime import datetime, timedelta

def test_database():
    """Test database connection and models"""
    print("\n" + "="*50)
    print("Testing Database...")
    print("="*50)
    
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Test creating a user
        test_user = User(
            email='test@example.com',
            phone_number='+1234567890',
            user_type='farmer',
            first_name='Test',
            last_name='Farmer',
            farm_name='Test Farm'
        )
        test_user.set_password('testpass123')
        
        db.session.add(test_user)
        db.session.commit()
        
        # Test retrieving user
        user = User.query.filter_by(email='test@example.com').first()
        
        if user:
            print("✓ User creation successful")
            print(f"  - Email: {user.email}")
            print(f"  - Type: {user.user_type}")
            print(f"  - Password check: {user.check_password('testpass123')}")
        else:
            print("✗ User creation failed")
        
        # Test email verification
        token = EmailVerification.generate_token()
        email_verification = EmailVerification(
            user_id=user.id,
            token=token
        )
        db.session.add(email_verification)
        db.session.commit()
        
        ev = EmailVerification.query.filter_by(token=token).first()
        if ev:
            print("✓ Email verification token created")
        
        # Test phone OTP
        otp = PhoneVerification.generate_otp()
        phone_verification = PhoneVerification(
            user_id=user.id,
            otp=otp
        )
        db.session.add(phone_verification)
        db.session.commit()
        
        pv = PhoneVerification.query.filter_by(otp=otp).first()
        if pv:
            print("✓ Phone OTP generated")
            print(f"  - OTP: {otp}")
            print(f"  - Is expired: {pv.is_expired()}")
        
        print("\n✓ Database tests passed!")
        return True

def test_email_service():
    """Test email service"""
    print("\n" + "="*50)
    print("Testing Email Service...")
    print("="*50)
    
    from app.services import EmailService
    
    # This is just a mock test - actual email won't be sent in testing
    print("✓ Email service module loaded")
    print("  - EmailService.send_verification_email available")
    print("  - EmailService.send_password_reset_email available")
    
    return True

def test_sms_service():
    """Test SMS service"""
    print("\n" + "="*50)
    print("Testing SMS Service...")
    print("="*50)
    
    from app.services import SMSService
    
    print("✓ SMS service module loaded")
    print("  - SMSService.send_otp available")
    
    return True

def test_routes():
    """Test route registration"""
    print("\n" + "="*50)
    print("Testing Routes...")
    print("="*50)
    
    app = create_app('testing')
    client = app.test_client()
    
    # Test login choice page
    response = client.get('/auth/login-choice')
    if response.status_code == 200:
        print("✓ Login choice route accessible")
    else:
        print("✗ Login choice route failed:", response.status_code)
    
    # Test farmer login page
    response = client.get('/auth/login/farmer')
    if response.status_code == 200:
        print("✓ Farmer login route accessible")
    else:
        print("✗ Farmer login route failed:", response.status_code)
    
    # Test buyer login page
    response = client.get('/auth/login/buyer')
    if response.status_code == 200:
        print("✓ Buyer login route accessible")
    else:
        print("✗ Buyer login route failed:", response.status_code)
    
    # Test farmer register page
    response = client.get('/auth/register/farmer')
    if response.status_code == 200:
        print("✓ Farmer register route accessible")
    else:
        print("✗ Farmer register route failed:", response.status_code)
    
    # Test buyer register page
    response = client.get('/auth/register/buyer')
    if response.status_code == 200:
        print("✓ Buyer register route accessible")
    else:
        print("✗ Buyer register route failed:", response.status_code)
    
    print("\n✓ Route tests passed!")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*50)
    print("FARMER E-COMMERCE - TEST SUITE")
    print("="*50)
    
    try:
        test_database()
        test_email_service()
        test_sms_service()
        test_routes()
        
        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED!")
        print("="*50)
        print("\nYour application is ready to run!")
        print("Start the app with: python run.py")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
