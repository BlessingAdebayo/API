SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
# Makefile Reference: https://tech.davis-hansson.com/p/make/

#ifeq ($(origin .RECIPEPREFIX), undefined)
#  $(error This Make does not support .RECIPEPREFIX. Please use GNU Make 4.0 or later)
#endif
# If they fix https://youtrack.jetbrains.com/issue/CPP-26382 I suggest we uncomment the next line: (and refactor our script)
#.RECIPEPREFIX = >

# Make will not look for a file named to the {command-name} on the file system
.PHONY: help env up check lint done build test integration clean loginaws push deploy

# Set prefix for containers
export COMPOSE_PROJECT_NAME=mercor

# Enable buildkit for faster docker builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# use SHOW to inform user of commands
SHOW:=@echo

# use HIDE to run commands invisibly, unless VERBOSE defined
HIDE:=$(if $(VERBOSE),,@)

# Set the check-directory (cdir) to s=cdir or '.':
cdir = '.'
ifneq ($(s),)
	cdir = $$s
endif

# Set ECR variables for pushing docker images:
REGION = eu-west-1
ECR_REGISTRY = 713011802156.dkr.ecr.eu-west-1.amazonaws.com
IMAGE_TAG := $(shell git rev-parse HEAD)
ECR_REPOSITORY = ''

# if MASTER_MERGE != '': (github actions trigger this)
# Get the sha of the last branch merged into the current.
# This enables the master branch to deploy the latest merged image of the development branch.
MASTER_MERGE = 0
ifeq ($(MASTER_MERGE), 1)
	ifeq ($(e), production)
		IMAGE_TAG := $(shell git log -1 --merges --pretty=format:%P | cat | awk '{print $$2}')
	endif
endif

# Set ECR variables
ifeq ($(s),trading_api)
	ifeq ($(e), development)
		ECR_REPOSITORY = trading-api-development
	else ifeq ($(e), staging)
		ECR_REPOSITORY = trading-api-staging
	else ifeq ($(e), production)
		ECR_REPOSITORY = trading-api-production
	endif
else ifeq ($(s), rse)
	ECR_REPOSITORY = rse
endif

ECR_REPOSITORY_URI = $(ECR_REGISTRY)/$(ECR_REPOSITORY)
IMAGE_LINK_LATEST = $(ECR_REGISTRY)/$(ECR_REPOSITORY):latest
IMAGE_LINK = $(ECR_REGISTRY)/$(ECR_REPOSITORY):$(IMAGE_TAG)

BASE_IMAGE_REPOSITORY = public.ecr.aws/x7n9m3l7
BASE_IMAGE_LINK = $(BASE_IMAGE_REPOSITORY)/developer-container-public:latest

# Setup pytest run command:
TEST_PATH = .
ifneq ($(p),)
	TEST_PATH = $(p)
else ifeq ($(MAKECMDGOALS), test)
	TEST_PATH = tests/unit
else ifeq ($(MAKECMDGOALS), integration)
	TEST_PATH = tests/integration
endif
TEST_ARGS =
ifeq ($(v), 1)
	TEST_ARGS = --log-cli-level="ERROR" -s -v
endif
TEST_ARGS_DIST =
ifeq ($(v), 1)
	TEST_ARGS_DIST = --log-cli-level="ERROR" -s -v
else
	TEST_ARGS_DIST = -n auto
endif
PYTEST_RUN_CMD = sh -c 'pipenv run pytest $(TEST_PATH) $(TEST_ARGS)'
PYTEST_RUN_CMD_DIST = sh -c 'pipenv run pytest $(TEST_PATH) $(TEST_ARGS) $(TEST_ARGS_DIST)'

# Export cmd line args:
export VERBOSE
export p
export v
export e

help:
	$(HIDE) target='^[a-z]*:'
	$(HIDE) format='\x1b[1m\1\x1b[0m'
	$(HIDE) grep -F -h "##" $(MAKEFILE_LIST) | grep -v grep | sed -e "s/\($$target\)/$$format/" -e 's/##//' | fold -s

##|----------------------------------------------------------------------------|
##				  Development
##|----------------------------------------------------------------------------|
##
env:##
##Install the Makefile `tooling` python environment, you need this for `make check`. Install service env with `s=service_name`.
	$(SHOW) Running pipenv install
	$(HIDE) cd $(cdir) && pipenv install
##
up:##
##Start service in detached mode using docker-compose, used for local development, specify service with `s=service_name`.
	$(SHOW) Stopping, Rebuilding and starting $$s
	docker-compose stop $$s
	docker-compose up -d --build $$s
##
check:##
##Run static analysis / linters (CHECKS) against our code base. Specify `s=service_name` or it runs against all services.
##Before running this make sure you install the Makefile (tooling) env: `make env`.
	$(SHOW) Running black $(cdir)
	pipenv run black $(cdir) --check
	$(SHOW) Running isort $(cdir)
	pipenv run isort $(cdir) --check --diff
	$(SHOW) Running mypy $(cdir)
	pipenv run mypy --install-types --non-interactive $(cdir) --ignore-missing-imports
