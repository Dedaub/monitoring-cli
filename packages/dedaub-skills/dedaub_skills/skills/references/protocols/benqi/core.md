# BENQI — Topics, Selectors, Addresses (Avalanche C-Chain only)

**Status:** verified against live Avalanche C-Chain (43114) RPC and the canonical `Benqi-fi/BENQI-Smart-Contracts` repo (+ `Cyfrin/2025-01-benqi` for Ignite) on 2026-06-08. Every topic0/selector recomputed locally as `keccak256(canonical sig)`; every address `eth_getCode`-checked; proxy wiring read live from storage slots + getters.
**Scope:** BENQI's two on-chain product lines, both deployed **only on Avalanche C-Chain (43114)**: (1) **BENQI Lending Market** — a Compound V2 fork (`qiToken` markets behind a `Unitroller`/`Comptroller`), and (2) **BENQI Liquid Staking** — `sAVAX` (StakedAvax, an EIP-1967 upgradeable ERC-20) + the **Ignite** validator-staking contract. Topics and selectors are chain-agnostic (keccak of the signature); addresses are network-specific. **BENQI lending + staking are NOT deployed on Ethereum, Base, BNB, Arbitrum, Optimism, or Polygon** — see §6. (The QI *token* alone exists as a bridged representation on BNB — a decoy; §6.)

BENQI is one continuously-upgraded Avalanche deployment (not version-bumped), so this is a single `core.md`. Three architecture facts a monitoring engineer must internalize before indexing:

1. **It is a Compound V2 fork with timestamp-based accrual** (like Moonwell, unlike stock per-block Compound). `AccrueInterest` is the **4-arg** form (`0x4dec04e7…`, 128-byte data — verified on 829 live qiUSDCn logs). `accrualBlockNumber()` / `supplyRatePerBlock()` **revert**; the live accessors are `accrualBlockTimestamp()` (a unix timestamp) and `supplyRatePerTimestamp()` / `borrowRatePerTimestamp()` (per-second mantissas). The Comptroller exposes `getBlockTimestamp()`.
2. **Two distinct proxy families.** The **Unitroller** (Comptroller) and every **qiErc20Delegator** market use the **Compound delegator pattern — NOT EIP-1967** (read `comptrollerImplementation()` / `implementation()`; their EIP-1967 slot is empty). **`qiAVAX` is a monolithic `QiAvax` (CEther-style) contract — NOT a delegator** (no `implementation()`, no `underlying()`). By contrast **sAVAX, Ignite, and veQI are EIP-1967 transparent proxies** (impl/admin slots populated). The **PriceOracle (`BenqiChainlinkOracle`) and the QI token are plain non-upgradeable contracts** (empty EIP-1967 slots).
3. **Rewards are dual-token and live on the Comptroller itself** (unlike Moonwell's separate MRD). Reward accounting is keyed by a `uint8 rewardType`: **`rewardQi = 0`, `rewardAvax = 1`**. Watch `DistributedSupplierReward` / `DistributedBorrowerReward` (both carry `tokenType` as topic1) and `SupplyRewardSpeedUpdated` / `BorrowRewardSpeedUpdated` on the Comptroller. There are **no** COMP-style `DistributedSupplierComp` events and **no** MRD contract.

---

## 0. Contract families & versions

| Family | Contracts | Proxy pattern |
|--------|-----------|---------------|
| Risk engine | `Unitroller` (proxy) + `Comptroller` (logic) | Compound delegator (NOT EIP-1967) |
| ERC-20 markets | 14× `qiErc20Delegator` (proxy) → `QiErc20Delegate` (logic) | Compound delegator (NOT EIP-1967) |
| Native market | `qiAVAX` = monolithic `QiAvax` (CEther) | none (immutable, no delegator) |
| Pricing | `BenqiChainlinkOracle` | non-upgradeable |
| Token | `Qi` (QI governance/reward ERC-20) | non-upgradeable |
| Liquid staking | `sAVAX` (`StakedAvax`) | EIP-1967 transparent proxy |
| Validator staking | `Ignite` | EIP-1967 transparent proxy |
| Vote-escrow | `veQI` (`VeQi`) | EIP-1967 transparent proxy |

15 entries are returned by `Comptroller.getAllMarkets()` (qiAVAX + 14 qiErc20). Markets are separately-deployed delegators (no CREATE2 salt) — enumerate via `getAllMarkets()`, don't hardcode.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 qiToken / qiErc20 / qiAVAX (per-market — the workhorse events)

Identical to stock Compound V2 (same signatures, same topic0s). `qiAVAX` (CEther) emits the same set minus nothing.

| topic0 | Event |
|--------|-------|
| `0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04` | `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` — **4-arg, 128-byte data** |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address minter, uint256 mintAmount, uint256 mintTokens)` |
| `0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929` | `Redeem(address redeemer, uint256 redeemAmount, uint256 redeemTokens)` |
| `0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80` | `Borrow(address borrower, uint256 borrowAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1` | `RepayBorrow(address payer, address borrower, uint256 repayAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address liquidator, address borrower, uint256 repayAmount, address qiTokenCollateral, uint256 seizeTokens)` |
| `0xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5` | `ReservesAdded(address benefactor, uint256 addAmount, uint256 newTotalReserves)` |
| `0x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e` | `ReservesReduced(address admin, uint256 reduceAmount, uint256 newTotalReserves)` |
| `0xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460` | `NewReserveFactor(uint256 oldReserveFactorMantissa, uint256 newReserveFactorMantissa)` |
| `0xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926` | `NewMarketInterestRateModel(address oldIRM, address newIRM)` |
| `0x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d` | `NewComptroller(address oldComptroller, address newComptroller)` |
| `0xf5815f353a60e815cce7553e4f60c533a59d26b1b5504ea4b6db8d60da3e4da2` | `NewProtocolSeizeShare(uint256 oldShare, uint256 newShare)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` — qiToken shares |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` — soft-fail legacy path |

> **`Mint` topic0 collides with Uniswap V2's `Mint`** (same `Mint(address,uint256,uint256)`). **`Redeem` topic0 collides with the qiToken `Redeem` vs nothing here, but the sAVAX `Redeem` is a *different* 4-arg event (§1.4)** — disambiguate by emitter + arity. `Transfer`/`Approval` are universal ERC-20. Always filter by emitter address (a qiToken in `getAllMarkets()`).

### 1.2 Comptroller (one, behind the Unitroller — risk + rewards)

| topic0 | Event |
|--------|-------|
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address qiToken)` |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address qiToken, address account)` |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address qiToken, address account)` |
| `0x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9` | `NewCloseFactor(uint256 oldCloseFactorMantissa, uint256 newCloseFactorMantissa)` |
| `0x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5` | `NewCollateralFactor(address qiToken, uint256 oldCFMantissa, uint256 newCFMantissa)` |
| `0xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316` | `NewLiquidationIncentive(uint256 oldIncentiveMantissa, uint256 newIncentiveMantissa)` |
| `0xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22` | `NewPriceOracle(address oldOracle, address newOracle)` |
| `0x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6` | `NewBorrowCap(address indexed qiToken, uint256 newBorrowCap)` |
| `0xeda98690e518e9a05f8ec6837663e188211b2da8f4906648b323f2c1d4434e29` | `NewBorrowCapGuardian(address oldBorrowCapGuardian, address newBorrowCapGuardian)` |
| `0x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e` | `NewPauseGuardian(address oldPauseGuardian, address newPauseGuardian)` |
| `0xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0` | `ActionPaused(string action, bool pauseState)` — global (Transfer/Seize) |
| `0x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0` | `ActionPaused(address qiToken, string action, bool pauseState)` — per-market (Mint/Borrow) |
| `0xaccd035d02c456be35306aecd5a5fe62320713dde09ccd68b0a5e8ed93039999` | `DistributedSupplierReward(uint8 indexed tokenType, address indexed qiToken, address indexed supplier, uint256 qiDelta, uint256 supplyIndex)` |
| `0xa1b6a046664a0ecf068059f26de56878f8d0e799907ca2e42d9148ccbdc717a7` | `DistributedBorrowerReward(uint8 indexed tokenType, address indexed qiToken, address indexed borrower, uint256 qiDelta, uint256 borrowIndex)` |
| `0x2577edc53863f2e6d759b5da2c36549292f23909793d20feb1886bc21b17782f` | `SupplyRewardSpeedUpdated(uint8 rewardToken, address indexed qiToken, uint256 newSupplyRewardSpeed)` |
| `0xee48fe28e41d25c72d48e0c4580dbeac6fb4ef83cd3401ced307912114e2e5eb` | `BorrowRewardSpeedUpdated(uint8 rewardToken, address indexed qiToken, uint256 newBorrowRewardSpeed)` |
| `0xa94c5c08a0ebc2f092acf456a0606b4580b03d985a0f30c433bc16bb282c4a0f` | `ContributorQiSpeedUpdated(address indexed contributor, uint256 newSpeed)` |
| `0x23b40999b12039b28906192443f166517e9b2c60ff1fd6ec74637416e1204417` | `QiGranted(address recipient, uint256 amount)` |

> Reward events carry `tokenType` (0 = QI, 1 = AVAX) as **topic1** on the `Distributed*` events (indexed); `qiToken` is topic2, holder is topic3. There is **no** separate MultiRewardDistributor — all reward logs are emitted by the Comptroller. The reward-speed events are named **`SupplyRewardSpeedUpdated` / `BorrowRewardSpeedUpdated`** (NOT Moonwell's `NewSupply/BorrowRewardSpeed`).

### 1.3 Unitroller (Comptroller proxy — admin/upgrade events)

| topic0 | Event |
|--------|-------|
| `0xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815` | `NewPendingImplementation(address oldPendingImplementation, address newPendingImplementation)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |

