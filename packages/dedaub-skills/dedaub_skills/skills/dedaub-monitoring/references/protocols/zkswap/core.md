# ZKSwap V1 and V2 — Topics, Selectors, Addresses (Ethereum only)

**Status:** verified on 2026-09-29 against live Ethereum RPC, the verified explorer source of both ZkSync implementations (`0x2f70f6d864f8f597a0ef57addf24323dfab5797f` for V1, `0xf2c351f22b148a9ff583a0f81701471a74e7338e` for V2) and of `ZkSyncCommitBlock`, `UpgradeGatekeeper` and `Governance`, the `l2labs/zkswap-contracts` repository, and the L2BEAT project pages. All eight target chains were probed.
**Scope:** ZKSwap 1.0 and ZKSwap 2.0 by L2 Labs: two zkSync 1.x-based ZK rollups with an AMM on L2. Each version is one set of contracts on **Ethereum (chain ID 1)**: the main `ZkSync` proxy (the escrow of all funds), Governance, Verifier, the pair-token manager, the UpgradeGatekeeper, and the `ZkSyncCommitBlock` and `ZkSyncExit` contracts that the main contract reaches by `delegatecall`. **No ZKSwap contract exists on Base, Arbitrum, Optimism, Polygon, BNB, Avalanche or Robinhood Chain.** Topics and selectors are chain-agnostic; addresses are Ethereum only.

**End of life.** ZKSwap halted V1 from 2021-08-26 and shut it down on 2021-09-25, with a migration to V2 (Chain Bulletin, 2021-08-26). L2BEAT archives both versions ("This project is archived and no longer maintained") and points users to ZkSpace (version 3). On chain, the V2 operator last committed and verified blocks in September 2024 (block 20,798,429), V1 entered exodus mode at block 22,881,853 (July 2025), and the V2 proxy still held 33.556 ETH on 2026-09-29 (explorer balance). See §8, items 7 to 9.

A ZK rollup bridge has no per-transfer message to another chain: a deposit moves funds into the Ethereum escrow and credits an L2 account; an exit moves them out after the operator proves an L2 block. Every contract is an upgradeable zkSync-style `Proxy` (3,426 B) that stores its implementation in the EIP-1967 slot; the master of each proxy is the version's **UpgradeGatekeeper**, which enforces an **8-day notice period** (L2BEAT). The gatekeepers' masters are EOAs.

---

## 0. Contract families and the flow

| Contract | V1 | V2 | Role |
|----------|----|----|------|
| **ZkSync (main, escrow)** | `0x8ECa806Aecc86CE90Da803b080Ca4E3A9b8097ad` | `0x6dE5bDC580f55Bc9dAcaFCB67b91674040A247e3` | Proxy. Holds all ETH and ERC-20 deposits; emits every user event. |
| ZkSync implementation | `0x2f70f6d864f8f597a0ef57addf24323dfab5797f` | `0xf2c351f22b148a9ff583a0f81701471a74e7338e` | Logic (verified `ZkSync`). |
| ZkSyncCommitBlock | `0x2c543ebd91dab7be40edb671d48cedf35a75e157` | `0xe26ebb18144cd2d8dcb14ce87fdcfbeb81bacad4` | Operator functions (`commitBlock`, `verifyBlocks`, `checkWithdrawals`, `triggerExodusIfNeeded`), reached by `delegatecall` from the fallback. |
| ZkSyncExit | `0x8a1dbf1c32a4f5afbd70d778f25fbeed7cc881e5` | `0xc0221a4dfb792aa71ce84c2687b1d2b1e7d3eea0` | Exodus exits (`exit`, `lpExit`), by `delegatecall`. |
| Governance (proxy) | `0x02ecef526f806f06357659ffd14834fe82ef4b04` | `0x86e527bc3c43e6ba3eff3a8cad54a7ed09cd8e8b` | Token id registry, validators, governor. |
| Verifier (proxy) | `0x27c229937745d697d28fc7853d1bfea7331edf56` | `0x42f15efe22993c88441ef3467f2e6fa8ffa9adef` | PLONK verifier. |
| VerifierExit | `0x961369d347ef7a6896bdd39cbe2b89e3911f521f` | `0xb56878d21f6b101f48bb55f1aa9d3f624f04e513` | Exit-proof verifier. |
| Pair-token manager (proxy) | `0x661121ae41ede3f6fecded922c59acc19a3ea9b3` | `0xd2cbdcd7c6b3152bdff6549c208052e4dbcd575d` | Mints and burns L1 pair (LP) tokens. |
| **UpgradeGatekeeper** | `0x714b2d10210f2a3a7aa614f949259c87613689ab` | `0x0dcce462ddea102d3ecf84a991d3ecfc251e02c7` | Master of the proxies; 8-day notice upgrades. |
| Gatekeeper master (EOA) | `0x7D1a14eeD7af8e26f24bf08BA6eD7A339AbcF037` | `0x9D7397204F32e0Ee919Ea3475630cdf131086255` | Can start and finish upgrades. |

