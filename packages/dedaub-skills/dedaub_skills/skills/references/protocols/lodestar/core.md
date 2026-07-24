# Lodestar Finance — Topics, Selectors, Addresses (Arbitrum One only)

**Status:** verified against Arbitrum One (42161) mainnet RPC (`arbitrum-one-rpc.publicnode.com`) at block ~471,350,000 and the Compound V2 reference (`compound-finance/compound-protocol`) on 2026-06-08. Every topic0/selector recomputed locally as `keccak256(canonical signature)`; every address `eth_getCode`-checked; the proxy/delegator wiring read live from storage + typed getters; the AccrueInterest variant confirmed both in delegate bytecode and on a live log.
**Scope:** the seven chains requested — **Lodestar lending is deployed on exactly ONE of them: Arbitrum One (chain 42161).** `eth_getCode` on the Lodestar Unitroller returns empty (`0x`) on **Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Optimism (10), and Polygon PoS (137)** — it is **not deployed** on any of those six. Topics and selectors are chain-agnostic; addresses are Arbitrum-specific. **Operational status: the protocol is FROZEN / wound down** (see orientation + §6).

Lodestar is a **Compound V2 fork** (cToken model) on Arbitrum: lTokens (`lUSDC`, `lETH`, `lARB`, `lplvGLP`, …) are the money markets, a **Comptroller** logic contract sits behind a **Unitroller** proxy as the risk engine, a custom **PriceOracle** (`PriceOracleProxy` with a staleness guard), and per-market **JumpRateModel** interest-rate strategies. Like stock Compound V2 it uses **two bespoke delegatecall-proxy patterns — NOT EIP-1967**: the Unitroller (Comptroller proxy) and per-market lToken **delegators** (`CErc20Delegator`-style; each lToken has its own logic via `implementation()`). The standard EIP-1967 impl slot is empty on every Lodestar contract.

Two fork-specific facts a monitoring engineer must internalise:

1. **AccrueInterest is the 4-arg form** `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)`, topic0 `0x4dec04e7…` — **not** stock Compound's original 3-arg `AccrueInterest(uint256,uint256,uint256)` (`0x8753…6cb9`). Confirmed both by delegate-bytecode scan (the 3-arg topic is absent, the 4-arg topic present in every delegate) and by a live lETH log (128 bytes of data = 4×uint256). Accrual is still **per block** (`accrualBlockNumber()` and `supplyRatePerBlock()`/`borrowRatePerBlock()` are present), unlike Moonwell's timestamp model.

2. **The protocol is paused/frozen.** Read live from the Comptroller: **every** market has `mintGuardianPaused = true`, `borrowGuardianPaused = true`, **and `collateralFactor = 0`**. No new supply, no new borrow, no asset usable as collateral. This is the post-exploit wound-down state — Lodestar suffered a **plvGLP price-oracle manipulation exploit in December 2022** (~$6.5M; the attacker inflated the `plvGLP` exchange rate to over-borrow other assets). The `lplvGLP` market remains listed in `getAllMarkets()` but is paused with a 0 collateral factor; treat any live event as residual repay/redeem/liquidation rather than organic growth.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally on 2026-06-08. `Mint`, `Redeem`, `Transfer`, `AccrueInterest`(4-arg), `DistributedSupplierComp`/`DistributedBorrowerComp` additionally confirmed against live Arbitrum logs on the lETH / lUSDC markets and the Unitroller. Lodestar is a clean Compound V2 fork, so these are byte-for-byte identical to [compound/v2.md](../compound/v2.md) **except** that Lodestar emits only the 4-arg `AccrueInterest`.

### 1.1 lToken (LErc20Delegator / LEther — per-market money-market events)

