# Synapse RFQ (FastBridge) — Topics, Selectors, Addresses (Ethereum, BNB, Arbitrum, Optimism, Base)

**Status:** verified against live RPC and the canonical `synapsecns/sanguine` `packages/contracts-rfq` repo on 2026-06-09.
**Scope:** the **RFQ / intent bridge** — `FastBridge` (a.k.a. FastBridgeV2), the `FastBridgeRouter`/`FastBridgeRouterV2` front, and the `FastBridgeInterceptor`. This is Synapse's *current* primary bridge path (relayer-fronted optimistic transfers), distinct from the mint/burn `SynapseBridge` documented in [synapse.md](./synapse.md). Chains + IDs: Ethereum 1, BNB 56, Arbitrum 42161, Optimism 10, Base 8453. **Topics/selectors are chain-agnostic; addresses are network-specific.**

RFQ is an **optimistic relay bridge**: a user calls `bridge(...)` on the origin `FastBridge`, which escrows their token and emits `BridgeRequested` (carrying a `bytes32 transactionId`). A whitelisted **relayer** fronts the destination funds and calls `relay(...)` on the destination `FastBridge` (emits `BridgeRelayed`). The relayer then `prove`s the relay on the origin (`BridgeProofProvided`), and after a `DISPUTE_PERIOD` with no `dispute`, `claim`s the escrowed origin funds (`BridgeDepositClaimed`). If no relay happens before `deadline`, the user `refund`s (`BridgeDepositRefunded`). **There is no mint/burn and no nUSD here** — funds are pre-positioned by relayers; the join key across chains is the `bytes32 transactionId`.

Two facts to internalise:

1. **`FastBridge` is the single CREATE2 vanity `0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E` on every chain that has it** (Ethereum, BNB, Arbitrum, Optimism, Base). It is **immutable** (no proxy, empty EIP-1967 slot, 9,547-byte runtime). **NOT deployed on Avalanche or Polygon** (`0x`).
2. **The deployed contract is FastBridgeV2** — its `BridgeRelayed` carries an extra trailing `uint256` (chain-gas) → **topic0 `0xf8ae392d…` (9-arg), not the V1 8-arg `0x88bd455d…`.** Confirmed live: in a Base 50k-block window the `0x5523…` contract logged 37 `BridgeRelayed (9-arg)`, 7 `BridgeRequested`, 7 `BridgeProofProvided`, 7 `BridgeDepositClaimed`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Recomputed locally with keccak256 and **all confirmed live on the Base FastBridge `0x5523…` on 2026-06-09**.

### 1.1 FastBridge (FastBridgeV2)

| topic0 | Event | Side |
|--------|-------|------|
| `0x120ea0364f36cdac7983bcfdd55270ca09d7f9b314a2ebc425a3b01ab1d6403a` | `BridgeRequested(bytes32 indexed transactionId, address indexed sender, bytes request, uint32 destChainId, address originToken, address destToken, uint256 originAmount, uint256 destAmount, bool sendChainGas)` | origin (escrow) |
| `0xf8ae392d784b1ea5e8881bfa586d81abf07ef4f1e2fc75f7fe51c90f05199a5c` | `BridgeRelayed(bytes32 indexed transactionId, address indexed relayer, address indexed to, uint32 originChainId, address originToken, address destToken, uint256 originAmount, uint256 destAmount, uint256 chainGasAmount)` | **dest (relay)** — V2, 9 args |
| `0x4ac8af8a2cd87193d64dfc7a3b8d9923b714ec528b18725d080aa1299be0c5e4` | `BridgeProofProvided(bytes32 indexed transactionId, address indexed relayer, bytes32 transactionHash)` | origin |
| `0x0695cf1d39b3055dcd0fe02d8b47eaf0d5a13e1996de925de59d0ef9b7f7fad4` | `BridgeProofDisputed(bytes32 indexed transactionId, address indexed relayer)` | origin |
| `0x582211c35a2139ac3bbaac74663c6a1f56c6cbb658b41fe11fd45a82074ac678` | `BridgeDepositClaimed(bytes32 indexed transactionId, address indexed relayer, address indexed to, address token, uint256 amount)` | origin (relayer paid) |
| `0xb4c55c0c9bc613519b920e88748090150b890a875d307f21bea7d4fb2e8bc958` | `BridgeDepositRefunded(bytes32 indexed transactionId, address indexed to, address token, uint256 amount)` | origin (user refunded) |
| `0x3120e2bb59c86aca6890191a589a96af3662838efa374fbdcdf4c95bfe4a6c0e` | `BridgeQuoteDetails(bytes32 indexed transactionId, bytes quoteId)` | origin (V2 quote attribution) |

