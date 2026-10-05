# LI.FI Diamond — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain + Arc)

**Status:** verified on 2026-09-29 against live RPC on all eight chains (Arc added 2026-10-05), the canonical `lifinance/contracts` repository (`src/`, `deployments/<network>.json`, `deployments/<network>.diamond.json`, `deployments/_deployments_log_file.json`) and the verified sources on the chain explorers. Every topic0 and selector was recomputed as `keccak256(signature)`. The live facet set of every diamond was read with the loupe call `facets()`, and every live selector was matched to a verified ABI. Every address was existence-checked with `eth_getCode`.
**Scope:** the LiFiDiamond (EIP-2535), which is the single entry point of LI.FI for bridge and swap transactions: its transfer events, its admin and security events, its admin and swap selectors, and its address, owner and pauser on each chain. The diamond has the same address on seven chains (`0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE`) its own address on Robinhood Chain (`0xB477751B76CF82d00a686A1232f5fCD772414Af3`) and its own address on Arc (`0xA4072583658Fae592A3506A42431cb6316a8d40b`). The per-bridge facets (entry selectors, data structs, facet addresses) are in [facets.md](facets.md). The destination-side contracts (Executor, receivers) and the other periphery are in [periphery.md](periphery.md). Topics and selectors are chain-agnostic; addresses are network-specific.

LI.FI is a bridge and DEX aggregator. It does not run a bridge. The user calls the diamond, the diamond takes the user's tokens (ERC-20 `Transfer` user → diamond, or native value in `msg.value`), takes fees, runs optional source swaps, and then calls the underlying bridge in the same transaction. The underlying bridge emits its own deposit event in that transaction (for example Across `FundsDeposited`, a Relay depository deposit, a Mayan or NEAR Intents deposit). The diamond emits `LiFiTransferStarted` as the source-leg record of every bridge route.

Four facts to know before indexing:

1. **Every facet event is emitted by the diamond address.** Facets run through `DELEGATECALL`, so `log.address` is the diamond, never the facet. The one exception is the packed Across facet, which is also called directly as a standalone contract (§1.2).
2. **The diamond is not an EIP-1967 proxy.** Its logic changes by `DiamondCut` events. The owner is a `LiFiTimelockController` with a minimum delay of 10,800 seconds (3 hours). A separate pauser wallet can pause the diamond or remove a facet at once (§12).
3. **`LiFiTransferStarted` has no indexed field.** Filter by topic0 and emitter, then decode the data words (§1.1). The link key `transactionId` is data word 1.
4. **There is no diamond event on the destination chain.** The funds arrive through the underlying bridge. Only routes with a destination call go through a LI.FI receiver and the Executor, which emit `LiFiTransferCompleted` or `LiFiTransferRecovered` ([periphery.md](periphery.md)).

---

## 0. Contract families & versions

| Contract | Address | Chains | Role | Upgradeable? |
|----------|---------|--------|------|--------------|
| **LiFiDiamond** | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | ETH·Base·Arb·OP·Poly·BNB·Avax | Entry point. Holds the selector-to-facet table and emits every facet event. | Yes: EIP-2535 `diamondCut`, owner only. |
| **LiFiDiamond** (Robinhood Chain) | `0xB477751B76CF82d00a686A1232f5fCD772414Af3` | Robinhood Chain (4663) | Same contract, another address. `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` has no code on Robinhood Chain. | Yes, as above. |
| **LiFiDiamond** (Arc) | `0xA4072583658Fae592A3506A42431cb6316a8d40b` | Arc (5042) | Same contract, another address. Neither `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` nor `0xB477751B76CF82d00a686A1232f5fCD772414Af3` has code on Arc. | Yes, as above. |
| Core facets | see [facets.md](facets.md) §3 | all 9 | DiamondCutFacet, DiamondLoupeFacet, OwnershipFacet, AccessManagerFacet, EmergencyPauseFacet, WithdrawFacet, PeripheryRegistryFacet, WhitelistManagerFacet, CalldataVerificationFacet. | Replaced by `diamondCut`. |
| GenericSwapFacetV3 | see [facets.md](facets.md) §3 | all 9 | Same-chain swaps. Emits `LiFiGenericSwapCompleted` and `AssetSwapped`. | Replaced by `diamondCut`. |
| Bridge facets | see [facets.md](facets.md) | per chain | One facet per bridge (Across, Relay, Mayan, NEAR Intents, Stargate, deBridge DLN, Glacis, Garden, GasZip, Symbiosis and others). Each emits `LiFiTransferStarted`. | Replaced by `diamondCut`. |
| **LiFiTimelockController** (owner) | see §3–§10a | all 9 | OpenZeppelin `TimelockController` with LI.FI helpers. Owner of the diamond. Minimum delay 10,800 s. | Not a proxy. |
| Pauser wallet | `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` | all 9 | Returned by `pauserWallet()`. Can call `pauseDiamond()` and `removeFacet()` with no delay. No code (EOA). | — |
| Staging diamonds | see §11 | 6 chains | LI.FI test diamonds. Same events and selectors. Not production traffic. | Yes |

Facets live on 2026-09-29 (loupe `facets()`): Ethereum 41 / 150, Base 34 / 134, Arbitrum 33 / 133, Optimism 29 / 121, Polygon 30 / 122, BNB 30 / 115, Avalanche 26 / 105, Robinhood Chain 19 / 68 (facets / selectors). Arc on 2026-10-05: 19 / 71.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Transfer events emitted by the diamond (source leg and same-chain swaps)

Emitter: the diamond on each chain (§3–§10).

| topic0 | Event |
|--------|-------|
| `0xcba69f43792f9f399347222505213b55af8e0b0b54b893085c2e27ecbe1644f1` | `LiFiTransferStarted((bytes32 transactionId, string bridge, string integrator, address referrer, address sendingAssetId, address receiver, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall) bridgeData)` |
| `0x815cd8dc72093a13fe3577112c391b6279303956526382ab98772d0239dbf78c` | `BridgeToNonEVMChainBytes32(bytes32 indexed transactionId, uint256 indexed destinationChainId, bytes32 receiver)` |
| `0xf9b69f466270c99522169d563c0a430e88c52865ec33b1cc36ee2a4a6ea5170b` | `BridgeToNonEVMChain(bytes32 indexed transactionId, uint256 indexed destinationChainId, bytes receiver)` |
| `0x7bfdfdb5e3a3776976e53cb0607060f54c5312701c8cba1155cc4d5394440b38` | `AssetSwapped(bytes32 transactionId, address dex, address fromAssetId, address toAssetId, uint256 fromAmount, uint256 toAmount, uint256 timestamp)` |
| `0x38eee76fd911eabac79da7af16053e809be0e12c8637f156e77e1af309b99537` | `LiFiGenericSwapCompleted(bytes32 indexed transactionId, string integrator, string referrer, address receiver, address fromAssetId, address toAssetId, uint256 fromAmount, uint256 toAmount)` |
| `0x93517b7c6f32856737008edf37cf2542b55d27d83fa299aa216f55a982a6ee1d` | `LiFiSwappedGeneric(bytes32 indexed transactionId, string integrator, string referrer, address fromAssetId, address toAssetId, uint256 fromAmount, uint256 toAmount)` |

Data layout for SQL (32-byte words, word 0 first):

