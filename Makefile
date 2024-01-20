all: flake mypy pylint

flake:
	pipenv run flake

mypy:
	pipenv run mypy

pylint:
	pipenv run pylint