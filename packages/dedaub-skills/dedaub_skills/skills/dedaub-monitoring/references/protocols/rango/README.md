# Rango Exchange — reference index (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain + Arc)

**Rango** is a cross-chain DEX and bridge aggregator. On EVM chains it runs one **RangoDiamond** (EIP-2535) at the same address on every chain, `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d`, and a set of destination **middlewares** that receive bridged tokens with a message and finish the route (swap, then pay). Rango runs no bridge of its own: the value crosses chains through the underlying bridge (Relay, Across, CCTP, Chainflip, Stargate, Symbiosis, deBridge, THORChain and others), whose own reference doc covers the second leg.

**Status:** verified on 2026-09-29 against live RPC on the eight original chains (Arc added on 2026-10-05), the canonical `rango-exchange/rango-contracts-v2` repository, the Rango docs (smart-contract architecture, deployment addresses, message passing) and the explorer-verified sources of the live facets and middlewares. Topics and selectors recomputed as `keccak256(signature)`; the live facet table of every diamond read with `facets()`; every address existence-checked with `eth_getCode`.

| File | Covers | Pattern | Chains (of the 9) |
|------|--------|---------|-------------------|
| [diamond.md](diamond.md) | The RangoDiamond: source events (`RangoBridgeInitiated`, `RangoSwap`, `SendToken`, `FeeInfo`, `CallResult`), per-bridge events, admin events, entry selectors per facet, owner and facets per chain | EIP-2535 diamond, same address on 9 chains | all 9 |
| [middlewares.md](middlewares.md) | Destination middlewares (Across, CCTP V2, OFT, Stargate, Symbiosis, Satellite, Wormhole, cBridge, Chainflip, deBridge, Connext, Nitro) and the MiddlewaresWhitelistsStorage: `RangoBridgeCompleted`, refunds, message events, entry functions, addresses per chain | Plain contracts, two address sets | ETH·Base·Arb·OP·Poly·BNB·Avax |

## The flow of one transfer

| Leg | Contract | Event (topic0) | Value movement in the same transaction |
|-----|----------|----------------|----------------------------------------|
| **Source** | RangoDiamond | `RangoBridgeInitiated` (`0x012c155f3836c4edb9222305b909a109f9efa46288efffe40a0e66da3a9a9800`) | ERC-20 `Transfer` user → diamond or native `msg.value`; `FeeInfo` and `SendToken` for fees; `RangoSwap` and `CallResult` for source swaps; then diamond → underlying bridge (for example the Relay depository or the Across spoke pool) |
| Same-chain swap | RangoDiamond | `RangoSwap` (`0x0e9201911743fd4d03e146f00ad23945dc8f3ffc200906eff25179a52b726f17`) with `SendToken` to the receiver | Token in, swap, token out to the receiver |
| **Destination, plain route** | The underlying bridge | The bridge's own payout event | The bridge (or its relayer) pays the receiver. **No Rango event.** |
| **Destination, route with a message** | Bridge → Rango middleware | `RangoBridgeCompleted` (`0x71e2229d8c5917bef9d5c3b4b1df412ba65253373b25d1c117223dbaaaa7c8d8`) plus `SendToken`, `ActionDone`, `CrossChainMessageCalled` | Bridge → middleware → (swap) → `Transfer` middleware → receiver |
| **Refund** | Middleware or the bridge | `RangoBridgeCompleted` with `status` = 1 (RefundInSource), 2 (RefundInDestination) or 3 (SwapFailedInDestination); `Refunded`; `RangoUserRefunded` (CCTP V2 middleware) | Middleware → user; or the bridge's own refund |

## Link key

- **`requestId`** (an `address`-typed id chosen by the Rango API; in the measured logs it is a 16-byte value in the low bytes, with 4 leading zero bytes) is topic1 of `RangoBridgeInitiated`, `RangoSwap` and `RangoBridgeCompleted`. It is on chain on both sides only for routes with an interchain message (`hasInterchainMessage` = true), which end at a Rango middleware. Otherwise the destination leg carries only the underlying bridge's id (Relay `orderId`, Across `depositId`, CCTP `nonce`, and so on) from the same source transaction.
- Off chain, the Rango API tracks a swap by its request id and source transaction hash.

## Chain ids

`destinationChainId` in `RangoBridgeInitiated` is the EVM chain id for EVM destinations (1, 8453, 42161, 10, 137, 56, 43114, 4663, 5042). **Non-EVM destinations are ASCII codes packed into the integer**, measured in the pinned window: `1414680398` = `0x54524f4e` "TRON", `1279348289` = `0x4c414e41` "LANA" (Solana), `4346947` = `0x425443` "BTC", `5461321` = `0x535549` "SUI". For those rows `receiver` holds the first 20 ASCII characters of the non-EVM address, not an EVM address.

## Addresses at a glance

