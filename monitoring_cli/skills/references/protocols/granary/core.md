# Granary Finance ("The Granary") — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism; not Polygon)

**Status:** verified against live RPC on every listed chain and the canonical `The-Granary/Granary-Protocol-v1` repo + the DefiLlama `the-granary` adapter, on 2026-06-08. Every topic0/selector recomputed locally as `keccak256(signature)` and a sample cross-checked against live `eth_getLogs`; every address resolved by walking the on-chain `LendingPoolAddressesProviderRegistry → LendingPoolAddressesProvider → LendingPool` graph and existence-checked via `eth_getCode`; proxy slots read live.
**Scope:** the seven chains the user asked about. **Granary's lending market is deployed on six of them — Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche (43114), Arbitrum One (42161), Optimism (10) — and is NOT deployed on Polygon PoS (137)** (no registry/provider/pool; every Granary address returns empty `eth_getCode` on Polygon — see §9). **BNB carries TWO parallel "Granary Genesis Market" deployments** (its own registered cluster + the shared ETH/Base/Avax cluster — §8). Topics + selectors are chain-agnostic; addresses are network-specific. Granary also runs on **Fantom (250)** and **Metis (1088)**, and once configured a **Linea (59144)** registry — all outside the 7-chain scope, documented as off-target anchors in §10.

Granary ("The Granary") is a **soft fork of Aave V2** (`aave/protocol-v2`-era, built by Byte Masons / the Ethos team). Its event topics and function selectors are **byte-for-byte identical to Aave V2** — see [aave/v2.md](../aave/v2.md). The market name on every chain is **"Granary Genesis Market"** (`LendingPoolAddressesProvider.getMarketId()`). The contract set is the V2 set: **`LendingPool`** (entrypoint, emits `Deposit`/`Borrow`/`Repay`/`Withdraw`/`LiquidationCall`/`ReserveDataUpdated`), **`LendingPoolAddressesProvider`** (per-market registry), **`LendingPoolConfigurator`** (risk admin), **`LendingPoolCollateralManager`** (delegatecall target for liquidations), per-reserve **gTokens** (the aToken equivalent, branded `grain*` e.g. `grainDAI` / "Granary DAI"), per-reserve **variableDebtToken** + **stableDebtToken** (stable rate exists in code), an **AaveOracle**-equivalent price oracle, a `LendingRateOracle`, an `AaveProtocolDataProvider`, an `AaveIncentivesController`-equivalent, and the **GRAIN** reward/governance token.

Three things to internalize before indexing:

1. **It's Aave V2, so the supply event is `Deposit` (not `Supply`) and `getUserAccountData` returns values in ETH/wei (1e18), not USD.** Reuse the [aave/v2.md](../aave/v2.md) detection set verbatim. The aToken/debt-token `Mint`/`Burn` topic0s are the **V2** ones (and differ between gToken and debt token — §1.2).
2. **Granary uses Aave's `InitializableImmutableAdminUpgradeabilityProxy`.** The **EIP-1967 implementation slot is used** (read it live), but the **admin is immutable** (baked into bytecode, not the EIP-1967 admin slot — that slot reads `0x0` on every Granary proxy). `LendingPoolAddressesProvider`, the price oracle, and the data provider are **plain non-proxy** contracts (impl slot `0x0`). See §11.
3. **Addresses partially collide across chains.** Ethereum, Base, Avalanche, **and BNB Smart Chain** all host the same shared cluster: `LendingPoolAddressesProvider` (`0xedc8…00fc`), `LendingPool` (`0xb702…eed3`), `LendingPoolConfigurator` (`0xc534…d61c`), and the same gToken/debt-token instance addresses (CREATE2-deterministic across those four). **BNB additionally runs a second, chain-unique cluster** (provider `0x12c2…dFBf`, pool `0x7171…9032`) with the SAME 6 reserves duplicated — so BNB has *two* "Granary Genesis Market" deployments (§8). Optimism and Arbitrum each diverge with fully unique addresses (the shared `0xb702…`/`0xedc8…`/`0xc534…` literals return empty `eth_getCode` there). **Always key on `(chainId, address)`** — the same literal `LendingPool` `0xb702…eed3` is a live Granary pool on **ETH/Base/Avax/BNB** but is absent (or unrelated bytecode) on Optimism/Arbitrum/Polygon.

> **Activity note (verified 2026-06-08):** Granary is low-TVL and largely winding down. Optimism is the most active market (live `Deposit`/`Withdraw`/`LiquidationCall`/gToken `Mint`/`Burn` logs in recent windows). The **Ethereum market is effectively dormant** (0 `Deposit`, 2 `ReserveDataUpdated` in ~450k blocks); **both BNB clusters are dormant** too (0 events in ~200k blocks — §8). Expect `Withdraw`/`Repay`/`LiquidationCall` to dominate over `Deposit`/`Borrow`.

---

## 0. Contract families & versions

| Family | Granary name | Aave V2 analogue | Per-chain? | Proxy? |
|---|---|---|---|---|
| Pool entrypoint | LendingPool | LendingPool | one per chain (ETH/Base/Avax/BNB share `0xb702…`; BNB has a 2nd unique pool) | ✓ EIP-1967 (immutable admin) |
| Registry | LendingPoolAddressesProvider | same | one per market | ✗ plain ownable |
| Registry-of-registries | LendingPoolAddressesProviderRegistry | same | one per chain | ✗ |
| Risk admin | LendingPoolConfigurator | same | one per chain | ✓ EIP-1967 |
| Liquidation logic | LendingPoolCollateralManager | same | one per chain | ✗ delegatecall target |
| Supply token | **gToken** (`grainXXX`) | aToken | per reserve | ✓ EIP-1967 (admin=Configurator) |
| Debt tokens | variableDebtXXX / stableDebtXXX | same | per reserve | ✓ EIP-1967 |
| Oracle | AaveOracle-equiv | AaveOracle | one per chain | ✗ |
| Rate oracle | LendingRateOracle | same | one per chain | ✗ |
| Data reader | AaveProtocolDataProvider | same | one per chain | ✗ |
| Rewards | AaveIncentivesController-equiv | StakedTokenIncentivesController | one per chain | ✓ proxy template (impl unset — §12.4) |
| Token | **GRAIN** | (stkAAVE/AAVE analogue) | per chain (unique addrs) | minimal/bridged ERC-20 |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Identical to Aave V2 (Granary is a fork). All values recomputed locally with keccak on 2026-06-08; `Deposit`/`Withdraw`/`LiquidationCall`/`ReserveDataUpdated` and gToken/debt `Mint`/`Burn` additionally confirmed against live Optimism logs (§12).

### 1.1 LendingPool (emits all lending activity) — emitter = the per-chain LendingPool (§3–§8)

| topic0 | Event |
|--------|-------|
| `0xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951` | `Deposit(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint16 indexed referral)` |
| `0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7` | `Withdraw(address indexed reserve, address indexed user, address indexed to, uint256 amount)` |
| `0xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b` | `Borrow(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint256 borrowRateMode, uint256 borrowRate, uint16 indexed referral)` |
| `0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa` | `Repay(address indexed reserve, address indexed user, address indexed repayer, uint256 amount)` |
| `0xea368a40e9570069bb8e6511d668293ad2e1f03b0d982431fd223de9f3b70ca6` | `Swap(address indexed reserve, address indexed user, uint256 rateMode)` (stable↔variable) |
| `0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2` | `ReserveUsedAsCollateralEnabled(address indexed reserve, address indexed user)` |
| `0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd` | `ReserveUsedAsCollateralDisabled(address indexed reserve, address indexed user)` |
| `0x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300` | `RebalanceStableBorrowRate(address indexed reserve, address indexed user)` |
| `0x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac` | `FlashLoan(address indexed target, address indexed initiator, address indexed asset, uint256 amount, uint256 premium, uint16 referralCode)` |
| `0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286` | `LiquidationCall(address indexed collateralAsset, address indexed debtAsset, address indexed user, uint256 debtToCover, uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)` |
| `0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a` | `ReserveDataUpdated(address indexed reserve, uint256 liquidityRate, uint256 stableBorrowRate, uint256 variableBorrowRate, uint256 liquidityIndex, uint256 variableBorrowIndex)` |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` |

`Deposit` is the workhorse supply event (V2 name; V3's `Supply` has a **different** topic0 — do not look for `Supply` here). `Withdraw`, `LiquidationCall`, `ReserveDataUpdated`, and the collateral-enabled/disabled events share their **topic0 with both Aave V2 and V3** — disambiguate strictly by `(emitting LendingPool address, chain)`. `Borrow`/`Swap` carry `borrowRateMode`/`rateMode` (1 = stable, 2 = variable); stable rate exists in the fork.

### 1.2 gToken & debt tokens (per-reserve) — **V2 signatures; gToken ≠ debt token**

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address indexed from, uint256 value, uint256 index)` | **gToken** |
| `0x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2` | `Burn(address indexed from, address indexed target, uint256 value, uint256 index)` | **gToken** |
| `0x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee` | `Mint(address indexed from, address indexed onBehalfOf, uint256 value, uint256 index)` | **variableDebtToken** |
| `0x49995e5dd6158cf69ad3e9777c46755a1a826a446c6416992167462dad033b2a` | `Burn(address indexed user, uint256 amount, uint256 index)` | **variableDebtToken** |
| `0x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666` | `BalanceTransfer(address indexed from, address indexed to, uint256 value, uint256 index)` | gToken |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 (gToken; debt tokens emit on mint/burn) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | gToken (ERC-20) |
| `0xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1` | `BorrowAllowanceDelegated(address indexed fromUser, address indexed toUser, address indexed asset, uint256 amount)` | debt token (credit delegation) |