- `LiFiTransferStarted`: the tuple is dynamic, so word 0 is the offset `0x20`. Word 1 `transactionId`, word 2 and word 3 are the offsets of the strings `bridge` and `integrator`, word 4 `referrer`, word 5 `sendingAssetId`, word 6 `receiver`, word 7 `minAmount`, word 8 `destinationChainId`, word 9 `hasSourceSwaps`, word 10 `hasDestinationCall`. The strings follow the head.
- `BridgeToNonEVMChainBytes32` / `BridgeToNonEVMChain`: topic1 `transactionId`, topic2 `destinationChainId` (LI.FI chain id, §13), data = the receiver on the non-EVM chain (`bytes32`, or `bytes` with an offset and a length).
- `AssetSwapped`: no indexed field. Word 0 `transactionId`, word 1 `dex` (the called contract), word 2 `fromAssetId`, word 3 `toAssetId`, word 4 `fromAmount`, word 5 `toAmount`, word 6 `timestamp`. The native asset is `0x0000000000000000000000000000000000000000`.
- `LiFiGenericSwapCompleted`: topic1 `transactionId`; the data holds two string offsets, then `receiver`, `fromAssetId`, `toAssetId`, `fromAmount`, `toAmount`.

`LiFiSwappedGeneric` is the deprecated predecessor of `LiFiGenericSwapCompleted`. It stays in the ABI to decode old logs.

### 1.2 Facet-specific source events

Emitter: the diamond, except `LiFiAcrossTransfer` and `CallExecutedAndFundsWithdrawn`, which the standalone AcrossFacetPackedV4 contract `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` also emits.

| topic0 | Event |
|--------|-------|
| `0xe11352fef0e24c9902a94910b5ce929151ea227f4c68572aada8f2105c66c133` | `LiFiAcrossTransfer(bytes8 _transactionId)` |
| `0xdfbe65d77c5440a078a2a1d95803d06b4a5f85b26ba3ec87bc9b421781e8dec1` | `CallExecutedAndFundsWithdrawn()` |
| `0x48a43ef17ee324c018374fc07c4daa0b29fa7f743a8b47f94df100a44988a16e` | `NEARIntentsBridgeStarted(bytes32 indexed transactionId, bytes32 indexed quoteId, address indexed depositAddress, address sendingAssetId, uint256 amount, uint256 deadline, uint256 minAmountOut, bytes32 destinationAsset)` |
| `0x58a66541dad6964200edd2115c2567d5b7d9d86a45b0df488d6506d2a41e248d` | `NEARIntentsBridgeStarted(bytes32 indexed transactionId, bytes32 indexed quoteId, address indexed depositAddress, address sendingAssetId, uint256 amount, uint256 deadline, uint256 minAmountOut)` |
| `0xf19318a6980c94fb206f1e506fa7017ed9dd61959634e8fa128a38df4e527db7` | `DlnOrderCreated(bytes32 indexed orderId)` |
| `0x324bb680d8f34b685b89431a2429f01c9b71c00ab9a18e3ad887c464200f1c5b` | `PolymerCCTPFeeSent(uint256 bridgeAmount, uint256 polymerFee, uint32 minFinalityThreshold)` |

- `LiFiAcrossTransfer` is the only LI.FI event of the packed Across calls. It carries the first 8 bytes of the `transactionId` (`bytes8(msg.data[4:12])` for the packed calldata). There is no `LiFiTransferStarted` for these calls. Link them to the Across `FundsDeposited` log in the same transaction.
- `NEARIntentsBridgeStarted` exists in two versions. The 7-field version is from NEARIntentsFacet 1.0.0 (`0xf8fA34D58A277060D07bCa7EC24D6B386d86a793` on Ethereum). The 8-field version (adds `bytes32 destinationAsset`) is from NEARIntentsFacet 3.0.0 (`0x8f00E690a45e75D7A1A765163829Ad33244a1C33`). On Ethereum the diamond switched at block 26082802 (2026-09-29 11:24:11 UTC, `DiamondCut` through the timelock). Measured on the Ethereum diamond: 7-field 395 logs and 8-field 0 logs in blocks 26072222–26082801; 7-field 0 logs and 8-field 1 log in blocks 26082803–26083052. The loupe read of 2026-09-29 shows facet 3.0.0 on all seven chains that have the facet. Index both topics.
- `DlnOrderCreated.orderId` is the deBridge DLN order id. The same order also emits the DLN source event of deBridge in the transaction.
- `PolymerCCTPFeeSent` accompanies a CCTP burn through the Polymer facet. It is a fee record, not a separate transfer.

### 1.3 Admin and security events (diamond)

