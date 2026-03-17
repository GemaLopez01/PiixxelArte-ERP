from datetime import datetime
from app.extensions import db

class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_info = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(150), nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    materials = db.relationship('Material', backref='supplier', lazy=True)
    purchases = db.relationship('Purchase', backref='supplier', lazy=True)

class Material(db.Model):
    __tablename__ = 'materials'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=True) # Rigidos, Flexibles, Tintas, etc.
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    
    stock_quantity = db.Column(db.Numeric(10, 2), default=0.0)
    min_stock = db.Column(db.Numeric(10, 2), default=0.0)
    
    unit_measure = db.Column(db.String(50), nullable=False) # m2, metros, piezas, ml
    location = db.Column(db.String(150), nullable=True)
    approx_cost = db.Column(db.Numeric(10, 2), nullable=True)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    movements = db.relationship('InventoryMovement', backref='material', lazy=True)
    products = db.relationship('Product', backref='material', lazy=True)

class InventoryMovement(db.Model):
    __tablename__ = 'inventory_movements'
    
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False) # Entrada or Salida
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    reason = db.Column(db.String(150), nullable=False) # Compra, Uso en pedido, Desperdicio, Ajuste
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Purchase(db.Model):
    __tablename__ = 'purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), default=0.0)
    status = db.Column(db.String(50), default='Pendiente') # Pendiente, Recibida
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('PurchaseItem', backref='purchase', lazy=True, cascade='all, delete-orphan')

class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
