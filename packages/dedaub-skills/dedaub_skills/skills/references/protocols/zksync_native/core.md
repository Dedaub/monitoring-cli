# zkSync Era Native Bridge (Elastic Chain) — Topics, Selectors, Addresses (Ethereum L1 ↔ zkSync Era L2)

**Status:** verified against live RPC on Ethereum (1), zkSync Era L2 (324) and all six other requested chains, and against the canonical `matter-labs/era-contracts` repo + official ZKsync docs, on 2026-06-09.
**Scope:** the native (canonical) ZKsync bridge — the Elastic-Chain ecosystem stack: the **BridgeHub** entry point, the **ZKsync Era DiamondProxy** (EIP-2535: Mailbox / Executor / Getters / Admin facets), the **L1AssetRouter** (the contract formerly named `L1SharedBridge`), the **L1Nullifier** (the renamed legacy SharedBridge), the **L1NativeTokenVault**, the legacy **L1ERC20Bridge**, the **ChainTypeManager** (formerly `StateTransitionManager`), **MessageRoot**, **ValidatorTimelock**, **Governance** and the proxy admins. Event topics and function selectors are **chain-agnostic**; addresses are **network-specific**. The user requested presence on Ethereum, Base, BNB, Avalanche, Arbitrum One, Optimism, Polygon. **The entire native bridge is anchored on Ethereum L1 (chain 1) of the seven.** Base, BNB, Avalanche, Arbitrum, Optimism and Polygon carry **none** of these contracts (`eth_getCode` = `0x` for every L1 address — §6). The L2 counterparty is **zkSync Era (chain 324), which is outside the seven** — its L2 system contracts are documented in §5 as a recorded finding.

> The tracker slug had a typo ("zkync_native"); this is **zkSync Era** (ZK Stack / Elastic Network).

ZKsync's L1 contracts are a mix of **two proxy patterns**: the Era chain itself is an **EIP-2535 Diamond** (`DiamondProxy`, dispatch by `facets()`), while the ecosystem contracts (BridgeHub, AssetRouter, Nullifier, NativeTokenVault, ChainTypeManager, L1ERC20Bridge) are **OpenZeppelin `TransparentUpgradeableProxy`** instances all sharing one `ProxyAdmin` (`0xc2a3…2cf1`). There is **no CREATE2 vanity / no per-token instances** — one fixed singleton per role. The Era DiamondProxy carries a famous vanity tail: `0x32400084…a000324` (the `…000324` suffix = chain id 324). Base-token for Era is **ETH** (`baseToken(324) = address(1)`), so most flows are ETH bridging.

The architecture turned over in the **Gateway / v26 upgrade**: the old `L1SharedBridge` was split into **L1AssetRouter** (active routing, asset-id based) + **L1Nullifier** (replay/finalization ledger, the contract that kept the old `0xD7f9…` address), and a **L1NativeTokenVault** now escrows token balances. The legacy `L1ERC20Bridge` (`0x5789…`) is **still deployed but dormant** — new ERC-20 deposits route through the AssetRouter; it had **0 logs** in a 5k-block window. Internalize that before indexing: the live deposit/withdraw events fire on the **AssetRouter / NativeTokenVault / DiamondProxy**, not the legacy bridge.

---

## 0. Contract families & versions

| Family | Contracts | Role | Pattern |
|--------|-----------|------|---------|
| **Chain (Era)** | DiamondProxy + MailboxFacet, ExecutorFacet, GettersFacet, AdminFacet | L1 entry/exit for chain 324, priority queue, batch commit/prove/execute, fraud window | EIP-2535 Diamond |
| **Ecosystem hub** | BridgeHub, ChainTypeManager (ex-StateTransitionManager), MessageRoot, L1CtmDeployer | Registry of all ZK chains + L1→L2 request router + cross-chain message aggregation | Transparent proxies |
| **Asset bridging** | L1AssetRouter (ex-L1SharedBridge), L1Nullifier (ex-SharedBridge ledger), L1NativeTokenVault, L1ERC20Bridge (legacy) | ETH + ERC-20 deposits/withdrawals, token escrow, withdrawal finalization/replay-protection | Transparent proxies |
| **Operations / governance** | ValidatorTimelock, ChainAdmin, Governance, ProxyAdmin | Batch-execution delay, per-chain admin, protocol upgrades, proxy upgrade auth | Mixed (timelock, multisig-owned, custom Governance) |

One continuously-upgraded generation. The live Era **protocol version is `0x1d00000004`** (= packed major.minor.patch `0.29.4`) read live from `getProtocolVersion()`. Hence one `core.md`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-09; each marked *(live)* was additionally confirmed against real `eth_getLogs` on the cited emitter on Ethereum.

### 1.1 MailboxFacet (L1→L2 deposits / priority queue) — emitter = DiamondProxy `0x3240…0324`

| topic0 | Event |
|--------|-------|
| `0x4531cd5795773d7101c17bdeb9f5ab7f47d7056017506f937083be5d6e77a382` | `NewPriorityRequest(uint256 txId, bytes32 txHash, uint64 expirationTimestamp, (uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256[4],bytes,bytes,uint256[],bytes,bytes) transaction, bytes[] factoryDeps)` *(live, 7 logs / 800 blk)* — **the canonical L1→L2 deposit / priority-tx event.** The tuple is the `L2CanonicalTransaction` struct (txType, from, to, gasLimit, gasPerPubdataByteLimit, maxFeePerGas, maxPriorityFeePerGas, paymaster, nonce, value, reserved[4], data, signature, factoryDeps[], paymasterInput, reservedDynamic). |
| `0x779f441679936c5441b671969f37400b8c3ed0071cb47444431bf985754560df` | `NewPriorityRequestId(uint256 indexed txId, bytes32 indexed txHash)` *(live, 7 logs)* — fully-indexed companion to `NewPriorityRequest` (cheap to filter on `txHash`). |
| `0x0137d2eaa6ec5b7e4f233f6d6f441410014535d0f3985367994c94bf15a2a564` | `NewRelayedPriorityTransaction(uint256 txId, bytes32 txHash, uint64 expirationTimestamp)` — relayed (Gateway settlement-layer) priority tx; not seen for direct ETH-settled Era. |

> `NewPriorityRequest` carries a **nested dynamic tuple with a fixed-size `uint256[4]` array** — its full canonical signature is the 17-field form above. The naive "ABI-named" form **will not hash to `0x4531cd57…`**; use the exact type string. `txHash` is the L2 canonical tx hash — the cross-chain attribution key, not `tx.from`.

### 1.2 ExecutorFacet (L2→L1 batch lifecycle) — emitter = DiamondProxy `0x3240…0324`

