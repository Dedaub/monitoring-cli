# LI.FI Bridge Facets — Selectors, Data Structs, Facet Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain + Arc)

**Status:** verified on 2026-09-29 (Arc added 2026-10-05). The facet table of every LiFiDiamond was read live with `facets()` (`0x7a0ed627`). Every selector below is registered in at least one of the nine diamonds, unless marked otherwise, and was recomputed as `keccak256(signature)[0:4]` from the explorer-verified ABI of the deployed facet. Facet names and versions come from `lifinance/contracts` `deployments/<network>.json` and `deployments/<network>.diamond.json`, and from the verified sources.
**Scope:** the bridge facets of the LiFiDiamond: their entry selectors, the data struct of each entry point, the key configuration functions, and the facet address on each of the nine chains. Facets are logic contracts: they run through `DELEGATECALL`, so their events come from the diamond ([diamond.md](diamond.md)). Topics and selectors are chain-agnostic; addresses are network-specific.

A monitor rarely needs a facet address. It needs the **entry selector** (the first 4 bytes of a call to the diamond), which names the bridge, and the facet table, which changes only by `DiamondCut`. Read the live table with `facets()`, or resolve one selector with `facetAddress(bytes4)` (`0xcdffacc6`).

---

## 0. How a bridge facet is called

- `startBridgeTokensVia<Bridge>(BridgeData _bridgeData, <Bridge>Data _data)`: bridge the input token as is.
- `swapAndStartBridgeTokensVia<Bridge>(BridgeData _bridgeData, SwapData[] _swapData, <Bridge>Data _data)`: swap first, then bridge.
- `BridgeData` = `(bytes32 transactionId, string bridge, string integrator, address referrer, address sendingAssetId, address receiver, uint256 minAmount, uint256 destinationChainId, bool hasSourceSwaps, bool hasDestinationCall)`.
- `SwapData` = `(address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)`.
- Every entry point emits `LiFiTransferStarted` at the diamond, except the packed Across calls (`LiFiAcrossTransfer` only).

`bridge` strings measured in `LiFiTransferStarted` in the pinned window 2026-09-28 00:00–12:00 UTC:

| Chain | Logs | Most frequent `bridge` values (count) |
|-------|------|----------------------------------------|
| Ethereum | 2,621 | `across` 994, `relaydepository` 804, `mayan` 196, `layerswap` 149, `near` 130, `lifiIntents` 83, `gasZipBridge` 59, `polymerStandard` 34, `stargateV2` 27, `eco` 24, `mayanFastMCTP` 19, `symbiosis` 18, `glacis` 16, `mayanMCTP` 13, `celercircle` 11, `polymer` 8 |
| Base | 3,258 | `relaydepository` 889, `across` 595, `layerswap` 473, `mayan` 353, `lifiIntents` 305, `polymerStandard` 146, `near` 133, `gasZipBridge` 105, `eco` 66, `polymer` 63, `mayanFastMCTP` 45, `stargateV2` 43, `mayanMCTP` 12, `stargateV2Bus` 10, `squid` 8, `glacis` 6 |

- Ethereum: `receiver` = `NON_EVM_ADDRESS` in 550 of 2,621 logs. Top `destinationChainId` values: 4663 (855), 1151111081099710 (414), 8453 (317), 56 (303), 42161 (221), 137 (85), 20000000000001 (79), 5042 (56). Top `integrator` values: `jumper.exchange` 539, `_binancewallet` 431, `phantom` 321, `metamask-bridge` 191, `tangem` 156, `base-app` 156.
- Base: `receiver` = `NON_EVM_ADDRESS` in 564 of 3,258 logs. Top `destinationChainId` values: 4663 (745), 1 (564), 1151111081099710 (540), 56 (371), 42161 (324), 137 (116), 10 (105), 5042 (82). Top `integrator` values: `jumper.exchange` 1,151, `base-app` 533, `rabbykmsv2` 336, `metamask-bridge` 235, `_binancewallet` 179, `phantom` 95.

The `bridge` string is set by the LI.FI API; the contract does not check it against the facet. The facet that ran is the one that owns the entry selector of the call.

---

## 1. Entry and key functions per facet (chain-agnostic)

The third column names the facet and the chains whose diamond has the selector registered (loupe read of 2026-09-29; Arc read on 2026-10-05).

