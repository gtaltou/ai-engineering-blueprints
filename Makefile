.PHONY: install lint format typecheck test check run-bp01

install:
pip install -e ".[dev]"

lint:
ruff check src/ blueprints/ tests/

format:
ruff format src/ blueprints/ tests/

typecheck:
mypy src/ blueprints/

test:
pytest

check: lint typecheck test

run-bp01:
python blueprints/01_structured_web_ingestion/pipeline.py
