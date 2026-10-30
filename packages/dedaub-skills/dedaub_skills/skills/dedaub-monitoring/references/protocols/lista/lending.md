# Lista Lending (Moolah) — Topics, Selectors, Addresses (BNB Chain, Ethereum)

**Status:** verified against live RPC on BNB Chain (56) and Ethereum (1) and the canonical `lista-dao/moolah` repo on 2026-10-30.
**Scope:** the Moolah isolated-market lending engine and everything around it: MoolahVault (ERC-4626 curated vaults), MoolahVaultFactory, MarketFactory, IRMs, collateral providers, LendingBroker fixed-rate markets, liquidators, the "Smart Lending" StableSwap LP collateral, and Credit Loans. Topics and selectors are chain-agnostic. Addresses are network-specific.

Moolah is a fork of Morpho Blue. It keeps the Morpho Blue market model (`Id = keccak256(abi.encode(MarketParams))`, shares accounting, `onBehalf` attribution) and **the same event signatures**, so most Moolah topic0s are identical to Morpho Blue topic0s. Moolah adds role-based access control, per-market whitelists, collateral/loan "providers", per-market brokers and a minimum loan value.

Unlike Morpho Blue, every Moolah contract is **upgradeable**: an ERC-1967 proxy (130–170 B) with a UUPS implementation. `_authorizeUpgrade` needs `DEFAULT_ADMIN_ROLE`. On BNB Chain the sole `DEFAULT_ADMIN_ROLE` holder is the 1-day TimelockController `0x07d274a68393e8b8a2ccf19a2ce4ba3518735253`. On Ethereum it is the "Admin TimeLock" `0xa18ae79AEDA3e711E0CD64cfe1Cd06402d400D61` (1-day delay).

Lista Lending lives on **BNB Chain and Ethereum only**. It is absent on Base, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc (`eth_getCode` = `0x` at both Moolah addresses).

---

## 0. Contract families

| Component | Role | Emits |
|-----------|------|-------|
| **Moolah** | Singleton per chain. Holds every market, all loan and collateral balances. Flash loans. | Morpho-Blue-style market events (§1.1) |
| **MoolahVault** | ERC-4626 curated vault that supplies into Moolah markets (MetaMorpho fork). | ERC-4626 `Deposit`/`Withdraw` + MetaMorpho-style admin events (§1.2) |
| **MoolahVaultFactory** | Deploys MoolahVault proxies. | `CreateMoolahVault` |
| **MarketFactory** | Creates common, broker (fixed-term) and V3-LP markets in one call. | `CommonMarketDeployed`, `BrokerMarketDeployed` |
| **InterestRateModel / FixedRateIrm** | Adaptive-curve IRM (Morpho fork) and a fixed-rate IRM. | `BorrowRateUpdate` |
| **Providers** (`SlisBNBProvider`, `BNBProvider`, `SmartProvider`, `ETHProvider`, `V3Provider`) | Wrap native BNB/ETH, LP tokens and slisBNB for Moolah. Act as `caller` in Moolah events. | own `Deposit`/`SupplyCollateral` events (§1.5) |
| **LendingBroker** | One per broker market. Fixed-term and dynamic loans on top of a Moolah market. | `FixedLoanPositionCreated`, `RepaidFixedLoanPosition`, … (§1.3) |
| **Liquidator / PublicLiquidator / BrokerLiquidator / V3Liquidator / LiquidationVault** | Liquidation bots and the public liquidation entry point. | §1.4 |
| **Smart Lending StableSwap** (`StableSwapFactory`, `StableSwapPool`, `StableSwapLP`, `StableSwapLPCollateral`) | Curve-style 2-coin pools whose LP is lending collateral. | §1.6 |
| **Credit Loans** (`CreditBroker`, `CreditToken`) | Credit-limit loans against a non-transferable credit token. | §1.3 |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Moolah (singleton) — **same topic0 as Morpho Blue**

| topic0 | Event |
|--------|-------|
| `0xac4b2400f169220b0c0afdde7a0b32e775ba727ea1cb30b35f935cdaab8683ac` | `CreateMarket(bytes32 indexed id, MarketParams marketParams)` — `MarketParams=(address loanToken,address collateralToken,address oracle,address irm,uint256 lltv)` |
| `0xedf8870433c83823eb071d3df1caa8d008f12f6440918c20d75a3602cda30fe0` | `Supply(bytes32 indexed id, address indexed caller, address indexed onBehalf, uint256 assets, uint256 shares)` |
| `0xa56fc0ad5702ec05ce63666221f796fb62437c32db1aa1aa075fc6484cf58fbf` | `Withdraw(bytes32 indexed id, address caller, address indexed onBehalf, address indexed receiver, uint256 assets, uint256 shares)` |
| `0x570954540bed6b1304a87dfe815a5eda4a648f7097a16240dcd85c9b5fd42a43` | `Borrow(bytes32 indexed id, address caller, address indexed onBehalf, address indexed receiver, uint256 assets, uint256 shares)` |
| `0x52acb05cebbd3cd39715469f22afbf5a17496295ef3bc9bb5944056c63ccaa09` | `Repay(bytes32 indexed id, address indexed caller, address indexed onBehalf, uint256 assets, uint256 shares)` |
| `0xa3b9472a1399e17e123f3c2e6586c23e504184d504de59cdaa2b375e880c6184` | `SupplyCollateral(bytes32 indexed id, address indexed caller, address indexed onBehalf, uint256 assets)` |
| `0xe80ebd7cc9223d7382aab2e0d1d6155c65651f83d53c8b9b06901d167e321142` | `WithdrawCollateral(bytes32 indexed id, address caller, address indexed onBehalf, address indexed receiver, uint256 assets)` |
| `0xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41` | `Liquidate(bytes32 indexed id, address indexed caller, address indexed borrower, uint256 repaidAssets, uint256 repaidShares, uint256 seizedAssets, uint256 badDebtAssets, uint256 badDebtShares)` |
| `0xc76f1b4fe4396ac07a9fa55a415d4ca430e72651d37d3401f3bed7cb13fc4f12` | `FlashLoan(address indexed caller, address indexed token, uint256 assets)` — very high volume (~4,000 logs per 40k BSC blocks) |
| `0x9d9bd501d0657d7dfe415f779a620a62b78bc508ddc0891fbbd8b7ac0f8fce87` | `AccrueInterest(bytes32 indexed id, uint256 prevBorrowRate, uint256 interest, uint256 feeShares)` |
| `0xd5e969f01efe921d3f766bdebad25f0a05e3f237311f56482bf132d0326309c0` | `SetAuthorization(address indexed caller, address indexed authorizer, address indexed authorized, bool newIsAuthorized)` |
| `0xa58af1a0c70dba0c7aa60d1a1a147ebd61000d1690a968828ac718bca927f2c7` | `IncrementNonce(address indexed caller, address indexed authorizer, uint256 usedNonce)` |
| `0x139d6f58e9a127229667c8e3b36e88890a66cfc8ab1024ddc513e189e125b75b` | `SetFee(bytes32 indexed id, uint256 newFee)` |
| `0x2e979f80fe4d43055c584cf4a8467c55875ea36728fc37176c05acd784eb7a73` | `SetFeeRecipient(address indexed newFeeRecipient)` |
| `0x590e04cdebeccba40f566186b9746ad295a4cd358ea4fefaaea6ce79630d96c0` | `EnableIrm(address indexed irm)` |
| `0x297b80e7a896fad470c630f6575072d609bde997260ff3db851939405ec29139` | `EnableLltv(uint256 lltv)` |

Moolah-only events (no Morpho equivalent):

