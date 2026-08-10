# Sonne Finance — Topics, Selectors, Addresses (Optimism + Base)

**Status:** verified against Optimism (10) and Base (8453) mainnet RPC and the Compound V2 reference design on 2026-06-08. Every topic0/selector computed locally with keccak and cross-checked against live `eth_getLogs`; every address `eth_getCode`-verified on the correct chain; proxy/immutability classified by reading the EIP-1967 slots and the Compound `implementation()` getter live. **Sonne Finance is a deprecated, wound-down protocol — see the exploit note below.**
**Scope:** the seven chains the user asked about — **Sonne Finance lending is deployed on only TWO of them: Optimism (chain 10) and Base (chain 8453).** It is **NOT deployed on Ethereum, BNB Smart Chain, Avalanche, Arbitrum, or Polygon PoS** (every Sonne address returns empty `eth_getCode` on those chains — except one address-collision decoy on BNB, see §8/§9). Topics and selectors are chain-agnostic; addresses are network-specific. Single file `core.md` — Sonne is a single-generation protocol (one Compound V2 fork, deployed twice).

> **⚠️ DEPRECATED / EXPLOITED — READ FIRST.** Sonne Finance suffered a **~$20M exploit on its BASE market on 2024-05-14** (the classic empty-market **donation / `exchangeRate` manipulation** on a freshly-listed, near-empty market — the attacker seeded a new market, donated underlying directly to inflate the exchange rate, then borrowed against rounding-inflated collateral). After the Base exploit the team **paused the protocol and wound it down**; the **Base deployment is effectively dead** and the **Optimism deployment was subsequently deprecated** as the project shut down. Treat **both** chains as **deprecated**: contracts are still on-chain and queryable, but markets are paused / drained / no longer maintained. Monitoring here is for **post-mortem / residual-activity / fund-recovery** purposes, not live protocol health. **The Base market especially is hostile ground** — assume any large `Mint`/`Redeem`/`AccrueInterest` swing on a low-cash Base market is the exploit signature, not organic use.

Sonne Finance is a **Compound V2 fork** with renamed types: cToken → **soToken** (per-market `so*` tokens — soWETH, soUSDC, soOP on Optimism; `sob*` tokens — sobUSDC, sobWETH, sobAERO on Base), Comptroller behind a **Unitroller** delegator proxy, a Compound-style `PriceOracle`, and per-market JumpRate interest-rate models. Three facts drive correct monitoring:

1. **4-arg `AccrueInterest`, not the 3-arg legacy form.** Sonne emits `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` (topic0 `0x4dec04e7…`) on **both** chains — the same 4-arg variant Moonwell uses, **not** stock Compound V2's 3-arg `AccrueInterest(uint256,uint256,uint256)` (`0x8753…6cb9`). Verified live: an Optimism soUSDC `AccrueInterest` log carries **128 bytes** of data (= 4×uint256), and the 3-arg topic produces **zero** logs. Index the 4-arg topic; do **not** scan for the 3-arg one.
2. **Two different soToken proxy patterns across the two chains — this is the #1 integration trap.** **Optimism soTokens are immutable `CErc20Immutable` contracts** (no proxy: the EIP-1967 impl slot is `0x0`, the Compound `implementation()` getter reverts, the market *is* its own logic). **Base soTokens are EIP-1967 proxies** (non-empty impl slot, each market delegating to its own separately-deployed-but-byte-identical logic contract, all under one shared ProxyAdmin). So the same protocol uses **`CErc20Immutable` on OP and an EIP-1967 transparent-proxy soToken on Base.** The Unitroller is a Compound **delegator** (not EIP-1967) on both chains.
3. **Compound's error-code convention + the `Failure` event still apply.** Many state-changing calls return a `uint` error code (0 = success) and emit `Failure(error, info, detail)` instead of reverting — a "successful" tx can be a silent no-op. Interest accrues on **`block.timestamp`** (per-second), not per block.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-08. `AccrueInterest(4-arg)`, `Mint`, `Borrow`, `Redeem`, `MarketEntered` additionally confirmed against live Optimism **and** Base logs (§ Verification). Topics are byte-for-byte the Compound V2 set (the renaming cToken→soToken does not change a single signature — event arg *types* are unchanged).

### 1.1 soToken (per-market; the workhorse money-market events)

Emitter = each `so*`/`sob*` market address (§3, §4). Events are **NOT indexed** — every field lives in `data`; filter by market address + topic0.

| topic0 | Event |
|--------|-------|
| `0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04` | `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` **(4-arg — the one Sonne uses on both chains)** |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address minter, uint256 mintAmount, uint256 mintTokens)` |
| `0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929` | `Redeem(address redeemer, uint256 redeemAmount, uint256 redeemTokens)` |
| `0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80` | `Borrow(address borrower, uint256 borrowAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1` | `RepayBorrow(address payer, address borrower, uint256 repayAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address liquidator, address borrower, uint256 repayAmount, address soTokenCollateral, uint256 seizeTokens)` |
| `0xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5` | `ReservesAdded(address benefactor, uint256 addAmount, uint256 newTotalReserves)` |
| `0x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e` | `ReservesReduced(address admin, uint256 reduceAmount, uint256 newTotalReserves)` |
| `0xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460` | `NewReserveFactor(uint256 oldReserveFactorMantissa, uint256 newReserveFactorMantissa)` |
| `0xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926` | `NewMarketInterestRateModel(address oldIRM, address newIRM)` |
| `0x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d` | `NewComptroller(address oldComptroller, address newComptroller)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` — soToken shares (8 decimals) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` — soft-fail; a "successful" tx that moved no funds |

> **3-arg `AccrueInterest` (`0x875352fb3fadeb8c0be7cbbe8ff761b308fa7033470cd0287f02f3436fd76cb9`) is NOT used by Sonne** — verified zero logs on the soUSDC market. Do not index it.

### 1.2 Comptroller (one per chain, behind a Unitroller delegator)

Emitter = the Unitroller proxy (`0x60CF…1C58` on OP, `0x1DB2…45F0` on Base).

| topic0 | Event |
|--------|-------|
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address soToken)` |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address soToken, address account)` |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address soToken, address account)` |
| `0x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9` | `NewCloseFactor(uint256 oldCloseFactorMantissa, uint256 newCloseFactorMantissa)` |
| `0x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5` | `NewCollateralFactor(address soToken, uint256 oldCFMantissa, uint256 newCFMantissa)` |
| `0xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316` | `NewLiquidationIncentive(uint256 oldIncentiveMantissa, uint256 newIncentiveMantissa)` |
| `0xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22` | `NewPriceOracle(address oldPriceOracle, address newPriceOracle)` |
| `0x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e` | `NewPauseGuardian(address oldPauseGuardian, address newPauseGuardian)` |
| `0xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0` | `ActionPaused(string action, bool pauseState)` — global (Transfer/Seize) |
| `0x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0` | `ActionPaused(address soToken, string action, bool pauseState)` — per-market (Mint/Borrow). **The wind-down pauses fire this.** |
| `0x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6` | `NewBorrowCap(address indexed soToken, uint256 newBorrowCap)` |
| `0xeda98690e518e9a05f8ec6837663e188211b2da8f4906648b323f2c1d4434e29` | `NewBorrowCapGuardian(address oldBorrowCapGuardian, address newBorrowCapGuardian)` |
| `0x2caecd17d02f56fa897705dcc740da2d237c373f70686f4e0d9bd3bf0400ea7a` | `DistributedSupplierComp(address indexed soToken, address indexed supplier, uint256 compDelta, uint256 compSupplyIndex)` — SONNE-reward distribution |
| `0x1fc3ecc087d8d2d15e23d0032af5a47059c3892d003d8e139fdcb6bb327c99a6` | `DistributedBorrowerComp(address indexed soToken, address indexed borrower, uint256 compDelta, uint256 compBorrowIndex)` |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` — also emitted by the Comptroller |

