# Agave — Topics, Selectors, Addresses (NONE of the 7 target chains; primary deployment = Gnosis Chain, chain 100)

**Status:** verified against live RPC on all seven requested chains + Gnosis Chain (chain 100), and against the canonical `Agave-DAO/protocol-v2` `deployed-contracts.json` + `Agave-DAO/agave-subgraph` config, on 2026-06-08. Every topic0/selector recomputed locally as `keccak256(signature)`; every address existence-checked via `eth_getCode`; proxy slots read live.

**Scope:** the user asked about Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137). **Agave is deployed on NONE of these seven chains.** Its one and only production lending market lives on **Gnosis Chain (xDai, chainId 100)** — which is *not* one of the seven targets. Every Agave address returns empty `eth_getCode` (`0x`) on all 7 targets (§4 records each). Topics/selectors are chain-agnostic (and reusable if Agave ever multi-chains); addresses are network-specific and documented below in a clearly-labelled **off-target reference** (§3) so the doc has real on-chain anchors.

> **Headline finding — Agave is ABSENT on all 7 requested chains.** It exists only on Gnosis Chain. **Do not author Agave monitors against any of the 7 target chains.**

> **Polygon decoy (resolved — read this before trusting any "Agave on Polygon" claim).** The Agave subgraph ships a `config/matic.json` that *looks* like an Agave Polygon deployment, but its `LendingPoolAddressesProviderRegistry` (`0x3ac4e9aa29940770aeC38fe853a4bbabb2dA9C19`) and `AaveOracle` (`0x0229F777B0fAb107F9591a41d5F02E4e98dB6f2d`) resolve on-chain to the **canonical Aave V2 Polygon market** — Pool `0x8dFf5E27EA6b7AC08EbFdf9eB090F32ee9a30fcf`, Provider `0xd05e3E715d945B59290df0ae8eF85c1BdB684744`, whose reserve aTokens carry the symbols **`amUSDC`/`amDAI`/`amWMATIC`** (Aave Matic Market), **not** Agave's `ag*` prefix (verified live: `symbol()` returns `amUSDC`). The Agave matic.json is a leftover template pointing at Aave's own deployment. **There is NO Agave-branded market on Polygon.** `deployed-contracts.json` lists only `xdai` (+ testnets `rinkeby`/`hardhat`). Treat any Polygon "Agave" address as Aave V2 Polygon, attributable to [aave/v2.md](../aave/v2.md), not to Agave.

Agave is a near-verbatim **fork of Aave V2** (`aave/protocol-v2`), branded for Gnosis Chain. Consequences for monitoring:

1. **Event topics & function selectors are byte-for-byte identical to Aave V2** — `Deposit` (not V3's `Supply`), `Borrow`, `Repay`, `Withdraw`, `LiquidationCall`, `FlashLoan`, `ReserveDataUpdated`, plus the **3-arg aToken `Mint`/`Burn`** and the **separate variableDebt/stableDebt `Mint`/`Burn`**. See [aave/v2.md](../aave/v2.md). The aTokens are **agTokens** (agWXDAI, agUSDC, …) but mechanically identical Aave V2 aTokens.
2. **`getUserAccountData` is denominated in ETH/wei (1e18), NOT USD** — Aave V2 semantics, not V3's 8-dec USD. On Gnosis the "ETH" base-unit is conceptually whatever the oracle base is (wei-scaled), so health-factor math follows V2.
3. **The Gnosis market is effectively dormant and ownerless.** `LendingPoolAddressesProvider.owner()`, `getPoolAdmin()` and `getEmergencyAdmin()` all return `0xdEAD00000000000000000000000000000000dEAD` (the `dEAD…dEAD` burn address — **not** the all-zeros `0x…0000dEaD`) — governance was **burned to the dead address** (post the March 2022 reentrancy/flash-loan exploit and subsequent wind-down). The pool is **not** paused (`paused()` = false) and still processes withdrawals/repayments/liquidations, but new activity is minimal (only `ReserveDataUpdated` accrual logs in recent 50k-block windows; no recent `Deposit`).
4. **agTokens are directly-deployed (NOT proxies).** Unlike canonical Aave V2 (where aTokens sit behind `InitializableImmutableAdminUpgradeabilityProxy`), Agave's agTokens are full ~10 KB logic contracts with all-zero storage and the underlying baked in as an immutable. They are **not upgradeable** and have **no EIP-1967 impl slot** (reads `0x`). The `LendingPool`/`Configurator`/`IncentivesController` *are* upgradeable proxies (§7).

---

## 0. Contract families & versions

| Family | Contracts | Upgradeable? |
|--------|-----------|--------------|
| Core market | `LendingPool` (proxy), `LendingPoolConfigurator` (proxy), `LendingPoolCollateralManager` (delegatecall lib) | Pool/Configurator = yes; CollateralManager = logic lib |
| Registry | `LendingPoolAddressesProvider`, `LendingPoolAddressesProviderRegistry` | No (plain registries) |
| Per-reserve tokens | `agToken` (aToken), `variableDebtToken`, `stableDebtToken` per reserve | **No** (directly deployed) |
| Oracles | `AgaveOracle` (price), `LendingRateOracle` (stable-rate ref), `ChainlinkSourcesRegistry` | No |
| Read helpers | `AaveProtocolDataProvider`, `WalletBalanceProvider`, `WETHGateway` (WXDAI gateway) | No |
| Incentives | `StakedTokenIncentivesController` (proxy), reward token = **Balancer 50AGVE-50GNO BPT** | IC = yes |
| Token / safety | `AGVE` token, `stkAGVE` (Staked Agave safety module) | stkAGVE = proxy |

Pool implementation lineage (Gnosis): originally deployed at `0xDD6267CCCb38c3F6B0bC6bE373D80179C2Cda2EC` (23,035 B, per `deployed-contracts.json`), but the **live impl is `0x73280Cc830a4be3F14ab2439660361DC70D024Fd`** (24,545 B) — Agave upgraded the LendingPool after the 2022 exploit. **There is drift between the repo's recorded impl and the live impl — always read the live EIP-1967 slot.**

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-08. `ReserveDataUpdated` (and the V2 `Withdraw`/`LiquidationCall` set) additionally **confirmed against live Gnosis Agave pool logs** (`0x5E15…6d9c`, recent 50k-block window) and against live Aave V2 logs. Identical to Aave V2 — Agave is a fork.

### 1.1 LendingPool (emits all lending activity) — Gnosis emitter `0x5E15d5E33d318dCEd84Bfe3F4EACe07909bE6d9c`

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

`Deposit` is the V2 supply event (**different topic0 from Aave V3 `Supply` `0x2b627736…`**). `Withdraw`, `LiquidationCall`, `ReserveDataUpdated`, and the collateral-enabled/disabled events share the **same topic0 as Aave V2/V3** — disambiguate by `(chainId, Pool address)`. `Borrow`/`Swap` carry `borrowRateMode`/`rateMode` (1 = stable, 2 = variable); stable rate is a live V2 feature.

### 1.2 agToken & debt tokens (per-reserve) — V2 signatures (differ from V3 and differ from each other)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address indexed from, uint256 value, uint256 index)` | **agToken** |
| `0x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2` | `Burn(address indexed from, address indexed target, uint256 value, uint256 index)` | **agToken** |
| `0x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee` | `Mint(address indexed from, address indexed onBehalfOf, uint256 value, uint256 index)` | **variableDebtToken** |
| `0x49995e5dd6158cf69ad3e9777c46755a1a826a446c6416992167462dad033b2a` | `Burn(address indexed user, uint256 amount, uint256 index)` | **variableDebtToken** |
| `0xc16f4e4ca34d790de4c656c72fd015c667d688f20be64eea360618545c4c530f` | `Mint(address indexed user, address indexed onBehalfOf, uint256 amount, uint256 currentBalance, uint256 balanceIncrease, uint256 newRate, uint256 avgStableRate, uint256 newTotalSupply)` | **stableDebtToken** (8-arg) |
| `0x44bd20a79e993bdcc7cbedf54a3b4d19fb78490124b6b90d04fe3242eea579e8` | `Burn(address indexed user, uint256 amount, uint256 currentBalance, uint256 balanceIncrease, uint256 avgStableRate, uint256 newTotalSupply)` | **stableDebtToken** (6-arg) |
| `0x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666` | `BalanceTransfer(address indexed from, address indexed to, uint256 value, uint256 index)` | agToken |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 (agToken + debt tokens) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | agToken |
| `0xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1` | `BorrowAllowanceDelegated(address indexed fromUser, address indexed toUser, address indexed asset, uint256 amount)` | debt token (credit delegation) |

> **Three distinct `Mint`/`Burn` topic0s** across agToken / variableDebt / stableDebt — disambiguate by `(topic0, emitting address)`. The **3-arg agToken `Mint` topic0 `0x4c209b5f…` collides with Uniswap-V2's `Mint`** (same `Mint(address,uint256,uint256)` sig) — disambiguate by emitter. `value`/`index`: `scaled = value * 1e27 / index` (index is the reserve's ray `liquidityIndex`/`variableBorrowIndex`).

