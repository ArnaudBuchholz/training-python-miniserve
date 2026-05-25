UV = uv run

.PHONY: install check lint fmt type-check test fix build publish

install:
	uv sync

# Run the full quality pipeline (lint + type-check + tests)
check: lint type-check test

lint:
	$(UV) ruff check src tests

fmt:
	$(UV) ruff format src tests

type-check:
	$(UV) mypy src

test:
	$(UV) pytest

# Auto-fix lint issues then format
fix:
	$(UV) ruff check --fix src tests
	$(UV) ruff format src tests

build:
	uv build

publish:
	uv publish
