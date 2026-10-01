# Arbitrum Orbit chains — Topics, Selectors, Addresses (Robinhood Chain + Orbit L2s on Ethereum + Orbit L3s on Base)

**Status:** verified on 2026-09-29 against live RPC on Ethereum (1), Base (8453) and Robinhood Chain (4663); against the Robinhood Chain contract list (`docs.robinhood.com/chain/protocol-contracts`), the Arbitrum bridge registry (`OffchainLabs/arbitrum-token-bridge` `orbitChainsData.json`), the Orbit SDK factory address maps, and the `OffchainLabs/nitro-contracts` (v2.1.3, v3.2.0), `OffchainLabs/token-bridge-contracts` (v1.2.5) and `OffchainLabs/upgrade-executor` sources. Activity is measured in the pinned 12-hour window 2026-09-28 00:00–12:00 UTC.
**Scope:** Arbitrum Orbit chains: chains that run the Arbitrum Nitro stack under their own chain id, with their own copies of the core contracts (Rollup, Bridge, Inbox, SequencerInbox, Outbox) and of the token bridge. This file covers the 13 Orbit L2s that settle to Ethereum (Robinhood Chain first), the 2 listed Orbit L3s that settle to Base, 18 further Orbit chains found on Ethereum and Base, the Orbit L3s that settle to Arbitrum One (34 Bridges), the L2-side contracts of Robinhood Chain (4663), and the one Orbit L3 observed on Robinhood Chain. Arbitrum One (42161) and Nova (42170) are in `core.md`. Topics and selectors are chain-agnostic and are the ones of `core.md` §1–§2; this file lists only the events and functions that `core.md` lacks. Addresses are network-specific.

Every Orbit chain deploys the same Nitro contracts, so every chain emits the same topic0 values. **The emitter address is the only thing that tells two Orbit chains apart.** A monitor keys on `(chain, emitter)`, and it resolves an unknown emitter on chain: `Bridge.rollup()` gives the live Rollup, `Rollup.chainId()` gives the Orbit chain id, and `Rollup.inbox()` / `outbox()` / `sequencerInbox()` give the rest. `inboxToL1Deployment(inbox)` on the TokenBridgeCreator gives the token bridge.

Three facts to know before indexing:

1. **Two fee models.** An ETH chain uses `Bridge` + `Inbox` (as in `core.md`): a deposit is `depositEth()` and the ETH rides in `msg.value`. A **custom fee-token chain** uses `ERC20Bridge` + `ERC20Inbox`: a deposit is `depositERC20(amount)` and it moves the fee token (for example SHIB, G, PLUME or SX), not ETH, as two ERC-20 `Transfer` rows (user to ERC20Inbox, ERC20Inbox to ERC20Bridge). The same `MessageDelivered` kind 12 marks both. `Bridge.nativeToken()` answers only on an ERC20Bridge.
2. **Two rollup generations.** A classic rollup emits `NodeCreated` / `NodeConfirmed` (§1.1). A BoLD rollup emits `AssertionCreated` / `AssertionConfirmed` (`core.md` §1.5). Registry values go stale: for Gravity Alpha, Plume and HPP the bridge registry still names the classic Rollup, while `Bridge.rollup()` now returns a BoLD Rollup (§9, item 3).
3. **Robinhood Chain is the only Orbit chain among the eight target chains.** Its Ethereum side is §3.1. Its L2 side (ArbSys, ArbRetryableTx, the L2 token bridge, WETH) is §6, and one Orbit L3 already settles to it (§6.4).

---

## 0. Contract families & versions

| Contract | Where | Role | Proxy? |
|---|---|---|---|
| **Bridge** / **ERC20Bridge** | parent chain | Escrow of the native asset (ETH, or the fee token). Emits `MessageDelivered` for every delayed message and `BridgeCallTriggered` for every payout. | EIP-1967 transparent |
| **Inbox** / **ERC20Inbox** ("Delayed Inbox") | parent chain | Entry point for deposits and retryable tickets. Emits `InboxMessageDelivered`. | EIP-1967 transparent |
| **SequencerInbox** | parent chain | Batch poster target. Emits `SequencerBatchDelivered` and, for batch-cost reports, `InboxMessageDelivered` too. Status only. | EIP-1967 transparent |
| **Outbox** | parent chain | Executes a withdrawal after its root is confirmed. Emits `OutBoxTransactionExecuted`, `SendRootUpdated`. | EIP-1967 transparent |
| **RollupEventInbox** | parent chain | Rollup-to-L2 system messages. Also an allowed delayed inbox of the Bridge. | EIP-1967 transparent |
| **Rollup** (classic RollupProxy or BoLD) | parent chain | State assertions and their confirmation. Status only. | double-logic proxy (admin logic + user logic) |
| **UpgradeExecutor** | parent chain and L2 | The chain owner's admin entry point: owns the ProxyAdmins, is the Rollup admin. | EIP-1967 transparent |
| **L1GatewayRouter**, **L1ERC20Gateway**, **L1CustomGateway**, **L1WethGateway** (Orbit variants `L1OrbitGatewayRouter`, `L1OrbitERC20Gateway`, `L1OrbitCustomGateway` on fee-token chains) | parent chain | ERC-20 escrow token bridge. A fee-token chain has no WETH gateway. | EIP-1967 transparent |
| **L2GatewayRouter**, **L2ERC20Gateway**, **L2CustomGateway**, **L2WethGateway**, **aeWETH** | the Orbit chain | Mint/burn side of the token bridge. | EIP-1967 transparent |
| **ArbSys** `0x0000000000000000000000000000000000000064`, **ArbRetryableTx** `0x000000000000000000000000000000000000006E` | the Orbit chain | Withdrawal origin (`L2ToL1Tx`) and retryable lifecycle (`TicketCreated`, `RedeemScheduled`). | ArbOS precompiles, 1-byte code `0xfe` |
| **RollupCreator**, **TokenBridgeCreator** | parent chain | Factories. `RollupCreated` and `OrbitTokenBridgeCreated` announce a new Orbit chain (§1.5). | RollupCreator immutable; TokenBridgeCreator proxy |

### 0.1 The flow, the link keys and the value movement

| Leg | Contract → event (all topic0 values in `core.md` §1 unless noted) | Value movement in the same transaction | Link key |
|---|---|---|---|
| **Source: ETH deposit** (ETH chain) | `Inbox.depositEth()` → Bridge `MessageDelivered` (kind 12) + Inbox `InboxMessageDelivered` | ETH in `msg.value`, user → Inbox → Bridge (no ERC-20 row) | `messageIndex` (= `messageNum`) |
| **Source: fee-token deposit** | `ERC20Inbox.depositERC20(amount)` → ERC20Bridge `MessageDelivered` (kind 12) + `InboxMessageDelivered` | fee token `Transfer` user → ERC20Inbox, then ERC20Inbox → ERC20Bridge | `messageIndex` |
| **Source: token deposit** | router `outboundTransfer` → `TransferRouted`, gateway `TxToL2` + `DepositInitiated`, Bridge `MessageDelivered` (kind 9), Inbox `InboxMessageDelivered` | token `Transfer` user → gateway escrow; retryable fee in ETH `msg.value`, or fee token `Transfer` user → ERC20Inbox | `DepositInitiated._sequenceNumber` = `TxToL2._seqNum` = `messageIndex` |
| **Destination of a deposit** (on the Orbit chain) | ArbRetryableTx `TicketCreated` + `RedeemScheduled`; L2 gateway `DepositFinalized` | L2 token minted (`Transfer` from `0x0`); ETH or fee-token deposits have no L2 log | `TicketCreated.ticketId` = the hash of the L2 submit-retryable transaction (type `0x69`) |
| **Source: withdrawal** (on the Orbit chain) | ArbSys `L2ToL1Tx` (+ `SendMerkleUpdate`); token: L2 router `TransferRouted`, L2 gateway `TxToL1` (§1.4) + `WithdrawalInitiated` | L2 token burned (`Transfer` to `0x0`); ETH or fee token in `callvalue` | `L2ToL1Tx.position` = `WithdrawalInitiated._l2ToL1Id` = `TxToL1._id` |
| Status (parent chain) | Rollup `AssertionConfirmed` or `NodeConfirmed` → Outbox `SendRootUpdated` | none | the send root |
| **Destination of a withdrawal** (parent chain, after the challenge period, user-triggered) | `Outbox.executeTransaction` → `OutBoxTransactionExecuted` + Bridge `BridgeCallTriggered`; token: gateway `WithdrawalFinalized` | ETH: internal call Bridge → recipient. Fee token: `Transfer` ERC20Bridge → recipient. Token: `Transfer` escrow → recipient | `OutBoxTransactionExecuted.transactionIndex` = `L2ToL1Tx.position`; `WithdrawalFinalized._exitNum` = `WithdrawalInitiated._exitNum` |
| **Refund / cancel / expiry** | ArbRetryableTx `Redeemed` (manual retry), `LifetimeExtended`, `Canceled`; a failed token deposit makes the L2 gateway start a `WithdrawalInitiated` back to the sender (its `_from` is the L2 gateway) | on cancel or expiry the L2 call value goes to `callValueRefundAddress`; no parent-chain event | `ticketId` |

Both sides of every link key are on chain; no off-chain API is needed. The parent-chain side and the Orbit-chain side are different transactions on different chains. Orbit chains use their own EVM chain id (`Rollup.chainId()`); there is no separate protocol domain id.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

The Bridge, Inbox, SequencerInbox, Outbox, BoLD Rollup, ArbSys, ArbRetryableTx, gateway and router topics are the ones of `core.md` §1.1–§1.8. They have the same values on every Orbit chain, on ETH chains and on fee-token chains alike. The tables below list only the events that `core.md` lacks.

### 1.1 Classic Rollup (pre-BoLD) — AlienX, AppChain, HYCHAIN, SX Rollup, Tranched and others (§3.3, §4.2)

| topic0 | Event | Notes |
|---|---|---|
| `0x4f4caa9e67fb994e349dd35d1ad0ce23053d4323f83ce11dc817b5435031d096` | `NodeCreated(uint64 indexed nodeNum, bytes32 indexed parentNodeHash, bytes32 indexed nodeHash, bytes32 executionHash, (((bytes32[2] bytes32Vals, uint64[2] u64Vals) globalState, uint8 machineStatus) beforeState, ((bytes32[2] bytes32Vals, uint64[2] u64Vals) globalState, uint8 machineStatus) afterState, uint64 numBlocks) assertion, bytes32 afterInboxBatchAcc, bytes32 wasmModuleRoot, uint256 inboxMaxCount)` | status only: a state claim was posted. 50 on Ethereum and 25 on Base in the window |
| `0x22ef0479a7ff660660d1c2fe35f1b632cf31675c2d9378db8cec95b00d8ffa3c` | `NodeConfirmed(uint64 indexed nodeNum, bytes32 blockHash, bytes32 sendRoot)` | status only: withdrawals up to `sendRoot` become executable |
| `0xeaffa3d968707ec919a2fc9f31d5ab2b86c905881ff561725d5a82fc95ad4640` | `NodeRejected(uint64 indexed nodeNum)` | high severity: a node lost a challenge. 0 in the window |
| `0xebd093d389ab57f3566918d2c379a2b4d9539e8eb95efad9d5e465457833fde6` | `UserStakeUpdated(address indexed user, uint256 initialBalance, uint256 finalBalance)` | classic 3-argument form; the BoLD 4-argument form is in `core.md` §1.5 |

`RollupChallengeStarted`, `UserWithdrawableFundsUpdated`, `RollupInitialized` and `OwnerFunctionCalled` have the same types, so the same topic0, in both generations (`core.md` §1.5).

### 1.2 SequencerInbox admin events (nitro-contracts v2.1 and v3)

| topic0 | Event | Notes |
|---|---|---|
| `0x28bcc5626d357efe966b4b0876aa1ee8ab99e26da4f131f6a2623f1800701c21` | `BatchPosterSet(address batchPoster, bool isBatchPoster)` | admin: batch poster added or removed. 3 in the window, each in the same transaction as an UpgradeExecutor `TargetCallExecuted` |
| `0xeb12a9a53eec138c91b27b4f912a257bd690c18fc8bde744be92a0365eb9b87e` | `SequencerSet(address addr, bool isSequencer)` | admin |
| `0x3cd6c184800297a0f2b00926a683cbe76890bb7fd01480ac0a10ed6c8f7f6659` | `BatchPosterManagerSet(address newBatchPosterManager)` | admin |
| `0xaa6a58dad31128ff7ecc2b80987ee6e003df80bc50cd8d0b0d1af0e07da6d19d` | `MaxTimeVariationSet((uint256 delayBlocks, uint256 futureBlocks, uint256 delaySeconds, uint256 futureSeconds) maxTimeVariation)` | admin: force-inclusion delay changed |
| `0xaa7a2d8175dee3b637814ad6346005dfcc357165396fb8327f649effe8abcf85` | `BufferConfigSet((uint64 threshold, uint64 max, uint64 replenishRateInBasis) bufferConfig)` | admin (v3 delay buffer) |
| `0xe83d6153add50e41b8ee6c1115c4178687349bb12bc3902a50b1f6ad78a0c541` | `FeeTokenPricerSet(address feeTokenPricer)` | admin (v3, fee-token chains) |

### 1.3 UpgradeExecutor (the chain owner's admin entry point)

| topic0 | Event | Notes |
|---|---|---|
| `0x49f6851d1cd01a518db5bdea5cffbbe90276baa2595f74250b7472b96806302e` | `UpgradeExecuted(address indexed upgrade, uint256 value, bytes data)` | admin: `execute(upgrade, data)` ran an upgrade action by `delegatecall` |
| `0x4d7dbdcc249630ec373f584267f10abf44938de920c32562f5aee93959c25258` | `TargetCallExecuted(address indexed target, uint256 value, bytes data)` | admin: `executeCall(target, data)`. 20 on Ethereum in the window (Mandala Chain 8, Mars Chain 6, T-Rex 6) |

### 1.4 L2 token-bridge messenger (L2 gateways, on the Orbit chain)

| topic0 | Event | Notes |
|---|---|---|
| `0x2b986d32a0536b7e19baa48ab949fec7b903b7fad7730820b20632d100cc3a68` | `TxToL1(address indexed _from, address indexed _to, uint256 indexed _id, bytes _data)` | status only: the L2 mirror of `TxToL2`, one per token withdrawal; `_to` is the parent-chain gateway, `_id` = `L2ToL1Tx.position`. 10 on Robinhood Chain in the window |

### 1.5 Factories (announce a new Orbit chain or token bridge)

| topic0 | Event | Notes |
|---|---|---|
| `0xd9bfd3bb3012f0caa103d1ba172692464d2de5c7b75877ce255c72147086a79d` | `RollupCreated(address indexed rollupAddress, address indexed nativeToken, address inboxAddress, address outbox, address rollupEventInbox, address challengeManager, address adminProxy, address sequencerInbox, address bridge, address upgradeExecutor, address validatorWalletCreator)` | RollupCreator v3.x; `nativeToken` = `0x0` for an ETH chain |
| `0x481277de518d1f364b196166b90219b996fba76138a3dc84e7fe02540eb1cbdb` | `RollupCreated(address indexed rollupAddress, address indexed nativeToken, address inboxAddress, address outbox, address rollupEventInbox, address challengeManager, address adminProxy, address sequencerInbox, address bridge, address upgradeExecutor, address validatorUtils, address validatorWalletCreator)` | RollupCreator v1.1 and v2.1 |
| `0x9a9203aa9ddcf21d8523e422e009214f0447efca13201ecdd802d8663092de7e` | `OrbitTokenBridgeCreated(address indexed inbox, address indexed owner, (address router, address standardGateway, address customGateway, address wethGateway, address weth) l1Deployment, (address router, address standardGateway, address customGateway, address wethGateway, address weth, address proxyAdmin, address beaconProxyFactory, address upgradeExecutor, address multicall) l2Deployment, address proxyAdmin, address upgradeExecutor)` | TokenBridgeCreator |
| `0x003661d67ef6fa28d5937e796b7701a68fbf54c16d9434eb705715ebc28f424b` | `OrbitTokenBridgeDeploymentSet(address indexed inbox, (address router, address standardGateway, address customGateway, address wethGateway, address weth) l1, (address router, address standardGateway, address customGateway, address wethGateway, address weth, address proxyAdmin, address beaconProxyFactory, address upgradeExecutor, address multicall) l2)` | TokenBridgeCreator owner overrides a record |

No factory event fired on Ethereum in the window (0 `RollupCreated` of either form, 0 `OrbitTokenBridgeCreated`).

### 1.6 Value legs

| topic0 | Event | Notes |
|---|---|---|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20: the fee-token leg (into and out of the ERC20Bridge) and the gateway escrow leg |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

The ETH-chain Inbox (`depositEth()` `0x439370b1`, 8-argument `createRetryableTicket` `0x679b6ded`), Bridge, Outbox, SequencerInbox, gateway and precompile selectors are in `core.md` §2. Only the functions that `core.md` lacks are below.

### 2.1 ERC20Inbox / ERC20Bridge (custom fee-token chains)

| Selector | Signature | Notes |
|---|---|---|
| `0xb79092fd` | `depositERC20(uint256 amount)` | **fee-token deposit**; pulls the fee token, emits `MessageDelivered` (kind 12) + `InboxMessageDelivered`. Present in the ERC20Inbox implementations of Shib Mainnet and Gravity Alpha; absent from the Robinhood Chain Inbox |
| `0x549e8426` | `createRetryableTicket(address to, uint256 l2CallValue, uint256 maxSubmissionCost, address excessFeeRefundAddress, address callValueRefundAddress, uint256 gasLimit, uint256 maxFeePerGas, uint256 tokenTotalFeeAmount, bytes data)` | 9-argument retryable of a fee-token chain; the ETH form `0x679b6ded` is absent from an ERC20Inbox |
| `0xb9b9a688` | `unsafeCreateRetryableTicket(address to, uint256 l2CallValue, uint256 maxSubmissionCost, address excessFeeRefundAddress, address callValueRefundAddress, uint256 gasLimit, uint256 maxFeePerGas, uint256 tokenTotalFeeAmount, bytes data)` | 9-argument form without the call-value check |
| `0xe1758bd8` | `nativeToken()` | ERC20Bridge view: the fee token. Reverts on an ETH Bridge |
| `0xad48cb5e` | `nativeTokenDecimals()` | ERC20Bridge view; `depositERC20` scales the amount to 18 decimals on L2 |
| `0x75d81e25` | `enqueueDelayedMessage(uint8 kind, address sender, bytes32 messageDataHash, uint256 tokenFeeAmount)` | ERC20Inbox → ERC20Bridge; the ETH form is `0x8db5993b` |

