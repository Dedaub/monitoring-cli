# zkBridge (Polyhedra) Native Messaging — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon)

**Status:** verified against live RPC on Ethereum, Base, BNB Smart Chain, Avalanche C-Chain, Arbitrum One, Optimism, and Polygon PoS, plus Etherscan-verified implementation source, on 2026-06-09.
**Scope:** the **native zkBridge cross-chain messaging stack** — the `ZKBridge` entrypoint (`send`/`validateTransactionProof`), the per-source-chain `*BlockUpdater` zk light clients, and the shared `MptVerifier`. Topics and selectors are **chain-agnostic** (`keccak256` of the canonical signature); addresses are **network-specific**. The separate LayerZero zkLightClient integration (the V1 Oracle + V2 DVN that Polyhedra runs as a verification provider inside LayerZero) is documented in [lightclient.md](./lightclient.md). There is **no separate Polyhedra-canonical token/NFT bridge contract** — token and NFT transfers are *application contracts written by integrators* on top of the messaging entrypoint (they call `send` and implement `zkReceive`); see §9.

zkBridge's native messaging layer is a **trustless message bus**: a sender calls `ZKBridge.send(dstChainId, dstAddress, payload)` on the source chain (emitting `MessagePublished`); a relayer later calls `ZKBridge.validateTransactionProof(srcChainId, srcBlockHash, logIndex, mptProof)` on the destination chain, which (1) checks `srcBlockHash` against the on-chain **BlockUpdater** zk light client for that source chain, (2) verifies the Merkle-Patricia receipt proof via the **MptVerifier**, then (3) delivers the payload to `dstAddress.zkReceive(...)` and emits `ExecutedMessage`. The receiving user-contract implements `IZKBridgeReceiver.zkReceive` — that function lives on the *application*, not on the entrypoint.

**Deployment shape (verified on-chain 2026-06-09):**
- The `ZKBridge` entrypoint is a **single CREATE2-style deterministic address `0xa8a4547Be2eCe6Dde2Dd91b4A5adFe4A043b21C7` on all 7 chains**, an **EIP-1967 Transparent proxy** whose implementation `0x6eab43ced4041ce6b4048844b3b2c811bffad43b` is **byte-identical on all 7 chains**, behind a **shared ProxyAdmin `0xe16d201ca134345601631d327a971a3741646b0d`** (same literal every chain).
- Each chain's entrypoint stores **per-source-chain `BlockUpdater` and `MptVerifier` addresses** in mappings keyed by the **zkBridge-internal chainId** (NOT the EVM chainId — see §0). The same entrypoint address therefore points at *different* light-client contracts on each chain.
- `BlockUpdater` contracts are per-source-chain (e.g. `BscBlockUpdater`, polygon/`HeimdallBlockUpdater`, BeaconBlockUpdater for Ethereum); some are Transparent proxies (same shared ProxyAdmin), some are immutable direct deploys. `MptVerifier` is an immutable `pure` helper.

---

## 0. zkBridge-internal chainId map (the number used in events/selectors, NOT the EVM chainId)

`ZKBridge.chainId()` returns the **zkBridge-internal id**, and every event's `dstChainId`/`srcChainId` and every `blockUpdaters(uint16)` / `mptVerifiers(uint16)` mapping key uses these internal ids. Verified live via `eth_call chainId()` on each chain 2026-06-09:

| Chain | EVM chainId | zkBridge-internal id (verified `chainId()`) |
|---|---|---|
| Ethereum | 1 | **2** |
| BNB Smart Chain | 56 | **3** |
| Polygon PoS | 137 | **4** |
| Avalanche C-Chain | 43114 | **5** |
| Optimism | 10 | **7** |
| Arbitrum One | 42161 | **8** |
| Base | 8453 | **22** |

> Indexing trap: a `MessagePublished` with `dstChainId = 3` means **BNB**, not "EVM chain 3". Always translate through this table; never feed the raw 16-bit id to an EVM-chainId lookup. (Testnet docs additionally list Sepolia=119, BSC-testnet=103, EXPchain=131 — those are testnet-only and out of scope here.)

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 ZKBridge entrypoint (`0xa8a4547…`, same address all chains)

