# Wormhole Core — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain, Arc)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the canonical `wormhole-foundation/wormhole` repo (`ethereum/contracts/`), the Wormhole docs contract-address page and the `wormhole-foundation/wormhole-sdk-ts` address constants. Topics and selectors recomputed as `keccak256(signature)`; addresses existence-checked with `eth_getCode`; implementations read from the EIP-1967 slot; implementation bytecode scanned for each event topic (`PUSH32`) and selector (`PUSH4`).
**Scope:** the Wormhole **Core contract** (the message bus that every Wormhole product publishes through), its guardian-set and governance surface, and three small guardian-governed helpers (Guardian Governance, Delegated Guardians, Custom Consistency Level). The Core is deployed on **all eight target chains, Robinhood Chain (4663) included**. Topics and selectors are chain-agnostic; addresses are network-specific. The products that sit on top (Token Bridge, NFT Bridge, Wormhole Relayer, Executor, Circle integration, NTT) have their own files; see [README.md](README.md).

The Core contract moves no user value. A sending application calls `publishMessage`, and the Core emits `LogMessagePublished` with the caller as `sender` and a per-sender `sequence`. The 19 guardians observe the event and sign a VAA over it. A destination contract calls `parseAndVerifyVM` on its own chain's Core to check the guardian signatures. So the Core is the **source-leg event of every Wormhole product**, and the identity of a message is `(emitterChain, emitterAddress, sequence)`: the Wormhole chain id of the source chain, the `sender` left-padded to 32 bytes, and `sequence`.

Two facts a monitor must know first:

1. **`LogMessagePublished` is shared by every application.** In the pinned window, the Token Bridge sent only 168 of 1,031 messages on Ethereum. Mayan's Swift destination contract (`SwiftDest`, `0xd78d199f8c402e7b5cc2abe278df0412400a3bae`) sent 731. Always filter on `topic1` (`sender`) before you treat a message as a bridge transfer.
2. **The Core is an EIP-1967 proxy with no admin key.** Upgrades, guardian-set rotations, fee changes and fee withdrawals all arrive as governance VAAs signed by the guardians and emitted from Solana (Wormhole chain 1, governance contract `0x0000000000000000000000000000000000000000000000000000000000000004`). Only a contract upgrade emits an event. A guardian-set rotation emits **no event**: `GuardianSetAdded` is declared in the source but no code path emits it (the event topic is absent from every live implementation).

---

## 0. Contract families

| Contract | Chains | Role | Proxy? |
|----------|--------|------|--------|
| **Core (`Wormhole` proxy + `Implementation`)** | all 8 + Arc | Publishes messages (`publishMessage`), verifies VAAs (`parseAndVerifyVM`), holds the guardian sets, executes core governance VAAs. | EIP-1967 proxy, upgraded by governance VAA (`submitContractUpgrade`) |
| **Guardian Governance** (`Governance.sol` of the NTT repo) | ETH, Base, ARB, OP, BNB, AVAX (not listed for Polygon, Robinhood or Arc) | "Guardian-governed ownership": an owner contract that executes only calls signed by a guardian quorum (`performGovernance`). It owns, for example, the W token's NTT managers. | No (immutable, 3,408 B) |
| **Delegated Guardians** (`WormholeDelegatedGuardians`) | Ethereum only | Stores per-chain configs of a delegated subset of guardians (`submitConfig`, governance VAA). | No |
| **Custom Consistency Level** (`CustomConsistencyLevel`) | Ethereum only (also Linea per the SDK) | Lets an emitter store a custom finality config (`configure`). | No (507 B) |

Product contracts that call the Core: Token Bridge and wrapped tokens ([token-bridge.md](token-bridge.md)), NFT Bridge ([nft-bridge.md](nft-bridge.md)), Wormhole Relayer and Executor ([relayer.md](relayer.md)), Circle Integration and CCTP helpers ([cctp.md](cctp.md)), NTT managers and transceivers ([ntt.md](ntt.md)).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Core contract — emitter = the Core proxy of each chain (§3, §4)

