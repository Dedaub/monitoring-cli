# Circle StableFX — Topics, Selectors, Addresses (Arc only; NOT on the other eight targets)

**Status:** verified on 2026-10-30 against live RPC on Arc (`https://rpc.mainnet.arc.io`) and on the eight other target chains, Arc's contract-address page and Circle's StableFX docs. No public source repository exists. Topics and selectors were recomputed as `keccak256(signature)` and found in the deployed implementation or in its linked libraries (bytecode scan). The workhorse events were matched against live logs.
**Scope:** Circle StableFX, the RFQ stablecoin FX venue (USDC ⇄ EURC). One on-chain contract: **FxEscrow** on Arc (5042). Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon PoS (137) and Robinhood Chain (4663) return `0x` at the FxEscrow address. Topics and selectors are chain-agnostic; the address is Arc-specific.

StableFX prices off chain and settles on chain. A taker asks Circle's StableFX API for a quote. Approved makers quote through Talos. Circle's relayer then sends one `recordTrade` to FxEscrow with the EIP-712 signatures of both parties. The taker funds the trade with a Permit2 transfer (`takerDeliver`). The maker funds next (`makerDeliver` or a net delivery). The maker funding settles the trade in the same transaction: FxEscrow pays both sides and the fee wallet.

Three facts to know before indexing:

1. **The trade `id` is the link key.** It is topic1 of every trade event (`TradeRecorded`, `TakerFunded`, `MakerFunded`, `TradeStatusChanged`, `FeesProcessed`). `lastTradeId()` = 1,943 (`0x797`) on 2026-10-30.
2. **One relayer sends almost all calls.** In a 120,000-block sample, 59 of 60 transactions came from the EOA `0x3f66a5ae970788246c43017f034efba102265acc` (`relayers(addr)` = true). The trader addresses are in the event topics and in `getTradeDetails(id)`, not in `tx.from`.
3. **Pull is by Permit2.** Funds move by `Permit2.permitWitnessTransferFrom` into FxEscrow, then by plain ERC-20 transfers out. The token `Transfer` logs come from USDC `0x3600…0000` and EURC `0xbEf5…21c1`, not from FxEscrow.

---

## 0. Contract families & the flow

| Contract | Role | Proxy | Chains |
|----------|------|-------|--------|
| **FxEscrow** | Records trades, holds escrowed funds, settles, refunds and marks breaches. | **UUPS** (ERC1967Proxy, 130-byte runtime) | Arc only |
| FxEscrow libraries (linked) | Four external libraries hold most logic and emit most events (`DELEGATECALL`, so logs come from the proxy). | not proxies | Arc |
| Permit2 | Pulls the trader funds (`0x000000000022d473030f116ddee9f6b43ac78ba3`, read live with `permit2()`). | shared infrastructure | — |
| Circle StableFX API + Talos | Quotes, signature collection, relaying. | off chain | — |

| Step | Call (selector) | Event(s) | Value movement |
|------|-----------------|----------|----------------|
| Record | `recordTrade` `0x7b9422c3` (relayer) | `TradeRecorded(id, quoteId)` | none |
| Taker funds | `takerDeliver` `0xa3e98b04` / `takerBatchDeliver` `0x08e91ee3` | `TakerFunded(id, taker)` | quote token: taker → FxEscrow |
| Maker funds and settle | `makerDeliver` `0x35e2958e` / `makerBatchDeliver` `0xa92d86c6` / `makerNetDeliver` `0x0b5242b0` | `MakerFunded(id, maker)` + `FeesProcessed(id, feeRecipient, takerFee, makerFee)` + `TradeStatusChanged(id, actor, 2)` | base token: maker → FxEscrow; then FxEscrow → taker, → maker, → fee recipient |
| Advance (delegate) | `*DelegateDeliver` (§2.1) | `TakerDelegateFunded` / `MakerDelegateFunded` | a third party funds one side |
| Refund | `refundTaker` / `refundMaker` / `refund` and batch forms | `TakerRefunded` / `MakerRefunded` | escrow → the funded party |
| Breach | `breach(uint256)` / `batchBreach(uint256[])` | `TradeStatusChanged` | none by itself |

