# Taiko native bridge (Bridge + vaults + SignalService) — Topics, Selectors, Addresses (Ethereum L1 ↔ Taiko Alethia; none of the seven other chains)

**Status:** verified on 2026-09-29 and 2026-10-01 against live Ethereum RPC (code, EIP-1967 slots, owner/quota/resolver views, pinned-window and historical log counts, sample receipts), the canonical `taikoxyz/taiko-mono` protocol sources, the Taiko docs contract-address page, L2BEAT's verified-ABI discovery data, and `eth_getCode` on all eight target chains.
**Scope:** the Taiko Alethia canonical bridge on Ethereum: the **Bridge** (messages and ETH escrow), the **ERC20Vault**, **ERC721Vault** and **ERC1155Vault** (token escrows), the **SignalService** (cross-chain signals and checkpoints), the **QuotaManager**, the address resolvers, and the rollup **Inbox** with its predecessor. Topics and selectors are chain-agnostic; addresses are network-specific. Taiko (chain id 167000) is not one of the eight targets. **Of the eight target chains, only Ethereum carries Taiko contracts** (§4).

Every Taiko transfer is a bridge message. `Bridge.sendMessage` stores a signal in the SignalService and emits `MessageSent` with the full message struct; the vaults call it for tokens. On the destination chain, a relayer or the owner calls `processMessage` with a proof of the source signal; the bridge pays the ETH value and, for a vault message, calls the vault, which releases or mints the tokens. A message that fails becomes retriable; the source owner can **recall** it (refund) once it is proven failed.

Three facts to know before indexing:

1. **The link key is `msgHash`, on chain on both sides.** `MessageSent.msgHash` (source) = `MessageProcessed.msgHash` and `MessageStatusChanged.msgHash` (destination). The vault events carry the same `msgHash` as their first indexed field.
2. **The message struct is in the event data.** `MessageSent` and `MessageProcessed` carry `(id, fee, gasLimit, from, srcChainId, srcOwner, destChainId, destOwner, to, value, data)`. `value` is the ETH amount, `fee` the relayer fee; token amounts are in the vault events.
3. **ETH payouts are rate-limited by the QuotaManager.** The bridge consumes a per-token daily quota (ETH 250 per day per L2BEAT); a processing that exceeds it leaves the message `RETRIABLE`. `QuotaConsumed` fires on each paid ETH message.

---

## 0. Contract families, flow and ids

### 0.1 Contract families

| Contract | Role | Proxy |
|---|---|---|
| **Bridge** | `sendMessage`, `processMessage`, `retryMessage`, `recallMessage`, `failMessage`; ETH escrow; message status. | EIP-1967 (UUPS) |
| **ERC20Vault** | ERC-20 escrow for L1-native tokens; mints and burns bridged copies of Taiko-native tokens. | EIP-1967 (UUPS) |
| **ERC721Vault**, **ERC1155Vault** | NFT escrows (same pattern, array events). | EIP-1967 (UUPS) |
| **SignalService** | Stores sent signals (`SignalSent`) and L2 checkpoints (`CheckpointSaved`) that the destination proves against. | EIP-1967 (UUPS) |
| **QuotaManager** | Daily withdrawal quotas per token for the Bridge and the ERC20Vault. | immutable |
| **Inbox** (current rollup) | Proposals and proofs of Taiko blocks (`Proposed`, `Proved`), bonds, forced inclusions. No user funds except bonds. | EIP-1967 (UUPS) |
| Previous rollup contract | `0x06a9Ab27c7e2255df1815E6CC0168d7755Feb19a`, still deployed. | EIP-1967 (UUPS) |
| DefaultResolver (SharedResolver), RollupAddressResolver, SharedAddressManager | Name → address maps; the bridge and vaults resolve their counterparts through them. | EIP-1967 (UUPS) |
| TaikoDAOController | Owner of the Bridge, vaults, SignalService, Inbox. | EIP-1967 (UUPS) |

### 0.2 The flow

| Leg | Contract and call | Events (same transaction) | Value movement |
|---|---|---|---|
| **ETH / message deposit (source)** | Bridge `sendMessage((...) _message)` (payable) | SignalService `SignalSent`; Bridge `MessageSent` | `msg.value = value + fee` stays in the Bridge |
| **ERC-20 deposit (source)** | ERC20Vault `sendToken((uint64 destChainId, address destOwner, address to, uint64 fee, address token, uint32 gasLimit, uint256 amount) _op)` (payable; `msg.value` = fee) | ERC-20 `Transfer(user → vault)` (L1-native) or burn (bridged token); `SignalSent`; Bridge `MessageSent`; vault `TokenSent` | token to the vault escrow |
| **NFT deposit (source)** | ERC721Vault / ERC1155Vault `sendToken((uint64,address,address,uint64,address,uint32,uint256[],uint256[]) _op)` | NFT transfers; `SignalSent`; `MessageSent`; vault `TokenSent` (arrays) | NFTs to the vault |
| **Checkpoint (status)** | Inbox `prove` | SignalService `CheckpointSaved`; Inbox `Proved` | none |
| **Payout (destination)** | Bridge `processMessage((...) _message, bytes _proof)` (relayer or owner) | QuotaManager `QuotaConsumed` (ETH); vault `Transfer(vault → to)` + `TokenReceived` (tokens); Bridge `MessageStatusChanged` (DONE) + `MessageProcessed` | ETH from the Bridge to `to` (internal); tokens from the vault (or minted) |
| **Retry** | Bridge `retryMessage((...), bool _isLastAttempt)` | `MessageStatusChanged` (DONE or FAILED) | as payout |
| **Recall (refund, source chain)** | Bridge `recallMessage((...), bytes _proof)` after the destination marked it FAILED | vault `TokenReleased` (tokens back to the sender); Bridge `MessageStatusChanged` (RECALLED) | ETH and tokens back to `srcOwner` / `from` |

