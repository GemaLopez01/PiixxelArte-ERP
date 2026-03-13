from datetime import datetime
from app.extensions import db

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=True, unique=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    unit_measure = db.Column(db.String(50), default='Pieza') # Pieza, Metro Lineal, M2 ...
    has_tax = db.Column(db.Boolean, default=False)
    image_path = db.Column(db.String(255), nullable=True)
    
    is_dynamic_pricing = db.Column(db.Boolean, default=False) # True for items sold by dimension
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
