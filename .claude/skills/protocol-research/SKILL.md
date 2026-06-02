---
name: protocol-research
description: >
  Research every on-chain deployment of a DeFi/EVM protocol (all contracts + all versions)
  across Ethereum, Base, BNB Smart Chain, Avalanche, Arbitrum, Optimism, and Polygon PoS, then
  write monitoring-grade reference docs (topics, function selectors, addresses, proxies) into
  monitoring_cli/skills/references/protocols/<protocol>/ in the house "v2.md/v3.md" shape — one
  file per protocol version. Combines evm-expert on-chain verification with deep-research
  multi-source fact-checking. REQUIRES a protocol name as the invocation argument
  (e.g. "/protocol-research aave"). Triggers on "research <protocol> deployments",
  "document <protocol> contracts/addresses/events", "add <protocol> to protocol references".
---

# Protocol Deployment Research

You produce **monitoring-grade protocol reference docs** for one protocol at a time. The output
is consumed by the `dedaub-monitoring` alert pipeline, so accuracy is non-negotiable: every
topic0, every 4-byte selector, and every address must be verified, not guessed.

This skill fuses two capabilities you already have:
- **`evm-expert`** — for on-chain verification methodology (RPC, keccak, proxy slots, ABI decoding).
  Read its references (`.claude/skills/evm-expert/references/`) when you need depth, especially
  `proxies.md`, `defi-protocols.md`, `multi-chain.md`, `contract-addresses.md`.
- **`deep-research`** — for multi-source discovery and adversarial fact-checking of claims.

## Input: the protocol name (required)

The protocol name is the **argument passed on invocation** (the text after the skill name, e.g.
`/protocol-research pendle` → protocol = "pendle"). If no protocol name was provided, ask for one
and stop — do not guess. You may also accept an optional hint about scope (e.g.
`/protocol-research aave v4 only`).