> **gToken `Mint`/`Burn` ≠ debt-token `Mint`/`Burn`** (unlike Aave V3 where they share a topic). gToken `Mint` = `0x4c209b5f`, varDebt `Mint` = `0x2f00e3cd`. Match on `(topic0, emitting address)`. The **gToken `Mint` topic0 `0x4c209b5f` also collides with Uniswap-V2 `Mint`** and Compound-fork `Mint(address,uint256,uint256)` — always pin the emitter. stableDebtToken has its own multi-arg `Mint`/`Burn` (rarely needed). Verified live on Optimism `grainUSDC` `0x7a0f…f0c0`: 31 gToken `Mint`, 12 `Burn`; varDebt `0xb271…d0bf`: 12 `Burn` (vDebt `Mint` 0 — no recent borrows).

### 1.3 LendingPoolConfigurator (risk admin)

| topic0 | Event |
|--------|-------|
| `0x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f` | `ReserveInitialized(address indexed asset, address indexed aToken, address stableDebtToken, address variableDebtToken, address interestRateStrategyAddress)` |
| `0xab2f7f9e5ca2772fafa94f355c1842a80ae6b9e41f83083098d81f67d7a0b508` | `BorrowingEnabledOnReserve(address indexed asset, bool stableRateEnabled)` |
| `0xe9a7e5fd4fc8ea18e602350324bf48e8f05d12434af0ce0be05743e6a5fdcb9e` | `BorrowingDisabledOnReserve(address indexed asset)` |
| `0x85dc710add8a0914461a7dc5a63f6fc529a7700f8c6089a3faf5e93256ccf12a` | `ReserveFrozen(address indexed asset)` |
| `0x838ecdc4709a31a26db48b0c853212cedde3f725f07030079d793fb071964760` | `ReserveUnfrozen(address indexed asset)` |
| `0x35b80cd8ea3440e9a8454f116fa658b858da1b64c86c48451f4559cefcdfb56c` | `ReserveActivated(address indexed asset)` |
| `0x6f60cf8bd0f218cabe1ea3150bd07b0b758c35c4cfdf7138017a283e65564d5e` | `ReserveDeactivated(address indexed asset)` |
| `0x637febbda9275aea2e85c0ff690444c8d87eb2e8339bbede9715abcc89cb0995` | `CollateralConfigurationChanged(address indexed asset, uint256 ltv, uint256 liquidationThreshold, uint256 liquidationBonus)` |
| `0x2694ccb0b585b6a54b8d8b4a47aa874b05c257b43d34e98aee50838be00d3405` | `ReserveFactorChanged(address indexed asset, uint256 factor)` |
| `0x2e73b7f1df792712003e6859f940c1e8711c3f1329474771fee71d2ec1163129` | `ReserveDecimalsChanged(address indexed asset, uint256 decimals)` |

> `CollateralConfigurationChanged` shares its topic0 with Aave V3's Configurator event of the same name — disambiguate by emitter. Granary V2 has **no** supply/borrow caps, e-mode, or isolation-mode events (those are V3-only).

### 1.4 Price oracle / LendingRateOracle

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x22c5b7b2d8561d39f7f210b6b326a1aa69f15311163082308ac4877db6339dc1` | `AssetSourceUpdated(address indexed asset, address indexed source)` | AaveOracle-equiv |
| `0xce7a780d33665b1ea097af5f155e3821b809ecbaa839d3b33aa83ba28168cefb` | `FallbackOracleUpdated(address indexed fallbackOracle)` | AaveOracle-equiv |

### 1.5 IncentivesController (Aave Distribution-Manager events; emitter = per-chain IC, §3–§8) — present but inert (§12.4)

| topic0 | Event |
|--------|-------|
| `0x2468f9268c60ad90e2d49edb0032c8a001e733ae888b3ab8e982edf535be1a76` | `RewardsAccrued(address indexed user, uint256 amount)` |
| `0x9310ccfcb8de723f578a9e4282ea9f521f05ae40dc08f3068dfad528a65ee3c7` | `RewardsClaimed(address indexed user, address indexed to, uint256 amount)` |
| `0x87fa03892a0556cb6b8f97e6d533a150d4d55fcbf275fff5fa003fa636bcc7fa` | `AssetConfigUpdated(address indexed asset, uint256 emission)` |
| `0x5777ca300dfe5bead41006fbce4389794dbc0ed8d6cccebfaf94630aa04184bc` | `AssetIndexUpdated(address indexed asset, uint256 index)` |
| `0xbb123b5c06d5408bbea3c4fef481578175cfb432e3b482c6186f02ed9086585b` | `UserIndexUpdated(address indexed user, address indexed asset, uint256 index)` |
| `0x4925eafc82d0c4d67889898eeed64b18488ab19811e61620f387026dec126a28` | `ClaimerSet(address indexed user, address indexed claimer)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Identical to Aave V2. `borrow`/`repay`/`withdraw`/`flashLoan`/`liquidationCall` **share selectors with Aave V3** (same signatures) — disambiguate by Pool address + chain.

### 2.1 LendingPool — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe8eda9df` | `deposit(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)` | Emits `Deposit`. **V2 supply selector** (V3 renamed it `supply` `0x617ba037`). |
| `0x69328dec` | `withdraw(address asset, uint256 amount, address to)` → `uint256` | `amount = type(uint256).max` = full balance. shared w/ V3. |
| `0xa415bcad` | `borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)` | mode 1=stable, 2=variable. shared w/ V3. |
| `0x573ade81` | `repay(address asset, uint256 amount, uint256 rateMode, address onBehalfOf)` → `uint256` | shared w/ V3. |
| `0x94ba89a2` | `swapBorrowRateMode(address asset, uint256 rateMode)` | stable↔variable. |
| `0xcd112382` | `rebalanceStableBorrowRate(address asset, address user)` | |
| `0x5a3b74b9` | `setUserUseReserveAsCollateral(address asset, bool useAsCollateral)` | shared w/ V3. |
| `0x00a718a9` | `liquidationCall(address collateralAsset, address debtAsset, address user, uint256 debtToCover, bool receiveAToken)` | Emits `LiquidationCall`. **Present in the V2 impl dispatcher** (unlike v3.4). Routes to `LendingPoolCollateralManager` via delegatecall. |
| `0xab9c4b5d` | `flashLoan(address receiverAddress, address[] assets, uint256[] amounts, uint256[] modes, address onBehalfOf, bytes params, uint16 referralCode)` | shared w/ V3. |

### 2.2 LendingPool — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xbf92857c` | `getUserAccountData(address user)` | `(totalCollateralETH, totalDebtETH, availableBorrowsETH, currentLiquidationThreshold, ltv, healthFactor)` — **values in ETH/wei (1e18), NOT USD.** HF in 1e18 (`<1e18` = liquidatable). |
| `0x35ea6a75` | `getReserveData(address asset)` | Full V2 `ReserveData` struct: word 7 = gToken, 8 = stableDebtToken, 9 = variableDebtToken, 10 = interestRateStrategy. |
| `0xd15e0053` | `getReserveNormalizedIncome(address asset)` | ray (27-dec) supply index. |
| `0x386497fd` | `getReserveNormalizedVariableDebt(address asset)` | ray borrow index. |
| `0xc44b11f7` | `getConfiguration(address asset)` | Packed reserve config bitmap. |
| `0x4417a583` | `getUserConfiguration(address user)` | Packed user collateral/borrow bitmap. |
| `0xd1946dbc` | `getReservesList()` | `address[]` of reserve underlyings. |
| `0xfe65acfe` | `getAddressesProvider()` | The owning `LendingPoolAddressesProvider`. |
| `0x5c975abb` | `paused()` | `bool`. |

