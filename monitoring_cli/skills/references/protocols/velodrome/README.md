# Velodrome Finance — Compressed Reference Index

**Status:** topic0/selectors computed locally with keccak (pycryptodome) from canonical source; addresses pulled from `velodrome-finance/*` `deployment-addresses/` JSON and re-verified on-chain via `eth_call`/`eth_getCode`/`eth_getLogs` vs publicnode/drpc (2026-06).

**What Velodrome is.** Velodrome is the **Solidly ve(3,3) AMM native to Optimism** — the *original* of the codebase that **Aerodrome (Base) is a fork of** (the prompt's "Velodrome is an Aerodrome fork" is backwards: Aerodrome, launched Aug 2023, forked Velodrome V2). Same team (formerly veDAO / "the Velodrome team"), same contracts, different chain + token (VELO vs AERO). The shared AMM/governance event & selector layout is documented (and on-chain verified) in [`aerodrome/amm.md`](../aerodrome/amm.md) and [`aerodrome/slipstream.md`](../aerodrome/slipstream.md); this folder is the Velodrome-specific, multi-chain-complete companion.

## ⚠️ Deployment footprint vs. the requested chain list

The prompt asked for Velodrome on **Ethereum, Base, Binance, Avalanche, Arbitrum, Optimism, Polygon PoS**. The verified reality:

| Requested chain | Velodrome deployed? | Reality |
|---|---|---|
| **Optimism** (10) | ✅ **YES — root/home chain** | Full V2 AMM + Slipstream + ve(3,3) governance + cross-chain root. |
| **Base** (8453) | ⚠️ **Partial** | Sister-protocol **Aerodrome** is the AMM here. Velodrome only deploys the *restricted-reward token bridge* leg on Base (XOP/restricted XERC20), **no Velodrome AMM/pools**. See [`superchain.md`](superchain.md). |
| **Ethereum** (1) | ❌ No AMM | No Velodrome AMM/pools. A **bridged XVELO/VELO representation** may appear on Ethereum for the merger, and aggregators list "Ethereum" among VELO-supported chains — but there is **nothing to monitor as a DEX** there. Full DEX planned under the **"Aero" Velodrome+Aerodrome merger**, Q2 2026 (Base/OP/Ethereum/Circle Arc) — **not yet live** as of 2026-06. |
| **Binance / BNB** (56) | ❌ No | Never deployed. |
| **Avalanche** (43114) | ❌ No | Never deployed. |
| **Arbitrum** (42161) | ❌ No | Not an OP-Stack/Superchain chain; not deployed. |
| **Polygon PoS** (137) | ❌ No | Not deployed. |

**Where Velodrome actually lives = the Optimism Superchain (OP-Stack) only.** Root chain = **Optimism**; leaf chains via the Root/Leaf + Hyperlane cross-chain stack: **Mode, Lisk, Fraxtal, Metal, Soneium, Ink, Unichain, Superseed, Swell, Celo, Bob** (+ restricted-bridge-only on **Base**). Full leaf list, addresses and architecture in [`superchain.md`](superchain.md).

## Versions / files

| File | Scope |
|---|---|
| [`v2.md`](v2.md) | **Velodrome V2** — Solidly volatile+stable AMM + ve(3,3) governance (Voter, VotingEscrow veNFT, Gauge, Minter, RewardsDistributor). Live home = Optimism. The canonical event/selector layout. |
| [`slipstream.md`](slipstream.md) | **Slipstream** — concentrated-liquidity AMM (Uniswap-V3 fork + gauge integration). Two live OP CL deployments + the superchain CL leaf stack. |
| [`superchain.md`](superchain.md) | **Superchain expansion** — Root/Leaf cross-chain architecture, Hyperlane message module, XVELO bridgeable token, leaf-chain deployment addresses (deterministic, shared across all leaf chains). |

**Version history:** V1 (Solidly fork, May 2022 — deprecated, legacy `VELO` token `0x3c8B650257cFb5f272f799F5e2b4e65093a11a05` ✓) → **V2 (June 2023, current)** → Slipstream CL (2024) → Superchain/SuperSwaps cross-chain (2024–2025).

## Key facts for monitoring
- **veToken is an ERC-721 veNFT** (veVELO), keyed by `tokenId`, not an ERC-20 balance.
- AMM `Swap` topic0 `0xb3e27736…` **≠ Uniswap V2** `Swap` (different arg layout). Slipstream core CL events **== Uniswap V3** topic0s (disambiguate by factory/pool address).
- **Leaf contracts are deterministically deployed (CreateX) → identical addresses on every leaf chain.** One address set covers Mode/Lisk/Soneium/Unichain/… (only `leafFeeModule` varies per chain). This is the big compression win — see [`superchain.md`](superchain.md).
- **Two distinct `NotifyReward` and two distinct `Deposit` layouts exist** across the stack — see per-file Detection sections.
- **Product surface = AMM only.** V2 AMM + Slipstream CL + ve(3,3) governance + **Relay** (veNFT autocompounder/autoconverter, addresses in [`v2.md`](v2.md)) + **Sugar** (read-only lens). **No lending, no perps.**
