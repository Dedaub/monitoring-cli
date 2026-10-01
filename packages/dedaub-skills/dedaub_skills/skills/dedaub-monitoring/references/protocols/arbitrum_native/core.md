# Arbitrum Canonical Bridge (Nitro) — Topics, Selectors, Addresses (Ethereum L1 ↔ Arbitrum One / Nova L2)

**Status:** verified against live RPC on Ethereum (1), Arbitrum One (42161) and Arbitrum Nova (42170) and against the canonical `OffchainLabs/nitro-contracts` + `OffchainLabs/token-bridge-contracts` repos on 2026-06-09. Extended on 2026-09-29 (live RPC on Ethereum, Arbitrum One and Robinhood Chain): the Classic Outboxes, the DAI, GRT, ARB and wstETH custom gateways and their escrows, `TxToL1`, the 4-argument L2 `outboundTransfer`, and Robinhood Chain (4663) coverage.
**Scope:** the native (canonical) Arbitrum bridge — the Nitro core messaging stack (Inbox / Bridge / Outbox / SequencerInbox / Rollup) plus the token bridge (GatewayRouter + ERC20/Custom/Weth gateways) and the L2 system precompiles (ArbSys, ArbRetryableTx). Event topics and function selectors are **chain-agnostic**; addresses are **network-specific**. The target chains are Ethereum, Base, BNB, Avalanche, Arbitrum One, Optimism, Polygon and Robinhood Chain (4663). **The canonical Arbitrum One / Nova bridge is anchored on Ethereum L1 (chain 1) and Arbitrum One L2 (42161) only of the eight.** Base, BNB, Avalanche, Optimism, Polygon and Robinhood Chain carry **none** of these contracts (`eth_getCode` = `0x` for every address — §6). Arbitrum **Nova** L2 (chain 42170) is the second counterparty but is **outside the eight**; its L1 contracts (which live on Ethereum) are documented in §4 as a recorded finding. Robinhood Chain and the other Arbitrum Orbit chains run their own copies of these contracts under their own addresses: see `orbit.md`.

The bridge is a set of **EIP-1967 transparent proxies** (no CREATE2 vanity, no per-token instances — one fixed singleton per role per rollup). Deposits are L1→L2 messages: a user calls a gateway/Inbox on L1, the `Bridge` enqueues a delayed message (`MessageDelivered`), the `Inbox` records the payload (`InboxMessageDelivered`), and a **retryable ticket** auto-executes on L2. Withdrawals are L2→L1: a user calls `ArbSys.sendTxToL1` (or an L2 gateway that calls it) emitting **`L2ToL1Tx`**, the sequencer posts a batch (`SequencerBatchDelivered`), the Rollup confirms an assertion (`AssertionConfirmed`), and after the ~6.4-day challenge window the user calls `Outbox.executeTransaction` (`OutBoxTransactionExecuted`). The two halves never share an event in the same transaction — attribution is by the cross-chain `messageHash` / `position`, not by `tx.from`.

> **Two non-obvious facts you must internalize before indexing.** (1) **The live Arbitrum One Rollup is `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0`, NOT the well-known `0x5eF0D09d1E6204141B4d37530808eD19f60FBa35`.** `0x5eF0D09d1E6204141B4d37530808eD19f60FBa35` is the **original, now-disconnected** classic-Nitro Rollup; `Bridge.rollup()` returns `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0`. The current rollup runs **BoLD** (Bound-Liquidity Delay) dispute resolution and emits **`AssertionCreated`/`AssertionConfirmed`**, *not* the legacy `NodeCreated`/`NodeConfirmed` (§1.5; the classic events are in `orbit.md` §1.1). (2) The L1 contract that an L2 contract "is" (its alias) is offset by `0x1111000000000000000000000000000000001111` — `MessageDelivered.sender` is the alias of the L1 caller, of an EOA as well as of a contract, not the raw L1 address (§9).

---

## 0. Contract families & versions

| Family | Contracts | Role | Repo |
|--------|-----------|------|------|
| **Core / messaging** | Inbox, Bridge, Outbox, SequencerInbox, RollupProxy (+ admin/user logic) | L1 entry/exit + sequencer + fraud proof | `OffchainLabs/nitro-contracts` |
| **Token bridge** | L1GatewayRouter, L1ERC20Gateway, L1CustomGateway, L1WethGateway (L1); L2GatewayRouter, L2ERC20Gateway, L2CustomGateway, L2WethGateway (L2) | Canonical ERC-20 / WETH / ETH bridging | `OffchainLabs/token-bridge-contracts` |
| **L2 system precompiles** | ArbSys (`0x0000000000000000000000000000000000000064`), ArbRetryableTx (`0x000000000000000000000000000000000000006E`), NodeInterface (`0x00000000000000000000000000000000000000C8`) | L2-side withdrawal init, retryable lifecycle, gas estimation | ArbOS (`OffchainLabs/nitro`) |

There is **one** continuously-upgraded generation (Nitro, live since the Aug-2022 Nitro migration). Arbitrum One's dispute layer was upgraded to **BoLD** in 2025; that changed the **Rollup address and its event set** but left the Inbox/Bridge/Outbox/SequencerInbox/gateway topics and selectors unchanged. Hence one `core.md`, with the classic vs BoLD Rollup split called out explicitly.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-09; each marked *(live)* was additionally confirmed against real `eth_getLogs` on the cited emitter.

### 1.1 Bridge (the message ledger) — ETH emitter (One) `0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a`, (Nova) `0xC1Ebd02f738644983b6C4B2d440b8e77DdE276Bd`

| topic0 | Event |
|--------|-------|
| `0x5e3c1311ea442664e8b1611bfabef659120ea7a0a2cfc0667700bebc69cbffe1` | `MessageDelivered(uint256 indexed messageIndex, bytes32 indexed beforeInboxAcc, address inbox, uint8 kind, address sender, bytes32 messageDataHash, uint256 baseFeeL1, uint64 timestamp)` *(live, 242 logs / 2k blk)* |
| `0x2d9d115ef3e4a606d698913b1eae831a3cdfe20d9a83d48007b0526749c3d466` | `BridgeCallTriggered(address indexed outbox, address indexed to, uint256 value, bytes data)` (L2→L1 call dispatched by Outbox via Bridge) |
| `0x6675ce8882cb71637de5903a193d218cc0544be9c0650cb83e0955f6aa2bf521` | `InboxToggle(address indexed inbox, bool enabled)` (delayed-inbox allowlist change) |
| `0x49477e7356dbcb654ab85d7534b50126772d938130d1350e23e2540370c8dffa` | `OutboxToggle(address indexed outbox, bool enabled)` |
| `0x8c1e6003ed33ca6748d4ad3dd4ecc949065c89dceb31fdf546a5289202763c6a` | `SequencerInboxUpdated(address newSequencerInbox)` |
| `0xae1f5aa15f6ff844896347ceca2a3c24c8d3a27785efdeacd581a0a95172784a` | `RollupUpdated(address rollup)` |

`MessageDelivered.kind` is the L1 message type (`3` = L2 message, `7` = L2 message funded by L1, `9` = retryable ticket, `12` = ETH deposit, `13` = batch-cost report from the SequencerInbox; `nitro-contracts` `MessageTypes.sol`). `MessageDelivered.sender` is **always aliased**: the Inbox passes `applyL1ToL2Alias(msg.sender)` for an EOA and for a contract alike (§9, item 3).

### 1.2 Inbox (delayed-message entry) — (One) `0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f`, (Nova) `0xc4448b71118c9071Bcb9734A0EAc55D18A153949`

| topic0 | Event |
|--------|-------|
| `0xff64905f73a67fb594e0f940a8075a860db489ad991e032f48c81123eb52d60b` | `InboxMessageDelivered(uint256 indexed messageNum, bytes data)` *(live, 51 logs / 2k blk; the SequencerInbox also emits it, once per batch-cost report: 364 at the One SequencerInbox against 160 at the Delayed Inbox in the window of §11)* |
| `0xab532385be8f1005a4b6ba8fa20a2245facb346134ac739fe9a5198dc1580b9c` | `InboxMessageDeliveredFromOrigin(uint256 indexed messageNum)` (gas-optimized variant: payload is in calldata, not the log) |

### 1.3 SequencerInbox (batch poster) — (One) `0x1c479675ad559DC151F6Ec7ed3FbF8ceE79582B6`, (Nova) `0x211E1c4c7f1bF5351Ac850Ed10FD68CFfCF6c21b`

| topic0 | Event |
|--------|-------|
| `0x7394f4a19a13c7b92b5bb71033245305946ef78452f7b4986ac1390b5df4ebd7` | `SequencerBatchDelivered(uint256 indexed batchSequenceNumber, bytes32 indexed beforeAcc, bytes32 indexed afterAcc, bytes32 delayedAcc, uint256 afterDelayedMessagesRead, (uint64,uint64,uint64,uint64) timeBounds, uint8 dataLocation)` *(live, 100 logs / 1k blk)* |
| `0xfe325ca1efe4c5c1062c981c3ee74b781debe4ea9440306a96d2a55759c66c20` | `SequencerBatchData(uint256 indexed batchSequenceNumber, bytes data)` (calldata batch payload; absent for blob/DAS batches) |
| `0xabca9b7986bc22ad0160eb0cb88ae75411eacfba4052af0b457a9335ef655722` | `SetValidKeyset(bytes32 indexed keysetHash, bytes keysetBytes)` (AnyTrust DAS keyset — primarily Nova) |
| `0x5cb4218b272fd214168ac43e90fb4d05d6c36f0b17ffb4c2dd07c234d744eb2a` | `InvalidateKeyset(bytes32 indexed keysetHash)` |
| `0xea8787f128d10b2cc0317b0c3960f9ad447f7f6c1ed189db1083ccffd20f456e` | `OwnerFunctionCalled(uint256 indexed id)` (admin action marker; **also** emitted by Rollup/Bridge — disambiguate by emitter) |

> The current `SequencerBatchDelivered` carries a `delayedAcc` field absent from older Nitro versions — the legacy 6-field signature hashes to `0x12331e99e77abfe6c3fda90920bb3a50e7d719bbd49c62e4341be6a086290996` and **does not appear** in live logs. Use `0x7394f4a19a13c7b92b5bb71033245305946ef78452f7b4986ac1390b5df4ebd7`.

### 1.4 Outbox (L2→L1 execution) — (One) `0x0B9857ae2D4A3DBe74ffE1d7DF045bb7F96E4840`, (Nova) `0xD4B80C3D7240325D18E645B49e6535A3Bf95cc58`