### 1.4 sAVAX / StakedAvax (liquid staking)

| topic0 | Event |
|--------|-------|
| `0xbb0070894135d02edfa550b04d7e5e141aa8090b46e57597ad45bfedd6554498` | `Submitted(address indexed user, uint256 avaxAmount, uint256 shareAmount)` — stake AVAX → mint sAVAX |
| `0xd843ce9ef55b27026be6c5e44e9f58097e0ebfa0d9d2d5823cb8ffa779585170` | `UnlockRequested(address indexed user, uint256 shareAmount)` — start unstake cooldown |
| `0x7e4a9502fd577f76f1dc8c9c8f63196816f7c1bd73c6db99f888e8d7bb2f8998` | `UnlockCancelled(address indexed user, uint256 unlockRequestedAt, uint256 shareAmount)` |
| `0xbd5034ffbd47e4e72a94baa2cdb74c6fad73cb3bcdc13036b72ec8306f5a7646` | `Redeem(address indexed user, uint256 unlockRequestedAt, uint256 shareAmount, uint256 avaxAmount)` — **4-arg; collides in NAME with qiToken Redeem (3-arg)** |
| `0xeaca243f6502ade1b9ea0909306c290366d6ea6778ca407ca4415c4a0f45e353` | `RedeemOverdueShares(address indexed user, uint256 shareAmount)` |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | `Withdraw(address indexed user, uint256 amount)` |
| `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | `Deposit(address indexed user, uint256 amount)` |
| `0x8fbf6a230d02fb8f41af8c1ca90b126472e11286c47d7ed86bb2e1fc51a283d8` | `AccrueRewards(uint256 value)` — **fire-rarely; updates the AVAX-per-share exchange rate** |
| `0x98eaabfe135a9c40c420208962bf81e7926b4d6df3e23502164c0554b7b35224` | `CooldownPeriodUpdated(uint256 oldCooldownPeriod, uint256 newCooldownPeriod)` |
| `0x13cca15637be33d4651625caf09528168b20c132463c69ab5c0ff48b3e639117` | `RedeemPeriodUpdated(uint256 oldRedeemPeriod, uint256 newRedeemPeriod)` |
| `0xc016457d0a92973d26bab98d68d6f20133e355c467d05e5206c88c25d3b739d0` | `TotalPooledAvaxCapUpdated(uint256 oldCap, uint256 newCap)` |
| `0x35365f539a67058ad0735a24a50fe45b0ee05207919e9f4a2f60d855f55e0c0e` | `MintingPaused(address user)` |
| `0x8a53acd29b3c02ba82b89c57b23196b792ccb00a28515221f71bd92eafbc2dc3` | `MintingResumed(address user)` |

> sAVAX is also a full ERC-20 — it emits standard `Transfer`/`Approval` (§1.1 topic0s). `Deposit(address,uint256)` topic0 `0xe1fffcc4…` **collides with WETH/WAVAX `Deposit`** — filter by emitter (`0x2b2C…A4bE`).

### 1.5 Ignite (validator staking)

| topic0 | Event |
|--------|-------|
| `0x911545ab01a7553b2c4eb100eb4054703d821e76fc5d0504a07b8246aa3b1232` | `NewRegistration(address registerer, string nodeId, bytes blsProofOfPossession, uint256 validationDuration, bool feePaid, uint256 avaxAmount, address token, uint256 tokenAmount)` |
| `0x04393636f796e0824c4807e9d1a98080042d261b6d4feea240a3d698ee713b52` | `RegistrationDeleted(string nodeId)` |
| `0xee444713008e3c266c8fb74c287dd853d5eb23d60c7e77730b0ed536556efd9a` | `Redeem(string nodeId, uint256 avaxAmount, address token, uint256 tokenAmount)` — **string-keyed; NOT the qiToken/sAVAX Redeem** |
| `0x834288ca549398403511a8b546b7e4885ac51b98630c0ffa3a07858dc5d9e40d` | `RegistrationExpired(string nodeId)` |
| `0xeb8d450bff74ef3c1d9319f07855afedfdfa4dce6a223c1c1920a3ac1088d3b4` | `ValidatorSlashed(string nodeId, uint256 qiAmount, uint256 avaxAmount)` |
| `0xc7b0487e0a21287b5a35f7ddf5ed5d8e9d30338d3ad76e60c0986c52addace48` | `ValidatorRewarded(string nodeId, uint256 amount)` |
| `0x5b6b431d4476a211bb7d41c20d1aab9ae2321deee0d20be3d9fc9b1093fa6e3d` | `Withdraw(uint256 amount)` — admin protocol-revenue withdrawal (NOT the sAVAX `Withdraw(address,uint256)`) |
| `0xeb1cee51f4786b91756ab6e79cde8b4ae39e831e78f9ef5d813b9e40d37883b7` | `QiSlashPercentageChanged(uint256 oldPercentage, uint256 newPercentage)` |
| `0x70a47d9b6bc76b08da6f8f076f24e0cb3e9c1bfb280f89f72d5e6fe1ffbff577` | `AvaxSlashPercentageChanged(uint256 oldPercentage, uint256 newPercentage)` |
| `0x3e0916468971c6a0496bb9e570a6490523f6f34b85407a78e713c5d0287fb898` | `MaximumSubsidisationAmountChanged(uint256 oldAmount, uint256 newAmount)` |
| `0xa317c10673baf4f03b3c1041bd5ddbb537d0333a86fec3607c75f9dbb630f48f` | `PaymentTokenAdded(address token)` |
| `0x85a3e72f8dd6db3794f93109c3c5f5b79d6112f6979431c45f98b26134b42af2` | `PaymentTokenRemoved(address token)` |
| `0xcb61de73a9b971ce0608f81d0ce8617289d2a44503653d2c16693dc08bc0db2d` | `PriceFeedChanged(address token, address oldFeed, address newFeed, uint256 oldMaxPriceAge, uint256 newMaxPriceAge)` |
| `0x32f07544d40b6594a49132ac8f5e83e155ea95048a4793168328979fbe18be1f` | `AvaxDepositRangeUpdated(uint256 oldMin, uint256 newMin, uint256 oldMax, uint256 newMax)` |
| `0x243f5920d630b2ce83f8881e8e61dfba5c13da5a74bf035e6b28827571b29fa1` | `QiPriceMultiplierUpdated(uint256 oldQiPriceMultiplier, uint256 newQiPriceMultiplier)` |

### 1.6 BenqiChainlinkOracle (price oracle)

| topic0 | Event |
|--------|-------|
| `0xdd71a1d19fcba687442a1d5c58578f1e409af71a79d10fd95a4d66efd8fa9ae7` | `PricePosted(address asset, uint256 previousPriceMantissa, uint256 requestedPriceMantissa, uint256 newPriceMantissa)` |
| `0xd9e7d1778ca05570ced72c9aeb12a41fcc76f7f57ea25853dea228f8836d0022` | `FeedSet(address feed, string symbol)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |

