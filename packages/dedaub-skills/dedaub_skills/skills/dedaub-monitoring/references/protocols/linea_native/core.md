# Linea native bridge (LineaRollup message service + TokenBridge) — Topics, Selectors, Addresses (Ethereum L1 ↔ Linea; none of the seven other chains)

**Status:** verified on 2026-09-29 against live Ethereum RPC (code, EIP-1967 slots, role and view reads, pinned-window log counts, sample receipts, historical log ranges), the canonical `Consensys/linea-monorepo` contracts, the Linea docs address page, L2BEAT's verified-ABI discovery data, and `eth_getCode` on all eight target chains.
**Scope:** the Linea canonical bridge on Ethereum: the **LineaRollup** (L1 message service, ETH escrow, rollup state), the **TokenBridge** (ERC-20 escrow and bridged-token minter), the retired **L1USDCBridge**, the **YieldManager** that stakes part of the ETH escrow, and their governance. Topics and selectors are chain-agnostic; addresses are network-specific. Linea (chain id 59144) is not one of the eight targets. **Of the eight target chains, only Ethereum carries Linea bridge contracts** (§4).

Linea moves ETH and data through its message service, which lives inside the LineaRollup contract. A sender calls `sendMessage` with `msg.value = value + fee`; the rollup keeps the ETH and emits `MessageSent`. An L2→L1 message is claimed on Ethereum with a Merkle proof (`claimMessageWithProof`), which pays the ETH and emits `MessageClaimed`. The TokenBridge rides on the message service: a token deposit locks (or burns) the token, then sends a message to the L2 TokenBridge; a token withdrawal is a claimed message that calls `completeBridging` and releases (or mints) the token.

Three facts to know before indexing:

1. **The link key is `_messageHash`, on chain on both sides.** `MessageSent._messageHash` (L1) equals the hash that the L2 message service claims, and an L2 `MessageSent._messageHash` equals the L1 `MessageClaimed._messageHash`. Claiming is manual (the user or a "postman" pays the gas); there is no automatic delivery event.
2. **`MessageClaimed` carries no amount and no recipient.** The ETH amount of an L1 payout is only in the internal value transfer from the rollup to `_to`, or in the decoded claim calldata. Token payouts are also visible in `BridgingFinalizedV2` and the ERC-20 `Transfer`.
3. **Not every `MessageSent` is a deposit.** `reportNativeYield` emits a synthetic `MessageSent` whose `_from` is the YieldManager and whose `_value` is staking yield minted on L2; no ETH enters in that transaction. And a token deposit emits `MessageSent` **and** `BridgingInitiatedV2`: count it once.

---

## 0. Contract families, flow and ids

### 0.1 Contract families

| Contract | Role | Proxy |
|---|---|---|
| **LineaRollup** | L1 message service (`sendMessage`, `claimMessage*`), ETH escrow, blob submission and finalization, forced transactions, 24-hour withdrawal rate limit (10,000 ETH read live). | EIP-1967 transparent |
| **TokenBridge (L1)** | Escrow for L1-native ERC-20s; mints and burns `BridgedToken` beacon proxies for L2-native tokens. | EIP-1967 transparent |
| **YieldManager** + **LidoStVaultYieldProvider** | Moves part of the rollup's ETH into a Lido V3 staking vault and back; can pay a withdrawal in stETH when the rollup lacks ETH. | YieldManager: EIP-1967 transparent; provider: immutable (delegate-called) |
| **L1USDCBridge** (retired) | The old USDC bridge. Paused; its locked USDC was burned by Circle in 2025 (`AllLockedUSDCBurnt`). USDC now uses Circle CCTP V2 (Linea is CCTP domain 11; see the `cctp` reference). | EIP-1967 transparent |
| UpgradeableBeacon + BridgedToken | Beacon of the L1 bridged-token proxies (tokens native to Linea). | beacon |
| CallForwardingProxy, AddressFilter | Public call forwarder to the rollup; blocklist for the forced-transaction path. | immutable |
| PlonkVerifierFull (×2) | Proof verifiers. No value flow. | immutable |
| ProxyAdmin ×2, Timelock, Security Council | Upgrade and role authority (§5). | — |

### 0.2 The flow

| Leg | Contract and call | Events (same transaction) | Value movement |
|---|---|---|---|
| **ETH / message deposit (source)** | rollup `sendMessage(address _to, uint256 _fee, bytes _calldata)` (payable) | `RollingHashUpdated` then `MessageSent` | `msg.value = _value + _fee` stays in the rollup. |
| **Token deposit (source)** | TokenBridge `bridgeToken(address _token, uint256 _amount, address _recipient)` (payable; `msg.value` = message fee) or `bridgeTokenWithPermit(...)` | ERC-20 `Transfer(sender → TokenBridge)` (L1-native token) or `Transfer(sender → 0x0)` (bridged token burn); rollup `RollingHashUpdated` + `MessageSent` (`_from` = TokenBridge, `_to` = L2 TokenBridge); TokenBridge `BridgingInitiatedV2` | token to escrow, or burn |
| **Finalization (status)** | rollup `finalizeBlocks` (operator) | `DataFinalizedV3`, `FinalizedStateUpdated`, `L2MerkleRootAdded`, `L2MessagingBlockAnchored` | none |
| **ETH / message payout (destination)** | rollup `claimMessageWithProof((...))` (anyone; the fee goes to `feeRecipient` or the caller) | `MessageClaimed` | ETH from the rollup to `_to` (internal value transfer), counted against the rate limit |
| **Token payout (destination)** | the same claim, which calls TokenBridge `completeBridging(...)` | ERC-20 `Transfer(TokenBridge → recipient)` (or mint from `0x0`), `BridgingFinalizedV2`, then rollup `MessageClaimed` | release from escrow or mint |
| **Payout in stETH** | rollup `claimMessageWithProofAndWithdrawLST((...), address _yieldProvider)` (only when the rollup balance is below the value; caller must be `to`) | YieldManager `LSTMinted`, rollup `MessageClaimed` | stETH minted to the recipient instead of ETH |
| **Yield report (not a deposit)** | rollup `reportNativeYield(uint256 _amount, address _l2YieldRecipient)` (YieldManager only) | `RollingHashUpdated`, `MessageSent` (`_from` = YieldManager, `_fee` = 0) | none on L1 |

