# Polymarket V2 PositionManager system — Topics, Selectors, Addresses (Polygon PoS)

**Status:** verified against live Polygon RPC and the canonical `Polymarket/polymarket-v2-external` repo on 2026-10-30.
**Scope:** the next-generation Polymarket contracts on Polygon PoS (137): PositionManager (own ERC-1155 ledger), the Binary / NegRisk / Combinatorial modules, Exchange, Router, AutoRedeemer, OracleAggregator and its reporter modules. Topics and selectors are chain-agnostic. Addresses are network-specific. **Polygon-only.** No address has code on the other eight chains (§4).

Naming: the repo calls this system "Polymarket V2". The `clob-client-v2` SDK calls its exchange `exchangeV3`. It is a third exchange, after CTFExchange (V1) and CTFExchangeV2.

This system **does not use the Gnosis CTF**. `PositionManager` is a new ERC-1155 token ledger. A position id is a structured bit field: `[moduleId(8) | baseHash(128) | arity(16) | reserved(64) | resolutionChain(16) | conditionIndex(16) | outcomeIndex(8)]`. The top byte names the module (1 = Binary, 2 = NegRisk, 3 = Combinatorial). Collateral is pUSD (`exchange_v2.md`). Legacy CTF positions move in through the `migratePositions` functions of the Binary and NegRisk modules.

Every contract is a **UUPS proxy** (Solady ERC-1967, 61-byte runtime) behind a vanity address. The owner of all of them is `0x47ebfac3353314c788b96cdcbf41daadfe03629c`. Activity on 2026-10-30 is real but small: about 30 `OrderFilled` on the Exchange in a 40-block sample, versus about 2,700 on the CTF Exchange V2 pair. The source also has a Chainlink CCIP bridge (`CcipBridge`) for a hub-and-spoke layout with Polygon as hub. **No bridge or spoke deployment was found.**

---

## 0. Contract families & versions

| Contract | Role | moduleId |
|----------|------|----------|
| **PositionManager** | ERC-1155 ledger. Registers modules. Mint / burn only by modules. | — |
| **BinaryModule** | YES/NO markets. Split / merge / redeem. Legacy CTF migration. | 1 |
| **NegRiskModule** | Multi-outcome events. Horizontal split / merge, NO-basket convert. Legacy NegRiskAdapter migration. | 2 |
| **CombinatorialModule** | Parlay-style conditions built from legs of other markets. | 3 |
| **Exchange** | CLOB settlement on PositionManager tokens. EIP-712 orders. | — |
| **Router** | User entry point. Pre-transfers tokens and calls the modules. | — |
| **AutoRedeemer** | Batch redemption of resolved positions for users. | — |
| **OracleAggregator** | Resolution state machine: reporters, disputers, arbitrator, liveness. | — |
| **OOReporterModule** / **ChainlinkReporterModule** / **EOAReporterModule** | Reporter plug-ins (UMA OO, Chainlink Data Streams, trusted EOAs). | — |
| CollateralToken (pUSD) + ramps | Shared with CTF Exchange V2. See `exchange_v2.md`. | — |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Common to every proxy here (Solady `OwnableRoles` + `UUPSUpgradeable` + `Initializable`): `OwnershipTransferred` `0x8be0…57e0`, `OwnershipHandoverRequested` `0xdbf3…7e1d`, `OwnershipHandoverCanceled` `0xfa7b…3c92`, `RolesUpdated` `0x715a…fe26`, `Upgraded` `0xbc7c…2d3b`, `Initialized(uint64)` `0xc7f5…81d2`. Full values in §7.

### 1.1 PositionManager
| topic0 | Event |
|--------|-------|
| `0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31` | `ApprovalForAll(address indexed, address indexed, bool)` |
| `0x26bdfbc198f2d30945bd9a2384cb5d3b97a1cfe249d1538aa803c7fbb79681cb` | `CrossModuleAuthSet(address indexed, bool)` |
| `0xa7839c29a2c3fc5208115d9be22d20b2a981203a3428218dd76c76d690254499` | `ModuleAdded(uint256 indexed, address indexed)` |
| `0x854cff40228579f66eb3dd26b84ef9d8bb9f43b2a6a03495f29fae9b2827d987` | `ModuleRemoved(uint256 indexed, address indexed)` |
| `0x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb` | `TransferBatch(address indexed, address indexed, address indexed, uint256[], uint256[])` |
| `0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62` | `TransferSingle(address indexed, address indexed, address indexed, uint256, uint256)` |

### 1.2 Exchange
| topic0 | Event |
|--------|-------|
| `0x55bb3cade9d43b798a4fe5ffdd05024b2d7870df53920673bfc7e68047cd0ab1` | `FeeCharged(address indexed, uint256)` |
| `0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee` | `OrderFilled(bytes32 indexed, address indexed, address indexed, uint8, uint256, uint256, uint256, uint256, bytes32, bytes32)` |
| `0xb766aa470f20b094f26a9a14ea5bf63a60af51703c15776e2e739b6a0428adf6` | `OrderPreapprovalInvalidated(bytes32 indexed)` |
| `0xe92c22722d9c284034b6c9f5aaec018edb3e593c0e084900b6b9d390a1182a0b` | `OrderPreapproved(bytes32 indexed)` |
| `0x174b3811690657c217184f89418266767c87e4805d09680c39fc9c031c0cab7c` | `OrdersMatched(bytes32 indexed, address indexed, uint8, uint256, uint256, uint256)` |
| `0x203c4bd3e526634f661575359ff30de3b0edaba6c2cb1eac60f730b6d2d9d536` | `TradingPaused(address indexed)` |
| `0xa1e8a54850dbd7f520bcc09f47bff152294b77b2081da545a7adf531b7ea283b` | `TradingUnpaused(address indexed)` |
| `0x8c8acf678b7cd311e3b5768c92794d63943684862fdea390856e14d9e2a9ef88` | `UserPauseBlockIntervalUpdated(uint256, uint256)` |
| `0xa3e76126f19eb25001b29726d2a9502b6377938633d2d6a955107dd442e7a14a` | `UserPaused(address indexed, uint256)` |
| `0x1419d4111b5c8636aecff843bf618525f4f8e1aa6898a14357021d68dde8af12` | `UserUnpaused(address indexed)` |

Same signatures and topic0 as CTF Exchange V2. Here `tokenId` is a PositionManager position id.

