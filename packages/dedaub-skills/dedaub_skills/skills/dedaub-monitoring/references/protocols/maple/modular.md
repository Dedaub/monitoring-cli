# Maple Modular Release (Strategies, StrategyManager, LiquidityRouter, PoolManager V500) — Topics, Selectors, Addresses (Ethereum)

**Status:** verified 2026-10-30 against the `maple-labs/address-registry` (`contracts/MapleAddressRegistryETH.sol`, modular release commit of 2026-10-19), the canonical `maple-labs` sources (`strategy-manager`, `allocation-strategy`, `defi-strategies`, `maple-strategies`, `pool-v2` "public-release-v5", `globals-v2` "public-release-v5", `maple-proxy-factory`), live `eth_getCode` / `eth_getStorageAt` / `eth_call` on `ethereum-rpc.publicnode.com`, and live `eth_getLogs` (blocks 25,907,000 to 26,307,000) on `mainnet.gateway.tenderly.co`.
**Scope:** This file covers the contracts that the Maple "modular release" adds to Maple 2.0: the strategy factories (legacy Aave / Sky / Basic, Allocation, ModularAave, ModularSky), the StrategyManager, the LiquidityRouterV100, the StrategyDeployerV100, PoolDeployerV5, the PoolManager V500 event and selector changes, the Globals V500 strategy registry, and the Secured Lending 2 and Secured Lending 3 USDC pools. The release is on **Ethereum (1) only**. The other eight chains (Base 8453, BNB 56, Avalanche 43114, Arbitrum 42161, Optimism 10, Polygon 137, Robinhood Chain 4663, Arc 5042) have no code at any of these addresses. Topics and selectors are chain-agnostic. Addresses are network-specific. For the core Pool / LoanManager / Loan / WithdrawalManager stack, see [v2.md](v2.md).

The release adds a second funding path to Maple 2.0. Before V500, a PoolManager sent cash only to LoanManagers and to "legacy" strategies (one Aave or Sky strategy for each pool). With V500, a PoolManager can also fund a **StrategyManager**. A StrategyManager is a share-based vault that one or more PoolManagers can fund. Each StrategyManager holds exactly one **underlying strategy**: an Allocation strategy (off-chain deployment to Maple-managed wallets), a ModularAave strategy (Aave v3), or a ModularSky strategy (sUSDS via the Lite PSM).

All strategies and StrategyManagers are `maple-proxy-factory` proxies. The implementation is at the standard EIP-1967 slot. Upgrades emit the Maple `Upgraded(uint256,bytes)` event, not the OpenZeppelin `Upgraded(address)` event.

Status on 2026-10-30: all four strategy factories and the StrategyManagerFactory have version 100 registered, and Globals lists them as valid instances. **No StrategyManager or modular strategy instance exists yet.** The factories emitted no `InstanceDeployed` event and the LiquidityRouter emitted no `ActionExecuted` event in the scanned range. On 2026-10-27 (block 26,284,267) all six Ethereum PoolManagers moved to V500. The V500 migrator removed the syrupUSDC Aave strategy, Sky strategy and FixedTermLoanManager from the syrupUSDC strategy list. Each PoolManager now lists only its OpenTermLoanManager.

---

## 0. Contract families & versions

| Component | Repo | Role | Status (2026-10-30) |
|-----------|------|------|---------------------|
| **PoolManager V500** | `pool-v2` | Adds StrategyManagers and per-strategy caps. Removes first-loss cover and collateral-liquidation entry points. | Live on all 6 Ethereum PMs. Base PM still V301. |
| **MapleGlobals V500** | `globals-v2` | Adds strategy delegates and StrategyManager ownership. | Live (`0x804a…390C` impl = `0xaFaA…26a8`). |
| **StrategyManagerFactory / StrategyManager V100** | `strategy-manager` | Share vault that PoolManagers fund. Holds one underlying strategy. | Factory live. 0 instances. |
| **LiquidityRouterV100** | `strategy-manager` | Bot entry point. Batches fund / redeem actions across StrategyManagers. | Live. No actions yet. |
| **StrategyDeployerV100** | `strategy-manager` | Deploys a StrategyManager plus its underlying strategy in one call. | Live. No deployments yet. |
| **AllocationStrategy V100** | `allocation-strategy` | Underlying strategy. Moves assets to Maple-managed wallets. Records yield and losses manually. | Factory live. 0 instances. |
| **ModularAaveStrategy V100** | `defi-strategies` (`aaveV3`) | Underlying strategy. Supplies to Aave v3. | Factory live. 0 instances. |
| **ModularSkyStrategy V100** | `defi-strategies` (`sky`) | Underlying strategy. Swaps through the USDS Lite PSM into sUSDS. | Factory live. 0 instances. |
| Legacy Aave / Sky / Basic strategy V100 | `maple-strategies` | Pre-V500 strategies owned directly by one PoolManager. | Proxies still have code. Removed from syrupUSDC strategy list by V500 migration. |
| **PoolDeployerV5** | `pool-v2` | Deploys Pool + PM + WMQueue + strategies + StrategyManager links. | Live. |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 PoolManager V500 (new or changed events)

| topic0 | Event | Note |
|--------|-------|------|
| `0xc4337e1c0960ac88a59f4bc4c791d1c34c50e4e788068ed19b44e0e02df5ece9` | `StrategyCapSet(address indexed strategy, uint256 cap)` | ✅ live: all 6 PMs at block 26,284,492 (cap = `type(uint256).max` for the OTLM) |
| `0xe949dc96022167fc8082115ea872f2c356b80ed87f05013e44a3c76f5c6bace9` | `StrategyManagerAdded(address indexed strategyManager)` | in V500 bytecode, not seen live yet |
| `0x7a44bb4293aefdc93f2c5a934d80e4aba83489c8f880a352a8757a2248ad539c` | `StrategyManagerRemoved(address indexed strategyManager)` | in V500 bytecode |
| `0x09a1db4b80c32706328728508c941a6b954f31eb5affd32f236c1fd405f8fea4` | `StrategyRemoved(address indexed strategy)` | ✅ live: emitted by `MaplePoolManagerMigratorV500` (delegatecall, so the emitter is the PM) |
| `0xaaaa7ee6b0c2f4ee1fa7312c7d5b3623a434da5a1a9ce3cb6e629caa23454ab6` | `Upgraded(uint256 toVersion, bytes arguments)` | ✅ live: PM upgrade to version 500 (`0x1f4`) |
| `0xad307780531f6353137c35adc50ad58d71b76e76aa891e729387f2e720f2de20` | `Initialized(address owner, address asset, address pool)` | ✅ live: PM initializer, at SL2/SL3 deploy |
| `0x3f008fd510eae7a9e7bee13513d7b83bef8003d488b5a3d0b0da4de71d6846f1` | `StrategyAdded(address indexed strategy)` | ✅ unchanged from V400 |

V500 keeps the other V400 events (`RedeemRequested`, `RedeemProcessed`, `SharesRemoved`, `LiquidityCapSet`, `SetAsActive`, `CollateralLiquidationFinished`, delegate and config events; see [v2.md §1.2](v2.md)). **V500 removes** `CoverDeposited` `0x11cdeb47…`, `CoverLiquidated` `0x94b78163…`, `CoverWithdrawn` `0x197c9d0c…`, `IsStrategySet` `0xcc29d2c1…`, `CollateralLiquidationTriggered` `0x371cc890…` and the PM `WithdrawalProcessed` `0xddfdc995…`. None of these topic constants is in the V500 implementation bytecode.

### 1.2 MapleGlobals V500 (strategy registry)

