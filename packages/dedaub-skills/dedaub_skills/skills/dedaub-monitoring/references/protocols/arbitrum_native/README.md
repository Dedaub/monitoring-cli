# Arbitrum native bridge (Nitro) — reference index

The Arbitrum canonical bridge is the Nitro contract set (Bridge, Inbox, SequencerInbox, Outbox, Rollup, and the gateway token bridge). Offchain Labs runs it for Arbitrum One and Nova. Every Arbitrum Orbit chain, Robinhood Chain included, runs its own copy of the same contracts under its own addresses and chain id.

**Status:** `core.md` verified on 2026-06-09 and extended on 2026-09-29; `orbit.md` verified on 2026-09-29. Activity counts use the pinned 12-hour window 2026-09-28 00:00–12:00 UTC.

| File | Covers | Contracts | Proxy pattern | Chains (of the 8) | Status |
|------|--------|-----------|---------------|-------------------|--------|
| [core.md](core.md) | **Arbitrum One and Nova**: the L1 contracts on Ethereum, the One L2 side, the Classic Outboxes and the DAI, GRT, ARB and wstETH gateways | Bridge, Inbox, SequencerInbox, Outbox, BoLD Rollup, gateways and router, ArbSys, ArbRetryableTx | EIP-1967 transparent proxies; double-logic Rollup; precompiles | Ethereum, Arbitrum One (Nova 42170 is outside the eight) | Live |
| [orbit.md](orbit.md) | **Orbit chains**: Robinhood Chain (Ethereum side and L2 side), 12 more Orbit L2s on Ethereum, Orbit L3s on Base, 34 Orbit L3s on Arbitrum One, one Orbit L3 on Robinhood Chain, and 18 further Orbit chains found on chain | the same Nitro contracts; `ERC20Bridge` / `ERC20Inbox` on fee-token chains; UpgradeExecutor; factories | the same patterns; Rollups classic or BoLD | Ethereum, Base, Arbitrum One, Robinhood Chain | Live |

Not deployed on Optimism, Polygon PoS, BNB or Avalanche: `eth_getCode` returns `0x` at every address of both files there, the Orbit factory maps list no deployment for those chain ids, and the pinned window has no Nitro log there.

## Shared topics (the same topic0 on every Nitro chain)

These values do not depend on the chain or on the fee model. **A monitor keys on the emitter**, never on topic0 alone.