> Sonne keeps Compound's in-Comptroller reward accounting (`DistributedSupplier/BorrowerComp`, the COMP-machinery renamed to the SONNE token) — there is **no** separate MultiRewardDistributor (unlike Moonwell). Rewards are pulled via the Comptroller's `claimComp`-style entrypoint.

### 1.3 Unitroller (Comptroller proxy — admin/upgrade events)

| topic0 | Event |
|--------|-------|
| `0xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815` | `NewPendingImplementation(address oldPendingImplementation, address newPendingImplementation)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` — **the topic to watch for a Comptroller logic upgrade** |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |

### 1.4 PriceOracle (Compound-style; one per chain)

Sonne's price oracle is a Compound `PriceOracle` (symbol/feed-keyed). Its event surface is minimal and oracle-implementation-specific; the load-bearing read is `getUnderlyingPrice(soToken)` (§2.4). The Comptroller-level oracle swap is observable via `NewPriceOracle` (§1.2).

### 1.5 EIP-1967 proxy events (Base soTokens only)

Base soTokens are OpenZeppelin transparent proxies — admin/upgrade is observed via the standard EIP-1967 events on each soToken proxy:

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **the topic to watch for a Base soToken logic upgrade** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |

> These two are the canonical OZ proxy topics (recomputed locally). On Optimism the soTokens are immutable `CErc20Immutable`, so **no** `Upgraded`/`AdminChanged` ever fire there — an OP soToken logic change is impossible by construction.

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

Selectors recomputed locally 2026-06-08, verified against deployed bytecode on OP + Base. Interface `uint` canonicalized to `uint256`. Byte-for-byte the Compound V2 set (renaming does not change signatures).

### 2.1 soToken (per-market) — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa0712d68` | `mint(uint256 mintAmount)` | Supply underlying, receive soTokens. Returns `uint` error code. Emits `Mint`+`AccrueInterest`+`Transfer`. |
| `0xdb006a75` | `redeem(uint256 redeemTokens)` | Burn soTokens for underlying. |
| `0x852a12e3` | `redeemUnderlying(uint256 redeemAmount)` | Redeem an exact underlying amount. |
| `0xc5ebeaec` | `borrow(uint256 borrowAmount)` | Emits `Borrow`. |
| `0x0e752702` | `repayBorrow(uint256 repayAmount)` | `type(uint256).max` repays full debt. |
| `0x2608f818` | `repayBorrowBehalf(address borrower, uint256 repayAmount)` | |
| `0xf5e3c462` | `liquidateBorrow(address borrower, uint256 repayAmount, address soTokenCollateral)` | Emits `LiquidateBorrow`. |
| `0xb2a02ff1` | `seize(address liquidator, address borrower, uint256 seizeTokens)` | Cross-market collateral seizure. |
| `0xa9059cbb` | `transfer(address dst, uint256 amount)` | soToken shares (8 decimals). |
| `0xa6afed95` | `accrueInterest()` | Emits 4-arg `AccrueInterest`. |
| `0xfca7820b` | `_setReserveFactor(uint256)` | Admin. Emits `NewReserveFactor`. |
| `0xf2b3abbd` | `_setInterestRateModel(address)` | Admin. Emits `NewMarketInterestRateModel`. |
| `0x601a0bf1` | `_reduceReserves(uint256)` | Admin reserve withdrawal — **watch during wind-down**. |

> **No `mint()` / `repayBorrow()` payable (CEther) selectors and no `liquidateBorrow(address,address)` (CEther) selector are needed:** the native-gas markets (soWETH on OP, sobWETH on Base) are **`CErc20`-style markets over wrapped WETH** (`underlying()` = `0x4200…0006`), **not** `CEther`. ETH is wrapped before `mint(uint256)`. Do not scan for `0x1249c58b`/`0x4e4d9fea`/`0xaae40a2a`.