Sample on 2026-10-30: trade `0x796` was taker-funded in tx `0x2d0b15ac96fa9646e2f731709e1b6607d121d085cbccf04bec8f2707b8acfd75` and settled in tx `0xbd951dd972e9330f0e8d4adbc1f2d7b98de16bd2e4ffa7258442440b8cd32ea1` (`MakerFunded`, `FeesProcessed`, `TradeStatusChanged` with status 2). Every one of the 76 `TradeStatusChanged` logs in the sample carried status 2 (settled after maker funding).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

`✓ log` = seen in live Arc logs (blocks 28,542,962–28,662,961, 2026-10-29/30). `✓ code` = topic constant found in the implementation or in a linked library. Event names come from the verified Arc-testnet FxEscrow ABI and from a public signature database.

### 1.1 Trade lifecycle

| topic0 | Event | Evidence |
|--------|-------|----------|
| `0x2614fcea77560c7095ea181b7f810b48af39499760aeeed440be79db28c1ba75` | `TradeRecorded(uint256 indexed id, bytes32 indexed quoteId)` | ✓ log (80) |
| `0x04a32bd17d403350ba1edad0aeac7d61f93257b8e3a8890f4308c7206efadbfe` | `TakerFunded(uint256 indexed id, address indexed taker)` | ✓ log (79) |
| `0x27010dd935a76095c06a5c85372e3eeec074340c892e02dd771454c702cc7175` | `MakerFunded(uint256 indexed id, address indexed maker)` | ✓ log (76) |
| `0xaf897ce251cd696d11380febc2db1305f35441cfcf2a88c673885c643f29280d` | `FeesProcessed(uint256 indexed id, address indexed feeRecipient, uint256 takerFee, uint256 makerFee)` | ✓ log (76) |
| `0x509c70ba99799df13e09af7eec0632b96e1c0d779a87d040848eaa491f05443c` | `TradeStatusChanged(uint256 indexed id, address indexed actor, uint8 newStatus)` | ✓ log (76) |
| `0x60469f41c078fb52fc7e45e846b61dbbd98fbaa181c0e6d02a1e41cbd744aad2` | `TradeAuthorized(uint256,address,bytes32)` | ✓ code (indexing not seen) |
| `0xde704ed51c6db41bc8a80b714d8648d33e15a472a728a1677d6028d137e87f49` | `TakerDelegateFunded(uint256,address,address)` | ✓ code |
| `0x48a9b2d5c97b340bbf96adb9e926980c18e769b5527ee92500c3fec571bb5aed` | `MakerDelegateFunded(uint256,address,address)` | ✓ code |
| `0xcc219d6e8a41021b27aa51185d5795672e1044a31e34fa394d0f18f55a7178d5` | `TakerRefunded(uint256,address)` | ✓ code |
| `0x308c2bf01eac35987b18da95db6373b4c482a82aaffb03e09cdc6c6af935f4fd` | `MakerRefunded(uint256,address)` | ✓ code |

The older testnet ABI had `FeesProcessed(uint256 indexed id, uint256 takerFee, uint256 makerFee)` (`0xf3b92bac10eca6b22ab7eb9e11474efe0a46765ca7dd7700877f4f776997beb9`). That topic is **not** in the mainnet code. Use the four-argument form.

### 1.2 Admin

