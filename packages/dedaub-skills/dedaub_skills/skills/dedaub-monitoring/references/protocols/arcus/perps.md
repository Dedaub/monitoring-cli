# Arcus Perps (rootchain) — Topics, Selectors, Addresses (Robinhood Chain)

**Status:** verified against live RPC on Robinhood Chain (4663) and the official `arcus-xyz/rootchain-contracts-abis` repo (commit `8275e1a4`, 2026-07-08) on 2026-10-30. Every ABI in that repo matches the live implementation bytecode (all selectors and all non-role topics present).
**Scope:** the on-chain ("rootchain") side of the Arcus perpetuals exchange: custody vault, checkpoint manager, validator consensus, block executor, validator-logic beacon, emergency settlement, the Paxos USDG deposit/withdraw adapters and the governance timelock. Arcus deploys these on **Robinhood Chain (4663) only**. Topics and selectors are chain-agnostic. Addresses are network-specific.

Arcus is a perpetuals exchange from the dYdX team. An off-chain matching engine and a permissioned appchain run the exchange. The EVM rootchain on Robinhood Chain holds the funds and the final state. Users deposit USDG. The `PaxosDepositProxy` wraps it into **arcUSDG** (a Paxos vault share) and deposits that into the `BridgeVault`. The `BridgeVault` puts each deposit and each raw request into the `CheckpointManager` inbox. Validators vote on appchain blocks in `ValidatorConsensus`. The `BlockExecutor` relays the quorum signatures. The executed block finalizes a batch in the `CheckpointManager`, which runs "side effects" (withdrawals, deposit confirmations) on the `BridgeVault`.

There is **no on-chain price oracle** in the rootchain. Mark and oracle prices live on the appchain. Validators check the signed oracle prices off-chain. A monitor sees only deposits, withdrawals, batch finalization and governance on-chain. Trades, funding and liquidations are not visible as rootchain events.

---

## 0. Contract families

| Contract | Role | Proxy? |
|----------|------|--------|
| **BridgeVault** | Custody of the margin asset (arcUSDG) and of multi-asset collateral tokens. Deposit inbox entry, withdrawal execution, escape-hatch payouts. Holds 64.5 M arcUSDG on 2026-10-30. | UUPS (EIP-1967) |
| **CheckpointManager** | Inbox of requests, state-root checkpoints (`BatchFinalized`), side-effect execution, emergency-settlement proofs. `marginAsset()` = arcUSDG. | UUPS (EIP-1967) |
| **ValidatorConsensus** | Validator set (3 validators, threshold 2), block votes, block execution, validator governance actions. | UUPS (EIP-1967) |
| **BlockExecutor** | Relays a validator vote quorum on-chain (`executeBlockWithSigs`). Callers need `OPS_EXECUTOR_ROLE`. | No (6,920 B) |
| **ValidatorBeacon** | Registry of approved validator logic versions (`proposeVersion`, opposition window). | UUPS (EIP-1967) |
| **EmergencySettlement** | Stateless Merkle-proof verifier for the escape hatch. All functions are `pure`. | No (2,240 B) |
| **PaxosDepositProxy** | USDG deposit entry point. Wraps USDG into arcUSDG through the Paxos Teller, then calls `BridgeVault.initiateDeposit*`. | UUPS (EIP-1967) |
| **PaxosWithdrawalUnwrapper** | Withdrawal hook. The `BridgeVault` uses it to turn arcUSDG back into USDG on payout. | No (864 B) |
| **TimelockController** | OpenZeppelin timelock (min delay 86,400 s), behind its own UUPS proxy. Holds `DEFAULT_ADMIN_ROLE` on the core contracts. | UUPS (EIP-1967) |
| arcUSDG ("Arcus USDG", 6 dec) | Paxos vault share token. The margin asset. Not part of the ABI repo. | No (8,659 B) |
| Paxos Teller | Mints and burns arcUSDG against USDG. Not part of the ABI repo. | No (6,111 B) |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 BridgeVault (`0x14b1…897c`)

| topic0 | Event |
|--------|-------|
| `0x4127e8b2fbc996854e6c019b71c15280dc22073ff1de294067d0ac9bb0090e07` | `DepositInitiated(uint64 indexed inboxIndex, address indexed depositor, address indexed owner, uint16 accountIndex, address token, uint256 amount, uint64 expiresAt, address cancelRecipient, bool anyoneCanExecuteCancel)` |
| `0x3c5abf8f58d5fe26962fcc25e4603a9487fdee95f79b17d69c6b4f10347e7f33` | `DepositConfirmed(uint64 indexed inboxIndex, address indexed owner, uint16 accountIndex, address token, uint256 amount)` |
| `0x501f866afc9de766bfb8f55d7f749d8ca754b0fef2864ee7b2bffdcd6733f8ea` | `DepositCancelled(uint64 indexed inboxIndex, address indexed cancelRecipient, address indexed token, uint256 amount)` |
| `0x54449f5f6330b0baa603fd546b6289f616cd725cfa266a09780c7c5fe806589b` | `WithdrawalInitiated(uint64 indexed withdrawalId, address indexed recipient, address indexed token, uint256 amount, bool anyoneCanExecute)` |
| `0x8c1b22e85e3e21f4299b06e651504b70a76ebe2c70ffecc1158a3c1bdddc06fa` | `WithdrawalUnwrapped(uint64 indexed withdrawalId, address indexed recipient, address indexed inputToken, uint256 inputAmount, address outputToken, uint256 outputAmount)` |
| `0xd4ae70ceaa0a8901abad43ac0f1d5f1229a537aa6ad0e22e21265e0948668ef1` | `WithdrawalExecuted(uint64 indexed withdrawalId, address indexed recipient, address indexed token, uint256 amount)` |
| `0x284854e64be3ab0d58fab57f3ada0f124c98e29ceffe796894f9217fa6d3c7b0` | `RawRequestEnqueued(uint64 indexed inboxIndex, address indexed sender, bytes payload)` |
| `0xb96afb8549c64ecf6cfc2e46d19f34b056423404c78d11f694a1252d8d677870` | `DepositConfigUpdated(address indexed token, bool allowed, uint256 minAmount)` |
| `0xc3a507db473a3906eb2525804e914c76ec27983c3630afddc285ebd1e785ed83` | `WithdrawalConfigUpdated(address indexed token, address unwrapper)` |
| `0x9fb50361ff20c95ee94e29cafef7c5a88611fb870013bc74091a2fd5e2cc496d` | `DepositsPausedUpdated(bool oldPaused, bool newPaused)` |
| `0x721196fd60398ccf5df75d7828dd741b90194465ae5dd29f42965050412779e3` | `WithdrawalsPausedUpdated(bool oldPaused, bool newPaused)` |
| `0x7d7cc90a8293e0a39e036c7afccc8d187cfc850e2018fe834409432f7a91a90d` | `DepositExpiryPeriodUpdated(uint64 oldSeconds, uint64 newSeconds)` |
| `0x3e4d40377bd5f07b07d593a4535c739778631e3ae6033a846ecfb5241ce56d7e` | `RawRequestGasBurnUpdated(uint64 oldGasBurn, uint64 newGasBurn)` |
| `0x2af994234257cf34fc6b286beb6322283abee0fed8f939348131c9f8cd9fe863` | `RawRequestMaxPayloadBytesUpdated(uint64 oldMax, uint64 newMax)` |
| `0x684ca2057b12fc6cc8862b2516ec7e0a7c470c66e8abfac4364d3bcb329f45df` | `CheckpointManagerUpdated(address indexed oldCm, address indexed newCm)` (also emitted by ValidatorConsensus) |

