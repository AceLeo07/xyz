from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Product, Order, OrderItem
from datetime import datetime, timedelta
from sqlalchemy import func

seller_bp = Blueprint('seller', __name__)

def is_seller():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user and user.role == 'seller'

@seller_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    if not is_seller():
        return jsonify({'error': 'Unauthorized'}), 403
    
    current_user_id = get_jwt_identity()
    
    # Get total products
    total_products = Product.query.filter_by(seller_id=current_user_id).count()
    
    # Get total sales
    total_sales = db.session.query(func.sum(OrderItem.quantity * OrderItem.price_at_time))\
        .join(Product)\
        .filter(Product.seller_id == current_user_id)\
        .scalar() or 0
    
    # Get recent orders
    recent_orders = Order.query.join(OrderItem).join(Product)\
        .filter(Product.seller_id == current_user_id)\
        .distinct()\
        .order_by(Order.created_at.desc())\
        .limit(5)\
        .all()
    
    # Get top selling products
    top_products = db.session.query(
        Product,
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.sum(OrderItem.quantity * OrderItem.price_at_time).label('total_revenue')
    ).join(OrderItem)\
        .filter(Product.seller_id == current_user_id)\
        .group_by(Product.id)\
        .order_by(func.sum(OrderItem.quantity).desc())\
        .limit(5)\
        .all()
    
    return jsonify({
        'summary': {
            'total_products': total_products,
            'total_sales': float(total_sales)
        },
        'recent_orders': [{
            'id': order.id,
            'total_amount': order.total_amount,
            'status': order.status,
            'created_at': order.created_at.isoformat()
        } for order in recent_orders],
        'top_products': [{
            'id': product.id,
            'name': product.name,
            'total_quantity': quantity,
            'total_revenue': float(revenue)
        } for product, quantity, revenue in top_products]
    }), 200

@seller_bp.route('/sales/analytics', methods=['GET'])
@jwt_required()
def get_sales_analytics():
    if not is_seller():
        return jsonify({'error': 'Unauthorized'}), 403
    
    current_user_id = get_jwt_identity()
    
    # Get date range from query parameters
    days = int(request.args.get('days', 7))
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get daily sales
    daily_sales = db.session.query(
        func.date(Order.created_at).label('date'),
        func.sum(OrderItem.quantity * OrderItem.price_at_time).label('total_sales')
    ).join(OrderItem).join(Product)\
        .filter(
            Product.seller_id == current_user_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        )\
        .group_by(func.date(Order.created_at))\
        .all()
    
    # Get sales by category
    category_sales = db.session.query(
        Product.category,
        func.sum(OrderItem.quantity * OrderItem.price_at_time).label('total_sales')
    ).join(OrderItem)\
        .filter(
            Product.seller_id == current_user_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        )\
        .group_by(Product.category)\
        .all()
    
    return jsonify({
        'daily_sales': [{
            'date': str(date),
            'total_sales': float(total_sales)
        } for date, total_sales in daily_sales],
        'category_sales': [{
            'category': category,
            'total_sales': float(total_sales)
        } for category, total_sales in category_sales]
    }), 200

@seller_bp.route('/inventory', methods=['GET'])
@jwt_required()
def get_inventory():
    if not is_seller():
        return jsonify({'error': 'Unauthorized'}), 403
    
    current_user_id = get_jwt_identity()
    
    # Get query parameters
    category = request.args.get('category')
    low_stock = request.args.get('low_stock', 'false').lower() == 'true'
    
    # Base query
    query = Product.query.filter_by(seller_id=current_user_id)
    
    # Apply filters
    if category:
        query = query.filter_by(category=category)
    if low_stock:
        query = query.filter(Product.stock < 10)  # Consider stock < 10 as low stock
    
    products = query.all()
    
    return jsonify([{
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'stock': product.stock,
        'category': product.category,
        'image_url': product.image_url
    } for product in products]), 200

@seller_bp.route('/orders/pending', methods=['GET'])
@jwt_required()
def get_pending_orders():
    if not is_seller():
        return jsonify({'error': 'Unauthorized'}), 403
    
    current_user_id = get_jwt_identity()
    
    # Get pending orders for seller's products
    pending_orders = Order.query.join(OrderItem).join(Product)\
        .filter(
            Product.seller_id == current_user_id,
            Order.status == 'pending'
        )\
        .distinct()\
        .order_by(Order.created_at.asc())\
        .all()
    
    return jsonify([{
        'id': order.id,
        'total_amount': order.total_amount,
        'created_at': order.created_at.isoformat(),
        'items': [{
            'product_id': item.product_id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'price': item.price_at_time
        } for item in order.items if item.product.seller_id == current_user_id]
    } for order in pending_orders]), 200 