| topic0 | Event |
|--------|-------|
| `0x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2` | `LogMessagePublished(address indexed sender, uint64 sequence, uint32 nonce, bytes payload, uint8 consistencyLevel)` — **the source event of every Wormhole message; status only, no value moves in the Core** |
| `0x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49` | `ContractUpgraded(address indexed oldContract, address indexed newContract)` — emitted by `submitContractUpgrade`; **same topic0 in Token Bridge, NFT Bridge, Wormhole Relayer, DeliveryProvider and Circle Integration** — key by emitter |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — OpenZeppelin `ERC1967Upgrade._upgradeTo`, emitted in the same transaction as `ContractUpgraded` |
| `0x2384dbc52f7b617fb7c5aa71e5455a21ff21d58604bb6daef6af2bb44aadebdd` | `GuardianSetAdded(uint32 indexed index)` — **declared in `Governance.sol` and `IWormhole.sol`, never emitted** (topic absent from all eight live implementations) |
| `0xdfb80683934199683861bf00b64ecdf0984bbaf661bf27983dba382e99297a62` | `LogGuardianSetChanged(uint32 oldGuardianIndex, uint32 newGuardianIndex)` — legacy declaration in `State.sol` (`contract Events`), never emitted |

`LogMessagePublished` data layout: `sequence` (word 0), `nonce` (word 1), offset of `payload` (word 2), `consistencyLevel` (word 3), then the payload length and bytes. `sender` is `topic1`. `nonce` is a caller-chosen batch id with no uniqueness; the unique key is `(sender, sequence)` on one chain.

### 1.2 Guardian-governed helpers (Ethereum)

| topic0 | Event |
|--------|-------|
| `0x60521c8f957274659667169ced5f227b61b730968b22ef66f02a72f27394eba4` | `ChainConfigSet(uint256 configIndex, uint16 chainId, uint8 threshold, address[] keys)` — Delegated Guardians: a new delegated guardian set for one chain (admin) |
| `0xa37f0112e03d41de27266c1680238ff1548c0441ad1e73c82917c000eefdd5ea` | `ConfigSet(address emitterAddress, bytes32 config)` — Custom Consistency Level: an emitter set its finality config (status only) |

Guardian Governance (`performGovernance`) emits no event of its own; the governed contract's event (for example `OwnershipTransferred`, `PeerUpdated`) is the only log.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Core contract

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb19a437e` | `publishMessage(uint32 nonce, bytes payload, uint8 consistencyLevel)` | Payable; `msg.value` must equal `messageFee()` (0 on all eight chains, measured). Returns `uint64 sequence`. Emits `LogMessagePublished`. |
| `0xc0fd8bde` | `parseAndVerifyVM(bytes encodedVM)` | View. Returns `(VM vm, bool valid, string reason)`. Every destination product calls it. |
| `0xa9e11893` | `parseVM(bytes encodedVM)` | Pure decode, no signature check. |
| `0x5cb8cae2` | `submitContractUpgrade(bytes _vm)` | Governance VAA (module `Core`). Emits `Upgraded` + `ContractUpgraded`. **Admin.** |
| `0x6606b4e0` | `submitNewGuardianSet(bytes _vm)` | Governance VAA. Stores guardian set `index+1`, expires the old one after 86,400 s. **No event — watch this selector.** |
| `0xf42bc641` | `submitSetMessageFee(bytes _vm)` | Governance VAA. **No event.** |
| `0x93df337e` | `submitTransferFees(bytes _vm)` | Governance VAA. Sends native fees held by the Core to a recipient with an internal value transfer. **No event.** |
| `0x178149e7` | `submitRecoverChainId(bytes _vm)` | Governance VAA, only on a forked chain (`isFork()`). |
| `0x8129fc1c` | `initialize()` | Called by `submitContractUpgrade` on the new implementation. |
| `0x1a90a219` | `messageFee()` | View — `uint256`. |
| `0x1cfe7951` | `getCurrentGuardianSetIndex()` | View — `uint32`; **7 on all eight chains** (read 2026-09-29). |
| `0xf951975a` | `getGuardianSet(uint32 index)` | View — `(address[] keys, uint32 expirationTime)`. |
| `0xeb8d3f12` | `getGuardianSetExpiry()` | View — `uint32`. |
| `0x9a8a0592` | `chainId()` | View — the Wormhole chain id (§4.2). |
| `0x64d42b17` | `evmChainId()` | View — the EVM chain id. |
| `0xfbe3c2cd` | `governanceChainId()` | View — `1` (Solana) on all eight chains. |
| `0xb172b222` | `governanceContract()` | View — `0x0000000000000000000000000000000000000000000000000000000000000004`. |
| `0x4cf842b5` | `nextSequence(address emitter)` | View — the next `sequence` of an emitter. |
| `0xe039f224` | `isFork()` | View. |
| `0x2c3c02a4` | `governanceActionIsConsumed(bytes32 hash)` | View — replay guard of governance VAAs. |

### 2.2 Guardian-governed helpers

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x56016724` | `performGovernance(bytes vaa)` | Guardian Governance: verifies a guardian-signed `EVM_CALL` message and calls `governedContract` with `callData`. **Admin.** |
| `0x555ff288` | `submitConfig(bytes vaa)` | Delegated Guardians: governance VAA; emits `ChainConfigSet`. **Admin.** |
| `0x70c852a1` | `getConfig(uint16 _chainId)` | Delegated Guardians view. |
| `0xca23addf` | `configure(bytes32 config)` | Custom Consistency Level; emits `ConfigSet` for `msg.sender`. |
| `0xc44b11f7` | `getConfiguration(address emitterAddress)` | Custom Consistency Level view. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All existence-checked with `eth_getCode` on 2026-09-29. Wormhole chain id **2**.

