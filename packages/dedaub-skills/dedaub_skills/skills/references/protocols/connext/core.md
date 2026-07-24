# Everclear V6 — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon)

**Status:** verified against live RPC on every listed chain and the canonical `everclearorg/monorepo` repo (`dev` branch) on 2026-06-09.
**Scope:** the current **Everclear** intent-based clearing layer (the rebrand of Connext, post-Amarok). Covers the **EverclearSpoke** (per-spoke-chain intent contract), **SpokeGateway** (Hyperlane messaging adapter), and **FeeAdapterV2** (the actual user-facing entrypoint). Topics and selectors are chain-agnostic; addresses are network-specific. The clearing **EverclearHub** lives on Everclear's own L2 (Hyperlane domain **25327**), which is **outside the seven requested chains** — its Hub topics are documented in §1.4 as a finding. For the legacy Connext Amarok Diamond, see [amarok.md](amarok.md).

Everclear is an **intent/clearing** protocol, not a lock-mint bridge: a user calls `newIntent` (via FeeAdapter) on the origin **Spoke**; solvers fill it on the destination Spoke; the **Hub** (clearing chain) nets and settles via Hyperlane messages between SpokeGateway↔HubGateway. The Spoke and Gateway are **UUPS (ERC-1967) proxies** — `eth_getCode` returns a ~183-byte minimal proxy; the EIP-1967 impl slot is set and the **admin slot is empty** (UUPS, upgrade auth in the impl's `owner`). The **FeeAdapterV2 is a direct (non-proxy) deployment** (~12.8 kB, identical bytecode on all 7 chains). 

**Deployed-version note (verified on-chain 2026-06-09):** the live Spoke is the **V6 interface** — it uses the `IEverclearV2.Intent` struct `(bytes32 initiator, bytes32 receiver, bytes32 inputAsset, bytes32 outputAsset, uint32 origin, uint64 nonce, uint48 timestamp, uint48 ttl, uint256 amount, uint256 amountOutMin, uint32[] destinations, bytes data)` — note **`amountOutMin` and NO `maxFee`** (unlike the older V1 `Intent` which had `uint24 maxFee` and no `amountOutMin`). The deployed entrypoint is **FeeAdapterV2**. All §1/§2 hashes are computed from this V6 struct and matched against the live bytecode and live logs.

> **Vanity / address-collision trap.** The EverclearSpoke, SpokeGateway and (oddly) the EverclearHub all share the **same literal `0xa05A3380…D816`** in the docs. On the **seven spoke chains** `0xa05A3380…` (or its per-chain variant) is the **Spoke**; on the **hub clearing chain** the same literal is the **Hub**. Disambiguate by chain: call `EVERCLEAR()` on a spoke — it returns the **hub domain 25327** (`0x62ef`), proving it is a Spoke pointing at the Hub, not the Hub itself.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Address pattern across the 7 |
|----------|------|--------|------------------------------|
| **EverclearSpoke** (V6) | Per-chain intent contract: `newIntent`, `fillIntent`, `deposit`/`withdraw`, queue processing, settlement receipt. | **UUPS / ERC-1967** | Vanity `0xa05A3380…D816` on ETH/Base/BNB/Arb/OP; **diverges** on Avalanche (`0x9aA2Ecad…`) and Polygon (`0x7189C59e…`). Per-chain impl. |
| **SpokeGateway** (V6) | Hyperlane messaging adapter (Spoke↔Hub). | **UUPS / ERC-1967** | Vanity `0x9ADA72CC…99A7` on ETH/Base/BNB/Arb/OP; diverges on Avax (`0x7EB63a64…`) and Polygon (`0x26CFF54f…`). |
| **FeeAdapterV2** | User-facing entrypoint: `newIntent` (+fee), `newOrder`, Permit2. Wraps the Spoke. | **No** (direct, ~12.8 kB) | **Same literal `0xd0185bfb…540e` on ALL 7 chains** (identical bytecode). |
| **CLEAR / Everclear token** | Governance token. | EIP-1967 proxy (ETH) / OFT | `0x58b9cb81…05E8` on ETH/BNB/Arb/OP/Polygon; absent Base+Avax — see [amarok.md](amarok.md) §10. |
| **EverclearHub** + **HubGateway** | Clearing-chain core (netting, invoices, settlements). | UUPS | On the Everclear L2 (Hyperlane domain **25327**) — NOT on any of the seven. §1.4. |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally with keccak on 2026-06-09 from `everclearorg/monorepo` (`dev`) interfaces. `IntentAdded` (Spoke) and `IntentWithFeesAdded` (FeeAdapter) **confirmed against live logs** at Base block 44 385 499 (one of each).

V6/V2 Intent tuple = `(bytes32,bytes32,bytes32,bytes32,uint32,uint64,uint48,uint48,uint256,uint256,uint32[],bytes)`

### 1.1 EverclearSpoke (V6) — emits all intent/settlement activity

| topic0 | Event |
|--------|-------|
| `0x80eb6c87e9da127233fe2ecab8adf29403109adc6bec90147df35eeee0745991` | `IntentAdded(bytes32 indexed _intentId, uint256 _queueIdx, Intent _intent)` — **origin: user created an intent.** *(verified live, Base)* |
| `0xe3bc4b05ac625e8c55084d86f8bb9a4c1ff02777dccc7ec0f3b3b7e7468cf383` | `IntentFilled(bytes32 indexed _intentId, address indexed _solver, bytes32 indexed _receiver, uint256 _amountOut, uint256 _queueIdx, Intent _intent)` — **destination: solver filled.** |
| `0x4190759d37d5cfe7a1a70e06ec7508a05d12fd9cb76f353da1c9e028e5a48dcf` | `Settled(bytes32 indexed _intentId, address _account, address _asset, uint256 _amount)` — settlement arrived from Hub. |
| `0x8752a472e571a816aea92eec8dae9baf628e840f4929fbcc2d155e6233ff68a7` | `Deposited(address indexed _depositant, address indexed _asset, uint256 _amount)` — solver liquidity in. |
| `0xd1c19fbcd4551a5edfb66d43d2e337c04837afda3482b42bdf569a8fccdae5fb` | `Withdrawn(address indexed _withdrawer, address indexed _asset, uint256 _amount)` — solver liquidity out. |
| `0x43a52e9a77f317a192970b363b14ece56df243fe0dd94f459f63029d657efec3` | `IntentQueueProcessed(bytes32 indexed _messageId, uint256 _firstIdx, uint256 _lastIdx, uint256 _quote)` |
| `0x5e3a5b80dcf8e0fb984fe128ed0db507a86cc0674c4f5980f83b129b2cfdc69e` | `FillQueueProcessed(bytes32 indexed _messageId, uint256 _firstIdx, uint256 _lastIdx, uint256 _quote)` |
| `0x72c7d97e6fac52d20092b101af2183fd0bd04b357a936e82537e8974ea2c0eb7` | `ExternalCalldataExecuted(bytes32 indexed _intentId, bytes _returnData)` |
| `0xc1f1475cd1d27fd368e9f8f208d68469a20695129a6bb78e7d1a0f970f602695` | `FeeAdapterUpdated(address _newFeeAdapter)` |
| `0x34f45330d12e136e35710c0b12bb3d009fb59bf6042d4d9fa611cb7ee4e74ead` | `FillSignerUpdated(address _oldFillSigner, address _newFillSigner)` |
| `0x68e84423772dadc3e4047f8b5bd221ddb02dc67796e7852533fd976947d86c51` | `GatewayUpdated(address _oldGateway, address _newGateway)` |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` |

> The **`Intent` struct must use the V6/V2 layout** (`amountOutMin`, no `maxFee`) or `IntentAdded`/`IntentFilled` topic0 won't match. The older V1 layout (with `uint24 maxFee`) yields **different, wrong** hashes (`IntentAdded` V1 would be `0xefe68281…`, which is NOT what the live contract emits).

### 1.2 FeeAdapterV2 — the user entrypoint (separate emitter)

| topic0 | Event |
|--------|-------|
| `0x4cc03dfa265ccd4670a5059498b2551525947958b26b5e70f6a6dc62a950fd4e` | `IntentWithFeesAdded(bytes32 indexed _intentId, bytes32 indexed _initiator, uint256 _tokenFee, uint256 _nativeFee)` — **the user-level "bridge initiated" event.** *(verified live, Base)* |
| `0xc5929cfdbbc98a41855839bee1396d17ee4a149e40d5c324b6f4332655f5cffd` | `OrderCreated(bytes32 indexed _orderId, bytes32 indexed _initiator, bytes32[] _intentIds, uint256 _tokenFee, uint256 _nativeFee)` — multi-intent order. |
| `0xaaebcf1bfa00580e41d966056b48521fa9f202645c86d4ddf28113e617c1b1d3` | `FeeRecipientUpdated(address indexed _updated, address indexed _previous)` |
| `0x76bd52e686622d2685524f18ca827265a39b781115ecfee7e344cec952442040` | `FeeSignerUpdated(address indexed _updated, address indexed _previous)` |

A user `newIntent` through the FeeAdapter emits **both** `IntentWithFeesAdded` (FeeAdapter) **and** `IntentAdded` (Spoke) in the same tx, sharing `_intentId`. Disambiguate by emitter; correlate on `_intentId`.

### 1.3 Shared proxy / upgrade constants

| topic0 / value | Meaning |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address implementation)` — **watch on Spoke/Gateway proxies** for impl rotations. |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` — OZ `Initializable`. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)`. |
| `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` | EIP-1967 **impl slot** (set on Spoke/Gateway). |
| `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` | EIP-1967 **admin slot** — **empty** on every Everclear proxy (UUPS). |

### 1.4 EverclearHub / HubGateway — clearing chain (Hyperlane domain 25327, **NOT among the 7**)

Computed from `IHubStorage.sol`. Recorded for completeness — these fire only on the Everclear L2, not on any requested chain. Hub address `0xa05A3380889115bf313f1Db9d5f335157Be4D816`, HubGateway `0xEFfAB7cCEBF63FbEFB4884964b12259d4374FaAa` (per docs; not on the seven).

| topic0 | Event |
|--------|-------|
| `0x2f2b163096bbf520e35d11c271a243546f1c1f37555d78c73fbe39ea2346d8a2` | `DepositEnqueued(uint48 indexed _epoch, uint32 indexed _domain, bytes32 indexed _tickerHash, bytes32 _intentId, uint256 _amount)` |
| `0xffe546d643c538f757b569f62e6a9522d63cc8e5ae9feb5ad9794796b6b20c78` | `DepositProcessed(uint48 indexed _epoch, uint32 indexed _domain, bytes32 indexed _tickerHash, bytes32 _intentId, uint256 _amountAndRewards)` |
| `0x81d2714b9bffefcf35121124a611a0914aff753af40903688b6ee930b4833398` | `InvoiceEnqueued(bytes32 indexed _intentId, bytes32 indexed _tickerHash, uint48 indexed _entryEpoch, uint256 _amount, bytes32 _owner)` |
| `0x49194ff94c3ef38c05285a812fd577edd49c55d9f0cf4d944568a80ff92a0516` | `SettlementEnqueued(bytes32 indexed _intentId, uint32 indexed _domain, uint48 indexed _entryEpoch, bytes32 _asset, uint256 _amount, bool _updateVirtualBalance, bytes32 _owner)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All selectors below were **matched PRESENT against the live deployed bytecode** (Spoke impl `0x1b97e14a…` on ETH; FeeAdapter `0xd0185bfb…`) on 2026-06-09 unless noted.

### 2.1 EverclearSpoke (V6) — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8249eb15` | `newIntent(uint32[] destinations, address receiver, address inputAsset, address outputAsset, uint256 amount, uint256 amountOutMin, uint48 ttl, bytes data)` | Direct intent creation. **PRESENT.** (The `bytes32`-receiver overload `0x00c58a2c` is NOT in this impl.) |
| `0x0ed6c47d` | `fillIntent(Intent _intent, uint256 _amountOut, bytes32 _receiver, uint32[] _destinations, bytes _signature, bool _pullFunds)` | Solver fill (destination). **PRESENT.** Emits `IntentFilled`. |
| `0xc9bd6a97` | `batchFillIntent(Intent[] _intents, uint256[] _amountOut, bytes32[] _receivers, uint32[][] _destinations, bytes _signature, bool _pullFunds)` | **PRESENT.** |
| `0xafa6fbd5` | `processIntentQueue(Intent[] _intents, uint256 _dynamicGasLimit)` | Batch origin→hub message. **PRESENT.** |
| `0x61b03cb7` | `processFillQueue(uint32 _amount, uint256 _dynamicGasLimit)` | Batch fill→hub message. **PRESENT.** |
| `0x47e7ef24` | `deposit(address _asset, uint256 _amount)` | Solver liquidity in. **PRESENT.** Emits `Deposited`. |
| `0xf3fef3a3` | `withdraw(address _asset, uint256 _amount)` | Solver/user liquidity out. **PRESENT.** Emits `Withdrawn`. |
| `0x17a297df` | `executeIntentCalldata(Intent _intent)` | Replays an intent's external call. **PRESENT.** |
| `0x0144a661` | `updateFeeAdapter(address)` | Owner-only. **PRESENT.** Emits `FeeAdapterUpdated`. |
| `0x92b4a6be` | `updateFillSigner(address)` | Owner-only. **PRESENT.** Emits `FillSignerUpdated`. |
| `0xc0346b20` | `updateGateway(address)` | Owner-only. **PRESENT.** |
| `0x8456cb59` | `pause()` / `0x3f4ba83a` `unpause()` | **PRESENT.** |
| `0x4f1ef286` | `upgradeToAndCall(address newImpl, bytes data)` | UUPS upgrade. **PRESENT.** Emits `Upgraded`. |

### 2.2 FeeAdapterV2 — user entrypoint (all PRESENT in `0xd0185bfb…`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xceb6341c` | `newIntent(uint32[] destinations, address receiver, address inputAsset, address outputAsset, uint256 amount, uint256 amountOutMin, uint48 ttl, bytes data, (uint256,uint256,bytes) feeParams)` | **The main user bridge call.** Emits `IntentWithFeesAdded` + Spoke `IntentAdded`. |
| `0xae9b2bad` | `newIntent(uint32[], bytes32 receiver, address inputAsset, bytes32 outputAsset, uint256, uint256, uint48, bytes, (uint256,uint256,bytes))` | bytes32-receiver variant (non-EVM dest). |
| `0xa7e4d189` | `newIntent(uint32[], address, address, address, uint256, uint256, uint48, bytes, (uint256,uint256,bytes) permit2, (uint256,uint256,bytes) fee)` | Permit2 variant. |
| `0x2e378bbe` | `newOrderSplitEvenly(uint32 numIntents, uint256 fee, uint256 deadline, bytes sig, (uint32[],address,address,address,uint256,uint256,uint48,bytes) params)` | Splits amount into N intents. Emits `OrderCreated`. |
| `0x72aaa187` | `newOrder(uint256 fee, uint256 deadline, bytes sig, (uint32[],address,address,address,uint256,uint256,uint48,bytes)[] params)` | Multi-intent order. Emits `OrderCreated`. |
| `0xf160d369` | `updateFeeRecipient(address)` | Owner-only. Emits `FeeRecipientUpdated`. |
| `0xb0834893` | `updateFeeSigner(address)` | Owner-only. Emits `FeeSignerUpdated`. |

### 2.3 Spoke / FeeAdapter views

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xf37c0a2e` | `EVERCLEAR()` → `uint32` | Spoke — returns hub domain **25327** (`0x62ef`); use to confirm a contract is a Spoke. |
| `0x338c5371` | `GATEWAY()` → `address` | Spoke — the SpokeGateway. |
| `0x8da5cb5b` | `owner()` → `address` | Spoke / FeeAdapter. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. `EVERCLEAR()` on the Spoke = **25327** (hub domain), confirming it is a Spoke.

| Role | Address | Impl (EIP-1967) | One-liner |
|------|---------|-----------------|-----------|
| **EverclearSpoke** (UUPS) | `0xa05A3380889115bf313f1Db9d5f335157Be4D816` | `0x1b97e14ac5cc126692dc6bce22f1c2e5fa6ccaae` | Intent contract; emits §1.1. owner `0xa02a88f0…`. |
| **SpokeGateway** (UUPS) | `0x9ADA72CCbAfe94248aFaDE6B604D1bEAacc899A7` | `0xa80bcfe3ccd475bd5e74671d10610d7010fe740d` | Hyperlane adapter. |
| **FeeAdapterV2** (direct) | `0xd0185bfb8107c5b2336bC73cE3fdd9Bfb504540e` | — (12 779 B) | User entrypoint; emits §1.2. owner `0xa02a88f0…`. |
| Owner (Spoke + FeeAdapter) | `0xa02a88f0bbd47045001bd460ad186c30f9a974d6` | — | Everclear governance Safe on Ethereum. |

## 4. Addresses — shared-vanity chains (Base 8453, BNB 56, Arbitrum 42161, Optimism 10)

On **Base, BNB, Arbitrum and Optimism** the Spoke and Gateway use the **same vanity literals as Ethereum**, and the FeeAdapter is the same on every chain. Only the **per-chain implementation** behind the proxy diverges (each chain is upgraded independently). All verified via `eth_getCode` on each chain's publicnode RPC. Owner of Spoke = `0xf20d5277ad2f301e2f18e2948ff3e72ad0a6dff9` on all four.

| Role | Address (Base/BNB/Arb/OP — identical literal) |
|------|------------------------------------------------|
| **EverclearSpoke** (UUPS) | `0xa05A3380889115bf313f1Db9d5f335157Be4D816` |
| **SpokeGateway** (UUPS) | `0x9ADA72CCbAfe94248aFaDE6B604D1bEAacc899A7` |
| **FeeAdapterV2** (direct) | `0xd0185bfb8107c5b2336bC73cE3fdd9Bfb504540e` |
| Owner (Spoke) | `0xf20d5277ad2f301e2f18e2948ff3e72ad0a6dff9` |

Per-chain live Spoke impls (read from EIP-1967 slot, 2026-06-09): **Base** `0xd0d94282063236a61ea0d61e1b068516be0a8e73` · **BNB** `0xaba33f246fcb6da288519a635a017d715a9c7e01` · **Arbitrum** `0xa29aaafad54c4205ffbd1e778448188211ae17f3` · **Optimism** `0x8c2c5c570ee35ae0dc781599af6886dd759561e9`. Per-chain Gateway impls: Base/Arb/OP/BNB all share `0xe0f010e465f15dcd42098df9b99f1038c11b3056`. **Read the live slot — never hard-code an impl.**

## 5. Addresses — Avalanche C-Chain (chain ID 43114) — divergent vanity

The vanity addresses are **NOT** used here; Everclear deployed at different literals. All verified via `eth_getCode` on `https://avalanche-c-chain-rpc.publicnode.com`. Owner = `0xf20d5277…`.

| Role | Address | Impl |
|------|---------|------|
| **EverclearSpoke** | `0x9aA2Ecad5C77dfcB4f34893993f313ec4a370460` | `0x22558bef6fe216b90e9652a86d427a17b6307c26` |
| **SpokeGateway** | `0x7EB63a646721de65eBa79ffe91c55DCE52b73c12` | `0xc24dc29774fd2c1c0c5fa31325bb9cbc11d8b751` |
| **FeeAdapterV2** | `0xd0185bfb8107c5b2336bC73cE3fdd9Bfb504540e` | — (same literal as everywhere) |

> Everclear **IS on Avalanche** (unlike the legacy Amarok Diamond, which is not). The CLEAR token, however, is **not** on Avalanche.

## 6. Addresses — Polygon PoS (chain ID 137) — divergent vanity

Verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com`. Owner = `0xf20d5277…`.

| Role | Address | Impl |
|------|---------|------|
| **EverclearSpoke** | `0x7189C59e245135696bFd2906b56607755F84F3fD` | `0x8c2149dcd02e7f1692a77c4dcd85e41cda1038c0` |
| **SpokeGateway** | `0x26CFF54f11608Cd3060408690803AB4a43f462f2` | `0x9214f8f690c2740b149a6fd177c8ce64a8f1a7ae` |
| **FeeAdapterV2** | `0xd0185bfb8107c5b2336bC73cE3fdd9Bfb504540e` | — |

## 7. EverclearHub — clearing chain (Hyperlane domain 25327, outside the 7)

| Role | Address | Notes |
|------|---------|-------|
| **EverclearHub** | `0xa05A3380889115bf313f1Db9d5f335157Be4D816` | Same literal as the Spoke vanity — disambiguate by chain. NOT on any of the seven. |
| **HubGateway** | `0xEFfAB7cCEBF63FbEFB4884964b12259d4374FaAa` | Hub-side Hyperlane adapter. |

The Hub is the **netting/clearing brain**; spoke chains never run it. Cross-chain settlement messages flow SpokeGateway↔HubGateway over **Hyperlane**.

---

## 8. Cross-chain summary

| Chain | ID | EverclearSpoke | SpokeGateway | FeeAdapterV2 | Vanity? |
|---|---|---|---|---|---|
| **Ethereum** | 1 | `0xa05A3380…D816` | `0x9ADA72CC…99A7` | `0xd0185bfb…540e` | ✅ shared |
| **Base** | 8453 | `0xa05A3380…D816` | `0x9ADA72CC…99A7` | `0xd0185bfb…540e` | ✅ shared |
| **BNB** | 56 | `0xa05A3380…D816` | `0x9ADA72CC…99A7` | `0xd0185bfb…540e` | ✅ shared |
| **Arbitrum** | 42161 | `0xa05A3380…D816` | `0x9ADA72CC…99A7` | `0xd0185bfb…540e` | ✅ shared |
| **Optimism** | 10 | `0xa05A3380…D816` | `0x9ADA72CC…99A7` | `0xd0185bfb…540e` | ✅ shared |
| **Avalanche** | 43114 | `0x9aA2Ecad…0460` | `0x7EB63a64…3c12` | `0xd0185bfb…540e` | ⚠️ Spoke/GW diverge |
| **Polygon** | 137 | `0x7189C59e…F3fD` | `0x26CFF54f…62f2` | `0xd0185bfb…540e` | ⚠️ Spoke/GW diverge |
| Everclear L2 (Hub) | domain 25327 | — (Hub `0xa05A3380…`) | HubGateway `0xEFfAB7cC…` | — | outside the 7 |

**All seven requested chains run an Everclear Spoke** (contrast Amarok, which skips Avalanche). The **FeeAdapterV2 literal `0xd0185bfb…540e` is identical on all 7** — the single most reliable cross-chain tell. Spoke/Gateway share a vanity on 5 of 7 (Avax + Polygon diverge). Counterparty chains outside the seven that Everclear also clears include the **Everclear L2 hub (25327)** plus **zkSync Era, Linea, Blast, Scroll, Mode, Mantle, Unichain, Ronin, and others** (Hyperlane domains).

---

## 9. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **EverclearSpoke** | **UUPS (ERC-1967)** | ~183 B proxy; EIP-1967 impl slot `0x3608…bbc` set (e.g. ETH `0x1b97e14a…`); **admin slot `0xb531…6103` empty**; impl exposes `upgradeToAndCall`/`proxiableUUID`. | `owner()` (`0xa02a88f0…` ETH; `0xf20d5277…` other chains). Emits `Upgraded`. |
| **SpokeGateway** | **UUPS (ERC-1967)** | ~183 B proxy; impl slot set (ETH `0xa80bcfe3…`); admin slot empty. | `owner()`. |
| **FeeAdapterV2** | **Direct deployment (no proxy)** | ~12 779 B full contract; EIP-1967 impl slot empty; identical bytecode all 7 chains. | `owner()` (immutable logic). |
| **CLEAR token** | EIP-1967 proxy (ETH) | impl slot `0x8d9a1606…`. | token owner. |

**To track Spoke/Gateway upgrades, watch `Upgraded(address)` `0xbc7cd75a…` on the proxy** — the impl differs per chain and rotates. Confirm "FeeAdapter is not a proxy" by an empty impl slot (`0x0`) on its address.

---

## 10. Detection invariants & gotchas

1. **A user bridge = TWO events in one tx, same `_intentId`:** FeeAdapter `IntentWithFeesAdded` (`0x4cc03dfa…`) **and** Spoke `IntentAdded` (`0x80eb6c87…`). Key the user flow on `IntentWithFeesAdded` (it carries the indexed `_initiator` and the fee split); correlate to settlement via `_intentId`.
2. **Use the V6/V2 Intent struct** (`amountOutMin`, NO `maxFee`) for `IntentAdded`/`IntentFilled` topic0 and `newIntent`/`fillIntent` selectors. The V1 layout (`uint24 maxFee`) gives **wrong** hashes — the live contracts emit the V6 ones (matched against live bytecode + logs).
3. **Lifecycle is cross-chain:** `IntentAdded` (origin Spoke) → `IntentFilled` (destination Spoke) → `Settled` (origin or virtual-balance Spoke). The Hub (`Deposit/Invoice/SettlementEnqueued`) sits on the clearing L2 (domain 25327), **not on any of the seven** — you won't see netting events on the requested chains.
4. **`_initiator`/`_receiver` are `bytes32`, not `address`,** in the Intent struct and `IntentWithFeesAdded` (left-padded EVM addresses, or raw non-EVM identifiers). Don't assume 20-byte addresses.
5. **The fill `_solver` (IntentFilled topic2) and the FeeAdapter caller are not the end user.** Attribute the bridge to `_initiator`; the user receives on the destination as `_receiver`.
6. **Vanity collision Hub vs Spoke:** `0xa05A3380…D816` is the **Spoke** on the seven chains and the **Hub** on the clearing L2. Call `EVERCLEAR()` (returns 25327 on a spoke) to confirm. Key on `(chainId, address)`.
7. **Spoke/Gateway vanity holds on 5 of 7;** Avalanche (`0x9aA2Ecad…`) and Polygon (`0x7189C59e…`) diverge. **FeeAdapterV2 (`0xd0185bfb…540e`) is identical on all 7** — the best cross-chain anchor.
8. **Per-chain impls differ and rotate.** Read the EIP-1967 slot live; watch `Upgraded`. Admin slot is always empty (UUPS).
9. **FeeAdapterV2 is NOT a proxy.** Its impl slot is `0x0` by design — that is not a missing proxy.
10. **`Deposited`/`Withdrawn` are solver liquidity, not user bridging.** A user bridge does not emit `Deposited`. Solvers pre-fund the destination Spoke; `IntentFilled` consumes that liquidity.
11. **Hyperlane domain ≠ chainId for most chains, but coincidentally equals chainId for many** (BNB=56, Avax=43114, Arb=42161, OP=10, Polygon=137, Base=8453, ETH=1). The **hub** is domain 25327 with no matching public chainId. Don't conflate with the Connext/Nomad domains used by Amarok ([amarok.md](amarok.md)).

---

## 11. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- EverclearSpoke (V6)
TOPIC_INTENT_ADDED            = '\x80eb6c87e9da127233fe2ecab8adf29403109adc6bec90147df35eeee0745991'
TOPIC_INTENT_FILLED           = '\xe3bc4b05ac625e8c55084d86f8bb9a4c1ff02777dccc7ec0f3b3b7e7468cf383'
TOPIC_SETTLED                 = '\x4190759d37d5cfe7a1a70e06ec7508a05d12fd9cb76f353da1c9e028e5a48dcf'
TOPIC_DEPOSITED               = '\x8752a472e571a816aea92eec8dae9baf628e840f4929fbcc2d155e6233ff68a7'
TOPIC_WITHDRAWN               = '\xd1c19fbcd4551a5edfb66d43d2e337c04837afda3482b42bdf569a8fccdae5fb'
TOPIC_INTENT_QUEUE_PROCESSED  = '\x43a52e9a77f317a192970b363b14ece56df243fe0dd94f459f63029d657efec3'
TOPIC_FILL_QUEUE_PROCESSED    = '\x5e3a5b80dcf8e0fb984fe128ed0db507a86cc0674c4f5980f83b129b2cfdc69e'
TOPIC_EXTERNAL_CALLDATA_EXEC  = '\x72c7d97e6fac52d20092b101af2183fd0bd04b357a936e82537e8974ea2c0eb7'
TOPIC_FEE_ADAPTER_UPDATED     = '\xc1f1475cd1d27fd368e9f8f208d68469a20695129a6bb78e7d1a0f970f602695'
TOPIC_FILL_SIGNER_UPDATED     = '\x34f45330d12e136e35710c0b12bb3d009fb59bf6042d4d9fa611cb7ee4e74ead'
TOPIC_GATEWAY_UPDATED         = '\x68e84423772dadc3e4047f8b5bd221ddb02dc67796e7852533fd976947d86c51'
TOPIC_PAUSED                  = '\x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752'
TOPIC_UNPAUSED                = '\xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933'
-- FeeAdapterV2
TOPIC_INTENT_WITH_FEES_ADDED  = '\x4cc03dfa265ccd4670a5059498b2551525947958b26b5e70f6a6dc62a950fd4e'
TOPIC_ORDER_CREATED           = '\xc5929cfdbbc98a41855839bee1396d17ee4a149e40d5c324b6f4332655f5cffd'
TOPIC_FEE_RECIPIENT_UPDATED   = '\xaaebcf1bfa00580e41d966056b48521fa9f202645c86d4ddf28113e617c1b1d3'
TOPIC_FEE_SIGNER_UPDATED      = '\x76bd52e686622d2685524f18ca827265a39b781115ecfee7e344cec952442040'
-- Hub (clearing L2, domain 25327 — NOT on the 7)
TOPIC_DEPOSIT_ENQUEUED        = '\x2f2b163096bbf520e35d11c271a243546f1c1f37555d78c73fbe39ea2346d8a2'
TOPIC_DEPOSIT_PROCESSED       = '\xffe546d643c538f757b569f62e6a9522d63cc8e5ae9feb5ad9794796b6b20c78'
TOPIC_INVOICE_ENQUEUED        = '\x81d2714b9bffefcf35121124a611a0914aff753af40903688b6ee930b4833398'
TOPIC_SETTLEMENT_ENQUEUED     = '\x49194ff94c3ef38c05285a812fd577edd49c55d9f0cf4d944568a80ff92a0516'
-- Proxy/upgrade
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_INITIALIZED             = '\xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2'
TOPIC_OWNERSHIP_TRANSFERRED   = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'

-- ===== Selectors =====
-- Spoke (V6)
SEL_NEW_INTENT                = '\x8249eb15'
SEL_FILL_INTENT               = '\x0ed6c47d'
SEL_BATCH_FILL_INTENT         = '\xc9bd6a97'
SEL_PROCESS_INTENT_QUEUE      = '\xafa6fbd5'
SEL_PROCESS_FILL_QUEUE        = '\x61b03cb7'
SEL_DEPOSIT                   = '\x47e7ef24'
SEL_WITHDRAW                  = '\xf3fef3a3'
SEL_EXECUTE_INTENT_CALLDATA   = '\x17a297df'
SEL_UPDATE_FEE_ADAPTER        = '\x0144a661'
SEL_UPDATE_FILL_SIGNER        = '\x92b4a6be'
SEL_UPGRADE_TO_AND_CALL       = '\x4f1ef286'
-- FeeAdapterV2
SEL_FEE_NEW_INTENT_ADDR       = '\xceb6341c'
SEL_FEE_NEW_INTENT_BYTES32    = '\xae9b2bad'
SEL_FEE_NEW_INTENT_PERMIT2    = '\xa7e4d189'
SEL_FEE_NEW_ORDER_SPLIT       = '\x2e378bbe'
SEL_FEE_NEW_ORDER             = '\x72aaa187'
-- views
SEL_EVERCLEAR                 = '\xf37c0a2e'
SEL_GATEWAY                   = '\x338c5371'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT            = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses — shared vanity (ETH/Base/BNB/Arb/OP) =====
SHARED_SPOKE                  = '\xa05a3380889115bf313f1db9d5f335157be4d816'
SHARED_GATEWAY                = '\x9ada72ccbafe94248afade6b604d1beaacc899a7'
FEE_ADAPTER_ALL_7             = '\xd0185bfb8107c5b2336bc73ce3fdd9bfb504540e'  -- identical on all 7 chains
-- Avalanche (divergent)
AVAX_SPOKE                    = '\x9aa2ecad5c77dfcb4f34893993f313ec4a370460'
AVAX_GATEWAY                  = '\x7eb63a646721de65eba79ffe91c55dce52b73c12'
-- Polygon (divergent)
POLY_SPOKE                    = '\x7189c59e245135696bfd2906b56607755f84f3fd'
POLY_GATEWAY                  = '\x26cff54f11608cd3060408690803ab4a43f462f2'
-- Hub (clearing L2, NOT on the 7)
HUB                           = '\xa05a3380889115bf313f1db9d5f335157be4d816'
HUB_GATEWAY                   = '\xeffab7ccebf63fbefb4884964b12259d4374faaa'
-- Owners
ETH_OWNER                     = '\xa02a88f0bbd47045001bd460ad186c30f9a974d6'
SPOKE_OWNER_NON_ETH           = '\xf20d5277ad2f301e2f18e2948ff3e72ad0a6dff9'
-- ETH live impls (read live; rotate per chain)
ETH_SPOKE_IMPL                = '\x1b97e14ac5cc126692dc6bce22f1c2e5fa6ccaae'
ETH_GATEWAY_IMPL              = '\xa80bcfe3ccd475bd5e74671d10610d7010fe740d'
```

---

## 12. Verification & sources

How constants were verified (2026-06-09):
- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from `everclearorg/monorepo` (`dev`) interfaces — `IEverclearV2.sol` (Intent struct), `IEverclearSpokeV6.sol`, `ISpokeStorageV6.sol`, `IFeeAdapterV2.sol`, `IHubStorage.sol`. **`IntentAdded` (`0x80eb6c87…`) and `IntentWithFeesAdded` (`0x4cc03dfa…`) cross-checked against live `eth_getLogs`** on the Base Spoke/FeeAdapter at block 44 385 499 (one of each). **Every Spoke and FeeAdapter selector in §2 was matched PRESENT against the live deployed bytecode** (Spoke impl `0x1b97e14a…`, FeeAdapter `0xd0185bfb…`) via PUSH4 scan — this is how the deployed version was pinned to V6 (the V1 `newIntent`/`fillIntent`/`IntentAdded` variants are absent on chain).
- **Addresses:** parsed from the Everclear mainnet contracts registry / docs, existence-checked via `eth_getCode` on each chain's publicnode RPC. Spoke/Gateway/FeeAdapter confirmed on all 7 (Spoke/Gateway vanity on 5, divergent on Avax + Polygon; FeeAdapter identical literal on all 7). `EVERCLEAR()` read live = 25327 confirms Spoke role; `owner()` read live per chain.
- **Proxy impls:** read from the EIP-1967 impl slot live per chain (Spoke + Gateway populated, admin slot empty → UUPS); FeeAdapter impl slot empty → direct deployment.
- **Chain/domain coverage:** Hyperlane domain IDs from the Everclear docs (hub = 25327). Hub/HubGateway on the clearing L2 noted as outside the seven.

Authoritative sources:
- Canonical repo: [`everclearorg/monorepo`](https://github.com/everclearorg/monorepo) — `packages/contracts/src/{contracts,interfaces}` (`EverclearSpoke`, `FeeAdapter`, `SpokeGateway`, `EverclearHub`, `IEverclearV2`).
- Docs: [Everclear mainnet contracts](https://docs.everclear.org/resources/contracts/mainnet) · [Everclear fundamentals](https://docs.everclear.org/developers/fundamentals).
- Explorers: [Basescan FeeAdapterV2](https://basescan.org/address/0xd0185bfb8107c5b2336bc73ce3fdd9bfb504540e) · [Etherscan EverclearSpoke](https://etherscan.io/address/0xa05a3380889115bf313f1db9d5f335157be4d816).