| Contract | Address | Chains |
|----------|---------|--------|
| **RangoDiamond** | `0x69460570c93f9DE5E2edbC3052bf10125f0Ca22d` | all 9 (same runtime code, 5,208 bytes) |
| RangoAcrossMiddleware | `0xd5C7176Ec638eF466c2Fee761762d9EAb673997d` | ETH·OP |
| RangoAcrossMiddleware | `0xB852e653f8FBC099F06DC9D61E269517a4990B73` | Base·Arb·Poly |
| RangoCCTPV2Middleware | `0xB5777E29aEEA886537E3fEF1c565F86e2d9760e8` | ETH·Base·Arb·OP·Poly·Avax |
| RangoOftMiddleware | `0x8B4A4A8b619ff52b0d35F74E4063F76cefCA618F` | ETH·Arb·OP·Poly·BNB·Avax |
| RangoStargateMiddleware | `0x5434eD2d9F5737986858de127545e8a2Fb6EB6aE` | ETH·OP |
| RangoStargateMiddleware | `0x7045F971e312f7F1e211b3085ACE9155DeB0a976` | Base·Arb·Poly·BNB·Avax |
| RangoSymbiosisMiddleware | `0x0b7728E6c51511E30788a3a393A3362d59Ca67Af` | ETH·OP |
| RangoSymbiosisMiddleware | `0x3Caed470a3215a4D6648D5c684c429B7A371C269` | Base·Arb·Poly·BNB·Avax |
| RangoSatelliteMiddleware | `0x901D602dCADE00e2d7384e3940a70Ef772A355c3` | ETH·OP |
| RangoSatelliteMiddleware | `0x0ADFb7975aa7c3aD90c57AEa8FDe5E31a721E9bb` | Base·Arb·Poly·BNB·Avax |
| RangoWormholeMiddleware | `0x93310c2A44C0Ea5B5381606d020980CC9B62f547` | ETH·OP |
| RangoWormholeMiddleware | `0x87f9bE4D0478dF182C95CBBd761381699B334342` | Base·Arb·Poly·BNB·Avax |
| RangoCBridgeMiddleware | `0xC1e311c06230C2fAe6425C07bB0a7C5fFCE9C785` | Arb·Poly·BNB·Avax |
| RangoChainFlipMiddleware | `0xB4231156BBF6025745046d9DE642A4eb242cD9ef` | ETH |
| RangoChainFlipMiddleware | `0x74C670A0BB4668F146FB5b97d0B4EA8eF60986dA` | Arb |
| RangoDeBridgeMiddleware | `0xD9Dc714D617608c273DA943840A17e4F1092D766` | ETH·OP |
| RangoDeBridgeMiddleware | `0x3Abaeb6399D3fc44838D75b88e642182e4b826fE` | Base·Arb·Poly·BNB·Avax |
| RangoConnextMiddleware | `0x0F415542e35A05A2655e2b1a0a95FE1cc74e84A3` | ETH·OP |
| RangoConnextMiddleware | `0x4a91efC961913fC24bFAE6BC3Eb5457e34e8F764` | Base·Arb·Poly·BNB |
| RangoNitroAssetForwarderMiddleware | `0x557BaBBa31BE0ca0571CF5dAf44fb8c42Ba10351` | ETH·OP |
| RangoNitroAssetForwarderMiddleware | `0xb05233e0779cA7952a27CBFF7c3820CFce9526b3` | Base·Arb·Poly·BNB·Avax |
| RangoMiddlewaresWhitelistsStorage | `0x89fE77AF04DB303d612D7e7F4C1c5E8664EDbEf6` | ETH·OP·Poly |
| RangoMiddlewaresWhitelistsStorage | `0x0484962f4Ff892Ee5608BE5eC80e2f461624a87C` | Base·Arb·Poly·BNB·Avax |

## Cross-cutting facts

1. **Same diamond address on all nine chains, different owner on each** ([diamond.md](diamond.md) §12).
2. **`RangoBridgeInitiated` exists in two versions.** The current one ends with `string dAppName`; the older one (`0xa551f5e7134cc110651fa6eb8a0423535b3ea90eedb01463af70e6798a75d426`) has no `dAppName`. Older facet functions that still emit it stay registered; it had 0 logs in the pinned window.
3. **`bridgeId` is a `uint8` topic.** Values 0–23 follow `IRango.BridgeType` (0 Across, 5 Stargate, 7 Thorchain, 16 CCTP, 19 DeBridge, 23 ChainFlip, and others). Higher values come from the Rango API through `genericBridge` and are not in the repository enum; in the pinned window the Ethereum diamond emitted `bridgeId` 56 (425 logs), 57, 60, 52, 51, 58, 55 and 59. The sample transaction with `bridgeId` 56 called the Relay depository.
4. **Robinhood Chain is live** with a reduced diamond: 7 facets (core, swapper, access manager, generic bridge, Across) and 137 `RangoBridgeInitiated` logs in the pinned window. **Arc** carries the same 7-facet diamond (Safe 1.5.0 owner `0xB1D330f5f1c467B76d5DB02315fEAA17CAbCBD01`) and emits Rango events (2026-10-05); no middleware has code there.