| topic0 | Event |
|--------|-------|
| `0xb8abfd5c33667c7440a4fc1153ae39a24833dbe44f7eb19cbe5cd5f2583e4940` | `MessagePublished(address indexed sender, uint16 indexed dstChainId, uint64 indexed sequence, address dstAddress, bytes payload)` — fired by `send()` on the **source** chain. *(verified live on Ethereum)* |
| `0x4a008ac830958ba6fe8a6e667e2ab53a530eb6cdf93e55b27fc42d7a54cf25b7` | `ExecutedMessage(address indexed sender, uint16 indexed srcChainId, uint64 indexed sequence, address dstAddress, bytes payload)` — fired by `validateTransactionProof()` on the **destination** chain after proof verification + delivery. *(verified live on Ethereum)* |
| `0xf40b9ca28516abde647ef8ed0e7b155e16347eb4d8dd6eb29989ed2c0c3d27e8` | `ClaimFee(address operator, uint256 amount)` |
| `0x7655e822a6d41e0420140c77742da5d6b5cbaa3906c73dc1440e9ff4b1b8302a` | `NewBlockUpdater(uint16 chainId, address oldBlockUpdater, address newBlockUpdater)` — admin re-points the light client for a source chain. |
| `0x8f3fd8462a96af532c9c18ddf370560d1bf475fec6bcc7d8e7761b794a31e8da` | `NewMptVerifier(uint16 chainId, address oldMptVerifier, address newMptVerifier)` |
| `0x3d9a6222528a5f37fccacff9e85c30a4b687e85338f74940f018b70c4f7461d7` | `NewFee(uint16 chainId, uint256 fee)` |
| `0x772ddcfc9a0f3b1401c0f60000a81999005d9d593b71bb67707c5f326eb7c94d` | `NewFeeManager(address feeManager)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` |

> The `NewBlockUpdater`/`NewMptVerifier`/`NewFee` event names are reconstructed from the verified ABI's setter pattern; `NewBlockUpdater` topic0 is unverified against a live log (rare admin event). See §11. `MessagePublished`/`ExecutedMessage` are the workhorses and are live-confirmed.

### 1.2 Proxy admin events (on the `0xa8a4547…` proxy itself — OpenZeppelin Transparent proxy)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **watch this to catch impl rotation of the entrypoint.** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |
| `0x1cf3b03a6cf19fa2baba4df148e9dcabedea7f8a5c07840e207e5c089be95d3e` | `BeaconUpgraded(address indexed beacon)` (present in the OZ proxy ABI; never fired — these are non-beacon proxies) |

### 1.3 BlockUpdater (per-source-chain zk light client, e.g. `BscBlockUpdater`)

| topic0 | Event |
|--------|-------|
| `0xa3fa2e60f4d1c7f6bd60da77a4be0625773dfb6b22c54fe77e725d03e49cdf2e` | `ImportBlock(uint256 indexed identifier, bytes32 blockHash, bytes32 receiptHash)` — a source-chain block header was zk-verified and stored. *(verified live on Ethereum, on the BSC-source BlockUpdater `0x11732663…`)* |
| `0xb20f83d7fca2253dd4a37d0ee1922398cbbecf5a89899514947161ae70c0037f` | `ImportValidator(uint256 indexed epoch, uint256 indexed blockNumber, bytes32 blockHash, bytes32 receiptHash)` — validator-set/epoch import (PoS source chains). |
| `0x5ab2642364d92dafb2be757706f004ccf8325cca566bc2d0742133d316a5eaed` | `ModBlockConfirmation(uint256 oldBlockConfirmation, uint256 newBlockConfirmation)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` |

`ImportBlock`/`ImportValidator` event field layout is stable across the `*BlockUpdater` family (Bsc/Polygon/Beacon/etc.) — the zk verification circuit differs per source chain but the storage/event ABI is shared.

### 1.4 MptVerifier (`0x8022ceaa…` on Ethereum)