### 1.3 LendingPoolConfigurator (risk admin) — Gnosis `0x4a1ac23dC8df045524cf8b59B25D1ccAe2eA62F5`

| topic0 | Event |
|--------|-------|
| `0x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f` | `ReserveInitialized(address indexed asset, address indexed aToken, address stableDebtToken, address variableDebtToken, address interestRateStrategyAddress)` |
| `0xab2f7f9e5ca2772fafa94f355c1842a80ae6b9e41f83083098d81f67d7a0b508` | `BorrowingEnabledOnReserve(address indexed asset, bool stableRateEnabled)` |
| `0xe9a7e5fd4fc8ea18e602350324bf48e8f05d12434af0ce0be05743e6a5fdcb9e` | `BorrowingDisabledOnReserve(address indexed asset)` |
| `0x637febbda9275aea2e85c0ff690444c8d87eb2e8339bbede9715abcc89cb0995` | `CollateralConfigurationChanged(address indexed asset, uint256 ltv, uint256 liquidationThreshold, uint256 liquidationBonus)` |
| `0x35b80cd8ea3440e9a8454f116fa658b858da1b64c86c48451f4559cefcdfb56c` | `ReserveActivated(address indexed asset)` |
| `0x6f60cf8bd0f218cabe1ea3150bd07b0b758c35c4cfdf7138017a283e65564d5e` | `ReserveDeactivated(address indexed asset)` |
| `0x85dc710add8a0914461a7dc5a63f6fc529a7700f8c6089a3faf5e93256ccf12a` | `ReserveFrozen(address indexed asset)` |
| `0x838ecdc4709a31a26db48b0c853212cedde3f725f07030079d793fb071964760` | `ReserveUnfrozen(address indexed asset)` |
| `0x2694ccb0b585b6a54b8d8b4a47aa874b05c257b43d34e98aee50838be00d3405` | `ReserveFactorChanged(address indexed asset, uint256 factor)` |

### 1.4 LendingPoolAddressesProvider — Gnosis `0x3673C22153E363B1da69732c4E0aA71872Bbb87F`

| topic0 | Event |
|--------|-------|
| `0x1eb35cb4b5bbb23d152f3b4016a5a46c37a07ae930ed0956aba951e231142438` | `ProxyCreated(bytes32 id, address indexed newAddress)` |
| `0xf2689d5d5cd0c639e137642cae5d40afced201a1a0327e7ac9358461dc9fff31` | `AddressSet(bytes32 id, address indexed newAddress, bool hasProxy)` |
| `0xc4e6c6cdf28d0edbd8bcf071d724d33cc2e7a30be7d06443925656e9cb492aa4` | `LendingPoolUpdated(address indexed newAddress)` |
| `0xdfabe479bad36782fb1e77fbfddd4e382671713527e4786cfc93a022ae763729` | `LendingPoolConfiguratorUpdated(address indexed newAddress)` |
| `0x991888326f0eab3df6084aadb82bee6781b5c9aa75379e8bc50ae86934541638` | `LendingPoolCollateralManagerUpdated(address indexed newAddress)` |
| `0xc20a317155a9e7d84e06b716b4b355d47742ab9f8c5d630e7f556553f582430d` | `ConfigurationAdminUpdated(address indexed newAddress)` |
| `0xe19673fc861bfeb894cf2d6b7662505497ef31c0f489b742db24ee3310826916` | `EmergencyAdminUpdated(address indexed newAddress)` |
| `0xefe8ab924ca486283a79dc604baa67add51afb82af1db8ac386ebbba643cdffd` | `PriceOracleUpdated(address indexed newAddress)` |
| `0x5c29179aba6942020a8a2d38f65de02fb6b7f784e7f049ed3a3cab97621859b5` | `LendingRateOracleUpdated(address indexed newAddress)` |
| `0x5e667c32fd847cf8bce48ab3400175cbf107bdc82b2dea62e3364909dfaee799` | `MarketIdSet(string newMarketId)` |

