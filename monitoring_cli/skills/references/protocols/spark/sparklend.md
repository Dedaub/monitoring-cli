# SparkLend — Topics, Selectors, Addresses (Ethereum + Gnosis; Spark non-lending footprint on Base/Arbitrum/Optimism/Avalanche/Unichain/World Chain)

**Status:** verified against Ethereum and Gnosis mainnet RPC, the canonical `sparkdotfi/spark-address-registry` `.sol` libraries, and `aave-dao/aave-v3-origin`, on 2026-05-29. Non-obvious claims additionally fact-checked against primary sources (Spark docs/forum, Sky governance, GitHub) — see §11.1.
**Scope:** the user requested Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon PoS. **The SparkLend lending market exists on only two chains — Ethereum (chain 1, active) and Gnosis Chain (chain 100, winding down).** None of Base / BNB / Avalanche / Arbitrum / Optimism / Polygon runs a SparkLend `Pool`. Base/Arbitrum/Optimism/Avalanche (plus Unichain & World Chain) host only the **Spark Savings + Spark Liquidity Layer** products (sUSDS/sUSDC, PSM3, ALM) — documented in §6 since the user asked for "all possible deployments." **BNB Smart Chain and Polygon PoS have no Spark contracts at all** (no registry file).

SparkLend is a **soft fork of Aave V3** (V3.0.x-era; built by Phoenix Labs), so **its event topics and function selectors are byte-for-byte identical to Aave V3** — see [aave/v3.md](../aave/v3.md). It deployed to Ethereum mainnet in March 2023 and **officially launched 2023-05-09**; the Gnosis instance followed in **September 2023** (its first and only cross-chain lending deployment). This doc records what is *specific* to SparkLend: which Aave features it has/lacks (it predates v3.2–v3.4), its Spark-specific contracts (FreezerMom, KillSwitchOracle, CapAutomator, fixed-$1 stable oracles, Sky D3M DAI source), its governance (`SPARK_PROXY`, the Spark subDAO), and its network-specific addresses. Every core contract is a **fully upgradeable proxy**; aTokens are branded **spTokens** (spWETH, spDAI, …) but are mechanically identical Aave aTokens.

> **Version / lineage note (verified on-chain 2026-05-29):** the live Ethereum Pool impl `0x5aE329203E00f76891094DcfedD5Aca082a50e1b` (= the registry `POOL_IMPL`, **no drift** — Spark keeps its registry current, unlike `aave-address-book`) is an **Aave V3.0/V3.1-era** Pool. Confirmed by bytecode selector scan: `supply`/`borrow`/`repay`/`withdraw`/`flashLoan`/`flashLoanSimple`/`mintUnbacked`/`backUnbacked`/`swapBorrowRateMode`/`rebalanceStableBorrowRate`/`rescueTokens`/eMode are **present**; the Aave **v3.3** (`getReserveDeficit`, `eliminateReserveDeficit`, `DeficitCreated`/`DeficitCovered`) and **v3.4** (`multicall`, `approvePositionManager`, `getReserveAToken`, Position Managers) additions are **all absent**. Stable-rate code is present-but-disabled by config (`stableBorrowEnabled = false` on every reserve) — SparkLend predates Aave v3.2's stable-rate removal but never enabled it. SparkLend has **no v2** and **no hub-and-spoke v4**; it is one continuously-patched deployment.

> **Liquidation dispatcher anomaly (verified, same as Aave):** the canonical `liquidationCall` selector `0x00a718a9` is **absent from the live Pool impl bytecode** (raw + PUSH4 scan = 0 occurrences) even though `supply`/`borrow`/`flashLoan` are present, yet `LiquidationCall` events fire normally (8 logs in a 45k-block window) and liquidations succeed (routed through bots/adapters, e.g. `0x1f2f10d1…`). **Detect SparkLend liquidations by the `LiquidationCall` event topic0 `0xe413a321…`, never by the function selector.** See §8.2.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Identical to Aave V3 (SparkLend is a fork). All values below recomputed locally with keccak on 2026-05-29; `Supply`/`Borrow`/`LiquidationCall`/`Mint`/`Burn` additionally confirmed against live SparkLend Pool/spToken logs.

### 1.1 Pool (emits all lending activity) — emitter on ETH = `0xC13e…BE987`, on Gnosis = `0x2Dae…07e0`

| topic0 | Event |
|--------|-------|
| `0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61` | `Supply(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint16 indexed referralCode)` |
| `0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7` | `Withdraw(address indexed reserve, address indexed user, address indexed to, uint256 amount)` |
| `0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0` | `Borrow(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint8 interestRateMode, uint256 borrowRate, uint16 indexed referralCode)` |
| `0xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051` | `Repay(address indexed reserve, address indexed user, address indexed repayer, uint256 amount, bool useATokens)` |
| `0xefefaba5e921573100900a3ad9cf29f222d995fb3b6045797eaea7521bd8d6f0` | `FlashLoan(address indexed target, address initiator, address indexed asset, uint256 amount, uint8 interestRateMode, uint256 premium, uint16 indexed referralCode)` |
| `0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286` | `LiquidationCall(address indexed collateralAsset, address indexed debtAsset, address indexed user, uint256 debtToCover, uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)` |
| `0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a` | `ReserveDataUpdated(address indexed reserve, uint256 liquidityRate, uint256 stableBorrowRate, uint256 variableBorrowRate, uint256 liquidityIndex, uint256 variableBorrowIndex)` |
| `0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2` | `ReserveUsedAsCollateralEnabled(address indexed reserve, address indexed user)` |
| `0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd` | `ReserveUsedAsCollateralDisabled(address indexed reserve, address indexed user)` |
| `0x7962b394d85a534033ba2efcf43cd36de57b7ebeb3de0ca4428965d9b3ddc481` | `SwapBorrowRateMode(address indexed reserve, address indexed user, uint8 interestRateMode)` (stable disabled; legacy) |
| `0x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300` | `RebalanceStableBorrowRate(address indexed reserve, address indexed user)` (legacy) |
| `0xbfa21aa5d5f9a1f0120a95e7c0749f389863cbdbfff531aa7339077a5bc919de` | `MintedToTreasury(address indexed reserve, uint256 amountMinted)` |
| `0xaef84d3b40895fd58c561f3998000f0583abb992a52fbdc99ace8e8de4d676a5` | `IsolationModeTotalDebtUpdated(address indexed asset, uint256 totalDebt)` |
| `0xd728da875fc88944cbf17638bcbe4af0eedaef63becd1d1c57cc097eb4608d84` | `UserEModeSet(address indexed user, uint8 categoryId)` |
| `0xf25af37b3d3ec226063dc9bdc103ece7eb110a50f340fe854bb7bc1b0676d7d0` | `MintUnbacked(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint16 indexed referralCode)` (Portal — present but unused) |
| `0x281596e92b2d974beb7d4f124df30a0b39067b096893e95011ce4bdad798b759` | `BackUnbacked(address indexed reserve, address indexed backer, uint256 amount, uint256 fee)` (Portal — present but unused) |

`Supply`/`Borrow` are the workhorses. `interestRateMode` is `uint8` (2 = variable; 1 = stable, never enabled on SparkLend). **`Supply` ≠ Aave V2 `Deposit`** (different topic0). **Aave v3.3 `DeficitCreated`/`DeficitCovered` do NOT exist on SparkLend** (feature not forked).