| topic0 | Event |
|--------|-------|
| `0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04` | `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` **(4-arg — the only variant Lodestar emits)** |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address minter, uint256 mintAmount, uint256 mintTokens)` |
| `0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929` | `Redeem(address redeemer, uint256 redeemAmount, uint256 redeemTokens)` |
| `0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80` | `Borrow(address borrower, uint256 borrowAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1` | `RepayBorrow(address payer, address borrower, uint256 repayAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address liquidator, address borrower, uint256 repayAmount, address lTokenCollateral, uint256 seizeTokens)` |
| `0xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5` | `ReservesAdded(address benefactor, uint256 addAmount, uint256 newTotalReserves)` |
| `0x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e` | `ReservesReduced(address admin, uint256 reduceAmount, uint256 newTotalReserves)` |
| `0xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460` | `NewReserveFactor(uint256 oldReserveFactorMantissa, uint256 newReserveFactorMantissa)` |
| `0xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926` | `NewMarketInterestRateModel(address oldInterestRateModel, address newInterestRateModel)` |
| `0x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d` | `NewComptroller(address oldComptroller, address newComptroller)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` — lToken delegator logic upgrade |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` — lToken ERC-20 share |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` — legacy soft-fail (no-op, no revert) |

> **`Mint`/`Redeem`/`Borrow`/`RepayBorrow`/`LiquidateBorrow` are NOT indexed** — every field is in `data`. Filter by lToken address + topic0. `Mint` topic0 `0x4c209b5f…` collides with Uniswap-V2 `Mint(address,uint256,uint256)` — disambiguate by emitter. The 3-arg `AccrueInterest` (`0x875352fb…`) **does not exist on Lodestar** — do not index it.

> **`0x6fadbf7329d21f278e724fa0d4511001a158f2a97ee35c5bc4cf8b64417399ef`** — a **Lodestar-specific, non-core lToken event** (192 bytes of data = 6 words; observed emitted by the lETH market alongside `Redeem` during router-driven redemptions, carrying two address words + four amount words). It is **unverified** as to exact signature (not a Compound V2 event; no canonical interface published) and is **not** a money-market primitive. Listed for completeness only — do not build supply/borrow/liquidation monitors on it.

### 1.2 Comptroller (one instance, behind the Unitroller)

| topic0 | Event |
|--------|-------|
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address lToken)` |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address lToken, address account)` |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address lToken, address account)` |
| `0x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9` | `NewCloseFactor(uint256 oldCloseFactorMantissa, uint256 newCloseFactorMantissa)` |
| `0x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5` | `NewCollateralFactor(address lToken, uint256 oldCollateralFactorMantissa, uint256 newCollateralFactorMantissa)` |
| `0xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316` | `NewLiquidationIncentive(uint256 oldLiquidationIncentiveMantissa, uint256 newLiquidationIncentiveMantissa)` |
| `0xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22` | `NewPriceOracle(address oldPriceOracle, address newPriceOracle)` |
| `0x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e` | `NewPauseGuardian(address oldPauseGuardian, address newPauseGuardian)` |
| `0xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0` | `ActionPaused(string action, bool pauseState)` — global (Transfer / Seize) |
| `0x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0` | `ActionPaused(address lToken, string action, bool pauseState)` — per-market (Mint / Borrow) |
| `0x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6` | `NewBorrowCap(address indexed lToken, uint256 newBorrowCap)` |
| `0xeda98690e518e9a05f8ec6837663e188211b2da8f4906648b323f2c1d4434e29` | `NewBorrowCapGuardian(address oldBorrowCapGuardian, address newBorrowCapGuardian)` |
| `0x9e0ad9cee10bdf36b7fbd38910c0bdff0f275ace679b45b922381c2723d676f8` | `NewSupplyCap(address indexed lToken, uint256 newSupplyCap)` (Lodestar carries supply caps) |
| `0x2caecd17d02f56fa897705dcc740da2d237c373f70686f4e0d9bd3bf0400ea7a` | `DistributedSupplierComp(address indexed lToken, address indexed supplier, uint256 compDelta, uint256 compSupplyIndex)` — LODE rewards |
| `0x1fc3ecc087d8d2d15e23d0032af5a47059c3892d003d8e139fdcb6bb327c99a6` | `DistributedBorrowerComp(address indexed lToken, address indexed borrower, uint256 compDelta, uint256 compBorrowIndex)` — LODE rewards |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` — Comptroller soft-fail |

> Comptroller reward distribution reuses Compound's **`Distributed*Comp`** event names (the comp-style accrual machinery distributes **LODE**, not COMP). All the topics above were confirmed present in the live Comptroller-implementation bytecode (`0xe64e44c9…`); the two `Distributed*Comp` topics + both `ActionPaused` overloads additionally observed on live Unitroller logs.

### 1.3 Unitroller (Comptroller proxy — admin/upgrade events)

| topic0 | Event |
|--------|-------|
| `0xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815` | `NewPendingImplementation(address oldPendingImplementation, address newPendingImplementation)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` — **watch this for Comptroller logic swaps** |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |

> Lodestar's "upgrade event to watch" is **`NewImplementation` (`0xd604de94…`)** — emitted by the Unitroller on a Comptroller logic swap and by each lToken delegator on its own logic swap (same topic0; disambiguate by emitter). There is **no EIP-1967 `Upgraded(address)` (`0xbc7cd75a…`)** anywhere in Lodestar — the proxies are Compound delegators, not ERC-1967.

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

Selectors recomputed locally; the core lToken + Comptroller selectors confirmed **present** in the live Arbitrum delegate / Comptroller-impl bytecode. Compound V2 `uint` canonicalised to `uint256`.

### 2.1 lToken — user actions (LErc20 / LEther)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa0712d68` | `mint(uint256 mintAmount)` | Supply underlying → receive lTokens. Returns `uint` error code. Emits `Mint`+`AccrueInterest`+`Transfer`. **Present on all LErc20 markets, absent on lETH.** |
| `0x1249c58b` | `mint()` | **lETH only** (`payable`; LEther has no `underlying`). |
| `0xdb006a75` | `redeem(uint256 redeemTokens)` | Burn lTokens for underlying. Emits `Redeem`. |
| `0x852a12e3` | `redeemUnderlying(uint256 redeemAmount)` | Redeem an exact underlying amount. |
| `0xc5ebeaec` | `borrow(uint256 borrowAmount)` | Emits `Borrow`. |
| `0x0e752702` | `repayBorrow(uint256 repayAmount)` | `type(uint256).max` = repay full debt. Emits `RepayBorrow`. |
| `0x4e4d9fea` | `repayBorrow()` | **lETH only** (`payable`). |
| `0x2608f818` | `repayBorrowBehalf(address borrower, uint256 repayAmount)` | Repay another account's debt. |
| `0xf5e3c462` | `liquidateBorrow(address borrower, uint256 repayAmount, address lTokenCollateral)` | LErc20 liquidation. Emits `LiquidateBorrow`. |
| `0xaae40a2a` | `liquidateBorrow(address borrower, address lTokenCollateral)` | **lETH only** (`payable`). |
| `0xb2a02ff1` | `seize(address liquidator, address borrower, uint256 seizeTokens)` | lToken→lToken collateral-share transfer during liquidation. |
| `0xa9059cbb` | `transfer(address dst, uint256 amount)` | lToken share ERC-20 transfer. |
| `0x555bcc40` | `_setImplementation(address implementation_, bool allowResign, bytes becomeImplementationData)` | Admin-only lToken logic swap (delegator). Emits `NewImplementation`. |

