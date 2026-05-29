"""add min_price to product

Revision ID: bc0c79be036c
Revises: cd62d5c319d9
Create Date: 2026-03-13 16:55:21.589948

"""
from alembic import op
import sqlalchemy as sa


 # Identificadores de revisión, usados por Alembic.
revision = 'bc0c79be036c'
down_revision = 'cd62d5c319d9'
branch_labels = None
depends_on = None


def upgrade():
    # ### comandos generados automáticamente por Alembic - ¡ajusta si es necesario! ###
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('min_price', sa.Numeric(precision=10, scale=2), nullable=True))

    # ### fin de comandos Alembic ###


def downgrade():
    # ### comandos generados automáticamente por Alembic - ¡ajusta si es necesario! ###
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('min_price')

    # ### fin de comandos Alembic ###