| topic0 | Event |
|--------|-------|
| `0xa1a14befd3a48c950763e461d129a4380ff579f8c7c977c5f232310c1fc42955` | `StrategyManagerActivated(address indexed strategyManager, address indexed strategyDelegate)` |
| `0x22383f230c4a0be5f9e0484efc6de2095ab60c7654cd63bb0be632c8c62472ab` | `StrategyManagerOwnershipTransferred(address indexed fromStrategyDelegate, address indexed toStrategyDelegate, address indexed strategyManager)` |
| `0x352bfdc20340358bc42831c16717dee972a216931e432e31e72204e935eb0eb7` | `ValidStrategyDelegateSet(address indexed account, bool isValid)` ✅ (18 accounts set at block 26,284,492) |
| `0x57c2985237d36106b3006c22a6bd79dfd8a26b3821516081b9441c92cd56b773` | `ValidInstanceSet(bytes32 indexed instanceKey, address indexed instance, bool isValid)` ✅ (shared with v2.md) |

`ValidInstanceSet` keys used by this release (ASCII `bytes32`): `STRATEGY_MANAGER_FACTORY`, `UNDERLYING_STRATEGY_FACTORY`, `LIQUIDITY_ROUTER`, `LIQUIDITY_ROUTER_BOT`, `LIQUIDITY_BOT`, `MAPLE_MANAGED_WALLET`, `STRATEGY_VAULT`, `PSM`. The keys `LIQUIDITY_BOT`, `LIQUIDITY_ROUTER_BOT` and `MAPLE_MANAGED_WALLET` gate who can move funds. Watch them.

### 1.3 StrategyManager

| topic0 | Event |
|--------|-------|
| `0xa137ad0c8177aba61beb1b2d091603860bad76c6d3b3be76bea7367c19c58de4` | `StrategyManagerFunded(address indexed poolManager, uint256 assetsIn, uint256 assetsDeposited, uint256 sharesMinted)` |
| `0x3779310b71beb93dce3cb4f282d1ee00e2a6c89891587b17c1842ba12f7d52a4` | `RedemptionRequested(address indexed poolManager, uint256 sharesRequested)` |
| `0x9aec5cafc1451c1485e4a0099bd4dfb4c9d2bb972b4e5c798da07db8323deaa3` | `RedemptionCancelled(address indexed poolManager, uint256 sharesCancelled)` |
| `0xf9f22dbb7dd6f69e7cd372268cb6067f61049833233f2653a00e171b4ac04a35` | `RedemptionProcessed(address indexed poolManager, uint256 sharesProcessed, uint256 assetsWithdrawn)` |
| `0x6a39752ad6bf36ecd7fd6e804a42c91f6425e4c6d2b2d8f059e132e4d23d242a` | `PoolManagerCapSet(address indexed poolManager, uint256 cap)` |
| `0xe39ef0330bd7b5f0bc634bc7a2fd027883b6ae722d9485fda9061ea87c5f019e` | `StrategyLiquidityCapSet(uint256 cap)` |
| `0xc4de5969230b6e1a5271556063cd3dcfa0b5e7ac9749a7242b091b561c223532` | `UnderlyingStrategySet(address indexed underlyingStrategy)` |
| `0x145eab1ae00d5abb19e7f56f7ad18a854beb049e75b8c13dea895f9e57ba8c75` | `PendingStrategyDelegateSet(address indexed pendingStrategyDelegate)` |
| `0xc9f344d0f58d6cb187256987d2f0c903974d0ec41eb3b5dd605d9bf4f8d35786` | `PendingStrategyDelegateAccepted(address indexed previousStrategyDelegate, address indexed newStrategyDelegate)` |
| `0x2c84388d2e7c157623e870b57a151f155d0e4611e8be0b6729aed21336930725` | `StrategyManagerConfigurationComplete()` |
| `0x3d5d61d217e7fecd922d11f2a46d0e10cc789ec3f1e4e2c2fa41c4c2f92489bb` | `SetAsActive(bool active)` — **same topic as PoolManager `SetAsActive`** |