### 0.3 Ids

| Id | Value |
|---|---|
| Taiko Alethia chain id | 167000 (read live with `eth_chainId` on the Taiko RPC); appears as `srcChainId` / `destChainId` in the message struct |
| Ethereum chain id in the struct | 1 |
| Message status (`uint8` in `MessageStatusChanged`) | 0 NEW, 1 RETRIABLE, 2 DONE, 3 FAILED, 4 RECALLED |
| L2 counterparts (on Taiko) | Bridge `0x1670000000000000000000000000000000000001`, ERC20Vault `0x1670000000000000000000000000000000000002`, ERC721Vault `0x1670000000000000000000000000000000000003`, ERC1155Vault `0x1670000000000000000000000000000000000004`, SignalService `0x1670000000000000000000000000000000000005` (docs) |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Tuple `Message` = `(uint64 id, uint64 fee, uint32 gasLimit, address from, uint64 srcChainId, address srcOwner, uint64 destChainId, address destOwner, address to, uint256 value, bytes data)`.

### 1.1 Bridge (emitter `0xd60247c6848B7Ca29eDdF63AA924E53dB6Ddd8EC`)

| topic0 | Event | Notes |
|---|---|---|
| `0xe33fd33b4f45b95b1c196242240c5b5233129d724b578f95b66ce8d8aae93517` | `MessageSent(bytes32 indexed msgHash, (uint64 id, uint64 fee, uint32 gasLimit, address from, uint64 srcChainId, address srcOwner, uint64 destChainId, address destOwner, address to, uint256 value, bytes data) message)` | **Source leg** of every transfer. |
| `0x8580f507761043ecdd2bdca084d6fb0109150b3d9842d854d34e3dea6d69387d` | `MessageProcessed(bytes32 indexed msgHash, (uint64 id, uint64 fee, uint32 gasLimit, address from, uint64 srcChainId, address srcOwner, uint64 destChainId, address destOwner, address to, uint256 value, bytes data) message, (uint32 gasUsedInFeeCalc, uint32 proofSize, uint32 numCacheOps, bool processedByRelayer) stats)` | **Destination leg** (emitted on every `processMessage`). |
| `0x6c51882bc2ed67617f77a1e9b9a25d2caad8448647ecb093b357a603b2575634` | `MessageStatusChanged(bytes32 indexed msgHash, uint8 status)` | Status only; 4 = RECALLED (refund). |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | Bridge, vaults, SignalService, Inbox, resolver (OpenZeppelin). |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | every proxy of §3. |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` | |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | |

### 1.2 ERC20Vault (emitter `0x996282cA11E5DEb6B5D122CC3B9A1FcAAD4415Ab`)

| topic0 | Event | Side |
|---|---|---|
| `0x256f5c87f6ab8d238ac244067613227eb6e2cd65299121135d4f778e8581e03d` | `TokenSent(bytes32 indexed msgHash, address indexed from, address indexed to, uint64 canonicalChainId, uint64 destChainId, address ctoken, address token, uint256 amount)` | **Source** (tokens) |
| `0x75a051823424fc80e92556c41cb0ad977ae1dcb09c68a9c38acab86b11a69f89` | `TokenReceived(bytes32 indexed msgHash, address indexed from, address indexed to, uint64 srcChainId, address ctoken, address token, uint256 amount)` | **Destination** (tokens) |
| `0x3dea0f5955b148debf6212261e03bd80eaf8534bee43780452d16637dcc22dd5` | `TokenReleased(bytes32 indexed msgHash, address indexed from, address ctoken, address token, uint256 amount)` | **Refund** (recall) |
| `0xb6b427556e8cb0ebf9175da4bc48c64c4f56e44cfaf8c3ab5ebf8e2ea1309079` | `BridgedTokenDeployed(uint256 indexed srcChainId, address indexed ctoken, address indexed btoken, string ctokenSymbol, string ctokenName, uint8 ctokenDecimal)` | A bridged copy of a Taiko-native token was deployed on L1 |
| `0x031d68e1805917560c34a5f55a7dd91bef98f911190ed02cdbb53caedae6c39d` | `BridgedTokenChanged(uint256 indexed srcChainId, address indexed ctoken, address btokenOld, address btokenNew, string ctokenSymbol, string ctokenName, uint8 ctokenDecimal)` | Admin. **High severity** (repoints a bridged token). |

### 1.3 ERC721Vault (`0x0b470dd3A0e1C41228856Fb319649E7c08f419Aa`) and ERC1155Vault (`0xaf145913EA4a56BE22E120ED9C24589659881702`)

| topic0 | Event | Side |
|---|---|---|
| `0xabbf62a1459339f9ac59136d313a5ccd83d2706cc6d4c04d90642520169144dc` | `TokenSent(bytes32 indexed msgHash, address indexed from, address indexed to, uint64 destChainId, address ctoken, address token, uint256[] tokenIds, uint256[] amounts)` | Source |
| `0x895f73e418d1bbbad2a311d085fad00e5d98a960e9f2afa4b942071d39bec43a` | `TokenReceived(bytes32 indexed msgHash, address indexed from, address indexed to, uint64 srcChainId, address ctoken, address token, uint256[] tokenIds, uint256[] amounts)` | Destination |
| `0xe48bef18455e47bca14864ab6e82dffa29df148b051c09de95aec44ecf13598c` | `TokenReleased(bytes32 indexed msgHash, address indexed from, address ctoken, address token, uint256[] tokenIds, uint256[] amounts)` | Refund |
| `0x44977f2d30fe1e3aee2c1476f2f95aaacaf34e44b9359c403da01fcc93fd751b` | `BridgedTokenDeployed(uint64 indexed chainId, address indexed ctoken, address indexed btoken, string ctokenSymbol, string ctokenName)` | Bridged NFT contract deployed |

### 1.4 SignalService, QuotaManager, resolver (status and admin)

| topic0 | Event | Emitter |
|---|---|---|
| `0x0ad2d108660a211f47bf7fb43a0443cae181624995d3d42b88ee6879d200e973` | `SignalSent(address app, bytes32 signal, bytes32 slot, bytes32 value)` | SignalService (pair of every `MessageSent`; status only) |
| `0xf726c53cbb9e62552afc4a8f1bb1d01fa9272e526a7e3a69eba93b778b3f42a6` | `CheckpointSaved(uint48 indexed blockNumber, bytes32 blockHash, bytes32 stateRoot)` | SignalService (L2 state that L2→L1 proofs check) |
| `0x554841bb9cd12af3b98e378802c3fb3e2945d87e70fce55147b2ac358707a0fc` | `QuotaConsumed(address indexed token, uint256 amount, uint256 available)` | QuotaManager (`token` = `0x0` for ETH) |
| `0xc1879fe680552d3452890fc07618b28ab4a629c2abf665db5837c367c6dd5ede` | `QuotaUpdated(address indexed token, uint256 oldQuota, uint256 newQuota)` | QuotaManager (admin) |
| `0x714cf57ffe172b008fcbb807b801535a5edc28672cff603865d82fc2708287ba` | `QuotaPeriodUpdated(uint256 quotaPeriod)` | QuotaManager (admin) |
| `0x3fd0559a7b01eb7106f9d9ce79ec76bb44f608a295878cce50856e54dba83d35` | `AddressRegistered(uint256 indexed chainId, bytes32 indexed name, address newAddress, address oldAddress)` | DefaultResolver (**repoints a bridge counterpart**) |

### 1.5 Inbox (rollup; emitter `0x6f21C543a4aF5189eBdb0723827577e1EF57ef1f`)

| topic0 | Event |
|---|---|
| `0x7c4c4523e17533e451df15762a093e0693a2cd8b279fe54c6cd3777ed5771213` | `Proposed(uint48 indexed id, address indexed proposer, bytes32 parentProposalHash, uint48 endOfSubmissionWindowTimestamp, uint8 basefeeSharingPctg, (bool isForcedInclusion, (bytes32[] blobHashes, uint24 offset, uint48 timestamp) blobSlice)[] sources)` |
| `0xa274dcaff3629ec7d69d144038e97732516ff306fcbf8a2bc9423d106779a2f0` | `Proved(uint48 firstProposalId, uint48 firstNewProposalId, uint48 lastProposalId, address indexed actualProver)` |
| `0xe5e95641fa87bdfef3ce0d39f0c9a37c200f3bf59f53623b3de21e03ed33e3d2` | `BondDeposited(address indexed depositor, address indexed recipient, uint64 amount)` |
| `0x3362c96009316515fccd3dd29c7036c305ad9e892d83dd5681845ac9edb0c9a8` | `BondWithdrawn(address indexed account, uint64 amount)` |
| `0xaa22f5157944b5fa6846460e159d57ea9c3878e71fda274af372fa2ccf285aa0` | `LivenessBondSettled(address indexed payer, address indexed payee, uint64 livenessBond, uint64 credited, uint64 slashed)` |
| `0x18c4fc1e6ac628dbb537b0375bf0efabf1ff2528af1ec22faa74d2da95c29471` | `ForcedInclusionSaved((uint64 feeInGwei, (bytes32[] blobHashes, uint24 offset, uint48 timestamp) blobSlice) forcedInclusion)` |
| `0xe4356761c97932c05c3ee0859fb1a5e4f91f7a1d7a3752c7d5a72d5cc6ecb2d2` | `InboxActivated(bytes32 lastPacayaBlockHash)` |
| `0x4c3db930215a6ed0bab3aa335e88316267503d6581fd0b9c52fc72bcfc3a8e00` | `StateRecovered(uint48 nextProposalId, uint48 lastFinalizedProposalId, bytes32 lastFinalizedBlockHash)` |
| `0x3bbe41cfdd142e0f9b2224dac18c6efd2a6966e35a9ec23ab57ce63a60b33604` | `WithdrawalRequested(address indexed account, uint48 withdrawableAt)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Bridge

