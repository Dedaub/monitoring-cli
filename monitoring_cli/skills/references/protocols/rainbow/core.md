# Rainbow Bridge (legacy) — Topics, Selectors, Addresses (Ethereum L1 only)

**Status:** verified against live RPC on Ethereum mainnet and all six other listed chains, and the canonical `aurora-is-near` / `Near-One` repos (`rainbow-bridge`, `rainbow-token-connector`, `eth-connector`), on 2026-06-09.
**Scope:** the **Ethereum-side** contracts of the original NEAR ⇄ Ethereum **Rainbow Bridge** — the light-client / Merkle-proof connector (NearBridge, NearProver) plus its three asset connectors (ERC20Locker, EthCustodian, eNEAR). Topics and selectors are **chain-agnostic**; addresses are network-specific. The counterparty is **NEAR Protocol (non-EVM)** — NEAR-side accounts are recorded by name but cannot be `eth_getCode`-checked. **Every contract in this file exists only on Ethereum mainnet (chain 1)**; all return `0x` on Base, BNB, Avalanche, Arbitrum, Optimism, and Polygon (verified §5).

Rainbow Bridge is a **trustless, light-client + Merkle-proof bridge**: a Solidity NEAR-light-client (`NearBridge`/EthClient) stores recent NEAR block hashes and Merkle roots on Ethereum; `NearProver`/EthProver verifies that a given NEAR receipt/outcome is committed under one of those roots; and three **asset connectors** consume those proofs to release value — `ERC20Locker` (locks/unlocks any ERC-20), `EthCustodian` (holds/releases native ETH for the Aurora EVM), and `eNEAR` (the bridged NEAR ERC-20, mints/burns). There are **no factories and no per-token vault contracts on Ethereum**: every locked ERC-20 sits inside the single `ERC20Locker`; the NEAR-side `factory.bridge.near` mints the mirrored NEP-141. All contracts are **immutable, non-proxy** (EIP-1967 impl slot = `0x0`) and governed by a custom `AdminControlled` pattern (an `admin` EOA/multisig with `adminPause`, `adminSstore`, `adminDelegatecall`, two-step `nominateAdmin`/`acceptAdmin`).

> **DEPRECATION (the single most important fact for a monitor):** this legacy light-client Rainbow Bridge is **sunset / deposits paused** and has been migrated to the MPC-validated **NEAR Omni Bridge** (`0xe00c629aFaCCb0510995A2B95560E446A24c85B9`, a UUPS proxy created block 22,188,279 / 2025; **out of scope for this file**). Live confirmation 2026-06-09: `ERC20Locker.paused()` = `1` (`PAUSED_LOCK` set → `lockToken` reverts for non-admin); `EthCustodian.paused()` = `3` (both deposit paths paused); the active `NearBridge` (`0x3fefc5a4…`) `paused()` = `0xd`; and **zero `Locked`/`Deposited`/`Unlocked`/`Withdrawn` events in the last ~2,000,000 blocks (~10 months)**. The contracts remain on-chain (still hold/release residual funds), so a monitor should index them for *withdrawals/unlocks* (the only remaining flows) and for **admin actions**, not for new deposits.

> **Two NearBridge (EthClient) deployments — pick the right one.** The original light client is `0x0151568a…` (created block 12,272,165 / Apr 2021). It was superseded by `0x3fefc5a4…` (created block 15,617,816 / Sep 2022), which is the one the live `NearProver` (`0x051ad3f0…`) points to via `bridge()`. **Both still return a current NEAR head from `bridgeState()`**, so both look "live" — always key on `(chainId, address)` and treat `0x3fefc5a4…` as canonical because the production `NearProver` resolves to it.

---

## 0. Contract families & versions

| Contract | Role | Repo source | Proxy? | NEAR-side counterpart |
|----------|------|-------------|--------|------------------------|
| **NearBridge** (a.k.a. EthClient) | NEAR light client on Ethereum: stores NEAR block hashes + Merkle roots; `addLightClientBlock` / `challenge` (optimistic Ed25519 fraud proofs). | `rainbow-bridge/contracts/eth/nearbridge` | **No** (immutable, `AdminControlled`) | EthOnNearClient (Rust on NEAR) |
| **NearProver** (a.k.a. EthProver) | Verifies a NEAR receipt/outcome proof against a root held by `NearBridge`. `proveOutcome` is the gate every connector calls. | `rainbow-bridge/contracts/eth/nearprover` | **No** (immutable, `AdminControlled`) | EthOnNearProver |
| **ERC20Locker** | Escrows arbitrary ERC-20s when bridging ETH→NEAR (`lockToken` → `Locked`); releases them on a burn proof from NEAR (`unlockToken` → `Unlocked`). Single shared vault for all tokens. | `rainbow-token-connector/erc20-connector` | **No** (immutable, `Locker` + `AdminControlled`) | `factory.bridge.near` (NEP-141 factory) |
| **EthCustodian** | Holds native **ETH** for the Aurora EVM bridge: `depositToEVM` / `depositToNear` → `Deposited`; releases on burn proof of nETH (`withdraw` → `Withdrawn`). | `eth-connector/eth-custodian` | **No** (immutable, `ProofKeeper` + `AdminControlled`) | `aurora` (the Aurora EVM account) |
| **eNEAR** (NEAR ERC-20) | The bridged **NEAR** token on Ethereum (24 dec). `transferToNear` burns + emits `TransferToNearInitiated`; `finaliseNearToEthTransfer` mints on a NEAR proof (`NearToEthTransferFinalised`). | aurora-is-near `e-near` | **No** (immutable, `AdminControlled`) | `e-near.near` |