### 1.3 BinaryModule
| topic0 | Event |
|--------|-------|
| `0xd310e554d3fd5335d0aca4ef77d4859f65a3e728008329aef6db44ebaf78f1e1` | `BridgePositionMinted(address indexed, uint256 indexed, uint256)` |
| `0x06735e2794e58fa40f90f6d752f9a94f47d33c04a1128e995673886ec726c3ae` | `BridgePositionsBurned(uint256[], uint256[])` |
| `0xe560c1a2847d4cf2e66de11fe592605556989449f38cc3ab96e2e287daa68caa` | `ConditionResolved(bytes31 indexed, uint256[])` |
| `0x7a07cc3efaf017520e4ad55e66052f0398632c810a3fab73e58e4c7050746825` | `LegacyCollateralSettled(address indexed, address indexed, uint256)` |
| `0x0da49435dfd3b856758ee0b1a2500f1e8062fed24dd654594af9fa163cc5bcb4` | `MigrationConditionRegistered(bytes31 indexed, bytes32 indexed)` |
| `0xf87100968b0fe70751acf87590ffac515231c5b999cba36e6820c7d312dcc8af` | `MigrationResolved(bytes31 indexed, bytes32 indexed, uint256, uint256, uint256, uint256)` |
| `0xe8d329e97d555e1e9d0da49d3b12d41a966458eee02ff4c869e54c6711d7c80b` | `PositionMigrated(address indexed, bytes31 indexed, uint256 indexed, uint256, uint256)` |
| `0x4fd474b703f46b453536518b4cbc159dfbea6fd663233763d321a9bc8ccdf97f` | `PositionRedeemed(address indexed, uint256 indexed, address indexed, uint256, uint256)` |
| `0xf233f7be4ce81130a78e8eb2fa626497586c56094d27bfec2e196471e9c60301` | `PositionsMerged(address indexed, bytes31 indexed, address indexed, uint256)` |
| `0xb6a6b8b17a43b07b9359dd12d304e42077eede9e672f8646144842c8604582a4` | `PositionsSplit(address indexed, bytes31 indexed, address indexed, address, uint256)` |
| `0xdc9b357849b1f270abed270e8b7b026ba0a6c0a0137ad63fe62595e9a5ef338e` | `ResolutionPaused(bytes29 indexed, uint256)` |
| `0x7c4b1aa57f3709ea7889a5749c87fea12721ab4484993ecc65c07cba4b99bd46` | `ResolutionUnpaused(bytes29 indexed)` |
| `0x2883146a9b6f97f0c11f47a78214d9b6763323144fa6b91962867087cc6ced3d` | `ResolverPaused(address indexed, uint256)` |
| `0x65ac3d2bec00c5066617c836d9abb95e150f3373fdec6bd5a86ad458fe48bab0` | `ResolverUnpaused(address indexed)` |
| `0x669c053fe14f2493990c0c90d8d2870cd45e2630b34b8a2b4f02869301987713` | `ResultReported(address indexed, bytes31 indexed, uint256[])` |

### 1.4 NegRiskModule (adds to the BinaryModule set)
| topic0 | Event |
|--------|-------|
| `0x9bdf886b29ff2e03765aa003845c79f3700b39f9628db119aeeaac5d0fd73306` | `EventPrepared(bytes29 indexed, uint256, bytes32)` |
| `0xbfdd473162148936b92fc229a1d66bcded27968d61ec543cbd86b433fd2d7b4b` | `HorizontalMerge(address indexed, bytes29 indexed, address indexed, uint256)` |
| `0x9dbee20759d31417e9b0d739e07904f87139522ce89cf2f6ad78e299067674ce` | `HorizontalSplit(address indexed, bytes29 indexed, address indexed, uint256)` |
| `0x975e919c2cacb75b8a9fc78ddf455a5211812df2f388c877c8d3adfe156e2779` | `PositionConverted(address indexed, bytes29 indexed, address indexed, uint256, uint256)` |
| `0x7b4e633936952f2babe4b4b548a8ccb384cdfdf1a95247fbacd18e387b490502` | `RemainingConditionsDerivableAsNo(bytes29 indexed)` |
| `0x5bea118d92630445b0b401b6883731630ed870edf2f259980efe977dfc128b36` | `SyntheticConditionDerivableAsYes(bytes29 indexed, bytes31 indexed)` |

### 1.5 CombinatorialModule
| topic0 | Event |
|--------|-------|
| `0x51c89d7ee51515f7235e928930da7f81be08212bc14870a6a37c64744492db96` | `CombinatorialConditionPrepared(bytes31 indexed, uint256[])` |
| `0x43f975db4a407bc85816b44922ab015dc6b990ead8d39099398c03a258e70bce` | `Compressed(address indexed, uint256 indexed, uint256 indexed, address, uint256, uint256, uint256)` |
| `0x93d226ffc1c7cc4176213b47c5966043f735f6d3c3e5c092fd619ff1fe5d3bd3` | `ConvertedOnEvent(address indexed, bytes31 indexed, bytes29 indexed, uint256, address[], uint256)` |
| `0x348359e703372b7a9511e430c7e4db280578fb31a773e6c075ef7328cec34da6` | `ConvertedToYesBasket(address indexed, bytes31 indexed, address[], uint256)` |
| `0x6c14fdbd417e901138c803349c26df1115726b468ebc6142d39f7b9aef7f17fe` | `Extracted(address indexed, bytes31 indexed, bytes31, bytes31, address, address, uint256)` |
| `0xbb32ee0762f37f8b1ace698804f2f31be362ada55b233e359de04fefd164819f` | `Injected(address indexed, bytes31 indexed, bytes31, bytes31, address, uint256)` |
| `0x09e4439e8186f011e12eb04a93f9d5477f79e7479375c8108d5e38e234a84ff6` | `MergedFromYesBasket(address indexed, bytes31 indexed, address, uint256)` |
| `0x532e91b101b4cdffc29d79b6ca1f3ae8690d4846c75145039161f4a22c55019a` | `MergedOnCondition(address indexed, bytes31 indexed, bytes31, bytes31, address, uint256)` |
| `0xb219258fc090ae084a29f0659e7e2947568de5694939da14181645a55f03f870` | `MergedOnEvent(address indexed, bytes31 indexed, bytes29 indexed, address, uint256)` |
| `0x1a07698f7dd85df4924787e65bad71fa08c54c04700b09c8c648c6e797540202` | `SplitOnCondition(address indexed, bytes31 indexed, bytes31, bytes31, address, address, uint256)` |
| `0x24ddc4002a06123a2abb28bb44889b496299eac2a85e9ccf87514396dda1d063` | `SplitOnEvent(address indexed, bytes31 indexed, bytes29 indexed, address[], uint256)` |
| `0x49c5e71a70e54b164c70c3345b2f3ca11fbad1c05a76146be4c4e849f992658b` | `Unwrapped(address indexed, uint256, uint256, address, uint256)` |
| `0xee943741871b99130d74367c491afe27aa9324108e10ae51d0a8f9e8cd9f9eff` | `Wrapped(address indexed, uint256, uint256, address, uint256)` |