| Step | Function | Event(s) | Value movement in the same transaction |
|------|----------|----------|----------------------------------------|
| Deposit (source leg) | `depositETH`, `depositERC20` | `NewPriorityRequest` (`opType` 1) then `OnchainDeposit` | ETH in `msg.value`, or ERC-20 `Transfer` user to the ZkSync proxy. A pair-token deposit burns the pair token instead. |
| Inclusion on L2 | `commitBlock` (operator) | `BlockCommit`, `DepositCommit` (status) | None. |
| Exit, operator-pushed (destination leg) | `checkWithdrawals` then `completeWithdrawals` | `PendingWithdrawalsAdd`, then **`PendingWithdrawalsComplete` only** | ERC-20 `Transfer` from the proxy to each owner, or ETH sent by call; one transaction pays many owners. |
| Exit, user-pulled (destination leg) | `withdrawETH`, `withdrawERC20` (V2 also `...WithAddress`) | `OnchainWithdrawal` | ERC-20 `Transfer` from the proxy, or ETH by call. |
| Forced exit | `fullExit` | `NewPriorityRequest` (`opType` 6), later `FullExitCommit` | Paid through the withdrawal queue. |
| Exodus | `triggerExodusIfNeeded`, then `exit` / `lpExit` with a Merkle proof; `cancelOutstandingDepositsForExodusMode` | `ExodusMode`, then `OnchainWithdrawal` when the user pulls | The proven balance becomes withdrawable. |

**Link key.** None crosses chains: L2 has no EVM logs here. On L1, a deposit is identified by `NewPriorityRequest.serialId` (the priority-queue id, emitted in the same transaction as `OnchainDeposit`); the L2 account is `owner`. Exits carry no deposit reference.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Emitter: the ZkSync proxy of each version, unless the notes say otherwise. `opType` is the `Operations.OpType` enum (`uint8`): 0 Noop, 1 Deposit, 2 TransferToNew, 3 PartialExit, 4 CloseAccount, 5 Transfer, 6 FullExit, 7 ChangePubKey, 8 CreatePair, 9 AddLiquidity, 10 RemoveLiquidity, 11 Swap.

### 1.1 Deposits, exits and exodus

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xb6866b029f3aa29cd9e2bff8159a8ccaa4389f7a087c710968e0b200c0c73b08` | `OnchainDeposit(address indexed sender, uint16 indexed tokenId, uint128 amount, address indexed owner)` | **Source leg (L1 to L2 deposit).** `sender` paid; `owner` is the L2 account. Same topic in V1 and V2. Verified live. |
| `0xd0943372c08b438a88d4b39d77216901079eda9ca59d45349841c099083b6830` | `NewPriorityRequest(address sender, uint64 serialId, uint8 opType, bytes pubData, uint256 expirationBlock)` | **V1.** Fires with every deposit (`opType` 1) and full exit (`opType` 6). `serialId` is the priority-queue id. Verified live. |
| `0x61a320c641d3946236359022627bfeb930f7a628b0d863a325a1d4983f2e4238` | `NewPriorityRequest(address sender, uint64 serialId, uint8 opType, bytes pubData, bytes userData, uint256 expirationBlock)` | **V2** (extra `userData`). Verified live. |
| `0x3ac065a1e69cd78fa12ba7269660a2894da2ec7f1ff1135ed5ca04de4b4e389e` | `OnchainWithdrawal(address indexed owner, uint16 indexed tokenId, uint128 amount)` | **Destination leg, user-pulled only**: `withdrawETH`, `withdrawERC20` and the V2 `...WithAddress` variants. **Not emitted by `completeWithdrawals`.** Verified live. |
| `0x9b5478c99b5ca41beec4f6f6084126d6f9e26382d017b4bb67c37c9e8453a313` | `PendingWithdrawalsComplete(uint32 queueStartIndex, uint32 queueEndIndex)` | **Destination leg, operator-pushed**: `completeWithdrawals` pays the queue (ERC-20 `Transfer` from the proxy, or ETH) and emits only this event. In the verified source; verified live. |
| `0xc4faeb4e73f28a46e4a5fa2db5b89c39698816488534ab7f0717c46f0852c366` | `PendingWithdrawalsAdd(uint32 queueStartIndex, uint32 queueEndIndex)` | Status: verified withdrawals enter the queue. Verified live. |
| `0xc71028c67eb0ef128ea270a59a674629e767d51c1af44ed6753fd2fad2c7b677` | `ExodusMode()` | **The rollup is frozen**; users exit with Merkle proofs (`exit`, `lpExit`). V1 emitted it at block 22,881,853. Verified live. |

### 1.2 Rollup status events (no value moves)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x81a92942d0f9c33b897a438384c9c3d88be397776138efa3ba1a4fc8b6268424` | `BlockCommit(uint32 indexed blockNumber)` | Status. Verified live. |
| `0x0cdbd8bd7813095001c5fe7917bd69d834dc01db7c1dfcf52ca135bd20384413` | `BlockVerification(uint32 indexed blockNumber)` | Status. |
| `0x0020b79376a95828218ec245f1ef8471e6be4610392401a9d295ba435a245647` | `MultiblockVerification(uint32 indexed blockNumberFrom, uint32 indexed blockNumberTo)` | Status. Verified live. |
| `0x6f3a8259cce1ea2680115053d21c971aa1764295a45850f520525f2bfdf3c9d3` | `BlocksRevert(uint32 indexed totalBlocksVerified, uint32 indexed totalBlocksCommitted)` | Status: unverified blocks were reverted. |
| `0xc4e73a5b67a0594d06ea2b5c311c2aa44aa340dd4dd9ec5a1a718dc391b64470` | `DepositCommit(uint32 indexed zkSyncBlockId, uint32 indexed accountId, address owner, uint16 indexed tokenId, uint128 amount)` | Status: a deposit was included in an L2 block. Verified live. |
| `0x66fc63d751ecbefca61d4e2e7c534e4f29c61aed8ece23ed635277a7ea6f9bc4` | `FullExitCommit(uint32 indexed zkSyncBlockId, uint32 indexed accountId, address owner, uint16 indexed tokenId, uint128 amount)` | Status: a full exit was included. |
| `0x9ea39b45a0cc96a2139996ec8dd30326216111249750781e563ae27c31ae8766` | `FactAuth(address indexed sender, uint32 nonce, bytes fact)` | Status: L2 public-key authorization. |
| `0x2c87b60b0d81063e9b0ba8089ea00f8b35b25ff04a89aa904d257b675d610b99` | `OnchainCreatePair(uint16 indexed tokenAId, uint16 indexed tokenBId, uint16 indexed pairId, address pair)` | A pair (LP) token was created on L1. Verified live. |
| `0x20c5fd01ebdff8049629c84c58f7230432fc2bfcb1c6393ef01c4d53fd3756a9` | `CreatePairCommit(uint32 indexed zkSyncBlockId, uint32 indexed accountId, uint16 tokenAId, uint16 tokenBId, uint16 indexed tokenPairId, address pair)` | Status. Verified live. |