| topic0 | Event |
|--------|-------|
| `0x8f2916b2f2d78cc5890ead36c06c0f6d5d112c7e103589947e8e2f0d6eddb763` | `BlockCommit(uint256 indexed batchNumber, bytes32 indexed batchHash, bytes32 indexed commitment)` *(live, 5 logs)* — a batch was committed. |
| `0x22c9005dd88c18b552a1cd7e8b3b937fcde9ca69213c1f658f54d572e4877a81` | `BlocksVerification(uint256 indexed previousLastVerifiedBatch, uint256 indexed currentLastVerifiedBatch)` *(live, 7 logs)* — ZK proof verified. |
| `0x2402307311a4d6604e4e7b4c8a15a7e1213edb39c16a31efa70afb06030d3165` | `BlockExecution(uint256 indexed batchNumber, bytes32 indexed batchHash, bytes32 indexed commitment)` *(live, 6 logs)* — batch executed → **withdrawals become finalizable.** |
| `0x8bd4b15ea7d1bc41ea9abc3fc487ccb89cd678a00786584714faa9d751c84ee5` | `BlocksRevert(uint256 totalBatchesCommitted, uint256 totalBatchesVerified, uint256 totalBatchesExecuted)` — committed batches rolled back (risk signal). |
| `0xfea115cea8c7414dc6c05dfb20821e4ea72c37b91e666a90ab4ddb5eabade850` | `BatchPrecommitmentSet(uint256 indexed batchNumber, uint256 indexed untrustedLastL2BlockNumberHint, bytes32 precommitment)` — interop pre-commitment (newer flow). |

> Event names say **"Block"** but the params are **batchNumber** — ZKsync's nomenclature predates the block/batch rename; do not assume these are per-L2-block.

### 1.3 AdminFacet (per-chain admin / freeze / upgrade) — emitter = DiamondProxy `0x3240…0324`

| topic0 | Event |
|--------|-------|
| `0xce6f42f7ce46cd12c695bbee4503fdd959206cdbb95fb3c37ebfe262cfffac2b` | `ExecuteUpgrade((((address,uint8,bool,bytes4[])[],address,bytes),(bytes,bytes),bytes,bytes,bytes32,uint256,bytes32,bytes32,bytes32,bytes,bytes32[]) diamondCut)` — a Diamond upgrade (facet cut) was executed. **Top upgrade-watch signal.** |
| `0x615acbaede366d76a8b8cb2a9ada6a71495f0786513d71aa97aaf0c3910b78de` | `Freeze()` — chain frozen (emergency halt). |
| `0x2f05ba71d0df11bf5fa562a6569d70c4f80da84284badbe015ce1456063d0ded` | `Unfreeze()` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |

### 1.4 BridgeHub (ecosystem registry / L1→L2 router) — emitter `0x303a…5213`

| topic0 | Event |
|--------|-------|
| `0x1e9125bc72db22c58abff6821d7333551967e26454b419ffa958e4cb8ef47600` | `NewChain(uint256 indexed chainId, address chainTypeManager, address chainGovernance)` — a new ZK chain registered into the Elastic Network. |
| `0x3df150949161462acf3be30521d7da9e533b247327a254e55dd01875897a6df3` | `BaseTokenAssetIdRegistered(bytes32 indexed assetId)` |
| `0x02629feb109d94b16a367231d248ba81c462f51ce5b984835f150f1c9f49ed25` | `SettlementLayerRegistered(uint256 indexed chainId, bool indexed isWhitelisted)` |
| `0x8f09d7694a9ae17acec5cf132d594d7eee23572f7fe132396ce72b1afbf7ef20` | `AssetRegistered(bytes32 indexed assetInfo, address indexed _assetAddress, bytes32 additionalData, address sender)` |

> The BridgeHub does **not** re-emit `NewPriorityRequest`; that fires on the target chain's DiamondProxy. The BridgeHub routes the call (`requestL2TransactionDirect` / `requestL2TransactionTwoBridges`) into the chain.

### 1.5 L1AssetRouter (ex-L1SharedBridge; active ERC-20/base-token routing) — emitter `0x8829…ce56`

| topic0 | Event |
|--------|-------|
| `0x0f87e1ea5eb1f034a6071ef630c174063e3d48756f853efaaf4292b929298240` | `BridgehubDepositBaseTokenInitiated(uint256 indexed chainId, address indexed from, bytes32 assetId, uint256 amount)` *(live, 113 logs / 5k blk — the highest-volume deposit event)* |
| `0xe21913bc89c1320d9709a5d236ffe06b54cf88aecfc9509ebd68f1adba45781e` | `BridgehubDepositInitiated(uint256 indexed chainId, bytes32 indexed txDataHash, address indexed from, bytes32 assetId, bytes bridgeMintData)` *(live, 5 logs)* — non-base-token deposit. |
| `0x44eb9a840094a49b3cd0a5205042598a1c08c4e87bafb5760bc2d8efa170c541` | `DepositFinalizedAssetRouter(uint256 indexed chainId, bytes32 indexed assetId, bytes assetData)` *(live, 61 logs)* — withdrawal/claim finalized on L1. |
| `0xe4def01b981193a97a9e81230d7b9f31812ceaf23f864a828a82c687911cb2df` | `BridgehubDepositFinalized(uint256 indexed chainId, bytes32 indexed txDataHash, bytes32 indexed l2DepositTxHash)` *(live, 5 logs — also emitted by L1Nullifier, see §1.6)* |
| `0xa1846a4248529db592da99da276f761d9f37a84d0f3d4e83819b869759000700` | `LegacyDepositInitiated(uint256 indexed chainId, bytes32 indexed l2DepositTxHash, address indexed from, address to, address l1Token, uint256 amount)` — legacy-shaped deposit (back-compat). |
| `0x4250817d22c13fba8067153d85ccd9706326ac2bd14d5c3898c8b1bccc440658` | `ClaimedFailedDepositAssetRouter(uint256 indexed chainId, bytes32 indexed assetId, bytes assetData)` — failed deposit refunded. |
| `0x14c1bae9bcc3777747463b66a36584aa75e4ded1aa38089f447beecb125a2175` | `AssetDeploymentTrackerSet(bytes32 indexed assetId, address indexed assetDeploymentTracker, bytes32 indexed additionalData)` |
| `0x31a15cb4f69820f57afabeaff74feae31dc25875c07c952ba742a3acf8690f91` | `BridgehubMintData(bytes bridgeMintData)` |

### 1.6 L1Nullifier (ex-SharedBridge ledger; finalization / replay protection) — emitter `0xd7f9…b2cb`

| topic0 | Event |
|--------|-------|
| `0xe4def01b981193a97a9e81230d7b9f31812ceaf23f864a828a82c687911cb2df` | `BridgehubDepositFinalized(uint256 indexed chainId, bytes32 indexed txDataHash, bytes32 indexed l2DepositTxHash)` *(live, 5 logs)* — **same topic0 as the AssetRouter event in §1.5; disambiguate by emitter address.** |

> The Nullifier holds the historical SharedBridge address `0xD7f9…b2cb` (the ZKsync docs still label this "Shared Bridge"). Functionally it is now the **withdrawal-finalization / nullifier ledger**; it is **not** the active router.

### 1.7 L1NativeTokenVault (token escrow) — emitter `0xbed1…11f6`

