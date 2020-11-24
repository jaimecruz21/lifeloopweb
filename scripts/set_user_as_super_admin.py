#!/usr/bin/env python

from lifeloopweb.db import models

email = input('Enter email of user to make a super admin:')

with models.transaction() as session:
    user = models.User.get_by_email(email)
    if user:
        print("User found: {}".format(user.full_name_and_email))
        user.super_admin = True
        session.add(user)
        print("Updated {}'s to a super admin".format(user.full_name_and_email))
    else:
        print("No user found with email {}".format(email))
