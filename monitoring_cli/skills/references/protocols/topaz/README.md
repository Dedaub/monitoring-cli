# Topaz Dex — Compressed Reference Index (BNB Chain only)

**Status:** every topic0/selector computed locally with keccak from the canonical source (`topazdex/topaz-contacts`, `topazdex/topaz-slipstream`) and re-verified on-chain via `publicnode` BSC RPC on 2026-06-05 (33/33 contracts have bytecode; all view-function wiring cross-links; clone bytecode + live `eth_getLogs` confirmed).
**Scope:** Topaz is **BNB's "agentic" ve(3,3) DEX** — a **Velodrome V2 fork** (the `v2` Solidly AMM + ve(3,3) governance) plus an **Aerodrome Slipstream fork** (the `v3` concentrated-liquidity product). It is deployed **only on BNB Smart Chain (chain id 56)**. The other six chains in the monitoring set (Ethereum, Base, Arbitrum, Optimism, Avalanche, Polygon PoS) have **no Topaz deployment** (verified: `eth_getCode` = `0x` for TOPAZ, Voter, CLFactory, NPM on all six).

This protocol is the same codebase as our [`aerodrome/`](../aerodrome/) docs (Aerodrome = Velodrome V2 + Slipstream on Base). If a fact isn't here, the Aerodrome/Velodrome and `uniswap/v3.md` references are byte-compatible for the shared pieces. Topaz-specific deltas are called out explicitly.

## Files (the two "versions" / products)

| File | Product | Contracts |
|------|---------|-----------|
| [`amm.md`](amm.md) | **Topaz v2** (Solidly AMM) **+ the shared ve(3,3) governance** | Pool (volatile+stable), PoolFactory, Router, Voter, VotingEscrow (veTOPAZ), Minter, RewardsDistributor, Gauge (v2), Fees/BribeVotingReward, factories, BonusLock, AirdropDistributor, TOPAZ token |
| [`slipstream.md`](slipstream.md) | **Topaz v3** (concentrated liquidity = Slipstream) | CLFactory, CLPool, CLGauge, NonfungiblePositionManager, SwapRouter, QuoterV2, MixedRouteQuoterV1, fee modules, descriptors |

The **ve(3,3) layer (Voter / VotingEscrow / Minter / RewardsDistributor) is shared** by both products — it lives in [`amm.md`](amm.md) and `slipstream.md` references it. A single `Voter` creates and feeds emissions to **both** v2 `Gauge`s and v3 `CLGauge`s; the `FactoryRegistry` whitelists exactly the two pool factories (verified `poolFactories()` → `[PoolFactory, CLFactory]`).

## One-screen architecture

- **Token:** `TOPAZ` ERC-20 (`symbol()="TOPAZ"`, 18 dec), emitted weekly by `Minter`. Lock TOPAZ → **`veTOPAZ`** (`symbol()="veTOPAZ"`), an **ERC-721 veNFT** (max lock 4 years), not an ERC-20.
- **Epoch = 1 week, flips Thursday 00:00 UTC** (`ProtocolTimeLibrary`: `epochStart = ts - ts % 1 weeks`). Vote window `+1h … +1week-1h`; first hour = distribute window; last hour = whitelisted-NFTs-only.
- **veTOPAZ votes** in `Voter` direct weekly emissions to pool gauges; voters earn that pool's trading fees (`FeesVotingReward`) + third-party `BribeVotingReward` incentives; lockers earn a rebase from `RewardsDistributor`.
- **Pools are EIP-1167 minimal-proxy clones** (both v2 and v3) of an immutable implementation; **gauges differ** (v2 Gauge = full deploy; CLGauge = clone). Nothing is behind an upgradeable (EIP-1967/UUPS) proxy. See each file's *Proxies* section.

## Security & upgradeability