| topic0 | Event |
|--------|-------|
| `0xbc0f4055a7869d8ecad34b33382a0bc181c5811565fec42f335505be5fd661d2` | `BridgeMint(uint256 indexed chainId, bytes32 indexed assetId, address receiver, uint256 amount)` *(live, 61 logs / 5k blk)* — tokens released to L1 on withdrawal-finalize. |
| `0x1cd02155ad1064c60598a8bd0e4e795d7e7d0a0f3c38aad04d261f1297fb2545` | `BridgeBurn(uint256 indexed chainId, bytes32 indexed assetId, address indexed sender, address receiver, uint256 amount)` *(live, 118 logs)* — tokens escrowed on deposit. |
| `0x5ed5e4f58bf9a324a38beaa1177fb96fcb7bf3a5f4c4585ebb78c4a8c0249d0f`† | `TokenBeaconUpdated(address indexed l2TokenBeacon)` — bridged-token beacon proxy pointer changed. |

† `TokenBeaconUpdated` topic0 recomputed from the interface signature; not observed in the sampled window (low-frequency admin event).

### 1.8 L1ERC20Bridge (legacy, dormant) — emitter `0x5789…e063`

| topic0 | Event |
|--------|-------|
| `0xdd341179f4edc78148d894d0213a96d212af2cbaf223d19ef6d483bdd47ab81d`† | `DepositInitiated(bytes32 indexed l2DepositTxHash, address indexed from, address indexed to, address l1Token, uint256 amount)` |
| `0xac1b18083978656d557d6e91c88203585cfda1031bdb14538327121ef140d383` | `WithdrawalFinalized(address indexed to, address indexed l1Token, uint256 amount)` |
| `0xbe066dc591f4a444f75176d387c3e6c775e5706d9ea9a91d11eb49030c66cf60`† | `ClaimedFailedDeposit(address indexed to, address indexed l1Token, uint256 amount)` |

† These legacy topics were recomputed locally; the bridge emitted **0 logs** in the sampled 5k-block window (deposits migrated to the AssetRouter). Documented for historical back-fill only.

### 1.9 ValidatorTimelock — emitter `0xdc26…539d`

| topic0 | Event |
|--------|-------|
| `0x7429a06e9412e469f0d64f9d222640b0af359f556b709e2913588c227851b88d` | `ValidatorAdded(uint256 indexed _chainId, address _addedValidator)` |
| `0x7126bef88d1149ccdff9681ed5aecd3ba5ae70c96517551de250af09cebd1a0b` | `ValidatorRemoved(uint256 indexed _chainId, address _removedValidator)` |
| `0xd32d6d626bb9c7077c559fc3b4e5ce71ef14609d7d216d030ee63dcf2422c2c4` | `NewExecutionDelay(uint256 _newExecutionDelay)` |

### 1.10 Transparent-proxy / standard constants (ecosystem proxies)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | OZ TransparentUpgradeableProxy impl pointer changed (BridgeHub / AssetRouter / Nullifier / NTV / CTM / L1ERC20Bridge). **Watch to catch impl rotations.** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | proxy admin rotation. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All selectors below verified **present** in the live facet/proxy bytecode on 2026-06-09 (facet membership confirmed via the Diamond's `facets()` output).

### 2.1 BridgeHub (`0x303a…5213`) — L1→L2 entry + registry

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd52471c1` | `requestL2TransactionDirect((uint256,uint256,address,uint256,bytes,uint256,uint256,bytes[],address))` | Single-bridge L1→L2 request (ETH-base flows). |
| `0x7827d314` | `requestL2TransactionTwoBridges((uint256,uint256,uint256,address,uint256,address,uint256,bytes))` | Two-bridge L1→L2 (token + base) request. |
| `0x71623274` | `l2TransactionBaseCost(uint256,uint256,uint256,uint256)` → `uint256` | Base cost incl. chainId. |
| `0xe680c4c1` | `getZKChain(uint256 chainId)` → `address` | **Era 324 → `0x3240…0324`** (verified). |
| `0xdead6f7f` | `getHyperchain(uint256 chainId)` → `address` | Legacy alias of `getZKChain`. |
| `0x59ec65a2` | `baseToken(uint256 chainId)` → `address` | **Era → `address(1)` = ETH** (verified). |
| `0xbc0aac10` | `assetRouter()` → `address` | → L1AssetRouter `0x8829…ce56`. |
| `0x38720778` | `sharedBridge()` → `address` | back-compat getter, also returns `0x8829…ce56`. |
| `0xd4b9f4fa` | `messageRoot()` → `address` | → `0x5ce9…b4ad`. |
| `0x9d5bd3da` | `chainTypeManager(uint256 chainId)` → `address` | **Era → `0xc2ee…5f5c`** (verified). |
| `0xcbe83612` | `l1CtmDeployer()` → `address` | → `0x6078…9860`. |
| `0x8da5cb5b` | `owner()` → `address` | → Governance `0xe30d…5ab3`. |
| `0xf851a440` | `admin()` → `address` | → ChainAdmin-style admin `0x2cf3…5063`. |

### 2.2 MailboxFacet (Diamond `0x3240…0324`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd52471c1` | `requestL2TransactionDirect((uint256,uint256,address,uint256,bytes,uint256,uint256,bytes[],address))` | Emits `NewPriorityRequest`. |
| `0x7827d314` | `requestL2TransactionTwoBridges((uint256,uint256,uint256,address,uint256,address,uint256,bytes))` | |
| `0x6c0960f9` | `finalizeEthWithdrawal(uint256,uint256,uint16,bytes,bytes32[])` | Claim an ETH withdrawal on L1. |
| `0xb473318e` | `l2TransactionBaseCost(uint256,uint256,uint256)` → `uint256` | Per-chain base cost (3-arg, on the Diamond). |
| `0xe4948f43` | `proveL2MessageInclusion(uint256,uint256,(uint16,address,bytes),bytes32[])` → `bool` | Merkle-prove an L2→L1 message. |
| `0x263b7f8e` | `proveL2LogInclusion(uint256,uint256,(uint8,bool,uint16,address,bytes32,bytes32),bytes32[])` → `bool` | |
| `0x042901c7` | `proveL1ToL2TransactionStatus(bytes32,uint256,uint256,uint16,bytes32[],uint8)` → `bool` | Used by `claimFailedDeposit`. |

### 2.3 ExecutorFacet (Diamond `0x3240…0324`) — validator entrypoints (called via ValidatorTimelock)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0b6db820` | `precommitSharedBridge(address chainAddress, uint256 batchNumber, bytes precommitData)` | Interop pre-commitment. |
| `0x0db9eb87` | `commitBatchesSharedBridge(address chainAddress, uint256 processFrom, uint256 processTo, bytes commitData)` | Emits `BlockCommit`. **Confirmed live as the selector the ValidatorTimelock calls.** |
| `0x9271e450` | `proveBatchesSharedBridge(address chainAddress, uint256 processBatchFrom, uint256 processBatchTo, bytes proofData)` | Emits `BlocksVerification`. |
| `0xa085344d` | `executeBatchesSharedBridge(address chainAddress, uint256 processFrom, uint256 processTo, bytes executeData)` | Emits `BlockExecution`. |
| `0x7ca4eff7` | `revertBatchesSharedBridge(address chainAddress, uint256 newLastBatch)` | Emits `BlocksRevert`. |

