# Chainlink Data Feeds — Topics, Selectors, Addresses (Ethereum, Base, BSC, Avalanche, Arbitrum, Optimism, Polygon)

**Status:** verified on 2026-05-29. Topic0/selectors computed locally (keccak) and the well-known ones cross-checked against canonical Chainlink interfaces; addresses verified via `eth_getCode` (non-empty) + `description()`/`symbol()` on each chain's publicnode RPC.
**Scope:** Chainlink Data Feeds (a.k.a. Price Feeds) + Proof-of-Reserve feeds + L2 Sequencer Uptime feeds on Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137). The LINK token lives in [link-token.md](link-token.md).

Data Feeds use a **proxy → aggregator** split. Consumers always read a stable **`EACAggregatorProxy`** address; the proxy forwards `latestRoundData()`/etc. to the current underlying **aggregator** (`AccessControlledOffchainAggregator`, OCR) and bridges round IDs across "phases" — each aggregator swap increments `phaseId` and the high 16 bits of every `roundId` so historical reads stay monotonic. There are **thousands** of feed proxies across these chains; this doc gives the architecture, the chain-agnostic event/function constants, the discovery method, and a verified set of canonical/example addresses — not an exhaustive per-asset list (that's the [docs feed-address page](https://docs.chain.link/data-feeds/price-feeds/addresses) / the on-chain Feed Registry).

---

## 1. Contract types & versions

| Contract | Role / 1-liner |
|----------|----------------|
| **`EACAggregatorProxy`** (= `AggregatorProxy` + access control) | The stable, per-feed address every consumer calls. Forwards reads to `aggregator()`; encodes `phaseId` into the high bits of `roundId`. Owner can `proposeAggregator`/`confirmAggregator`. `version()` returns 4 or 6. **This is what every "feed address" below is.** |
| **`AccessControlledOCR2Aggregator`** / **`AccessControlledOffchainAggregator`** | The current OCR (Off-Chain Reporting) aggregator behind the proxy, with a `SimpleReadAccessController` read gate. Oracles submit one aggregated signed report per round via `transmit()`. Emits `NewTransmission` + `AnswerUpdated` + `NewRound`. Live `typeAndVersion()` varies by feed/generation — most canonical feeds today are **OCR2** (`"AccessControlledOCR2Aggregator 1.0.0"`, observed on the ETH/USD aggregators on Ethereum, BNB, Arbitrum); older feeds are **OCR1** (`"AccessControlledOffchainAggregator 3.0.0"`, observed on Optimism ETH/USD). OCR1 and OCR2 differ in their `transmit` selector and `NewTransmission` topic0 (see §2.1 / §3.3). |
| **`OffchainAggregator`** | Same as above without the read-access gate. Base OCR contract. |
| **`FluxAggregator`** | Legacy pre-OCR aggregator: each oracle calls `submit()` individually, on-chain median. Emits `SubmissionReceived`, `NewRound`, `AnswerUpdated`. Still behind older feeds/historical phases — relevant for historical log scans. |
| **`AggregatorFacade`** | Compatibility shim wrapping a bare aggregator to expose the full `AggregatorV2V3Interface`. |
| **`SimpleReadAccessController` / `AccessControllerInterface`** | Allowlist gating read access (`hasAccess(address,bytes)`). EOAs generally allowed; contract callers may be gated. |
| **`FeedRegistry`** | Ethereum-only on-chain registry resolving `(base, quote)` asset pairs → feed. See §4. |
| **L2 Sequencer Uptime Feed** | Special `AggregatorV3`-shaped feed on optimistic L2s; `answer` 0 = sequencer up, 1 = down; `startedAt` = last status-change timestamp. **Must be checked before trusting any price on an L2.** See §5. |

**Interface lineage:** `AggregatorInterface` (V2: `latestAnswer`/`latestRound`/`latestTimestamp` + `AnswerUpdated`/`NewRound` events) → `AggregatorV3Interface` (V3: `latestRoundData`/`getRoundData` + `decimals`/`description`/`version`) → `AggregatorV2V3Interface` (both). Feeds implement V2V3; **prefer `latestRoundData()`** — `latestAnswer()` is deprecated and has no staleness data.

---

## 2. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 2.1 Aggregator (OCR + Flux + proxy-forwarded)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f` | `AnswerUpdated(int256 indexed current, uint256 indexed roundId, uint256 updatedAt)` | aggregator — **the workhorse price-update event** |
| `0x0109fc6f55cf40689f02fbaad7af7fe7bbac8a3d2186600afc7d3e10cac60271` | `NewRound(uint256 indexed roundId, address indexed startedBy, uint256 startedAt)` | aggregator |
| `0xf6a97944f31ea060dfde0566e4167c1a1082551e64b60ecb14d599a9d023d451` | `NewTransmission(uint32 indexed aggregatorRoundId, int192 answer, address transmitter, int192[] observations, bytes observers, bytes32 rawReportContext)` | **OCR1** aggregator (`OffchainAggregator`) — fires once per OCR round; `answer` is the new price |
| `0xc797025feeeaf2cd924c99e9205acb8ec04d5cad21c41ce637a38fb6dee6016a` | `NewTransmission(uint32 indexed aggregatorRoundId, …)` — **OCR2** variant (extra config-digest/epoch fields in the unindexed tail; `aggregatorRoundId` still the sole indexed arg) | **OCR2** aggregator (`OCR2Aggregator`) — fires once per OCR2 round; **this is the topic0 the canonical ETH/USD feeds emit today**, not `0xf6a97944…` |
| `0x25d719d88a4512dd76c7442b910a83360845505894eb444ef299409e180f8fb9` | `ConfigSet(uint32 previousConfigBlockNumber, uint64 configCount, address[] signers, address[] transmitters, uint8 threshold, uint64 encodedConfigVersion, bytes encoded)` | OCR aggregator config change |
| `0x92e98423f8adac6e64d0608e519fd1cefb861498385c6dee70d58fc926ddc68c` | `SubmissionReceived(int256 indexed submission, uint32 indexed round, address indexed oracle)` | **FluxAggregator** (legacy) |
| `0x18dd09695e4fbdae8d1a5edb11221eb04564269c29a089b9753a6535c54ba92e` | `OraclePermissionsUpdated(address indexed oracle, bool indexed whitelisted)` | FluxAggregator |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed from, address indexed to)` | proxy + aggregator |
| `0xed8889f560326eb138920d842192f0eb3dd22b4f139c87a2c57538e05bae1278` | `OwnershipTransferRequested(address indexed from, address indexed to)` | 2-step ownable |
| `0x87286ad1f399c8e82bf0c4ef4fcdc570ea2e1e92176e5c848b6413545b885db4` | `AddedAccess(address user)` | access controller |
| `0x3d68a6fce901d20453d1a7aa06bf3950302a735948037deb182a8db66df2a0d1` | `RemovedAccess(address user)` | access controller |

> The OCR aggregator emits **both** `NewTransmission` (rich, OCR-native) and `AnswerUpdated` (legacy `AggregatorInterface`) on each round. **`NewTransmission` has two distinct topic0s by OCR generation** — OCR1 = `0xf6a97944…`, OCR2 = `0xc797025f…` — and the canonical feeds today are OCR2, so a monitor keyed only on the OCR1 topic0 would miss every OCR2 feed's transmissions. **`AnswerUpdated` (`0x0559884f…`) and `NewRound` (`0x0109fc6f…`) are emitted identically by both OCR1 and OCR2** (and by FluxAggregator), so they are the portable "new price" triggers — prefer them. **The proxy address does not emit `AnswerUpdated`** — it's emitted by the underlying aggregator, so to watch a feed you must resolve `proxy.aggregator()` and subscribe to *that* address (and re-resolve on `phaseId` change).

### 2.2 Proxy / EIP-1967 (only if a feed proxy is itself upgradeable — rare; most are plain `EACAggregatorProxy`)

`EACAggregatorProxy` is **not** an EIP-1967 proxy — it's a bespoke forwarder with a public `aggregator()` getter, not a delegatecall proxy. Aggregator swaps are tracked via `AnswerUpdated`/phase changes, not `Upgraded` events.

---

## 3. Function signatures (chain-agnostic)

### 3.1 AggregatorV2V3Interface (read on any feed proxy)

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xfeaf968c` | `latestRoundData()` | `(uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)` — **use this; check `updatedAt` for staleness** |
| `0x9a6fc8f5` | `getRoundData(uint80 _roundId)` | same 5-tuple for a historical round |
| `0x50d25bcd` | `latestAnswer()` | `int256` — **deprecated** (no staleness) |
| `0x668a0f02` | `latestRound()` | `uint256` |
| `0x8205bf6a` | `latestTimestamp()` | `uint256` |
| `0xb5ab58dc` | `getAnswer(uint256 roundId)` | `int256` |
| `0xb633620c` | `getTimestamp(uint256 roundId)` | `uint256` |
| `0x313ce567` | `decimals()` | `uint8` — **8 for USD pairs, 18 for ETH-quoted** |
| `0x7284e416` | `description()` | `string` — e.g. `"ETH / USD"` |
| `0x54fd4d50` | `version()` | `uint256` |

