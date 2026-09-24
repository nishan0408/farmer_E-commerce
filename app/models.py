from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for both farmers and buyers"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'farmer' or 'buyer'
    
    # Profile Information
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    profile_picture = db.Column(db.String(255))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    
    # Account Status
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Farmer specific fields
    farm_name = db.Column(db.String(200))
    farm_size = db.Column(db.String(100))
    crops_grown = db.Column(db.Text)
    
    # Shop owner specific fields
    shop_name = db.Column(db.String(200))
    shop_category = db.Column(db.String(100))  # grocery, electronics, clothing, etc.
    shop_license_number = db.Column(db.String(100), unique=True)
    shop_description = db.Column(db.Text)
    shop_registration_number = db.Column(db.String(100), unique=True)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'


class Product(db.Model):
    """Product listed by a farmer"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    quality = db.Column(db.String(20), nullable=False)  # average, good, premium
    image_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    farmer = db.relationship('User', backref=db.backref('products', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Product {self.name} by farmer {self.farmer_id}>'


class Order(db.Model):
    """Order placed by a buyer for a farmer product"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), nullable=False, default='INR')
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, accepted, shipped, completed, cancelled
    shipping_address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    product = db.relationship('Product', backref=db.backref('orders', cascade='all, delete-orphan'))
    farmer = db.relationship('User', foreign_keys=[farmer_id], backref=db.backref('received_orders', cascade='all, delete-orphan'))
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref=db.backref('placed_orders', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Order #{self.id} status={self.status}>'


class Wishlist(db.Model):
    """Wishlist item for a buyer"""
    __tablename__ = 'wishlist'
    
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    buyer = db.relationship('User', backref=db.backref('wishlist_items', cascade='all, delete-orphan'))
    product = db.relationship('Product', backref=db.backref('in_wishlists', cascade='all, delete-orphan'))
    
    __table_args__ = (db.UniqueConstraint('buyer_id', 'product_id', name='unique_buyer_product_wishlist'),)
    
    def __repr__(self):
        return f'<Wishlist {self.buyer_id} - {self.product_id}>'


class EmailVerification(db.Model):
    """Email verification token storage"""
    __tablename__ = 'email_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))
    verified = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('email_verifications', cascade='all, delete-orphan'))
    
    @staticmethod
    def generate_token():
        """Generate a random verification token"""
        return secrets.token_urlsafe(32)


class PhoneVerification(db.Model):
    """Phone OTP verification storage"""
    __tablename__ = 'phone_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=10))
    verified = db.Column(db.Boolean, default=False)
    attempts = db.Column(db.Integer, default=0)
    
    user = db.relationship('User', backref=db.backref('phone_verifications', cascade='all, delete-orphan'))
    
    @staticmethod
    def generate_otp():
        """Generate a random 6-digit OTP"""
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    def is_expired(self):
        """Check if OTP has expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid_attempt(self):
        """Check if attempts haven't exceeded limit"""
        return self.attempts < 3


class PasswordReset(db.Model):
    """Password reset token storage"""
    __tablename__ = 'password_resets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=1))
    used = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('password_resets', cascade='all, delete-orphan'))
    
    @staticmethod
    def generate_token():
        """Generate a random reset token"""
        return secrets.token_urlsafe(32)