> These are the **only 5 selectors** on the Executor facet (`0x0597caa8…`). The argument list is the **post-Gateway `…SharedBridge(address,…)` form** — the older `commitBatches(...)`/`commitBatchesSharedBridge(uint256,...)` variants hash differently and are absent here.

### 2.4 GettersFacet (Diamond `0x3240…0324`) — read state

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x7a0ed627` | `facets()` | `Facet[]` — the EIP-2535 facet map. **4 facets on Era.** |
| `0x6e9960c3` | `getAdmin()` | `address` — ChainAdmin `0x2cf3…5063`. |
| `0x46657fe9` | `getVerifier()` | `address` — `0xcd27…7a45`. |
| `0x3591c1a0` | `getBridgehub()` | `address` — `0x303a…5213`. |
| `0x98acd7a6` | `getBaseToken()` | `address` — `0x…01` (ETH). |
| `0x33ce93fe` | `getProtocolVersion()` | `uint256` — live `0x1d00000004`. |
| `0xdb1f0bf9` | `getTotalBatchesCommitted()` | `uint256` |
| `0xef3f0bae` | `getTotalBatchesVerified()` | `uint256` |
| `0xb8c2f66f` | `getTotalBatchesExecuted()` | `uint256` |
| `0xa1954fc5` | `getTotalPriorityTxs()` | `uint256` |
| `0x631f4bac` | `getPriorityQueueSize()` | `uint256` |
| `0x79823c9a` | `getFirstUnprocessedPriorityTx()` | `uint256` |

### 2.5 AdminFacet (Diamond `0x3240…0324`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4dd18bf5` | `setPendingAdmin(address)` | Emits `NewPendingAdmin`. |
| `0x27ae4c16` | `freezeDiamond()` | Emits `Freeze()`. |
| `0x17338945` | `unfreezeDiamond()` | Emits `Unfreeze()`. |

### 2.6 L1AssetRouter / L1Nullifier / L1NativeTokenVault / L1ERC20Bridge — key getters & flows

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xe60ccaba` | `L1_NULLIFIER()` → `address` | AssetRouter → `0xd7f9…b2cb`. |
| `0x64e130cf` | `nativeTokenVault()` → `address` | AssetRouter → `0xbed1…11f6`. |
| `0x6e9d7899` | `legacyBridge()` → `address` | AssetRouter/Nullifier → `0x5789…e063`. |
| `0x5d4edca7` | `BRIDGE_HUB()` → `address` | AssetRouter → `0x303a…5213`. |
| `0x11a2ccc1` | `finalizeWithdrawal(uint256,uint256,uint16,bytes,bytes32[])` | L1ERC20Bridge (legacy). Distinct from Mailbox `finalizeEthWithdrawal` `0x6c0960f9`. |
| `0xe8b99b1b` | `deposit(address,address,uint256,uint256,uint256,address)` → `bytes32` | L1ERC20Bridge (legacy) — multi-arg deposit; not used by the active flow. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. The ecosystem addresses were read **directly from the on-chain BridgeHub** (`assetRouter()`, `messageRoot()`, `chainTypeManager(324)`, `getZKChain(324)`, `l1CtmDeployer()`) and from the AssetRouter (`L1_NULLIFIER()`, `nativeTokenVault()`, `legacyBridge()`), then cross-checked against the official ZKsync L1-contracts docs.

### 3.1 Chain (zkSync Era, chain 324) — EIP-2535 Diamond

| Role | Address | One-liner |
|------|---------|-----------|
| **DiamondProxy (Era)** | `0x32400084C286CF3E17e7B677ea9583e60a000324` | The zkSync Era chain contract; emits §1.1/1.2/1.3 events. Vanity `…000324`. |
| MailboxFacet | `0x1e34ab39a9682149165ddecc0583d238a5448b45` | L1→L2 priority queue, withdrawal finalization, inclusion proofs. |
| GettersFacet | `0x1666124221622eb6154306ea9ba87043e8be88b2` | Read-only state (`facets()`, batch counts, version). |
| ExecutorFacet | `0x0597caa8a823a699d7cd9e62b5e5d4153ff82691` | commit/prove/execute/revert/precommit batches. |
| AdminFacet | `0x37cefd5b44c131fef27e9bc542e5b77a177a7253` | freeze, admin, fee-param, upgrade. |
| Verifier | `0xcd279bd537c8e1a1acc46ac2205bebd8902f7a45` | ZK proof verifier (read from `getVerifier()`). |

### 3.2 Ecosystem hub & bridging

| Role | Address | One-liner |
|------|---------|-----------|
| **BridgeHub** (proxy) | `0x303a465B659cBB0ab36eE643eA362c509EEb5213` | Elastic-Network registry + L1→L2 router; §1.4 events. |
| **L1AssetRouter** (ex-L1SharedBridge, proxy) | `0x8829AD80E425C646DAB305381ff105169FeEcE56` | **Active** ERC-20/base-token routing; §1.5 events (highest volume). |
| **L1Nullifier** (ex-SharedBridge ledger, proxy) | `0xD7f9f54194C633F36CCD5F3da84ad4a1c38cB2cB` | Withdrawal finalization / replay protection; the docs still call this "Shared Bridge". |
| **L1NativeTokenVault** (proxy) | `0xbeD1EB542f9a5aA6419Ff3deb921A372681111f6` | Token escrow; emits `BridgeMint`/`BridgeBurn` (§1.7). |
| **L1ERC20Bridge** (legacy, proxy) | `0x57891966931eb4bb6fb81430e6ce0a03aabde063` | Old ERC-20 bridge — **deployed but dormant** (0 logs / 5k blk). |
| **ChainTypeManager** (ex-StateTransitionManager, proxy) | `0xc2eE6b6af7d616f6e27ce7F4A451aedc2b0F5f5C` | Deploys/manages ZK chains; `chainTypeManager(324)`. |
| **MessageRoot** (proxy) | `0x5cE9257755391d1509cD4ec1899D3F88a57bb4ad` | Cross-chain message aggregation root. |
| L1CtmDeployer | `0x6078f6B379F103de1aA912dC46bb8df0c8809860` | Deterministic CTM/asset deployer. |

### 3.3 Operations & governance

| Role | Address | One-liner |
|------|---------|-----------|
| **ValidatorTimelock** | `0xdc26b08f0335b68721f64001c38B05d0bC9B539D` | Wraps `commit/prove/execute`; enforces an execution delay. The tx-`to` for batch ops. `owner()` = `0x4e49…7828`. |
| **ChainAdmin (Era)** | `0x2cF3bD6a9056b39999f3883955E183f655345063` | Era's `getAdmin()`; `owner()` = `0x4e49…7828`. |
| **Governance** | `0xe30dca3047b37dc7D88849De4A4Dc07937ad5ab3` | Protocol-upgrade governor; owner of BridgeHub & ProxyAdmin. |
| **ProxyAdmin** | `0xc2a36181fb524a6BEFE639aFEd37A67e77d62Cf1` | OZ `ProxyAdmin` for **all** ecosystem transparent proxies; `owner()` = Governance `0xe30d…5ab3`. |
| ML admin multisig | `0x4e4943346848c4867F81dFb37c4cA9C5715A7828` | Owns ValidatorTimelock + ChainAdmin. |
| Era validator (operator EOA) | `0xc75CdcBEEf3aE3365abf0217815748586f9047f1` | Submits batches through the ValidatorTimelock. |

> **Base token of Era = ETH** (`baseToken(324) = 0x…01`). ETH deposits/withdrawals dominate; ERC-20s route via AssetRouter + NativeTokenVault.

---

## 4. Addresses — other six requested chains (Base, BNB, Avalanche, Arbitrum, Optimism, Polygon)

**None of the zkSync native-bridge contracts is deployed on any of these chains.** `eth_getCode` returned `0x` (empty) on 2026-06-09 for every one of `DiamondProxy`, `BridgeHub`, `L1AssetRouter`, `L1Nullifier`, `L1NativeTokenVault` and `L1ERC20Bridge` on:

| Chain | ID | RPC | Result |
|---|---|---|---|
| Base | 8453 | base-rpc.publicnode.com | all `0x` |
| BNB Smart Chain | 56 | bsc-rpc.publicnode.com | all `0x` |
| Avalanche C-Chain | 43114 | avalanche-c-chain-rpc.publicnode.com | all `0x` |
| Arbitrum One | 42161 | arbitrum-one-rpc.publicnode.com | all `0x` |
| Optimism | 10 | optimism-rpc.publicnode.com | all `0x` |
| Polygon PoS | 137 | polygon-bor-rpc.publicnode.com | all `0x` |

The native bridge is **Ethereum-L1-anchored**: ZKsync settles to Ethereum, not to any of these L2s. (The Elastic Network can settle ZK chains to a **Gateway** settlement layer, but that is a ZK chain, not any of the seven.)

---

## 5. Addresses — zkSync Era L2 (chain ID 324) — the counterparty (OUTSIDE the seven)

zkSync Era (324) is the L2 counterparty. Recorded here as a finding (it is not one of the seven target chains). Its L2 system contracts live at **fixed canonical addresses** (`0x…0001x` / `0x…800x`), all verified live via `eth_getCode` on `https://mainnet.era.zksync.io` (chainId 324 confirmed) on 2026-06-09.