### 1.4 LiquidityRouterV100 and StrategyDeployerV100

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xa46e5e78bfe815d8f44b02a54f9d18c58b7a435bc9c73c2aae992826c95fe473` | `ActionExecuted(uint256 actionIndex, uint8 indexed actionType, address indexed strategyManager, address indexed poolManager, uint256 amount)` | LiquidityRouter. `actionType` enum: 0 `FUND_STRATEGY`, 1 `REQUEST_REDEEM`, 2 `CANCEL_REDEMPTION`, 3 `PROCESS_REDEMPTION`. |
| `0xd86a70899bbf7799d77564d7aba7ce5f114dfc64bb6563561b0555da3d613cd6` | `StrategyManagerDeployed(address indexed strategyDelegate, address indexed strategyManager, address indexed underlyingStrategy)` | StrategyDeployer |
| `0x8307758e931f63bfd57ea77a5a50503e0536b16afa4dafdda14fc1bab57e38b1` | `PoolDeployed(address indexed pool, address indexed poolManager, address indexed withdrawalManager, address[] strategies, address[] strategyManagers)` | PoolDeployerV5 |

### 1.5 AllocationStrategy (underlying strategy, managed wallets)

| topic0 | Event |
|--------|-------|
| `0xb9604a9ad6dcb570b9913035d6d312dffa9c0bfc935d16bd0d4c9adec2f96ea2` | `StrategyFunded(address indexed strategyManager, uint256 assets, uint256 recordedAssets)` — **same topic as ModularAave `StrategyFunded`** |
| `0xe8da4fd93dfef82d36835b8bcc5bb2e5eab810078bb85c3dd5e348eaf3f3726b` | `StrategyWithdrawn(address indexed strategyManager, address indexed destination, uint256 assets, uint256 recordedAssets)` |
| `0x8694c6e3190e2c3f94de9e1e582500d8cf5ea6d6d03a676e18ecf2864501b870` | `AssetsDeployed(address indexed deployer, uint256 assets, uint256 recordedAssets, bytes metadata)` — **assets leave the chain-visible strategy for a managed wallet** |
| `0x34f04a2d9246787577a75dc4677f025ac8e0fac53d5e6c1b0eb391b6af56b03e` | `AssetsReturned(address indexed caller, address indexed onBehalfOf, uint256 assets, uint256 recordedAssets, bytes metadata)` |
| `0x9032f6ce4816874bdf59d769ee1aecec6590ffe0792034de0ba9eb350f8cae68` | `AssetsSkimmed(address indexed recipient, uint256 assets)` |
| `0xbcc8c665985e44525378c7f609dcf37ad9a5cf547ba518b9cab7d4dbd845b827` | `YieldRealized(address indexed caller, uint256 unrealizedYield, uint256 netYield, uint256 delegateFee, uint256 protocolFee, uint256 recordedAssets, uint32 duration, bytes metadata)` |
| `0xfa1088c6df2d6ea24d731d0a03014ce8c85b1ee2fe42f6a435d125314c0a6782` | `YieldCancelled(address indexed caller, address indexed recipient, uint256 assets, uint256 recordedAssets)` |
| `0xe3a8892d98a85e27e5915f949c9bfa69e15ee3d019403681523ea8150f46b553` | `YieldCapSet(uint256 yieldCap)` |
| `0xb477a35177f736ca0c21727c1b0494e580983172c6d469269a8786150fd75ca3` | `LossRecognized(address indexed caller, address indexed deployer, uint256 assets)` |
| `0x3d1e299f39b6e4e65aaa2cbde0955f28b32a6c26830ca216256616506eceeebd` | `Impaired(uint256 assets)` — shared by all three modular strategies |
| `0x94f3387cabdaf912caff343ac490a3056bb348c474be2c718b9f59f56f1b7d97` | `ImpairmentRemoved(uint256 assets)` — shared by all three modular strategies **and FixedTermLoan** `ImpairmentRemoved(uint256)` |
| `0xf3e85a8a32d3a402acbdc917fdc3af7c1e1b1876f8ca7191b1a3bd7c8c445a60` | `DeploymentCapSet(address indexed account, uint256 deploymentCap)` |
| `0xa34ed5e9c5d2532dfb13e11b6f806059e6f44ef598718ee44da19e20a55e32d6` | `PermissionSet(address indexed account, bool canDeployAssets, bool canReturnAssets, bool canRealizeYield)` |
| `0xf4addd7cb1000a2bf599c5dc49d3840334f8b830cbb2b66e13bbcc257d4d713c` | `StrategyDelegateFeeRateSet(uint32 strategyDelegateFeeRate)` — shared, all modular strategies |
| `0x7d6737ad553738a795366755ba1ded1d9dd689a62ab1ea7a743c7e79c25a91ae` | `StrategyProtocolFeeRateSet(uint32 strategyProtocolFeeRate)` — shared |
| `0xe4851a57b1e23e9586bf96b1b08d14e8f0f568b6daed3747eecceebb4a012e6d` | `StrategyMetadataSet(string strategyMetadata)` — shared |

### 1.6 ModularAaveStrategy and ModularSkyStrategy

| topic0 | Event | Strategy |
|--------|-------|----------|
| `0xb9604a9ad6dcb570b9913035d6d312dffa9c0bfc935d16bd0d4c9adec2f96ea2` | `StrategyFunded(address indexed strategyManager, uint256 assetsIn, uint256 deployedAssets)` | Aave (same topic as Allocation) |
| `0xf3a2537583064f88f4c6122997a696a0cbb3cf497c6e23f23cfbca871bef7dd2` | `StrategyFunded(address indexed strategyManager, uint256 assetsIn, uint256 sharesMinted, uint256 deployedAssets)` | Sky |
| `0xd5ad0f046bd35f48b421a3e575435de38cea1980177b1c6da935d2f26049f3fa` | `StrategyWithdrawal(address indexed destination, uint256 assetsOut)` | Aave |
| `0x88f0c01d2402991a2098e1cf989cb2c54cefe3b20ccb83c55989866f419a6ff5` | `StrategyWithdrawal(address indexed destination, uint256 sharesBurned, uint256 assetsOut)` | Sky |
| `0xa6b2ff5d1ba994844f597ecc1b29116e234378f7614499c6eaa93d84b9de0d7e` | `StrategyFeesCollected(uint256 delegateFee, uint256 protocolFee)` | both |
| `0x456a2c591797fc5c7f65b85461f55bf486edd2bb464bbdb7b42577dfd74dbb42` | `LossRecognized()` | both |
| `0x3fb151d8dddd4dd180f8b324be13da04e5ddc747df9576e2d1efc5fb69e129d0` | `PositionRecovered(uint256 shares)` | both |
| `0x1fd3255ebb47c661867be4ec9d626e409b0984cd18c7ba548c2a2ead5e56888f` | `ReferralCodeSet(uint16 referralCode)` | both |
| `0xfc30cddea38e2bf4d6ea7d3f9ed3b6ad7f176419f4963bd81318067a4aee73fe` | `RewardsClaimed(address indexed rewardToken, uint256 amount)` | Aave (same topic as legacy Aave) |
| `0xeac980e16b6521081f5eb660011cea93f1ab66d41b0bce28e6dbcb83a934475e` | `UseVirtualUnderlyingBalanceSet(bool useVirtualUnderlyingBalance)` | Aave |
| `0x710a917c03749fe98cc5b20147989affa3121c4925cca3419ed6138546ca6634` | `FallbackToutSet(uint256 fallbackTout)` | Sky |

Plus `Impaired`, `ImpairmentRemoved`, `StrategyDelegateFeeRateSet`, `StrategyProtocolFeeRateSet`, `StrategyMetadataSet` from §1.5.

### 1.7 Legacy Aave / Sky / Basic strategies (`maple-strategies`, pre-V500)

| topic0 | Event | Aave | Sky | Basic |
|--------|-------|:---:|:---:|:---:|
| `0x3d6565101a1c6c13991358f5851c7af96dfda23edf4f1391da423b26c1d3df75` | `StrategyFunded(uint256 assets)` | ✓ | | |
| `0xdf6bc5d53caf80630bcba0ff64b0f79c973ce3cb0c3edf552df7e00951519b54` | `StrategyFunded(uint256 assets, uint256 shares)` | | ✓ | ✓ |
| `0x1e3b88c775a5ef3ca37ef9424a3dde5b6328b543e7ea0d0250804698030bf29a` | `StrategyWithdrawal(uint256 assets)` | ✓ | | |
| `0x7f9a30215421fe39f77e4b9088e3f8d5977897d39e5696eccd312f7899d00085` | `StrategyWithdrawal(uint256 assets, uint256 shares)` | | ✓ | ✓ |
| `0x9276f1867fd63028a391b04a7ea7ad4772dd6eb3c65b9d84d43a4191deafa585` | `StrategyFeesCollected(uint256 fees)` | ✓ | ✓ | ✓ |
| `0xd4e301cce72cd0440a56cdeab2102ff8e851e0ac79c5e37904287904d19ecb91` | `StrategyFeeRateSet(uint256 feeRate)` | ✓ | ✓ | ✓ |
| `0x1b4bdf15e9083497b4929bf7a5dbe5bc33142228d131e43e84a546ecb0518df1` | `StrategyImpaired()` | ✓ | ✓ | ✓ |
| `0xf82141db4260bd315c4143a3791ae7d00593cc834891fadde268d54e2da75c34` | `StrategyDeactivated()` | ✓ | ✓ | ✓ |
| `0x6f1e5df07a9e115b89ad6fb551f92196704d1c3160aad1c9eb7d68c6468337ce` | `StrategyReactivated(bool updateAccounting)` | ✓ | ✓ | ✓ |
| `0xfc30cddea38e2bf4d6ea7d3f9ed3b6ad7f176419f4963bd81318067a4aee73fe` | `RewardsClaimed(address indexed rewardToken, uint256 amount)` | ✓ | | |
| `0xf0148d1b2505aca406503d95f5049e6f7ef83bfb44bf8a69c26c97b9c1a31423` | `PsmSet(address indexed psm)` | | ✓ | |

### 1.8 Proxy factories (all strategy and StrategyManager factories)

| topic0 | Event |
|--------|-------|
| `0x8919387fe006fdc29a3dfcc183071d7974bc03747fedb0019630f1e13f85cc64` | `InstanceDeployed(uint256 indexed version, address indexed instance, bytes initializationArguments)` — **new StrategyManager / strategy** |
| `0xfbb4f36b70dba8ecedc8b38361f44f1b0c61e04ec4e0ccf620649dc558573f5f` | `InstanceUpgraded(address indexed instance, uint256 indexed fromVersion, uint256 indexed toVersion, bytes migrationArguments)` |
| `0xe69962526b7f07862bf85663f861564361295f9601236fbbe056591eb1b63f3b` | `ImplementationRegistered(uint256 indexed version, address indexed implementationAddress, address indexed initializer)` ✅ (v100 on all 4 new factories, block 26,205,357 area) |
| `0xddb2013cf7f102d15447c4c1e94cf56823455f02eb244d0c3b2ef65163389346` | `DefaultVersionSet(uint256 indexed version)` ✅ |
| `0x549a41e54b51dcc3f29b51bb02a8adcc4ec5ae26604608e41bde60311dcef106` | `UpgradePathEnabled(uint256 indexed fromVersion, uint256 indexed toVersion, address indexed migrator)` |
| `0xa46f1addc2236b7d93ed2a8a507f1c47cc92656d2b6f82bf0876da9e964b9e5e` | `UpgradePathDisabled(uint256 indexed fromVersion, uint256 indexed toVersion)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All selectors below were found as `PUSH4` immediates in the deployed implementation bytecode.