`Wrapped` / `Unwrapped` here are `(address,uint256,uint256,address,uint256)`. They differ from the pUSD events of the same name.

### 1.6 Router
| topic0 | Event |
|--------|-------|
| `0xf96012c33cad3242c6e56a0c9a4d003fdf70ca495dff976cff4295e03ffe3b86` | `CombinatorialCollateralReturned(address indexed, uint256)` |
| `0x69e13930513c83de572f0fdb24c4d1c3f8f8f77b841d792e0b89d81588581716` | `RouterHorizontalMerge(address indexed, bytes29 indexed, uint256)` |
| `0xd470f36e1347dd1dbb72529813b06678ff587a767ea8eae6bc3906b24e6a08ab` | `RouterHorizontalSplit(address indexed, bytes29 indexed, uint256)` |
| `0x87e385df53b4ec94408ffc0ae0728448abc68c13f48490c9e614af5262600282` | `RouterPositionConverted(address indexed, bytes29 indexed, uint256, uint256)` |
| `0x81b466b1b365aea7f5664f9a2d8b3a8591d3244acffb5134355ad4da7fe2366a` | `RouterPositionRedeemed(address indexed, uint256 indexed, uint256)` |
| `0x04373eecd7397b9318ae470769098aaab46f432620d95b0d84fc2297a415704c` | `RouterPositionSplit(address indexed, bytes31 indexed, uint256)` |
| `0x8eb905ea8eb4589289705df45fe31e6d4a35385a223b60c259691cc86dbfb982` | `RouterPositionsMerged(address indexed, bytes31 indexed, uint256)` |

### 1.7 AutoRedeemer
| topic0 | Event |
|--------|-------|
| `0xb434294b5904213c83a167af0068ab82637c6fd4fac945e2abc74ed8d3f4d52a` | `BinaryRedemption(address indexed, bytes32 indexed, uint256)` |
| `0x74a51ebefec30281ec6849b727ec7916f9b1a3e5e148d6771d98315215b38b96` | `NegRiskRedemption(address indexed, bytes32 indexed, uint256)` |
| `0xeebddeddf4ae1ee54a48517af27958e7666d69c7ba2e3e7c2b0ff87ef5f4491e` | `Redemption(address indexed, uint256 indexed, uint256)` |

### 1.8 OracleAggregator
| topic0 | Event |
|--------|-------|
| `0x6141166d67d9e01ddaf66f0aa3b4f57290d442fa83745ddf768aa606d0838270` | `ArbitrationTriggered(bytes32 indexed)` |
| `0xb88d17e2c533909318ad5841d80e7acb1fdf0dbdbcc9fd1c2b8420e00b93f8f8` | `ArbitratorHookFailed(bytes32 indexed, address indexed)` |
| `0xa159b7e0d335e3dd77d4204ac81d6fa58f27a4d3481f35bcfdfc5d9be250bf14` | `ArbitratorModuleSet(bytes29 indexed, address indexed)` |
| `0xd54c991263cd8bb37409a5ee463709e8e3e2483ba755f2a6a99ce38a4c1601e6` | `DisputerModuleAdded(bytes29 indexed, address indexed)` |
| `0x1abf75d24ad7ea6438fcd7eba8023e4ef38b7dcd60b430f7e44fdae9a9283815` | `DisputerModuleRemoved(bytes29 indexed, address indexed)` |
| `0xae7e76bdf56027b25e2c628816e7fc1528e769899c30cac15868e657d173b452` | `FinalizerSet(bytes29 indexed, address indexed)` |
| `0x971be26fcde2df81b2b63dfb7fa1d2294b524eb1896b10e5228d9c154a30af09` | `GlobalPauseSet(bool)` |
| `0x9e2a844f43a3d18a45e8f1b0440095036c12635d9db49395b30780cf7422a6d9` | `LivenessWindowSet(bytes29 indexed, uint32)` |
| `0xc51886d63e98dce9b94e65fdd117981be37c579382c2306e29fbe38a9ad2868b` | `MarketPauseSet(bytes29 indexed, bool)` |
| `0xb8e19bf6c02c74c20cfc00567a3be20e29f089d4ed11da6726011dbbcd2ee787` | `OutcomeProposed(bytes32 indexed, bytes32, uint256[])` |
| `0x276e741ebae8abaf0570c9ed0966d2d2ad14ced02a2f436d9fd882a20e249aca` | `ProductSpecificationUpdated(bytes32 indexed, string, string, uint64, uint64)` |
| `0x6dfa2acc6f02c2512d0bea4c4ab45f5f781fe2abb365a6eb04ab2b2ddcd66402` | `ReporterConflict(bytes32 indexed, bytes32 indexed, bytes32 indexed, uint256[])` |
| `0xc14be9714cff6af699b94f2fa548a5a69ca0997966844840847cf531f82102e0` | `ReporterModuleAdded(bytes29 indexed, address indexed)` |
| `0xc963d7e540a2eabd6f748feea23fc08ec8a139eb6e5e62d7b233bdedd31526c6` | `ReporterModuleRemoved(bytes29 indexed, address indexed)` |
| `0x3f540a7f583087a9dcc5ae409a9757c451baede9df196f29fb15fe29fe2662c9` | `RequestInitialized(bytes29 indexed, address, uint256, uint256, uint16, uint8, address, uint32, address)` |
| `0x1e15c34094c71de8f5cafd2ab5e84ffb03d5b44394eb40632b3a4dce1c4311a0` | `RequestResolved(bytes32 indexed, bytes32, address indexed)` |
| `0x6a2ba1a9b0df571f4ca699d337da6ecff0b0362663edbfddca1cb3a3ac1c06bf` | `RequestRulesUpdated(bytes32 indexed, uint256)` |
| `0xbc5cfd3515610af0e2196d410032fb4ab213d3cee8e295a4ae2a6267d061bad0` | `ResultDisputed(bytes32 indexed, address indexed)` |
| `0x553ed0b8f6413e4ecbf8434f6ca75a7752f7620c095aedd5929c6e8212149396` | `ResultReported(bytes32 indexed, address indexed, bytes32, uint256)` |
| `0xeb2f63efe5d8d4ddfbb3ee2e77f31460c93206cae5c1800897b8830b84471091` | `RuleAdded(bytes32 indexed, uint256, uint256, bytes)` |

