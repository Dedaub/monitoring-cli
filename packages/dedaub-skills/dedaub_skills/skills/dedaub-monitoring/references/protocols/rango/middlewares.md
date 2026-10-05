# Rango Middlewares — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain + Arc)

**Status:** verified on 2026-09-29 against live RPC on the eight original chains (Arc checked on 2026-10-05), `rango-exchange/rango-contracts-v2` (`contracts/facets/base/RangoBaseInterchainMiddleware*.sol`, `contracts/facets/bridges/*Middleware.sol`, `contracts/libraries/LibInterchain*.sol`), the Rango docs (deployment addresses, message passing) and the explorer-verified sources of the deployed middlewares. Topics and selectors recomputed as `keccak256(signature)`; every address existence-checked with `eth_getCode` on all eight chains.
**Scope:** the Rango **middlewares** (the destination "receivers" of routes that carry an interchain message) and the **MiddlewaresWhitelistsStorage** they share: their payout, refund and message events, their bridge entry functions, their admin functions, and their addresses per chain. The diamond is in [diamond.md](diamond.md). Topics and selectors are chain-agnostic; addresses are network-specific.

A middleware is called by the underlying bridge on the destination chain (the Across spoke pool, the CCTP V2 message transmitter through a relayer, the LayerZero endpoint, the Chainflip vault, the deBridge external-call adapter, and so on). It decodes the `RangoInterChainMessage` (`requestId`, destination token, receiver, action), runs the destination swap or dApp call, pays the receiver, and emits `RangoBridgeCompleted` with the source `requestId`. If the swap fails, it pays the bridged token instead and reports the status.

Three facts to know before indexing:

1. **Two address sets.** The Rango docs list one address per middleware for most EVM chains and another for "Ethereum and Optimism (Cancun)". Newer middlewares (CCTP V2, OFT) use one deterministic address on several chains. §3–§10 give the measured presence per chain.
2. **`RangoBridgeCompleted` is the destination record.** topic1 `requestId` (the same as the source `RangoBridgeInitiated`), topic2 `token`, topic3 `originalSender`; data word 0 `receiver`, word 1 `amount`, word 2 `status`, word 3 `dAppTag`. `status`: 0 Succeeded, 1 RefundInSource, 2 RefundInDestination, 3 SwapFailedInDestination.
3. **Most Rango routes never reach a middleware.** Only routes with `hasInterchainMessage` = true do (8 of 842 on the Ethereum diamond and 0 of 284 on the Base diamond in the pinned window).

---

## 0. Contract families & versions