| topic0 | Event |
|--------|-------|
| `0x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673` | `DiamondCut((address facetAddress, uint8 action, bytes4[] functionSelectors)[] _diamondCut, address _init, bytes _calldata)` |
| `0xed8889f560326eb138920d842192f0eb3dd22b4f139c87a2c57538e05bae1278` | `OwnershipTransferRequested(address indexed _from, address indexed _to)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |
| `0xb8fad2fa0ed7a383e747c309ef2c4391d7b65592a48893e57ccc1fab70791456` | `EmergencyPaused(address indexed msgSender)` |
| `0xf5cbf596165cc457b2cd92e8d8450827ee314968160a5696402d75766fc52caf` | `EmergencyUnpaused(address indexed msgSender)` |
| `0x706807c5bad215e3dcb9056c9bcb73bbede85a028c0256ae6ab6d04c71813360` | `EmergencyFacetRemoved(address indexed facetAddress, address indexed msgSender)` |
| `0xd97cb52d6a919c35d1a9848f69806a32611c1381fa1078e5ea866186ee4c46c7` | `ExecutionAllowed(address indexed account, bytes4 indexed method)` |
| `0x2fb75e73eca07a04ac148df401d1f013ddb4c8177a453af29c97c88037bac848` | `ExecutionDenied(address indexed account, bytes4 indexed method)` |
| `0x9207361cc2a04b9c7a06691df1eb87c6a63957ae88bf01d0d18c81e3d1272099` | `LogWithdraw(address indexed _assetAddress, address _to, uint256 amount)` |
| `0x565ec6e69c37ed7e06dad89507c35f4e77eac7390c9e25b775b6ba442d99ebbc` | `PeripheryContractRegistered(string name, address contractAddress)` |
| `0x1026451bc49d23b939d8e3c16eb4fc3ea6dd8b0be5549aa0dae6675b0083a840` | `ContractSelectorWhitelistChanged(address indexed contractAddress, bytes4 indexed selector, bool indexed whitelisted)` |

- `DiamondCut` is the upgrade signal. `action` is `0` Add, `1` Replace, `2` Remove. In production the owner timelock sends it, so a `CallExecuted` log of the timelock precedes it in the same transaction.
- `EmergencyPaused` means the pauser wallet or the owner redirected every selector to the EmergencyPauseFacet: every call to the diamond now reverts with `DiamondIsPaused()`. `EmergencyFacetRemoved` removes one facet at once, with no timelock delay.
- `LogWithdraw` is an owner withdrawal of tokens that were stranded in the diamond.
- `ExecutionAllowed` / `ExecutionDenied` change which address may call an access-controlled selector (AccessManagerFacet).
- `ContractSelectorWhitelistChanged` changes which external contract and selector the diamond may call during swaps (WhitelistManagerFacet). A new pair lets the diamond call a new DEX or bridge contract.

### 1.4 Facet configuration events (diamond)

These change the chain-id mappings or the bridge addresses that a facet uses. They move no value.

| topic0 | Event |
|--------|-------|
| `0x3e50ab2149768e79e14486591ce94dda1939b5d7247173675016b9a3c3ce45d7` | `AllBridgeChainMappingsInitialized((uint256 chainId, uint256 allBridgeChainId)[] chainIdConfigs)` |
| `0x1de6d16294a393ebbc1d9d4a6eafa8ff0bee426895d0a99924a603bb94c63f57` | `ChainIdToAllBridgeChainIdSet(uint256 indexed chainId, uint256 allBridgeChainId)` |
| `0x7e2819820559b77138a52234f500981056527217117d8bb3515c9a450465b5fc` | `ChainIdToAllBridgeChainIdUnset(uint256 indexed chainId)` |
| `0x0cd20b776bdd48fad561fb65af5b002cf62ca0e0d5e89f165a9364d9da52a21b` | `DeBridgeInitialized((uint256 chainId, uint256 deBridgeChainId)[] chainIdConfigs)` |
| `0xdc55a9203281afff9f6c3a20ab84a4858a398d4b5050c87a02ca78e573d8b34b` | `DeBridgeChainIdSet(uint256 indexed chainId, uint256 deBridgeChainId)` |
| `0xeb2fc90e92cd6872c67b476f416041c22a47406b15ba86c8542fe104d8b4c0de` | `PolymerCCTPChainMappingsInitialized((uint256 chainId, uint32 domainId)[] chainIdConfigs)` |
| `0xa475624af48483e356a270c0b6ab33a1378acdfb3aaa12f79269bcc10a078414` | `ChainIdToDomainIdSet(uint256 indexed chainId, uint32 domainId)` |
| `0x48203834611a2b212056b93cc86ada133e93a33eba2f1853158e435fc4ced32b` | `ChainIdToDomainIdUnset(uint256 indexed chainId)` |
| `0x2f773bc7e4f5bb0c3debe2a218e670f6a21dd348524a1a8657d719e30f0807ad` | `FraxChainMappingsInitialized((uint256 chainId, uint32 lzEid)[] chainIdConfigs)` |
| `0xf897cacea8c61cb020d362e093b9ede255ab740bd501c01bca26c485a33e8dcc` | `FraxChainIdToEidSet(uint256 indexed chainId, uint32 lzEid)` |
| `0xdb392b246556508e5cf7ced2aaafd17333404ffd66115f4e5f12979f2a760673` | `FraxChainIdToEidUnset(uint256 indexed chainId)` |
| `0x11540ef30f5d30a57780ceb12458f32059618a0213feb7db9e81dc752199d647` | `SupersetChainMappingsInitialized((uint256 chainId, uint32 lzEid)[] chainIdConfigs)` |
| `0x010b01c68d87c7ce7ee9bd2f5c44a9fc5058745365df809b7326827610200901` | `ChainIdToEidSet(uint256 indexed chainId, uint32 lzEid)` |
| `0xe4cb03dc27a25a069e8330089c15f40d78e36c9e7213bc181ad3bee503cdf3ea` | `MegaETHInitialized((address assetId, address bridge)[] configs)` |
| `0xf4630b7492ff2bf9c0e541238b1ba50baf1b992e27998b5d2f501e9bcdf4a37b` | `MegaETHBridgeRegistered(address indexed assetId, address bridge)` |
| `0xd192688003c02a257d1ee3ef083c31f3ba31e400ad8655bf4257081255c91568` | `OptimismInitialized((address assetId, address bridge)[] configs)` |
| `0x8ba151f3405c32cff2d4c159409e00b97b0b46fbcbe59438e7f62c1283f80638` | `OptimismBridgeRegistered(address indexed assetId, address bridge)` |

### 1.5 Destination events (not emitted by the diamond)

`ILiFi` also declares the two destination events. The Executor and the receivers emit them; see [periphery.md](periphery.md) §1.

| topic0 | Event |
|--------|-------|
| `0xb8c86983f929c6b770461983d1bbde1870408120f07123e9c12d49f35a0b4c4b` | `LiFiTransferCompleted(bytes32 indexed transactionId, address receivingAssetId, address receiver, uint256 amount, uint256 timestamp)` |
| `0x1fbfa988fd46deed0de12c94c7b5dcb537d51b804246d0083f245f7a8997d170` | `LiFiTransferRecovered(bytes32 indexed transactionId, address receivingAssetId, address receiver, uint256 amount, uint256 timestamp)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Diamond core, admin and security

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1f931c1c` | `diamondCut((address facetAddress, uint8 action, bytes4[] functionSelectors)[] _diamondCut, address _init, bytes _calldata)` | Owner only (the timelock). Emits `DiamondCut`. |
| `0x7a0ed627` | `facets()` | View: every facet and its selectors. |
| `0x52ef6b2c` | `facetAddresses()` | View. |
| `0xcdffacc6` | `facetAddress(bytes4 _functionSelector)` | View: facet of one selector. |
| `0xadfca15e` | `facetFunctionSelectors(address _facet)` | View. |
| `0x01ffc9a7` | `supportsInterface(bytes4 _interfaceId)` | View (ERC-165). |
| `0x8da5cb5b` | `owner()` | View: the LiFiTimelockController. |
| `0xf2fde38b` | `transferOwnership(address _newOwner)` | Owner only. Two-step: emits `OwnershipTransferRequested`. |
| `0x7200b829` | `confirmOwnershipTransfer()` | Pending owner only. Emits `OwnershipTransferred`. |
| `0x23452b9c` | `cancelOwnershipTransfer()` | Owner only. |
| `0xf86368ae` | `pauseDiamond()` | Pauser wallet or owner. Emits `EmergencyPaused`. |
| `0x2fc487ae` | `unpauseDiamond(address[] _blacklist)` | Owner only. Emits `EmergencyUnpaused`. |
| `0x0340e905` | `removeFacet(address _facetAddress)` | Pauser wallet or owner. Emits `EmergencyFacetRemoved`. |
| `0x5ad317a4` | `pauserWallet()` | View. |
| `0xa4c3366e` | `setCanExecute(bytes4 _selector, address _executor, bool _canExecute)` | Owner only. Emits `ExecutionAllowed` / `ExecutionDenied`. |
| `0x612ad9cb` | `addressCanExecuteMethod(bytes4 _selector, address _executor)` | View. |
| `0xd9caed12` | `withdraw(address _assetAddress, address _to, uint256 _amount)` | Owner or allowed executor. Emits `LogWithdraw`. |
| `0x1458d7ad` | `executeCallAndWithdraw(address _callTo, bytes _callData, address _assetAddress, address _to, uint256 _amount)` | Owner or allowed executor. Emits `LogWithdraw`. |
| `0x5c2ed36a` | `registerPeripheryContract(string _name, address _contractAddress)` | Owner or allowed executor. Emits `PeripheryContractRegistered`. |
| `0xa516f0f3` | `getPeripheryContract(string _name)` | View: address of a named periphery contract (for example `Executor`). |
| `0x51fed648` | `setContractSelectorWhitelist(address _contract, bytes4 _selector, bool _whitelisted)` | Owner or allowed executor. Emits `ContractSelectorWhitelistChanged`. |
| `0x1171c007` | `batchSetContractSelectorWhitelist(address[] _contracts, bytes4[] _selectors, bool _whitelisted)` | Owner or allowed executor. Emits `ContractSelectorWhitelistChanged` per pair. |
| `0x9baf00f9` | `isContractSelectorWhitelisted(address _contract, bytes4 _selector)` | View. |
| `0x00816c97` | `getAllContractSelectorPairs()` | View. |
| `0x94ddf663` | `getWhitelistedSelectorsForContract(address _contract)` | View. |

### 2.2 GenericSwapFacetV3 (same-chain swaps)

Each call emits one `AssetSwapped` per swap step and one `LiFiGenericSwapCompleted`. The `SwapData` tuple is `(address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4666fc80` | `swapTokensSingleV3ERC20ToERC20(bytes32 _transactionId, string _integrator, string _referrer, address _receiver, uint256 _minAmountOut, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit) _swapData)` | Payable: no. One swap step. |
| `0x733214a3` | `swapTokensSingleV3ERC20ToNative(bytes32 _transactionId, string _integrator, string _referrer, address _receiver, uint256 _minAmountOut, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit) _swapData)` | One swap step, native out. |
| `0xaf7060fd` | `swapTokensSingleV3NativeToERC20(bytes32 _transactionId, string _integrator, string _referrer, address _receiver, uint256 _minAmountOut, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit) _swapData)` | Payable: native in. |
| `0x5fd9ae2e` | `swapTokensMultipleV3ERC20ToERC20(bytes32 _transactionId, string _integrator, string _referrer, address _receiver, uint256 _minAmountOut, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData)` | Several swap steps. |
| `0x2c57e884` | `swapTokensMultipleV3ERC20ToNative(bytes32 _transactionId, string _integrator, string _referrer, address _receiver, uint256 _minAmountOut, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData)` | Several steps, native out. |
| `0x736eac0b` | `swapTokensMultipleV3NativeToERC20(bytes32 _transactionId, string _integrator, string _referrer, address _receiver, uint256 _minAmountOut, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData)` | Payable: native in, several steps. |

### 2.3 CalldataVerificationFacet (pure decoders)

These helpers decode LI.FI calldata. They move no value. They are useful to decode a transaction input off chain with an `eth_call`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7f99d7af` | `extractBridgeData(bytes data)` | Pure: returns the `BridgeData` of a diamond calldata. |
| `0xee0aa320` | `extractMainParameters(bytes data)` | Pure: bridge name, sending asset, receiver, amount, destination chain, flags. |
| `0x070e81f1` | `extractSwapData(bytes data)` | Pure. |
| `0x103c5200` | `extractData(bytes data)` | Pure. |
| `0xc318eeda` | `extractGenericSwapParameters(bytes data)` | Pure. |
| `0xd53482cf` | `validateCalldata(bytes data, string bridge, address sendingAssetId, address receiver, uint256 amount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall)` | Pure. |
| `0xf58ae2ce` | `validateDestinationCalldata(bytes data, bytes callTo, bytes dstCalldata)` | Pure. |

