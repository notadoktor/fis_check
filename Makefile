.EXPORT_ALL_VARIABLES:
PIPENV_VENV_IN_PROJECT = 1

DOCKER_DB ?= psqlol

pipenv: ## setus up a venv based on the Pipfile
	pipenv install --dev

sync_setup: ## syncs setup.py packages to match Pipfile.lock
	pipenv run pipenv-setup sync --dev

install: pipenv sync_setup ## installs fis_check
	pip install -e .

pipx_install: pipenv sync_setup ## install (static) fis_check with pipx
	pipx install .

clean: ## removes existing venvs, Pipfile.lock, misc temp files
	-rm -rf .venv Pipfile.lock
	-find . -name '*.pyc' -delete -print

clean_install: clean install ## runs make clean install

.PHONY: start
start: ## starts uvicorn in the foreground
	uvicorn fis_check.api:app --reload

.PHONY: reset_db
reset_db:
	-docker rm -f psqlol
	docker run -d --name $(DOCKER_DB) -p 5432:5432 --env-file .env.db postgres:12
	# alembic upgrade head

.PHONY: psql
psql:
	docker exec -it $(DOCKER_DB) bash -ilc 'psql -U $$POSTGRES_USER -d $$POSTGRES_DB'


.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
