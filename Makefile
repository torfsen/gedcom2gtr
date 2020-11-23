.PHONY: pre-commit tests

pre-commit:
	pre-commit run --all-files

tests:
	pytest -v
