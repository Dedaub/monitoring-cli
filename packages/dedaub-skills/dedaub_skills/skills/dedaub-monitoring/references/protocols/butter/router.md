# Butter Network — ButterRouter (V2 / V3 / V31 / V4) + Receiver + SwapAdapter — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain)

**Status:** verified against live RPC on Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137) and the canonical `butternetwork/butter-router-contracts` repo on 2026-06-09. Extended on 2026-09-29: Robinhood Chain (4663), the live destination executor **Receiver V3.1** `0xC6136f019a7ca92044482373c73367e13bA4c672`, the second V4 set of `deployments/deploy.json` (env `main`) and the OmniAdapter; every address re-checked with `eth_getCode` on all eight chains, and the receiver event topics checked in the deployed bytecode.
**Scope:** the **user-facing router layer** that sits in front of the MOS bridge ([mos-v3.md](mos-v3.md)): `ButterRouterV2` (legacy), `ButterRouterV3`, `ButterRouterV31`, `ButterRouterV4`, the destination-side `Receiver` / `ReceiverV2` / Receiver V3.1, and the DEX-call helpers `SwapAdapter` / `SwapAdapterV3` / `SwapAggregator` (plus the MORC20 `OmniAdapter`). Topics + selectors are **chain-agnostic**; addresses are network-specific (and **identical across chains** by deterministic deploy — key on `(chainId, address)`).

A ButterRouter is a **swap-and-bridge aggregator**, not the bridge itself. The source-side flow is: `swapAndBridge` does an optional local DEX swap (via SwapAdapter/SwapAggregator, e.g. into USDC), takes the integrator/router fee (`CollectFee`), then calls `MOS.swapOutToken` — all in one tx, emitting **`SwapAndBridge`** alongside the bridge's `MessageOut`. The destination side: the MOS bridge calls **`Receiver.onReceived`**, which does the destination DEX swap + final callback and emits **`RemoteSwapAndCall`**. A same-chain swap with no bridge emits **`SwapAndCall`**.

**Destination failure and refund path.** When the destination swap fails (or gas runs low), the receiver keeps the bridged source token, stores a hash of the order, and emits **`SwapFailed`** (status only: the token stays in the receiver). A keeper then either retries with `execSwap` (emits `RemoteSwapAndCall`) or refunds with `swapRescueFunds`, which sends the source token from the receiver to the user and emits **`SwapRescueFunds`**. All three events carry the bridge `orderId` in topic1, the same key as `MessageOut` / `MessageIn` in [mos-v3.md](mos-v3.md). In the pinned 12-hour window 2026-09-28 00:00–12:00 UTC every `RemoteSwapAndCall`, `SwapFailed` and `SwapRescueFunds` log on the eight chains came from Receiver V3.1 `0xC6136f019a7ca92044482373c73367e13bA4c672`.

**Each router version is a non-upgradeable (immutable) standalone deployment** at a deterministic, version-distinct address shared across chains. There is **no proxy** — to "upgrade," Butter deploys a new version (V2→V3→V31→V4) at a new address and points the front-end at it. So a monitor must index **all live router versions in parallel**.

**Router version map (deterministic addresses, same on every EVM chain):**

| Version | Address | Solc | Status |
|---------|---------|------|--------|
| ButterRouterV2 | `0xbB21e441fb738F54e6eC244e435475096E179d66` | 0.8.x | legacy (MOS V2-era), still live |
| ButterRouterV3 | `0xEE030ec6F4307411607E55aCD08e628Ae6655B86` | 0.8.20 | **live, primary** (most volume) |
| ButterRouterV31 | `0xEE0319cF0BCa5d09333f9F6277743E8De31bD69A` | 0.8.25 | live (gas-optimized, zero-fee variant) |
| ButterRouterV4 | `0xee040187f934FB9E41621966B1bd3E98D8319b86` | 0.8.25 | live (newest; low volume so far) |
| ButterRouterV4 (deploy.json env `main`) | `0x2c702868572b2B7BAa70B7296dB6C0991f46B150` | 0.8.25 | second V4 deployment; same runtime bytecode as `0xee040187f934FB9E41621966B1bd3E98D8319b86` on each chain; 0 `SwapAndBridge` in the pinned window |
| Receiver | `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5` | 0.8.20 | destination executor (`Receiver.sol` build, no `doSwapAndCall`); the official docs list it as the Receiver on Avalanche, Optimism and the other chains that have no Receiver V3.1 |
| ReceiverV2 | `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` | 0.8.25 | earlier `ReceiverV2.sol` build; deploy.json names it `ReceiverV2` on Optimism only; 0 receiver events in the pinned window |
| **Receiver V3.1** (deploy.json key `ReceiverV2`) | `0xC6136f019a7ca92044482373c73367e13bA4c672` | 0.8.25 | **live destination executor** (`ReceiverV2.sol` build); the official "Deployed Contracts v3" page calls it "Receiver V3.1" |
| ReceiverV2 (deploy.json env `main`) | `0xed991c6c1B24811CA4D15ed0E0CFB21aAB3c2ef7` | 0.8.25 | receiver of the `main` V4 set; 0 receiver events in the pinned window |
| SwapAdapter | `0x002162B2aEe2dD657FB131b28CC34deE6797b66f` | 0.8.20 | DEX-call helper |
| SwapAdapterV3 | `0xaa301070448385cfAaC5913A67B16C4392944a8f` | — | DEX-call helper ("Adaptor V3.1" in the official docs) |
| SwapAggregator | `0x4C0Ce9aD38BC3132ad1C8AE7E00D48f9524EbC03` | — | DEX aggregation helper (V4-era) |
| OmniAdapter | `0x3321dE36B6C29A6fa102A67bd5C48E5756Baa596` | 0.8.20 | MORC20 omnichain-token adapter (`interTransferAndCall`); Ethereum and BNB only |

> **The V3, V31 and V4 routers emit byte-identical `SwapAndBridge` / `SwapAndCall` / `CollectFee` events** (same topic0s) — disambiguate by emitter address. `RemoteSwapAndCall` is declared in the V3/V4 interfaces, but its topic0 is in the runtime bytecode of ButterRouterV2 and ButterRouterV3 only (absent from V31 and both V4 routers); the receivers emit it. The V2 router emits a **different** `SwapAndBridge` / `SwapAndCall` / `CollectFee` shape (see §1.2). The `swapAndBridge` *function selector* differs between V3/V31 and V4 (V4 added a `_deadline` param).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally on 2026-06-09; `SwapAndBridge` confirmed against live ETH router logs (§Verification).

