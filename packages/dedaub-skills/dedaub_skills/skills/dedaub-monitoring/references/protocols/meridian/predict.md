# Meridian Predict — Topics, Selectors, Addresses (Robinhood Chain + Arbitrum + Polygon)

**Status:** verified against live RPC on Robinhood Chain (4663), Arbitrum One (42161) and Polygon PoS (137) on 2026-10-30. ABIs come from the official front-end SDK (`sapiencexyz/sapience`, `src/lib/sdk/abis/*.json`); every ABI was matched against the live bytecode (all selectors and events present, except where noted).
**Scope:** the Meridian prediction-market contracts (formerly **Sapience**, rebranded to Meridian Predict): escrow, LP vaults, position-token factory, secondary-market escrow, condition resolvers, onboarding sponsor and the LayerZero bridge. The core runs on **Robinhood Chain (4663)**. A position-token bridge peer runs on **Arbitrum (42161)** and a Polymarket condition reader runs on **Polygon (137)**. Topics and selectors are chain-agnostic. Addresses are network-specific.

A **prediction** is a two-sided bet. A predictor and a counterparty each lock USDe (`0x5d3a1Ff2…ef34`) in the `PredictionMarketEscrow` and receive ERC-20 **position tokens** (predictor token and counterparty token). The `PredictionMarketTokenFactory` deploys these tokens per "pick config" (a set of `(resolver, conditionId, outcome)` picks). Resolvers settle each condition. The escrow then settles the prediction and holders redeem tokens for USDe. The `PredictionMarketVault` is the passive counterparty: LPs deposit USDe and a manager approves vault funds for escrow positions. Conditions mirror Polymarket (Gnosis Conditional Tokens on Polygon): the Polygon reader reads payouts and sends them to the Robinhood resolver over LayerZero.

All contracts are **immutable** (no proxy). Every Robinhood contract is owned by Safe `0x99a8…212c` (1.4.1, **threshold 1 of 2 owners**).

---

## 0. Contract families

| Contract | Role | Chain |
|----------|------|-------|
| **PredictionMarketEscrow** | Mint (lock collateral, mint position tokens), settle, redeem, burn (mutual exit). Holds 40,199.89 USDe on 2026-10-30. | Robinhood |
| **PredictionMarketVault** ("Meridian Robinhood Vault") | Main LP vault (shares ERC-20), asset USDe, async deposit/withdraw requests, emergency mode. Holds 994,337.55 USDe. | Robinhood |
| **Single-leg vault** ("Meridian Robinhood Single-Leg Vault") | Same contract type (same 16,036 B size, different code hash). Holds 19,841.46 USDe. | Robinhood |
| **PredictionMarketTokenFactory** | CREATE2 deployer of position tokens; `deployer()` = the escrow. | Robinhood (+ twin on Arbitrum) |
| PredictionMarketToken | Per-side ERC-20 position token; `mint`/`burn` by the escrow (or bridge). | Robinhood (+ bridged copies on Arbitrum) |
| **SecondaryMarketEscrow** | Atomic OTC swap of position tokens for collateral (signed trades). | Robinhood |
| **ConditionalTokensConditionResolver** | LayerZero receiver of Polymarket condition payouts from the Polygon reader. | Robinhood |
| **ManualConditionResolver** | Approved settlers set outcomes directly. | Robinhood |
| **OnboardingSponsor** | Pays a predictor's collateral within a budget (sponsored mints). | Robinhood |
| **PredictionMarketBridge** | LayerZero bridge of position tokens Robinhood → Arbitrum (locks here). | Robinhood |
| **PredictionMarketBridgeRemote** | Bridge peer; mints bridged position tokens through its own token factory. | Arbitrum |
| **ConditionalTokensReader** | Reads Gnosis CT payouts and sends them to the Robinhood resolver. | Polygon |

---

## 1. Topics (chain-agnostic)

### 1.1 PredictionMarketEscrow