### 2.2 lToken — views / state

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x182df0f5` | `exchangeRateStored()` | `uint` — cached lToken→underlying rate (scaled `1e(18-8+underlyingDecimals)`). |
| `0xbd6d894d` | `exchangeRateCurrent()` | `uint` — accrues first (non-view). |
| `0x3b1d21a2` | `getCash()` | `uint` — underlying held by the market. |
| `0xae9d70b0` | `supplyRatePerBlock()` | `uint` — **per block** (Lodestar accrues per block, not per second). |
| `0xf8f9da28` | `borrowRatePerBlock()` | `uint` — per block. |
| `0x6c540baf` | `accrualBlockNumber()` | `uint` — **block number** of last accrual (NOT a timestamp). |
| `0x47bd3718` | `totalBorrows()` | `uint` |
| `0x8f840ddd` | `totalReserves()` | `uint` |
| `0x18160ddd` | `totalSupply()` | `uint` — total lToken shares. |
| `0x70a08231` | `balanceOf(address)` | `uint` — lToken share balance (8 decimals). |
| `0x3af9e669` | `balanceOfUnderlying(address)` | `uint` — non-view; `balanceOf × exchangeRateCurrent`. |
| `0x95dd9193` | `borrowBalanceStored(address)` | `uint` — cached debt incl. interest. |
| `0x17bfdfbc` | `borrowBalanceCurrent(address)` | `uint` — non-view, accrues first. |
| `0xc37f68e2` | `getAccountSnapshot(address)` | `(uint err, uint lTokenBalance, uint borrowBalance, uint exchangeRateMantissa)` |
| `0xa6afed95` | `accrueInterest()` | Pokes accrual. Emits `AccrueInterest` (4-arg). |
| `0x6f307dc3` | `underlying()` | `address` — **reverts / absent on lETH (LEther).** |
| `0x5fe3b567` | `comptroller()` | `address` — the Unitroller. |
| `0xf3fdb15a` | `interestRateModel()` | `address` — per-market JumpRateModel. |
| `0x173b9904` | `reserveFactorMantissa()` | `uint` (1e18). |
| `0xaa5af0fd` | `borrowIndex()` | `uint` — global borrow interest index. |
| `0x5c60da1b` | `implementation()` | `address` — **the current delegate logic** (read this, NOT the EIP-1967 slot). |
| `0x95d89b41` / `0x06fdde03` / `0x313ce567` | `symbol()` / `name()` / `decimals()` | lTokens are **8 decimals**; `symbol()` = `l`+underlying (`lUSDC`, `lETH`), `name()` = `Lodestar …`. |

### 2.3 Comptroller (behind the Unitroller)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc2998238` | `enterMarkets(address[] lTokens)` | Use markets as collateral. Returns `uint[]` error codes. Emits `MarketEntered`. |
| `0xede4edd0` | `exitMarket(address lToken)` | Emits `MarketExited`. |
| `0xabfceffc` | `getAssetsIn(address account)` | `address[]` — markets entered. |
| `0x8e8f294b` | `markets(address lToken)` | `(bool isListed, uint collateralFactorMantissa, …)` — **collateralFactor = 0 on every market today.** |
| `0x929fe9a1` | `checkMembership(address account, address lToken)` | `bool` |
| `0x5ec88c79` | `getAccountLiquidity(address account)` | `(uint err, uint liquidity, uint shortfall)` — shortfall > 0 ⇒ liquidatable. |
| `0xb0772d0b` | `getAllMarkets()` | `address[]` — all listed lTokens (**15**; re-read live, do not hardcode). |
| `0xe8755446` | `closeFactorMantissa()` | `uint` — max fraction of debt repayable per liquidation (live = `0.5e18`). |
| `0x4ada90af` | `liquidationIncentiveMantissa()` | `uint` — liquidator collateral bonus (live = `1.08e18`). |
| `0x7dc0d1d0` | `oracle()` | `address` — the Lodestar PriceOracle proxy. |
| `0x731f0c2b` | `mintGuardianPaused(address lToken)` | `bool` — **true on every market.** |
| `0x6d154ea5` | `borrowGuardianPaused(address lToken)` | `bool` — **true on every market.** |
| `0x4a584432` | `borrowCaps(address lToken)` | `uint` — 0 = uncapped. |
| `0x02c3bcbb` | `supplyCaps(address lToken)` | `uint` |
| `0xcc7ebdc4` | `compAccrued(address)` | `uint` — unclaimed LODE. |
| `0xe9af0292` | `claimComp(address holder)` | Claim accrued LODE (function keeps the Compound name). |
| `0x1c3db2e0` | `claimComp(address holder, address[] lTokens)` | Targeted claim. |
| `0xbb82aa5e` | `comptrollerImplementation()` | `address` — live Comptroller logic (Unitroller storage). |
| `0xf851a440` | `admin()` | `address` — the governance multisig (Gnosis Safe). |
| `0x26782247` | `pendingAdmin()` | `address` — live = `0x0`. |

### 2.4 PriceOracle

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfc57d4df` | `getUnderlyingPrice(address lToken)` | `uint` — Comptroller's pricing entry point (mantissa scaled to `36 − underlyingDecimals`). **Reverts `"Price not fresh"` for several markets today** (see §9) — a hardened staleness guard. |

> Lodestar's oracle is **not** a stock Compound `UniswapAnchoredView` and **not** a simple Chainlink passthrough — it is a custom `PriceOracleProxy` that (a) sources Chainlink feeds for plain assets, (b) computed `plvGLP` from the Plutus vault exchange rate (the surface that was manipulated in the Dec-2022 exploit), and (c) enforces a freshness check that now reverts on stale/disabled feeds. Read `getUnderlyingPrice` per lToken; expect reverts.

---

## 3. Addresses — Arbitrum One (chain ID 42161)

All verified via `eth_getCode` (non-empty) on `https://arbitrum-one-rpc.publicnode.com` on 2026-06-08. Wiring confirmed live: `Unitroller.comptrollerImplementation()` → Comptroller impl; `Unitroller.oracle()` → PriceOracle; `Unitroller.admin()` → the Safe; every lToken's `comptroller()` → the Unitroller; `getAllMarkets()` → the 15 lTokens below.

### 3.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| **Unitroller** (Comptroller proxy) | `0xa86DD95c210dd186Fa7639F93E4177E97d057576` | The risk engine + entry point. Storage lives here; logic delegated. **Point all market/collateral/pause monitors here.** |
| Comptroller implementation (current) | `0xe64e44c97F9a019F70F8cdB3F4D3D465C56E9AB2` | Live Comptroller logic behind the Unitroller (read via `comptrollerImplementation()` — it rotates with `NewImplementation`). |
| **PriceOracle** (`PriceOracleProxy`) | `0xcCF9393df2F656262FD79599175950faB4D4ec01` | Custom oracle; `getUnderlyingPrice(lToken)`. Reverts `"Price not fresh"` on several markets. |
| **admin / governance** (Gnosis Safe v1.3.0, 3-of-N) | `0xeD093f9720b2507C9b54FC117ECB2618910734dD` | `admin` of the Unitroller **and** every lToken. Safe singleton `0x3e5c…d36e`, threshold 3. All admin actions originate here. |
| **pauseGuardian** | `0x8cE938fCd4E2bE078d8cDc71a63979848e131236` | **EOA (no code)** — can pause mint/borrow/transfer/seize independently of the multisig. |
| **LODE** (governance / reward token) | `0xF19547f9ED24aA66b03c3a552D181Ae334FBb8DB` | ERC-20 "Lodestar"; distributed via the Comptroller's comp-style accrual (`Distributed*Comp`). |