There is no refund or cancel path for a Linea message: an unclaimed message stays claimable. Pausing (`Paused`, by type) and the rate limit are the only stops.

### 0.3 Ids

| Id | Value |
|---|---|
| Linea chain id | 59144 (read live: `eth_chainId` on the Linea RPC, and `TokenBridge.targetChainId()`) |
| Ethereum chain id in the TokenBridge | 1 (`sourceChainId()`) |
| L2 counterparts (on Linea) | L2MessageService `0x508Ca82Df566dCD1B0DE8296e70a96332cD644ec`, L2 TokenBridge `0x353012dc4a9A6cF55c941bADC267f82004A8ceB9` (= `TokenBridge.remoteSender()`, read live) |
| Pause types (`uint8`) | 1 GENERAL, 2 L1_L2, 3 L2_L1, 4 BLOB_SUBMISSION (deprecated), 5 CALLDATA_SUBMISSION (deprecated), 6 FINALIZATION, 7 INITIATE_TOKEN_BRIDGING, 8 COMPLETE_TOKEN_BRIDGING, 9 NATIVE_YIELD_STAKING, 10 NATIVE_YIELD_UNSTAKING, 11 NATIVE_YIELD_PERMISSIONLESS_ACTIONS, 12 NATIVE_YIELD_REPORTING, 13 STATE_DATA_SUBMISSION |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 LineaRollup — message service (emitter `0xd19d4B5d358258f05D7B411E21A1460D11B0876F`)

| topic0 | Event | Notes |
|---|---|---|
| `0xe856c2b8bd4eb0027ce32eeaf595c21b0b6b4644b326e5b7bd80a1cf8db72e6c` | `MessageSent(address indexed _from, address indexed _to, uint256 _fee, uint256 _value, uint256 _nonce, bytes _calldata, bytes32 indexed _messageHash)` | **Source leg.** `_from` is the direct caller (often a router or the TokenBridge). |
| `0xea3b023b4c8680d4b4824f0143132c95476359a2bb70a81d6c5a36f6918f6339` | `RollingHashUpdated(uint256 indexed messageNumber, bytes32 indexed rollingHash, bytes32 indexed messageHash)` | Pair of every `MessageSent` (status only); `messageNumber` = `_nonce`. |
| `0xa4c827e719e911e8f19393ccdb85b5102f08f0910604d340ba38390b7ff2ab0e` | `MessageClaimed(bytes32 indexed _messageHash)` | **Destination leg** of an L2→L1 message. No amount. |
| `0x810484e22f73d8f099aaee1edb851ec6be6d84d43045d0a7803e5f7b3612edce` | `L2L1MessageHashAddedToInbox(bytes32 indexed messageHash)` | Historical (2023 finalization path; 318 logs in Ethereum blocks 18500000–18510000). |

### 1.2 LineaRollup — rollup state, forced transactions, rate limit (status and admin)

| topic0 | Event |
|---|---|
| `0x300e6f978eee6a4b0bba78dd8400dc64fd5652dbfc868a2258e16d0977be222b` | `L2MerkleRootAdded(bytes32 indexed l2MerkleRoot, uint256 indexed treeDepth)` |
| `0x3c116827db9db3a30c1a25db8b0ee4bab9d2b223560209cfd839601b621c726d` | `L2MessagingBlockAnchored(uint256 indexed l2Block)` |
| `0xa0262dc79e4ccb71ceac8574ae906311ae338aa4a2044fd4ec4b99fad5ab60cb` | `DataFinalizedV3(uint256 indexed startBlockNumber, uint256 indexed endBlockNumber, bytes32 indexed shnarf, bytes32 parentStateRootHash, bytes32 finalStateRootHash)` |
| `0x55f4c645c36aa5cd3f443d6be44d7a7a5df9d2100d7139dfc69d4289ee072319` | `DataSubmittedV3(bytes32 parentShnarf, bytes32 indexed shnarf, bytes32 finalStateRootHash)` |
| `0x32e016ccc5c33419c35caa94023fdeb75143da613fb2ac738ab736404c09fc5d` | `FinalizedStateUpdated(uint256 indexed blockNumber, uint256 timestamp, uint256 messageNumber, uint256 forcedTransactionNumber)` |
| `0x8fbc8fbd65675eb32c567d4a559963c7d002c2be67b5b266fb13d85b4375fce5` | `ForcedTransactionAdded(uint256 indexed forcedTransactionNumber, address indexed from, uint256 blockNumberDeadline, bytes32 forcedTransactionRollingHash, bytes rlpEncodedSignedTransaction)` |
| `0xbc3dc0cb5c15c51c81316450d44048838bb478b9809447d01c766a06f3e9f2c8` | `LimitAmountChanged(address indexed amountChangeBy, uint256 amount, bool amountUsedLoweredToLimit, bool usedAmountResetToZero)` |
| `0xba88c025b0cbb77022c0c487beef24f759f1e4be2f51a205bc427cee19c2eaa6` | `AmountUsedInPeriodReset(address indexed resettingAddress)` |
| `0x8f805c372b66240792580418b7328c0c554ae235f0932475c51b026887fe26a9` | `RateLimitInitialized(uint256 periodInSeconds, uint256 limitInWei, uint256 currentPeriodEnd)` |
| `0x4a29db3fc6b42bda201e4b4d69ce8d575eeeba5f153509c0d0a342af0f1bd021` | `VerifierAddressChanged(address indexed verifierAddress, uint256 indexed proofType, address indexed verifierSetBy, address oldVerifierAddress)` |
| `0xeb44f28f73dc4d72ac2ee43ebf59a1e0c84c11c4d614746c0dc99d9071abd8f9` | `YieldManagerChanged(address oldYieldManagerAddress, address newYieldManagerAddress)` |
| `0xe455499c2acd509bdadebaf5a8fd54c083da31dbe98e785f2a72cdff04e32e00` | `FundingReceived(uint256 amount)` |
| `0x2f8492a7a430cf917798dfb60bc5af634f68e6c40287947df0ea6f7ec0669bd8` | `LineaRollupVersionChanged(bytes8 indexed previousVersion, bytes8 indexed newVersion)` |
| `0x70a40b63da92dd99e111281bc23dfb08922b6d1337f71f895cf498eb60ff7a0b` | `AddressFilterChanged(address oldAddressFilter, address newAddressFilter)` |

