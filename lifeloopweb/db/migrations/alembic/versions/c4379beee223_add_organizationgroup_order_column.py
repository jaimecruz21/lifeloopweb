"""Add OrganizationGroup.order column

Revision ID: c4379beee223
Revises: aa51a9aacd00
Create Date: 2018-04-06 00:44:49.028529

"""
from alembic import op
import sqlalchemy as sa

import lifeloopweb.db.models
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'c4379beee223'
down_revision = 'aa51a9aacd00'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('organization_groups', sa.Column('order', sa.Integer(), nullable=True))


def downgrade():
    print("Downgrades not supported")