| Middleware | Called by | Entry function | Address sets (docs) |
|------------|-----------|----------------|---------------------|
| RangoAcrossMiddleware | Across spoke pool (whitelisted callers) | handleV3AcrossMessage / handleAcrossMessage | EVM `0xB852e653f8FBC099F06DC9D61E269517a4990B73`, Cancun `0xd5C7176Ec638eF466c2Fee761762d9EAb673997d` |
| RangoCCTPV2Middleware | a relayer with the CCTP V2 message and attestation | callReceiveMessage / processMessageAndTransferUSDC | `0xB5777E29aEEA886537E3fEF1c565F86e2d9760e8` |
| RangoOftMiddleware | LayerZero endpoint (whitelisted OApps) | lzCompose | `0x8B4A4A8b619ff52b0d35F74E4063F76cefCA618F` |
| RangoStargateMiddleware | Stargate router (V1) or LayerZero endpoint (V2) | sgReceive / lzCompose | EVM `0x7045F971e312f7F1e211b3085ACE9155DeB0a976`, Cancun `0x5434eD2d9F5737986858de127545e8a2Fb6EB6aE` |
| RangoSymbiosisMiddleware | Symbiosis gateway | messageReceive | EVM `0x3Caed470a3215a4D6648D5c684c429B7A371C269`, Cancun `0x0b7728E6c51511E30788a3a393A3362d59Ca67Af` |
| RangoSatelliteMiddleware | Axelar gateway | execute / executeWithToken | EVM `0x0ADFb7975aa7c3aD90c57AEa8FDe5E31a721E9bb`, Cancun `0x901D602dCADE00e2d7384e3940a70Ef772A355c3` |
| RangoWormholeMiddleware | a relayer with the Wormhole VAA | completeTransferWithPayload | EVM `0x87f9bE4D0478dF182C95CBBd761381699B334342`, Cancun `0x93310c2A44C0Ea5B5381606d020980CC9B62f547` |
| RangoCBridgeMiddleware | Celer message bus | executeMessageWithTransfer (+ Fallback / Refund) | EVM `0xC1e311c06230C2fAe6425C07bB0a7C5fFCE9C785` |
| RangoChainFlipMiddleware | Chainflip vault | cfReceive | EVM `0x74C670A0BB4668F146FB5b97d0B4EA8eF60986dA`, Cancun `0xB4231156BBF6025745046d9DE642A4eb242cD9ef` |
| RangoDeBridgeMiddleware | deBridge DLN external-call adapter | onERC20Received / onEtherReceived | EVM `0x3Abaeb6399D3fc44838D75b88e642182e4b826fE`, Cancun `0xD9Dc714D617608c273DA943840A17e4F1092D766` |
| RangoConnextMiddleware | Connext bridge | xReceive | EVM `0x4a91efC961913fC24bFAE6BC3Eb5457e34e8F764`, Cancun `0x0F415542e35A05A2655e2b1a0a95FE1cc74e84A3` |
| RangoNitroAssetForwarderMiddleware | Router Nitro asset forwarder | handleMessage | EVM `0xb05233e0779cA7952a27CBFF7c3820CFce9526b3`, Cancun `0x557BaBBa31BE0ca0571CF5dAf44fb8c42Ba10351` |
| RangoMiddlewaresWhitelistsStorage | — | — (whitelists, pause, diamond address) |  |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Payout, refund and message events

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x98970fb6752fa5c55ab7355a52caf0811312939be1b8fc26b0305fe02224c652` | `ActionDone(uint8 actionType, address contractAddress, bool success, string reason)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0x1cbe9d2f9c17d230efb5c6ed6065b9872001bf185d0c6bdd82b60fe57e84cbbe` | `CBridgeIMStatusUpdated(bytes32 id, address token, uint256 outputAmount, uint8 status, address destination)` | CBridge |
| `0xb82ab614e05585ddbdff921ec7c00df0c150470292b0f063d8839ea6928f669d` | `CBridgeSend(address receiver, address token, uint256 amount, uint64 dstChainId, uint64 nonce, uint32 maxSlippage)` | CBridge |
| `0xfe3b53aeaf88b6a28abd020460eefc20897bd3db095a4b8b21a7b9007cf52ef7` | `CrossChainMessageCalled(address _receiverContract, address _token, uint256 _amount, uint8 _status, bytes _appMessage, bool success, string failReason)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0x96475a3e1ba67b38af103e210b5d41e9c22f60746ecd5f221d6f2284f45b26f6` | `PayloadHashRefunded(bytes32 indexed refundHash, address refundAddress)` | Satellite, Wormhole |
| `0x71e2229d8c5917bef9d5c3b4b1df412ba65253373b25d1c117223dbaaaa7c8d8` | `RangoBridgeCompleted(address indexed requestId, address indexed token, address indexed originalSender, address receiver, uint256 amount, uint8 status, uint16 dAppTag)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0x012c155f3836c4edb9222305b909a109f9efa46288efffe40a0e66da3a9a9800` | `RangoBridgeInitiated(address indexed requestId, address bridgeToken, uint256 bridgeAmount, address receiver, uint256 destinationChainId, bool hasInterchainMessage, bool hasDestinationSwap, uint8 indexed bridgeId, uint16 indexed dAppTag, string dAppName)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0xdc5736cbc70c0769c8938a6a3bf69a501b964ef916f1c25ae96d934ef9a10c3e` | `RangoUserRefunded(address indexed user, address token, uint256 indexed amount)` | CCTPV2 |
| `0xadddb5de0e3d0908d05874317a41a5257f830e62d84f3da6e00b4d32f4f82537` | `RefundHashStateUpdated(bytes32 indexed refundHash, bool enabled, address refundAddress)` | Satellite, Wormhole |
| `0xd7dee2702d63ad89917b6a4da9981c90c4d24f8c2bdfd64c604ecae57d8d0651` | `Refunded(address _token, uint256 _amount)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0xdf4363408b2d9811d1e5c23efdb5bae0b7a68bd9de2de1cbae18a11be3e67ef5` | `SendToken(address _token, uint256 _amount, address _receiver)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0x13fee4cd47ddae5c78a79ac9e0f49f3bc079fd45b98cb6bf0a8698624a7cc0bd` | `SubActionDone(uint8 subActionType, address contractAddress, bool success, string reason)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0xe1cdc506b86cc05898c568c4ae5eb4f1d110f20840d600bb3b426c4deb5c9a62` | `SymbiosisSwapStatusUpdated(address token, uint256 outputAmount, uint8 status, address source, address destination)` | Symbiosis |

- `SendToken` (middleware) is the payout transfer record; the ERC-20 `Transfer` middleware → receiver is in the same transaction.
- `CrossChainMessageCalled` reports the call of the dApp contract of a message route; `ActionDone` / `SubActionDone` report the destination swap and the post-action.
- `Refunded` is an owner rescue from the middleware; `RangoUserRefunded` (CCTP V2) is a refund to the user.
- `RefundHashStateUpdated` / `PayloadHashRefunded` (Satellite, Wormhole) manage refunds of stuck messages by payload hash.

### 1.2 Admin and configuration events

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xf5da36b087bd0d0f4109d09e657da656ffbcb920539a3c66ffe4c2c005572d11` | `AcrossWhitelistedCallersAdded(address[] _addresses)` | Across |
| `0x8959875821433a4ccb2231edc366855c68f44b4a4f0ee5b9a1be9a77cd31c79e` | `AcrossWhitelistedCallersRemoved(address[] _addresses)` | Across |
| `0xa9d7ede4051cd51e676a40194e8854cbdc3238a26c45bc0f8c1bb24ca01780b7` | `CBridgeAddressUpdated(address oldAddress, address newAddress)` | CBridge |
| `0x90f75f84ddafc026cf92b6d067e74b76b536e7421e7e4c73d1edef5d14a4d0e2` | `ChainFlipWhitelistedCallersAdded(address[] _addresses)` | ChainFlip |
| `0x1b56ed3908fd7beb277ebe6ca6a7dc9fc32187c7e38cb857fa9f6de17f562c22` | `ChainFlipWhitelistedCallersRemoved(address[] _addresses)` | ChainFlip |
| `0xc8d9be95e6186a3f2176c058d605c1894d88a4201acedeb1a29bc5295088f7f2` | `ConnextBridgeAddressUpdated(address oldAddress, address newAddress)` | Connext |
| `0xfb00f7adc91459b5048ecdc60b783959a583bafb1e3041f3e1f017540a0e47d3` | `ContractBlacklisted(address _contractAddress)` | sMiddleware whitelists storage |
| `0xb7269578552456138d47dc37471d94886205143f138387446eff0148047965f6` | `ContractWhitelisted(address _contractAddress)` | sMiddleware whitelists storage |
| `0x5b9324467146d7a472a33d1d592dba762cdea1dbc98111745935e5e1984f6016` | `DlnExtCallAdapterAddressUpdated(address _oldAddress, address _newAddress)` | DeBridge |
| `0x3f8223bcd8b3b875473e9f9e14e1ad075451a2b5ffd31591655da9a01516bf5e` | `MessageBusUpdated(address messageBus)` | CBridge |
| `0x9504779dcbafef71cf1ff8c61ed703b26a971d365c0a760f22458145990afd99` | `MessageTransmitterV2AddressUpdated(address _oldAddress, address _newAddress)` | CCTPV2 |
| `0x5276dbc01d9903b8a77951393384788da9d9e89410a1a5e89fb9aacd7a1bfb08` | `MessagingDAppBlacklisted(address _DApp)` | sMiddleware whitelists storage |
| `0x15d897562fef1ba129ba167650a82269469efce20aece13fe277d18a02fdd0a6` | `MessagingDAppWhitelisted(address _DApp)` | sMiddleware whitelists storage |
| `0x6e800a0218388799ae51e714b3917e21b38b5b7f368ab34f94bdfa80238a9bd7` | `NitroAssetForwarderAddressUpdated(address _oldAddress, address _newAddress)` | NitroAssetForwarder |
| `0xe34613ac0058c39c3f6a39c5e5af689e78441af4065629dc8e8938c9c1ff5f4a` | `OappsRemoved(address[] oapps)` | Oft |
| `0x38b54b12961757186642c5b98decb72c28b6907af64c8e9369209a9aa1b95571` | `OappsWhitelisted((address oApp, address token)[] oapps)` | Oft |
| `0xb474579ebf3a761ca65519e5f72da75e4f33c1eb213fb424fa9c102eab7db92a` | `OftEndpointAddressUpdated(address oldAddress, address newAddress)` | Oft |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole, sMiddleware whitelists storage |
| `0xbfe19c616282c006fd97e57c7fc8eb0e16d0399422c333ccce7bc72f3a1ac843` | `PausedStateUpdated(bool _oldPausedState, bool _newPausedState, address indexed _middlewareAddress)` | sMiddleware whitelists storage |
| `0xde99b0d1dabdadb73ebd7438dd737500ed3a596a247ba47febd9108f98c11174` | `RangoDiamondAddressUpdated(address _oldAddress, address _newAddress)` | sMiddleware whitelists storage |
| `0xc5474af28634e5155be634ccaea8d3e9e77344679b451d664aef7e190a1ba17e` | `SatelliteGatewayAddressUpdated(address _oldAddress, address _newAddress)` | Satellite |
| `0xd2960b2623fc8f0add618752eaed1adc3004920a364b22d2bc04614510dfe1a1` | `StargateComposerAddressUpdated(address oldComposerAddress, address newComposerAddress, address oldSgethAddress, address newSgethAddress)` | Stargate |
| `0x3d13765045a05885759e076f11c5ef9b847a0bab5d437eb9b806f64a8158f439` | `StargateV2TreasurerAndEndpointAddressUpdated(address oldTreasurerAddress, address newTreasurerAddress, address oldEndpointAddress, address newEndpointAddress)` | Stargate |
| `0x76e986cd13bf71a8a240988fea38de00b0de8942adfc6b939d507554c750a723` | `SymbiosisAddressUpdated(address oldMetaRouter, address oldMetaRouterGateway, address indexed newMetaRouter, address indexed newMetaRouterGateway)` | Symbiosis |
| `0xec9fc77409b3224e46d50b2e92ab7ae0b43f0cb85d9743888276f56d73ed6b51` | `WethAddressUpdated(address _oldAddress, address _newAddress)` | sMiddleware whitelists storage |
| `0xa24130b75a8bf66270e29156ab91ec1ee3df62d286ceb96fd86523682923a38c` | `WhitelistStorageAddressUpdated(address _oldAddress, address _newAddress)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0x75704d0ba64cb627dbf74bb16de0bbae244e187e80d754a6fd221f0066708883` | `WormholeRouterAddressUpdated(address oldAddress, address newAddress)` | Wormhole |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Bridge entry points (called by the underlying bridge or its relayer)

