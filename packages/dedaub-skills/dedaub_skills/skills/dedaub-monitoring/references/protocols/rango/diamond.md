# RangoDiamond — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain + Arc)

**Status:** verified on 2026-09-29 against live RPC on the eight original chains (Arc added on 2026-10-05 with the same checks), `rango-exchange/rango-contracts-v2` (`contracts/rango/RangoDiamond.sol`, `contracts/facets/`, `contracts/libraries/LibSwapper*.sol`, `contracts/interfaces/IRango*.sol`), the Rango docs (architecture, deployment addresses) and the explorer-verified sources of the live facets. The facet table of every diamond was read with `facets()`, and every live selector was matched to a verified facet ABI or to the repository source. Topics and selectors recomputed as `keccak256(signature)`; addresses existence-checked with `eth_getCode`.
**Scope:** the RangoDiamond (EIP-2535) at `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` on all nine chains: its source-leg and swap events, its per-bridge events, its admin events, the entry selectors of every live facet, and its owner and facet set per chain. The destination middlewares are in [middlewares.md](middlewares.md). Topics and selectors are chain-agnostic; addresses are network-specific.

The user calls the diamond. A bridge facet takes the user's tokens (ERC-20 `Transfer` user → diamond, or native `msg.value`), pays fees (`FeeInfo`, `SendToken` to the fee receivers), runs optional swaps (`CallResult`, `RangoSwap`), and calls the underlying bridge in the same transaction. The diamond then emits `RangoBridgeInitiated`, the source-leg record of the route. All facet events come from the diamond address (facets run by `DELEGATECALL`).

Three facts to know before indexing:

1. **Same address on all nine chains, one runtime code (5,208 bytes), a different owner per chain, and a different facet set per chain** (§3–§12). Robinhood Chain and Arc have only 7 facets (the same seven facet addresses).
2. **`RangoBridgeInitiated` indexes `requestId`, `bridgeId` and `dAppTag`.** `bridgeId` names the bridge only for values 0–23 (`IRango.BridgeType`); the `genericBridge` facet takes any `bridgeId` from the API (measured: 51–60).
3. **There is no diamond event on the destination chain.** Routes with an interchain message end at a middleware with `RangoBridgeCompleted` (same `requestId`); other routes end with the bridge's own payout.

---

## 0. Contract families & versions