| topic0 | Event |
|--------|-------|
| `0x20af7f3bbfe38132b8900ae295cd9c8d1914be7052d061a511f3f728dab18964` | `OutBoxTransactionExecuted(address indexed to, address indexed l2Sender, uint256 indexed zero, uint256 transactionIndex)` *(live, 28 logs / 7k blk; fires once per finalized withdrawal claim)* |
| `0xb4df3847300f076a369cd76d2314b470a1194d9e8a6bb97f1860aee88a5f6748` | `SendRootUpdated(bytes32 indexed outputRoot, bytes32 indexed l2BlockHash)` *(live, 24 logs / 7k blk; a new withdrawal Merkle root became spendable)* |

**Classic Outboxes (One only, pre-Nitro)** — `0x760723CD2e632826c38Fef8CD438A4CC7E7E1A40` and `0x667e23ABd27E623c11d4CC00ca3EC4d0bD63337a` (§3.4). They still pay old pre-Nitro withdrawals through the same Bridge. The classic event has the same types, so the same topic0, but its third indexed field is the classic outbox entry index, not zero:

| topic0 | Event |
|--------|-------|
| `0x20af7f3bbfe38132b8900ae295cd9c8d1914be7052d061a511f3f728dab18964` | `OutBoxTransactionExecuted(address indexed destAddr, address indexed l2Sender, uint256 indexed outboxEntryIndex, uint256 transactionIndex)` *(live: 4 at Classic Outbox 1 and 0 at Classic Outbox 2 in the window of §11; sample third topic `0x204e`)* |
| `0xe5ccc8d7080a4904b2f4e42d91e8f06b13fe6cb2181ad1fe14644e856b44c131` | `OutboxEntryCreated(uint256 indexed batchNum, uint256 outboxEntryIndex, bytes32 outputRoot, uint256 numInBatch)` (historical: no new classic entries; 0 in the window) |

### 1.5 Rollup — **current (BoLD) Arbitrum One** `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0` · Nova `0xE7E8cCC7c381809BDC4b213CE44016300707B7Bd`

These are the events the **live** rollup emits. The legacy `NodeCreated`/`NodeConfirmed`/`NodeRejected` (classic Nitro, `orbit.md` §1.1; still live on the classic Rollups of several Orbit chains) are **dead** on Arbitrum One — they only ever fired on the now-disconnected `0x5eF0D09d1E6204141B4d37530808eD19f60FBa35` rollup.

| topic0 | Event |
|--------|-------|
| `0x901c3aee23cf4478825462caaab375c606ab83516060388344f0650340753630` | `AssertionCreated(bytes32 indexed assertionHash, bytes32 indexed parentAssertionHash, ((bytes32,bytes32,(bytes32,uint256,address,uint64,uint64)),((bytes32[2],uint64[2]),uint8,bytes32),((bytes32[2],uint64[2]),uint8,bytes32)) assertion, bytes32 afterInboxBatchAcc, uint256 inboxMaxCount, bytes32 wasmModuleRoot, uint256 requiredStake, address challengeManager, uint64 confirmPeriodBlocks)` *(live, 34 logs / 30k blk)* |
| `0xfc42829b29c259a7370ab56c8f69fce23b5f351a9ce151da453281993ec0090c` | `AssertionConfirmed(bytes32 indexed assertionHash, bytes32 blockHash, bytes32 sendRoot)` *(live, 60 logs / 30k blk)* |
| `0xfc1b83c11d99d08a938e0b82a0bd45f822f71ff5abf23f999c93c4533d752464` | `RollupInitialized(bytes32 machineHash, uint256 chainId)` (one-shot at deploy) |
| `0x6db7dc2f507647d135035469b27aa79cea90582779d084a7821d6cd092cbd873` | `RollupChallengeStarted(uint64 indexed challengeIndex, address asserter, address challenger, uint64 challengedAssertion)` |
| `0xd957cf2340073335d256f72a9ef89cf1a43c31143341a6a53575ef33e987beb8` | `UserStakeUpdated(address indexed user, address indexed withdrawalAddress, uint256 initialBalance, uint256 finalBalance)` (BoLD 4-arg) |
| `0xa740af14c56e4e04a617b1de1eb20de73270decbaaead14f142aabf3038e5ae2` | `UserWithdrawableFundsUpdated(address indexed user, uint256 initialBalance, uint256 finalBalance)` |
| `0xea8787f128d10b2cc0317b0c3960f9ad447f7f6c1ed189db1083ccffd20f456e` | `OwnerFunctionCalled(uint256 indexed id)` |

### 1.6 ArbSys precompile (L2 `0x0000000000000000000000000000000000000064`) — L2→L1 message origin

| topic0 | Event |
|--------|-------|
| `0x3e7aafa77dbf186b7fd488006beff893744caa3c4f6f299e8a709fa2087374fc` | `L2ToL1Tx(address caller, address indexed destination, uint256 indexed hash, uint256 indexed position, uint256 arbBlockNum, uint256 ethBlockNum, uint256 timestamp, uint256 callvalue, bytes data)` *(live; this is the canonical Nitro withdrawal event)* |
| `0xe9e13da364699fb5b0496ff5a0fc70760ad5836e93ba96568a4e42b9914a8b95` | `SendMerkleUpdate(uint256 indexed reserved, bytes32 indexed hash, uint256 indexed position)` *(live; the withdrawal-tree leaf companion to L2ToL1Tx)* |

> **`L2ToL1Tx` (`0x3e7aafa77dbf186b7fd488006beff893744caa3c4f6f299e8a709fa2087374fc`) replaced the pre-Nitro `L2ToL1Transaction(address caller, address indexed destination, uint256 indexed uniqueId, uint256 indexed batchNumber, uint256 indexInBatch, uint256 arbBlockNum, uint256 ethBlockNum, uint256 timestamp, uint256 callvalue, bytes data)` (`0x5baaa87db386365b5c161be377bc3d8e317e8d98d71a3ca7ed7d555340c8f767`, 10 arguments), which the ArbSys interface (`OffchainLabs/nitro-precompile-interfaces` `ArbSys.sol`) still declares as deprecated.** In the window of §11 ArbSys on Arbitrum One emitted 12 `L2ToL1Tx` and 0 `L2ToL1Transaction`. Two mis-derived values circulate and never fire: `0x60d31e9c307cb3cf20a3a452ca6019c46058a1b278f098b85c648543bb4a4902` (an 11-argument `L2ToL1Transaction` that no contract declares) and `0x47ee703badfed63a907c70867d6cedee0757d28f943ceb03353f090945195454` (a 10-argument `L2ToL1Tx` with one extra `uint256`).

### 1.7 ArbRetryableTx precompile (L2 `0x000000000000000000000000000000000000006E`)

| topic0 | Event |
|--------|-------|
| `0x5ccd009502509cf28762c67858994d85b163bb6e451f5e9df7c5e18c9c2e123e` | `RedeemScheduled(bytes32 indexed ticketId, bytes32 indexed retryTxHash, uint64 indexed sequenceNum, uint64 donatedGas, address gasDonor, uint256 maxRefund, uint256 submissionFeeRefund)` |
| `0x7c793cced5743dc5f531bbe2bfb5a9fa3f40adef29231e6ab165c08a29e3dd89` | `TicketCreated(bytes32 indexed ticketId)` (a retryable ticket was created on L2) |
| `0xf4c40a5f930e1469fcc053bf25f045253a7bad2fcc9b88c05ec1fca8e2066b83` | `LifetimeExtended(bytes32 indexed ticketId, uint256 newTimeout)` (`keepalive`) |
| `0x134fdd648feeaf30251f0157f9624ef8608ff9a042aad6d13e73f35d21d3f88d` | `Canceled(bytes32 indexed ticketId)` |
| `0x27fc6cca2a0e9eb6f4876c01fc7779b00cdeb7277a770ac2b844db5932449578` | `Redeemed(bytes32 indexed ticketId)` |

### 1.8 Token bridge — gateways & router

L1ERC20Gateway/L1CustomGateway/L1WethGateway emit `DepositInitiated` (L1→L2) and `WithdrawalFinalized` (when an L2 withdrawal is paid out on L1). L2 gateways emit the mirror `WithdrawalInitiated` / `DepositFinalized`. The `TxToL2` event is the inbox-ticket helper fired by L1 gateways. Same topic0s on both rollups.

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xb8910b9960c443aac3240b98585384e3a6f109fbf6969e264c3f183d69aba7e1` | `DepositInitiated(address l1Token, address indexed from, address indexed to, uint256 indexed sequenceNumber, uint256 amount)` *(live, 409 logs / 50k blk on L1ERC20Gateway)* | L1 gateways |
| `0x3073a74ecb728d10be779fe19a74a1428e20468f5b4d167bf9c73d9067847d73` | `WithdrawalInitiated(address l1Token, address indexed from, address indexed to, uint256 indexed l2ToL1Id, uint256 exitNum, uint256 amount)` | L2 gateways |
| `0xc7f2e9c55c40a50fbc217dfc70cd39a222940dfa62145aa0ca49eb9535d4fcb2` | `DepositFinalized(address indexed l1Token, address indexed from, address indexed to, uint256 amount)` *(live on L2ERC20Gateway)* | L2 gateways |
| `0x891afe029c75c4f8c5855fc3480598bc5a53739344f6ae575bdb7ea2a79f56b3` | `WithdrawalFinalized(address l1Token, address indexed from, address indexed to, uint256 indexed exitNum, uint256 amount)` *(live, 139 logs / 50k blk on L1ERC20Gateway)* | L1 gateways |
| `0xc1d1490cf25c3b40d600dfb27c7680340ed1ab901b7e8f3551280968a3b372b0` | `TxToL2(address indexed from, address indexed to, uint256 indexed seqNum, bytes data)` *(live, 409 logs / 50k blk on L1ERC20Gateway)* | L1 gateways/router |
| `0x85291dff2161a93c2f12c819d31889c96c63042116f5bc5a205aa701c2c429f5` | `TransferRouted(address indexed token, address indexed _userFrom, address indexed _userTo, address gateway)` *(live, 709 logs / 50k blk on L1GatewayRouter)* | GatewayRouter |
| `0x812ca95fe4492a9e2d1f2723c2c40c03a60a27b059581ae20ac4e4d73bfba354` | `GatewaySet(address indexed l1Token, address indexed gateway)` | GatewayRouter |
| `0x3a8f8eb961383a94d41d193e16a3af73eaddfd5764a4c640257323a1603ac331` | `DefaultGatewayUpdated(address newDefaultGateway)` | GatewayRouter |
| `0x0dd664a155dd89526bb019e22b00291bb7ca9d07ba3ec4a1a76b410da9797ceb` | `TokenSet(address indexed l1Address, address indexed l2Address)` | L1CustomGateway |
| `0x2b986d32a0536b7e19baa48ab949fec7b903b7fad7730820b20632d100cc3a68` | `TxToL1(address indexed _from, address indexed _to, uint256 indexed _id, bytes _data)` *(live: 3 on the Arbitrum One L2ERC20Gateway in the window of §11, one per `WithdrawalInitiated`)* | L2 gateways |

`DepositInitiated.sequenceNumber` / `TxToL2.seqNum` / `WithdrawalInitiated.l2ToL1Id` are the cross-chain keys; `WithdrawalFinalized.exitNum` links an L1 payout back to its L2 `WithdrawalInitiated`. `TxToL1._id` equals `WithdrawalInitiated.l2ToL1Id` and `L2ToL1Tx.position`.

The DAI, GRT, ARB and wstETH gateways (§3.4) emit the same `DepositInitiated` / `TxToL2` / `WithdrawalFinalized` topics, but DAI and GRT keep the tokens in a **separate escrow** (the ERC-20 `Transfer` goes to the escrow, not to the gateway), ARB is **burned** on deposit (`Transfer` to `0x0000000000000000000000000000000000000000`) and minted on withdrawal, and wstETH stays in its gateway.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Selectors recomputed locally on 2026-06-09; each marked *(impl)* was confirmed **present** in the live implementation bytecode on Ethereum.

### 2.1 Inbox (deposit / send-message entry)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x439370b1` | `depositEth()` | *(impl)* ETH deposit, value-carrying; mints ETH to `msg.sender` on L2 (aliased only when the caller is a contract). |
| `0x0f4d14e9` | `depositEth(uint256)` | *(impl)* legacy arg form. |
| `0x679b6ded` | `createRetryableTicket(address to, uint256 l2CallValue, uint256 maxSubmissionCost, address excessFeeRefundAddress, address callValueRefundAddress, uint256 gasLimit, uint256 maxFeePerGas, bytes data)` | *(impl)* the canonical 8-arg retryable creator. |
| `0x6e6e8a6a` | `unsafeCreateRetryableTicket(address,uint256,uint256,address,address,uint256,uint256,bytes)` | *(impl)* skips the L2-callvalue check. |
| `0xb75436bb` | `sendL2Message(bytes)` | *(impl)* raw L2 message. |
| `0x8a631aa6` | `sendContractTransaction(uint256,uint256,address,uint256,bytes)` | *(impl)* |
| `0x5075788b` | `sendUnsignedTransaction(uint256,uint256,uint256,address,uint256,bytes)` | *(impl)* |
| `0xa66b327d` | `calculateRetryableSubmissionFee(uint256,uint256)` → `uint256` | *(impl)* view. |
| `0xe78cea92` | `bridge()` → `address` | *(impl)* the owning Bridge. |
| `0xee35f327` | `sequencerInbox()` → `address` | the paired SequencerInbox. |

