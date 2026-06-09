# Polygon AggLayer Unified Bridge (LxLy) — Topics, Selectors, Addresses (Ethereum L1 only of the 7 targets; mirror on attached chains outside the 7)

**Status:** verified against live RPC on Ethereum L1 + all six other requested chains and against Polygon zkEVM (chain 1101, the canonical attached chain), and the `0xPolygonHermez/zkevm-contracts` repos, on 2026-06-09.
**Scope:** the Polygon AggLayer "Unified Bridge" (a.k.a. LxLy bridge): `PolygonZkEVMBridgeV2` + its on-chain counterparties `PolygonZkEVMGlobalExitRootV2` and `PolygonRollupManager`, plus the `AggLayerGateway`, on **Ethereum mainnet (chain 1)**. Topics/selectors are chain-agnostic (recomputed locally as keccak256 of the canonical signature); addresses are network-specific. **Of the seven requested chains, AggLayer's canonical contracts exist ONLY on Ethereum L1.** Base, BNB, Avalanche, Arbitrum, Optimism, and Polygon PoS run **no** AggLayer contract (every address below returns `0x` there). The bridge *mirror* runs on the attached L2s — Polygon zkEVM 1101, X Layer 196, and sovereign chains — all **outside** the seven (documented in §6 as a finding, not an omission).

The Unified Bridge is the single asset+message gateway of the AggLayer interoperability network. It is **NOT** the legacy Polygon PoS bridge (that is a separate, older system on chain 1↔137 — see §9.1) and it is **NOT** an immutable contract: every core contract is a **Transparent (EIP-1967) upgradeable proxy** behind one shared `ProxyAdmin`, itself owned by a 3-day `TimelockController`. The L1 bridge is deployed **once** at a deterministic address and the **same address `0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe` is reused on every attached chain** (L1, Polygon zkEVM, X Layer, sovereign chains) — so you must key bridge state on `(chainId, address)`, never on address alone.

The non-obvious facts a monitoring engineer needs before indexing:
1. **`networkID` is the chain's slot in the AggLayer mesh, not the EVM chainId.** L1 = network 0; Polygon zkEVM = network 1; each attached chain has its own small integer. Bridge events carry `originNetwork`/`destinationNetwork` as these AggLayer ids.
2. **`ClaimEvent` on the v2 unified bridge uses `uint256 globalIndex` (topic0 `0x1df3f2a9…`), NOT the legacy `uint32 index` variant (`0x25308c93…`)** — the legacy topic fires **zero** times on the v2 bridge (verified live). Index on `0x1df3f2a9…`.
3. **`BridgeEvent` and `ClaimEvent` are fully non-indexed** (topic0 only, all params in `data`). You cannot pre-filter by user in the topics array — decode the data.
4. **The L1 deployment is `PolygonZkEVMBridgeV2`, NOT `BridgeL2SovereignChain`.** The sovereign-only functions (`setSovereignTokenAddress`, `migrateLegacyToken`, `setSovereignWETHAddress`, `wethToken`) are **absent** from the L1 impl bytecode (verified). They appear only on sovereign-chain mirrors (§6).

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Verified on L1 (impl size) |
|----------|------|--------|----------------------------|
| **PolygonZkEVMBridgeV2** | Single asset+message bridge. Emits `BridgeEvent` (deposit) / `ClaimEvent` (withdraw). Holds escrowed assets on L1; mints CREATE2 `TokenWrapped` ERC-20s on destination. | **Transparent EIP-1967** | impl `0x66e0120e…` (13 986 B) |
| **PolygonZkEVMGlobalExitRootV2** | Global Exit Root manager: combines the L1 mainnet-exit-root (from the bridge) with the rollup-exit-root (from RollupManager) into the GER; maintains the L1 Info Tree. Only the bridge may call `updateExitRoot`. | **Transparent EIP-1967** | impl `0x7f1655d9…` (3 353 B) |
| **PolygonRollupManager** | Registry/verifier hub for all attached rollups+sovereign chains. `rollupCount()` = 27 live (2026-06-09). Verifies state transitions (zk batches + pessimistic proofs), feeds the rollup-exit-root to the GER, pays/charges POL. | **Transparent EIP-1967** | impl `0x15caf18d…` (23 734 B) |
| **AggLayerGateway** | Verification-key / proof-route gateway used by RollupManager's pessimistic-proof path (`aggLayerGateway()` on RM → this). | **Transparent EIP-1967** | impl `0xd062b7f9…` (12 233 B) |
| **TokenWrapped** | Per-(originNetwork,originToken) wrapped ERC-20, deployed by the bridge via CREATE2. Address is deterministic (`precalculatedWrapperAddress` / `getTokenWrappedAddress`). | Plain ERC-20 (not a proxy) | — |
| **TimelockController** | 3-day timelock that owns the ProxyAdmin (upgrade authority). | not a proxy | `0xeF146245…` (10 107 B) |
| **ProxyAdmin** | Transparent-proxy admin for all four core proxies. Owner = the Timelock. | not a proxy | `0x0f99738B…` (2 149 B) |

The L1 bridge is the **production AggLayer v2 / "Unified Bridge" generation** (single `BridgeV2` codebase shared across L1 and all attached chains). There is no separately-deployed v1 on L1 to document — the v1 zkEVM bridge was upgraded in place to V2. Hence this single `core.md`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak256 on 2026-06-09 and, where noted, cross-checked against live `eth_getLogs` on the L1 contracts.

### 1.1 PolygonZkEVMBridgeV2 (emitter on L1 = `0x2a3D…2EDe`)