| Role | Address | One-liner |
|------|---------|-----------|
| **Core** (proxy) | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | 680 B EIP-1967 proxy; implementation `0x3c3d457f1522d3540ab3325aa5f1864e34cba9d0` (13,904 B). Same address on BNB. |
| **Guardian Governance** | `0x23Fea5514DFC9821479fBE18BA1D7e1A61f6FfCf` | Guardian-governed owner; `owner()` of the W NttManager `0xc072b1aef336edde59a049699ef4e8fa9d594a48`. |
| **Delegated Guardians** | `0x1462800febd49232798132e8c8b721aa86c4c209` | Delegated guardian-set registry (7,422 B). |
| **Custom Consistency Level** | `0x6A4B4A882F5F0a447078b4Fd0b4B571A82371ec2` | Per-emitter finality config (507 B). |

---

## 4. Addresses — the other seven chains and Arc

### 4.1 Core proxy per chain

| Chain | EVM id | Wormhole id | Core (proxy) | Proxy size | Live implementation (EIP-1967) |
|-------|--------|-------------|--------------|-----------|---------------------------------|
| Ethereum | 1 | 2 | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | 680 B | `0x3c3d457f1522d3540ab3325aa5f1864e34cba9d0` |
| Base | 8453 | 30 | `0xbebdb6C8ddC678FfA9f8748f85C815C556Dd8ac6` | 680 B | `0xfc0d459b8c299095dee743645caac8ed3f9abc4d` |
| Arbitrum One | 42161 | 23 | `0xa5f208e072434bC67592E4C49C1B991BA79BCA46` | 680 B | `0x621199f6beb2ba6fbd962e8a52a320ea4f6d4aa3` |
| Optimism | 10 | 24 | `0xEe91C335eab126dF5fDB3797EA9d6aD93aeC9722` | 680 B | `0x659eda9db86ef4fed5151953f2f42f1130f5a160` |
| Polygon PoS | 137 | 5 | `0x7A4B5a56256163F07b2C80A7cA55aBE66c4ec4d7` | 729 B | `0x381752f5458282d317d12c30d2bd4d6e1fd8841e` |
| BNB Smart Chain | 56 | 4 | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | 680 B | `0xc41172cc37e98bebd12abb39f9124a47e4d072ee` |
| Avalanche C-Chain | 43114 | 6 | `0x54a8e5f9c4CbA08F9943965859F6c34eAF03E26c` | 680 B | `0x64da33455c1abb6c018ac804f1930e36a02b5065` |
| **Robinhood Chain** | 4663 | **72** | `0x141fBa8AD5D61bdaB45A047cF60b5Ad9784987FB` | 680 B | `0x1aafb0d5aab9ffbe09d4d30c9fd90d695c4f0881` |
| **Arc** | 5042 | **71** | `0xC8aD24fC6063c41cB5C12a8e3851AafC3b3CF027` | 680 B | `0x5e02b1ec373bfe93077f335243f170f204db9777` |

