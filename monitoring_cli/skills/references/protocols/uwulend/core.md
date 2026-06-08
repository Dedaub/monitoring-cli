# UwU Lend — Topics, Selectors, Addresses (Ethereum mainnet only)

**Status:** verified against live Ethereum mainnet RPC (`eth_getCode` / `eth_call` / `eth_getStorageAt` / `eth_getLogs`) and the canonical `aave/protocol-v2` event/function ABIs on 2026-06-08. Every topic0/selector recomputed locally as `keccak256(signature)`; the LendingPool registry was walked on-chain from the live `LendingPoolAddressesProvider`.
**Scope:** the ENTIRE UwU Lend protocol — an **Aave V2 soft-fork**. Core lending (LendingPool behind `InitializableImmutableAdminUpgradeabilityProxy`, LendingPoolAddressesProvider, LendingPoolConfigurator, uTokens=aTokens, variable + stable debt tokens, the AaveOracle-style price oracle, LendingPoolCollateralManager, DefaultReserveInterestRateStrategy) plus the UWU reward periphery (UWU token, ChefIncentivesController, MultiFeeDistribution, WETHGateway). The user requested Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon — **UwU Lend exists on Ethereum (chain 1) ONLY.** All six other chains return `0x` (no bytecode) for every UwU contract — recorded as a verified absence in §5, not an omission. **Topics + selectors are chain-agnostic but UwU is single-chain; all addresses are Ethereum-mainnet.**