### 3.2 Proxy-specific

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x245a7bfc` | `aggregator()` | current underlying aggregator address |
| `0x58303b10` | `phaseId()` | `uint16` — increments on each aggregator swap |
| `0xc1597304` | `phaseAggregators(uint16)` | historical aggregator for a phase |
| `0xe8c4be30` | `proposedAggregator()` | aggregator pending `confirmAggregator` |
| `0xbc43cbaf` | `accessController()` | access controller address |
| `0xf8a2abd3` | `proposeAggregator(address)` | owner-only |
| `0xa928c096` | `confirmAggregator(address)` | owner-only; triggers phase bump |
| `0x8da5cb5b` | `owner()` | |

### 3.3 OCR aggregator-specific

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc9807539` | `transmit(bytes _report, bytes32[] _rs, bytes32[] _ss, bytes32 _rawVs)` | **OCR1** round-submission entrypoint (transmitter-only) |
| `0xb1dc65a4` | `transmit(bytes32[3] reportContext, bytes report, bytes32[] rs, bytes32[] ss, bytes32 rawVs)` | **OCR2** round-submission entrypoint (transmitter-only) — the canonical ETH/USD feeds today are OCR2 and call this, not `0xc9807539` |
| `0x81ff7048` | `latestConfigDetails()` | `(uint32 configCount, uint32 blockNumber, bytes16 configDigest)` |
| `0xe5fe4577` | `latestTransmissionDetails()` | `(bytes16 configDigest, uint32 epoch, uint8 round, int192 latestAnswer, uint64 latestTimestamp)` |
| `0x181f5a77` | `typeAndVersion()` | version string |
| `0x6b14daf8` | `hasAccess(address, bytes)` | access controller check |