Registry: `AddressesProviderRegistered(address)` = `0x2db38786c10176b033a1608361716b0ca992e3af55dc05b6dc710969790beeda`; `AddressesProviderUnregistered(address)` = `0x851e5971c053e6b76e3a1e0b8ffa81430df738007fad86e195c409a757faccd2`.

### 1.5 AgaveOracle (price aggregator) — live Gnosis emitter `0x062b9d1D3F5357Ef399948067E93B81F4B85db7a`

| topic0 | Event |
|--------|-------|
| `0x22c5b7b2d8561d39f7f210b6b326a1aa69f15311163082308ac4877db6339dc1` | `AssetSourceUpdated(address indexed asset, address indexed source)` |
| `0xce7a780d33665b1ea097af5f155e3821b809ecbaa839d3b33aa83ba28168cefb` | `FallbackOracleUpdated(address indexed fallbackOracle)` |

### 1.6 StakedTokenIncentivesController — Gnosis `0xfa255f5104f129B78f477e9a6D050a02f31A5D86`

| topic0 | Event |
|--------|-------|
| `0x2468f9268c60ad90e2d49edb0032c8a001e733ae888b3ab8e982edf535be1a76` | `RewardsAccrued(address indexed user, uint256 amount)` |
| `0x5637d7f962248a7f05a7ab69eec6446e31f3d0a299d997f135a65c62806e7891` | `RewardsClaimed(address indexed user, address indexed to, address indexed claimer, uint256 amount)` |
| `0x87fa03892a0556cb6b8f97e6d533a150d4d55fcbf275fff5fa003fa636bcc7fa` | `AssetConfigUpdated(address indexed asset, uint256 emission)` |
| `0x5777ca300dfe5bead41006fbce4389794dbc0ed8d6cccebfaf94630aa04184bc` | `AssetIndexUpdated(address indexed asset, uint256 index)` |
| `0xbb123b5c06d5408bbea3c4fef481578175cfb432e3b482c6186f02ed9086585b` | `UserIndexUpdated(address indexed user, address indexed asset, uint256 index)` |
| `0x4925eafc82d0c4d67889898eeed64b18488ab19811e61620f387026dec126a28` | `ClaimerSet(address indexed user, address indexed claimer)` |

> **Reward token is the Balancer 50AGVE-50GNO BPT** (`0x388cae2f7d3704c937313d990298ba67d70a3709`, `REWARD_TOKEN()` verified live), **not** raw AGVE. EmissionManager = `0x6626528de0c75ccc7a0d24f2d24b99060f74edee`.

### 1.7 Proxy admin (EIP-1967 / Aave proxy) events

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All Pool selectors verified **present** in the live Gnosis Pool impl bytecode `0x73280Cc8…` (24,545 B) on 2026-06-08 **except `liquidationCall`** (§7.2 dispatcher anomaly). Identical to Aave V2.

### 2.1 LendingPool — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe8eda9df` | `deposit(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)` | Emits `Deposit`. **V3 renamed this `supply` (`0x617ba037`).** |
| `0x69328dec` | `withdraw(address asset, uint256 amount, address to)` → `uint256` | `amount = type(uint256).max` = full balance. Shared w/ Aave V3. |
| `0xa415bcad` | `borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)` | Mode 1 = stable, 2 = variable. |
| `0x573ade81` | `repay(address asset, uint256 amount, uint256 rateMode, address onBehalfOf)` → `uint256` | |
| `0x94ba89a2` | `swapBorrowRateMode(address asset, uint256 rateMode)` | Stable↔variable (functional in V2). |
| `0xcd112382` | `rebalanceStableBorrowRate(address asset, address user)` | |
| `0x5a3b74b9` | `setUserUseReserveAsCollateral(address asset, bool useAsCollateral)` | |
| `0x00a718a9` | `liquidationCall(address collateralAsset, address debtAsset, address user, uint256 debtToCover, bool receiveAToken)` | Emits `LiquidationCall`. **ABSENT from live impl dispatcher — detect via event (§7.2).** |
| `0xab9c4b5d` | `flashLoan(address receiverAddress, address[] assets, uint256[] amounts, uint256[] modes, address onBehalfOf, bytes params, uint16 referralCode)` | Multi-asset (the vector for the 2022 reentrancy exploit). |

### 2.2 LendingPool — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xbf92857c` | `getUserAccountData(address user)` | `(totalCollateralETH, totalDebtETH, availableBorrowsETH, currentLiquidationThreshold, ltv, healthFactor)` — **base-unit/wei (1e18), NOT 8-dec USD.** HF in 1e18 (`< 1e18` = liquidatable). |
| `0x35ea6a75` | `getReserveData(address asset)` | Full V2 `ReserveData` struct (config bitmap, indices, rates, agToken/stable/variable token addrs, id). |
| `0xd15e0053` | `getReserveNormalizedIncome(address asset)` | `uint256` ray — supply index. |
| `0x386497fd` | `getReserveNormalizedVariableDebt(address asset)` | `uint256` ray — borrow index. |
| `0xc44b11f7` | `getConfiguration(address asset)` | Packed reserve config bitmap. |
| `0x4417a583` | `getUserConfiguration(address user)` | Packed user collateral/borrow bitmap. |
| `0xd1946dbc` | `getReservesList()` | `address[]` — 11 reserves live on Gnosis. |
| `0xfe65acfe` | `getAddressesProvider()` | `address` — the LendingPoolAddressesProvider. |
| `0x5c975abb` | `paused()` | `bool` (currently false on Gnosis). |

### 2.3 agToken / debt token

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1da24f3e` | `scaledBalanceOf(address user)` | **Use for accounting** — `balanceOf` rebases every block. |
| `0xb1bf962d` | `scaledTotalSupply()` | `uint256`. |
| `0xb16a19de` | `UNDERLYING_ASSET_ADDRESS()` | Underlying reserve token (immutable in agToken bytecode). |
| `0xc04a8a10` | `approveDelegation(address delegatee, uint256 amount)` | debt token — credit delegation. |
| `0x70a08231` / `0x18160ddd` | `balanceOf` / `totalSupply` | **Rebasing** — changes every block. |

### 2.4 LendingPoolAddressesProvider / AgaveOracle / DataProvider / IncentivesController

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x0261bf8b` | `getLendingPool()` → `address` | Provider |
| `0x85c858b1` | `getLendingPoolConfigurator()` → `address` | Provider |
| `0xfca513a8` | `getPriceOracle()` → `address` | Provider |
| `0x712d9171` | `getLendingPoolCollateralManager()` → `address` | Provider |
| `0xaecda378` | `getPoolAdmin()` → `address` | Provider (Gnosis = `0xdEAD…dEAD`) |
| `0xddcaa9ea` | `getEmergencyAdmin()` → `address` | Provider (Gnosis = `0xdEAD…dEAD`) |
| `0x21f8a721` | `getAddress(bytes32 id)` → `address` | Provider |
| `0x365ccbbf` | `getAddressesProvidersList()` → `address[]` | Registry |
| `0xb3596f07` | `getAssetPrice(address asset)` → `uint256` | AgaveOracle (base-unit price) |
| `0xd2493b6c` | `getReserveTokensAddresses(address asset)` → `(agToken, stableDebt, variableDebt)` | AaveProtocolDataProvider |
| `0x3111e7b3` | `claimRewards(address[] assets, uint256 amount, address to)` → `uint256` | IncentivesController |
| `0x8b599f26` | `getRewardsBalance(address[] assets, address user)` → `uint256` | IncentivesController |
| `0x198fa81e` | `getUserUnclaimedRewards(address user)` → `uint256` | IncentivesController |

