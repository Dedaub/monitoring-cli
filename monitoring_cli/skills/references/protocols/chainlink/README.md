# Chainlink — Protocol Reference Index

Monitoring-grade references for Chainlink's product suite across **Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137)**. Verified 2026-05-29.

Chainlink is not a single versioned protocol like Uniswap — it's a suite of products, each with its own versions. One file per product (each covers its versions):

| File | Product | Versions covered | Key contracts |
|------|---------|------------------|---------------|
| [data-feeds.md](data-feeds.md) | **Data Feeds** (Price Feeds, PoR, L2 Sequencer Uptime) | Flux (legacy) → OCR | `EACAggregatorProxy`, `AccessControlledOffchainAggregator`, `FeedRegistry` |
| [vrf.md](vrf.md) | **VRF** (verifiable randomness) | v1, v2, v2.5 | `VRFCoordinator`/`V2`/`V2_5`, `VRFV2Wrapper`/`V2PlusWrapper`, `BlockhashStore` |
| [automation.md](automation.md) | **Automation** (Keepers) | Keepers v1.x, Automation v2.0/2.1/2.2/2.3 | `KeeperRegistry`/`AutomationRegistry`, `AutomationRegistrar`, `AutomationForwarder` |
| [ccip.md](ccip.md) | **CCIP** (cross-chain) | v1.0/1.2/1.5/1.6 | `Router`, `OnRamp`/`OffRamp`, `CommitStore`, `FeeQuoter`/`PriceRegistry`, `ARMProxy`, `TokenAdminRegistry` |
| [data-streams.md](data-streams.md) | **Data Streams** (low-latency pull oracle) | v2.0 / V3 report schema | `VerifierProxy`, `Verifier`, `FeeManager`, `RewardManager` |
| [functions.md](functions.md) | **Functions** (serverless DON compute) | v1 | `FunctionsRouter`, `FunctionsCoordinator`, `FunctionsBilling` |
| [link-token.md](link-token.md) | **LINK token** (ERC-677) + PegSwap | — | LINK per chain, `transferAndCall`, PegSwap |

Each file follows the house shape: **Topics** (chain-agnostic `topic0 = keccak256(event sig)`) → **Function signatures** (chain-agnostic 4-byte selectors) → **Addresses** (network-specific) → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Proxy/aggregator split (Data Feeds):** consumers read a stable `EACAggregatorProxy`; events (`AnswerUpdated`/`NewTransmission`) come from the underlying aggregator. Resolve `proxy.aggregator()` and watch *that* address; re-resolve on `phaseId` change.
- **OCR2/OCR3 shared topics:** `Transmitted(bytes32,uint32)` (`0xb04e63db…`) and OCR `ConfigSet` shapes recur across Automation, CCIP, Data Streams, Functions. Always disambiguate by emitter contract, not topic0 alone.
- **LINK funding is `transferAndCall` (ERC-677), not `approve`** — watch the 4-arg `Transfer` (`0xe19260af…`) to coordinators/registries/routers. See [link-token.md](link-token.md).
- **CCIP uses uint64 chain selectors, NOT EVM chain IDs** — see [ccip.md §1](ccip.md).
- **Version drift changes topic0:** VRF v2→v2.5 (`subId` `uint64`→`uint256`) and Automation v1/v2.0/v2.1 (`UpkeepPerformed`) each have multiple version-specific topic0s. Pick by the contract's `typeAndVersion()`.
- **Deterministic-deploy address collisions are real:** e.g. VRF coordinator `0xd5D517…` is AVAX-v2 *and* Base-v2.5; Data Streams VerifierProxy `0xF276…98d1` is shared by BNB+Polygon. Always key by `(chainId, …)`.
- **L2 safety:** on Arbitrum/Optimism/Base, gate prices on the Sequencer Uptime Feed ([data-feeds.md §5](data-feeds.md)).

## Verification methodology

- **Topic0 / selectors:** computed locally with keccak-256 (pycryptodome) from canonical `smartcontractkit/chainlink` signatures; key ones cross-checked against live `eth_getLogs` (Data Feeds `AnswerUpdated`, VRF v2.5 `RandomWordsRequested`, Automation v2.1/v2.3 events, Functions `RequestStart`/`RequestProcessed`, Data Streams `ReportVerified`) and against deployed bytecode for selectors.
- **Addresses:** every listed address `eth_getCode`-verified non-empty on its chain's publicnode RPC; versions read via `typeAndVersion()` (`0x181f5a77`); proxy/aggregator links read live.
- **Product/chain availability** confirmed against the official `docs.chain.link` supported-networks pages and the `smartcontractkit/chain-selectors` repo.

## Coverage caveats (read these)

- **Data Feeds** lists architecture + canonical ETH/USD & BTC/USD anchors per chain, not all ~thousands of per-asset feeds — resolve the rest via the docs feed-address page or the Ethereum `FeedRegistry`.
- **CCIP** lists Routers (all 7, verified) + chain selectors + Ethereum support contracts; per-chain RMN/FeeQuoter/TokenAdminRegistry/lane-ramps are version-specific — resolve via `Router.getOnRamp`/`getOffRamps` or the (JS-rendered) CCIP Directory.
- **Send-side / OCR3 struct-carrying events** (CCIP `CCIPSendRequested`/`CCIPMessageSent`, VRF v2.5 `ConfigSet`, Data Streams OCR3 `ConfigSet`, Functions `OracleRequest`) have large version-specific tuples; their topic0s are flagged in-doc and should be recomputed against the exact deployed contract before decoding.