### 1.1 ButterRouterV3 / V31 / V4 (identical signatures — disambiguate by emitter)

| topic0 | Event |
|--------|-------|
| `0xba828651bf4de06e53231285961e555fd7dfe17a3e39d64b09fbaa8ebc0166c6` | `SwapAndBridge(address indexed referrer, address indexed initiator, address indexed from, bytes32 transferId, bytes32 orderId, address originToken, address bridgeToken, uint256 originAmount, uint256 bridgeAmount, uint256 toChain, bytes to)` |
| `0x60656aafa8d4c0a705aeb148b167d7db921d08852cd2261b270d5c7a2e655f83` | `SwapAndCall(address indexed referrer, address indexed initiator, address indexed from, bytes32 transferId, address originToken, address swapToken, uint256 originAmount, uint256 swapAmount, address receiver, address target, uint256 callAmount)` (same-chain swap) |
| `0x593e4dbcb8f7312fc3bdd77e2095da131a6e1993f37752d12576d04e1f7253b4` | `RemoteSwapAndCall(bytes32 indexed orderId, address indexed receiver, address indexed target, address originToken, address swapToken, uint256 originAmount, uint256 swapAmount, uint256 callAmount, uint256 fromChain, uint256 toChain, bytes from)` (topic0 present in the V3 router bytecode, absent from V31/V4; the live emitter is the Receiver — see §1.3) |
| `0xfe2e49614659d9447156c9e3846112ea8edda361dcd696be486f6f977ce854e5` | `CollectFee(address indexed token, address indexed receiver, address indexed integrator, uint256 routerAmount, uint256 integratorAmount, uint256 nativeAmount, uint256 integratorNative, bytes32 transferId)` |

### 1.2 ButterRouterV2 (legacy — DIFFERENT shapes, distinct topic0s)

| topic0 | Event |
|--------|-------|
| `0x140fc1ae4910fc65859bbe978cf17402f862c5bd87a15aa3a0894d5aa50b0b06` | `SwapAndBridge(bytes32 indexed orderId, address indexed from, address indexed originToken, address bridgeToken, uint256 originAmount, uint256 bridgeAmount, uint256 fromChain, uint256 toChain, bytes to)` |
| `0x54592234b1278d8a9675f22721443e0b9f8a1f4410b55bf6753330073b55e3ef` | `SwapAndCall(address indexed from, address indexed receiver, address indexed target, bytes32 transferId, address originToken, address swapToken, uint256 originAmount, uint256 swapAmount, uint256 callAmount)` |
| `0x593e4dbcb8f7312fc3bdd77e2095da131a6e1993f37752d12576d04e1f7253b4` | `RemoteSwapAndCall(bytes32 indexed orderId, address indexed receiver, address indexed target, address originToken, address swapToken, uint256 originAmount, uint256 swapAmount, uint256 callAmount, uint256 fromChain, uint256 toChain, bytes from)` — **same topic0 as V3** (signature identical; `legacy/interface/IButterRouterV2.sol`). |
| `0xcc4044b4bd9f077089a3cbea5f01bcacf584f45336b1b50a8fb5f5e552da5f14` | `CollectFee(address indexed token, address indexed receiver, uint256 indexed amount, bytes32 transferId, uint8 feeType)` (`feeType`: 0=FIXED, 1=PROPORTION) |

### 1.3 Receiver / ReceiverV2 / Receiver V3.1 (destination-side execution) — emitters `0xC6136f019a7ca92044482373c73367e13bA4c672` (live), `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5`, `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883`, `0xed991c6c1B24811CA4D15ed0E0CFB21aAB3c2ef7`

`Receiver.sol` and `ReceiverV2.sol` declare the same events. All four receiver addresses carry the `RemoteSwapAndCall`, `SwapFailed` and seven-field `SwapRescueFunds` topic0s in their runtime bytecode on Ethereum; `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` and `0xC6136f019a7ca92044482373c73367e13bA4c672` were also checked on Robinhood Chain. The admin topics below were checked in the bytecode of `0xC6136f019a7ca92044482373c73367e13bA4c672` on Ethereum.

| topic0 | Event |
|--------|-------|
| `0x593e4dbcb8f7312fc3bdd77e2095da131a6e1993f37752d12576d04e1f7253b4` | `RemoteSwapAndCall(bytes32 indexed orderId, address indexed receiver, address indexed target, address originToken, address swapToken, uint256 originAmount, uint256 swapAmount, uint256 callAmount, uint256 fromChain, uint256 toChain, bytes from)` — **destination payout** (swap done; `receiver` got `swapAmount - callAmount` of `swapToken`). Same topic0 as the V2/V3 routers: disambiguate by emitter. |
| `0xd457b25e0e458857e38c937f68af3100c40afd88fc5522c5820440d07b44351f` | `SwapFailed(bytes32 indexed _orderId, uint256 _fromChain, address _srcToken, address _dscToken, uint256 _amount, address _receiver, uint256 _minReceived, bytes _from, bytes _callData)` — **status only: destination swap failed; the source token stays parked in the receiver** (alert). |
| `0x7097a92401cb3cede25c9b17516e7ac039f9b02ac27d72e269b2aad16a4ca8f5` | `SwapRescueFunds(bytes32 indexed orderId, address indexed token, address indexed receiver, uint256 amount, uint256 fromChain, uint256 toChain, bytes from)` — **refund payout**: keeper `swapRescueFunds` sent the parked `token` to `receiver`. |
| `0x1f478f1e5aee36a892d86e821aba410dc0934cb0ebd0241dd753708338845453` | `Approve(address indexed executor, bool indexed flag)` — admin: DEX executor allow-list change. |
| `0x53b7c37d01415b2804281f4684b0722e0b01fbd375bf502609f465e17ab4441e` | `SetBridgeAddress(address indexed _bridgeAddress)` — **admin: the only caller allowed into `onReceived` changed** (high severity). |
| `0xf47543a7cab136b12cca0a2ecd728c9d1943f57b923b98db48725d2b76dd4da9` | `SetGasForReFund(uint256 indexed _gasForReFund)` — admin: gas reserve for the failure path. |
| `0xd963701e30b9d04e85bfbf92c227f5d0b832d24c25598c3fbeeae8761d6ded95` | `UpdateKeepers(address _keeper, bool _flag)` — admin: keeper set (keepers call `execSwap` / `swapRescueFunds`). |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` — Ownable2Step owner handover started. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |

An earlier revision of this file listed `SwapRescueFunds` as a four-field event with topic0 `0x96bd27c30adb4ab40a10d5bd2f782f70f15773d913046b658cf92a15a0abb399`. That topic0 is in the bytecode of none of the receivers, and it returned 0 logs on all eight chains in the pinned window; use `0x7097a92401cb3cede25c9b17516e7ac039f9b02ac27d72e269b2aad16a4ca8f5`.

### 1.4 SwapAdapter / SwapAggregator

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` (token movement during the adapter swap) |