| Role | Address | Code |
|------|---------|------|
| L2 Bridgehub | `0x0000000000000000000000000000000000010002` | 63,520 B |
| L2AssetRouter | `0x0000000000000000000000000000000000010003` | 42,528 B |
| L2NativeTokenVault | `0x0000000000000000000000000000000000010004` | 68,192 B |
| L2MessageRoot | `0x0000000000000000000000000000000000010005` | 31,328 B |
| L2BaseToken (ETH) system | `0x000000000000000000000000000000000000800A` | 7,584 B |
| L1Messenger (L2→L1 msgs) | `0x0000000000000000000000000000000000008008` | 14,688 B |
| L2 legacy ERC-20 bridge | `0x11f943b2c77b743AB90f4A0Ae7d5A4e7FCA3E102` | 11,872 B |

---

## 6. Cross-chain summary

| Chain | ID | DiamondProxy (Era) | BridgeHub | L1AssetRouter | L1Nullifier | L1NTV | L1ERC20Bridge |
|---|---|---|---|---|---|---|---|
| **Ethereum** | 1 | ✅ `0x3240…0324` | ✅ `0x303a…5213` | ✅ `0x8829…ce56` | ✅ `0xd7f9…b2cb` | ✅ `0xbed1…11f6` | ✅ `0x5789…e063` (dormant) |
| Base | 8453 | — | — | — | — | — | — |
| BNB | 56 | — | — | — | — | — | — |
| Avalanche | 43114 | — | — | — | — | — | — |
| Arbitrum One | 42161 | — | — | — | — | — | — |
| Optimism | 10 | — | — | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — | — | — |
| *zkSync Era* | *324* | *(L2 system contracts §5 — outside the seven)* | | | | | |

**Vanity tell:** the Era DiamondProxy ends in `…a000324` (chain id 324). No other contract uses a vanity address. Everything is Ethereum-L1-only of the seven; the only non-Ethereum counterparty is zkSync Era (324), outside the set.

---

## 7. Proxies (old & new)

EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. All impl/admin values below read **live** from these slots on 2026-06-09.

| Contract | Pattern | Live impl | Detection / admin |
|----------|---------|-----------|-------------------|
| **DiamondProxy (Era)** | **EIP-2535 Diamond** | n/a (4 facets, §3.1) | `facets()` returns 4 facets; EIP-1967 impl slot is **empty**; dispatch by selector. Upgrade auth = ChainAdmin `0x2cf3…5063` + ChainTypeManager. Watch `ExecuteUpgrade` (`0xce6f42f7…`). |
| **BridgeHub** | OZ TransparentUpgradeableProxy | `0xc89423b4909080fb8f8a43df5e1c27001e55c24b` | impl slot set; admin slot = ProxyAdmin `0xc2a3…2cf1`. |
| **L1AssetRouter** | OZ Transparent proxy | `0x2386bc2e26f39b72f0d4fde0c07d68e4eeffc725` | admin = `0xc2a3…2cf1`. |
| **L1Nullifier** | OZ Transparent proxy | `0x71759c4ea628293f5a99aab1585df1c8da4718e0` | admin = `0xc2a3…2cf1`. |
| **L1NativeTokenVault** | OZ Transparent proxy | `0x8e1c5a8c5d8c33ed0ec756d6f4006f2d875ba083` | admin = `0xc2a3…2cf1`. |
| **L1ERC20Bridge** | OZ Transparent proxy | `0x6ed98623e0b51be68748ab5091aa891adb883e13` | admin = `0xc2a3…2cf1`. |
| **ChainTypeManager** | OZ Transparent proxy | `0x4ab7204e4205c96c32e23ada9191720976dc084f` | admin = `0xc2a3…2cf1`; `owner()` = Governance `0xe30d…5ab3`. |
| **ValidatorTimelock** | OZ Transparent proxy | `0xc954b4d51031870624f3e779ead14c57249c111d` | 2,840 B proxy; impl slot set; admin = a **dedicated** ProxyAdmin `0x0d8d1be440f997bdb9ca44c0140fd12551f99bbb` (separate from the ecosystem `0xc2a3…2cf1`), itself `owner()` = ML multisig `0x4e49…7828`; the proxy's `owner()` (via impl) = `0x4e49…7828`. |
| **Governance** | OZ Transparent proxy | `0x36625bd3ddb469377c6e9893712158ca3c0cc14b` | 1,129 B proxy; impl slot set; admin slot = `0x1e4c534e7ce1ff5621ea506d99b367d7d8efbe3e`. |
| **ChainAdmin / ProxyAdmin** | **immutable** (no proxy) | — | plain contracts; impl slot empty. |

