# Rubic — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain)

**Status:** verified on 2026-09-29 to 2026-10-01 against live RPC on all eight target chains and the canonical `Cryptorubic/multi-proxy-rubic` repository (`deployments/<chain>.json`, `deployments/<chain>.diamond.json`, `src/`). Topic0 and selectors recomputed as `keccak256(signature)`. Addresses existence-checked with `eth_getCode`. The live facet table read with `facets()` on every chain.
**Scope:** Rubic's cross-chain aggregator contracts: the **RubicMultiProxy** diamond (EIP-2535; a fork of the LI.FI diamond), its approval front **ERC20Proxy**, and the destination helpers **Executor**, **Receiver** and **StargateV2Receiver**. Rubic's older single-provider proxies (`Cryptorubic/proxy-instant-trades`, `Multichain-proxy`, `only-source-cross-chain-proxy`, 2022) are out of scope. Topics and selectors are chain-agnostic. Addresses are network-specific.

Rubic is an aggregator that sits on top of other bridges. One user transaction calls `ERC20Proxy.startViaRubic` (or the diamond directly for native coin). The ERC20Proxy pulls the tokens into the diamond. The diamond takes Rubic's and the integrator's fees, optionally swaps, calls the chosen provider (Relay, Symbiosis, Across, LI.FI, Rango, Squid, Stargate, Allbridge, a deposit address, and others), and then emits **`RubicTransferStarted(bridgeData)`**. That event is the source leg. The destination leg belongs to the provider: Rubic emits `RubicTransferCompleted` only when its own Executor or Receiver performs a destination swap, and that did not happen in the pinned window.

**Link key: `bridgeData.transactionId`.** It is a Rubic UUID (16 bytes, left-padded to `bytes32`), the same value as the `rubicId` of the Rubic API. It is on chain only on the source side for most routes. The destination transaction is available only from the Rubic API `GET /api/info/statusExtended?id=<rubicId>&srcTxHash=<hash>`, or from the underlying provider's own key. On the routes with a Rubic destination helper, `RubicTransferCompleted.transactionId` (topic1) carries the same value.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Address style |
|----------|------|--------|---------------|
| **RubicMultiProxy** | Diamond; all entry facets; emits `RubicTransferStarted`, fee events, `DiamondCut` | EIP-2535 diamond | `0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3` on Ethereum, Arbitrum, Optimism, Polygon, BNB, Avalanche; own address on Base and on Robinhood Chain |
| **ERC20Proxy** | Token-approval target. `startViaRubic` pulls tokens from the user to the diamond, then calls it | No (Ownable) | `0x3335733c454805df6a77f825f266e136FB4a3333` on all eight chains |
| **Executor** | Destination swap after a bridge; emits `RubicTransferCompleted` | No | `0x9E4B1205291d21eDaB4f710b2905628640e8D0F1` on six chains, not Base, not Robinhood Chain |
| **Receiver** | Stargate v1 (`sgReceive`) and Connext (`xReceive`) delivery; destination swap or recovery | No | `0xb15A66101ac2A6de589dAd1dCbbd7566DCCaB61D` on six chains, not Base, not Robinhood Chain |
| **StargateV2Receiver** | Stargate v2 `lzCompose` delivery; `ReceivedWithoutSwap` fallback | No | per chain (§4) |
| Facets | Logic contracts behind the diamond (§4) | — | Shared addresses on the six chains; own addresses on Base and Robinhood Chain |

Flow of one bridge transaction:

| Step | Chain | Event (emitter) | Value movement in the same tx |
|------|-------|-----------------|-------------------------------|
| Deposit | Source | `FixedNativeFee` and/or `TokenFee` (diamond), the provider's own event, then `RubicTransferStarted` (diamond) | ERC-20 `Transfer` user → diamond (pulled by the ERC20Proxy); fee `Transfer`s diamond → integrator and diamond → fee treasury; diamond → provider router or deposit address. Native coin in `msg.value` |
| Payout | Destination | Provider event (for example Relay, Symbiosis, Across). `RubicTransferCompleted` (Executor or Receiver) only on routes with a Rubic destination swap | Provider (solver or pool) → `receiver` |
| Refund | Source or destination | Provider-specific; `RubicTransferRecovered` (Receiver) when the Rubic destination swap fails | Bridged token → `receiver` on the destination chain |
| Same-chain swap | One chain | `RubicSwappedGeneric` (diamond) | Not a bridge exit |

Rubic's chain ids: `bridgeData.destinationChainId` is the EVM chain id for EVM targets (1, 8453 seen). For other targets Rubic uses its own values; 7565164, 195 and 5555 were seen in the window. Their mapping is not published (unverified). `bridgeData.bridge` names the provider route, for example `native:relay`, `native:symbiosis`, `native:across`, `native:squidrouter`, `native:rango`, `native:usdt_zero_bridge`, `lifi:lifi`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Transfer lifecycle (diamond; Executor, Receiver, StargateV2Receiver for the destination events)