### 2.4 Bridge entry points

Every bridge facet has two entry points: `startBridgeTokensVia<Bridge>(BridgeData, <Bridge>Data)` and `swapAndStartBridgeTokensVia<Bridge>(BridgeData, SwapData[], <Bridge>Data)`. The `BridgeData` tuple is the same as in `LiFiTransferStarted`: `(bytes32 transactionId, string bridge, string integrator, address referrer, address sendingAssetId, address receiver, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall)`. [facets.md](facets.md) lists every live entry selector with the chains where it is registered.

---

## 3. Addresses — Ethereum (chain ID 1)

All checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **LiFiDiamond** | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 5,176-byte runtime. 41 facets / 150 selectors live. |
| Owner: LiFiTimelockController | `0x55117ECcC867Db72aEb25f728CCf57C3C3B4faEe` | `owner()` of the diamond. 10,254-byte contract. `getMinDelay()` = 10,800 s. |
| Pauser wallet (EOA) | `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` | `pauserWallet()` of the diamond. No code on this chain. |
| Staging diamond | `0xbEbCDb5093B47Cd7add8211E4c77B6826aF7bc5F` | LI.FI test diamond (`deployments/mainnet.staging.json`). Same events; not production. |
| AcrossFacetPackedV4 (standalone use) | `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` | Registered facet that is also called directly; emits `LiFiAcrossTransfer`. |
| Timelock executor (EOA) | `0xb05e63458a51731aad26bdcd6e12246330e6095f` | Called the timelock for both `DiamondCut` transactions of §12. No code, nonce 67. |
| Not a diamond: RobinhoodEthRecovery | `0xB477751B76CF82d00a686A1232f5fCD772414Af3` | LI.FI one-off contract (693 bytes) at the Robinhood Chain diamond's CREATE3 address on Ethereum; it sweeps ETH that users sent there by mistake. |

`0xB477751B76CF82d00a686A1232f5fCD772414Af3` (the Robinhood Chain diamond address) holds the unrelated recovery contract above on Ethereum.

## 4. Addresses — Base (chain ID 8453)

All checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **LiFiDiamond** | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 5,176-byte runtime. 34 facets / 134 selectors live. |
| Owner: LiFiTimelockController | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | `owner()` of the diamond. 10,522-byte contract. `getMinDelay()` = 10,800 s. |
| Pauser wallet (EOA) | `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` | `pauserWallet()` of the diamond. No code on this chain. |
| Staging diamond | `0x947330863B5BA5E134fE8b73e0E1c7Eed90446C7` | LI.FI test diamond (`deployments/base.staging.json`). Same events; not production. |
| AcrossFacetPackedV4 (standalone use) | `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` | Registered facet that is also called directly; emits `LiFiAcrossTransfer`. |

`0xB477751B76CF82d00a686A1232f5fCD772414Af3` (the Robinhood Chain diamond address) has no code on Base.

## 5. Addresses — Arbitrum One (chain ID 42161)

All checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **LiFiDiamond** | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 5,176-byte runtime. 33 facets / 133 selectors live. |
| Owner: LiFiTimelockController | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | `owner()` of the diamond. 10,522-byte contract. `getMinDelay()` = 10,800 s. |
| Pauser wallet (EOA) | `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` | `pauserWallet()` of the diamond. No code on this chain. |
| Staging diamond | `0xD3b2b0aC0AFdd0d166a495f5E9fca4eCc715a782` | LI.FI test diamond (`deployments/arbitrum.staging.json`). Same events; not production. |
| AcrossFacetPackedV4 (standalone use) | `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` | Registered facet that is also called directly; emits `LiFiAcrossTransfer`. |

`0xB477751B76CF82d00a686A1232f5fCD772414Af3` (the Robinhood Chain diamond address) has no code on Arbitrum.

## 6. Addresses — Optimism (chain ID 10)

All checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **LiFiDiamond** | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 5,176-byte runtime. 29 facets / 121 selectors live. |
| Owner: LiFiTimelockController | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | `owner()` of the diamond. 10,522-byte contract. `getMinDelay()` = 10,800 s. |
| Pauser wallet (EOA) | `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` | `pauserWallet()` of the diamond. No code on this chain. |
| Staging diamond | `0x2904f234CCda47206532DBb44e8fE48Dc6d177D7` | LI.FI test diamond (`deployments/optimism.staging.json`). Same events; not production. |
| AcrossFacetPackedV4 (standalone use) | `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` | Registered facet that is also called directly; emits `LiFiAcrossTransfer`. |

`0xB477751B76CF82d00a686A1232f5fCD772414Af3` (the Robinhood Chain diamond address) has no code on Optimism.

## 7. Addresses — Polygon PoS (chain ID 137)

All checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **LiFiDiamond** | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 5,176-byte runtime. 30 facets / 122 selectors live. |
| Owner: LiFiTimelockController | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | `owner()` of the diamond. 10,522-byte contract. `getMinDelay()` = 10,800 s. |
| Pauser wallet (EOA) | `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` | `pauserWallet()` of the diamond. No code on this chain. |
| Staging diamond | `0xA235CD94f8B1e2DBc0A9Cb4Cd20d4C921604dfAa` | LI.FI test diamond (`deployments/polygon.staging.json`). Same events; not production. |
| AcrossFacetPackedV4 (standalone use) | `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` | Registered facet that is also called directly; emits `LiFiAcrossTransfer`. |

`0xB477751B76CF82d00a686A1232f5fCD772414Af3` (the Robinhood Chain diamond address) has no code on Polygon.

## 8. Addresses — BNB Smart Chain (chain ID 56)

All checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **LiFiDiamond** | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 5,176-byte runtime. 30 facets / 115 selectors live. |
| Owner: LiFiTimelockController | `0x55117ECcC867Db72aEb25f728CCf57C3C3B4faEe` | `owner()` of the diamond. 10,254-byte contract. `getMinDelay()` = 10,800 s. |
| Pauser wallet (EOA) | `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` | `pauserWallet()` of the diamond. No code on this chain. |
| Staging diamond | `0x2904f234CCda47206532DBb44e8fE48Dc6d177D7` | LI.FI test diamond (`deployments/bsc.staging.json`). Same events; not production. |
| AcrossFacetPackedV4 (standalone use) | `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` | Registered facet that is also called directly; emits `LiFiAcrossTransfer`. |

`0xB477751B76CF82d00a686A1232f5fCD772414Af3` (the Robinhood Chain diamond address) has no code on BNB.

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

All checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **LiFiDiamond** | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 5,176-byte runtime. 26 facets / 105 selectors live. |
| Owner: LiFiTimelockController | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | `owner()` of the diamond. 10,522-byte contract. `getMinDelay()` = 10,800 s. |
| Pauser wallet (EOA) | `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` | `pauserWallet()` of the diamond. No code on this chain. |

`0xB477751B76CF82d00a686A1232f5fCD772414Af3` (the Robinhood Chain diamond address) has no code on Avalanche.

## 10. Addresses — Robinhood Chain (chain ID 4663)

All checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **LiFiDiamond** | `0xB477751B76CF82d00a686A1232f5fCD772414Af3` | 254-byte runtime: a compact diamond fallback (solc 0.8.29) that reads the standard diamond storage slot `0xc8fcad8db84d3cc18b4c41d551ea0ee66dd599cde068d998e57d5e09332c131c`. 19 facets / 68 selectors live. |
| Owner: LiFiTimelockController | `0x6E9Beb6997dAE04122f1f8f8980f3dc8225443F3` | `owner()` of the diamond. 10,254-byte contract. `getMinDelay()` = 10,800 s. |
| Pauser wallet (EOA) | `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` | `pauserWallet()` of the diamond. No code on this chain. |

`0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` has no code on Robinhood Chain (nonce 0). No staging diamond and no AcrossFacetPackedV4 is deployed there; the Across route uses AcrossFacetV4 only.

## 10a. Addresses — Arc (chain ID 5042)

All checked with `eth_getCode` on 2026-10-05. Source: `deployments/arc.json` and the LI.FI API (`GET https://li.quest/v1/chains`, key `arc`, `diamondAddress`).

| Role | Address | One-liner |
|------|---------|-----------|
| **LiFiDiamond** | `0xA4072583658Fae592A3506A42431cb6316a8d40b` | 254-byte runtime, the same compact diamond fallback as on Robinhood Chain. 19 facets / 71 selectors live. |
| Owner: LiFiTimelockController | `0x50Ad2949DBCF80B4019fA9cA01Cc38AB7cE2ED8C` | `owner()` of the diamond. 10,254-byte contract. `getMinDelay()` = 10,800 s. |
| Pauser wallet (EOA) | `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` | `pauserWallet()` of the diamond. |

`0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE`, `0xB477751B76CF82d00a686A1232f5fCD772414Af3` and AcrossFacetPackedV4 `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` have no code on Arc. No staging diamond is listed for Arc. In blocks 24,335,947–24,375,947 (2026-10-05 04:48–10:26 UTC) the Arc diamond emitted 133 `LiFiTransferStarted`, 301 `AssetSwapped`, 186 `LiFiGenericSwapCompleted`, 10 `PolymerCCTPFeeSent` and 1 `BridgeToNonEVMChainBytes32`.

---

## 11. Cross-chain summary

| Chain | ID | LiFiDiamond | Owner (timelock) | Facets / selectors | Staging diamond |
|-------|----|-------------|------------------|--------------------|-----------------|
| Ethereum | 1 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x55117ECcC867Db72aEb25f728CCf57C3C3B4faEe` | 41 / 150 | `0xbEbCDb5093B47Cd7add8211E4c77B6826aF7bc5F` |
| Base | 8453 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | 34 / 134 | `0x947330863B5BA5E134fE8b73e0E1c7Eed90446C7` |
| Arbitrum One | 42161 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | 33 / 133 | `0xD3b2b0aC0AFdd0d166a495f5E9fca4eCc715a782` |
| Optimism | 10 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | 29 / 121 | `0x2904f234CCda47206532DBb44e8fE48Dc6d177D7` |
| Polygon PoS | 137 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | 30 / 122 | `0xA235CD94f8B1e2DBc0A9Cb4Cd20d4C921604dfAa` |
| BNB Smart Chain | 56 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x55117ECcC867Db72aEb25f728CCf57C3C3B4faEe` | 30 / 115 | `0x2904f234CCda47206532DBb44e8fE48Dc6d177D7` |
| Avalanche C-Chain | 43114 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | 26 / 105 | — |
| Robinhood Chain | 4663 | `0xB477751B76CF82d00a686A1232f5fCD772414Af3` | `0x6E9Beb6997dAE04122f1f8f8980f3dc8225443F3` | 19 / 68 | — |
| Arc | 5042 | `0xA4072583658Fae592A3506A42431cb6316a8d40b` | `0x50Ad2949DBCF80B4019fA9cA01Cc38AB7cE2ED8C` | 19 / 71 | — |

The diamond address `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` is shared by seven chains. Its runtime is 5,176 bytes on each; the code hash is identical on six chains and differs on Base. The facet sets differ per chain (§0). **Robinhood Chain uses its own diamond `0xB477751B76CF82d00a686A1232f5fCD772414Af3`**, which is listed in `deployments/robinhood.json` and which emitted the LI.FI events on that chain in the pinned window (§15). **Arc uses its own diamond `0xA4072583658Fae592A3506A42431cb6316a8d40b`** (`deployments/arc.json`, §10a). The staging diamonds emit the same topics as production; exclude them by emitter.

---

## 12. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **LiFiDiamond** (all 9) | EIP-2535 diamond | `facets()` (`0x7a0ed627`) returns the facet table; the EIP-1967 implementation slot is empty. Watch `DiamondCut` (topic0 `0x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673`). | `owner()` = LiFiTimelockController: proposals wait at least 10,800 s, then an executor runs them. `pauserWallet()` can `pauseDiamond()` / `removeFacet()` at once; only the owner can `unpauseDiamond()`. |
| **LiFiTimelockController** | Not a proxy (OpenZeppelin `TimelockController`) | Plain contract; `getMinDelay()` (`0xf27a0c92`) = `0x2a30` (10,800) on all nine chains. | Its own roles (`RoleGranted` / `RoleRevoked`, [periphery.md](periphery.md) §1). `updateDelay` goes through the timelock itself. |
| Facets | Plain contracts | Code only runs through `DELEGATECALL` from the diamond. | Replaced by `diamondCut`. |

Upgrade history seen in this work: Ethereum block 26052901 (2026-09-25 07:13:47 UTC) added the CentrifugeFacet (`0x6275c64C1DA8919D1F7F5D558D36A6D750C74838`, selectors `0x0315138f`, `0x8fd4d4dd`). Ethereum block 26082802 (2026-09-29 11:24:11 UTC) replaced the NEARIntentsFacet with version 3.0.0. Both cuts were sent by the timelock `0x55117ECcC867Db72aEb25f728CCf57C3C3B4faEe`, called by `0xb05e63458a51731aad26bdcd6e12246330e6095f` (no code, nonce 67: an EOA executor).

---

## 13. Detection invariants & gotchas