| topic0 | Event |
|--------|-------|
| `0x940f83c8b6b893567b5c9801752a42eb34c837bd16bad7d8c8346755dbb66a37` | `SetMarketBroker(bytes32 indexed id, address indexed broker, bool isAddition)` — market becomes broker-only |
| `0x618a463b3fb7f87438225fc638bb7c845a91f0d5acb6dcdf130ab42602a9cd3a` | `AddProvider(bytes32 id, address token, address provider)` (no indexed args) |
| `0x947f6c8867611e8a0d1b077012313862254b705d036b946b69ea602ebea3ed52` | `RemoveProvider(bytes32 id, address token, address provider)` |
| `0x8c16c1b380f1ee4f48cffce541cb2a31322e35491b5c18fbb4e01e1c048c9d4f` | `AddLiquidationWhitelist(bytes32 indexed id, address indexed account)` |
| `0x7da4876a6261512daeda3787842e1c79aa5a4a08d24885232df66de269b2ba9b` | `RemoveLiquidationWhitelist(bytes32 indexed id, address indexed account)` |
| `0x502fdcc5a5194ac94b5d7933962827d32baa2cb041816c5af824b2b378434d27` | `AddWhiteList(bytes32 indexed id, address indexed account)` — supply/borrow whitelist |
| `0x9ac1cf1e7272f8cd1a9556f6091b6d4bb0d8a8c08503ffb93474d468fae9a755` | `SetVaultBlacklist(address indexed account, bool isBlacklisted)` |
| `0xbf952d6d04f8e2574f1ec8a6d04da2a270d0e9fd3735bb7dcdb25472153b1ae8` | `SetFlashLoanTokenBlacklist(address indexed token, bool isBlacklisted)` |
| `0xac8f76827181d17440c15c03795bb054795ef387844bbdfec8bdf227e10bd792` | `SetMinLoanValue(uint256 minLoan)` |
| `0x0e32e30bf106776f9d968623763cd13174ee9fce430d6f2a63dc20d1aaaba160` | `SetDefaultMarketFee(uint256 fee)` |

Moolah has **no** `SetOwner` event. Access is role-based (OpenZeppelin `RoleGranted`/`RoleRevoked`). `RemoveWhiteList(bytes32,address)` (`0x00611819…`) is declared in source but is absent from the live BSC implementation bytecode.

### 1.2 MoolahVault (instance) and MoolahVaultFactory

| topic0 | Event |
|--------|-------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` — ERC-4626 |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` — ERC-4626 |
| `0xf66f28b40975dbb933913542c7e6a0f50a1d0f20aa74ea6e0efe65ab616323ec` | `AccrueInterest(uint256 newTotalAssets, uint256 feeShares)` — 2-field, same as MetaMorpho |
| `0x15c027cc4fd826d986cad358803439f7326d3aa4ed969ff90dbee4bc150f68e9` | `UpdateLastTotalAssets(uint256 updatedTotalAssets)` |
| `0x89bf199df65bf65155e3e0a8abc4ad4a1be606220c8295840dba2ab5656c1f6d` | `ReallocateSupply(address indexed caller, bytes32 indexed id, uint256 suppliedAssets, uint256 suppliedShares)` — emitted from the linked `MoolahVaultLib` |
| `0xdd8bf5226dff861316e0fa7863fdb7dc7b87c614eb29a135f524eb79d5a1189a` | `ReallocateWithdraw(address indexed caller, bytes32 indexed id, uint256 withdrawnAssets, uint256 withdrawnShares)` — linked library |
| `0xe86b6d3313d3098f4c5f689c935de8fde876a597c185def2cedab85efedac686` | `SetCap(address indexed caller, bytes32 indexed id, uint256 cap)` |
| `0x6ce31538fc7fba95714ddc8a275a09252b4b1fb8f33d2550aa58a5f62ad934de` | `SetSupplyQueue(address indexed caller, bytes32[] newSupplyQueue)` |
| `0xe0c2db6b54586be6d7d49943139fccf0dd315ba63e55364a76c73cd8fdba724d` | `SetWithdrawQueue(address indexed caller, bytes32[] newWithdrawQueue)` |
| `0x01fe2943baee27f47add82886c2200f910c749c461c9b63c5fe83901a53bdb49` | `SetFee(address indexed caller, uint256 newFee)` |
| `0x2ae72b44f59d038340fca5739135a1d51fc5ab720bb02d983e4c5ff4119ca7b8` | `Skim(address indexed caller, address indexed token, uint256 amount)` |
| `0xee331e94a757d017642c44fc43a795e9a4401226d4a67602a96ee1db3da6b573` | `InitProvider(address indexed provider)` — Lista-only |
| `0xfecc36774198faf97c38a18c8bdcda770e34f4bc5441ad5894695857889245b6` | `SetLockBuffer(address indexed lockBuffer)` — Lista-only |
| `0xfd813a33bba8e3b5e540229e266ccd9c045fd61bcb50873786f1bede0ddad367` | `SetWhiteList(address indexed account, bool enabled)` — linked library |
| `0x22e5b540ae5cb8ec1114db7253f1812c4eb0d3443b8ad013e0e495297e4803c1` | **Factory:** `CreateMoolahVault(address indexed moolahVault, address implementation, address managerTimeLock, address curatorTimeLock, uint256 timeLockDelay, address indexed caller, address manager, address curator, address guardian, address indexed asset, string name, string symbol)` |

The MetaMorpho timelock/guardian/curator events (`SubmitCap`, `SubmitTimelock`, `SetGuardian`, `SetCurator`, `SetIsAllocator`, …) are declared in `EventsLib` but are **not emitted**: Lista replaced the timelock flow with roles (`MANAGER`, `CURATOR`, `ALLOCATOR`, `BOT`).

### 1.3 LendingBroker (one per broker market) and CreditBroker