| topic0 | Event |
|--------|-------|
| `0x2d4ed813b53c17a12aaa4afc8753d89c6e7c19832cd77e9cf7eded87d041332d` | `PredictionCreated(bytes32 indexed predictionId, address indexed predictor, address indexed counterparty, address predictorToken, address counterpartyToken, uint256 predictorCollateral, uint256 counterpartyCollateral, bytes32 refCode, bytes32 pickConfigId)` — **position tokens minted, collateral in** |
| `0xd752175fe73028b933ce110fbf0ff2e6e254cd0384b5773960fe1114e29bdda6` | `CollateralDeposited(bytes32 indexed predictionId, uint256 totalAmount)` |
| `0xfcd98b53416b6b58751d427451c1676e86d69ce5e08a9c6dc51be484e6b68794` | `PickConfigCreated(bytes32 indexed pickConfigId, address predictorToken, address counterpartyToken, (address,bytes,uint8)[] picks)` |
| `0x19a1ab7281f31c1c0269a711a1f8f8f120603fae8c9a428c174a353e1a42a36c` | `PredictionSettled(bytes32 indexed predictionId, uint8 result, uint256 predictorClaimable, uint256 counterpartyClaimable, bytes32 refCode)` |
| `0x0940a538f31336c9c4c8b69c2a9c162248b0cbd3d8754dd98b57924473d062f2` | `TokensRedeemed(bytes32 indexed pickConfigId, address indexed holder, address indexed positionToken, uint256 tokensBurned, uint256 collateralPaid, bytes32 refCode)` — **collateral out** |
| `0x1dec3c594461ff2a5efb3a3ec8dc40c1d022cec67babb4163b3980f98f3c99c5` | `PositionsBurned(bytes32 indexed pickConfigId, address indexed predictorHolder, address indexed counterpartyHolder, uint256 predictorTokensBurned, uint256 counterpartyTokensBurned, uint256 predictorPayout, uint256 counterpartyPayout, bytes32 refCode)` — mutual early exit |
| `0x11383ef262d16356f5d9a3521f309cf2655487c4445fc0de016704935b6e58da` | `DustSwept(bytes32 indexed pickConfigId, address indexed recipient, uint256 amount)` |
| `0x0456aca3fbe5d05290327a61730fbe7c862ea1baf6b1da1c68a29ff54c22623e` | `SessionKeyRevoked(address indexed owner, address indexed sessionKey, uint256 revokedAt)` (same topic0 on SecondaryMarketEscrow) |

Live sample (blocks 100,824,352–101,824,352): `CollateralDeposited` 52, `PredictionCreated` 52, `PickConfigCreated` 48, `PredictionSettled` 43, `TokensRedeemed` 39.

### 1.2 PredictionMarketVault (main and single-leg)

| topic0 | Event |
|--------|-------|
| `0x4bbff5ff15bd29f2f89bf775111d06fa58687637c5f4c378236ab2eb7efd4da3` | `PendingRequestCreated(address indexed user, bool direction, uint256 shares, uint256 assets)` |
| `0x68f2bac2f315fc91af2d1be6aecfd21d30ce271d7318b725eaf192398952e54f` | `PendingRequestProcessed(address indexed user, bool direction, uint256 shares, uint256 assets)` — **LP deposit or withdrawal executed** |
| `0x690561cdc32a399f9f903089c233c90ef3b53917860783bfbcd5050965f1ad16` | `PendingRequestCancelled(address indexed user, bool direction, uint256 shares, uint256 assets)` |
| `0x1ccb38018cedc62b333e3bf6dead6d44d6f053e3a7e770772a1147fcc7fb1f3f` | `FundsApproved(address indexed manager, uint256 assets, address targetProtocol)` — **manager lets a protocol pull vault USDe** |
| `0x1ce760147aa1227538c72913854edd45cc434b0f6c646a298cd67080f04a369c` | `EscrowRedeemed(address indexed escrow, address indexed positionToken, uint256 amount, uint256 payout, bytes32 refCode)` |
| `0x7d22abaa6285cc6a86b7e1d7d7b94a20044697001d6249a0f0b19d804ed77a9e` | `EscrowBurned(address indexed escrow, bytes32 indexed pickConfigId)` |
| `0x2e5a1930def2f974808cd3dd28f6606d8d2cb5d7adb78f6761ea31062ced1a33` | `EmergencyModeUpdated(bool emergencyMode)` |
| `0x56da9a5ae0bcf6e7c3fdd78a10550e7d0458de1c39bfb7f6e96a3e92dd344a68` | `EmergencyWithdrawal(address indexed user, uint256 shares, uint256 assets)` |
| `0xdac3632743b879638fd2d51c4d3c1dd796615b4758a55b50b0c19b971ba9fbc7` | `ManagerUpdated(address indexed oldManager, address indexed newManager)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` / `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Paused(address)` / `Unpaused(address)` |
| `0x23a8022949b47ace445d590324eb7e4204fc27254d3acf1f41609a02a805e1b1` | `ExpirationTimeUpdated(uint256 oldExpirationTime, uint256 newExpirationTime)` |
| `0xb505669a84c5f128738565bee00373350f8ceed47ad5dec41b0aa44cf190ea7b` / `0xc33d8cc58e3a818a4a83430b4d5f2ba86c7b72ad59c9865e4e62514ed78d093f` | `DepositInteractionDelayUpdated(uint256,uint256)` / `WithdrawalInteractionDelayUpdated(uint256,uint256)` |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` (Ownable2Step) |
| `0xddf252ad…b3ef` / `0x8c5be1e5…c925` | `Transfer` / `Approval` (vault share ERC-20) |

### 1.3 Position tokens and secondary market

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x1b4fd659e4acd5d9815e89e3121e07040378b06b48db2e660335c4d4d34a1ff3` | `TokenDeployed(bytes32 indexed pickConfigId, bool indexed isPredictorToken, address token, bytes32 salt)` | TokenFactory (96 logs in the sample) |
| `0xe6c88b191a9a46395cf85a7dd6dacf4a85212007fd5d0ebba0d688f2463b7408` | `TradeExecuted(bytes32 indexed tradeHash, address indexed seller, address indexed buyer, address token, address collateral, uint256 tokenAmount, uint256 price, bytes32 refCode)` | SecondaryMarketEscrow |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | each position token |