### 1.3 Governance and UpgradeGatekeeper

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xfe74dea79bde70d1990ddb655bac45735b14f495ddc508cfab80b7729aa9d668` | `NewToken(address indexed token, uint16 indexed tokenId)` | Governance (and PairTokenManager): token id registry. Verified live. |
| `0x5425363a03f182281120f5919107c49c7a1a623acc1cbc6df468b6f0c11fcf8c` | `NewGovernor(address newGovernor)` | Governance. **Admin event.** |
| `0x27a62b6770204c21f1cea70018df609d5c9261d4d3ec9d34fe5e3fcbf1320c6e` | `NewTokenLister(address newTokenLister)` | V2 Governance. Verified live. |
| `0x065b77b53864e46fda3d8986acb51696223d6dde7ced42441eb150bae6d48136` | `ValidatorStatusUpdate(address indexed validatorAddress, bool isActive)` | Governance: operator allowlist. **Admin event.** Verified live. |
| `0xecfd8b4d8bfc0590001d923f6db32faaad4c3d96097734fe5950f43980dabfc4` | `NewUpgradable(uint256 indexed versionId, address indexed upgradeable)` | UpgradeGatekeeper. Verified live. |
| `0xabce748366d7d01473824f1bee75dc176759f56b88f00253e4a10d7528ca806f` | `NoticePeriodStart(uint256 indexed versionId, address[] newTargets, uint256 noticePeriod)` | UpgradeGatekeeper: **an upgrade is announced** (8-day notice). Admin event. |
| `0x55cd34119fd31f1a8cc60aad1098023b450274eef2294e3e1b6dd452d58ce6fd` | `UpgradeCancel(uint256 indexed versionId)` | UpgradeGatekeeper. |
| `0xd2b7d4a4a2b38481e36a9b8198af8b427261011fd199b7a1b7cb8f437aa25acd` | `PreparationStart(uint256 indexed versionId)` | UpgradeGatekeeper. |
| `0x48bc8be43b04d57da4f0d65c05db98278a94d9e90b7348d5d2705cc78c9a9d2e` | `UpgradeComplete(uint256 indexed versionId, address[] newTargets)` | UpgradeGatekeeper: **the proxies now point to `newTargets`**. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 User functions (ZkSync and ZkSyncExit)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2d2da806` | `depositETH(address _franklinAddr)` | `payable`. ETH in `msg.value`. Emits `NewPriorityRequest` and `OnchainDeposit`. |
| `0xe17376b5` | `depositERC20(address _token, uint104 _amount, address _franklinAddr)` | ERC-20 `Transfer` user to proxy (or a pair-token burn). Emits `NewPriorityRequest` and `OnchainDeposit`. |
| `0x000000e2` | `fullExit(uint32 _accountId, address _token)` | Forced exit request on L1 (priority queue, `opType` 6). |
| `0xc488a09c` | `withdrawETH(uint128 _amount)` | User pulls ETH from `balancesToWithdraw`. Emits `OnchainWithdrawal`. |
| `0xc94c5b7c` | `withdrawERC20(address _token, uint128 _amount)` | User pulls an ERC-20. Emits `OnchainWithdrawal`. |
| `0xa5dcdf71` | `withdrawETHWithAddress(uint128 _amount, address _to)` | V2 only. Emits `OnchainWithdrawal`. |
| `0xf3a4d4af` | `withdrawERC20WithAddress(address _token, uint128 _amount, address _to)` | V2 only. Emits `OnchainWithdrawal`. |
| `0x6a387fc9` | `completeWithdrawals(uint32 _n)` | Anyone; pays up to `_n` queued withdrawals. Emits `PendingWithdrawalsComplete` only. |
| `0x9a83400d` | `withdrawERC20Guarded(address _token, address _to, uint128 _amount, uint128 _maxAmount)` | Internal-only (`msg.sender == this`); the ERC-20 leg of `completeWithdrawals`. |
| `0xd6973fc6` | `exit(uint32 _accountId, uint16 _tokenId, uint128 _amount, uint256[] _proof)` | Exodus mode: proof-based exit (in `ZkSyncExit`, reached by `delegatecall`). |
| `0x8420b370` | `lpExit(bytes32 _rootHash, uint32[] _accountIds, address[] _addresses, uint16[] _tokenIds, uint128[] _amounts, uint256[] _proof)` | Exodus mode: LP-position exit. |
| `0x2f804bd2` | `cancelOutstandingDepositsForExodusMode(uint64 _n)` | Exodus mode: refunds deposits that were never included. |
| `0xc9c65396` | `createPair(address _tokenA, address _tokenB)` | Creates an L1 pair token. Emits `OnchainCreatePair`. |
| `0x8d43428a` | `createETHPair(address _tokenERC20)` | The same with ETH. |

