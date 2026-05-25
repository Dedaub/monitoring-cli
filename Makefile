.PHONY: format typecheck

format:
	uv run ruff check --fix monitoring_cli tests
	uv run ruff format monitoring_cli tests

typecheck:
	uv run ty check monitoring_cli
