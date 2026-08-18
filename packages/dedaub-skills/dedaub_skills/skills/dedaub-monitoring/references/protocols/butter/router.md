# Butter Network — ButterRouter (V2 / V3 / V31 / V4) + Receiver + SwapAdapter — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon)

**Status:** verified against live RPC on Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137) and the canonical `butternetwork/butter-router-contracts` repo on 2026-06-09.
**Scope:** the **user-facing router layer** that sits in front of the MOS bridge ([mos-v3.md](mos-v3.md)): `ButterRouterV2` (legacy), `ButterRouterV3`, `ButterRouterV31`, `ButterRouterV4`, the destination-side `Receiver` / `ReceiverV2`, and the DEX-call helpers `SwapAdapter` / `SwapAdapterV3` / `SwapAggregator`. Topics + selectors are **chain-agnostic**; addresses are network-specific (and **identical across chains** by deterministic deploy — key on `(chainId, address)`).

A ButterRouter is a **swap-and-bridge aggregator**, not the bridge itself. The source-side flow is: `swapAndBridge` does an optional local DEX swap (via SwapAdapter/SwapAggregator, e.g. into USDC), takes the integrator/router fee (`CollectFee`), then calls `MOS.swapOutToken` — all in one tx, emitting **`SwapAndBridge`** alongside the bridge's `MessageOut`. The destination side: the MOS bridge calls **`Receiver.onReceived`**, which does the destination DEX swap + final callback and emits **`RemoteSwapAndCall`**. A same-chain swap with no bridge emits **`SwapAndCall`**.

**Each router version is a non-upgradeable (immutable) standalone deployment** at a deterministic, version-distinct address shared across chains. There is **no proxy** — to "upgrade," Butter deploys a new version (V2→V3→V31→V4) at a new address and points the front-end at it. So a monitor must index **all live router versions in parallel**.

**Router version map (deterministic addresses, same on every EVM chain):**

| Version | Address | Solc | Status |
|---------|---------|------|--------|
| ButterRouterV2 | `0xbB21e441fb738F54e6eC244e435475096E179d66` | 0.8.x | legacy (MOS V2-era), still live |
| ButterRouterV3 | `0xEE030ec6F4307411607E55aCD08e628Ae6655B86` | 0.8.20 | **live, primary** (most volume) |
| ButterRouterV31 | `0xEE0319cF0BCa5d09333f9F6277743E8De31bD69A` | 0.8.25 | live (gas-optimized, zero-fee variant) |
| ButterRouterV4 | `0xee040187f934FB9E41621966B1bd3E98D8319b86` | 0.8.25 | live (newest; low volume so far) |
| Receiver | `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5` | 0.8.20 | destination executor |
| ReceiverV2 | `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` | 0.8.25 | destination executor (V4-era) |
| SwapAdapter | `0x002162B2aEe2dD657FB131b28CC34deE6797b66f` | 0.8.20 | DEX-call helper |
| SwapAdapterV3 | `0xaa301070448385cfAaC5913A67B16C4392944a8f` | — | DEX-call helper |
| SwapAggregator | `0x4C0Ce9aD38BC3132ad1C8AE7E00D48f9524EbC03` | — | DEX aggregation helper (V4-era) |

> **The V3, V31 and V4 routers emit byte-identical `SwapAndBridge` / `SwapAndCall` / `RemoteSwapAndCall` / `CollectFee` events** (same topic0s) — disambiguate by emitter address. The V2 router emits a **different** `SwapAndBridge` / `SwapAndCall` / `CollectFee` shape (see §1.2). The `swapAndBridge` *function selector* differs between V3/V31 and V4 (V4 added a `_deadline` param).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally on 2026-06-09; `SwapAndBridge` confirmed against live ETH router logs (§Verification).

### 1.1 ButterRouterV3 / V31 / V4 (identical signatures — disambiguate by emitter)