| Selector | Signature | Facet: live on |
|----------|-----------|----------------|
| `0x1fd8010c` | `startBridgeTokensViaAcross((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(int64,uint32,bytes,uint256))` | AcrossFacet: Base·Arb·Poly |
| `0x3a3f7332` | `swapAndStartBridgeTokensViaAcross((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(int64,uint32,bytes,uint256))` | AcrossFacet: Base·Arb·Poly |
| `0x7260352d` | `startBridgeTokensViaAcrossV4ERC20Min((bytes8,bytes32,bytes32,uint64,bytes32,uint256,bytes32,uint32,uint32,uint32,bytes),bytes32,uint256)` | AcrossFacetPackedV4: ETH·Base·Arb·OP·Poly·BNB |
| `0x36b92404` | `startBridgeTokensViaAcrossV4ERC20Packed()` | AcrossFacetPackedV4: ETH·Base·Arb·OP·Poly·BNB |
| `0x72dd147e` | `startBridgeTokensViaAcrossV4NativeMin((bytes8,bytes32,bytes32,uint64,bytes32,uint256,bytes32,uint32,uint32,uint32,bytes))` | AcrossFacetPackedV4: ETH·Base·Arb·OP·Poly·BNB |
| `0xc5d60e97` | `startBridgeTokensViaAcrossV4NativePacked()` | AcrossFacetPackedV4: ETH·Base·Arb·OP·Poly·BNB |
| `0x23452b9c` | `cancelOwnershipTransfer()` | AcrossFacetPackedV4: standalone contract only (owner) |
| `0x7200b829` | `confirmOwnershipTransfer()` | AcrossFacetPackedV4: standalone contract only (owner) |
| `0x1458d7ad` | `executeCallAndWithdraw(address,bytes,address,address,uint256)` | AcrossFacetPackedV4: standalone contract only (owner) |
| `0x4c478642` | `setApprovalForBridge(address[])` | AcrossFacetPackedV4: standalone contract only (owner) |
| `0xf2fde38b` | `transferOwnership(address)` | AcrossFacetPackedV4: standalone contract only (owner) |
| `0xa1f1ce43` | `startBridgeTokensViaAcrossV4((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes32,bytes32,bytes32,bytes32,uint256,uint128,bytes32,uint32,uint32,uint32,bytes))` | AcrossFacetV4: ETH·Base·Arb·OP·Poly·BNB·RH·Arc |
| `0x1794958f` | `swapAndStartBridgeTokensViaAcrossV4((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes32,bytes32,bytes32,bytes32,uint256,uint128,bytes32,uint32,uint32,uint32,bytes))` | AcrossFacetV4: ETH·Base·Arb·OP·Poly·BNB·RH·Arc |
| `0x6a90d66e` | `startBridgeTokensViaAcrossV4Swap((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(uint8,bytes,bytes))` | AcrossV4SwapFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0x9b054bc4` | `swapAndStartBridgeTokensViaAcrossV4Swap((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(uint8,bytes,bytes))` | AcrossV4SwapFacet: ETH·Base·Arb·OP·Poly·BNB |
| `0x6a51e9a9` | `startBridgeTokensViaAllBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes32,uint256,bytes32,uint256,uint8,bool))` | AllBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x63267469` | `swapAndStartBridgeTokensViaAllBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes32,uint256,bytes32,uint256,uint8,bool))` | AllBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xa62ef168` | `setChainIdToAllBridgeChainId((uint256,uint256)[])` | AllBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x37f6bf4e` | `unsetChainIdToAllBridgeChainId(uint256)` | AllBridgeFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xc9851d0b` | `startBridgeTokensViaArbitrumBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(uint256,uint256,uint256))` | ArbitrumBridgeFacet: ETH |
| `0x3cc9517b` | `swapAndStartBridgeTokensViaArbitrumBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(uint256,uint256,uint256))` | ArbitrumBridgeFacet: ETH |
| `0xe0a4201c` | `startBridgeTokensViaCelerCircleBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(uint256,uint32))` | CelerCircleBridgeFacet: ETH·Base·Arb·OP·Poly·Avax |
| `0x4f3b0759` | `swapAndStartBridgeTokensViaCelerCircleBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(uint256,uint32))` | CelerCircleBridgeFacet: ETH·Base·Arb·OP·Poly·Avax |
| `0xbf69fa61` | `CIRCLE_BRIDGE_PROXY()` | CelerCircleBridgeFacet: ETH·Base·Arb·OP·Poly·Avax |
| `0x0315138f` | `startBridgeTokensViaCentrifuge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(uint256,address))` | CentrifugeFacet: ETH·Base |
| `0x8fd4d4dd` | `swapAndStartBridgeTokensViaCentrifuge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(uint256,address))` | CentrifugeFacet: ETH·Base |
| `0x0ad553b3` | `startBridgeTokensViaChainflip((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes,uint32,address,(address,address,address,address,uint256,bytes,bool)[],uint256,bytes))` | ChainflipFacet: ETH·Arb |
| `0xee3314a1` | `swapAndStartBridgeTokensViaChainflip((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes,uint32,address,(address,address,address,address,uint256,bytes,bool)[],uint256,bytes))` | ChainflipFacet: ETH·Arb |
| `0x7766d1ed` | `chainflipVault()` | ChainflipFacet: ETH·Arb |
| `0x4004633e` | `startBridgeTokensViaDeBridgeDln((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes,bytes,bytes,uint256))` | DeBridgeDlnFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x2c7d2db0` | `swapAndStartBridgeTokensViaDeBridgeDln((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes,bytes,bytes,uint256))` | DeBridgeDlnFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x9eaeb24f` | `DLN_SOURCE()` | DeBridgeDlnFacet: ETH |
| `0x8f4bef1c` | `dlnSource()` | DeBridgeDlnFacet: Base·Arb·OP·Poly·BNB·Avax |
| `0x9f5e58f5` | `initDeBridgeDln((uint256,uint256)[])` | DeBridgeDlnFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xf2455b71` | `setDeBridgeChainId(uint256,uint256)` | DeBridgeDlnFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xbff90b61` | `startBridgeTokensViaEco((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes,address,uint64,bytes,bytes32,address,uint256,bytes))` | EcoFacet: ETH·Base·Arb·OP·Poly·BNB·Arc |
| `0x762aea18` | `swapAndStartBridgeTokensViaEco((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes,address,uint64,bytes,bytes32,address,uint256,bytes))` | EcoFacet: ETH·Base·Arb·OP·Poly·BNB·Arc |
| `0x0ff754ea` | `PORTAL()` | EcoFacet: ETH·Base·Arb·OP·Poly·BNB·Arc |
| `0x678786ea` | `startBridgeTokensViaFrax((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,uint32,uint256,address,bytes32))` | FraxFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x07b8e4c7` | `swapAndStartBridgeTokensViaFrax((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(address,uint32,uint256,address,bytes32))` | FraxFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xd1d4fbcf` | `FRAX_HOP()` | FraxFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xa8e13b68` | `setFraxChainIdToEid((uint256,uint32)[])` | FraxFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x3fc027ce` | `unsetFraxChainIdToEid(uint256[])` | FraxFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x5f9af35d` | `startBridgeTokensViaGarden((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,uint256,bytes32,bytes32))` | GardenFacet: ETH·Base·Arb·BNB·RH·Arc |
| `0x76ad76fe` | `swapAndStartBridgeTokensViaGarden((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(address,address,uint256,bytes32,bytes32))` | GardenFacet: ETH·Base·Arb·BNB·RH·Arc |
| `0xfc5f1003` | `startBridgeTokensViaGasZip((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes32,uint256))` | GasZipFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0x606326ff` | `swapAndStartBridgeTokensViaGasZip((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes32,uint256))` | GasZipFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0x194c869f` | `GAS_ZIP_ROUTER()` | GasZipFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0x6f9206ba` | `startBridgeTokensViaGlacis((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes32,address,uint256,bytes32))` | GlacisFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0x9c4b6dd9` | `swapAndStartBridgeTokensViaGlacis((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes32,address,uint256,bytes32))` | GlacisFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xbbbf77d5` | `AIRLIFT()` | GlacisFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| `0xf66fe519` | `startBridgeTokensViaGnosisBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool))` | GnosisBridgeFacet: ETH |
| `0x7bf96e0a` | `swapAndStartBridgeTokensViaGnosisBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[])` | GnosisBridgeFacet: ETH |
| `0xee9e98e0` | `startBridgeTokensViaLayerSwap((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes32,address,address,bytes32,bytes,uint256))` | LayerSwapFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0x4c279d6b` | `swapAndStartBridgeTokensViaLayerSwap((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes32,address,address,bytes32,bytes,uint256))` | LayerSwapFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0xb48fae2f` | `LAYERSWAP_DEPOSITORY()` | LayerSwapFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0x7dbcf1d9` | `startBridgeTokensViaLiFiIntentEscrowV2((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes32,bytes32,address,uint256,uint32,uint32,address,bytes32,bytes32,bytes32,uint128,(address,address,address,address,uint256,bytes,bool)[],bytes))` | LiFiIntentEscrowFacetV2: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0x6d21c5df` | `swapAndStartBridgeTokensViaLiFiIntentEscrowV2((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes32,bytes32,address,uint256,uint32,uint32,address,bytes32,bytes32,bytes32,uint128,(address,address,address,address,uint256,bytes,bool)[],bytes))` | LiFiIntentEscrowFacetV2: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0x6577661f` | `LIFI_INTENT_ESCROW_SETTLER_V2()` | LiFiIntentEscrowFacetV2: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0xb4875292` | `startBridgeTokensViaMayan((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes32,address,bytes,address,bytes,address,uint256,address,uint256))` | MayanFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x80c65808` | `swapAndStartBridgeTokensViaMayan((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes32,address,bytes,address,bytes,address,uint256,address,uint256))` | MayanFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xce90a721` | `MAYAN()` | MayanFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x4213dfff` | `startBridgeTokensViaMegaETHBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,uint32,bool))` | MegaETHBridgeFacet: ETH |
| `0x22256e89` | `swapAndStartBridgeTokensViaMegaETHBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(address,uint32,bool))` | MegaETHBridgeFacet: ETH |
| `0x3f44d05f` | `registerMegaETHBridge(address,address)` | MegaETHBridgeFacet: ETH |
| `0x4698f032` | `startBridgeTokensViaNEARIntents((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes32,bytes32,address,bytes32,uint256,uint256,address,bytes))` | NEARIntentsFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x02631b09` | `swapAndStartBridgeTokensViaNEARIntents((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes32,bytes32,address,bytes32,uint256,uint256,address,bytes))` | NEARIntentsFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xcc67a1aa` | `isQuoteConsumed(bytes32)` | NEARIntentsFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x782621d8` | `startBridgeTokensViaOmniBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool))` | OmniBridgeFacet: ETH·BNB |
| `0x95726782` | `swapAndStartBridgeTokensViaOmniBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[])` | OmniBridgeFacet: ETH·BNB |
| `0xce8a97a5` | `startBridgeTokensViaOptimismBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,uint32,bool))` | OptimismBridgeFacet: ETH |
| `0x5bb5d448` | `swapAndStartBridgeTokensViaOptimismBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(address,uint32,bool))` | OptimismBridgeFacet: ETH |
| `0xdecb09d7` | `registerOptimismBridge(address,address)` | OptimismBridgeFacet: ETH |
| `0x5080ffe2` | `startBridgeTokensViaPaxosTransit((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(((uint32,address,address),uint256,address,uint256,uint256,address,bytes32,uint256,bytes32),bytes,uint256,address))` | PaxosTransitFacet: ETH·RH |
| `0x637f1d04` | `swapAndStartBridgeTokensViaPaxosTransit((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(((uint32,address,address),uint256,address,uint256,uint256,address,bytes32,uint256,bytes32),bytes,uint256,address))` | PaxosTransitFacet: ETH·RH |
| `0xc3c7a5be` | `TRANSIT_STATION()` | PaxosTransitFacet: ETH·RH |
| `0xaf62c7d6` | `startBridgeTokensViaPolygonBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool))` | PolygonBridgeFacet: ETH |
| `0xb4f37581` | `swapAndStartBridgeTokensViaPolygonBridge((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[])` | PolygonBridgeFacet: ETH |
| `0xf434d6ca` | `startBridgeTokensViaPolymerCCTP((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(uint256,uint256,bytes32,bytes32,uint32,address,bytes))` | PolymerCCTPFacet: ETH·Base·Arb·OP·Poly·Avax·Arc |
| `0x17917a4e` | `swapAndStartBridgeTokensViaPolymerCCTP((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(uint256,uint256,bytes32,bytes32,uint32,address,bytes))` | PolymerCCTPFacet: ETH·Base·Arb·OP·Poly·Avax·Arc |
| `0x8eb8fd56` | `POLYMER_FEE_RECEIVER()` | PolymerCCTPFacet: ETH·Base·Arb·OP·Poly·Avax·Arc |
| `0xb8b32ff7` | `TOKEN_MESSENGER()` | PolymerCCTPFacet: ETH·Base·Arb·OP·Poly·Avax·Arc |
| `0xb4ecdca6` | `setChainIdToDomainId((uint256,uint32)[])` | PolymerCCTPFacet: ETH·Base·Arb·OP·Poly·Avax·Arc |
| `0x373abe8e` | `unsetChainIdToDomainId(uint256)` | PolymerCCTPFacet: ETH·Base·Arb·OP·Poly·Avax·Arc |
| `0x092e8fa4` | `startBridgeTokensViaRelayDepository((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes32,address))` | RelayDepositoryFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0xa3443faa` | `swapAndStartBridgeTokensViaRelayDepository((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes32,address))` | RelayDepositoryFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0xb94289bb` | `RELAY_DEPOSITORY()` | RelayDepositoryFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0x3f313808` | `startBridgeTokensViaSquid((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(uint8,string,string,string,address,(uint8,address,uint256,bytes,bytes)[],bytes,uint256,bool))` | SquidFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xa8f66666` | `swapAndStartBridgeTokensViaSquid((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(uint8,string,string,string,address,(uint8,address,uint256,bytes,bytes)[],bytes,uint256,bool))` | SquidFacet: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x14d53077` | `startBridgeTokensViaStargate((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(uint16,(uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address))` | StargateFacetV2: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xa6010a66` | `swapAndStartBridgeTokensViaStargate((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(uint16,(uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address))` | StargateFacetV2: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0xfb214c2f` | `tokenMessaging()` | StargateFacetV2: ETH·Base·Arb·OP·Poly·BNB·Avax |
| `0x0691ff78` | `startBridgeTokensViaSuperset((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(bytes,uint256,address,address,uint256,uint32,bytes,uint256))` | SupersetFacet: Base·Arb |
| `0xf26e657f` | `swapAndStartBridgeTokensViaSuperset((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(bytes,uint256,address,address,uint256,uint32,bytes,uint256))` | SupersetFacet: Base·Arb |
| `0x62308e85` | `POOL_MANAGER()` | SupersetFacet: Base·Arb |
| `0x5b1ee840` | `setChainIdToEid((uint256,uint32)[])` | SupersetFacet: Base·Arb |
| `0xe23b7a08` | `startBridgeTokensViaSymbiosis((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,bytes32,bytes,bytes,address,address,address[],address,bytes,bool,address,address,bytes,uint256,uint256,bytes))` | SymbiosisFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0xc46059b2` | `swapAndStartBridgeTokensViaSymbiosis((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(address,bytes32,bytes,bytes,address,address,address[],address,bytes,bool,address,address,bytes,uint256,uint256,bytes))` | SymbiosisFacet: ETH·Base·Arb·OP·Poly·BNB·Avax·RH·Arc |
| `0x2541ec57` | `startBridgeTokensViaThorSwap((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,string,uint256))` | ThorSwapFacet: ETH·Base·BNB·Avax |
| `0xad673d88` | `swapAndStartBridgeTokensViaThorSwap((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(address,string,uint256))` | ThorSwapFacet: ETH·Base·BNB·Avax |
| `0x64261d58` | `startBridgeTokensViaUnit((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,bytes,uint256))` | UnitFacet: ETH |
| `0x21a3af52` | `swapAndStartBridgeTokensViaUnit((bytes32,string,string,address,address,address,uint256,uint256,bool,bool),(address,address,address,address,uint256,bytes,bool)[],(address,bytes,uint256))` | UnitFacet: ETH |

Selectors of retired facet versions are no longer in any of the eight diamonds and are not listed. Example: NEARIntentsFacet 1.0.0 (`0xf8fA34D58A277060D07bCa7EC24D6B386d86a793` on Ethereum) had a 7-field `NEARIntentsData`; version 3.0.0 replaced it on 2026-09-29 ([diamond.md](diamond.md) §1.2).

---

## 2. Data structs of the entry points (field names from the verified ABIs)

| Facet | `<Bridge>Data` tuple |
|-------|----------------------|
| AcrossFacet | `(int64 relayerFeePct, uint32 quoteTimestamp, bytes message, uint256 maxCount) _acrossData` |
| AcrossFacetV4 | `(bytes32 receiverAddress, bytes32 refundAddress, bytes32 sendingAssetId, bytes32 receivingAssetId, uint256 outputAmount, uint128 outputAmountMultiplier, bytes32 exclusiveRelayer, uint32 quoteTimestamp, uint32 fillDeadline, uint32 exclusivityParameter, bytes message) _acrossData` |
| AcrossV4SwapFacet | `(uint8 swapApiTarget, bytes callData, bytes signature) _acrossV4SwapFacetData` |
| AllBridgeFacet | `(bytes32 recipient, uint256 fees, bytes32 receiveToken, uint256 nonce, uint8 messenger, bool payFeeWithSendingAsset) _allBridgeData` |
| ArbitrumBridgeFacet | `(uint256 maxSubmissionCost, uint256 maxGas, uint256 maxGasPrice) _arbitrumData` |
| CelerCircleBridgeFacet | `(uint256 maxFee, uint32 minFinalityThreshold) _celerCircleData` |
| CentrifugeFacet | `(uint256 nativeFee, address refundRecipient) _centrifugeData` |
| ChainflipFacet | `(bytes nonEVMReceiver, uint32 dstToken, address dstCallReceiver, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] dstCallSwapData, uint256 gasAmount, bytes cfParameters) _chainflipData` |
| DeBridgeDlnFacet | `(bytes receivingAssetId, bytes receiver, bytes orderAuthorityDst, uint256 minAmountOut) _deBridgeData` |
| EcoFacet | `(bytes nonEVMReceiver, address prover, uint64 rewardDeadline, bytes encodedRoute, bytes32 solanaATA, address refundRecipient, uint256 deadline, bytes signature) _ecoData` |
| FraxFacet | `(address oft, uint32 dstEid, uint256 nativeFee, address refundRecipient, bytes32 nonEVMReceiver) _fraxData` |
| GardenFacet | `(address redeemer, address refundAddress, uint256 timelock, bytes32 secretHash, bytes32 nonEvmReceiver) _gardenData` |
| GasZipFacet | `(bytes32 receiverAddress, uint256 destinationChains) _gasZipData` |
| GlacisFacet | `(bytes32 receiverAddress, address refundAddress, uint256 nativeFee, bytes32 outputToken) _glacisData` |
| LayerSwapFacet | `(bytes32 requestId, address depositoryReceiver, address refundRecipient, bytes32 nonEVMReceiver, bytes signature, uint256 deadline) _layerSwapData` |
| LiFiIntentEscrowFacetV2 | `(bytes32 dstCallReceiver, bytes32 recipient, address depositAndRefundAddress, uint256 nonce, uint32 expires, uint32 fillDeadline, address inputOracle, bytes32 outputOracle, bytes32 outputSettler, bytes32 outputToken, uint128 outputAmountMultiplier, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] dstCallSwapData, bytes outputContext) _lifiIntentData` |
| MayanFacet | `(bytes32 nonEVMReceiver, address mayanProtocol, bytes protocolData, address swapProtocol, bytes swapData, address middleToken, uint256 minMiddleAmount, address refundRecipient, uint256 mayanAmountIn) _mayanData` |
| MegaETHBridgeFacet | `(address assetIdOnL2, uint32 l2Gas, bool requiresDepositTo) _megaETHData` |
| NEARIntentsFacet | `(bytes32 nonEVMReceiver, bytes32 destinationAsset, address depositAddress, bytes32 quoteId, uint256 deadline, uint256 minAmountOut, address refundRecipient, bytes signature) _nearData` |
| OptimismBridgeFacet | `(address assetIdOnL2, uint32 l2Gas, bool isSynthetix) _optimismData` |
| PaxosTransitFacet | `(((uint32 destEID, address offerAsset, address wantAsset) route, uint256 offerAmount, address receiver, uint256 protocolFee, uint256 integratorFee, address integratorFeeReceiver, bytes32 distributorCode, uint256 deadline, bytes32 salt) quote, bytes signature, uint256 nativeFee, address refundRecipient) _paxosData` |
| PolymerCCTPFacet | `(uint256 polymerTokenFee, uint256 maxCCTPFee, bytes32 nonEVMReceiver, bytes32 solanaReceiverATA, uint32 minFinalityThreshold, address refundRecipient, bytes hookData) _polymerData` |
| RelayDepositoryFacet | `(bytes32 orderId, address depositorAddress) _relayDepositoryData` |
| SquidFacet | `(uint8 routeType, string destinationChain, string destinationAddress, string bridgedTokenSymbol, address depositAssetId, (uint8 callType, address target, uint256 value, bytes callData, bytes payload)[] sourceCalls, bytes payload, uint256 fee, bool enableExpress) _squidData` |
| StargateFacetV2 | `(uint16 assetId, (uint32 dstEid, bytes32 to, uint256 amountLD, uint256 minAmountLD, bytes extraOptions, bytes composeMsg, bytes oftCmd) sendParams, (uint256 nativeFee, uint256 lzTokenFee) fee, address refundAddress) _stargateData` |
| SupersetFacet | `(bytes path, uint256 amountOutMin, address refundAddress, address fallbackEoA, uint256 deadline, uint32 toEid, bytes options, uint256 lzFee) _supersetData` |
| SymbiosisFacet | `(address refundRecipient, bytes32 nonEvmReceiver, bytes firstSwapCalldata, bytes secondSwapCalldata, address firstDexRouter, address secondDexRouter, address[] approvedTokens, address callTo, bytes callData, bool viaOnchainSwapV3, address dex, address dexgateway, bytes onchainSwapData, uint256 fee, uint256 deadline, bytes signature) _symbiosisData` |
| ThorSwapFacet | `(address vault, string memo, uint256 expiration) _thorSwapData` |
| UnitFacet | `(address depositAddress, bytes signature, uint256 deadline) _unitData` |

Fields that name the destination or the refund: `receiverAddress` / `recipient` / `nonEVMReceiver` (the receiver on the destination chain), `refundAddress` / `refundRecipient` (where the underlying bridge refunds), `orderId` / `requestId` / `quoteId` (the underlying bridge's id), `depositAddress` (a one-time deposit address, for example NEAR Intents or Unit).

---

## 3. Facet addresses per chain (live table of 2026-09-29)

The "Version" column is the facet version recorded in `deployments/<network>.diamond.json`. The core facets are listed too, because a `DiamondCut` can replace them.

| Facet | Address | Version | Chains where this address is registered |
|-------|---------|---------|------------------------------------------|
| AccessManagerFacet | `0x77A13abB679A0DAFB4435D1Fa4cCC95D1ab51cfc` | 1.0.0 | ETH·Arb·OP·Poly·BNB·Avax |
| AccessManagerFacet | `0xFf296c17499C8eda2DdF61db580149bB819C804A` | 1.0.0 | Base |
| AccessManagerFacet | `0xE32fA08536068CA3A2B341D462AfD2D9C2528d7f` | 1.0.0 | RH |
| AccessManagerFacet | `0xb2CC627989D26766b1CB9259760FC873cD463598` | 1.0.0 | Arc |
| AcrossFacet | `0xBeE13d99dD633fEAa2a0935f00CbC859F8305FA7` | 2.0.0 | Arb·Poly |
| AcrossFacet | `0x98e3E949E8310D836A625495eA70eEAa92073862` | 2.0.0 | Base |
| AcrossFacetPackedV4 | `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` | 1.0.0 | ETH·Base·Arb·OP·Poly·BNB |
| AcrossFacetV4 | `0xAd3f1634a917924cBb54A0F76e43ca035D2B6BCd` | 1.0.0 | ETH·Base·Arb·OP·Poly·BNB |
| AcrossFacetV4 | `0xB2b9903cfCe365e1521D7B961bfCe0d6635D49a9` | 1.0.0 | RH |
| AcrossFacetV4 | `0xbfe96f30dCa6Dd1705A53E6a8DA32E9090f2eB75` | 1.0.0 | Arc |
| AcrossV4SwapFacet | `0x2beEf67989a236e9CA97E8F731050bf7E8039e90` | 1.0.0 | ETH·Base·Arb·OP·Poly·BNB |
| AllBridgeFacet | `0x317D089BBe46AaE816b27Eeb1ac26cFB7AB1850D` | 2.2.0 | ETH·Base·Arb·OP·Poly·BNB·Avax |
| ArbitrumBridgeFacet | `0xac82fA2D953Ee5C61d87686ADE620b0728F484E6` | 1.0.0 | ETH |
| CalldataVerificationFacet | `0x7A5c119ec5dDbF9631cf40f6e5DB28f31d4332a0` | 1.1.1 | ETH·Base·Arb·OP·Poly·BNB·Avax |
| CalldataVerificationFacet | `0xa5498A7a05A0C71b05e27B8558ccE13120B01387` | 1.3.1 | RH |
| CalldataVerificationFacet | `0x2aAf442EF000Cf62519FE379D945D89A594523de` | 1.3.1 | Arc |
| CelerCircleBridgeFacet | `0xB815B47ad429436892Fc3C6ed1D401F515C7F763` | 2.0.0 | ETH·Base·Arb·OP·Poly·Avax |
| CentrifugeFacet | `0x6275c64C1DA8919D1F7F5D558D36A6D750C74838` | 1.0.0 | ETH·Base |
| ChainflipFacet | `0xFa93141130a11FdaB7C6c800dfB93a5d19Da6aA4` | 1.0.0 | ETH·Arb |
| DeBridgeDlnFacet | `0x18C85B940c29ECC3c210Ea40a5B6d91F5aeE2803` | 1.0.0 | Base·Arb·Poly·BNB·Avax |
| DeBridgeDlnFacet | `0x108B0C3F20F266469fD2E98750926811aD632589` | 1.0.1 | ETH |
| DeBridgeDlnFacet | `0x007f2d2DDd83c12c73E9324F34493141a5d567d1` | 1.0.0 | OP |
| DiamondCutFacet | `0xf7993A8df974AD022647E63402d6315137c58ABf` | 1.0.0 | ETH·Arb·OP·Poly·BNB·Avax |
| DiamondCutFacet | `0xb09e20930242327f9aC4DA95dd0c421fbE15D4db` | 1.0.0 | Base |
| DiamondCutFacet | `0x4925491632d4688312433C428f94f9883a49C5a7` | 1.0.0 | RH |
| DiamondCutFacet | `0xbd85CfC8f613c3bb7b26B2a32CAe79d96b9208cA` | 1.0.0 | Arc |
| DiamondLoupeFacet | `0xF5ba8Db6fEA7aF820De35C8D0c294e17DBC1b9D2` | not recorded | ETH·OP·Poly·BNB |
| DiamondLoupeFacet | `0xc21a00a346d5b29955449Ca912343a3bB4c5552f` | 1.0.0 | Arb·Avax |
| DiamondLoupeFacet | `0x48Fb9d260c36709D48a9DfDef7c055672e445e8C` | 1.0.0 | Base |
| DiamondLoupeFacet | `0x02B307FfcE0b11120124Bc8209CC4fAEef933e69` | 1.0.0 | RH |
| DiamondLoupeFacet | `0x142F8679ba994e6697B7A472c2D0600C2F117FfA` | 1.0.0 | Arc |
| EcoFacet | `0x019f30c78535FAAAf19199A64E17E8FEC8C25181` | 2.0.0 | ETH·Base·Arb·OP·Poly·BNB |
| EcoFacet | `0xa385254749E33619a3f494490dDC5d413dC2A126` | 2.0.0 | Arc |
| EmergencyPauseFacet | `0xce52856e4d95220389350A822C60779D0D921E30` | 1.0.1 | ETH·Base·Arb·OP·Poly·BNB·Avax |
| EmergencyPauseFacet | `0xe85C0289e2f2Ff98f1Ccd0a58E643263b68Abf97` | 1.0.1 | RH |
| EmergencyPauseFacet | `0x9d9785F4C40a1FF1497fBE141219E94ccd89c008` | 1.0.1 | Arc |
| FraxFacet | `0x8452788daad6af88fe88BC5dFc892974C11C32Ad` | 1.0.0 | ETH·Base·Arb·OP·Poly·BNB·Avax |
| GardenFacet | `0xaa7911Ce0bab34fd8D4DdfA161004CB7e4BE1958` | 1.0.0 | Base·BNB |
| GardenFacet | `0xA20D724c81dDDe4A65f682A766881970245B31aF` | 1.0.0 | ETH |
| GardenFacet | `0xB2d2D9e94B8C690aE642c71B3Cc080E5893CE839` | 1.0.0 | Arb |
| GardenFacet | `0x19498b49FB4AA541fd208E4520a9Dc14a8A9d88E` | 1.0.0 | RH |
| GardenFacet | `0x6fE64248aecf7a8fC8a11cc63B804Bb75C2BAf04` | 1.0.0 | Arc |
| GasZipFacet | `0x65d6B9A368Be49bcA4964B66e54F828cAB64B8F9` | 2.0.4 | ETH·Base·Arb·OP |
| GasZipFacet | `0xB391B85Fcdecf94eA5f0EE96F64fFf7D9303B5bb` | 2.0.4 | Poly·BNB·Avax |
| GasZipFacet | `0x7FFE27a83a95bF814188C3244E06C8d497589287` | 2.0.5 | RH |
| GasZipFacet | `0x8d80bcbD33b2570d5233f5d5D051A90eCfefc7f0` | 2.0.5 | Arc |
| GenericSwapFacetV3 | `0x31a9b1835864706Af10103b31Ea2b79bdb995F5F` | 1.0.0 | Base·Arb·Poly·BNB·Avax |
| GenericSwapFacetV3 | `0x8C9dBA771220Ed09580b77F0765e7153fbDE7790` | 1.0.2 | ETH |
| GenericSwapFacetV3 | `0x8dFDaeBB42655a4A4e2b89687dd117074AE8c665` | 1.0.2 | OP |
| GenericSwapFacetV3 | `0xB129ce9C3fCD55726Ff314a2764d3937FA496071` | 2.0.0 | RH |
| GenericSwapFacetV3 | `0x0E60f12E2CE6b4EA51bde7A2aD61A22B12605c9C` | 2.0.0 | Arc |
| GlacisFacet | `0xd69e5eA7458aBFF098e9240f81F733898535c7A0` | 1.2.0 | ETH·OP·Poly·BNB |
| GlacisFacet | `0x6956df7664ACbd742cBCae485a57C4BFe3e075b3` | 1.2.0 | Base·Arb·Avax |
| GlacisFacet | `0x36DBCD6F5Afca9508261F4d533F91C55B41B5109` | 1.2.0 | RH |
| GnosisBridgeFacet | `0x9a82bB477c30D92dAB74875027E14D1De3510ef9` | 2.0.0 | ETH |
| LayerSwapFacet | `0x04E051D8e3627A79785f8E210B1d61A877AA737A` | 1.0.0 | ETH·Base·OP·Poly·BNB·Avax |
| LayerSwapFacet | `0x7Babf9c78e5c040B1bBd8981189ea4d6E3Fc8344` | 1.0.0 | Arb |
| LayerSwapFacet | `0x88545564793A470B511CC3E7e225a459bA29D291` | 1.0.0 | RH |
| LayerSwapFacet | `0x2af47e3266a5120b0C07658447aaD001680Fbb77` | 1.0.0 | Arc |
| LiFiIntentEscrowFacetV2 | `0x1B5c543CFe993ec1c89ad399E5433562A8CF4e05` | 1.0.0 | ETH·Base·Arb·OP·Poly·BNB |
| LiFiIntentEscrowFacetV2 | `0xf18E7d025BdB3e0DD952Cc9b20A977f6E296DF45` | 1.0.0 | Avax |
| LiFiIntentEscrowFacetV2 | `0xF824feC6aCdD168C9Db95B1Eaed18bf3E8Aae0FF` | 1.0.0 | RH |
| LiFiIntentEscrowFacetV2 | `0x821ABffbB6C0924B80454D8C73d98B9FB0471877` | 2.0.0 | Arc |
| MayanFacet | `0x124Aa9169E6c0851a4A54D0ebb9158f2313d9Dd8` | 2.0.0 | ETH·Base·Arb·OP·Poly·BNB·Avax |
| MegaETHBridgeFacet | `0xE46E9a5Ae71f1Fb3Ac59D09469830d6Ecc1D21f2` | 1.0.0 | ETH |
| NEARIntentsFacet | `0x8f00E690a45e75D7A1A765163829Ad33244a1C33` | 3.0.0 (verified source; not yet in the repository files) | ETH·Base·Arb·OP·Poly·BNB·Avax |
| OmniBridgeFacet | `0x7570E6b01e43df1b0c67f99C4156285AdC36c360` | 1.0.0 | ETH |
| OmniBridgeFacet | `0x3C826D17B47DB69E1a9C1e32E10768d3709f1b9A` | 1.0.0 | BNB |
| OptimismBridgeFacet | `0x54678c366682a29112609882DC58dEF6753BFC27` | 1.0.0 | ETH |
| OwnershipFacet | `0x6faA6906b9e4A59020e673910105567e809789E0` | 1.0.0 | ETH·Arb·OP·Poly·BNB·Avax |
| OwnershipFacet | `0x03106740Ec9558c8D1cb1076255E9a5c76bB1745` | 1.0.0 | Base |
| OwnershipFacet | `0xe1A910021eDf98F692c9fa08dC699e77e57bd794` | 1.0.0 | RH |
| OwnershipFacet | `0xefD77f2301a1AB2ca464f44025d17877B7930037` | 1.0.0 | Arc |
| PaxosTransitFacet | `0x5C47966EAAa5dbf30E20C1a01ED0acFCBCcF1349` | 1.0.0 | ETH |
| PaxosTransitFacet | `0x12A395526Dc6b257ddb6953b1a0e8Ae91Ac5Fd9b` | 1.0.0 | RH |
| PeripheryRegistryFacet | `0x69cb467EfD8044ac9eDB88F363309ab1cbFA0A15` | 1.0.0 | ETH·Arb·OP·Poly·BNB·Avax |
| PeripheryRegistryFacet | `0xf1269030deB739edB0b7dABA9b701E102116d86c` | 1.0.0 | Base |
| PeripheryRegistryFacet | `0x5C3C6cE45449d1d4A8B69Cb07Cf025147295c9d7` | 1.0.0 | RH |
| PeripheryRegistryFacet | `0xE33437Cf491C80FDC1D9d4Cd0EbeDCBcC7c9d188` | 1.0.0 | Arc |
| PolygonBridgeFacet | `0x99Fb0bAbBA2c437153D25Aff79DC80B905a27A5a` | 1.0.0 | ETH |
| PolymerCCTPFacet | `0x5E79e8C67CC7FEd03b283E84A5e16500f094B6b5` | 3.1.0 | ETH·Base·Arb·OP·Poly·Avax |
| PolymerCCTPFacet | `0xBbdFFF46eD41b4B56BC73ab6466D523C284Adc8A` | 3.1.0 | Arc |
| RelayDepositoryFacet | `0x88E0Dd83E6da24bF317323E5Ca06842406D57eD0` | 1.0.0 | ETH·Base·Arb·OP·Poly·BNB·Avax |
| RelayDepositoryFacet | `0x628Aa47ba1739EaBD021e7e48d308320cB984378` | 1.0.0 | RH |
| RelayDepositoryFacet | `0xC8CDF58E4ec70342B3A10bC870f081E34C3D526d` | 1.0.0 | Arc |
| SquidFacet | `0x5C2C3F56e33F45389aa4e1DA4D3a807A532a910c` | 1.0.0 | Base·Arb·Poly·BNB·Avax |
| SquidFacet | `0x03f58Dc7e2195A0c6F501BC4819066fd9dFe307F` | 1.0.0 | ETH |
| SquidFacet | `0xa7cc8D27420A8fA56353989F4c5db3b8FD9c7fE8` | 1.0.0 | OP |
| StargateFacetV2 | `0x6e378C84e657C57b2a8d183CFf30ee5CC8989b61` | 1.0.1 | Base·Arb·Poly·BNB·Avax |
| StargateFacetV2 | `0xbF4aD13FA0e6E05916a78C201f147c5152dbe1C9` | 1.0.1 | ETH |
| StargateFacetV2 | `0xb6424d61c2c3930c91D93E33D0654f9412bFDD81` | 1.0.1 | OP |
| SupersetFacet | `0x3556edeCDd99D567641F796cB2ac648006f4E257` | 1.1.0 | Base·Arb |
| SymbiosisFacet | `0xd04034AE565062D105D55C2de41C48A8838316FA` | 2.0.0 | Base·Arb·BNB·Avax |
| SymbiosisFacet | `0xa0353221443CA4E2e6A040F30A57B47F5A6d479D` | 2.0.0 | ETH·OP·Poly |
| SymbiosisFacet | `0x42caefaD13aD83ADCdd83c99Ae27058055CbF521` | 2.0.0 | RH |
| SymbiosisFacet | `0x69347aE9C155BA6dEba08a1dB2b6eFd76Db377CA` | 2.0.0 | Arc |
| ThorSwapFacet | `0x376f99f7EADE8A17f036fCff9eBA978E66e5fd28` | 1.2.0 | BNB·Avax |
| ThorSwapFacet | `0xcAefaC1Ea4DeC8fd866CBc5B6Dd3054f80d49B80` | 1.2.1 | ETH |
| ThorSwapFacet | `0x4BE836589E666fEA7D3E75a786b39E10E59a83ac` | 1.2.1 | Base |
| UnitFacet | `0x989a7eFaBb9bE76ac3424B940862d9cf55334873` | 1.0.1 | ETH |
| WhitelistManagerFacet | `0xb28Dd740D27853A91639795223AB409088A73E23` | 1.0.0 | ETH·Base·Arb·OP·Poly·BNB·Avax |
| WhitelistManagerFacet | `0x1dbaa8086B650a2b8B1ACD6993DF16b05896F6FA` | 1.1.0 | RH |
| WhitelistManagerFacet | `0x74971eEF6058f2AEBe87EF2759e996E5e4A8811D` | 1.1.0 | Arc |
| WithdrawFacet | `0x711e80A9c1eB906d9Ae9d37E5432E6E7aCeEdA0B` | 1.0.0 | Arb·Poly·BNB·Avax |
| WithdrawFacet | `0x94eF6D1702ac7E30a5CeF39dEE26FAb180C251Fe` | 1.0.0 | ETH·OP |
| WithdrawFacet | `0x3cC42345FdbfEaAD668074ba3F8d3f664A243188` | 1.0.0 | Base |
| WithdrawFacet | `0x68ff3e074F27F33DaDC45bAaCeE0fDd073dA987d` | 1.0.0 | RH |
| WithdrawFacet | `0x571AE718406d869400357cc5ae0ef94ED6065C73` | 1.0.0 | Arc |

Chain totals (facets / selectors): Ethereum 41 / 150, Base 34 / 134, Arbitrum 33 / 133, Optimism 29 / 121, Polygon 30 / 122, BNB 30 / 115, Avalanche 26 / 105, Robinhood Chain 19 / 68, Arc 19 / 71 (2026-10-05).

---

## 4. Cross-chain summary

| Chain | ID | Diamond | Bridge facets live | Missing compared with Ethereum |
|-------|----|---------|--------------------|--------------------------------|
| Ethereum | 1 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 31 | none |
| Base | 8453 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 24 | ArbitrumBridgeFacet, ChainflipFacet, GnosisBridgeFacet, MegaETHBridgeFacet, OmniBridgeFacet, OptimismBridgeFacet, PaxosTransitFacet, PolygonBridgeFacet, UnitFacet; extra: AcrossFacet, SupersetFacet |
| Arbitrum One | 42161 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 23 | ArbitrumBridgeFacet, CentrifugeFacet, GnosisBridgeFacet, MegaETHBridgeFacet, OmniBridgeFacet, OptimismBridgeFacet, PaxosTransitFacet, PolygonBridgeFacet, ThorSwapFacet, UnitFacet; extra: AcrossFacet, SupersetFacet |
| Optimism | 10 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 19 | ArbitrumBridgeFacet, CentrifugeFacet, ChainflipFacet, GardenFacet, GnosisBridgeFacet, MegaETHBridgeFacet, OmniBridgeFacet, OptimismBridgeFacet, PaxosTransitFacet, PolygonBridgeFacet, ThorSwapFacet, UnitFacet |
| Polygon PoS | 137 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 20 | ArbitrumBridgeFacet, CentrifugeFacet, ChainflipFacet, GardenFacet, GnosisBridgeFacet, MegaETHBridgeFacet, OmniBridgeFacet, OptimismBridgeFacet, PaxosTransitFacet, PolygonBridgeFacet, ThorSwapFacet, UnitFacet; extra: AcrossFacet |
| BNB Smart Chain | 56 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 20 | ArbitrumBridgeFacet, CelerCircleBridgeFacet, CentrifugeFacet, ChainflipFacet, GnosisBridgeFacet, MegaETHBridgeFacet, OptimismBridgeFacet, PaxosTransitFacet, PolygonBridgeFacet, PolymerCCTPFacet, UnitFacet |
| Avalanche C-Chain | 43114 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | 16 | AcrossFacetPackedV4, AcrossFacetV4, AcrossV4SwapFacet, ArbitrumBridgeFacet, CentrifugeFacet, ChainflipFacet, EcoFacet, GardenFacet, GnosisBridgeFacet, MegaETHBridgeFacet, OmniBridgeFacet, OptimismBridgeFacet, PaxosTransitFacet, PolygonBridgeFacet, UnitFacet |
| Robinhood Chain | 4663 | `0xB477751B76CF82d00a686A1232f5fCD772414Af3` | 9 | AcrossFacetPackedV4, AcrossV4SwapFacet, AllBridgeFacet, ArbitrumBridgeFacet, CelerCircleBridgeFacet, CentrifugeFacet, ChainflipFacet, DeBridgeDlnFacet, EcoFacet, FraxFacet, GnosisBridgeFacet, MayanFacet, MegaETHBridgeFacet, NEARIntentsFacet, OmniBridgeFacet, OptimismBridgeFacet, PolygonBridgeFacet, PolymerCCTPFacet, SquidFacet, StargateFacetV2, ThorSwapFacet, UnitFacet |
| Arc | 5042 | `0xA4072583658Fae592A3506A42431cb6316a8d40b` | 9 | AcrossFacetPackedV4, AcrossV4SwapFacet, AllBridgeFacet, ArbitrumBridgeFacet, CelerCircleBridgeFacet, CentrifugeFacet, ChainflipFacet, DeBridgeDlnFacet, FraxFacet, GlacisFacet, GnosisBridgeFacet, MayanFacet, MegaETHBridgeFacet, NEARIntentsFacet, OmniBridgeFacet, OptimismBridgeFacet, PaxosTransitFacet, PolygonBridgeFacet, SquidFacet, StargateFacetV2, ThorSwapFacet, UnitFacet |

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| All facets | Plain contracts, no proxy | They are logic behind the diamond. A new version is a new address; the diamond points to it through `diamondCut`. | Diamond owner (LiFiTimelockController, 3-hour minimum delay). The pauser wallet can remove a facet at once (`removeFacet`, `EmergencyFacetRemoved`). |
| AcrossFacetPackedV4 | Plain contract, also used standalone | Has its own `owner()` and `setApprovalForBridge(address[])`, used when it is called directly. | Its own owner (TransferrableOwnership) for the standalone functions. |

---

## 6. Detection invariants & gotchas

1. **Key on the selector, not on the facet address.** A call to the diamond with selector `0x80c65808` is `swapAndStartBridgeTokensViaMayan` on every chain that has the facet, whatever the facet address.
2. **Facet addresses differ by chain and by version.** One facet name can have three addresses (for example DeBridgeDlnFacet on Ethereum, on OP, and on the other chains). Do not hard-code them; read `facets()`.
3. **Chain-specific facets.** The canonical-bridge facets exist only on Ethereum (ArbitrumBridgeFacet, OptimismBridgeFacet, PolygonBridgeFacet, GnosisBridgeFacet, MegaETHBridgeFacet, UnitFacet). The Across facets are absent on Avalanche: its live table has none, and `deployments/avalanche.diamond.json` has no Across facet and empty `ReceiverAcrossV3` / `ReceiverAcrossV4` entries. Robinhood Chain and Arc have the smallest sets: 19 facets each (§4).
4. **Two Across generations are live.** The old AcrossFacet (V2 spoke pool interface) is still registered on Base, Arbitrum and Polygon next to AcrossFacetV4, AcrossV4SwapFacet and AcrossFacetPackedV4.
5. **Packed calls have no ABI arguments.** `startBridgeTokensViaAcrossV4NativePacked()` and `startBridgeTokensViaAcrossV4ERC20Packed()` read tightly packed calldata after the selector: bytes 4–11 are the first 8 bytes of the `transactionId`, which `LiFiAcrossTransfer(bytes8)` repeats. Use the `decode_*` helpers of the facet, or the Across `FundsDeposited` log of the same transaction, to read the rest.
6. **Retired selectors can come back.** A replaced facet's selectors disappear from the loupe. Historical transactions still carry them; decode old calls with the ABI of the facet version that was live at that block.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Bridge entry selectors (chain-agnostic; call the diamond) =====
SEL_START_ACROSS_V4                    = '\xa1f1ce43'
SEL_SWAP_START_ACROSS_V4               = '\x1794958f'
SEL_START_ACROSS_V4_SWAP               = '\x6a90d66e'
SEL_START_ACROSS_V4_NATIVE_PACKED      = '\xc5d60e97'
SEL_START_ACROSS_V4_ERC20_PACKED       = '\x36b92404'
SEL_START_ACROSS_V4_NATIVE_MIN         = '\x72dd147e'
SEL_START_ACROSS_V4_ERC20_MIN          = '\x7260352d'
SEL_START_RELAY_DEPOSITORY             = '\x092e8fa4'
SEL_SWAP_START_RELAY_DEPOSITORY        = '\xa3443faa'
SEL_START_MAYAN                        = '\xb4875292'
SEL_SWAP_START_MAYAN                   = '\x80c65808'
SEL_START_NEAR_INTENTS                 = '\x4698f032'
SEL_SWAP_START_NEAR_INTENTS            = '\x02631b09'
SEL_START_LAYERSWAP                    = '\xee9e98e0'
SEL_SWAP_START_LAYERSWAP               = '\x4c279d6b'
SEL_START_LIFI_INTENT_ESCROW_V2        = '\x7dbcf1d9'
SEL_SWAP_START_LIFI_INTENT_ESCROW_V2   = '\x6d21c5df'
SEL_START_GAS_ZIP                      = '\xfc5f1003'
SEL_SWAP_START_GAS_ZIP                 = '\x606326ff'
SEL_START_POLYMER_CCTP                 = '\xf434d6ca'
SEL_SWAP_START_POLYMER_CCTP            = '\x17917a4e'
SEL_START_STARGATE_V2                  = '\x14d53077'
SEL_SWAP_START_STARGATE_V2             = '\xa6010a66'
SEL_START_DEBRIDGE_DLN                 = '\x4004633e'
SEL_SWAP_START_DEBRIDGE_DLN            = '\x2c7d2db0'
SEL_START_GLACIS                       = '\x6f9206ba'
SEL_SWAP_START_GLACIS                  = '\x9c4b6dd9'
SEL_START_ECO                          = '\xbff90b61'
SEL_SWAP_START_ECO                     = '\x762aea18'
SEL_START_SYMBIOSIS                    = '\xe23b7a08'
SEL_SWAP_START_SYMBIOSIS               = '\xc46059b2'
SEL_START_ALLBRIDGE                    = '\x6a51e9a9'
SEL_SWAP_START_ALLBRIDGE               = '\x63267469'
SEL_START_CHAINFLIP                    = '\x0ad553b3'
SEL_SWAP_START_CHAINFLIP               = '\xee3314a1'
SEL_START_THORSWAP                     = '\x2541ec57'
SEL_SWAP_START_THORSWAP                = '\xad673d88'
SEL_START_SQUID                        = '\x3f313808'
SEL_SWAP_START_SQUID                   = '\xa8f66666'
SEL_START_GARDEN                       = '\x5f9af35d'
SEL_SWAP_START_GARDEN                  = '\x76ad76fe'
SEL_START_FRAX                         = '\x678786ea'
SEL_SWAP_START_FRAX                    = '\x07b8e4c7'
SEL_START_CELER_CIRCLE                 = '\xe0a4201c'
SEL_SWAP_START_CELER_CIRCLE            = '\x4f3b0759'
SEL_START_PAXOS_TRANSIT                = '\x5080ffe2'
SEL_SWAP_START_PAXOS_TRANSIT           = '\x637f1d04'
SEL_START_CENTRIFUGE                   = '\x0315138f'
SEL_SWAP_START_CENTRIFUGE              = '\x8fd4d4dd'
SEL_START_SUPERSET                     = '\x0691ff78'
SEL_SWAP_START_SUPERSET                = '\xf26e657f'
SEL_START_ACROSS_OLD                   = '\x1fd8010c'
SEL_SWAP_START_ACROSS_OLD              = '\x3a3f7332'
SEL_START_ARBITRUM_BRIDGE              = '\xc9851d0b'
SEL_START_OPTIMISM_BRIDGE              = '\xce8a97a5'
SEL_START_POLYGON_BRIDGE               = '\xaf62c7d6'
SEL_START_GNOSIS_BRIDGE                = '\xf66fe519'
SEL_START_MEGAETH_BRIDGE               = '\x4213dfff'
SEL_START_UNIT                         = '\x64261d58'
SEL_START_OMNIBRIDGE                   = '\x782621d8'

-- ===== Standalone packed facet (also a diamond facet) =====
ETH_LIFI_ACROSS_PACKED_V4              = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
BASE_LIFI_ACROSS_PACKED_V4             = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
ARB_LIFI_ACROSS_PACKED_V4              = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
OP_LIFI_ACROSS_PACKED_V4               = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
POLY_LIFI_ACROSS_PACKED_V4             = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
BNB_LIFI_ACROSS_PACKED_V4              = '\x8cd89ea14345f24d0299c2180aec97a417ca34e3'
```

---

## 8. Verification & sources

- **Selectors:** every live selector of the eight diamonds of 2026-09-29 was matched to a function of a verified facet ABI (explorer verification of the exact deployed facet), and recomputed as `keccak256(signature)[0:4]`. Robinhood Chain facets are not verified on its explorer; their selectors were matched to the verified ABIs of the same facet names on the other chains, and one selector (`extractNonEVMAddress(bytes)`) to the repository source. Arc facets (2026-10-05) were matched by name and address to `deployments/arc.json` and `deployments/arc.diamond.json`; 65 of their 71 selectors appear in the tables of this file and [diamond.md](diamond.md).
- **Facet table:** `facets()` read on 2026-09-29 on all eight diamonds and on 2026-10-05 on the Arc diamond; totals in §3.
- **`bridge` strings:** decoded from the data of every `LiFiTransferStarted` log of the diamond in the pinned window (Ethereum and Base).
- **Addresses:** from the live facet table; names and versions from the repository deployment files. Every facet address of §3 was existence-checked with `eth_getCode` on each chain where it is registered: Ethereum 41 of 41 have code; Base 34 of 34 have code; Arbitrum 33 of 33 have code; Optimism 29 of 29 have code; Polygon 30 of 30 have code; BNB 30 of 30 have code; Avalanche 26 of 26 have code; Robinhood Chain 19 of 19 have code; Arc 19 of 19 have code (2026-10-05).

Authoritative sources:
- [lifinance/contracts](https://github.com/lifinance/contracts) (`src/Facets/`, `deployments/<network>.json`, `deployments/<network>.diamond.json`, `docs/`)
- [LI.FI docs index](https://docs.li.fi/llms.txt) · [LI.FI smart contract addresses](https://docs.li.fi/introduction/lifi-architecture/smart-contract-addresses)
- Explorers with the verified facet sources: [Blockscout Ethereum](https://eth.blockscout.com) · [Blockscout Base](https://base.blockscout.com) · [Blockscout Arbitrum](https://arbitrum.blockscout.com) · [Blockscout Optimism](https://optimism.blockscout.com) · [Blockscout Polygon](https://polygon.blockscout.com)
