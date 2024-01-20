all: flake mypy pylint test

flake:
	pipenv run flake

mypy:
	pipenv run mypy

pylint:
	pipenv run pylint

test:
	pipenv run pytest