> The 10-arg `createRetryableTicket(address,uint256,uint256,address,address,uint256,uint256,uint256,uint256,bytes)` (`0xc5bc9eca`) and 10-arg `unsafeCreateRetryableTicket(address,uint256,uint256,address,address,uint256,uint256,uint256,uint256,bytes)` (`0xfb4efa27`) are **absent** from the current Inbox impl (`0x7C058ad1D0Ee415f7e7f30e62DB1BCf568470a10`) — confirmed by bytecode scan. Index the 8-arg forms.

### 2.2 Bridge (message ledger / call dispatcher)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8db5993b` | `enqueueDelayedMessage(uint8 kind, address sender, bytes32 messageDataHash)` → `uint256` | *(impl)* delayed-inbox → Bridge; emits `MessageDelivered`. payable. |
| `0x9e5d4c49` | `executeCall(address to, uint256 value, bytes data)` → `(bool,bytes)` | *(impl)* Outbox→Bridge L2→L1 call; emits `BridgeCallTriggered`. |
| `0xcee3d728` | `setOutbox(address,bool)` | *(impl)* admin; emits `OutboxToggle`. |
| `0x47fb24c5` | `setDelayedInbox(address,bool)` | *(impl)* admin; emits `InboxToggle`. |
| `0x4f61f850` | `setSequencerInbox(address)` | admin; emits `SequencerInboxUpdated`. |
| `0xab5d8943` | `activeOutbox()` → `address` | *(impl)* the currently-executing Outbox (0 outside a withdrawal). |
| `0xcb23bcb5` | `rollup()` → `address` | *(impl)* **returns the LIVE rollup** (`0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0` on One) — use this, never the docs. |
| `0xeca067ad` | `delayedMessageCount()` → `uint256` | total delayed messages. |
| `0x0084120c` | `sequencerMessageCount()` → `uint256` | total sequencer batches. |

### 2.3 Outbox (L2→L1 finalization)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x08635a95` | `executeTransaction(bytes32[] proof, uint256 index, address l2Sender, address to, uint256 l2Block, uint256 l1Block, uint256 l2Timestamp, uint256 value, bytes data)` | *(impl)* spend a withdrawal; emits `OutBoxTransactionExecuted` + `BridgeCallTriggered`. |
| `0x288e5b10` | `executeTransactionSimulation(uint256,address,address,uint256,uint256,uint256,uint256,bytes)` | *(impl)* dry-run. |
| `0x5a129efe` | `isSpent(uint256 index)` → `bool` | *(impl)* has this withdrawal been claimed. |
| `0xa04cee60` | `updateSendRoot(bytes32 root, bytes32 l2BlockHash)` | *(impl)* Rollup→Outbox; emits `SendRootUpdated`. |
| `0xae6dead7` | `roots(bytes32)` → `bytes32` | *(impl)* registered output roots. |
| `0xe78cea92` | `bridge()` → `address` | *(impl)* |
| `0x9c5cfe0b` | `executeTransaction(uint256 batchNum, bytes32[] proof, uint256 index, address l2Sender, address destAddr, uint256 l2Block, uint256 l1Block, uint256 l2Timestamp, uint256 amount, bytes calldataForL1)` | **Classic Outboxes only** (§3.4): present in both classic implementations (`0x360861b7b245c968128F0a53d281aDb1Df760711`, `0x263a68002876E307804168795519da0B32CC62fE`), and the Nitro `0x08635a95` is absent there. |

### 2.4 SequencerInbox (batch poster)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe0bc9729` | `addSequencerL2Batch(uint256,bytes,uint256,address,uint256,uint256)` | *(impl)* batch via calldata. |
| `0x8f111f3c` | `addSequencerL2BatchFromOrigin(uint256,bytes,uint256,address,uint256,uint256)` | *(impl)* batch from EOA (cheaper). |
| `0xf1981578` | `forceInclusion(uint256,uint8,uint64[2],uint256,address,bytes32)` | *(impl)* censorship escape hatch (after delay). |
| `0xd1ce8da8` | `setValidKeyset(bytes)` | *(impl)* DAS keyset; emits `SetValidKeyset`. |
| `0x84420860` | `invalidateKeysetHash(bytes32)` | *(impl)* emits `InvalidateKeyset`. |
| `0x06f13056` | `batchCount()` → `uint256` | *(impl)* |

### 2.5 GatewayRouter (L1 & L2 — same selectors)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd2ce7d65` | `outboundTransfer(address token, address to, uint256 amount, uint256 maxGas, uint256 gasPriceBid, bytes data)` → `bytes` | core bridge call (routes to the token's gateway). |
| `0x4fb1a07b` | `outboundTransferCustomRefund(address,address,address,uint256,uint256,uint256,bytes)` → `bytes` | L1-only; custom excess-fee refund addr. |
| `0x2e567b36` | `finalizeInboundTransfer(address,address,address,uint256,bytes)` | incoming finalize (counterpart-only). |
| `0xbda009fe` | `getGateway(address token)` → `address` | which gateway serves a token. |
| `0xa7e28d48` | `calculateL2TokenAddress(address)` → `address` | deterministic L2 token address. |
| `0x2d67b72d` | `setGateway(address,uint256,uint256,uint256,address)` → `uint256` | token issuer self-registers its gateway. |
| `0x5625a952` | `setDefaultGateway(address,uint256,uint256,uint256)` → `uint256` | admin. |
| `0x03295802` | `defaultGateway()` → `address` | = the standard ERC20 gateway. |
| `0x7b3a3c8b` | `outboundTransfer(address _l1Token, address _to, uint256 _amount, bytes _data)` → `bytes` | **L2 only**: the 4-argument withdrawal entry of the L2GatewayRouter and L2 gateways (present in all four Arbitrum One L2 implementations of §5); emits `TransferRouted`, `TxToL1`, `WithdrawalInitiated`. |

### 2.6 Token gateways (ERC20 / Custom / Weth)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd2ce7d65` | `outboundTransfer(address,address,uint256,uint256,uint256,bytes)` → `bytes` | shared with router. |
| `0x2e567b36` | `finalizeInboundTransfer(address,address,address,uint256,bytes)` | |
| `0xa7e28d48` | `calculateL2TokenAddress(address)` → `address` | |
| `0xca346d4a` | `registerTokenToL2(address,uint256,uint256,uint256,address)` → `uint256` | L1CustomGateway: map an L1 token to its L2 custom token. |
| `0x1d3a689f` | `forceRegisterTokenToL2(address[],address[],uint256,uint256,uint256)` → `uint256` | admin force-map. |
| `0x2db09c1c` | `counterpartGateway()` → `address` | the paired gateway on the other layer. |
| `0xf887ea40` | `router()` → `address` | the owning GatewayRouter. |

### 2.7 ArbSys precompile (`0x0000000000000000000000000000000000000064`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x928c169a` | `sendTxToL1(address destination, bytes data)` → `uint256` | **the withdrawal entrypoint**; emits `L2ToL1Tx`. payable. |
| `0x25e16063` | `withdrawEth(address destination)` → `uint256` | ETH withdrawal shortcut. payable. |
| `0xa3b1b31d` | `arbBlockNumber()` → `uint256` | L2 block number. |
| `0x2b407a82` | `arbBlockHash(uint256)` → `bytes32` | |
| `0xd127f54a` | `arbChainID()` → `uint256` | 42161 (One) / 42170 (Nova). |
| `0x051038f2` | `arbOSVersion()` → `uint256` | ArbOS version. |
| `0x7aeecd2a` | `sendMerkleTreeState()` → `(uint256,bytes32,bytes32[])` | withdrawal tree state. |
| `0xd74523b3` | `myCallersAddressWithoutAliasing()` → `address` | un-alias the caller. |