| topic0 | Event |
|--------|-------|
| `0xba828651bf4de06e53231285961e555fd7dfe17a3e39d64b09fbaa8ebc0166c6` | `SwapAndBridge(address indexed referrer, address indexed initiator, address indexed from, bytes32 transferId, bytes32 orderId, address originToken, address bridgeToken, uint256 originAmount, uint256 bridgeAmount, uint256 toChain, bytes to)` |
| `0x60656aafa8d4c0a705aeb148b167d7db921d08852cd2261b270d5c7a2e655f83` | `SwapAndCall(address indexed referrer, address indexed initiator, address indexed from, bytes32 transferId, address originToken, address swapToken, uint256 originAmount, uint256 swapAmount, address receiver, address target, uint256 callAmount)` (same-chain swap) |
| `0x593e4dbcb8f7312fc3bdd77e2095da131a6e1993f37752d12576d04e1f7253b4` | `RemoteSwapAndCall(bytes32 indexed orderId, address indexed receiver, address indexed target, address originToken, address swapToken, uint256 originAmount, uint256 swapAmount, uint256 callAmount, uint256 fromChain, uint256 toChain, bytes from)` (emitted by Router **and** Receiver — see §1.3) |
| `0xfe2e49614659d9447156c9e3846112ea8edda361dcd696be486f6f977ce854e5` | `CollectFee(address indexed token, address indexed receiver, address indexed integrator, uint256 routerAmount, uint256 integratorAmount, uint256 nativeAmount, uint256 integratorNative, bytes32 transferId)` |

### 1.2 ButterRouterV2 (legacy — DIFFERENT shapes, distinct topic0s)

| topic0 | Event |
|--------|-------|
| `0x140fc1ae4910fc65859bbe978cf17402f862c5bd87a15aa3a0894d5aa50b0b06` | `SwapAndBridge(bytes32 indexed orderId, address indexed from, address indexed originToken, address bridgeToken, uint256 originAmount, uint256 bridgeAmount, uint256 fromChain, uint256 toChain, bytes to)` |
| `0x54592234b1278d8a9675f22721443e0b9f8a1f4410b55bf6753330073b55e3ef` | `SwapAndCall(address indexed from, address indexed receiver, address indexed target, bytes32 transferId, address originToken, address swapToken, uint256 originAmount, uint256 swapAmount, uint256 callAmount)` |
| `0x593e4dbcb8f7312fc3bdd77e2095da131a6e1993f37752d12576d04e1f7253b4` | `RemoteSwapAndCall(...)` — **same topic0 as V3** (signature identical). |
| `0xcc4044b4bd9f077089a3cbea5f01bcacf584f45336b1b50a8fb5f5e552da5f14` | `CollectFee(address indexed token, address indexed receiver, uint256 indexed amount, bytes32 transferId, uint8 feeType)` (`feeType`: 0=FIXED, 1=PROPORTION) |

### 1.3 Receiver / ReceiverV2 (destination-side execution) — emitter = `0xFF031cc2…` / `0xa410c91A…`

| topic0 | Event |
|--------|-------|
| `0x593e4dbcb8f7312fc3bdd77e2095da131a6e1993f37752d12576d04e1f7253b4` | `RemoteSwapAndCall(...)` — **same topic0 as the routers** (identical signature). Disambiguate by emitter. |
| `0xd457b25e0e458857e38c937f68af3100c40afd88fc5522c5820440d07b44351f` | `SwapFailed(bytes32 indexed _orderId, uint256 _fromChain, address _srcToken, address _dscToken, uint256 _amount, address _receiver, uint256 _minReceived, bytes _from, bytes _callData)` — **destination swap failed; funds parked** (alert). |
| `0x96bd27c30adb4ab40a10d5bd2f782f70f15773d913046b658cf92a15a0abb399` | `SwapRescueFunds(bytes32, address, uint256, address)` — keeper rescued parked funds. |