(`SwapComplete` / `SweepTokenWithFee` are internal-tooling events; the load-bearing router events are §1.1–1.3.)

### 1.4a OmniAdapter (MORC20 omnichain tokens) — emitter `0x3321dE36B6C29A6fa102A67bd5C48E5756Baa596` (Ethereum, BNB)

| topic0 | Event |
|--------|-------|
| `0xadc8fb4fd6236a49e67bfef72a2bc5667378b180e839beee9200fb60c2bd4b22` | `InterTransferAndCall(address proxy, address token, uint256 amount)` — MORC20 cross-chain send through the token's own proxy (not through MOS). |
| `0x54592234b1278d8a9675f22721443e0b9f8a1f4410b55bf6753330073b55e3ef` | `SwapAndCall(address indexed from, address indexed receiver, address indexed target, bytes32 transferId, address originToken, address swapToken, uint256 originAmount, uint256 swapAmount, uint256 callAmount)` — **same shape and topic0 as the ButterRouterV2 `SwapAndCall`**; disambiguate by emitter. |

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

### 2.4 Receiver / ReceiverV2 / Receiver V3.1 — callback entrypoint, keeper and admin functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2344e655` | `onReceived(bytes32 _orderId, address _srcToken, uint256 _amount, uint256 _fromChain, bytes _from, bytes _swapAndCall)` | **called only by the MOS bridge** (`msg.sender == bridgeAddress`). Does destination swap + callback; emits `RemoteSwapAndCall` or `SwapFailed`. |
| `0x4bb24c4e` | `doSwapAndCall(bytes32 _orderId, address _srcToken, uint256 _amount, uint256 _fromChain, bytes _from, bytes _swapData, bytes _callbackData)` | self-call only (`msg.sender == address(this)`), wrapped in `try` by `onReceived`; present in the `ReceiverV2.sol` builds (`0xa410c91AE49633D78A55BbB3479FDb8fCae0D883`, `0xC6136f019a7ca92044482373c73367e13bA4c672`, `0xed991c6c1B24811CA4D15ed0E0CFB21aAB3c2ef7`), absent from `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5`. |
| `0x2c9e3421` | `swapRescueFunds(bytes32 _orderId, uint256 _fromChain, address _srcToken, uint256 _amount, address _dscToken, address _receiver, bytes _from, bytes _callbackData)` | **keeper only**. Refund path: checks the stored failed-order hash, sends `_srcToken` to `_receiver`, emits `SwapRescueFunds`. |
| `0x3f07fe0d` | `execSwap(bytes32 _orderId, uint256 _fromChain, address _srcToken, uint256 _amount, bytes _from, bytes _swapData, bytes _callbackData)` | **keeper only**. Retries a failed order; emits `RemoteSwapAndCall`. |
| `0xa7931169` | `storedFailedSwap(bytes32)` → `bytes32` | view: non-zero = the order is parked (failed, not yet rescued or retried). |
| `0xa3c573eb` | `bridgeAddress()` → `address` | view: returns the MOS V3 bridge `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` (read at `0xC6136f019a7ca92044482373c73367e13bA4c672` on Ethereum and Robinhood Chain, and at `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` on Ethereum). |
| `0x7f5a22f9` | `setBridgeAddress(address _bridgeAddress)` | owner only; emits `SetBridgeAddress`. |
| `0x9178bd70` | `updateKeepers(address _keeper, bool _flag)` | owner only; emits `UpdateKeepers`. |
| `0x78e3214f` | `rescueFunds(address _token, uint256 _amount)` | owner only: sweeps any token held by the receiver to the owner; emits no receiver event (only the token `Transfer`). |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09 (rows added on 2026-09-29 checked the same way). **The same literals are used on the other chains** (deterministic deploy) — see §4 for the per-chain presence (Optimism, Avalanche and Robinhood Chain are partial).

| Role | Address | Bytecode | One-liner |
|------|---------|----------|-----------|
| ButterRouterV2 | `0xbB21e441fb738F54e6eC244e435475096E179d66` | 15193 B | Legacy aggregator (MOS V2-era). |
| **ButterRouterV3** | `0xEE030ec6F4307411607E55aCD08e628Ae6655B86` | 20281 B | **Primary** aggregator (1789 `SwapAndBridge` in 49k blocks). |
| ButterRouterV31 | `0xEE0319cF0BCa5d09333f9F6277743E8De31bD69A` | 15317 B | Gas-optimized variant (62 logs/49k). |
| ButterRouterV4 | `0xee040187f934FB9E41621966B1bd3E98D8319b86` | 15768 B | Newest (0 logs in window — deployed, low usage). |
| ButterRouterV4 (env `main`) | `0x2c702868572b2B7BAa70B7296dB6C0991f46B150` | 15768 B | Same runtime bytecode as `0xee040187f934FB9E41621966B1bd3E98D8319b86`; 0 `SwapAndBridge` in the pinned window. |
| Receiver | `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5` | 14771 B | Destination executor (`Receiver.sol` build). |
| ReceiverV2 | `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` | 13686 B | Earlier `ReceiverV2.sol` build; 0 receiver events in the pinned window. |
| **Receiver V3.1** | `0xC6136f019a7ca92044482373c73367e13bA4c672` | 13807 B | **Live destination executor**: 8 `RemoteSwapAndCall` in the pinned window. `owner()` = EOA `0x0cdae5da23b64bfecd421d6487ffeabf6558828d`; `bridgeAddress()` = MOS V3 bridge. |
| ReceiverV2 (env `main`) | `0xed991c6c1B24811CA4D15ed0E0CFB21aAB3c2ef7` | 13756 B | Receiver of the `main` V4 set; 0 receiver events in the pinned window. |
| SwapAdapter | `0x002162B2aEe2dD657FB131b28CC34deE6797b66f` | 10533 B | DEX-call helper. |
| SwapAdapterV3 | `0xaa301070448385cfAaC5913A67B16C4392944a8f` | 11170 B | DEX-call helper. |
| SwapAggregator | `0x4C0Ce9aD38BC3132ad1C8AE7E00D48f9524EbC03` | 11749 B | DEX aggregation helper. |
| OmniAdapter | `0x3321dE36B6C29A6fa102A67bd5C48E5756Baa596` | 8545 B | MORC20 omnichain-token adapter (also on BNB; no code on the other six targets). |