**No events.** `MptVerifier.validateMPT(bytes)` is a `pure` helper that returns a decoded receipt; it emits nothing. Nothing to index here — it appears only as an internal call inside `validateTransactionProof` txs.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 ZKBridge entrypoint — all verified **present** in the live impl bytecode `0x6eab43…` on 2026-06-09

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb1d995dd` | `send(uint16 dstChainId, address dstAddress, bytes payload)` → `uint64 nonce` | `payable`. Emits `MessagePublished`. The **source-side entrypoint**. |
| `0x207bae8a` | `estimateFee(uint16 dstChainId)` → `uint256` | View; quote in source-native gas for `send`. |
| `0x4f64ca19` | `validateTransactionProof(uint16 srcChainId, bytes32 srcBlockHash, uint256 logIndex, bytes mptProof)` | The **destination-side delivery** call. Checks BlockUpdater + MptVerifier, calls `dstAddress.zkReceive`, emits `ExecutedMessage`. |
| `0x72ee3f69` | `blockUpdaters(uint16 srcChainId)` → `address` | Public mapping getter — the light client for a source chain. |
| `0xc314cdae` | `mptVerifiers(uint16 srcChainId)` → `address` | Public mapping getter — the receipt verifier for a source chain. |
| `0x9a8a0592` | `chainId()` → `uint16` | The **zkBridge-internal** id of this chain (§0). |
| `0x813d31c9` | `setBlockUpdater(uint16 chainId, address blockUpdater)` | owner-only. Emits `NewBlockUpdater`. |
| `0x7cf5744f` | `setMptVerifier(uint16 chainId, address mptVerifier)` | owner-only. Emits `NewMptVerifier`. |
| `0xc7f0da13` | `setFee(uint16 chainId, uint256 fee)` | owner/feeManager. Emits `NewFee`. |
| `0x5c46ff99` | `claimFees(address payable to, uint256 amount)` | owner-only. Emits `ClaimFee`. |
| `0x13750946` | `initialize(uint16 chainId)` | one-shot proxy init. |
| `0x8da5cb5b` | `owner()` → `address` | Per-chain owner (a multisig, see §3/§7). |

> The fee-manager getter is **not** `feeManager()` (that selector reverts `ZKBridge:unsupported` on-chain) and is **not** `feeManagers(address)` (`0xef897f07` absent from bytecode). The exact getter name is **unverified** — read fee config via the `NewFee`/`NewFeeManager` events or `setFee`/`setFeeManager` calls instead. See §11.

### 2.2 Proxy / upgrade surface (OZ Transparent proxy on `0xa8a4547…`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3659cfe6` | `upgradeTo(address newImplementation)` | admin-only (via ProxyAdmin). Emits `Upgraded`. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | `payable`, admin-only. Emits `Upgraded`. |
| `0x8f283970` | `changeAdmin(address newAdmin)` | Emits `AdminChanged`. |
| `0xf851a440` | `admin()` → `address` | admin-only. |
| `0x5c60da1b` | `implementation()` → `address` | admin-only (Transparent proxy hides it from non-admin). |

### 2.3 BlockUpdater (e.g. `BscBlockUpdater`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x36fbafad` | `importBlock(bytes proof)` | Submits a zk-verified source block header. Emits `ImportBlock`/`ImportValidator`. |
| `0xdc3588ea` | `checkBlock(bytes32 blockHash, bytes32 receiptHash)` → `bool` | View used by `validateTransactionProof`. |
| `0x254252af` | `checkBlockConfirmation(bytes32 blockHash, bytes32 receiptHash)` → `(bool, uint256)` | |
| `0x9d0167e7` | `setBlockConfirmation(uint256 minBlockConfirmation)` | owner-only. Emits `ModBlockConfirmation`. |
| `0x76671808` | `currentEpoch()` → `uint256` | |
| `0xa9ef31de` | `minBlockConfirmation()` → `uint256` | |

