# Canteen Management System - Backend

This is the backend API for the Canteen Management System, built with Flask and SQLAlchemy.

## Features

- User authentication and authorization
- Product management for sellers
- Order management
- Payment processing with Stripe
- Role-based access control (User/Seller)

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
- Copy `.env.example` to `.env`
- Update the values in `.env` with your configuration

4. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

5. Run the application:
```bash
python app.py
```

## API Endpoints

### Authentication
- POST `/api/auth/register` - Register a new user
- POST `/api/auth/login` - Login user
- GET `/api/auth/profile` - Get user profile

### Products
- GET `/api/products` - List all products
- GET `/api/products/<id>` - Get product details
- POST `/api/products` - Create new product (seller only)
- PUT `/api/products/<id>` - Update product (seller only)
- DELETE `/api/products/<id>` - Delete product (seller only)

### Orders
- POST `/api/orders` - Create new order
- GET `/api/orders` - List orders
- GET `/api/orders/<id>` - Get order details
- PUT `/api/orders/<id>/status` - Update order status (seller only)

### Payments
- POST `/api/payments/create-payment-intent` - Create payment intent
- GET `/api/payments/<id>` - Get payment details
- GET `/api/payments/order/<id>` - Get order payment details

## Security

- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- Input validation
- Secure payment processing with Stripe

## Error Handling

The API uses standard HTTP status codes and returns JSON responses with error messages when something goes wrong.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 