| topic0 | Event | Leg / meaning |
|--------|-------|---------------|
| `0xf834e948c18ff30cc76e65c4bb09ce6f070fcea13e3cb45413d9a66686584b94` | `RubicTransferStarted((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) bridgeData)` | **Source leg.** Diamond, every bridge facet. No indexed field: `transactionId` sits in the data. The provider call that moves the funds ran before it in the same tx. |
| `0x34e358aa7c9dc397606c975bcb8d9b7719948910089f88899ad925da6cf37914` | `RubicTransferCompleted(bytes32 indexed transactionId, address receivingAssetId, address receiver, uint256 amount, uint256 timestamp)` | **Destination leg, Rubic-executed routes only.** Executor or Receiver after a destination swap. `amount` reached `receiver`. |
| `0xb4d555aedc14ae22500f15c3ea5430a96a258184c686762e56b945dac733ed4c` | `RubicTransferRecovered(bytes32 indexed transactionId, address receivingAssetId, address receiver, uint256 amount, uint256 timestamp)` | **Destination refund.** The destination swap failed; Receiver sent the bridged token to `receiver` as is. |
| `0xb6422835e7046b0692f1b80a12361c9fc693dbaf86a063f876a82ef68755670b` | `RubicSwappedGeneric(bytes32 indexed transactionId, address integrator, address referrer, address fromAssetId, address toAssetId, uint256 fromAmount, uint256 toAmount)` | Same-chain swap (`swapTokensGeneric`, `swapTokensGenericV2`). Not a bridge exit. |
| `0x7bfdfdb5e3a3776976e53cb0607060f54c5312701c8cba1155cc4d5394440b38` | `AssetSwapped(bytes32 transactionId, address dex, address fromAssetId, address toAssetId, uint256 fromAmount, uint256 toAmount, uint256 timestamp)` | One DEX step inside a source or destination swap. `transactionId` is not indexed. |
| `0x765fae3370ccbc0bb360d428d4e3b25fdb5d7fe8d143905a9759ece57afc91e1` | `Deposit((bytes32 rubicId, address integrator, address tokenIn, uint256 amountIn, address tokenIntermediateSrc, uint256 amountIntermediate, bytes32 tokenIntermediateDest, bytes32 tokenOut, uint256 amountOutMin, bytes32 finalReceiver, bytes32 allBridgeReceiver, uint256 allBridgeFee, uint256 destinationChainId, uint256 nonce, uint256 deadline) params)` | StellarFacet, Allbridge route to Stellar. Fires with `RubicTransferStarted`. `finalReceiver` is a Stellar key as `bytes32`. |
| `0x56c77728a6372ed33dcdc531f73975e2fed9d66cc790cbf7e753903f558d5e2d` | `ReceivedWithoutSwap(address receiver, address token, uint256 amount)` | StargateV2Receiver: the composed message could not swap; the token went to `receiver`. **Destination fallback.** |

### 1.2 Fees (diamond, inside the source transaction)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x74d5029b0a85dd485bf2414b0920760500d9535db170f72375f811087a6d2073` | `FixedNativeFee(uint256 RubicPart, uint256 integratorPart, address indexed integrator)` | Source tx: the fixed fee in native coin, paid to the fee treasury and the integrator. |
| `0x25471ec9f39b4ceb20d58f63c37f9c738011f0babcc4b6af69bdd82984ca5f8e` | `TokenFee(uint256 RubicPart, uint256 integratorPart, address indexed integrator, address token)` | Source tx: the percentage fee taken from the input token. |
| `0x053f4bc328e99290d8684003d9dd7baa32aae44c7feaf4da701bafa588afa6ac` | `FixedNativeFeeCollected(uint256 amount, address collector)` | Fee withdrawal (declared in `LibFees`). |
| `0x6f83ca8ce48e63b2a223b9f9e7ef1ea7bf3a8385c7a9bd63baae22963b2b26e0` | `IntegratorTokenFeeCollected(uint256 amount, address indexed integrator, address token)` | Fee withdrawal (declared in `LibFees`). |

