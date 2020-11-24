"""Consolidate repeat notifications

Revision ID: 6da65a033f4e
Revises: 938703e6665d
Create Date: 2018-01-03 21:45:57.961935

"""
from alembic import op
import sqlalchemy as sa

import lifeloopweb.db.models
from sqlalchemy.dialects import mysql
from sqlalchemy.sql import table, column
from sqlalchemy import Binary, Boolean, DateTime

# revision identifiers, used by Alembic.
revision = '6da65a033f4e'
down_revision = '938703e6665d'
branch_labels = None
depends_on = None

notifications = table(
    'notifications',
    column('id', Binary),
    column('notification_type_id', Binary),
    column('user_from_id', Binary),
    column('user_to_id', Binary),
    column('group_id', Binary),
    column('organization_id', DateTime),
    column('acknowledge_only', Boolean),
    column('accepted', DateTime),
    column('declined', DateTime),
    column('acknowledged', DateTime))


def upgrade():
    op.add_column('notifications', sa.Column('blocked_as_spam', sa.Boolean(), nullable=True))
    conn = op.get_bind()
    consolidated_data = []
    columns = ["notification_type_id",
              "user_from_id",
              "user_to_id",
              "group_id",
              "organization_id",
              "acknowledge_only",
              "accepted",
              "declined",
              "acknowledged"]
    columns_query = ",".join(columns)
    query = "select distinct " + columns_query + " from notifications;"
    result = conn.execute(query)

    for row in result:
        row_data = {'id':lifeloopweb.db.utils.generate_guid().bytes}
        for index, data in enumerate(row):
            row_data[columns[index]] = data
        consolidated_data.append(row_data)

    conn.execute(notifications.delete())
    op.bulk_insert(notifications, consolidated_data)

    

def downgrade():
    print("Downgrades not supported")