| Selector | Signature | Middleware |
|----------|-----------|------------|
| `0x25ba5540` | `RefundWithPayloadAndSend(bytes vaas, address expectedToken, address refundAddr, uint256 amount)` | Wormhole |
| `0xf44452f1` | `callReceiveMessage(bytes message, bytes signature)` | CCTPV2 |
| `0x4904ac5f` | `cfReceive(uint32 srcChain, bytes srcAddress, bytes message, address token, uint256 amount)` | ChainFlip |
| `0xfeac30f1` | `completeTransferWithPayload(address expectedToken, bytes vaas)` | Wormhole |
| `0x5e3c1dad` | `doCBridgeIM(address fromToken, uint256 inputAmount, address receiverContract, uint64 dstChainId, uint64 nonce, uint32 maxSlippage, uint256 sgnFee, (address requestId, uint64 dstChainId, address bridgeRealOutput, address toToken, address originalSender, address recipient, uint8 actionType, bytes action, uint8 postAction, uint16 dAppTag, bytes dAppMessage, address dAppSourceContract, address dAppDestContract) imMessage)` | CBridge |
| `0xec77c9ce` | `doSend(address receiver, address token, uint256 amount, uint64 dstChainId, uint64 nonce, uint32 maxSlippage)` | CBridge |
| `0x49160658` | `execute(bytes32 commandId, string sourceChain, string sourceAddress, bytes payload)` | Satellite |
| `0x9c649fdf` | `executeMessage(address _sender, uint64 _srcChainId, bytes _message, address _executor)` | CBridge |
| `0x7cd2bffc` | `executeMessageWithTransfer(address, address token, uint256 amount, uint64 srcChainId, bytes message, address)` | CBridge |
| `0x5ab7afc6` | `executeMessageWithTransferFallback(address, address token, uint256 amount, uint64 srcChainId, bytes message, address)` | CBridge |
| `0x0bcb4982` | `executeMessageWithTransferRefund(address token, uint256 amount, bytes message, address)` | CBridge |
| `0x1a98b2e0` | `executeWithToken(bytes32 commandId, string sourceChain, string sourceAddress, bytes payload, string tokenSymbol, uint256 amount)` | Satellite |
| `0xfab7e159` | `fetchTokenFromRouterAndRefund(address _tokenAddress, uint256 _amount, address _refundReceiver)` | Symbiosis |
| `0x0ea1f938` | `handleAcrossMessage(address tokenSent, uint256 amount, bool fillCompleted, address relayer, bytes message)` | Across |
| `0xd00a2d5f` | `handleMessage(address tokenSent, uint256 amount, bytes message)` | NitroAssetForwarder |
| `0x3a5be8cb` | `handleV3AcrossMessage(address tokenSent, uint256 amount, address relayer, bytes message)` | Across |
| `0xd0a10260` | `lzCompose(address _oApp, bytes32, bytes _message, address, bytes)` | Oft, Stargate |
| `0x685a302c` | `messageReceive(uint256 amount, address token, (address requestId, uint64 dstChainId, address bridgeRealOutput, address toToken, address originalSender, address recipient, uint8 actionType, bytes action, uint8 postAction, uint16 dAppTag, bytes dAppMessage, address dAppSourceContract, address dAppDestContract) receivedMessage)` | Symbiosis |
| `0x7cbf7a55` | `onERC20Received(bytes32 _orderId, address _token, uint256 _transferredAmount, address _fallbackAddress, bytes _payload)` | DeBridge |
| `0x3d266812` | `onEtherReceived(bytes32 _orderId, address _fallbackAddress, bytes _payload)` | DeBridge |
| `0xf5bf4d63` | `processMessageAndTransferUSDC(bytes message, bytes signature, address _recipient, address _mintToken, uint256 _amount)` | CCTPV2 |
| `0xab8236f3` | `sgReceive(uint16, bytes, uint256, address _token, uint256 amountLD, bytes payload)` | Stargate |
| `0xfd614f41` | `xReceive(bytes32 _transferId, uint256 _amount, address _asset, address _originSender, uint32 _origin, bytes _callData)` | Connext |

### 2.2 Admin and configuration

