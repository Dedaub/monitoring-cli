# Connext / Everclear — reference index

Connext rebranded to **Everclear** and re-architected from a lock-mint Diamond bridge ("Amarok") into an **intent-based clearing layer**. Three generations are documented as separate files: NXTP v1 (2021 to 2023), Amarok and Everclear.

| File | Generation | Architecture | Status | Chains (of the 8) |
|------|-----------|--------------|--------|--------------------|
| [nxtp.md](nxtp.md) | **Connext NXTP v1** (first generation, plus the older v0 contracts) | One immutable **TransactionManager** per chain; user `prepare` locks funds, router `prepare` locks liquidity, `fulfill` with the user signature pays out; link key `transactionId`; EVM chain ids | **Ended** (last Ethereum `TransactionPrepared` 2023-05-22; owner and router-liquidity activity in 2025) | ETH, Arbitrum, Optimism, Polygon, BNB, Avalanche — **NOT Base, NOT Robinhood** |
| [amarok.md](amarok.md) | **Connext Amarok** (legacy) | EIP-2535 **Diamond** per chain; `xcall`/`execute` (BridgeFacet), router liquidity (RoutersFacet); Nomad/Connext domain IDs | Deployed but **dormant** (xcall/execute activity ~zero since late 2025; flow moved to Everclear) | ETH, Base, BNB, Arbitrum, Optimism, Polygon — **NOT Avalanche, NOT Robinhood** |
| [core.md](core.md) | **Everclear V6** (latest) | **Spoke/Hub intent** model; `newIntent` via **FeeAdapterV2**, solver `fillIntent`, Hyperlane settlement; UUPS proxies | **Sunset announced 2026-05-21**; 0 intent logs on the eight chains in the 2026-09-28 window | **7 of 8** (ETH, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon) — **NOT Robinhood** |

## Cross-cutting facts

- **Three link keys and three id schemes.** NXTP: `transactionId` (topic3), EVM chain ids in `txData`. Amarok: `transferId`, Connext/Nomad domain ids. Everclear: `intentId`, Hyperlane domain ids.
- **Robinhood Chain (4663):** no Connext contract of any generation (`eth_getCode` = `0x` at every literal in the three files, 2026-09-29).
- **One literal, three contracts.** `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` is the NXTP v1 TransactionManager on Ethereum, Optimism and Avalanche and the NXTP v0 TransactionManager on Polygon and BNB (nxtp.md §10).

- **Two address namespaces, do not mix.** Amarok uses **Connext/Nomad domain IDs** (ETH = 6648936 = "eth", Base = 1650553709, BNB = 6450786, …, read `domain()`). Everclear uses **Hyperlane domain IDs** (which equal chainId for ETH/Base/BNB/Avax/Arb/OP/Polygon; the **hub** is domain **25327** with no public chainId).
- **Amarok ≠ EIP-1967.** The Diamond's impl slot is `0x0`; track upgrades via the `DiamondCut` event and resolve logic per selector via `facetAddress()`. **Everclear Spoke/Gateway ARE UUPS** (EIP-1967 impl slot set, admin slot empty); FeeAdapterV2 is a **direct (non-proxy)** deployment.
- **Address tells.** Amarok Diamonds have **no shared vanity** and a **different owner Safe per chain**. Everclear's **FeeAdapterV2 (`0xd0185bfb8107c5b2336bC73cE3fdd9Bfb504540e`) is byte-identical on all 7 deployed chains** — the strongest cross-chain anchor; the Spoke/Gateway vanity (`0xa05A3380889115bf313f1Db9d5f335157Be4D816`/`0x9ADA72CCbAfe94248aFaDE6B604D1bEAacc899A7`) holds on 5 of 7 and **diverges on Avalanche and Polygon**.
- **Avalanche split.** Everclear runs a Spoke on Avalanche; **Amarok does not** (no Diamond there despite Avalanche being a registered Connext domain).
- **Hub is off-target.** Everclear's clearing **EverclearHub / HubGateway** (netting, invoices, settlements) live on the Everclear L2 (Hyperlane domain **25327**) — none of its events fire on any of the eight target chains. Documented in core.md §1.4/§7 for completeness.
- **Shared event topics across files (disambiguate by emitter):** `OwnershipTransferred` `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0`, `Paused` `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752`, `Unpaused` `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` appear in both generations. `ExternalCalldataExecuted` has **different topic0** in Amarok (`0xb1a4ab59facaedd6d3a71da3902e0a1fa5b99750c0e20cd878334378a41cb335`, args `bool,bytes`) vs Everclear (`0x72c7d97e6fac52d20092b101af2183fd0bd04b357a936e82537e8974ea2c0eb7`, arg `bytes`).
- **CLEAR / Everclear governance token** (`0x58b9cb810A68a7f3e1E4f8Cb45D1B9B3c79705E8`) is shared infra: canonical upgradeable token on ETH, OFT on BNB/Arb/OP/Polygon, **absent on Base, Avalanche and Robinhood Chain**. (Detailed in amarok.md §10.)

All topic0s, selectors, addresses and proxy classifications in amarok.md and core.md were recomputed locally with keccak256 and existence-/value-checked against live RPC on 2026-06-09 (re-checked 2026-09-29), and those in nxtp.md on 2026-09-29; key topics were cross-checked against live `eth_getLogs` and selectors against deployed bytecode.
