# ZeroLend (ZeroLend One) — Topics, Selectors, Addresses (Ethereum + Base; absent on BNB/Avalanche/Arbitrum/Optimism/Polygon)

**Status:** verified against Ethereum and Base mainnet RPC, the official ZeroLend deployed-addresses registry (`docs.zerolend.xyz/security/deployed-addresses`, mirror `github.com/zerolend/docs.zerolend.xyz`), and the canonical Aave V3 contract source (`aave-dao/aave-v3-origin`), on 2026-06-08.
**Scope:** the seven requested chains. **The ZeroLend "One" lending market exists on only two of them — Ethereum (chain 1) and Base (chain 8453).** ZeroLend's *primary* markets live on non-target L2s (Linea, zkSync Era, Manta, Blast, X Layer) — those are noted in §11 for completeness but **not** exhaustively verified. **BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10) and Polygon PoS (137) have NO ZeroLend One contracts** (`eth_getCode` = `0x` for every candidate address — a recorded finding, §10). Topics + selectors are chain-agnostic; addresses are network-specific.

ZeroLend One is a **soft fork of Aave V3** (V3.1/V3.2-era), so **its event topic0s and function selectors are byte-for-byte identical to Aave V3** — see [aave/v3.md](../aave/v3.md). aTokens are branded **zTokens** (`zWETH`, `zUSDC`, …) but are mechanically identical Aave aTokens; the price aggregator is an unmodified Aave `AaveOracle`; the data reader is `AaveProtocolDataProvider` (labelled `PoolDataProvider`); the incentives controller is Aave's `RewardsController`. Every core contract sits behind a proxy controlled by the `PoolAddressesProvider` / `ACLManager` governance stack. This file records what is *specific* to ZeroLend: which two target chains carry a market, the per-chain addresses (almost entirely **divergent** between ETH and Base — ZeroLend did **not** vanity-align them), the two distinct market identities, and the Aave-fork detection caveats (shared `Mint`/`Burn` topic, the `liquidationCall` dispatcher anomaly, the absent v3.3/v3.4 features).

> **Two distinct markets, two distinct identities (verified on-chain 2026-06-08).** The Ethereum deployment is an **LRT (liquid-restaking) market** — `PoolAddressesProvider.getMarketId()` returns **"LRT ZeroLend Market"**, its Etherscan labels read `…-mainnet-lrt`, and its 12 reserves are WETH + liquid-restaking tokens (weETH, ezETH, rsETH, pufETH, swETH, pzETH, two Pendle PT tokens) plus DAI/USDC/USDT. The Base deployment (`getMarketId()` = **"Base ZeroLend Market"**) is a broader 18-reserve market (WETH, AERO, USDC, cbETH, cbBTC, LBTC, OETH/superOETH, USDz/sUSDz, ZAI, USR, Pendle PTs, …). They share the **same ABI** but **different addresses and reserves**.

> **Version / lineage note (verified on-chain 2026-06-08).** The live Pool impls (`0xFF67…9385` on ETH, `0x8010…3A80` on Base) are an **Aave V3.1/V3.2-era Pool**. Bytecode selector scan: `supply`/`borrow`/`withdraw`/`repay`/`repayWithATokens`/`flashLoan`/`flashLoanSimple`/`mintUnbacked`/`mintToTreasury`/`rescueTokens` are **present**; the Aave **v3.3** (`getReserveDeficit`, `DeficitCreated`/`DeficitCovered`) and **v3.4** (`multicall`, `getReserveAToken`, Position Managers) additions are **all absent**. The `ReserveData` struct still carries the legacy `stableDebtTokenAddress` slot (id packed at struct word 7, token addrs at words 8/9/10) — confirming pre-v3.2-removal era — but stable-rate borrowing is disabled by config. There is no ZeroLend "v2" and no hub-and-spoke; each chain is one continuously-patched deployment.

> **Liquidation dispatcher anomaly (verified, same as Aave/Spark).** The canonical `liquidationCall` selector `0x00a718a9` is **absent from the live Pool impl bytecode** on both chains (raw + PUSH4 scan = 0 occurrences) even though `supply`/`borrow`/`flashLoan` are present, yet `LiquidationCall` events fire normally (16 logs in a 50k-block window on the ETH Pool; 1 on Base). **Detect ZeroLend liquidations by the `LiquidationCall` event topic0 `0xe413a321…`, never by the function selector.** See §8.2.

---

## 0. Contract families & versions

| Family | Role | Aave-fork name | Per-chain? | Proxy? |
|--------|------|----------------|-----------|--------|
| **PoolAddressesProvider** | per-market registry / source of truth | same | yes | no (plain registry) |
| **PoolAddressesProviderRegistry** | lists addresses-providers | same | ETH only (listed) | no |
| **Pool** | lending entrypoint; emits §1.1 events | same | yes | yes (Transparent) |
| **PoolConfigurator** | risk-admin; emits §1.3 events | same | yes | yes (Transparent) |
| **zToken** (= aToken) | per-reserve interest-bearing rebasing token | aToken | per reserve | yes (impl shared per chain) |
| **variableDebtToken** | per-reserve debt token | same | per reserve | yes |
| **stableDebtToken** | legacy stable-debt token (disabled) | same | per reserve | yes |
| **AaveOracle** | USD price aggregator (1e8) | same | yes | no (replaceable pointer) |
| **ACLManager** | role registry (POOL_ADMIN, RISK_ADMIN, …) | same | yes | no |
| **PoolDataProvider** | reserve/user read helper | AaveProtocolDataProvider | yes | no |
| **RewardsController** (`IncentivesProxy`) | liquidity-mining rewards | same | yes | yes (Transparent) |
| **EmissionManager** | configures reward emissions | same | yes | no |
| **Treasury / Collector** | reserve-factor / fee sink | Collector | yes | yes (minimal-proxy clone) |
| **WrappedTokenGatewayV3** | ETH↔WETH supply/repay helper | same | yes | no |
| **UiPoolDataProviderV3** / **UiIncentiveDataProviderV3** | front-end batch readers | same | yes | no |
| **ZERO token / OFT** | governance/utility token (LayerZero OFT) | — | native Linea; OFT mirrors | n/a |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Identical to Aave V3 (ZeroLend is a fork). All values recomputed locally with keccak on 2026-06-08; `Withdraw`/`LiquidationCall`/`ReserveDataUpdated` additionally confirmed against live ZeroLend Pool logs on both chains.

### 1.1 Pool (emits all lending activity) — emitter on ETH = `0x3BC3…B4c0`, on Base = `0x766f…c671`

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
| `0xbfa21aa5d5f9a1f0120a95e7c0749f389863cbdbfff531aa7339077a5bc919de` | `MintedToTreasury(address indexed reserve, uint256 amountMinted)` |
| `0xaef84d3b40895fd58c561f3998000f0583abb992a52fbdc99ace8e8de4d676a5` | `IsolationModeTotalDebtUpdated(address indexed asset, uint256 totalDebt)` |
| `0xd728da875fc88944cbf17638bcbe4af0eedaef63becd1d1c57cc097eb4608d84` | `UserEModeSet(address indexed user, uint8 categoryId)` |
| `0xf25af37b3d3ec226063dc9bdc103ece7eb110a50f340fe854bb7bc1b0676d7d0` | `MintUnbacked(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint16 indexed referralCode)` (Portal — present, unused) |
| `0x281596e92b2d974beb7d4f124df30a0b39067b096893e95011ce4bdad798b759` | `BackUnbacked(address indexed reserve, address indexed backer, uint256 amount, uint256 fee)` (Portal — present, unused) |
| `0x7962b394d85a534033ba2efcf43cd36de57b7ebeb3de0ca4428965d9b3ddc481` | `SwapBorrowRateMode(address indexed reserve, address indexed user, uint8 interestRateMode)` (stable disabled; legacy) |
| `0x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300` | `RebalanceStableBorrowRate(address indexed reserve, address indexed user)` (legacy) |

