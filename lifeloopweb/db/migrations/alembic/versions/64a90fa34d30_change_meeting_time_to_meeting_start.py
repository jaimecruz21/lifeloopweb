"""Change meeting_time to meeting_start

Revision ID: 64a90fa34d30
Revises: caa2785a330b
Create Date: 2017-11-22 11:16:56.498122

"""
from alembic import op
import sqlalchemy as sa

import lifeloopweb.db.models
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '64a90fa34d30'
down_revision = 'caa2785a330b'
branch_labels = None
depends_on = None


def upgrade():
  op.alter_column('zoom_meetings', 'meeting_time', existing_type=sa.DateTime(timezone=False), new_column_name='meeting_start')

def downgrade():
    print("Downgrades not supported")