### 1.4 Resolvers and sponsor

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xd51b7654de6c35da107817ecef62e0a008d0d246709c53babba4e32a40fb5b66` | `ConditionResolved(bytes conditionId, bool isIndecisive, bool resolvedToYes)` | both resolvers — **outcome set** |
| `0x9c576f8d187420a1a90d38bbe16a9be675a74dbb86e873df558e1f353105e528` | `ConditionResolutionDetail(bytes32 indexed conditionId, bool invalid, bool nonDecisive, bool resolvedToYes, uint256 payoutDenominator, uint256 noPayout, uint256 yesPayout, uint256 timestamp)` | ConditionalTokensConditionResolver |
| `0xdb8d46ffe47dcc30909d995729a81ac7cfdf06937bbf3b0f6b3c507929848e7b` | `ConditionResolutionDetail(bytes32 indexed conditionId, uint256 yesWeight, uint256 noWeight, address indexed settler)` | ManualConditionResolver (different topic0, same name) |
| `0x7cc192543075d048bda6651839216afe0940208189d8505c750be1ebb1c3077c` / `0x6fb1d52d3d220b332827a2d78aaa8fc2da7c48e2a2e29e1c264291787628e89e` | `SettlerApproved(address indexed settler)` / `SettlerRevoked(address indexed settler)` | ManualConditionResolver |
| `0x667c4919e9f81a90720a09575224afc1e5c12c569c86afa746138907a029cd0d` | `BridgeConfigUpdated((uint32,address) config)` | CT resolver, Polygon reader |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` | LayerZero OApps (resolver, reader, bridges) — **trust root change** |
| `0x7e747b454c55645836f5bf5b9554cb46e8a7cd19601eb58b14f8277adc36cd2e` | `Sponsored(address indexed predictor, uint256 collateral, address indexed escrow)` | OnboardingSponsor |
| `0x107877fe73fde3011599848fdc241395c13078377bc23c53e1b2d791340ba72e` / `0x3f431c3b632a0797b94391f1fc7cd2524b2058ad2e0fd0bbc3bf8a6b4e51d619` / `0x4f51b727dd162ccf3c38c1e738d5af75a9ec94b051e0f27e8f65f3986af52c54` | `BudgetSet(address indexed beneficiary, uint256 allocated)` / `BudgetManagerSet(address indexed manager)` / `MatchLimitSet(uint256 matchLimit)` | OnboardingSponsor |

Polygon reader events (types from the public signature database; `indexed` flags not known): `ResolutionRequested(bytes32,bytes32,uint256)` `0x23cc117a973a48c4d2bf6d4b6b46dd07110606ca1edbf21e6c09135b26416627`, `ResolutionSent(bytes32,uint256,uint256,uint256,bytes32,uint256)` `0x3de49c63d0ac758b5a2ce8e3249695c1839826dc5ba17bda32d06b1c10c88521`, `ConfigUpdated(address)` `0x89b8aa6a0bad94aca607eff7d3631d67e0e67b2c775044f517a269ae8b6662af`.

### 1.5 Bridge (Robinhood `PredictionMarketBridge` and Arbitrum `PredictionMarketBridgeRemote`)