1. **Source leg = `LiFiTransferStarted` at the diamond.** Pair it with the underlying bridge event in the same transaction for the bridge's own id (Across `depositId`, Stargate `guid`, CCTP `nonce`, deBridge `orderId`, Relay `orderId`, NEAR Intents `quoteId`). The `bridge` string names the route (for example `across`, `relaydepository`, `mayan`, `near`, `stargateV2`, `glacis`, `gasZipBridge`).
2. **`transactionId` is the LI.FI link key.** It is on chain on the source side in every LI.FI event of the route. It is on chain on the destination side only when the route has a destination call (Executor `LiFiTransferCompleted`, receiver `LiFiTransferRecovered`). For plain bridging, the destination leg carries only the underlying bridge's id; the LI.FI API (`GET https://li.quest/v1/status?txHash=`) links the sending and receiving transactions off chain.
3. **The value is not in the event you expect.** `minAmount` is the amount after source swaps and fees that the facet hands to the bridge. The user's input is the ERC-20 `Transfer` from the user (or from Permit2Proxy) to the diamond, or `msg.value`. Fees go to FeeCollector or FeeForwarder in the same transaction.
4. **Non-EVM destinations.** `receiver` is then `0x11f111f111f111F111f111f111F111f111f111F1` (`NON_EVM_ADDRESS`) and the real receiver is in `BridgeToNonEVMChainBytes32` / `BridgeToNonEVMChain` with the same `transactionId`, in the same transaction. Only facets that support non-EVM receivers emit these events. The Relay depository route and the THORChain route emit none: the destination address is then only in the underlying bridge's data (the Relay order, the THORChain memo).
5. **LI.FI chain ids.** `destinationChainId` is the EVM chain id for EVM chains (for example 1, 8453, 42161, 10, 137, 56, 43114, 4663 and 5042). For other chains LI.FI uses its own ids: Solana `1151111081099710`, Bitcoin `20000000000001`, Bitcoin Cash `20000000000002`, Litecoin `20000000000003`, Dogecoin `20000000000004`, Sui `9270000000000000`, Aptos `9271000000000010`, Tron `1885080386571452`, Stellar `1201081091099710`, HyperCore `1337` (`src/Helpers/LiFiData.sol`).
6. **`AssetSwapped` is not always a swap.** The fee step is recorded as an `AssetSwapped` whose `dex` is the FeeForwarder or the FeeCollector and whose `fromAssetId` equals `toAssetId`. Exclude those rows from swap volume.
7. **Other contracts emit the same topics.** LI.FI staging diamonds (§11) emit the full event set. LI.FI-derived diamonds of other aggregators also emit `AssetSwapped` (for example RubicMultiProxy `0x6AA981bFF95eDfea36Bdae98C26B274FfcafE8d3` on Ethereum, measured as an `AssetSwapped` emitter in the pinned window). Always filter by the diamond address.
8. **Packed Across calls bypass the diamond.** The AcrossFacetPackedV4 contract `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` is registered in the diamond and is also called directly. In the pinned window most `LiFiAcrossTransfer` logs came from that address, not from the diamond (§15). A monitor that keys only on the diamond misses them.
9. **`tx.from` and `tx.to` are often not the user.** Calls arrive through smart wallets (ERC-4337 EntryPoint), through Permit2Proxy (gasless, the signer is the user), and through integrator contracts. Attribute by the token `Transfer` into the diamond and by `receiver` in `LiFiTransferStarted`.
10. **`integrator` names the front end.** The `integrator` string of `LiFiTransferStarted` identifies the app (for example `jumper.exchange`); filter on it when needed.
11. **Two `NEARIntentsBridgeStarted` topics.** See §1.2. A monitor keyed on the 7-field topic stopped matching at the facet upgrade of 2026-09-29.
12. **Admin triggers.** Alert on `DiamondCut`, `EmergencyPaused`, `EmergencyFacetRemoved`, `EmergencyUnpaused`, `OwnershipTransferRequested`, `OwnershipTransferred`, `ExecutionAllowed`, `ContractSelectorWhitelistChanged` at the diamond, and on `CallScheduled` / `MinDelayChange` / `RoleGranted` at the timelock ([periphery.md](periphery.md)). A `CallScheduled` whose data starts with `0x1f931c1c` is a pending `diamondCut` with at least 3 hours of notice.

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Diamond topics (chain-agnostic) =====
TOPIC_LIFI_TRANSFER_STARTED        = '\xcba69f43792f9f399347222505213b55af8e0b0b54b893085c2e27ecbe1644f1'
TOPIC_BRIDGE_TO_NON_EVM_BYTES32    = '\x815cd8dc72093a13fe3577112c391b6279303956526382ab98772d0239dbf78c'
TOPIC_BRIDGE_TO_NON_EVM            = '\xf9b69f466270c99522169d563c0a430e88c52865ec33b1cc36ee2a4a6ea5170b'
TOPIC_ASSET_SWAPPED                = '\x7bfdfdb5e3a3776976e53cb0607060f54c5312701c8cba1155cc4d5394440b38'
TOPIC_LIFI_GENERIC_SWAP_COMPLETED  = '\x38eee76fd911eabac79da7af16053e809be0e12c8637f156e77e1af309b99537'
TOPIC_LIFI_SWAPPED_GENERIC_OLD     = '\x93517b7c6f32856737008edf37cf2542b55d27d83fa299aa216f55a982a6ee1d'
TOPIC_LIFI_ACROSS_TRANSFER         = '\xe11352fef0e24c9902a94910b5ce929151ea227f4c68572aada8f2105c66c133'
TOPIC_NEAR_INTENTS_STARTED_V3      = '\x48a43ef17ee324c018374fc07c4daa0b29fa7f743a8b47f94df100a44988a16e'
TOPIC_NEAR_INTENTS_STARTED_V1      = '\x58a66541dad6964200edd2115c2567d5b7d9d86a45b0df488d6506d2a41e248d'
TOPIC_DLN_ORDER_CREATED            = '\xf19318a6980c94fb206f1e506fa7017ed9dd61959634e8fa128a38df4e527db7'
TOPIC_POLYMER_CCTP_FEE_SENT        = '\x324bb680d8f34b685b89431a2429f01c9b71c00ab9a18e3ad887c464200f1c5b'
TOPIC_LIFI_TRANSFER_COMPLETED      = '\xb8c86983f929c6b770461983d1bbde1870408120f07123e9c12d49f35a0b4c4b'
TOPIC_LIFI_TRANSFER_RECOVERED      = '\x1fbfa988fd46deed0de12c94c7b5dcb537d51b804246d0083f245f7a8997d170'
-- admin / security
TOPIC_DIAMOND_CUT                  = '\x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673'
TOPIC_OWNERSHIP_TRANSFER_REQUESTED = '\xed8889f560326eb138920d842192f0eb3dd22b4f139c87a2c57538e05bae1278'
TOPIC_OWNERSHIP_TRANSFERRED        = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_EMERGENCY_PAUSED             = '\xb8fad2fa0ed7a383e747c309ef2c4391d7b65592a48893e57ccc1fab70791456'
TOPIC_EMERGENCY_UNPAUSED           = '\xf5cbf596165cc457b2cd92e8d8450827ee314968160a5696402d75766fc52caf'
TOPIC_EMERGENCY_FACET_REMOVED      = '\x706807c5bad215e3dcb9056c9bcb73bbede85a028c0256ae6ab6d04c71813360'
TOPIC_EXECUTION_ALLOWED            = '\xd97cb52d6a919c35d1a9848f69806a32611c1381fa1078e5ea866186ee4c46c7'
TOPIC_EXECUTION_DENIED             = '\x2fb75e73eca07a04ac148df401d1f013ddb4c8177a453af29c97c88037bac848'
TOPIC_LOG_WITHDRAW                 = '\x9207361cc2a04b9c7a06691df1eb87c6a63957ae88bf01d0d18c81e3d1272099'
TOPIC_PERIPHERY_REGISTERED         = '\x565ec6e69c37ed7e06dad89507c35f4e77eac7390c9e25b775b6ba442d99ebbc'
TOPIC_SELECTOR_WHITELIST_CHANGED   = '\x1026451bc49d23b939d8e3c16eb4fc3ea6dd8b0be5549aa0dae6675b0083a840'

