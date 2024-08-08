# Mercor

Mono-repository for the Mercor project.

#### Services

- mercor_website
- mercor_smart_contracts
- trading_api
- rse `(runnable secure environment)`
- infra `(infra as code: deploy infra from the cli)`

## Development {trading_api, rse}

All development is done using docker & docker-compose (locally).

> Note: If `docker-compose` complains about an unsupported compose file
> version, make sure you have the current stable release installed by following
> the instructions [here][1].

Use `make` to view the available commands:
```

|------------------------------------------------------------------------|
			Help
|------------------------------------------------------------------------|
help:  Show this help.

|------------------------------------------------------------------------|
			Development
|------------------------------------------------------------------------|
env:   Install the Makefile `tooling` python environment, you need this for `make check`. Install service env with `s=service_name`
up:  Start service in detached mode using docker-compose, used for local development, specify service with `s=service_name`
check:   Run static analysis / linters (CHECKS) against our code base. Specify `s=service_name` or it runs against all services
		 Before running this make sure you install the Makefile (tooling) env: `make env`
lint:   Run linters & checks against our code base. Specify `s=service_name` or it runs against all services
	 Before running this make sure you install the Makefile (tooling) env: `make env`
build:  Build service dockers (for running locally), specify service with `s=service_name`

|------------------------------------------------------------------------|
			Tests
|------------------------------------------------------------------------|
test:  Runs the s={service_name} unit tests. e.g.: `make test s=trading_api`, `make test s=rse`
integration:  Run service integration tests, specify service with `s=service_name`

|------------------------------------------------------------------------|
			Deployment
|------------------------------------------------------------------------|
loginaws:   Login to AWS ECR
push:  Push a service docker image to the ECR, specify service with `s=service_name`
deploy:  Deploy the **current branch** to a service's EC2 nodes, specify service with `s=service_name`, specify environment with `e=environment_name`
		 Before deploying `make push s={service_name}` the image you want to deploy
```

Run a specific component:
``` sh
make up s=trading_api
```

### Service uris

| Component                    | Address                                                                |
| -----------------            | -------------------------------------------------------------------    |
| TradingAPI FastAPI           | [trading_api.localhost/](trading_api.localhost/)                       |
| TradingAPI FastAPI Docs      | [trading_api.localhost/docs](trading_api.localhost/docs)               |
| Traefik Dashboard            | [traefik.localhost:8080/dashboard/](traefik.localhost:8080/dashboard/) |
| Mercor Website               | [localhost:8000](localhost:8000)                                       |

### Testing

To run the tests use the `make test` or `make integration` command:

``` sh
make test s=trading_api
make integration s=trading_api
```

Recommended is to also setup unit-tests using a local python env in your IDE of choice. 
Integration tests however require other docker containers and should be run with the `make` command. 


### Local Environment

To setup a local pipenv environment for the trading API / rse you need python 3.9 on
your machine and pipenv installed, as well as the python 3.9 development
binaries (on ubuntu: apt package `python3.9-dev`).

For ubuntu (first install python3.9):

``` sh
sudo apt install python3.9-dev
```

Then install the pipenv environment of the service of choise using the Makefile:
```sh
make env  # install makefile env
make env s=trading_api # install trading_api env
make env s=rse # install rse env
pipenv shell # Activate it using pipenv shell:
```


## Mercor Website

To setup a local copy of the Mercor website make sure you have the mercor_website component running and run:

``` sh
docker-compose run mercor_website sh setup.sh
```
This command will install local dependencies, run migrations, create a superuser and add tokens to the DB. The default username and password is 'admin'.
The tickers of the algorithms can be frequently updated with the command:
``` sh
python3 manage.py update_algorithm_tickers
```
To updates sparklines run:
``` sh
python3 manage.py update_sparklines
```