### 2.8 ArbRetryableTx precompile (`0x000000000000000000000000000000000000006E`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xeda1122c` | `redeem(bytes32 ticketId)` → `bytes32` | manually redeem a retryable; emits `RedeemScheduled`. |
| `0xf0b21a41` | `keepalive(bytes32)` → `uint256` | extend lifetime; emits `LifetimeExtended`. |
| `0xc4d252f5` | `cancel(bytes32)` | emits `Canceled`. |
| `0x9f1025c6` | `getTimeout(bytes32)` → `uint256` | |
| `0xba20dda4` | `getBeneficiary(bytes32)` → `address` | |
| `0x81e6e083` | `getLifetime()` → `uint256` | global retryable lifetime (≈ 7 days). |

---

## 3. Addresses — Ethereum mainnet (chain ID 1) · Arbitrum One L1 contracts

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Wiring confirmed: `Inbox.bridge()` = `0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a`, `Bridge.rollup()` = `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0`.

### 3.1 Core / messaging (One)

| Role | Address | One-liner |
|------|---------|-----------|
| **Inbox** (proxy) | `0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f` | L1→L2 deposit/retryable entry; emits `InboxMessageDelivered`. |
| **Bridge** (proxy) | `0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a` | message ledger; emits `MessageDelivered`. The hub `eth_call` `rollup()`. |
| **Outbox** (proxy) | `0x0B9857ae2D4A3DBe74ffE1d7DF045bb7F96E4840` | L2→L1 finalization; emits `OutBoxTransactionExecuted`/`SendRootUpdated`. |
| **SequencerInbox** (proxy) | `0x1c479675ad559DC151F6Ec7ed3FbF8ceE79582B6` | batch poster; emits `SequencerBatchDelivered`. |
| **Rollup — LIVE (BoLD)** (double-proxy) | `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0` | **current** rollup; emits `AssertionCreated`/`AssertionConfirmed`. Admin-logic impl `0x7FC126FF51183a78C5E0437467f325f661D8Df17`, user-logic impl `0x6490bA0a60Cc7d3a59C9eeE135D9eeD24553a60d`. |
| Rollup — legacy/classic (deprecated) | `0x5eF0D09d1E6204141B4d37530808eD19f60FBa35` | the **old** classic-Nitro rollup. `bridge()` still returns `0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a` but `Bridge.rollup()` no longer points here — **do not index** (silent, ~0 logs). |

### 3.2 Token bridge (One)

| Role | Address | One-liner |
|------|---------|-----------|
| **L1GatewayRouter** (proxy) | `0x72Ce9c846789fdB6fC1f34aC4AD25Dd9ef7031ef` | routes tokens to gateways; emits `TransferRouted`/`GatewaySet`. |
| **L1ERC20Gateway** (proxy) | `0xa3A7B6F88361F48403514059F1F16C8E78d60EeC` | standard ERC-20 escrow; emits `DepositInitiated`/`WithdrawalFinalized`. |
| **L1CustomGateway** (proxy) | `0xcEe284F754E854890e311e3280b767F80797180d` | custom-token (arbitrary L2 impl) bridge; emits `TokenSet`. |
| **L1WethGateway** (proxy) | `0xd92023E9d9911199a6711321D1277285e6d4e2db` | unwraps/rewraps WETH across layers. |

### 3.3 Live implementations & admins (One, read 2026-06-09 from EIP-1967 slots)

| Proxy | Impl slot value | Admin slot value |
|-------|-----------------|------------------|
| Inbox | `0x7c058ad1d0ee415f7e7f30e62db1bcf568470a10` | `0x554723262467f125ac9e1cdfa9ce15cc53822dbd` |
| Bridge | `0xfe4749061fb052c354aac65b9fb0ccd7e20d2418` | `0x554723262467f125ac9e1cdfa9ce15cc53822dbd` |
| Outbox | `0x3fff9bdc3ce99d3d587b0d06aa7c4a10075193b4` | `0x554723262467f125ac9e1cdfa9ce15cc53822dbd` |
| SequencerInbox | `0x98a58adab0f8a66a1bf4544d804bc0475dff32c7` | `0x554723262467f125ac9e1cdfa9ce15cc53822dbd` |
| Rollup (BoLD) | admin-logic `0x7fc126ff51183a78c5e0437467f325f661d8df17` · user-logic `0x6490ba0a60cc7d3a59c9eee135d9eed24553a60d` | `0x3fffbadaf827559da092217e474760e2b2c3cedd` |
| L1GatewayRouter | `0x52595021fa01b3e14ec6c88953afc8e35dff423c` | `0x9ad46fac0cf7f790e5be05a0f15223935a0c0ada` |
| L1ERC20Gateway | `0xb4299a1f5f26ff6a98b7ba35572290c359fde900` | `0x9ad46fac0cf7f790e5be05a0f15223935a0c0ada` |
| L1CustomGateway | `0xc8d26ab9e132c79140b3376a0ac7932e4680aa45` | `0x9ad46fac0cf7f790e5be05a0f15223935a0c0ada` |
| L1WethGateway | `0x4b8e9b3f253e68837bf719997b1eeb9e8f1960e2` | `0x9ad46fac0cf7f790e5be05a0f15223935a0c0ada` |

`0x554723262467F125Ac9e1cDFa9Ce15cc53822dbD` is the **core ProxyAdmin** (One); `0x9aD46fac0Cf7f790E5be05A0F15223935A0c0aDa` is the **token-bridge ProxyAdmin** (One); both ultimately answer to the Arbitrum DAO `UpgradeExecutor`. The Rollup uses the double-logic admin/user proxy with its own admin `0x3ffFbAdAF827559da092217e474760E2b2c3CeDd`.

### 3.4 Classic Outboxes and token-specific gateways (One)

The One Bridge allows three outboxes (`allowedOutboxList(0..2)` read live 2026-09-29): the Nitro Outbox and two Classic Outboxes. The L1GatewayRouter maps some tokens to their own gateways (`getGateway(token)` read live). All addresses below have code on Ethereum and none on the other seven chains.

| Role | Address | One-liner |
|------|---------|-----------|
| **Classic Outbox 1** (proxy) | `0x760723CD2e632826c38Fef8CD438A4CC7E7E1A40` | pre-Nitro withdrawals, still paying: 4 `OutBoxTransactionExecuted` in the window of §11. `bridge()` = the One Bridge. Impl `0x360861b7b245c968128f0a53d281adb1df760711`, admin the core ProxyAdmin. Listed as "Classic Outbox" in the Arbitrum docs. |
| **Classic Outbox 2** (proxy) | `0x667e23ABd27E623c11d4CC00ca3EC4d0bD63337a` | same role; 0 in the window. Impl `0x263a68002876e307804168795519da0b32cc62fe`, admin the core ProxyAdmin. |
| **L1 DAI gateway** (MakerDAO, not a proxy) | `0xD3B5b60020504bc3489D6949d545893982BA3011` | router gateway of DAI `0x6B175474E89094C44Da98b954EedeAC495271d0F`; emits `DepositInitiated`/`TxToL2`/`WithdrawalFinalized` (3 deposits in the window). MakerDAO chainlog `ARBITRUM_DAI_BRIDGE`. L2 counterpart `0x467194771dAe2967Aef3ECbEDD3Bf9a310C76C65`. |
| **L1 DAI escrow** (not a proxy) | `0xA10c7CE4b876998858b1a9E12b10092229539400` | holds the bridged DAI: the deposit `Transfer` goes here, not to the gateway (`l1Escrow()` of the gateway). MakerDAO chainlog `ARBITRUM_ESCROW`. |
| **L1 GRT gateway** (The Graph, proxy) | `0x01cDC91B0A9bA741903aA3699BF4CE31d6C5cC06` | router gateway of GRT `0xc944E90C64B2c07662A292be6244BDf05Cda44a7` (3 deposits in the window). Impl `0xd41ca6a1d034d178c196dfa916f22f7d1a1b8222`, admin GraphProxyAdmin `0xF3B000a6749259539aF4E49f24EEc74Ea0e71430`. L2 counterpart `0x65E1a5e8946e7E87d9774f5288f41c30a99fD302`. The Graph `addresses.json` `L1GraphTokenGateway`. |
| **GRT escrow** (The Graph `BridgeEscrow`, proxy) | `0x36aFF7001294daE4C2ED4fDEfC478a00De77F090` | holds the bridged GRT (`escrow()` of the gateway). Impl `0xbcd54513aa593646d72aea31406c633c235ad6ea`, admin GraphProxyAdmin. |
| **L1 ARB gateway** (reverse custom gateway, proxy) | `0xbbcE8aA77782F13D4202a230d978F361B011dB27` | router gateway of the L1 ARB token `0xB50721BCf8d664c30412Cfbc6cf7a15145234ad1`: **burns** L1 ARB on deposit, mints on withdrawal (no escrow). 0 deposits in the window; 10 in Ethereum blocks 26,060,000–26,075,812. Impl `0x4e8c24617c4592895d52ac6df29d9647e9d01bb5`, admin the DAO L1 ProxyAdmin `0x5613AF0474EB9c528A34701A5b1662E3C8FA0678`, `owner()` the L1 UpgradeExecutor `0x3ffFbAdAF827559da092217e474760E2b2c3CeDd`. L2 counterpart `0xCaD7828a19b363A2B44717AFB1786B5196974D8E`. Arbitrum DAO deployment list "$ARB Gateway (L1)". |
| **Lido wstETH gateway** (`L1ERC20TokenGateway`, proxy) | `0x0F25c1DC2a9922304f2eac71DCa9B07E310e8E5a` | router gateway of wstETH `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0`; the gateway itself holds the wstETH. 0 deposits in the window; 8 in Ethereum blocks 26,000,000–26,075,812. Impl `0xc4E3ff0b5B106f88Fc64c43031BE8b076ee9F21C`, admin the Lido DAO Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c`. L2 counterpart `0x07D4692291B9E30E326fd31706f686f83f331B82`. Lido deployed-contracts list. |

Other tokens also route to their own gateways: for example LPT `0x58b6A8A3302369DAEc383334672404Ee733aB239` → `0x6142f1C8bBF02E6A6bd074E8d564c9A5420a0676` (read live, not researched further), while USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` routes to the generic L1CustomGateway. Enumerate the rest from `GatewaySet` history or with `getGateway(token)`.

---

## 4. Addresses — Ethereum mainnet (chain ID 1) · Arbitrum **Nova** L1 contracts

Same chain (Ethereum), a **separate rollup** (Nova, L2 chain 42170 — outside the seven, recorded here as a finding). All verified via `eth_getCode` non-empty on 2026-06-09. Nova is an AnyTrust chain (DAS-backed), so `SetValidKeyset`/`InvalidateKeyset` are common on its SequencerInbox.

