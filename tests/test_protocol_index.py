"""INDEX.md is the chain lookup, so an understated row hides a deployment.

The file's own purpose line says it answers "which are on chain X" *before*
anything opens a protocol doc. An agent that trusts a row and stops there never
learns about the chains the row left out.

Six rows were doing exactly that. `morpho` listed five chains while `v1.md`
carries full address tables for all seven — including BNB, whose section
exists to warn that the Ethereum/Base vanity address `0xBBBB…EEFFCb` is a
DECOY there. Skip BNB because the index says Morpho is not on it, and the
warning is never read.

The rule below is deliberately one-directional and conservative. A chain must
appear in the row when the docs carry a section for it that names the chain,
names its id, and contains at least one address. A "not deployed" section
documents an absence and is correctly omitted, so the negative markers are
excluded — that distinction is the whole reason this can be a test rather than
a lint everyone ignores.
"""

import re
from pathlib import Path

import pytest

PROTOCOLS = (
    Path(__file__).resolve().parents[1]
    / "packages/dedaub-skills/dedaub_skills/skills/dedaub-monitoring"
    / "references/protocols"
)
INDEX = PROTOCOLS / "INDEX.md"

# The seven target chains, and how a per-chain heading names each one. Both
# halves must match in the SAME heading: "polygon" alone appears in prose all
# over these files, and a bare "137" matches any number.
CHAIN_HEADING = {
    "ETH": (r"ethereum", r"\b1\b"),
    "Base": (r"\bbase\b", r"8453"),
    "BNB": (r"\bbnb\b|binance smart chain", r"\b56\b"),
    "Avax": (r"avalanche", r"43114"),
    "Arb": (r"arbitrum", r"42161"),
    "OP": (r"optimism", r"\b10\b"),
    "Poly": (r"polygon", r"137"),
}

# A heading that documents an ABSENCE. Its section may still quote the address
# it checked and found empty, so the address test alone is not enough.
ABSENT = re.compile(
    r"not deployed|no [\w -]*deployment|not on |absent|— no |no canonical|"
    r"not an official|not reachable",
    re.IGNORECASE,
)
ADDRESS = re.compile(r"0x[0-9a-fA-F]{40}")
ROW = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|([^|]*)\|([^|]*)\|", re.MULTILINE)


def index_rows() -> dict[str, str]:
    """slug -> the row's chain cell, for every slug with a directory."""
    return {
        slug: chains.strip()
        for slug, _cat, chains in ROW.findall(INDEX.read_text(encoding="utf-8"))
        if (PROTOCOLS / slug).is_dir()
    }


def chains_claimed(cell: str) -> set[str]:
    """The legend's `7` means all seven; otherwise the codes present."""
    if re.search(r"(?<![\w.])7(?![\w.])", cell):
        return set(CHAIN_HEADING)
    return {
        code
        for code in CHAIN_HEADING
        if re.search(rf"(?<![A-Za-z]){code}(?![A-Za-z])", cell)
    }


def sections(text: str):
    """(heading, body) for every markdown heading in a file."""
    heading, body = None, []
    for line in text.splitlines():
        if line.startswith("#"):
            if heading is not None:
                yield heading, "\n".join(body)
            heading, body = line, []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        yield heading, "\n".join(body)


def chains_documented(slug: str) -> set[str]:
    """Chains this protocol's docs give a real, populated address section for."""
    found: set[str] = set()
    for path in sorted((PROTOCOLS / slug).glob("*.md")):
        for heading, body in sections(path.read_text(encoding="utf-8")):
            if ABSENT.search(heading) or not ADDRESS.search(body):
                continue
            low = heading.lower()
            found |= {
                code
                for code, (name, ident) in CHAIN_HEADING.items()
                if re.search(name, low) and re.search(ident, low)
            }
    return found


@pytest.mark.parametrize("slug", sorted(index_rows()))
def test_the_index_row_lists_every_chain_the_docs_document(slug: str) -> None:
    missing = chains_documented(slug) - chains_claimed(index_rows()[slug])
    assert not missing, (
        f"INDEX.md row `{slug}` omits {sorted(missing)}, but "
        f"references/protocols/{slug}/ has a populated address section for "
        f"each. A reader who trusts the row never opens the file."
    )


def test_the_index_covers_every_protocol_directory() -> None:
    """A directory with no row is invisible to the lookup that exists to find it."""
    dirs = {p.name for p in PROTOCOLS.iterdir() if p.is_dir()}
    assert not dirs - set(index_rows())