### 2.2 soToken — views / accounting

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x182df0f5` | `exchangeRateStored()` | `uint` — cached soToken→underlying rate (scaled `1e(18-8+underlyingDecimals)`). **The exploit was an inflation of this value.** |
| `0xbd6d894d` | `exchangeRateCurrent()` | Accrues, then returns the rate (non-view). |
| `0x3b1d21a2` | `getCash()` | Underlying held by the market. A near-zero `getCash()` on a listed market is the exploit precondition. |
| `0xd3bd2c72` | `supplyRatePerTimestamp()` | **Per-second** supply mantissa (NOT per-block). |
| `0xcd91801c` | `borrowRatePerTimestamp()` | **Per-second** borrow mantissa. |
| `0xcfa99201` | `accrualBlockTimestamp()` | **Unix timestamp** of last accrual (NOT block number). |
| `0x47bd3718` / `0x8f840ddd` / `0xaa5af0fd` | `totalBorrows()` / `totalReserves()` / `borrowIndex()` | |
| `0x95dd9193` / `0x17bfdfbc` | `borrowBalanceStored(address)` / `borrowBalanceCurrent(address)` | Cached / accrue-then-read debt. |
| `0xc37f68e2` | `getAccountSnapshot(address)` | `(uint err, uint soTokenBalance, uint borrowBalance, uint exchangeRateMantissa)` |
| `0x3af9e669` | `balanceOfUnderlying(address)` | Non-view; `balanceOf × exchangeRateCurrent`. |
| `0x6f307dc3` | `underlying()` | Underlying ERC-20. Present on **every** Sonne market incl. the WETH market. |
| `0x5fe3b567` | `comptroller()` | Returns the Unitroller address. |
| `0xf3fdb15a` | `interestRateModel()` | Per-market JumpRateModel (§3.3/§4.3). |
| `0x173b9904` | `reserveFactorMantissa()` | |
| `0x5c60da1b` | `implementation()` | **Reverts on OP (immutable `CErc20Immutable`).** On Base soTokens it also reverts (they are EIP-1967 proxies, not Compound delegators) — read the **EIP-1967 impl slot** instead (§8). |
| `0x70a08231`/`0x18160ddd`/`0x313ce567`/`0x95d89b41`/`0x06fdde03` | `balanceOf`/`totalSupply`/`decimals`/`symbol`/`name` | soTokens: **8 decimals**; `symbol()`=`so*` (OP) / `sob*` (Base). |

### 2.3 Comptroller (behind the Unitroller)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc2998238` | `enterMarkets(address[] soTokens)` | Use markets as collateral. Emits `MarketEntered`. |
| `0xede4edd0` | `exitMarket(address soToken)` | Emits `MarketExited`. |
| `0xabfceffc` | `getAssetsIn(address account)` | `address[]` — markets entered. |
| `0x8e8f294b` | `markets(address soToken)` | `(bool isListed, uint collateralFactorMantissa, bool isComped)` |
| `0x929fe9a1` | `checkMembership(address account, address soToken)` | `bool` |
| `0x5ec88c79` | `getAccountLiquidity(address account)` | `(uint err, uint liquidity, uint shortfall)` — shortfall>0 ⇒ liquidatable. |
| `0xb0772d0b` | `getAllMarkets()` | `address[]` — **OP = 13, Base = 7** (verified live 2026-06-08). Re-read rather than hardcoding. |
| `0x7dc0d1d0` | `oracle()` | The Sonne PriceOracle. |
| `0xe8755446` | `closeFactorMantissa()` | `0.5e18` on both chains (verified). |
| `0x4ada90af` | `liquidationIncentiveMantissa()` | `1.08e18` (OP, verified). |
| `0x4a584432` | `borrowCaps(address)` | Per-market cap. |
| `0xbb82aa5e` | `comptrollerImplementation()` | **Read this on the Unitroller for the live Comptroller logic** (Compound delegator storage, NOT EIP-1967). |
| `0xf851a440` | `admin()` | The governance Timelock (§8). |
| `0xa76b3fda` | `_supportMarket(address)` | Admin. Emits `MarketListed`. **The exploit began with a fresh `_supportMarket`.** |
| `0xe4028eee` | `_setCollateralFactor(address,uint256)` | Admin. Emits `NewCollateralFactor`. |
| `0x55ee1fe1` | `_setPriceOracle(address)` | Admin. Emits `NewPriceOracle`. |
| `0xe9af0292` | `claimComp(address)` | SONNE-reward claim (Compound naming retained). |

### 2.4 PriceOracle

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfc57d4df` | `getUnderlyingPrice(address soToken)` | Comptroller pricing entry point. Returns a price mantissa scaled to `36 − underlyingDecimals`. |

### 2.5 Unitroller (delegator admin)

| Selector | Signature |
|----------|-----------|
| `0xe992a041` | `_setPendingImplementation(address)` |
| `0xc1e80334` | `_acceptImplementation()` — emits `NewImplementation` |

---

## 3. Addresses — Optimism (chain ID 10)  *[the original deployment — immutable soTokens]*

All verified via `eth_getCode` (non-empty) on `https://optimism-rpc.publicnode.com`, 2026-06-08. Unitroller wiring confirmed live: `comptrollerImplementation()`→ Comptroller impl, `oracle()`→ PriceOracle, `admin()`→ Timelock, `getAllMarkets()`=13. **Now deprecated (project wound down).**

### 3.1 Core system

| Role | Address | One-liner |
|------|---------|-----------|
| **UNITROLLER** (Comptroller proxy) | `0x60CF091cD3f50420d50fD7f707414d0DF4751C58` | The risk engine; emits §1.2 events. `comptrollerImplementation()`→ impl; `oracle()`→ PriceOracle; `getAllMarkets()`=13. Point all market-policy monitors here. Compound **delegator** (not EIP-1967). |
| COMPTROLLER (impl) | `0xe8FF1489227Fa74F77E49C688903E69e1583c03F` | Comptroller logic behind the Unitroller (47,076-char bytecode). Read live via `comptrollerImplementation()`. |
| **PriceOracle** | `0x22c7E5cE392Bc951F63B68a8020B121A8e1c0fEA` | Sonne PriceOracle; `getUnderlyingPrice(soToken)`. |
| **Timelock** (`admin`) | `0x37ff10390f22fABDc2137E428a6E6965960D60b6` | OpenZeppelin TimelockController — `admin` of the Unitroller **and** every OP soToken. `getMinDelay()` = **172800 (2 days)**. Governance/admin actions originate here. |

### 3.2 soToken markets (13) — immutable `CErc20Immutable`, **8 decimals**, symbol `so*`

soToken addresses cannot be derived (each is a separately-deployed `CErc20Immutable`, not a CREATE2 clone) — enumerate via `getAllMarkets()`. **`implementation()` reverts and the EIP-1967 slot is `0x0` on every one of these — they are immutable and are their own logic.**