| topic0 | Event | Emitter (per chain) |
|--------|-------|---------------------|
| `0x5e3c1311ea442664e8b1611bfabef659120ea7a0a2cfc0667700bebc69cbffe1` | `MessageDelivered(uint256 indexed messageIndex, bytes32 indexed beforeInboxAcc, address inbox, uint8 kind, address sender, bytes32 messageDataHash, uint256 baseFeeL1, uint64 timestamp)` | Bridge / ERC20Bridge (every delayed message; kind 13 = batch report) |
| `0xff64905f73a67fb594e0f940a8075a860db489ad991e032f48c81123eb52d60b` | `InboxMessageDelivered(uint256 indexed messageNum, bytes data)` | Inbox (deposits) **and** SequencerInbox (batch reports) |
| `0x2d9d115ef3e4a606d698913b1eae831a3cdfe20d9a83d48007b0526749c3d466` | `BridgeCallTriggered(address indexed outbox, address indexed to, uint256 value, bytes data)` | Bridge (every payout, from any allowed outbox) |
| `0x20af7f3bbfe38132b8900ae295cd9c8d1914be7052d061a511f3f728dab18964` | `OutBoxTransactionExecuted(address indexed to, address indexed l2Sender, uint256 indexed zero, uint256 transactionIndex)` | Outbox (and One's Classic Outboxes, with a non-zero third topic) |
| `0xb4df3847300f076a369cd76d2314b470a1194d9e8a6bb97f1860aee88a5f6748` | `SendRootUpdated(bytes32 indexed outputRoot, bytes32 indexed l2BlockHash)` | Outbox (status only) |
| `0x7394f4a19a13c7b92b5bb71033245305946ef78452f7b4986ac1390b5df4ebd7` | `SequencerBatchDelivered(uint256 indexed batchSequenceNumber, bytes32 indexed beforeAcc, bytes32 indexed afterAcc, bytes32 delayedAcc, uint256 afterDelayedMessagesRead, (uint64 minTimestamp, uint64 maxTimestamp, uint64 minBlockNumber, uint64 maxBlockNumber) timeBounds, uint8 dataLocation)` | SequencerInbox (status only) |
| `0xfc42829b29c259a7370ab56c8f69fce23b5f351a9ce151da453281993ec0090c` | `AssertionConfirmed(bytes32 indexed assertionHash, bytes32 blockHash, bytes32 sendRoot)` | BoLD Rollup (status only) |
| `0x22ef0479a7ff660660d1c2fe35f1b632cf31675c2d9378db8cec95b00d8ffa3c` | `NodeConfirmed(uint64 indexed nodeNum, bytes32 blockHash, bytes32 sendRoot)` | classic Rollup (status only) |
| `0xb8910b9960c443aac3240b98585384e3a6f109fbf6969e264c3f183d69aba7e1` | `DepositInitiated(address l1Token, address indexed _from, address indexed _to, uint256 indexed _sequenceNumber, uint256 _amount)` | parent-chain gateways |
| `0x891afe029c75c4f8c5855fc3480598bc5a53739344f6ae575bdb7ea2a79f56b3` | `WithdrawalFinalized(address l1Token, address indexed _from, address indexed _to, uint256 indexed _exitNum, uint256 _amount)` | parent-chain gateways |
| `0xc1d1490cf25c3b40d600dfb27c7680340ed1ab901b7e8f3551280968a3b372b0` | `TxToL2(address indexed _from, address indexed _to, uint256 indexed _seqNum, bytes _data)` | parent-chain gateways and router, and any other contract built on the L1 messenger |
| `0x85291dff2161a93c2f12c819d31889c96c63042116f5bc5a205aa701c2c429f5` | `TransferRouted(address indexed token, address indexed _userFrom, address indexed _userTo, address gateway)` | gateway routers, both layers (status only) |
| `0x7c793cced5743dc5f531bbe2bfb5a9fa3f40adef29231e6ab165c08a29e3dd89` | `TicketCreated(bytes32 indexed ticketId)` | ArbRetryableTx `0x000000000000000000000000000000000000006E` on the child chain |
| `0xc7f2e9c55c40a50fbc217dfc70cd39a222940dfa62145aa0ca49eb9535d4fcb2` | `DepositFinalized(address indexed l1Token, address indexed _from, address indexed _to, uint256 _amount)` | child-chain gateways |
| `0x3073a74ecb728d10be779fe19a74a1428e20468f5b4d167bf9c73d9067847d73` | `WithdrawalInitiated(address l1Token, address indexed _from, address indexed _to, uint256 indexed _l2ToL1Id, uint256 _exitNum, uint256 _amount)` | child-chain gateways |
| `0x2b986d32a0536b7e19baa48ab949fec7b903b7fad7730820b20632d100cc3a68` | `TxToL1(address indexed _from, address indexed _to, uint256 indexed _id, bytes _data)` | child-chain gateways |
| `0x3e7aafa77dbf186b7fd488006beff893744caa3c4f6f299e8a709fa2087374fc` | `L2ToL1Tx(address caller, address indexed destination, uint256 indexed hash, uint256 indexed position, uint256 arbBlockNum, uint256 ethBlockNum, uint256 timestamp, uint256 callvalue, bytes data)` | ArbSys `0x0000000000000000000000000000000000000064` on the child chain |

The full topic and selector sets are in `core.md` §1–§2; `orbit.md` §1–§2 adds the events and functions that only Orbit deployments use (classic Rollup, fee-token inbox, UpgradeExecutor, factories).

## Collision notes

1. **Same topic0, many chains.** In the pinned window, `SequencerBatchDelivered` came from 22 SequencerInboxes on Ethereum, 7 on Base and 18 on Arbitrum One (Orbit L3s, `orbit.md` §5). Arbitrum One, Nova and Robinhood Chain are three emitter sets among them. Filter on the emitter address, or resolve an unknown emitter with `Bridge.rollup()` then `Rollup.chainId()`.
2. **Same topic0, different meaning of a field.** One's Classic Outboxes emit `OutBoxTransactionExecuted` with the third indexed field = the classic `outboxEntryIndex`, not zero (`core.md` §1.4). On a fee-token chain, `BridgeCallTriggered.value` and the kind-12 amount count the fee token, not ETH (`orbit.md` §9, item 4).
3. **Same topic0, two emitters in one chain.** `InboxMessageDelivered` comes from the Inbox (deposits) and from the SequencerInbox (batch reports); `OwnerFunctionCalled` comes from the SequencerInbox, the Bridge and the Rollup. Filter on the address.
4. **Same name, different topic0 in another bridge.** The OP Stack bridges also emit `WithdrawalInitiated` and `DepositFinalized`, with 6-parameter signatures (`op_stack` slug). They do not collide with the Nitro values above:

| topic0 | Event (OP Stack, not Nitro) |
|--------|-----------------------------|
| `0x73d170910aba9e6d50b102db522b1dbcd796216f5128b445aa2135272886497e` | `WithdrawalInitiated(address indexed l1Token, address indexed l2Token, address indexed from, address to, uint256 amount, bytes extraData)` |
| `0xb0444523268717a02698be47d0803aa7468c00acbed2f8bd93a0459cde61dd89` | `DepositFinalized(address indexed l1Token, address indexed l2Token, address indexed from, address to, uint256 amount, bytes extraData)` |

5. **Generic topics.** `Upgraded(address)` (`0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`) and the ERC-20 `Transfer` (`0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`) come from every proxy and token. They mean a bridge event only at a bridge address.

## Cross-cutting facts

- **Link keys are on chain on both sides.** Deposit: `MessageDelivered.messageIndex` = `InboxMessageDelivered.messageNum` = `TxToL2._seqNum` = `DepositInitiated._sequenceNumber`; on the child chain `TicketCreated.ticketId` is the hash of the submit-retryable transaction. Withdrawal: `L2ToL1Tx.position` = `WithdrawalInitiated._l2ToL1Id` = `TxToL1._id` = `OutBoxTransactionExecuted.transactionIndex`; `_exitNum` joins the two gateway events.
- **`MessageDelivered.sender` is always aliased** (`+ 0x1111000000000000000000000000000000001111`), for an EOA as well as for a contract.
- **Chain ids are EVM chain ids.** Nitro has no separate domain id; `Rollup.chainId()` gives it (One 42161, Nova 42170, Robinhood Chain 4663).
- **Robinhood Chain (4663)** is an ETH-gas Orbit L2 with a BoLD Rollup. Ethereum-side Bridge `0xDf8755334ce7A73cCF6b581C02eA649AE3E864b3`; L2GatewayRouter `0x1E324B9316138CA9a73F960213621AD1aaf01B89` on 4663. Its rows: `orbit.md` §3.1 and §6.
