# LayerBank — Protocol Reference Index

Monitoring-grade references for LayerBank. Re-checked on 2026-10-30 against live RPC and the DefiLlama LayerBank adapter.

| File | Generation | Design | Target-chain presence |
|------|-----------|--------|-----------------------|
| [core.md](core.md) | **V1 / V2** | Own `Core` (risk engine) + per-asset `LToken` markets, `PriceCalculator`, `Validator`, LAB token. Plain (non-proxy) contracts. | **BNB Smart Chain** only (V2 `Core`, 15 markets, near-zero liquidity). Main activity is off-target (Linea, Scroll, Mode, Manta, …). |
| [v3.md](v3.md) | **V3** | **Aave V3 fork** (Pool, PoolConfigurator, AddressesProvider, aTokens). Same topics/selectors as Aave V3. | **Robinhood Chain** ("LayerBank Robinhood Core Market": tokenized equities/ETFs + USDG/WETH/cbBTC; about $3.8M TVL on DefiLlama). Also on Plume, Hemi, Nibiru, BOB, Rootstock (off-target). |

## Cross-cutting facts

- **V1/V2 and V3 share no event topics.** V1/V2 emit `MarketSupply`/`MarketRedeem` on the `Core` and `Borrow`/`RepayBorrow` on each `LToken`; V3 emits the Aave V3 `Supply`/`Borrow`/`Repay`/`LiquidationCall` on the Pool. Pick the file by chain.
- **Addresses are per chain.** There is no CREATE2-shared LayerBank address. Key on `(chainId, address)`.
- **Not deployed** on Ethereum, Base, Avalanche, Arbitrum, Optimism, Polygon or Arc (no V1/V2/V3 contracts).
