# Fraxswap — Protocol Reference Index

Monitoring-grade references for Fraxswap (Frax Finance's TWAMM-AMM) across **Ethereum (1), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137)**. Verified on-chain 2026-06.

**Not on Base (8453)** — `eth_getCode = 0x` confirmed. Also not on the other target chains.

| File | Version | Status | Key contracts |
|------|---------|--------|---------------|
| [v2.md](v2.md) | **V2** (current) | Active — per-pool configurable fees, full TWAMM | `FraxswapFactory` (per-chain), `FraxswapRouter`, `FraxswapRouterMultihop` (ETH only) |
| [v1.md](v1.md) | **V1** (deprecated) | Contracts live but no new pairs; fixed 1% fee | See [v1.md](v1.md) for factory addresses |

Each file follows the house shape: **Topics** → **Function signatures** → **Addresses** (per-chain) → **Proxies** → **Detection invariants & gotchas** → **Quick-copy constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Fraxswap = Uniswap V2 + TWAMM.** The standard AMM events (`Swap`, `Mint`, `Burn`, `Sync`, `PairCreated`) have **identical topic0s to Uniswap V2**. Use the TWAMM-specific events to positively identify Fraxswap pairs.
- **TWAMM discriminator events** (Fraxswap-only):
  - `LongTermSwap0To1` = `0x9971294258…` — user placed a DCA order selling token0
  - `LongTermSwap1To0` = `0xe1ce0726…` — user placed a DCA order selling token1
  - `VirtualOrderExecution` = `0x793ee8b0…` — TWAMM settled accumulated virtual swaps
  - `CancelLongTermOrder` = `0x3c5d5e09…` — order cancelled
  - `WithdrawProceedsFromLongTermOrder` = `0x43168622…` — proceeds claimed
- **TWAMM virtual swaps do NOT emit `Swap` per interval** — they update reserves and emit `VirtualOrderExecution` + `Sync`. A standard UniV2 monitor will miss TWAMM volume.
- **Factory addresses differ per chain** (non-deterministic; not CREATE2 with same salt). Always use chain-specific addresses from [v2.md](v2.md).
- **All contracts are immutable** (no proxies; EIP-1967 slots return zero on all deployed contracts).
- **`globalPause()`** — Fraxswap factories expose a pause flag absent from Uniswap V2. Monitor for `OwnershipTransferred` or owner calls that might toggle this.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(sig)` from `FraxFinance/fraxswap` GitHub source; `LongTermSwap0To1`, `CancelLongTermOrder`, and `VirtualOrderExecution` confirmed live via `eth_getLogs` on Ethereum pair `0x56695c26…`. Standard UniV2 events confirmed identical to Uniswap V2 topic0s.
- **Addresses:** all factories and routers `eth_getCode`-verified on each claimed chain; `allPairsLength()` cross-checked on Ethereum and Polygon; Base confirmed `0x` for all addresses.