## 4. Addresses — Base / BNB / Arbitrum / Optimism / Polygon (identical literals) + Avalanche and Robinhood Chain (partial)

Verified via `eth_getCode` on each chain on 2026-09-29 (✓ = runtime bytecode present, ✗ = `0x` and nonce 0). **Base (8453), BNB (56), Arbitrum (42161) and Polygon (137) carry almost the full set at the exact Ethereum literals**; Optimism, Avalanche and Robinhood Chain carry a subset. The bytecode size is given where it differs from Ethereum; a same-size contract can still have a different code hash (constructor arguments differ per chain).

| Router/contract | Address | ETH | Base | BNB | Arb | OP | Poly | Avax | RH |
|---|---|---|---|---|---|---|---|---|---|
| ButterRouterV2 | `0xbB21e441fb738F54e6eC244e435475096E179d66` | ✓ | ✓ | ✓ | ✓ (15640 B) | ✓ (15640 B) | ✓ | ✗ | ✗ |
| ButterRouterV3 | `0xEE030ec6F4307411607E55aCD08e628Ae6655B86` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| ButterRouterV31 | `0xEE0319cF0BCa5d09333f9F6277743E8De31bD69A` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (15473 B) |
| ButterRouterV4 | `0xee040187f934FB9E41621966B1bd3E98D8319b86` | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✗ |
| ButterRouterV4 (env `main`) | `0x2c702868572b2B7BAa70B7296dB6C0991f46B150` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Receiver | `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5` | ✓ | ✓ (14829 B) | ✓ (14829 B) | ✓ (14829 B) | ✓ (14829 B) | ✓ (14829 B) | ✓ (14465 B) | ✗ |
| ReceiverV2 | `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| **Receiver V3.1** | `0xC6136f019a7ca92044482373c73367e13bA4c672` | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| ReceiverV2 (env `main`) | `0xed991c6c1B24811CA4D15ed0E0CFB21aAB3c2ef7` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| SwapAdapter | `0x002162B2aEe2dD657FB131b28CC34deE6797b66f` | ✓ | ✓ | ✓ | ✓ (10919 B) | ✓ (10919 B) | ✓ | ✗ | ✗ |
| SwapAdapterV3 | `0xaa301070448385cfAaC5913A67B16C4392944a8f` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (10784 B) | ✓ (10784 B) |
| SwapAggregator | `0x4C0Ce9aD38BC3132ad1C8AE7E00D48f9524EbC03` | ✓ | ✓ (11714 B) | ✓ (11714 B) | ✓ (11714 B) | ✓ | ✓ (11714 B) | ✗ | ✓ |
| OmniAdapter | `0x3321dE36B6C29A6fa102A67bd5C48E5756Baa596` | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Optimism** lacks ButterRouterV4 `0xee040187f934FB9E41621966B1bd3E98D8319b86` and Receiver V3.1; it does carry the `main` V4 set, ReceiverV2 `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` and SwapAggregator (the 2026-06-09 check found `0x` at the last two; both had code on 2026-09-29). The official docs list the Receiver `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5` for Optimism. **Avalanche** runs a minimal set: **ButterRouterV31 + Receiver + SwapAdapterV3 only**. MOS V3 is fully present on Optimism, Avalanche and Robinhood Chain (see mos-v3.md).

### 4.1 Robinhood Chain (chain ID 4663)

Listed on the official "Deployed Contracts v3" page (Router V3.1, Adaptor, Receiver) and in `deployments/deploy.json` (`prod` → `Robinhood`: ButterRouterV31, SwapAdapterV3, SwapAggregator, ReceiverV2 = `0xC6136f019a7ca92044482373c73367e13bA4c672`). Verified with `eth_getCode` on `https://rpc.mainnet.chain.robinhood.com` on 2026-09-29.

| Role | Address | Bytecode | One-liner |
|------|---------|----------|-----------|
| **ButterRouterV31** | `0xEE0319cF0BCa5d09333f9F6277743E8De31bD69A` | 15473 B | The only router on Robinhood Chain. A different build from the 15317 B one on the other chains; its bytecode carries the same `SwapAndBridge` / `SwapAndCall` / `CollectFee` topic0s and the V3 `swapAndBridge` / `swapAndCall` selectors. 8 `SwapAndBridge` in the pinned window. |
| **Receiver V3.1** | `0xC6136f019a7ca92044482373c73367e13bA4c672` | 13807 B | Live destination executor: 2 `RemoteSwapAndCall` in the pinned window. `owner()` = EOA `0x0cdae5da23b64bfecd421d6487ffeabf6558828d`; `bridgeAddress()` = `0x0000317Bec33Af037b5fAb2028f52d14658F6A56`. |
| ReceiverV2 | `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` | 13686 B | Earlier `ReceiverV2.sol` build; not in the official lists for Robinhood Chain; 0 receiver events in the pinned window. |
| SwapAdapterV3 | `0xaa301070448385cfAaC5913A67B16C4392944a8f` | 10784 B | DEX-call helper ("Adaptor"). |
| SwapAggregator | `0x4C0Ce9aD38BC3132ad1C8AE7E00D48f9524EbC03` | 11749 B | DEX aggregation helper. |