### 2.1 PoolManager V500

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf122073e` | `addStrategyManager(address)` | governor (or before configuration) |
| `0xb57ee836` | `removeStrategyManager(address)` | operational admin. Requires `assetsOf(PM) == 0`. |
| `0xeb824c25` | `setStrategyCap(address,uint256)` | emits `StrategyCapSet` |
| `0xa80da3bd` | `addStrategy(address,bytes32,bytes)` | deploys a LoanManager or strategy from a factory |
| `0x494666b6` | `requestFunds(address,uint256)` | called by LoanManager or StrategyManager. Moves pool cash to `destination`. |
| `0xffb43a5f` | `triggerDefault(address)` | **new one-argument form** (V400 used `triggerDefault(address,address)` `0x40504ba0`) |
| `0x60af6ad3` / `0xe345f4b6` | `processRedeem(uint256,address,address)` / `processWithdraw(uint256,address,address)` | WM-only |
| `0x7d41c86e` / `0xd4dd0438` | `requestRedeem(uint256,address,address)` / `requestWithdraw(uint256,uint256,address,address)` | pool-only |
| `0x7bec9b18` | `strategyListLength()` | view. Use with `strategyList(uint256)` `0xa267526b`. |
| `0xcaf901dd` | `hasSufficientCover()` | now `pure` (always true) |

Removed in V500 (absent from bytecode): `depositCover(uint256)` `0x8b1c4990`, `withdrawCover(uint256,address)` `0x26af24b7`, `finishCollateralLiquidation(address)` `0x9e5df6c2`.

### 2.2 MapleGlobals V500 (strategy additions)

| Selector | Signature |
|----------|-----------|
| `0x9b1f1fea` | `setValidStrategyDelegate(address,bool)` |
| `0xa6513d1f` | `activateStrategyManager(address)` |
| `0xe38fa06b` | `transferOwnedStrategyManager(address,address)` |
| `0x2406509e` | `isStrategyDelegate(address)` (view) |
| `0x5869fa69` | `ownedStrategyManager(address)` (view) |

### 2.3 StrategyManager

| Selector | Signature | Access |
|----------|-----------|--------|
| `0x181b19a6` | `fundStrategyManager(address poolManager, uint256 assetsIn, bytes data)` | operator (strategy delegate, or a `LIQUIDITY_BOT` instance when the strategy is not impaired) |
| `0x65b89f9f` | `requestRedeem(address poolManager, uint256 shares)` | operator or pool delegate |
| `0x635403f6` | `cancelRedemption(address poolManager, uint256 shares)` | operator or pool delegate |
| `0xc8dbe7a6` | `processRedemption(address poolManager, uint256 shares, bytes data)` | operator |
| `0x0b2f2d34` | `setPoolManagerCap(address,uint256)` | admin |
| `0x449c6679` | `setStrategyLiquidityCap(uint256)` | admin |
| `0xcac19215` | `setUnderlyingStrategy(address)` | admin |
| `0x88d75b43` | `completeConfiguration(uint256 bootstrapAssets, bytes bootstrapFundingData)` | one time |
| `0xacec338a` | `setActive(bool)` | same selector as PoolManager `setActive` |
| `0x10f046e1` / `0xff2bb8f7` | `setPendingStrategyDelegate(address)` / `acceptStrategyDelegate()` | |
| `0x2c62fa10` | `assetsOf(address poolManager)` | view |
| `0xb31b1c1d` | `unrealizedLossesOf(address poolManager)` | view |
| `0xf6de0bd2` | `assetsUnderManagement()` | view |
| `0xe322ad2b` | `availableToWithdraw()` | view |
| `0x464b4158` | `isAssetSupported(address)` | view |

### 2.4 LiquidityRouterV100, StrategyDeployerV100, PoolDeployerV5

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5e49a51d` | `executeActions((uint8,address,address,uint256,bytes)[] actions, uint256 deadline)` | Router. Caller must be a `LIQUIDITY_ROUTER_BOT` instance. Each action calls the StrategyManager. |
| `0xdad52ef5` | `deploy(address strategyManagerFactory, address strategyFactory, uint256 strategyLiquidityCap, bytes strategyDeploymentData, bytes bootstrapFundingData)` | StrategyDeployer. Returns `(strategyManager, underlyingStrategy)`. |
| `0x973b5182` | `getDeploymentAddresses(address,address,address,bytes)` | StrategyDeployer view |
| `0x178aee6c` | `deployPool(address,address,(address,uint256,string,string),(address,uint256,uint256),(address,uint256,bytes32,bytes)[],(address,uint256)[])` | PoolDeployerV5 |

### 2.5 Underlying strategies (modular)

| Selector | Signature | Allocation | Aave | Sky |
|----------|-----------|:---:|:---:|:---:|
| `0x0c9e543c` | `fundUnderlyingStrategy(uint256,bytes)` | ✓ | ✓ | ✓ |
| `0xa6b221a2` | `withdrawFromUnderlyingStrategy(address,uint256,bytes)` | ✓ | ✓ | ✓ |
| `0x8318369e` | `impair(uint256)` | ✓ | ✓ | ✓ |
| `0xc9dd3860` | `removeImpairment(uint256)` | ✓ | ✓ | ✓ |
| `0x73fb6c3a` | `deployAssets(uint256,bytes)` | ✓ managed wallet only | | |
| `0xc5f0ec55` | `returnAssets(uint256,address,bytes)` | ✓ | | |
| `0x7d2598fb` | `realizeYield(uint256,uint32,bytes)` | ✓ (1-hour cooldown) | | |
| `0x3ad93481` | `cancelYield(uint256,address)` | ✓ | | |
| `0x38c9be44` | `recognizeLoss(uint256,address)` | ✓ | | |
| `0x476c9993` | `recognizeLossAndRemoveImpairment(uint256,uint256,address)` | ✓ | | |
| `0x0b202016` | `setDeploymentCaps(address[],uint256[])` | ✓ | | |
| `0x6bdd5ee3` | `setPermissions(address[],bool[],bool[],bool[])` | ✓ | | |
| `0x062aa034` | `setYieldCap(uint256)` | ✓ | | |
| `0xbc25cf77` | `skim(address)` | ✓ | | |
| `0xa7744ff0` | `recognizeLoss()` | | ✓ | ✓ |
| `0xc2768b69` | `recoverPosition()` | | ✓ | ✓ |
| `0x3111e7b3` | `claimRewards(address[],uint256,address)` | | ✓ | |
| `0x0e5dcb8b` | `setUseVirtualUnderlyingBalance(bool)` | | ✓ | |
| `0xe42627f6` | `setFallbackTout(uint256)` | | | ✓ |
| `0x5d0e83d5` / `0x6c4248c3` | `setStrategyDelegateFeeRate(uint32)` / `setStrategyProtocolFeeRate(uint32)` | ✓ | ✓ | ✓ |

### 2.6 Legacy strategies (`maple-strategies`)

