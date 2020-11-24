"""Add notification_type 'Response Alert'

Revision ID: e0f35f5bf29c
Revises: 6da65a033f4e
Create Date: 2018-01-17 12:47:29.190050

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Binary, Integer

import lifeloopweb.db.models
import lifeloopweb.db.utils
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'e0f35f5bf29c'
down_revision = '6da65a033f4e'
branch_labels = None
depends_on = None


notification_types = table(
    'notification_types',
    column('id', Binary),
    column('priority', Integer),
    column('description', String))


def upgrade():
    op.bulk_insert(notification_types,
    [
      {'id': lifeloopweb.db.utils.generate_guid().bytes,
        'priority': 900,
        'description': 'Declined Alert'}
    ])
    op.bulk_insert(notification_types,
    [
      {'id': lifeloopweb.db.utils.generate_guid().bytes,
        'priority': 1000,
        'description': 'Accepted Alert'}
    ])


def downgrade():
    print("Downgrades not supported")