### 1.4 SwapAdapter / SwapAggregator

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` (token movement during the adapter swap) |

(`SwapComplete` / `SweepTokenWithFee` are internal-tooling events; the load-bearing router events are §1.1–1.3.)

### 1.5 Proxy / standards (none of the routers are proxies — see §6)

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address,address,uint256)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 ButterRouterV3 / V31 — entrypoints

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6e1537da` | `swapAndBridge(bytes32 _transferId, address _initiator, address _srcToken, uint256 _amount, bytes _swapData, bytes _bridgeData, bytes _permitData, bytes _feeData)` → `bytes32 orderId` | **the main cross-chain entrypoint.** Emits `SwapAndBridge` + (via MOS) `MessageOut`. |
| `0x119b8248` | `swapAndCall(bytes32 _transferId, address _initiator, address _srcToken, uint256 _amount, bytes _swapData, bytes _callbackData, bytes _permitData, bytes _feeData)` | same-chain swap + callback. Emits `SwapAndCall`. |

### 2.2 ButterRouterV4 — entrypoints (selectors differ — `_deadline` added)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xdffbf35f` | `swapAndBridge(address _initiator, address _srcToken, uint256 _amount, uint256 _deadline, bytes _swapData, bytes _bridgeData, bytes _permitData, bytes _feeData)` → `bytes32 orderId` | V4 entrypoint (deadline-guarded). Same `SwapAndBridge` **event** topic0 as V3. |

### 2.3 ButterRouterV2 (legacy) — entrypoints

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x480a3411` | `swapAndBridge(address _srcToken, uint256 _amount, bytes _swapData, bytes _bridgeData, bytes _permitData)` | V2 entrypoint (no `_initiator`, no fee data). |
| `0x8217062d` | `swapAndCall(bytes32 _transferId, address _srcToken, uint256 _amount, bytes _swapData, bytes _callbackData, bytes _permitData, bytes _feeData)` | V2 same-chain. |

### 2.4 Receiver / ReceiverV2 — callback entrypoint

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2344e655` | `onReceived(bytes32 _orderId, address _srcToken, uint256 _amount, uint256 _fromChain, bytes _from, bytes _swapAndCall)` | **called only by the MOS bridge** (`msg.sender == bridgeAddress`). Does destination swap + callback; emits `RemoteSwapAndCall` or `SwapFailed`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. **Every address below is identical on Base, BNB, Arbitrum, Optimism and Polygon** (deterministic deploy) — see §4 for the Avalanche divergence.

| Role | Address | Bytecode | One-liner |
|------|---------|----------|-----------|
| ButterRouterV2 | `0xbB21e441fb738F54e6eC244e435475096E179d66` | 15193 B | Legacy aggregator (MOS V2-era). |
| **ButterRouterV3** | `0xEE030ec6F4307411607E55aCD08e628Ae6655B86` | 20281 B | **Primary** aggregator (1789 `SwapAndBridge` in 49k blocks). |
| ButterRouterV31 | `0xEE0319cF0BCa5d09333f9F6277743E8De31bD69A` | 15317 B | Gas-optimized variant (62 logs/49k). |
| ButterRouterV4 | `0xee040187f934FB9E41621966B1bd3E98D8319b86` | 15768 B | Newest (0 logs in window — deployed, low usage). |
| Receiver | `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5` | 14771 B | Destination executor. |
| ReceiverV2 | `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` | 13686 B | Destination executor (V4-era). |
| SwapAdapter | `0x002162B2aEe2dD657FB131b28CC34deE6797b66f` | 10533 B | DEX-call helper. |
| SwapAdapterV3 | `0xaa301070448385cfAaC5913A67B16C4392944a8f` | 11170 B | DEX-call helper. |
| SwapAggregator | `0x4C0Ce9aD38BC3132ad1C8AE7E00D48f9524EbC03` | 11749 B | DEX aggregation helper. |

## 4. Addresses — Base / BNB / Arbitrum / Optimism / Polygon (identical literals) + Avalanche (partial)

Verified via `eth_getCode` on each chain's publicnode RPC. **Base (8453), BNB (56), Arbitrum (42161), Optimism (10), Polygon (137) carry the full set at the exact Ethereum literals** — with two router-version gaps:

| Router/contract | Base | BNB | Arbitrum | Optimism | Polygon | **Avalanche** |
|---|---|---|---|---|---|---|
| ButterRouterV2 `0xbB21e441…` | ✓ | ✓ | ✓ | ✓ | ✓ | **✗ (0x)** |
| ButterRouterV3 `0xEE030ec6…` | ✓ | ✓ | ✓ | ✓ | ✓ | **✗ (0x)** |
| ButterRouterV31 `0xEE0319cF…` | ✓ | ✓ | ✓ | ✓ | ✓ | **✓** |
| ButterRouterV4 `0xee040187…` | ✓ | ✓ | ✓ | **✗ (0x)** | ✓ | **✗ (0x)** |
| Receiver `0xFF031cc2…` | ✓ | ✓ | ✓ | ✓ | ✓ | **✓** |
| ReceiverV2 `0xa410c91A…` | ✓ | ✓ | ✓ | **✗ (0x)** | ✓ | **✗ (0x)** |
| SwapAdapter `0x002162B2…` | ✓ | ✓ | ✓ | ✓ | ✓ | **✗ (0x)** |
| SwapAdapterV3 `0xaa301070…` | ✓ | ✓ | ✓ | ✓ | ✓ | **✓** |
| SwapAggregator `0x4C0Ce9aD…` | ✓ | ✓ | ✓ | **✗ (0x)** | ✓ | **✗ (0x)** |

**Optimism** lacks the V4-era set (ButterRouterV4, ReceiverV2, SwapAggregator return `0x`) — it runs V2/V3/V31 + Receiver only. **Avalanche** runs a minimal set: **ButterRouterV31 + Receiver + SwapAdapterV3 only** (V2/V3/V4 routers, ReceiverV2, SwapAdapter, SwapAggregator all return `0x`). MOS V3 is fully present on both (see mos-v3.md).

## 5. Cross-chain summary

| Chain | ID | V2 | V3 | V31 | V4 | Receiver | ReceiverV2 |
|---|---|---|---|---|---|---|---|
| Ethereum | 1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Base | 8453 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BNB | 56 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Arbitrum | 42161 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Optimism | 10 | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ |
| Polygon | 137 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Avalanche | 43114 | ✗ | ✗ | ✓ | ✗ | ✓ | ✗ |

**Vanity-address tells:** the live routers cluster on `0xEE03…` (V3 `0xEE030ec6…`, V31 `0xEE0319cF…`), V4 on `0xee0401…`, and the Receivers on `0xFF03…` / `0xa410…`. Same literal everywhere ⇒ key on `(chainId, address)`.

**Counterparty / extra-target chains:** the same router addresses also exist on zkSync Era (324, *different* literals — `0x73E0d6E6…`), Linea, Scroll, Mantle, Blast (81457), Merlin, Bevm, AINN, Conflux, Klaytn, X Layer, Unichain, zkLink, Monad, plus **Tron** (base58 addresses, e.g. ButterRouterV3 `TPYm4fQJxmoBuhAbNWCBx2ehzhVJ1fxFNP`) and a **Solana** receiver (`SolanaReceiver.sol`). Recorded as findings; only the seven targets are detailed above.

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **ButterRouterV2/V3/V31/V4** | **NOT proxies — immutable** | Full-size bytecode (13–20 KB); EIP-1967 impl slot `0x360894…` reads `0x0` (confirmed live on ETH ButterRouterV3). No `Upgraded` event. "Upgrade" = new version at a new address. | `Ownable` owner sets fee/bridge/adapter config; **code is fixed**. |
| **Receiver / ReceiverV2** | **NOT proxies — immutable** | Full bytecode (13–14 KB); impl slot `0x0`. | `Ownable`; `bridgeAddress` settable. |
| **SwapAdapter / SwapAdapterV3 / SwapAggregator** | **NOT proxies — immutable** | Full bytecode (10–12 KB); impl slot `0x0`. | `Ownable`. |

There is **no `Upgraded(address)` to watch in the router layer** — instead watch for *new router-version deployments* and the front-end repointing. The upgradeable parts of Butter are all in the bridge layer ([mos-v3.md](mos-v3.md) §Proxies).

## 7. Detection invariants & gotchas

