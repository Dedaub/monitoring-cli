# Pendle — PENDLE token, sPENDLE / vePENDLE, Incentives & Cross-chain — Topics, Selectors, Addresses (Ethereum, Arbitrum, Base, BNB, Optimism, Robinhood Chain, Avalanche)

**Status:** verified against live RPC on every listed chain and the canonical `pendle-finance/pendle-core-v2-public` repo (`deployments/<chainId>-core.json`, npm `@pendle/core-v2` ABIs) on 2026-10-30.
**Scope:** the token and incentive layer around Pendle V2: the PENDLE token on each chain, **sPENDLE** (current staking token, Ethereum only), the deprecated **vePENDLE** / `VotingController` / fee distributors, the per-chain `GaugeController`, the merkle reward distributors, the LayerZero V1 governance messaging endpoints, and the cross-chain PT periphery (PT OFT adapters, `PendleCrossChainSwapHub`, `OFTPTSwapper`, `FixedPricePTAMMV2`). Chains: Ethereum (1), Arbitrum One (42161), Base (8453), BNB Smart Chain (56), Optimism (10), Robinhood Chain (4663), Avalanche (43114, periphery only). **Not deployed on Polygon PoS (137) or Arc (5042).** Topics and selectors are chain-agnostic. Addresses are network-specific.

**Incentive model changed.** Until 2026 Pendle used Curve-style **vePENDLE** (lock PENDLE up to 2 years) on Ethereum. vePENDLE holders voted in the Ethereum `VotingController`. The controller broadcast weekly PENDLE rates over LayerZero V1 to each chain's `GaugeController`. The registry now lists `vePendle`, `votingController`, `feeDistributor` and `feeDistributorV2` under `deprecated`. The live staking token is **sPENDLE** (`0x999999999991e178d52cd95afd4b00d066664144`), a liquid ERC-20 with a 14-day cooldown (`cooldownDuration() = 1,209,600`) or a 5 % instant-unstake fee (`instantUnstakeFeeRate() = 5e16`). Each `GaugeController` now gets reward rates by an owner call (`setRewardDatas` → `UpdateMarketRewardV2`). The owner is `governanceProxy` `0x2ad631f7…f31e` on Ethereum and Robinhood Chain.

PENDLE is **not** one token across chains. Ethereum has the native token. Arbitrum, Base and Optimism use canonical-bridge tokens. BNB uses a Wormhole-wrapped token. Robinhood Chain uses a LayerZero V2 `PendleOFT`, paired with an Ethereum OFT adapter.

---

## 0. Contract families & versions

| Contract | Role | Status | Pattern |
|----------|------|--------|---------|
| **PENDLE** (Ethereum) | Native ERC-20 (`governance()` = `0x8119ec16…6ee1`) | Live | Immutable (9943 B) |
| PENDLE (Arbitrum) | Arbitrum standard-gateway token (`l1Address()` = ETH PENDLE, gateway `0x09e9222e…1eee`) | Live | Beacon proxy (760 B) |
| PENDLE (Base, Optimism) | OP-Stack `OptimismMintableERC20` (`bridge()` = `0x4200…0010`, `remoteToken()` = ETH PENDLE) | Live | Immutable |
| PENDLE (BNB) | Wormhole `BridgeToken` (Sourcify name) | Live | Beacon proxy (831 B), beacon `0xb6f6d86a…a6e7` |
| **PENDLE (Robinhood)** | LayerZero V2 `PendleOFT` (Sourcify), `owner()` = `governanceProxy`, endpoint `0x6f475642…dd5b` | Live | Immutable (16152 B) |
| PENDLE OFT adapter (Ethereum) | `WOFTAdapter` for ETH PENDLE, peer of the Robinhood OFT (eid 30101 → this address) | Live | Immutable |
| **sPENDLE** (`StakedPendle`) | Stake PENDLE, cooldown, instant unstake | **Live**, Ethereum only | Transparent proxy |
| vePENDLE (`VotingEscrowPendleMainchain`) | Lock PENDLE, broadcast positions | **Deprecated** | Immutable |
| vePENDLE sidechain (`VotingEscrowPendleSidechain`) | Mirror of ETH positions | **Deprecated** | Immutable |
| `PendleVotingControllerUpg` | Weekly gauge votes | **Deprecated** | UUPS (ERC1967Proxy) |
| `PendleFeeDistributor` / `PendleFeeDistributorV2` | vePENDLE fee rewards | **Deprecated** | UUPS |
| **`PendleGaugeControllerUpg`** | Holds PENDLE incentives, streams them to markets | Live, every market chain | UUPS (ERC1967Proxy) |
| `PendleMsgSendEndpointUpg` / `PendleMsgReceiveEndpointUpg` | LayerZero V1 governance messaging | Live (legacy path) | UUPS |
| `PendleMultiTokenMerkleDistributor` | `vePendleAirdropDistributor`, `externalRewardsDistributor` | Live | UUPS |
| Cross-chain PT | `PendlePTOFTAdapterFactory`, `OFTPTSwapper`, `PendleCrossChainSwapHub`, `DepositBoxFactory`, `FixedPricePTAMMV2`, `PendleExchangeRateOracle` | Live | Transparent / ERC1967 proxies |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 sPENDLE (`StakedPendle`) — *all six live on Ethereum*

