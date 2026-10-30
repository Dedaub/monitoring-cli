# Ramses Exchange — Protocol Reference Index

Monitoring-grade references for Ramses, the ve(3,3) + concentrated-liquidity DEX on **Arbitrum One (42161)**, **Polygon PoS (137)** and **Robinhood Chain (4663)**. Verified on-chain 2026-06. Re-checked on 2026-10-30: added [`v3.md`](v3.md) for the 2026 redeploy (tickSpacing-keyed `RamsesV3Factory` on Arbitrum, Polygon and Robinhood; DLMM and Voter on Robinhood).

**The 2023 generation (`legacy.md`, `cl.md`) is Arbitrum-only** — `eth_getCode = 0x` on all other target chains; its core contracts use an `AAA`/`AA2c` vanity prefix. **The 2026 generation (`v3.md`) is on Arbitrum, Polygon and Robinhood Chain**, uses plain `CREATE` addresses (no vanity prefix), and the same address holds a different contract on each chain. Nothing is on Ethereum, Base, BNB, Avalanche, Optimism or Arc.

| File | Component | What it covers | Key contracts |
|------|-----------|----------------|---------------|
| [legacy.md](legacy.md) | **Legacy AMM + Governance** | Solidly volatile+stable pairs + ve(3,3) governance (RAM token, veRAM NFT, Voter, Minter, Gauges, Bribes, RewardDistributor) | `PairFactory` `0xAAA20D08…`, `Router` `0xAAA87963…`, `Voter` `0xAAA2564D…`, `VotingEscrow` `0xAAA34303…`, `RAM` `0xAAA6C1E3…` |
| [v3.md](v3.md) | **2026 redeploy: CL (RamsesV3) + DLMM + new legacy factory** | tickSpacing-keyed CL (Pharaoh-style `Mint` with `index`), new 4-arg `PairCreated` PairFactory, AccessHub; DLMM and Voter/RAM/r33 on Robinhood only | `RamsesV3Factory` Arb `0xd0019e86…`, Poly `0x2Bef16A0…`, Robin `0xE0c4ceb9…` |
| [cl.md](cl.md) | **CL AMM (RamsesV3 / UniV3-style)** | Concentrated liquidity with fee-tier pools (NOT tickSpacing-keyed), NFPM, SwapRouter, gauges | `RamsesV3Factory` `0xAA2cd747…`, `NFPM` (find via factory), `SwapRouter` |

Each file follows the house shape: **Topics** → **Function signatures** → **Addresses** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Legacy `PairCreated` INCLUDES `bool stable`** — `PairCreated(address,address,bool,address,uint256)` = `0xc4805696…`. This is the 5-arg Solidly-canonical form (unlike Pharaoh which uses 3-arg without `bool stable`).
- **Legacy `Swap` = Uniswap V2** (`0xd78ad95f…`). Disambiguate by pair address.
- **CL `Swap` = Uniswap V3** (`0xc42079f9…`). CL `Mint` = `0x7a53080b…` (standard 7-param, same as UniV3). The factory key is **fee (uint24)**, not tickSpacing — call `getPool(tokenA, tokenB, fee)`.
- **NFPM is branded `"Ramses V2 Positions NFT-V1"` / `"RAM-V2-POS"`** (distinct from Pharaoh's `"ALGB-POS"`).
- **Voter, VotingEscrow, and BribeFactory are EIP-1967 proxies** sharing a single ProxyAdmin `0xa388d2dd…`. All other contracts are immutable.
- **No xRAM token** on Arbitrum (unlike Pharaoh which has xPHAR).
- **"ramses-hl" on DefiLlama** refers to the HyperEVM deployment on Hyperliquid L1 — a separate chain outside the 7 target chains. No HL pool type exists on Arbitrum.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(sig)` from Ramses GitHub source; legacy `PairCreated`/`Swap`/`Voted`/`GaugeCreated` and CL `Swap`/`Mint` confirmed live via `eth_getLogs` on Arbitrum.
- **Addresses:** every contract `eth_getCode`-verified on Arbitrum; confirmed `0x` on all 6 other target chains; contract views (Voter.factory(), Minter._ve(), etc.) cross-checked.
- **Coverage caveats:** CL `PoolCreated` events not live-confirmed (all pools created at launch in blocks beyond publicnode's window); topic0 confirmed in factory bytecode.