Live sample (blocks 101,724,352–101,824,352): `WithdrawalInitiated` 262, `WithdrawalUnwrapped` 262, `DepositInitiated` 225, `DepositConfirmed` 225.

### 1.2 CheckpointManager (`0xa3d4…f487`)

| topic0 | Event |
|--------|-------|
| `0x16fe649dcfbffb4558cd7d26ca49811aee0b43a841a9b79b317700a1367f4dbc` | `RequestEnqueued(uint64 indexed inboxIndex, bytes32 indexed hash, uint64 timestamp, bytes payload)` |
| `0xcbfb96c256e48608df21cfaea3461e46689bb491fb9e894fc32c8de2e7e5cdf8` | `BatchFinalized(uint64 indexed index, bytes32 stateRoot, bytes32 processedRequestsHash, bytes32 sideEffectsHash)` |
| `0xd95edd2f13f5d609ea80af610f1376a17a0592f23ffead544302a8988636c521` | `SideEffectExecuted(uint64 indexed batchIndex, uint64 indexed effectIndex, address indexed target)` |
| `0x13b21a05f34e34561fe0d14ec6ce47d2dbb756c68ac06ce537bc9035ae9be13c` | `EmergencySettlementActivated(uint64 finalizedCount, uint64 finalInboxHead)` — **escape hatch fired** |
| `0xf86845e225d059d83768edbfd064aa82f914a7ee9f11c8e3a2fbd72ce965fcc2` | `SettlementSummaryProven(uint256 marginPool, uint256 totalPositiveMargin, uint256 totalBadDebt)` |
| `0x6667d17650fad7c5aab52fa9f2a44a73492c24bf72dfcce1f7515abd6b4ec230` | `MarginSettled(address indexed owner, uint16 indexed accountIndex, int256 netMargin, uint256 payout)` |
| `0x2344491a9d495c7ebcef347e110fee8540ea779119deb83441032534a5729c15` | `CollateralSettled(address indexed owner, uint16 indexed accountIndex, address indexed token, uint256 amount)` |
| `0x86cafad4e48ec1edd3bf1bb4b05fbe08a979cc3a0bfceb82a841aa502c5e666b` | `BridgeVaultUpdated(address indexed oldBv, address indexed newBv)` |
| `0x5a5339ada220b41e93217d3456d1ffee426a067f8107fa616b7a3d8cb3639dbb` | `EmergencySettlementUpdated(address indexed oldEs, address indexed newEs)` |
| `0xa921b88bb89385856d3c94e118d7092bfd3a987bda1fa912a4151cd93c5e00b2` | `EmergencySettlementDelayUpdated(uint64 oldSeconds, uint64 newSeconds)` |
| `0x01299c9156edaa5cfe54790b331c6be4f003f6e43d46b725ae014e0614c8e4b6` | `MaxInboxBacklogUpdated(uint64 oldMax, uint64 newMax)` |

Live sample (blocks 101,780,000–101,830,000): `BatchFinalized` 352, `SideEffectExecuted` 276, `RequestEnqueued` 116.

### 1.3 ValidatorConsensus (`0x9d03…5da8`) and BlockExecutor (`0xa49f…c123`)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x76644ae2a4aff6b7b437ebcf769723cc74db48be900adaaefe688c38a5fb09d8` | `BlockVoteCast(uint64 indexed blockNumber, address indexed validator, bytes32 indexed blockHash, string dataAvailability, uint64 logicVersion)` | VC |
| `0x8ee1fd17f60d0cc5f1674dc517d3f5fd24758fb1d8d5bacfea26f49a58ea48e7` | `BlockVoteRetracted(uint64 indexed blockNumber, address indexed validator, bytes32 indexed blockHash)` | VC |
| `0x8574a03e6f3849034e975e95d1a671efded4ea18b39f1d783bfc0bee11acd95f` | `BlockExecuted(uint64 indexed blockNumber, bytes32 indexed blockHash, bytes32 stateRoot)` | VC |
| `0x0142109ca194e36671c745253dd9d1855d60bc168d1c6809eeb0c499bc616f3c` | `GovernanceVoteCast(uint64 indexed actionNumber, address indexed validator, bytes32 indexed actionHash, bytes32 parentActionHash, (address,bytes)[] calls, uint64 deadline)` | VC |
| `0x5ab62d452f0a675526a5eeaf630b5efdf3a111f6bd466774958dcd8e6c4ab06d` | `GovernanceVoteRetracted(uint64 indexed actionNumber, address indexed validator, bytes32 indexed actionHash)` | VC |
| `0x12b5001f75701a111a484218726a1bba0d7b3cd9b7c2f9b6727a1873ea48cfcd` | `GovernanceActionExecuted(uint64 indexed actionNumber, bytes32 indexed actionHash, uint256 callCount)` | VC — **validator-governed admin call** |
| `0xa21090c78fee7c1d590accd2ebdc6e3265a01cb67bbfff5b5d8927a55f9d46e8` | `ThresholdUpdated(uint64 oldThreshold, uint64 newThreshold)` | VC |
| `0xc83ae09279ecff656a01fdd2aee1f00beb68461ff8ce9bed10c82d7d2f18af1f` | `BlockExecutedWithSigs(uint64 indexed blockNumber, bytes32 indexed blockHash, uint256 relayedVotes, address indexed caller)` | BE |
| `0xdabef4ebaef8d898f7ae6de78b6df36b245203c5c86b74c010796d21970a1888` | `GovernanceActionExecutedWithSigs(uint64 indexed actionNumber, uint256 relayedVotes, address indexed caller)` | BE |

