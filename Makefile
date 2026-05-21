.PHONY: format pip-compile pre-commit tests

format:
	ruff format

pip-compile:
	pip-compile --quiet --strip-extras requirements.in
	pip-compile --quiet --strip-extras requirements-dev.in

pre-commit:
	pre-commit run --all-files

tests:
	pytest -v