`chainId()` returned the Wormhole id and `evmChainId()` the EVM id on every chain. The implementations on Base, Arbitrum, Optimism, Polygon, BNB and Avalanche have identical bytecode (14,522 B, code hash `0xd2d3926de5f9d9b7e881155589b07c3a424a6cf1cddc2394257f4e1dc7b3f7fa`). Ethereum's implementation is an older 13,904 B build (code hash `0x637863b4940357181f66fc748cf3133b516864f6251bf89fde8dcf019d862522`). Robinhood's is 14,522 B with a different hash (`0x49ef719d3d246ab781470db9dba6aa4326112e79bb9bb402fd92952e74ded443`). Arc's is 14,522 B with hash `0x5651fcea0ee7c4a726467244e3967389d566fb4fe6326fdb0089eb368edf1c83` (read 2026-10-05). The SDK also lists `0xBB73cB66C26740F31d1FabDC6b7A46a038A300dd` for Arc and Robinhood in a second map; it has no code on Arc. All eight contain `LogMessagePublished`, `ContractUpgraded` and `Upgraded`, and none contains `GuardianSetAdded`.

### 4.2 Guardian Governance per chain (docs contract-address page)

| Chain | Guardian Governance | Checked |
|-------|---------------------|---------|
| Ethereum | `0x23Fea5514DFC9821479fBE18BA1D7e1A61f6FfCf` | 3,408 B; `performGovernance` selector present |
| Base | `0x838a95B6a3E06B6f11C437e22f3C7561a6ec40F1` | 3,408 B; `owner()` of the W NttManager on Base |
| Arbitrum One | `0x36CF4c88FA548c6Ad9fcDc696e1c27Bb3306163F` | 3,408 B; `owner()` of the W NttManager on Arbitrum |
| Optimism | `0x0E09a3081837ff23D2e59B179E0Bc48A349Afbd8` | 3,408 B; `owner()` of the W NttManager on Optimism |
| BNB Smart Chain | `0x8E4dc685e990379b8D53EcA47841E09B8d30043e` | 3,408 B |
| Avalanche C-Chain | `0x169D91C797edF56100F1B765268145660503a423` | 3,408 B |
| Polygon PoS | — | not in the docs list |
| Robinhood Chain | — | not in the docs list; the shared address `0x574B7864119C9223A9870Ea614dC91A8EE09E512` (HyperEVM, Monad, Unichain) has no code on Robinhood |
| Arc | — | not in the docs list; `0x574B7864119C9223A9870Ea614dC91A8EE09E512` has no code on Arc |

---

## 5. Cross-chain summary

| Chain | EVM id | Wormhole id | Core | Guardian Governance | Delegated Guardians / CCL | Guardian set index | `messageFee()` |
|-------|--------|-------------|------|---------------------|---------------------------|--------------------|----------------|
| Ethereum | 1 | 2 | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | ✅ | ✅ / ✅ | 7 | 0 |
| Base | 8453 | 30 | `0xbebdb6C8ddC678FfA9f8748f85C815C556Dd8ac6` | ✅ | — | 7 | 0 |
| Arbitrum One | 42161 | 23 | `0xa5f208e072434bC67592E4C49C1B991BA79BCA46` | ✅ | — | 7 | 0 |
| Optimism | 10 | 24 | `0xEe91C335eab126dF5fDB3797EA9d6aD93aeC9722` | ✅ | — | 7 | 0 |
| Polygon PoS | 137 | 5 | `0x7A4B5a56256163F07b2C80A7cA55aBE66c4ec4d7` | — (not listed) | — | 7 | 0 |
| BNB Smart Chain | 56 | 4 | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | ✅ | — | 7 | 0 |
| Avalanche C-Chain | 43114 | 6 | `0x54a8e5f9c4CbA08F9943965859F6c34eAF03E26c` | ✅ | — | 7 | 0 |
| **Robinhood Chain** | 4663 | 72 | `0x141fBa8AD5D61bdaB45A047cF60b5Ad9784987FB` | — (not listed) | — | 7 | 0 |
| **Arc** | 5042 | 71 | `0xC8aD24fC6063c41cB5C12a8e3851AafC3b3CF027` | — (not listed) | — | 7 | 0 |