`Withdraw`/`Borrow`/`Supply` are the workhorses. `interestRateMode` is `uint8` (2 = variable; 1 = stable, never enabled). **`Supply` ≠ Aave V2 `Deposit`** (different topic0). **Aave v3.3 `DeficitCreated`/`DeficitCovered` do NOT exist on ZeroLend** (feature not forked).

### 1.2 zToken & variableDebtToken (per-reserve, scaled rebasing — Aave aToken mechanics)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x458f5fa412d0f69b08dd84872b0215675cc67bc1d5b6fd93300a1c3878b86196` | `Mint(address indexed caller, address indexed onBehalfOf, uint256 value, uint256 balanceIncrease, uint256 index)` | zToken **and** variableDebtToken |
| `0x4cf25bc1d991c17529c25213d3cc0cda295eeaad5f13f361969b12ea48015f90` | `Burn(address indexed from, address indexed target, uint256 value, uint256 balanceIncrease, uint256 index)` | zToken **and** variableDebtToken |
| `0x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666` | `BalanceTransfer(address indexed from, address indexed to, uint256 value, uint256 index)` | zToken only |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 (zToken; debt tokens emit on mint/burn) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | zToken (ERC-20 + EIP-2612) |
| `0xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1` | `BorrowAllowanceDelegated(address indexed fromUser, address indexed toUser, address indexed asset, uint256 amount)` | debt token (credit delegation) |

**Same `Mint`/`Burn` topic0 on zToken and variableDebtToken** — disambiguate by the emitting `address` (look up whether it is a zToken or a debt token). `value` is the actual amount; `index` is the reserve `liquidityIndex`/`variableBorrowIndex` (ray, 27-dec) so `scaled = value * 1e27 / index`.

### 1.3 PoolConfigurator (governance/risk-admin) — ETH `0x09Ed…8B5f`, Base `0xB40e…e6E3`

| topic0 | Event |
|--------|-------|
| `0x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f` | `ReserveInitialized(address indexed asset, address indexed aToken, address stableDebtToken, address variableDebtToken, address interestRateStrategyAddress)` |
| `0x637febbda9275aea2e85c0ff690444c8d87eb2e8339bbede9715abcc89cb0995` | `CollateralConfigurationChanged(address indexed asset, uint256 ltv, uint256 liquidationThreshold, uint256 liquidationBonus)` |
| `0x2443ba28e8d1d88d531a3d90b981816a4f3b3c7f1fd4085c6029e81d1b7a570d` | `ReserveBorrowing(address indexed asset, bool enabled)` |
| `0x0c4443d258a350d27dc50c378b2ebf165e6469725f786d21b30cab16823f5587` | `ReserveFrozen(address indexed asset, bool frozen)` |
| `0xe188d542a5f11925d3a3af33703cdd30a43cb3e8066a3cf68b1b57f61a5a94b5` | `ReservePaused(address indexed asset, bool paused)` |
| `0xc36c7d11ba01a5869d52aa4a3781939dab851cbc9ee6e7fdcedc7d58898a3f1e` | `ReserveActive(address indexed asset, bool active)` |
| `0xb46e2b82b0c2cf3d7d9dece53635e165c53e0eaa7a44f904d61a2b7174826aef` | `ReserveFactorChanged(address indexed asset, uint256 oldReserveFactor, uint256 newReserveFactor)` |
| `0x0263602682188540a2d633561c0b4453b7d8566285e99f9f6018b8ef2facef49` | `SupplyCapChanged(address indexed asset, uint256 oldSupplyCap, uint256 newSupplyCap)` |
| `0xc51aca575985d521c5072ad11549bad77013bb786d57f30f94b40ed8f8dc9bc4` | `BorrowCapChanged(address indexed asset, uint256 oldBorrowCap, uint256 newBorrowCap)` |
| `0xdb8dada53709ce4988154324196790c2e4a60c377e1256790946f83b87db3c33` | `ReserveInterestRateStrategyChanged(address indexed asset, address oldStrategy, address newStrategy)` |
| `0x0acf8b4a3cace10779798a89a206a0ae73a71b63acdd3be2801d39c2ef7ab3cb` | `EModeCategoryAdded(uint8 indexed categoryId, uint256 ltv, uint256 liquidationThreshold, uint256 liquidationBonus, address oracle, string label)` |
| `0x5bb69795b6a2ea222d73a5f8939c23471a1f85a99c7ca43c207f1b71f10c6264` | `EModeAssetCategoryChanged(address indexed asset, uint8 oldCategoryId, uint8 newCategoryId)` |
| `0xb5b0a963825337808b6e3154de8e98027595a5cad4219bb3a9bc55b192f4b391` | `LiquidationProtocolFeeChanged(address indexed asset, uint256 oldFee, uint256 newFee)` |

### 1.4 AaveOracle (ZeroLend keeps Aave's oracle aggregator) — ETH `0x1cc9…3385`, Base `0xF49E…d82c`

| topic0 | Event |
|--------|-------|
| `0x22c5b7b2d8561d39f7f210b6b326a1aa69f15311163082308ac4877db6339dc1` | `AssetSourceUpdated(address indexed asset, address indexed source)` |
| `0xe27c4c1372396a3d15a9922f74f9dfc7c72b1ad6d63868470787249c356454c1` | `BaseCurrencySet(address indexed baseCurrency, uint256 baseCurrencyUnit)` |
| `0xce7a780d33665b1ea097af5f155e3821b809ecbaa839d3b33aa83ba28168cefb` | `FallbackOracleUpdated(address indexed fallbackOracle)` |

### 1.5 Proxy & RewardsController (incidental)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | every Transparent/UUPS proxy (Pool, Configurator, Incentives, zTokens) |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | proxy admin change |
| `0xc052130bc4ef84580db505783484b067ea8b71b3bca78a7e12db7aea8658f004` | `RewardsClaimed(address indexed user, address indexed reward, address indexed to, address claimer, uint256 amount)` | RewardsController |
| `0x265d57baf657b18682d2860b3be72b97974eccdf217e7c93949449e6cf9cfec4` | `Accrued(address indexed asset, address indexed reward, address indexed user, uint256 assetIndex, uint256 rewardsAccrued)` | RewardsController |

---

## 2. Function signatures (chain-agnostic)

Selectors = `keccak256(canonical signature)[0:4]`. All Pool selectors below verified **present** in the live Pool impl bytecode (`0xFF67…9385` on ETH, `0x8010…3A80` on Base) on 2026-06-08 **except `liquidationCall`** (§8.2). The Aave v3.3/v3.4 selectors are listed at the end as **absent on ZeroLend**.

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
| `0x9cd19996` | `mintToTreasury(address[] assets)` | Sweeps reserve factor to Collector. |
| `0xcea9d26f` | `rescueTokens(address token, address to, uint256 amount)` | Recover stuck tokens (POOL_ADMIN). |