### 3.2 lToken markets (15) — `symbol` is `l`+underlying, **8 decimals**, each its own delegator

Each lToken is a separately-deployed delegator with its **own** logic contract (`implementation()`); they are **not** CREATE2 clones and cannot be derived — enumerate via `getAllMarkets()`. lETH is the `LEther` (payable, no `underlying()`). **All 15 are currently mint-paused, borrow-paused, and have collateralFactor = 0.**

| lToken | Address | Underlying | Underlying addr (decimals) | Delegate (`implementation()`) | JumpRateModel |
|--------|---------|-----------|----------------------------|-------------------------------|---------------|
| **lplvGLP** | `0xeA0a73c17323d1a9457D722F10E7baB22dc0cB83` | plvGLP (exploited) | `0x5326E71Ff593Ecc2CF7AcaE5Fe57582D6e74CFF1` (18) | `0x3bBfBE6fa43D75413968b1c9A7B7305E4d36e47C` | `0xb74e21f4B73380abf617AffE8C564a612b655D93` |
| **lUSDC** | `0x4C9aAed3b8c443b4b634D1A189a5e25C604768dE` | USDC (native) | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` (6) | `0x254936D0451F0198272F9C64BCDA2534061FBBCC` | `0xeC68bC9190c815289a5A187cA88D3769a4406DCf` |
| **lETH** (LEther) | `0x2193c45244AF12C280941281c8aa67dd08be0a64` | ETH (native) | WETH `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` (18) | `0xf96Bc59fc200b485fe5A84CC077529De3627B24B` | `0x0C6f39040b4eaaA8970b6Ec07Ada9F9151D352fB` |
| **lDPX** | `0x5d27cFf80dF09f28534bb37d386D43aA60f88e25` | DPX | `0x6C2C06790b3E3E3c38e12Ee22F8183b37a13EE55` (18) | `0xfaD157A82243546832bB40121E2f9132df833Bb1` | `0x06d322a466993Fd394C99d73C601EB88239F300f` |
| **lFRAX** | `0xD12d43Cdf498e377D3bfa2c6217f05B466E14228` | FRAX | `0x17FC002b466eEc40DaE837Fc4bE5c67993ddBd6F` (18) | `0xFC47e6A405402a7da7D66d360cc58D2f93f81F47` | `0xb74e21f4B73380abf617AffE8C564a612b655D93` |
| **lMAGIC** | `0xf21Ef887CB667f84B8eC5934C1713A7Ade8c38Cf` | MAGIC | `0x539bdE0d7Dbd336b79148AA742883198BBF60342` (18) | `0x48BF1d7966cc74F57E39c55fE6Bde5f456f0335b` | `0x06d322a466993Fd394C99d73C601EB88239F300f` |
| **lWBTC** | `0xC37896Bf3EE5a2c62Cdbd674035069776f721668` | WBTC | `0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f` (8) | `0x1d8F62736CCcddDdD0914e5822743D6a54c60FE1` | `0xb74e21f4B73380abf617AffE8C564a612b655D93` |
| **lDAI** | `0x4987782da9a63bC3ABace48648B15546D821c720` | DAI | `0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1` (18) | `0x0B2c0a787Cf2E13Bab703FD5b12F21dbDB0706b1` | `0xb74e21f4B73380abf617AffE8C564a612b655D93` |
| **lARB** | `0x8991d64fe388fA79A4f7Aa7826E8dA09F0c3C96a` | ARB | `0x912CE59144191C1204E64559FE8253a0e49E6548` (18) | `0x8A76fF3410ed18a404EA5624a2C2C145A16B0F5D` | `0xb74e21f4B73380abf617AffE8C564a612b655D93` |
| **lwstETH** | `0xfEcE754D92bd956F681A941Cef4632AB65710495` | wstETH | `0x5979D7b546E38E414F7E9822514be443A4800529` (18) | `0xB7F7D0790B21DECc56493FdB62c690B2C1A9a7Ba` | `0xb74e21f4B73380abf617AffE8C564a612b655D93` |
| **lGMX** | `0x79B6c5e1A7C0aD507E1dB81eC7cF269062BAb4Eb` | GMX | `0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a` (18) | `0xFab93372a50878a340dD03079ff332f33b36DB65` | `0xb74e21f4B73380abf617AffE8C564a612b655D93` |
| **lUSDT** | `0x9365181A7df82a1cC578eAE443EFd89f00dbb643` | USDT0 (USD₮0) | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` (6) | `0x5fF0b96F0b1bA8a441baa9EE3acBec94517a3d9B` | `0x8181DEa7f49B30175ef3E14B1b86412c17b0961c` |
| **lUSDC.e** | `0x1ca530f02DD0487cEf4943c674342c5aEa08922F` | USDC.e (bridged) | `0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8` (6) | `0xEA1DCC22339520a9e5442C3B9315ECf41d24DdEC` | `0xFc7Df1a97A5669f9781049ba459B638fC9E64BaD` |
| **lMIM** | `0x929CC7Eba600Ccb3FaF5494210206C93219cCB28` | MIM | `0xFEa7a6a0B346362BF88A9e4A88416B77a57D6c2A` (18) | `0x816270dA1664Ea8D7D5096112F0eFce7C2DE06fE` | `0x8181DEa7f49B30175ef3E14B1b86412c17b0961c` |
| **lPENDLE** | `0x39C27dFDc9364a976926A820c8caa8FD035d0727` | PENDLE | `0x0c880f6761F1af8d9Aa9C466984b80DAb9a8c9e8` (18) | `0x463Debcafd91Af3a6e3eF91C320Aa0BfBb7903ca` | `0x06d322a466993Fd394C99d73C601EB88239F300f` |