### 1.7 EIP-1967 proxy lifecycle (sAVAX / Ignite / veQI)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Selectors verified present in the deployed `QiErc20Delegate`, `Comptroller`, sAVAX, and Ignite bytecode. Source: `Benqi-fi/BENQI-Smart-Contracts` (`lending/`, `sAVAX/`) + `Cyfrin/2025-01-benqi` (`ignite/src/Ignite.sol`). Interface `uint` canonicalized to `uint256`.

### 2.1 qiToken / qiErc20 / qiAVAX (per-market)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa0712d68` | `mint(uint256 mintAmount)` | qiErc20: supply underlying. Emits `Mint`+`AccrueInterest`+`Transfer`. |
| `0x1249c58b` | `mint()` | **qiAVAX only** (payable; native AVAX). |
| `0xdb006a75` | `redeem(uint256 redeemTokens)` | Burn qiTokens for underlying. **Same selector as `sAVAX.redeem(uint256)`** — disambiguate by `to`. |
| `0x852a12e3` | `redeemUnderlying(uint256 redeemAmount)` | |
| `0xc5ebeaec` | `borrow(uint256 borrowAmount)` | Emits `Borrow`. |
| `0x0e752702` | `repayBorrow(uint256 repayAmount)` | `type(uint).max` repays full debt. |
| `0x4e4d9fea` | `repayBorrow()` | **qiAVAX only** (payable). |
| `0x2608f818` | `repayBorrowBehalf(address borrower, uint256 repayAmount)` | qiErc20. |
| `0xe5974619` | `repayBorrowBehalf(address borrower)` | **qiAVAX only** (payable). |
| `0xf5e3c462` | `liquidateBorrow(address borrower, uint256 repayAmount, address qiTokenCollateral)` | qiErc20. Emits `LiquidateBorrow`. |
| `0xaae40a2a` | `liquidateBorrow(address borrower, address qiTokenCollateral)` | **qiAVAX only** (payable). |
| `0xb2a02ff1` | `seize(address liquidator, address borrower, uint256 seizeTokens)` | Cross-market collateral seizure. |
| `0xa9059cbb` / `0x23b872dd` / `0x095ea7b3` | `transfer` / `transferFrom` / `approve` | qiToken shares (ERC-20). |
| `0xc37f68e2` | `getAccountSnapshot(address)` | `(err, qiTokenBalance, borrowBalance, exchangeRateMantissa)` |
| `0xa6afed95` | `accrueInterest()` | Emits `AccrueInterest` (4-arg). |
| `0xbd6d894d` | `exchangeRateCurrent()` | Accrues, then returns exchange rate. |
| `0x182df0f5` | `exchangeRateStored()` | View; last-stored rate. |
| `0x17bfdfbc` / `0x95dd9193` | `borrowBalanceCurrent(address)` / `borrowBalanceStored(address)` | |
| `0x3b1d21a2` | `getCash()` | Underlying held by the market. |
| `0xd3bd2c72` | `supplyRatePerTimestamp()` | **Per-second** supply rate mantissa (NOT per-block). |
| `0xcd91801c` | `borrowRatePerTimestamp()` | **Per-second** borrow rate mantissa. |
| `0xcfa99201` | `accrualBlockTimestamp()` | **Unix timestamp** of last accrual (NOT block number). |
| `0x47bd3718` / `0x8f840ddd` / `0xaa5af0fd` / `0x173b9904` | `totalBorrows` / `totalReserves` / `borrowIndex` / `reserveFactorMantissa` | |
| `0x5fe3b567` | `comptroller()` | Returns the Unitroller address. |
| `0xf3fdb15a` | `interestRateModel()` | Per-market JumpRateModel. |
| `0x6f307dc3` | `underlying()` | Underlying ERC-20. **Reverts/absent on qiAVAX** (native market). |
| `0x5c60da1b` | `implementation()` | **Read for the qiErc20 delegate logic** — NOT the EIP-1967 slot. **Reverts/absent on qiAVAX** (monolithic). |
| `0x70a08231`/`0x18160ddd`/`0x313ce567`/`0x95d89b41`/`0x06fdde03` | `balanceOf`/`totalSupply`/`decimals`/`symbol`/`name` | qiTokens: **8 decimals**, `symbol()` = `qi`+underlying (e.g. "qiUSDCn"). |

### 2.2 Comptroller (behind Unitroller)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc2998238` | `enterMarkets(address[] qiTokens)` | Emits `MarketEntered`. |
| `0xede4edd0` | `exitMarket(address qiToken)` | Emits `MarketExited`. |
| `0x5ec88c79` | `getAccountLiquidity(address)` | `(err, liquidity, shortfall)`. Shortfall>0 ⇒ liquidatable. |
| `0xb0772d0b` | `getAllMarkets()` | All listed qiTokens (15 as of 2026-06). Re-read live. |
| `0x8e8f294b` | `markets(address qiToken)` | `(bool isListed, uint collateralFactorMantissa, bool isQied)` |
| `0x7dc0d1d0` | `oracle()` | The `BenqiChainlinkOracle` address. |
| `0xe8755446` | `closeFactorMantissa()` | |
| `0x4ada90af` | `liquidationIncentiveMantissa()` | |
| `0x4a584432` | `borrowCaps(address)` | Per-market borrow cap. |
| `0x26d71f1e` | `qiAddress()` | QI token used for rewards. |
| `0x05b9783d` | `rewardAccrued(uint8 rewardType, address holder)` | Per `rewardType` (0=QI,1=AVAX). |
| `0xcf9cfb61` | `supplyRewardSpeeds(uint8, address)` | |
| `0xc376fada` | `borrowRewardSpeeds(uint8, address)` | |
| `0x0952c563` | `claimReward(uint8 rewardType, address holder)` | Claim QI or AVAX rewards. |
| `0x744532ae` | `claimReward(uint8 rewardType, address holder, address[] qiTokens)` | |
| `0xa76b3fda` | `_supportMarket(address)` | Admin. Emits `MarketListed`. |
| `0xe4028eee` | `_setCollateralFactor(address,uint256)` | Admin. Emits `NewCollateralFactor`. |
| `0x3bcf7ec1` / `0x18c882a5` | `_setMintPaused(address,bool)` / `_setBorrowPaused(address,bool)` | Emit `ActionPaused(address,string,bool)`. |
| `0x8ebf6364` / `0x2d70db78` | `_setTransferPaused(bool)` / `_setSeizePaused(bool)` | Emit `ActionPaused(string,bool)`. |
| `0x55ee1fe1` | `_setPriceOracle(address)` | Emits `NewPriceOracle`. |
| `0x4c0cc832` | `_grantQi(address,uint256)` | Admin QI grant. Emits `QiGranted`. |
| `0xbb82aa5e` | `comptrollerImplementation()` | **Unitroller: read for live Comptroller logic** (storage slot 2). |

