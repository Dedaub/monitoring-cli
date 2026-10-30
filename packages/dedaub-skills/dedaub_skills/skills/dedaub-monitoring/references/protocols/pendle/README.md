# Pendle — Protocol Reference Index

Monitoring-grade references for **Pendle V2** (yield tokenization: SY → PT + YT, PT/SY AMM markets) across Ethereum (1), Arbitrum One (42161), Base (8453), BNB Smart Chain (56), Optimism (10) and Robinhood Chain (4663), with cross-chain PT periphery on Avalanche (43114). **Not deployed on Polygon PoS (137) or Arc (5042).** Verified against live RPC and `pendle-finance/pendle-core-v2-public` on 2026-10-30.

| File | Covers | Status |
|------|--------|--------|
| [v2.md](v2.md) | Router (`PendleRouterV4` + action facets), market factories V1/V3/V4/V5/V6 (V6 proxy runs V7 code), PT/YT factories, SY factory, per-market AMM, PT/YT/SY events, Limit Router, PY/LP oracle | **Live** on ETH, Arb, Base, BNB, OP, Robinhood |
| [governance.md](governance.md) | PENDLE token per chain, **sPENDLE** (live), vePENDLE / VotingController / fee distributors (deprecated), GaugeController, merkle distributors, LayerZero V1 governance messaging, PENDLE OFT (LZ V2), cross-chain PT (adapter factory, swap hub, OFT PT swapper, fixed-price PT AMM) | sPENDLE + gauges live; ve-system deprecated |

Pendle V1 (2021–2022, Ethereum and Avalanche, different contracts) is out of scope.

## Cross-cutting facts worth knowing before you start

- **Markets are immutable clones; factories stack.** Each market keeps its creating factory (`factory()`). Old-generation markets stay live until expiry. Index every factory generation per chain: ETH/Arb/BNB/OP have V1, V3, V4, V5, V6; Base has V5, V6; Robinhood Chain has V6 only.
- **Two `CreateNewMarket` topic0s.** V1 factory: 4-arg `0x166ae5f5…`. V3+: 5-arg `0xae811fae…`.
- **"marketFactoryV6" runs V7 code** (`PendleMarketFactoryV7Upg`, `VERSION()=7`) on ETH, Arb, Base, BNB and Robinhood. Optimism stays at 6.
- **One router address on six chains:** `0x888888888889758f76e7103c6cbf23abbf58f946`. It dispatches by selector to facets. The live facets differ from the registry JSON on five chains (only OP matches). Watch `SelectorToFacetSet`.
- **The router is the market's `caller`.** Attribute users from router events (`SwapPtAndToken`, `SwapYtAndToken`, `AddLiquiditySingleToken`, …) or the tx sender, not from the market `Swap.caller`.
- **Signed `int256` amounts** in market `Swap` and router swap events: positive = to the account.
- **Robinhood Chain is a real deployment** (lead `0x544bf81c855ae84c1e8b65d5e38770898d01eee2`, 2973 B TransparentUpgradeableProxy → `PendleMarketFactoryV7Upg` `0xb8b037ce…`; 18 markets). It is not a decoy forwarder.
- **Incentives moved from vePENDLE to sPENDLE.** The VotingController stopped broadcasting at Ethereum block 24,286,615. Gauge rates now come from owner calls (`UpdateMarketRewardV2`). sPENDLE `0x999999999991…4144` exists on Ethereum only.
- **PENDLE is a different token per chain:** native (ETH), Arbitrum gateway token, OP-Stack mintable (Base, OP), Wormhole wrapped (BNB), LayerZero V2 OFT (Robinhood, peered with ETH adapter `0xd7e67c97…e0e4`).
- **Deployer nonce reuse:** the same address can be a different Pendle contract on another chain (`0x17f100fb…` = OP V1 market factory and Base GaugeController). Always key on `(chainId, address)`.

## Verification methodology

- Topic0 / selectors recomputed locally with keccak-256 from the ABIs in npm `@pendle/core-v2@6.12.0` and `@5.0.0` (legacy V1/V3 market and voting contracts).
- Addresses from `deployments/<chainId>-core.json` and `-offchain-helper.json`; existence checked with `eth_getCode` on all nine chains; EIP-1967 impl/admin/beacon slots read live; router facets read with `selectorToFacet`; implementation names from Sourcify.
- Event topics confirmed in live logs on Robinhood Chain (router, markets, YT, SY, factories, gauge, OFT) and Ethereum (factories, sPENDLE, gauge, vePENDLE, VotingController, limit router, swap hub).

## Coverage caveats

- Individual markets, PT, YT and SY are not listed. Discover them from `CreateNewMarket`, `CreateYieldContract` and `DeployedSY`.
- Market counts were taken for Ethereum and Robinhood factories only.
- SY contracts have per-asset extra events (source in `pendle-finance/Pendle-SY-Public`); only the common `IStandardizedYield` events are listed.
- Pendle also runs on non-target chains (Mantle 5000, Sonic 146, Berachain 80094, HyperEVM 999, Plasma 9745, Unichain 130, X Layer 196, Monad 143, Katana 747474, others). They are not covered here.