UwU Lend is a fork of **Aave V2** (`LendingPool`, not V3's `Pool`; supply event is **`Deposit`**, not `Supply`). Each reserve has a **uToken** (rebasing aToken, named e.g. "uWETH" / "UwU interest bearing WETH"), a `variableDebtToken`, and a `stableDebtToken`. Core contracts are **upgradeable proxies** (EIP-1967 impl slot; the proxy admin is an *immutable* constructor arg, not the EIP-1967 admin slot — so admin-slot reads return empty even though the contract is a proxy). The reward periphery (ChefIncentivesController, MultiFeeDistribution, UWU token) is **immutable** (plain, non-proxy). The registry root is the **`LendingPoolAddressesProvider` `0x011c0d38…f7f1fb`**, owned by the team multisig `0xb8416eac…3bc20d`; resolve everything from it (`getLendingPool()`, `getPriceOracle()`, etc.).

> **The oracle is the key risk surface — UwU was exploited twice in June 2024 (~$24M total).** Both exploits (2024-06-10 ≈ $19.4M and 2024-06-13 ≈ $3.7M) manipulated the **sUSDe / USDe price feed** (a Curve-EMA-based source feeding UwU's `AaveOracle`-style aggregator `0xac4a2ac7…772598`), inflating sUSDe collateral value to borrow out the pools. UwU's oracle returns **8-decimal USD** prices (e.g. `getAssetPrice(WETH) = 168918000000` = $1689.18, `getAssetPrice(DAI) = 99951115`), and routes some assets (incl. sUSDe) through a **fallback oracle `0x9bc63330…698b9`**. The protocol still runs — every live contract is documented below regardless. See §9 (invariants) for the oracle-monitoring detail.

---

## 0. Contract families

| Family | Pattern | Count / note |
|--------|---------|--------------|
| LendingPool / Configurator | EIP-1967 proxy, immutable admin = AddressesProvider | 1 each |
| LendingPoolAddressesProvider | plain ownable registry (NOT a proxy) | 1 (registry root) |
| uToken / variableDebtToken / stableDebtToken | EIP-1967 proxy, admin = Configurator; **per-reserve impl** (not a shared singleton) | 19 reserves × 3 |
| AaveOracle / LendingRateOracle / FallbackOracle | plain (replaceable via provider) | 1 each |
| LendingPoolCollateralManager | logic contract `delegatecall`ed by Pool on liquidation | 1 |
| DefaultReserveInterestRateStrategy | plain, per-reserve-group | several (shared by asset class) |
| WETHGateway | plain ETH↔WETH helper | 1 |
| ChefIncentivesController (CIC) | **immutable** MasterChef-style emitter | 1 active (+ legacy) |
| MultiFeeDistribution (MFD) | **immutable** lock/stake + reward minter | 1 active (+ legacy) |
| UWU token | plain ERC-20, owner-mintable | 1 |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally on 2026-06-08; the LendingPool / uToken / Configurator / Oracle / CIC / MFD topics marked **(live)** were additionally confirmed via `eth_getLogs` against the live UwU contracts.

### 1.1 LendingPool (emitter `0x2409aF02…87c668`) — Aave V2 signatures

| topic0 | Event |
|--------|-------|
| `0xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951` | `Deposit(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint16 indexed referral)` **(live)** |
| `0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7` | `Withdraw(address indexed reserve, address indexed user, address indexed to, uint256 amount)` **(live)** |
| `0xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b` | `Borrow(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint256 borrowRateMode, uint256 borrowRate, uint16 indexed referral)` |
| `0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa` | `Repay(address indexed reserve, address indexed user, address indexed repayer, uint256 amount)` |
| `0xea368a40e9570069bb8e6511d668293ad2e1f03b0d982431fd223de9f3b70ca6` | `Swap(address indexed reserve, address indexed user, uint256 rateMode)` (stable↔variable) |
| `0x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac` | `FlashLoan(address indexed target, address indexed initiator, address indexed asset, uint256 amount, uint256 premium, uint16 referralCode)` **(live)** |
| `0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286` | `LiquidationCall(address indexed collateralAsset, address indexed debtAsset, address indexed user, uint256 debtToCover, uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)` **(live — 30 logs / 40k blocks)** |
| `0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a` | `ReserveDataUpdated(address indexed reserve, uint256 liquidityRate, uint256 stableBorrowRate, uint256 variableBorrowRate, uint256 liquidityIndex, uint256 variableBorrowIndex)` **(live)** |
| `0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2` | `ReserveUsedAsCollateralEnabled(address indexed reserve, address indexed user)` |
| `0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd` | `ReserveUsedAsCollateralDisabled(address indexed reserve, address indexed user)` |
| `0x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300` | `RebalanceStableBorrowRate(address indexed reserve, address indexed user)` |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` |

**`Deposit`, not `Supply`** (UwU is V2). `Withdraw`, `LiquidationCall`, `ReserveDataUpdated`, and the collateral-enabled/disabled topics are **shared byte-for-byte with Aave V2 and V3** — disambiguate by emitter address (the LendingPool `0x2409aF02…`) + chain. `Borrow`/`Swap` carry `borrowRateMode`/`rateMode` (1=stable, 2=variable); stable rate is a real, enabled feature in V2 (stableDebtToken contracts exist per reserve).

### 1.2 uToken & debt tokens (per-reserve) — V2 signatures (differ from V3)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address indexed from, uint256 value, uint256 index)` | **uToken** **(live)** |
| `0x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2` | `Burn(address indexed from, address indexed target, uint256 value, uint256 index)` | **uToken** **(live)** |
| `0x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee` | `Mint(address indexed from, address indexed onBehalfOf, uint256 value, uint256 index)` | **variableDebtToken** |
| `0x49995e5dd6158cf69ad3e9777c46755a1a826a446c6416992167462dad033b2a` | `Burn(address indexed user, uint256 amount, uint256 index)` | **variableDebtToken** |
| `0x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666` | `BalanceTransfer(address indexed from, address indexed to, uint256 value, uint256 index)` | uToken |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 (uToken; debt tokens emit on mint/burn) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | uToken |
| `0xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1` | `BorrowAllowanceDelegated(address indexed fromUser, address indexed toUser, address indexed asset, uint256 amount)` | debt token |

> **V2 ≠ V3 token events.** uToken `Mint` is the 3-arg `Mint(address,uint256,uint256)` (topic `0x4c209b5f`); V3 uses a 5-arg `Mint` (`0x458f5fa4`). The **uToken and variableDebtToken `Mint`/`Burn` differ from each other in V2** (unlike V3 where they share a topic) — disambiguate by `(topic0, emitting address)`. Each `stableDebtToken` has its own multi-arg `Mint`/`Burn` (deprecated path; omitted). `value` is the actual amount; `index` is the reserve `liquidityIndex` / `variableBorrowIndex` (ray, 27-dec) → `scaled = value * 1e27 / index`.

### 1.3 LendingPoolConfigurator (emitter `0x408C9764…5b005c`) — Aave V2 admin

| topic0 | Event |
|--------|-------|
| `0x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f` | `ReserveInitialized(address indexed asset, address indexed aToken, address stableDebtToken, address variableDebtToken, address interestRateStrategyAddress)` |
| `0x637febbda9275aea2e85c0ff690444c8d87eb2e8339bbede9715abcc89cb0995` | `CollateralConfigurationChanged(address indexed asset, uint256 ltv, uint256 liquidationThreshold, uint256 liquidationBonus)` **(live)** |
| `0xab2f7f9e5ca2772fafa94f355c1842a80ae6b9e41f83083098d81f67d7a0b508` | `BorrowingEnabledOnReserve(address indexed asset, bool stableRateEnabled)` |
| `0xe9a7e5fd4fc8ea18e602350324bf48e8f05d12434af0ce0be05743e6a5fdcb9e` | `BorrowingDisabledOnReserve(address indexed asset)` |
| `0x85dc710add8a0914461a7dc5a63f6fc529a7700f8c6089a3faf5e93256ccf12a` | `ReserveFrozen(address indexed asset)` |
| `0x838ecdc4709a31a26db48b0c853212cedde3f725f07030079d793fb071964760` | `ReserveUnfrozen(address indexed asset)` |
| `0x35b80cd8ea3440e9a8454f116fa658b858da1b64c86c48451f4559cefcdfb56c` | `ReserveActivated(address indexed asset)` |
| `0x6f60cf8bd0f218cabe1ea3150bd07b0b758c35c4cfdf7138017a283e65564d5e` | `ReserveDeactivated(address indexed asset)` |
| `0x2694ccb0b585b6a54b8d8b4a47aa874b05c257b43d34e98aee50838be00d3405` | `ReserveFactorChanged(address indexed asset, uint256 factor)` |
| `0x8dee2b2f3e98319ae6347eda521788f73f4086c9be9a594942b370b137fb8cb1` | `StableRateEnabledOnReserve(address indexed asset)` |
| `0x8bbf35441ac2c607ddecadd3d8ee58636d32f217fad201fb2655581502dd84e3` | `StableRateDisabledOnReserve(address indexed asset)` |
| `0xa76f65411ec66a7fb6bc467432eb14767900449ae4469fa295e4441fe5e1cb73` | `ATokenUpgraded(address indexed asset, address indexed proxy, address indexed implementation)` |
| `0x9439658a562a5c46b1173589df89cf001483d685bad28aedaff4a88656292d81` | `VariableDebtTokenUpgraded(address indexed asset, address indexed proxy, address indexed implementation)` |
| `0x7a943a5b6c214bf7726c069a878b1e2a8e7371981d516048b84e03743e67bc28` | `StableDebtTokenUpgraded(address indexed asset, address indexed proxy, address indexed implementation)` |

### 1.4 LendingPoolAddressesProvider (emitter `0x011c0d38…f7f1fb`)

| topic0 | Event |
|--------|-------|
| `0xc4e6c6cdf28d0edbd8bcf071d724d33cc2e7a30be7d06443925656e9cb492aa4` | `LendingPoolUpdated(address indexed newAddress)` |
| `0xdfabe479bad36782fb1e77fbfddd4e382671713527e4786cfc93a022ae763729` | `LendingPoolConfiguratorUpdated(address indexed newAddress)` |
| `0xefe8ab924ca486283a79dc604baa67add51afb82af1db8ac386ebbba643cdffd` | `PriceOracleUpdated(address indexed newAddress)` |
| `0x5c29179aba6942020a8a2d38f65de02fb6b7f784e7f049ed3a3cab97621859b5` | `LendingRateOracleUpdated(address indexed newAddress)` |
| `0x1eb35cb4b5bbb23d152f3b4016a5a46c37a07ae930ed0956aba951e231142438` | `ProxyCreated(bytes32 id, address indexed newAddress)` |
| `0xf2689d5d5cd0c639e137642cae5d40afced201a1a0327e7ac9358461dc9fff31` | `AddressSet(bytes32 id, address indexed newAddress, bool hasProxy)` |

### 1.5 AaveOracle-style price oracle (emitter `0xac4a2ac7…772598`)

| topic0 | Event |
|--------|-------|
| `0x22c5b7b2d8561d39f7f210b6b326a1aa69f15311163082308ac4877db6339dc1` | `AssetSourceUpdated(address indexed asset, address indexed source)` **(live)** |
| `0xce7a780d33665b1ea097af5f155e3821b809ecbaa839d3b33aa83ba28168cefb` | `FallbackOracleUpdated(address indexed fallbackOracle)` |

### 1.6 Reward periphery — ChefIncentivesController + MultiFeeDistribution (UWU emissions)

CIC `0xf8390b84…d6c568`, MFD `0x630de118…2bdd44`. Topics confirmed from live MFD/CIC logs.

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x526824944047da5b81071fb6349412005c5da81380b336103fbe5dd34556c776` | `BalanceUpdated(address indexed token, address indexed user, uint256 balance, uint256 totalSupply)` | **CIC** **(live — 120 logs / 40k blocks; the workhorse)** |
| `0x30385c845b448a36257a6a1716e6ad2e1bc2cbe333cde1e69fe849ad6511adfe` | `Minted(address indexed user, uint256 amount)` (rewards minted/locked into MFD) | **MFD** **(live)** |
| `0x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5` | `Withdrawn(address indexed user, uint256 amount)` | **MFD** **(live)** |
| `0x37d4053e34fde482e96f6bcd424dfa31342cbd5fe184d497fb3c8bb4b4b97580` | `Staked(address indexed user, uint256 amount, bool locked)` | MFD |
| `0x540798df468d7b23d11f156fdb954cb19ad414d150722a7b6d55ba369dea792e` | `RewardPaid(address indexed user, address indexed rewardsToken, uint256 reward)` | MFD |
| `0x401321eacd32d0779a1de4ef7e54230af5e1a657bb38a39afb7f3916aecc357a` | `WithdrawnExpiredLocks(address indexed user, uint256 amount)` | MFD |

> The MFD here uses Geist/Radiant-style lock-staking but its dominant on-chain event is **`Minted(address,uint256)`** (topic `0x30385c84…`) — emitted when CIC-minted UWU is locked into a user's vesting position. The full Staked/RewardPaid set is in the ABI but fires less often. The **CIC `BalanceUpdated`** is the highest-frequency reward signal (fires on every supply/borrow that touches a tracked uToken/debt token).

### 1.7 Proxy upgrade

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` (EIP-1967 proxies — Pool, Configurator, uTokens, debt tokens) |

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

All LendingPool selectors below recomputed locally and verified **present in the live LendingPool impl `0x05bfa915…25ea4d` bytecode (21,953 bytes)** on 2026-06-08 — **except `liquidationCall`** (see §8.2). `borrow`/`repay`/`withdraw`/`flashLoan`/`liquidationCall` selectors are **identical to Aave V2 and V3** (same signatures); only `deposit` (V2) vs `supply` (V3) differ. Disambiguate by Pool address.

### 2.1 LendingPool — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe8eda9df` | `deposit(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)` | Emits `Deposit`. **V2 supply** (V3 = `supply` `0x617ba037`). PRESENT in impl. |
| `0x69328dec` | `withdraw(address asset, uint256 amount, address to)` → `uint256` | `amount = type(uint256).max` = full. PRESENT. |
| `0xa415bcad` | `borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)` | Mode 1=stable, 2=variable. PRESENT. |
| `0x573ade81` | `repay(address asset, uint256 amount, uint256 rateMode, address onBehalfOf)` → `uint256` | PRESENT. |
| `0x94ba89a2` | `swapBorrowRateMode(address asset, uint256 rateMode)` | Stable↔variable (functional in V2). PRESENT. |
| `0xcd112382` | `rebalanceStableBorrowRate(address asset, address user)` | PRESENT. |
| `0x5a3b74b9` | `setUserUseReserveAsCollateral(address asset, bool useAsCollateral)` | PRESENT. |
| `0x00a718a9` | `liquidationCall(address collateralAsset, address debtAsset, address user, uint256 debtToCover, bool receiveAToken)` | Emits `LiquidationCall`. **ABSENT from impl dispatcher** — delegatecalls LendingPoolCollateralManager (§8.2). **Detect via the event.** |
| `0xab9c4b5d` | `flashLoan(address receiverAddress, address[] assets, uint256[] amounts, uint256[] modes, address onBehalfOf, bytes params, uint16 referralCode)` | PRESENT. |
| `0xd5ed3933` | `finalizeTransfer(address asset, address from, address to, uint256 amount, uint256 balanceFromBefore, uint256 balanceToBefore)` | uToken-only callback. PRESENT. |
| `0x7a708e92` | `initReserve(address,address,address,address,address)` | Configurator-only. |
| `0xb8d29276` | `setConfiguration(address asset, uint256 configuration)` | Configurator-only. |

### 2.2 LendingPool — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xbf92857c` | `getUserAccountData(address user)` | `(totalCollateral, totalDebt, availableBorrows, currentLiquidationThreshold, ltv, healthFactor)`. **In UwU the oracle is USD-quoted (8-dec)** — verify the units against `getAssetPrice` (§9). HF in 1e18. |
| `0x35ea6a75` | `getReserveData(address asset)` | Full V2 `ReserveData` struct (config, indices, rates, uToken[7]/stableDebt[8]/varDebt[9]/strategy[10]). PRESENT. |
| `0xd15e0053` | `getReserveNormalizedIncome(address asset)` | ray supply index. |
| `0x386497fd` | `getReserveNormalizedVariableDebt(address asset)` | ray borrow index. |
| `0xc44b11f7` | `getConfiguration(address asset)` | Packed config bitmap. |
| `0x4417a583` | `getUserConfiguration(address user)` | Packed user bitmap. |
| `0xd1946dbc` | `getReservesList()` | `address[]` — **19 reserves** (§3.3). |
| `0xfe65acfe` | `getAddressesProvider()` | `address` → `0x011c0d38…f7f1fb`. |
| `0x5c975abb` | `paused()` | `bool`. |

### 2.3 uToken / debt token

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1da24f3e` | `scaledBalanceOf(address user)` | **Use for accounting** — `balanceOf` rebases. |
| `0xb1bf962d` | `scaledTotalSupply()` | |
| `0xb16a19de` | `UNDERLYING_ASSET_ADDRESS()` | Underlying reserve token. |
| `0xae167335` | `RESERVE_TREASURY_ADDRESS()` | uToken only. |
| `0xc04a8a10` | `approveDelegation(address delegatee, uint256 amount)` | debt token credit delegation. |
| `0x6bd76d24` | `borrowAllowance(address fromUser, address toUser)` | debt token. |
| `0x70a08231` / `0x18160ddd` | `balanceOf` / `totalSupply` | **Rebasing.** |

### 2.4 AddressesProvider / Oracle / strategy

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x0261bf8b` | `getLendingPool()` → `address` | AddressesProvider |
| `0x85c858b1` | `getLendingPoolConfigurator()` → `address` | AddressesProvider |
| `0xfca513a8` | `getPriceOracle()` → `address` | AddressesProvider |
| `0x3618abba` | `getLendingRateOracle()` → `address` | AddressesProvider |
| `0x21f8a721` | `getAddress(bytes32 id)` → `address` | AddressesProvider (e.g. `getAddress("COLLATERAL_MANAGER")`) |
| `0xb3596f07` | `getAssetPrice(address asset)` → `uint256` | Oracle — **8-dec USD** (verified). |
| `0x9d23d9f2` | `getAssetsPrices(address[] assets)` → `uint256[]` | Oracle |
| `0x92bf2be0` | `getSourceOfAsset(address asset)` → `address` | Oracle (per-asset feed; some assets fall through to fallback). |
| `0x6210308c` | `getFallbackOracle()` → `address` | Oracle → `0x9bc63330…698b9`. |
| `0x9584df28` | `calculateInterestRates(address,uint256,uint256,uint256,uint256,uint256)` | DefaultReserveInterestRateStrategy |
| `0xb2589544` / `0x7b832f58` / `0x65614f81` | `baseVariableBorrowRate()` / `variableRateSlope1()` / `variableRateSlope2()` | strategy (ray-encoded) |

### 2.5 Reward periphery — CIC / MFD / token

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x31873e2e` | `handleAction(address user, uint256 userBalance, uint256 totalSupply)` | CIC (called by uTokens/debt tokens → emits `BalanceUpdated`) |
| `0x77329f35` | `claimAll(address user)` | CIC |
| `0xabe50f19` | `stake(uint256 amount, bool lock)` | MFD |
| `0x3d18b912` | `getReward()` | MFD |
| `0xe9fad8ee` | `exit()` | MFD |
| `0x40c10f19` | `mint(address user, uint256 amount)` | UWU token (owner/CIC-only) |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` / `eth_call` on `https://ethereum-rpc.publicnode.com` on 2026-06-08. Wiring confirmed: `LendingPool.getAddressesProvider()` → Provider; `Provider.getLendingPool()` → Pool (round-trip); `Provider.getPriceOracle()` → Oracle.

### 3.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| **LendingPool** (proxy) | `0x2409aF0251DCB89EE3Dee572629291f9B087c668` | Main entrypoint; emits all §1.1 events. impl `0x05bfa915…25ea4d`. |
| **LendingPoolAddressesProvider** | `0x011c0d38da64B431a1Bdfc17aD72678eABf7f1fb` | Registry root (owner = team multisig `0xb8416eac…`). NOT a proxy. |
| **LendingPoolConfigurator** (proxy) | `0x408C9764993209dc772EB12fF641f4B55F5b005c` | Risk admin; emits §1.3. impl `0x40daf7be…835347`. |
| **Price oracle** (AaveOracle-style) | `0xaC4A2aC76D639E10f2C05a41274c1aF85B772598` | **8-dec USD** prices; routes some feeds via fallback. **Key risk surface.** |
| LendingRateOracle | `0x413A1F0098A8C5BA1078552Af515BD0146522Fe4` | Stable-rate reference oracle. |
| FallbackOracle | `0x9bC6333081266E55D88942e277FC809b485698B9` | Used when a per-asset source is unset (incl. sUSDe-class). |
| **LendingPoolCollateralManager** | `0x2E9F846cE3820531B52C08D3D4543BE5c8FE7DDb` | `delegatecall`ed by Pool during `liquidationCall`. |
| PoolAdmin (Gnosis Safe) | `0x0e1894D8642330FF917c04F57E2e88cd08cA465d` | Governance executor (multisig). |
| EmergencyAdmin (Gnosis Safe) | `0x4415F30f264593fcC0F28b93A8735b3c02357768` | Guardian (pause). |
| WETHGateway | `0xe08D97e151473A848C3D9CA3f323cB720472D015` | ETH↔WETH supply/withdraw/repay helper (UwU-specific sig; takes Pool as arg). |
| **UWU token** | `0x55C08ca52497e2f1534B59E2917BF524D4765257` | Reward/gov ERC-20 (18-dec, `totalSupply` 16,000,000 live = `0xd3c21bcecceda10000000`). owner `0x5dd596c9…c15d77`. |

### 3.2 Reward periphery (UWU emissions)

| Role | Address | One-liner |
|------|---------|-----------|
| **ChefIncentivesController** (active) | `0xf8390b84533Db97D3e415b4C7Bf4251953D6c568` | MasterChef-style; 38 pools; `BalanceUpdated` workhorse; mints to MFD. **Immutable** (non-proxy). owner = `0xb8416eac…`. |
| **MultiFeeDistribution** (active) | `0x630De1180a22e76e70e041DA5eB9b676CE2bdd44` | CIC.rewardMinter; lock-stakes UWU/WETH LP, vests UWU rewards. rewardToken = UWU. **Immutable.** |
| MFD staking token | (LP held by MFD, slot0 = team multisig wrapper `0xb8416eac…`) | UWU/WETH liquidity (see SushiSwap LP below). |
| SushiSwap UWU/WETH LP (SLP) | `0x3E04863DBa602713Bb5d0edbf7DB7C3A9A2B6027` | `SushiSwap LP Token` (token0=UWU, token1=WETH); staking asset for legacy MFDs. |
| Legacy CIC #1 | `0x21953192664867e19F85E96E1D1Dd79dc31cCcdB` | Superseded (no longer the active emitter; still has 24 stale pools, `rewardMinter` = legacy MFD `0x7c0bF110…`). uTokens point at the *active* CIC `0xf8390b84…`, not this one. |
| Legacy MFD #1 | `0x7c0bF1108935e7105E218BBB4f670E5942c5e237` | Tracked by DefiLlama as "PoolV1"; rewardToken=UWU, stakingToken=SLP. |
| Legacy CIC #2 | `0xdb5C23ae97f76dacC907F5F13bDa54131c8e9E5a` | Retired; rewardMinter = legacy MFD `0x0a7B2A21…`. |
| Legacy MFD #2 | `0x0a7B2A21027F92243C5e5E777aa30BB7969b0188` | Tracked by DefiLlama as "PoolV2"; rewardToken=UWU, stakingToken=SLP. |

> The reward system has migrated through several CIC↔MFD pairs. The **active pair is CIC `0xf8390b84…` ↔ MFD `0x630De118…`** (the uTokens' `getIncentivesController()` points at CIC `0xf8390b84…`, and CIC `.rewardMinter()` = MFD `0x630De118…`). DefiLlama's "PoolV1/PoolV2" labels are the *legacy MFD staking contracts*, NOT lending pools — do not mistake them for the LendingPool.

### 3.3 Reserves (19) — underlying → uToken / variableDebtToken / stableDebtToken / interestRateStrategy

uTokens/debt tokens are **per-reserve EIP-1967 proxies with per-asset implementations** (no shared singleton). All 19 underlyings have live bytecode. Read the live impl slot per token; do not hard-code.

| Symbol | Dec | Underlying | uToken | variableDebtToken | stableDebtToken |
|--------|-----|-----------|--------|-------------------|-----------------|
| DAI | 18 | `0x6B175474E89094C44Da98b954EedeAC495271d0F` | `0xb95BD0793bCC5524AF358ffaae3e38c3903C7626` | `0x1254b1Fd988a1168E44A4588Bb503a867f8e410F` | `0x20f6b999e189394d6a7301eCf485671042917EDf` |
| FRAX | 18 | `0x853d955aCEf822Db058eb8505911ED77F175b99e` | `0x8c240C385305Aeb2D5cEb60425aabcb3488fA93d` | `0x51e0F19BF0b765bc55724C7374Fe00ab229427D9` | `0x1E7aaC68f40A5019e9895749aB4997Fbbf9BC47f` |
| WETH | 18 | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` | `0x67FadBd9bf8899D7C578Db22D7af5e2E500e13e5` | `0xBaC9D17F290260a1d5F1B69cAc84dba6b4488d66` | `0xB55794603888363DEdf91C47d0b01af0201E88B7` |
| WBTC | 8 | `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599` | `0x6acE5C946A3aBd8241F31F182c479e67A4D8fc8d` | `0x64E4843ffDFB62D205b049dDbE8B949534e4E2D4` | `0xcaa6DfB9eF468e771c14df378843554abc7158F9` |
| sifu | 18 | `0x29127fE04ffa4c32AcAc0fFe17280ABD74Eac313` | `0x02738Ef3F8d8d3161dBBeDBdA25574154c560dAe` | `0x5c8CB0E43CB17553aB4A37011c3dc743AEB3F241` | `0xb2633960Aa357d091Da70034E439e4C8CcD2A289` |
| MIM | 18 | `0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3` | `0xc480a11A524e4DB27c6D4e814b4D9B3646bc12fc` | `0xd5BFD3D736477f48eFC873EE464F4A8b5447850B` | `0x463D8d094253064AE75F0eBF32848776964dF1f4` |
| LUSD | 18 | `0x5f98805A4E8be255a32880FDeC7F6728C6568bA0` | `0xaDfa5fA0c51d11b54c8a0B6a15F47987Bd500086` | `0x9abe34021128c17de3C2180a02932EB5e1Bb18Ef` | `0xeA2d26059Ae22a415b15B29Eaa81Ad310796f223` |
| sSPELL | 18 | `0x26FA3fFFB6EFE8c1E69103aCb4044C26B9A106a9` | `0x243387a7036Bfcb09f9BF4ECEd1e60765d31AA70` | `0x29d567fA37b4Af64dD1B886571cD1ff5D403AC3f` | `0x382e98B18888504C4D40Ad601A11d8d162Eb94B6` |
| CRV | 18 | `0xD533a949740bb3306d119CC777fa900bA034cd52` | `0xdb1A8F07F6964EfCfff1AA8025B8CE192ba59EbA` | `0xb9e8bcD56f26B0540989a66Aa24d431cdB0aFFa0` | `0xc3737bA9E6957D25696c9eD6Af470b8FE1164642` |
| wMEMO | 18 | `0x3b79a28264fC52c7b4CEA90558Aa0B162f7Faf57` | `0xc4BF704F51AA4CE1aA946Ffe15646f9b271bA0FA` | `0x13cDFdD18E6bb8d41be0a55d9CF697c0eF11176B` | `0x30b0a048De7A9015fDf21c67BF2491b39DDAd002` |
| USDT | 6 | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | `0x24959F75D7BDA1884f1Ec9861f644821Ce233c7D` | `0xaaC1d67F1c17ec01593d76e831c51A4F458Dc160` | `0x2350fd0d27762651Eb4d8df19f0fec882e3CC24A` |
| SifuM | 18 | `0x5938999DD0cc4D480c3b1A451aECC78ae4DDaAb5` | `0x8028Ea7Da2ea9bCb9288c1f6f603169b8AeA90A6` | `0x39A873f3F60Bb4cd81fE46f3beB6285BdB7726B9` | `0xD80A9E696Ad8b7Ed6c829bE5018D6a28df7d656d` |
| bLUSD | 18 | `0xB9D7DDDca9a4AC480991865EfEf82E01273F79C3` | `0x51144708b82eA3b5b1002C9DC38b71eC63b7e670` | `0xEc12F63116bD2493104a26fbDBcd70f51AB7B2C1` | `0x41C1A2a0CFE44832F8c512120077A95e3E383517` |
| Sifu | 18 | `0x8dD09822E83313aDcA54C75696aE80c5429697ff` | `0xd1e6B03BF65b381cBdeCCf275535d40D4c3510e2` | `0x453842BA9dCD4569407B2adeDeb8636314D023D3` | `0x45c29Cc32ed146E84E194639e3c989Ba9c83B88e` |
| Volta | 18 | `0x9b06f3C5dE42D4623d7a2bD940EC735103c68A76` | `0xe873e375065CE4dd7f96A289f74F885509748fAD` | `0x82a49C799c4Ca5bdb629bCd6107737A3DE8d2805` | `0x13F68f41dEdaD872F089206B1F25aDAEe4E1F343` |
| crvUSD | 18 | `0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E` | `0xeb61E567cBaeAccB6c259def92900Bc59D8a14CC` | `0xEb6a0037cA1087e783494B533a53a60e43f2DAbD` | `0xA4469EA3207f91e9DE38d477ea03e264F075bf3b` |
| sDAI | 18 | `0x83F20F44975D03b1b09e64809B757c47f942BEeA` | `0x20e61BA4365cc4bFA82B1449982E091904564Aa4` | `0xe42016bD5884555d9053a0F0563a34992C1d44e9` | `0x4BC2916C10aE5b22F5c9fC5E51b2BBcFEd979e04` |
| sUSDe | 18 | `0x9D39A5DE30e57443BfF2A8307A4256c8797A3497` | `0xf1293141fC6Ab23B2A0143ACc196e3429E0b67a6` | `0xD7f6e4e10fd1e7fAf642fA924c5Ea2b6C5450D11` | `0x51598d13B3B0d181F448485ce2B15DfE33AF8864` |
| DUMMY | 18 | `0xe3d0E323c6531EC9340cf3DDB1C29667798e8eBc` | `0x27Ef61CA55D9Fe28929fFf19E9bE42431a72253E` | `0x76aC0B9F3544fAaaCA910B13FAA0EC0Cc22448B4` | `0x24278d0cf1648bf9d2Fd91E8DA6855fF36c2dFA1` |

All uToken/debt addresses above were read live from `getReserveData(asset)` on 2026-06-08. The last reserve **"DUMMY"** (`0xe3d0…8eBc`) is a placeholder/test reserve — its uToken/debt tokens exist but it carries no real liquidity.

---

## 4. Cross-chain summary

| Chain | ID | UwU LendingPool? | Any UwU contract? |
|---|---|---|---|
| **Ethereum** | 1 | ✅ `0x2409aF02…87c668` | ✅ full protocol + UWU token + rewards |
| Base | 8453 | ❌ `0x` | ❌ none |
| BNB Smart Chain | 56 | ❌ `0x` | ❌ none |
| Avalanche C-Chain | 43114 | ❌ `0x` | ❌ none |
| Arbitrum One | 42161 | ❌ `0x` | ❌ none |
| Optimism | 10 | ❌ `0x` | ❌ none |
| Polygon PoS | 137 | ❌ `0x` | ❌ none |

**UwU Lend is Ethereum-mainnet-only.** Existence-checked via `eth_getCode` on all 7 RPCs (2026-06-08): the LendingPool, AddressesProvider, oracle, UWU token, CIC, and MFD all return `0x` (empty) on the six non-Ethereum chains. There is no bridged UWU and no satellite deployment. Topics/selectors are nominally chain-agnostic but in practice only ever fire on chain 1.

---

## 5. Proxies

Every UwU **core** contract is Aave V2's `InitializableImmutableAdminUpgradeabilityProxy` — EIP-1967 **impl** slot is populated, but the **admin is an immutable constructor arg** (so the EIP-1967 admin slot reads `0x0` — that does NOT mean "not a proxy"). The **reward periphery (CIC, MFD, UWU token) is immutable / plain** (impl slot empty). `LendingPoolAddressesProvider`, the oracle, and the rate strategies are plain (replaceable via the provider, not proxied).

EIP-1967 implementation slot: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`.

### 5.1 Live implementations (read 2026-06-08)

| Proxy | Address | Live impl | Upgrade authority |
|---|---|---|---|
| LendingPool | `0x2409aF02…87c668` | `0x05bfa9157e92690b179033ca2f6dd1e86b25ea4d` | `Provider.setLendingPoolImpl()` |
| LendingPoolConfigurator | `0x408C9764…5b005c` | `0x40daf7be3a99b898f54fb7968d16db5103835347` | `Provider.setLendingPoolConfiguratorImpl()` |
| uWETH (representative uToken) | `0x67FadBd9…0e13e5` | `0x550649c2a66ca0ad5fc54e74d5603c7be3b0e4aa` | `Configurator.updateAToken()` |
| variableDebtWETH | `0xBaC9D17F…488d66` | `0xa2c32a116e959ee35d5c99a2a575697814d9eebc` | `Configurator.updateVariableDebtToken()` |
| stableDebtWETH | `0xB5579460…1E88B7` | `0xbf772d84e26ceace3521b7c0ed5cf456149d7e96` | `Configurator.updateStableDebtToken()` |
| uDAI | `0xb95BD079…3C7626` | `0x3435ccfa639b756aa7c5097008ab70984524eaf5` | (per-reserve impl differs from uWETH) |
| variableDebtDAI | `0x1254b1Fd…8e410F` | `0x28d9ca44105ff50ae51edd3f43b4df67c541e51b` | |

> **uTokens/debt tokens have per-reserve impls** (uWETH ≠ uDAI impl) — unlike Spark/Aave-mainnet where a single aToken impl is shared. Always read the live EIP-1967 impl slot per token; never hard-code.

**Not proxies (impl slot empty):** LendingPoolAddressesProvider, price oracle `0xaC4A2aC7…`, LendingRateOracle, FallbackOracle, LendingPoolCollateralManager, the rate strategies, WETHGateway, ChefIncentivesController, MultiFeeDistribution, UWU token. The CIC and MFD are confirmed **immutable** (impl slot `0x0`, plain bytecode 18,694 / 11,026 bytes).

### 5.2 The `liquidationCall` dispatcher gotcha

The live LendingPool impl `0x05bfa915…25ea4d` (21,953 bytes) does **not** contain selector `0x00a718a9` (`liquidationCall`) — raw + `63`-prefixed PUSH4 scan = 0 occurrences — while `deposit` (`e8eda9df`), `withdraw`, `borrow`, `repay`, `flashLoan`, `finalizeTransfer` are all present. The LendingPoolCollateralManager `0x2E9F846c…` (10,735 bytes) also lacks the selector in its bytecode (it's reached by `delegatecall` and runs the liquidation logic). Nonetheless `LiquidationCall` events fire normally (30 in a 40k-block window) and liquidations execute. **Detect UwU liquidations by the `LiquidationCall` event topic0 `0xe413a321…`, never by the function selector.** Liquidations are also usually routed through bots, so `tx.to` ≠ LendingPool.

---

## 6. Decimals & math

- Indices `liquidityIndex` / `variableBorrowIndex` are **rays (27-dec)**: `actual = scaled * index / 1e27`.
- **Oracle prices are 8-decimal USD** (verified: WETH `168918000000`=$1689.18, DAI `99951115`=$0.9995, USDT `99962394`, sUSDe `104000000`=$1.04). This is a **deviation from canonical Aave V2** (which is ETH/wei-based). Treat `getUserAccountData` collateral/debt/borrows as **USD (8-dec)** here, and verify against `getAssetPrice` if in doubt; `healthFactor` is 1e18 (`< 1e18` = liquidatable).
- Reserve decimals: USDT 6; WBTC 8; everything else 18.
- Interest-rate strategy `0xca2a8300…edebf3` (shared by stablecoins/WETH/CRV/USDT/crvUSD): `baseVariableBorrowRate` 0.065e27, slope1 0.185e27, slope2 0.815e27, optimal utilization 0.90e27 (ray-encoded). Other asset classes use distinct strategies (e.g. `0xba285ed9…`, `0x9203a201…`, `0x690dcb18…`).
- UWU token: 18-dec, live `totalSupply` 16,000,000 UWU (`0xd3c21bcecceda10000000` = 16e6·1e18, verified via `totalSupply()`; note 100M·1e18 would be `0x52b7d2dcc80cd2e4000000`).

---

## 7. Detection invariants & gotchas

1. **UwU Lend is Ethereum-only.** All six other requested chains return `0x` for every UwU contract (§4). Any "UwU on L2" claim is false.
2. **It's an Aave V2 fork — `Deposit`, not `Supply`.** Supply event is `Deposit` (topic `0xde685721…`, selector `deposit` `0xe8eda9df`). Do not scan for V3's `Supply`/`supply`.
3. **The price oracle is the #1 risk surface.** UwU was exploited TWICE in June 2024 (~$24M total) via manipulation of the **sUSDe/USDe** feed into the `AaveOracle`-style aggregator `0xaC4A2aC7…772598`. **Monitor `AssetSourceUpdated` (topic `0x22c5b7b2…`) on the oracle, `FallbackOracleUpdated` (`0xce7a780d…`), and large/abrupt `getAssetPrice` deltas for sUSDe / sDAI / wMEMO / sSPELL / SifuM and the other thin LST/staked-token collaterals.** Several feeds (incl. sUSDe-class) resolve through the fallback oracle `0x9bC63330…698B9` rather than a per-asset Chainlink source — read `getSourceOfAsset` per asset.
4. **uToken vs variableDebtToken `Mint`/`Burn` have DIFFERENT topic0s** (V2 behavior). uToken `Mint`=`0x4c209b5f`, varDebt `Mint`=`0x2f00e3cd`. Match on `(topic0, emitting address)`.
5. **`Withdraw` / `LiquidationCall` / `ReserveDataUpdated` / collateral-enabled/disabled topics are shared with Aave V2 & V3** — disambiguate by the LendingPool address `0x2409aF02…` (single chain, so unambiguous here).
6. **Detect liquidations by the `LiquidationCall` event, not the selector** (§5.2). `liquidationCall` (`0x00a718a9`) is absent from the Pool impl bytecode (delegatecalls the CollateralManager `0x2E9F846c…`), and bots route them so `tx.to` ≠ Pool.
7. **uTokens rebase.** Store `scaledBalanceOf`, reconstruct with `liquidityIndex` (ray). Same for debt with `variableBorrowIndex`.
8. **`onBehalfOf` ≠ `tx.from`.** Attribute positions to `onBehalfOf`/`user` from the event (WETHGateway `0xe08D97e1…`, credit delegation, liquidation bots).
9. **Stable rate is real in V2.** `borrowRateMode`/`rateMode` 1=stable, 2=variable; `Swap`, `RebalanceStableBorrowRate`, and per-reserve `stableDebtToken`s are active.
10. **Reward attribution: CIC `BalanceUpdated` is the workhorse** (topic `0x52682494…`, 120 logs/40k blocks; fires on every supply/borrow touching a tracked token). UWU emissions are minted by the CIC `0xf8390b84…` into the MFD `0x630De118…` (event `Minted(address,uint256)` topic `0x30385c84…`), then vested/locked. **Use the active CIC↔MFD pair, not DefiLlama's "PoolV1/PoolV2"** which are the *legacy* MFD staking contracts (`0x7c0bF110…`, `0x0a7B2A21…`), not lending pools.
11. **Proxy admin slot is empty even though core contracts ARE proxies** (immutable-admin proxy pattern) — confirm proxy-ness via the populated EIP-1967 *impl* slot, not the admin slot.
12. **uToken/debt-token impls are per-reserve** (uWETH impl ≠ uDAI impl). Read each token's live impl slot; never assume a shared singleton.
13. **Reserves include thin/exotic collateral** (sifu/Sifu/SifuM, wMEMO, sSPELL, bLUSD, Volta, a "DUMMY" test reserve) on top of the standard stable/blue-chip set — these illiquid feeds are the historical attack vector; weight oracle-deviation alerts toward them.
14. **Governance = PoolAdmin Safe `0x0e1894D8…` + EmergencyAdmin Safe `0x4415F30f…`**; the AddressesProvider owner is the team multisig `0xb8416eac…` (also CIC owner). Admin actions (impl upgrades via `Upgraded`, `setLendingPoolImpl`, reserve config changes) originate from these.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; Aave V2 fork) =====
TOPIC_DEPOSIT                = '\xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951'
TOPIC_WITHDRAW               = '\x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'  -- shared V2/V3
TOPIC_BORROW                 = '\xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b'
TOPIC_REPAY                  = '\x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa'
TOPIC_SWAP_RATE              = '\xea368a40e9570069bb8e6511d668293ad2e1f03b0d982431fd223de9f3b70ca6'
TOPIC_FLASHLOAN              = '\x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac'
TOPIC_LIQUIDATIONCALL        = '\xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'  -- shared V2/V3; detect liq by THIS
TOPIC_RESERVE_DATA_UPDATED   = '\x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a'  -- shared V2/V3
TOPIC_COLLATERAL_ENABLED     = '\x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2'
TOPIC_COLLATERAL_DISABLED    = '\x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd'
TOPIC_REBALANCE_STABLE       = '\x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300'
TOPIC_PAUSED                 = '\x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752'
TOPIC_UNPAUSED               = '\xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933'
-- uToken / debt tokens (V2-specific; disambiguate by emitter) =====
TOPIC_UTOKEN_MINT            = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'  -- Mint(address,uint256,uint256)
TOPIC_UTOKEN_BURN            = '\x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2'
TOPIC_VDEBT_MINT             = '\x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee'  -- Mint(address,address,uint256,uint256)
TOPIC_VDEBT_BURN             = '\x49995e5dd6158cf69ad3e9777c46755a1a826a446c6416992167462dad033b2a'
TOPIC_BALANCE_TRANSFER       = '\x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666'
TOPIC_ERC20_TRANSFER         = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- Configurator / Provider / Oracle / proxy =====
TOPIC_RESERVE_INITIALIZED    = '\x3a0ca721fc364424566385a1aa271ed508cc2c0949c2272575fb3013a163a45f'
TOPIC_COLLATERAL_CFG_CHANGED = '\x637febbda9275aea2e85c0ff690444c8d87eb2e8339bbede9715abcc89cb0995'
TOPIC_RESERVE_FROZEN         = '\x85dc710add8a0914461a7dc5a63f6fc529a7700f8c6089a3faf5e93256ccf12a'
TOPIC_RESERVE_FACTOR_CHANGED = '\x2694ccb0b585b6a54b8d8b4a47aa874b05c257b43d34e98aee50838be00d3405'
TOPIC_ASSET_SOURCE_UPDATED   = '\x22c5b7b2d8561d39f7f210b6b326a1aa69f15311163082308ac4877db6339dc1'  -- ORACLE risk signal
TOPIC_FALLBACK_ORACLE_UPD    = '\xce7a780d33665b1ea097af5f155e3821b809ecbaa839d3b33aa83ba28168cefb'
TOPIC_PRICE_ORACLE_UPDATED   = '\xefe8ab924ca486283a79dc604baa67add51afb82af1db8ac386ebbba643cdffd'
TOPIC_UPGRADED               = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- Reward periphery (CIC / MFD) =====
TOPIC_CIC_BALANCE_UPDATED    = '\x526824944047da5b81071fb6349412005c5da81380b336103fbe5dd34556c776'
TOPIC_MFD_MINTED             = '\x30385c845b448a36257a6a1716e6ad2e1bc2cbe333cde1e69fe849ad6511adfe'
TOPIC_MFD_WITHDRAWN          = '\x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5'
TOPIC_MFD_STAKED             = '\x37d4053e34fde482e96f6bcd424dfa31342cbd5fe184d497fb3c8bb4b4b97580'
TOPIC_MFD_REWARD_PAID        = '\x540798df468d7b23d11f156fdb954cb19ad414d150722a7b6d55ba369dea792e'

-- ===== Selectors — LendingPool =====
SEL_DEPOSIT                  = '\xe8eda9df'   -- V2 supply (V3 = supply 0x617ba037)
SEL_WITHDRAW                 = '\x69328dec'
SEL_BORROW                   = '\xa415bcad'
SEL_REPAY                    = '\x573ade81'
SEL_SWAP_BORROW_RATE_MODE    = '\x94ba89a2'
SEL_LIQUIDATION_CALL         = '\x00a718a9'   -- ABSENT from impl bytecode; detect via event
SEL_FLASHLOAN                = '\xab9c4b5d'
SEL_SET_USE_RESERVE_AS_COLL  = '\x5a3b74b9'
SEL_FINALIZE_TRANSFER        = '\xd5ed3933'
SEL_GET_USER_ACCOUNT_DATA    = '\xbf92857c'
SEL_GET_RESERVE_DATA         = '\x35ea6a75'
SEL_SCALED_BALANCE_OF        = '\x1da24f3e'
SEL_GET_ASSET_PRICE          = '\xb3596f07'
SEL_HANDLE_ACTION            = '\x31873e2e'   -- CIC reward hook

-- ===== Addresses — Ethereum (chain ID 1) — UwU Lend =====
UWU_LENDING_POOL             = '\x2409af0251dcb89ee3dee572629291f9b087c668'
UWU_ADDRESSES_PROVIDER       = '\x011c0d38da64b431a1bdfc17ad72678eabf7f1fb'
UWU_CONFIGURATOR             = '\x408c9764993209dc772eb12ff641f4b55f5b005c'
UWU_PRICE_ORACLE             = '\xac4a2ac76d639e10f2c05a41274c1af85b772598'
UWU_LENDING_RATE_ORACLE      = '\x413a1f0098a8c5ba1078552af515bd0146522fe4'
UWU_FALLBACK_ORACLE          = '\x9bc6333081266e55d88942e277fc809b485698b9'
UWU_COLLATERAL_MANAGER       = '\x2e9f846ce3820531b52c08d3d4543be5c8fe7ddb'
UWU_WETH_GATEWAY             = '\xe08d97e151473a848c3d9ca3f323cb720472d015'
UWU_POOL_ADMIN_SAFE          = '\x0e1894d8642330ff917c04f57e2e88cd08ca465d'
UWU_EMERGENCY_ADMIN_SAFE     = '\x4415f30f264593fcc0f28b93a8735b3c02357768'
UWU_TEAM_MULTISIG            = '\xb8416eac2155e9636b5f728dd29810bf7e3bc20d'  -- provider owner / CIC owner
-- token / rewards
UWU_TOKEN                    = '\x55c08ca52497e2f1534b59e2917bf524d4765257'
UWU_CHEF_INCENTIVES          = '\xf8390b84533db97d3e415b4c7bf4251953d6c568'  -- active CIC
UWU_MULTIFEE_DISTRIBUTION    = '\x630de1180a22e76e70e041da5eb9b676ce2bdd44'  -- active MFD
UWU_SLP_UWU_WETH             = '\x3e04863dba602713bb5d0edbf7db7c3a9a2b6027'  -- SushiSwap UWU/WETH LP
UWU_LEGACY_CIC_1             = '\x21953192664867e19f85e96e1d1dd79dc31cccdb'
UWU_LEGACY_MFD_1             = '\x7c0bf1108935e7105e218bbb4f670e5942c5e237'  -- DefiLlama "PoolV1"
UWU_LEGACY_CIC_2             = '\xdb5c23ae97f76dacc907f5f13bda54131c8e9e5a'
UWU_LEGACY_MFD_2             = '\x0a7b2a21027f92243c5e5e777aa30bb7969b0188'  -- DefiLlama "PoolV2"
-- impls (read live; per-reserve token impls differ)
UWU_POOL_IMPL                = '\x05bfa9157e92690b179033ca2f6dd1e86b25ea4d'
UWU_CONFIGURATOR_IMPL        = '\x40daf7be3a99b898f54fb7968d16db5103835347'

EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## 9. Verification & sources

- **Event topic0 / function selectors:** every value recomputed locally as `keccak256(signature)` (no param names, `uint`→`uint256`, indexed irrelevant). Cross-checked against live `eth_getLogs` on the UwU LendingPool `0x2409aF02…` (Deposit/Withdraw/FlashLoan/LiquidationCall=30/ReserveDataUpdated all present in a 40k-block window), the uWETH token (uToken `Mint`/`Burn`), the Configurator (`CollateralConfigurationChanged`), the oracle (`AssetSourceUpdated`), the CIC (`BalanceUpdated`=120 logs), and the MFD (`Minted`/`Withdrawn`). The MFD `Minted(address,uint256)` topic0 was resolved against the openchain signature DB and re-confirmed by local keccak.
- **Function presence:** selectors scanned in the live LendingPool impl `0x05bfa915…25ea4d` bytecode (deposit/withdraw/borrow/repay/flashLoan/finalizeTransfer/swapBorrowRateMode/setUserUseReserveAsCollateral/getReserveData/getUserAccountData PRESENT; `liquidationCall` `0x00a718a9` ABSENT — §5.2).
- **Addresses:** walked on-chain from the live `LendingPoolAddressesProvider` `0x011c0d38…f7f1fb` (`getLendingPool`/`getLendingPoolConfigurator`/`getPriceOracle`/`getLendingRateOracle`/`getAddress("COLLATERAL_MANAGER")`); reserves enumerated via `LendingPool.getReservesList()` (19) and `getReserveData(asset)` for each uToken/stableDebt/variableDebt/strategy; symbols/decimals via `symbol()`/`decimals()`. CIC↔MFD wiring via uToken `getIncentivesController()` → CIC `0xf8390b84…`, CIC `.rewardMinter()` → MFD `0x630De118…`. Every address existence-checked via `eth_getCode`.
- **Proxies:** EIP-1967 impl slot `0x360894…382bbc` read live per contract; admin slot reads empty (immutable-admin proxy). CIC/MFD/UWU confirmed non-proxy (impl slot `0x0`).
- **Oracle units:** `getAssetPrice` returns 8-dec USD (WETH=$1689.18, DAI=$0.9995, etc.) — verified live; fallback oracle `0x9bC63330…698B9` from `getFallbackOracle()`.
- **Chain absence:** `eth_getCode` for LendingPool / AddressesProvider / oracle / UWU token / CIC / MFD on Base, BNB, Avalanche, Arbitrum, Optimism, Polygon RPCs — all `0x`.

Authoritative external sources:

- [`aave/protocol-v2`](https://github.com/aave/protocol-v2) — canonical V2 contracts UwU forks (LendingPool, LendingPoolConfigurator, aToken, debt tokens, AaveOracle, DefaultReserveInterestRateStrategy, WETHGateway).
- [`UwU-Lend/uwu-contracts`](https://github.com/UwU-Lend/uwu-contracts) — UwU's source (dirs: `aave-protocol-v2`, `fallback-oracle`, `price-getters`, `staking`, `misc`).
- [UwU Lend](https://uwulend.fi/) — official site.
- [UWU token on Etherscan](https://etherscan.io/token/0x55C08ca52497e2f1534B59E2917BF524D4765257) · [LendingPool on Etherscan](https://etherscan.io/address/0x2409aF0251DCB89EE3Dee572629291f9B087c668).
- [DefiLlama — UwU Lend](https://defillama.com/protocol/uwu-lend) (note: its "PoolV1/PoolV2" labels are the legacy MFD staking contracts, not lending pools).
- Exploit post-mortems (June 2024, ~$24M, sUSDe/USDe oracle manipulation): [Merkle Science](https://www.merklescience.com/blog/investigating-the-uwu-lend-hack-and-flow-of-funds), [QuillAudits](https://quillaudits.medium.com/decoding-uwu-lends-19-4-million-exploit-quillaudits-15a9c158166a), [Neptune Mutual](https://neptunemutual.medium.com/understanding-the-uwu-lend-exploit-b32ea552f030).
