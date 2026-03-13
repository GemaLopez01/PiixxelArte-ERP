from datetime import datetime
from app.extensions import db

class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_info = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    materials = db.relationship('Material', backref='supplier', lazy=True)

class Material(db.Model):
    __tablename__ = 'materials'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    stock_quantity = db.Column(db.Numeric(10, 2), default=0.0)
    unit_measure = db.Column(db.String(50), nullable=False) # e.g., meters, rolls, units, liters
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