Live sample (same window): `BlockVoteCast` 704, `BlockExecuted` 352, `BlockExecutedWithSigs` 352. One block = two votes + one execution.

### 1.4 ValidatorBeacon (`0x9ffc…d8ad`)

| topic0 | Event |
|--------|-------|
| `0xb1ebc98c593e8741353f03895b6149b47759f82523880b1defbb65df01630669` | `VersionProposed(uint64 indexed version, bytes32 indexed logicHash, string artifactURI, uint64 proposedAt, uint64 earliestActivation)` |
| `0xeb95af8a27c14978d2c7e7637745a17ee93335907f8286251fab8417bd965843` | `VersionOpposed(uint64 indexed version, address indexed opposer)` |
| `0x39076ddd9d3bdf20433b9586a3c41c8432c969e831ce5464cb8730d5fa6551cf` | `VersionUnopposed(uint64 indexed version, address indexed opposer)` |
| `0x4f86ea186dc793c70c8979a09684e7f4646b62199d57af115f77e227b861b77c` | `VersionCancelled(uint64 indexed version)` |

One `VersionProposed` log exists since deployment (the genesis version).

### 1.5 PaxosDepositProxy (`0xd42c…e8b2`)

| topic0 | Event |
|--------|-------|
| `0x2b99bfed5ab08e90a6e4f5a50e45ddb72666aa6fc63e8a77efcdbf0466f4fbfc` | `PaxosDepositInitiated(uint64 indexed inboxIndex, address indexed depositor, address indexed cancelRecipient, bool anyoneCanExecuteCancel)` |
| `0x6166d8c1326378f25d595ca34b79c29c17ba4dbecbb7c9e6c691fa2cf27ddba0` | `PaxosDepositCancelled(uint64 indexed inboxIndex, address indexed recipient)` |

### 1.6 TimelockController (`0x0dA1…001D`) — OpenZeppelin

| topic0 | Event |
|--------|-------|
| `0x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca` | `CallScheduled(bytes32 indexed id, uint256 indexed index, address target, uint256 value, bytes data, bytes32 predecessor, uint256 delay)` |
| `0xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58` | `CallExecuted(bytes32 indexed id, uint256 indexed index, address target, uint256 value, bytes data)` |
| `0x20fda5fd27a1ea7bf5b9567f143ac5470bb059374a27e8f67cb44f946f6d0387` | `CallSalt(bytes32 indexed id, bytes32 salt)` |
| `0xbaa1eb22f2a492ba1a5fea61b8df4d27c6c8b5f3971e63bb58fa14ff72eedb70` | `Cancelled(bytes32 indexed id)` |
| `0x11c24f4ead16507c69ac467fbd5e4eed5fb5c699626d2cc6d66421df253886d5` | `MinDelayChange(uint256 oldDuration, uint256 newDuration)` |

### 1.7 Shared (OpenZeppelin AccessControl / UUPS) — all proxies above

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 BridgeVault

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x43ecb268` | `initiateDeposit(address,uint16,address,uint256)` | `(uint64 inboxIndex)`. `(owner, accountIndex, token, amount)`. Direct token deposits (multi-asset collateral). |
| `0x277f8fe0` | `initiateDepositReturnToOwner(address,uint16,address,uint256,bool)` | `(uint64)`. Cancel refund goes to owner. |
| `0x37e91fa5` | `initiateDepositReturnToSender(address,uint16,address,uint256,bool)` | `(uint64)`. Cancel refund goes to `msg.sender`. |
| `0x575d5907` | `cancelDeposit(uint64)` | Reclaim an unconfirmed deposit after `expiresAt`. |
| `0x39a2a7bd` | `confirmDeposit(uint64)` | Side effect from the CheckpointManager. |
| `0xcb1f83a3` | `initiateWithdrawal(address,address,uint256,bool)` | `(uint64 withdrawalId)`. Side effect from the CheckpointManager. |
| `0xd28dfa6e` | `executeWithdrawal(uint64)` | Pays a pending withdrawal. |
| `0x530ef25c` | `enqueueRawRequest(bytes)` | `(uint64)`. Forced request (forced trade / forced withdrawal) into the inbox. Burns gas (`rawRequestGasBurn`). |
| `0xd86fac1b` | `setDepositConfigs(address[],(bool,uint256)[])` | Admin. Token allow-list + minimum. |
| `0x14667b34` | `setWithdrawalConfigs(address[],(address)[])` | Admin. Unwrapper per token. |
| `0x1c481e2d` | `setDepositsPaused(bool)` | Privileged (guardian or admin). |
| `0xb6737162` | `setWithdrawalsPaused(bool)` | Privileged (guardian or admin). |
| `0x873710ee` | `setDepositExpiryPeriod(uint64)` | Admin (now 345,600 s = 4 days). |
| `0x5d7fcbce` | `setRawRequestGasBurn(uint64)` | Admin. |
| `0x59d571c9` | `setRawRequestMaxPayloadBytes(uint64)` | Admin. |
| `0xbc08452b` | `setCheckpointManager(address)` | Admin. Rewires the trust root. |
| `0x228a66e3` | `depositConfig(address)` | `((bool allowed,uint256 minAmount))`. view. |
| `0xb73c0b21` | `withdrawalConfig(address)` | `((address unwrapper))`. view. |
| `0x523fba7f` | `tokenBalances(address)` | `((uint256,uint256,uint256))`. view. |
| `0x6ee34522` | `pendingDepositByIndex(uint64)` | `((address,uint16,uint64,bool,address,uint256,address))`. view. |
| `0xe9e417a3` | `pendingWithdrawalById(uint64)` | `((address,address,uint256,bool))`. view. |
| `0x4a9122e3` | `nextWithdrawalId()` | `(uint64)`. view (32,114 on 2026-10-30). |
| `0x60da3e83` / `0xe9f2838e` | `depositsPaused()` / `withdrawalsPaused()` | `(bool)`. view. |
| `0xc0857ba0` | `checkpointManager()` | `(address)`. view. |
| `0xd7964043` / `0x8769c47c` / `0xda7300bf` | `depositExpiryPeriod()` / `rawRequestGasBurn()` / `rawRequestMaxPayloadBytes()` | `(uint64)`. view. |

### 2.2 PaxosDepositProxy and PaxosWithdrawalUnwrapper

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x43ecb268` | `initiateDeposit(address,uint16,address,uint256)` | `(uint64)`. USDG entry point. `token` must be USDG. Same selector as BridgeVault — disambiguate by `to`. |
| `0x277f8fe0` | `initiateDepositReturnToOwner(address,uint16,address,uint256,bool)` | `(uint64)`. |
| `0xf9740b64` | `initiateDepositReturnToOwnerWithPermit(address,uint16,address,uint256,bool,uint256,uint256,bytes)` | `(uint64)`. Permit2 path. |
| `0x37e91fa5` | `initiateDepositReturnToSender(address,uint16,address,uint256,bool)` | `(uint64)`. |
| `0x575d5907` | `cancelDeposit(uint64)` | Unwraps and refunds an expired deposit. |
| `0x76dafdd2` | `cancelInfoByIndex(uint64)` | `(address,bool)`. view. |
| `0xac03e9f0` / `0x57edab4e` / `0x2495a599` / `0x996c6cc3` / `0x12261ee7` | `bridgeVault()` / `teller()` / `underlyingToken()` / `wrappedToken()` / `permit2()` | `(address)`. view. |
| `0x00f714ce` | `withdraw(uint256,address)` | Unwrapper. `(address token, uint256 amount)`. Called by the BridgeVault. |