**Not deployed on Robinhood Chain** (`eth_getCode` = `0x`, nonce 0): ButterRouterV2, ButterRouterV3, ButterRouterV4 (both sets), Receiver `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5`, ReceiverV2 (env `main`), SwapAdapter, OmniAdapter. The bridged asset in the sampled Robinhood transfers is WETH `0x0bd7d308f8e1639fab988df18a8011f41eacad73` (`symbol()` = `WETH`): `swapAndBridge` wraps the native ETH (a `Transfer` from `0x0` to the router), then the router moves the WETH into the bridge. An inbound `messageIn` burns WETH at the bridge (a `Transfer` to `0x0`) and pays native ETH to the recipient, which leaves no log: the sampled `MessageIn` (tx `0x048dd79a5812c456d87fb53cf0c172aa1e3e3238693677c7fce6a65072d89f91`, from X Layer 196) has `token` = `0x0000000000000000000000000000000000000000` and `to` = the recipient.

## 5. Cross-chain summary

| Chain | ID | V2 | V3 | V31 | V4 | V4 (`main`) | Receiver | ReceiverV2 | Receiver V3.1 | SwapAdapterV3 | SwapAggregator |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Ethereum | 1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Base | 8453 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| BNB | 56 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Arbitrum | 42161 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Optimism | 10 | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ |
| Polygon | 137 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Avalanche | 43114 | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ |
| Robinhood Chain | 4663 | ✗ | ✗ | ✓ (15473 B build) | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✓ |

Columns: V2 `0xbB21e441fb738F54e6eC244e435475096E179d66`, V3 `0xEE030ec6F4307411607E55aCD08e628Ae6655B86`, V31 `0xEE0319cF0BCa5d09333f9F6277743E8De31bD69A`, V4 `0xee040187f934FB9E41621966B1bd3E98D8319b86`, V4 (`main`) `0x2c702868572b2B7BAa70B7296dB6C0991f46B150`, Receiver `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5`, ReceiverV2 `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883`, Receiver V3.1 `0xC6136f019a7ca92044482373c73367e13bA4c672`, SwapAdapterV3 `0xaa301070448385cfAaC5913A67B16C4392944a8f`, SwapAggregator `0x4C0Ce9aD38BC3132ad1C8AE7E00D48f9524EbC03`. The ReceiverV2 (`main`) `0xed991c6c1B24811CA4D15ed0E0CFB21aAB3c2ef7` follows the V4 (`main`) column; SwapAdapter `0x002162B2aEe2dD657FB131b28CC34deE6797b66f` follows the V2 column; OmniAdapter `0x3321dE36B6C29A6fa102A67bd5C48E5756Baa596` is on Ethereum and BNB only.

**Vanity-address tells:** the live routers V3 `0xEE030ec6F4307411607E55aCD08e628Ae6655B86` and V31 `0xEE0319cF0BCa5d09333f9F6277743E8De31bD69A` share their first two bytes, and V4 `0xee040187f934FB9E41621966B1bd3E98D8319b86` and the Receiver `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5` follow the same vanity pattern (a version-like second byte). Receiver V3.1 `0xC6136f019a7ca92044482373c73367e13bA4c672` and ReceiverV2 `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` have no vanity prefix. Same literal everywhere ⇒ key on `(chainId, address)`.

**Counterparty / extra-target chains:** the same router addresses also exist on zkSync Era (324, *different* literals — ButterRouterV2 `0x73E0d6E696Fc38DaC6bf68b4A0b06d35Df10492E`), Linea, Scroll, Mantle, Blast (81457), Merlin, Bevm, AINN, Conflux, Klaytn, X Layer, Unichain, zkLink, Monad, Arc (5042, Receiver `0x1c657A87071ff402acD673f3559457e1003D9718` per the official docs), plus **Tron** (base58 addresses, e.g. ButterRouterV3 `TPYm4fQJxmoBuhAbNWCBx2ehzhVJ1fxFNP`) and a **Solana** receiver (`SolanaReceiver.sol`). Recorded as findings; only the eight targets are detailed above.

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **ButterRouterV2/V3/V31/V4** | **NOT proxies — immutable** | Full-size bytecode (13–20 KB); EIP-1967 impl slot `0x360894…` reads `0x0` (confirmed live on ETH ButterRouterV3). No `Upgraded` event. "Upgrade" = new version at a new address. | `Ownable` owner sets fee/bridge/adapter config; **code is fixed**. |
| **Receiver / ReceiverV2 / Receiver V3.1** | **NOT proxies — immutable** | Full bytecode (13–14 KB); impl slot `0x0` (read on 2026-09-29 on every chain where each receiver has code). | `Ownable2Step`; the owner can change `bridgeAddress`, the keeper set and the executor allow-list, and can sweep tokens with `rescueFunds`. Receiver V3.1 `owner()` = EOA `0x0cdae5da23b64bfecd421d6487ffeabf6558828d` on Ethereum and Robinhood Chain. |
| **SwapAdapter / SwapAdapterV3 / SwapAggregator / OmniAdapter** | **NOT proxies — immutable** | Full bytecode (8–12 KB); impl slot `0x0`. | `Ownable` / `Ownable2Step`. |

There is **no `Upgraded(address)` to watch in the router layer** — instead watch for *new router-version deployments* and the front-end repointing. The upgradeable parts of Butter are all in the bridge layer ([mos-v3.md](mos-v3.md) §Proxies).

## 7. Detection invariants & gotchas

