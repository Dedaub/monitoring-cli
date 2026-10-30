# ether.fi Cash (v3) — Topics, Selectors, Addresses (Optimism core chain; top-up contracts on Ethereum, Base, BNB, Arbitrum)

**Status:** verified against live RPC on all nine chains and the verified Optimism implementation ABIs on 2026-10-30. Addresses come from the official ether.fi "Deployed Contracts" page and `etherfi-protocol/cash-v3` `deployments/mainnet/<chainId>/deployments.json`.
**Scope:** the ether.fi **Cash** card stack: per-user smart-account safes, the `CashModule` (spend / borrow / repay / withdraw), the `CashEventEmitter` (one emitter for all Cash events), the legacy `DebtManager`, the settlement dispatchers that pay the card issuers, the `TopUpDest` that credits deposits, and the per-chain **top-up** factories that bridge user deposits to the core chain. Topics and selectors are chain-agnostic. Addresses are per chain.

**Lending is now Aave V4.** Cash borrowing moved to a white-label **Aave V4** stack on Optimism ("EtherFi Cash": Cash Hub `0x6675…C572`, Cash Spoke `0xdffc…5308`, LendGateway `0x01F8…03F4`). That stack is documented in [../aave/v4.md](../aave/v4.md) (section "Addresses — Optimism — EtherFi Cash white-label instance"). This file does not repeat it. The legacy `DebtManager` still emits `MigratedToLendGateway` as positions move.

**Core chain moved to Optimism.** The official "Account upgrade" page says the Cash core chain changed to Optimism in April 2026. The old core chain (Scroll, outside the nine targets) is now a top-up chain. Each user has one **universal address** on every top-up chain. Deposits there are bridged to the user's safe on Optimism.

---

## 0. Components

| Component | Role |
|-----------|------|
| **EtherFiSafe** (one per user) | Smart account. `BeaconProxy` deployed by `EtherFiSafeFactory` (`BeaconProxyDeployed`). Impl `0x79A6d202…397e` (23,980 B). Modules act on it with `execTransactionFromModule`. |
| **CashModule** | Card logic: `spend`, `borrow`, `repay`, `requestWithdrawal`/`processWithdrawal`, liquidation hooks. Emits nothing itself: all events go through `CashEventEmitter`. |
| **CashEventEmitter** | Single emitter: `Spend`, `Cashback`, `WithdrawalRequested/Processed/Cancelled`, `Repay`, `ModeSet`, `SpendingLimitChanged`, `LendBorrowed`, … |
| **EtherFiDataProvider** | Registry: whitelisted modules, CashModule, hook, price provider. |
| **DebtManager** (legacy) | Old in-house lending (`Borrowed`, `Repaid`, `Liquidated`). Positions migrate to the Aave V4 LendGateway. |
| **SettlementDispatcher** ×4 | Rain, Reap, Pix, CardOrder. Receive spent funds and forward them to the card issuer (`FundsSettled`), by CCTP/OFT/Stargate if needed. |
| **TopUpDest** | Credits a user's safe on Optimism after a cross-chain top-up (`TopUp`). |
| **TopUpSourceFactory** (top-up chains) | Deploys each user's `TopUp` beacon proxy at the universal address and bridges collected funds (`Bridge`). Bridge adapters run by `delegatecall`, so their events appear at the factory address. |
| **TradingSafeFactory** | Separate trading-account safes; same literal on all seven publicnode chains. |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 CashEventEmitter (Optimism `0x380B…81acB`)
| topic0 | Event |
|--------|-------|
| `0x244f4cc0665ad7ee4709aa59b30d3ea581cecde1b0430a3f23a5dc609d4890fc` | `Spend(address indexed safe, bytes32 indexed txId, uint8 indexed binSponsor, address[] tokens, uint256[] amounts, uint256[] amountInUsd, uint256 totalUsdAmt, uint8 mode)` |
| `0x89d3571a498b5d3d68599f5f00c3016f9604aafa7701c52c1b04109cd909a798` | `Cashback(address indexed safe, uint256 spendingInUsd, address indexed recipient, address cashbackToken, uint256 cashbackAmountInToken, uint256 cashbackInUsd, uint256 cashbackType, bool indexed paid)` |
| `0xb2304e3d75f4667ae0ecb838e9dda697e12be232df354a420abc4f76639026ca` | `PendingCashbackCleared(address indexed recipient, address cashbackToken, uint256 cashbackAmount, uint256 cashbackInUsd)` |
| `0xc48955aee858164993e89d10d9ad1aaf03010012434dac8ebae005105b1d4d6d` | `WithdrawalRequested(address indexed safe, address[] tokens, uint256[] amounts, address indexed recipient, uint256 finalizeTimestamp)` |
| `0x5eed621d1eddc71f0ca04e002e24088109cd3fd594c7af230edbf9e73d616047` | `WithdrawalProcessed(address indexed safe, address[] tokens, uint256[] amounts, address indexed recipient)` |
| `0x50efeea714c351006c4fa7822fb73539a491c1d587e149b8dc5bf4c1a7056066` | `WithdrawalCancelled(address indexed safe, address[] tokens, uint256[] amounts, address indexed recipient)` |
| `0xa240c4826a4f75edb281475f9abb4af98d8566f787e9d9752267a2f0228d9743` | `WithdrawalAmountUpdated(address indexed safe, address indexed token, uint256 amount)` |
| `0xe4a1ae657f49cb1fb1c7d3a94ae6093565c4c8c0e03de488f79c377c3c3a24e0` | `Repay(address indexed safe, address indexed token, uint256 debtAmount, uint256 debtAmountInUsd)` |
| `0x774a98d5aacabc2dff76b4531406533e8f7e7fe933646d221fdd9f088ee1b278` | `RepayDebtManager(address indexed safe, address indexed token, uint256 debtAmount, uint256 debtAmountInUsd)` |
| `0x80d94516dbc7014196ff764eb8b1c468e44e6f2891bf9a132fc145f75a3f9f23` | `RepayLendTokenAmount(address indexed safe, address indexed token, uint256 debtAmount)` |
| `0x38578014f71a287d9193d79e855fe47d225d8e5637ef400a63adbccfce03fc85` | `LendBorrowed(address indexed safe, address indexed token, uint256 amount, uint256 amountInUsd)` |
| `0xae6e182563c29e4cf783741fbf3d788afb490f6c665153ee267bf4399a6c0b5e` | `LendOptedIn(address indexed safe)` |
| `0x4a516b667da385a7b253a757b505a54ea639d06934baabd9f968bbb67979e23b` | `LendOptOutRequested(address indexed safe, uint256 finalizeTime)` |
| `0x14f8729a9a0faae3c2c837f46d47008ff10ad346034ae755e469365047571156` | `LendOptOutExecuted(address indexed safe)` |
| `0x63de5d9e3abf8e61d1625bc807f124544d7525e524d461ce3c0085fa4e6722e9` | `LendSupplyFailed(address indexed safe, address indexed token, uint256 amount, bytes reason)` |
| `0xefaf1dca2e49b79c93b6e4f6de1ac1c64bc2564d5fd3277237af49e51e173ff9` | `CollateralResupplied(address indexed safe, address indexed token, uint256 amount)` |
| `0xf6eabb9d9f10b3f417c46c38955eb7aea4886a913b32069a91a2af002dffee8d` | `ModeSet(address indexed safe, uint8 prevMode, uint8 newMode, uint256 incomingModeStartTime)` |
| `0x386efab796ecb0c216c9a39430a74f99716e683b28c915533174087017fe5d2d` | `SpendingLimitChanged(address indexed safe, (uint256,uint256,uint256,uint256,uint256,uint256,uint64,uint64,uint64,uint64,int256) oldLimit, (uint256,uint256,uint256,uint256,uint256,uint256,uint64,uint64,uint64,uint64,int256) newLimit)` |
| `0x33bdb4ad7a5e64d7fa41d735f724cc28a096df97d3349faf5bb084efb2bde4cc` | `SafeTiersSet(address[] safes, uint8[] tiers)` |
| `0xf83edca8884b7bfc5ffcac35221eceb5e91ab682e2ad8b8818d53b7b2790c47b` | `TierCashbackPercentageSet(uint8[] tiers, uint256[] cashbackPercentages)` |
| `0x9a7a564efdc544efb2511d89c7c8f8a2ffd24e178ebdd198acf620e3c769dd68` | `SettlementDispatcheUpdated(uint8 binSponsor, address oldDispatcher, address newDispatcher)` |
| `0x0636ab8ae94ed9790b956b5528d2e025f4432b480391e5bb185211f71c42e842` | `DelaysSet(uint64 withdrawalDelay, uint64 spendingLimitDelay, uint64 modeDelay)` |
| `0x4c1ac134bc04c2ce1a4e0d779d167b72a7bde79a5822e9577af08f0a7e3d2f48` | `WithdrawTokensConfigured(address[] tokens, bool[] shouldWhitelist)` |
| `0x0175263c7d40d19ed9e0a1462eba9955221fed6931ecb73b0c47661a0b2305b9` | `ModulesCanRequestWithdrawConfigured(address[] modules, bool[] shouldWhitelist)` |
| `0x0dff6e7a572ad68ae9b4f090554f15cddb311ac5de08425e88dbf10f81911b43` | `LendGatewaySet(address indexed gateway)` |

