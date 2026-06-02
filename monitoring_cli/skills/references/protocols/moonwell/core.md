# Moonwell — Topics, Selectors, Addresses (Base, Optimism; + Ethereum gov-hub, Moonbeam/Moonriver origins)

**Status:** verified against Base (8453) and Optimism (10) mainnet RPC and the canonical `moonwell-fi/moonwell-contracts-v2` repo on 2026-05-29. Every topic0/selector computed locally with keccak; every Base/OP address `eth_getCode`-checked; proxy wiring read live from storage + getters.
**Scope:** the seven chains the user asked about — **Moonwell lending is deployed on only TWO of them: Base and Optimism.** Ethereum hosts the WELL/xWELL token + MultichainGovernor **but no lending markets**. **Moonwell is NOT deployed on BNB, Avalanche, Arbitrum, or Polygon PoS** (no `chains/<id>.json`, no docs entry, no DeFiLlama TVL; Base Unitroller/Comptroller addresses return empty `eth_getCode` on all four). The original Moonbeam (1284, "Artemis") and Moonriver (1285, "Apollo") deployments — outside the requested set — are summarized in §11 for completeness.

Moonwell is a **Compound V2 fork** with renamed types: cToken → **MToken**, CErc20Delegator → **MErc20Delegator** (the per-market proxy), CErc20Delegate → **MErc20Delegate** (`MTOKEN_IMPLEMENTATION`), Comptroller behind a **Unitroller** proxy. Three deviations from stock Compound V2 matter for monitoring and are the cause of most integration bugs:

1. **Timestamp-based accrual, not per-block.** Interest accrues on `block.timestamp`. The accessors are `supplyRatePerTimestamp()` / `borrowRatePerTimestamp()` (per-second mantissas) and `accrualBlockTimestamp()` (a unix timestamp). **There is no `supplyRatePerBlock` / `borrowRatePerBlock` / `accrualBlockNumber`** — code that calls them reverts.
2. **`AccrueInterest` is the 4-arg form** `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` (topic0 `0x4dec04e7…`), **not** stock Compound's 3-arg `AccrueInterest(uint256,uint256,uint256)`. Verified live: Base mUSDC logs carry **128 bytes** of data (= 4×uint256).
3. **Rewards live in a separate MultiRewardDistributor (MRD), not the Comptroller.** There are **no** COMP-style `DistributedSupplierComp` / `DistributedBorrowerComp` events on the Comptroller. Reward index/disbursal events are emitted by the MRD with split supply/borrow names. The Comptroller's `claimReward(...)` just proxies into the MRD.

Governance is **cross-chain via Wormhole**: a MultichainGovernor publishes VAAs that each lending chain's **TemporalGovernor** consumes (`queueProposal(bytes)` → `executeProposal(bytes)`). The TemporalGovernor is the `admin` of the Unitroller and every mToken. The governance origin is being moved from Moonbeam to Ethereum mainnet (MIP-X58): the Ethereum `MULTICHAIN_GOVERNOR_V2_PROXY` is deployed and live (verified on-chain), but the full cutover from the Moonbeam MultichainGovernor was still in progress as of 2026-05 — treat **both** the Moonbeam and Ethereum governors as potentially-authoritative VAA sources until the cutover is confirmed executed.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 MToken / MErc20 (per-market; the workhorse events)

| topic0 | Event |
|--------|-------|
| `0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04` | `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address minter, uint256 mintAmount, uint256 mintTokens)` |
| `0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929` | `Redeem(address redeemer, uint256 redeemAmount, uint256 redeemTokens)` |
| `0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80` | `Borrow(address borrower, uint256 borrowAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1` | `RepayBorrow(address payer, address borrower, uint256 repayAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address liquidator, address borrower, uint256 repayAmount, address mTokenCollateral, uint256 seizeTokens)` |
| `0xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5` | `ReservesAdded(address benefactor, uint256 addAmount, uint256 newTotalReserves)` |
| `0x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e` | `ReservesReduced(address admin, uint256 reduceAmount, uint256 newTotalReserves)` |
| `0xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460` | `NewReserveFactor(uint256 oldReserveFactorMantissa, uint256 newReserveFactorMantissa)` |
| `0xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926` | `NewMarketInterestRateModel(address oldIRM, address newIRM)` |
| `0x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d` | `NewComptroller(address oldComptroller, address newComptroller)` |
| `0xf5815f353a60e815cce7553e4f60c533a59d26b1b5504ea4b6db8d60da3e4da2` | `NewProtocolSeizeShare(uint256 oldShare, uint256 newShare)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` — mToken shares |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` — soft-fail; pre-revert legacy path |

> **`Mint` topic0 collides with Uniswap V2's `Mint`** (`0x4c209b5f…`, same `Mint(address,uint256,uint256)` signature). Distinguish by emitter address. Same for `Transfer`/`Approval` (every ERC-20).

### 1.2 Comptroller (one per chain, behind Unitroller)

| topic0 | Event |
|--------|-------|
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address mToken)` |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address mToken, address account)` |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address mToken, address account)` |
| `0x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9` | `NewCloseFactor(uint256 oldCloseFactorMantissa, uint256 newCloseFactorMantissa)` |
| `0x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5` | `NewCollateralFactor(address mToken, uint256 oldCFMantissa, uint256 newCFMantissa)` |
| `0xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316` | `NewLiquidationIncentive(uint256 oldIncentiveMantissa, uint256 newIncentiveMantissa)` |
| `0xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22` | `NewPriceOracle(address oldOracle, address newOracle)` |
| `0x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6` | `NewBorrowCap(address indexed mToken, uint256 newBorrowCap)` |
| `0xeda98690e518e9a05f8ec6837663e188211b2da8f4906648b323f2c1d4434e29` | `NewBorrowCapGuardian(address oldBorrowCapGuardian, address newBorrowCapGuardian)` |
| `0x9e0ad9cee10bdf36b7fbd38910c0bdff0f275ace679b45b922381c2723d676f8` | `NewSupplyCap(address indexed mToken, uint256 newSupplyCap)` |
| `0xb0d3622c24ac9bd967d8f37a25808b3e668fe7ed4f3075bbe82842d3e287c044` | `NewSupplyCapGuardian(address oldSupplyCapGuardian, address newSupplyCapGuardian)` |
| `0x8ddca872a7a62d68235cff1a03badc845dc3007cfaa6145379f7bf3452ecb9b9` | `NewRewardDistributor(address oldRewardDistributor, address newRewardDistributor)` |
| `0x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e` | `NewPauseGuardian(address oldPauseGuardian, address newPauseGuardian)` |
| `0xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0` | `ActionPaused(string action, bool pauseState)` — global (Transfer/Seize) |
| `0x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0` | `ActionPaused(address mToken, string action, bool pauseState)` — per-market (Mint/Borrow) |

> Moonwell uses **only these two `ActionPaused` overloads** for pausing — there is **no** `MarketActionPaused` / `MarketSupplyPaused` / `MarketBorrowPaused` / `NewBorrowPaused`.

### 1.3 MultiRewardDistributor (MRD — one proxy per chain; all reward accounting)