### 2.2 Pool — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xbf92857c` | `getUserAccountData(address user)` | `(totalCollateralBase, totalDebtBase, availableBorrowsBase, currentLiquidationThreshold, ltv, healthFactor)` — first 5 in **8-dec USD**, HF in **1e18**. |
| `0x35ea6a75` | `getReserveData(address asset)` | Full `ReserveData` struct — **legacy layout**: config(0), liquidityIndex(1), liquidityRate(2), variableBorrowIndex(3), variableBorrowRate(4), stableBorrowRate(5), lastUpdateTimestamp+id packed(6/7), **aToken(8), stableDebtToken(9), variableDebtToken(10), interestRateStrategy(11)**. |
| `0xd15e0053` | `getReserveNormalizedIncome(address asset)` | `uint256` ray — supply index. |
| `0x386497fd` | `getReserveNormalizedVariableDebt(address asset)` | `uint256` ray — borrow index. |
| `0xc44b11f7` | `getConfiguration(address asset)` | Packed reserve config bitmap. |
| `0x4417a583` | `getUserConfiguration(address user)` | Packed user collateral/borrow bitmap. |
| `0xd1946dbc` | `getReservesList()` | `address[]` — all reserve underlyings (12 on ETH, 18 on Base). |
| `0xeddf1b79` | `getUserEMode(address user)` | `uint256` category id. |
| `0x0542975c` | `ADDRESSES_PROVIDER()` | The owning PoolAddressesProvider. |

### 2.3 zToken / variableDebtToken

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1da24f3e` | `scaledBalanceOf(address user)` | **Use for accounting** — `balanceOf` rebases every block. |
| `0xb1bf962d` | `scaledTotalSupply()` | `uint256`. |
| `0xb16a19de` | `UNDERLYING_ASSET_ADDRESS()` | Underlying reserve token. |
| `0x7535d246` | `POOL()` | Owning Pool. |
| `0xc04a8a10` | `approveDelegation(address delegatee, uint256 amount)` | debt token — credit delegation. |
| `0x6bd76d24` | `borrowAllowance(address fromUser, address toUser)` | debt token. |
| `0x70a08231` / `0x18160ddd` | `balanceOf` / `totalSupply` | **Rebasing** — changes every block. |

### 2.4 AaveOracle / PoolDataProvider / PoolAddressesProvider

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xb3596f07` | `getAssetPrice(address asset)` → `uint256` | AaveOracle (8-dec USD; `BASE_CURRENCY_UNIT = 1e8`, confirmed live = `0x5f5e100`). |
| `0x9d23d9f2` | `getAssetsPrices(address[] assets)` → `uint256[]` | AaveOracle. |
| `0x92bf2be0` | `getSourceOfAsset(address asset)` → `address` | AaveOracle (feed/adapter). |
| `0xe19f4700` | `BASE_CURRENCY()` → `address` | AaveOracle (0x0 = USD). |
| `0x8c89b64f` | `BASE_CURRENCY_UNIT()` → `uint256` | AaveOracle (1e8). |
| `0x568ef470` | `getMarketId()` → `string` | PoolAddressesProvider ("LRT ZeroLend Market" / "Base ZeroLend Market"). |
| `0x026b1d5f` | `getPool()` → `address` | PoolAddressesProvider. |
| `0xfca513a8` | `getPriceOracle()` → `address` | PoolAddressesProvider. |
| `0x707cd716` | `getACLManager()` → `address` | PoolAddressesProvider. |
| `0x631adfca` | `getPoolConfigurator()` → `address` | PoolAddressesProvider. |
| `0xe860accb` | `getPoolDataProvider()` → `address` | PoolAddressesProvider. |

### 2.5 RewardsController

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x236300dc` | `claimRewards(address[] assets, uint256 amount, address to, address reward)` → `uint256` | Emits `RewardsClaimed`. |
| `0xbb492bf5` | `claimAllRewards(address[] assets, address to)` → `(address[], uint256[])` | |

### 2.6 Aave selectors **absent on ZeroLend** (do NOT scan for these — feature not forked)

| Selector | Signature | Aave version |
|----------|-----------|--------------|
| `0xac9650d8` | `multicall(bytes[])` | v3.4 — absent (scan = 0) |
| `0xcff027d9` | `getReserveAToken(address)` | v3.4 — absent |
| `0xc952485d` | `getReserveDeficit(address)` | v3.3 — absent |
| `0xb8caa7c5` | `approvePositionManager(address,bool)` | v3.4 — absent (no Position Managers) |

---

## 3. Addresses — Ethereum mainnet (chain ID 1) — the "LRT ZeroLend Market"

Source: `docs.zerolend.xyz/security/deployed-addresses`. All verified via `eth_getCode` / `eth_call` on `https://ethereum-rpc.publicnode.com` on 2026-06-08. Wiring confirmed: `Pool.ADDRESSES_PROVIDER()` → Provider; `Provider.getPool()` → Pool (round-trip); `Provider.getMarketId()` = **"LRT ZeroLend Market"**; `Provider.getPriceOracle()` → AaveOracle; `Provider.getACLManager()` → ACLManager; `Provider.getPoolConfigurator()`/`getPoolDataProvider()` match the table.

