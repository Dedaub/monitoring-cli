# Pharaoh Exchange — Protocol Reference Index

Monitoring-grade references for Pharaoh, a ve(3,3) + concentrated-liquidity DEX on **Avalanche C-Chain (43114)** forked from RAMSES (which itself forked from Velodrome/Solidly). Verified on-chain 2026-06.

**Pharaoh is Avalanche-only** — `eth_getCode = 0x` on all other six target chains (Ethereum, Base, BNB, Arbitrum, Optimism, Polygon) for every contract in both files.

| File | Component | What it covers | Key contracts |
|------|-----------|----------------|---------------|
| [legacy.md](legacy.md) | **Legacy AMM** | Solidly V2 classic AMM + ve(3,3) governance (Voter, Minter, vePHAR NFT, gauges, epoch emissions) | `PairFactory` `0x85448bF2…`, `Router` `0x9CEE04…`, `Voter` `0x922b9C…`, `VotingEscrow/vePHAR` `0xfe99e9…` |
| [cl.md](cl.md) | **CL + DLMM** | RamsesV3 concentrated-liquidity pools + NFPM + DLMM (Dynamic Liquidity Market Maker) | `RamsesV3Factory` `0xAE6E5c…`, `NFPM` `0x0B4478…`, `SwapRouter` `0xc8B8fC…`, `DLMMFactory` `0xEb4800…` |

Each file follows the house shape: **Topics** → **Function signatures** → **Addresses** → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Three liquidity pool types exist on Pharaoh, each with different topic0s:**
  1. **Legacy pairs** (Solidly V2): `Swap` = `0xd78ad95f…` (identical to Uniswap V2 — disambiguate by address)
  2. **CL pools** (RamsesV3): `Swap` = `0xc42079f9…` (identical to Uniswap V3 — disambiguate by address); **`Mint` = `0xd78218c0…`** (Ramses-specific — 3rd param is `uint256 index`, differs from Uniswap V3's `0x7a53080b…`)
  3. **DLMM pairs**: `Swap` = `0xad7d6f97…` (distinct — no collision with either of the above)
- **`PairCreated` is 3-arg (no `bool stable`)** — `PairCreated(address,address,address,uint256)` = `0x0d3648bd…`. Call `Pair.stable()` to determine stable vs volatile pool type.
- **CL pools use `tickSpacing (int24)` as the pool key**, not `fee (uint24)`. `RamsesV3Factory.getPool(tokenA, tokenB, tickSpacing)`. The `PoolCreated` event has `uint24 fee` as 3rd param but the lookup key in the factory is tickSpacing.
- **`FeeAdjustment(uint24,uint24)` = `0x0cba8718…`** is a Ramses-specific CL pool event (live-confirmed). Uniswap V3 uses `SetFeeProtocol(uint8,uint8)` = `0x7a8f5b6a…` instead — monitors built for Uniswap V3 will miss Pharaoh fee changes.
- **Voter and VotingEscrow are EIP-1967 transparent proxies** (upgradeable). The VotingEscrow proxy admin (`0x6a66…`) is owned by an EOA — a separate upgrade surface from the Team Multisig.
- **PHAR token** `0x13A466…` · **xPHAR** `0xE8164E…` (liquid wrapper; deposited into VotingEscrow for vePHAR NFTs). Emissions are weekly PHAR → xPHAR → VoteModule → distributed to gauges voted on by vePHAR holders.
- **DLMM source is not public** — 2 DLMM events were identified from live on-chain logs; `LBPairCreated` and other factory events were not observed in the sampled windows and remain unverified. See [cl.md](cl.md) §6.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` (`cast keccak`) from `PharaohExchange/pharaoh-contracts` source (IRamsesV3PoolEvents.sol, Solidly pair/factory interfaces); live-confirmed on Avalanche: Legacy `Swap`/`GaugeCreated`/`Voted`/vePHAR events, CL `Swap`/`Mint`/`Burn`/`CollectProtocol`/`FeeAdjustment`.
- **Addresses:** every contract `eth_getCode`-verified non-empty on Avalanche; confirmed `0x` on all other 6 target chains; factory wiring confirmed via `eth_call` (PairFactory `allPairsLength()`, Voter views, NFPM `factory()`).
- **Coverage caveats:** DLMM full event set partially unverified (source not public); two live Legacy events (`0x3e218be5…`, `0xf97732ff…`) identified on-chain but not resolved in 4byte.directory — flagged in [legacy.md](legacy.md). `PoolCreated` was not observed in the sampled block ranges (low-frequency factory event); topic0 `0xb4b64a6a…` computed from source.
