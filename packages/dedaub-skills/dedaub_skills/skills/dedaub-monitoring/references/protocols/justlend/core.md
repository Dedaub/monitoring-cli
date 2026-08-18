# JustLend DAO — Topics, Selectors, Addresses (Compound-V2 fork; **TRON-only** — ABSENT on all 7 EVM targets)

**Status:** verified on 2026-06-08 against live `eth_getCode` on all seven EVM target chains, the canonical `justlend/justlend-protocol` repo, the `docs.justlend.org` address registry, and **live TRON logs/state via TronGrid** (jUSDT Borrow tx `d5e45da0…1f1e5b`, Unitroller event stream, on-chain `comptrollerImplementation()`/`implementation()` reads). Every topic0/selector recomputed locally with keccak; the JustLend-specific event shapes were additionally confirmed byte-for-byte against real TRON logs.

**Scope.** **The headline finding: JustLend DAO is deployed only on TRON (TRON mainnet, not one of the seven requested chains), and it is NOT deployed on any of the seven EVM targets.** Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10) and Polygon PoS (137) **all return empty `eth_getCode` (`0x`)** for the JustLend Unitroller, Comptroller and jToken addresses (the same 20-byte hash a TRON address resolves to). This doc still fully documents the chain-agnostic Compound-V2-fork topics/selectors (they are reusable should JustLend ever bridge a market, and they anchor the absence checks), and records the canonical TRON deployment addresses in a clearly-labelled **off-target reference (§5)** — those TRON addresses are base58/`0x41`-hex and are **not** `eth_getCode`-able on the EVM RPCs.

JustLend is a **Compound V2 fork** (the repo keeps Compound's class names — `CToken`/`CErc20`/`CEther`/`Comptroller`/`Unitroller` — while the *deployed* markets are branded **jTokens**: jTRX, jUSDT, jUSDD, …). It is the largest lending protocol on TRON. Three deviations from stock Compound V2 are load-bearing for monitoring and were each confirmed against live TRON logs:

1. **`Borrow` and `RepayBorrow` carry an extra trailing `borrowIndex` argument.** JustLend's `Borrow` is **5-arg** `Borrow(address,uint256,uint256,uint256,uint256)` → topic0 `0x2dd79f4f…` (NOT stock Compound's 4-arg `0x13ed6866…`), and `RepayBorrow` is **6-arg** `RepayBorrow(address,address,uint256,uint256,uint256,uint256)` → topic0 `0x6fadbf73…` (NOT stock 5-arg `0x1a2a22cb…`). Verified live: jUSDT `Borrow` log data = **160 bytes** (5×uint256) with topic0 `0x2dd79f4f…`.
2. **`AccrueInterest` is the 4-arg form** `AccrueInterest(uint256,uint256,uint256,uint256)` (topic0 `0x4dec04e7…`), confirmed live as **128-byte** data on jUSDT — same as newer-Compound/Moonwell, not the legacy 3-arg `0x875352fb…`.
3. **Two JustLend-only telemetry events fire on every market mutation:** **`JTokenStatus(uint256×7)`** (topic0 `0x24d9ee20…`, 224-byte data — confirmed live) emits a full market snapshot (cash/borrow/reserve/supply/borrowRatePerBlock/borrowIndex/reserveFactor), and **`JTokenBalance(address,uint256)`** (topic0 `0x58709c72…`) emits the acting user's post-action jToken balance. These have no Compound analogue.

**Rewards are NOT Compound-style.** The live Comptroller has **no** `claimComp` / `compSupplySpeeds` / `compBorrowSpeeds` and emits **no** `DistributedSupplierComp` / `DistributedBorrowerComp` / `CompSpeedUpdated` / `MarketComped`. JST "supply/liquidity mining" rewards are distributed off the core Comptroller (frozen 24-week vesting, governance-phased campaigns) — do not scan for COMP distribution events here. The Comptroller keeps a `compAddress` storage slot but the distribution machinery was never wired into this fork's Comptroller. **JustLend is per-block (not timestamp) accrual** — `accrualBlockNumber()`/`borrowRatePerBlock()`/`supplyRatePerBlock()` exist (unlike Moonwell's timestamp fork).

Governance is **GovernorBravo + Timelock + WJST** (wrapped JST voting token), on TRON. The Timelock is admin of the Unitroller and (via reserve-admin) the jTokens.

> **Interpreting the absence checks:** TRON addresses are `base58check` over a 21-byte `0x41‖<20-byte-hash>` payload. Dropping the `0x41` prefix yields the same 20-byte address Solidity/EVM tooling uses, so the *literal* JustLend Unitroller resolves to `0x4a33bf2666f2e75f3d6ad3b9ad316685d5c668d4` on any EVM RPC — and that address is **empty (`0x`) on all 7 targets**. TRON itself is not an `eth_*`-JSON-RPC EVM target in this scope; its addresses are recorded in §5 for reference only.

---

## 0. Contract families & versions

| Family | Repo class (Compound name) | Deployed brand | Pattern | Notes |
|--------|----------------------------|----------------|---------|-------|
| Risk engine | `Unitroller` + `Comptroller` | Unitroller (proxy) + Comptroller (logic) | **Compound Unitroller delegator** (impl in storage slot 2, NOT EIP-1967) | live impl rotated via governance — read `comptrollerImplementation()` |
| Markets | `CErc20Delegator`/`CErc20Delegate`, `CEther` | jUSDT, jUSDD, jTRX (native), … | **Compound `CErc20Delegator` delegator** (`implementation()` getter, NOT EIP-1967) | jTRX is the native-TRX market (payable `mint()`), no `underlying()` |
| Oracle | `PriceOracleProxy` → `PriceOracle` | PriceOracleProxy | proxy → impl | feeds underlying USD prices to Comptroller |
| Governance | `GovernorBravoDelegator`, `Timelock`, `WJST` | GovernorBravo + Timelock | delegator + timelock | JST holders propose/vote; Timelock executes |
| Token | JST (TRC-20) | JST | immutable TRC-20 | governance + rewards token |
| Sub-products (out of lending scope) | stUSDT, sTRX, EnergyRental/SunPump | — | — | mentioned in §9; not the lending market |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally with keccak on 2026-06-08. Items marked **(live-confirmed)** were matched byte-for-byte against real TRON logs (jUSDT Borrow tx + Unitroller event stream).