| Role | Address |
|------|---------|
| Inbox | `0xc4448b71118c9071Bcb9734A0EAc55D18A153949` |
| Bridge | `0xC1Ebd02f738644983b6C4B2d440b8e77DdE276Bd` |
| Outbox | `0xD4B80C3D7240325D18E645B49e6535A3Bf95cc58` |
| SequencerInbox | `0x211E1c4c7f1bF5351Ac850Ed10FD68CFfCF6c21b` |
| Rollup (LIVE) | `0xe7e8ccc7c381809bdc4b213ce44016300707b7bd` (= `Bridge.rollup()`) |
| Rollup (legacy proxy) | `0xFb209827c58283535b744575e11953DCC4bEAD88` (the original Nova rollup proxy; superseded) |
| L1GatewayRouter | `0xC840838Bc438d73C16c2f8b22D2Ce3669963cD48` |
| L1ERC20Gateway | `0xB2535b988dcE19f9D71dfB22dB6da744aCac21bf` |
| L1CustomGateway | `0x23122da8C581AA7E0d07A36Ff1f16F799650232f` |
| L1WethGateway | `0xE4E2121b479017955Be0b175305B35f312330BaE` |

---

## 5. Addresses — Arbitrum One L2 (chain ID 42161)

All verified via `eth_getCode` non-empty on `https://arbitrum-one-rpc.publicnode.com` on 2026-06-09. Precompiles return the ArbOS marker byte `0xfe` (4-char code = `0xfe`) — they are **not** EVM contracts; they have no impl slot.

| Role | Address | One-liner |
|------|---------|-----------|
| **ArbSys** (precompile) | `0x0000000000000000000000000000000000000064` | withdrawal origin; emits `L2ToL1Tx`. |
| **ArbRetryableTx** (precompile) | `0x000000000000000000000000000000000000006E` | retryable lifecycle. |
| NodeInterface (precompile, read-only) | `0x00000000000000000000000000000000000000C8` | gas/outbox-proof estimation (not callable on-chain by contracts). |
| **L2GatewayRouter** (proxy) | `0x5288c571Fd7aD117beA99bF60FE0846C4E84F933` | L2 routing mirror; impl `0xe80eb0238029333e368e0bDDB7acDf1b9cb28278`, admin `0xd570aCE65C43af47101fC6250FD6fC63D1c22a86`. |
| **L2ERC20Gateway** (proxy) | `0x09e9222E96E7B4AE2a407B98d48e330053351EEe` | L2 escrow mirror; emits `DepositFinalized`/`WithdrawalInitiated`; impl `0x1DCf7D03574fbC7C205F41f2e116eE094a652e93`, admin `0xd570aCE65C43af47101fC6250FD6fC63D1c22a86`. |
| **L2CustomGateway** (proxy) | `0x096760F208390250649E3e8763348E783AEF5562` | impl `0x190274fEa8f30e3f48CE43aDCBd9a74110118284`. |
| **L2WethGateway** (proxy) | `0x6c411aD3E74De3E7Bd422b94A27770f5B86C623B` | impl `0x806421D09cDb253aa9d128a658e60c0B95eFFA01`. |

`0xd570ace65c43af47101fc6250fd6fc63d1c22a86` is the L2 token-bridge ProxyAdmin (shared by all L2 gateways).

---

## 6. Addresses — the other requested chains (NO Arbitrum One / Nova bridge here)

`eth_getCode` returns `0x` for **every** Arbitrum bridge address (Inbox/Bridge/Rollup/L1GatewayRouter and the L2 set) on each of these — verified 2026-06-09, and for Robinhood Chain on 2026-09-29. The canonical One / Nova bridge has no presence on:

| Chain | ID | RPC checked | Result |
|---|---|---|---|
| Base | 8453 | base-rpc.publicnode.com | `0x` for Inbox, Bridge, L1GatewayRouter, L2GatewayRouter |
| BNB Smart Chain | 56 | bsc-rpc.publicnode.com | `0x` for Inbox, Bridge, L1GatewayRouter |
| Avalanche C-Chain | 43114 | avalanche-c-chain-rpc.publicnode.com | `0x` for Inbox, Bridge, L1GatewayRouter |
| Optimism | 10 | optimism-rpc.publicnode.com | `0x` for Inbox, Bridge, L1GatewayRouter |
| Polygon PoS | 137 | polygon-bor-rpc.publicnode.com | `0x` for Inbox, Bridge, L1GatewayRouter |
| Robinhood Chain | 4663 | rpc.mainnet.chain.robinhood.com | `0x` for the One Inbox, Bridge, Rollup, L1GatewayRouter, L2GatewayRouter and L2ERC20Gateway; Robinhood Chain runs its own Nitro stack (`orbit.md` §6) |

This is expected: the Arbitrum canonical bridge is **strictly Ethereum-L1-anchored** — its only counterparties are Arbitrum One (42161) and Arbitrum Nova (42170). The L1 side lives **only** on Ethereum; the L2 side lives **only** on the respective Orbit chain. There is no One / Nova deployment on any other settlement layer. Other Orbit chains (Robinhood Chain, the Orbit L2s on Ethereum, the Orbit L3s on Base and on Arbitrum One) use the same contracts at their own addresses: `orbit.md`.

---

## 7. Cross-chain summary

| Chain | ID | Inbox | Bridge | Outbox | SeqInbox | Rollup (live) | L1 Router | L1 ERC20 GW | L2 Router | L2 ERC20 GW | ArbSys |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Ethereum (One L1)** | 1 | `0x4Dbd4fc535Ac27206064B68FfCf827b0A60BAB3f` | `0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a` | `0x0B9857ae2D4A3DBe74ffE1d7DF045bb7F96E4840` | `0x1c479675ad559DC151F6Ec7ed3FbF8ceE79582B6` | `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0` | `0x72Ce9c846789fdB6fC1f34aC4AD25Dd9ef7031ef` | `0xa3A7B6F88361F48403514059F1F16C8E78d60EeC` | — | — | — |
| **Ethereum (Nova L1)** | 1 | `0xc4448b71118c9071Bcb9734A0EAc55D18A153949` | `0xC1Ebd02f738644983b6C4B2d440b8e77DdE276Bd` | `0xD4B80C3D7240325D18E645B49e6535A3Bf95cc58` | `0x211E1c4c7f1bF5351Ac850Ed10FD68CFfCF6c21b` | `0xE7E8cCC7c381809BDC4b213CE44016300707B7Bd` | `0xC840838Bc438d73C16c2f8b22D2Ce3669963cD48` | `0xB2535b988dcE19f9D71dfB22dB6da744aCac21bf` | — | — | — |
| **Arbitrum One (L2)** | 42161 | — | — | — | — | — | — | — | `0x5288c571Fd7aD117beA99bF60FE0846C4E84F933` | `0x09e9222E96E7B4AE2a407B98d48e330053351EEe` | `0x0000000000000000000000000000000000000064` |
| Base | 8453 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| BNB | 56 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Avalanche | 43114 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Optimism | 10 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Polygon | 137 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Robinhood Chain | 4663 | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ (own ArbSys, see `orbit.md`) |

**Robinhood Chain (4663)** has no One / Nova contract, but it is itself an Orbit L2 on the same Nitro code: its Ethereum-side Bridge is `0xDf8755334ce7A73cCF6b581C02eA649AE3E864b3` (Inbox `0x1A07cc4BD17E0118BdB54D70990D2158AbAD7a2D`, Outbox `0xf0ce991ea4A0d2400A4AB49b20ae333f6Dce3DE9`), and its L2 side (ArbSys `0x0000000000000000000000000000000000000064`, L2GatewayRouter `0x1E324B9316138CA9a73F960213621AD1aaf01B89`) is on 4663. Full rows: `orbit.md` §3.1 and §6.

