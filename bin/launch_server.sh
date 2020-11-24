#!/bin/sh
FLAVOR=$1
BINARY=lifeloop_${FLAVOR}_server
lifeloop_db_manage upgrade head && $BINARY
