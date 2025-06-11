from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Payment, Order, User
import stripe
import os

payment_bp = Blueprint('payment', __name__)

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@payment_bp.route('/create-payment-intent', methods=['POST'])
@jwt_required()
def create_payment_intent():
    data = request.get_json()
    if not data or 'order_id' not in data:
        return jsonify({'error': 'Order ID is required'}), 400
    
    order = Order.query.get_or_404(data['order_id'])
    
    # Verify that the order belongs to the current user
    if order.user_id != get_jwt_identity():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if payment already exists
    if order.payment:
        return jsonify({'error': 'Payment already exists for this order'}), 400
    
    try:
        # Create a payment intent with Stripe
        intent = stripe.PaymentIntent.create(
            amount=int(order.total_amount * 100),  # Convert to cents
            currency='usd',
            metadata={'order_id': order.id}
        )
        
        # Create payment record
        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            status='pending',
            payment_method='stripe',
            transaction_id=intent.id
        )
        
        db.session.add(payment)
        db.session.commit()
        
        return jsonify({
            'client_secret': intent.client_secret,
            'payment_id': payment.id
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid signature'}), 400
    
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        payment = Payment.query.filter_by(
            transaction_id=payment_intent['id']
        ).first()
        
        if payment:
            payment.status = 'completed'
            payment.order.status = 'confirmed'
            db.session.commit()
    
    return jsonify({'status': 'success'}), 200

@payment_bp.route('/<int:payment_id>', methods=['GET'])
@jwt_required()
def get_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    # Check if user has permission to view this payment
    if payment.order.user_id != get_jwt_identity():
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'id': payment.id,
        'order_id': payment.order_id,
        'amount': payment.amount,
        'status': payment.status,
        'payment_method': payment.payment_method,
        'created_at': payment.created_at.isoformat()
    }), 200

@payment_bp.route('/order/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_payment(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Check if user has permission to view this payment
    if order.user_id != get_jwt_identity():
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not order.payment:
        return jsonify({'error': 'No payment found for this order'}), 404
    
    return jsonify({
        'id': order.payment.id,
        'amount': order.payment.amount,
        'status': order.payment.status,
        'payment_method': order.payment.payment_method,
        'created_at': order.payment.created_at.isoformat()
    }), 200 