| topic0 | Event | Side |
|--------|-------|------|
| `0xc0e3fd33faee4334193a75f8e95207ab0e96945f538c8fe93e6017faabc803f6` | `BridgeInitiated(bytes32 indexed bridgeId, address indexed token, address indexed sender, address recipient, uint256 amount, uint64 createdAt, bytes32 refCode)` | both |
| `0x95d209edc2dd51498eb0f9b4c7fb85223de3a46f6a83e0aba5d2d0e9a0d72077` | `TokensReleased(bytes32 indexed bridgeId, address indexed token, address indexed recipient, uint256 amount)` | Robinhood (unlock) |
| `0x4e6aaa4e458d16db05d9c9657dd87dbeeb891796cc94cefeab25cfdaa9b5b246` | `TokensMinted(bytes32 indexed bridgeId, address indexed token, address indexed recipient, uint256 amount, bool isNewDeployment)` | Arbitrum (mint) |
| `0xf858475f6ceaf814cde2c67e14c95826e45be5bfd12b07fdb49acbf06ca75a67` | `BridgeCompleted(bytes32 indexed bridgeId)` | both |
| `0xa0cfb40f77100f2a67bca980b062298a58088e62f90e6513125a8bfa314799b2` | `BridgeProcessed(bytes32 indexed bridgeId, bool alreadyProcessed)` | both |
| `0x169c962092c0f4d6357ffd25919f4a251ff047e440ad441d223d53c05c223922` | `BridgeRetried(bytes32 indexed bridgeId, bytes32 refCode)` | both |
| `0xda94d5a00f848ba516ce6d7d3defb48a622b37484bc1b7214aae538c6cbcec1d` / `0x6b16a26cbb70417c03e034d7bfbf54ced3fcce5ce350fde5d6d723a5cf7ab7d5` / `0x6dc078bbe79a8535f2283f55845bd0d941d31635cf984c6ccd3ca03a8157b06e` | `AckSent(bytes32 indexed,uint256)` / `AckSendFailed(bytes32 indexed)` / `AckInsufficientBalance(bytes32 indexed,uint256,uint256)` | both |
| `0x3cd59993b68a111e221a5952cef1ff0f2d39bf72d0b2fda67e4f112c7b583388` | `BridgeConfigUpdated((uint32,address,uint128) config)` | both |
| `0x24cd1310c8883cbeaf5b805ab13586ce018b79c022827158ff3e8df14d344936` | `FactoryUpdated(address factory)` | Arbitrum (ABI only; not in live bytecode) |
| `0x94b2de810873337ed265c5f8cf98c9cffefa06b8607f9a2f1fbaebdfbcfbef1c` | `ETHWithdrawn(address indexed to, uint256 amount)` | both |

No bridge logs on Robinhood in blocks 100.8 M–101.8 M.

---

## 2. Function signatures (chain-agnostic)