| topic0 | Event |
|--------|-------|
| `0xa76959d76a349a0b8fd3120607e3aea6af58897ae6531bfe60a0267c4ea0c272` | `NewConfigCreated(address indexed mToken, address indexed owner, address indexed emissionToken, uint256 supplySpeed, uint256 borrowSpeed, uint256 endTime)` |
| `0xc4d50731808aa5d941c471c0b29364fecd810aa0565344f6cdcab2c873422baf` | `NewSupplyRewardSpeed(address indexed mToken, address indexed emissionToken, uint256 oldSpeed, uint256 newSpeed)` |
| `0x8fc43850ed5c7aaa0ce83829a1a40202c3fcf8257788d69881611dff1a0b32e9` | `NewBorrowRewardSpeed(address indexed mToken, address indexed emissionToken, uint256 oldSpeed, uint256 newSpeed)` |
| `0x6ca67f2e3675f2b549fe77271364ebde88b3c7eb3ef84af329c373ca64fa2578` | `NewEmissionConfigOwner(address indexed mToken, address indexed emissionToken, address currentOwner, address newOwner)` |
| `0x10f16113484fbc6e60553a394eb2a3ae47999b610e4212fad6903486dbca7f92` | `NewRewardEndTime(address indexed mToken, address indexed emissionToken, uint256 oldEndTime, uint256 newEndTime)` |
| `0x3b8f57f20bd4827c21500a7a7f2a3678469e0105bb63283aac9d23728677f8ce` | `GlobalSupplyIndexUpdated(address mToken, address emissionToken, uint224 newSupplyIndex, uint32 newTimestamp)` |
| `0x5559ecfcede13ec3e698c975f248029152126d3b5a5c14bcb780d0af2126964e` | `GlobalBorrowIndexUpdated(address mToken, address emissionToken, uint224 newIndex, uint32 newTimestamp)` |
| `0x51761e1f6548bc99f2a61f299986e1b08a489f06622f689a413e02d7654a4766` | `DisbursedSupplierRewards(address indexed mToken, address indexed supplier, address indexed emissionToken, uint256 totalAccrued)` |
| `0x48a32d6daeb4317b45f49c3a1c0b1bd7d53a175d1f46c425138e328900cdccb4` | `DisbursedBorrowerRewards(address indexed mToken, address indexed borrower, address indexed emissionToken, uint256 totalAccrued)` |
| `0x8b079e2b0be6cc9631b7883d8478590fe708e9d360391aab49aa147901fc7a37` | `InsufficientTokensToEmit(address payable user, address emissionToken, uint256 amount)` |
| `0xc4474c2790e13695f6d2b6f1d8e164290b55370f87a542fd7711abe0a1bf40ac` | `FundsRescued(address token, uint256 amount)` |
| `0x8d2ad4bb95e94ce8d50ed07769a97467ba4db3f80fc0badf6c81d0907a0b410a` | `NewEmissionCap(uint256 oldEmissionCap, uint256 newEmissionCap)` |
| `0xb83b93884b98604cbc549e7e4a81a9e49bd62c603026ec82f04915037258c564` | `RewardsPaused()` |
| `0x24abc2b8df8d63728da8fe06c1555853a3f293f812e1ebd4303a5d6df7173e6c` | `RewardsUnpaused()` |

### 1.4 ChainlinkOracle (Moonwell price oracle; one per chain)

| topic0 | Event |
|--------|-------|
| `0xdd71a1d19fcba687442a1d5c58578f1e409af71a79d10fd95a4d66efd8fa9ae7` | `PricePosted(address asset, uint256 previousPriceMantissa, uint256 requestedPriceMantissa, uint256 newPriceMantissa)` |
| `0xd9e7d1778ca05570ced72c9aeb12a41fcc76f7f57ea25853dea228f8836d0022` | `FeedSet(address feed, string symbol)` |

### 1.5 TemporalGovernor (Wormhole cross-chain governor; one per chain)

| topic0 | Event |
|--------|-------|
| `0xc486294e67e6b98e19d854bb8a606f314e248d45e842a98b09a51be7b13ce2a5` | `QueuedTransaction(address target, address[] targets, uint256[] values, bytes[] datas)` |
| `0xaf022f6b53b11c364e2dfc0aea08eb9416c94f2661451ea82ead8831385617a6` | `ExecutedTransaction(address target, uint256 value, bytes data)` |
| `0xad5ad009fb0380817906297d4db849c9a30b93e0d3761c005ef8c487d9239224` | `TrustedSenderUpdated(uint16 chainId, address addr, bool added)` |
| `0x309f3735db2677e216920b5dc9d0b76108f0fa9fc1176a6701bd4e77f5065ac1` | `GuardianPauseGranted(uint256 indexed timestamp)` |
| `0x01c6520cf747e4632b43b535b91afe3950ccabc4ab29bbd89e3c1f6b0ba05655` | `GuardianChanged(address newGuardian)` |
| `0x0c92d12d8037dd6d77aed8d12addd54d5eb2a6801541a1bf87c9822e78eea421` | `GuardianRevoked(address oldGuardian)` |
| `0x5607d774129cad49296363738883d35576762c63e621f31b16c5e2214e2c03b4` | `PermissionlessUnpaused(uint256 indexed timestamp)` |

> `QueuedTransaction`/`ExecutedTransaction` (NOT "QueueProposal"/"ExecutedProposal"). TemporalGovernor consumes inbound Wormhole VAAs — there is no `publishMessage`.

### 1.6 Unitroller (Comptroller proxy — admin/upgrade events)

| topic0 | Event |
|--------|-------|
| `0xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815` | `NewPendingImplementation(address oldPendingImplementation, address newPendingImplementation)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |

---

## 2. Function signatures (chain-agnostic)

Selectors = `keccak256(canonical signature)[0:4]`, verified against deployed bytecode on Base + Optimism. Source: `moonwell-fi/moonwell-contracts-v2` (`src/`). Interface-file `uint` is canonicalized to `uint256`.

### 2.1 MErc20 / MToken (per-market)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa0712d68` | `mint(uint256 mintAmount)` | Supply underlying, receive mTokens. Emits `Mint`+`AccrueInterest`+`Transfer`. |
| `0xd0248fb4` | `mintWithPermit(uint256,uint256,uint8,bytes32,bytes32)` | EIP-2612 permit + mint (Moonwell addition). |
| `0xdb006a75` | `redeem(uint256 redeemTokens)` | Burn mTokens for underlying. |
| `0x852a12e3` | `redeemUnderlying(uint256 redeemAmount)` | Redeem an exact underlying amount. |
| `0xc5ebeaec` | `borrow(uint256 borrowAmount)` | Emits `Borrow`. |
| `0x0e752702` | `repayBorrow(uint256 repayAmount)` | `type(uint).max` repays full debt. |
| `0x2608f818` | `repayBorrowBehalf(address borrower, uint256 repayAmount)` | |
| `0xf5e3c462` | `liquidateBorrow(address borrower, uint256 repayAmount, address mTokenCollateral)` | Emits `LiquidateBorrow`. |
| `0xb2a02ff1` | `seize(address liquidator, address borrower, uint256 seizeTokens)` | Cross-market collateral seizure. |
| `0xa9059cbb` | `transfer(address dst, uint256 amount)` | mToken shares. |
| `0x23b872dd` | `transferFrom(address src, address dst, uint256 amount)` | |
| `0x095ea7b3` | `approve(address spender, uint256 amount)` | |
| `0x3af9e669` | `balanceOfUnderlying(address owner)` | State-mutating (accrues). Returns underlying-denominated balance. |
| `0xc37f68e2` | `getAccountSnapshot(address)` | `(uint err, uint mTokenBalance, uint borrowBalance, uint exchangeRateMantissa)` |
| `0xa6afed95` | `accrueInterest()` | Emits `AccrueInterest`. |
| `0xbd6d894d` | `exchangeRateCurrent()` | Accrues, then returns exchange rate (scaled by 1e18 × underlying-decimal adjustment). |
| `0x182df0f5` | `exchangeRateStored()` | View; last-stored rate. |
| `0x17bfdfbc` | `borrowBalanceCurrent(address)` | Accrues then returns debt. |
| `0x95dd9193` | `borrowBalanceStored(address)` | View. |
| `0x73acee98` | `totalBorrowsCurrent()` | |
| `0x3b1d21a2` | `getCash()` | Underlying held by the mToken. |
| `0xd3bd2c72` | `supplyRatePerTimestamp()` | **Per-second** supply rate mantissa (NOT per-block). |
| `0xcd91801c` | `borrowRatePerTimestamp()` | **Per-second** borrow rate mantissa. |
| `0xcfa99201` | `accrualBlockTimestamp()` | **Unix timestamp** of last accrual (NOT block number). |
| `0x47bd3718` | `totalBorrows()` | |
| `0x8f840ddd` | `totalReserves()` | |
| `0xaa5af0fd` | `borrowIndex()` | |
| `0x173b9904` | `reserveFactorMantissa()` | |
| `0x6752e702` | `protocolSeizeShareMantissa()` | Protocol cut of liquidation seizure. |
| `0x5fe3b567` | `comptroller()` | Returns the Unitroller address. |
| `0xf3fdb15a` | `interestRateModel()` | Per-market JumpRateModel. |
| `0x6f307dc3` | `underlying()` | Underlying ERC-20 (absent on the native-gas market). |
| `0x5c60da1b` | `implementation()` | **Read this for the mToken logic contract** — NOT the EIP-1967 slot (see §10). |
| `0x70a08231` / `0x18160ddd` / `0x313ce567` / `0x95d89b41` / `0x06fdde03` | `balanceOf`/`totalSupply`/`decimals`/`symbol`/`name` | mTokens: **8 decimals**, `name()="Moonwell USDC"`, `symbol()="mUSDC"` (prefix `m`). |
| `0x555bcc40` | `_setImplementation(address implementation_, bool allowResign, bytes becomeImplementationData)` | Admin-only mToken logic upgrade (delegator pattern). Not Unitroller-style. |
| `0xfca7820b` | `_setReserveFactor(uint256)` | Admin. Emits `NewReserveFactor`. |
| `0xf2b3abbd` | `_setInterestRateModel(address)` | Admin. Emits `NewMarketInterestRateModel`. |
| `0x83030846` | `_setProtocolSeizeShare(uint256)` | Admin. |
| `0x601a0bf1` | `_reduceReserves(uint256)` / `0x3e941010 _addReserves(uint256)` | Reserve management. |