### 2.3 gToken / debt token

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1da24f3e` | `scaledBalanceOf(address user)` | **Use for accounting** — `balanceOf` rebases every block. |
| `0xb1bf962d` | `scaledTotalSupply()` | |
| `0xb16a19de` | `UNDERLYING_ASSET_ADDRESS()` | Underlying reserve token. |
| `0xae167335` | `RESERVE_TREASURY_ADDRESS()` | gToken only. |
| `0x75d26413` | `getIncentivesController()` | Returns the per-chain IC (inert — §12.4). |
| `0xc04a8a10` | `approveDelegation(address delegatee, uint256 amount)` | debt token — credit delegation. |
| `0x6bd76d24` | `borrowAllowance(address fromUser, address toUser)` | debt token. |
| `0x70a08231` / `0x18160ddd` | `balanceOf` / `totalSupply` | **Rebasing** — change every block. |
| `0x06fdde03` / `0x95d89b41` | `name()` / `symbol()` | gToken name = "Granary DAI", symbol = **`grainDAI`** (prefix `grain`). |

### 2.4 Oracle / registry / data provider

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xb3596f07` | `getAssetPrice(address asset)` → `uint256` | AaveOracle-equiv (**base = ETH/wei**, not USD). |
| `0xfca513a8` | `getPriceOracle()` → `address` | LendingPoolAddressesProvider. |
| `0x0261bf8b` | `getLendingPool()` → `address` | LendingPoolAddressesProvider. |
| `0x85c858b1` | `getLendingPoolConfigurator()` → `address` | LendingPoolAddressesProvider. |
| `0x712d9171` | `getLendingPoolCollateralManager()` → `address` | LendingPoolAddressesProvider. |
| `0x568ef470` | `getMarketId()` → `string` | LendingPoolAddressesProvider (= "Granary Genesis Market"). |
| `0x21f8a721` | `getAddress(bytes32 id)` → `address` | DataProvider id = `0x0100…0000`. |
| `0x365ccbbf` | `getAddressesProvidersList()` → `address[]` | LendingPoolAddressesProviderRegistry. |
| `0xd2493b6c` | `getReserveTokensAddresses(address asset)` | AaveProtocolDataProvider → `(gToken, stableDebt, variableDebt)`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` / `eth_call` on `https://ethereum-rpc.publicnode.com` (2026-06-08). Pool wiring confirmed: `Registry.getAddressesProvidersList()` → `[0xedc8…00fc]`; `Provider.getLendingPool()` → Pool; `Provider.getMarketId()` = **"Granary Genesis Market"**. **Market is dormant** (0 `Deposit` in ~450k recent blocks).

### 3.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| LendingPoolAddressesProviderRegistry | `0x5C93B799D31d3d6a7C977f75FDB88d069565A55b` | Top-level registry (**same literal on Base**, different chain). |
| **LendingPoolAddressesProvider** | `0xedC83309549E36f3C7FD8C2C5C54B4c8e5fA00fc` | Per-market registry / source of truth (**shared addr w/ Base + Avax**). |
| **LendingPool** (proxy) | `0xB702cE183b4E1Faa574834715E5D4a6378D0eEd3` | Main entrypoint; emits §1.1 events (**shared addr w/ Base + Avax**). |
| LendingPool impl | `0xc01a7ad7Fb8a085a3Cc16BE8eaa10302c78A1783` | Read live via EIP-1967 slot. |
| **LendingPoolConfigurator** (proxy) | `0xc534F577c0E6C46b27FdCA6d27D132C543b0D61C` | Risk admin; emits §1.3 (**shared addr w/ Base + Avax**). |
| Configurator impl | `0x37133A8dCA96400c249102E59B11e25b0F663Ee0` | |
| LendingPoolCollateralManager | `0xf6d1Cabe63237970b0E5fEC45afC5b2C1312D8E0` | Liquidation logic (delegatecall target). |
| **Price oracle** | `0x9546F673ef71FF666ae66d01Fd6E7C6Dae5a9995` | AaveOracle-equiv (ETH-base, 1e18). |
| LendingRateOracle | `0x6E20E155819F0Ee08D1291B0b9889B0E011B8224` | Stable-rate reference oracle. |
| **AaveProtocolDataProvider** | `0x33C62Bc416309F010C4941163abea3725E4645bF` | Read helper (reserve/user data). |
| IncentivesController | `0xC043BA54F34C9fb3a0B45d22e2Ef1f171272Bc9D` | Wired into gTokens; inert on-chain (§12.4). |
| PoolAdmin | `0xa15Aa70706d56AC83491AB90Ea6A3eC3F47639aB` | Governance executor (from `Provider.getPoolAdmin()`). |
| EmergencyAdmin | `0x4A0241978a0fd92dd0Cd3b183ab50fA4D66238c3` | Guardian (pause). |
| **GRAIN** (reward/gov token) | `0xf88baf18FaB7e330fa0C4F83949E23F52FECECce` | ERC-20; chain-unique address. |

### 3.2 Reserves (5) — underlying → gToken / variableDebtToken / stableDebtToken

gToken impl = `0x8429d0afADE80498eAdB9919e41437a14d45A00b`; variableDebt impl = `0x8e82618E67783D6595cd02CDe94c11A7Ce894d45`; stableDebt impl = `0xd2abc5d7841D49C40fD35A1ec832ee1daCc8d339` (read live via EIP-1967 slot).

| Symbol | Underlying | gToken | variableDebtToken |
|--------|-----------|--------|-------------------|
| DAI | `0x6B175474E89094C44Da98b954EedeAC495271d0F` | `0xe7334Ad0e325139329E747cF2Fc24538dD564987` | `0xe5415Fa763489C813694d7a79D133f0A7363310C` |
| USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | `0x02cD18c03b5b3F250d2B29C87949CDAb4Ee11488` | `0xbce07537DF8aD5519C1D65e902e10aA48af83d88` |
| USDT | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | `0x9c29a8eC901DBec4fFf165cD57D4f9E03D4838f7` | `0x06d38C309d1Dc541A23b0025B35d163C25754288` |
| WBTC | `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599` | `0x272CFCcefBefBE1518cd87002A8F9DfD8845A6c4` | `0x5EEA43129024EeE861481f32c2541B12dDD44C08` |
| WETH | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` | `0x58254000eE8127288387b04ce70292B56098D55C` | `0x05249f9Ba88F7d98fE21A8f3C460F4746689aea5` |

(stableDebt tokens, rarely needed: DAI `0xc407…98c9`, USDC `0x73c1…e1a7`, USDT `0x6f66…eb70`, WBTC `0x09ab…a7f8`, WETH `0xc73a…db24`.)

---

## 4. Addresses — Base (chain ID 8453)

All verified via `eth_getCode` on `https://base-rpc.publicnode.com` (2026-06-08). **Base reuses the shared ETH/Avax/BNB provider, pool, configurator, and gToken/debt instance addresses** (CREATE2-deterministic; the same cluster is also live on BNB — §8.B), but has a **chain-unique oracle, collateral manager, data provider, and admins**. **No GRAIN token on Base.**

| Role | Address |
|------|---------|
| LendingPoolAddressesProviderRegistry | `0x5C93B799D31d3d6a7C977f75FDB88d069565A55b` |
| **LendingPoolAddressesProvider** | `0xedC83309549E36f3C7FD8C2C5C54B4c8e5fA00fc` (shared literal — key on chain) |
| **LendingPool** (proxy) | `0xB702cE183b4E1Faa574834715E5D4a6378D0eEd3` (shared literal — key on chain) |
| LendingPoolConfigurator (proxy) | `0xc534F577c0E6C46b27FdCA6d27D132C543b0D61C` |
| LendingPoolCollateralManager | `0x352bC36e5552A364d4D2aa01c8C12bec11C6cc11` |
| **Price oracle** | `0x5a3423210536d930150080f699248EdEbC65E2B4` (shared literal w/ Avax) |
| LendingRateOracle | `0x8429d0afADE80498eAdB9919e41437a14d45A00b` (shared literal w/ Avax) |
| AaveProtocolDataProvider | `0xeD984A0E9C12Ee27602314191fc4487a702bb83f` (shared literal w/ Avax) |
| IncentivesController | `0xC043BA54F34C9fb3a0B45d22e2Ef1f171272Bc9D` (inert — §12.4) |
| PoolAdmin | `0xbDb399Dd6f66609303D906D90765E432C04f77A4` |
| EmergencyAdmin | `0xB2Adf47Ecbc8236Ff2097075a3F080DFD79b583A` |

### 4.1 Base reserves (7)

| Symbol | Underlying | gToken | variableDebtToken |
|--------|-----------|--------|-------------------|
| DAI | `0x50c5725949A6F0c72E6c4a641F24049A917DB0Cb` | `0xe7334Ad0e325139329E747cF2Fc24538dD564987` | `0xe5415Fa763489C813694d7a79D133f0A7363310C` |
| USDbC | `0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA` | `0x02cD18c03b5b3F250d2B29C87949CDAb4Ee11488` | `0xbce07537DF8aD5519C1D65e902e10aA48af83d88` |
| WETH | `0x4200000000000000000000000000000000000006` | `0x9c29a8eC901DBec4fFf165cD57D4f9E03D4838f7` | `0x06d38C309d1Dc541A23b0025B35d163C25754288` |
| cbETH | `0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22` | `0x272CFCcefBefBE1518cd87002A8F9DfD8845A6c4` | `0x5EEA43129024EeE861481f32c2541B12dDD44C08` |
| cbBTC | `0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf` | `0x58254000eE8127288387b04ce70292B56098D55C` | `0x05249f9Ba88F7d98fE21A8f3C460F4746689aea5` |
| AERO | `0x940181a94A35A4569E4529A3CDfB74e38FD98631` | `0xe3F709397E87032E61f4248F53ee5C9a9aBb6440` | `0x083E519E76Fe7e68C15A6163279eaAf87e2ADdaE` |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | `0xC17312076f48764D6b4d263EFDD5A30833e311DC` | `0x3f332f38926b809670b3cAc52DF67706856A1555` |

---

