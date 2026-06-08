# Strike (Strike Price) — Topics, Selectors, Addresses (Ethereum only)

**Status:** verified against Ethereum mainnet (1) RPC and the canonical `StrikeFinance/strike-protocol` source + `docs.strike.org` on 2026-06-08. Every topic0/selector recomputed locally as `keccak256(signature)`; every address `eth_getCode`-checked; proxy wiring + accrual model read live from storage, getters, and deployed bytecode.

**Scope:** the entire Strike lending protocol — a **Compound V2 fork** with the cToken→sToken rename: `CErc20Delegator`→**SErc20Delegator** (per-market proxy), `CErc20Delegate`→**SErc20Delegate** (shared logic), `CEther`→**SEther** (native-gas market), `Comptroller` behind a **Unitroller**, the **STRK** governance token + GovernorAlpha + Timelock, per-market JumpRate/WhitePaper interest-rate models, a Chainlink-backed PriceOracle, and Maximillion. **Strike lending is deployed on ONLY ONE of the seven requested chains: Ethereum mainnet (1).** It is NOT on Base, BNB Smart Chain, Avalanche, Arbitrum, Optimism, or Polygon (see §5). Topics/selectors are chain-agnostic; addresses are Ethereum-specific.

Three protocol facts a monitor must internalize:

1. **Per-block accrual (stock Compound V2), NOT timestamp-based.** Interest accrues on `block.number`. The accessors are `supplyRatePerBlock()` / `borrowRatePerBlock()` (per-block mantissas) and `accrualBlockNumber()` (a block number, verified live = `0x17c3664` = 24,917,604 on sUSDC). There is **no** `supplyRatePerTimestamp` / `accrualBlockTimestamp`. APR ≈ `ratePerBlock × blocksPerYear / 1e18` (~2,628,000 blocks/yr at 12s).
2. **`AccrueInterest` is the 4-arg form** `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` (topic0 `0x4dec04e7…`), **not** legacy Compound's 3-arg `AccrueInterest(uint256,uint256,uint256)` (`0x875352fb…`). Confirmed two ways: the SErc20Delegate bytecode (`0x20db276e…`) contains the 4-arg topic and NOT the 3-arg topic, and live logs on sETH/sUSDC/sUSDT carry **128 bytes** of data (= 4×uint256). Strike runs a *newer* Compound V2 codebase than the original 3-arg cToken even though accrual is still per-block.
3. **STRK distribution lives in the Comptroller (COMP-style), split into supply/borrow speeds.** The Comptroller emits `DistributedSupplierStrike` / `DistributedBorrowerStrike` (live, ~108/107 in a 6M-block window) and the speed-config events `StrikeSupplySpeedUpdated` / `StrikeBorrowSpeedUpdated` (present in impl bytecode). There is **no** separate reward distributor and **no** single-speed `StrikeSpeedUpdated` / `MarketStriked` in the live impl — Strike is on the G3+ *split-speed* generation. Read speeds via `strikeSupplySpeeds(address)` (`0x21f5492b`) / `strikeBorrowSpeeds(address)` (`0x2b5fc299`); the legacy `strikeSpeeds(address)` (`0xca9a7a63`) mapping is still populated.

Governance is the classic Compound stack (GovernorAlpha → Timelock → Unitroller/sToken `admin`), and admin is **split across two layers** (verified live by reading `admin()` on each contract):
- **Unitroller** (Comptroller proxy) and the **Timelock** are both admined by an **EOA** `0xc3c4c0aaf09ece96af97688198d46ab5e360ff94` (codelen 0). So all *Comptroller-level* policy (collateral factors, market listing, pause flags, reward speeds, oracle, close factor, liquidation incentive, Unitroller upgrades) is gated by that EOA — watch transactions FROM it.
- **Every active sToken's `admin()` is the Timelock** `0xe789af79D295B0e4fA1C1E8a1B6Fe186c1ae2326` (confirmed on sETH/sUSDT/sUSDC/sWBTC/sSTRK/sCRVUSD/sRETH/sWSTETH/sAPE/sCOMP#2). So all *market-level* admin (`_setReserveFactor`, `_setInterestRateModel`, `_reduceReserves`, `_setImplementation`, `_setComptroller`) MUST route through the Timelock's `QueueTransaction`/`ExecuteTransaction` — watch the Timelock for those. The deprecated sCOMP#1 (`0xa28d…`) is the lone exception (its `admin()` is the deployer EOA `0x752dfb1c…`).

The Timelock currently has **no logs in the recent 2M blocks** (the protocol is quiet, not that the Timelock is bypassed) — but it is still the on-chain authority over every sToken, so do not treat it as inert.

---

## 0. Contract families & versions

| Family | Contract | Pattern | Notes |
|--------|----------|---------|-------|
| Risk engine | **Unitroller** (proxy) + **Comptroller** (impl) | Compound Unitroller (impl in storage slot 2) | one per protocol; the `oracle()`/markets hub |
| Markets (ERC-20) | **SErc20Delegator** (per-market proxy) + **SErc20Delegate** (shared logic) | Compound delegator (`implementation()` getter, NOT EIP-1967) | 17 ERC-20 markets; mostly share impl `0x20db276e…`, a few older variants |
| Market (native) | **SEther** (sETH) | immutable full contract (no delegator) | no `underlying()`, no `implementation()`; supply/redeem ETH directly |
| Rates | per-market **JumpRateModel / WhitePaperInterestRateModel** | immutable | read live via `sToken.interestRateModel()` |
| Pricing | **PriceOracle** (Chainlink-backed) | immutable (plain `admin`) | `getUnderlyingPrice(sToken)` |
| Token | **STRK** | immutable ERC-20 (Comp-style, 18 dec, with `delegate`/votes) | governance + reward asset |
| Governance | **GovernorAlpha** + **Timelock** | immutable | Unitroller+Timelock admin = EOA `0xc3c4c0aa…`; **Timelock = admin of every sToken** |
| Helper | **Maximillion** | immutable | repay-ETH-on-behalf helper for sETH (address not on-chain-confirmed — see §9) |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 sToken / SErc20 / SEther (per-market — the workhorse events)

