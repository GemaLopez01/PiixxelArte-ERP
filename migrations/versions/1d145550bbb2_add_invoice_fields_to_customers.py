"""add invoice fields to customers

Revision ID: 1d145550bbb2
Revises: 7a6abfb2b273
Create Date: 2026-03-13 14:36:08.683807

"""
from alembic import op
import sqlalchemy as sa


 # Identificadores de revisión, usados por Alembic.
revision = '1d145550bbb2'
down_revision = '7a6abfb2b273'
branch_labels = None
depends_on = None


def upgrade():
    # ### comandos generados automáticamente por Alembic - ¡ajusta si es necesario! ###
    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('requires_invoice', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('rfc', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('business_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('tax_regime', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('zip_code', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('billing_address', sa.Text(), nullable=True))

    # ### fin de comandos Alembic ###


def downgrade():
    # ### comandos generados automáticamente por Alembic - ¡ajusta si es necesario! ###
    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.drop_column('billing_address')
        batch_op.drop_column('zip_code')
        batch_op.drop_column('tax_regime')
        batch_op.drop_column('business_name')
        batch_op.drop_column('rfc')
        batch_op.drop_column('requires_invoice')

    # ### fin de comandos Alembic ###