> lToken decimals = **8** always (not the underlying's). Underlying value = `lTokenAmount × exchangeRateStored`, with `exchangeRateStored` scaled by `1e(18 − 8 + underlyingDecimals)`. lUSDC uses **native** Arbitrum USDC (`0xaf88…`); lUSDC.e uses the **bridged** USDC.e (`0xFF97…`) — two distinct markets. lUSDT's underlying is the migrated **USDT0** token.

### 3.3 Interest-rate models (JumpRateModel — 6 distinct)

Per-market `JumpRateModel` contracts (`isInterestRateModel()` = true; ~1.4 KB each). Several markets share one model. Read each market's live model via `lToken.interestRateModel()` rather than hardcoding.

| JumpRateModel | Markets using it |
|---------------|------------------|
| `0xb74e21f4B73380abf617AffE8C564a612b655D93` | plvGLP, FRAX, WBTC, DAI, ARB, wstETH, GMX (the shared "blue-chip" model) |
| `0xeC68bC9190c815289a5A187cA88D3769a4406DCf` | USDC |
| `0x0C6f39040b4eaaA8970b6Ec07Ada9F9151D352fB` | ETH |
| `0x06d322a466993Fd394C99d73C601EB88239F300f` | DPX, MAGIC, PENDLE |
| `0x8181DEa7f49B30175ef3E14B1b86412c17b0961c` | USDT, MIM |
| `0xFc7Df1a97A5669f9781049ba459B638fC9E64BaD` | USDC.e |

---

## 4. Chains with NO Lodestar deployment

**Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Optimism (10), Polygon PoS (137): Lodestar is NOT deployed.** `eth_getCode` on the Unitroller `0xa86DD95c…` returns empty (`0x`) on every one of these six chains (checked 2026-06-08). Lodestar was an **Arbitrum-native** protocol; it never deployed lending markets anywhere else. Any "Lodestar" contract claimed on these chains is unrelated. Do not author Lodestar monitors for them.

---

## 5. Cross-chain summary

| Chain | ID | Lodestar lending? | Unitroller | Notes |
|-------|----|--------------------|-----------|-------|
| **Arbitrum One** | 42161 | ✅ deployed, **frozen** | `0xa86DD95c…7576` | 15 lTokens, all paused, CF = 0 |
| Ethereum | 1 | ❌ not deployed | — | `eth_getCode` = `0x` |
| Base | 8453 | ❌ not deployed | — | `eth_getCode` = `0x` |
| BNB | 56 | ❌ not deployed | — | `eth_getCode` = `0x` |
| Avalanche | 43114 | ❌ not deployed | — | `eth_getCode` = `0x` |
| Optimism | 10 | ❌ not deployed | — | `eth_getCode` = `0x` |
| Polygon PoS | 137 | ❌ not deployed | — | `eth_getCode` = `0x` |

**Three things to internalise:**
1. **Lodestar = Arbitrum One, single deployment, and it is wound down** (every market mint/borrow-paused, collateral factor 0).
2. **Topics/selectors are Compound V2's** — reuse the Compound V2 set, but **only the 4-arg `AccrueInterest`** (`0x4dec04e7…`); the 3-arg variant never fires.
3. **No vanity addresses, no cross-chain address reuse to worry about** (one chain). The only "reused-looking" address concern is the underlying USDC pair (native `0xaf88…` vs bridged `0xFF97…`) — two different markets.

---

## 6. Proxies

Lodestar predates EIP-1967 and inherits Compound V2's **two bespoke delegatecall-proxy patterns**. The standard EIP-1967 impl/admin/beacon slots (`0x3608…bbc` / `0xb531…6103` / `0xa3f0…3d50`) are **all empty (`0x`)** on every Lodestar contract — confirmed live on the Unitroller, the lToken delegators, the Comptroller impl, the oracle, and the LODE token. Do not probe the EIP-1967 slot; read the typed getters.

| Contract | Pattern | Read current impl | Upgrade auth / event |
|----------|---------|-------------------|----------------------|
| **Comptroller** | `Unitroller` — storage contract; `fallback` delegatecalls `comptrollerImplementation`. Impl in a plain storage var (NOT EIP-1967). | `comptrollerImplementation()` → `0xbb82aa5e` (live = `0xe64e44c9…`) | Two-step: `_setPendingImplementation` → impl `_become(unitroller)`. **Emits `NewImplementation` (`0xd604de94…`).** Auth = the Safe `0xeD09…34dD`. |
| **lToken markets (all 15)** | `LErc20Delegator` / `LEtherDelegator` — `fallback` delegatecalls a per-market `implementation`. Plain storage var. | `implementation()` → `0x5c60da1b` (per-market delegate, see §3.2) | `_setImplementation(impl, allowResign, becomeData)` → `0x555bcc40`. **Emits `NewImplementation` (`0xd604de94…`).** Auth = the Safe (each lToken's `admin` = `0xeD09…34dD`). |
| **PriceOracle** | **Not a delegatecall proxy** — replaceable pointer held by the Comptroller (`oracle()`). | n/a (read `Comptroller.oracle()`) | Swapped via Comptroller `_setPriceOracle`; **emits `NewPriceOracle` (`0xd52b2b9b…`)**. |
| **admin (governance)** | **Gnosis Safe v1.3.0 proxy** (`GnosisSafeProxy`; singleton `0x3e5c63644e683549055b9be8653de26e0b4cd36e`, threshold 3). | Safe `getThreshold()`/`getOwners()` | Safe owner set; not a Compound proxy. |
| **LODE token** | **Immutable** (no proxy; EIP-1967 slot empty). | n/a | Not upgradeable. |

**Detection:** to get the live Comptroller logic call `comptrollerImplementation()` on the Unitroller; to get an lToken's live logic call `implementation()` on the lToken (this works on all 15 markets including lETH — Lodestar's lETH is a delegator, unlike Compound's immutable `CEther`). Neither lives at the EIP-1967 slot. **The single upgrade topic to watch is `NewImplementation` `0xd604de94…`** (Unitroller for Comptroller swaps, each lToken for its own logic) — there is no ERC-1967 `Upgraded`.

---

## 7. Decimals & math (same as Compound V2)

- lToken shares: **8 decimals**, independent of the underlying.
- `exchangeRateStored` scaled `1e(18 − 8 + underlyingDecimals)`; underlying = `lTokenAmount × exchangeRateStored / 1e18` (with that scaling).
- Rates are **per block** (`supplyRatePerBlock`/`borrowRatePerBlock`); `accrualBlockNumber` is a block number. Annualise with Arbitrum blocks/year — but note Arbitrum's "block number" tracks an L2 sequencer clock, so rate-period assumptions baked into the IRM are nominal.
- `closeFactor = 0.5e18` (≤ 50 % of a debt repayable per liquidation); `liquidationIncentive = 1.08e18` (8 % collateral bonus). Both currently moot — the protocol is paused.
- `getUnderlyingPrice` returns a mantissa scaled to `36 − underlyingDecimals`; it **reverts** for stale-feed markets.

---

## 8. Verification & sources

**Methodology (all on-chain, 2026-06-08, Arbitrum block ~471,350,000):**
- **Topics + selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` (pycryptodome). Cross-checked against the live Comptroller-impl bytecode (`0xe64e44c9…`, all Comptroller topics present) and the live lToken delegate bytecode (`0x254936…` lUSDC, `0xf96bc5…` lETH, `0x3bbfbe…` lplvGLP): **the 4-arg `AccrueInterest` topic is present in every delegate, the 3-arg topic is absent.** Live `eth_getLogs` on lETH (≈ block 371,342,666) returned `AccrueInterest` (`0x4dec04e7…`, **128-byte data = 4×uint256**), `Redeem` (`0xe5b754fb…`, 96-byte data), and `Transfer`; live lUSDC log returned `Mint` (`0x4c209b5f…`, 96-byte data); the Unitroller returned `DistributedSupplierComp`/`DistributedBorrowerComp` and both `ActionPaused` overloads. (`Borrow`/`RepayBorrow`/`LiquidateBorrow` were not re-observed live in the sampled windows because the protocol is paused/low-activity, but their topic0s are the canonical Compound V2 values and the events exist in the delegate logic.)
- **Addresses:** `getAllMarkets()` on the Unitroller returned exactly the 15 lTokens in §3.2; each lToken's `symbol`/`name`/`decimals`/`underlying`/`implementation`/`interestRateModel`/`comptroller`/`admin` read live; every underlying token symbol+decimals decoded on-chain. All addresses `eth_getCode`-verified non-empty on Arbitrum.
- **Proxy classification:** EIP-1967 impl/admin/beacon slots read live (`eth_getStorageAt`) on the Unitroller, an lToken delegator, the Comptroller impl, the oracle, and LODE — **all empty**, confirming the Compound delegator pattern (not ERC-1967). The governance admin's Safe singleton (`0x3e5c…d36e`, threshold 3) read from storage slot 0 + `getThreshold()`; `VERSION()` = "1.3.0". The pauseGuardian has no code (EOA).
- **Operational status:** `mintGuardianPaused`/`borrowGuardianPaused` = true and `markets().collateralFactor` = 0 for every market; `closeFactor` = 0.5e18, `liquidationIncentive` = 1.08e18 read live; oracle `getUnderlyingPrice` reverts `"Price not fresh"` for lUSDC and lplvGLP, returns 1e18 for lETH.
- **Absence:** `eth_getCode(0xa86DD95c…)` returns `0x` on Ethereum, Base, BNB, Avalanche, Optimism, and Polygon PoS.

**Authoritative sources:** [`compound-finance/compound-protocol`](https://github.com/compound-finance/compound-protocol) (CToken / Comptroller / Unitroller / CErc20Delegator semantics, byte-for-byte forked); Lodestar Finance docs (`docs.lodestarfinance.io`) and GitHub (`LodestarFinance`); Arbiscan for the deployed contracts; on-chain reads via the Arbitrum One public RPC.

### Independent fact-check (2026-06-08)

| Claim | Method | Verdict |
|-------|--------|---------|
| Lodestar is Arbitrum-only; absent on the other 6 requested chains | `eth_getCode` on the Unitroller on all 7 chains | **Confirmed** — non-empty on Arbitrum, `0x` on the other six |
| `AccrueInterest` is the **4-arg** variant, not the 3-arg | delegate bytecode scan (3-arg absent / 4-arg present) **+** live lETH log with 128-byte data | **Confirmed** |
| Accrual is **per block** (not timestamp like Moonwell) | `accrualBlockNumber()` + `supplyRatePerBlock()` present in delegate bytecode | **Confirmed** |
| Proxies are Compound **delegators, NOT EIP-1967** | EIP-1967 impl/admin/beacon slots all `0x` on Unitroller, lToken, impl, oracle, LODE | **Confirmed** |
| Protocol is **frozen / wound down** post-exploit | live `mintGuardianPaused`=true, `borrowGuardianPaused`=true, `collateralFactor`=0 on all 15 markets | **Confirmed** |
| Suffered a **Dec-2022 plvGLP oracle-manipulation exploit** | `lplvGLP` market still listed but paused, CF 0; underlying confirmed = `plvGLP` (`0x5326…CFF1`); oracle reverts "Price not fresh" | **Confirmed** (on-chain residue consistent with the public exploit record) |
| Governance = a **3-of-N Gnosis Safe** (not a Compound Timelock) | Safe singleton in slot 0, `getThreshold()`=3, `VERSION()`="1.3.0"; Timelock `delay()` reverts | **Corrected** — it is a Safe multisig, not a `Timelock` |
| pauseGuardian is a contract | `eth_getCode` | **Corrected** — it is an **EOA** (no code) |
| 15 markets enumerated | `getAllMarkets()` returned 15 lTokens, all live | **Confirmed** |

---

## 9. Detection invariants & gotchas

1. **Arbitrum One only, and the whole protocol is paused.** One Unitroller (`0xa86DD95c…`), 15 lTokens, all mint/borrow-paused with collateral factor 0. Off Arbitrum there is nothing (§4). Any live event today is residual repay/redeem/liquidation/admin, not organic growth.
2. **It's a Compound V2 fork** — `Mint`/`Redeem`/`Borrow`/`RepayBorrow`/`LiquidateBorrow`/`Transfer` topics and selectors are identical to [compound/v2.md](../compound/v2.md). Reuse that set.
3. **Only the 4-arg `AccrueInterest` fires** (`0x4dec04e7…`, 128-byte data). The 3-arg `0x875352fb…` **never** fires on Lodestar — do not index it. Accrual is per block (`accrualBlockNumber`/`supplyRatePerBlock`), so do not apply Moonwell's timestamp accessors.
4. **`Failure` is a silent no-op signal.** A `mint`/`borrow`/`redeem`/`liquidate` tx emitting `Failure(error,info,detail)` (`0x45b9…9aa0`, from an lToken or the Comptroller) **did not move funds** (legacy error-code convention returns instead of reverting). Especially relevant now: a borrow/mint against a paused market returns/reverts rather than succeeding.
5. **`Mint`/`Redeem`/`Borrow`/`RepayBorrow`/`LiquidateBorrow` are NOT indexed** — all fields in `data`. Filter by lToken address + topic0. `Mint` topic0 collides with Uniswap-V2 `Mint` — disambiguate by emitter.
6. **lETH is the LEther market** (`0x2193c45…`): `underlying()` reverts; uses payable `mint()` (`0x1249c58b`) / `repayBorrow()` (`0x4e4d9fea`) / `liquidateBorrow(address,address)` (`0xaae40a2a`). Detection code that always calls `underlying()` or `mint(uint256)` will revert on lETH. Unlike Compound's immutable `CEther`, **Lodestar's lETH is a delegator** — `implementation()` works on it.
7. **The plvGLP market is the exploited one.** `lplvGLP` (`0xeA0a73c1…`, underlying plvGLP `0x5326…CFF1`) was the December-2022 oracle-manipulation vector. It remains listed but paused with CF 0; treat it as deprecated.
8. **The oracle reverts `"Price not fresh"`.** `getUnderlyingPrice` reverts on stale/disabled markets (lUSDC, lplvGLP observed; lETH returns 1e18). Health-factor / liquidation logic that assumes a live price will throw — handle the revert. This is a hardened staleness guard, not a bug.
9. **`NewImplementation` (`0xd604de94…`) is the upgrade signal** — fired by the Unitroller on a Comptroller logic swap and by any lToken on its own logic swap (same topic0; key on emitter). There is **no ERC-1967 `Upgraded`** event. `NewPriceOracle` (`0xd52b2b9b…`) signals an oracle swap; `NewPauseGuardian`/`ActionPaused`/`NewCollateralFactor`/`NewBorrowCap`/`NewSupplyCap` are the other admin-action topics worth watching.
10. **Governance = a 3-of-N Gnosis Safe** (`0xeD09…34dD`), which is `admin` of the Unitroller and every lToken. The **pauseGuardian is a separate EOA** (`0x8cE938fC…`) that can pause independently. Admin-action monitoring watches Safe-originated calls + the topics in §9.9.
11. **Two USDC markets.** lUSDC (native USDC `0xaf88…`) vs lUSDC.e (bridged USDC.e `0xFF97…`) — distinct lTokens, distinct underlyings, distinct IRMs. lUSDT's underlying is **USDT0** (`0xFd08…`), not legacy USDT.
12. **Rewards = LODE, via Compound's comp machinery.** `DistributedSupplierComp`/`DistributedBorrowerComp` and the `claimComp(...)` selectors keep the Compound "Comp" names but distribute the **LODE** token (`0xF195…b8DB`). Accrual is pull-based; LODE is not auto-sent on supply/borrow.
13. **`onBehalfOf`-style attribution.** `LiquidateBorrow.liquidator` ≠ `tx.from` in general; `RepayBorrow` carries both `payer` and `borrower`. Attribute positions to the event's `borrower`/`minter`/`redeemer`, not the sender — routers and liquidation bots are common.
14. **Liquidation = `LiquidateBorrow` on the debt lToken + `seize`/`Transfer` on the collateral lToken** in one tx. Seize (`0xb2a02ff1`) moves collateral shares to the liquidator at `liquidationIncentiveMantissa`.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; Compound V2 fork — 4-arg AccrueInterest only) =====
-- lToken money-market
TOPIC_LT_ACCRUE_INTEREST_4ARG = '\x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04'
TOPIC_LT_MINT                 = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'
TOPIC_LT_REDEEM               = '\xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929'
TOPIC_LT_BORROW               = '\x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'
TOPIC_LT_REPAY_BORROW         = '\x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1'
TOPIC_LT_LIQUIDATE_BORROW     = '\x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
TOPIC_LT_RESERVES_ADDED       = '\xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5'
TOPIC_LT_RESERVES_REDUCED     = '\x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e'
TOPIC_LT_NEW_IMPLEMENTATION   = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'
TOPIC_LT_FAILURE              = '\x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0'
-- ERC-20 (lToken share + LODE)
TOPIC_ERC20_TRANSFER          = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_ERC20_APPROVAL          = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
-- Comptroller / Unitroller
TOPIC_MARKET_LISTED           = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_MARKET_ENTERED          = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'
TOPIC_MARKET_EXITED           = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_NEW_COLLATERAL_FACTOR   = '\x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5'
TOPIC_NEW_PRICE_ORACLE        = '\xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22'
TOPIC_NEW_PAUSE_GUARDIAN      = '\x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e'
TOPIC_ACTION_PAUSED_GLOBAL    = '\xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0'
TOPIC_ACTION_PAUSED_MARKET    = '\x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0'
TOPIC_NEW_BORROW_CAP          = '\x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6'
TOPIC_NEW_SUPPLY_CAP          = '\x9e0ad9cee10bdf36b7fbd38910c0bdff0f275ace679b45b922381c2723d676f8'
TOPIC_DISTRIB_SUPPLIER_COMP   = '\x2caecd17d02f56fa897705dcc740da2d237c373f70686f4e0d9bd3bf0400ea7a'
TOPIC_DISTRIB_BORROWER_COMP   = '\x1fc3ecc087d8d2d15e23d0032af5a47059c3892d003d8e139fdcb6bb327c99a6'
TOPIC_UNITROLLER_NEW_IMPL     = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'
TOPIC_NEW_PENDING_IMPL        = '\xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815'

-- ===== Selectors — lToken =====
SEL_LT_MINT                   = '\xa0712d68'   -- mint(uint256)  [LErc20]
SEL_LT_MINT_ETH               = '\x1249c58b'   -- mint()  [LEther, payable]
SEL_LT_REDEEM                 = '\xdb006a75'   -- redeem(uint256)
SEL_LT_REDEEM_UNDERLYING      = '\x852a12e3'   -- redeemUnderlying(uint256)
SEL_LT_BORROW                 = '\xc5ebeaec'   -- borrow(uint256)
SEL_LT_REPAY_BORROW           = '\x0e752702'   -- repayBorrow(uint256)
SEL_LT_REPAY_BORROW_ETH       = '\x4e4d9fea'   -- repayBorrow()  [LEther]
SEL_LT_REPAY_BEHALF           = '\x2608f818'   -- repayBorrowBehalf(address,uint256)
SEL_LT_LIQUIDATE              = '\xf5e3c462'   -- liquidateBorrow(address,uint256,address)
SEL_LT_LIQUIDATE_ETH          = '\xaae40a2a'   -- liquidateBorrow(address,address)  [LEther]
SEL_LT_SEIZE                  = '\xb2a02ff1'   -- seize(address,address,uint256)
SEL_LT_EXCHANGE_RATE_STORED   = '\x182df0f5'   -- exchangeRateStored()
SEL_LT_EXCHANGE_RATE_CURRENT  = '\xbd6d894d'   -- exchangeRateCurrent()
SEL_LT_BORROW_BAL_STORED      = '\x95dd9193'   -- borrowBalanceStored(address)
SEL_LT_GET_ACCOUNT_SNAPSHOT   = '\xc37f68e2'   -- getAccountSnapshot(address)
SEL_LT_UNDERLYING             = '\x6f307dc3'   -- underlying()  [absent on lETH]
SEL_LT_ACCRUAL_BLOCK_NUMBER   = '\x6c540baf'   -- accrualBlockNumber()
SEL_LT_SUPPLY_RATE_PER_BLOCK  = '\xae9d70b0'   -- supplyRatePerBlock()
SEL_LT_IMPLEMENTATION         = '\x5c60da1b'   -- implementation()
SEL_LT_SET_IMPLEMENTATION     = '\x555bcc40'   -- _setImplementation(address,bool,bytes)

-- ===== Selectors — Comptroller / Unitroller =====
SEL_ENTER_MARKETS             = '\xc2998238'   -- enterMarkets(address[])
SEL_EXIT_MARKET               = '\xede4edd0'   -- exitMarket(address)
SEL_GET_ALL_MARKETS           = '\xb0772d0b'   -- getAllMarkets()
SEL_MARKETS                   = '\x8e8f294b'   -- markets(address)
SEL_GET_ACCOUNT_LIQUIDITY     = '\x5ec88c79'   -- getAccountLiquidity(address)
SEL_ORACLE                    = '\x7dc0d1d0'   -- oracle()
SEL_MINT_GUARDIAN_PAUSED      = '\x731f0c2b'   -- mintGuardianPaused(address)
SEL_BORROW_GUARDIAN_PAUSED    = '\x6d154ea5'   -- borrowGuardianPaused(address)
SEL_CLAIM_COMP                = '\xe9af0292'   -- claimComp(address)  [claims LODE]
SEL_COMPTROLLER_IMPL          = '\xbb82aa5e'   -- comptrollerImplementation()
SEL_ADMIN                     = '\xf851a440'   -- admin()
SEL_GET_UNDERLYING_PRICE      = '\xfc57d4df'   -- getUnderlyingPrice(address)  [oracle]

-- ===== Arbitrum One addresses (chain ID 42161) =====
ARB_UNITROLLER                = '\xa86dd95c210dd186fa7639f93e4177e97d057576'   -- Comptroller proxy
ARB_COMPTROLLER_IMPL          = '\xe64e44c97f9a019f70f8cdb3f4d3d465c56e9ab2'
ARB_PRICE_ORACLE              = '\xccf9393df2f656262fd79599175950fab4d4ec01'
ARB_ADMIN_SAFE                = '\xed093f9720b2507c9b54fc117ecb2618910734dd'   -- Gnosis Safe 3-of-N
ARB_PAUSE_GUARDIAN            = '\x8ce938fcd4e2be078d8cdc71a63979848e131236'   -- EOA
ARB_LODE                      = '\xf19547f9ed24aa66b03c3a552d181ae334fbb8db'
-- lToken markets
ARB_LPLVGLP                   = '\xea0a73c17323d1a9457d722f10e7bab22dc0cb83'   -- exploited collateral
ARB_LUSDC                     = '\x4c9aaed3b8c443b4b634d1a189a5e25c604768de'   -- native USDC
ARB_LETH                      = '\x2193c45244af12c280941281c8aa67dd08be0a64'   -- LEther
ARB_LDPX                      = '\x5d27cff80df09f28534bb37d386d43aa60f88e25'
ARB_LFRAX                     = '\xd12d43cdf498e377d3bfa2c6217f05b466e14228'
ARB_LMAGIC                    = '\xf21ef887cb667f84b8ec5934c1713a7ade8c38cf'
ARB_LWBTC                     = '\xc37896bf3ee5a2c62cdbd674035069776f721668'
ARB_LDAI                      = '\x4987782da9a63bc3abace48648b15546d821c720'
ARB_LARB                      = '\x8991d64fe388fa79a4f7aa7826e8da09f0c3c96a'
ARB_LWSTETH                   = '\xfece754d92bd956f681a941cef4632ab65710495'
ARB_LGMX                      = '\x79b6c5e1a7c0ad507e1db81ec7cf269062bab4eb'
ARB_LUSDT                     = '\x9365181a7df82a1cc578eae443efd89f00dbb643'   -- USDT0
ARB_LUSDCE                    = '\x1ca530f02dd0487cef4943c674342c5aea08922f'   -- bridged USDC.e
ARB_LMIM                      = '\x929cc7eba600ccb3faf5494210206c93219ccb28'
ARB_LPENDLE                   = '\x39c27dfdc9364a976926a820c8caa8fd035d0727'
```