### 2.2 Comptroller (behind Unitroller)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc2998238` | `enterMarkets(address[] mTokens)` | Use mTokens as collateral. Emits `MarketEntered`. |
| `0xede4edd0` | `exitMarket(address mToken)` | Emits `MarketExited`. |
| `0x5ec88c79` | `getAccountLiquidity(address)` | `(uint err, uint liquidity, uint shortfall)`. Shortfall>0 ⇒ liquidatable. |
| `0x4e79238f` | `getHypotheticalAccountLiquidity(address,address,uint256,uint256)` | What-if liquidity check. |
| `0xabfceffc` | `getAssetsIn(address)` | mTokens the account has entered. |
| `0x929fe9a1` | `checkMembership(address account, address mToken)` | |
| `0xb0772d0b` | `getAllMarkets()` | All listed mTokens (Base = 21, OP = 14 as of 2026-06 — the OP array retains the deprecated VELO market). Re-read live rather than hardcoding. |
| `0x8e8f294b` | `markets(address mToken)` | `(bool isListed, uint collateralFactorMantissa, ...)` |
| `0x7dc0d1d0` | `oracle()` | The ChainlinkOracle address. |
| `0xe8755446` | `closeFactorMantissa()` | Max fraction of debt repayable per liquidation. |
| `0x4ada90af` | `liquidationIncentiveMantissa()` | Liquidator bonus. |
| `0x4a584432` | `borrowCaps(address)` / `0x02c3bcbb supplyCaps(address)` | Per-market caps. |
| `0xacc2166a` | `rewardDistributor()` | Returns the MRD proxy. |
| `0xc488847b` | `liquidateCalculateSeizeTokens(address,address,uint256)` | |
| `0x4ef4c3e1` / `0xda3d454c` | `mintAllowed(...)` / `borrowAllowed(...)` | Policy hooks (called by mTokens). |
| `0xa76b3fda` | `_supportMarket(address)` | Admin. Emits `MarketListed`. |
| `0xe4028eee` | `_setCollateralFactor(address,uint256)` | Admin. Emits `NewCollateralFactor`. |
| `0x607ef6c1` / `0x51a485e4` | `_setMarketBorrowCaps(address[],uint256[])` / `_setMarketSupplyCaps(address[],uint256[])` | |
| `0x3bcf7ec1` / `0x18c882a5` | `_setMintPaused(address,bool)` / `_setBorrowPaused(address,bool)` | Emit `ActionPaused(address,string,bool)`. |
| `0x8ebf6364` / `0x2d70db78` | `_setTransferPaused(bool)` / `_setSeizePaused(bool)` | Emit `ActionPaused(string,bool)`. |
| `0x55ee1fe1` / `0x317b0b77` / `0x4fd42e17` | `_setPriceOracle` / `_setCloseFactor` / `_setLiquidationIncentive` | |
| `0x5c254d11` | `_setRewardDistributor(address)` | Emits `NewRewardDistributor`. |
| `0xb88a802f` | `claimReward()` | Proxies to MRD. |
| `0xd279c191` | `claimReward(address holder)` | |
| `0x3685ffe7` | `claimReward(address holder, address[] mTokens)` | |
| `0x114b9d19` | `claimReward(address[] holders, address[] mTokens, bool borrowers, bool suppliers)` | |
| `0xbb82aa5e` | `comptrollerImplementation()` | **Unitroller: read this for the live Comptroller logic** (storage slot 2). |
| `0xdcfbc0c7` | `pendingComptrollerImplementation()` | Storage slot 3. |

### 2.3 MultiRewardDistributor (MRD)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc9a06b45` | `getOutstandingRewardsForUser(address user)` | All-markets reward preview. |
| `0x07e8ce85` | `getOutstandingRewardsForUser(address mToken, address user)` | Single market. |
| `0x7e218f90` | `getAllMarketConfigs(address mToken)` | All emission configs for a market. |
| `0x8b62a51a` | `getConfigForMarket(address mToken, address emissionToken)` | |
| `0xe88d9c1b` | `getCurrentEmissionCap()` | |
| `0xea0f3dff` | `_addEmissionConfig(address mToken, address owner, address emissionToken, uint256 supplySpeed, uint256 borrowSpeed, uint256 endTime)` | Admin. Emits `NewConfigCreated`. |
| `0x28392380` | `_setEmissionCap(uint256)` | Admin. Emits `NewEmissionCap`. |
| `0x610393a0` / `0x7f7336ba` | `_updateSupplySpeed(...)` / `_updateBorrowSpeed(...)` | Emit `NewSupplyRewardSpeed`/`NewBorrowRewardSpeed`. |

> `claimReward` is **not** on the MRD — call it on the Comptroller (§2.2), which invokes MRD disburse functions.

### 2.4 ChainlinkOracle

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfc57d4df` | `getUnderlyingPrice(address mToken)` | Comptroller's pricing entry point. Returns price mantissa scaled to `36 − underlyingDecimals`. |
| `0x3b39a51c` | `getFeed(string symbol)` | Feed keyed by **underlying token symbol string**. |
| `0x0c607acf` | `setFeed(string symbol, address feed)` | Admin. Emits `FeedSet`. |
| `0xbd58fe56` | `getChainlinkPrice(address)` | |

### 2.5 TemporalGovernor

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x63c6c6a3` | `queueProposal(bytes VAA)` | Verify Wormhole VAA, queue. Emits `QueuedTransaction`. |
| `0x30faa259` | `executeProposal(bytes VAA)` | After `proposalDelay()`. Emits `ExecutedTransaction`. |
| `0x3f4b28f4` | `fastTrackProposalExecution(bytes VAA)` | Guardian bypass of delay. |
| `0xbe6a2f0c` | `permissionlessUnpause()` | |
| `0x4a354891` | `setTrustedSenders((uint16,address)[])` | Tuple = (wormholeChainId, sourceAddr). |
| `0x35a2017d` / `0x8ab9b2e1` | `isTrustedSender(uint16,address)` / `allTrustedSenders(uint16)` | |

### 2.6 Unitroller

| Selector | Signature |
|----------|-----------|
| `0xe992a041` | `_setPendingImplementation(address)` |
| `0xc1e80334` | `_acceptImplementation()` |
| `0xb71d1a0c` | `_setPendingAdmin(address)` |
| `0xe9c714f2` | `_acceptAdmin()` |

---

## 3. Addresses — Base mainnet (chain ID 8453)  *[flagship — largest deployment]*

All verified via `eth_getCode` (non-empty) on `https://base-rpc.publicnode.com`. Proxy wiring confirmed live (see §10). Launched ~2023-08 (MIP-B0).