---

## 4. Feed Registry — Ethereum mainnet only (chain ID 1)

| Contract | Address | Verified |
|----------|---------|----------|
| **FeedRegistry** | `0x47Fb2585D2C56Fe188D0E6ec628a38b74fCeeeDf` | ✅ (13310 B; absent on every other chain) |

On-chain registry mapping `(base, quote)` → feed, so consumers resolve a feed by token addresses / `Denominations` (e.g. `Denominations.ETH`, `Denominations.USD = 0x0000000000000000000000000000000000000348`) instead of hardcoding proxies. Key selectors: `latestRoundData(address base, address quote)` `0xbcfd032d`, `getFeed(address,address)` `0xd2edb6dd`, plus `decimals(base,quote)` / `description(base,quote)`. **Ethereum only** — no Feed Registry on the L2s/sidechains; there you must hardcode proxy addresses or use the docs page.

---

## 5. L2 Sequencer Uptime Feeds (per L2)

Before trusting any price on an optimistic rollup, read the uptime feed and require `answer == 0` (up) **and** that enough time has elapsed since `startedAt` (grace period, typically 3600 s). All verified (`description() = "L2 Sequencer Uptime Status Feed"`, `version() = 1`, 9571 B):

| Chain | Sequencer Uptime Feed | Verified |
|-------|------------------------|----------|
| Arbitrum One (42161) | `0xFdB631F5EE196F0ed6FAa767959853A9F217697D` | ✅ |
| Optimism (10) | `0x371EAD81c9102C9BF4874A9075FFFf170F2Ee389` | ✅ |
| Base (8453) | `0xBCF85224fc0756B9Fa45aA7892530B47e10b6433` | ✅ |

