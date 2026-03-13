from datetime import datetime
from app.extensions import db

class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    # Fiscal Details
    requires_invoice = db.Column(db.Boolean, default=False)
    rfc = db.Column(db.String(20), nullable=True)
    business_name = db.Column(db.String(150), nullable=True) # Razón social
    tax_regime = db.Column(db.String(100), nullable=True)
    zip_code = db.Column(db.String(10), nullable=True)
    billing_address = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    orders = db.relationship('Order', backref='customer', lazy=True)