### 3.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| **Pool** (proxy) | `0x3BC3D34C32cc98bf098D832364Df8A222bBaB4c0` | Main lending entrypoint; emits all §1.1 events. |
| **PoolAddressesProvider** | `0xFD856E1a33225B86f70D686f9280435E3fF75FCF` | Per-market registry / source of truth. |
| PoolAddressesProviderRegistry | `0x7503A8823B523629E28587317901BA4C055791eb` | Lists ZeroLend addresses-providers. |
| **PoolConfigurator** (proxy) | `0x09EdC8F101897AA693932c1966725E05d6D68B5f` | Risk-admin; emits §1.3 events. |
| **AaveOracle** | `0x1cc993f2C8b6FbC43a9bafd2A44398E739733385` | Price aggregator (USD, 1e8). |
| **ACLManager** | `0x749dF84Fd6DE7c0A67db3827e5118259ed3aBBa5` | Role registry (POOL_ADMIN, RISK_ADMIN, …). |
| **PoolDataProvider** (AaveProtocolDataProvider) | `0x47223D4eA966a93b2cC96FFB4D42c22651FADFcf` | Read helper for reserve/user data. |
| RewardsController (`IncentivesProxy`) | `0x5be89bB10E2234204A2607765714916Ed95a73a2` | Liquidity-mining rewards. |
| EmissionManager | `0x859C2ca97EAd2742a0758bc9dD889e9D0e7e84E8` | Configures reward emissions. |
| Treasury / Collector (proxy) | `0x464c71f6c2f760dda6093dcb91c24c39e5d6e18c` | Reserve-factor / fee sink. |
| Treasury Controller | `0x5300A1a15135EA4dc7aD5a167152C01EFc9b192A` | Treasury admin. |
| WrappedTokenGatewayV3 (`WETH_GATEWAY`) | `0x6eA9d99c6653DF987bDEa11ffcd56DFB4B5d38b4` | ETH↔WETH supply/repay helper. |
| UiPoolDataProviderV3 | `0xa6EA08D16d47feE408505fda73520EbefC68Ef01` | Front-end batch reader. |
| UiIncentiveDataProviderV3 | `0x0A1198DDb5247a283F76077Bb1E45e5858ee100b` | (same literal also = Base's UiPoolDataProviderV3 — key on `(chainId, addr)`). |

### 3.2 Reserves (12) — underlying → zToken / variableDebtToken

zToken impl (shared) = `0xb7ed499e7570ee7691eef4df9d708d258de2b512`; variableDebtToken impl = `0x5d50be703836c330fc2d147a631cdd7bb8d7171c` (both verified live via EIP-1967 slot). This is an **LRT (liquid-restaking) market**; reserves still carry legacy stableDebtToken slots (disabled).

| Symbol | Underlying | zToken | variableDebtToken |
|--------|-----------|--------|-------------------|
| DAI | `0x6b175474e89094c44da98b954eedeac495271d0f` | `0x29a3a6af690942a3b7665bb2839a3f563c6f987b` | `0x0047cac82cf5fb36954de1b9d86d657915ab3b47` |
| USDC | `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` | `0xb2feb2c46305329a340e6188532f31fce9347a5c` | `0x227f86fbfccb5664403b62a5b6d4e0e593968275` |
| USDT | `0xdac17f958d2ee523a2206206994597c13d831ec7` | `0x6c735966bc965bd4066c14fca3df443496ce14fb` | `0xdaccf47046ae4fee3f9f3bcfe68696a95db6ccb7` |
| WETH | `0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | `0xfb932a75c5f69d03b0f6e59573fde6976af0d88c` | `0x7ef98cd28902ce57b7aeec66dfb06b454cda1941` |
| weETH | `0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee` | `0x84e55c6bc5b7e9505d87b3df6ceff7753e15a0c5` | `0x53c94fd63ef4001d45744c311d6bbe2171d4a11e` |
| ezETH | `0xbf5495efe5db9ce00f80364c8b423567e58d2110` | `0x68fd75cf5a91f49effad0e857ef2e97e5d1f35e7` | `0x27c1706ddd2467622ca63aaec03332127919a690` |
| rsETH | `0xa1290d69c65a6fe4df752f95823fae25cb99e5a7` | `0xef4a41e692319ae4aa596314d282b3f2a3830bed` | `0xe4fe2d282dead5759199df364f3f419dfac17339` |
| pufETH | `0xd9a442856c234a39a81a089c06451ebaa4306a72` | `0xdd7afc0f014a1e1716307ff040704fa12e8d33a3` | `0xf99728a4b9f3371cfcf671099edf00f49b006125` |
| swETH | `0xf951e335afb289353dc249e82926178eac7ded78` | `0xb7cadc9cdfbbef6d230dd99a7c62e294fc44bfc6` | `0xb04adaff2f221f63b977185f5a7d8ee49aacbaff` |
| pzETH | `0x8c9532a60e0e7c6bbd2b2c1303f63ace1c3e9811` | `0xd9855847ffd9bc0c5f3effbef67b558dbf090a71` | `0x8e3e54599d6f40c8306b895214f54882d98cd2b5` |
| PT-rsETH-26SEP2024 | `0x7baf258049cc8b9a78097723dc19a8b103d4098f` | `0x7740f60f773bc743ed76310ac1d054a4a4a17e7c` | `0xb8d45c7fbbbc6e1d36bc1caa7d43dcc7d0513cfd` |
| PT-ezETH-26DEC2024 | `0xf7906f274c174a52d444175729e3fa98f9bde285` | `0xb2db477a6c198f5c524302bb67085f8f3ab06059` | `0x8eb2f05a24b6859aadb5d26abbc129f53d10e934` |

### 3.3 Implementations (Ethereum)

| Role | Address |
|------|---------|
| Pool impl | `0xFF679e5B4178A2f74A56f0e2c0e1FA1C80579385` |
| PoolConfigurator impl | `0x9C6F1367256bE65eE744740c72aD80dA5bc96cA6` |
| zToken (aToken) impl | `0xb7ed499e7570ee7691eef4df9d708d258de2b512` |
| variableDebtToken impl | `0x5d50be703836c330fc2d147a631cdd7bb8d7171c` |
| RewardsController impl (IncentivesV2) | `0x854138f891FE0A86270f6F153A06fBfabF69E0Ad` |
| Treasury / Collector impl | `0x80f2c02224a2E548FC67c0bF705eBFA825dd5439` |

### 3.4 ZERO token (Ethereum)

| Role | Address |
|------|---------|
| ZERO (LayerZero OFT) | `0x11dCc26d4bDAc03FFa8841f69313C38240FC429e` | (confirmed `symbol()`="ZERO", `name()`="ZeroLend"). The canonical/native ZERO is on **Linea** `0x78354f8dccb269a615a7e0a24f9b0718fdc3c7a7` (§11). |

---

## 4. Addresses — Base mainnet (chain ID 8453) — the "Base ZeroLend Market"

Source: `docs.zerolend.xyz/security/deployed-addresses`. All verified via `eth_getCode` / `eth_call` on `https://base-rpc.publicnode.com` on 2026-06-08. Wiring confirmed: `Pool.ADDRESSES_PROVIDER()` → Provider; `Provider.getPool()` → Pool; `Provider.getMarketId()` = **"Base ZeroLend Market"**; oracle/ACL/configurator match. **Addresses diverge from Ethereum** (no vanity alignment).

### 4.1 Core protocol

| Role | Address |
|------|---------|
| **Pool** (proxy) | `0x766f21277087E18967c1b10bF602d8Fe56d0c671` |
| **PoolAddressesProvider** | `0x5213ab3997a596c75Ac6ebF81f8aEb9cf9A31007` |
| **PoolConfigurator** (proxy) | `0xB40e21D5cD8E9E192B0da3107883f8b0f4e4e6E3` |
| **AaveOracle** | `0xF49Ee3EA9C56D90627881d88004aaBDFc44Fd82c` |
| **ACLManager** | `0x1cc993f2C8b6FbC43a9bafd2A44398E739733385` (same literal as **ETH's AaveOracle** — key on `(chainId, addr)`) |
| **PoolDataProvider** | `0xA754b2f1535287957933db6e2AEE2b2FE6f38588` |
| RewardsController (`IncentivesProxy`) | `0x73a7a4B40f3FE11e0BcaB5538c75D3B984082CAE` |
| EmissionManager | `0x0f9bfa294bE6e3CA8c39221Bb5DFB88032C8936E` |
| Treasury / Collector (minimal-proxy clone) | `0x6F5Ae60d89dbbc4EeD4B08d08A68dD5679Ac61B4` |
| WrappedTokenGatewayV3 | `0x11CCDcFb19151FEb086ee6F1f62bfA0940C85612` |
| UiPoolDataProviderV3 | `0x0A1198DDb5247a283F76077Bb1E45e5858ee100b` (same literal as ETH's UiIncentiveDataProviderV3) |
| UiIncentiveDataProviderV3 | `0xa1e6BcDab01B9d7De83647d1Bbd4113c6c2B4e0d` |

### 4.2 Reserves (18) — underlying → zToken / variableDebtToken

zToken impl (shared) = `0xe230cf9cee7b299f69778ef950a61de0de520ba7` (verified live via EIP-1967 slot).

| Symbol | Underlying | zToken | variableDebtToken |
|--------|-----------|--------|-------------------|
| WETH | `0x4200000000000000000000000000000000000006` | `0x4677201dbb575d485ad69e5c5b1e7e7888c3ab29` | `0xfec889b48d8cb51bfd988bf211d4cfe854af085c` |
| AERO | `0x940181a94a35a4569e4529a3cdfb74e38fd98631` | `0x3c2b86d6308c24632bb8716ed013567c952b53ae` | `0x98ef767a6184323bf2788a0936706432698d3400` |
| USDC | `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` | `0xd09600475435cab0e40dabdb161fb5a3311efcb3` | `0xa397391b718f3c7f21c63e8beb09b66607419c38` |
| xUSDz | `0x0a27e060c0406f8ab7b64e3bee036a37e5a62853` | `0x2e1f66d89a95a88afe594f6ed936b1ca76efb74c` | `0x5e4043a302a827bfa4cb51fa18c66109683d08ee` |
| cbETH | `0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22` | `0x1f3f89ffc8cd686cecc845b5f52246598f1e3196` | `0x371cfa36ef5e33c46d1e0ef2111862d5ff9f78cd` |
| cbBTC | `0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf` | `0x4433cf6e9458027ff0833f22a3cf73318908e48e` | `0x7e1b2ac5339e8bba83c67a9444e9ee981c46ce42` |
| vAMM-USDC/AERO | `0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d` | `0xb6ccd85f92fb9a8bbc99b55091855714aaeebfee` | `0x80e898e5ad81940fe094ac3159b08a3494198570` |
| sUSDZUSDC | `0x1097dfe9539350cb466df9ca89a5e61195a520b0` | `0x89bb87137afe8bae03f4ab286de667a513ceebdd` | `0x6b0b75c223ddd146b213ef4e35bc61d1de7b46a4` |
| USDz | `0x04d5ddf5f3a8939889f11e97f8c4bb48317f1938` | `0x9357e7f1c49e6d0094287f882fc47774fd3bc291` | `0x19887e3d984cbbd75805dfdbc9810efe923b897f` |
| sUSDz | `0xe31ee12bdfdd0573d634124611e85338e2cbf0cf` | `0xf382e613ff8ee69f3f7557424e7cfd48792286c5` | `0x591d8d962278bd35182decb2852de50f83dd29d0` |
| superOETHb | `0xdbfefd2e8460a6ee4955a68582f85708baea60a3` | `0xe48d605bb303f7e88561a9b09640af4323c5b921` | `0xd6290195faab4b78f43eb38554e36f243218f334` |
| pumpBTC | `0xf469fbd2abcd6b9de8e169d128226c0fc90a012e` | `0x4759417285100f0a11846304af76d1ed8d9ad253` | `0x95beb0d11951e3e4140f1265b3df76f685740e18` |
| wsuperOETHb | `0x7fcd174e80f264448ebee8c88a7c4476aaf58ea6` | `0x134efc999957fc7984c5ab91bc7ec0f0d373b71e` | `0x1c7f3d9d02ad5fefd1a8feed65957be1ea5f649c` |
| LBTC | `0xecac9c5f704e954931349da37f60e39f515c11c1` | `0xbbb4080b4d4510ace168d1ff8c5cc256ab74e1fb` | `0x8307952247925a2ed9f5729eaf67172a77e08999` |
| PT-cbETH-25DEC2025 | `0xe46c8ba948f8071b425a1f7ba45c0a65cbacea2e` | `0xfc68bfbf891c0e61bc0dba0a2db05632e551e570` | `0x053cf31de7d82deac8e026ac2078bf7d9d3eab14` |
| PT-LBTC-29MAY2025 | `0x5d746848005507da0b1717c137a10c30ad9ee307` | `0x09ff10b3bd188eaf1b972379cc4940833361e5a8` | `0xa59ba82be54926368407f67fc80a26e4768b6dd1` |
| ZAI | `0x69000dfd5025e82f48eb28325a2b88a241182ced` | `0xb2de5acea05a42b05d05bcf252a2e15a3c93c19e` | `0xc9fcd2e88662191706657adc69a3cbdd641d53ae` |
| USR | `0x35e5db674d8e93a03d814fa0ada70731efe8a4b9` | `0x9e08e9119883f9ffc59f97bbab45340f4da0db39` | `0x4dfa4449f0ddd7fdea916d1242acd8a7f78259df` |

### 4.3 Implementations (Base)

| Role | Address |
|------|---------|
| Pool impl | `0x80102a3cbAcADa39560555340e1bC567B83C3A80` |
| PoolConfigurator impl | `0x749dF84Fd6DE7c0A67db3827e5118259ed3aBBa5` (same literal as **ETH's ACLManager** — collision, key on `(chainId, addr)`) |
| zToken (aToken) impl | `0xe230cf9cee7b299f69778ef950a61de0de520ba7` |
| RewardsController impl (IncentivesV2) | `0xaa999eA356F925BF1e856038c5D182Ae5E8A4973` |
| Treasury / Collector clone target (read via `masterCopy()` 0xa619486e) | `0xfb1bffc9d739b8d520daf37df666da4c687191ea` |

---

## 5. Decimals & math (same as Aave V3)

- Indices `liquidityIndex`/`variableBorrowIndex` are **rays (27-dec)**: `actual = scaled * index / 1e27`.
- `getUserAccountData` collateral/debt/borrows in **8-dec USD**; `healthFactor` in **1e18** (`< 1e18` = liquidatable; `type(uint256).max` = no debt).
- Oracle prices 8-dec USD (`BASE_CURRENCY_UNIT = 1e8`, confirmed live on both chains). E.g. `getAssetPrice(WETH)` on ETH returned `0x27544c2180` (~$1689).
- USDC/USDT 6-dec; DAI/WETH/LSTs/LRTs 18-dec; WBTC/cbBTC/LBTC/pumpBTC 8-dec.

---

## 6. Target chains with NO ZeroLend One deployment (recorded findings)

For each chain below, every candidate ZeroLend address (the ETH Pool/Provider and the Base Pool/Provider literals, and—by extension—any core contract) returns `eth_getCode = 0x`. **There is no ZeroLend One market on any of these five target chains.** ZeroLend's other live markets are on non-target L2s (§11).

| Chain | ID | RPC | Result |
|---|---|---|---|
| BNB Smart Chain | 56 | `https://bsc-rpc.publicnode.com` | ❌ no code at any ZeroLend address |
| Avalanche C-Chain | 43114 | `https://avalanche-c-chain-rpc.publicnode.com` | ❌ no code |
| Arbitrum One | 42161 | `https://arbitrum-one-rpc.publicnode.com` | ❌ no code |
| Optimism | 10 | `https://optimism-rpc.publicnode.com` | ❌ no code |
| Polygon PoS | 137 | `https://polygon-bor-rpc.publicnode.com` | ❌ no code |

---

## 7. Cross-chain summary

Presence matrix — rows = chains (+ID), cols = key contracts. Cell = address (truncated) or ❌.

| Chain | ID | ZeroLend Pool? | Pool | PoolAddressesProvider | AaveOracle | ACLManager | MarketId |
|---|---|---|---|---|---|---|---|
| **Ethereum** | 1 | ✅ active | `0x3BC3…B4c0` | `0xFD85…5FCF` | `0x1cc9…3385` | `0x749d…BBa5` | "LRT ZeroLend Market" |
| **Base** | 8453 | ✅ active | `0x766f…c671` | `0x5213…1007` | `0xF49E…d82c` | `0x1cc9…3385` | "Base ZeroLend Market" |
| BNB | 56 | ❌ | — | — | — | — | — |
| Avalanche | 43114 | ❌ | — | — | — | — | — |
| Arbitrum One | 42161 | ❌ | — | — | — | — | — |
| Optimism | 10 | ❌ | — | — | — | — | — |
| Polygon PoS | 137 | ❌ | — | — | — | — | — |

**Address-collision tells (key on `(chainId, address)`):**
- `0x1cc993f2…3385` = **ETH AaveOracle** AND **Base ACLManager** (different role on each chain).
- `0x749dF84F…BBa5` = **ETH ACLManager** AND **Base PoolConfigurator impl**.
- `0x0A1198DD…100b` = **ETH UiIncentiveDataProviderV3** AND **Base UiPoolDataProviderV3**.
- `0x7503A882…91eb` = **ETH PoolAddressesProviderRegistry** AND (per registry) **Blast ACLManager**.
- `0xFF679e5B…9385` = **ETH Pool impl** AND (per registry) **Linea/Manta AaveOracle** — these are CREATE2 redeploys of the same bytecode, NOT the same contract.

**Three things to internalize:**
1. **ZeroLend One lending = Ethereum + Base** among the target chains. The bulk of ZeroLend TVL is on **Linea / zkSync / Manta / Blast / X Layer** (non-target; §11).
2. **Topics/selectors are Aave V3's** — reuse the Aave V3 detection set, minus the v3.3/v3.4 additions (§2.6).
3. ETH and Base addresses **diverge** and several literals **collide cross-chain in different roles** — always key on `(chainId, address)`.

---

## 8. Proxies

Every ZeroLend core contract that holds state is an **upgradeable proxy** (Aave's `InitializableImmutableAdminUpgradeabilityProxy`, EIP-1967 impl slot; immutable admin = PoolAddressesProvider for Pool/Configurator; admin = PoolConfigurator for zTokens/debt tokens). `PoolAddressesProvider`, `AaveOracle`, `ACLManager`, `PoolDataProvider`, `EmissionManager` are **not** proxies (plain registry / replaceable pointer — EIP-1967 impl slot reads `0x0`, confirmed live). The Treasury/Collector is a **minimal-proxy clone** (it answers `masterCopy()` `0xa619486e`, not the canonical `implementation()` `0x5c60da1b` and not the EIP-1967 slot).

EIP-1967 implementation slot: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`. Admin slot: `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. `Upgraded(address)` topic0 = `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`.

### 8.1 Live implementations (EIP-1967 slot read 2026-06-08)

| Chain | Proxy | Live impl (from slot) | Matches registry? |
|---|---|---|---|
| Ethereum | Pool `0x3BC3…B4c0` | `0xFF679e5B4178A2f74A56f0e2c0e1FA1C80579385` | ✅ |
| Ethereum | PoolConfigurator `0x09Ed…8B5f` | `0x9C6F1367256bE65eE744740c72aD80dA5bc96cA6` | ✅ |
| Ethereum | Incentives `0x5be8…73a2` | `0x854138f891FE0A86270f6F153A06fBfabF69E0Ad` | ✅ |
| Ethereum | zToken (any reserve) | `0xb7ed499e7570ee7691eef4df9d708d258de2b512` | ✅ |
| Ethereum | variableDebtToken (any reserve) | `0x5d50be703836c330fc2d147a631cdd7bb8d7171c` | ✅ |
| Base | Pool `0x766f…c671` | `0x80102a3cbAcADa39560555340e1bC567B83C3A80` | ✅ |
| Base | PoolConfigurator `0xB40e…e6E3` | `0x749dF84Fd6DE7c0A67db3827e5118259ed3aBBa5` | ✅ |
| Base | Incentives `0x73a7…2CAE` | `0xaa999eA356F925BF1e856038c5D182Ae5E8A4973` | ✅ |
| Base | zToken (any reserve) | `0xe230cf9cee7b299f69778ef950a61de0de520ba7` | ✅ |

Admin slot on the Pool proxy reads `0x0` (immutable admin baked into bytecode, Aave pattern). **Read the live EIP-1967 slot — never hard-code an impl.** No `Upgraded` events fired in sampled windows (impls stable since deploy).

### 8.2 The `liquidationCall` dispatcher gotcha (verified, same as Aave/Spark)

On both live Pool impls (ETH `0xFF67…9385`, 21,754 bytes; Base `0x8010…3A80`, 21,811 bytes), selector `0x00a718a9` (`liquidationCall`) is **absent from the bytecode** (raw + `63`-prefixed PUSH4 scan = 0), while `supply`/`borrow`/`withdraw`/`repay`/`flashLoan`/`flashLoanSimple` **are** present. Yet `LiquidationCall` events fire (16 in a 50k-block window on the ETH Pool, 1 on Base) and liquidations execute — liquidation logic is reached through a delegatecalled logic library / fallback extension that keeps the Pool under the EIP-170 limit. **Detect liquidations by `LiquidationCall` topic0 `0xe413a321…`, never by selector** — and most liquidations arrive via third-party bots, so `tx.to` ≠ Pool.

---

## 9. Detection invariants & gotchas

1. **ZeroLend One lending lives on Ethereum (Pool `0x3BC3…B4c0`, "LRT ZeroLend Market") and Base (`0x766f…c671`, "Base ZeroLend Market") only** among the seven target chains. BNB/Avalanche/Arbitrum/Optimism/Polygon have **no** ZeroLend contracts (§6). The protocol's primary markets are on Linea/zkSync/Manta/Blast/X Layer (§11).
2. **It's an Aave V3.1/V3.2 fork** — `Supply`/`Borrow`/`Repay`/`Withdraw`/`LiquidationCall`/`FlashLoan` topics and selectors are identical to [aave/v3.md](../aave/v3.md). Reuse that detection set.
3. **No v3.3/v3.4 features.** Don't scan for `DeficitCreated`/`DeficitCovered`, `multicall`, `getReserveAToken`, `getReserveDeficit`, Position Managers — all absent (§2.6). The `ReserveData` struct is the **legacy layout** (id at struct word 7; aToken/stable/variable/strategy at words 8/9/10/11) — adjust any struct decoder accordingly.
4. **Detect liquidations by the `LiquidationCall` event, not the selector** (§8.2) — selector absent from impl; bots route liquidations so `tx.to` ≠ Pool.
5. **zTokens rebase every block.** Store `scaledBalanceOf` + reconstruct with the reserve `liquidityIndex` (ray). Same for debt with `variableBorrowIndex`. `Mint`/`Burn` topic0 is **shared between zToken and debt token** — disambiguate by emitting address.
6. **`onBehalfOf` ≠ `tx.from`.** Attribute positions to `onBehalfOf`/`user` from the event, not the sender (WrappedTokenGateway, credit delegation, relayers).
7. **The Ethereum market is restaking-centric.** Its 12 reserves are mostly LRT/LST tokens (weETH, ezETH, rsETH, pufETH, swETH, pzETH) plus two Pendle **PT tokens** (fixed-maturity, can expire) and DAI/USDC/USDT. Watch the PT maturities — a matured PT can de-peg.
8. **Stable rate exists in code but is disabled.** `SwapBorrowRateMode`/`RebalanceStableBorrowRate` topics are dead; `interestRateMode = 1` reverts. Reserves still carry stableDebtToken contracts (~0 supply).
9. **Cross-chain address collisions in different roles.** `0x1cc993f2…3385` = ETH AaveOracle = Base ACLManager; `0x749dF84F…BBa5` = ETH ACLManager = Base PoolConfigurator impl; `0x0A1198DD…100b` = two different UI readers. **Always key on `(chainId, address)`.**
10. **Treasury/Collector is a minimal-proxy clone** (answers `masterCopy()` `0xa619486e`, not the canonical `implementation()` `0x5c60da1b` and not EIP-1967). Flash-loan premium + reserve factor accrue to it via `mintToTreasury` (`MintedToTreasury`), not a direct transfer.
11. **MarketId distinguishes the two markets** — `PoolAddressesProvider.getMarketId()` = "LRT ZeroLend Market" (ETH) vs "Base ZeroLend Market" (Base) when crawling the registry.
12. **ZERO is a LayerZero OFT.** The native token is on **Linea** (`0x7835…c7a7`); on Ethereum the OFT mirror is `0x11dC…429e` (`symbol`="ZERO", `name`="ZeroLend"). There is **no ZERO OFT on Base** (`eth_getCode` = `0x` at the ETH OFT literal). Cross-chain ZERO movement = LayerZero `OFTSent`/`OFTReceived`, not Pool events.

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
-- zToken / debt token
TOPIC_TOKEN_MINT             = '\x458f5fa412d0f69b08dd84872b0215675cc67bc1d5b6fd93300a1c3878b86196'  -- zToken+vDebt
TOPIC_TOKEN_BURN             = '\x4cf25bc1d991c17529c25213d3cc0cda295eeaad5f13f361969b12ea48015f90'  -- zToken+vDebt
TOPIC_BALANCE_TRANSFER       = '\x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666'
TOPIC_BORROW_ALLOW_DELEGATED = '\xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1'
TOPIC_ERC20_TRANSFER         = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- PoolConfigurator (risk admin)
TOPIC_RESERVE_INITIALIZED    = '\x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f'
TOPIC_COLLAT_CONFIG_CHANGED  = '\x637febbda9275aea2e85c0ff690444c8d87eb2e8339bbede9715abcc89cb0995'
TOPIC_RESERVE_FROZEN         = '\x0c4443d258a350d27dc50c378b2ebf165e6469725f786d21b30cab16823f5587'
TOPIC_RESERVE_PAUSED         = '\xe188d542a5f11925d3a3af33703cdd30a43cb3e8066a3cf68b1b57f61a5a94b5'
TOPIC_SUPPLY_CAP_CHANGED     = '\x0263602682188540a2d633561c0b4453b7d8566285e99f9f6018b8ef2facef49'
TOPIC_BORROW_CAP_CHANGED     = '\xc51aca575985d521c5072ad11549bad77013bb786d57f30f94b40ed8f8dc9bc4'
-- AaveOracle
TOPIC_ASSET_SOURCE_UPDATED   = '\x22c5b7b2d8561d39f7f210b6b326a1aa69f15311163082308ac4877db6339dc1'
-- proxy / rewards
TOPIC_UPGRADED               = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_REWARDS_CLAIMED        = '\xc052130bc4ef84580db505783484b067ea8b71b3bca78a7e12db7aea8658f004'
-- NOTE: Aave v3.3 DeficitCreated/Covered and v3.4 events do NOT exist on ZeroLend.

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
SEL_RESCUE_TOKENS            = '\xcea9d26f'
SEL_GET_USER_ACCOUNT_DATA    = '\xbf92857c'
SEL_GET_RESERVE_DATA         = '\x35ea6a75'
SEL_GET_RESERVES_LIST        = '\xd1946dbc'
SEL_SCALED_BALANCE_OF        = '\x1da24f3e'
SEL_GET_ASSET_PRICE          = '\xb3596f07'
SEL_GET_MARKET_ID            = '\x568ef470'
-- absent on ZeroLend (do NOT scan): multicall \xac9650d8, getReserveAToken \xcff027d9,
--   getReserveDeficit \xc952485d, approvePositionManager \xb8caa7c5

-- ===== Ethereum ZeroLend "LRT ZeroLend Market" (chain ID 1) =====
ZL_ETH_POOL                  = '\x3bc3d34c32cc98bf098d832364df8a222bbab4c0'
ZL_ETH_ADDRESSES_PROVIDER    = '\xfd856e1a33225b86f70d686f9280435e3ff75fcf'
ZL_ETH_ADDR_PROV_REGISTRY    = '\x7503a8823b523629e28587317901ba4c055791eb'
ZL_ETH_POOL_CONFIGURATOR     = '\x09edc8f101897aa693932c1966725e05d6d68b5f'
ZL_ETH_ORACLE                = '\x1cc993f2c8b6fbc43a9bafd2a44398e739733385'
ZL_ETH_ACL_MANAGER           = '\x749df84fd6de7c0a67db3827e5118259ed3abba5'
ZL_ETH_DATA_PROVIDER         = '\x47223d4ea966a93b2cc96ffb4d42c22651fadfcf'
ZL_ETH_INCENTIVES            = '\x5be89bb10e2234204a2607765714916ed95a73a2'
ZL_ETH_EMISSION_MANAGER      = '\x859c2ca97ead2742a0758bc9dd889e9d0e7e84e8'
ZL_ETH_TREASURY              = '\x464c71f6c2f760dda6093dcb91c24c39e5d6e18c'
ZL_ETH_WETH_GATEWAY          = '\x6ea9d99c6653df987bdea11ffcd56dfb4b5d38b4'
ZL_ETH_POOL_IMPL             = '\xff679e5b4178a2f74a56f0e2c0e1fa1c80579385'
ZL_ETH_ZTOKEN_IMPL           = '\xb7ed499e7570ee7691eef4df9d708d258de2b512'
ZL_ETH_VDEBT_IMPL            = '\x5d50be703836c330fc2d147a631cdd7bb8d7171c'
ZL_ETH_ZERO_OFT              = '\x11dcc26d4bdac03ffa8841f69313c38240fc429e'

-- ===== Base ZeroLend "Base ZeroLend Market" (chain ID 8453) =====
ZL_BASE_POOL                 = '\x766f21277087e18967c1b10bf602d8fe56d0c671'
ZL_BASE_ADDRESSES_PROVIDER   = '\x5213ab3997a596c75ac6ebf81f8aeb9cf9a31007'
ZL_BASE_POOL_CONFIGURATOR    = '\xb40e21d5cd8e9e192b0da3107883f8b0f4e4e6e3'
ZL_BASE_ORACLE               = '\xf49ee3ea9c56d90627881d88004aabdfc44fd82c'
ZL_BASE_ACL_MANAGER          = '\x1cc993f2c8b6fbc43a9bafd2a44398e739733385'  -- == ETH ORACLE literal
ZL_BASE_DATA_PROVIDER        = '\xa754b2f1535287957933db6e2aee2b2fe6f38588'
ZL_BASE_INCENTIVES           = '\x73a7a4b40f3fe11e0bcab5538c75d3b984082cae'
ZL_BASE_EMISSION_MANAGER     = '\x0f9bfa294be6e3ca8c39221bb5dfb88032c8936e'
ZL_BASE_TREASURY             = '\x6f5ae60d89dbbc4eed4b08d08a68dd5679ac61b4'
ZL_BASE_WETH_GATEWAY         = '\x11ccdcfb19151feb086ee6f1f62bfa0940c85612'
ZL_BASE_POOL_IMPL            = '\x80102a3cbacada39560555340e1bc567b83c3a80'
ZL_BASE_ZTOKEN_IMPL          = '\xe230cf9cee7b299f69778ef950a61de0de520ba7'

-- ===== ZERO token (LayerZero OFT family) =====
ZERO_LINEA_NATIVE            = '\x78354f8dccb269a615a7e0a24f9b0718fdc3c7a7'  -- canonical/native (Linea, non-target)

-- Universal
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT           = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
```

---

## 11. Other chains (for completeness — ZeroLend's primary markets, NOT verified here)

ZeroLend's largest markets are on **non-target** chains. Addresses below are quoted from the official registry (`docs.zerolend.xyz/security/deployed-addresses`) and were **not** existence-checked in this pass — treat as informational. Several CREATE2-redeploy the **same impl bytecode** as the target chains, so impl literals recur (a deployer-reuse tell, not a shared contract).

| Chain | PoolAddressesProvider | Pool Proxy | PoolConfigurator Proxy | ACLManager | AaveOracle | PoolDataProvider |
|---|---|---|---|---|---|---|
| **Linea** (ZERO home) | `0xC44827C51d00381ed4C52646aeAB45b455d200eB` | `0x2f9bB73a8e98793e26Cb2F6C4ad037BDf1C6B269` | `0xf17218B09699d0F7145e40E771e72130FF616498` | `0xb2178109A414C3a869E5104283Fcf1a18923D0B8` | `0xFF679e5B4178A2f74A56f0e2c0e1FA1C80579385` | `0x67f93d36792c49a4493652B91ad4bD59f428AD15` |
| **zkSync Era** | `0x4f285Ea117eF0067B59853D6d16a5dE8088bA259` | `0x4d9429246EA989C9CeE203B43F6d1C7D83e3B8F8` | `0x9C3058F7bfCA6139ac3013999F57D7aa6a3AB1Ed` | `0x9A60cce3da06d246b492931d2943A8F574e67389` | `0x785765De3E9ac3D8eEb42B4724A7FEA8990142B8` | `0xB73550bC1393207960A385fC8b34790e5133175E` |
| **Manta** | `0xC44827C51d00381ed4C52646aeAB45b455d200eB` | `0x2f9bB73a8e98793e26Cb2F6C4ad037BDf1C6B269` | `0xf17218B09699d0F7145e40E771e72130FF616498` | `0xb2178109A414C3a869E5104283Fcf1a18923D0B8` | `0xFF679e5B4178A2f74A56f0e2c0e1FA1C80579385` | `0x67f93d36792c49a4493652B91ad4bD59f428AD15` |
| **Blast** | `0xb0811a1FC9Fb9972ee683Ba04c32Cb828Bcf587B` | `0xa70B0F3C2470AbBE104BdB3F3aaa9C7C54BEA7A8` | `0x22d3cDb2fbD1528a0eBb047EC4DE369098EFcda1` | `0x7503A8823B523629E28587317901BA4C055791eb` | `0xBE0ab675a478A759ECA580f0D6c9d399085547D8` | `0xc6DF4ddDBFaCb866e78Dcc01b813A41C15A08C10` |
| **X Layer** | `0x2f7e54ff5d45f77bFfa11f2aee67bD7621Eb8a93` | `0xfFd79D05D5dc37E221ed7d3971E75ed5930c6580` | `0x92eb7A4000Bd4A9045aa8a9d633718f8058FC2a7` | `0x67f93d36792c49a4493652B91ad4bD59f428AD15` | `0x78Ad3d53045b6582841e2a1a688C52Be2CA2A7a7` | `0x97e59722318F1324008484ACA9C343863792cBf6` |

**ZERO token / OFT (LayerZero):** native `0x78354f8dccb269a615a7e0a24f9b0718fdc3c7a7` (Linea); OFT adapter on Linea `0x1dad693787c5817ef3102f513025fa6a66039e8e`; OFT mirrors on **Ethereum** `0x11dCc26d4bDAc03FFa8841f69313C38240FC429e` (verified, §3.4), Blast `0x357f93E17FdabEcd3fEFc488a2d27dff8065d00f`, Manta `0x35a57eFB9b4ae833e9A200bb191ff69420caFa1D`, zkSync `0x27d0A2b5316b98088294378692F4EAbfB3222e36`, X Layer `0x843D794eD4335b27d02184ca86787C14e6247074`. **No ZERO OFT on Base** (verified `eth_getCode` = `0x`).

---

## 12. Verification & sources

How constants in this doc were verified (2026-06-08):

- **Event topic0 / selectors:** all recomputed locally as `keccak256(signature)`. On the ETH Pool `0x3BC3…B4c0`: `ReserveDataUpdated` (36 logs / 50k blocks), `Withdraw` (several windows), `LiquidationCall` (16 logs / 50k blocks). On the Base Pool `0x766f…c671`: `Withdraw` (10 logs / 50k), `LiquidationCall` (1 log / 50k). `Supply`/`Borrow` are low-frequency (restaking market) but their topics match Aave V3 and the selectors are present in the Pool impls.
- **Selector presence:** raw + PUSH4 byte-scan of the live Pool impls (ETH `0xFF67…9385`, 21,754 bytes; Base `0x8010…3A80`, 21,811 bytes). Present: supply/borrow/withdraw/repay/repayWithATokens/flashLoan/flashLoanSimple/mintUnbacked/mintToTreasury/rescueTokens. **Absent:** `liquidationCall` (§8.2), `multicall`, `getReserveAToken` (v3.4), `getReserveDeficit` (v3.3) — confirming a pre-v3.3 fork.
- **Addresses:** taken from the official ZeroLend deployed-addresses registry and existence-checked via `eth_getCode` (all ETH + Base core contracts non-empty; the five other target chains all `0x`). Pool wiring (`ADDRESSES_PROVIDER`/`getPool`/`getMarketId`/`getPriceOracle`/`getACLManager`/`getPoolConfigurator`/`getPoolDataProvider`) read live and round-trips cleanly. Reserve token addresses pulled from `getReservesList()` + `getReserveData(asset)` per reserve (12 ETH, 18 Base); zToken/debt impls read via the EIP-1967 slot. Oracle `BASE_CURRENCY_UNIT` = `1e8` and `getAssetPrice(WETH)` read live.
- **Proxy classification:** EIP-1967 impl + admin slots read live (`eth_getStorageAt`). Pool/Configurator/Incentives/zTokens = proxies (impl slot non-zero, admin slot zero = immutable-admin Aave proxy); AddressesProvider/Oracle/ACLManager/DataProvider/EmissionManager = non-proxy (impl slot `0x0`); Treasury = minimal-proxy clone (answers `masterCopy()` `0xa619486e` → `0xfb1b…91ea` on Base; the canonical `implementation()` `0x5c60da1b` reverts).
- **ZERO token:** ETH OFT `0x11dC…429e` confirmed via `symbol()`="ZERO" / `name()`="ZeroLend"; no ZERO OFT on Base.

Authoritative sources:

- [ZeroLend docs — Deployed Addresses](https://docs.zerolend.xyz/security/deployed-addresses) (source of truth) · mirror [`zerolend/docs.zerolend.xyz`](https://github.com/zerolend/docs.zerolend.xyz).
- [`zerolend` GitHub org](https://github.com/zerolend) — fork source.
- [`aave-dao/aave-v3-origin`](https://github.com/aave-dao/aave-v3-origin) — upstream V3 contracts (Pool/Configurator/aToken/debt token ABIs & selectors). See [aave/v3.md](../aave/v3.md).
- Explorers: [Etherscan Pool (mainnet-lrt)](https://etherscan.io/address/0x3BC3D34C32cc98bf098D832364Df8A222bBaB4c0) · [Etherscan PoolAddressesProvider](https://etherscan.io/address/0xFD856E1a33225B86f70D686f9280435E3fF75FCF) · [BaseScan Pool](https://basescan.org/address/0x766f21277087E18967c1b10bF602d8Fe56d0c671).