### 1.9 Reporter modules
| topic0 | Event |
|--------|-------|
| `0x94b241e14651a9658c51a45c82167e4f25ac3d3e7f8a2beae9d10b1ba07a94a0` | `AggregatorSet(address indexed)` |
| `0xa4f237d18e5dbeb37a898a168eda3563460d4e4a6c8a19a7cec931ccee81c537` | `OOReporterRequestCreated(bytes32 indexed, bytes32)` |
| `0xbd38647ecefb296b23744d285f2b49943cf5e86d01de4271390f24f6dde12acf` | `OOReporterResultReported(bytes32 indexed, int256, bytes32)` |
| `0xf2165347e8cf6cbe46f0d7c9d8cb0a93acfe4fba186d5213bcf03eee7febbd3a` | `OOReporterRulesForwardFailed(bytes32 indexed, bytes)` |
| `0x23edd263567242c6caacfa756e88698d5771b6eb6d83ba42419ff944bc24c8d3` | `OOReporterRulesForwarded(bytes32 indexed, bytes)` |
| `0xac441911eac0e33a5e77f3fc8534bcb4c3a2814dc0e9a5f77e9a8458c5a360de` | `RequestInitialized(bytes31 indexed)` |

ChainlinkReporterModule adds:
| topic0 | Event |
|--------|-------|
| `0xb1d3fd1043ba7e8aa4dc147ae75d3b4d9c9d05e5087cae2e72765ef47d84678f` | `FeedIdUpdated(bytes32 indexed, bytes32)` |
| `0x971be26fcde2df81b2b63dfb7fa1d2294b524eb1896b10e5228d9c154a30af09` | `GlobalPauseSet(bool)` |
| `0xd0d8fcba5b80285328e7548929f62b04b74231003b83f988b2534b12782987eb` | `PriceSourceUpdated(address indexed, address indexed)` |
| `0xdc53ded0d26e27b31f5cf0e3d4c9c4bbf186d45abf6b5f88af0b1534bfbe677f` | `RequestReported(bytes29 indexed, bytes32 indexed, int192, int192, uint256)` |

EOAReporterModule adds:
| topic0 | Event |
|--------|-------|
| `0x5a0e1b88d8fab2783c9b8319efb377157ba306962b9b5cb72532fe4c1eacd52c` | `Reported(bytes32 indexed, address indexed, bytes32)` |
| `0x6bf8245b5da690a960a87fd564ee12cb93035e5878548d8e0b90309dde55a76a` | `ReporterAdded(bytes29 indexed, address indexed)` |

### 1.10 topic0 collisions (disambiguate by emitter)
- `ResultReported`: modules use `(address,bytes31,uint256[])` (`0x669c…7713`). OracleAggregator uses `(bytes32,address,bytes32,uint256)` (`0x553e…9396`).
- `RequestInitialized`: aggregator `(bytes29,…)` (`0x3f54…62c9`) vs reporter modules `(bytes31)` (`0xac44…60de`).
- `GlobalPauseSet(bool)`: OracleAggregator and ChainlinkReporterModule.
- `PositionsSplit` / `PositionsMerged` / `PositionRedeemed`: all three modules.
- `OrderFilled` / `OrdersMatched` / `FeeCharged` / `TradingPaused`: Exchange here and CTF Exchange V2.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

`ORDER2` = `(uint256,address,address,uint256,uint256,uint256,uint8,uint8,uint256,bytes32,bytes32,bytes)` (same as CTF Exchange V2). `TakerAmounts` = `(uint256 takerFillAmount, uint256 takerReceiveAmount, uint256 takerFeeAmount)`. `bytes31` = condition id, `bytes29` = event id.

### 2.1 Exchange
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0fb25ba4` | `matchOrders((uint256,address,address,uint256,uint256,uint256,uint8,uint8,uint256,bytes32,bytes32,bytes),(uint256,address,address,uint256,uint256,uint256,uint8,uint8,uint256,bytes32,bytes32,bytes)[],uint256[],uint256[],(uint256,uint256,uint256))` | `matchOrders(ORDER2, ORDER2[], makerFills[], makerFees[], TakerAmounts)`. Operator only. |
| `0xe75cf6e5` | `matchOrdersAndPrepareCombinatorial((uint256,address,address,uint256,uint256,uint256,uint8,uint8,uint256,bytes32,bytes32,bytes),(uint256,address,address,uint256,uint256,uint256,uint8,uint8,uint256,bytes32,bytes32,bytes)[],uint256[],uint256[],(uint256,uint256,uint256),uint256[])` | Operator. Prepares a combinatorial condition, then matches. |
| `0xe3a5ced5` | `preapproveOrder((uint256,address,address,uint256,uint256,uint256,uint8,uint8,uint256,bytes32,bytes32,bytes))` | Emits `OrderPreapproved`. |
| `0x437f1994` | `invalidatePreapprovedOrder(bytes32)` | Emits `OrderPreapprovalInvalidated`. |
| `0x1031e36e` | `pauseTrading()` | Admin. Emits `TradingPaused`. |
| `0x456068d2` | `unpauseTrading()` | Admin. |
| `0xc0c3132c` | `pauseUser()` | Self-pause. Emits `UserPaused`. |
| `0x9870d7fe` | `addOperator(address)` | Admin. Emits `RolesUpdated`. |
| `0xbf5a5595` | `getLegacyPositionId(bytes32,uint256)` | view. CTF position id of a migrated condition. |

### 2.2 PositionManager
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1ed86f19` | `addModule(address)` | Owner / admin. Emits `ModuleAdded`. |
| `0xd8e55e14` | `removeModule(uint256)` | Emits `ModuleRemoved`. |
| `0x56c35ef3` | `setCrossModuleAuth(address,bool)` | Emits `CrossModuleAuthSet`. |
| `0x156e29f6` | `mint(address,uint256,uint256)` | Module only. |
| `0x0ca83480` | `batchMint(address,uint256[],uint256[])` | Module only. |
| `0xb390c0ab` | `burn(uint256,uint256)` | Module only. |
| `0x20ec271b` | `batchBurn(uint256[],uint256[])` | Module only. |
| `0xfbc37ca9` | `unsafeTransferFrom(address,address,uint256,uint256)` | Transfer without receiver hook. |
| `0x4028e8ea` | `unsafeBatchTransferFrom(address,address,uint256[],uint256[])` | Batch transfer without receiver hook. |
| `0xf242432a` | `safeTransferFrom(address,address,uint256,uint256,bytes)` | ERC-1155. |
| `0x00fdd58e` | `balanceOf(address,uint256)` | view |
| `0x4c619e4c` | `getPayout(uint256,uint256)` | view |

