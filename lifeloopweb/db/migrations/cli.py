#!/usr/bin/env python
# pylint: disable=unexpected-keyword-arg

import os
import sys

from alembic import command as alembic_command
from alembic import config as alembic_config
from alembic import script as alembic_script
from alembic import util as alembic_util
import click
import sqlalchemy_utils

from lifeloopweb.db import models

HEAD_FILENAME = "head"

# TODO(mdietz): These should all be configurable
ALEMBIC_INI = "alembic.ini"
SCRIPT_LOCATION = "lifeloopweb.db.migrations:alembic"
MIGRATION_LOCATION = "lifeloopweb.db.migrations:alembic_migrations"


# TODO(mdietz): a more efficient create_all script would be lovely
# http://alembic.zzzcomputing.com/en/latest/cookbook.html#building-an-up-to-date-database-from-scratch

@click.group()
def migrate_cli():
    pass


def _dispatch_alembic_cmd(config, cmd, *args, **kwargs):
    try:
        getattr(alembic_command, cmd)(config, *args, **kwargs)
    except alembic_util.CommandError as e:
        alembic_util.err(e)


def _update_head_file(config):
    script = alembic_script.ScriptDirectory.from_config(config)
    with open(_get_head_path(script), 'w+') as f:
        f.write(script.get_current_head())


def _get_head_path(script):
    if len(script.get_heads()) > 1:
        alembic_util.err('Timeline branches unable to generate timeline')

    head_path = os.path.join(script.versions, HEAD_FILENAME)
    return head_path


def _create_db():
    if not sqlalchemy_utils.database_exists(models.engine.url):
        sqlalchemy_utils.create_database(models.engine.url)


def _drop_db():
    if sqlalchemy_utils.database_exists(models.engine.url):
        sqlalchemy_utils.drop_database(models.engine.url)


def test_connection():
    if not models.can_connect():
        print("Couldn't connect to the database. Your engine URL is:")
        print(models.engine.url)
        sys.exit(1)


@migrate_cli.command(help="Creates the database. Must be run before any "
                          "migrations as 'upgrade' itself will not create "
                          "the database")
def create_database():
    _create_db()


def abort_if_false(ctx, _param, value):
    if not value:
        ctx.abort()


@migrate_cli.command(help="Drops the database if it exists")
@click.option('--confirm', is_flag=True, callback=abort_if_false,
              expose_value=False,
              prompt='Are you sure you want to drop the database?')
def drop_database():
    _drop_db()


@migrate_cli.command(help="Shows revision SHA of newest migration file")
@click.pass_context
def latest_version(ctx):
    config = ctx.obj["alembic_config"]
    script = alembic_script.ScriptDirectory.from_config(config)
    with open(_get_head_path(script), 'r') as f:
        click.echo("Latest version: {}".format(f.readlines()[0]))


@migrate_cli.command(help="Shows current revision SHA in the database")
@click.pass_context
@click.option("-u", "--url", help="RFC1738 URL to your database")
def current(ctx, url):
    test_connection()
    config = ctx.obj["alembic_config"]
    if url:
        config.set_main_option("sqlalchemy.url", url)
    _dispatch_alembic_cmd(config, "current")


@migrate_cli.command(help="Robert'); DROP TABLE students;--")
@click.pass_context
@click.option("--yarly", is_flag=True, default=False,
              help="Actually delete the tables. Otherwise, the tables to be "
                   "deleted will be shown")
@click.option("-u", "--url", help="RFC1738 URL to your database")
def drop_tables(ctx, yarly, url):
    test_connection()
    config = ctx.obj["alembic_config"]
    if url:
        config.set_main_option("sqlalchemy.url", url)
    # This finds tables that sqlalchemy doesn't know about
    # from the DeclarativeBase, i.e. alembic_version
    models.Base.metadata.reflect(models.engine)
    if yarly:
        click.echo("Dropping tables:")
    else:
        click.echo("The following tables would be dropped. Please re-run "
                   "with --yarly to apply changes:")
    click.echo(models.engine.table_names())
    models.Base.metadata.drop_all()


@migrate_cli.command(help="Friends don't let friends downgrade")
@click.pass_context
def downgrade(ctx):
    click.echo("Downgrades are not supported. They never really work anyway")
    ctx.exit(1)


# pylint: disable=unused-argument
@migrate_cli.command(help="Upgrades the database to the specified version. "
                          "Pass head as the revision to upgrade to the latest "
                          "version")
@click.pass_context
@click.argument("migration_revision")
@click.option("-u", "--url", help="RFC1738 URL to your database")
@click.option("--delta")
def upgrade(ctx, migration_revision, url, delta):
    # TODO(mdietz): wire up delta
    test_connection()
    config = ctx.obj["alembic_config"]
    if not sqlalchemy_utils.database_exists(models.engine.url):
        alembic_util.err("Cannot continue. The database must be created with "
                         "'create_database' first")
    migration_revision = migration_revision.lower()
    if url:
        config.set_main_option("sqlalchemy.url", url)
    _dispatch_alembic_cmd(config, "upgrade", revision=migration_revision)


@migrate_cli.command(help="Generates a new database migration")
@click.pass_context
@click.option("-m", "--message", help="Message to store with the migration")
@click.option("--autogenerate/--no-autogenerate", is_flag=True, default=True,
              help="Provide a blank the migration from existing schema. "
                   "Defaults to True.")
# TODO(mdietz): Should probably wire this up at some point
@click.option("--sql", help="SQL to generate a migration from."
                            "Don't use for now")
def revision(ctx, message, autogenerate, sql):
    test_connection()
    config = ctx.obj["alembic_config"]
    _dispatch_alembic_cmd(config, "revision", message=message,
                          autogenerate=autogenerate, sql=sql)
    _update_head_file(config)


def main():
    config = alembic_config.Config(
        os.path.join(os.path.dirname(__file__), ALEMBIC_INI)
    )
    config.set_main_option("script_location",
                           SCRIPT_LOCATION)

    # TODO(mdietz): the engine URL should be in a config
    #               rather than in the model
    config.set_main_option("sqlalchemy.url",
                           models.ENGINE_URL)
    migrate_cli(obj={"alembic_config": config})