### 1.3 Admin and configuration

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673` | `DiamondCut((address facetAddress, uint8 action, bytes4[] functionSelectors)[] _diamondCut, address _init, bytes _calldata)` | **Upgrade.** Facets added, replaced or removed. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Diamond, Executor, Receiver, ERC20Proxy, StargateV2Receiver. Admin. |
| `0xed8889f560326eb138920d842192f0eb3dd22b4f139c87a2c57538e05bae1278` | `OwnershipTransferRequested(address indexed _from, address indexed _to)` | Two-step owner change started. Admin. |
| `0x9207361cc2a04b9c7a06691df1eb87c6a63957ae88bf01d0d18c81e3d1272099` | `LogWithdraw(address indexed _assetAddress, address _to, uint256 amount)` | WithdrawFacet: the owner moved tokens out of the diamond. **Value moves.** |
| `0xd97cb52d6a919c35d1a9848f69806a32611c1381fa1078e5ea866186ee4c46c7` | `ExecutionAllowed(address indexed account, bytes4 indexed method)` | AccessManagerFacet. Admin. |
| `0x2fb75e73eca07a04ac148df401d1f013ddb4c8177a453af29c97c88037bac848` | `ExecutionDenied(address indexed account, bytes4 indexed method)` | AccessManagerFacet. Admin. |
| `0x7e0058dd0cbc0a8b7beaa013a4825655d8e9e81a5e2cc6582818deded0a41b99` | `DexAdded(address indexed dexAddress)` | Allow-list of call targets. Admin. |
| `0x78e0a2ffcdfbbb49ba5c8050d8630fab2176d825e8360809db049cd98f462a78` | `DexRemoved(address indexed dexAddress)` | Admin. |
| `0x9167f6a23d52a4522e9211205d62ce63f02d928227ae0fe00326f51e152a3c45` | `FunctionSignatureApprovalChanged(bytes4 indexed functionSignature, bool indexed approved)` | Allow-list of call selectors. Admin. |
| `0xb8097dccc219251c3398cc256986db299795be9f12cc8236420508f5cdb808fe` | `SetFixedNativeFee(uint256 fee)` | Admin. |
| `0xde73cb90b3667e7bb939263027398ebba5f7ff53aad0d7eba99f555e0c5ff379` | `SetRubicPlatformFee(uint256 fee)` | Admin. |
| `0x77970227df5d6e4dd8d30d52bd6c0c2e2aa3d8643ea960caec0627f53c0e3c97` | `SetMaxRubicPlatformFee(uint256 fee)` | Admin. |
| `0x8621ad378521883daa8108c9f45a36f29f3afaf85b0a464009b9b206aa7126ec` | `SelectorToInfoUpdated(address[] _routers, bytes4[] _selectors, (bool isAvailable, uint256 offset)[] _infos)` | GenericCrossChainFacet: provider routers and selectors that the generic route may call. Admin. |
| `0xb958172d7ec4fbc39369ce70d59e9962213cfb3e0c3fe159a3b3638f08292fd0` | `TransferWithBytesWhitelistUpdated(address[] addresses, bool[] whitelisted)` | TransferWithBytesFacet deposit-address allow-list. Admin. |
| `0xc2c7b6f89581aaed297b266b8b7687a221c3bbb4fadafb49df5e5d0a1fdea4ab` | `DiamondSet(address diamond)` | ERC20Proxy now forwards to another diamond. Admin. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

`BridgeData` = `(bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall)`. `SwapData` = `(address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)`; the V2 facets add `uint256 extraNative` after `fromAmount`.

### 2.1 Source entry points (ERC20Proxy and diamond facets)

Every `startBridgeTokensVia*` has a `swapAndStartBridgeTokensVia*` twin with a `SwapData[]` argument; only the twins that are live on a target chain and used by the generic routes are listed with their full signature.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe1fcde8e` | `startViaRubic(address[] tokens, uint256[] amounts, bytes facetCallData)` | **ERC20Proxy entry.** Pulls each token from `msg.sender` to the diamond, then calls the diamond with `facetCallData`. Users approve the ERC20Proxy, not the diamond. |
| `0x647eb57e` | `startBridgeTokensViaGenericCrossChain((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address router, address approveTo, uint256 extraNative, bytes callData) _genericData)` | Generic provider route (Relay, Symbiosis, Across, LI.FI, Rango and others). Calls `router` with `callData`. |
| `0xdc7ffff7` | `swapAndStartBridgeTokensViaGenericCrossChain((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData, (address router, address approveTo, uint256 extraNative, bytes callData) _genericData)` | Same, with source swaps. |
| `0xf3e639ef` | `startBridgeTokensViaGenericCrossChainV2((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address router, address approveTo, uint256 extraNative, bytes callData) _genericData)` | V2 facet (Arbitrum, BNB). Same flow. |
| `0xd0d97c4c` | `swapAndStartBridgeTokensViaGenericCrossChainV2((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, uint256 extraNative, bytes callData, bool requiresDeposit)[] _swapData, (address router, address approveTo, uint256 extraNative, bytes callData) _genericData)` | V2, source swaps with `extraNative`. |
| `0xfae622f5` | `startBridgeTokensViaGenericCrossChain((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address router, bytes callData) _genericData)` | Older generic facet still cut into the diamond on Ethereum, Arbitrum, Optimism, Polygon, BNB and Avalanche. |
| `0x8a2ef6e2` | `startBridgeTokensViaTransfer((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address destination) _transferData)` | Deposit-address route: a plain transfer of the input to `destination`. |
| `0x5b4c5718` | `swapAndStartBridgeTokensViaTransfer((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData, (address destination) _transferData)` | Same, with source swaps. |
| `0xe1731ba9` | `startBridgeTokensViaTransferWithBytes((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address destination, bytes extraData) _transferData)` | Deposit-address route with extra calldata appended (memo). Native only to allow-listed addresses. |
| `0x910ee221` | `swapAndStartBridgeTokensViaTransferWithBytes((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData, (address destination, bytes extraData) _transferData)` | Same, with source swaps. |
| `0xdb5482d8` | `startBridgeTokensViaSymbiosis((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (bytes firstSwapCalldata, bytes secondSwapCalldata, address intermediateToken, address firstDexRouter, address secondDexRouter, address approveTo, address callTo, bytes otherSideCalldata) _symbiosisData)` | Symbiosis facet. |
| `0x82361d3a` | `startBridgeTokensViaStargate((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (uint256 dstPoolId, uint256 minAmountLD, uint256 dstGasForCall, uint256 lzFee, address refundAddress, bytes callTo, bytes callData) _stargateData)` | Stargate v1 facet. |
| `0xd0eaff76` | `startBridgeTokensViaXY((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address toChainToken, uint256 expectedToChainTokenAmount, uint32 slippage) _xyData)` | XY facet. |
| `0x988f3e5f` | `startBridgeTokensViaMultichain((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (address router) _multichainData)` | Multichain facet (Optimism only; Multichain is defunct). |
| `0xbc2d6f1d` | `startBridgeTokensViaAllBridge((bytes32 transactionId, string bridge, address integrator, address referrer, address sendingAssetId, address receivingAssetId, address receiver, address refundee, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) _bridgeData, (bytes32[2] tokensOut, uint256 amountOutMin, bytes32 finalReceiver, bytes32 allBridgeReceiver, uint256 nonce, uint256 destinationSwapDeadline, uint256 allBridgeFee) _stellarData)` | StellarFacet: Allbridge to Stellar. Emits `Deposit`. |
| `0xb3474174` | `swapTokensGeneric(bytes32 _transactionId, address _integrator, address _referrer, address _receiver, uint256 _minAmount, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData)` | Same-chain swap. |
| `0x1a5e66f0` | `swapTokensGenericV2(bytes32 _transactionId, address _integrator, address _referrer, address _receiver, uint256 _minAmount, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, uint256 extraNative, bytes callData, bool requiresDeposit)[] _swapData)` | Same-chain swap, V2 facet (Arbitrum, BNB). |

