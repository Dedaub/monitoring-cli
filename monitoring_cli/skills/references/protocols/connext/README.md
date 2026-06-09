# Connext / Everclear — reference index

Connext rebranded to **Everclear** and re-architected from a lock-mint Diamond bridge ("Amarok") into an **intent-based clearing layer**. Two distinct generations are documented as separate files.

| File | Generation | Architecture | Status | Chains (of the 7) |
|------|-----------|--------------|--------|--------------------|
| [amarok.md](amarok.md) | **Connext Amarok** (legacy) | EIP-2535 **Diamond** per chain; `xcall`/`execute` (BridgeFacet), router liquidity (RoutersFacet); Nomad/Connext domain IDs | Deployed but **dormant** (xcall/execute activity ~zero since late 2025; flow moved to Everclear) | ETH, Base, BNB, Arbitrum, Optimism, Polygon — **NOT Avalanche** |
| [core.md](core.md) | **Everclear V6** (current) | **Spoke/Hub intent** model; `newIntent` via **FeeAdapterV2**, solver `fillIntent`, Hyperlane settlement; UUPS proxies | **Active** | **All 7** (ETH, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon) |

## Cross-cutting facts

- **Two address namespaces, do not mix.** Amarok uses **Connext/Nomad domain IDs** (ETH = 6648936 = "eth", Base = 1650553709, BNB = 6450786, …, read `domain()`). Everclear uses **Hyperlane domain IDs** (which equal chainId for ETH/Base/BNB/Avax/Arb/OP/Polygon; the **hub** is domain **25327** with no public chainId).
- **Amarok ≠ EIP-1967.** The Diamond's impl slot is `0x0`; track upgrades via the `DiamondCut` event and resolve logic per selector via `facetAddress()`. **Everclear Spoke/Gateway ARE UUPS** (EIP-1967 impl slot set, admin slot empty); FeeAdapterV2 is a **direct (non-proxy)** deployment.
- **Address tells.** Amarok Diamonds have **no shared vanity** and a **different owner Safe per chain**. Everclear's **FeeAdapterV2 (`0xd0185bfb…540e`) is byte-identical on all 7 chains** — the strongest cross-chain anchor; the Spoke/Gateway vanity (`0xa05A3380…`/`0x9ADA72CC…`) holds on 5 of 7 and **diverges on Avalanche and Polygon**.
- **Avalanche split.** Everclear runs a Spoke on Avalanche; **Amarok does not** (no Diamond there despite Avalanche being a registered Connext domain).
- **Hub is off-target.** Everclear's clearing **EverclearHub / HubGateway** (netting, invoices, settlements) live on the Everclear L2 (Hyperlane domain **25327**) — none of its events fire on any of the seven requested chains. Documented in core.md §1.4/§7 for completeness.
- **Shared event topics across files (disambiguate by emitter):** `OwnershipTransferred` `0x8be0079c…`, `Paused` `0x9e87fac8…`, `Unpaused` `0xa45f47fd…` appear in both generations. `ExternalCalldataExecuted` has **different topic0** in Amarok (`0xb1a4ab59…`, args `bool,bytes`) vs Everclear (`0x72c7d97e…`, arg `bytes`).
- **CLEAR / Everclear governance token** (`0x58b9cb81…05E8`) is shared infra: canonical upgradeable token on ETH, OFT on BNB/Arb/OP/Polygon, **absent on Base + Avalanche**. (Detailed in amarok.md §10.)

All topic0s, selectors, addresses and proxy classifications in both files were recomputed locally with keccak256 and existence-/value-checked against live RPC on 2026-06-09; key topics were cross-checked against live `eth_getLogs` and selectors against deployed bytecode.
