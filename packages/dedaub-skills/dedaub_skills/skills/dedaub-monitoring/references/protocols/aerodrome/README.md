# Aerodrome / Aero — Protocol Reference Index

Monitoring-grade references for **Aerodrome** (Base, 2023-08 → 2026-10) and its successor **Aero** (2026-10-21 →, Base root + Ethereum, Optimism, Arbitrum, Robinhood Chain, Arc leaves). Verified against live RPC and the canonical `aerodrome-finance/*` and `dromos-labs/metadex-*` repos. Re-checked on 2026-10-30: Aero added ([aero.md](aero.md)); legacy status marked in [amm.md](amm.md) and [slipstream.md](slipstream.md).

Dromos Labs merged Aerodrome (Base) and Velodrome (Optimism) into one DEX, **Aero**. Aero is a new set of contracts with a new AERO token. It is not an upgrade of the old contracts. The legacy Velodrome docs are in [`../velodrome/`](../velodrome/README.md).

| File | Generation | Components | Status |
|------|-----------|------------|--------|
| [amm.md](amm.md) | **Aerodrome V2 AMM + ve(3,3)** (Velodrome V2 codebase) | volatile/stable Pools, PoolFactory, Router, Voter, VotingEscrow (veAERO), Minter, legacy AERO `0x940181a9…8631`; also the Velodrome (Optimism) twin addresses | **Legacy.** Gauges killed on 2026-10-21; pools still trade; AERO/veAERO migrate 1:1 to Aero. Base + Optimism. Immutable. |
| [slipstream.md](slipstream.md) | **Aerodrome / Velodrome Slipstream CL** | CLFactory generations, NFPM (`AERO-CL-POS` / `VELO-CL-POS`), SwapRouter | **Legacy.** Same status as amm.md. Base + Optimism. |
| [aero.md](aero.md) | **Aero (MetaDEX03)** | V2 + CL pools, gauges, sAERO escrow, root Voter + LeafVoter, new AERO, xAERO receipt token, Hyperlane messaging, Metarouter, Relay, migration contracts | **Live, current.** Base (root), Ethereum, Optimism, Arbitrum, Robinhood Chain, Arc (+ Ink). Not on BNB, Avalanche, Polygon. Immutable (clones, no proxies). |

## Cross-cutting facts worth knowing before you start

- **Two AERO tokens.** Legacy AERO `0x940181a94A35A4569E4529A3CDfB74e38FD98631` and new AERO `0x3f5bF3EdAc59d650D8fDf9657a71F2f904A3a4Ee`. Both are on Base and both have symbol "AERO". Always filter on the address.
- **Migration.** `AerodromeMigration` `0x22a2F7340a3fB4C7C389D91eE954766B12476721` (Base) converts AERO and veAERO 1:1. VELO / veVELO convert at 0.044 AERO per VELO through `VelodromeMigration` (Optimism) → `VelodromeMigrationEntrypoint` (Base), both at `0x6daE95FE833f190640dB1176F8C8a2e50C6a66c0`. Details in [aero.md §0.1](aero.md).
- **Topic changes between generations.** Aero keeps the V2 `Swap`/`Burn`/`Sync`/`Fees` and the CL `PoolCreated` topic0s, but changes V2 `PoolCreated` (`0xebbbe9dc…`, no `bool stable`), V2 `Mint`, V2 `Claim`, NFPM `IncreaseLiquidity`, the escrow `Deposit`/`Withdraw`/`Supply` and the gauge `Deposit`/`Withdraw`/claim events. A monitor written for amm.md / slipstream.md misses Aero activity.
- **Key on `(chainId, address)`.** Aero reuses some literals across chains with different roles (e.g. `0x7F832356…9751` is the Arc CLFactory, an Ethereum gauge factory and a Robinhood rewards factory).

Each file follows the house layout: Topics → Function signatures → Addresses per chain → Cross-chain summary → Proxies → Detection invariants → Quick-copy constants → Verification & sources (amm.md and slipstream.md use the older compressed layout).
