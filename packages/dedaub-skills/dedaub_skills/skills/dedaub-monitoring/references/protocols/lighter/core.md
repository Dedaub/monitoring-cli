# Lighter (zkLighter) — Topics, Selectors, Addresses (Ethereum L1; a separate instance on Robinhood Chain)

**Status:** verified against live RPC on every listed chain and the canonical `elliottech/lighter-contracts` / `elliottech/lighter-prover` repos (Sourcify-verified source, solc 0.8.25, viaIR) on 2026-06-09. Re-checked on 2026-09-29: Robinhood Chain (4663) hosts a separate Lighter instance with its own contracts (§6a); the Ethereum ZkLighter and ZkLighterVerifier impls rotated after 2026-06-09. Re-read on 2026-10-05: all three Ethereum impls (ZkLighter, ZkLighterVerifier, Governance) changed again in two upgrades on 2026-09-30 and 2026-10-01 (§8).
**Scope:** the entire on-chain footprint of Lighter — an application-specific zk-rollup perpetuals + spot CLOB DEX whose settlement contracts live **only on Ethereum mainnet (chain ID 1)**. Topics and selectors are **chain-agnostic**; addresses are network-specific. **Lighter is NOT deployed on Base, BNB, Avalanche, Arbitrum, Optimism, or Polygon** — `eth_getCode` returns `0x` for every Lighter address on all six (§7). **Robinhood Chain (4663) carries a separate instance** — Robinhood Chain's "Lighter Domain", a USDG-margined fork with its own contracts, sequencer, blockspace and liquidity that settles on Robinhood Chain itself (§6a). Its proxy has the same code hash as the Ethereum proxy, and it emits the same user-flow and batch topic0s. There is no live "Lighter v1 orderbook" contract suite on any of the seven chains: despite older marketing that calls Lighter "an Arbitrum DEX," the production system is its own L1-settled zk-rollup and the only deployment on-chain — hence this single `core.md` rather than `v1.md`/`v2.md`.

Lighter is architecturally a **zkBNB / zkSync-Lite (ZecRey-lineage) rollup**: an off-chain Sequencer matches orders and a Prover produces Plonky2 zk-SNARKs that are verified on L1. The L1 contracts (a) custody all user collateral, (b) hold the canonical state root, (c) accept `commitBatch → verifyBatch → executeBatches` from validators, and (d) process L1↔L2 deposits/withdrawals via a **priority queue** (`NewPriorityRequest`). Because the L2 logic is far larger than the EVM 24,576-byte limit, the main contract is split across **two implementation contracts** — `ZkLighter` (deposits/withdrawals/batch lifecycle, the live impl behind the proxy) and `AdditionalZkLighter` (delegatecall fallback target for the rest of the surface). Both expose nearly the same external ABI; **their event signatures are byte-for-byte identical**, so every topic0 in §1.1 applies regardless of which impl emitted it.

Three core contracts (`ZkLighter`, `ZkLighterVerifier`, `Governance`) are **EIP-1967 proxies** whose admin is the **`UpgradeGatekeeper`** (a 21-day upgrade timelock; a 4-of-7 Security Council Safe can cut the delay to zero). `DesertVerifier` and `UpgradeGatekeeper` are **non-proxy** contracts. The whole system is governed from two Gnosis Safes. The single non-obvious fact a monitoring engineer must internalise: **there is no Aave/Compound-style per-user lending event stream** — almost all trading happens inside the rollup and surfaces on L1 only as opaque batch commits and zk proofs; the only user-attributable L1 events are `Deposit`, `WithdrawPending` (claimable balance credited), and the desert-mode forced-exit path.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Verified name on chain |
|----------|------|--------|------------------------|
| **ZkLighter** | Main rollup entrypoint. Custodies collateral, holds the state root, processes deposits/withdrawals + batch lifecycle. Proxy at `0x3B4D…5ca7`. | **EIP-1967** (admin = UpgradeGatekeeper) | `ZkLighter` (live impl) |
| **AdditionalZkLighter** | Second logic contract — delegatecall fallback target for ABI that does not fit in the main impl. Same storage layout, identical events. | impl-only (no proxy of its own) | `AdditionalZkLighter` |
| **ZkLighterVerifier** | Main zk-SNARK verifier; settles the proof of correct L2 state transition (perp + spot trading logic). Proxy at `0xac3C…2BaA`. | **EIP-1967** (admin = UpgradeGatekeeper) | `ZkLighterVerifier` |
| **DesertVerifier** | zk verifier for **forced exits** during *desert mode* (the escape hatch: if the sequencer censors withdrawals for >14 days the rollup freezes and users exit directly from L1). | **No** (7,263 B, impl slot empty) | `DesertVerifier` |
| **Governance** | Validator registry + network governor. `setValidator`, `changeGovernor`. Proxy at `0xa464…81A1`. | **EIP-1967** (admin = UpgradeGatekeeper) | `Governance` |
| **UpgradeGatekeeper** | Upgrade timelock managing the three proxies above (`managedContracts(0..2)` = Governance, Verifier, ZkLighter). 21-day notice period; Security Council can zero it. | **No** (4,116 B) | `UpgradeGatekeeper` |
| **Lighter Multisig** (Security Council) | Gnosis Safe v1.4.1, **4-of-7**. `UpgradeGatekeeper.securityCouncilAddress()` — can `cutUpgradeNoticePeriod(0)`. | Safe proxy (171 B) | Safe `1.4.1` |
| **Lighter Multisig 2** (Governor) | Gnosis Safe v1.4.1, **3-of-5**. `= Governance.networkGovernor()` **and** `UpgradeGatekeeper.getMaster()` — drives validator/market admin and starts upgrades. | Safe proxy (171 B) | Safe `1.4.1` |

`commitBatch/verifyBatch/executeBatches/revertBatches/updateStateRoot` use a `StoredBatchInfo` tuple `(uint64,uint64,uint32,uint64,uint64,uint32,bytes32,bytes32,bytes32,bytes32,bytes32)` — the same tuple shape appears in several selectors below.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-09 from the Sourcify ABIs. Six of them additionally confirmed against **live `eth_getLogs`** on the ZkLighter proxy `0x3B4D…5ca7` in blocks 25,276,511–25,279,511 (counts in the right column).

### 1.1 ZkLighter **and** AdditionalZkLighter (identical event sets — disambiguate by emitter address, which is always the proxy `0x3B4D…5ca7`)