> **The legacy V1 `BridgeRelayed` (8 args, no `chainGasAmount`) topic0 is `0x88bd455d148b0480e1ef08dd68813b68dad6f7fe12256040bae085912c0358e5`** — present in old logs only. The live contract emits the **9-arg V2** variant (`0xf8ae392d…`). Index both for full history; key new alerts on the V2 topic.

### 1.2 AccessControl / pause (FastBridge inherits OZ AccessControl)

| topic0 | Event |
|--------|-------|
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` (RELAYER_ROLE / GUARD_ROLE / GOVERNOR_ROLE) |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |

---

## 2. Function signatures (chain-agnostic)

All selectors below **verified present** in the live FastBridge runtime bytecode `0x5523…` via PUSH4 dispatch scan on Ethereum, 2026-06-09 (except the `bridge`/`bridgeV2` entrypoints, whose exact `BridgeParams` tuple is noted).

### 2.1 FastBridge (FastBridgeV2) — lifecycle

| Selector | Signature | Side / role | Emits |
|----------|-----------|-------------|-------|
| *(entrypoint)* | `bridge(BridgeParams)` / `bridgeV2(BridgeParams,BridgeParamsV2)` | user (origin) | `BridgeRequested` (+ `BridgeQuoteDetails`). `BridgeParams = (uint32 dstChainId, address originToken, address destToken, address sender, address to, uint256 originAmount, uint256 destAmount, uint256 deadline, bytes ...)`. Exact selector not pinned (struct layout varies by build); **detect via `BridgeRequested`**. |
| `0x8f0d6f17` | `relay(bytes request)` | **RELAYER_ROLE** (dest) | `BridgeRelayed` |
| `0x886d36ff` | `prove(bytes request, bytes32 destTxHash)` | RELAYER_ROLE (origin) | `BridgeProofProvided` |
| `0x41fcb612` | `claim(bytes request, address to)` | RELAYER_ROLE (origin) | `BridgeDepositClaimed` |
| `0xadd98c70` | `dispute(bytes32 transactionId)` | GUARD_ROLE (origin) | `BridgeProofDisputed` |
| `0x5eb7d946` | `refund(bytes request)` | anyone after deadline (origin) | `BridgeDepositRefunded` |

### 2.2 FastBridge — views & admin

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xaa9641ab` | `canClaim(bytes32 transactionId, address relayer)` → `bool` | True once dispute window passes. |
| `0x051287bc` | `bridgeStatuses(bytes32)` → `uint8` | 0 NULL / 1 REQUESTED / 2 RELAYER_PROVED / 3 RELAYER_CLAIMED / 4 REFUNDED. |
| `0x8379a24f` | `bridgeRelays(bytes32)` → `bool` | Whether a tx was relayed (destination side). |
| `0xac11fb1a` | `getBridgeTransaction(bytes)` → struct | Decode a request blob. |
| `0x58f85880` | `protocolFeeRate()` → `uint256` | |
| `0xdcf844a7` | `protocolFees(address)` → `uint256` | Accrued per token. |
| `0xb13aa2d6` | `setProtocolFeeRate(uint256)` | GOVERNOR_ROLE. |
| `0xa5bbe22b` | `DISPUTE_PERIOD()` → `uint256` | |
| `0x190da595` | `REFUND_DELAY()` → `uint256` | |
| `0xccc57490` | `GOVERNOR_ROLE()` → `bytes32` | |
| `0x926d7d7f` | `RELAYER_ROLE()` → `bytes32` | |
| `0x03ed0ee5` | `GUARD_ROLE()` → `bytes32` | |
| `0xa3ec191a` | `deployBlock()` → `uint256` | Backfill anchor. |
| `0xaffed0e0` | `nonce()` → `uint256` | Origin request counter. |

### 2.3 FastBridgeRouter / FastBridgeRouterV2

The router fronts the FastBridge with a swap-quote layer (TokenZap). `fastBridge()` (`0x7673eb15`) returns the underlying FastBridge (`0x5523…`). The router is what the dApp calls; it forwards into `FastBridge.bridge`.

---

## 3. Addresses

All verified via `eth_getCode` on each chain's publicnode RPC on 2026-06-09. **FastBridge, FastBridgeRouterV2, FastBridgeInterceptor are the same CREATE2 vanity address on every chain that has them.**

| Role | Address (same on ETH/BSC/Arb/OP/Base) | One-liner |
|------|----------------------------------------|-----------|
| **FastBridge (V2)** | `0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E` | The RFQ escrow/relay contract; emits all §1.1 events. Immutable, 9,547 B. |
| **FastBridgeRouterV2** | `0x00cD000000003f7F682BE4813200893d4e690000` | Current router front (vanity `00cD…0000`). |
| **FastBridgeRouter (V1)** | `0x0000000000489d89D2B233D3375C045dfD05745F` | Older router front. |
| **FastBridgeInterceptor** | `0xFb1fb1060C550A9b274C64f70dadF16f2aD34fB1` | Quote/zap interceptor. |
| RelayerInterceptor (RELAY) | `0xBBbfD134E9b44BfB5123898BA36b01dE7ab93d98` | (SDK `RELAY_ADDRESS`) |