| topic0 | Event |
|--------|-------|
| `0x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d` | `Staked(address indexed user, uint256 amount)` |
| `0x810500030f51f04e0a6a7c0323c84654a386b2572d248a7ae15432d4496cc9d1` | `CooldownInitiated(address indexed user, uint256 amount, uint256 cooldownStart)` |
| `0x526c2f609254f61e4f8ad7e187f5cd1a08553c70348f25168012b30ae57abf44` | `CooldownCanceled(address indexed user, uint256 amount)` |
| `0x7fc4727e062e336010f2c282598ef5f14facb3de68cf8195c2f23e1454b2b74e` | `Unstaked(address indexed user, uint256 amountAfterFee, uint256 fee)` |
| `0xd1eb84e494bccd5db03f09b20ac3b6513b255866e3322d58cd6a816b55d24f35` | `CooldownDurationAndFeeUpdated(uint24 newDuration, uint64 instantUnstakeFeeRate)` (admin) |
| `0x27aae5db36d94179909d019ae0b1ac7c16d96d953148f63c0f6a0a9c8ead79ee` | `FeeReceiverUpdated(address indexed feeReceiver)` (admin) |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` (sPENDLE is transferable) |

### 1.2 vePENDLE (deprecated)

| topic0 | Event | Contract |
|--------|-------|----------|
| `0xb1a3371956c54dc1d83695b4a006b051c8313ee986e533b6b964e77c9066fc2c` | `NewLockPosition(address indexed user, uint128 amount, uint128 expiry)` | Mainchain |
| `0x0e1bb0545c1ebb9fb680bde73514e572831de93b479c087ec1ef6c35c3a19fd6` | `Withdraw(address indexed user, uint128 amount)` | Mainchain |
| `0x82e92e1b0568d98f095fc0c76ccb0f2ac5b64534f69a2c706281e223b6477683` | `BroadcastUserPosition(address indexed user, uint256[] chainIds)` | Mainchain |
| `0x5f9e7cb1ed2eca254f75b6e350699887aa8597e3a2ec9e0aa2b3504c211facbd` | `BroadcastTotalSupply((uint128,uint128) newTotalSupply, uint256[] chainIds)` | Mainchain |
| `0x776960a80ccfa09c52229b183bf0ef49b26a5d15f9ae2c1c0f780a450d3b2a9f` | `SetNewUserPosition((uint128,uint128) position)` | Sidechain |
| `0x460b96294ff8de4eea3be3fb4fac9f978cffe83c7cc3140a4bfe0bedba26b92f` | `SetNewTotalSupply((uint128,uint128) totalSupply)` | Sidechain |
| `0x8d268954369e04c7941c3a7876f40c618eb97919add31202c9a235e75e84cf1b` | `SetNewDelegator(address delegator, address receiver)` | Sidechain |

### 1.3 VotingController (deprecated, Ethereum)

| topic0 | Event |
|--------|-------|
| `0xc71e393f1527f71ce01b78ea87c9bd4fca84f1482359ce7ac9b73f358c61b1e1` | `Vote(address indexed user, address indexed pool, uint64 weight, (uint128,uint128) vote)` |
| `0xa512c82e73ec974de3c794a3ea6bbdfbad18531c1394ace9972f3f0166b67863` | `PoolVoteChange(address indexed pool, (uint128,uint128) vote)` |
| `0xc78a580f215ba474e75ecbd7636c375e8d2cd25edb0f2467f99b2d0752e104ba` | `BroadcastResults(uint64 indexed chainId, uint128 indexed wTime, uint128 totalPendlePerSec)` |
| `0x336f0b3cc523e98d21e261389542b62abaffc094a21a82f1eec2779d7c8323cb` | `AddPool(uint64 indexed chainId, address indexed pool)` |
| `0xf2e3b584c4d1ed5ead9a4b7de2a8225fd42d13f09e417cd294d03f1dd07fc914` | `RemovePool(uint64 indexed chainId, address indexed pool)` |
| `0xfe870af61f024df0d7f960ad100676f3ffaa7ea6a44bc6c7adf2756cb8cf4b38` | `SetPendlePerSec(uint256 newPendlePerSec)` |

### 1.4 GaugeController (live, every market chain)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xf7823f78d472190ac0f94e11854ed334dce4a2e571e5f1bf7a8aec9469891d97` | `MarketClaimReward(address indexed market, uint256 amount)` | PENDLE streamed to a market. *(live ETH, Robinhood)* |
| `0xd854b889a6ed01552356fb0476be5b2f3bb578e30cd48f37fde3d5f0ffe01ad5` | `UpdateMarketRewardV2(address indexed market, uint128 pendlePerSec, uint128 incentiveEndsAt)` | **Current** rate-set event. *(live ETH, Robinhood)* |
| `0x04c50548091a7c7fc3c76277602df5b55cfe396f9856aa741d9f729309466d36` | `WhitelistMarketSet(address indexed market, bool isWhitelisted)` | *(live Robinhood)* |
| `0x77f3621b33a2ea072a89f61066691007da80431c230ce13f6e4f984d1773a7bf` | `UpdateMarketReward(address indexed market, uint256 pendlePerSec, uint256 incentiveEndsAt)` | Legacy (vote-driven) |
| `0xc2a95122fde68f77e93e8f353620af282e72051c5b744320e519fc07ed708ba3` | `ReceiveVotingResults(uint128 indexed wTime, address[] markets, uint256[] pendleAmounts)` | Legacy (from LayerZero) |

### 1.5 Fee & merkle distributors

