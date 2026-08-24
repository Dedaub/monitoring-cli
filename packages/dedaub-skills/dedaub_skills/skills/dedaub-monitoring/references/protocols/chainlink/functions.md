# Chainlink Functions — Topics, Selectors, Addresses

**Status:** Router addresses verified via `eth_getCode` (non-empty, `len=49110` each) on Ethereum, Base, Avalanche, Arbitrum, Optimism, Polygon mainnet on 2026-05-29 (BNB has no Functions deployment). Topic0/selectors computed locally (keccak); `RequestStart` + `RequestProcessed` topics **confirmed against live Ethereum Router logs**, and core selectors confirmed in deployed Router bytecode. Topics/selectors chain-agnostic; addresses network-specific.

Chainlink Functions is **serverless off-chain compute** run by a DON. A consumer contract calls `FunctionsRouter.sendRequest(...)` referencing a funded **subscription**; the request is routed to the per-DON `FunctionsCoordinator`, executed off-chain, and the result is delivered back via `fulfillRequest` → the consumer's `_fulfillRequest` callback. Billing (LINK) flows through `FunctionsBilling`/the subscription.

## Functions — contract types

| Contract | Role |
|----------|------|
| `FunctionsRouter` | Stable entrypoint + subscription manager. `sendRequest`, `createSubscription`, `addConsumer`, `getSubscription`, `fulfill`. Holds the route table mapping `donId → Coordinator`. Emits `RequestStart`, `RequestProcessed`, `Subscription*`. |
| `FunctionsCoordinator` | Per-DON contract. Receives the routed request, runs OCR2 reporting over the DON, calls back into the Router to fulfill. Emits `OracleRequest` / `OracleResponse`, `ConfigSet`. Holds the `getDONID()`. |
| `FunctionsBilling` | Billing/fee logic mixed into the Coordinator (admin fee, gas overhead, LINK/native cost estimation). `oracleWithdraw`, `getAdminFee`, `getWeiPerUnitLink`. |

## Functions — event signatures (exact)