| topic0 | Event | Live? |
|--------|-------|-------|
| `0x493c3b8240368e8343bcd42cac5f4b8b161c06d061710e542a72f06a40ddd9d1` | `Deposit(uint48 toAccountIndex,address toAddress,uint16 assetIndex,uint8 routeType,uint128 baseAmount)` | ✅ 239 logs |
| `0xef80235b5f4cf1822ad6a8621af41ac64372ff672c402874f507fc63dbe5e06f` | `WithdrawPending(address indexed owner,uint16 assetIndex,uint128 baseAmount)` | ✅ 137 logs |
| `0xefdd379e3e15772fcc7d2a67fa5bbb0790b932724153aded4648307094733b2f` | `NewPriorityRequest(address sender,uint64 serialId,uint8 pubdataType,bytes pubData,uint64 expirationTimestamp)` | ✅ 250 logs |
| `0x181b25ea9d4d730f30d779f3d2099c03b26b653c889d33eef253d54baaacbd0d` | `BatchCommit(uint64 batchNumber,uint32 batchSize,uint64 endBlockNumber)` | ✅ 227 logs |
| `0x5c836e1ff20ea85c52b6e3d2ef0124d3304bf3b37cc8fb0e2c84ae7d44c0593e` | `BatchVerification(uint64 batchNumber,uint32 batchSize,uint64 endBlockNumber)` | ✅ 248 logs |
| `0x5d490d991d08230b7690c7511bb854b7b8a05fb7c87e2348e1909384cb325511` | `BatchesExecuted(uint64 batchNumber,uint64 endBlockNumber)` | ✅ 195 logs |
| `0x6d80424573caa7280d1b1d9933dd38c7532f82305e148b3f3a9df551a4c53581` | `BatchesRevert(uint64 newTotalBlocksCommitted)` | (revert path) |
| `0x645e0b8f839353842bdac87abd27fc8bdda536e0731cdb7cc75e4f0740b575ac` | `StateRootUpdate(uint64 batchNumber,bytes32 oldStateRoot,bytes32 newStateRoot)` | |
| `0x9f7e400a81dddbf1c18b1c37f82aa303d166295ca4b577eb2a7c23d4b704ba89` | `DesertMode()` | **freeze trigger** |
| `0x134f63a6bbe3b3ef885ce4067eb2753fe1c912c51c4b8e0cc7966f21773c047e` | `CreateMarket((uint16,uint8,bytes) params,uint8 sizeDecimals,uint8 priceDecimals,bytes32 symbol)` | |
| `0x3551e43c2bd6cb132e6bc5e0ab4022d8fa63dff212a9dd4ebaf40801705731b9` | `UpdateMarket((uint16,uint8,bytes) params)` | |
| `0xf1b24e81016b9f39e2290cf2a9303264a07534a569df7e6200a39573d7f26b0c` | `RegisterAssetConfig(uint16 assetIndex,address tokenAddress,uint8 withdrawalsEnabled,uint56 extensionMultiplier,uint128 tickSize,uint64 depositCapTicks,uint64 minDepositTicks)` | |
| `0xff23feaffcab98dc102270f0c98539db1067368280f613f9dfd91a601c20113d` | `UpdateAssetConfig(uint16 assetIndex,uint8 withdrawalsEnabled,uint64 depositCapTicks,uint64 minDepositTicks)` | |
| `0x8a3509a4057c89a5993a4a3140c2ebf7e829d325d8998eaa6c48adcff98b2cef` | `TreasuryUpdate(address newTreasury)` | |
| `0xbbc858f043fabd2c7f56f0751bc461f96ba7e4a8d059fa6507ac6cf51238fa0f` | `InsuranceFundOperatorUpdate(address newInsuranceFundOperator)` | |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` | OZ Initializable (proxy init/re-init) |

`Deposit` here is **NOT** the EIP-4626/Aave deposit event — it is the Lighter-specific 5-field credit-to-L2 event (different topic0). `routeType` distinguishes the destination sub-account flow. `WithdrawPending` is the **claimable-balance credit** on L1 (the funds are then pulled with `withdrawPendingBalance`). Topic0 for `Deposit`/`WithdrawPending` is unique to Lighter — no collision risk.

### 1.2 Governance (`0xa464…81A1`)

| topic0 | Event |
|--------|-------|
| `0x5425363a03f182281120f5919107c49c7a1a623acc1cbc6df468b6f0c11fcf8c` | `NewGovernor(address newGovernor)` |
| `0x065b77b53864e46fda3d8986acb51696223d6dde7ced42441eb150bae6d48136` | `ValidatorStatusUpdate(address validatorAddress,bool isActive)` |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8)` (≡ §1.1) |

### 1.3 UpgradeGatekeeper (`0x94da…6f67`) — watch all of these for impl rotations

| topic0 | Event |
|--------|-------|
| `0xecfd8b4d8bfc0590001d923f6db32faaad4c3d96097734fe5950f43980dabfc4` | `NewUpgradable(uint256 indexed versionId,address indexed upgradeable)` |
| `0xabce748366d7d01473824f1bee75dc176759f56b88f00253e4a10d7528ca806f` | `NoticePeriodStart(uint256 indexed versionId,address[] newTargets,uint256 noticePeriod)` — **upgrade proposed** |
| `0xd2b7d4a4a2b38481e36a9b8198af8b427261011fd199b7a1b7cb8f437aa25acd` | `PreparationStart(uint256 indexed versionId)` |
| `0x48bc8be43b04d57da4f0d65c05db98278a94d9e90b7348d5d2705cc78c9a9d2e` | `UpgradeComplete(uint256 indexed versionId,address[] newTargets)` — **impl actually changed** |
| `0x55cd34119fd31f1a8cc60aad1098023b450274eef2294e3e1b6dd452d58ce6fd` | `UpgradeCancel(uint256 indexed versionId)` |
| `0xf2b18f8abbd8a0d0c1fb8245146eedf5304887b12f6395b548ca238e054a1483` | `NoticePeriodChange(uint256 newNoticePeriod)` |

> **Lighter has no `Upgraded(address)` event.** The zkBNB/zkSync-Lite proxy upgrades through this `UpgradeGatekeeper` flow, not OZ's `upgradeToAndCall`. To catch an implementation change, watch **`UpgradeComplete`** (`0x48bc8be4…`) on the gatekeeper and **`NoticePeriodStart`** (`0xabce7483…`) for the 21-day warning — there is no `0xbc7cd75a…` topic0 here. (See §9 for the fast-path Security Council bypass.)

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All selectors recomputed locally on 2026-06-09 from the Sourcify ABIs and confirmed present in the live impl bytecode. `ZkLighter` and `AdditionalZkLighter` share most of this surface.

### 2.1 ZkLighter — user deposit/withdraw (the L1-attributable money flow)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8a857083` | `deposit(address toAddress,uint16 assetIndex,uint8 routeType,uint256 amount)` | Credit collateral to an L2 account. Emits `Deposit` + `NewPriorityRequest`. ERC-20 (pull) **and** native ETH (`assetIndex` = `NATIVE_ASSET_INDEX`, value-bearing). |
| `0xea2102e4` | `depositBatch(uint64[] amounts,address[] toAddresses,uint48[] toAccountIndexes)` | Batched deposits in one tx. |
| `0xd20191bd` | `withdraw(uint48 fromAccountIndex,uint16 assetIndex,uint8 routeType,uint64 amount)` | Request an L2→L1 withdrawal (enters priority queue). |
| `0x2f25807e` | `withdrawPendingBalance(address owner,uint16 assetIndex,uint128 amount)` | Pull the L1 claimable balance credited by `WithdrawPending`. |
| `0x975364c6` | `withdrawPendingBalanceLegacy(address owner,uint128 amount)` | Legacy single-asset variant. |
| `0xd1cbc64f` | `getPendingBalance(address,uint16)` → `uint128` | View: claimable balance per asset. |
| `0xaf7c0260` | `getPendingBalanceLegacy(address)` → `uint128` | View. |
| `0x17010c68` | `changePubKey(uint48 accountIndex,uint8 pubKeyType,bytes pubKey)` | Register/rotate the L2 trading pubkey (priority op). |

