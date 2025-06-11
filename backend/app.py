from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configure app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///canteen.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# Initialize extensions (do not create db here)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)

# Import models and use the db instance from models.py
from models import db, User, Product, Order, OrderItem, Payment, OTP

db.init_app(app)

# Import and register blueprints
from routes.auth import auth_bp
from routes.product import product_bp
from routes.order import order_bp
from routes.payment import payment_bp
from routes.user import user_bp
from routes.seller import seller_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(product_bp, url_prefix='/api/products')
app.register_blueprint(order_bp, url_prefix='/api/orders')
app.register_blueprint(payment_bp, url_prefix='/api/payments')
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(seller_bp, url_prefix='/api/seller')

# Create database tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return "Backend is running! Use the /api/ endpoints for API access."

if __name__ == '__main__':
    app.run(debug=True) 