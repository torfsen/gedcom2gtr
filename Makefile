.PHONY: format mypy pip-compile pre-commit tests

format:
	ruff format

mypy:
	mypy --non-interactive --install-types -m gedcom2gtr

pip-compile:
	pip-compile --quiet --strip-extras requirements.in
	pip-compile --quiet --strip-extras requirements-lint.in
	pip-compile --quiet --strip-extras requirements-mypy.in
	pip-compile --quiet --strip-extras requirements-tests.in
	pip-compile --quiet --strip-extras requirements-dev.in

pre-commit:
	pre-commit run --all-files

tests:
	pytest -v
