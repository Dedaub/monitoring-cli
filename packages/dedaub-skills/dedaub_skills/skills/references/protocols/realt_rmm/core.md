# RealT RMM (RealToken Money Market) — Topics, Selectors, Addresses (Gnosis Chain only)

**Status:** verified against Gnosis Chain mainnet RPC (`https://gnosis-rpc.publicnode.com`), the live RMM contracts (recomputed keccak + live `eth_getLogs` + `eth_getCode` + EIP-1967 slot reads), and cross-checked against RealT docs / Aave governance / GnosisScan, on 2026-06-08. **RMM exists on Gnosis Chain (chain ID 100) ONLY. It is NOT deployed on any of the seven monitored chains — Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137) — every RMM address returns `0x` (empty bytecode) on all seven (swept and confirmed).**
**Scope:** the RMM money market — RealT's Aave fork for tokenized-real-estate collateral. Two coexisting generations live on Gnosis: **RMM v2** (an Aave **V2** fork, marketId `"RealToken Money Market"`, now largely dormant) and **RMM v3** (an Aave **V3** fork, marketId `"RMM V3"`, the active deployment). Topics/selectors are chain-agnostic and inherited from Aave V2 / V3 respectively; addresses are Gnosis-network-specific. RealT also runs a peer-to-peer marketplace (**YAM**) and RealToken (RWA) ERC-20s — those are out of scope here and mentioned only as context.

RMM lets RealToken holders (and stablecoin lenders) collateralize tokenized US-real-estate ERC-20s to borrow WXDAI / USDC / USDT. Both generations are **fully proxied, upgradeable** Aave forks. Each contract sits behind an Aave proxy controlled by the addresses-provider / ACL governance stack, and the **owner / pool-admin / ACL-admin on both generations is the same governance key `0x5fc96c182bb7e0413c08e8e03e9d7efc6cf0b099`** (an EOA-controlled multisig — empty code).

> **Two generations, one chain — the non-obvious fact.** RealT first shipped RMM on **Aave V2** (`LendingPool`, `Deposit` event, ETH-style account math) where **each RealToken is its own reserve** (58 reserves total). To get past Aave V3's 128-market health-factor gas ceiling for hundreds of properties, RealT then shipped **RMM v3** on **Aave V3** with a **wrapper token** (`RTWxusd` / "RealToken Wrapped USD" — `RTW-USD-01`, `REUSD`) that pools many RealTokens into a **single** reserve. So RMM v3 has only **4 reserves** (WXDAI, USDC, RTW-USD-01, REUSD), and the per-property risk lives *inside* the wrapper, not in the Pool. A monitoring engineer must treat these as **two separate Aave deployments** (different Pool/Provider/aToken sets, different event ABIs) that happen to share governance.

> **Lineage determined on-chain (not from docs).** The RealT governance forum discusses "deploying RMM with the V3 version," but the live contracts are unambiguous from bytecode: the **RMM v2 Pool** (`0x5b8d…cb2a`) impl exposes `deposit` (`0xe8eda9df`), `getAddressesProvider` (`0xfe65acfe`), `paused`, `swapBorrowRateMode` and emits the V2 `Deposit`/`Borrow`/aToken-`Mint` topics → **Aave V2**. The **RMM v3 Pool** (`0xFb9b…fdb3`) impl exposes `supply` (`0x617ba037`), `flashLoanSimple`, `setUserEMode`, `mintToTreasury`, `repayWithATokens`, `ADDRESSES_PROVIDER` (`0x0542975c`) and emits the V3 `Supply`/`Borrow`/aToken-`Mint` topics → **Aave V3** (a V3.0/V3.1-era fork that still carries `stableDebtToken`s, like SparkLend; pre-v3.2). Both verified by live `eth_getLogs`.

> **`liquidationCall` dispatcher note (both generations).** On both the RMM v2 and RMM v3 Pool impls, the `liquidationCall` selector `0x00a718a9` is **not present in the Pool implementation dispatcher** (RMM v2 routes liquidations through the `LendingPoolCollateralManager` delegatecall target; RMM v3 reaches liquidation logic via the same V3 split-impl pattern as Aave/SparkLend). The `LiquidationCall` event topic0 `0xe413a321…` is the canonical detector for both. **Detect liquidations by event, never by selector.**

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-08. The "verified live" counts are from `eth_getLogs` on the RMM Gnosis Pools/tokens (windows noted in §10).

### 1.1 RMM **v2** — `LendingPool` (Aave V2) — emitter = `0x5b8d36de471880ee21936f328aab2383a280cb2a`