| Selector | Signature | Aave | Sky | Basic |
|----------|-----------|:---:|:---:|:---:|
| `0x11a5ffad` | `fundStrategy(uint256)` | ✓ | ✓ | |
| `0x82f85c90` | `fundStrategy(uint256,uint256)` | | | ✓ |
| `0x48b19335` | `withdrawFromStrategy(uint256)` | ✓ | ✓ | |
| `0xf840cb83` | `withdrawFromStrategy(uint256,uint256)` | | | ✓ |
| `0x1790b39a` | `impairStrategy()` | ✓ | ✓ | ✓ |
| `0x21401dd1` | `deactivateStrategy()` | ✓ | ✓ | ✓ |
| `0x4bc6a056` | `reactivateStrategy(bool)` | ✓ | ✓ | ✓ |
| `0x5f1e2bdc` | `setStrategyFeeRate(uint256)` | ✓ | ✓ | ✓ |
| `0x81e492c4` | `setPsm(address)` | | ✓ | |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` on `ethereum-rpc.publicnode.com` on 2026-10-30. Byte sizes are runtime code.

### 3.1 Factories (each is a `MapleProxyFactory`, not a proxy)

| Role | Address | Registered impl (v100) |
|------|---------|------------------------|
| **strategyManagerFactory** | `0xc72A81c771BCFdD3C60C642dAdBa1896760747F4` | StrategyManager `0x8B29e619366aD9194e18ba196434B4FFA5b1C696` (13,276 B), initializer `0xd0E9D99216Aff5D0885E961f96298fb020e3F808` |
| **allocationStrategyFactory** | `0x7C9bB6ddf53d6ada9592f478CF224034c1fC1126` | AllocationStrategy `0x010fcE31660Aac02930FfB11aF3A51af0De0e2f8` (19,511 B), init `0x2EAb99d8edc1A1354e3c0D0e9C2ac2ed31CD9b93` |
| **modularAaveStrategyFactory** | `0x2b1E33ed3d742Be945A6A81b581d824C9FBa6cd7` | ModularAave `0x25DE505b3A449456E7a85400b71B5185A66bb908` (16,002 B), init `0xa1696F6042C0756F73D9701B12D983f20FF3EC4C` |
| **modularSkyStrategyFactory** | `0xb9965C97bD7a64CB8DA10e947A2aDE8b32396ca0` | ModularSky `0x20C7c396ef6F2710FA15301925c61bA99Dd0504d` (16,831 B), init `0x103e84e2E3869087558E59233859F0a249451918` |
| aaveStrategyFactory (legacy) | `0x01ab799f77F9a9f4dd0D2b6E7C83DCF3F48D5650` | Aave `0xFc8F7F97165d446B02Cc95363d2cA31154BBe9F9` (9,759 B), init `0x0d2dBb28B1c7d225132722FAdb2402E93A35c1Be` |
| skyStrategyFactory (legacy) | `0x27327E08de810c687687F95bfCE92088089b56dB` | Sky `0xBBEe42621499005Ff0dDEF947BBDeFfBBeE77730` (11,664 B), init `0x29199d071717c72baab50eEf9adD6736A18A1d1d` |
| basicStrategyFactory (legacy) | `0x876D54DBF61473cA169b89B95344A14E81F37afe` | Basic `0x7a1E281Ec29F3A861f211a28a23161762BD55B73` (8,961 B), init `0x2b9aDDb5244548f126e59FA5483040efc102f69e` |

The registry key `UNDERLYING_STRATEGY_FACTORY` lists only the three modular factories (Allocation, ModularAave, ModularSky). The legacy factories are not valid sources for a StrategyManager underlying strategy.

### 3.2 Singletons

| Role | Address | One-liner |
|------|---------|-----------|
| **LiquidityRouterV100** | `0x28Bb4fF6ac910D9DceA90e11625559b8345c0588` | 2,608 B, immutable. Globals key `LIQUIDITY_ROUTER`. |
| **StrategyDeployerV100** | `0x5e9D93016B2F5A2920B56EfDb784fBA4099100cD` | 3,697 B, immutable. `canDeployFrom` on all four new factories. |
| **PoolDeployerV5** | `0x0EFD7a4B98a4eC8bf7d7Ec9F30a3274B0B51c075` | 6,650 B. `canDeployFrom` on poolManagerFactory and withdrawalManagerQueueFactory. |
| PoolManager V500 impl | `0x47feAa096Efe5D44ED9378A29705C47C60ffC3B5` | 16,871 B. Initializer `0x823CA9278B5fCccCcBb4a9DB724f46Cc964C6798`, migrator `0x648b23cf5c81f18E877DA40d8b7d2a6477b16a13`. |
| MapleGlobals V500 impl | `0xaFaAa45bc170384F07188d04C6412fa3716826a8` | 14,249 B. Behind Globals `0x804a6F5F667170F545Bf14e5DDB48C70B788390C`. |
| STRATEGY_VAULT (registered in Globals) | `0x7c0477d085ecb607cf8429f3ec91ae5e1e460f4f` | Not a Maple contract: Aave `aEthUSDG` ("Aave Ethereum USDG"). The key `STRATEGY_VAULT` lists the external vaults (aToken, sUSDS) that a modular Aave or Sky strategy may use. |

### 3.3 Secured Lending 2 and 3 USDC pools (Maple Institutional)

Both pools use USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`. They have one OpenTermLoanManager and no FixedTermLoanManager.

| Role | Secured Lending 2 USDC | Secured Lending 3 USDC |
|------|------------------------|------------------------|
| **Pool** (ERC-4626, not a proxy) | `0x6a956aA2D183b6b5E9d9F64b1c137098BeF627Ea` (`MISLUSDC2`) | `0xa7f5df53165FaEb890ae37f4B0f973A42D166222` (`MISLUSDC3`) |
| PoolManager (proxy, V500) | `0x462e6203176b41B741B3DD03Db14ffb29fcfA693` | `0xb0eAD5d35c07f9EE6fc4E2c82B929CA39151E98D` |
| OpenTermLoanManager (proxy, V100 `0xbAD0…B241`) | `0x7d4c8157c29BaFf70D5d08CE57Eaf32820415E12` | `0x7eC236b4B1c6cA0D87405057714eAD0f63Ed8849` |
| WithdrawalManagerQueue (proxy, V201) | `0xb84A4aF193ba7b2ecfc8E65a099e0f01EbbbF6f4` | `0x3c139C88D45cD17d85f75371De4DE4368BFc18fd` |
| PoolDelegateCover (plain, 759 B) | `0x938F9532F8Afd8fF9294AbBa37B89b780aaFD186` | `0x442155C5DEF2a733EAE0365b87F63C2457047fbd` |
| Pool delegate (from `PoolManagerActivated`) | `0xa34af9c3cca1e2592553feba6675a1a05bde6aae` | `0xeb8320e2e0d85ec8f6884cf0fe2d693aac4ba4b4` |
| Activated | 2026-09-29 (block 26,084,251) | 2026-10-13 (block 26,185,035) |

Both pools held only about 4 USDC (bootstrap) on 2026-10-30. Pool names: "Maple Institutional - Secured Lending 2 USDC" and "... 3 USDC".

### 3.4 PoolManager strategy lists after V500 (read live via `strategyList(i)`)