### 2.3 Unitroller

| Selector | Signature |
|----------|-----------|
| `0xe992a041` | `_setPendingImplementation(address)` |
| `0xc1e80334` | `_acceptImplementation()` |
| `0xb71d1a0c` | `_setPendingAdmin(address)` |
| `0xe9c714f2` | `_acceptAdmin()` |

### 2.4 sAVAX / StakedAvax

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5bcb2fc6` | `submit()` | Payable. Stake AVAX → mint sAVAX. Emits `Submitted`. |
| `0xd0e30db0` | `deposit()` | Payable. **Same selector as WAVAX `deposit()`**. Emits `Deposit`. |
| `0xc9d2ff9d` | `requestUnlock(uint256 shareAmount)` | Start cooldown. Emits `UnlockRequested`. |
| `0x01550f64` | `cancelPendingUnlockRequests()` | Emits `UnlockCancelled`. |
| `0xbe040fb0` | `redeem()` | Redeem all matured unlock requests. Emits `Redeem`. |
| `0xdb006a75` | `redeem(uint256 unlockIndex)` | **Same selector as `qiToken.redeem(uint256)`** — disambiguate by `to`. |
| `0x0d10d32c` | `redeemOverdueShares()` | |
| `0x0f7e2048` | `redeemOverdueShares(uint256 unlockIndex)` | |
| `0x4a36d6c1` | `getPooledAvaxByShares(uint256 shareAmount)` | sAVAX → AVAX (the exchange rate). |
| `0xf1ee8d92` | `getSharesByPooledAvax(uint256 avaxAmount)` | AVAX → sAVAX. |
| `0xe1a472b9` | `accrueRewards(uint256 amount)` | Role-gated; updates exchange rate. Emits `AccrueRewards`. |
| `0x629e8056` / `0x3a98ef39` | `totalPooledAvax()` / `totalShares()` | |

### 2.5 Ignite (validator staking)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7d1aacad` | `registerWithStake(string nodeId, bytes blsProofOfPossession, uint256 validationDuration)` | Payable. Stake AVAX collateral. Emits `NewRegistration`. |
| `0x80286737` | `registerWithAvaxFee(string,bytes,uint256)` | Payable. Pay-As-You-Go AVAX fee. |
| `0x8567a2e5` | `registerWithErc20Fee(address tokenAddress, string,bytes,uint256)` | PAYG with an ERC-20 fee. |
| `0xac966e15` | `registerWithoutCollateral(string,bytes,uint256)` | Role-gated. |
| `0x1df1a433` | `registerWithPrevalidatedQiStake(address beneficiary, string,bytes,uint256, uint256 qiAmount)` | Role-gated; QI-collateral path *(not in the older deployed impl — verify before keying)*. |
| `0x5b499a97` | `redeemAfterExpiry(string nodeId)` | Reclaim collateral after the validation period. Emits `Redeem`. |
| `0x0ffbccdb` | `releaseLockedTokens(string nodeId, bool failed)` | Payable; role-gated. |
| `0x2e1a7d4d` | `withdraw(uint256 amount)` | Admin protocol-revenue withdrawal. Emits `Withdraw(uint256)`. |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | |

### 2.6 BenqiChainlinkOracle

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfc57d4df` | `getUnderlyingPrice(address qiToken)` | Comptroller's pricing entry point. Mantissa scaled to `36 − underlyingDecimals`. |
| `0x3b39a51c` / `0x0c607acf` | `getFeed(string symbol)` / `setFeed(string symbol, address feed)` | Feed keyed by underlying symbol. |

---

## 3. Addresses — Avalanche C-Chain (chain ID 43114)  *[the only deployment]*

All verified via `eth_getCode` (non-empty) on `https://avalanche-c-chain-rpc.publicnode.com` on 2026-06-08. Proxy wiring read live (see §8).

### 3.1 Core lending system

| Role | Address | One-liner |
|------|---------|-----------|
| **COMPTROLLER** (Unitroller proxy) | `0x486Af39519B4Dc9a7fCcd318217352830E8AD9b4` | The risk + reward engine. `comptrollerImplementation()`→ impl below; `oracle()`→ ORACLE; `admin()`→ `0xb952c860…dB3D` (Timelock). `getAllMarkets()` = 15. Point all market-policy + reward monitors here. |
| Comptroller (impl/logic) | `0xd8E426c61b0FBBdA06e9F603263abEa09D717dbD` | Comptroller logic behind the Unitroller. |
| **ORACLE** (`BenqiChainlinkOracle`) | `0xf81b4C4ABf7De8B8Fc560D66f0eb70598D8bf15e` | Symbol→Chainlink-feed mapping. **Non-upgradeable** (no EIP-1967 slot). |
| QI_TOKEN (`Qi`) | `0x8729438EB15e2C8B576fCc6AeCdA6A148776C0F5` | Governance + reward token. `name()="BENQI"`, `symbol()="QI"`, 18d, totalSupply 7.2B. Non-upgradeable. **NB: same address is a bridged decoy on BNB — §6.** |
| qiErc20Delegate (logic v-current) | `0xf28043598A1824053097D5c4FEDd7CD1cF731E76` | Shared logic for newer qiErc20 delegators (qiUSDCn/qisAVAX/qiBTC.b/…). |
| qiErc20Delegate (logic v-older) | `0x76145E99d3F4165A313e8219141ae0D26900b710` | Shared logic for older qiErc20 delegators (qiUSDC/qiUSDT/qiETH/qiQI/…). |
| Comptroller admin (Timelock) | `0xB952C860F1296eAe87494c7d8a4c96EDd43adb3d` | `admin()` of the Unitroller (a contract; governance Timelock/multisig). |

### 3.2 Markets (15 — `getAllMarkets()`; `symbol` = `qi`+underlying, **8 decimals**)