### 1.2 spToken & variableDebtToken (per-reserve, scaled rebasing — Aave aToken mechanics)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x458f5fa412d0f69b08dd84872b0215675cc67bc1d5b6fd93300a1c3878b86196` | `Mint(address indexed caller, address indexed onBehalfOf, uint256 value, uint256 balanceIncrease, uint256 index)` | spToken **and** variableDebtToken |
| `0x4cf25bc1d991c17529c25213d3cc0cda295eeaad5f13f361969b12ea48015f90` | `Burn(address indexed from, address indexed target, uint256 value, uint256 balanceIncrease, uint256 index)` | spToken **and** variableDebtToken |
| `0x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666` | `BalanceTransfer(address indexed from, address indexed to, uint256 value, uint256 index)` | spToken only |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 (spToken; debt tokens emit on mint/burn) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | spToken (ERC-20 + EIP-2612) |
| `0xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1` | `BorrowAllowanceDelegated(address indexed fromUser, address indexed toUser, address indexed asset, uint256 amount)` | debt token (credit delegation) |

**Same `Mint`/`Burn` topic0 on spToken and variableDebtToken** — disambiguate by the emitting `address`. `value` is the actual amount; `index` is the reserve `liquidityIndex`/`variableBorrowIndex` (ray, 27-dec) so `scaled = value * 1e27 / index`. On Gnosis, reserves additionally have **stableDebtTokens** (with the same `Mint`/`Burn` topic) — Ethereum reserves do not carry stable debt tokens despite the impl existing.

### 1.3 PoolConfigurator (governance/risk-admin) — ETH `0x542D…0738`, Gnosis `0x2Fc8…b588`

| topic0 | Event |
|--------|-------|
| `0x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f` | `ReserveInitialized(address indexed asset, address indexed aToken, address stableDebtToken, address variableDebtToken, address interestRateStrategyAddress)` |
| `0x637febbda9275aea2e85c0ff690444c8d87eb2e8339bbede9715abcc89cb0995` | `CollateralConfigurationChanged(address indexed asset, uint256 ltv, uint256 liquidationThreshold, uint256 liquidationBonus)` |
| `0x2443ba28e8d1d88d531a3d90b981816a4f3b3c7f1fd4085c6029e81d1b7a570d` | `ReserveBorrowing(address indexed asset, bool enabled)` |
| `0x0c4443d258a350d27dc50c378b2ebf165e6469725f786d21b30cab16823f5587` | `ReserveFrozen(address indexed asset, bool frozen)` (← fired by FreezerMom/spells) |
| `0xe188d542a5f11925d3a3af33703cdd30a43cb3e8066a3cf68b1b57f61a5a94b5` | `ReservePaused(address indexed asset, bool paused)` |
| `0xc36c7d11ba01a5869d52aa4a3781939dab851cbc9ee6e7fdcedc7d58898a3f1e` | `ReserveActive(address indexed asset, bool active)` |
| `0xb46e2b82b0c2cf3d7d9dece53635e165c53e0eaa7a44f904d61a2b7174826aef` | `ReserveFactorChanged(address indexed asset, uint256 oldReserveFactor, uint256 newReserveFactor)` |
| `0x0263602682188540a2d633561c0b4453b7d8566285e99f9f6018b8ef2facef49` | `SupplyCapChanged(address indexed asset, uint256 oldSupplyCap, uint256 newSupplyCap)` (← fired by CapAutomator) |
| `0xc51aca575985d521c5072ad11549bad77013bb786d57f30f94b40ed8f8dc9bc4` | `BorrowCapChanged(address indexed asset, uint256 oldBorrowCap, uint256 newBorrowCap)` (← fired by CapAutomator) |
| `0xdb8dada53709ce4988154324196790c2e4a60c377e1256790946f83b87db3c33` | `ReserveInterestRateStrategyChanged(address indexed asset, address oldStrategy, address newStrategy)` |
| `0x0acf8b4a3cace10779798a89a206a0ae73a71b63acdd3be2801d39c2ef7ab3cb` | `EModeCategoryAdded(uint8 indexed categoryId, uint256 ltv, uint256 liquidationThreshold, uint256 liquidationBonus, address oracle, string label)` |
| `0x5bb69795b6a2ea222d73a5f8939c23471a1f85a99c7ca43c207f1b71f10c6264` | `EModeAssetCategoryChanged(address indexed asset, uint8 oldCategoryId, uint8 newCategoryId)` |
| `0xb5b0a963825337808b6e3154de8e98027595a5cad4219bb3a9bc55b192f4b391` | `LiquidationProtocolFeeChanged(address indexed asset, uint256 oldFee, uint256 newFee)` |

### 1.4 AaveOracle (SparkLend keeps Aave's oracle aggregator) — ETH `0x8105…cFD9`

| topic0 | Event |
|--------|-------|
| `0x22c5b7b2d8561d39f7f210b6b326a1aa69f15311163082308ac4877db6339dc1` | `AssetSourceUpdated(address indexed asset, address indexed source)` |
| `0xe27c4c1372396a3d15a9922f74f9dfc7c72b1ad6d63868470787249c356454c1` | `BaseCurrencySet(address indexed baseCurrency, uint256 baseCurrencyUnit)` |
| `0xce7a780d33665b1ea097af5f155e3821b809ecbaa839d3b33aa83ba28168cefb` | `FallbackOracleUpdated(address indexed fallbackOracle)` |

---

## 2. Function signatures (chain-agnostic)

Selectors = `keccak256(canonical signature)[0:4]`. All Pool selectors below verified **present** in the live Ethereum Pool impl bytecode (`0x5aE329…`) on 2026-05-29 **except `liquidationCall`** (§8.2). The Aave v3.3/v3.4 selectors are listed at the end as **absent on SparkLend**.

### 2.1 Pool — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x617ba037` | `supply(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)` | Emits `Supply`. |
| `0x02c205f0` | `supplyWithPermit(address asset, uint256 amount, address onBehalfOf, uint16 referralCode, uint256 deadline, uint8 permitV, bytes32 permitR, bytes32 permitS)` | EIP-2612 one-tx supply. |
| `0x69328dec` | `withdraw(address asset, uint256 amount, address to)` → `uint256` | `amount = type(uint256).max` = full balance. |
| `0xa415bcad` | `borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)` | `interestRateMode` 2 = variable (1 = stable, disabled). |
| `0x573ade81` | `repay(address asset, uint256 amount, uint256 interestRateMode, address onBehalfOf)` → `uint256` | |
| `0xee3e210b` | `repayWithPermit(address asset, uint256 amount, uint256 interestRateMode, address onBehalfOf, uint256 deadline, uint8 permitV, bytes32 permitR, bytes32 permitS)` → `uint256` | |
| `0x2dad97d4` | `repayWithATokens(address asset, uint256 amount, uint256 interestRateMode)` → `uint256` | `Repay.useATokens = true`. |
| `0x94ba89a2` | `swapBorrowRateMode(address asset, uint256 interestRateMode)` | Present but stable disabled. |
| `0xcd112382` | `rebalanceStableBorrowRate(address asset, address user)` | Present but stable disabled. |
| `0x00a718a9` | `liquidationCall(address collateralAsset, address debtAsset, address user, uint256 debtToCover, bool receiveAToken)` | Emits `LiquidationCall`. **NOT in impl dispatcher — detect via event (§8.2).** |
| `0xab9c4b5d` | `flashLoan(address receiverAddress, address[] assets, uint256[] amounts, uint256[] interestRateModes, address onBehalfOf, bytes params, uint16 referralCode)` | Multi-asset. |
| `0x42b0b77c` | `flashLoanSimple(address receiverAddress, address asset, uint256 amount, bytes params, uint16 referralCode)` | Single-asset, no-debt. |
| `0x5a3b74b9` | `setUserUseReserveAsCollateral(address asset, bool useAsCollateral)` | |
| `0x28530a47` | `setUserEMode(uint8 categoryId)` | Emits `UserEModeSet`. |
| `0x69a933a5` | `mintUnbacked(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)` | Portal (BRIDGE role) — present, unused. |
| `0xd65dc7a1` | `backUnbacked(address asset, uint256 amount, uint256 fee)` → `uint256` | Portal — present, unused. |
| `0x9cd19996` | `mintToTreasury(address[] assets)` | Sweeps reserve factor to Treasury. |
| `0xcea9d26f` | `rescueTokens(address token, address to, uint256 amount)` | Recover stuck tokens (POOL_ADMIN). |