### 3.1 Core lending system

| Role | Address | One-liner |
|------|---------|-----------|
| **UNITROLLER** (Comptroller proxy) | `0xfBb21d0380beE3312B33c4353c8936a0F13EF26C` | The risk engine. `comptrollerImplementation()`→ COMPTROLLER; `oracle()`→ CHAINLINK_ORACLE; `getAllMarkets()`=21. Point all market-policy monitors here. |
| COMPTROLLER (impl) | `0x73D8A3bF62aACa6690791E57EBaEE4e1d875d8Fe` | Comptroller logic behind the Unitroller. |
| **MTOKEN_IMPLEMENTATION** (MErc20Delegate) | `0x1FADFF493529C3Fcc7EE04F1f15D19816ddA45B7` | Shared logic for every ERC-20 mToken delegator. |
| MWETH_IMPLEMENTATION (MWETH logic) | `0x599D4a1538d686814eE11b331EACBBa166D7C41a` | Logic for the WETH/native market. |
| **MRD_PROXY** (MultiRewardDistributor) | `0xe9005b078701e2A0948D2EaC43010D35870Ad9d2` | All reward accounting. EIP-1967 proxy → MRD_IMPL. |
| MRD_IMPL | `0xdC649f4fa047a3C98e8705E85B8b1BafCbCFef0f` | MRD logic. |
| MRD_PROXY_ADMIN | `0x8D7d2230A2d195F023588eDd13dBAd56dd69770F` | EIP-1967 admin of MRD (and other transparent proxies). |
| **CHAINLINK_ORACLE** | `0xEC942bE8A8114bFD0396A5052c36027f2cA6a9d0` | Moonwell price oracle; symbol→Chainlink-feed mapping. |
| CHAINLINK_ORACLE_PROXY_ADMIN | `0x3fCA08493283E79cbD1E733Ca3Cb8eC8C6074deC` | Proxy admin for the oracle. |
| **TEMPORAL_GOVERNOR** | `0x8b621804a7637b781e2BbD58e256a591F2dF7d51` | Wormhole governor; **`admin` of the Unitroller + every mToken**. Also `EMISSIONS_ADMIN`. |
| WETH_ROUTER | `0x70778cfcFC475c7eA0f24cC625Baf6EaE475D0c9` | ETH↔mWETH supply/redeem helper. |
| WETH_UNWRAPPER | `0x1382cFf3CeE10D283DccA55A30496187759e4cAf` | Unwraps WETH→ETH on redeem. |
| SECURITY_COUNCIL | `0x446342AF4F3bCD374276891C6bb3411bf2F8779E` | Pause guardian multisig. |
| xWELL_PROXY (WELL token) | `0xA88594D404727625A9437C3f886C7643872296AE` | Canonical xWELL — **same address on every Moonwell chain**. |
| stkWELL (STK_GOVTOKEN_PROXY) | `0xe66E3A37C3274Ac24FE8590f7D84A2427194DC17` | Safety-module staked WELL. |

### 3.2 mToken markets (21) — `symbol` is `m`+underlying, **8 decimals**

| mToken | Address | Underlying | Underlying addr |
|--------|---------|-----------|-----------------|
| MOONWELL_USDC | `0xEdc817A28E8B93B03976FBd4a3dDBc9f7D176c22` | USDC (6d) | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| MOONWELL_USDBC | `0x703843C3379b52F9FF486c9f5892218d2a065cC8` | USDbC (6d, bridged) | `0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA` |
| MOONWELL_DAI | `0x73b06D8d18De422E269645eaCe15400DE7462417` | DAI | `0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb` |
| MOONWELL_USDS | `0xb6419c6C2e60c4025D6D06eE4F913ce89425a357` | USDS | `0x820C137fa70C8691f0e44Dc420a5e53c168921Dc` |
| MOONWELL_EURC | `0xb682c840B5F4FC58B20769E691A6fa1305A501a2` | EURC (6d) | `0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42` |
| MOONWELL_WETH | `0x628ff693426583D9a7FB391E54366292F509D457` | WETH | `0x4200000000000000000000000000000000000006` |
| MOONWELL_cbETH | `0x3bf93770f2d4a794c3d9EBEfBAeBAE2a8f09A5E5` | cbETH | `0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22` |
| MOONWELL_wstETH | `0x627Fe393Bc6EdDA28e99AE648fD6fF362514304b` | wstETH | `0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452` |
| MOONWELL_rETH | `0xCB1DaCd30638ae38F2B94eA64F066045B7D45f44` | rETH | `0xB6fe221Fe9EeF5aBa221c348bA20A1Bf5e73624c` |
| MOONWELL_weETH | `0xb8051464C8c92209C92F3a4CD9C73746C4c3CFb3` | weETH | `0x04C0599Ae5A44757c0af6F9eC3b93da8976c150A` |
| MOONWELL_wrsETH | `0xfC41B49d064Ac646015b459C522820DB9472F4B5` | wrsETH | `0xEDfa23602D0EC14714057867A78d01e94176BEA0` |
| MOONWELL_AERO | `0x73902f619CEB9B31FD8EFecf435CbDf89E369Ba6` | AERO | `0x940181a94A35A4569E4529A3CDfB74e38FD98631` |
| MOONWELL_WELL | `0xdC7810B47eAAb250De623F0eE07764afa5F71ED1` | WELL | `0xA88594D404727625A9437C3f886C7643872296AE` |
| MOONWELL_cbBTC | `0xF877ACaFA28c19b96727966690b2f44d35aD5976` | cbBTC (8d) | `0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf` |
| MOONWELL_LBTC | `0x10fF57877b79e9bd949B3815220eC87B9fc5D2ee` | LBTC | `0xecAc9C5F704e954931349Da37F60E39f515c11c1` |
| MOONWELL_TBTC | `0x9A858ebfF1bEb0D3495BB0e2897c1528eD84A218` | TBTC | `0x236aa50979D5f3De3Bd1Eeb40E81137F22ab794b` |
| MOONWELL_VIRTUAL | `0xdE8Df9d942D78edE3Ca06e60712582F79CFfFC64` | VIRTUAL | `0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b` |
| MOONWELL_VVV | `0xD64BCb70C613a6D1F4D7D57Ba64bb4a0767A9682` | VVV | `0xacfE6019Ed1A7Dc6f7B508C02d1b04ec88cC21bf` |
| MOONWELL_MORPHO | `0x6308204872BdB7432dF97b04B42443c714904F3E` | MORPHO | `0xBAa5CC21fd487B8Fcc2F632f3F4E8D37262a0842` |
| MOONWELL_MAMO | `0x2F90Bb22eB3979f5FfAd31EA6C3F0792ca66dA32` | MAMO | `0x7300B37DfdfAb110d83290A29DfB31B1740219fE` |
| MOONWELL_cbXRP | `0xb4fb8fed5b3AaA8434f0B19b1b623d977e07e86d` | cbXRP | `0xcB585250f852C6c6bf90434AB21A00f02833a4af` |

> No `MOONWELL_WBTC` on Base — BTC exposure is via cbBTC / LBTC / TBTC. mToken addresses cannot be derived (each is a separately-deployed MErc20Delegator, not a CREATE2 clone) — enumerate via `getAllMarkets()`.

### 3.3 Interest rate models (active JumpRateModels)

Per-market `JumpRateModel` contracts. ~70 additional `*_MIP_*`-suffixed historical IRM versions exist in the repo (superseded by governance re-parameterizations) — not monitoring-relevant; read each market's live model via `mToken.interestRateModel()`.