| topic0 | Event |
|--------|-------|
| `0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04` | `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` — **4-arg** |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address minter, uint256 mintAmount, uint256 mintTokens)` |
| `0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929` | `Redeem(address redeemer, uint256 redeemAmount, uint256 redeemTokens)` |
| `0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80` | `Borrow(address borrower, uint256 borrowAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1` | `RepayBorrow(address payer, address borrower, uint256 repayAmount, uint256 accountBorrows, uint256 totalBorrows)` (live data = 160 B = 5 fields) |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address liquidator, address borrower, uint256 repayAmount, address sTokenCollateral, uint256 seizeTokens)` |
| `0xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5` | `ReservesAdded(address benefactor, uint256 addAmount, uint256 newTotalReserves)` |
| `0x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e` | `ReservesReduced(address admin, uint256 reduceAmount, uint256 newTotalReserves)` |
| `0xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460` | `NewReserveFactor(uint256 oldReserveFactorMantissa, uint256 newReserveFactorMantissa)` |
| `0xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926` | `NewMarketInterestRateModel(address oldIRM, address newIRM)` |
| `0x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d` | `NewComptroller(address oldComptroller, address newComptroller)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` — sToken shares |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` — soft-fail (pre-revert legacy path) |

> **`Mint` topic0 collides with Uniswap V2's `Mint`** (`0x4c209b5f…`, identical `Mint(address,uint256,uint256)` signature). Always filter by emitter (an sToken). Same for `Transfer`/`Approval` (every ERC-20).
> **`NewProtocolSeizeShare` is NOT emitted** by the deployed SErc20Delegate (`0x20db276e…`) — this is an older cToken without the protocol-seize-share feature.

### 1.2 Comptroller (behind Unitroller — one per protocol)

Event presence confirmed in the live Comptroller impl bytecode (`0xd01ce4a7…`).

| topic0 | Event | In impl? |
|--------|-------|----------|
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address sToken)` | ✅ |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address sToken, address account)` | ✅ |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address sToken, address account)` | ✅ |
| `0x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9` | `NewCloseFactor(uint256 oldCloseFactorMantissa, uint256 newCloseFactorMantissa)` | ✅ |
| `0x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5` | `NewCollateralFactor(address sToken, uint256 oldCFMantissa, uint256 newCFMantissa)` | ✅ |
| `0xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316` | `NewLiquidationIncentive(uint256 oldIncentiveMantissa, uint256 newIncentiveMantissa)` | ✅ |
| `0xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22` | `NewPriceOracle(address oldOracle, address newOracle)` | ✅ |
| `0x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e` | `NewPauseGuardian(address oldPauseGuardian, address newPauseGuardian)` | ✅ |
| `0x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0` | `ActionPaused(address sToken, string action, bool pauseState)` — per-market (Mint/Borrow) | ✅ |
| `0xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0` | `ActionPaused(string action, bool pauseState)` — global (Transfer/Seize) | ❌ **NOT in impl** |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` | ✅ |

> **Pausing:** only the **3-arg per-market** `ActionPaused(address,string,bool)` is in the live impl. The 2-arg global overload is absent. **There is no `NewBorrowCap` / `NewBorrowCapGuardian` / `NewSupplyCap`** in this impl — Strike's deployed Comptroller predates supply/borrow caps.

### 1.3 Comptroller — STRK rewards (split-speed model, G3+)

| topic0 | Event | In impl? |
|--------|-------|----------|
| `0x926dc6130c8a69503e637fa5aed5b3ba65bd6d241957047e4bcc24485e0c48fb` | `DistributedSupplierStrike(address indexed sToken, address indexed supplier, uint256 strikeDelta, uint256 strikeSupplyIndex)` | ✅ (live ~108) |
| `0x730ec20a857394345ba1d81394d16c333202df6c655e85f7cf16c65954def57e` | `DistributedBorrowerStrike(address indexed sToken, address indexed borrower, uint256 strikeDelta, uint256 strikeBorrowIndex)` | ✅ (live ~107) |
| `0x898847f275797e75839591f6be6df865612ff8dc0f9f3a169897a3fac1415cdc` | `StrikeSupplySpeedUpdated(address indexed sToken, uint256 newSpeed)` | ✅ |
| `0xd849eae9f25bdb1c95a86ded3675b83bcbf3fa8e8b784375dc1f0fb13617dd15` | `StrikeBorrowSpeedUpdated(address indexed sToken, uint256 newSpeed)` | ✅ |
| `0x96d2fd0650b0c3afb0e7857c50126f0824d10b3b5156ae4e077ed7ccc18236c4` | `StrikeGranted(address recipient, uint256 amount)` | ✅ |
| `0xd864d325a0ec23107c1ff2fdc67d16598d133c01befa325469f2b7374ac20f18` | `ContributorStrikeSpeedUpdated(address indexed contributor, uint256 newSpeed)` | ✅ |
| `0x60a65f19752012d4f9f657966c52c36646668cd58677cd1aa9459a98d61eee30` | `StrikeSpeedUpdated(address indexed sToken, uint256 newSpeed)` — single-speed legacy | ❌ NOT in impl |
| `0xf9c0ca9605dd33f829f3c2b2a6761b34fcfc40656ffe0f23d57268b465e210a2` | `MarketStriked(address sToken, bool isStriked)` — legacy | ❌ NOT in impl |

> The two `Distributed*Strike` events are **the only events that fire on the Comptroller in a 6M-block window** (Strike is low-volume). Both have **2 indexed args (ntopics=3) + 64 data bytes** on-chain — `indexed` does not change topic0.

### 1.4 Unitroller (Comptroller proxy — admin/upgrade events)

| topic0 | Event |
|--------|-------|
| `0xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815` | `NewPendingImplementation(address oldPendingImplementation, address newPendingImplementation)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |

