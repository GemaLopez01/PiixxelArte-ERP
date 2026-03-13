from datetime import datetime
from app.extensions import db

class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    advance_payment = db.Column(db.Numeric(10, 2), default=0.0)
    remaining_payment = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pendiente') # Pendiente, Pagado, Anticipo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