### 2.3 Modules (Binary / NegRisk / Combinatorial)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2d20cffd` | `split(address[],bytes31,uint256)` | All modules. pUSD → complete set. Emits `PositionsSplit`. |
| `0x1d479a82` | `merge(address,bytes31,uint256)` | All modules. Emits `PositionsMerged`. |
| `0x2b83cccd` | `redeem(address,uint256,uint256)` | All modules. Emits `PositionRedeemed`. |
| `0x1102befc` | `reportResult(bytes31,uint256[])` | Resolver role (OracleAggregator) or bridge. Emits `ResultReported`, `ConditionResolved`. |
| `0xc8b42caf` | `pauseResolution(bytes29)` | Admin. Emits `ResolutionPaused`. |
| `0x3dbbf7eb` | `pauseResolver(address)` | Admin. Emits `ResolverPaused`. |
| `0x390a0b6f` | `addResolver(address)` | Admin. |
| `0x9712fdf8` | `addBridge(address)` | Admin. |
| `0xbc6c8557` | `mintFromBridge(address,uint256,uint256)` | Bridge only. Emits `BridgePositionMinted`. |
| `0x773a860d` | `burnFromBridge(uint256[],uint256[])` | Bridge only. Emits `BridgePositionsBurned`. |
| `0xaedac620` | `migratePositions(bytes32[],uint256[],uint256[])` | Binary / NegRisk. Legacy CTF → PositionManager. Emits `PositionMigrated`. |
| `0xdf219aa0` | `migratePositions(address,bytes32[],uint256[],uint256[])` | Operator on behalf of a user. |
| `0xf37d5729` | `resolveMigrationCondition(bytes32)` | Permissionless. Emits `MigrationResolved`. |
| `0xaf5c826c` | `horizontalSplit(address,bytes29,uint256)` | NegRisk only. Emits `HorizontalSplit`. |
| `0x3244d673` | `horizontalMerge(address,bytes29,uint256)` | NegRisk only. Emits `HorizontalMerge`. |
| `0x4f6b8da3` | `convert(address,bytes29,uint256,uint256)` | NegRisk only. Emits `PositionConverted`. |
| `0x2a7c9809` | `prepareMigrationEvent(bytes32)` | NegRisk only. Creator role. |

BinaryModule only: `prepareMigrationCondition(bytes32)` = `0x3ae2319a`. CombinatorialModule only: `prepareCondition(uint256[])` = `0x097dd164`, `inject(address,uint256,uint256,uint256)` = `0x3bc5e9b4`, `extract(address[],uint256,uint256,uint256)` = `0x5d5a4f7e`, `compress(address,uint256,uint256)` = `0xb871f2a8`.

### 2.4 Router (user entry points)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x82d3b9f1` | `split(bytes31,uint256)` | Caller pays pUSD. Emits `RouterPositionSplit`. |
| `0x5b63685e` | `merge(bytes31,uint256)` | Emits `RouterPositionsMerged`. |
| `0xd217a3cc` | `redeem(bytes31,uint256,uint256)` | Emits `RouterPositionRedeemed`. |
| `0x9380f1c8` | `convert(bytes29,uint16,uint256)` | NegRisk convert. Emits `RouterPositionConverted`. |
| `0x40657b52` | `horizontalSplit(bytes29,uint256)` | Emits `RouterHorizontalSplit`. |
| `0x24f24944` | `horizontalMerge(bytes29,uint256)` | Emits `RouterHorizontalMerge`. |
| `0x25ded586` | `wrap(uint256,uint256)` | Combinatorial wrap. |
| `0x6e286671` | `unwrap(uint256,uint256)` | Combinatorial unwrap. |
| `0xe86d745b` | `combinatorialCollateralReturn((uint256,uint256[],uint256[]),bytes[])` | Batched flow. Emits `CombinatorialCollateralReturned`. |

### 2.5 AutoRedeemer
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x53d190cf` | `redeem(address[],uint256[])` | Operator. Batch redeem for users. Emits `Redemption`. |
| `0xc9489691` | `redeemBinary(address[],bytes32[])` | Operator. Legacy CTF binary redemptions. Emits `BinaryRedemption`. |
| `0x5ede0646` | `redeemNegRisk(address[],bytes32[])` | Operator. Legacy neg-risk redemptions. Emits `NegRiskRedemption`. |

### 2.6 OracleAggregator
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6a01a72b` | `initializeRequest((bytes29,uint8,address,uint16,(address,bytes)[],uint16,(address,bytes)[],uint16,address,bytes,uint32,address))` | Operator. Emits `RequestInitialized`. |
| `0x853dbee4` | `reportResult(bytes32,uint256[])` | Reporter module. Emits `ResultReported`. |
| `0xb1f6eb6f` | `disputeResult(bytes32)` | Disputer module. Emits `ResultDisputed`. |
| `0x2db4cc62` | `finalize(bytes32,uint256[])` | Finalizer (or anyone if unset). Emits `RequestResolved`. |
| `0x3fbdddf1` | `resolveResult(bytes32,uint256[])` | Arbitrator path. Emits `RequestResolved`. |
| `0x253ea980` | `pauseOracle()` | Admin. Emits `GlobalPauseSet`. |
| `0x0fab6865` | `unpauseOracle()` | Admin. |
| `0x36e99457` | `pauseMarkets(bytes29[])` | Admin. Emits `MarketPauseSet`. |
| `0x25bf8ea1` | `setArbitratorModule(bytes32,address,bytes)` | Admin. Emits `ArbitratorModuleSet`. |
| `0x14a3b31d` | `setFinalizer(bytes32,address)` | Admin. Emits `FinalizerSet`. |
| `0xb70d73a0` | `setLivenessWindow(bytes32,uint32)` | Admin. Emits `LivenessWindowSet`. |
| `0x39c29994` | `addReporterModules(bytes32,(address,bytes)[])` | Admin. Emits `ReporterModuleAdded`. |
| `0xc6cea49c` | `addDisputerModules(bytes32,(address,bytes)[])` | Admin. Emits `DisputerModuleAdded`. |