## 5. Addresses — Avalanche C-Chain (chain ID 43114)

All verified via `eth_getCode` on `https://avalanche-c-chain-rpc.publicnode.com` (2026-06-08). **Avax reuses the shared ETH/Base/BNB provider, pool, configurator, gToken/debt addresses, and the Base oracle/rate-oracle/data-provider literals** (the same cluster is also live on BNB — §8.B), with chain-unique collateral manager + admins.

| Role | Address |
|------|---------|
| LendingPoolAddressesProviderRegistry | `0xC043BA54F34C9fb3a0B45d22e2Ef1f171272Bc9D` |
| **LendingPoolAddressesProvider** | `0xedC83309549E36f3C7FD8C2C5C54B4c8e5fA00fc` |
| **LendingPool** (proxy) | `0xB702cE183b4E1Faa574834715E5D4a6378D0eEd3` |
| LendingPoolConfigurator (proxy) | `0xc534F577c0E6C46b27FdCA6d27D132C543b0D61C` |
| LendingPoolCollateralManager | `0x4d8d90faF90405b9743Ce600e98a2Aa8cDF579A0` |
| **Price oracle** | `0x5a3423210536d930150080f699248EdEbC65E2B4` |
| LendingRateOracle | `0x8429d0afADE80498eAdB9919e41437a14d45A00b` |
| AaveProtocolDataProvider | `0xeD984A0E9C12Ee27602314191fc4487a702bb83f` |
| IncentivesController | `0xddE5Dc81e40799750B92079723Da2acAf9e1C6D6` (inert — §12.4) |
| PoolAdmin | `0x060E95881F4FC62F4146eBe53535267d9FE33dc7` |
| EmergencyAdmin | `0x79f15A2A0c3F60B392234f30D368fD93a12513D4` |
| **GRAIN** | `0x9DF4Ac62F9E435DBcD85E06C990a7F0eA32739a9` |

### 5.1 Avalanche reserves (7) — bridged `.e` assets

| Symbol | Underlying | gToken | variableDebtToken |
|--------|-----------|--------|-------------------|
| DAI.e | `0xd586E7F844cEa2F87f50152665BCbc2C279D8d70` | `0xe7334Ad0e325139329E747cF2Fc24538dD564987` | `0xe5415Fa763489C813694d7a79D133f0A7363310C` |
| USDC.e | `0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664` | `0x02cD18c03b5b3F250d2B29C87949CDAb4Ee11488` | `0xbce07537DF8aD5519C1D65e902e10aA48af83d88` |
| USDT.e | `0xc7198437980c041c805A1EDcbA50c1Ce5db95118` | `0x9c29a8eC901DBec4fFf165cD57D4f9E03D4838f7` | `0x06d38C309d1Dc541A23b0025B35d163C25754288` |
| WBTC.e | `0x50b7545627a5162F82A992c33b87aDc75187B218` | `0x272CFCcefBefBE1518cd87002A8F9DfD8845A6c4` | `0x5EEA43129024EeE861481f32c2541B12dDD44C08` |
| WETH.e | `0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB` | `0x58254000eE8127288387b04ce70292B56098D55C` | `0x05249f9Ba88F7d98fE21A8f3C460F4746689aea5` |
| WAVAX | `0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7` | `0xe3F709397E87032E61f4248F53ee5C9a9aBb6440` | `0x083E519E76Fe7e68C15A6163279eaAf87e2ADdaE` |
| XAVA | `0xd1c3f94DE7e5B45fa4eDBBA472491a9f4B166FC4` | `0xC17312076f48764D6b4d263EFDD5A30833e311DC` | `0x3f332f38926b809670b3cAc52DF67706856A1555` |

---

## 6. Addresses — Arbitrum One (chain ID 42161)

All verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com` (2026-06-08). **All addresses chain-unique** (no sharing with the ETH/Base/Avax/BNB cluster; the shared `0xb702…`/`0xedc8…` literals return empty `eth_getCode` here). Note: the literal `0xedc8…00fc` happens to host an unrelated non-Granary stub on Arbitrum (impl slot `0x0`, `getMarketId()` reverts) — it is *not* the Granary provider; the real ARB provider is `0x642c…1563`.

| Role | Address |
|------|---------|
| LendingPoolAddressesProviderRegistry | `0x512f582fFCCF3C14bD872152EeAe60866dCB2A1e` |
| **LendingPoolAddressesProvider** | `0x642cC899652b068d1Bed786C4b060Ec1027d1563` |
| **LendingPool** (proxy) | `0x102442A3BA1e441043154Bc0B8a2E2FB5e0F94A7` |
| LendingPool impl | `0xf88baf18FaB7e330fa0C4F83949E23F52FECECce` (note: literal collides with the ETH GRAIN token — different chain/role) |
| LendingPoolConfigurator (proxy) | `0x0DBf9689FaF89e91186BBcCc3CE5A9b5ae3F2f78` |
| LendingPoolCollateralManager | `0xC2cda52c7DC64d4FF01B58B0981E1FCdD94B16C2` |
| **Price oracle** | `0xe12E084fc4550387cb2B252b5F289bA38b755354` |
| LendingRateOracle | `0xB839c82630a36b5F7a5320cd0814886bf4900F1e` |
| AaveProtocolDataProvider | `0x96bcFB86f1bFf315c13E00D850e2faEA93CCD3e7` |
| IncentivesController | `0x7A191973eaf8cdcc4De683D10c1e11C5a5BC717d` (inert — §12.4) |
| PoolAdmin | `0x4f8b86FF37C5cDB8df2BfACd481266Cb91Edd975` |
| EmergencyAdmin | `0x195e8eA61621D0D2bF6Ad6Df8eA3835AC9012956` |
| **GRAIN** | `0x80bb30D62a16e1f2084dEAE84dC293531C3aC3A1` |

### 6.1 Arbitrum reserves (9)

| Symbol | Underlying | gToken | variableDebtToken |
|--------|-----------|--------|-------------------|
| DAI | `0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1` | `0xfc2EAc1AEB490d5fF727E659273c8afC5dd2B0bb` | `0xfDf4ee30CEFF9a6253D4EB43257AbC361433Bf04` |
| USDC.e | `0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8` | `0x6c4Cb1115927d50E495e554D38b83f2973f05361` | `0xe2b1674F85c8a1729567F38Cb502088c6E147938` |
| USD₮0 (USDT) | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` | `0x66dDd8f3a0c4cEb6a324376eA6c00B4C8c1bB3D9` | `0x3e2DEeda33D8bA579430F38868dB3eD0E2394576` |
| WBTC | `0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f` | `0x731E2246a0c67b1B19188C7019094Ba9f107404f` | `0x8dAeC4344A99f575B13dE9F16C53d5bf65E75a42` |
| WETH | `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` | `0x712f1955E5Ed3F7A5aC7b5E4C480DB8eDf9b3FD7` | `0xC5e029c1097d9585629aE4bdF74C37182eC8d1bA` |
| ARB | `0x912CE59144191C1204E64559FE8253a0e49E6548` | `0x8B9a4DEd05ad8c3aB959980538437b0562DbB129` | `0x5935530b52332D1030d98c1ce06f2943e06B75aD` |
| USDC | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | `0x2af47E1786C1AF2dEBeE2DEdE590a0D00005129B` | `0x86547Cb041C7A98576dA7FA87aCD6eAC66c51e0c` |
| wstETH | `0x5979D7b546E38E414F7E9822514be443A4800529` | `0x93E5E80029b36e5E5e75311cf50EBC60995F9ea6` | `0x5d13ffBc005a2BDD16F3c50e527d42c387759299` |
| rETH | `0xEC70Dcb4A1EFa46b8F2D97C310C9c4790ba5ffA8` | `0x883B786504A2c6Bfa2C9e578E5d1752eCBc24DEe` | `0x458d60c27B433a157462C7959e2a103389De3FCE` |

---

## 7. Addresses — Optimism (chain ID 10) — most active market

All verified via `eth_getCode` on `https://optimism-rpc.publicnode.com` (2026-06-08). **All addresses chain-unique.** Live event activity confirmed here (§12). Market name "Granary Genesis Market".

| Role | Address |
|------|---------|
| LendingPoolAddressesProviderRegistry | `0x872B9e8aea5D65Fbf29b8B05bfA4AA3fE94cC11f` |
| **LendingPoolAddressesProvider** | `0xdDE5Dc81e40799750B92079723Da2acAf9e1C6D6` |
| **LendingPool** (proxy) | `0x8FD4aF47E4E63d1D2D45582c3286b4BD9Bb95DfE` |
| LendingPool impl | `0x72fAd09e3da8cEC0e975Bf253c1E5EAfdB927Fec` |
| LendingPoolConfigurator (proxy) | `0x494Bf60B3b58664D5A674E692C718D33687E663a` |
| LendingPoolCollateralManager | `0x025D9D36c616946530fF8eA32D912ABf73170947` |
| **Price oracle** | `0x9AEEfeF549323511E027d70562F0c7eDcDeB294c` |
| LendingRateOracle | `0x158B0b1414f153E58f8aCAc50e777FEec234dd9D` |
| AaveProtocolDataProvider | `0x9546F673ef71FF666ae66d01Fd6E7C6Dae5a9995` |
| IncentivesController | `0x6a0406B8103Ec68EE9A713A073C7bD587c5e04aD` (inert — §12.4) |
| PoolAdmin | `0xF6fd4C5cB0d2A92FBf8E08e6c2a27ca7Fe39FDCC` |
| EmergencyAdmin | `0x581C4a57197f0fc6Ff9340267DC2f82F4a2fE1c0` |
| **GRAIN** | `0xfd389Dc9533717239856190F42475d3f263a270d` |