| topic0 | Event |
|--------|-------|
| `0x1e0698020a99de4d142f51db1c05c57cef303cff88a7421eb43226798f1f4f4d` | `FixedLoanPositionCreated(address indexed user, uint256 posId, uint256 principal, uint256 start, uint256 end, uint256 apr, uint256 termId)` — Lending + Credit broker |
| `0x6e104f7953d981e935d5abe2353189aeca848bfb9f9e0ef9cffa1ea60e79d0fe` | `DynamicLoanPositionBorrowed(address indexed user, uint256 borrowed, uint256 principalLeft)` |
| `0x05b3220325c16d99b8807c85544cec911feb69ea7dc53755c8cd9d69e0bb84f1` | `DynamicLoanPositionRepaid(address indexed user, uint256 repaid, uint256 principalLeft)` |
| `0x5254e54ae4b52d4f67430f479c097b7152f5756a97ef9c0d2bb04894aac902fe` | `RepaidFixedLoanPosition(address indexed user, uint256 posId, uint256 principal, uint256 start, uint256 end, uint256 apr, uint256 principalRepaid, uint256 repayPrincipal, uint256 repayInterest, uint256 repayPenalty, uint256 totalInterestRepaid)` — LendingBroker (11 fields) |
| `0x9b383b7ebe07b0838262fdad020131bfe87b7e8fab8b1e7ed00b61d826b23678` | `RepaidFixedLoanPosition(…11 fields…, bool isBadDebt)` — **CreditBroker** (12 fields, different topic0) |
| `0x377958838441f204b9300e1a32c4333c7cfbf8b70880c9628cae282bbcd46494` | `FixedPositionRefinanced(address indexed user, uint256 posId, uint256 principal, uint256 start, uint256 end, uint256 apr)` |
| `0xffdfa305a14d27117a01ca3334c80c59341de211ff95f47c87f2386e18668825` | `FixedLoanPositionRemoved(address indexed user, uint256 posId)` |
| `0xac4323582e73844d4f5173e00af9f5d3173d4fdc7bc6a2e2d5c377d37ccdec3c` | `AllPositionsRepaid(address indexed user, uint256 totalRepaid)` |
| `0x09c223cfcd8c93e245f558f5f8de755fc0930fd9bc257441155ef5d54a170e0f` | `Liquidated(address indexed user, uint256 principalCleared, uint256 interestCleared)` — broker side of a liquidation |
| `0x19587c1b2bf3bc03905b09851d1bf27d9f95a8f2f668e14f23fc720c857e3490` | `FixedTermAndRateUpdated(uint256 termId, uint256 duration, uint256 apr)` — **noisy** (~340 logs per 49k BSC blocks across 10 brokers) |
| `0x91fb1e7b57920506b01254360642cf7db9f5e91cf748241ca0b22f0bd691b717` | `BorrowPaused(bool paused)` |
| `0x457e4fe0c9f161a0c6f3bfb8d7809a4ac19f6291bd81b03b86b0d00f9af3717b` | `EmergencyWithdrawn(address indexed sender, address indexed token, uint256 amount)` |
| `0x3f32684a32a11dabdbb8c0177de80aa3ae36a004d75210335b49e544e48cd0aa` | `OracleSet(address indexed oracle)` |
| `0xeda4d94e94cd5b0bc0e9469c61e15627536747401016481ff20ca9d6c51d21ec` | `PositionLiquidate(address indexed user, uint256 posId)` — CreditBroker |
| `0xef1d9f8c02fd60e6d29e17b4a8dc8967c944e0d4d5baced43bbf8e3d03d713c9` | `RepayInterestWithLista(address indexed user, uint256 posId, uint256 interestAmount, uint256 listaAmount, uint256 listaPrice)` — CreditBroker |

**MarketFactory** (market discovery for broker / V3 markets):

| topic0 | Event |
|--------|-------|
| `0xc2bb1f6e1878a45dcfff7d41e675d28aaf25b048c7e7786cc64ca1d9ba645a74` | `CommonMarketDeployed(MarketParams marketParams, bytes32 marketId)` |
| `0x177ae1918ff4739db8b4e0be87970a23ea64fe717820f56d30f83d324acd472e` | `BrokerMarketDeployed(FixedTermMarketParams fixedTermMarketParams, bytes32 marketId, address broker)` — `FixedTermMarketParams=(address,address,address,address,uint256,uint256,uint256)` |
| `0xf243403d988a434b290f0feea27ed79036cd1550822d684ccd75ca245442fbf7` | `V3ProviderRegistered(address indexed share, address indexed oracle)` |

**BrokerInterestRelayer:** `InterestAccumulated(address indexed broker, uint256 amount)` `0xc2c200990ee1c68055e059ad867ef209e2bb106d48a7d934005e8d01cd307241` · `SuppliedToMoolahVault(uint256 amount)` `0xed57f13319fad87ae3cc673099aa0a179fd638813f36e58552ace152c10b6cea`.

### 1.4 Liquidators, LiquidationVault, IRM

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xc825af5ed71c3d4e8384fad1414973f60116d9c9ff5a485f91bb499802bd8e27` | `Liquidated(bytes32 indexed id, address indexed borrower, uint256 seizedAssets, uint256 repaidAssets, uint256 repaidShares, address liquidator)` | PublicLiquidator |
| `0xe1127b61fe62d1651bece292ed170fda3a193b633d22786a854d43b15a8378f2` | `SmartLiquidation(bytes32 indexed id, address indexed lpToken, address indexed collateralToken, uint256 lpAmount, uint256 minToken0Amt, uint256 minToken1Amt, uint256 amount0, uint256 amount1)` | Liquidator, BrokerLiquidator |
| `0x03ece4470b1488beb686e902d96b7e7db6975f7896080ad9e2448cd7d28bae60` | `V3Liquidation(bytes32 indexed id, address indexed v3Provider, address indexed borrower, uint256 seized, uint256 repaid, uint256 amount0, uint256 amount1)` | V3Liquidator |
| `0x4074a3aaedf75c9437a98701d04ed60ee9843b9506bf0b3396c4198d26ba288a` | `SellToken(address pair, address spender, address tokenIn, address tokenOut, uint256 amountIn, uint256 actualAmountOut)` — V3Liquidator indexes `pair`, so its logs carry one more topic | Liquidator, V3Liquidator, LiquidationVault |
| `0x3777ada1f29c57dc9f52ec130201cacc736716ed28016fa1407688f01da206cb` | `SellToken(address pair, address tokenIn, address tokenOut, uint256 amountIn, uint256 actualAmountOut)` (5 args) | BrokerLiquidator |
| `0x957684c1ab369b81d05dc346d5c1c6360549879e8c4d4f4b8732d40df6ba4450` | `DailyLossAccrued(uint256 indexed day, uint256 loss, uint256 accum)` | LiquidationVault |
| `0x7120161a7b3d31251e01294ab351ef15a41b91659a36032e4641bb89b121e321` | `BorrowRateUpdate(bytes32 indexed id, uint256 avgBorrowRate, uint256 rateAtTarget)` — same as Morpho AdaptiveCurveIRM | InterestRateModel, FixedRateIrm |
| `0x994fbfe5ac32e79b5f988fd12f0af0ada46a40731a02dc30c96972a69fb31528` | `SetBorrowRate(bytes32 indexed id, int256 newBorrowRate)` | FixedRateIrm |

Whitelist admin events on the liquidators: `MarketWhitelistChanged(bytes32,bool)` `0x846d7655…dbe0`, `PairWhitelistChanged(address,bool)` `0xf84396a1…49a3`, `TokenWhitelistChanged(address,bool)` `0x6b2d0400…22a2`.

### 1.5 Providers

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15` | `Deposit(address indexed account, uint256 amount, uint256 lPAmount)` | SlisBNBProvider (Moolah) — also the CDP slisBNB provider |
| `0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65` | `Withdrawal(address indexed owner, uint256 amount)` — **same topic0 as WETH/WBNB `Withdrawal`** | SlisBNBProvider |
| `0x16fe95424cfa92af8f42d2e965427975753fb1f250b688a721fb4013a2923624` | `UserLpRebalanced(address account, uint256 userLp, uint256 reservedLp)` — slisBNBx balance resync | SlisBNBProvider |
| `0xbe3e9417871c0c377818df8bfe2480c49164c463fb3820cb48e948a0cac5f5dd` | `SupplyCollateral(address indexed onBehalf, address indexed collateralToken, uint256 collateralAmount, uint256 amount0, uint256 amount1)` | SmartProvider |
| `0x06e135d1dc5bc3fd80908d171bdf9307bc88ce2f0807f6177e37d492439246c8` | `WithdrawCollateral(address indexed collateralToken, address indexed onBehalf, uint256 collateralAmount, uint256 token0Amount, uint256 token1Amount, address receiver)` | SmartProvider |
| `0x52713c14add9eb3db583d1cc31e0fc708256e584907f72a8a075802ddb9e2faf` | `Deposit(address indexed onBehalf, uint256 amount0Used, uint256 amount1Used, uint256 shares, bytes32 indexed marketId)` | V3Provider |

### 1.6 Smart Lending StableSwap (pool / factory)