| topic0 | Event | Evidence |
|--------|-------|----------|
| `0x03580ee9f53a62b7cb409a2cb56f9be87747dd15017afc5cef6eef321e4fb2c5` | `RelayerAdded(address indexed relayer)` | ✓ code |
| `0x10e1f7ce9fd7d1b90a66d13a2ab3cb8dd7f29f3f8d520b143b063ccfbab6906b` | `RelayerRemoved(address indexed relayer)` | ✓ code |
| `0x0bc21fe5c3ab742ff1d15b5c4477ffbacf1167e618228078fa625edebe7f331d` | `FeeRecipientChanged(address oldRecipient, address newRecipient)` | ✓ code |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address)` | ✓ code |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address)` | ✓ code |
| `0x1ff153f4b082245afbf3211a8d2d207da4c5df490e965f9a9ad141b0cd001dda` | `PauserUpdated(address,address)` | ✓ code |
| `0x1d6bf6e0a370ac6883f3122294c413906f5147d33e00d83d1c829a3444ae3000` | **unidentified** admin event in the admin library (no match in public signature databases) | ✓ code |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` | ✓ code |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | ✓ code |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | ✓ log (1, 2026-10-30) |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` | ✓ code |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All selectors below are in the live implementation `0x59ac322681578a8c671b3be687f72919010285c2` (PUSH4 scan).

### 2.1 Trade calls

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7b9422c3` | `recordTrade(address,((address,uint256),uint256,uint256,((bytes32,address,address,uint256,uint256,uint256),address,uint256,address),bytes),address,((address,uint256),uint256,uint256,((bytes32,address,address,uint256,uint256,uint256),address,uint256,address),bytes))` | Relayer only. Args: taker, taker permit + `TraderDetails` witness, maker, maker permit + witness. Returns `id`. Emits `TradeRecorded`. The testnet form `0x2439f76e` is not in the mainnet code. |
| `0x78c4134c` | `authorizeTrade(address,(…TraderDetails…),address,(…TraderDetails…),address,(…AuthorizerDetails…))` | Records a trade with a third-party authorizer witness. Full tuple from a public signature database; selector in the code. |
| `0xa3e98b04` | `takerDeliver(uint256,((address,uint256),uint256,uint256),bytes)` | Taker funds one trade by Permit2 → `TakerFunded`. |
| `0x08e91ee3` | `takerBatchDeliver(uint256[],((address,uint256)[],uint256,uint256),bytes)` | Taker funds many trades. |
| `0x35e2958e` | `makerDeliver(uint256,((address,uint256),uint256,uint256),bytes)` | Maker funds and settles → `MakerFunded` + `FeesProcessed` + `TradeStatusChanged`. |
| `0xa92d86c6` | `makerBatchDeliver(uint256[],((address,uint256)[],uint256,uint256),bytes)` | Maker funds many trades. |
| `0x0b5242b0` | `makerNetDeliver(uint256[],((address,uint256)[],uint256,uint256),bytes)` | Maker funds only the net position across trades with one taker. |
| `0x786410a4` / `0xe1ab03ab` | `takerDelegateDeliver(...)` / `makerDelegateDeliver(...)` | A delegate (Circle's settlement advance) funds one side. |
| `0xe6afd743` / `0x3ddb716b` / `0xce546ba9` | `takerBatchDelegateDeliver(...)` / `makerBatchDelegateDeliver(...)` / `makerNetDelegateDeliver(...)` | Batch and net delegate forms. |
| `0xa8cdfc1a` / `0xf8d01089` | `refundTaker(uint256)` / `batchRefundTaker(uint256[])` | Return escrowed taker funds. |
| `0x7f06264e` / `0xaa3f17d8` | `refundMaker(uint256)` / `batchRefundMaker(uint256[])` | Return escrowed maker funds. |
| `0x278ecde1` / `0x05424c54` | `refund(uint256)` / `batchRefund(uint256[])` | Refund both sides. |
| `0x7e70d962` / `0x24924c92` | `breach(uint256)` / `batchBreach(uint256[])` | Mark a matured, unfunded trade as breached. |

### 2.2 Admin

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xdd39f00d` / `0x60f0a5ac` | `addRelayer(address)` / `removeRelayer(address)` | Owner only. |
| `0xe74b981b` | `setFeeRecipient(address)` | Owner only. |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | Pauser only. |
| `0x554bab3c` | `updatePauser(address)` | Owner only. |
| `0xf2fde38b` / `0x79ba5097` / `0x715018a6` | `transferOwnership(address)` / `acceptOwnership()` / `renounceOwnership()` | Two-step ownership. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | UUPS upgrade, owner only. |

