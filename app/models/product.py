from datetime import datetime
from app.extensions import db

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    is_dynamic_pricing = db.Column(db.Boolean, default=False) # True for items sold by meter (vinyl, canvas)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