### 2.2 ZkLighter — batch lifecycle (validator-only; the rollup heartbeat)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe415f0f4` | `commitBatch((uint64,uint32,uint64,uint64,uint32,bytes32,bytes32,bytes32,bytes32,bytes),(uint64,uint64,uint32,uint64,uint64,uint32,bytes32,bytes32,bytes32,bytes32,bytes32))` | Validator commits a new batch. Emits `BatchCommit`. |
| `0x23ff50e1` | `verifyBatch((uint64,uint64,uint32,uint64,uint64,uint32,bytes32,bytes32,bytes32,bytes32,bytes32),bytes proof)` | Settle the zk proof for a committed batch. Emits `BatchVerification`; calls `ZkLighterVerifier.Verify`. |
| `0x2d320e28` | `executeBatches((uint64,uint64,uint32,uint64,uint64,uint32,bytes32,bytes32,bytes32,bytes32,bytes32)[] batches,bytes[] pendingOps)` | Finalize verified batches; processes withdrawals. Emits `BatchesExecuted` + `WithdrawPending`. |
| `0xbdf723e8` | `revertBatches((uint64,uint64,uint32,uint64,uint64,uint32,bytes32,bytes32,bytes32,bytes32,bytes32)[],(uint64,uint64,uint32,uint64,uint64,uint32,bytes32,bytes32,bytes32,bytes32,bytes32))` | Roll back committed-but-unverified batches. Emits `BatchesRevert`. |
| `0x7271277e` | `updateStateRoot((uint64,uint64,uint32,uint64,uint64,uint32,bytes32,bytes32,bytes32,bytes32,bytes32),bytes32,bytes32,bytes)` | Validium-root / state-root update path. Emits `StateRootUpdate`. |

### 2.3 ZkLighter — desert (forced-exit) mode

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x22b22256` | `activateDesertMode()` | Anyone can trigger if priority requests expired (>14 d). Emits `DesertMode`; **freezes the rollup**. |
| `0x377d4194` | `performDesert(uint48 accountIndex,address owner,uint16 assetIndex,uint128 amount,bytes proof)` | Exit a balance directly from L1 using a `DesertVerifier` proof. |
| `0x1b6592fa` | `cancelOutstandingDepositsForDesertMode(uint64 number,bytes[] depositsPubdata)` | Refund queued deposits that never made it into L2. |

### 2.4 ZkLighter — admin (governor / market & asset config)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x25216fda` | `registerAssetConfig(uint16,address,uint8,uint56,uint128,uint64,uint64)` | Register a collateral asset. Emits `RegisterAssetConfig`. |
| `0xef228c02` | `registerAsset(uint8,uint8,uint8,bytes32,(uint16,uint56,uint64,uint64,uint8,uint16,uint16,uint16,uint32,uint56))` | Register a tradable asset (full config tuple). |
| `0x0b4d1558` | `createMarket(uint8 sizeDecimals,uint8 priceDecimals,bytes32 symbol,(uint16,uint8,bytes))` | Emits `CreateMarket`. |
| `0x99e51881` | `updateMarket((uint16,uint8,bytes))` | Emits `UpdateMarket`. |
| `0x7b7289dc` | `updateAsset((uint16,uint64,uint64,uint8,uint16,uint16,uint16,uint32))` | |
| `0xcd626497` | `updateAssetConfig(uint16,uint8,uint64,uint64)` | Emits `UpdateAssetConfig`. |
| `0xf0f44260` | `setTreasury(address)` | Emits `TreasuryUpdate`. |
| `0xaabe6078` | `setInsuranceFundOperator(address)` | Emits `InsuranceFundOperatorUpdate`. |
| `0x58d73468` | `setSystemConfig((uint48,uint48,uint48,uint48,uint32,uint32,uint32,uint32))` | |
| `0x439fab91` | `initialize(bytes)` | one-shot proxy init. |
| `0x25394645` | `upgrade(bytes)` | called by gatekeeper during `finishUpgrade`. |

### 2.5 ZkLighter — views & counters (monitoring keys)

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x9588eca2` | `stateRoot()` | `bytes32` — canonical L2 root. |
| `0x02cfb563` | `desertMode()` | `bool` — `true` once frozen. **Alert if true.** |
| `0x61d027b3` | `treasury()` | `address` (= `0x3dd7…4dae`). |
| `0xbaa08f7d` | `insuranceFundOperator()` | `address` (= `0x9cce…7310`). |
| `0xaab78a8e` | `committedBatchesCount()` | `uint64` (≈186,894 on 2026-06-09). |
| `0x90fda39b` | `verifiedBatchesCount()` | `uint64`. |
| `0xd5102eea` | `executedBatchesCount()` | `uint64` (≈186,878). |
| `0x72fc4c39` | `openPriorityRequestCount()` | `uint64` — backlog of L1→L2 ops; a growing gap is a censorship signal. |
| `0xabf6a038` | `addressToAccountIndex(address)` | `uint48` — L1 addr → L2 account. |
| `0x899cfa29` | `tokenToAssetIndex(address)` | `uint16` — ERC-20 → asset index (USDC → **3**, verified live). |
| `0xcd565e08` | `assetConfigs(uint16)` | per-asset config. |

### 2.6 Governance (`0xa464…81A1`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4623c91d` | `setValidator(address,bool)` | Governor-only. Emits `ValidatorStatusUpdate`. |
| `0xe4c0aaf4` | `changeGovernor(address)` | Emits `NewGovernor`. |
| `0x40550a1c` | `isActiveValidator(address)` → `bool` | |
| `0xf39349ef` | `networkGovernor()` → `address` | = Multisig 2 (`0x97A9…03a2`). |
| `0x3e413bee` | `usdc()` → `address` | = Circle USDC `0xA0b8…eB48`. |

### 2.7 UpgradeGatekeeper (`0x94da…6f67`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x31a94da3` | `startUpgrade(address[] newTargets)` | Master-only. Emits `NoticePeriodStart`. |
| `0x6b131e06` | `startPreparation()` | Emits `PreparationStart`. |
| `0x253b153b` | `finishUpgrade(bytes[])` | Executes the impl swap. Emits `UpgradeComplete`. |
| `0x55f29166` | `cancelUpgrade()` | Emits `UpgradeCancel`. |
| `0x389b8b3a` | `cutUpgradeNoticePeriod(uint256)` | **Security-Council-only fast path** — can set delay to 0 (the key custody risk). |
| `0x999f0be2` | `addUpgradeable(address)` | Emits `NewUpgradable`. |
| `0x5a99719e` | `getMaster()` → `address` | = Multisig 2. |
| `0xc727927f` | `securityCouncilAddress()` → `address` | = Multisig 1 (`0x92b1…2045`). |
| `0xd4d543c5` | `upgradeStatus()` → `uint8` | 0=Idle,1=NoticePeriod,2=Preparation. |
| `0xac0d925c` | `versionId()` → `uint256` | upgrade counter (60 on 2026-06-09, 74 on 2026-10-05). |

### 2.8 ZkLighterVerifier / DesertVerifier (identical 3-fn ABI)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7e4f7a8a` | `Verify(bytes proof,uint256[] publicInputs)` → `bool` | The zk-SNARK check. Capital-V `Verify` (Plonky2/gnark convention) — **lowercase `verify` is the wrong selector.** |
| `0x439fab91` | `initialize(bytes)` | |
| `0x25394645` | `upgrade(bytes)` | (ZkLighterVerifier only — DesertVerifier is non-proxy.) |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Proxy wiring confirmed live: `UpgradeGatekeeper.zkLighterProxy()` = ZkLighter; `UpgradeGatekeeper.managedContracts(0..2)` = Governance / ZkLighterVerifier / ZkLighter; `Governance.networkGovernor()` = Multisig 2.

### 3.1 Core protocol

