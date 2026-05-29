"""add title and has_design to orders

Revision ID: 7a6abfb2b273
Revises: 4c50145b58f1
Create Date: 2026-03-13 13:36:24.322949

"""
from alembic import op
import sqlalchemy as sa


 # Identificadores de revisión, usados por Alembic.
revision = '7a6abfb2b273'
down_revision = '4c50145b58f1'
branch_labels = None
depends_on = None


def upgrade():
    # ### comandos generados automáticamente por Alembic - ¡ajusta si es necesario! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('has_design', sa.Boolean(), nullable=True))

    # ### fin de comandos Alembic ###


def downgrade():
    # ### comandos generados automáticamente por Alembic - ¡ajusta si es necesario! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('has_design')
        batch_op.drop_column('title')

    # ### fin de comandos Alembic ###