### 1.3 Pause, roles and proxy (LineaRollup, TokenBridge, YieldManager)

| topic0 | Event | Notes |
|---|---|---|
| `0x534f879afd40abb4e39f8e1b77a316be4c8e3521d9cf5a3a3db8959d574d4559` | `Paused(address messageSender, uint8 indexed pauseType)` | Linea pause manager (not the OpenZeppelin `Paused(address)`). |
| `0xd071d2b85dec4489435b541d2f0e2570db09b09db9efd8703948d44a433df65a` | `UnPaused(address messageSender, uint8 indexed pauseType)` | |
| `0x36287ed6be33e8d1abe33ad8d38ab23b67a5126b7140660a8a25920bdc30a199` | `PausedIndefinitely(address messageSender, uint8 indexed pauseType)` | Security Council pause with no expiry. |
| `0x3ddaeb19197ed3b5334f4c1cd5716f663d0f6dce30c52800bd1674da0b88e87a` | `UnPausedDueToExpiry(uint8 indexed pauseType)` | A 2-day pause expired. |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` | |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | EIP-1967 upgrade. **Watch on every proxy of §3.** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | |
| `0x1cf3b03a6cf19fa2baba4df148e9dcabedea7f8a5c07840e207e5c089be95d3e` | `BeaconUpgraded(address indexed beacon)` | |

### 1.4 TokenBridge (emitter `0x051F1D88f0aF5763fB888eC4378b4D8B29ea3319`)

| topic0 | Event | Notes |
|---|---|---|
| `0x8780a94875b70464f8ac6c28851501d32e7fd4ee574e4b94beb28923a3c42d9c` | `BridgingInitiatedV2(address indexed sender, address indexed recipient, address indexed token, uint256 amount)` | **Source leg (tokens), current.** |
| `0x6ed06519caca659cdefa71015c79a561928d3cf8cc4a3e9739fde9fb5fb38d64` | `BridgingFinalizedV2(address indexed nativeToken, address indexed bridgedToken, uint256 amount, address indexed recipient)` | **Destination leg (tokens), current.** `bridgedToken` = `0x0` when the token is L1-native (released from escrow). |
| `0xde5fcf0a1aebed387067eb25655de732ccfc43fe5b5a3d91d367c26e773fcd1c` | `BridgingInitiated(address indexed sender, address recipient, address indexed token, uint256 indexed amount)` | V1, historical (20 logs in Ethereum blocks 18500000–18510000; 0 in the pinned window). Note the different indexed set. |
| `0xd28a2d30314c6a2f46b657c15ee4d7ffc33b2817e78f341a260e216cebfbdbef` | `BridgingFinalized(address indexed nativeToken, address indexed bridgedToken, uint256 indexed amount, address recipient)` | V1, historical (6 logs in the same 2023 range). |
| `0x0f53e2a811b6fd2d6cd965fd6c27b44fb924ca39f7a7f321115705c22366d623` | `NewToken(address indexed token)` | First bridging of a token. |
| `0xd5d4920bb61e6141c8499d50a7bd617dae2b1818c9d6b995d3f2ba4975e32ea4` | `NewTokenDeployed(address indexed bridgedToken, address indexed nativeToken)` | A `BridgedToken` proxy was created on this side. |
| `0x91d24864a084ab70b268a1f865e757ca12006cf298d763b6be697302ef86498c` | `TokenDeployed(address indexed token)` | |
| `0x59eab5b5f813ac9e0c10035dfb55b5e3419eff53c0f7a869fb3c22400ea036d6` | `DeploymentConfirmed(address[] tokens, address indexed confirmedBy)` | |
| `0x844cb5c635052898ad92bea4ece14519111765d835105e76aa1f77ad0d0aa81f` | `CustomContractSet(address indexed nativeToken, address indexed customContract, address indexed setBy)` | Admin: a custom bridged-token contract. |
| `0xc96d462e42a71473da49a1d58c1754b9b2d319786692d621dc7f921331c517e9` | `MessageServiceUpdated(address indexed newMessageService, address indexed oldMessageService, address indexed setBy)` | Admin. **High severity.** |
| `0xe68b208814fdb633b222cd15e73d5a27fb4ef9eef4cae78c623bc27702141d28` | `RemoteSenderSet(address indexed remoteSender, address indexed setter)` | Admin. **High severity.** |
| `0x5e023c7a09fa0534ce3199f65fc3e635a5e851c5adc88ebda3b9d332ae07cbe9` | `TokenReserved(address indexed token)` | Admin. |
| `0x0145163d8d460d1ab21463758d147fdfe79d4b57c81ca3d1439996104ae68959` | `ReservationRemoved(address indexed token)` | Admin. |

### 1.5 YieldManager (emitter `0xeb63cABDd78537b9b72A2AFB573F7caa91bd8D94`) and the retired L1USDCBridge (`0x504A330327A089d8364C4ab3811Ee26976d388ce`)

| topic0 | Event | Notes |
|---|---|---|
| `0x064da12803777b899def6d3c6a0fe76bbfc1aa0a14c37ce5607fb3c1fd9b0850` | `LSTMinted(address indexed yieldProvider, address indexed recipient, uint256 amount)` | **Payout in stETH** (destination leg variant). |
| `0xda51c3b2bf48c0a6a6f0b2022a50ad3c6cfda56ca9733b418d93f8ef8a3ad590` | `YieldProviderFunded(address indexed yieldProvider, uint256 amount)` | ETH leaves the rollup reserve to staking. |
| `0x9a18553bf7bf097999c2a627f77cb273166610756fd09b4793c3ebe973dd1cc9` | `YieldProviderWithdrawal(address indexed yieldProvider, uint256 amountWithdrawn, uint256 reserveIncrementAmount)` | ETH returns toward the reserve. |
| `0x734acce255d0ede0d369eb2a376adfaeb638ec809047968d9aede73ac267ac2d` | `ReserveFundsReceived(uint256 amount)` | |
| `0x1311c746864667581a3412c2b7e38122d40283f6607236c06a735da05960f4d1` | `NativeYieldReported(address indexed yieldProvider, address indexed l2YieldRecipient, uint256 yieldAmount, uint256 outstandingNegativeYield)` | Pairs with the synthetic `MessageSent`. |
| `0xb4e1304f97b5093610f51b33ddab6622388422e2dac138b0d32f93dcfbd39edf` | `Deposited(address indexed depositor, uint256 amount, address indexed to)` | Old USDC bridge source leg (historical). |
| `0xc79857a8951ecfecbabd2f50997eb17d43f2b30e775d4e471c351d5be1e63b93` | `ReceivedFromOtherLayer(address indexed recipient, uint256 indexed amount)` | Old USDC bridge destination leg (historical). |
| `0x8ede55428cc5dd71bf87d8af8f0e1d5002a29058a976f4330ab7615857e6ed32` | `AllLockedUSDCBurnt(address indexed sender)` | Emitted once (2025, tx `0x5332f51c9e06b5835bfc96b8f3b7aecfa3bd937009871bed31084e3a1588d025`) when the locked USDC was burned. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 LineaRollup

Tuple `ClaimMessageWithProofParams` = `(bytes32[] proof, uint256 messageNumber, uint32 leafIndex, address from, address to, uint256 fee, uint256 value, address feeRecipient, bytes32 merkleRoot, bytes data)`.

| Selector | Signature | Notes |
|---|---|---|
| `0x9f3ce55a` | `sendMessage(address _to, uint256 _fee, bytes _calldata)` | payable. **Source leg** for ETH and messages. |
| `0x6463fb2a` | `claimMessageWithProof((bytes32[] proof, uint256 messageNumber, uint32 leafIndex, address from, address to, uint256 fee, uint256 value, address feeRecipient, bytes32 merkleRoot, bytes data) _params)` | **Destination leg.** Anyone may call. |
| `0x6b783172` | `claimMessageWithProofAndWithdrawLST((bytes32[] proof, uint256 messageNumber, uint32 leafIndex, address from, address to, uint256 fee, uint256 value, address feeRecipient, bytes32 merkleRoot, bytes data) _params, address _yieldProvider)` | Pays stETH when the rollup lacks ETH; caller must be `to`. |
| `0x491e0936` | `claimMessage(address _from, address _to, uint256 _fee, uint256 _value, address _feeRecipient, bytes _calldata, uint256 _nonce)` | Legacy (pre-proof) claim path. |
| `0x4bb97413` | `reportNativeYield(uint256 _amount, address _l2YieldRecipient)` | YieldManager only; emits a synthetic `MessageSent`. |
| `0xe66c2a93` | `transferFundsForNativeYield(uint256 _amount)` | Moves ETH from the rollup to the YieldManager. |
| `0xb60d4288` | `fund()` | payable; emits `FundingReceived`. |
| `0x755bc62f` | `finalizeBlocks(bytes _aggregatedProof, uint256 _proofType, (bytes32 parentStateRootHash, uint256 endBlockNumber, (bytes32 parentShnarf, bytes32 snarkHash, bytes32 finalStateRootHash, bytes32 dataEvaluationPoint, bytes32 dataEvaluationClaim) shnarfData, uint256 lastFinalizedTimestamp, uint256 finalTimestamp, bytes32 lastFinalizedL1RollingHash, bytes32 l1RollingHash, uint256 lastFinalizedL1RollingHashMessageNumber, uint256 l1RollingHashMessageNumber, uint256 l2MerkleTreesDepth, uint256 lastFinalizedForcedTransactionNumber, uint256 finalForcedTransactionNumber, bytes32 lastFinalizedForcedTransactionRollingHash, bytes32[] l2MerkleRoots, address[] filteredAddresses, bytes l2MessagingBlocksOffsets) _finalizationData)` | Operator. |
| `0x99467a35` | `submitBlobs((uint256 dataEvaluationClaim, bytes kzgCommitment, bytes kzgProof, bytes32 finalStateRootHash, bytes32 snarkHash)[] _blobSubmissions, bytes32 _parentShnarf, bytes32 _finalBlobShnarf)` | Operator. |
| `0x248c6126` | `storeForcedTransaction(bytes32 _forcedTransactionRollingHash, address _from, uint256 _blockNumberDeadline, bytes _rlpEncodedSignedTransaction)` | payable; forced-transaction path. |
| `0xe196fb5d` | `pauseByType(uint8 _pauseType)` | Pause role of the type. |
| `0x1065a399` | `unPauseByType(uint8 _pauseType)` | |
| `0x95ba81fa` | `unPauseByExpiredType(uint8 _pauseType)` | Anyone, after expiry. |
| `0x557eac73` | `resetRateLimitAmount(uint256 _amount)` | Rate-limit setter role. |
| `0xaea4f745` | `resetAmountUsedInPeriod()` | |
| `0xc2116974` | `setVerifierAddress(address _newVerifierAddress, uint256 _proofType)` | **High severity.** |
| `0x74ce962c` | `setYieldManager(address _newYieldManager)` | **High severity.** |
| `0x8c7c363a` | `setAddressFilter(address _addressFilter)` | |
| `0x2f2ff15d` | `grantRole(bytes32 role, address account)` | |
| `0xd547741f` | `revokeRole(bytes32 role, address account)` | |
| `0x91d14854` | `hasRole(bytes32 role, address account)` | view. |
| `0xb837dbe9` | `nextMessageNumber()` | view (810064 on 2026-09-29). |
| `0xad422ff0` | `limitInWei()` | view (10,000 ETH). |
| `0xc0729ab1` | `currentPeriodAmountInWei()` | view. |
| `0xbc61e733` | `isPaused(uint8 _pauseType)` | view. |
| `0x9ee8b211` | `isMessageClaimed(uint256 _messageNumber)` | view. |
| `0x914e57eb` | `rollingHashes(uint256 messageNumber)` | view. |
| `0x695378f5` | `currentL2BlockNumber()` | view. |
| `0x80b7af18` | `yieldManager()` | view. |

### 2.2 TokenBridge

| Selector | Signature | Notes |
|---|---|---|
| `0x522ea81a` | `bridgeToken(address _token, uint256 _amount, address _recipient)` | payable (message fee). **Source leg (tokens).** |
| `0xdfa96efb` | `bridgeTokenWithPermit(address _token, uint256 _amount, address _recipient, bytes _permitData)` | payable. |
| `0xe4d27451` | `completeBridging(address _nativeToken, uint256 _amount, address _recipient, uint256 _chainId, bytes _tokenMetadata)` | Only the message service, during a claim. **Destination leg (tokens).** |
| `0x4bf98dce` | `confirmDeployment(address[] _tokens)` | payable. |
| `0x1754f301` | `setCustomContract(address _nativeToken, address _targetContract)` | Admin. |
| `0xcdd914c5` | `setReserved(address _token)` | Admin. |
| `0xedc42a22` | `removeReserved(address _token)` | Admin. |
| `0xbe46096f` | `setMessageService(address _messageService)` | Admin. **High severity.** |
| `0x2a564f34` | `setDeployed(address[] _nativeTokens)` | Message service only. |
| `0x0f6f86ec` | `nativeToBridgedToken(uint256 chainId, address nativeToken)` | view. |
| `0xca41a247` | `bridgedToNativeToken(address bridgedToken)` | view. |
| `0xa6ef995f` | `remoteSender()` | view (the L2 TokenBridge). |
| `0x8dae45dd` | `messageService()` | view (the LineaRollup). |
| `0x1544298e` | `sourceChainId()` | view (1). |
| `0x146ffb26` | `targetChainId()` | view (59144). |

### 2.3 YieldManager, old USDC bridge, ProxyAdmin

| Selector | Signature | Notes |
|---|---|---|
| `0x3e4903b7` | `withdrawLST(address _yieldProvider, uint256 _amount, address _recipient)` | YieldManager; called by the rollup's LST claim. |
| `0xb6b55f25` | `deposit(uint256 amount)` | Old USDC bridge (paused). |
| `0x70aff70f` | `depositTo(uint256 amount, address to)` | Old USDC bridge (paused). |
| `0x26dfbc20` | `receiveFromOtherLayer(address recipient, uint256 amount)` | Old USDC bridge. |
| `0x21846ebb` | `burnAllLockedUSDC()` | Old USDC bridge (already executed). |
| `0x9623609d` | `upgradeAndCall(address proxy, address implementation, bytes data)` | ProxyAdmin. **Upgrade.** |
| `0x99a88ec4` | `upgrade(address proxy, address implementation)` | ProxyAdmin. **Upgrade.** |
| `0x7eff275e` | `changeProxyAdmin(address proxy, address newAdmin)` | ProxyAdmin. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All existence-checked with `eth_getCode` on 2026-09-29; implementations and admins read from the EIP-1967 slots.

### 3.1 Bridge and rollup

| Role | Address | Notes |
|---|---|---|
| **LineaRollup** (message service, ETH escrow) | `0xd19d4B5d358258f05D7B411E21A1460D11B0876F` | proxy (2227 B); impl `0x052b73d934E9412045Bf731574463Fd026D74645`; admin ProxyAdmin `0xF5058616517C068C7b8c7EbC69FF636Ade9066d6`. |
| **TokenBridge** (token escrow) | `0x051F1D88f0aF5763fB888eC4378b4D8B29ea3319` | proxy; impl `0xF0e003F0dE2d583Ae28FA8cBF66aa096CdAce3ff`; admin ProxyAdmin `0xF5058616517C068C7b8c7EbC69FF636Ade9066d6`. |
| **YieldManager** | `0xeb63cABDd78537b9b72A2AFB573F7caa91bd8D94` | proxy; impl `0x751236A1aFC11B7F1A7630fe87b0Bd96AC5203C4`; admin ProxyAdmin `0xF5058616517C068C7b8c7EbC69FF636Ade9066d6`; `LineaRollup.yieldManager()` returns it. |
| LidoStVaultYieldProvider | `0x486D8cADc10489B30b64c890aEc747F1220eEEC3` | immutable (13066 B), delegate-called by the YieldManager. |
| L1USDCBridge (retired) | `0x504A330327A089d8364C4ab3811Ee26976d388ce` | proxy; impl `0x66CFD1562d6Aa4629e9e4142662c1A403528Df00`; admin ProxyAdmin `0x41fAD3Df1B07B647D120D055259E474fE8046eb5`; `paused()` = true; holds 36 USDC. |
| UpgradeableBeacon (bridged tokens) | `0x971f46a2852d11D59dbF0909e837cfd06f357DeB` | implementation `0x36f274C1C197F277EA3C57859729398FCc8a3763` (BridgedToken). |
| CallForwardingProxy | `0x3697bD0bC6C050135b8321F989a5316eACbF367D` | forwards any call to the LineaRollup. |
| AddressFilter | `0x526AE78F0103Ae73F05449ae30eb626C1003784E` | forced-transaction blocklist. |
| PlonkVerifierFull | `0x09ac9f7E5Fb37e241e0B1e52aaF01eFE0a488a77`, `0xAFF26999780901ee8B48f0a1271a177ff46fD53F` | immutable (9118 B each). |

### 3.2 Governance

| Role | Address | Notes (read live) |
|---|---|---|
| ProxyAdmin (rollup, TokenBridge, YieldManager) | `0xF5058616517C068C7b8c7EbC69FF636Ade9066d6` | `owner()` = Timelock. |
| Timelock | `0xd6B95c960779c72B8C6752119849318E5d550574` | `getMinDelay()` = 0. |
| ProxyAdmin (old USDC bridge) | `0x41fAD3Df1B07B647D120D055259E474fE8046eb5` | `owner()` = Security Council. |
| Linea Security Council (Safe) | `0x892bb7EeD71efB060ab90140e7825d8127991DD3` | `DEFAULT_ADMIN_ROLE` and `PAUSE_ALL_ROLE` on the rollup; owner of the old USDC bridge. |
| Pauser (EOA) | `0x2532bfdc9Ba58B13358A9C5C05136d6938Bc42d0` | holds `PAUSE_ALL_ROLE` on the rollup (`hasRole` = true); no code, nonce 0. |

### 3.3 A look-alike on Ethereum

`0x508Ca82Df566dCD1B0DE8296e70a96332cD644ec` is the **L2** message service address on Linea, but it also has code on Ethereum: an EIP-1967 proxy (impl `0x369DB650D875938252682532eA9E4Af267a7d126`, admin `0x1E1f6F22f97b4a7522D8B62e983953639239774E`, which is the address of the L2 ProxyAdmin). It is not the L1 message service and emitted no `MessageSent` in the pinned window. The L1 message service is the LineaRollup.

---

## 4. Cross-chain summary

| Chain | ID | LineaRollup (message service) | TokenBridge | YieldManager | Old USDC bridge |
|---|---|---|---|---|---|
| **Ethereum** | 1 | ✅ `0xd19d4B5d358258f05D7B411E21A1460D11B0876F` | ✅ `0x051F1D88f0aF5763fB888eC4378b4D8B29ea3319` | ✅ `0xeb63cABDd78537b9b72A2AFB573F7caa91bd8D94` | ✅ `0x504A330327A089d8364C4ab3811Ee26976d388ce` (paused) |
| Base | 8453 | — | — | — | — |
| Arbitrum One | 42161 | — | — | — | — |
| Optimism | 10 | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — |
| BNB Smart Chain | 56 | — | — | — | — |
| Avalanche C-Chain | 43114 | — | — | — | — |
| Robinhood Chain | 4663 | — | — | — | — |

"—" means `eth_getCode` returned `0x` with nonce 0 on 2026-09-29 at the rollup, TokenBridge, old USDC bridge, YieldManager, ProxyAdmin and Timelock addresses, and at the L2 message service and L2 TokenBridge addresses. The Linea docs list no L1 contract outside Ethereum. In the pinned window no Linea topic0 of §1.1 or §1.4 was emitted on any of the seven other chains.

The counterparty, Linea (59144), is outside the eight. USDC between Linea and the target chains moves over Circle CCTP V2, not over this bridge.

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade authority |
|---|---|---|---|
| LineaRollup, TokenBridge, YieldManager | EIP-1967 transparent | impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` and admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` both set | ProxyAdmin `0xF5058616517C068C7b8c7EbC69FF636Ade9066d6` → owner Timelock `0xd6B95c960779c72B8C6752119849318E5d550574` with **0 s** minimum delay (read live). Roles (pause, rate limit, verifier, yield manager) sit with the Security Council (`DEFAULT_ADMIN_ROLE`). |
| L1USDCBridge | EIP-1967 transparent | both slots set | ProxyAdmin `0x41fAD3Df1B07B647D120D055259E474fE8046eb5` → owner Security Council. |
| BridgedToken proxies (L1 copies of Linea-native tokens) | beacon | beacon `0x971f46a2852d11D59dbF0909e837cfd06f357DeB` | beacon owner (not read). |
| LidoStVaultYieldProvider, CallForwardingProxy, AddressFilter, PlonkVerifierFull | immutable | no impl slot | none |

Current implementations (2026-09-29): rollup `0x052b73d934E9412045Bf731574463Fd026D74645`, TokenBridge `0xF0e003F0dE2d583Ae28FA8cBF66aa096CdAce3ff`, YieldManager `0x751236A1aFC11B7F1A7630fe87b0Bd96AC5203C4`, old USDC bridge `0x66CFD1562d6Aa4629e9e4142662c1A403528Df00`. L2BEAT counts 13 upgrades of the rollup and 4 of the TokenBridge.

---

## 6. Detection invariants & gotchas

1. **Link by `_messageHash`.** L1 `MessageSent._messageHash` ↔ L2 claim; L2 `MessageSent._messageHash` ↔ L1 `MessageClaimed._messageHash`. `_nonce` / `messageNumber` orders the L1→L2 messages (`nextMessageNumber()` = 810064 on 2026-09-29).
2. **ETH payouts have no amount event.** Read the value from the internal transfer out of `0xd19d4B5d358258f05D7B411E21A1460D11B0876F`, or decode `value` from the claim calldata. In the guide's measurement most ETH claims carried only `MessageClaimed`.
3. **Count a token deposit once.** `bridgeToken` emits `MessageSent` (`_from` = TokenBridge, `_value` = 0) and `BridgingInitiatedV2`. Use `BridgingInitiatedV2.amount` for the token amount and drop the paired `MessageSent`.
4. **Exclude the synthetic yield messages.** A `MessageSent` with `_from` = YieldManager `0xeb63cABDd78537b9b72A2AFB573F7caa91bd8D94` is a staking-yield report (`NativeYieldReported`), not a deposit, even though `_value` > 0.
5. **Some payouts are in stETH.** When the rollup's ETH balance is short (part of it is staked through the YieldManager), `claimMessageWithProofAndWithdrawLST` pays stETH and `LSTMinted` fires; there is no ETH transfer. A drop in the rollup's ETH balance can be `YieldProviderFunded`, not an exit.
6. **`_from` is the direct caller.** Deposits come through routers and other bridges; in the pinned window the sample `MessageSent` came from the Across HubPool (`0xc186fA914353c44b2E33eBE05f21846F1048bEda`). Attribute by `_from` and `_to` with that in mind.
7. **V1 vs V2 TokenBridge events have different indexed fields.** V1 `BridgingInitiated` indexes `amount` and not `recipient`; V1 `BridgingFinalized` indexes `amount` and not `recipient`. Back-fills before mid-2024 need the V1 topics.
8. **`BridgingFinalizedV2.bridgedToken = 0x0`** means an L1-native token released from escrow; a non-zero value means a Linea-native token minted on L1 (a `BridgedToken` proxy).
9. **The rate limit is a monitor signal.** L2→L1 ETH claims count against 10,000 ETH per 24 hours; `LimitAmountChanged` and `AmountUsedInPeriodReset` are admin actions.
10. **Admin triggers:** `Upgraded` (0 s timelock), `Paused` / `PausedIndefinitely` (by type), `VerifierAddressChanged`, `YieldManagerChanged`, `RoleGranted` / `RoleRevoked`, TokenBridge `MessageServiceUpdated`, `RemoteSenderSet`, `CustomContractSet`. An EOA (`0x2532bfdc9Ba58B13358A9C5C05136d6938Bc42d0`) can pause everything.
11. **USDC.** The old USDC bridge is paused and emptied (36 USDC left). A USDC transfer to or from Linea today is a CCTP burn/mint, not a Linea bridge event.
12. **Large-transfer trigger:** `MessageSent._value` (excluding the YieldManager) and the internal ETH value of claims; `BridgingInitiatedV2.amount` / `BridgingFinalizedV2.amount` per token.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== LineaRollup (message service) =====
TOPIC_LINEA_MESSAGE_SENT             = '\xe856c2b8bd4eb0027ce32eeaf595c21b0b6b4644b326e5b7bd80a1cf8db72e6c'
TOPIC_LINEA_ROLLING_HASH_UPDATED     = '\xea3b023b4c8680d4b4824f0143132c95476359a2bb70a81d6c5a36f6918f6339'
TOPIC_LINEA_MESSAGE_CLAIMED          = '\xa4c827e719e911e8f19393ccdb85b5102f08f0910604d340ba38390b7ff2ab0e'
TOPIC_LINEA_L2_MERKLE_ROOT_ADDED     = '\x300e6f978eee6a4b0bba78dd8400dc64fd5652dbfc868a2258e16d0977be222b'
TOPIC_LINEA_DATA_FINALIZED_V3        = '\xa0262dc79e4ccb71ceac8574ae906311ae338aa4a2044fd4ec4b99fad5ab60cb'
TOPIC_LINEA_PAUSED                   = '\x534f879afd40abb4e39f8e1b77a316be4c8e3521d9cf5a3a3db8959d574d4559'
TOPIC_LINEA_PAUSED_INDEFINITELY      = '\x36287ed6be33e8d1abe33ad8d38ab23b67a5126b7140660a8a25920bdc30a199'
TOPIC_LINEA_VERIFIER_CHANGED         = '\x4a29db3fc6b42bda201e4b4d69ce8d575eeeba5f153509c0d0a342af0f1bd021'
TOPIC_LINEA_LIMIT_AMOUNT_CHANGED     = '\xbc3dc0cb5c15c51c81316450d44048838bb478b9809447d01c766a06f3e9f2c8'
TOPIC_UPGRADED                       = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ROLE_GRANTED                   = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
-- ===== TokenBridge =====
TOPIC_LINEA_BRIDGING_INITIATED_V2    = '\x8780a94875b70464f8ac6c28851501d32e7fd4ee574e4b94beb28923a3c42d9c'
TOPIC_LINEA_BRIDGING_FINALIZED_V2    = '\x6ed06519caca659cdefa71015c79a561928d3cf8cc4a3e9739fde9fb5fb38d64'
TOPIC_LINEA_BRIDGING_INITIATED_V1    = '\xde5fcf0a1aebed387067eb25655de732ccfc43fe5b5a3d91d367c26e773fcd1c'
TOPIC_LINEA_BRIDGING_FINALIZED_V1    = '\xd28a2d30314c6a2f46b657c15ee4d7ffc33b2817e78f341a260e216cebfbdbef'
TOPIC_LINEA_MESSAGE_SERVICE_UPDATED  = '\xc96d462e42a71473da49a1d58c1754b9b2d319786692d621dc7f921331c517e9'
TOPIC_LINEA_REMOTE_SENDER_SET        = '\xe68b208814fdb633b222cd15e73d5a27fb4ef9eef4cae78c623bc27702141d28'
-- ===== YieldManager / old USDC bridge =====
TOPIC_LINEA_LST_MINTED               = '\x064da12803777b899def6d3c6a0fe76bbfc1aa0a14c37ce5607fb3c1fd9b0850'
TOPIC_LINEA_YIELD_PROVIDER_FUNDED    = '\xda51c3b2bf48c0a6a6f0b2022a50ad3c6cfda56ca9733b418d93f8ef8a3ad590'
TOPIC_LINEA_NATIVE_YIELD_REPORTED    = '\x1311c746864667581a3412c2b7e38122d40283f6607236c06a735da05960f4d1'
TOPIC_LINEA_USDC_DEPOSITED           = '\xb4e1304f97b5093610f51b33ddab6622388422e2dac138b0d32f93dcfbd39edf'
TOPIC_LINEA_ALL_LOCKED_USDC_BURNT    = '\x8ede55428cc5dd71bf87d8af8f0e1d5002a29058a976f4330ab7615857e6ed32'

-- ===== Selectors =====
SEL_LINEA_SEND_MESSAGE               = '\x9f3ce55a'
SEL_LINEA_CLAIM_MESSAGE_WITH_PROOF   = '\x6463fb2a'
SEL_LINEA_CLAIM_WITH_PROOF_LST       = '\x6b783172'
SEL_LINEA_CLAIM_MESSAGE_LEGACY       = '\x491e0936'
SEL_LINEA_BRIDGE_TOKEN               = '\x522ea81a'
SEL_LINEA_BRIDGE_TOKEN_WITH_PERMIT   = '\xdfa96efb'
SEL_LINEA_COMPLETE_BRIDGING          = '\xe4d27451'
SEL_LINEA_PAUSE_BY_TYPE              = '\xe196fb5d'
SEL_LINEA_SET_VERIFIER_ADDRESS       = '\xc2116974'
SEL_LINEA_REPORT_NATIVE_YIELD        = '\x4bb97413'
SEL_PROXYADMIN_UPGRADE_AND_CALL      = '\x9623609d'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT                    = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                   = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Ethereum (chain ID 1) =====
ETH_LINEA_ROLLUP                     = '\xd19d4b5d358258f05d7b411e21a1460d11b0876f'
ETH_LINEA_ROLLUP_IMPL                = '\x052b73d934e9412045bf731574463fd026d74645'
ETH_LINEA_TOKEN_BRIDGE               = '\x051f1d88f0af5763fb888ec4378b4d8b29ea3319'
ETH_LINEA_TOKEN_BRIDGE_IMPL          = '\xf0e003f0de2d583ae28fa8cbf66aa096cdace3ff'
ETH_LINEA_YIELD_MANAGER              = '\xeb63cabdd78537b9b72a2afb573f7caa91bd8d94'
ETH_LINEA_LIDO_YIELD_PROVIDER        = '\x486d8cadc10489b30b64c890aec747f1220eeec3'
ETH_LINEA_USDC_BRIDGE_RETIRED        = '\x504a330327a089d8364c4ab3811ee26976d388ce'
ETH_LINEA_BRIDGED_TOKEN_BEACON       = '\x971f46a2852d11d59dbf0909e837cfd06f357deb'
ETH_LINEA_CALL_FORWARDING_PROXY      = '\x3697bd0bc6c050135b8321f989a5316eacbf367d'
ETH_LINEA_PROXY_ADMIN                = '\xf5058616517c068c7b8c7ebc69ff636ade9066d6'
ETH_LINEA_PROXY_ADMIN_USDC           = '\x41fad3df1b07b647d120d055259e474fe8046eb5'
ETH_LINEA_TIMELOCK                   = '\xd6b95c960779c72b8c6752119849318e5d550574'
ETH_LINEA_SECURITY_COUNCIL           = '\x892bb7eed71efb060ab90140e7825d8127991dd3'
ETH_LINEA_PAUSER_EOA                 = '\x2532bfdc9ba58b13358a9c5c05136d6938bc42d0'
-- counterpart addresses on Linea (59144; not a target chain)
LINEA_L2_MESSAGE_SERVICE             = '\x508ca82df566dcd1b0de8296e70a96332cd644ec'
LINEA_L2_TOKEN_BRIDGE                = '\x353012dc4a9a6cf55c941badc267f82004a8ceb9'
-- Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain: no Linea bridge contracts
```