| soToken | Address | Underlying | Underlying addr | IRM |
|---------|---------|-----------|-----------------|-----|
| soWETH | `0xf7B5965f5C117Eb1B5450187c9DcFccc3C317e8E` | WETH | `0x4200000000000000000000000000000000000006` | `0xbBbD…13c6` |
| soUSDC | `0xEC8FEa79026FfEd168cCf5C627c7f486D77b765F` | USDC.e (bridged, 6d) | `0x7F5c764cBc14f9669B88837ca1490cCa17c31607` | `0xbBbD…13c6` |
| soUSDT | `0x5Ff29E4470799b982408130EFAaBdeeAE7f66a10` | USDT (6d) | `0x94b008aA00579c1307B0EF2c499aD98a8ce58e58` | `0xbBbD…13c6` |
| soDAI | `0x5569b83de187375d43FBd747598bfe64fC8f6436` | DAI | `0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1` | `0xbBbD…13c6` |
| soOP | `0x8cD6b19A07d754bF36AdEEE79EDF4F2134a8F571` | OP | `0x4200000000000000000000000000000000000042` | `0x3F6f…631e` |
| soSUSD | `0xd14451E0Fa44B18f08aeb1E4a4d092B823Caca68` | sUSD | `0x8c6f28f2F1A3C87F0f938b96d27520d9751ec8d9` | `0xbBbD…13c6` |
| soSNX | `0xD7dAabd899D1fAbbC3A9ac162568939CEc0393Cc` | SNX | `0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4`† | `0x7320…741e` |
| soWBTC | `0x33865E09A572d4F1CC4d75Afc9ABcc5D3d4d867D` | WBTC (8d) | `0x68f180fcCe6836688e9084f035309E29Bf0A2095` | `0x3F6f…631e` |
| soLUSD | `0xAFdf91f120DEC93c65fd63DBD5ec372e5dcA5f82` | LUSD | `0xc40F949F8a4e094D1b49a23ea9241D289B7b2819` | `0xbBbD…13c6` |
| sowstETH | `0x26AaB17f27CD1c8d06a0Ad8E4a1af8B1032171d5` | wstETH | `0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb` | `0x3F6f…631e` |
| soMAI | `0xE7De932d50EfC9ea0a7a409Fc015b4f71443528e` | MAI (miMATIC) | `0xdFA46478F9e5EA86d57387849598dbFB2e964b02` | `0x3F6f…631e` |
| soUSDCnative | `0x1AfD1ff9e441973b7D34c7B8Abe91d94f1B23ce0` | USDC (native, 6d) | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` | `0xbBbD…13c6` |
| soVELO | `0xE3b81318B1b6776F0877c3770AFDdFF97b9f5fE5` | VELO | `0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db` | `0x7320…741e` |

† `soSNX.underlying()` reads `0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4` (live on OP: `symbol()`=`SNX`, `name()`=`Synthetix Network Token`) — note the last byte is `b4`, not `04`. All underlyings `eth_getCode`-confirmed live.

### 3.3 Interest rate models (Optimism)

Shared JumpRateModels across markets (read each market's live `interestRateModel()`):

| IRM address | Used by |
|-------------|---------|
| `0xbBbD75383f6a61D5eb5B43E94e6372df6F7f13c6` | soWETH, soUSDC, soUSDT, soDAI, soSUSD, soLUSD, soUSDCnative (stable/ETH) |
| `0x3F6fb832279ac7DB0b4F92b79cbb8df03702631e` | soOP, soWBTC, sowstETH, soMAI |
| `0x7320bD5fa56F8a7ea959a425f0c0b8caC56f741e` | soSNX, soVELO |

---

## 4. Addresses — Base (chain ID 8453)  *[the EXPLOITED deployment — EIP-1967-proxy soTokens]*

All verified via `eth_getCode` (non-empty) on `https://base-rpc.publicnode.com`, 2026-06-08. Unitroller wiring confirmed live: `getAllMarkets()`=7, `oracle()`→ PriceOracle, `admin()`→ Timelock. **This is the deployment that was exploited for ~$20M on 2024-05-14 and then paused / wound down. Treat as dead.**

### 4.1 Core system

| Role | Address | One-liner |
|------|---------|-----------|
| **UNITROLLER** (Comptroller proxy) | `0x1DB2466d9F5e10D7090E7152B68d62703a2245F0` | The risk engine; emits §1.2 events. `getAllMarkets()`=7. Compound **delegator** (not EIP-1967). **Same-address decoy on BNB — see §8/§9.** |
| COMPTROLLER (impl) | `0x076c7883e154f6CC0cA04888288b350D78cF1321` | Comptroller logic (47,076-char bytecode; same era as OP). |
| **PriceOracle** | `0x807FBC283805d4aaee7CD6a6c1f98000c3F51C9b` | Sonne PriceOracle on Base. |
| **Timelock** (`admin`) | `0x81077d101293Eca45114af55a63897CeC8732fD3` | OpenZeppelin TimelockController — `admin` of the Unitroller and every Base soToken, **and** owner of the soToken ProxyAdmin. `getMinDelay()` = **86400 (1 day)**. |
| **soToken ProxyAdmin** (EIP-1967) | `0xb19bD9fc8fa8F00599A04115193b915E1929BC5f` | The shared OZ `ProxyAdmin` that owns/upgrades all 7 Base soToken proxies. `owner()` = the Timelock above. **Upgrade authority for every Base soToken.** |

### 4.2 soToken markets (7) — EIP-1967 transparent proxies, **8 decimals**, symbol `sob*`

Each soToken is an **EIP-1967 transparent proxy** (impl in the standard slot, non-empty; admin = the shared ProxyAdmin `0xb19b…BC5f`). Each market delegates to its **own** logic contract (distinct address per market, but all byte-identical, 31,338-char bytecode). Read the live impl from the EIP-1967 slot, never `implementation()` (which reverts here).

