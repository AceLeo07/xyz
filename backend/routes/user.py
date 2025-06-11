from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Order, OrderItem, Product

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    
    # Get user's recent orders
    recent_orders = Order.query.filter_by(user_id=current_user_id)\
        .order_by(Order.created_at.desc())\
        .limit(5)\
        .all()
    
    # Get user's favorite products (most ordered)
    favorite_products = db.session.query(
        Product,
        db.func.sum(OrderItem.quantity).label('total_quantity')
    ).join(OrderItem).join(Order)\
        .filter(Order.user_id == current_user_id)\
        .group_by(Product.id)\
        .order_by(db.desc('total_quantity'))\
        .limit(5)\
        .all()
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'created_at': user.created_at.isoformat()
        },
        'recent_orders': [{
            'id': order.id,
            'total_amount': order.total_amount,
            'status': order.status,
            'created_at': order.created_at.isoformat()
        } for order in recent_orders],
        'favorite_products': [{
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'total_ordered': quantity
        } for product, quantity in favorite_products]
    }), 200

@user_bp.route('/orders/history', methods=['GET'])
@jwt_required()
def get_order_history():
    current_user_id = get_jwt_identity()
    
    # Get query parameters for filtering
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query
    query = Order.query.filter_by(user_id=current_user_id)
    
    # Apply filters
    if status:
        query = query.filter_by(status=status)
    if start_date:
        query = query.filter(Order.created_at >= start_date)
    if end_date:
        query = query.filter(Order.created_at <= end_date)
    
    # Get orders
    orders = query.order_by(Order.created_at.desc()).all()
    
    return jsonify([{
        'id': order.id,
        'total_amount': order.total_amount,
        'status': order.status,
        'created_at': order.created_at.isoformat(),
        'items': [{
            'product_id': item.product_id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price': item.price_at_time
        } for item in order.items]
    } for order in orders]), 200

@user_bp.route('/profile/update', methods=['PUT'])
@jwt_required()
def update_profile():
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    
    data = request.get_json()
    
    # Update fields if provided
    if 'username' in data:
        # Check if username is already taken
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user and existing_user.id != current_user_id:
            return jsonify({'error': 'Username already taken'}), 400
        user.username = data['username']
    
    if 'email' in data:
        # Check if email is already taken
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user and existing_user.id != current_user_id:
            return jsonify({'error': 'Email already taken'}), 400
        user.email = data['email']
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile'}), 500

@user_bp.route('/cart', methods=['GET'])
@jwt_required()
def get_cart():
    # Note: This is a placeholder for cart functionality
    # In a real application, you would implement a Cart model and related operations
    return jsonify({
        'message': 'Cart functionality to be implemented',
        'cart': []
    }), 200 