The `ERC20Locker`, `EthCustodian`, and `eNEAR` all inherit the same proof-consuming base (`Locker`/`ProofKeeper`) — they each hold an immutable `prover` pointer (→ `NearProver 0x051ad3f0…`), an immutable NEAR producer account, and a `usedProofs`/`usedEvents_` replay-guard mapping.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak256 on 2026-06-09 and cross-checked against live `eth_getLogs` (historical, since deposits are paused) — see the per-row "verified" notes and §8.

### 1.1 ERC20Locker — emitter `0x23ddd3e3692d1861ed57ede224608875809e127f`

| topic0 | Event |
|--------|-------|
| `0xdd85dc56b5b4da387bf69c28ec19b1d66e793e0d51b567882fa31dc50bbd32c5` | `Locked(address indexed token, address indexed sender, uint256 amount, string accountId)` — *verified live: 962 logs @ block ~14.0M, 3 topics* |
| `0x5fd575e9a8dd4ba1e9f434728800fe78c3c5ffccfa6a852bc7415294ecc0c2d5` | `Unlocked(uint128 amount, address recipient)` — *verified live: 425 logs, 1 topic (no indexed)* |

`Locked.accountId` is the destination NEAR account (string, **not** an EVM address). `Unlocked` has **no indexed fields** — you cannot topic-filter by recipient; decode `data`.

### 1.2 EthCustodian — emitter `0x6BFaD42cFC4EfC96f529D786D643Ff4A8B89FA52`

| topic0 | Event |
|--------|-------|
| `0xd142439c278e25dad9a50766f153d0e3d2d7bf2bd16fc2781c4bd494b2b15a9d` | `Deposited(address indexed sender, string recipient, uint256 amount, uint256 fee)` — *verified live: 1586 logs, 2 topics (sender indexed)* |
| `0xab48b3d59a240196dc5bdd7f7a638fca310f8194c7d350c3dd7765861311ddf8` | `Withdrawn(address indexed recipient, uint128 amount)` — *verified live: 298 logs, 2 topics (recipient indexed)* |

`Deposited` fires from **both** `depositToEVM` and `depositToNear` (same event); the destination is encoded in the `recipient` string (`depositToEVM` prefixes the NEAR EVM producer account + `:` separator; `depositToNear` is a raw NEAR account id). `amount` is `msg.value`; `fee` is the relayer fee subtracted on the NEAR side (not a separate transfer).

### 1.3 eNEAR (NEAR ERC-20) — emitter `0x85f17cf997934a597031b2e18a9ab6ebd4b9f6a4`