### 2.2 Destination helpers

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4f91bc2b` | `swapAndCompleteBridgeTokens(bytes32 _transactionId, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData, address _transferredAssetId, address _receiver)` | Executor and Receiver: destination swap. Emits `RubicTransferCompleted`. |
| `0xab8236f3` | `sgReceive(uint16 _chainId, bytes _srcAddress, uint256 _nonce, address _token, uint256 _amountLD, bytes _payload)` | Receiver: Stargate v1 delivery. |
| `0xfd614f41` | `xReceive(bytes32 _transferId, uint256 _amount, address _asset, address _originSender, uint32 _origin, bytes _callData)` | Receiver: Connext (Amarok) delivery. |
| `0xd0a10260` | `lzCompose(address _from, bytes32 _guid, bytes _message, address _executor, bytes _extraData)` | StargateV2Receiver: Stargate v2 composed delivery. |

### 2.3 Admin

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1f931c1c` | `diamondCut((address facetAddress, uint8 action, bytes4[] functionSelectors)[] _diamondCut, address _init, bytes _calldata)` | Owner only. Emits `DiamondCut`. |
| `0xd9caed12` | `withdraw(address _assetAddress, address _to, uint256 _amount)` | Owner only. Emits `LogWithdraw`. |
| `0x1458d7ad` | `executeCallAndWithdraw(address _callTo, bytes _callData, address _assetAddress, address _to, uint256 _amount)` | Owner only. Arbitrary call, then withdraw. |
| `0xf2fde38b` | `transferOwnership(address _newOwner)` | Owner only, step 1 of 2 (diamond). |
| `0x7200b829` | `confirmOwnershipTransfer()` | Pending owner, step 2 of 2. |
| `0xa4c3366e` | `setCanExecute(bytes4 _selector, address _executor, bool _canExecute)` | Owner only. Emits `ExecutionAllowed` or `ExecutionDenied`. |
| `0x536db266` | `addDex(address _dex)` | Owner or allowed caller. Emits `DexAdded`. |
| `0xc3a6a96b` | `setFunctionApprovalBySignature(bytes4 _signature, bool _approval)` | Emits `FunctionSignatureApprovalChanged`. |
| `0x2bd19fde` | `updateSelectorInfo(address[] _routers, bytes4[] _selectors, (bool isAvailable, uint256 offset)[] _infos)` | Owner only. Emits `SelectorToInfoUpdated`. |
| `0xb395d295` | `setFeeTreasure(address _feeTreasure)` | Changes where Rubic fees go. |
| `0x95c54f5a` | `setRubicPlatformFee(uint256 _platformFee)` | Emits `SetRubicPlatformFee`. |
| `0x6d0f18c4` | `setFixedNativeFee(uint256 _fixedNativeFee)` | Emits `SetFixedNativeFee`. |
| `0x76ed535a` | `setDiamond(address _diamond)` | ERC20Proxy owner only. Emits `DiamondSet`. |

### 2.4 Views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8da5cb5b` | `owner()` | `address`. |
| `0x7a0ed627` | `facets()` | `(address,bytes4[])[]`: the live facet table. |
| `0xcdffacc6` | `facetAddress(bytes4 _functionSelector)` | `address` of the facet that serves a selector. |
| `0xb6f33048` | `feeTreasure()` | `address`. |
| `0xf0b7db4e` | `diamond()` | ERC20Proxy: the diamond it forwards to. |

Selectors live in the diamond but without verified source (unverified, not decoded): `0x159d733f` and `0xc18e2e2b` (facet `0xBd7f4c3f40d79e421AE2cE67fCBf74cc9601dCcE`, Ethereum), `0x2aef58f2` (facet `0xB1Df4293DE4526602A49994e520b9171Ea668356`, Ethereum), `0x65f0fb1c` and `0x8b2fba1b` (facet `0x2477aEdF720bcef191a172667266C3435b7FB89d`, Base).

---

## 3. Addresses — Ethereum (chain ID 1)

| Role | Address | One-liner |
|------|---------|-----------|
| **RubicMultiProxy** (diamond) | `0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3` | 5,176 B; 18 facets live |
| **ERC20Proxy** | `0x3335733c454805df6a77f825f266e136FB4a3333` | `diamond()` = the diamond above |
| **Executor** | `0x9E4B1205291d21eDaB4f710b2905628640e8D0F1` | Destination swap helper |
| **Receiver** | `0xb15A66101ac2A6de589dAd1dCbbd7566DCCaB61D` | Stargate v1 / Connext receiver |
| StargateV2Receiver | `0x15A50d8417c2cD58d0A3535F1b1533b312346623` | `lzCompose` receiver |
| Diamond owner | `0x00009cc27c811a3e0fdd2fd737afcc721b67ee8e` | Same owner on all eight chains. Here it has 23 B of code: an EIP-7702 delegation (`0xef0100` + `0x63c0c19a282a1b52b07dd5a65b58948a07dae32b`). Not a Safe |
| Fee treasury (`feeTreasure()`) | `0x60745f5a9742fe905bbde2f57808416edf2b8696` | EOA (nonce 22,818); same on Ethereum, Base and Robinhood Chain |

## 4. Addresses — the other chains, and the facet tables

### 4.1 Arbitrum One (42161), Optimism (10), Polygon PoS (137), BNB Smart Chain (56), Avalanche C-Chain (43114)

The diamond, ERC20Proxy, Executor and Receiver have the Ethereum addresses (same code hash on all six chains). The owner is `0x00009cc27c811a3e0fdd2fd737afcc721b67ee8e` on all: an EIP-7702-delegated account on Arbitrum (23 B of code), a plain EOA elsewhere.