### 7.1 Optimism reserves (11)

| Symbol | Underlying | gToken | variableDebtToken |
|--------|-----------|--------|-------------------|
| DAI | `0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1` | `0x18d2B18Af9a1F379025f46b8AeB4af75F6642C9F` | `0xbabDD3e2231990B1f47844536e19b2f1CC1d5077` |
| USDC.e | `0x7F5c764cBc14f9669B88837ca1490cCa17c31607` | `0x7A0FDDBA78ff45d353B1630b77f4D175a00Df0C0` | `0xb271973B367e50fcde5EE5e426944C37045Dd0BF` |
| USDT | `0x94b008aA00579c1307B0EF2c499aD98a8ce58e58` | `0x4e7849f846f8CddAF37c72065B65EC22cECEE109` | `0x5c4ACFcbA420f8A0E14B7aADA3D8726452642FBB` |
| WBTC | `0x68f180fcCe6836688e9084f035309E29Bf0A2095` | `0xBD3DBF914f3e9C3133a815b04A4d0E5930957cB9` | `0x62BbFaef552522bE2bDA7F69cc5B2c36C1879600` |
| WETH | `0x4200000000000000000000000000000000000006` | `0xfF94cC8e2C4b17e3cC65d7b83C7E8c643030D936` | `0x0a05D3D77b66Af45233599FE4F5558326E4Ad269` |
| OP | `0x4200000000000000000000000000000000000042` | `0x30091E843dEB234EbB45c7e1da4bbC4C33b3F0b4` | `0xB1aFe7c8d6D94e8EF04ab3C99848A3b21a33d9eF` |
| sUSD | `0x8c6f28f2F1A3C87F0f938b96d27520d9751ec8d9` | `0x8aaa9D29305d331aE67AD65495b9e22Cf98F9035` | `0xC0031304549E494f1f48a9AC568242b1A6cA1804` |
| BAL | `0xFE8B128bA8C78aabC59d4c64cEE7fF28e9379921` | `0x7Fb37AE8be7f6177F265E3fF6D6731672779eb0b` | `0x49E03C399F0f84083d6F6549383fc80d11701bD4` |
| SNX | `0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4` | `0xa73B7C26ef3221Bf9eA7E5981840519427F7Dcaf` | `0x9dD559b1D7454979b1699d710885ba5C658277E3` |
| wstETH | `0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb` | `0x1A7450AacC67d90AFb9e2C056229973354Cc8987` | `0xd0260eA91b263619a27EfeEf512a04fb482915E7` |
| cbETH | `0xadDb6A0412DE1BA0F936DCaeb8Aaa24578dcF3B2` | `0xc69eC3664687659dC541CD88eF9D52a470b93FBe` | `0xBed938b24e2432168Cb1c09f10ec9609bF5BADb0` |

---

## 8. Addresses — BNB Smart Chain (chain ID 56) — **two parallel markets**

All verified via `eth_getCode` / `eth_call` on `https://bsc-rpc.publicnode.com` (2026-06-08). **BNB hosts TWO independent "Granary Genesis Market" deployments with the SAME 6 reserve underlyings (DAI/USDC/USDT/BTCB/ETH/WBNB):**

- **Cluster A — BNB-unique** (the only one in the on-chain `LendingPoolAddressesProviderRegistry` `0x7c8E…bbDa`, and the one the DefiLlama adapter walks). Provider `0x12c2…dFBf` → Pool `0x7171…9032`. Chain-unique addresses, table §8.A.
- **Cluster B — the shared ETH/Base/Avax cluster** (provider `0xedC8…00fc` → Pool `0xb702…eed3`, configurator `0xc534…d61c`, same CREATE2 gToken/debt literals as ETH/Base/Avax). This cluster is live on BNB — `getMarketId()` = "Granary Genesis Market", `getLendingPool().getReservesList()` returns the same 6 assets, Pool impl `0xc01a7ad7…` (same as ETH). It is **NOT** registered in the BNB registry but is fully deployed. Table §8.B.

Both clusters are **dormant** in recent windows (0 `Deposit`/`Withdraw`/`ReserveDataUpdated` in the last ~200k blocks). Monitor both, keyed on the specific Pool address.

### 8.A Cluster A (BNB-unique) — core

| Role | Address |
|------|---------|
| LendingPoolAddressesProviderRegistry | `0x7c8E7536c5044E1B3693eB564C6dE3a3CE58bbDa` |
| **LendingPoolAddressesProvider** | `0x12c26138B666360Ab2b7A1B149DF9CF6642CdFBf` |
| **LendingPool** (proxy) | `0x7171054f8d148Fe1097948923c91A6596fc29032` |
| LendingPool impl | `0xe1537FEF008944D1c8dCAfBace4dC76d31d22dC5` |
| LendingPoolConfigurator (proxy) | `0xd057DD41F71397854D00050dCB634261cE7e0893` |
| LendingPoolCollateralManager | `0xf957262DB8B35181A0Ab8F034ec8CE73a7531F9b` |
| **Price oracle** | `0x417cA1091Fa4c329cEe19452851dFF46902440a5` |
| LendingRateOracle | `0x96bcFB86f1bFf315c13E00D850e2faEA93CCD3e7` |
| AaveProtocolDataProvider | `0x7Fb479624cA336ba8F2dC66439F8683330eE2880` |
| IncentivesController | `0x250b47F097Ec51225ece85b13273b70A4233e1e9` (inert — §12.4) |
| PoolAdmin | `0x0bA2504eaD26F10dec40Cf277Bb8d5b2338BAE2A` |
| EmergencyAdmin | `0xe0919D23fECc572a7eABc12dB85cAD2B54a078FD` |
| **GRAIN** | `0x8f87a7d376821C7B2658a005AAf190EC778bf37a` |

Cluster A reserves (6):

| Symbol | Underlying | gToken | variableDebtToken |
|--------|-----------|--------|-------------------|
| DAI | `0x1AF3F329e8BE154074d8769D1FFa4eE058B1DBc3` | `0x6055558D88DDE78dF51bF9e90bDD225D525cf80B` | `0xa0758cd24CF68f486f3F6D96e833680d4971CCf8` |
| USDC | `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` | `0xe37bBfdD50b715D49df6E596f9248bfE6b967cd7` | `0x2f4e44316Af0CaC2154F95acca305082A2382e98` |
| USDT | `0x55d398326f99059fF775485246999027B3197955` | `0x7e25119b5E52C32970161F1e0dA3E66BBeF100F1` | `0x573BcE236692B48F5fAa07947E78C1e282E16C28` |
| BTCB | `0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c` | `0x6c578574a5400c5E45F18BE65227cfC2a64d94f7` | `0x7F459f3c6D068168EF791746602cA29180b5D03f` |
| ETH | `0x2170Ed0880ac9A755fd29B2688956BD959F933F8` | `0x2A050a0d74C9a12bA44bD2acA9d7d7d1bdF988E9` | `0xa7eDE8701d7daC898B04ddf27c781b4eB961443f` |
| WBNB | `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` | `0x70Ad5e32E6Ea548DCe7D331b447C2791Cf695a98` | `0x839c8cA0873DE853c5f8DF1Ef3E82e9da398abf6` |

### 8.B Cluster B (the shared ETH/Base/Avax cluster, also live on BNB) — core

| Role | Address |
|------|---------|
| **LendingPoolAddressesProvider** | `0xedC83309549E36f3C7FD8C2C5C54B4c8e5fA00fc` (shared literal — key on chain) |
| **LendingPool** (proxy) | `0xB702cE183b4E1Faa574834715E5D4a6378D0eEd3` (shared literal; impl `0xc01a7ad7…`) |
| LendingPoolConfigurator (proxy) | `0xc534F577c0E6C46b27FdCA6d27D132C543b0D61C` (shared literal) |

Cluster B reserves (6) — same CREATE2 gToken/debt literals as ETH/Base/Avax:

| Symbol | Underlying | gToken | variableDebtToken |
|--------|-----------|--------|-------------------|
| DAI | `0x1AF3F329e8BE154074d8769D1FFa4eE058B1DBc3` | `0xe7334Ad0e325139329E747cF2Fc24538dD564987` | `0xe5415Fa763489C813694d7a79D133f0A7363310C` |
| USDC | `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` | `0x02cD18c03b5b3F250d2B29C87949CDAb4Ee11488` | `0xbce07537DF8aD5519C1D65e902e10aA48af83d88` |
| USDT | `0x55d398326f99059fF775485246999027B3197955` | `0x9c29a8eC901DBec4fFf165cD57D4f9E03D4838f7` | `0x06d38C309d1Dc541A23b0025B35d163C25754288` |
| BTCB | `0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c` | `0x272CFCcefBefBE1518cd87002A8F9DfD8845A6c4` | `0x5EEA43129024EeE861481f32c2541B12dDD44C08` |
| ETH | `0x2170Ed0880ac9A755fd29B2688956BD959F933F8` | `0x58254000eE8127288387b04ce70292B56098D55C` | `0x05249f9Ba88F7d98fE21A8f3C460F4746689aea5` |
| WBNB | `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` | `0xe3F709397E87032E61f4248F53ee5C9a9aBb6440` | `0x083E519E76Fe7e68C15A6163279eaAf87e2ADdaE` |

