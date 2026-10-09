.PHONY: setup login token format lint typecheck test check

# One-shot setup: install the CLI (force, via uv), install the agent skill, and
# log in. install-skill (picker) and login (browser) are interactive on their own.
setup:
	uv tool install . --force
	dedaub-monitoring install-skill
	dedaub-monitoring login

# Authenticate the installed CLI via the browser device flow.
login:
	dedaub-monitoring login

# Print the stored refresh token for headless use (CI, containers). Export it as
# DEDAUB_MONITORING_REFRESH_TOKEN there. Treat the value as a password.
token:
	@dedaub-monitoring token

format:
	uv run ruff check --fix monitoring_cli tests
	uv run ruff format monitoring_cli tests

lint:
	uv run ruff check monitoring_cli tests
	uv run ruff format --check monitoring_cli tests

typecheck:
	uv run ty check monitoring_cli

test:
	uv run pytest

# Everything CI runs, in one target.
check: lint typecheck test