| Chain | StargateV2Receiver |
|-------|--------------------|
| Arbitrum One | `0x5386Ff2EEF2D50069F2dfF2F79f3126c9940BAe8` |
| Optimism | `0xC2b704A6690A5bE68712C5828B58A9f73B0e9285` |
| Polygon PoS | `0xB41c1eFFa54Fc948f98BC4324C15bb0Ed3e2212a` |
| BNB Smart Chain | `0xDAd6723eb88bf4D20404687B1828e26d5D6eA498` |
| Avalanche C-Chain | `0x3DAd1f1702fEF42bDe9953ae30290d0d89F2890a` |

Live facets (`facets()`), shared addresses on the six chains:

| Facet | Address | ETH | ARB | OP | POLY | BNB | AVAX |
|-------|---------|-----|-----|----|------|-----|------|
| DiamondCutFacet | `0xcc64E129D2A80adee32D9bF2BCBecf0E9226Bfa6` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| DiamondLoupeFacet | `0x1918B6cE6E7B1E536de210f43382b958dAfDC3B9` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| OwnershipFacet | `0x1265C279CbB0DF619808B82cb1f47DC46a10E7e9` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WithdrawFacet | `0xF67778b8475Fe1D0b6c392899A61CC1846aC77C0` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| DexManagerFacet | `0x0B24e264659B3c903C818170498e093916Ed66AA` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| AccessManagerFacet | `0x65FDD04099a08b362d8ddB7e4a8EF467D464EC1c` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| FeesFacet | `0xEA967afBA9E692E4B8dd984A0713FA5E4139993b` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| GenericCrossChainFacet | `0x050b1A40fBcAC0beccD9520D7363A33827283030` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| GenericCrossChainFacet (older, `(address router, bytes callData)` data) | `0x51439AdC4d262580F355c450e78662BC80ab35ed` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| GenericCrossChainFacetV2 | `0x4dd8D62229BaF0B1ACcC3dE5c0637291323EF6b6` | — | ✓ | — | — | ✓ | — |
| GenericSwapFacet | `0x9149e311B70A7E61CCe4C963CbeFC6bc72746A22` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| GenericSwapFacetV2 | `0x167D54C29A448fC0b9596EA530223330D608e22f` | — | ✓ | — | — | ✓ | — |
| TransferFacet | `0x9f50F4122B3d66397859C146e3489B4c0f66E17d` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| TransferWithBytesFacet | `0x9556eC186526C028c3260737EA26A53EB51ce47B` (Arbitrum: `0x8E49E1A0B9C2315780Ba732c825062A10C4A82B8`) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| SymbiosisFacet | `0xeCF2e32AfC90A774b0fc3cbd012B681EBfaA0BAF` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| StargateFacet | `0x578b327C89DF0f33995Cb93415E191e7bF942270` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| XYFacet | `0x21998A2E576B62152D64eCFcE9DE2DAAeCDa75D6` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| MultichainFacet | `0x25192a562D1d14735a5b3c52432766a6Cd04a841` | — | — | ✓ | — | — | — |
| StellarFacet (Allbridge) | `0x3dd2f184953A72EA00011D854C371639b95169d0` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

The `deployments/<chain>.json` files still list MultichainFacet on Ethereum, Arbitrum, Polygon, BNB and Avalanche, but `facets()` does not serve it there.

### 4.2 Base (chain ID 8453)

| Role | Address |
|------|---------|
| **RubicMultiProxy** (diamond) | `0xAf14797CcF963B1e3d028a9d51853acE16aedBA1` (same 5,176-byte code hash as the other diamond) |
| **ERC20Proxy** | `0x3335733c454805df6a77f825f266e136FB4a3333` (`diamond()` = `0xAf14797CcF963B1e3d028a9d51853acE16aedBA1`) |
| StargateV2Receiver | `0x329260b208e30c778Cd0869b3646931113129A4c` |
| Facets | DiamondCut `0xAa4472EC72cF4771dfD38467f161F6DF6cA3FB1a`, DiamondLoupe `0xf747DA269c7a65d123d4851515927b082e23aBd2`, Ownership `0xce0f6610fc406f689C854Ac517eA15D0205c11E3`, Withdraw `0x40785ea9e20B7F93ab0d9DCe73B0775d52901e66`, DexManager `0xc4A04649E0e2bCC5859F8aAa7c7A79a1a0cC388d`, AccessManager `0xC9fa6Ca19d49ff5a677181369eB8a58688E74924`, Fees `0x6535B3E3802941B91405306CDF6c89A45875Fc98`, GenericSwap `0xb656E75248Ee97e14Dccb5EC559Da32a5b70c8eF`, GenericCrossChain `0x1C7cc271Ad9DBe625a07C653aE61b757fdFCbe91`, Transfer `0x8c47b31591700b9134c0560E2CF813e6Dc14EDcf`, Stargate `0xa3fF0c0Fa72D893956cec227096658ec67169d89`, TransferWithBytes `0xF0d40864FC8d0b2255871af3C355963593372e01`, unverified `0x2477aEdF720bcef191a172667266C3435b7FB89d` |

No Executor and no Receiver on Base (`eth_getCode` = `0x` at both addresses). `0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3` has no code on Base.

### 4.3 Robinhood Chain (chain ID 4663)