| Market | qiToken address | Underlying | Underlying address |
|--------|-----------------|-----------|--------------------|
| **qiAVAX** (CEther) | `0x5C0401e81Bc07Ca70fAD469b451682c0d747Ef1c` | native AVAX | — (no `underlying()`) |
| qiBTC | `0xe194c4c5aC32a3C9ffDb358d9Bfd523a0B6d1568` | WBTC.e | `0x50b7545627a5162F82A992c33b87aDc75187B218` |
| qiBTC.b | `0x89a415b3D20098E6A6C8f7a59001C67BD3129821` | BTC.b | `0x152b9d0FdC40C096757F570A51E494bd4b943E50` |
| qiETH | `0x334AD834Cd4481BB02d09615E7c11a00579A7909` | WETH.e | `0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB` |
| qiLINK | `0x4e9f683A27a6BdAD3FC2764003759277e93696e6` | LINK.e | `0x5947BB275c521040051D82396192181b413227A3` |
| qiUSDT | `0xc9e5999b8e75C3fEB117F6f73E664b9f3C8ca65C` | USDT.e | `0xc7198437980c041c805A1EDcbA50c1Ce5db95118` |
| qiUSDTn | `0xd8fcDa6ec4Bdc547C0827B8804e89aCd817d56EF` | USDt (native) | `0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7` |
| qiUSDC | `0xBEb5d47A3f720Ec0a390d04b4d41ED7d9688bC7F` | USDC.e | `0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664` |
| qiUSDCn | `0xB715808a78F6041E46d61Cb123C9B4A27056AE9C` | USDC (native) | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` |
| qiDAI | `0x835866d37AFB8CB8F8334dCCdaf66cf01832Ff5D` | DAI.e | `0xd586E7F844cEa2F87f50152665BCbc2C279D8d70` |
| qiBUSD | `0x872670CcAe8C19557cC9443Eff587D7086b8043A` | BUSD.e | `0x9C9e5fD8bbc25984B178FdCE6117Defa39d2db39` |
| qiQI | `0x35Bd6aedA81a7E5FC7A7832490e71F757b0cD9Ce` | QI | `0x8729438EB15e2C8B576fCc6AeCdA6A148776C0F5` |
| **qisAVAX** | `0xF362feA9659cf036792c9cb02f8ff8198E21B4cB` | sAVAX | `0x2b2C81e08f1Af8835a78Bb2A90AE924ACE0eA4bE` |
| qiAUSD | `0x190D94613a09ad7931fcD17cd6A8f9b6b47AD414` | AUSD | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |
| qiEURC | `0x7fa9442f28948e948e86c0258e361f1208699b41` | EURC | `0xC891EB4cbDEFf6e073e859e987815Ed1505c2ACD` |

> qiAVAX is the only **monolithic** market (`QiAvax`, codelen ~21 KB / 21,080 bytes, no `implementation()`/`underlying()`, native-AVAX mint/repay overloads §2.1). The other 14 are thin `qiErc20Delegator` proxies (codelen ~8 KB / 7,961 bytes) that delegate to one of the two shared delegate logic contracts (~22 KB each, §3.1). The qisAVAX market's underlying is the sAVAX liquid-staking token — a lending↔staking link.

### 3.3 Interest rate models

Per-market `JumpRateModel` contracts; read each market's live model via `qiToken.interestRateModel()` (`0xf3fdb15a`). Sampled live (2026-06-08): qiUSDCn `0xF4FFc8e539a4FB003878b18864c713EB14ec8B6E`; qiUSDC/qiUSDT (share) `0x52C83a032f2ec3edC5dd358e5BA1F6Ee46c0e4a6`; qisAVAX `0xc436F5BC8A8bD9C9e240a2A83D44705EC87a9d55`; qiBTC.b `0xd290D05Fd2A177b4dA4A5014A6fdABEAdBbB5638`; qiQI `0xf805e22C81Ef330967eEc52f7eDb0C6b31FD5cCf`; qiETH `0x0c89E33b8f6e06a64e96E4DdD500a2cbD0E01614`. IRMs change with governance re-parameterizations — always read live.

### 3.4 Liquid staking + validator staking

| Role | Address | One-liner |
|------|---------|-----------|
| **sAVAX** (`StakedAvax`) | `0x2b2C81e08f1Af8835a78Bb2A90AE924ACE0eA4bE` | Liquid-staked AVAX ERC-20. `name()="Staked AVAX"`, `symbol()="sAVAX"`. **EIP-1967 transparent proxy** → impl `0xb791…fa53`, admin `0x2295…5a66`. |
| **IGNITE** | `0xB71a820d80189073F69498010cb67bDDAe050633` | Validator-staking (PAYG + stake). **EIP-1967 transparent proxy** → impl `0xa61f…1554`, admin `0x3ebb…21ca`. |
| veQI (`VeQi`) | `0x7Ee65Fdc1C534A6b4f9ea2Cc3ca9aC8d6c602aBd` | Vote-escrowed QI (validator weight / governance). **EIP-1967 transparent proxy** → impl `0x11a6…9668`, admin `0x73ad…9930`. |

---

## 4. *(reserved)*

---

## 5. *(reserved)*

---

## 6. Chains with NO BENQI deployment

**BENQI lending + liquid staking + Ignite are deployed ONLY on Avalanche C-Chain (43114).** Verified by `eth_getCode` returning empty (`0x`) for the Comptroller, sAVAX, Ignite, and qiUSDCn on **Ethereum (1), Base (8453), BNB (56), Arbitrum (42161), Optimism (10), Polygon (137)**. Corroborated by `docs.benqi.fi` (Avalanche-only) and DeFiLlama. Do not author lending/staking monitors for BENQI on these chains.

> **Decoy:** the QI token address `0x8729438EB15e2C8B576fCc6AeCdA6A148776C0F5` **is PRESENT on BNB Smart Chain** (`name()="BENQI"`, `symbol()="QI"`, totalSupply ≈ 27.3M, **not a proxy**). This is a **bridged QI representation** (a fraction of the 7.2B Avalanche supply), deployed at the same address via a deterministic deployment — it is a token only. **There is no BENQI lending or staking on BNB.** Treat a QI hit on BNB as a token-bridge artifact, never as a BENQI deployment.

---

## 7. Cross-chain summary

| Chain | ID | BENQI? | Comptroller | sAVAX | Ignite | QI token | Markets |
|-------|----|--------|-------------|-------|--------|----------|---------|
| **Avalanche C-Chain** | 43114 | ✅ full | `0x486Af395…D9b4` | `0x2b2C81e0…A4bE` | `0xB71a820d…0633` | `0x8729438E…C0F5` | 15 |
| Ethereum | 1 | ❌ | — | — | — | — | 0 |
| Base | 8453 | ❌ | — | — | — | — | 0 |
| BNB Smart Chain | 56 | ❌ (token-bridge decoy only) | — | — | — | `0x8729438E…C0F5` (bridged QI) | 0 |
| Arbitrum One | 42161 | ❌ | — | — | — | — | 0 |
| Optimism | 10 | ❌ | — | — | — | — | 0 |
| Polygon PoS | 137 | ❌ | — | — | — | — | 0 |

Patterns to internalize:
1. **Single-chain protocol.** Key everything to chainId 43114. Any "BENQI" claim on another chain is a fork or a bridged-token artifact.
2. **Markets are enumerated, not derived.** Each qiErc20 is a separately-deployed delegator (no CREATE2 salt). Read `getAllMarkets()`; don't hardcode the 15-count.
3. **Comptroller `admin()` = `0xb952…dB3D` (Timelock).** Parameter changes (collateral factor, caps, pauses, oracle, reward speeds) originate there.

---

## 8. Proxies (old & new)

BENQI mixes **three** patterns. Getting them wrong is the #1 integration error.

| Contract | Pattern | How to read the impl | Verified (Avalanche) |
|----------|---------|----------------------|----------------------|
| **Unitroller** (Comptroller) | **Compound Unitroller** — NOT EIP-1967. Impl in **storage slot 2** (`comptrollerImplementation`); `admin` slot 0, `pendingAdmin` slot 1. | `comptrollerImplementation()` (`0xbb82aa5e`) or `eth_getStorageAt(slot 2)`. **EIP-1967 impl slot empty.** | `comptrollerImplementation()`=`0xd8E4…7dbD`; `admin()`=`0xb952…dB3D`; `oracle()`=`0xf81b…f15e`; EIP-1967 slot = `0x0` ✓ |
| **qiErc20** (qiErc20Delegator) | **Compound delegator** — NOT EIP-1967. `implementation` is a plain storage var; upgraded via `_setImplementation(address,bool,bytes)`. | `implementation()` (`0x5c60da1b`). | qiUSDCn `implementation()`=`0xf280…1E76`; `comptroller()`=`0x486A…D9b4`; `underlying()`=native USDC; EIP-1967 slot = `0x0` ✓ |
| **qiAVAX** (QiAvax / CEther) | **Immutable** — no delegator, no proxy. | `implementation()` **reverts**; `underlying()` **reverts**. | codelen ≈ 21 KB (21,080 bytes); both getters revert ✓ |
| **sAVAX** (StakedAvax) | **EIP-1967 transparent proxy** | EIP-1967 impl slot `0x360894…bbc`; admin slot `0xb53127…6103`. | impl=`0xb791c7a42fd0d10f90deaa906a8735f79719fa53`; admin=`0x2295e1cad2ea081a4a2ed85f59006e6fd42b5a66` ✓ |
| **Ignite** | **EIP-1967 transparent proxy** | EIP-1967 impl/admin slots. | impl=`0xa61f2411351649cc0ce4443517f16b0f522e1554`; admin=`0x3ebbfc5f7aeb55f294f71846f2c3af4df79421ca` ✓ |
| **veQI** (VeQi) | **EIP-1967 transparent proxy** | EIP-1967 impl/admin slots. | impl=`0x11a6f0abe9f8cac70d4f81d872498e7a630c9668`; admin=`0x73ad25e61d707c900393eca73a6909a59d6a9930` ✓ |
| **BenqiChainlinkOracle** | **Non-upgradeable** | EIP-1967 impl slot = `0x0`. | confirmed empty ✓ |
| **QI token** (`Qi`) | **Non-upgradeable** ERC-20 | EIP-1967 impl slot = `0x0`. | confirmed empty ✓ |

```
Unitroller storage layout (Compound):
  slot 0 = admin            (= Timelock 0xb952…dB3D)
  slot 1 = pendingAdmin
  slot 2 = comptrollerImplementation   ← live Comptroller logic
  slot 3 = pendingComptrollerImplementation