| soToken (proxy) | Address | Underlying | Underlying addr | EIP-1967 impl | IRM |
|-----------------|---------|-----------|-----------------|---------------|-----|
| sobDAI | `0xb864BA2aab1f53BC3af7AE49a318202dd3fd54C2` | DAI | `0x50c5725949A6F0c72E6c4a641F24049A917DB0Cb` | `0xa6082A68d6378dA0Eea5446881A964dcB75E2094` | `0x9Eff…69b1` |
| sobUSDbC | `0x225886C9beb5eEE254F79d58bbD80cf9F200D4d0` | USDbC (bridged, 6d) | `0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA` | `0x608Dad78cB92dEd86dEE9b014437957F67A3f6b1` | `0x9Eff…69b1` |
| sobWETH | `0x5F5c479fe590cD4442A05aE4a941dd991A633B8E` | WETH | `0x4200000000000000000000000000000000000006` | `0x00e29Cf7d7aA0Dd9d1FCacd5189d3AB9eCDcd85A` | `0x93dD…0fEf` |
| sobUSDC | `0xfd68F92B45b633bbe0f475294C1A86AEcd62985A` | USDC (native, 6d) | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | `0xa02Fc37e2d25d3abe617C6A8a92ACced5e3e6139` | `0x9Eff…69b1` |
| sobcbETH | `0x6c91BeECEEDda2089307FAB818E12757948BF489` | cbETH | `0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cF0DEc22` | `0x38D0A612a4851FB220E6793d6a08096485Bf267a` | `0x93dD…0fEf` |
| sobwstETH | `0x7A6468053CDcD7e8Fe507D7eDB77336F5057D206` | wstETH | `0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452` | `0xC0915a1F9CA495dD138cb467A4E6901d5D64A16e` | `0x93dD…0fEf` |
| sobAERO | `0xfA78196acE4048C4cCce6D3d97890d7B6c8f59dA` | AERO | `0x940181a94A35A4569E4529A3CDfB74e38FD98631` | `0xF711761697cf945BFd2D128b12cb418d11e287c5` | `0x17063…0eD7` |

### 4.3 Interest rate models (Base)

| IRM address | Used by |
|-------------|---------|
| `0x9Eff321DDf8AB509c8C65f7e57289258E9c169b1` | sobDAI, sobUSDbC, sobUSDC (stables) |
| `0x93DDa3095C0f435FD3590500140e8449a7600fEf` | sobWETH, sobcbETH, sobwstETH (ETH/LSTs) |
| `0x17063AD4e83b0aBa4ca0f3fC3a9794e807A00ed7` | sobAERO |

---

## 5. Chains with NO Sonne deployment

**Ethereum (1), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Polygon PoS (137): Sonne Finance is NOT deployed.** Confirmed by `eth_getCode` returning empty (`0x`) for the OP Unitroller, Base Unitroller, and a representative soToken on every one of these five chains — **with one false-positive that is NOT Sonne:** on **BNB**, the literal address of the **Base Unitroller** (`0x1DB2466d…45F0`) **does** carry bytecode (4,102 chars), but it is an **unrelated contract** — none of the Comptroller selectors (`getAllMarkets`/`comptrollerImplementation`/`admin`) respond (all revert), the bytecode length differs from the real 3,008-char Unitroller, and the EIP-1967 slot is empty. It is an **address collision** (a different contract deployed by the same EOA at the same nonce on BNB), **not a Sonne deployment.** Do not author Sonne monitors on any of these five chains.

---

## 6. Decimals & math (same as Compound V2)

- **soTokens have 8 decimals** on both chains, independent of the underlying. Underlying value = `soTokenAmount × exchangeRateStored / 1e18`, where `exchangeRateStored` itself is scaled by `1e(18 − 8 + underlyingDecimals)`.
- Rates are **per-second** (`supplyRatePerTimestamp`/`borrowRatePerTimestamp`), accrual keyed on `block.timestamp` (`accrualBlockTimestamp`). **There is no `supplyRatePerBlock`/`borrowRatePerBlock`/`accrualBlockNumber`** — those revert.
- `getAccountLiquidity` returns `(err, liquidity, shortfall)`; **shortfall > 0 ⇒ liquidatable**.
- Oracle prices are mantissas scaled to `36 − underlyingDecimals` (Compound convention).
- `closeFactor` = 0.5e18, `liquidationIncentive` = 1.08e18 (verified).

---

## 7. Cross-chain summary

| Chain | ID | Sonne lending? | Unitroller | soToken proxy model | Markets | Status |
|-------|----|----------------|------------|---------------------|---------|--------|
| **Optimism** | 10 | ✅ (original) | `0x60CF091cD3f50420d50fD7f707414d0DF4751C58` | immutable `CErc20Immutable` | 13 | deprecated (wound down) |
| **Base** | 8453 | ✅ (exploited) | `0x1DB2466d9F5e10D7090E7152B68d62703a2245F0` | EIP-1967 transparent proxy | 7 | **exploited 2024-05-14, dead** |
| Ethereum | 1 | ❌ | — | — | 0 | not deployed |
| BNB | 56 | ❌ (decoy address only) | — | — | 0 | **not Sonne** (address collision at `0x1DB2…45F0`) |
| Avalanche | 43114 | ❌ | — | — | 0 | not deployed |
| Arbitrum | 42161 | ❌ | — | — | 0 | not deployed |
| Polygon | 137 | ❌ | — | — | 0 | not deployed |

**Three things to internalize:**
1. **Sonne = Optimism + Base only, and both are deprecated.** Optimism is the original; Base is the exploited one.
2. **The two chains use DIFFERENT soToken proxy models** — immutable on OP, EIP-1967 proxy on Base. Key proxy detection on `(chainId, address)`.
3. **No cross-chain address reuse** between the two real deployments (every contract is independent); the only "shared" address is the BNB decoy that collides with the Base Unitroller literal and is **not** Sonne.

---

## 8. Proxies (old & new)

| Contract | Chain | Pattern | Detection | Upgrade auth |
|----------|-------|---------|-----------|--------------|
| **Unitroller** (Comptroller) | OP + Base | Compound **delegator** (NOT EIP-1967): storage contract; `fallback` delegatecalls `comptrollerImplementation` stored in a plain storage var. | `comptrollerImplementation()` (`0xbb82aa5e`); EIP-1967 impl slot is `0x0`. | `_setPendingImplementation`→`_acceptImplementation`; emits `NewImplementation` (`0xd604de94…`). Authorized by the Timelock `admin`. |
| **soTokens** | **Optimism** | **None — immutable `CErc20Immutable`.** | `implementation()` (`0x5c60da1b`) **reverts**; EIP-1967 impl slot = `0x0` (verified on soWETH/soUSDC/soUSDCnative). | **Not upgradeable.** A revert from `implementation()` here means "immutable", not "detection failed". |
| **soTokens** | **Base** | **EIP-1967 transparent proxy** (one logic per market, all byte-identical). | EIP-1967 impl slot (`0x3608…bbc`) **non-empty** (e.g. sobUSDC → `0xa02Fc37e…6139`); EIP-1967 admin slot (`0xb531…6103`) = the shared ProxyAdmin `0xb19b…BC5f` on every market. `implementation()` (`0x5c60da1b`) reverts (not a Compound delegator). | OZ `ProxyAdmin` `0xb19b…BC5f` (owned by the Base Timelock). Emits `Upgraded(address)` (`0xbc7cd75a…`) on the soToken. |
| **PriceOracle** | OP + Base | Plain contract (replaceable Comptroller pointer). | EIP-1967 impl slot = `0x0`; swapped via Comptroller `_setPriceOracle` → `NewPriceOracle`. | Comptroller `admin` (Timelock). |
| **Comptroller impl / IRMs** | OP + Base | Immutable logic contracts. | n/a (delegatecall targets / pointers). | replaced via the delegator / `_setInterestRateModel`. |

