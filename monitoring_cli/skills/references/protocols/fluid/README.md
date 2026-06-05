# Fluid (Instadapp) — Protocol Reference Index

Monitoring-grade references for Fluid across **Ethereum (1), Base (8453), Arbitrum One (42161), Polygon PoS (137), BNB Smart Chain (56)**. Verified against live RPC + canonical `Instadapp/fluid-contracts-public` (`main`) + `deployments/deployments.md`; core built 2026-05-29, **counts + factory/Lite/periphery completeness re-verified 2026-06-05**.

> **NOT deployed on Optimism (10) or Avalanche (43114).** Re-confirmed 2026-06-05: every Fluid core address (Liquidity, VaultFactory, DexFactory, LendingFactory, resolvers, ReserveProxy) returns empty `eth_getCode` on both, and the repo's `deployments/` contains only `mainnet, arbitrum, base, polygon, bnb, plasma`. Any "Fluid on OP/Avax" claim refers to legacy Instadapp DSA/Avocado infra, not Fluid. (`plasma` exists in-repo but is out of scope here.)

Fluid is **module-based, not version-based** (no linear `v1→v2`). One shared **Liquidity Layer** custodies all funds; the lending/vault/DEX modules are allow-listed "users" that settle through it. One file per module, each following the same section layout:

| File | Module | What it is | Chains | Versioning |
|------|--------|-----------|--------|-----------|
| [liquidity-layer.md](liquidity-layer.md) | **Liquidity Layer (core)** | The single InfiniteProxy that custodies ALL liquidity; every supply/borrow/withdraw/payback settles here as one `LogOperate`. + FLUID token, InfiniteProxy mechanics. **Base file.** | 5 | Continuously-governed proxy; evolves by swapping per-selector modules, never redeploys. |
| [lending.md](lending.md) | **Lending (fTokens)** | ERC-4626 "Lend & Earn" tokens (pure suppliers to Liquidity). | 5 | Not versioned. fTokens = non-upgradeable CREATE3; "new version" = new address. |
| [vaults.md](vaults.md) | **Vault Protocol** | Overcollateralized borrowing; positions are ERC-721 NFTs. **T1** (normal), **T2** (smart collateral), **T3** (smart debt), **T4** (smart col+debt). | **5 (incl. BNB)** | Vault *types* T1–T4 are the "versions"; per-vault modules upgradeable-by-governance. |
| [dex.md](dex.md) | **DEX** | AMM whose liquidity IS the Liquidity Layer. **DEX V1** (poolT1, factory-deployed pools) + **DEX Lite** (next-gen singleton). **No "DEX V2."** | V1: 5 · Lite: **ETH only** | V1 (poolT1) and DEX Lite are the two on-chain generations; `smartLending` (fSL) wraps V1, not a new AMM. |
| [periphery.md](periphery.md) | **Periphery** | FLUID token (per chain), 3 reward systems (RateModel / StakingRewards / MerkleDistributor), resolvers, buyback. | varies | — |

Each file: **Topics** (chain-agnostic `topic0 = keccak256(event sig)`) → **Function signatures** (4-byte selectors) → **Addresses** (network-specific) → **Proxies** → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## Chain × module matrix (live counts, 2026-06-05)

| | ETH (1) | Base (8453) | Arbitrum (42161) | Polygon (137) | BNB (56) | OP (10) | Avax (43114) |
|---|---|---|---|---|---|---|---|
| Liquidity Layer | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| fTokens (`allTokens()`) | 7 | 6 | 9 | 6 | 5 | ✗ | ✗ |
| Vaults (`totalVaults()`) | 170 | 50 | 91 | 29 | 35 | ✗ | ✗ |
| DEX V1 (`totalDexes()`) | 45 | 18 | 21 | 8 | 5 | ✗ | ✗ |
| DEX Lite (singleton) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| FLUID token | native | bridged | bridged | — | bridged | ✗ | ✗ |

New since the 2026-05-29 build: **Arb fPYUSD**, **BNB fETH** (fTokens); **vaults on BNB** (35) corrected from "4 chains" to 5; **DEX Lite** documented (ETH); FLUID bridged-OFT confirmed on Base+BNB.

## Cross-cutting facts worth knowing before you start

