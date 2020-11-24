import os
import sys

from alembic import command as alembic_command
from alembic import config as alembic_config
from alembic import script as alembic_script
from alembic import util as alembic_util
import click
import sqlalchemy_utils

from subprocess import Popen, PIPE
import fileinput
import tinys3
from lifeloopweb import config
from lifeloopweb.db import models

CONF = config.CONF
S3_ACCESS_KEY = CONF.get('aws.access.key.id')
S3_SECRET_KEY = CONF.get('aws.secret.access.key')
S3_BUCKET_NAME = 'lifeloopproduction'
CONN = tinys3.Connection(
    S3_ACCESS_KEY,
    S3_SECRET_KEY,
    default_bucket=S3_BUCKET_NAME)

def get_latest_dump_key():
    conn_list = list(CONN.list('backups', S3_BUCKET_NAME))
    last_modified = max(o['last_modified'] for o in conn_list)
    key = [o['key'] for o in conn_list if o['last_modified'] == last_modified]
    return key[0]

def get_dump(key=False):
    key = get_latest_dump_key()
    response = CONN.get(key, S3_BUCKET_NAME)
    if os.path.exists(key):
        print("{} already exists".format(key))
    elif response.status_code == 200:
        new_dump = open(key, 'wb')
        new_dump.write(response.content)
        latest = "backups/lifeloopweb_database_latest.sql"
        print("Pulled production backup: {}".format(key))
        with open(key, 'rb') as backup_file, open(latest, 'wb') as import_file:
            for line in backup_file:
                # This condition will allow the function to be run on both Prod and Dev
                env = CONF.get('environment')
                data = line.replace(b"lifeloopweb_production", str.encode("lifeloopweb_{}".format(env)))
                import_file.write(data)
        print("Created local restore file: {}".format(latest))
    else:
        print("Error getting {} from {}".format(key, S3_BUCKET_NAME))

def main():
    get_dump()

if __name__ == "__main__":
    main()