---

## 3. Addresses — Gnosis Chain (chain ID 100) — **PRIMARY deployment (OFF-TARGET reference — outside the 7-chain monitoring scope)**

> These addresses are **on Gnosis Chain, chainId 100**, which is **NOT one of the 7 requested chains**. They are documented as real on-chain anchors. **Do NOT point a 7-chain monitor at them.** Source: `Agave-DAO/protocol-v2` `deployed-contracts.json` (`xdai`) + `Agave-DAO/agave-subgraph` `config/xdai.json`, all verified via `eth_getCode`/`eth_call` on `https://gnosis-rpc.publicnode.com`. Wiring confirmed: `Provider.getLendingPool()` → Pool, `Pool.getAddressesProvider()` → Provider.

### 3.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| **LendingPool** (proxy) | `0x5E15d5E33d318dCEd84Bfe3F4EACe07909bE6d9c` | Main entrypoint; emits all §1.1 events. |
| **LendingPoolAddressesProvider** | `0x3673C22153E363B1da69732c4E0aA71872Bbb87F` | Registry / source of truth. `owner()` = `0xdEAD…dEAD` (burned). |
| LendingPoolAddressesProviderRegistry | `0x4BaacD04B13523D5e81f398510238E7444E11744` | Lists Agave providers (`getAddressesProvidersList()` → `[0x3673…b87F]`). |
| **LendingPoolConfigurator** (proxy) | `0x4a1ac23dC8df045524cf8b59B25D1ccAe2eA62F5` | Risk admin; emits §1.3 events. |
| LendingPoolCollateralManager (live) | `0xd7E6500Dfb81A5B2553b7604Cb55305AA7db949F` | Delegatecall target for liquidations — **live** `getLendingPoolCollateralManager()` (verified across multiple Gnosis RPCs 2026-06-08). The older `0x897aac43B8F22BA093Ac1D7C6c36Cf91e458ee8C` is **superseded** — read the Provider live. |
| **AgaveOracle** (price, live) | `0x062b9d1D3F5357Ef399948067E93B81F4B85db7a` | **Live** `Provider.getPriceOracle()` (verified across multiple Gnosis RPCs 2026-06-08). **base = wei/ETH-scaled, not USD.** |
| AgaveOracle (superseded) | `0xe9E7153E03d1a77ee2aAf0A91e0D278e4F71B462` | **Earlier** AgaveOracle deployment (same interface, still live and returns prices) but the Provider **no longer points here** — current price oracle is `0x062b…db7a`. Do not key on this; read `Provider.getPriceOracle()` live. |
| AaveOracle (subgraph config alias) | `0x64cE22B5bA4175002AC5B6CCE3570432cA363c29` | Even-earlier oracle address recorded in `xdai.json`; superseded — read `Provider.getPriceOracle()` live. |
| LendingRateOracle | `0x08da9F00ec4DF6CfDec457985F324ec4E10530d3` | Stable-rate reference oracle. |
| ChainlinkSourcesRegistry | `0x3d0f609b9DD6b297C27735f1DbBA4ACdf3Af4FdF` | Chainlink feed registry. |
| **AaveProtocolDataProvider** | `0xBC01c7E3989a6011c1F9992a1BE7D58CCdDfe4c3` | Read helper (`getReserveTokensAddresses`, etc.). |
| WalletBalanceProvider | `0xc83259C1A02d7105A400706c3e1aDc054C5A1B87` | Batch token balances. |
| WETHGateway (WXDAI gateway) | `0xB48505A15E584E244e5E02bB72c4bDB0d13a9e59` | Native xDai ↔ WXDAI supply/repay helper. |
| **StakedTokenIncentivesController** (proxy) | `0xfa255f5104f129B78f477e9a6D050a02f31A5D86` | Liquidity-mining; rewards in 50AGVE-50GNO BPT. |

### 3.2 Token & governance / safety

| Role | Address | One-liner |
|------|---------|-----------|
| **AGVE** (governance token) | `0x3a97704a1b25F08aa230ae53B352e2e72ef52843` | `symbol()="AGVE"`, `name()="Agave Token"`. |
| **stkAGVE** (Staked Agave, safety module) | `0x610525b415c1BFAeAB1a3fc3d85D87b92f048221` | `symbol()="stkAGVE"`, `name()="Staked Agave"`. |
| Reward token (IC `REWARD_TOKEN()`) | `0x388cae2f7d3704c937313d990298ba67d70a3709` | Balancer **50AGVE-50GNO** BPT. |
| EmissionManager (IC) | `0x6626528de0c75ccc7a0d24f2d24b99060f74edee` | Controls reward emission. |
| PoolAdmin / EmergencyAdmin | `0xdEAD00000000000000000000000000000000dEAD` | **Burned** — governance renounced to the `dEAD…dEAD` burn address (verified live: `owner()`/`getPoolAdmin()`/`getEmergencyAdmin()` all return this; **not** the all-zeros `0x…0000dEaD`). |

### 3.3 Reserves (11 live) — underlying → agToken / variableDebtToken / stableDebtToken

agToken / debt tokens are **directly-deployed, non-upgradeable** (no proxy). Enumerate via `Pool.getReservesList()` + `DataProvider.getReserveTokensAddresses(asset)` — verified live 2026-06-08. The newer reserves (LINK/FOX/EURe/wstETH/sDAI) use vanity `0x00…` token addresses.

