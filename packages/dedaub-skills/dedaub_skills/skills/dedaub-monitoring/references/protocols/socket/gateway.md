# SocketGateway (Socket v2 routes) — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche; not Robinhood Chain, not Arc)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the `SocketDotTech/bungee-contracts-public` repository (`src/SocketGateway.sol`, `src/bridges/`, `src/swap/`, `src/static/RouteIdentifiers.sol`, `deployments/<network>.json`) and the explorer-verified sources of the gateway and of the current route implementations. Topics and selectors recomputed as `keccak256(signature)`; addresses existence-checked with `eth_getCode`; a sample `SocketBridge` transaction read on Ethereum.
**Scope:** the SocketGateway, which the Socket docs call "legacy routes": one gateway contract per chain that runs registered route implementations (bridges and swaps) by `DELEGATECALL`, the SocketDeployFactory that deploys and disables routes, and the route events. It has the same address on seven chains; Robinhood Chain has none. Topics and selectors are chain-agnostic; addresses are network-specific.

The gateway keeps a table `routes[routeId] → implementation`. A caller runs a route with `executeRoute(routeId, routeData)`, with `executeRoutes`, or with the **route-id fallback**: the first 4 bytes of the calldata are the `routeId` (as a `uint32`), and the gateway `DELEGATECALL`s the route with the rest of the calldata. Every route event is therefore emitted by the **gateway address**. A bridge route calls the underlying bridge in the same transaction and emits `SocketBridge`. There is no Socket event on the destination chain.

Three facts to know before indexing:

1. **Transaction selectors are route ids.** An input that starts with `0x000001be` is route 446, not a function. `routesCount()` was 447 on Ethereum and 428 on Base on 2026-09-29.
2. **`bridgeName` is `keccak256` of the route name** (for example `keccak256("Across")` = `0x709f58818bedd58450336213e1f2f6ff7405a2b1e594f64270a17b7e2249419c`). Table in §13.
3. **No link key.** `SocketBridge` has no transfer id. Link it to the underlying bridge's event in the same transaction (for example Across `FundsDeposited.depositId`).

---

## 0. Contract families & versions

| Contract | Address | Chains | Role | Upgradeable? |
|----------|---------|--------|------|--------------|
| **SocketGateway** | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | ETH·Base·Arb·OP·Poly·BNB·Avax | Route registry and executor; emits every route event. 24,305-byte runtime on each of the seven chains; the code hash is not identical on every chain. | Not a proxy. New logic = a new route (`addRoute`, `NewRouteAdded`); `disableRoute` points a route at DisabledSocketRoute. |
| SocketDeployFactory | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | ETH·Base·Arb·OP·Poly·BNB·Avax | Deploys route implementations; emits `Deployed`, `DisabledRoute`, `Destroyed`. | No |
| DisabledSocketRoute | `0x0f34A522FF82151c90679b73211955068FD854F1` | ETH·Base·Arb·OP·Poly·BNB·Avax | Target of disabled route ids (reverts). | No |
| Route implementations | per chain (for example AcrossImplV3 `0x740EA79e2FccDDB4eE8bB8Fc8ccAC5eb6dFa0b40`, CctpV2Impl `0xb701aB56ACB5897eEc7905afF72b52706638a2ec` on Ethereum) | per chain | Bridge and swap logic, run by `DELEGATECALL`. Listed in `deployments/<network>.json`; resolve a live one with `getRoute(routeId)`. | Replaced by adding a new route. |
| Owner | `0xb0bbff6311b7f245761a7846d3ce7b1b100c1836` | 7 chains | `owner()` of the gateway (two-step `nominateOwner` / `claimOwner`). An EOA (no code; nonce 909 on Ethereum). Same owner on all seven chains; it is also `owner()` of BungeeReceiver ([openrouter.md](openrouter.md)). | — |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Route events (emitted by the gateway)

| topic0 | Event |
|--------|-------|
| `0x74594da9e31ee4068e17809037db37db496702bf7d8d63afe6f97949277d1609` | `SocketBridge(uint256 amount, address token, uint256 toChainId, bytes32 bridgeName, address sender, address receiver, bytes32 metadata)` |
| `0xf2c396ae8338050cbc11bc6ee6a9750e8c2aba63521138b6597eca449e65ded8` | `SocketNonEvmDestBridge(uint256 amount, address token, uint256 toChainId, bytes32 bridgeName, address sender, bytes32 receiver, bytes32 metadata)` |
| `0x62e24e0f5ff17555bb43febccccf2721375425fdd421652271b70f05afe0ae64` | `SocketNonEvmDestBridge(uint256 amount, address fromToken, bytes32 toToken, uint256 toChainId, bytes32 bridgeName, address sender, bytes32 receiver, bytes32 metadata)` |
| `0xb346a959ba6c0f1c7ba5426b10fd84fe4064e392a0dfcf6609e9640a0dd260d3` | `SocketSwapTokens(address fromToken, address toToken, uint256 buyAmount, uint256 sellAmount, bytes32 routeName, address receiver, bytes32 metadata)` |
| `0x6ea2964966a13d361befaca87edb26595ca75a30f3b77887d67d5a7d0e4805c0` | `SocketFeesDeducted(uint256 fees, address feesToken, address feesTaker)` |
| `0x8e0b0751421473f3daf88dfc27ad9ba2d30fde6d03b085963254163fb456ed37` | `NativeBridgeFee(uint256 fee)` |