| Market | IRM address |
|--------|-------------|
| USDC | `0x54dC357F7461BcEEE5BdbA80996f5CB7d7512445` |
| USDBC | `0xF22c8255eA615b3Da6CA5CF5aeCc8956bfF07Aa8` |
| DAI | `0x32f3A6134590fc2d9440663d35a2F0a6265F04c4` |
| USDS | `0x310FBf531Ba386B0f4Cc207dcdE9f8BDBfdBdB52` |
| EURC | `0x7830f646E6cb7460eF1069E4Fec8CF5B10F7BBea` |
| LBTC | `0x01177F591C4D4fC89cDEE039f7E17d7412CE9A7b` |
| TBTC | `0x13820AA528Dc5Ce2dE39F9A4495272e9500452C2` |
| cbBTC | `0x0738483Add6ab8620B731aEc0121d1d3A70BD6EA` |
| MAMO | `0x6D8CB0C4C5caA9876939cB6e5EED8ca84d474c0c` |
| MORPHO | `0xfeA5a5927645C0DC5C1E740Ec1B24AD320c7e58f` |
| VIRTUAL | `0x048442d10E4c54655440f1C580bfcd27961b5bD8` |
| VVV | `0xCF1A3322977ef557899ad2BF3056d8411EdC87A1` |
| WELL | `0x2A62AC4f8BE9E07bB0686c070A811027452D4dA1` |
| weETH | `0x6ac79dF84FA8A704711a2fb8c3763e48Ed2c0Ed6` |
| wrsETH | `0x63f9f904CE2912853C2F7bb43dD1c1A6136F09b1` |
| cbXRP | `0xcB95579c706144f3150f7C3b1BD3F24A48d3463e` |

### 3.4 Governance / cross-chain (Base)

| Role | Address |
|------|---------|
| VOTE_COLLECTION_PROXY | `0xe0278B32c627FF6fFbbe7de6A18Ade145603e949` |
| WORMHOLE_CORE | `0xbebdb6C8ddC678FfA9f8748f85C815C556Dd8ac6` |
| WORMHOLE_BRIDGE_ADAPTER_PROXY | `0x734AbBCe07679C9A6B4Fe3bC16325e028fA6DbB7` |
| ECOSYSTEM_RESERVE_PROXY | `0x65A633E8E379F9358C389c75ff1D913a92ab95B8` |

---

## 4. Addresses — Optimism (chain ID 10)

All verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`. Launched 2024 ("Activate Moonwell on Optimism"). Same architecture as Base; **different addresses** (independent deployment).

### 4.1 Core lending system

| Role | Address | One-liner |
|------|---------|-----------|
| **UNITROLLER** | `0xCa889f40aae37FFf165BccF69aeF1E82b5C511B9` | `comptrollerImplementation()`→ COMPTROLLER; `oracle()`→ CHAINLINK_ORACLE. |
| COMPTROLLER (impl) | `0x8dFBb21dbD61af533092d54B293660CF77A30Ce2` | |
| **MTOKEN_IMPLEMENTATION** | `0xA9CE0A4DE55791c5792B50531b18Befc30B09dcC` | mToken logic. |
| MWETH_IMPLEMENTATION | `0x66Fb793e75053A07301c7c21A3cF77616123227b` | |
| **MRD_PROXY** | `0xF9524bfa18C19C3E605FbfE8DFd05C6e967574Aa` | EIP-1967 proxy → MRD_IMPL. |
| MRD_IMPL | `0xFf0731337F615aC5403cb243623283BC04cDe121` | |
| MRD_PROXY_ADMIN | `0x8568A675384d761f36eC269D695d6Ce4423cfaB1` | |
| **CHAINLINK_ORACLE** | `0x2f1490bD6aD10C9CE42a2829afa13EAc0b746dcf` | |
| **TEMPORAL_GOVERNOR** | `0x17C9ba3fDa7EC71CcfD75f978Ef31E21927aFF3d` | Admin of Unitroller + mTokens. |
| WETH_ROUTER | `0xc4Ab8C031717d7ecCCD653BE898e0f92410E11dC` | |
| WETH_UNWRAPPER | `0xa962F2974A846b30366251f4634384C1e42aeF16` | |
| xWELL_PROXY (WELL) | `0xA88594D404727625A9437C3f886C7643872296AE` | Same canonical xWELL. |
| stkWELL | `0xfB26A4947A38cb53e2D083c6490060CCCE7438c5` | |

### 4.2 mToken markets (13 active; `getAllMarkets()` returns 14 — it also retains the deprecated VELO market)

| mToken | Address | Underlying | Underlying addr |
|--------|---------|-----------|-----------------|
| MOONWELL_USDC | `0x8E08617b0d66359D73Aa11E11017834C29155525` | USDC (6d) | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |
| MOONWELL_USDT | `0xa3A53899EE8f9f6E963437C5B3f805FEc538BF84` | USDT (6d) | `0x94b008aA00579c1307B0EF2c499aD98a8ce58e58` |
| MOONWELL_USDT0 | `0xed37cD7872c6fe4020982d35104bE7919b8f8b33` | USDT0 | `0x01bFF41798a0BcF287b996046Ca68b395dbC1071` |
| MOONWELL_DAI | `0x3FE782C2Fe7668C2F1Eb313ACf3022a31feaD6B2` | DAI | `0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1` |
| MOONWELL_WETH | `0xb4104C02BBf4E9be85AAa41a62974E4e28D59A33` | WETH | `0x4200000000000000000000000000000000000006` |
| MOONWELL_OP | `0x9fc345a20541Bf8773988515c5950eD69aF01847` | OP | `0x4200000000000000000000000000000000000042` |
| MOONWELL_WBTC | `0x6e6CA598A06E609c913551B729a228B023f06fDB` | WBTC (8d) | `0x68f180fcCe6836688e9084f035309E29Bf0A2095` |
| MOONWELL_cbETH | `0x95C84F369bd0251ca903052600A3C96838D78bA1` | cbETH | `0xadDb6A0412DE1BA0F936DCaeb8Aaa24578dcF3B2` |
| MOONWELL_rETH | `0x4c2E35E3eC4A0C82849637BC04A4609Dbe53d321` | rETH | `0x9Bcef72be871e61ED4fBbc7630889beE758eb81D` |
| MOONWELL_weETH | `0xb8051464C8c92209C92F3a4CD9C73746C4c3CFb3` | weETH | `0x5A7fACB970D094B6C7FF1df0eA68D99E6e73CBFF` |
| MOONWELL_wrsETH | `0x181bA797ccF779D8aB339721ED6ee827E758668e` | wrsETH | `0x87eEE96D50Fb761AD85B1c982d28A042169d61b1` |
| MOONWELL_wstETH | `0xbb3b1aB66eFB43B10923b87460c0106643B83f9d` | wstETH | `0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb` |
| MOONWELL_VELO | `0x866b838b97Ee43F2c818B3cb5Cc77A0dc22003Fc` | VELO | `0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db` |

> `DEPRECATED_MOONWELL_VELO` = `0x21d851585840942B0eF9f20d842C00C5f3735eaF` (old VELO market; **still present in `getAllMarkets()`** — Compound's market array retains deprecated markets rather than removing them, so the on-chain count is 14 while only 13 are active). Distinguish the active VELO market (`0x866b838b97Ee43F2c818B3cb5Cc77A0dc22003Fc`) from this deprecated one by address.

### 4.3 Active IRMs (Optimism)

| Market | IRM | Market | IRM |
|--------|-----|--------|-----|
| USDC | `0xBD2FcfB778fef7a1650E19a6E0754E982F0fAae2` | USDT | `0xdAdA7DB2cC9a5D3d3C12509B71964E82d4AE76D6` |
| USDT0 | `0xeB7605508225517fE289c46406999F31b96c3B4A` | DAI | `0x04e6322D196E0E4cCBb2610dd8B8f2871E160bd7` |
| WETH | `0x2a55ba986a8c6EE17979f6233985414A865a280f` | OP | `0x69ff8B55d6f08e2266FEB10092AcE88217e0668e` |
| WBTC | `0xf5E4b63B8447879E8F44A988128ab1836F21f12A` | cbETH | `0x7c94e5bddFDDB4a22C0432873844224036dFb4c1` |
| rETH | `0x612e737586Ae0cCF4a55DF3FCAF19993C16Db9E9` | weETH | `0x6ac79dF84FA8A704711a2fb8c3763e48Ed2c0Ed6` |
| wrsETH | `0x9008f34b1abeA057B625917A97BC546D88404425` | wstETH | `0xEa952aCFa68ED588313134D81Ed9B19411E99B80` |
| VELO | `0x7b2FaBffa53F59203aE5db1dd8E0e9A4D50c744e` | | |

### 4.4 Governance / cross-chain (Optimism)

| Role | Address |
|------|---------|
| VOTE_COLLECTION_PROXY | `0x3C968481BE3ba1a99fed5f73dB2Ff51151037738` |
| WORMHOLE_CORE | `0xEe91C335eab126dF5fDB3797EA9d6aD93aeC9722` |
| WORMHOLE_BRIDGE_ADAPTER_PROXY | `0x734AbBCe07679C9A6B4Fe3bC16325e028fA6DbB7` |
| ECOSYSTEM_RESERVE_PROXY | `0x966450Ee0757846963F17f7978a8A906e078EF4b` |

---

## 5. Addresses — Ethereum mainnet (chain ID 1)  *[governance hub — NO LENDING]*

**There are no Moonwell lending markets on Ethereum.** `chains/1.json` contains no Unitroller / Comptroller / mTokens. Ethereum hosts only the WELL token and the cross-chain governance contracts (the destination of the in-progress MIP-X58 Moonbeam→Ethereum governance-origin migration — the `MULTICHAIN_GOVERNOR_V2_PROXY` is deployed and live; cutover not fully confirmed as of 2026-05). **Do not point Comptroller/mToken monitors at chain 1.**

| Role | Address | One-liner |
|------|---------|-----------|
| xWELL_PROXY (WELL token) | `0xA88594D404727625A9437C3f886C7643872296AE` | Canonical xWELL — same address as Base/OP/Moonbeam. |
| MULTICHAIN_GOVERNOR_V2_PROXY | `0x8769B70ac7c93AF0e75de0D69877709B66d75838` | Governance origin; publishes Wormhole VAAs to each chain's TemporalGovernor. |
| VOTING_POWER_AGGREGATOR | `0x908dF70C2EDEA165eE22fe63549af46944Ea4689` | Aggregates xWELL + stkWELL voting power across chains. |
| WORMHOLE_CORE | `0x98f3c9e6E3fACe36bAAd05FE09d375Ef1464288B` | Canonical Wormhole core (Ethereum). |
| WORMHOLE_BRIDGE_ADAPTER_PROXY | `0x734AbBCe07679C9A6B4Fe3bC16325e028fA6DbB7` | xWELL bridge adapter. |
| ECOSYSTEM_RESERVE_PROXY | `0xAbd65097F869f36f56Be9eC60DfB4A441a00c47C` | |

---

## 6. Chains with NO Moonwell deployment

**BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Polygon PoS (137): Moonwell is NOT deployed.** Triangulated three ways — (1) no `chains/<id>.json` in `moonwell-fi/moonwell-contracts-v2`; (2) not listed on `docs.moonwell.fi`; (3) no DeFiLlama TVL — and confirmed by `eth_getCode` returning empty (`0x`) for the Base Unitroller/Comptroller addresses on all four. Any "Moonwell" contract claimed on these chains is a different protocol or a fork. Do not author monitors for Moonwell on these chains.

---

## 7. Cross-chain summary

| Chain | ID | Lending? | Unitroller | Comptroller impl | ChainlinkOracle | TemporalGovernor | Markets |
|-------|----|---------|-----------|------------------|-----------------|------------------|---------|
| Base | 8453 | ✅ | `0xfBb21d03…F26C` | `0x73D8A3bF…d8Fe` | `0xEC942bE8…a9d0` | `0x8b621804…7d51` | 21 |
| Optimism | 10 | ✅ | `0xCa889f40…11B9` | `0x8dFBb21d…0Ce2` | `0x2f1490bD…6dcf` | `0x17C9ba3f…fF3d` | 14 (`getAllMarkets()`; 13 active + deprecated VELO) |
| Ethereum | 1 | ❌ (gov+token only) | — | — | — | — | 0 |
| BNB / Avalanche / Arbitrum / Polygon | 56/43114/42161/137 | ❌ (not deployed) | — | — | — | — | 0 |

Patterns to internalize:
1. **Per-chain addresses are all unique** (no cross-chain address reuse for lending contracts) — the ONLY shared address is `xWELL_PROXY = 0xA885…96AE` (WELL token) and the `WORMHOLE_BRIDGE_ADAPTER_PROXY = 0x734A…DbB7`. Always key on `(chainId, address)`.
2. **TemporalGovernor is the admin** of the Unitroller and every mToken on its chain — admin-action monitoring watches the TemporalGovernor's `ExecutedTransaction`.
3. **mToken count grows** — re-read `getAllMarkets()` per chain rather than hardcoding the market list.

---

## 8. Proxies (old + new)

Moonwell mixes **two** proxy families. Getting them wrong is the #1 integration error.

| Contract | Pattern | How to read the impl | Verified (Base) |
|----------|---------|----------------------|------------------|
| **Unitroller** (Comptroller) | **Compound Unitroller** — NOT EIP-1967. Impl in **storage slot 2** (`comptrollerImplementation`), pending in slot 3; `admin` slot 0, `pendingAdmin` slot 1. | `comptrollerImplementation()` (`0xbb82aa5e`) or `eth_getStorageAt(slot 2)`. **EIP-1967 slot is empty.** | slot0=`…8b621804…7d51` (TemporalGovernor=admin), slot2=`…73d8a3…d8fe`=Comptroller ✓; EIP-1967 slot = `0x0` ✓ |
| **mToken** (MErc20Delegator) | **Compound delegator** — NOT EIP-1967. `implementation` is a plain storage var; upgraded via `_setImplementation(address,bool,bytes)`. | `implementation()` (`0x5c60da1b`). | mUSDC `implementation()`=`0x1FADFF…45B7` ✓; slot3 packs `decimals=0x08`+admin; slot5=comptroller `0xfBb2…F26C` ✓ |
| **MultiRewardDistributor** | **EIP-1967 transparent proxy** (OpenZeppelin). | EIP-1967 impl slot `0x360894…bbc`. | MRD_PROXY impl slot=`0xdC649f…ef0f`=MRD_IMPL ✓; admin slot `0xb53127…6103`=`0x8D7d22…770F`=MRD_PROXY_ADMIN ✓ |
| **ChainlinkOracle** | **EIP-1967 transparent proxy** (has `CHAINLINK_ORACLE_PROXY_ADMIN`). | EIP-1967 impl slot. | proxy admin present on Base. |
| **xWELL / VoteCollection / WormholeBridgeAdapter / EcosystemReserve** | **EIP-1967 transparent proxies** (multiple historical impl versions: `_IMPL_V2/V5/V6`). | EIP-1967 impl slot. | — |

```
Unitroller storage layout (Compound):
  slot 0 = admin            (= TemporalGovernor)
  slot 1 = pendingAdmin
  slot 2 = comptrollerImplementation   ← live Comptroller logic
  slot 3 = pendingComptrollerImplementation
