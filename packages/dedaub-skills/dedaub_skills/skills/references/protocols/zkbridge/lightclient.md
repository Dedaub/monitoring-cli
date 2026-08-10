# zkBridge (Polyhedra) zkLightClient on LayerZero — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon)

**Status:** verified against live RPC on Ethereum, Base, BNB Smart Chain, Avalanche C-Chain, Arbitrum One, Optimism, and Polygon PoS, plus Etherscan-verified implementation source, on 2026-06-09.
**Scope:** Polyhedra's **zkLightClient verification service deployed *inside* LayerZero** — the LayerZero **V1 Oracle** (`ZkBridgeOracle`) and the LayerZero **V2 DVN** (`ZkBridgeOracleV2`, a Decentralized Verification Network). These are the contracts a LayerZero app (OApp/UA) wires in to have Polyhedra's zk light client attest source-block validity. Topics/selectors are **chain-agnostic**; addresses are **network-specific**. The native zkBridge messaging stack (`ZKBridge` entrypoint + BlockUpdaters) is a *separate* product — see [messaging.md](./messaging.md).

This file covers the **provider side** of LayerZero verification, not LayerZero's own Endpoint/MessageLib. A LayerZero message that selects Polyhedra as its oracle/DVN flows: source UA → LayerZero send → Polyhedra's contract is *assigned a job* (`OracleNotified`) → Polyhedra's relayer zk-proves the source block and calls the V1 `updateMptHash`/`updateFpHash` or V2 `verify`/`verifyByTx` to attest, which LayerZero's MessageLib then reads to authorize delivery. Polyhedra never controls LayerZero's funds; it is one selectable verifier.

**Deployment shape (verified on-chain 2026-06-09):**
- **V1 Oracle** `ZkBridgeOracle` lives at the **single deterministic address `0xE014fe8c4d5C23EDB7AC4011F226e869ac7Ef5CC` on all 7 chains**, an **EIP-1967 Transparent proxy** whose implementation `0x161d3815a175a566ac12c7b4ba4d53c3a3181af4` is **byte-identical on all 7 chains**, behind the **shared ProxyAdmin `0xe16d201ca134345601631d327a971a3741646b0d`** (same as the messaging stack).
- **V2 DVN** `ZkBridgeOracleV2` lives at the **single deterministic address `0x8ddF05F9A5c488b4973897E278B58895bF87Cb24` on all 7 chains** (Blast, out of scope, uses `0x0ff4cc28…`), an **EIP-1967 Transparent proxy** — but its implementation is **DIFFERENT on every chain** (per-chain bytecode; same proxy address), behind the same shared ProxyAdmin.
- V2 is the **active** path (28 `OracleNotified` logs in a recent ~49k-block Ethereum window; V1 Oracle was quiet). V1 remains deployed for legacy LayerZero v1 apps.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 ZkBridgeOracle — LayerZero **V1** (`0xE014fe8c…`, same address all chains)

| topic0 | Event |
|--------|-------|
| `0xdaebd99ba0f67a2d7a70d027ab177cad40ce040f65a9c4d98544a5463a172ebd` | `OracleNotified(uint16 dstChainId, uint16 proofType, uint256 blockConfirmations, address userApplication, uint256 fee)` — LayerZero assigned a verification job to Polyhedra. |
| `0x6bd1ecba474b4539a7f4175c23e52de4e2ad70d374cba8c744609eb8c6bb0a27` | `SetFee(uint16 dstChainId, uint16 proofType, uint256 fee)` |
| `0x2fe8b99495ccc68fc1995374ef15e331f1d9f73995dafd0813b5cde8383d8d16` | `RemoveFee(uint16 dstChainId, uint16 proofType)` |
| `0x882386da003a547e108f4013481dc50dd637ba9e2f89b0a884803db03eef247a` | `SetFeeManager(address feeManager, bool flag)` |
| `0x66bf9186b00db666fc37aaffbb95a050c66e599e000c785c1dff0467d868f1b1` | `WithdrawFee(address receiver, uint256 amount)` |
| `0xb7fadf96c12f12cde47625d532f5ac111781c8ca270be73c25434cfce3df01ec` | `EnableSupportedDstChain(uint16 proofType, uint16 dstChainId)` |
| `0xcb92f61b0a2eacdffd0b9e9643c8f4eec03973e9854811080d29919332029361` | `DisableSupportedDstChain(uint16 proofType, uint16 dstChainId)` |
| `0x25a1ae020d581a4676219671150e9a1518e6b2b0147a4e0b160a13d561282058` | `ModBlockUpdater(uint16 sourceChainId, address oldBlockUpdater, address newBlockUpdater)` |
| `0x9bb1ee10df65f2ea6e9b6f1911afe80df0374a7e2fa65c7786fe98398e5eda9f` | `ModLayerZeroEndpoint(address oldLayerZeroEndpoint, address newLayerZeroEndpoint)` |
| `0x7232a6669d25bc6d450f5c74c7cbc1e4ca02fa2386e736f19a83cd269baeb734` | `ModZKMptValidator(address oldZKMptValidator, address newZKMptValidator)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` |

