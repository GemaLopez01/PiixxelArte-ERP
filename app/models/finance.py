from datetime import datetime
from app.extensions import db

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False) # 'Ingreso' or 'Egreso'
    category = db.Column(db.String(100), nullable=False) 
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True) 
    
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Optional links
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey('purchases.id'), nullable=True)