### 1.1 jToken / CErc20 (per-market; the workhorse events) — emitter = each jToken

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04` | `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` | **4-arg**, 128-byte data **(live-confirmed)** |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address minter, uint256 mintAmount, uint256 mintTokens)` | **(live-confirmed)**; collides w/ UniV2 `Mint` |
| `0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929` | `Redeem(address redeemer, uint256 redeemAmount, uint256 redeemTokens)` | **(live-confirmed)** |
| `0x2dd79f4fccfd18c360ce7f9132f3621bf05eee18f995224badb32d17f172df73` | `Borrow(address borrower, uint256 borrowAmount, uint256 accountBorrows, uint256 totalBorrows, uint256 borrowIndex)` | **JustLend 5-arg** (extra `borrowIndex`), 160-byte data **(live-confirmed)** — NOT stock `0x13ed6866…` |
| `0x6fadbf7329d21f278e724fa0d4511001a158f2a97ee35c5bc4cf8b64417399ef` | `RepayBorrow(address payer, address borrower, uint256 repayAmount, uint256 accountBorrows, uint256 totalBorrows, uint256 borrowIndex)` | **JustLend 6-arg** — NOT stock `0x1a2a22cb…` |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address liquidator, address borrower, uint256 repayAmount, address cTokenCollateral, uint256 seizeTokens)` | standard Compound shape |
| `0x24d9ee20a6e9910fbe793dcfe50a7f6bd805a9a17e894f22ac7d0bbb35e065b7` | `JTokenStatus(uint256 totalCash, uint256 totalBorrow, uint256 totalReserve, uint256 totalSupply, uint256 borrowRatePerBlock, uint256 borrowIndex, uint256 reserveFactorMantissa)` | **JustLend-only**, 224-byte data **(live-confirmed)** — fires on every mutation |
| `0x58709c72c20546249fd8c38365fe4d57bcc1f800af6b7a7a33e0c256217a4399` | `JTokenBalance(address user, uint256 jtoken_balance)` | **JustLend-only** — acting user's post-action balance |
| `0xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5` | `ReservesAdded(address benefactor, uint256 addAmount, uint256 newTotalReserves)` | |
| `0x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e` | `ReservesReduced(address admin, uint256 reduceAmount, uint256 newTotalReserves)` | |
| `0xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460` | `NewReserveFactor(uint256 oldReserveFactorMantissa, uint256 newReserveFactorMantissa)` | |
| `0xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926` | `NewMarketInterestRateModel(address oldIRM, address newIRM)` | |
| `0x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d` | `NewComptroller(address oldComptroller, address newComptroller)` | |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` | jToken delegator upgrade |
| `0x6b05e4710a05e41140c8589bc8113d9a357a2202e233f6c599bc07971cc1b9c4` | `NewReserveAdmin(address oldReserveAdmin, address newReserveAdmin)` | **JustLend-only** (separate reserve-withdrawal admin) |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` | |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` | |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` | jToken shares (ERC-20) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` | |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` | soft-fail (pre-revert legacy path) |

> **`Mint`/`Transfer`/`Approval` topic0s collide** with Uniswap-V2 / every ERC-20. Disambiguate by emitter (a jToken). The **5-arg `Borrow`/6-arg `RepayBorrow`** topic0s are JustLend-specific — a decoder keyed on stock-Compound `0x13ed6866…`/`0x1a2a22cb…` will **silently miss every JustLend borrow/repay**.

### 1.2 Comptroller (one Unitroller per deployment) — emitter = Unitroller

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address cToken)` | |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address cToken, address account)` | **(live-confirmed)** |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address cToken, address account)` | **(live-confirmed)** |
| `0x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9` | `NewCloseFactor(uint256 oldCloseFactorMantissa, uint256 newCloseFactorMantissa)` | |
| `0x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5` | `NewCollateralFactor(address cToken, uint256 oldCFMantissa, uint256 newCFMantissa)` | |
| `0xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316` | `NewLiquidationIncentive(uint256 oldIncentiveMantissa, uint256 newIncentiveMantissa)` | |
| `0x7093cf1eb653f749c3ff531d6df7f92764536a7fa0d13530cd26e070780c32ea` | `NewMaxAssets(uint256 oldMaxAssets, uint256 newMaxAssets)` | **older-Compound** field (caps # markets entered) — JustLend uses `maxAssets`, NOT supply/borrow caps |
| `0xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22` | `NewPriceOracle(address oldOracle, address newOracle)` | |
| `0x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e` | `NewPauseGuardian(address oldPauseGuardian, address newPauseGuardian)` | |
| `0xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0` | `ActionPaused(string action, bool pauseState)` | global (Transfer/Seize) |
| `0x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0` | `ActionPaused(address cToken, string action, bool pauseState)` | per-market (Mint/Borrow) |

> **Absent on the JustLend Comptroller** (do NOT scan for these — feature not in this fork's Comptroller): `NewBorrowCap`/`NewSupplyCap`/`NewBorrowCapGuardian` (no caps — it uses `maxAssets`); `MarketComped`/`CompSpeedUpdated`/`DistributedSupplierComp`/`DistributedBorrowerComp`/`CompGranted` (no COMP-style rewards). `NewImplementation`/`NewPendingImplementation` fire on the **Unitroller** at impl rotation (Unitroller-delegator events; same topic0s as in §1.1's `NewImplementation` for the jToken delegator — disambiguate by emitter).

### 1.3 Unitroller (Comptroller proxy — admin/upgrade events)

| topic0 | Event |
|--------|-------|
| `0xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815` | `NewPendingImplementation(address oldPendingImplementation, address newPendingImplementation)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Selectors recomputed locally on 2026-06-08; cross-checked against known Compound canon (`mint`=`0xa0712d68`, `borrow`=`0xc5ebeaec`, `enterMarkets`=`0xc2998238`, `getUnderlyingPrice`=`0xfc57d4df`). Interface-file `uint` canonicalized to `uint256`. **The event *shapes* diverge (5/6-arg Borrow/RepayBorrow) but the *call selectors* below are stock Compound** — the extra `borrowIndex` is an emit-only field, so `borrow(uint256)` etc. are unchanged.

### 2.1 jToken / CErc20 (per-market)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa0712d68` | `mint(uint256 mintAmount)` | Supply underlying → jTokens. Emits `Mint`+`AccrueInterest`+`JTokenStatus`. |
| `0x1249c58b` | `mint()` | **Native jTRX market** — payable mint of TRX. |
| `0xdb006a75` | `redeem(uint256 redeemTokens)` | Burn jTokens for underlying. |
| `0x852a12e3` | `redeemUnderlying(uint256 redeemAmount)` | |
| `0xc5ebeaec` | `borrow(uint256 borrowAmount)` | Emits 5-arg `Borrow`. |
| `0x0e752702` | `repayBorrow(uint256 repayAmount)` | `type(uint).max` repays full. Emits 6-arg `RepayBorrow`. |
| `0x4e4d9fea` | `repayBorrow()` | Native jTRX repay (payable). |
| `0x2608f818` | `repayBorrowBehalf(address borrower, uint256 repayAmount)` | |
| `0xf5e3c462` | `liquidateBorrow(address borrower, uint256 repayAmount, address cTokenCollateral)` | Emits `LiquidateBorrow`. |
| `0xaae40a2a` | `liquidateBorrow(address borrower, address cTokenCollateral)` | Native jTRX (payable) overload. |
| `0xb2a02ff1` | `seize(address liquidator, address borrower, uint256 seizeTokens)` | Cross-market collateral seizure. |
| `0xa9059cbb` / `0x23b872dd` / `0x095ea7b3` | `transfer` / `transferFrom` / `approve` | jToken shares (ERC-20). |
| `0xa6afed95` | `accrueInterest()` | Emits `AccrueInterest`+`JTokenStatus`. |
| `0xbd6d894d` / `0x182df0f5` | `exchangeRateCurrent()` / `exchangeRateStored()` | Accrue-then-read / view. |
| `0x17bfdfbc` / `0x95dd9193` | `borrowBalanceCurrent(address)` / `borrowBalanceStored(address)` | Debt accrue-then-read / view. |
| `0x3b1d21a2` | `getCash()` | Underlying held by the jToken. |
| `0xae9d70b0` | `supplyRatePerBlock()` | **Per-block** supply rate mantissa (JustLend is per-block, not per-timestamp). |
| `0xf8f9da28` | `borrowRatePerBlock()` | **Per-block** borrow rate mantissa. |
| `0x6c540baf` | `accrualBlockNumber()` | **Block number** of last accrual (NOT a timestamp). |
| `0x47bd3718` / `0x8f840ddd` / `0xaa5af0fd` / `0x173b9904` | `totalBorrows()` / `totalReserves()` / `borrowIndex()` / `reserveFactorMantissa()` | |
| `0x5fe3b567` | `comptroller()` | Returns the Unitroller address. |
| `0xf3fdb15a` | `interestRateModel()` | Per-market JumpRateModelV2 / WhitePaper model. |
| `0x6f307dc3` | `underlying()` | Underlying TRC-20 (absent on native jTRX). |
| `0x5c60da1b` | `implementation()` | **Read this for the jToken logic contract** — Compound delegator, NOT EIP-1967 (§7). |
| `0x3af9e669` | `balanceOfUnderlying(address owner)` | State-mutating (accrues). |
| `0xc37f68e2` | `getAccountSnapshot(address)` | `(err, jTokenBalance, borrowBalance, exchangeRateMantissa)`. |
| `0x555bcc40` | `_setImplementation(address implementation_, bool allowResign, bytes becomeImplementationData)` | Admin-only delegator upgrade. Emits `NewImplementation`. |
| `0xfca7820b` / `0xf2b3abbd` | `_setReserveFactor(uint256)` / `_setInterestRateModel(address)` | Admin. |

### 2.2 Comptroller (behind Unitroller)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc2998238` | `enterMarkets(address[] cTokens)` | Emits `MarketEntered`. |
| `0xede4edd0` | `exitMarket(address cToken)` | Emits `MarketExited`. |
| `0x5ec88c79` | `getAccountLiquidity(address)` | `(err, liquidity, shortfall)`; shortfall>0 ⇒ liquidatable. |
| `0x4e79238f` | `getHypotheticalAccountLiquidity(address,address,uint256,uint256)` | What-if check. |
| `0xabfceffc` | `getAssetsIn(address)` | jTokens the account has entered. |
| `0x929fe9a1` | `checkMembership(address account, address cToken)` | |
| `0xb0772d0b` | `getAllMarkets()` | All listed jTokens — enumerate here (not derivable). |
| `0x8e8f294b` | `markets(address cToken)` | `(bool isListed, uint collateralFactorMantissa, …)` |
| `0x7dc0d1d0` | `oracle()` | The PriceOracleProxy address. |
| `0xe8755446` | `closeFactorMantissa()` | Max fraction of debt repayable per liquidation. |
| `0x4ada90af` | `liquidationIncentiveMantissa()` | Liquidator bonus. |
| `0xc488847b` | `liquidateCalculateSeizeTokens(address,address,uint256)` | |
| `0xa76b3fda` | `_supportMarket(address)` | Admin. Emits `MarketListed`. |
| `0xe4028eee` | `_setCollateralFactor(address,uint256)` | Admin. Emits `NewCollateralFactor`. |
| `0x3bcf7ec1` / `0x18c882a5` | `_setMintPaused(address,bool)` / `_setBorrowPaused(address,bool)` | Emit `ActionPaused(address,string,bool)`. |
| `0x55ee1fe1` / `0x317b0b77` / `0x4fd42e17` | `_setPriceOracle` / `_setCloseFactor` / `_setLiquidationIncentive` | Admin. |
| `0xbb82aa5e` | `comptrollerImplementation()` | **Unitroller: read for live Comptroller logic** (storage slot 2). |
| `0xdcfbc0c7` | `pendingComptrollerImplementation()` | Storage slot 3. |

> **Compound borrow-cap and COMP-reward selectors do NOT resolve on the JustLend Comptroller** — `_setMarketBorrowCaps`/`borrowCaps`/`claimComp`/`compSupplySpeeds`/`compBorrowSpeeds`/`_setCompSpeeds` are absent (this fork predates caps and never wired COMP distribution). Do not key monitors on them.

### 2.3 Unitroller / Oracle

| Selector | Signature |
|----------|-----------|
| `0xe992a041` | `_setPendingImplementation(address)` |
| `0xc1e80334` | `_acceptImplementation()` |
| `0xb71d1a0c` | `_setPendingAdmin(address)` |
| `0xe9c714f2` | `_acceptAdmin()` |
| `0xfc57d4df` | `getUnderlyingPrice(address cToken)` *(PriceOracleProxy)* |

---

## 3. Addresses — the 7 EVM target chains: **NOT DEPLOYED**

**JustLend has no deployment on any of Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137).** Verified 2026-06-08 by `eth_getCode` on each chain's publicnode RPC for the JustLend Unitroller (`0x4a33bf26…668d4`), Comptroller impl (`0x0b81cf71…f7ab`), jTRX (`0x2c7c9963…5c28`) and jUSDT (`0xea09611b…a3e5`) — **all return `0x` on all 7 chains** (28 checks, 28 empty). JustLend is a **TRON-native** protocol; TRON's chainId is not in scope and TRON is not an `eth_*`-RPC EVM target here.