### 1.2 ZkBridgeOracleV2 — LayerZero **V2 DVN** (`0x8ddF05F9…`, same address all chains)

| topic0 | Event |
|--------|-------|
| `0x915615b444fd15cbe20634e8d0a109373bea8c1ed15d3c503ca9e70547a4c220` | `OracleNotified(uint32 dstEid, uint64 blockConfirmations, address userApplication, uint256 fee)` — DVN job assigned. *(verified live on Ethereum — 28 logs)* |
| `0x3722a9f6d5cdd3d4506591f2182163eedf8e74f346faf115ae42f4f0ffdc1a1f` | `SetFee(uint32 dstEid, uint256 fee)` |
| `0xf15a0a3784dea9b4fe33bc98e2450745e262d310237b2868ea8ef56967ff3ecb` | `WithdrawFee(address messageLib, address receiver, uint256 amount)` |
| `0x968effd490f9188c28dc3411469f24794e98398797d621c8670c5ff1f99dd4af` | `DstChainStatusChanged(uint32 dstEid, bool enabled)` |
| `0x9738de301c763a91427d836968b3504d77cf4c72624e54407b8482707897fcac` | `NewBlockUpdater(uint32 srcEid, address oldBlockUpdater, address newBlockUpdater)` |
| `0x1abe69b439fa9d46894d9f24dc9e27392ec01df1994af5471c79d256211453cd` | `NewDefaultTxValidator(address oldValidator, address newValidator)` |
| `0x46f228076186c559dfeeb080f2e41a90702c6a6d3c5b6345f050e0f958f1220b` | `NewDefaultZkValidator(address oldValidator, address newValidator)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` |

> **`OracleNotified` topic0 collision-by-name.** V1 (`uint16,uint16,uint256,address,uint256`, topic0 `0xdaebd99b…`) and V2 (`uint32,uint64,address,uint256`, topic0 `0x915615b4…`) have the **same event name but different signatures → different topic0s**. Disambiguate by topic0 AND by emitter address (V1 = `0xE014fe8c…`, V2 = `0x8ddF05F9…`). Likewise `SetFee` differs between V1 (`0x6bd1ecba…`) and V2 (`0x3722a9f6…`), and `WithdrawFee` differs (V1 2-arg `0x66bf9186…`, V2 3-arg `0xf15a0a37…`).

### 1.3 Proxy admin events (on both proxies)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **watch on both `0xE014fe8c…` and `0x8ddF05F9…`.** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 ZkBridgeOracle — V1 (all verified present in impl `0x161d3815…`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc5e193cd` | `assignJob(uint16 dstChainId, uint16 proofType, uint64 blockConfirmations, address userApplication)` → `uint256 price` | LayerZero relayer entrypoint; emits `OracleNotified`. |
| `0x5553fb8e` | `getFee(uint16 dstChainId, uint16 proofType, uint64 blockConfirmations, address userApplication)` → `uint256` | View quote. |
| `0x5704518f` | `updateFpHash(uint16 srcChainId, bytes32 blockHash, bytes proof, address ua)` | Attest a finality-proof block hash. |
| `0xe7430049` | `updateMptHash(uint16 srcChainId, bytes32 blockHash, bytes32 receiptHash, address ua)` | Attest an MPT receipt hash to LayerZero. |
| `0xfd9be522` | `withdrawFee(address receiver, uint256 amount)` | Emits `WithdrawFee`. |

