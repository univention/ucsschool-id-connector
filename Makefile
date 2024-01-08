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
APP_VERSION := `cat VERSION.txt`

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

lint: ## check style (requires Python interpreter activated from venv)
	isort --check-only src src/queue_management src/schedule_user
	black --config .black --check src src/queue_management src/schedule_user
	flake8 src src/queue_management src/schedule_user

format: ## format source code (requires Python interpreter activated from venv)
	isort src src/schedule_user src/schedule_group src/schedule_school
	black --config .black src src/schedule_user src/schedule_group src/schedule_school

test: ## run tests with the Python interpreter from 'venv'
	python3 -m pytest -l -v src/tests/unittests