### 2.4 MptVerifier

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0afb22da` | `validateMPT(bytes proof)` → `(bytes32 receiptHash, bytes logs)` | `pure`. Decodes/validates a Merkle-Patricia receipt proof. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1, zkBridge-internal id 2)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Proxy impls read live from the EIP-1967 implementation slot.

| Role | Address | One-liner |
|------|---------|-----------|
| **ZKBridge entrypoint** (proxy) | `0xa8a4547Be2eCe6Dde2Dd91b4A5adFe4A043b21C7` | `send`/`validateTransactionProof`; emits §1.1. Impl `0x6eab43ced4041ce6b4048844b3b2c811bffad43b`. |
| **ProxyAdmin** (shared, all chains) | `0xe16d201ca134345601631d327a971a3741646b0d` | EIP-1967 admin of the entrypoint + the proxied BlockUpdaters (1683 B contract). |
| Entrypoint **owner** (per-chain) | `0xa926f089e07a9fd7a1a9438b1bb801963807a6d7` | `owner()` on ETH — a contract (multisig, 171 B). |
| **MptVerifier** | `0x8022ceaa2771fdc188a6f3c783e7207f53b121d2` | Immutable `pure` receipt-proof decoder (3921 B, no proxy, no events). |
| BlockUpdater — src **BSC (id 3)** | `0x11732663d735db99569bd9fd19dc853fbea48696` | `BscBlockUpdater`; Transparent proxy, impl `0xbe0b942df3e28cc0373f39be729a6a83f0d7e0c6`. *(`ImportBlock` verified live)* |
| BlockUpdater — src **Polygon (id 4)** | `0xcc069839654d10ebe29229a9f44bbb0a8056b28d` | Polygon light client; Transparent proxy, impl `0x75d32e80c32012da98019cb76954fc37fda29576`. |
| BlockUpdater — src **Optimism (id 7)** | `0x9d5a7f0ce68bba0ea9a720ad5b4a3a0e2513c0a0` | Direct (immutable) deploy — impl slot `0x0`. |
| BlockUpdater — src **Arbitrum (id 8)** | `0x29aea16936502b41af199a975a74779d5151c4c3` | Per-source light client. |
| BlockUpdater — src **Base (id 22)** | `0xb5a6da0c0334a83fee0f8cbf8b0dd1d0dfe95099` | Base light client (1743 B contract). |
| BlockUpdater — src **id 14** | `0x5833ce34eade14673bae79dbcfd0c4c55b0bf953` | (counterparty chain outside the 7 — see §9). |
| BlockUpdater — src **id 20** | `0xbe3872e260ee81385a2a692750e21f8e2966ab3e` | (counterparty chain outside the 7 — see §9). |

Each BlockUpdater above is read from `blockUpdaters(srcId)` on the Ethereum entrypoint; all share `mptVerifiers(srcId) = 0x8022ceaa…`. **Ethereum receives from BSC/Polygon/OP/Arb/Base (+two non-target chains).** The **Base-source (id 22)** light client is live at `0xb5a6da0c0334a83fee0f8cbf8b0dd1d0dfe95099` (`blockUpdaters(22)`, a 1743 B contract); **no Avalanche-source (id 5)** BlockUpdater is configured (`blockUpdaters(5)` = `0x0`). Routes rotate — recheck `blockUpdaters(srcId)` rather than assuming a fixed source set.

---

## 4. Addresses — the other six chains (entrypoint + ProxyAdmin shared; light-clients per-chain)

On **every** target chain the entrypoint and ProxyAdmin are the **same literal address with the same entrypoint implementation** (`0x6eab43…`). What differs per chain is the **owner multisig** and the **set of per-source `BlockUpdater`/`MptVerifier` contracts** (read live via `blockUpdaters(srcId)`).

| Chain | EVM id | zk id | ZKBridge entrypoint | Entrypoint impl | Owner (`owner()`) |
|---|---|---|---|---|---|
| Base | 8453 | 22 | `0xa8a4547Be2eCe6Dde2Dd91b4A5adFe4A043b21C7` | `0x6eab43…d43b` | `0xd85dc8cb3145411fe334d5c1698d36562ba18473` |
| BNB Smart Chain | 56 | 3 | `0xa8a4547Be2eCe6Dde2Dd91b4A5adFe4A043b21C7` | `0x6eab43…d43b` | `0xaf7757a1aa3024cf19308343cebbbc06f8cc8338` |
| Avalanche C-Chain | 43114 | 5 | `0xa8a4547Be2eCe6Dde2Dd91b4A5adFe4A043b21C7` | `0x6eab43…d43b` | `0xaf7757a1aa3024cf19308343cebbbc06f8cc8338` |
| Arbitrum One | 42161 | 8 | `0xa8a4547Be2eCe6Dde2Dd91b4A5adFe4A043b21C7` | `0x6eab43…d43b` | `0xaf7757a1aa3024cf19308343cebbbc06f8cc8338` |
| Optimism | 10 | 7 | `0xa8a4547Be2eCe6Dde2Dd91b4A5adFe4A043b21C7` | `0x6eab43…d43b` | `0xd85dc8cb3145411fe334d5c1698d36562ba18473` |
| Polygon PoS | 137 | 4 | `0xa8a4547Be2eCe6Dde2Dd91b4A5adFe4A043b21C7` | `0x6eab43…d43b` | `0xaf7757a1aa3024cf19308343cebbbc06f8cc8338` |

ProxyAdmin `0xe16d201ca134345601631d327a971a3741646b0d` is the EIP-1967 admin on **all six** (verified). Two distinct owner multisigs are in use: `0xaf7757a1…` (BSC/Avax/Arb/Polygon) and `0xd85dc8cb…` (Base/OP); Ethereum uses a third (`0xa926f089…`). To enumerate a chain's light clients, call `blockUpdaters(srcId)`/`mptVerifiers(srcId)` for each source id in §0 against the entrypoint on that chain — these are network-specific and not listed exhaustively here (they rotate as routes are added).

**The entrypoint is present and active on all 7 target chains** — no target chain returns `0x`.

---

## 5. Cross-chain summary

| Chain | EVM id | zk id | ZKBridge entrypoint | Entrypoint impl | ProxyAdmin | Per-chain BlockUpdaters/MptVerifier |
|---|---|---|---|---|---|---|
| Ethereum | 1 | 2 | `0xa8a4547…21C7` ✓ | `0x6eab43…d43b` | `0xe16d201c…` | yes (per-source) |
| Base | 8453 | 22 | `0xa8a4547…21C7` ✓ | `0x6eab43…d43b` | `0xe16d201c…` | yes |
| BNB | 56 | 3 | `0xa8a4547…21C7` ✓ | `0x6eab43…d43b` | `0xe16d201c…` | yes |
| Avalanche | 43114 | 5 | `0xa8a4547…21C7` ✓ | `0x6eab43…d43b` | `0xe16d201c…` | yes |
| Arbitrum | 42161 | 8 | `0xa8a4547…21C7` ✓ | `0x6eab43…d43b` | `0xe16d201c…` | yes |
| Optimism | 10 | 7 | `0xa8a4547…21C7` ✓ | `0x6eab43…d43b` | `0xe16d201c…` | yes |
| Polygon | 137 | 4 | `0xa8a4547…21C7` ✓ | `0x6eab43…d43b` | `0xe16d201c…` | yes |

**Vanity/determinism tells:** the entrypoint `0xa8a4547…21C7`, its impl `0x6eab43…d43b`, and the ProxyAdmin `0xe16d201c…` are **identical literals on all 7 chains** (deterministic deploy via the shared ProxyAdmin/deployer). The light-client (`*BlockUpdater`) addresses are **not** shared — they are per `(chain, source-chain)` and must be resolved through the entrypoint mappings.

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **ZKBridge entrypoint** (`0xa8a4547…`) | **EIP-1967 Transparent** (`OptimizedTransparentUpgradeableProxy`) | EIP-1967 impl slot = `0x6eab43…d43b`; admin slot = `0xe16d201c…` (both populated, all 7 chains). | ProxyAdmin `0xe16d201ca134345601631d327a971a3741646b0d`, itself `owner`-gated by the per-chain multisig. Watch `Upgraded` topic0 `0xbc7cd75a…`. |
| **BlockUpdater** (BSC-src `0x11732663…`, Polygon-src `0xcc069839…`) | **EIP-1967 Transparent** | impl slot populated (e.g. `0xbe0b942d…`, `0x75d32e80…`); admin slot = shared ProxyAdmin. | ProxyAdmin `0xe16d201c…`. |
| **BlockUpdater** (OP-src `0x9d5a7f0c…`) | **Immutable (no proxy)** | EIP-1967 impl + admin slots both `0x0`. | none — redeploy + `setBlockUpdater` to rotate. |
| **MptVerifier** (`0x8022ceaa…`) | **Immutable (no proxy)** | impl + admin slots `0x0`; `pure` contract. | none — replaced via `setMptVerifier`. |

EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. Read with `eth_getStorageAt(addr, slot)`. The entrypoint impl `0x6eab43…` is the **same on all 7 chains** (CREATE2 determinism); BlockUpdater impls vary per source chain. No Beacon (slot `0xa3f0ad74…`) and no Diamond — every proxy here is a single-impl Transparent proxy.

---

## 7. Detection invariants & gotchas

1. **`dstChainId`/`srcChainId` in events are zkBridge-internal ids, not EVM chainIds.** Translate via §0 (ETH=2, BSC=3, Polygon=4, Avax=5, OP=7, Arb=8, Base=22). A `MessagePublished(dstChainId=3)` is destined for **BNB**.
2. **`send` and `validateTransactionProof` fire on *different* chains.** A complete message = `MessagePublished` on the **source** chain (keyed by `(sender, dstChainId, sequence)`) → `ExecutedMessage` on the **destination** chain (keyed by `(sender, srcChainId, sequence)`). Join the two legs on `(sender, sequence)` plus the translated chain pair. `sequence` (the third indexed topic) is the per-`(sender)` nonce.
3. **The `sender` in the events is the application contract, not the EOA.** `MessagePublished.sender` is `msg.sender` of `send` — the integrator's app (token/NFT bridge, etc.), not the end user. Attribute by decoding the app's own payload, not by `sender`.
4. **`dstAddress` and the payload are in the non-indexed data**, not topics — you must ABI-decode the log data to get the destination app and message body.
5. **There is no `zkReceive` event and no `zkReceive` function on the entrypoint.** Delivery confirmation is the `ExecutedMessage` event; `zkReceive` is a callback the *receiving application* implements. Do not scan the entrypoint for a `zkReceive` selector.
6. **Detect message delivery by the `ExecutedMessage` event, not by a function selector** — `validateTransactionProof` is relayer-driven and `tx.to` is the entrypoint, but the meaningful key is the event's `(srcChainId, sequence, sender)`.
7. **One entrypoint address, many light clients.** The same `0xa8a4547…` proxy resolves a *different* `BlockUpdater`/`MptVerifier` per source chain via `blockUpdaters(srcId)`/`mptVerifiers(srcId)`. Don't assume a single light-client address per chain.
8. **`ImportBlock` on a BlockUpdater is the relay heartbeat** — frequent `ImportBlock`/`ImportValidator` logs mean the route is live; their absence means that source chain isn't currently being relayed into this destination.
9. **Entrypoint impl is shared across all 7 chains; BlockUpdater impls are not.** Reading the entrypoint's EIP-1967 slot gives `0x6eab43…` everywhere; reading a BlockUpdater's slot gives a per-source impl (and `0x0` for the immutable ones).
10. **Owner ≠ ProxyAdmin.** The ProxyAdmin (`0xe16d201c…`, shared all chains) controls *upgrades*; the per-chain `owner()` multisig controls *config* (`setBlockUpdater`/`setMptVerifier`/`setFee`/`claimFees`). Monitor both: `Upgraded`/`AdminChanged` (proxy) and `NewBlockUpdater`/`NewMptVerifier`/`OwnershipTransferred` (entrypoint).
11. **No canonical Polyhedra token/NFT bridge contract.** Token zkBridge / NFT transfers are integrator-deployed apps on top of `send`/`zkReceive`; there is no single "zkBridge token vault" address to index (§9). The Polyhedra Network ERC-20 token (`0xc71b5f631354be6853efe9c3ab6b9590f8302e81`, on-chain `symbol()` = `ZK`, `name()` = `Polyhedra Network`; `ZKJ` is the older CEX ticker) is a *governance token*, unrelated to the bridge message path.
12. **Fee config getter name is unverified** (the obvious `feeManager()` reverts). Track fees via `NewFee`/`NewFeeManager`/`ClaimFee` events rather than a view call.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- ZKBridge entrypoint
TOPIC_MESSAGE_PUBLISHED       = '\xb8abfd5c33667c7440a4fc1153ae39a24833dbe44f7eb19cbe5cd5f2583e4940'
TOPIC_EXECUTED_MESSAGE        = '\x4a008ac830958ba6fe8a6e667e2ab53a530eb6cdf93e55b27fc42d7a54cf25b7'
TOPIC_CLAIM_FEE               = '\xf40b9ca28516abde647ef8ed0e7b155e16347eb4d8dd6eb29989ed2c0c3d27e8'
TOPIC_NEW_BLOCK_UPDATER       = '\x7655e822a6d41e0420140c77742da5d6b5cbaa3906c73dc1440e9ff4b1b8302a'
TOPIC_NEW_MPT_VERIFIER        = '\x8f3fd8462a96af532c9c18ddf370560d1bf475fec6bcc7d8e7761b794a31e8da'
TOPIC_NEW_FEE                 = '\x3d9a6222528a5f37fccacff9e85c30a4b687e85338f74940f018b70c4f7461d7'
TOPIC_NEW_FEE_MANAGER         = '\x772ddcfc9a0f3b1401c0f60000a81999005d9d593b71bb67707c5f326eb7c94d'
TOPIC_OWNERSHIP_TRANSFERRED   = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_INITIALIZED             = '\x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498'
-- Proxy
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED           = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_BEACON_UPGRADED         = '\x1cf3b03a6cf19fa2baba4df148e9dcabedea7f8a5c07840e207e5c089be95d3e'
-- BlockUpdater
TOPIC_IMPORT_BLOCK            = '\xa3fa2e60f4d1c7f6bd60da77a4be0625773dfb6b22c54fe77e725d03e49cdf2e'
TOPIC_IMPORT_VALIDATOR        = '\xb20f83d7fca2253dd4a37d0ee1922398cbbecf5a89899514947161ae70c0037f'
TOPIC_MOD_BLOCK_CONFIRMATION  = '\x5ab2642364d92dafb2be757706f004ccf8325cca566bc2d0742133d316a5eaed'

-- ===== Selectors =====
-- ZKBridge entrypoint
SEL_SEND                      = '\xb1d995dd'
SEL_ESTIMATE_FEE              = '\x207bae8a'
SEL_VALIDATE_TX_PROOF         = '\x4f64ca19'
SEL_BLOCK_UPDATERS            = '\x72ee3f69'
SEL_MPT_VERIFIERS             = '\xc314cdae'
SEL_CHAIN_ID                  = '\x9a8a0592'
SEL_SET_BLOCK_UPDATER         = '\x813d31c9'
SEL_SET_MPT_VERIFIER          = '\x7cf5744f'
SEL_SET_FEE                   = '\xc7f0da13'
SEL_CLAIM_FEES                = '\x5c46ff99'
-- Proxy
SEL_UPGRADE_TO                = '\x3659cfe6'
SEL_UPGRADE_TO_AND_CALL       = '\x4f1ef286'
SEL_CHANGE_ADMIN              = '\x8f283970'
-- BlockUpdater
SEL_IMPORT_BLOCK              = '\x36fbafad'
SEL_CHECK_BLOCK               = '\xdc3588ea'
SEL_SET_BLOCK_CONFIRMATION    = '\x9d0167e7'
-- MptVerifier
SEL_VALIDATE_MPT              = '\x0afb22da'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT            = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses (same literal on all 7 chains) =====
ZKBRIDGE_ENTRYPOINT           = '\xa8a4547be2ece6dde2dd91b4a5adfe4a043b21c7'
ZKBRIDGE_ENTRYPOINT_IMPL      = '\x6eab43ced4041ce6b4048844b3b2c811bffad43b'
ZKBRIDGE_PROXY_ADMIN          = '\xe16d201ca134345601631d327a971a3741646b0d'

-- ===== Ethereum (chain 1) light clients =====
ETH_MPT_VERIFIER              = '\x8022ceaa2771fdc188a6f3c783e7207f53b121d2'
ETH_BLOCKUPDATER_SRC_BSC      = '\x11732663d735db99569bd9fd19dc853fbea48696'
ETH_BLOCKUPDATER_SRC_POLYGON  = '\xcc069839654d10ebe29229a9f44bbb0a8056b28d'
ETH_BLOCKUPDATER_SRC_OP       = '\x9d5a7f0ce68bba0ea9a720ad5b4a3a0e2513c0a0'
ETH_BLOCKUPDATER_SRC_ARB      = '\x29aea16936502b41af199a975a74779d5151c4c3'
ETH_BLOCKUPDATER_SRC_BASE     = '\xb5a6da0c0334a83fee0f8cbf8b0dd1d0dfe95099'
ETH_ENTRYPOINT_OWNER          = '\xa926f089e07a9fd7a1a9438b1bb801963807a6d7'

-- ===== Per-chain entrypoint owner multisigs =====
OWNER_BSC_AVAX_ARB_POLY       = '\xaf7757a1aa3024cf19308343cebbbc06f8cc8338'
OWNER_BASE_OP                 = '\xd85dc8cb3145411fe334d5c1698d36562ba18473'
```

