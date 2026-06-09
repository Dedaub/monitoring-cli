# Camelot DEX — Protocol Reference Index

Monitoring-grade references for Camelot, the Arbitrum-native DEX. Verified on-chain 2026-06.

**Camelot is Arbitrum-only** — `eth_getCode = 0x` on all other six target chains (Ethereum, Base, BNB, Avalanche, Optimism, Polygon) for every contract in both files.

| File | Component | What it covers | Key contracts |
|------|-----------|----------------|---------------|
| [v2.md](v2.md) | **V2 AMM + Governance** | Classic volatile/stable AMM + GRAIL/xGRAIL governance + deprecated NFTPool/NitroPool farming | `Factory` `0x6EcCab42…`, `Router` `0xc873fEcb…`, `GRAIL` `0x3d9907F9…`, `xGRAIL` `0x3CAaE25E…` |
| [v3.md](v3.md) | **V3 CL (Algebra)** | Concentrated liquidity AMM on Algebra V1 engine + Camelot-specific pool modifications | `AlgebraFactory` `0x1a3c9B1d…`, `SwapRouter` `0x1F721E2E…`, `NFPM` `0x00c7f308…` |

Each file follows the house shape: **Topics** → **Function signatures** → **Addresses** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **All contracts are immutable** (EIP-1967 impl slot = `0x0` on every contract in both V2 and V3). No upgradeable proxies.
- **V2 Swap topic0 = Uniswap V2** (`0xd78ad95f…`). Disambiguate by pair address (get via `Factory.getPair(tokenA, tokenB, stable)`).
- **V2 PairCreated does NOT include `bool stable`** in the event — must call `pair.stable()` to determine pool type.
- **V3 Swap topic0 = Uniswap V3** (`0xc42079f9…`); **V3 pool Mint topic0 = Uniswap V3** too (`0x7a53080b…`). Use the Algebra-specific `Fee(uint16)` event (`0x598b9f04…`, fires frequently) or the factory `Pool` event (`0x91ccaa7a…`) to distinguish Camelot pools from UniV3.
- **V3 NFPM IncreaseLiquidity is 6-arg** (`0x8a82de7f…`, adds `actualLiquidity`+`pool`). UniV3 NFPM uses 4-arg (`0x3067048b…`). This IS a reliable discriminator at the NFPM level.
- **Camelot-specific V3 pool event** `0x8a89de70…` — fires as LOG1 (no indexed params, data = `(uint256 fee0, uint256 fee1)`) on every swap. Hardcoded in Camelot's forked pool bytecode. Not present on upstream Algebra V1 or Uniswap V3.
- **V2 Router has no standard `swapExactTokensForTokens`** — all swap functions require a `referrer` address parameter (fee-share system). Filter by the `to` address to identify the actual trader.
- **V2 feeTo → FeeManager** (`0x6a63830E…`): fees split to dividends (56.25%) and buyback-and-burn (31.25%).
- **GRAIL/xGRAIL governance**: xGRAIL is non-transferable (except to/from whitelisted contracts). Watch `Convert` (`0xccfaeb30…`) and `Allocate` (`0x5168bfb8…`) for participation signals.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(sig)` from `CamelotExchange` GitHub + Algebra V1 source; V2 `PairCreated`/`Swap`/xGRAIL `Convert`/`Allocate` and V3 `Swap`/`Mint`/`Fee`/`IncreaseLiquidity` confirmed live via `eth_getLogs` on Arbitrum.
- **Addresses:** every contract `eth_getCode`-verified on Arbitrum; confirmed `0x` on the other six target chains; factory views (`allPairsLength`, `poolByPair`) cross-checked.
- **Coverage caveats:** rare admin events (V2 `SetStableSwap`, xGRAIL governance; V3 `Flash`/`CommunityFee`/`Incentive`/`LiquidityCooldown`) computed from source but not live-matched. V3 Camelot-specific event `0x8a89de70…` confirmed via bytecode inspection but signature not in 4byte.directory.