### 2.3 Views

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x695730a5` | `getTradeDetails(uint256)` | Trade struct (tokens, taker, maker, recipient, amounts, fees, risk buffers, maturity, statuses). The mainnet layout differs from the testnet ABI. |
| `0x1e6c598e` | `trades(uint256)` | Raw storage getter. |
| `0x52bcfd5b` | `lastTradeId()` | `uint256`. |
| `0x5300f841` | `relayers(address)` | `bool`. |
| `0xe693e3fd` / `0x55768a2f` / `0x3b0c4b13` | `getMakerNetBalances(uint256[])` / `getMakerTotalBaseBalances(uint256[])` / `getTakerTotalQuoteBalances(uint256[])` | Netting helpers. |
| `0x46904840` | `feeRecipient()` | `address`. |
| `0x12261ee7` | `permit2()` | `address`. |
| `0x9fd0506d` / `0x5c975abb` | `pauser()` / `paused()` | |
| `0xa77b017e` | `MAX_MATURITY_DURATION()` | `345,600` s (4 days), read live. |
| `0x8da5cb5b` / `0xe30c3978` | `owner()` / `pendingOwner()` | |

---

## 3. Addresses — Arc (chain ID 5042)

All read with `eth_getCode` / `eth_getStorageAt` / `eth_call` on `https://rpc.mainnet.arc.io` on 2026-10-30.

| Role | Address | One-liner |
|------|---------|-----------|
| **FxEscrow** (proxy) | `0xe2E5F173576B513d994073CCbDaCBE027d43DFe6` | 130 B ERC1967Proxy; created at block 2,219,820 (2026-05-28). |
| FxEscrow implementation | `0x59ac322681578a8c671b3be687f72919010285c2` | 23,579 B; live since block 28,653,632 (2026-10-30 13:27 UTC). |
| Linked library (admin) | `0xaa5a1b7c53e46fc81a76c6a00cdf159b27b3d45f` | 1,333 B; relayer, fee recipient, pause and pauser events. |
| Linked library (settlement) | `0x6fdf20cec61120c75d4da1e8e0dc0b46bae05693` | 13,142 B; `FeesProcessed`, delegate funding, `TradeStatusChanged`. |
| Linked library (maker funding) | `0xafefec32e9143d56e0cf0b008e7ab3d0529c30cc` | 5,868 B; `MakerFunded`, `TradeStatusChanged`. |
| Linked library (signatures) | `0x36aaa42a4b71132197595b4a3ba964c2f13a25f5` | 5,298 B; EIP-712 witness types, `TradeAuthorized`. |
| `owner()` | `0x2cd71b282e7e46ba3fe88955e7af368a8970c916` | EOA; sent the 2026-10-30 upgrade. |
| `pauser()` | `0x1f27b824a5ac02e8d23482b3614f53079346b01c` | EOA. |
| `feeRecipient()` | `0x7ee042f21fba1bb5fc6185cf4c3ef8b956a4c62c` | EOA (StableFX fee wallet). |
| Relayer (observed) | `0x3f66a5ae970788246c43017f034efba102265acc` | EOA; `relayers()` = true. |
| Traded tokens | USDC `0x3600000000000000000000000000000000000000` · EURC `0xbEf5f6d51CB62b58e6A8f77868681825C6fe21c1` | See [../circle_tokens/README.md](../circle_tokens/README.md). |
| Arc testnet (not mainnet) | `0xd68256f4D69C6BbEcB873D8588AE0Dc6B8E22E10` (current); `0x867650F5eAe8df91445971f14d89fd84F0C9a9f8` (older) | Testnet only. Do not index on mainnet. |

## 4. Cross-chain summary

| Chain | ID | FxEscrow |
|-------|----|----------|
| Arc | 5042 | ✅ `0xe2E5…DFe6` |
| Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon PoS | 1, 8453, 56, 43114, 42161, 10, 137 | ❌ `0x` |
| Robinhood Chain | 4663 | ❌ `0x` |