| Selector | Signature | Middleware |
|----------|-----------|------------|
| `0x129f5a96` | `addAcrossWhitelistedCallers(address[] _addresses)` | Across |
| `0x18379fbb` | `addChainFlipWhitelistedCallers(address[] _addresses)` | ChainFlip |
| `0x6566f30a` | `addMessagingDApp(address _dapp)` | sMiddleware whitelists storage |
| `0x100c393f` | `addMessagingDApps(address[] DApps)` | sMiddleware whitelists storage |
| `0xf80f5dd5` | `addWhitelist(address contractAddress)` | sMiddleware whitelists storage |
| `0x4d0d594a` | `addWhitelistedOapps((address oApp, address token)[] newWhitelistedOapps)` | Oft |
| `0xc8eaf28f` | `addWhitelists(address[] contractAddresses)` | sMiddleware whitelists storage |
| `0x38ecd34e` | `changePauseState(bool _paused, address _middlewareAddress)` | sMiddleware whitelists storage |
| `0xacca1854` | `changePauseState(bool _paused, address[] _middlewareAddresses)` | sMiddleware whitelists storage |
| `0xe37bbeed` | `initAcrossMiddleware(address _owner, address[] _whitelistedCallers, address whitelistsContract)` | Across |
| `0x5517c10a` | `initBaseMiddleware(address _owner, address _whitelistsContract)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0x7b92b679` | `initCBridgeMiddleware(address _owner, address _cBridgeAddress, address _cBridgeMessageBusAddress, address whitelistsContract)` | CBridge |
| `0x45ac8047` | `initCCTPV2Middleware(address _owner, address _messageTransmitterV2, address _tokenMinterV2, address whitelistsContract)` | CCTPV2 |
| `0xefff605d` | `initChainFlipMiddleware(address _owner, address[] _whitelistedCallers, address whitelistsContract)` | ChainFlip |
| `0xd7ae1909` | `initConnextMiddleware(address _owner, address _connextBridge, address _whitelistsContract)` | Connext |
| `0xe62aaf0f` | `initDeBridgeMiddleware(address _owner, address _whitelistsContract, address _dlnExtCallAdapterAddress)` | DeBridge |
| `0x6655c8b9` | `initMiddlewaresWhitelistsStorage(address _owner, address _rangoDiamond, address _weth, address[] _whitelistContracts, address[] _whitelistDApps)` | sMiddleware whitelists storage |
| `0xf03f3221` | `initNitroAssetForwarderMiddleware(address _owner, address _nitroAssetForwarder, address whitelistsContract)` | NitroAssetForwarder |
| `0x8393bf72` | `initOftMiddleware(address _owner, address _oftEndpoint, (address oApp, address token)[] _whitelistedOapps, address _whitelistsContract)` | Oft |
| `0x335c05c8` | `initSatelliteMiddleware(address _owner, address _gatewayAddress, address whitelistsContract)` | Satellite |
| `0xd93e317a` | `initStargateMiddleware(address _owner, address _stargateComposer, address _whitelistsContract, address _sgeth, address _stargateV2Treasurer, address _stargateV2Endpoint)` | Stargate |
| `0x59fba66b` | `initSymbiosisMiddleware(address _owner, address _gatewayAddress, address _routerAddress, address whitelistsContract)` | Symbiosis |
| `0x825cd248` | `initWormholeMiddleware(address _owner, address _wormholeRouter, address whitelistsContract)` | Wormhole |
| `0x410085df` | `refund(address _tokenAddress, uint256 _amount)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0x9fae52e6` | `refundNative(uint256 _amount)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0x323c79ec` | `removeAcrossWhitelistedCallers(address[] _addresses)` | Across |
| `0x1da944c8` | `removeChainFlipWhitelistedCallers(address[] _addresses)` | ChainFlip |
| `0xd4ec5265` | `removeMessagingDApp(address _dapp)` | sMiddleware whitelists storage |
| `0x78c8cda7` | `removeWhitelist(address contractAddress)` | sMiddleware whitelists storage |
| `0x0e53f03c` | `removeWhitelistedOapps(address[] oappsToRemove)` | Oft |
| `0x547cad12` | `setMessageBus(address _messageBus)` | CBridge |
| `0xdae03389` | `updateCBridgeAddress(address newAddress)` | CBridge |
| `0xf97e7782` | `updateConnextBridgeAddress(address newAddress)` | Connext |
| `0xb6a4b8a6` | `updateDlnExtCallAdapterAddress(address _address)` | DeBridge |
| `0x8d7f3ada` | `updateMessageTransmitterV2(address _address)` | CCTPV2 |
| `0xc246797a` | `updateNitroAssetForwarder(address _nitroAssetForwarder)` | NitroAssetForwarder |
| `0xd162e5a9` | `updateOftEndpoint(address newEndpoint)` | Oft |
| `0x880cdc31` | `updateOwner(address newAddress)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole, sMiddleware whitelists storage |
| `0x3ff81ddd` | `updateRangoDiamond(address _rangoDiamond)` | sMiddleware whitelists storage |
| `0x9e081a10` | `updateRefundHashes(bytes32[] hashes, bool[] booleans, address[] addresses)` | Satellite, Wormhole |
| `0x59c94b37` | `updateSatelliteGatewayAddress(address _address)` | Satellite |
| `0x2e369cf2` | `updateStargateComposer(address newComposerAddress)` | Stargate |
| `0xf1409aaf` | `updateStargateV2TreasurerAndEndpoint(address newTreasurerAddress, address newEndpointAddress)` | Stargate |
| `0x8648ba08` | `updateStargetSGETH(address sgethAddress)` | Stargate |
| `0x00b688d1` | `updateSymbiosisGatewayAddress(address metaRouter, address metaRouterGateway)` | Symbiosis |
| `0x875655dd` | `updateTokenMinterV2(address _address)` | CCTPV2 |
| `0x1b5ad801` | `updateWeth(address _weth)` | sMiddleware whitelists storage |
| `0xcb369ae7` | `updateWhitelistsContractAddress(address newAddress)` | Across, CBridge, CCTPV2, ChainFlip, Connext, DeBridge, NitroAssetForwarder, Oft, Satellite, Stargate, Symbiosis, Wormhole |
| `0x386e9f5f` | `updateWormholeRouter(address newAddress)` | Wormhole |

---

## 3. Addresses — Ethereum (chain ID 1)

Every documented address of every middleware was checked with `eth_getCode` on this chain (runtime size in bytes).

| Middleware | Address | Code |
|------------|---------|------|
| RangoAcrossMiddleware (Cancun set) | `0xd5C7176Ec638eF466c2Fee761762d9EAb673997d` | 17,462 |
| RangoCCTPV2Middleware | `0xB5777E29aEEA886537E3fEF1c565F86e2d9760e8` | 19,689 |
| RangoOftMiddleware | `0x8B4A4A8b619ff52b0d35F74E4063F76cefCA618F` | 16,073 |
| RangoStargateMiddleware (Cancun set) | `0x5434eD2d9F5737986858de127545e8a2Fb6EB6aE` | 18,153 |
| RangoSymbiosisMiddleware (Cancun set) | `0x0b7728E6c51511E30788a3a393A3362d59Ca67Af` | 16,076 |
| RangoSatelliteMiddleware (Cancun set) | `0x901D602dCADE00e2d7384e3940a70Ef772A355c3` | 19,059 |
| RangoWormholeMiddleware (Cancun set) | `0x93310c2A44C0Ea5B5381606d020980CC9B62f547` | 22,224 |
| RangoChainFlipMiddleware (Cancun set) | `0xB4231156BBF6025745046d9DE642A4eb242cD9ef` | 16,536 |
| RangoDeBridgeMiddleware (Cancun set) | `0xD9Dc714D617608c273DA943840A17e4F1092D766` | 16,725 |
| RangoConnextMiddleware (Cancun set) | `0x0F415542e35A05A2655e2b1a0a95FE1cc74e84A3` | 15,981 |
| RangoNitroAssetForwarderMiddleware (Cancun set) | `0x557BaBBa31BE0ca0571CF5dAf44fb8c42Ba10351` | 15,928 |
| RangoMiddlewaresWhitelistsStorage (Cancun set) | `0x89fE77AF04DB303d612D7e7F4C1c5E8664EDbEf6` | 5,874 |

No code at any documented address on Ethereum: RangoCBridgeMiddleware.

## 4. Addresses — Base (chain ID 8453)

Every documented address of every middleware was checked with `eth_getCode` on this chain (runtime size in bytes).

| Middleware | Address | Code |
|------------|---------|------|
| RangoAcrossMiddleware (EVM set) | `0xB852e653f8FBC099F06DC9D61E269517a4990B73` | 17,851 |
| RangoCCTPV2Middleware | `0xB5777E29aEEA886537E3fEF1c565F86e2d9760e8` | 19,689 |
| RangoStargateMiddleware (EVM set) | `0x7045F971e312f7F1e211b3085ACE9155DeB0a976` | 18,538 |
| RangoSymbiosisMiddleware (EVM set) | `0x3Caed470a3215a4D6648D5c684c429B7A371C269` | 16,427 |
| RangoSatelliteMiddleware (EVM set) | `0x0ADFb7975aa7c3aD90c57AEa8FDe5E31a721E9bb` | 19,485 |
| RangoWormholeMiddleware (EVM set) | `0x87f9bE4D0478dF182C95CBBd761381699B334342` | 22,713 |
| RangoDeBridgeMiddleware (EVM set) | `0x3Abaeb6399D3fc44838D75b88e642182e4b826fE` | 17,088 |
| RangoConnextMiddleware (EVM set) | `0x4a91efC961913fC24bFAE6BC3Eb5457e34e8F764` | 16,335 |
| RangoNitroAssetForwarderMiddleware (EVM set) | `0xb05233e0779cA7952a27CBFF7c3820CFce9526b3` | 16,282 |
| RangoMiddlewaresWhitelistsStorage (EVM set) | `0x0484962f4Ff892Ee5608BE5eC80e2f461624a87C` | 5,927 |

No code at any documented address on Base: RangoOftMiddleware, RangoCBridgeMiddleware, RangoChainFlipMiddleware.

## 5. Addresses — Arbitrum One (chain ID 42161)

Every documented address of every middleware was checked with `eth_getCode` on this chain (runtime size in bytes).

| Middleware | Address | Code |
|------------|---------|------|
| RangoAcrossMiddleware (EVM set) | `0xB852e653f8FBC099F06DC9D61E269517a4990B73` | 17,851 |
| RangoCCTPV2Middleware | `0xB5777E29aEEA886537E3fEF1c565F86e2d9760e8` | 19,689 |
| RangoOftMiddleware | `0x8B4A4A8b619ff52b0d35F74E4063F76cefCA618F` | 16,073 |
| RangoStargateMiddleware (EVM set) | `0x7045F971e312f7F1e211b3085ACE9155DeB0a976` | 18,538 |
| RangoSymbiosisMiddleware (EVM set) | `0x3Caed470a3215a4D6648D5c684c429B7A371C269` | 16,427 |
| RangoSatelliteMiddleware (EVM set) | `0x0ADFb7975aa7c3aD90c57AEa8FDe5E31a721E9bb` | 19,485 |
| RangoWormholeMiddleware (EVM set) | `0x87f9bE4D0478dF182C95CBBd761381699B334342` | 22,713 |
| RangoCBridgeMiddleware (EVM set) | `0xC1e311c06230C2fAe6425C07bB0a7C5fFCE9C785` | 22,018 |
| RangoChainFlipMiddleware (EVM set) | `0x74C670A0BB4668F146FB5b97d0B4EA8eF60986dA` | 16,915 |
| RangoDeBridgeMiddleware (EVM set) | `0x3Abaeb6399D3fc44838D75b88e642182e4b826fE` | 17,088 |
| RangoConnextMiddleware (EVM set) | `0x4a91efC961913fC24bFAE6BC3Eb5457e34e8F764` | 16,335 |
| RangoNitroAssetForwarderMiddleware (EVM set) | `0xb05233e0779cA7952a27CBFF7c3820CFce9526b3` | 16,282 |
| RangoMiddlewaresWhitelistsStorage (EVM set) | `0x0484962f4Ff892Ee5608BE5eC80e2f461624a87C` | 5,927 |

Every middleware has code on Arbitrum.

## 6. Addresses — Optimism (chain ID 10)

Every documented address of every middleware was checked with `eth_getCode` on this chain (runtime size in bytes).

| Middleware | Address | Code |
|------------|---------|------|
| RangoAcrossMiddleware (Cancun set) | `0xd5C7176Ec638eF466c2Fee761762d9EAb673997d` | 17,462 |
| RangoCCTPV2Middleware | `0xB5777E29aEEA886537E3fEF1c565F86e2d9760e8` | 19,689 |
| RangoOftMiddleware | `0x8B4A4A8b619ff52b0d35F74E4063F76cefCA618F` | 16,073 |
| RangoStargateMiddleware (Cancun set) | `0x5434eD2d9F5737986858de127545e8a2Fb6EB6aE` | 18,153 |
| RangoSymbiosisMiddleware (Cancun set) | `0x0b7728E6c51511E30788a3a393A3362d59Ca67Af` | 16,076 |
| RangoSatelliteMiddleware (Cancun set) | `0x901D602dCADE00e2d7384e3940a70Ef772A355c3` | 19,059 |
| RangoWormholeMiddleware (Cancun set) | `0x93310c2A44C0Ea5B5381606d020980CC9B62f547` | 22,224 |
| RangoDeBridgeMiddleware (Cancun set) | `0xD9Dc714D617608c273DA943840A17e4F1092D766` | 16,725 |
| RangoConnextMiddleware (Cancun set) | `0x0F415542e35A05A2655e2b1a0a95FE1cc74e84A3` | 15,981 |
| RangoNitroAssetForwarderMiddleware (Cancun set) | `0x557BaBBa31BE0ca0571CF5dAf44fb8c42Ba10351` | 15,928 |
| RangoMiddlewaresWhitelistsStorage (Cancun set) | `0x89fE77AF04DB303d612D7e7F4C1c5E8664EDbEf6` | 5,874 |

No code at any documented address on Optimism: RangoCBridgeMiddleware, RangoChainFlipMiddleware.

## 7. Addresses — Polygon PoS (chain ID 137)

Every documented address of every middleware was checked with `eth_getCode` on this chain (runtime size in bytes).

| Middleware | Address | Code |
|------------|---------|------|
| RangoAcrossMiddleware (EVM set) | `0xB852e653f8FBC099F06DC9D61E269517a4990B73` | 17,851 |
| RangoCCTPV2Middleware | `0xB5777E29aEEA886537E3fEF1c565F86e2d9760e8` | 19,689 |
| RangoOftMiddleware | `0x8B4A4A8b619ff52b0d35F74E4063F76cefCA618F` | 16,073 |
| RangoStargateMiddleware (EVM set) | `0x7045F971e312f7F1e211b3085ACE9155DeB0a976` | 18,538 |
| RangoSymbiosisMiddleware (EVM set) | `0x3Caed470a3215a4D6648D5c684c429B7A371C269` | 16,427 |
| RangoSatelliteMiddleware (EVM set) | `0x0ADFb7975aa7c3aD90c57AEa8FDe5E31a721E9bb` | 19,485 |
| RangoWormholeMiddleware (EVM set) | `0x87f9bE4D0478dF182C95CBBd761381699B334342` | 22,713 |
| RangoCBridgeMiddleware (EVM set) | `0xC1e311c06230C2fAe6425C07bB0a7C5fFCE9C785` | 22,018 |
| RangoDeBridgeMiddleware (EVM set) | `0x3Abaeb6399D3fc44838D75b88e642182e4b826fE` | 17,088 |
| RangoConnextMiddleware (EVM set) | `0x4a91efC961913fC24bFAE6BC3Eb5457e34e8F764` | 16,335 |
| RangoNitroAssetForwarderMiddleware (EVM set) | `0xb05233e0779cA7952a27CBFF7c3820CFce9526b3` | 16,282 |
| RangoMiddlewaresWhitelistsStorage (EVM set) | `0x0484962f4Ff892Ee5608BE5eC80e2f461624a87C` | 5,927 |
| RangoMiddlewaresWhitelistsStorage (Cancun set) | `0x89fE77AF04DB303d612D7e7F4C1c5E8664EDbEf6` | 5,874 |

No code at any documented address on Polygon: RangoChainFlipMiddleware.

## 8. Addresses — BNB Smart Chain (chain ID 56)

Every documented address of every middleware was checked with `eth_getCode` on this chain (runtime size in bytes).

| Middleware | Address | Code |
|------------|---------|------|
| RangoOftMiddleware | `0x8B4A4A8b619ff52b0d35F74E4063F76cefCA618F` | 16,073 |
| RangoStargateMiddleware (EVM set) | `0x7045F971e312f7F1e211b3085ACE9155DeB0a976` | 18,538 |
| RangoSymbiosisMiddleware (EVM set) | `0x3Caed470a3215a4D6648D5c684c429B7A371C269` | 16,427 |
| RangoSatelliteMiddleware (EVM set) | `0x0ADFb7975aa7c3aD90c57AEa8FDe5E31a721E9bb` | 19,485 |
| RangoWormholeMiddleware (EVM set) | `0x87f9bE4D0478dF182C95CBBd761381699B334342` | 22,713 |
| RangoCBridgeMiddleware (EVM set) | `0xC1e311c06230C2fAe6425C07bB0a7C5fFCE9C785` | 22,018 |
| RangoDeBridgeMiddleware (EVM set) | `0x3Abaeb6399D3fc44838D75b88e642182e4b826fE` | 17,088 |
| RangoConnextMiddleware (EVM set) | `0x4a91efC961913fC24bFAE6BC3Eb5457e34e8F764` | 16,335 |
| RangoNitroAssetForwarderMiddleware (EVM set) | `0xb05233e0779cA7952a27CBFF7c3820CFce9526b3` | 16,282 |
| RangoMiddlewaresWhitelistsStorage (EVM set) | `0x0484962f4Ff892Ee5608BE5eC80e2f461624a87C` | 5,927 |

No code at any documented address on BNB: RangoAcrossMiddleware, RangoCCTPV2Middleware, RangoChainFlipMiddleware.

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

Every documented address of every middleware was checked with `eth_getCode` on this chain (runtime size in bytes).

| Middleware | Address | Code |
|------------|---------|------|
| RangoCCTPV2Middleware | `0xB5777E29aEEA886537E3fEF1c565F86e2d9760e8` | 19,689 |
| RangoOftMiddleware | `0x8B4A4A8b619ff52b0d35F74E4063F76cefCA618F` | 16,073 |
| RangoStargateMiddleware (EVM set) | `0x7045F971e312f7F1e211b3085ACE9155DeB0a976` | 18,538 |
| RangoSymbiosisMiddleware (EVM set) | `0x3Caed470a3215a4D6648D5c684c429B7A371C269` | 16,427 |
| RangoSatelliteMiddleware (EVM set) | `0x0ADFb7975aa7c3aD90c57AEa8FDe5E31a721E9bb` | 19,485 |
| RangoWormholeMiddleware (EVM set) | `0x87f9bE4D0478dF182C95CBBd761381699B334342` | 22,713 |
| RangoCBridgeMiddleware (EVM set) | `0xC1e311c06230C2fAe6425C07bB0a7C5fFCE9C785` | 22,018 |
| RangoDeBridgeMiddleware (EVM set) | `0x3Abaeb6399D3fc44838D75b88e642182e4b826fE` | 17,088 |
| RangoNitroAssetForwarderMiddleware (EVM set) | `0xb05233e0779cA7952a27CBFF7c3820CFce9526b3` | 16,282 |
| RangoMiddlewaresWhitelistsStorage (EVM set) | `0x0484962f4Ff892Ee5608BE5eC80e2f461624a87C` | 5,927 |

No code at any documented address on Avalanche: RangoAcrossMiddleware, RangoChainFlipMiddleware, RangoConnextMiddleware.

## 10. Addresses — Robinhood Chain (chain ID 4663) and Arc (chain ID 5042)

Every documented address of every middleware was checked with `eth_getCode` on this chain (runtime size in bytes).

| Middleware | Address | Code |
|------------|---------|------|

No code at any documented address on Robinhood Chain: RangoAcrossMiddleware, RangoCCTPV2Middleware, RangoOftMiddleware, RangoStargateMiddleware, RangoSymbiosisMiddleware, RangoSatelliteMiddleware, RangoWormholeMiddleware, RangoCBridgeMiddleware, RangoChainFlipMiddleware, RangoDeBridgeMiddleware, RangoConnextMiddleware, RangoNitroAssetForwarderMiddleware, RangoMiddlewaresWhitelistsStorage.

Arc (2026-10-05, `https://rpc.mainnet.arc.io`): the same result. No documented middleware address and no whitelists storage has code. Routes to Arc end with the underlying bridge's payout.