**Counterparty chains outside the eight:** Arbitrum One L2 (42161 — *in* the eight) and **Arbitrum Nova L2 (42170 — outside)**. Both anchor their L1 contracts on Ethereum. No vanity addresses — every contract is a plain deterministic deploy, distinct per rollup.

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Inbox / Bridge / Outbox / SequencerInbox | **EIP-1967 Transparent proxy** | impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` set; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` set (One core = `0x554723262467F125Ac9e1cDFa9Ce15cc53822dbD`) | core ProxyAdmin → DAO UpgradeExecutor; watch `Upgraded(address)` topic0 `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. |
| L1/L2 GatewayRouter, ERC20/Custom/Weth gateways | **EIP-1967 Transparent proxy** | impl slot set; L1 admin `0x9aD46fac0Cf7f790E5be05A0F15223935A0c0aDa`, L2 admin `0xd570aCE65C43af47101fC6250FD6fC63D1c22a86` | token-bridge ProxyAdmin → UpgradeExecutor; same `Upgraded` topic. |
| **Rollup (BoLD)** `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0` | **Double-logic proxy** (admin-logic + user-logic) | EIP-1967 impl slot = **admin-logic** `0x7FC126FF51183a78C5E0437467f325f661D8Df17`; a *secondary* slot `0x2b1dbce74324248c222f0ec2d5ed7bd323cfc425b336f0253c5ccfda7265546d` = **user-logic** `0x6490bA0a60Cc7d3a59C9eeE135D9eeD24553a60d`; admin slot `0x3ffFbAdAF827559da092217e474760E2b2c3CeDd` | RollupAdminLogic via UpgradeExecutor; emits `Upgraded`. |
| Classic Outbox 1 / 2 | **EIP-1967 Transparent proxy** | impl `0x360861b7b245c968128f0a53d281adb1df760711` / `0x263a68002876e307804168795519da0b32cc62fe`; admin slot = the core ProxyAdmin `0x554723262467F125Ac9e1cDFa9Ce15cc53822dbD` | core ProxyAdmin → DAO UpgradeExecutor. |
| L1 GRT gateway, GRT escrow | **EIP-1967 proxy (The Graph `GraphProxy`)** | impl `0xd41ca6a1d034d178c196dfa916f22f7d1a1b8222` / `0xbcd54513aa593646d72aea31406c633c235ad6ea`; admin slot = GraphProxyAdmin `0xF3B000a6749259539aF4E49f24EEc74Ea0e71430` | The Graph governance. |
| L1 ARB gateway | **EIP-1967 Transparent proxy** | impl `0x4e8c24617c4592895d52ac6df29d9647e9d01bb5`; admin slot = DAO L1 ProxyAdmin `0x5613AF0474EB9c528A34701A5b1662E3C8FA0678` | ProxyAdmin `owner()` = L1 UpgradeExecutor `0x3ffFbAdAF827559da092217e474760E2b2c3CeDd` (read live). |
| Lido wstETH gateway | **EIP-1967 proxy (Lido `OssifiableProxy`)** | impl `0xc4E3ff0b5B106f88Fc64c43031BE8b076ee9F21C`; admin slot = Lido DAO Aragon Agent `0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c` | Lido DAO. |
| L1 DAI gateway, DAI escrow | **Not proxies** | EIP-1967 impl and admin slots read `0x0` (8,283 B and 1,574 B of plain bytecode) | MakerDAO `wards` (not read). |
| ArbSys / ArbRetryableTx / NodeInterface | **Not proxies — ArbOS precompiles** | `eth_getCode` returns the 1-byte marker `0xfe`; **no impl slot** (slot read returns `0x0`). Logic lives in the node binary; upgraded via ArbOS version bumps, not on-chain `Upgraded`. | ArbOS upgrade (governed). |

**Reading the live impl:** `eth_getStorageAt(proxy, 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc)`. For the Rollup, also read the secondary slot `0x2b1dbce74324248c222f0ec2d5ed7bd323cfc425b336f0253c5ccfda7265546d` to get the user-facing logic. **Never hard-code an impl** — read the slot live; gateway/inbox impls rotate on upgrades.

---

## 9. Detection invariants & gotchas

1. **The live Arbitrum One Rollup is `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0`, not `0x5eF0D09d1E6204141B4d37530808eD19f60FBa35`.** The famous `0x5eF0D09d1E6204141B4d37530808eD19f60FBa35` is the original classic-Nitro rollup, now **disconnected** (`Bridge.rollup()` returns `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0`). Index the address returned by `Bridge.rollup()`, not a docs-pinned literal.
2. **Arbitrum One uses BoLD — `AssertionCreated`/`AssertionConfirmed` (`0x901c3aee23cf4478825462caaab375c606ab83516060388344f0650340753630`/`0xfc42829b29c259a7370ab56c8f69fce23b5f351a9ce151da453281993ec0090c`), NOT `NodeCreated`/`NodeConfirmed`.** The legacy node events never fire on the live rollup. Withdrawal-finality monitoring keys on `AssertionConfirmed` → `SendRootUpdated`.
3. **`MessageDelivered.sender` is always the *alias* of the L1 caller, not the raw L1 address.** Alias = `L1addr + 0x1111000000000000000000000000000000001111` (mod 2^160). The Inbox applies it to an EOA as well as to a contract (`nitro-contracts` `Inbox._deliverToBridge`; sample `0x18100c3e54f24ccb7437eb58abfa626a95a9c08e6712177c4c9448099c45b40b` on Robinhood Chain's Inbox: EOA `0xf6017e7195dfd4eae02c4a0ed54146b282294ef3` shows as `0x07127e7195dfd4eae02c4a0ed54146b282296004`). Un-alias before you attribute any deposit. Only the L2 recipient inside the `depositEth` data stays raw for an EOA.
4. **A deposit and its L2 effect are different transactions on different chains.** `DepositInitiated`/`MessageDelivered`/`InboxMessageDelivered` on L1 → retryable `TicketCreated`/`RedeemScheduled`/`DepositFinalized` on L2. Link by `sequenceNumber` (= `MessageDelivered.messageIndex` / `TxToL2.seqNum`), never by `tx.from`.
5. **A withdrawal spans days and three events.** `L2ToL1Tx`/`WithdrawalInitiated` (L2, instant) → `AssertionConfirmed` + `SendRootUpdated` (L1, after assertion) → `OutBoxTransactionExecuted`/`WithdrawalFinalized` (L1, after the ~6.4-day window, **user-initiated**). The L1 payout will not appear until someone calls `Outbox.executeTransaction`. Key on `L2ToL1Tx.position` / `WithdrawalFinalized.exitNum`.
6. **`SequencerBatchDelivered` topic0 is `0x7394f4a19a13c7b92b5bb71033245305946ef78452f7b4986ac1390b5df4ebd7` (has the `delayedAcc` field), not the older `0x12331e99e77abfe6c3fda90920bb3a50e7d719bbd49c62e4341be6a086290996`.** The legacy 6-field variant does not appear in current logs.
7. **`L2ToL1Tx` topic0 is `0x3e7aafa77dbf186b7fd488006beff893744caa3c4f6f299e8a709fa2087374fc`** (Nitro). The pre-Nitro `L2ToL1Transaction` is `0x5baaa87db386365b5c161be377bc3d8e317e8d98d71a3ca7ed7d555340c8f767` (10 arguments, still declared as deprecated in ArbSys; 0 logs in the window of §11). The values `0x60d31e9c307cb3cf20a3a452ca6019c46058a1b278f098b85c648543bb4a4902` and `0x47ee703badfed63a907c70867d6cedee0757d28f943ceb03353f090945195454` are mis-derivations that no contract emits.
8. **`OwnerFunctionCalled(uint256)` topic0 `0xea8787f128d10b2cc0317b0c3960f9ad447f7f6c1ed189db1083ccffd20f456e` is emitted by SequencerInbox, Bridge AND Rollup.** Disambiguate the admin action by the emitting address (and the `id` param).
9. **`InboxMessageDelivered` is emitted by both the Inbox and the SequencerInbox** (the latter once per batch-cost report, which is also a `MessageDelivered` of kind 13: 364 of One's 524 `MessageDelivered` in the window of §11). Filter by emitter, or keep kinds 9 and 12 only, to count deposits.
10. **`InboxMessageDeliveredFromOrigin` (`0xab532385be8f1005a4b6ba8fa20a2245facb346134ac739fe9a5198dc1580b9c`) carries NO payload in the log** — the message body is in the transaction calldata. If you need the body, fetch the tx input; the event only gives `messageNum`.
11. **Gateways escrow on L1, mint on L2.** A standard ERC-20 deposit locks tokens in `L1ERC20Gateway` and mints a bridged token on L2 at `calculateL2TokenAddress(l1Token)`. `L1CustomGateway` tokens have arbitrary L2 implementations (registered via `TokenSet`/`registerTokenToL2`) — do not assume the deterministic address for custom tokens.
12. **Two ProxyAdmins per rollup.** Core (Inbox/Bridge/Outbox/SeqInbox) share one admin (One: `0x554723262467F125Ac9e1cDFa9Ce15cc53822dbD`); the token bridge shares another (L1 `0x9aD46fac0Cf7f790E5be05A0F15223935A0c0aDa`, L2 `0xd570aCE65C43af47101fC6250FD6fC63D1c22a86`). The Rollup has its own. Watching `Upgraded` across all of them catches every bridge upgrade.
13. **Precompiles emit logs under their fixed L2 address.** `ArbSys` logs appear under `0x0000000000000000000000000000000000000064` — but they are sparse (withdrawals are rarer than deposits); widen your scan window before concluding "no activity."
14. **Nova (42170) is a separate rollup that shares the Ethereum L1 settlement layer.** Its L1 contracts (§4) are distinct addresses; do not merge Nova and One metrics. Nova is AnyTrust (DAS), so its SequencerInbox keyset events are frequent and its data-availability model differs.
15. **`createRetryableTicket` on the current Inbox is the 8-arg form (`0x679b6ded`).** The 10-arg variants (`0xc5bc9eca` / `0xfb4efa27`) are absent from the live impl — do not scan for them.
16. **Three outboxes can pay out of the One Bridge.** Besides the Nitro Outbox, the two Classic Outboxes (§3.4) still execute old withdrawals (4 in the window of §11). Their `OutBoxTransactionExecuted` has the same topic0, but the third topic is the classic `outboxEntryIndex`, not zero, and their entry point is the classic `executeTransaction` (`0x9c5cfe0b`). Key payouts on `BridgeCallTriggered` at the Bridge, whose `outbox` topic names the paying outbox; read `allowedOutboxList(i)` for the full set.
17. **The token leg of a custom gateway may not touch the gateway.** DAI goes to `0xA10c7CE4b876998858b1a9E12b10092229539400` and GRT to `0x36aFF7001294daE4C2ED4fDEfC478a00De77F090` (separate escrows); ARB is burned to `0x0000000000000000000000000000000000000000`; wstETH stays in its gateway. Join the ERC-20 row to `DepositInitiated` on the transaction, token, sender and amount, not on the escrow address (samples: DAI `0x7f6fde936fdfa0888f2cc48418dce4a0e4a2d38c165224c7f7cc762951e8f834`, GRT `0x6849f2a401f40d1d2e2382a03224f50c2e66d9ecb51dfcf5969a0229020a216e`, ARB `0xd5281a977129a18099731327d3622d12656db5e0f2839c74f745a13658a6272c`, wstETH `0xfaff4accbee4c48f6e38affb176266de00697e770e4a8902b113df9cb1d80fc6`).
18. **`TxToL2` alone does not prove a token deposit.** Any contract built on the L1 messenger emits it: in the window `0x48D5354Ee0DBE52099534D7c4b9CC7Fb4f618Bb3` sent a kind-9 message to One with `TxToL2` and no `DepositInitiated`. Its L2 mirror `TxToL1` (§1.8) fires with each token withdrawal.
19. **Robinhood Chain and the other Orbit chains emit every topic of this file from their own addresses.** A topic0 filter on Ethereum without an emitter filter mixes One and Nova with Robinhood Chain and about twenty other Orbit chains; on Arbitrum One the same topics also come from 34 Orbit L3 Bridges (`orbit.md` §9, item 1).

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- Bridge
TOPIC_MESSAGE_DELIVERED         = '\x5e3c1311ea442664e8b1611bfabef659120ea7a0a2cfc0667700bebc69cbffe1'
TOPIC_BRIDGE_CALL_TRIGGERED     = '\x2d9d115ef3e4a606d698913b1eae831a3cdfe20d9a83d48007b0526749c3d466'
TOPIC_INBOX_TOGGLE              = '\x6675ce8882cb71637de5903a193d218cc0544be9c0650cb83e0955f6aa2bf521'
TOPIC_OUTBOX_TOGGLE             = '\x49477e7356dbcb654ab85d7534b50126772d938130d1350e23e2540370c8dffa'
TOPIC_SEQUENCER_INBOX_UPDATED   = '\x8c1e6003ed33ca6748d4ad3dd4ecc949065c89dceb31fdf546a5289202763c6a'
TOPIC_ROLLUP_UPDATED            = '\xae1f5aa15f6ff844896347ceca2a3c24c8d3a27785efdeacd581a0a95172784a'
-- Inbox
TOPIC_INBOX_MESSAGE_DELIVERED   = '\xff64905f73a67fb594e0f940a8075a860db489ad991e032f48c81123eb52d60b'
TOPIC_INBOX_MSG_FROM_ORIGIN     = '\xab532385be8f1005a4b6ba8fa20a2245facb346134ac739fe9a5198dc1580b9c'
-- SequencerInbox
TOPIC_SEQ_BATCH_DELIVERED       = '\x7394f4a19a13c7b92b5bb71033245305946ef78452f7b4986ac1390b5df4ebd7'
TOPIC_SEQ_BATCH_DATA            = '\xfe325ca1efe4c5c1062c981c3ee74b781debe4ea9440306a96d2a55759c66c20'
TOPIC_SET_VALID_KEYSET          = '\xabca9b7986bc22ad0160eb0cb88ae75411eacfba4052af0b457a9335ef655722'
TOPIC_INVALIDATE_KEYSET         = '\x5cb4218b272fd214168ac43e90fb4d05d6c36f0b17ffb4c2dd07c234d744eb2a'
-- Outbox
TOPIC_OUTBOX_TX_EXECUTED        = '\x20af7f3bbfe38132b8900ae295cd9c8d1914be7052d061a511f3f728dab18964'
TOPIC_SEND_ROOT_UPDATED         = '\xb4df3847300f076a369cd76d2314b470a1194d9e8a6bb97f1860aee88a5f6748'
-- Rollup (BoLD)
TOPIC_ASSERTION_CREATED         = '\x901c3aee23cf4478825462caaab375c606ab83516060388344f0650340753630'
TOPIC_ASSERTION_CONFIRMED       = '\xfc42829b29c259a7370ab56c8f69fce23b5f351a9ce151da453281993ec0090c'
TOPIC_ROLLUP_INITIALIZED        = '\xfc1b83c11d99d08a938e0b82a0bd45f822f71ff5abf23f999c93c4533d752464'
TOPIC_ROLLUP_CHALLENGE_STARTED  = '\x6db7dc2f507647d135035469b27aa79cea90582779d084a7821d6cd092cbd873'
TOPIC_USER_STAKE_UPDATED        = '\xd957cf2340073335d256f72a9ef89cf1a43c31143341a6a53575ef33e987beb8'
TOPIC_OWNER_FUNCTION_CALLED     = '\xea8787f128d10b2cc0317b0c3960f9ad447f7f6c1ed189db1083ccffd20f456e'
-- ArbSys / ArbRetryableTx (L2)
TOPIC_L2_TO_L1_TX               = '\x3e7aafa77dbf186b7fd488006beff893744caa3c4f6f299e8a709fa2087374fc'
TOPIC_SEND_MERKLE_UPDATE        = '\xe9e13da364699fb5b0496ff5a0fc70760ad5836e93ba96568a4e42b9914a8b95'
TOPIC_REDEEM_SCHEDULED          = '\x5ccd009502509cf28762c67858994d85b163bb6e451f5e9df7c5e18c9c2e123e'
TOPIC_TICKET_CREATED            = '\x7c793cced5743dc5f531bbe2bfb5a9fa3f40adef29231e6ab165c08a29e3dd89'
TOPIC_RETRYABLE_REDEEMED        = '\x27fc6cca2a0e9eb6f4876c01fc7779b00cdeb7277a770ac2b844db5932449578'
-- Token bridge (gateways / router)
TOPIC_DEPOSIT_INITIATED         = '\xb8910b9960c443aac3240b98585384e3a6f109fbf6969e264c3f183d69aba7e1'
TOPIC_WITHDRAWAL_INITIATED      = '\x3073a74ecb728d10be779fe19a74a1428e20468f5b4d167bf9c73d9067847d73'
TOPIC_DEPOSIT_FINALIZED         = '\xc7f2e9c55c40a50fbc217dfc70cd39a222940dfa62145aa0ca49eb9535d4fcb2'
TOPIC_WITHDRAWAL_FINALIZED      = '\x891afe029c75c4f8c5855fc3480598bc5a53739344f6ae575bdb7ea2a79f56b3'
TOPIC_TX_TO_L2                  = '\xc1d1490cf25c3b40d600dfb27c7680340ed1ab901b7e8f3551280968a3b372b0'
TOPIC_TRANSFER_ROUTED           = '\x85291dff2161a93c2f12c819d31889c96c63042116f5bc5a205aa701c2c429f5'
TOPIC_GATEWAY_SET               = '\x812ca95fe4492a9e2d1f2723c2c40c03a60a27b059581ae20ac4e4d73bfba354'
TOPIC_TOKEN_SET                 = '\x0dd664a155dd89526bb019e22b00291bb7ca9d07ba3ec4a1a76b410da9797ceb'
TOPIC_TX_TO_L1                  = '\x2b986d32a0536b7e19baa48ab949fec7b903b7fad7730820b20632d100cc3a68'   -- L2 gateways
-- Classic / legacy (historical)
TOPIC_OUTBOX_ENTRY_CREATED_CLASSIC = '\xe5ccc8d7080a4904b2f4e42d91e8f06b13fe6cb2181ad1fe14644e856b44c131'
TOPIC_L2_TO_L1_TRANSACTION_LEGACY  = '\x5baaa87db386365b5c161be377bc3d8e317e8d98d71a3ca7ed7d555340c8f767'
-- Proxy upgrade
TOPIC_UPGRADED                  = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors =====
-- Inbox
SEL_DEPOSIT_ETH                 = '\x439370b1'
SEL_CREATE_RETRYABLE_TICKET     = '\x679b6ded'
SEL_UNSAFE_CREATE_RETRYABLE     = '\x6e6e8a6a'
SEL_SEND_L2_MESSAGE             = '\xb75436bb'
-- Bridge
SEL_ENQUEUE_DELAYED_MESSAGE     = '\x8db5993b'
SEL_EXECUTE_CALL                = '\x9e5d4c49'
SEL_BRIDGE_ROLLUP               = '\xcb23bcb5'
SEL_SET_OUTBOX                  = '\xcee3d728'
SEL_SET_DELAYED_INBOX           = '\x47fb24c5'
-- Outbox
SEL_EXECUTE_TRANSACTION         = '\x08635a95'
SEL_IS_SPENT                    = '\x5a129efe'
SEL_UPDATE_SEND_ROOT            = '\xa04cee60'
SEL_EXECUTE_TRANSACTION_CLASSIC = '\x9c5cfe0b'   -- Classic Outboxes only
-- SequencerInbox
SEL_ADD_SEQ_BATCH               = '\xe0bc9729'
SEL_ADD_SEQ_BATCH_FROM_ORIGIN   = '\x8f111f3c'
SEL_FORCE_INCLUSION             = '\xf1981578'
SEL_SET_VALID_KEYSET            = '\xd1ce8da8'
-- GatewayRouter / gateways
SEL_OUTBOUND_TRANSFER           = '\xd2ce7d65'
SEL_OUTBOUND_TRANSFER_REFUND    = '\x4fb1a07b'
SEL_FINALIZE_INBOUND_TRANSFER   = '\x2e567b36'
SEL_GET_GATEWAY                 = '\xbda009fe'
SEL_CALC_L2_TOKEN_ADDRESS       = '\xa7e28d48'
SEL_REGISTER_TOKEN_TO_L2        = '\xca346d4a'
SEL_L2_OUTBOUND_TRANSFER_4ARG   = '\x7b3a3c8b'   -- L2 router / gateways
-- ArbSys / ArbRetryableTx
SEL_SEND_TX_TO_L1               = '\x928c169a'
SEL_WITHDRAW_ETH                = '\x25e16063'
SEL_RETRYABLE_REDEEM            = '\xeda1122c'
SEL_RETRYABLE_KEEPALIVE         = '\xf0b21a41'
SEL_RETRYABLE_CANCEL            = '\xc4d252f5'
-- proxy
SEL_UPGRADE_TO_AND_CALL         = '\x4f1ef286'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT               = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT              = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
ROLLUP_USER_LOGIC_SLOT          = '\x2b1dbce74324248c222f0ec2d5ed7bd323cfc425b336f0253c5ccfda7265546d'

-- ===== Addresses — Ethereum L1 · Arbitrum One =====
ETH_ONE_INBOX                   = '\x4dbd4fc535ac27206064b68ffcf827b0a60bab3f'
ETH_ONE_BRIDGE                  = '\x8315177ab297ba92a06054ce80a67ed4dbd7ed3a'
ETH_ONE_OUTBOX                  = '\x0b9857ae2d4a3dbe74ffe1d7df045bb7f96e4840'
ETH_ONE_SEQUENCER_INBOX         = '\x1c479675ad559dc151f6ec7ed3fbf8cee79582b6'
ETH_ONE_ROLLUP_LIVE             = '\x4dceb440657f21083db8add07665f8ddbe1dcfc0'   -- BoLD; = Bridge.rollup()
ETH_ONE_ROLLUP_LEGACY           = '\x5ef0d09d1e6204141b4d37530808ed19f60fba35'   -- classic, disconnected
ETH_ONE_L1_GATEWAY_ROUTER       = '\x72ce9c846789fdb6fc1f34ac4ad25dd9ef7031ef'
ETH_ONE_L1_ERC20_GATEWAY        = '\xa3a7b6f88361f48403514059f1f16c8e78d60eec'
ETH_ONE_L1_CUSTOM_GATEWAY       = '\xcee284f754e854890e311e3280b767f80797180d'
ETH_ONE_L1_WETH_GATEWAY         = '\xd92023e9d9911199a6711321d1277285e6d4e2db'
ETH_ONE_CORE_PROXY_ADMIN        = '\x554723262467f125ac9e1cdfa9ce15cc53822dbd'
ETH_ONE_TOKEN_PROXY_ADMIN       = '\x9ad46fac0cf7f790e5be05a0f15223935a0c0ada'
ETH_ONE_CLASSIC_OUTBOX_1        = '\x760723cd2e632826c38fef8cd438a4cc7e7e1a40'   -- still pays old withdrawals
ETH_ONE_CLASSIC_OUTBOX_2        = '\x667e23abd27e623c11d4cc00ca3ec4d0bd63337a'
ETH_ONE_DAI_GATEWAY             = '\xd3b5b60020504bc3489d6949d545893982ba3011'   -- emits the events
ETH_ONE_DAI_ESCROW              = '\xa10c7ce4b876998858b1a9e12b10092229539400'   -- holds the DAI
ETH_ONE_GRT_GATEWAY             = '\x01cdc91b0a9ba741903aa3699bf4ce31d6c5cc06'   -- emits the events
ETH_ONE_GRT_ESCROW              = '\x36aff7001294dae4c2ed4fdefc478a00de77f090'   -- holds the GRT
ETH_ONE_ARB_GATEWAY             = '\xbbce8aa77782f13d4202a230d978f361b011db27'   -- burns / mints L1 ARB
ETH_ONE_WSTETH_GATEWAY          = '\x0f25c1dc2a9922304f2eac71dca9b07e310e8e5a'   -- Lido; holds the wstETH
ETH_ONE_L1_UPGRADE_EXECUTOR     = '\x3fffbadaf827559da092217e474760e2b2c3cedd'

-- ===== Robinhood Chain (4663) and the other Orbit chains: orbit.md §10 =====

-- ===== Addresses — Ethereum L1 · Arbitrum Nova (chain 42170, outside the 8) =====
ETH_NOVA_INBOX                  = '\xc4448b71118c9071bcb9734a0eac55d18a153949'
ETH_NOVA_BRIDGE                 = '\xc1ebd02f738644983b6c4b2d440b8e77dde276bd'
ETH_NOVA_OUTBOX                 = '\xd4b80c3d7240325d18e645b49e6535a3bf95cc58'
ETH_NOVA_SEQUENCER_INBOX        = '\x211e1c4c7f1bf5351ac850ed10fd68cffcf6c21b'
ETH_NOVA_ROLLUP_LIVE            = '\xe7e8ccc7c381809bdc4b213ce44016300707b7bd'
ETH_NOVA_L1_GATEWAY_ROUTER      = '\xc840838bc438d73c16c2f8b22d2ce3669963cd48'
ETH_NOVA_L1_ERC20_GATEWAY       = '\xb2535b988dce19f9d71dfb22db6da744acac21bf'
ETH_NOVA_L1_CUSTOM_GATEWAY      = '\x23122da8c581aa7e0d07a36ff1f16f799650232f'
ETH_NOVA_L1_WETH_GATEWAY        = '\xe4e2121b479017955be0b175305b35f312330bae'

-- ===== Addresses — Arbitrum One L2 (chain 42161) =====
ARB_ARBSYS                      = '\x0000000000000000000000000000000000000064'
ARB_ARB_RETRYABLE_TX            = '\x000000000000000000000000000000000000006e'
ARB_NODE_INTERFACE              = '\x00000000000000000000000000000000000000c8'
ARB_L2_GATEWAY_ROUTER           = '\x5288c571fd7ad117bea99bf60fe0846c4e84f933'
ARB_L2_ERC20_GATEWAY            = '\x09e9222e96e7b4ae2a407b98d48e330053351eee'
ARB_L2_CUSTOM_GATEWAY           = '\x096760f208390250649e3e8763348e783aef5562'
ARB_L2_WETH_GATEWAY             = '\x6c411ad3e74de3e7bd422b94a27770f5b86c623b'
ARB_L2_TOKEN_PROXY_ADMIN        = '\xd570ace65c43af47101fc6250fd6fc63d1c22a86'

-- ===== L1<->L2 address alias offset =====
L1_TO_L2_ALIAS_OFFSET           = '\x1111000000000000000000000000000000001111'
```