EIP-1967 impl slot = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc  (empty on Unitroller & mTokens)
EIP-1967 admin slot = 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103  (used by MRD/oracle/xWELL)
```

---

## 9. Detection invariants & gotchas

1. **Timestamp, not block.** `accrualBlockTimestamp()` is a **unix timestamp**; rate accessors are `supplyRatePerTimestamp()`/`borrowRatePerTimestamp()` (**per-second**). APR = `ratePerTimestamp × 31_536_000 / 1e18`. Calling `*PerBlock`/`accrualBlockNumber` reverts.
2. **`AccrueInterest` is 4-arg** (`0x4dec04e7…`, 128-byte data). Stock-Compound 3-arg decoders mis-parse it. Verified live on Base mUSDC.
3. **`Mint` topic0 collides with Uniswap V2** (`0x4c209b5f…`) — always filter by emitter (an mToken). Same for ERC-20 `Transfer`/`Approval`.
4. **Rewards are in the MRD, not the Comptroller.** Watch `DisbursedSupplierRewards`/`DisbursedBorrowerRewards` + `NewSupplyRewardSpeed`/`NewBorrowRewardSpeed` on `MRD_PROXY` — not the Comptroller. Multiple emission tokens per market (WELL + the underlying's native incentive, e.g. OP, AERO).
5. **mTokens are 8 decimals; underlying decimals vary** (USDC 6, cbBTC/WBTC 8, most others 18). `exchangeRateStored` is scaled by `1e(18 + underlyingDec − 8)`. `getUnderlyingPrice` returns a mantissa scaled to `36 − underlyingDec`.
6. **`admin` of everything is the TemporalGovernor.** A parameter change (collateral factor, cap, IRM, pause) is an `ExecutedTransaction` on the TemporalGovernor that fans out to Comptroller/mToken calls — correlate by tx hash.
7. **Pausing uses two `ActionPaused` overloads only.** Per-market (Mint/Borrow) = `ActionPaused(address,string,bool)` (`0x71aec636…`); global (Transfer/Seize) = `ActionPaused(string,bool)` (`0xef159d9a…`).
8. **Caps emit indexed-mToken events** (`NewBorrowCap`/`NewSupplyCap`, mToken is `indexed`) — filter on topic1 for a specific market.
9. **Markets are enumerated, not derived.** Each mToken is a separately-deployed delegator (no CREATE2 salt). Read `getAllMarkets()`; don't hardcode.
10. **Liquidations:** `LiquidateBorrow` on the borrowed mToken carries `mTokenCollateral` + `seizeTokens`; the seized market emits a `Transfer` of mToken shares to the liquidator (plus a protocol-cut transfer per `protocolSeizeShareMantissa`).
11. **Ethereum is a trap chain.** It has WELL + governance but **zero lending** — never aim Comptroller/mToken monitors at chain 1.
12. **Native-gas market** uses `MWETH_IMPLEMENTATION` and has no `underlying()`; supply/redeem ETH via `WETH_ROUTER`.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- MToken
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
TOPIC_ERC20_APPROVAL         = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_FAILURE                = '\x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0'
-- Comptroller
TOPIC_MARKET_LISTED          = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_MARKET_ENTERED         = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'
TOPIC_MARKET_EXITED          = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_NEW_CLOSE_FACTOR       = '\x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9'
TOPIC_NEW_COLLATERAL_FACTOR  = '\x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5'
TOPIC_NEW_LIQ_INCENTIVE      = '\xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316'
TOPIC_NEW_PRICE_ORACLE       = '\xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22'
TOPIC_NEW_BORROW_CAP         = '\x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6'
TOPIC_NEW_SUPPLY_CAP         = '\x9e0ad9cee10bdf36b7fbd38910c0bdff0f275ace679b45b922381c2723d676f8'
TOPIC_NEW_REWARD_DISTRIBUTOR = '\x8ddca872a7a62d68235cff1a03badc845dc3007cfaa6145379f7bf3452ecb9b9'
TOPIC_NEW_PAUSE_GUARDIAN     = '\x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e'
TOPIC_ACTION_PAUSED_GLOBAL   = '\xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0'  -- (string,bool)
TOPIC_ACTION_PAUSED_MARKET   = '\x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0'  -- (address,string,bool)
-- MultiRewardDistributor
TOPIC_MRD_NEW_CONFIG         = '\xa76959d76a349a0b8fd3120607e3aea6af58897ae6531bfe60a0267c4ea0c272'
TOPIC_MRD_NEW_SUPPLY_SPEED   = '\xc4d50731808aa5d941c471c0b29364fecd810aa0565344f6cdcab2c873422baf'
TOPIC_MRD_NEW_BORROW_SPEED   = '\x8fc43850ed5c7aaa0ce83829a1a40202c3fcf8257788d69881611dff1a0b32e9'
TOPIC_MRD_DISBURSE_SUPPLIER  = '\x51761e1f6548bc99f2a61f299986e1b08a489f06622f689a413e02d7654a4766'
TOPIC_MRD_DISBURSE_BORROWER  = '\x48a32d6daeb4317b45f49c3a1c0b1bd7d53a175d1f46c425138e328900cdccb4'
TOPIC_MRD_NEW_EMISSION_CAP   = '\x8d2ad4bb95e94ce8d50ed07769a97467ba4db3f80fc0badf6c81d0907a0b410a'
-- ChainlinkOracle
TOPIC_PRICE_POSTED           = '\xdd71a1d19fcba687442a1d5c58578f1e409af71a79d10fd95a4d66efd8fa9ae7'
TOPIC_FEED_SET               = '\xd9e7d1778ca05570ced72c9aeb12a41fcc76f7f57ea25853dea228f8836d0022'
-- TemporalGovernor
TOPIC_TG_QUEUED              = '\xc486294e67e6b98e19d854bb8a606f314e248d45e842a98b09a51be7b13ce2a5'
TOPIC_TG_EXECUTED            = '\xaf022f6b53b11c364e2dfc0aea08eb9416c94f2661451ea82ead8831385617a6'
TOPIC_TG_TRUSTED_SENDER      = '\xad5ad009fb0380817906297d4db849c9a30b93e0d3761c005ef8c487d9239224'
-- Unitroller
TOPIC_NEW_IMPLEMENTATION     = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'

-- ===== Selectors =====
SEL_MINT                     = '\xa0712d68'   -- mint(uint256)
SEL_REDEEM                   = '\xdb006a75'
SEL_REDEEM_UNDERLYING        = '\x852a12e3'
SEL_BORROW                   = '\xc5ebeaec'
SEL_REPAY_BORROW             = '\x0e752702'
SEL_REPAY_BORROW_BEHALF      = '\x2608f818'
SEL_LIQUIDATE_BORROW         = '\xf5e3c462'
SEL_EXCHANGE_RATE_STORED     = '\x182df0f5'
SEL_SUPPLY_RATE_PER_TS       = '\xd3bd2c72'   -- supplyRatePerTimestamp()
SEL_BORROW_RATE_PER_TS       = '\xcd91801c'   -- borrowRatePerTimestamp()
SEL_ACCRUAL_BLOCK_TIMESTAMP  = '\xcfa99201'
SEL_GET_CASH                 = '\x3b1d21a2'
SEL_UNDERLYING               = '\x6f307dc3'
SEL_MTOKEN_IMPLEMENTATION    = '\x5c60da1b'   -- implementation()  (mToken delegator)
SEL_COMPTROLLER_IMPL         = '\xbb82aa5e'   -- comptrollerImplementation()  (Unitroller)
SEL_GET_ALL_MARKETS          = '\xb0772d0b'
SEL_GET_ACCOUNT_LIQUIDITY    = '\x5ec88c79'
SEL_ENTER_MARKETS            = '\xc2998238'
SEL_EXIT_MARKET              = '\xede4edd0'
SEL_ORACLE                   = '\x7dc0d1d0'
SEL_GET_UNDERLYING_PRICE     = '\xfc57d4df'
SEL_CLAIM_REWARD             = '\xb88a802f'   -- claimReward()
SEL_QUEUE_PROPOSAL           = '\x63c6c6a3'
SEL_EXECUTE_PROPOSAL         = '\x30faa259'

-- ===== Base (chain 8453) =====
BASE_UNITROLLER              = '\xfbb21d0380bee3312b33c4353c8936a0f13ef26c'
BASE_COMPTROLLER_IMPL        = '\x73d8a3bf62aaca6690791e57ebaee4e1d875d8fe'
BASE_MTOKEN_IMPL             = '\x1fadff493529c3fcc7ee04f1f15d19816dda45b7'
BASE_MWETH_IMPL              = '\x599d4a1538d686814ee11b331eacbba166d7c41a'
BASE_MRD_PROXY               = '\xe9005b078701e2a0948d2eac43010d35870ad9d2'
BASE_MRD_IMPL                = '\xdc649f4fa047a3c98e8705e85b8b1bafcbcfef0f'
BASE_CHAINLINK_ORACLE        = '\xec942be8a8114bfd0396a5052c36027f2ca6a9d0'
BASE_TEMPORAL_GOVERNOR       = '\x8b621804a7637b781e2bbd58e256a591f2df7d51'
BASE_WETH_ROUTER             = '\x70778cfcfc475c7ea0f24cc625baf6eae475d0c9'
BASE_M_USDC                  = '\xedc817a28e8b93b03976fbd4a3ddbc9f7d176c22'
BASE_M_WETH                  = '\x628ff693426583d9a7fb391e54366292f509d457'
BASE_M_cbBTC                 = '\xf877acafa28c19b96727966690b2f44d35ad5976'
BASE_M_AERO                  = '\x73902f619ceb9b31fd8efecf435cbdf89e369ba6'
BASE_M_WELL                  = '\xdc7810b47eaab250de623f0ee07764afa5f71ed1'

-- ===== Optimism (chain 10) =====
OP_UNITROLLER                = '\xca889f40aae37fff165bccf69aef1e82b5c511b9'
OP_COMPTROLLER_IMPL          = '\x8dfbb21dbd61af533092d54b293660cf77a30ce2'
OP_MTOKEN_IMPL               = '\xa9ce0a4de55791c5792b50531b18befc30b09dcc'
OP_MWETH_IMPL                = '\x66fb793e75053a07301c7c21a3cf77616123227b'
OP_MRD_PROXY                 = '\xf9524bfa18c19c3e605fbfe8dfd05c6e967574aa'
OP_MRD_IMPL                  = '\xff0731337f615ac5403cb243623283bc04cde121'
OP_CHAINLINK_ORACLE          = '\x2f1490bd6ad10c9ce42a2829afa13eac0b746dcf'
OP_TEMPORAL_GOVERNOR         = '\x17c9ba3fda7ec71ccfd75f978ef31e21927aff3d'
OP_WETH_ROUTER               = '\xc4ab8c031717d7ecccd653be898e0f92410e11dc'
OP_M_USDC                    = '\x8e08617b0d66359d73aa11e11017834c29155525'
OP_M_WETH                    = '\xb4104c02bbf4e9be85aaa41a62974e4e28d59a33'
OP_M_OP                      = '\x9fc345a20541bf8773988515c5950ed69af01847'
OP_M_VELO                    = '\x866b838b97ee43f2c818b3cb5cc77a0dc22003fc'

-- ===== Ethereum (chain 1) — GOVERNANCE/TOKEN ONLY, NO LENDING =====
ETH_WELL_xWELL_PROXY         = '\xa88594d404727625a9437c3f886c7643872296ae'  -- same addr on Base/OP/Moonbeam
ETH_MULTICHAIN_GOVERNOR      = '\x8769b70ac7c93af0e75de0d69877709b66d75838'
ETH_VOTING_POWER_AGGREGATOR  = '\x908df70c2edea165ee22fe63549af46944ea4689'

-- EIP-1967 slots
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'  -- MRD/oracle/xWELL (NOT Unitroller/mTokens)
EIP1967_ADMIN_SLOT           = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
```