- `SocketBridge` has no indexed field. Data words: 0 `amount`, 1 `token` (`0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` = native), 2 `toChainId`, 3 `bridgeName`, 4 `sender`, 5 `receiver`, 6 `metadata`.
- `SocketNonEvmDestBridge` replaces `receiver` with a `bytes32` for non-EVM destinations (Mayan routes). The first version has no `toToken`; the current MayanBridgeImplV2 adds `bytes32 toToken`.
- `SocketSwapTokens` is a same-chain swap route. `SocketFeesDeducted` is emitted by the fee-taking controller. `NativeBridgeFee` records a native fee paid to the bridge.

### 1.2 Admin events

| topic0 | Event |
|--------|-------|
| `0x7977983873e5c968018b0deaedba28f6ce6253277670e94e627fbc08efc50cb1` | `NewRouteAdded(uint32 indexed routeId, address indexed route)` |
| `0xc60cf0bdf6c913c2d080d151c29909503abb49cdd09b459a7a10a16a466d02da` | `RouteDisabled(uint32 indexed routeId)` |
| `0x7601ed90c4c6f485f9633a9355c473c63ec60dfb8e04d060dbda9a80cf48eb68` | `ControllerAdded(uint32 indexed controllerId, address indexed controllerAddress)` |
| `0xc203fc627a1b6dd6b6dad3f6b7a313417bb01b1b5ebcd77ed25aff6a0b160865` | `ControllerDisabled(uint32 indexed controllerId)` |
| `0x906a1c6bd7e3091ea86693dd029a831c19049ce77f1dce2ce0bab1cacbabce22` | `OwnerNominated(address indexed nominee)` |
| `0xfbe19c9b601f5ee90b44c7390f3fa2319eba01762d34ee372aeafd59b25c7f87` | `OwnerClaimed(address indexed claimer)` |
| `0xed8889f560326eb138920d842192f0eb3dd22b4f139c87a2c57538e05bae1278` | `OwnershipTransferRequested(address indexed _from, address indexed _to)` |
| `0xf40fcec21964ffb566044d083b4073f29f7f7929110ea19e1b3ebe375d89055e` | `Deployed(address _addr)` |
| `0x53440d5e7a0bd8ddea19135519c56ae739271e670980885596582a08edc71382` | `DisabledRoute(address _addr)` |
| `0x7dec311f70bce33f6997a1cc140bcb6149f9ee83d6be656e848b00d170c98200` | `Destroyed(address _addr)` |

