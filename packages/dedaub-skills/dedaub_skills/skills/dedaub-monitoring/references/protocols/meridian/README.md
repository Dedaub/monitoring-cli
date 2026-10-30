# Meridian — Protocol Reference Index

Monitoring-grade references for Meridian (meridian.xyz), the Robinhood Chain venue for RWA perpetuals and prediction markets. Meridian succeeds the Ethereal venue; Meridian Predict is the rebranded Sapience prediction protocol. Verified against live RPC on 2026-10-30.

| File | Product line | Components | Chains | Status |
|------|--------------|------------|--------|--------|
| [perps.md](perps.md) | **Perps** | ExchangeGateway (UUPS) + 8 delegatecall modules, merUSD (UUPS), third-party LP vault | Robinhood Chain (4663) | Live. Sourcify-verified gateway and merUSD. |
| [predict.md](predict.md) | **Predict** | PredictionMarketEscrow, two LP vaults, position-token factory, secondary escrow, two resolvers, onboarding sponsor, LayerZero bridge | Robinhood Chain (4663) core; Arbitrum (42161) bridge peer; Polygon (137) Polymarket reader | Live. Immutable contracts. ABIs from the official SDK. |

**Chain presence.** Robinhood Chain hosts every core contract. Arbitrum hosts only the Predict bridge peer and its token-factory twin. Polygon hosts only the Predict condition reader. Ethereum, Base, BNB, Avalanche, Optimism and Arc have no Meridian contract (`eth_getCode` = `0x`).

## Cross-cutting facts

- **Collateral is USDe.** Perps: users hold **merUSD** (`0xad22…f009`), a 1:1 wrapper of USDe (`0x5d3a1Ff2…ef34`) held by the merUSD contract; merUSD sits in the ExchangeGateway. Predict: USDe sits directly in the escrow and the vaults.
- **One emitter for perps.** Every perps event (deposits, fills, funding, liquidations, admin) comes from the gateway proxy `0xD540…F44A`, because the modules run by `delegatecall`.
- **Two owner Safes with different strength.** Perps: Safe 2-of-5 `0xf806…a5f7` (gateway, merUSD). Predict: Safe **1-of-2** `0x99a8…212c` (all Predict contracts on Robinhood). The Arbitrum and Polygon Predict contracts are owned by EOA `0x20c5…2086`.
- **Oracles.** Perps prices: Pyth Lazer verifier `0xACeA…F481` (gateway `getExchangePythLazer()`). Predict outcomes: Polymarket payouts relayed from Polygon over LayerZero, or manual settlers.
- **Upgrade surface.** Perps: `Upgraded` on two proxies plus `RegistryRecordUpdated` (module swap). Predict: no proxies; watch `PeerSet`, `BridgeConfigUpdated`, `SettlerApproved`, `ManagerUpdated`, `OwnershipTransferred`.

## Verification methodology

- **Topic0 / selectors:** `keccak256` recomputed locally from verified sources (Sourcify) or from official SDK ABIs, then matched against live bytecode and live `eth_getLogs`. Two liquidation/deleverage events were recovered by `keccak256` matching against module bytecode constants.
- **Addresses:** DefiLlama adapters, the Sapience/Meridian SDK address registry, the gateway's on-chain module registry and LayerZero peer configs; all existence-checked with `eth_getCode` on the nine target chains.