### 1.5 STRK token (Comp-style ERC-20 with governance votes)

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` |
| `0x3134e8a2e6d97e929a7e54011ea5485d7d196dd5f0ba4d4ef95803e8e3fc257f` | `DelegateChanged(address indexed delegator, address indexed fromDelegate, address indexed toDelegate)` (live; ntopics=4) |
| `0xdec2bacdd2f05b59de34da9b523dff8be42e5e38e818c82fdb0bae774387a724` | `DelegateVotesChanged(address indexed delegate, uint256 previousBalance, uint256 newBalance)` (live; ntopics=2, data 64) |

### 1.6 GovernorAlpha (Compound governor)

| topic0 | Event |
|--------|-------|
| `0x7d84a6263ae0d98d3329bd7b46bb4e8d6f98cd35a7adb45c274c8b7fd5ebd5e0` | `ProposalCreated(uint256 id, address proposer, address[] targets, uint256[] values, string[] signatures, bytes[] calldatas, uint256 startBlock, uint256 endBlock, string description)` |
| `0x877856338e13f63d0c36822ff0ef736b80934cd90574a3a5bc9262c39d217c46` | `VoteCast(address voter, uint256 proposalId, bool support, uint256 votes)` — Alpha |
| `0xb8e138887d0aa13bab447e82de9d5c1777041ecd21ca36ba824ff1e6c07ddda4` | `VoteCast(address indexed voter, uint256 proposalId, uint8 support, uint256 votes, string reason)` — Bravo (if upgraded) |
| `0x789cf55be980739dad1d0699b93b58e806b51c9d96619bfa8fe0a28abaa7b30c` | `ProposalCanceled(uint256 id)` |
| `0x9a2e42fd6722813d69113e7d0079d3d940171428df7373df9c7f7617cfda2892` | `ProposalQueued(uint256 id, uint256 eta)` |
| `0x712ae1383f79ac853f8d882153778e0260ef8f03b504e2866e0593e04d2b291f` | `ProposalExecuted(uint256 id)` |

### 1.7 Timelock

| topic0 | Event |
|--------|-------|
| `0x76e2796dc3a81d57b0e8504b647febcbeeb5f4af818e164f11eef8131a6a763f` | `QueueTransaction(bytes32 indexed txHash, address indexed target, uint256 value, string signature, bytes data, uint256 eta)` |
| `0xa560e3198060a2f10670c1ec5b403077ea6ae93ca8de1c32b451dc1a943cd6e7` | `ExecuteTransaction(bytes32 indexed txHash, address indexed target, uint256 value, string signature, bytes data, uint256 eta)` |
| `0x2fffc091a501fd91bfbff27141450d3acb40fb8e6d8382b243ec7a812a3aaf87` | `CancelTransaction(bytes32 indexed txHash, address indexed target, uint256 value, string signature, bytes data, uint256 eta)` |
| `0x71614071b88dee5e0b2ae578a9dd7b2ebbe9ae832ba419dc0242cd065a290b6c` | `NewAdmin(address indexed newAdmin)` |
| `0x69d78e38a01985fbb1462961809b4b2d65531bc93b2b94037f3334b82ca4a756` | `NewPendingAdmin(address indexed newPendingAdmin)` |
| `0x948b1f6a42ee138b7e34058ba85a37f716d55ff25ff05a763f15bed6a04c8d2c` | `NewDelay(uint256 indexed newDelay)` |

> The Timelock has **no logs in the recent 2M blocks** (the protocol is quiet), **but it is the `admin()` of every active sToken** — any market-level admin action (`_setReserveFactor`/`_setInterestRateModel`/`_reduceReserves`/`_setImplementation`) surfaces here as `QueueTransaction`/`ExecuteTransaction`. The Timelock's *own* admin is the EOA `0xc3c4c0aa…`.

### 1.8 PriceOracle (Strike, Chainlink-backed)

| topic0 | Event |
|--------|-------|
| `0xdd71a1d19fcba687442a1d5c58578f1e409af71a79d10fd95a4d66efd8fa9ae7` | `PricePosted(address asset, uint256 previousPriceMantissa, uint256 requestedPriceMantissa, uint256 newPriceMantissa)` — admin price override (not observed live; oracle uses Chainlink feeds) |

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

Selectors recomputed locally; cross-checked against deployed Ethereum bytecode and known Compound selectors. Interface-file `uint`→`uint256`.

### 2.1 sToken / SErc20 / SEther (per-market)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa0712d68` | `mint(uint256 mintAmount)` | SErc20: supply underlying. Emits `Mint`+`AccrueInterest`+`Transfer`. |
| `0x1249c58b` | `mint()` | **SEther (sETH) only** — payable; supply ETH. |
| `0xdb006a75` | `redeem(uint256 redeemTokens)` | Burn sTokens for underlying. |
| `0x852a12e3` | `redeemUnderlying(uint256 redeemAmount)` | Redeem an exact underlying amount. |
| `0xc5ebeaec` | `borrow(uint256 borrowAmount)` | Emits `Borrow`. |
| `0x0e752702` | `repayBorrow(uint256 repayAmount)` | SErc20; `type(uint).max` repays full debt. |
| `0x4e4d9fea` | `repayBorrow()` | **SEther only** — payable. |
| `0x2608f818` | `repayBorrowBehalf(address borrower, uint256 repayAmount)` | SErc20. |
| `0xe5974619` | `repayBorrowBehalf(address borrower)` | **SEther only** — payable. |
| `0xf5e3c462` | `liquidateBorrow(address borrower, uint256 repayAmount, address sTokenCollateral)` | SErc20. Emits `LiquidateBorrow`. |
| `0xaae40a2a` | `liquidateBorrow(address borrower, address sTokenCollateral)` | **SEther only** — payable. |
| `0xb2a02ff1` | `seize(address liquidator, address borrower, uint256 seizeTokens)` | Cross-market collateral seizure. |
| `0xa6afed95` | `accrueInterest()` | Emits 4-arg `AccrueInterest`. |
| `0xbd6d894d` | `exchangeRateCurrent()` | Accrues, then returns exchange rate. |
| `0x182df0f5` | `exchangeRateStored()` | View; last-stored rate (scaled `1e(18 + underlyingDec − 8)`). |
| `0x17bfdfbc` | `borrowBalanceCurrent(address)` | Accrues then returns debt. |
| `0x95dd9193` | `borrowBalanceStored(address)` | View. |
| `0xc37f68e2` | `getAccountSnapshot(address)` | `(uint err, uint sTokenBalance, uint borrowBalance, uint exchangeRateMantissa)`. |
| `0x3b1d21a2` | `getCash()` | Underlying held by the sToken. |
| `0xae9d70b0` | `supplyRatePerBlock()` | **Per-block** supply rate mantissa. |
| `0xf8f9da28` | `borrowRatePerBlock()` | **Per-block** borrow rate mantissa. |
| `0x6c540baf` | `accrualBlockNumber()` | **Block number** of last accrual (NOT a timestamp). |
| `0x47bd3718` | `totalBorrows()` / `0x8f840ddd totalReserves()` / `0xaa5af0fd borrowIndex()` | |
| `0x173b9904` | `reserveFactorMantissa()` | |
| `0x5fe3b567` | `comptroller()` | Returns the Unitroller address. |
| `0xf3fdb15a` | `interestRateModel()` | Per-market JumpRate/WhitePaper model. |
| `0x6f307dc3` | `underlying()` | Underlying ERC-20 (**absent on sETH** — reverts). |
| `0x5c60da1b` | `implementation()` | **Read this for the sToken logic** (delegator) — NOT EIP-1967 (§8). Absent on sETH. |
| `0xd0248fb4` | `mintWithPermit(uint256,uint256,uint8,bytes32,bytes32)` | EIP-2612 permit + mint (present on some delegates). |
| `0x3af9e669` | `balanceOfUnderlying(address)` | State-mutating (accrues). |
| `0x70a08231`/`0x18160ddd`/`0x313ce567`/`0x95d89b41`/`0x06fdde03` | `balanceOf`/`totalSupply`/`decimals`/`symbol`/`name` | sTokens: **8 decimals**, `symbol()`=`s`+underlying (e.g. `sUSDC`), `name()`=`Strike USDC`/`Strike ETH`. |
| `0x555bcc40` | `_setImplementation(address implementation_, bool allowResign, bytes becomeImplementationData)` | Admin sToken logic upgrade (delegator). |
| `0xfca7820b` | `_setReserveFactor(uint256)` / `0xf2b3abbd _setInterestRateModel(address)` / `0x601a0bf1 _reduceReserves(uint256)` / `0x3e941010 _addReserves(uint256)` | Reserve/IRM management (admin). |

### 2.2 Comptroller (behind Unitroller)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc2998238` | `enterMarkets(address[] sTokens)` | Use as collateral. Emits `MarketEntered`. |
| `0xede4edd0` | `exitMarket(address sToken)` | Emits `MarketExited`. |
| `0x5ec88c79` | `getAccountLiquidity(address)` | `(err, liquidity, shortfall)`. Shortfall>0 ⇒ liquidatable. |
| `0xb0772d0b` | `getAllMarkets()` | All listed sTokens (**18** as of 2026-06; includes two sCOMP markets). Re-read live. |
| `0x8e8f294b` | `markets(address sToken)` | `(bool isListed, uint collateralFactorMantissa, bool isStriked)`. |
| `0x7dc0d1d0` | `oracle()` | The PriceOracle address. |
| `0xe8755446` | `closeFactorMantissa()` / `0x4ada90af liquidationIncentiveMantissa()` | |
| `0xa76b3fda` | `_supportMarket(address)` | Admin. Emits `MarketListed`. |
| `0xe4028eee` | `_setCollateralFactor(address,uint256)` | Admin. Emits `NewCollateralFactor`. |
| `0x3bcf7ec1` | `_setMintPaused(address,bool)` / `0x18c882a5 _setBorrowPaused(address,bool)` | Emit `ActionPaused(address,string,bool)`. |
| `0x8ebf6364` | `_setTransferPaused(bool)` / `0x2d70db78 _setSeizePaused(bool)` | Global pauses (no global `ActionPaused` event in this impl). |
| `0x55ee1fe1` | `_setPriceOracle(address)` / `0x317b0b77 _setCloseFactor(uint256)` / `0x4fd42e17 _setLiquidationIncentive(uint256)` | Admin. |
| `0xca9a7a63` | `strikeSpeeds(address)` | Legacy single-speed mapping (still populated). |
| `0x21f5492b` | `strikeSupplySpeeds(address)` | **Split supply speed** (G3+). |
| `0x2b5fc299` | `strikeBorrowSpeeds(address)` | **Split borrow speed** (G3+). |
| `0x1b749376` | `strikeAccrued(address)` | Unclaimed STRK per holder. |
| `0x871f1e79` | `claimStrike(address holder)` | Claim accrued STRK. |
| `0x9cc543fd` | `claimStrike(address holder, address[] sTokens)` | |
| `0x34b5ce3e` | `_grantStrike(address recipient, uint256 amount)` | Admin. Emits `StrikeGranted`. |
| `0xbb82aa5e` | `comptrollerImplementation()` | **Unitroller: read for live Comptroller logic** (storage slot 2). |
| `0xe992a041` | `_setPendingImplementation(address)` / `0xc1e80334 _acceptImplementation()` | Unitroller upgrade. |
| `0xb71d1a0c` | `_setPendingAdmin(address)` / `0xe9c714f2 _acceptAdmin()` | Unitroller admin handover. |