| topic0 | Event | Contract |
|--------|-------|----------|
| `0x913c992353dc81b7a8ba31496c484e9b6306bd2f6c509a649a38fdf5e1c953b2` | `Claimed(address indexed token, address indexed user, address indexed receiver, uint256 amount)` | MultiTokenMerkleDistributor *(live Robinhood)* |
| `0x914960aef5e033ce5cae8a7992d4b7a6f0f9741227b66acb67c605b7019f8a46` | `SetMerkleRoot(bytes32 indexed merkleRoot)` | Merkle distributors *(live Robinhood)* |
| `0xf7a40077ff7a04c7e61f6f26fb13774259ddf1b6bce9ecf26a8276cdd3992683` | `Claimed(address indexed user, address indexed receiver, uint256 amount)` | PendleMerkleDistributor (single token) |
| `0xd8138f8a3f377c5259ca548e70e4c2de94f129f5a11036a15b69513cba2b426a` | `Claimed(address indexed user, uint256 amountOut)` | FeeDistributorV2 (deprecated) |
| `0xc3cf50db282eb67e0c487a5fe4dbeb3a964478b2edd1615ef91160c7205ffccd` | `SetMerkleRootAndFund(bytes32 indexed merkleRoot, uint256 amountFunded)` | FeeDistributorV2 |
| `0x4d490fc5b632b5a4319f50b51d1716cf9c227f26dfb9f1c3ea96a1d0707af184` | `UpdateProtocolClaimable(address indexed user, uint256 sumTopUp)` | FeeDistributorV2 |
| `0xfe7c5fc89da23a432c91f264decb100ab9d08ab7b14650c3cdb9b6b4f84a60e9` | `ClaimReward(address indexed pool, address indexed user, uint256 wTime, uint256 amount)` | FeeDistributor V1 (deprecated) |
| `0xc9920255a27e7e0a5d647597e867ab827659000ae32276c878d8a04120efabb0` | `UpdateFee(address indexed pool, uint256 indexed wTime, uint256 amount)` | FeeDistributor V1 |

### 1.6 Messaging (LayerZero V1 endpoints)

| topic0 | Event |
|--------|-------|
| `0xe183f33de2837795525b4792ca4cd60535bd77c53b7e7030060bfcf5734d6b0c` | `MessageFailed(uint16 _srcChainId, bytes _path, uint64 _nonce, bytes _payload, bytes _reason)` — receive endpoint, failed delivery |

The send endpoint emits no own event. Track sends by the LayerZero V1 endpoint logs or by `sendMessage` calls (§2.5).

### 1.7 PENDLE OFT / PT OFT (LayerZero V2 OApp standard)

| topic0 | Event |
|--------|-------|
| `0x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a` | `OFTSent(bytes32 indexed guid, uint32 dstEid, address indexed fromAddress, uint256 amountSentLD, uint256 amountReceivedLD)` *(live Robinhood: 137)* |
| `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c` | `OFTReceived(bytes32 indexed guid, uint32 srcEid, address indexed toAddress, uint256 amountReceivedLD)` *(live Robinhood: 180)* |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` — **trust change** *(live)* |
| `0xbe4864a8e820971c0247f5992e2da559595f7bf076a21cb5928d443d2a13b674` | `EnforcedOptionSet((uint32,uint16,bytes)[] _enforcedOptions)` *(live)* |
| `0xfa05891d7928e6898fc05852475dc6b82c0e82887e0af865a99ed79f35638c0a` | `PtAdapterCreated(address indexed pt, address indexed adapter)` — PT OFT adapter factory |
| `0x497996dac69d679583cab49a7b067859c8b623151a7001356974afe003bfb50f` | `PTOFTDeployed(uint32 indexed lzEid, bytes32 indexed originalPt, address indexed oft)` — bridged-PT factory |

### 1.8 Cross-chain PT periphery

| topic0 | Event | Contract |
|--------|-------|----------|
| `0x2d9e4b4ad37b1c82b8eb1ef31a3989777d7340f3a4c410ecb118fa36a8313385` | `BridgeToken(address owner, uint32 boxId, uint256 requestId, uint256 nonce, address bridgeExtRouter, address token, uint256 amountBridge, uint256 amountFee)` | CrossChainSwapHub |
| `0x0783848e87066d8f9c59220b080160a862da8b90aceb126448084ca99152c329` | `SwapToken(address owner, uint32 boxId, uint256 requestId, uint256 nonce, address tokenSpent, uint256 amountSpent, address tokenReceived, uint256 netTokenReceived)` | CrossChainSwapHub |
| `0xdf6f01d1bc23db1f488a7260ed908f03717f23e8ce18c8d943a61af76742d62f` | `WithdrawToken(address owner, uint32 boxId, uint256 requestId, uint256 nonce, address token, uint256 amountWithdraw, uint256 amountFee)` | CrossChainSwapHub |
| `0xcd3829a3813dc3cdd188fd3d01dcf3268c16be2fdd2dd21d0665418816e46062` | `Swap(address indexed caller, address indexed receiver, address PT, uint256 netPtIn, uint256 netTokenOut)` | FixedPricePTAMMV2 |
| `0xbd0c663d46f68911676b9f500d7d2a6ac0e13b575566785968f8eca902ba21c7` | `TokenFunded(address indexed sender, uint256 amount)` | FixedPricePTAMMV2 |
| `0xa2bd9fcfcdba69f52bcd9a520846ad4bd685b187483f53efc42d035b2ddebff0` | `TokenWithdrawn(address indexed sender, uint256 amount)` | FixedPricePTAMMV2 |
| `0xeb22591d10206f52ed5223e074c07e1c3fa148aaa0352001f84ba469c13edbd9` | `PauseStatusUpdated(address indexed PT, bool isPaused)` | FixedPricePTAMMV2 |

### 1.9 Admin / proxy

`Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` · `AdminChanged(address,address)` `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` · `Initialized(uint8)` `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` · `OwnershipTransferred(address,address)` `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 sPENDLE

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa694fc3a` | `stake(uint256 amount)` | Emits `Staked` |
| `0xda276040` | `cooldown(uint256 amount)` | Emits `CooldownInitiated` |
| `0x7674e44e` | `cancelCooldown()` | Emits `CooldownCanceled` |
| `0x716907a7` | `finalizeCooldown()` | After 14 days. Emits `Unstaked` (fee 0) |
| `0x7c0696e8` | `instantUnstake(uint256 amount)` | 5 % fee. Emits `Unstaked` |
| `0xe809290b` | `userCooldown(address)` | view |
| `0x35269315` | `cooldownDuration()` / `0x442f1871` `instantUnstakeFeeRate()` / `0x7cf738d2` `PENDLE()` | views |
| `0xc36347db` | `setCooldownDurationAndFee(uint24,uint64)` / `0xefdcd974` `setFeeReceiver(address)` | owner-only |

### 2.2 vePENDLE (deprecated)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc8121ec2` | `increaseLockPosition(uint128 additionalAmountToLock,uint128 newExpiry)` | Emits `NewLockPosition` |
| `0xcc471bb8` | `increaseLockPositionAndBroadcast(uint128,uint128,uint256[])` | payable |
| `0x3ccfd60b` | `withdraw()` | Emits `Withdraw` |
| `0x0b9efa22` | `broadcastUserPosition(address,uint256[])` / `0xb92e106a` `broadcastTotalSupply(uint256[])` | payable (LZ fee) |
| `0x70a08231` | `balanceOf(address)` / `0x30d981af` `totalSupplyCurrent()` / `0xcb6b4f3c` `positionData(address)` | views |
| `0xe0299bf5` | `executeMessage(bytes)` | Sidechain. Called by the receive endpoint |