`Deployed`, `DisabledRoute` and `Destroyed` come from the SocketDeployFactory; the others from the gateway.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 SocketGateway

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1028c2bd` | `executeRoute(uint32 routeId, bytes routeData)` | Runs route `routeId` by `DELEGATECALL`. |
| `0xc3540448` | `executeRoutes(uint32[] routeIds, bytes[] dataItems)` | Several routes in one call. |
| `0x37c6145a` | `executeController((uint32 controllerId, bytes data) socketControllerRequest)` | Runs a controller (fee taker, refuel). |
| `0x5dbd8f6b` | `executeControllers((uint32 controllerId, bytes data)[] controllerRequests)` | Several controllers. |
| `0x96f4130c` | `swapAndMultiBridge((uint32 swapRouteId, bytes swapImplData, uint32[] bridgeRouteIds, bytes[] bridgeImplDataItems, uint256[] bridgeRatios, bytes[] eventDataItems) swapMultiBridgeRequest)` | Swap, then split the output across several bridge routes. |
| `0x8c95ff1e` | `addRoute(address routeAddress)` | Owner only. Emits `NewRouteAdded`. |
| `0x9e0bbd9f` | `disableRoute(uint32 routeId)` | Owner only. Emits `RouteDisabled`. |
| `0xa7fc7a07` | `addController(address controllerAddress)` | Owner only. Emits `ControllerAdded`. |
| `0x734427c8` | `disableController(uint32 controllerId)` | Owner only. Emits `ControllerDisabled`. |
| `0x82230446` | `setApprovalForRouters(address[] routeAddresses, address[] tokenAddresses, bool isMax)` | Owner only. |
| `0x6ccae054` | `rescueFunds(address token, address userAddress, uint256 amount)` | Owner only. |
| `0xe42e0ea9` | `rescueEther(address userAddress, uint256 amount)` | Owner only. |
| `0x5b94db27` | `nominateOwner(address nominee_)` | Owner only. Emits `OwnerNominated`. |
| `0x3bd1adec` | `claimOwner()` | Nominee only. Emits `OwnerClaimed`. |
| `0x263af8e8` | `routes(uint32)` | View: route address. |
| `0xfd326921` | `routesCount()` | View: number of routes. |
| `0x7095d471` | `getRoute(uint32 routeId)` | View. |
| `0x915ad7e9` | `addressAt(uint32 routeId)` | View. |

### 2.2 Route implementations (run inside the gateway)

These selectors appear inside `executeRoute(routeId, routeData)` (as the first 4 bytes of `routeData`) or after the 4-byte route id of a fallback call. Examples from the current Across, Stargate V2, CCTP V2 and Mayan V2 routes on Ethereum:

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb3dc8da4` | `bridgeAfterSwap(uint256 amount, bytes bridgeData)` | AcrossImplV3 (and every bridge route) |
| `0xcc54d224` | `bridgeERC20To(uint256 amount, (address[] senderReceiverAddresses, address[] inputOutputTokens, uint256 toChainId, uint32[] quoteAndDeadlineTimeStamps, uint256 bridgeFee, uint8 inputTokenDecimals, uint8 outputTokenDecimals, bytes32 metadata, bytes message) acrossBridgeData)` | AcrossImplV3 |
| `0xa3b8bfba` | `bridgeNativeTo(uint256 amount, (address[] senderReceiverAddresses, address outputToken, uint256 toChainId, uint32[] quoteAndDeadlineTimeStamps, uint256 bridgeFee, uint8 inputTokenDecimals, uint8 outputTokenDecimals, bytes32 metadata, bytes message) acrossBridgeData)` | AcrossImplV3 |
| `0x55153e59` | `swapAndBridge(uint32 swapId, bytes swapData, (address[] senderReceiverAddresses, address outputToken, uint256 toChainId, uint32[] quoteAndDeadlineTimeStamps, uint256 bridgeFee, uint8 inputTokenDecimals, uint8 outputTokenDecimals, bytes32 metadata, bytes message) acrossBridgeData)` | AcrossImplV3 |
| `0x51c0f7b0` | `bridgeERC20To(address token, uint256 amount, (uint32 dstEid, uint256 minAmountLD, address stargatePoolAddress, bytes destinationPayload, bytes destinationExtraOptions, (uint256 nativeFee, uint256 lzTokenFee) messagingFee, bytes32 metadata, uint256 toChainId, address receiver, bytes swapData, uint32 swapId, bool isNativeSwapRequired, bool isApprovalRequired) stargateBridgeData)` | StargateImplV2 |
| `0xdb32a6bf` | `bridgeNativeTo(uint256 amount, (uint32 dstEid, uint256 minAmountLD, address stargatePoolAddress, bytes destinationPayload, bytes destinationExtraOptions, (uint256 nativeFee, uint256 lzTokenFee) messagingFee, bytes32 metadata, uint256 toChainId, address receiver, bytes swapData, uint32 swapId, bool isNativeSwapRequired, bool isApprovalRequired) stargateBridgeData)` | StargateImplV2 |
| `0x7eee0611` | `swapAndBridge(uint32 swapId, bytes swapData, (uint32 dstEid, uint256 minAmountLD, address stargatePoolAddress, bytes destinationPayload, bytes destinationExtraOptions, (uint256 nativeFee, uint256 lzTokenFee) messagingFee, bytes32 metadata, uint256 toChainId, address receiver, bytes swapData, uint32 swapId, bool isNativeSwapRequired, bool isApprovalRequired) stargateBridgeData)` | StargateImplV2 |
| `0x3ca7f5bc` | `bridgeERC20To(uint256 amount, bytes32 metadata, address receiverAddress, address token, uint256 toChainId, uint32 destinationDomain, uint256 feeAmount, uint256 maxFee, uint32 minFinalityThreshold)` | CctpV2Impl |
| `0x4db9cf6a` | `swapAndBridge(uint32 swapId, bytes swapData, (address receiverAddress, uint32 destinationDomain, uint256 toChainId, uint256 feeAmount, uint256 maxFee, uint32 minFinalityThreshold, bytes32 metadata) cctpData)` | CctpV2Impl |
| `0xc41719e4` | `bridgeERC20To(address token, uint256 amount, (address receiver, bytes32 metadata, bytes32 toToken, uint256 toChainId, bytes protocolData, address mayanProtocolAddress, bool isNonEvmDest, bytes32 nonEvmAddress) mayanBridgeData)` | MayanBridgeImplV2 |
| `0x8231a98b` | `bridgeNativeTo(uint256 amount, (address receiver, bytes32 metadata, bytes32 toToken, uint256 toChainId, bytes protocolData, address mayanProtocolAddress, bool isNonEvmDest, bytes32 nonEvmAddress) mayanBridgeData)` | MayanBridgeImplV2 |
| `0x3b43789c` | `swapAndBridge(uint32 swapId, bytes swapData, (address receiver, bytes32 metadata, bytes32 toToken, uint256 toChainId, bytes protocolData, address mayanProtocolAddress, bool isNonEvmDest, bytes32 nonEvmAddress) mayanBridgeData)` | MayanBridgeImplV2 |
| `0xec60816a` | `swapAndBridgeERC20ToViaMayan(address token, uint256 amount, (address receiver, bytes32 metadata, bytes32 toToken, uint256 toChainId, bytes protocolData, address mayanProtocolAddress, bool isNonEvmDest, bytes32 nonEvmAddress, address mayanSwapProtocolAddress, bytes mayanSwapData, address mayanMiddleToken, uint256 mayanMinMiddleAmount) mayanBridgeData)` | MayanBridgeImplV2 |
| `0xa57fbaf8` | `swapAndBridgeNativeToViaMayan(uint256 amount, (address receiver, bytes32 metadata, bytes32 toToken, uint256 toChainId, bytes protocolData, address mayanProtocolAddress, bool isNonEvmDest, bytes32 nonEvmAddress, address mayanSwapProtocolAddress, bytes mayanSwapData, address mayanMiddleToken, uint256 mayanMinMiddleAmount) mayanBridgeData)` | MayanBridgeImplV2 |

