# LI.FI — reference index (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain)

**LI.FI** is a bridge and DEX aggregator. One contract, the **LiFiDiamond** (EIP-2535), takes the user's funds, runs optional swaps, takes fees and calls an underlying bridge (Across, Relay, Mayan, NEAR Intents, Stargate, deBridge DLN, Glacis, Gas.zip, CCTP through Polymer, and others) in the same transaction. LI.FI runs no bridge of its own: the value crosses chains through the underlying bridge, whose own reference doc covers the second leg.

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the canonical `lifinance/contracts` repository (`deployments/*.json`, `src/`) and the explorer-verified sources. Topics and selectors recomputed as `keccak256(signature)`; every address existence-checked with `eth_getCode`; the live facet table of every diamond read with `facets()`.

| File | Covers | Pattern | Chains (of the 8) |
|------|--------|---------|-------------------|
| [diamond.md](diamond.md) | The LiFiDiamond: source-leg events (`LiFiTransferStarted` and its companions), same-chain swap events, admin and security events, admin and swap selectors, the diamond, owner timelock and pauser on each chain | EIP-2535 diamond, owned by a 3-hour timelock | all 8 |
| [facets.md](facets.md) | The bridge facets: entry selectors, data structs, facet addresses per chain, measured `bridge` strings | Facets behind the diamond | all 8 |
| [periphery.md](periphery.md) | Destination side (Executor and the bridge receivers), Permit2Proxy, ERC20Proxy, fee contracts, utilities, LiFiTimelockController | Immutable contracts, per-chain addresses | all 8 |

## The flow of one transfer

| Leg | Contract | Event (topic0) | Value movement in the same transaction |
|-----|----------|----------------|----------------------------------------|
| **Source** | LiFiDiamond | `LiFiTransferStarted` (`0xcba69f43792f9f399347222505213b55af8e0b0b54b893085c2e27ecbe1644f1`); for a non-EVM destination also `BridgeToNonEVMChainBytes32` (`0x815cd8dc72093a13fe3577112c391b6279303956526382ab98772d0239dbf78c`) or `BridgeToNonEVMChain` (`0xf9b69f466270c99522169d563c0a430e88c52865ec33b1cc36ee2a4a6ea5170b`) | ERC-20 `Transfer` user (or Permit2Proxy) → diamond, or native value in `msg.value`; fee transfers to FeeCollector / FeeForwarder; one `AssetSwapped` per swap step; then diamond → underlying bridge contract, which emits its own deposit event |
| Source (packed Across) | LiFiDiamond or the standalone AcrossFacetPackedV4 `0x8CD89Ea14345F24d0299c2180Aec97a417Ca34E3` | `LiFiAcrossTransfer(bytes8)` (`0xe11352fef0e24c9902a94910b5ce929151ea227f4c68572aada8f2105c66c133`) only | Token → Across spoke pool (`FundsDeposited` in the same transaction) |
| **Destination, plain route** | The underlying bridge | The bridge's own payout event (for example Across `FilledRelay`) | The bridge (or its relayer / solver) pays the receiver. **No LI.FI event.** |
| **Destination, route with a destination call** | Bridge → LI.FI receiver → Executor | Executor `LiFiTransferCompleted` (`0xb8c86983f929c6b770461983d1bbde1870408120f07123e9c12d49f35a0b4c4b`) and `AssetSwapped` | Bridge → receiver → Executor → DEX → Executor → final receiver |
| Destination, swap failed | LI.FI receiver | `LiFiTransferRecovered` (`0x1fbfa988fd46deed0de12c94c7b5dcb537d51b804246d0083f245f7a8997d170`) | Receiver sends the bridged token itself to the final receiver. This is a payout, not a refund. |
| **Refund / expiry** | The underlying bridge | The bridge's refund event (for example an Across refund to the depositor) | The refund address is a field of the facet data (`refundAddress` / `refundRecipient`, [facets.md](facets.md) §2). LI.FI has no refund event of its own. |

## Link keys

- **`transactionId` (`bytes32`)** is LI.FI's id for one route. It is on chain on the source side in `LiFiTransferStarted`, `BridgeToNonEVMChain*`, `AssetSwapped` and `NEARIntentsBridgeStarted`. It is on chain on the destination side only for routes with a destination call (`LiFiTransferCompleted`, `LiFiTransferRecovered`, destination `AssetSwapped`). The packed Across route carries only its first 8 bytes (`LiFiAcrossTransfer(bytes8)`).
- For plain routes, link the legs with the underlying bridge's own key from the same source transaction: Across `depositId`, Stargate / LayerZero `guid`, CCTP `nonce`, deBridge `orderId` (also in `DlnOrderCreated`), Relay `orderId`, NEAR Intents `quoteId` and `depositAddress`.
- Off chain, the LI.FI API links both transaction hashes and the `transactionId`: `GET https://li.quest/v1/status?txHash=<source or destination hash>`.

## Chain and domain ids