### 2.3 VotingController (deprecated)

| Selector | Signature |
|----------|-----------|
| `0x698766ee` | `vote(address[] pools,uint64[] weights)` |
| `0x82ae9ef7` | `finalizeEpoch()` |
| `0xc291230d` | `broadcastResults(uint64 chainId)` (payable) |
| `0x1c9bdb49` | `forceBroadcastResults(uint64,uint128,uint128)` (owner) |
| `0xd68ffecb` | `addPool(uint64,address)` / `0x3b7d0946` `removePool(address)` / `0x59255706` `setPendlePerSec(uint128)` (owner) |

### 2.4 GaugeController

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x58f3d163` | `redeemMarketReward()` | Called by a market. Emits `MarketClaimReward` |
| `0xe04e9c92` | `setRewardDatas(address[] markets,uint128[] pendlePerSecs,uint128[] incentiveEndsAts)` | owner-only. Emits `UpdateMarketRewardV2` |
| `0x8bcbba16` | `whitelistMarkets(address[],bool)` | owner-only |
| `0xa0262b3b` | `withdrawPendle(uint256)` | owner-only. **Drains incentives** |
| `0x48e5d9f8` | `rewardData(address market)` | view |
| `0x3659cfe6` | `upgradeTo(address)` / `0x4f1ef286` `upgradeToAndCall(address,bytes)` | UUPS |

### 2.5 Messaging endpoints (LayerZero V1)

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xb2267a7b` | `sendMessage(address dstAddress,uint256 dstChainId,bytes payload,uint256 estimatedGasAmount)` | Send endpoint (whitelisted callers only) |
| `0x93bf751e` | `addReceiveEndpoints(address,uint256)` / `0x9281aa0b` `setWhitelisted(address,bool)` | Send endpoint, owner |
| `0xf080765a` | `getAllReceiveEndpoints()` | Send endpoint, view |
| `0x001d3567` | `lzReceive(uint16,bytes,uint64,bytes)` | Receive endpoint (LZ V1 callback) |
| `0x7efec77a` | `govExecuteMessage(address,bytes)` | Receive endpoint, owner |

