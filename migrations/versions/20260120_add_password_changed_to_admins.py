"""Add password_changed column to admins table

Revision ID: 20260120password001
Revises: 57a7fcdd6e8b
Create Date: 2026-01-20 12:00:00.000000+00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '20260120password001'
down_revision = '57a7fcdd6e8b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add password_changed column to admins table"""
    op.add_column('admins', sa.Column('password_changed', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Remove password_changed column from admins table"""
    op.drop_column('admins', 'password_changed')