| Symbol | Underlying | agToken | variableDebtToken | stableDebtToken |
|--------|-----------|---------|-------------------|-----------------|
| WXDAI | `0xe91D153E0b41518A2Ce8Dd3D7944Fa863463a97d` | `0x5d0D1B231c90cB3e61A83f00C667f5Cd07dd6ee4` | `0x91A0beb56A2D746A9993307104941e5065d7ce1d` | `0x15346aDbfE1ed17543f72d664DE96F707E4a7B16` |
| USDC | `0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83` | `0x6a6A8F9951B07FE5EC750F5Aa14844B1dD872462` | `0x655aaBd40686B0402A8AED6698285B8D9A61f833` | `0xc7A83B684DA7676c3dFA63e061560365C5Cb15a0` |
| USDT | `0x4ECaBa5870353805a9F068101A40E0f32ed605C6` | *(via DataProvider — verify live)* | | |
| GNO | `0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb` | `0x05CB3Cf9935F78a34D0912c3422DD12F2b25538A` | `0xA5Fc8014F8f4B7C6d1111E123135fb4a48E70c66` | `0xa4eFbc2204eD45BBe08E6Bea5D091E561D427a3A` |
| WBTC | `0x8e5bBbb09Ed1ebdE8674Cda39A0c169401db4252` | `0x64C8DfdF4385E8a1bC49aFf24977A1084412117B` | `0xA08C7a035F8e1aD93ace15B1de1F1ae7C4300464` | `0x16121DD2E79b318f092883D8F40A7eE60d3AfE7b` |
| WETH | `0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1` | `0x9fC6aaCd739b3FCCB935fc2c7ac5958226e4cbaA` | `0x6fd4bC29f6dc14d8eAD37dB0116D55811e682EC8` | `0xF9488401Abcf1A2943312b4047d6Fc7Fbe50b2C9` |
| LINK | `0xE2e73A1c69ecF83F464EFCE6A5be353a37cA09b2` | `0x00a286Ce70Fb3a6269676C8d99bd9860dE212252` | `0x005b0568531322759eaB69269a86448B39b47e2a` | `0x004f9401Fb52FE53de977dCBF05a0F6237aADc7e` |
| FOX | `0x21a42669643f45Bc0e086b8Fc2ed70c23D67509d` | `0x00A916a4891D80494C6cB0B49b11Fd68238AaaF6` | `0x007388cBdeb284902e1E07bE616f92aDb3660ED3` | `0x006ca958336E7a1bdcdf7762aEB81613EaDDcC31` |
| EURe | `0xcB444e90D8198415266c6a2724b7900fb12FC56E` | `0x00eb20B07A9aBe765252e6B45e8292B12cb553Cc` | `0x00A4a45b550897dD5d8a44c68DBd245C5934EBac` | `0x0078A69AfC50e7705AD4588Cb57Cf8d27b29161e` |
| wstETH | `0x6C76971f98945AE98dD7d4DFcA8711ebea946eA6` | `0x00606b2689bA4a9F798F449fa6495186021486dd` | `0x00d0B168Fd6a4E220F1A8FA99dE97f8f428587E1` | `0x00eC7F91F26e7Fd42E90FFa53CA0b0b02095a6B4` |
| sDAI | `0xaf204776c7245bF4147c2612BF6e5972Ee483701` | `0x00e1cF0D5a56C993c3C2A0442dd645386aEff1Fc` | `0x00aD15Fec0026E28DfB10588fa35A383b07014e0` | `0x006927a7cda946910126008af78Eba50db641528` |

> `deployed-contracts.json` records only the original **8** reserves (WXDAI/USDC/LINK/STAKE/GNO/WBTC/WETH/FOX); the live pool has **11** (STAKE delisted; EURe/wstETH/sDAI added later via governance). USDT debt tokens were added post-repo — read `getReserveTokensAddresses(0x4ECaBa…)` live.

### 3.4 Implementations & logic libs (Gnosis)

| Role | Address |
|------|---------|
| LendingPool impl (live, current) | `0x73280Cc830a4be3F14ab2439660361DC70D024Fd` |
| LendingPool impl (repo `deployed-contracts.json`, **superseded**) | `0xDD6267CCCb38c3F6B0bC6bE373D80179C2Cda2EC` |
| LendingPoolConfigurator impl | `0x577773e87CAd8d57Be16baAFFe457a1B30e7641F` |
| IncentivesController impl (live) | `0x501e282847e87245e3D7a25515C69b7Ae8B4031A` |
| agToken reference impl | `0x3e2081400517E9eF8436401E0c06dC2cBe9eC2d2` |
| variableDebtToken reference impl | `0x9546320a15179d0F4ac6F5Dc0996C43Fa87325B0` |
| stableDebtToken reference impl | `0x5D9a99C1E2B0D7B0a446688FFaFB5189baC7Dc09` |
| ReserveLogic / GenericLogic / ValidationLogic | `0xaAf07A1B052049fA677EEabFC6a7e83b7301678f` · `0x2a3Da19ceCf5231c287260f74CD4098Ef154374f` · `0xDE41Aa7e5656d97Aa236460e4D59Daea807eAFDe` |

---

## 4. Target-chain absence sweep — Agave is NOT deployed on any of the 7

`eth_getCode` on each target's public RPC, 2026-06-08. **Every Agave Gnosis address returns `0x` on all 7 chains.** Recorded explicitly per the requirement that absence is a finding.

| Address checked | ETH (1) | Base (8453) | BNB (56) | Avax (43114) | Arb (42161) | OP (10) | Polygon (137) |
|---|---|---|---|---|---|---|---|
| Agave LendingPool `0x5E15…6d9c` | 0x | 0x | 0x | 0x | 0x | 0x | 0x |
| Agave Provider `0x3673…b87F` | 0x | 0x | 0x | 0x | 0x | 0x | 0x |
| AGVE token `0x3a97…2843` | 0x | 0x | 0x | 0x | 0x | 0x | 0x |

- **Ethereum / Base / BNB / Avalanche / Arbitrum / Optimism / Polygon:** Agave LendingPool, Provider and AGVE all absent (`0x`). No Agave markets, tokens or incentives on any target chain.
- **Polygon caveat (the decoy):** the addresses present on Polygon at `0x8dFf5E27…` (Pool) and `0xd05e3E71…` (Provider) — which the Agave subgraph's `matic.json` references — are the **Aave V2 Polygon** market (`amUSDC`/`amDAI` aTokens), NOT Agave. They belong to [aave/v2.md](../aave/v2.md). Agave never deployed a market on Polygon.
- **AGVE bridged token:** an AGVE ERC-20 exists on Arbitrum (`0x848e0ba28b637e8490d88bae51fa99c87116409b`, bridged) but there is **no Agave lending market** on Arbitrum — it is a bridged token only, not in scope for lending monitoring.