### 2.2 ZkBridgeOracleV2 — V2 DVN (verified present in the per-chain impl, ETH `0xdff54e8d…`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x95d376d7` | `assignJob((uint32 dstEid,bytes packetHeader,bytes32 payloadHash,uint64 confirmations,address sender) param, bytes options)` → `uint256 fee` | `payable`. LayerZero `ILayerZeroDVN.assignJob`; emits `OracleNotified`. |
| `0x30bb3aac` | `getFee(uint32 dstEid, uint64 confirmations, address sender, bytes options)` → `uint256` | View quote (`ILayerZeroDVN.getFee`). |
| `0x5bf48e3a` | `verify(bytes32 blockHash, bytes encodedPayload, bytes zkProof)` | DVN attests via zk proof of the source block. |
| `0x414af43a` | `verifyByTx(bytes32 blockHash, uint32 srcEid, bytes txData)` | Alternative tx-based attestation. |
| `0xc879c6d8` | `withdrawFee(address messageLib, address payable to)` | Emits `WithdrawFee` (3-arg event). |
| `0x84795a2c` | `withdrawFeeAll(address payable to)` | Sweep all fees. |

> `assignJob((uint32,bytes,bytes32,uint64,address),bytes)` selector is `0x95d376d7` — verified present in bytecode. (A naive `(uint32,bytes32,uint64,address)` tuple guess `0xee5a6341` is **absent**; the real LayerZero `AssignJobParam` struct has 5 fields incl. `packetHeader`/`payloadHash`.)

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Proxy impls read live from the EIP-1967 slot.

| Role | Address | One-liner |
|------|---------|-----------|
| **ZkBridgeOracle** (V1, proxy) | `0xE014fe8c4d5C23EDB7AC4011F226e869ac7Ef5CC` | LayerZero v1 oracle; impl `0x161d3815a175a566ac12c7b4ba4d53c3a3181af4` (shared all chains). |
| **ZkBridgeOracleV2** (V2 DVN, proxy) | `0x8ddF05F9A5c488b4973897E278B58895bF87Cb24` | LayerZero v2 DVN; impl `0xdff54e8d2b31a197dc5859739e7177aa31fc3390` (**ETH-specific**). *(`OracleNotified` verified live)* |
| **ProxyAdmin** (shared) | `0xe16d201ca134345601631d327a971a3741646b0d` | EIP-1967 admin of both proxies on every chain. |

---

## 4. Addresses — Base / BNB / Avalanche / Arbitrum / Optimism / Polygon

Both contracts use the **same proxy literal on all 7 chains**; the **V1 impl is shared**, the **V2 impl diverges per chain** (same proxy address, different bytecode). All existence-checked via `eth_getCode` (non-empty) and impls read live from the EIP-1967 slot 2026-06-09.

| Chain | EVM id | V1 Oracle proxy | V1 impl (shared) | V2 DVN proxy | V2 impl (per-chain) |
|---|---|---|---|---|---|
| Ethereum | 1 | `0xE014fe8c…cFD9` | `0x161d3815…1af4` | `0x8ddF05F9…Cb24` | `0xdff54e8d2b31a197dc5859739e7177aa31fc3390` |
| Base | 8453 | `0xE014fe8c…cFD9` | `0x161d3815…1af4` | `0x8ddF05F9…Cb24` | `0xe43116735da929d6aa66705f6f9a08d6722755e1` |
| BNB | 56 | `0xE014fe8c…cFD9` | `0x161d3815…1af4` | `0x8ddF05F9…Cb24` | `0xc81c8f259585165f5650ff8e554b1784270d03ce` |
| Avalanche | 43114 | `0xE014fe8c…cFD9` | `0x161d3815…1af4` | `0x8ddF05F9…Cb24` | `0xb01b26c5859dcc0d082e145ed418d6cbd9298805` |
| Arbitrum | 42161 | `0xE014fe8c…cFD9` | `0x161d3815…1af4` | `0x8ddF05F9…Cb24` | `0x14cbef4f4f53c8f486de55c24945336addd742a3` |
| Optimism | 10 | `0xE014fe8c…cFD9` | `0x161d3815…1af4` | `0x8ddF05F9…Cb24` | `0xe894843363a806d6f68f2c7801991a626fecb4f0` |
| Polygon | 137 | `0xE014fe8c…cFD9` | `0x161d3815…1af4` | `0x8ddF05F9…Cb24` | `0xc6e51b02c522567ce8f79e84967f33688785d663` |

