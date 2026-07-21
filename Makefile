.PHONY: install test build run-api run-ui seed

install:
	python3 -m venv .venv
	.venv/bin/pip install -e './backend[dev,openai]'
	cd frontend && npm install

test:
	cd backend && ../.venv/bin/pytest && ../.venv/bin/ruff check app tests

build:
	cd frontend && npm run build

run-api:
	.venv/bin/uvicorn app.main:app --app-dir backend --reload

run-ui:
	cd frontend && npm run dev

seed:
	.venv/bin/python scripts/seed_demo.py