### 2.2 Pool — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xbf92857c` | `getUserAccountData(address user)` | `(totalCollateralBase, totalDebtBase, availableBorrowsBase, currentLiquidationThreshold, ltv, healthFactor)` — first 5 in **8-dec USD**, HF in **1e18**. |
| `0x35ea6a75` | `getReserveData(address asset)` | Full `ReserveData` struct (config bitmap, indices, rates, spToken/stable/variable token addrs, id, …). |
| `0xd15e0053` | `getReserveNormalizedIncome(address asset)` | `uint256` ray — supply index. |
| `0x386497fd` | `getReserveNormalizedVariableDebt(address asset)` | `uint256` ray — borrow index. |
| `0xc44b11f7` | `getConfiguration(address asset)` | Packed reserve config bitmap. |
| `0x4417a583` | `getUserConfiguration(address user)` | Packed user collateral/borrow bitmap. |
| `0xd1946dbc` | `getReservesList()` | `address[]` — all reserve underlyings (18 on ETH). |
| `0xeddf1b79` | `getUserEMode(address user)` | `uint256` category id. |
| `0x6c6f6ae1` | `getEModeCategoryData(uint8 id)` | E-Mode config. |
| `0x074b2e43` | `FLASHLOAN_PREMIUM_TOTAL()` | `uint128` bps. |

### 2.3 spToken / variableDebtToken

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1da24f3e` | `scaledBalanceOf(address user)` | **Use for accounting** — `balanceOf` rebases every block. |
| `0x0afbcdc9` | `getScaledUserBalanceAndSupply(address user)` | `(uint256, uint256)`. |
| `0xb1bf962d` | `scaledTotalSupply()` | `uint256`. |
| `0xb16a19de` | `UNDERLYING_ASSET_ADDRESS()` | Underlying reserve token. |
| `0x7535d246` | `POOL()` | Owning Pool. |
| `0xe0753986` | `getPreviousIndex(address user)` | Last index applied to user. |
| `0xc04a8a10` | `approveDelegation(address delegatee, uint256 amount)` | debt token — credit delegation. |
| `0x6bd76d24` | `borrowAllowance(address fromUser, address toUser)` | debt token. |
| `0x70a08231` / `0x18160ddd` | `balanceOf` / `totalSupply` | **Rebasing** — changes every block. |

### 2.4 AaveOracle / ProtocolDataProvider

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xb3596f07` | `getAssetPrice(address asset)` → `uint256` | AaveOracle (8-dec USD; `BASE_CURRENCY_UNIT = 1e8`). |
| `0x9d23d9f2` | `getAssetsPrices(address[] assets)` → `uint256[]` | AaveOracle. |
| `0x92bf2be0` | `getSourceOfAsset(address asset)` → `address` | AaveOracle (feed/adapter; fixed-$1 for DAI). |
| `0xe19f4700` | `BASE_CURRENCY()` → `address` | AaveOracle (0x0 = USD). |
| `0x8c89b64f` | `BASE_CURRENCY_UNIT()` → `uint256` | AaveOracle (1e8). |
| `0x6744362a` | `getInterestRateStrategyAddress(address asset)` → `address` | ProtocolDataProvider — DAI returns the custom DSR-linked IRM. |

### 2.5 Aave selectors **absent on SparkLend** (do NOT scan for these — feature not forked)

| Selector | Signature | Aave version |
|----------|-----------|--------------|
| `0xac9650d8` | `multicall(bytes[])` | v3.4 — absent |
| `0xb8caa7c5` | `approvePositionManager(address,bool)` | v3.4 — absent |
| `0xf9c2bd87` | `isApprovedPositionManager(address,address)` | v3.4 — absent |
| `0xcff027d9` | `getReserveAToken(address)` | v3.4 — absent |
| `0x365090a0` | `getReserveVariableDebtToken(address)` | v3.4 — absent |
| `0xc952485d` | `getReserveDeficit(address)` | v3.3 — absent |
| `0xa1d2f3c4` | `eliminateReserveDeficit(address,uint256)` | v3.3 — absent |

---

## 3. Addresses — Ethereum mainnet (chain ID 1) — the active SparkLend market

Source: `spark-address-registry/src/SparkLend.sol` + `Ethereum.sol`. All verified via `eth_getCode` / `eth_call` on `https://ethereum-rpc.publicnode.com`. Pool wiring confirmed: `Pool.ADDRESSES_PROVIDER()` → Provider, `Provider.getPool()` → Pool, `Provider.getMarketId()` = **"Spark Protocol"**, `Provider.getACLAdmin()` → `SPARK_PROXY`.

### 3.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| **Pool** (proxy) | `0xC13e21B648A5Ee794902342038FF3aDAB66BE987` | Main lending entrypoint; emits all §1.1 events. |
| **PoolAddressesProvider** | `0x02C3eA4e34C0cBd694D2adFa2c690EECbC1793eE` | Per-market registry / source-of-truth. |
| PoolAddressesProviderRegistry | `0x03cFa0C4622FF84E50E75062683F44c9587e6Cc1` | Lists Spark addresses-providers. |
| **PoolConfigurator** (proxy) | `0x542DBa469bdE58FAeE189ffB60C6b49CE60E0738` | Risk-admin; emits §1.3 events. |
| **AaveOracle** | `0x8105f69D9C41644c6A0803fDA7D03Aa70996cFD9` | Price aggregator (USD, 1e8); DAI fixed at $1. |
| **ACLManager** | `0xdA135Cd78A086025BcdC87B038a1C462032b510C` | Role registry (POOL_ADMIN, RISK_ADMIN, …). |
| **ProtocolDataProvider** | `0xFc21d6d146E6086B8359705C8b28512a983db0cb` | Read helper for reserve/user data. |
| RewardsController (`INCENTIVES`, proxy) | `0x4370D3b6C9588E02ce9D22e684387859c7Ff5b34` | Liquidity-mining rewards. |
| EmissionManager | `0xf09e48dd4CA8e76F63a57ADd428bB06fee7932a4` | Configures reward emissions. |
| Treasury (Collector, proxy) | `0xb137E7d16564c81ae2b0C8ee6B55De81dd46ECe5` | Reserve-factor / fee sink. |
| TreasuryController | `0x92eF091C5a1E01b3CE1ba0D0150C84412d818F7a` | Treasury admin. |
| DAI Treasury | `0x856900aa78e856a5df1a2665eE3a66b2487cD68f` | Separate DAI fee sink (Maker D3M flow). |
| WrappedTokenGatewayV3 (`WETH_GATEWAY`) | `0xBD7D6a9ad7865463DE44B05F04559f65e3B11704` | ETH↔WETH supply/repay helper. |
| UiPoolDataProviderV3 | `0xF028c2F4b19898718fD0F77b9b881CbfdAa5e8Bb` | Front-end batch reader. |
| UiIncentiveDataProvider | `0xA7F8A757C4f7696c015B595F51B2901AC0121B18` | |
| WalletBalanceProvider | `0xd2AeF86F51F92E8e49F42454c287AE4879D1BeDc` | Batch token balances. |

### 3.2 Spark-specific safety & governance contracts (NOT in Aave)

