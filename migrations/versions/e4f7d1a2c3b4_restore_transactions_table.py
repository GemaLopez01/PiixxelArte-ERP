"""Restore transactions table for finance features

Revision ID: e4f7d1a2c3b4
Revises: ac04076c10e1
Create Date: 2026-04-11 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'e4f7d1a2c3b4'
down_revision = 'ac04076c10e1'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table('transactions'):
        op.create_table(
            'transactions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('type', sa.String(length=50), nullable=False),
            sa.Column('category', sa.String(length=100), nullable=False),
            sa.Column('amount', sa.Numeric(10, 2), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('payment_method', sa.String(length=50), nullable=True),
            sa.Column('date', sa.DateTime(), nullable=False),
            sa.Column('order_id', sa.Integer(), sa.ForeignKey('orders.id'), nullable=True),
            sa.Column('purchase_id', sa.Integer(), sa.ForeignKey('purchases.id'), nullable=True),
        )
        return

    columns = {column['name'] for column in inspector.get_columns('transactions')}

    if 'date' not in columns:
        op.add_column('transactions', sa.Column('date', sa.DateTime(), nullable=True))

        if 'created_at' in columns:
            op.execute(sa.text('UPDATE transactions SET date = created_at WHERE date IS NULL'))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table('transactions'):
        op.drop_table('transactions')