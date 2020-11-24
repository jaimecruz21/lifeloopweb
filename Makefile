# It would be snazzy if we either had a tool that could autodiscover possible
# tasks available in the project or be able to generate them as part of the
# initial scaffolding
-include .env

# -e says exit immediately when a command fails
# -o sets pipefail, meaning if it exits with a failing command, the exit code should be of the failing command
# -u fails a bash script immediately if a variable is unset
# -x prints every command before running it
SHELL = /bin/bash -eu -o pipefail
DOCKER := docker
DOCKER_BUILD := $(DOCKER) build -t
DOCKER_TAG := $(DOCKER) tag
DOCKER_PUSH := $(DOCKER) push
ANSIBLE_PLAYBOOK := ansible-playbook -i deploy/hosts deploy/deploy.yml -u ubuntu
DOCKER_RMI := $(DOCKER) rmi
DOCKER_COMPOSE := docker-compose -f
SUDO := sudo
DOCKERFILE := Dockerfile
APP_TARGET := lifeloopweb
CODE_ROOT := lifeloopweb/
TEST_ROOT := tests/
TOPDIR := $(shell git rev-parse --show-toplevel)
DOCKERIZE_WAIT := dockerize -timeout 120s -wait
DB_URL := tcp://database:3306
PRIMARY_GROUP := $(shell id -gn)
PYTHON_EXE := python3
IN_VENV := ${VIRTUAL_ENV}
COMPOSE_CHECK := $(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml ps
ENV_FILE ?= ".env"
GIT_SHA := $(shell git rev-parse HEAD)
GIT_DATE := $(shell git log -1 --format=%cd)
SOURCE_ENV := $(shell set -a; source ${ENV_FILE}; set +a;)
BASENAME := $(shell basename $(CURDIR))
MAJOR_VERSION := 3
MINOR_VERSION := 0
ifndef CIRCLE_BUILD_NUM
	BUILD_VERSION := 0
else
	BUILD_VERSION := ${CIRCLE_BUILD_NUM}
endif

ifndef CIRCLE_SHA1
	REVISION_VERSION := ${GIT_SHA}
else
	REVISION_VERSION := ${CIRCLE_SHA1}
endif
VERSION := ${MAJOR_VERSION}.${MINOR_VERSION}.${BUILD_VERSION}.${REVISION_VERSION}

.PHONY : help
help: # Display help
	@awk -F ':|##' \
		'/^[^\t].+?:.*?##/ {\
			printf "\033[36m%-30s\033[0m %s\n", $$1, $$NF \
		}' $(MAKEFILE_LIST)

.PHONY : all
all : build_venv build run database ## all the things
	@echo "Local dev environment created."

.PHONY : running_database
running_database :
	@if [ "$(shell ${COMPOSE_CHECK} database | egrep -q "database.*Up" && echo 1 || echo 0)" -eq 0 ]; \
	then \
		echo "No running database found. Please start it with 'make run'"; \
	fi

.PHONY : stopped_database
stopped_database :
	@if [ "$(shell ${COMPOSE_CHECK} database | egrep -q "database.*Up" && echo 0 || echo 1)" -eq 0 ]; \
	then \
		echo "Found a running database. Please stop it with 'make stop'"; \
	fi

.PHONY : running_web
running_web :
	@if [ "$(shell ${COMPOSE_CHECK} web | egrep -q "web.*Up" && echo 1 || echo 0)" -eq 0 ]; \
	then \
		echo "No running web found. Please start it with 'make run'"; \
	fi

.PHONY : stopped_web
stopped_web :
	@if [ "$(shell ${COMPOSE_CHECK} web | egrep -q "web.*Up" && echo 0 || echo 1)" -eq 0 ]; \
	then \
		echo "Found a running web container. Please stop it with 'make stop'"; \
	fi

.PHONY : database
database : running_database ## create and restore database from production mysqldump
	if [ ! -d "./backups" ]; then mkdir -p ./backups; fi
	$ python scripts/get_prod_backups.py
	$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml exec web $(DOCKERIZE_WAIT) $(DB_URL) lifeloop_db_manage drop_database
	$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml exec web $(DOCKERIZE_WAIT) $(DB_URL) lifeloop_db_manage create_database
	docker exec -i $(shell ${COMPOSE_CHECK} database | grep 'database_1' | awk '{print $$1}') mysql -uroot lifeloopweb_${ENVIRONMENT} < ./backups/lifeloopweb_database_latest.sql
	$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml exec web $(DOCKERIZE_WAIT) $(DB_URL) lifeloop_db_manage upgrade head

.PHONY : build
build : build_dev build_prod

.PHONY : build_dev
build_dev : version
	@$(SUDO) $(RM) -rf lifeloopweb/static/bower_components; \
	$(SUDO) $(RM) -rf lifeloopweb/static/css; \
	$(SUDO) $(RM) -rf lifeloopweb/build; \
	$(DOCKER_BUILD) $(APP_TARGET) --file $(DOCKERFILE) .

.PHONY : build_db_util
build_db_util : version
	$(DOCKER_BUILD) $(APP_TARGET)_db_util --file $(DOCKERFILE).db_util .

.PHONY : build_prod
build_prod: build_dev
	$(DOCKER_BUILD) $(APP_TARGET)_prod --file $(DOCKERFILE).prod .

.PHONY : build_venv
build_venv: ## build virtual environment
ifndef VIRTUAL_ENV
	@test -d venv || virtualenv -p $(PYTHON_EXE) venv
	@echo "export TOP_DIR=$(TOPDIR)" >> venv/bin/activate
	@set +u; source venv/bin/activate; set -u
endif
	@pip install -U pip && pip install -r requirements.txt -r test-requirements.txt
	@pip install -e .

.PHONY : validate_env
validate_env: ## validate your environment variables key/values
	@$(PYTHON_EXE) scripts/validate_env.py

.PHONY : run
run :  ## docker compose everything
	if [ ! -d "./database_data" ]; then mkdir -p ./database_data; fi
	@echo "environment: ${ENVIRONMENT}"
	@$(SUDO) chown -R $$USER:$(PRIMARY_GROUP) ./database_data; \
	$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml up -d
	@echo "run 'make logs' to connect to docker log output"

.PHONY : up
up : ## shorthand for current environment docker-compose up -d
	$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml up -d

.PHONY : stop
stop : ## teardown compose containers
	@$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml stop; \
	$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml rm -f

.PHONY : reset_web
reset_web: ## teardown and recreate web container
	@$(DOCKER) stop $(BASENAME)_web_1; \
	$(DOCKER) rm $(BASENAME)_web_1; \
	$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml up -d

.PHONY : stopped_web
clean : stopped_web ## Clean venv
	@$(RM) -rf venv
	@find $(CODE_ROOT) -name "*.pyc" -exec $(RM) -rf {} \;
	@find $(TEST_ROOT) -name "*.pyc" -exec $(RM) -rf {} \;

.PHONY : clean_db
clean_db : stopped_database
	@$(SUDO) $(RM) -rf ./database_data; \

.PHONY : clean_images
clean_images :
	@$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml down --rmi all

.PHONY : nuke
nuke : stop clean_db clean clean_images ## stop relevant containers, delete them and images

.PHONY : logs
logs : running_web running_database
	@$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml logs -f

.PHONY : web_cli
web_cli : running_web ## go to database CLI
	@$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml exec web bash

.PHONY : db_cli
db_cli : running_web running_database ## go to database CLI
	@$(DOCKER_COMPOSE) docker-compose.${ENVIRONMENT}.yml exec database mysql -uroot --database lifeloopweb_${ENVIRONMENT}

.PHONY : build_and_deploy_staging ## build and deploy to staging
build_and_deploy_staging: ## deploy to staging environment
	@$(DOCKER_RMI) toneo/lifeloopweb_prod:$$TAG; \
	$(DOCKER_TAG) lifeloopweb_prod:latest toneo/lifeloopweb_prod:$$TAG; \
  $(DOCKER_PUSH) toneo/lifeloopweb_prod:$$TAG; \
	deploy_staging

.PHONY : deploy_staging
deploy_staging: ## deploy to staging environment
	$(ANSIBLE_PLAYBOOK) --extra-vars="hosts=staging env=staging image_name=toneo/lifeloopweb_prod image_tag=$$TAG" -vv

.PHONY : deploy_production
deploy_production: ## deploy to production environment
	$(ANSIBLE_PLAYBOOK) --extra-vars="hosts=production env=production image_name=toneo/lifeloopweb_prod image_tag=$$TAG" -vv

.PHONY : activate
activate: ## activate virtual env
ifndef VIRTUAL_ENV
	@source venv/bin/activate
endif

.PHONY : test
test: ## Run tests
	@tox -r

.PHONY : dev_lifeloop_live
dev_lifeloop_live: ## change domain to dev.lifeloop.live:5000 in .env
	@if grep -R "127\.0\.0\.1.*dev\.lifeloop\.live" /etc/hosts > /dev/null; then echo 'dev.lifeloop.live entry in /etc/hosts already'; else $(SUDO) -- sh -c "echo '127.0.0.1     dev.lifeloop.live' >> /etc/hosts"; fi
	@sed -i -e 's/127.0.0.1:5000/dev.lifeloop.live:5000/g' ./.env; \
  $(SOURCE_ENV)

.PHONY : db_localhost
db_localhost: ## change database to 127.0.0.1:3306 in .env
	@sed -i -e 's/@database/@127.0.0.1:3306/g' ./.env; \
  $(SOURCE_ENV)

.PHONY : db_unset_localhost
db_unset_localhost: ## change 127.0.0.1:3306 to database in .env
	@sed -i -e 's/@127.0.0.1:3306/@database/g' ./.env; \
  $(SOURCE_ENV)

.PHONY : env
env: ## Create .env file from .env.template
	@if [ ! -f $(HOME)/.lifeloopenv ]; then cp .env.template $(HOME)/.lifeloopenv; fi
	@if [ ! -f ${ENV_FILE} ]; then ln -s $(HOME)/.lifeloopenv ${ENV_FILE}; fi

.PHONY : shell
shell :
	@lifeloop_shell ${ENV_FILE}

.PHONY : version
version : ## Update version
	@echo "${VERSION}" > VERSION || true
	@echo "${VERSION}<br/>created on $(GIT_DATE)" > lifeloopweb/templates/version.html || true
	@echo ${VERSION}

.PHONY : webpack
webpack : ## Run webpack watcher
	$(DOCKER) exec -it $(BASENAME)_web_1 yarn watch
