# Chainlink CCIP — Topics, Selectors, Chain Selectors, Addresses

**Status:** verified 2026-05-29. Chain selectors verified against `smartcontractkit/chain-selectors`; Router addresses verified via `eth_getCode` (non-empty) on every chain; Ethereum support contracts + `ccipSend`/`isChainSupported` selectors verified against live bytecode; Ethereum Router `typeAndVersion() = "Router 1.2.0"`. Extended 2026-09-29: the 1.6.0 and 2.0.0 ramps, the legacy Ethereum↔Base EVM2EVM ramps, the token pools and the support contracts of all eight target chains, taken from the CCIP Directory data (`smartcontractkit/documentation` `src/config/data/ccip/v1_2_0/mainnet/{chains,lanes,tokens}.json`) and checked with `eth_getCode` and `typeAndVersion()`; ramp and pool events re-derived from `smartcontractkit/chainlink-ccip` (`main` = 2.0.0, branch `contracts-ccip-release/1.6.0`) and `smartcontractkit/ccip` (tag `v2.17.0-ccip1.5.16`); two §2.2 rows corrected; Robinhood Chain (4663) added.
**Scope:** Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Robinhood Chain (4663). LINK token (a valid fee token): [link-token.md](link-token.md).

CCIP sends arbitrary messages + token transfers across chains. A user calls **`Router.ccipSend()`** on the source chain; the lane's **OnRamp** emits the message; the DON commits it on the destination's **OffRamp**, which executes it via the destination **Router**. **CCIP does NOT use EVM chain IDs** — every lane is addressed by a uint64 **chain selector** (§1).