| topic0 | Event |
|--------|-------|
| `0x501781209a1f8899323b96b4ef08b168df93e0a90c673d1e4cce39366cb62f9b` | `BridgeEvent(uint8 leafType, uint32 originNetwork, address originAddress, uint32 destinationNetwork, address destinationAddress, uint256 amount, bytes metadata, uint32 depositCount)` — **deposit/bridge out** *(verified live: 318 logs in 49k blocks; topic0-only, 9 data words)* |
| `0x1df3f2a973a00d6635911755c260704e95e8a5876997546798770f76396fda4d` | `ClaimEvent(uint256 globalIndex, uint32 originNetwork, address originAddress, address destinationAddress, uint256 amount)` — **withdraw/claim** *(verified live: 68 logs; topic0-only, 5 data words). THIS is the v2 variant.* |
| `0x25308c93ceeed162da955b3f7ce3e3f93606579e40fb92029faa9efe27545983` | `ClaimEvent(uint32 index, uint32 originNetwork, address originAddress, address destinationAddress, uint256 amount)` — **LEGACY v1 variant; fires 0× on the v2 bridge** *(verified absent live).* |
| `0x490e59a1701b938786ac72570a1efeac994a3dbe96e2e883e19e902ace6e6a39` | `NewWrappedToken(uint32 originNetwork, address originTokenAddress, address wrappedTokenAddress, bytes metadata)` — first time a foreign token is bridged in (CREATE2 wrapper deployed). Rare. |

`leafType`: `0` = asset, `1` = message. `globalIndex` encodes `(mainnetFlag, rollupIndex, localIndex)` packed in a `uint256` (the v2 unified-leaf index) — do not treat it as a flat counter.

### 1.2 BridgeL2SovereignChain — additional events (sovereign mirrors only; NOT on L1, NOT on zkEVM 1101)

These are inherited-plus-extended. `BridgeEvent`/`ClaimEvent`/`NewWrappedToken` are identical to §1.1. The extras (recomputed locally; not present on any of the 7 chains — documented for counterparty completeness):

| topic0 | Event |
|--------|-------|
| `0xdbe8a5da6a7a916d9adfda9160167a0f8a3da415ee6610e810e753853597fce7` | `SetSovereignTokenAddress(uint32 originNetwork, address originTokenAddress, address sovereignTokenAddress, bool isNotMintable)` |
| `0xb7f8fd4d1faf9b2929dc269f59c53e3a2bccc44e9950f33a568fcbcb37eb69a9` | `MigrateLegacyToken(address sender, address legacyTokenAddress, address updatedTokenAddress, uint256 amount)` |
| `0xc7318b7ed6ba4f2908a3de396d8ab49b1dadb55db5b55123247a401f29ff8d82` | `SetSovereignWETHAddress(address sovereignWETHTokenAddress, bool isNotMintable)` |
| `0xc2ae0bd0ec0fd0352bfe5bacac49637af342c1e40f1b80a7f74440dc7fe3f063` | `RemoveLegacySovereignTokenAddress(address sovereignTokenAddress)` |

### 1.3 PolygonZkEVMGlobalExitRootV2 (emitter on L1 = `0x580b…3CFb`)

| topic0 | Event |
|--------|-------|
| `0xda61aa7823fcd807e37b95aabcbe17f03a6f3efd514176444dae191d27fd66b3` | `UpdateL1InfoTree(bytes32 indexed mainnetExitRoot, bytes32 indexed rollupExitRoot)` *(verified live: 14 logs)* |
| `0xaf6c6cd7790e0180a4d22eb8ed846e55846f54ed10e5946db19972b5a0813a59` | `UpdateL1InfoTreeV2(bytes32 currentL1InfoRoot, uint32 indexed leafCount, uint256 blockhash, uint64 minTimestamp)` *(verified live: 14 logs)* |
| `0x11f50c71891002839c2637ce302087160298255a87f1ea60d40e8db081383fad` | `InitL1InfoRootMap(uint32 leafCount, bytes32 currentL1InfoRoot)` |

> **`UpdateL1InfoTree` and `UpdateL1InfoTreeV2` both fire on every GER update** (14 + 14 in the same window). V2 is the indexed-leaf-count variant added for the L1 Info Tree v2; index whichever you key on, but expect both.

### 1.4 PolygonRollupManager (emitter on L1 = `0x5132…7aB2`)

| topic0 | Event |
|--------|-------|
| `0xd1ec3a1216f08b6eff72e169ceb548b782db18a6614852618d86bb19f3f9b0d3` | `VerifyBatchesTrustedAggregator(uint32 indexed rollupID, uint64 numBatch, bytes32 stateRoot, bytes32 exitRoot, address indexed aggregator)` *(verified live: 12 logs)* |
| `0xaac1e7a157b259544ebacd6e8a82ae5d6c8f174e12aa48696277bcc9a661f0b4` | `VerifyBatches(uint32 indexed rollupID, uint64 numBatch, bytes32 stateRoot, bytes32 exitRoot, address indexed aggregator)` |
| `0xdf47e7dbf79874ec576f516c40bc1483f7c8ddf4b45bfd4baff4650f1229a711` | `VerifyPessimisticStateTransition(uint32 indexed rollupID, bytes32 prevPessimisticRoot, bytes32 newPessimisticRoot, bytes32 prevLocalExitRoot, bytes32 newLocalExitRoot, bytes32 l1InfoRoot, address indexed trustedAggregator)` *(verified live: 8 logs — the AggLayer pessimistic-proof path)* |
| `0x1d9f30260051d51d70339da239ea7b080021adcaabfa71c9b0ea339a20cf9a25` | `OnSequenceBatches(uint32 indexed rollupID, uint64 lastBatchSequenced)` |
| `0x194c983456df6701c6a50830b90fe80e72b823411d0d524970c9590dc277a641` | `CreateNewRollup(uint32 indexed rollupID, uint32 rollupTypeID, address rollupAddress, uint64 chainID, address gasTokenAddress)` |
| `0xadfc7d56f7e39b08b321534f14bfb135ad27698f7d2f5ad0edc2356ea9a3f850` | `AddExistingRollup(uint32 indexed rollupID, uint64 forkID, address rollupAddress, uint64 chainID, uint8 rollupVerifierType, uint64 lastVerifiedBatchBeforeUpgrade)` |
| `0xa2970448b3bd66ba7e524e7b2a5b9cf94fa29e32488fb942afdfe70dd4b77b52` | `AddNewRollupType(uint32 indexed rollupTypeID, address consensusImplementation, address verifier, uint64 forkID, uint8 rollupVerifierType, bytes32 genesis, string description)` |
| `0xf585e04c05d396901170247783d3e5f0ee9c1df23072985b50af089f5e48b19d` | `UpdateRollup(uint32 indexed rollupID, uint32 newRollupTypeID, uint64 lastVerifiedBatchBeforeUpgrade)` |