---

## 11. Cross-chain summary

| Middleware | ETH | Base | Arb | OP | Poly | BNB | Avax | RH | Arc |
|------------|-----|------|-----|----|------|-----|------|----|-----|
| RangoAcrossMiddleware | Cancun | EVM | EVM | Cancun | EVM | — | — | — | — |
| RangoCCTPV2Middleware | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | — |
| RangoOftMiddleware | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| RangoStargateMiddleware | Cancun | EVM | EVM | Cancun | EVM | EVM | EVM | — | — |
| RangoSymbiosisMiddleware | Cancun | EVM | EVM | Cancun | EVM | EVM | EVM | — | — |
| RangoSatelliteMiddleware | Cancun | EVM | EVM | Cancun | EVM | EVM | EVM | — | — |
| RangoWormholeMiddleware | Cancun | EVM | EVM | Cancun | EVM | EVM | EVM | — | — |
| RangoCBridgeMiddleware | — | — | EVM | — | EVM | EVM | EVM | — | — |
| RangoChainFlipMiddleware | Cancun | — | EVM | — | — | — | — | — | — |
| RangoDeBridgeMiddleware | Cancun | EVM | EVM | Cancun | EVM | EVM | EVM | — | — |
| RangoConnextMiddleware | Cancun | EVM | EVM | Cancun | EVM | EVM | — | — | — |
| RangoNitroAssetForwarderMiddleware | Cancun | EVM | EVM | Cancun | EVM | EVM | EVM | — | — |
| RangoMiddlewaresWhitelistsStorage | Cancun | EVM | EVM | Cancun | EVM/Cancun | EVM | EVM | — | — |