1. **`SwapAndBridge` is the source-side router event; `MessageOut` (mos-v3.md) is the bridge twin** — they fire in the **same tx**. The shared `orderId` joins router→bridge→destination. (Live: ButterRouterV3 `SwapAndBridge` and MOS `MessageOut` shared tx `0x6477b1e1…`.)
2. **V3, V31 and V4 emit the SAME `SwapAndBridge`/`SwapAndCall`/`RemoteSwapAndCall`/`CollectFee` topic0s.** You cannot tell the router version from topic0 alone — **disambiguate by emitter address** (`0xEE030ec6…` vs `0xEE0319cF…` vs `0xee040187…`).
3. **`RemoteSwapAndCall` topic0 `0x593e4dbc…` is shared by the routers AND the Receivers AND ButterRouterV2** (identical signature across all). Always pair it with the emitter to know whether it's a source-side or destination-side log.
4. **ButterRouterV2 events are a DIFFERENT shape** (its `SwapAndBridge` indexes `orderId/from/originToken`, no `referrer/initiator`; its `CollectFee` is the 5-field FIXED/PROPORTION variant). Don't reuse V3 topic0s for the V2 router address.
5. **The real user is `initiator`/`from`/`referrer`, never `msg.sender`.** The router forwards to MOS; the Receiver is invoked by the bridge. Attribute by event fields.
6. **`swapAndBridge` function selector differs V3/V31 (`0x6e1537da`) vs V4 (`0xdffbf35f`)** because V4 added a `_deadline` parameter — useful to tell which router version a raw tx hit.
7. **`SwapFailed` (`0xd457b25e…`) on a Receiver = a stuck/parked destination delivery** (swap on the destination chain failed; funds held in the Receiver's failed-store pending a keeper `SwapRescueFunds`). High-value alert.
8. **`onReceived` is bridge-gated** (`msg.sender == bridgeAddress`). A direct external call reverts — so every `RemoteSwapAndCall` from a Receiver traces back to a MOS `MessageIn` in the same tx.
9. **Avalanche has only ButterRouterV31 + Receiver + SwapAdapterV3** of the router layer; Optimism lacks the V4-era set. If you index only V3/V4 you will miss Avalanche router traffic entirely (it's all on V31).
10. **Routers are immutable** — no `Upgraded` event to track in this layer; instead a new version address appears (V2→V3→V31→V4). Keep the full version list in your address set.
11. **Same literal on every EVM chain** (except zkSync, which uses different literals) — key everything on `(chainId, address)`.

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics — ButterRouter V3/V31/V4 (chain-agnostic; key on emitter) =====
TOPIC_SWAP_AND_BRIDGE_V3   = '\xba828651bf4de06e53231285961e555fd7dfe17a3e39d64b09fbaa8ebc0166c6'
TOPIC_SWAP_AND_CALL_V3     = '\x60656aafa8d4c0a705aeb148b167d7db921d08852cd2261b270d5c7a2e655f83'
TOPIC_REMOTE_SWAP_AND_CALL = '\x593e4dbcb8f7312fc3bdd77e2095da131a6e1993f37752d12576d04e1f7253b4'  -- router V2/V3 + Receiver share this
TOPIC_COLLECT_FEE_V3       = '\xfe2e49614659d9447156c9e3846112ea8edda361dcd696be486f6f977ce854e5'
-- ===== Topics — ButterRouter V2 (legacy, distinct shapes) =====
TOPIC_SWAP_AND_BRIDGE_V2   = '\x140fc1ae4910fc65859bbe978cf17402f862c5bd87a15aa3a0894d5aa50b0b06'
TOPIC_SWAP_AND_CALL_V2     = '\x54592234b1278d8a9675f22721443e0b9f8a1f4410b55bf6753330073b55e3ef'
TOPIC_COLLECT_FEE_V2       = '\xcc4044b4bd9f077089a3cbea5f01bcacf584f45336b1b50a8fb5f5e552da5f14'
-- ===== Topics — Receiver =====
TOPIC_SWAP_FAILED          = '\xd457b25e0e458857e38c937f68af3100c40afd88fc5522c5820440d07b44351f'
TOPIC_SWAP_RESCUE_FUNDS    = '\x96bd27c30adb4ab40a10d5bd2f782f70f15773d913046b658cf92a15a0abb399'

-- ===== Selectors =====
SEL_SWAP_AND_BRIDGE_V3     = '\x6e1537da'
SEL_SWAP_AND_CALL_V3       = '\x119b8248'
SEL_SWAP_AND_BRIDGE_V4     = '\xdffbf35f'
SEL_SWAP_AND_BRIDGE_V2     = '\x480a3411'
SEL_SWAP_AND_CALL_V2       = '\x8217062d'
SEL_ON_RECEIVED            = '\x2344e655'

-- ===== Addresses (IDENTICAL on all EVM targets except zkSync; key on (chainId,addr)) =====
BUTTER_ROUTER_V2           = '\xbb21e441fb738f54e6ec244e435475096e179d66'
BUTTER_ROUTER_V3           = '\xee030ec6f4307411607e55acd08e628ae6655b86'
BUTTER_ROUTER_V31          = '\xee0319cf0bca5d09333f9f6277743e8de31bd69a'
BUTTER_ROUTER_V4           = '\xee040187f934fb9e41621966b1bd3e98d8319b86'
BUTTER_RECEIVER            = '\xff031cc2563988bc4afa29e2cd7bcc2d389900a5'
BUTTER_RECEIVER_V2         = '\xa410c91ae49633d78a55bbb3479fdb8fcae0d883'
BUTTER_SWAP_ADAPTER        = '\x002162b2aee2dd657fb131b28cc34dee6797b66f'
BUTTER_SWAP_ADAPTER_V3     = '\xaa301070448385cfaac5913a67b16c4392944a8f'
BUTTER_SWAP_AGGREGATOR     = '\x4c0ce9ad38bc3132ad1c8ae7e00d48f9524ebc03'
-- Avalanche present: V31, Receiver, SwapAdapterV3 only.  Optimism missing: V4, ReceiverV2, SwapAggregator.
```

## 9. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from `butternetwork/butter-router-contracts/contracts/` (`ButterRouterV3.sol`, `ButterRouterV31.sol`, `ButterRouterV4.sol`, `Receiver.sol`, `ReceiverV2.sol`, `interface/IButterRouterV3.sol`, `interface/IButterRouterV4.sol`, `legacy/ButterRouterV2.sol`, `legacy/interface/IButterRouterV2.sol`). A `diff` of the V3 vs V4 interface event blocks confirmed the `SwapAndBridge`/`SwapAndCall`/`RemoteSwapAndCall` bodies are byte-identical (⇒ shared topic0); the V4 *function* differs (`_deadline`).
- **Live cross-check:** `SwapAndBridge` topic0 `0xba828651…` confirmed via `eth_getLogs` on ButterRouterV3 `0xEE030ec6…` (1789 logs/49k blocks, first tx `0x6477b1e1…` — same tx as the MOS `MessageOut`) and on ButterRouterV31 `0xEE0319cF…` (62 logs); ButterRouterV4 `0xee040187…` returned 0 in-window (deployed, low usage).
- **Addresses:** parsed from `deployments/deploy.json` (`prod` env) and existence-checked via `eth_getCode` on all seven target RPCs. The per-chain presence matrix (§4/§5) reflects actual non-empty/`0x` results — Avalanche carries only V31+Receiver+SwapAdapterV3; Optimism lacks V4/ReceiverV2/SwapAggregator.
- **Proxy classification:** EIP-1967 impl slot read live via `eth_getStorageAt` on ButterRouterV3 (ETH) returned `0x0` ⇒ immutable, not a proxy (consistent with full-size bytecode).

**Authoritative sources:**
- Router repo: <https://github.com/butternetwork/butter-router-contracts> (`deployments/deploy.json`, `contracts/`)
- Docs: <https://docs.butternetwork.io> (Butter Bridge & Routing Integration)
- Explorers: Etherscan / Basescan / BscScan / Snowscan / Arbiscan / Optimistic Etherscan / Polygonscan.