### 1.5 Proxy / governance (all four core proxies)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **watch on every core proxy to catch impl rotation.** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Selectors recomputed locally on 2026-06-09; presence checked against the live L1 impl runtime bytecode (occurrences noted).

### 2.1 PolygonZkEVMBridgeV2 — state-changing (all present in L1 impl `0x66e0120e…` unless noted)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xcd586579` | `bridgeAsset(uint32 destinationNetwork, address destinationAddress, uint256 amount, address token, bool forceUpdateGlobalExitRoot, bytes permitData)` | **deposit / bridge out an ERC-20 or native.** Emits `BridgeEvent` (leafType 0). `payable`. ✓present |
| `0x240ff378` | `bridgeMessage(uint32 destinationNetwork, address destinationAddress, bool forceUpdateGlobalExitRoot, bytes metadata)` | bridge a message. Emits `BridgeEvent` (leafType 1). `payable`. ✓present |
| `0xb8b284d0` | `bridgeMessageWETH(uint32 destinationNetwork, address destinationAddress, uint256 amountWETH, bool forceUpdateGlobalExitRoot, bytes metadata)` | message + WETH value (gas-token chains). ✓present |
| `0xccaa2d11` | `claimAsset(bytes32[32] smtProofLocalExitRoot, bytes32[32] smtProofRollupExitRoot, uint256 globalIndex, bytes32 mainnetExitRoot, bytes32 rollupExitRoot, uint32 originNetwork, address originTokenAddress, uint32 destinationNetwork, address destinationAddress, uint256 amount, bytes metadata)` | **claim an asset (withdraw).** Emits `ClaimEvent` (0x1df3f2a9). Dual-SMT-proof v2 signature. ✓present |
| `0xf5efcd79` | `claimMessage(bytes32[32] smtProofLocalExitRoot, bytes32[32] smtProofRollupExitRoot, uint256 globalIndex, bytes32 mainnetExitRoot, bytes32 rollupExitRoot, uint32 originNetwork, address originAddress, uint32 destinationNetwork, address destinationAddress, uint256 amount, bytes metadata)` | claim a message. Emits `ClaimEvent`. ✓present |
| `0x79e2cf97` | `updateGlobalExitRoot()` | pushes the bridge's new mainnet-exit-root into the GER manager. ✓present |
| `0x2072f6c5` | `activateEmergencyState()` | pauses bridge (Pausable). ✓present |
| `0xdbc16976` | `deactivateEmergencyState()` | unpause. |

### 2.2 PolygonZkEVMBridgeV2 — views

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xcc461632` | `isClaimed(uint32 index, uint32 sourceBridgeNetwork)` → `bool` | **the live isClaimed on L1/zkEVM** (✓ 2 occ). |
| `0x175a9209` | `isClaimed(uint256 globalIndex, uint32 sourceBridgeNetwork)` → `bool` | sovereign-chain variant; **absent on L1** (0 occ). |
| `0x22e95f2c` | `getTokenWrappedAddress(uint32 originNetwork, address originTokenAddress)` → `address` | CREATE2 wrapper for a foreign token (0x0 if not yet deployed). ✓present |
| `0xaaa13cc2` | `precalculatedWrapperAddress(uint32 originNetwork, address originTokenAddress, string name, string symbol, uint8 decimals)` → `address` | deterministic wrapper address. |
| `0xbab161bf` | `networkID()` → `uint32` | AggLayer network id (**L1 = 0**, verified). |
| `0xd02103ca` | `globalExitRootManager()` → `address` | → GER manager (`0x580b…3CFb` on L1, verified). |
| `0x8ed7e3f2` | `polygonRollupManager()` → `address` | → RollupManager (`0x5132…7aB2` on L1, verified). |
| `0x3c351e10` | `gasTokenAddress()` → `address` | `0x0` on L1 (native gas = ETH, verified). |
| `0x2dfdf0b5` | `depositCount()` → `uint256` | leaf count of the local exit tree. |
| `0xfb570834` | `verifyMerkleProof(bytes32 leafHash, bytes32[32] smtProof, uint32 index, bytes32 root)` → `bool` | |

### 2.3 PolygonZkEVMBridgeV2 — sovereign-only (BridgeL2SovereignChain; **all ABSENT on L1**, verified 0 occ)

| Selector | Signature |
|----------|-----------|
| `0xb42f6b3a` | `setSovereignTokenAddress(uint32,address,address,bool)` — 0 occ on L1 |
| `0x57cfbee3` | `setMultipleSovereignTokenAddress(uint32[],address[],address[],bool[])` |
| `0xb0b37920` | `migrateLegacyToken(address,uint256,bytes)` — 0 occ on L1 |
| `0xbf130d7f` | `setSovereignWETHAddress(address,bool)` — 0 occ on L1 |
| `0xb4586962` | `removeLegacySovereignTokenAddress(address)` |
| `0x4b57b0be` | `wethToken()` → `address` — **0 occ on L1** (native-gas chain; only present on gas-token sovereign chains) |

### 2.4 PolygonZkEVMGlobalExitRootV2

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x33d6247d` | `updateExitRoot(bytes32 newRoot)` | **only the bridge may call** (sets mainnet exit root). |
| `0x3ed691ef` | `getLastGlobalExitRoot()` → `bytes32` | current GER. |
| `0x5ca1e165` | `getRoot()` → `bytes32` | L1 Info Tree root (verified live). |
| `0xa3c573eb` | `bridgeAddress()` → `address` | → bridge (verified `0x2a3D…2EDe`). |
| `0xef4eeb35` | `l1InfoRootMap(uint32 depositCount)` → `bytes32` | historical L1 Info root by leaf count. |