### 2.2 Operator, views and upgrade functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4e913cd9` | `commitBlock(uint32 _blockNumber, uint32 _feeAccount, bytes32[] _newBlockInfo, bytes _publicData, bytes _ethWitness, uint32[] _ethWitnessSizes)` | Operator. Emits `BlockCommit`. |
| `0x241735bb` | `commitMultiBlock(uint32[] _blockInfo, bytes32[] _newRootAndCommitment, bytes[] _publicDatas, uint32[] _ethWitnessSizes)` | Operator (V2 CommitBlock). |
| `0x6898e6fc` | `verifyBlocks(uint32 _blockNumberFrom, uint32 _blockNumberTo, uint256[] _recursiveInput, uint256[] _proof, uint256[] _subProofLimbs)` | Operator. Emits `MultiblockVerification`. |
| `0xae917732` | `checkWithdrawals(uint32 _blockNumberFrom, uint32 _blockNumberTo, bytes[] _withdrawalsData)` | Operator: moves verified withdrawals to the queue. Emits `PendingWithdrawalsAdd`. |
| `0xa6289e5a` | `revertBlocks(uint32 _maxBlocksToRevert)` | Operator. Emits `BlocksRevert`. |
| `0x6b27a044` | `triggerExodusIfNeeded()` | Anyone: enters exodus mode when a priority request expired. Emits `ExodusMode`. |
| `0x264c0912` | `exodusMode()` | View: `bool`. V1 = true, V2 = false on 2026-09-29. |
| `0x2d24006c` | `totalBlocksVerified()` | View: `uint32`. |
| `0x3c06e514` | `numberOfPendingWithdrawals()` | View: `uint32` (V1 = 6, V2 = 0 on 2026-09-29). |
| `0xfa6b53c3` | `getBalanceToWithdraw(address _address, uint16 _tokenId)` | View: a user's claimable balance. |
| `0x6fc49140` | `upgradeTarget(address newTarget, bytes newTargetUpgradeParameters)` | Proxy: master (the UpgradeGatekeeper) only. |
| `0xf00e6a2a` | `getTarget()` | Proxy view: the implementation. |
| `0x5a99719e` | `getMaster()` | Proxy and gatekeeper view: the master. |
| `0x31a94da3` | `startUpgrade(address[] newTargets)` | UpgradeGatekeeper, master only. Emits `NoticePeriodStart`. |
| `0x253b153b` | `finishUpgrade(bytes[] targetsUpgradeParameters)` | UpgradeGatekeeper, master only, after the notice period. Emits `UpgradeComplete`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified with `eth_getCode` on 2026-09-29; implementations read from the EIP-1967 slot; `getMaster()` and `getTarget()` read live. Deployment addresses come from the `Addresses(address governance, address zksync, address verifier, address pair, address gatekeeper)` and `AddressesOther(address commitblock, address exit, address verifierexit)` events of the deployment transactions (V1 block 11,841,962; V2 block 12,810,001).

