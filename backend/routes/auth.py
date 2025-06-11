from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User, OTP
from flask_bcrypt import Bcrypt
from email_validator import validate_email, EmailNotValidError
from datetime import datetime, timedelta
import random
import string
import os
import requests

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')
MAILGUN_DOMAIN = os.getenv('MAILGUN_DOMAIN')
MAILGUN_FROM_EMAIL = os.getenv('MAILGUN_FROM_EMAIL')

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_otp(email, otp_code):
    """
    Send OTP via Mailgun email
    """
    if not (MAILGUN_API_KEY and MAILGUN_DOMAIN and MAILGUN_FROM_EMAIL):
        print(f"[DEV] Sending OTP {otp_code} to {email} (Mailgun not configured)")
        return True
    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": MAILGUN_FROM_EMAIL,
                "to": [email],
                "subject": "Your OTP Code",
                "text": f"Your OTP code is: {otp_code}"
            }
        )
        print(f"[MAILGUN] Sent OTP {otp_code} to {email}. Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"[MAILGUN ERROR] {e}")
        return False

@auth_bp.route('/register/initiate', methods=['POST'])
def initiate_registration():
    data = request.get_json()
    required_fields = ['username', 'role']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    # Accept either email or phone_number
    email = data.get('email')
    phone_number = data.get('phone_number')
    if not email and not phone_number:
        return jsonify({'error': 'Email or phone number required'}), 400
    if email:
        try:
            validate_email(email)
        except EmailNotValidError:
            return jsonify({'error': 'Invalid email address'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400
    if phone_number and User.query.filter_by(phone_number=phone_number).first():
        return jsonify({'error': 'Phone number already registered'}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 400
    otp_code = generate_otp()
    new_user = User(
        username=data['username'],
        phone_number=phone_number,
        email=email,
        role=data['role']
    )
    try:
        db.session.add(new_user)
        db.session.flush()
        otp = OTP(
            user_id=new_user.id,
            code=otp_code,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(otp)
        db.session.commit()
        # Send OTP via email if provided, else print for dev
        if email:
            sent = send_otp(email, otp_code)
        else:
            print(f"[DEV] OTP for {phone_number}: {otp_code}")
            sent = True
        if sent:
            return jsonify({'message': 'OTP sent successfully', 'user_id': new_user.id}), 200
        else:
            db.session.rollback()
            return jsonify({'error': 'Failed to send OTP'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/register/verify', methods=['POST'])
def verify_registration():
    data = request.get_json()
    if not data or 'user_id' not in data or 'otp' not in data:
        return jsonify({'error': 'Missing user ID or OTP'}), 400
    user = User.query.get_or_404(data['user_id'])
    otp = OTP.query.filter_by(user_id=user.id, is_used=False).order_by(OTP.created_at.desc()).first()
    if not otp or not otp.is_valid():
        return jsonify({'error': 'Invalid or expired OTP'}), 400
    if otp.code != data['otp']:
        return jsonify({'error': 'Invalid OTP'}), 400
    otp.is_used = True
    db.session.commit()
    access_token = create_access_token(identity=user.id)
    return jsonify({
        'message': 'Registration successful',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'phone_number': user.phone_number,
            'email': user.email,
            'role': user.role
        }
    }), 200

@auth_bp.route('/login/initiate', methods=['POST'])
def initiate_login():
    data = request.get_json()
    email = data.get('email')
    phone_number = data.get('phone_number')
    if not email and not phone_number:
        return jsonify({'error': 'Email or phone number is required'}), 400
    user = None
    if email:
        user = User.query.filter_by(email=email).first()
    elif phone_number:
        user = User.query.filter_by(phone_number=phone_number).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    otp_code = generate_otp()
    otp = OTP(
        user_id=user.id,
        code=otp_code,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    try:
        db.session.add(otp)
        db.session.commit()
        if email:
            sent = send_otp(email, otp_code)
        else:
            print(f"[DEV] OTP for {phone_number}: {otp_code}")
            sent = True
        if sent:
            return jsonify({'message': 'OTP sent successfully', 'user_id': user.id}), 200
        else:
            db.session.rollback()
            return jsonify({'error': 'Failed to send OTP'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/login/verify', methods=['POST'])
def verify_login():
    data = request.get_json()
    if not data or 'user_id' not in data or 'otp' not in data:
        return jsonify({'error': 'Missing user ID or OTP'}), 400
    user = User.query.get_or_404(data['user_id'])
    otp = OTP.query.filter_by(user_id=user.id, is_used=False).order_by(OTP.created_at.desc()).first()
    if not otp or not otp.is_valid():
        return jsonify({'error': 'Invalid or expired OTP'}), 400
    if otp.code != data['otp']:
        return jsonify({'error': 'Invalid OTP'}), 400
    otp.is_used = True
    db.session.commit()
    access_token = create_access_token(identity=user.id)
    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'phone_number': user.phone_number,
            'email': user.email,
            'role': user.role
        }
    }), 200

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'id': user.id,
        'username': user.username,
        'phone_number': user.phone_number,
        'email': user.email,
        'role': user.role,
        'created_at': user.created_at.isoformat()
    }), 200 