| Pool | PoolManager | Strategy list (2026-10-30) |
|------|-------------|----------------------------|
| syrupUSDC | `0x7aD5fFa5fdF509E30186F4609c2f6269f4B6158F` | OTLM `0x6ACE…0fAc` only. Aave `0x560B…91d4`, Sky `0x859C…038C` and FTLM `0x4A1c…371b` removed (`StrategyRemoved`, block 26,284,267). |
| syrupUSDT | `0x0cdA32E08B48bFDDbc7eE96B44b09cf286F9E21a` | OTLM `0x6160…FAFf` only |
| syrupUSDG | `0x6c48CD22086F3Db3F23E7cEeDD5c429D93FF3327` | OTLM `0x7bE9…920A` only |
| Secured Lending USDC | `0x9ceF7d1D390A4811bBa1BC40A53B40a506C33B19` | OTLM `0xb50D…675E` only |
| Secured Lending 2 USDC | `0x462e6203176b41B741B3DD03Db14ffb29fcfA693` | OTLM `0x7d4c…5E12` only |
| Secured Lending 3 USDC | `0xb0eAD5d35c07f9EE6fc4E2c82B929CA39151E98D` | OTLM `0x7eC2…8849` only |

Legacy strategy proxies still have code (147 B, impl = legacy Aave or Sky): syrupUSDC Aave `0x560B3A85Af1cEF113BB60105d0Cf21e1d05F91d4`, syrupUSDC Sky `0x859C9980931fa0A63765fD8EF2e29918Af5b038C`, syrupUSDT Aave `0x2b817B822B0ddd4597a92dBEd1bD0a6796CA37E0`, Secured Lending Aave `0x87Aa770f610679DFC2553FB95fAc1B4d996BA1cd`, Secured Lending Sky `0xe3eE1b26AF5396Cec45c8C3b4c4FD5136A2455CC`.

---

## 4. Other chains

| Chain (ID) | Modular release present? | Evidence |
|------------|--------------------------|----------|
| Base (8453) | No | `eth_getCode` = `0x` for all 8 key addresses. `MapleAddressRegistryBASEL2.sol` has no strategy, router or V500 entry. Base PoolManager `0x7aA1…90ee` impl = V301 `0x5b1D…86c2`. |
| BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137), Robinhood Chain (4663), Arc (5042) | No | `eth_getCode` = `0x` for the router, deployer, 5 factories and the PM V500 impl. The first five hold only bridged Syrup tokens ([syrup-cross-chain.md](syrup-cross-chain.md)). |

---

## 5. Cross-chain summary

| Chain | StrategyManagerFactory | Strategy factories | LiquidityRouter | StrategyDeployer | PoolDeployerV5 | PM V500 | SL2 / SL3 pools |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Ethereum (1) | ✓ | ✓ (6) | ✓ | ✓ | ✓ | ✓ (6 PMs) | ✓ |
| Base (8453) | — | — | — | — | — | — (V301) | — |
| BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood, Arc | — | — | — | — | — | — | — |

---

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| PoolManager (6 on Ethereum) | `MapleProxy` (155 B), EIP-1967 impl slot | slot = `0x47fe…C3B5` (V500) on all 6 | factory + Globals governor timelock. Event `Upgraded(uint256,bytes)` `0xaaaa7ee6…` on the proxy, `InstanceUpgraded` on the factory. |
| StrategyManager instances | `MapleProxy`, EIP-1967 | slot → `0x8B29…C696` | strategyManagerFactory |
| Allocation / ModularAave / ModularSky instances | `MapleProxy`, EIP-1967 | slot → registered impl | their factory |
| Legacy Aave / Sky / Basic instances | `MapleProxy` (147 B), EIP-1967 | slot → `0xFc8F…E9F9` / `0xBBEe…7730` / `0x7a1E…5B73` | their factory |
| OTLM (SL2/SL3) | `MapleProxy` | slot → `0xbAD0…B241` | OTLM factory |
| WMQueue (SL2/SL3) | `MapleProxy` | slot → `0x9daf…C644` (V201) | WMQ factory |
| MapleGlobals | NonTransparentProxy | slot → `0xaFaA…26a8` (V500) | governor |
| Factories, LiquidityRouter, StrategyDeployer, PoolDeployerV5, Pools, PoolDelegateCovers | **not proxies** | impl slot = 0 | redeploy only |

---

## 7. Detection invariants & gotchas

