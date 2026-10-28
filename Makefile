.PHONY: install lint typecheck test check clean

install:
python -m pip install --upgrade pip
pip install -e ".[dev]"

lint:
ruff check .
ruff format --check .

typecheck:
mypy src tests
mypy blueprints/01_structured_web_ingestion/pipeline.py
mypy blueprints/02_hybrid_rag_reranking/pipeline.py

test:
pytest

check: lint typecheck test

clean:
rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
