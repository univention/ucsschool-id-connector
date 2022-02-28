.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except ImportError:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"


help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr src/build/
	rm -fr src/dist/
	rm -fr src/.eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f src/.coverage
	rm -fr src/htmlcov/
	rm -fr src/.pytest_cache

setup_devel_env: ## setup development environment (virtualenv)
	@if [ -d venv ]; then \
		echo "Directory 'venv' exists."; \
	else \
		python3.8 -m venv venv && \
		. venv/bin/activate && \
		python3 -m pip install -U pip && \
		python3 -m pip install -r src/requirements.txt -r src/requirements-dev.txt && \
		python3 -m pip list --editable && \
		pre-commit install && \
		echo "==> Run '. venv/bin/activate' to activate virtual env."; \
		echo "==> Run 'pre-commit run -a' to execute pre-commit hooks manually."; \
	fi

lint: ## check style (requires Python interpreter activated from venv)
	isort --check-only src src/queue_management src/schedule_user
	black --config .black --check src src/queue_management src/schedule_user
	flake8 src src/queue_management src/schedule_user

format: ## format source code (requires Python interpreter activated from venv)
	isort src src/queue_management src/schedule_user
	black --config .black src src/queue_management src/schedule_user

test: ## run tests with the Python interpreter from 'venv'
	python3 -m pytest -l -v src/tests/unittests

src/.coverage: src/*.json src/*.py src/*/*.py
	rm -fv src/tests/integration_tests/auth-school-mapping.json
	cd src && coverage run --source tests,ucsschool_id_connector -m pytest || true
	cd src && coverage report -m

coverage: src/.coverage ## check code coverage with the Python interpreter from 'venv'

coverage-html: src/.coverage ## generate HTML coverage report
	cd src && coverage html
	$(BROWSER) src/htmlcov/index.html

install: clean setup_devel_env ## install the package to the active Python's site-packages
	cd src && python3 -m pip install -e .
	python3 -m pip list --editable
	pre-commit install

build-docker-img: ## build docker image locally quickly
	./build_docker_image -q

build-docker-img-on-knut: clean lint ## copy source to docker.knut, build and push docker image
	rsync -av --delete --exclude-from=.gitignore --exclude .git ./ docker.knut.univention.de:git/ucsschool-id-connector/
	git rev-parse --short HEAD > .last_git_commit
	scp .last_git_commit docker.knut.univention.de:git/ucsschool-id-connector/
	ssh docker.knut.univention.de "cd ~/git/ucsschool-id-connector && ./build_docker_image --release --push"
