# Stargate — reference index

Stargate is a liquidity-pool bridge built on LayerZero. Each chain holds pools of the bridged asset; a transfer takes tokens into the source pool and pays them out of the destination pool. Two generations exist on the same chains with different contracts, events and chain ids. Index both; v2 carries the live traffic.

**Status:** all constants verified on 2026-10-01 against live RPC on the eight target chains, the Stargate v1 and v2 contract pages, and the `stargate-protocol/stargate` and `stargate-protocol/stargate-v2` repositories.

| File | Generation | Contracts | Proxy pattern | Chains (of the 8) | Status |
|------|-----------|-----------|---------------|-------------------|--------|
| [v2.md](v2.md) | **Stargate v2** (LayerZero V2, taxi and bus) | StargatePoolNative / USDC / USDT / EURC / METIS / mETH, TokenMessaging, CreditMessaging, FeeLibV1*, Treasurer, OFTWrapper | **None** (immutable); owner = OneSig per chain | ETH, Base, Arb, OP, Poly, BNB, Avax — **not Robinhood** | Live |
| [v1.md](v1.md) | **Stargate v1** (LayerZero V1) | Router, RouterETH, Bridge, Factory, Pool (per asset), STG, StargateComposer | **None** (immutable) | ETH, Base, Arb, OP, Poly, BNB, Avax — **not Robinhood** | Winding down: no swaps in the pinned window |

## Chain identifiers

| Chain | EVM chain id | LayerZero V2 eid (v2) | Stargate v1 / LayerZero V1 id (v1) | Stargate |
|-------|-------------:|----------------------:|-----------------------------------:|----------|
| Ethereum | 1 | 30101 | 101 | v1, v2 |
| BNB Smart Chain | 56 | 30102 | 102 | v1, v2 |
| Avalanche C-Chain | 43114 | 30106 | 106 | v1, v2 |
| Polygon PoS | 137 | 30109 | 109 | v1, v2 |
| Arbitrum One | 42161 | 30110 | 110 | v1, v2 |
| Optimism | 10 | 30111 | 111 | v1, v2 |
| Base | 8453 | 30184 | 184 | v1, v2 |
| Robinhood Chain | 4663 | 30416 | 416 | **none** |

The LayerZero endpoints, libraries and the generic OFT events are documented in [../layerzero/README.md](../layerzero/README.md); these files do not repeat them. On Robinhood Chain, LayerZero is deployed (eid 30416, `EndpointV2` `0x6f475642a6e85809b1c36fa62763669b1b48dd5b`) but Stargate is not: `eth_getCode` returns `0x` for all 151 Stargate literals of the other chains, and the v2 repository has no Robinhood deployment.

## Cross-cutting facts

1. **v2 link key = LayerZero `guid`.** Taxi: `OFTSent.guid` = `OFTReceived.guid`. Bus: `OFTSent.guid` is zero; the `BusRode` ticket id maps to a later `BusDriven.guid`, and all passengers of that bus share the `guid` on the destination ([v2.md](v2.md) §6).
2. **v1 link key = the LayerZero V1 nonce** of the Bridge path (`SendMsg.nonce` on the source; the V1 delivery log in the `SwapRemote` transaction on the destination). The pool events carry no id.
3. **The v2 pools emit the generic OFT events**, so a rule on `OFTSent` / `OFTReceived` by topic0 also catches every other OFT. Allow-list the pools, and exclude them from generic OFT rules to avoid double counting.
4. **Lock and release on all eight chains.** The target chains hold pools (no Hydra OFT mints there); the source leg is a transfer into the pool or native value, the destination leg is a payout from the pool.
5. **No proxies.** Neither generation is upgradeable through EIP-1967. Changes come through owner settings (`setAddressConfig`, `setPeer`, `setAssetId` in v2; `setBridge`, `setFeeLibrary`, `setSwapStop` in v1). The Ethereum owner of both generations is the OneSig `0xbe634b030feaab661300667eaf82510a3a025413` (threshold 5).
6. **Addresses are chain-specific and reused for other roles across chains** (for example `0x5634c4a5FEd09819E3c46D86A965Dd9447d86e47`: v2 `TokenMessaging` on Base, v2 USDC pool on Avalanche). Key every address on `(chain, address)`.
7. **Pinned-window activity (2026-09-28 00:00–12:00 UTC):** v2 `OFTSent` from the pools — Ethereum 105, Base 167, Arbitrum 154, Optimism 21, Polygon 13, BNB 128, Avalanche 2; v1 `Swap` — 0 on every chain.