| Selector | Signature | Contract / notes |
|----------|-----------|------------------|
| `0x2e3f9da8` | `mint(((address,bytes,uint8)[],uint256,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes32,bytes,bytes,address,bytes))` | Escrow. `(predictionId, predictorToken, counterpartyToken)`. Two signed sides. |
| `0xd32a9cd9` | `settle(bytes32,bytes32)` | Escrow. `(predictionId, refCode)`. Permissionless once resolved. |
| `0x992c3e4b` | `redeem(address,uint256,bytes32)` | Escrow. `(positionToken, amount, refCode)`. |
| `0xcd3bd974` | `burn((bytes32,uint256,uint256,address,address,uint256,uint256,uint256,uint256,uint256,uint256,bytes,bytes,bytes32,bytes,bytes))` | Escrow. Mutual exit. |
| `0x6c42b2f0` | `sweepDust(bytes32,address)` | Escrow. |
| `0x84f4fc6a` | `revokeSessionKey(address)` | Escrow / SecondaryMarketEscrow. |
| `0xe945a069` / `0xae2ebd7f` | `requestDeposit(uint256,uint256)` / `requestWithdrawal(uint256,uint256)` | Vault. |
| `0x96cb1cfe` / `0x3c1a5012` / `0x925ab1c9` / `0xa10e2c90` | `processDeposit(address)` / `processWithdrawal(address)` / `batchProcessDeposit(address[])` / `batchProcessWithdrawal(address[])` | Vault manager. |
| `0x3d561602` / `0x22611280` | `cancelDeposit()` / `cancelWithdrawal()` | Vault. |
| `0xf422d50e` | `approveFundsUsage(address,uint256)` | Vault manager. **Approves a protocol to pull USDe.** |
| `0x208a37fd` / `0x8b2985c2` | `redeemFromEscrow(address,address,uint256,bytes32)` / `burnFromEscrow(address,(…))` | Vault manager. |
| `0x4c17b530` / `0x5312ea8e` | `toggleEmergencyMode()` / `emergencyWithdraw(uint256)` | Vault owner / user. |
| `0xd0ebdbe7` / `0x8456cb59` / `0x3f4ba83a` | `setManager(address)` / `pause()` / `unpause()` | Vault owner. |
| `0x311e9525` | `deploy(bytes32,bool,string,string,address)` | TokenFactory (deployer only). `(address)`. |
| `0x96214735` / `0xa88ac8cd` | `setDeployer(address)` / `renounceOwnershipSafe()` | TokenFactory owner. |
| `0x40c10f19` / `0x9dc29fac` | `mint(address,uint256)` / `burn(address,uint256)` | PredictionMarketToken (escrow/bridge only). |
| `0x52bb0979` | `executeTrade((address,address,address,address,uint256,uint256,uint256,uint256,uint256,uint256,bytes,bytes,bytes32,bytes,bytes))` | SecondaryMarketEscrow. |
| `0xc6fa9075` / `0x067b40cb` | `settleCondition(bytes32,(uint256,uint256))` / `settleConditions(bytes32[],(uint256,uint256)[])` | ManualConditionResolver (settlers). |
| `0x1b953557` / `0x3208b3b0` / `0xa4cd1a42` | `approveSettler(address)` / `approveSettlers(address[])` / `revokeSettler(address)` | ManualConditionResolver owner. |
| `0x13137d65` | `lzReceive((uint32,bytes32,uint64),bytes32,bytes,address,bytes)` | payable. CT resolver, bridges (LayerZero endpoint only). |
| `0x3400288b` / `0xca5eb5e1` | `setPeer(uint32,bytes32)` / `setDelegate(address)` | LayerZero OApps, owner. |
| `0x90919c2e` / `0xf5878d32` | `setBridgeConfig((uint32,address))` / `setBridgeConfig((uint32,address,uint128))` | Resolver+reader / bridges, owner. |
| `0xe779e226` | `getBridgeConfig()` | view. Remote eid + peer. |
| `0xd2603203` | `bridge(address,address,uint256,bytes32)` | payable. Bridges. `(bytes32 bridgeId)`. |
| `0xafbf092f` / `0xea8aa25d` / `0x4782f779` | `retry(bytes32,bytes32)` / `sendAckWithFee(bytes,bytes,(uint256,uint256))` / `withdrawETH(address,uint256)` | Bridges. |
| `0x89869599` | `fundMint(address,((address,bytes,uint8)[],uint256,uint256,address,address,uint256,uint256,uint256,uint256,bytes,bytes,bytes32,bytes,bytes,address,bytes))` | OnboardingSponsor. **Live selector**; the SDK ABI lists an older `0xb060c207` (`bytes32` pick field), absent from the bytecode. |
| `0x74bfb426` / `0xa03a77ad` / `0x8588b687` / `0xa3661e4f` | `setBudget(address,uint256)` / `setBudgets(address[],uint256[])` / `setBudgetManager(address)` / `setMatchLimit(uint256)` | OnboardingSponsor. |
| `0x64aff9ec` / `0x9646f3ea` | `sweepToken(address,address,uint256)` / `sweepNative(address,uint256)` | OnboardingSponsor owner. |
| `0x5717192a` / `0x8439252e` | `requestResolution(bytes32)` / `quoteResolution(bytes32)` | Polygon reader. |

---

## 3. Addresses

All verified with `eth_getCode` on 2026-10-30. No contract here is a proxy (EIP-1967 implementation slot = 0 for all).

### 3.1 Robinhood Chain (chain ID 4663)

| Role | Address | One-liner |
|------|---------|-----------|
| **PredictionMarketEscrow** | `0xE4cea507b19796362A5a28Fa7cb705A3F1866213` | Core escrow. `collateralToken()` = USDe. `tokenFactory()` = factory below. 20,951 B. |
| **PredictionMarketVault** (main) | `0x79cB914f3F336426E89FaB55A9488AB25770552D` | LP vault. `manager()` = EOA `0x69078941fa413f7d224dac21c490d5f1cc75e2dd`. |
| **Single-leg vault** | `0xdD9B39FFedf8602Ff86c3621f30Bbc598a2Df223` | LP vault. `manager()` = `0x952165d1606d8be44cd60fb2549371f65a55b0f4`. |
| **PredictionMarketTokenFactory** | `0xa3261443CB7730BfD6dC93C9b95A71f85Fb00c6F` | `deployer()` = escrow. |
| **SecondaryMarketEscrow** | `0x7E318ef37c3bC3d0cBA205Af2D1Fc9F9CeFEB5df` | OTC position-token trades. No `owner()`. No logs in the sample. |
| **ConditionalTokensConditionResolver** | `0xE42847eE3feE1B29065F14D39EcF664A04d70475` | Peer: Polygon reader (eid 30109). 12 `ConditionResolved` in the sample. |
| **ManualConditionResolver** | `0xdC1Fa830aD1de01f1EF603749f48bD73384286BE` | Owner-approved settlers. |
| **OnboardingSponsor** | `0xd8d656427A8D4d65ecc83c34E5e7685251D9ba7C` | Sponsored mints. |
| **PredictionMarketBridge** | `0xE538DA0b97e288A1A4C311fdEB1E68F3F87fDE01` | Peer: Arbitrum remote (eid 30110). |
| Owner Safe | `0x99a8e932b40ed10dd03ce11e424030efa997212c` | Safe 1.4.1, **1-of-2**. Owns all of the above except SecondaryMarketEscrow. |
| USDe (collateral) | `0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34` | Ethena USDe OFT. Not a Meridian contract. |

