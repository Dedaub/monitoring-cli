# Connext NXTP v1 — Topics, Selectors, Addresses (Ethereum, Arbitrum, Optimism, Polygon, BNB, Avalanche; not Base or Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains and against the canonical Connext source: the `legacy` branch of `connext/monorepo` (the former `connext/nxtp` repository), with `packages/contracts/contracts/*.sol`, `packages/contracts/deployments.json` and the subgraph configs `packages/subgraph/config/{v0,v1-runtime,prod}.json`.
**Scope:** NXTP, the first Connext transfer system (2021 to 2023). This file covers the **TransactionManager** of each chain, the **FulfillInterpreter** that each TransactionManager creates, the **RouterFactory** and its per-router **Router** contracts, and the older **v0 TransactionManager** that ran before v1 on Polygon, BNB and Arbitrum. Six of the eight target chains have NXTP: Ethereum (1), Arbitrum One (42161), Optimism (10), Polygon PoS (137), BNB Smart Chain (56) and Avalanche C-Chain (43114). Base (8453) and Robinhood Chain (4663) have no deployment. Topics and selectors are chain-agnostic; addresses are network-specific. The later generations are in [amarok.md](amarok.md) (Amarok Diamond) and [core.md](core.md) (Everclear).

NXTP is a two-phase lock between a user and a router, not a lock-and-mint bridge. The user locks funds in the sending chain's TransactionManager. A router locks the same amount (less its fee) from its own liquidity in the receiving chain's TransactionManager. The user's signature unlocks the router's funds to the user on the receiving chain. The router then submits the same signature on the sending chain and takes the user's locked funds into its liquidity balance. No token is minted or burned, and no message bridge is used.

The contracts are **not upgradeable**: each TransactionManager is a plain contract (EIP-1967 implementation slot empty, 16-17 kB of full logic) with a `ProposedOwnable` owner. The owner can only allow or remove routers and assets; no function lets the owner move user or router funds. Each chain has its own TransactionManager address, but a TransactionManager that the same deployer created at the same nonce shares the literal `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` on several chains, with **v1 code on Ethereum, Optimism and Avalanche and v0 code on Polygon and BNB**. Always key on `(chain, address)`.

NXTP uses **EVM chain ids** (`sendingChainId`, `receivingChainId` in the transaction data); it has no domain ids of its own. The last `TransactionPrepared` of the Ethereum TransactionManager is at block 17,314,962 (2023-05-22, explorer transaction list). Residual owner and liquidity activity continued in 2025 (§12, item 12).

---

## 0. Contract families and the transfer flow

| Contract | Role | Chains (of the eight) | Proxy? |
|----------|------|-----------------------|--------|
| **TransactionManager (v1)** | Holds user deposits and router liquidity; `prepare` / `fulfill` / `cancel`; emits every transfer event. | ETH, ARB, OP, POLY, BNB, AVAX | No (immutable, `ProposedOwnable`) |
| **TransactionManager (v0)** | Earlier ABI: no `initiator` field and no argument structs. Ran before v1 (2021). | POLY, BNB, ARB | No |
| **FulfillInterpreter** | Created by each TransactionManager in its constructor. Runs the receiving-chain call to `callTo`; sends the funds to the fallback address when the call fails. | one per TransactionManager | No |
| **RouterFactory** | CREATE2 factory of Router contracts (salt from the router signer). | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` on all six | No |
| **Router** | Per-router wrapper. A relayer submits the router signer's signed `prepare` / `fulfill` / `cancel` / `removeLiquidity`; the Router is then the `router` in the TransactionManager events. | one per router and chain | No |
| ConnextPriceOracle | Price feed for off-chain fee quotes. Emits no transfer event. | one per chain | No |

One transfer takes four transactions on two chains, all tied by the same `transactionId`:

| Step | Chain | Caller | Function | Event | Value movement in the same transaction |
|------|-------|--------|----------|-------|----------------------------------------|
| 1. Deposit (source leg) | sending | the user (`initiator`) | `prepare` | `TransactionPrepared` | ERC-20 `Transfer` user to TransactionManager, or native `msg.value`. `txData.amount` is the amount received (fee-on-transfer safe). |
| 2. Router commitment | receiving | the router or its Router contract | `prepare` | `TransactionPrepared` | None. `routerBalances[router][receivingAssetId]` falls by `amount`. |
| 3. Payout (destination leg) | receiving | anyone with the user's signature (usually a relayer) | `fulfill` | `TransactionFulfilled` | TransactionManager pays `amount - relayerFee` to `receivingAddress` and `relayerFee` to `msg.sender`. With `callTo` set, the funds go through the FulfillInterpreter (`Executed`) to `callTo`, or to `receivingAddress` when the call fails. |
| 4. Router claim | sending | the router only | `fulfill` | `TransactionFulfilled` | None. `routerBalances[router][sendingAssetId]` rises by the deposit. |
| Refund | sending | the router before `expiry`, anyone after | `cancel` | `TransactionCancelled` | TransactionManager pays the full deposit to `sendingChainFallback`. |
| Release | receiving | the user (or a relayer with the user's cancel signature) before `expiry`, anyone after | `cancel` | `TransactionCancelled` | None. Router liquidity is credited back. |

`expiry` must be 1 to 30 days after the `prepare` block (`MIN_TIMEOUT` = 86400, `MAX_TIMEOUT` = 2592000).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 TransactionManager v1 — transfer events (the link key is `transactionId`, topic3)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x88fbf1dbc326c404155bad4643bd0ddadd23f0636929c66442f0433208b2c905` | `TransactionPrepared(address indexed user, address indexed router, bytes32 indexed transactionId, (address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, address caller, ((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, uint256 sendingChainId, uint256 receivingChainId, bytes32 callDataHash, bytes32 transactionId) invariantData, uint256 amount, uint256 expiry, bytes encryptedCallData, bytes encodedBid, bytes bidSignature, bytes encodedMeta) args)` | **Sending chain: the user's deposit** (ERC-20 `Transfer` user to TransactionManager, or native `msg.value`). **Receiving chain: the router's commitment** (no token moves). Verified live. |
| `0x8e5df24f8b9ac0e3455417a1d7060762388ce3c1d4941aa49dc1b61943031d32` | `TransactionFulfilled(address indexed user, address indexed router, bytes32 indexed transactionId, ((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, uint256 relayerFee, bytes signature, bytes callData, bytes encodedMeta) args, bool success, bool isContract, bytes returnData, address caller)` | **Receiving chain: the payout** (TransactionManager pays `receivingAddress` and the relayer fee). **Sending chain: the router's claim** (no token moves). Verified live. |
| `0x56a92405e111173b950d90846413f755ca35bb7631d49a4a564778b21affe287` | `TransactionCancelled(address indexed user, address indexed router, bytes32 indexed transactionId, ((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, bytes signature, bytes encodedMeta) args, address caller)` | **Sending chain: the refund** to `sendingChainFallback`. Receiving chain: router liquidity is credited back (no token moves). Verified live. |

