# Moola Market — Topics, Selectors, Addresses (Celo only — absent on all 7 monitored chains)

**Status:** verified against Celo mainnet (chain ID 42220) RPC (live + historic `eth_getLogs`, `eth_getCode`, `eth_getStorageAt`, `eth_call`) and the canonical `moolamarket/moola` (V1) + `moolamarket/moola-v2` (V2) repos, on 2026-06-08. Non-obvious claims additionally fact-checked against primary sources (Moola docs, migration blog, CeloScan) — see the final section.
**Scope:** the monitoring pipeline targets **Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137)**. **Moola Market is deployed on Celo (42220) ONLY and exists on NONE of those seven chains** — every Moola address returns `0x` from `eth_getCode` on all seven (verified per address per chain; see §5). This file documents the real Celo deployment so the reference has value for cross-chain attribution, look-alike disambiguation, and Celo-aware tooling. Topics + selectors are chain-agnostic; addresses are Celo-network-specific.

Moola is an **Aave fork** with two distinct on-chain generations on Celo:

- **Moola V1** = an **Aave V1**-lineage market (the original "Moola genesis"-era contracts): funds live in a separate **`LendingPoolCore`**, the **`LendingPool`** is the logic entrypoint, a **`LendingPoolDataProvider`** serves reads, the supply event is **`Deposit`** and redemption is **`RedeemUnderlying`** (no `Withdraw`). V1 mTokens are named **mCUSD / mCELO / mCEUR** (capitalised). This generation carried the heavy 2020–2021 activity (verified: ~3.1k `Deposit` logs in a single 50k-block window).
- **Moola V2** = an **Aave V2**-lineage market (the migration target, launched ~Oct 2021): a **single `LendingPool`** (no `LendingPoolCore`), supply event **`Deposit`**, withdrawal event **`Withdraw`**, per-reserve **aTokens (mTokens) + variableDebtToken + stableDebtToken**, `getUserAccountData` denominated in **CELO/wei (1e18)** — not USD. V2 mTokens are **mCELO / mcUSD / mcEUR / mCREAL / mMOO**. **V2 is the live market** today (verified: `Deposit`/`Withdraw`/`Borrow`/`Repay`/`LiquidationCall`/`FlashLoan`/`ReserveDataUpdated` all firing in 2026 windows).

> **Which Aave era?** V2's topics and selectors are **byte-for-byte identical to Aave V2** (see [aave/v2.md](../aave/v2.md)); V1's are **byte-for-byte identical to Aave V1** (see [aave/v1.md](../aave/v1.md)). This was confirmed by recomputing keccak locally AND matching against live Moola logs. The one Celo-specific twist is the **price oracle**: Moola does not use a stock Aave Chainlink-aggregator oracle — it reads Celo's native price registry / `SortedOracles`, and quotes prices in **CELO** (base currency = CELO, `getAssetPrice(CELO) = 1e18`), not USD. Everything else is stock Aave.

> **Both generations are live contracts, but V1 is effectively wound down** (liquidity migrated to V2 in the Oct-2021 migration). For *current* monitoring, watch V2 (`0x970b…f670`). V1 (`0xc154…e535`) is kept here for historical backfill and to disambiguate the two `Deposit` topic0s (V1 `Deposit` carries a trailing `_timestamp` → different topic0 from V2 `Deposit`).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-08. V2 lending topics additionally confirmed against **live Moola V2 LendingPool / mToken logs** on Celo; V1 `Deposit` confirmed against **live Moola V1 LendingPool logs**.

### 1.1 V2 LendingPool (the live market) — emitter = `0x970b…f670`

| topic0 | Event |
|--------|-------|
| `0xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951` | `Deposit(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint16 indexed referral)` |
| `0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7` | `Withdraw(address indexed reserve, address indexed user, address indexed to, uint256 amount)` |
| `0xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b` | `Borrow(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint256 borrowRateMode, uint256 borrowRate, uint16 indexed referral)` |
| `0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa` | `Repay(address indexed reserve, address indexed user, address indexed repayer, uint256 amount)` |
| `0xea368a40e9570069bb8e6511d668293ad2e1f03b0d982431fd223de9f3b70ca6` | `Swap(address indexed reserve, address indexed user, uint256 rateMode)` (stable↔variable) |
| `0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286` | `LiquidationCall(address indexed collateralAsset, address indexed debtAsset, address indexed user, uint256 debtToCover, uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)` |
| `0x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac` | `FlashLoan(address indexed target, address indexed initiator, address indexed asset, uint256 amount, uint256 premium, uint16 referralCode)` |
| `0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a` | `ReserveDataUpdated(address indexed reserve, uint256 liquidityRate, uint256 stableBorrowRate, uint256 variableBorrowRate, uint256 liquidityIndex, uint256 variableBorrowIndex)` |
| `0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2` | `ReserveUsedAsCollateralEnabled(address indexed reserve, address indexed user)` |
| `0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd` | `ReserveUsedAsCollateralDisabled(address indexed reserve, address indexed user)` |
| `0x9f439ae0c81e41a04d3fdfe07aed54e6a179fb0db15be7702eb66fa8ef6f5300` | `RebalanceStableBorrowRate(address indexed reserve, address indexed user)` |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` |

`Deposit` is the V2 supply event (**different topic0 from V1**, below, and from Aave V3's `Supply`). `borrowRateMode`/`rateMode` = 1 (stable) or 2 (variable); stable rate is a real, used feature in the V2 lineage. `Withdraw`, `LiquidationCall`, `ReserveDataUpdated`, and the two collateral-flag events share topic0 with Aave V2/V3 — disambiguate by emitter address + chain.

### 1.2 V2 mToken (aToken) & debt tokens (per-reserve, scaled rebasing — Aave V2 mechanics)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address indexed from, uint256 value, uint256 index)` | **mToken (aToken)** |
| `0x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2` | `Burn(address indexed from, address indexed target, uint256 value, uint256 index)` | **mToken (aToken)** |
| `0x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee` | `Mint(address indexed from, address indexed onBehalfOf, uint256 value, uint256 index)` | **variableDebtToken** |
| `0x49995e5dd6158cf69ad3e9777c46755a1a826a446c6416992167462dad033b2a` | `Burn(address indexed user, uint256 amount, uint256 index)` | **variableDebtToken** |
| `0x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666` | `BalanceTransfer(address indexed from, address indexed to, uint256 value, uint256 index)` | mToken |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 (mToken; debt tokens emit on mint/burn) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | mToken (ERC-20) |
| `0xda919360433220e13b51e8c211e490d148e61a3bd53de8c097194e458b97f3e1` | `BorrowAllowanceDelegated(address indexed fromUser, address indexed toUser, address indexed asset, uint256 amount)` | debt token (credit delegation) |