---

## 11. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` (and `[0:4]` for selectors) with keccak-256, then cross-checked against live `eth_getLogs` / bytecode:
  - `MessageDelivered` (242 logs), `InboxMessageDelivered` (51), `SequencerBatchDelivered` `0x7394f4a19a13c7b92b5bb71033245305946ef78452f7b4986ac1390b5df4ebd7` (100), `OutBoxTransactionExecuted` (28), `SendRootUpdated` (24), `DepositInitiated`/`TxToL2` (409 each), `WithdrawalFinalized` (139), `TransferRouted` (709) on the cited Ethereum emitters; `DepositFinalized` and `L2ToL1Tx` `0x3e7aafa77dbf186b7fd488006beff893744caa3c4f6f299e8a709fa2087374fc` / `SendMerkleUpdate` on Arbitrum One; `AssertionCreated` `0x901c3aee23cf4478825462caaab375c606ab83516060388344f0650340753630` (34) and `AssertionConfirmed` `0xfc42829b29c259a7370ab56c8f69fce23b5f351a9ce151da453281993ec0090c` (60) on the live rollup `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0`.
  - `SequencerBatchDelivered` and `AssertionCreated` signatures were reconstructed field-by-field from live log topic/data layout and matched exactly against the keccak of the full tuple (the BoLD `AssertionInputs` struct resolved from `nitro-contracts/src/rollup/Assertion.sol` + `AssertionState`/`GlobalState`).
  - Core function selectors (`depositEth`, `createRetryableTicket` 8-arg, `enqueueDelayedMessage`, `executeCall`, `executeTransaction`, `addSequencerL2Batch`, `forceInclusion` and the other rows marked *(impl)*) existence-checked as **present** in the live implementation bytecode via PUSH4 scan; the 10-arg `createRetryableTicket`/`unsafeCreateRetryableTicket` variants confirmed **absent**.
