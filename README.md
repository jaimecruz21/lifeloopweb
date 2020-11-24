# lifeloopweb

## Getting Started

### Install Requirements
    * Pyenv
      * If Python 3.6 is already available on your favorite distro, you can skip this step
    * Python 3.6.2
    * Pip
      * Latest version
    * GNU Make
    * Docker 17.05
    * Docker Compose

### Using Pyenv

  Install pyenv-virtualenvwrapper:

    git clone https://github.com/yyuu/pyenv-virtualenvwrapper.git ~/.pyenv/plugins/pyenv-virtualenvwrapper

  Launch pyenv virtualenvwrapper:

    pyenv virtualenvwrapper

### First Install Quickstart

  Builds containers, sets up a venv, brings a compose environment, migrates the database and imports test data. This will take a while, so be patient
    
    make all
  
  Install requirements in your virtual machine

    pip install -r requirements.txt

### Create environment file and source it

    make env

## Populate Environment Variables

  Run this _every time_ the container is built

    . ./scripts/local_env.sh

  This will populate the environment variables to your local env (aka the docker host)
  Errors such as `log level not found` are often due to forgetting this step

## Running tests

  Tests have been separated into unit and functional tests. Currently, the default test environment only triggers the unit tests, as functional tests are very heavy weight and require containers to run. Unit tests can be triggered with:

    tox

  Additionally, you can pass the name of the tox unit environment directly with -e:

    tox -e unit

  Similarly, to run functional tets:

    tox -e functional

## Running a Docker Compose environment

  A docker-compose configuration has been provided, which starts web service and database containers for easier testing.

### Makefile Commands

* `make` - See what other options are available
* `make run` - Start all containers and restore database
* `make database` - Drop the current database and restore it from the most recent prod backup
* `make web_cli` - Go to the web container CLI
* `make db_cli` - Enter the database container CLI, jumping directly into MySQL
* `make reset_web` - Reset the lifeloopweb_web_1 container. You MUST do this anytime you change an environment variable
* `make stop` - Teardown compose containers (You will need to delete the containers for a thorough cleanup)
* `make webpack` - Runs a webpack watcher

### Helpful Bash Aliases
    
  By adding these aliases to your .bash_profile, you can use the dka command to quickly and methodically delete everything associated with your running docker containers.

  _Outside_ of your env:

    alias dka='dkc;dki;dkv'
    alias dkc='docker ps -aq | xargs docker rm -f'
    alias dki='docker images -aq | xargs docker rmi -f'
    alias dkv='docker volume ls -qf dangling=true | xargs docker volume rm'

## Check environment variables are loading

    make shell

  Then:

    In [1]: from lifeloopweb import *

## Making a new migration file

Create a template file and update the head reference:

    lifeloop_db_manage revision -m "Revision File Name"

Run the completed migration:

    lifeloop_db_manage upgrade head

Cleaning up after yourself:

    lifeloop_db_manage drop_tables

## Add a new requirement? Code change?

  Don't forget to rebuild your containers:

    make reset_web

## To View the Build Status

[![CircleCI](https://circleci.com/gh/toneosa/lifeloopweb.svg?style=svg&circle-token=d3c22d4c10e0a9924b9664632884e4e01032639c)](https://circleci.com/gh/toneosa/lifeloopweb)