- **Watch `LogOperate` on the Liquidity proxy `0x52Aa899454998Be5b000Ad077a46Bbe360F4e497` = the single highest-signal Fluid event.** Every fToken deposit, vault borrow/repay, and DEX liquidity change ultimately settles as one `LogOperate` (topic `0x4d93b232…`). Fluid analogue of "watch the Balancer Vault." `supplyAmount`/`borrowAmount` are signed (`+`=add, `−`=remove); **`user` is the protocol** (fToken/vault/pool), never the end user — correlate by tx hash.
- **Core addresses are deterministic and identical on all 5 chains** (CREATE3/CREATE2): Liquidity `0x52Aa…E497`, VaultFactory `0x324c5Dc1…Bf2d`, DexFactory `0x91716C4E…9085`, LendingFactory `0x54B91A0D…1D03`, LiquidityResolver `0xca13A15d…5C60`. **Exception: DEX Lite singleton (`0xBbcb9144…`) is ETH-only**, and FLUID token / per-instance addresses vary.
- **InfiniteProxy (Liquidity/Vault/DEX cores):** reuses the *standard* EIP-1967 admin/impl slots, but the impl slot holds only an ABI **dummy stub** — real dispatch is per-selector at `_SIG_SLOT_BASE | bytes4(selector)`. **Resolve the live module with `getSigsImplementation(bytes4)` (`0xa5fcc8bc`) — never hardcode a module addr or trust a registry snapshot.** fTokens, the factories, resolvers and RewardsRateModels are **NOT** proxies (plain CREATE3/normal contracts). See [liquidity-layer.md §5](liquidity-layer.md).
- **Topics + selectors are chain-agnostic** (same hash on every chain; only the emitting address changes) — but **arity/type drift across vault types**: `LogUpdateCoreSettings` has 4 topic0s (T1/T2/T3/T4), `LogUpdateOracle` has 2 (T1 1-arg vs smart 2-arg), and DEX `Swap` (V1, `0xdc004dbc…`) ≠ `LogSwap` (Lite, `0xfbce846c…`). Struct-array event args must be hashed with tuple types **expanded**.
- **Three separate reward systems** ([periphery.md](periphery.md)): `LendingRewardsRateModel` (rate-only, no claim event — yield accrues into exchange price), `StakingRewards` (Synthetix-style, `Staked`/`Withdrawn`/`RewardPaid`), `MerkleDistributor` (campaign claims, `LogClaimed`). Don't conflate.
- **Live deployments can lag HEAD source** — when a selector matters, verify against the live contract, not the repo file (e.g. mainnet fWETH lacks the 2-arg `mintNative` in current `main`).

## Verification methodology

- **Topic0 / selectors:** computed locally with keccak-256 from canonical `Instadapp/fluid-contracts-public` (`main`) `events.sol`/interface signatures (struct args expanded to tuples); the keccak helper was validated against known hashes (`Transfer`, `LogOperate`, `operate`) before use. Spot-checked on-chain for the core (`LogOperate` via `eth_getLogs`).
- **Addresses/counts:** `eth_getCode` non-empty + `eth_call` getters (`totalVaults`/`totalDexes`/`allTokens`/`symbol`/`name`) on each chain's publicnode RPC (`{ethereum,base,arbitrum-one,polygon-bor,bsc}-rpc.publicnode.com`), 2026-06-05. OP/Avax negative confirmed by empty `getCode` on all core addresses + repo `deployments/` listing.
- **Source:** [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) (source + `deployments/<chain>/*.json` + `deployments/deployments.md`) · [docs.fluid.io](https://docs.fluid.io) · explorers (Etherscan/BaseScan/Arbiscan/PolygonScan/BscScan).

## Coverage caveats

- **Per-instance addresses are not exhaustively enumerated** — individual vaults (per market), DEX V1 pools, DEX Lite pools, and the full StakingRewards/MerkleDistributor sets are discovered via factory/singleton events (`VaultDeployed`, `LogDexDeployed`, `LogInitialize`, `LogClaimed`) or the resolvers ([periphery.md §5](periphery.md)). The module files give the factories/singletons + the notable instances.
- **`totalAmounts`/`exchangePricesAndConfig` in `LogOperate` are bit-packed** — decode via the Fluid `BigMath`/packing layout or `FluidLiquidityResolver`.
- **DEX Lite events are bit-packed and fully non-indexed** — `LogSwap(swapData, dexVariables)` etc. decode via `libraries/dexLiteSlotsLink.sol`.
