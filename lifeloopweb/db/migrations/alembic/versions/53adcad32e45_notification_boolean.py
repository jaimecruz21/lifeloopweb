"""Notification boolean

Revision ID: 53adcad32e45
Revises: 691e6ed74b18
Create Date: 2017-10-19 12:45:27.061973

"""
from alembic import op
import sqlalchemy as sa

import lifeloopweb.db.models
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '53adcad32e45'
down_revision = '691e6ed74b18'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('notifications_on', sa.Boolean(), nullable=False, server_default="1"))


def downgrade():
    print("Downgrades not supported")
