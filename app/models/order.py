from datetime import datetime
from app.extensions import db

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # The user who created the order
    
    title = db.Column(db.String(150), nullable=True) # Nombre del trabajo
    has_design = db.Column(db.Boolean, default=False) # ¿Ya tienen diseño?
    
    status = db.Column(db.String(50), nullable=False, default='Pendiente') # Pendiente, Diseño, Producción, Listo, Entregado
    delivery_date = db.Column(db.DateTime, nullable=True)
    
    subtotal_amount = db.Column(db.Numeric(10, 2), default=0.0) # Sum of all items before global discount
    discount_amount = db.Column(db.Numeric(10, 2), default=0.0) # Global manual discount
    tax_amount = db.Column(db.Numeric(10, 2), default=0.0)      # IVA explicitly tracked
    total_amount = db.Column(db.Numeric(10, 2), default=0.0)    # Final amount
    
    # Financial Tracking
    advance_payment = db.Column(db.Numeric(10, 2), default=0.0) # Anticipo
    payment_method = db.Column(db.String(50), nullable=True)    # Efectivo, Tarjeta, Transferencia
    payment_status = db.Column(db.String(50), default='Pendiente de pago') # Pendiente de pago, Parcial, Pagado
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='order', lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False, default=1)
    
    # Dimensions for dynamically calculated products (in meters or cm, based on business logic)
    width = db.Column(db.Numeric(8, 2), nullable=True)  
    height = db.Column(db.Numeric(8, 2), nullable=True) 
    
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    discount_applied = db.Column(db.Boolean, default=False) # True if min_qty was met
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