### 2.2 L2 router and gateways (Robinhood Chain and every Nitro chain)

| Selector | Signature | Notes |
|---|---|---|
| `0x7b3a3c8b` | `outboundTransfer(address _l1Token, address _to, uint256 _amount, bytes _data)` | **the 4-argument L2 withdrawal entry** of the L2GatewayRouter and L2 gateways; present in the Robinhood Chain and Arbitrum One L2 implementations. Emits `TransferRouted`, `TxToL1`, `WithdrawalInitiated` |

### 2.3 Fee-token token bridge (Orbit router and custom gateway)

| Selector | Signature | Notes |
|---|---|---|
| `0xdc121927` | `setGateway(address _gateway, uint256 _maxGas, uint256 _gasPriceBid, uint256 _maxSubmissionCost, uint256 _feeAmount)` | L1OrbitGatewayRouter: a token registers its gateway and pays the retryable in the fee token |
| `0x3e8ee3df` | `registerTokenToL2(address _l2Address, uint256 _maxGas, uint256 _gasPriceBid, uint256 _maxSubmissionCost, uint256 _feeAmount)` | L1OrbitCustomGateway: map an L1 token to its L2 token, fee in the fee token |

`outboundTransfer` (`0xd2ce7d65`) and `outboundTransferCustomRefund` (`0x4fb1a07b`) keep their selectors on the Orbit gateways; `_data` then encodes `(maxSubmissionCost, callHookData, tokenTotalFeeAmount)` and `msg.value` must be 0.

### 2.4 UpgradeExecutor

| Selector | Signature | Notes |
|---|---|---|
| `0x1cff79cd` | `execute(address upgrade, bytes upgradeCallData)` | executor role only; emits `UpgradeExecuted` |
| `0xbca8c7b5` | `executeCall(address target, bytes targetCallData)` | executor role only; emits `TargetCallExecuted` |
| `0x75b238fc` | `ADMIN_ROLE()` | view; answers on an UpgradeExecutor (identification probe) |
| `0x07bd0265` | `EXECUTOR_ROLE()` | view |

### 2.5 Wiring views (resolve an unknown emitter)

| Selector | Signature | Notes |
|---|---|---|
| `0xcb23bcb5` | `rollup()` | Bridge or SequencerInbox → the **live** Rollup |
| `0x9a8a0592` | `chainId()` | Rollup → the Orbit chain id |
| `0xfb0e722b` | `inbox()` | Rollup → the Delayed Inbox; also on the parent-chain gateways and router |
| `0xce11e6ab` | `outbox()` | Rollup → the canonical Outbox |
| `0xee35f327` | `sequencerInbox()` | Rollup or Bridge → the SequencerInbox |
| `0xe78cea92` | `bridge()` | Rollup, Inbox, Outbox or SequencerInbox → the Bridge |
| `0xe76f5c8d` | `allowedDelayedInboxList(uint256 index)` | Bridge → each allowed inbox (the Inbox and the RollupEventInbox) |
| `0x945e1147` | `allowedOutboxList(uint256 index)` | Bridge → **every** contract that can pay out (§9, item 5) |
| `0x7ba9534a` | `latestNodeCreated()` | answers on a classic Rollup only |
| `0x353325e0` | `genesisAssertionHash()` | answers on a BoLD Rollup only |
| `0x2e7acfa6` | `confirmPeriodBlocks()` | challenge period, in parent-chain blocks |
| `0xd9ce0ef9` | `inboxToL1Deployment(address inbox)` | TokenBridgeCreator → `(router, standardGateway, customGateway, wethGateway, weth)` on the parent chain |
| `0x46052706` | `inboxToL2Deployment(address inbox)` | TokenBridgeCreator → `(router, standardGateway, customGateway, wethGateway, weth, proxyAdmin, beaconProxyFactory, upgradeExecutor, multicall)` on the Orbit chain |

---

## 3. Addresses — Ethereum mainnet (chain ID 1): Orbit L2 contracts

All addresses below have code on Ethereum (`eth_getCode`, 2026-09-29). Each row was resolved from its Bridge on chain (`rollup()`, `chainId()`, `inbox()`, `outbox()`, `sequencerInbox()`) and cross-checked against the Robinhood Chain docs or the Arbitrum bridge registry where the chain appears there.

### 3.1 Core contracts (13 Orbit L2s)

| Chain | ID | Fee token | Rollup (live, = `Bridge.rollup()`) | Bridge (escrow) | Delayed Inbox | SequencerInbox | Outbox |
|---|---|---|---|---|---|---|---|
| **Robinhood Chain** | 4663 | ETH | `0x23A19d23e89166adedbDcB432518AB01e4272D94` | `0xDf8755334ce7A73cCF6b581C02eA649AE3E864b3` | `0x1A07cc4BD17E0118BdB54D70990D2158AbAD7a2D` | `0xBd0D173EEb87D57A09521c24388a12789F33ba96` | `0xf0ce991ea4A0d2400A4AB49b20ae333f6Dce3DE9` |
| AlienX | 10241024 | ETH | `0x6fa8b24c85409A4fcb541c9964766862aA007f39` | `0x69aB55146Bc52A0b31F74dBDc527b8B7e9c7C27c` | `0x7b0159484f5cb4F3D4bb496A2eD7A01F409e70D1` | `0xb7d188eb30e7984f93Bec34Ee8b45A148bd594C6` | `0xCA2AA2AA53C2225849Cc711FD472E4D2bFcD634b` |
| AppChain | 466 | ETH | `0x28293c7855797B0441000EF144119727f3cBCA9B` | `0x19df42E085e2c3fC4497172E412057F54D9f013E` | `0x010aDE5d8F9DC340531140802438798C189c36E0` | `0x8045B2aa6b823CbA8f99ef3D3404F711619d3473` | `0x190C720892d0786BF75B77B4acD21c726ea8FDEd` |
| Dual | 6301 | DUAL `0x6aF487BEb661CCeCD1D045E9561A0dAC9AA5c7db` | `0x7c148C9c454916A36DDFAf282fb0F559e143cb7d` | `0xF568d6942808C3b57b4c85cFb6984Ec41D3cF83C` | `0x5A2626323F7D7113Dcd06b0a0De9A6e9945478Fa` | `0x6081bc691eF670Ae4F46de92680155880D19517C` | `0x432c4c0c2174E21346B6cA48998035e701C3262b` |
| Gravity Alpha | 1625 | G `0x9C7BEBa8F6eF6643aBd725e45a4E8387eF260649` | `0x2807B1d5d94ca823ca7d8642A5F5DDac120ce48f` | `0x7983403dDA368AA7d67145a9b81c5c517F364c42` | `0x7AD2a94BefF3294a31894cFb5ba4206957a53c19` | `0x8D99372612e8cFE7163B1a453831Bc40eAeb3cF3` | `0x1153a1e4B1523DFf36f77d696bd6eBF2B0e7DAbF` |
| HPP | 190415 | ETH | `0x8361fC54C99AdDbeD390Af68e7e6115323AB8DB1` | `0x9948eDFBb9e0b104bAd60393dBe79d0BC7937014` | `0xE0400a87d5Ee8a2Fc1dF2aAf4B6d8f89d0B9bE55` | `0x9B26957a661bc862FA0d7eb21813Aa008d0Cc6E6` | `0x433da6d107e942Ec4EAB1e86B16427B6071F6491` |
| HYCHAIN | 2911 | TOPIA `0xcccCb68e1A848CBDB5b60a974E07aAE143ed40C3` | `0x8f98f9ae2f2836Ed3a628c23311Ad9976B9fBF1B` | `0x73C6af7029E714DFf1F1554F88b79B335011Da68` | `0xD6c596b7ca17870DD50D322393deCE6C2085a116` | `0xaF5800ADF22301968613c37DA9C3C2a486eA915A` | `0x0389E24A4Bc96518169f83F50FCDdA442dD8eAFd` |
| Pepe Unchained V2 | 97741 | PEPU `0x93aA0ccD1e5628d3A841C4DbdF602D9eb04085d6` | `0x0aeAe1A2A6f24284aA676B1E93f44AdC1A712850` | `0xd3643255ea784c75a5325CC5a4A549C7CD62E499` | `0xE92Df19F4e0Fd067FE3b788Cf03ffD06Cd9Be4A7` | `0x93CA3db0dF3e78e798004bbE14e1ADE222B14dFa` | `0xd2E3B3be0ddA5E3214f551aF5A4f4049b9D031A9` |
| Plume | 98866 | PLUME `0x4C1746A800D224393fE2470C70A35717eD4eA5F1` | `0x4eD3F488a5a4417839BbC39712EB76D8Aaee6eE8` | `0x35381f63091926750F43b2A7401B083263aDEF83` | `0x943fc691242291B74B105e8D19bd9E5DC2fcBa1D` | `0x85eC1b9138a8b9659A51e2b51bb0861901040b59` | `0x7e4627bC114Fcd12ba912103279FD2858E644E71` |
| Reya | 1729 | ETH | `0xB55002d2795217Fd3B91EcBb3385ba9A231E5327` | `0x383c03c4EfF819E73409DbC690755a9992393814` | `0x672109752635177ebcb17F2C7e04575A709014BD` | `0x6CA2A628fb690Bd431F4aA608655ce37c66aff9d` | `0x3f373b0A7DcEe7b7bCfC16DF85CfAE18388542c9` |
| Shib Mainnet | 5816 | SHIB `0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE` | `0x5E96a2e830dF7A271383C6f516898feF5a57BbC5` | `0x577Dae1F00430d0013Bf0B0383C460f41d3e8a8f` | `0xdc62F39a24366e708D4E09560F73Df2Bd1542372` | `0xD65A35d19910d9F4E4aEB3CB4A87c3153BFB0FC6` | `0xe459eB07E9B4707CAA1520651d3a367177049c85` |
| SX Rollup | 4162 | SX `0xbe9F61555F50DD6167f2772e9CF7519790d96624` | `0x36c6C69A6186D4475fc5c21181CD980Bd6E5e11F` | `0xa104C0426e95a5538e89131DbB4163d230C35f86` | `0xEa83E8907C89Bc0D9517632f0ba081972E328631` | `0xD80a805c86C14c879420eC6acb366D04D318fC0C` | `0xB360b2f57c645E847148d7C479b7468AbF6F707d` |
| T-Rex | 1628 | ETH | `0x7705e53B707AF758aCEa86580d5da155d2fB2921` | `0x61C4b51f9388A2DD62C791341f0d50AD88d64Fd4` | `0x1744424936C6F1A4921130b12AA4F3832B421002` | `0xfF3e828FD206bD8491A7C77ABfb128860D314b6B` | `0xa0419E39cA100DCfC6F0d68D605d2445f387Fb4e` |