BNB, Avalanche, and Polygon PoS are not optimistic rollups and have **no** sequencer uptime feed.

---

## 6. Representative feed proxies (verified examples — NOT exhaustive)

All are `EACAggregatorProxy` addresses, verified via `eth_getCode` + `description()` (decimals = 8). Use these as canonical ETH/USD + BTC/USD anchors; resolve all other assets via the docs feed-address page or (Ethereum) the Feed Registry.

| Chain | ETH/USD | BTC/USD |
|-------|---------|---------|
| Ethereum (1) | `0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419` *(phase 7)* | `0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c` |
| Base (8453) | `0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70` | `0x64c911996D3c6aC71f9b455B1E8E7266BcbD848F` |
| BNB Chain (56) | `0x9ef1B8c0E4F7dc8bF5719Ea496883DC6401d5b2e` | `0x264990fbd0A4796A3E3d8E37C4d5F87a3aCa5Ebf` |
| Avalanche (43114) | `0x976B3D034E162d8bD72D6b9C989d545b839003b0` | `0x2779D32d5166BAaa2B2b658333bA7e6Ec0C65743` |
| Arbitrum One (42161) | `0x639Fe6ab55C921f74e7fac1ee960C0B6293ba612` | `0x6ce185860a4963106506C203335A2910413708e9` |
| Optimism (10) | `0x13e3Ee699D1909E989722E753853AE30b17e08c5` | `0xD702DD976Fb76Fffc2D3963D037dfDae5b04E593` |
| Polygon PoS (137) | `0xF9680D99D6C9589e2a93a78A04A279e509205945` | `0xc907E116054Ad103354f2D350FD2514433D57F6f` |

