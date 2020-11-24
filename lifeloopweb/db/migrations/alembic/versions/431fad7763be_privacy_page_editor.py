"""privacy page editor

Revision ID: 431fad7763be
Revises: aa51a9aacd00
Create Date: 2018-04-05 09:28:18.570912

"""
from alembic import op
import sqlalchemy as sa

import lifeloopweb.db.models
from sqlalchemy.dialects import mysql
from sqlalchemy.sql import table, column
from sqlalchemy import String, Binary, Integer

# revision identifiers, used by Alembic.
revision = '431fad7763be'
down_revision = 'c4379beee223'
branch_labels = None
depends_on = None

pages = table(
    'pages',
    column('id', Binary),
    column('title', String),
    column('content', String),
    column('pagetype', Integer),
    column('updated_by', String))

def upgrade():
    op.create_table('pages',
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('id', lifeloopweb.db.models.GUID(length=16), nullable=False),
    sa.Column('title', sa.String(length=60), nullable=False),
    sa.Column('content', sa.String(length=20000), nullable=False),
    sa.Column('pagetype', sa.String(length=16), nullable=False),
    sa.Column('updated_by', sa.String(length=60), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8',
    mysql_collate='utf8_general_ci',
    mysql_engine='InnoDB'
    )

    op.bulk_insert(pages,
    [{'id': lifeloopweb.db.utils.generate_guid().bytes,
        'title': '<p>Test Terms</p>',
        'content': '<p>Terms Content</p>',
        'pagetype': 'terms',
        'updated_by': 'test@email.com'},
        {'id': lifeloopweb.db.utils.generate_guid().bytes,
        'title': '<p>Test Privacy</p>',
        'content': '<p>Privacy Content</p>',
        'pagetype': 'privacy',
        'updated_by': 'test@email.com'}])

def downgrade():
    print("Downgrades not supported")