---

## 3. Addresses — Ethereum (chain ID 1)

From `deployments/ethereum.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| SocketGateway | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | 24,305 |
| SocketDeployFactory | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | 4,673 |
| DisabledSocketRoute | `0x0f34A522FF82151c90679b73211955068FD854F1` | 1,324 |
| AcrossImplV3 | `0x740EA79e2FccDDB4eE8bB8Fc8ccAC5eb6dFa0b40` | 10,766 |
| StargateImplV2 | `0x05b108fD88d042eF0145DCcd564DCd6471852FC2` | 9,159 |
| CctpV2Impl | `0xb701aB56ACB5897eEc7905afF72b52706638a2ec` | 6,744 |
| MayanBridgeImplV2 | `0x51fDcA877B3E1a73C6C730F9665372549bfc0E67` | 12,462 |
| FeesTakerController | `0xF37561Cd1C4b42f8c004C977fb140a4679089526` | 5,055 |
| RefuelSwapAndBridgeController | `0x5Cb5A509beD96B2d168DC8aD85736B0b90da8473` | 1,885 |

`owner()` of the gateway = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 4. Addresses — Base (chain ID 8453)

From `deployments/base.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| SocketGateway | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | 24,305 |
| SocketDeployFactory | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | 4,673 |
| DisabledSocketRoute | `0x0f34A522FF82151c90679b73211955068FD854F1` | 1,324 |
| AcrossImplV3 | `0x740EA79e2FccDDB4eE8bB8Fc8ccAC5eb6dFa0b40` | 10,766 |
| StargateImplV2 | `0x0CB0552405846a4fcd83FBD791eF4a1F43ab3D94` | 9,159 |
| CctpV2Impl | `0x8EAeE07f8FFF38695708be900c1F9aacFB8b3C09` | 6,744 |
| MayanBridgeImplV2 | `0xf4f62E1D36B0Be2a701EDaa25967b6204C6b5aBE` | 12,462 |
| FeesTakerController | `0x6808dC8Fc272827c9236cb3bBf3d77e3e9A9B056` | 5,055 |
| RefuelSwapAndBridgeController | `0x5ce6d37c2fd66Fe1531F44C5141e815b7c9aC8a4` | 1,885 |

`owner()` of the gateway = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 5. Addresses — Arbitrum One (chain ID 42161)