| topic0 | Event |
|--------|-------|
| `0xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951` | `Deposit(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint16 indexed referral)` |
| `0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7` | `Withdraw(address indexed reserve, address indexed user, address indexed to, uint256 amount)` |
| `0xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b` | `Borrow(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint256 borrowRateMode, uint256 borrowRate, uint16 indexed referral)` |
| `0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa` | `Repay(address indexed reserve, address indexed user, address indexed repayer, uint256 amount)` |
| `0xea368a40e9570069bb8e6511d668293ad2e1f03b0d982431fd223de9f3b70ca6` | `Swap(address indexed reserve, address indexed user, uint256 rateMode)` (stable↔variable) |
| `0x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300` | `RebalanceStableBorrowRate(address indexed reserve, address indexed user)` |
| `0x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac` | `FlashLoan(address indexed target, address indexed initiator, address indexed asset, uint256 amount, uint256 premium, uint16 referralCode)` |
| `0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286` | `LiquidationCall(address indexed collateralAsset, address indexed debtAsset, address indexed user, uint256 debtToCover, uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)` |
| `0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a` | `ReserveDataUpdated(address indexed reserve, uint256 liquidityRate, uint256 stableBorrowRate, uint256 variableBorrowRate, uint256 liquidityIndex, uint256 variableBorrowIndex)` |
| `0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2` | `ReserveUsedAsCollateralEnabled(address indexed reserve, address indexed user)` |
| `0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd` | `ReserveUsedAsCollateralDisabled(address indexed reserve, address indexed user)` |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` |

`Deposit` is the **V2** supply event (NOT V3 `Supply` — different topic0). Verified live (block window 24.96M–25.008M): `Deposit` 247, `Borrow` 63, `Repay` 252, `Withdraw` 92, `ReserveDataUpdated` 654; V3 `Supply` (`0x2b627736…`) = 0 logs on this Pool (confirms V2 lineage). `borrowRateMode` = 1 (stable) / 2 (variable); stable rate is a live V2 feature here.

### 1.2 RMM **v3** — `Pool` (Aave V3) — emitter = `0xFb9b496519fCa8473fba1af0850B6B8F476BFdB3`

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
| `0x7962b394d85a534033ba2efcf43cd36de57b7ebeb3de0ca4428965d9b3ddc481` | `SwapBorrowRateMode(address indexed reserve, address indexed user, uint8 interestRateMode)` (stable carried but disabled in practice) |
| `0x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300` | `RebalanceStableBorrowRate(address indexed reserve, address indexed user)` |
| `0xbfa21aa5d5f9a1f0120a95e7c0749f389863cbdbfff531aa7339077a5bc919de` | `MintedToTreasury(address indexed reserve, uint256 amountMinted)` |
| `0xaef84d3b40895fd58c561f3998000f0583abb992a52fbdc99ace8e8de4d676a5` | `IsolationModeTotalDebtUpdated(address indexed asset, uint256 totalDebt)` |
| `0xd728da875fc88944cbf17638bcbe4af0eedaef63becd1d1c57cc097eb4608d84` | `UserEModeSet(address indexed user, uint8 categoryId)` |

`Supply` is the **V3** supply event. Verified live (RMM v3 is the active market — block window ~39.95M–40.0M): `Supply` 642, `Borrow` 399, `ReserveDataUpdated` 1678; in the most recent ~48k-block window `Supply` = 9, `Borrow` = 0. **RMM v3 is an early V3 fork: V3.3 `DeficitCreated`/`DeficitCovered` and V3.4 features (`multicall`, Position Managers) are NOT present** (selector scan confirms `multicall`/`getReserveDeficit` absent on the v3 impl).

### 1.3 aToken & debt tokens (per-reserve, scaled rebasing)

**RMM v2** (Aave V2 token events — aToken and varDebt have *different* topic0s; disambiguate by `(topic0, emitter)`):

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address indexed from, uint256 value, uint256 index)` | **v2 aToken** |
| `0x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2` | `Burn(address indexed from, address indexed target, uint256 value, uint256 index)` | **v2 aToken** |
| `0x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee` | `Mint(address indexed from, address indexed onBehalfOf, uint256 value, uint256 index)` | **v2 variableDebtToken** |
| `0x49995e5dd6158cf69ad3e9777c46755a1a826a446c6416992167462dad033b2a` | `Burn(address indexed user, uint256 amount, uint256 index)` | **v2 variableDebtToken** |

**RMM v3** (Aave V3 token events — aToken and varDebt **share** these topic0s; disambiguate by emitter only):

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x458f5fa412d0f69b08dd84872b0215675cc67bc1d5b6fd93300a1c3878b86196` | `Mint(address indexed caller, address indexed onBehalfOf, uint256 value, uint256 balanceIncrease, uint256 index)` | v3 aToken **and** variableDebtToken |
| `0x4cf25bc1d991c17529c25213d3cc0cda295eeaad5f13f361969b12ea48015f90` | `Burn(address indexed from, address indexed target, uint256 value, uint256 balanceIncrease, uint256 index)` | v3 aToken **and** variableDebtToken |

**Shared by both generations** (ERC-20 / aToken common events):

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666` | `BalanceTransfer(address indexed from, address indexed to, uint256 value, uint256 index)` | aToken |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 (a/debt tokens) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | aToken |
| `0xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1` | `BorrowAllowanceDelegated(address indexed fromUser, address indexed toUser, address indexed asset, uint256 amount)` | debt token |

Verified live on the v2 armmWXDAI aToken (`0x7349…f8a0`): V2 `Mint` 623, V2 `Burn` 49, V3 `Mint` (`0x458f5fa4…`) = 0. On the v3 armmv3WXDAI aToken (`0x0ca4…157b`): V3 `Mint` 422, V3 `Burn` 115 (window ~39.95M–40.0M).

### 1.4 Configurator & Oracle (both generations, standard Aave topics)

| topic0 | Event | Contract |
|--------|-------|----------|
| `0x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f` | `ReserveInitialized(address indexed asset, address indexed aToken, address stableDebtToken, address variableDebtToken, address interestRateStrategyAddress)` | Configurator |
| `0x637febbda9275aea2e85c0ff690444c8d87eb2e8339bbede9715abcc89cb0995` | `CollateralConfigurationChanged(address indexed asset, uint256 ltv, uint256 liquidationThreshold, uint256 liquidationBonus)` | Configurator |
| `0x0c4443d258a350d27dc50c378b2ebf165e6469725f786d21b30cab16823f5587` | `ReserveFrozen(address indexed asset, bool frozen)` (v3 form) | v3 Configurator |
| `0xe188d542a5f11925d3a3af33703cdd30a43cb3e8066a3cf68b1b57f61a5a94b5` | `ReservePaused(address indexed asset, bool paused)` | v3 Configurator |
| `0xb46e2b82b0c2cf3d7d9dece53635e165c53e0eaa7a44f904d61a2b7174826aef` | `ReserveFactorChanged(address indexed asset, uint256 oldReserveFactor, uint256 newReserveFactor)` (v3 2-arg form) | v3 Configurator |
| `0x0263602682188540a2d633561c0b4453b7d8566285e99f9f6018b8ef2facef49` | `SupplyCapChanged(address indexed asset, uint256 oldSupplyCap, uint256 newSupplyCap)` | v3 Configurator |
| `0xc51aca575985d521c5072ad11549bad77013bb786d57f30f94b40ed8f8dc9bc4` | `BorrowCapChanged(address indexed asset, uint256 oldBorrowCap, uint256 newBorrowCap)` | v3 Configurator |
| `0x22c5b7b2d8561d39f7f210b6b326a1aa69f15311163082308ac4877db6339dc1` | `AssetSourceUpdated(address indexed asset, address indexed source)` | AaveOracle |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | every proxy — watch for impl changes |