| topic0 | Event |
|--------|-------|
| `0x143f1f8e861fbdeddd5b46e844b7d3ac7b86a122f36e8c463859ee6811b1f29c` | `TokenExchange(address indexed buyer, uint256 sold_id, uint256 tokens_sold, uint256 bought_id, uint256 tokens_bought, uint256 swap_fee, uint256 admin_fee)` — 7 fields, **not** the Curve 5-field topic |
| `0xd65676560b492a7fad9eaab0b89a1316676d38ed89a6dfc48552da598d9828a3` | `AddLiquidity(address indexed provider, uint256[2] token_amounts, uint256[2] fees, uint256 invariant, uint256 token_supply, uint256 admin_fee_rate)` |
| `0x7c363854ccf79623411f8995b362bce5eddff18c927edc6f5dbbb5e05819a82c` | `RemoveLiquidity(address indexed provider, uint256[2] token_amounts, uint256[2] fees, uint256 token_supply)` |
| `0xe200e24d4a4c7cd367dd9befe394dc8a14e6d58c88ff5e2f512d65a9e0aa9c5c` | `RemoveLiquidityOne(address indexed provider, uint256 index, uint256 token_amount, uint256 coin_amount, uint256 token_supply, uint256 admin_fee_rate)` |
| `0x92c9505c4878513c6de017eda85a92a69e71baf1dce8f1c72fda89fd67a4df83` | `RemoveLiquidityImbalance(address indexed provider, uint256[2] token_amounts, uint256[2] fees, uint256 invariant, uint256 token_supply, uint256 admin_fee_rate)` |
| `0xa2b71ec6df949300b59aab36b55e189697b750119dd349fcfa8c0f779e83c254` | `RampA(uint256 old_A, uint256 new_A, uint256 initial_time, uint256 future_time)` |
| `0xc3977c9522c218453912bcab15964a7788968fbf3fe4d4e2965252c9f07055de` | `ChangeOracle(address newOracle)` |
| `0x02583535965f7dd02141472f8e87a2e147f8bd330781dfaf90081a3089e921e2` | **Factory:** `NewStableSwapPair(address indexed swapContract, address tokenA, address tokenB, address lp)` |

---

## 2. Function signatures (chain-agnostic)

### 2.1 Moolah — **same selectors as Morpho Blue** for the core set

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8c1358a2` | `createMarket((address,address,address,address,uint256))` | Role-gated (Morpho Blue: permissionless). |
| `0xa99aad89` | `supply((address,address,address,address,uint256),uint256,uint256,address,bytes)` | Whitelist check on `onBehalf` if set. |
| `0x5c2bea49` | `withdraw((address,address,address,address,uint256),uint256,uint256,address,address)` | |
| `0x50d8cd4b` | `borrow((address,address,address,address,uint256),uint256,uint256,address,address)` | Broker markets: only the broker can call; `receiver` must be the broker. |
| `0x20b76e81` | `repay((address,address,address,address,uint256),uint256,uint256,address,bytes)` | |
| `0x238d6579` | `supplyCollateral((address,address,address,address,uint256),uint256,address,bytes)` | Provider markets: only the provider can call. |
| `0x8720316d` | `withdrawCollateral((address,address,address,address,uint256),uint256,address,address)` | |
| `0xd8eabcb8` | `liquidate((address,address,address,address,uint256),address,uint256,uint256,bytes)` | Liquidation-whitelist check per market. |
| `0xab953674` | `liquidateBrokerPosition((address,address,address,address,uint256),address,uint256)` | Moolah-only. Broker-market liquidation. |
| `0xe0232b42` | `flashLoan(address,uint256,bytes)` | |
| `0x151c1ade` | `accrueInterest((address,address,address,address,uint256))` | |
| `0xeecea000` | `setAuthorization(address,bool)` | |
| `0x8069218f` | `setAuthorizationWithSig((address,address,bool,uint256,uint256),(uint8,bytes32,bytes32))` | |
| `0x4d7dd360` | `setMarketBroker(bytes32,address,bool)` | Manager. |
| `0x26fce440` | `setProvider(bytes32,address,bool)` | Manager. |
| `0xfaf50e65` | `setWhiteList(bytes32,address,bool)` | Manager. |
| `0x3a746bec` | `batchToggleLiquidationWhitelist(bytes32[],address[][],bool)` | Manager. |
| `0x2b4f013c` | `setFee((address,address,address,address,uint256),uint256)` | |
| `0x45b21a55` | `setMinLoanValue(uint256)` | |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | Pauser role. |
| `0x5c60e39a` | `market(bytes32)` | view: `(totalSupplyAssets, totalSupplyShares, totalBorrowAssets, totalBorrowShares, lastUpdate, fee)` |
| `0x93c52062` | `position(bytes32,address)` | view: `(supplyShares, borrowShares, collateral)` |
| `0x2c3c9157` | `idToMarketParams(bytes32)` | view |
| `0x2c2c904f` | `isHealthy((address,address,address,address,uint256),bytes32,address)` | view |

### 2.2 MoolahVault / factory / BNBProvider

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6e553f65` | `deposit(uint256,address)` | ERC-4626. |
| `0x94bf804d` | `mint(uint256,address)` | ERC-4626. |
| `0xb460af94` | `withdraw(uint256,address,address)` | ERC-4626. |
| `0xba087652` | `redeem(uint256,address,address)` | ERC-4626. |
| `0x4fb15b3f` / `0x5c0bfa88` | `withdrawFor(uint256,address,address)` / `redeemFor(uint256,address,address)` | Provider-only (native BNB path). |
| `0x7299aa31` | `reallocate(((address,address,address,address,uint256),uint256)[])` | Allocator/bot. |
| `0xd3ac290c` | `setCap((address,address,address,address,uint256),uint256)` | Curator. |
| `0x2acc56f9` / `0x41b67833` | `setSupplyQueue(bytes32[])` / `updateWithdrawQueue(uint256[])` | Allocator. |
| `0x72147ee8` | `createMoolahVault(address,address,address,uint256,address,string,string)` | Factory. Emits `CreateMoolahVault`. |
| `0xf340fa01` | `deposit(address)` | BNBProvider: native BNB → WBNB vault. |
| `0xf9609f08` | `deposit(address,address)` | BNBProvider `(vault, receiver)`. |
| `0xdfcd412e` | `withdraw(address,uint256,address,address)` | BNBProvider. |
| `0xac69d359` | `supplyCollateral((address,address,address,address,uint256),address,bytes)` | BNBProvider (payable). |
| `0x833947fd` | `reallocateTo(address,((address,address,address,address,uint256),uint128)[],(address,address,address,address,uint256))` | VaultAllocator (Morpho PublicAllocator fork). |