| Role | Address |
|------|---------|
| **RubicMultiProxy** (diamond) | `0xDEDC96a5FA4C3C4A329816E167b620C38A3BB228` (5,176 B, own code hash) |
| **ERC20Proxy** | `0x3335733c454805df6a77f825f266e136FB4a3333` (own code hash; `diamond()` = `0xDEDC96a5FA4C3C4A329816E167b620C38A3BB228`) |
| Facets | DiamondCut `0xA0c914534e9B2228d613213ffF27A94B4e047db5`, DiamondLoupe `0x2d35bA27790A2DE45C35a53c39F07Fb8b6630743`, Ownership `0x60CdEE71f1f95CE89F630C5667E7fAD5334e2DfF`, Withdraw `0x52648b5Af9D1547323eDBb4c49dc404F5e95812B`, DexManager `0x39853d117202818867c13B3902590109f6177F01`, AccessManager `0x56Ba315c91e0AdE48c54396284af4d4b70D30D60`, Fees `0x6407f6fBC8849D705E3Ae3D3A232b88321e410cf`, GenericCrossChain `0x8EdF8231E0A72D02b4f9CF263B3BB562d299b063`, GenericSwap `0x3388E5a7EE2bf67d11e8bDbe19603443b964Cdb4`, TransferWithBytes `0xF0d40864FC8d0b2255871af3C355963593372e01` |

Only generic, transfer-with-bytes and swap routes exist here. No Executor, Receiver or StargateV2Receiver. The owner `0x00009cc27c811a3e0fdd2fd737afcc721b67ee8e` is a plain EOA here (nonce 26).

---

## 5. Cross-chain summary

| Chain | ID | RubicMultiProxy | ERC20Proxy | Executor / Receiver | StargateV2Receiver | `RubicTransferStarted` in the window |
|-------|----|-----------------|------------|---------------------|--------------------|-------------------------------------:|
| Ethereum | 1 | `0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3` | `0x3335733c454805df6a77f825f266e136FB4a3333` | yes | yes | 7 |
| Base | 8453 | `0xAf14797CcF963B1e3d028a9d51853acE16aedBA1` | `0x3335733c454805df6a77f825f266e136FB4a3333` | no | yes | 2 |
| Arbitrum One | 42161 | `0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3` | `0x3335733c454805df6a77f825f266e136FB4a3333` | yes | yes | 1 |
| Optimism | 10 | `0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3` | `0x3335733c454805df6a77f825f266e136FB4a3333` | yes | yes | 0 |
| Polygon PoS | 137 | `0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3` | `0x3335733c454805df6a77f825f266e136FB4a3333` | yes | yes | 13 |
| BNB Smart Chain | 56 | `0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3` | `0x3335733c454805df6a77f825f266e136FB4a3333` | yes | yes | 11 |
| Avalanche C-Chain | 43114 | `0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3` | `0x3335733c454805df6a77f825f266e136FB4a3333` | yes | yes | 0 |
| Robinhood Chain | 4663 | `0xDEDC96a5FA4C3C4A329816E167b620C38A3BB228` | `0x3335733c454805df6a77f825f266e136FB4a3333` | no | no | 0 |

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **RubicMultiProxy** | EIP-2535 diamond (`LibDiamond`) | No EIP-1967 slot; the logic per selector comes from `facetAddress(bytes4)` / `facets()`. Watch `DiamondCut` (`0x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673`) on the diamond | `diamondCut`, contract owner only. Owner `0x00009cc27c811a3e0fdd2fd737afcc721b67ee8e` on all eight chains: a single account, not a Safe |
| ERC20Proxy | Not a proxy (OpenZeppelin `Ownable`) | Plain code | `setDiamond` (owner) redirects every future `startViaRubic`; watch `DiamondSet` |
| Executor, Receiver, StargateV2Receiver | Not proxies | Plain code | Owner can change the Stargate router, executor and recover gas (Receiver) and withdraw stuck assets (StargateV2Receiver) |

---

## 7. Detection invariants & gotchas