ProxyAdmin `0xe16d201ca134345601631d327a971a3741646b0d` is the EIP-1967 admin of **both** proxies on **all 7** chains (verified). **Both contracts are present on all 7 target chains** — no target chain returns `0x`. The V2 ETH vs Base impls were confirmed to be genuinely different bytecode (distinct code hashes), not a read artifact.

---

## 5. Cross-chain summary

| Chain | EVM id | V1 Oracle `0xE014fe8c…` | V2 DVN `0x8ddF05F9…` | V1 impl | V2 impl |
|---|---|---|---|---|---|
| Ethereum | 1 | ✓ | ✓ | `0x161d3815…` (shared) | `0xdff54e8d…` |
| Base | 8453 | ✓ | ✓ | `0x161d3815…` | `0xe4311673…` |
| BNB | 56 | ✓ | ✓ | `0x161d3815…` | `0xc81c8f25…` |
| Avalanche | 43114 | ✓ | ✓ | `0x161d3815…` | `0xb01b26c5…` |
| Arbitrum | 42161 | ✓ | ✓ | `0x161d3815…` | `0x14cbef4f…` |
| Optimism | 10 | ✓ | ✓ | `0x161d3815…` | `0xe8948433…` |
| Polygon | 137 | ✓ | ✓ | `0x161d3815…` | `0xc6e51b02…` |

**Vanity/determinism tells:** V1 proxy `0xE014fe8c…cFD9`, V2 proxy `0x8ddF05F9…Cb24`, V1 impl `0x161d3815…`, and ProxyAdmin `0xe16d201c…` are **identical literals on every chain**. The **V2 impl is the lone per-chain divergence** — always read the EIP-1967 slot per chain rather than assuming a shared V2 impl. (Out of scope: Blast uses a different V2 DVN proxy `0x0ff4cc28826356503BB79c00637bec0eE006f237`.)

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **ZkBridgeOracle** (V1, `0xE014fe8c…`) | **EIP-1967 Transparent** | impl slot = `0x161d3815…` (same all chains); admin slot = `0xe16d201c…`. | ProxyAdmin `0xe16d201ca134345601631d327a971a3741646b0d`. Watch `Upgraded` `0xbc7cd75a…`. |
| **ZkBridgeOracleV2** (V2 DVN, `0x8ddF05F9…`) | **EIP-1967 Transparent** | impl slot = **per-chain** (§4); admin slot = `0xe16d201c…`. | ProxyAdmin `0xe16d201c…`. Watch `Upgraded`. |

EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. Both proxies are single-impl Transparent (no Beacon slot, no Diamond). **Not immutable** — impl slot is populated on every chain.

---

## 7. Detection invariants & gotchas