### 2.3 LendingBroker / CreditBroker

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc5ebeaec` | `borrow(uint256)` | Dynamic-rate borrow. |
| `0x0ecbcdab` | `borrow(uint256,uint256)` | Fixed-term borrow `(amount, termId)`. |
| `0x3d5d4a9e` | `borrow(uint256,uint256,address,address)` | Borrow on behalf (authorised). |
| `0xacb70815` | `repay(uint256,address)` | Dynamic repay. |
| `0xb1e8f8ef` | `repay(uint256,uint256,address)` | Fixed repay `(amount, posId, onBehalf)`. |
| `0x7c27383b` | `repayAll(address)` | Emits `AllPositionsRepaid`. |
| `0x38a63b78` | `convertDynamicToFixed(uint256,uint256)` | |
| `0x6437cd04` | `refinanceMaturedFixedPositions(address,uint256[])` | Bot. |
| `0x29fda0ba` | `updateFixedTermAndRate((uint256,uint256,uint256),bool)` | Manager/bot. Emits `FixedTermAndRateUpdated`. |
| `0x869f8a1b` | `onMoolahLiquidate(uint256,bytes)` | Moolah callback. |
| `0x85e9df46` | `supplyAndBorrow(uint256,uint256,uint256,uint256,bytes32[])` | CreditBroker (Merkle-proof credit). |
| `0xddd326c9` | `repayInterestWithLista(uint256,uint256,uint256,address)` | CreditBroker. |
| `0xbcbaf487` | `liquidate(address,uint256)` | CreditBroker. |

### 2.4 Liquidators, IRM, StableSwap

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8539ca00` | `liquidate(bytes32,address,uint256,uint256)` | Liquidator / PublicLiquidator / BrokerLiquidator / V3Liquidator. |
| `0x8d9dcff4` | `flashLiquidate(bytes32,address,uint256,address,bytes)` | Bot-only on Liquidator. |
| `0x83276667` | `liquidateWithCollTransferOpt(bytes32,address,uint256,uint256,bool)` | PublicLiquidator. |
| `0x5efe916b` | `liquidateSmartCollateral(bytes32,address,address,uint256,uint256,bytes)` | |
| `0x43ac0360` / `0xeb2f51a6` | `sellToken(address,address,address,address,uint256,uint256,bytes)` / `sellToken(address,address,address,uint256,uint256,bytes)` | Bot sells seized collateral. |
| `0x72337a54` | `provideFund(address,uint256)` | LiquidationVault. |
| `0x2329790a` / `0x7f22b176` | `updateRateCap(bytes32,uint256)` / `updateRateFloor(bytes32,uint256)` | InterestRateModel (Lista-only). |
| `0x98364356` | `setBorrowRate(bytes32,int256)` | FixedRateIrm. |
| `0x5b41b908` | `exchange(uint256,uint256,uint256,uint256)` | StableSwapPool swap. |
| `0x0b4c7e4d` | `add_liquidity(uint256[2],uint256)` | |
| `0x5b36389c` | `remove_liquidity(uint256,uint256[2])` | |
| `0xf1dc3cc9` | `remove_liquidity_one_coin(uint256,uint256,uint256)` | |
| `0x61fd391e` | `supplyDexLp((address,address,address,address,uint256),address,uint256)` | SmartProvider. |
| `0x2f1a11e1` | `supplyCollateral((address,address,address,address,uint256),address,uint256,uint256,uint256)` | SmartProvider (tokens → LP → collateral). |
| `0xfc74c3b0` | `createSwapPair(address,address,string,string,uint256,uint256,uint256,address,address,address,address)` | StableSwapFactory. |

---

## 3. Addresses — BNB Smart Chain (chain ID 56)

All verified via `eth_getCode` on `https://bsc-rpc.publicnode.com` on 2026-10-30. Every row is an ERC-1967 proxy unless marked.

| Role | Address | One-liner |
|------|---------|-----------|
| **Moolah** | `0x8F73b65B4caAf64FBA2aF91cC5D4a2A1318E5D8C` | Lending singleton. Impl `0x9321587ea0dc8247f8f03e8696c047b2713bb79a`. |
| InterestRateModel | `0xFe7dAe87Ebb11a7BEB9F534BB23267992d9cDe7c` | Adaptive IRM. |
| InterestRateModel (Alpha) | `0x5F9f9173B405C6CEAfa7f98d09e4B8447e9797E6` | IRM for "alpha" markets. |
| MarketFactory | `0xce26859127d236a61f168d2d0905f77d7E286Ab2` | Market + broker deployer. |
| MoolahVaultFactory | `0x2a0Cb6401FD3c6196750dc6b46702040761D9671` | Vault deployer. |
| MoolahVaultManager | `0x5021319C1B8245e0680F19b7aA84a0F0F3d91AA9` | Vault admin helper. |
| VaultAllocator | `0x9ECF66f016FCaA853FdA24d223bdb4276E5b524a` | Public reallocation (PublicAllocator fork). |
| OracleAdaptor | `0x21650E416dC6C89486B2E654c86cC2c36c597b58` | Oracle used by markets. |
| Liquidator | `0x6a87C15598929B2db22cF68a9a0dDE5Bf297a59a` | Lista bot liquidator. |
| PublicLiquidator | `0x882475d622c687b079f149B69a15683FCbeCC6D9` | Public liquidation entry. |
| BrokerLiquidator | `0x3AA647a1e902833b61E503DbBFbc58992daa4868` | Broker-market liquidator. |
| V3Liquidator | `0x670004c8c63ab6A4F38e29b6876e8fE2aCf9FD71` | V3-LP collateral liquidator. |
| LiquidationVault | `0xEe3aa1AF4Ee231f2e1277A48fc4A2f29A3D7C028` | Funds liquidations. |
| PositionManager | `0x8eBFa9e687aF71EC2e87A0380F73b9f57FDf3ec0` | Position helper. |
| LendingFeeRecipient | `0x2E2Eed557FAb1d2E11fEA1E1a23FF8f1b23551f3` | Fee sink. |
| LendingRevenueDistributor | `0xea55952a51ddd771d6eBc45Bd0B512276dd0b866` | Revenue split. |
| RevenueCollector | `0x86E09296aeDA129D3b0b4c134B3202b84Cd8945C` | DEX fee and liquidation profit. |
| Rate Calculator (brokers) | `0xF81A3067ACF683B7f2f40a22bCF17c8310be2330` | Broker rate source. |
| Lending TimeLock / TimeLockNew | `0x2e2807F88C381Cb0CC55c808a751fC1E3fcCbb85` / `0x5E3358352153c864E2b1F03c620f80d66Bd30752` | Plain TimelockControllers (1-day delay). Not the `DEFAULT_ADMIN_ROLE` holder. |
| **Upgrade admin** | `0x07d274a68393e8b8a2ccf19a2ce4ba3518735253` | TimelockController (1 day). Sole `DEFAULT_ADMIN_ROLE` on Moolah, vaults, factory, brokers. Not in the docs list. |

**Vaults** (impl `0x713a7e23cff5016a479b079e48b575818a3fcc95` shared):

| Vault | Address |
|-------|---------|
| MoolahVault (WBNB) | `0x57134a64B7cD9F9eb72F8255A671F5Bf2fe3E2d0` |
| MoolahVault (USD1) | `0xfa27f172e0b6ebcEF9c51ABf817E2cb142FbE627` |
| MoolahVault (U) | `0x9A17Fd5Cb8EFc25d11567e713aE795A89775a759` |
| MoolahVault (BTCB) | `0xE46b8E65006e6450bdd8cb7D3274AB4F76f4C705` |
| MoolahVault (USDT) | `0x6d6783C146F2B0B2774C1725297f1845dc502525` |
| LisUSD Vault | `0xE03D86e5Baa3509AC4A059A41737bAa8169B6529` |
| MoolahVault (Credit Vault) | `0x4E82Fa869F8D05c8F94900d4652Fdb82f3C7A004` |

About 20 more curated vaults (MEV, Re7, Solv, Puffer, Aster, XAUt, …) are listed on the docs page. Discover all of them with `CreateMoolahVault` on the factory.

**Providers:** SlisBNBProvider `0x33f7A980a246f9B8FEA2254E3065576E127D4D5f` · SlisBNBxMinter `0x2959c423bfe5Cc6E41516599D982A29C0773F11a` · BNBProvider (Lista WBNB vault) `0x367384C54756a25340c63057D87eA22d47Fd5701` · BNBProvider (MEV WBNB) `0x501bE17CcA1d8a009753Da271D6714C18c1A35c9` · BNBProvider (Loop WBNB) `0x7901Cb0db0db005c44ee5957Fa22D478258ef64E`.