**Shared literal address:** Ethereum and BNB use the same Core address. The other chains use chain-unique addresses. Key every Core query on `(chain, address)`.

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Core** (all 8 + Arc) | EIP-1967 proxy (`Wormhole is ERC1967Proxy`); upgrade logic lives in the implementation (`Governance.upgradeImplementation`) | Implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` populated (§4.1); admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` = 0 on all eight and Arc | Guardian governance VAA: `submitContractUpgrade`, module `Core` (`0x00000000000000000000000000000000000000000000000000000000436f7265`), emitter chain 1, emitter `0x0000000000000000000000000000000000000000000000000000000000000004`, signed by the current guardian set only |
| Guardian Governance | Not a proxy | 3,408 B full bytecode; implementation slot 0 | Guardian-signed VAA per call |
| Delegated Guardians | Not a proxy | 7,422 B; implementation slot 0 | Governance VAA (`submitConfig`) |
| Custom Consistency Level | Not a proxy | 507 B; implementation slot 0 | none (per-emitter self-service) |

An upgrade emits `Upgraded(address)` then `ContractUpgraded(old, new)` from the Core proxy. The implementation addresses in §4.1 are point-in-time; read the slot live.

---

## 7. Detection invariants & gotchas

1. **Filter `LogMessagePublished` on `sender` (`topic1`).** Measured senders in the pinned window, Ethereum: `SwiftDest` (`0xd78d199f8c402e7b5cc2abe278df0412400a3bae`) 731, Token Bridge 168, 19 NTT transceivers 67, Mayan's `MayanCircle` (`0x875d6d37ec55c8cf220b9e5080717549d8aa8eca`) 33, Wormhole Relayer 1, other integrators the rest. On BNB the Token Bridge sent 309 of 750. On Robinhood all 4 messages came from NTT transceivers.
2. **The message key is `(emitterChain, emitterAddress, sequence)`.** `sequence` counts per sender, from `nextSequence(sender)`. It is not global, and two senders can have the same `sequence`. `nonce` is not unique.
3. **The Core emits one log per message and never a destination log.** Destination products echo the key: Token Bridge `TransferRedeemed(emitterChainId, emitterAddress, sequence)`, Circle Integration `Redeemed(...)`, Wormhole Relayer `Delivery(..., sourceChain, sequence, ...)`, NTT transceiver `ReceivedMessage(digest, emitterChainId, emitterAddress, sequence)`.
4. **Guardian-set rotations are invisible in logs.** `submitNewGuardianSet` (`0x6606b4e0`) emits nothing. Detect it by the call selector, or poll `getCurrentGuardianSetIndex()` (7 today). The same is true for `submitSetMessageFee` and `submitTransferFees`: a fee withdrawal moves native value out of the Core with no event.
5. **`consistencyLevel` is the finality that the sender requests**, not a status. The guardians sign only after that finality. The Token Bridge requests 1 on Ethereum, Base, Arbitrum, Optimism and Avalanche, and 15 on BNB and Polygon (`finality()`, measured). Other applications choose their own value per message.
6. **`messageFee()` is 0 on all eight chains**, so a send transaction's `msg.value` is not a Core fee today. When a product forwards value, it is for the product (for example a relayer quote or WETH wrapping).
7. **Robinhood Chain has a Core but few products.** The Core, the Executor and NTT-with-Executor helpers exist on Robinhood. The Token Bridge, NFT Bridge, Wormhole Relayer and Circle Integration have no code there (`eth_getCode` = `0x` at every known address, and no entry in the docs list or the SDK). **Arc** is the same shape: Core, Executor, NTT-with-Executor v2 and CCTPv2WithExecutor exist; Token Bridge, NFT Bridge, Wormhole Relayer and Circle Integration return `0x`.
8. **Upgrades and governance come from Solana.** Every VAA-governed contract in this family checks `governanceChainId() == 1` and `governanceContract() == 0x0000000000000000000000000000000000000000000000000000000000000004`. There is no multisig owner to watch; watch the `submit*` selectors and the `Upgraded` / `ContractUpgraded` topics.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_LOG_MESSAGE_PUBLISHED   = '\x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2'
TOPIC_CONTRACT_UPGRADED       = '\x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49'
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_GUARDIAN_SET_ADDED      = '\x2384dbc52f7b617fb7c5aa71e5455a21ff21d58604bb6daef6af2bb44aadebdd'   -- declared, never emitted
TOPIC_CHAIN_CONFIG_SET        = '\x60521c8f957274659667169ced5f227b61b730968b22ef66f02a72f27394eba4'
TOPIC_CCL_CONFIG_SET          = '\xa37f0112e03d41de27266c1680238ff1548c0441ad1e73c82917c000eefdd5ea'