| Role | Address | One-liner |
|------|---------|-----------|
| **SPARK_PROXY** (Spark subDAO executor) | `0x3300f198988e4C9C63F75dF86De36421f06af8c4` | **ACL_ADMIN / POOL_ADMIN** — governs SparkLend; controlled by Sky governance. |
| **FreezerMom** (SparkLendFreezerMom) | `0x237e3985dD7E373F2ec878EC1Ac48A228Cf2e7a3` | Holds RISK_ADMIN + EMERGENCY_ADMIN roles; `freezeMarket`/`freezeAllMarkets`/`pauseMarket`/`pauseAllMarkets`. Callable by the Freezer multisig or via a voted spell (Chief hat) / PauseProxy — emergency freeze without full gov delay. |
| **KillSwitchOracle** | `0x909A86f78e1cdEd68F9c2Fe2c9CD922c401abe82` | Disables **all** borrowing if a tracked feed falls below threshold (LST/collateral de-peg). Activated 2024-03; live for **wstETH + LBTC** (0.95 trigger). |
| **CapAutomator** | `0x4C1341636721b8B687647920B2E9481f3AB1F2eE` | Auto-adjusts supply/borrow caps on a schedule/slope (ChainSecurity-audited) → emits `SupplyCapChanged`/`BorrowCapChanged`. |
| SSR rate source | `0x57027B6262083E3aC3c8B2EB99f7e8005f669973` | Sky Savings Rate source (sUSDS pricing). |
| Spell: freeze all reserves | `0x9e2890BF7f8D5568Cc9e5092E67Ba00C8dA3E97f` | Emergency spell (via FreezerMom). |
| Spell: freeze DAI | `0xa2039bef2c5803d66E4e68F9E23a942E350b938c` | |
| Spell: pause all reserves | `0x425b0de240b4c2DC45979DB782A355D090Dc4d37` | |
| Spell: pause DAI | `0xCacB88e39112B56278db25b423441248cfF94241` | |
| SparkLend Freezer multisig | `0x44efFc473e81632B12486866AA1678edbb7BEeC3` | Holds freeze power via FreezerMom. |
| SparkLend Rewards multisig | `0x8076807464DaC94Ac8Aa1f7aF31b58F73bD88A27` | |
| Sky PauseProxy (D3M owner) | `0xBE8E3e3618f7474F8cB1d074A26afFef007E98FB` | Sky/Maker executor behind SPARK_PROXY; owns the DAI D3M. |

### 3.3 Reserves (18) — underlying → spToken / variableDebtToken

spToken (`*_SPTOKEN`) impl = `0x6175ddEc3B9b38c88157C10A01ed4A3fa8639cC6`; variableDebtToken (`*_DEBT_TOKEN`) impl = `0x86C71796CcDB31c3997F8Ec5C2E3dB3e9e40b985` (both verified live via EIP-1967 slot). No per-reserve stable debt tokens on Ethereum.

