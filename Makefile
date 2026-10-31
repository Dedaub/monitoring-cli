.PHONY: setup setup-local install install-local login token format lint typecheck test check

REPO := https://github.com/Dedaub/monitoring-cli

# One-shot setup: install the latest CLI, install the agent skill, and log in.
# install-skill (picker) and login (browser) are interactive on their own.
setup: install
	dedaub-monitoring install-skill
	dedaub-monitoring login

# The same, but with the CLI of this working tree (to test a branch).
setup-local: install-local
	dedaub-monitoring install-skill
	dedaub-monitoring login

# Always the latest main from GitHub, never the state of this clone: a clone
# that is behind main installed an old CLI with no widget commands.
# --reinstall makes uv fetch and build again, also when the version is the same.
install:
	uv tool install --force --reinstall "git+$(REPO)"
	dedaub-monitoring --version

# The CLI of this working tree, built again.
install-local:
	uv tool install --force --reinstall .
	dedaub-monitoring --version

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