**Brokers:** 27 `LendingBroker` proxies (impl `0xf1db84c5788fb2174d61e1c98f962f56c224b128`), one per market, for example WBNB/lisUSD `0x6BAF9648cffB7C9c4cB7275000a27b9a7dBD59Bc`, BTCB/U `0xFEb7D3Deb6a4CEE8f5da4F618098Ac943440Ff69`, slisBNB/U `0xDf05774Cd68cE1FBaE01be3181524c904f91d628`, USDe/U `0x52ee1F685ef41E8D1158E2508dC46561Ca839864`. Discover them with `BrokerMarketDeployed` (MarketFactory) or `SetMarketBroker` (Moolah).

**Smart Lending:** StableSwapFactory `0xDE9c8E1536989d8c3817afDabC37C0fb44cB49b4` · StableSwapPoolInfo `0x73D2623C8497421B55234e6B25fB744625557a1A` · slisBNB/BNB pool `0x3DcEA6AFBA8af84b25F1f8947058AF1ac4c06131` (SmartProvider `0xC3be83DE4b19aFC4F6021Ea5011B75a3542024dE`) · U/USDT pool `0x6783a05B98Cb83c3f456197A035b9C17a9d57388` · USDC/USDT pool `0xF5448fC2bEB9324900d08225fE4530bA3bBf654f` · USD1/USDT pool `0x723ccd2FB5897673Ad108706578886baA15d7242` · lisUSD/USDT pool `0x8df7891fb2Cb3e98C7AB3cfB4d9A59FbCC63c956`. Discover new pools with `NewStableSwapPair`.

**Credit:** CreditBroker `0x2A6704D56BDedF4c7564C9534D7fa8D8D204D578` · CreditToken `0x1f9831626CE85909794eEaA5C35BF34DB3eB52d8` · CreditBrokerInterestRelayer `0xBd94C4E931c1a15941B6273A952Af322891adC47`.

## 4. Addresses — Ethereum (chain ID 1)

All verified via `eth_getCode` on `https://ethereum-rpc.publicnode.com` on 2026-10-30. All are UUPS ERC-1967 proxies (130 B) unless marked.

| Role | Address | One-liner |
|------|---------|-----------|
| **Moolah** | `0xf820fB4680712CD7263a0D3D024D5b5aEA82Fd70` | Lending singleton. Impl `0xd7c983093065e0169e955c44ab8370110231d3cf`. |
| MoolahVault (USD1) | `0x1A9BeE2F5c85F6b4a0221fB1C733246AF5306Ae3` | |
| MoolahVault (USDT) | `0x28643FFD79256719D6AcbCF25Cb44576cAeBCf12` | |
| MoolahVault (USDC) | `0x9651Ae50a5763c6f9B883f9d50e8116281CFcab2` | |
| MoolahVault (WETH) | `0x2E3BbD03DbC6D890c8c7e06BE4e065c5c0EeE7e8` | |
| IRM | `0x8b7d334d243b74D63C4b963893267A0F5240F990` | |
| FixedRateIRM | `0x9A7cA2CfB886132B6024789163e770979E4222e1` | |
| Liquidator / PublicLiquidator | `0x5Bf5c3B5f5c29dBC647d2557Cc22B00ED29f301C` / `0x796302e041d1715a8b1f16Fd7d7CBA38bb031DE5` | |
| BrokerLiquidator | `0x0aEfEC58e6339c663E80306e38fFEBbAe0820C70` | |
| LiquidationVault | `0xC1D8F6072D8a987BCbB675dc4805E8A2dE604899` | |
| MoolahVaultFactory / MarketFactory | `0xa91D9E7343d7EEe8Ed2C8f55e9162827850A7F17` / `0xA2ff080D4c0b71B6c8796129DD4aCc0B09D7592c` | |
| ETHProvider | `0xFe34BF713F3C2499026cdFA5af43eb22AA2d1aDb` | Native ETH wrapper. |
| LendingBroker (wBETH/WETH, wstETH/WETH, sUSDS/USDT, sUSDS/USDC) | `0x2B7cb7Fe6C545e23cb96f2B8E7e5120fF9e16444`, `0x39acab377A7cA24c1BF4B2AE5294F57519d8719B`, `0x1961ef66C252cDCB09FaF464Ea1360Ca4bb4269C`, `0x0780b0E16C6d60798AFee808633f1E91665b403a` | Shared impl `0x63fa516949e12f194095562424c6e1d5e2f096f0`. |
| RateCalculator | `0xeA00cE2992656A0F1DeDf3bBF082A3c725477796` | |
| StableSwapFactory | `0xF6c9ffA64bD0aE8a068dd7b7d954c654A3E7F8a6` | Six Smart-Lending pools (ETH/wstETH `0x23072d031d5Af614395C8E58B7f7e91F003b331a`, USDT/USDC `0x35c9a4DaE1ff05788f24B5B32721D89340CBB636`, …). |
| ResilientOracle | `0xA64FE284EB8279B9b63946DD51813b0116099301` | OZ v5 Transparent proxy (1159 B). |
| LendingFeeRecipient / RevenueCollector | `0xd10a024602E042dcb9C19e21682c3b896c8B0d30` / `0x8a6e34A7860dD9C46770635fe3Da4073C56f8131` | |
| PositionManager | `0x6d9eD2A68c2759DA53A74D6a85Cd486737257A82` | |
| Admin TimeLock / Manager TimeLock | `0xa18ae79AEDA3e711E0CD64cfe1Cd06402d400D61` / `0x375fdA2Bf66f4CE85EAB29AB6407dCd4a4C428BA` | TimelockControllers (1 day). Admin TimeLock is `DEFAULT_ADMIN_ROLE` on Moolah. |

## 5. Cross-chain summary

| Chain (ID) | Moolah | Vaults | Brokers | Smart Lending | Credit |
|------------|--------|--------|---------|---------------|--------|
| BNB (56) | `0x8F73b6…5D8C` | ✓ (~27) | ✓ (27) | ✓ | ✓ |
| Ethereum (1) | `0xf820fB…Fd70` | ✓ (4) | ✓ (4) | ✓ | — |
| Base (8453) · Avalanche (43114) · Arbitrum (42161) · Optimism (10) · Polygon (137) · Robinhood (4663) · Arc (5042) | — | — | — | — | — |

The two Moolah addresses differ. There is no vanity or CREATE2 address.

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Moolah, MoolahVault, factories, brokers, liquidators, providers, StableSwap pools (both chains) | ERC-1967 proxy → UUPS impl | 130 B / 163 B / 170 B proxy; impl slot non-zero; admin slot `0x0` | `DEFAULT_ADMIN_ROLE` (BSC `0x07d274…5253`, ETH `0xa18ae7…0D61`) |
| ResilientOracle (ETH) | OZ v5 TransparentUpgradeableProxy | 1159 B; admin slot = per-proxy ProxyAdmin `0x4f8c1f1a85bc36165d4459f8df3b7cc172e778ab` | ProxyAdmin owner |
| Lending TimeLock, TimeLockNew, Admin/Manager TimeLock | not proxies | impl slot `0x0` | — |

Watch `Upgraded(address indexed implementation)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` on each proxy. Every BSC MoolahVault, the LisUSD Vault and the Credit Vault share impl `0x713a7e23…fcc95`. One upgrade of that impl pointer happens per vault, not once.

## 7. Detection invariants & gotchas