---

## 8. Verification & sources

How the constants were verified (2026-09-29):

- **Topics and selectors:** recomputed as `keccak256(signature)` from the deployed ABIs (verified sources of the current implementations, as captured in L2BEAT's discovery data) and cross-checked with `linea-monorepo` (`contracts/src/security/pausing/interfaces/IPauseManager.sol` for the pause enum; `rollup/LinethRollupYieldExtension.sol` and `yield/LidoStVaultYieldProvider.sol` for the yield paths). Live logs confirmed `MessageSent`, `RollingHashUpdated`, `MessageClaimed`, `BridgingInitiatedV2`, `BridgingFinalizedV2`, `L2MerkleRootAdded`, `DataFinalizedV3` in the pinned window, and `BridgingInitiated`, `BridgingFinalized`, `L2L1MessageHashAddedToInbox`, `MessageClaimed` in Ethereum blocks 18500000–18510000, and `AllLockedUSDCBurnt` (1 log) in blocks 22000000–22600000.
- **Sample transactions read:** `0x0a318d9738ffa0236965042f3e2ee14cb8e30bb8211aeaed98bb6e0dc5a7249b` (Across HubPool `sendMessage`: `RollingHashUpdated` then `MessageSent`, same `_messageHash`); `0xf17b8be93a60d1f9ed117d57aaf3c7432a7d77d481ee758d914b6cf3dd9473b3` (`bridgeToken`: LINEA `Transfer` user → TokenBridge, `MessageSent` from the TokenBridge to the L2 TokenBridge, `BridgingInitiatedV2`); `0x0c83da710f7ca2034dd54c71bbb64bdf75b7bf5e1312958c6bf114a3c299463d` (`claimMessageWithProof` by the recipient: LINEA `Transfer` TokenBridge → recipient, `BridgingFinalizedV2` with `bridgedToken = 0x0`, `MessageClaimed`).
- **Addresses:** rollup, TokenBridge and Security Council from the Linea docs; the others from L2BEAT's discovery data; all existence-checked with `eth_getCode`; implementations and admins from the EIP-1967 slots; `owner()` of both ProxyAdmins; `getMinDelay()` of the Timelock; `hasRole` for the Security Council and the pauser EOA; `yieldManager()`, `limitInWei()`, `nextMessageNumber()`, `isPaused(1..12)` of the rollup; `sourceChainId()`, `targetChainId()`, `messageService()`, `remoteSender()` of the TokenBridge; `paused()`, `owner()` and the USDC balance of the old USDC bridge.
- **Chain coverage:** `eth_getCode` = `0x` (nonce 0) on Base, Arbitrum, Optimism, Polygon, BNB, Avalanche and Robinhood Chain at the rollup, TokenBridge, old USDC bridge, YieldManager, ProxyAdmin, Timelock, L2 message service and L2 TokenBridge addresses.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Ethereum blocks 26072222–26075812):** `MessageSent` 33, `RollingHashUpdated` 33, `MessageClaimed` 66, `L2MerkleRootAdded` 3, `DataFinalizedV3` 4, `BridgingInitiatedV2` 2, `BridgingFinalizedV2` 2, `BridgingInitiated` (V1) 0, `BridgingFinalized` (V1) 0, `LSTMinted` 0 (any emitter), old USDC `Deposited` 0. The other seven chains: no Linea emitter exists; 0 logs of these topics.

Sources opened:
- [Consensys/linea-monorepo](https://github.com/Consensys/linea-monorepo) (`contracts/src/`)
- [Linea docs — contracts](https://docs.linea.build/network/build/contracts) · [Linea docs — bridge](https://docs.linea.build/network/build/bridge)
- [L2BEAT discovery data for Linea](https://github.com/l2beat/l2beat/blob/main/packages/config/src/projects/linea/discovered.json)
- Linea JSON-RPC `eth_chainId` (public endpoint) for 59144

Circle's Linea case-study page (https://www.circle.com/case-studies/linea) describes the March 2025 native-USDC upgrade. Only its search summary was read; the on-chain `AllLockedUSDCBurnt` log is the evidence used here.