### 2.5 PolygonRollupManager

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa3c573eb` | `bridgeAddress()` → `address` | verified → bridge. |
| `0xd02103ca` | `globalExitRootManager()` → `address` | verified → `0x580b…3CFb`. |
| `0xa2967d99` | `getRollupExitRoot()` → `bytes32` | aggregated rollup exit root fed to the GER. ✓present in impl |
| `0xf4e92675` | `rollupCount()` → `uint32` | **27** live (verified). |
| `0xe46761c4` | `pol()` → `address` | POL fee token (`0x455e…c3f6`, verified). |
| `0xab0475cf` | `aggLayerGateway()` → `address` | → `0x046b…74b3` (verified). ✓present in impl |
| `0x9a908e73` | `onSequenceBatches(uint64,bytes32)` | called by a rollup when it sequences. ✓present in impl |
| `0xf9c4c2ae` | `rollupIDToRollupData(uint32)` | full per-rollup struct. |
| `0xceee281d` | `rollupAddressToID(address)` → `uint32` | reverse lookup. |

### 2.6 Proxy upgrade surface (Transparent — admin-only, on the ProxyAdmin)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x99a88ec4` | `upgrade(address proxy, address implementation)` | ProxyAdmin; emits `Upgraded` on the proxy. |
| `0x9623609d` | `upgradeAndCall(address proxy, address implementation, bytes data)` | ProxyAdmin. |
| `0x8da5cb5b` | `owner()` → `address` | ProxyAdmin owner = the Timelock (`0xeF14…A4EF`, verified). |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Wiring confirmed live: `bridge.globalExitRootManager()` → GER, `bridge.polygonRollupManager()` → RollupManager, `GER.bridgeAddress()` → bridge, `RM.bridgeAddress()` → bridge, `RM.globalExitRootManager()` → GER, `RM.aggLayerGateway()` → gateway.

| Role | Address | One-liner |
|------|---------|-----------|
| **PolygonZkEVMBridgeV2** (proxy) | `0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe` | The Unified Bridge. Emits §1.1 events. `networkID()` = 0. Same address on every attached chain. |
| **PolygonZkEVMGlobalExitRootV2** (proxy) | `0x580bda1e7A0CFAe92Fa7F6c20A3794F169CE3CFb` | GER manager / L1 Info Tree. Emits §1.3. |
| **PolygonRollupManager** (proxy) | `0x5132A183E9F3CB7C848b0AAC5Ae0c4f0491B7aB2` | Rollup registry+verifier; `rollupCount()` = 27. Emits §1.4. |
| **AggLayerGateway** (proxy) | `0x046bb8bb98db4cecbb2929542686b74b516274b3` | Pessimistic-proof verification-key gateway. |
| **POL token** | `0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6` | ERC-20 fee/stake token used by RollupManager. |
| **ProxyAdmin** (shared) | `0x0f99738B2Fc14D77308337f3e2596b63aE7bCC4A` | Transparent-proxy admin for all four core proxies; `owner()` = Timelock. |
| **TimelockController** | `0xeF1462451C30Ea7aD8555386226059fE837CA4EF` | Upgrade authority; `getMinDelay()` = **259 200 s (3 days)**. Owns the ProxyAdmin. |

### 3.1 Live implementations (read from EIP-1967 slot `0x360894…bbc` on 2026-06-09)

| Proxy | Live implementation | impl size |
|-------|---------------------|-----------|
| Bridge `0x2a3D…2EDe` | `0x66e0120e3C965552A89aCC37b03f762624BAC5ad` | 13 986 B |
| GER `0x580b…3CFb` | `0x7f1655D9D570167b2a3FFD1ef809D3fdd74427C5` | 3 353 B |
| RollupManager `0x5132…7aB2` | `0x15caf18DED768E3620E0F656221bf6b400Ad2618` | 23 734 B |
| AggLayerGateway `0x046b…74b3` | `0xd062B7f9FBb89bDa59262E77015c34A27DC9aB49` | 12 233 B (gateway proxy runtime = 2 227 B) |

All four admin slots (`0xb53127…6103`) read `0x…0f99738b2fc14d77308337f3e2596b63ae7bcc4a` = the shared ProxyAdmin → confirms **Transparent** (not UUPS) pattern.

---

## 4. Addresses — Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon PoS (137)

**No AggLayer Unified-Bridge contract is deployed on any of these six chains.** Verified 2026-06-09: `eth_getCode` for the bridge `0x2a3DD3EB…`, the RollupManager `0x5132A183…`, and the GER `0x580bda1e…` returns **`0x` (empty)** on each of Base, BNB, Avalanche, Arbitrum, Optimism, and Polygon PoS.