##
lint:##
##Run linters & checks against our code base. Specify `s=service_name` or it runs against all services.
##Before running this make sure you install the Makefile (tooling) env: `make env`.
ifeq ($(s), )
	echo "please don't do this.."
	exit 1
endif
	$(SHOW) Running black $(cdir)
	pipenv run black $(cdir)
	$(SHOW) Running isort $(cdir)
	pipenv run isort $(cdir)
	$(SHOW) Running mypy $(cdir)
	pipenv run mypy --install-types --non-interactive $(cdir) --ignore-missing-imports
##
done:##
##Run this before committing to check everything is correct, runs make cmds: `lint`, `test` and `integration`.
ifeq ($(s),)
	$(HIDE) (echo "Specify a valid service with s={service_name}"; exit 1)
else
	$(HIDE) make lint s=$$s
	$(HIDE) make test s=$$s
	$(HIDE) make integration s=$$s
endif
#
build:#
##Build service dockers (for running locally), specify service with `s=service_name`.
ifeq ($(s),)
	$(HIDE) (echo "Specify a valid service with s={service_name}"; exit 1)
else
	docker build . -f $(cdir)/Dockerfile
endif
##
##|----------------------------------------------------------------------------|
##				     Tests
##|----------------------------------------------------------------------------|
##
test:##
##Runs the s={service_name} unit tests. e.g.: `make test s=trading_api`, `make test s=rse`.
##For verbose output run with v=1 (by default its quiet).
##Specify a path to run pytest against with p={path}.
ifeq ($(s),trading_api)
	docker-compose -f base.yml -f .ci/trading-api-docker-compose.yml run --rm trading_api_unit $(PYTEST_RUN_CMD_DIST)
	docker-compose -f base.yml -f .ci/trading-api-docker-compose.yml down
else ifeq ($(s),rse)
	docker-compose -f base.yml -f .ci/rse-docker-compose.yml run --rm rse_unit $(PYTEST_RUN_CMD_DIST)
	docker-compose -f base.yml -f .ci/rse-docker-compose.yml down
else
	$(HIDE) (echo "Specify a valid service with s={service_name}"; exit 1)
endif
##
integration:##
##Run service integration tests, specify service with {s=service_name}.
##For verbose output run with v=1 (by default its quiet).
##Specify a path to run pytest against with p={path}.
ifeq ($(s),trading_api)
	docker-compose -f base.yml -f .ci/trading-api-docker-compose.yml run --rm trading_api_integration $(PYTEST_RUN_CMD)
	docker-compose -f base.yml -f .ci/trading-api-docker-compose.yml down
else ifeq ($(s),rse)
	docker-compose -f base.yml -f .ci/rse-docker-compose.yml run --rm rse_integration $(PYTEST_RUN_CMD)
	docker-compose -f base.yml -f .ci/rse-docker-compose.yml down --volumes
else
	$(HIDE) (echo "Specify a valid service with s={service_name}"; exit 1)
endif
##
clean:##
##Force cleanup of containers used for testing, specify service with {s=service_name}.
ifeq ($(s),trading_api)
	docker-compose -f base.yml -f .ci/trading-api-docker-compose.yml down --remove-orphans
else ifeq ($(s),rse)
	docker-compose -f base.yml -f .ci/rse-docker-compose.yml down --remove-orphans --volumes
else
	$(HIDE) (echo "Specify a valid service with s={service_name}"; exit 1)
endif
##
##|----------------------------------------------------------------------------|
##		   		   Deployment
##|----------------------------------------------------------------------------|
##
loginaws:##
##Log in to AWS ECR.
	$(SHOW) Logging in to aws...
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(ECR_REGISTRY)
##
push:##
##Push a service docker image to ECR, specify service with `s=service_name`, specify environment with `e=environment_name`.
ifeq ($(s),)
	$(HIDE) (echo "Specify a valid service with s={service_name}"; exit 1)
else ifeq ($(e),)
	$(HIDE) (echo "Specify a valid environment with e={environment} and options {development|staging|production}"; exit 1)
else
	docker build . -f $(cdir)/Dockerfile.prod -t $(IMAGE_LINK) -t $(IMAGE_LINK_LATEST)
	docker push $(IMAGE_LINK)
	docker push $(IMAGE_LINK_LATEST)
endif
##
pushbase:##
##Push the developer base image to ECR (runtime image for algorithms).
	aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(BASE_IMAGE_REPOSITORY)
	docker build developer_base_image -f developer_base_image/Dockerfile -t $(BASE_IMAGE_LINK)
	docker push $(BASE_IMAGE_LINK)
##
deploy:##
##Deploy the **current branch** to a service's EC2 nodes, specify service with `s=service_name`, specify environment with `e=environment_name`.
##Before deploying `make push s={service_name} e={environment_name}` the image you want to deploy.
ifeq ($(s),)
	$(HIDE) (echo "Specify a valid service with s={service_name}"; exit 1)
else ifeq ($(e),)
	$(HIDE) (echo "Specify a valid environment with e={environment} and options {development|staging|production}"; exit 1)
else
	pipenv run python ./scripts/deploy.py $(s) $(ECR_REPOSITORY_URI) $(IMAGE_TAG) $(e) $(REGION)
endif