1. **`RubicTransferStarted` has no indexed field.** Filter on topic0 and the emitter (the diamond), then decode the tuple. `transactionId` is the first word of the tuple data, not a topic.
2. **`transactionId` is the off-chain `rubicId`.** On-chain value `0x00000000000000000000000000000000f5f2f404cb834a7f94af0f9fc30160d6` = API id `f5f2f404-cb83-4a7f-94af-0f9fc30160d6`. The Rubic API returned the destination tx of that transfer (§9). Without the API, link through the underlying provider's own key.
3. **The value moves before the event.** In the same tx: user → diamond (pulled by the ERC20Proxy), fee transfers, then diamond → provider. `minAmount` in the event is the amount after fees and source swaps, sent to the provider.
4. **Rubic stacks on other aggregators.** `bridge` = `lifi:lifi` means the diamond called LI.FI, which emits its own `LiFiTransferStarted`; `native:squidrouter` means the diamond called the SquidRouter; `native:relay`, `native:across`, `native:symbiosis` call those bridges. The same exit can appear two or three times. Count it once.
5. **`receiver` may be a placeholder.** For a non-EVM destination (`destinationChainId` 7565164, 195, 5555), the real recipient is in the provider calldata or the provider's event, not in the `address receiver` field.
6. **`tx.to` is the ERC20Proxy for token deposits.** Users approve and call `0x3335733c454805df6a77f825f266e136FB4a3333`; native-coin deposits call the diamond directly. The diamond address differs on Base and Robinhood Chain; the ERC20Proxy address does not.
7. **Destination events are rare.** `RubicTransferCompleted`, `RubicTransferRecovered` and the Stellar `Deposit` returned 0 logs from any emitter on all eight chains in the pinned window. Do not wait for a Rubic destination event to close a transfer.
8. **The owner can move funds held by the diamond.** `withdraw` and `executeCallAndWithdraw` (WithdrawFacet) emit `LogWithdraw`; `diamondCut` can add any logic. The diamond holds funds only inside a transaction, but a malicious cut affects every approval given to the ERC20Proxy. Alert on `DiamondCut`, `DiamondSet`, `OwnershipTransferred`, `LogWithdraw`, `SelectorToInfoUpdated` and `TransferWithBytesWhitelistUpdated`.
9. **`OwnershipTransferred(address,address)` collides** with every OpenZeppelin contract. Filter on the emitter.
10. **Deployment files are not the live state.** The live facet table differs from `deployments/<chain>.diamond.json` (V2 facets on Arbitrum and BNB, MultichainFacet only on Optimism, unverified facets on Ethereum and Base). Read `facets()` before you trust a selector-to-facet map. The Avalanche file writes the StargateV2Receiver with a trailing dot (`0x3DAd1f1702fEF42bDe9953ae30290d0d89F2890a.`); the address without the dot has code.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_RUBIC_TRANSFER_STARTED      = '\xf834e948c18ff30cc76e65c4bb09ce6f070fcea13e3cb45413d9a66686584b94'
TOPIC_RUBIC_TRANSFER_COMPLETED    = '\x34e358aa7c9dc397606c975bcb8d9b7719948910089f88899ad925da6cf37914'
TOPIC_RUBIC_TRANSFER_RECOVERED    = '\xb4d555aedc14ae22500f15c3ea5430a96a258184c686762e56b945dac733ed4c'
TOPIC_RUBIC_SWAPPED_GENERIC       = '\xb6422835e7046b0692f1b80a12361c9fc693dbaf86a063f876a82ef68755670b'
TOPIC_RUBIC_ASSET_SWAPPED         = '\x7bfdfdb5e3a3776976e53cb0607060f54c5312701c8cba1155cc4d5394440b38'
TOPIC_RUBIC_STELLAR_DEPOSIT       = '\x765fae3370ccbc0bb360d428d4e3b25fdb5d7fe8d143905a9759ece57afc91e1'
TOPIC_RUBIC_RECEIVED_WITHOUT_SWAP = '\x56c77728a6372ed33dcdc531f73975e2fed9d66cc790cbf7e753903f558d5e2d'
TOPIC_RUBIC_FIXED_NATIVE_FEE      = '\x74d5029b0a85dd485bf2414b0920760500d9535db170f72375f811087a6d2073'
TOPIC_RUBIC_TOKEN_FEE             = '\x25471ec9f39b4ceb20d58f63c37f9c738011f0babcc4b6af69bdd82984ca5f8e'
TOPIC_RUBIC_DIAMOND_CUT           = '\x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673'
TOPIC_RUBIC_LOG_WITHDRAW          = '\x9207361cc2a04b9c7a06691df1eb87c6a63957ae88bf01d0d18c81e3d1272099'
TOPIC_RUBIC_DIAMOND_SET           = '\xc2c7b6f89581aaed297b266b8b7687a221c3bbb4fadafb49df5e5d0a1fdea4ab'
TOPIC_RUBIC_SELECTOR_INFO_UPDATED = '\x8621ad378521883daa8108c9f45a36f29f3afaf85b0a464009b9b206aa7126ec'
TOPIC_OWNERSHIP_TRANSFERRED       = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'

-- ===== Selectors (chain-agnostic) =====
SEL_RUBIC_START_VIA_RUBIC         = '\xe1fcde8e'
SEL_RUBIC_GENERIC_CROSS_CHAIN     = '\x647eb57e'
SEL_RUBIC_SWAP_GENERIC_CROSS_CHAIN= '\xdc7ffff7'
SEL_RUBIC_GENERIC_CROSS_CHAIN_V2  = '\xf3e639ef'
SEL_RUBIC_VIA_TRANSFER            = '\x8a2ef6e2'
SEL_RUBIC_VIA_TRANSFER_WITH_BYTES = '\xe1731ba9'
SEL_RUBIC_VIA_SYMBIOSIS           = '\xdb5482d8'
SEL_RUBIC_VIA_STARGATE            = '\x82361d3a'
SEL_RUBIC_VIA_ALLBRIDGE           = '\xbc2d6f1d'
SEL_RUBIC_SWAP_TOKENS_GENERIC     = '\xb3474174'
SEL_RUBIC_COMPLETE_BRIDGE_TOKENS  = '\x4f91bc2b'
SEL_RUBIC_DIAMOND_CUT             = '\x1f931c1c'
SEL_RUBIC_WITHDRAW                = '\xd9caed12'
SEL_RUBIC_EXECUTE_CALL_AND_WITHDRAW='\x1458d7ad'