> Live (150 most recent): `Spend` 132, `WithdrawalProcessed` 8, `WithdrawalRequested` 6, `WithdrawalCancelled` 3, `ModeSet` 1. `SettlementDispatcheUpdated` is spelled without the final "r" in source: hash it as written.

### 1.2 EtherFiSafe (each user safe) and EtherFiSafeFactory
| topic0 | Event |
|--------|-------|
| `0xfdf8460245894f3316dac7bb64530a1ca0d54faa23a8fa680cf3e3db32661537` | `ExecTransactionFromModule(address[] to, uint256[] value, bytes[] data)` |
| `0xeb11e8ccbe97d4a65bf30443d702bdaa76e75ddfc0fe83d3e29e1b52385fd62d` | `ModulesConfigured(address[] modules, bool[] shouldWhitelist)` |
| `0xb5a63fa5098067ef2c54c579cc497500049a4c323feb49f9d704baf2040dbb0b` | `ModulesSetup(address[] modules)` |
| `0xe08e325dc20947840f420f7c361a8cdd6c074d5e577754e222e41ff918ec83ec` | `OwnersConfigured(address[] owners, bool[] shouldAdd)` |
| `0xb56e25549126f7f4a642a3a8b0df4ec75d7346f58d90543990da797f54c416b2` | `AdminsConfigured(address[] accounts, bool[] shouldAdd)` |
| `0x28a4f2bc9a2d1e8262aceeb52de887dda6aab13506e563af344f61cc95f1f4aa` | `ThresholdSet(uint8 oldThreshold, uint8 newThreshold)` |
| `0x3dd16130d88f9c4aacc13e83eeed8a5180cc85ab0b098c220e0736cc40c59818` | `Recovery(address newOwner, uint256 startTime)` |
| `0x444b9fc80713a03bfc01b03089babd94aa51edececce36355031fd7d1ed50b4a` | `AccountRecovered(address newOwner)` |
| `0xedd770ee01b7c0ef4f503125eafdc2725536cbf32342dffcaa300d95a7cafce3` | `RecoveryCancelled()` |
| `0x8e06ea6a4b54c82f6acec3009a2e20b3a7cc107c797102db684e9012211eaa61` | `IncomingOwnerSet(address incomingOwner, uint256 startTime)` |
| `0xe52c545f9eb7091773b6d69738499692e65fb1a4060bf5e61ca12ee5f3e9c5da` | `RecoverySignersConfigured(address[] recoverySigners, bool[] shouldAdd)` |
| `0x07a80e125a4acbb6dc0e55c065e2d1cb92c86a995e878bf5d6b7468373b8f7ea` | `RecoveryThresholdSet(uint8 oldThreshold, uint8 newThreshold)` |
| `0xc5c82c4fb74f97e446b78edada7cf112504453ba5a7328573be04be93171f242` | `EthWrapped(address indexed caller, uint256 amount)` |
| `0x5889f63567a2730b47d0d74082206509fb86668d46a900bd695e655d099d586e` | `BeaconProxyDeployed(bytes32 salt, address indexed deployed)` |
| `0xd8518b5f9760cf035849134f93f54b517edb9f10ce176b56bf030f3f9440389a` | `BeaconImplemenationUpgraded(address oldImpl, address newImpl)` |