> The single `ProxyAdmin` `0xc2a3…2cf1` is the upgrade authority for **all six** ecosystem transparent proxies (verified: every one returned the same admin-slot value). Its `owner()` = Governance `0xe30d…5ab3`. Watch `Upgraded(address)` topic `0xbc7cd75a…` on each proxy and `AdminChanged` `0x7e644d79…` for admin rotations. **Always read the live EIP-1967 slot — never hard-code an impl.**

---

## 8. Detection invariants & gotchas

1. **All native-bridge contracts are Ethereum-L1-only of the seven.** Base/BNB/Avalanche/Arbitrum/Optimism/Polygon return `0x` for every address (§4). The L2 counterparty is **zkSync Era 324**, outside the set (§5).
2. **Deposits = `NewPriorityRequest` (`0x4531cd57…`) on the Era DiamondProxy `0x3240…0324`** — the canonical L1→L2 event. Its signature has a **nested 17-field tuple with a `uint256[4]`**; the naive form does not hash. Pair with `NewPriorityRequestId` (`0x779f4416…`) for a cheap indexed `txHash` filter.
3. **The cross-chain key is `txHash` (L2 canonical tx hash) / batchNumber, never `tx.from`.** Deposits are often relayed; the real user is in the event payload (`from` field of the tuple), not the sender.
4. **`L1AssetRouter` (`0x8829…ce56`) is the active bridge; `L1Nullifier` (`0xd7f9…b2cb`) is the renamed legacy SharedBridge ledger; `L1ERC20Bridge` (`0x5789…e063`) is dormant.** Index the AssetRouter + NativeTokenVault for live token flow. The ZKsync docs still label `0xd7f9…` "Shared Bridge" — it is the Nullifier (finalization/replay ledger), confirmed via `BridgeHub.l1Nullifier()`.
5. **`BridgehubDepositFinalized` topic0 `0xe4def01b…` is emitted by BOTH the AssetRouter and the L1Nullifier** — disambiguate by emitter address (§1.5 vs §1.6).
6. **Highest-volume deposit event is `BridgehubDepositBaseTokenInitiated` (`0x0f87e1ea…`, 113 logs / 5k blk)** because Era's base token is ETH and most deposits are ETH. Non-base-token deposits fire the rarer `BridgehubDepositInitiated` (`0xe21913bc…`).
7. **Withdrawal-finalize fires `BridgeMint` (`0xbc0f4055…`) on the NativeTokenVault + `DepositFinalizedAssetRouter` (`0x44eb9a84…`) on the AssetRouter**; deposit escrow fires `BridgeBurn` (`0x1cd02155…`). Both topic0s are NTV-specific.
8. **The Era chain is an EIP-2535 Diamond, not an EIP-1967 proxy** — its impl slot is empty. To enumerate logic, call `facets()` (4 facets) or `facetAddress(bytes4)`; the impl can only "change" via a facet cut (`ExecuteUpgrade` `0xce6f42f7…`). Watching the EIP-1967 slot will mislead you.
9. **Batch ops are routed through the ValidatorTimelock (`0xdc26…539d`), so `tx.to` for `BlockCommit`/`BlockExecution` is the timelock, not the Diamond.** The validator EOA is `0xc75c…47f1`. Executor selectors are the `…SharedBridge(address,uint256,uint256,bytes)` form (`commit 0x0db9eb87`, `prove 0x9271e450`, `execute 0xa085344d`).
10. **Event names say "Block" but params are batchNumber** (`BlockCommit`/`BlockExecution`). Pre-rename nomenclature; not per-L2-block.
11. **`BlocksRevert` (`0x8bd4b15e…`) and `Freeze()` (`0x615acbae…`) are emergency/risk signals.** A revert rolls back committed batches; a freeze halts the chain.
12. **One ProxyAdmin (`0xc2a3…2cf1`) governs all six ecosystem proxies.** A single `Upgraded`/`AdminChanged` on it, or any impl-slot change, is a protocol-wide upgrade signal. The Diamond is upgraded separately (facet cut + ChainAdmin/CTM).
13. **`getZKChain(chainId)` on the BridgeHub is the authoritative way to find any ZK chain's DiamondProxy** (`getZKChain(324) = 0x3240…0324`). New chains register via `NewChain` (`0x1e9125bc…`).
14. **Protocol version is packed** (`getProtocolVersion()` = `0x1d00000004` ⇒ minor 29, patch 4). A version bump usually accompanies a Diamond facet cut.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- MailboxFacet (Diamond) — deposits / priority queue
TOPIC_NEW_PRIORITY_REQUEST        = '\x4531cd5795773d7101c17bdeb9f5ab7f47d7056017506f937083be5d6e77a382'
TOPIC_NEW_PRIORITY_REQUEST_ID     = '\x779f441679936c5441b671969f37400b8c3ed0071cb47444431bf985754560df'
TOPIC_NEW_RELAYED_PRIORITY_TX     = '\x0137d2eaa6ec5b7e4f233f6d6f441410014535d0f3985367994c94bf15a2a564'
-- ExecutorFacet (Diamond) — batch lifecycle
TOPIC_BLOCK_COMMIT                = '\x8f2916b2f2d78cc5890ead36c06c0f6d5d112c7e103589947e8e2f0d6eddb763'
TOPIC_BLOCKS_VERIFICATION         = '\x22c9005dd88c18b552a1cd7e8b3b937fcde9ca69213c1f658f54d572e4877a81'
TOPIC_BLOCK_EXECUTION             = '\x2402307311a4d6604e4e7b4c8a15a7e1213edb39c16a31efa70afb06030d3165'
TOPIC_BLOCKS_REVERT               = '\x8bd4b15ea7d1bc41ea9abc3fc487ccb89cd678a00786584714faa9d751c84ee5'
TOPIC_BATCH_PRECOMMITMENT_SET     = '\xfea115cea8c7414dc6c05dfb20821e4ea72c37b91e666a90ab4ddb5eabade850'
-- AdminFacet (Diamond)
TOPIC_EXECUTE_UPGRADE             = '\xce6f42f7ce46cd12c695bbee4503fdd959206cdbb95fb3c37ebfe262cfffac2b'
TOPIC_FREEZE                      = '\x615acbaede366d76a8b8cb2a9ada6a71495f0786513d71aa97aaf0c3910b78de'
TOPIC_UNFREEZE                    = '\x2f05ba71d0df11bf5fa562a6569d70c4f80da84284badbe015ce1456063d0ded'
TOPIC_NEW_PENDING_ADMIN           = '\xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9'
TOPIC_NEW_ADMIN                   = '\xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc'
-- BridgeHub
TOPIC_NEW_CHAIN                   = '\x1e9125bc72db22c58abff6821d7333551967e26454b419ffa958e4cb8ef47600'
TOPIC_BASE_TOKEN_ASSETID_REG      = '\x3df150949161462acf3be30521d7da9e533b247327a254e55dd01875897a6df3'
TOPIC_SETTLEMENT_LAYER_REG        = '\x02629feb109d94b16a367231d248ba81c462f51ce5b984835f150f1c9f49ed25'
TOPIC_ASSET_REGISTERED            = '\x8f09d7694a9ae17acec5cf132d594d7eee23572f7fe132396ce72b1afbf7ef20'
-- L1AssetRouter (active ERC-20/base-token)
TOPIC_BH_DEPOSIT_BASE_TOKEN_INIT  = '\x0f87e1ea5eb1f034a6071ef630c174063e3d48756f853efaaf4292b929298240'
TOPIC_BH_DEPOSIT_INITIATED        = '\xe21913bc89c1320d9709a5d236ffe06b54cf88aecfc9509ebd68f1adba45781e'
TOPIC_DEPOSIT_FINALIZED_AR        = '\x44eb9a840094a49b3cd0a5205042598a1c08c4e87bafb5760bc2d8efa170c541'
TOPIC_BH_DEPOSIT_FINALIZED        = '\xe4def01b981193a97a9e81230d7b9f31812ceaf23f864a828a82c687911cb2df'  -- also L1Nullifier
TOPIC_LEGACY_DEPOSIT_INITIATED    = '\xa1846a4248529db592da99da276f761d9f37a84d0f3d4e83819b869759000700'
TOPIC_CLAIMED_FAILED_DEPOSIT_AR   = '\x4250817d22c13fba8067153d85ccd9706326ac2bd14d5c3898c8b1bccc440658'
TOPIC_ASSET_DEPLOY_TRACKER_SET    = '\x14c1bae9bcc3777747463b66a36584aa75e4ded1aa38089f447beecb125a2175'
TOPIC_BRIDGEHUB_MINT_DATA         = '\x31a15cb4f69820f57afabeaff74feae31dc25875c07c952ba742a3acf8690f91'
-- L1NativeTokenVault
TOPIC_NTV_BRIDGE_MINT             = '\xbc0f4055a7869d8ecad34b33382a0bc181c5811565fec42f335505be5fd661d2'
TOPIC_NTV_BRIDGE_BURN             = '\x1cd02155ad1064c60598a8bd0e4e795d7e7d0a0f3c38aad04d261f1297fb2545'
-- L1ERC20Bridge (legacy, dormant)
TOPIC_L1ERC20_DEPOSIT_INITIATED   = '\xdd341179f4edc78148d894d0213a96d212af2cbaf223d19ef6d483bdd47ab81d'
TOPIC_L1ERC20_WITHDRAWAL_FINAL    = '\xac1b18083978656d557d6e91c88203585cfda1031bdb14538327121ef140d383'
TOPIC_L1ERC20_CLAIMED_FAILED_DEP  = '\xbe066dc591f4a444f75176d387c3e6c775e5706d9ea9a91d11eb49030c66cf60'
-- ValidatorTimelock
TOPIC_VALIDATOR_ADDED             = '\x7429a06e9412e469f0d64f9d222640b0af359f556b709e2913588c227851b88d'
TOPIC_VALIDATOR_REMOVED           = '\x7126bef88d1149ccdff9681ed5aecd3ba5ae70c96517551de250af09cebd1a0b'
TOPIC_NEW_EXECUTION_DELAY         = '\xd32d6d626bb9c7077c559fc3b4e5ce71ef14609d7d216d030ee63dcf2422c2c4'
-- Transparent-proxy standard
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED               = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'