-- ===== Addresses =====
ETH_RUBIC_DIAMOND                 = '\x6aa981bff95edfea36bdae98c26b274ffcafe8d3'
ARB_RUBIC_DIAMOND                 = '\x6aa981bff95edfea36bdae98c26b274ffcafe8d3'
OP_RUBIC_DIAMOND                  = '\x6aa981bff95edfea36bdae98c26b274ffcafe8d3'
POLY_RUBIC_DIAMOND                = '\x6aa981bff95edfea36bdae98c26b274ffcafe8d3'
BNB_RUBIC_DIAMOND                 = '\x6aa981bff95edfea36bdae98c26b274ffcafe8d3'
AVAX_RUBIC_DIAMOND                = '\x6aa981bff95edfea36bdae98c26b274ffcafe8d3'
BASE_RUBIC_DIAMOND                = '\xaf14797ccf963b1e3d028a9d51853ace16aedba1'
RH_RUBIC_DIAMOND                  = '\xdedc96a5fa4c3c4a329816e167b620c38a3bb228'
ETH_RUBIC_ERC20_PROXY             = '\x3335733c454805df6a77f825f266e136fb4a3333'
BASE_RUBIC_ERC20_PROXY            = '\x3335733c454805df6a77f825f266e136fb4a3333'
RH_RUBIC_ERC20_PROXY              = '\x3335733c454805df6a77f825f266e136fb4a3333'
ETH_RUBIC_EXECUTOR                = '\x9e4b1205291d21edab4f710b2905628640e8d0f1'
ETH_RUBIC_RECEIVER                = '\xb15a66101ac2a6de589dad1dcbbd7566dccab61d'
ETH_RUBIC_STARGATE_V2_RECEIVER    = '\x15a50d8417c2cd58d0a3535f1b1533b312346623'
BASE_RUBIC_STARGATE_V2_RECEIVER   = '\x329260b208e30c778cd0869b3646931113129a4c'
ARB_RUBIC_STARGATE_V2_RECEIVER    = '\x5386ff2eef2d50069f2dff2f79f3126c9940bae8'
OP_RUBIC_STARGATE_V2_RECEIVER     = '\xc2b704a6690a5be68712c5828b58a9f73b0e9285'
POLY_RUBIC_STARGATE_V2_RECEIVER   = '\xb41c1effa54fc948f98bc4324c15bb0ed3e2212a'
BNB_RUBIC_STARGATE_V2_RECEIVER    = '\xdad6723eb88bf4d20404687b1828e26d5d6ea498'
AVAX_RUBIC_STARGATE_V2_RECEIVER   = '\x3dad1f1702fef42bde9953ae30290d0d89f2890a'
RUBIC_DIAMOND_OWNER_EOA           = '\x00009cc27c811a3e0fdd2fd737afcc721b67ee8e'
RUBIC_FEE_TREASURY_EOA            = '\x60745f5a9742fe905bbde2f57808416edf2b8696'
```

---

## 9. Verification & sources

How the constants were verified (2026-09-29 to 2026-10-01):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `Cryptorubic/multi-proxy-rubic` `src/` (`IRubic.sol`, `LibFees.sol`, `LibSwap.sol`, `LibDiamond.sol`, the facets and the periphery) and from the verified ABIs on Blockscout (Ethereum facets, Executor, Receiver, StargateV2Receiver, ERC20Proxy; Arbitrum `GenericCrossChainFacetV2` and `GenericSwapFacetV2`). Every facet selector in §2.1 and §2.3 is served by the live `facets()` table of at least one chain. The V2 selectors `0xf3e639ef`, `0xd0d97c4c` and `0x1a5e66f0` also match the public signature database.
- **Addresses:** from `deployments/<chain>.json` for `mainnet`, `base`, `arbitrum`, `optimism`, `polygon`, `bsc`, `avalanche` and `robinhood`, existence-checked with `eth_getCode` on all eight chains. `facets()`, `owner()`, `feeTreasure()` and `ERC20Proxy.diamond()` read live. The owner's code on Ethereum read with `eth_getCode` (`0xef0100` delegation designator).
- **Measured activity**, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (`eth_getLogs`): `RubicTransferStarted` at the diamond — Ethereum 7, Base 2, Arbitrum 1, Optimism 0, Polygon 13, BNB 11, Avalanche 0, Robinhood Chain 0 (the Robinhood diamond emitted 0 logs of any topic). `RubicTransferCompleted`, `RubicTransferRecovered` and Stellar `Deposit`: 0 from any emitter on all eight chains. All 34 `RubicTransferStarted` logs were decoded; `bridge` and `destinationChainId` values in §0 come from them. Counts hold for this window only.
- **Sample transactions read:** Ethereum `0x38629cd302b08ea9f6c3102775fa078b1bae79d9b2517a64bf6b98e2cdd83e17` (`startViaRubic` on the ERC20Proxy; token user → diamond; `FixedNativeFee` and `TokenFee`; fees to integrator `0x8192128df845469d3f4bb6acfeea057dbe34f4fc` and to the treasury; Relay route; `RubicTransferStarted`, `bridge` = `native:relay`, destination 8453). The Rubic API `statusExtended` for its `rubicId` returned `SUCCESS` and Base tx `0x0b19afe1be8ee2c7e8654b2286b4cda04f5cc0454a2d0ba500d13568058fc7de`; that tx is a Relay solver fill that pays the `receivingAssetId` token to the same `receiver`. A control query with an unknown id returned `NOT_FOUND`.

Sources:
- [Cryptorubic/multi-proxy-rubic](https://github.com/Cryptorubic/multi-proxy-rubic) (`deployments/`, `src/Interfaces/IRubic.sol`, `src/Facets/`, `src/Periphery/`)
- [Rubic docs — Understanding Flow Execution](https://docs.rubic.finance/api-docs/about/core-concepts/understanding-flow-execution) · [Refunds](https://docs.rubic.finance/api-docs/about/core-concepts/refunds) · [Get transaction status](https://docs.rubic.finance/api-reference/info/get-transaction-status) · [Security](https://docs.rubic.finance/rubic/overview/security)
- Verified source: [Blockscout Ethereum, RubicMultiProxy](https://eth.blockscout.com/address/0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3) · [Blockscout Ethereum, ERC20Proxy](https://eth.blockscout.com/address/0x3335733c454805df6a77f825f266e136FB4a3333) · [Blockscout Arbitrum, GenericCrossChainFacetV2](https://arbitrum.blockscout.com/address/0x4dd8D62229BaF0B1ACcC3dE5c0637291323EF6b6) · [Etherscan, RubicMultiProxy](https://etherscan.io/address/0x6aa981bff95edfea36bdae98c26b274ffcafe8d3)
