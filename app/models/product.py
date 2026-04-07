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
    is_on_demand = db.Column(db.Boolean, default=False)
    image_path = db.Column(db.String(255), nullable=True)
    
    is_dynamic_pricing = db.Column(db.Boolean, default=False) # True for items sold by dimension (Deprecated implicitly by pricing_strategy)
    
    # New Pricing Strategies
    # standard: fixed price
    # area_based: uses width * height (replaces is_dynamic_pricing)
    # formula_sellos: (base_price * 2) + 60
    # tiered_blocks: base_price + ((qty - 1) * block_increment)
    pricing_strategy = db.Column(db.String(50), default='standard') 
    block_increment = db.Column(db.Numeric(10, 2), nullable=True) # Used for tiered_blocks
    # Discounts & Limits
    min_qty_discount = db.Column(db.Integer, nullable=True) # Minimum pieces for discount
    discount_percentage = db.Column(db.Numeric(5, 2), nullable=True) # Percentage (e.g., 10 for 10%)
    min_price = db.Column(db.Numeric(10, 2), nullable=True) # Minimum price to charge for dynamic items
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Inventory Integration
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=True)

    # Relationships
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    def calculate_price(self, qty=1, width=None, height=None):
        """Calculated total price considering the strategy."""
        total_price = 0.0
        
        # Determine strategy (fallback to old ones if strategy not explicitly migrated)
        strategy = self.pricing_strategy
        if self.is_dynamic_pricing and strategy == 'standard':
            strategy = 'area_based'
            
        if strategy == 'area_based':
            if width is not None and height is not None:
                area = (width / 100) * (height / 100)  # cm to m2
                total_price = area * float(self.base_price) * qty
            else:
                total_price = float(self.base_price) * qty
                
            if self.min_price is not None:
                total_price = max(total_price, float(self.min_price) * qty)
                
        elif strategy == 'formula_sellos':
            # Formula: (Precio Lista * 2 + 60) per unit
            # Assumes 60 is the hardware cost per piece
            total_price = ((float(self.base_price) * 2.0) + 60.0) * qty
            
        elif strategy == 'tiered_blocks':
            # Formula: base_price for the first block, then + block_increment for each additional block
            if qty > 0:
                increment = float(self.block_increment) if self.block_increment else 0.0
                total_price = float(self.base_price) + ((qty - 1) * increment)
            else:
                total_price = 0.0
                
        else: # standard
            total_price = float(self.base_price) * qty

        # Discount override limit applies to area_based usually, but we keep it modular
        # (Assuming the main view applies min_qty_discount percentage manually, we just return the raw total here)
        return total_price
        
    def calculate_unit_price(self, width=None, height=None):
        """Calculated unit price for standard and area items for UI display."""
        if self.pricing_strategy == 'area_based' or self.is_dynamic_pricing:
            if width is not None and height is not None:
                area = (width / 100) * (height / 100)
                unit_price = area * float(self.base_price)
            else:
                unit_price = float(self.base_price)
            if self.min_price is not None:
                unit_price = max(unit_price, float(self.min_price))
            return unit_price
        elif self.pricing_strategy == 'formula_sellos':
            return (float(self.base_price) * 2.0) + 60.0
        elif self.pricing_strategy == 'tiered_blocks':
            # Unit price doesn't linearly make sense for display if mixed, we return base to display
            return float(self.base_price)
        return float(self.base_price)