| Symbol | Underlying | spToken | variableDebtToken |
|--------|-----------|---------|-------------------|
| WETH | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` | `0x59cD1C87501baa753d0B5B5Ab5D8416A45cD71DB` | `0x2e7576042566f8D6990e07A1B61Ad1efd86Ae70d` |
| wstETH | `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0` | `0x12B54025C112Aa61fAce2CDB7118740875A566E9` | `0xd5c3E3B566a42A6110513Ac7670C1a86D76E13E6` |
| weETH | `0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee` | `0x3CFd5C0D4acAA8Faee335842e4f31159fc76B008` | `0xc2bD6d2fEe70A0A73a33795BdbeE0368AeF5c766` |
| rETH | `0xae78736Cd615f374D3085123A210448E74Fc6393` | `0x9985dF20D7e9103ECBCeb16a84956434B6f06ae8` | `0xBa2C8F2eA5B56690bFb8b709438F049e5Dd76B96` |
| ezETH | `0xbf5495Efe5DB9ce00f80364C8B423567e58d2110` | `0xB131cD463d83782d4DE33e00e35EF034F0869bA1` | `0xB0B14Dd477E6159B4F3F210cF45F0954F57c0FAb` |
| rsETH | `0xA1290d69c65A6Fe4DF752f95823fae25cB99e5A7` | `0x856f1Ea78361140834FDCd0dB0b08079e4A45062` | `0xc528F0C91CFAE4fd86A68F6Dfd4d7284707Bec68` |
| WBTC | `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599` | `0x4197ba364AE6698015AE5c1468f54087602715b2` | `0xf6fEe3A8aC8040C3d6d81d9A4a168516Ec9B51D2` |
| cbBTC | `0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf` | `0xb3973D459df38ae57797811F2A1fd061DA1BC123` | `0x661fE667D2103eb52d3632a3eB2cAbd123F27938` |
| tBTC | `0x18084fbA666a33d37592fA2633fD49a74DD93a88` | `0xce6Ca9cDce00a2b0c0d1dAC93894f4Bd2c960567` | `0x764591dC9ba21c1B92049331b80b6E2a2acF8B17` |
| LBTC | `0x8236a87084f8B84306f72007F36F2618A5634494` | `0xa9d4EcEBd48C282a70CfD3c469d6C8F178a5738E` | `0x096bdDFEE63F44A97cC6D2945539Ee7C8f94637D` |
| **DAI** | `0x6B175474E89094C44Da98b954EedeAC495271d0F` | `0x4DEDf26112B3Ec8eC46e7E31EA5e123490B05B8B` | `0xf705d2B7e92B3F38e6ae7afaDAA2fEE110fE5914` |
| sDAI | `0x83F20F44975D03b1b09e64809B757c47f942BEeA` | `0x78f897F0fE2d3B5690EbAe7f19862DEacedF10a7` | `0xaBc57081C04D921388240393ec4088Aa47c6832B` |
| USDS | `0xdC035D45d973E3EC169d2276DDab16f1e407384F` | `0xC02aB1A5eaA8d1B114EF786D9bde108cD4364359` | `0x8c147debea24Fb98ade8dDa4bf142992928b449e` |
| sUSDS | `0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD` | `0x6715bc100A183cc65502F05845b589c1919ca3d3` | `0x4e89b83f426fED3f2EF7Bb2d7eb5b53e288e1A13` |
| USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | `0x377C3bd93f2a2984E1E7bE6A5C22c525eD4A4815` | `0x7B70D04099CB9cfb1Db7B6820baDAfB4C5C70A67` |
| USDT | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | `0xe7dF13b8e3d6740fe17CBE928C7334243d86c92f` | `0x529b6158d1D2992E3129F7C69E81a7c677dc3B12` |
| PYUSD | `0x6c3ea9036406852006290770BEdFcAbA0e23A0e8` | `0x779224df1c756b4EDD899854F32a53E8c2B2ce5d` | `0x3357D2DB7763D6Cd3a99f0763EbF87e0096D95f9` |
| GNO | `0x6810e776880C02933D47DB1b9fc05908e5386b96` | `0x7b481aCC9fDADDc9af2cBEA1Ff2342CB1733E50F` | `0x57a2957651DA467fCD4104D749f2F3684784c25a` |

> **DAI is special.** Its liquidity is supplied by the **Sky/Maker D3M** (Direct Deposit Module, `DIRECT-SPARK-DAI`), minted directly into SparkLend — not deposited by users. Its borrow rate is governance-set via a **custom DSR-linked interest-rate strategy** (`getInterestRateStrategyAddress(DAI)` = `0x8a95998639a34462a1FdaAAa5506f66f90Ef2fdD`, differs from the standard strategy used by e.g. WETH `0xDfB6206ffc5bA5B48d2852370eE6a1bF6887476A`), and DAI is **priced at a fixed $1** in the oracle (verified `getAssetPrice(DAI)=100000000`).

### 3.4 Implementations & libraries (Ethereum)

| Role | Address |
|------|---------|
| Pool impl (live = registry; **no drift**) | `0x5aE329203E00f76891094DcfedD5Aca082a50e1b` |
| PoolConfigurator impl | `0xF7b656C95420194b79687fc86D965FB51DA4799F` |
| spToken (aToken) impl | `0x6175ddEc3B9b38c88157C10A01ed4A3fa8639cC6` |
| variableDebtToken impl | `0x86C71796CcDB31c3997F8Ec5C2E3dB3e9e40b985` |
| stableDebtToken impl (unused) | `0x026a5B6114431d8F3eF2fA0E1B2EDdDccA9c540E` |
| RewardsController impl | `0x0ee554F6A1f7a4Cb4f82D4C124DdC2AD3E37fde1` |
| Treasury impl | `0xF1E57711Eb5F897b415de1aEFCB64d9BAe58D312` |
| ConfigEngine | `0x3254F7cd0565aA67eEdC86c2fB608BE48d5cCd78` |
| ProxyAdmin | `0x883A82BDd3d07ae6ACfD151020faD350df25087e` |
| TransparentProxyFactory | `0x777803CbDD89D5D5Bc1DdD2151B51b0B07F6bf37` |
| RatesFactory | `0xfE57e187EF6285e90d7049e6a21571aa47cF11a2` |
| **Pool libraries** (delegatecall targets) | BorrowLogic `0x4662C88C542F0954F8CccCDE4542eEc32d7E7e9a` · BridgeLogic `0x2C54924711E479E639032704146b865E12f0C6D1` · EModeLogic `0x2Ad00613A66D71Ff2B0607fB3C4632C47a50DADe` · FlashLoanLogic `0x7f44e1c1dE70059D7cc483378BEFeE2a030CE247` · **LiquidationLogic** `0x6aEa92693C527bC2c7B3171C6f2598d67d619088` · PoolLogic `0x1761a0f74032963B6Ad0774C5EBF4586c0bD7604` · SupplyLogic `0x46256841e36b7557BB8e4c706beD38b17A9EB2c1` |

---

## 4. Addresses — Gnosis Chain (chain ID 100) — SparkLend instance (winding down, Q1 2026)

Source: `spark-address-registry/src/Gnosis.sol`. Pool verified live (`0x2Dae…07e0`, impl `0xCF86…B1bF` = registry, no drift) but **0 Supply logs in a 45k-block window** — consistent with the governance-approved wind-down. Governed cross-chain from Ethereum via the AMB executor. Reserves here **do** carry stableDebtTokens (older deployment). Standard Aave aToken naming (`*_ATOKEN`), not spToken.

| Role | Address |
|------|---------|
| **Pool** (proxy) | `0x2Dae5307c5E3FD1CF5A72Cb6F698f915860607e0` |
| PoolAddressesProvider | `0xA98DaCB3fC964A6A0d2ce3B77294241585EAbA6d` |
| PoolAddressesProviderRegistry | `0x49d24798d3b84965F0d1fc8684EF6565115e70c1` |
| PoolConfigurator | `0x2Fc8823E1b967D474b47Ae0aD041c2ED562ab588` |
| AaveOracle | `0x8105f69D9C41644c6A0803fDA7D03Aa70996cFD9` (same literal as ETH, different chain — key on `(chainId, addr)`) |
| ACLManager | `0x86C71796CcDB31c3997F8Ec5C2E3dB3e9e40b985` |
| ProtocolDataProvider | `0x2a002054A06546bB5a264D57A81347e23Af91D18` |
| RewardsController (`INCENTIVES`) | `0x98e6BcBA7d5daFbfa4a92dAF08d3d7512820c30C` |
| EmissionManager | `0x4d988568b5f0462B08d1F40bA1F5f17ad2D24F76` |
| Treasury | `0xb9E6DBFa4De19CCed908BcbFe1d015190678AB5f` |
| WrappedTokenGatewayV3 (WXDAI) | `0xBD7D6a9ad7865463DE44B05F04559f65e3B11704` |
| Pool impl | `0xCF86A65779e88bedfF0319FE13aE2B47358EB1bF` |
| AMB governance executor | `0xc4218C1127cB24a0D6c1e7D25dc34e10f2625f5A` |

### 4.1 Gnosis reserves (9) — underlying → aToken / variableDebtToken (+ stableDebtToken)

| Symbol | Underlying | aToken | variableDebtToken |
|--------|-----------|--------|-------------------|
| WXDAI | `0xe91D153E0b41518A2Ce8Dd3D7944Fa863463a97d` | `0xC9Fe2D32E96Bb364c7d29f3663ed3b27E30767bB` | `0x868ADfDf12A86422524EaB6978beAE08A0008F37` |
| sxDAI (sDAI) | `0xaf204776c7245bF4147c2612BF6e5972Ee483701` | `0xE877b96caf9f180916bF2B5Ce7Ea8069e0123182` | `0x1022E390E2457A78E18AEEE0bBf0E96E482EeE19` |
| WETH | `0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1` | `0x629D562E92fED431122e865Cc650Bc6bdE6B96b0` | `0x0aD6cCf9a2e81d4d48aB7db791e9da492967eb84` |
| wstETH | `0x6C76971f98945AE98dD7d4DFcA8711ebea946eA6` | `0x9Ee4271E17E3a427678344fd2eE64663Cb78B4be` | `0x3294dA2E28b29D1c08D556e2B86879d221256d31` |
| GNO | `0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb` | `0x5671b0B8aC13DC7813D36B99C21c53F6cd376a14` | `0xd4bAbF714964E399f95A7bb94B3DeaF22d9F575d` |
| USDC | `0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83` | `0x5850D127a04ed0B4F1FCDFb051b3409FB9Fe6B90` | `0xBC4f20DAf4E05c17E93676D2CeC39769506b8219` |
| USDC.e | `0x2a22f9c3b484c3629090FeED35F17Ff8F88f76F0` | `0xA34DB0ee8F84C4B90ed268dF5aBbe7Dcd3c277ec` | `0x397b97b572281d0b3e3513BD4A7B38050a75962b` |
| USDT | `0x4ECaBa5870353805a9F068101A40E0f32ed605C6` | `0x08B0cAebE352c3613302774Cd9B82D08afd7bDC4` | `0x3A98aBC6F46CA2Fc6c7d06eD02184D63C55e19B2` |
| EURe | `0xcB444e90D8198415266c6a2724b7900fb12FC56E` | `0x6dc304337BF3EB397241d1889cAE7da638e6e782` | `0x0b33480d3FbD1E2dBE88c82aAbe191D7473759D5` |

Stable debt tokens (rarely needed): WXDAI `0xab1B…EA22`, WETH `0xe21B…2f93`, wstETH `0x0F0e…4a42`, GNO `0x2f58…a33c`, USDC `0x40BF…7ae4`, USDC.e `0xC5df…6c15`, USDT `0x4cB3…23C2`, EURe `0x80F8…FDA6`, sxDAI `0x2cF7…2789`.

---

## 5. Decimals & math (same as Aave V3)

- Indices `liquidityIndex`/`variableBorrowIndex` are **rays (27-dec)**: `actual = scaled * index / 1e27`.
- `getUserAccountData` collateral/debt/borrows in **8-dec USD**; `healthFactor` in **1e18** (`< 1e18` = liquidatable; `type(uint256).max` = no debt).
- Oracle prices 8-dec USD (`BASE_CURRENCY_UNIT = 1e8`); DAI/USDS pinned to $1, sDAI/sUSDS via savings rate.
- USDC/USDT 6-dec; DAI/USDS/sDAI/sUSDS/GNO/WETH/LSTs 18-dec; WBTC/cbBTC/tBTC/LBTC 8-dec.

---

## 6. Spark non-lending footprint on the other requested chains (NO SparkLend market here)

The user listed Base, BNB, Avalanche, Arbitrum, Optimism, Polygon. **None runs a SparkLend `Pool`.** What Spark *does* deploy on the satellite chains is **Spark Savings** (sUSDS/sUSDC ERC-4626-style vaults) fed by the **Spark Liquidity Layer (ALM)** through a **PSM3** (USDC↔USDS↔sUSDS swap module), with Sky Savings Rate piped in via SSR/DSR oracles. These are a *different product* from SparkLend lending — no `Supply`/`Borrow`/`LiquidationCall`, no spTokens, no health factors. Addresses are network-specific (verified present in the registry; chain IDs noted).

| Chain | ID | ALM Controller | ALM Proxy | PSM3 | sUSDS | sUSDC |
|---|---|---|---|---|---|---|
| Base | 8453 | `0x86036CE5d2f792367C0AA43164e688d13c5A60A8` | `0x2917956eFF0B5eaF030abDB4EF4296DF775009cA` | `0x1601843c5E9bC251A3272907010AFa41Fa18347E` | `0x5875eEE11Cf8398102FdAd704C9E96607675467a` | `0x3128a0F7f0ea68E7B7c9B00AFa7E41045828e858` |
| Arbitrum One | 42161 | `0xC40611AC4Fff8572Dc5F02A238176edCF15Ea7ba` | `0x92afd6F2385a90e44da3a8B60fe36f6cBe1D8709` | `0x2B05F8e1cACC6974fD79A673a341Fe1f58d27266` | `0xdDb46999F8891663a8F2828d25298f70416d7610` | `0x940098b108fB7D0a7E374f6eDED7760787464609` |
| Optimism | 10 | `0x689502bc817E6374286af8f171Ed4715721406f7` | `0x876664f0c9Ff24D1aa355Ce9f1680AE1A5bf36fB` | `0xe0F9978b907853F354d79188A3dEfbD41978af62` | `0xb5B2dc7fd34C249F4be7fB1fCea07950784229e0` | `0xCF9326e24EBfFBEF22ce1050007A43A3c0B6DB55` |
| Unichain | 130 | `0xF16DE710899C7bdd6D46873265392CCA68e5D5bA` | `0x345E368fcCd62266B3f5F37C9a131FD1c39f5869` | `0x7b42Ed932f26509465F7cE3FAF76FfCe1275312f` | `0xA06b10Db9F390990364A3984C04FaDf1c13691b5` | `0x14d9143BEcC348920b68D123687045db49a016C6` |
| Avalanche | 43114 | `0x4eE67c8Db1BAa6ddE99d936C7D313B5d31e8fa38` | `0xecE6B0E8a54c2f44e066fBb9234e7157B15b7FeC` | *(none yet)* | *(none yet)* | *(none yet)* |
| World Chain | 480 | *(DSR oracle only)* | — | — | — | — |

- **Avalanche** has only the ALM (Liquidity Layer relayer) — no PSM3 / Savings token yet. **World Chain** has only a `DSR_AUTH_ORACLE` (`0x779053E25267B591Dcfbb20b2397462aaaD6B776`).
- Governance reaches satellites via per-chain `SkyGovRelay` + `SPARK_EXECUTOR`/`SPARK_RECEIVER` and SSR/DSR forwarders on Ethereum (`ARBITRUM_SSR_FORWARDER`, `BASE_SSR_FORWARDER`, …).
- Cross-chain stablecoin movement uses **Circle CCTP** (`CCTP_TOKEN_MESSENGER 0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` on ETH).
- **BNB Smart Chain (56) and Polygon PoS (137): no Spark contracts of any kind** (no registry file → no SparkLend, no Savings, no SLL).

---

## 7. Cross-chain summary

| Chain | ID | SparkLend Pool? | Pool address | Spark Savings / SLL? |
|---|---|---|---|---|
| **Ethereum** | 1 | ✅ active | `0xC13e…BE987` | ✅ (Savings + SLL + D3M) |
| **Gnosis** | 100 | ⚠️ winding down | `0x2Dae…07e0` | — |
| Base | 8453 | ❌ | — | ✅ Savings + SLL + PSM3 |
| Arbitrum One | 42161 | ❌ | — | ✅ Savings + SLL + PSM3 |
| Optimism | 10 | ❌ | — | ✅ Savings + SLL + PSM3 |
| Unichain | 130 | ❌ | — | ✅ Savings + SLL + PSM3 |
| Avalanche | 43114 | ❌ | — | ⚠️ SLL only |
| World Chain | 480 | ❌ | — | ⚠️ DSR oracle only |
| **BNB** | 56 | ❌ | — | ❌ no Spark |
| **Polygon PoS** | 137 | ❌ | — | ❌ no Spark |

**Three things to internalize:**
1. **SparkLend lending = Ethereum (+ Gnosis, sunsetting).** Treat any "SparkLend on L2" claim as Spark *Savings*, not the lending market.
2. **AaveOracle uses the same literal `0x8105…cFD9` on ETH and Gnosis** — always key on `(chainId, address)`.
3. **Topics/selectors are Aave V3's** — reuse the Aave V3 detection set, minus the v3.3 deficit events and v3.4 selectors (§2.5).

---

## 8. Proxies

Every SparkLend core contract is an **upgradeable proxy** (Aave's `InitializableImmutableAdminUpgradeabilityProxy`, EIP-1967 impl slot, immutable admin = PoolAddressesProvider for Pool/Configurator; admin = PoolConfigurator for spTokens/debt tokens). `PoolAddressesProvider` and `AaveOracle` are **not** proxies (plain registry / replaceable pointer). Treasury & RewardsController are transparent proxies under `ProxyAdmin` `0x883A82…087e`.

EIP-1967 implementation slot: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`. Read with `eth_getStorageAt(addr, slot)`.