**Feed discovery (the right way to get them all):** there is no on-chain factory/registry that enumerates feeds on L2s. Either (a) scrape the [docs feed-address page](https://docs.chain.link/data-feeds/price-feeds/addresses) per chain, (b) on Ethereum walk the `FeedRegistry`, or (c) collect proxy addresses from your own config and resolve `aggregator()` per proxy, then index `AnswerUpdated`/`NewTransmission` on the resolved aggregator (re-resolving on `phaseId` change).

---

## 7. Detection invariants & gotchas

1. **Watch the aggregator, not the proxy, for events.** `AnswerUpdated`/`NewTransmission` are emitted by the underlying aggregator. Resolve `proxy.aggregator()` and subscribe to that; re-resolve whenever `phaseId()` changes (aggregator was swapped via `confirmAggregator`).
2. **`roundId` is phase-encoded.** A proxy `roundId` = `(phaseId << 64) | aggregatorRoundId`. Don't compare raw round IDs across phases. `NewTransmission.aggregatorRoundId` is the *phase-local* round.
3. **Always check staleness.** Use `latestRoundData().updatedAt` and compare to `block.timestamp` against the feed's heartbeat. `latestAnswer()` gives you no timestamp — avoid it.
4. **On L2s, gate on the sequencer uptime feed** (§5) with a grace period before trusting a price.
5. **`AnswerUpdated.current` and the answer are `int256`/`int192`** — signed. Negative is theoretically possible for some indices; most price feeds are positive. `decimals()` is per-feed (8 for USD, 18 for ETH-quoted, 0 for some indices).
6. **Two `ConfigSet` shapes exist.** The Data Feeds OCR `ConfigSet` (`0x25d719d8…`) is distinct from CCIP/Automation OCR2 `ConfigSet` — different arg tuple, different topic0. Match on the emitter contract.
7. **FluxAggregator vs OCR1 vs OCR2.** Pre-2021 feeds and some long-tail feeds still use `FluxAggregator` (per-oracle `SubmissionReceived`); modern feeds are OCR. **OCR comes in two generations with different constants:** OCR1 (`OffchainAggregator`, `typeAndVersion` `…3.0.0`) uses `transmit` `0xc9807539` and `NewTransmission` topic0 `0xf6a97944…`; OCR2 (`OCR2Aggregator`, `typeAndVersion` `AccessControlledOCR2Aggregator 1.0.0`) uses `transmit` `0xb1dc65a4` and `NewTransmission` topic0 `0xc797025f…`. The canonical ETH/USD feeds today are OCR2. A historical scan of one feed proxy may cross all three as phases changed — key OCR monitoring on the portable `AnswerUpdated`/`NewRound` topics rather than a single `NewTransmission`/`transmit` constant.
8. **Proof-of-Reserve feeds reuse the exact same interface** (`AggregatorV3`) — they're just feeds whose `answer` is a reserve balance. No separate ABI.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- Topics (chain-agnostic)
TOPIC_ANSWER_UPDATED        = '\x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'
TOPIC_NEW_ROUND             = '\x0109fc6f55cf40689f02fbaad7af7fe7bbac8a3d2186600afc7d3e10cac60271'
TOPIC_NEW_TRANSMISSION_OCR1 = '\xf6a97944f31ea060dfde0566e4167c1a1082551e64b60ecb14d599a9d023d451'
TOPIC_NEW_TRANSMISSION_OCR2 = '\xc797025feeeaf2cd924c99e9205acb8ec04d5cad21c41ce637a38fb6dee6016a'
TOPIC_OCR_CONFIG_SET        = '\x25d719d88a4512dd76c7442b910a83360845505894eb444ef299409e180f8fb9'
TOPIC_SUBMISSION_RECEIVED   = '\x92e98423f8adac6e64d0608e519fd1cefb861498385c6dee70d58fc926ddc68c'
TOPIC_OWNERSHIP_TRANSFERRED = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'

-- Selectors (read interface)
SEL_LATEST_ROUND_DATA       = '\xfeaf968c'
SEL_GET_ROUND_DATA          = '\x9a6fc8f5'
SEL_LATEST_ANSWER           = '\x50d25bcd'
SEL_DECIMALS                = '\x313ce567'
SEL_DESCRIPTION             = '\x7284e416'
SEL_VERSION                 = '\x54fd4d50'
SEL_AGGREGATOR              = '\x245a7bfc'
SEL_PHASE_ID                = '\x58303b10'
SEL_TRANSMIT_OCR1           = '\xc9807539'
SEL_TRANSMIT_OCR2           = '\xb1dc65a4'

-- Ethereum
ETH_FEED_REGISTRY           = '\x47fb2585d2c56fe188d0e6ec628a38b74fceeedf'
ETH_ETHUSD                  = '\x5f4ec3df9cbd43714fe2740f5e3616155c5b8419'
ETH_BTCUSD                  = '\xf4030086522a5beea4988f8ca5b36dbc97bee88c'
-- L2 sequencer uptime feeds
ARB_SEQ_UPTIME              = '\xfdb631f5ee196f0ed6faa767959853a9f217697d'
OP_SEQ_UPTIME               = '\x371ead81c9102c9bf4874a9075ffff170f2ee389'
BASE_SEQ_UPTIME             = '\xbcf85224fc0756b9fa45aa7892530b47e10b6433'
-- USD = Denominations.USD sentinel for FeedRegistry
DENOM_USD                   = '\x0000000000000000000000000000000000000348'
```

---

## 9. Verification & sources

- **Topic0 / selectors:** computed locally as `keccak256(canonical signature)` / `[0:4]` (pycryptodome). `AnswerUpdated`/`NewRound`/`latestRoundData` match the canonical `AggregatorV2V3Interface` and the widely-known live values.
- **Addresses:** `eth_getCode` (non-empty) on the 7 publicnode RPCs; feeds additionally confirmed by `description()` and `decimals()=8`; the ETH/USD Ethereum proxy reports `phaseId = 7` (phase mechanism live).
- **Sequencer feeds / Feed Registry:** verified deployed (9571 B / 13310 B respectively); Feed Registry confirmed absent on Base (Ethereum-only).
- Sources: [Data Feeds API reference](https://docs.chain.link/data-feeds/api-reference) · [Price Feed addresses](https://docs.chain.link/data-feeds/price-feeds/addresses) · [L2 Sequencer feeds](https://docs.chain.link/data-feeds/l2-sequencer-feeds) · [Feed Registry](https://docs.chain.link/data-feeds/feed-registry) · `smartcontractkit/chainlink` `contracts/src/v0.8/shared/interfaces/AggregatorV2V3Interface.sol` + `…/llo-feeds`/`…/shared/access`.
