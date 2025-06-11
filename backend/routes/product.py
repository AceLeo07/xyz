from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Product, User

product_bp = Blueprint('product', __name__)

def is_seller():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user and user.role == 'seller'

@product_bp.route('/', methods=['POST'])
@jwt_required()
def create_product():
    if not is_seller():
        return jsonify({'error': 'Only sellers can create products'}), 403
    
    data = request.get_json()
    required_fields = ['name', 'price', 'stock']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    new_product = Product(
        name=data['name'],
        description=data.get('description', ''),
        price=float(data['price']),
        stock=int(data['stock']),
        seller_id=get_jwt_identity(),
        category=data.get('category', ''),
        image_url=data.get('image_url', '')
    )
    
    try:
        db.session.add(new_product)
        db.session.commit()
        return jsonify({
            'message': 'Product created successfully',
            'product': {
                'id': new_product.id,
                'name': new_product.name,
                'price': new_product.price,
                'stock': new_product.stock
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create product'}), 500

@product_bp.route('/', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'price': p.price,
        'stock': p.stock,
        'category': p.category,
        'image_url': p.image_url,
        'seller_id': p.seller_id
    } for p in products]), 200

@product_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description,
        'price': product.price,
        'stock': product.stock,
        'category': product.category,
        'image_url': product.image_url,
        'seller_id': product.seller_id
    }), 200

@product_bp.route('/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    if not is_seller():
        return jsonify({'error': 'Only sellers can update products'}), 403
    
    product = Product.query.get_or_404(product_id)
    if product.seller_id != get_jwt_identity():
        return jsonify({'error': 'You can only update your own products'}), 403
    
    data = request.get_json()
    if 'name' in data:
        product.name = data['name']
    if 'description' in data:
        product.description = data['description']
    if 'price' in data:
        product.price = float(data['price'])
    if 'stock' in data:
        product.stock = int(data['stock'])
    if 'category' in data:
        product.category = data['category']
    if 'image_url' in data:
        product.image_url = data['image_url']
    
    try:
        db.session.commit()
        return jsonify({'message': 'Product updated successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update product'}), 500

@product_bp.route('/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    if not is_seller():
        return jsonify({'error': 'Only sellers can delete products'}), 403
    
    product = Product.query.get_or_404(product_id)
    if product.seller_id != get_jwt_identity():
        return jsonify({'error': 'You can only delete your own products'}), 403
    
    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({'message': 'Product deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete product'}), 500 