### 2.7 Reporter modules
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa60c7bb2` | `createRequest(bytes32,bytes,uint64,uint64)` | OOReporterModule. Opens a UMA OO request. Emits `OOReporterRequestCreated`. |
| `0x26030a34` | `report(bytes32)` | OO / Chainlink reporter. Pushes the result to the aggregator. |
| `0xb5341501` | `report(bytes32,uint256[])` | EOAReporterModule. Trusted reporter vote. Emits `Reported`. |
| `0xba00f270` | `setFeedId(bytes32,bytes32)` | ChainlinkReporterModule admin. Emits `FeedIdUpdated`. |
| `0xbda53107` | `setPriceSource(address)` | ChainlinkReporterModule admin. Emits `PriceSourceUpdated`. |
| `0xf9120af6` | `setAggregator(address)` | All reporter modules. Admin. Emits `AggregatorSet`. |

### 2.8 Common admin (all proxies)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | Owner. Emits `Upgraded`. |
| `0xf2fde38b` | `transferOwnership(address)` | Owner. |
| `0xf04e283e` | `completeOwnershipHandover(address)` | Owner. |
| `0x1c10893f` | `grantRoles(address,uint256)` | Owner. Emits `RolesUpdated`. |
| `0x70480275` | `addAdmin(address)` | Wrapper over `grantRoles`. |
| `0x9870d7fe` | `addOperator(address)` | Wrapper over `grantRoles`. |

---

## 3. Addresses — Polygon PoS (chain ID 137)

All proxies verified with `eth_getCode` (61-byte Solady ERC-1967 proxy) on `https://polygon-bor-rpc.publicnode.com` on 2026-10-30. "Live impl" is the EIP-1967 slot value on that date.

| Role | Proxy | Live impl | Note |
|------|-------|-----------|------|
| **PositionManager** | `0x006f54f7f9a22e0000cc2ab60031000000ae9fef` | `0xcc5de1e9d14a7ab75e872e23fc9d605518bac2d0` | Same as README. |
| **Exchange** | `0xe3333700ca9d93003f00f0f71f8515005f6c00aa` | `0x862f1cff1bd6246a2585e3622137e6f961b34e55` | Upgraded. README impl `0x641b40ec414a076b9e79e703fc7bf4ebec248bb7`. |
| **Router** | `0x12121212006e4cd160d18e3f00711da5c3372600` | `0x91fa5e2f12a308a13defdb6aaf80b71dbe9b7696` | Same as README. |
| **AutoRedeemer** | `0xa1200000d0002264c9a1698e001292d00e1b00af` | `0x64860bfd14fccaac09cd36f347784a9616afb66c` | Same as README. |
| **BinaryModule** | `0x1000008dd9001b968442c1000017eae6e0da00ba` | `0xf92ab45679d89a9430ee9123e7c88d5c8d044b85` | Upgraded. README impl `0xf6428c0b5fa9361c0708cddb95468cf54c56e9a2`. |
| **NegRiskModule** | `0x200000900045e3b6259600682756002200028933` | `0xf870c21179ffb45fc7fa0fdbf938f72405808086` | Upgraded. README impl `0x39a5b01a100edf811f2748aa37b1313715ded70e`. |
| **CombinatorialModule** | `0x30000034706c7d8e12009dab006be20000c031a8` | `0xf96968a44022b17240b42c557693e7c383d2d8a3` | Same as README. |
| **OracleAggregator** | `0x0a0a0a0a8b00c51b7d810501b03f230028c04a87` | `0x822e8a97af8005073f2f6e88435d692e33ab6082` | Same as README. |
| **OOReporterModule** | `0x000012e0009c84078c4924fba808a41b9f67527f` | `0xbd49a21677da630ff5efec52b7309d0ada685d81` | Same as README. |
| **ChainlinkReporterModule** | `0xc12ec12e0000326890ca5560def5eb5c22b16814` | `0x33823856ff1c89cd6940f8ad3d03786c439d6ca5` | Same as README. |
| **EOAReporterModule** | `0x8ef9d6d668798b1f363b305d916f30739d2b0419` | `0x5fe0280873f5539da12b6b5b37484e0b0c28ab14` | Same as README. |
| CollateralToken (pUSD) | `0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb` | `0xce84e053301a82937f90ee2c2c1889cab1db25de` | Shared. See `exchange_v2.md`. |
| Owner (all proxies) | `0x47ebfac3353314c788b96cdcbf41daadfe03629c` | — | `owner()` of PositionManager, Exchange, pUSD. |

Not deployed: `CcipBridge`, `BridgeRouter`, `CtfRouter` (no address in the README, no code found).

---

## 4. Cross-chain summary

| Chain (ID) | PositionManager + modules | Exchange / Router | OracleAggregator + reporters |
|------------|---------------------------|-------------------|------------------------------|
| Ethereum (1) | — | — | — |
| Base (8453) | — | — | — |
| BNB (56) | — | — | — |
| Avalanche (43114) | — | — | — |
| Arbitrum (42161) | — | — | — |
| Optimism (10) | — | — | — |
| **Polygon (137)** | ✓ | ✓ | ✓ |
| Robinhood Chain (4663) | — | — | — |
| Arc (5042) | — | — | — |