-- ===== Selectors =====
SEL_PUBLISH_MESSAGE           = '\xb19a437e'
SEL_PARSE_AND_VERIFY_VM       = '\xc0fd8bde'
SEL_SUBMIT_CONTRACT_UPGRADE   = '\x5cb8cae2'
SEL_SUBMIT_NEW_GUARDIAN_SET   = '\x6606b4e0'
SEL_SUBMIT_SET_MESSAGE_FEE    = '\xf42bc641'
SEL_SUBMIT_TRANSFER_FEES      = '\x93df337e'
SEL_SUBMIT_RECOVER_CHAIN_ID   = '\x178149e7'
SEL_GET_CURRENT_GUARDIAN_SET  = '\x1cfe7951'
SEL_MESSAGE_FEE               = '\x1a90a219'
SEL_NEXT_SEQUENCE             = '\x4cf842b5'
SEL_PERFORM_GOVERNANCE        = '\x56016724'
SEL_SUBMIT_CONFIG             = '\x555ff288'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
WH_GOVERNANCE_CONTRACT        = '\x0000000000000000000000000000000000000000000000000000000000000004'

-- ===== Core per chain =====
ETH_CORE                      = '\x98f3c9e6e3face36baad05fe09d375ef1464288b'
BASE_CORE                     = '\xbebdb6c8ddc678ffa9f8748f85c815c556dd8ac6'
ARB_CORE                      = '\xa5f208e072434bc67592e4c49c1b991ba79bca46'
OP_CORE                       = '\xee91c335eab126df5fdb3797ea9d6ad93aec9722'
POLY_CORE                     = '\x7a4b5a56256163f07b2c80a7ca55abe66c4ec4d7'
BNB_CORE                      = '\x98f3c9e6e3face36baad05fe09d375ef1464288b'
AVAX_CORE                     = '\x54a8e5f9c4cba08f9943965859f6c34eaf03e26c'
RH_CORE                       = '\x141fba8ad5d61bdab45a047cf60b5ad9784987fb'
ARC_CORE                      = '\xc8ad24fc6063c41cb5c12a8e3851aafc3b3cf027'