### 8.1 Live implementations (read 2026-05-29) — registry is current (no drift, unlike Aave)

| Chain | Proxy | Live Pool impl | Registry `POOL_IMPL` | Drift? |
|---|---|---|---|---|
| Ethereum | `0xC13e…BE987` | `0x5aE329203E00f76891094DcfedD5Aca082a50e1b` | `0x5aE329203E00f76891094DcfedD5Aca082a50e1b` | — (matches) |
| Gnosis | `0x2Dae…07e0` | `0xCF86A65779e88bedfF0319FE13aE2B47358EB1bF` | `0xCF86A65779e88bedfF0319FE13aE2B47358EB1bF` | — (matches) |

spToken proxies → impl `0x6175ddEc…` (verified for spWETH/spDAI/spUSDC); variableDebtToken proxies → impl `0x86C71796…` (verified for variableDebtWETH). Still, **read the live EIP-1967 slot — never hard-code an impl.**

### 8.2 The `liquidationCall` dispatcher gotcha (verified, same as Aave)

On the live Ethereum Pool impl `0x5aE329…` (21,754 bytes), selector `0x00a718a9` (`liquidationCall`) is **absent from the bytecode** (raw scan + `63`-prefixed PUSH4 scan both return 0), while `supply` (`617ba037`), `borrow` (`a415bcad`), `flashLoan` (`ab9c4b5d`) are present. Yet `LiquidationCall` events fire (8 in 45k blocks) and liquidations execute — the sampled liquidation tx called a bot/adapter `0x1f2f10d1…` which reaches `Pool.liquidationCall` internally. The Pool delegatecalls **LiquidationLogic** (`0x6aEa9269…`). **Takeaway: detect liquidations by `LiquidationCall` topic0 `0xe413a321…`, never by selector** — and most liquidations arrive via third-party bots, so `tx.to` ≠ Pool.

---

## 9. Detection invariants & gotchas