Derive a **slug** (lowercase, no spaces, the protocol's common short name): "Uniswap" → `uniswap`,
"PancakeSwap" → `pancakeswap`, "Aave" → `aave`. Match existing directory conventions — list
`monitoring_cli/skills/references/protocols/` first and reuse the slug if a directory already exists.

## Target chains (always all seven unless the user narrows scope)

| Chain | ID | RPC endpoint (verified working) |
|-------|----|--------------------------------|
| Ethereum | 1 | `https://ethereum-rpc.publicnode.com` |
| Base | 8453 | `https://base-rpc.publicnode.com` |
| BNB Smart Chain (Binance) | 56 | `https://bsc-rpc.publicnode.com` |
| Avalanche C-Chain | 43114 | `https://avalanche-c-chain-rpc.publicnode.com` |
| Arbitrum One | 42161 | `https://arbitrum-one-rpc.publicnode.com` |
| Optimism | 10 | `https://optimism-rpc.publicnode.com` |
| Polygon PoS | 137 | `https://polygon-bor-rpc.publicnode.com` |

A protocol need not be on all seven. Your job is to determine **exactly** which chains each contract
of each version is deployed on, and to record absence explicitly (an address that returns `0x` is a
finding, not a gap — note "not deployed here").

## Output location & file-split rule

Write to: `monitoring_cli/skills/references/protocols/<slug>/`

- **One file per protocol version / generation.** Uniswap → `v2.md`, `v3.md`, `v4.md`.
  Aave → `v1.md`…`v4.md`. Name files after the version as the protocol itself names it.
- **Version-less / single-generation protocols → a single file.** Use `core.md` (e.g. `40acres/core.md`,
  `moonwell/core.md`) or `<slug>.md` (e.g. `curve/curve.md`) — match what neighbouring protocols do.
- **Distinct product lines that aren't linear versions get their own descriptively-named file**
  (e.g. `chainlink/{vrf,ccip,automation}.md`, `fluid/{dex,lending,vaults}.md`, `morpho/optimizers.md`).
- **If you produce ≥2 files, also write a `README.md` index** that maps each file to its
  generation/components/status and lists cross-cutting facts (model it on
  `morpho/README.md` and `chainlink/README.md`).
- **Never clobber.** If the directory already exists, read what's there and extend/correct it; don't
  silently overwrite verified content.

## The house shape (target format — match it exactly)

Study these gold-standard files before writing and mirror their structure, density, and tone:
`uniswap/v3.md` (multi-contract immutable), `40acres/core.md` (single file, proxies old&new),
`spark/sparklend.md` (fork + chain-absence handling), `morpho/README.md` (multi-file index).

Each version file follows this section order:

```markdown
# <Protocol> <Version> — Topics, Selectors, Addresses (<chains covered>)

**Status:** verified against live RPC on every listed chain and the canonical `<org/repo>` repos on <DATE>.
**Scope:** <one or two sentences: what contracts/version this file covers, the chains + IDs, and the
note that topics/selectors are chain-agnostic while addresses are network-specific>.

<1–3 short paragraphs of orientation: Is the protocol immutable or upgradeable? How are instances
deployed (CREATE2? factory? per-market)? Any single cross-chain canonical address vs per-chain
addresses? The non-obvious fact a monitoring engineer must know before indexing.>

---

## 0. Contract families & versions          ← OPTIONAL: include only when the file spans several components
<table or list mapping each contract/component to its role and status>

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)
### 1.1 <ContractName> (<what emits these / why you care>)
| topic0 | Event |
|--------|-------|
| `0x<64hex>` | `EventName(type1 indexed, type2, ...)` |
<one subsection per contract that emits events. Note topic0 collisions across contracts and how to
disambiguate by emitter.>

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)
### 2.1 <ContractName>
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x<8hex>` | `funcName(type1,type2,...)` | `(returnType ...)`. brief note: callback? owner-only? view? |
<cover the state-changing functions a monitor would key on, plus the important views. You don't need
every getter, but don't omit any function that emits a tracked event or moves funds.>

## 3. Addresses — Ethereum mainnet (chain ID 1)
All verified via `eth_getCode` returning non-empty bytecode on <RPC> on <DATE>.
| Role | Address | One-liner |
|------|---------|-----------|
| **<ContractName>** | `0x<40hex>` | <one-line description of what it does> |
<...one "## N. Addresses — <Chain> (chain ID X)" section per chain that has a deployment. When a chain
shares identical canonical addresses with Ethereum, say so and show only the divergences + a shared
table, exactly as uniswap/v3.md §5 does. Always state which contracts are NOT deployed on a chain.>

## <N>. Cross-chain summary
<a presence matrix: rows = chains (+ ID), columns = key contracts, cells = address or ✓/—. This is the
at-a-glance "where is what" table. Include vanity-address tells if any.>

## <N+1>. Proxies (old & new)
| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **<name>** | EIP-1967 Transparent / UUPS / Beacon / Diamond / immutable | how to detect (slot read, bytecode size) | who controls upgrades |
<For each upgradeable contract: the EIP-1967 impl/admin slot values per chain, current impl address,
and the `Upgraded(address)` topic to watch for rotations. List old impls if discoverable. Explicitly
list the contracts that are NOT proxies (plain immutable deployments) and how you confirmed it (impl
slot returns 0x).>

## <N+2>. Detection invariants & gotchas
<numbered list of the non-obvious things an indexer must know: signed amounts, which field is the real
user vs the router, topic0 collisions, events that fire once, attribution traps, fee-on-transfer
breakage, chains where a contract looks present but is a decoy, etc. This is the highest-value section
— be specific and concrete.>

## <N+3>. Quick-copy detection constants (bytea-ready for PG)
```
-- ===== Topics (chain-agnostic) =====
TOPIC_<NAME>        = '\x<64hex>'
-- ===== Selectors (chain-agnostic) =====
SEL_<NAME>          = '\x<8hex>'
-- ===== Addresses (network-specific) =====
ETH_<NAME>          = '\x<40hex>'
BASE_<NAME>         = '\x<40hex>'
...
```
<Postgres `\x` bytea literals, lowercase, even digit count: 64 for topic0, 8 for selector, 40 for
address. These are copy-paste-ready for dedaub-monitoring queries.>

## <N+4>. Verification & sources
How constants in this doc were verified (<DATE>):
- **Topic0 / selectors:** recomputed locally as keccak256(signature); cross-checked against live
  `eth_getLogs` on <contract/block evidence>.
- **Addresses:** parsed from <authoritative registry/repo> and existence-checked via `eth_getCode`;
  proxy impls read from the EIP-1967 slot live.
- **Chain coverage:** how you confirmed presence/absence on each of the seven chains.

Authoritative sources:
- [<canonical repo>](url) — source of truth for signatures.
- [<official docs / address registry>](url)
- Explorers: [Etherscan](url) · [Basescan](url) · …
```

The "Deep-research fact-check" subsection (§Verification.1) is added in the final phase below.

---

# Workflow

Work the phases in order. Lead with thoroughness — the user's standing instruction is *"get all
possible deployments, double-check, finalize."* Never silently cap coverage; if you bound something
(skipped a chain, couldn't verify an address), say so in the doc and the final report.

## Phase 0 — Scope & plan (do this yourself, in the main thread)

1. Resolve the protocol name from the argument and compute the slug. List the protocols directory and
   check for an existing `<slug>/`.
2. Quick recon (a few web searches + check `evm-expert/references/defi-protocols.md`): enumerate the
   protocol's **versions/generations and distinct product lines**, and a first guess at which of the
   seven chains each is on. This is what determines your **file-split plan**.
3. Decide the file plan and announce it to the user before the heavy work, e.g.:
   > "Aave has 4 lending-market generations + the GHO/Umbrella periphery. I'll write `v1.md`, `v2.md`,
   > `v3.md`, `v4.md` and a `README.md` index under `protocols/aave/`. Researching all 7 chains now."
4. Create the output directory.

## Phase 1 — Per-version research (dispatch subagents, parallelize)

For **each version/file** in the plan, dispatch a `general-purpose` subagent. Run independent versions
**in parallel** (multiple Agent calls in one message). Give each subagent this prompt (fill the
`<...>`):

---
**Research Agent prompt:**

You are researching one version of a DeFi protocol to produce a monitoring-grade reference file. Apply
the `evm-expert` skill's methodology and references throughout (especially `references/proxies.md`,
`references/defi-protocols.md`, `references/rpc-and-tracing.md`, `references/multi-chain.md`).

**Protocol:** `<name>`  **This file covers:** `<version/component, e.g. "V3 core + periphery">`
**Target chains (verify each):** Ethereum(1), Base(8453), BNB(56), Avalanche(43114), Arbitrum(42161),
Optimism(10), Polygon PoS(137) — RPCs in the table you were given.
**Write your result to:** `monitoring_cli/skills/references/protocols/<slug>/<file>.md` in the exact
house shape you were shown (Status/Scope → Topics → Selectors → Addresses per chain → Cross-chain
summary → Proxies → Invariants → Quick-copy constants → Verification & sources).

Do the following and **double-check every constant**:

1. **Discover contracts.** Find the canonical GitHub org/repos and official docs / address registry for
   this version. Enumerate **every** contract: core + periphery + factories + routers + helpers +
   token/governance pieces relevant to monitoring. Don't stop at the obvious two.
2. **Signatures → topic0 / selectors (chain-agnostic).** For every event, compute
   `topic0 = keccak256("EventName(types)")`. For every function, compute the 4-byte selector
   `keccak256("name(types)")[0:4]`. Use canonical signatures from source (no param names, no spaces;
   tuples as `(type,type)`). Compute locally — see the keccak recipe in the Verification Toolbox. Then
   **cross-check** a sample against live `eth_getLogs` (topic0 appears in real logs) and against
   4byte.directory / Etherscan's "Event/Write" tabs. Flag any signature you could not confirm.
3. **Addresses per chain.** For each of the seven chains, find the canonical deployment address of every
   contract (from the address registry/repo/docs), then **verify on-chain** with `eth_getCode` (non-empty
   = present; `0x` = NOT deployed — record that explicitly). Note when chains share identical canonical
   addresses (deterministic CREATE2) vs diverge.
4. **Proxies.** For each contract, read the EIP-1967 implementation slot
   (`0x360894…382bbc`) and admin slot (`0xb53127…5d6103`) via `eth_getStorageAt`. Classify the pattern
   (Transparent / UUPS / Beacon / Diamond / immutable). Record current impl per chain and the
   `Upgraded(address)` topic to watch. Confirm "not a proxy" by an empty impl slot. Capture old impls if
   the `Upgraded` history is easy to read.
5. **Write the file** in the house shape. Include the Quick-copy `\x` bytea block (lowercase; 64 hex for
   topic0, 8 for selectors, 40 for addresses). Fill "Verification & sources" with exactly how you
   verified (cite block/contract evidence and link the canonical repo + registry + explorers).

**Coverage rules:** enumerate ALL contracts and ALL seven chains — do not sample or truncate. If you
cannot verify something, write it down as unverified rather than omitting it. Return a short summary of:
file written, # contracts, # topics, # selectors, chains present, and anything you could not confirm.

---

While subagents run, you may read the existing gold-standard files so you can review the drafts against
them.

## Phase 2 — Review & assemble

When subagents finish, read each produced file and check it against the house shape and the
gold-standard examples:
- Every topic0 is 64 hex; every selector 8 hex; every address 40 hex; all lowercase in the `\x` block.
- Topics/selectors are presented as chain-agnostic; addresses are per-chain with absence noted.
- Proxies section distinguishes upgradeable vs immutable and gives slot evidence.
- Spot-check a few constants yourself with the Verification Toolbox (recompute one topic0, re-run one
  `eth_getCode`). Fix any drift directly with Edit.
- If ≥2 files, write/refresh `README.md` (index table + cross-cutting facts), modeled on
  `morpho/README.md`.

## Phase 3 — Final deep-research fact-check (the "/deep-research at the very end" pass)

Now invoke the **`deep-research`** skill over the finished file(s) to adversarially verify and to catch
anything missed. Frame the research question concretely, e.g.:

> "Verify the completeness and accuracy of these <protocol> deployment references. (1) Are there
> additional <protocol> contracts or **versions** deployed on Ethereum, Base, BNB, Avalanche, Arbitrum,
> Optimism, or Polygon PoS that are missing? (2) Are any listed addresses wrong, deprecated, or actually
> a different contract? (3) Are launch dates / immutability / proxy-admin claims correct? Cross-check the
> official docs, the canonical GitHub repos, the address registry, and block explorers."

Feed the deep-research agent the list of contracts/addresses/claims you recorded. For every correction
it surfaces, **re-verify on-chain yourself** (eth_getCode / slot read / recompute topic0) before editing
— deep-research findings are leads, not gospel.

Then append a fact-check subsection to each file's Verification section:

```markdown
### <N+4>.1 Deep-research fact-check (<DATE>) — <one-line verdict>

<K> non-obvious claims were cross-checked against <sources>. Verdicts:
1. **<claim>** — ✅ confirmed / ⚠️ corrected (<what changed>) / ❌ refuted.
...
**Net corrections folded in:** <summary of edits made to the doc>, or "none — all claims confirmed."
```

Fold every confirmed correction into the body of the doc (don't leave them only in the fact-check log).

## Phase 4 — Report to the user

Summarize: files written (with paths), versions/components covered, per-chain presence, total
topics/selectors/addresses recorded, and any explicit gaps or unverified items. Note that the docs are
ready for the `dedaub-monitoring` pipeline.

---

# Verification Toolbox (tested in this environment)

**keccak256 (topic0 / selector) — pure, no project-venv conflicts:**
```bash
uv run --isolated --no-project --with pycryptodome python - <<'PY'
from Crypto.Hash import keccak
def k(sig):
    h = keccak.new(digest_bits=256); h.update(sig.encode()); return h.hexdigest()
sigs = [
    "Transfer(address,address,uint256)",            # event  -> topic0 (full 64 hex)
    "swap(address,bool,int256,uint160,bytes)",       # function -> selector (first 8 hex)
]
for s in sigs:
    d = k(s)
    print(f"{s}\n  topic0   0x{d}\n  selector 0x{d[:8]}")
PY
```
Canonical-signature rules: no parameter names, no spaces, `uint`/`int` → `uint256`/`int256`, tuples/structs
as `(type,type,...)`, dynamic arrays `type[]`. `indexed` does NOT change the hash (drop it for hashing;
keep it in the human-readable event row).

**RPC via curl (all seven endpoints accept this shape):**
```bash
RPC=https://ethereum-rpc.publicnode.com
# presence: non-empty result = contract deployed; "0x" = not deployed
curl -s -X POST $RPC -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getCode","params":["0x<addr>","latest"]}'
# EIP-1967 implementation slot (proxy impl address lives in the low 20 bytes):
curl -s -X POST $RPC -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getStorageAt","params":["0x<proxy>","0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc","latest"]}'
# EIP-1967 admin slot:
#   0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103
# confirm an event topic0 actually occurs (proves the signature) — narrow the block range:
curl -s -X POST $RPC -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getLogs","params":[{"address":"0x<contract>","topics":["0x<topic0>"],"fromBlock":"0x<hex>","toBlock":"0x<hex>"}]}'
# read a view (e.g. factory.owner(), pool.token0()) to confirm wiring:
curl -s -X POST $RPC -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x<addr>","data":"0x<selector>"},"latest"]}'
```
EIP-1967 slots (memorize): impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`,
admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`,
beacon `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50`.

**Address registries worth checking first** (saves time vs scraping explorers): the protocol's own
`@org/sdk` address files (e.g. Morpho's `@morpho-org/blue-sdk addresses.ts`, Spark's
`spark-address-registry`), the deploy JSONs in the canonical repo, and the official docs' "Deployments"
page. Always existence-check what they claim with `eth_getCode` — registries drift.

# Quality bar (the user's standing mandate)

- **All deployments.** Every contract of every version on all seven chains. Absence is a recorded
  finding (`0x` from eth_getCode), never an omission.
- **Verified, not guessed.** Recompute every topic0/selector; existence-check every address; read every
  proxy slot. A constant you can't verify is labeled unverified in the doc.
- **No silent caps.** If you skip or sample anything, log it in the doc and the final report.
- **Finalize.** End with the deep-research pass and fold corrections into the docs before reporting done.