---

## 5. Cross-chain summary (presence matrix)

| Chain | ID | Agave LendingPool | AgaveOracle | IncentivesController | AGVE token | Agave lending market? |
|-------|----|-----|-----|-----|-----|-----|
| **Gnosis (off-target)** | 100 | `0x5E15…6d9c` | `0x062b…db7a` | `0xfa25…5D86` | `0x3a97…2843` | ✅ (dormant, gov burned) |
| Ethereum | 1 | — | — | — | — | ❌ |
| Base | 8453 | — | — | — | — | ❌ |
| BNB | 56 | — | — | — | — | ❌ |
| Avalanche | 43114 | — | — | — | — | ❌ |
| Arbitrum One | 42161 | — | — | — | (bridged AGVE only) | ❌ |
| Optimism | 10 | — | — | — | — | ❌ |
| Polygon PoS | 137 | — (decoy = Aave V2 Polygon) | — | — | — | ❌ |

**Three things to internalize:**
1. **Agave = Gnosis Chain only.** Zero footprint on the 7 targets. The only valid monitoring chain is chain 100 (off-target).
2. **It's an Aave V2 fork** — topics/selectors are byte-identical to Aave V2 (`Deposit` not `Supply`; ETH/wei account data not USD). Reuse [aave/v2.md](../aave/v2.md) detection set.
3. **The Gnosis market is governance-burned (`0xdEAD…dEAD`) and dormant.** Useful chiefly for residual liquidation/withdraw monitoring, not new originations.

---

## 6. Decimals & math (Aave V2 semantics)

- Indices `liquidityIndex`/`variableBorrowIndex` are **rays (27-dec)**: `actual = scaled * index / 1e27`.
- `getUserAccountData` collateral/debt/borrows in **base-unit/wei (1e18), NOT 8-dec USD** (key V2-vs-V3 difference). `healthFactor` in 1e18 (`< 1e18` = liquidatable; `type(uint256).max` = no debt).
- Stable rate is a live feature (mode 1); `Swap`/`RebalanceStableBorrowRate` are functional.
- WXDAI/WETH/GNO/wstETH/sDAI 18-dec; USDC/USDT 6-dec; WBTC 8-dec; EURe 18-dec.

---

## 7. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **LendingPool** | EIP-1967 `InitializableImmutableAdminUpgradeabilityProxy` (impl in EIP-1967 slot; **admin immutable in bytecode** = the AddressesProvider, so the EIP-1967 *admin* slot reads `0x`) | impl slot `0x3608…2bbc` = `0x73280Cc8…` | AddressesProvider (gov burned → frozen) |
| **LendingPoolConfigurator** | same Aave proxy | impl slot non-zero | AddressesProvider |
| **StakedTokenIncentivesController** | standard EIP-1967 transparent proxy | impl slot = `0x501e2828…` | proxy admin |
| stkAGVE | EIP-1967 proxy | impl slot non-zero | gov |
| **agTokens / variableDebt / stableDebt** | **NOT proxies — directly deployed logic** | impl slot reads `0x`; ~10 KB code with function dispatcher at byte 0; storage all-zero (underlying is an immutable) | **immutable / not upgradeable** |
| **LendingPoolAddressesProvider** | **NOT a proxy** (plain registry) | impl slot = `0x` | `owner()` (Gnosis = `0xdEAD…dEAD`) |
| LendingPoolAddressesProviderRegistry / AgaveOracle / DataProvider | **NOT proxies** | impl slot = `0x` | owner |