### 1.2 TransactionManager v0 and v1 — liquidity and admin events (the same topics in both versions)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x4bd28ccd068c4853d24d35f727ef2a3fea11ce55e8d93461e45f785818e1e139` | `LiquidityAdded(address indexed router, address indexed assetId, uint256 amount, address caller)` | Router liquidity in (ERC-20 `Transfer` caller to TransactionManager, or `msg.value`). |
| `0x7da12116be8cb7af4b2d9e9b4a2ca2c3a3243ddd6fd3a94411902367b8eed568` | `LiquidityRemoved(address indexed router, address indexed assetId, uint256 amount, address recipient)` | Router liquidity out (TransactionManager pays `recipient`). **Watch on a dormant contract.** Verified live. |
| `0xbc68405e644da2aaf25623ce2199da82c6dfd2e1de102b400eba6a091704d4f4` | `RouterAdded(address indexed addedRouter, address indexed caller)` | Owner-only admin. Verified live. |
| `0xbee3e974bb6a6f44f20096ede047c191eef60322e65e4ee4bd3392230a8716d5` | `RouterRemoved(address indexed removedRouter, address indexed caller)` | Owner-only admin. |
| `0x0bb5715f0f217c2fe9a0c877ea87d474380c641102f3440ee2a4c8b9d9790918` | `AssetAdded(address indexed addedAssetId, address indexed caller)` | Owner-only admin. |
| `0x0fa1e4606af435f32f05b3804033d2933e691fab32ee74d2db6fa82d2741f1ea` | `AssetRemoved(address indexed removedAssetId, address indexed caller)` | Owner-only admin. |
| `0x6ab4d119f23076e8ad491bc65ce85f017fb0591dce08755ba8591059cc51737a` | `OwnershipProposed(address indexed proposedOwner)` | Owner change, step 1 (7-day delay). Verified live. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Owner change, step 2. Verified live. |
| `0xa52048c5f468d21a62e4644ac4db19bcaa1a20f0cf37d163ba49c7217d35feb8` | `RouterOwnershipRenunciationProposed(uint256 timestamp)` | v1 only. Starts the delay before the router allowlist can be dropped. |
| `0x243ebbb2f905234bbf0556bb38e1f7c23b09ffd2e441a16e58b844eb2ab7a397` | `RouterOwnershipRenounced(bool renounced)` | v1 only. After it, any address can act as a router. |
| `0xa78fdca214e4619ef34a695316d423f5b0d8274bc919d29733bf8f92ec8cbb7a` | `AssetOwnershipRenunciationProposed(uint256 timestamp)` | v1 only. |
| `0x868d89ead22a5d10f456845ac0014901d9af7203e71cf0892d70d9dc262c2fb9` | `AssetOwnershipRenounced(bool renounced)` | v1 only. After it, any asset is accepted. |

### 1.3 TransactionManager v0 — transfer events (Polygon, BNB and Arbitrum, 2021)