| Role | Address | One-liner |
|------|---------|-----------|
| **ZkLighter** (proxy) | `0x3B4D794a66304F130a4Db8F2551B0070dfCf5ca7` | Main rollup entrypoint; custodies funds, holds the state root, emits all §1.1 events. Live impl `0xE16c…E5A7` (2026-10-05). |
| **ZkLighter impl** (live) | `0xE16c893252616dD49913969f145e733b96a3E5A7` | `ZkLighter` logic (24,421 B; slot re-read 2026-10-05). Retired: `0x831EF69BaB8AF8B1037a4961B8d0674b124E7008` (2026-06-09), `0x6e1433585b320880f488D0A7c1d2077D43B6Ca4E` (2026-09-29). |
| **AdditionalZkLighter impl** | `0x22F05515497ce8D78f3898088C474403Ac9C668f` | second logic contract (24,523 B), delegatecall fallback. Value of 2026-06-09: an upgrade can replace it (`upgrade()` params), and it sits in internal storage, so it was not re-read after the 2026-10 upgrades. |
| **ZkLighterVerifier** (proxy) | `0xac3Ce44B6ff4E402858C99D5699ff63131572BaA` | Main zk-SNARK verifier. Impl `0xc4c2…aE11` (2026-10-05). |
| **ZkLighterVerifier impl** | `0xc4c2067ece6e33e50a30087ec14096715e56aE11` | 7,263 B (2026-10-05). Retired: `0xAa0b5b65890162C5C96D82F088822247EC5Df5D6` (2026-06-09), `0xd3E043d6E17Cb28d73BAa469Aa632411e1dE8046` (2026-09-29). |
| **DesertVerifier** | `0x2aDBd91742B64105a097bC37D20Ebbca9a496085` | Forced-exit (desert-mode) verifier. **Non-proxy** (7,263 B). |
| **Governance** (proxy) | `0xa464DA0B43f80EE3FfC4795cbbFC78472b5c81A1` | Validator registry + governor. Impl `0xE935…6D43` (2026-10-05). |
| **Governance impl** | `0xE935fa009Ae2F913A26B4411a901ECF6dBAb6D43` | 6,323 B (2026-10-05). Retired: `0x46D3C0c01D5DAae4FE8e3f54f32901d9Fbde1f08` (live 2026-06-09 to at least 2026-09-29). |

### 3.2 Governance, upgrade & treasury

| Role | Address | One-liner |
|------|---------|-----------|
| **UpgradeGatekeeper** | `0x94da8A995D0D82Ef0fE7E509C6D76c22603B6f67` | Upgrade timelock (21-day notice); admin of the 3 proxies. **Non-proxy** (4,116 B). |
| **Lighter Multisig** (Security Council) | `0x92b12c9d85BF7bd2EF5d2F53F4cd4Ce0BE432045` | Gnosis Safe v1.4.1, **4-of-7**. `securityCouncilAddress()`; can zero the upgrade delay. |
| **Lighter Multisig 2** (Governor) | `0x97A90Ec950B6BCd9B190b566525B2Bb92A2C03a2` | Gnosis Safe v1.4.1, **3-of-5**. `networkGovernor()` + gatekeeper `getMaster()`. |
| **Treasury** | `0x3dd7c834eaa70c98e1c224808a3c62163b344dae` | Fee/treasury sink (`treasury()`). **Gnosis Safe v1.4.1 proxy (171 B), 2-of-3** — slot-0 singleton `0x41675C09…7461a` (same as the two Multisigs), not an EOA. |
| **InsuranceFundOperator** | `0x9cce444f8c60bd570986cd7d0ed7aec29f127310` | Insurance-fund operator (`insuranceFundOperator()`). **Gnosis Safe v1.4.1 proxy (171 B), 3-of-5** — slot-0 singleton `0x41675C09…7461a`. |
| **Safe singleton (masterCopy)** | `0x41675C099F32341bf84BFc5382aF534df5C7461a` | Gnosis Safe v1.4.1 implementation behind all four Lighter Safes — both Multisigs **and** the Treasury / InsuranceFundOperator Safes (slot-0 read). |

### 3.3 Collateral assets (L1 tokens custodied by ZkLighter)

| Asset | Address | Asset index |
|-------|---------|-------------|
| **USDC** (settlement collateral) | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | `3` (verified `tokenToAssetIndex(USDC)` = 3 and `USDC_ASSET_INDEX()` = 3) |
| Native ETH | — (no token; `NATIVE_ASSET_INDEX`) | native |

USDC is the primary quote/collateral asset for the perps system (6 decimals). `Governance.usdc()` returns the same Circle USDC address.

---

## 4–6. Addresses — Base / BNB / Avalanche / Arbitrum / Optimism / Polygon

**No Lighter contracts on any of these chains.** Every address in §3 returns `0x` from `eth_getCode` on all six target RPCs (verified 2026-06-09):

- Base (8453) — `https://base-rpc.publicnode.com` → all `0x`
- BNB (56) — `https://bsc-rpc.publicnode.com` → all `0x`
- Avalanche (43114) — `https://avalanche-c-chain-rpc.publicnode.com` → all `0x`
- Arbitrum One (42161) — `https://arbitrum-one-rpc.publicnode.com` → all `0x`
- Optimism (10) — `https://optimism-rpc.publicnode.com` → all `0x`
- Polygon PoS (137) — `https://polygon-bor-rpc.publicnode.com` → all `0x`

Lighter is an **app-specific rollup that settles on Ethereum L1 directly** — it does **not** run on a general-purpose L2 (Arbitrum/Optimism/zkSync). The L2 itself is Lighter's own chain (not in the seven), reachable only via the L1 deposit/withdraw queue and the API/SDK; it has no separate EVM RPC in this set. Older third-party write-ups describing Lighter as "an Arbitrum DEX" are **inaccurate** for the production deployment — no Lighter contract exists on Arbitrum.

---

## 6a. Addresses — Robinhood Chain (chain ID 4663) — a separate Lighter instance

Not the Ethereum system: a second deployment with its own state, validators and upgrade governance. The Robinhood Chain docs name the proxy as the "Lighter Contract (Robinhood Chain)"; L2BEAT ("Lighter on Robinhood") lists the full set below. All verified via `eth_getCode` on `https://rpc.mainnet.chain.robinhood.com` on 2026-09-29; wiring read live with `eth_call`: `UpgradeGatekeeper.zkLighterProxy()` = the proxy, `getMaster()` = `Governance.networkGovernor()` = the Governor Safe, `securityCouncilAddress()` = the Security Council address, `approvedUpgradeNoticePeriod()` = 1,814,400 s (21 d), `versionId()` = 6.