---

## 9. Counterparty chains & application layer (findings, not omissions)

- **Token zkBridge / NFT zkBridge are application contracts**, not core Polyhedra contracts. They are built by integrators on top of `ZKBridge.send` (implementing `IZKBridgeReceiver.zkReceive`). There is **no single canonical token-vault/minter address** to index in the core stack; index per-integrator app contracts that appear as `MessagePublished.sender`. (The deBridge-style "lock-on-source / mint-on-dest" pattern referenced in the scope is realized this way, not as a distinct Polyhedra contract.)
- **Counterparty chains outside the 7 target chains:** the Ethereum entrypoint had configured BlockUpdaters for **zkBridge-internal ids 14 and 20** (light clients `0x5833ce34…` and `0xbe3872e2…`) in addition to the in-set sources. These correspond to non-target chains in Polyhedra's wider footprint (the LayerZero zkLightClient side — [lightclient.md](./lightclient.md) — lists opBNB, Linea, Scroll, Mantle, Celo, Core, Fantom, Moonbeam, Metis, Gnosis, Manta, Mode, Klaytn, X Layer, Flare, Merlin, Sei, Cyber, Blast, Arbitrum Nova). The native zkBridge also messages **Bitcoin** (Bitcoin Messaging Protocol) and Polyhedra's own **EXPchain** — both out of scope here but recorded as counterparties.
- The **Polyhedra Network ERC-20 token** (`0xc71b5f631354be6853efe9c3ab6b9590f8302e81`, Ethereum; on-chain `symbol()` = `ZK`, `name()` = `Polyhedra Network` — `ZKJ` is the older CEX ticker) is governance, **not** part of the bridge message path.