EIP-1967 slots used: impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. **Always read the live slot on Base soTokens — never hard-code an impl.**

---

## 9. Detection invariants & gotchas

1. **DEPRECATED / EXPLOITED.** Sonne is wound down. The **Base** market was drained ~$20M on **2024-05-14** via an **empty-market `exchangeRate` donation/inflation** on a freshly-listed market (`_supportMarket` → seed → donate underlying to spike `exchangeRateStored` → over-borrow on rounding-inflated collateral). Any large `Mint`/`Redeem`/`AccrueInterest`/`Borrow` swing on a **low-`getCash()`** market — especially on Base — is the exploit pattern, not organic activity. Optimism was subsequently deprecated too. Treat both as post-mortem/residual monitoring.
2. **4-arg `AccrueInterest` only** (`0x4dec04e7…`, 128-byte data, 4 words). The 3-arg legacy Compound topic (`0x8753…6cb9`) **never fires** on Sonne — do not index it. (Same 4-arg form as Moonwell; differs from stock Compound V2 on Ethereum.)
3. **Two soToken proxy models, one protocol.** **OP soTokens are immutable** (`implementation()` reverts, EIP-1967 slot `0x0`). **Base soTokens are EIP-1967 proxies** (read the impl slot; admin = ProxyAdmin `0xb19b…BC5f`). Code that assumes the Compound `CErc20Delegator` `implementation()` getter will **revert on every Sonne market** — use the EIP-1967 slot on Base and accept the revert as "immutable" on OP.
4. **`Failure` is a silent no-op signal.** A `mint`/`borrow`/`redeem`/`liquidate` that emits `Failure(error,info,detail)` (`0x45b9…9aa0`, from soToken or Comptroller) moved **no** funds — the legacy error-code convention. Treat presence of `Failure` as a failed action.
5. **soToken decimals = 8 always** (not the underlying's). Underlying value = `soTokenAmount × exchangeRateStored`, with `exchangeRateStored` scaled by `1e(18 − 8 + underlyingDecimals)`.
6. **Per-second rates, not per-block.** `supplyRatePerTimestamp`/`borrowRatePerTimestamp`/`accrualBlockTimestamp`. `accrualBlockNumber()`/`*RatePerBlock()` revert.
7. **Native-gas markets are WETH `CErc20`, not `CEther`.** soWETH (OP) / sobWETH (Base) have `underlying()` = `0x4200…0006` and use `mint(uint256)`. No payable `mint()`/`repayBorrow()`/`liquidateBorrow(address,address)` selectors exist. Detection code that special-cases cETH does not apply.
8. **Liquidation emits `LiquidateBorrow` on the debt soToken + `seize`/`Transfer` on the collateral soToken** in the same tx. Detect by the `LiquidateBorrow` topic0 (`0x2986…bb52`) on the debt market.
9. **`Mint`/`Borrow`/`Redeem`/`RepayBorrow`/`LiquidateBorrow` are NOT indexed** — all fields in `data`; filter by market address + topic0. **`Mint` topic0 collides with Uniswap-V2 `Mint`** (same `Mint(address,uint256,uint256)`) — disambiguate by emitter.
10. **Same topic0 on Unitroller vs soToken for admin events.** `NewAdmin`/`NewPendingAdmin` (`0xf9ff…417dc`/`0xca4f…b16a9`) are emitted by both the Unitroller and each soToken — disambiguate by emitting address.
11. **Governance = OZ TimelockController.** OP admin `0x37ff…d60b6` (`getMinDelay` 2 days), Base admin `0x81077d…2fd3` (`getMinDelay` 1 day). Admin actions (`_supportMarket`, `_setCollateralFactor`, `_setPriceOracle`, soToken upgrades on Base) originate from these. The Base Timelock also owns the soToken ProxyAdmin `0xb19b…BC5f`.
12. **BNB address-collision decoy.** The Base Unitroller literal `0x1DB2466d…45F0` has unrelated bytecode on **BNB** — it is **not** Sonne (Comptroller selectors revert, length differs, EIP-1967 empty). Never key Sonne detection on address alone; always pair `(chainId, address)`.
13. **`getAllMarkets()` includes only the 13 (OP) / 7 (Base) listed markets.** Compound's market array retains markets even when paused — re-read live rather than hardcoding; a market being in the array does not mean it is active (most are paused post-wind-down).

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; Compound-V2-fork) =====
-- soToken money-market
TOPIC_ACCRUE_INTEREST_4ARG    = '\x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04'
TOPIC_MINT                    = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'
TOPIC_REDEEM                  = '\xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929'
TOPIC_BORROW                  = '\x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'
TOPIC_REPAY_BORROW            = '\x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1'
TOPIC_LIQUIDATE_BORROW        = '\x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
TOPIC_RESERVES_ADDED          = '\xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5'
TOPIC_RESERVES_REDUCED        = '\x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e'
TOPIC_NEW_RESERVE_FACTOR      = '\xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460'
TOPIC_NEW_MARKET_IRM          = '\xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926'
-- ERC-20 (soToken share + SONNE)
TOPIC_ERC20_TRANSFER          = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_ERC20_APPROVAL          = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
-- Comptroller
TOPIC_MARKET_LISTED           = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_MARKET_ENTERED          = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'
TOPIC_MARKET_EXITED           = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_NEW_COLLATERAL_FACTOR   = '\x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5'
TOPIC_NEW_PRICE_ORACLE        = '\xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22'
TOPIC_ACTION_PAUSED_GLOBAL    = '\xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0'
TOPIC_ACTION_PAUSED_MARKET    = '\x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0'
TOPIC_NEW_BORROW_CAP          = '\x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6'
TOPIC_DISTRIB_SUPPLIER_COMP   = '\x2caecd17d02f56fa897705dcc740da2d237c373f70686f4e0d9bd3bf0400ea7a'
TOPIC_DISTRIB_BORROWER_COMP   = '\x1fc3ecc087d8d2d15e23d0032af5a47059c3892d003d8e139fdcb6bb327c99a6'
TOPIC_FAILURE                 = '\x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0'
-- Unitroller (Comptroller proxy) admin/upgrade
TOPIC_NEW_IMPLEMENTATION      = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'
TOPIC_NEW_PENDING_IMPL        = '\xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815'
TOPIC_NEW_ADMIN               = '\xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc'
TOPIC_NEW_PENDING_ADMIN       = '\xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9'
-- Base soToken EIP-1967 proxy (NOT present on OP — immutable there)
TOPIC_PROXY_UPGRADED          = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_PROXY_ADMIN_CHANGED     = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'