---

## 9. Granary is NOT on Polygon PoS (chain ID 137)

Verified on `https://polygon-bor-rpc.publicnode.com` (2026-06-08): **no `LendingPoolAddressesProviderRegistry`, no provider, no pool.** The DefiLlama `the-granary` adapter has **no Polygon entry**, and every Granary anchor address returns empty `eth_getCode` on Polygon:

| Address (Granary on another chain) | Polygon `eth_getCode` |
|---|---|
| Provider `0xedc8…00fc` (ETH/Base/Avax/BNB) | `0x` (absent) |
| Pool `0xb702…eed3` (ETH/Base/Avax/BNB) | `0x` (absent) |
| Registry `0x5C93…A55b` (ETH/Base) | `0x` (absent) |
| Registry `0x872B…cC11f` (OP) | `0x` (absent) |

Do not author Granary monitors for Polygon. (Aave's *own* V2 market does exist on Polygon — see [aave/v2.md](../aave/v2.md) §4 — but that is Aave, not Granary.)

---

## 10. Off-target deployments (reference anchors, outside the 7-chain scope)

Granary also runs on chains the user did not request. Recorded here for completeness; **not** part of the monitoring set. (All are EVM and on-chain-verifiable on their own RPCs.)

| Chain | ID | LendingPoolAddressesProviderRegistry | GRAIN token |
|---|---|---|---|
| Fantom Opera | 250 | `0x773E0277667F0c38d3Ca2Cf771b416bfd065da83` | `0x02838746d9E1413e07eE064fcBaDA57055417f21` |
| Metis Andromeda | 1088 | `0x37133A8dCA96400c249102E59B11e25b0F663Ee0` | — |
| Linea | 59144 | `0xd539294830EaF5C22467CE6e085Ae4E02861845A` | — |

Fantom was Granary's original home chain (DefiLlama still lists GRAIN's canonical chain as Fantom). Metis is its second-largest market by TVL. The registries above are the canonical entries in the DefiLlama `the-granary` adapter; walk `getAddressesProvidersList()` on each to reach that chain's pool. **GRAIN is also LayerZero-bridged** across chains (chain-unique addresses; see §3.1/§5/§6/§7/§8 for the in-scope ones).

---

## 11. Cross-chain summary

Presence matrix. Cells = address (truncated) or — for "not deployed". **Note the shared `0xb702…`/`0xedc8…` cluster spans ETH/Base/Avax AND BNB** (shared provider/pool/configurator/gToken literals); **only OP and ARB diverge entirely**. BNB carries this shared cluster *in addition to* its own unique cluster — two markets (§8).

| Chain | ID | LendingPool | AddressesProvider | DataProvider | Price oracle | GRAIN | Reserves |
|---|---|---|---|---|---|---|---|
| Ethereum | 1 | `0xb702…eed3` | `0xedc8…00fc` | `0x33C6…45bF` | `0x9546…9995` | `0xf88b…ECce` | 5 (dormant) |
| Base | 8453 | `0xb702…eed3` | `0xedc8…00fc` | `0xeD98…b83f` | `0x5a34…E2B4` | — | 7 |
| Avalanche | 43114 | `0xb702…eed3` | `0xedc8…00fc` | `0xeD98…b83f` | `0x5a34…E2B4` | `0x9DF4…39A9` | 7 |
| Arbitrum One | 42161 | `0x1024…94A7` | `0x642c…1563` | `0x96bc…D3e7` | `0xe12E…5354` | `0x80bb…c3A1` | 9 |
| Optimism | 10 | `0x8FD4…95DfE` | `0xdDE5…C6D6` | `0x9546…9995` | `0x9AEE…294c` | `0xfd38…270d` | 11 (active) |
| BNB (cluster A, registered) | 56 | `0x7171…9032` | `0x12c2…dFBf` | `0x7Fb4…2880` | `0x417c…40a5` | `0x8f87…f37a` | 6 |
| BNB (cluster B, shared) | 56 | `0xb702…eed3` | `0xedc8…00fc` | — | — | — | 6 |
| **Polygon PoS** | 137 | — | — | — | — | — | **not deployed** |

> The OP `AaveProtocolDataProvider` literal `0x9546…9995` equals the **Ethereum price-oracle** literal — pure address coincidence across chains/roles. Always key on `(chainId, address, role)`.

---

## 12. Proxies (old & new)

Every Granary core/token contract is Aave's **`InitializableImmutableAdminUpgradeabilityProxy`**: the **EIP-1967 implementation slot `0x360894…382bbc`** holds the live logic address, while the **admin is immutable** (compiled into bytecode), so the EIP-1967 **admin slot `0xb53127…5d6103` reads `0x0`** on every Granary proxy. The `LendingPoolAddressesProvider`, the price oracle, the `LendingRateOracle`, and the `AaveProtocolDataProvider` are **plain (non-proxy) contracts** (impl slot `0x0`).

| Contract | Pattern | Detection | Upgrade authority |
|----------|---------|-----------|-------------------|
| LendingPool | EIP-1967 (immutable admin) | impl slot non-zero; admin slot `0x0` | `AddressesProvider.setLendingPoolImpl()` |
| LendingPoolConfigurator | EIP-1967 (immutable admin) | impl slot non-zero | `AddressesProvider.setLendingPoolConfiguratorImpl()` |
| gToken / variableDebt / stableDebt | EIP-1967 (admin = Configurator) | impl slot non-zero | `LendingPoolConfigurator.updateAToken()` etc. |
| IncentivesController | proxy template | impl slot **`0x0`** (unset) — §12.4 | n/a |
| LendingPoolAddressesProvider | **non-proxy** ownable registry | impl slot `0x0` | the stable anchor |
| Price oracle / LendingRateOracle | **non-proxy** | impl slot `0x0` | replaced via `setPriceOracle()` |
| AaveProtocolDataProvider | **non-proxy** | impl slot `0x0` | redeployed + re-registered |
| LendingPoolCollateralManager | **non-proxy** logic (delegatecall target) | impl slot `0x0` | swapped via provider |

### 12.1 Live implementations (read 2026-06-08)

| Chain | LendingPool proxy | Live Pool impl |
|---|---|---|
| Ethereum | `0xb702…eed3` | `0xc01a7ad7Fb8a085a3Cc16BE8eaa10302c78A1783` |
| Optimism | `0x8FD4…95DfE` | `0x72fAd09e3da8cEC0e975Bf253c1E5EAfdB927Fec` |
| Arbitrum | `0x1024…94A7` | `0xf88baf18FaB7e330fa0C4F83949E23F52FECECce` |
| BNB | `0x7171…9032` | `0xe1537FEF008944D1c8dCAfBace4dC76d31d22dC5` |

ETH token impls: gToken `0x8429d0afADE80498eAdB9919e41437a14d45A00b`, variableDebt `0x8e82618E67783D6595cd02CDe94c11A7Ce894d45`, stableDebt `0xd2abc5d7841D49C40fD35A1ec832ee1daCc8d339`. Configurator impl (ETH) `0x37133A8dCA96400c249102E59B11e25b0F663Ee0`. **Always read the live EIP-1967 slot — never hard-code an impl.** `Upgraded(address)` topic0 = `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`.

### 12.2 The `liquidationCall` dispatcher (V2 — selector IS present)

Unlike Aave v3.4 (split impl), Granary's V2 `LendingPool` impl carries the `liquidationCall` selector `0x00a718a9` directly; the actual liquidation math runs in `LendingPoolCollateralManager` via **delegatecall** (so `LiquidationCall` is emitted by the **Pool** address, not the collateral manager). You can detect liquidations by either the `LiquidationCall` event topic0 `0xe413a321…` (recommended; 50 logs on the OP pool in a recent ~600k-block window) or the selector.

### 12.3 Address-collision caution

The same literal `LendingPool` `0xb702…eed3` is a live Granary pool on **ETH/Base/Avax AND BNB** (§8.B) but is absent on OP/ARB/Polygon; the OP `DataProvider` literal `0x9546…9995` equals the ETH oracle literal; the ARB Pool impl literal `0xf88baf18…` equals the ETH GRAIN token. **All detection must key on `(chainId, address)`.**

### 12.4 IncentivesController is wired but inert

Every gToken's `getIncentivesController()` returns a per-chain IC address (§3–§8), and all six ICs share identical 10,423-byte bytecode, but their **EIP-1967 impl slot is `0x0`** and every reward view (`REWARD_TOKEN`/`STAKE_TOKEN`/`REWARDS_VAULT`/`EMISSION_MANAGER`/`getDistributionEnd`) **reverts**. In practice the on-chain incentives controller is a non-initialized proxy stub — **do not expect `RewardsAccrued`/`RewardsClaimed` distribution logs from it.** GRAIN incentives, where they existed, were driven outside this contract (staking pools / off-chain emissions). Treat the IC address as a wiring pointer, not an active rewards source.