**Architecture by version:**
- **v1.0 / v1.2:** per-lane `EVM2EVMOnRamp` + `EVM2EVMOffRamp` + `CommitStore`; fees priced by a shared **`PriceRegistry`**. Router `"Router 1.2.0"`.
- **v1.5:** adds **`TokenAdminRegistry`** + `RegistryModuleOwnerCustom` (self-serve token-pool registration / CCT) and replaces `PriceRegistry` with **`FeeQuoter`**; lanes still OnRamp/OffRamp/CommitStore.
- **v1.6:** new architecture — unified **`OnRamp`**/**`OffRamp`** (CommitStore folded into OffRamp), a chain-wide **`NonceManager`**, OCR3, and the message-id-centric `CCIPMessageSent` event.
- **v2.0:** a second unified pair, **`OnRamp 2.0.0`** / **`OffRamp 2.0.0`** (one each per chain, all lanes), with cross-chain verifiers (CCVs) instead of the commit plugin; `CCIPMessageSent` indexes `messageId`, and `ExecutionStateChanged` is keyed by `messageNumber`. New pools: `CCTPThroughCCVTokenPool`, `LockReleaseTokenPool 2.0.0` backed by an `ERC20LockBox`, `BurnMintTokenPool 2.0.0`.

**What runs where (CCIP Directory, 2026-09-29):** every lane between two of the eight target chains uses the **2.0.0** ramps; each chain keeps one **1.6.0** OnRamp/OffRamp for lanes to other chains; many lanes to other chains still use per-lane **1.5.0** `EVM2EVMOnRamp`/`EVM2EVMOffRamp` pairs. So three send events and three execution events are live at once (§2.2).

The Router address is **stable across versions** on a given chain; lane contracts (ramps) are swapped underneath.

---

## 1. Chain selectors (CRITICAL — not EVM chain IDs)

Verified against `smartcontractkit/chain-selectors` `selectors.yml`.

| Chain | EVM chainId | CCIP chain selector (uint64) |
|-------|-------------|------------------------------|
| Ethereum | 1 | `5009297550715157269` |
| Base | 8453 | `15971525489660198786` |
| BNB Smart Chain | 56 | `11344663589394136015` |
| Avalanche C-Chain | 43114 | `6433500567565415381` |
| Arbitrum One | 42161 | `4949039107694359620` |
| Optimism | 10 | `3734403246176062136` |
| Polygon PoS | 137 | `4051577828743386545` |
| Robinhood Chain | 4663 | `6180753054346818345` |

The Robinhood Chain selector is taken from the CCIP Directory (`robinhood-mainnet`) and read live as the first word of `getStaticConfig()` on its OnRamps and OffRamps (`0x55c67227e8c0b329`). The words `0x45849994fc9c7b15` (Ethereum) and `0xdda641cfe44aff82` (Base) appear the same way on the Ethereum and Base ramps.

---

## 2. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 2.1 Router

| topic0 | Event |
|--------|-------|
| `0x9b877de93ea9895756e337442c657f95a34fc68e7eb988bdfa693d5be83016b6` | `MessageExecuted(bytes32 messageId, uint64 sourceChainSelector, address offRamp, bytes32 calldataHash)` |
| `0xa4bdf64ebdf3316320601a081916a75aa144bcef6c4beeb0e9fb1982cacc6b94` | `OffRampAdded(uint64 indexed sourceChainSelector, address offRamp)` |
| `0xa823809efda3ba66c873364eec120fa0923d9fabda73bc97dd5663341e2d9bcb` | `OffRampRemoved(uint64 indexed sourceChainSelector, address offRamp)` |
| `0x1f7d0ec248b80e5c0dde0ee531c4fc8fdb6ce9a2b3d90f560c74acd6a7202f23` | `OnRampSet(uint64 indexed destChainSelector, address onRamp)` |

### 2.2 OnRamp / OffRamp / CommitStore — the message legs

Emitters: the ramps of §4.3–§4.4. Three generations are live at the same time, each with its own send and execution event.

**Source leg (OnRamp):**

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x371bc2ff0a006f4ef863b1d27a065d4e9f938b6d883eb154572b4aea593b32cc` | `CCIPMessageSent(uint64 indexed destChainSelector, address indexed sender, bytes32 indexed messageId, address feeToken, uint256 tokenAmountBeforeTokenPoolFees, bytes encodedMessage, (address issuer, uint32 destGasLimit, uint32 destBytesOverhead, uint256 feeTokenAmount, bytes extraArgs)[] receipts, bytes[] verifierBlobs)` | **OnRamp 2.0.0.** `messageId` is topic3; `sender` is the calling contract or user. |
| `0x192442a2b2adb6a7948f097023cb6b57d29d3a7a5dd33e6666d33c39cc456f32` | `CCIPMessageSent(uint64 indexed destChainSelector, uint64 indexed sequenceNumber, ((bytes32 messageId, uint64 sourceChainSelector, uint64 destChainSelector, uint64 sequenceNumber, uint64 nonce) header, address sender, bytes data, bytes receiver, bytes extraArgs, address feeToken, uint256 feeTokenAmount, uint256 feeValueJuels, (address sourcePoolAddress, bytes destTokenAddress, bytes extraData, uint256 amount, bytes destExecData)[] tokenAmounts) message)` | **OnRamp 1.6.0.** `messageId` = `message.header.messageId` (in data). |
| `0xd0c3c799bf9e2639de44391e7f524d229b2b55f5b1ea94b2bf7da42f7243dddd` | `CCIPSendRequested((uint64 sourceChainSelector, address sender, address receiver, uint64 sequenceNumber, uint256 gasLimit, bool strict, uint64 nonce, address feeToken, uint256 feeTokenAmount, bytes data, (address token, uint256 amount)[] tokenAmounts, bytes[] sourceTokenData, bytes32 messageId) message)` | **EVM2EVMOnRamp 1.2.0 / 1.5.0** (one per lane). No indexed field. |

**Destination leg (OffRamp) and commit:**

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x8c324ce1367b83031769f6a813e3bb4c117aba2185789d66b98b791405be6df2` | `ExecutionStateChanged(uint64 indexed sourceChainSelector, uint64 indexed messageNumber, bytes32 indexed messageId, uint8 state, bytes returnData)` | **OffRamp 2.0.0.** The payout event on every lane between target chains. |
| `0x05665fe9ad095383d018353f4cbcba77e84db27dd215081bbf7cdf9ae6fbe48b` | `ExecutionStateChanged(uint64 indexed sourceChainSelector, uint64 indexed sequenceNumber, bytes32 indexed messageId, bytes32 messageHash, uint8 state, bytes returnData, uint256 gasUsed)` | **OffRamp v1.6** (adds sourceChainSelector + gasUsed) |
| `0xd4f851956a5d67c3997d1c9205045fef79bae2947fdee7e9e2641abc7391ef65` | `ExecutionStateChanged(uint64 indexed sequenceNumber, bytes32 indexed messageId, uint8 state, bytes returnData)` | **OffRamp (≤v1.5)** — `state`: 0=Untouched,1=InProgress,2=Success,3=Failure (same enum in 1.6.0 and 2.0.0). |
| `0xb967c9b9e1b7af9a61ca71ff00e9f5b89ec6f2e268de8dacf12f0de8e51f3e47` | `CommitReportAccepted((uint64 sourceChainSelector, bytes onRampAddress, uint64 minSeqNr, uint64 maxSeqNr, bytes32 merkleRoot)[] blessedMerkleRoots, (uint64 sourceChainSelector, bytes onRampAddress, uint64 minSeqNr, uint64 maxSeqNr, bytes32 merkleRoot)[] unblessedMerkleRoots, ((address sourceToken, uint224 usdPerToken)[] tokenPriceUpdates, (uint64 destChainSelector, uint224 usdPerUnitGas)[] gasPriceUpdates) priceUpdates)` | **OffRamp 1.6.0** commit (CommitStore folded in). Status only — no value moves. |
| `0x198d6990ef96613a9026203077e422916918b03ff47f0be6bee7b02d8e139ef0` | `Transmitted(uint8 indexed ocrPluginType, bytes32 configDigest, uint64 sequenceNumber)` | **OffRamp 1.6.0** OCR3 transmit (`ocrPluginType` 0 = commit, 1 = execution). Status only. |
| `0x291698c01aa71f912280535d88a00d2c59fb63530a3f5d0098560468acb9ebf5` | `ReportAccepted((((address sourceToken, uint224 usdPerToken)[] tokenPriceUpdates, (uint64 destChainSelector, uint224 usdPerUnitGas)[] gasPriceUpdates) priceUpdates, (uint64 min, uint64 max) interval, bytes32 merkleRoot) report)` | **CommitStore 1.2.0 / 1.5.0** — commit of a batch's Merkle root. Status only. |
| `0xb04e63db38c49950639fa09d29872f21f5d49d614f3a969d8adf3d4b52e41a62` | `Transmitted(bytes32 configDigest, uint32 epoch)` | OCR2 transmit on CommitStore and EVM2EVMOffRamp (≤v1.5). Status only. |
| `0x3b575419319662b2a6f5e2467d84521517a3382b908eb3d557bb3fdb0c50e23c` | `SkippedAlreadyExecutedMessage(uint64 sourceChainSelector, uint64 sequenceNumber)` | OffRamp 1.6.0, status only |
| `0x3ef2a99c550a751d4b0b261268f05a803dfb049ab43616a1ffb388f61fe65120` | `AlreadyAttempted(uint64 sourceChainSelector, uint64 sequenceNumber)` | OffRamp 1.6.0, status only |
| `0x202f1139a3e334b6056064c0e9b19fd07e44a88d8f6e5ded571b24cf8c371f12` | `RootRemoved(bytes32 root)` | OffRamp 1.6.0 admin (a committed root was deleted) |
| `0xd5ad72bc37dc7a80a8b9b9df20500046fd7341adb1be2258a540466fdd7dcef5` | `DestChainConfigSet(uint64 indexed destChainSelector, uint64 sequenceNumber, address router, bool allowlistEnabled)` | OnRamp 1.6.0 admin |
| `0x508d7d183612c18fc339b42618912b9fa3239f631dd7ec0671f950200a0fa66e` | `FeeTokenWithdrawn(address indexed feeAggregator, address indexed feeToken, uint256 amount)` | OnRamp 1.6.0 fee sweep |

> All three send shapes above were recomputed from source and each matched live logs in the pinned window (§7). The 1.2/1.5 CommitStore event `ReportAccepted` hashes to `0x291698c01aa71f912280535d88a00d2c59fb63530a3f5d0098560468acb9ebf5` (seen on both Ethereum CommitStores of the Ethereum↔Base lane), and the 1.6.0 `CommitReportAccepted` hashes to `0xb967c9b9e1b7af9a61ca71ff00e9f5b89ec6f2e268de8dacf12f0de8e51f3e47` (41 to 806 logs per chain in the pinned 12-hour window). The cross-chain join key is **`messageId`** (a `bytes32`): topic3 of the 2.0.0 send and of every `ExecutionStateChanged` from 1.6.0 on, topic2 of the ≤1.5 `ExecutionStateChanged`, and a field inside the 1.6.0 and ≤1.5 send structs.

### 2.3 Token pools — the value legs

Emitter: the token's pool (§4.6); resolve any token's pool with `TokenAdminRegistry.getPool(token)`. Two event generations exist, and the version is in `typeAndVersion()`.

| topic0 | Event | Pool type |
|--------|-------|-----------|
| `0x9d228d69b5fdb8d273a2336f8fb8612d039631024ea9bf09c424a9503aa078f0` | `Minted(address indexed sender, address indexed recipient, uint256 amount)` | BurnMint (dest) — pools 1.5.0 / 1.5.1 / 1.6.0 |
| `0x696de425f79f4a40bc6d2122ca50507f0efbeabbff86a84871b7196ab8ea8df7` | `Burned(address indexed sender, uint256 amount)` | BurnMint (source) — pools 1.5.0 / 1.5.1 / 1.6.0 |
| `0x2d87480f50083e2b2759522a8fdda59802650a8055e609a7772cf70c07748f52` | `Released(address indexed sender, address indexed recipient, uint256 amount)` | LockRelease / SiloedLockRelease (dest) — pools ≤ 1.6.0 |
| `0x9f1ec8c880f76798e7b793325d625e9b60e4082a553c98f42b6cda368dd60008` | `Locked(address indexed sender, uint256 amount)` | LockRelease / SiloedLockRelease (source) — pools ≤ 1.6.0 |
| `0xf33bc26b4413b0e7f19f1ea739fdf99098c0061f1f87d954b11f5293fad9ae10` | `LockedOrBurned(uint64 indexed remoteChainSelector, address token, address sender, uint256 amount)` | every pool type (source) — pools 1.6.1+, 2.0.0 and some 1.6.0 variants (`HybridWithExternalMinterTokenPool 1.6.0`) |
| `0xfc5e3a5bddc11d92c2dc20fae6f7d5eb989f056be35239f7de7e86150609abc0` | `ReleasedOrMinted(uint64 indexed remoteChainSelector, address token, address sender, address recipient, uint256 amount)` | every pool type (dest) — pools 1.6.1+, 2.0.0 and some 1.6.0 variants |

*(Some pool versions use the 3-arg `Released(address,address,address,uint256)` `0xefb6092a…` / `Locked(address,address,uint256)` `0x989eaa91…` — verify against the deployed pool.)*

In both generations **`sender` is the ramp that called the pool** (the OnRamp on the source, the OffRamp on the destination), not the end user — measured: a Base `Burned` log carries the Base 1.6.0 OnRamp in topic1. The user is `CCIPMessageSent.sender`, and the recipient is `recipient` on the destination. In 2.0.0 pools `LockedOrBurned.amount` is net of the pool fee.

**Rate limits, liquidity and pool admin:**

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x1871cdf8010e63f2eb8384381a68dfa7416dc571a5517e66e88b2d2d0c0a690a` | `TokensConsumed(uint256 tokens)` | RateLimiter, pools ≤ 1.6.0 — fires next to each lock/burn/release/mint |
| `0xff0133389f9bb82d5b9385826160eaf2328039f6fa950eeb8cf0836da8178944` | `OutboundRateLimitConsumed(uint64 indexed remoteChainSelector, address token, uint256 amount)` | pools 1.6.1+ / 2.0.0 (source) |
| `0x50f6fbee3ceedce6b7fd7eaef18244487867e6718aec7208187efb6b7908c14c` | `InboundRateLimitConsumed(uint64 indexed remoteChainSelector, address token, uint256 amount)` | pools 1.6.1+ / 2.0.0 (dest) |
| `0xc17cea59c2955cb181b03393209566960365771dbba9dc3d510180e7cb312088` | `LiquidityAdded(address indexed provider, uint256 indexed amount)` | LockRelease (`ILiquidityContainer`) |
| `0xc2c3f06e49b9f15e7b4af9055e183b0d73362e033ad82a07dec9bf9840171719` | `LiquidityRemoved(address indexed provider, uint256 indexed amount)` | LockRelease — **the rebalancer pulls locked funds out: watch for drains** |
| `0x6fa7abcf1345d1d478e5ea0da6b5f26a90eadb0546ef15ed3833944fbfd1db62` | `LiquidityTransferred(address indexed from, uint256 amount)` | LockRelease pool migration |
| `0x569a440e6842b5e5a7ac02286311855f5a0b81b9390909e552e82aaf02c9e9bf` | `LiquidityAdded(uint64 remoteChainSelector, address indexed provider, uint256 amount)` | SiloedLockRelease |
| `0x58fca2457646a9f47422ab9eb9bff90cef88cd8b8725ab52b1d17baa392d784e` | `LiquidityRemoved(uint64 remoteChainSelector, address indexed remover, uint256 amount)` | SiloedLockRelease — drain watch |
| `0x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62` | `Deposit(address indexed token, address indexed depositor, uint256 amount)` | `ERC20LockBox` 2.0.0 (the liquidity of a 2.0.0 LockRelease pool) |
| `0x2717ead6b9200dd235aad468c9809ea400fe33ac69b5bfaa6d3e90fc922b6398` | `Withdrawal(address indexed token, address indexed recipient, uint256 amount)` | `ERC20LockBox` 2.0.0 |
| `0xdb4d6220746a38cbc5335f7e108f7de80f482f4d23350253dfd0917df75a14bf` | `RemotePoolSet(uint64 indexed remoteChainSelector, bytes previousPoolAddress, bytes remotePoolAddress)` | pools 1.5.x admin — **the trusted remote pool changed** |
| `0x7d628c9a1796743d365ab521a8b2a4686e419b3269919dc9145ea2ce853b54ea` | `RemotePoolAdded(uint64 indexed remoteChainSelector, bytes remotePoolAddress)` | pools 1.6.0+ admin — high severity |
| `0x52d00ee4d9bd51b40168f2afc5848837288ce258784ad914278791464b3f4d76` | `RemotePoolRemoved(uint64 indexed remoteChainSelector, bytes remotePoolAddress)` | pools 1.6.0+ admin |
| `0x5204aec90a3c794d8e90fded8b46ae9c7c552803e7e832e0c1d358396d859916` | `ChainRemoved(uint64 remoteChainSelector)` | admin |
| `0x02dc5c233404867c793b749c6d644beb2277536d18a7e7974d3f238e4c6f1684` | `RouterUpdated(address oldRouter, address newRouter)` | admin (pools ≤ 1.6.0) |
| `0x44676b5284b809a22248eba0da87391d79098be38bb03154be88a58bf4d09174` | `RateLimitAdminSet(address rateLimitAdmin)` | admin (pools 1.6.0) |

### 2.4 FeeQuoter / PriceRegistry

| topic0 | Event |
|--------|-------|
| `0xdd84a3fa9ef9409f550d54d6affec7e9c480c878c6ab27b78912a03e1b371c6e` | `UsdPerUnitGasUpdated(uint64 indexed destChain, uint256 value, uint256 timestamp)` |
| `0x52f50aa6d1a95a4595361ecf953d095f125d442e4673716dede699e049de148a` | `UsdPerTokenUpdated(address indexed token, uint256 value, uint256 timestamp)` |

### 2.5 TokenAdminRegistry and RMN — admin and halt signals

| topic0 | Event | Emitter / notes |
|--------|-------|-----------------|
| `0x754449ec3aff3bd528bfce43ae9319c4a381b67fcd1d20097b3b24dacaecc35d` | `PoolSet(address indexed token, address indexed previousPool, address indexed newPool)` | TokenAdminRegistry (§4.5) — **a token's pool changed: high severity** |
| `0x399b55200f7f639a63d76efe3dcfa9156ce367058d6b673041b84a628885f5a7` | `AdministratorTransferred(address indexed token, address indexed newAdmin)` | TokenAdminRegistry — token admin changed |
| `0x1716e663a90a76d3b6c7e5f680673d1b051454c19c627e184c8daf28f3104f74` | `Cursed(bytes16[] subjects)` | RMNRemote 1.6.0 (behind the chain's ARMProxy) — **lanes halted** |
| `0x0676e709c9cc74fa0519fd78f7c33be0f1b2b0bae0507c724aef7229379c6ba1` | `Uncursed(bytes16[] subjects)` | RMNRemote 1.6.0 |

---

## 3. Function signatures (chain-agnostic)

### 3.1 Router (entrypoint)

`EVM2AnyMessage = (bytes receiver, bytes data, (address token, uint256 amount)[] tokenAmounts, address feeToken, bytes extraArgs)`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x96f4e9f9` | `ccipSend(uint64 destinationChainSelector, (bytes,bytes,(address,uint256)[],address,bytes) message)` → `bytes32 messageId` | `payable` (native fee) or pulls `feeToken`. **Verified present in ETH Router bytecode.** |
| `0x20487ded` | `getFee(uint64 destinationChainSelector, (bytes,bytes,(address,uint256)[],address,bytes) message)` → `uint256 fee` | quote in `feeToken` units |
| `0xa48a9058` | `isChainSupported(uint64 chainSelector)` → `bool` | **Verified present in ETH Router bytecode.** |
| `0xfbca3b74` | `getSupportedTokens(uint64 chainSelector)` → `address[]` | *(deprecated in newer routers; use TokenAdminRegistry)* |
| `0xa8d87a3b` | `getOnRamp(uint64 destChainSelector)` → `address` | lane onRamp |
| `0xa40e69c7` | `getOffRamps()` → `(uint64 sourceChainSelector, address offRamp)[]` | |
| `0x83826b2b` | `isOffRamp(uint64 sourceChainSelector, address offRamp)` → `bool` | |
| `0xe861e907` | `getWrappedNative()` → `address` | |
| `0x181f5a77` | `typeAndVersion()` → e.g. `"Router 1.2.0"` | version oracle |

### 3.2 FeeQuoter (v1.5) / PriceRegistry (v1.2)

| Selector | Signature |
|----------|-----------|
| `0xd02641a0` | `getTokenPrice(address token)` → `(uint224 value, uint32 timestamp)` |
| `0xd8694ccd` | `getValidatedFee(uint64 destChainSelector, (bytes,bytes,(address,uint256)[],address,bytes) message)` → `uint256` |

### 3.3 Ramps, pools and TokenAdminRegistry

`LockOrBurnInV1 = (bytes receiver, uint64 remoteChainSelector, address originalSender, uint256 amount, address localToken)`; `ReleaseOrMintInV1 = (bytes originalSender, uint64 remoteChainSelector, address receiver, uint256 amount, address localToken, bytes sourcePoolAddress, bytes sourcePoolData, bytes offchainTokenData)` (1.5 / 1.6 layout).

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x06285c69` | `getStaticConfig()` | view on every ramp: first word = local chain selector; 1.6.0 OnRamp word 3 = `NonceManager`; ≤1.5 OffRamp word 1 = its `CommitStore`. |
| `0x6def4ce7` | `getDestChainConfig(uint64 destChainSelector)` | view, OnRamp 1.6.0 / 2.0.0 |
| `0x5e36480c` | `getExecutionState(uint64 sourceChainSelector, uint64 sequenceNumber)` | view, OffRamp 1.6.0 |
| `0x142a98fc` | `getExecutionState(uint64 sequenceNumber)` | view, EVM2EVMOffRamp ≤ 1.5 |
| `0x856c8247` | `getSenderNonce(address sender)` | view, EVM2EVMOnRamp ≤ 1.5 |
| `0x9a4575b9` | `lockOrBurn((bytes receiver, uint64 remoteChainSelector, address originalSender, uint256 amount, address localToken) lockOrBurnIn)` | pool, OnRamp-only. Source-leg value movement. (2.0.0 pools keep this overload.) |
| `0x39077537` | `releaseOrMint((bytes originalSender, uint64 remoteChainSelector, address receiver, uint256 amount, address localToken, bytes sourcePoolAddress, bytes sourcePoolData, bytes offchainTokenData) releaseOrMintIn)` | pool, OffRamp-only. Destination-leg value movement. |
| `0x21df0da7` | `getToken()` | view: the pool's token |
| `0xa42a7b8b` | `getRemotePools(uint64 remoteChainSelector)` | view (pools 1.6.0+) |
| `0xc4bffe2b` | `getSupportedChains()` | view |
| `0xeb521a4c` | `provideLiquidity(uint256 amount)` | LockRelease pools. Emits `LiquidityAdded`. |
| `0x0a861f2a` | `withdrawLiquidity(uint256 amount)` | LockRelease pools, rebalancer-only. Emits `LiquidityRemoved`. |
| `0xbbe4f6db` | `getPool(address token)` | view on TokenAdminRegistry: the token's current pool |

---

## 4. Core addresses per chain

### 4.1 Routers (verified live — 11130 B each, same build as Ethereum)

| Chain (id) | Router |
|------------|--------|
| Ethereum (1) | `0x80226fc0Ee2b096224EeAc085Bb9a8cba1146f7D` |
| Base (8453) | `0x881e3A65B4d4a04dD529061dd0071cf975F58bCD` |
| BNB (56) | `0x34B03Cb9086d7D758AC55af71584F81A598759FE` |
| Avalanche (43114) | `0xF4c7E640EdA248ef95972845a62bdC74237805dB` |
| Arbitrum One (42161) | `0x141fa059441E0ca23ce184B6A78bafD2A517DdE8` |
| Optimism (10) | `0x3206695CaE29952f4b0c22a169725a865bc8Ce0f` |
| Polygon PoS (137) | `0x849c5ED5a80F5B408Dd4969b78c2C8fdf0565Bfe` |
| Robinhood Chain (4663) | `0x06fC836cf9839B1cd891C440A0a45242DA6Ae1c9` (10,761 B; `typeAndVersion()` = "Router 1.2.0"; checked 2026-09-29) |

### 4.2 Ethereum support contracts (verified live)

| Contract | Address | Verified |
|----------|---------|----------|
| **ARMProxy / RMN** (Risk Management Network proxy) | `0x411dE17f12D1A34ecC7F45f49844626267c75e81` | ✅ (1452 B) |
| **TokenAdminRegistry** (v1.5) | `0xb22764f98dD05c789929716D677382Df22C05Cb6` | ✅ (5193 B) |
| **RegistryModuleOwnerCustom** | `0x13022e3e6C77524308BD56AEd716E88311b2E533` | ✅ (972 B) |
| **RegistryModuleOwnerCustom 1.6.0** (current in the CCIP Directory) | `0x4855174E9479E211337832E109E7721d43A4CA64` | ✅ (1,432 B; `typeAndVersion()` checked 2026-09-29) |
| **CCIPHome 1.6.0** | `0x76a443768A5e3B8d1AED0105FC250877841Deb40` | CCIP Directory; the same literal is the 1.6.0 **OnRamp** on Arbitrum and Optimism (§4.3) |

> **Per-chain RMN / FeeQuoter / TokenAdminRegistry / lane ramps:** these are network-specific and change with each lane/version. The authoritative live source is the [CCIP Directory](https://docs.chain.link/ccip/directory/mainnet) (JS-rendered — not scrapable via plain fetch). Resolve at runtime: the lane OnRamp is `Router.getOnRamp(destSelector)` (`0xa8d87a3b`); OffRamps via `Router.getOffRamps()` (`0xa40e69c7`); then read the ramp's `getDynamicConfig()` for the FeeQuoter/RMN it uses. **Only the addresses explicitly marked verified above were bytecode-checked; do not assume the Ethereum support addresses carry to other chains.**

### 4.3 Ramps per chain — 1.6.0 and 2.0.0 (one of each per chain, all lanes)

From the CCIP Directory `lanes.json` (2026-09-29); every address has code and the listed `typeAndVersion()` (§7). The **2.0.0** pair serves every lane between two target chains (Robinhood Chain: lanes to Ethereum, Base, Arbitrum and BNB among the targets); the **1.6.0** pair serves lanes to other chains.

| Chain | OnRamp 2.0.0 | OffRamp 2.0.0 | OnRamp 1.6.0 | OffRamp 1.6.0 |
|-------|--------------|---------------|--------------|---------------|
| Ethereum | `0xc3423F3FB30857D9C14717b119884b1B63d250b7` | `0x408428bca0e24A25ac8baAc1b70f64AF257717c3` | `0x913814782144864e523C3FdB78E3ca25D2c2aeCa` | `0x26d3681DfC9E4c8C79cfbf461adec8A21d5d73C5` |
| Base | `0xF75bf16b03aaE98677926F0987F195A2153996B9` | `0x16E577f1724AE2598F9b43a52C19E6f67eE13808` | `0xee85aEfb15b9489563A6a29891ebe0750AA1A7Ae` | `0xf09AFe78d3c7d359b334d7cB88995751F7eC5E13` |
| Arbitrum One | `0x7B73923E101950eFe098C2Eca74C8320b2813f48` | `0xD4ad79ed3372460F1e63Feb8fC41C3b757198C6e` | `0x76a443768A5e3B8d1AED0105FC250877841Deb40` | `0xee85aEfb15b9489563A6a29891ebe0750AA1A7Ae` |
| Optimism | `0xcBfaAbCb95358817d2FE859f1ca223Cf83FaE199` | `0x4Ef20b2071ecc7653d5Ba12e758383d1542cFD90` | `0x76a443768A5e3B8d1AED0105FC250877841Deb40` | `0xee85aEfb15b9489563A6a29891ebe0750AA1A7Ae` |
| Polygon PoS | `0x7b8C563e2b29c2D194Bc8D18092684420aa47bBE` | `0xbb1E3552baDC3498638D20D0b6903aFc432c7253` | `0x530Ae314EC3fA038bd9A215095E37295ec76162a` | `0x77FDbd20ED582794b1d9F1a8a94e4a60494D677e` |
| BNB | `0x84a0797B31Ac0d3E1D06157663dd4b18cFFdA188` | `0x4914044f8d787bd5DC7528f00775D850dC54477e` | `0xf09AFe78d3c7d359b334d7cB88995751F7eC5E13` | `0xA27056438FfA1f286AB197488808692F0db93F8B` |
| Avalanche | `0xa556c22b7F73A15963813a9a0fDBA50f44fe5cf9` | `0x65D04D8dA1405b50d3508aaF94e1B6F5f1A3895C` | `0x02A4D69cFfeC00Fbf7F3B60c93e3529Dfc58894d` | `0xe72d25aDd538E8ef9CeF85622eA8912a6CB98Be6` |
| Robinhood Chain | `0xE86CeddDAEfa1999AaE234C056B51877BFfBD73f` | `0x5060De90b723a7Eb705742Ff1a22a908b1D8b626` | `0xe72d25aDd538E8ef9CeF85622eA8912a6CB98Be6` | `0xcDca5D374e46A6DDDab50bD2D9acB8c796eC35C3` |

**Cross-chain address reuse with different roles:** `0xee85aEfb15b9489563A6a29891ebe0750AA1A7Ae` is the 1.6.0 OnRamp on Base but the 1.6.0 OffRamp on Arbitrum and Optimism; `0xf09AFe78d3c7d359b334d7cB88995751F7eC5E13` is the 1.6.0 OffRamp on Base but the 1.6.0 OnRamp on BNB; `0xe72d25aDd538E8ef9CeF85622eA8912a6CB98Be6` is the 1.6.0 OffRamp on Avalanche but the 1.6.0 OnRamp on Robinhood Chain; `0x76a443768A5e3B8d1AED0105FC250877841Deb40` is CCIPHome on Ethereum and the 1.6.0 OnRamp on Arbitrum and Optimism. Key every ramp on `(chainId, address)`.

Router wiring read live: `getOnRamp(Base)` and `getOnRamp(Robinhood Chain)` on the Ethereum Router return the Ethereum 2.0.0 OnRamp; `getOnRamp(Ethereum)` on the Robinhood Router returns the Robinhood 2.0.0 OnRamp. The 2.0.0 message fee moves in the send transaction from the OnRamp to `0x6608d995bBDE874De5292bFD289643c88D176ED3` (`typeAndVersion()` = "Proxy 2.0.0"; the same literal on Ethereum and Robinhood Chain).

### 4.4 Legacy EVM2EVM ramps of the Ethereum ↔ Base lane (1.2.0 / 1.5.0)

This lane now runs on the 2.0.0 ramps (§4.3). The per-lane contracts below are still deployed; they emitted no event in the pinned window 2026-09-28 00:00–12:00 UTC. `typeAndVersion()` and `getStaticConfig()` read live on 2026-09-29 (the static config links each OffRamp to its CommitStore, its source OnRamp and its predecessor).

| Chain | Contract | Address | Wiring (`getStaticConfig`) |
|-------|----------|---------|----------------------------|
| Ethereum | EVM2EVMOnRamp 1.2.0 (→ Base) | `0xe2c2ab221aa0b957805f229d2aa57fbe2f4dadf7` | dest selector = Base |
| Ethereum | EVM2EVMOnRamp 1.5.0 (→ Base) | `0xb8a882f3b88bd52d1ff56a873bfdb84b70431937` | `prevOnRamp` = the 1.2.0 OnRamp; TokenAdminRegistry `0xb22764f98dD05c789929716D677382Df22C05Cb6` |
| Ethereum | EVM2EVMOffRamp 1.2.0 (← Base) | `0xdf85c8381954694e74abd07488f452b4c2cddfb3` | CommitStore 1.2.0 `0x8dc27d621c41a32140e22e2a4daf1259639bae04`; source OnRamp = Base 1.2.0 |
| Ethereum | EVM2EVMOffRamp 1.5.0 (← Base) | `0x6b4b6359dd5b47cdb030e5921456d2a0625a9ebd` | CommitStore 1.5.0 `0xdac3a82cc5e7c137bf28e6ef4f68f29d66205ffe`; source OnRamp = Base 1.5.0; `prevOffRamp` = the 1.2.0 OffRamp |
| Base | EVM2EVMOnRamp 1.2.0 (→ Ethereum) | `0xdea286dc0e01cb4755650a6cf8d1076b454ea1cb` | dest selector = Ethereum |
| Base | EVM2EVMOnRamp 1.5.0 (→ Ethereum) | `0x56b30a0dcd8dc87ec08b80fa09502bab801fa78e` | `prevOnRamp` = the 1.2.0 OnRamp; TokenAdminRegistry `0x6f6C373d09C07425BaAE72317863d7F6bb731e37` |
| Base | EVM2EVMOffRamp 1.2.0 (← Ethereum) | `0xec0cfe335a4d53dba70cb650ab56eec32788f0bb` | CommitStore 1.2.0 `0x0ae3c2c7fb789bd05a450cd3075d11f6c2ca4f77`; source OnRamp = Ethereum 1.2.0 |
| Base | EVM2EVMOffRamp 1.5.0 (← Ethereum) | `0xca04169671a81e4fb8768cfad46c347ae65371f1` | CommitStore 1.5.0 `0xb40659aacb709d1d54c80fc0d38b15705358ce0b`; source OnRamp = Ethereum 1.5.0; `prevOffRamp` = the 1.2.0 OffRamp |

Last CommitStore activity seen through the Blockscout API: Ethereum CommitStore 1.5.0 at block 25,044,081, CommitStore 1.2.0 at block 21,184,007. Other 1.5.0 lanes stay live: in the pinned window the BNB→Base EVM2EVMOffRamp 1.5.0 `0x45d524b6fe99c005c52c65c578dc0e02d9751083` emitted 4 `ExecutionStateChanged`, and the Ethereum EVM2EVMOnRamp 1.5.0 `0x8469b5abd81987f9347c0babd47b9eb11da7d0df` emitted 1 `CCIPSendRequested`.

### 4.5 Support contracts per chain

From the CCIP Directory `chains.json`; each existence-checked with `eth_getCode` and `typeAndVersion()` on 2026-09-29.

| Chain | ARMProxy 1.0.0 | TokenAdminRegistry 1.5.0 | RegistryModuleOwnerCustom 1.6.0 | TokenPoolFactory 2.0.0 |
|-------|----------------|--------------------------|--------------------------------|------------------------|
| Ethereum | `0x411dE17f12D1A34ecC7F45f49844626267c75e81` | `0xb22764f98dD05c789929716D677382Df22C05Cb6` | `0x4855174E9479E211337832E109E7721d43A4CA64` | `0x3d8E30F9d31316C2870d93FAc6bDBF5deE23A274` |
| Base | `0xC842c69d54F83170C42C4d556B4F6B2ca53Dd3E8` | `0x6f6C373d09C07425BaAE72317863d7F6bb731e37` | `0xAFEd606Bd2CAb6983fC6F10167c98aaC2173D77f` | `0x8cE19F73e85a68490e08c89b510215Ca71B0F2B8` |
| Arbitrum One | `0xC311a21e6fEf769344EB1515588B9d535662a145` | `0x39AE1032cF4B334a1Ed41cdD0833bdD7c7E7751E` | `0x1f1df9f7fc939E71819F766978d8F900B816761b` | `0x5c4b24A9c8B840399611f707bAaF1B1343054dE9` |
| Optimism | `0x55b3FCa23EdDd28b1f5B4a3C7975f63EFd2d06CE` | `0x657c42abE4CD8aa731Aec322f871B5b90cf6274F` | `0xAFEd606Bd2CAb6983fC6F10167c98aaC2173D77f` | `0x22c728125dba77774260B9c4968608513CD19112` |
| Polygon PoS | `0xf1ceAa46D8d13Cac9fC38aaEF3d3d14754C5A9c2` | `0x00F027eA6D0fb03256A15E9182B2B9227A4931d8` | `0xc751E86208F0F8aF2d5CD0e29716cA7AD98B5eF5` | `0x170dC4442624D564D357B9F8f2B0f67e6308ef3e` |
| BNB | `0x9e09697842194f77d315E0907F1Bda77922e8f84` | `0x736Fd8660c443547a85e4Eaf70A49C1b7Bb008fc` | `0x47Db76c9c97F4bcFd54D8872FDb848Cab696092d` | `0xa0c6066147a30348102A582D8D2513fEdB8B0a91` |
| Avalanche | `0xcBD48A8eB077381c3c4Eb36b402d7283aB2b11Bc` | `0xc8df5D618c6a59Cc6A311E96a39450381001464F` | `0x76Aa17dCda9E8529149E76e9ffaE4aD1C4AD701B` | `0x172f94f347c6762C9bf21ABb90eA6683CB90fc96` |
| Robinhood Chain | `0xe8464c353210Cc398A45dB2454FBc5BCd25fFf20` | `0x1912C3cFafE8A76A32a92861d815aC2837F237Ca` | `0x3237c0D7B58BEc8Dc17F00103B784Bd6678f789E` | `0x614B367841ec854994706f06AAB4aA2C80Fe06D9` |

`RegistryModuleOwnerCustom` `0xAFEd606Bd2CAb6983fC6F10167c98aaC2173D77f` is the same literal on Base and Optimism.

### 4.6 Token pools of note (per chain)

Pools that moved value in the pinned window 2026-09-28 00:00–12:00 UTC, matched to tokens through the CCIP Directory `tokens.json`; `typeAndVersion()` and `getToken()` read live on 2026-09-29. Counts = logs of the pool's source / destination event in the window; "—" = the pool was not among the 12 busiest emitters of that event on the chain (not counted). The Directory lists 208 pools on Ethereum, 150 on Base, 94 on Arbitrum, 30 on Optimism, 42 on Polygon, 100 on BNB, 46 on Avalanche and 18 on Robinhood Chain.

| Chain | Token | Pool | `typeAndVersion()` | Source / dest events in window |
|-------|-------|------|--------------------|--------------------------------|
| Ethereum | GHO | `0x06179f7c1be40863405f374e7f5f8806c728660a` | LockReleaseTokenPool 1.5.1 (EIP-1967 proxy → `0x2ce400703dacc37b7edfa99d228b8e70a4d3831b`) | `Locked` 21 / `Released` 19 |
| Ethereum | WETH | `0x011ef1fe26d20077a59f38e9ad155b166ad87d40` | SiloedLockReleaseTokenPool 1.6.0 | `Locked` 10 / `Released` 3 |
| Ethereum | LINK | `0x1b7492c3bd23a4adb448710e4275ff14a5288932` | LockReleaseTokenPool 1.5.1 | `Locked` 6 / `Released` 3 |
| Ethereum | syrupUSDC | `0x20b79d39bd44deee4f89b1e9d0e3b945fde06491` | LockReleaseTokenPool 1.5.1 | `Locked` 8 / `Released` 2 |
| Ethereum | DIP | `0xac3453eef710e1e6457383f29d696db5435bf95b` | LockReleaseTokenPoolAndProxy 1.5.0 | `Locked` 9 / `Released` 3 |
| Ethereum | WPROS | `0x6f0c4c3f0f1ca8f0513b542a124a0208fee72d97` | BurnMintTokenPool 1.6.1 | `LockedOrBurned` 8 / `ReleasedOrMinted` 4 |
| Ethereum | FLOCK | `0x05e42e03996379cd0b6290cc2767a1bdd78b737a` | BurnMintTokenPool 1.6.1 | 7 / 13 |
| Ethereum | USD1 | `0x36a72ed0096b414521c45e3ddc9ed657d1d9c141` | HybridWithExternalMinterTokenPool 1.6.0 | `LockedOrBurned` 5 / — |
| Ethereum | USDC | `0x806489226179d519d7bf5814ba8ea0f7d850acf2` | CCTPThroughCCVTokenPool 2.0.0 (token = native USDC) | 2 / 26 |
| Ethereum | TRUF | `0x7134dc364fb6b9585a1320a4d7b4215ca52ff0b1` | LockReleaseTokenPool 2.0.0; liquidity in `ERC20LockBox 2.0.0` `0x4d4522a30673a6b1dfa70b1bed60f778eb542f6b` | 0 / 1 |
| Ethereum | CHEX | `0xaf819a87231cf522f1e2b2965acdbc436c737c98` | BurnMintTokenPool 1.5.1 | — / `Minted` 27 |
| Ethereum | BTR | `0xc78210649af8a450c0f6e98107a0b614a3198359` | BurnMintTokenPool 1.5.0 | `Burned` 7 / `Minted` 2 |
| Base | CHEX | `0x1c01171761a94538377fd0fda230ec921274df47` | BurnMintTokenPool 1.5.1 | `Burned` 27 / — |
| Base | GHO | `0x98217a06721ebf727f2c8d9ad7718ec28b7aae34` | BurnMintTokenPool 1.5.1 (EIP-1967 proxy → `0x06179f7c1be40863405f374e7f5f8806c728660a`, the Ethereum GHO pool's literal) | — / `Minted` 5 |
| Base | LINK | `0xba148baf60ccc4d7d86aed4fcff04d5b3265cad4` | BurnMintTokenPool 1.5.1 | — / `Minted` 3 |
| Base | WPROS | `0x7126c3fef4e6a680eee09fb039b2236f638384b0` | BurnMintTokenPool 1.6.1 | 5 / 5 |
| Base | FLOCK | `0xcbdf4be5195636e39fc3d2b5c42f443471e8d026` | LockReleaseTokenPool 1.6.1 | 78 / 18 |
| Base | QUICK | `0xf7c2dbff4dfec28eaf52caac8fda22fba19199ce` | LockReleaseTokenPool 1.6.1 | — / 37 |
| Base | cbBTC | `0x93cf6f19fdd01c8c240651357193e25abf41523a` | LockReleaseTokenPool 1.6.1 | 8 / 17 |
| Base | YNE | `0xd8f5e7fac317c638d2fe4d07ab3f436ca6b5e5c7` | BurnMintTokenPool 1.5.1 | `Burned` 40 / — |
| Base | ZEST | `0xb2ff0dbe1fda1bc4323bbde5ab8f0cfd4fc7dee7` | BurnMintTokenPool 1.5.1 | `Burned` 5 / `Minted` 45 |
| Base | VIRTUAL | `0x06763d2b1acaef69f4378b73a0ca41ce79606a1f` | LockReleaseTokenPool 1.5.1 | `Locked` 11 / `Released` 8 |
| Arbitrum One | GHO | `0xb94ab28c6869466a46a42aba834ca2b3cecca5eb` | BurnMintTokenPool 1.5.1 (EIP-1967 proxy → `0x6e637e1e48025e51315d50ab96d5b3be1971a715`) | `Burned` 9 / `Minted` 18 |
| Optimism | ZCHF | `0x7cbac118b3f299f8be1c3dba66368d96b37d7743` | BurnMintTokenPool 1.5.1 | `Burned` 2 / — |
| Polygon PoS | QUICK | `0x8d89611841d3389711ea3c74538f953f8dffa427` | LockReleaseTokenPool 1.6.1 (Directory) | 36 / — |
| BNB | ZEST | `0x82e689cec1f20fa5c909c91c1161003f23667918` | LockReleaseTokenPool 1.5.1 | `Locked` 50 / `Released` 4 |
| BNB | FLOCK | `0x05e42e03996379cd0b6290cc2767a1bdd78b737a` | BurnMintTokenPool 1.6.1 | 1 / 6 |
| BNB | BTR | `0x86248be697645cfe0fdeb37fba0102604f355efa` | BurnMintTokenPool 1.5.0 | `Burned` 2 / `Minted` 10 |
| Avalanche | GHO | `0xde6539018b095353a40753dc54c91c68c9487d4e` | BurnMintTokenPool 1.5.1 (EIP-1967 proxy → `0xb77e872a68c62cfc0dfb02c067ecc3da23b4bbf3`) | `Burned` 3 / — |

The FLOCK pool `0x05e42e03996379cd0b6290cc2767a1bdd78b737a` has the same literal on Ethereum, BNB and Robinhood Chain (BurnMint 1.6.1 on all three), while the Base FLOCK pool is a LockRelease pool at another address.

### 4.7 Robinhood Chain (chain ID 4663) — CCIP deployed

The CCIP Directory lists `robinhood-mainnet` (chain selector `6180753054346818345`; fee tokens LINK and WETH `0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73`). Every contract below has code on `https://rpc.mainnet.chain.robinhood.com` and the listed `typeAndVersion()` (2026-09-29).

| Role | Address |
|------|---------|
| **Router** (Router 1.2.0) | `0x06fC836cf9839B1cd891C440A0a45242DA6Ae1c9` |
| **OnRamp 2.0.0** (7 lanes, among them Ethereum, Base, Arbitrum and BNB) | `0xE86CeddDAEfa1999AaE234C056B51877BFfBD73f` |
| **OffRamp 2.0.0** | `0x5060De90b723a7Eb705742Ff1a22a908b1D8b626` |
| OnRamp 1.6.0 (1 lane) | `0xe72d25aDd538E8ef9CeF85622eA8912a6CB98Be6` |
| OffRamp 1.6.0 | `0xcDca5D374e46A6DDDab50bD2D9acB8c796eC35C3` |
| NonceManager 1.6.0 (word 3 of the 1.6.0 OnRamp static config) | `0xc23071a8ae83671f37bda1dadbc745a9780f632a` |
| ARMProxy 1.0.0 | `0xe8464c353210Cc398A45dB2454FBc5BCd25fFf20` |
| TokenAdminRegistry 1.5.0 | `0x1912C3cFafE8A76A32a92861d815aC2837F237Ca` |
| RegistryModuleOwnerCustom 1.6.0 | `0x3237c0D7B58BEc8Dc17F00103B784Bd6678f789E` |
| TokenPoolFactory 2.0.0 | `0x614B367841ec854994706f06AAB4aA2C80Fe06D9` |

Token pools (all burn-and-mint; Directory `tokens.json`):

| Token | Token address | Pool | Version | Window (source / dest) |
|-------|---------------|------|---------|------------------------|
| FLOCK | `0x5aB3D4c385B400F3aBB49e80DE2fAF6a88A7B691` | `0x05E42e03996379cd0B6290cC2767A1BDd78B737a` | BurnMintTokenPool 1.6.1 | `LockedOrBurned` 8 / `ReleasedOrMinted` 60 |
| VIRTUAL | `0xc6911796042b15d7Fa4F6CDe69e245DdCd3d9c31` | `0x78680385fcb8187ac1b28E0d6b1e0ACf5e0d0992` | BurnMintTokenPool 1.6.1 | 5 / 1 |
| cbBTC | `0xCEC185eB182c47d1bA1EFc84e6959e18cd620Be4` | `0x402430ca607c52a99Aa82AB4C726001D4203C9e7` | BurnMintTokenPool 1.6.1 | 3 / 6 |
| syrupUSDC | `0xC6a4854eeB493224d5f9485E12Dd3A81f22EEE14` | `0x50056397CF6ccF50D1748e95c32EC361951ee6F9` | BurnMintTokenPool 1.6.1 | — |
| syrupUSDG | `0x40858070814a57FdF33a613ae84fE0a8b4a874f7` | `0x01FA676ECC8662E6923fdF06bA5278A96ccD725c` | BurnMintTokenPool 1.6.1 | — |
| wstETH | `0x2dC99af320BC317c567f24eE95811dcbd5983DfD` | `0x1c2F528e3BEeFF81Bc03CC63E64dB131d18be7fA` | BurnMintTokenPool 1.6.1 | — |
| USDUC | `0xBbb8Ef3181661512CEAB66e0B213C29211B24b6c` | `0x8287C5cFF1eAFf9802012840f55edDe7783aa6BD` | BurnMintTokenPool 2.0.0 | — |
| W0G | `0x32003CC8357938bCF615c1222a349c58f2B30698` | `0x5B6fc9601AeF9805579E8Ae559CD9Ab61a557649` | BurnMintTokenPool 1.5.1 | `Burned` 26 / `Minted` 12 |
| TAO | `0xf3081494B87e8D5fb7960f066E931D1D0e6E3d67` | `0xF5AC6D6Bd12d8b87dE3c136FAc9375961577e794` | BurnMintTokenPool 1.5.1 | `Burned` 1 / `Minted` 47 |
| NPC | `0x241F3Caad03Db31137F641beF005A32176530024` | `0x665AA13B440212ddA704f76624f5CD246eFc0361` | BurnMintTokenPool 1.5.1 | — / `Minted` 1 |
| LINK | `0x492641F648a4986844848E0beFE66D14817bCE34` | `0x3201a20D2a33820C0DaC8Bc93C4819755C2a8c7F` | BurnMintTokenPool 1.5.1 | — |
| BWLK | `0x8b7dAF8ca650Ab30dF4c686e1E3689E9248732C6` | `0xCFae9bE1c5693AB26560c84B30489f3946363b41` | BurnMintTokenPool 1.5.1 | — |
| GREEN | `0x355bB7F0f6c730e4460d620420a300fa08FF82F3` | `0x4B19f165Bb1Ce3f19Bbe828D150706B9deeEeC95` | BurnMintTokenPool 1.5.1 | — |
| RIPE | `0x4D3f37a965b21aB4122e92Dd41D2693E742c883b` | `0xE51aF1311832818A6D366081Fc535CA56357a6EE` | BurnMintTokenPool 1.5.1 | — |
| SPX | `0x8D1c258C76c87559078bb3b2B77a1f9C41f58eEB` | `0x071C19fEc04DBA83F2E4bEE77D0e38fED84E2197` | BurnMintTokenPool 1.5.1 | — |
| VOOI | `0xB47E8ad95ca1e0bA1C76768FE0F109D82B5fDCC4` | `0xc95209823Cfc5b30DD24CFE45cd4B732DbC226cD` | BurnMintTokenPool 1.5.1 | — |
| SDM | `0x764A7cfe40984180c55554D9A1Cfb341D1BD0CF3` | `0x5efA4982240E8cEEbffB4bdec7c9022cF42386B4` | BurnMintTokenPool 1.5.0 | — |

Measured in the pinned window on Robinhood Chain: `CCIPMessageSent` 2.0.0 = 43 and 1.6.0 = 2; `ExecutionStateChanged` 2.0.0 = 127; `CommitReportAccepted` = 656 on the 1.6.0 OffRamp; Router `MessageExecuted` = 0 (the reason was not checked message by message; on Ethereum, too, `MessageExecuted` (107) is fewer than the 2.0.0 `ExecutionStateChanged` (209)). Sample send (tx `0xaf809818093a88079575d9cffbc5ee05e016ae6eb87c4cfbcce89e265f8357d3`): a router contract swaps into VIRTUAL, the Router wraps the native fee into WETH, the VIRTUAL pool burns (`Transfer` to `0x0`) and emits `LockedOrBurned` for Base, and the 2.0.0 OnRamp emits `CCIPMessageSent`. **Collision on Robinhood Chain:** `Released(address,address,uint256)` came 177 times from `0x37e99e88ca9a49886bf9fa2b489d90f52fba095b`, which is not a CCIP pool in the Directory.

### 4.8 Cross-chain summary

| Chain | ID | CCIP chain selector | Router | 2.0.0 ramps | 1.6.0 ramps | Directory pools |
|-------|----|---------------------|--------|-------------|-------------|-----------------|
| Ethereum | 1 | `5009297550715157269` | `0x80226fc0Ee2b096224EeAc085Bb9a8cba1146f7D` | ✅ | ✅ | 208 |
| Base | 8453 | `15971525489660198786` | `0x881e3A65B4d4a04dD529061dd0071cf975F58bCD` | ✅ | ✅ | 150 |
| Arbitrum One | 42161 | `4949039107694359620` | `0x141fa059441E0ca23ce184B6A78bafD2A517DdE8` | ✅ | ✅ | 94 |
| Optimism | 10 | `3734403246176062136` | `0x3206695CaE29952f4b0c22a169725a865bc8Ce0f` | ✅ | ✅ | 30 |
| Polygon PoS | 137 | `4051577828743386545` | `0x849c5ED5a80F5B408Dd4969b78c2C8fdf0565Bfe` | ✅ | ✅ | 42 |
| BNB | 56 | `11344663589394136015` | `0x34B03Cb9086d7D758AC55af71584F81A598759FE` | ✅ | ✅ | 100 |
| Avalanche | 43114 | `6433500567565415381` | `0xF4c7E640EdA248ef95972845a62bdC74237805dB` | ✅ | ✅ | 46 |
| Robinhood Chain | 4663 | `6180753054346818345` | `0x06fC836cf9839B1cd891C440A0a45242DA6Ae1c9` | ✅ | ✅ | 18 |

The Router, ARMProxy and TokenAdminRegistry are chain-specific; only a few literals repeat across chains (§4.3, §4.5, §4.6), and a repeated literal can hold a different role.

### 4.9 Proxies

The Router, OnRamps, OffRamps, CommitStores, TokenAdminRegistry, RegistryModuleOwnerCustom and TokenPoolFactory are plain contracts: `eth_getCode` shows full runtime code and the EIP-1967 implementation slot is empty (2026-09-29). New versions are deployed side by side and wired in through the Router (`OnRampSet`, `OffRampAdded`, `OffRampRemoved`). Some token pools are EIP-1967 proxies: the GHO pools (Ethereum `0x06179f7c1be40863405f374e7f5f8806c728660a`, Base `0x98217a06721ebf727f2c8d9ad7718ec28b7aae34`, Arbitrum `0xb94ab28c6869466a46a42aba834ca2b3cecca5eb`, Avalanche `0xde6539018b095353a40753dc54c91c68c9487d4e`); watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` on them. The 2.0.0 fee recipient `0x6608d995bBDE874De5292bFD289643c88D176ED3` reports "Proxy 2.0.0".

---

## 5. Detection invariants & gotchas

1. **Use the chain selector, never the EVM chain ID** for any CCIP lane logic. The mapping in §1 is the only correct bridge.
2. **`messageId` is the cross-chain join key.** A send on the source and its `ExecutionStateChanged`/`MessageExecuted` on the destination share the same `bytes32 messageId`. Sequence numbers are per-lane and not globally unique.
3. **`ExecutionStateChanged.state`**: 2 = Success, 3 = Failure. A `Failure` still means the message was delivered/consumed — it won't be retried automatically unless it's a manual-exec recoverable failure.
4. **Three `ExecutionStateChanged` shapes** (≤v1.5, 1.6.0, 2.0.0) → three topic0s (§2.2). Match by OffRamp version; on lanes between target chains the 2.0.0 shape `0x8c324ce1367b83031769f6a813e3bb4c117aba2185789d66b98b791405be6df2` carries almost all executions.
5. **The send-side event has three version-specific shapes** (§2.2): 2.0.0 `CCIPMessageSent` `0x371bc2ff0a006f4ef863b1d27a065d4e9f938b6d883eb154572b4aea593b32cc` (indexed `destChainSelector`, `sender`, `messageId`), 1.6.0 `CCIPMessageSent` `0x192442a2b2adb6a7948f097023cb6b57d29d3a7a5dd33e6666d33c39cc456f32`, ≤1.5 `CCIPSendRequested` `0xd0c3c799bf9e2639de44391e7f524d229b2b55f5b1ea94b2bf7da42f7243dddd`. All three were recomputed from source and matched live logs. Key on `messageId`.
6. **Router is stable; ramps are not.** `Router.getOnRamp`/`getOffRamps` reflect the *current* lane contracts; historical messages may have used now-decommissioned ramps. For historical scans, collect ramp addresses from `OnRampSet`/`OffRampAdded` events on the Router.
7. **Fee token can be LINK or the wrapped-native** (or native via `msg.value`); `getFee` returns the amount in the chosen `feeToken`. Watch the `feeToken` field, not just LINK.
8. **RMN (Risk Management Network)** can "curse" a lane, halting it — monitor the ARMProxy if you depend on liveness.
9. **The value moves at the pool, the message at the ramp.** Source tx: the user (or an app) calls `Router.ccipSend`; the fee moves (native → wrapped, then to the OnRamp, then, for 2.0.0, to the fee proxy `0x6608d995bBDE874De5292bFD289643c88D176ED3`); the pool locks (`Transfer` user → pool) or burns (`Transfer` → `0x0`) and emits `Locked`/`Burned` or `LockedOrBurned`; the OnRamp emits the send event. Destination tx: the OffRamp executes, the pool releases or mints to the receiver and emits `Released`/`Minted` or `ReleasedOrMinted`, the OffRamp emits `ExecutionStateChanged`. A message with no tokens has no pool event.
10. **Pool `sender` is the ramp, not the user** (§2.3). Attribute the source to `CCIPMessageSent.sender` (2.0.0 topic2) or the struct `sender` (1.6.0 / ≤1.5); attribute the payout to the pool event's `recipient`.
11. **Pool event names collide with unrelated contracts.** `Burned(address,uint256)`, `Minted(address,address,uint256)`, `Locked(address,uint256)` and `Released(address,address,uint256)` are common names: in the pinned window non-CCIP emitters produced most of them (for example 177 `Released` logs on Robinhood Chain from `0x37e99e88ca9a49886bf9fa2b489d90f52fba095b`, not a CCIP pool). Filter pool events by the pool addresses of the Directory or `TokenAdminRegistry.getPool`, never by topic alone. `LockedOrBurned`/`ReleasedOrMinted` carry the `remoteChainSelector` and are CCIP-specific in practice.
12. **Large transfers and drains:** alert on pool `LockedOrBurned`/`Locked`/`Burned` above a threshold, on `LiquidityRemoved` and lockbox `Withdrawal` (liquidity leaves a lock pool without a message), on `PoolSet` and `RemotePoolAdded`/`RemotePoolSet` (a pool or its trusted remote changed), on `RootRemoved`, and on `Cursed`.
13. **Refund and failure path:** CCIP has no automatic refund. A failed execution (`state` = 3) stays on the destination and is retried by manual execution; the tokens stay locked or burned on the source until then.
14. **Robinhood Chain is a live CCIP chain** (§4.7): selector `6180753054346818345`, 2.0.0 lanes to Ethereum, Base, Arbitrum and BNB, 18 burn-and-mint pools. Key it on its own Router and ramps; several of its literals hold other roles on other chains (§4.3).

---

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- chain selectors (uint64, decimal — store as numeric, shown here for reference)
-- ETH 5009297550715157269 | BASE 15971525489660198786 | BNB 11344663589394136015
-- AVAX 6433500567565415381 | ARB 4949039107694359620 | OP 3734403246176062136 | POL 4051577828743386545
-- RH (Robinhood Chain) 6180753054346818345

-- topics
ROUTER_MESSAGE_EXECUTED   = '\x9b877de93ea9895756e337442c657f95a34fc68e7eb988bdfa693d5be83016b6'
ROUTER_OFFRAMP_ADDED      = '\xa4bdf64ebdf3316320601a081916a75aa144bcef6c4beeb0e9fb1982cacc6b94'
ROUTER_ONRAMP_SET         = '\x1f7d0ec248b80e5c0dde0ee531c4fc8fdb6ce9a2b3d90f560c74acd6a7202f23'
EXEC_STATE_CHANGED_V15    = '\xd4f851956a5d67c3997d1c9205045fef79bae2947fdee7e9e2641abc7391ef65'
EXEC_STATE_CHANGED_V16    = '\x05665fe9ad095383d018353f4cbcba77e84db27dd215081bbf7cdf9ae6fbe48b'
COMMIT_REPORT_ACCEPTED_V15= '\x291698c01aa71f912280535d88a00d2c59fb63530a3f5d0098560468acb9ebf5'   -- CommitStore ReportAccepted, recomputed and seen live
USD_PER_UNIT_GAS_UPDATED  = '\xdd84a3fa9ef9409f550d54d6affec7e9c480c878c6ab27b78912a03e1b371c6e'
POOL_BURNED               = '\x696de425f79f4a40bc6d2122ca50507f0efbeabbff86a84871b7196ab8ea8df7'
POOL_MINTED               = '\x9d228d69b5fdb8d273a2336f8fb8612d039631024ea9bf09c424a9503aa078f0'
TOPIC_CCIP_MESSAGE_SENT_V2      = '\x371bc2ff0a006f4ef863b1d27a065d4e9f938b6d883eb154572b4aea593b32cc'
TOPIC_CCIP_MESSAGE_SENT_V16     = '\x192442a2b2adb6a7948f097023cb6b57d29d3a7a5dd33e6666d33c39cc456f32'
TOPIC_CCIP_SEND_REQUESTED_V15   = '\xd0c3c799bf9e2639de44391e7f524d229b2b55f5b1ea94b2bf7da42f7243dddd'
TOPIC_EXEC_STATE_CHANGED_V2     = '\x8c324ce1367b83031769f6a813e3bb4c117aba2185789d66b98b791405be6df2'
TOPIC_COMMIT_REPORT_ACCEPTED_V16= '\xb967c9b9e1b7af9a61ca71ff00e9f5b89ec6f2e268de8dacf12f0de8e51f3e47'
TOPIC_OCR3_TRANSMITTED          = '\x198d6990ef96613a9026203077e422916918b03ff47f0be6bee7b02d8e139ef0'
TOPIC_POOL_LOCKED               = '\x9f1ec8c880f76798e7b793325d625e9b60e4082a553c98f42b6cda368dd60008'
TOPIC_POOL_RELEASED             = '\x2d87480f50083e2b2759522a8fdda59802650a8055e609a7772cf70c07748f52'
TOPIC_POOL_LOCKED_OR_BURNED     = '\xf33bc26b4413b0e7f19f1ea739fdf99098c0061f1f87d954b11f5293fad9ae10'
TOPIC_POOL_RELEASED_OR_MINTED   = '\xfc5e3a5bddc11d92c2dc20fae6f7d5eb989f056be35239f7de7e86150609abc0'
TOPIC_POOL_LIQUIDITY_REMOVED    = '\xc2c3f06e49b9f15e7b4af9055e183b0d73362e033ad82a07dec9bf9840171719'
TOPIC_SILOED_LIQUIDITY_REMOVED  = '\x58fca2457646a9f47422ab9eb9bff90cef88cd8b8725ab52b1d17baa392d784e'
TOPIC_LOCKBOX_WITHDRAWAL        = '\x2717ead6b9200dd235aad468c9809ea400fe33ac69b5bfaa6d3e90fc922b6398'
TOPIC_POOL_REMOTE_POOL_ADDED    = '\x7d628c9a1796743d365ab521a8b2a4686e419b3269919dc9145ea2ce853b54ea'
TOPIC_POOL_REMOTE_POOL_SET      = '\xdb4d6220746a38cbc5335f7e108f7de80f482f4d23350253dfd0917df75a14bf'
TOPIC_TAR_POOL_SET              = '\x754449ec3aff3bd528bfce43ae9319c4a381b67fcd1d20097b3b24dacaecc35d'
TOPIC_RMN_CURSED                = '\x1716e663a90a76d3b6c7e5f680673d1b051454c19c627e184c8daf28f3104f74'
TOPIC_OFFRAMP_ROOT_REMOVED      = '\x202f1139a3e334b6056064c0e9b19fd07e44a88d8f6e5ded571b24cf8c371f12'
-- selectors
SEL_CCIP_SEND             = '\x96f4e9f9'
SEL_GET_FEE               = '\x20487ded'
SEL_IS_CHAIN_SUPPORTED    = '\xa48a9058'
SEL_GET_ONRAMP            = '\xa8d87a3b'
SEL_POOL_LOCK_OR_BURN     = '\x9a4575b9'
SEL_POOL_RELEASE_OR_MINT  = '\x39077537'
SEL_POOL_WITHDRAW_LIQUIDITY = '\x0a861f2a'
SEL_TAR_GET_POOL          = '\xbbe4f6db'
SEL_TYPE_AND_VERSION      = '\x181f5a77'

-- routers
ETH_CCIP_ROUTER   = '\x80226fc0ee2b096224eeac085bb9a8cba1146f7d'
BASE_CCIP_ROUTER  = '\x881e3a65b4d4a04dd529061dd0071cf975f58bcd'
BNB_CCIP_ROUTER   = '\x34b03cb9086d7d758ac55af71584f81a598759fe'
AVAX_CCIP_ROUTER  = '\xf4c7e640eda248ef95972845a62bdc74237805db'
ARB_CCIP_ROUTER   = '\x141fa059441e0ca23ce184b6a78bafd2a517dde8'
OP_CCIP_ROUTER    = '\x3206695cae29952f4b0c22a169725a865bc8ce0f'
POL_CCIP_ROUTER   = '\x849c5ed5a80f5b408dd4969b78c2c8fdf0565bfe'
-- Ethereum support
ETH_CCIP_ARMPROXY = '\x411de17f12d1a34ecc7f45f49844626267c75e81'
ETH_CCIP_TOKEN_ADMIN_REGISTRY = '\xb22764f98dd05c789929716d677382df22c05cb6'
-- Robinhood Chain (4663)
RH_CCIP_ROUTER            = '\x06fc836cf9839b1cd891c440a0a45242da6ae1c9'
RH_CCIP_ONRAMP_V2         = '\xe86cedddaefa1999aae234c056b51877bffbd73f'
RH_CCIP_OFFRAMP_V2        = '\x5060de90b723a7eb705742ff1a22a908b1d8b626'
RH_CCIP_ONRAMP_V16        = '\xe72d25add538e8ef9cef85622ea8912a6cb98be6'
RH_CCIP_OFFRAMP_V16       = '\xcdca5d374e46a6dddab50bd2d9acb8c796ec35c3'
RH_CCIP_ARMPROXY          = '\xe8464c353210cc398a45db2454fbc5bcd25fff20'
RH_CCIP_TOKEN_ADMIN_REGISTRY = '\x1912c3cfafe8a76a32a92861d815ac2837f237ca'
-- 2.0.0 ramps (all lanes between target chains)
ETH_CCIP_ONRAMP_V2        = '\xc3423f3fb30857d9c14717b119884b1b63d250b7'
ETH_CCIP_OFFRAMP_V2       = '\x408428bca0e24a25ac8baac1b70f64af257717c3'
BASE_CCIP_ONRAMP_V2       = '\xf75bf16b03aae98677926f0987f195a2153996b9'
BASE_CCIP_OFFRAMP_V2      = '\x16e577f1724ae2598f9b43a52c19e6f67ee13808'
ARB_CCIP_ONRAMP_V2        = '\x7b73923e101950efe098c2eca74c8320b2813f48'
ARB_CCIP_OFFRAMP_V2       = '\xd4ad79ed3372460f1e63feb8fc41c3b757198c6e'
OP_CCIP_ONRAMP_V2         = '\xcbfaabcb95358817d2fe859f1ca223cf83fae199'
OP_CCIP_OFFRAMP_V2        = '\x4ef20b2071ecc7653d5ba12e758383d1542cfd90'
POLY_CCIP_ONRAMP_V2       = '\x7b8c563e2b29c2d194bc8d18092684420aa47bbe'
POLY_CCIP_OFFRAMP_V2      = '\xbb1e3552badc3498638d20d0b6903afc432c7253'
BNB_CCIP_ONRAMP_V2        = '\x84a0797b31ac0d3e1d06157663dd4b18cffda188'
BNB_CCIP_OFFRAMP_V2       = '\x4914044f8d787bd5dc7528f00775d850dc54477e'
AVAX_CCIP_ONRAMP_V2       = '\xa556c22b7f73a15963813a9a0fdba50f44fe5cf9'
AVAX_CCIP_OFFRAMP_V2      = '\x65d04d8da1405b50d3508aaf94e1b6f5f1a3895c'
-- 1.6.0 ramps (lanes to other chains); several literals change role per chain (§4.3)
ETH_CCIP_ONRAMP_V16       = '\x913814782144864e523c3fdb78e3ca25d2c2aeca'
ETH_CCIP_OFFRAMP_V16      = '\x26d3681dfc9e4c8c79cfbf461adec8a21d5d73c5'
BASE_CCIP_ONRAMP_V16      = '\xee85aefb15b9489563a6a29891ebe0750aa1a7ae'
BASE_CCIP_OFFRAMP_V16     = '\xf09afe78d3c7d359b334d7cb88995751f7ec5e13'
ARB_CCIP_ONRAMP_V16       = '\x76a443768a5e3b8d1aed0105fc250877841deb40'
ARB_CCIP_OFFRAMP_V16      = '\xee85aefb15b9489563a6a29891ebe0750aa1a7ae'
OP_CCIP_ONRAMP_V16        = '\x76a443768a5e3b8d1aed0105fc250877841deb40'
OP_CCIP_OFFRAMP_V16       = '\xee85aefb15b9489563a6a29891ebe0750aa1a7ae'
POLY_CCIP_ONRAMP_V16      = '\x530ae314ec3fa038bd9a215095e37295ec76162a'
POLY_CCIP_OFFRAMP_V16     = '\x77fdbd20ed582794b1d9f1a8a94e4a60494d677e'
BNB_CCIP_ONRAMP_V16       = '\xf09afe78d3c7d359b334d7cb88995751f7ec5e13'
BNB_CCIP_OFFRAMP_V16      = '\xa27056438ffa1f286ab197488808692f0db93f8b'
AVAX_CCIP_ONRAMP_V16      = '\x02a4d69cffec00fbf7f3b60c93e3529dfc58894d'
AVAX_CCIP_OFFRAMP_V16     = '\xe72d25add538e8ef9cef85622ea8912a6cb98be6'
-- legacy Ethereum <-> Base lane (EVM2EVM 1.2.0 / 1.5.0)
ETH_CCIP_EVM2EVM_ONRAMP_120_TO_BASE   = '\xe2c2ab221aa0b957805f229d2aa57fbe2f4dadf7'
ETH_CCIP_EVM2EVM_ONRAMP_150_TO_BASE   = '\xb8a882f3b88bd52d1ff56a873bfdb84b70431937'
ETH_CCIP_EVM2EVM_OFFRAMP_120_FROM_BASE= '\xdf85c8381954694e74abd07488f452b4c2cddfb3'
ETH_CCIP_EVM2EVM_OFFRAMP_150_FROM_BASE= '\x6b4b6359dd5b47cdb030e5921456d2a0625a9ebd'
BASE_CCIP_EVM2EVM_ONRAMP_120_TO_ETH   = '\xdea286dc0e01cb4755650a6cf8d1076b454ea1cb'
BASE_CCIP_EVM2EVM_ONRAMP_150_TO_ETH   = '\x56b30a0dcd8dc87ec08b80fa09502bab801fa78e'
BASE_CCIP_EVM2EVM_OFFRAMP_120_FROM_ETH= '\xec0cfe335a4d53dba70cb650ab56eec32788f0bb'
BASE_CCIP_EVM2EVM_OFFRAMP_150_FROM_ETH= '\xca04169671a81e4fb8768cfad46c347ae65371f1'
-- token pools of the evidence
ETH_CCIP_POOL_GHO         = '\x06179f7c1be40863405f374e7f5f8806c728660a'
ETH_CCIP_POOL_WETH_SILOED = '\x011ef1fe26d20077a59f38e9ad155b166ad87d40'
ETH_CCIP_POOL_LINK        = '\x1b7492c3bd23a4adb448710e4275ff14a5288932'
ETH_CCIP_POOL_WPROS       = '\x6f0c4c3f0f1ca8f0513b542a124a0208fee72d97'
ETH_CCIP_POOL_USDC_CCTP_CCV = '\x806489226179d519d7bf5814ba8ea0f7d850acf2'
ETH_CCIP_POOL_TRUF        = '\x7134dc364fb6b9585a1320a4d7b4215ca52ff0b1'
ETH_CCIP_LOCKBOX_TRUF     = '\x4d4522a30673a6b1dfa70b1bed60f778eb542f6b'
BASE_CCIP_POOL_CHEX       = '\x1c01171761a94538377fd0fda230ec921274df47'
BASE_CCIP_POOL_GHO        = '\x98217a06721ebf727f2c8d9ad7718ec28b7aae34'
BASE_CCIP_POOL_LINK       = '\xba148baf60ccc4d7d86aed4fcff04d5b3265cad4'
BASE_CCIP_POOL_WPROS      = '\x7126c3fef4e6a680eee09fb039b2236f638384b0'
BASE_CCIP_POOL_FLOCK      = '\xcbdf4be5195636e39fc3d2b5c42f443471e8d026'
RH_CCIP_POOL_FLOCK        = '\x05e42e03996379cd0b6290cc2767a1bdd78b737a'   -- same literal is the FLOCK pool on Ethereum and BNB
```

---

## 7. Verification & sources

- **Chain selectors:** `smartcontractkit/chain-selectors` `selectors.yml` (all 7 confirmed exact).
- **Re-checked and extended 2026-09-29:**
  - **Addresses:** chain records, lanes and token pools from the CCIP Directory data files `chains.json`, `lanes.json`, `tokens.json` (`smartcontractkit/documentation`, `src/config/data/ccip/v1_2_0/mainnet/`). Every Router, ramp, support contract and listed pool of §4.3–§4.7 was existence-checked with `eth_getCode` and identified with `typeAndVersion()` (`0x181f5a77`); pools also with `getToken()`. The first word of `getStaticConfig()` on every 1.6.0 / 2.0.0 ramp equals the chain's selector (Robinhood Chain `0x55c67227e8c0b329` = 6180753054346818345). Router wiring read with `getOnRamp` and `isChainSupported`.
  - **Topics and selectors:** recomputed as `keccak256` of the canonical signatures in `smartcontractkit/chainlink-ccip` (`main`: `onRamp/OnRamp.sol`, `offRamp/OffRamp.sol`, `pools/TokenPool.sol`, `pools/ERC20LockBox.sol`; branch `contracts-ccip-release/1.6.0`: the same files plus `libraries/Internal.sol`, `ocr/MultiOCR3Base.sol`, `rmn/RMNRemote.sol`, `tokenAdminRegistry/TokenAdminRegistry.sol`, `pools/SiloedLockReleaseTokenPool.sol`, `interfaces/ILiquidityContainer.sol`) and `smartcontractkit/ccip` tag `v2.17.0-ccip1.5.16` (`EVM2EVMOnRamp.sol`, `EVM2EVMOffRamp.sol`, `CommitStore.sol`, `pools/TokenPool.sol`). `ReportAccepted` `0x291698c01aa71f912280535d88a00d2c59fb63530a3f5d0098560468acb9ebf5` confirmed on the Ethereum CommitStores through the Blockscout API; the earlier `ReportAccepted` value `0xe7083f062ca92dcb8a99d77975265459469cea4eb12c03948142d04587a4fdfa` hashes a tuple that does not exist in the source.
  - **Pinned 12-hour window 2026-09-28 00:00–12:00 UTC (any emitter):** `CCIPMessageSent` 2.0.0 — Ethereum 192, Base 149, Arbitrum 40, Optimism 2, Polygon 37, BNB 106, Avalanche 16, Robinhood Chain 43; `CCIPMessageSent` 1.6.0 — Ethereum 12, Base 52, BNB 2, Robinhood Chain 2, the others 0; `CCIPSendRequested` — Ethereum 1, the others 0; `ExecutionStateChanged` 2.0.0 — Ethereum 209, Base 198, Arbitrum 28, Optimism 0, Polygon 5, BNB 64, Avalanche 7, Robinhood Chain 127; `ExecutionStateChanged` 1.6.0 — Ethereum 6, Base 7, BNB 2, the others 0; `ExecutionStateChanged` ≤1.5 — Ethereum 1, Base 4; `CommitReportAccepted` — Ethereum 806, Base 714, Arbitrum 800, Optimism 41, Polygon 77, BNB 503, Avalanche 435, Robinhood Chain 656; Router `MessageExecuted` — Ethereum 107, Base 18, Arbitrum 25, Optimism 0, Polygon 0, BNB 33, Avalanche 3, Robinhood Chain 0. Every emitter of the 2.0.0 and 1.6.0 events was a ramp of §4.3.
  - **Sample transactions read:** Ethereum send `0xdc188c620c42ca025bc0a5ba3902a6c67c12c515ef1dfefc62c85d5c57b021ed` (WETH fee to the OnRamp and on to the fee proxy; WPROS `Transfer` user → pool and pool → `0x0`; `LockedOrBurned`; `CCIPMessageSent` 2.0.0); Ethereum execution `0x0db80696d5708d491eab9c6c512bc9d885dcff64aa36b739a487cafd0b219f96` (OffRamp 2.0.0 `ExecutionStateChanged` from BNB, Router `MessageExecuted`); Base send `0xf2cf1e3f46c464422164f179d247a9a2f684d2f01e615be2a225053bd9b741e4` (LINK fee, YNE burn, `Burned` with the 1.6.0 OnRamp as `sender`, `CCIPMessageSent` 1.6.0); Robinhood Chain send `0xaf809818093a88079575d9cffbc5ee05e016ae6eb87c4cfbcce89e265f8357d3` (§4.7).
- Sources added 2026-09-29: [CCIP Directory data](https://github.com/smartcontractkit/documentation/tree/main/src/config/data/ccip/v1_2_0/mainnet) · [chainlink-ccip](https://github.com/smartcontractkit/chainlink-ccip) (`main`, `contracts-ccip-release/1.6.0`) · [ccip v2.17.0-ccip1.5.16](https://github.com/smartcontractkit/ccip/tree/v2.17.0-ccip1.5.16/contracts/src/v0.8/ccip) · [Blockscout Ethereum API](https://eth.blockscout.com).
- **Routers:** `eth_getCode` non-empty (11130 B) on all 7 chains; Ethereum `typeAndVersion() = "Router 1.2.0"`.
- **Selectors:** computed locally (keccak); `ccipSend` (`0x96f4e9f9`) and `isChainSupported` (`0xa48a9058`) confirmed present in the live Ethereum Router bytecode.
- **Ethereum support contracts:** `eth_getCode` non-empty (ARMProxy 1452 B, TokenAdminRegistry 5193 B, RegistryModuleOwnerCustom 972 B).
- **Topics:** computed locally from canonical signatures. The send-side message-struct events and the v1.6 commit event tuples are version-specific — flagged in §2.2.
- Sources: [CCIP Directory (mainnet)](https://docs.chain.link/ccip/directory/mainnet) · [CCIP architecture](https://docs.chain.link/ccip/concepts/architecture) · [chain-selectors repo](https://github.com/smartcontractkit/chain-selectors) · `smartcontractkit/chainlink` & `smartcontractkit/ccip` `contracts/src/v0.8/ccip/`.