Names: T-Rex (1628) is named by the Arbitrum bridge registry and chainlist. Dual (6301) is "dual network" on chainlist (fee token DUAL, the BLOCKv successor). Shib Mainnet (5816) is named by an open ethereum-lists pull request (#8781); its RPC `rpc.shib.club` answers chain id 5816.

### 3.2 Token bridge L1 contracts

| Chain | L1GatewayRouter | L1ERC20Gateway (escrow) | L1CustomGateway (escrow) | L1WethGateway |
|---|---|---|---|---|
| **Robinhood Chain** | `0x6a2E3a1e16FC29f27Ce61429746D558d656975bB` | `0x85001CC4867C5e1C22dA4B79BB8852B9e2a06da0` | `0x9368EAEbFe6E063C69dcF8126711A6997E0eCeE1` | `0xF7e12b9614b509C747ab4423bC4ACF923759Cf1B` |
| AlienX | `0xeA685ba6f0C3ec5e7891C17CfFBD009EbAdC9E49` | `0x5625d2a46fc582b3e6dE5288D9C5690B20EBdb8D` | `0xC71B0d2cD97b5EC810Dd15D6EF39D196e7692262` | `0x20C42f28F8bac0972DB8d404bdDdea2EC175502D` |
| AppChain | none registered (`inboxToL1Deployment` returns zero) | — | — | — |
| Dual | `0x2b89168abD130ae8626aaD77Dc549Fa0C58Fc1C4` | `0x8595d3E4F504D8B970102c6bD881b272b10577B6` | `0xEd31AA96f1acBB02F1eE8a3E22c3aD8aE41EF30c` | none (fee-token chain) |
| Gravity Alpha | `0x8713569d016f981D956715e9EE2795382168b5c0` | `0xb23988D9728EF147EAa02D602D7e067B6131A1bB` | `0xa26Fd1c23634870303e42311E114D5cc8301Ed1E` | none (fee-token chain) |
| HPP | `0x1f948D3718b279d602887ca0FB28Df4EDF77023F` | `0x8F31c7a6806432F05A936Ade26a7407c968f13eA` | `0x2241e2a93b4DE8da10b0748d6b349bfB76DCC45F` | `0x8f10926536478dabff58A748C54385a346830546` |
| HYCHAIN | `0x9E795A6b44Ba1Ad02469C88ECA7348D60050051c` | `0xa3Ce255824D5E0c75d38CC88ae8D0d6a03c108Cb` | `0x86b6E73AC34D3Cc8b02ebf8BfB33db3cbf0e6062` | none (fee-token chain) |
| Pepe Unchained V2 | `0x5d9bD342cd880EA2697800622455E78887E4B22F` | `0x7c2838461fa468896a06CA1e7d88BDeCE1f2e1bE` | `0x91ab8D0913616DbF0c8B3b7Fc36a1e55cad323C3` | none (fee-token chain) |
| Plume | `0x17551CBD1ed02768b00D5Bd198c2D86a4c7ee43d` | `0xE2C902BC61296531e556962ffC81A082b82f5F28` | `0x2053fcB0AC660d8B6769dDD9d02031EDa103F440` | none (fee-token chain) |
| Reya | `0x905c0E4396403035e3B5CB14708cE7bfdC3Bc728` | `0xD117f93c458Bed69FCeEB8EDD4bABbce89DB0d67` | `0x3Efe8AA11AB79B7a2cd6671449ec927Df0e1e7ab` | `0x7bEaB88B958e2374C907d90831cffB92C9652d96` |
| Shib Mainnet | `0xf1bEacabBF3e5AF5b6Be70Cb17436575Cf6C052C` | `0x17fe731dfb2110AfeD0a1811f876E0b58603A6d2` | `0x4775cB0d2ab5922aE1FB27Cba08B2F7b675131d9` | none (fee-token chain) |
| SX Rollup | `0x5F00446D785421d65B50c192D7129e3C3906438A` | `0xB4968C66BECc8fb4f73b50354301c1aDb2Abaa91` | `0x54F4853fDfC80F6bA4e66a7946c2B9086B1dE45F` | none (fee-token chain) |
| T-Rex | `0xac586C4a3C8e4165d046ed3F64816058A5d4f00e` | `0xd1Fc6140377f4b8F31f250B922B5a6A59eFaAC41` | `0x043349BFE53Ba7684492c49eDbF8355205e5e454` | `0x8CF7f2E0E29ACd80A7dab0A4a9d2b5C6Da706166` |

All token bridges above are the TokenBridgeCreator records (`inboxToL1Deployment(inbox)` on `0x60D9A46F24D5a35b95A78Dd3E793e55D94EE0660`). The Robinhood Chain row equals the Robinhood Chain docs, and the SX Rollup, Gravity Alpha, HPP, HYCHAIN, Plume and T-Rex routers equal the Arbitrum bridge registry. Wiring read live for Robinhood Chain: each gateway's `router()` is the L1GatewayRouter, its `inbox()` is the Delayed Inbox, and its `counterpartGateway()` is the matching L2 gateway of §6.2. The L1 WETH of every ETH chain here is the canonical WETH9 `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2`.

### 3.3 Rollup generation, challenge period and admins

| Chain | Rollup generation | `confirmPeriodBlocks` | UpgradeExecutor (= Rollup admin slot) | Core ProxyAdmin (= Bridge admin slot) | RollupEventInbox |
|---|---|---|---|---|---|
| **Robinhood Chain** | BoLD | 45,818 | `0x552603b4bc1f5E896AF2854548D6380f45f1B4bf` | `0x1232813BDd40aa9d53066A880dE78a4Be70B90FD` | `0xc34f4907822d1cDC6aE3038Be22e6f12DEa35bd4` |
| AlienX | classic | 45,818 | `0xD4972734Ed659c03ca3e476e06Fc6f016397dfD4` | `0x123C1E324BC742295B4278B41C4E33831C77655C` | `0x01c1Be00BA202332a1A9244D2C36f51B8C2aA84b` |
| AppChain | classic | 45,818 | `0x7c4e8195FB560D1557C52f051dCdA4724a2894b3` | `0xF025D25aE360D0D33a275dF74863CCc6600E6f8E` | `0x269F6f6FC8177a5A8c475AE0e2487508634EC8Ed` |
| Dual | BoLD | 50,400 | `0x552DaE0665423D7FeEEF022897E251e36e3c39D8` | `0x55E7207620380F4D8aD7687ACa9B6F5DF2F66ea0` | `0x9beBBe909cA6AaBd250751c81B71890cBD37999f` |
| Gravity Alpha | BoLD | 40,320 | `0xa5D23c69894241825dAffB570c3c742C0F52df96` | `0xBbc3872E30C91ef69336937838c2a283F79f7E68` | `0xa24eDA32bb36171a6c34CBB4B56f89FF7B8fD49A` |
| HPP | BoLD | 40,320 | `0x988abda4487731e37623A0c282547E36d7B311a9` | `0x662e2446598Cad19f8dc74d912126B044C5F57ec` | `0x7c32F1044bABE5270115717BB35f2a3CA1be165B` |
| HYCHAIN | classic | 45,818 | `0x88d3f3F43Ecd46635bd9f546bE7C4d52eBc20881` | `0x4C5984E3841790335E6DC2e7ed92802FbF8a300F` | `0x617f70525Dc4D2BBbd6ADFd3781DbEAe5C8F0048` |
| Pepe Unchained V2 | BoLD | 40,320 | `0x53E276D701Fc2338F6F015B0038Ce8ba3d5d01CC` | `0x16a93209382236236e964b9C22853e34C3095028` | `0xd1AF4aD8Be9a8A2f288048140c6E6380420c55fA` |
| Plume | BoLD | 40,320 | `0xd688dabDBb14D673898689135a23a174560c8C04` | `0xb90fe445014e74eA5aA7681291212bfEa37031CC` | `0xf576102530749344D2f4C04D15C2B8609c7897ea` |
| Reya | BoLD | 45,818 | `0x07390626b8Bc2C04b1D93c7D246A0629198D7868` | `0x74627dd54FA6E94c87F12DBAdAEc275758f51dF9` | `0xFd9f59554351122b231F832a0e0A1aBb0604D7fd` |
| Shib Mainnet | BoLD | 50,400 | `0x0FD84dD33327c51908F7fB0D24043289bC801d9d` | `0xa084e573831ae38C1Ce628C4F6FE94F1E56dbAD0` | `0xE9EdeE59B9fc5eBcDBa4F47132592D0e72058d5d` |
| SX Rollup | classic | 45,818 | `0x44Ec40D86b4643Bd5110ED07BE188F8473Ad2d3a` | `0xe8606A55d105EF857F187C32Ae0E9a168aF8F497` | `0x9f1045201f8b9D0b12f6d1e40e8B8e6c047A81E3` |
| T-Rex | BoLD | 7,200 | `0xde50DB75a0f2E8a0678bd42Ef005f63F7a0dA515` | `0x25E0f32b13cBfd9B076FD921e72fc1101530fdF1` | `0xD7C5161e1165Ec3F75B499831fB0FD8f6317C996` |

Robinhood Chain's UpgradeExecutor `0x552603b4bc1f5E896AF2854548D6380f45f1B4bf` answers `ADMIN_ROLE()` / `EXECUTOR_ROLE()`, owns the core ProxyAdmin `0x1232813BDd40aa9d53066A880dE78a4Be70B90FD` (`owner()` read live), and is the Rollup `owner()`. Its ChallengeManager is `0x6f38FC91105Fc9a43931DcA33450ab3315E3D4Fa`. Robinhood Chain also lists an L1 Multicall `0x7cdCB0Cc61f47B8Dd8f47C5A29edaDd84a1BDf5e`.

### 3.4 Other Orbit chains that settle to Ethereum

These chains posted batches in the pinned window (their SequencerInbox emitted `SequencerBatchDelivered`), or they are in the Arbitrum bridge registry with Ethereum as parent. Each row was resolved on chain from its SequencerInbox or Bridge; names come from the Arbitrum bridge registry, `chainid.network` and chainlist ("Studio Chain" for 4509).

| Chain | ID | Fee token | Rollup generation | Rollup (live) | Bridge (escrow) | Delayed Inbox | SequencerInbox | Outbox |
|---|---|---|---|---|---|---|---|---|
| DIA Lasernet | 1050 | DIA `0x84cA8bc7997272c7CfB4D0Cd3D55cd942B3c9419` | BoLD | `0x769b70b6b1fA281ab5c99e9C5A284BE4117e4783` | `0x1eeE9b9F024188E54930D2927d7a28e66E7649a7` | `0xa2809b5f031bf91d2408B3e2464774A28B0F4949` | `0x661b39a5EB200dFcbb436d98453BdBf88Da02AA1` | `0xDb5abc57397530DddC1e33BC023F2ef73Db6A86A` |
| Humanity Mainnet | 6985385 | H `0xcf5104D094e3864CfCBDa43B82e1cEFD26A016eB` | BoLD | `0x4ef3463F0Ffc1E9bfe30f72D705C259A0A0cCb56` | `0x8620F893F6321C31909e4a58bcEb6948A289e0fD` | `0xe7D7C04885f460e0c58504D617C65ab064A4879D` | `0xa80dD081B83399614fa0BB497174Bdcb3EF4Efe6` | `0x74045319D890f0C0CD7914F2DE757F25492331f0` |
| Humanity (id 13600000) | 13600000 | H `0xE76c5b78f93909d34404E9eb4C1f19e7582a5dE1` | BoLD | `0xc9233936E49ff34ca35fdB2F0C11f203F8f259B3` | `0x29786f674ED06684C5493aA5071b8B6F235Ba411` | `0x11e947d771A9282292d52aC855EB912A55761e3d` | `0x6dC90693715f04fA363D4D3dAA99123C60319ca9` | `0x9FBb23735eD9a1fB43dc99066eb1eAF196c05A3D` |
| Galactica Mainnet | 613419 | GNET `0x690F1eEf8AcEaD09Ac695d9111Af081045c6d5b7` | BoLD | `0xf3B30Fd67211C57e2Cc36D5a41dB28415AF55BB7` | `0xd75a60aFcBC113C1c76e42184663Da141f839053` | `0x46a2f92Fa215eBc734e51b26da3d205de71FA930` | `0x2fccc2de02Dd598E14403C4151F192d962E646Ba` | `0xC327F5cDBAAc8879EE8017A0977C9a685A850a4F` |
| Symbiosis | 13863860 | SIS `0xd38BB40815d2B0c2d2c866e0c72c5728ffC76dd9` | classic | `0x2d16B1CA78079A1C3e79c93d017558c7d685E57f` | `0xE61FBe55EC57394B02BDB6a88c3D71ADb2d63826` | `0x3ad488cD8b0705B6Ede84c275f764541ab9B36AD` | `0xa150Ff19A31E1054f950098869834afFe9bC6fdC` | `0xa925C3f804A6c0e048a15bF1BEcBf517a31d1Dae` |
| Mandala Chain | 20010 | KPG `0x5a30Ed2D3650c99e9B0de9063982495e9818BBE2` | BoLD | `0x218D35154D1efEBFC46D64451C9495288219b275` | `0x65DB181838b53f32428ce106fA5355b7e4806b79` | `0x62DfD05c460C7E55DA85B39EaD3eBc6e0CcdD0d5` | `0x325acf46079d3f750D5D7E6182E094B1fD0AC2F4` | `0x004eF39261cee56409Dbd26040a33Eca8326490C` |
| Citronus | 50000 | CITRO `0xA1366679a500050026EF84DB26c09d3774358954` | classic | `0x7dcB571b6897d22dC4f6e75beC660B632688617b` | `0x9016fA334b99282B01a9507a607861AD333e9315` | `0x4E82220a80C0929841084922132ECBEB0F2215D5` | `0x3410a45FCD0adbF859E6D89d6E9b74B337d95F8D` | `0xC386cab2867CF6e0e20594FC044dbf3A3c7c5BcC` |
| Studio Chain | 4509 | KARRAT `0xAcd2c239012D17BEB128B0944D49015104113650` | classic | `0x8f69Df10286393D6C4015B0a4cBCbC6858C50999` | `0xca5F6Ec5c9b482BfDaaE6074e7686e7Fbd4755AD` | `0x0E22B2568b765af4b0828210e09e4c9838E4B6c1` | `0x2e1d9bf177d3Be96320F25b776D2fD4068b6a732` | `0x3Cf9DF7a28D33B31f00B0DEd826f19931654bdcb` |
| XCHAIN (no batch in the window) | 94524 | ETH | classic | `0xeb61c3FA03544021cf76412eFb9D0Ce7D8c0290d` | `0x2Be65c5b58F78B02AB5c0e798A9ffC181703D3C1` | `0xE961Ef06c26D0f032F0298c97C41e648d3bb715a` | `0x47861E0419BE83d0175818a09221B6DF2EFD7793` | `0x0b8071337dcB089478Ea740efC10904d9F359141` |
| Plume Legacy (no batch in the window) | 98865 | ETH | classic | `0x59EF2FBa6ED4366cb1C3F67f232aaf824B536AB9` | `0xd53645c6b5e19b3CE2d00bA27d734dCC928FCC54` | `0xC45276467BDb1a9D083010c7CA7Fe2d593a10d01` | `0x3fD761A6eFC2137F03f03Da3d46933dD2e6FF0BB` | `0x4e3C79Bf30Fc3d4Cf975dE1596e7Fb9Bfd0bf192` |
| Syndicate Network (no batch in the window) | 510 | SYND `0x1bAB804803159aD84b8854581AA53AC72455614E` | classic | `0x451bD7813909B899DA6EbEC55E8fF823c057e14A` | `0x3C8cF0ae6E89AC0796f29B3a58e7dEa1cD072277` | `0x5EA55Fd41D42Eb307D281bdE78E4e7572A35ea13` | `0x12ad349e5d72B582856290736e0f13FE5fA57Aa4` | `0xf555Bc86D1C953414F676479Bf7C979b1A737E8C` |

Token bridge L1 contracts of these chains (`inboxToL1Deployment(inbox)` on the TokenBridgeCreator):

| Chain | L1GatewayRouter | L1ERC20Gateway (escrow) | L1CustomGateway (escrow) | L1WethGateway |
|---|---|---|---|---|
| DIA Lasernet | `0x6072E7BC21E64f0b957B6Fe192f6b590E53949F5` | `0xDD9f0252Dc82fDCDf71E38C214AF9340d80F6E56` | `0xAeBCCf13bFc076CD95bc223ef14D721cE62dA496` | none |
| Humanity Mainnet | `0x0266191d2a5ED66A308874E9266099039AF19cD2` | `0xa84A5f9565DB67129Be5bEb7fA94dB0F74098f37` | `0xdbcC9e1e24C0b8f9b7bEE5b32E0A9332D9818686` | none |
| Humanity (id 13600000) | `0xfBb16dFD0C79783EDe0C6B51c95E807f2e1640Ee` | `0x1759C81B758eC80F8DDEb760E069A6afef4B4e26` | `0x76b77D588629d8C837396dE5F295A9665b5c1AA9` | none |
| Galactica Mainnet | `0x8200d6f1f080DDc28Ec6ce2972999C9Cbd014B07` | `0x15B37ad0bE0cCB5Cdb3004d740E5D2d95C08cD9e` | `0x2AA8436882f207aD42dD62B169650EDe658B2BB0` | none |
| Symbiosis | none registered | — | — | — |
| Mandala Chain | `0x9E615026f372Bd8EAe831f88ad661D5d5fBb2c9f` | `0x920B251832F273b2127D3163815971ae96226beF` | `0x5f46e3cA07b8a55cC90Ff8fEcC14264A9C7762B6` | none |
| Citronus | `0xb9fF366C6Ce207D35f0b8656320E4CbB43A1f6d5` | `0x2cf6c1Cc409A8747B4769b6c26C198FE46596f69` | `0xf935404762d8349461f8ed3E32A720252a7C261E` | none |
| Studio Chain | none registered | — | — | — |
| XCHAIN | `0xe0a99350288971456EE4BAc4568495352929B769` | `0xFFb821ca61e823a884D79226B0fcD7a99A4d48aa` | `0xEFb1F8ae759c595907782e9bD45F119c9814b308` | `0xCAde60b1331f1cF714ECb01f08117780887A0AF4` |
| Plume Legacy | `0x5b4658BA87c2aB8A5555D402B0dc4a4Fa0546134` | `0x54504F3F4304394BedE5420a565b79d41E3060BC` | `0x7F78Bb34c2525d0a42989B0228376edE11611a6D` | `0x82F584b8edfb05464163D7492c503D49a64FAD8d` |
| Syndicate Network | `0x534Eb1F79C8df3aB1E507e408EeF4e99D53A1239` | `0x6CA109706c6EBe5379c45f20B3311441D50cb711` | `0x85C88ddc2f525459E243AB27D6059f55Ce80EB0c` | none |

Mars Chain (704851, chainlist name) did not post a batch in the window, but it made an admin change: its UpgradeExecutor `0x4f731ee18887aD3EBd57483217A0F085b8De1985` (its Rollup admin) emitted `TargetCallExecuted`, and its SequencerInbox `0x357B846f75c0AAF643f94c9b26f050eAE843Cb28` emitted `BatchPosterSet` in the same transaction. Its Bridge is `0x8b4Fea8C461178b88764BDd1ED55511ADe8ED2D0` and its Rollup `0xFe4c435944aa9530E3A2F8A0B7561838Ba89E249`.

### 3.5 Factories on Ethereum (Orbit SDK address maps)

| Factory | Address |
|---|---|
| TokenBridgeCreator | `0x60D9A46F24D5a35b95A78Dd3E793e55D94EE0660` |
| RollupCreator v3.2 | `0xe06Bc77336E201c4C08751918A4bB99ddf0e1Bf7` |
| RollupCreator v3.1 | `0x43698080f40dB54DEE6871540037b8AB8fD0AB44` |
| RollupCreator v2.1 | `0x8c88430658a03497D13cDff7684D37b15aA2F3e1` |
| RollupCreator v1.1 | `0x90D68B056c411015eaE3EC0b98AD94E2C91419F1` |

---

## 4. Addresses — Base (chain ID 8453): Orbit L3 contracts

All addresses below have code on Base (`eth_getCode`, 2026-09-29). An L3 on Base keeps its escrow, inboxes and Outbox on Base, so its deposits and payouts are Base events with the same topic0 values. The two listed L3s: Tranched (743) Bridge `0x08abBE019C351D5124256D3602da6a5a40fa7C72` and chain 846737 Bridge `0x9d4AB2E611a7b9Fdc0168C4C1EEd563eba35A43D`; the TokenBridgeCreator on Base is `0x4C240987d6fE4fa8C7a0004986e3db563150CA55`.

### 4.1 Core contracts (the 2 listed L3s)

| Chain | ID | Fee token | Rollup (live, = `Bridge.rollup()`) | Bridge (escrow) | Delayed Inbox | SequencerInbox | Outbox |
|---|---|---|---|---|---|---|---|
| Tranched | 743 | ETH | `0x4D18AbAc5A46f387Df6c0fC13D7f057C43231666` | `0x08abBE019C351D5124256D3602da6a5a40fa7C72` | `0x02064f9943015B5675972e04289849a5F706d8Fa` | `0x53C8693D544359ED82F4009cC3a668DAf89349A3` | `0xB42f8b96CbC3F455474c3C0a2914d45BFa675161` |
| unnamed (fee token PANAX) | 846737 | PAX (name PANAX) `0x9Ffb8BAE5feD58AF7dC06C096D1AfC981DE8A387` | `0x2abc91f8C84C548a7F388F59e8BD10dbFB5E994F` | `0x9d4AB2E611a7b9Fdc0168C4C1EEd563eba35A43D` | `0xAFbB601aa3c5F7D38e8C19422A9a16EcD066bCde` | `0x9fE4399563Cb6e1Bbb0947d51420Dbb725b16ffE` | `0x12097891604714718b1eaf24C4e7c5BcBFBc6A0A` |

Tranched (743) is named in `chainid.network` (Caldera-hosted). Chain 846737 has no registry entry that this research found; its fee token reads `name()` = `PANAX`, `symbol()` = `PAX` on Base.

### 4.2 Token bridge and admins

| Chain | L1GatewayRouter | L1ERC20Gateway (escrow) | L1CustomGateway (escrow) | L1WethGateway |
|---|---|---|---|---|
| Tranched | none registered (`inboxToL1Deployment` returns zero) | — | — | — |
| unnamed (fee token PANAX) | `0x95A7E6c232D4650A25fEbD2a92f741360E267c70` | `0x11D203350A7B5177aD94efe04acda422564295a6` | `0x13D38d37d0f9416A4b690189A9Ea69951d413dA5` | none (fee-token chain) |

| Chain | Rollup generation | `confirmPeriodBlocks` | UpgradeExecutor (= Rollup admin slot) | Core ProxyAdmin (= Bridge admin slot) | RollupEventInbox |
|---|---|---|---|---|---|
| Tranched | classic | 274,908 | `0x94f31b29F467d1aFae66EdFE482f7bc49cD4F39c` | `0x1740ea0B40F4a7252B82419926A883D709e12384` | `0x7E60fA9797989541f94a1DF9395fAb5Ab67032B9` |
| unnamed (fee token PANAX) | BoLD | 302,400 | `0x58f7836CAc6c1311dDbf6b559749938a0158027b` | `0x9DE3e35E9Be0468d111D2c4354922b5E2Aa8Ab68` | `0xDccd50fcb23F8eE17Da35Eda78f8f478fAa1b46E` |

### 4.3 Other Orbit L3s that settle to Base

| Chain | ID | Fee token | Rollup generation | Rollup (live) | Bridge (escrow) | Delayed Inbox | SequencerInbox | Outbox |
|---|---|---|---|---|---|---|---|---|
| World Mobile Chain | 869 | WMTX `0x3e31966d4f81C72D2a55310A6365A56A4393E98D` | BoLD | `0x851c037dF70A208573A2D635744BbEdaa21A0959` | `0x249888c93F18f50a0EcA6a29b644F8Fa1Ff7539d` | `0x46EE1145523b58125fF5ed02A8946F748B9735FB` | `0x3Ba9426AcC831cDDa0Dd0b537f6b4E98670Bf280` | `0xa38d087580480A2266D2e50656bF43a39982c694` |
| Intuition Mainnet | 1155 | TRUST `0x6cd905dF2Ed214b22e0d48FF17CD4200C1C6d8A3` | classic | `0x6B78C90257A7a12a3E91EbF3CAFcc7E518FAcD38` | `0x98EC528e10d54c3Db77c08021644DBe48e994726` | `0x9F82973d054809dD9cae4836d70ce70DcE1403B0` | `0xFC239694C97b06BF2409C88EA199f7110f39A9bF` | `0x8830c56BAe59ac366DeCddB32F33851002e14251` |
| XMTP Mainnet | 241320162 | xUSD `0x63C6667798fdA65E2E29228C43fbfDa0Cd4634A8` | classic | `0xB6B4C28278FbBF444Ff7B6dF8fEdB7Bc90f72924` | `0xA9C3B7672C477EeDA999A3ab1c8Eec28DEEB7d41` | `0x249D5D37502f26c5286De3096e0120FeAFa6772a` | `0x5107C4267F13D0e55eab45A3129DB04AE8BB1AF3` | `0x5997b6350580178f0eaD414500eBA266b3C8d569` |
| unnamed (fee token F2) | 414 | F2 `0x7b460a17Df7ECb04Fa44ec700F90a48306239996` | BoLD | `0x66dEe37F11CFF58BC3e1BB1F8977a5AE91bBE1d0` | `0x2dF9DeA9c9289bae9658CB732c45D0B0657341E6` | `0x9F7454C56B571474167506aBaFb6372Ea819482d` | `0x979487D5dd1D3E7E6DCf16197EcBeb918BA7b7de` | `0x49B29C4154a70682E651470eE80c5fDE43E9382a` |
| Crynux on Base | 18896214 | CNX `0x9557DD9E241bc9636732623B672B4090AF519396` | BoLD | `0xC351e736615aE833759E5E4BDc331170f0c8553A` | `0x01D9Db097DC8b30EFbc266fd80b233fB6b6BFF40` | `0x02DEE6E98b651c73B60D8D0282a1DbE04F8Ce575` | `0xb413CADD409Ef1392d60E4152e6124Af28051733` | `0x4039CB909D11558a31Df28705d5Fd12FE8b7D239` |
| Unite Mainnet (no batch in the window) | 88899 | UNITE `0xA6C6ea2e0140849bE02A3a34780CF61b766916c5` | classic | `0xd6df93D93c2554412622C567965DA7B16929f0A5` | `0x80b4c2dBEacFF9921cD456e5E1489919185b8a1d` | `0x319a9c8be1CF9ECB16D29d6327A6Fa2e26Bf42BC` | `0x3A2898B10c88cb619635efdC027538D7Aa99BF79` | `0xd9AD042DCb18628a941C8868bf25e5eCf897E48c` |

Token bridge L1 contracts of these chains (`inboxToL1Deployment(inbox)` on the TokenBridgeCreator):

| Chain | L1GatewayRouter | L1ERC20Gateway (escrow) | L1CustomGateway (escrow) | L1WethGateway |
|---|---|---|---|---|
| World Mobile Chain | none registered | — | — | — |
| Intuition Mainnet | none registered | — | — | — |
| XMTP Mainnet | none registered | — | — | — |
| unnamed (fee token F2) | `0x19436A7f17218b08c9E954e164F81EA545021f88` | `0x12ba69299Bb66c1A806E637895c6053f1262122c` | `0x1Af5B40252BcC80814eF1f67d0Df054206E5e283` | none |
| Crynux on Base | `0xcA1D420cF2e85AfB4E2CFAaF40626F45969D82C0` | `0x1B39D3bfD021006c7753848004c37613c5ed0429` | `0x9b80E9e9b3B150267D584aE197799E10F98C1C2a` | none |
| Unite Mainnet | `0xbaD53A171A9D0785EC179b5C3eFd3d7083b8D3a7` | `0x03b9C7978143A3A360cb37101F2A3f7f1B0eE8e8` | `0xeA2Ffb3BA907418a5a9A9Cdb90212c814230Ba5d` | none |

Degen Chain (666666666, fee token DEGEN `0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed`, classic Rollup `0xD34F3a11F10DB069173b32d84F02eDA578709143`) also settles to Base: Bridge `0xEfEf4558802bF373Ce3307189C79a9cAb0a4Cb9C`, Delayed Inbox `0x21A1e2BFC61F30F2E81E0b08cd37c1FC7ef776E7`, SequencerInbox `0x6216dD1EE27C5aCEC7427052d3eCDc98E2bc2221`, Outbox `0xe63ddb12FBb6211a73F12a4367b10dA0834B82da`. Its Bridge also allows a second outbox, `0xDb8E759859058952c34953c8469f464109826e52`, which paid both of Degen Chain's 2 `BridgeCallTriggered` in the window (§9, item 5). No token bridge is registered for it.

### 4.4 Factories on Base (Orbit SDK address maps)

| Factory | Address |
|---|---|
| TokenBridgeCreator | `0x4C240987d6fE4fa8C7a0004986e3db563150CA55` |
| RollupCreator v3.2 | `0x8d1668636D053C10F57367D68118bD624f41ffe6` |
| RollupCreator v3.1 | `0xDbe3e840569a0446CDfEbc65D7d429c5Da5537b7` |
| RollupCreator v2.1 | `0x091b8FC0F48613b191f81009797ce55Cf97Af7C8` |
| RollupCreator v1.1 | `0x850F050C65B34966895AdA26a4D06923901916DB` |

---

## 5. Addresses — Arbitrum One (chain ID 42161): Orbit L3 contracts

An Orbit L3 on Arbitrum One keeps its Bridge (escrow), inboxes, SequencerInbox, Outbox and Rollup on Arbitrum One, so its deposits and payouts are Arbitrum One events with the topic0 values of `core.md` §1. The set below is every Bridge that emitted a Nitro event on Arbitrum One in the pinned window, plus every chain of the Arbitrum bridge registry whose parent is 42161. Each row was resolved on chain from its Bridge (`rollup()` → `chainId()`, `inbox()`, `outbox()`, `sequencerInbox()`, `nativeToken()`), and every address has code on Arbitrum One (`eth_getCode`, 2026-10-01). Names come from the Arbitrum bridge registry, `chainid.network` (Edge, CarrChain, Animechain, Miracle Chain) and chainlist (Ethereal, Mawari, Superposition); a chain without a registry name is labelled by its fee token, and its name is unverified. None of the 34 chain ids is a target chain.

### 5.1 Core contracts (34 Orbit L3s)

| Chain | ID | Fee token | Rollup generation | Rollup (live, = `Bridge.rollup()`) | Bridge (escrow) | Delayed Inbox | SequencerInbox | Outbox |
|---|---|---|---|---|---|---|---|---|
| unnamed 2886 (ETH gas) | 2886 | ETH | classic | `0xA113e2E9620a3Bc088a681eBB2C234FDbeb85e21` | `0x53a7559d1e57E371F3D1e55Fea97e9B6748418a3` | `0x14F38F96C4CAB971D0Ec466241c422b23d0FA992` | `0xE79283a775f6A1de250cB3284E7fF3541ff7668A` | `0x47dA6c41d03Ac0608924e86f61577df558114Bd8` |
| Edge | 3343 | ETH | BoLD | `0x0D9cCeB5Cd108CC9B0b7Ac3aACe3d85c28243c9e` | `0x6F4836aFD5e21EDcee9b838C5a4125829EC198d0` | `0xeB88b89e085D6B747Dd6b9CEaf2716bdd89F1E7c` | `0xe44B83D8a3A86994043C809E29B723a44FAEE479` | `0x9f427c80C4DF962726808d4c876fc2c55474a764` |
| ApeChain | 33139 | APE `0x7f9FBf9bDd3F4105C478b996B648FE6e828a1e98` | classic | `0x374de579AE15aD59eD0519aeAf1A23F348Df259c` | `0x6B71AFb4b7725227ab944c96FE018AB9dc0434b8` | `0x1B98e4ED82Ee1a91A65a38C690e2266364064D15` | `0xE6a92Ae29E24C343eE66A2B3D3ECB783d65E4a3C` | `0x4F405BA65291063d8A524c2bDf55d4e67405c2aF` |
| Xai | 660279 | XAI `0x4Cb9a7AE498CEDcBb5EAe9f25736aE7d428C9D66` | classic | `0xC47DacFbAa80Bd9D8112F4e8069482c2A3221336` | `0x7dd8A76bdAeBE3BBBaCD7Aa87f1D4FDa1E60f94f` | `0xaE21fDA3de92dE2FDAF606233b2863782Ba046F9` | `0x995a9d3ca121D48d21087eDE20bc8acb2398c8B1` | `0x1E400568AD4840dbE50FB32f306B842e9ddeF726` |
| unnamed 8818 (fee token CBIT) | 8818 | CBIT `0x87f71CBC3a55700059eDcFa9c36fE43B59dbfB6b` | BoLD | `0xc5f29A8911a40ce5E56984F0Fe15802ab4Db4cd0` | `0xaA4f1669d4f366626fD0630B2954883143e1Bc3D` | `0x9869baE89F17d6CE1d2CA8B62d057Ecb15379fE3` | `0xAB08DA432C583F295b9D52B51cd9E7c678c1C2Db` | `0xAE4c2bD2c65dA85dE6c7Fe8eF45e519c2de6Eb79` |
| unnamed 4485770 (fee token COR) | 4485770 | COR `0x1CA54aEC8205e6F11b48bba222e7BB02b4e253c3` | BoLD | `0xfcE3c8F7CaaF42B2078426Abd314D8c8C437608c` | `0xE486cCb88ac257b2c55Fc3d5F222cCc895812121` | `0xDa901334BcCf813e4b1E13dCebd8BB58a1668448` | `0xECf0d637AAf5161bD97d4c9496aCFe71F6CF54e5` | `0x7f5F2Ebfc839AD8805e54c8D43020E47A485492E` |
| Mawari Mainnet | 1576 | MAWARI `0x0101bb150d4Ad6A7D19f705D1dee0E0BF4C413ab` | classic | `0xa06071BACbF598ff18fA4a1Efd8c62431ed1B1cB` | `0x3437Bd1A174E0528989Ae0d5023c05018502Cc34` | `0x4978e023914457E55c2A9A7587Fc8cf20F280FA0` | `0x0a1d9315C08692CBE7772Ce32D49a5D62F1D3eD9` | `0xf7De01ecb4E4Df7F57c6939A90fF85707871F094` |
| Miracle Chain Mainnet | 1247 | PNIC `0x19D33c4B6Ef26591cb6E74028454a82F24a4A4b9` | classic | `0x3f443872274b01c9a34D1ca9754969D8777Fd156` | `0xa4b7c8ae3CcB4960F45E753C5690902ef53CB28C` | `0x6aDEaC411242Ab18CC82006E719978EC10826871` | `0x16133A3B784aDdEca487F2f7f7A44b8E8888b8E6` | `0x6689ee70a8493D94f887AddF05A6A88036cFca57` |
| unnamed 61022894 (fee token DKA) | 61022894 | DKA `0x1E2C41d3fF045488D0921591e6B5532583e54F1C` | BoLD | `0x11e3D0e9604a0AD8a8B32068B95e83d7C63b3af7` | `0x42C4b496edA79215872De91f71D77F434098e162` | `0xB17a5495FA25FBcA887083b7048Bc60A796A201B` | `0x48781bAec9B5f9eBCf6fd96134f24231c6987Aa0` | `0x947fe294C167A6e9b7bc5c328AeF0aCe9ac83584` |
| Ethereal Mainnet | 5064014 | USDe `0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34` | BoLD | `0x75c070fe237817Bd027d402327069e9cd07De078` | `0xd86f5ad3fa5becbB07e565DbD4b70DBd817A43A8` | `0x574b121c469583c3a46cd88bBCC9Ac5c8C907d06` | `0x0E2480384E3703FDf84c7A0448658E8C7543b3a8` | `0xA2A5DCA414e3AaBD48B9CA97426f7e3Fba967492` |
| Animechain Mainnet | 69000 | ANIME `0x37a645648dF29205C6261289983FB04ECD70b4B3` | BoLD | `0x5Ca07271b6728150d6472FaADbF6D392d57765a0` | `0x8764106F840841183855e291a0E64b40Cf20d9D3` | `0xA203252940839c8482dD4b938b4178f842E343D7` | `0x180546907e94A8e556D8159BB399FC4E017131Fb` | `0xbb71461A2D4665E03F272B145695fD3E96bBD7e6` |
| Edu Chain | 41923 | EDU `0xf8173a39c56a554837C4C7f104153A005D284D11` | BoLD | `0xC92793985e0026583Dc70aBDFBa167b1932b834D` | `0x2F12c50b46adB01a4961AdDa5038c0974C7C78e8` | `0x590044e628ea1B9C10a86738Cf7a7eeF52D031B8` | `0xA3464bf0ed52cFe6676D3e34ab1F4DF53f193631` | `0x6339965Cb3002f5c746895e4eD895bd775dbfdf9` |
| Earnm Mainnet | 32766 | EARNM `0x3e62fED35c97145e6B445704B8CE74B2544776A9` | BoLD | `0x2E3f48e1A9B9849e5c0e4Fe987AEa2dA1702Ddda` | `0xA9F4ee72439afC704db48dc049CbFb7E914aD300` | `0x446626827f14F89B38D5bA1ab152B484cd7912fD` | `0x38d41Ac2fbc3f13FcA7838F6638D8FbDb189e807` | `0x39919941b42DAb335d9924Ef56dF7b9813b2D6d9` |
| unnamed 529375 (fee token LYK) | 529375 | LYK `0x83A32F2818b6754F7d58af0e559fA9d3fA99ce13` | BoLD | `0x9f7C924189BB3e4a063429181c05cD78690f1F07` | `0xe8c495583789A49b90d2DE3021bCc5bf42673F89` | `0x108964DDACAc3420Fe46c291031a59721dFFA637` | `0xA59c2F62C0d53fe4439df7b4B995b768d9088b9d` | `0xD6a1337bEC237D0BaFC8d4801463FA0e15Db481C` |
| CarrChain Mainnet | 7667 | CARR `0xFa0F7D729d6959aF6a95de58e4898071E8D2C438` | classic | `0x9177FdE42aD13B108E85563d67659F342a38CaF9` | `0x1157f519750BDB190c4AD847aC2f53E805Df5c0c` | `0x160Aa559Cc86f12B27a77e7E076fF3162EF945B0` | `0xAEdaFDa97324FfB00794f96A5c339F339673fa0C` | `0xbc7126712808bcf78c05C990F61038aF252F623D` |
| unnamed 20231119 (ETH gas) | 20231119 | ETH | classic | `0x846387C3D6001F74170455B1074D01f05eB3067a` | `0xD4FE46D2533E7d03382ac6cACF0547F336e59DC0` | `0xFF55fB76F5671dD9eB6c62EffF8D693Bb161a3ad` | `0xe347C1223381b9Dcd6c0F61cf81c90175A7Bae77` | `0xA597e0212971e65f53f288Ff1fFd26A6C8201f83` |
| unnamed 261131 (ETH gas) | 261131 | ETH | BoLD | `0x92EE92a148cf8431424dB3fB55AB12934B0AF1a6` | `0xB95b70f48C9F45293d1EE6670d0C5D8D4F045e46` | `0x893a8A0d0FC49cEA7d27dac7E5Ab760639A041C7` | `0xAe7B43ec6f8d0EccebB7879Ddc42dab57b75654D` | `0xE1eDC1c92B198761d0e9977862B6D12d9Ee8fCD2` |
| unnamed 27182 (ETH gas) | 27182 | ETH | BoLD | `0x869E22EC4a03BF7145074396F1Cfa1385B1a61f2` | `0xcfa2a006e3bf72a7BD300e2a04295D69F9934b73` | `0x9e78cab4838829F59F9a722b5635a2e501767233` | `0x2E711DB78831e24439C29d13CB0Bce44C4Ef1956` | `0x5c3A45540859D631Fdf4eE7076d606BCDf43dB6A` |
| Sanko | 1996 | DMT `0x8B0E6f19Ee57089F7649A455D89D7bC6314D04e8` | classic | `0x9A59EdF7080fdA05396373a85DdBf2cEBDB81Cd4` | `0x2f285781B8d58678a3483de52D618198E4d27532` | `0x718E2a83775343d5c0B1eE0676703cBAF30CaFCD` | `0x24B68936C13A414cd91437aE7AA730321B9ff159` | `0x575d32f7ff0C72921645e302cb14d2757E300786` |
| RARI Mainnet | 1380012617 | ETH | classic | `0x2e988Ea0873C9d712628F0bf38DAFdE754927C89` | `0x255f80Ef2F09FCE0944faBb292b8510F01316Cf0` | `0x37e60F80d921dc5E7f501a7130F31f6548dBa564` | `0xA436f1867adD490BF1530c636f2FB090758bB6B3` | `0x91591BB66075BCfF94AA128B003134165C3Ab83a` |
| Muster | 4078 | ETH | BoLD | `0xE383D432F039f4377CC9AA003FfaE4c814936864` | `0xB0EC3C1368AF7d9C2CAE6B7f8E022Cc14d59D2b1` | `0x18BB8310E3a3DF4EFcCb6B3E9AeCB8bE6d4af07f` | `0xfb27e42E964F3364630F76D62EB295ae792BD4FA` | `0xD17550876106645988051ffDd31dFc3cDaA29F9c` |
| Superposition | 55244 | not read (`nativeToken()` reverts) | classic (registry Rollup) | `0x325Dd0279Ba31bC346BA80F3D00628deFa2EacD4` | `0xEca0fEB4aA6112a3923823559e7197294Bc49CC7` | `0x2EAf07A964c6601c4fAefd6D8969DF0B84f65e55` | `0xe0064A9fb8e45BfD8e5aB1cE7523888814A096E0` | `0xa4b3B4D5f7976a8D283864ea83f1Bb3D815b1798` |
| Mind Network | 228 | ETH | BoLD | `0x435CEf963dE6CC2241da6f09CE6Bb3600cF259a9` | `0x34F81F9C4F3227DbaCcFF8E51DBaa1571e114759` | `0x703F97120c8E5F5fC7c878C309E9e84E118B0478` | `0xD00d2ef101d86C570dA8f38801f236b79a7a2A93` | `0x31A1A120939007547aBC5e3BFaBDB6AcA6C00378` |
| Spotlight Mainnet | 10058111 | ETH | classic | `0x49B3Bb2c0E54F548F17473d7669b14E009Da407c` | `0x37d3139024D017C2152849B154F2631E2F2C8560` | `0x21092752C8BB70b8043379a00dCB9aCdA2302181` | `0x627C3Eac80782493B3a633F09C82F510ad710A2D` | `0xb07b44B3D5C7df02905B9c156Ba44b5762f7b268` |
| CheeseChain | 383353 | CHEESE `0x05AEa20947A9A376eF50218633BB0a5A05d40A0C` | classic | `0xb9E6B5AcB523D431f6D136C56d371271456757E7` | `0xA337997ab18164Dfe1e8A94E8D912e8d4e2ce173` | `0x58e3F0ed71ac29501326aeE9564674E43812cc24` | `0x714d792CB8BFB9F70Cde071904d8743280267ab2` | `0x9bAA9C2c313510D4f3CB2673b2f2603ED45d6eDd` |
| ChainBounty | 51828 | BOUNTY `0x6a9896837021EA3eD83F623F655C119c54abE02c` | BoLD | `0xc905b1F4e9fFcC21a58B430FBa06d07203F641E1` | `0xd46AB997110a91C4CB6f4576ffE6769a3033622A` | `0xF649EF414d5674851614615b3e3861E90a812379` | `0x6CBf221c8cc7E2B9De4bce3a5c75378591Bdf8Ea` | `0x48a5c0942046753B8026b1dc074Dd22297A31340` |
| Conwai | 668668 | CNW `0xb8D4554538991977E49E4C5490B92CFE58EF5281` | classic | `0x65DC757cd6A72332e37FD49382396b9aCee35462` | `0x9be649C1C1D073536D55db83abA093E8558A962E` | `0x1BEdFe383749b07A73370496E035c31Fd336509C` | `0xF759d5DD167072D470D08BF65Aef1aD3F8Efc947` | `0x09E2EF7161c89aAC723f817695629BEBd9914f41` |
| Miracle Chain | 92278 | MPT `0xa4f63404b58C3efD9Db6D53352BD386fFa174e5A` | BoLD | `0x0DA5198b8ae8aE9354061649D08BE1c53ec8a377` | `0xaF25849aEb040bEab7a0c783fc6861d26aE49796` | `0xc7b143E5E4Bf1893BA33007ecb3Db9c1092dab38` | `0x21f9c31eD91612B48A8ae450Bdd0f19F8f5Bea40` | `0xA5b6E1DbA5c9037cCd2013D7dd7BD173AFc90d4c` |
| BirdLayer | 53456 | ETH | BoLD | `0xd6e33A7898aE63Cb3D56b4B51575141E953BD9D5` | `0x113E7DC5e4A42b1bEe9DB0594f48EFdEa7b88eE0` | `0x5b777fa9fBF1587509fe5b2Ab681af7Af890A5A3` | `0xf5299083F7C234425f01CccDD9141e500011fffb` | `0x1B7b002b9430c6D59058beFa1f718A91fBe51ff0` |
| RCADE | 101069 | RCADE `0x077574441C4F8763a37a2cFeE2ECb444aA60A15e` | classic | `0x5aE6380a5E9306A616CCDffF5a53813dbC4b88F3` | `0x13355730A242744D71f1e489896837f70797fB26` | `0x09a0f92A165dE693E2f5A9dE6c78605Fe873b36E` | `0x9876fC5268F4053e6339ead270311582A4983cE5` | `0xbBe348691B0765B04D5a72EBfD502Acd3bf5d09A` |
| Molten | 360 | MOLTEN `0x66E535e8D2ebf13F49F3D49e5c50395a97C137b1` | classic | `0x0f28D76Ec5c62b502625351726b4A3E3F54FF5F0` | `0xE1d32C985825562edAa906fAC39295370Db72195` | `0x235000876bd58336C802B3546Fc0250f285fCc79` | `0x0fFe9ACC296ddd4De5F616Aa482C99fA4b41A3E2` | `0xb255de22d39a26D4CbcAFd6Cf660ccaCa047e95B` |
| MeerChain | 98215 | TRIX `0x49bEf7dE007B944505f5A2Fac1F00737C8E4fA96` | BoLD | `0xCE9b9DcC2D281356a7591F3D8307991546172771` | `0x55A1B18E0300aD707617B828E0554765dBFc8535` | `0x306c4D4032862813db6554519e03DA31C1387cFf` | `0xA672239e003124455c00FdAB7D15dD682BCe97AE` | `0x8D6513Bc0cafaa0CaEdB80dB392997E92c7FA125` |

Three rows need care:

- **Edge (3343)** changed its Rollup around the window. In the window the classic Rollup `0x14FdC47483e79d5A76599a74A2D622DA1cf97BBF` (`bridge()` = the Edge Bridge, `chainId()` = 3343) emitted 117 `NodeCreated` and 116 `NodeConfirmed`, and the Edge Outbox emitted 116 `SendRootUpdated` in the same transactions. On 2026-10-01 `Bridge.rollup()` and `Outbox.rollup()` return the BoLD Rollup of the table. Watch both Rollups until the old one is silent. Edge's UpgradeExecutor `0xabf2650D259213d6b3E1bC46Fc1eDb7405d48Fdf` emitted 1 `TargetCallExecuted` in the window.
- **Superposition (55244)**: its Bridge `0xEca0fEB4aA6112a3923823559e7197294Bc49CC7` now runs a 536-byte implementation (`0x56D438188FF580C25EcfAF39644dC6b91f66B292`), and `rollup()` and `nativeToken()` revert there. The row shows the registry Rollup, which still answers `bridge()` = that Bridge and `chainId()` = 55244. Whether the chain still settles here is unverified.
- **Sanko (1996)** paid its 2 withdrawals of the window through a second allowed outbox, `0xa9Aa07F082D9c15D0B6D7e9e5B68b1f898399C29` (16,379 B, not a proxy), with no `OutBoxTransactionExecuted` (sample `0xc45afae668dc98c48901354fb44e8b0981ae951195824d65355061ff1df75a0f`: DMT `Transfer` from the ERC20Bridge). This is the pattern of Degen Chain on Base (§9, item 5).

### 5.2 Token bridge contracts on Arbitrum One (`inboxToL1Deployment(inbox)` on the TokenBridgeCreator)

| Chain | L1GatewayRouter | L1ERC20Gateway (escrow) | L1CustomGateway (escrow) | L1WethGateway |
|---|---|---|---|---|
| unnamed 2886 (ETH gas) | `0xed4440aF18C35A29b3928e9D283469c662db73BF` | `0x483754470664ea3d99Fa79AE803e56cA0afe4827` | `0xfFA83F83aED855Cd1e1760e7C77C90B9e58E26ac` | `0x5eee4D349AD45F755d2E4aef93e309b463B65E41` |
| Edge (3343) | `0x3616995dF5D07B28f2B186F1386cace9EB9Bbd20` | `0x107695630130919cb040B095b9b20511D6e211bB` | `0x5c87311c2F3F6eE4e9fa7ecBF142451fc22f1754` | `0x9580Af28042fCC37DF0569f3Ccf2d8b8A897EFFC` |
| Xai (660279) | `0x22CCA5Dc96a4Ac1EC32c9c7C5ad4D66254a24C35` | `0xb591cE747CF19cF30e11d656EB94134F523A9e77` | `0xb15A0826d65bE4c2fDd961b72636168ee70Af030` | none |
| unnamed 8818 (fee token CBIT) | `0x223B10aD4BAA3E2a8c512606986e242C226DF6BF` | `0x7DDd55266Af448eDf9F2Ce25106f2160D77267d0` | `0x7E25F64bcDA391CA4BE2aB372436b8578e1fb79D` | none |
| unnamed 4485770 (fee token COR) | `0x2f169f7195BBD9C86a1aaa8DD21E2D7e2D28B23A` | `0x92eb265C201df4717E45678d618a8eECAFea1BF4` | `0xA2f2fA66917Ab90E3361A14096645fDe207d9cBa` | none |
| unnamed 61022894 (fee token DKA) | `0xcF6298ca74B278e5CB02B75f100D766BDfAC11A2` | `0x306485BFA7c6c0b533A9Bd3C3B363bE848c7A289` | `0x03141af6d5ca65E8D3Ee5CbC17f9ff26D81D47E3` | none |
| Ethereal Mainnet (5064014) | `0x1FEfA62f98B1a734575f3eF44B826BcC32ce5bb1` | `0x1B83B2f5977A2CB6f34526259eA083b43423400a` | `0x98f1390e3e88B8C19aD67D927E2994A98B95Ef52` | none |
| Animechain Mainnet (69000) | `0x40D337cE575539E23deB48F558fe725e4F7710E5` | `0x4b1E0B1AdB50e1f28A9211A7353b034447149e3c` | `0xeb6be9b70a3CC53ffcD686dB750cBe911ac99133` | none |
| Edu Chain (41923) | `0xDa4ac9E9cB8Af8afBB2Df1ffe7b82efEA17ba0f6` | `0x419e439e5c0B839d6e31d7C438939EEE1A4f4184` | `0xDd7A9dEcBB0b16B37fE6777e245b18fC0aC63759` | none |
| Earnm Mainnet (32766) | `0xFCF106865f380D73b52406933B3e74498771F3Ef` | `0x0b6b5aFEe8602A4d88dC26Fc2E85b2d1236156F6` | `0x24f926249F73203112400756801A41Cb519a87aa` | none |
| unnamed 529375 (fee token LYK) | `0xE9E6e749f76858E6A6EdcD1EE737D4A58b183CAb` | `0x0f6Ac4f57Aa2053c17B3893b12c317248670D7F6` | `0x7e974088bAF57DC80f808DBF8E8112fb52D2D532` | none |
| CarrChain Mainnet (7667) | `0xd9F78e154E6648752F2d2788b197794E990aEb4b` | `0xBAA43624E8E047a20da97810643be56F6D6d3Ea1` | `0x2dd483937904cfc0AbcfD778a13deD4e1cf3EE64` | none |
| unnamed 261131 (ETH gas) | `0xF95dDa1Aa4274CBd98141D6a04913E00E618a88d` | `0x8B0fE566dDC3E0788a4E907706ac170B51D2B482` | `0x22dDb4F7022B96c189eD7c32737a8bb0417A7a22` | `0x24169c477b825c4A28117951939F4A59A753d4DF` |
| unnamed 27182 (ETH gas) | `0x0Ae9dB012a622249F088106125D0D96139FdAD86` | `0x87280BF48d090B2E1d4E87B088a098b3cCFfa767` | `0xf93a755EeDd989e38d9836d652b22AB55615391c` | `0x1e1A81Be696b7A2F5444A7dA70C103c17722842d` |
| Mind Network (228) | `0x7E2349E5d0A3E8418864576d0D7a1747456B0849` | `0x281587c05DeA1a1ceCE83F6FFea23c5aFd287fb3` | `0xA6a623F64931Bcf1368B120e9Dc29254676D0D8E` | `0xe525299577D2431312beF921d4c29E1Fd1efC4E7` |
| Spotlight Mainnet (10058111) | `0xf50201e8963A07cEF57f58C56C2349b10B487091` | `0xaB24881b11c1c7eb6b9C22288eDB12B67defCEb9` | `0x443E16416b49Ad675F7E4F00CbA3916F5564DEf3` | `0x44a9a5C2416702BeDC562f8023f19Bc1D732bE94` |
| ChainBounty (51828) | `0xa55090a934B9863Ae6E7a011a320693bEFd703BA` | `0x81d8Bb220060Ba83653925c2a5D5c7060fD7729B` | `0x5113CD511cB1bBf6d5A2BbA7c6dBe1D37D5Bd55a` | none |
| Miracle Chain (92278) | `0xb7dd0d29CB25D825aF320A09eA8Fc28A13E15F2B` | `0x841C2f295fAd92eD08c52CD5304Ec5BC88962124` | `0x7f8FBbDEAB9Dca3114809EE55ff465d770E0f839` | none |
| BirdLayer (53456) | `0xf222cf6633f381B10D3b01793FC9bD3C07975800` | `0x6111D7AAa83fbE979301C458fF8f07F1d2E30002` | `0x07a873c2372653615e2EA3D4405Aa19D2972Eb7C` | `0x8F6D27486eb773C7eEd27760D6aBd7355e0B64e9` |
| MeerChain (98215) | `0x5d94E722d350579662De3Bd57298a42D148432b3` | `0x70e43daC8f9140752C0937251c9345DDE97183C7` | `0x2A4054528972748aaaF6224Ff46F2A6349CE1426` | none |

No token bridge is registered for: ApeChain (33139), Mawari Mainnet (1576), Miracle Chain Mainnet (1247), unnamed 20231119 (ETH gas), Sanko (1996), RARI Mainnet (1380012617), Muster (4078), Superposition (55244), CheeseChain (383353), Conwai (668668), RCADE (101069), Molten (360). The L1 WETH of the ETH-gas L3s with a WETH gateway is the Arbitrum One WETH `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1`. Chain 2886's gateway and router were the only L3 token-bridge emitters in the window (3 `DepositInitiated`, 3 `TxToL2`, 2 `WithdrawalFinalized`, 3 `TransferRouted`); both answer `inbox()` = chain 2886's Delayed Inbox.

### 5.3 Measured events (pinned window, Arbitrum One blocks 509,539,969–509,698,804)

| Chain | `MessageDelivered` (Bridge) | Delayed-inbox messages | Batches (`SequencerBatchDelivered`) | `SendRootUpdated` | `OutBoxTransactionExecuted` | `BridgeCallTriggered` | Nodes or assertions created / confirmed |
|---|---|---|---|---|---|---|---|
| unnamed 2886 (ETH gas) | 875 | 3 | 872 | 47 | 2 | 2 | 47 / 47 |
| Edge (3343) | 138 | 0 | 138 | 116 | 0 | 0 | 117 / 116 |
| ApeChain (33139) | 0 | 0 | 120 | 12 | 0 | 0 | 12 / 12 |
| Xai (660279) | 0 | 0 | 47 | 12 | 0 | 0 | 12 / 12 |
| unnamed 8818 (fee token CBIT) | 0 | 0 | 27 | 18 | 0 | 0 | 21 / 18 |
| unnamed 4485770 (fee token COR) | 0 | 0 | 22 | 22 | 0 | 0 | 21 / 22 |
| Mawari Mainnet (1576) | 0 | 0 | 22 | 12 | 0 | 0 | 12 / 12 |
| Miracle Chain Mainnet (1247) | 0 | 0 | 12 | 12 | 0 | 0 | 11 / 12 |
| unnamed 61022894 (fee token DKA) | 0 | 0 | 11 | 12 | 0 | 0 | 12 / 12 |
| Ethereal Mainnet (5064014) | 1 | 1 | 12 | 5 | 0 | 0 | 4 / 5 |
| Animechain Mainnet (69000) | 0 | 0 | 11 | 3 | 0 | 0 | 4 / 3 |
| Edu Chain (41923) | 0 | 0 | 12 | 1 | 0 | 0 | 1 / 1 |
| Earnm Mainnet (32766) | 0 | 0 | 12 | 0 | 0 | 0 | 12 / 0 |
| unnamed 529375 (fee token LYK) | 0 | 0 | 10 | 1 | 0 | 0 | 3 / 1 |
| CarrChain Mainnet (7667) | 0 | 0 | 1 | 8 | 0 | 0 | 1 / 8 |
| unnamed 20231119 (ETH gas) | 3 | 0 | 3 | 2 | 0 | 0 | 3 / 2 |
| unnamed 261131 (ETH gas) | 2 | 0 | 2 | 3 | 0 | 0 | 2 / 3 |
| unnamed 27182 (ETH gas) | 1 | 0 | 1 | 1 | 0 | 0 | 1 / 1 |
| Sanko (1996) | 0 | 0 | 0 | 0 | 0 | 2 | 0 / 0 |

No Nitro event in the window: RARI Mainnet (1380012617), Muster (4078), Superposition (55244), Mind Network (228), Spotlight Mainnet (10058111), CheeseChain (383353), ChainBounty (51828), Conwai (668668), Miracle Chain (92278), BirdLayer (53456), RCADE (101069), Molten (360), MeerChain (98215). Chain 2886 is the busiest L3 (875 `MessageDelivered`, of which 872 are batch reports and 3 delayed-inbox messages). All counts are `eth_getLogs` per emitter; a 0 is a 12-hour measurement.

### 5.4 Factories on Arbitrum One (Arbitrum docs and Orbit SDK address maps)

| Factory | Address |
|---|---|
| TokenBridgeCreator | `0x2f5624dc8800dfA0A82AC03509Ef8bb8E7Ac000e` |
| RollupCreator v3.2 | `0xF5962AD061A1aD6F38F340F5b267b3593cC1Cd7B` |
| RollupCreator v3.1 | `0xB90e53fd945Cd28Ec4728cBfB566981dD571eB8b` |
| RollupCreator v2.1 | `0x79607f00e61E6d7C0E6330bd7E9c4AC320D50FC9` |
| RollupCreator v1.1 | `0x9CAd81628aB7D8e239F1A5B497313341578c5F71` |

## 6. Addresses — Robinhood Chain (chain ID 4663)

Robinhood Chain is an Orbit L2 that settles to Ethereum and pays gas in ETH (an ETH chain: `Bridge` + `Inbox`, BoLD Rollup). Its Ethereum-side contracts are §3.1–§3.3. Public RPC `https://rpc.mainnet.chain.robinhood.com`, explorer `https://robinhoodchain.blockscout.com`. All addresses in §6.2–§6.5 have code on chain 4663 (`eth_getCode`, 2026-09-29), except NodeInterface. Key L2 contracts: ArbSys `0x0000000000000000000000000000000000000064`, ArbRetryableTx `0x000000000000000000000000000000000000006E`, L2GatewayRouter `0x1E324B9316138CA9a73F960213621AD1aaf01B89`, L2ERC20Gateway `0xfd9b17206278C16DdaacF6AC8f05dBf97EdCb31e`, WETH `0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73`.

### 6.1 Robinhood Chain on Ethereum (summary; full rows in §3)

| Role | Address (Ethereum) | EIP-1967 implementation |
|---|---|---|
| Rollup (BoLD, live) | `0x23A19d23e89166adedbDcB432518AB01e4272D94` | admin logic `0xAb7A44CE7e66963d2116dCe74AB63eeF88266C82`; user logic `0xedC23dFC7D1e57EC07eA5ff7419634DbAe08Ed2C` |
| Bridge (ETH escrow) | `0xDf8755334ce7A73cCF6b581C02eA649AE3E864b3` | `0xC678f7B95A7D1F77c6024c0086301D21402854b1` |
| Delayed Inbox | `0x1A07cc4BD17E0118BdB54D70990D2158AbAD7a2D` | `0x8D3b93dfFFf4842E7B61FB553b383db2C6BC91c6` |
| SequencerInbox | `0xBd0D173EEb87D57A09521c24388a12789F33ba96` | `0xb015D78fb9B890e96FD3E23819b2C8D9fffA3cC5` |
| Outbox | `0xf0ce991ea4A0d2400A4AB49b20ae333f6Dce3DE9` | `0x396765AEbE540575ef927F769b0d7b89594f931c` |
| RollupEventInbox | `0xc34f4907822d1cDC6aE3038Be22e6f12DEa35bd4` | `0x796FeE4adceD1cb47a3e3d1B6925472F8fC8f1f9` |
| L1GatewayRouter | `0x6a2E3a1e16FC29f27Ce61429746D558d656975bB` | `0x6525137BfF366fbc0A89E3e5A4d244B5A0090a6D` |
| L1ERC20Gateway (escrow) | `0x85001CC4867C5e1C22dA4B79BB8852B9e2a06da0` | `0xf43bce5D32742FFC862eA182b0b5544CbDBB0F02` |
| L1CustomGateway (escrow) | `0x9368EAEbFe6E063C69dcF8126711A6997E0eCeE1` | `0xedB05ED1a37750833fBE85b808c872D841d00859` |
| L1WethGateway | `0xF7e12b9614b509C747ab4423bC4ACF923759Cf1B` | `0xa86996bED19547f7dEf22a087dD61b5F9Fb6C684` |
| UpgradeExecutor (Rollup admin) | `0x552603b4bc1f5E896AF2854548D6380f45f1B4bf` | `0x9149DF379237a935cf0658fE54D2325109493CBb` |
| Core ProxyAdmin (all proxies above except the Rollup) | `0x1232813BDd40aa9d53066A880dE78a4Be70B90FD` | not a proxy |

### 6.2 L2-side contracts on Robinhood Chain

| Role | Address (chain 4663) | Notes |
|---|---|---|
| **ArbSys** (precompile) | `0x0000000000000000000000000000000000000064` | withdrawal origin: `sendTxToL1` / `withdrawEth` emit `L2ToL1Tx` + `SendMerkleUpdate`. Code is the 1-byte marker `0xfe` |
| **ArbRetryableTx** (precompile) | `0x000000000000000000000000000000000000006E` | retryable lifecycle: `TicketCreated`, `RedeemScheduled`, `Redeemed`, `LifetimeExtended`, `Canceled`. Code `0xfe` |
| NodeInterface (virtual) | `0x00000000000000000000000000000000000000C8` | **no code on 4663** (`eth_getCode` = `0x`); the node answers calls to it. Arbitrum One returns `0xfe` here |
| **L2GatewayRouter** | `0x1E324B9316138CA9a73F960213621AD1aaf01B89` | impl `0x030c64a359Be400AF05F9230A6F65F30537cdd12`; `counterpartGateway()` = the L1GatewayRouter; `defaultGateway()` = the L2ERC20Gateway |
| **L2ERC20Gateway** | `0xfd9b17206278C16DdaacF6AC8f05dBf97EdCb31e` | impl `0xdf988cF6D83ebd578f6801820d01FEe7280886d6`; counterpart `0x85001CC4867C5e1C22dA4B79BB8852B9e2a06da0` |
| **L2CustomGateway** | `0x912285144fC0f6e89d3Ed16F5Ab72f87A1878959` | impl `0x833608D6d6769E8bbA82731F628Cb2c68ad87c64`; counterpart `0x9368EAEbFe6E063C69dcF8126711A6997E0eCeE1` |
| **L2WethGateway** | `0x1D187C3E2dA52D72BC9C41e3AbA0fdFa6a7bF055` | impl `0x0354a93fe0DB94bB72Ec053f43301746Fc806EDf`; `l1Weth()` = WETH9, `l2Weth()` = the aeWETH below |
| **WETH** (aeWETH, canonical L2 WETH) | `0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73` | impl `0xC6B81b429797E0f555440b70cD99e032D7AE947e`; minted by the L2WethGateway on a WETH deposit |
| L2 ProxyAdmin | `0xa3Acd31AFb851B4eB9DAD00F5204c01D924267dF` | admin of every L2 proxy here; `owner()` = the L2 UpgradeExecutor |
| L2 UpgradeExecutor | `0x2A153c6A1B66DBc930a8d7017230ab0253005C09` | impl `0x3c3E52bC8C181D06A76e2518bBc655C5BB3Ce7Cd` |
| BeaconProxyFactory | `0xc302CcbC357A39a7231A681C61943b2DC032Dd51` | deploys the standard bridged-token proxies |
| L2 Multicall | `0x2cAC2D899eCC914d704FeaAE33ac1bF36277DaD1` | helper |

The L2 addresses equal the Robinhood Chain docs and the TokenBridgeCreator record (`inboxToL2Deployment` of the Robinhood Chain Inbox, read on Ethereum). The Arbitrum One L2 addresses of `core.md` §5 have no code on 4663.

### 6.3 Measured L2 events (pinned window, Robinhood Chain blocks 74,350,994–74,780,331)

| Event | Emitter | Count | Sample transaction |
|---|---|---|---|
| `TicketCreated` (deposit arrives) | ArbRetryableTx | 95 | `0x0a3c3bb91314b9b5a4eefa7b0750a77f18f07b925a9d9f63ab74bbed8a4e25c4` |
| `RedeemScheduled` (auto-redeem) | ArbRetryableTx | 95 | same |
| `DepositFinalized` (token deposit paid) | L2ERC20Gateway | 51 | `0xa29c703db345fc01eb23829c8523b9f6c8cd13771e9fb12cc473858866abad50` |
| `DepositFinalized` (WETH deposit paid) | L2WethGateway | 4 | `0xfc781573000965100b55457dd1cda3be8db0348a3b633325e0cd18a7f0993960` |
| `DepositFinalized` | L2CustomGateway | 0 | — |
| `L2ToL1Tx` (withdrawal starts) | ArbSys | 15 | `0x983a98b3a0a8515d074333bd767cc358b11d6945e022791d26bb24dcad524fea` |
| `SendMerkleUpdate` | ArbSys | 19 | same |
| `WithdrawalInitiated` (token withdrawal) | L2ERC20Gateway | 10 | `0xe4df59795cda847facea2e17fe8a9bc14ca83b5fcb687c173453b110f9719d19` |
| `TxToL1` | L2ERC20Gateway | 10 | same |
| `TransferRouted` | L2GatewayRouter | 10 | same |

The token deposit `0x0d6994a1c67f2e0eba7d59031b7afb32a4e1c7bdb550bf8386528d3829de827e` on Ethereum (message 327,346) arrived as `0xa29c703db345fc01eb23829c8523b9f6c8cd13771e9fb12cc473858866abad50` on 4663, with the same token and amount. In the same window Ethereum saw 51 `DepositInitiated` at the Robinhood L1ERC20Gateway and 4 at its L1WethGateway. The counts come from one `eth_getLogs` pass over all the emitters above; a separate per-address count of `L2ToL1Tx` at ArbSys and of `DepositFinalized` at the L2ERC20Gateway gave the same 15 and 51, with the same first transactions.

### 6.4 Orbit L3 on Robinhood Chain: xMoney (chain 466302)

The pinned window shows one Orbit chain that settles to Robinhood Chain; other, idle ones are not excluded. It is resolved on chain from its Bridge (`rollup()` → `chainId()` = 466302). The name is unverified: it comes from the fee token (`name()` = `X Money`, `symbol()` = `xMoney`) and from the project's own description as an Orbit chain that settles on Robinhood Chain.

| Chain | ID | Fee token | Rollup (live, = `Bridge.rollup()`) | Bridge (escrow) | Delayed Inbox | SequencerInbox | Outbox |
|---|---|---|---|---|---|---|---|
| xMoney | 466302 | xMoney `0xa924C725B64cC346f275269EFA4Bd0538cfBa97E` | `0x5868266C0c0663f4bc39329B525884f137BAD93E` | `0x2290f4505484f055B710e7Df37e2482c90B8B6fb` | `0xa7087693676F2Ca8e5e9563A6859952258688146` | `0xCA038a032154d0091b019A9104b369F94FD5c75F` | `0xA6f07dd42CFE78EC8D88484b238b3B05149Eb2b3` |

| Chain | Rollup generation | `confirmPeriodBlocks` | UpgradeExecutor (= Rollup admin slot) | Core ProxyAdmin (= Bridge admin slot) | RollupEventInbox |
|---|---|---|---|---|---|
| xMoney | BoLD | 50,400 | `0x43E881A831Ec5680aa6f63d2b48913050038b9F9` | `0xbd80F0f92F2a4f49e41C2923d37993e60ee977Bd` | `0xa5E0Ca089b66004F7FFD1f50Ced692f27A6F55B5` |

No token bridge is registered for it in the Robinhood Chain TokenBridgeCreator. In the window its Bridge emitted 1 `MessageDelivered` (a batch report) and 1 `BridgeCallTriggered`, and its Outbox 1 `OutBoxTransactionExecuted`. The fee token burns part of every transfer: in payout `0x2deb7314f77893a47a02e32f72f0cd2483408b3b51afbdd0f909378f2d14ceee` the ERC20Bridge sent part of the value to `0x000000000000000000000000000000000000dEaD`, so the recipient's `Transfer` is smaller than `BridgeCallTriggered.value`.

### 6.5 Factories on Robinhood Chain (Orbit SDK address maps)

| Factory | Address (chain 4663) |
|---|---|
| TokenBridgeCreator | `0x8B1EFf64E1eAd493A82C6798f5708183AF91A3AD` |
| RollupCreator v3.2 | `0xF5962AD061A1aD6F38F340F5b267b3593cC1Cd7B` |

---

## 7. Cross-chain summary

| Chain | ID | Orbit settlement contracts on this chain | Orbit L2-side contracts | Measured in the window |
|---|---|---|---|---|
| Ethereum | 1 | ✅ 13 listed L2s (§3.1), Robinhood Chain `0xDf8755334ce7A73cCF6b581C02eA649AE3E864b3` first; 11 more in §3.4; factories §3.5 | — | 22 SequencerInboxes posted batches |
| Base | 8453 | ✅ Tranched `0x08abBE019C351D5124256D3602da6a5a40fa7C72`, chain 846737 `0x9d4AB2E611a7b9Fdc0168C4C1EEd563eba35A43D` (§4.1); 7 more in §4.3; factories §4.4 | — | 7 SequencerInboxes posted batches |
| Arbitrum One | 42161 | ✅ 34 Orbit L3 Bridges (§5.1), the busiest chain 2886 `0x53a7559d1e57E371F3D1e55Fea97e9B6748418a3`; factories §5.4 | its own L2 side: `core.md` §5 | 18 SequencerInboxes posted batches; 6 L3 Bridges emitted `MessageDelivered` |
| Optimism | 10 | ❌ none found | ❌ | 0 logs of any Nitro topic0 |
| Polygon PoS | 137 | ❌ none found | ❌ | 0 |
| BNB Smart Chain | 56 | ❌ none found | ❌ | 0 |
| Avalanche C-Chain | 43114 | ❌ none found | ❌ | 0 |
| **Robinhood Chain** | 4663 | ✅ xMoney L3 `0x2290f4505484f055B710e7Df37e2482c90B8B6fb` (§6.4); factories §6.5 | ✅ §6.2 (L2GatewayRouter `0x1E324B9316138CA9a73F960213621AD1aaf01B89`) | 95 `TicketCreated`, 15 `L2ToL1Tx` |

Absence on Optimism, Polygon PoS, BNB and Avalanche: `eth_getCode` returns `0x` at every Orbit address of this file on those chains; the Orbit SDK factory maps list no RollupCreator or TokenBridgeCreator for chain ids 10, 137, 56 or 43114; and the pinned window has 0 logs of `MessageDelivered`, `InboxMessageDelivered`, `SequencerBatchDelivered`, `OutBoxTransactionExecuted`, `BridgeCallTriggered`, `DepositInitiated` or `WithdrawalFinalized` from any emitter there (the same queries return data on Ethereum, Base, Arbitrum One and Robinhood Chain). A custom Nitro deployment outside the factories is not excluded.

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|---|---|---|---|
| Bridge, Inbox, SequencerInbox, Outbox, RollupEventInbox (every chain) | **EIP-1967 transparent proxy** | impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` set; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` = the chain's core ProxyAdmin (§3.3, §4.2) | the ProxyAdmin `owner()` = the chain's UpgradeExecutor (Robinhood Chain: read live) |
| Rollup (classic and BoLD) | **double-logic proxy** | EIP-1967 impl slot = admin logic; slot `0x2b1dbce74324248c222f0ec2d5ed7bd323cfc425b336f0253c5ccfda7265546d` = user logic; admin slot = the UpgradeExecutor itself | UpgradeExecutor |
| Parent-chain gateways and router | **EIP-1967 transparent proxy** | admin slot = the core ProxyAdmin (Robinhood Chain: `0x1232813BDd40aa9d53066A880dE78a4Be70B90FD`) | UpgradeExecutor |
| L2 gateways, router, aeWETH, L2 UpgradeExecutor (Robinhood Chain) | **EIP-1967 transparent proxy** | admin slot = L2 ProxyAdmin `0xa3Acd31AFb851B4eB9DAD00F5204c01D924267dF` | L2 UpgradeExecutor `0x2A153c6A1B66DBc930a8d7017230ab0253005C09` |
| UpgradeExecutor (parent chain) | **EIP-1967 transparent proxy** | Robinhood Chain: impl `0x9149DF379237a935cf0658fE54D2325109493CBb`, admin = the core ProxyAdmin | its own `EXECUTOR_ROLE` holders (not read) |
| ArbSys, ArbRetryableTx | **ArbOS precompile** | 1-byte code `0xfe`, no impl slot | ArbOS upgrade |
| Registry-stale Rollups (Gravity Alpha `0xf993AF239770932A0EDaB88B6A5ba3708Bd58239`, Plume `0x35c60Cc77b0A8bf6F938B11bd3E9D319a876c2aC`, HPP `0xf0d2960a37B33567FF7507C2d59da021277663A1`) | classic RollupProxy, **disconnected** | `bridge()` still names the chain's Bridge and `latestNodeCreated()` answers (1232, 691, 222), but `Bridge.rollup()` names the BoLD Rollup of §3.1 | — |

Implementations are shared templates. For example the Orbit ERC20 gateway implementation `0xe80b4E0ed5e92d865F4708eeE0E1564287a7D848` sits behind the Gravity Alpha, Pepe Unchained V2 and SX Rollup gateways. A shared implementation or a shared proxy bytecode does not identify the chain; the proxy address does. Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` on every proxy, and `TargetCallExecuted` / `UpgradeExecuted` on each UpgradeExecutor.

---

## 9. Detection invariants & gotchas

1. **Same topic0 on every chain: key on the emitter.** In the window, `SequencerBatchDelivered` came from 22 SequencerInboxes on Ethereum, 7 on Base and 18 on Arbitrum One (the L3s of §5.1). A filter on topic0 alone mixes Robinhood Chain with every other Orbit chain.
2. **Resolve with `Bridge.rollup()`, not with a list.** An unknown Bridge resolves in two calls: `rollup()` then `chainId()`. A SequencerInbox or Outbox resolves through `bridge()` first.
3. **Registries go stale.** The Arbitrum bridge registry names the classic Rollups of Gravity Alpha, Plume and HPP (§8), while `Bridge.rollup()` returns their BoLD Rollups (`0x2807B1d5d94ca823ca7d8642A5F5DDac120ce48f`, `0x4eD3F488a5a4417839BbC39712EB76D8Aaee6eE8`, `0x8361fC54C99AdDbeD390Af68e7e6115323AB8DB1`). The same move happened on Arbitrum One (`core.md` §9, item 1).
4. **Fee-token chains move a token, not ETH.** A `depositERC20` deposit shows two fee-token `Transfer` rows (user → ERC20Inbox → ERC20Bridge) and no ETH value. A payout is a fee-token `Transfer` from the ERC20Bridge, and `BridgeCallTriggered.value` counts fee-token units (Gravity Alpha payout `0xf00b672feb4d755d14c97da2de8eb1931192e44ba6a75343e344e9c6c0efacde`: G from `0x7983403dDA368AA7d67145a9b81c5c517F364c42`). Never price a fee-token chain's `value` as ETH.
5. **Every allowed outbox can pay; only the canonical one emits `OutBoxTransactionExecuted`.** Read `allowedOutboxList(i)` on each Bridge. Degen Chain's Bridge on Base allows a second outbox `0xDb8E759859058952c34953c8469f464109826e52`; in the window it paid 2 withdrawals (`BridgeCallTriggered`) after a LayerZero `EndpointV2` receive in the same transaction, and the canonical Outbox emitted nothing. Sanko on Arbitrum One did the same through `0xa9Aa07F082D9c15D0B6D7e9e5B68b1f898399C29` (§5.1). Key payouts on `BridgeCallTriggered` at the Bridge, and treat an `OutboxToggle` (a new payout authority) as a high-severity admin event.
6. **Batch reports are not deposits.** Keep `MessageDelivered` kind 9 (retryable) and kind 12 (ETH or fee-token deposit); kind 13 is the batch-cost report. On an ETH chain every batch adds one report (Robinhood Chain: 1,363 of 1,516 `MessageDelivered` in the window). On a fee-token chain the report depends on the SequencerInbox version: v2.1 skips it, v3 can send it (Shib Mainnet and the xMoney L3 did; Gravity Alpha, Plume, SX Rollup and chain 846737 did not). `InboxMessageDelivered` at the SequencerInbox is the same report: filter on the Delayed Inbox address.
7. **`MessageDelivered.sender` is always aliased.** The Inbox passes `applyL1ToL2Alias(msg.sender)` for an EOA and for a contract alike (sample `0x18100c3e54f24ccb7437eb58abfa626a95a9c08e6712177c4c9448099c45b40b`: EOA `0xf6017e7195dfd4EAE02c4A0ed54146B282294EF3` shows as `0x07127e7195DFd4eaE02C4A0ED54146b282296004`). Only the L2 recipient inside the `depositEth` / `depositERC20` data stays unaliased for an EOA. Subtract `0x1111000000000000000000000000000000001111` (mod 2^160) before you attribute the sender.
8. **Two rollup generations, two event sets.** Classic Rollups (AlienX, AppChain, HYCHAIN, SX Rollup, Tranched, Symbiosis, Citronus, Studio Chain, Intuition, XMTP, Degen Chain and others) emit `NodeCreated` / `NodeConfirmed`; BoLD Rollups emit `AssertionCreated` / `AssertionConfirmed`. Probe `genesisAssertionHash()` (BoLD) or `latestNodeCreated()` (classic).
9. **The challenge period differs per chain.** `confirmPeriodBlocks` ranges from 7,200 (T-Rex) to 50,400 on Ethereum, and it counts Base blocks for a Base L3 (Tranched 274,908, chain 846737 302,400). On a Nitro parent chain `block.number` is the Ethereum block number, so the xMoney L3's 50,400 counts Ethereum blocks. A payout cannot come before `NodeConfirmed` / `AssertionConfirmed` plus the user's own `executeTransaction`.
10. **`TxToL2` is not a gateway signature.** Any contract that inherits the L1 messenger emits it: in the window `0x48D5354Ee0DBE52099534D7c4b9CC7Fb4f618Bb3` sent a kind-9 message to Arbitrum One with `TxToL2` and no `DepositInitiated`. Value moves only where `DepositInitiated` / `WithdrawalFinalized` fire.
11. **A fee token can tax its own transfers.** The xMoney L3's payout burned part of the value to `0x000000000000000000000000000000000000dEaD` (§6.4). Match amounts on the recipient's `Transfer`, not on `BridgeCallTriggered.value`.
12. **Admin actions come in pairs.** An Orbit owner acts through its UpgradeExecutor: `TargetCallExecuted` there, plus the target's own event in the same transaction (3 × `BatchPosterSet` in the window: Mandala Chain, Mars Chain, T-Rex). Watch `TargetCallExecuted`, `UpgradeExecuted`, `Upgraded`, `InboxToggle`, `OutboxToggle`, `RollupUpdated`, `SequencerInboxUpdated`, `BatchPosterSet`, `SequencerSet`, `MaxTimeVariationSet` and `OwnerFunctionCalled`.
13. **Robinhood Chain has no NodeInterface code.** `eth_getCode(0x00000000000000000000000000000000000000C8)` is `0x` on 4663, while Arbitrum One returns `0xfe`. Existence checks that expect precompile code there fail on Robinhood Chain; ArbSys and ArbRetryableTx do return `0xfe`.
14. **Idle is not dead.** HYCHAIN, AppChain and Plume Legacy showed no deposit and no payout in the 12-hour window. The window is a floor for activity, not a list of live chains.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics that core.md lacks (chain-agnostic) =====
TOPIC_NODE_CREATED                  = '\x4f4caa9e67fb994e349dd35d1ad0ce23053d4323f83ce11dc817b5435031d096'
TOPIC_NODE_CONFIRMED                = '\x22ef0479a7ff660660d1c2fe35f1b632cf31675c2d9378db8cec95b00d8ffa3c'
TOPIC_NODE_REJECTED                 = '\xeaffa3d968707ec919a2fc9f31d5ab2b86c905881ff561725d5a82fc95ad4640'
TOPIC_USER_STAKE_UPDATED_CLASSIC    = '\xebd093d389ab57f3566918d2c379a2b4d9539e8eb95efad9d5e465457833fde6'
TOPIC_BATCH_POSTER_SET              = '\x28bcc5626d357efe966b4b0876aa1ee8ab99e26da4f131f6a2623f1800701c21'
TOPIC_SEQUENCER_SET                 = '\xeb12a9a53eec138c91b27b4f912a257bd690c18fc8bde744be92a0365eb9b87e'
TOPIC_BATCH_POSTER_MANAGER_SET      = '\x3cd6c184800297a0f2b00926a683cbe76890bb7fd01480ac0a10ed6c8f7f6659'
TOPIC_MAX_TIME_VARIATION_SET        = '\xaa6a58dad31128ff7ecc2b80987ee6e003df80bc50cd8d0b0d1af0e07da6d19d'
TOPIC_BUFFER_CONFIG_SET             = '\xaa7a2d8175dee3b637814ad6346005dfcc357165396fb8327f649effe8abcf85'
TOPIC_FEE_TOKEN_PRICER_SET          = '\xe83d6153add50e41b8ee6c1115c4178687349bb12bc3902a50b1f6ad78a0c541'
TOPIC_UPGRADE_EXECUTED              = '\x49f6851d1cd01a518db5bdea5cffbbe90276baa2595f74250b7472b96806302e'
TOPIC_TARGET_CALL_EXECUTED          = '\x4d7dbdcc249630ec373f584267f10abf44938de920c32562f5aee93959c25258'
TOPIC_TX_TO_L1                      = '\x2b986d32a0536b7e19baa48ab949fec7b903b7fad7730820b20632d100cc3a68'
TOPIC_ROLLUP_CREATED_V3             = '\xd9bfd3bb3012f0caa103d1ba172692464d2de5c7b75877ce255c72147086a79d'
TOPIC_ROLLUP_CREATED_V1_V2          = '\x481277de518d1f364b196166b90219b996fba76138a3dc84e7fe02540eb1cbdb'
TOPIC_ORBIT_TOKEN_BRIDGE_CREATED    = '\x9a9203aa9ddcf21d8523e422e009214f0447efca13201ecdd802d8663092de7e'
TOPIC_ORBIT_TOKEN_BRIDGE_SET        = '\x003661d67ef6fa28d5937e796b7701a68fbf54c16d9434eb705715ebc28f424b'
TOPIC_ERC20_TRANSFER                = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- the flow topics (MessageDelivered, InboxMessageDelivered, BridgeCallTriggered, OutBoxTransactionExecuted, DepositInitiated, WithdrawalFinalized, TicketCreated, DepositFinalized, L2ToL1Tx, WithdrawalInitiated, OutboxToggle) are in core.md §10

-- ===== Selectors that core.md lacks =====
SEL_DEPOSIT_ERC20                   = '\xb79092fd'
SEL_CREATE_RETRYABLE_TICKET_ERC20   = '\x549e8426'
SEL_UNSAFE_CREATE_RETRYABLE_ERC20   = '\xb9b9a688'
SEL_NATIVE_TOKEN                    = '\xe1758bd8'
SEL_NATIVE_TOKEN_DECIMALS           = '\xad48cb5e'
SEL_ENQUEUE_DELAYED_MESSAGE_ERC20   = '\x75d81e25'
SEL_L2_OUTBOUND_TRANSFER_4ARG       = '\x7b3a3c8b'
SEL_ORBIT_SET_GATEWAY_FEE           = '\xdc121927'
SEL_ORBIT_REGISTER_TOKEN_FEE        = '\x3e8ee3df'
SEL_UPGRADE_EXECUTOR_EXECUTE        = '\x1cff79cd'
SEL_UPGRADE_EXECUTOR_EXECUTE_CALL   = '\xbca8c7b5'
SEL_ROLLUP_CHAIN_ID                 = '\x9a8a0592'
SEL_ALLOWED_OUTBOX_LIST             = '\x945e1147'
SEL_ALLOWED_DELAYED_INBOX_LIST      = '\xe76f5c8d'
SEL_GENESIS_ASSERTION_HASH          = '\x353325e0'
SEL_LATEST_NODE_CREATED             = '\x7ba9534a'
SEL_INBOX_TO_L1_DEPLOYMENT          = '\xd9ce0ef9'
SEL_INBOX_TO_L2_DEPLOYMENT          = '\x46052706'

-- ===== Robinhood Chain (4663) — contracts on Ethereum =====
ETH_ROBINHOOD_BRIDGE                = '\xdf8755334ce7a73ccf6b581c02ea649ae3e864b3'   -- ETH escrow
ETH_ROBINHOOD_INBOX                 = '\x1a07cc4bd17e0118bdb54d70990d2158abad7a2d'
ETH_ROBINHOOD_SEQUENCER_INBOX       = '\xbd0d173eeb87d57a09521c24388a12789f33ba96'   -- batch reports: exclude
ETH_ROBINHOOD_OUTBOX                = '\xf0ce991ea4a0d2400a4ab49b20ae333f6dce3de9'
ETH_ROBINHOOD_ROLLUP                = '\x23a19d23e89166adedbdcb432518ab01e4272d94'   -- BoLD
ETH_ROBINHOOD_L1_GATEWAY_ROUTER     = '\x6a2e3a1e16fc29f27ce61429746d558d656975bb'
ETH_ROBINHOOD_L1_ERC20_GATEWAY      = '\x85001cc4867c5e1c22da4b79bb8852b9e2a06da0'   -- escrow
ETH_ROBINHOOD_L1_CUSTOM_GATEWAY     = '\x9368eaebfe6e063c69dcf8126711a6997e0ecee1'   -- escrow
ETH_ROBINHOOD_L1_WETH_GATEWAY       = '\xf7e12b9614b509c747ab4423bc4acf923759cf1b'
ETH_ROBINHOOD_UPGRADE_EXECUTOR      = '\x552603b4bc1f5e896af2854548d6380f45f1b4bf'
ETH_ROBINHOOD_CORE_PROXY_ADMIN      = '\x1232813bdd40aa9d53066a880de78a4be70b90fd'

-- ===== Robinhood Chain (4663) — L2 side =====
RH_ARBSYS                          = '\x0000000000000000000000000000000000000064'
RH_ARB_RETRYABLE_TX                = '\x000000000000000000000000000000000000006e'
RH_L2_GATEWAY_ROUTER               = '\x1e324b9316138ca9a73f960213621ad1aaf01b89'
RH_L2_ERC20_GATEWAY                = '\xfd9b17206278c16ddaacf6ac8f05dbf97edcb31e'
RH_L2_CUSTOM_GATEWAY               = '\x912285144fc0f6e89d3ed16f5ab72f87a1878959'
RH_L2_WETH_GATEWAY                 = '\x1d187c3e2da52d72bc9c41e3aba0fdfa6a7bf055'
RH_L2_WETH                         = '\x0bd7d308f8e1639fab988df18a8011f41eacad73'
RH_L2_PROXY_ADMIN                  = '\xa3acd31afb851b4eb9dad00f5204c01d924267df'
RH_L2_UPGRADE_EXECUTOR             = '\x2a153c6a1b66dbc930a8d7017230ab0253005c09'
-- NodeInterface 0x00000000000000000000000000000000000000c8 has no code on 4663 (virtual)

-- ===== Orbit L2s on Ethereum (Bridge = escrow; Inbox = deposit entry; Outbox = payout) =====
ETH_ALIENX_BRIDGE                   = '\x69ab55146bc52a0b31f74dbdc527b8b7e9c7c27c'   -- chain 10241024
ETH_ALIENX_INBOX                    = '\x7b0159484f5cb4f3d4bb496a2ed7a01f409e70d1'
ETH_ALIENX_OUTBOX                   = '\xca2aa2aa53c2225849cc711fd472e4d2bfcd634b'
ETH_ALIENX_L1_ERC20_GATEWAY         = '\x5625d2a46fc582b3e6de5288d9c5690b20ebdb8d'
ETH_APPCHAIN_BRIDGE                 = '\x19df42e085e2c3fc4497172e412057f54d9f013e'   -- chain 466
ETH_APPCHAIN_INBOX                  = '\x010ade5d8f9dc340531140802438798c189c36e0'
ETH_APPCHAIN_OUTBOX                 = '\x190c720892d0786bf75b77b4acd21c726ea8fded'
ETH_DUAL_BRIDGE                     = '\xf568d6942808c3b57b4c85cfb6984ec41d3cf83c'   -- chain 6301
ETH_DUAL_INBOX                      = '\x5a2626323f7d7113dcd06b0a0de9a6e9945478fa'
ETH_DUAL_OUTBOX                     = '\x432c4c0c2174e21346b6ca48998035e701c3262b'
ETH_DUAL_L1_ERC20_GATEWAY           = '\x8595d3e4f504d8b970102c6bd881b272b10577b6'
ETH_GRAVITY_BRIDGE                  = '\x7983403dda368aa7d67145a9b81c5c517f364c42'   -- chain 1625
ETH_GRAVITY_INBOX                   = '\x7ad2a94beff3294a31894cfb5ba4206957a53c19'
ETH_GRAVITY_OUTBOX                  = '\x1153a1e4b1523dff36f77d696bd6ebf2b0e7dabf'
ETH_GRAVITY_L1_ERC20_GATEWAY        = '\xb23988d9728ef147eaa02d602d7e067b6131a1bb'
ETH_HPP_BRIDGE                      = '\x9948edfbb9e0b104bad60393dbe79d0bc7937014'   -- chain 190415
ETH_HPP_INBOX                       = '\xe0400a87d5ee8a2fc1df2aaf4b6d8f89d0b9be55'
ETH_HPP_OUTBOX                      = '\x433da6d107e942ec4eab1e86b16427b6071f6491'
ETH_HPP_L1_ERC20_GATEWAY            = '\x8f31c7a6806432f05a936ade26a7407c968f13ea'
ETH_HYCHAIN_BRIDGE                  = '\x73c6af7029e714dff1f1554f88b79b335011da68'   -- chain 2911
ETH_HYCHAIN_INBOX                   = '\xd6c596b7ca17870dd50d322393dece6c2085a116'
ETH_HYCHAIN_OUTBOX                  = '\x0389e24a4bc96518169f83f50fcdda442dd8eafd'
ETH_HYCHAIN_L1_ERC20_GATEWAY        = '\xa3ce255824d5e0c75d38cc88ae8d0d6a03c108cb'
ETH_PEPU_BRIDGE                     = '\xd3643255ea784c75a5325cc5a4a549c7cd62e499'   -- chain 97741
ETH_PEPU_INBOX                      = '\xe92df19f4e0fd067fe3b788cf03ffd06cd9be4a7'
ETH_PEPU_OUTBOX                     = '\xd2e3b3be0dda5e3214f551af5a4f4049b9d031a9'
ETH_PEPU_L1_ERC20_GATEWAY           = '\x7c2838461fa468896a06ca1e7d88bdece1f2e1be'
ETH_PLUME_BRIDGE                    = '\x35381f63091926750f43b2a7401b083263adef83'   -- chain 98866
ETH_PLUME_INBOX                     = '\x943fc691242291b74b105e8d19bd9e5dc2fcba1d'
ETH_PLUME_OUTBOX                    = '\x7e4627bc114fcd12ba912103279fd2858e644e71'
ETH_PLUME_L1_ERC20_GATEWAY          = '\xe2c902bc61296531e556962ffc81a082b82f5f28'
ETH_REYA_BRIDGE                     = '\x383c03c4eff819e73409dbc690755a9992393814'   -- chain 1729
ETH_REYA_INBOX                      = '\x672109752635177ebcb17f2c7e04575a709014bd'
ETH_REYA_OUTBOX                     = '\x3f373b0a7dcee7b7bcfc16df85cfae18388542c9'
ETH_REYA_L1_ERC20_GATEWAY           = '\xd117f93c458bed69fceeb8edd4babbce89db0d67'
ETH_SHIB_BRIDGE                     = '\x577dae1f00430d0013bf0b0383c460f41d3e8a8f'   -- chain 5816
ETH_SHIB_INBOX                      = '\xdc62f39a24366e708d4e09560f73df2bd1542372'
ETH_SHIB_OUTBOX                     = '\xe459eb07e9b4707caa1520651d3a367177049c85'
ETH_SHIB_L1_ERC20_GATEWAY           = '\x17fe731dfb2110afed0a1811f876e0b58603a6d2'
ETH_SX_BRIDGE                       = '\xa104c0426e95a5538e89131dbb4163d230c35f86'   -- chain 4162
ETH_SX_INBOX                        = '\xea83e8907c89bc0d9517632f0ba081972e328631'
ETH_SX_OUTBOX                       = '\xb360b2f57c645e847148d7c479b7468abf6f707d'
ETH_SX_L1_ERC20_GATEWAY             = '\xb4968c66becc8fb4f73b50354301c1adb2abaa91'
ETH_TREX_BRIDGE                     = '\x61c4b51f9388a2dd62c791341f0d50ad88d64fd4'   -- chain 1628
ETH_TREX_INBOX                      = '\x1744424936c6f1a4921130b12aa4f3832b421002'
ETH_TREX_OUTBOX                     = '\xa0419e39ca100dcfc6f0d68d605d2445f387fb4e'
ETH_TREX_L1_ERC20_GATEWAY           = '\xd1fc6140377f4b8f31f250b922b5a6a59efaac41'

-- ===== Orbit L3s on Base =====
BASE_TRANCHED_BRIDGE                 = '\x08abbe019c351d5124256d3602da6a5a40fa7c72'   -- chain 743
BASE_TRANCHED_INBOX                  = '\x02064f9943015b5675972e04289849a5f706d8fa'
BASE_TRANCHED_OUTBOX                 = '\xb42f8b96cbc3f455474c3c0a2914d45bfa675161'
BASE_L3_846737_BRIDGE                = '\x9d4ab2e611a7b9fdc0168c4c1eed563eba35a43d'   -- chain 846737
BASE_L3_846737_INBOX                 = '\xafbb601aa3c5f7d38e8c19422a9a16ecd066bcde'
BASE_L3_846737_OUTBOX                = '\x12097891604714718b1eaf24c4e7c5bcbfbc6a0a'
BASE_L3_846737_L1_ERC20_GATEWAY      = '\x11d203350a7b5177ad94efe04acda422564295a6'
BASE_DEGEN_BRIDGE                    = '\xefef4558802bf373ce3307189c79a9cab0a4cb9c'   -- chain 666666666
BASE_DEGEN_SECOND_OUTBOX             = '\xdb8e759859058952c34953c8469f464109826e52'   -- pays without OutBoxTransactionExecuted

-- ===== Other Orbit chains: Bridge (escrow) only; full rows in §3.4 and §4.3 =====
ETH_DIA_BRIDGE                      = '\x1eee9b9f024188e54930d2927d7a28e66e7649a7'   -- chain 1050
ETH_HUMANITY_BRIDGE                 = '\x8620f893f6321c31909e4a58bceb6948a289e0fd'   -- chain 6985385
ETH_HUMANITY_13600000_BRIDGE        = '\x29786f674ed06684c5493aa5071b8b6f235ba411'   -- chain 13600000
ETH_GALACTICA_BRIDGE                = '\xd75a60afcbc113c1c76e42184663da141f839053'   -- chain 613419
ETH_SYMBIOSIS_BRIDGE                = '\xe61fbe55ec57394b02bdb6a88c3d71adb2d63826'   -- chain 13863860
ETH_MANDALA_BRIDGE                  = '\x65db181838b53f32428ce106fa5355b7e4806b79'   -- chain 20010
ETH_CITRONUS_BRIDGE                 = '\x9016fa334b99282b01a9507a607861ad333e9315'   -- chain 50000
ETH_STUDIO_BRIDGE                   = '\xca5f6ec5c9b482bfdaae6074e7686e7fbd4755ad'   -- chain 4509
BASE_WORLD_MOBILE_BRIDGE             = '\x249888c93f18f50a0eca6a29b644f8fa1ff7539d'   -- chain 869
BASE_INTUITION_BRIDGE                = '\x98ec528e10d54c3db77c08021644dbe48e994726'   -- chain 1155
BASE_XMTP_BRIDGE                     = '\xa9c3b7672c477eeda999a3ab1c8eec28deeb7d41'   -- chain 241320162
BASE_L3_414_BRIDGE                   = '\x2df9dea9c9289bae9658cb732c45d0b0657341e6'   -- chain 414
BASE_CRYNUX_BRIDGE                   = '\x01d9db097dc8b30efbc266fd80b233fb6b6bff40'   -- chain 18896214
ETH_XCHAIN_BRIDGE                   = '\x2be65c5b58f78b02ab5c0e798a9ffc181703d3c1'   -- chain 94524
ETH_PLUME_LEGACY_BRIDGE             = '\xd53645c6b5e19b3ce2d00ba27d734dcc928fcc54'   -- chain 98865
ETH_SYNDICATE_BRIDGE                = '\x3c8cf0ae6e89ac0796f29b3a58e7dea1cd072277'   -- chain 510
BASE_UNITE_BRIDGE                    = '\x80b4c2dbeacff9921cd456e5e1489919185b8a1d'   -- chain 88899

-- ===== Orbit L3s on Arbitrum One (Bridge = escrow); full rows in §5 =====
ARB_L3_2886_BRIDGE                  = '\x53a7559d1e57e371f3d1e55fea97e9b6748418a3'   -- chain 2886
ARB_EDGE_BRIDGE                     = '\x6f4836afd5e21edcee9b838c5a4125829ec198d0'   -- chain 3343
ARB_L3_20231119_BRIDGE              = '\xd4fe46d2533e7d03382ac6cacf0547f336e59dc0'   -- chain 20231119
ARB_L3_261131_BRIDGE                = '\xb95b70f48c9f45293d1ee6670d0c5d8d4f045e46'   -- chain 261131
ARB_ETHEREAL_BRIDGE                 = '\xd86f5ad3fa5becbb07e565dbd4b70dbd817a43a8'   -- chain 5064014
ARB_L3_27182_BRIDGE                 = '\xcfa2a006e3bf72a7bd300e2a04295d69f9934b73'   -- chain 27182
ARB_SANKO_BRIDGE                    = '\x2f285781b8d58678a3483de52d618198e4d27532'   -- chain 1996
ARB_L3_4485770_BRIDGE               = '\xe486ccb88ac257b2c55fc3d5f222ccc895812121'   -- chain 4485770
ARB_L3_8818_BRIDGE                  = '\xaa4f1669d4f366626fd0630b2954883143e1bc3d'   -- chain 8818
ARB_L3_61022894_BRIDGE              = '\x42c4b496eda79215872de91f71d77f434098e162'   -- chain 61022894
ARB_APECHAIN_BRIDGE                 = '\x6b71afb4b7725227ab944c96fe018ab9dc0434b8'   -- chain 33139
ARB_MAWARI_BRIDGE                   = '\x3437bd1a174e0528989ae0d5023c05018502cc34'   -- chain 1576
ARB_XAI_BRIDGE                      = '\x7dd8a76bdaebe3bbbacd7aa87f1d4fda1e60f94f'   -- chain 660279
ARB_L3_1247_BRIDGE                  = '\xa4b7c8ae3ccb4960f45e753c5690902ef53cb28c'   -- chain 1247
ARB_CARRCHAIN_BRIDGE                = '\x1157f519750bdb190c4ad847ac2f53e805df5c0c'   -- chain 7667
ARB_ANIMECHAIN_BRIDGE               = '\x8764106f840841183855e291a0e64b40cf20d9d3'   -- chain 69000
ARB_L3_529375_BRIDGE                = '\xe8c495583789a49b90d2de3021bcc5bf42673f89'   -- chain 529375
ARB_EDU_CHAIN_BRIDGE                = '\x2f12c50b46adb01a4961adda5038c0974c7c78e8'   -- chain 41923
ARB_EARNM_BRIDGE                    = '\xa9f4ee72439afc704db48dc049cbfb7e914ad300'   -- chain 32766
ARB_RARI_BRIDGE                     = '\x255f80ef2f09fce0944fabb292b8510f01316cf0'   -- chain 1380012617
ARB_MUSTER_BRIDGE                   = '\xb0ec3c1368af7d9c2cae6b7f8e022cc14d59d2b1'   -- chain 4078
ARB_SUPERPOSITION_BRIDGE            = '\xeca0feb4aa6112a3923823559e7197294bc49cc7'   -- chain 55244
ARB_MIND_NETWORK_BRIDGE             = '\x34f81f9c4f3227dbaccff8e51dbaa1571e114759'   -- chain 228
ARB_SPOTLIGHT_BRIDGE                = '\x37d3139024d017c2152849b154f2631e2f2c8560'   -- chain 10058111
ARB_CHEESECHAIN_BRIDGE              = '\xa337997ab18164dfe1e8a94e8d912e8d4e2ce173'   -- chain 383353
ARB_CHAINBOUNTY_BRIDGE              = '\xd46ab997110a91c4cb6f4576ffe6769a3033622a'   -- chain 51828
ARB_CONWAI_BRIDGE                   = '\x9be649c1c1d073536d55db83aba093e8558a962e'   -- chain 668668
ARB_L3_92278_BRIDGE                 = '\xaf25849aeb040beab7a0c783fc6861d26ae49796'   -- chain 92278
ARB_BIRDLAYER_BRIDGE                = '\x113e7dc5e4a42b1bee9db0594f48efdea7b88ee0'   -- chain 53456
ARB_RCADE_BRIDGE                    = '\x13355730a242744d71f1e489896837f70797fb26'   -- chain 101069
ARB_MOLTEN_BRIDGE                   = '\xe1d32c985825562edaa906fac39295370db72195'   -- chain 360
ARB_MEERCHAIN_BRIDGE                = '\x55a1b18e0300ad707617b828e0554765dbfc8535'   -- chain 98215
ARB_L3_2886_L1_ERC20_GATEWAY        = '\x483754470664ea3d99fa79ae803e56ca0afe4827'
ARB_SANKO_SECOND_OUTBOX             = '\xa9aa07f082d9c15d0b6d7e9e5b68b1f898399c29'   -- pays without OutBoxTransactionExecuted
ARB_TOKEN_BRIDGE_CREATOR            = '\x2f5624dc8800dfa0a82ac03509ef8bb8e7ac000e'
ARB_ROLLUP_CREATOR_V3_2             = '\xf5962ad061a1ad6f38f340f5b267b3593cc1cd7b'

-- ===== xMoney L3 (466302) on Robinhood Chain =====
RH_XMONEY_BRIDGE                   = '\x2290f4505484f055b710e7df37e2482c90b8b6fb'   -- ERC20Bridge, fee token xMoney
RH_XMONEY_INBOX                    = '\xa7087693676f2ca8e5e9563a6859952258688146'
RH_XMONEY_OUTBOX                   = '\xa6f07dd42cfe78ec8d88484b238b3b05149eb2b3'

-- ===== Factories =====
ETH_TOKEN_BRIDGE_CREATOR            = '\x60d9a46f24d5a35b95a78dd3e793e55d94ee0660'
ETH_ROLLUP_CREATOR_V3_2             = '\xe06bc77336e201c4c08751918a4bb99ddf0e1bf7'
BASE_TOKEN_BRIDGE_CREATOR            = '\x4c240987d6fe4fa8c7a0004986e3db563150ca55'
BASE_ROLLUP_CREATOR_V3_2             = '\x8d1668636d053c10f57367d68118bd624f41ffe6'
RH_TOKEN_BRIDGE_CREATOR            = '\x8b1eff64e1ead493a82c6798f5708183af91a3ad'
RH_ROLLUP_CREATOR_V3_2             = '\xf5962ad061a1ad6f38f340f5b267b3593cc1cd7b'
```

---

## 11. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` and `[0:4]` from the Solidity sources: `nitro-contracts` v2.1.3 `IRollupCore.sol` + `Node.sol` + `GlobalState.sol` + `Machine.sol` (classic Rollup structs), v3.2.0 `ISequencerInbox.sol` + `DelayBufferTypes.sol`, `IERC20Inbox.sol`, `IERC20Bridge.sol`, `RollupCreator.sol` (v1.1.1, v2.1.3, v3.2.0); `token-bridge-contracts` v1.2.5 `L2ArbitrumMessenger.sol`, `L1AtomicTokenBridgeCreator.sol`, `L1TokenBridgeRetryableSender.sol` (deployment structs), `L1OrbitGatewayRouter.sol`, `L1OrbitCustomGateway.sol`; `upgrade-executor` `UpgradeExecutor.sol`. Live confirmation: `NodeCreated` / `NodeConfirmed` 50 each on Ethereum and 25 each on Base; `TargetCallExecuted` 20 and `BatchPosterSet` 3 on Ethereum; `TxToL1` 10 on Robinhood Chain and 3 on Arbitrum One (L2ERC20Gateway `0x09e9222E96E7B4AE2a407B98d48e330053351EEe`). Selectors found by a PUSH4 scan of the live implementation bytecode: `depositERC20`, the 9-argument retryables, `nativeToken`, `nativeTokenDecimals` and 4-argument `enqueueDelayedMessage` in the Shib Mainnet and Gravity Alpha ERC20Inbox / ERC20Bridge (and `depositEth` absent there); `depositEth` and the 8-argument retryable in the Robinhood Chain Inbox (and `depositERC20` absent); the 4-argument L2 `outboundTransfer` in the Robinhood Chain and Arbitrum One L2 router and gateways; the fee-amount `setGateway` / `registerTokenToL2` in the Gravity Alpha Orbit router and custom gateway; `execute` / `executeCall` in the Robinhood Chain UpgradeExecutor; `genesisAssertionHash` present and `latestNodeCreated` absent in the Robinhood Chain Rollup user logic.
- **Addresses:** every Orbit chain resolved on chain from its Bridge, SequencerInbox or Outbox (`rollup()`, `chainId()`, `inbox()`, `outbox()`, `sequencerInbox()`, `allowedDelayedInboxList`, `allowedOutboxList`, `nativeToken()`); token bridges from the TokenBridgeCreator (`inboxToL1Deployment`, `inboxToL2Deployment`); 425 addresses existence-checked with `eth_getCode` on their chain, all with code except NodeInterface on 4663. Proxy implementation and admin slots read live. Robinhood Chain rows equal the Robinhood Chain docs one for one.
- **Chain coverage:** Ethereum, Base, Arbitrum One and Robinhood Chain carry Orbit settlement contracts; Optimism, Polygon PoS, BNB and Avalanche carry none (§7).
- **Activity** (pinned 12-hour window 2026-09-28 00:00–12:00 UTC: Ethereum blocks 26,072,222–26,075,812; Base blocks 51,882,127–51,903,726; Robinhood Chain blocks 74,350,994–74,780,331), `eth_getLogs` counted per emitter:

| Chain | Delayed-inbox messages (`InboxMessageDelivered` at the Inbox) | Batch reports (at the SequencerInbox) | `DepositInitiated` (gateways) | `OutBoxTransactionExecuted` | `BridgeCallTriggered` | `WithdrawalFinalized` | Batches | Assertions or nodes created / confirmed |
|---|---|---|---|---|---|---|---|---|
| **Robinhood Chain** | 153 | 1,363 | 55 | 19 | 19 | 17 | 1,363 | 23 / 23 |
| AlienX | 0 | 3 | 0 | 5 | 5 | 0 | 3 | 3 / 2 (node) |
| AppChain | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 / 0 (node) |
| Dual | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 12 / 12 |
| Gravity Alpha | 0 | 0 | 0 | 23 | 23 | 0 | 1 | 1 / 1 |
| HPP | 0 | 24 | 0 | 0 | 0 | 0 | 24 | 2 / 2 |
| HYCHAIN | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 / 0 (node) |
| Pepe Unchained V2 | 0 | 0 | 0 | 2 | 2 | 0 | 11 | 1 / 1 |
| Plume | 0 | 0 | 0 | 0 | 0 | 0 | 71 | 2 / 1 |
| Reya | 0 | 124 | 0 | 2 | 2 | 0 | 124 | 22 / 23 |
| Shib Mainnet | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 1 / 0 |
| SX Rollup | 0 | 0 | 0 | 2 | 2 | 2 | 47 | 46 / 46 (node) |
| T-Rex | 0 | 2 | 0 | 4 | 4 | 0 | 2 | 1 / 0 |
| Tranched (Base) | 0 | 2 | 0 | 0 | 0 | 0 | 2 | 2 / 2 (node) |
| unnamed (fee token PANAX) (Base) | 1 | 0 | 0 | 0 | 0 | 0 | 46 | 36 / 37 |

  A 0 is a measurement of 12 hours, not a verdict on the chain. Sample receipts read to confirm the value legs: Robinhood Chain `depositEth` `0x18100c3e54f24ccb7437eb58abfa626a95a9c08e6712177c4c9448099c45b40b` (kind 12, 0.0999 ETH in `msg.value`); token deposit `0x0d6994a1c67f2e0eba7d59031b7afb32a4e1c7bdb550bf8386528d3829de827e` (token `Transfer` user → L1ERC20Gateway, kind 9); ETH payout `0xec27ef3d1ec9dfbed082f5871836045df50e8a781e564e8ac602010453f7ccce` (`BridgeCallTriggered` value 0.1294 ETH); Shib Mainnet `depositERC20` `0xde666994d4c9919ad6743a55d3b831c299fb98ed094b0adaddcce03f54566405` (SHIB user → ERC20Inbox → ERC20Bridge); Gravity Alpha payout `0xf00b672feb4d755d14c97da2de8eb1931192e44ba6a75343e344e9c6c0efacde` (G from the ERC20Bridge); SX Rollup token payout `0xd24c3be2b823f75b3eb2afb8e5c88de1f34a3bac6d710a8eae721ed688826bf6` (USDC escrow → user, `WithdrawalFinalized`); chain 846737 retryable `0x3abee364d49b0053c07e5b5c3a36d662dcaaecb44add722b1aa2990c3e88a084` on Base (PANAX user → ERC20Inbox → ERC20Bridge); Degen Chain payout `0x97578c44507608d6697b4b226666ccab2f5e0063d39130266851ae8ec5a2b515` on Base (second outbox); the Robinhood Chain L2 receipts of §6.3; xMoney payout `0x2deb7314f77893a47a02e32f72f0cd2483408b3b51afbdd0f909378f2d14ceee`.

Sources opened:

- Robinhood Chain docs — [protocol contracts](https://docs.robinhood.com/chain/protocol-contracts)
- Arbitrum docs — [contract addresses](https://docs.arbitrum.io/build-decentralized-apps/reference/contract-addresses)
- Arbitrum bridge registry — [`OffchainLabs/arbitrum-token-bridge` `packages/arb-token-bridge-ui/src/util/orbitChainsData.json`](https://github.com/OffchainLabs/arbitrum-token-bridge/blob/master/packages/arb-token-bridge-ui/src/util/orbitChainsData.json)
- Orbit SDK factory maps — [`OffchainLabs/arbitrum-orbit-sdk` `src/contracts/TokenBridgeCreator/v1.2.ts` and `src/contracts/RollupCreator/v1.1.ts`, `v2.1.ts`, `v3.1.ts`, `v3.2.ts`](https://github.com/OffchainLabs/arbitrum-orbit-sdk/tree/main/src/contracts)
- Canonical sources — [`OffchainLabs/nitro-contracts`](https://github.com/OffchainLabs/nitro-contracts) (tags v1.1.1, v2.1.3, v3.2.0) · [`OffchainLabs/token-bridge-contracts`](https://github.com/OffchainLabs/token-bridge-contracts) (tag v1.2.5) · [`OffchainLabs/upgrade-executor`](https://github.com/OffchainLabs/upgrade-executor) · [`OffchainLabs/nitro-precompile-interfaces`](https://github.com/OffchainLabs/nitro-precompile-interfaces)
- Chain names — [chainid.network `chains.json`](https://chainid.network/chains.json) · chainlist [1628](https://chainlist.org/chain/1628), [6301](https://chainlist.org/chain/6301), [4509](https://chainlist.org/chain/4509), [704851](https://chainlist.org/chain/704851) · [ethereum-lists/chains PR #8781 (Shib Mainnet, open)](https://github.com/ethereum-lists/chains/pull/8781)
- Chain state — the public RPC endpoints of Ethereum, Base, Arbitrum One, Optimism, Polygon PoS, BNB, Avalanche and Robinhood Chain (`https://rpc.mainnet.chain.robinhood.com`); `https://rpc.shib.club` (`eth_chainId` only)