-- ===== Selectors (chain-agnostic) =====
SEL_DIAMOND_CUT                    = '\x1f931c1c'
SEL_FACETS                         = '\x7a0ed627'
SEL_FACET_ADDRESS                  = '\xcdffacc6'
SEL_OWNER                          = '\x8da5cb5b'
SEL_TRANSFER_OWNERSHIP             = '\xf2fde38b'
SEL_CONFIRM_OWNERSHIP_TRANSFER     = '\x7200b829'
SEL_PAUSE_DIAMOND                  = '\xf86368ae'
SEL_UNPAUSE_DIAMOND                = '\x2fc487ae'
SEL_REMOVE_FACET                   = '\x0340e905'
SEL_PAUSER_WALLET                  = '\x5ad317a4'
SEL_WITHDRAW                       = '\xd9caed12'
SEL_EXECUTE_CALL_AND_WITHDRAW      = '\x1458d7ad'
SEL_SET_CAN_EXECUTE                = '\xa4c3366e'
SEL_REGISTER_PERIPHERY             = '\x5c2ed36a'
SEL_GET_PERIPHERY                  = '\xa516f0f3'
SEL_SET_SELECTOR_WHITELIST         = '\x51fed648'
SEL_BATCH_SET_SELECTOR_WHITELIST   = '\x1171c007'
SEL_SWAP_SINGLE_ERC20_TO_ERC20     = '\x4666fc80'
SEL_SWAP_SINGLE_ERC20_TO_NATIVE    = '\x733214a3'
SEL_SWAP_SINGLE_NATIVE_TO_ERC20    = '\xaf7060fd'
SEL_SWAP_MULTI_ERC20_TO_ERC20      = '\x5fd9ae2e'
SEL_SWAP_MULTI_ERC20_TO_NATIVE     = '\x2c57e884'
SEL_SWAP_MULTI_NATIVE_TO_ERC20     = '\x736eac0b'
SEL_EXTRACT_BRIDGE_DATA            = '\x7f99d7af'

-- ===== Addresses (network-specific) =====
ETH_LIFI_DIAMOND                   = '\x1231deb6f5749ef6ce6943a275a1d3e7486f4eae'
ETH_LIFI_TIMELOCK                  = '\x55117eccc867db72aeb25f728ccf57c3c3b4faee'
ETH_LIFI_PAUSER_EOA                = '\xf9d8ba34a51750cf6abfa9de7acd37f182081a4a'
ETH_LIFI_STAGING_DIAMOND           = '\xbebcdb5093b47cd7add8211e4c77b6826af7bc5f'
ETH_LIFI_ACROSS_PACKED_V4          = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
BASE_LIFI_DIAMOND                  = '\x1231deb6f5749ef6ce6943a275a1d3e7486f4eae'
BASE_LIFI_TIMELOCK                 = '\x5604a94a3438c3074efff803fab14b7244fe4e29'
BASE_LIFI_PAUSER_EOA               = '\xf9d8ba34a51750cf6abfa9de7acd37f182081a4a'
BASE_LIFI_STAGING_DIAMOND          = '\x947330863b5ba5e134fe8b73e0e1c7eed90446c7'
BASE_LIFI_ACROSS_PACKED_V4         = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
ARB_LIFI_DIAMOND                   = '\x1231deb6f5749ef6ce6943a275a1d3e7486f4eae'
ARB_LIFI_TIMELOCK                  = '\x5604a94a3438c3074efff803fab14b7244fe4e29'
ARB_LIFI_PAUSER_EOA                = '\xf9d8ba34a51750cf6abfa9de7acd37f182081a4a'
ARB_LIFI_STAGING_DIAMOND           = '\xd3b2b0ac0afdd0d166a495f5e9fca4ecc715a782'
ARB_LIFI_ACROSS_PACKED_V4          = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
OP_LIFI_DIAMOND                    = '\x1231deb6f5749ef6ce6943a275a1d3e7486f4eae'
OP_LIFI_TIMELOCK                   = '\x5604a94a3438c3074efff803fab14b7244fe4e29'
OP_LIFI_PAUSER_EOA                 = '\xf9d8ba34a51750cf6abfa9de7acd37f182081a4a'
OP_LIFI_STAGING_DIAMOND            = '\x2904f234ccda47206532dbb44e8fe48dc6d177d7'
OP_LIFI_ACROSS_PACKED_V4           = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
POLY_LIFI_DIAMOND                  = '\x1231deb6f5749ef6ce6943a275a1d3e7486f4eae'
POLY_LIFI_TIMELOCK                 = '\x5604a94a3438c3074efff803fab14b7244fe4e29'
POLY_LIFI_PAUSER_EOA               = '\xf9d8ba34a51750cf6abfa9de7acd37f182081a4a'
POLY_LIFI_STAGING_DIAMOND          = '\xa235cd94f8b1e2dbc0a9cb4cd20d4c921604dfaa'
POLY_LIFI_ACROSS_PACKED_V4         = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
BNB_LIFI_DIAMOND                   = '\x1231deb6f5749ef6ce6943a275a1d3e7486f4eae'
BNB_LIFI_TIMELOCK                  = '\x55117eccc867db72aeb25f728ccf57c3c3b4faee'
BNB_LIFI_PAUSER_EOA                = '\xf9d8ba34a51750cf6abfa9de7acd37f182081a4a'
BNB_LIFI_STAGING_DIAMOND           = '\x2904f234ccda47206532dbb44e8fe48dc6d177d7'
BNB_LIFI_ACROSS_PACKED_V4          = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
AVAX_LIFI_DIAMOND                  = '\x1231deb6f5749ef6ce6943a275a1d3e7486f4eae'
AVAX_LIFI_TIMELOCK                 = '\x5604a94a3438c3074efff803fab14b7244fe4e29'
AVAX_LIFI_PAUSER_EOA               = '\xf9d8ba34a51750cf6abfa9de7acd37f182081a4a'
RH_LIFI_DIAMOND                    = '\xb477751b76cf82d00a686a1232f5fcd772414af3'
RH_LIFI_TIMELOCK                   = '\x6e9beb6997dae04122f1f8f8980f3dc8225443f3'
RH_LIFI_PAUSER_EOA                 = '\xf9d8ba34a51750cf6abfa9de7acd37f182081a4a'
ARC_LIFI_DIAMOND                   = '\xa4072583658fae592a3506a42431cb6316a8d40b'
ARC_LIFI_TIMELOCK                  = '\x50ad2949dbcf80b4019fa9ca01cc38ab7ce2ed8c'
ARC_LIFI_PAUSER_EOA                = '\xf9d8ba34a51750cf6abfa9de7acd37f182081a4a'
ETH_LIFI_TIMELOCK_EXECUTOR_EOA     = '\xb05e63458a51731aad26bdcd6e12246330e6095f'
ETH_ROBINHOOD_ETH_RECOVERY         = '\xb477751b76cf82d00a686a1232f5fcd772414af3'   -- not a diamond
```

---

## 15. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` / `[0:4]` from the verified ABIs of the live facets (explorer-verified source of the exact deployed facet) and cross-checked against `lifinance/contracts` `src/Interfaces/ILiFi.sol`, `src/Libraries/LibSwap.sol`, `src/Libraries/LibDiamond.sol` and `src/Facets/*.sol`. The loupe call `facets()` on every diamond returned Ethereum 41 facets / 150 selectors, Base 34 facets / 134 selectors, Arbitrum 33 facets / 133 selectors, Optimism 29 facets / 121 selectors, Polygon 30 facets / 122 selectors, BNB 30 facets / 115 selectors, Avalanche 26 facets / 105 selectors, Robinhood Chain 19 facets / 68 selectors; each live selector matched a verified ABI of a facet with the same name, and one Robinhood Chain selector (`extractNonEVMAddress(bytes)`, `0xdf1c3a5b`) matched the repository source of CalldataVerificationFacet 1.3.1.
- **Addresses:** from `deployments/<network>.json` and `deployments/<network>.diamond.json` for `mainnet`, `base`, `arbitrum`, `optimism`, `polygon`, `bsc`, `avalanche` and `robinhood`, and existence-checked with `eth_getCode`. The diamond runtime code is 5,176 bytes on the seven shared-address chains (one code hash on six chains, another on Base) and 254 bytes on Robinhood Chain. `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` has no code (nonce 0) on Robinhood Chain.
- **Arc (2026-10-05):** `deployments/arc.json` and `li.quest/v1/chains` give the diamond `0xA4072583658Fae592A3506A42431cb6316a8d40b`; `eth_getCode` = 254 bytes; `facets()` = 19 facets / 71 selectors, every facet address matching `deployments/arc.diamond.json`; `owner()` = the timelock `0x50Ad2949DBCF80B4019fA9cA01Cc38AB7cE2ED8C` (`getMinDelay()` = 10,800); `pauserWallet()` = `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a`. Activity from `eth_getLogs` (§10a).
- **Owner and pauser:** `owner()` and `pauserWallet()` read with `eth_call` on each diamond (§3–§10); `getMinDelay()` read on the timelocks of all eight chains.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, logs counted per emitter):**

  Logs emitted by the diamond (address-wide `eth_getLogs` scan of the diamond, every topic0 counted):

  | Event | ETH | Base | Arb | OP | Poly | BNB | Avax | RH |
  |---|---|---|---|---|---|---|---|---|
  | `LiFiTransferStarted` | 2,621 | 3,258 | 1,639 | 431 | 653 | 3,034 | 214 | 3,139 |
  | `BridgeToNonEVMChainBytes32` | 311 | 287 | 101 | 6 | 46 | 113 | 9 | 27 |
  | `BridgeToNonEVMChain` | 5 | 3 | 10 | 0 | 1 | 0 | 0 | 0 |
  | `AssetSwapped` | 4,606 | 18,141 | 3,146 | 995 | 1,253 | 11,220 | 418 | 11,292 |
  | `LiFiGenericSwapCompleted` | 1,309 | 7,690 | 861 | 344 | 251 | 6,731 | 101 | 6,051 |
  | `LiFiAcrossTransfer` | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
  | `NEARIntentsBridgeStarted (7 fields)` | 130 | 133 | 70 | 10 | 39 | 18 | 34 | 0 |
  | `NEARIntentsBridgeStarted (8 fields)` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | `PolymerCCTPFeeSent` | 42 | 209 | 82 | 26 | 54 | 0 | 26 | 0 |
  | `DlnOrderCreated` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | `DiamondCut` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | `EmergencyPaused` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

  Other emitters of the same topics (topic scans from any emitter in the same window):
  - `LiFiAcrossTransfer`: Ethereum 6 (6 standalone AcrossFacetPackedV4); Base 30 (29 standalone AcrossFacetPackedV4, 1 diamond); Arbitrum 26 (25 standalone AcrossFacetPackedV4, 1 diamond); Optimism 9 (8 standalone AcrossFacetPackedV4, 1 diamond); Polygon 0; BNB 0; Avalanche 0; Robinhood Chain 0.
  - `AssetSwapped`: Ethereum 4,656 (4,606 diamond, 49 RubicMultiProxy, 1 Executor); Base 18,230 (18,141 diamond, 87 Executor, 2 RubicMultiProxy); Arbitrum 3,157 (3,146 diamond, 11 Executor); Optimism 997 (995 diamond, 2 Executor); Polygon 1,263 (1,253 diamond, 9 Executor, 1 RubicMultiProxy); BNB 11,702 (11,220 diamond, 479 Executor, 3 RubicMultiProxy); Avalanche 418 (418 diamond); Robinhood Chain 11,592 (11,292 diamond, 298 Executor, 2 `0x099Cf17C8fA5C1c0E3B8cd2367819240E7680413`).
  - `LiFiTransferStarted`: Ethereum 2,621 (2,621 diamond); Base 3,258 (3,258 diamond); Arbitrum 1,640 (1,639 diamond, 1 staging diamond); Optimism 431 (431 diamond); Polygon 653 (653 diamond); BNB 3,034 (3,034 diamond); Avalanche 214 (214 diamond); Robinhood Chain 3,139 (3,139 diamond).
  - `NEARIntentsBridgeStarted (8 fields)`: Ethereum 0; Base 0; Arbitrum 1 (1 staging diamond); Optimism 0; Polygon 0; BNB 0; Avalanche 0; Robinhood Chain 0.