| topic0 | Event |
|--------|-------|
| `0xabeef16c62fe7504587dd9ef5d707aeb0932570da8eb1a4f099c6e80524b17c3` | `TransferToNearInitiated(address indexed sender, uint256 amount, string accountId)` — *verified live: 5 logs @ ~12.5M, 2 topics* |
| `0x3538c3349544a9ce6d1cfda849857b2b8fa919c15fe6d382e08573b9838d2aa8` | `NearToEthTransferFinalised(uint128 amount, address indexed recipient)` — *verified live: 4 logs, 2 topics* |
| `0xb226e263cb7a3bde6afd6e46c543e956d49171b4fe4f0daf93cb1798f2315d1d` | `ConsumedProof(bytes32 indexed receiptId)` — replay-guard marker fired when a NEAR→ETH proof is consumed; *verified live: 4 logs, 2 topics* |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — standard ERC-20 (mint = from 0x0, burn = to 0x0) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` — standard ERC-20 |

A NEAR→ETH eNEAR transfer = `Transfer(0x0 → recipient)` **+** `NearToEthTransferFinalised` **+** `ConsumedProof`. An ETH→NEAR transfer = `Transfer(sender → 0x0)` **+** `TransferToNearInitiated`.

### 1.4 NearBridge (EthClient) — emitter `0x3fefc5a4…` (canonical) / `0x0151568a…` (legacy)

The `INearBridge` interface declares `BlockHashAdded(uint64,bytes32)` (`0x5d45c22c…`) and `BlockHashReverted(uint64,bytes32)` (`0x4e9ddd5d…`), **but neither topic is present in the deployed bytecode of either NearBridge** (grep of `eth_getCode` returns 0 occurrences on both `0x3fefc5a4…` and `0x0151568a…`), and `eth_getLogs` returns **0 logs of any topic** from these contracts in their active eras. **The deployed light client emits NO events** — `addLightClientBlock` updates the `blockHashes` / `blockMerkleRoots` storage mappings silently. See §9.1 — you cannot track NEAR header submission by event; watch the `addLightClientBlock` **call** (selector `0x6d2d6ae0`) instead.

| topic0 | Event | Status |
|--------|-------|--------|
| `0x5d45c22c440038a3aaf9f8134e7aa1fa59aa2a7fa411d7e818d7701c63827d7e` | `BlockHashAdded(uint64 indexed height, bytes32 blockHash)` | **interface-only; NOT emitted by deployed bytecode** |
| `0x4e9ddd5df7d5ac983348809fe8a0617e2e53415abf6f504c73ee2b2b22076ef6` | `BlockHashReverted(uint64 indexed height, bytes32 blockHash)` | **interface-only; NOT emitted by deployed bytecode** |

### 1.5 NearProver — emitter `0x051ad3f020274910065dcb421629cd2e6e5b46c4`

`NearProver` and `AdminControlled` declare **no events** (it is a pure verifier + admin pointer). `proveOutcome` is `view` and emits nothing.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Selectors recomputed locally 2026-06-09. "present/ABSENT" = scanned in the live deployed bytecode.

### 2.1 ERC20Locker

| Selector | Signature | Returns/notes |
|----------|-----------|---------------|
| `0x0889bfe7` | `lockToken(address ethToken, uint256 amount, string accountId)` | Escrow → emits `Locked`. **present.** Currently `PAUSED_LOCK` (reverts for non-admin). |
| `0x4a00c629` | `unlockToken(bytes proofData, uint64 proofBlockHeight)` | Release on NEAR burn proof → emits `Unlocked`. **present.** |
| `0xda72c1e8` | `adminTransfer(address token, address destination, uint256 amount)` | Admin sweep of escrowed ERC-20. **present.** |
| `0xf851a440` | `admin()` → `address` | **present.** Returns `0x2468603819bF09ed3FB6F3EFEFf24b1955F3CdE1`. |
| `0x5c975abb` | `paused()` → `uint256` | **present.** Bitmask (`1`=PAUSED_LOCK, `2`=PAUSED_UNLOCK). Live value `1`. |
| `0x2692c59f` | `adminPause(uint256 flags)` | **present.** Admin-only. |
| `0x32a8f30f` | `prover()` → `address` | **ABSENT** — the deployed Locker predates the public getter. Read **storage slot 0** instead (= `0x051ad3f0…`, verified). |
| `0x4a6295dc` | `nearTokenFactory()` → `bytes` | **ABSENT** — read **storage slot 1** instead (= `"factory.bridge.near"`, verified). |
| `0xc30a0f25` | `usedProofs(bytes32)` → `bool` | Replay-guard mapping (slot 3). |

### 2.2 EthCustodian

| Selector | Signature | Returns/notes |
|----------|-----------|---------------|
| `0xed940ed7` | `depositToEVM(string ethRecipientOnNear, uint256 fee)` `payable` | → emits `Deposited`. **present.** |
| `0xa8eb3b51` | `depositToNear(string nearRecipientAccountId, uint256 fee)` `payable` | → emits `Deposited`. **present.** |
| `0x9813954e` | `withdraw(bytes proofData, uint64 proofBlockHeight)` | Release ETH on nETH burn proof → emits `Withdrawn`. **present.** |
| `0xbb00b698` | `prover_()` → `address` | **present.** Returns `0x051ad3f0…` (the same `NearProver`). |
| `0x79ac038a` | `nearProofProducerAccount_()` → `bytes` | **present.** Returns `"aurora"`. |
| `0x1c420a20` | `minBlockAcceptanceHeight_()` → `uint64` | Min NEAR block height accepted. |
| `0xf851a440` | `admin()` → `address` | Returns `0x2468603819bF09ed3FB6F3EFEFf24b1955F3CdE1`. |
| `0x5c975abb` | `paused()` → `uint256` | `1`=DEPOSIT_TO_EVM, `2`=DEPOSIT_TO_NEAR, `4`=WITHDRAW. Live value `3` (both deposits paused). |

### 2.3 NearProver

| Selector | Signature | Returns/notes |
|----------|-----------|---------------|
| `0x92d68dfd` | `proveOutcome(bytes proofData, uint64 blockHeight)` → `bool` | **present.** `view`; the verification gate every connector calls. |
| `0xe78cea92` | `bridge()` → `address` | **present.** Returns the linked `NearBridge` = `0x3fefc5a4…`. |
| `0xf851a440` | `admin()` → `address` | **present.** Returns `0x2468…CdE1`. |

### 2.4 NearBridge (EthClient)

| Selector | Signature | Returns/notes |
|----------|-----------|---------------|
| `0xd0e30db0` | `deposit()` `payable` | **present.** Relayer stakes ETH to submit blocks (challengeable). |
| `0x3ccfd60b` | `withdraw()` | **present.** Relayer unstakes. |
| `0x6d2d6ae0` | `addLightClientBlock(bytes data)` | **present.** Submit a NEAR light-client block. **Emits no event — watch the call** (§9.1). |
| `0xacb99828` | `challenge(address payable receiver, uint256 signatureIndex)` | **present.** Optimistic fraud-proof challenge (Ed25519). |
| `0xa3155fbb` | `checkBlockProducerSignatureInHead(uint256 signatureIndex)` → `bool` | `view`. |
| `0x37da8ec5` | `blockHashes(uint64 height)` → `bytes32` | NEAR block hash by height. |
| `0x1e703806` | `blockMerkleRoots(uint64 height)` → `bytes32` | Merkle root used by `NearProver`. |
| `0x4466ec2c` | `bridgeState()` → `(currentHeight, nextTimestamp, numBlockProducers)` | Returns current NEAR head; live on both deployments. |
| `0x160bc0ba` | `initWithBlock(bytes)` | admin-only init. |
| `0x09d7e8e7` | `initWithValidators(bytes)` | admin-only init. |
| `0x70a08231` | `balanceOf(address)` → `uint256` | Relayer stake balance. |

### 2.5 eNEAR (NEAR ERC-20)

| Selector | Signature | Returns/notes |
|----------|-----------|---------------|
| `0xe3113e3b` | `transferToNear(uint256 amount, string accountId)` | Burn + emit `TransferToNearInitiated`. **present.** |
| `0x3a239bee` | `finaliseNearToEthTransfer(bytes proofData, uint64 proofBlockHeight)` | Mint on NEAR proof → `NearToEthTransferFinalised` + `ConsumedProof`. **present.** |
| `0x70a08231` / `0xa9059cbb` / `0x95d89b41` | `balanceOf` / `transfer` / `symbol` | Standard ERC-20 (`symbol()` = `"NEAR"`, 24 dec). |
| `0xf851a440` | `admin()` → `address` | Returns `0x150C79c8a70b1d528E95E200c6Ca5ED0421C44f7`. |

### 2.6 AdminControlled (inherited by ERC20Locker, EthCustodian, NearBridge, NearProver, eNEAR)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2692c59f` | `adminPause(uint256 flags)` | Set the `paused` bitmask. |
| `0xcd5ad4c5` | `nominateAdmin(address)` | Two-step admin handover (step 1). |
| `0x0e18b681` | `acceptAdmin()` | Step 2 — nominated admin accepts. |
| `0xac77a535` | `rejectNominatedAdmin()` | Cancel a pending nomination. |
| `0xbe831a2e` | `adminSstore(uint256 key, uint256 value)` | **Raw storage write** — admin can overwrite any slot. |
| `0x6c4624c3` | `adminSstoreWithMask(uint256 key, uint256 value, uint256 mask)` | Masked raw storage write. |
| `0x530208f2` | `adminSendEth(address payable destination, uint256 amount)` | Admin ETH withdrawal. |
| `0xf48ab4e0` | `adminReceiveEth()` `payable` | |
| `0xb8e9744c` | `adminDelegatecall(address target, bytes data)` `payable` | **Arbitrary delegatecall** — the broadest admin power; treat as upgrade-equivalent. |