Circle's StableFX contract page lists Arc mainnet and Arc testnet only.

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **FxEscrow** | **UUPS** (ERC1967Proxy) | 130 B runtime; EIP-1967 impl slot set; admin slot `0x0`; `proxiableUUID()` and `upgradeToAndCall` in the implementation; `UPGRADE_INTERFACE_VERSION()` = `5.0.0`. | `owner()` EOA `0x2cd7…c916`. |

Implementation history (EIP-1967 slot read at sampled blocks and bisected; a short-lived implementation between samples could be missed):

| From block | Date | Implementation |
|-----------|------|----------------|
| 2,219,820 | 2026-05-28 | `0x5bf849e6550383f83107d5dd1d77648bc05284e9` |
| 5,840,893 | 2026-06-18 | `0xbd01a88ae56f9dd6791dfc39079387901d77cc6d` (22,550 B; other linked libraries) |
| 28,653,632 | 2026-10-30 | `0x59ac322681578a8c671b3be687f72919010285c2` (current) |

The linked libraries change with each implementation. The old implementation `0xbd01…cc6d` links `0x1844d5d7abe2cf43602abd845ee2ea59adcc6c3e`, `0xbbd5ec5f31dfd60f2b58d4db469f4167a68a5498`, `0x0ed59c8f5a4fc59723a9593286139bdd8940dda1` and `0x9947402567e47313744cf2c6fd9918be13e1e7ef`.

## 6. Detection invariants & gotchas