`—` = `eth_getCode` returned `0x` for every proxy and implementation in §3 on 2026-10-30. Polygon is the resolution hub (`resolutionChain` = 0). A spoke chain would show the same vanity proxy addresses only if the same deployer and salts are reused. None was found.

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| All 11 contracts in §3 + pUSD | UUPS, Solady ERC-1967 minimal proxy (61 B runtime, hash prefix `aaa52c`) | impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` (values in §3). Admin and beacon slots are zero. | `owner()` `0x47eb…629c` through `upgradeToAndCall`. Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. |

Known old implementations (README vs live): Exchange `0x641b…8bb7`, BinaryModule `0xf642…e9a2`, NegRiskModule `0x39a5…d70e`. The migration mixins hold legacy CTF / NegRiskAdapter addresses as immutables, so each module proxy has its own implementation.

---

## 6. Detection invariants & gotchas

1. **Different token contract.** Positions are on PositionManager `0x006f…9fef`, not on the CTF. ERC-1155 `TransferSingle` / `TransferBatch` there are the position movements.
2. **Decode the position id.** Top byte = module. `outcomeIndex` = low byte (0 = YES, 1 = NO for binary). `resolutionChain` 0 = Polygon. The condition id is the position id with the low byte cleared, stored as `bytes31`.
3. **Router events vs module events.** A Router call emits `RouterPositionSplit` (etc.) on the Router **and** `PositionsSplit` on the module. Count one of them.
4. **Pre-transfer pattern.** Users send tokens to the Router / module before the call. There is no `transferFrom` pull. The pUSD `Transfer` to the module is the deposit.
5. **Migration flow.** `PositionMigrated` + CTF `TransferSingle` to the module = a user leaving the legacy CTF. `LegacyCollateralSettled` = released USDC.e sent to the pUSD vault.
6. **Resolution path.** OracleAggregator `ResultReported` (reporter votes) → `OutcomeProposed` → liveness → `RequestResolved` → module `ResultReported` + `ConditionResolved`. `ArbitrationTriggered` and `ReporterConflict` signal disputes.
7. **Pause controls.** `GlobalPauseSet(true)`, `MarketPauseSet`, `ResolutionPaused`, `ResolverPaused`, `TradingPaused` are all admin actions to alert on.
8. **Exchange events = CTF Exchange V2 events.** Filter by emitter `0xe333…00aa` to separate this venue from `0xe111…996b` / `0xe222…0f59`.
9. **Bridge events** (`BridgePositionMinted`, `BridgePositionsBurned`) should be absent while no bridge is deployed. Any occurrence means a bridge was added (`addBridge`).

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- PositionManager (ERC-1155)
TOPIC_ERC1155_TRANSFER_SINGLE        = '\xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62'
TOPIC_ERC1155_TRANSFER_BATCH         = '\x4a39dc06d4c0dbc64b70af90fd698a233a518aa5d07e595d983b8c0526c8f7fb'
TOPIC_PM_MODULE_ADDED                = '\xa7839c29a2c3fc5208115d9be22d20b2a981203a3428218dd76c76d690254499'
TOPIC_PM_MODULE_REMOVED              = '\x854cff40228579f66eb3dd26b84ef9d8bb9f43b2a6a03495f29fae9b2827d987'
TOPIC_PM_CROSS_MODULE_AUTH_SET       = '\x26bdfbc198f2d30945bd9a2384cb5d3b97a1cfe249d1538aa803c7fbb79681cb'
-- Exchange (same as CTF Exchange V2)
TOPIC_V2_ORDER_FILLED                = '\xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee'
TOPIC_V2_ORDERS_MATCHED              = '\x174b3811690657c217184f89418266767c87e4805d09680c39fc9c031c0cab7c'
TOPIC_V2_FEE_CHARGED                 = '\x55bb3cade9d43b798a4fe5ffdd05024b2d7870df53920673bfc7e68047cd0ab1'
TOPIC_TRADING_PAUSED                 = '\x203c4bd3e526634f661575359ff30de3b0edaba6c2cb1eac60f730b6d2d9d536'
-- Modules
TOPIC_MOD_POSITIONS_SPLIT            = '\xb6a6b8b17a43b07b9359dd12d304e42077eede9e672f8646144842c8604582a4'
TOPIC_MOD_POSITIONS_MERGED           = '\xf233f7be4ce81130a78e8eb2fa626497586c56094d27bfec2e196471e9c60301'
TOPIC_MOD_POSITION_REDEEMED          = '\x4fd474b703f46b453536518b4cbc159dfbea6fd663233763d321a9bc8ccdf97f'
TOPIC_MOD_RESULT_REPORTED            = '\x669c053fe14f2493990c0c90d8d2870cd45e2630b34b8a2b4f02869301987713'
TOPIC_MOD_CONDITION_RESOLVED         = '\xe560c1a2847d4cf2e66de11fe592605556989449f38cc3ab96e2e287daa68caa'
TOPIC_MOD_RESOLUTION_PAUSED          = '\xdc9b357849b1f270abed270e8b7b026ba0a6c0a0137ad63fe62595e9a5ef338e'
TOPIC_MOD_RESOLVER_PAUSED            = '\x2883146a9b6f97f0c11f47a78214d9b6763323144fa6b91962867087cc6ced3d'
TOPIC_MOD_POSITION_MIGRATED          = '\xe8d329e97d555e1e9d0da49d3b12d41a966458eee02ff4c869e54c6711d7c80b'
TOPIC_MOD_MIGRATION_RESOLVED         = '\xf87100968b0fe70751acf87590ffac515231c5b999cba36e6820c7d312dcc8af'
TOPIC_MOD_LEGACY_COLLATERAL_SETTLED  = '\x7a07cc3efaf017520e4ad55e66052f0398632c810a3fab73e58e4c7050746825'
TOPIC_MOD_BRIDGE_POSITION_MINTED     = '\xd310e554d3fd5335d0aca4ef77d4859f65a3e728008329aef6db44ebaf78f1e1'
TOPIC_NRM_EVENT_PREPARED             = '\x9bdf886b29ff2e03765aa003845c79f3700b39f9628db119aeeaac5d0fd73306'
TOPIC_NRM_HORIZONTAL_SPLIT           = '\x9dbee20759d31417e9b0d739e07904f87139522ce89cf2f6ad78e299067674ce'
TOPIC_NRM_HORIZONTAL_MERGE           = '\xbfdd473162148936b92fc229a1d66bcded27968d61ec543cbd86b433fd2d7b4b'
TOPIC_NRM_POSITION_CONVERTED         = '\x975e919c2cacb75b8a9fc78ddf455a5211812df2f388c877c8d3adfe156e2779'
TOPIC_CM_CONDITION_PREPARED          = '\x51c89d7ee51515f7235e928930da7f81be08212bc14870a6a37c64744492db96'
-- Router / AutoRedeemer
TOPIC_ROUTER_POSITION_SPLIT          = '\x04373eecd7397b9318ae470769098aaab46f432620d95b0d84fc2297a415704c'
TOPIC_ROUTER_POSITIONS_MERGED        = '\x8eb905ea8eb4589289705df45fe31e6d4a35385a223b60c259691cc86dbfb982'
TOPIC_ROUTER_POSITION_REDEEMED       = '\x81b466b1b365aea7f5664f9a2d8b3a8591d3244acffb5134355ad4da7fe2366a'
TOPIC_AR_REDEMPTION                  = '\xeebddeddf4ae1ee54a48517af27958e7666d69c7ba2e3e7c2b0ff87ef5f4491e'
TOPIC_AR_BINARY_REDEMPTION           = '\xb434294b5904213c83a167af0068ab82637c6fd4fac945e2abc74ed8d3f4d52a'
TOPIC_AR_NEGRISK_REDEMPTION          = '\x74a51ebefec30281ec6849b727ec7916f9b1a3e5e148d6771d98315215b38b96'
-- OracleAggregator / reporters
TOPIC_OA_REQUEST_INITIALIZED         = '\x3f540a7f583087a9dcc5ae409a9757c451baede9df196f29fb15fe29fe2662c9'
TOPIC_OA_RESULT_REPORTED             = '\x553ed0b8f6413e4ecbf8434f6ca75a7752f7620c095aedd5929c6e8212149396'
TOPIC_OA_OUTCOME_PROPOSED            = '\xb8e19bf6c02c74c20cfc00567a3be20e29f089d4ed11da6726011dbbcd2ee787'
TOPIC_OA_RESULT_DISPUTED             = '\xbc5cfd3515610af0e2196d410032fb4ab213d3cee8e295a4ae2a6267d061bad0'
TOPIC_OA_ARBITRATION_TRIGGERED       = '\x6141166d67d9e01ddaf66f0aa3b4f57290d442fa83745ddf768aa606d0838270'
TOPIC_OA_REPORTER_CONFLICT           = '\x6dfa2acc6f02c2512d0bea4c4ab45f5f781fe2abb365a6eb04ab2b2ddcd66402'
TOPIC_OA_REQUEST_RESOLVED            = '\x1e15c34094c71de8f5cafd2ab5e84ffb03d5b44394eb40632b3a4dce1c4311a0'
TOPIC_OA_GLOBAL_PAUSE_SET            = '\x971be26fcde2df81b2b63dfb7fa1d2294b524eb1896b10e5228d9c154a30af09'
TOPIC_OA_MARKET_PAUSE_SET            = '\xc51886d63e98dce9b94e65fdd117981be37c579382c2306e29fbe38a9ad2868b'
TOPIC_EOA_REPORTED                   = '\x5a0e1b88d8fab2783c9b8319efb377157ba306962b9b5cb72532fe4c1eacd52c'
TOPIC_CL_REQUEST_REPORTED            = '\xdc53ded0d26e27b31f5cf0e3d4c9c4bbf186d45abf6b5f88af0b1534bfbe677f'
TOPIC_OO_RESULT_REPORTED             = '\xbd38647ecefb296b23744d285f2b49943cf5e86d01de4271390f24f6dde12acf'
-- Solady admin (all proxies)
TOPIC_UPGRADED                       = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ROLES_UPDATED                  = '\x715ad5ce61fc9595c7b415289d59cf203f23a94fa06f04af7e489a0a76e1fe26'
TOPIC_OWNERSHIP_TRANSFERRED          = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_OWNERSHIP_HANDOVER_REQUESTED   = '\xdbf36a107da19e49527a7176a1babf963b4b0ff8cde35ee35d6cd8f1f9ac7e1d'
TOPIC_OWNERSHIP_HANDOVER_CANCELED    = '\xfa7b8eab7da67f412cc9575ed43464468f9bfbae89d1675917346ca6d8fe3c92'
TOPIC_INITIALIZED_U64                = '\xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2'
-- ===== Selectors (chain-agnostic) =====
SEL_EX3_MATCH_ORDERS                 = '\x0fb25ba4'
SEL_MOD_SPLIT                        = '\x2d20cffd'
SEL_MOD_MERGE                        = '\x1d479a82'
SEL_MOD_REDEEM                       = '\x2b83cccd'
SEL_MOD_REPORT_RESULT                = '\x1102befc'
SEL_MOD_MIGRATE_POSITIONS            = '\xaedac620'
SEL_ROUTER_SPLIT                     = '\x82d3b9f1'
SEL_ROUTER_MERGE                     = '\x5b63685e'
SEL_ROUTER_REDEEM                    = '\xd217a3cc'
SEL_OA_FINALIZE                      = '\x2db4cc62'
SEL_OA_RESOLVE_RESULT                = '\x3fbdddf1'
SEL_OA_PAUSE_ORACLE                  = '\x253ea980'
SEL_PM_ADD_MODULE                    = '\x1ed86f19'
SEL_UPGRADE_TO_AND_CALL              = '\x4f1ef286'
-- ===== Addresses (Polygon 137) =====
POLY_POSITION_MANAGER                = '\x006f54f7f9a22e0000cc2ab60031000000ae9fef'
POLY_EXCHANGE_V3                     = '\xe3333700ca9d93003f00f0f71f8515005f6c00aa'
POLY_ROUTER                          = '\x12121212006e4cd160d18e3f00711da5c3372600'
POLY_AUTO_REDEEMER                   = '\xa1200000d0002264c9a1698e001292d00e1b00af'
POLY_BINARY_MODULE                   = '\x1000008dd9001b968442c1000017eae6e0da00ba'
POLY_NEGRISK_MODULE                  = '\x200000900045e3b6259600682756002200028933'
POLY_COMBINATORIAL_MODULE            = '\x30000034706c7d8e12009dab006be20000c031a8'
POLY_ORACLE_AGGREGATOR               = '\x0a0a0a0a8b00c51b7d810501b03f230028c04a87'
POLY_OO_REPORTER_MODULE              = '\x000012e0009c84078c4924fba808a41b9f67527f'
POLY_CHAINLINK_REPORTER_MODULE       = '\xc12ec12e0000326890ca5560def5eb5c22b16814'
POLY_EOA_REPORTER_MODULE             = '\x8ef9d6d668798b1f363b305d916f30739d2b0419'
POLY_PM_OWNER                        = '\x47ebfac3353314c788b96cdcbf41daadfe03629c'
```