1. **SparkLend lending lives on Ethereum (Pool `0xC13e…BE987`) and Gnosis (`0x2Dae…07e0`) only.** The other requested chains host Spark *Savings/SLL*, not lending (§6). BNB & Polygon have nothing.
2. **It's an Aave V3 fork** — `Supply`/`Borrow`/`Repay`/`Withdraw`/`LiquidationCall`/`FlashLoan` topics and selectors are identical to [aave/v3.md](../aave/v3.md). Reuse that detection set.
3. **No v3.3/v3.4 features.** Don't scan for `DeficitCreated`/`DeficitCovered`, `multicall`, `approvePositionManager`, `getReserveDeficit`, `getReserveAToken` — absent (§2.5). No Position Managers, no batched Multicall, no bad-debt deficit accounting.
4. **Stable rate exists in code but is config-disabled** (`stableBorrowEnabled = false` on every reserve; `interestRateMode = 1` reverts). `SwapBorrowRateMode`/`RebalanceStableBorrowRate` are dead. Gnosis reserves still have stableDebtToken contracts (~0 supply).
5. **Detect liquidations by the `LiquidationCall` event, not the selector** (§8.2) — selector absent from impl; bots route liquidations so `tx.to` ≠ Pool.
6. **spTokens rebase every block.** Store `scaledBalanceOf` + reconstruct with the reserve `liquidityIndex` (ray). Same for debt with `variableBorrowIndex`. `Mint`/`Burn` topic0 is shared between spToken and debt token — disambiguate by emitting address.
7. **`onBehalfOf` ≠ `tx.from`.** Attribute positions to `onBehalfOf`/`user` from the event, not the sender (WETHGateway, credit delegation, relayers).
8. **DAI is D3M-supplied, $1-fixed, DSR-rate.** DAI liquidity is minted by the Sky/Maker D3M (not user supply); the borrow rate is governance/DSR-set via a custom IRM (`0x8a959986…`); the oracle pins DAI at exactly `1e8`. Spikes in DAI `MintedToTreasury`/`ReserveDataUpdated` reflect Maker actions, not organic demand.
9. **CapAutomator fires `SupplyCapChanged`/`BorrowCapChanged` automatically** (not only governance) — `0x4C134163…`. **FreezerMom** (`0x237e3985…`) can fire `ReserveFrozen` outside the normal gov path; **KillSwitchOracle** (`0x909A86f7…`) can disable borrowing on a de-peg. Monitor these as risk signals.
10. **Governance = SPARK_PROXY** (`0x3300f198…`, the Spark subDAO), itself downstream of Sky's PauseProxy (`0xBE8E3e36…`). `ACLManager`/`PoolConfigurator` admin actions originate there.
11. **`AaveOracle` literal `0x8105…cFD9` is reused on ETH and Gnosis** — key on `(chainId, address)`.
12. **Flash-loan premium accrues to Treasury via `mintToTreasury`** (`MintedToTreasury`), not a direct transfer.
13. **MarketId is "Spark Protocol"** (from `PoolAddressesProvider.getMarketId()`), distinguishing it from Aave's providers when crawling `PoolAddressesProviderRegistry`.
14. **Oracle sources are not pure Chainlink.** SparkLend's `AaveOracle` aggregator points many feeds at **Aggor** adapters (Chronicle + Chainlink + Redstone median, a Sky/Chronicle product) and at fixed-price / rate-based sources for DAI/USDS/sDAI/sUSDS. Read `getSourceOfAsset(asset)` rather than assuming a Chainlink feed.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; identical to Aave V3) =====
TOPIC_SUPPLY                 = '\x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61'
TOPIC_WITHDRAW               = '\x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'
TOPIC_BORROW                 = '\xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0'
TOPIC_REPAY                  = '\xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051'
TOPIC_FLASHLOAN              = '\xefefaba5e921573100900a3ad9cf29f222d995fb3b6045797eaea7521bd8d6f0'
TOPIC_LIQUIDATIONCALL        = '\xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
TOPIC_RESERVE_DATA_UPDATED   = '\x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a'
TOPIC_COLLATERAL_ENABLED     = '\x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2'
TOPIC_COLLATERAL_DISABLED    = '\x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd'
TOPIC_MINTED_TO_TREASURY     = '\xbfa21aa5d5f9a1f0120a95e7c0749f389863cbdbfff531aa7339077a5bc919de'
TOPIC_ISOLATION_DEBT_UPDATED = '\xaef84d3b40895fd58c561f3998000f0583abb992a52fbdc99ace8e8de4d676a5'
TOPIC_USER_EMODE_SET         = '\xd728da875fc88944cbf17638bcbe4af0eedaef63becd1d1c57cc097eb4608d84'
-- spToken / debt token
TOPIC_TOKEN_MINT             = '\x458f5fa412d0f69b08dd84872b0215675cc67bc1d5b6fd93300a1c3878b86196'  -- spToken+vDebt
TOPIC_TOKEN_BURN             = '\x4cf25bc1d991c17529c25213d3cc0cda295eeaad5f13f361969b12ea48015f90'  -- spToken+vDebt
TOPIC_BALANCE_TRANSFER       = '\x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666'
TOPIC_BORROW_ALLOW_DELEGATED = '\xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1'
TOPIC_ERC20_TRANSFER         = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- PoolConfigurator (risk admin)
TOPIC_RESERVE_INITIALIZED    = '\x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f'
TOPIC_RESERVE_FROZEN         = '\x0c4443d258a350d27dc50c378b2ebf165e6469725f786d21b30cab16823f5587'
TOPIC_RESERVE_PAUSED         = '\xe188d542a5f11925d3a3af33703cdd30a43cb3e8066a3cf68b1b57f61a5a94b5'
TOPIC_SUPPLY_CAP_CHANGED     = '\x0263602682188540a2d633561c0b4453b7d8566285e99f9f6018b8ef2facef49'
TOPIC_BORROW_CAP_CHANGED     = '\xc51aca575985d521c5072ad11549bad77013bb786d57f30f94b40ed8f8dc9bc4'
-- NOTE: Aave v3.3 DeficitCreated/Covered do NOT exist on SparkLend.

-- ===== Selectors — Pool (canonical; identical to Aave V3) =====
SEL_SUPPLY                   = '\x617ba037'
SEL_SUPPLY_WITH_PERMIT       = '\x02c205f0'
SEL_WITHDRAW                 = '\x69328dec'
SEL_BORROW                   = '\xa415bcad'
SEL_REPAY                    = '\x573ade81'
SEL_REPAY_WITH_ATOKENS       = '\x2dad97d4'
SEL_LIQUIDATION_CALL         = '\x00a718a9'   -- canonical; NOT in impl dispatcher (detect via event)
SEL_FLASHLOAN                = '\xab9c4b5d'
SEL_FLASHLOAN_SIMPLE         = '\x42b0b77c'
SEL_SET_USE_RESERVE_AS_COLL  = '\x5a3b74b9'
SEL_SET_USER_EMODE           = '\x28530a47'
SEL_MINT_TO_TREASURY         = '\x9cd19996'
SEL_GET_USER_ACCOUNT_DATA    = '\xbf92857c'
SEL_GET_RESERVE_DATA         = '\x35ea6a75'
SEL_GET_RESERVES_LIST        = '\xd1946dbc'
SEL_SCALED_BALANCE_OF        = '\x1da24f3e'
SEL_GET_ASSET_PRICE          = '\xb3596f07'
-- absent on SparkLend (do NOT scan): multicall \xac9650d8, approvePositionManager \xb8caa7c5,
--   getReserveAToken \xcff027d9, getReserveDeficit \xc952485d, eliminateReserveDeficit \xa1d2f3c4