| Role | Address | One-liner |
|------|---------|-----------|
| **ZkLighter** (proxy) | `0x94bAB9693Ba2f6358507eFfcbd372b0660AFfF9d` | Custodies USDG margin; emits §1.1 events. 1,367 B, same proxy code hash as Ethereum; admin slot = UpgradeGatekeeper. |
| ZkLighter impl (live) | `0x82DE5B1161C93afDFE21bA0D5343f01Cd7401d90` | 23,168 B (EIP-1967 impl slot). |
| Second logic contract | `0xDa2B59fFB41485a6f21E14e479AE7B7AB29a997c` | 24,520 B (L2BEAT "Implementation #2"; the AdditionalZkLighter role). |
| **ZkLighterVerifier** (proxy) | `0xe1aFBE2D670eFF0e7C8A41F080792C011916ac31` | impl `0xCBF92533F5816c6Ee0e4250F4E138b3f49962EF2` (7,263 B). |
| **DesertVerifier** | `0x56aeED6920DBB9E198C2C0072147A45684A06E10` | 7,263 B, not a proxy. |
| **Governance** (proxy) | `0xf6F6Bd6eEA2b9A2041328732CcAe4c5e1DD278B7` | impl `0x3468Dcab5a2D81Af207B3e301DFA889321989a61` (2,460 B). `usdc()` reverts here (the quote asset is USDG). |
| **UpgradeGatekeeper** | `0x43CfF77CD060A155dCe5deb12B93b875f69F2716` | 4,116 B, not a proxy; admin of the three proxies. |
| **Governor Safe** (3-of-5 per L2BEAT) | `0x8Caf9FF9392F39E87cBC65A130c026caaCD321ef` | 171-B Safe proxy; slot-0 singleton `0x29fcb43b46531bca003ddc8fcb67ffe91900c762`. `getMaster()` + `networkGovernor()`. |
| **Security Council** | `0x4972E0CaCb2AC45644BA054838e96fF4f6f7eFDb` | **No code on Robinhood Chain (EOA, nonce 6 on 2026-09-29)**, yet it is `securityCouncilAddress()` — it can cut the 21-day notice to zero. |
| Treasury | `0xac71ec137c892d02d531e48ceb1d060f9c9ac357` | `treasury()`; EOA (no code, nonce 20,742). |
| InsuranceFundOperator | `0x6ccdd1f3f599c69fa74eedc3dab28559fe99ab0a` | `insuranceFundOperator()`; EOA (no code, nonce 102). |
| **USDG** (Global Dollar, margin asset) | `0x5fc5360d0400a0fd4f2af552add042d716f1d168` | 6 decimals; EIP-1967 proxy → impl `0x68184c449e1a8f34fa18d289737129fd27b66f8f`. |

Live state (2026-09-29): `desertMode()` = false; `committedBatchesCount()` = 128,962; `executedBatchesCount()` = 128,956; `openPriorityRequestCount()` = 22.

Measured flow (pinned window 2026-09-28 00:00–12:00 UTC): `Deposit` 2,463, `NewPriorityRequest` 2,618, `WithdrawPending` 598 on the Robinhood proxy (Ethereum proxy in the same window: 337 / 363 / 169). The last 10,000 blocks of the window also show `BatchCommit` 16, `BatchVerification` 15 and `BatchesExecuted` 14, with the same topic0s as §1.1. Sample deposit (tx `0xe3a56f64eb31e19aff8ad7044200320c90cf38f219845c2a502feee56ceee281`, `deposit` `0x8a857083`): a USDG `Transfer` from the user to the proxy, then `NewPriorityRequest` and `Deposit`. Sample withdrawal (tx `0x1a4db80e5ea3c3ca34a074511325bb239900bd7eaf7016d1969da55d910440fb`, selector `0xe3a49048` through the caller `0xa91803ac55c9f583162a5d43006f98d10a41088f`): `WithdrawPending(owner)` and a USDG `Transfer` from the proxy to the owner in the same transaction — the Ethereum system shows the same pattern (tx `0x999adc76de3653cc697e92531862cb2a2c3f2bd51efce3cd71c6e61e39c3a630`).

---

## 7. Cross-chain summary

| Chain | ID | ZkLighter | ZkLighterVerifier | DesertVerifier | Governance | UpgradeGatekeeper | Multisigs |
|---|---|---|---|---|---|---|---|
| **Ethereum** | 1 | `0x3B4D…5ca7` ✅ | `0xac3C…2BaA` ✅ | `0x2aDB…6085` ✅ | `0xa464…81A1` ✅ | `0x94da…6f67` ✅ | `0x92b1…2045` / `0x97A9…03a2` ✅ |
| Base | 8453 | — | — | — | — | — | — |
| BNB | 56 | — | — | — | — | — | — |
| Avalanche | 43114 | — | — | — | — | — | — |
| Arbitrum One | 42161 | — | — | — | — | — | — |
| Optimism | 10 | — | — | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — | — | — |
| **Robinhood Chain** (separate instance) | 4663 | `0x94bAB9693Ba2f6358507eFfcbd372b0660AFfF9d` ✅ | `0xe1aFBE2D670eFF0e7C8A41F080792C011916ac31` ✅ | `0x56aeED6920DBB9E198C2C0072147A45684A06E10` ✅ | `0xf6F6Bd6eEA2b9A2041328732CcAe4c5e1DD278B7` ✅ | `0x43CfF77CD060A155dCe5deb12B93b875f69F2716` ✅ | Safe `0x8Caf9FF9392F39E87cBC65A130c026caaCD321ef` / Security Council EOA `0x4972E0CaCb2AC45644BA054838e96fF4f6f7eFDb` |

**Vanity tell:** the main rollup proxy is **`0x3B4D…5ca7`** ("3B4D" — no semantic vanity). All four Lighter Safes — the two governance Multisigs **plus** the Treasury and InsuranceFundOperator Safes — share the Safe v1.4.1 singleton `0x41675C09…`. No CREATE2 cross-chain address reuse exists: the Ethereum literals return `0x` on Robinhood Chain, and the Robinhood instance uses its own addresses (§6a).

**Counterparty chain outside the seven:** Lighter's own **L2 rollup (a custom Plonky2 zk-rollup)** — not an EVM chain in this set; it has no chainId among the seven and is accessed only through the L1 queue + off-chain API.

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **ZkLighter** | **EIP-1967 transparent-style** (zkBNB/zkSync-Lite `Proxy`) | impl slot `0x3608…2bbc` = `0xE16c…E5A7` (2026-10-05); admin slot `0xb531…6103` = **UpgradeGatekeeper** `0x94da…6f67`; 1,367 B proxy. | UpgradeGatekeeper (21-day timelock); Security Council can cut to 0. |
| **ZkLighterVerifier** | **EIP-1967** | impl slot = `0xc4c2…aE11`; admin slot = UpgradeGatekeeper; 1,367 B. | UpgradeGatekeeper. |
| **Governance** | **EIP-1967** | impl slot = `0xE935…6D43`; admin slot = UpgradeGatekeeper; 1,367 B. | UpgradeGatekeeper. |
| **DesertVerifier** | **Not a proxy** | impl/admin/beacon slots all `0x000…0`; 7,263 B full contract. | immutable (replaced only by a full ZkLighter upgrade pointing at a new verifier). |
| **UpgradeGatekeeper** | **Not a proxy** | impl/admin/beacon slots `0x000…0`; 4,116 B. | n/a (`transferMastership`). |
| **Lighter Multisig / Multisig 2** | **Gnosis Safe proxy** (EIP-1167-style Safe proxy) | 171 B; storage slot 0 = Safe singleton `0x41675C09…`; `VERSION()` = `1.4.1`. | Safe owners (4-of-7 / 3-of-5). |

