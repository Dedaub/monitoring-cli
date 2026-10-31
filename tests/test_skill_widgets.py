"""The skill's widget step and its reference must match the CLI.

The Dedaub backend loads this same SKILL.md as the prompt of its in-app agent,
which has no shell. The widget step must say that it needs a shell, so that
agent skips it. And each command that references/widgets.md names must be a
real command, or an agent that follows it gets "No such command".
"""

import re
from pathlib import Path

import typer.main

from monitoring_cli.cli import app

SKILL_DIR = (
    Path(__file__).resolve().parents[1]
    / "packages/dedaub-skills/dedaub_skills/skills/dedaub-monitoring"
)
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
WIDGETS = (SKILL_DIR / "references/widgets.md").read_text(encoding="utf-8")


def _step() -> str:
    m = re.search(r"### Optional final step — a widget.*?(?=\n---)", SKILL, re.S)
    assert m, "SKILL.md lost its optional widget step"
    return m.group(0)


def test_the_widget_step_needs_a_shell_and_says_to_skip_without_one():
    step = _step()
    assert "in a shell" in step
    assert "not inside the" in step
    assert "skip this step" in step
    assert "references/widgets.md" in step


def test_every_command_in_the_widget_reference_exists():
    commands = set(typer.main.get_command(app).commands)
    named = set(re.findall(r"dedaub-monitoring ([a-z][a-z-]+)", WIDGETS))
    assert named, "widgets.md names no commands"
    assert named <= commands, f"unknown commands: {sorted(named - commands)}"


def test_the_widget_commands_in_the_step_exist():
    commands = set(typer.main.get_command(app).commands)
    named = set(re.findall(r"`([a-z]+-[a-z-]+)`", _step())) - {"dedaub-monitoring"}
    assert named, "the step names no commands"
    assert named <= commands, f"unknown commands: {sorted(named - commands)}"