> `BeaconProxyDeployed(bytes32 salt, address indexed deployed)` is shared by `EtherFiSafeFactory` (Optimism) and `TopUpSourceFactory` (top-up chains). `BeaconImplemenationUpgraded` is spelled without the "t" in source. `ModulesConfigured` is also emitted by `EtherFiDataProvider` for the global whitelist.

### 1.3 DebtManager (legacy lending)
| topic0 | Event |
|--------|-------|
| `0x3fc499aeb0bb1cb58b6de8b02b3f86f4e7394e9690bef0110e32ced8a5631045` | `Borrowed(address indexed user, address indexed token, uint256 amount)` |
| `0x861660e9b7ead7183d53fe928b5638c7b57a7bcf16a89d7fdb04db65ce3ad6d5` | `Repaid(address indexed user, address indexed payer, address indexed token, uint256 amount)` |
| `0x50413727b37795d672f09d0997645a955fa227befaefdd4adb611542dea3fd80` | `Supplied(address indexed sender, address indexed user, address indexed token, uint256 amount)` |
| `0xfd54f2a27ee93a2b60fa895931f0067b8eab4f20662e14ef1ef0720eb772ea9c` | `Liquidated(address indexed liquidator, address indexed user, address indexed debtTokenToLiquidate, (address,uint256,uint256)[] userCollateralLiquidated, uint256 beforeDebtAmount, uint256 debtAmountLiquidated)` |
| `0x4836b2e457ff051f5a3c300848cc5dc19535c7be3b5233117b1a9ec7c189eebe` | `MigratedToLendGateway(address indexed safe, uint256 debtUsd)` |
| `0xc6ecd996cf998cfeedb2b1379b047e8579d888439dacbc60641c6dfd07f1f802` | `InterestIndexUpdated(address indexed borrowToken, uint256 oldIndex, uint256 newIndex)` |
| `0x129c6de5e40c1dd150d47fb9ae711d9c22b118affbbaa6c3851334318b804d72` | `TotalBorrowingUpdated(address indexed borrowToken, uint256 totalBorrowingAmtBeforeInterest, uint256 totalBorrowingAmtAfterInterest)` |
| `0x0888589249a19f760c73a4c12cef4d35bba86ecf227a50bccf8387efa0bf721e` | `UserInterestAdded(address indexed user, uint256 borrowingAmtBeforeInterest, uint256 borrowingAmtAfterInterest)` |
| `0x2930a7b877d817b672bfa2846d236a1da511a35f283e7a75c55d4124216841e6` | `WithdrawBorrowToken(address indexed withdrawer, address indexed borrowToken, uint256 amount)` |
| `0x0a79a2c3945fa1460b7ce0aa563cc1cd6424a51a3f0d888754e797ebb54baf66` | `BorrowApySet(address indexed token, uint256 oldApy, uint256 newApy)` |
| `0x011128805ea0277047e3f7163c2d734358e71e614d3c0487497ef1813a2ea110` | `CollateralTokenConfigSet(address indexed collateralToken, (uint80,uint80,uint96) oldConfig, (uint80,uint80,uint96) newConfig)` |
| `0x1ad7ec344404069a779d110ce8e12ead2a2d263f4ea2728ac643e52913ac3904` | `BorrowTokenConfigSet(address indexed token, (uint256,uint256,uint256,uint64,uint64,uint128) config)` |
| `0xcdadd717dc9ee3550a289071d1af75e229726888d51e3a31c9e3dfc693d4852b` | `LiquidationThresholdUpdated(uint256 oldThreshold, uint256 newThreshold)` |