**Do not author any JustLend market/Comptroller/jToken monitor against these 7 chains.** Any contract found at one of these literal addresses on an EVM chain is unrelated to JustLend (the address space is shared but the deployments are not).

---

## 4. Cross-chain summary

| Chain | ID | JustLend lending? | Unitroller `eth_getCode` | jUSDT `eth_getCode` |
|-------|----|--------------------|--------------------------|---------------------|
| Ethereum | 1 | ❌ not deployed | `0x` | `0x` |
| Base | 8453 | ❌ not deployed | `0x` | `0x` |
| BNB Smart Chain | 56 | ❌ not deployed | `0x` | `0x` |
| Avalanche C-Chain | 43114 | ❌ not deployed | `0x` | `0x` |
| Arbitrum One | 42161 | ❌ not deployed | `0x` | `0x` |
| Optimism | 10 | ❌ not deployed | `0x` | `0x` |
| Polygon PoS | 137 | ❌ not deployed | `0x` | `0x` |
| **TRON mainnet** *(off-target — §5)* | 728126428 (`0x2b6653dc`) | ✅ **the only deployment** | n/a (TRON, not `eth_*`) | n/a |

---

## 5. Off-target reference — TRON mainnet deployment (NOT in the 7-chain scope, NOT `eth_getCode`-checked)