| Role | Address | One-liner |
|------|---------|-----------|
| **ZKSwap V1 ZkSync (proxy, escrow)** | `0x8ECa806Aecc86CE90Da803b080Ca4E3A9b8097ad` | Implementation `0x2f70f6d864f8f597a0ef57addf24323dfab5797f` (14,757 B). `exodusMode()` = true; `totalBlocksVerified()` = 130,744; `numberOfPendingWithdrawals()` = 6. |
| **ZKSwap V2 ZkSync (proxy, escrow)** | `0x6dE5bDC580f55Bc9dAcaFCB67b91674040A247e3` | Implementation `0xf2c351f22b148a9ff583a0f81701471a74e7338e` (16,877 B). `exodusMode()` = false; `totalBlocksVerified()` = 32,259; `numberOfPendingWithdrawals()` = 0. |
| V1 Governance (proxy) | `0x02ecef526f806f06357659ffd14834fe82ef4b04` | Implementation `0x9d3fdf9b4782753d12f6262bf22b6322608962b8`. |
| V2 Governance (proxy) | `0x86e527bc3c43e6ba3eff3a8cad54a7ed09cd8e8b` | Implementation `0x95269f9e76540459c797089034dc74b48df780a2`. |
| V1 Verifier (proxy) | `0x27c229937745d697d28fc7853d1bfea7331edf56` | Implementation `0x165dfa76dfd3f6ad6ad614ae4566c2e9262e532f`. |
| V2 Verifier (proxy) | `0x42f15efe22993c88441ef3467f2e6fa8ffa9adef` | Implementation `0x94b9401945a9bc06ce5b69e6db3c6b671aabc829`. |
| V1 pair-token manager (proxy) | `0x661121ae41ede3f6fecded922c59acc19a3ea9b3` | Implementation `0x65fab217f1948af2d7a8eeb11ff111b0993c5df8`. |
| V2 pair-token manager (proxy) | `0xd2cbdcd7c6b3152bdff6549c208052e4dbcd575d` | Implementation `0xb2639ba16c7a5b0c55ca22d77cda3d7ed88a5c89`. |
| V1 UpgradeGatekeeper | `0x714b2d10210f2a3a7aa614f949259c87613689ab` | 4,452 B, not a proxy. `mainContract()` = the V1 proxy; `getMaster()` = `0x7D1a14eeD7af8e26f24bf08BA6eD7A339AbcF037`. |
| V2 UpgradeGatekeeper | `0x0dcce462ddea102d3ecf84a991d3ecfc251e02c7` | 4,452 B, not a proxy. `mainContract()` = the V2 proxy; `getMaster()` = `0x9D7397204F32e0Ee919Ea3475630cdf131086255`. |
| V1 ZkSyncCommitBlock | `0x2c543ebd91dab7be40edb671d48cedf35a75e157` | `zkSyncCommitBlockAddress()` of the V1 proxy. |
| V2 ZkSyncCommitBlock | `0xe26ebb18144cd2d8dcb14ce87fdcfbeb81bacad4` | `zkSyncCommitBlockAddress()` of the V2 proxy. |
| V1 ZkSyncExit | `0x8a1dbf1c32a4f5afbd70d778f25fbeed7cc881e5` | `zkSyncExitAddress()` of the V1 proxy. |
| V2 ZkSyncExit | `0xc0221a4dfb792aa71ce84c2687b1d2b1e7d3eea0` | `zkSyncExitAddress()` of the V2 proxy. Not verified on Blockscout; source in `l2labs/zkswap-contracts`. |
| V1 gatekeeper master (EOA) | `0x7D1a14eeD7af8e26f24bf08BA6eD7A339AbcF037` | Nonce 149. Deployed V1. |
| V2 gatekeeper master (EOA) | `0x9D7397204F32e0Ee919Ea3475630cdf131086255` | Nonce 60. Deployed V2. |
| July 2025 actor contract | `0x728001a80a3657e886810daab9e796fefd66b6c7` | 6,576 B, called by the EOA `0x0a652decf9caca373e2b50607ecb7b069d71a7ba` (nonce 74). See §8, item 8. |

## 4. The other seven target chains — no deployment

`eth_getCode` returns `0x` at all 14 addresses checked (the two ZkSync proxies, Governance, Verifier, pair-token managers, gatekeepers, the actor contract and the EOAs) on Base (8453), Arbitrum One (42161), Optimism (10), Polygon PoS (137), BNB Smart Chain (56), Avalanche C-Chain (43114) and Robinhood Chain (4663). ZKSwap is an Ethereum rollup, and L2BEAT lists only Ethereum contracts.

---

## 5. Cross-chain summary

| Chain | ID | ZKSwap V1 | ZKSwap V2 |
|-------|----|-----------|-----------|
| Ethereum | 1 | `0x8ECa806Aecc86CE90Da803b080Ca4E3A9b8097ad` | `0x6dE5bDC580f55Bc9dAcaFCB67b91674040A247e3` |
| Base | 8453 | — (no code) | — (no code) |
| Arbitrum One | 42161 | — | — |
| Optimism | 10 | — | — |
| Polygon PoS | 137 | — | — |
| BNB Smart Chain | 56 | — | — |
| Avalanche C-Chain | 43114 | — | — |
| Robinhood Chain | 4663 | — | — |

---

## 6. Proxies (old and new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| ZkSync, Governance, Verifier, pair-token manager (both versions) | zkSync 1.x `Proxy` (`Ownable` + `UpgradeableMaster`) | 3,426 B proxy; implementation in the EIP-1967 slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; `getTarget()` returns the same address. | `upgradeTarget` only from the master = the UpgradeGatekeeper. |
| UpgradeGatekeeper | Immutable | 4,452 B, no implementation slot. | Its master EOA: `startUpgrade` (`NoticePeriodStart`, 8 days) then `finishUpgrade` (`UpgradeComplete`). |
| ZkSyncCommitBlock, ZkSyncExit | Plain contracts | Their addresses are stored in the ZkSync proxy (`zkSyncCommitBlockAddress()`, `zkSyncExitAddress()`). | Changed only by a ZkSync upgrade. |

There is no `Upgraded(address)` event: watch `NoticePeriodStart` and `UpgradeComplete` on the gatekeepers.

---

## 7. Topic sharing with zkSync 1.x