- **Sample transactions read:** Ethereum `0x042c389d0c6bd1f2ab8d70c584bc9ef3ca5634de33880e8c01c38980e49cdef9` (`swapAndStartBridgeTokensViaMayan`: wstETH `Transfer` user → diamond, two fee transfers and `FeesForwarded`, a fee-step `AssetSwapped`, a wstETH → WETH `AssetSwapped`, WETH diamond → Mayan, `BridgeToNonEVMChainBytes32` and `LiFiTransferStarted` with `bridge` = `mayan`, `receiver` = `NON_EVM_ADDRESS`, `destinationChainId` = 1151111081099710 (Solana)); Base `0x86582b3134abe4c79594f622b19aad50f168f11e84f148cf43335df58e29cd32` (a smart-wallet call through the ERC-4337 EntryPoint; USDC `Transfer` wallet → diamond, swaps, WETH diamond → Relay depository `0x4cD00E387622C35bDDB9b4c962C136462338BC31`, `LiFiTransferStarted`); Base `0x876ae4fdcfd38cb14554bf8314405aa6663aca526facf8c823a690ccf6133ab2` (`LiFiAcrossTransfer` from the standalone AcrossFacetPackedV4 next to the Across `FundsDeposited`); Robinhood Chain `0x70316fa91a7cf955a3aeee71645536dc5604256ec876b058aa9db348eedd9a52` (native ETH in `msg.value` to `0xB477751B76CF82d00a686A1232f5fCD772414Af3`, `FeesForwarded`, `LiFiTransferStarted` with `bridge` = `relaydepository`, `destinationChainId` = 1); Ethereum `0x6f12f5b728e4338b03afc3923611a8e17d2858b7ca24e1cb654f31eeb6722a5b` and `0x70a91050da17a645cf2a2759b6a60acb6473ea43c604cda981f45b0dc7ef5c1c` (the two `DiamondCut` transactions of §12).

Authoritative sources:
- Canonical repository — [lifinance/contracts](https://github.com/lifinance/contracts) (`deployments/`, `src/LiFiDiamond.sol`, `src/Interfaces/ILiFi.sol`, `src/Libraries/LibSwap.sol`, `src/Facets/`, `src/Security/LiFiTimelockController.sol`, `src/Helpers/LiFiData.sol`)
- Docs — [LI.FI smart contract addresses](https://docs.li.fi/introduction/lifi-architecture/smart-contract-addresses) · [status tracking](https://docs.li.fi/introduction/user-flows-and-examples/status-tracking) · [docs index](https://docs.li.fi/llms.txt)
- Explorers (verified sources and ABIs) — [Etherscan diamond](https://etherscan.io/address/0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae) · [Blockscout Ethereum](https://eth.blockscout.com/address/0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE) · [Basescan diamond](https://basescan.org/address/0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae) · [Robinhood Chain Blockscout diamond](https://robinhoodchain.blockscout.com/address/0xB477751B76CF82d00a686A1232f5fCD772414Af3)
