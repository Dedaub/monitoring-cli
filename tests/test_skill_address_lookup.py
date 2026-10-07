"""The SKILL's address-lookup branch builds app.dedaub.com links by hand.

Nothing executes that link: the agent reads the rule and writes the URL. So the
rule's parts are prose, and only these tests stop them drifting:

- The app routes `/<network>/address/<address>/<tab>` by the platform network
  name, which is `binance` for the chain the CLI and the SQL call `bnb`. A link
  built from the CLI slug alone 404s on BNB.
- The chain question names every chain the CLI targets, so a user on Robinhood
  or Arc can still answer it through "Other".
"""

import re
from pathlib import Path

import pytest

SKILL = (
    Path(__file__).resolve().parents[1]
    / "packages/dedaub-skills/dedaub_skills/skills/dedaub-monitoring/SKILL.md"
)

# The network names the app accepts in a contract-page URL: the platform's
# `Network` enum, minus chains the CLI does not target.
APP_CHAINS = {
    "ethereum",
    "optimism",
    "binance",
    "polygon",
    "base",
    "arbitrum",
    "avalanche",
    "robinhood",
    "arc",
}
# CLI slug -> app network name, where the two differ.
APP_NAME_FOR = {"bnb": "binance"}

LINK = "https://app.dedaub.com/<app-chain>/address/<address>/overview"


@pytest.fixture(scope="module")
def skill() -> str:
    return SKILL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def lookup(skill: str) -> str:
    """The address-lookup block, from its heading to the first numbered step."""
    m = re.search(r"\*\*Address lookup — .*?(?=\n1\. )", skill, re.DOTALL)
    assert m, "SKILL.md lost its Step 0 address-lookup block"
    return m.group(0)


@pytest.fixture(scope="module")
def cli_chains(skill: str) -> list[str]:
    """The network slugs Step 0(b) offers, which are the CLI's target chains."""
    m = re.search(r"\*\*\(b\) Network\*\*.*?Slugs: `([^`]+)`", skill, re.DOTALL)
    assert m, "Step 0(b) no longer lists the network slugs"
    return [s.strip() for s in m.group(1).split(",")]


def test_link_template_is_the_app_route(lookup: str) -> None:
    assert LINK in lookup


def test_bnb_maps_to_the_app_network_name(lookup: str) -> None:
    for cli_slug, app_name in APP_NAME_FOR.items():
        assert f"`{cli_slug}` → `{app_name}`" in lookup


def test_every_cli_chain_has_an_app_page(cli_chains: list[str]) -> None:
    for slug in cli_chains:
        assert APP_NAME_FOR.get(slug, slug) in APP_CHAINS, slug


def test_chain_question_names_every_cli_chain(
    lookup: str, cli_chains: list[str]
) -> None:
    question = lookup.split("**Chain.**", 1)[1].split("**Link.**", 1)[0]
    for slug in cli_chains:
        assert re.search(rf"\b{slug}\b", question), (
            f"the chain question never names {slug}"
        )


def test_branch_is_limited_to_an_address_with_no_direction(lookup: str) -> None:
    # The detour replaces the mode question, so it must not catch an ask that
    # already says what to build ("large transfers from 0x…").
    assert "only for an address with no direction" in lookup
    assert "Any direction at all → not this branch" in lookup
    assert "When unsure, the normal flow wins" in lookup