1. **No StrategyManager exists yet.** Watch the four new factories for `InstanceDeployed` `0x8919387f…` and the StrategyDeployer for `StrategyManagerDeployed`. The first instances define the addresses to monitor.
2. **Pool cash goes straight from the Pool to the underlying strategy.** `fundStrategyManager` calls `PoolManager.requestFunds(underlyingStrategy, assets)`. The USDC `Transfer` goes Pool → underlying strategy, not Pool → StrategyManager.
3. **`AssetsDeployed` on an AllocationStrategy is the main off-chain exposure signal.** The assets leave for a `MAPLE_MANAGED_WALLET` instance. Yield and losses come back only as manual `YieldRealized` / `LossRecognized` reports. Alert on `AssetsDeployed` above a threshold and on `ValidInstanceSet` for key `MAPLE_MANAGED_WALLET`.
4. **Topic collisions — key on (emitter, topic0).** `StrategyFunded(address,uint256,uint256)` `0xb9604a9a…` is the same for Allocation and ModularAave. `ImpairmentRemoved(uint256)` `0x94f3387c…` is the same for all modular strategies and FixedTermLoan. `SetAsActive(bool)` `0x3d5d61d2…` is the same for PoolManager and StrategyManager. `RewardsClaimed` `0xfc30cdde…` is the same for legacy and modular Aave.
5. **Same name, different topic.** StrategyManager `RedemptionRequested(address,uint256)` `0x3779310b…` differs from Pool `RedemptionRequested(address,uint256,uint256)` `0x46949ee5…`. `LossRecognized()` (Aave/Sky) differs from `LossRecognized(address,address,uint256)` (Allocation). Legacy and modular `StrategyFunded` / `StrategyWithdrawal` have five different topics in total.
6. **V500 removed first-loss cover.** No `CoverDeposited` / `CoverWithdrawn` / `CoverLiquidated` events come from V500 PMs. `hasSufficientCover()` is now `pure`. A monitor keyed on those topics goes silent after block 26,284,267. That is not an outage.
7. **`triggerDefault` changed arity.** V500 PM uses `triggerDefault(address)` `0xffb43a5f`. The two-argument `0x40504ba0` is still in the bytecode only as an outgoing call to the LoanManager.
8. **Maple `Upgraded` is not EIP-1967 `Upgraded`.** Use `Upgraded(uint256,bytes)` `0xaaaa7ee6…`. The `data` holds `toVersion` (500 = `0x1f4` for V500).
9. **Bots are gated by Globals keys, not roles.** Router callers need `LIQUIDITY_ROUTER_BOT`. StrategyManager bot operators need `LIQUIDITY_BOT`. A bot cannot operate a StrategyManager whose underlying strategy has `impairedAssets() != 0`; only the strategy delegate can.
10. **`ActionExecuted.actionType` is an indexed `uint8` enum.** Decode it as 0 fund, 1 request redeem, 2 cancel, 3 process.
11. **Ethereum only.** None of these contracts is on Base or the other seven chains. Base still runs PoolManager V301 and has no strategy registry.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_PM_STRATEGY_CAP_SET          = '\xc4337e1c0960ac88a59f4bc4c791d1c34c50e4e788068ed19b44e0e02df5ece9'
TOPIC_PM_STRATEGY_MANAGER_ADDED    = '\xe949dc96022167fc8082115ea872f2c356b80ed87f05013e44a3c76f5c6bace9'
TOPIC_PM_STRATEGY_MANAGER_REMOVED  = '\x7a44bb4293aefdc93f2c5a934d80e4aba83489c8f880a352a8757a2248ad539c'
TOPIC_PM_STRATEGY_REMOVED          = '\x09a1db4b80c32706328728508c941a6b954f31eb5affd32f236c1fd405f8fea4'
TOPIC_MAPLE_UPGRADED               = '\xaaaa7ee6b0c2f4ee1fa7312c7d5b3623a434da5a1a9ce3cb6e629caa23454ab6'
TOPIC_GLOBALS_SM_ACTIVATED         = '\xa1a14befd3a48c950763e461d129a4380ff579f8c7c977c5f232310c1fc42955'
TOPIC_GLOBALS_SM_OWNERSHIP_XFER    = '\x22383f230c4a0be5f9e0484efc6de2095ab60c7654cd63bb0be632c8c62472ab'
TOPIC_GLOBALS_VALID_STRAT_DELEGATE = '\x352bfdc20340358bc42831c16717dee972a216931e432e31e72204e935eb0eb7'
TOPIC_GLOBALS_VALID_INSTANCE_SET   = '\x57c2985237d36106b3006c22a6bd79dfd8a26b3821516081b9441c92cd56b773'
TOPIC_SM_FUNDED                    = '\xa137ad0c8177aba61beb1b2d091603860bad76c6d3b3be76bea7367c19c58de4'
TOPIC_SM_REDEMPTION_REQUESTED      = '\x3779310b71beb93dce3cb4f282d1ee00e2a6c89891587b17c1842ba12f7d52a4'
TOPIC_SM_REDEMPTION_CANCELLED      = '\x9aec5cafc1451c1485e4a0099bd4dfb4c9d2bb972b4e5c798da07db8323deaa3'
TOPIC_SM_REDEMPTION_PROCESSED      = '\xf9f22dbb7dd6f69e7cd372268cb6067f61049833233f2653a00e171b4ac04a35'
TOPIC_SM_POOL_MANAGER_CAP_SET      = '\x6a39752ad6bf36ecd7fd6e804a42c91f6425e4c6d2b2d8f059e132e4d23d242a'
TOPIC_SM_LIQUIDITY_CAP_SET         = '\xe39ef0330bd7b5f0bc634bc7a2fd027883b6ae722d9485fda9061ea87c5f019e'
TOPIC_SM_UNDERLYING_STRATEGY_SET   = '\xc4de5969230b6e1a5271556063cd3dcfa0b5e7ac9749a7242b091b561c223532'
TOPIC_ROUTER_ACTION_EXECUTED       = '\xa46e5e78bfe815d8f44b02a54f9d18c58b7a435bc9c73c2aae992826c95fe473'
TOPIC_DEPLOYER_SM_DEPLOYED         = '\xd86a70899bbf7799d77564d7aba7ce5f114dfc64bb6563561b0555da3d613cd6'
TOPIC_POOL_DEPLOYED_V5             = '\x8307758e931f63bfd57ea77a5a50503e0536b16afa4dafdda14fc1bab57e38b1'
TOPIC_ALLOC_ASSETS_DEPLOYED        = '\x8694c6e3190e2c3f94de9e1e582500d8cf5ea6d6d03a676e18ecf2864501b870'
TOPIC_ALLOC_ASSETS_RETURNED        = '\x34f04a2d9246787577a75dc4677f025ac8e0fac53d5e6c1b0eb391b6af56b03e'
TOPIC_ALLOC_YIELD_REALIZED         = '\xbcc8c665985e44525378c7f609dcf37ad9a5cf547ba518b9cab7d4dbd845b827'
TOPIC_ALLOC_LOSS_RECOGNIZED        = '\xb477a35177f736ca0c21727c1b0494e580983172c6d469269a8786150fd75ca3'
TOPIC_ALLOC_STRATEGY_WITHDRAWN     = '\xe8da4fd93dfef82d36835b8bcc5bb2e5eab810078bb85c3dd5e348eaf3f3726b'
TOPIC_STRAT_FUNDED_ALLOC_AAVE      = '\xb9604a9ad6dcb570b9913035d6d312dffa9c0bfc935d16bd0d4c9adec2f96ea2'  -- Allocation & ModularAave
TOPIC_STRAT_FUNDED_SKY             = '\xf3a2537583064f88f4c6122997a696a0cbb3cf497c6e23f23cfbca871bef7dd2'
TOPIC_STRAT_WITHDRAWAL_AAVE        = '\xd5ad0f046bd35f48b421a3e575435de38cea1980177b1c6da935d2f26049f3fa'
TOPIC_STRAT_WITHDRAWAL_SKY         = '\x88f0c01d2402991a2098e1cf989cb2c54cefe3b20ccb83c55989866f419a6ff5'
TOPIC_STRAT_IMPAIRED               = '\x3d1e299f39b6e4e65aaa2cbde0955f28b32a6c26830ca216256616506eceeebd'
TOPIC_STRAT_IMPAIRMENT_REMOVED     = '\x94f3387cabdaf912caff343ac490a3056bb348c474be2c718b9f59f56f1b7d97'  -- also FTL
TOPIC_STRAT_LOSS_RECOGNIZED_DEFI   = '\x456a2c591797fc5c7f65b85461f55bf486edd2bb464bbdb7b42577dfd74dbb42'
TOPIC_STRAT_FEES_COLLECTED         = '\xa6b2ff5d1ba994844f597ecc1b29116e234378f7614499c6eaa93d84b9de0d7e'
TOPIC_LEGACY_STRAT_FUNDED_1        = '\x3d6565101a1c6c13991358f5851c7af96dfda23edf4f1391da423b26c1d3df75'
TOPIC_LEGACY_STRAT_FUNDED_2        = '\xdf6bc5d53caf80630bcba0ff64b0f79c973ce3cb0c3edf552df7e00951519b54'
TOPIC_LEGACY_STRAT_WITHDRAWAL_1    = '\x1e3b88c775a5ef3ca37ef9424a3dde5b6328b543e7ea0d0250804698030bf29a'
TOPIC_LEGACY_STRAT_WITHDRAWAL_2    = '\x7f9a30215421fe39f77e4b9088e3f8d5977897d39e5696eccd312f7899d00085'
TOPIC_LEGACY_STRAT_IMPAIRED        = '\x1b4bdf15e9083497b4929bf7a5dbe5bc33142228d131e43e84a546ecb0518df1'
TOPIC_FACTORY_INSTANCE_DEPLOYED    = '\x8919387fe006fdc29a3dfcc183071d7974bc03747fedb0019630f1e13f85cc64'
TOPIC_FACTORY_INSTANCE_UPGRADED    = '\xfbb4f36b70dba8ecedc8b38361f44f1b0c61e04ec4e0ccf620649dc558573f5f'
TOPIC_FACTORY_IMPL_REGISTERED      = '\xe69962526b7f07862bf85663f861564361295f9601236fbbe056591eb1b63f3b'
-- ===== Selectors (chain-agnostic) =====
SEL_PM_ADD_STRATEGY_MANAGER        = '\xf122073e'   -- addStrategyManager(address)
SEL_PM_REMOVE_STRATEGY_MANAGER     = '\xb57ee836'   -- removeStrategyManager(address)
SEL_PM_SET_STRATEGY_CAP            = '\xeb824c25'   -- setStrategyCap(address,uint256)
SEL_PM_REQUEST_FUNDS               = '\x494666b6'   -- requestFunds(address,uint256)
SEL_PM_TRIGGER_DEFAULT_V500        = '\xffb43a5f'   -- triggerDefault(address)
SEL_SM_FUND                        = '\x181b19a6'   -- fundStrategyManager(address,uint256,bytes)
SEL_SM_REQUEST_REDEEM              = '\x65b89f9f'   -- requestRedeem(address,uint256)
SEL_SM_PROCESS_REDEMPTION          = '\xc8dbe7a6'   -- processRedemption(address,uint256,bytes)
SEL_ROUTER_EXECUTE_ACTIONS         = '\x5e49a51d'   -- executeActions((uint8,address,address,uint256,bytes)[],uint256)
SEL_DEPLOYER_DEPLOY                = '\xdad52ef5'   -- deploy(address,address,uint256,bytes,bytes)
SEL_POOL_DEPLOYER_V5_DEPLOY_POOL   = '\x178aee6c'
SEL_STRAT_FUND_UNDERLYING          = '\x0c9e543c'   -- fundUnderlyingStrategy(uint256,bytes)
SEL_STRAT_WITHDRAW_UNDERLYING      = '\xa6b221a2'   -- withdrawFromUnderlyingStrategy(address,uint256,bytes)
SEL_ALLOC_DEPLOY_ASSETS            = '\x73fb6c3a'   -- deployAssets(uint256,bytes)
SEL_ALLOC_RETURN_ASSETS            = '\xc5f0ec55'   -- returnAssets(uint256,address,bytes)
SEL_ALLOC_REALIZE_YIELD            = '\x7d2598fb'   -- realizeYield(uint256,uint32,bytes)
SEL_ALLOC_RECOGNIZE_LOSS           = '\x38c9be44'   -- recognizeLoss(uint256,address)
SEL_STRAT_IMPAIR                   = '\x8318369e'   -- impair(uint256)
SEL_GLOBALS_SET_VALID_STRAT_DELEG  = '\x9b1f1fea'   -- setValidStrategyDelegate(address,bool)
-- ===== Addresses (Ethereum, chain ID 1) =====
ETH_STRATEGY_MANAGER_FACTORY       = '\xc72a81c771bcfdd3c60c642dadba1896760747f4'
ETH_ALLOCATION_STRATEGY_FACTORY    = '\x7c9bb6ddf53d6ada9592f478cf224034c1fc1126'
ETH_MODULAR_AAVE_STRATEGY_FACTORY  = '\x2b1e33ed3d742be945a6a81b581d824c9fba6cd7'
ETH_MODULAR_SKY_STRATEGY_FACTORY   = '\xb9965c97bd7a64cb8da10e947a2ade8b32396ca0'
ETH_AAVE_STRATEGY_FACTORY          = '\x01ab799f77f9a9f4dd0d2b6e7c83dcf3f48d5650'
ETH_SKY_STRATEGY_FACTORY           = '\x27327e08de810c687687f95bfce92088089b56db'
ETH_BASIC_STRATEGY_FACTORY         = '\x876d54dbf61473ca169b89b95344a14e81f37afe'
ETH_LIQUIDITY_ROUTER_V100          = '\x28bb4ff6ac910d9dcea90e11625559b8345c0588'
ETH_STRATEGY_DEPLOYER_V100         = '\x5e9d93016b2f5a2920b56efdb784fba4099100cd'
ETH_POOL_DEPLOYER_V5               = '\x0efd7a4b98a4ec8bf7d7ec9f30a3274b0b51c075'
ETH_POOL_MANAGER_V500_IMPL         = '\x47feaa096efe5d44ed9378a29705c47c60ffc3b5'
ETH_GLOBALS_V500_IMPL              = '\xafaaa45bc170384f07188d04c6412fa3716826a8'
ETH_SL2_USDC_POOL                  = '\x6a956aa2d183b6b5e9d9f64b1c137098bef627ea'
ETH_SL2_USDC_POOL_MANAGER          = '\x462e6203176b41b741b3dd03db14ffb29fcfa693'
ETH_SL2_USDC_OTLM                  = '\x7d4c8157c29baff70d5d08ce57eaf32820415e12'
ETH_SL2_USDC_WMQ                   = '\xb84a4af193ba7b2ecfc8e65a099e0f01ebbbf6f4'
ETH_SL3_USDC_POOL                  = '\xa7f5df53165faeb890ae37f4b0f973a42d166222'
ETH_SL3_USDC_POOL_MANAGER          = '\xb0ead5d35c07f9ee6fc4e2c82b929ca39151e98d'
ETH_SL3_USDC_OTLM                  = '\x7ec236b4b1c6ca0d87405057714ead0f63ed8849'
ETH_SL3_USDC_WMQ                   = '\x3c139c88d45cd17d85f75371de4de4368bfc18fd'
```

---

## 9. Verification & sources

How the constants in this file were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(sig)` from the verbatim interface sources. Enum `ActionType` is hashed as `uint8`. Struct `Action` is hashed as `(uint8,address,address,uint256,bytes)`. Every event topic was found as a `PUSH32` immediate and every selector as a `PUSH4` immediate in the matching deployed implementation (StrategyManager, AllocationStrategy, ModularAave, ModularSky, legacy Aave/Sky/Basic, LiquidityRouter, StrategyDeployer, PoolDeployerV5, PoolManager V500, Globals V500).
- **Live logs:** `StrategyCapSet`, `StrategyRemoved`, `Upgraded(uint256,bytes)`, `Initialized`, `StrategyAdded` (PoolManagers), `ValidInstanceSet`, `ValidStrategyDelegateSet`, `CanDeployFromSet`, `PoolManagerActivated` (Globals), and `ImplementationRegistered` / `DefaultVersionSet` (the four new factories) were seen in blocks 25,907,000 to 26,307,000. The V500 upgrade tx is `0x81854c475b5ddbc15526bc185fe9b5064275acf396eea20e8315ea94eb2b4ca4` (block 26,284,267).
- **Addresses:** parsed from `MapleAddressRegistryETH.sol` and confirmed via `eth_getCode`. Implementations read from the EIP-1967 slot. Strategy lists read via `strategyListLength()` and `strategyList(uint256)`. Registered implementations confirmed from `ImplementationRegistered` logs.
- **Chain coverage:** `eth_getCode` returned `0x` for the router, deployer, five factories and PM V500 impl on Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc.
- **Not verified live:** no StrategyManager, Allocation, ModularAave or ModularSky instance exists yet, so their events are confirmed only in bytecode, not in logs.

