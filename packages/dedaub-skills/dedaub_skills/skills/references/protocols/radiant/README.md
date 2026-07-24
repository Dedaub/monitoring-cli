# Radiant Capital — Protocol Reference Index

Monitoring-grade references for Radiant Capital, an **omnichain money market** built as an **Aave V2 fork** with a LayerZero (RDNT OFTV2) + Stargate cross-chain layer. Verified against live RPC + the canonical `radiant-capital/v2` repo + official Radiant docs deployment pages on **2026-06-08**.

> **OPERATIONAL STATUS — exploited & winding down.** On **2024-10-16** Radiant suffered a **~$50M exploit on its Arbitrum and BNB markets**, executed through a **private-key / operational compromise** (malware → developers' hardware wallets → ≥3 multisig/owner keys; Mandiant attributed it to North Korea's **AppleJeus / Lazarus** campaign). It was **not a core-contract bug** — the vector was the contracts' legitimate **upgradeability/ownership surface**. Funds were never recovered; the DAO **began winding down on 2026-06-01** and the protocol is in **maintenance mode** (front-end + core contracts online so users can withdraw/repay/manage existing positions). Live `Deposit`/`Borrow` volume is near zero; `Withdraw`/`Repay`/`ReserveDataUpdated` dominate (verified live on all 4 chains).

Radiant is **two generations** of an Aave-V2-style lending core. One file per generation:

| File | Generation | Components | Chains | Status |
|------|-----------|------------|--------|--------|
| [v1.md](v1.md) | **V1** — original Aave V2 fork | LendingPool + AddressesProvider + rTokens/debt tokens (6 reserves) | **Arbitrum One (42161) only** | **Deprecated** (superseded 2022/23). ~zero activity. |
| [v2.md](v2.md) | **V2** — omnichain Aave V2 fork + LayerZero/Stargate | LendingPool, rTokens/variable+stable debt, AaveProtocolDataProvider, LendingPoolAddressesProvider(+Registry), AaveOracle/OracleRouter, ChefIncentivesController, MultiFeeDistribution(+Middle), RadiantOFT (RDNT), Leverager, WethGateway, StargateBorrowV2 | **Arbitrum (42161), BNB (56), Ethereum (1), Base (8453)** | **Live but in wind-down/maintenance** after the Oct-2024 exploit. |

Each file follows the house layout: **Topics** (chain-agnostic `topic0 = keccak256(event sig)`) → **Function signatures** (chain-agnostic 4-byte selectors) → **Addresses** (one section per chain) → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **It's an Aave V2 fork.** Every `Deposit`/`Withdraw`/`Borrow`/`Repay`/`LiquidationCall`/`FlashLoan`/`ReserveDataUpdated` topic0 and selector is **byte-for-byte identical to Aave V2** ([aave/v2.md](../aave/v2.md)) — **and identical between Radiant V1 and V2**. The supply event is **`Deposit`** (not V3's `Supply`); rToken vs variableDebtToken `Mint`/`Burn` carry **different** topic0s (V2 lineage). **Disambiguate strictly by `(Pool address, chain)`**, never by topic0/selector alone.
- **Lending exists on 4 chains: Arbitrum, BNB, Ethereum, Base.** **Avalanche, Optimism, and Polygon have ZERO Radiant contracts** — every core/RDNT address `eth_getCode`-checks to `0x` there (verified). V1 is Arbitrum-only.
- **No shared cross-chain vanity address — not even for the RDNT OFT.** Each chain has unique addresses; key on `(chainId, address)`. **Decoy:** the BNB RDNT address `0xf7DE7E8A…84dF` also has bytecode on Arbitrum but is an **unrelated "NOVA" token** there (pure collision, verified via `name()`/`symbol()`). Never filter an RDNT address on the wrong chain.
- **The exploit was an admin/upgrade-path compromise, so the monitoring alpha is the proxy/ownership surface, not the lending math.** Core contracts are upgradeable: LendingPool + rTokens/debt = EIP-1967 (Aave style, immutable admin via the AddressesProvider); ChefIncentivesController / MultiFeeDistribution / MiddleFeeDistribution / Leverager / PriceProvider = TransparentUpgradeableProxy (shared ProxyAdmin per chain, e.g. ETH `0x653652b5…`). **Watch `Upgraded(address)` topic0 `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` and ProxyAdmin/owner changes.** Immutable (impl slot `0x0`, verified): **AaveOracle, OracleRouter, LendingRateOracle, AaveProtocolDataProvider, LendingPoolAddressesProvider, and the RDNT OFT token**.
- **Oracle base is 8-dec USD, NOT Aave-V2's ETH/wei** (fork divergence, verified live: `getAssetPrice(USDC)≈$1`, `getAssetPrice(WETH)≈$1686` in 1e8). Scale account-data/prices like Aave **V3**.
- **Cross-chain plumbing:** RDNT moves via **LayerZero OFTV2** (`SendToChain`/`ReceiveFromChain`); cross-chain deposit/borrow via **Stargate** (`StargateBorrowV2` on Arbitrum). RDNT and the LendingPool also each emit their own `Paused`/`Unpaused` shapes — the OFT's `Paused(address)` (OZ) is distinct from the LendingPool's no-arg `Paused()`.

## Verification methodology

- **Topic0 / selectors:** computed locally with keccak-256 from canonical `radiant-capital/v2` source signatures; validated against live `eth_getLogs` on the LendingPool on all four chains (Ethereum/BNB/Base showing `Deposit`/`Withdraw`/`ReserveDataUpdated`; Arbitrum near-idle, 1 RDU over ~990k blocks) and on Ethereum `rWETH` (Mint/Burn). `sendFrom` selector confirmed in deployed RDNT bytecode.
- **Addresses:** parsed from the official Radiant docs deployment pages and existence-checked via `eth_getCode` per chain; pool/rToken/oracle wiring and every proxy's EIP-1967 impl/admin slot read live; oracle USD-scale confirmed by reading `getAssetPrice`.

## Coverage caveats

- **V1 rToken/debt-token addresses are not re-enumerated** (deprecated; recover on-chain via `getReserveData` if ever needed). V2 reserves are fully listed per chain.
- **Base runs no on-chain ChefIncentivesController** (emissions there ran through Merkl) — don't scan for §1.3 Chef events on Base.
- **Per-reserve stableDebtToken addresses** are omitted (stable rate is largely unused); recover via `getReserveTokensAddresses(asset)` if required.
