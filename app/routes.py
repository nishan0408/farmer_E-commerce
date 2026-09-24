from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, EmailVerification, PhoneVerification, PasswordReset, Product, Order, Wishlist
from app.services import OTPDeliveryService
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
import re
import logging
import os
import uuid

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
main_bp = Blueprint('main', __name__)


def parse_roles(user_type_value):
    """Parse stored user_type string into a set of roles."""
    if not user_type_value:
        return set()
    return {role.strip() for role in str(user_type_value).split(',') if role.strip()}


def serialize_roles(roles):
    """Serialize role set for storage."""
    ordered = [role for role in ['farmer', 'buyer', 'shop_owner'] if role in roles]
    return ','.join(ordered)


def user_has_role(user, role):
    """Check whether user has a specific role."""
    return role in parse_roles(user.user_type)


def ensure_user_role(user, role):
    """Add role to user if missing."""
    roles = parse_roles(user.user_type)
    roles.add(role)
    user.user_type = serialize_roles(roles)

# Helper function to validate email
def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Helper function to validate phone
def is_valid_phone(phone):
    """Validate phone number (basic validation)"""
    phone = re.sub(r'[^0-9+]', '', phone)
    return len(phone) >= 10


def send_otp_for_user(user, otp, retries=2):
    """Send OTP via both email and SMS and return delivery status."""
    return OTPDeliveryService.send_otp_via_email_and_sms(
        user.email,
        user.phone_number,
        otp,
        retries=retries,
    )


def otp_delivery_failure_reason(delivery_result):
    """Build a short channel-specific delivery failure description."""
    errors = []
    if not delivery_result.get('email_sent'):
        errors.append(f"email: {delivery_result.get('email_error') or 'unknown error'}")
    if not delivery_result.get('sms_sent'):
        errors.append(f"sms: {delivery_result.get('sms_error') or 'unknown error'}")
    return '; '.join(errors) if errors else 'unknown delivery error'


def sms_unavailable_message(delivery_result):
    """Return SMS failure text suitable for end users."""
    if current_app.config.get('DEBUG'):
        return f"SMS delivery failed ({delivery_result.get('sms_error') or 'unknown SMS error'})."
    return 'SMS delivery is temporarily unavailable.'