Authoritative sources:
- [maple-labs/address-registry](https://github.com/maple-labs/address-registry) — `contracts/MapleAddressRegistryETH.sol`, `contracts/MapleAddressRegistryBASEL2.sol`
- [maple-labs/strategy-manager](https://github.com/maple-labs/strategy-manager) · [maple-labs/allocation-strategy](https://github.com/maple-labs/allocation-strategy) · [maple-labs/defi-strategies](https://github.com/maple-labs/defi-strategies) · [maple-labs/maple-strategies](https://github.com/maple-labs/maple-strategies)
- [maple-labs/pool-v2](https://github.com/maple-labs/pool-v2) · [maple-labs/globals-v2](https://github.com/maple-labs/globals-v2) · [maple-labs/maple-proxy-factory](https://github.com/maple-labs/maple-proxy-factory)
- Explorers: [Etherscan LiquidityRouter](https://etherscan.io/address/0x28Bb4fF6ac910D9DceA90e11625559b8345c0588) · [Etherscan StrategyManagerFactory](https://etherscan.io/address/0xc72A81c771BCFdD3C60C642dAdBa1896760747F4) · [Etherscan SL2 Pool](https://etherscan.io/address/0x6a956aA2D183b6b5E9d9F64b1c137098BeF627Ea)