EIP-1967 impl slot: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`. Upgrade event: `Upgraded(address)` topic0 `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`.

### 7.1 Live implementations (Gnosis, read 2026-06-08)

| Proxy | Live impl | Repo-recorded impl | Drift? |
|---|---|---|---|
| LendingPool `0x5E15…6d9c` | `0x73280Cc830a4be3F14ab2439660361DC70D024Fd` | `0xDD6267CC…` | **YES** — repo stale; pool was upgraded post-2022-exploit. Read the live slot. |
| IncentivesController `0xfa25…5D86` | `0x501e282847e87245e3D7a25515C69b7Ae8B4031A` | — | read live |

### 7.2 The `liquidationCall` dispatcher anomaly (same as Aave/Spark)

In the live Gnosis Pool impl `0x73280Cc8…` (24,545 B), selector `0x00a718a9` (`liquidationCall`) is **absent from the bytecode** (PUSH4 scan = 0) while `deposit`/`withdraw`/`borrow`/`repay`/`flashLoan`/`swapBorrowRateMode`/`rebalanceStableBorrowRate`/`setUserUseReserveAsCollateral` are all present. Liquidations route through a `delegatecall` to the **LendingPoolCollateralManager** (live `0xd7E6500D…`, via `getLendingPoolCollateralManager()`) yet still emit `LiquidationCall` on the Pool. **Detect Agave liquidations by the `LiquidationCall` event topic0 `0xe413a321…`, never by the function selector**, and remember liquidations usually arrive via third-party bots so `tx.to` ≠ Pool.

---

## 8. Detection invariants & gotchas

1. **Agave is on Gnosis Chain (chain 100) ONLY — absent on all 7 requested chains.** Do not author 7-chain Agave monitors. The single valid target is the off-target Gnosis pool `0x5E15…6d9c`.
2. **The "Polygon Agave" is a decoy = Aave V2 Polygon.** The subgraph `matic.json` registry/oracle resolve to Aave's market (`amUSDC`/`amDAI`). Attribute to [aave/v2.md](../aave/v2.md), not Agave.
3. **It's an Aave V2 fork** — `Deposit`/`Borrow`/`Repay`/`Withdraw`/`LiquidationCall`/`FlashLoan`/`ReserveDataUpdated` topics + selectors are identical to Aave V2. `Deposit` (V2), not `Supply` (V3). Account data in **ETH/wei**, not USD.
4. **Three distinct aToken/debt `Mint`/`Burn` topic0s.** agToken `Mint` = 3-arg `0x4c209b5f…` (collides with Uniswap-V2 `Mint`); variableDebt `Mint` = `0x2f00e3cd…`, `Burn` = `0x49995e5d…`; stableDebt `Mint` = 8-arg `0xc16f4e4c…`, `Burn` = 6-arg `0x44bd20a7…`. **Disambiguate by `(topic0, emitting address)`.**
5. **agTokens are NOT proxies** — directly-deployed, non-upgradeable contracts with the underlying as an immutable (impl slot reads `0x`, storage all-zero). Don't expect an EIP-1967 impl behind an agToken.
6. **The Pool IS a proxy whose EIP-1967 admin slot reads `0x`** (admin is immutable = AddressesProvider). Read the **impl** slot for the logic; the repo-recorded impl is stale (drift — §7.1).
7. **Detect liquidations by the `LiquidationCall` event, not the selector** (§7.2) — selector absent from impl; routed via LendingPoolCollateralManager; bots make `tx.to` ≠ Pool.
8. **Governance is burned (`0xdEAD…dEAD`).** `getPoolAdmin()`/`getEmergencyAdmin()`/`owner()` all = the dead address. No new admin actions are possible — the config is effectively frozen. Any `ReserveFrozen`/config event would be historic.
9. **agTokens rebase every block** — store `scaledBalanceOf` + reconstruct with the reserve `liquidityIndex` (ray). Same for debt with `variableBorrowIndex`.
10. **`onBehalfOf` ≠ `tx.from`.** Attribute positions to `onBehalfOf`/`user` from the event, not the sender (WXDAI gateway, credit delegation, liquidation bots).
11. **Rewards pay in a Balancer 50AGVE-50GNO BPT** (`0x388cae2f…`), not raw AGVE. `RewardsClaimed` `amount` is denominated in that BPT.
12. **AGVE on Arbitrum (`0x848e…409b`) is a bridged token, not a market.** No Agave lending on Arbitrum.
13. **Reserve count drifted (8 in repo → 11 live).** Enumerate via `getReservesList()` + `getReserveTokensAddresses()`; don't hardcode the repo's 8.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; identical to Aave V2) =====
TOPIC_DEPOSIT                  = '\xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951'
TOPIC_WITHDRAW                 = '\x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'
TOPIC_BORROW                   = '\xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b'
TOPIC_REPAY                    = '\x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa'
TOPIC_SWAP_RATEMODE            = '\xea368a40e9570069bb8e6511d668293ad2e1f03b0d982431fd223de9f3b70ca6'
TOPIC_FLASHLOAN                = '\x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac'
TOPIC_LIQUIDATIONCALL          = '\xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
TOPIC_RESERVEDATAUPDATED       = '\x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a'
TOPIC_COLLATERAL_ENABLED       = '\x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2'
TOPIC_COLLATERAL_DISABLED      = '\x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd'
TOPIC_REBALANCE_STABLE         = '\x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300'
TOPIC_PAUSED                   = '\x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752'
TOPIC_UNPAUSED                 = '\xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933'
-- aToken / debt token (V2 — three distinct Mint/Burn, disambiguate by emitter)
TOPIC_AGTOKEN_MINT             = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'
TOPIC_AGTOKEN_BURN             = '\x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2'
TOPIC_VARDEBT_MINT             = '\x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee'
TOPIC_VARDEBT_BURN             = '\x49995e5dd6158cf69ad3e9777c46755a1a826a446c6416992167462dad033b2a'
TOPIC_STABLEDEBT_MINT          = '\xc16f4e4ca34d790de4c656c72fd015c667d688f20be64eea360618545c4c530f'
TOPIC_STABLEDEBT_BURN          = '\x44bd20a79e993bdcc7cbedf54a3b4d19fb78490124b6b90d04fe3242eea579e8'
TOPIC_BALANCE_TRANSFER         = '\x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666'
TOPIC_TRANSFER                 = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_BORROW_ALLOWANCE_DELEG   = '\xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1'
-- Configurator
TOPIC_RESERVE_INITIALIZED      = '\x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f'
TOPIC_COLLATERAL_CONFIG_CHG    = '\x637febbda9275aea2e85c0ff690444c8d87eb2e8339bbede9715abcc89cb0995'
TOPIC_RESERVE_FROZEN           = '\x85dc710add8a0914461a7dc5a63f6fc529a7700f8c6089a3faf5e93256ccf12a'
TOPIC_RESERVE_UNFROZEN         = '\x838ecdc4709a31a26db48b0c853212cedde3f725f07030079d793fb071964760'
-- Provider / Oracle / Incentives / Proxy
TOPIC_PROXY_CREATED            = '\x1eb35cb4b5bbb23d152f3b4016a5a46c37a07ae930ed0956aba951e231142438'
TOPIC_ADDRESS_SET              = '\xf2689d5d5cd0c639e137642cae5d40afced201a1a0327e7ac9358461dc9fff31'
TOPIC_LENDINGPOOL_UPDATED      = '\xc4e6c6cdf28d0edbd8bcf071d724d33cc2e7a30be7d06443925656e9cb492aa4'
TOPIC_ASSET_SOURCE_UPDATED     = '\x22c5b7b2d8561d39f7f210b6b326a1aa69f15311163082308ac4877db6339dc1'
TOPIC_REWARDS_ACCRUED          = '\x2468f9268c60ad90e2d49edb0032c8a001e733ae888b3ab8e982edf535be1a76'
TOPIC_REWARDS_CLAIMED          = '\x5637d7f962248a7f05a7ab69eec6446e31f3d0a299d997f135a65c62806e7891'
TOPIC_UPGRADED                 = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors (chain-agnostic) =====
SEL_DEPOSIT                    = '\xe8eda9df'
SEL_WITHDRAW                   = '\x69328dec'
SEL_BORROW                     = '\xa415bcad'
SEL_REPAY                      = '\x573ade81'
SEL_SWAP_BORROW_RATE_MODE      = '\x94ba89a2'
SEL_REBALANCE_STABLE           = '\xcd112382'
SEL_SET_USE_RESERVE_COLLATERAL = '\x5a3b74b9'
SEL_LIQUIDATIONCALL            = '\x00a718a9'
SEL_FLASHLOAN                  = '\xab9c4b5d'
SEL_GET_USER_ACCOUNT_DATA      = '\xbf92857c'
SEL_GET_RESERVE_DATA           = '\x35ea6a75'
SEL_GET_RESERVES_LIST          = '\xd1946dbc'
SEL_GET_RESERVE_TOKENS_ADDR    = '\xd2493b6c'
SEL_SCALED_BALANCE_OF          = '\x1da24f3e'
SEL_GET_LENDING_POOL           = '\x0261bf8b'
SEL_GET_PRICE_ORACLE           = '\xfca513a8'
SEL_GET_ASSET_PRICE            = '\xb3596f07'
SEL_CLAIM_REWARDS              = '\x3111e7b3'

-- ===== Addresses (Gnosis Chain / chainId 100 — OFF-TARGET; do NOT use on the 7 target chains) =====
GNOSIS_LENDINGPOOL             = '\x5e15d5e33d318dced84bfe3f4eace07909be6d9c'
GNOSIS_ADDRESSES_PROVIDER      = '\x3673c22153e363b1da69732c4e0aa71872bbb87f'
GNOSIS_PROVIDER_REGISTRY       = '\x4baacd04b13523d5e81f398510238e7444e11744'
GNOSIS_CONFIGURATOR            = '\x4a1ac23dc8df045524cf8b59b25d1ccae2ea62f5'
GNOSIS_COLLATERAL_MANAGER      = '\xd7e6500dfb81a5b2553b7604cb55305aa7db949f'   -- live getLendingPoolCollateralManager(); old 0x897aac43… superseded
GNOSIS_PRICE_ORACLE            = '\x062b9d1d3f5357ef399948067e93b81f4b85db7a'   -- live getPriceOracle(); old 0xe9e7…b462 superseded
GNOSIS_PROTOCOL_DATA_PROVIDER  = '\xbc01c7e3989a6011c1f9992a1be7d58ccddfe4c3'
GNOSIS_INCENTIVES_CONTROLLER   = '\xfa255f5104f129b78f477e9a6d050a02f31a5d86'
GNOSIS_WETH_GATEWAY            = '\xb48505a15e584e244e5e02bb72c4bdb0d13a9e59'
GNOSIS_LENDINGPOOL_IMPL_LIVE   = '\x73280cc830a4be3f14ab2439660361dc70d024fd'
GNOSIS_AGVE_TOKEN              = '\x3a97704a1b25f08aa230ae53b352e2e72ef52843'
GNOSIS_STKAGVE                 = '\x610525b415c1bfaeab1a3fc3d85d87b92f048221'
GNOSIS_REWARD_BPT_50AGVE50GNO  = '\x388cae2f7d3704c937313d990298ba67d70a3709'
-- agTokens (Gnosis)
GNOSIS_AGWXDAI                 = '\x5d0d1b231c90cb3e61a83f00c667f5cd07dd6ee4'
GNOSIS_AGUSDC                  = '\x6a6a8f9951b07fe5ec750f5aa14844b1dd872462'
GNOSIS_AGGNO                   = '\x05cb3cf9935f78a34d0912c3422dd12f2b25538a'
GNOSIS_AGWBTC                  = '\x64c8dfdf4385e8a1bc49aff24977a1084412117b'
GNOSIS_AGWETH                  = '\x9fc6aacd739b3fccb935fc2c7ac5958226e4cbaa'
-- NOTE: NO Agave addresses on Ethereum/Base/BNB/Avalanche/Arbitrum/Optimism/Polygon (all eth_getCode = 0x)
-- Polygon 0x8dff5e27ea6b7ac08ebfdf9eb090f32ee9a30fcf is AAVE V2 Polygon, NOT Agave.
```