1. **`OracleNotified` is name-collided between V1 and V2 with different topic0s** — V1 `0xdaebd99b…` (5 args, `uint16`), V2 `0x915615b4…` (4 args, `uint32`). Key on `(topic0, emitter)`. V2 is the live path today.
2. **These are LayerZero verifier contracts, not a bridge.** `OracleNotified`/`assignJob` mean "Polyhedra was asked to attest a LayerZero message," not "a transfer happened." The actual asset/message flow is LayerZero's; Polyhedra only attests source-block validity. Do not treat these as value-bearing bridge events.
3. **`userApplication`/`sender` is the LayerZero OApp**, not an end user. Fee and job attribution is per-OApp.
4. **V1 = LayerZero `uint16` chainIds; V2 = LayerZero `uint32` EIDs.** These are **LayerZero's** id spaces (e.g. ETH v2 EID 30101), distinct from both EVM chainIds and the zkBridge-internal ids in [messaging.md](./messaging.md) §0. Three different id namespaces coexist across the two products — never cross-map them.
5. **V2 impl differs per chain; V1 impl is shared.** Reading the V1 slot gives `0x161d3815…` everywhere; reading the V2 slot gives a per-chain impl. Hard-coding one V2 impl is wrong.
6. **Both proxies share ProxyAdmin `0xe16d201c…` with the native messaging stack.** An `Upgraded`/`AdminChanged` from that admin can touch the entrypoint, the BlockUpdaters, the V1 Oracle, or the V2 DVN — scope by the emitting proxy address.
7. **`verify`/`verifyByTx`/`updateMptHash`/`updateFpHash` are relayer attestation calls**, not user actions. They are the heartbeat that Polyhedra is actively serving a route; `tx.to` is the oracle/DVN.
8. **Blast (and other non-target chains) use a different V2 DVN proxy** (`0x0ff4cc28…`); within the 7 targets the proxy literal is uniform.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- V1 ZkBridgeOracle
TOPIC_V1_ORACLE_NOTIFIED      = '\xdaebd99ba0f67a2d7a70d027ab177cad40ce040f65a9c4d98544a5463a172ebd'
TOPIC_V1_SET_FEE              = '\x6bd1ecba474b4539a7f4175c23e52de4e2ad70d374cba8c744609eb8c6bb0a27'
TOPIC_V1_REMOVE_FEE           = '\x2fe8b99495ccc68fc1995374ef15e331f1d9f73995dafd0813b5cde8383d8d16'
TOPIC_V1_SET_FEE_MANAGER      = '\x882386da003a547e108f4013481dc50dd637ba9e2f89b0a884803db03eef247a'
TOPIC_V1_WITHDRAW_FEE         = '\x66bf9186b00db666fc37aaffbb95a050c66e599e000c785c1dff0467d868f1b1'
TOPIC_V1_ENABLE_DST           = '\xb7fadf96c12f12cde47625d532f5ac111781c8ca270be73c25434cfce3df01ec'
TOPIC_V1_DISABLE_DST          = '\xcb92f61b0a2eacdffd0b9e9643c8f4eec03973e9854811080d29919332029361'
TOPIC_V1_MOD_BLOCK_UPDATER    = '\x25a1ae020d581a4676219671150e9a1518e6b2b0147a4e0b160a13d561282058'
TOPIC_V1_MOD_LZ_ENDPOINT      = '\x9bb1ee10df65f2ea6e9b6f1911afe80df0374a7e2fa65c7786fe98398e5eda9f'
TOPIC_V1_MOD_ZK_MPT_VALIDATOR = '\x7232a6669d25bc6d450f5c74c7cbc1e4ca02fa2386e736f19a83cd269baeb734'
-- V2 ZkBridgeOracleV2 (DVN)
TOPIC_V2_ORACLE_NOTIFIED      = '\x915615b444fd15cbe20634e8d0a109373bea8c1ed15d3c503ca9e70547a4c220'
TOPIC_V2_SET_FEE              = '\x3722a9f6d5cdd3d4506591f2182163eedf8e74f346faf115ae42f4f0ffdc1a1f'
TOPIC_V2_WITHDRAW_FEE         = '\xf15a0a3784dea9b4fe33bc98e2450745e262d310237b2868ea8ef56967ff3ecb'
TOPIC_V2_DST_STATUS_CHANGED   = '\x968effd490f9188c28dc3411469f24794e98398797d621c8670c5ff1f99dd4af'
TOPIC_V2_NEW_BLOCK_UPDATER    = '\x9738de301c763a91427d836968b3504d77cf4c72624e54407b8482707897fcac'
TOPIC_V2_NEW_TX_VALIDATOR     = '\x1abe69b439fa9d46894d9f24dc9e27392ec01df1994af5471c79d256211453cd'
TOPIC_V2_NEW_ZK_VALIDATOR     = '\x46f228076186c559dfeeb080f2e41a90702c6a6d3c5b6345f050e0f958f1220b'
-- shared
TOPIC_OWNERSHIP_TRANSFERRED   = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED           = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'