The canonical JustLend deployment. Addresses below are the official **base58** form (from `docs.justlend.org` Deployed Contracts + the `justlend/justlend-protocol` repo) with the **EVM-form 20-byte hash** alongside (the `0x41`-hex payload minus its `41` prefix). All base58 checksums verified locally. **These are TRON addresses — they are NOT reachable via the EVM RPCs in §3** and are recorded here only as real anchors for the topics/selectors above.

### 5.1 Core lending system

| Role | base58 (TRON) | EVM-form hash | One-liner |
|------|---------------|---------------|-----------|
| **Unitroller** (Comptroller proxy) | `TGjYzgCyPobsNS9n6WcbdLVR9dH7mWqFx7` | `0x4a33bf2666f2e75f3d6ad3b9ad316685d5c668d4` | The risk engine. `comptrollerImplementation()` → live impl below; `oracle()` → PriceOracleProxy. Point all market-policy monitors here. |
| Comptroller (impl — **per docs**) | `TB23wYojvAsSx6gR8ebHiBqwSeABiBMPAr` | `0x0b81cf71fc58313e1b379797cf39afab33d3f7ab` | The impl the docs list — **stale**, see drift note. |
| Comptroller (impl — **live 2026-06-08**) | `TCtzg2CQsAuLkSxrGjFGbHVwKvv95W9C8e` | `0x201c6c23426f8c1e62fde0c78af9328d62f29628` | Read live from `Unitroller.comptrollerImplementation()` — the rotated, currently-active logic. |
| **PriceOracleProxy** | `TCKp2AzuhzV4B4Ahx1ej4mvQgHZ1kH7F7k` | `0x19d5cda987533693ffbd7a5eb77acd209042acbb` | `getUnderlyingPrice(jToken)`; forwards to PriceOracle. |
| PriceOracle (impl) | `TMiNCmvD3zdsv6mk7niBU6NPBzVNjYMQTV` | `0x80d2f390957701fb7c80de8767203ea1673f83db` | Underlying USD price source. |

### 5.2 jToken markets (each a `CErc20Delegator`; jTRX is native `CEther`-equivalent)