-- ===== Selectors =====
-- BridgeHub
SEL_REQUEST_L2_TX_DIRECT          = '\xd52471c1'
SEL_REQUEST_L2_TX_TWO_BRIDGES     = '\x7827d314'
SEL_BH_L2_TX_BASE_COST            = '\x71623274'
SEL_GET_ZK_CHAIN                  = '\xe680c4c1'
SEL_BASE_TOKEN                    = '\x59ec65a2'
SEL_ASSET_ROUTER                  = '\xbc0aac10'
SEL_SHARED_BRIDGE                 = '\x38720778'
SEL_MESSAGE_ROOT                  = '\xd4b9f4fa'
SEL_CHAIN_TYPE_MANAGER            = '\x9d5bd3da'
-- Mailbox (Diamond)
SEL_FINALIZE_ETH_WITHDRAWAL       = '\x6c0960f9'
SEL_L2_TX_BASE_COST               = '\xb473318e'
SEL_PROVE_L2_MESSAGE_INCLUSION    = '\xe4948f43'
SEL_PROVE_L2_LOG_INCLUSION        = '\x263b7f8e'
SEL_PROVE_L1_TO_L2_TX_STATUS      = '\x042901c7'
-- Executor (Diamond) — via ValidatorTimelock
SEL_PRECOMMIT_BATCHES             = '\x0b6db820'
SEL_COMMIT_BATCHES                = '\x0db9eb87'
SEL_PROVE_BATCHES                 = '\x9271e450'
SEL_EXECUTE_BATCHES               = '\xa085344d'
SEL_REVERT_BATCHES                = '\x7ca4eff7'
-- Getters (Diamond)
SEL_FACETS                        = '\x7a0ed627'
SEL_GET_PROTOCOL_VERSION          = '\x33ce93fe'
SEL_GET_TOTAL_BATCHES_COMMITTED   = '\xdb1f0bf9'
SEL_GET_TOTAL_BATCHES_EXECUTED    = '\xb8c2f66f'
SEL_GET_TOTAL_PRIORITY_TXS        = '\xa1954fc5'
-- Admin (Diamond)
SEL_FREEZE_DIAMOND                = '\x27ae4c16'
SEL_UNFREEZE_DIAMOND              = '\x17338945'
SEL_SET_PENDING_ADMIN             = '\x4dd18bf5'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT                 = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses — Ethereum mainnet (chain 1) =====
-- Chain (Era, 324) — Diamond + facets
ETH_ERA_DIAMOND_PROXY             = '\x32400084c286cf3e17e7b677ea9583e60a000324'
ETH_ERA_MAILBOX_FACET             = '\x1e34ab39a9682149165ddecc0583d238a5448b45'
ETH_ERA_GETTERS_FACET             = '\x1666124221622eb6154306ea9ba87043e8be88b2'
ETH_ERA_EXECUTOR_FACET            = '\x0597caa8a823a699d7cd9e62b5e5d4153ff82691'
ETH_ERA_ADMIN_FACET               = '\x37cefd5b44c131fef27e9bc542e5b77a177a7253'
ETH_ERA_VERIFIER                  = '\xcd279bd537c8e1a1acc46ac2205bebd8902f7a45'
-- Ecosystem hub & bridging
ETH_BRIDGEHUB                     = '\x303a465b659cbb0ab36ee643ea362c509eeb5213'
ETH_L1_ASSET_ROUTER               = '\x8829ad80e425c646dab305381ff105169feece56'
ETH_L1_NULLIFIER                  = '\xd7f9f54194c633f36ccd5f3da84ad4a1c38cb2cb'
ETH_L1_NATIVE_TOKEN_VAULT         = '\xbed1eb542f9a5aa6419ff3deb921a372681111f6'
ETH_L1_ERC20_BRIDGE_LEGACY        = '\x57891966931eb4bb6fb81430e6ce0a03aabde063'
ETH_CHAIN_TYPE_MANAGER            = '\xc2ee6b6af7d616f6e27ce7f4a451aedc2b0f5f5c'
ETH_MESSAGE_ROOT                  = '\x5ce9257755391d1509cd4ec1899d3f88a57bb4ad'
ETH_L1_CTM_DEPLOYER               = '\x6078f6b379f103de1aa912dc46bb8df0c8809860'
-- Ops & governance
ETH_VALIDATOR_TIMELOCK            = '\xdc26b08f0335b68721f64001c38b05d0bc9b539d'
ETH_ERA_CHAIN_ADMIN               = '\x2cf3bd6a9056b39999f3883955e183f655345063'
ETH_GOVERNANCE                    = '\xe30dca3047b37dc7d88849de4a4dc07937ad5ab3'
ETH_PROXY_ADMIN                   = '\xc2a36181fb524a6befe639afed37a67e77d62cf1'
ETH_ML_ADMIN_MULTISIG             = '\x4e4943346848c4867f81dfb37c4ca9c5715a7828'