1. **Logs come from the proxy, but the code is in libraries.** A topic scan of the implementation alone misses `FeesProcessed`, `MakerFunded`, `TakerDelegateFunded` and others. Scan the linked libraries too.
2. **`FeesProcessed` changed shape.** Mainnet emits the four-argument form with `feeRecipient` as topic2. The three-argument testnet topic does not occur on mainnet.
3. **`TradeStatusChanged.actor` is the caller, not a trader.** In the sample it is always the relayer `0x3f66…5acc`. Read `getTradeDetails(id)` or join `TakerFunded.taker` / `MakerFunded.maker` for the parties.
4. **`TradeRecorded.quoteId` (topic2) is the off-chain quote id.** It joins the chain record to Circle API trade records. It is a `bytes32` with the UUID in the low 16 bytes.
5. **A settled trade has three events in one tx.** `MakerFunded` + `FeesProcessed` + `TradeStatusChanged(status 2)`. A `TakerFunded` with no later `MakerFunded` before maturity is a breach candidate. Watch `breach`, `refund*` and the refund events.
6. **Maturity cap.** `MAX_MATURITY_DURATION` = 4 days. Circle's tenors are 30 minutes, 1 hour and 1 day.
7. **The contract upgraded on 2026-10-30.** Watch `Upgraded` on the proxy. The new implementation added the delegate, refund, authorizer and pause surfaces.
8. **Admin triggers.** `Upgraded`, `OwnershipTransferStarted`, `RelayerAdded`/`RelayerRemoved`, `FeeRecipientChanged`, `Paused`, `PauserUpdated`, and the unidentified `0x1d6bf6e0…3000`. Owner, pauser and fee wallet are EOAs.
9. **Blacklist checks.** The implementation calls `isBlacklisted(address)` (`0xfe575a87`) on an external contract and has the error `AddressBlacklisted(address,address)`. A blocklisted trader makes funding revert; no event is emitted.
10. **No FxEscrow off Arc.** Do not expect StableFX settlement on any other target chain.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_TRADE_RECORDED            = '\x2614fcea77560c7095ea181b7f810b48af39499760aeeed440be79db28c1ba75'
TOPIC_TAKER_FUNDED              = '\x04a32bd17d403350ba1edad0aeac7d61f93257b8e3a8890f4308c7206efadbfe'
TOPIC_MAKER_FUNDED              = '\x27010dd935a76095c06a5c85372e3eeec074340c892e02dd771454c702cc7175'
TOPIC_FEES_PROCESSED            = '\xaf897ce251cd696d11380febc2db1305f35441cfcf2a88c673885c643f29280d'
TOPIC_TRADE_STATUS_CHANGED      = '\x509c70ba99799df13e09af7eec0632b96e1c0d779a87d040848eaa491f05443c'
TOPIC_TRADE_AUTHORIZED          = '\x60469f41c078fb52fc7e45e846b61dbbd98fbaa181c0e6d02a1e41cbd744aad2'
TOPIC_TAKER_DELEGATE_FUNDED     = '\xde704ed51c6db41bc8a80b714d8648d33e15a472a728a1677d6028d137e87f49'
TOPIC_MAKER_DELEGATE_FUNDED     = '\x48a9b2d5c97b340bbf96adb9e926980c18e769b5527ee92500c3fec571bb5aed'
TOPIC_TAKER_REFUNDED            = '\xcc219d6e8a41021b27aa51185d5795672e1044a31e34fa394d0f18f55a7178d5'
TOPIC_MAKER_REFUNDED            = '\x308c2bf01eac35987b18da95db6373b4c482a82aaffb03e09cdc6c6af935f4fd'
TOPIC_RELAYER_ADDED             = '\x03580ee9f53a62b7cb409a2cb56f9be87747dd15017afc5cef6eef321e4fb2c5'
TOPIC_RELAYER_REMOVED           = '\x10e1f7ce9fd7d1b90a66d13a2ab3cb8dd7f29f3f8d520b143b063ccfbab6906b'
TOPIC_FEE_RECIPIENT_CHANGED     = '\x0bc21fe5c3ab742ff1d15b5c4477ffbacf1167e618228078fa625edebe7f331d'
TOPIC_PAUSED                    = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                  = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_PAUSER_UPDATED            = '\x1ff153f4b082245afbf3211a8d2d207da4c5df490e965f9a9ad141b0cd001dda'
TOPIC_UNIDENTIFIED_ADMIN        = '\x1d6bf6e0a370ac6883f3122294c413906f5147d33e00d83d1c829a3444ae3000'
TOPIC_OWNERSHIP_TRANSFER_STARTED= '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'
TOPIC_OWNERSHIP_TRANSFERRED     = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_UPGRADED                  = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors (chain-agnostic) =====
SEL_RECORD_TRADE                = '\x7b9422c3'
SEL_AUTHORIZE_TRADE             = '\x78c4134c'
SEL_TAKER_DELIVER               = '\xa3e98b04'
SEL_TAKER_BATCH_DELIVER         = '\x08e91ee3'
SEL_MAKER_DELIVER               = '\x35e2958e'
SEL_MAKER_BATCH_DELIVER         = '\xa92d86c6'
SEL_MAKER_NET_DELIVER           = '\x0b5242b0'
SEL_TAKER_DELEGATE_DELIVER      = '\x786410a4'
SEL_MAKER_DELEGATE_DELIVER      = '\xe1ab03ab'
SEL_TAKER_BATCH_DELEGATE_DELIVER= '\xe6afd743'
SEL_MAKER_BATCH_DELEGATE_DELIVER= '\x3ddb716b'
SEL_MAKER_NET_DELEGATE_DELIVER  = '\xce546ba9'
SEL_REFUND                      = '\x278ecde1'
SEL_BATCH_REFUND                = '\x05424c54'
SEL_REFUND_TAKER                = '\xa8cdfc1a'
SEL_BATCH_REFUND_TAKER          = '\xf8d01089'
SEL_REFUND_MAKER                = '\x7f06264e'
SEL_BATCH_REFUND_MAKER          = '\xaa3f17d8'
SEL_BREACH                      = '\x7e70d962'
SEL_BATCH_BREACH                = '\x24924c92'
SEL_ADD_RELAYER                 = '\xdd39f00d'
SEL_REMOVE_RELAYER              = '\x60f0a5ac'
SEL_SET_FEE_RECIPIENT           = '\xe74b981b'
SEL_PAUSE                       = '\x8456cb59'
SEL_UNPAUSE                     = '\x3f4ba83a'
SEL_UPDATE_PAUSER               = '\x554bab3c'
SEL_UPGRADE_TO_AND_CALL         = '\x4f1ef286'
SEL_GET_TRADE_DETAILS           = '\x695730a5'
SEL_LAST_TRADE_ID               = '\x52bcfd5b'
-- ===== Addresses (Arc 5042) =====
ARC_FX_ESCROW                   = '\xe2e5f173576b513d994073ccbdacbe027d43dfe6'
ARC_FX_ESCROW_IMPL              = '\x59ac322681578a8c671b3be687f72919010285c2'
ARC_FX_LIB_ADMIN                = '\xaa5a1b7c53e46fc81a76c6a00cdf159b27b3d45f'
ARC_FX_LIB_SETTLE               = '\x6fdf20cec61120c75d4da1e8e0dc0b46bae05693'
ARC_FX_LIB_MAKER                = '\xafefec32e9143d56e0cf0b008e7ab3d0529c30cc'
ARC_FX_LIB_SIG                  = '\x36aaa42a4b71132197595b4a3ba964c2f13a25f5'
ARC_FX_OWNER                    = '\x2cd71b282e7e46ba3fe88955e7af368a8970c916'
ARC_FX_PAUSER                   = '\x1f27b824a5ac02e8d23482b3614f53079346b01c'
ARC_FX_FEE_RECIPIENT            = '\x7ee042f21fba1bb5fc6185cf4c3ef8b956a4c62c'
ARC_FX_RELAYER                  = '\x3f66a5ae970788246c43017f034efba102265acc'
ARC_USDC                        = '\x3600000000000000000000000000000000000000'
ARC_EURC                        = '\xbef5f6d51cb62b58e6a8f77868681825c6fe21c1'
```

## 8. Verification & sources

How constants were verified (2026-10-30):

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)`. Names and argument types come from the verified Arc-testnet FxEscrow ABI (implementation `0x721eAFa9C1e38DD7fFf81d30ea1a5500b37Cf658`, solc 0.8.26) and, for the functions and events new on mainnet, from the public signature database at 4byte.sourcify.dev. Each listed topic was found as a PUSH32 constant in the mainnet implementation or in one of its four linked libraries (found as PUSH20 constants in the implementation). Each listed selector was found as a PUSH4 in the implementation. The indexed layout of the five workhorse events comes from 388 live logs (60 windows of 2,000 blocks, blocks 28,542,962–28,662,961). The call-to-event mapping comes from 60 transaction inputs.
- **Address and roles:** from Arc's contract-address page and Circle's StableFX contract-interfaces page; `eth_getCode` on all nine chains; EIP-1967 slots and `owner()`, `pauser()`, `feeRecipient()`, `permit2()`, `lastTradeId()`, `relayers()` and `MAX_MATURITY_DURATION()` read with `eth_call`. Role holders returned no code (EOAs).
- **Not confirmed:** the indexed layout of `TradeAuthorized`, the delegate events and the refund events (no live log in the sample); the name of topic `0x1d6bf6e0…3000`; the full tuple types of `authorizeTrade` and the delegate functions (database text, selector match only).

Authoritative sources:
- [Arc contract addresses](https://docs.arc.io/arc/references/contract-addresses) (Payments and settlement → FxEscrow)
- [StableFX contract interfaces](https://developers.circle.com/stablefx/references/contract-interfaces) · [StableFX technical guide](https://developers.circle.com/stablefx/concepts/technical-guide) · [Fund trade settlement advance](https://developers.circle.com/stablefx/howtos/fund-trade-settlement-advance)
- [Permit2](https://github.com/Uniswap/permit2) (`ISignatureTransfer`)
- Explorer — [Arc explorer FxEscrow](https://explorer.arc.io/address/0xe2E5F173576B513d994073CCbDaCBE027d43DFe6)