> The RMM v2 `LendingPoolConfigurator` uses Aave-**V2** event signatures for frozen/active state (`ReserveFrozen(address)` / `ReserveUnfrozen(address)` / `ReserveActivated(address)` — no `bool` arg; different topic0s from the v3 forms above). These are rarely queried; compute the topic0 per exact V2 signature if needed.

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

All selectors recomputed locally 2026-06-08 and probed against the live impl dispatchers (RMM v2 impl `0xa7d3…f4af`, RMM v3 impl `0xd9cf…6833`). Presence/absence below reflects the actual bytecode.

### 2.1 RMM v2 `LendingPool` (Aave V2)

| Selector | Signature | In impl? | Notes |
|----------|-----------|----------|-------|
| `0xe8eda9df` | `deposit(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)` | yes | **V2 supply.** Emits `Deposit`. (V3 = `supply` `0x617ba037`, absent here.) |
| `0x69328dec` | `withdraw(address asset, uint256 amount, address to)` → `uint256` | yes | shared with V3. |
| `0xa415bcad` | `borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)` | yes | mode 1=stable, 2=variable. shared with V3. |
| `0x573ade81` | `repay(address asset, uint256 amount, uint256 rateMode, address onBehalfOf)` → `uint256` | yes | shared with V3. |
| `0x94ba89a2` | `swapBorrowRateMode(address asset, uint256 rateMode)` | yes | stable↔variable (functional in V2). |
| `0xcd112382` | `rebalanceStableBorrowRate(address asset, address user)` | (V2) | |
| `0x5a3b74b9` | `setUserUseReserveAsCollateral(address asset, bool useAsCollateral)` | yes | shared with V3. |
| `0x00a718a9` | `liquidationCall(address collateralAsset, address debtAsset, address user, uint256 debtToCover, bool receiveAToken)` | **NO** | Routed via `LendingPoolCollateralManager` delegatecall. **Detect via event.** |
| `0xab9c4b5d` | `flashLoan(address receiverAddress, address[] assets, uint256[] amounts, uint256[] modes, address onBehalfOf, bytes params, uint16 referralCode)` | yes | |
| `0xfe65acfe` | `getAddressesProvider()` → `address` | yes | **V2 getter** (V3 uses `ADDRESSES_PROVIDER` `0x0542975c`, absent here). |
| `0x5c975abb` | `paused()` → `bool` | yes | V2-only on the Pool. |
| `0xbf92857c` | `getUserAccountData(address user)` → `(totalCollateral, totalDebt, availableBorrows, liqThreshold, ltv, healthFactor)` | yes | **In RMM v2 the first five are in 8-dec USD** (RMM's oracle base is a synthetic USD unit, `1e8`) — NOT ETH/wei as in stock Aave V2. HF in `1e18`. |
| `0x35ea6a75` | `getReserveData(address asset)` → V2 `ReserveData` (…, aToken, stableDebt, variableDebt, strategy, id) | yes | |
| `0xd1946dbc` | `getReservesList()` → `address[]` | yes | 58 reserves. |
| `0xd15e0053` / `0x386497fd` | `getReserveNormalizedIncome` / `…VariableDebt(address)` → ray | yes | supply/borrow index. |

### 2.2 RMM v3 `Pool` (Aave V3)

| Selector | Signature | In impl? | Notes |
|----------|-----------|----------|-------|
| `0x617ba037` | `supply(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)` | yes | **V3 supply.** Emits `Supply`. |
| `0x02c205f0` | `supplyWithPermit(address,uint256,address,uint16,uint256,uint8,bytes32,bytes32)` | yes | EIP-2612 one-tx supply. |
| `0xe8eda9df` | `deposit(address,uint256,address,uint16)` | yes | back-compat alias to `supply` (still in this V3 impl). |
| `0x69328dec` | `withdraw(address asset, uint256 amount, address to)` → `uint256` | yes | |
| `0xa415bcad` | `borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)` | yes | mode 2=variable. |
| `0x573ade81` | `repay(address asset, uint256 amount, uint256 interestRateMode, address onBehalfOf)` → `uint256` | yes | |
| `0x2dad97d4` | `repayWithATokens(address asset, uint256 amount, uint256 interestRateMode)` → `uint256` | yes | `Repay.useATokens=true`. |
| `0x42b0b77c` | `flashLoanSimple(address receiverAddress, address asset, uint256 amount, bytes params, uint16 referralCode)` | yes | V3-only — single-asset. |
| `0xab9c4b5d` | `flashLoan(address,address[],uint256[],uint256[],address,bytes,uint16)` | yes | multi-asset. |
| `0x28530a47` | `setUserEMode(uint8 categoryId)` | yes | V3-only. Emits `UserEModeSet`. |
| `0x9cd19996` | `mintToTreasury(address[] assets)` | yes | V3-only. |
| `0x00a718a9` | `liquidationCall(address,address,address,uint256,bool)` | **NO** | Same split-impl pattern as Aave V3 / SparkLend. **Detect via event.** |
| `0x0542975c` | `ADDRESSES_PROVIDER()` → `address` | yes | **V3 getter.** |
| `0xbf92857c` | `getUserAccountData(address)` → (…, healthFactor) | yes | first five in 8-dec USD (oracle base = USD, `1e8`); HF `1e18`. |
| `0x35ea6a75` / `0xd1946dbc` | `getReserveData(address)` / `getReservesList()` | yes | 4 reserves. |
| `0xac9650d8` | `multicall(bytes[])` | **NO** | v3.4 — absent (early V3 fork). |
| `0xc952485d` | `getReserveDeficit(address)` | **NO** | v3.3 — absent. |

### 2.3 aToken / variableDebtToken (both generations)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1da24f3e` | `scaledBalanceOf(address user)` | **Use for accounting** — `balanceOf` rebases every block. |
| `0xb1bf962d` | `scaledTotalSupply()` → `uint256` | |
| `0xb16a19de` | `UNDERLYING_ASSET_ADDRESS()` → `address` | Underlying reserve token. |
| `0x7535d246` | `POOL()` → `address` | Owning Pool (v3 aToken). |
| `0xc04a8a10` | `approveDelegation(address delegatee, uint256 amount)` | debt token — credit delegation. |
| `0x70a08231` / `0x18160ddd` | `balanceOf` / `totalSupply` | **Rebasing** — changes every block. |

### 2.4 PoolAddressesProvider getters (differ by generation)

| Selector | Signature | Generation |
|----------|-----------|------------|
| `0x0261bf8b` | `getLendingPool()` → `address` | **v2 provider** |
| `0x85c858b1` | `getLendingPoolConfigurator()` → `address` | v2 provider |
| `0x712d9171` | `getLendingPoolCollateralManager()` → `address` | v2 provider |
| `0xaecda378` / `0xddcaa9ea` | `getPoolAdmin()` / `getEmergencyAdmin()` → `address` | v2 provider |
| `0xfca513a8` | `getPriceOracle()` → `address` | both |
| `0x568ef470` | `getMarketId()` → `string` | both (`"RealToken Money Market"` v2 / `"RMM V3"` v3) |
| `0x026b1d5f` | `getPool()` → `address` | **v3 provider** |
| `0x631adfca` / `0xfca513a8` | `getPoolConfigurator()` / `getPriceOracle()` | v3 provider |
| `0x707cd716` / `0x0e67178c` / `0xe860accb` | `getACLManager()` / `getACLAdmin()` / `getPoolDataProvider()` | v3 provider |

---

## 3. Addresses — RMM v2 (Aave V2) — Gnosis Chain (chain ID 100)

Source: live on-chain resolution via `LendingPoolAddressesProvider.getMarketId()` = `"RealToken Money Market"` and its getters; GnosisScan. All verified via `eth_getCode` / `eth_call` on `https://gnosis-rpc.publicnode.com` on 2026-06-08. Wiring confirmed: `armmWXDAI.POOL()` → Pool; `Pool.getAddressesProvider()` → Provider; `Provider.getLendingPool()` → Pool.

### 3.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| **LendingPool** (proxy) | `0x5b8d36de471880ee21936f328aab2383a280cb2a` | Main entrypoint; emits all §1.1 events. impl `0xa7d3066bb8347de86fb14117950a40769af8f4af`. |
| **LendingPoolAddressesProvider** | `0x0ade75f269a054673883319baa50e5e0360a775f` | Registry / source-of-truth (not a proxy). `getMarketId()` = "RealToken Money Market". |
| **LendingPoolConfigurator** (proxy) | `0xcc71725de4744da245c91cfb26457438c558f98b` | Risk-admin. impl `0x879a58a3be3fe83e37d71a6c25fd2432963fe61e`. |
| **LendingPoolCollateralManager** | `0x1c327865d4dd2348170153d5b6ed6fd48cf3389d` | Delegatecall target for `liquidationCall` (logic runs in Pool context; event emitted by Pool). |
| **AaveOracle (PriceOracle)** | `0x1a88d967936a73326562d2310062ece226ed6664` | Price oracle. `BASE_CURRENCY_UNIT = 1e8`; base = a synthetic USD unit `0x678df3415fc31947da4324ec63212874be5a82f8` (8-dec, no symbol) → **prices are USD, not ETH**. |
| LendingRateOracle | `0xa27b10cb7ab050b5574a1dcf6b6da816459c3db1` | Stable-rate reference oracle. |
| **AaveProtocolDataProvider** | `0x8956488dc17cea7cbec19388aebdb37273f523be` | Read helper (`getReserveTokensAddresses`, etc.). |
| **PoolAdmin / owner** | `0x5fc96c182bb7e0413c08e8e03e9d7efc6cf0b099` | Governance key (empty code = EOA/multisig signer). Also the v3 ACL_ADMIN. |
| EmergencyAdmin (guardian) | `0xa26851621ae64c66d09742c43591ad620a5b8256` | Pause authority (has code — small contract/Safe). |
| WETHGateway V1 | `0x80Dc050A8C923C0051D438026f1192d53033728c` | xDAI↔WXDAI supply/repay helper. |

### 3.2 RMM v2 reserves — key fungible markets (underlying → aToken / variableDebtToken / stableDebtToken)

The v2 Pool has **58 reserves**: the borrowable stablecoins/majors below plus dozens of individual **RealToken** RWA ERC-20s (e.g. `armmREALTOKEN-S-1521-1523-S.DRAKE-AVE-CHICAGO-IL` at aToken `0x5c1b324eb3d14a73ee6e16023941b991e311c2e1`). RealToken reserves are typically collateral-only. aTokens are branded **armm…** (`Mint`/`Burn` per §1.3 v2). v2 aToken impl `0x6740ac1a7901b041e432f65bae8bbc39ddca6105`, varDebt impl `0x10ec8f37b755d8f3a9890a66d5b8d19beb3a7087`, stableDebt impl `0x24e71929b3eff7d14a2791df608101df1323fcef`.

| Symbol | Underlying | aToken (armm) | variableDebtToken | stableDebtToken |
|--------|-----------|---------------|-------------------|-----------------|
| WXDAI | `0xe91d153e0b41518a2ce8dd3d7944fa863463a97d` | `0x7349c9eaa538e118725a6130e0f8341509b9f8a0` | `0x6a7ced66902d07066ad08c81179d17d0fbe36829` | `0x7d0b84f344cea96003076847a6da52d94c4ac1cc` |
| USDC | `0xddafbb505ad214d7b80b1f830fccc89b60fb7a83` (6-dec) | `0x05d909006cd38ba9e73db72c083081726b67971d` | `0xefea0b5a48f1b936759a3279dcc3ba252884c764` | `0x62ac77d67fbc79213094422479469b827534a0b5` |
| USDT | `0x4ecaba5870353805a9f068101a40e0f32ed605c6` | `0xa0c95bebe678eeed33a51dc24acf60fd1900552a` | `0x461dad55579a190688d9558fce9cf4d61d8e1c4f` | `0x202931452cb4cd3fe7e30c2e621c0d2b209e8403` |
| WETH | `0x6a023ccd1ff6f2045c3309768ead9e68f978f6e1` | `0x2cfab362fdb1e8c7d58659d0c6b04f575eaaba25` | `0x44b2bc30de2ca1128927202f8cf462aa7718a850` | `0x80baf7c730f8104d50e0feacc808f300ab8b1609` |
| WBTC | `0x8e5bbbb09ed1ebde8674cda39a0c169401db4252` | `0x890ab77c02c2e85e78c05bbb431b46bab0bee220` | `0x6272c98a897c3eb554bed948b8fb7bc6ac36cde2` | `0x1a938de87949e97a2c762519e147d39ed58defbf` |

---

## 4. Addresses — RMM v3 (Aave V3) — Gnosis Chain (chain ID 100) — the active market

Source: live resolution via `PoolAddressesProvider.getMarketId()` = `"RMM V3"`. All verified via `eth_getCode` / `eth_call` on Gnosis on 2026-06-08. Wiring confirmed: `Pool.ADDRESSES_PROVIDER()` → Provider; `Provider.getPool()` → Pool.

### 4.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| **Pool** (proxy) | `0xFb9b496519fCa8473fba1af0850B6B8F476BFdB3` | Main entrypoint; emits all §1.2 events. impl `0xd9cf63c4120dc195e2eb9b7133f31c80807d6833`. |
| **PoolAddressesProvider** | `0xdaa06cf7adceb69fcfde68d896818b9938984a70` | Registry. `getMarketId()` = "RMM V3". owner `0x5fc96c18…`. |
| **PoolConfigurator** (proxy) | `0xc2af0ffe79eb3e0110c108f7b2d849818c338e8d` | Risk-admin. impl `0x2c1134079676babe28f8239db4b88dcd8999dc92`. |
| **AaveOracle** | `0xb4ae809ad7ceb7e5b579dedd0de7c213ad5ab516` | Price oracle. `BASE_CURRENCY = 0x0` (USD), `BASE_CURRENCY_UNIT = 1e8`. |
| **ACLManager** | `0x6a1163daf9f5909990b547c15dbd672169464055` | Role registry. |
| ACL_ADMIN / PoolAdmin / owner | `0x5fc96c182bb7e0413c08e8e03e9d7efc6cf0b099` | Same governance key as RMM v2. |
| **AaveProtocolDataProvider** | `0x11b45acc19656c6c52f93d8034912083ac7dd756` | Read helper. |

### 4.2 RMM v3 reserves (all 4) — underlying → aToken / variableDebtToken / stableDebtToken

aTokens branded **armmv3…**. v3 aToken impl `0x565cff7a77ba690fc9d860530413761d77c2ddd3`, varDebt impl `0x0ac8b3f53e610ed89c56b21f835bb1332f405bfc`, stableDebt impl `0x671ab2985bc1dfcf9cafd37235fd41bf756ff2b3`.

| Symbol | Underlying | aToken (armmv3) | variableDebtToken | stableDebtToken |
|--------|-----------|-----------------|-------------------|-----------------|
| WXDAI | `0xe91d153e0b41518a2ce8dd3d7944fa863463a97d` | `0x0ca4f5554dd9da6217d62d8df2816c82bba4157b` | `0x9908801df7902675c3fedd6fea0294d18d5d5d34` | `0x8acd88d494cfa56f542234f8924f06024b5795b5` |
| USDC | `0xddafbb505ad214d7b80b1f830fccc89b60fb7a83` (6-dec) | `0xed56f76e9cbc6a64b821e9c016eafbd3db5436d1` | `0x69c731ae5f5356a779f44c355abb685d84e5e9e6` | `0x3d1dae285860153169e17a5365492c6bba16979e` |
| **RTW-USD-01** (RealToken Wrapped USD 01) | `0xd3dff217818b4f33eb38a243158fbed2bbb029d3` | `0xf3220cd8f66aeb86fc2a82502977eab4bfd2f647` | `0x9fc319476836e4b7d70d332aea3e33ec3f14ffde` | `0x2629eedfd294172b26972444e5985c362eb9604d` |
| **REUSD** (Realtoken Ecosystem USD) | `0x3390742ac0dce14ea6fcbd5ae02e2303c5d62ad9` | `0xd04c3b20f08b1d51f7429b2205491183a7b3583f` | `0x00eddae5c334bfe4e929c775aaa7aee1a116e077` | `0xf4c85940709af241316d806b7b07729e9de31071` |

> **`RTW-USD-01` / `REUSD` are wrapper reserves**, not single properties. They aggregate the value of many RealTokens into one ERC-20 so RMM v3 stays under Aave V3's 128-market limit. Per-property exposure lives inside the wrapper; the Pool sees only the four reserves above.

---

## 5. Cross-chain summary — presence matrix

Every RMM contract (v2 and v3, Pool / Provider / aTokens) was `eth_getCode`-checked on all seven monitored chains on 2026-06-08 → **`0x` (empty) on every one**. RMM lives only on Gnosis Chain (100).

| Chain | ID | RMM v2 Pool | RMM v3 Pool | Any RMM contract? |
|---|---|---|---|---|
| **Gnosis** | 100 | ✅ `0x5b8d…cb2a` (dormant) | ✅ `0xFb9b…fdb3` (active) | ✅ |
| Ethereum | 1 | ❌ `0x` | ❌ `0x` | ❌ none |
| Base | 8453 | ❌ `0x` | ❌ `0x` | ❌ none |
| BNB | 56 | ❌ `0x` | ❌ `0x` | ❌ none |
| Avalanche | 43114 | ❌ `0x` | ❌ `0x` | ❌ none |
| Arbitrum One | 42161 | ❌ `0x` | ❌ `0x` | ❌ none |
| Optimism | 10 | ❌ `0x` | ❌ `0x` | ❌ none |
| Polygon PoS | 137 | ❌ `0x` | ❌ `0x` | ❌ none |

**No vanity addresses** — RMM uses ordinary CREATE-derived addresses, no shared cross-chain salt (it is single-chain). RMM addresses do **not** collide with Aave/Spark's Gnosis deployments (different Pools, different marketIds).

---

## 6. Proxies

Every RMM core contract on both generations is an **upgradeable Aave proxy** (`InitializableImmutableAdminUpgradeabilityProxy`). Detection: read the EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` with `eth_getStorageAt`; a non-zero value = a proxy. **Note:** the EIP-1967 *admin* slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` reads `0x` on RMM proxies — Aave's `*ImmutableAdmin*` proxy bakes the admin into immutable bytecode rather than the standard admin slot, so an empty admin slot here does **not** mean "not a proxy" (check the impl slot instead). The `AaveOracle`/`LendingRateOracle`/`LendingPoolAddressesProvider`/`PoolAddressesProvider` are plain (non-proxy) contracts — replaced via provider setters, not upgraded.

| Contract | Pattern | Live impl (read 2026-06-08) | Upgrade auth |
|----------|---------|------------------------------|--------------|
| RMM v2 LendingPool | EIP-1967 proxy, immutable admin = Provider | `0xa7d3066bb8347de86fb14117950a40769af8f4af` | `Provider.setLendingPoolImpl()` (owner `0x5fc96c18…`) |
| RMM v2 LendingPoolConfigurator | EIP-1967 proxy | `0x879a58a3be3fe83e37d71a6c25fd2432963fe61e` | Provider |
| RMM v2 aToken (e.g. armmWXDAI) | EIP-1967 proxy, admin = Configurator | `0x6740ac1a7901b041e432f65bae8bbc39ddca6105` | `Configurator.updateAToken()` |
| RMM v2 variableDebtToken | EIP-1967 proxy | `0x10ec8f37b755d8f3a9890a66d5b8d19beb3a7087` | Configurator |
| RMM v2 stableDebtToken | EIP-1967 proxy | `0x24e71929b3eff7d14a2791df608101df1323fcef` | Configurator |
| RMM v3 Pool | EIP-1967 proxy | `0xd9cf63c4120dc195e2eb9b7133f31c80807d6833` | `Provider.setPoolImpl()` |
| RMM v3 PoolConfigurator | EIP-1967 proxy | `0x2c1134079676babe28f8239db4b88dcd8999dc92` | Provider |
| RMM v3 aToken (armmv3WXDAI) | EIP-1967 proxy | `0x565cff7a77ba690fc9d860530413761d77c2ddd3` | `Configurator.updateAToken()` |
| RMM v3 variableDebtToken | EIP-1967 proxy | `0x0ac8b3f53e610ed89c56b21f835bb1332f405bfc` | Configurator |
| RMM v3 stableDebtToken | EIP-1967 proxy | `0x671ab2985bc1dfcf9cafd37235fd41bf756ff2b3` | Configurator |
| LendingPoolAddressesProvider / PoolAddressesProvider | **non-proxy** registry | — (impl slot reads via direct storage; ownable) | `owner` |
| AaveOracle / LendingRateOracle | **non-proxy** | — | replaced via Provider setter |

**Upgraded(address) topic0 to watch on every proxy:** `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. Always read the live impl slot before relying on an impl address.

---

## 7. Detection invariants & gotchas

1. **RMM is Gnosis-only (chain 100).** Absent on all seven monitored chains (`eth_getCode` = `0x` everywhere — §5). Any "RMM on Ethereum/Base/L2" claim is wrong.
2. **Two coexisting generations — never conflate them.** RMM v2 = Aave **V2** fork (`LendingPool 0x5b8d…cb2a`, `Deposit` event, marketId "RealToken Money Market", 58 reserves, dormant). RMM v3 = Aave **V3** fork (`Pool 0xFb9b…fdb3`, `Supply` event, marketId "RMM V3", 4 reserves, **active**). Different Pool addresses, different event ABIs. Key all detection on `(generation, emitter address)`.
3. **`Deposit` vs `Supply`.** RMM v2 supply = `Deposit` topic `0xde685721…` (selector `deposit` `0xe8eda9df`). RMM v3 supply = `Supply` topic `0x2b627736…` (selector `supply` `0x617ba037`). Picking the wrong topic silently misses half the protocol.
4. **aToken `Mint`/`Burn` topics differ by generation.** RMM v2: aToken `Mint` `0x4c209b5f` ≠ varDebt `Mint` `0x2f00e3cd` (different topics per token type). RMM v3: aToken **and** varDebt share `Mint` `0x458f5fa4` — disambiguate by emitter. The two generations also use different aToken `Mint` topics from each other.
5. **Detect liquidations by the `LiquidationCall` event** `0xe413a321…`, never by the `liquidationCall` selector `0x00a718a9` — it is absent from both Pool impl dispatchers (v2 → CollateralManager delegatecall; v3 → split-impl). The event is emitted by the Pool address in both cases.
6. **Attribute to `onBehalfOf`/`user` from the event, not `tx.from`.** The WETHGateway, credit delegation, and the RTWxusd wrapper flows mean the sender is often not the position owner.
7. **RMM v2 account math is USD, not ETH.** Unlike stock Aave V2 (ETH/wei base), RMM v2's oracle base is a synthetic USD unit (`0x678df341…`, 8-dec) so `getUserAccountData` returns 8-dec **USD** for collateral/debt/borrows (HF in `1e18`). Same units as RMM v3. Don't apply the "V2 = ETH" rule here.
8. **RMM v3 is an early V3 fork (pre-v3.2).** It still carries `stableDebtToken`s, and it lacks V3.3 (`DeficitCreated`/`DeficitCovered`, `getReserveDeficit`) and V3.4 (`multicall`, Position Managers, `getReserveAToken`) — do not scan for those.
9. **The RTWxusd wrapper reserves (`RTW-USD-01`, `REUSD`) hide per-property risk.** RMM v3 health factors and liquidations are computed against the wrapper price, not individual RealTokens. To follow real-estate exposure you must look *inside* the wrapper contract, not just the four Pool reserves.
10. **aTokens rebase.** Store `scaledBalanceOf` and reconstruct with the reserve `liquidityIndex` (ray, 27-dec); same for debt with `variableBorrowIndex`.
11. **Both generations share the governance key `0x5fc96c18…`** (owner / PoolAdmin / ACL_ADMIN). Admin actions on either Pool/Configurator originate there.
12. **Low absolute volume.** RMM v2 is effectively dormant (0 events in recent multi-day windows; activity concentrated in 2022–2023). RMM v3 is active but small (single-digit `Supply` per recent ~48k-block window). Wide log windows (and patience) are needed to sample events.
13. **No FlashLoan/Liquidation activity sampled recently.** `FlashLoan` (v2 topic `0x631042c8…`) and `LiquidationCall` returned 0 in the windows scanned — the events/selectors are correct (inherited Aave constants, recomputed) but rarely fire; treat any occurrence as high-signal.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== RMM v2 (Aave V2) topics =====
TOPIC_V2_DEPOSIT             = '\xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951'
TOPIC_V2_WITHDRAW            = '\x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'  -- shared v2/v3
TOPIC_V2_BORROW             = '\xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b'
TOPIC_V2_REPAY              = '\x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa'
TOPIC_V2_SWAP_RATE         = '\xea368a40e9570069bb8e6511d668293ad2e1f03b0d982431fd223de9f3b70ca6'
TOPIC_V2_FLASHLOAN         = '\x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac'
TOPIC_V2_ATOKEN_MINT       = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'
TOPIC_V2_ATOKEN_BURN       = '\x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2'
TOPIC_V2_VDEBT_MINT        = '\x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee'
TOPIC_V2_VDEBT_BURN        = '\x49995e5dd6158cf69ad3e9777c46755a1a826a446c6416992167462dad033b2a'

-- ===== RMM v3 (Aave V3) topics =====
TOPIC_V3_SUPPLY            = '\x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61'
TOPIC_V3_WITHDRAW          = '\x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'
TOPIC_V3_BORROW            = '\xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0'
TOPIC_V3_REPAY             = '\xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051'
TOPIC_V3_FLASHLOAN         = '\xefefaba5e921573100900a3ad9cf29f222d995fb3b6045797eaea7521bd8d6f0'
TOPIC_V3_ATOKEN_MINT       = '\x458f5fa412d0f69b08dd84872b0215675cc67bc1d5b6fd93300a1c3878b86196'  -- aToken+varDebt
TOPIC_V3_ATOKEN_BURN       = '\x4cf25bc1d991c17529c25213d3cc0cda295eeaad5f13f361969b12ea48015f90'

-- ===== Shared (both generations) =====
TOPIC_LIQUIDATIONCALL      = '\xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
TOPIC_RESERVE_DATA_UPDATED = '\x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a'
TOPIC_COLLATERAL_ENABLED   = '\x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2'
TOPIC_COLLATERAL_DISABLED  = '\x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd'
TOPIC_BALANCE_TRANSFER     = '\x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666'
TOPIC_ERC20_TRANSFER       = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_UPGRADED             = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors =====
SEL_V2_DEPOSIT             = '\xe8eda9df'
SEL_V3_SUPPLY              = '\x617ba037'
SEL_WITHDRAW               = '\x69328dec'
SEL_BORROW                 = '\xa415bcad'
SEL_REPAY                  = '\x573ade81'
SEL_LIQUIDATION_CALL       = '\x00a718a9'   -- absent from both impl dispatchers; use the event
SEL_FLASHLOAN              = '\xab9c4b5d'
SEL_V3_FLASHLOAN_SIMPLE    = '\x42b0b77c'
SEL_SCALED_BALANCE_OF      = '\x1da24f3e'

-- ===== RMM v2 addresses (Gnosis, chain 100) =====
RMMV2_LENDING_POOL         = '\x5b8d36de471880ee21936f328aab2383a280cb2a'
RMMV2_ADDRESSES_PROVIDER   = '\x0ade75f269a054673883319baa50e5e0360a775f'
RMMV2_CONFIGURATOR         = '\xcc71725de4744da245c91cfb26457438c558f98b'
RMMV2_COLLATERAL_MANAGER   = '\x1c327865d4dd2348170153d5b6ed6fd48cf3389d'
RMMV2_ORACLE               = '\x1a88d967936a73326562d2310062ece226ed6664'
RMMV2_DATA_PROVIDER        = '\x8956488dc17cea7cbec19388aebdb37273f523be'
RMMV2_ATOKEN_WXDAI         = '\x7349c9eaa538e118725a6130e0f8341509b9f8a0'
RMMV2_VDEBT_WXDAI          = '\x6a7ced66902d07066ad08c81179d17d0fbe36829'

-- ===== RMM v3 addresses (Gnosis, chain 100) =====
RMMV3_POOL                 = '\xfb9b496519fca8473fba1af0850b6b8f476bfdb3'
RMMV3_ADDRESSES_PROVIDER   = '\xdaa06cf7adceb69fcfde68d896818b9938984a70'
RMMV3_CONFIGURATOR         = '\xc2af0ffe79eb3e0110c108f7b2d849818c338e8d'
RMMV3_ORACLE               = '\xb4ae809ad7ceb7e5b579dedd0de7c213ad5ab516'
RMMV3_ACL_MANAGER          = '\x6a1163daf9f5909990b547c15dbd672169464055'
RMMV3_DATA_PROVIDER        = '\x11b45acc19656c6c52f93d8034912083ac7dd756'
RMMV3_ATOKEN_WXDAI         = '\x0ca4f5554dd9da6217d62d8df2816c82bba4157b'
RMMV3_VDEBT_WXDAI          = '\x9908801df7902675c3fedd6fea0294d18d5d5d34'
RMMV3_ATOKEN_RTW_USD_01    = '\xf3220cd8f66aeb86fc2a82502977eab4bfd2f647'
RMMV3_ATOKEN_REUSD         = '\xd04c3b20f08b1d51f7429b2205491183a7b3583f'

-- ===== Shared governance / infra =====
RMM_GOV_OWNER              = '\x5fc96c182bb7e0413c08e8e03e9d7efc6cf0b099'
GNOSIS_WXDAI               = '\xe91d153e0b41518a2ce8dd3d7944fa863463a97d'
GNOSIS_USDC_NATIVE         = '\xddafbb505ad214d7b80b1f830fccc89b60fb7a83'
EIP1967_IMPL_SLOT          = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## 9. Decimals & math

- Indices `liquidityIndex` / `variableBorrowIndex` are **rays (27-dec)**: `actual = scaled * index / 1e27`.
- `getUserAccountData` (both generations) returns collateral/debt/borrows in **8-dec USD**; `healthFactor` in **1e18** (`< 1e18` = liquidatable; `type(uint256).max` = no debt).
- Oracle prices are **8-dec USD** (`BASE_CURRENCY_UNIT = 1e8`) on both generations.
- Underlying decimals: WXDAI / WETH / RealTokens / RTWxusd = **18-dec**; USDC (native Gnosis) / USDT = **6-dec**; WBTC = 8-dec.

---

## 10. Verification & sources

**How this was verified (all on 2026-06-08):**
- **Event topic0 & selectors:** recomputed locally as `keccak256(canonical signature)` (no parameter names; `uint`→`uint256`; tuples `(t,t)`; `indexed` dropped for hashing). Every value here matches the recompute.
- **Lineage:** determined from live impl bytecode selector scans — RMM v2 impl `0xa7d3…f4af` has `deposit`/`getAddressesProvider`/`paused`/`swapBorrowRateMode` and lacks all V3-only selectors → Aave V2; RMM v3 impl `0xd9cf…6833` has `supply`/`flashLoanSimple`/`setUserEMode`/`mintToTreasury`/`repayWithATokens`/`supplyWithPermit`/`ADDRESSES_PROVIDER` and lacks `multicall`/`getReserveDeficit` → early Aave V3. Confirmed by live `eth_getLogs`: v2 Pool emits `Deposit` (247) and zero V3 `Supply`; v3 Pool emits `Supply` (642) and `Borrow` (399).
- **Live event proof (Gnosis):** v2 LendingPool `0x5b8d…cb2a` window 24,960,000–25,008,000 — `Deposit` 247, `Borrow` 63, `Repay` 252, `Withdraw` 92, `ReserveDataUpdated` 654; v2 armmWXDAI `Mint` 623 / `Burn` 49. v3 Pool `0xFb9b…fdb3` window ~39,951,000–40,000,000 — `Supply` 642, `Borrow` 399, `ReserveDataUpdated` 1678; v3 armmv3WXDAI `Mint` 422 / `Burn` 115. Most-recent ~48k-block window — v3 `Supply` 9, v2 all events 0.
- **Topology:** resolved on-chain from each `PoolAddressesProvider` — v2 `getMarketId()` = "RealToken Money Market", `getLendingPool/Configurator/CollateralManager/PriceOracle/PoolAdmin/EmergencyAdmin`; v3 `getMarketId()` = "RMM V3", `getPool/PoolConfigurator/PriceOracle/ACLManager/ACLAdmin/PoolDataProvider`. Reserve token addresses from `AaveProtocolDataProvider.getReserveTokensAddresses`.
- **Existence / absence:** every contract `eth_getCode`-checked. All RMM contracts present (non-empty bytecode) on Gnosis (chain 100); **all RMM contracts return `0x` on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon** (swept and recorded — §5).
- **Proxies:** EIP-1967 impl slot read live (`eth_getStorageAt`) for Pools, Configurators, and a/debt tokens on both generations (impls in §6). EIP-1967 admin slot reads `0x` (Aave immutable-admin proxy stores admin in bytecode, not the slot). Providers/oracles confirmed non-proxy.

**Authoritative sources:**
- RealT RMM app & docs — [rmm.realtoken.network](https://rmm.realtoken.network/), [faq.realt.co](https://faq.realt.co/) (RMM/YAM usage, WETH Gateway, repaying debt).
- Aave governance forum — ["Deploy the RMM V2 with the Aave V3 version"](https://governance.aave.com/t/deploy-the-rmm-v2-with-the-aave-v3-version/11249) and ["Add armmWXDAI to Aave v3 Gnosis"](https://governance.aave.com/t/temp-check-add-armmwxdai-realt-rmm-xdai-deposit-token-to-aave-v3-gnosis/22378) (the RTWxusd wrapper / 128-market motivation).
- Canonical fork sources — [`aave/protocol-v2`](https://github.com/aave/protocol-v2) (RMM v2 ABI: LendingPool, Configurator, aToken/debt tokens) and [`aave-dao/aave-v3-origin`](https://github.com/aave-dao/aave-v3-origin) (RMM v3 ABI). Address parsing cross-checked against [`bgd-labs/aave-address-book`](https://github.com/bgd-labs/aave-address-book) Gnosis libraries for the standard Aave-Gnosis WXDAI/USDC underlyings.
- Explorer — [GnosisScan](https://gnosisscan.io/) (armmWXDAI `0x7349…f8a0`, RMM v3 Pool `0xFb9b…fdb3`, RTW-USD token `0xf3220cd8…`).

### Independent fact-check (2026-06-08)

| Claim | Verdict | Basis |
|------|---------|-------|
| RMM is deployed on Gnosis only; absent on all 7 monitored chains | **confirmed** | `eth_getCode` = `0x` for every RMM address on ETH/Base/BNB/Avax/Arb/OP/Polygon; non-empty on Gnosis. |
| Two generations coexist: RMM v2 (Aave V2) + RMM v3 (Aave V3) | **confirmed** | Distinct Pools with marketIds "RealToken Money Market" and "RMM V3"; impl-bytecode selector scans + live event ABIs differ as expected. |
| RMM is an "Aave V2 fork" (per the task brief) | **corrected/refined** | The *original* RMM is Aave V2, but the **active** market is an Aave **V3** fork (RMM v3). Both documented here. |
| RMM v3 caps at 4 reserves via an RTWxusd wrapper to dodge Aave's 128-market limit | **confirmed** | `getReservesList()` returns 4 (WXDAI, USDC, RTW-USD-01, REUSD); wrapper underlyings verified (`RealToken Wrapped USD 01`, `Realtoken Ecosystem USD`); matches the Aave-governance rationale. |
| RMM v2 account data is in USD (not ETH like stock Aave V2) | **confirmed** | Oracle `BASE_CURRENCY_UNIT = 1e8` with a synthetic 8-dec USD base token (`0x678df341…`). |
| `liquidationCall` selector absent from both Pool impls; detect via event | **confirmed** | PUSH4 scan = 0 occurrences on both impls; `LiquidationCall` topic is the canonical detector (same pattern as Aave V3 / SparkLend). |
| RMM v3 lacks Aave v3.3/v3.4 features | **confirmed** | `multicall` / `getReserveDeficit` absent from the v3 impl; it is an early V3 fork still carrying stableDebtTokens. |