-- ===== Addresses — zkSync Era L2 (chain 324, OUTSIDE the seven) =====
L2_BRIDGEHUB                      = '\x0000000000000000000000000000000000010002'
L2_ASSET_ROUTER                   = '\x0000000000000000000000000000000000010003'
L2_NATIVE_TOKEN_VAULT             = '\x0000000000000000000000000000000000010004'
L2_MESSAGE_ROOT                   = '\x0000000000000000000000000000000000010005'
L2_BASE_TOKEN_SYSTEM              = '\x000000000000000000000000000000000000800a'
L2_L1_MESSENGER                   = '\x0000000000000000000000000000000000008008'
L2_LEGACY_ERC20_BRIDGE            = '\x11f943b2c77b743ab90f4a0ae7d5a4e7fca3e102'
```

---

## 10. Verification & sources

How every constant was verified (2026-06-09):

- **Addresses (discovery):** the ecosystem set was read **directly on-chain** from the live BridgeHub `0x303a…5213` — `assetRouter()=0x8829…ce56`, `messageRoot()=0x5ce9…b4ad`, `chainTypeManager(324)=0xc2ee…5f5c`, `getZKChain(324)=0x3240…0324`, `l1CtmDeployer()=0x6078…9860`, `owner()=0xe30d…5ab3`, `admin()=0x2cf3…5063` — then from the L1AssetRouter (`L1_NULLIFIER()=0xd7f9…b2cb`, `nativeTokenVault()=0xbed1…11f6`, `legacyBridge()=0x5789…e063`). Cross-checked against the official ZKsync L1-contracts / ZK-chain-addresses docs (which independently list DiamondProxy, BridgeHub, L1AssetRouter, L1NativeTokenVault, and the "Shared Bridge" `0xD7f9…`).
- **Existence:** `eth_getCode` returned non-empty bytecode for every Ethereum address; `0x` (empty) for all six other target chains (§4) and live multi-KB bytecode for the L2 (324) system contracts (§5).
- **Diamond facets:** `facets()` on the DiamondProxy returned **4 facets**; each facet's selector list was classified against the canonical `matter-labs/era-contracts` interface signatures, mapping `0x1e34…` → Mailbox, `0x1666…` → Getters, `0x0597…` → Executor, `0x037c…` → Admin. `getProtocolVersion()` = `0x1d00000004`.
- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from the era-contracts `IExecutor`/`IMailboxImpl`/`IL1AssetRouter`/`IL1ERC20Bridge`/`IL1NativeTokenVault` sources and the `L2CanonicalTransaction`/`BridgehubL2TransactionRequest` structs in `common/Messaging.sol`. **Live-confirmed via `eth_getLogs`:** on the Era Diamond — `NewPriorityRequest` `0x4531cd57…`, `NewPriorityRequestId` `0x779f4416…`, `BlockCommit` `0x8f2916b2…`, `BlocksVerification` `0x22c9005d…`, `BlockExecution` `0x24023073…`; on the AssetRouter — `0x0f87e1ea…`, `0xe21913bc…`, `0x44eb9a84…`; on the L1Nullifier — `0xe4def01b…`; on the NativeTokenVault — `BridgeMint` `0xbc0f4055…`, `BridgeBurn` `0x1cd02155…`. The `commitBatchesSharedBridge` selector `0x0db9eb87` was confirmed as the actual selector in a live batch-commit tx routed through the ValidatorTimelock.
- **Proxies:** EIP-1967 impl/admin slots read live (§7) — every ecosystem contract is an OZ TransparentUpgradeableProxy under the single ProxyAdmin `0xc2a3…2cf1` (admin slot identical across all six); the Era chain is an EIP-2535 Diamond (empty impl slot, non-empty `facets()`); the **ValidatorTimelock** and **Governance** are themselves OZ Transparent proxies (non-empty impl slots — VT impl `0xc954…111d` behind its own dedicated ProxyAdmin `0x0d8d…9bbb`; Governance impl `0x3662…c14b`), while **ChainAdmin** and **ProxyAdmin** are non-proxy contracts (empty impl slot).

Authoritative sources:
- Canonical repo: [matter-labs/era-contracts](https://github.com/matter-labs/era-contracts) (`l1-contracts/contracts/`: `bridgehub/`, `bridge/asset-router/`, `bridge/ntv/`, `state-transition/chain-interfaces/IExecutor.sol` + `IMailboxImpl.sol`, `common/Messaging.sol`).
- Official docs: [ZKsync L1 ecosystem contracts](https://docs.zksync.io/zksync-protocol/contracts/l1-contracts/l1-ecosystem-contracts) · [ZK-chain addresses](https://docs.zksync.io/zksync-protocol/contracts/l1-contracts/zk-chain-addresses) · [L1 contracts overview](https://docs.zksync.io/zksync-protocol/contracts/l1-contracts).
- Explorers: [Etherscan DiamondProxy](https://etherscan.io/address/0x32400084C286CF3E17e7B677ea9583e60a000324) · [Etherscan BridgeHub](https://etherscan.io/address/0x303a465B659cBB0ab36eE643eA362c509EEb5213) · [Etherscan L1AssetRouter](https://etherscan.io/address/0x8829AD80E425C646DAB305381ff105169FeEcE56) · [zkSync Era explorer](https://explorer.zksync.io/).
- [L2BEAT — ZKsync Era](https://l2beat.com/scaling/projects/zksync-era) (architecture / permissions cross-check).