ZKSwap reuses the zkSync 1.x event set, so `OnchainDeposit` `0xb6866b029f3aa29cd9e2bff8159a8ccaa4389f7a087c710968e0b200c0c73b08`, `OnchainWithdrawal` `0x3ac065a1e69cd78fa12ba7269660a2894da2ec7f1ff1135ed5ca04de4b4e389e`, `BlockCommit` and the other status topics can also come from zkSync Lite and other forks. Always filter by the two ZkSync proxy addresses.

## 8. Detection invariants and gotchas

1. **The escrow is the ZkSync proxy.** All deposited ETH and ERC-20 sit at `0x8ECa806Aecc86CE90Da803b080Ca4E3A9b8097ad` (V1) and `0x6dE5bDC580f55Bc9dAcaFCB67b91674040A247e3` (V2). The other contracts hold nothing.
2. **ETH moves without a token log.** `depositETH` (`0x2d2da806`) carries the ETH in `msg.value`; ETH exits are value transfers from the proxy. Read native transfers for the amounts.
3. **`OnchainWithdrawal` misses most exits.** `completeWithdrawals` (`0x6a387fc9`) pays the whole queue with ERC-20 `Transfer` logs (and ETH calls) and emits only `PendingWithdrawalsComplete`: the measured V1 transaction `0x3f143042bdb3dbe75eeafaf2103169581cb41d86cfa1a9d71846b418b23f5d9b` paid eight owners with one event. `OnchainWithdrawal` comes only from user-called `withdrawETH` / `withdrawERC20` (and, in exodus, after `exit`). Key exits on the proxy's outgoing transfers.
4. **Two `NewPriorityRequest` topics.** V1 `0xd0943372c08b438a88d4b39d77216901079eda9ca59d45349841c099083b6830` and V2 `0x61a320c641d3946236359022627bfeb930f7a628b0d863a325a1d4983f2e4238` (V2 adds `bytes userData`). `serialId` is the only on-chain id of a deposit.
5. **Token ids, not addresses.** Events carry `uint16 tokenId`. Map ids with Governance `NewToken(token, tokenId)` (ETH is id 0); pair (LP) tokens have their own ids from the pair-token manager (`PAIR_TOKEN_START_ID` and above).
6. **`depositERC20` takes `uint104` amounts** and measures the balance change, so fee-on-transfer tokens credit less than `_amount`. Use the event `amount`.
7. **V2 still holds ETH and is not in exodus.** On 2026-09-29 the V2 proxy held 33.556 ETH (explorer) with `exodusMode()` = false and no pending withdrawals; the last `BlockCommit` and `MultiblockVerification` are at blocks 20,797,833 and 20,798,429 (2024-09-21). Deposits after that date are not included by any operator.
8. **July 2025 activity by one actor.** The contract `0x728001a80a3657e886810daab9e796fefd66b6c7`, called by the EOA `0x0a652decf9caca373e2b50607ecb7b069d71a7ba`: block 22,864,541, a pair-token deposit on V1 (`OnchainDeposit`, token id 130, 1,000,000,000,000,000,000 base units burned); block 22,864,704, an `OnchainWithdrawal` on V2 that minted 99,999,999,999,999,991,611,392 base units of pair token `0x33e67e07a36bf828e02b0bbd0699e87ea1654f03` (token id 16393) to the contract; block 22,864,829, a deposit (burn) of 89,999,999,999,999,995,805,696 base units back into V2; block 22,881,853, the V1 `ExodusMode()` event. The purpose was not established. Watch both proxies for `OnchainWithdrawal`, `ExodusMode` and pair-token mints.
9. **V1 exodus exits continue.** V1 is in exodus mode (`exodusMode()` = true). Block 25,016,806 (2026-05-03): `exit` by `0x383b019141b243d3ab83e793cfa8d53854cb2d84`, then `withdrawERC20` (block 25,016,813) paid 3,195,652,235,651,790 base units of token `0x0316eb71485b0ab14103307bf65a021042c6d380` with `OnchainWithdrawal`.
10. **Upgrades need 8 days of notice.** Watch `NoticePeriodStart` and `UpgradeComplete` on both gatekeepers; the masters are single EOAs.
11. **Ethereum only.** No ZKSwap contract on any other target chain; L2 transfers, swaps and liquidity changes leave no EVM logs.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (V1 and V2 unless marked) =====
TOPIC_ONCHAIN_DEPOSIT                 = '\xb6866b029f3aa29cd9e2bff8159a8ccaa4389f7a087c710968e0b200c0c73b08'
TOPIC_ONCHAIN_WITHDRAWAL              = '\x3ac065a1e69cd78fa12ba7269660a2894da2ec7f1ff1135ed5ca04de4b4e389e'
TOPIC_PENDING_WITHDRAWALS_COMPLETE    = '\x9b5478c99b5ca41beec4f6f6084126d6f9e26382d017b4bb67c37c9e8453a313'
TOPIC_PENDING_WITHDRAWALS_ADD         = '\xc4faeb4e73f28a46e4a5fa2db5b89c39698816488534ab7f0717c46f0852c366'
TOPIC_NEW_PRIORITY_REQUEST_V1         = '\xd0943372c08b438a88d4b39d77216901079eda9ca59d45349841c099083b6830'
TOPIC_NEW_PRIORITY_REQUEST_V2         = '\x61a320c641d3946236359022627bfeb930f7a628b0d863a325a1d4983f2e4238'
TOPIC_EXODUS_MODE                     = '\xc71028c67eb0ef128ea270a59a674629e767d51c1af44ed6753fd2fad2c7b677'
TOPIC_BLOCK_COMMIT                    = '\x81a92942d0f9c33b897a438384c9c3d88be397776138efa3ba1a4fc8b6268424'
TOPIC_MULTIBLOCK_VERIFICATION         = '\x0020b79376a95828218ec245f1ef8471e6be4610392401a9d295ba435a245647'
TOPIC_DEPOSIT_COMMIT                  = '\xc4e73a5b67a0594d06ea2b5c311c2aa44aa340dd4dd9ec5a1a718dc391b64470'
TOPIC_ONCHAIN_CREATE_PAIR             = '\x2c87b60b0d81063e9b0ba8089ea00f8b35b25ff04a89aa904d257b675d610b99'
TOPIC_NEW_TOKEN                       = '\xfe74dea79bde70d1990ddb655bac45735b14f495ddc508cfab80b7729aa9d668'
TOPIC_NOTICE_PERIOD_START             = '\xabce748366d7d01473824f1bee75dc176759f56b88f00253e4a10d7528ca806f'
TOPIC_UPGRADE_COMPLETE                = '\x48bc8be43b04d57da4f0d65c05db98278a94d9e90b7348d5d2705cc78c9a9d2e'