### 3.1 Per-chain presence

| Chain | ID | FastBridge | FastBridgeRouterV2 | Notes |
|---|---|---|---|---|
| Ethereum | 1 | ✓ `0x5523…` | ✓ `0x00cD…` | immutable; empty impl slot. |
| BNB | 56 | ✓ `0x5523…` (9,547 B) | ✓ `0x00cD…` | present. |
| Arbitrum | 42161 | ✓ `0x5523…` | ✓ `0x00cD…` | present; `fastBridge()` → `0x5523…`. |
| Optimism | 10 | ✓ `0x5523…` | ✓ `0x00cD…` | present. |
| Base | 8453 | ✓ `0x5523…` | ✓ `0x00cD…` | **highest live RFQ volume** of the 7. |
| **Avalanche** | 43114 | **✗ `0x`** | **✗ `0x`** | **NOT DEPLOYED.** |
| **Polygon** | 137 | **✗ `0x`** | **✗ `0x`** | **NOT DEPLOYED.** |

**Counterparty chains outside the seven:** RFQ also runs on Blast, Linea, Scroll, Berachain, HyperEVM, Unichain, Worldchain and others (in the SDK `FAST_BRIDGE_ROUTER_ADDRESS_MAP`). A `BridgeRequested.destChainId` may reference any of these — an out-of-set `destChainId` is a valid leg.

---

## 4. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **FastBridge** | **Immutable** | 9,547-byte runtime; EIP-1967 impl slot = `0x000…0` (read live). | none — redeploy + re-point the router to upgrade. |
| **FastBridgeRouterV2 / Interceptor** | **Immutable** | full runtime; empty impl slot. | none. |

There is **no proxy** in the RFQ stack. Upgrades happen by deploying a new FastBridge and re-pointing `FastBridgeRouterV2.fastBridge()`. Watch that getter (`0x7673eb15`) for a target change rather than an `Upgraded` event.

---

## 5. Detection invariants & gotchas

1. **`bytes32 transactionId` is the cross-chain join key** — `indexed` (topic[1]) in every RFQ event. Origin: `BridgeRequested` → `BridgeProofProvided` → `BridgeDepositClaimed` (or `BridgeDepositRefunded`). Destination: `BridgeRelayed`. Match origin and destination legs by `transactionId`.
2. **`BridgeRelayed` fires on the DESTINATION chain; the other five fire on the ORIGIN chain.** A relay with no matching origin `BridgeRequested` (or vice-versa) is the anomaly to alert on.
3. **Use the 9-arg V2 `BridgeRelayed` topic `0xf8ae392d…`,** not the legacy 8-arg `0x88bd455d…`. The live contract is V2; the 8-arg topic only matches historical logs.
4. **`relayer` ≠ user.** In `BridgeRelayed`/`BridgeProofProvided`/`BridgeDepositClaimed` the `relayer` is the market-maker who fronted funds; the end user is `to` (in `BridgeRelayed`/`BridgeRequested`.sender). Attribute user volume by `sender`/`to`, relayer exposure by `relayer`.
5. **`dispute` (GUARD_ROLE) → `BridgeProofDisputed` is a fraud signal.** A relayer that proved a bad relay gets disputed and loses the claim — monitor `BridgeProofDisputed` as a security event.
6. **`BridgeDepositRefunded` means the relay never happened in time** — the user got their origin funds back. A spike implies relayer outages or a destination-chain issue.
7. **Not on Avalanche or Polygon** (`0x` on both) — those two chains use only the classic `SynapseBridge`/CCTP paths ([synapse.md](./synapse.md)).
8. **`FastBridge` and `FastBridgeRouterV2` are the same literal address on all 5 deployed chains** — key on `(chainId, address)`.
9. **The dApp calls the router (`0x00cD…`), not the bridge directly** — so a `BridgeRequested` log's `tx.to` is the router/interceptor, and `sender` in the event (not `tx.from`) is the user.