---

## 13. Detection invariants & gotchas

1. **Granary lending = Ethereum, Base, Avalanche, Arbitrum, Optimism, BNB.** NOT Polygon (§9). Off-target: Fantom, Metis, Linea (§10).
2. **It's an Aave V2 fork** — supply event is **`Deposit`** (`0xde685721…`), not V3's `Supply`. `getUserAccountData` returns **ETH/wei (1e18), not USD**. Reuse the [aave/v2.md](../aave/v2.md) detection set verbatim.
3. **gToken vs debt-token `Mint`/`Burn` have different topic0s** (V2 behavior). gToken `Mint` = `0x4c209b5f` (also collides with Uniswap-V2 / Compound `Mint`), varDebt `Mint` = `0x2f00e3cd`. Match on `(topic0, emitting address)`.
4. **Several topics/selectors are shared with Aave V2 AND V3** — `Withdraw`, `LiquidationCall`, `ReserveDataUpdated`, collateral enabled/disabled, and selectors `borrow`/`repay`/`withdraw`/`flashLoan`/`liquidationCall`. **Disambiguate by Pool address + chain, never by topic/selector alone** — Granary literally shares the `0xb702…eed3` Pool address with itself across **4 chains (ETH/Base/Avax/BNB)** and shares topics with Aave's own markets.
5. **`liquidationCall` selector IS in the impl dispatcher** (unlike v3.4) — but still prefer detecting liquidations by the `LiquidationCall` event (§12.2). `LiquidationCall` is emitted by the Pool (collateral manager runs via delegatecall).
6. **gTokens rebase every block.** Store `scaledBalanceOf` + reconstruct with the reserve `liquidityIndex` (ray, 27-dec). Same for debt with `variableBorrowIndex`. gTokens are 8-/6-/18-dec matching the underlying; `name()` = "Granary XXX", `symbol()` = **`grainXXX`**.
7. **`onBehalfOf`/`user` ≠ `tx.from`.** Attribute positions to the event's `onBehalfOf`/`user`, not the sender (gateways, credit delegation, liquidation bots route via `tx.to ≠ Pool`).
8. **Address clusters & coincidences.** ETH/Base/Avax **and BNB** share the `0xb702…`/`0xedc8…`/`0xc534…` provider/pool/configurator/gToken cluster; BNB also runs a second unique cluster (§8); some literals coincide across roles/chains (§12.3). Key everything on `(chainId, address)`.
9. **Oracle is ETH-denominated.** `getAssetPrice` returns wei (1e18 base), matching Aave V2. Don't treat values as USD.
10. **Stable rate exists** (`borrowRateMode`/`rateMode` 1=stable, 2=variable; `Swap`/`RebalanceStableBorrowRate`/`stableDebtToken`s present) — though most current activity is variable.
11. **Incentives controller is inert** (§12.4) — don't rely on it for reward events; GRAIN is a separate per-chain ERC-20.
12. **Low activity / winding down.** Optimism is the live market; Ethereum is dormant. Expect `Withdraw`/`Repay`/`LiquidationCall` to dominate over `Deposit`/`Borrow`.
13. **MarketId = "Granary Genesis Market"** on every chain (from `Provider.getMarketId()`) — distinguishes Granary providers from Aave's when crawling a `LendingPoolAddressesProviderRegistry`.

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; identical to Aave V2) =====
TOPIC_DEPOSIT                = '\xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951'
TOPIC_WITHDRAW               = '\x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'  -- shared V2/V3
TOPIC_BORROW                 = '\xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b'
TOPIC_REPAY                  = '\x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa'
TOPIC_SWAP_RATE              = '\xea368a40e9570069bb8e6511d668293ad2e1f03b0d982431fd223de9f3b70ca6'
TOPIC_FLASHLOAN              = '\x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac'
TOPIC_LIQUIDATIONCALL        = '\xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'  -- shared V2/V3
TOPIC_RESERVE_DATA_UPDATED   = '\x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a'  -- shared V2/V3
TOPIC_COLLATERAL_ENABLED     = '\x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2'  -- shared V2/V3
TOPIC_COLLATERAL_DISABLED    = '\x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd'  -- shared V2/V3
TOPIC_REBALANCE_STABLE       = '\x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300'  -- shared V2/V3
TOPIC_PAUSED                 = '\x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752'
TOPIC_UNPAUSED               = '\xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933'
-- gToken / debt tokens (V2-specific signatures; gToken != debt token)
TOPIC_GTOKEN_MINT            = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'  -- Mint(address,uint256,uint256) (collides w/ UniV2/Compound)
TOPIC_GTOKEN_BURN            = '\x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2'
TOPIC_VDEBT_MINT             = '\x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee'  -- Mint(address,address,uint256,uint256)
TOPIC_VDEBT_BURN             = '\x49995e5dd6158cf69ad3e9777c46755a1a826a446c6416992167462dad033b2a'
TOPIC_BALANCE_TRANSFER       = '\x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666'
TOPIC_ERC20_TRANSFER         = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- Configurator
TOPIC_RESERVE_INITIALIZED    = '\x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f'
TOPIC_RESERVE_FROZEN         = '\x85dc710add8a0914461a7dc5a63f6fc529a7700f8c6089a3faf5e93256ccf12a'
TOPIC_RESERVE_UNFROZEN       = '\x838ecdc4709a31a26db48b0c853212cedde3f725f07030079d793fb071964760'
TOPIC_COLLAT_CONFIG_CHANGED  = '\x637febbda9275aea2e85c0ff690444c8d87eb2e8339bbede9715abcc89cb0995'  -- shared w/ V3 Configurator
TOPIC_RESERVE_FACTOR_CHANGED = '\x2694ccb0b585b6a54b8d8b4a47aa874b05c257b43d34e98aee50838be00d3405'
TOPIC_UPGRADED               = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'  -- Upgraded(address)

-- ===== Selectors — LendingPool (identical to Aave V2) =====
SEL_DEPOSIT                  = '\xe8eda9df'   -- V2 supply (V3 = supply 0x617ba037)
SEL_WITHDRAW                 = '\x69328dec'   -- shared V2/V3
SEL_BORROW                   = '\xa415bcad'   -- shared V2/V3
SEL_REPAY                    = '\x573ade81'   -- shared V2/V3
SEL_SWAP_BORROW_RATE_MODE    = '\x94ba89a2'
SEL_LIQUIDATION_CALL         = '\x00a718a9'   -- present in V2 impl dispatcher
SEL_FLASHLOAN                = '\xab9c4b5d'   -- shared V2/V3
SEL_SET_USE_RESERVE_AS_COLL  = '\x5a3b74b9'
SEL_GET_USER_ACCOUNT_DATA    = '\xbf92857c'   -- returns ETH/wei, not USD
SEL_GET_RESERVE_DATA         = '\x35ea6a75'
SEL_GET_RESERVES_LIST        = '\xd1946dbc'
SEL_SCALED_BALANCE_OF        = '\x1da24f3e'
SEL_GET_ASSET_PRICE          = '\xb3596f07'

-- ===== Ethereum (chain ID 1) =====
ETH_REGISTRY                 = '\x5c93b799d31d3d6a7c977f75fdb88d069565a55b'
ETH_PROVIDER                 = '\xedc83309549e36f3c7fd8c2c5c54b4c8e5fa00fc'  -- shared w/ Base+Avax
ETH_POOL                     = '\xb702ce183b4e1faa574834715e5d4a6378d0eed3'  -- shared w/ Base+Avax
ETH_CONFIGURATOR             = '\xc534f577c0e6c46b27fdca6d27d132c543b0d61c'  -- shared w/ Base+Avax
ETH_COLLATERAL_MANAGER       = '\xf6d1cabe63237970b0e5fec45afc5b2c1312d8e0'
ETH_ORACLE                   = '\x9546f673ef71ff666ae66d01fd6e7c6dae5a9995'
ETH_DATA_PROVIDER            = '\x33c62bc416309f010c4941163abea3725e4645bf'
ETH_POOL_IMPL                = '\xc01a7ad7fb8a085a3cc16be8eaa10302c78a1783'
ETH_GRAIN                    = '\xf88baf18fab7e330fa0c4f83949e23f52fececce'

-- ===== Base (chain ID 8453) =====
BASE_REGISTRY                = '\x5c93b799d31d3d6a7c977f75fdb88d069565a55b'
BASE_PROVIDER                = '\xedc83309549e36f3c7fd8c2c5c54b4c8e5fa00fc'
BASE_POOL                    = '\xb702ce183b4e1faa574834715e5d4a6378d0eed3'
BASE_CONFIGURATOR            = '\xc534f577c0e6c46b27fdca6d27d132c543b0d61c'
BASE_COLLATERAL_MANAGER      = '\x352bc36e5552a364d4d2aa01c8c12bec11c6cc11'
BASE_ORACLE                  = '\x5a3423210536d930150080f699248edebc65e2b4'  -- shared w/ Avax
BASE_DATA_PROVIDER           = '\xed984a0e9c12ee27602314191fc4487a702bb83f'  -- shared w/ Avax