These chains are **not** attached to AggLayer (they are independent L1s / Optimistic-and-Arbitrum-stack L2s anchored to Ethereum by their own native bridges). **Polygon PoS (137) in particular is served by the *legacy* Polygon PoS bridge, a completely separate system** (§9.1) — it shares the "Polygon" brand but none of the LxLy code/addresses.

| Chain | ID | Bridge `0x2a3D…2EDe` | RollupManager | GER | AggLayer contracts? |
|---|---|---|---|---|---|
| Base | 8453 | `0x` | `0x` | `0x` | **none** |
| BNB Smart Chain | 56 | `0x` | `0x` | `0x` | **none** |
| Avalanche C-Chain | 43114 | `0x` | `0x` | `0x` | **none** |
| Arbitrum One | 42161 | `0x` | `0x` | `0x` | **none** |
| Optimism | 10 | `0x` | `0x` | `0x` | **none** |
| Polygon PoS | 137 | `0x` | `0x` | `0x` | **none** (legacy PoS bridge instead — §9.1) |

---

## 5. Cross-chain summary

| Chain | ID | Bridge | GER | RollupManager | AggLayerGateway | POL |
|---|---|---|---|---|---|---|
| **Ethereum** | 1 | ✅ `0x2a3D…2EDe` | ✅ `0x580b…3CFb` | ✅ `0x5132…7aB2` | ✅ `0x046b…74b3` | ✅ `0x455e…c3F6` |
| Base | 8453 | — | — | — | — | — |
| BNB | 56 | — | — | — | — | — |
| Avalanche | 43114 | — | — | — | — | — |
| Arbitrum One | 42161 | — | — | — | — | — |
| Optimism | 10 | — | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — | — |
| *Polygon zkEVM (counterparty, **not** in the 7)* | 1101 | ✅ `0x2a3D…2EDe` (mirror, impl `0x5f41…cbd5`, 22 811 B) | ✅ GER-L2 `0xa40d…b8fa` | — (L1-only) | — | — |

**Vanity / address tell:** the bridge is the **same literal `0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe` on L1 and every attached chain** (deterministic deploy). Presence is NOT distinguishable by address — only by `eth_getCode` + chainId. The RollupManager, GER, AggLayerGateway, POL, ProxyAdmin and Timelock are **Ethereum-L1-only** (each rollup runs its own L2 GER mirror but no RollupManager).

**Three things to internalize:**
1. **All AggLayer canonical contracts of interest to a monitor live on Ethereum L1.** None of the seven requested chains except Ethereum has any AggLayer code.
2. **The bridge mirror lives on the attached chains (Polygon zkEVM 1101, X Layer 196, sovereign chains) — all outside the seven.** To watch the L2 side of a transfer you must index those out-of-set chains.
3. **Key bridge state on `(chainId, address)`** because the bridge address is identical across chains.

---

## 6. Counterparty chains outside the seven (a finding, not an omission)

AggLayer's whole purpose is cross-chain, so most bridge *destinations* are outside the requested seven. Verified/known counterparties:

- **Polygon zkEVM (chain 1101)** — the original AggLayer rollup. Bridge mirror at the **same `0x2a3DD3EB…`** (verified live, impl `0x5f4115…cbd5`, 22 811 B — `PolygonZkEVMBridgeV2`, **not** sovereign: `setSovereignTokenAddress`/`wethToken` = 0 occ). Its L2 GER manager is `0xa40d5f56745A118D0906a34E69aEC8C0Db1cb8fA` (2 112 B).
- **X Layer (OKB, chain 196)**, **Astar zkEVM**, **Wirex/GPT, Silicon, Pentagon, Lumia, Ternoa, Witness Chain, …** — the 27 rollups tracked by `RollupManager.rollupCount()` are attached AggLayer chains, **none of which is among the seven**. Newer attachments deploy `BridgeL2SovereignChain` (the §1.2/§2.3 sovereign variant) at the same bridge address.

When indexing an AggLayer transfer that *originates* on or is *destined* for any of the seven, note: **only Ethereum (network 0) is a valid AggLayer endpoint among the seven.** A bridge from "Polygon" via AggLayer means Polygon **zkEVM (1101)**, never Polygon **PoS (137)**.

---

## 7. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **PolygonZkEVMBridgeV2** | **Transparent (EIP-1967)** | impl slot `0x360894…bbc` set (`0x66e0120e…`); admin slot `0xb53127…6103` = ProxyAdmin `0x0f99738b…`. Runtime = 2 583 B proxy stub; logic in impl (13 986 B). | ProxyAdmin ← Timelock (3-day). |
| **PolygonZkEVMGlobalExitRootV2** | **Transparent (EIP-1967)** | impl `0x7f1655d9…`; admin = ProxyAdmin. | ProxyAdmin ← Timelock. |
| **PolygonRollupManager** | **Transparent (EIP-1967)** | impl `0x15caf18d…`; admin = ProxyAdmin. | ProxyAdmin ← Timelock. |
| **AggLayerGateway** | **Transparent (EIP-1967)** | impl `0xd062b7f9…`; admin = ProxyAdmin. | ProxyAdmin ← Timelock. |
| **TokenWrapped** (CREATE2 wrappers) | **NOT a proxy** | plain ERC-20 bytecode; EIP-1967 impl slot returns `0x0`. | none (immutable; bridge is minter). |
| **POL token** | not relevant to AggLayer upgrades | — | own admin. |
| **ProxyAdmin / TimelockController** | **NOT proxies** | full bytecode, impl slot `0x0`. | Timelock owner = AggLayer multisig/governance. |

- **EIP-1967 implementation slot:** `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` (read live for all four core proxies above).
- **EIP-1967 admin slot:** `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` (all four = `0x0f99738B…`, i.e. shared ProxyAdmin → **Transparent, not UUPS**).
- **Beacon slot** `0xa3f0ad74…` is empty on all four (no Beacon pattern).
- **`Upgraded(address)` topic0 to watch:** `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` (the L1 bridge `0x2a3D…2EDe`, GER, RollupManager, gateway). An impl rotation on the **bridge** is the highest-severity upgrade event (it controls escrowed funds).

