"""Group Organization Add Notification Type

Revision ID: 8caf035d7fea
Revises: aef05d715e7c
Create Date: 2017-09-18 16:17:48.637227

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Binary, Integer

import lifeloopweb.db.models
import lifeloopweb.db.utils
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8caf035d7fea'
down_revision = 'aef05d715e7c'
branch_labels = None
depends_on = None

notification_types = table(
    'notification_types',
    column('id', Binary),
    column('priority', Integer),
    column('description', String))


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.bulk_insert(notification_types,
    [
      {'id': lifeloopweb.db.utils.generate_guid().bytes,
        'priority': 800,
        'description': 'Group Organization Add Request'}
    ])
    # ### end Alembic commands ###


def downgrade():
    print("Downgrades not supported")