-- ===== Guardian-governed helpers =====
ETH_GUARDIAN_GOVERNANCE       = '\x23fea5514dfc9821479fbe18ba1d7e1a61f6ffcf'
BASE_GUARDIAN_GOVERNANCE      = '\x838a95b6a3e06b6f11c437e22f3c7561a6ec40f1'
ARB_GUARDIAN_GOVERNANCE       = '\x36cf4c88fa548c6ad9fcdc696e1c27bb3306163f'
OP_GUARDIAN_GOVERNANCE        = '\x0e09a3081837ff23d2e59b179e0bc48a349afbd8'
BNB_GUARDIAN_GOVERNANCE       = '\x8e4dc685e990379b8d53eca47841e09b8d30043e'
AVAX_GUARDIAN_GOVERNANCE      = '\x169d91c797edf56100f1b765268145660503a423'
ETH_DELEGATED_GUARDIANS       = '\x1462800febd49232798132e8c8b721aa86c4c209'
ETH_CUSTOM_CONSISTENCY_LEVEL  = '\x6a4b4a882f5f0a447078b4fd0b4b571a82371ec2'
```

---

## 9. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `ethereum/contracts/Implementation.sol`, `Governance.sol`, `State.sol`, `interfaces/IWormhole.sol`, `delegated_guardians/WormholeDelegatedGuardians.sol`, `custom_consistency_level/CustomConsistencyLevel.sol` and the NTT repo's `evm/src/wormhole/Governance.sol`. Each live Core implementation was scanned for the topics as `PUSH32` constants: `LogMessagePublished`, `ContractUpgraded` and `Upgraded` present on all eight; `GuardianSetAdded` absent on all eight.
- **Addresses:** the Core list of the Wormhole docs contract-address page and `core/base/src/constants/contracts/core.ts` of the SDK agree on all eight chains, Robinhood included. Every address was existence-checked with `eth_getCode`; implementation slots and admin slots were read live. `getCurrentGuardianSetIndex()` = 7, `messageFee()` = 0, `governanceChainId()` = 1 and `governanceContract()` = 4 on every chain; `chainId()` / `evmChainId()` returned the ids of §4.1. Arc (2026-10-05): the Core address is from `contracts/core.ts` of the SDK (not yet in the docs list); the same reads returned 71 / 5042, guardian set 7, fee 0, governance chain 1; the implementation contains `LogMessagePublished`, `ContractUpgraded` and `Upgraded`, not `GuardianSetAdded`.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):** `LogMessagePublished` at the Core: Ethereum 1,031, Base 174, Arbitrum 61, Optimism 9, Polygon 85, BNB 750, Avalanche 62, Robinhood 4; Arc 0 in the ~7 days to 2026-10-05 (`eth_getLogs`). `ContractUpgraded` and `GuardianSetAdded`: 0 on the seven chains scanned for them (all except Polygon). Sample: Robinhood transaction `0xd70f7def815e10b1f9c044a858c04bf6653232acc29839593bef2c577d15e4c5` shows the NTT flow (token burn, `LogMessagePublished` with `sender` = transceiver `0x352874cd039bd2f8e23ed203941c684912009d43`).
- **Sender attribution:** `SwiftDest` is the verified contract name of `0xd78d199f8c402e7b5cc2abe278df0412400a3bae` on the Ethereum Blockscout explorer (BscScan labels it "Mayan: Swift v2 Destination"); `MayanCircle` is the verified name of `0x875d6d37ec55c8cf220b9e5080717549d8aa8eca` on Polygon.

Authoritative sources:
- [wormhole-foundation/wormhole](https://github.com/wormhole-foundation/wormhole) — `ethereum/contracts/` (Core, governance, delegated guardians, custom consistency level)
- [wormhole-foundation/wormhole-sdk-ts](https://github.com/wormhole-foundation/wormhole-sdk-ts) — `core/base/src/constants/chains.ts` (Wormhole chain ids) and `core/base/src/constants/contracts/core.ts`
- [wormhole-foundation/native-token-transfers](https://github.com/wormhole-foundation/native-token-transfers) — `evm/src/wormhole/Governance.sol` (Guardian Governance)
- Docs — [Contract addresses](https://wormhole.com/docs/reference/contract-addresses/) · [Supported networks and chain ids](https://wormhole.com/docs/reference/supported-networks/) · [Wormhole finality](https://wormhole.com/docs/reference/consistency-levels/) · [Core contracts](https://wormhole.com/docs/protocol/infrastructure/core-contracts/)
- Explorers — [Etherscan Core](https://etherscan.io/address/0x98f3c9e6e3face36baad05fe09d375ef1464288b) · [Basescan Core](https://basescan.org/address/0xbebdb6c8ddc678ffa9f8748f85c815c556dd8ac6) · [Robinhood Chain Blockscout Core](https://robinhoodchain.blockscout.com/address/0x141fBa8AD5D61bdaB45A047cF60b5Ad9784987FB) · [Ethereum Blockscout `SwiftDest`](https://eth.blockscout.com/address/0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe)