-- ===== Selectors — soToken =====
SEL_MINT                      = '\xa0712d68'   -- mint(uint256)
SEL_REDEEM                    = '\xdb006a75'   -- redeem(uint256)
SEL_REDEEM_UNDERLYING         = '\x852a12e3'   -- redeemUnderlying(uint256)
SEL_BORROW                    = '\xc5ebeaec'   -- borrow(uint256)
SEL_REPAY_BORROW              = '\x0e752702'   -- repayBorrow(uint256)
SEL_REPAY_BEHALF              = '\x2608f818'   -- repayBorrowBehalf(address,uint256)
SEL_LIQUIDATE                 = '\xf5e3c462'   -- liquidateBorrow(address,uint256,address)
SEL_SEIZE                     = '\xb2a02ff1'   -- seize(address,address,uint256)
SEL_EXCHANGE_RATE_STORED      = '\x182df0f5'   -- exchangeRateStored()
SEL_EXCHANGE_RATE_CURRENT     = '\xbd6d894d'   -- exchangeRateCurrent()
SEL_GET_CASH                  = '\x3b1d21a2'   -- getCash()
SEL_SUPPLY_RATE_PER_TS        = '\xd3bd2c72'   -- supplyRatePerTimestamp()
SEL_BORROW_RATE_PER_TS        = '\xcd91801c'   -- borrowRatePerTimestamp()
SEL_ACCRUAL_BLOCK_TS          = '\xcfa99201'   -- accrualBlockTimestamp()
SEL_GET_ACCOUNT_SNAPSHOT      = '\xc37f68e2'   -- getAccountSnapshot(address)
SEL_UNDERLYING                = '\x6f307dc3'   -- underlying()
SEL_IMPLEMENTATION            = '\x5c60da1b'   -- implementation()  [reverts on all Sonne markets]

-- ===== Selectors — Comptroller / Unitroller =====
SEL_ENTER_MARKETS             = '\xc2998238'   -- enterMarkets(address[])
SEL_EXIT_MARKET               = '\xede4edd0'   -- exitMarket(address)
SEL_GET_ASSETS_IN             = '\xabfceffc'   -- getAssetsIn(address)
SEL_MARKETS                   = '\x8e8f294b'   -- markets(address)
SEL_GET_ACCOUNT_LIQUIDITY     = '\x5ec88c79'   -- getAccountLiquidity(address)
SEL_GET_ALL_MARKETS           = '\xb0772d0b'   -- getAllMarkets()
SEL_ORACLE                    = '\x7dc0d1d0'   -- oracle()
SEL_COMPTROLLER_IMPL          = '\xbb82aa5e'   -- comptrollerImplementation()
SEL_ADMIN                     = '\xf851a440'   -- admin()
SEL_SUPPORT_MARKET            = '\xa76b3fda'   -- _supportMarket(address)
SEL_SET_COLLATERAL_FACTOR     = '\xe4028eee'   -- _setCollateralFactor(address,uint256)
SEL_GET_UNDERLYING_PRICE      = '\xfc57d4df'   -- getUnderlyingPrice(address)

-- ===== Optimism addresses (chain ID 10) =====
OP_UNITROLLER                 = '\x60cf091cd3f50420d50fd7f707414d0df4751c58'
OP_COMPTROLLER_IMPL           = '\xe8ff1489227fa74f77e49c688903e69e1583c03f'
OP_PRICE_ORACLE               = '\x22c7e5ce392bc951f63b68a8020b121a8e1c0fea'
OP_TIMELOCK                   = '\x37ff10390f22fabdc2137e428a6e6965960d60b6'
OP_SOWETH                     = '\xf7b5965f5c117eb1b5450187c9dcfccc3c317e8e'
OP_SOUSDC                     = '\xec8fea79026ffed168ccf5c627c7f486d77b765f'
OP_SOUSDT                     = '\x5ff29e4470799b982408130efaabdeeae7f66a10'
OP_SODAI                      = '\x5569b83de187375d43fbd747598bfe64fc8f6436'
OP_SOOP                       = '\x8cd6b19a07d754bf36adeee79edf4f2134a8f571'
OP_SOSUSD                     = '\xd14451e0fa44b18f08aeb1e4a4d092b823caca68'
OP_SOSNX                      = '\xd7daabd899d1fabbc3a9ac162568939cec0393cc'
OP_SOWBTC                     = '\x33865e09a572d4f1cc4d75afc9abcc5d3d4d867d'
OP_SOLUSD                     = '\xafdf91f120dec93c65fd63dbd5ec372e5dca5f82'
OP_SOWSTETH                   = '\x26aab17f27cd1c8d06a0ad8e4a1af8b1032171d5'
OP_SOMAI                      = '\xe7de932d50efc9ea0a7a409fc015b4f71443528e'
OP_SOUSDCNATIVE               = '\x1afd1ff9e441973b7d34c7b8abe91d94f1b23ce0'
OP_SOVELO                     = '\xe3b81318b1b6776f0877c3770afddff97b9f5fe5'