| jToken | base58 (TRON) | EVM-form hash | Underlying |
|--------|---------------|---------------|-----------|
| **jUSDT** | `TXJgMdjVX5dKiQaUi9QobwNxtSQaFqccvd` | `0xea09611b57e89d67fbb33a516eb90508ca95a3e5` | USDT (TRC-20) |
| **jTRX** | `TE2RzoSV3wFK99w6J9UnnZ4vLfXYoxvRwP` | `0x2c7c9963111905d29eb8da37d28b0f53a7bb5c28` | TRX (native; payable `mint()`, no `underlying()`) |
| jUSDD | `TKFRELGGoRgiayhwJTNNLqCNjFoLBh3Mnf` | `0x65c9fede72ba73cd1b0dca2a974c070153dc6fcb` | USDD |
| jTUSD | `TSXv71Fy5XdL3Rh2QfBoUu3NAaM4sMif8R` | `0xb5b1a24c3067f985ac2da2f6bce0fa685bf8ec06` | TUSD |
| jUSDJ | `TL5x9MtSnDy537FXKx53yAaHRRNdg9TkkA` | `0x6ef7c4870977c6a2543b0e8cf4f659af883c96dc` | USDJ |
| jSUN | `TPXDpkg9e3eZzxqxAUyke9S4z4pGJBJw9e` | `0x94a7a1e585a77e2edfd834005be9f545fe1f3c97` | SUN |
| jBTT | `TUaUHU9Dy8x5yNi1pKnFYqHWojot61Jfto` | `0xcc1d948f9397db4c047de179eb74ca013529022a` | BTT (new) |
| jNFT | `TFpPyDCKvNFgos3g3WVsAqMrdqhB81JXHE` | `0x40262ab2a177fb3fc6d2709a816db3b1a10bc78e` | NFT |
| jJST | `TWQhCXaWz4eHK4Kd1ErSDHjMFPoPc9czts` | `0xe03473f8720297d9bf887f2d7e4ec2efc70c3460` | JST |
| jWIN | `TRg6MnpsFXc82ymUPgf5qbj59ibxiEDWvv` | `0xac456571ac5a383b77c65d9fdcd66d8ac2ed62bb` | WIN |
| jBTC | `TLeEu311Cbw63BcmMHDgDLu7fnk9fqGcqT` | `0x7513102bc947f138b88f4bcc6acf73acb8d4d087` | BTC |
| jWBTC | `TVyvpmaVmz25z2GaXBDDjzLZi5iR5dBzGd` | `0xdb856d6b452971e16b9fc85169b14b781aa5d442` | WBTC |
| jETH | `TR7BUFRQeq1w5jAZf1FKx85SHuX6PfMqsV` | `0xa60befaf69b18090b762a83177f09831773967ea` | ETH |
| jETHB | `TWBxQMb6RD3qmkXUXpNwVCYbL8SHNreru6` | `0xddcbbcb2f17db034fc970fbd87ffa7da51bebbfc` | ETH (B) |
| jHTX | `TDA1mWPyAjTRATMGA55UTswGAHhV2itEXR` | `0x22f39357b77c4a2459e362ae4c6a822028dbeacc` | HTX (`0xca0303e8…271a`) |
| jUSD1 | `TBEKggwqFkrc4KckQVR9BLucAmQugafEZf` | `0x0dd3f1b2e5781688d5cf8c350050c5c236535642` | USD1 (`0x91bed8e7…ace2`) |
| jwstUSDT | `TD5SdLw5scR6mXgyMK2xKrFJpauDjpKqrW` | `0x22163f4926c1b7e1d22dbbc76fbef7f54d364d87` | wstUSDT (`0x4a7832a4…4624`) |
| jsTRX | `TJQ9rbVe9ei3nNtyGgBL22Fuu2xYjZaLAQ` | `0x5c78c77bbad44c3ebd2088e6b7b5d5f01bb0a8f5` | sTRX (the §5.4 sTRX `0xc64e69ac…c2b3`) |

All 14 rows above plus jUSDJ/jSUN/jBTT/jNFT/jWIN are confirmed live in `Comptroller.getAllMarkets()` (23 entries on 2026-06-08); each `symbol()`/`underlying()` was read on-chain.