---

## 8. Detection invariants & gotchas

1. **AggLayer = Ethereum L1 only among the seven.** Base/BNB/Avax/Arb/OP/Polygon-PoS return `0x` for every AggLayer address. Do not look for the bridge on those chains; do look on Ethereum and (for the counterparty leg) on Polygon zkEVM 1101 / X Layer 196 / sovereign chains.
2. **`ClaimEvent` v2 topic0 = `0x1df3f2a9…` (`uint256 globalIndex`), not `0x25308c93…`.** The legacy `uint32 index` topic fires **zero** times on the v2 bridge (verified). Indexing the wrong topic = missing every withdrawal.
3. **`BridgeEvent` and `ClaimEvent` are topic0-only (no indexed params).** You must decode `data` — there is no indexed user/token to pre-filter on. `BridgeEvent` has 9 data words (the trailing `bytes metadata` takes offset+len+payload); `ClaimEvent` has 5.
4. **The real destination user is `destinationAddress` inside the event data, not `tx.from`.** Claims are routinely submitted by relayers/auto-claim bots, so `tx.to`/`tx.from` ≠ the bridging user.
5. **`originNetwork`/`destinationNetwork` are AggLayer network ids, NOT EVM chainIds.** L1 = 0, zkEVM = 1, etc. Maintain a network-id → chainId map; do not equate network 1 with "Ethereum mainnet."
6. **`globalIndex` is a packed `uint256`** `(mainnetFlag, rollupIndex, localLeafIndex)`, not a monotonic counter. Use it as the dedupe key for a claim against its deposit, but parse the bit-packing rather than treating it as an ordinal.
7. **The L1 deployment is `PolygonZkEVMBridgeV2`, NOT `BridgeL2SovereignChain`.** `setSovereignTokenAddress`, `migrateLegacyToken`, `setSovereignWETHAddress`, `wethToken`, and `isClaimed(uint256,uint32)` are **absent** from the L1 impl (verified 0 occ); `isClaimed(uint32,uint32)` (`0xcc461632`) is the live one. The sovereign events/selectors (§1.2/§2.3) only appear on sovereign-chain mirrors.
8. **Wrapped tokens are CREATE2-deterministic.** A new foreign token emits `NewWrappedToken` (`0x490e59a1…`) once; thereafter the wrapper address is fixed and re-derivable via `getTokenWrappedAddress` / `precalculatedWrapperAddress`. The bridge is the sole minter/burner.
9. **Native-asset bridging carries `token = address(0)` and value in `msg.value`.** `gasTokenAddress()` = `0x0` on L1 → native = ETH. On gas-token sovereign chains the gas token differs and `wethToken()` becomes meaningful — but that's off the seven.
10. **GER updates fire BOTH `UpdateL1InfoTree` (`0xda61aa78…`) and `UpdateL1InfoTreeV2` (`0xaf6c6cd7…`)** per update (verified 14+14). Don't double-count a GER advance.
11. **Two state-verification paths on RollupManager:** legacy zk batches emit `VerifyBatchesTrustedAggregator`/`VerifyBatches`; the AggLayer pessimistic path emits `VerifyPessimisticStateTransition` (`0xdf47e7db…`, verified 8 logs). A monitor watching rollup finality must watch all three.
12. **Same bridge address everywhere → always key on `(chainId, 0x2a3D…2EDe)`.** GER/RollupManager/Gateway/POL/ProxyAdmin/Timelock are L1-exclusive — finding them on an L2 would be an anomaly.
13. **Upgrade authority is a 3-day timelock** (`getMinDelay()` = 259 200 s). A queued `upgrade`/`upgradeAndCall` on the ProxyAdmin via the Timelock is the early-warning signal for a bridge logic change — watch `Upgraded` (`0xbc7cd75a…`) on the four core proxies, and the Timelock's `CallScheduled`/`CallExecuted`.
14. **Do not conflate with the legacy Polygon PoS bridge** (§9.1): different contracts, different chain pair (1↔137), different events (`LockedEther`/`NewDepositBlock`/`Withdraw`), no LxLy global exit root.

---

## 9. Notes on adjacent systems

