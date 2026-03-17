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
    
    # Discounts & Limits
    min_qty_discount = db.Column(db.Integer, nullable=True) # Minimum pieces for discount
    discount_percentage = db.Column(db.Numeric(5, 2), nullable=True) # Percentage (e.g., 10 for 10%)
    min_price = db.Column(db.Numeric(10, 2), nullable=True) # Minimum price to charge for dynamic items
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    def calculate_unit_price(self, width=None, height=None):
        """Calculated unit price with dynamic pricing + minimum price guard."""
        if self.is_dynamic_pricing and width is not None and height is not None:
            area = (width / 100) * (height / 100)  # cm to m2
            unit_price = area * float(self.base_price)
        else:
            unit_price = float(self.base_price)

        if self.min_price is not None:
            unit_price = max(unit_price, float(self.min_price))

        return unit_price