EIP-1967 slots used: impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`, admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. The **beacon slot** `0xa3f0ad74…` is empty on every Lighter contract (no beacon proxies).

**Live impls read from the slot on 2026-06-09:** ZkLighter → `0x831EF69BaB8AF8B1037a4961B8d0674b124E7008`; ZkLighterVerifier → `0xAa0b5b65890162C5C96D82F088822247EC5Df5D6`; Governance → `0x46D3C0c01D5DAae4FE8e3f54f32901d9Fbde1f08`. **Re-read on 2026-09-29:** ZkLighter → `0x6e1433585b320880f488d0a7c1d2077d43b6ca4e` (24,502 B); ZkLighterVerifier → `0xd3e043d6e17cb28d73baa469aa632411e1de8046` (7,263 B); Governance unchanged; `UpgradeGatekeeper.versionId()` = 72 (60 on 2026-06-09), `upgradeStatus()` = 0. **Re-read on 2026-10-05 (live):** ZkLighter → `0xE16c893252616dD49913969f145e733b96a3E5A7` (24,421 B); ZkLighterVerifier → `0xc4c2067ece6e33e50a30087ec14096715e56aE11` (7,263 B); Governance → `0xE935fa009Ae2F913A26B4411a901ECF6dBAb6D43` (6,323 B); `versionId()` = 74, `upgradeStatus()` = 0. Two gatekeeper cycles did it: `UpgradeComplete` in tx `0x1e9044695ebca965fdfcc1a837e73bc52bdbbc1b4b6a09dbc07196e03396378d` (block 26,093,171, 2026-09-30 22:05 UTC) and `0xa23c2cbf56da3c129a56b5691a289b621d81b0da8946983e0b33898501322723` (block 26,099,289, 2026-10-01 18:34 UTC), each about 25 minutes after its `NoticePeriodStart` — the notice period was cut, not the 21-day default. **Robinhood Chain instance:** ZkLighter → `0x82DE5B1161C93afDFE21bA0D5343f01Cd7401d90`, ZkLighterVerifier → `0xCBF92533F5816c6Ee0e4250F4E138b3f49962EF2`, Governance → `0x3468Dcab5a2D81Af207B3e301DFA889321989a61`; admin slot of all three = its own UpgradeGatekeeper `0x43CfF77CD060A155dCe5deb12B93b875f69F2716`. The admin slot of all three holds the UpgradeGatekeeper, not a ProxyAdmin contract and not an EOA.

**There is NO `Upgraded(address)` topic0.** Track impl rotations via the gatekeeper's `UpgradeComplete` (`0x48bc8be4…`) / `NoticePeriodStart` (`0xabce7483…`) — not via `0xbc7cd75a…` (which does not appear in this protocol).

---

## 9. Detection invariants & gotchas

1. **Lighter Core is on Ethereum L1 — nothing on Base/BNB/Avalanche/Arbitrum/Optimism/Polygon.** (Robinhood Chain runs a separate instance — gotcha 15.) If you scan Base/BNB/Avax/Arbitrum/Optimism/Polygon you will find `0x` for every address. "Lighter on Arbitrum" is stale marketing; the production rollup settles on L1.
2. **Two implementation contracts, one proxy, identical events.** `ZkLighter` (`0xE16c…E5A7` since 2026-10-01) and `AdditionalZkLighter` (`0x22F0…668f`) back the same proxy `0x3B4D…5ca7` (zkSync-Lite split-logic pattern). The **emitter is always the proxy**, never the impls — index events on `0x3B4D…5ca7` only.
3. **`Deposit` is Lighter's own 5-field event, not EIP-4626/Aave.** topic0 `0x493c3b82…` (`Deposit(uint48,address,uint16,uint8,uint128)`). Do not confuse with the generic `Deposit`/`Supply` topics; no collision here, but `toAddress` (field 2) is the **L1 owner** and `toAccountIndex` (field 1) is the **L2 account** — attribute to `toAddress`.
4. **Withdrawals are two-phase.** `executeBatches` credits an L1 **claimable** balance → `WithdrawPending(owner, asset, amount)` (`0xef80235b…`, `owner` indexed); the user then calls `withdrawPendingBalance` to actually receive tokens. A `WithdrawPending` log is *not* a token transfer out yet.
5. **`NewPriorityRequest` (`0xefdd379e…`) is the L1→L2 queue.** Each deposit / `changePubKey` / full-exit enqueues one. **`openPriorityRequestCount()` rising without matching `executeBatches` = censorship/liveness alert** and is the precondition for desert mode.
6. **Desert mode is the freeze switch.** `activateDesertMode()` → `DesertMode()` event (`0x9f7e400a…`) → rollup frozen, users exit via `performDesert` + a `DesertVerifier` proof. **Monitor `desertMode()` view and the `DesertMode` topic0 as a critical alert.** Currently `false`.
7. **No `Upgraded(address)` event.** Watch the UpgradeGatekeeper: `NoticePeriodStart` (`0xabce7483…`) = 21-day warning of an impl change; `UpgradeComplete` (`0x48bc8be4…`) = it happened. (§8.)
8. **The 21-day delay can be bypassed.** The Security Council Safe (`0x92b1…2045`, 4-of-7) can call `cutUpgradeNoticePeriod(0)` (`0x389b8b3a`) — this is the documented "funds can be stolen via a malicious instant upgrade" risk. **Treat any `cutUpgradeNoticePeriod` call, and any Safe tx from `0x92b1…2045` touching the gatekeeper, as high-severity.**
9. **Governance vs. Security Council are different Safes.** Governor = Multisig 2 `0x97A9…03a2` (3-of-5, validators/markets/start-upgrade); Security Council = Multisig 1 `0x92b1…2045` (4-of-7, delay-cut). Don't conflate.
10. **Validators are the only addresses that can `commitBatch`/`verifyBatch`/`executeBatches`.** Registered via `Governance.setValidator` → `ValidatorStatusUpdate` (`0x065b77b5…`). A new validator appearing is a config-change signal.
11. **USDC is asset index 3; native ETH is `NATIVE_ASSET_INDEX`.** Asset indices are Lighter-internal, not token addresses — resolve with `tokenToAssetIndex(token)` / `assetConfigs(index)`. Per-asset withdrawals can be toggled (`UpdateAssetConfig.withdrawalsEnabled`) — watch that flag.
12. **`Verify` is capital-V** (`0x7e4f7a8a`) on both verifiers — the gnark/Plonky2 naming convention; the lowercase `verify(...)` selector is wrong.
13. **Treasury (`0x3dd7…4dae`) and InsuranceFundOperator (`0x9cce…7310`) are Gnosis Safe v1.4.1 proxies (171 B, slot-0 singleton `0x41675C09…`), not EOAs** — Treasury is a 2-of-3 Safe, InsuranceFundOperator a 3-of-5 Safe (same singleton as the two governance Multisigs). `setTreasury`/`setInsuranceFundOperator` changes (events `0x8a3509a4…` / `0xbbc858f0…`) reroute fee/insurance flow and should be alerted.
14. **`commitBatch` ≠ funds settled.** Order: `commitBatch` → `verifyBatch` (proof) → `executeBatches` (finalize + withdrawals). `committedBatchesCount` ahead of `executedBatchesCount` by a few is normal; a large divergence (commits with no verifications) signals a stalled prover.
15. **Robinhood Chain is a second, independent Lighter instance.** Proxy `0x94bAB9693Ba2f6358507eFfcbd372b0660AFfF9d` custodies **USDG** (`0x5fc5360d0400a0fd4f2af552add042d716f1d168`), not USDC. Same topic0s, separate state: a Robinhood `Deposit` never appears on Ethereum and vice versa, and its batch counters are its own. Its upgrade path has the same 21-day gatekeeper, but the `securityCouncilAddress()` that can zero the delay (`0x4972E0CaCb2AC45644BA054838e96fF4f6f7eFDb`) has **no code on Robinhood Chain** — an EOA (nonce 6), not a Safe, by `eth_getCode` and `eth_getTransactionCount` on 2026-09-29. Treat `cutUpgradeNoticePeriod` there as critical.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) — ZkLighter / AdditionalZkLighter =====
TOPIC_DEPOSIT                     = '\x493c3b8240368e8343bcd42cac5f4b8b161c06d061710e542a72f06a40ddd9d1'
TOPIC_WITHDRAW_PENDING            = '\xef80235b5f4cf1822ad6a8621af41ac64372ff672c402874f507fc63dbe5e06f'
TOPIC_NEW_PRIORITY_REQUEST        = '\xefdd379e3e15772fcc7d2a67fa5bbb0790b932724153aded4648307094733b2f'
TOPIC_BATCH_COMMIT                = '\x181b25ea9d4d730f30d779f3d2099c03b26b653c889d33eef253d54baaacbd0d'
TOPIC_BATCH_VERIFICATION          = '\x5c836e1ff20ea85c52b6e3d2ef0124d3304bf3b37cc8fb0e2c84ae7d44c0593e'
TOPIC_BATCHES_EXECUTED            = '\x5d490d991d08230b7690c7511bb854b7b8a05fb7c87e2348e1909384cb325511'
TOPIC_BATCHES_REVERT              = '\x6d80424573caa7280d1b1d9933dd38c7532f82305e148b3f3a9df551a4c53581'
TOPIC_STATE_ROOT_UPDATE           = '\x645e0b8f839353842bdac87abd27fc8bdda536e0731cdb7cc75e4f0740b575ac'
TOPIC_DESERT_MODE                 = '\x9f7e400a81dddbf1c18b1c37f82aa303d166295ca4b577eb2a7c23d4b704ba89'
TOPIC_CREATE_MARKET               = '\x134f63a6bbe3b3ef885ce4067eb2753fe1c912c51c4b8e0cc7966f21773c047e'
TOPIC_UPDATE_MARKET               = '\x3551e43c2bd6cb132e6bc5e0ab4022d8fa63dff212a9dd4ebaf40801705731b9'
TOPIC_REGISTER_ASSET_CONFIG       = '\xf1b24e81016b9f39e2290cf2a9303264a07534a569df7e6200a39573d7f26b0c'
TOPIC_UPDATE_ASSET_CONFIG         = '\xff23feaffcab98dc102270f0c98539db1067368280f613f9dfd91a601c20113d'
TOPIC_TREASURY_UPDATE             = '\x8a3509a4057c89a5993a4a3140c2ebf7e829d325d8998eaa6c48adcff98b2cef'
TOPIC_INSURANCE_FUND_OP_UPDATE    = '\xbbc858f043fabd2c7f56f0751bc461f96ba7e4a8d059fa6507ac6cf51238fa0f'
TOPIC_INITIALIZED                 = '\x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498'
-- Governance
TOPIC_NEW_GOVERNOR                = '\x5425363a03f182281120f5919107c49c7a1a623acc1cbc6df468b6f0c11fcf8c'
TOPIC_VALIDATOR_STATUS_UPDATE     = '\x065b77b53864e46fda3d8986acb51696223d6dde7ced42441eb150bae6d48136'
-- UpgradeGatekeeper (impl-rotation watch)
TOPIC_NEW_UPGRADABLE              = '\xecfd8b4d8bfc0590001d923f6db32faaad4c3d96097734fe5950f43980dabfc4'
TOPIC_NOTICE_PERIOD_START         = '\xabce748366d7d01473824f1bee75dc176759f56b88f00253e4a10d7528ca806f'
TOPIC_PREPARATION_START           = '\xd2b7d4a4a2b38481e36a9b8198af8b427261011fd199b7a1b7cb8f437aa25acd'
TOPIC_UPGRADE_COMPLETE            = '\x48bc8be43b04d57da4f0d65c05db98278a94d9e90b7348d5d2705cc78c9a9d2e'
TOPIC_UPGRADE_CANCEL              = '\x55cd34119fd31f1a8cc60aad1098023b450274eef2294e3e1b6dd452d58ce6fd'
TOPIC_NOTICE_PERIOD_CHANGE        = '\xf2b18f8abbd8a0d0c1fb8245146eedf5304887b12f6395b548ca238e054a1483'

-- ===== Selectors =====
-- ZkLighter user money flow
SEL_DEPOSIT                       = '\x8a857083'
SEL_DEPOSIT_BATCH                 = '\xea2102e4'
SEL_WITHDRAW                      = '\xd20191bd'
SEL_WITHDRAW_PENDING_BALANCE      = '\x2f25807e'
SEL_WITHDRAW_PENDING_LEGACY       = '\x975364c6'
SEL_CHANGE_PUBKEY                 = '\x17010c68'
-- ZkLighter batch lifecycle
SEL_COMMIT_BATCH                  = '\xe415f0f4'
SEL_VERIFY_BATCH                  = '\x23ff50e1'
SEL_EXECUTE_BATCHES               = '\x2d320e28'
SEL_REVERT_BATCHES                = '\xbdf723e8'
SEL_UPDATE_STATE_ROOT             = '\x7271277e'
-- ZkLighter desert mode
SEL_ACTIVATE_DESERT_MODE          = '\x22b22256'
SEL_PERFORM_DESERT                = '\x377d4194'
SEL_CANCEL_OUTSTANDING_DEPOSITS   = '\x1b6592fa'
-- ZkLighter admin
SEL_REGISTER_ASSET_CONFIG         = '\x25216fda'
SEL_REGISTER_ASSET                = '\xef228c02'
SEL_CREATE_MARKET                 = '\x0b4d1558'
SEL_UPDATE_MARKET                 = '\x99e51881'
SEL_SET_TREASURY                  = '\xf0f44260'
SEL_SET_INSURANCE_FUND_OPERATOR   = '\xaabe6078'
-- ZkLighter views
SEL_STATE_ROOT                    = '\x9588eca2'
SEL_DESERT_MODE                   = '\x02cfb563'
SEL_OPEN_PRIORITY_REQUEST_COUNT   = '\x72fc4c39'
SEL_COMMITTED_BATCHES_COUNT       = '\xaab78a8e'
SEL_EXECUTED_BATCHES_COUNT        = '\xd5102eea'
SEL_TOKEN_TO_ASSET_INDEX          = '\x899cfa29'
-- Governance
SEL_SET_VALIDATOR                 = '\x4623c91d'
SEL_CHANGE_GOVERNOR               = '\xe4c0aaf4'
SEL_IS_ACTIVE_VALIDATOR           = '\x40550a1c'
-- UpgradeGatekeeper
SEL_START_UPGRADE                 = '\x31a94da3'
SEL_FINISH_UPGRADE                = '\x253b153b'
SEL_CANCEL_UPGRADE                = '\x55f29166'
SEL_CUT_UPGRADE_NOTICE_PERIOD     = '\x389b8b3a'
SEL_SECURITY_COUNCIL_ADDRESS      = '\xc727927f'
-- Verifiers (both)
SEL_VERIFY                        = '\x7e4f7a8a'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT                 = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses — Ethereum mainnet (chain ID 1) =====
ETH_ZKLIGHTER_PROXY               = '\x3b4d794a66304f130a4db8f2551b0070dfcf5ca7'
ETH_ZKLIGHTER_IMPL                = '\xe16c893252616dd49913969f145e733b96a3e5a7'   -- live 2026-10-05
ETH_ADDITIONAL_ZKLIGHTER_IMPL     = '\x22f05515497ce8d78f3898088c474403ac9c668f'
ETH_ZKLIGHTER_VERIFIER_PROXY      = '\xac3ce44b6ff4e402858c99d5699ff63131572baa'
ETH_ZKLIGHTER_VERIFIER_IMPL       = '\xc4c2067ece6e33e50a30087ec14096715e56ae11'   -- live 2026-10-05
ETH_DESERT_VERIFIER               = '\x2adbd91742b64105a097bc37d20ebbca9a496085'
ETH_GOVERNANCE_PROXY              = '\xa464da0b43f80ee3ffc4795cbbfc78472b5c81a1'
ETH_GOVERNANCE_IMPL               = '\xe935fa009ae2f913a26b4411a901ecf6dbab6d43'   -- live 2026-10-05
ETH_UPGRADE_GATEKEEPER            = '\x94da8a995d0d82ef0fe7e509c6d76c22603b6f67'
ETH_MULTISIG_SECURITY_COUNCIL     = '\x92b12c9d85bf7bd2ef5d2f53f4cd4ce0be432045'   -- 4-of-7
ETH_MULTISIG_GOVERNOR             = '\x97a90ec950b6bcd9b190b566525b2bb92a2c03a2'   -- 3-of-5
ETH_TREASURY                      = '\x3dd7c834eaa70c98e1c224808a3c62163b344dae'
ETH_INSURANCE_FUND_OPERATOR       = '\x9cce444f8c60bd570986cd7d0ed7aec29f127310'
ETH_SAFE_SINGLETON_141            = '\x41675c099f32341bf84bfc5382af534df5c7461a'
ETH_USDC                          = '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'   -- asset index 3
-- Retired impls (match historical traces only): ZkLighter 0x831ef69b... (2026-06), 0x6e143358... (2026-09-29); Verifier 0xaa0b5b65... (2026-06), 0xd3e043d6... (2026-09-29); Governance 0x46d3c0c0... (to 2026-09-29)
-- ===== Robinhood Chain (4663) — separate Lighter instance (USDG-margined) =====
RH_ZKLIGHTER_PROXY                = '\x94bab9693ba2f6358507effcbd372b0660afff9d'
RH_ZKLIGHTER_IMPL                 = '\x82de5b1161c93afdfe21ba0d5343f01cd7401d90'
RH_SECOND_LOGIC_IMPL              = '\xda2b59ffb41485a6f21e14e479ae7b7ab29a997c'
RH_ZKLIGHTER_VERIFIER_PROXY       = '\xe1afbe2d670eff0e7c8a41f080792c011916ac31'
RH_DESERT_VERIFIER                = '\x56aeed6920dbb9e198c2c0072147a45684a06e10'
RH_GOVERNANCE_PROXY               = '\xf6f6bd6eea2b9a2041328732ccae4c5e1dd278b7'
RH_UPGRADE_GATEKEEPER             = '\x43cff77cd060a155dce5deb12b93b875f69f2716'
RH_GOVERNOR_SAFE                  = '\x8caf9ff9392f39e87cbc65a130c026caacd321ef'
RH_SECURITY_COUNCIL_EOA           = '\x4972e0cacb2ac45644ba054838e96ff4f6f7efdb'
RH_TREASURY_EOA                   = '\xac71ec137c892d02d531e48ceb1d060f9c9ac357'
RH_INSURANCE_FUND_OPERATOR_EOA    = '\x6ccdd1f3f599c69fa74eedc3dab28559fe99ab0a'
RH_USDG                           = '\x5fc5360d0400a0fd4f2af552add042d716f1d168'
-- NOTE: NOT deployed on Base / BNB / Avalanche / Arbitrum / Optimism / Polygon (eth_getCode = 0x)
```