1. **`SwapAndBridge` is the source-side router event; `MessageOut` (mos-v3.md) is the bridge twin** — they fire in the **same tx**. The shared `orderId` joins router→bridge→destination. (Live: ButterRouterV3 `SwapAndBridge` and MOS `MessageOut` shared tx `0x6477b1e1…`.)
2. **V3, V31 and V4 emit the SAME `SwapAndBridge`/`SwapAndCall`/`CollectFee` topic0s.** You cannot tell the router version from topic0 alone — **disambiguate by emitter address** (`0xEE030ec6F4307411607E55aCD08e628Ae6655B86` vs `0xEE0319cF0BCa5d09333f9F6277743E8De31bD69A` vs `0xee040187f934FB9E41621966B1bd3E98D8319b86` / `0x2c702868572b2B7BAa70B7296dB6C0991f46B150`).
3. **`RemoteSwapAndCall` topic0 `0x593e4dbcb8f7312fc3bdd77e2095da131a6e1993f37752d12576d04e1f7253b4` is in the bytecode of ButterRouterV2, ButterRouterV3 and all four receivers** (identical signature). The V31 and V4 router bytecode does not contain it. In the pinned window every emitter was Receiver V3.1 `0xC6136f019a7ca92044482373c73367e13bA4c672`. Always pair the topic with the emitter.
4. **ButterRouterV2 events are a DIFFERENT shape** (its `SwapAndBridge` indexes `orderId/from/originToken`, no `referrer/initiator`; its `CollectFee` is the 5-field FIXED/PROPORTION variant). Don't reuse V3 topic0s for the V2 router address.
5. **The real user is `initiator`/`from`/`referrer`, never `msg.sender`.** The router forwards to MOS; the Receiver is invoked by the bridge. Attribute by event fields.
6. **`swapAndBridge` function selector differs V3/V31 (`0x6e1537da`) vs V4 (`0xdffbf35f`)** because V4 added a `_deadline` parameter — useful to tell which router version a raw tx hit.
7. **`SwapFailed` (`0xd457b25e0e458857e38c937f68af3100c40afd88fc5522c5820440d07b44351f`) on a Receiver = a stuck/parked destination delivery** (swap on the destination chain failed; the source token stays in the receiver and `storedFailedSwap(orderId)` becomes non-zero). It is status only: no token leaves the receiver in that transaction. The order closes with either `RemoteSwapAndCall` (keeper `execSwap`) or `SwapRescueFunds` (keeper `swapRescueFunds`, a `Transfer` of the source token from the receiver to the user). High-value alert. Sample on Base: `SwapFailed` in tx `0x910d32e926d287f1992ed4f420008f23cfcd7fba7a961f9accbce5036766bae6`, then `SwapRescueFunds` for the same `orderId` in tx `0xb85102b557c8f0b19e01644af8162b639f108c632b7641bdf299c1b525c68a72`, sent by keeper EOA `0x9c9a4b36da9c3dc7161cce8e70ead290055df9d1`.
8. **`onReceived` is bridge-gated** (`msg.sender == bridgeAddress`). A direct external call reverts — so every `RemoteSwapAndCall` or `SwapFailed` from `onReceived` traces back to a MOS `MessageIn` in the same tx, with the same `orderId` in topic1. The value leg in that tx is a `Transfer` of the bridged token from `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` to the receiver, then (on success) a `Transfer` of the swapped token from the receiver to `RemoteSwapAndCall.receiver`.
9. **Avalanche has only ButterRouterV31 + Receiver + SwapAdapterV3** of the router layer; Optimism lacks ButterRouterV4 `0xee040187f934FB9E41621966B1bd3E98D8319b86` and Receiver V3.1; Robinhood Chain has only ButterRouterV31 (its own 15473 B build), the two `ReceiverV2.sol` receivers, SwapAdapterV3 and SwapAggregator. If you index only V3/V4 you will miss Avalanche and Robinhood router traffic entirely (it's all on V31).
10. **Routers are immutable** — no `Upgraded` event to track in this layer; instead a new version address appears (V2→V3→V31→V4). Keep the full version list in your address set.
11. **Same literal on every EVM chain** (except zkSync, which uses different literals) — key everything on `(chainId, address)`.
12. **Index every receiver address, not only the one named in the docs.** The live destination executor is Receiver V3.1 `0xC6136f019a7ca92044482373c73367e13bA4c672` (deploy.json calls it `ReceiverV2`); `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5`, `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` and `0xed991c6c1B24811CA4D15ed0E0CFB21aAB3c2ef7` still have code, point to the same bridge and carry the same event set. The destination receiver comes from the source-side swap data, so a routing change can move traffic back to them without any on-chain admin event.
13. **Receiver admin triggers.** `SetBridgeAddress` changes the only caller allowed into `onReceived`; `UpdateKeepers` changes who can call `execSwap` / `swapRescueFunds`; `rescueFunds(address,uint256)` lets the owner (an EOA for Receiver V3.1) sweep any parked token and emits only the token `Transfer`. Watch `Transfer` events **from** a receiver whose recipient is the owner.

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics — ButterRouter V3/V31/V4 (chain-agnostic; key on emitter) =====
TOPIC_SWAP_AND_BRIDGE_V3   = '\xba828651bf4de06e53231285961e555fd7dfe17a3e39d64b09fbaa8ebc0166c6'
TOPIC_SWAP_AND_CALL_V3     = '\x60656aafa8d4c0a705aeb148b167d7db921d08852cd2261b270d5c7a2e655f83'
TOPIC_REMOTE_SWAP_AND_CALL = '\x593e4dbcb8f7312fc3bdd77e2095da131a6e1993f37752d12576d04e1f7253b4'  -- in router V2/V3 bytecode + all receivers; live emitter = Receiver V3.1
TOPIC_COLLECT_FEE_V3       = '\xfe2e49614659d9447156c9e3846112ea8edda361dcd696be486f6f977ce854e5'
-- ===== Topics — ButterRouter V2 (legacy, distinct shapes) =====
TOPIC_SWAP_AND_BRIDGE_V2   = '\x140fc1ae4910fc65859bbe978cf17402f862c5bd87a15aa3a0894d5aa50b0b06'
TOPIC_SWAP_AND_CALL_V2     = '\x54592234b1278d8a9675f22721443e0b9f8a1f4410b55bf6753330073b55e3ef'  -- also OmniAdapter SwapAndCall
TOPIC_COLLECT_FEE_V2       = '\xcc4044b4bd9f077089a3cbea5f01bcacf584f45336b1b50a8fb5f5e552da5f14'
-- ===== Topics — Receiver / ReceiverV2 / Receiver V3.1 =====
TOPIC_SWAP_FAILED          = '\xd457b25e0e458857e38c937f68af3100c40afd88fc5522c5820440d07b44351f'  -- status only: token parked in the receiver
TOPIC_SWAP_RESCUE_FUNDS    = '\x7097a92401cb3cede25c9b17516e7ac039f9b02ac27d72e269b2aad16a4ca8f5'  -- 7-field form (the four-field value of an earlier revision was wrong, see §1.3)
TOPIC_RECEIVER_APPROVE     = '\x1f478f1e5aee36a892d86e821aba410dc0934cb0ebd0241dd753708338845453'
TOPIC_SET_BRIDGE_ADDRESS   = '\x53b7c37d01415b2804281f4684b0722e0b01fbd375bf502609f465e17ab4441e'
TOPIC_SET_GAS_FOR_REFUND   = '\xf47543a7cab136b12cca0a2ecd728c9d1943f57b923b98db48725d2b76dd4da9'
TOPIC_UPDATE_KEEPERS       = '\xd963701e30b9d04e85bfbf92c227f5d0b832d24c25598c3fbeeae8761d6ded95'
TOPIC_OWNERSHIP_XFER_START = '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'
-- ===== Topics — OmniAdapter =====
TOPIC_INTER_TRANSFER_CALL  = '\xadc8fb4fd6236a49e67bfef72a2bc5667378b180e839beee9200fb60c2bd4b22'

-- ===== Selectors =====
SEL_SWAP_AND_BRIDGE_V3     = '\x6e1537da'
SEL_SWAP_AND_CALL_V3       = '\x119b8248'
SEL_SWAP_AND_BRIDGE_V4     = '\xdffbf35f'
SEL_SWAP_AND_BRIDGE_V2     = '\x480a3411'
SEL_SWAP_AND_CALL_V2       = '\x8217062d'
SEL_ON_RECEIVED            = '\x2344e655'
SEL_DO_SWAP_AND_CALL       = '\x4bb24c4e'
SEL_SWAP_RESCUE_FUNDS      = '\x2c9e3421'   -- keeper only (refund path)
SEL_EXEC_SWAP              = '\x3f07fe0d'   -- keeper only (retry path)
SEL_STORED_FAILED_SWAP     = '\xa7931169'
SEL_BRIDGE_ADDRESS         = '\xa3c573eb'
SEL_SET_BRIDGE_ADDRESS     = '\x7f5a22f9'
SEL_UPDATE_KEEPERS         = '\x9178bd70'
SEL_RECEIVER_RESCUE_FUNDS  = '\x78e3214f'   -- owner sweep, no receiver event

-- ===== Addresses (IDENTICAL on all EVM targets except zkSync; key on (chainId,addr)) =====
BUTTER_ROUTER_V2           = '\xbb21e441fb738f54e6ec244e435475096e179d66'
BUTTER_ROUTER_V3           = '\xee030ec6f4307411607e55acd08e628ae6655b86'
BUTTER_ROUTER_V31          = '\xee0319cf0bca5d09333f9f6277743e8de31bd69a'
BUTTER_ROUTER_V4           = '\xee040187f934fb9e41621966b1bd3e98d8319b86'
BUTTER_ROUTER_V4_MAIN      = '\x2c702868572b2b7baa70b7296db6c0991f46b150'
BUTTER_RECEIVER            = '\xff031cc2563988bc4afa29e2cd7bcc2d389900a5'
BUTTER_RECEIVER_V2         = '\xa410c91ae49633d78a55bbb3479fdb8fcae0d883'
BUTTER_RECEIVER_V31        = '\xc6136f019a7ca92044482373c73367e13ba4c672'   -- live destination executor (deploy.json key ReceiverV2)
BUTTER_RECEIVER_V2_MAIN    = '\xed991c6c1b24811ca4d15ed0e0cfb21aab3c2ef7'
BUTTER_SWAP_ADAPTER        = '\x002162b2aee2dd657fb131b28cc34dee6797b66f'
BUTTER_SWAP_ADAPTER_V3     = '\xaa301070448385cfaac5913a67b16c4392944a8f'
BUTTER_SWAP_AGGREGATOR     = '\x4c0ce9ad38bc3132ad1c8ae7e00d48f9524ebc03'
BUTTER_OMNI_ADAPTER        = '\x3321de36b6c29a6fa102a67bd5c48e5756baa596'   -- Ethereum and BNB only
BUTTER_RECEIVER_V31_OWNER_EOA = '\x0cdae5da23b64bfecd421d6487ffeabf6558828d'
BUTTER_RELAYER_EOA         = '\xdb61db256a30f3ef46110b8e2520aaec0db08153'   -- messageIn caller seen on ETH, Base, Robinhood
BUTTER_KEEPER_EOA          = '\x9c9a4b36da9c3dc7161cce8e70ead290055df9d1'   -- swapRescueFunds caller seen on Base
-- Avalanche present: V31, Receiver, SwapAdapterV3 only.  Optimism missing: BUTTER_ROUTER_V4, BUTTER_RECEIVER_V31.
-- Robinhood present: V31 (own build), RECEIVER_V31, RECEIVER_V2, SWAP_ADAPTER_V3, SWAP_AGGREGATOR only.
-- ===== Robinhood Chain (chain ID 4663) =====
RH_BUTTER_ROUTER_V31       = '\xee0319cf0bca5d09333f9f6277743e8de31bd69a'   -- 15473 B build
RH_BUTTER_RECEIVER_V31     = '\xc6136f019a7ca92044482373c73367e13ba4c672'
RH_BUTTER_RECEIVER_V2      = '\xa410c91ae49633d78a55bbb3479fdb8fcae0d883'
RH_BUTTER_SWAP_ADAPTER_V3  = '\xaa301070448385cfaac5913a67b16c4392944a8f'
RH_BUTTER_SWAP_AGGREGATOR  = '\x4c0ce9ad38bc3132ad1c8ae7e00d48f9524ebc03'
RH_WETH                    = '\x0bd7d308f8e1639fab988df18a8011f41eacad73'   -- bridged asset in the sampled transfers
```

## 9. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from `butternetwork/butter-router-contracts/contracts/` (`ButterRouterV3.sol`, `ButterRouterV31.sol`, `ButterRouterV4.sol`, `Receiver.sol`, `ReceiverV2.sol`, `interface/IButterRouterV3.sol`, `interface/IButterRouterV4.sol`, `legacy/ButterRouterV2.sol`, `legacy/interface/IButterRouterV2.sol`). A `diff` of the V3 vs V4 interface event blocks confirmed the `SwapAndBridge`/`SwapAndCall`/`RemoteSwapAndCall` bodies are byte-identical (⇒ shared topic0); the V4 *function* differs (`_deadline`).
- **Live cross-check:** `SwapAndBridge` topic0 `0xba828651…` confirmed via `eth_getLogs` on ButterRouterV3 `0xEE030ec6…` (1789 logs/49k blocks, first tx `0x6477b1e1…` — same tx as the MOS `MessageOut`) and on ButterRouterV31 `0xEE0319cF…` (62 logs); ButterRouterV4 `0xee040187…` returned 0 in-window (deployed, low usage).
- **Addresses:** parsed from `deployments/deploy.json` (`prod` env) and existence-checked via `eth_getCode` on all seven target RPCs. The per-chain presence matrix (§4/§5) reflects actual non-empty/`0x` results — Avalanche carries only V31+Receiver+SwapAdapterV3; Optimism lacks V4/ReceiverV2/SwapAggregator.
- **Proxy classification:** EIP-1967 impl slot read live via `eth_getStorageAt` on ButterRouterV3 (ETH) returned `0x0` ⇒ immutable, not a proxy (consistent with full-size bytecode).

Extension of 2026-09-29:

- **Receiver events:** signatures taken from `contracts/Receiver.sol` and `contracts/ReceiverV2.sol` (branch `main`), hashed as `keccak256(sig)`, and checked as `PUSH32` constants in the runtime bytecode (`eth_getCode`) of all four receivers on Ethereum and of `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` / `0xC6136f019a7ca92044482373c73367e13bA4c672` on Robinhood Chain. The four-field `SwapRescueFunds` topic0 of the earlier revision is in none of them. The same bytecode scan showed `RemoteSwapAndCall` in the V2/V3 routers only, the V4 `swapAndBridge` selector `0xdffbf35f` in both V4 routers, and the V3 selector `0x6e1537da` in the Robinhood V31 build.
- **Addresses:** `deployments/deploy.json` (`prod` and `main` environments) and the official "Deployed Contracts v3" page, each address existence-checked with `eth_getCode` on all eight chains (§4 matrix). `owner()` and `bridgeAddress()` read with `eth_call`; WETH `symbol()` read on Robinhood Chain.
- **Activity** (`eth_getLogs`, pinned 12-hour window 2026-09-28 00:00–12:00 UTC, all emitters): `SwapAndBridge` — Ethereum 45 (ButterRouterV3 44, V31 1), Base 26 (V3), Arbitrum 13 (V3), Optimism 0, Polygon 77 (V3), BNB 153 (V3 152, V31 1), Avalanche 0, Robinhood 8 (V31). `RemoteSwapAndCall` — Ethereum 8, Base 4, Arbitrum 2, Optimism 0, Polygon 53, BNB 69, Avalanche 0, Robinhood 2 (all from `0xC6136f019a7ca92044482373c73367e13bA4c672`). `SwapFailed` — Base 1, Arbitrum 1, Polygon 2, BNB 2, others 0. `SwapRescueFunds` (seven-field) — Base 1, Arbitrum 1, Polygon 2, BNB 2, others 0. The four-field topic0 `0x96bd27c30adb4ab40a10d5bd2f782f70f15773d913046b658cf92a15a0abb399`: 0 on all eight chains. A 0 is what was measured in these 12 hours, not a statement that a contract is unused.
- **Sample transactions** (`eth_getTransactionReceipt`): Ethereum `0x7beb518ebcd3b87e6ac6a0f74f862dbc908e98e7f05fb30ef713e229af168b9c` (USDT `Transfer` ButterRouterV3 → bridge, `MessageOut`, `CollectFee`, `SwapAndBridge` in one tx); Ethereum `0xd32148ef67d10691b74608f5eed82abf68d6f08e88d399ed83864794c08a1c6a` (bridge → Receiver V3.1 USDC `Transfer`, swap through SwapAdapterV3, `RemoteSwapAndCall` and `MessageIn` with the same `orderId`); Base `0x910d32e926d287f1992ed4f420008f23cfcd7fba7a961f9accbce5036766bae6` (`SwapFailed`) and `0xb85102b557c8f0b19e01644af8162b639f108c632b7641bdf299c1b525c68a72` (`swapRescueFunds`, USDC `Transfer` receiver → user, `SwapRescueFunds`); Robinhood `0x7fc7503851e04f57fcf2bec0b4bfca3820b21848a7415be39ac684d904875261` (V31 `swapAndBridge` with 0.48 ETH, WETH wrap, `MessageOut` to BNB 56, `SwapAndBridge`) and `0x9f6455dd1d3979396cd74ca0082f592e8a82047f73ccd3ab3d3a7ae55a84732b` (`RemoteSwapAndCall` by Receiver V3.1).
- **Source disagreements:** deploy.json names `0xC6136f019a7ca92044482373c73367e13bA4c672` `ReceiverV2`, the docs name it "Receiver V3.1"; deploy.json names `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` the Optimism `ReceiverV2`, while the docs list `0xFF031cc2563988Bc4afA29E2cD7Bcc2d389900a5` as the Optimism Receiver. On-chain, `0xa410c91AE49633D78A55BbB3479FDb8fCae0D883` has code on seven of the eight chains (not Avalanche) but emitted nothing in the pinned window.

**Authoritative sources:**
- Router repo: <https://github.com/butternetwork/butter-router-contracts> (`deployments/deploy.json`, `contracts/`, `contracts/Receiver.sol`, `contracts/ReceiverV2.sol`, `contracts/OmniAdapter.sol`)
- Docs: <https://docs.butternetwork.io> (Butter Bridge & Routing Integration) · <https://docs.butternetwork.io/butter-swap-integration/deployed-contracts-v3.0>
- Explorers: Etherscan / Basescan / BscScan / Snowscan / Arbiscan / Optimistic Etherscan / Polygonscan / <https://robinhoodchain.blockscout.com>.
