from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Order, OrderItem, Product, User

order_bp = Blueprint('order', __name__)

@order_bp.route('/', methods=['POST'])
@jwt_required()
def create_order():
    data = request.get_json()
    if not data or 'items' not in data:
        return jsonify({'error': 'No items provided'}), 400
    
    # Calculate total amount and validate items
    total_amount = 0
    order_items = []
    
    for item in data['items']:
        product = Product.query.get(item['product_id'])
        if not product:
            return jsonify({'error': f'Product {item["product_id"]} not found'}), 404
        if product.stock < item['quantity']:
            return jsonify({'error': f'Insufficient stock for product {product.name}'}), 400
        
        total_amount += product.price * item['quantity']
        order_items.append({
            'product': product,
            'quantity': item['quantity'],
            'price': product.price
        })
    
    # Create order
    new_order = Order(
        user_id=get_jwt_identity(),
        total_amount=total_amount,
        status='pending'
    )
    
    try:
        db.session.add(new_order)
        db.session.flush()  # Get the order ID
        
        # Create order items and update stock
        for item in order_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item['product'].id,
                quantity=item['quantity'],
                price_at_time=item['price']
            )
            item['product'].stock -= item['quantity']
            db.session.add(order_item)
        
        db.session.commit()
        return jsonify({
            'message': 'Order created successfully',
            'order_id': new_order.id,
            'total_amount': total_amount
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create order'}), 500

@order_bp.route('/', methods=['GET'])
@jwt_required()
def get_orders():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if user.role == 'seller':
        # Sellers see orders for their products
        orders = Order.query.join(OrderItem).join(Product).filter(
            Product.seller_id == current_user_id
        ).distinct().all()
    else:
        # Users see their own orders
        orders = Order.query.filter_by(user_id=current_user_id).all()
    
    return jsonify([{
        'id': order.id,
        'total_amount': order.total_amount,
        'status': order.status,
        'created_at': order.created_at.isoformat(),
        'items': [{
            'product_id': item.product_id,
            'quantity': item.quantity,
            'price': item.price_at_time
        } for item in order.items]
    } for order in orders]), 200

@order_bp.route('/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    order = Order.query.get_or_404(order_id)
    
    # Check if user has permission to view this order
    if user.role == 'user' and order.user_id != current_user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    elif user.role == 'seller':
        # Check if seller has any products in this order
        seller_products = any(
            item.product.seller_id == current_user_id
            for item in order.items
        )
        if not seller_products:
            return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({
        'id': order.id,
        'total_amount': order.total_amount,
        'status': order.status,
        'created_at': order.created_at.isoformat(),
        'items': [{
            'product_id': item.product_id,
            'quantity': item.quantity,
            'price': item.price_at_time
        } for item in order.items]
    }), 200

@order_bp.route('/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if user.role != 'seller':
        return jsonify({'error': 'Only sellers can update order status'}), 403
    
    order = Order.query.get_or_404(order_id)
    
    # Check if seller has any products in this order
    seller_products = any(
        item.product.seller_id == current_user_id
        for item in order.items
    )
    if not seller_products:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    if 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
    
    valid_statuses = ['pending', 'confirmed', 'completed', 'cancelled']
    if data['status'] not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400
    
    order.status = data['status']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Order status updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update order status'}), 500 