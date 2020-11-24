#!/usr/bin/env python

from lifeloopweb.db import models
from flask_bcrypt import Bcrypt

password = input('Enter password to hash:')
hashed_password = Bcrypt().generate_password_hash(password).decode('utf-8')

email = input('Enter email of user whose password to update:')

with models.transaction() as session:
    user_query = session.query(models.User)
    user = user_query.filter_by(email=email).first()
    if user:
        print("User found: {}".format(user.email))
        user.hashed_password = hashed_password
    else:
        print("No user found with email {}".format(email))

print("Updated {}'s hashed password".format(email))