-- ===== Base addresses (chain ID 8453) — EXPLOITED, dead =====
BASE_UNITROLLER               = '\x1db2466d9f5e10d7090e7152b68d62703a2245f0'
BASE_COMPTROLLER_IMPL         = '\x076c7883e154f6cc0ca04888288b350d78cf1321'
BASE_PRICE_ORACLE             = '\x807fbc283805d4aaee7cd6a6c1f98000c3f51c9b'
BASE_TIMELOCK                 = '\x81077d101293eca45114af55a63897cec8732fd3'
BASE_SOTOKEN_PROXY_ADMIN      = '\xb19bd9fc8fa8f00599a04115193b915e1929bc5f'
BASE_SOBDAI                   = '\xb864ba2aab1f53bc3af7ae49a318202dd3fd54c2'
BASE_SOBUSDBC                 = '\x225886c9beb5eee254f79d58bbd80cf9f200d4d0'
BASE_SOBWETH                  = '\x5f5c479fe590cd4442a05ae4a941dd991a633b8e'
BASE_SOBUSDC                  = '\xfd68f92b45b633bbe0f475294c1a86aecd62985a'
BASE_SOBCBETH                 = '\x6c91beeceedda2089307fab818e12757948bf489'
BASE_SOBWSTETH                = '\x7a6468053cdcd7e8fe507d7edb77336f5057d206'
BASE_SOBAERO                  = '\xfa78196ace4048c4ccce6d3d97890d7b6c8f59da'
```

---

## 11. Verification & sources

- **Topics + selectors:** computed locally as `keccak256(canonical signature)` / `[0:4]` (pycryptodome) on 2026-06-08. Cross-checked against live `eth_getLogs`:
  - **Optimism soUSDC** (`0xEC8F…765F`, blocks ~110,000,000–110,050,000): observed `AccrueInterest`(4-arg) ×84, `Mint` ×41, `Borrow` ×18, `Redeem` ×23; the **3-arg** `AccrueInterest` topic produced **0** logs. One `AccrueInterest` log inspected = **128 bytes data / 4 words / 1 topic** ⇒ 4-arg confirmed.
  - **Optimism Comptroller** (`0x60CF…1C58`): `MarketEntered` ×24 in the same window.
  - **Base sobUSDC** (`0xfd68…985A`, blocks ~14,400,000–14,450,000): `AccrueInterest`(4-arg) ×893, `Mint` ×162, `Borrow` ×306; 3-arg = 0.
  - **Base Comptroller** (`0x1DB2…45F0`): `MarketEntered` ×686 in the same window.
- **Addresses:** every core contract and every soToken returns non-empty `eth_getCode` on its chain (OP via `optimism-rpc.publicnode.com`, Base via `base-rpc.publicnode.com`), 2026-06-08. Markets enumerated live from `Unitroller.getAllMarkets()` (OP=13, Base=7) and each market's `symbol()`/`decimals()`/`underlying()`/`interestRateModel()`/`comptroller()`/`admin()` read via `eth_call`. Wiring confirmed: every market's `comptroller()` points back to its chain's Unitroller; every market's `admin()` points to its chain's Timelock.
- **Proxy classification (read live 2026-06-08):**
  - OP soTokens (soWETH/soUSDC/soUSDCnative sampled): EIP-1967 impl slot = `0x0`, `implementation()` reverts ⇒ **immutable `CErc20Immutable`**.
  - Base soTokens (all 7): EIP-1967 impl slot non-empty (distinct per market, all → byte-identical 31,338-char logic); EIP-1967 admin slot = `0xb19b…BC5f` (shared OZ ProxyAdmin, `owner()` = Base Timelock) ⇒ **EIP-1967 transparent proxy**.
  - Unitroller (both): EIP-1967 impl slot = `0x0`; `comptrollerImplementation()` returns the live Comptroller logic ⇒ **Compound delegator**.
  - Comptroller admins are **OZ TimelockController** — `getMinDelay()` returns 172800 (OP, 2 days) / 86400 (Base, 1 day); `VERSION()`/`getOwners()` (Safe) revert.
- **Absence on the other five chains:** `eth_getCode` for the OP Unitroller, Base Unitroller, and OP soUSDC is empty (`0x`) on Ethereum, BNB, Avalanche, Arbitrum, Polygon — **except** the Base-Unitroller literal on BNB, which carries unrelated bytecode (4,102 chars; all Comptroller selectors revert; EIP-1967 empty) ⇒ an **address collision, not Sonne** (§5/§9).

### Independent fact-check (2026-06-08)

Non-obvious claims cross-checked against primary on-chain evidence (RPC reads above) and the public exploit record:

- **"Sonne is a Compound V2 fork on OP + Base only"** — **confirmed.** Compound-V2 selector/event surface present and live on both; absent (eth_getCode 0x) on the other 5 (BNB hit is a decoy, refuted as Sonne).
- **"Sonne uses 4-arg `AccrueInterest` (Moonwell-style), not 3-arg legacy Compound"** — **confirmed** by bytecode topic-constant scan (4-arg present, 3-arg absent) **and** live logs (4-arg ×84/×893, 3-arg ×0) **and** the 128-byte/4-word log data width.
- **"~$20M Base exploit on 2024-05-14 via empty-market `exchangeRate` donation/inflation, then wind-down"** — **confirmed** against the public incident record; the Compound-V2 empty-market donation/rounding mechanism is consistent with Sonne's `CErc20`-style `exchangeRateStored` math and the fresh-`_supportMarket` precondition observable in the Comptroller's `MarketListed`/`NewCollateralFactor` admin path. Status recorded as deprecated/dead.
- **"OP soTokens immutable, Base soTokens EIP-1967 proxies"** — **confirmed** by live EIP-1967 slot reads (OP slot `0x0` + `implementation()` revert; Base slot non-empty + shared ProxyAdmin). This is a genuine per-chain divergence within one protocol and the highest-value monitoring distinction.
- **"BNB `0x1DB2466d…45F0` is the Base Unitroller redeployed there"** — **refuted.** It is an unrelated contract sharing the address by deployer-nonce collision (selectors revert, length differs, EIP-1967 empty). Recorded as a decoy, not a Sonne deployment.

**Authoritative sources:** the Compound V2 reference design (`compound-finance/compound-protocol`: `CToken.sol`, `CErc20Immutable.sol`, `Comptroller.sol`, `Unitroller.sol`); Optimistic Etherscan (`optimistic.etherscan.io`) and BaseScan (`basescan.org`) for the deployed, verified Sonne contracts; the public Sonne Finance exploit post-mortems (2024-05). All constants in this doc were recomputed and re-verified on-chain rather than copied from any third-party list.