EIP-1967 impl slot  = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc  (populated on sAVAX/Ignite/veQI; EMPTY on Unitroller/qiTokens/oracle/QI)
EIP-1967 admin slot = 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103
Upgraded(address) topic0 = 0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b  (watch on sAVAX/Ignite/veQI)
```

---

## 9. Detection invariants & gotchas

1. **Timestamp, not block.** `accrualBlockTimestamp()` is a unix timestamp; rate accessors are `supplyRatePerTimestamp()`/`borrowRatePerTimestamp()` (**per-second**). APR = `ratePerTimestamp × 31_536_000 / 1e18`. Calling `accrualBlockNumber()`/`supplyRatePerBlock()` **reverts** (verified).
2. **`AccrueInterest` is 4-arg** (`0x4dec04e7…`, **128-byte data**). Stock-Compound 3-arg decoders (`0x875352fb…`) mis-parse it — that 3-arg topic produces **zero** logs on BENQI markets.
3. **`Redeem` is overloaded across three contracts, all colliding in name.** qiToken `Redeem(address,uint256,uint256)` (3-arg, topic0 `0xe5b754fb…`); sAVAX `Redeem(address,uint256,uint256,uint256)` (4-arg, topic0 `0xbd5034ff…`); Ignite `Redeem(string,uint256,address,uint256)` (topic0 `0xee444713…`). **Three different topic0s** — key on the exact topic0 AND the emitter, never on the name.
4. **`Mint` topic0 collides with Uniswap/Pangolin V2** (`0x4c209b5f…`). **sAVAX `Deposit` topic0 collides with WAVAX `Deposit`** (`0xe1fffcc4…`). Always filter by emitter.
5. **Rewards are dual-token and on the Comptroller.** `tokenType`/`rewardType` is `0 = QI`, `1 = AVAX`. `Distributed{Supplier,Borrower}Reward` carry `tokenType` as **topic1 (indexed)**, `qiToken` as topic2, holder as topic3 — filter on topic1 to split QI- vs AVAX-reward flows. There is **no** MultiRewardDistributor and **no** COMP-style event. Reward-speed changes = `SupplyRewardSpeedUpdated`/`BorrowRewardSpeedUpdated` (qiToken indexed).
6. **qiTokens are 8 decimals; underlying decimals vary** (USDC/USDt 6, BTC.b/WBTC.e 8, most others 18). `exchangeRateStored` scales by `1e(18 + underlyingDec − 8)`; `getUnderlyingPrice` returns a mantissa scaled to `36 − underlyingDec`.
7. **qiAVAX is special.** It is the native-AVAX market, a monolithic CEther with **no `underlying()`/`implementation()`** and payable mint/repay/liquidate overloads (`mint()` `0x1249c58b`, `repayBorrow()` `0x4e4d9fea`, `liquidateBorrow(address,address)` `0xaae40a2a`). Do not assume the qiErc20 ABI for it.
8. **qisAVAX bridges the two products.** Its underlying is the sAVAX liquid-staking token — a depeg or pause on sAVAX cascades into the qisAVAX lending market.
9. **Caps emit indexed-qiToken events** (`NewBorrowCap`, qiToken `indexed`) — filter on topic1 for a specific market. BENQI uses **only `NewBorrowCap`** (no `NewSupplyCap` in this fork).
10. **Pausing uses two `ActionPaused` overloads only.** Per-market (Mint/Borrow) = `ActionPaused(address,string,bool)` (`0x71aec636…`); global (Transfer/Seize) = `ActionPaused(string,bool)` (`0xef159d9a…`).
11. **Liquidations:** `LiquidateBorrow` on the borrowed qiToken carries `qiTokenCollateral` + `seizeTokens`; the seized market emits a `Transfer` of qiToken shares to the liquidator (plus a protocol-cut transfer per `protocolSeizeShareMantissa`).
12. **sAVAX unstaking is two-phase with a cooldown.** `requestUnlock` (`UnlockRequested`) → wait → `redeem` (`Redeem` 4-arg). Overdue requests need `redeemOverdueShares`. The AVAX-per-share rate only moves on `AccrueRewards` (rare).
13. **Ignite validator events are string-`nodeId`-keyed and infrequent** (registrations batch — ~10 per ~22h window observed). `NewRegistration`/`Redeem`/`RegistrationExpired`/`ValidatorSlashed` are the lifecycle; `ValidatorSlashed` is the high-severity one.
14. **BNB QI is a bridged-token decoy** (§6) — never a BENQI deployment.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- qiToken / qiAVAX (per-market)
TOPIC_ACCRUE_INTEREST        = '\x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04'  -- 4-arg, 128B
TOPIC_MINT                   = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'  -- collides w/ UniV2 Mint
TOPIC_REDEEM                 = '\xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929'  -- qiToken (3-arg)
TOPIC_BORROW                 = '\x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'
TOPIC_REPAY_BORROW           = '\x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1'
TOPIC_LIQUIDATE_BORROW       = '\x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
TOPIC_RESERVES_ADDED         = '\xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5'
TOPIC_RESERVES_REDUCED       = '\x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e'
TOPIC_NEW_RESERVE_FACTOR     = '\xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460'
TOPIC_NEW_MARKET_IRM         = '\xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926'
TOPIC_ERC20_TRANSFER         = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_FAILURE                = '\x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0'
-- Comptroller (risk + rewards)
TOPIC_MARKET_LISTED          = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_MARKET_ENTERED         = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'
TOPIC_MARKET_EXITED          = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_NEW_CLOSE_FACTOR       = '\x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9'
TOPIC_NEW_COLLATERAL_FACTOR  = '\x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5'
TOPIC_NEW_LIQ_INCENTIVE      = '\xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316'
TOPIC_NEW_PRICE_ORACLE       = '\xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22'
TOPIC_NEW_BORROW_CAP         = '\x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6'
TOPIC_NEW_BORROW_CAP_GUARD   = '\xeda98690e518e9a05f8ec6837663e188211b2da8f4906648b323f2c1d4434e29'
TOPIC_NEW_PAUSE_GUARDIAN     = '\x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e'
TOPIC_ACTION_PAUSED_GLOBAL   = '\xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0'  -- (string,bool)
TOPIC_ACTION_PAUSED_MARKET   = '\x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0'  -- (address,string,bool)
TOPIC_DIST_SUPPLIER_REWARD   = '\xaccd035d02c456be35306aecd5a5fe62320713dde09ccd68b0a5e8ed93039999'  -- topic1=tokenType(0=QI,1=AVAX)
TOPIC_DIST_BORROWER_REWARD   = '\xa1b6a046664a0ecf068059f26de56878f8d0e799907ca2e42d9148ccbdc717a7'
TOPIC_SUPPLY_REWARD_SPEED    = '\x2577edc53863f2e6d759b5da2c36549292f23909793d20feb1886bc21b17782f'
TOPIC_BORROW_REWARD_SPEED    = '\xee48fe28e41d25c72d48e0c4580dbeac6fb4ef83cd3401ced307912114e2e5eb'
TOPIC_CONTRIB_QI_SPEED       = '\xa94c5c08a0ebc2f092acf456a0606b4580b03d985a0f30c433bc16bb282c4a0f'
TOPIC_QI_GRANTED             = '\x23b40999b12039b28906192443f166517e9b2c60ff1fd6ec74637416e1204417'
-- Unitroller
TOPIC_NEW_IMPLEMENTATION     = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'
TOPIC_NEW_PENDING_IMPL       = '\xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815'
-- sAVAX (liquid staking)
TOPIC_SAVAX_SUBMITTED        = '\xbb0070894135d02edfa550b04d7e5e141aa8090b46e57597ad45bfedd6554498'
TOPIC_SAVAX_UNLOCK_REQUESTED = '\xd843ce9ef55b27026be6c5e44e9f58097e0ebfa0d9d2d5823cb8ffa779585170'
TOPIC_SAVAX_UNLOCK_CANCELLED = '\x7e4a9502fd577f76f1dc8c9c8f63196816f7c1bd73c6db99f888e8d7bb2f8998'
TOPIC_SAVAX_REDEEM           = '\xbd5034ffbd47e4e72a94baa2cdb74c6fad73cb3bcdc13036b72ec8306f5a7646'  -- 4-arg
TOPIC_SAVAX_REDEEM_OVERDUE   = '\xeaca243f6502ade1b9ea0909306c290366d6ea6778ca407ca4415c4a0f45e353'
TOPIC_SAVAX_ACCRUE_REWARDS   = '\x8fbf6a230d02fb8f41af8c1ca90b126472e11286c47d7ed86bb2e1fc51a283d8'
TOPIC_SAVAX_MINTING_PAUSED   = '\x35365f539a67058ad0735a24a50fe45b0ee05207919e9f4a2f60d855f55e0c0e'
TOPIC_SAVAX_MINTING_RESUMED  = '\x8a53acd29b3c02ba82b89c57b23196b792ccb00a28515221f71bd92eafbc2dc3'
-- Ignite (validator staking)
TOPIC_IGNITE_NEW_REGISTER    = '\x911545ab01a7553b2c4eb100eb4054703d821e76fc5d0504a07b8246aa3b1232'
TOPIC_IGNITE_REG_DELETED     = '\x04393636f796e0824c4807e9d1a98080042d261b6d4feea240a3d698ee713b52'
TOPIC_IGNITE_REDEEM          = '\xee444713008e3c266c8fb74c287dd853d5eb23d60c7e77730b0ed536556efd9a'
TOPIC_IGNITE_REG_EXPIRED     = '\x834288ca549398403511a8b546b7e4885ac51b98630c0ffa3a07858dc5d9e40d'
TOPIC_IGNITE_VALID_SLASHED   = '\xeb8d450bff74ef3c1d9319f07855afedfdfa4dce6a223c1c1920a3ac1088d3b4'
TOPIC_IGNITE_VALID_REWARDED  = '\xc7b0487e0a21287b5a35f7ddf5ed5d8e9d30338d3ad76e60c0986c52addace48'
-- Oracle
TOPIC_PRICE_POSTED           = '\xdd71a1d19fcba687442a1d5c58578f1e409af71a79d10fd95a4d66efd8fa9ae7'
TOPIC_FEED_SET               = '\xd9e7d1778ca05570ced72c9aeb12a41fcc76f7f57ea25853dea228f8836d0022'
-- EIP-1967 proxy lifecycle (sAVAX/Ignite/veQI)
TOPIC_UPGRADED               = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED          = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'

-- ===== Selectors (chain-agnostic) =====
SEL_MINT                     = '\xa0712d68'   -- mint(uint256)  [qiErc20]
SEL_MINT_AVAX                = '\x1249c58b'   -- mint()         [qiAVAX]
SEL_REDEEM                   = '\xdb006a75'   -- redeem(uint256) [qiToken AND sAVAX.redeem(uint256)!]
SEL_REDEEM_UNDERLYING        = '\x852a12e3'
SEL_BORROW                   = '\xc5ebeaec'
SEL_REPAY_BORROW             = '\x0e752702'
SEL_REPAY_BORROW_AVAX        = '\x4e4d9fea'   -- repayBorrow() [qiAVAX]
SEL_LIQUIDATE_BORROW         = '\xf5e3c462'
SEL_LIQUIDATE_BORROW_AVAX    = '\xaae40a2a'   -- liquidateBorrow(address,address) [qiAVAX]
SEL_SUPPLY_RATE_PER_TS       = '\xd3bd2c72'   -- supplyRatePerTimestamp()
SEL_ACCRUAL_BLOCK_TIMESTAMP  = '\xcfa99201'
SEL_QITOKEN_IMPLEMENTATION   = '\x5c60da1b'   -- implementation()  (qiErc20 delegator)
SEL_COMPTROLLER_IMPL         = '\xbb82aa5e'   -- comptrollerImplementation() (Unitroller)
SEL_GET_ALL_MARKETS          = '\xb0772d0b'
SEL_CLAIM_REWARD             = '\x0952c563'   -- claimReward(uint8,address)
SEL_CLAIM_REWARD_MKTS        = '\x744532ae'   -- claimReward(uint8,address,address[])
SEL_ORACLE                   = '\x7dc0d1d0'
SEL_GET_UNDERLYING_PRICE     = '\xfc57d4df'
-- sAVAX
SEL_SAVAX_SUBMIT             = '\x5bcb2fc6'   -- submit()
SEL_SAVAX_REQUEST_UNLOCK     = '\xc9d2ff9d'   -- requestUnlock(uint256)
SEL_SAVAX_REDEEM_ALL         = '\xbe040fb0'   -- redeem()
SEL_SAVAX_GET_AVAX_BY_SHARES = '\x4a36d6c1'   -- getPooledAvaxByShares(uint256)
SEL_SAVAX_ACCRUE_REWARDS     = '\xe1a472b9'   -- accrueRewards(uint256)
-- Ignite
SEL_IGNITE_REG_WITH_STAKE    = '\x7d1aacad'   -- registerWithStake(string,bytes,uint256)
SEL_IGNITE_REG_AVAX_FEE      = '\x80286737'
SEL_IGNITE_REG_ERC20_FEE     = '\x8567a2e5'
SEL_IGNITE_REDEEM_EXPIRY     = '\x5b499a97'   -- redeemAfterExpiry(string)
SEL_IGNITE_RELEASE_LOCKED    = '\x0ffbccdb'

-- ===== Addresses (Avalanche C-Chain, chain 43114) =====
AVAX_COMPTROLLER             = '\x486af39519b4dc9a7fccd318217352830e8ad9b4'  -- Unitroller proxy
AVAX_COMPTROLLER_IMPL        = '\xd8e426c61b0fbbda06e9f603263abea09d717dbd'
AVAX_ORACLE                  = '\xf81b4c4abf7de8b8fc560d66f0eb70598d8bf15e'
AVAX_QI_TOKEN                = '\x8729438eb15e2c8b576fcc6aecda6a148776c0f5'  -- decoy-present on BNB
AVAX_SAVAX                   = '\x2b2c81e08f1af8835a78bb2a90ae924ace0ea4be'
AVAX_IGNITE                  = '\xb71a820d80189073f69498010cb67bddae050633'
AVAX_VEQI                    = '\x7ee65fdc1c534a6b4f9ea2cc3ca9ac8d6c602abd'
AVAX_COMPTROLLER_ADMIN       = '\xb952c860f1296eae87494c7d8a4c96edd43adb3d'  -- Timelock
-- markets
AVAX_QIAVAX                  = '\x5c0401e81bc07ca70fad469b451682c0d747ef1c'  -- CEther (monolithic)
AVAX_QIBTC                   = '\xe194c4c5ac32a3c9ffdb358d9bfd523a0b6d1568'  -- WBTC.e
AVAX_QIBTCB                  = '\x89a415b3d20098e6a6c8f7a59001c67bd3129821'  -- BTC.b
AVAX_QIETH                   = '\x334ad834cd4481bb02d09615e7c11a00579a7909'
AVAX_QILINK                  = '\x4e9f683a27a6bdad3fc2764003759277e93696e6'
AVAX_QIUSDT                  = '\xc9e5999b8e75c3feb117f6f73e664b9f3c8ca65c'  -- USDT.e
AVAX_QIUSDTN                 = '\xd8fcda6ec4bdc547c0827b8804e89acd817d56ef'  -- native USDt
AVAX_QIUSDC                  = '\xbeb5d47a3f720ec0a390d04b4d41ed7d9688bc7f'  -- USDC.e
AVAX_QIUSDCN                 = '\xb715808a78f6041e46d61cb123c9b4a27056ae9c'  -- native USDC
AVAX_QIDAI                   = '\x835866d37afb8cb8f8334dccdaf66cf01832ff5d'
AVAX_QIBUSD                  = '\x872670ccae8c19557cc9443eff587d7086b8043a'
AVAX_QIQI                    = '\x35bd6aeda81a7e5fc7a7832490e71f757b0cd9ce'
AVAX_QISAVAX                 = '\xf362fea9659cf036792c9cb02f8ff8198e21b4cb'
AVAX_QIAUSD                  = '\x190d94613a09ad7931fcd17cd6a8f9b6b47ad414'
AVAX_QIEURC                  = '\x7fa9442f28948e948e86c0258e361f1208699b41'

-- ===== EIP-1967 slots =====
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'  -- sAVAX/Ignite/veQI (EMPTY on Unitroller/qiTokens/oracle/QI)
EIP1967_ADMIN_SLOT           = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
```