1. **Topic0 collision with Morpho Blue.** Moolah emits the same `Supply`/`Withdraw`/`Borrow`/`Repay`/`SupplyCollateral`/`WithdrawCollateral`/`Liquidate`/`FlashLoan`/`AccrueInterest`/`CreateMarket`/`SetAuthorization` topic0s as Morpho Blue. MoolahVault shares the MetaMorpho `AccrueInterest`/`SetCap`/`SetSupplyQueue`/`ReallocateSupply` topic0s. The VaultAllocator shares PublicAllocator topic0s. **Always filter by emitter.** On BNB, Moolah is `0x8F73b6…5D8C`; Morpho Blue is `0x01b0Bd…7a83a` (see [../morpho/v1.md](../morpho/v1.md)). On Ethereum, Moolah is `0xf820fB…Fd70`; Morpho Blue is `0xBBBBBbbB…EFFCb`.
2. **Selectors also collide with Morpho Blue.** `supply` `0xa99aad89`, `borrow` `0x50d8cd4b`, `liquidate` `0xd8eabcb8` and the rest are identical. Key on `to` address.
3. **Attribution.** The position owner is `onBehalf`. In provider markets (slisBNB, LP, native BNB) the `caller` is the provider contract. In broker markets `caller` = `receiver` = the LendingBroker; the real user is `onBehalf` in Moolah and `user` in the broker events.
4. **Broker loans have two event layers.** A fixed-term borrow emits Moolah `Borrow` and broker `FixedLoanPositionCreated` in the same transaction. Do not double-count.
5. **Two `RepaidFixedLoanPosition` topics.** LendingBroker uses `0x5254e54a…` (11 fields). CreditBroker uses `0x9b383b7e…` (adds `bool isBadDebt`).
6. **Library-emitted events.** `ReallocateSupply`/`ReallocateWithdraw`/`SetWhiteList` (vault) and `DynamicLoanPositionRepaid`/`RepaidFixedLoanPosition`/`AllPositionsRepaid` (broker) are emitted from linked libraries through `DELEGATECALL`. The log address is still the vault or broker. The topics are not in the implementation bytecode.
7. **Address literal reuse across chains.** Lista deploys from the same EOA on both chains, so one address can be two unrelated contracts. Example: `0xf820fB…Fd70` is Moolah on Ethereum but the VeListaRevenueDistributor implementation on BNB. `0x8b7d33…F990` is the IRM on Ethereum but a ClisBNBLaunchPoolDistributor on BNB. Several Ethereum implementation addresses equal BNB proxy addresses. Always key on `(chainId, address)`.
8. **Flash-loan noise.** Moolah `FlashLoan` dominates log volume on BNB. `FixedTermAndRateUpdated` is the noisiest broker event.
9. **StableSwap is not Curve.** `TokenExchange` has 7 fields (`0x143f1f8e…`), so the Curve topic `0x8b3e96f2…` does not match.

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_MOOLAH_CREATE_MARKET        = '\xac4b2400f169220b0c0afdde7a0b32e775ba727ea1cb30b35f935cdaab8683ac'
TOPIC_MOOLAH_SUPPLY               = '\xedf8870433c83823eb071d3df1caa8d008f12f6440918c20d75a3602cda30fe0'
TOPIC_MOOLAH_WITHDRAW             = '\xa56fc0ad5702ec05ce63666221f796fb62437c32db1aa1aa075fc6484cf58fbf'
TOPIC_MOOLAH_BORROW               = '\x570954540bed6b1304a87dfe815a5eda4a648f7097a16240dcd85c9b5fd42a43'
TOPIC_MOOLAH_REPAY                = '\x52acb05cebbd3cd39715469f22afbf5a17496295ef3bc9bb5944056c63ccaa09'
TOPIC_MOOLAH_SUPPLY_COLLATERAL    = '\xa3b9472a1399e17e123f3c2e6586c23e504184d504de59cdaa2b375e880c6184'
TOPIC_MOOLAH_WITHDRAW_COLLATERAL  = '\xe80ebd7cc9223d7382aab2e0d1d6155c65651f83d53c8b9b06901d167e321142'
TOPIC_MOOLAH_LIQUIDATE            = '\xa4946ede45d0c6f06a0f5ce92c9ad3b4751452d2fe0e25010783bcab57a67e41'
TOPIC_MOOLAH_FLASHLOAN            = '\xc76f1b4fe4396ac07a9fa55a415d4ca430e72651d37d3401f3bed7cb13fc4f12'
TOPIC_MOOLAH_ACCRUE_INTEREST      = '\x9d9bd501d0657d7dfe415f779a620a62b78bc508ddc0891fbbd8b7ac0f8fce87'
TOPIC_MOOLAH_SET_MARKET_BROKER    = '\x940f83c8b6b893567b5c9801752a42eb34c837bd16bad7d8c8346755dbb66a37'
TOPIC_MOOLAH_ADD_PROVIDER         = '\x618a463b3fb7f87438225fc638bb7c845a91f0d5acb6dcdf130ab42602a9cd3a'
TOPIC_VAULT_DEPOSIT_4626          = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_VAULT_WITHDRAW_4626         = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_VAULT_SET_CAP               = '\xe86b6d3313d3098f4c5f689c935de8fde876a597c185def2cedab85efedac686'
TOPIC_VAULT_REALLOCATE_SUPPLY     = '\x89bf199df65bf65155e3e0a8abc4ad4a1be606220c8295840dba2ab5656c1f6d'
TOPIC_VAULT_REALLOCATE_WITHDRAW   = '\xdd8bf5226dff861316e0fa7863fdb7dc7b87c614eb29a135f524eb79d5a1189a'
TOPIC_FACTORY_CREATE_VAULT        = '\x22e5b540ae5cb8ec1114db7253f1812c4eb0d3443b8ad013e0e495297e4803c1'
TOPIC_FACTORY_BROKER_MARKET       = '\x177ae1918ff4739db8b4e0be87970a23ea64fe717820f56d30f83d324acd472e'
TOPIC_FACTORY_COMMON_MARKET       = '\xc2bb1f6e1878a45dcfff7d41e675d28aaf25b048c7e7786cc64ca1d9ba645a74'
TOPIC_BROKER_FIXED_CREATED        = '\x1e0698020a99de4d142f51db1c05c57cef303cff88a7421eb43226798f1f4f4d'
TOPIC_BROKER_FIXED_REPAID         = '\x5254e54ae4b52d4f67430f479c097b7152f5756a97ef9c0d2bb04894aac902fe'
TOPIC_CREDIT_FIXED_REPAID         = '\x9b383b7ebe07b0838262fdad020131bfe87b7e8fab8b1e7ed00b61d826b23678'
TOPIC_BROKER_DYNAMIC_BORROWED     = '\x6e104f7953d981e935d5abe2353189aeca848bfb9f9e0ef9cffa1ea60e79d0fe'
TOPIC_BROKER_DYNAMIC_REPAID       = '\x05b3220325c16d99b8807c85544cec911feb69ea7dc53755c8cd9d69e0bb84f1'
TOPIC_BROKER_LIQUIDATED           = '\x09c223cfcd8c93e245f558f5f8de755fc0930fd9bc257441155ef5d54a170e0f'
TOPIC_PUBLIC_LIQUIDATED           = '\xc825af5ed71c3d4e8384fad1414973f60116d9c9ff5a485f91bb499802bd8e27'
TOPIC_SMART_LIQUIDATION           = '\xe1127b61fe62d1651bece292ed170fda3a193b633d22786a854d43b15a8378f2'
TOPIC_IRM_BORROW_RATE_UPDATE      = '\x7120161a7b3d31251e01294ab351ef15a41b91659a36032e4641bb89b121e321'
TOPIC_SS_TOKEN_EXCHANGE           = '\x143f1f8e861fbdeddd5b46e844b7d3ac7b86a122f36e8c463859ee6811b1f29c'
TOPIC_SS_ADD_LIQUIDITY            = '\xd65676560b492a7fad9eaab0b89a1316676d38ed89a6dfc48552da598d9828a3'
TOPIC_SS_REMOVE_LIQUIDITY         = '\x7c363854ccf79623411f8995b362bce5eddff18c927edc6f5dbbb5e05819a82c'
TOPIC_SS_NEW_PAIR                 = '\x02583535965f7dd02141472f8e87a2e147f8bd330781dfaf90081a3089e921e2'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors (chain-agnostic) =====
SEL_MOOLAH_SUPPLY                 = '\xa99aad89'
SEL_MOOLAH_WITHDRAW               = '\x5c2bea49'
SEL_MOOLAH_BORROW                 = '\x50d8cd4b'
SEL_MOOLAH_REPAY                  = '\x20b76e81'
SEL_MOOLAH_SUPPLY_COLLATERAL      = '\x238d6579'
SEL_MOOLAH_WITHDRAW_COLLATERAL    = '\x8720316d'
SEL_MOOLAH_LIQUIDATE              = '\xd8eabcb8'
SEL_MOOLAH_LIQUIDATE_BROKER_POS   = '\xab953674'
SEL_MOOLAH_FLASHLOAN              = '\xe0232b42'
SEL_MOOLAH_CREATE_MARKET          = '\x8c1358a2'
SEL_VAULT_DEPOSIT                 = '\x6e553f65'
SEL_VAULT_WITHDRAW                = '\xb460af94'
SEL_VAULT_REDEEM                  = '\xba087652'
SEL_VAULT_REALLOCATE              = '\x7299aa31'
SEL_BROKER_BORROW_DYNAMIC         = '\xc5ebeaec'
SEL_BROKER_BORROW_FIXED           = '\x0ecbcdab'
SEL_BROKER_REPAY_FIXED            = '\xb1e8f8ef'
SEL_LIQUIDATOR_LIQUIDATE          = '\x8539ca00'
SEL_SS_EXCHANGE                   = '\x5b41b908'
-- ===== Addresses (network-specific) =====
BSC_MOOLAH                        = '\x8f73b65b4caaf64fba2af91cc5d4a2a1318e5d8c'
BSC_MARKET_FACTORY                = '\xce26859127d236a61f168d2d0905f77d7e286ab2'
BSC_VAULT_FACTORY                 = '\x2a0cb6401fd3c6196750dc6b46702040761d9671'
BSC_IRM                           = '\xfe7dae87ebb11a7beb9f534bb23267992d9cde7c'
BSC_VAULT_WBNB                    = '\x57134a64b7cd9f9eb72f8255a671f5bf2fe3e2d0'
BSC_VAULT_USD1                    = '\xfa27f172e0b6ebcef9c51abf817e2cb142fbe627'
BSC_VAULT_U                       = '\x9a17fd5cb8efc25d11567e713ae795a89775a759'
BSC_VAULT_USDT                    = '\x6d6783c146f2b0b2774c1725297f1845dc502525'
BSC_VAULT_BTCB                    = '\xe46b8e65006e6450bdd8cb7d3274ab4f76f4c705'
BSC_LIQUIDATOR                    = '\x6a87c15598929b2db22cf68a9a0dde5bf297a59a'
BSC_PUBLIC_LIQUIDATOR             = '\x882475d622c687b079f149b69a15683fcbecc6d9'
BSC_BROKER_LIQUIDATOR             = '\x3aa647a1e902833b61e503dbbfbc58992daa4868'
BSC_SLISBNB_PROVIDER              = '\x33f7a980a246f9b8fea2254e3065576e127d4d5f'
BSC_STABLESWAP_FACTORY            = '\xde9c8e1536989d8c3817afdabc37c0fb44cb49b4'
BSC_CREDIT_BROKER                 = '\x2a6704d56bdedf4c7564c9534d7fa8d8d204d578'
BSC_UPGRADE_TIMELOCK              = '\x07d274a68393e8b8a2ccf19a2ce4ba3518735253'
ETH_MOOLAH                        = '\xf820fb4680712cd7263a0d3d024d5b5aea82fd70'
ETH_MARKET_FACTORY                = '\xa2ff080d4c0b71b6c8796129dd4acc0b09d7592c'
ETH_VAULT_FACTORY                 = '\xa91d9e7343d7eee8ed2c8f55e9162827850a7f17'
ETH_VAULT_USD1                    = '\x1a9bee2f5c85f6b4a0221fb1c733246af5306ae3'
ETH_VAULT_USDT                    = '\x28643ffd79256719d6acbcf25cb44576caebcf12'
ETH_VAULT_USDC                    = '\x9651ae50a5763c6f9b883f9d50e8116281cfcab2'
ETH_VAULT_WETH                    = '\x2e3bbd03dbc6d890c8c7e06be4e065c5c0eee7e8'
ETH_PUBLIC_LIQUIDATOR             = '\x796302e041d1715a8b1f16fd7d7cba38bb031de5'
ETH_ADMIN_TIMELOCK                = '\xa18ae79aeda3e711e0cd64cfe1cd06402d400d61'
```

## 9. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `lista-dao/moolah` source (`MarketParams` → `(address,address,address,address,uint256)`, `Id` → `bytes32`, `N_COINS` → `2`). Every listed topic0 and selector was then found as a `PUSH32`/`PUSH4` constant in the live BSC implementation bytecode (Moolah, MoolahVault, factories, LendingBroker, CreditBroker, liquidators, IRM, providers, StableSwapPool), except the library-emitted events noted in §7.6. Live `eth_getLogs` on BSC Moolah (40k-block window) returned `Supply` 85, `Borrow` 33, `SupplyCollateral` 37, `AccrueInterest` 363, `FlashLoan` 3,988, plus `Liquidate` and `CreateMarket` in older windows. Ten BSC brokers returned `FixedTermAndRateUpdated` 342, `RepaidFixedLoanPosition` 5, `FixedLoanPositionCreated` 3, `DynamicLoanPositionBorrowed` 2. Smart-Lending pools returned `AddLiquidity`/`RemoveLiquidity`. Ethereum Moolah returned `AccrueInterest` 121 in 9k blocks.
- **Addresses:** parsed from the official docs pages "BSC Core", "BSC Lending Brokers", "BSC Smart Lending", "BSC Credit" and "Ethereum", then existence-checked with `eth_getCode`. EIP-1967 implementation and admin slots were read live. `DEFAULT_ADMIN_ROLE` holders were read with `getRoleMember(0x00,0)`.
- **Chain coverage:** both Moolah addresses return `0x` on Base, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc. The `lista-dao/moolah` `broadcast/` folder holds only chain IDs 1 and 56.
- **Limit:** the public BSC endpoint serves logs for recent blocks only. Rare events (`Liquidate`, `SetCap`, IRM admin events) were confirmed by bytecode presence, not by historical logs.

Authoritative sources:
- [lista-dao/moolah](https://github.com/lista-dao/moolah) — source of truth for signatures.
- [Lista docs — Lista Lending smart contracts](https://docs.bsc.lista.org/for-developer/lista-lending/smart-contract) (BSC Core, Brokers, Smart Lending, Oracles, Credit, Ethereum).
- [Lista docs — Events and callbacks](https://docs.bsc.lista.org/for-developer/lista-lending/events-and-callbacks).
- Explorers: [BscScan](https://bscscan.com/address/0x8F73b65B4caAf64FBA2aF91cC5D4a2A1318E5D8C) · [Etherscan](https://etherscan.io/address/0xf820fB4680712CD7263a0D3D024D5b5aEA82Fd70)
