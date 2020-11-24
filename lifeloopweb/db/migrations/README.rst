Generic single-database configuration.

See http://alembic.readthedocs.org/en/latest/tutorial.html for more usage.


Examples:
=========

- Applying Migration Locally (using sqlite3)

.. code-block:: bash

    $ lifeloop-db-manage --database-connection sqlite:////home/vagrant/dev/lifeloop.db
        upgrade 1284c81cf727

    INFO  [alembic.migration] Context impl SQLiteImpl.                                    
    INFO  [alembic.migration] Will assume non-transactional DDL.                          
    INFO  [alembic.migration] Running upgrade 4358d1b8cc75 -> 1284c81cf727, 


- Checking Current Version Locally After Migration

.. code-block:: bash

    $ lifeloop-db-manage --database-connection sqlite:////home/vagrant/dev/lifeloop.db
        current

    INFO  [alembic.migration] Context impl SQLiteImpl.
    INFO  [alembic.migration] Will assume non-transactional DDL.
    Current revision for sqlite:////home/vagrant/dev/lifeloop.db: 
    4358d1b8cc75 -> 1284c81cf727 (head), 

Having problem with Lifeloop db Migration run

 create new_version migration file and the give the revision number from alembic_version
  example:
      revision = '1f71e54a85e7'
      down_revision = None
  And then goto initial_version.py file then down_version set to new_version's revision number
    example:
        revision = '1817eef6373c'
        down_revision = '1f71e54a85e7'
  then run migration
     example:
         lifeloop-db-manage --config-file lifeloop.conf upgrade head


Workflow for creating a revision
================================

1. Modify lifeloop/db/models.py with your added table/columns.
2. Run ``lifeloop-db-manage ... upgrade head``.
3. Run ``lifeloop-db-manage ... revision --autogenerate``.