### 2.3 CheckpointManager

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x3e9f3796` | `enqueueRequest(bytes)` | `(uint64)`. `INBOX_WRITER_ROLE` (= BridgeVault). |
| `0x9c0ba83a` | `finalizeBatch(uint64,bytes32,bytes32,bytes32,bytes32[],(address,bytes)[])` | `FINALIZER_ROLE` (= ValidatorConsensus). Runs side effects. |
| `0x9c6b317d` | `activateEmergencySettlement()` | Permissionless after `emergencySettlementDelay` (1,209,600 s = 14 days) of no finalization. |
| `0xcd7e56f4` | `proveSettlementMargin(address,uint16,int256,bytes32,(uint256,bytes32[]))` | Escape-hatch claim of USDG margin. |
| `0x47a7e794` | `proveSettlementCollateral(address,uint16,int256,bytes32,address,uint256,(uint256,bytes32[]),(uint256,bytes32[]))` | Escape-hatch claim of a collateral token. |
| `0xc8474200` | `proveSettlementSummary(uint256,uint256,uint256,(uint256,bytes32[]))` | Escape-hatch summary (margin pool, bad debt). |
| `0xebcb0b7a` / `0xceffe815` / `0x67e4b67b` / `0x14f83e30` | `setBridgeVault(address)` / `setEmergencySettlement(address)` / `setEmergencySettlementDelay(uint64)` / `setMaxInboxBacklog(uint64)` | Admin. |
| `0x991beafd` | `latestStateRoot()` | `(bytes32)`. view. |
| `0xe5cb0d17` | `finalizedCount()` | `(uint64)`. view (2,538,752 on 2026-10-30). |
| `0x884b5c14` / `0x1bf19a5a` | `inboxHead()` / `inboxTail()` | `(uint64)`. view. Backlog = tail − head; max 1,000. |
| `0x4b8f506e` | `getInboxEntry(uint64)` | `((bytes32,uint64))`. view. |
| `0x70636f9f` | `inEmergencySettlement()` | `(bool)`. view. `false` on 2026-10-30. |
| `0x82689cae` | `marginAsset()` | `(address)`. view = arcUSDG. |
| `0x6332520b` / `0x5ce6099d` | `marginClaimed(uint256)` / `collateralClaimed(uint256,address)` | `(bool)`. view. Escape-hatch nullifiers. |
| `0x3df55efd` / `0xe86afa79` | `FINALIZER_ROLE()` / `INBOX_WRITER_ROLE()` | `(bytes32)`. view. |

### 2.4 ValidatorConsensus, BlockExecutor, ValidatorBeacon

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x87ce6526` | `voteBlock(uint64,bytes32,string,uint64)` | `VALIDATOR_ROLE`. |
| `0x47e457af` | `voteBlockBySig(uint64,bytes32,string,uint64,address,uint64,uint64,bytes)` | EIP-712 signed vote. |
| `0xb887874f` | `unvoteBlock(uint64,bytes32)` | |
| `0x56dd1f61` | `executeBlock((bytes32,bytes32,bytes32,uint64,uint64,bytes32,bytes32),bytes32[],(address,bytes)[])` | `EXECUTOR_ROLE` (= BlockExecutor). Calls `finalizeBatch`. |
| `0xd531ec5b` | `voteGovernanceAction(uint64,bytes32,(address,bytes)[],uint64)` | Validator governance. |
| `0x6d8e3154` | `voteGovernanceActionBySig(uint64,bytes32,(address,bytes)[],address,uint64,uint64,bytes)` | |
| `0x613ed15d` | `unvoteGovernanceAction(uint64,bytes32)` | |
| `0x90459522` | `executeGovernanceAction(uint64,bytes32,(address,bytes)[],uint64)` | `(bytes[])`. Arbitrary calls with ValidatorConsensus as `msg.sender`. |
| `0x43bd65f1` / `0x7813780a` | `cancelBlockVoteSignatures(uint64)` / `cancelGovernanceVoteSignatures(uint64)` | `(uint256)`. Nonce bump. |
| `0x17c4de35` | `setThreshold(uint64)` | Admin. |
| `0xbc08452b` | `setCheckpointManager(address)` | Admin. |
| `0x42cde4e8` | `threshold()` | `(uint64)`. view = 2. |
| `0x5fc3c09f` | `executeBlockWithSigs((bytes32,bytes32,bytes32,uint64,uint64,bytes32,bytes32),bytes32[],(address,bytes)[],(string,uint64,address,uint64,uint64,bytes)[])` | BlockExecutor. `OPS_EXECUTOR_ROLE`. |
| `0x62c7baca` | `executeBlocksWithSigs(((bytes32,bytes32,bytes32,uint64,uint64,bytes32,bytes32),bytes32[],(address,bytes)[],(string,uint64,address,uint64,uint64,bytes)[])[])` | `(uint64)`. BlockExecutor batch. |
| `0x59354462` | `executeGovernanceActionWithSigs(uint64,bytes32,(address,bytes)[],uint64,(address,uint64,bytes)[])` | `(bytes[])`. BlockExecutor. |
| `0x1c5b7a3c` | `proposeVersion(bytes32,string,uint64)` | `(uint64)`. ValidatorBeacon, `PROPOSER_ROLE`. |
| `0x35ec6482` / `0x194b67f8` / `0x03ee6c7d` | `opposeVersion(uint64)` / `unopposeVersion(uint64)` / `cancelVersion(uint64)` | ValidatorBeacon. |
| `0xc07f47d4` | `latestVersion()` | `(uint64)`. view. |