### 1.4 SettlementDispatcher (`SettlementDispatcherV2`) and TopUpDest
| topic0 | Event |
|--------|-------|
| `0x6435cb7c5450b5cfb0e43a0dcf384145e74d42dd7538567c16230f84544ed152` | `FundsSettled(address indexed token, address indexed recipient, uint256 amount)` |
| `0xe9171aeff46c37ab955b8aff908e14ae9732bd06634fa131226cfe5c25bfd2fb` | `FundsWithdrawn(address indexed token, uint256 amount, address indexed recipient)` |
| `0xd8f7c78f293a52ff06285b09819d7625a13eb9080c991b7fac88cbf2b7239e89` | `TransferToRefundWallet(address asset, address refundWallet, uint256 amount)` |
| `0x11696737af02e4f7ffd397fd11ec2351fe2089ea435eb1184680ab735c6caa0a` | `FundsBridgedWithOFT(address indexed token, uint256 amount)` |
| `0xeef44502f779c4a230d0676fe3f549eb216a8378d673e4ee27b9940fe222f360` | `FundsBridgedWithCCTP(address indexed token, uint256 amount, uint32 destinationDomain, address indexed recipient)` |
| `0xe80703b9d39d09d58bef629ae1125035c47d1da0342880315557c8ca9a2151cb` | `FundsBridgedWithStargate(address indexed token, uint256 amount, (uint72,bytes) ticket)` |
| `0x89fb53d0c0f0f36db1043a54a7bb546fd820379fef6a90aec7293c3cf7ca13c9` | `CanonicalBridgeWithdraw(address indexed token, address indexed recipient, uint256 amount)` |
| `0x51bf130244aab3e8452888df64bfe19c8c35a258af2516c5c1b791db7eae2f85` | `LiquidWithdrawalRequested(address indexed liquidToken, address indexed assetOut, uint128 amountToWithdraw, uint128 amountOut)` |
| `0x59370fcdb23894dafe810b26abeae731484eab86a11820dad1d5e3b21debd227` | `MidasRedeemed(address indexed midasToken, address indexed assetOut, uint256 amount, uint256 minReceive)` |
| `0x36d4f968438f47a4959388f57df78f42832efb651528b7f66886aab538b2d1ca` | `FraxRedeemed(uint256 amount, uint256 amountOut)` |
| `0x0b6c234da9c3ac12d5c07bd0a4d56113235542e4fc01c541a62c3ed6cdd0c37f` | `FraxAsyncRedeemed(uint256 amount, address indexed recipient)` |
| `0x9594a5d709ec968361fa251e01afdc4d45867e08a1245c98fd7279fd3d3a4e62` | `SettlementRecipientSet(address indexed token, address indexed recipient)` |
| `0x362bf1b2691bc777b4bfbdca438b0e63bca3a523dcc1f1dbb1eb4fea9c3e9a0e` | `RefundWalletSet(address indexed refundWallet)` |
| `0xd42270db70d2ad14fcdd31d350b67c4c43435e869f0bc31d8ab165cfd72604e9` | `DestinationDataSet(address[] tokens, (uint32,address,address,bool,uint64,bool,address,bool)[] destDatas)` |
| `0x2ff66106aff37c72533c0686de51adb6d1b86dd1709407dc6a2236533ebe3c19` | `TopUp(bytes32 indexed txId, address indexed user, address indexed token, bytes32 sourceTxHash, uint256 chainId, uint256 amount)` |
| `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | `Deposit(address indexed token, uint256 amount)` |
| `0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65` | `Withdrawal(address indexed token, uint256 amount)` |
| `0x63de5d9e3abf8e61d1625bc807f124544d7525e524d461ce3c0085fa4e6722e9` | `LendSupplyFailed(address indexed safe, address indexed token, uint256 amount, bytes reason)` |
| `0x72c69fc2339c41ef8a09471418a0ef448d7294a8ef4dc07e138cb277fccd277f` | `StockWrapped(address indexed raw, address indexed wrapper, uint256 amount, uint256 shares)` |

### 1.5 TopUpSourceFactory (top-up chains) and its delegate-called bridge adapters
| topic0 | Event |
|--------|-------|
| `0xdeb96a3e5294fabe38d8824397be657fbe695d61f3457274027345cca6f26aaa` | `Bridge(address indexed token, uint256 amount, uint256 indexed destChainId)` |
| `0x5889f63567a2730b47d0d74082206509fb86668d46a900bd695e655d099d586e` | `BeaconProxyDeployed(bytes32 salt, address indexed deployed)` |
| `0x93ec1b6d292b7baab10097610d02fd4e579dce988855ff8617c7a2411e94d2cb` | `RedirectFunds(address indexed topUp, address indexed tradingSafe, address indexed token, uint256 amount)` |
| `0xf731d5013020dffa63f52339f4b47a4fb9a2b8bc6b88f1e0d4da0d105d11f815` | `WrapOnRedirect(address indexed topUp, address indexed wrapper, address indexed underlying, uint256 assets, uint256 shares)` |
| `0xfc300d77be3e07df57a475f2614150263fc5af44ad77e8e2da207aa9bc690514` | `WrapStock(address indexed topUp, address indexed wrapper, address indexed underlying, uint256 assets, uint256 shares)` |
| `0xb66c2595c5f377625ce78f02a4e5a1e17bd8e65fb805e6262a77398172989923` | `Recovery(address recoveryWallet, address indexed token, uint256 amount)` |
| `0xadb84db668ad3a3e3aa18a04bfddc5be02e91df5a50b6f582d333ff4aadc6238` | `RecoveryWalletSet(address oldRecoveryWallet, address newRecoveryWallet)` |
| `0x38b4ba5b5b718d46113d57ec0ea9e7e617b824c53b05851ba43b3c0725a93622` | `TokenConfigSet(address[] tokens, uint256[] chainIds, (address,address,uint96,bytes)[] config)` |
| `0x1cca7286aff149fdea06341568f4ba0cf89cd2cda75d59ebc1bbe76e41dbec0b` | `TokenConfigRemoved(address[] tokens, uint256[] chainIds)` |
| `0xd8fa7fa75f9c76e3ad6668d336b7bb2abe2599c7f77603e99143133390519191` | `TradingSafeFactorySet(address oldFactory, address newFactory)` |
| `0x80b19d4ae73b8f503d0df885f7a6252161aa3f8ff59f61389259541309d7f69e` | `BridgeViaCCTP(address token, uint256 amount, uint32 destinationDomain, bytes32 mintRecipient)` (CCTPAdapter) |
| `0xd78f10ceb472c9a2682253afe5f9512921f72e176a757030e53338fe095bfdb9` | `BridgeOFT(address indexed token, uint256 amount, (bytes32,uint64,(uint256,uint256)) messageReceipt, (uint256,uint256) oftReceipt)` (EtherFiOFTBridgeAdapter) |
| `0xc0287a34aa851832b0d4e1a2abfefd65dad182809adaf4b3cf538d8c871c5416` | `EtherFiLiquidTokenBridged(address indexed token, address indexed destRecipient, uint256 amount, uint32 destEid)` (EtherFiLiquidBridgeAdapter) |
| `0x07eddb5fc8fae77b818eb5aaa2ae709369cbba09470a6e872639876836839cb6` | `BridgeViaStargate(address indexed token, uint256 amount, (uint72,bytes) ticket)` (StargateAdapter) |
| `0x23560d34d78cbe245d17fea7af14f51642dc0aca2e9d425de7a67421e5f41639` | `BridgeToOptimism(address indexed l1Token, address indexed l2Token, address destRecipient, uint256 amount)` (OptimismBridgeAdapter, Ethereum) |
| `0xb3138792dabb976312cbda8fa266253aa071af5a2633c88517f4ab9b70efb95f` | `BridgeERC20(address indexed token, uint256 amount, address indexed destRecipient)` (Base-withdraw / Scroll ERC20 adapters) |
| `0x7b203b4ab77754ad28ea56fc1bfc46fd9b11dc38f8cbc30cf6a164f9bdc3871d` | `BridgeViaHop(address indexed token, address destRecipient, uint256 amount, uint32 destEid)` (HopBridgeAdapter) |
| `0xf76116bc28f75f5701d8893bfefda7eb7bb5349e761e4576cf0ccbba40185848` | `BridgeViaNTT(address token, uint256 amount, uint64 msgId)` (NTTAdapter) |
| `0x181414017b1410980a374761c7671e6d92077a0b31957b481f4bf25111f54764` | `BridgeStockOFT(address indexed token, address indexed wrapper, uint256 amount, uint256 shares, (bytes32,uint64,(uint256,uint256)) messageReceipt, (uint256,uint256) oftReceipt)` (StockOFTBridgeAdapter) |

> The adapter rows are computed from `src/top-up/bridge/*.sol` and confirmed live at the factory address: on Base `BridgeViaCCTP` 34, `EtherFiLiquidTokenBridged` 1, `BridgeViaStargate` 3; on Ethereum `BridgeToOptimism` 30, `BridgeOFT` 13, `BridgeViaCCTP` 10.

---

## 2. Function signatures (chain-agnostic)

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x4e309099` | `spend(address,bytes32,uint8,address[],uint256[],(address,(address,uint256,uint256)[])[])` | -> () |
| `0xd274056c` | `borrow(address,address,uint256,address[],bytes[])` | -> () |
| `0x1da649cf` | `repay(address,address,uint256)` | -> () |
| `0x478c9cbf` | `repayLendTokenAmount(address,address,uint256)` | -> () |
| `0x3c1a5012` | `processWithdrawal(address)` | -> () |
| `0xb7f48173` | `supplyToLend(address,address[])` | -> () |
| `0x0a994e0e` | `preLiquidate(address)` | -> () |
| `0x0bd735b7` | `postLiquidate(address,address,(address,uint256,uint256)[])` | -> () |
| `0xbcde317c` | `execTransactionFromModule(address[],uint256[],bytes[])` | -> () |
| `0x94f0339c` | `configureModules(address[],bool[],bytes[],address[],bytes[])` | -> () |
| `0x2d959e81` | `configureOwners(address[],bool[],uint8,address[],bytes[])` | -> () |
| `0xfec7ad88` | `recoverSafe(address,address[],bytes[])` | -> () |
| `0xff024c7b` | `deployEtherFiSafe(bytes32,address[],address[],bytes[],uint8)` | -> () |
| `0xde9d008d` | `upgradeBeaconImplementation(address)` | -> () |
| `0xeda7fbcd` | `borrow(uint8,address,uint256)` | -> () |
| `0x1da649cf` | `repay(address,address,uint256)` | -> () |
| `0x0c0a769b` | `supply(address,address,uint256)` | -> () |
| `0xea515161` | `liquidate(address,address,address[])` | -> () |
| `0x0bf5d35e` | `bridge(address,uint256,uint256)` | payable -> () |
| `0x1c20fadd` | `withdrawFunds(address,address,uint256)` | -> () |
| `0x22d932f4` | `transferFundsToRefundWallet(address,uint256)` | -> () |
| `0x391c13f5` | `withdrawLiquidAsset(address,address,uint128,uint128,uint16,uint24)` | -> () |
| `0x216094de` | `redeemMidasToAsset(address,address,uint256,uint256)` | -> () |
| `0x2b4911e0` | `topUpUserSafe(bytes32,address,uint256,address,uint256)` | -> () |
| `0x9e784431` | `topUpUserSafeBatch(bytes32[],address[],uint256[],address[],uint256[])` | -> () |
| `0x47e7ef24` | `deposit(address,uint256)` | -> () |
| `0xf3fef3a3` | `withdraw(address,uint256)` | -> () |
| `0x760d0f9d` | `deployTopUpContract(bytes32)` | -> () |
| `0xc93d2b1d` | `processTopUp(address[],uint256,uint256)` | -> () |
| `0x7b0eb57d` | `processTopUpFromContracts(address[],address[])` | -> () |
| `0x0bf5d35e` | `bridge(address,uint256,uint256)` | payable -> () |
| `0x58609754` | `recoverFunds(address,uint256)` | -> () |
| `0x0345bdbe` | `redirectToTradingSafe(address,address,uint256)` | -> () |

> `repay(address,address,uint256)` = `0x1da649cf` exists on both CashModule and DebtManager. `bridge(address,uint256,uint256)` = `0x0bf5d35e` exists on SettlementDispatcher and TopUpSourceFactory. Key on the target.

---

## 3. Addresses — Optimism (chain ID 10, core chain)

All UUPS `ERC1967Proxy` (122 B, admin slot `0x0`) unless noted; verified with `eth_getCode` on 2026-10-30.

| Role | Address | Impl (2026-10-30) |
|------|---------|-------------------|
| **CashModule** | `0x7Ca0b75E67E33c0014325B739A8d019C4FE445F0` | `0xd4591b40af911ed7b06b78a0aee35255429d58b3` (`CashModuleCore`) |
| **CashEventEmitter** | `0x380B2e96799405be6e3D965f4044099891881acB` | `0x07db0864e7a922fb77342d83671a6c8010f59e30` |
| **EtherFiSafeFactory** | `0xF4e147Db314947fC1275a8CbB6Cde48c510cd8CF` | `0xae143062e65edbebfc4eded8a31092e3fdb496b8`; safe beacon impl `0x79A6d20280e4b564ea1d8f5369C6544887F7397e` |
| EtherFiDataProvider | `0xDC515Cb479a64552c5A11a57109C314E40A1A778` | `0x7b0c84e0959f92725d7ed2c0e83317a633be3191` |
| EtherFiHook | `0x5D3c4f5CF2208bB54e8fd129730d01D82d4611b3` | `0xe7107d95b411a9386c88e260fb2f85be3d05900b` |
| CashLens | `0x7DA874f3BacA1A8F0af27E5ceE1b8C66A772F84E` | `0x31684300adebb262b952f61ecbb889292d5551a1` |
| **DebtManager** (legacy) | `0x0078C5a459132e279056B2371fE8A8eC973A9553` | `0xec22154811cd6510f4443438e0dbd04acfb908a1` |
| PriceProvider | `0x44dd2372FE7B97C4B4D6a7d4DeCf72466485BAcB` | `0xd63aea4cce895f2a866b2b62320635e100ecb07e` |
| CashbackDispatcher / CashbackDistributor | `0xef55eC694B0B8273967f28627C5BC26F5deea836` / `0x38F2fBb259F042DE3A601E0f7135f768DE08F5A2` | `0xd5d37b89…0cb5` / `0x3e1ff341…9aa7` |
| **TopUpDest** | `0x3a6A724595184dda4be69dB1Ce726F2Ac3D66B87` | `0xfd082f251d27e83a62a8ef9c045efaef26b9ce26` |
| **SettlementDispatcher Rain** | `0x50A233C4a0Bb1d7124b0224880037d35767a501C` | `0x759fdbf74f34f66e0d1991e6edf55d1b828a4097` |
| **SettlementDispatcher Reap** | `0x9623e86Df854FF3b48F7B4079a516a4F64861Db2` | `0xe98320e0279ad1d2aff2a01d89db4276b8e0d681` |
| SettlementDispatcher Pix | `0x95aaddD43b6edF838ec486E9f9814787212Bf42D` | `0x514c4cfe19c63a4d9ad8d1750a9f8f48c286cf0f` |
| SettlementDispatcher CardOrder | `0xb14FDfd7D2cfFb6Cc6953C1b80F1B1d12c2F766a` | `0x4becc1a98f008934463b7d1159e25a36d98fea65` |
| Cash RoleRegistry | `0x5C1E3D653fcbC54Ae25c2AD9d59548D2082C687B` | `0x08e5cc67…1566`; `owner()` = Cash Timelock |
| Cash Timelock | `0x9106cD76E10Ac60D1dd16144243416EbD2C64434` | OZ `TimelockController`, min delay 172,800 s (2 days) |
| LendGateway (Aave V4 position manager) | `0x01F8cDFb1694eA8fE4ED6c38a0fD78d1188E03F4` | see [../aave/v4.md](../aave/v4.md) |
| TradingSafeFactory | `0xE54e00b0e72F8FC8Cb7e124C378bAd2E7371d2b8` | `0xe3cd5e563cf5531fa0df33c6d3070e6e84f029e3` |

**Whitelisted modules (read live from `EtherFiDataProvider.getWhitelistedModules()`, 21 entries):** CashModule; EtherFiLiquidModuleWithReferrer `0x48651bf1ED1eE15C7493a79188E3326602b321c4`; EtherFiLiquidModule `0xf4d5Be5CfcCE8C32785FC36bF3851D2f1E3C0154`; EtherFiStakeModule `0xD4F81cF925248513631723A5cd0a8842f8cC2C3E`; FraxModule `0x3C97a4899a92b7e84d92c5032dC7d865E7471EcE`; StargateModule `0x8ad28aB6b117dA4f9cf92960cd43bDAA7FE45be4`; BeHYPEStakeModule `0xd2fBD2fCac7e88ef323694e617141Efb20140c56`; LiquidUSDLiquifierModule `0x39161A44588ec2327a18D4707EA5216C721ba539`; MidasModule `0x1052fDcE6CBE3D2AD265050e1426D41E23fc54dc`; OpenOceanSwapModule `0xFec8640113C5ff6c28A9aBAE5162f8602D8BD4bF`; AssetRecoveryModule `0x431d271D544aC67fAfFa8a9FfabAabCB14563102`; LendGateway; AcrossSwapModule `0x241D0227e6Ae4df1747f2A04F4bF3d33eD850cA7`; EnsoSwapModule `0xac6BcA0bB66D4587171CFc77b19E5E68F74De55e`; SafeAssetRecoveryModule `0x7abdECa95d0e81bDECE2C055EE8D1a5b5bFb18E2`; StockWithdrawModule `0xB9D4cdD267CB8f5F4123471A5B3dac8845EeAcA3`; CCTPModule `0xD3f5c617EF328b73130467b0ec867aD9058a1784`; MidasLiquifierModule `0x162c9f902867308B6f92c80B7329f5883385FC87`; plus three UUPS-proxy modules not named in the repo (`0x15a90d4548beb6d0f7140c17497f632e329e14dd`, `0xe7c6a85fa9a8edf84870e5658a83d94ed7e09270`, `0x2e654540fec9b409f67c0c0e3bf3973e6a987482`).

> **Stale module addresses on the official page.** The page lists EtherFiStakeModule `0xD908…0A1B`, BeHYPEStakeModule `0xd12e…DbB9F3`, EtherFiLiquidModule `0x9008…E7A5`, EtherFiLiquidModuleWithReferrer `0x80D4…8613`, StargateModule `0x865a…182E`, FraxModule `0x6742…7088`, MidasModule `0x2D43…08aa`, OpenOceanSwapModule `0x5765…c375`. All have code, but **none is in the live whitelist**. Use the live list above.

## 4. Addresses — top-up chains

| Chain | TopUpSourceFactory `0xF4e147Db…d8CF` | Impl | TradingSafeFactory `0xE54e…d2b8` | Notes |
|-------|--------------------------------------|------|----------------------------------|-------|
| Ethereum (1) | ✓ (135 B proxy) | `0x0681a8bb55f509c5952063163a1dda710084b80c` (`TopUpFactory`) | ✓ | adapters: Stargate `0x9895…f84a`, EtherFiOFT `0xfD60…2cd9`, EtherFiLiquid `0x251d…807f`, NTT `0x16B4…8975`, Scroll ERC20 `0x319a…E793`, Optimism `0x63D9…1dea`, CCTP `0x1D75…A8fb`, Hop `0xf184…9e88`, StockOFT `0x12e0…2E4B`; AssetRecoveryDispatcher `0x418e…6A29` |
| Base (8453) | ✓ (135 B) | `0x0681…B80C` | ✓ | adapters: Stargate `0xbef9…Fa54`, EtherFiOFT `0x0CcE…4F5C`, EtherFiLiquid `0x44E9…6D32`, NTT `0x16B4…8975`, BaseWithdrawERC20 `0x83c5…044e`, CCTP `0x6745…6E9E` |
| BNB (56) | ✓ (122 B) | `0x0681…B80C` | ✓ | |
| Arbitrum (42161) | ✓ (122 B) | `0x0681…B80C` | ✓ | adapter: CCTP `0xc8e6…30C5` |
| Avalanche (43114) | proxy only | `0x0168d60b…cead` = `EtherFiPlaceholder` (2,832 B) | ✓ | address reserved; no top-up logic |
| Polygon PoS (137) | proxy only | `0x70d7e0c9…aA9` (21,601 B, unverified; the repo labels the proxy `EtherFiSafeFactory`) | ✓ | not listed as a Cash chain on the official page |
| Optimism (10) | = EtherFiSafeFactory (core) | §3 | ✓ | |
| Robinhood Chain (4663), Arc (5042) | — | — | — | no Cash literal has code |

---

## 5. Cross-chain summary

| Chain | Cash core (CashModule, emitter, safes, dispatchers) | Top-up factory | Trading safe factory | Aave V4 Cash lending |
|-------|------------------------------------------------------|----------------|----------------------|----------------------|
| Optimism (10) | ✓ | (EtherFiSafeFactory) | ✓ | ✓ ([aave/v4.md](../aave/v4.md)) |
| Ethereum (1) | — | ✓ | ✓ | — |
| Base (8453) | — | ✓ | ✓ | — |
| BNB (56) | — | ✓ | ✓ | — |
| Arbitrum (42161) | — | ✓ | ✓ | — |
| Avalanche (43114) | — | placeholder | ✓ | — |
| Polygon PoS (137) | — | proxy, unverified impl | ✓ | — |
| Robinhood Chain (4663) / Arc (5042) | — | — | — | — |

Vanity tell: `0xF4e147Db…d8CF` is one CREATE3 literal with a **different role per chain** (Optimism: EtherFiSafeFactory; Ethereum/Base/BNB/Arbitrum: TopUpSourceFactory; Avalanche: placeholder).

---

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| All §3 rows, TopUpSourceFactory, TradingSafeFactory | UUPS `ERC1967Proxy` (122/135 B) | impl slot set, admin slot `0x0` | `_authorizeUpgrade` → `RoleRegistry.onlyUpgrader` = `RoleRegistry.owner()` = Cash Timelock `0x9106…4434` (2 days) on Optimism |
| EtherFiSafe, TopUp (per user) | `BeaconProxy` | beacon = the factory | `upgradeBeaconImplementation(address)` on the factory → `BeaconImplemenationUpgraded` |
| Module contracts (Liquid, Stake, Frax, Stargate, Midas, OpenOcean, …) | mostly immutable | impl slot `0x0` | replaced by whitelist change (`ModulesConfigured` on the DataProvider) |

---

## 7. Detection invariants & gotchas

1. **All Cash activity is emitted by one address.** Filter `CashEventEmitter` `0x380B…81acB` and read `safe` (topic1) to get the user. CashModule itself emits only `Upgraded`/`Initialized`.
2. **`Spend` is the card swipe.** `Spend(safe, txId, binSponsor, tokens[], amounts[], amountInUsd[], totalUsdAmt, mode)`. `binSponsor` selects the settlement dispatcher (enum `BinSponsor`: 0 Reap, 1 Rain, 2 PIX, 3 CardOrder). `mode` follows enum `Mode`: 0 = Credit (borrow), 1 = Debit.
3. **Withdrawals have a delay.** `WithdrawalRequested(…, finalizeTimestamp)` → `WithdrawalProcessed` after the delay, or `WithdrawalCancelled`. A recovery or owner change near a pending withdrawal is a takeover signal.
4. **Safe recovery.** `Recovery(newOwner, startTime)` → `AccountRecovered(newOwner)` or `RecoveryCancelled()` on the user safe. `IncomingOwnerSet` starts an owner change. Alert on these for high-balance safes.
5. **Bridge-adapter events appear at the factory.** The TopUpSourceFactory `delegatecall`s adapters. `BridgeViaCCTP`, `BridgeOFT`, `BridgeToOptimism`, `BridgeViaStargate` etc. are logged with the factory as emitter.
6. **Settlement leaves the protocol.** `FundsSettled(token, recipient, amount)` sends funds to the card issuer. `TransferToRefundWallet` and `FundsWithdrawn` are admin exits. `SettlementRecipientSet` changes where money goes: high-value alert.
7. **Legacy lending is winding down.** `DebtManager.MigratedToLendGateway(safe, debtUsd)` (22 of the last 150 logs) moves debt to Aave V4. New borrows show as `CashEventEmitter.LendBorrowed` plus Aave V4 Spoke events.
8. **The official module list is stale.** See §3. Trust `getWhitelistedModules()`.
9. **`BeaconProxyDeployed` means a new user** on Optimism (safe) and on top-up chains (TopUp contract). One user gets the same address on every chain.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_CASH_SPEND                 = '\x244f4cc0665ad7ee4709aa59b30d3ea581cecde1b0430a3f23a5dc609d4890fc'
TOPIC_CASH_CASHBACK              = '\x89d3571a498b5d3d68599f5f00c3016f9604aafa7701c52c1b04109cd909a798'
TOPIC_CASH_WITHDRAWAL_REQUESTED  = '\xc48955aee858164993e89d10d9ad1aaf03010012434dac8ebae005105b1d4d6d'
TOPIC_CASH_WITHDRAWAL_PROCESSED  = '\x5eed621d1eddc71f0ca04e002e24088109cd3fd594c7af230edbf9e73d616047'
TOPIC_CASH_WITHDRAWAL_CANCELLED  = '\x50efeea714c351006c4fa7822fb73539a491c1d587e149b8dc5bf4c1a7056066'
TOPIC_CASH_REPAY                 = '\xe4a1ae657f49cb1fb1c7d3a94ae6093565c4c8c0e03de488f79c377c3c3a24e0'
TOPIC_CASH_LEND_BORROWED         = '\x38578014f71a287d9193d79e855fe47d225d8e5637ef400a63adbccfce03fc85'
TOPIC_CASH_MODE_SET              = '\xf6eabb9d9f10b3f417c46c38955eb7aea4886a913b32069a91a2af002dffee8d'
TOPIC_CASH_SPENDING_LIMIT        = '\x386efab796ecb0c216c9a39430a74f99716e683b28c915533174087017fe5d2d'
TOPIC_SAFE_EXEC_FROM_MODULE      = '\xfdf8460245894f3316dac7bb64530a1ca0d54faa23a8fa680cf3e3db32661537'
TOPIC_SAFE_RECOVERY              = '\x3dd16130d88f9c4aacc13e83eeed8a5180cc85ab0b098c220e0736cc40c59818'
TOPIC_SAFE_ACCOUNT_RECOVERED     = '\x444b9fc80713a03bfc01b03089babd94aa51edececce36355031fd7d1ed50b4a'
TOPIC_SAFE_OWNERS_CONFIGURED     = '\xe08e325dc20947840f420f7c361a8cdd6c074d5e577754e222e41ff918ec83ec'
TOPIC_MODULES_CONFIGURED         = '\xeb11e8ccbe97d4a65bf30443d702bdaa76e75ddfc0fe83d3e29e1b52385fd62d'
TOPIC_BEACON_PROXY_DEPLOYED      = '\x5889f63567a2730b47d0d74082206509fb86668d46a900bd695e655d099d586e'
TOPIC_BEACON_IMPL_UPGRADED       = '\xd8518b5f9760cf035849134f93f54b517edb9f10ce176b56bf030f3f9440389a'
TOPIC_DM_BORROWED                = '\x3fc499aeb0bb1cb58b6de8b02b3f86f4e7394e9690bef0110e32ced8a5631045'
TOPIC_DM_REPAID                  = '\x861660e9b7ead7183d53fe928b5638c7b57a7bcf16a89d7fdb04db65ce3ad6d5'
TOPIC_DM_LIQUIDATED              = '\xfd54f2a27ee93a2b60fa895931f0067b8eab4f20662e14ef1ef0720eb772ea9c'
TOPIC_DM_MIGRATED_TO_GATEWAY     = '\x4836b2e457ff051f5a3c300848cc5dc19535c7be3b5233117b1a9ec7c189eebe'
TOPIC_SD_FUNDS_SETTLED           = '\x6435cb7c5450b5cfb0e43a0dcf384145e74d42dd7538567c16230f84544ed152'
TOPIC_SD_FUNDS_WITHDRAWN         = '\xe9171aeff46c37ab955b8aff908e14ae9732bd06634fa131226cfe5c25bfd2fb'
TOPIC_SD_RECIPIENT_SET           = '\x9594a5d709ec968361fa251e01afdc4d45867e08a1245c98fd7279fd3d3a4e62'
TOPIC_SD_REFUND_TRANSFER         = '\xd8f7c78f293a52ff06285b09819d7625a13eb9080c991b7fac88cbf2b7239e89'
TOPIC_TOPUPDEST_TOPUP            = '\x2ff66106aff37c72533c0686de51adb6d1b86dd1709407dc6a2236533ebe3c19'
TOPIC_TOPUP_FACTORY_BRIDGE       = '\xdeb96a3e5294fabe38d8824397be657fbe695d61f3457274027345cca6f26aaa'
TOPIC_ADAPTER_BRIDGE_VIA_CCTP    = '\x80b19d4ae73b8f503d0df885f7a6252161aa3f8ff59f61389259541309d7f69e'
TOPIC_ADAPTER_BRIDGE_OFT         = '\xd78f10ceb472c9a2682253afe5f9512921f72e176a757030e53338fe095bfdb9'
TOPIC_ADAPTER_BRIDGE_TO_OPTIMISM = '\x23560d34d78cbe245d17fea7af14f51642dc0aca2e9d425de7a67421e5f41639'
TOPIC_ADAPTER_BRIDGE_STARGATE    = '\x07eddb5fc8fae77b818eb5aaa2ae709369cbba09470a6e872639876836839cb6'
TOPIC_ADAPTER_LIQUID_BRIDGED     = '\xc0287a34aa851832b0d4e1a2abfefd65dad182809adaf4b3cf538d8c871c5416'
-- ===== Selectors (chain-agnostic) =====
SEL_CASH_SPEND                   = '\x4e309099'
SEL_CASH_BORROW                  = '\xd274056c'
SEL_CASH_PROCESS_WITHDRAWAL      = '\x3c1a5012'
SEL_SAFE_EXEC_FROM_MODULE        = '\xbcde317c'
SEL_SAFE_FACTORY_DEPLOY          = '\xff024c7b'
SEL_TOPUPDEST_TOPUP              = '\x2b4911e0'
SEL_TOPUP_FACTORY_BRIDGE         = '\x0bf5d35e'
-- ===== Addresses =====
OP_ETHERFI_CASH_MODULE           = '\x7ca0b75e67e33c0014325b739a8d019c4fe445f0'
OP_ETHERFI_CASH_EVENT_EMITTER    = '\x380b2e96799405be6e3d965f4044099891881acb'
OP_ETHERFI_SAFE_FACTORY          = '\xf4e147db314947fc1275a8cbb6cde48c510cd8cf'
OP_ETHERFI_DATA_PROVIDER         = '\xdc515cb479a64552c5a11a57109c314e40a1a778'
OP_ETHERFI_DEBT_MANAGER          = '\x0078c5a459132e279056b2371fe8a8ec973a9553'
OP_ETHERFI_TOPUP_DEST            = '\x3a6a724595184dda4be69db1ce726f2ac3d66b87'
OP_ETHERFI_SETTLEMENT_RAIN       = '\x50a233c4a0bb1d7124b0224880037d35767a501c'
OP_ETHERFI_SETTLEMENT_REAP       = '\x9623e86df854ff3b48f7b4079a516a4f64861db2'
OP_ETHERFI_SETTLEMENT_PIX        = '\x95aaddd43b6edf838ec486e9f9814787212bf42d'
OP_ETHERFI_SETTLEMENT_CARDORDER  = '\xb14fdfd7d2cffb6cc6953c1b80f1b1d12c2f766a'
OP_ETHERFI_CASH_TIMELOCK         = '\x9106cd76e10ac60d1dd16144243416ebd2c64434'
ETHERFI_TOPUP_SOURCE_FACTORY     = '\xf4e147db314947fc1275a8cbb6cde48c510cd8cf'   -- ETH/Base/BNB/Arb
ETHERFI_TRADING_SAFE_FACTORY     = '\xe54e00b0e72f8fc8cb7e124c378bad2e7371d2b8'   -- all 7 publicnode chains
```

---

## 9. Verification & sources

How the constants were verified (2026-10-30):
- **Topic0 / selectors:** computed locally as `keccak256(signature)` from the verified Optimism implementation ABIs (CashModuleCore, CashEventEmitter, EtherFiSafe, EtherFiSafeFactory, DebtManagerCore, SettlementDispatcherV2, TopUpDest) and the Base `TopUpFactory` ABI (Sourcify). Bridge-adapter topics computed from `src/top-up/bridge/*.sol` and matched to live factory logs on Base and Ethereum. Live log pages on Optimism decoded with no unknown topic0 for the emitter, factory, DebtManager, TopUpDest and the Rain/Reap dispatchers.
- **Addresses:** official Deployed Contracts list and `cash-v3/deployments/mainnet/*/deployments.json`; existence, impl slot and code size checked on all nine chains. The module whitelist was read with `getWhitelistedModules()` / `getDefaultModules()` / `getCashModule()` on the DataProvider. Timelock delay read with `getMinDelay()`.

Authoritative sources:
- [etherfi-protocol/cash-v3](https://github.com/etherfi-protocol/cash-v3) — source and deployment files.
- [ether.fi Deployed Contracts](https://etherfi.gitbook.io/etherfi/developers/contracts-and-integrations/deployed-contracts) · [Cash technical documentation](https://etherfi.gitbook.io/etherfi/products/cash/technical-documentation) · [Account upgrade](https://etherfi.gitbook.io/etherfi/products/cash/account-upgrade) · [Lending market parameters](https://etherfi.gitbook.io/etherfi/products/borrow/lending-market-parameters)
- Explorers: [Optimism explorer](https://explorer.optimism.io) · [Etherscan](https://etherscan.io) · [Basescan](https://basescan.org)