The v0 `TransactionData` tuple has 15 fields: it has no `initiator`. The v0 events carry the call data, bid and bid signature as plain `bytes` fields.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xab398cccfbdc6ce7daf9d26bc84174d4d49bde657c28c1cc456b4eb7c0aa720a` | `TransactionPrepared(address indexed user, address indexed router, bytes32 indexed transactionId, (address receivingChainTxManagerAddress, address user, address router, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, address caller, bytes encryptedCallData, bytes encodedBid, bytes bidSignature)` | v0 deposit (sending chain) or router commitment (receiving chain). Verified live on Polygon. |
| `0x61bafb0ebbe27dfee40c81c31c114db452f16caed88c1f653c14d8645f1d78c7` | `TransactionFulfilled(address indexed user, address indexed router, bytes32 indexed transactionId, (address receivingChainTxManagerAddress, address user, address router, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, uint256 relayerFee, bytes signature, bytes callData, bool success, bytes returnData, address caller)` | v0 payout (receiving chain) or router claim (sending chain). Verified live on Polygon. |
| `0x9ff4e119c7d03c442b1656c62e4fb6c3cd6490a27ab86e7ff2ce50dd3b73a4c1` | `TransactionCancelled(address indexed user, address indexed router, bytes32 indexed transactionId, (address receivingChainTxManagerAddress, address user, address router, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, address caller)` | v0 refund or router credit. From the v0 ABI; not seen in the sampled windows. |

### 1.4 FulfillInterpreter (receiving-chain calls only)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x03196b76502b81bbf14393f8b5ed67dff323f1f86667b064820f1fdf293686a1` | `Executed(bytes32 indexed transactionId, address callTo, address assetId, address fallbackAddress, uint256 amount, bytes callData, bytes returnData, bool success, bool isContract)` | v1 interpreter. `success = false` means the funds went to `fallbackAddress` (the `receivingAddress`). Verified live on Polygon. |
| `0xbf49bd2de448d90a19e0510ab1030fead50ebfc64a4f112ca42535ae79fbab79` | `Executed(bytes32 indexed transactionId, address callTo, address assetId, address fallbackAddress, uint256 amount, bytes callData, bytes returnData, bool success)` | v0 interpreter (source tag `v0.0.50`). Not seen in four sampled Polygon windows. |

### 1.5 Router contract and RouterFactory

These are status events of the router's own wrapper. The token movement is always in the TransactionManager's event of the same transaction.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x583ad731037599752e477b0d462b10b6067dab73e63227960e20403a8ee7f7f0` | `Prepare((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, uint256 sendingChainId, uint256 receivingChainId, bytes32 callDataHash, bytes32 transactionId) invariantData, address routerRelayerFeeAsset, uint256 routerRelayerFee, address caller)` | Router contract; precedes the TransactionManager's `TransactionPrepared` in the same transaction. Verified live. |
| `0xbd58fe74fd3111b8d37f5a35a025b9cec45d1f01f329eb4e1b86a1428d5d3337` | `Fulfill((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, address routerRelayerFeeAsset, uint256 routerRelayerFee, address caller)` | Router contract; the router's sending-chain claim. Verified live. |
| `0xdb26fb99c342114246dbc5580bb4d02519f9250cacf10aafc127b24f755d4e3f` | `Cancel((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, address routerRelayerFeeAsset, uint256 routerRelayerFee, address caller)` | Router contract. Verified live. |
| `0x964a82560b2c071ffde7bc11cc169cfbef31770b4457ff7fa561d5e2bfb51543` | `RemoveLiquidity(uint256 amount, address assetId, address routerRelayerFeeAsset, uint256 routerRelayerFee, address caller)` | Router contract; precedes `LiquidityRemoved`. Verified live. |
| `0x1104e763408245681528382e9b9fcd4d8f1b4bce2e83f5ce2be8d1a5ec8323a0` | `RelayerFeeAdded(address assetId, uint256 amount, address caller)` | Router contract: gas money for relayers. |
| `0x5d760a2d1cc0892ddaea1748093916f51d345b37724db0f69b41574a92adc06f` | `RelayerFeeRemoved(address assetId, uint256 amount, address caller)` | Router contract (owner-only). |
| `0xe8e811674d167b407a67a22f592a226ade5e34b608e7d56721f82422f3b98197` | `RouterCreated(address router, address routerSigner, address recipient, address transactionManager)` | RouterFactory. Verified live. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 TransactionManager v1 — transfer functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd9459372` | `prepare(((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, uint256 sendingChainId, uint256 receivingChainId, bytes32 callDataHash, bytes32 transactionId) invariantData, uint256 amount, uint256 expiry, bytes encryptedCallData, bytes encodedBid, bytes bidSignature, bytes encodedMeta) args)` | `payable`. Sending chain: called by `initiator`, pulls the funds. Receiving chain: called by the router. Emits `TransactionPrepared`. |
| `0x9b151a80` | `fulfill(((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, uint256 relayerFee, bytes signature, bytes callData, bytes encodedMeta) args)` | Receiving chain: any caller with the user's signature (a relayer); pays out. Sending chain: the router only. Emits `TransactionFulfilled`. |
| `0xbe91a2ba` | `cancel(((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, bytes signature, bytes encodedMeta) args)` | Before `expiry`: the router (sending chain) or the user or a relayer with the user's signature (receiving chain). After `expiry`: anyone. Emits `TransactionCancelled`. |

### 2.2 TransactionManager v0 and v1 — liquidity and admin functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc95f9d0e` | `addLiquidity(uint256 amount, address assetId)` | `payable`; the caller is the router. Emits `LiquidityAdded`. |
| `0xe070da09` | `addLiquidityFor(uint256 amount, address assetId, address router)` | `payable`; funds a named router. Emits `LiquidityAdded`. |
| `0xf31abcc4` | `removeLiquidity(uint256 amount, address assetId, address recipient)` | The router (`msg.sender`) withdraws its own balance; no owner approval. Emits `LiquidityRemoved`. |
| `0x24ca984e` | `addRouter(address router)` | Owner-only. Emits `RouterAdded`. |
| `0x6ae0b154` | `removeRouter(address router)` | Owner-only. Emits `RouterRemoved`. |
| `0x34e9393c` | `addAssetId(address assetId)` | Owner-only. Emits `AssetAdded`. |
| `0xb1d2618d` | `removeAssetId(address assetId)` | Owner-only. Emits `AssetRemoved`. |
| `0xb1f8100d` | `proposeNewOwner(address newlyProposed)` | Owner-only. Emits `OwnershipProposed`. |
| `0xc5b350df` | `acceptProposedOwner()` | The proposed owner, after the 7-day delay. Emits `OwnershipTransferred`. |
| `0x715018a6` | `renounceOwnership()` | Owner-only, after the delay. |
| `0xe47602f7` | `proposeRouterOwnershipRenunciation()` | v1, owner-only. |
| `0xc0c17baf` | `renounceRouterOwnership()` | v1, owner-only, after the delay. |
| `0x8741eac5` | `proposeAssetOwnershipRenunciation()` | v1, owner-only. |
| `0x3855b467` | `renounceAssetOwnership()` | v1, owner-only, after the delay. |

### 2.3 TransactionManager — views

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x41258b5c` | `routerBalances(address router, address assetId)` | `uint256`: the router's free liquidity. The same selector exists on the Amarok Diamond (`RoutersFacet`). |
| `0x5e679856` | `variantTransactionData(bytes32 digest)` | `bytes32`: hash of (amount, expiry, preparedBlockNumber) per invariant digest; `preparedBlockNumber = 0` after fulfill or cancel. |
| `0x445b1e4b` | `approvedRouters(address router)` | `bool`. |
| `0x97eb0088` | `approvedAssets(address assetId)` | `bool`. |
| `0x3a35cf17` | `interpreter()` | `address`: the FulfillInterpreter of this TransactionManager. |
| `0x3408e470` | `getChainId()` | `uint256`: the chain id that the contract enforces. |
| `0x8da5cb5b` | `owner()` | `address`. |
| `0x2004ef45` | `isRouterOwnershipRenounced()` | `bool` (v1). |
| `0xe8be0dfc` | `isAssetOwnershipRenounced()` | `bool` (v1). |
| `0x543ad1df` | `MIN_TIMEOUT()` | `uint256` = 86400 (1 day). |
| `0xde38eb3a` | `MAX_TIMEOUT()` | `uint256` = 2592000 (30 days). |

### 2.4 TransactionManager v0 — transfer functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x63405b93` | `prepare((address receivingChainTxManagerAddress, address user, address router, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, uint256 sendingChainId, uint256 receivingChainId, bytes32 callDataHash, bytes32 transactionId) invariantData, uint256 amount, uint256 expiry, bytes encryptedCallData, bytes encodedBid, bytes bidSignature)` | v0 `payable`. Emits the v0 `TransactionPrepared`. |
| `0x7bac72b5` | `fulfill((address receivingChainTxManagerAddress, address user, address router, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, uint256 relayerFee, bytes signature, bytes callData)` | v0. Emits the v0 `TransactionFulfilled`. |
| `0x67df6017` | `cancel((address receivingChainTxManagerAddress, address user, address router, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, bytes signature)` | v0. Emits the v0 `TransactionCancelled`. |

### 2.5 FulfillInterpreter, Router and RouterFactory

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xcf9a3604` | `execute(bytes32 transactionId, address callTo, address assetId, address fallbackAddress, uint256 amount, bytes callData)` | FulfillInterpreter, `payable`; callable only by its TransactionManager. Emits `Executed`. |
| `0xce976539` | `prepare(((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, uint256 sendingChainId, uint256 receivingChainId, bytes32 callDataHash, bytes32 transactionId) invariantData, uint256 amount, uint256 expiry, bytes encryptedCallData, bytes encodedBid, bytes bidSignature, bytes encodedMeta) args, address routerRelayerFeeAsset, uint256 routerRelayerFee, bytes signature)` | Router contract; a relayer submits the router signer's signed request and gets `routerRelayerFee`. Emits `Prepare`. |
| `0x6e2054a9` | `fulfill(((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, uint256 relayerFee, bytes signature, bytes callData, bytes encodedMeta) args, address routerRelayerFeeAsset, uint256 routerRelayerFee, bytes signature)` | Router contract. Emits `Fulfill`. |
| `0xd42030ed` | `cancel(((address receivingChainTxManagerAddress, address user, address router, address initiator, address sendingAssetId, address receivingAssetId, address sendingChainFallback, address receivingAddress, address callTo, bytes32 callDataHash, bytes32 transactionId, uint256 sendingChainId, uint256 receivingChainId, uint256 amount, uint256 expiry, uint256 preparedBlockNumber) txData, bytes signature, bytes encodedMeta) args, address routerRelayerFeeAsset, uint256 routerRelayerFee, bytes signature)` | Router contract. Emits `Cancel`. |
| `0x82977466` | `removeLiquidity(uint256 amount, address assetId, address routerRelayerFeeAsset, uint256 routerRelayerFee, bytes signature)` | Router contract; sends the liquidity to the Router's `recipient`. Emits `RemoveLiquidity`, then the TransactionManager's `LiquidityRemoved`. |
| `0xfc6bee13` | `addRelayerFee(uint256 amount, address assetId)` | Router contract, `payable`. |
| `0x4f64cfc5` | `removeRelayerFee(uint256 amount, address assetId)` | Router contract, owner-only. |
| `0x3bbed4a0` | `setRecipient(address _recipient)` | Router contract, owner-only: changes where removed liquidity goes. |
| `0x6c19e783` | `setSigner(address _routerSigner)` | Router contract, owner-only. |
| `0x7f629efc` | `createRouter(address routerSigner, address recipient)` | RouterFactory: CREATE2 deploy of a Router (salt from `routerSigner`). Emits `RouterCreated`. |
| `0x463a6176` | `getRouterAddress(address routerSigner)` | RouterFactory view: the CREATE2 address of a signer's Router. |

The relayed calls reach the TransactionManager as internal calls. In the samples of §14, `tx.to` is a relay contract or a Router contract, not the TransactionManager. Key a monitor on the TransactionManager events, not on the selector of `tx.input`.

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified with `eth_getCode` on 2026-09-29. `getChainId()` = 1. `interpreter()` and `owner()` read live.

| Role | Address | One-liner |
|------|---------|-----------|
| **TransactionManager (v1)** | `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` | 17,031 B. Subgraph start block 13,548,432. Emits all §1.1 and §1.2 events. |
| FulfillInterpreter (v1) | `0x5b9e4d0dd21f4e071729a9eb522a2366abed149a` | 2,902 B. `interpreter()` of the TransactionManager. |
| RouterFactory | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | 12,800 B; the same code hash on all six chains. |
| ConnextPriceOracle | `0x92a36570CaBe5a3b4C7831874BE8a95ccAE87435` | 4,325 B. |
| Owner (EOA) | `0x4d96f2d2143dd74a96d015a70953a5686fa6ed55` | `owner()` since 2025-10-20 (block 23,621,167). Also the v0 owner on Polygon and BNB. |
| Previous owner (EOA with an EIP-7702 delegation) | `0x155b15a7e9ff0e34ceaf2439589d5c661adc9493` | The deployer of the TransactionManager. Its 23-byte code is `0xef0100` plus a delegate address, so it is an EOA, not a contract. |
| Router contract (sample) | `0x95ce8b1c273af612cd895e6b0c633039c3572827` | 10,274 B. The Router that the 2025 liquidity removals used (§12, item 12). |

No v0 TransactionManager on Ethereum: the v0 subgraph config has no Ethereum entry.

## 4. Addresses — Arbitrum One (chain ID 42161)

`getChainId()` = 42161 on both TransactionManagers.

| Role | Address | One-liner |
|------|---------|-----------|
| **TransactionManager (v1)** | `0xcF4d2994088a8CDE52FB584fE29608b63Ec063B2` | 17,031 B. Subgraph start block 1,915,295. |
| FulfillInterpreter (v1) | `0x4e678366780d7b1cc0dd3081efd9ebd64c029a65` | 2,902 B. |
| **TransactionManager (v0)** | `0xF293D5d599c046681AB28c1Bc7927Fff859c67A7` | 16,295 B. v0 subgraph start block 244,433 (pre-Nitro). |
| FulfillInterpreter (v0) | `0x7fccd4537abd881c6f83fa31b6eb03eaad1e350a` | 2,707 B. |
| RouterFactory | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | Same code hash as on Ethereum. |
| ConnextPriceOracle | `0x57d1e2c546f605b8fbd38Cbf97E052b4477C8De5` | 4,109 B. |
| Owner of v1 (EOA) | `0x99834733c91aae2f5bb0725105c9e843cb297a27` | nonce 456. |
| Owner of v0 (EOA with an EIP-7702 delegation) | `0x155b15a7e9ff0e34ceaf2439589d5c661adc9493` | 23-byte delegation code. |

`0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` has no code on Arbitrum.

## 5. Addresses — Optimism (chain ID 10)

| Role | Address | One-liner |
|------|---------|-----------|
| **TransactionManager (v1)** | `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` | 17,031 B. Subgraph start block 114,843. `getChainId()` = 10. |
| FulfillInterpreter (v1) | `0x5b9e4d0dd21f4e071729a9eb522a2366abed149a` | 2,902 B; the same code hash as on Ethereum. |
| RouterFactory | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | |
| ConnextPriceOracle | `0x262bcedD20b6223cBB807a0bE3900aB87316C671` | 4,109 B. |
| Owner (EOA) | `0x25dc768d5dad1972220058ea0d27259df7e00c2e` | nonce 73. |

No v0 on Optimism.

## 6. Addresses — Polygon PoS (chain ID 137)

`getChainId()` = 137 on both TransactionManagers.

| Role | Address | One-liner |
|------|---------|-----------|
| **TransactionManager (v1)** | `0x6090De2EC76eb1Dc3B5d632734415c93c44Fd113` | 17,031 B. Subgraph start block 19,835,794. |
| FulfillInterpreter (v1) | `0x7d34b2be5190299a778d367bc1b171e66f53a065` | 2,902 B. |
| **TransactionManager (v0)** | `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` | **16,295 B: v0 code at the Ethereum v1 literal.** v0 subgraph start block 18,421,338. |
| FulfillInterpreter (v0) | `0x5b9e4d0dd21f4e071729a9eb522a2366abed149a` | **2,707 B: v0 code at the Ethereum v1 literal.** |
| RouterFactory | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | |
| ConnextPriceOracle | `0x1F1047476ce5d696023A4A31e037a753E860Ab8C` | 4,109 B. |
| Owner of v1 (EOA) | `0xabcf9220fd6186c2fdcf47f8914dc6db3249efb4` | nonce 460. |
| Owner of v0 (EOA) | `0x4d96f2d2143dd74a96d015a70953a5686fa6ed55` | |

## 7. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | One-liner |
|------|---------|-----------|
| **TransactionManager (v1)** | `0x2A9EA5e8cDDf40730f4f4F839F673a51600C314e` | 17,031 B. Subgraph start block 11,481,191. `getChainId()` = 56. |
| FulfillInterpreter (v1) | `0x3940a0a4cb508da64cb11b13cdba7e3b04fb9b34` | 2,902 B. |
| **TransactionManager (v0)** | `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` | 16,295 B (v0 code). v0 subgraph start block 10,370,113. |
| FulfillInterpreter (v0) | `0x5b9e4d0dd21f4e071729a9eb522a2366abed149a` | 2,707 B (v0 code). |
| RouterFactory | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | |
| ConnextPriceOracle | `0x45adFa7763b123e456d677d876F6a1C52aFc8085` | 4,109 B. |
| Owner of v1 (EOA) | `0xf8cfd0344cc5552203be99c82474fda3ea0ea0f8` | nonce 14,009. |
| Owner of v0 (EOA) | `0x4d96f2d2143dd74a96d015a70953a5686fa6ed55` | |

## 8. Addresses — Avalanche C-Chain (chain ID 43114)

| Role | Address | One-liner |
|------|---------|-----------|
| **TransactionManager (v1)** | `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` | 17,031 B. Subgraph start block 5,285,668. `getChainId()` = 43114. |
| FulfillInterpreter (v1) | `0x5b9e4d0dd21f4e071729a9eb522a2366abed149a` | 2,902 B. |
| RouterFactory | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | |
| ConnextPriceOracle | `0xE43Ee0700698F1d64491eA2AeBFBFC18Df18590E` | 4,109 B. |
| Owner (EOA) | `0x155b15a7e9ff0e34ceaf2439589d5c661adc9493` | No code on Avalanche. |

## 9. Base (chain ID 8453) and Robinhood Chain (chain ID 4663) — no deployment

`eth_getCode` returns `0x` (nonce 0) on both chains for every NXTP address in this file: the three TransactionManager literals, `0xF293D5d599c046681AB28c1Bc7927Fff859c67A7`, the RouterFactory, and the interpreters. `deployments.json` has no entry for 8453 or 4663. Base launched in 2023 and Robinhood Chain in 2026, after the end of NXTP.

---

## 10. Cross-chain summary

| Chain | ID | TransactionManager v1 | TransactionManager v0 | FulfillInterpreter v1 | RouterFactory | v1 owner (EOA) |
|-------|----|-----------------------|-----------------------|-----------------------|---------------|----------------|
| Ethereum | 1 | `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` | — | `0x5b9e4d0dd21f4e071729a9eb522a2366abed149a` | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | `0x4d96f2d2143dd74a96d015a70953a5686fa6ed55` |
| Base | 8453 | — (no code) | — | — | — | — |
| Arbitrum One | 42161 | `0xcF4d2994088a8CDE52FB584fE29608b63Ec063B2` | `0xF293D5d599c046681AB28c1Bc7927Fff859c67A7` | `0x4e678366780d7b1cc0dd3081efd9ebd64c029a65` | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | `0x99834733c91aae2f5bb0725105c9e843cb297a27` |
| Optimism | 10 | `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` | — | `0x5b9e4d0dd21f4e071729a9eb522a2366abed149a` | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | `0x25dc768d5dad1972220058ea0d27259df7e00c2e` |
| Polygon PoS | 137 | `0x6090De2EC76eb1Dc3B5d632734415c93c44Fd113` | `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` | `0x7d34b2be5190299a778d367bc1b171e66f53a065` | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | `0xabcf9220fd6186c2fdcf47f8914dc6db3249efb4` |
| BNB Smart Chain | 56 | `0x2A9EA5e8cDDf40730f4f4F839F673a51600C314e` | `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` | `0x3940a0a4cb508da64cb11b13cdba7e3b04fb9b34` | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | `0xf8cfd0344cc5552203be99c82474fda3ea0ea0f8` |
| Avalanche C-Chain | 43114 | `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` | — | `0x5b9e4d0dd21f4e071729a9eb522a2366abed149a` | `0x73a37b3EB030cC3f9739CA5C16b7E6802F294122` | `0x155b15a7e9ff0e34ceaf2439589d5c661adc9493` |
| Robinhood Chain | 4663 | — (no code) | — | — | — | — |

Counterparty chains outside the eight, from `deployments.json`: Gnosis (100), Fantom (250), Moonriver (1285), Moonbeam (1284), Cronos (25), Boba (288), Fuse (122), Harmony (1666600000), Evmos (9001), Milkomeda Cardano (2001), Arbitrum Nova (42170) and Gather (192837465). The literal `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` is the v1 TransactionManager on most of them too.

---

## 11. Proxies (old and new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **TransactionManager v0 and v1** | **Immutable** | EIP-1967 implementation slot empty on every chain; 16,295 B (v0) or 17,031 B (v1) of full logic. `chainId` and `interpreter` are immutables, so the code hash differs per chain at the same size. | None. `ProposedOwnable` owner: `proposeNewOwner` then `acceptProposedOwner` after 7 days. Watch `OwnershipProposed` and `OwnershipTransferred`. |
| FulfillInterpreter | Immutable | Created in the TransactionManager constructor; 2,707 B (v0) or 2,902 B (v1). | None. |
| RouterFactory | Immutable (OpenZeppelin `Ownable`) | 12,800 B, one code hash on all six chains. | The factory owner can call `init` again to point new Routers at another TransactionManager. |
| Router | Immutable (OpenZeppelin `Ownable`) | CREATE2 child of the RouterFactory; about 10 kB. | The router's owner can change `recipient` and `routerSigner`: watch `setRecipient` on a Router that holds liquidity. |

To move NXTP to new code, Connext deployed a new TransactionManager (v0 to v1) and moved routers and liquidity. There is no `Upgraded` event to watch.

---

## 12. Detection invariants and gotchas

1. **Both main events fire on both chains.** `TransactionPrepared` is the user's deposit on the sending chain and the router's commitment on the receiving chain. `TransactionFulfilled` is the user's payout on the receiving chain and the router's claim on the sending chain. Decide by comparing `txData.sendingChainId` and `txData.receivingChainId` with the chain that emitted the log. A search for one chain id in the log data does not give the direction, because each log holds both ids.
2. **Only steps 1, 3 and the sending-chain refund move tokens.** Steps 2 and 4 and the receiving-chain cancel change `routerBalances` only. A value monitor on `TransactionPrepared` counts router commitments as deposits unless it applies item 1.
3. **Link key = `transactionId`** (topic3 of all three transfer events, the same on both chains, also inside `txData`). The pair of chains is in `txData`; the receiving TransactionManager is `txData.receivingChainTxManagerAddress`. Both sides are on chain.
4. **Who is who.** The funds come from `initiator` (the `msg.sender` of the sending-chain `prepare`). `user` (topic1) signs the fulfill and cancel messages. The payout goes to `receivingAddress`, or to `callTo` through the FulfillInterpreter. `sendingChainFallback` receives a refund. `tx.from` is usually a relayer or a router bot.
5. **`router` (topic2) is often a Router contract**, created by the RouterFactory and driven by a relay service. In the Ethereum samples, `tx.to` is a relay contract (`0x3caca7b48d0573d793d3b0279b5f0029180e83b6`) and the Router emits `Prepare` or `Cancel` before the TransactionManager event. Rules on `tx.to` or on the TransactionManager selectors miss these flows.
6. **The relayer fee comes out of the payout.** On the receiving chain the TransactionManager pays `relayerFee` to `msg.sender` and the rest to the receiver in the same transaction (two ERC-20 `Transfer` logs from the TransactionManager).
7. **Amounts differ between the two chains.** The receiving `amount` is the router's bid (the sending amount less the router fee), and the two assets can have different decimals (for example USDT with 6 decimals on Polygon and BSC-USD with 18 decimals on BNB). Compare amounts in token units, not raw integers.
8. **Native assets are `address(0)`.** A native deposit arrives as `msg.value`; a native payout or refund is an internal value transfer with no `Transfer` log.
9. **v0 and v1 use different topics and selectors, and one literal holds both versions.** `0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` is v1 on Ethereum, Optimism and Avalanche and v0 on Polygon and BNB; `0x5b9e4d0dd21f4e071729a9eb522a2366abed149a` is the matching interpreter. Decode with the topics of the version that is on that chain.
10. **Cancel paths.** On the sending chain the router can cancel before `expiry` and anyone can cancel after it; the deposit goes to `sendingChainFallback`. On the receiving chain only the user (or a relayer with the user's cancel signature) can cancel before `expiry`. A `TransactionCancelled` on the sending chain is a refund, not a transfer.
11. **Admin surface is small.** The owner can add or remove routers and assets and change the owner (7-day delay). There is no pause and no owner withdrawal. `removeLiquidity` needs no owner approval: a router withdraws its own balance at any time.
12. **Residual activity after the end of transfers.** On the Ethereum TransactionManager, block 23,563,791 (2025) has `RouterAdded` and `OwnershipProposed` in one transaction from the previous owner. Blocks 23,563,825 to 23,563,828 have three `LiquidityRemoved` events from Router `0x95ce8b1c273af612cd895e6b0c633039c3572827` to `0x4d96f2d2143dd74a96d015a70953a5686fa6ed55`: 987.368511 USDC, 529.823539 USDT and 49.277774115166331680 DAI. Block 23,621,167 (2025-10-20) has `OwnershipTransferred`. Watch `LiquidityRemoved` and the ownership events on every TransactionManager, even when no transfer happens.
13. **The previous owner `0x155b15a7e9ff0e34ceaf2439589d5c661adc9493` has code** on Ethereum and Arbitrum: 23 bytes that start with `0xef0100` (an EIP-7702 delegation). It is an EOA. Do not classify it as a contract.
14. **`routerBalances(address,address)` has the selector `0x41258b5c` on both NXTP and the Amarok Diamond.** Disambiguate by the address.
15. **Not on Base or Robinhood Chain.** No code at any NXTP literal and no entry in the official deployment list.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== TransactionManager v1 topics =====
TOPIC_TRANSACTION_PREPARED        = '\x88fbf1dbc326c404155bad4643bd0ddadd23f0636929c66442f0433208b2c905'
TOPIC_TRANSACTION_FULFILLED       = '\x8e5df24f8b9ac0e3455417a1d7060762388ce3c1d4941aa49dc1b61943031d32'
TOPIC_TRANSACTION_CANCELLED       = '\x56a92405e111173b950d90846413f755ca35bb7631d49a4a564778b21affe287'
-- ===== TransactionManager v0 topics (Polygon, BNB, Arbitrum; 2021) =====
TOPIC_TRANSACTION_PREPARED_V0     = '\xab398cccfbdc6ce7daf9d26bc84174d4d49bde657c28c1cc456b4eb7c0aa720a'
TOPIC_TRANSACTION_FULFILLED_V0    = '\x61bafb0ebbe27dfee40c81c31c114db452f16caed88c1f653c14d8645f1d78c7'
TOPIC_TRANSACTION_CANCELLED_V0    = '\x9ff4e119c7d03c442b1656c62e4fb6c3cd6490a27ab86e7ff2ce50dd3b73a4c1'
-- ===== Liquidity and admin topics (v0 and v1) =====
TOPIC_LIQUIDITY_ADDED             = '\x4bd28ccd068c4853d24d35f727ef2a3fea11ce55e8d93461e45f785818e1e139'
TOPIC_LIQUIDITY_REMOVED           = '\x7da12116be8cb7af4b2d9e9b4a2ca2c3a3243ddd6fd3a94411902367b8eed568'
TOPIC_ROUTER_ADDED                = '\xbc68405e644da2aaf25623ce2199da82c6dfd2e1de102b400eba6a091704d4f4'
TOPIC_ROUTER_REMOVED              = '\xbee3e974bb6a6f44f20096ede047c191eef60322e65e4ee4bd3392230a8716d5'
TOPIC_ASSET_ADDED                 = '\x0bb5715f0f217c2fe9a0c877ea87d474380c641102f3440ee2a4c8b9d9790918'
TOPIC_ASSET_REMOVED               = '\x0fa1e4606af435f32f05b3804033d2933e691fab32ee74d2db6fa82d2741f1ea'
TOPIC_OWNERSHIP_PROPOSED          = '\x6ab4d119f23076e8ad491bc65ce85f017fb0591dce08755ba8591059cc51737a'
TOPIC_OWNERSHIP_TRANSFERRED       = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_ROUTER_OWNERSHIP_RENOUNCED  = '\x243ebbb2f905234bbf0556bb38e1f7c23b09ffd2e441a16e58b844eb2ab7a397'
TOPIC_ASSET_OWNERSHIP_RENOUNCED   = '\x868d89ead22a5d10f456845ac0014901d9af7203e71cf0892d70d9dc262c2fb9'
-- ===== FulfillInterpreter, Router, RouterFactory =====
TOPIC_INTERPRETER_EXECUTED        = '\x03196b76502b81bbf14393f8b5ed67dff323f1f86667b064820f1fdf293686a1'
TOPIC_INTERPRETER_EXECUTED_V0     = '\xbf49bd2de448d90a19e0510ab1030fead50ebfc64a4f112ca42535ae79fbab79'
TOPIC_ROUTER_PREPARE              = '\x583ad731037599752e477b0d462b10b6067dab73e63227960e20403a8ee7f7f0'
TOPIC_ROUTER_FULFILL              = '\xbd58fe74fd3111b8d37f5a35a025b9cec45d1f01f329eb4e1b86a1428d5d3337'
TOPIC_ROUTER_CANCEL               = '\xdb26fb99c342114246dbc5580bb4d02519f9250cacf10aafc127b24f755d4e3f'
TOPIC_ROUTER_REMOVE_LIQUIDITY     = '\x964a82560b2c071ffde7bc11cc169cfbef31770b4457ff7fa561d5e2bfb51543'
TOPIC_ROUTER_CREATED              = '\xe8e811674d167b407a67a22f592a226ade5e34b608e7d56721f82422f3b98197'

-- ===== Selectors =====
SEL_PREPARE                       = '\xd9459372'
SEL_FULFILL                       = '\x9b151a80'
SEL_CANCEL                        = '\xbe91a2ba'
SEL_PREPARE_V0                    = '\x63405b93'
SEL_FULFILL_V0                    = '\x7bac72b5'
SEL_CANCEL_V0                     = '\x67df6017'
SEL_ADD_LIQUIDITY                 = '\xc95f9d0e'
SEL_ADD_LIQUIDITY_FOR             = '\xe070da09'
SEL_REMOVE_LIQUIDITY              = '\xf31abcc4'
SEL_ADD_ROUTER                    = '\x24ca984e'
SEL_REMOVE_ROUTER                 = '\x6ae0b154'
SEL_ADD_ASSET_ID                  = '\x34e9393c'
SEL_REMOVE_ASSET_ID               = '\xb1d2618d'
SEL_PROPOSE_NEW_OWNER             = '\xb1f8100d'
SEL_ACCEPT_PROPOSED_OWNER         = '\xc5b350df'
SEL_ROUTER_BALANCES               = '\x41258b5c'
SEL_INTERPRETER                   = '\x3a35cf17'
SEL_GET_CHAIN_ID                  = '\x3408e470'
SEL_ROUTER_CONTRACT_PREPARE       = '\xce976539'
SEL_ROUTER_CONTRACT_FULFILL       = '\x6e2054a9'
SEL_ROUTER_CONTRACT_CANCEL        = '\xd42030ed'
SEL_ROUTER_CONTRACT_REMOVE_LIQ    = '\x82977466'
SEL_ROUTER_SET_RECIPIENT          = '\x3bbed4a0'
SEL_CREATE_ROUTER                 = '\x7f629efc'

-- ===== TransactionManager v1 (per chain) =====
ETH_TRANSACTION_MANAGER           = '\x31efc4aeaa7c39e54a33fdc3c46ee2bd70ae0a09'
ARB_TRANSACTION_MANAGER           = '\xcf4d2994088a8cde52fb584fe29608b63ec063b2'
OP_TRANSACTION_MANAGER            = '\x31efc4aeaa7c39e54a33fdc3c46ee2bd70ae0a09'
POLY_TRANSACTION_MANAGER          = '\x6090de2ec76eb1dc3b5d632734415c93c44fd113'
BNB_TRANSACTION_MANAGER           = '\x2a9ea5e8cddf40730f4f4f839f673a51600c314e'
AVAX_TRANSACTION_MANAGER          = '\x31efc4aeaa7c39e54a33fdc3c46ee2bd70ae0a09'
-- ===== TransactionManager v0 (per chain) =====
ARB_TRANSACTION_MANAGER_V0        = '\xf293d5d599c046681ab28c1bc7927fff859c67a7'
POLY_TRANSACTION_MANAGER_V0       = '\x31efc4aeaa7c39e54a33fdc3c46ee2bd70ae0a09'
BNB_TRANSACTION_MANAGER_V0        = '\x31efc4aeaa7c39e54a33fdc3c46ee2bd70ae0a09'
-- ===== FulfillInterpreter (per chain) =====
ETH_FULFILL_INTERPRETER           = '\x5b9e4d0dd21f4e071729a9eb522a2366abed149a'
ARB_FULFILL_INTERPRETER           = '\x4e678366780d7b1cc0dd3081efd9ebd64c029a65'
OP_FULFILL_INTERPRETER            = '\x5b9e4d0dd21f4e071729a9eb522a2366abed149a'
POLY_FULFILL_INTERPRETER          = '\x7d34b2be5190299a778d367bc1b171e66f53a065'
BNB_FULFILL_INTERPRETER           = '\x3940a0a4cb508da64cb11b13cdba7e3b04fb9b34'
AVAX_FULFILL_INTERPRETER          = '\x5b9e4d0dd21f4e071729a9eb522a2366abed149a'
ARB_FULFILL_INTERPRETER_V0        = '\x7fccd4537abd881c6f83fa31b6eb03eaad1e350a'
POLY_FULFILL_INTERPRETER_V0       = '\x5b9e4d0dd21f4e071729a9eb522a2366abed149a'
BNB_FULFILL_INTERPRETER_V0        = '\x5b9e4d0dd21f4e071729a9eb522a2366abed149a'
-- ===== RouterFactory (the same literal on ETH, ARB, OP, POLY, BNB, AVAX) =====
ETH_ROUTER_FACTORY                = '\x73a37b3eb030cc3f9739ca5c16b7e6802f294122'
ARB_ROUTER_FACTORY                = '\x73a37b3eb030cc3f9739ca5c16b7e6802f294122'
OP_ROUTER_FACTORY                 = '\x73a37b3eb030cc3f9739ca5c16b7e6802f294122'
POLY_ROUTER_FACTORY               = '\x73a37b3eb030cc3f9739ca5c16b7e6802f294122'
BNB_ROUTER_FACTORY                = '\x73a37b3eb030cc3f9739ca5c16b7e6802f294122'
AVAX_ROUTER_FACTORY               = '\x73a37b3eb030cc3f9739ca5c16b7e6802f294122'
-- ===== Owners (EOAs) =====
ETH_OWNER_EOA                     = '\x4d96f2d2143dd74a96d015a70953a5686fa6ed55'
ETH_PREVIOUS_OWNER_EOA            = '\x155b15a7e9ff0e34ceaf2439589d5c661adc9493'   -- EIP-7702 delegation code
ARB_OWNER_EOA                     = '\x99834733c91aae2f5bb0725105c9e843cb297a27'
OP_OWNER_EOA                      = '\x25dc768d5dad1972220058ea0d27259df7e00c2e'
POLY_OWNER_EOA                    = '\xabcf9220fd6186c2fdcf47f8914dc6db3249efb4'
BNB_OWNER_EOA                     = '\xf8cfd0344cc5552203be99c82474fda3ea0ea0f8'
AVAX_OWNER_EOA                    = '\x155b15a7e9ff0e34ceaf2439589d5c661adc9493'
-- Base (8453) and Robinhood Chain (4663): no NXTP contract (eth_getCode = 0x at every literal above)
```

---

## 14. Verification and sources

How the constants were verified (2026-09-29):

- **Topic0 and selectors:** recomputed as `keccak256(canonical signature)` (first 4 bytes for selectors), with the structs written out from `ITransactionManager.sol` (`TransactionData`, `InvariantTransactionData`, `PrepareArgs`, `FulfillArgs`, `CancelArgs`), `IFulfillInterpreter.sol`, `Router.sol`, `IRouterFactory.sol` and `ProposedOwnable.sol` on the `legacy` branch. The v0 forms come from the v0 subgraph ABI (`packages/subgraph/src/v0/abis/TransactionManager.json`) and from tag `v0.0.50`, whose `TransactionData` has no `initiator`. The v1 `TransactionPrepared` and `TransactionFulfilled` topics equal the values that the Connext subgraph ABI gives.
- **Live logs (positive controls):** Ethereum TransactionManager, blocks 15,000,000 to 15,004,999: 209 `TransactionPrepared`, 194 `TransactionFulfilled`, 1 `TransactionCancelled`. Polygon v1, blocks 23,727,554 to 23,737,553: 578 / 566 / 5 cancelled / 2 `LiquidityRemoved`. Avalanche, blocks 9,579,290 to 9,589,289: 71 / 71 / 2 `LiquidityRemoved`. Optimism, blocks 29,394,033 to 29,404,032: 5 / 5. Arbitrum v1, blocks 30,153,138 to 30,163,137: 6 / 7. Polygon v0 (`0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09` on Polygon), blocks 19,115,834 to 19,125,833: 143 v0 `TransactionPrepared` and 139 v0 `TransactionFulfilled`. Polygon v1 FulfillInterpreter: 6, 5 and 12 `Executed` logs in the 10,000-block windows from blocks 27,000,000, 29,000,000 and 31,000,000. Router `Prepare`, `Cancel`, `Fulfill` and `RemoveLiquidity` and RouterFactory `RouterCreated` were seen in the sample transactions below.
- **Not measured:** BNB history (the public BNB endpoints refused archive `eth_getLogs`), and the Arbitrum v0 contract (blocks 866,024 to 876,023 returned 0 logs; that range is before the Nitro migration, and no positive control shows that the endpoint serves those logs). The v0 `TransactionCancelled` and the v0 interpreter `Executed` were not seen in the sampled windows.
- **Sample transactions read with `eth_getTransactionReceipt`:** Ethereum `0x0f26a0704fd785b51d1b109777ca998ab819a24477a88b2f5fda0b6630309c12` (receiving-chain `TransactionPrepared`, Evmos to Ethereum, 207.303652 USDC, Router `Prepare` in the same transaction, no token movement); Ethereum `0xa317163baa2e1acfec92287de20375af91602f7defdedb7b483abc4ebaba2937` (receiving-chain `TransactionFulfilled`: USDC `Transfer` of 200.803211 to the receiver and 6.500441 to the relayer); Ethereum `0x903f3353984c45daf63f36ca56b2e4205908f967a8a5c34e972d2eb039a9c3cc` (sending-chain `TransactionCancelled` of 1 ETH to Arbitrum, Router `Cancel`); Polygon `0x0c67429fd9ddd7e6f20b57e4c4ed44b03eb9c5489819195705d9d8e7b13d7140` (sending-chain `TransactionPrepared`, Polygon to Moonbeam, WETH `Transfer` of 4.566898 from the user to the TransactionManager, `tx.to` = TransactionManager); Polygon `0x6f91a1dd1190585f95efc8a880f5364b9a54c468658e2a6ea21fc14177a7d904` (sending-chain `TransactionFulfilled`, the router's claim through Router `0x3df415d9e0539de5e746ff36ff98b54cf6570722`, no token `Transfer`); Ethereum `0xb2df510a76b9a9fe9f0636442c105f225ed05f46b36536d4dd4b485c5eb78bbf` (`createRouter`, `RouterCreated`); Ethereum `0x3a2d3d1eb5d11eb8d14069640d15ecb1774544c57f65d089fcd33943c1631dd3`, `0xeb0b226e311d665a2269aef390cdc3fb3fd8d9e4a40ce526ebc91b9ad4eb7d98`, `0xaecdaebf524e067e289bbfb6e6176f5473d89e56912fe7a994760451d46181e0`, `0xd858632ef6c667fbb98f3e4c30b40ffffbd510ced420e6b99278269e7958832a` and `0x99a44f0a67e947eef4a691dc43c3800645ecd18bdb521dd5e10a547644196f9f` (the 2025 admin and liquidity sequence of §12, item 12).
- **Pinned 12-hour window 2026-09-28 00:00 to 12:00 UTC:** `TransactionPrepared` (v1) and `TransactionFulfilled` (v1) from any emitter: Ethereum 0, Base 0, Arbitrum 0, Optimism 0, Polygon 0, BNB 0, Avalanche 0, Robinhood 0. v0 events at the v0 TransactionManagers: Arbitrum 0 and 0, BNB 0 and 0, Polygon 0 (`TransactionPrepared`) and 0 (`TransactionFulfilled`).
- **Addresses:** `deployments.json` (`TransactionManager`, `RouterFactory`, `ConnextPriceOracle` per chain id) and the subgraph configs (`v0.json`, `v1-runtime.json`, `prod.json`: address and start block per network). Every address was checked with `eth_getCode` on its chain; the EIP-1967 implementation slot is empty on every TransactionManager. `interpreter()`, `owner()`, `getChainId()`, `isRouterOwnershipRenounced()` (false) and `isAssetOwnershipRenounced()` (false) were read with `eth_call`. Owners were classified by `eth_getCode` and nonce.
- **Chain coverage:** all eight chains probed at the literals of every chain. Base and Robinhood Chain: no code at any literal and no entry in `deployments.json`.

Sources:
- [connext/monorepo, `legacy` branch: `packages/contracts`](https://github.com/connext/monorepo/tree/legacy/packages/contracts) (`contracts/TransactionManager.sol`, `contracts/interfaces/ITransactionManager.sol`, `contracts/interpreters/FulfillInterpreter.sol`, `contracts/Router.sol`, `contracts/RouterFactory.sol`, `contracts/ProposedOwnable.sol`, `deployments.json`)
- [connext/monorepo, `legacy` branch: `packages/subgraph/config`](https://github.com/connext/monorepo/tree/legacy/packages/subgraph/config) (`v0.json`, `v1-runtime.json`, `prod.json`) and `packages/subgraph/src/{v0,v1-runtime}/abis/TransactionManager.json`
- [connext/monorepo, tag `v0.0.50`](https://github.com/connext/monorepo/tree/v0.0.50/packages/contracts/contracts) (v0 interfaces)
- Explorers: [Blockscout TransactionManager (Ethereum)](https://eth.blockscout.com/address/0x31eFc4AeAA7c39e54A33FDc3C46ee2Bd70ae0A09) (verified `TransactionManager`, creator `0x155b15a7e9ff0e34ceaf2439589d5c661adc9493`, latest transactions and logs) · [Blockscout RouterFactory (Ethereum)](https://eth.blockscout.com/address/0x73a37b3EB030cC3f9739CA5C16b7E6802F294122) · [Blockscout Router (Ethereum)](https://eth.blockscout.com/address/0x31769170acae5f8c06a4577e7ff8719d742fd4c5)