### 3.2 Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **PredictionMarketBridgeRemote** | `0x8d562a9bbfc47a6c8e208b0b0fa67bf4f7f773bf` | Peer of the Robinhood bridge (`getBridgeConfig()` → eid 30416 = Robinhood, `0xE538…DE01`). 14,125 B. Owner EOA `0x20c54b26f00bb323908011792fadeed278202086`. |
| **PredictionMarketTokenFactory** (twin) | `0xa3261443CB7730BfD6dC93C9b95A71f85Fb00c6F` | **Same address and code hash as Robinhood**, but `deployer()` = the bridge remote. Mints bridged position tokens. Owner EOA `0x20c5…2086`. |

The front-end SDK lists a different Arbitrum `predictionMarketBridgeRemote` (`0x6810b69c…88BC`). Its `getBridgeConfig()` points to LayerZero eid 30391 (the Ethereal deployment), not to Robinhood Chain. The live Robinhood bridge points to `0x8d56…73bf`.

### 3.3 Polygon PoS (chain ID 137)

| Role | Address | One-liner |
|------|---------|-----------|
| **ConditionalTokensReader** | `0x3e402e220fb36f4d849f8b3b3b139f68ddb69c98` | Reads Polymarket (Gnosis CT) payouts. `getBridgeConfig()` → eid 30416, Robinhood resolver `0xE428…0475`. 6,680 B. Owner EOA `0x20c5…2086`. |

### 3.4 Other chains and decoys

Ethereum, Base, BNB, Avalanche, Optimism and Arc: `eth_getCode` = `0x` for all Robinhood Predict addresses (2026-10-30).

**Decoy:** `0x79cB914f…552D` (the Robinhood main vault) also has code on **Polygon**. There it is a retired Sapience `ConditionalTokensReader` (6,680 B; listed as `legacy` in the SDK), not a vault. Key on `(chainId, address)`.

## 4. Cross-chain summary

| Chain (ID) | Escrow | Vaults | TokenFactory | Resolvers | Bridge | CT reader |
|------------|--------|--------|--------------|-----------|--------|-----------|
| Robinhood (4663) | `0xE4ce…6213` | `0x79cB…552D`, `0xdD9B…F223` | `0xa326…0c6F` | `0xE428…0475`, `0xdC1F…86BE` | `0xE538…DE01` | — |
| Arbitrum (42161) | — | — | `0xa326…0c6F` (bridge twin) | — | `0x8d56…73bf` (remote) | — |
| Polygon (137) | — | decoy at `0x79cB…552D` | — | — | — | `0x3e40…9c98` |
| ETH / Base / BNB / Avax / OP / Arc | — | — | — | — | — | — |

## 5. Proxies

None. Every Predict contract on all three chains is a plain deployment (EIP-1967 implementation, admin and beacon slots = 0). A redeploy is the only way to change logic; the SDK keeps a `legacy` list per contract for earlier Ethereal and testnet deployments. Watch `OwnershipTransferred`, `PeerSet`, `BridgeConfigUpdated`, `SettlerApproved` and `ManagerUpdated` instead of `Upgraded`.

## 6. Detection invariants & gotchas