-- ===== Selectors =====
SEL_DEPOSIT_ETH                       = '\x2d2da806'
SEL_DEPOSIT_ERC20                     = '\xe17376b5'
SEL_FULL_EXIT                         = '\x000000e2'
SEL_WITHDRAW_ETH                      = '\xc488a09c'
SEL_WITHDRAW_ERC20                    = '\xc94c5b7c'
SEL_COMPLETE_WITHDRAWALS              = '\x6a387fc9'
SEL_EXIT                              = '\xd6973fc6'
SEL_TRIGGER_EXODUS_IF_NEEDED          = '\x6b27a044'

-- ===== Ethereum addresses =====
ETH_ZKSWAP_V1                         = '\x8eca806aecc86ce90da803b080ca4e3a9b8097ad'
ETH_ZKSWAP_V1_IMPL                    = '\x2f70f6d864f8f597a0ef57addf24323dfab5797f'
ETH_ZKSWAP_V1_GATEKEEPER              = '\x714b2d10210f2a3a7aa614f949259c87613689ab'
ETH_ZKSWAP_V1_GOVERNANCE              = '\x02ecef526f806f06357659ffd14834fe82ef4b04'
ETH_ZKSWAP_V1_COMMIT_BLOCK            = '\x2c543ebd91dab7be40edb671d48cedf35a75e157'
ETH_ZKSWAP_V1_PAIR_MANAGER            = '\x661121ae41ede3f6fecded922c59acc19a3ea9b3'
ETH_ZKSWAP_V2                         = '\x6de5bdc580f55bc9dacafcb67b91674040a247e3'
ETH_ZKSWAP_V2_IMPL                    = '\xf2c351f22b148a9ff583a0f81701471a74e7338e'
ETH_ZKSWAP_V2_GATEKEEPER              = '\x0dcce462ddea102d3ecf84a991d3ecfc251e02c7'
ETH_ZKSWAP_V2_GOVERNANCE              = '\x86e527bc3c43e6ba3eff3a8cad54a7ed09cd8e8b'
ETH_ZKSWAP_V2_COMMIT_BLOCK            = '\xe26ebb18144cd2d8dcb14ce87fdcfbeb81bacad4'
ETH_ZKSWAP_V2_EXIT                    = '\xc0221a4dfb792aa71ce84c2687b1d2b1e7d3eea0'
ETH_ZKSWAP_V2_PAIR_MANAGER            = '\xd2cbdcd7c6b3152bdff6549c208052e4dbcd575d'
ETH_ZKSWAP_V1_MASTER_EOA              = '\x7d1a14eed7af8e26f24bf08ba6ed7a339abcf037'
ETH_ZKSWAP_V2_MASTER_EOA              = '\x9d7397204f32e0ee919ea3475630cdf131086255'
ETH_ZKSWAP_2025_ACTOR_CONTRACT        = '\x728001a80a3657e886810daab9e796fefd66b6c7'
-- Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain: no ZKSwap contract
```

---

## 10. Verification and sources

How the constants were verified (2026-09-29):

- **Topic0 and selectors:** recomputed as `keccak256(canonical signature)` from the verified `Events.sol`, `ZkSync.sol` and `Governance.sol` of both implementations (`Operations.OpType` encoded as `uint8`), the verified `ZkSyncCommitBlock` (V2) and `UpgradeGatekeeper` (V2), the verified V2 Governance implementation `0x95269f9e76540459c797089034dc74b48df780a2` (`NewTokenLister`), and `ZkSyncExit.sol` of `l2labs/zkswap-contracts`. `PendingWithdrawalsComplete` is in the verified source of both versions.
- **Live logs (positive controls):** V1 proxy, blocks 12,200,000 to 12,204,999 (April 2021): 484 `BlockCommit`, 89 `PendingWithdrawalsAdd`, 85 V1 `NewPriorityRequest`, 84 `OnchainDeposit`, 84 `DepositCommit`, 24 `MultiblockVerification`, 22 `PendingWithdrawalsComplete`, 1 `NewToken`, 1 `OnchainCreatePair`, 1 `CreatePairCommit`. V2 proxy, blocks 13,000,000 to 13,004,999 (August 2021): 156 `BlockCommit`, 31 `MultiblockVerification`, 12 `PendingWithdrawalsAdd`, 7 `PendingWithdrawalsComplete`, 4 V2 `NewPriorityRequest`, 4 `OnchainDeposit`, 4 `DepositCommit`. The deployment transactions emitted `NewUpgradable`, `NewToken`, `ValidatorStatusUpdate` and `NewTokenLister`.
- **Sample transactions read with `eth_getTransactionReceipt`:** `0x0097c7116e2eb1c44db3a426299dae8139ee8201dacb0db8a16ed01ecec8cd2f` (V1 `depositERC20`: token `Transfer` user to proxy, `NewPriorityRequest`, `OnchainDeposit`); `0x3f143042bdb3dbe75eeafaf2103169581cb41d86cfa1a9d71846b418b23f5d9b` (V1 `completeWithdrawals`: eight ERC-20 transfers out of the proxy, one `PendingWithdrawalsComplete`, no `OnchainWithdrawal`); `0x32a48adb056c44ac8308bd21307949d51737a28c7710b27fbe52c6116e258c51` (V2 `completeWithdrawals`, 2024); `0xde5183c88f9ac6ec1f0349feab2ea9757fc53f2ff1468dd18ce46f97c10c54ac`, `0xae0f91a2dbf568d1da657cb714527a9895f1999e6df70decede5ff26ac6fc51b`, `0xf801de3ff21d01eac1559d10cbf99b0c85d80d926cb626349d972f7fab6393b5`, `0xfdb93e00f3b1d24303db7f43eaa5ef50d3fde957ddeec7c0feb8c5497ba11182` (the July 2025 sequence of §8, item 8); `0x59686407fdb75c433401bc0a7cd6c84c805e6b1ac37f542ca82a744d11ade7a5` and `0x60a60e6a91ae745fb125ff1f49dab22d80152cf60865150264ae7e55dde951ff` (V1 exodus `exit` and `withdrawERC20`, 2026); `0x88d1ab73c6f4b447a4411eaf4bbc1f4d8dbd3409fdcf4baef5209b665aa545df` and `0xed7b7dea431c4cb5a56ce3b5a3146bdf5735dfa49bf974765b2441597fa90955` (deployments).
- **Pinned 12-hour window 2026-09-28 00:00 to 12:00 UTC:** `OnchainDeposit` and `OnchainWithdrawal` from any emitter: Ethereum 0, Base 0, Arbitrum 0, Optimism 0, Polygon 0, BNB 0, Avalanche 0, Robinhood 0. All logs of the V1 and V2 proxies in the Ethereum window (blocks 26,072,222 to 26,075,812): 0 and 0.
- **Addresses and state:** deployment `Addresses` / `AddressesOther` events, EIP-1967 slot reads, `getTarget()`, `getMaster()`, `mainContract()`, `zkSyncCommitBlockAddress()`, `zkSyncExitAddress()`, `exodusMode()`, `totalBlocksCommitted()`, `totalBlocksVerified()` and `numberOfPendingWithdrawals()` read live; the ETH balance and latest activity from the Blockscout address pages. L2BEAT lists the same V1 proxy, implementation, gatekeeper and CommitBlock, and the same V2 proxy, CommitBlock, Exit, Governance, Verifier, VerifierExit and gatekeeper.
- **Not verified:** the purpose of the July 2025 actor; any Robinhood or other-chain plan of the team (none found).

Sources:
- [l2labs/zkswap-contracts](https://github.com/l2labs/zkswap-contracts) (`contracts/ZkSync.sol`, `contracts/Events.sol`, `contracts/ZkSyncExit.sol`, `contracts/DeployFactory.sol`, `README.md`) · [l2labs/zkswap-contracts-v2](https://github.com/l2labs/zkswap-contracts-v2)
- [L2BEAT: ZKSwap 1.0](https://l2beat.com/scaling/projects/zkswap) · [L2BEAT: ZKSwap 2.0](https://l2beat.com/scaling/projects/zkswap2)
- [Chain Bulletin, 2021-08-26: "ZKSwap to shut down V1 mainnet and migrate assets to V2"](https://chainbulletin.com/zkswap-to-shut-down-v1-mainnet-and-migrate-assets-to-v2)
- Explorers: [Blockscout V1 proxy](https://eth.blockscout.com/address/0x8ECa806Aecc86CE90Da803b080Ca4E3A9b8097ad) · [Blockscout V2 proxy](https://eth.blockscout.com/address/0x6dE5bDC580f55Bc9dAcaFCB67b91674040A247e3) · [Blockscout V1 implementation](https://eth.blockscout.com/address/0x2f70f6d864f8f597a0ef57addf24323dfab5797f) · [Blockscout V2 implementation](https://eth.blockscout.com/address/0xf2c351f22b148a9ff583a0f81701471a74e7338e)