Cell = the address set that has code on that chain (`EVM`, `Cancun`, or the single address of the newer middlewares); — = no code at any documented address. The docs' table gives the CBridgeMiddleware Cancun address as `0x89fE77AF04DB303d612D7e7F4C1c5E8664EDbEf6`, which is the MiddlewaresWhitelistsStorage (verified name on Ethereum); no CBridgeMiddleware was found on Ethereum or Optimism.

---

## 12. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| All middlewares and the whitelists storage | Immutable, no proxy | EIP-1967 implementation slot empty (code check). They have `init*` functions but are plain deployments. | `owner` (`updateOwner`); new logic = a new middleware address, registered in the whitelists storage. |

---

## 13. Detection invariants & gotchas

1. **Destination payout = `RangoBridgeCompleted` at a middleware**, with the payout `Transfer` in the same transaction. Join to the source by `requestId`.
2. **`status` tells refund from success.** A `RangoBridgeCompleted` with `status` 2 or 3 is still a payout to the user on the destination, in the bridged token.
3. **`originalSender` is the source user**, carried in the message; `tx.from` is a relayer.
4. **Key on `(chain, address)`.** The same middleware name has different addresses on Ethereum/Optimism and on the other chains; the newer middlewares share one address.
5. **Admin triggers.** `OwnershipTransferred`, `WhitelistStorageAddressUpdated`, `PausedStateUpdated` (storage, per middleware), `ContractWhitelisted`, `MessagingDAppWhitelisted`, `RangoDiamondAddressUpdated`, and the bridge-address update events.

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_RANGO_BRIDGE_COMPLETED          = '\x71e2229d8c5917bef9d5c3b4b1df412ba65253373b25d1c117223dbaaaa7c8d8'
TOPIC_RANGO_SEND_TOKEN                = '\xdf4363408b2d9811d1e5c23efdb5bae0b7a68bd9de2de1cbae18a11be3e67ef5'
TOPIC_RANGO_CROSS_CHAIN_MESSAGE_CALLED = '\xfe3b53aeaf88b6a28abd020460eefc20897bd3db095a4b8b21a7b9007cf52ef7'
TOPIC_RANGO_ACTION_DONE               = '\x98970fb6752fa5c55ab7355a52caf0811312939be1b8fc26b0305fe02224c652'
TOPIC_RANGO_SUB_ACTION_DONE           = '\x13fee4cd47ddae5c78a79ac9e0f49f3bc079fd45b98cb6bf0a8698624a7cc0bd'
TOPIC_RANGO_REFUNDED                  = '\xd7dee2702d63ad89917b6a4da9981c90c4d24f8c2bdfd64c604ecae57d8d0651'
TOPIC_RANGO_USER_REFUNDED             = '\xdc5736cbc70c0769c8938a6a3bf69a501b964ef916f1c25ae96d934ef9a10c3e'
TOPIC_RANGO_MW_PAUSED_STATE_UPDATED   = '\xbfe19c616282c006fd97e57c7fc8eb0e16d0399422c333ccce7bc72f3a1ac843'
TOPIC_RANGO_WHITELIST_STORAGE_UPDATED = '\xa24130b75a8bf66270e29156ab91ec1ee3df62d286ceb96fd86523682923a38c'