`AdminControlled` defines **no events** — admin actions are storage writes / pause-flag changes with **no log**. Detect them by `tx.to ∈ {contracts}` AND `tx.input[0:4] ∈ {adminPause, adminSstore, adminSstoreWithMask, adminDelegatecall, nominateAdmin, acceptAdmin, adminTransfer, adminSendEth}` (§9.4).

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Linkages confirmed on-chain: `EthCustodian.prover_()` and `ERC20Locker` storage-slot-0 both → `NearProver`; `NearProver.bridge()` → `NearBridge 0x3fefc5a4…`.

| Role | Address | Created (block) | One-liner |
|------|---------|-----------------|-----------|
| **ERC20Locker** | `0x23ddd3e3692d1861ed57ede224608875809e127f` | 12,044,301 | Single shared escrow vault for all bridged ERC-20s. `Locked`/`Unlocked`. **`paused()=1`.** |
| **EthCustodian** | `0x6BFaD42cFC4EfC96f529D786D643Ff4A8B89FA52` | 12,702,964 | Native-ETH custodian for the Aurora EVM. `Deposited`/`Withdrawn`. **`paused()=3`.** NEAR producer = `aurora`. |
| **eNEAR (NEAR ERC-20)** | `0x85f17cf997934a597031b2e18a9ab6ebd4b9f6a4` | 12,475,891 | Bridged NEAR token (24 dec). `TransferToNearInitiated`/`NearToEthTransferFinalised`/`ConsumedProof`. NEAR side = `e-near.near`. |
| **NearProver** (EthProver) | `0x051ad3f020274910065dcb421629cd2e6e5b46c4` | 12,040,114 | Merkle-proof verifier (`proveOutcome`) used by all three connectors. `bridge()` → `0x3fefc5a4…`. |
| **NearBridge** (EthClient, **canonical**) | `0x3fefc5a4b1c02f21cbc8d3613643ba0635b9a873` | 15,617,816 | NEAR light client the live `NearProver` resolves to. `paused()=0xd`. **Emits no events.** |
| NearBridge (EthClient, **legacy, superseded**) | `0x0151568af92125fb289f1dd81d9d8f7484efc362` | 12,272,165 | Original 2021 light client; still returns a NEAR head from `bridgeState()` but the production prover no longer points here. **Emits no events.** Different admin (`0xB8e1…16D9`). |
| eNEAR minter/prover helper | `0xe2c20f46554fEf9F5b94966029120149a61675a6` | — | Small (~230 B) helper referenced from eNEAR storage slot 5; mint authority side. |
| **admin** (ERC20Locker / EthCustodian / NearProver / canonical NearBridge) | `0x2468603819bF09ed3FB6F3EFEFf24b1955F3CdE1` | EOA/multisig | `admin()` of the four core connector contracts. |
| admin (eNEAR) | `0x150C79c8a70b1d528E95E200c6Ca5ED0421C44f7` | EOA/multisig | `admin()` of the NEAR ERC-20. |
| admin (legacy NearBridge `0x0151…`) | `0xB8e11A1Ad588863379a3e523b37d8C78070C16d9` | EOA/multisig | `admin()` of the superseded light client. |