From `deployments/arbitrum.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| SocketGateway | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | 24,305 |
| SocketDeployFactory | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | 4,673 |
| DisabledSocketRoute | `0x0f34A522FF82151c90679b73211955068FD854F1` | 1,324 |
| AcrossImplV3 | `0x740EA79e2FccDDB4eE8bB8Fc8ccAC5eb6dFa0b40` | 10,766 |
| StargateImplV2 | `0xBf6fa3f58113139E7437dA5dcCE1CB005DA387f3` | 9,159 |
| CctpV2Impl | `0x2a6dcEc445Ac3B9F9111605857eCEA4E9baf9b3f` | 6,744 |
| MayanBridgeImplV2 | `0x0E1E7Dad45c0baF66956d0b9D82a29129a85FA0A` | 12,462 |
| FeesTakerController | `0xb3f1271c809fF47767205851E7334407354A862F` | 5,055 |
| RefuelSwapAndBridgeController | `0xFC42BcAA16a54e7E48D0c39e4713dC5923BD551D` | 1,885 |

`owner()` of the gateway = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 6. Addresses — Optimism (chain ID 10)

From `deployments/optimism.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| SocketGateway | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | 24,305 |
| SocketDeployFactory | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | 4,673 |
| DisabledSocketRoute | `0x0f34A522FF82151c90679b73211955068FD854F1` | 1,324 |
| AcrossImplV3 | `0x740EA79e2FccDDB4eE8bB8Fc8ccAC5eb6dFa0b40` | 10,766 |
| StargateImplV2 | `0xF20B3CB7508c519296556C1Caa9dB6F210e0232a` | 9,159 |
| MayanBridgeImplV2 | `0xf4f62E1D36B0Be2a701EDaa25967b6204C6b5aBE` | 12,462 |
| FeesTakerController | `0x4E7f21d92b70fCBBcB6AFCb8Bf59420622c158B3` | 5,055 |
| RefuelSwapAndBridgeController | `0x3Dd7419889FF387A58D3Dad1F8B49ea1064290fB` | 1,885 |

`owner()` of the gateway = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 7. Addresses — Polygon PoS (chain ID 137)

From `deployments/polygon.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| SocketGateway | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | 24,305 |
| SocketDeployFactory | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | 4,673 |
| DisabledSocketRoute | `0x0f34A522FF82151c90679b73211955068FD854F1` | 1,324 |
| AcrossImplV3 | `0x740EA79e2FccDDB4eE8bB8Fc8ccAC5eb6dFa0b40` | 10,766 |
| StargateImplV2 | `0x0CB0552405846a4fcd83FBD791eF4a1F43ab3D94` | 9,159 |
| MayanBridgeImplV2 | `0xB412f6F3d855a79EBe0AF5040cC25A7f9AB7645b` | 12,462 |
| FeesTakerController | `0x58B3353f1249cc65993D42E4eFc60F2a0CA1062f` | 5,055 |
| RefuelSwapAndBridgeController | `0x1717004FA6668bAAD3a20258876A88dAd908cd21` | 1,885 |

`owner()` of the gateway = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 8. Addresses — BNB Smart Chain (chain ID 56)

From `deployments/bsc.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| SocketGateway | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | 24,305 |
| SocketDeployFactory | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | 4,673 |
| DisabledSocketRoute | `0x0f34A522FF82151c90679b73211955068FD854F1` | 1,324 |
| AcrossImplV3 | `0x740EA79e2FccDDB4eE8bB8Fc8ccAC5eb6dFa0b40` | 10,766 |
| StargateImplV2 | `0x4682e8315B80cF757e2077280E0471729c992Ed3` | 9,159 |
| MayanBridgeImplV2 | `0xFBd820d7C4aFB954532107b8DD37D0515C90eBb0` | 12,462 |
| FeesTakerController | `0x21185370305A12d71CFd8ceA619905DEc4118F99` | 5,055 |
| RefuelSwapAndBridgeController | `0x77cf21917FF767e2FDEd80760Ee847CAb99BE13b` | 1,885 |

`owner()` of the gateway = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

From `deployments/avalanche.json`; existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| SocketGateway | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | 24,305 |
| SocketDeployFactory | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | 4,673 |
| DisabledSocketRoute | `0x0f34A522FF82151c90679b73211955068FD854F1` | 1,324 |
| StargateImplV2 | `0xd0389e84178f809903cbFE7D1EfAE3EFa9c1769c` | 9,159 |
| CctpV2Impl | `0x65fEABBcfBc796Ee3d8bF1aDd02963468F3Eb8C2` | 6,744 |
| MayanBridgeImplV2 | `0xf4f62E1D36B0Be2a701EDaa25967b6204C6b5aBE` | 12,462 |
| FeesTakerController | `0x9D4Ec3eae994A8b35e8FE52082e3e3D0240c7694` | 5,055 |
| RefuelSwapAndBridgeController | `0xAe21DC9F43d335BF7925E69E2d272288492d91c5` | 1,885 |

`owner()` of the gateway = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

---

## 11. Cross-chain summary

| Chain | ID | SocketGateway | SocketDeployFactory | `routesCount()` | `SocketBridge` logs in the pinned window |
|-------|----|---------------|---------------------|-----------------|--------------------------------------------|
| Ethereum | 1 | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | 447 | 96 |
| Base | 8453 | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | 428 | 127 |
| Arbitrum One | 42161 | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | not read | 12 |
| Optimism | 10 | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | not read | 2 |
| Polygon PoS | 137 | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | not read | 7 |
| BNB Smart Chain | 56 | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | not read | 26 |
| Avalanche C-Chain | 43114 | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | `0x71630095e3F08A86aFC73f7b07342192adf39C55` | not read | 0 |
| Robinhood Chain | 4663 | — (no code) | — | — | — |
| Arc | 5042 | — (no code, 2026-10-05) | — | — | — |

