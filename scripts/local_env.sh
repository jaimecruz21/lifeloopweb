#!/bin/bash

make dev_lifeloop_live
make db_localhost
set -a
source .env
set +a
make db_unset_localhost
