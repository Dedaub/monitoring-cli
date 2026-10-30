# Polymarket — Protocol Reference Index

Monitoring-grade references for Polymarket, the prediction-market order book on **Polygon PoS (137)**. Checked on all nine target chains (Ethereum 1, Base 8453, BNB 56, Avalanche 43114, Arbitrum 42161, Optimism 10, Polygon 137, Robinhood Chain 4663, Arc 5042) against live RPC and the canonical `Polymarket/*` repos on 2026-10-30.

Polymarket has **three settlement generations** on Polygon. They share wallets and, partly, collateral. One file per generation:

| File | Generation | Components | Status (2026-10-30) |
|------|-----------|------------|---------------------|
| [v1.md](v1.md) | **V1 — CTF stack** | Gnosis CTF, CTFExchange, NegRiskCtfExchange, NegRiskAdapter, 2 NegRiskOperators, WCOL, NegRiskVault, fee modules, UMA CTF adapters V1–V4 (binary + neg-risk), UmaSportsOracle, ProxyWalletFactory, SafeProxyFactory, legacy FPMM. Collateral USDC.e. | CTF, NegRiskAdapter and UMA adapters **live** (shared with V2). V1 **exchanges quiet** since mid-2026. Immutable. |
| [exchange_v2.md](exchange_v2.md) | **V2 — CTF Exchange V2 + pUSD** | CTFExchangeV2, NegRiskCtfExchangeV2, CollateralToken (pUSD), on/off ramps, PermissionedRamp, CTF collateral adapters. | **Main venue.** About 2,700 fills per 40 blocks. pUSD supply ≈ 484M. Exchanges immutable, pUSD UUPS. |
| [position_manager.md](position_manager.md) | **"Polymarket V2" PositionManager system** (SDK name `exchangeV3`) | PositionManager (own ERC-1155), Binary / NegRisk / Combinatorial modules, Exchange, Router, AutoRedeemer, OracleAggregator + OO / Chainlink / EOA reporter modules. | **Live, low volume** since June 2026. All UUPS. No bridge deployed. |

Each file follows the same layout: **Topics** → **Function signatures** → **Addresses** → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Polygon only.** No Polymarket market, exchange, adapter or collateral contract has code on the other eight chains. The only hits elsewhere are same-bytecode replicas of the wallet factories (ProxyWalletFactory on Ethereum and Base; SafeProxyFactory on Ethereum, Base, BNB, Arbitrum, Optimism, Robinhood Chain) and the 2020 Ethereum legacy AMM (Gnosis CTF `0xc59b…7e0c`, FPMM factory `0x4b4f…755b`). Avalanche and Arc have nothing.
- **Three exchanges, two event schemas.** V1 `OrderFilled` = `0xd0a08e8c…`. V2 and the PositionManager Exchange share `OrderFilled` = `0xd543adfd…`. Always key on `(emitter, topic0)`.
- **Two token ledgers.** V1 and V2 trade Gnosis CTF tokens (`0x4d97…6045`). The PositionManager system trades its own ERC-1155 (`0x006f…9fef`). Legacy CTF positions migrate in through `migratePositions`.
- **Three collateral layers.** USDC.e (V1 exchanges, CTF binary collateral), WCOL (neg-risk CTF collateral, owned by the NegRiskAdapter), pUSD (V2 and PositionManager trading collateral, backed by USDC.e + USDC in vault `0xc417…9db1`).
- **The user is a wallet contract.** Most makers are proxy wallets (ProxyWalletFactory) or Safes (SafeProxyFactory). `tx.from` is a Polymarket operator. Map wallets to owners before attribution.
- **Resolution is UMA-based** for V1 / V2 markets (UMA CTF adapters, NegRiskOperator, UmaSportsOracle). The PositionManager system uses its own OracleAggregator with UMA, Chainlink and EOA reporters.
- **Admin events are the security signal.** V1 / V2 contracts use the `Auth` mixin (`NewAdmin`, `NewOperator`, …). pUSD and the PositionManager system use Solady `OwnableRoles` (`RolesUpdated`, `OwnershipTransferred`) and UUPS (`Upgraded`). All upgradeable proxies share owner `0x47eb…629c`.

## Coverage caveats

- **Per-market contracts are not listed.** Markets are condition ids / position ids, not contracts. Legacy FPMM pools are clones; find them through `FixedProductMarketMakerCreation`.
- **Proxy wallets and Safes are not listed.** Derive them with the exchange views (`getPolyProxyWalletAddress`, `getSafeAddress`, `getProxyWalletAddress`, `getSafeWalletAddress`) or the Safe `ProxyCreation` event.
- **docs.polymarket.com** did not respond from the verification host. Addresses come from the official repos and SDK configs, and were all checked on-chain.
- **Polymarket US** (the CFTC-regulated venue) has no on-chain contract in these repos. It is not covered.