**Robinhood Chain (4663): no SocketGateway.** `eth_getCode` returns `0x` at `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` (nonce 0), no `deployments/robinhood.json` exists in the repository, and the Socket docs list only the OpenRouter contracts for Robinhood Chain.

---

## 12. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| SocketGateway | Not a proxy; route table + `DELEGATECALL` | EIP-1967 implementation slot empty. The logic of a route id changes only through `addRoute` (new id) or `disableRoute`. Watch `NewRouteAdded`, `RouteDisabled`, `ControllerAdded`, `ControllerDisabled`. | `owner()` |
| Route implementations | Plain contracts | Run by `DELEGATECALL` from the gateway; only owner-restricted helpers check the gateway owner. | Replaced by adding a route. |

---

## 13. Detection invariants & gotchas

1. **Key on the gateway address, not on the route address.** Route implementations run by `DELEGATECALL`; `log.address` is the gateway.
2. **`bridgeName` values** (`keccak256` of the route identifier):

| Route | `bridgeName` |
|-------|--------------|
| `Across` | `0x709f58818bedd58450336213e1f2f6ff7405a2b1e594f64270a17b7e2249419c` |
| `Anyswap` | `0xfb124487a9ad253606517a08816473db34d3f4319cda7e548f718d1bd7aec4f3` |
| `CBridge` | `0xc77ff9af68efffed7454e77fb54f8ff0ce78a7d153d8b300824b82b55aad654f` |
| `Hop` | `0x837ed841e30438f54fb6b0097c30a5c4f64b47545c3df655bcd6e44bb8991e37` |
| `Hyphen` | `0xd36025cd509d584ab5657a1932f5097aa97e23f66deca532635f79998b4f0bce` |
| `NativeOptimism` | `0x2e27c951e4ed3f2f1e7771dd262432f093b6ddeabfca0688443958d00b9bcf56` |
| `NativeArbitrum` | `0x7da5d3610317b9820c1f9de12c4c257f3f0e2ea5b63c99f27ed8e0592ac8fb4c` |
| `NativePolygon` | `0xf1c09a354cd800a13f6f260a3a96a0e33db28b0b53528072473336977bba34f4` |
| `Refuel` | `0x0d2fea28d1562e741fbdf63c210c9b730d85f6504e95650096acf21f93afe549` |
| `Stargate` | `0x6debe1c49ff1a7d2012a7d55f3935c306a5eb673882f4edde41dbcaa58467fd1` |
| `OneInch` | `0x2ab0b866d21ac9b7200cb612980a6bede5fc41279d81375c7fe2efd9fa4d9073` |
| `Zerox` | `0x861b086cbd3ddee2b0b12c8ce3b43e1c111ac87dcabda086e02f18095da12f20` |
| `Rainbow` | `0x520b7e0fa71292fc3580658e9fcf097987149f9bab7aa0a213933370b9f02218` |
| `cctp` | `0xf8455f3379434a3ef6559858314c8f61d36412da9937cd3f1de59562deb078e6` |
| `cctp-v2` | `0xf902d88747f99d9d727ec886787b85f54753de026065d14f26a61e357d1c13ff` |
| `Connext` | `0x6e6ef0d56d65c2193ef8da79bb1e0bac59c8ac17fdd0b3cc6122f82f7d42cc9d` |
| `Synapse` | `0x47443678ca5bb8034d5e764a6f20d6e5cfcbb4a3912e12f8bae660cd0face530` |
| `ZkSync` | `0x2e760812e6696b561a918e71ad2845639638959ed846b188488dd0d8c0b953ef` |
| `Symbiosis` | `0xea698b477c99ea804835b684c4c3009f282df52a6bf660d4006c72a3b60fd670` |
| `NativeGnosis` | `0x7c4e564b66172ccd4006719b3b9e6d8e4eabbc54c5cf017495bf6a3b3f4dd06f` |
| `NativeScroll` | `0x69f44f5233c0e8b1c14833d7401ce82f23c362f7e7e125bedc2c5e126ab38bb6` |
| `Zeroxv2` | `0xd20b015e92b28033d88b4cafd3b6db4dda8e3b0159caff34f2de623a8e6ff9c6` |
| `MayanBridge` | `0xe9936f0ec4354ed5e05fe939bfc04444115d879c284276c89567806a9a5fa275` |