| Contract | Chains | Role | Upgradeable? |
|----------|--------|------|--------------|
| **RangoDiamond** `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | all 9 | Entry point; emits every facet event. | Yes: `diamondCut`, owner only (EIP-2535, not EIP-1967). |
| Core facets (DiamondCut, DiamondLoupe, Ownership, RangoAccessManager) | all 9 | Upgrade, introspection, ownership, whitelist of DEX / bridge targets and pause. | Replaced by `diamondCut`. |
| RangoSwapperFacet | all 9 | Same-chain swaps (`onChainSwaps`), refunds, fee receiver. | Replaced by `diamondCut`. |
| RangoGenericBridgeFacet | all 9 | `genericBridge`: runs whitelisted calls to any bridge target; `bridgeId` comes from the request. | Replaced by `diamondCut`. |
| Bridge facets | per chain | Across, AllBridge, Arbitrum bridge, cBridge, CCTP, ChainFlip, Connext, deBridge, Hyphen, Multichain, Nitro, Optimism bridge, Orbiter, Poly, Satellite (Axelar), Stargate, Stargate V2, Swft, Symbiosis, Synapse, THORChain, Voyager, Wormhole, YBridge. | Replaced by `diamondCut`. |

Facets live on 2026-09-29 (loupe `facets()`): Ethereum 42 / 152, Base 26 / 105, Arbitrum 38 / 141, Optimism 36 / 135, Polygon 36 / 135, BNB 36 / 126, Avalanche 34 / 116, Robinhood Chain 7 / 34, Arc 7 / 34 (2026-10-05) (facets / selectors).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Source-leg, swap and fee events (diamond)

| topic0 | Event |
|--------|-------|
| `0x012c155f3836c4edb9222305b909a109f9efa46288efffe40a0e66da3a9a9800` | `RangoBridgeInitiated(address indexed requestId, address bridgeToken, uint256 bridgeAmount, address receiver, uint256 destinationChainId, bool hasInterchainMessage, bool hasDestinationSwap, uint8 indexed bridgeId, uint16 indexed dAppTag, string dAppName)` |
| `0xa551f5e7134cc110651fa6eb8a0423535b3ea90eedb01463af70e6798a75d426` | `RangoBridgeInitiated(address indexed requestId, address bridgeToken, uint256 bridgeAmount, address receiver, uint256 destinationChainId, bool hasInterchainMessage, bool hasDestinationSwap, uint8 indexed bridgeId, uint16 indexed dAppTag)` |
| `0x0e9201911743fd4d03e146f00ad23945dc8f3ffc200906eff25179a52b726f17` | `RangoSwap(address indexed requestId, address fromToken, address toToken, uint256 amountIn, uint256 minimumAmountExpected, uint16 indexed dAppTag, uint256 outputAmount, address receiver, string dAppName)` |
| `0xdf4363408b2d9811d1e5c23efdb5bae0b7a68bd9de2de1cbae18a11be3e67ef5` | `SendToken(address _token, uint256 _amount, address _receiver)` |
| `0x2fc0d44e6ef6b3e7707cacd3cc326511198c3d1598c65dd54be5a9e37ce02f12` | `CallResult(address target, bool success, bytes returnData)` |
| `0xf14fbd8b6e3ad3ae34babfa1f3b6a099f57643662f4cfc24eb335ae8718f534b` | `FeeInfo(address token, address indexed affiliatorAddress, uint256 platformFee, uint256 destinationExecutorFee, uint256 affiliateFee, uint16 indexed dAppTag)` |
| `0x7f32e90e3fb6eb794eaf193eacb729a5b0bf5ab7d1f5f348f8f5beeac89e3d54` | `FeeInfo(address token, address indexed affiliatorAddress, uint256 affiliateFee, uint8 indexed feeType, uint16 indexed dAppTag)` |
| `0xd7dee2702d63ad89917b6a4da9981c90c4d24f8c2bdfd64c604ecae57d8d0651` | `Refunded(address _token, uint256 _amount)` |
| `0x71e2229d8c5917bef9d5c3b4b1df412ba65253373b25d1c117223dbaaaa7c8d8` | `RangoBridgeCompleted(address indexed requestId, address indexed token, address indexed originalSender, address receiver, uint256 amount, uint8 status, uint16 dAppTag)` |

- The first `RangoBridgeInitiated` row is the current version; the second (no `dAppName`) is the older version, which still-registered older entry points can emit (0 logs in the pinned window, §15).
- `RangoBridgeInitiated`: topic1 `requestId`, topic2 `bridgeId`, topic3 `dAppTag`. Data word 0 `bridgeToken`, word 1 `bridgeAmount`, word 2 `receiver`, word 3 `destinationChainId`, word 4 `hasInterchainMessage`, word 5 `hasDestinationSwap`, word 6 the offset of `dAppName`.
- `bridgeAmount` is the amount handed to the bridge after fees and source swaps. The user's input is the token `Transfer` into the diamond or `msg.value`.
- `SendToken(_token, _amount, _receiver)` records every token that the diamond sends out: fees to the affiliate and platform, swap output to the user, leftovers. `_token` = `0x0000000000000000000000000000000000000000` is native. It is not a bridge deposit.
- `FeeInfo` has two versions: the older one splits `platformFee`, `destinationExecutorFee` and `affiliateFee`; the newer one (from RangoGenericBridgeFacet and newer facets) has one `affiliateFee` and a `feeType` topic.
- `RangoBridgeCompleted` is declared by the facets too, but only the middlewares emit it ([middlewares.md](middlewares.md)).

### 1.2 Bridge-specific events (diamond)

| topic0 | Event |
|--------|-------|
| `0xc295b66e7b42fe7598f77459b85e32813c6e62763388a1e8b614bfff53b8c9f3` | `CCTPBridgeDepositAndBurnDone(uint32 destinationDomainId, bytes32 recipient, address token, uint256 amount)` |
| `0x5fe7ba3dde699cb814362252ee89c82961d1b80e6a91574b41a207d2a23cdeb5` | `ArbitrumBridgeRouterCalled(address router, address recipient, address token, uint256 amount)` |
| `0xe7e76cc37439b0f6049d074942f9a1e738d7930326898e502cfa4b30a3116ba7` | `OptimismBridgeCalled(address bridge, address recipient, address token, uint256 amount, bool isSynth)` |
| `0x81ea314f46b4cfa696b8dd3642508f80bacbd2511f83659a175ca0dd4ee6b9c9` | `ConnextBridgeCalled(uint256 _dstChainId, address _token, string _receiver, uint256 _amount, uint8 _bridgeType)` |
| `0x82af8b970953622fe2907c80207d2172a5ebf37b26f9b41e730c207035c9c80f` | `DeBridgeSendTokenCalled(uint256 _dstChainId, address _token, string _receiver, uint256 _amount, uint8 _type)` |
| `0x675fd9e5424c5cee2cedf832b1b0cc06c164d6fa74b75ce1e7c9359e74463163` | `SatelliteSendTokenCalled(uint256 _dstChainId, address _token, string _receiver, uint256 _amount)` |
| `0xf2713048ad6c476f22d9c81b363aaf6fe15ccdda103e11ef04628fe8fd5fd00d` | `ThorchainTxInitiated(address vault, address token, uint256 amount, string memo, uint256 expiration)` |
| `0xc043158bdcb2aaaed115dab269f289e91b2e138832c54c53eb960551926e44c7` | `SynapseBridgeDetailEvent(address bridgeToken, uint8 tokenIndexFrom, uint8 tokenIndexTo, uint256 minDy, uint256 deadline, uint8 swapTokenIndexFrom, uint8 swapTokenIndexTo, uint256 swapMinDy, uint256 swapDeadline)` |
| `0x118c5826693211a5b7b1e524d40ed4356d17812c4c5b41def75ee3003f57b5db` | `PolyDeposit(uint64 dstChainId, address token, address receiver, uint256 amount, uint256 fee)` |
| `0xe1cdc506b86cc05898c568c4ae5eb4f1d110f20840d600bb3b426c4deb5c9a62` | `SymbiosisSwapStatusUpdated(address token, uint256 outputAmount, uint8 status, address source, address destination)` |

### 1.3 Admin events (diamond)

| topic0 | Event |
|--------|-------|
| `0x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673` | `DiamondCut((address facetAddress, uint8 action, bytes4[] functionSelectors)[] _diamondCut, address _init, bytes _calldata)` |
| `0xed8889f560326eb138920d842192f0eb3dd22b4f139c87a2c57538e05bae1278` | `OwnershipTransferRequested(address indexed _from, address indexed _to)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |
| `0xba619e056949849c0c3e5942f98229e94566a0ac75b482e7602fc3100e8854f8` | `PausedStateUpdated(bool _oldPausedState, bool _newPausedState)` |
| `0xb7269578552456138d47dc37471d94886205143f138387446eff0148047965f6` | `ContractWhitelisted(address _address)` |
| `0xfb00f7adc91459b5048ecdc60b783959a583bafb1e3041f3e1f017540a0e47d3` | `ContractBlacklisted(address _address)` |
| `0xf3db38b8bdedf89980dccafd178b958066ba0cfbf68c8b37b9845a176438a332` | `ContractAndMethodsWhitelisted(address contractAddress, bytes4[] methods)` |
| `0x9128663055bb19dea35383762b39d6420bbfdb1d4ead002518dd0e8062fabf60` | `ContractAndMethodsBlacklisted(address contractAddress, bytes4[] methods)` |
| `0x1c7cb0cdc9ba781f9745f3e24b6de0c45db97bf81b2091dfbcc45e9fdd1c1d13` | `FeeContractAddressUpdated(address _oldAddress, address _newAddress)` |
| `0xcfdb33c0c0613c5035b8848040c10b9625e341ee97988ee2720de0ffbe5392d2` | `WethContractAddressUpdated(address _oldAddress, address _newAddress)` |

`PausedStateUpdated` (RangoAccessManagerFacet `changePauseState`) pauses all entry points. `ContractWhitelisted` / `ContractAndMethodsWhitelisted` add a DEX or bridge target that the diamond may call.

### 1.4 Facet configuration events (diamond)

These change the bridge addresses that a facet uses. They move no value, but they redirect future deposits.