`topic0 = keccak256(signature)`. **† = confirmed against live Ethereum Router logs (2026-05-29).**

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xf67aec45c9a7ede407974a3e0c3a743dffeab99ee3f2d4c9a8144c2ebf2c7ec9` † | `RequestStart(bytes32 indexed requestId, bytes32 indexed donId, uint64 indexed subscriptionId, address subscriptionOwner, address requestingContract, address requestInitiator, bytes data, uint16 dataVersion, uint32 callbackGasLimit, uint96 estimatedTotalCostJuels)` | Router |
| `0x64778f26c70b60a8d7e29e2451b3844302d959448401c0535b768ed88c6b505e` † | `RequestProcessed(bytes32 indexed requestId, uint64 indexed subscriptionId, uint96 totalCostJuels, address transmitter, uint8 resultCode, bytes response, bytes err, bytes returnData)` | Router |
| `0x1a90e9a50793db2e394cf581e7c522e10c358a81e70acf6b5a0edd620c08dee1` | `RequestNotProcessed(bytes32 indexed requestId, address coordinator, address transmitter, uint8 resultCode)` | Router |
| `0xd6bf2929a5458fc22a90821275e4f54e2566c579e4bb3d38184880bf1701762c` | `OracleRequest(bytes32 indexed requestId, address indexed requestingContract, address requestInitiator, uint64 subscriptionId, address subscriptionOwner, bytes data, uint16 dataVersion, bytes32 flags, uint64 callbackGasLimit, ...)` — **flag arg tuple as approximate; recompute against target Coordinator** | Coordinator |
| `0xc708e0440951fd63499c0f7a73819b469ee5dd3ecc356c0ab4eb7f18389009d9` | `OracleResponse(bytes32 indexed requestId, address transmitter)` | Coordinator |
| `0x464722b4166576d3dcbba877b999bc35cf911f4eaf434b7eba68fa113951d0bf` | `SubscriptionCreated(uint64 indexed subscriptionId, address owner)` | Router |
| `0xd39ec07f4e209f627a4c427971473820dc129761ba28de8906bd56f57101d4f8` | `SubscriptionFunded(uint64 indexed subscriptionId, uint256 oldBalance, uint256 newBalance)` | Router |
| `0x43dc749a04ac8fb825cbd514f7c0e13f13bc6f2ee66043b76629d51776cff8e0` | `SubscriptionConsumerAdded(uint64 indexed subscriptionId, address consumer)` | Router |
| `0x182bff9831466789164ca77075fffd84916d35a8180ba73c27e45634549b445b` | `SubscriptionConsumerRemoved(uint64 indexed subscriptionId, address consumer)` | Router |
| `0xe8ed5b475a5b5987aa9165e8731bb78043f39eee32ec5a1169a89e27fcd49815` | `SubscriptionCanceled(uint64 indexed subscriptionId, address fundsRecipient, uint256 fundsAmount)` | Router |
| `0xe7d947486bc76b1f545e2d2f51439952b639f1dc571a9037a9888d0d2f4d1635` | `ConfigSet(uint16 maxConsumersPerSubscription, uint32 adminFee, bytes32[] allowListId, ...)` — **arg tuple approximate; Router/Coordinator have different ConfigSet shapes, recompute before decoding** | Router/Coordinator |

> **`RequestSent` / `RequestFulfilled` / `RequestProcessed` naming:** the legacy/consumer-helper events `RequestSent(bytes32)` (`0x1131…`) and `RequestFulfilled(bytes32)` (`0x85e1…`) are emitted by the **`FunctionsClient` consumer base contract**, not the Router. The Router uses `RequestStart` (sent) and `RequestProcessed` (fulfilled) — both confirmed live above. Monitor the Router pair for protocol-level coverage; monitor `RequestSent`/`RequestFulfilled` on the consumer if you index a specific dApp.
> `RequestSent(bytes32)` = `0x1131472297a800fee664d1d89cfa8f7676ff07189ecc53f80bbb5f4969099db8`, `RequestFulfilled(bytes32)` = `0x85e1543bf2f84fe80c6badbce3648c8539ad1df4d2b3d822938ca0538be727e6` (consumer-emitted).

## Functions — function signatures (exact)

4-byte selectors. **bold = confirmed present in live Ethereum FunctionsRouter bytecode.**

| selector | Function | On |
|----------|----------|----|
| **`0x461d2762`** | `sendRequest(uint64 subscriptionId, bytes data, uint16 dataVersion, uint32 callbackGasLimit, bytes32 donId) returns (bytes32 requestId)` | Router |
| **`0xa21a23e4`** | `createSubscription() returns (uint64)` | Router |
| **`0x7341c10c`** | `addConsumer(uint64 subscriptionId, address consumer)` | Router |
| **`0x9f87fad7`** | `removeConsumer(uint64 subscriptionId, address consumer)` | Router |
| **`0xa47c7696`** | `getSubscription(uint64 subscriptionId) returns (...)` | Router |
| **`0xc3f909d4`** | `getConfig() returns (...)` | Router |
| **`0xa9c9a918`** | `getContractById(bytes32 id) returns (address)` (route lookup) | Router |
| `0xdfaba794` | `fundSubscription(uint64)` — **NOT on Router.** Funding is done by sending LINK to the Router via `LinkToken.transferAndCall(router, amount, abi.encode(subId))` (`onTokenTransfer`). No direct `fundSubscription` selector. | n/a (LINK transferAndCall) |
| `0x940af431` | `getDONID() returns (bytes32)` — on the **Coordinator**, not the Router | Coordinator |
| `0xd1c6e6b8` | `fulfillRequest(bytes32,bytes,bytes,address,address)` — internal fulfill path (Coordinator → Router → consumer `handleOracleFulfillment`); the consumer callback the user overrides is `_fulfillRequest(bytes32,bytes,bytes)` | Coordinator/Router |
| `0x582c001c` | `startRequest((bytes32,uint96,address,uint64,uint16,bytes32,uint64,uint32,uint72,uint16,bytes))` (Router→Coordinator handoff) — arg tuple approximate | Router |

## Functions — Router addresses + DON IDs per chain

Routers verified non-empty bytecode (`len=49110`), 2026-05-29. DON ID string is hashed/right-padded to `bytes32` for `sendRequest` (e.g. `fun-ethereum-mainnet-1` → ascii bytes, right-padded).

| Chain | chainId | FunctionsRouter | Verified | DON ID (string) |
|-------|---------|-----------------|----------|-----------------|
| Ethereum | 1 | `0x65Dcc24F8ff9e51F10DCc7Ed1e4e2A61e6E14bd6` | yes | `fun-ethereum-mainnet-1` |
| Arbitrum One | 42161 | `0x97083E831f8F0638855e2A515c90EdCF158DF238` | yes | `fun-arbitrum-mainnet-1` |
| Base | 8453 | `0xf9B8fc078197181C841c296C876945aaa425B278` | yes | `fun-base-mainnet-1` |
| Optimism (OP) | 10 | `0xaA8AaA682C9eF150C0C8E96a8D60945BCB21faad` | yes | `fun-optimism-mainnet-1` |
| Avalanche C-Chain | 43114 | `0x9f82a6A0758517FD0AfA463820F586999AF314a0` | yes | `fun-avalanche-mainnet-1` |
| Polygon PoS | 137 | `0xdc2AAF042Aeff2E68B3e8E33F19e4B9fA7C73F10` | yes | `fun-polygon-mainnet-1` |
| BNB Smart Chain | 56 | **NOT SUPPORTED** | n/a | n/a |

> **BNB Smart Chain has no Functions deployment** — it is absent from Chainlink's supported-networks list for Functions (unlike Data Streams, where BNB is live). Functions mainnets: Ethereum, Arbitrum, Base, Optimism, Avalanche, Polygon (+ others not in scope). The DON ID is `bytes32(stringToBytes32("fun-<chain>-mainnet-1"))`; the `getDONID()` getter lives on the per-DON Coordinator, resolvable from the Router route table.

## Quick-copy bytea constants (Postgres)

```
-- topic0 (Router)
RequestStart      '\xf67aec45c9a7ede407974a3e0c3a743dffeab99ee3f2d4c9a8144c2ebf2c7ec9'
RequestProcessed  '\x64778f26c70b60a8d7e29e2451b3844302d959448401c0535b768ed88c6b505e'
SubscriptionCreated       '\x464722b4166576d3dcbba877b999bc35cf911f4eaf434b7eba68fa113951d0bf'
SubscriptionFunded        '\xd39ec07f4e209f627a4c427971473820dc129761ba28de8906bd56f57101d4f8'
SubscriptionConsumerAdded '\x43dc749a04ac8fb825cbd514f7c0e13f13bc6f2ee66043b76629d51776cff8e0'
-- consumer-emitted
RequestSent       '\x1131472297a800fee664d1d89cfa8f7676ff07189ecc53f80bbb5f4969099db8'
RequestFulfilled  '\x85e1543bf2f84fe80c6badbce3648c8539ad1df4d2b3d822938ca0538be727e6'
-- selectors
sendRequest          '\x461d2762'
createSubscription   '\xa21a23e4'
addConsumer          '\x7341c10c'
getSubscription      '\xa47c7696'
```

## Sources

- Chainlink docs — Data Streams onchain verification (verify(), ReportV3 struct): https://docs.chain.link/data-streams/reference/data-streams-api/onchain-verification
- Chainlink docs — Data Streams supported networks / crypto streams: https://docs.chain.link/data-streams/supported-networks , https://docs.chain.link/data-streams/crypto-streams
- VerifierProxy address source (canonical): https://github.com/smartcontractkit/documentation/blob/main/src/features/feeds/data/StreamsNetworksData.ts
- Chainlink docs — Functions supported networks (Router addresses + DON IDs): https://docs.chain.link/chainlink-functions/supported-networks
- On-chain verification: publicnode RPCs, `eth_getCode` + `eth_getLogs` + `eth_call(typeAndVersion/s_feeManager)`, 2026-05-29. Topic0/selectors via keccak256 (pycryptodome).