`destinationChainId` in `LiFiTransferStarted` is the EVM chain id for EVM chains: Ethereum 1, Base 8453, Arbitrum 42161, Optimism 10, Polygon 137, BNB 56, Avalanche 43114, Robinhood Chain 4663. LI.FI uses its own ids for other chains: Solana `1151111081099710`, Bitcoin `20000000000001`, Bitcoin Cash `20000000000002`, Litecoin `20000000000003`, Dogecoin `20000000000004`, Sui `9270000000000000`, Aptos `9271000000000010`, Tron `1885080386571452`, Stellar `1201081091099710`, HyperCore `1337`.

## Addresses at a glance

| Chain | ID | LiFiDiamond (source events) | Executor (`LiFiTransferCompleted`) | ReceiverAcrossV4 | ReceiverStargateV2 | Owner (timelock) |
|-------|----|-----------------------------|------------------------------------|------------------|--------------------|------------------|
| Ethereum | 1 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0xd9B2Da9C45b118e4e93A004FB1452bCDB6cC0E88` | `0x07Cc0a0b41641D349240e1988169Fa11b31FC24E` | `0xB539B40793171211DCA8834da044fC14bCe64BDC` | `0x55117ECcC867Db72aEb25f728CCf57C3C3B4faEe` |
| Base | 8453 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x4DaC9d1769b9b304cb04741DCDEb2FC14aBdF110` | `0x33b255b5db44A78c34381f89f1a454bc0Ef49871` | `0x1493e7B8d4DfADe0a178dAD9335470337A3a219A` | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` |
| Arbitrum One | 42161 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x2dfaDAB8266483beD9Fd9A292Ce56596a2D1378D` | `0x33b255b5db44A78c34381f89f1a454bc0Ef49871` | `0x1493e7B8d4DfADe0a178dAD9335470337A3a219A` | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` |
| Optimism | 10 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0xC9E66aa9b08EB667e450e072E96F7086AD9f2c91` | `0xe417AD5eb9e919567620A48B3757cc182cCdf9e4` | `0x556701899905f2f83AcA2977D3202Ee3a80f37b7` | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` |
| Polygon PoS | 137 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x2dfaDAB8266483beD9Fd9A292Ce56596a2D1378D` | `0x33b255b5db44A78c34381f89f1a454bc0Ef49871` | `0x1493e7B8d4DfADe0a178dAD9335470337A3a219A` | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` |
| BNB Smart Chain | 56 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x2dfaDAB8266483beD9Fd9A292Ce56596a2D1378D` | `0x33b255b5db44A78c34381f89f1a454bc0Ef49871` | `0x1493e7B8d4DfADe0a178dAD9335470337A3a219A` | `0x55117ECcC867Db72aEb25f728CCf57C3C3B4faEe` |
| Avalanche C-Chain | 43114 | `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` | `0x2dfaDAB8266483beD9Fd9A292Ce56596a2D1378D` | — | `0x1493e7B8d4DfADe0a178dAD9335470337A3a219A` | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` |
| Robinhood Chain | 4663 | `0xB477751B76CF82d00a686A1232f5fCD772414Af3` | `0x464fC28B9CbC1781286c8626B6E925275c8C14F1` | `0x90dd81bD07763f39dF31D0089B61520461557D71` | — | `0x6E9Beb6997dAE04122f1f8f8980f3dc8225443F3` |

Every contract of the table has code on its chain (checked with `eth_getCode` on 2026-09-29). **The diamond address `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE` is shared by seven chains; Robinhood Chain uses `0xB477751B76CF82d00a686A1232f5fCD772414Af3`.** On Ethereum that second address holds an unrelated LI.FI recovery contract (RobinhoodEthRecovery), not a diamond.

## Cross-cutting facts

1. **Filter by emitter.** LI.FI staging diamonds, the standalone AcrossFacetPackedV4 and LI.FI-derived diamonds of other aggregators emit the same topics ([diamond.md](diamond.md) §13).
2. **`LiFiTransferStarted` has no indexed field.** Decode `transactionId` (data word 1), `receiver` (word 6), `minAmount` (word 7) and `destinationChainId` (word 8) from the data.
3. **Non-EVM receivers.** `receiver` = `0x11f111f111f111F111f111f111F111f111f111F1` means "non-EVM destination": read the real receiver from `BridgeToNonEVMChain*` in the same transaction. Some routes (Relay depository, THORChain) emit no such event.
4. **The upgrade path is slow, the pause path is fast.** Facet changes go through the LiFiTimelockController (10,800 s minimum delay: watch `CallScheduled`). The pauser wallet `0xf9d8ba34a51750cf6abfa9de7acd37f182081a4a` can pause the diamond or remove a facet at once (`EmergencyPaused`, `EmergencyFacetRemoved`).
5. **Topics change with facet versions.** `NEARIntentsBridgeStarted` changed from 7 to 8 fields on 2026-09-29 ([diamond.md](diamond.md) §1.2). Index both versions.
6. **Robinhood Chain is live.** Its diamond emitted 3,139 `LiFiTransferStarted` logs in the pinned window 2026-09-28 00:00–12:00 UTC, and Robinhood Chain (4663) was the most frequent destination of the Ethereum and Base diamonds in that window ([facets.md](facets.md) §0).