### 2.5 EmergencySettlement (all `pure`)

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x66954244` | `proveSettlementMargin(address,uint16,int256,bytes32,(uint256,bytes32[]),bytes32)` | `(int256)` |
| `0xbc83d690` | `proveSettlementCollateral(address,uint16,int256,bytes32,address,uint256,(uint256,bytes32[]),(uint256,bytes32[]),bytes32)` | `(uint256)` |
| `0x88fab7f0` | `proveSettlementSummary(address,uint256,uint256,uint256,(uint256,bytes32[]),bytes32)` | `(uint256,uint256,uint256)` |
| `0x3ddbca92` | `computeAccountKey(address,uint16)` | `(uint256)` |

### 2.6 TimelockController and shared admin

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x01d5062a` | `schedule(address,uint256,bytes,bytes32,bytes32,uint256)` | `PROPOSER_ROLE`. |
| `0x8f2a0bb0` | `scheduleBatch(address[],uint256[],bytes[],bytes32,bytes32,uint256)` | |
| `0x134008d3` | `execute(address,uint256,bytes,bytes32,bytes32)` | payable. `EXECUTOR_ROLE`. |
| `0xe38335e5` | `executeBatch(address[],uint256[],bytes[],bytes32,bytes32)` | payable. |
| `0xc4d252f5` | `cancel(bytes32)` | `CANCELLER_ROLE`. |
| `0x64d62353` | `updateDelay(uint256)` | Self-call only. |
| `0xf27a0c92` | `getMinDelay()` | view = 86,400. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | payable. UUPS upgrade on every proxy here. |
| `0x2f2ff15d` / `0xd547741f` / `0x36568abe` | `grantRole(bytes32,address)` / `revokeRole(bytes32,address)` / `renounceRole(bytes32,address)` | AccessControl. |
| `0xa3246ad3` | `getRoleMembers(bytes32)` | `(address[])`. view (AccessControlEnumerable). |

### 2.7 Role identifiers (`keccak256(name)`)

| Role | bytes32 | Holders on 2026-10-30 |
|------|---------|-----------------------|
| `DEFAULT_ADMIN_ROLE` | `0x00…00` | BridgeVault, CheckpointManager, ValidatorConsensus, ValidatorBeacon, PaxosDepositProxy, TimelockController: {TimelockController, ValidatorConsensus, CheckpointManager}. BlockExecutor: {Safe `0x4f1d…ebe2`, ValidatorConsensus, CheckpointManager}. |
| `GUARDIAN_ROLE` | `0x55435dd261a4b9b3364963f7738a7a662ad9c84396d64be3365284bb7f0a5041` | BridgeVault: Safes `0x4f1d…ebe2`, `0x1d6f…7316` (pause). |
| `FINALIZER_ROLE` | `0x53ea8c2084bd069d8c2df22bdca7223415cd9c0b605c29d1a0d06f15fcd3eed4` | CheckpointManager: ValidatorConsensus. |
| `INBOX_WRITER_ROLE` | `0x5bc4c9cb37a60b31fcb37fbe931b16adafbd727056a2dcd8b1781f6d5656fb2f` | CheckpointManager: BridgeVault. |
| `VALIDATOR_ROLE` | `0x21702c8af46127c7fa207f89d0b0a8441bb32959a0ac7df790e9ab1a25c98926` | ValidatorConsensus: `0xfd2b…ee51`, `0x19f4…009b`, `0x0f51…7ff7`. |
| `EXECUTOR_ROLE` | `0xd8aa0f3194971a2a116679f7c2090f6939c8d4e01a2a8d7e41d55e5351469e63` | ValidatorConsensus: BlockExecutor. Timelock: {Safe `0x4f1d…ebe2`, VC, CM}. |
| `OPS_EXECUTOR_ROLE` | `0xeb8c85c773f27d014b80f70f7e0928b598de17d7d7d4b93ec50904fa5330e1ed` | BlockExecutor: EOAs `0xa9e2…0f93`, `0xa1f8…5cd7`. |
| `PROPOSER_ROLE` | `0xb09aa5aeb3702cfd50b6b62bc4532604938f21248a27a1d5ca736082b6819cc1` | ValidatorBeacon: Safe `0x4f1d…ebe2`. Timelock: {Safe `0x4f1d…ebe2`, VC, CM}. |
| `CANCELLER_ROLE` | `0xfd643c72710c63c0180259aba6b2d05451e3591a24e58b62239378085726f783` | Same as `PROPOSER_ROLE`. |

---

## 3. Addresses — Robinhood Chain (chain ID 4663)

All verified with `eth_getCode` on `https://robinhood-rpc.publicnode.com` on 2026-10-30. Deployment blocks are from the official `deployments.json` and match the deployment receipts.

| Role | Address | One-liner |
|------|---------|-----------|
| **BridgeVault** | `0x14b107cf534239c59571b066cb6497a321da897c` | Custody vault. EIP-712 `verifyingContract` for withdrawals. Block 159,148. |
| **CheckpointManager** | `0xa3d46d248224070f58c5f750e1f2fca2123df487` | Inbox + checkpoints + escape hatch. Block 159,135. |
| **ValidatorConsensus** | `0x9d032106ae6e41f36132fff1e7b0d973b4e55da8` | Validator votes, threshold 2 of 3. Block 159,142. |
| **BlockExecutor** | `0xa49f317086368da903ea40a286ad675664c9e123` | Quorum relayer. Block 159,162. |
| **ValidatorBeacon** | `0x9ffc5bce40ca9f0f17e7a01911199d7b1761d8ad` | Validator logic versions. Block 159,145. |
| **EmergencySettlement** | `0x9edf37f7dbe61ccd75794d5f727bef1bc4d4eabe` | Proof verifier. Block 159,146. |
| **PaxosDepositProxy** | `0xd42c46c7bad6a54b38395f846b09981ce75fb8e2` | USDG deposit entry. Also the `bridgeVault()` of the pToken factory. Block 159,150. |
| **PaxosWithdrawalUnwrapper** | `0xa4aca501bd4c11f3c09019e5a3d876e48286edaa` | arcUSDG → USDG on withdrawal. Block 159,152. |
| **TimelockController** | `0x0dA180B14721CE46A83669b4816cb652caa1001D` | 1-day timelock. Block 814,616. |
| arcUSDG (margin asset) | `0x4fdbdaf4800fc28c22a967d23a343acce34315a4` | "Arcus USDG", 6 decimals. BridgeVault balance 64,500,097.71 on 2026-10-30. |
| Paxos Teller | `0x323f89aa49ea8626008de5d6941a25bde406b501` | Wraps USDG ↔ arcUSDG. |
| USDG (Paxos) | `0x5fc5360d0400a0fd4f2af552add042d716f1d168` | Underlying token (see [paxos/usdg.md](../paxos/usdg.md)). |
| Safe (guardian / proposer) | `0x4f1d777bf36e259f3cb66f2ce969f4c5de05ebe2` | Safe 2-of-5. |
| Safe (guardian) | `0x1d6f8dc865326080a393b0986d9d9af0d7e97316` | Safe 2-of-5. |
| Validators | `0xfd2b8e0529cccba28faa0946318322f1ca9bee51`, `0x19f45260a20f38181a87a8da866dccff7f6d009b`, `0x0f517fd397c7dd6baa968bbeaef5622a52717ff7` | `VALIDATOR_ROLE` on ValidatorConsensus. |
| Ops executors | `0xa9e27a418529c23fc0848357a14f3adbbc9e0f93`, `0xa1f8e664d0d9567eaa7e120958f4cbc973ff5cd7` | `OPS_EXECUTOR_ROLE` on BlockExecutor. |