### 9.1 Legacy Polygon PoS bridge (separate — NOT this protocol)
Polygon PoS (chain 137) is bridged from Ethereum by the **legacy Plasma/PoS bridge** (`RootChainManager` `0xA0c68C638235ee32657e8f720a23ceC1bFc77C77`, `ERC20PredicateProxy`, `DepositManager`, `StateSender`). It emits `LockedERC20`/`LockedEther`/`NewDepositBlock`/`Withdraw`/`StateSynced`, has no `BridgeEvent`/`ClaimEvent`, and is unrelated to AggLayer LxLy. If a request says "Polygon bridge," disambiguate: AggLayer ⇒ Polygon **zkEVM 1101**; PoS bridge ⇒ Polygon **PoS 137**.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- PolygonZkEVMBridgeV2
TOPIC_BRIDGE_EVENT              = '\x501781209a1f8899323b96b4ef08b168df93e0a90c673d1e4cce39366cb62f9b'
TOPIC_CLAIM_EVENT_V2           = '\x1df3f2a973a00d6635911755c260704e95e8a5876997546798770f76396fda4d'  -- uint256 globalIndex (USE THIS)
TOPIC_CLAIM_EVENT_LEGACY       = '\x25308c93ceeed162da955b3f7ce3e3f93606579e40fb92029faa9efe27545983'  -- uint32 index (v1; 0 logs on v2)
TOPIC_NEW_WRAPPED_TOKEN        = '\x490e59a1701b938786ac72570a1efeac994a3dbe96e2e883e19e902ace6e6a39'
-- BridgeL2SovereignChain extras (sovereign mirrors only; NOT on the 7)
TOPIC_SET_SOVEREIGN_TOKEN      = '\xdbe8a5da6a7a916d9adfda9160167a0f8a3da415ee6610e810e753853597fce7'
TOPIC_MIGRATE_LEGACY_TOKEN     = '\xb7f8fd4d1faf9b2929dc269f59c53e3a2bccc44e9950f33a568fcbcb37eb69a9'
TOPIC_SET_SOVEREIGN_WETH       = '\xc7318b7ed6ba4f2908a3de396d8ab49b1dadb55db5b55123247a401f29ff8d82'
TOPIC_REMOVE_LEGACY_SOV_TOKEN  = '\xc2ae0bd0ec0fd0352bfe5bacac49637af342c1e40f1b80a7f74440dc7fe3f063'
-- PolygonZkEVMGlobalExitRootV2
TOPIC_UPDATE_L1_INFO_TREE      = '\xda61aa7823fcd807e37b95aabcbe17f03a6f3efd514176444dae191d27fd66b3'
TOPIC_UPDATE_L1_INFO_TREE_V2   = '\xaf6c6cd7790e0180a4d22eb8ed846e55846f54ed10e5946db19972b5a0813a59'
TOPIC_INIT_L1_INFO_ROOT_MAP    = '\x11f50c71891002839c2637ce302087160298255a87f1ea60d40e8db081383fad'
-- PolygonRollupManager
TOPIC_VERIFY_BATCHES_TRUSTED   = '\xd1ec3a1216f08b6eff72e169ceb548b782db18a6614852618d86bb19f3f9b0d3'
TOPIC_VERIFY_BATCHES           = '\xaac1e7a157b259544ebacd6e8a82ae5d6c8f174e12aa48696277bcc9a661f0b4'
TOPIC_VERIFY_PESSIMISTIC       = '\xdf47e7dbf79874ec576f516c40bc1483f7c8ddf4b45bfd4baff4650f1229a711'
TOPIC_ON_SEQUENCE_BATCHES      = '\x1d9f30260051d51d70339da239ea7b080021adcaabfa71c9b0ea339a20cf9a25'
TOPIC_CREATE_NEW_ROLLUP        = '\x194c983456df6701c6a50830b90fe80e72b823411d0d524970c9590dc277a641'
TOPIC_ADD_EXISTING_ROLLUP      = '\xadfc7d56f7e39b08b321534f14bfb135ad27698f7d2f5ad0edc2356ea9a3f850'
TOPIC_ADD_NEW_ROLLUP_TYPE      = '\xa2970448b3bd66ba7e524e7b2a5b9cf94fa29e32488fb942afdfe70dd4b77b52'
TOPIC_UPDATE_ROLLUP            = '\xf585e04c05d396901170247783d3e5f0ee9c1df23072985b50af089f5e48b19d'
-- Proxy
TOPIC_UPGRADED                 = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED            = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'

-- ===== Selectors =====
-- Bridge state-changing
SEL_BRIDGE_ASSET               = '\xcd586579'
SEL_BRIDGE_MESSAGE             = '\x240ff378'
SEL_BRIDGE_MESSAGE_WETH        = '\xb8b284d0'
SEL_CLAIM_ASSET                = '\xccaa2d11'
SEL_CLAIM_MESSAGE              = '\xf5efcd79'
SEL_UPDATE_GLOBAL_EXIT_ROOT    = '\x79e2cf97'
SEL_ACTIVATE_EMERGENCY         = '\x2072f6c5'
SEL_DEACTIVATE_EMERGENCY       = '\xdbc16976'
-- Bridge views
SEL_IS_CLAIMED_U32             = '\xcc461632'  -- live on L1
SEL_IS_CLAIMED_U256            = '\x175a9209'  -- sovereign only (absent L1)
SEL_GET_TOKEN_WRAPPED_ADDRESS  = '\x22e95f2c'
SEL_NETWORK_ID                 = '\xbab161bf'
SEL_GLOBAL_EXIT_ROOT_MANAGER   = '\xd02103ca'
SEL_POLYGON_ROLLUP_MANAGER     = '\x8ed7e3f2'
SEL_GAS_TOKEN_ADDRESS          = '\x3c351e10'
SEL_DEPOSIT_COUNT              = '\x2dfdf0b5'
-- Sovereign-only (absent on L1)
SEL_SET_SOVEREIGN_TOKEN        = '\xb42f6b3a'
SEL_MIGRATE_LEGACY_TOKEN       = '\xb0b37920'
SEL_SET_SOVEREIGN_WETH         = '\xbf130d7f'
SEL_WETH_TOKEN                 = '\x4b57b0be'
-- GER
SEL_UPDATE_EXIT_ROOT           = '\x33d6247d'
SEL_GET_LAST_GLOBAL_EXIT_ROOT  = '\x3ed691ef'
SEL_GET_ROOT                   = '\x5ca1e165'
SEL_BRIDGE_ADDRESS             = '\xa3c573eb'
-- RollupManager
SEL_GET_ROLLUP_EXIT_ROOT       = '\xa2967d99'
SEL_ROLLUP_COUNT               = '\xf4e92675'
SEL_POL                        = '\xe46761c4'
SEL_AGGLAYER_GATEWAY           = '\xab0475cf'
SEL_ON_SEQUENCE_BATCHES        = '\x9a908e73'
-- ProxyAdmin
SEL_UPGRADE                    = '\x99a88ec4'
SEL_UPGRADE_AND_CALL           = '\x9623609d'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT              = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT             = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses — Ethereum mainnet (chain ID 1) =====
ETH_BRIDGE_V2                  = '\x2a3dd3eb832af982ec71669e178424b10dca2ede'  -- same literal on every attached chain
ETH_GLOBAL_EXIT_ROOT_V2        = '\x580bda1e7a0cfae92fa7f6c20a3794f169ce3cfb'
ETH_ROLLUP_MANAGER             = '\x5132a183e9f3cb7c848b0aac5ae0c4f0491b7ab2'
ETH_AGGLAYER_GATEWAY           = '\x046bb8bb98db4cecbb2929542686b74b516274b3'
ETH_POL_TOKEN                  = '\x455e53cbb86018ac2b8092fdcd39d8444affc3f6'
ETH_PROXY_ADMIN                = '\x0f99738b2fc14d77308337f3e2596b63ae7bcc4a'
ETH_TIMELOCK                   = '\xef1462451c30ea7ad8555386226059fe837ca4ef'
-- Live impls (read from EIP-1967 slot 2026-06-09; can rotate via Upgraded)
ETH_BRIDGE_IMPL                = '\x66e0120e3c965552a89acc37b03f762624bac5ad'
ETH_GER_IMPL                   = '\x7f1655d9d570167b2a3ffd1ef809d3fdd74427c5'
ETH_ROLLUP_MANAGER_IMPL        = '\x15caf18ded768e3620e0f656221bf6b400ad2618'
ETH_AGGLAYER_GATEWAY_IMPL      = '\xd062b7f9fbb89bda59262e77015c34a27dc9ab49'