### 2.3 PriceOracle

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfc57d4df` | `getUnderlyingPrice(address sToken)` | Comptroller's pricing entry point. Returns mantissa scaled to `36 − underlyingDecimals`. |
| `0x127ffda0` | `setUnderlyingPrice(address,uint256)` | Admin override (test/fallback). |
| `0x09a8acb0` | `setDirectPrice(address,uint256)` | Admin direct price set. |

### 2.4 Maximillion

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9f35c3d5` | `repayBehalf(address borrower)` | payable; repay a borrower's ETH debt via sETH. |
| `0x367b7f05` | `repayBehalfExplicit(address borrower, address sEther_)` | |
| `0x1caef219` | `sEther()` | Returns the sETH market. |

### 2.5 STRK token / GovernorAlpha / Timelock

| Selector | Signature |
|----------|-----------|
| `0x5c19a95c` | `delegate(address delegatee)` |
| `0xc3cda520` | `delegateBySig(address,uint256,uint256,uint8,bytes32,bytes32)` |
| `0xb4b5ea57` | `getCurrentVotes(address)` |
| `0xda95691a` | `propose(address[],uint256[],string[],bytes[],string)` |
| `0x15373e3d` | `castVote(uint256 proposalId, bool support)` |
| `0xddf0b009` | `queue(uint256 proposalId)` / `0xfe0d94c1 execute(uint256 proposalId)` |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All `eth_getCode`-verified non-empty on `https://ethereum-rpc.publicnode.com` on 2026-06-08. **This is the only chain with a Strike deployment.** Deployed by `Strike ETH: Deployer` `0x752dfb1c709eea4621c8e95f48f3d0b6dde5d126`.

### 3.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| **UNITROLLER** (Comptroller proxy) | `0xe2e17b2CBbf48211FA7eB8A875360e5e39bA2602` | The risk engine + STRK reward hub. `comptrollerImplementation()`→COMPTROLLER; `oracle()`→PRICE_ORACLE; `getAllMarkets()`=18. Point all market-policy/reward monitors here. |
| COMPTROLLER (impl) | `0xd01ce4a7368cf81c34b1257691eedf34d825a694` | Comptroller logic (codelen 24551). Split-speed reward impl. |
| **SERC20_DELEGATE** (shared sToken logic) | `0x20db276ea50373497863496354d9bd5cf5a6b54c` | `implementation()` for most ERC-20 markets (codelen 23009). 4-arg `AccrueInterest`; no `NewProtocolSeizeShare`. |
| **PRICE_ORACLE** (Chainlink-backed) | `0x4386c6d63a4b10e4bc5a5191d8c5c7fa55402674` | `Comptroller.oracle()`. `getUnderlyingPrice(sToken)` returns live prices. `admin`=`0xc7b365c2…`. Plain proxy/contract (no EIP-1967 slot). |
| **STRK** (governance token) | `0x74232704659ef37c08995e386A2E26cc27a8d7B1` | `name()="Strike Token"`, `symbol()="STRK"`, **18 decimals**. Comp-style votes (`delegate`/`getCurrentVotes`). Reward asset. |
| GOVERNOR_ALPHA | *(see §9 — docs value `0x2Cc7f3…` is empty on-chain; live address not confirmed)* | Compound GovernorAlpha. |
| TIMELOCK | `0xe789af79D295B0e4fA1C1E8a1B6Fe186c1ae2326` | Compound Timelock; its own `admin()`→`0xc3c4c0aa…`. **It is the `admin()` of every active sToken** — market-level admin actions route through its `QueueTransaction`/`ExecuteTransaction`. No logs in recent 2M blocks (protocol is quiet), but NOT bypassed. |
| MAXIMILLION | *(see §9 — not on-chain-confirmed)* | ETH-repay-on-behalf helper for sETH. |
| **ADMIN_EOA** | `0xc3c4c0aaf09ece96af97688198d46ab5e360ff94` | **codelen 0 (EOA).** The live `admin()` of the **Unitroller and the Timelock** (i.e. all Comptroller-level policy + Timelock control). It is **NOT** the direct admin of the sTokens — those are admined by the Timelock. Watch this EOA for Comptroller-level admin actions. |
| ORACLE_ADMIN | `0xc7b365c24f6c5cb1574364dcbcd39b2e06485317` | `admin()` of the PriceOracle. |

### 3.2 sToken markets (18 — from live `getAllMarkets()`; `symbol`=`s`+underlying, **8 decimals**)