Testnet (Robinhood Chain testnet 46630, not a target chain): BridgeVault `0x9a6d3499149fea853efe775a3577701539054eaf`, PaxosDepositProxy `0xb872366eef371d4afb7c6d4d2abd53c17292a34d`, mock USDG `0x293b337712d4312776a3a2d292f44410e7873bad`. The docs say these change on every testnet reset.

## 4. Cross-chain summary

| Chain (ID) | BridgeVault | CheckpointManager | Other rootchain contracts |
|------------|-------------|-------------------|---------------------------|
| Robinhood Chain (4663) | `0x14b1…897c` | `0xa3d4…f487` | ✓ all nine |
| Ethereum (1) | — | — | — |
| Base (8453) | — | — | — |
| BNB (56) | — | — | — |
| Avalanche (43114) | — | — | — |
| Arbitrum (42161) | — | — | — |
| Optimism (10) | — | — | — |
| Polygon (137) | — | — | — |
| Arc (5042) | — | — | — |

`eth_getCode` returns `0x` for all eleven listed addresses (nine rootchain contracts, arcUSDG and the Teller) on the other eight chains (2026-10-30). Arcus has no rootchain on any other chain. Users from other chains arrive through the third-party "Fun" deposit flow, which bridges to USDG on Robinhood Chain first.

## 5. Proxies

| Contract | Pattern | Current implementation | Upgrade history (`Upgraded` block → impl) | Upgrade auth |
|----------|---------|------------------------|-------------------------------------------|--------------|
| **BridgeVault** | UUPS (ERC1967Proxy, 109 B) | `0x71fce0590d6ce46d92e9fd982e1d65bb8aac6319` (`version()` = 4) | 159,148 `0x255590eaf01e637599c044554768ae75f128b3e7` → 429,869 `0x44c6c2a96e7e51eb0dd81cef58940faa39babf78` → 89,453,534 `0x71fce0590d6ce46d92e9fd982e1d65bb8aac6319` | `DEFAULT_ADMIN_ROLE` |
| **CheckpointManager** | UUPS | `0x8e3e5ca0ec4a76bb68c83873abcabd5a34787589` | 159,135 only | `DEFAULT_ADMIN_ROLE` |
| **ValidatorConsensus** | UUPS | `0xabd100265d53e92ec5fb2c95b8f601aff6061676` | 159,142 only | `DEFAULT_ADMIN_ROLE` |
| **ValidatorBeacon** | UUPS | `0x56a989dda43b1c67d073f8f8a49e9bd99d372b11` | 159,145 only | `DEFAULT_ADMIN_ROLE` |
| **PaxosDepositProxy** | UUPS | `0x15858943f4be0a4fe01e42898242c00d1a99122b` | 159,150 only | `DEFAULT_ADMIN_ROLE` |
| **TimelockController** | UUPS | `0x20cde9c3c7f053e049b4ef94d042dde589f20264` | 814,616 only | `DEFAULT_ADMIN_ROLE` (TL, VC, CM) |
| BlockExecutor | Not a proxy | — | — | — |
| EmergencySettlement | Not a proxy | — | — | — |
| PaxosWithdrawalUnwrapper | Not a proxy | — | — | — |

All five 109-byte proxies share one code hash. The EIP-1967 admin and beacon slots are zero on every proxy (UUPS, no ProxyAdmin). Watch `Upgraded(address)` `0xbc7cd75a…` on each proxy.

## 6. Detection invariants & gotchas