---

## 11. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` (pycryptodome) from the **Sourcify-verified ABIs** of `ZkLighter`, `AdditionalZkLighter`, `ZkLighterVerifier`, `DesertVerifier`, `Governance`, `UpgradeGatekeeper` (all solc 0.8.25+commit.b61c2a91, viaIR, optimizer runs 1000). Six event topic0s cross-checked against **live `eth_getLogs`** on the ZkLighter proxy `0x3B4D…5ca7` in blocks 25,276,511–25,279,511 (1,296 logs; `NewPriorityRequest`/`BatchVerification`/`Deposit`/`BatchCommit`/`BatchesExecuted`/`WithdrawPending` all matched the computed values exactly).
- **Addresses:** existence-checked via `eth_getCode` on each of the seven chains' public RPCs — present on **Ethereum only**, `0x` on the other six. Proxy/impl wiring confirmed via `eth_call`: `UpgradeGatekeeper.zkLighterProxy()` = ZkLighter, `managedContracts(0..2)` = Governance / ZkLighterVerifier / ZkLighter, `getMaster()` = Multisig 2, `securityCouncilAddress()` = Multisig 1, `approvedUpgradeNoticePeriod()` = 1,814,400 s (21 d), `versionId()` = 60; `Governance.networkGovernor()` = Multisig 2, `usdc()` = Circle USDC; `ZkLighter.treasury()`/`insuranceFundOperator()`/`desertMode()` (false)/`stateRoot()`/counts read live; `tokenToAssetIndex(USDC)` = `USDC_ASSET_INDEX()` = 3.
- **Proxy impls:** read live from the EIP-1967 implementation slot `0x3608…2bbc` (2026-06-09: ZkLighter → `0x831E…7008`, ZkLighterVerifier → `0xAa0b…f5D6`, Governance → `0x46D3…1f08`; 2026-10-05: `0xE16c…E5A7`, `0xc4c2…aE11`, `0xE935…6D43`); admin slot `0xb531…6103` holds the UpgradeGatekeeper on all three; beacon slot `0xa3f0…3d50` empty everywhere. `DesertVerifier` + `UpgradeGatekeeper` confirmed non-proxy (all three slots `0x000…0`). The two Safes' singleton read from storage slot 0 (`0x41675C09…`, Safe v1.4.1) with `VERSION()` = `1.4.1`, thresholds 4 and 3.
- **Architecture:** Lighter is a zkBNB/zkSync-Lite-lineage app-specific rollup; the dual `ZkLighter`/`AdditionalZkLighter` split-logic pattern was confirmed by both impls being ≈24.5 KB (near the EVM code-size limit) behind one proxy. zk circuits and the verifier-generation pipeline are in `elliottech/lighter-prover` (Plonky2).
- **Re-checked 2026-09-29 (Robinhood Chain):** every Ethereum literal of §3 returns `0x` on Robinhood Chain (nonce 0). The Robinhood instance's addresses come from the Robinhood Chain docs ("Lighter Domains") and L2BEAT ("Lighter on Robinhood"); each one existence-checked with `eth_getCode`, proxy slots read, and the gatekeeper/governance/ZkLighter views of §6a read with `eth_call`. Pinned 12-hour window 2026-09-28 00:00–12:00 UTC: `Deposit` / `NewPriorityRequest` / `WithdrawPending` = Ethereum 337 / 363 / 169, Robinhood Chain 2,463 / 2,618 / 598; zero on the other six chains. All emitters on Robinhood Chain were the proxy of §6a.