| # | sToken | Address | Underlying | Underlying addr (dec) | Logic impl |
|---|--------|---------|-----------|------------------------|------------|
| 0 | **sETH** | `0xbEe9Cf658702527b0AcB2719c1FAA29EdC006a92` | ETH (native) | — | SEther (full contract; no `implementation()`) |
| 1 | sUSDT | `0x69702cfd7DAd8bCcAA24D6B440159404AAA140F5` | USDT (6) | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | `0x20db276e…` |
| 2 | sUSDC | `0x3774E825d567125988Fb293e926064B6FAa71DAB` | USDC (6) | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | `0x20db276e…` |
| 3 | sBUSD | `0x18A908eD663823C908A900b934D6249d4befbE44` | BUSD (18) | `0x4Fabb145d64652a948d72533023f6E7A623C7C53` | `0x20db276e…` |
| 4 | sLINK | `0x3F3B3B269d9f7088B022290906acff8710914be1` | LINK (18) | `0x514910771AF9Ca656af840dff83E8264EcF986CA` | `0x20db276e…` |
| 5 | sUNI | `0x280f76a218DDC8d56B490B5835e251E55a2e8F8d` | UNI (18) | `0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984` | `0x20db276e…` |
| 6 | sWBTC | `0x9d1C2A187cf908aEd8CFAe2353Ef72F06223d54D` | WBTC (8) | `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599` | `0x20db276e…` |
| 7 | **sCOMP** (#1) | `0xa28d2ec98c6bb076a2e152dc9e0d94c8c01e36b0` | COMP (18) | `0xc00e94Cb662C3520282E6f5717214004A7f26888` | `0x980c889b…` (variant) |
| 8 | **sCOMP** (#2) | `0xb7E11002228D599F2a64b0C44D2299C9c644ff26` | COMP (18) | `0xc00e94Cb662C3520282E6f5717214004A7f26888` | `0x20db276e…` |
| 9 | sSXP | `0xdBee1d8C452c781C17Ea20115CbaD0d5f627a680` | SXP (18) | `0x8CE9137d39326AD0cD6491fb5CC0CbA0e089b6A9` | `0x20db276e…` |
| 10 | sSTRK | `0x4164e5b047842Ad7dFf18fc6A6e63a1e40610f46` | STRK (18) | `0x74232704659ef37c08995e386A2E26cc27a8d7B1` | `0x20db276e…` |
| 11 | sUST | `0xa9bA206cfb0548bF93eF1040dDDD5121da9eaf85` | UST (6) | `0xa693B19d2931d498c5B318dF961919BB4aee87a5` | `0x2a803b33…` (variant) |
| 12 | sAPE | `0xf24A7D2077285E192Aa7dF957a4a699c144510d8` | APE (18) | `0x4d224452801ACEd8B2F0aebE155379bb5D594381` | `0x20db276e…` |
| 13 | sDAI | `0x54a0eD40aBeA082Ed62C3a4F92621b8eD47732a2` | DAI (18) | `0x6B175474E89094C44Da98b954EedeAC495271d0F` | `0x20db276e…` |
| 14 | sXCN | `0xC13fdf3aF7eC87dca256d9c11FF96405d360f522` | XCN (18) | `0xA2cd3D43c775978A96BDBf12d733D5A1ED94fb18` | `0xa6d0a145…` (variant) |
| 15 | sWSTETH | `0x1eBfd36223079DC79feFc62260dB9E25f3F5e2C7` | wstETH (18) | `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0` | `0x20db276e…` |
| 16 | sRETH | `0x34c93F84181f566a642aa6Bc2af6caC29C3246E3` | rETH (18) | `0xae78736Cd615f374D3085123A210448E74Fc6393` | `0x20db276e…` |
| 17 | sCRVUSD | `0xfd814C643d389ec095389Da6a5C99684BEB7f905` | crvUSD (18) | `0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E` | `0x72a40277…` (variant) |

> **Two simultaneous sCOMP markets** (#7 `0xa28d…` impl `0x980c889b…` and #8 `0xb7e1…` impl `0x20db276e…`) — both `isListed=true`. #8 is the active one; treat #7 as a deprecated duplicate. Distinguish by address.
> sToken addresses are **not** CREATE2-derived — each SErc20Delegator is separately deployed. Enumerate via `getAllMarkets()`; do not hardcode.

### 3.3 Interest-rate models (active, from live `sToken.interestRateModel()`)

| IRM address | Markets using it |
|-------------|------------------|
| `0xe24e4ba45bdd013ac3180e404a8cfbbbaa2b4db2` | sUSDT, sUSDC, sBUSD, sWBTC, sUST, sDAI, sCRVUSD (stable/BTC model) |
| `0x2ba2fb8c787a2e471532e1f9555d3bf9856c289a` | sETH, sLINK, sUNI, sCOMP#1 |
| `0x2a5cdad0e9d958a435c1c832da2c8c108fe5e034` | sSXP, sSTRK, sAPE, sXCN |
| `0x8ad13c44b76eaeab5b99d9cc71848a198e672307` | sWSTETH, sRETH (LST model) |

> Many historical `*_MIP_*`-style IRM versions exist; read each market's live model rather than hardcoding.

---

## 4. Cross-chain summary

| Chain | ID | Strike lending? | Unitroller | Comptroller impl | PriceOracle | STRK | Markets |
|-------|----|-----------------|-----------|------------------|-------------|------|---------|
| **Ethereum** | 1 | ✅ | `0xe2e17b2C…2602` | `0xd01ce4a7…a694` | `0x4386c6d6…2674` | `0x74232704…d7B1` | 18 |
| Base | 8453 | ❌ not deployed | — | — | — | — | 0 |
| BNB Smart Chain | 56 | ❌ not deployed | — | — | — | — | 0 |
| Avalanche | 43114 | ❌ not deployed | — | — | — | — | 0 |
| Arbitrum One | 42161 | ❌ not deployed | — | — | — | — | 0 |
| Optimism | 10 | ❌ not deployed | — | — | — | — | 0 |
| Polygon PoS | 137 | ❌ not deployed | — | — | — | — | 0 |

**Strike is a single-chain (Ethereum) protocol.** Every distinctive contract — Unitroller `0xe2e17b2C…`, Comptroller impl `0xd01ce4a7…`, SErc20Delegate `0x20db276e…`, PriceOracle `0x4386c6d6…`, STRK `0x74232704…`, sETH `0xbEe9Cf65…` — returns empty `eth_getCode` (`0x`) on all six other chains.

### Name-collision / decoy warning (BNB Smart Chain)
- **BSC `0x9f8c1b7831fa308949dd0bbd2251161110a11252`** is a **decoy** "Strike Protocol (STRK)" token — **9 decimals**, Solidity 0.6.12, Uniswap-V2 fee logic, ~21 holders. It is NOT the real Strike STRK (which is 18-decimal on Ethereum) and there is no Strike lending market behind it.
- A separate **Strike Finance perpetuals DEX on Cardano** (non-EVM) and the **Strike Bitcoin/Lightning payments company** are unrelated projects. The correct protocol here is the Compound-fork money market (DeFiLlama slug `strike`).

---

## 5. Chains with NO Strike deployment

**Base (8453), BNB Smart Chain (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon PoS (137): Strike is NOT deployed.** Confirmed by `eth_getCode` returning `0x` for all distinctive Strike contracts on each chain, and by the absence of any Strike address registry / docs entry for these chains (`docs.strike.org/getting-started/networks` lists only a single "Mainnet" tab = Ethereum). Do not author Strike monitors for these chains; any "Strike" contract claimed there is a different protocol or a fork/decoy.

> Historical note: Strike's GitHub `networks/mainnet.json` is an **unmodified Compound V2 fork artifact** — it contains Compound's addresses (e.g. `STRK=0xc00e94Cb…`=COMP token, `Unitroller=0x3d98…`=Compound Comptroller, `Maximillion=0xf859A1AD…`="Compound: Contract 1"). **Do not use the repo's `networks/` JSON for Strike addresses** — use `docs.strike.org` + live on-chain reads (as done here).

---

## 6. Proxies (old + new)

| Contract | Pattern | How to read the impl | Verified (Ethereum) |
|----------|---------|----------------------|---------------------|
| **Unitroller** (Comptroller) | **Compound Unitroller** — NOT EIP-1967. Impl in **storage slot 2** (`comptrollerImplementation`), pending in slot 3; `admin` slot 0, `pendingAdmin` slot 1. | `comptrollerImplementation()` (`0xbb82aa5e`) or `eth_getStorageAt(slot 2)`. | slot0=`…c3c4c0aa…` (ADMIN_EOA), slot2=`…d01ce4a7…a694`=Comptroller ✓; EIP-1967 impl slot = `0x0` ✓ |
| **sToken** (SErc20Delegator) | **Compound delegator** — NOT EIP-1967. `implementation` is a plain storage var; upgraded via `_setImplementation(address,bool,bytes)`. | `implementation()` (`0x5c60da1b`). | sUSDC/sSTRK `implementation()`=`0x20db276e…` ✓; EIP-1967 slot = `0x0` ✓ |
| **sETH** (SEther) | **immutable full contract** — no delegator, no proxy. | n/a — `implementation()` reverts; bytecode self-contained (codelen 19842). | confirmed: no `underlying()`/`implementation()` ✓ |
| **SErc20Delegate** (`0x20db276e…` + variants) | **immutable logic** contract (the delegatee). | n/a. | codelen 23009 ✓ |
| **Comptroller impl** (`0xd01ce4a7…`) | **immutable logic** contract. | n/a. | codelen 24551 ✓ |
| **PriceOracle** (`0x4386c6d6…`) | plain admin contract (NOT EIP-1967; `admin`=`0xc7b365c2…`). | n/a; `getUnderlyingPrice` live. | EIP-1967 impl slot empty (not read as proxy); behaves as a direct contract. |
| **STRK / Timelock / GovernorAlpha** | **immutable** (Compound stack). | n/a. | STRK codelen 11651, Timelock 5955. |

```
Unitroller storage layout (Compound):
  slot 0 = admin                       (= ADMIN_EOA 0xc3c4c0aa…)
  slot 1 = pendingAdmin
  slot 2 = comptrollerImplementation   ← live Comptroller logic (0xd01ce4a7…)
  slot 3 = pendingComptrollerImplementation
EIP-1967 impl slot 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc — EMPTY on Unitroller & all sTokens
```

---

## 7. Detection invariants & gotchas

1. **Per-block, not timestamp.** `accrualBlockNumber()` returns a **block number**; rates are `supplyRatePerBlock()`/`borrowRatePerBlock()`. Calling `*PerTimestamp`/`accrualBlockTimestamp` reverts. (Contrast Moonwell, which is timestamp-based.)
2. **`AccrueInterest` is 4-arg** (`0x4dec04e7…`, 128-byte data) — confirmed in the SErc20Delegate bytecode (the 3-arg `0x875352fb…` is absent) and in live logs. 3-arg decoders mis-parse it.
3. **`Mint` topic0 collides with Uniswap V2** (`0x4c209b5f…`) — always filter by emitter (an sToken). Same for ERC-20 `Transfer`/`Approval`.
4. **STRK rewards are on the Comptroller, split-speed.** Watch `DistributedSupplierStrike`/`DistributedBorrowerStrike` (both indexed sToken+account) and `StrikeSupplySpeedUpdated`/`StrikeBorrowSpeedUpdated`. There is **no** single-speed `StrikeSpeedUpdated`/`MarketStriked` and **no** separate reward distributor contract. Read speeds via `strikeSupplySpeeds`/`strikeBorrowSpeeds` (the legacy `strikeSpeeds` mapping is still populated).
5. **No supply/borrow caps in the live Comptroller.** `NewBorrowCap`/`NewSupplyCap`/`NewBorrowCapGuardian` are absent from the impl — do not expect cap events.
6. **Pausing uses ONLY the per-market 3-arg `ActionPaused(address,string,bool)`** (`0x71aec636…`). The global 2-arg overload (`0xef159d9a…`) is NOT in the impl, even though `_setTransferPaused`/`_setSeizePaused` exist (they flip state silently).
7. **Two sCOMP markets coexist** (`0xa28d…` and `0xb7e1…`), both listed, with different logic impls. Liquidity-monitoring keyed on "the COMP market" must disambiguate by address (use `0xb7e1…`, the active one).
8. **sETH is a distinct contract family.** No `underlying()`/`implementation()`; supply/borrow/repay/liquidate use the *payable* overloads (`mint()`, `repayBorrow()`, `repayBorrowBehalf(address)`, `liquidateBorrow(address,address)`) with different selectors than the SErc20 versions.
9. **Admin is split by layer — watch BOTH the EOA and the Timelock.** The **Unitroller** and the **Timelock** are admined by the EOA `0xc3c4c0aa…` (codelen 0), so *Comptroller-level* admin actions (`_setCollateralFactor`, `_supportMarket`, `_setPriceOracle`, `_setMintPaused`/`_setBorrowPaused`/`_setTransferPaused`/`_setSeizePaused`, reward-speed setters, `_grantStrike`, Unitroller upgrade) come FROM that EOA — watch it. But **every active sToken's `admin()` is the Timelock** `0xe789af79…` (verified live on sETH/sUSDT/sUSDC/sWBTC/sSTRK/sCRVUSD/sRETH/sWSTETH/sAPE/sCOMP#2), so *market-level* admin actions (`_setReserveFactor`, `_setInterestRateModel`, `_reduceReserves`, `_setImplementation`) are NOT EOA-direct — they appear as Timelock `QueueTransaction`/`ExecuteTransaction`. The Timelock has no recent logs (protocol is quiet) but is the on-chain authority over the sTokens. (Exception: deprecated sCOMP#1 `0xa28d…` is admined by the deployer EOA `0x752dfb1c…`.)
10. **sTokens are 8 decimals; underlying decimals vary** (USDC/USDT/UST 6, WBTC 8, BUSD/DAI/most others 18). `exchangeRateStored` scaled by `1e(18 + underlyingDec − 8)`; `getUnderlyingPrice` returns a mantissa scaled to `36 − underlyingDec`.
11. **Liquidations:** `LiquidateBorrow` on the borrowed sToken carries `sTokenCollateral`+`seizeTokens`; the seized market emits a sToken-share `Transfer` to the liquidator. (No `NewProtocolSeizeShare` / protocol-cut in this delegate version.)
12. **Markets are enumerated, not derived** — read `getAllMarkets()` (currently 18); each sToken is a standalone delegator.
13. **Decoys:** the BSC "STRK" `0x9f8c1b78…` (9-dec, Uniswap fee token) and the repo's `networks/mainnet.json` (Compound's addresses) are traps — neither reflects the real Strike deployment.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- sToken
TOPIC_ACCRUE_INTEREST        = '\x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04'  -- 4-arg!
TOPIC_MINT                   = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'  -- collides w/ UniV2 Mint
TOPIC_REDEEM                 = '\xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929'
TOPIC_BORROW                 = '\x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'
TOPIC_REPAY_BORROW           = '\x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1'
TOPIC_LIQUIDATE_BORROW       = '\x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
TOPIC_RESERVES_ADDED         = '\xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5'
TOPIC_RESERVES_REDUCED       = '\x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e'
TOPIC_NEW_RESERVE_FACTOR     = '\xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460'
TOPIC_NEW_MARKET_IRM         = '\xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926'
TOPIC_ERC20_TRANSFER         = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_FAILURE                = '\x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0'
-- Comptroller (live impl)
TOPIC_MARKET_LISTED          = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_MARKET_ENTERED         = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'
TOPIC_MARKET_EXITED          = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_NEW_CLOSE_FACTOR       = '\x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9'
TOPIC_NEW_COLLATERAL_FACTOR  = '\x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5'
TOPIC_NEW_LIQ_INCENTIVE      = '\xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316'
TOPIC_NEW_PRICE_ORACLE       = '\xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22'
TOPIC_NEW_PAUSE_GUARDIAN     = '\x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e'
TOPIC_ACTION_PAUSED_MARKET   = '\x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0'  -- (address,string,bool) ONLY
-- Comptroller STRK rewards (split-speed)
TOPIC_DIST_SUPPLIER_STRIKE   = '\x926dc6130c8a69503e637fa5aed5b3ba65bd6d241957047e4bcc24485e0c48fb'
TOPIC_DIST_BORROWER_STRIKE   = '\x730ec20a857394345ba1d81394d16c333202df6c655e85f7cf16c65954def57e'
TOPIC_STRIKE_SUPPLY_SPEED    = '\x898847f275797e75839591f6be6df865612ff8dc0f9f3a169897a3fac1415cdc'
TOPIC_STRIKE_BORROW_SPEED    = '\xd849eae9f25bdb1c95a86ded3675b83bcbf3fa8e8b784375dc1f0fb13617dd15'
TOPIC_STRIKE_GRANTED         = '\x96d2fd0650b0c3afb0e7857c50126f0824d10b3b5156ae4e077ed7ccc18236c4'
-- Unitroller
TOPIC_NEW_IMPLEMENTATION     = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'
TOPIC_NEW_PENDING_IMPL       = '\xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815'
-- STRK token
TOPIC_DELEGATE_CHANGED       = '\x3134e8a2e6d97e929a7e54011ea5485d7d196dd5f0ba4d4ef95803e8e3fc257f'
TOPIC_DELEGATE_VOTES_CHANGED = '\xdec2bacdd2f05b59de34da9b523dff8be42e5e38e818c82fdb0bae774387a724'
-- GovernorAlpha
TOPIC_PROPOSAL_CREATED       = '\x7d84a6263ae0d98d3329bd7b46bb4e8d6f98cd35a7adb45c274c8b7fd5ebd5e0'
TOPIC_VOTE_CAST_ALPHA        = '\x877856338e13f63d0c36822ff0ef736b80934cd90574a3a5bc9262c39d217c46'
TOPIC_PROPOSAL_QUEUED        = '\x9a2e42fd6722813d69113e7d0079d3d940171428df7373df9c7f7617cfda2892'
TOPIC_PROPOSAL_EXECUTED      = '\x712ae1383f79ac853f8d882153778e0260ef8f03b504e2866e0593e04d2b291f'
-- Timelock
TOPIC_TL_QUEUE               = '\x76e2796dc3a81d57b0e8504b647febcbeeb5f4af818e164f11eef8131a6a763f'
TOPIC_TL_EXECUTE             = '\xa560e3198060a2f10670c1ec5b403077ea6ae93ca8de1c32b451dc1a943cd6e7'
-- PriceOracle
TOPIC_PRICE_POSTED           = '\xdd71a1d19fcba687442a1d5c58578f1e409af71a79d10fd95a4d66efd8fa9ae7'

-- ===== Selectors =====
SEL_MINT                     = '\xa0712d68'   -- mint(uint256)  (SErc20)
SEL_MINT_ETH                 = '\x1249c58b'   -- mint()         (sETH, payable)
SEL_REDEEM                   = '\xdb006a75'
SEL_REDEEM_UNDERLYING        = '\x852a12e3'
SEL_BORROW                   = '\xc5ebeaec'
SEL_REPAY_BORROW             = '\x0e752702'   -- repayBorrow(uint256) (SErc20)
SEL_REPAY_BORROW_ETH         = '\x4e4d9fea'   -- repayBorrow()        (sETH)
SEL_REPAY_BORROW_BEHALF      = '\x2608f818'   -- (address,uint256) SErc20
SEL_REPAY_BEHALF_ETH         = '\xe5974619'   -- (address) sETH
SEL_LIQUIDATE_BORROW         = '\xf5e3c462'   -- (address,uint256,address) SErc20
SEL_LIQUIDATE_BORROW_ETH     = '\xaae40a2a'   -- (address,address) sETH
SEL_SEIZE                    = '\xb2a02ff1'
SEL_EXCHANGE_RATE_STORED     = '\x182df0f5'
SEL_SUPPLY_RATE_PER_BLOCK    = '\xae9d70b0'
SEL_BORROW_RATE_PER_BLOCK    = '\xf8f9da28'
SEL_ACCRUAL_BLOCK_NUMBER     = '\x6c540baf'
SEL_GET_CASH                 = '\x3b1d21a2'
SEL_UNDERLYING               = '\x6f307dc3'
SEL_STOKEN_IMPLEMENTATION    = '\x5c60da1b'   -- implementation()  (sToken delegator)
SEL_COMPTROLLER_IMPL         = '\xbb82aa5e'   -- comptrollerImplementation()  (Unitroller)
SEL_GET_ALL_MARKETS          = '\xb0772d0b'
SEL_GET_ACCOUNT_LIQUIDITY    = '\x5ec88c79'
SEL_ENTER_MARKETS            = '\xc2998238'
SEL_EXIT_MARKET              = '\xede4edd0'
SEL_ORACLE                   = '\x7dc0d1d0'
SEL_GET_UNDERLYING_PRICE     = '\xfc57d4df'
SEL_STRIKE_SUPPLY_SPEEDS     = '\x21f5492b'
SEL_STRIKE_BORROW_SPEEDS     = '\x2b5fc299'
SEL_STRIKE_SPEEDS_LEGACY     = '\xca9a7a63'
SEL_CLAIM_STRIKE             = '\x871f1e79'   -- claimStrike(address)
SEL_MAX_REPAY_BEHALF         = '\x9f35c3d5'   -- Maximillion repayBehalf(address)
SEL_DELEGATE                 = '\x5c19a95c'

-- ===== Ethereum (chain 1) — the ONLY chain =====
ETH_UNITROLLER               = '\xe2e17b2cbbf48211fa7eb8a875360e5e39ba2602'
ETH_COMPTROLLER_IMPL         = '\xd01ce4a7368cf81c34b1257691eedf34d825a694'
ETH_SERC20_DELEGATE          = '\x20db276ea50373497863496354d9bd5cf5a6b54c'
ETH_PRICE_ORACLE             = '\x4386c6d63a4b10e4bc5a5191d8c5c7fa55402674'
ETH_STRK_TOKEN               = '\x74232704659ef37c08995e386a2e26cc27a8d7b1'
ETH_TIMELOCK                 = '\xe789af79d295b0e4fa1c1e8a1b6fe186c1ae2326'
ETH_ADMIN_EOA                = '\xc3c4c0aaf09ece96af97688198d46ab5e360ff94'  -- admin of Unitroller+Timelock (Comptroller-level); sTokens are admined by the Timelock, not this EOA
ETH_ORACLE_ADMIN             = '\xc7b365c24f6c5cb1574364dcbcd39b2e06485317'
ETH_DEPLOYER                 = '\x752dfb1c709eea4621c8e95f48f3d0b6dde5d126'
-- markets
ETH_sETH                     = '\xbee9cf658702527b0acb2719c1faa29edc006a92'
ETH_sUSDT                    = '\x69702cfd7dad8bccaa24d6b440159404aaa140f5'
ETH_sUSDC                    = '\x3774e825d567125988fb293e926064b6faa71dab'
ETH_sBUSD                    = '\x18a908ed663823c908a900b934d6249d4befbe44'
ETH_sLINK                    = '\x3f3b3b269d9f7088b022290906acff8710914be1'
ETH_sUNI                     = '\x280f76a218ddc8d56b490b5835e251e55a2e8f8d'
ETH_sWBTC                    = '\x9d1c2a187cf908aed8cfae2353ef72f06223d54d'
ETH_sCOMP_1                  = '\xa28d2ec98c6bb076a2e152dc9e0d94c8c01e36b0'  -- deprecated dup
ETH_sCOMP_2                  = '\xb7e11002228d599f2a64b0c44d2299c9c644ff26'  -- active
ETH_sSXP                     = '\xdbee1d8c452c781c17ea20115cbad0d5f627a680'
ETH_sSTRK                    = '\x4164e5b047842ad7dff18fc6a6e63a1e40610f46'
ETH_sUST                     = '\xa9ba206cfb0548bf93ef1040dddd5121da9eaf85'
ETH_sAPE                     = '\xf24a7d2077285e192aa7df957a4a699c144510d8'
ETH_sDAI                     = '\x54a0ed40abea082ed62c3a4f92621b8ed47732a2'
ETH_sXCN                     = '\xc13fdf3af7ec87dca256d9c11ff96405d360f522'
ETH_sWSTETH                  = '\x1ebfd36223079dc79fefc62260db9e25f3f5e2c7'
ETH_sRETH                    = '\x34c93f84181f566a642aa6bc2af6cac29c3246e3'
ETH_sCRVUSD                  = '\xfd814c643d389ec095389da6a5c99684beb7f905'

-- EIP-1967 slots (EMPTY on Unitroller & sTokens — Compound patterns)
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT           = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- DECOY (NOT Strike): BSC 0x9f8c1b7831fa308949dd0bbd2251161110a11252 (9-dec fee token)
```

---

## 9. Verification & sources

- **topic0 / selectors:** all recomputed locally as `keccak256(canonical sig)` / `[0:4]`. Spot-matched to known Compound selectors (`mint`=`0xa0712d68`, `borrow`=`0xc5ebeaec`, `getUnderlyingPrice`=`0xfc57d4df`, `enterMarkets`=`0xc2998238`) and ERC-20 (`Transfer`=`0xddf252ad…`).
- **Accrual model:** `accrualBlockNumber()` on sUSDC returns `0x17c3664` (= block 24,917,604, a block number); `supplyRatePerBlock()`/`borrowRatePerBlock()` return live values — **per-block**, stock Compound V2.
- **`AccrueInterest` arity:** the SErc20Delegate bytecode (`0x20db276e…`) **contains** the 4-arg topic `0x4dec04e7…` and **does not contain** the 3-arg topic `0x875352fb…`; live logs on sETH/sUSDC/sUSDT carry **128 bytes** (4×uint256). Definitive: 4-arg.
- **Comptroller event set:** confirmed against the live impl bytecode (`0xd01ce4a7…`): present = `MarketListed`, `MarketEntered/Exited`, `NewCloseFactor`, `NewCollateralFactor`, `NewLiquidationIncentive`, `NewPriceOracle`, `NewPauseGuardian`, `ActionPaused(address,string,bool)`, `Distributed{Supplier,Borrower}Strike`, `Strike{Supply,Borrow}SpeedUpdated`, `StrikeGranted`, `ContributorStrikeSpeedUpdated`, `Failure`; absent = global `ActionPaused(string,bool)`, `NewBorrowCap*`, single-speed `StrikeSpeedUpdated`, `MarketStriked`, `NewProtocolSeizeShare`. `Distributed{Supplier,Borrower}Strike` and STRK `Delegate{Changed,VotesChanged}` additionally confirmed in live logs.
- **Addresses & wiring (live):** `Comptroller.comptrollerImplementation()`→`0xd01ce4a7…`, `oracle()`→`0x4386c6d6…`, `getAllMarkets()`=18 (enumerated, mapped to symbols/underlyings/IRMs above); each sToken `implementation()`→`0x20db276e…` (variants `0x980c889b…`/`0x2a803b33…`/`0xa6d0a145…`/`0x72a40277…` confirmed via the market's `implementation()`), `comptroller()`→Unitroller, `underlying()` & `decimals()`=8 verified, sUSDC `symbol()`="sUSDC"/`name()`="Strike USDC"; Unitroller storage slot0=admin EOA `0xc3c4c0aa…`, slot2=impl `0xd01ce4a7…`, EIP-1967 slot empty; STRK `name()`="Strike Token"/`symbol()`="STRK"/`decimals()`=18; PriceOracle `getUnderlyingPrice(sETH)` returns a live mantissa (~`$1.69e3`), `admin()`=`0xc7b365c2…`. Ground-truth addresses = `docs.strike.org` (mainnet tab) + on-chain reads. Deployer label `Strike ETH: Deployer 0x752dfb1c…` from Etherscan.
- **Admin topology (live `admin()` reads):** Unitroller `admin()`=`0xc3c4c0aa…` (EOA), Timelock `admin()`=`0xc3c4c0aa…` (EOA), but **every active sToken `admin()`=`0xe789af79…` (the Timelock)** — confirmed on sETH/sUSDT/sUSDC/sWBTC/sSTRK/sCRVUSD/sRETH/sWSTETH/sAPE/sCOMP#2. The deprecated sCOMP#1 (`0xa28d…`) `admin()`=deployer EOA `0x752dfb1c…` and is listed with collateral-factor 0 (`markets()`→(true,0,false)). The Timelock has 0 logs in the recent 2M blocks.
- **AccrueInterest arity (live):** observed on sUSDC near block 24,917,604 (= its `accrualBlockNumber()` `0x17c3664`) with **128-byte** data (4×uint256), alongside a 160-byte `RepayBorrow` (5 fields) — matching the 4-arg form. Activity is sparse (sUSDC otherwise emitted no logs in the last ~6M blocks), so the bytecode test (4-arg topic present, 3-arg absent in `0x20db276e…`) is the definitive check.
- **STRK rewards (live):** `DistributedSupplierStrike` still fires recently (e.g. ≥4 events in [25,222,905..25,272,904], latest at block 25,263,078) with ntopics=3 (2 indexed addresses) + 64-byte data — confirming the split-speed model is active.
- **Non-deployment:** Unitroller, Comptroller impl, SErc20Delegate, PriceOracle, STRK, and sETH all return empty `eth_getCode` on Base, BNB, Avalanche, Arbitrum, Optimism, Polygon.
- **UNVERIFIED (recorded, not omitted):**
  - **GovernorAlpha address** — `docs.strike.org` lists `0x2Cc7f36f5FFfe1f8880409f71240aAd71b1b802c`, but that address returns `eth_getCode`=`0x` (empty) on mainnet; the live Strike GovernorAlpha address was not independently confirmed. (Comptroller-level policy is currently exercised via the admin EOA `0xc3c4c0aa…`; the Timelock — itself admined by that EOA — is the `admin()` of the sTokens but has had no recent activity.) The GovernorAlpha/Bravo **topic0s and selectors** in §1.6/§2.5 are still valid for whatever the live governor is (standard Compound governor ABI). The repo's `networks/mainnet.json` lists yet another GovernorAlpha value (`0xc0dA01a0…`) — also a Compound-fork artifact, not confirmed as Strike's live governor.
  - **Maximillion address** — not in the Strike docs; the repo's value (`0xf859A1AD…`) is Compound's (Etherscan-labeled "Compound: Contract 1"), and no contract was observed calling `repayBorrowBehalf` on sETH (the single live sETH repay was a self-repay). Strike's own Maximillion was not located; the **selectors** in §2.4 are the standard Maximillion ABI.
  - Several **older SErc20Delegate logic variants** back specific markets (sCOMP#1 `0x980c889b…`, sUST `0x2a803b33…`, sXCN `0xa6d0a145…`, sCRVUSD `0x72a40277…`). Each is `eth_getCode`-present and reachable via the market's `implementation()`; their per-variant event/feature deltas were not individually diffed (the dominant `0x20db276e…` impl was).

Authoritative sources:
- [`StrikeFinance/strike-protocol`](https://github.com/StrikeFinance/strike-protocol) — Solidity source (`SToken`, `SErc20Delegator/Delegate`, `SEther`, `Comptroller`, `Unitroller`, `PriceOracle`, `Maximillion`, `Strk`, `GovernorAlpha`, `Timelock`). **NB: its `networks/mainnet.json` is an unmodified Compound fork artifact — do not use it for Strike addresses.** Confirmed: it lists `STRK=0xc00e94Cb…` (= COMP token), `Unitroller=Comptroller=0x3d981921…` (= Compound Comptroller), `Maximillion=0xf859A1AD…`, `sUSDC=0x39AA39c0…` (= cUSDC), `sETH=0x4Ddc2D19…` (= cETH) — all Compound mainnet addresses, none of which match the real Strike deployment in §3.
- [docs.strike.org](https://docs.strike.org) — `getting-started/networks` (mainnet address tab), `stokens`, `comptroller`, `governance`.
- [Compound V2](https://github.com/compound-finance/compound-protocol) — fork ancestor (cToken/Comptroller/Unitroller/GovernorAlpha/Timelock/Maximillion).
- Etherscan (Ethereum) — contract labels, deployer, bytecode verification.
- RPC: publicnode `ethereum-rpc` (+ `base-rpc`, `bsc-rpc`, `avalanche-c-chain-rpc`, `arbitrum-one-rpc`, `optimism-rpc`, `polygon-bor-rpc` for non-deployment checks).