---

## 11. Verification & sources

- **topic0 / selectors:** all computed locally as `keccak256(canonical sig)` / `[0:4]` (pycryptodome). qiToken/Comptroller/Unitroller signatures taken verbatim from `Benqi-fi/BENQI-Smart-Contracts` `lending/QiTokenInterfaces.sol`, `lending/Comptroller.sol`, `lending/Unitroller.sol`; sAVAX from `sAVAX/StakedAvax.sol`; Ignite from `Cyfrin/2025-01-benqi` `ignite/src/Ignite.sol`; oracle from `lending/Chainlink/BenqiChainlinkOracle.sol`. Spot-matched to stock Compound selectors (`mint`=`0xa0712d68`, `borrow`=`0xc5ebeaec`, `getUnderlyingPrice`=`0xfc57d4df`, `enterMarkets`=`0xc2998238`).
- **Live topic cross-checks (Avalanche, last ~40k blocks):** `AccrueInterest` 4-arg = **829** qiUSDCn logs with **128-byte data** (3-arg topic `0x875352fb…` = 0 logs); `Mint` 264, `Borrow` 204 on qiUSDCn; `DistributedSupplierReward` 3668 / `DistributedBorrowerReward` 960 on the Comptroller; sAVAX `Submitted` 18, `UnlockRequested` 11, `Redeem`(4-arg) 5; Ignite `NewRegistration` (`0x911545ab…`) confirmed present in real logs (10 in one window).
- **Accrual model (live):** `accrualBlockNumber()`/`supplyRatePerBlock()` **revert**; `accrualBlockTimestamp()` returns a unix timestamp; `supplyRatePerTimestamp()` returns a per-second mantissa. Comptroller exposes `getBlockTimestamp()` and `rewardQi=0`/`rewardAvax=1` constants.
- **Addresses:** ground truth = `docs.benqi.fi/resources/contracts` (core-markets, liquid-staking, ignite pages) cross-checked with on-chain `Comptroller.getAllMarkets()` (returns the 15 listed) and per-market `symbol()`/`underlying()`. Every address `eth_getCode`-verified non-empty on Avalanche.
- **Proxy wiring (live):** Comptroller `comptrollerImplementation()`→`0xd8E4…7dbD`, `admin()`→`0xb952…dB3D` (a contract = Timelock), `oracle()`→`0xf81b…f15e`; qiUSDCn `implementation()`→`0xf280…1E76`, `comptroller()`→Comptroller, `underlying()`→native USDC, `symbol()`→"qiUSDCn", `decimals()`→8; qiAVAX `implementation()`/`underlying()` **revert** (monolithic CEther). EIP-1967 impl/admin slots read directly: sAVAX impl `0xb791…fa53`/admin `0x2295…5a66`, Ignite impl `0xa61f…1554`/admin `0x3ebb…21ca`, veQI impl `0x11a6…9668`/admin `0x73ad…9930`; Unitroller, qiUSDCn, oracle, and QI EIP-1967 slots all empty (Compound-delegator / non-upgradeable confirmed). Ignite registration selectors verified present in the deployed impl bytecode.
- **Non-deployment:** Comptroller / sAVAX / Ignite / qiUSDCn return empty `eth_getCode` on Ethereum, Base, BNB, Arbitrum, Optimism, Polygon. The QI token address alone returns code on BNB (`name()="BENQI"`, supply ≈ 27.3M, not a proxy) — a bridged-token decoy, not a BENQI deployment.

Authoritative sources:
- [`Benqi-fi/BENQI-Smart-Contracts`](https://github.com/Benqi-fi/BENQI-Smart-Contracts) — `lending/` (Comptroller, Unitroller, QiToken/QiErc20/QiAvax, BenqiChainlinkOracle, Qi), `sAVAX/StakedAvax.sol`, `veQI/`
- [`Cyfrin/2025-01-benqi`](https://github.com/Cyfrin/2025-01-benqi) — `ignite/src/Ignite.sol` (audit snapshot; canonical Ignite event/function source)
- [docs.benqi.fi/resources/contracts](https://docs.benqi.fi/resources/contracts) — official address registry (core-markets / liquid-staking / ignite)
- [Compound V2](https://github.com/compound-finance/compound-protocol) — fork ancestor (cToken/Comptroller/Unitroller)
- RPCs: publicnode (`avalanche-c-chain-rpc`, plus `ethereum-rpc`, `base-rpc`, `bsc-rpc`, `arbitrum-one-rpc`, `optimism-rpc`, `polygon-bor-rpc` for absence checks)