3. **Route-id fallback.** Most transactions call the gateway with the route id as the first 4 bytes (for example `0x000001be`). Decode the rest of the input with the route's ABI.
4. **Value movement.** In the sample transaction the gateway received 0.07442027 ETH as `msg.value`, and the Across route deposited it into the Across spoke pool in the same transaction (`FundsDeposited` to chain 8453). For ERC-20 routes the gateway pulls the token from the sender (`Transfer` sender → gateway) and approves the bridge.
5. **`sender` and `receiver` are in the event.** `tx.from` can be an integrator contract; use `SocketBridge.sender` and `SocketBridge.receiver`.
6. **Admin triggers.** `NewRouteAdded` (a new implementation becomes callable), `RouteDisabled`, `ControllerAdded`, `ControllerDisabled`, `OwnerNominated`, `OwnerClaimed`; and the factory's `Deployed` / `Destroyed`.

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_SOCKET_BRIDGE                 = '\x74594da9e31ee4068e17809037db37db496702bf7d8d63afe6f97949277d1609'
TOPIC_SOCKET_NON_EVM_DEST_BRIDGE_V1 = '\xf2c396ae8338050cbc11bc6ee6a9750e8c2aba63521138b6597eca449e65ded8'
TOPIC_SOCKET_NON_EVM_DEST_BRIDGE_V2 = '\x62e24e0f5ff17555bb43febccccf2721375425fdd421652271b70f05afe0ae64'
TOPIC_SOCKET_SWAP_TOKENS            = '\xb346a959ba6c0f1c7ba5426b10fd84fe4064e392a0dfcf6609e9640a0dd260d3'
TOPIC_SOCKET_FEES_DEDUCTED          = '\x6ea2964966a13d361befaca87edb26595ca75a30f3b77887d67d5a7d0e4805c0'
TOPIC_NATIVE_BRIDGE_FEE             = '\x8e0b0751421473f3daf88dfc27ad9ba2d30fde6d03b085963254163fb456ed37'
TOPIC_NEW_ROUTE_ADDED               = '\x7977983873e5c968018b0deaedba28f6ce6253277670e94e627fbc08efc50cb1'
TOPIC_ROUTE_DISABLED                = '\xc60cf0bdf6c913c2d080d151c29909503abb49cdd09b459a7a10a16a466d02da'
TOPIC_CONTROLLER_ADDED              = '\x7601ed90c4c6f485f9633a9355c473c63ec60dfb8e04d060dbda9a80cf48eb68'
TOPIC_CONTROLLER_DISABLED           = '\xc203fc627a1b6dd6b6dad3f6b7a313417bb01b1b5ebcd77ed25aff6a0b160865'
TOPIC_OWNER_NOMINATED               = '\x906a1c6bd7e3091ea86693dd029a831c19049ce77f1dce2ce0bab1cacbabce22'
TOPIC_OWNER_CLAIMED                 = '\xfbe19c9b601f5ee90b44c7390f3fa2319eba01762d34ee372aeafd59b25c7f87'

-- ===== bridgeName values (data word 3 of SocketBridge) =====
BRIDGE_NAME_ACROSS                  = '\x709f58818bedd58450336213e1f2f6ff7405a2b1e594f64270a17b7e2249419c'
BRIDGE_NAME_CCTP                    = '\xf8455f3379434a3ef6559858314c8f61d36412da9937cd3f1de59562deb078e6'
BRIDGE_NAME_CCTP_V2                 = '\xf902d88747f99d9d727ec886787b85f54753de026065d14f26a61e357d1c13ff'
BRIDGE_NAME_STARGATE                = '\x6debe1c49ff1a7d2012a7d55f3935c306a5eb673882f4edde41dbcaa58467fd1'
BRIDGE_NAME_MAYANBRIDGE             = '\xe9936f0ec4354ed5e05fe939bfc04444115d879c284276c89567806a9a5fa275'
BRIDGE_NAME_NATIVEOPTIMISM          = '\x2e27c951e4ed3f2f1e7771dd262432f093b6ddeabfca0688443958d00b9bcf56'
BRIDGE_NAME_NATIVEARBITRUM          = '\x7da5d3610317b9820c1f9de12c4c257f3f0e2ea5b63c99f27ed8e0592ac8fb4c'
BRIDGE_NAME_NATIVEPOLYGON           = '\xf1c09a354cd800a13f6f260a3a96a0e33db28b0b53528072473336977bba34f4'
BRIDGE_NAME_SYMBIOSIS               = '\xea698b477c99ea804835b684c4c3009f282df52a6bf660d4006c72a3b60fd670'
BRIDGE_NAME_REFUEL                  = '\x0d2fea28d1562e741fbdf63c210c9b730d85f6504e95650096acf21f93afe549'

