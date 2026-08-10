# Seamless Protocol — Protocol Reference Index

Monitoring-grade references for Seamless Protocol, verified against live RPC + the canonical `seamless-protocol/*` GitHub repos on **2026-06-08**. Seamless is a **Base-native** DeFi protocol (the longest-running native protocol on Base, live since 2023) that pivoted from its own Aave-V3 fork to a **Morpho-powered** design ("Seamless 2.0"), then announced an **orderly wind-down on 2026-04-07** (web app offline **2026-06-30**).

Seamless is **two distinct product lines**, not a linear `v1→v2`. One file per line (each follows the same section layout):

| File | Generation / line | Components | Chains | Status |
|------|-------------------|-----------|--------|--------|
| [v1.md](v1.md) | **Legacy lending market** | Aave-V3.0 **soft fork**: Pool behind PoolAddressesProvider, sTokens (sUSDC/sWETH…), variableDebt tokens, AaveOracle, PoolDataProvider, ACLManager, PoolConfigurator, CapsPlusRiskSteward | **Base (8453) only** | **Deprecated / winding down.** Upgradeable Aave proxies. |
| [leveragetokens.md](leveragetokens.md) | **Morpho-powered ILM (current)** | **LeverageManager** (singleton) + permissionless **LeverageToken** beacon proxies + **MorphoLendingAdapter** (Morpho Blue position owner) + **RebalanceAdapter** + **LeverageRouter** periphery; **Seamless Morpho Vaults** (smUSDC/smcbBTC/smWETH = MetaMorpho V1.1) on the Earn side | **Base (8453) + Ethereum (1)** | **Deprecated / winding down** (Leverage Tokens lacked PMF; Vaults drained by curator Gauntlet). UUPS + Beacon proxies; adapters/periphery immutable. |

Each file follows: **Topics** (chain-agnostic `topic0 = keccak256(event sig)`) → **Function signatures** (chain-agnostic 4-byte selectors) → **Addresses** (network-specific, one section per chain) → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Chain coverage is narrow.** The **lending market is Base-only**; the **Leverage Tokens** extend to **Base + Ethereum**; the **Morpho Vaults are Base-only**. **Nothing exists on BNB, Avalanche, Arbitrum, Optimism or Polygon** — `eth_getCode` = `0x` for every Seamless address there (verified 2026-06-08).
- **DEPRECATED.** Wind-down announced 2026-04-07 (Leverage Tokens lacked product-market fit, liquidity/revenue constraints). App offline **2026-06-30**; withdraw-only afterward. All contracts are still **live on-chain** (read 2026-06-08) but treat activity as redemptions, not growth. Morpho Vaults APY → 0% (Gauntlet pulling funds); **stkSEAM** staking yield turned off.
- **V1 is an Aave V3.0 fork** — its `Supply`/`Borrow`/`Repay`/`LiquidationCall`/`FlashLoan` topic0s and selectors are **byte-for-byte identical to Aave V3** (reuse [../aave/v3.md](../aave/v3.md)), minus the v3.3 deficit events and v3.4 selectors. aTokens are branded **sTokens** (`s` = "Seamless"; e.g. `name()` = "Seamless USDC", symbol `sUSDC`). The market id is **"Base Seamless Market"**.
- **V1 liquidation dispatcher anomaly** (same as Aave/Spark): the `liquidationCall` selector `0x00a718a9` is **absent from the live Pool impl bytecode**, but `LiquidationCall` events fire (555 logs in one 49k window). **Detect V1 liquidations by the event, never the selector.**
- **The leverage-token underlying lending is Morpho Blue, not a Seamless contract.** Each LeverageToken's `MorphoLendingAdapter` is the `onBehalf` of the Morpho Blue singleton (`0xBBBB…EEFFCb` on both chains) — real debt/collateral motions are Morpho Blue events, not Seamless events. See [../morpho/v1.md](../morpho/v1.md).
- **Address-reuse trap (Leverage Tokens):** Base and Ethereum were deployed at matching deployer nonces, so the **same address means different contracts per chain** — e.g. `0x5C37EB14…E351` = LeverageManager proxy on ETH but VeloraAdapter on Base; `0x603Da735…0a82` = factory proxy on ETH but LeverageToken impl on Base; `0xfE910134…1856` = LeverageToken impl on ETH but LeverageManager impl on Base. **Always key on `(chainId, address, role)`.**
- **Proxy zoo:** V1 core = Aave immutable-admin EIP-1967 proxies. LeverageManager = **UUPS**; LeverageToken factory = **UpgradeableBeacon**; each LeverageToken = **beacon proxy** (beacon = the factory, so one beacon swap upgrades them all); adapters/router/periphery = **immutable**; Morpho Vaults = **immutable** MetaMorpho V1.1. **SEAM (Base), esSEAM, stkSEAM are upgradeable proxies; SEAM on Ethereum is a plain (non-proxy) bridged token.**

## Tokens & governance (shared across both lines)

| Token / role | Address | Chain | Notes |
|---|---|---|---|
| **SEAM** (gov token) | `0x1C7a460413dD4e964f96D8dFC56E7223cE88CD85` | Base 8453 | Upgradeable proxy (impl `0x57b4…fd3f`); also a V1 reserve. |
| SEAM | `0x6b66ccd1340c479B07B390d326eaDCbb84E726Ba` | Ethereum 1 | Plain non-proxy bridged token (impl slot `0x`). |
| **EscrowSEAM** (esSEAM) | `0x998e44232BEF4F8B033e5A5175BDC97F2B10d5e5` | Base 8453 | Vesting-escrowed SEAM (proxy). |
| **StakedSEAM** (stkSEAM) | `0x73f0849756f6A79C1d536b7abAB1E6955f7172A4` | Base 8453 | Safety-module staking (proxy); yield being switched off in wind-down. |
| Timelock Short / Governor Short | `0x639d2dD24304aC2e6A691d8c1cFf4a2665925fee` / `0x8768c789C6df8AF1a92d96dE823b4F80010Db294` | Base 8453 | Short two-tier governance (Timelock Short = V1 ACL_ADMIN + leverage-token treasury). |
| Timelock Long / Governor Long | `0xA96448469520666EDC351eff7676af2247b16718` / `0x04faA2826DbB38a7A4E9a5E3dB26b9E389E761B6` | Base 8453 | Long two-tier governance. |
| Guardian | `0xA1b5f2cc9B407177CD8a4ACF1699fa0b99955A22` (Base) / `0x90E8C75e2917E3C2F284F6922Df6c16F7C03123c` (ETH) | both | Emergency guardian for leverage tokens. |

## Coverage caveats (read these)

- **Per-reserve / per-LeverageToken addresses are not fully enumerated** — V1 reserves shrink during the wind-down (read `Pool.getReservesList()` + `getReserveData(asset)` live); LeverageTokens are permissionless (discover via `BeaconProxyFactory.numProxies()` / `BeaconProxyCreated` / `LeverageTokenCreated`). The files list the live core singletons + a confirmed sample.
- **Morpho Vault internals** use the standard MetaMorpho V1.1 / Morpho Blue ABI — see [../morpho/v1.md](../morpho/v1.md). [leveragetokens.md §5](leveragetokens.md) lists the three Seamless vault addresses and confirms their classification, but does not re-document the Morpho ABI.
- **Older pre-migration ILM "LoopStrategy" contracts** (the original 2024-era leverage vaults before the Morpho rebuild) are retired and not documented here; the current Leverage-Token contract set (Oct 2025 deploy) supersedes them.
