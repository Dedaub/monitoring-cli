# Liquity — Index

Liquity is an immutable CDP (collateralized debt position) protocol on Ethereum. Two generations are live. Both are Ethereum-only among the nine target chains.

| File | Generation | Stablecoin | Collateral | Status |
|------|-----------|------------|------------|--------|
| [v1.md](v1.md) | Liquity V1 (2021-04) | LUSD `0x5f98805A4E8be255a32880FDeC7F6728C6568bA0` | ETH (native) | Live, immutable, no admin |
| [v2.md](v2.md) | Liquity V2 relaunch (2025-05-19) | BOLD `0x6440f144b7e50d6a8439336510312d2f54beb01d` | WETH, wstETH, rETH (one branch each) | Live, immutable, no admin |

## Cross-cutting facts

- **No proxies anywhere.** EIP-1967 slots are zero. Ownership is renounced or absent. There is no `Upgraded` event to watch.
- **Chain presence:** Ethereum only. Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc have no Liquity contracts.
  Bridged LUSD tokens exist on Base, Arbitrum and Optimism (see v1.md §4). They emit only ERC-20 events.
- **Shared contracts:** LQTY (`0x6DEA81C8…c54D`) and V1 LQTYStaking (`0x4f9Fbb3f…605d`) serve both generations. V2 Governance stakes LQTY in V1 LQTYStaking through per-user proxies.
- **Trove key:** V1 uses the borrower address. V2 uses a `uint256` troveId that is also a TroveNFT token id.
- **Legacy V2:** the January 2025 V2 deployment is legacy (Stability Pool issue). Legacy BOLD is `0xb01dd87B29d187F3E3a4Bf6cdAebfb97f3d9aB98`.
- **Topic0 overlaps between V1 and V2:** `P_Updated`, `CollBalanceUpdated`, `BaseRateUpdated`, `LastFeeOpTimeUpdated`, `Transfer`. Filter by emitter.
- **Forks:** many Liquity V1 and V2 forks reuse the same topic0 values at other addresses. V2 forks on target chains include Nerite (Arbitrum), Ebisu (Ethereum), USDaf (Ethereum), DeFi Dollar (Ethereum) and Aesyx (Avalanche). They are not documented here.

## Highest-value alerts

| Signal | V1 | V2 |
|--------|----|----|
| Liquidation | `Liquidation` + `TroveLiquidated` on TroveManager | `Liquidation` + `TroveOperation(op=5)` on each branch TroveManager |
| Redemption (peg defence) | `Redemption` on TroveManager | `Redemption` on branch TroveManagers; `BaseRateUpdated` on CollateralRegistry |
| Oracle trouble | `PriceFeedStatusChanged` | `ShutDownFromOracleFailure` on branch PriceFeed |
| Branch shutdown | — | `ShutDown(tcr)` on branch BorrowerOperations |
| Stability Pool drain | `UserDepositChanged`, `StabilityPoolLUSDBalanceUpdated` | `DepositOperation`, `StabilityPoolBoldBalanceUpdated` |