Legacy/deprecated markets (still returned by `getAllMarkets()` — distinguish by address; verified live on 2026-06-08): `jWBTT` (`0xcba95c57…c008`), `jSUNOLD TGBr8uh9jBVHJhhkwSJvQN2ZAKzVkxDmno` (`0x4434beca…328b`), `jUSDC TNSBA6KvSvMoTqQcEgpVK7VhHT3z7wifxy` (`0x88bb336c70a33fe2506240a19826c2ad487ae6d8`), `jUSDD-OLD TX7kybeP6UwTBRHLNPYmswFESHfyjm9bAS` (`0xe7f8a90ede3d84c7c0166bd84a4635e4675accfc`, distinct from the active jUSDD `0x65c9fede…` above), `jBUSD TLHASseQymmpGQdfAyNjkMXFTJh8nzR2x2` (`0x71169cc742905196d4ae1b6330e5366b5459a3dc`). **Always enumerate live via `Comptroller.getAllMarkets()`** rather than hardcoding (Compound's market array retains deprecated markets). The market set grows; the live array held exactly **23 jToken markets** (active + retained-deprecated) as of 2026-06-08.

### 5.3 Governance & token

| Role | base58 (TRON) | EVM-form hash |
|------|---------------|---------------|
| JST (TRC-20 gov/reward token) | `TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9` | `0x18fd0626daf3af02389aef3ed87db9c33f638ffa` |
| WJST (wrapped JST, voting) | `TXk9LnTnLN7oH96H3sKxJayMxLxR9M4ZD6` | `0xeeda4dfab78d92917f11df192f9b460715d7f67b` |
| GovernorBravoDelegator | `TEqiF5JbhDPD77yjEfnEMncGRZNDt2uogD` | `0x356db5ff7599825aff31a25f8177f390304c93b8` |
| Timelock (admin of Unitroller/jTokens) | `TRWNvb15NmfNKNLhQpxefFz7cNjrYjEw7x` | `0xaa6f10960ed9f7fe44aacc3aa33dd8f7da108c23` |

### 5.4 Sub-products (outside the lending market — see §9)

| Role | base58 (TRON) | EVM-form hash |
|------|---------------|---------------|
| sTRX (staked-TRX) | `TU3kjFuhtEo42tsCBtfYUAZxoqQ4yuSLQ5` | `0xc64e69acde1c7b16c2a3efcdbbdaa96c3644c2b3` |
| EnergyRental (energy/bandwidth rental) | `TU2MJ5Veik1LRAgjeSzEdvmDYx7mefJZvd` | `0xc60a6f5c81431c97ed01b61698b6853557f3afd4` |

---

## 6. (no per-EVM-chain address sections — JustLend has zero EVM-target deployments; see §3/§4)

---

## 7. Proxies

| Contract | Pattern | How to read the impl | Detection |
|----------|---------|----------------------|-----------|
| **Unitroller** (Comptroller) | **Compound Unitroller** — NOT EIP-1967. Impl in **storage slot 2** (`comptrollerImplementation`), pending in slot 3; `admin` slot 0, `pendingAdmin` slot 1. | `comptrollerImplementation()` (`0xbb82aa5e`). EIP-1967 impl slot is **empty**. | live read returns `0x201c6c23…29628` (rotated from the docs' `0x0b81cf71…`). |
| **jToken** (CErc20Delegator) | **Compound delegator** — NOT EIP-1967. `implementation` is a plain storage var; upgraded via `_setImplementation(address,bool,bytes)`, emits `NewImplementation`. | `implementation()` (`0x5c60da1b`). | jUSDT live `implementation()` = `0x761f2a87105fef1e84fd5279e333e69f1e49cc58` (`TLjn59xNM7VEK6VZ3VQ8Y1ipxsdsFka5wZ`); `comptroller()` = Unitroller ✓. |
| **PriceOracleProxy** | proxy → `PriceOracle` impl | call the proxy; it forwards. | — |
| **GovernorBravoDelegator** | **Compound GovernorBravo delegator** — NOT EIP-1967 (`implementation` storage var). | `implementation()` getter. | — |

```
Unitroller storage layout (Compound):
  slot 0 = admin (= Timelock)   slot 1 = pendingAdmin
  slot 2 = comptrollerImplementation   ← live Comptroller logic
  slot 3 = pendingComptrollerImplementation
EIP-1967 impl slot 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc  → EMPTY on Unitroller & jTokens (this is a Compound delegator fork, not EIP-1967)
```
**Upgrade auth = Timelock** (driven by GovernorBravo proposals). The `NewImplementation`/`NewPendingImplementation` topic0s in §1.3 fire on the Unitroller at every Comptroller-logic rotation; watch them for governance upgrades.

---

## 8. Detection invariants & gotchas

1. **JustLend is TRON-only — ABSENT on all 7 EVM targets.** `eth_getCode` is `0x` for every JustLend address on Ethereum/Base/BNB/Avalanche/Arbitrum/Optimism/Polygon (§3). Never aim a JustLend monitor at the 7 chains.
2. **`Borrow` is 5-arg / `RepayBorrow` is 6-arg** (extra trailing `borrowIndex`): topic0s `0x2dd79f4f…` / `0x6fadbf73…`, **not** stock Compound `0x13ed6866…` / `0x1a2a22cb…`. A stock-Compound decoder misses every JustLend borrow/repay. Verified live (jUSDT Borrow data = 160 B).
3. **`AccrueInterest` is 4-arg** (`0x4dec04e7…`, 128-B data) — not the legacy 3-arg `0x875352fb…`.
4. **Two JustLend-only events fire on every market action:** `JTokenStatus(uint256×7)` (`0x24d9ee20…`, 224-B, full market snapshot incl. `borrowRatePerBlock`/`borrowIndex`) and `JTokenBalance(address,uint256)` (`0x58709c72…`). They precede/accompany Mint/Redeem/Borrow/Repay — handy for state without a follow-up `eth_call`, but unique to JustLend.
5. **No COMP-style rewards on the Comptroller.** No `claimComp`/`compSpeeds`/`DistributedSupplierComp`/`MarketComped`. JST mining is distributed off-core with 24-week frozen vesting — don't scan the Comptroller for reward events.
6. **No supply/borrow caps.** This fork uses the older `maxAssets` (max # markets a user can enter; `NewMaxAssets` `0x7093cf1e…`), not Compound's `borrowCaps`/`NewBorrowCap`. Risk-cap monitors must target collateral factor / pause events instead.
7. **Per-block accrual** (`accrualBlockNumber()`/`borrowRatePerBlock()`/`supplyRatePerBlock()`) — unlike timestamp forks (Moonwell). APR uses TRON's ~3 s block time × blocks/year.
8. **`Mint`/`Transfer`/`Approval` topic0s collide** with UniV2 / every ERC-20 — always filter by emitter (a jToken).
9. **Comptroller impl drifts from docs.** Live `comptrollerImplementation()` = `0x201c6c23…29628`, **not** the docs' `0x0b81cf71…f7ab`. Read the impl live; treat the docs address as a snapshot.
10. **Proxies are Compound delegators, not EIP-1967.** EIP-1967 impl slot is empty on the Unitroller and jTokens; use `comptrollerImplementation()` / `implementation()` (§7).
11. **jTRX is the native-TRX market** — payable `mint()`/`repayBorrow()`/`liquidateBorrow(address,address)` overloads, no `underlying()`. Distinguish from TRC-20 jTokens.
12. **Markets are enumerated, not derived** — each jToken is a separately-deployed `CErc20Delegator` (no CREATE2 salt). Read `getAllMarkets()`; the array retains deprecated `*OLD`/`jWBTT` markets.
13. **Admin of everything is the Timelock** (`TRWNvb1…`), driven by GovernorBravo. Parameter changes (collateral factor, pause, IRM, impl rotation) trace back to a Timelock-executed proposal.
14. **TRON address ↔ EVM hash:** a TRON base58 address is `base58check(0x41 ‖ 20-byte-hash)`; the EVM-form hash (dropping `41`) is what an `eth_getCode` literal uses. JustLend's literals resolve to empty contracts on the EVM targets — the address space overlaps, the deployments do not.

---

## 9. JustLend DAO sub-products (context; NOT the lending market)

JustLend DAO is broader than the money market. Out of scope for this lending doc but noted so a monitor doesn't conflate them: **stUSDT** (a TRON RWA/savings stablecoin product), **sTRX** (liquid-staked TRX), and the **Energy/Bandwidth rental (SunPump-adjacent EnergyRental)** market that lets users rent TRON resource credits. These have their own contracts and events (`sTRX TU3kjFu…`, `EnergyRental TU2MJ5V…`) and are **not** Compound-fork jToken markets — none of the §1 topics apply to them. Keep lending monitors keyed strictly on the jToken / Comptroller set above.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- jToken (per-market)
TOPIC_ACCRUE_INTEREST        = '\x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04'  -- 4-arg, 128B
TOPIC_MINT                   = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'  -- collides UniV2 Mint
TOPIC_REDEEM                 = '\xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929'
TOPIC_BORROW_JL              = '\x2dd79f4fccfd18c360ce7f9132f3621bf05eee18f995224badb32d17f172df73'  -- JustLend 5-arg!
TOPIC_REPAY_BORROW_JL        = '\x6fadbf7329d21f278e724fa0d4511001a158f2a97ee35c5bc4cf8b64417399ef'  -- JustLend 6-arg!
TOPIC_LIQUIDATE_BORROW       = '\x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
TOPIC_JTOKEN_STATUS          = '\x24d9ee20a6e9910fbe793dcfe50a7f6bd805a9a17e894f22ac7d0bbb35e065b7'  -- JustLend-only, 224B
TOPIC_JTOKEN_BALANCE         = '\x58709c72c20546249fd8c38365fe4d57bcc1f800af6b7a7a33e0c256217a4399'  -- JustLend-only
TOPIC_RESERVES_ADDED         = '\xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5'
TOPIC_RESERVES_REDUCED       = '\x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e'
TOPIC_NEW_RESERVE_FACTOR     = '\xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460'
TOPIC_NEW_MARKET_IRM         = '\xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926'
TOPIC_NEW_COMPTROLLER        = '\x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d'
TOPIC_NEW_RESERVE_ADMIN      = '\x6b05e4710a05e41140c8589bc8113d9a357a2202e233f6c599bc07971cc1b9c4'  -- JustLend-only
TOPIC_JTOKEN_NEW_IMPL        = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'  -- also Unitroller NewImplementation
TOPIC_ERC20_TRANSFER         = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_ERC20_APPROVAL         = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_FAILURE                = '\x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0'
-- Comptroller
TOPIC_MARKET_LISTED          = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_MARKET_ENTERED         = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'
TOPIC_MARKET_EXITED          = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_NEW_CLOSE_FACTOR       = '\x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9'
TOPIC_NEW_COLLATERAL_FACTOR  = '\x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5'
TOPIC_NEW_LIQ_INCENTIVE      = '\xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316'
TOPIC_NEW_MAX_ASSETS         = '\x7093cf1eb653f749c3ff531d6df7f92764536a7fa0d13530cd26e070780c32ea'  -- (no borrow/supply caps)
TOPIC_NEW_PRICE_ORACLE       = '\xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22'
TOPIC_NEW_PAUSE_GUARDIAN     = '\x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e'
TOPIC_ACTION_PAUSED_GLOBAL   = '\xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0'  -- (string,bool)
TOPIC_ACTION_PAUSED_MARKET   = '\x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0'  -- (address,string,bool)
-- Unitroller (impl rotation)
TOPIC_NEW_PENDING_IMPL       = '\xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815'
-- NOTE: NO COMP-style reward topics exist on JustLend's Comptroller.

-- ===== Selectors (chain-agnostic) =====
SEL_MINT                     = '\xa0712d68'   -- mint(uint256)
SEL_MINT_NATIVE              = '\x1249c58b'   -- mint()  (jTRX)
SEL_REDEEM                   = '\xdb006a75'
SEL_REDEEM_UNDERLYING        = '\x852a12e3'
SEL_BORROW                   = '\xc5ebeaec'
SEL_REPAY_BORROW             = '\x0e752702'
SEL_REPAY_BORROW_NATIVE      = '\x4e4d9fea'   -- repayBorrow()  (jTRX)
SEL_REPAY_BORROW_BEHALF      = '\x2608f818'
SEL_LIQUIDATE_BORROW         = '\xf5e3c462'   -- (address,uint256,address)
SEL_LIQUIDATE_BORROW_NATIVE  = '\xaae40a2a'   -- (address,address)  (jTRX)
SEL_SEIZE                    = '\xb2a02ff1'
SEL_ACCRUE_INTEREST          = '\xa6afed95'
SEL_EXCHANGE_RATE_STORED     = '\x182df0f5'
SEL_SUPPLY_RATE_PER_BLOCK    = '\xae9d70b0'   -- per-BLOCK (not timestamp)
SEL_BORROW_RATE_PER_BLOCK    = '\xf8f9da28'
SEL_ACCRUAL_BLOCK_NUMBER     = '\x6c540baf'
SEL_GET_CASH                 = '\x3b1d21a2'
SEL_UNDERLYING               = '\x6f307dc3'
SEL_JTOKEN_IMPLEMENTATION    = '\x5c60da1b'   -- implementation()  (jToken delegator)
SEL_COMPTROLLER_IMPL         = '\xbb82aa5e'   -- comptrollerImplementation()  (Unitroller)
SEL_GET_ALL_MARKETS          = '\xb0772d0b'
SEL_GET_ACCOUNT_LIQUIDITY    = '\x5ec88c79'
SEL_ENTER_MARKETS            = '\xc2998238'
SEL_EXIT_MARKET              = '\xede4edd0'
SEL_ORACLE                   = '\x7dc0d1d0'
SEL_GET_UNDERLYING_PRICE     = '\xfc57d4df'

-- ===== Addresses (off-target TRON; EVM-form hash — EMPTY on all 7 EVM targets) =====
TRON_UNITROLLER              = '\x4a33bf2666f2e75f3d6ad3b9ad316685d5c668d4'  -- TGjYzgCyPobsNS9n6WcbdLVR9dH7mWqFx7
TRON_COMPTROLLER_IMPL_LIVE   = '\x201c6c23426f8c1e62fde0c78af9328d62f29628'  -- TCtzg2CQsAuLkSxrGjFGbHVwKvv95W9C8e (live)
TRON_COMPTROLLER_IMPL_DOCS   = '\x0b81cf71fc58313e1b379797cf39afab33d3f7ab'  -- TB23wYojvAsSx6gR8ebHiBqwSeABiBMPAr (stale)
TRON_PRICE_ORACLE_PROXY      = '\x19d5cda987533693ffbd7a5eb77acd209042acbb'  -- TCKp2AzuhzV4B4Ahx1ej4mvQgHZ1kH7F7k
TRON_JST                     = '\x18fd0626daf3af02389aef3ed87db9c33f638ffa'  -- TCFLL5dx5ZJdKnWuesXxi1VPwjLVmWZZy9
TRON_TIMELOCK                = '\xaa6f10960ed9f7fe44aacc3aa33dd8f7da108c23'  -- TRWNvb15NmfNKNLhQpxefFz7cNjrYjEw7x
TRON_J_USDT                  = '\xea09611b57e89d67fbb33a516eb90508ca95a3e5'  -- TXJgMdjVX5dKiQaUi9QobwNxtSQaFqccvd
TRON_J_TRX                   = '\x2c7c9963111905d29eb8da37d28b0f53a7bb5c28'  -- TE2RzoSV3wFK99w6J9UnnZ4vLfXYoxvRwP (native)
TRON_J_USDD                  = '\x65c9fede72ba73cd1b0dca2a974c070153dc6fcb'  -- TKFRELGGoRgiayhwJTNNLqCNjFoLBh3Mnf
TRON_J_JST                   = '\xe03473f8720297d9bf887f2d7e4ec2efc70c3460'  -- TWQhCXaWz4eHK4Kd1ErSDHjMFPoPc9czts
TRON_J_BTC                   = '\x7513102bc947f138b88f4bcc6acf73acb8d4d087'  -- TLeEu311Cbw63BcmMHDgDLu7fnk9fqGcqT
TRON_J_ETH                   = '\xa60befaf69b18090b762a83177f09831773967ea'  -- TR7BUFRQeq1w5jAZf1FKx85SHuX6PfMqsV

-- EIP-1967 impl slot (EMPTY on Unitroller/jTokens — Compound delegator fork, not EIP-1967)
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## 11. Verification & sources

How constants in this doc were verified (2026-06-08):

- **Event topic0 / selectors:** all recomputed locally as `keccak256(canonical sig)` / `[0:4]` (pycryptodome). The JustLend-specific shapes were confirmed **byte-for-byte against a live TRON jUSDT Borrow transaction** (`d5e45da06c9255a638da350ab26aeafeb17f88f34256783bdf2f602c461f1e5b`, via TronGrid `gettransactioninfobyid`): `AccrueInterest` topic0 `0x4dec04e7…` with 128-byte data (4×uint256); `Borrow` topic0 `0x2dd79f4f…` with 160-byte data (5×uint256, extra `borrowIndex`); `JTokenStatus` topic0 `0x24d9ee20…` with 224-byte data (7×uint256). `MarketEntered`/`MarketExited` confirmed on the live Unitroller event stream. The `Borrow`/`RepayBorrow`/`JTokenStatus`/`JTokenBalance` declarations were read from `justlend/justlend-protocol` `contracts/CTokenInterfaces.sol`; the Comptroller event set from `contracts/Comptroller.sol`.
- **Reward-model absence:** `contracts/Comptroller.sol` defines **no** `claimComp`/`compSpeeds`/`DistributedSupplierComp`/`MarketComped` and the docs confirm JST mining is an off-core, frozen-vesting distribution — recorded as a headline gotcha.
- **Addresses:** ground truth = `docs.justlend.org` Deployed Contracts + `justlend/justlend-protocol`. Every base58 address checksum-verified locally and converted to its EVM-form 20-byte hash. The TRON addresses are **off-target reference only** (TRON is not an `eth_*`-RPC EVM target here).
- **Absence on the 7 EVM targets:** `eth_getCode` for the JustLend Unitroller, Comptroller impl, jTRX and jUSDT literals returned `0x` on **all of** Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon (publicnode RPCs) — 28 checks, 28 empty.
- **Live TRON proxy wiring (TronGrid `triggerconstantcontract`):** Unitroller `comptrollerImplementation()` → `0x201c6c23…29628` (rotated from the docs' `0x0b81cf71…`, recorded as drift); jUSDT `implementation()` → `0x761f2a87…cc58` (Compound delegator pattern, not EIP-1967); jUSDT `comptroller()` → the Unitroller `0x4a33bf26…668d4` ✓.

Authoritative sources:
- [`justlend/justlend-protocol`](https://github.com/justlend/justlend-protocol) — Compound-V2-fork contracts (`CToken`/`CErc20`/`CEther`/`Comptroller`/`Unitroller`, `Governance/WJST`, `Timelock`, `PriceOracle`); fork ancestor [`compound-finance/compound-protocol`](https://github.com/compound-finance/compound-protocol).
- [docs.justlend.org — Deployed Contracts](https://docs.justlend.org/developers/deployed_contracts/) and [Contracts Overview](https://docs.justlend.org/developers/contracts_overview/) — canonical TRON address registry.
- TronGrid (`api.trongrid.io`) — live TRON logs (`/v1/contracts/{addr}/events`), tx info (`gettransactioninfobyid`), and constant calls (`triggerconstantcontract`) for byte-for-byte event/wiring confirmation.
- RPCs (absence checks): publicnode (`ethereum-rpc`, `base-rpc`, `bsc-rpc`, `avalanche-c-chain-rpc`, `arbitrum-one-rpc`, `optimism-rpc`, `polygon-bor-rpc`).
- Explorers: [TronScan — Unitroller](https://tronscan.org/#/contract/TGjYzgCyPobsNS9n6WcbdLVR9dH7mWqFx7) · [TronScan — jUSDT](https://tronscan.org/#/contract/TXJgMdjVX5dKiQaUi9QobwNxtSQaFqccvd).