-- ===== Avalanche (chain ID 43114) =====
AVAX_REGISTRY                = '\xc043ba54f34c9fb3a0b45d22e2ef1f171272bc9d'
AVAX_PROVIDER                = '\xedc83309549e36f3c7fd8c2c5c54b4c8e5fa00fc'
AVAX_POOL                    = '\xb702ce183b4e1faa574834715e5d4a6378d0eed3'
AVAX_CONFIGURATOR            = '\xc534f577c0e6c46b27fdca6d27d132c543b0d61c'
AVAX_COLLATERAL_MANAGER      = '\x4d8d90faf90405b9743ce600e98a2aa8cdf579a0'
AVAX_ORACLE                  = '\x5a3423210536d930150080f699248edebc65e2b4'
AVAX_DATA_PROVIDER           = '\xed984a0e9c12ee27602314191fc4487a702bb83f'
AVAX_GRAIN                   = '\x9df4ac62f9e435dbcd85e06c990a7f0ea32739a9'

-- ===== Arbitrum One (chain ID 42161) =====
ARB_REGISTRY                 = '\x512f582ffccf3c14bd872152eeae60866dcb2a1e'
ARB_PROVIDER                 = '\x642cc899652b068d1bed786c4b060ec1027d1563'
ARB_POOL                     = '\x102442a3ba1e441043154bc0b8a2e2fb5e0f94a7'
ARB_CONFIGURATOR             = '\x0dbf9689faf89e91186bbccc3ce5a9b5ae3f2f78'
ARB_COLLATERAL_MANAGER       = '\xc2cda52c7dc64d4ff01b58b0981e1fcdd94b16c2'
ARB_ORACLE                   = '\xe12e084fc4550387cb2b252b5f289ba38b755354'
ARB_DATA_PROVIDER            = '\x96bcfb86f1bff315c13e00d850e2faea93ccd3e7'
ARB_POOL_IMPL                = '\xf88baf18fab7e330fa0c4f83949e23f52fececce'
ARB_GRAIN                    = '\x80bb30d62a16e1f2084deae84dc293531c3ac3a1'

-- ===== Optimism (chain ID 10) — most active =====
OP_REGISTRY                  = '\x872b9e8aea5d65fbf29b8b05bfa4aa3fe94cc11f'
OP_PROVIDER                  = '\xdde5dc81e40799750b92079723da2acaf9e1c6d6'
OP_POOL                      = '\x8fd4af47e4e63d1d2d45582c3286b4bd9bb95dfe'
OP_CONFIGURATOR              = '\x494bf60b3b58664d5a674e692c718d33687e663a'
OP_COLLATERAL_MANAGER        = '\x025d9d36c616946530ff8ea32d912abf73170947'
OP_ORACLE                    = '\x9aeefef549323511e027d70562f0c7edcdeb294c'
OP_DATA_PROVIDER             = '\x9546f673ef71ff666ae66d01fd6e7c6dae5a9995'
OP_POOL_IMPL                 = '\x72fad09e3da8cec0e975bf253c1e5eafdb927fec'
OP_GRAIN                     = '\xfd389dc9533717239856190f42475d3f263a270d'

-- ===== BNB Smart Chain (chain ID 56) — TWO clusters =====
-- Cluster A (BNB-unique; the registered market)
BSC_REGISTRY                 = '\x7c8e7536c5044e1b3693eb564c6de3a3ce58bbda'
BSC_PROVIDER                 = '\x12c26138b666360ab2b7a1b149df9cf6642cdfbf'
BSC_POOL                     = '\x7171054f8d148fe1097948923c91a6596fc29032'
BSC_CONFIGURATOR             = '\xd057dd41f71397854d00050dcb634261ce7e0893'
BSC_COLLATERAL_MANAGER       = '\xf957262db8b35181a0ab8f034ec8ce73a7531f9b'
BSC_ORACLE                   = '\x417ca1091fa4c329cee19452851dff46902440a5'
BSC_DATA_PROVIDER            = '\x7fb479624ca336ba8f2dc66439f8683330ee2880'
BSC_POOL_IMPL                = '\xe1537fef008944d1c8dcafbace4dc76d31d22dc5'
BSC_GRAIN                    = '\x8f87a7d376821c7b2658a005aaf190ec778bf37a'
-- Cluster B (shared ETH/Base/Avax cluster, ALSO live on BNB — §8.B; not in BSC registry)
BSC_PROVIDER_SHARED          = '\xedc83309549e36f3c7fd8c2c5c54b4c8e5fa00fc'
BSC_POOL_SHARED              = '\xb702ce183b4e1faa574834715e5d4a6378d0eed3'  -- impl 0xc01a7ad7… (same as ETH)
BSC_CONFIGURATOR_SHARED      = '\xc534f577c0e6c46b27fdca6d27d132c543b0d61c'

-- ===== Universal =====
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT           = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'  -- reads 0x0 on Granary (immutable admin)
-- Polygon PoS (137): NO Granary deployment.
```

---

## 15. Verification & sources

How constants in this doc were verified (2026-06-08):

- **Event topic0 / selectors:** all recomputed locally as `keccak256(signature)` (pycryptodome). Sample cross-checked against live `eth_getLogs` on the Optimism LendingPool `0x8FD4…95DfE` over a ~600k-block window: `Deposit` (26, topic0 `0xde685721…`), `Withdraw` (13, `0x3115d144…`), `LiquidationCall` (50, `0xe413a321…`), `ReserveDataUpdated` (140, `0x804c9b84…`); gToken `Mint`/`Burn` on `grainUSDC` `0x7a0f…f0c0` (31 / 12, `0x4c209b5f` / `0x5d624aa9`) and varDebt `Burn` on `0xb271…d0bf` (12, `0x49995e5d`). `Borrow`/vDebt `Mint` returned 0 in the recent window — consistent with the protocol winding down. Ethereum market confirmed dormant (0 `Deposit` in ~450k blocks).
- **Addresses:** discovered by walking the on-chain graph — `LendingPoolAddressesProviderRegistry.getAddressesProvidersList()` (seeded from the canonical DefiLlama `the-granary` adapter registries) → `LendingPoolAddressesProvider.{getLendingPool, getLendingPoolConfigurator, getLendingPoolCollateralManager, getPriceOracle, getLendingRateOracle, getPoolAdmin, getEmergencyAdmin, getMarketId, getAddress(0x01…)}` → `LendingPool.getReservesList()` → per-reserve `getReserveData(asset)` for gToken/variableDebt/stableDebt/IRM. Every resulting address existence-checked via `eth_getCode` on the listed RPC. `getMarketId()` = "Granary Genesis Market" on all six chains. gToken naming read live (`name()`="Granary DAI", `symbol()`="grainDAI"). GRAIN tokens confirmed via `symbol()`="GRAIN" + non-empty `eth_getCode` on ETH/Avax/Arb/OP/BNB (absent on Base).
- **Proxies:** EIP-1967 impl slot `0x360894…382bbc` and admin slot `0xb53127…5d6103` read via `eth_getStorageAt`. Pool/Configurator/gToken/debt proxies have non-zero impl + zero admin (immutable-admin pattern); Provider/oracle/rate-oracle/data-provider/collateral-manager have zero impl (non-proxy). IncentivesController impl slot = `0x0` and all reward views revert (inert — §12.4).
- **Chain coverage:** Polygon absence confirmed by empty `eth_getCode` for all Granary anchors and no Polygon entry in the DefiLlama adapter. Fantom/Metis/Linea registries taken from the same adapter as off-target anchors.

Authoritative sources:

- [`The-Granary/Granary-Protocol-v1`](https://github.com/The-Granary/Granary-Protocol-v1) — canonical fork source (LendingPool, LendingPoolConfigurator, LendingPoolCollateralManager, LendingPoolAddressesProvider/Registry, tokenization). Confirms the Aave-V2 lineage and proxy pattern.
- [`aave/protocol-v2`](https://github.com/aave/protocol-v2) — upstream V2 contracts (LendingPool, configurator, aToken, debt tokens) whose event/function signatures Granary inherits byte-for-byte. See [aave/v2.md](../aave/v2.md).
- [DefiLlama `the-granary` adapter](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/the-granary/index.js) — per-chain `LendingPoolAddressesProviderRegistry` set (source for the address walk + chain list).
- [Granary Finance on DefiLlama](https://defillama.com/protocol/granary-finance) — chain/TVL footprint (Optimism, Metis, Arbitrum, BNB, Avalanche, Fantom, Ethereum, Base — no Polygon).
- Explorers: [Optimistic Etherscan LendingPool](https://optimistic.etherscan.io/address/0x8FD4aF47E4E63d1D2D45582c3286b4BD9Bb95DfE) · [Etherscan LendingPool](https://etherscan.io/address/0xB702cE183b4E1Faa574834715E5D4a6378D0eEd3) · [Arbiscan GRAIN](https://arbiscan.io/token/0x80bb30d62a16e1f2084deae84dc293531c3ac3a1).