- **Addresses:** parsed from the official Arbitrum docs/SDK address tables and the `nitro-contracts` / `token-bridge-contracts` deployment files, then existence-checked via `eth_getCode` (non-empty on Ethereum + Arbitrum One; `0x` on Base/BNB/Avalanche/Optimism/Polygon). Wiring re-derived live: `Inbox.bridge()` → Bridge, `Bridge.rollup()` → **the live rollup** (`0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0` One, `0xE7E8cCC7c381809BDC4b213CE44016300707B7Bd` Nova), confirming the legacy `0x5eF0D09d1E6204141B4d37530808eD19f60FBa35` rollup is disconnected.
- **Proxies:** EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` and admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` read live for every proxy; the Rollup's secondary user-logic slot `0x2b1dbce74324248c222f0ec2d5ed7bd323cfc425b336f0253c5ccfda7265546d` read live. Generation determined by selector probing the user-logic impl: `getAssertion(bytes32)` present + `latestNodeCreated()`/`getNode(uint64)` absent ⇒ **BoLD** on `0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0`; the inverse on the legacy `0x5eF0D09d1E6204141B4d37530808eD19f60FBa35` ⇒ classic Nitro. Precompiles confirmed non-proxy (`eth_getCode` = `0xfe`, impl slot `0x0`).
- **Chain coverage:** `eth_getCode` for Inbox/Bridge/Rollup/L1GatewayRouter/L2GatewayRouter on all seven target RPCs, and on Robinhood Chain (4663) on 2026-09-29; non-empty only on Ethereum (1) and Arbitrum One (42161).
- **Rows added on 2026-09-29** (Classic Outboxes, DAI / GRT / ARB / wstETH gateways and escrows, `TxToL1`, `OutboxEntryCreated`, the legacy `L2ToL1Transaction`, the classic `executeTransaction`, the 4-argument L2 `outboundTransfer`): hashes recomputed as `keccak256(sig)` from `token-bridge-contracts` v1.2.5 (`L2ArbitrumMessenger.sol`, `L1ReverseCustomGateway.sol`), `nitro-precompile-interfaces` `ArbSys.sol` and the classic Outbox ABI shipped in `OffchainLabs/arbitrum-sdk` (`packages/sdk/src/lib/dataEntities/Outbox.json`). Wiring read live: `Bridge.allowedOutboxList(0..2)` names the Nitro Outbox and both Classic Outboxes; `L1GatewayRouter.getGateway(token)` maps DAI, GRT, L1 ARB and wstETH to the four gateways; `l1Escrow()` (DAI) and `escrow()` (GRT) name the escrows; `counterpartGateway()` names the L2 gateways (code on Arbitrum One). Owner registries agree: MakerDAO chainlog `ARBITRUM_DAI_BRIDGE` / `ARBITRUM_ESCROW` (read on chain at `0xdA0Ab1e0017DEbCd72Be8599041a2aa3bA7e740F`), The Graph `addresses.json` (`L1GraphTokenGateway`, `BridgeEscrow`), the Arbitrum DAO deployment list ("$ARB Gateway (L1)", "L1 Proxy Admin", "L1 Upgrade Executor"), and the Lido deployed-contracts list (`L1ERC20TokenGateway`). PUSH4 scans: the classic `executeTransaction` `0x9c5cfe0b` is present and the Nitro `0x08635a95` absent in both classic implementations; `0x7b3a3c8b` is present in the four Arbitrum One L2 implementations. Value legs read from receipts (gotcha 17 samples; Classic Outbox payout `0x4cce04f5cef8e575035880f04fe568e9ca788fca7f2fceee39e8d6654b540e05`, third topic `0x204e`).
- **Window of the 2026-09-29 counts:** 2026-09-28 00:00–12:00 UTC, Ethereum blocks 26,072,222–26,075,812 and Arbitrum One blocks 509,539,969–509,698,804, counted with `eth_getLogs` per emitter. One: 160 `InboxMessageDelivered` at the Delayed Inbox and 364 at the SequencerInbox; 91 `DepositInitiated` (64 ERC20, 19 WETH, 3 DAI, 3 GRT, 2 custom); 80 `OutBoxTransactionExecuted` at the Outbox and 4 at Classic Outbox 1; 84 `BridgeCallTriggered`; 28 `WithdrawalFinalized`; 12 `AssertionCreated` / 12 `AssertionConfirmed`. Nova: 64 `OutBoxTransactionExecuted`, 34 batch reports, 0 delayed-inbox deposits. Arbitrum One L2: 12 `L2ToL1Tx`, 0 `L2ToL1Transaction`, 3 `TxToL1`.

Authoritative sources:
- Canonical repos: [`OffchainLabs/nitro-contracts`](https://github.com/OffchainLabs/nitro-contracts) (Inbox, Bridge, Outbox, SequencerInbox, Rollup/BoLD, Assertion structs) · [`OffchainLabs/token-bridge-contracts`](https://github.com/OffchainLabs/token-bridge-contracts) (gateways + router) · [`OffchainLabs/nitro`](https://github.com/OffchainLabs/nitro) (ArbOS precompiles ArbSys/ArbRetryableTx/NodeInterface).
- Official docs / address registry: [Arbitrum docs — contract addresses](https://docs.arbitrum.io/build-decentralized-apps/reference/contract-addresses) (lists both Classic Outboxes) · [Arbitrum SDK `networks`](https://github.com/OffchainLabs/arbitrum-sdk).
- Custom-gateway owners: [Arbitrum DAO deployment addresses](https://docs.arbitrum.foundation/deployment-addresses) · [Lido deployed contracts](https://docs.lido.fi/deployed-contracts/) · [The Graph `packages/contracts/addresses.json`](https://github.com/graphprotocol/contracts/blob/main/packages/contracts/addresses.json) · MakerDAO chainlog (on chain) · [`OffchainLabs/nitro-precompile-interfaces` `ArbSys.sol`](https://github.com/OffchainLabs/nitro-precompile-interfaces).
- Explorers: [Etherscan Bridge](https://etherscan.io/address/0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a) · [Etherscan live Rollup](https://etherscan.io/address/0x4DCeB440657f21083db8aDd07665f8ddBe1DCfc0) · [Arbiscan L2GatewayRouter](https://arbiscan.io/address/0x5288c571Fd7aD117beA99bF60FE0846C4E84F933).
