"""Guards for the agent-skill distribution manifests under .claude-plugin/.

`plugin.json` and `marketplace.json` tell `npx skills` and `/plugin marketplace
add` exactly where the skill lives, so discovery is explicit instead of a
recursive scan. Those declarations are plain strings in JSON: nothing except
these tests stops them drifting away from the packaged skill directory the next
time files move.
"""

import json
import re
from importlib.resources import as_file, files
from pathlib import Path

import pytest

from monitoring_cli.cli import _SKILL_NAME

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"

# The `category` values Claude Code accepts on a marketplace plugin entry.
_CATEGORIES = {
    "productivity",
    "developer-tools",
    "code-quality",
    "deployment",
    "integrations",
    "lsp",
    "security",
    "other",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def plugin() -> dict:
    return _load(PLUGIN_JSON)


@pytest.fixture(scope="module")
def entry() -> dict:
    plugins = _load(MARKETPLACE_JSON)["plugins"]
    assert len(plugins) == 1, (
        "one plugin entry expected; update these tests if that changes"
    )
    return plugins[0]


def test_names_agree_with_the_cli(plugin, entry):
    assert plugin["name"] == _SKILL_NAME
    assert entry["name"] == _SKILL_NAME


def test_marketplace_entry_is_well_formed(entry):
    # Anything outside the allowed set makes the entry fail schema validation
    # for the directories that crawl this file.
    assert entry["category"] in _CATEGORIES
    # A marketplace-root source: the repo itself is the plugin, so the declared
    # skill paths are the complete set for this entry.
    assert entry["source"] == "./"


def test_both_manifests_declare_the_same_skill_paths(plugin, entry):
    assert plugin["skills"], "plugin.json must declare the skill path explicitly"
    assert plugin["skills"] == entry["skills"]


def test_declared_paths_point_at_the_packaged_skill(plugin):
    """The declared directory must be the one the wheel actually ships.

    `install-skill` reads the skill through importlib.resources; the manifests
    read it through a repo-relative path. This pins the two together, so moving
    the skill without updating the manifests fails here instead of silently
    de-listing the skill.
    """
    with as_file(files("dedaub_skills") / "skills" / _SKILL_NAME) as packaged:
        shipped = {p.relative_to(packaged) for p in packaged.rglob("*") if p.is_file()}

    for declared in plugin["skills"]:
        assert declared.startswith("./"), f"{declared} must be a repo-relative ./ path"
        skill_dir = (REPO_ROOT / declared).resolve()
        assert skill_dir.is_relative_to(REPO_ROOT), f"{declared} escapes the repository"
        assert skill_dir.is_dir(), f"{declared} does not exist"
        assert skill_dir.name == _SKILL_NAME, (
            f"{declared} must end in the skill name so agents install it under that name"
        )

        on_disk = {
            p.relative_to(skill_dir) for p in skill_dir.rglob("*") if p.is_file()
        }
        assert on_disk == shipped, (
            "declared skill directory differs from the packaged one"
        )


def test_declared_skill_carries_matching_frontmatter(plugin):
    for declared in plugin["skills"]:
        text = (REPO_ROOT / declared / "SKILL.md").read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---\n", text, re.S)
        assert m, "SKILL.md needs YAML frontmatter for any agent to load it"
        frontmatter = m.group(1)
        assert re.search(rf"^name:\s*{re.escape(_SKILL_NAME)}\s*$", frontmatter, re.M)
        assert re.search(r"^description:", frontmatter, re.M)


def test_plugin_version_tracks_pyproject(plugin):
    """One version string, two files.

    `version` pins the plugin: users keep a cached copy until it changes, so a
    stale value silently withholds updates. pyproject.toml is the source of
    truth, and /bump-version edits only that file, so pin the two together.
    """
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    expected = re.search(r'^version = "([^"]+)"', pyproject, re.M).group(1)
    assert plugin["version"] == expected, (
        f"bump .claude-plugin/plugin.json to {expected} to match pyproject.toml"
    )