-- ===== Selectors (chain-agnostic) =====
SEL_HANDLE_V3_ACROSS_MESSAGE          = '\x3a5be8cb'
SEL_CCTPV2_CALL_RECEIVE_MESSAGE       = '\xf44452f1'
SEL_LZ_COMPOSE                        = '\xd0a10260'
SEL_SG_RECEIVE                        = '\xab8236f3'
SEL_CF_RECEIVE                        = '\x4904ac5f'
SEL_X_RECEIVE                         = '\xfd614f41'
SEL_MW_REFUND                         = '\x410085df'
SEL_MW_REFUND_NATIVE                  = '\x9fae52e6'

-- ===== Addresses (network-specific; only where the code check found code) =====
ETH_RANGO_ACROSS_MW_CANCUN             = '\xd5c7176ec638ef466c2fee761762d9eab673997d'
ETH_RANGO_CCTPV2_MW                    = '\xb5777e29aeea886537e3fef1c565f86e2d9760e8'
ETH_RANGO_OFT_MW                       = '\x8b4a4a8b619ff52b0d35f74e4063f76cefca618f'
ETH_RANGO_STARGATE_MW_CANCUN           = '\x5434ed2d9f5737986858de127545e8a2fb6eb6ae'
ETH_RANGO_SYMBIOSIS_MW_CANCUN          = '\x0b7728e6c51511e30788a3a393a3362d59ca67af'
ETH_RANGO_SATELLITE_MW_CANCUN          = '\x901d602dcade00e2d7384e3940a70ef772a355c3'
ETH_RANGO_WORMHOLE_MW_CANCUN           = '\x93310c2a44c0ea5b5381606d020980cc9b62f547'
ETH_RANGO_CHAINFLIP_MW_CANCUN          = '\xb4231156bbf6025745046d9de642a4eb242cd9ef'
ETH_RANGO_DEBRIDGE_MW_CANCUN           = '\xd9dc714d617608c273da943840a17e4f1092d766'
ETH_RANGO_CONNEXT_MW_CANCUN            = '\x0f415542e35a05a2655e2b1a0a95fe1cc74e84a3'
ETH_RANGO_NITRO_MW_CANCUN              = '\x557babba31be0ca0571cf5daf44fb8c42ba10351'
ETH_RANGO_MIDDLEWARESTORAGE_MW_CANCUN  = '\x89fe77af04db303d612d7e7f4c1c5e8664edbef6'
BASE_RANGO_ACROSS_MW_EVM               = '\xb852e653f8fbc099f06dc9d61e269517a4990b73'
BASE_RANGO_CCTPV2_MW                   = '\xb5777e29aeea886537e3fef1c565f86e2d9760e8'
BASE_RANGO_STARGATE_MW_EVM             = '\x7045f971e312f7f1e211b3085ace9155deb0a976'
BASE_RANGO_SYMBIOSIS_MW_EVM            = '\x3caed470a3215a4d6648d5c684c429b7a371c269'
BASE_RANGO_SATELLITE_MW_EVM            = '\x0adfb7975aa7c3ad90c57aea8fde5e31a721e9bb'
BASE_RANGO_WORMHOLE_MW_EVM             = '\x87f9be4d0478df182c95cbbd761381699b334342'
BASE_RANGO_DEBRIDGE_MW_EVM             = '\x3abaeb6399d3fc44838d75b88e642182e4b826fe'
BASE_RANGO_CONNEXT_MW_EVM              = '\x4a91efc961913fc24bfae6bc3eb5457e34e8f764'
BASE_RANGO_NITRO_MW_EVM                = '\xb05233e0779ca7952a27cbff7c3820cfce9526b3'
BASE_RANGO_MIDDLEWARESTORAGE_MW_EVM    = '\x0484962f4ff892ee5608be5ec80e2f461624a87c'
ARB_RANGO_ACROSS_MW_EVM                = '\xb852e653f8fbc099f06dc9d61e269517a4990b73'
ARB_RANGO_CCTPV2_MW                    = '\xb5777e29aeea886537e3fef1c565f86e2d9760e8'
ARB_RANGO_OFT_MW                       = '\x8b4a4a8b619ff52b0d35f74e4063f76cefca618f'
ARB_RANGO_STARGATE_MW_EVM              = '\x7045f971e312f7f1e211b3085ace9155deb0a976'
ARB_RANGO_SYMBIOSIS_MW_EVM             = '\x3caed470a3215a4d6648d5c684c429b7a371c269'
ARB_RANGO_SATELLITE_MW_EVM             = '\x0adfb7975aa7c3ad90c57aea8fde5e31a721e9bb'
ARB_RANGO_WORMHOLE_MW_EVM              = '\x87f9be4d0478df182c95cbbd761381699b334342'
ARB_RANGO_CBRIDGE_MW_EVM               = '\xc1e311c06230c2fae6425c07bb0a7c5ffce9c785'
ARB_RANGO_CHAINFLIP_MW_EVM             = '\x74c670a0bb4668f146fb5b97d0b4ea8ef60986da'
ARB_RANGO_DEBRIDGE_MW_EVM              = '\x3abaeb6399d3fc44838d75b88e642182e4b826fe'
ARB_RANGO_CONNEXT_MW_EVM               = '\x4a91efc961913fc24bfae6bc3eb5457e34e8f764'
ARB_RANGO_NITRO_MW_EVM                 = '\xb05233e0779ca7952a27cbff7c3820cfce9526b3'
ARB_RANGO_MIDDLEWARESTORAGE_MW_EVM     = '\x0484962f4ff892ee5608be5ec80e2f461624a87c'
OP_RANGO_ACROSS_MW_CANCUN              = '\xd5c7176ec638ef466c2fee761762d9eab673997d'
OP_RANGO_CCTPV2_MW                     = '\xb5777e29aeea886537e3fef1c565f86e2d9760e8'
OP_RANGO_OFT_MW                        = '\x8b4a4a8b619ff52b0d35f74e4063f76cefca618f'
OP_RANGO_STARGATE_MW_CANCUN            = '\x5434ed2d9f5737986858de127545e8a2fb6eb6ae'
OP_RANGO_SYMBIOSIS_MW_CANCUN           = '\x0b7728e6c51511e30788a3a393a3362d59ca67af'
OP_RANGO_SATELLITE_MW_CANCUN           = '\x901d602dcade00e2d7384e3940a70ef772a355c3'
OP_RANGO_WORMHOLE_MW_CANCUN            = '\x93310c2a44c0ea5b5381606d020980cc9b62f547'
OP_RANGO_DEBRIDGE_MW_CANCUN            = '\xd9dc714d617608c273da943840a17e4f1092d766'
OP_RANGO_CONNEXT_MW_CANCUN             = '\x0f415542e35a05a2655e2b1a0a95fe1cc74e84a3'
OP_RANGO_NITRO_MW_CANCUN               = '\x557babba31be0ca0571cf5daf44fb8c42ba10351'
OP_RANGO_MIDDLEWARESTORAGE_MW_CANCUN   = '\x89fe77af04db303d612d7e7f4c1c5e8664edbef6'
POLY_RANGO_ACROSS_MW_EVM               = '\xb852e653f8fbc099f06dc9d61e269517a4990b73'
POLY_RANGO_CCTPV2_MW                   = '\xb5777e29aeea886537e3fef1c565f86e2d9760e8'
POLY_RANGO_OFT_MW                      = '\x8b4a4a8b619ff52b0d35f74e4063f76cefca618f'
POLY_RANGO_STARGATE_MW_EVM             = '\x7045f971e312f7f1e211b3085ace9155deb0a976'
POLY_RANGO_SYMBIOSIS_MW_EVM            = '\x3caed470a3215a4d6648d5c684c429b7a371c269'
POLY_RANGO_SATELLITE_MW_EVM            = '\x0adfb7975aa7c3ad90c57aea8fde5e31a721e9bb'
POLY_RANGO_WORMHOLE_MW_EVM             = '\x87f9be4d0478df182c95cbbd761381699b334342'
POLY_RANGO_CBRIDGE_MW_EVM              = '\xc1e311c06230c2fae6425c07bb0a7c5ffce9c785'
POLY_RANGO_DEBRIDGE_MW_EVM             = '\x3abaeb6399d3fc44838d75b88e642182e4b826fe'
POLY_RANGO_CONNEXT_MW_EVM              = '\x4a91efc961913fc24bfae6bc3eb5457e34e8f764'
POLY_RANGO_NITRO_MW_EVM                = '\xb05233e0779ca7952a27cbff7c3820cfce9526b3'
POLY_RANGO_MIDDLEWARESTORAGE_MW_EVM    = '\x0484962f4ff892ee5608be5ec80e2f461624a87c'
POLY_RANGO_MIDDLEWARESTORAGE_MW_CANCUN = '\x89fe77af04db303d612d7e7f4c1c5e8664edbef6'
BNB_RANGO_OFT_MW                       = '\x8b4a4a8b619ff52b0d35f74e4063f76cefca618f'
BNB_RANGO_STARGATE_MW_EVM              = '\x7045f971e312f7f1e211b3085ace9155deb0a976'
BNB_RANGO_SYMBIOSIS_MW_EVM             = '\x3caed470a3215a4d6648d5c684c429b7a371c269'
BNB_RANGO_SATELLITE_MW_EVM             = '\x0adfb7975aa7c3ad90c57aea8fde5e31a721e9bb'
BNB_RANGO_WORMHOLE_MW_EVM              = '\x87f9be4d0478df182c95cbbd761381699b334342'
BNB_RANGO_CBRIDGE_MW_EVM               = '\xc1e311c06230c2fae6425c07bb0a7c5ffce9c785'
BNB_RANGO_DEBRIDGE_MW_EVM              = '\x3abaeb6399d3fc44838d75b88e642182e4b826fe'
BNB_RANGO_CONNEXT_MW_EVM               = '\x4a91efc961913fc24bfae6bc3eb5457e34e8f764'
BNB_RANGO_NITRO_MW_EVM                 = '\xb05233e0779ca7952a27cbff7c3820cfce9526b3'
BNB_RANGO_MIDDLEWARESTORAGE_MW_EVM     = '\x0484962f4ff892ee5608be5ec80e2f461624a87c'
AVAX_RANGO_CCTPV2_MW                   = '\xb5777e29aeea886537e3fef1c565f86e2d9760e8'
AVAX_RANGO_OFT_MW                      = '\x8b4a4a8b619ff52b0d35f74e4063f76cefca618f'
AVAX_RANGO_STARGATE_MW_EVM             = '\x7045f971e312f7f1e211b3085ace9155deb0a976'
AVAX_RANGO_SYMBIOSIS_MW_EVM            = '\x3caed470a3215a4d6648d5c684c429b7a371c269'
AVAX_RANGO_SATELLITE_MW_EVM            = '\x0adfb7975aa7c3ad90c57aea8fde5e31a721e9bb'
AVAX_RANGO_WORMHOLE_MW_EVM             = '\x87f9be4d0478df182c95cbbd761381699b334342'
AVAX_RANGO_CBRIDGE_MW_EVM              = '\xc1e311c06230c2fae6425c07bb0a7c5ffce9c785'
AVAX_RANGO_DEBRIDGE_MW_EVM             = '\x3abaeb6399d3fc44838d75b88e642182e4b826fe'
AVAX_RANGO_NITRO_MW_EVM                = '\xb05233e0779ca7952a27cbff7c3820cfce9526b3'
AVAX_RANGO_MIDDLEWARESTORAGE_MW_EVM    = '\x0484962f4ff892ee5608be5ec80e2f461624a87c'
```

---

## 15. Verification & sources

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the explorer-verified ABIs of the middlewares on Ethereum, Base and Arbitrum (the ChainFlip middleware of the EVM set is not verified on Arbitrum; its interface matches the verified Ethereum one by name only).
- **Addresses:** the two sets of the Rango docs deployment page, plus the CCTP V2 and OFT middlewares found as `RangoBridgeCompleted` emitters and by name on the explorers; each existence-checked with `eth_getCode` on all eight chains.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, topic scans from any emitter):**
  - `RangoBridgeCompleted`: Ethereum 19 (8 CCTPV2Middleware, 7 OftMiddleware, 4 AcrossMiddleware (Cancun)); Base 4 (4 AcrossMiddleware (EVM)); Arbitrum 3 (3 AcrossMiddleware (EVM)); Optimism 1 (1 AcrossMiddleware (Cancun)); Polygon 0; BNB 0; Avalanche 0; Robinhood Chain 0.
  - `SendToken` from middlewares (the rest comes from the diamond): Ethereum 19; Base 4; Arbitrum 3; Optimism 1; Polygon 0; BNB 0; Avalanche 0; Robinhood Chain 0.
- **Sample transaction read:** Ethereum `0xef64580aa432bb8b9622e5441d7cc006d6a87efcc5d67cadc6ce0774b0c3aa2f` (a relayer calls `callReceiveMessage` on RangoCCTPV2Middleware `0xB5777E29aEEA886537E3fEF1c565F86e2d9760e8`; CCTP V2 mints 0.249418 USDC to the middleware; the middleware swaps it through the Uniswap V3 router, sends the output token to the receiver (`SendToken`, `Transfer`) and emits `ActionDone` and `RangoBridgeCompleted`).

Authoritative sources:
- [rango-exchange/rango-contracts-v2](https://github.com/rango-exchange/rango-contracts-v2) (`contracts/facets/bridges/`, `contracts/facets/base/RangoBaseInterchainMiddleware.sol`, `contracts/facets/base/RangoMiddlewaresWhitelistsStorage.sol`, `contracts/interfaces/Interchain.sol`)
- Rango docs — [deployment addresses](https://docs.rango.exchange/smart-contracts/deployment-addresses) · [message passing](https://docs.rango.exchange/smart-contracts/message-passing)
- Explorers (verified sources) — [RangoCCTPV2Middleware on Blockscout](https://eth.blockscout.com/address/0xB5777E29aEEA886537E3fEF1c565F86e2d9760e8) · [RangoAcrossMiddleware on Blockscout](https://eth.blockscout.com/address/0xd5C7176Ec638eF466c2Fee761762d9EAb673997d) · [RangoOftMiddleware on Blockscout](https://eth.blockscout.com/address/0x8B4A4A8b619ff52b0d35F74E4063F76cefCA618F)