**Authoritative sources:**
- Canonical repos: [`elliottech/lighter-contracts`](https://github.com/elliottech/lighter-contracts) · [`elliottech/lighter-prover`](https://github.com/elliottech/lighter-prover) (zk circuits → `ZkLighterVerifier`/`DesertVerifier`) · [`elliottech/lighter-python`](https://github.com/elliottech/lighter-python) / [`lighter-go`](https://github.com/elliottech/lighter-go) (SDKs)
- Docs: [docs.lighter.xyz](https://docs.lighter.xyz/) · [security audits](https://docs.lighter.xyz/security/security-audits) · [whitepaper](https://assets.lighter.xyz/whitepaper.pdf)
- Verified source: Sourcify `https://sourcify.dev/server/v2/contract/1/0x831EF69BaB8AF8B1037a4961B8d0674b124E7008` (the 2026-06-09 ZkLighter impl)
- Risk/architecture registry: [L2BEAT — Lighter](https://l2beat.com/scaling/projects/lighter) · [L2BEAT — Lighter on Robinhood](https://l2beat.com/layer2s/projects/lighter-robinhood) · [Robinhood Chain docs — Lighter Domains](https://docs.robinhood.com/chain/lighter-domains/)
- Explorer: [Etherscan — ZkLighter](https://etherscan.io/address/0x3b4d794a66304f130a4db8f2551b0070dfcf5ca7)