> **V2 mToken vs debt-token `Mint`/`Burn` have DIFFERENT topic0s** (unlike Aave V3, where they share one). mToken `Mint` = `0x4c209b5f`, varDebt `Mint` = `0x2f00e3cd`. Match on `(topic0, emitting address)`. `value` is the actual amount; `index` is the reserve `liquidityIndex`/`variableBorrowIndex` (ray, 27-dec) so `scaled = value * 1e27 / index`. mToken `Mint`/`Burn`/`Transfer` confirmed live on mcUSD (`0x9181…DBc3`).

### 1.3 V1 LendingPool (legacy genesis market — all events carry a trailing `_timestamp`) — emitter = `0xc154…e535`

| topic0 | Event |
|--------|-------|
| `0xc12c57b1c73a2c3a2ea4613e9476abb3d8d146857aab7329e24243fb59710c82` | `Deposit(address indexed _reserve, address indexed _user, uint256 _amount, uint16 indexed _referral, uint256 _timestamp)` |
| `0x9c4ed599cd8555b9c1e8cd7643240d7d71eb76b792948c49fcb4d411f7b6b3c6` | `RedeemUnderlying(address indexed _reserve, address indexed _user, uint256 _amount, uint256 _timestamp)` (V1's "withdraw") |
| `0x1e77446728e5558aa1b7e81e0cdab9cc1b075ba893b740600c76a315c2caa553` | `Borrow(address indexed _reserve, address indexed _user, uint256 _amount, uint256 _borrowRateMode, uint256 _borrowRate, uint256 _originationFee, uint256 _borrowBalanceIncrease, uint16 indexed _referral, uint256 _timestamp)` |
| `0xb718f0b14f03d8c3adf35b15e3da52421b042ac879e5a689011a8b1e0036773d` | `Repay(address indexed _reserve, address indexed _user, address indexed _repayer, uint256 _amountMinusFees, uint256 _fees, uint256 _borrowBalanceIncrease, uint256 _timestamp)` |
| `0xb3e2773606abfd36b5bd91394b3a54d1398336c65005baf7bf7a05efeffaf75b` | `Swap(address indexed _reserve, address indexed _user, uint256 _newRateMode, uint256 _newRate, uint256 _borrowBalanceIncrease, uint256 _timestamp)` |
| `0x5b8f46461c1dd69fb968f1a003acee221ea3e19540e350233b612ddb43433b55` | `FlashLoan(address indexed _target, address indexed _reserve, uint256 _amount, uint256 _totalFee, uint256 _protocolFee, uint256 _timestamp)` |
| `0x56864757fd5b1fc9f38f5f3a981cd8ae512ce41b902cf73fc506ee369c6bc237` | `LiquidationCall(address indexed _collateral, address indexed _reserve, address indexed _user, uint256 _purchaseAmount, uint256 _liquidatedCollateralAmount, uint256 _accruedBorrowInterest, address _liquidator, bool _receiveAToken, uint256 _timestamp)` |
| `0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2` | `ReserveUsedAsCollateralEnabled(address indexed _reserve, address indexed _user)` (same topic0 as V2) |
| `0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd` | `ReserveUsedAsCollateralDisabled(address indexed _reserve, address indexed _user)` (same topic0 as V2) |

> **V1 `Deposit` (`0xc12c57b1…`) ≠ V2 `Deposit` (`0xde685721…`).** The V1 events all carry `_timestamp` and use Aave-V1 signatures, so every V1 topic0 (except the two collateral flags) differs from V2. There is **no `Withdraw`** in V1 — redemptions emit **`RedeemUnderlying`**. Confirmed live: V1 `Deposit` fired thousands of times in 2020–2021 windows.

### 1.4 Proxy upgrade signal (both generations)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | Standard EIP-1967. Emitted by each upgradeable proxy (LendingPool, LendingPoolConfigurator, mTokens, debt tokens) when its implementation is swapped. **No `Upgraded` log seen on the V2 LendingPool proxy in the sampled 2021–2026 windows** — the impl is stable; treat any future `Upgraded` from a Moola proxy as a high-signal admin event. |

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

### 2.1 V2 LendingPool — state-changing (Aave-V2 identical)

All verified **present** in the live V2 LendingPool implementation bytecode (`0xbecd348aa5cc976be8e82ca6f13bc3b53197711f`) on 2026-06-08 **except `liquidationCall`** (see §8 / §9).

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe8eda9df` | `deposit(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)` | Emits `Deposit`. (Aave V3 renamed this `supply` `0x617ba037` — not present here.) |
| `0x69328dec` | `withdraw(address asset, uint256 amount, address to)` → `uint256` | `amount = type(uint256).max` = full balance. |
| `0xa415bcad` | `borrow(address asset, uint256 amount, uint256 interestRateMode, uint16 referralCode, address onBehalfOf)` | Mode 1=stable, 2=variable. |
| `0x573ade81` | `repay(address asset, uint256 amount, uint256 rateMode, address onBehalfOf)` → `uint256` | |
| `0x94ba89a2` | `swapBorrowRateMode(address asset, uint256 rateMode)` | Stable↔variable. |
| `0xcd112382` | `rebalanceStableBorrowRate(address asset, address user)` | |
| `0x5a3b74b9` | `setUserUseReserveAsCollateral(address asset, bool useAsCollateral)` | |
| `0x00a718a9` | `liquidationCall(address collateralAsset, address debtAsset, address user, uint256 debtToCover, bool receiveAToken)` | Emits `LiquidationCall`. **NOT in the LendingPool impl dispatcher — detect via the event (§9).** |
| `0xab9c4b5d` | `flashLoan(address receiverAddress, address[] assets, uint256[] amounts, uint256[] modes, address onBehalfOf, bytes params, uint16 referralCode)` | Multi-asset. |

### 2.2 V2 LendingPool — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xbf92857c` | `getUserAccountData(address user)` | `(totalCollateralETH, totalDebtETH, availableBorrowsETH, currentLiquidationThreshold, ltv, healthFactor)` — **values in CELO/wei (1e18), NOT USD.** HF in 1e18 (`< 1e18` = liquidatable). The `…ETH` field names are inherited Aave-V2 naming; on Celo the base unit is **CELO**. |
| `0x35ea6a75` | `getReserveData(address asset)` | Full V2 `ReserveData` struct (config, indices, rates, mToken/stable/variable token addrs, strategy, id). |
| `0xd15e0053` | `getReserveNormalizedIncome(address asset)` | `uint256` ray — supply index. |
| `0x386497fd` | `getReserveNormalizedVariableDebt(address asset)` | `uint256` ray — borrow index. |
| `0xd1946dbc` | `getReservesList()` | `address[]` — 5 reserves (CELO, cUSD, cEUR, cREAL, MOO). |
| `0xc44b11f7` | `getConfiguration(address asset)` | Packed reserve config bitmap. |
| `0x4417a583` | `getUserConfiguration(address user)` | Packed user collateral/borrow bitmap. |

### 2.3 LendingPoolAddressesProvider — registry getters (resolve everything from here)

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x0261bf8b` | `getLendingPool()` → `address` | → V2 `0x970b…f670` / V1 `0xc154…e535`. |
| `0x85c858b1` | `getLendingPoolConfigurator()` → `address` | |
| `0xfca513a8` | `getPriceOracle()` → `address` | → V2 `0xba22…4d29` / V1 `0x5685…98D0`. |
| `0x3618abba` | `getLendingRateOracle()` → `address` | |
| `0x712d9171` | `getLendingPoolCollateralManager()` → `address` | V2 → `0xa2db…3b32` (liquidation delegatecall target). |
| `0xaecda378` | `getPoolAdmin()` → `address` | V2 → `0x313b…3e5c`. |
| `0xddcaa9ea` | `getEmergencyAdmin()` → `address` | V2 → `0x643c…2624`. |
| `0x568ef470` | `getMarketId()` → `string` | V2 returns **"Moola genesis market"**. |
| `0x21f8a721` | `getAddress(bytes32 id)` → `address` | Generic registry lookup. |
| `0xed6ff760` | `getLendingPoolCore()` → `address` | **V1 only** → `0xaf10…8F73` (the fund-holding core). Reverts/absent on V2. |
| `0x2f58b80d` | `getLendingPoolDataProvider()` → `address` | **V1 only** → `0xb1f1…20E5`. |

### 2.4 mToken / debt token / oracle

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x1da24f3e` | `scaledBalanceOf(address user)` | mToken / debt — **use for accounting** (`balanceOf` rebases every block). |
| `0xb1bf962d` | `scaledTotalSupply()` | mToken / debt. |
| `0xb16a19de` | `UNDERLYING_ASSET_ADDRESS()` → `address` | mToken / debt. |
| `0xc04a8a10` | `approveDelegation(address delegatee, uint256 amount)` | debt token — credit delegation. |
| `0x70a08231` / `0x18160ddd` | `balanceOf` / `totalSupply` | **Rebasing** — changes every block. |
| `0xb3596f07` | `getAssetPrice(address asset)` → `uint256` | PriceOracle — quoted in **CELO/wei** (`getAssetPrice(CELO) = 1e18`, not USD). |

### 2.5 V1 LendingPool — state-changing (Aave-V1 identical, ETH sentinel replaced by native-CELO handling)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd2d0e066` | `deposit(address _reserve, uint256 _amount, uint16 _referralCode)` | Emits V1 `Deposit`. |
| `0xc858f5f9` | `borrow(address _reserve, uint256 _amount, uint256 _interestRateMode, uint16 _referralCode)` | Mode 1=stable, 2=variable. |
| `0x5ceae9c4` | `repay(address _reserve, uint256 _amount, address _onBehalfOf)` | |
| `0x9895e3d8` | `redeemUnderlying(address _reserve, address _user, uint256 _amount, uint256 _aTokenBalanceAfterRedeem)` | Called by the mToken on redeem; emits `RedeemUnderlying`. |
| `0x48ca1300` | `swapBorrowRateMode(address _reserve)` | |
| `0x00a718a9` | `liquidationCall(address _collateral, address _reserve, address _user, uint256 _purchaseAmount, bool _receiveAToken)` | **Same 4-byte selector as V2/Aave** — disambiguate by Pool address. |
| `0x5cffe9de` | `flashLoan(address _receiver, address _reserve, uint256 _amount, bytes _params)` | Single-asset (V1 shape). |

---

## 3. Addresses — Celo mainnet (chain ID 42220) — Moola V2 (the live market)

Source: `moolamarket/moola-v2` deploy artifacts, then **every address re-resolved on-chain from the AddressesProvider** and existence-checked via `eth_getCode` on `https://celo-rpc.publicnode.com` (fallback `https://forno.celo.org`). Wiring confirmed: `Provider.getLendingPool()` → Pool; `Provider.getMarketId()` = **"Moola genesis market"**; `Pool.getReservesList()` = the 5 reserves below; each reserve's mToken/debt tokens read from `Pool.getReserveData(asset)`.

### 3.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| **LendingPool** (proxy) | `0x970b12522CA9b4054807a2c5B736149a5BE6f670` | Main lending entrypoint; emits all §1.1 events. |
| **LendingPoolAddressesProvider** | `0xD1088091A174d33412a968Fa34Cb67131188B332` | Per-market registry / source-of-truth (plain ownable, **not** a proxy). |
| **LendingPoolConfigurator** (proxy) | `0x928F63a83217e427A84504950206834CBDa4Aa65` | Risk-admin; reserve init / freeze / cap changes. |
| **LendingPoolCollateralManager** | `0xa2dB2e70A795b566f129ae7Dff242a4Ad1393b32` | `delegatecall` target for `liquidationCall` (not a proxy). |
| **PriceOracle** (Moola oracle) | `0xba2224905ad3cdba6c1b764cd62fda52bd524d29` | Celo-native price source; **quotes in CELO (1e18)**, not a stock Aave Chainlink aggregator. Reverts on `ADDRESSES_PROVIDER()`. |
| **LendingRateOracle** | `0xaA6e0F0B63287EAC5DDBEefd1f133Fc7F554ee9b` | Stable-rate reference oracle. |
| **AaveProtocolDataProvider** | `0x43d067ed784D9DD2ffEda73775e2CC4c560103A1` | Read helper (`getAllReservesTokens`, per-reserve data). `ADDRESSES_PROVIDER()` → `0xD108…B332`. |
| Reserve-factor collector (`OwnedWallet`) | `0x313bc86D3D6e86ba164B2B451cB0D9CfA7943e5c` | Fee sink **and** `getPoolAdmin()`/`owner()` of the provider (governance multisig executor). |
| Emergency admin | `0x643C574128c7C56A1835e021Ad0EcC2592E72624` | `getEmergencyAdmin()` — pause guardian. |
| Governance multisig (4-of-10) | `0xd7f77169d5E6a32C5044052F9a49eb94697b25ED` | On-chain owner of upgrade/risk powers (per Moola governance docs). |

### 3.2 Reserves (5) — underlying → mToken / variableDebtToken / stableDebtToken

mToken/debt tokens read live from `LendingPool.getReserveData(asset)`. All `eth_getCode`-verified present; mTokens are EIP-1967 proxies (impl per §8). `cUSD` reports ERC-20 `symbol()="USDm"`, `cEUR`→`"EURm"`, `cREAL`→`"BRLm"` (Celo Mento stable naming) — the *mTokens* report `mcUSD`/`mCEUR`/`mCREAL`.

| Symbol | Underlying | mToken (aToken) | variableDebtToken | stableDebtToken |
|--------|-----------|-----------------|-------------------|-----------------|
| CELO | `0x471EcE3750Da237f93B8E339c536989b8978a438` | `0x7D00cd74FF385c955EA3d79e47BF06bD7386387D` (mCELO) | `0xaf451d23d6f0FA680113Ce2d27a891aA3587f0c3` | `0x02661DD90C6243Fe5cDF88de3e8cB74bcc3bD25e` |
| cUSD | `0x765DE816845861e75A25fCA122bb6898B8B1282a` | `0x918146359264C492BD6934071c6Bd31C854EDBc3` (mcUSD) | `0xF602D9617564C07f1e128687798d8C699cED3961` | `0xA9f50d9F7C03e8b48b2415218008822EA3334AdB` |
| cEUR | `0xD8763CBa276a3738E6de85b4b3bF5FDed6D6cA73` | `0xE273Ad7ee11dCfAA87383aD5977EE1504aC07568` (mCEUR) | `0xFB6c830C13d8322B31B282EF1Fe85cBb669D9aE8` | `0x612599d8421f36b7Da4dDbA201A3854Ff55e3d03` |
| cREAL | `0xe8537a3d056dA446677B9e9d6c5dB704EAaB4787` | `0x9802d866fdE4563d088a6619F7CeF82C0B991A55` (mCREAL) | `0xBd408042909351b649dc50353532deeF6De9faA9` | `0x0d00d9A02b85e9274F60a082609F44f7C57f373D` |
| MOO | `0x17700282592D6917F6A73D0bF8AcCf4D578c131e` | `0x3A5024e3AAB31A1d3184127B52b0E4b4e9adcc34` (mMOO) | `0x3D6D8a1562Ff973aD89887c0A5C001f42ad66Cb8` | `0x0Bb14e95A4ff117f7f536d605e2b506e937619C4` |

### 3.3 Implementations (V2)

| Role | Live implementation (read via EIP-1967 slot 2026-06-08) |
|------|--------------------------------------------------------|
| LendingPool impl | `0xbecd348aA5Cc976bE8E82Ca6f13Bc3b53197711F` |
| LendingPoolConfigurator impl | `0x2cca742585B39e0538f7Cc01ab8FfA005f1B1f1c` |
| mCELO mToken impl | `0xf44E15badbC9a2c5D71A569d6DfB584A8cc97a2a` |

---

## 4. Addresses — Celo mainnet (chain ID 42220) — Moola V1 (legacy genesis market)

The original Aave-V1-lineage deployment (funds in `LendingPoolCore`). All `eth_getCode`-verified present; wiring confirmed from the V1 provider (`getLendingPool/Core/PriceOracle`). **V1 liquidity was migrated to V2 in Oct 2021** — keep for historical backfill and to distinguish the V1 `Deposit` topic0. V1 mToken `symbol()` is capitalised **mCUSD / mCELO / mCEUR**.

| Role | Address | One-liner |
|------|---------|-----------|
| **LendingPool** (proxy) | `0xc1548F5AA1D76CDcAB7385FA6B5cEA70f941e535` | V1 logic entrypoint; emits all §1.3 events. |
| **LendingPoolCore** | `0xAF106F8D4756490E7069027315F4886cc94A8F73` | **Holds all V1 deposited funds** + reserve state (V1-specific; no V2 analogue). |
| **LendingPoolAddressesProvider** | `0x7AAaD5a5fa74Aec83b74C2a098FBC86E17Ce4aEA` | V1 registry / source of truth. |
| **LendingPoolDataProvider** | `0xB1f1904b339BA1CdA1Ac3E866f497F55a52320E5` | V1 read helper. |
| **PriceOracle** (V1) | `0x568547688121AA69bDEB8aEB662C321c5D7B98D0` | V1 Celo price source (distinct from the V2 oracle). |
| mCELO (V1 mToken) | `0x7037F7296B2fc7908de7b57a89efaa8319f0C500` | `symbol()="mCELO"`. |
| mCUSD (V1 mToken) | `0x64dEFa3544c695db8c535D289d843a189aa26b98` | `symbol()="mCUSD"`. |
| mCEUR (V1 mToken) | `0xa8d0E6799FF3Fd19c6459bf02689aE09c4d78Ba7` | V1 cEUR mToken. |
| LendingPool impl (V1) | `0x3c95Be77b6Ea2E8d6dA19c70305b559D1a9e42Ef` | Read via EIP-1967 slot. |

> Underlying CELO/cUSD/cEUR tokens are **shared with V2** (same `0x471E…`, `0x765D…`, `0xD876…`). Only the mTokens, core, pool, provider, and oracle differ between V1 and V2.

---

## 5. Cross-chain presence — Moola is Celo-only

`eth_getCode` was run for **every** Moola V1+V2 contract (LendingPool, AddressesProvider, Configurator, PriceOracle, DataProvider, every mToken) on **each of the seven monitored chains**. **Every call returned `0x` (no code) on all seven.** Moola has no deployment, no proxy, no look-alike on any of them.

| Chain | ID | RPC | Moola LendingPool? | Any Moola contract? |
|---|---|---|---|---|
| **Celo** | 42220 | celo-rpc.publicnode.com | ✅ V2 `0x970b…f670` (+ V1 `0xc154…e535`) | ✅ full V1 + V2 fleet |
| Ethereum | 1 | ethereum-rpc.publicnode.com | ❌ `0x` | ❌ none |
| Base | 8453 | base-rpc.publicnode.com | ❌ `0x` | ❌ none |
| BNB | 56 | bsc-rpc.publicnode.com | ❌ `0x` | ❌ none |
| Avalanche | 43114 | avalanche-c-chain-rpc.publicnode.com | ❌ `0x` | ❌ none |
| Arbitrum One | 42161 | arbitrum-one-rpc.publicnode.com | ❌ `0x` | ❌ none |
| Optimism | 10 | optimism-rpc.publicnode.com | ❌ `0x` | ❌ none |
| Polygon PoS | 137 | polygon-bor-rpc.publicnode.com | ❌ `0x` | ❌ none |

**Bottom line:** Moola Market is a **Celo-only Aave fork**. If any of the seven monitored chains needs Aave-fork lending coverage, Moola is **not** the protocol — it never deployed there. Use the Celo RPC (chain 42220) for any Moola monitoring.

---

## 6. Decimals & math (same as Aave V2)

- Indices `liquidityIndex`/`variableBorrowIndex` are **rays (27-dec)**: `actual = scaled * index / 1e27`.
- `getUserAccountData` collateral/debt/borrows in **CELO/wei (1e18)** (base currency = CELO, not USD); `healthFactor` in **1e18** (`< 1e18` = liquidatable; `type(uint256).max` = no debt).
- Oracle (`getAssetPrice`) returns price **in CELO/wei (1e18)** — `getAssetPrice(CELO)=1e18`. Mento stables cUSD/cEUR/cREAL are 18-dec; CELO and MOO are 18-dec — **all five Moola reserves are 18-decimal**, so there is no 6-dec USDC/USDT decimals trap here.
- Flash-loan premium follows the Aave V2 default (0.09%); the `FlashLoan` event carries `premium`.

---

## 7. Cross-generation summary

| Property | Moola V1 (Aave-V1 lineage) | Moola V2 (Aave-V2 lineage) |
|---|---|---|
| LendingPool | `0xc154…e535` | `0x970b…f670` (live) |
| Funds held in | `LendingPoolCore` `0xaf10…8F73` | the LendingPool itself (no core) |
| Supply event | `Deposit` `0xc12c57b1…` (+`_timestamp`) | `Deposit` `0xde685721…` |
| Withdraw event | **`RedeemUnderlying`** `0x9c4ed599…` | `Withdraw` `0x3115d144…` |
| mToken naming | mCELO / mCUSD / mCEUR | mCELO / mcUSD / mCEUR / mCREAL / mMOO |
| AddressesProvider | `0x7AAa…4aEA` | `0xD108…B332` |
| PriceOracle | `0x5685…98D0` | `0xba22…4d29` |
| Reserves | CELO, cUSD, cEUR (genesis) | CELO, cUSD, cEUR, cREAL, MOO (5) |
| Status | wound down (migrated 2021) | **operational** |

**Three things to internalize:**
1. **Live Moola = V2 LendingPool `0x970b…f670` on Celo.** Watch its §1.1 + §1.2 topics.
2. **Two `Deposit` topic0s.** V1 `0xc12c57b1…` (has `_timestamp`) vs V2 `0xde685721…`. Don't conflate.
3. **Oracle quotes in CELO, not USD**, and account data is CELO-denominated — the inherited `…ETH` field names are misleading.

---

## 8. Proxies

Every Moola core/token contract is an **upgradeable proxy** of Aave's `InitializableImmutableAdminUpgradeabilityProxy` type (EIP-1967 impl slot, admin baked in as **immutable** at construction → the EIP-1967 admin slot reads `0x0`). The `LendingPoolAddressesProvider` is **not** a proxy (plain ownable registry — its EIP-1967 impl slot reads `0x0`); the `LendingPoolCollateralManager` and `PriceOracle` are **not** proxies (logic / pointer contracts). All verified by live slot reads on 2026-06-08.

EIP-1967 implementation slot: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`. Admin slot: `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`.

| Contract | Pattern | Detection (live read) | Upgrade authority |
|----------|---------|-----------------------|-------------------|
| V2 LendingPool `0x970b…f670` | EIP-1967 (immutable-admin) | impl slot → `0xbecd…711F`; admin slot → `0x0` | `AddressesProvider.setLendingPoolImpl()` (PoolAdmin / gov multisig) |
| V2 Configurator `0x928f…aa65` | EIP-1967 (immutable-admin) | impl slot → `0x2cca…1f1c`; admin slot → `0x0` | `AddressesProvider.setLendingPoolConfiguratorImpl()` |
| V2 mTokens / debt tokens | EIP-1967 (admin = Configurator) | impl slot non-zero (e.g. mCELO → `0xf44e…7a2a`); admin slot → `0x0` | `LendingPoolConfigurator.updateAToken()` / `updateVariableDebtToken()` |
| V1 LendingPool `0xc154…e535` | EIP-1967 (immutable-admin) | impl slot → `0x3c95…42ef` | V1 provider |
| **LendingPoolAddressesProvider** (V1 & V2) | plain ownable registry | impl slot → `0x0` | `owner()` (gov multisig) |
| **LendingPoolCollateralManager** `0xa2db…3b32` | not a proxy | impl slot → `0x0` | swapped via provider |
| **PriceOracle** (V1 & V2) | not a proxy | impl slot → `0x0` | replaced via `setPriceOracle()` |

The `Upgraded(address)` topic0 to watch on any proxy: `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. **Read the live EIP-1967 slot before relying on any impl address** — never hard-code an impl.

---

## 9. Detection invariants & gotchas

1. **Moola is Celo-only (chain 42220).** It is absent (`eth_getCode = 0x`) on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, and Polygon — all seven monitored chains (§5). Any "Moola on L2/mainnet" claim is wrong. Monitor via the Celo RPC.
2. **It's an Aave fork, two generations.** V2 (live) = Aave V2 topics/selectors; V1 (legacy) = Aave V1 topics/selectors. Reuse [aave/v2.md](../aave/v2.md) and [aave/v1.md](../aave/v1.md) decoders respectively, keyed on the Moola Pool addresses.
3. **Live market = V2 `0x970b…f670`.** `Deposit`/`Withdraw`/`Borrow`/`Repay`/`LiquidationCall`/`FlashLoan`/`ReserveDataUpdated` all confirmed firing in 2026 windows.
4. **Two distinct `Deposit` topic0s.** V1 `0xc12c57b1…` (Aave-V1, `_timestamp`) vs V2 `0xde685721…` (Aave-V2). V1 also has **no `Withdraw`** — it emits `RedeemUnderlying` (`0x9c4ed599…`).
5. **Detect liquidations by the `LiquidationCall` event, not the selector.** On the V2 LendingPool impl, selector `0x00a718a9` (`liquidationCall`) is **absent from the dispatcher bytecode** (verified by PUSH4 scan) — liquidations route through the `LendingPoolCollateralManager` (`0xa2db…3b32`) via `delegatecall`, so the Pool emits `LiquidationCall` (`0xe413a321…`, verified live) but does not expose the selector at top level. Same dispatcher anomaly as upstream Aave V2.
6. **mToken vs debt-token `Mint`/`Burn` have DIFFERENT topic0s** (Aave-V2 behaviour). mToken `Mint`=`0x4c209b5f`, varDebt `Mint`=`0x2f00e3cd`. Match on `(topic0, emitting address)`.
7. **mTokens rebase every block.** Store `scaledBalanceOf` + reconstruct with the reserve `liquidityIndex` (ray). Same for debt with `variableBorrowIndex`.
8. **`onBehalfOf`/`user` ≠ `tx.from`.** Attribute positions to the event's `onBehalfOf`/`user`, not the sender (gateways, credit delegation, relayers, liquidation bots).
9. **Oracle and account data are CELO-denominated, not USD.** `getUserAccountData` returns CELO/wei; `getAssetPrice` returns CELO/wei (`getAssetPrice(CELO)=1e18`). The inherited `…ETH` field names are Aave-V2 leftovers. The oracle is a **Celo-native price source** (reads Celo `SortedOracles`/registry), not a stock Aave Chainlink aggregator — don't assume a Chainlink feed behind `getSourceOfAsset`.
10. **Five reserves, all 18-decimal:** CELO, cUSD (`symbol()="USDm"`), cEUR (`"EURm"`), cREAL (`"BRLm"`), and the **MOO governance token** itself (a listed reserve). No 6-dec stablecoin → no decimals trap, but note MOO is a thin/volatile collateral.
11. **The reserve-factor collector `0x313b…3e5c` is also the PoolAdmin/provider owner** — admin actions (reserve config, cap/freeze changes, impl swaps) originate from there; the emergency admin `0x643c…2624` can pause.
12. **V1 and V2 share underlying token addresses** but have separate mTokens, pools, providers, oracles. Key Moola state on `(generation, contract address)`, never on the underlying alone.
13. **MarketId = "Moola genesis market"** (`AddressesProvider.getMarketId()`) — useful to distinguish Moola's provider from any other Aave-fork provider when crawling Celo.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== V2 topics (live market; identical to Aave V2) =====
TOPIC_V2_DEPOSIT             = '\xde6857219544bb5b7746f48ed30be6386fefc61b2f864cacf559893bf50fd951'
TOPIC_V2_WITHDRAW            = '\x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'
TOPIC_V2_BORROW             = '\xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b'
TOPIC_V2_REPAY              = '\x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa'
TOPIC_V2_SWAP_RATE          = '\xea368a40e9570069bb8e6511d668293ad2e1f03b0d982431fd223de9f3b70ca6'
TOPIC_V2_LIQUIDATIONCALL    = '\xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
TOPIC_V2_FLASHLOAN          = '\x631042c832b07452973831137f2d73e395028b44b250dedc5abb0ee766e168ac'
TOPIC_V2_RESERVE_DATA_UPD   = '\x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a'
TOPIC_COLLATERAL_ENABLED    = '\x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2'  -- shared V1/V2
TOPIC_COLLATERAL_DISABLED   = '\x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd'  -- shared V1/V2
TOPIC_PAUSED                = '\x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752'
TOPIC_UNPAUSED              = '\xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933'
-- mToken / debt tokens (V2-specific signatures)
TOPIC_MTOKEN_MINT           = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'  -- Mint(address,uint256,uint256)
TOPIC_MTOKEN_BURN           = '\x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2'
TOPIC_VDEBT_MINT            = '\x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee'  -- Mint(address,address,uint256,uint256)
TOPIC_VDEBT_BURN            = '\x49995e5dd6158cf69ad3e9777c46755a1a826a446c6416992167462dad033b2a'
TOPIC_BALANCE_TRANSFER      = '\x4beccb90f994c31aced7a23b5611020728a23d8ec5cddd1a3e9d97b96fda8666'
TOPIC_ERC20_TRANSFER        = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_UPGRADED              = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== V1 topics (legacy genesis market; Aave V1, all carry _timestamp) =====
TOPIC_V1_DEPOSIT            = '\xc12c57b1c73a2c3a2ea4613e9476abb3d8d146857aab7329e24243fb59710c82'
TOPIC_V1_REDEEM_UNDERLYING  = '\x9c4ed599cd8555b9c1e8cd7643240d7d71eb76b792948c49fcb4d411f7b6b3c6'
TOPIC_V1_BORROW            = '\x1e77446728e5558aa1b7e81e0cdab9cc1b075ba893b740600c76a315c2caa553'
TOPIC_V1_REPAY             = '\xb718f0b14f03d8c3adf35b15e3da52421b042ac879e5a689011a8b1e0036773d'
TOPIC_V1_SWAP              = '\xb3e2773606abfd36b5bd91394b3a54d1398336c65005baf7bf7a05efeffaf75b'
TOPIC_V1_FLASHLOAN         = '\x5b8f46461c1dd69fb968f1a003acee221ea3e19540e350233b612ddb43433b55'
TOPIC_V1_LIQUIDATIONCALL    = '\x56864757fd5b1fc9f38f5f3a981cd8ae512ce41b902cf73fc506ee369c6bc237'

-- ===== Selectors — LendingPool (V2 = Aave V2) =====
SEL_V2_DEPOSIT             = '\xe8eda9df'
SEL_V2_WITHDRAW            = '\x69328dec'
SEL_V2_BORROW             = '\xa415bcad'
SEL_V2_REPAY              = '\x573ade81'
SEL_V2_SWAP_BORROW_RATE   = '\x94ba89a2'
SEL_LIQUIDATION_CALL      = '\x00a718a9'   -- ABSENT from V2 LendingPool dispatcher; detect via event
SEL_V2_FLASHLOAN          = '\xab9c4b5d'
SEL_SET_USE_AS_COLLATERAL = '\x5a3b74b9'
SEL_GET_USER_ACCT_DATA    = '\xbf92857c'   -- returns CELO/wei, not USD
SEL_GET_RESERVE_DATA      = '\x35ea6a75'
SEL_GET_RESERVES_LIST     = '\xd1946dbc'
SEL_SCALED_BALANCE_OF     = '\x1da24f3e'
SEL_GET_ASSET_PRICE       = '\xb3596f07'   -- price in CELO/wei
-- Selectors — V1 LendingPool (Aave V1)
SEL_V1_DEPOSIT            = '\xd2d0e066'
SEL_V1_BORROW            = '\xc858f5f9'
SEL_V1_REPAY             = '\x5ceae9c4'
SEL_V1_REDEEM_UNDERLYING  = '\x9895e3d8'
SEL_V1_FLASHLOAN         = '\x5cffe9de'

-- ===== Addresses — Celo (chain ID 42220) — V2 (live) =====
CELO_V2_LENDING_POOL      = '\x970b12522ca9b4054807a2c5b736149a5be6f670'
CELO_V2_ADDRESSES_PROVIDER = '\xd1088091a174d33412a968fa34cb67131188b332'
CELO_V2_CONFIGURATOR      = '\x928f63a83217e427a84504950206834cbda4aa65'
CELO_V2_COLLATERAL_MANAGER = '\xa2db2e70a795b566f129ae7dff242a4ad1393b32'
CELO_V2_PRICE_ORACLE      = '\xba2224905ad3cdba6c1b764cd62fda52bd524d29'
CELO_V2_LENDING_RATE_ORACLE = '\xaa6e0f0b63287eac5ddbeefd1f133fc7f554ee9b'
CELO_V2_DATA_PROVIDER     = '\x43d067ed784d9dd2ffeda73775e2cc4c560103a1'
CELO_V2_MCELO             = '\x7d00cd74ff385c955ea3d79e47bf06bd7386387d'
CELO_V2_MCUSD             = '\x918146359264c492bd6934071c6bd31c854edbc3'
CELO_V2_MCEUR             = '\xe273ad7ee11dcfaa87383ad5977ee1504ac07568'
CELO_V2_MCREAL            = '\x9802d866fde4563d088a6619f7cef82c0b991a55'
CELO_V2_MMOO              = '\x3a5024e3aab31a1d3184127b52b0e4b4e9adcc34'

-- ===== Addresses — Celo (chain ID 42220) — V1 (legacy) =====
CELO_V1_LENDING_POOL      = '\xc1548f5aa1d76cdcab7385fa6b5cea70f941e535'
CELO_V1_LENDING_POOL_CORE  = '\xaf106f8d4756490e7069027315f4886cc94a8f73'
CELO_V1_ADDRESSES_PROVIDER = '\x7aaad5a5fa74aec83b74c2a098fbc86e17ce4aea'
CELO_V1_DATA_PROVIDER     = '\xb1f1904b339ba1cda1ac3e866f497f55a52320e5'
CELO_V1_PRICE_ORACLE      = '\x568547688121aa69bdeb8aeb662c321c5d7b98d0'

-- ===== Underlyings (shared V1/V2; chain ID 42220) =====
CELO_TOKEN                = '\x471ece3750da237f93b8e339c536989b8978a438'
CELO_CUSD                 = '\x765de816845861e75a25fca122bb6898b8b1282a'
CELO_CEUR                 = '\xd8763cba276a3738e6de85b4b3bf5fded6d6ca73'
CELO_CREAL                = '\xe8537a3d056da446677b9e9d6c5db704eaab4787'
CELO_MOO                  = '\x17700282592d6917f6a73d0bf8accf4d578c131e'

EIP1967_IMPL_SLOT         = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT        = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
```

---

## 11. Verification & sources

- **Event topic0:** recomputed locally as `keccak256(signature)` for every event. **V2** topics verified against live `eth_getLogs` on the Moola V2 LendingPool `0x970b…f670` (Celo): `Deposit` (74 in a recent 50k-block window), `Withdraw` (100), `Borrow` (2–3 per window), `Repay`, `LiquidationCall` (2 in one window), `FlashLoan` (1), `ReserveDataUpdated` (175), `ReserveUsedAsCollateralEnabled` (203). mToken `Mint`/`Burn`/`Transfer` verified on mcUSD `0x9181…DBc3`. **V1** `Deposit` (`0xc12c57b1…`) verified on the V1 LendingPool `0xc154…e535` (979 / 3 159 / 2 548 logs across 2020–2021 windows). The V1 `Deposit` topic returns **0** logs on the V2 Pool — confirming the two generations are distinct.
- **Function selectors:** `keccak256(sig)[0:4]`. The V2 set was scanned against the live LendingPool implementation bytecode `0xbecd…711F` — `deposit`/`withdraw`/`borrow`/`repay`/`flashLoan`/`swapBorrowRateMode`/`setUserUseReserveAsCollateral`/views all **present**; `liquidationCall` (`0x00a718a9`) **absent** (routed via the CollateralManager — §9.5).
- **Addresses:** parsed from `moolamarket/moola` (V1) and `moolamarket/moola-v2` (V2) deploy artifacts, then **re-resolved on-chain from each generation's AddressesProvider** (`getLendingPool`/`getLendingPoolConfigurator`/`getPriceOracle`/`getLendingPoolCore`/`getMarketId`) and per-reserve via `LendingPool.getReserveData`. Every address existence-checked via `eth_getCode` on Celo. mToken/underlying `symbol()` read via `eth_call`. The V2 PriceOracle resolved from the provider (`0xba22…4d29`) differs from the V1 oracle (`0x5685…98D0`) — confirmed both have code and belong to their respective generations.
- **Proxy classification:** EIP-1967 impl + admin slots read live via `eth_getStorageAt` for LendingPool (V1 & V2), Configurator, mCELO, CollateralManager, AddressesProvider, PriceOracle. Proxies show a non-zero impl slot and a **`0x0` admin slot** (immutable-admin Aave proxy); the AddressesProvider, CollateralManager, and PriceOracle show a `0x0` impl slot (not proxies).
- **Chain absence:** `eth_getCode` run for every Moola V1+V2 contract on Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137) — **all returned `0x`** (§5). Celo chainId confirmed `0xa4ec` (42220) via `eth_chainId`.

Authoritative sources:

- [`moolamarket/moola`](https://github.com/moolamarket/moola) — V1 (Aave-V1-fork) contracts + Celo deploy log.
- [`moolamarket/moola-v2`](https://github.com/moolamarket/moola-v2) — V2 (Aave-V2-fork) contracts + `deploy-celo.log`.
- [`aave/protocol-v2`](https://github.com/aave/protocol-v2) / [`aave/aave-protocol`](https://github.com/aave/aave-protocol) — upstream V2 / V1 contracts (the topic/selector source).
- [Moola docs](https://docs.moola.market) and the [v1→v2 migration write-up](https://moolamarket.medium.com/moola-migration-from-v1-to-v2-96268238399e).
- Explorer: [CeloScan — V2 LendingPool](https://celoscan.io/address/0x970b12522CA9b4054807a2c5B736149a5BE6f670) · [mcUSD](https://celoscan.io/address/0x918146359264c492bd6934071c6bd31c854edbc3).

### Independent fact-check (2026-06-08)

Non-obvious claims cross-checked against multiple primary sources (canonical repos + live RPC + docs/blog + CeloScan):

- **"Moola is an Aave fork, not original code."** — **Confirmed.** V2 topics/selectors are byte-for-byte Aave V2 (keccak + live logs); V1 topics are byte-for-byte Aave V1; the migration blog and repos describe it as an Aave fork.
- **"V1 = Aave V1 lineage (LendingPoolCore), V2 = Aave V2 lineage (single Pool)."** — **Confirmed.** V1 provider exposes `getLendingPoolCore()` → `0xaf10…8F73` (a funded core contract); V2 provider has no core and emits `Withdraw`. Both verified on-chain.
- **"V2 is the live market; V1 is wound down."** — **Confirmed.** V2 Pool shows ongoing 2026 lending logs; V1 Pool's heavy activity is concentrated in 2020–2021 windows (migration was Oct 2021).
- **"Oracle quotes in CELO, not USD; account data is CELO-denominated."** — **Confirmed.** `getAssetPrice(CELO) = 1e18` (CELO is the base unit); the oracle reverts on `ADDRESSES_PROVIDER()`, indicating a custom Celo-native price source rather than a stock Aave Chainlink AaveOracle.
- **"`liquidationCall` selector absent from the V2 Pool impl; detect liquidations via event."** — **Confirmed.** PUSH4/raw scan of impl `0xbecd…711F` finds `deposit`/`borrow`/`flashLoan` but not `0x00a718a9`; the `LiquidationCall` event nonetheless fires (verified). Liquidations route through CollateralManager `0xa2db…3b32` (provider-resolved delegatecall target).
- **"Moola is Celo-only; absent on the seven monitored chains."** — **Confirmed.** Every Moola address returns `0x` from `eth_getCode` on all seven (§5).
- **mToken vs underlying symbol mismatch (cUSD reports `USDm`).** — **Confirmed** via live `symbol()` calls; the mToken wrappers report `mcUSD`/`mCEUR`/`mCREAL`. Recorded as a gotcha (§9.10) to avoid mislabeling reserves.