-- ===== Selectors =====
-- V1
SEL_V1_ASSIGN_JOB             = '\xc5e193cd'
SEL_V1_GET_FEE                = '\x5553fb8e'
SEL_V1_UPDATE_FP_HASH         = '\x5704518f'
SEL_V1_UPDATE_MPT_HASH        = '\xe7430049'
SEL_V1_WITHDRAW_FEE           = '\xfd9be522'
-- V2 DVN
SEL_V2_ASSIGN_JOB             = '\x95d376d7'
SEL_V2_GET_FEE                = '\x30bb3aac'
SEL_V2_VERIFY                 = '\x5bf48e3a'
SEL_V2_VERIFY_BY_TX           = '\x414af43a'
SEL_V2_WITHDRAW_FEE           = '\xc879c6d8'
SEL_V2_WITHDRAW_FEE_ALL       = '\x84795a2c'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT            = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses (proxies same literal on all 7 chains) =====
ZKBRIDGE_ORACLE_V1            = '\xe014fe8c4d5c23edb7ac4011f226e869ac7ef5cc'
ZKBRIDGE_ORACLE_V1_IMPL       = '\x161d3815a175a566ac12c7b4ba4d53c3a3181af4'  -- shared all 7 chains
ZKBRIDGE_DVN_V2               = '\x8ddf05f9a5c488b4973897e278b58895bf87cb24'
ZKBRIDGE_PROXY_ADMIN          = '\xe16d201ca134345601631d327a971a3741646b0d'
-- V2 DVN impls (per-chain)
V2_IMPL_ETH                   = '\xdff54e8d2b31a197dc5859739e7177aa31fc3390'
V2_IMPL_BASE                  = '\xe43116735da929d6aa66705f6f9a08d6722755e1'
V2_IMPL_BSC                   = '\xc81c8f259585165f5650ff8e554b1784270d03ce'
V2_IMPL_AVAX                  = '\xb01b26c5859dcc0d082e145ed418d6cbd9298805'
V2_IMPL_ARB                   = '\x14cbef4f4f53c8f486de55c24945336addd742a3'
V2_IMPL_OP                    = '\xe894843363a806d6f68f2c7801991a626fecb4f0'
V2_IMPL_POLYGON               = '\xc6e51b02c522567ce8f79e84967f33688785d663'
-- out of scope (recorded): Blast V2 DVN proxy
BLAST_DVN_V2                  = '\x0ff4cc28826356503bb79c00637bec0ee006f237'
```

---

## 9. Verification & sources

How every constant was verified (2026-06-09):
- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]`. V2 `OracleNotified` (`0x915615b4…`) confirmed against **live `eth_getLogs`** on the V2 DVN `0x8ddF05F9…` (28 logs, ~49k-block Ethereum window). All V1 selectors (`assignJob`/`getFee`/`updateMptHash`/`updateFpHash`/`withdrawFee`) and all V2 selectors (`assignJob`/`getFee`/`verify`/`verifyByTx`/`withdrawFee`/`withdrawFeeAll`) confirmed **present in the live implementation bytecode** via PUSH4 scan; the V2 `assignJob` tuple was corrected to the 5-field LayerZero `AssignJobParam` (`0x95d376d7` present, naive 4-field guess absent).
- **Addresses:** V1 Oracle, V2 DVN, ProxyAdmin existence-checked via `eth_getCode` (non-empty) on all 7 chains. V1 impl read identical on all 7; V2 impl read per chain and confirmed divergent (distinct code hashes ETH vs Base).
- **Proxy impls/admins:** read live from the EIP-1967 implementation and admin slots; both are EIP-1967 Transparent with the shared ProxyAdmin `0xe16d201c…`.
- **Contract names + ABIs:** Etherscan-verified source — V1 impl = `ZkBridgeOracle` (`0x161d3815…`), V2 impl = `ZkBridgeOracleV2` (`0xdff54e8d…`).
- **Unverified:** the V1/V2 admin-event topic0s (`SetFee`/`RemoveFee`/`Mod*`/`New*Validator`/`DstChainStatusChanged`) are computed from the verified ABI but not all seen in a live log; `OracleNotified` is live-confirmed.

**Authoritative sources:**
- Polyhedra zkLightClient / LayerZero configs — [LayerZero v1 zkLightClient oracle addresses](https://docs.zkbridge.com/layerzero-zklightclient-configurations/layerzero-v1-zklightclient-oracle-addresses) and [LayerZero v2 zkLightClient DVN addresses](https://docs.zkbridge.com/layerzero-zklightclient-configurations/layerzero-v2-zklightclient-dvn-addresses) at [docs.zkbridge.com](https://docs.zkbridge.com).
- Etherscan — V1 Oracle [`0xE014fe8c…cFD9`](https://etherscan.io/address/0xE014fe8c4d5C23EDB7AC4011F226e869ac7Ef5CC) (impl [`0x161d3815…`](https://etherscan.io/address/0x161d3815a175a566ac12c7b4ba4d53c3a3181af4)), V2 DVN [`0x8ddF05F9…Cb24`](https://etherscan.io/address/0x8ddF05F9A5c488b4973897E278B58895bF87Cb24) (impl [`0xdff54e8d…`](https://etherscan.io/address/0xdff54e8d2b31a197dc5859739e7177aa31fc3390)).
- Block explorers for the other six chains: Basescan, BscScan, Snowscan, Arbiscan, Optimistic Etherscan, Polygonscan (both contracts present on each).
- LayerZero DVN interface reference (`ILayerZeroDVN.AssignJobParam`) — LayerZero V2 documentation.
