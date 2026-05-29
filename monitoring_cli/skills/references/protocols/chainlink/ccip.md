# Chainlink CCIP — Topics, Selectors, Chain Selectors, Addresses

**Status:** verified 2026-05-29. Chain selectors verified against `smartcontractkit/chain-selectors`; Router addresses verified via `eth_getCode` (non-empty) on every chain; Ethereum support contracts + `ccipSend`/`isChainSupported` selectors verified against live bytecode; Ethereum Router `typeAndVersion() = "Router 1.2.0"`.
**Scope:** Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137). LINK token (a valid fee token): [link-token.md](link-token.md).

CCIP sends arbitrary messages + token transfers across chains. A user calls **`Router.ccipSend()`** on the source chain; the lane's **OnRamp** emits the message; the DON commits it on the destination's **OffRamp**, which executes it via the destination **Router**. **CCIP does NOT use EVM chain IDs** — every lane is addressed by a uint64 **chain selector** (§1).

**Architecture by version:**
- **v1.0 / v1.2:** per-lane `EVM2EVMOnRamp` + `EVM2EVMOffRamp` + `CommitStore`; fees priced by a shared **`PriceRegistry`**. Router `"Router 1.2.0"`.
- **v1.5:** adds **`TokenAdminRegistry`** + `RegistryModuleOwnerCustom` (self-serve token-pool registration / CCT) and replaces `PriceRegistry` with **`FeeQuoter`**; lanes still OnRamp/OffRamp/CommitStore.
- **v1.6:** new architecture — unified **`OnRamp`**/**`OffRamp`** (CommitStore folded into OffRamp), a chain-wide **`NonceManager`**, OCR3, and the message-id-centric `CCIPMessageSent` event.

The Router address is **stable across versions** on a given chain; lane contracts (ramps) are swapped underneath.

---

## 1. Chain selectors (CRITICAL — not EVM chain IDs)

Verified against `smartcontractkit/chain-selectors` `selectors.yml`.

| Chain | EVM chainId | CCIP chain selector (uint64) |
|-------|-------------|------------------------------|
| Ethereum | 1 | `5009297550715157269` |
| Base | 8453 | `15971525489660198786` |
| BNB Smart Chain | 56 | `11344663589394136015` |
| Avalanche C-Chain | 43114 | `6433500567565415381` |
| Arbitrum One | 42161 | `4949039107694359620` |
| Optimism | 10 | `3734403246176062136` |
| Polygon PoS | 137 | `4051577828743386545` |

---

## 2. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 2.1 Router

| topic0 | Event |
|--------|-------|
| `0x9b877de93ea9895756e337442c657f95a34fc68e7eb988bdfa693d5be83016b6` | `MessageExecuted(bytes32 messageId, uint64 sourceChainSelector, address offRamp, bytes32 calldataHash)` |
| `0xa4bdf64ebdf3316320601a081916a75aa144bcef6c4beeb0e9fb1982cacc6b94` | `OffRampAdded(uint64 indexed sourceChainSelector, address offRamp)` |
| `0xa823809efda3ba66c873364eec120fa0923d9fabda73bc97dd5663341e2d9bcb` | `OffRampRemoved(uint64 indexed sourceChainSelector, address offRamp)` |
| `0x1f7d0ec248b80e5c0dde0ee531c4fc8fdb6ce9a2b3d90f560c74acd6a7202f23` | `OnRampSet(uint64 indexed destChainSelector, address onRamp)` |

### 2.2 OnRamp / OffRamp / CommitStore

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xd4f851956a5d67c3997d1c9205045fef79bae2947fdee7e9e2641abc7391ef65` | `ExecutionStateChanged(uint64 indexed sequenceNumber, bytes32 indexed messageId, uint8 state, bytes returnData)` | **OffRamp (≤v1.5)** — `state`: 0=Untouched,1=InProgress,2=Success,3=Failure. The workhorse "message executed on dest" event. |
| `0x05665fe9ad095383d018353f4cbcba77e84db27dd215081bbf7cdf9ae6fbe48b` | `ExecutionStateChanged(uint64 indexed sourceChainSelector, uint64 indexed sequenceNumber, bytes32 indexed messageId, bytes32 messageHash, uint8 state, bytes returnData, uint256 gasUsed)` | **OffRamp v1.6** (adds sourceChainSelector + gasUsed) |
| `0xe7083f062ca92dcb8a99d77975265459469cea4eb12c03948142d04587a4fdfa` | `ReportAccepted((uint256 priceUpdates, uint256 minSeqNr, (bytes32,uint64,uint64)[] merkleRoots, bytes32 rmnSignatures, uint64 maxSeqNr))` | **CommitStore (≤v1.5)** — commit of a batch's Merkle root |
| `0x1f7fde3216478485539a075584e9c97db890ba7550b5d799117ae29eb7b0d9d8` | `CommitReportAccepted(...)` | **OffRamp v1.6** commit (CommitStore folded in) |
| `0xb04e63db38c49950639fa09d29872f21f5d49d614f3a969d8adf3d4b52e41a62` | `Transmitted(bytes32 configDigest, uint32 epoch)` | OCR transmit (shared OCR2/3 topic) |

> **`CCIPSendRequested` (OnRamp, ≤v1.5)** and **`CCIPMessageSent` (OnRamp, v1.6)** carry the full `EVM2EVMMessage`/`EVM2AnyRampMessage` struct, whose tuple layout is large and **version-specific**. Their topic0 must be computed against the exact deployed OnRamp's ABI — do not hardcode a guessed tuple. The reliable cross-chain join key is **`messageId`** (a `bytes32`), present on `ExecutionStateChanged`/`MessageExecuted` and inside the send event's message struct.

### 2.3 Token pools

| topic0 | Event | Pool type |
|--------|-------|-----------|
| `0x9d228d69b5fdb8d273a2336f8fb8612d039631024ea9bf09c424a9503aa078f0` | `Minted(address indexed sender, address indexed recipient, uint256 amount)` | BurnMint (dest) |
| `0x696de425f79f4a40bc6d2122ca50507f0efbeabbff86a84871b7196ab8ea8df7` | `Burned(address indexed sender, uint256 amount)` | BurnMint (source) |
| `0x2d87480f50083e2b2759522a8fdda59802650a8055e609a7772cf70c07748f52` | `Released(address indexed sender, address indexed recipient, uint256 amount)` | LockRelease (dest) |
| `0x9f1ec8c880f76798e7b793325d625e9b60e4082a553c98f42b6cda368dd60008` | `Locked(address indexed sender, uint256 amount)` | LockRelease (source) |

*(Some pool versions use the 3-arg `Released(address,address,address,uint256)` `0xefb6092a…` / `Locked(address,address,uint256)` `0x989eaa91…` — verify against the deployed pool.)*

### 2.4 FeeQuoter / PriceRegistry

| topic0 | Event |
|--------|-------|
| `0xdd84a3fa9ef9409f550d54d6affec7e9c480c878c6ab27b78912a03e1b371c6e` | `UsdPerUnitGasUpdated(uint64 indexed destChain, uint256 value, uint256 timestamp)` |
| `0x52f50aa6d1a95a4595361ecf953d095f125d442e4673716dede699e049de148a` | `UsdPerTokenUpdated(address indexed token, uint256 value, uint256 timestamp)` |

---

## 3. Function signatures (chain-agnostic)

### 3.1 Router (entrypoint)

`EVM2AnyMessage = (bytes receiver, bytes data, (address token, uint256 amount)[] tokenAmounts, address feeToken, bytes extraArgs)`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x96f4e9f9` | `ccipSend(uint64 destinationChainSelector, (bytes,bytes,(address,uint256)[],address,bytes) message)` → `bytes32 messageId` | `payable` (native fee) or pulls `feeToken`. **Verified present in ETH Router bytecode.** |
| `0x20487ded` | `getFee(uint64 destinationChainSelector, (bytes,bytes,(address,uint256)[],address,bytes) message)` → `uint256 fee` | quote in `feeToken` units |
| `0xa48a9058` | `isChainSupported(uint64 chainSelector)` → `bool` | **Verified present in ETH Router bytecode.** |
| `0xfbca3b74` | `getSupportedTokens(uint64 chainSelector)` → `address[]` | *(deprecated in newer routers; use TokenAdminRegistry)* |
| `0xa8d87a3b` | `getOnRamp(uint64 destChainSelector)` → `address` | lane onRamp |
| `0xa40e69c7` | `getOffRamps()` → `(uint64 sourceChainSelector, address offRamp)[]` | |
| `0x83826b2b` | `isOffRamp(uint64 sourceChainSelector, address offRamp)` → `bool` | |
| `0xe861e907` | `getWrappedNative()` → `address` | |
| `0x181f5a77` | `typeAndVersion()` → e.g. `"Router 1.2.0"` | version oracle |

### 3.2 FeeQuoter (v1.5) / PriceRegistry (v1.2)

| Selector | Signature |
|----------|-----------|
| `0xd02641a0` | `getTokenPrice(address token)` → `(uint224 value, uint32 timestamp)` |
| `0xd8694ccd` | `getValidatedFee(uint64 destChainSelector, (bytes,bytes,(address,uint256)[],address,bytes) message)` → `uint256` |

---

## 4. Core addresses per chain

### 4.1 Routers (verified live — 11130 B each, same build as Ethereum)

| Chain (id) | Router |
|------------|--------|
| Ethereum (1) | `0x80226fc0Ee2b096224EeAc085Bb9a8cba1146f7D` |
| Base (8453) | `0x881e3A65B4d4a04dD529061dd0071cf975F58bCD` |
| BNB (56) | `0x34B03Cb9086d7D758AC55af71584F81A598759FE` |
| Avalanche (43114) | `0xF4c7E640EdA248ef95972845a62bdC74237805dB` |
| Arbitrum One (42161) | `0x141fa059441E0ca23ce184B6A78bafD2A517DdE8` |
| Optimism (10) | `0x3206695CaE29952f4b0c22a169725a865bc8Ce0f` |
| Polygon PoS (137) | `0x849c5ED5a80F5B408Dd4969b78c2C8fdf0565Bfe` |

### 4.2 Ethereum support contracts (verified live)

| Contract | Address | Verified |
|----------|---------|----------|
| **ARMProxy / RMN** (Risk Management Network proxy) | `0x411dE17f12D1A34ecC7F45f49844626267c75e81` | ✅ (1452 B) |
| **TokenAdminRegistry** (v1.5) | `0xb22764f98dD05c789929716D677382Df22C05Cb6` | ✅ (5193 B) |
| **RegistryModuleOwnerCustom** | `0x13022e3e6C77524308BD56AEd716E88311b2E533` | ✅ (972 B) |

> **Per-chain RMN / FeeQuoter / TokenAdminRegistry / lane ramps:** these are network-specific and change with each lane/version. The authoritative live source is the [CCIP Directory](https://docs.chain.link/ccip/directory/mainnet) (JS-rendered — not scrapable via plain fetch). Resolve at runtime: the lane OnRamp is `Router.getOnRamp(destSelector)` (`0xa8d87a3b`); OffRamps via `Router.getOffRamps()` (`0xa40e69c7`); then read the ramp's `getDynamicConfig()` for the FeeQuoter/RMN it uses. **Only the addresses explicitly marked verified above were bytecode-checked; do not assume the Ethereum support addresses carry to other chains.**

---

## 5. Detection invariants & gotchas

1. **Use the chain selector, never the EVM chain ID** for any CCIP lane logic. The mapping in §1 is the only correct bridge.
2. **`messageId` is the cross-chain join key.** A send on the source and its `ExecutionStateChanged`/`MessageExecuted` on the destination share the same `bytes32 messageId`. Sequence numbers are per-lane and not globally unique.
3. **`ExecutionStateChanged.state`**: 2 = Success, 3 = Failure. A `Failure` still means the message was delivered/consumed — it won't be retried automatically unless it's a manual-exec recoverable failure.
4. **Two `ExecutionStateChanged` shapes** (≤v1.5 vs v1.6) → different topic0 (§2.2). Match by OffRamp version.
5. **The send-side event (`CCIPSendRequested`/`CCIPMessageSent`) carries a large version-specific struct** — compute its topic0 against the live OnRamp ABI, don't hardcode. Prefer keying on `messageId`.
6. **Router is stable; ramps are not.** `Router.getOnRamp`/`getOffRamps` reflect the *current* lane contracts; historical messages may have used now-decommissioned ramps. For historical scans, collect ramp addresses from `OnRampSet`/`OffRampAdded` events on the Router.
7. **Fee token can be LINK or the wrapped-native** (or native via `msg.value`); `getFee` returns the amount in the chosen `feeToken`. Watch the `feeToken` field, not just LINK.
8. **RMN (Risk Management Network)** can "curse" a lane, halting it — monitor the ARMProxy if you depend on liveness.

---

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- chain selectors (uint64, decimal — store as numeric, shown here for reference)
-- ETH 5009297550715157269 | BASE 15971525489660198786 | BNB 11344663589394136015
-- AVAX 6433500567565415381 | ARB 4949039107694359620 | OP 3734403246176062136 | POL 4051577828743386545

-- topics
ROUTER_MESSAGE_EXECUTED   = '\x9b877de93ea9895756e337442c657f95a34fc68e7eb988bdfa693d5be83016b6'
ROUTER_OFFRAMP_ADDED      = '\xa4bdf64ebdf3316320601a081916a75aa144bcef6c4beeb0e9fb1982cacc6b94'
ROUTER_ONRAMP_SET         = '\x1f7d0ec248b80e5c0dde0ee531c4fc8fdb6ce9a2b3d90f560c74acd6a7202f23'
EXEC_STATE_CHANGED_V15    = '\xd4f851956a5d67c3997d1c9205045fef79bae2947fdee7e9e2641abc7391ef65'
EXEC_STATE_CHANGED_V16    = '\x05665fe9ad095383d018353f4cbcba77e84db27dd215081bbf7cdf9ae6fbe48b'
COMMIT_REPORT_ACCEPTED_V15= '\xe7083f062ca92dcb8a99d77975265459469cea4eb12c03948142d04587a4fdfa'
USD_PER_UNIT_GAS_UPDATED  = '\xdd84a3fa9ef9409f550d54d6affec7e9c480c878c6ab27b78912a03e1b371c6e'
POOL_BURNED               = '\x696de425f79f4a40bc6d2122ca50507f0efbeabbff86a84871b7196ab8ea8df7'
POOL_MINTED               = '\x9d228d69b5fdb8d273a2336f8fb8612d039631024ea9bf09c424a9503aa078f0'
-- selectors
SEL_CCIP_SEND             = '\x96f4e9f9'
SEL_GET_FEE               = '\x20487ded'
SEL_IS_CHAIN_SUPPORTED    = '\xa48a9058'
SEL_GET_ONRAMP            = '\xa8d87a3b'

-- routers
ETH_CCIP_ROUTER   = '\x80226fc0ee2b096224eeac085bb9a8cba1146f7d'
BASE_CCIP_ROUTER  = '\x881e3a65b4d4a04dd529061dd0071cf975f58bcd'
BNB_CCIP_ROUTER   = '\x34b03cb9086d7d758ac55af71584f81a598759fe'
AVAX_CCIP_ROUTER  = '\xf4c7e640eda248ef95972845a62bdc74237805db'
ARB_CCIP_ROUTER   = '\x141fa059441e0ca23ce184b6a78bafd2a517dde8'
OP_CCIP_ROUTER    = '\x3206695cae29952f4b0c22a169725a865bc8ce0f'
POL_CCIP_ROUTER   = '\x849c5ed5a80f5b408dd4969b78c2c8fdf0565bfe'
-- Ethereum support
ETH_CCIP_ARMPROXY = '\x411de17f12d1a34ecc7f45f49844626267c75e81'
ETH_CCIP_TOKEN_ADMIN_REGISTRY = '\xb22764f98dd05c789929716d677382df22c05cb6'
```

---

## 7. Verification & sources

- **Chain selectors:** `smartcontractkit/chain-selectors` `selectors.yml` (all 7 confirmed exact).
- **Routers:** `eth_getCode` non-empty (11130 B) on all 7 chains; Ethereum `typeAndVersion() = "Router 1.2.0"`.
- **Selectors:** computed locally (keccak); `ccipSend` (`0x96f4e9f9`) and `isChainSupported` (`0xa48a9058`) confirmed present in the live Ethereum Router bytecode.
- **Ethereum support contracts:** `eth_getCode` non-empty (ARMProxy 1452 B, TokenAdminRegistry 5193 B, RegistryModuleOwnerCustom 972 B).
- **Topics:** computed locally from canonical signatures. The send-side message-struct events and the v1.6 commit event tuples are version-specific — flagged in §2.2.
- Sources: [CCIP Directory (mainnet)](https://docs.chain.link/ccip/directory/mainnet) · [CCIP architecture](https://docs.chain.link/ccip/concepts/architecture) · [chain-selectors repo](https://github.com/smartcontractkit/chain-selectors) · `smartcontractkit/chainlink` & `smartcontractkit/ccip` `contracts/src/v0.8/ccip/`.