---

## 10. Verification & sources

- **Fork identity & event/function signatures.** Agave is a fork of `aave/protocol-v2`; every topic0/selector in §1–§2 recomputed locally as `keccak256(canonical signature)` and matches Aave V2 ([aave/v2.md](../aave/v2.md)). Canonical sigs from `Agave-DAO/protocol-v2` (`contracts/`). `ReserveDataUpdated` topic0 `0x804c9b84…` confirmed in **live Gnosis Agave pool logs** (`0x5E15…6d9c`, 50k-block window ending block 46,591,268). `Withdraw`/`LiquidationCall`/`ReserveDataUpdated` additionally cross-checked against live Aave V2 logs (byte-identical, as expected for a fork).
- **Addresses.** Core set from `Agave-DAO/protocol-v2/deployed-contracts.json` (`xdai` block) and `Agave-DAO/agave-subgraph/config/xdai.json`. Wiring verified live on `https://gnosis-rpc.publicnode.com`: `Registry.getAddressesProvidersList()` → `[0x3673…b87F]`; `Provider.getLendingPool()` → `0x5E15…6d9c`; `Provider.getPriceOracle()` → `0x062b…db7a` (the older `0xe9E7…B462` is superseded); `Provider.getLendingPoolCollateralManager()` → `0xd7E6…949F` (the older `0x897a…ee8C` is superseded); `Provider.getPoolAdmin()`/`getEmergencyAdmin()`/`owner()` → `0xdEAD…dEAD` (the `dEAD…dEAD` burn address). Reserve agTokens/debt tokens read from `AaveProtocolDataProvider.getReserveTokensAddresses(asset)` for all 11 live reserves; symbols (`AGVE`, `stkAGVE`, `agUSDC`, …) confirmed via `symbol()`/`name()`. IncentivesController `REWARD_TOKEN()` → `0x388c…3709` (Balancer 50AGVE-50GNO BPT), `EMISSION_MANAGER()` → `0x6626…edee`.
- **Proxy classification.** EIP-1967 impl slot `0x3608…2bbc` read live: LendingPool → `0x73280Cc8…` (≠ repo `0xDD6267CC…`, drift recorded); IncentivesController → `0x501e2828…`. Provider, Registry, Oracle, DataProvider impl slots read `0x` (confirmed not proxies). agToken `0x6a6A…2462` (agUSDC): impl slot `0x`, 10,237 B code with a function dispatcher at byte 0, storage slots 0-12 all-zero → directly-deployed, non-upgradeable. LendingPool impl bytecode PUSH4 scan: `deposit`/`withdraw`/`borrow`/`repay`/`flashLoan`/`swapBorrowRateMode`/`rebalanceStableBorrowRate`/`setUserUseReserveAsCollateral` present; `liquidationCall` (`0x00a718a9`) absent (§7.2).
- **7-chain absence.** `eth_getCode` for the Agave LendingPool, Provider and AGVE on each of `ethereum-rpc`, `base-rpc`, `bsc-rpc`, `avalanche-c-chain-rpc`, `arbitrum-one-rpc`, `optimism-rpc`, `polygon-bor-rpc` (publicnode) — all returned `0x` (empty). The Polygon `0x8dFf5E27…`/`0xd05e3E71…` that the Agave `matic.json` references resolve on-chain to Aave V2 Polygon (`amUSDC` aToken symbol confirmed live) — a template decoy, not Agave.
- **Repos / explorers.** `github.com/Agave-DAO/protocol-v2`, `github.com/Agave-DAO/agave-subgraph`, `github.com/Agave-DAO/aave-stake-v2` (safety module), `github.com/Agave-DAO/incentives-controller`; `gnosisscan.io`; `agave.finance`; DeFiLlama `protocol/agave`. The 2022 reentrancy/flash-loan exploit (Hacxyk "Forked protocols are not battle-tested" write-up) explains the post-hack pool-impl upgrade and the subsequent governance burn to `0xdEAD…dEAD`.