---

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the `polymarket-v2-external` sources. User-defined value types were expanded (`ConditionId` → `bytes31`, `EventId` → `bytes29`, `PositionId` → `uint256`). Each topic0 was found as a `PUSH32` operand, and each selector as a `PUSH4` operand, in the **live implementation** bytecode read from the EIP-1967 slot.
- **Live events:** a 40-block `eth_getLogs` sample showed `OrderFilled` / `OrdersMatched` / `FeeCharged` on the Exchange, `TransferSingle` / `ApprovalForAll` on PositionManager, `ResultReported` / `ConditionResolved` / `MigrationResolved` on NegRiskModule, `CombinatorialConditionPrepared` / `PositionsSplit` on CombinatorialModule, and `BinaryRedemption` on AutoRedeemer. The Exchange has emitted fills since about block 88.2M (June 2026).
- **Addresses:** from the `polymarket-v2-external` README and the `clob-client-v2` contract config (`exchangeV3`). Each proxy and implementation was existence-checked with `eth_getCode`. `owner()` read live.
- **Chain coverage:** every proxy and implementation in §3 returned `0x` from `eth_getCode` on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Robinhood Chain and Arc.

Authoritative sources:
- [Polymarket/polymarket-v2-external](https://github.com/Polymarket/polymarket-v2-external) — source, docs (architecture, modules, oracle, bridge, migration), deployed addresses.
- [Polymarket/clob-client-v2](https://github.com/Polymarket/clob-client-v2) — `src/config.ts` (`exchangeV3`).
- [docs.polymarket.com](https://docs.polymarket.com) — contract address pages.
- Explorer: [Polygonscan](https://polygonscan.com).