| Selector | Signature | Notes |
|---|---|---|
| `0x1bdb0037` | `sendMessage((uint64 id, uint64 fee, uint32 gasLimit, address from, uint64 srcChainId, address srcOwner, uint64 destChainId, address destOwner, address to, uint256 value, bytes data) _message)` | payable. **Source leg.** |
| `0x2035065e` | `processMessage((uint64 id, uint64 fee, uint32 gasLimit, address from, uint64 srcChainId, address srcOwner, uint64 destChainId, address destOwner, address to, uint256 value, bytes data) _message, bytes _proof)` | **Destination leg.** Relayer or `destOwner`. |
| `0x0432873c` | `retryMessage((uint64 id, uint64 fee, uint32 gasLimit, address from, uint64 srcChainId, address srcOwner, uint64 destChainId, address destOwner, address to, uint256 value, bytes data) _message, bool _isLastAttempt)` | |
| `0x9efc7a2e` | `recallMessage((uint64 id, uint64 fee, uint32 gasLimit, address from, uint64 srcChainId, address srcOwner, uint64 destChainId, address destOwner, address to, uint256 value, bytes data) _message, bytes _proof)` | **Refund** on the source chain. |
| `0x913b16cb` | `failMessage((uint64 id, uint64 fee, uint32 gasLimit, address from, uint64 srcChainId, address srcOwner, uint64 destChainId, address destOwner, address to, uint256 value, bytes data) _message)` | Marks a retriable message FAILED (enables recall). |
| `0x8456cb59` | `pause()` | Owner or the immutable pauser. |
| `0x3f4ba83a` | `unpause()` | |
| `0x3659cfe6` | `upgradeTo(address newImplementation)` | UUPS, owner. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | UUPS, owner. |
| `0xc012fa77` | `hashMessage((uint64 id, uint64 fee, uint32 gasLimit, address from, uint64 srcChainId, address srcOwner, uint64 destChainId, address destOwner, address to, uint256 value, bytes data) _message)` | pure: the `msgHash`. |
| `0x3c6cf473` | `messageStatus(bytes32 msgHash)` | view. |
| `0xeefbf17e` | `nextMessageId()` | view (40537 on 2026-09-29). |
| `0x64d391b4` | `quotaManager()` | view (immutable). |
| `0x62d09453` | `signalService()` | view. |
| `0x04f3bcec` | `resolver()` | view. |
| `0x9fd0506d` | `pauser()` | view. |