def allowed_image_file(filename):
    """Allow common image extensions for product images."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in {'jpg', 'jpeg', 'png', 'webp'}


# Exchange reference: value means 1 INR equals this many target currency units.
SUPPORTED_CURRENCY_RATES = {
    'INR': 1.0,
    'USD': 0.012,
    'EUR': 0.011,
    'GBP': 0.0094,
    'NPR': 1.60,
    'AUD': 0.018,
    'CAD': 0.016,
    'JPY': 1.82,
    'AED': 0.044,
    'SGD': 0.016,
}


def validate_and_create_product_for_user(user):
    """Validate product form input and persist a product for the given user."""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price_raw = request.form.get('price', '').strip()
    currency_code = request.form.get('currency', 'INR').strip().upper()
    quality = request.form.get('quality', '').strip().lower()
    image_file = request.files.get('image')

    errors = []
    if not name:
        errors.append('Product name is required.')
    if not description:
        errors.append('Product description is required.')
    if currency_code not in SUPPORTED_CURRENCY_RATES:
        errors.append('Please choose a valid currency.')
    if quality not in {'average', 'good', 'premium'}:
        errors.append('Please choose a valid product quality.')

    try:
        price = float(price_raw)
        if price <= 0:
            errors.append('Price must be greater than 0.')
    except (TypeError, ValueError):
        price = None
        errors.append('Please enter a valid price.')

    if not image_file or not image_file.filename:
        errors.append('Product image is required.')
    elif not allowed_image_file(image_file.filename):
        errors.append('Only JPG, JPEG, PNG, and WEBP images are allowed.')

    if errors:
        return {'success': False, 'errors': errors}

    inr_price = convert_currency(price, currency_code, 'INR')
    if inr_price is None:
        return {'success': False, 'errors': ['Unable to convert selected currency right now.']}

    original_name = secure_filename(image_file.filename)
    extension = original_name.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{extension}"

    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'products')
    os.makedirs(upload_dir, exist_ok=True)
    image_path = os.path.join(upload_dir, unique_name)
    image_file.save(image_path)

    product = Product(
        farmer_id=user.id,
        name=name,
        description=description,
        price=round(inr_price, 2),
        quality=quality,
        image_filename=unique_name,
    )
    db.session.add(product)
    db.session.commit()

    return {'success': True, 'inr_price': inr_price}


def convert_currency(amount, from_currency, to_currency):
    """Convert amount between supported currencies via INR base."""
    from_rate = SUPPORTED_CURRENCY_RATES.get(from_currency)
    to_rate = SUPPORTED_CURRENCY_RATES.get(to_currency)
    if from_rate is None or to_rate is None:
        return None

    amount_in_inr = float(amount) / from_rate
    return amount_in_inr * to_rate

# ==================== ROUTES ====================

@main_bp.route('/')
def index():
    """Home page"""
    if current_user.is_authenticated:
        if user_has_role(current_user, 'farmer'):
            return redirect(url_for('main.farmer_dashboard'))
        elif user_has_role(current_user, 'buyer'):
            return redirect(url_for('main.buyer_dashboard'))
        elif user_has_role(current_user, 'shop_owner'):
            return redirect(url_for('main.shop_owner_dashboard'))
    return redirect(url_for('auth.login_choice'))


@auth_bp.route('/login-choice', methods=['GET', 'POST'])
def login_choice():
    """Choose between farmer and buyer login"""
    role = request.args.get('role', 'farmer')
    if role not in ['farmer', 'buyer', 'shop_owner']:
        role = 'farmer'
    return render_template('login_choice.html', active_role=role)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register_account():
    """Unified registration for one account across farmer, buyer, and shop owner dashboards."""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        password_confirm = data.get('password_confirm', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        farm_name = data.get('farm_name', '').strip()

        errors = []
        if not email or not is_valid_email(email):
            errors.append('Invalid email address')
        if not phone or not is_valid_phone(phone):
            errors.append('Invalid phone number')
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters')
        if password != password_confirm:
            errors.append('Passwords do not match')
        if not first_name:
            errors.append('First name is required')

        existing_email_user = User.query.filter_by(email=email).first()
        existing_phone_user = User.query.filter_by(phone_number=phone).first()
        target_user = existing_email_user or existing_phone_user

        if existing_email_user and existing_phone_user and existing_email_user.id != existing_phone_user.id:
            errors.append('Email and phone belong to different accounts. Please use matching credentials.')
        if existing_email_user and existing_email_user.phone_number != phone:
            errors.append('This email is already registered with a different phone number.')
        if existing_phone_user and existing_phone_user.email != email:
            errors.append('This phone number is already registered with a different email.')

        if target_user and target_user.email_verified and target_user.phone_verified:
            errors.append('This account is already verified. Please login directly.')

        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html', email=email, phone=phone, first_name=first_name,
                                 last_name=last_name, farm_name=farm_name)

        try:
            if target_user:
                user = target_user
                user.phone_number = phone
                user.first_name = first_name
                user.last_name = last_name
                if farm_name:
                    user.farm_name = farm_name
            else:
                user = User(
                    email=email,
                    phone_number=phone,
                    first_name=first_name,
                    last_name=last_name,
                    farm_name=farm_name or None,
                )
                db.session.add(user)

            # Unified account: enable all dashboards after one verification.
            user.user_type = 'farmer,buyer,shop_owner'
            user.set_password(password)
            user.email_verified = False
            user.phone_verified = False
            db.session.flush()

            EmailVerification.query.filter_by(user_id=user.id, verified=False).delete()
            PhoneVerification.query.filter_by(user_id=user.id, verified=False).delete()

            otp = PhoneVerification.generate_otp()
            phone_verification = PhoneVerification(user_id=user.id, otp=otp)
            db.session.add(phone_verification)
            db.session.commit()

            delivery_result = send_otp_for_user(user, otp, retries=2)
            if delivery_result['any_sent']:
                if request.is_json:
                    return jsonify({'success': True, 'message': 'OTP sent. Verify once to activate all dashboards.'}), 201
                if delivery_result['both_sent']:
                    flash('OTP sent to both your email and phone. Verify once to use farmer, buyer, and shop owner dashboards.', 'success')
                elif delivery_result['email_sent']:
                    flash(f"OTP sent to your email. {sms_unavailable_message(delivery_result)}", 'warning')
                else:
                    flash('OTP sent to your phone. Email failed this time.', 'warning')
                return redirect(url_for('auth.verify_phone_otp', user_id=user.id))

            detailed_error = otp_delivery_failure_reason(delivery_result)
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Account created, but OTP delivery failed. Please login to resend OTP.',
                    'warning': f'Failed to send OTP: {detailed_error}'
                }), 202

            if current_app.config.get('DEBUG'):
                flash(f'OTP delivery failed on both channels. Dev fallback OTP: {otp}', 'warning')
            else:
                flash('Account created, but OTP could not be delivered right now. Please login to resend OTP.', 'warning')
            return redirect(url_for('auth.verify_phone_otp', user_id=user.id))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Unified registration error: {str(e)}")
            error_msg = 'Registration failed. Please try again.'
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 500
            flash(error_msg, 'danger')
            return render_template('register.html', email=email, phone=phone, first_name=first_name,
                                 last_name=last_name, farm_name=farm_name)

    return render_template('register.html')


@auth_bp.route('/register/<user_type>', methods=['GET', 'POST'])
def register(user_type):
    """Register as farmer, buyer, or shop owner"""
    if user_type not in ['farmer', 'buyer', 'shop_owner']:
        flash('Invalid user type', 'danger')
        return redirect(url_for('auth.login_choice'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        password = data.get('password', '')
        password_confirm = data.get('password_confirm', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        farm_name = data.get('farm_name', '').strip() if user_type == 'farmer' else None
        shop_name = data.get('shop_name', '').strip() if user_type == 'shop_owner' else None
        shop_category = data.get('shop_category', '').strip() if user_type == 'shop_owner' else None
        shop_license_number = data.get('shop_license_number', '').strip() if user_type == 'shop_owner' else None
        shop_registration_number = data.get('shop_registration_number', '').strip() if user_type == 'shop_owner' else None
        shop_description = data.get('shop_description', '').strip() if user_type == 'shop_owner' else None
        
        # Validation
        errors = []
        
        if not email or not is_valid_email(email):
            errors.append('Invalid email address')
        
        if not phone or not is_valid_phone(phone):
            errors.append('Invalid phone number')
        
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters')
        
        if password != password_confirm:
            errors.append('Passwords do not match')
        
        if not first_name:
            errors.append('First name is required')
        
        if user_type == 'farmer' and not farm_name:
            errors.append('Farm name is required')
        
        if user_type == 'shop_owner':
            if not shop_name:
                errors.append('Shop name is required')
            if not shop_category:
                errors.append('Shop category is required')
            if not shop_license_number:
                errors.append('Shop license number is required')
            if not shop_registration_number:
                errors.append('Shop registration number is required')
        
        # Check if email or phone already exists
        existing_email_user = User.query.filter_by(email=email).first()
        existing_phone_user = User.query.filter_by(phone_number=phone).first()

        target_user = existing_email_user or existing_phone_user

        # If both exist, they must point to same account
        if existing_email_user and existing_phone_user and existing_email_user.id != existing_phone_user.id:
            errors.append('Email and phone belong to different accounts. Please use matching credentials.')

        # Email is already used with a different phone
        if existing_email_user and existing_email_user.phone_number != phone:
            errors.append('This email is already registered with a different phone number.')

        # Phone is already used with a different email
        if existing_phone_user and existing_phone_user.email != email:
            errors.append('This phone number is already registered with a different email.')
        
        if user_type == 'shop_owner':
            license_owner = User.query.filter_by(shop_license_number=shop_license_number).first()
            if license_owner and (not target_user or license_owner.id != target_user.id):
                errors.append('Shop license number already registered')
            registration_owner = User.query.filter_by(shop_registration_number=shop_registration_number).first()
            if registration_owner and (not target_user or registration_owner.id != target_user.id):
                errors.append('Shop registration number already registered')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'danger')
            return render_template(f'{user_type}/register.html', user_type=user_type, 
                                 email=email, phone=phone, first_name=first_name, last_name=last_name)
        
        try:
            # Create a new user or reuse existing account to add another role
            if target_user:
                user = target_user

                # Existing verified account must keep the same password when adding a new role
                if user.password_hash and not user.check_password(password):
                    msg = 'This account already exists. Please use your existing password to add another role.'
                    if request.is_json:
                        return jsonify({'success': False, 'errors': [msg]}), 400
                    flash(msg, 'danger')
                    return render_template(f'{user_type}/register.html', user_type=user_type,
                                         email=email, phone=phone, first_name=first_name, last_name=last_name)

                user.phone_number = phone
                user.first_name = first_name
                user.last_name = last_name

                if user_type == 'farmer' and farm_name:
                    user.farm_name = farm_name

                if user_type == 'shop_owner':
                    user.shop_name = shop_name
                    user.shop_category = shop_category
                    user.shop_license_number = shop_license_number
                    user.shop_registration_number = shop_registration_number
                    user.shop_description = shop_description
            else:
                user = User(
                    email=email,
                    phone_number=phone,
                    user_type=user_type,
                    first_name=first_name,
                    last_name=last_name,
                    farm_name=farm_name,
                    shop_name=shop_name,
                    shop_category=shop_category,
                    shop_license_number=shop_license_number,
                    shop_registration_number=shop_registration_number,
                    shop_description=shop_description
                )
                db.session.add(user)

            # Ensure this account contains the selected role as well
            ensure_user_role(user, user_type)

            if not user.password_hash:
                user.set_password(password)

            # Keep verification state for previously verified users
            if not (user.email_verified and user.phone_verified):
                user.set_password(password)
                user.email_verified = False
                user.phone_verified = False
            db.session.flush()  # Ensure user ID exists

            # Replace any previous pending tokens/codes for this user
            EmailVerification.query.filter_by(user_id=user.id, verified=False).delete()
            PhoneVerification.query.filter_by(user_id=user.id, verified=False).delete()

            # If account is already fully verified, role has been added and no OTP resend is required
            if user.email_verified and user.phone_verified:
                db.session.commit()
                success_msg = f'{user_type.replace("_", " ").title()} role added successfully. You can now login with the same email and phone.'
                if request.is_json:
                    return jsonify({'success': True, 'message': success_msg}), 200
                flash(success_msg, 'success')
                return redirect(url_for('auth.login', user_type=user_type))

            # OTP-only verification flow: send OTP immediately after registration
            otp = PhoneVerification.generate_otp()
            phone_verification = PhoneVerification(
                user_id=user.id,
                otp=otp
            )
            db.session.add(phone_verification)
            db.session.commit()
            
            # Send OTP on both channels after saving account so user can retry safely
            delivery_result = send_otp_for_user(user, otp, retries=2)
            if delivery_result['any_sent']:
                if request.is_json:
                    return jsonify({'success': True, 'message': 'OTP sent. Please verify your account.'}), 201
                if delivery_result['both_sent']:
                    flash('OTP sent to both your email and phone number. Please enter it to complete registration.', 'success')
                elif delivery_result['email_sent']:
                    flash(f"OTP sent to your email. {sms_unavailable_message(delivery_result)}", 'warning')
                else:
                    flash('OTP sent to your phone number. Email delivery failed this time.', 'warning')
                return redirect(url_for('auth.verify_phone_otp', user_id=user.id))
            else:
                detailed_error = otp_delivery_failure_reason(delivery_result)
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': 'Account created. OTP delivery failed on email and SMS. Please use login to resend OTP.',
                        'warning': f'Failed to send OTP: {detailed_error}'
                    }), 202

                if current_app.config.get('DEBUG'):
                    flash(f'OTP delivery failed on both channels. Account is created. Reason: {detailed_error}', 'warning')
                    flash(f'Dev fallback OTP: {otp}', 'info')
                else:
                    flash('Account created, but OTP could not be delivered right now. Please login to resend OTP.', 'warning')
                return redirect(url_for('auth.verify_phone_otp', user_id=user.id))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            error_msg = 'Registration failed. Please try again.'
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 500
            flash(error_msg, 'danger')
            return render_template(f'{user_type}/register.html', user_type=user_type)
    
    return render_template(f'{user_type}/register.html', user_type=user_type)


@auth_bp.route('/verify-email', methods=['GET'])
def verify_email_page():
    """Email verification page"""
    return render_template('verify_email.html')


@auth_bp.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """Verify email with token"""
    email_verification = EmailVerification.query.filter_by(token=token, verified=False).first()
    
    if not email_verification:
        flash('Invalid or expired verification link', 'danger')
        return redirect(url_for('auth.login_choice'))
    
    if email_verification.expires_at < datetime.utcnow():
        flash('Verification link has expired', 'danger')
        return redirect(url_for('auth.login_choice'))
    
    try:
        user = User.query.get(email_verification.user_id)
        user.email_verified = True
        email_verification.verified = True

        # Keep only one active OTP to avoid matching an older code.
        PhoneVerification.query.filter_by(user_id=user.id, verified=False).delete()

        # Generate phone OTP immediately after email verification
        otp = PhoneVerification.generate_otp()
        phone_verification = PhoneVerification(
            user_id=user.id,
            otp=otp
        )
        db.session.add(phone_verification)
        db.session.commit()

        # Send OTP via both email and SMS
        delivery_result = send_otp_for_user(user, otp, retries=2)
        if delivery_result['any_sent']:
            if delivery_result['both_sent']:
                flash('Email verified! An OTP has been sent to your email and phone number.', 'success')
            elif delivery_result['email_sent']:
                flash(f"Email verified! OTP sent to your email. {sms_unavailable_message(delivery_result)}", 'warning')
            else:
                flash('Email verified! OTP sent to your phone. Email delivery failed this time.', 'warning')
            return redirect(url_for('auth.verify_phone_otp', user_id=user.id))
        else:
            detailed_error = otp_delivery_failure_reason(delivery_result)
            if current_app.config.get('DEBUG'):
                flash(f'OTP delivery failed on both channels. Dev fallback OTP: {otp}', 'warning')
                return redirect(url_for('auth.verify_phone_otp', user_id=user.id))
            flash('Email verified, but OTP could not be delivered right now. Please try resend OTP.', 'warning')
            return redirect(url_for('auth.phone_verification_page', email=user.email))
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Email verification error: {str(e)}")
        flash('Email verification failed', 'danger')
        return redirect(url_for('auth.login_choice'))


@auth_bp.route('/verify-phone', methods=['GET', 'POST'])
def phone_verification_page():
    """Phone verification page"""
    email = request.args.get('email')
    
    if not email:
        flash('Invalid request', 'danger')
        return redirect(url_for('auth.login_choice'))
    
    user = User.query.filter_by(email=email).first()
    if not user or not user.email_verified:
        flash('Please verify your email first', 'danger')
        return redirect(url_for('auth.login_choice'))
    
    if request.method == 'POST':
        # Generate and send OTP
        try:
            # Keep only one active OTP to avoid matching an older code.
            PhoneVerification.query.filter_by(user_id=user.id, verified=False).delete()

            otp = PhoneVerification.generate_otp()
            phone_verification = PhoneVerification(
                user_id=user.id,
                otp=otp
            )
            db.session.add(phone_verification)
            db.session.commit()
            
            # Send OTP via both email and SMS
            delivery_result = send_otp_for_user(user, otp, retries=2)
            if delivery_result['any_sent']:
                if delivery_result['both_sent']:
                    flash('OTP sent to your registered email and phone number.', 'success')
                elif delivery_result['email_sent']:
                    flash(f"OTP sent to your email. {sms_unavailable_message(delivery_result)}", 'warning')
                else:
                    flash('OTP sent to your phone. Email delivery failed this time.', 'warning')
                return redirect(url_for('auth.verify_phone_otp', user_id=user.id))
            else:
                detailed_error = otp_delivery_failure_reason(delivery_result)
                if current_app.config.get('DEBUG'):
                    flash(f'Failed to send OTP on both channels. Dev fallback OTP: {otp}', 'warning')
                    return redirect(url_for('auth.verify_phone_otp', user_id=user.id))
                flash('Failed to send OTP right now. Please try again in a moment.', 'danger')
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"OTP generation error: {str(e)}")
            flash('Error sending OTP', 'danger')
    
    return render_template('verify_phone.html', email=email)


@auth_bp.route('/verify-phone-otp/<int:user_id>', methods=['GET', 'POST'])
def verify_phone_otp(user_id):
    """Verify phone OTP"""
    user = User.query.get(user_id)
    if not user:
        flash('Invalid request', 'danger')
        return redirect(url_for('auth.login_choice'))
    
    if request.method == 'POST':
        # Normalize copied/pasted OTP values (e.g., spaces, hyphens) to digits only.
        otp = re.sub(r'\D', '', request.form.get('otp', ''))

        if len(otp) != 6:
            flash('Please enter a valid 6-digit OTP.', 'danger')
            return render_template('verify_phone_otp.html', user_id=user_id, user_email=user.email)
        
        phone_verification = PhoneVerification.query.filter_by(
            user_id=user_id,
            verified=False
        ).order_by(PhoneVerification.created_at.desc(), PhoneVerification.id.desc()).first()
        
        if not phone_verification:
            flash('OTP verification not found. Please request a new OTP.', 'danger')
            return redirect(url_for('auth.phone_verification_page', email=user.email))
        
        if phone_verification.is_expired():
            flash('OTP has expired. Please request a new one.', 'danger')
            return redirect(url_for('auth.phone_verification_page', email=user.email))
        
        if not phone_verification.is_valid_attempt():
            flash('Too many attempts. Please request a new OTP.', 'danger')
            return redirect(url_for('auth.phone_verification_page', email=user.email))
        
        if otp != phone_verification.otp:
            phone_verification.attempts += 1
            db.session.commit()
            flash('Invalid OTP. Please try again.', 'danger')
            return render_template('verify_phone_otp.html', user_id=user_id, user_email=user.email)
        
        try:
            # OTP is used as the final account verification step
            user.email_verified = True
            user.phone_verified = True
            phone_verification.verified = True
            db.session.commit()
            
            # Auto-login user after successful verification
            login_user(user, remember=True)
            flash('Account registered successfully! You are now logged in.', 'success')
            
            if user_has_role(user, 'farmer'):
                return redirect(url_for('main.farmer_dashboard'))
            elif user_has_role(user, 'buyer'):
                return redirect(url_for('main.buyer_dashboard'))
            else:
                return redirect(url_for('main.shop_owner_dashboard'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Phone verification error: {str(e)}")
            flash('Phone verification failed', 'danger')
            return redirect(url_for('auth.login_choice'))
    
    return render_template('verify_phone_otp.html', user_id=user_id, user_email=user.email)


@auth_bp.route('/login/<user_type>', methods=['GET', 'POST'])
def login(user_type):
    """Login for farmer, buyer, or shop owner"""
    if user_type not in ['farmer', 'buyer', 'shop_owner']:
        flash('Invalid user type', 'danger')
        return redirect(url_for('auth.login_choice'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email', '').strip()
        password = data.get('password', '')
        remember = data.get('remember', False)
        
        errors = []
        
        if not email or not password:
            errors.append('Email and password are required')
        
        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for error in errors:
                flash(error, 'danger')
            return render_template('login_choice.html', active_role=user_type, email=email, remember=bool(remember))
        
        user = User.query.filter_by(email=email).first()

        if not user:
            error_msg = 'Invalid email or password'
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 401
            flash(error_msg, 'danger')
            return render_template('login_choice.html', active_role=user_type, email=email, remember=bool(remember))

        if not user_has_role(user, user_type):
            error_msg = f'This account is not yet registered as {user_type.replace("_", " ")}. Register in that tab using the same email and phone to add the role.'
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 403
            flash(error_msg, 'danger')
            return render_template('login_choice.html', active_role=user_type, email=email, remember=bool(remember))

        # Allow pending users to continue OTP verification without password mismatch blocking them
        if not user.email_verified or not user.phone_verified:
            try:
                PhoneVerification.query.filter_by(user_id=user.id, verified=False).delete()
                otp = PhoneVerification.generate_otp()
                phone_verification = PhoneVerification(user_id=user.id, otp=otp)
                db.session.add(phone_verification)

                delivery_result = send_otp_for_user(user, otp, retries=2)
                if delivery_result['any_sent']:
                    db.session.commit()
                    if delivery_result['both_sent']:
                        msg = 'Your account is pending verification. A new OTP has been sent to your email and phone.'
                    elif delivery_result['email_sent']:
                        msg = f"Your account is pending verification. A new OTP has been sent to your email. {sms_unavailable_message(delivery_result)}"
                    else:
                        msg = 'Your account is pending verification. A new OTP has been sent to your phone (email failed).'
                    if request.is_json:
                        return jsonify({'success': False, 'errors': [msg]}), 403
                    flash(msg, 'warning')
                    return redirect(url_for('auth.verify_phone_otp', user_id=user.id))
                else:
                    detailed_error = otp_delivery_failure_reason(delivery_result)
                    if current_app.config.get('DEBUG'):
                        db.session.commit()
                        msg = f'OTP delivery failed on both channels in debug mode. Use this OTP for testing: {otp}'
                        if request.is_json:
                            return jsonify({'success': False, 'errors': [msg]}), 403
                        flash(msg, 'warning')
                        return redirect(url_for('auth.verify_phone_otp', user_id=user.id))

                    db.session.rollback()
                    msg = 'OTP step is pending, but delivery failed on both channels. Please try again shortly.'
                    if request.is_json:
                        return jsonify({'success': False, 'errors': [msg]}), 500
                    flash(msg, 'danger')
                    return render_template('login_choice.html', active_role=user_type, email=email, remember=bool(remember))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Resend OTP error: {str(e)}")
                msg = 'Unable to process OTP verification now. Please try again.'
                if request.is_json:
                    return jsonify({'success': False, 'errors': [msg]}), 500
                flash(msg, 'danger')
                return render_template('login_choice.html', active_role=user_type, email=email, remember=bool(remember))

        if not user.check_password(password):
            error_msg = 'Invalid email or password'
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 401
            flash(error_msg, 'danger')
            return render_template('login_choice.html', active_role=user_type, email=email, remember=bool(remember))
        
        if not user.is_active:
            error_msg = 'Your account has been deactivated'
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 403
            flash(error_msg, 'danger')
            return render_template('login_choice.html', active_role=user_type, email=email, remember=bool(remember))
        
        try:
            login_user(user, remember=bool(remember))
            if request.is_json:
                return jsonify({'success': True, 'message': 'Login successful'}), 200
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            
            if user_type == 'farmer':
                return redirect(url_for('main.farmer_dashboard'))
            elif user_type == 'buyer':
                return redirect(url_for('main.buyer_dashboard'))
            else:  # shop_owner
                return redirect(url_for('main.shop_owner_dashboard'))
        
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            error_msg = 'Login failed'
            if request.is_json:
                return jsonify({'success': False, 'errors': [error_msg]}), 500
            flash(error_msg, 'danger')
            return render_template('login_choice.html', active_role=user_type, email=email, remember=bool(remember))
    
    return render_template('login_choice.html', active_role=user_type)


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login_choice'))


# ==================== MAIN PAGES ====================

@main_bp.route('/farmer/dashboard')
@login_required
def farmer_dashboard():
    """Farmer dashboard"""
    if not user_has_role(current_user, 'farmer'):
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))

    active_tab = request.args.get('tab', 'dashboard').strip().lower()
    allowed_tabs = {'dashboard', 'products', 'orders', 'finished_orders'}
    if active_tab not in allowed_tabs:
        active_tab = 'dashboard'

    products = Product.query.filter_by(farmer_id=current_user.id).order_by(Product.created_at.desc()).all()
    completed_orders = Order.query.filter_by(
        farmer_id=current_user.id,
        status='completed'
    ).order_by(Order.completed_at.desc(), Order.created_at.desc()).all()

    return render_template(
        'farmer/dashboard.html',
        user=current_user,
        products=products,
        completed_orders=completed_orders,
        active_tab=active_tab,
        currency_rates=SUPPORTED_CURRENCY_RATES,
        display_currencies=['INR', 'USD', 'EUR', 'GBP', 'NPR', 'JPY'],
    )


@main_bp.route('/farmer/products/add', methods=['POST'])
@login_required
def add_farmer_product():
    """Add a new product for the logged-in farmer."""
    if not user_has_role(current_user, 'farmer'):
        flash('Only farmers can add products.', 'danger')
        return redirect(url_for('main.index'))

    try:
        result = validate_and_create_product_for_user(current_user)
        if not result['success']:
            for error in result['errors']:
                flash(error, 'danger')
            return redirect(url_for('main.farmer_dashboard', tab='products'))

        flash(f"Product added successfully! Saved base price: INR {result['inr_price']:.2f}", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Add product error: {str(e)}")
        flash('Unable to add product right now. Please try again.', 'danger')

    return redirect(url_for('main.farmer_dashboard', tab='products'))


@main_bp.route('/farmer/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_farmer_product(product_id):
    """Delete a product that belongs to the logged-in farmer."""
    if not user_has_role(current_user, 'farmer'):
        flash('Only farmers can delete products.', 'danger')
        return redirect(url_for('main.index'))

    product = Product.query.filter_by(id=product_id, farmer_id=current_user.id).first()
    if not product:
        flash('Product not found or access denied.', 'danger')
        return redirect(url_for('main.farmer_dashboard', tab='products'))

    try:
        if product.image_filename:
            image_path = os.path.join(current_app.static_folder, 'uploads', 'products', product.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)

        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete product error: {str(e)}")
        flash('Unable to delete product right now. Please try again.', 'danger')

    return redirect(url_for('main.farmer_dashboard', tab='products'))


@main_bp.route('/buyer/dashboard')
@login_required
def buyer_dashboard():
    """Buyer dashboard"""
    if not user_has_role(current_user, 'buyer'):
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))
    
    # Get statistics for dashboard
    active_orders = Order.query.filter_by(buyer_id=current_user.id).filter(
        Order.status.in_(['pending', 'accepted', 'shipped'])
    ).count()
    completed_orders = Order.query.filter_by(buyer_id=current_user.id, status='completed').count()
    total_spent = db.session.query(db.func.sum(Order.total_price)).filter_by(
        buyer_id=current_user.id, status='completed'
    ).scalar() or 0
    wishlist_count = Wishlist.query.filter_by(buyer_id=current_user.id).count()
    
    return render_template('buyer/dashboard.html', 
                         user=current_user,
                         active_orders=active_orders,
                         completed_orders=completed_orders,
                         total_spent=total_spent,
                         wishlist_count=wishlist_count)


@main_bp.route('/buyer/browse-products', methods=['GET'])
@login_required
def buyer_browse_products():
    """Browse all available products"""
    if not user_has_role(current_user, 'buyer'):
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all products from all sellers (farmers and shop owners)
    products = Product.query.order_by(Product.created_at.desc()).all()
    
    # Get wishlist items for current user
    wishlist_ids = db.session.query(Wishlist.product_id).filter_by(
        buyer_id=current_user.id
    ).all()
    wishlist_ids = [item[0] for item in wishlist_ids]
    
    return render_template('buyer/browse_products.html',
                         user=current_user,
                         products=products,
                         wishlist_ids=wishlist_ids)


@main_bp.route('/buyer/my-orders', methods=['GET'])
@login_required
def buyer_my_orders():
    """View all orders placed by the buyer"""
    if not user_has_role(current_user, 'buyer'):
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all orders placed by current user
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    return render_template('buyer/my_orders.html',
                         user=current_user,
                         orders=orders)


@main_bp.route('/buyer/wishlist', methods=['GET'])
@login_required
def buyer_wishlist():
    """View wishlist items"""
    if not user_has_role(current_user, 'buyer'):
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))
    
    # Get all wishlist items for current user
    wishlist_items = Wishlist.query.filter_by(buyer_id=current_user.id).all()
    
    return render_template('buyer/wishlist.html',
                         user=current_user,
                         wishlist_items=wishlist_items)


@main_bp.route('/buyer/profile', methods=['GET'])
@login_required
def buyer_profile():
    """View buyer profile"""
    if not user_has_role(current_user, 'buyer'):
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))
    
    return render_template('buyer/profile.html', user=current_user)


@main_bp.route('/buyer/profile/edit', methods=['GET', 'POST'])
@login_required
def buyer_profile_edit():
    """Edit buyer profile"""
    if not user_has_role(current_user, 'buyer'):
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            current_user.first_name = request.form.get('first_name', '').strip()
            current_user.last_name = request.form.get('last_name', '').strip()
            current_user.address = request.form.get('address', '').strip()
            current_user.city = request.form.get('city', '').strip()
            current_user.state = request.form.get('state', '').strip()
            current_user.postal_code = request.form.get('postal_code', '').strip()
            current_user.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('main.buyer_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('buyer/profile_edit.html', user=current_user)


@main_bp.route('/buyer/wishlist/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_wishlist(product_id):
    """Add product to wishlist"""
    if not user_has_role(current_user, 'buyer'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Check if product exists
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 404
        
        # Check if already in wishlist
        existing = Wishlist.query.filter_by(
            buyer_id=current_user.id,
            product_id=product_id
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'Product already in wishlist'}), 400
        
        # Add to wishlist
        wishlist_item = Wishlist(buyer_id=current_user.id, product_id=product_id)
        db.session.add(wishlist_item)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Added to wishlist'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@main_bp.route('/buyer/wishlist/remove/<int:wishlist_id>', methods=['POST'])
@login_required
def remove_from_wishlist(wishlist_id):
    """Remove product from wishlist"""
    if not user_has_role(current_user, 'buyer'):
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        wishlist_item = Wishlist.query.get(wishlist_id)
        if not wishlist_item or wishlist_item.buyer_id != current_user.id:
            return jsonify({'success': False, 'message': 'Wishlist item not found'}), 404
        
        db.session.delete(wishlist_item)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Removed from wishlist'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@main_bp.route('/shop-owner/dashboard')
@login_required
def shop_owner_dashboard():
    """Shop owner dashboard"""
    if not user_has_role(current_user, 'shop_owner'):
        flash('Access denied', 'danger')
        return redirect(url_for('main.index'))

    own_products = Product.query.filter_by(farmer_id=current_user.id).order_by(Product.created_at.desc()).all()
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('shop_owner/dashboard.html', user=current_user, own_products=own_products, products=products)


@main_bp.route('/shop-owner/products/add', methods=['POST'])
@login_required
def add_shop_owner_product():
    """Add a new product for the logged-in shop owner."""
    if not user_has_role(current_user, 'shop_owner'):
        flash('Only shop owners can add products.', 'danger')
        return redirect(url_for('main.index'))

    try:
        result = validate_and_create_product_for_user(current_user)
        if not result['success']:
            for error in result['errors']:
                flash(error, 'danger')
            return redirect(url_for('main.shop_owner_dashboard'))

        flash(f"Product added successfully! Saved base price: INR {result['inr_price']:.2f}", 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Add shop owner product error: {str(e)}")
        flash('Unable to add product right now. Please try again.', 'danger')

    return redirect(url_for('main.shop_owner_dashboard'))


@main_bp.route('/shop-owner/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_shop_owner_product(product_id):
    """Delete a product that belongs to the logged-in shop owner."""
    if not user_has_role(current_user, 'shop_owner'):
        flash('Only shop owners can delete products.', 'danger')
        return redirect(url_for('main.index'))

    product = Product.query.filter_by(id=product_id, farmer_id=current_user.id).first()
    if not product:
        flash('Product not found or access denied.', 'danger')
        return redirect(url_for('main.shop_owner_dashboard'))

    try:
        if product.image_filename:
            image_path = os.path.join(current_app.static_folder, 'uploads', 'products', product.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)

        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete shop owner product error: {str(e)}")
        flash('Unable to delete product right now. Please try again.', 'danger')

    return redirect(url_for('main.shop_owner_dashboard'))