- **Audited by Shieldify Security** — "Topaz DEX Security Review" ([report PDF](https://github.com/shieldify-security/audits-portfolio/blob/main/reports/Topaz-Dex-Security-Review.pdf)), covering ve(3,3) lock/voting, gauge factory, bribe markets, fee distribution, and the Slipstream CL modules. No public exploit/incident known for Topaz as of 2026-06-05 (the "Topaz" hack reports online are an unrelated zkSync DEX, "Merlin").
- **Upgrade path = `FactoryRegistry`, not proxies.** The team states core contracts (Pool, Gauge, VotingEscrow, Voter, Minter, RewardsDistributor, Governors) are **immutable**; the protocol evolves by the admin approving **new factory generations** (pool/gauge/rewards factories) in `FactoryRegistry`, with existing pools/positions **not** force-migrated. So the only "old vs new" axis is **coexisting factory generations** — enumerate via `FactoryRegistry.poolFactories()` (today = `[PoolFactory, CLFactory]`), not via EIP-1967 impl slots.
- **Admin = a single team multisig** `0xf407739e81574a3C9a3195bcb85ee694C94E540c` holding `governor`/`epochGovernor`/`emergencyCouncil`/`VE.team`/`VE.allowedManager`/`Minter.team`. The repo ships immutable `EpochGovernor`/`ProtocolGovernor` contracts, but live those roles currently resolve to the multisig (see [`amm.md`](amm.md) §3.1).

## Cross-chain summary

| Chain | id | Topaz? |
|-------|----|--------|
| **BNB Smart Chain** | **56** | **✓ full deployment (v2 + v3 + ve(3,3))** |
| Ethereum | 1 | ✗ not deployed (`getCode`=0x) |
| Base | 8453 | ✗ not deployed |
| Arbitrum One | 42161 | ✗ not deployed |
| Optimism | 10 | ✗ not deployed |
| Avalanche C-Chain | 43114 | ✗ not deployed |
| Polygon PoS | 137 | ✗ not deployed |

> If Topaz ever multi-chains, the contracts are CREATE2/CREATE-deployed per chain, so **addresses will differ** — re-derive per chain; only topics/selectors are chain-agnostic.

## Top-level detection invariants (see each file for the full list)

1. **One chain only (BNB, 56).** Any "Topaz" address on another chain is unrelated.
2. **v2 AMM `Swap` topic0 `0xb3e27736…` ≠ Uniswap V2 `Swap` `0xd78ad95f…`** (different arg order: `amount0In,amount1In,amount0Out,amount1Out`).
3. **v3 CL events are byte-identical to Uniswap V3** (`Swap 0xc42079f9…`, `Mint 0x7a53080b…`, `Burn 0x0c396cd9…`, `Collect 0x70935338…`). Disambiguate Topaz CL by **pool address provenance** (clone of `CLPool_impl`, created by `CLFactory`), not by topic0.
4. **veTOPAZ is an ERC-721** — locks/votes are keyed by `tokenId`; the escrow emits ERC-721 `Transfer`.
5. **Pools are 45-byte EIP-1167 clones** — a pool's `eth_getCode` is the minimal-proxy stub embedding the impl address, **not** the full pool bytecode. Don't detect pools by full-bytecode hash.

## Quick verification recap (2026-06-05, BSC)

- `TOPAZ.symbol()`=TOPAZ/18dec · `VotingEscrow.token()`→TOPAZ, `.symbol()`=veTOPAZ · `Voter.ve()`→VotingEscrow, `.minter()`→Minter, `.factoryRegistry()`→FactoryRegistry · `PoolFactory.implementation()`→Pool_impl, `allPoolsLength()`=20 · `CLFactory.poolImplementation()`→CLPool_impl, `allPoolsLength()`=50 · `NPM.factory()`→CLFactory, `name()`="Topaz CL Position", `symbol()`="TOPAZ-CL-POS", `WETH9()`→WBNB · `FactoryRegistry.poolFactories()`→[PoolFactory, CLFactory].
- Live `eth_getLogs` confirmed: v2 `Swap`/`Sync`, CL `Swap`/`Mint`/`Burn`/`Collect`, veNFT `Deposit`(enum)/`Supply`/`Merge`/`Split`/`UnlockPermanent`/`Transfer`, `Voted`/`Abstained`, v2+CL gauge `Deposit`/`Withdraw`/`ClaimRewards`.
- Sources: [topazdex/topaz-contacts](https://github.com/topazdex/topaz-contacts) (v2), [topazdex/topaz-slipstream](https://github.com/topazdex/topaz-slipstream) (v3), [topazdex/agent-skill](https://github.com/topazdex/agent-skill) `references/addresses.md`, [docs](https://topazdex.com/docs/contracts) (BscScan-verified).