### 2.6 Distributors, OFT, cross-chain PT

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xa0165082` | `claim(address receiver,address[] tokens,uint256[] totalAccrueds,bytes32[][] proofs)` | MultiTokenMerkleDistributor |
| `0x053f6a70` | `claimRetail(address,uint256,bytes32[])` / `0xff5b4066` `claimProtocol(address,address[])` | FeeDistributorV2 |
| `0x3685ffe7` | `claimReward(address,address[])` | FeeDistributor V1 |
| `0xc7c7f5b3` | `send((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address)` | OFT / OFT adapter (payable) |
| `0x13137d65` | `lzReceive((uint32,bytes32,uint64),bytes32,bytes,address,bytes)` | OFT (LZ V2 callback) |
| `0x628577fd` | `bridgeToken(((address,uint32,uint256,uint256,uint256),address,uint256,uint256,address,address,bytes),bytes)` | CrossChainSwapHub (payable) |
| `0x0df93821` | `swapToken(((address,uint32,uint256,uint256,uint256),address,uint256,address,uint256,address,address,bytes),bytes)` | CrossChainSwapHub |
| `0xccd02bda` | `withdrawToken(((address,uint32,uint256,uint256,uint256),address,uint256,uint256),bytes)` | CrossChainSwapHub |
| `0x1530a170` | `swapExactPtForToken(address receiver,address PT,uint256 exactPtIn,bytes data)` | FixedPricePTAMMV2 |

---

## 3. Addresses — Ethereum (chain ID 1)

All verified via `eth_getCode` on `ethereum-rpc.publicnode.com` on 2026-10-30.

| Role | Address | One-liner |
|------|---------|-----------|
| **PENDLE** | `0x808507121b80c02388fad14726482e061b8da827` | Native token |
| PENDLE OFT adapter (`WOFTAdapter`) | `0xd7e67c97cc48253b28737ec3981b0a7ad6d7e0e4` | LZ V2 (endpoint `0x1a44076050125825900e736c501f859c50fe728c`). Peer of Robinhood PENDLE. `owner()` = `governanceProxy` |
| **sPENDLE** | `0x999999999991e178d52cd95afd4b00d066664144` | Proxy → `StakedPendle` `0xa98d1483781c08e60d944a63721b93fe40749032` |
| vePENDLE (deprecated) | `0x4f30a9d41b80ecc5b94306ab4364951ae3170210` | `VotingEscrowPendleMainchain` |
| VotingController (deprecated) | `0x44087e105137a5095c008aab6a6530182821f2f0` | Proxy → `0xca10fb0f2ce19cde44b42df2f42607977dfa4549` |
| FeeDistributor (deprecated) | `0xd7b34a6fdcb2a7ced2115ff7f5fdd72aa6aa4de2` | Proxy → `0xb0caa67c712d96809f2abaf2c95369ef942ce8cb` |
| FeeDistributorV2 (deprecated) | `0x8c237520a8e14d658170a633d96f8e80764433b9` | Proxy → `0xafaae49c7684a2f386eb18569966604973f9d83d` |
| **GaugeController** | `0x47d74516b33ed5d70dde7119a40839f6fcc24e57` | Proxy → `PendleGaugeControllerUpg` `0xef5579f4e7b0063a414a42a65dfd86a1562466e1` |
| MsgSendEndpoint | `0x07b1014c88f14c9e910092526db57a20052e989f` | Proxy → `0x5f142ff25a1a46be1a591dbc1ef59a15e767fcb7`. LZ V1 endpoint `0x66a71dcef29a0ffbdbe3c6a460a3b5bc225cd675` |
| vePendleAirdropDistributor | `0x3942f7b55094250644cffda7160226caa349a38e` | MultiTokenMerkleDistributor |
| externalRewardsDistributor | `0x33305665f69b4642d1275f4ce81c23651674d21c` | MultiTokenMerkleDistributor |
| merkleDepositor | `0x3dae3d1734ca3c7b3089d4dd03c9876e0a0102b4` | |
| PT OFT adapter factory | `0x905af80c4de82e0075a19fde2f5777f1a6636732` | Proxy → `PendlePTOFTAdapterFactory` |
| exchangeRateOracle | `0xa914c44e960cc95d996969bdf0ab5d6f4f2b5870` | Proxy. Cross-chain PT rate |
| CrossChainSwapHub / DepositBoxFactory | `0xd41c99760f4a7e27e736ed25cd6915110948ea8a` / `0x15ff9d268ef3300a3fcce5de4bc4326316c5dd6d` | Same on 7 chains |
| OFTPTSwapper | `0x8ef78ad230887e05fa3324277a5225fe93889b08` | Admin `devProxyAdmin` |
| PendlePTLooper / View / LoopPositionBoxFactory | `0xf82ef4080a53b71093f9c470676fc80e2adc4263` / `0x887b00b5f584f1cc015e8f68c29d6feb6bf95b02` / `0xe5125dfe3fc232723e7ae17cfa66034b3bcac696` | ETH + Arb |
| governanceProxy | `0x2ad631f72fb16d91c4953a7f4260a97c2fe2f31e` | Owner of GaugeController, OFT, V5/V6 market factories |

## 4. Addresses — Arbitrum, Base, BNB, Optimism, Robinhood Chain, Avalanche

| Role | Arbitrum (42161) | Base (8453) | BNB (56) | Optimism (10) | Robinhood (4663) | Avalanche (43114) |
|------|------------------|-------------|----------|---------------|------------------|-------------------|
| **PENDLE** | `0x0c880f6761f1af8d9aa9c466984b80dab9a8c9e8` | `0xa99f6e6785da0f5d6fb42495fe424bce029eeb3e` | `0xb3ed0a426155b79b898849803e3b36552f7ed507` | `0xbc7b1ff1c6989f006a1185318ed4e7b5796e66e1` | `0x5e49e1f85813f2b65858860a3fa231b4186f2e0e` | — |
| PENDLE type | Arbitrum gateway token | OP-Stack mintable | Wormhole wrapped | OP-Stack mintable | LZ V2 OFT | — |
| **GaugeController** | `0x1e56299ebc8a1010cec26005d12e3e5c5cc2db00` | `0x17f100fb4be2707675c6439468d38249dd993d58` | `0x704478dd72fd7f9b83d1f1e0fc18c14b54f034d0` | `0x6875e4a945e498fe1b90bbb13cfbaf0b68658c9c` | `0x7e500c6efbb00fd3227888256e477171a1304721` | — |
| MsgReceiveEndpoint | `0xc9215ae9ec67385f38c755d862c8ee3702b5793a` | `0xee708fc793a02f1edd5bb9dbd7fd13010d1f7136` | `0x998cf52b2585e05494bf9f2bf502351a9c7fda8f` | `0xed18de5442297a4ec1ce59c7c7d9427adc2a012b` | — | — |
| vePENDLE sidechain (deprecated) | `0x3209e9412cca80b18338f2a56ada59c484c39644` | `0x051dcd6a80f11fe68f77fb0ebde03853fa96b1fd` | `0x8a09574b0401a856d89d1b583ee22e8cb0c5530b` | `0xd5c47d2383fddc19596489280c0a33ac42b2bb18` | — | — |
| vePendleAirdrop / externalRewards distributors | `0x3942…a38e` / `0x3330…d21c` | same | same | same | same | — |
| arbMerkleDistribution | `0x23a102e78d1ff1645a3666691495174764a5fcaf` | — | — | — | — | — |
| PT OFT adapter factory | `0x4f215b3f8a6e056ff293e6818f3f501b5f4787d7` | — | — | `0x45dd4aecc425b01bf98c567407ab4a4ff3c7d349` | — | — |
| exchangeRateOracle | `0xa914…5870` | `0xa914…5870` | `0xa914…5870` | `0xa914…5870` | — | — |
| CrossChainSwapHub | `0xd41c…ea8a` | same | same | same | same | same |
| DepositBoxFactory | `0x15ff…dd6d` | same | same | same | same | same |
| OFTPTSwapper | `0x8ef7…9b08` | same | same | — | — | same |
| FixedPricePTAMMV2 | — | — | `0x9b5ddd4b59cc26f4f4238dbc774fb2dc2860be46` | — | — | `0x4d717868f4bd14ac8b29bb6361901e30ae05e340` |
| LayerZero endpoint used | V1 `0x3c2269811836af69497e5f486a85d7316753cf62` | V1 `0xb6319cc6c8c27a8f5daf0dd3df91ea35c4720dd7` | V1 `0x3c22…cf62` | V1 `0x3c22…cf62` | V2 `0x6f475642a6e85809b1c36fa62763669b1b48dd5b` (OFT) | V1 `0x3c22…cf62` |

sPENDLE, vePENDLE mainchain, VotingController, the fee distributors and the send endpoint exist **only on Ethereum**. Robinhood Chain has no vePENDLE and no receive endpoint: its GaugeController is fed by the owner directly. Avalanche has only the cross-chain PT periphery (no PENDLE, no gauge). Polygon and Arc: no contract from this file (`eth_getCode` = `0x`).

The Ethereum send endpoint lists 9 receive endpoints (`getAllReceiveEndpoints()`): Arbitrum, BNB, Mantle (5000), Optimism, Base, Sonic (146), Berachain (80094), HyperEVM (999), Plasma (9745). Robinhood Chain is not in the list.

## 5. Cross-chain summary

| Chain (ID) | PENDLE | sPENDLE | vePENDLE | GaugeController | Msg endpoint | Cross-chain PT |
|------------|--------|---------|----------|-----------------|--------------|----------------|
| Ethereum (1) | native | ✓ | mainchain (deprecated) | ✓ | send | adapter factory, hub, swapper, oracle |
| Arbitrum (42161) | gateway | — | sidechain (deprecated) | ✓ | receive | adapter factory, hub, swapper, oracle |
| Base (8453) | OP-mintable | — | sidechain (deprecated) | ✓ | receive | hub, swapper, oracle |
| BNB (56) | Wormhole | — | sidechain (deprecated) | ✓ | receive | hub, swapper, oracle, fixed-price AMM |
| Optimism (10) | OP-mintable | — | sidechain (deprecated) | ✓ | receive | adapter factory, hub, oracle |
| Robinhood (4663) | LZ V2 OFT | — | — | ✓ | — | hub |
| Avalanche (43114) | — | — | — | — | — | hub, swapper, fixed-price AMM |
| Polygon (137) | — | — | — | — | — | — |
| Arc (5042) | — | — | — | — | — | — |

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| sPENDLE | Transparent proxy (2999 B) | Impl `0xa98d1483781c08e60d944a63721b93fe40749032` | Admin `proxyAdmin` `0xa28c08f1…5e64` |
| GaugeController | UUPS (`ERC1967Proxy`, 843 B; Base 177 B; Robinhood 225 B) | Impl `0xef5579f4…66e1` on ETH/Arb/Base/BNB; OP `0x964840644b88c583500f473e4b829ab629af96a8`; Robinhood `0xda172dc638235d5f5bcb74c2ecf02f70621deeee` | Contract `owner()` (`governanceProxy`) |
| VotingController, FeeDistributor(V2), MsgSend/ReceiveEndpoint, arbMerkleDistribution | UUPS (`ERC1967Proxy`) | Impl slot read live (see §3–§4) | `owner()` |
| vePendleAirdrop / externalRewards distributors | UUPS (225 B) | Impl `0xd2f9c41e348662cea2356d84a71eaf8899c75bab` (ETH/Arb/Base/BNB); per-chain on OP and Robinhood | `owner()` |
| CrossChainSwapHub / DepositBoxFactory | Transparent proxy | Impl `0xbe9cc5cdbb6ae6a4378e2795099c5e951d3ec5e4` / `0x71f2b64886586334a27b54814e227286f6b903f9` (same on all 7 chains) | `proxyAdmin` |
| OFTPTSwapper | Transparent proxy | Impl `0x55ac3ac2ca5daa93db298d4282d4de79713b252b` | `devProxyAdmin` `0xd37eb2e6…ea9` |
| exchangeRateOracle | Transparent proxy | Impl `0x7f0491d9612c0d6b24ff37ff81fa8cf1bce27098` (OP `0xe574de45…7c64`) | `proxyAdmin` |
| PENDLE (Arbitrum) | Beacon proxy (Arbitrum gateway) | Beacon slot `0xe72ba9418b5f2ce0a6a40501fe77c6839aa37333` | Arbitrum gateway |
| PENDLE (BNB) | Beacon proxy (Wormhole) | Beacon `0xb6f6d86a8f9879a9c87f643768d9efc38c1da6e7` → impl `0x7f8c5e730121657e17e452c5a1ba3fa1ef96f22a` | Wormhole token bridge |
| PENDLE (ETH, Base, OP, Robinhood), vePENDLE (all) | **Immutable** | Impl slot `0x0` | — |

## 7. Detection invariants & gotchas

1. **vePENDLE and voting are deprecated.** The last `BroadcastResults` / `ReceiveVotingResults` on Ethereum is at block 24,286,615. No `Vote`/`BroadcastResults` traffic appears in recent blocks. Current incentive changes show as `UpdateMarketRewardV2` from each GaugeController, set by the owner.
2. **sPENDLE `Unstaked` carries the fee.** `fee > 0` means an instant unstake (5 %). `fee = 0` means a finalized 14-day cooldown.
3. **sPENDLE is a transferable ERC-20.** A `Transfer` from `0x0` with a `Staked` in the same tx is a stake. A plain `Transfer` is a secondary transfer, not a stake.
4. **`Withdraw(address,uint128)` on vePENDLE is not the ERC-4626 `Withdraw`.** Different topic0. Filter by emitter.
5. **Four `Claimed` events.** MultiToken (`0x913c9923…`), single-token merkle (`0xf7a40077…`), FeeDistributorV2 (`0xd8138f8a…`) and others. Disambiguate by emitter.
6. **PENDLE supply on L2s is bridged, not minted.** Arbitrum, Base and OP PENDLE mint only on canonical-bridge deposits. BNB PENDLE mints only through Wormhole. Robinhood PENDLE mints only on `OFTReceived`. A mint without the bridge event is an anomaly.
7. **`PeerSet` on the PENDLE OFT or OFT adapter changes trust.** Alert on it. The Robinhood OFT peer for Ethereum (eid 30101) is `0xd7e67c97…e0e4`.
8. **Same address, different role per chain.** `0x17f100fb…3d58` is the Base GaugeController and the Optimism V1 market factory. `0x704478dd…34d0` is the BNB GaugeController and the Optimism RouterStatic. Key on `(chainId, address)`.
9. **`withdrawPendle(uint256)` on a GaugeController removes incentive PENDLE.** It is owner-only, but it is the one call that moves the incentive pool out.
10. **Avalanche has no PENDLE token in the registry.** Treat any "PENDLE" on Avalanche as unverified.

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_SPENDLE_STAKED              = '\x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d'
TOPIC_SPENDLE_COOLDOWN_INITIATED  = '\x810500030f51f04e0a6a7c0323c84654a386b2572d248a7ae15432d4496cc9d1'
TOPIC_SPENDLE_COOLDOWN_CANCELED   = '\x526c2f609254f61e4f8ad7e187f5cd1a08553c70348f25168012b30ae57abf44'
TOPIC_SPENDLE_UNSTAKED            = '\x7fc4727e062e336010f2c282598ef5f14facb3de68cf8195c2f23e1454b2b74e'
TOPIC_SPENDLE_COOLDOWN_FEE_UPDATE = '\xd1eb84e494bccd5db03f09b20ac3b6513b255866e3322d58cd6a816b55d24f35'
TOPIC_VE_NEW_LOCK_POSITION        = '\xb1a3371956c54dc1d83695b4a006b051c8313ee986e533b6b964e77c9066fc2c'
TOPIC_VE_WITHDRAW                 = '\x0e1bb0545c1ebb9fb680bde73514e572831de93b479c087ec1ef6c35c3a19fd6'
TOPIC_VOTE                        = '\xc71e393f1527f71ce01b78ea87c9bd4fca84f1482359ce7ac9b73f358c61b1e1'
TOPIC_BROADCAST_RESULTS           = '\xc78a580f215ba474e75ecbd7636c375e8d2cd25edb0f2467f99b2d0752e104ba'
TOPIC_GAUGE_MARKET_CLAIM_REWARD   = '\xf7823f78d472190ac0f94e11854ed334dce4a2e571e5f1bf7a8aec9469891d97'
TOPIC_GAUGE_UPDATE_REWARD_V2      = '\xd854b889a6ed01552356fb0476be5b2f3bb578e30cd48f37fde3d5f0ffe01ad5'
TOPIC_GAUGE_UPDATE_REWARD         = '\x77f3621b33a2ea072a89f61066691007da80431c230ce13f6e4f984d1773a7bf'
TOPIC_GAUGE_RECEIVE_VOTING        = '\xc2a95122fde68f77e93e8f353620af282e72051c5b744320e519fc07ed708ba3'
TOPIC_GAUGE_WHITELIST_MARKET      = '\x04c50548091a7c7fc3c76277602df5b55cfe396f9856aa741d9f729309466d36'
TOPIC_MERKLE_MULTI_CLAIMED        = '\x913c992353dc81b7a8ba31496c484e9b6306bd2f6c509a649a38fdf5e1c953b2'
TOPIC_MERKLE_SET_ROOT             = '\x914960aef5e033ce5cae8a7992d4b7a6f0f9741227b66acb67c605b7019f8a46'
TOPIC_LZ_MESSAGE_FAILED           = '\xe183f33de2837795525b4792ca4cd60535bd77c53b7e7030060bfcf5734d6b0c'
TOPIC_OFT_SENT                    = '\x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a'
TOPIC_OFT_RECEIVED                = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
TOPIC_OFT_PEER_SET                = '\x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b'
TOPIC_PT_ADAPTER_CREATED          = '\xfa05891d7928e6898fc05852475dc6b82c0e82887e0af865a99ed79f35638c0a'
TOPIC_HUB_BRIDGE_TOKEN            = '\x2d9e4b4ad37b1c82b8eb1ef31a3989777d7340f3a4c410ecb118fa36a8313385'
TOPIC_HUB_SWAP_TOKEN              = '\x0783848e87066d8f9c59220b080160a862da8b90aceb126448084ca99152c329'
TOPIC_HUB_WITHDRAW_TOKEN          = '\xdf6f01d1bc23db1f488a7260ed908f03717f23e8ce18c8d943a61af76742d62f'
TOPIC_FIXED_PT_AMM_SWAP           = '\xcd3829a3813dc3cdd188fd3d01dcf3268c16be2fdd2dd21d0665418816e46062'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors (chain-agnostic) =====
SEL_SPENDLE_STAKE                 = '\xa694fc3a'
SEL_SPENDLE_COOLDOWN              = '\xda276040'
SEL_SPENDLE_FINALIZE_COOLDOWN     = '\x716907a7'
SEL_SPENDLE_INSTANT_UNSTAKE       = '\x7c0696e8'
SEL_VE_INCREASE_LOCK              = '\xc8121ec2'
SEL_VE_WITHDRAW                   = '\x3ccfd60b'
SEL_VOTE                          = '\x698766ee'
SEL_GAUGE_SET_REWARD_DATAS        = '\xe04e9c92'
SEL_GAUGE_WITHDRAW_PENDLE         = '\xa0262b3b'
SEL_GAUGE_REDEEM_MARKET_REWARD    = '\x58f3d163'
SEL_MSG_SEND                      = '\xb2267a7b'
SEL_MERKLE_MULTI_CLAIM            = '\xa0165082'
SEL_OFT_SEND                      = '\xc7c7f5b3'
-- ===== Addresses (network-specific) =====
ETH_PENDLE                        = '\x808507121b80c02388fad14726482e061b8da827'
ETH_PENDLE_OFT_ADAPTER            = '\xd7e67c97cc48253b28737ec3981b0a7ad6d7e0e4'
ETH_SPENDLE                       = '\x999999999991e178d52cd95afd4b00d066664144'
ETH_VEPENDLE                      = '\x4f30a9d41b80ecc5b94306ab4364951ae3170210'
ETH_VOTING_CONTROLLER             = '\x44087e105137a5095c008aab6a6530182821f2f0'
ETH_GAUGE_CONTROLLER              = '\x47d74516b33ed5d70dde7119a40839f6fcc24e57'
ETH_MSG_SEND_ENDPOINT             = '\x07b1014c88f14c9e910092526db57a20052e989f'
ETH_FEE_DISTRIBUTOR_V2            = '\x8c237520a8e14d658170a633d96f8e80764433b9'
ANY_VEPENDLE_AIRDROP_DISTRIBUTOR  = '\x3942f7b55094250644cffda7160226caa349a38e'
ANY_EXTERNAL_REWARDS_DISTRIBUTOR  = '\x33305665f69b4642d1275f4ce81c23651674d21c'
ANY_CROSS_CHAIN_SWAP_HUB          = '\xd41c99760f4a7e27e736ed25cd6915110948ea8a'
ARB_PENDLE                        = '\x0c880f6761f1af8d9aa9c466984b80dab9a8c9e8'
ARB_GAUGE_CONTROLLER              = '\x1e56299ebc8a1010cec26005d12e3e5c5cc2db00'
ARB_MSG_RECEIVE_ENDPOINT          = '\xc9215ae9ec67385f38c755d862c8ee3702b5793a'
BASE_PENDLE                       = '\xa99f6e6785da0f5d6fb42495fe424bce029eeb3e'
BASE_GAUGE_CONTROLLER             = '\x17f100fb4be2707675c6439468d38249dd993d58'
BNB_PENDLE                        = '\xb3ed0a426155b79b898849803e3b36552f7ed507'
BNB_GAUGE_CONTROLLER              = '\x704478dd72fd7f9b83d1f1e0fc18c14b54f034d0'
OP_PENDLE                         = '\xbc7b1ff1c6989f006a1185318ed4e7b5796e66e1'
OP_GAUGE_CONTROLLER               = '\x6875e4a945e498fe1b90bbb13cfbaf0b68658c9c'
ROBIN_PENDLE_OFT                  = '\x5e49e1f85813f2b65858860a3fa231b4186f2e0e'
ROBIN_GAUGE_CONTROLLER            = '\x7e500c6efbb00fd3227888256e477171a1304721'
```

## 9. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the ABIs in npm `@pendle/core-v2@6.12.0` (sPENDLE, gauge, endpoints, OFT, cross-chain) and `@5.0.0` (`PendleVotingControllerUpg`, `PendleFeeDistributor`). Live `eth_getLogs` confirmed: sPENDLE `Staked`/`Unstaked`/`CooldownInitiated`/`CooldownCanceled` (Ethereum, last 10k blocks); GaugeController `MarketClaimReward`/`UpdateMarketRewardV2` (Ethereum and Robinhood: 1560 / 302) and `WhitelistMarketSet` (Robinhood: 15); Robinhood PENDLE OFT `OFTSent` 137 / `OFTReceived` 180 / `PeerSet` / `EnforcedOptionSet`; MultiTokenMerkleDistributor `Claimed` / `SetMerkleRoot` (Robinhood). Historical Ethereum logs (Routescan Etherscan-compatible API) confirmed the deprecated topics: vePENDLE `NewLockPosition`/`Withdraw`/`BroadcastUserPosition`/`BroadcastTotalSupply` (≥1000 each from block 16.03M); VotingController `Vote`/`PoolVoteChange` (≥1000), `BroadcastResults` 778 and `AddPool` 669 (last at blocks 24,286,615 / 24,282,214), `SetPendlePerSec` 15; GaugeController `ReceiveVotingResults` 165 (last 24,286,615) and `UpdateMarketReward` (≥1000, last 19.7M); FeeDistributorV2 `Claimed` / `SetMerkleRootAndFund` (29); FeeDistributor V1 `ClaimReward` / `UpdateFee` (126); PENDLE OFT adapter `OFTSent` 497 / `OFTReceived` (≥1000); PT adapter factory `PtAdapterCreated` 16; CrossChainSwapHub `BridgeToken` 293 / `SwapToken` 525 / `WithdrawToken` 456 (from block 24,647,228). Sidechain vePENDLE topics (`SetNewUserPosition`, `SetNewTotalSupply`, `SetNewDelegator`) and `MessageFailed` come from the published ABIs only (not re-read live).
- **Addresses:** parsed from `deployments/*-core.json`; existence-checked with `eth_getCode` on all nine chains; proxy impl/admin/beacon slots read live; token types read live (`l1Address()`, `remoteToken()`, `bridge()`, `endpoint()`, `peers(30101)`, `owner()`). Contract names cross-checked on Sourcify (`StakedPendle`, `PendleGaugeControllerUpg`, `PendleMsgSendEndpointUpg`, `PendleVotingControllerUpg`, `PendleMultiTokenMerkleDistributor`, `PendlePTOFTAdapterFactory`, `PendleOFT`, `WOFTAdapter`, Wormhole `BridgeToken`).
- **Chain coverage:** Polygon and Arc return `0x` for every address here. Avalanche carries only the cross-chain PT periphery.

Authoritative sources:
- [pendle-finance/pendle-core-v2-public](https://github.com/pendle-finance/pendle-core-v2-public) — contracts, `contracts/LiquidityMining/README.md`, `deployments/*.json`.
- [npm @pendle/core-v2](https://www.npmjs.com/package/@pendle/core-v2) — compiled ABIs.
- [Pendle docs](https://docs.pendle.finance) — sPENDLE, incentives, deployments.
- Explorers: [Etherscan](https://etherscan.io/address/0x999999999991e178d52cd95afd4b00d066664144) · [Arbiscan](https://arbiscan.io) · [Basescan](https://basescan.org) · [BscScan](https://bscscan.com) · [Optimistic Etherscan](https://optimistic.etherscan.io) · [Sourcify](https://sourcify.dev).