1. **`DepositInitiated.depositor` is usually the PaxosDepositProxy, not the user.** In the sample, 225 of 225 deposits had `depositor = 0xd42c…e8b2`. The beneficiary is `owner` (topic3) plus `accountIndex`. `token` is arcUSDG for USDG deposits. Direct token deposits (multi-asset collateral, e.g. WETH or Stock Tokens) have `depositor = owner`.
2. **Amounts are arcUSDG with 6 decimals.** The Teller wraps 1:1 at deposit in the sample (`WithdrawalUnwrapped` input = output). Do not assume this ratio holds forever. Read both amounts.
3. **A deposit is not credited until `DepositConfirmed`.** `DepositInitiated` → (batch finalized) → `DepositConfirmed` with the same `inboxIndex`. An unconfirmed deposit can be reclaimed after `expiresAt` with `cancelDeposit` (`DepositCancelled`, and `PaxosDepositCancelled` on the proxy path).
4. **Withdrawals take two transactions.** (a) The validators approve the payout. The `BlockExecutor.executeBlockWithSigs` tx emits `BlockVoteCast` ×2 → `WithdrawalInitiated` (BridgeVault) → `SideEffectExecuted` → `BatchFinalized` → `BlockExecuted` → `BlockExecutedWithSigs`. Deposit confirmations (`DepositConfirmed`) arrive the same way. (b) A separate `executeWithdrawal(withdrawalId)` call pays out. For arcUSDG it burns arcUSDG through the Teller, sends USDG and emits `WithdrawalUnwrapped` (not `WithdrawalExecuted`). `WithdrawalExecuted` is the event for a token with no unwrapper. In the sample, a keeper EOA (`0xc161636bead2ff84d8d875a7d3ab5277a6c47680`) sent the `executeWithdrawal` calls. Join (a) and (b) on `withdrawalId` (topic1).
5. **The validator set is the real admin.** ValidatorConsensus and CheckpointManager hold `DEFAULT_ADMIN_ROLE` on every core contract. A `GovernanceActionExecuted` with 2 of 3 validator votes can upgrade any proxy, rewire the CheckpointManager or grant roles without the timelock. Alert on `GovernanceVoteCast`, `GovernanceActionExecuted`, `Upgraded`, `RoleGranted`.
6. **Escape hatch.** If no batch finalizes for 14 days, anyone can call `activateEmergencySettlement()`. After `EmergencySettlementActivated`, users exit with Merkle proofs (`MarginSettled`, `CollateralSettled`). This event should never fire in normal operation.
7. **Pause events.** `DepositsPausedUpdated` / `WithdrawalsPausedUpdated` on the BridgeVault stop deposits or withdrawals. The two Safes hold `GUARDIAN_ROLE` on the BridgeVault. The ABI does not show which role may call each setter, so treat any caller as significant.
8. **`initiateDeposit` selector `0x43ecb268` exists on two contracts** (BridgeVault and PaxosDepositProxy). Key on `(to, selector)`.
9. **`CheckpointManagerUpdated` topic0 is shared** by BridgeVault and ValidatorConsensus. Key on emitter.
10. **Block numbers on Robinhood Chain advance fast** (genesis contracts at block ~159k; head ~101.8 M on 2026-10-30). The public log RPC caps `eth_getLogs` at 10 M blocks and 10,000 logs per query.
11. **The ABI repo is the source, not explorer source.** No rootchain source is verified on Sourcify or Blockscout. The `arcus-xyz/rootchain-contracts-abis` ABIs match the live bytecode exactly.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_BV_DEPOSIT_INITIATED        = '\x4127e8b2fbc996854e6c019b71c15280dc22073ff1de294067d0ac9bb0090e07'
TOPIC_BV_DEPOSIT_CONFIRMED        = '\x3c5abf8f58d5fe26962fcc25e4603a9487fdee95f79b17d69c6b4f10347e7f33'
TOPIC_BV_DEPOSIT_CANCELLED        = '\x501f866afc9de766bfb8f55d7f749d8ca754b0fef2864ee7b2bffdcd6733f8ea'
TOPIC_BV_WITHDRAWAL_INITIATED     = '\x54449f5f6330b0baa603fd546b6289f616cd725cfa266a09780c7c5fe806589b'
TOPIC_BV_WITHDRAWAL_UNWRAPPED     = '\x8c1b22e85e3e21f4299b06e651504b70a76ebe2c70ffecc1158a3c1bdddc06fa'
TOPIC_BV_WITHDRAWAL_EXECUTED      = '\xd4ae70ceaa0a8901abad43ac0f1d5f1229a537aa6ad0e22e21265e0948668ef1'
TOPIC_BV_RAW_REQUEST_ENQUEUED     = '\x284854e64be3ab0d58fab57f3ada0f124c98e29ceffe796894f9217fa6d3c7b0'
TOPIC_BV_DEPOSIT_CONFIG_UPDATED   = '\xb96afb8549c64ecf6cfc2e46d19f34b056423404c78d11f694a1252d8d677870'
TOPIC_BV_WITHDRAWAL_CONFIG_UPDATED= '\xc3a507db473a3906eb2525804e914c76ec27983c3630afddc285ebd1e785ed83'
TOPIC_BV_DEPOSITS_PAUSED          = '\x9fb50361ff20c95ee94e29cafef7c5a88611fb870013bc74091a2fd5e2cc496d'
TOPIC_BV_WITHDRAWALS_PAUSED       = '\x721196fd60398ccf5df75d7828dd741b90194465ae5dd29f42965050412779e3'
TOPIC_CHECKPOINT_MANAGER_UPDATED  = '\x684ca2057b12fc6cc8862b2516ec7e0a7c470c66e8abfac4364d3bcb329f45df'
TOPIC_CM_REQUEST_ENQUEUED         = '\x16fe649dcfbffb4558cd7d26ca49811aee0b43a841a9b79b317700a1367f4dbc'
TOPIC_CM_BATCH_FINALIZED          = '\xcbfb96c256e48608df21cfaea3461e46689bb491fb9e894fc32c8de2e7e5cdf8'
TOPIC_CM_SIDE_EFFECT_EXECUTED     = '\xd95edd2f13f5d609ea80af610f1376a17a0592f23ffead544302a8988636c521'
TOPIC_CM_EMERGENCY_ACTIVATED      = '\x13b21a05f34e34561fe0d14ec6ce47d2dbb756c68ac06ce537bc9035ae9be13c'
TOPIC_CM_MARGIN_SETTLED           = '\x6667d17650fad7c5aab52fa9f2a44a73492c24bf72dfcce1f7515abd6b4ec230'
TOPIC_CM_COLLATERAL_SETTLED       = '\x2344491a9d495c7ebcef347e110fee8540ea779119deb83441032534a5729c15'
TOPIC_CM_SETTLEMENT_SUMMARY       = '\xf86845e225d059d83768edbfd064aa82f914a7ee9f11c8e3a2fbd72ce965fcc2'
TOPIC_CM_BRIDGE_VAULT_UPDATED     = '\x86cafad4e48ec1edd3bf1bb4b05fbe08a979cc3a0bfceb82a841aa502c5e666b'
TOPIC_VC_BLOCK_VOTE_CAST          = '\x76644ae2a4aff6b7b437ebcf769723cc74db48be900adaaefe688c38a5fb09d8'
TOPIC_VC_BLOCK_EXECUTED           = '\x8574a03e6f3849034e975e95d1a671efded4ea18b39f1d783bfc0bee11acd95f'
TOPIC_VC_GOV_VOTE_CAST            = '\x0142109ca194e36671c745253dd9d1855d60bc168d1c6809eeb0c499bc616f3c'
TOPIC_VC_GOV_ACTION_EXECUTED      = '\x12b5001f75701a111a484218726a1bba0d7b3cd9b7c2f9b6727a1873ea48cfcd'
TOPIC_VC_THRESHOLD_UPDATED        = '\xa21090c78fee7c1d590accd2ebdc6e3265a01cb67bbfff5b5d8927a55f9d46e8'
TOPIC_BE_BLOCK_EXECUTED_WITH_SIGS = '\xc83ae09279ecff656a01fdd2aee1f00beb68461ff8ce9bed10c82d7d2f18af1f'
TOPIC_BE_GOV_EXECUTED_WITH_SIGS   = '\xdabef4ebaef8d898f7ae6de78b6df36b245203c5c86b74c010796d21970a1888'
TOPIC_VB_VERSION_PROPOSED         = '\xb1ebc98c593e8741353f03895b6149b47759f82523880b1defbb65df01630669'
TOPIC_PDP_DEPOSIT_INITIATED       = '\x2b99bfed5ab08e90a6e4f5a50e45ddb72666aa6fc63e8a77efcdbf0466f4fbfc'
TOPIC_PDP_DEPOSIT_CANCELLED       = '\x6166d8c1326378f25d595ca34b79c29c17ba4dbecbb7c9e6c691fa2cf27ddba0'
TOPIC_TL_CALL_SCHEDULED           = '\x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca'
TOPIC_TL_CALL_EXECUTED            = '\xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ROLE_GRANTED                = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED                = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
-- ===== Selectors (chain-agnostic) =====
SEL_INITIATE_DEPOSIT              = '\x43ecb268'
SEL_INITIATE_DEPOSIT_RET_OWNER    = '\x277f8fe0'
SEL_INITIATE_DEPOSIT_RET_SENDER   = '\x37e91fa5'
SEL_INITIATE_DEPOSIT_PERMIT       = '\xf9740b64'
SEL_CANCEL_DEPOSIT                = '\x575d5907'
SEL_ENQUEUE_RAW_REQUEST           = '\x530ef25c'
SEL_EXECUTE_WITHDRAWAL            = '\xd28dfa6e'
SEL_SET_DEPOSITS_PAUSED           = '\x1c481e2d'
SEL_SET_WITHDRAWALS_PAUSED        = '\xb6737162'
SEL_SET_CHECKPOINT_MANAGER        = '\xbc08452b'
SEL_FINALIZE_BATCH                = '\x9c0ba83a'
SEL_ACTIVATE_EMERGENCY_SETTLEMENT = '\x9c6b317d'
SEL_EXECUTE_GOVERNANCE_ACTION     = '\x90459522'
SEL_EXECUTE_BLOCK_WITH_SIGS       = '\x5fc3c09f'
SEL_EXECUTE_BLOCKS_WITH_SIGS      = '\x62c7baca'
SEL_UPGRADE_TO_AND_CALL           = '\x4f1ef286'
-- ===== Addresses (Robinhood Chain 4663) =====
RH_ARCUS_BRIDGE_VAULT             = '\x14b107cf534239c59571b066cb6497a321da897c'
RH_ARCUS_CHECKPOINT_MANAGER       = '\xa3d46d248224070f58c5f750e1f2fca2123df487'
RH_ARCUS_VALIDATOR_CONSENSUS      = '\x9d032106ae6e41f36132fff1e7b0d973b4e55da8'
RH_ARCUS_BLOCK_EXECUTOR           = '\xa49f317086368da903ea40a286ad675664c9e123'
RH_ARCUS_VALIDATOR_BEACON         = '\x9ffc5bce40ca9f0f17e7a01911199d7b1761d8ad'
RH_ARCUS_EMERGENCY_SETTLEMENT     = '\x9edf37f7dbe61ccd75794d5f727bef1bc4d4eabe'
RH_ARCUS_PAXOS_DEPOSIT_PROXY      = '\xd42c46c7bad6a54b38395f846b09981ce75fb8e2'
RH_ARCUS_PAXOS_UNWRAPPER          = '\xa4aca501bd4c11f3c09019e5a3d876e48286edaa'
RH_ARCUS_TIMELOCK                 = '\x0da180b14721ce46a83669b4816cb652caa1001d'
RH_ARCUS_ARCUSDG                  = '\x4fdbdaf4800fc28c22a967d23a343acce34315a4'
RH_ARCUS_PAXOS_TELLER             = '\x323f89aa49ea8626008de5d6941a25bde406b501'
RH_USDG                           = '\x5fc5360d0400a0fd4f2af552add042d716f1d168'
RH_ARCUS_GUARDIAN_SAFE_1          = '\x4f1d777bf36e259f3cb66f2ce969f4c5de05ebe2'
RH_ARCUS_GUARDIAN_SAFE_2          = '\x1d6f8dc865326080a393b0986d9d9af0d7e97316'
```

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the official ABI JSON files. Each ABI was matched against the live implementation bytecode: every selector appears in the dispatcher and every event topic appears as a `PUSH32` (except the OpenZeppelin `RoleAdminChanged`, which the implementations never emit). The BridgeVault, CheckpointManager, ValidatorConsensus, BlockExecutor and PaxosDepositProxy topics were also seen in live `eth_getLogs` on `https://rpc.mainnet.chain.robinhood.com` (counts in §1).
- **Addresses:** taken from the official `deployments.json`, existence-checked with `eth_getCode`, and the BridgeVault deployment receipt was read (`contractAddress` and block match). The BridgeVault address is also the documented withdrawal `verifyingContract`. arcUSDG, Teller and USDG came from `PaxosDepositProxy.wrappedToken() / teller() / underlyingToken()` and `CheckpointManager.marginAsset()`.
- **Proxies:** EIP-1967 implementation, admin and beacon slots read live. Upgrade history from `Upgraded` logs over the full chain range.
- **Roles:** read with `getRoleMembers(bytes32)` for each role constant on each contract. Safe thresholds from `getThreshold()` / `getOwners()`.
- **Chain coverage:** `eth_getCode` on the seven other target chains and Arc returned `0x` for every address.

Authoritative sources:
- [arcus-xyz/rootchain-contracts-abis](https://github.com/arcus-xyz/rootchain-contracts-abis) — ABIs and `deployments.json`.
- [Arcus docs — Architecture](https://docs.arcus.xyz/concepts/exchange-architecture.md) · [Submit withdrawal (verifyingContract table)](https://docs.arcus.xyz/api-reference/exchange/submit-withdrawal.md) · [Multi-Asset Collateral](https://docs.arcus.xyz/concepts/perpetuals/multi-asset-collateral.md) · [Fund a testnet account](https://docs.arcus.xyz/guides/fund-testnet-account.md)
- [Trail of Bits — Arcus Labs Rootchain Security Review (June 2026)](https://github.com/trailofbits/publications/blob/master/reviews/2026-06-arcuslabs-rootchain-securityreview.pdf) · [OpenZeppelin — Arcus Rootchain Contracts Audit](https://www.openzeppelin.com/news/arcus-rootchain-contracts-audit)
- [DefiLlama — Arcus Perps](https://defillama.com/protocol/arcus-perps)
- Explorer: [Robinhood Chain Blockscout — BridgeVault](https://robinhoodchain.blockscout.com/address/0x14b107cf534239c59571b066cb6497a321da897c)