| topic0 | Event |
|--------|-------|
| `0x582b079c313c12210d017af811111c00df441d7ad74b7b474a9ae81131f73193` | `AcrossSpokePoolsAdded(address[] _addresses)` |
| `0x742412c0a9b12d3e5fac09159eae18cea14f2c0bfba2edb1785d0270d0f5b860` | `AcrossSpokePoolsRemoved(address[] _addresses)` |
| `0x5e716f57c6e19831a3621ab4b843d399557f4fbc1e0b7ff73fb69a9fba62ee01` | `AcrossRewardBytesUpdated(bytes rewardBytes)` |
| `0x6b23750dfe5fa94916c04d68fb07d9885aba04f298d6f544584df1543071775d` | `AllBridgeBridgeAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x21d2dcb4013eb8f9c4543b00f845d0b8914d652d3216d7488fa3d8bc9caae354` | `ArbitrumBridgeAddressChanged(address oldInboxAddress, address oldRouterAddress, address newInboxAddress, address newRouterAddress)` |
| `0xf02fb17e01c7e29424f96d2822178244d6d50480f818fadb694eba551e842480` | `CCTPTokenMessengerAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x195cbd5ca242aee6add873b53232a98467688ebc502dd14d6c0ac0907f4a9553` | `CCTPUSDCTokenAddressUpdated(address _oldAddress, address _newAddress)` |
| `0xef5e48903952cc16aa163bc459215e6389b53c85a64413d2a1471e280ef90f1f` | `ChainFlipVaultAddressChangedTo(address changedFromAddress, address changedToAddress)` |
| `0x0e92f28b845f1e861a5b2d2dd53667873f7f7ca6843d80c61e483426be00d89a` | `ConnextAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x21c9021c97f90689b456b6c5596ad7b34e35956310cd9adb3e827510f91eeb4b` | `DeBridgeDlnSourceAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x522c31269e18a0944e80ae7f42e41aecece936c3522cc6892f456ad133ecf402` | `HyphenAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x81c16a53fbd623a5a4d8455016c10ed2dac832fbb7577c812df3d615bae7f3aa` | `MultichainRoutersAdded(address[] _addresses)` |
| `0xf60edbae2829c4ad242912d9f5c804cb71407ecebc5395f229534994239b7f06` | `MultichainRoutersRemoved(address[] _addresses)` |
| `0x6e800a0218388799ae51e714b3917e21b38b5b7f368ab34f94bdfa80238a9bd7` | `NitroAssetForwarderAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x96e0d782c390ea15a06ecb2668e2297683997347f96b42bd476eb8d1507b046f` | `OptimismBridgesAdded((address bridgeAddress)[] data)` |
| `0xe5c274b293a611521defe16f5ae457739c6621ece6a63f5ba5bd8ff049f703e8` | `OptimismBridgesRemoved((address bridgeAddress)[] data)` |
| `0xe05003db83feccfca292a328551733e0e54478d48abc879be93097282c3d9a7d` | `OrbiterRoutersAdded(address[] _addresses)` |
| `0x81776a8561be88ecc071a6b7e859bbc337de4e7790bdf2b173537e97955fb5d1` | `OrbiterRoutersRemoved(address[] _addresses)` |
| `0x4cae7955e31824be5cfe2c2176b68c49ef941c7275b7f6eaebc1d9f88a3e0afa` | `PolyAddressUpdated(address _oldAddress, address _newAddress)` |
| `0xc5474af28634e5155be634ccaea8d3e9e77344679b451d664aef7e190a1ba17e` | `SatelliteGatewayAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x92e582258b051d853fc828c6d04995b357ec8508517b4e55eced0fd2281191cc` | `SatelliteGasServiceAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x16e93be1e2a77323b126a6817a072e6492bb2391f38ef917990623361ea8a286` | `StargateAddressUpdated(address _oldRouter, address _oldRouterEth, address _newRouter, address _newRouterEth)` |
| `0x8ddaf216d7ab7b2a5cbeea2697f8262531d8bf871a09c65da5aca079abefc005` | `StargateWidgetUpdated(address _widgetAddress, bytes2 _partnerId)` |
| `0x4b0225db3af98483f3480c9a00a6540ce212fd0b32166d7983c25e52be8cdea8` | `StargateV2TreasurerAddressUpdated(address _oldTreasurer, address _newTreasurer)` |
| `0xbf8cb295ad941f1d941ce049925fe9be3752a513b07415d28167b25666c1d4cd` | `SwftContractAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x76e986cd13bf71a8a240988fea38de00b0de8942adfc6b939d507554c750a723` | `SymbiosisAddressUpdated(address oldMetaRouter, address oldMetaRouterGateway, address indexed newMetaRouter, address indexed newMetaRouterGateway)` |
| `0xe18ad9e1b0843ff9f1c71eab0f5691dba2c7359e49163e13a347ce129f0f2b28` | `SynapseAddressUpdated(address _oldAddress, address _newAddress)` |
| `0xf3d5ff20743591b40638a4ce7a31e08808d27c267992e17c740184c8f8925b46` | `ReserveHandlerAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x4a505e8956939fe6056593b41a5366ce1729021b36be5744e901c1bbf71a3897` | `RouterBridgeAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x4a6f01e203e02ddd3ac45125fb9e4f91ee49d02d11356588b6c13bc297164c32` | `WormholeAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x24176c81d00961cf639ffef043039cf4da7fc88f1b61f778343ff6aaf6cce525` | `YBridgeAddressUpdated(address _oldAddress, address _newAddress)` |
| `0x480901a71e514084ce3f1e1110eb88f1f878fc71da1b3a1fe24393e5fea6c0d7` | `RangoCBridgeMiddlewareAddressUpdated(address oldAddress, address newAddress)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

The third column names the facet and the chains whose diamond has the selector registered (loupe read of 2026-09-29). Many bridge facets exist in two generations: the older entry points take a `RangoBridgeRequest` without `string dAppName`, the newer ones with it; both are registered on most chains.

| Selector | Signature | Facet: live on |
|----------|-----------|----------------|
| `0x1f931c1c` | `diamondCut((address,uint8,bytes4[])[],address,bytes)` | DiamondCutFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xcdffacc6` | `facetAddress(bytes4)` | DiamondLoupeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x52ef6b2c` | `facetAddresses()` | DiamondLoupeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xadfca15e` | `facetFunctionSelectors(address)` | DiamondLoupeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x7a0ed627` | `facets()` | DiamondLoupeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x6e25b978` | `selectors()` | DiamondLoupeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x01ffc9a7` | `supportsInterface(bytes4)` | DiamondLoupeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x716344dc` | `burnOwnership()` | OwnershipFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x23452b9c` | `cancelOwnershipTransfer()` | OwnershipFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x7200b829` | `confirmOwnershipTransfer()` | OwnershipFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x8da5cb5b` | `owner()` | OwnershipFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xf2fde38b` | `transferOwnership(address)` | OwnershipFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x81ccf213` | `addWhitelistContract((address,bytes4[])[])` | RangoAccessManagerFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xd56d5a7d` | `addWhitelistContract(address)` | RangoAccessManagerFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xc8eaf28f` | `addWhitelists(address[])` | RangoAccessManagerFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xd95b3221` | `changePauseState(bool)` | RangoAccessManagerFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x03de9416` | `removeContractAndMethodIdsFromWhitelist(address,bytes4[])` | RangoAccessManagerFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xb260343d` | `removeWhitelistContract(address)` | RangoAccessManagerFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xb0652ee6` | `acrossBridge((address,address,address,address,uint32,uint32,address,uint256,uint256,uint32,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoAcrossFacet: ETH·Base·Arb·OP·Poly·BNB·RH |
| `0xcb7a0b4b` | `acrossBridge((address,address,uint256,int64,uint32,bytes,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoAcrossFacet: ETH·Base·Arb·OP·Poly |
| `0xe6c806ff` | `acrossSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(address,address,address,address,uint32,uint32,address,uint256,uint256,uint32,bytes))` | RangoAcrossFacet: ETH·Base·Arb·OP·Poly·BNB·RH |
| `0x4e42d6d6` | `acrossSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(address,address,uint256,int64,uint32,bytes,uint256))` | RangoAcrossFacet: ETH·Base·Arb·OP·Poly |
| `0x6e2241b8` | `addAcrossSpokePools(address[])` | RangoAcrossFacet: ETH·Base·Arb·OP·Poly·BNB·RH |
| `0x7daed652` | `initAcross(address[],bytes)` | RangoAcrossFacet: ETH·Base·Arb·OP·Poly·BNB·RH |
| `0x6d2cf5c2` | `removeAcrossSpokePools(address[])` | RangoAcrossFacet: ETH·Base·Arb·OP·Poly·BNB·RH |
| `0x9a1fca88` | `setAcrossRewardBytes(bytes)` | RangoAcrossFacet: ETH·Base·Arb·OP·Poly·BNB·RH |
| `0xc064fbe2` | `speedUpAcrossDeposit(address,int64,uint32,address,bytes,bytes)` | RangoAcrossFacet: ETH·Base·Arb·OP·Poly |
| `0x6629ed7a` | `speedUpAcrossDepositWithHash(address,bytes32,int64,uint32,address,bytes,bytes)` | RangoAcrossFacet: ETH·Base·Arb·OP·Poly |
| `0xa862f37a` | `allbridgeBridge((bytes32,uint256,bytes32,uint256,uint8,uint256,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoAllBridgeFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xec9c6cb1` | `allbridgeBridge((bytes32,uint256,bytes32,uint256,uint8,uint256,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoAllBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x58bf7c03` | `allbridgeSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(bytes32,uint256,bytes32,uint256,uint8,uint256,uint256))` | RangoAllBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x503c1c98` | `allbridgeSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(bytes32,uint256,bytes32,uint256,uint8,uint256,uint256))` | RangoAllBridgeFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x2223f844` | `updateAllBridgeBridgeAddress(address)` | RangoAllBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xdc782c39` | `arbitrumBridge((address,uint256,uint256,uint256,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoArbitrumBridgeFacet: ETH |
| `0x9be0d06f` | `arbitrumBridge((address,uint256,uint256,uint256,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoArbitrumBridgeFacet: ETH |
| `0x49e6458e` | `arbitrumSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(address,uint256,uint256,uint256,uint256))` | RangoArbitrumBridgeFacet: ETH |
| `0x2991e8ac` | `arbitrumSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(address,uint256,uint256,uint256,uint256))` | RangoArbitrumBridgeFacet: ETH |
| `0x472b4195` | `initArbitrum(address,address)` | RangoArbitrumBridgeFacet: ETH |
| `0x28f4e0b4` | `cBridgeBridge((address,address,uint256,uint256,uint256,address,uint256,uint16),(uint8,address,uint64,uint64,uint32,uint256,bytes))` | RangoCBridgeFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xb738e473` | `cBridgeBridge((address,address,uint256,uint256,uint256,address,uint256,uint16,string),(uint8,address,uint64,uint64,uint32,uint256,bytes))` | RangoCBridgeFacet: Arb·OP·Poly·BNB·Avax |
| `0xea1ffbd8` | `cBridgeSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint8,address,uint64,uint64,uint32,uint256,bytes))` | RangoCBridgeFacet: Arb·OP·Poly·BNB·Avax |
| `0x058590f4` | `cBridgeSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(uint8,address,uint64,uint64,uint32,uint256,bytes))` | RangoCBridgeFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x4b4c6d30` | `initCBridge(address)` | RangoCBridgeFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x3410816d` | `cctpBridge((uint32,bytes32,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoCCTPFacet: ETH·Base·Arb·OP·Poly·Avax |
| `0x60d09476` | `cctpSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint32,bytes32,uint256))` | RangoCCTPFacet: ETH·Base·Arb·OP·Poly·Avax |
| `0x35668dbf` | `initCCTP(address,address)` | RangoCCTPFacet: ETH·Base·Arb·OP·Poly·Avax |
| `0xf776dcf4` | `replaceDeposit(bytes,bytes,bytes32)` | RangoCCTPFacet: ETH·Base·Arb·OP·Poly·Avax |
| `0xb7135a9b` | `updateCCTPTokenMessengerAddress(address)` | RangoCCTPFacet: ETH·Base·Arb·OP·Poly·Avax |
| `0x0377a631` | `updateCCTPUSDCTokenAddress(address)` | RangoCCTPFacet: ETH·Base·Arb·OP·Poly·Avax |
| `0x9fe99b64` | `chainFlipBridge((uint32,bytes,uint32,bytes,uint256,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoChainFlipFacet: ETH·Arb |
| `0x57e780ad` | `chainFlipSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint32,bytes,uint32,bytes,uint256,bytes))` | RangoChainFlipFacet: ETH·Arb |
| `0x29900c83` | `changeChainFlipVaultAddress(address)` | RangoChainFlipFacet: ETH·Arb |
| `0x8f105d8f` | `initChainFlip(address)` | RangoChainFlipFacet: ETH·Arb |
| `0x458a6f78` | `connextBridge((uint8,address,address,uint256,uint256,uint32,uint256,bool,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoConnextFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0x1d37475f` | `connextSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint8,address,address,uint256,uint256,uint32,uint256,bool,bytes))` | RangoConnextFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0x4c0d58c1` | `initConnext((address))` | RangoConnextFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0xef1906ed` | `updateConnextAddress(address)` | RangoConnextFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0x6debed2b` | `deBridgeBridge(((address,uint256,bytes,uint256,uint256,bytes,address,bytes,bytes,bytes,bytes),uint64,uint32,bytes,bytes,bytes,uint256,uint8,bool),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoDeBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x40316f76` | `deBridgeSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],((address,uint256,bytes,uint256,uint256,bytes,address,bytes,bytes,bytes,bytes),uint64,uint32,bytes,bytes,bytes,uint256,uint8,bool))` | RangoDeBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x32b32f7e` | `initDeBridge(address)` | RangoDeBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x6bfa2ec6` | `updateDlnSourceAddress(address)` | RangoDeBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xb25b1c31` | `genericBridge((uint8,(address,address,bytes,uint256,uint256,bool)[],address,uint256,bool,bool,uint256,uint256),(address,address,uint256,(address,uint256,uint8)[],uint256,uint16,string))` | RangoGenericBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x35019106` | `genericSwapAndBridge((address,address,address,uint256,(address,uint256,uint8)[],uint256,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint8,(address,address,bytes,uint256,uint256,bool)[],address,uint256,bool,bool,uint256,uint256))` | RangoGenericBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xead31fbc` | `onChainSwaps((address,address,address,uint256,(address,uint256,uint8)[],uint256,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],address)` | RangoGenericBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x40e83407` | `hyphenBridge((address,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoHyphenFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xa48e74f4` | `hyphenBridge((address,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoHyphenFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xd0b9ed20` | `hyphenSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(address,uint256))` | RangoHyphenFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x28ad014c` | `hyphenSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(address,uint256))` | RangoHyphenFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x0ee164e3` | `initHyphen(address)` | RangoHyphenFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xcc818ad1` | `initMultichain(address[])` | RangoMultichainFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x95c2d6f3` | `multichainBridge((uint8,uint8,address,address,address,uint256,string,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoMultichainFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xa6c3d51f` | `multichainSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(uint8,uint8,address,address,address,uint256,string,bytes))` | RangoMultichainFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xda2ad947` | `removeMultichainRouters(address[])` | RangoMultichainFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x859e2a23` | `initRouterNitroAssetForwarded(address)` | RangoNitroAssetForwarderFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x989d3626` | `nitroAssetForwarderBridge((uint256,uint256,address,bytes32,bytes,bytes,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoNitroAssetForwarderFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x12767c5d` | `nitroAssetForwarderSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint256,uint256,address,bytes32,bytes,bytes,bytes))` | RangoNitroAssetForwarderFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xc246797a` | `updateNitroAssetForwarder(address)` | RangoNitroAssetForwarderFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x0d8aa7ea` | `initOptimism((address)[])` | RangoOptimismBridgeFacet: ETH |
| `0x681ab59e` | `optimismBridge((address,address,address,uint32,bool),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoOptimismBridgeFacet: ETH |
| `0xf974e94a` | `optimismBridge((address,address,address,uint32,bool),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoOptimismBridgeFacet: ETH |
| `0xb8c3f750` | `optimismSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(address,address,address,uint32,bool))` | RangoOptimismBridgeFacet: ETH |
| `0xa67d3931` | `optimismSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(address,address,address,uint32,bool))` | RangoOptimismBridgeFacet: ETH |
| `0xeab0be56` | `removeOptimismBridges((address)[])` | RangoOptimismBridgeFacet: ETH |
| `0xe550c0e3` | `addOrbiterRouterContracts(address[])` | RangoOrbiterFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0x3158d765` | `initOrbiter(address[])` | RangoOrbiterFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0xa6fa59ca` | `orbiterBridge((address,address,address,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoOrbiterFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0xbd760e97` | `orbiterSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(address,address,address,bytes))` | RangoOrbiterFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0x7b2eb386` | `removeOrbiterRouterContracts(address[])` | RangoOrbiterFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0xe3aa85dc` | `initPoly(address)` | RangoPolyFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x11a99156` | `polyBridge((address,uint64,uint256,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoPolyFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x6adbd598` | `polySwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(address,uint64,uint256,uint256))` | RangoPolyFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x8e6eea55` | `initSatellite((address,address))` | RangoSatelliteFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x63e5468f` | `satelliteBridge((uint8,string,uint256,string,string,uint256,address,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoSatelliteFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x66155375` | `satelliteBridge((uint8,string,uint256,string,string,uint256,address,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoSatelliteFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x5a18f941` | `satelliteSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint8,string,uint256,string,string,uint256,address,bytes))` | RangoSatelliteFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x52b30bbe` | `satelliteSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(uint8,string,uint256,string,string,uint256,address,bytes))` | RangoSatelliteFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xd9f03f29` | `updateSatelliteGasServiceAddress(address)` | RangoSatelliteFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x59c94b37` | `updateSatelliteGatewayAddress(address)` | RangoSatelliteFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x12249b40` | `initStargate((address,address,address,bytes2))` | RangoStargateFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xc0fd2fc1` | `stargateBridge((uint8,uint16,uint256,uint256,address,uint256,uint256,uint256,bytes,bytes,uint256,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoStargateFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x0eb564a3` | `stargateBridge((uint8,uint16,uint256,uint256,address,uint256,uint256,uint256,bytes,bytes,uint256,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoStargateFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xa5a11ab4` | `stargateSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint8,uint16,uint256,uint256,address,uint256,uint256,uint256,bytes,bytes,uint256,bytes))` | RangoStargateFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x3070c305` | `stargateSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(uint8,uint16,uint256,uint256,address,uint256,uint256,uint256,bytes,bytes,uint256,bytes))` | RangoStargateFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x78d46f99` | `updateStargateAddress(address,address)` | RangoStargateFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x0d768d31` | `updateStargateWidget(address,bytes2)` | RangoStargateFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xfdfb8b16` | `initStargateV2(address)` | RangoStargateV2Facet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x7263e87d` | `stargateV2Bridge((address,uint32,uint16,bytes32,uint256,address,uint256,bytes,bytes,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoStargateV2Facet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xb6ba374a` | `stargateV2SwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(address,uint32,uint16,bytes32,uint256,address,uint256,bytes,bytes,bytes))` | RangoStargateV2Facet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xd1bd2122` | `updateStargateV2TreasurerAddress(address)` | RangoStargateV2Facet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xeb26b356` | `initBaseSwapper(address,address)` | RangoSwapperFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xc057058a` | `isContractWhitelisted(address)` | RangoSwapperFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x14d08fca` | `onChainSwaps((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],address)` | RangoSwapperFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xb17d0e6e` | `onChainSwaps((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],bool,address)` | RangoSwapperFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x410085df` | `refund(address,uint256)` | RangoSwapperFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x9fae52e6` | `refundNative(uint256)` | RangoSwapperFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xc69bebe4` | `updateFeeReceiver(address)` | RangoSwapperFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x18318291` | `initSwft(address)` | RangoSwftFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x345ad697` | `swftBridge((string,string,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoSwftFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xe95df283` | `swftSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(string,string,uint256))` | RangoSwftFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xc0c979c4` | `updateSwftContractAddress(address)` | RangoSwftFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xd2764559` | `initSymbiosis((address,address))` | RangoSymbiosisFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x48852518` | `symbiosisBridge((uint8,(bytes,bytes,address[],address,address,uint256,bool,address,bytes),address,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoSymbiosisFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xab2d4dca` | `symbiosisBridge((uint8,(bytes,bytes,address[],address,address,uint256,bool,address,bytes),address,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoSymbiosisFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x00c8169b` | `symbiosisSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint8,(bytes,bytes,address[],address,address,uint256,bool,address,bytes),address,uint256))` | RangoSymbiosisFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x441ad8a4` | `symbiosisSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(uint8,(bytes,bytes,address[],address,address,uint256,bool,address,bytes),address,uint256))` | RangoSymbiosisFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x22a65510` | `initSynapse(address)` | RangoSynapseFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x4651fe41` | `synapseBridge((uint8,address,address,uint256,address,uint8,uint8,uint256,uint256,uint8,uint8,uint256,uint256,uint256[]),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoSynapseFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xc1605666` | `synapseBridge((uint8,address,address,uint256,address,uint8,uint8,uint256,uint256,uint8,uint8,uint256,uint256,uint256[]),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoSynapseFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x73d54bbb` | `synapseSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint8,address,address,uint256,address,uint8,uint8,uint256,uint256,uint8,uint8,uint256,uint256,uint256[]))` | RangoSynapseFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xd0c9c6d6` | `synapseSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(uint8,address,address,uint256,address,uint8,uint8,uint256,uint256,uint8,uint8,uint256,uint256,uint256[]))` | RangoSynapseFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x08a018aa` | `thorchainBridge((address,address,uint256,uint256,uint256,address,uint256,uint16),address,address,string,uint256)` | RangoThorchainFacet: ETH·BNB·Avax |
| `0xe5f27d54` | `thorchainBridge((address,address,uint256,uint256,uint256,address,uint256,uint16,string),(address,address,string,uint256,bool))` | RangoThorchainFacet: ETH·Base·Arb·BNB·Avax |
| `0x24ac9c35` | `thorchainSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(address,address,string,uint256,bool))` | RangoThorchainFacet: ETH·Base·Arb·BNB·Avax |
| `0xdf759fce` | `thorchainSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],address,address,string,uint256)` | RangoThorchainFacet: ETH·BNB·Avax |
| `0xee8f169a` | `initVoyager((address,address,address))` | RangoVoyagerFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x15ede747` | `updateVoyagerReserveHandler(address)` | RangoVoyagerFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x5467be8b` | `updateVoyagerRouters(address)` | RangoVoyagerFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xb2237c89` | `updateVoyagerSpecificNativeWrappedAddress(address)` | RangoVoyagerFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xb2c95cda` | `voyagerBridge((uint8,bytes32,address,uint256,uint256,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoVoyagerFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xd5e9e0c5` | `voyagerSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(uint8,bytes32,address,uint256,uint256,bytes))` | RangoVoyagerFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x2c4e0ccc` | `initWormhole(address)` | RangoWormholeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x9a6c3086` | `updateWormholeAddress(address)` | RangoWormholeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xf3b428ca` | `wormholeBridge((uint8,uint16,bytes32,uint256,uint32,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16))` | RangoWormholeFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0x2e4bbc8e` | `wormholeBridge((uint8,uint16,bytes32,uint256,uint32,bytes),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoWormholeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x97d44ec6` | `wormholeSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(uint8,uint16,bytes32,uint256,uint32,bytes))` | RangoWormholeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x79bdcbf9` | `wormholeSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,uint16),(address,address,address,address,bool,uint256,bytes)[],(uint8,uint16,bytes32,uint256,uint32,bytes))` | RangoWormholeFacet: ETH·Arb·OP·Poly·BNB·Avax |
| `0xe1848368` | `initYBridge(address)` | RangoYBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xb746d71b` | `updateYBridgeAddress(address)` | RangoYBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x53e4a6f4` | `yBridgeBridge((address,uint32,address,address,address,uint32,uint256),(address,address,uint256,uint256,uint256,address,uint256,uint16,string))` | RangoYBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x6b39e82b` | `yBridgeSwapAndBridge((address,address,address,uint256,uint256,uint256,uint256,address,uint256,bool,uint16,string),(address,address,address,address,bool,uint256,bytes)[],(address,uint32,address,address,address,uint32,uint256))` | RangoYBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |

---

## 3. Addresses — Ethereum (chain ID 1)

Checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **RangoDiamond** | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | 5,208-byte runtime. 42 facets / 152 selectors live. |
| Owner | `0xaFd5B23F8e84A8b77f01D5f73D5207e28DAd71eB` | `owner()` of the diamond; 171-byte contract: a Safe 1.3.0 proxy, 3-of-5 (`getThreshold()`, `getOwners()`, `VERSION()` read on 2026-09-29). |

## 4. Addresses — Base (chain ID 8453)

Checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **RangoDiamond** | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | 5,208-byte runtime. 26 facets / 105 selectors live. |
| Owner | `0xE4A00993C9DeE173526A30d417cE5C8f1ef67A3f` | `owner()` of the diamond; 171-byte contract: a Safe 1.3.0 proxy, 3-of-5 (`getThreshold()`, `getOwners()`, `VERSION()` read on 2026-09-29). |

## 5. Addresses — Arbitrum One (chain ID 42161)

Checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **RangoDiamond** | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | 5,208-byte runtime. 38 facets / 141 selectors live. |
| Owner | `0x741AE1fcF519671Cdf467Ca9cF764c2492a95cfa` | `owner()` of the diamond; 171-byte contract: a Safe 1.3.0 proxy, 3-of-5 (`getThreshold()`, `getOwners()`, `VERSION()` read on 2026-09-29). |

## 6. Addresses — Optimism (chain ID 10)

Checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **RangoDiamond** | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | 5,208-byte runtime. 36 facets / 135 selectors live. |
| Owner | `0xa2CF562b1d8E8C6F7C59441F836837F7eDC4852F` | `owner()` of the diamond; 171-byte contract: a Safe 1.3.0 proxy, 3-of-5 (`getThreshold()`, `getOwners()`, `VERSION()` read on 2026-09-29). |

## 7. Addresses — Polygon PoS (chain ID 137)

Checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **RangoDiamond** | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | 5,208-byte runtime. 36 facets / 135 selectors live. |
| Owner | `0xe12989Ae0f1d8068aF0e8D0CF26f5F8e7b615a26` | `owner()` of the diamond; 171-byte contract: a Safe 1.3.0 proxy, 3-of-5 (`getThreshold()`, `getOwners()`, `VERSION()` read on 2026-09-29). |

## 8. Addresses — BNB Smart Chain (chain ID 56)

Checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **RangoDiamond** | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | 5,208-byte runtime. 36 facets / 126 selectors live. |
| Owner | `0x4BE54063df659898625fC48C8161432CDD793E9b` | `owner()` of the diamond; 171-byte contract: a Safe 1.3.0 proxy, 3-of-5 (`getThreshold()`, `getOwners()`, `VERSION()` read on 2026-09-29). |

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

Checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **RangoDiamond** | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | 5,208-byte runtime. 34 facets / 116 selectors live. |
| Owner | `0xFd8AB8F12c17E0C4f2d701931Bc4825626482bc2` | `owner()` of the diamond; 171-byte contract: a Safe 1.3.0 proxy, 3-of-5 (`getThreshold()`, `getOwners()`, `VERSION()` read on 2026-09-29). |

## 10. Addresses — Robinhood Chain (chain ID 4663)

Checked with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **RangoDiamond** | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | 5,208-byte runtime. 7 facets / 34 selectors live. |
| Owner | `0x5C449b48Ec0f94B63CF1FF828D19A8C6758EB4ad` | `owner()` of the diamond; 123-byte contract: a Safe 1.5.0 proxy, 3-of-5 (`getThreshold()`, `getOwners()`, `VERSION()` read on 2026-09-29). |

---

## 11. Addresses — Arc (chain ID 5042)

Checked with `eth_getCode` on `https://rpc.mainnet.arc.io` on 2026-10-05.

| Role | Address | One-liner |
|------|---------|-----------|
| **RangoDiamond** | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | 5,208-byte runtime, same code hash as Ethereum. 7 facets / 34 selectors live, the same seven facet addresses as Robinhood Chain. EIP-1967 implementation slot empty. |
| Owner | `0xB1D330f5f1c467B76d5DB02315fEAA17CAbCBD01` | `owner()` of the diamond; 123-byte contract: a Safe 1.5.0 proxy, 3-of-5 (`getThreshold()`, `getOwners()`, `VERSION()` read on 2026-10-05). |

In ~40,000 Arc blocks (about 5.7 h) to 2026-10-05 the diamond emitted `RangoBridgeInitiated` 3, `RangoSwap` 5, `CallResult` 7, `SendToken` 13, `FeeInfo` 3 and `FeeInfo` (old) 5 (`eth_getLogs`).

---

## 12. Cross-chain summary

| Chain | ID | RangoDiamond | Owner | Facets / selectors |
|-------|----|--------------|-------|--------------------|
| Ethereum | 1 | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | `0xaFd5B23F8e84A8b77f01D5f73D5207e28DAd71eB` | 42 / 152 |
| Base | 8453 | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | `0xE4A00993C9DeE173526A30d417cE5C8f1ef67A3f` | 26 / 105 |
| Arbitrum One | 42161 | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | `0x741AE1fcF519671Cdf467Ca9cF764c2492a95cfa` | 38 / 141 |
| Optimism | 10 | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | `0xa2CF562b1d8E8C6F7C59441F836837F7eDC4852F` | 36 / 135 |
| Polygon PoS | 137 | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | `0xe12989Ae0f1d8068aF0e8D0CF26f5F8e7b615a26` | 36 / 135 |
| BNB Smart Chain | 56 | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | `0x4BE54063df659898625fC48C8161432CDD793E9b` | 36 / 126 |
| Avalanche C-Chain | 43114 | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | `0xFd8AB8F12c17E0C4f2d701931Bc4825626482bc2` | 34 / 116 |
| Robinhood Chain | 4663 | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | `0x5C449b48Ec0f94B63CF1FF828D19A8C6758EB4ad` | 7 / 34 |
| Arc | 5042 | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | `0xB1D330f5f1c467B76d5DB02315fEAA17CAbCBD01` | 7 / 34 |

The Rango docs list the diamond on Ethereum, Polygon, Optimism, Arbitrum, BNB, Avalanche and Base among other networks. Robinhood Chain and Arc are not in that list, but `eth_getCode` shows the same 5,208-byte runtime at `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` on both, the loupe returns 7 facets on both, and the diamond emitted Rango events on Robinhood Chain in the pinned window (§16) and on Arc on 2026-10-05 (§11).

---

## 13. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **RangoDiamond** | EIP-2535 diamond | `facets()` returns the facet table; the EIP-1967 implementation slot is empty. Watch `DiamondCut` (topic0 `0x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673`). | `owner()` (per chain, §3–§11); two-step transfer (`OwnershipTransferRequested`, `OwnershipTransferred`); `burnOwnership()` exists. |
| Facets | Plain contracts | Run only through `DELEGATECALL` from the diamond. | Replaced by `diamondCut`. |

---

## 14. Detection invariants & gotchas

1. **Source leg = `RangoBridgeInitiated` at the diamond.** Pair it with the underlying bridge's deposit event in the same transaction for the bridge's own id.
2. **Non-EVM destinations are encoded in ASCII.** `destinationChainId` `1414680398` = "TRON", `1279348289` = "LANA" (Solana), `4346947` = "BTC", `5461321` = "SUI"; `receiver` then holds the first 20 characters of the destination address as ASCII bytes. In the pinned window 464 of the 842 Ethereum logs and 74 of the 284 Base logs had such an ASCII `receiver`. The full destination address is only in the bridge's own data.
3. **`dAppName` names the integrator.** Measured on Ethereum: `TrustWallet` 745 of 842, `BinanceWeb3Wallet` 58, `MetaMask` 23. `dAppTag` (topic3) is the numeric integrator id.
4. **`hasInterchainMessage` decides where the destination record is.** In the pinned window it was false for 834 of 842 Ethereum logs and for all 284 Base logs: those routes end with the bridge's payout, not with `RangoBridgeCompleted`.
5. **Fees and payouts are `SendToken`, not transfers you can attribute by topic alone.** Read the ERC-20 `Transfer` logs of the same transaction for the exact amounts.
6. **Admin triggers.** `DiamondCut`, `OwnershipTransferRequested`, `OwnershipTransferred`, `PausedStateUpdated`, `ContractWhitelisted`, `ContractAndMethodsWhitelisted`, `FeeContractAddressUpdated`, and the bridge-address update events of §1.4.

---

## 15. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_RANGO_BRIDGE_INITIATED          = '\x012c155f3836c4edb9222305b909a109f9efa46288efffe40a0e66da3a9a9800'
TOPIC_RANGO_BRIDGE_INITIATED_OLD      = '\xa551f5e7134cc110651fa6eb8a0423535b3ea90eedb01463af70e6798a75d426'
TOPIC_RANGO_SWAP                      = '\x0e9201911743fd4d03e146f00ad23945dc8f3ffc200906eff25179a52b726f17'
TOPIC_RANGO_SEND_TOKEN                = '\xdf4363408b2d9811d1e5c23efdb5bae0b7a68bd9de2de1cbae18a11be3e67ef5'
TOPIC_RANGO_CALL_RESULT               = '\x2fc0d44e6ef6b3e7707cacd3cc326511198c3d1598c65dd54be5a9e37ce02f12'
TOPIC_RANGO_FEE_INFO_OLD              = '\xf14fbd8b6e3ad3ae34babfa1f3b6a099f57643662f4cfc24eb335ae8718f534b'
TOPIC_RANGO_FEE_INFO                  = '\x7f32e90e3fb6eb794eaf193eacb729a5b0bf5ab7d1f5f348f8f5beeac89e3d54'
TOPIC_RANGO_BRIDGE_COMPLETED          = '\x71e2229d8c5917bef9d5c3b4b1df412ba65253373b25d1c117223dbaaaa7c8d8'
TOPIC_RANGO_CCTP_DEPOSIT_AND_BURN     = '\xc295b66e7b42fe7598f77459b85e32813c6e62763388a1e8b614bfff53b8c9f3'
TOPIC_RANGO_THORCHAIN_TX_INITIATED    = '\xf2713048ad6c476f22d9c81b363aaf6fe15ccdda103e11ef04628fe8fd5fd00d'
-- admin
TOPIC_DIAMOND_CUT                     = '\x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673'
TOPIC_OWNERSHIP_TRANSFER_REQUESTED    = '\xed8889f560326eb138920d842192f0eb3dd22b4f139c87a2c57538e05bae1278'
TOPIC_OWNERSHIP_TRANSFERRED           = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_RANGO_PAUSED_STATE_UPDATED      = '\xba619e056949849c0c3e5942f98229e94566a0ac75b482e7602fc3100e8854f8'
TOPIC_RANGO_CONTRACT_WHITELISTED      = '\xb7269578552456138d47dc37471d94886205143f138387446eff0148047965f6'
TOPIC_RANGO_CONTRACT_METHODS_WHITELISTED = '\xf3db38b8bdedf89980dccafd178b958066ba0cfbf68c8b37b9845a176438a332'

-- ===== Selectors (chain-agnostic) =====
SEL_GENERIC_BRIDGE                    = '\xb25b1c31'
SEL_GENERIC_SWAP_AND_BRIDGE           = '\x35019106'
SEL_ON_CHAIN_SWAPS                    = '\x14d08fca'
SEL_ACROSS_BRIDGE                     = '\xb0652ee6'
SEL_ACROSS_SWAP_AND_BRIDGE            = '\xe6c806ff'
SEL_CCTP_BRIDGE                       = '\x3410816d'
SEL_CHAINFLIP_BRIDGE                  = '\x9fe99b64'
SEL_THORCHAIN_BRIDGE                  = '\xe5f27d54'
SEL_STARGATE_V2_BRIDGE                = '\x7263e87d'
SEL_DIAMOND_CUT                       = '\x1f931c1c'
SEL_CHANGE_PAUSE_STATE                = '\xd95b3221'
SEL_TRANSFER_OWNERSHIP                = '\xf2fde38b'

-- ===== Addresses (same diamond on all nine chains) =====
ETH_RANGO_DIAMOND                     = '\x69460570c93f9de5e2edbc3052bf10125f0ca22d'
BASE_RANGO_DIAMOND                    = '\x69460570c93f9de5e2edbc3052bf10125f0ca22d'
ARB_RANGO_DIAMOND                     = '\x69460570c93f9de5e2edbc3052bf10125f0ca22d'
OP_RANGO_DIAMOND                      = '\x69460570c93f9de5e2edbc3052bf10125f0ca22d'
POLY_RANGO_DIAMOND                    = '\x69460570c93f9de5e2edbc3052bf10125f0ca22d'
BNB_RANGO_DIAMOND                     = '\x69460570c93f9de5e2edbc3052bf10125f0ca22d'
AVAX_RANGO_DIAMOND                    = '\x69460570c93f9de5e2edbc3052bf10125f0ca22d'
RH_RANGO_DIAMOND                      = '\x69460570c93f9de5e2edbc3052bf10125f0ca22d'
ARC_RANGO_DIAMOND                     = '\x69460570c93f9de5e2edbc3052bf10125f0ca22d'
ETH_RANGO_OWNER                       = '\xafd5b23f8e84a8b77f01d5f73d5207e28dad71eb'
BASE_RANGO_OWNER                      = '\xe4a00993c9dee173526a30d417ce5c8f1ef67a3f'
ARB_RANGO_OWNER                       = '\x741ae1fcf519671cdf467ca9cf764c2492a95cfa'
OP_RANGO_OWNER                        = '\xa2cf562b1d8e8c6f7c59441f836837f7edc4852f'
POLY_RANGO_OWNER                      = '\xe12989ae0f1d8068af0e8d0cf26f5f8e7b615a26'
BNB_RANGO_OWNER                       = '\x4be54063df659898625fc48c8161432cdd793e9b'
AVAX_RANGO_OWNER                      = '\xfd8ab8f12c17e0c4f2d701931bc4825626482bc2'
RH_RANGO_OWNER                        = '\x5c449b48ec0f94b63cf1ff828d19a8c6758eb4ad'
ARC_RANGO_OWNER                       = '\xb1d330f5f1c467b76d5db02315feaa17cabcbd01'
```

---

## 16. Verification & sources

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the explorer-verified ABIs of the live facets; the facets of Robinhood Chain and one BNB facet are not verified on an explorer, and their selectors matched the verified ABIs of the same facets on other chains or the repository source. The loupe `facets()` returned Ethereum 42 facets / 152 selectors, Base 26 facets / 105 selectors, Arbitrum 38 facets / 141 selectors, Optimism 36 facets / 135 selectors, Polygon 36 facets / 135 selectors, BNB 36 facets / 126 selectors, Avalanche 34 facets / 116 selectors, Robinhood Chain 7 facets / 34 selectors.
- **Addresses:** the diamond from the Rango docs deployment page and from the loupe; owners read with `owner()` on each chain and existence-checked with `eth_getCode`.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):**

  Logs emitted by the diamond (address-wide `eth_getLogs` scan, every topic0 counted):

  | Event | ETH | Base | Arb | OP | Poly | BNB | Avax | RH |
  |---|---|---|---|---|---|---|---|---|
  | `RangoBridgeInitiated` | 842 | 284 | 257 | 53 | 215 | 2,578 | 38 | 137 |
  | `RangoBridgeInitiated (old, no dAppName)` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | `RangoSwap` | 291 | 156 | 87 | 11 | 62 | 673 | 4 | 658 |
  | `SendToken` | 1,199 | 423 | 314 | 57 | 289 | 2,605 | 28 | 907 |
  | `CallResult` | 291 | 157 | 87 | 11 | 62 | 673 | 4 | 658 |
  | `FeeInfo (new)` | 734 | 211 | 234 | 39 | 205 | 1,886 | 28 | 34 |
  | `FeeInfo (old)` | 217 | 97 | 32 | 11 | 27 | 194 | 0 | 215 |
  | `CCTPBridgeDepositAndBurnDone` | 10 | 0 | 2 | 5 | 1 | 0 | 0 | 0 |
  | `DiamondCut` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | all topics | 3,584 | 1,328 | 1,014 | 187 | 861 | 8,609 | 102 | 2,609 |

  - `bridgeId` of the Ethereum `RangoBridgeInitiated` logs (value, count): 56 (425), 57 (161), 60 (133), 52 (57), 0 (25), 23 (14), 16 (10), 51 (9), 58 (3), 55 (3), 59 (2). Base: 52 (79), 56 (77), 57 (52), 60 (43), 0 (22), 58 (7), 55 (3), 5 (1).
  - `destinationChainId` on Ethereum: 56 (225), 1414680398 (221), 1279348289 (173), 8453 (62), 4346947 (60), 4663 (26), 42161 (21), 137 (9), 5461321 (8), 3 (7).
- **Decoded fields:** every `RangoBridgeInitiated` log of the Ethereum and Base diamonds in the pinned window was decoded for `bridgeId`, `destinationChainId`, `dAppName` and `receiver` (§13).
- **Sample transaction read:** Ethereum `0x236458df89c5193052788746347b5292a9871066e389588617784e264da2c8fa` (`genericBridge`, 0.003717910738096371 ETH `msg.value`; `SendToken` of the native fee to the affiliate, `FeeInfo`, a Relay depository deposit in the same transaction, `RangoBridgeInitiated` with `bridgeId` 56 and `dAppTag` 1197).

Authoritative sources:
- [rango-exchange/rango-contracts-v2](https://github.com/rango-exchange/rango-contracts-v2) (`contracts/rango/RangoDiamond.sol`, `contracts/facets/`, `contracts/libraries/LibSwapper.sol`, `contracts/libraries/LibSwapperV2.sol`, `contracts/interfaces/IRango.sol`)
- Rango docs — [architecture](https://docs.rango.exchange/smart-contracts/architecture) · [deployment addresses](https://docs.rango.exchange/smart-contracts/deployment-addresses) · [message passing](https://docs.rango.exchange/smart-contracts/message-passing)
- Explorers (verified facets) — [RangoDiamond on Etherscan](https://etherscan.io/address/0x69460570c93f9de5e2edbc3052bf10125f0ca22d) · [Blockscout Ethereum](https://eth.blockscout.com/address/0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d) · [Louper (diamond inspector)](https://louper.dev/diamond/0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d?network=mainnet)