-- ===== Ethereum SparkLend (chain ID 1) =====
SPARK_ETH_POOL               = '\xc13e21b648a5ee794902342038ff3adab66be987'
SPARK_ETH_ADDRESSES_PROVIDER = '\x02c3ea4e34c0cbd694d2adfa2c690eecbc1793ee'
SPARK_ETH_POOL_CONFIGURATOR  = '\x542dba469bde58faee189ffb60c6b49ce60e0738'
SPARK_ETH_ORACLE             = '\x8105f69d9c41644c6a0803fda7d03aa70996cfd9'
SPARK_ETH_ACL_MANAGER         = '\xda135cd78a086025bcdc87b038a1c462032b510c'
SPARK_ETH_DATA_PROVIDER      = '\xfc21d6d146e6086b8359705c8b28512a983db0cb'
SPARK_ETH_POOL_IMPL          = '\x5ae329203e00f76891094dcfedd5aca082a50e1b'
SPARK_ETH_SPTOKEN_IMPL       = '\x6175ddec3b9b38c88157c10a01ed4a3fa8639cc6'
SPARK_ETH_VDEBT_IMPL         = '\x86c71796ccdb31c3997f8ec5c2e3db3e9e40b985'
SPARK_PROXY_GOVERNOR         = '\x3300f198988e4c9c63f75df86de36421f06af8c4'
SPARK_FREEZER_MOM            = '\x237e3985dd7e373f2ec878ec1ac48a228cf2e7a3'
SPARK_KILL_SWITCH_ORACLE     = '\x909a86f78e1cded68f9c2fe2c9cd922c401abe82'
SPARK_CAP_AUTOMATOR          = '\x4c1341636721b8b687647920b2e9481f3ab1f2ee'

-- ===== Gnosis SparkLend (chain ID 100) — winding down =====
SPARK_GNO_POOL               = '\x2dae5307c5e3fd1cf5a72cb6f698f915860607e0'
SPARK_GNO_ADDRESSES_PROVIDER = '\xa98dacb3fc964a6a0d2ce3b77294241585eaba6d'
SPARK_GNO_POOL_CONFIGURATOR  = '\x2fc8823e1b967d474b47ae0ad041c2ed562ab588'
SPARK_GNO_ORACLE             = '\x8105f69d9c41644c6a0803fda7d03aa70996cfd9'
SPARK_GNO_DATA_PROVIDER      = '\x2a002054a06546bb5a264d57a81347e23af91d18'
SPARK_GNO_POOL_IMPL          = '\xcf86a65779e88bedff0319fe13ae2b47358eb1bf'

-- Universal
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## 11. Verification & sources

How constants in this doc were verified (2026-05-29):

- **Event topic0 / selectors:** all recomputed locally as `keccak256(signature)` (pycryptodome). `Supply`/`Borrow`/`LiquidationCall` confirmed against live `eth_getLogs` on the Ethereum Pool `0xC13e…BE987` (614 Supply, 311 Borrow, 8 LiquidationCall in a 45k-block window); spToken `Mint`/`Burn` confirmed on spDAI `0x4DEDf261…` (33 / 24 logs).
- **Selector presence:** PUSH4 + raw byte-scan of the live Pool impl `0x5aE329…`. Present: supply/borrow/withdraw/repay/repayWithATokens/flashLoan/flashLoanSimple/supplyWithPermit/repayWithPermit/swapBorrowRateMode/rebalanceStableBorrowRate/mintUnbacked/backUnbacked/mintToTreasury/rescueTokens/eMode/views. **Absent:** `liquidationCall` (§8.2) and all v3.3/v3.4 additions (§2.5).
- **Addresses:** parsed from `sparkdotfi/spark-address-registry` (`src/SparkLend.sol`, `Ethereum.sol`, `Gnosis.sol`, `Base.sol`, `Arbitrum.sol`, `Optimism.sol`, `Avalanche.sol`, `Unichain.sol`, `WorldChain.sol`) and existence-checked via `eth_getCode`. Pool wiring (`ADDRESSES_PROVIDER`/`getPool`/`getPriceOracle`/`getACLAdmin`/`getMarketId`), token proxy impls (EIP-1967 slot), and oracle prices (`getAssetPrice(DAI)=1e8`, fixed-$1) read live. Live Pool impls equal the registry `POOL_IMPL` on both chains (no drift).
- **Chain coverage:** confirmed there is **no `Binance.sol` / `Polygon.sol`** in the registry and **no Pool** in the satellite-chain files (only ALM/PSM3/Savings) — so SparkLend lending is Ethereum + Gnosis only.

Authoritative sources:

- [`sparkdotfi/spark-address-registry`](https://github.com/sparkdotfi/spark-address-registry) — generated address libraries (source of truth).
- [`aave-dao/aave-v3-origin`](https://github.com/aave-dao/aave-v3-origin) — upstream V3 contracts (Pool/Configurator/aToken/debt token ABIs & selectors). See [aave/v3.md](../aave/v3.md).
- [`sparkdotfi/sparklend-v1-core`](https://github.com/sparkdotfi/sparklend-v1-core) (fka `marsfoundation/sparklend`) — SparkLend's V3 fork source.
- [Spark docs — SparkLend](https://docs.spark.fi/) · [Address registry site](https://docs.spark.fi/dev/deployments/address-registry).
- Explorers: [Etherscan Pool](https://etherscan.io/address/0xC13e21B648A5Ee794902342038FF3aDAB66BE987) · [Gnosisscan Pool](https://gnosisscan.io/address/0x2Dae5307c5E3FD1CF5A72Cb6F698f915860607e0).

### 11.1 Independent fact-check (2026-05-29) — all primary claims confirmed

Six non-obvious claims were cross-checked against Spark docs, the Sky governance forum, MakerDAO polls, and GitHub. Verdicts:

1. **SparkLend lending = Ethereum + Gnosis only** — ✅ confirmed. The Spark Q1 2026 report places the **Spark Liquidity Layer** (not the lending market) on Ethereum/Base/Unichain/Arbitrum/Optimism/Avalanche; the address registry has a `Pool` only in `SparkLend.sol` (Ethereum) and `Gnosis.sol`. Note the **common conflation**: press/aggregators say "Spark is on Arbitrum/Base/…", but that is Spark *Savings/SLL*, not SparkLend lending. With Gnosis sunsetting, **Ethereum is effectively the sole active SparkLend market.**
2. **Gnosis wind-down** — ✅ confirmed verbatim (Spark Q1 2026 Financial Report): *"Spark initiated the wind-down process of the SparkLend Gnosis Chain instance, removing tail risk and reducing operational overhead."* No fixed completion date published; on-chain Supply activity is already ~0.
3. **Soft fork of Aave V3, launched May 2023** — ✅ confirmed. Phoenix Labs "soft fork of Aave V3"; mainnet deploy Mar 2023, official launch 2023-05-09; Gnosis Sept 2023. The exact upstream patch (V3.0.2) is not stated in public sources, but the **on-chain selector scan proves it predates Aave v3.2/v3.3/v3.4** (the monitoring-relevant fact).
4. **DAI = D3M-supplied, $1-fixed, DSR-linked custom IRM** — ✅ confirmed. Native MakerDAO D3M (`DIRECT-SPARK-DAI`) mints DAI directly into the market; DAI borrow rate is governance/DSR-driven via a dedicated strategy (there is even a "DAI Interest Rate Strategy V2" in `sparkdotfi/sparklend-deployments`); fixed-$1 oracle verified on-chain.
5. **FreezerMom / KillSwitchOracle / CapAutomator** — ✅ all confirmed with mechanics: FreezerMom (`sparklend-freezer`, freeze/pause all-or-one market via Chief hat / ward / PauseProxy); KillSwitchOracle (disable all borrowing on collateral de-peg; activated Mar 2024, live for wstETH + LBTC at 0.95); CapAutomator (auto supply/borrow cap management, ChainSecurity-audited).
6. **Governance = Spark SubDAO Proxy `0x3300f198…`** — ✅ confirmed (exact address); it is the SparkLend owner with the **MCD Chief** as authority, downstream of Sky (ex-MakerDAO); changes ship via spells (active "Proposed Changes to Spark" spells through 2026 on the Sky forum).

**Net corrections folded in:** "fork" → "soft fork (Phoenix Labs)"; added launch dates (mainnet Mar 2023, launch 2023-05-09, Gnosis Sept 2023); enriched FreezerMom/KillSwitch/CapAutomator descriptions; added the Aggor multi-oracle note (§9.14). No claim was refuted.