-- ===== Counterparty (OUTSIDE the 7) — Polygon zkEVM (chain ID 1101) =====
ZKEVM_BRIDGE_V2                = '\x2a3dd3eb832af982ec71669e178424b10dca2ede'  -- mirror, impl 0x5f4115...cbd5
ZKEVM_GER_L2                   = '\xa40d5f56745a118d0906a34e69aec8c0db1cb8fa'

-- ===== NOT deployed (verified eth_getCode = 0x on 2026-06-09): =====
--   Base(8453), BNB(56), Avalanche(43114), Arbitrum(42161), Optimism(10), Polygon PoS(137)
```

---

## 11. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` (keccak, no param names, `uint`→`uint256`). Cross-checked against live `eth_getLogs` on the L1 contracts: `BridgeEvent` `0x501781…` (318 logs / 49k blocks), `ClaimEvent` `0x1df3f2a9…` (68 logs; legacy `0x25308c93…` = 0 logs), `UpdateL1InfoTree`/`UpdateL1InfoTreeV2` (14+14), `VerifyBatchesTrustedAggregator` (12), `VerifyPessimisticStateTransition` (8). Event shapes confirmed by data-word counts (BridgeEvent 9 words / ClaimEvent 5 words, both topic0-only).
- **Selector presence:** scanned the live bridge impl runtime bytecode (`0x66e0120e…`, 13 986 B) — `bridgeAsset`/`bridgeMessage`/`bridgeMessageWETH`/`claimAsset(0xccaa2d11)`/`claimMessage`/`updateGlobalExitRoot`/`getTokenWrappedAddress`/`activateEmergencyState`/`isClaimed(0xcc461632)` present; `isClaimed(uint256,uint32)`/`setSovereignTokenAddress`/`migrateLegacyToken`/`wethToken` **absent** (confirms `PolygonZkEVMBridgeV2`, not the sovereign variant). RollupManager impl scanned for `getRollupExitRoot`/`onSequenceBatches`/`aggLayerGateway` (present).
- **Addresses:** existence-checked via `eth_getCode` on each of the seven chains' publicnode RPC + Polygon zkEVM. L1 wiring verified by `eth_call`: bridge↔GER↔RollupManager↔gateway↔POL cross-references all resolve. `networkID()` = 0, `gasTokenAddress()` = 0x0, `rollupCount()` = 27, `pol()` = `0x455e…c3f6`, ProxyAdmin `owner()` = Timelock, Timelock `getMinDelay()` = 259 200 s.
- **Proxy impls:** read live from EIP-1967 impl slot `0x360894…bbc` and admin slot `0xb53127…6103` for all four core proxies; admin = shared ProxyAdmin `0x0f99738b…` on each → **Transparent** (not UUPS/Beacon).
- **Chain coverage:** for all six non-Ethereum target chains, `eth_getCode` of the bridge, RollupManager, and GER returned `0x` → recorded as not-deployed. Polygon zkEVM (1101) mirror confirmed present (bridge same address, L2 GER `0xa40d…b8fa`).

**Authoritative sources:**
- Canonical repos: [`0xPolygonHermez/zkevm-contracts`](https://github.com/0xPolygonHermez/zkevm-contracts) (PolygonZkEVMBridgeV2, BridgeL2SovereignChain, PolygonZkEVMGlobalExitRootV2, PolygonRollupManager) · [`agglayer/agglayer`](https://github.com/agglayer/agglayer) · [`agglayer/agglayer-contracts`](https://github.com/agglayer/agglayer-contracts)
- Official docs: [Polygon AggLayer / Unified Bridge docs](https://docs.polygon.technology/agglayer/) · [LxLy bridge](https://docs.polygon.technology/zkEVM/architecture/unified-LxLy/)
- Explorers: [Etherscan — Bridge](https://etherscan.io/address/0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe) · [Etherscan — RollupManager](https://etherscan.io/address/0x5132A183E9F3CB7C848b0AAC5Ae0c4f0491B7aB2) · [Etherscan — GlobalExitRootV2](https://etherscan.io/address/0x580bda1e7A0CFAe92Fa7F6c20A3794F169CE3CFb)
```
