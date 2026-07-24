# GMX — Protocol Reference Index

Monitoring-grade references for GMX across the target chains **Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon PoS (137)**. Verified on-chain 2026-06.

GMX is a perpetuals + spot DEX with two generations, each its own codebase. **Both generations are deployed only on Arbitrum One (42161) and Avalanche C-Chain (43114)** — `eth_getCode` returns `0x` on the other five target chains. One file per generation:

| File | Generation | Model | Chains (of 7) | Key contracts |
|------|-----------|-------|---------------|---------------|
| [v1.md](v1.md) | **V1** (officially sunset; contracts persist) | `Vault` + `GLP` shared-liquidity pool; typed events | Arbitrum, Avalanche | `Vault`, `Router`, `PositionRouter`, `OrderBook`, `GlpManager` |
| [v2.md](v2.md) | **V2** (current) | Isolated synthetic markets (`GM` pools); central `DataStore` + `EventEmitter` | Arbitrum, Avalanche | `EventEmitter`, `DataStore`, `ExchangeRouter`, `OrderHandler`, `Reader` |

Each file follows the house shape: **Topics** → **Function signatures** → **Addresses** (per-chain, absence recorded) → **Proxies** → **Detection invariants & gotchas** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **⚠️ GMX V2 emits NO typed events — everything flows through one `EventEmitter`.** It emits three generic events; the real action is the indexed `keccak256(eventName)` in `topics[1]`:
  - `EventLog1` topic0 = `0x137a44067c8961cd7e1d876f4754a5a3a75989b4552f1843fc69c3b372def160`
  - `EventLog2` topic0 = `0x468a25a7ba624ceea6e540ad6f49171b52495b648417ae91bca21676d8a24dc5`
  - `EventLog`  topic0 = `0x7e3bde2ba7aca4a8499608ca57f3b0c1c1c93ace63ffd3741a9fab204146fc9a`

  **Monitoring V2 = subscribe to the `EventEmitter` address, filter `topic0 ∈ {EventLog1, EventLog2}`, then discriminate on `topics[1] = keccak256(eventName)`.** Key eventName hashes (full table in [v2.md](v2.md)): `PositionIncrease` `0xf94196cc…`, `PositionDecrease` `0x07d51b51…`, `OrderExecuted` `0x680f10f0…`. The payload is an `EventUtils.EventLogData` tuple — decode by key, not by fixed offsets.
- **V1 is the opposite — typed events on the `Vault`** (`IncreasePosition`, `DecreasePosition`, `LiquidatePosition`, `Swap` `0x0874b2d5…`, …) and on `PositionRouter`/`OrderBook`. V1 Vault events index *nothing* — filter by `(address, topic0)`. PositionRouter/OrderBook index only `account`.
- **Both generations: Arbitrum + Avalanche only.** Not on Ethereum/Base/BNB/Optimism/Polygon. V1 is officially sunset (kept for historical indexing); V2 is the active protocol.
- **Cross-chain address-collision trap:** several GMX addresses carry *unrelated* bytecode at the same address on the other chain (and across V1/V2) — and they revert on GMX view calls. **Always confirm a GMX contract by a successful GMX view call, never by code presence alone, and key by `(chain_id, role)`.**
- **Reward-tracker role reuse (V1):** some `RewardTracker` addresses are reused across the two chains at *different* roles (e.g. `0xd2D1…728F` = feeGmxTracker on Arbitrum but feeGlpTracker on Avalanche) — attribute by `(chainId, role)`.
- **All contracts are immutable** (EIP-1967 impl slot `0x0`) in both V1 and V2. The "upgrade" path is governance redeploying + rewiring (V1: Timelock/gov; V2: roles in `RoleStore`/`DataStore`), not proxy upgrades.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` (`cast keccak`) from canonical `gmx-io/gmx-contracts` (V1) and `gmx-io/gmx-synthetics` (V2) sources; the V1 `Swap` topic0 and the V2 `EventLog1`/`EventLog2` topic0s + key eventName hashes were cross-checked against live `eth_getLogs` on both Arbitrum and Avalanche `EventEmitter`/`Vault`.
- **Addresses:** every contract `eth_getCode`-verified present on Arbitrum + Avalanche and confirmed `0x` (absent) on the other five; core wiring confirmed via view calls (V1 `Vault.router()`/`priceFeed()`/`usdg()` round-trips; V2 EventEmitter live emissions).
- **Coverage caveats:** the V2 keyless `EventLog` topic0 and several low-frequency eventName hashes (`PositionLiquidated`, `OrderFrozen`, `MarketCreated`, `*Cancelled`, `Shift*`, `GlvDepositCreated`) are computed from source but not observed live in the sampled window — flagged in [v2.md](v2.md). V1 `Reader`/`OrderBookReader` helpers and `VaultUtils` were not enumerated (not load-bearing for event/selector detection).

### Independent fact-check (2026-06)
Both files passed an adversarial multi-source cross-check (GMX docs, `gmx-io` repos `deployments/`, explorers, live RPC). **Every submitted claim was confirmed** — addresses, the EventEmitter architecture, the EventLog topic0s, the ExchangeRouter-rotation/immutability model, and the Arbitrum+Avalanche-only coverage. Only additions (no corrections): the V2 **Config** + **Timelock** governance contracts (both chains) and the Arbitrum **GlvReader** address were folded into [v2.md](v2.md), each on-chain-verified. V1 confirmed sunset-but-live.