### 2.2 Vaults, SignalService, QuotaManager, resolver, Inbox

| Selector | Signature | Notes |
|---|---|---|
| `0xb84d9ffe` | `sendToken((uint64 destChainId, address destOwner, address to, uint64 fee, address token, uint32 gasLimit, uint256 amount) _op)` | ERC20Vault, payable. **Source (tokens).** |
| `0x1f59a830` | `sendToken((uint64 destChainId, address destOwner, address to, uint64 fee, address token, uint32 gasLimit, uint256[] tokenIds, uint256[] amounts) _op)` | ERC721Vault / ERC1155Vault, payable. |
| `0x7f07c947` | `onMessageInvocation(bytes _data)` | Vaults; Bridge only (payout). |
| `0x0178733a` | `onMessageRecalled((uint64 id, uint64 fee, uint32 gasLimit, address from, uint64 srcChainId, address srcOwner, uint64 destChainId, address destOwner, address to, uint256 value, bytes data) _message, bytes32 _msgHash)` | Vaults; Bridge only (refund). |
| `0x0ecd8be9` | `changeBridgedToken((uint64 chainId, address addr, uint8 decimals, string symbol, string name) _ctoken, address _btokenNew)` | ERC20Vault owner. **High severity.** |
| `0x66ca2bc0` | `sendSignal(bytes32 _signal)` | SignalService. |
| `0x910af6ed` | `proveSignalReceived(uint64 _chainId, address _app, bytes32 _signal, bytes _proof)` | SignalService. |
| `0xc9a0b8c8` | `saveCheckpoint((uint48 blockNumber, bytes32 blockHash, bytes32 stateRoot) _checkpoint)` | SignalService (from the Inbox). |
| `0xae31c7d8` | `consumeQuota(address _token, uint256 _amount)` | QuotaManager (Bridge, ERC20Vault). |
| `0xeabbe47b` | `updateQuota(address _token, uint104 _quota)` | QuotaManager owner. |
| `0xb91d1651` | `setQuotaPeriod(uint24 _quotaPeriod)` | QuotaManager owner. |
| `0x105d9e6c` | `availableQuota(address _token, uint256 _leap)` | view. |
| `0xb490d87f` | `registerAddress(uint256 _chainId, bytes32 _name, address _newAddress)` | DefaultResolver owner. **High severity.** |
| `0x6c6563f6` | `resolve(uint256 _chainId, bytes32 _name, bool _allowZeroAddress)` | view. |
| `0x9791e644` | `propose(bytes _lookahead, bytes _data)` | Inbox (whitelisted proposer). |
| `0xea191743` | `prove(bytes _data, bytes _proof)` | Inbox. |
| `0xdf596d9e` | `saveForcedInclusion((uint16 blobStartIndex, uint16 numBlobs, uint24 offset) _blobReference)` | Inbox, payable. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | every owned contract. |
| `0x79ba5097` | `acceptOwnership()` | |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All existence-checked with `eth_getCode`; implementations read from the EIP-1967 slot; the admin slot is empty on every proxy (UUPS: upgrades go through the implementation's `upgradeTo*`, gated by `owner()`).

### 3.1 Bridge and escrows

| Role | Address | Implementation | Notes (read live) |
|---|---|---|---|
| **Bridge** (ETH escrow) | `0xd60247c6848B7Ca29eDdF63AA924E53dB6Ddd8EC` | `0x1c94D798CFA08F396E5BA9F81697289c53273381` | `owner()` = TaikoDAOController; `pauser()` = Taiko Multisig; `quotaManager()` = `0xBaCb003f0B13CeAF09Eb9Baf5915A640BD4Bc6cC`; `paused()` = false. |
| **ERC20Vault** | `0x996282cA11E5DEb6B5D122CC3B9A1FcAAD4415Ab` | `0x024253C6FDC27d3161aFd43fb0241411A28dDc3c` | same owner and quota manager; `resolver()` = DefaultResolver. |
| **ERC721Vault** | `0x0b470dd3A0e1C41228856Fb319649E7c08f419Aa` | `0xA4C5c20aB33C96B1c281Dca37D03E23609274C49` | owner TaikoDAOController; not paused. |
| **ERC1155Vault** | `0xaf145913EA4a56BE22E120ED9C24589659881702` | `0x838ed469db456b67EB3b0B74D759Be4DA999b9c8` | owner TaikoDAOController; not paused. |
| **SignalService** | `0x9e0a24964e5397B566c1ed39258e21aB5E35C77C` | `0x1A06832992785766a105838C95c1E13a0045AC85` | owner TaikoDAOController. |
| **QuotaManager** (in use) | `0xBaCb003f0B13CeAF09Eb9Baf5915A640BD4Bc6cC` | immutable (2559 B) | `owner()` = Taiko Multisig. |
| QuotaManager listed on the docs page | `0x91f67118DD47d502B1f0C354D0611997B022f29E` | `0xdb627bfD79e81fE42138Eb875287F94FAd5BBc64` | Not referenced by the live Bridge or ERC20Vault (owner TaikoDAOController). |

### 3.2 Rollup, resolvers, governance

| Role | Address | Notes |
|---|---|---|
| **Inbox** (current rollup) | `0x6f21C543a4aF5189eBdb0723827577e1EF57ef1f` | impl `0x5253D4C91e80b880DdB54B78E74082Abe066F6b9`; owner TaikoDAOController. |
| Previous rollup contract | `0x06a9Ab27c7e2255df1815E6CC0168d7755Feb19a` | impl `0x38Dd73fed93F8051E7A0dDd6FB3b9E7C25668187`; owner TaikoDAOController (read live). Its role as the pre-Inbox rollup is unverified here. |
| DefaultResolver (SharedResolver) | `0x8Efa01564425692d0a0838DC10E300BD310Cb43e` | impl `0xFca4F0Ab7B95EEf2e3A60EF2Bc0c42DdAA62E66D`. |
| RollupAddressResolver | `0x5A982Fb1818c22744f5d7D36D0C4c9f61937b33a` | impl `0xE78659fbF234c84C909Cf317D84edc2f6C0D8413`. |
| SharedAddressManager (old) | `0xEf9EaA1dd30a9AA1df01c36411b5F082aA65fBaa` | impl `0xEC1a9aa1C648F047752fe4eeDb2C21ceab0c6449`. |
| PreconfWhitelist / ProverWhitelist | `0xFD019460881e6EeC632258222393d5821029b2ac` / `0xEa798547d97e345395dA071a0D7ED8144CD612Ae` | rollup access lists. |
| ZkRequiredVerifier | `0x7284aaC05555Ae6559bdAd8B4221eC9584254Eec` | proof policy (immutable). |
| TAIKO token | `0x10dea67478c5F8C5E2D90e5E9B26dBe60c54d800` | impl `0x5C96Ff5B7F61b9E3436Ef04DA1377C8388dfC106`. |
| **TaikoDAOController** | `0x75Ba76403b13b26AD1beC70D6eE937314eeaCD0a` | owner (and upgrader) of the Bridge, vaults, SignalService, Inbox; impl `0x4347df63bdC82b8835fC9FF47bC5a71a12cC0f06`. L2BEAT: driven by the Aragon DAO `0x9CDf589C941ee81D75F34d3755671d614f7cf261` with an optimistic token-voting plugin. |
| Taiko Multisig (Safe) | `0x9CBeE534B5D8a6280e01a14844Ee8aF350399C7F` | Bridge `pauser()`; QuotaManager `owner()`. |

---

## 4. Cross-chain summary

| Chain | ID | Bridge | ERC20Vault | ERC721 / ERC1155 vaults | SignalService | Inbox | QuotaManager |
|---|---|---|---|---|---|---|---|
| **Ethereum** | 1 | ✅ `0xd60247c6848B7Ca29eDdF63AA924E53dB6Ddd8EC` | ✅ `0x996282cA11E5DEb6B5D122CC3B9A1FcAAD4415Ab` | ✅ / ✅ | ✅ | ✅ `0x6f21C543a4aF5189eBdb0723827577e1EF57ef1f` | ✅ |
| Base | 8453 | — | — | — | — | — | — |
| Arbitrum One | 42161 | — | — | — | — | — | — |
| Optimism | 10 | — | — | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — | — | — |
| BNB Smart Chain | 56 | — | — | — | — | — | — |
| Avalanche C-Chain | 43114 | — | — | — | — | — | — |
| Robinhood Chain | 4663 | — | — | — | — | — | — |

"—" means `eth_getCode` returned `0x` with nonce 0 at the Ethereum addresses of the Bridge, ERC20Vault, both NFT vaults, SignalService, Inbox, QuotaManager and the previous rollup contract (checked 2026-09-29 to 2026-10-01). The Taiko docs list no L1 contract outside Ethereum, and the six transfer topic0s (`MessageSent`, `MessageProcessed`, `MessageStatusChanged`, `TokenSent`, `TokenReceived`, `TokenReleased`) had 0 logs on the other seven chains in the pinned window. The counterparty, Taiko Alethia (167000), is outside the eight.

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade authority |
|---|---|---|---|
| Bridge, ERC20Vault, ERC721Vault, ERC1155Vault, SignalService, Inbox, resolvers, TAIKO, TaikoDAOController | EIP-1967 **UUPS** (170-byte `ERC1967Proxy`) | impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` set; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` empty; `upgradeTo` / `upgradeToAndCall` in the implementation | `owner()` = TaikoDAOController `0x75Ba76403b13b26AD1beC70D6eE937314eeaCD0a` (read live). L2BEAT lists 13 upgrades of the Bridge and 9 of the ERC20Vault. |
| QuotaManager (in use), ZkRequiredVerifier | immutable | no impl slot | QuotaManager quotas: `owner()` = Taiko Multisig. |

Watch `Upgraded(address)` on every proxy and `OwnershipTransferStarted` on the DAOController-owned contracts.

---

## 6. Detection invariants & gotchas

1. **Join by `msgHash`.** Source `MessageSent.msgHash` → destination `MessageProcessed.msgHash` / `MessageStatusChanged.msgHash`; the vault's `TokenSent` / `TokenReceived` / `TokenReleased` carry the same hash. `Bridge.hashMessage(message)` recomputes it.
2. **A token deposit is one transfer, three events.** `sendToken` emits `SignalSent`, `MessageSent` (`from` = the vault, `value` = 0 for ERC-20) and `TokenSent`. Use `TokenSent.amount`; do not add the `MessageSent` again.
3. **ETH value = `message.value`.** `msg.value` of `sendMessage` also includes `message.fee` (relayer fee). The ETH payout is an internal transfer from the Bridge to `message.to`; read the amount from the struct in `MessageProcessed`.
4. **Status matters.** A `MessageProcessed` can end in RETRIABLE (status 1): no payout yet. Payment happened when `MessageStatusChanged` reports 2 (DONE). Status 4 (RECALLED) is a refund on the source chain, with `TokenReleased` for tokens.
5. **Quota can delay ETH and token exits.** `QuotaConsumed(token, amount, available)` shows the remaining daily quota; an exhausted quota leaves messages RETRIABLE. A `QuotaUpdated` that raises a quota is an admin trigger.
6. **`processMessage` is called by relayers.** `tx.from` (and sometimes `tx.to`, a relayer contract) is not the user; use `message.to` / `TokenReceived.to`. One sample payout went through the relayer contract `0xa7A51036802788925f77F1222C6e4cB27f70b29A`.
7. **Two QuotaManagers exist.** The live Bridge and ERC20Vault use `0xBaCb003f0B13CeAF09Eb9Baf5915A640BD4Bc6cC`; the docs page still lists `0x91f67118DD47d502B1f0C354D0611997B022f29E`. Monitor the one the bridge reads (`quotaManager()`).
8. **Bridged copies on L1.** Taiko-native tokens arrive on L1 as bridged tokens minted by the vault (`BridgedTokenDeployed`); sending them back burns them (Transfer to `0x0`), not an escrow lock.
9. **Admin triggers:** `Upgraded`, `OwnershipTransferStarted`, `Paused` (Bridge pauser is a multisig), `BridgedTokenChanged`, resolver `AddressRegistered`, `QuotaUpdated`, `QuotaPeriodUpdated`.
10. **Large-transfer trigger:** `message.value` in `MessageSent` / `MessageProcessed` (ETH), `TokenSent.amount` / `TokenReceived.amount` per token; for a drain, the ETH balance of the Bridge and the token balances of the ERC20Vault.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Bridge =====
TOPIC_TAIKO_MESSAGE_SENT             = '\xe33fd33b4f45b95b1c196242240c5b5233129d724b578f95b66ce8d8aae93517'
TOPIC_TAIKO_MESSAGE_PROCESSED        = '\x8580f507761043ecdd2bdca084d6fb0109150b3d9842d854d34e3dea6d69387d'
TOPIC_TAIKO_MESSAGE_STATUS_CHANGED   = '\x6c51882bc2ed67617f77a1e9b9a25d2caad8448647ecb093b357a603b2575634'
-- ===== ERC20Vault =====
TOPIC_TAIKO_ERC20_TOKEN_SENT         = '\x256f5c87f6ab8d238ac244067613227eb6e2cd65299121135d4f778e8581e03d'
TOPIC_TAIKO_ERC20_TOKEN_RECEIVED     = '\x75a051823424fc80e92556c41cb0ad977ae1dcb09c68a9c38acab86b11a69f89'
TOPIC_TAIKO_ERC20_TOKEN_RELEASED     = '\x3dea0f5955b148debf6212261e03bd80eaf8534bee43780452d16637dcc22dd5'
TOPIC_TAIKO_BRIDGED_TOKEN_CHANGED    = '\x031d68e1805917560c34a5f55a7dd91bef98f911190ed02cdbb53caedae6c39d'
-- ===== NFT vaults =====
TOPIC_TAIKO_NFT_TOKEN_SENT           = '\xabbf62a1459339f9ac59136d313a5ccd83d2706cc6d4c04d90642520169144dc'
TOPIC_TAIKO_NFT_TOKEN_RECEIVED       = '\x895f73e418d1bbbad2a311d085fad00e5d98a960e9f2afa4b942071d39bec43a'
TOPIC_TAIKO_NFT_TOKEN_RELEASED       = '\xe48bef18455e47bca14864ab6e82dffa29df148b051c09de95aec44ecf13598c'
-- ===== SignalService / quota / resolver / rollup =====
TOPIC_TAIKO_SIGNAL_SENT              = '\x0ad2d108660a211f47bf7fb43a0443cae181624995d3d42b88ee6879d200e973'
TOPIC_TAIKO_CHECKPOINT_SAVED         = '\xf726c53cbb9e62552afc4a8f1bb1d01fa9272e526a7e3a69eba93b778b3f42a6'
TOPIC_TAIKO_QUOTA_CONSUMED           = '\x554841bb9cd12af3b98e378802c3fb3e2945d87e70fce55147b2ac358707a0fc'
TOPIC_TAIKO_QUOTA_UPDATED            = '\xc1879fe680552d3452890fc07618b28ab4a629c2abf665db5837c367c6dd5ede'
TOPIC_TAIKO_ADDRESS_REGISTERED       = '\x3fd0559a7b01eb7106f9d9ce79ec76bb44f608a295878cce50856e54dba83d35'
TOPIC_TAIKO_PROPOSED                 = '\x7c4c4523e17533e451df15762a093e0693a2cd8b279fe54c6cd3777ed5771213'
TOPIC_TAIKO_PROVED                   = '\xa274dcaff3629ec7d69d144038e97732516ff306fcbf8a2bc9423d106779a2f0'
TOPIC_OZ_PAUSED                      = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UPGRADED                       = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_OWNERSHIP_TRANSFER_STARTED     = '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'

-- ===== Selectors =====
SEL_TAIKO_SEND_MESSAGE               = '\x1bdb0037'
SEL_TAIKO_PROCESS_MESSAGE            = '\x2035065e'
SEL_TAIKO_RETRY_MESSAGE              = '\x0432873c'
SEL_TAIKO_RECALL_MESSAGE             = '\x9efc7a2e'
SEL_TAIKO_FAIL_MESSAGE               = '\x913b16cb'
SEL_TAIKO_ERC20_SEND_TOKEN           = '\xb84d9ffe'
SEL_TAIKO_NFT_SEND_TOKEN             = '\x1f59a830'
SEL_TAIKO_CHANGE_BRIDGED_TOKEN       = '\x0ecd8be9'
SEL_TAIKO_REGISTER_ADDRESS           = '\xb490d87f'
SEL_UPGRADE_TO_AND_CALL              = '\x4f1ef286'

-- ===== Ethereum (chain ID 1) =====
ETH_TAIKO_BRIDGE                     = '\xd60247c6848b7ca29eddf63aa924e53db6ddd8ec'
ETH_TAIKO_ERC20_VAULT                = '\x996282ca11e5deb6b5d122cc3b9a1fcaad4415ab'
ETH_TAIKO_ERC721_VAULT               = '\x0b470dd3a0e1c41228856fb319649e7c08f419aa'
ETH_TAIKO_ERC1155_VAULT              = '\xaf145913ea4a56be22e120ed9c24589659881702'
ETH_TAIKO_SIGNAL_SERVICE             = '\x9e0a24964e5397b566c1ed39258e21ab5e35c77c'
ETH_TAIKO_QUOTA_MANAGER              = '\xbacb003f0b13ceaf09eb9baf5915a640bd4bc6cc'
ETH_TAIKO_QUOTA_MANAGER_DOCS         = '\x91f67118dd47d502b1f0c354d0611997b022f29e'
ETH_TAIKO_INBOX                      = '\x6f21c543a4af5189ebdb0723827577e1ef57ef1f'
ETH_TAIKO_PREVIOUS_ROLLUP            = '\x06a9ab27c7e2255df1815e6cc0168d7755feb19a'
ETH_TAIKO_DEFAULT_RESOLVER           = '\x8efa01564425692d0a0838dc10e300bd310cb43e'
ETH_TAIKO_DAO_CONTROLLER             = '\x75ba76403b13b26ad1bec70d6ee937314eeacd0a'
ETH_TAIKO_MULTISIG                   = '\x9cbee534b5d8a6280e01a14844ee8af350399c7f'
ETH_TAIKO_TOKEN                      = '\x10dea67478c5f8c5e2d90e5e9b26dbe60c54d800'
-- counterparts on Taiko (167000; not a target chain)
TAIKO_L2_BRIDGE                      = '\x1670000000000000000000000000000000000001'
TAIKO_L2_ERC20_VAULT                 = '\x1670000000000000000000000000000000000002'
-- Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain: no Taiko contracts
```

---

## 8. Verification & sources

How the constants were verified:

- **Topics and selectors:** recomputed as `keccak256(signature)` from the deployed ABIs of the Bridge, ERC20Vault, SignalService, QuotaManager, DefaultResolver and Inbox implementations (verified sources as captured in L2BEAT's discovery data), and from `taiko-mono` `packages/protocol/contracts/shared/bridge/{Bridge,IBridge}.sol`, `shared/vault/{BaseNFTVault,ERC20Vault,ERC721Vault,ERC1155Vault}.sol`, `shared/signal/ISignalService.sol`. The NFT-vault topics were confirmed from live logs (Ethereum blocks 25700000–26075812: ERC721Vault `TokenSent` 1, `BridgedTokenDeployed` 1, `TokenReceived` 1; ERC1155Vault `TokenSent` 1).
- **Sample transactions read:** TAIKO deposit `0x97277f12f000125f8143c530c279ab33e4f631f327a1c3c5f7060006ad43b8b2` (ERC20Vault `sendToken`, `msg.value` = fee; TAIKO `Transfer` user → vault, `MessageSent`, `SignalSent`, `TokenSent`, same `msgHash`); ETH payout `0x0d6f90ff0adb30b73b40a5b46b3db182aceaf236587060868755260a9c4599a2` (through a relayer contract: `QuotaConsumed` for token `0x0`, `MessageStatusChanged`, `MessageProcessed`); token payout `0x1f00f15ba25f2823a03337b79d9d694915837e8c98156a9cee38bb3f41722070` (`processMessage` by the recipient: CRV `Transfer` vault → user, `TokenReceived`, `MessageStatusChanged`, `MessageProcessed`).
- **Addresses:** from the Taiko docs page, existence-checked with `eth_getCode`; implementations from the EIP-1967 slot; `owner()`, `paused()` of every listed contract; Bridge `quotaManager()`, `signalService()`, `resolver()`, `pauser()`, `nextMessageId()`; ERC20Vault `quotaManager()`, `resolver()`; both QuotaManagers' `owner()`.
- **Chain coverage:** `eth_getCode` = `0x` (nonce 0) on Base, Arbitrum, Optimism, Polygon, BNB, Avalanche and Robinhood Chain for the addresses listed under §4.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Ethereum blocks 26072222–26075812):** Bridge `MessageSent` 1, `MessageProcessed` 7, `MessageStatusChanged` 7; ERC20Vault `TokenSent` 1, `TokenReceived` 0, `TokenReleased` 0; NFT vault `TokenSent` / `TokenReceived` 0; SignalService `SignalSent` 1, `CheckpointSaved` 20; QuotaManager `QuotaConsumed` 7; Inbox `Proposed` 113, `Proved` 20. In the prior Ethereum blocks 26040000–26072221 the ERC20Vault emitted 2 `TokenReceived`. The other seven chains: no Taiko emitter exists.

Sources opened:
- [taikoxyz/taiko-mono](https://github.com/taikoxyz/taiko-mono) (`packages/protocol/contracts/`)
- [Taiko docs — contract addresses](https://docs.taiko.xyz/network/contract-addresses)
- [L2BEAT discovery data for Taiko](https://github.com/l2beat/l2beat/blob/main/packages/config/src/projects/taiko/discovered.json)
- Taiko JSON-RPC `eth_chainId` (public endpoint) for 167000
