# Spark — Protocol Reference Index

Monitoring-grade references for Spark across **Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Robinhood Chain (4663), Arc (5042)**. Spark is a Sky "star" (subDAO). It runs three distinct product lines. Each line has its own file:

| File | Product line | Components | Chains |
|------|-------------|------------|--------|
| [sparklend.md](sparklend.md) | **SparkLend** (money market) | Aave-V3 fork: Pool, spTokens, oracle, FreezerMom, CapAutomator, D3M DAI | ETH (+ Gnosis, winding down) |
| [liquidity-layer.md](liquidity-layer.md) | **Spark Liquidity Layer (SLL / ALM)** | ALMProxy, MainnetController, ForeignController, RateLimits, ALMProxyFreezable, PAU (diamond) | ETH, Base, Arb, OP, Avax, Robinhood |
| [savings.md](savings.md) | **Spark Savings** | Spark Vaults V2 (spUSDC, spUSDT, spETH, spPYUSD, spUSDG), sUSDC, PSM3, SSR/DSR oracles, Savings Intents | ETH, Base, Arb, OP, Avax, Robinhood |

The Sky core (USDS, sUSDS, Vat, LitePSM, Allocator Vaults) is in [../sky/](../sky/). Grove, the other Sky star that runs a fork of the SLL, is in [../grove/core.md](../grove/core.md).

## Cross-cutting facts worth knowing before you start

- **One registry for all addresses.** `sparkdotfi/spark-address-registry` has one Solidity library for each chain (`Ethereum.sol`, `Base.sol`, `Arbitrum.sol`, `Optimism.sol`, `Avalanche.sol`, `Robinhood.sol`, `BSC.sol`, plus Gnosis, Unichain, World Chain, X Layer). Each address has a source/commit comment. All the target-chain entries in these docs were checked live with `eth_getCode` on 2026-10-30.
- **Money flows in one loop.** Sky mints USDS into the Spark Allocator Vault. The SLL `MainnetController.mintUSDS` moves it into the ALMProxy. The SLL swaps to USDC, bridges with CCTP, and deposits into venues. Spark Vault V2 deposits come back to the SLL with `take`. The ALMProxy is the `TAKER_ROLE` on every Spark Vault.
- **Address reuse across chains is common and dangerous.** The same 20-byte address is a different Spark contract on different chains (for example `0x1601843c…347E` = ETH ALMProxy and Base PSM3, `0x28B3a8fb…a43d` = spUSDC on ETH and Avalanche). Always key on `(chainId, address)`.
- **Upgrade model.** SLL contracts and PSM3 are immutable. Logic changes by controller rotation (`RoleGranted(CONTROLLER, …)`). Spark Vaults V2 and sUSDC are UUPS proxies. SparkLend is fully upgradeable (Aave model).

## Chain presence

| Chain | SparkLend | SLL | Savings | Other |
|-------|-----------|-----|---------|-------|
| Ethereum (1) | ✓ | ✓ | spUSDC, spUSDT, spETH, spPYUSD, sUSDC, Intents | SPK, stSPK, governance |
| Base (8453) | — | ✓ | sUSDC, PSM3 | — |
| Arbitrum (42161) | — | ✓ | spUSDT, sUSDC, PSM3 | — |
| Optimism (10) | — | ✓ | sUSDC, PSM3 | — |
| Avalanche (43114) | — | ✓ | spUSDC | — |
| Robinhood Chain (4663) | — | ✓ | spUSDG | — |
| BNB (56) | — | — | — | SPK LayerZero OFT `0xAfF2e841851700D1Fc101995Ee6b81Ae21Bb87D7` only |
| Polygon PoS (137) | — | — | — | none (a 2770 B sweep contract sits at some Spark addresses — decoy) |
| Arc (5042) | — | — | — | none |