---

## 10. Verification & sources

How every constant was verified (2026-06-09):
- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]`. `MessagePublished` (`0xb8abfd5c…`), `ExecutedMessage` (`0x4a008ac8…`) confirmed against **live `eth_getLogs`** on the Ethereum entrypoint `0xa8a4547…` (3 + 1 logs in a ~49k-block window); `ImportBlock` (`0xa3fa2e60…`) confirmed live on the BSC-source BlockUpdater `0x11732663…`. All entrypoint/BlockUpdater/MptVerifier selectors (`send`/`validateTransactionProof`/`blockUpdaters`/`mptVerifiers`/`importBlock`/`validateMPT`, …) confirmed **present in the live implementation bytecode** via PUSH4 scan.
- **Addresses:** entrypoint, ProxyAdmin, and per-source BlockUpdaters/MptVerifier existence-checked via `eth_getCode` (non-empty) on all 7 chains; light clients resolved live via `eth_call blockUpdaters(uint16)` / `mptVerifiers(uint16)` on each entrypoint. zkBridge-internal ids read live via `eth_call chainId()`. Owners read via `eth_call owner()`.
- **Proxy impls/admins:** read live from the EIP-1967 implementation and admin slots; entrypoint impl `0x6eab43…` confirmed identical across all 7 chains; BlockUpdater impls (`0xbe0b942d…` BSC, `0x75d32e80…` Polygon) and immutables (OP BlockUpdater + MptVerifier, slots `0x0`) read per contract.
- **Contract names + ABIs:** Etherscan-verified source — entrypoint impl = `ZKBridge`, light client = `BscBlockUpdater` (impl `0xbe0b942d…`), `MptVerifier`, proxy = `OptimizedTransparentUpgradeableProxy`.
- **Unverified:** the fee-manager getter name (`feeManager()` reverts; `feeManagers(address)` absent); the `NewBlockUpdater`/`NewMptVerifier`/`NewFee` topic0s (computed from the verified setter pattern but not seen in a live log — rare admin events).

**Authoritative sources:**
- Polyhedra zkBridge docs — [docs.zkbridge.com](https://docs.zkbridge.com) (message-passing, NFT transfer, zkLightClient sections) and the EXPchain zkBridge guide [docs.polyhedra.network/expchain/zkbridge](https://docs.polyhedra.network/expchain/zkbridge/) (IZKBridge / IZKBridgeReceiver interfaces, internal chainId examples).
- Etherscan — entrypoint [`0xa8a4547…21C7`](https://etherscan.io/address/0xa8a4547Be2eCe6Dde2Dd91b4A5adFe4A043b21C7) (impl [`0x6eab43…d43b`](https://etherscan.io/address/0x6eab43ced4041ce6b4048844b3b2c811bffad43b)), BlockUpdater [`0x11732663…`](https://etherscan.io/address/0x11732663d735db99569bd9fd19dc853fbea48696) (impl [`0xbe0b942d…`](https://etherscan.io/address/0xbe0b942df3e28cc0373f39be729a6a83f0d7e0c6)), MptVerifier [`0x8022ceaa…`](https://etherscan.io/address/0x8022ceaa2771fdc188a6f3c783e7207f53b121d2).
- Block explorers for the other six chains: Basescan, BscScan, Snowscan, Arbiscan, Optimistic Etherscan, Polygonscan (entrypoint present on each).