1. **Money in:** `PredictionCreated` + `CollateralDeposited` on the escrow (USDe `Transfer` into the escrow). **Money out:** `TokensRedeemed` and `PositionsBurned` (USDe out), plus vault `PendingRequestProcessed` for LP flows.
2. **The vault is the usual counterparty.** In the sample, 41 of 52 `PredictionCreated` logs had `counterparty` = the main vault. The vault manager pre-approves the escrow with `approveFundsUsage` (`FundsApproved`). A `FundsApproved` to an unknown `targetProtocol` is a drain signal.
3. **Outcomes come from two resolver paths.** Polymarket mirror (Polygon reader → LayerZero → CT resolver) and manual settlers. A `SettlerApproved` or `PeerSet` change can decide every open market. The owner Safe is 1-of-2, so one key can do it.
4. **`ConditionResolutionDetail` has two topic0s** (CT resolver `0x9c57…`, manual resolver `0xdb8d…`). `ConditionResolved` has one topic0 for both; key on emitter. `conditionId` in `ConditionResolved` is non-indexed `bytes`.
5. **Position tokens are created per pick config.** Index `TokenDeployed` on the factory (two per new pick config: predictor and counterparty) to build the token set; then follow `Transfer`.
6. **Bridged tokens on Arbitrum** are minted by the remote's factory twin at the **same address** as the Robinhood factory. A token address seen on both chains is the same pick-config token family, but balances are per chain.
7. **SDK drift.** The front-end ABI's `fundMint` (`0xb060c207`) is not in the live OnboardingSponsor; the live selector is `0x89869599`. The SDK's Arbitrum remote address is stale (see §3.2).
8. **`SessionKeyRevoked` topic0 is shared** by both escrows.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_PM_PREDICTION_CREATED       = '\x2d4ed813b53c17a12aaa4afc8753d89c6e7c19832cd77e9cf7eded87d041332d'
TOPIC_PM_COLLATERAL_DEPOSITED     = '\xd752175fe73028b933ce110fbf0ff2e6e254cd0384b5773960fe1114e29bdda6'
TOPIC_PM_PICK_CONFIG_CREATED      = '\xfcd98b53416b6b58751d427451c1676e86d69ce5e08a9c6dc51be484e6b68794'
TOPIC_PM_PREDICTION_SETTLED       = '\x19a1ab7281f31c1c0269a711a1f8f8f120603fae8c9a428c174a353e1a42a36c'
TOPIC_PM_TOKENS_REDEEMED          = '\x0940a538f31336c9c4c8b69c2a9c162248b0cbd3d8754dd98b57924473d062f2'
TOPIC_PM_POSITIONS_BURNED         = '\x1dec3c594461ff2a5efb3a3ec8dc40c1d022cec67babb4163b3980f98f3c99c5'
TOPIC_PMV_REQUEST_CREATED         = '\x4bbff5ff15bd29f2f89bf775111d06fa58687637c5f4c378236ab2eb7efd4da3'
TOPIC_PMV_REQUEST_PROCESSED       = '\x68f2bac2f315fc91af2d1be6aecfd21d30ce271d7318b725eaf192398952e54f'
TOPIC_PMV_FUNDS_APPROVED          = '\x1ccb38018cedc62b333e3bf6dead6d44d6f053e3a7e770772a1147fcc7fb1f3f'
TOPIC_PMV_ESCROW_REDEEMED         = '\x1ce760147aa1227538c72913854edd45cc434b0f6c646a298cd67080f04a369c'
TOPIC_PMV_EMERGENCY_MODE          = '\x2e5a1930def2f974808cd3dd28f6606d8d2cb5d7adb78f6761ea31062ced1a33'
TOPIC_PMV_EMERGENCY_WITHDRAWAL    = '\x56da9a5ae0bcf6e7c3fdd78a10550e7d0458de1c39bfb7f6e96a3e92dd344a68'
TOPIC_PMV_MANAGER_UPDATED         = '\xdac3632743b879638fd2d51c4d3c1dd796615b4758a55b50b0c19b971ba9fbc7'
TOPIC_PMTF_TOKEN_DEPLOYED         = '\x1b4fd659e4acd5d9815e89e3121e07040378b06b48db2e660335c4d4d34a1ff3'
TOPIC_SME_TRADE_EXECUTED          = '\xe6c88b191a9a46395cf85a7dd6dacf4a85212007fd5d0ebba0d688f2463b7408'
TOPIC_RES_CONDITION_RESOLVED      = '\xd51b7654de6c35da107817ecef62e0a008d0d246709c53babba4e32a40fb5b66'
TOPIC_CTRES_RESOLUTION_DETAIL     = '\x9c576f8d187420a1a90d38bbe16a9be675a74dbb86e873df558e1f353105e528'
TOPIC_MANRES_RESOLUTION_DETAIL    = '\xdb8d46ffe47dcc30909d995729a81ac7cfdf06937bbf3b0f6b3c507929848e7b'
TOPIC_MANRES_SETTLER_APPROVED     = '\x7cc192543075d048bda6651839216afe0940208189d8505c750be1ebb1c3077c'
TOPIC_LZ_PEER_SET                 = '\x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b'
TOPIC_PMB_BRIDGE_INITIATED        = '\xc0e3fd33faee4334193a75f8e95207ab0e96945f538c8fe93e6017faabc803f6'
TOPIC_PMB_TOKENS_RELEASED         = '\x95d209edc2dd51498eb0f9b4c7fb85223de3a46f6a83e0aba5d2d0e9a0d72077'
TOPIC_PMB_TOKENS_MINTED           = '\x4e6aaa4e458d16db05d9c9657dd87dbeeb891796cc94cefeab25cfdaa9b5b246'
TOPIC_SPONSOR_SPONSORED           = '\x7e747b454c55645836f5bf5b9554cb46e8a7cd19601eb58b14f8277adc36cd2e'
TOPIC_OWNERSHIP_TRANSFERRED       = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- ===== Selectors (chain-agnostic) =====
SEL_PM_MINT                       = '\x2e3f9da8'
SEL_PM_SETTLE                     = '\xd32a9cd9'
SEL_PM_REDEEM                     = '\x992c3e4b'
SEL_PM_BURN                       = '\xcd3bd974'
SEL_PMV_APPROVE_FUNDS_USAGE       = '\xf422d50e'
SEL_PMV_TOGGLE_EMERGENCY_MODE     = '\x4c17b530'
SEL_MANRES_SETTLE_CONDITION       = '\xc6fa9075'
SEL_LZ_SET_PEER                   = '\x3400288b'
SEL_PMB_BRIDGE                    = '\xd2603203'
SEL_SPONSOR_FUND_MINT             = '\x89869599'
-- ===== Addresses (network-specific) =====
RH_PM_ESCROW                      = '\xe4cea507b19796362a5a28fa7cb705a3f1866213'
RH_PM_VAULT                       = '\x79cb914f3f336426e89fab55a9488ab25770552d'
RH_PM_SINGLE_LEG_VAULT            = '\xdd9b39ffedf8602ff86c3621f30bbc598a2df223'
RH_PM_TOKEN_FACTORY               = '\xa3261443cb7730bfd6dc93c9b95a71f85fb00c6f'
RH_PM_SECONDARY_ESCROW            = '\x7e318ef37c3bc3d0cba205af2d1fc9f9cefeb5df'
RH_PM_CT_RESOLVER                 = '\xe42847ee3fee1b29065f14d39ecf664a04d70475'
RH_PM_MANUAL_RESOLVER             = '\xdc1fa830ad1de01f1ef603749f48bd73384286be'
RH_PM_ONBOARDING_SPONSOR          = '\xd8d656427a8d4d65ecc83c34e5e7685251d9ba7c'
RH_PM_BRIDGE                      = '\xe538da0b97e288a1a4c311fdeb1e68f3f87fde01'
RH_PM_OWNER_SAFE                  = '\x99a8e932b40ed10dd03ce11e424030efa997212c'
ARB_PM_BRIDGE_REMOTE              = '\x8d562a9bbfc47a6c8e208b0b0fa67bf4f7f773bf'
ARB_PM_TOKEN_FACTORY              = '\xa3261443cb7730bfd6dc93c9b95a71f85fb00c6f'
POLY_PM_CT_READER                 = '\x3e402e220fb36f4d849f8b3b3b139f68ddb69c98'
```

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed as `keccak256(signature)` from the SDK ABIs. Each ABI was matched against live bytecode: every function selector is in the dispatcher and every event topic is a `PUSH32`, except `EIP712DomainChanged` (never emitted), the CT resolver `ConditionResolutionDetail` (not a literal `PUSH32`, but seen in 12 live logs), `FactoryUpdated` (absent from the live remote) and `fundMint` (live selector `0x89869599` recomputed with the escrow's `(address,bytes,uint8)` pick tuple). Escrow, vault, factory and resolver counts come from `eth_getLogs` on `https://rpc.mainnet.chain.robinhood.com`.
- **Addresses:** Robinhood mainnet entries of the SDK `addresses.ts` (`CHAIN_ID_ROBINHOOD_MAINNET = 4663`) and the escrow address in DefiLlama-Adapters PR #19932. The Arbitrum remote and Polygon reader were found on-chain with `getBridgeConfig()` on the Robinhood bridge and resolver, and checked back from each peer. Owners from `owner()`, Safe thresholds from `getThreshold()`.
- **Chain coverage:** `eth_getCode` on all nine target chains; the Polygon `0x79cB…` and Arbitrum `0xa326…` hits were classified by code size, code hash and `deployer()`.

Sources:
- [sapiencexyz/sapience](https://github.com/sapiencexyz/sapience) — `src/lib/sdk/contracts/addresses.ts`, `src/lib/sdk/abis/`.
- [DefiLlama-Adapters PR #19932 (Meridian predict TVL)](https://github.com/DefiLlama/DefiLlama-Adapters/pull/19932) · [DefiLlama — Meridian Predict](https://defillama.com/protocol/meridian-predict)
- [Sapience audits](https://docs.sapience.xyz/user-guide/other-resources/audits) · [Meridian docs](https://docs.meridian.xyz)
- Explorers: [Robinhood Chain Blockscout — Escrow](https://robinhoodchain.blockscout.com/address/0xE4cea507b19796362A5a28Fa7cb705A3F1866213) · [Arbiscan — BridgeRemote](https://arbiscan.io/address/0x8d562a9bbfc47a6c8e208b0b0fa67bf4f7f773bf) · [Polygonscan — CT reader](https://polygonscan.com/address/0x3e402e220fb36f4d849f8b3b3b139f68ddb69c98)
