"""Opt-in email users column

Revision ID: acb797ccbc06
Revises: e0f35f5bf29c
Create Date: 2018-01-24 12:47:06.418723

"""
from alembic import op
import sqlalchemy as sa

import lifeloopweb.db.models
from sqlalchemy.dialects import mysql
from sqlalchemy import Boolean

# revision identifiers, used by Alembic.
revision = 'acb797ccbc06'
down_revision = 'e0f35f5bf29c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('opt_in_emails', sa.Boolean(), nullable=False))


def downgrade():
    print("Downgrades not supported")