-- ===== Selectors (chain-agnostic) =====
SEL_EXECUTE_ROUTE                   = '\x1028c2bd'
SEL_EXECUTE_ROUTES                  = '\xc3540448'
SEL_SWAP_AND_MULTI_BRIDGE           = '\x96f4130c'
SEL_ADD_ROUTE                       = '\x8c95ff1e'
SEL_DISABLE_ROUTE                   = '\x9e0bbd9f'
SEL_NOMINATE_OWNER                  = '\x5b94db27'

-- ===== Addresses (network-specific) =====
ETH_SOCKET_GATEWAY                  = '\x3a23f943181408eac424116af7b7790c94cb97a5'
ETH_SOCKET_DEPLOY_FACTORY           = '\x71630095e3f08a86afc73f7b07342192adf39c55'
BASE_SOCKET_GATEWAY                 = '\x3a23f943181408eac424116af7b7790c94cb97a5'
BASE_SOCKET_DEPLOY_FACTORY          = '\x71630095e3f08a86afc73f7b07342192adf39c55'
ARB_SOCKET_GATEWAY                  = '\x3a23f943181408eac424116af7b7790c94cb97a5'
ARB_SOCKET_DEPLOY_FACTORY           = '\x71630095e3f08a86afc73f7b07342192adf39c55'
OP_SOCKET_GATEWAY                   = '\x3a23f943181408eac424116af7b7790c94cb97a5'
OP_SOCKET_DEPLOY_FACTORY            = '\x71630095e3f08a86afc73f7b07342192adf39c55'
POLY_SOCKET_GATEWAY                 = '\x3a23f943181408eac424116af7b7790c94cb97a5'
POLY_SOCKET_DEPLOY_FACTORY          = '\x71630095e3f08a86afc73f7b07342192adf39c55'
BNB_SOCKET_GATEWAY                  = '\x3a23f943181408eac424116af7b7790c94cb97a5'
BNB_SOCKET_DEPLOY_FACTORY           = '\x71630095e3f08a86afc73f7b07342192adf39c55'
AVAX_SOCKET_GATEWAY                 = '\x3a23f943181408eac424116af7b7790c94cb97a5'
AVAX_SOCKET_DEPLOY_FACTORY          = '\x71630095e3f08a86afc73f7b07342192adf39c55'
ETH_SOCKET_GATEWAY_OWNER_EOA        = '\xb0bbff6311b7f245761a7846d3ce7b1b100c1836'
```

---

## 15. Verification & sources

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified ABIs of the gateway, the SocketDeployFactory and the route implementations AcrossImplV3, StargateImplV2, CctpV2Impl and MayanBridgeImplV2 on Ethereum; `SocketSwapTokens`, `SocketFeesDeducted` and the first `SocketNonEvmDestBridge` from the repository sources (`src/swap/SwapImplBase.sol`, `src/controllers/FeesTakerController.sol`, `src/bridges/mayan/MayanBridge.sol`).
- **Addresses:** from `deployments/<network>.json` of the repository, existence-checked with `eth_getCode` on the eight chains.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, address-wide log scan of the gateway):**

  | Event (gateway address scan) | ETH | Base | Arb | OP | Poly | BNB | Avax |
  |---|---|---|---|---|---|---|---|
  | `SocketBridge` | 96 | 127 | 12 | 2 | 7 | 26 | 0 |
  | `SocketNonEvmDestBridge` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | `NativeBridgeFee` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | `NewRouteAdded` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | all topics | 169 | 210 | 13 | 2 | 10 | 54 | 0 |
- **Sample transaction read:** Ethereum `0x9f5a073cefc824957cd5ff4ffe17f81f4f9d103d4b52acff8a76b2b6234a26e8` (input `0x000001be` = route 446; 0.07442027 ETH `msg.value`; Across `FundsDeposited` to chain 8453, deposit id 4681398; `SocketBridge` with `token` = native, `toChainId` = 8453, `bridgeName` = `keccak256("Across")`).

Authoritative sources:
- [SocketDotTech/bungee-contracts-public](https://github.com/SocketDotTech/bungee-contracts-public) (`src/SocketGateway.sol`, `src/static/RouteIdentifiers.sol`, `src/bridges/`, `deployments/`)
- Socket docs — [docs index](https://docs.socket.tech/llms.txt) · [contract addresses](https://docs.socket.tech/integrate/contract-addresses) · [Socket v2 API migration](https://docs.socket.tech/integrate/migration-guide-v2.md)
- Explorers — [SocketGateway on Etherscan](https://etherscan.io/address/0x3a23F943181408EAC424116Af7b7790c94Cb97a5) · [SocketGateway on Basescan](https://basescan.org/address/0x3a23F943181408EAC424116Af7b7790c94Cb97a5) · [Blockscout Ethereum](https://eth.blockscout.com/address/0x3a23F943181408EAC424116Af7b7790c94Cb97a5)