NEAR-side counterparts (non-EVM — recorded, not `eth_getCode`-checkable): `factory.bridge.near` (ERC20Locker token factory), `aurora` (EthCustodian / Aurora EVM), `e-near.near` (eNEAR), `client.bridge.near` / `prover.bridge.near` (the Ethereum-light-client + prover **on** NEAR, the mirror image of `NearBridge`/`NearProver`).

> **Successor (out of scope, recorded for completeness):** **NEAR Omni Bridge** `0xe00c629aFaCCb0510995A2B95560E446A24c85B9` — a **UUPS proxy** (EIP-1967 impl slot = `0x53785920165fbdf33b3f56885dbc8d12854ac414`, ~16.7 KB impl; admin slot empty), created block 22,188,279 (2025). MPC/Chain-Signatures validated, **not** light-client based. Document it separately if Omni Bridge monitoring is required.

---

## 4. Decimals & encoding

- **eNEAR / NEAR ERC-20 is 24 decimals** (matches NEAR's yoctoNEAR scaling), **not 18** — `symbol()="NEAR"`, `name()="NEAR"`. Verified `decimals()=0x18`=24.
- `Locked.amount` and `Deposited.amount` are in the **locked token's / ETH's** native decimals; `Unlocked.amount` and `Withdrawn.amount` are `uint128` (the NEAR-side burn amount).
- `EthCustodian.fee` is the relayer fee in nETH, **subtracted on the NEAR side** — it is part of `msg.value`, not an extra ETH transfer.
- NEAR destinations are **strings** (`accountId` / `recipient`), e.g. `alice.near`, never EVM addresses.

---

## 5. Cross-chain summary

Every Rainbow Bridge contract is **Ethereum-mainnet-only**. `eth_getCode` returned `0x` for all of them on each of the other six requested chains on 2026-06-09.

| Chain | ID | ERC20Locker | EthCustodian | eNEAR | NearProver | NearBridge | OmniBridge (successor) |
|---|---|---|---|---|---|---|---|
| **Ethereum** | 1 | ✅ `0x23ddd3…` | ✅ `0x6BFaD4…` | ✅ `0x85f17c…` | ✅ `0x051ad3…` | ✅ `0x3fefc5…` (+legacy `0x0151…`) | ✅ `0xe00c62…` |
| Base | 8453 | — | — | — | — | — | — |
| BNB | 56 | — | — | — | — | — | — |
| Avalanche | 43114 | — | — | — | — | — | — |
| Arbitrum One | 42161 | — | — | — | — | — | — |
| Optimism | 10 | — | — | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — | — | — |

**Counterparty chain is NEAR Protocol (non-EVM) — outside the seven requested chains.** The bridge also fed **Aurora** (the NEAR-hosted EVM, chain ID 1313161554, also outside the seven) via `EthCustodian` (NEAR producer `aurora`). No bridged Rainbow Bridge contract exists on any of the seven L2/alt-L1 targets — the canonical contracts are anchored on Ethereum L1 and mirrored only on NEAR.

No vanity addresses (the contracts predate vanity-deploy conventions); identity must be confirmed by linkage (`prover_()` / `bridge()` / storage slot 0), not by address pattern.

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| ERC20Locker | **Immutable, non-proxy** | EIP-1967 impl slot `0x3608…2bbc` = `0x0` (verified); ~9.1 KB full bytecode. | `AdminControlled.admin` — no code upgrade; admin can `adminSstore`/`adminDelegatecall` (storage rewrite / arbitrary delegatecall, effectively unbounded). |
| EthCustodian | **Immutable, non-proxy** | impl slot = `0x0`; ~8.5 KB. | same `AdminControlled` pattern. |
| eNEAR | **Immutable, non-proxy** | impl slot = `0x0`; ~10.5 KB. | `AdminControlled.admin` (`0x150C79c8…`). |
| NearProver | **Immutable, non-proxy** | impl slot = `0x0`; ~6.2 KB. | `AdminControlled.admin`. |
| NearBridge (both) | **Immutable, non-proxy** | impl slot = `0x0` on `0x3fefc5a4…` and `0x0151568a…`; ~10.8 KB and ~9.7 KB. | `AdminControlled.admin`. |
| **OmniBridge** (successor) | **UUPS proxy** (ERC-1967) | impl slot `0x3608…2bbc` = `0x53785920165fbdf33b3f56885dbc8d12854ac414` (set); admin slot empty; ~170 B proxy. | UUPS `owner`/`upgradeToAndCall`; watch `Upgraded(address)` topic `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. |

**There is no `Upgraded(address)` event to watch on any legacy Rainbow Bridge contract — they are not proxies.** The upgrade-equivalent risk is the `AdminControlled` admin calling `adminSstore`/`adminSstoreWithMask`/`adminDelegatecall` (no event). EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` and admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` both read `0x0` on all six legacy contracts (confirmed not EIP-1967 proxies).

---

## 7. (reserved)

---

## 8. Verifying topics against live logs (how the §1 values were proven)

Because deposits are paused, recent windows are empty; the topics were confirmed against the bridge's active era (2021–2022). Representative confirmations on `https://ethereum-rpc.publicnode.com`, 2026-06-09:

- `ERC20Locker.Locked` `0xdd85dc56…` — **962 logs** in blocks 14,000,000–14,049,000, 3 topics (token + sender indexed). 
- `EthCustodian.Deposited` `0xd142439c…` — **1586 logs**, 2 topics (sender indexed).
- `EthCustodian.Withdrawn` `0xab48b3d5…` — **298 logs**, 2 topics (recipient indexed).
- `ERC20Locker.Unlocked` `0x5fd575e9…` — **425 logs**, 1 topic (no indexed).
- `eNEAR.TransferToNearInitiated` `0xabeef16c…`, `NearToEthTransferFinalised` `0x3538c334…`, `ConsumedProof` `0xb226e263…` — confirmed in eNEAR logs from block ~12.48M (2 topics each).
- `NearBridge` `0x3fefc5a4…` / `0x0151568a…` — **0 logs of any topic** in their active eras; `BlockHashAdded`/`BlockHashReverted` topic bytes **absent from deployed bytecode** → confirmed event-less light client (§1.4, §9.1).

---

## 9. Detection invariants & gotchas

1. **The light client emits NOTHING.** Both `NearBridge` deployments return zero `eth_getLogs` and do not carry the `BlockHashAdded`/`BlockHashReverted` topic bytes in their bytecode. **You cannot index NEAR-header submission by event.** To track it, watch **transactions calling `addLightClientBlock` (selector `0x6d2d6ae0`)** to the bridge address, or poll `bridgeState()` / `blockHashes(height)`. The `INearBridge` events are interface-only vestiges — do not configure an alert on `0x5d45c22c…`/`0x4e9ddd5d…` for this bridge; it will never fire.

2. **Bridge is deprecated / deposits paused.** `ERC20Locker.paused()=1`, `EthCustodian.paused()=3`. New `Locked`/`Deposited` should not appear; if one does, it came from the **admin** (the `pausable` modifier exempts `msg.sender == admin`) — treat an admin-originated deposit as a notable event. The only organic remaining flows are `Unlocked` / `Withdrawn` / eNEAR `NearToEthTransferFinalised` (NEAR→ETH withdrawals draining residual escrow).

3. **Two NearBridge / EthClient addresses.** `0x3fefc5a4…` is canonical (the live `NearProver.bridge()` resolves to it); `0x0151568a…` is the superseded 2021 client and has a **different admin** (`0xB8e1…16D9`). Both answer `bridgeState()` — do not assume "responds = canonical." Key on `(chainId, address)`.

4. **Admin actions have no events.** `AdminControlled` (admin pause, `adminSstore`, `adminSstoreWithMask`, `adminDelegatecall`, `adminTransfer`, `adminSendEth`, two-step admin handover) emits no log. Detect admin/governance activity by **`tx.to` = a bridge contract AND `tx.input[0:4]` ∈ the §2.6 selector set**. `adminDelegatecall` (`0xb8e9744c`) is upgrade-equivalent (arbitrary delegatecall) — highest-priority admin alert.

5. **`Unlocked` has no indexed fields** (`0x5fd575e9…`, 1 topic) — you must ABI-decode `data` for `(uint128 amount, address recipient)`; you cannot topic-filter by recipient.

6. **The real destination is a NEAR account string, not an EVM address.** `Locked.accountId`, `Deposited.recipient`, `TransferToNearInitiated.accountId` are strings (e.g. `alice.near`). `Deposited` from `depositToEVM` additionally prefixes the NEAR EVM producer + `:` separator — parse accordingly. The indexed `sender` is the Ethereum payer.

7. **One shared ERC20Locker vault, no per-token contracts.** Every bridged ERC-20 is escrowed inside `0x23ddd3…`; there is no factory and no per-asset vault on Ethereum. Attribute the locked asset from `Locked.token` (indexed), not from the emitter.

8. **eNEAR is 24 decimals.** A `Transfer`/`TransferToNearInitiated` `amount` of `1e24` = 1 NEAR. Do not apply 18-dec assumptions.

9. **eNEAR NEAR→ETH = three logs** in one tx: ERC-20 `Transfer(0x0→recipient)` + `NearToEthTransferFinalised` + `ConsumedProof(receiptId)`. Use `ConsumedProof`'s indexed `receiptId` as the NEAR-side dedup key.

10. **`ERC20Locker` has no `prover()` / `nearTokenFactory()` getters** — those selectors are ABSENT from the deployed bytecode (it predates them). Read **storage slot 0** for the prover (`0x051ad3f0…`) and **slot 1** for the factory (`"factory.bridge.near"`). `EthCustodian` *does* expose `prover_()`/`nearProofProducerAccount_()`.

11. **Proof replay guards.** `ERC20Locker.usedProofs(bytes32)`, `EthCustodian.usedEvents_(bytes32)`, and eNEAR's `ConsumedProof` mark a NEAR receipt as consumed — the NEAR receipt id is the cross-chain idempotency key. A second `unlockToken`/`withdraw` with the same receipt reverts.

12. **Not deployed off-Ethereum.** All addresses return `0x` on Base/BNB/Avalanche/Arbitrum/Optimism/Polygon. The counterparties are **NEAR** (chain 1313161554-adjacent / non-EVM) and **Aurora** (NEAR-hosted EVM) — both outside the seven requested chains.

13. **`EthCustodian.Deposited` fires from two functions** (`depositToEVM` and `depositToNear`) with the same topic0 — disambiguate the destination by parsing the `recipient` string, not by topic.

14. **Successor confusion.** `0xe00c629a…` (Omni Bridge) is a UUPS proxy on a totally different (MPC) trust model and is NOT part of this light-client bridge. Don't mix its events/selectors into legacy Rainbow Bridge detection.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- ERC20Locker
TOPIC_LOCKED                         = '\xdd85dc56b5b4da387bf69c28ec19b1d66e793e0d51b567882fa31dc50bbd32c5'
TOPIC_UNLOCKED                       = '\x5fd575e9a8dd4ba1e9f434728800fe78c3c5ffccfa6a852bc7415294ecc0c2d5'
-- EthCustodian
TOPIC_DEPOSITED                      = '\xd142439c278e25dad9a50766f153d0e3d2d7bf2bd16fc2781c4bd494b2b15a9d'
TOPIC_WITHDRAWN                      = '\xab48b3d59a240196dc5bdd7f7a638fca310f8194c7d350c3dd7765861311ddf8'
-- eNEAR (NEAR ERC-20)
TOPIC_TRANSFER_TO_NEAR_INITIATED     = '\xabeef16c62fe7504587dd9ef5d707aeb0932570da8eb1a4f099c6e80524b17c3'
TOPIC_NEAR_TO_ETH_FINALISED          = '\x3538c3349544a9ce6d1cfda849857b2b8fa919c15fe6d382e08573b9838d2aa8'
TOPIC_CONSUMED_PROOF                 = '\xb226e263cb7a3bde6afd6e46c543e956d49171b4fe4f0daf93cb1798f2315d1d'
TOPIC_ERC20_TRANSFER                 = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- NearBridge interface-only (NOT emitted by deployed bytecode — DO NOT alert)
TOPIC_BLOCK_HASH_ADDED_VESTIGIAL     = '\x5d45c22c440038a3aaf9f8134e7aa1fa59aa2a7fa411d7e818d7701c63827d7e'
TOPIC_BLOCK_HASH_REVERTED_VESTIGIAL  = '\x4e9ddd5df7d5ac983348809fe8a0617e2e53415abf6f504c73ee2b2b22076ef6'

-- ===== Selectors =====
-- ERC20Locker
SEL_LOCK_TOKEN                       = '\x0889bfe7'
SEL_UNLOCK_TOKEN                     = '\x4a00c629'
SEL_ADMIN_TRANSFER                   = '\xda72c1e8'
-- EthCustodian
SEL_DEPOSIT_TO_EVM                   = '\xed940ed7'
SEL_DEPOSIT_TO_NEAR                  = '\xa8eb3b51'
SEL_CUSTODIAN_WITHDRAW               = '\x9813954e'
SEL_PROVER_                          = '\xbb00b698'
-- eNEAR
SEL_TRANSFER_TO_NEAR                 = '\xe3113e3b'
SEL_FINALISE_NEAR_TO_ETH             = '\x3a239bee'
-- NearProver
SEL_PROVE_OUTCOME                    = '\x92d68dfd'
SEL_BRIDGE                           = '\xe78cea92'
-- NearBridge (watch the CALL — no event)
SEL_ADD_LIGHT_CLIENT_BLOCK           = '\x6d2d6ae0'
SEL_CHALLENGE                        = '\xacb99828'
SEL_BRIDGE_DEPOSIT                   = '\xd0e30db0'
SEL_BRIDGE_STATE                     = '\x4466ec2c'
SEL_BLOCK_MERKLE_ROOTS               = '\x1e703806'
-- AdminControlled (no events — detect by call)
SEL_ADMIN_PAUSE                      = '\x2692c59f'
SEL_NOMINATE_ADMIN                   = '\xcd5ad4c5'
SEL_ACCEPT_ADMIN                     = '\x0e18b681'
SEL_ADMIN_SSTORE                     = '\xbe831a2e'
SEL_ADMIN_SSTORE_WITH_MASK           = '\x6c4624c3'
SEL_ADMIN_SEND_ETH                   = '\x530208f2'
SEL_ADMIN_DELEGATECALL               = '\xb8e9744c'
SEL_ADMIN                            = '\xf851a440'
SEL_PAUSED                           = '\x5c975abb'

-- ===== Proxy slots (legacy = empty; successor = set) =====
EIP1967_IMPL_SLOT                    = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                   = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
TOPIC_UPGRADED_OMNI                  = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Addresses — Ethereum mainnet (chain ID 1) — ONLY chain with deployments =====
ETH_ERC20_LOCKER                     = '\x23ddd3e3692d1861ed57ede224608875809e127f'
ETH_ETH_CUSTODIAN                    = '\x6bfad42cfc4efc96f529d786d643ff4a8b89fa52'
ETH_ENEAR                            = '\x85f17cf997934a597031b2e18a9ab6ebd4b9f6a4'
ETH_NEAR_PROVER                      = '\x051ad3f020274910065dcb421629cd2e6e5b46c4'
ETH_NEAR_BRIDGE_CANONICAL            = '\x3fefc5a4b1c02f21cbc8d3613643ba0635b9a873'
ETH_NEAR_BRIDGE_LEGACY               = '\x0151568af92125fb289f1dd81d9d8f7484efc362'
ETH_ENEAR_MINTER_HELPER              = '\xe2c20f46554fef9f5b94966029120149a61675a6'
ETH_ADMIN_CORE                       = '\x2468603819bf09ed3fb6f3efeff24b1955f3cde1'
ETH_ADMIN_ENEAR                      = '\x150c79c8a70b1d528e95e200c6ca5ed0421c44f7'
ETH_ADMIN_BRIDGE_LEGACY              = '\xb8e11a1ad588863379a3e523b37d8c78070c16d9'
ETH_OMNI_BRIDGE_SUCCESSOR            = '\xe00c629afaccb0510995a2b95560e446a24c85b9'
```

---

## 11. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` (and `[0:4]` for selectors) from the contract sources in `aurora-is-near/rainbow-bridge` (`NearBridge.sol`, `INearBridge.sol`, `NearProver.sol`, `AdminControlled.sol`), `aurora-is-near/rainbow-token-connector` (`ERC20Locker.sol`, `Locker.sol`), and `aurora-is-near/eth-connector` (`EthCustodian.sol`, `ProofKeeper.sol`). Cross-checked against live `eth_getLogs` in the bridge's active era (ERC20Locker `Locked` ×962 @ block 14.0M; EthCustodian `Deposited` ×1586, `Withdrawn` ×298; ERC20Locker `Unlocked` ×425; eNEAR `TransferToNearInitiated`/`NearToEthTransferFinalised`/`ConsumedProof` @ block ~12.48M) — log `ntopics` counts match the indexed-field layout of each computed signature.
- **Addresses:** the ERC20Locker / EthClient leads came from the project READMEs and L2BEAT; **every address was then re-derived on-chain by linkage** — `EthCustodian.prover_()` and `ERC20Locker` storage-slot-0 both return `NearProver 0x051ad3f0…`; `NearProver.bridge()` returns `NearBridge 0x3fefc5a4…`; `ERC20Locker` slot-1 decodes to `"factory.bridge.near"` and `EthCustodian.nearProofProducerAccount_()` to `"aurora"`; eNEAR storage decodes to `"e-near.near"`. Existence checked via `eth_getCode` (non-empty on Ethereum; `0x` on all six other chains). Creation blocks found by binary search on `eth_getCode`.
- **Pause / deprecation state:** read live — `ERC20Locker.paused()=1`, `EthCustodian.paused()=3`, `NearBridge(0x3fefc5a4).paused()=0xd`; zero deposit/lock events in the last ~2,000,000 blocks; the NEAR light client carries no event topics in bytecode.
- **Proxy classification:** EIP-1967 impl/admin slots read live via `eth_getStorageAt` — `0x0` on all six legacy contracts (→ immutable, non-proxy, `AdminControlled`); set on the Omni Bridge successor (→ UUPS, impl `0x53785920…`). Selector presence/absence confirmed by scanning deployed `eth_getCode` bytecode.
- **Chain coverage:** `eth_getCode` against all seven listed RPCs for every address.

Authoritative sources:
- Canonical repos: [`aurora-is-near/rainbow-bridge`](https://github.com/aurora-is-near/rainbow-bridge) (NearBridge/NearProver/Ed25519) · [`aurora-is-near/rainbow-token-connector`](https://github.com/aurora-is-near/rainbow-token-connector) (ERC20Locker, BridgeTokenFactory) · [`aurora-is-near/eth-connector`](https://github.com/aurora-is-near/eth-connector) (EthCustodian, eNEAR) · successor [`Near-One/omni-bridge`](https://github.com/Near-One/omni-bridge)
- Docs: [Aurora — What is the Rainbow Bridge](https://doc.aurora.dev/bridge/introduction/) · [NEAR — Omni Bridge: how it works](https://docs.near.org/chain-abstraction/omnibridge/how-it-works) · [Rainbow Bridge app](https://rainbowbridge.app/)
- Registry / analytics: [L2BEAT — Rainbow Bridge](https://l2beat.com/bridges/projects/near) · [L2BEAT — Near Omni Bridge](https://l2beat.com/bridges/projects/nearomni)
- Explorer: [Etherscan — ERC20Locker](https://etherscan.io/address/0x23ddd3e3692d1861ed57ede224608875809e127f) · [EthCustodian](https://etherscan.io/address/0x6BFaD42cFC4EfC96f529D786D643Ff4A8B89FA52) · [eNEAR/NEAR token](https://etherscan.io/token/0x85f17cf997934a597031b2e18a9ab6ebd4b9f6a4)