---

## 11. Appendix — original deployments (Moonbeam 1284 "Artemis", Moonriver 1285 "Apollo")

Outside the 7 requested chains, but the protocol's origin and still live. Same Compound-fork mToken core, but **different governance** (native Moonbeam/Moonriver governors, not the Wormhole/TemporalGovernor pattern) and **API3 price feeds** alongside Chainlink on Moonbeam.

**Moonriver (1285, "Apollo")** — first-ever deployment (~2022-02): `UNITROLLER 0x0b7a0EAA884849c6Af7a129e899536dDDcA4905E`, `MNATIVE (mMOVR) 0x6a1A771C7826596652daDC9145fEAaE62b1cd07f`, `APOLLO_GOVERNOR 0x2BE2e230e89c59c8E20E633C524AD2De246e7370`, `GOVTOKEN (MFAM) 0xBb8d88bcD9749636BC4D2bE22aaC4Bb3B01A58F1`. Markets enumerated on-chain via `getAllMarkets()`. **Being wound down** — markets deprecated via MIP-R35 ahead of Chainlink-feed deprecation (Jan 2026), and a governance attack hit Moonriver in March 2026; low-value to monitor going forward.

**Moonbeam (1284, "Artemis")** — `UNITROLLER 0x8E00D5e02E65A19337Cdba98bbA9F84d4186a180`, `MNATIVE (mGLMR) 0x091608f4e4a15335145be0A279483C0f8E4c7955`, `CHAINLINK_ORACLE 0xED301cd3EB27217BDB05C4E9B820a8A3c8B665f9`, `ARTEMIS_GOVERNOR 0xfc4DFB17101A12C5CEc5eeDd8E92B5b16557666d`, `MOONBEAM_TIMELOCK 0x3a9249d70dCb4A4E9ef4f3AF99a3A130452ec19B`. mTokens are Wormhole-wrapped/XC-20 assets: mxcDOT `0xD22Da948c0aB3A27f5570b604f3ADef5F68211C3`, mxcUSDC `0x22b1a40e3178fe7C7109eFCc247C5bB2B34ABe32`, mxcUSDT `0x42A96C0681B74838eC525AdbD13c37f66388f289`, mUSDCwh `0x744b1756e7651c6D57f5311767EAFE5E931D615b`, mFRAX `0x1C55649f73CDA2f72CEf3DD6C5CA3d49EFcF484C`, mWBTC `0xaaa20c5a584a9fECdFEDD71E46DA7858B774A9ce`, mETHwh `0xb6c94b3a378537300387b57ab1cc0d2083f9aeac`. The MultichainGovernor V1 originated here (`0x9A8464C4C11CeA17e191653Deb7CdC1bE30F1Af4`) before MIP-X58 moved the origin to Ethereum.

---

## 12. Verification & sources

- **topic0 / selectors:** all computed locally as `keccak256(canonical sig)` / `[0:4]` (pycryptodome). Spot-matched to known Compound selectors (`mint`=`0xa0712d68`, `borrow`=`0xc5ebeaec`, `getUnderlyingPrice`=`0xfc57d4df`, `enterMarkets`=`0xc2998238`) and ERC-20 (`Transfer`=`0xddf252ad…`). `AccrueInterest` 4-arg topic confirmed against **218 live Base mUSDC logs** (data = 128 B = 4×uint256).
- **Addresses:** ground truth = `moonwell-fi/moonwell-contracts-v2` `chains/<chainId>.json` (one file per chain; mainnet files = exactly 1, 10, 1284, 1285, 8453). Corroborated by `docs.moonwell.fi` and DeFiLlama. Every Base/OP address `eth_getCode`-verified non-empty.
- **Proxy wiring (live):** Base Unitroller `comptrollerImplementation()`→`0x73D8…d8Fe`, `oracle()`→`0xEC94…a9d0`; mUSDC `implementation()`→`0x1FAD…45B7`, `comptroller()`→Unitroller, `underlying()`→USDC, `symbol()`→"mUSDC"; storage slots read directly (Unitroller slot0=admin=TemporalGovernor, slot2=impl; EIP-1967 slot empty). MRD_PROXY EIP-1967 impl/admin slots match MRD_IMPL/MRD_PROXY_ADMIN. OP Unitroller/oracle/mUSDC wiring all match; `supplyRatePerTimestamp()`/`accrualBlockTimestamp()` return live values (timestamp-based fork confirmed).
- **Non-deployment:** Base Unitroller/Comptroller addresses return empty `eth_getCode` on BNB, Avalanche, Arbitrum, Polygon.

Authoritative sources:
- [`moonwell-fi/moonwell-contracts-v2`](https://github.com/moonwell-fi/moonwell-contracts-v2) — `src/` (MToken, Comptroller, rewards/MultiRewardDistributor, oracles/ChainlinkOracle, governance/TemporalGovernor) + `chains/<id>.json` address registry
- [docs.moonwell.fi](https://docs.moonwell.fi) — deployed-contract pages (Base, Optimism, Moonbeam, Moonriver only)
- [Compound V2](https://github.com/compound-finance/compound-protocol) — fork ancestor (cToken/Comptroller/Unitroller)
- RPCs: publicnode (`base-rpc`, `optimism-rpc`, `bsc-rpc`, `avalanche-c-chain-rpc`, `arbitrum-one-rpc`, `polygon-bor-rpc`, `ethereum-rpc`)
