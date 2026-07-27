.PHONY: install install-dev run test lint fmt check backup

install:
	python3 -m pip install -r requirements.txt

install-dev:
	python3 -m pip install -r requirements-dev.txt

run:
	python3 main.py

test:
	python3 -m pytest

lint:
	python3 -m ruff check .

fmt:
	python3 -m ruff check . --fix

check: lint test

backup:
	python3 scripts/backup_db.py