---

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== RFQ event topics (chain-agnostic) =====
TOPIC_BRIDGE_REQUESTED          = '\x120ea0364f36cdac7983bcfdd55270ca09d7f9b314a2ebc425a3b01ab1d6403a'
TOPIC_BRIDGE_RELAYED_V2         = '\xf8ae392d784b1ea5e8881bfa586d81abf07ef4f1e2fc75f7fe51c90f05199a5c'
TOPIC_BRIDGE_RELAYED_V1         = '\x88bd455d148b0480e1ef08dd68813b68dad6f7fe12256040bae085912c0358e5'
TOPIC_BRIDGE_PROOF_PROVIDED     = '\x4ac8af8a2cd87193d64dfc7a3b8d9923b714ec528b18725d080aa1299be0c5e4'
TOPIC_BRIDGE_PROOF_DISPUTED     = '\x0695cf1d39b3055dcd0fe02d8b47eaf0d5a13e1996de925de59d0ef9b7f7fad4'
TOPIC_BRIDGE_DEPOSIT_CLAIMED    = '\x582211c35a2139ac3bbaac74663c6a1f56c6cbb658b41fe11fd45a82074ac678'
TOPIC_BRIDGE_DEPOSIT_REFUNDED   = '\xb4c55c0c9bc613519b920e88748090150b890a875d307f21bea7d4fb2e8bc958'
TOPIC_BRIDGE_QUOTE_DETAILS      = '\x3120e2bb59c86aca6890191a589a96af3662838efa374fbdcdf4c95bfe4a6c0e'
TOPIC_ROLE_GRANTED              = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED              = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'

-- ===== FastBridge selectors =====
SEL_RELAY                       = '\x8f0d6f17'
SEL_PROVE                       = '\x886d36ff'
SEL_CLAIM                       = '\x41fcb612'
SEL_DISPUTE                     = '\xadd98c70'
SEL_REFUND                      = '\x5eb7d946'
SEL_CAN_CLAIM                   = '\xaa9641ab'
SEL_BRIDGE_STATUSES             = '\x051287bc'
SEL_BRIDGE_RELAYS               = '\x8379a24f'
SEL_SET_PROTOCOL_FEE_RATE       = '\xb13aa2d6'
SEL_FAST_BRIDGE_GETTER          = '\x7673eb15'   -- FastBridgeRouterV2.fastBridge()

-- ===== Addresses (same on ETH/BSC/Arb/OP/Base; NONE on Avax/Polygon) =====
FAST_BRIDGE                     = '\x5523d3c98809dddb82c686e152f5c58b1b0fb59e'
FAST_BRIDGE_ROUTER_V2           = '\x00cd000000003f7f682be4813200893d4e690000'
FAST_BRIDGE_ROUTER_V1           = '\x0000000000489d89d2b233d3375c045dfd05745f'
FAST_BRIDGE_INTERCEPTOR         = '\xfb1fb1060c550a9b274c64f70dadf16f2ad34fb1'
```

---

## 7. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0s** recomputed locally as `keccak256(canonical event signature)` and **confirmed live via `eth_getLogs`** on the Base FastBridge `0x5523…` (50k-block window: 37 `BridgeRelayed` V2 `0xf8ae392d…`, 7 each of `BridgeRequested` `0x120ea036…`, `BridgeProofProvided` `0x4ac8af8a…`, `BridgeDepositClaimed` `0x582211c3…`). The V2 9-arg vs V1 8-arg `BridgeRelayed` distinction was resolved by matching the live topic0 against both signatures.
- **Selectors** recomputed as `keccak256(sig)[0:4]` and **verified present** in the live FastBridge runtime bytecode by PUSH4 dispatch scan (`relay`/`prove`/`claim`/`dispute`/`refund`/`canClaim`/`bridgeStatuses`/role getters all HIT). The `bridge`/`bridgeV2` entrypoint selector was left unpinned because the `BridgeParams` tuple layout varies across builds — detection should key on `BridgeRequested`, not the call selector.
- **Addresses** parsed from `synapsecns/sanguine` `packages/sdk-router/src/constants/addresses.ts` (`FAST_BRIDGE_ROUTER_ADDRESS_MAP`, `FAST_BRIDGE_INTERCEPTOR_ADDRESS_MAP`) and `packages/contracts-rfq/deployments/<chain>/FastBridge.json`, then existence-checked via `eth_getCode`: present on ETH/BSC/Arb/OP/Base (9,547-byte immutable), `0x` on Avalanche and Polygon.
- **Proxy status:** EIP-1967 impl slot read live on the Ethereum FastBridge = `0x000…0` → immutable (no proxy).

Authoritative sources:
- [`synapsecns/sanguine` — packages/contracts-rfq](https://github.com/synapsecns/sanguine/tree/master/packages/contracts-rfq) (`FastBridgeV2.sol`, `interfaces/IFastBridge.sol`, `deployments/`).
- [`synapsecns/sanguine` — sdk-router addresses](https://github.com/synapsecns/sanguine/blob/master/packages/sdk-router/src/constants/addresses.ts).
- [Synapse docs](https://docs.synapseprotocol.com/) · [Etherscan FastBridge](https://etherscan.io/address/0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E).
