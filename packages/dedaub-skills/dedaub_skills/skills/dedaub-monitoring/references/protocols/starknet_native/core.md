# Starknet native bridge (StarkGate) — Topics, Selectors, Addresses (Ethereum L1 ↔ Starknet; none of the seven other chains)

**Status:** verified on 2026-09-29 against live Ethereum RPC (code, StarkWare proxy slots, `identify()`, role reads, pinned-window log counts, sample receipts), the canonical `starkware-libs/starkgate-contracts` (branch `SN-v0.14.2`) and `starkware-libs/cairo-lang` Solidity sources, the official `starknet-io/starknet-addresses` token registry, the Starknet docs address page, and `eth_getCode` on all eight target chains.
**Scope:** the Starknet core contract on Ethereum (L1↔L2 messaging, state updates), the StarkGate control plane (StarkgateManager, StarkgateRegistry), the StarkGate multi-token bridge, every per-token StarkGate bridge in the official registry (32 L1 bridges), the MakerDAO DAI v0 gateway and escrow, and the custom LORDS bridge. Topics and selectors are chain-agnostic; addresses are network-specific. Starknet itself (chain id `SN_MAIN`) is not an EVM chain and is not one of the eight targets. **Of the eight target chains, only Ethereum carries Starknet contracts** (§4).

StarkGate is a lock-and-mint bridge. On Ethereum, each bridge contract is also the escrow of its tokens. The Starknet core contract carries the messages and never holds bridged funds (only the L1→L2 message fees, until the next state update pays them to the fee collector). A deposit locks funds in a bridge and sends an L1→L2 message through the core. A withdrawal is a two-step exit: the L2→L1 message is registered by a state update of the core, then anyone calls `withdraw` on the bridge, which consumes the message and releases the funds.

Three facts to know before indexing:

1. **Every bridge and the core are StarkWare proxies, not EIP-1967 proxies.** The implementation sits in slot `keccak256("StarkWare2019.implemntation-slot")` (typo in the original) = `0x177667240aeeea7e35eabe3a35e18306f336219e1386f7710a6bf8783f761b24`. An upgrade emits `ImplementationUpgraded`, not `Upgraded`. `identify()` on the proxy returns the implementation version string (for example `StarkWare_StarknetTokenBridge_2.0_6`).
2. **The link key is the L1→L2 message nonce, and it is on chain only on Ethereum.** `Deposit.nonce` equals `LogMessageToL2.nonce` in the same transaction. No Ethereum event carries the Starknet transaction hash. For a withdrawal, no L1 event carries a key that names the L2 transaction: `ConsumedMessageToL1` and `Withdrawal` carry the recipient, the token and the amount only.
3. **The recipient of a deposit is a Starknet felt (32 bytes), not an address.** `l2Recipient` is an indexed `uint256`. Do not truncate it to 20 bytes.

---

## 0. Contract families, flow and ids

### 0.1 Contract families

| Contract | Role | Proxy |
|---|---|---|
| **Starknet core** | L1↔L2 messaging (`sendMessageToL2`, `consumeMessageFromL2`, cancellation), state updates, program/config hashes, operators. Also emits the per-message events of each state update. | StarkWare legacy proxy |
| **StarknetTokenBridge (multi-token)** | One bridge and escrow for 93 registry tokens (`deposit(token, amount, l2Recipient)`). | StarkWare ProxyV5 (roles) |
| **Per-token StarkGate bridges** (31, §3.2) | One bridge and escrow per token. Three implementation classes: `StarknetERC20Bridge_2.0_5`, `StarknetEthBridge_2.0_4` (both keep the legacy one-token ABI), and `StarknetTokenBridge_2.0_x` (token-explicit ABI only). Two bridges run a haltable class (`2.0_6-halt`) and are halted (§5). | StarkWare legacy proxy or ProxyV5 |
| **StarkgateManager / StarkgateRegistry** | Enroll, deactivate and block tokens; map each token to its deposit bridge and its withdrawal bridges (`getBridge`, `getWithdrawalBridges`). | StarkWare ProxyV5 |
| **DAI v0 gateway (MakerDAO `L1DAIBridge`) + L1Escrow** | The original DAI bridge. Closed for deposits (`isOpen() = 0`); withdrawals of DAI v0 still work. The DAI sits in the separate escrow. | Immutable |
| **LORDS bridge** | A custom, immutable bridge and escrow for LORDS that uses the same core. Not in the StarkGate registry. | Immutable |
| **SHARP verifier (call proxy)** | Verifies the state-update proofs. No value flow. | StarkWare call proxy |

### 0.2 The flow

| Leg | Contract and call | Events (same transaction) | Value movement |
|---|---|---|---|
| **Deposit (source)** | bridge `deposit(address token, uint256 amount, uint256 l2Recipient)` (payable) or `depositWithMessage(...)`; legacy `deposit(uint256 amount, uint256 l2Recipient)` on the ERC20/ETH bridge classes | core `LogMessageToL2` (nonce, fee) → bridge `Deposit` or `DepositWithMessage` (+ `LogDeposit` for the legacy call) | ERC-20 `Transfer(sender → bridge)`. ETH bridge: `msg.value = amount + fee`, the amount stays in the bridge. The fee (wei) goes from the bridge to the core. |
| **L2 consumption (status)** | core `updateState*` (operator) | core `ConsumedMessageToL2` (one per L1→L2 message consumed on Starknet), `LogStateUpdate`, `LogStateTransitionFact` | none (the state update pays the accumulated message fees to the fee collector) |
| **L2→L1 registration (status)** | core `updateState*` | core `LogMessageToL1` (one per L2→L1 message) | none |
| **Withdrawal (destination)** | bridge `withdraw(address token, uint256 amount, address recipient)` (anyone may call it); legacy `withdraw(uint256,address)` / `withdraw(uint256)` | core `ConsumedMessageToL1` → bridge `Withdrawal` | ERC-20 `Transfer(bridge → recipient)`; ETH as an internal value transfer (no log). |
| **Deposit cancel (refund)** | bridge `depositCancelRequest(...)`, then after the cancellation delay `depositReclaim(...)` (same arguments, same nonce) | core `MessageToL2CancellationStarted` + bridge `DepositCancelRequest`; later core `MessageToL2Canceled` + bridge `DepositReclaimed` | the reclaim returns the funds from the bridge to the depositor |

The core's `messageCancellationDelay` is 432100 s (5 days and 100 s, per L2BEAT). Only the original depositor (`msg.sender` of the deposit) can cancel. A withdrawal can be throttled per token to 5 % of the bridge balance per UTC day when the security agent enables the limit (`WithdrawalLimitEnabled`).

### 0.3 Starknet ids

| Id | Value | Where it appears |
|---|---|---|
| Starknet chain id | `SN_MAIN` = `0x534e5f4d41494e` (read live with `starknet_chainId`) | off chain only (no L1 event carries it) |
| L1 handler `handle_token_deposit` | `0x01b64b1b3b690b43b9b514fb81377518f4039cd3e4f4914d8a6bdf01d679fb19` | `LogMessageToL2.selector` (topic3) of a `deposit` |
| L1 handler `handle_deposit_with_message` | `0x008bce41827dd5484d80312a2e43bc42a896e3fcf75bf84c2b49339168dfa00a` | `LogMessageToL2.selector` of a `depositWithMessage` |
| L1 handler `handle_token_deployment` | `0x03d78c7ddffebbba7bd7263963b2e0e86b2ed9e990a4fc1b9aed7acd11b37dbc` | `LogMessageToL2.selector` of a token enrollment (no value) |
| L1 handler `handle_deposit` (legacy and DAI v0) | `0x02d757788a8d8d6f21d1cd40bce38a8222d70654214e96ff95d8086e684fbee5` | pre-2024 deposits and DAI v0 deposits |
| L1 handler `handle_force_withdrawal` (DAI v0) | `0x0283eea9c550fc21d0a9053ca1a8ee6f1cb531fd758474d1b82cc67c236b855d` | DAI v0 forced withdrawal requests |
| Withdrawal payload word 0 | `0` (`TRANSFER_FROM_STARKNET`) | `ConsumedMessageToL1.payload[0]` |
| L2 bridge of each L1 bridge | felt, §3.2 | `LogMessageToL2.toAddress` (topic2) and `ConsumedMessageToL1.fromAddress` (topic1) |
| ETH token marker | `0x0000000000000000000000000000000000455448` (the short string `ETH`) | the `token` field of ETH `Deposit` / `Withdrawal` |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Starknet core — messaging (emitter `0xc662c410C0ECf747543f5bA90660f6ABeBD9C8c4`)

| topic0 | Event | Notes |
|---|---|---|
| `0xdb80dd488acf86d17c747445b0eabb5d57c541d3bd7b6b87af987858e5066b2b` | `LogMessageToL2(address indexed fromAddress, uint256 indexed toAddress, uint256 indexed selector, uint256[] payload, uint256 nonce, uint256 fee)` | **Source-leg message.** `fromAddress` = the L1 bridge, `toAddress` = the L2 bridge felt. Payload of a `deposit`: `[l1Token, depositor, l2Recipient, amountLow, amountHigh]`. |
| `0x7a06c571aa77f34d9706c51e5d8122b5595aebeaa34233bfe866f22befb973b1` | `ConsumedMessageToL1(uint256 indexed fromAddress, address indexed toAddress, uint256[] payload)` | **Destination-leg message**, same transaction as `Withdrawal`. Payload: `[0, recipient, l1Token, amountLow, amountHigh]`. |
| `0x4264ac208b5fde633ccdd42e0f12c3d6d443a4f3779bbf886925b94665b63a22` | `LogMessageToL1(uint256 indexed fromAddress, address indexed toAddress, uint256[] payload)` | Status only: an L2→L1 message registered by a state update (the withdrawal becomes claimable). |
| `0x9592d37825c744e33fa80c469683bbd04d336241bb600b574758efd182abe26a` | `ConsumedMessageToL2(address indexed fromAddress, uint256 indexed toAddress, uint256 indexed selector, uint256[] payload, uint256 nonce)` | Status only: an L1→L2 message was consumed on Starknet (the deposit landed). Carries the same `nonce`. |
| `0x2e00dccd686fd6823ec7dc3e125582aa82881b6ff5f6b5a73856e1ea8338a3be` | `MessageToL2CancellationStarted(address indexed fromAddress, uint256 indexed toAddress, uint256 indexed selector, uint256[] payload, uint256 nonce)` | Refund path, step 1 (status). |
| `0x8abd2ec2e0a10c82f5b60ea00455fa96c41fd144f225fcc52b8d83d94f803ed8` | `MessageToL2Canceled(address indexed fromAddress, uint256 indexed toAddress, uint256 indexed selector, uint256[] payload, uint256 nonce)` | Refund path, step 2; the bridge releases the funds in the same transaction. |

### 1.2 Starknet core — state, configuration, operators and governance (status and admin)

| topic0 | Event |
|---|---|
| `0xd342ddf7a308dec111745b00315c14b7efb2bdae570a6856e088ed0c65a3576c` | `LogStateUpdate(uint256 globalRoot, int256 blockNumber, uint256 blockHash)` |
| `0x9866f8ddfe70bb512b2f2b28b49d4017c43f7ba775f1a20c61c13eea8cdac111` | `LogStateTransitionFact(bytes32 stateTransitionFact)` |
| `0x600a61c1b32ac42fb2fe76e8fc7582a98106668fc16dcd85567cd3937363e49b` | `ProgramHashChanged(address indexed changedBy, uint256 oldProgramHash, uint256 newProgramHash)` |
| `0x07688623ef226ae0c2f88d3fdc7f6bb41427c804bcec3f36699b07148e3f5340` | `AggregatorProgramHashChanged(address indexed changedBy, uint256 oldAggregatorProgramHash, uint256 newAggregatorProgramHash)` |
| `0x393c6beb5756a944b2967f15f31ff671e312e945d7a84fd3bdcfd6b408b2dc79` | `ConfigHashChanged(address indexed changedBy, uint256 oldConfigHash, uint256 newConfigHash)` |
| `0x50a18c352ee1c02ffe058e15c2eb6e58be387c81e73cc1e17035286e54c19a57` | `LogOperatorAdded(address operator)` |
| `0xec5f6c3a91a1efb1f9a308bb33c6e9e66bf9090fad0732f127dfdbf516d0625d` | `LogOperatorRemoved(address operator)` |
| `0x6823b073d48d6e3a7d385eeb601452d680e74bb46afe3255a7d778f3a9b17681` | `Finalized()` |
| `0x6166272c8d3f5f579082f2827532732f97195007983bb5b83ac12c56700b01a6` | `LogNominatedGovernor(address nominatedGovernor)` |
| `0xcfb473e6c03f9a29ddaf990e736fa3de5188a0bd85d684f5b6e164ebfbfff5d2` | `LogNewGovernorAccepted(address acceptedGovernor)` |
| `0xd75f94825e770b8b512be8e74759e252ad00e102e38f50cce2f7c6f868a29599` | `LogRemovedGovernor(address removedGovernor)` |
| `0x7a8dc7dd7fffb43c4807438fa62729225156941e641fd877938f4edade3429f5` | `LogNominationCancelled()` |

The four governor events are emitted both by the core's application governance and by the legacy proxies' proxy governance (and by `OverrideLegacyProxyGovernance` in the legacy bridge classes). Filter on the emitter.

### 1.3 StarkWare proxy — upgrade events (every bridge proxy, the Manager, the Registry and the core)

| topic0 | Event | Notes |
|---|---|---|
| `0xff14288d542bc1c1d15a652cb52af735f065c0c9d70b48e454a203c260733544` | `ImplementationUpgraded(address indexed implementation, bytes initializer)` | **The upgrade event.** Watch it on every address of §3. |
| `0x723a7080d63c133cf338e44e00705cc1b7b2bde7e88d6218a8d62710a329ce1b` | `ImplementationAdded(address indexed implementation, bytes initializer, bool finalize)` | An upgrade is scheduled; the time lock (upgrade delay, §3.2) starts. **Early warning.** |
| `0xe99b980b5259f200e4c1da973ff0251b6d9aaa144714c8773976ecd62b8ebe8d` | `ImplementationRemoved(address indexed implementation, bytes initializer, bool finalize)` | A scheduled upgrade is withdrawn. |
| `0xc13b75a5f14b69ebdc2431a5d475b3bff371abe251b5064144306fbd9c4de35c` | `FinalizedImplementation(address indexed implementation)` | The proxy is frozen for good. |

### 1.4 StarkGate token bridges — value events (multi-token bridge and every per-token StarkWare bridge)

| topic0 | Event | Side |
|---|---|---|
| `0x5f971bd00bf3ffbca8a6d72cdd4fd92cfd4f62636161921d1e5a64f0b64ccb6d` | `Deposit(address indexed sender, address indexed token, uint256 amount, uint256 indexed l2Recipient, uint256 nonce, uint256 fee)` | **Source leg.** `nonce` = the core message nonce. |
| `0x2203a49c69f1a46c1164f5e4a30643dd77b7c59c0ff9bc433256048365c247f1` | `DepositWithMessage(address indexed sender, address indexed token, uint256 amount, uint256 indexed l2Recipient, uint256[] message, uint256 nonce, uint256 fee)` | **Source leg** with an L2 call payload. |
| `0x2717ead6b9200dd235aad468c9809ea400fe33ac69b5bfaa6d3e90fc922b6398` | `Withdrawal(address indexed recipient, address indexed token, uint256 amount)` | **Destination leg.** No nonce, no L2 sender. |
| `0x8f3da3ce93acd45e015b069c8f032d37be93dc9efcaaeda368aa9ca74f64c30a` | `DepositCancelRequest(address indexed sender, address indexed token, uint256 amount, uint256 indexed l2Recipient, uint256 nonce)` | Refund step 1 (status only). |
| `0x50485fb0face2cfd73784044ab4191986b4a6713f01854414e2331a6bb41837d` | `DepositReclaimed(address indexed sender, address indexed token, uint256 amount, uint256 indexed l2Recipient, uint256 nonce)` | **Refund** (funds return to `sender`). |
| `0x889e470f207032611b2f68dbd2124e3139794f19a6b536c83892fd5057603860` | `DepositWithMessageCancelRequest(address indexed sender, address indexed token, uint256 amount, uint256 indexed l2Recipient, uint256[] message, uint256 nonce)` | Refund step 1 (status only). |
| `0xa465a02eedf06ceffd1d99159ad98c5d8fa7f17b870eb22e0bfcec06398a8f73` | `DepositWithMessageReclaimed(address indexed sender, address indexed token, uint256 amount, uint256 indexed l2Recipient, uint256[] message, uint256 nonce)` | **Refund.** |

### 1.5 StarkGate token bridges — configuration, limits, halt and roles (admin, no value unless noted)

| topic0 | Event | Notes |
|---|---|---|
| `0x90fc3f39f8e4669d1bf5f9038707949f8af42a973f62988143be0fa7c3997f18` | `SetL2TokenBridge(uint256 value)` | Repoints the L2 counterpart. High severity. |
| `0xb895637c7d86c9b7b5b747e72195206a3fc21d8df0e019edd2312454ffa733b1` | `SetMaxTotalBalance(address indexed token, uint256 value)` | Deposit cap per token. |
| `0xe2deca319add01142d26def2de47e64bf1fdc70e6f90c13a1862a48bdaaa7cfd` | `WithdrawalLimitEnabled(address indexed sender, address indexed token)` | 5 % per day throttle on (security agent). |
| `0x109dee66091b7a145f557f52c55d7beccb6a29011fc705557e2975749474076b` | `WithdrawalLimitDisabled(address indexed sender, address indexed token)` | Throttle off (security admin). |
| `0xb670c236b17dd3aaf925b2bc17b1a1cc9a5c1523d8f620f09e33f4403fb1c73a` | `TokenEnrollmentInitiated(address token, bytes32 deploymentMsgHash)` | A token is being added to the multi-token bridge. |
| `0x86d6e4556eae726303caf49a75add7d92ac713e46db458dab0622aa263fb48e6` | `TokenDeactivated(address token)` | Deposits of that token stop. |
| `0xc7e24f95ec7b87fb2168f2ab0eb1bec907984818a0930c9886f118f94cbc5a39` | `TokenHaltSignalled(address indexed sender, address indexed token)` | Haltable class only (WBTC, SolvBTC bridges). |
| `0x86de951cb81f3e6fe625737b6a21bbe80650de4d1cc8a9501d1595d6d14755d1` | `TokenHaltCompleted(address indexed sender, address indexed token)` | **Value moves:** the escrow is swept to a clearing address in the same transaction. |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | Roles: app governor, security agent/admin, upgrade governor, token admin. |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` | |

### 1.6 Legacy one-token events

| topic0 | Event | Emitters today |
|---|---|---|
| `0x5b5dbc6c64043a15d3fe6943a6e443a826b78755edc257b2ec890c022225dbcf` | `LogDeposit(address indexed sender, uint256 amount, uint256 indexed l2Recipient, uint256 nonce, uint256 fee)` | The `StarknetERC20Bridge_2.0_5` and `StarknetEthBridge_2.0_4` classes, **in addition to** `Deposit`, when the legacy `deposit(uint256,uint256)` is called. Count one of the two. |
| `0xea57f52faafe318751f75acb6756cff3f66afc10201ef8f2d504e788985db3f5` | `LogDepositCancelRequest(address indexed sender, uint256 amount, uint256 indexed l2Recipient, uint256 nonce)` | Same classes, `legacyDepositCancelRequest` (pre-upgrade deposits). |
| `0xb0b548d5e12b6a60adac4d6dd7610f55134cea4fd145535edc303a48063e0cb4` | `LogDepositReclaimed(address indexed sender, uint256 amount, uint256 indexed l2Recipient, uint256 nonce)` | Same classes, `legacyDepositReclaim` (refund). |
| `0xb4214c8c54fc7442f36d3682f59aebaf09358a4431835b30efb29d52cf9e1e91` | `LogWithdrawal(address indexed recipient, uint256 amount)` | Pre-2.0 bridges (historical); today the DAI v0 gateway and the LORDS bridge (there the first field is named `l1Recipient`). |

### 1.7 DAI v0 gateway (MakerDAO `L1DAIBridge`), its escrow, and the LORDS bridge

| topic0 | Event | Emitter |
|---|---|---|
| `0x9dbb0e7dda3e09710ce75b801addc87cf9d9c6c581641b3275fca409ad086c62` | `LogDeposit(address indexed l1Sender, uint256 amount, uint256 l2Recipient)` | DAI v0 gateway and LORDS bridge (source leg; the gateway is closed, so DAI v0 deposits revert today). |
| `0xdee288762e02cf1a2e99896626b9675625e9fa32cce23d9ee7d490763436eaa3` | `LogForceWithdrawal(address indexed l1Recipient, uint256 amount, uint256 indexed l2Sender)` | DAI v0 gateway (a forced L2 withdrawal request; no value on L1). |
| `0xb8b6bc18e48f410a36e8867df19f26eb867bad25616833b0ed9141f6d8933929` | `LogStartDepositCancellation(uint256 indexed l2Receipient, uint256 amount, uint256 nonce)` | DAI v0 gateway (the field name is misspelled in the source). |
| `0x27342a36c014a937136f67690b80039f954cc7acd1d6a2f5bca3f3d3e7b94837` | `LogCancelDeposit(uint256 indexed l2Recipient, address l1Recipient, uint256 amount, uint256 nonce)` | DAI v0 gateway (refund from the escrow). |
| `0x6defc6f2eb7fe7d2a05d39d89d53405300c4dafb0e9cd1d6affeb7c02a9c3e54` | `LogCeiling(uint256 ceiling)` | DAI v0 gateway (admin). |
| `0x0abf56f125eb3b9ec6b166b22f262406810c29da2da4c902a6ee31694ae11a39` | `LogMaxDeposit(uint256 maxDeposit)` | DAI v0 gateway (admin). |
| `0x1cdde67b72a90f19919ac732a437ac2f7a10fc128d28c2a6e525d89ce5cd9d3a` | `Closed()` | DAI v0 gateway (admin; already closed). |
| `0xdd0e34038ac38b2a1ce960229778ac48a8719bc900b6c4f8d0475c6e8b385a60` | `Rely(address indexed usr)` | DAI v0 gateway and escrow (admin). |
| `0x184450df2e323acec0ed3b5c7531b81f9b4cdef7914dfd4c0a4317416bb5251b` | `Deny(address indexed usr)` | DAI v0 gateway and escrow (admin). |
| `0x6e11fb1b7f119e3f2fa29896ef5fdf8b8a2d0d4df6fe90ba8668e7d8b2ffa25e` | `Approve(address indexed token, address indexed spender, uint256 value)` | DAI v0 escrow: grants a spender access to the escrowed DAI. **High severity.** |

### 1.8 StarkgateManager and StarkgateRegistry (admin)

| topic0 | Event | Emitter |
|---|---|---|
| `0x22a7d63273ca5d74f19d48b49212c82be27729cc3353449d494d000fc435bee4` | `TokenEnrolled(address indexed token, address indexed sender)` | Manager |
| `0xf4b704dd6f08403eab5741ede579b6c3f7f8984842d9ca8ddb2b58efc9a8cef0` | `ExistingBridgeAdded(address indexed token, address indexed bridge)` | Manager |
| `0x00068b447690811e3678da5fdb0b8f068476a81898e529dfc87d3dc69af019ff` | `TokenDeactivated(address indexed token, address indexed sender)` | Manager (two-argument form; the bridge form is §1.5) |
| `0x9069e4065b5a726f2c4660d01a195dfe89fec6c66ddeb2820353bc5a7518c7e9` | `TokenBlocked(address indexed token, address indexed sender)` | Manager |
| `0x169097aa60be141cd725083125ddf0d1330273f15ba137cf74914d24b4c6d362` | `TokenEnlisted(address indexed token, address indexed bridge)` | Registry |
| `0x8f41c4654c849cdf55aec592405d4ed6fcad4c16895633c4e8ff23bb4ebdd2a2` | `TokenStatusBlocked(address indexed token)` | Registry |
| `0x0d8ce137b708fa1f68a42ceb628ec64227e0381c4ecfd1c920804fa9e718a308` | `TokenSelfRemoved(address indexed token, address indexed bridge)` | Registry |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Token bridges — current ABI (every StarkWare bridge)

| Selector | Signature | Notes |
|---|---|---|
| `0x0efe6a8b` | `deposit(address token, uint256 amount, uint256 l2Recipient)` | payable (`msg.value` = fee; ETH bridge: amount + fee). Emits `Deposit`. |
| `0xbe58b18e` | `depositWithMessage(address token, uint256 amount, uint256 l2Recipient, uint256[] message)` | payable. Emits `DepositWithMessage`. |
| `0x69328dec` | `withdraw(address token, uint256 amount, address recipient)` | Anyone may call; pays `recipient`. Emits `Withdrawal`. |
| `0xf3fef3a3` | `withdraw(address token, uint256 amount)` | Pays `msg.sender`. |
| `0xa6d1d6c6` | `depositCancelRequest(address token, uint256 amount, uint256 l2Recipient, uint256 nonce)` | Depositor only. |
| `0x23205c52` | `depositReclaim(address token, uint256 amount, uint256 l2Recipient, uint256 nonce)` | After the delay; refunds the depositor. |
| `0xcf50fd1c` | `depositWithMessageCancelRequest(address token, uint256 amount, uint256 l2Recipient, uint256[] message, uint256 nonce)` | |
| `0xb5cd0c3c` | `depositWithMessageReclaim(address token, uint256 amount, uint256 l2Recipient, uint256[] message, uint256 nonce)` | |
| `0x7fc2ab3e` | `setL2TokenBridge(uint256 l2TokenBridge_)` | App governor. |
| `0xd2b51eea` | `setMaxTotalBalance(address token, uint256 maxTotalBalance_)` | App governor. |
| `0x14af98b3` | `enableWithdrawalLimit(address token)` | Security agent. |
| `0x5a72af89` | `disableWithdrawalLimit(address token)` | Security admin. |
| `0xad8b92b4` | `enrollToken(address token)` | Manager only (multi-token bridge). |
| `0x3ea053eb` | `deactivate(address token)` | Manager only. |
| `0xa7acb6ed` | `signalTokenHalt(address token)` | Haltable class only. |
| `0xb1ed16a4` | `completeTokenHalt(address token, uint256 amount, address recipient)` | Haltable class only; sweeps the escrow. |
| `0xeeb72866` | `identify()` | view: implementation version string. |
| `0x3429072c` | `getL2Bridge()` | view: the L2 bridge felt. |
| `0x30ccebb5` | `getStatus(address token)` | view: `0` unknown, `1` pending, `2` active, `3` deactivated. |
| `0x0c6f8664` | `isServicingToken(address token)` | view. |
| `0x496ae54c` | `getRemainingIntradayAllowance(address token)` | view: withdrawal quota left today. |
| `0x4baf43da` | `getMaxTotalBalance(address token)` | view. |
| `0xaf8bc15e` | `estimateDepositFeeWei()` | view. |

### 2.2 Token bridges — legacy one-token ABI (`StarknetERC20Bridge_2.0_5`, `StarknetEthBridge_2.0_4`)

| Selector | Signature | Notes |
|---|---|---|
| `0xe2bbb158` | `deposit(uint256 amount, uint256 l2Recipient)` | payable. Emits `Deposit` **and** `LogDeposit`. |
| `0x00f714ce` | `withdraw(uint256 amount, address recipient)` | Also the DAI v0 gateway and the LORDS bridge (there: `withdraw(uint256 amount, address l1Recipient)`). |
| `0x2e1a7d4d` | `withdraw(uint256 amount)` | |
| `0x6ffed68b` | `legacyDepositCancelRequest(uint256 amount, uint256 l2Recipient, uint256 nonce)` | |
| `0x7d22dbc7` | `legacyDepositReclaim(uint256 amount, uint256 l2Recipient, uint256 nonce)` | |
| `0x19534075` | `maxTotalBalance()` | view. |

### 2.3 Starknet core

| Selector | Signature | Notes |
|---|---|---|
| `0x3e3aa6c5` | `sendMessageToL2(uint256 toAddress, uint256 selector, uint256[] payload)` | payable (fee, at most `getMaxL1MsgFee()`); returns `(bytes32 msgHash, uint256 nonce)`. |
| `0x2c9dd5c0` | `consumeMessageFromL2(uint256 fromAddress, uint256[] payload)` | `msg.sender` must be the L1 recipient of the message. |
| `0x7a98660b` | `startL1ToL2MessageCancellation(uint256 toAddress, uint256 selector, uint256[] payload, uint256 nonce)` | |
| `0x6170ff1b` | `cancelL1ToL2Message(uint256 toAddress, uint256 selector, uint256[] payload, uint256 nonce)` | |
| `0x507ee528` | `updateStateKzgDA(uint256[] programOutput, bytes[] kzgProofs)` | Operator only (current state-update path). |
| `0x77552641` | `updateState(uint256[] programOutput, uint256 onchainDataHash, uint256 onchainDataSize)` | Operator only (calldata path). |
| `0xb64b6737` | `l1ToL2MsgHash(address fromAddress, uint256 toAddress, uint256 selector, uint256[] payload, uint256 nonce)` | pure: the L1→L2 message hash. |
| `0x3d8a5df8` | `l2ToL1MsgHash(uint256 fromAddress, address toAddress, uint256[] payload)` | pure. |
| `0x77c7d7a9` | `l1ToL2Messages(bytes32 msgHash)` | view: fee + 1 while pending, 0 once consumed or canceled. |
| `0xa46efaf3` | `l2ToL1Messages(bytes32 msgHash)` | view: count of unconsumed L2→L1 messages. |
| `0x018cccdf` | `l1ToL2MessageNonce()` | view: next nonce. |
| `0x8303bd8a` | `messageCancellationDelay()` | view. |
| `0x35befa5d` | `stateBlockNumber()` | view. |
| `0x9588eca2` | `stateRoot()` | view. |
| `0xe87e7332` | `setProgramHash(uint256 newProgramHash)` | Governance. **High severity.** |
| `0x3d07b336` | `setConfigHash(uint256 newConfigHash)` | Governance. |
| `0x9020429c` | `setAggregatorProgramHash(uint256 newAggregatorProgramHash)` | Governance. |
| `0xc99d397f` | `setMessageCancellationDelay(uint256 delayInSeconds)` | Governance. |
| `0x3682a450` | `registerOperator(address newOperator)` | Governance. |
| `0x96115bc2` | `unregisterOperator(address removedOperator)` | Governance. |
| `0x6d70f7ae` | `isOperator(address user)` | view. |
| `0x91a66a26` | `starknetNominateNewGovernor(address newGovernor)` | Governance. |
| `0x946be3ed` | `starknetAcceptGovernance()` | |
| `0x84f921cd` | `starknetRemoveGovernor(address governorForRemoval)` | |
| `0x01a01590` | `starknetIsGovernor(address user)` | view. |

### 2.4 StarkWare proxy and roles

| Selector | Signature | Notes |
|---|---|---|
| `0x5e3a97e7` | `addImplementation(address newImplementation, bytes data, bool finalize)` | Upgrade governor. Starts the time lock. |
| `0x7147855d` | `upgradeTo(address newImplementation, bytes data, bool finalize)` | Upgrade governor. Emits `ImplementationUpgraded`. |
| `0x5cef2e86` | `removeImplementation(address removedImplementation, bytes data, bool finalize)` | |
| `0x5c60da1b` | `implementation()` | view (also readable from the slot). |
| `0x72a44f07` | `getUpgradeActivationDelay()` | view (seconds). |
| `0xe907fa3c` | `isNotFinalized()` | view. |
| `0x8757653f` | `proxyNominateNewGovernor(address newGovernor)` | Legacy proxies. |
| `0x6684b1d6` | `proxyAcceptGovernance()` | Legacy proxies. |
| `0x12f16e6d` | `proxyRemoveGovernor(address governorForRemoval)` | Legacy proxies. |
| `0xb449ea5d` | `proxyIsGovernor(address testGovernor)` | view, legacy proxies. |
| `0x6c04d9d5` | `isUpgradeGovernor(address account)` | view, ProxyV5 proxies. |
| `0x5a5d1bb9` | `isAppGovernor(address account)` | view. |
| `0x757bd9ab` | `isSecurityAgent(address account)` | view. |
| `0xd08fb6cb` | `isSecurityAdmin(address account)` | view. |
| `0xcb1cccce` | `isGovernanceAdmin(address account)` | view. |
| `0xa2bdde3d` | `isTokenAdmin(address account)` | view. |
| `0x6fc97cbf` | `registerUpgradeGovernor(address account)` | Governance admin. |
| `0x0e770f23` | `registerSecurityAgent(address account)` | Security admin. |
| `0xcdd1f70d` | `registerAppGovernor(address account)` | App role admin. |

### 2.5 StarkgateManager, StarkgateRegistry, DAI v0 gateway, LORDS bridge

| Selector | Signature | Notes |
|---|---|---|
| `0xc1d220fe` | `enrollTokenBridge(address token)` | Manager, payable, permissionless: adds a token to the multi-token bridge. |
| `0x4ee165d6` | `addExistingBridge(address token, address bridge_)` | Manager, token admin. |
| `0x68173bcf` | `deactivateToken(address token)` | Manager, token admin. |
| `0x726176e8` | `blockToken(address token)` | Manager (token admin) and Registry (manager). |
| `0x5ab1bd53` | `getRegistry()` | Manager view. |
| `0xf44c7c8f` | `getBridge(address token)` | Registry view: the deposit bridge of a token. |
| `0xdf5f8c0c` | `getL2Bridge(address token)` | Registry view. |
| `0x557133f6` | `getWithdrawalBridges(address token)` | Registry view: every bridge that still honours withdrawals (DAI: v0 gateway and current bridge). |
| `0xa3ecff8f` | `enlistToken(address token, address bridge)` | Registry, manager only. |
| `0x65650288` | `selfRemove(address token)` | Registry, called by a bridge. |
| `0xe2bbb158` | `deposit(uint256 amount, uint256 l2Recipient)` | DAI v0 gateway (payable; reverts while closed). |
| `0x00aeef8a` | `deposit(uint256 amount, uint256 l2Recipient, uint256 fee)` | LORDS bridge (payable). |
| `0xfd1275eb` | `forceWithdrawal(uint256 amount, uint256 l2Sender)` | DAI v0 gateway. |
| `0x7c1c29ac` | `startDepositCancellation(uint256 amount, uint256 l2Recipient, uint256 nonce)` | DAI v0 gateway. |
| `0x6c6e4ae3` | `cancelDeposit(uint256 amount, uint256 l2Recipient, address l1Recipient, uint256 nonce)` | DAI v0 gateway (refund from the escrow). |
| `0xe2fdcc17` | `escrow()` | DAI v0 gateway view. |
| `0x47535d7b` | `isOpen()` | DAI v0 gateway view (`0` = closed). |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All addresses below were existence-checked with `eth_getCode` on 2026-09-29. Implementations were read from the StarkWare implementation slot `0x177667240aeeea7e35eabe3a35e18306f336219e1386f7710a6bf8783f761b24`, and versions from `identify()`.

### 3.1 Core, control plane and governance

| Role | Address | Notes |
|---|---|---|
| **Starknet core** | `0xc662c410C0ECf747543f5bA90660f6ABeBD9C8c4` | legacy StarkWare proxy (6151 B); impl `0x9961D34D3baE6914635c882e8FE382e14E0F172A` = `StarkWare_Starknet_2026_11`. |
| **StarkgateManager** | `0x0c5aE94f8939182F2D06097025324D1E537d5B60` | ProxyV5; impl `0x64608BDF1867110f622391196989bF4cE37BBb33` = `StarkWare_StarkgateManager_2.0_1`. |
| **StarkgateRegistry** | `0x1268cc171c54F2000402DfF20E93E60DF4c96812` | ProxyV5; impl `0x39C3b4e670ACa8BC668e5A79680973e57a4C8CEC` = `StarkWare_StarkgateRegistry_2.0_6`. |
| **StarknetTokenBridge (multi-token)** | `0xF5b6Ee2CAEb6769659f6C091D209DfdCaF3F69Eb` | ProxyV5; impl `0xf39d314C5aD7DC88958116dfA7d5ac095d563Aff` = `StarkWare_StarknetTokenBridge_2.0_6`; escrow of 93 tokens; L2 bridge `0x0616757a151c21f9be8775098d591c2807316d992bbc3bb1a5c1821630589256`. |
| SHARP verifier (call proxy) | `0x47312450B3Ac8b5b8e247a6bB6d523e7605bDb60` | impl `0x3597c5CBCbCB30079a0bD2A68cDE5f98272f9feb`; `identify()` = `StarkWare_GpsStatementVerifier_2026_13`; upgrade delay 691200 s. |
| Starkware Security Council (Safe) | `0x15e8c684FD095d4796A0c0CF678554F4c1C7C361` | `proxyIsGovernor` and `starknetIsGovernor` = true on the core; governor of the ETH and STRK bridges. |
| DelayedExecutor (timelock) | `0xCA112018fEB729458b628AadC8f996f9deCbCa0c` | Same rights as the Security Council on the core, ETH and STRK bridges. 8-day delay; owner Starkware Multisig 1 (per L2BEAT). |
| Starkware Multisig 1 (Safe) | `0x83C0A700114101D1283D1405E2c8f21D3F03e988` | Owner of the DelayedExecutor (per L2BEAT). |
| Starkware Multisig 2 (Safe) | `0x015277f49d5dD035A5F3Ce34aD5eBfDBaCA0C6Ec` | Upgrade governor and security admin of the multi-token bridge (read live); proxy governor of most per-token bridges. |
| Starkware Multisig 4 (Safe) | `0x77Dd0cf03e1cCbDC750c9E5FDc34b8A3671f88c5` | Security agent (can enable withdrawal limits) of the multi-token bridge (read live). |
| Starknet operator (EOA) | `0x2C169DFe5fBbA12957Bdd0Ba47d9CEDbFE260CA7` | `isOperator` = true; sends `updateStateKzgDA` (nonce 702,669 on 2026-09-29). |

### 3.2 Token bridges (every L1 bridge of the official registry, plus LORDS)

Each StarkWare bridge is its own escrow: it holds the locked tokens (the ETH bridge holds ETH). The L2 bridge felt is the `toAddress` of the bridge's `LogMessageToL2`. "Delay" is the StarkWare upgrade activation delay read from the proxy on 2026-09-29.

| Token | L1 token | L1 bridge (escrow) | L2 bridge (felt) | Implementation (`identify`) | Delay (s) |
|---|---|---|---|---|---|
| 93 tokens (multi-token) | per token | `0xF5b6Ee2CAEb6769659f6C091D209DfdCaF3F69Eb` | `0x0616757a151c21f9be8775098d591c2807316d992bbc3bb1a5c1821630589256` | StarknetTokenBridge_2.0_6 | 0 |
| ETH | `0x0000000000000000000000000000000000455448` (marker) | `0xae0Ee0A63A2cE6BaeEFFE56e7714FB4EFE48D419` | `0x073314940630fd6dcda0d772d4c972c4e0a9946bef9dabf4ef84eda8ef542b82` | StarknetEthBridge_2.0_4 | 0 |
| STRK | `0xCa14007Eff0dB1f8135f4C25B34De49AB0d42766` | `0xcE5485Cfb26914C5dcE00B9BAF0580364daFC7a4` | `0x0594c1582459ea03f77deaf9eb7e3917d6994a03c13405ba42867f83d85f085d` | StarknetERC20Bridge_2.0_5 | 0 |
| USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | `0xF6080D9fbEEbcd44D89aFfBFd42F098cbFf92816` | `0x05cd48fccbfd8aa2773fe22c217e808319ffcc1c5a6a463f7d8fa2da48218196` | StarknetERC20Bridge_2.0_5 | 259200 |
| USDT | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | `0xbb3400F107804DFB482565FF1Ec8D8aE66747605` | `0x074761a8d48ce002963002becc6d9c3dd8a2a05b1075d55e5967f42296f16bd0` | StarknetERC20Bridge_2.0_5 | 259200 |
| DAI | `0x6B175474E89094C44Da98b954EedeAC495271d0F` | `0xCA14057f85F2662257fd2637FdEc558626bCe554` | `0x07754236934aeaf4c29d287b94b5fde8687ba7d59466ea6b80f3f57d6467b7d6` | StarknetTokenBridge_2.0_4 | 259200 |
| DAI (v0) | `0x6B175474E89094C44Da98b954EedeAC495271d0F` | gateway `0x9F96fE0633eE838D0298E8b8980E6716bE81388d`; **escrow `0x0437465dfb5B79726e35F08559B0cBea55bb585C`** | `0x075ac198e734e289a6892baa8dd14b21095f13bf8401900f5349d5569c3f6e60` | MakerDAO `L1DAIBridge` (immutable, closed) | n/a |
| wstETH | `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0` | `0xBf67F59D2988A46FBFF7ed79A621778a3Cd3985B` | `0x0088eedbe2fe3918b69ccb411713b7fa72079d4eddf291103ccbe41e78a9615c` | StarknetERC20Bridge_2.0_5 | 259200 |
| rETH | `0xae78736Cd615f374D3085123A210448E74Fc6393` | `0xcf58536D6Fab5E59B654228a5a4ed89b13A876C2` | `0x0078da8023b3c08e5a41540a34f7c385fd4f4540d5668f1be3ede0d3bb1b9d4d` | StarknetERC20Bridge_2.0_5 | 259200 |
| UNI | `0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984` | `0xf76e6bF9e2df09D0f854F045A3B724074dA1236B` | `0x04fe90c0c4594b4a5ce3031a4bbdfbc7c046b4b9d7cf31b79647540c85b8ec79` | StarknetERC20Bridge_2.0_5 | 0 |
| FRAX | `0x853d955aCEf822Db058eb8505911ED77F175b99e` | `0xDc687e1E0B85CB589b2da3C47c933De9Db3d1ebb` | `0x006646a87b8e9e51a893c52facd89f99539a152b96e72daee6a7a3734aa5299a` | StarknetERC20Bridge_2.0_5 | 0 |
| FXS | `0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0` | `0x66ba83ba3D3AD296424a2258145d9910E9E40B7C` | `0x06bf25c0911c6c63abfe3600428144d0d0dbf8b7bfbc44306a3386aa95a24296` | StarknetERC20Bridge_2.0_5 | 0 |
| sfrxETH | `0xac3E018457B222d93114458476f3E3416Abbe38F` | `0xd8E8531fdD446DF5298819d3Bc9189a5D8948Ee8` | `0x06dcc61c4cf056ff42a8f4b8635c207e3da73332282aa2132058022520fa0179` | StarknetERC20Bridge_2.0_5 | 0 |
| LUSD | `0x5f98805A4E8be255a32880FDeC7F6728C6568bA0` | `0xF3F62F23dF9C1D2C7C63D9ea6B90E8d24c7E3DF5` | `0x05841ed9b790719b61dc98826246a7a3012dd35b0ed728e3c455af2647385c80` | StarknetERC20Bridge_2.0_5 | 0 |
| R | `0x183015a9bA6fF60230fdEaDc3F43b3D788b13e21` | `0xb27d0dCAFd63db302C155c8864886f33BD2a41E5` | `0x00b0cefce685e321eba324fac1c8e2db768892bc1ddb8375fe40fd269fa69fb2` | StarknetERC20Bridge_2.0_5 | 0 |
| WBTC | `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599` | `0x283751A21eafBFcD52297820D27C1f1963D9b5b4` | `0x07aeec4870975311a7396069033796b61cd66ed49d22a786cba12a8d76717302` | StarknetTokenBridge_2.0_6-halt (**halted**) | 0 |
| SolvBTC | `0x7A56E1C57C7475CCf742a1832B028F0456652F97` | `0xA86b9b9c58d4f786F8ea89356c9c9Dde9432Ab10` | `0x032c68653622292bedf0ed6d941888a01d3923c7f4eb633a0c08c5497a1f5f58` | StarknetTokenBridge_2.0_6-halt (**halted**) | 0 |
| LINK | `0x514910771AF9Ca656af840dff83E8264EcF986CA` | `0x9FaDA9F29492Af64A852f35EAfd957b790B7ea7E` | `0x0028db8d8b55770675e2ea79382290772368d88b1f9b83eb3e956700447735bc` | StarknetTokenBridge_2.0_5 | 259200 |
| tBTC | `0x18084fbA666a33d37592fA2633fD49a74DD93a88` | `0x2111A49ebb717959059693a3698872a0aE9866b9` | `0x067eb1988556edd7543a3c9ee24cc078be35fd49f0b7f264cc0434aeb6dfb09e` | StarknetTokenBridge_2.0_6 | 259200 |
| AAVE | `0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9` | `0x3cDe3eE221aD64d096C92e0F750Feb8A750519A8` | `0x07b8093075fe02cd1e596f1a6bcb2aea1ff84698e1cec42012336f27fc976d87` | StarknetTokenBridge_2.0_6 | 691200 |
| ENA | `0x57e114B691Db790C35207b2e685D4A43181e6061` | `0xEa90D8aE0Fe18a8aF72E57EFDDfE819aa96f244E` | `0x05e2b3bbf0fe1a2547ba6c55fb5888ee8bd7d7e3e773cdda19d6174749547caf` | StarknetTokenBridge_2.0_6 | 691200 |
| ZRO | `0x6985884C4392D348587B19cb9eAAf157F13271cd` | `0x52c65B6795216c4D76fAcACdE8B5f4BAd2c9b9d7` | `0x04b61b603821164c38f3f3cf552a24b3d7fd0710d40d84a0dcf765bb625d0f01` | StarknetTokenBridge_2.0_6 | 691200 |
| USR | `0x66a1E37c9b0eAddca17d3662D6c05F4DECf3e110` | `0x6F3229B9056bC42F147f309B10877cC5919EeFd5` | `0x07a17b56fb56830807c1f59faf8c3e20a1d48292b018b4f5ef5d9e349ae7013e` | StarknetTokenBridge_2.0_6 | 691200 |
| pumpBTC | `0xF469fBD2abcd6B9de8E169d128226C0Fc90a012e` | `0x9aAA37e5bf214E6446Bb7f1690876410C996860e` | `0x00c0b5dc25ae1a0f11f459cb2b8a43faaa7047e6f8bde3ea786e7417faf780d9` | StarknetTokenBridge_2.0_6 | 691200 |
| LBTC | `0x8236a87084f8B84306f72007F36F2618A5634494` | `0x96C8AE2AC9A5cd5fC354e375dB4d0ca75fc0685e` | `0x0239eee60e6d0bed42315ac74a1fc43db8074646d4d2a0a9e6fa5272685a0eb5` | StarknetTokenBridge_2.0_6 | 0 |
| uniBTC | `0x004E9C3EF86bc1ca1f0bB5C7662861Ee93350568` | `0x4ea91eD5A1f5e2Be18791F210C52d0fe285744d5` | `0x006f04d4e0dd89ee364650ae5264e7cfeb8fd567913d3be9a332e50f2b612810` | StarknetTokenBridge_2.0_6 | 0 |
| enzoBTC | `0x6A9A65B84843F5fD4aC9a0471C4fc11AFfFBce4a` | `0x30A155a161f6b5f4C0226C3744C4d69eEfDbf483` | `0x01cdc690d569bd29f07fcf76d775289c3f6daa717e43de9a7faa16acc797c6c4` | StarknetTokenBridge_2.0_6 | 0 |
| brBTC | `0x2eC37d45FCAE65D9787ECf71dc85a444968f6646` | `0x1febb800fa36938Fdb6131c643C72dfAB91633bb` | `0x061bf111d6e862a749f6a5c62ab6ecf76795a83eca92bb0187a99f43818d42b9` | StarknetTokenBridge_2.0_6 | 0 |
| mRe7BTC | `0x9FB442d6B612a6dcD2acC67bb53771eF1D9F661A` | `0x7a095101eF5c7a66056f801335F8605d3b2452a5` | `0x0639069b8c2daef5a245fc82b7be76f44dad088f078a99c17eb5f157af7463cc` | StarknetTokenBridge_2.0_6 | 0 |
| GGMT | `0x76aAb5FD2243d99EAc92d4d9EBF23525d3ACe4Ec` | `0x448Acb9F2e57a409a60Cf8901EA4123b6E2EC253` | `0x033cfdafdb07aa0f829f36ed981cab9b6c3dd7c0e2ca9272dcf9ae221dbf1964` | StarknetTokenBridge_2.0_6 | 0 |
| EURC | `0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c` | `0x00b0466f8dC04B0782DbF1A1DfdCe333F0Dd082B` | `0x01f15367623cb89b2a8f745dd04744080630ce43fd02f4591fe445d4fedd94aa` | StarknetTokenBridge_2.0_6 | 0 |
| EUROP | `0x888883b5F5D21fb10Dfeb70e8f9722B9FB0E5E51` | `0x4c4eE256fFE216a23A39827bcd4C5CB0b6cf11F3` | `0x0278efd5184f23116a9058cc4c4e34b30b4ee959535d4fad15d103e71f7d8a3e` | StarknetTokenBridge_2.0_6 | 0 |
| LORDS (custom, not in the registry) | `0x686f2404e77Ab0d9070a46cdfb0B7feCDD2318b0` | `0x023A2aAc5d0fa69E3243994672822BA43E34E5C9` | `0x07c76a71952ce3acd1f953fd2a3fda8564408b821ff367041c89f44526076633` | immutable (`starknet()` = the core) | n/a |

The multi-token bridge serves 93 registry tokens (for example WETH, POL, USDe, EIGEN, PEPE); resolve any token with `StarkgateRegistry.getBridge(token)`. Balances read on 2026-09-29: USDC bridge 4,806,399 USDC; DAI v0 escrow 373,908 DAI; LORDS bridge 114,656,860 LORDS; WBTC bridge 0.00023605 WBTC and SolvBTC bridge 0.0516 SolvBTC (both swept by the halt).

### 3.3 Look-alike contracts that are NOT Starknet (Paradex, a separate Starknet-stack chain)

| Contract | Address | What it is |
|---|---|---|
| Paradex core | `0xF338cad020D506e8e3d9B4854986E0EcE6C23640` | Same core implementation as Starknet (`0x9961D34D3baE6914635c882e8FE382e14E0F172A`); emits the same `LogMessageToL2` / `ConsumedMessageToL1` topics. |
| Paradex token bridge | `0xE3cbE3A636AB6A754e9e41B12b09d09Ce9E53Db3` | `StarkWare_StarknetTokenBridge_2.0_5`; bridges DIME (`0xb32E10022FFBeDfE10bc818a1C7e67D9d87e0fa7`) and emits `DepositWithMessage` / `Withdrawal`. |
| ETH bridge that messages the Paradex core | `0x45B79622C095ab834b9C8dC71013ed13B39F1B8D` | `StarkWare_StarknetEthBridge_2.0_5`; its `LogMessageToL2` is emitted by the Paradex core (read from a live receipt). Not listed on the L2BEAT Paradex page (unverified name). |

---

## 4. Cross-chain summary

| Chain | ID | Starknet core | Manager / Registry | Multi-token bridge | Per-token bridges (31) | DAI v0 gateway / escrow | LORDS bridge |
|---|---|---|---|---|---|---|---|
| **Ethereum** | 1 | ✅ `0xc662c410C0ECf747543f5bA90660f6ABeBD9C8c4` | ✅ `0x0c5aE94f8939182F2D06097025324D1E537d5B60` / `0x1268cc171c54F2000402DfF20E93E60DF4c96812` | ✅ `0xF5b6Ee2CAEb6769659f6C091D209DfdCaF3F69Eb` | ✅ §3.2 | ✅ | ✅ |
| Base | 8453 | — | — | — | — | — | — |
| Arbitrum One | 42161 | — | — | — | — | — | — |
| Optimism | 10 | — | — | — | — | — | — |
| Polygon PoS | 137 | — | — | — | — | — | — |
| BNB Smart Chain | 56 | — | — | — | — | — | — |
| Avalanche C-Chain | 43114 | — | — | — | — | — | — |
| Robinhood Chain | 4663 | — | — | — | — | — | — |

"—" means `eth_getCode` returned `0x` with nonce 0 on 2026-09-29 at the Ethereum addresses of the core, the Manager, the Registry, the verifier, the multi-token bridge and all 32 registry bridges. Neither the Starknet docs nor the registry list any L1 contract outside Ethereum. The StarkGate topic0s do appear on other chains, but only from unrelated contracts (§6, item 9).

The counterparty chain, Starknet (`SN_MAIN`), is outside the eight. Starknet also appears as CCTP domain 25 (see the `cctp` reference); that USDC path does not use StarkGate.

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade authority (read live unless noted) |
|---|---|---|---|
| Starknet core | StarkWare legacy proxy | implementation in slot `0x177667240aeeea7e35eabe3a35e18306f336219e1386f7710a6bf8783f761b24`; `proxyIsGovernor(address)` answers | Security Council `0x15e8c684FD095d4796A0c0CF678554F4c1C7C361` and DelayedExecutor `0xCA112018fEB729458b628AadC8f996f9deCbCa0c` (both `proxyIsGovernor` = true). Upgrade activation delay 0 s. |
| ETH bridge | StarkWare legacy proxy | `proxyIsGovernor(address)` answers | Security Council and DelayedExecutor (both true). Delay 0 s. |
| STRK bridge, DAI bridge, multi-token bridge, Manager, Registry | StarkWare ProxyV5 (roles, 8051-byte proxy) | `proxyIsGovernor` reverts; `isUpgradeGovernor(address)` answers | STRK: Security Council and DelayedExecutor. DAI, multi-token, Manager, Registry: Starkware Multisig 2 `0x015277f49d5dD035A5F3Ce34aD5eBfDBaCA0C6Ec` (multi-token and DAI read live; Manager and Registry per L2BEAT). |
| USDC, USDT, wstETH, rETH, UNI, FRAX, FXS, sfrxETH, R bridges | StarkWare legacy proxy | `proxyIsGovernor(address)` | Starkware Multisig 2 (USDC read live; others per L2BEAT). |
| LUSD bridge | StarkWare legacy proxy | `proxyIsGovernor(address)` | **EOA** `0x5751a83170BeA11fE7CdA5D599B04153C021f21A` (`proxyIsGovernor` = true; nonce 1,301). |
| SolvBTC bridge (halted) | StarkWare ProxyV5 | `isUpgradeGovernor(address)` | **EOA** `0x5751a83170BeA11fE7CdA5D599B04153C021f21A` (true). |
| LBTC bridge | StarkWare ProxyV5 | `isUpgradeGovernor(address)` | **EOA** `0xF689688640E88160c07C6FC5cc63039F29EDe86b` (true; nonce 561). |
| Other 2024+ single-token bridges (AAVE, ENA, ZRO, USR, pumpBTC, uniBTC, enzoBTC, brBTC, mRe7BTC, GGMT, EURC, EUROP, tBTC, LINK) | StarkWare ProxyV5 (7561-byte proxy) | `isUpgradeGovernor(address)` | Not read for each bridge (unverified); the upgrade delays in §3.2 were read live. |
| DAI v0 gateway, DAI v0 escrow, LORDS bridge | **Immutable** | implementation slot = 0; `identify()` reverts | MakerDAO `wards` (`Rely`/`Deny`) on the gateway and escrow; none on LORDS. |

Implementation classes read live on 2026-09-29: `StarknetERC20Bridge_2.0_5` = `0x6ad74D4B79A06A492C288eF66Ef868Dd981fdC85` (STRK, USDC, USDT, wstETH, rETH, UNI, FRAX, FXS, sfrxETH, LUSD, R); `StarknetEthBridge_2.0_4` = `0x95ff25A59Dc9c5A41cF0709dc916041E5dC7fd95`; `StarknetTokenBridge_2.0_4` = `0x5cd6847aCb72a7d61342e611FB31d4b59942379c` (DAI); `StarknetTokenBridge_2.0_5` = `0x264c70F10261B523aEA6B5B258130401cd4df778` (LINK); `StarknetTokenBridge_2.0_6` = `0xf39d314C5aD7DC88958116dfA7d5ac095d563Aff` (multi-token and 14 single-token bridges); haltable `2.0_6-halt` = `0xE0D1fab527A85D955d4c05323250367E61bA3f18` (WBTC) and `0x205Fef0daB48D83CbA6888C5F050FeE36C4762B7` (SolvBTC).

**Halt.** The haltable class lets the app governor call `signalTokenHalt`, then `completeTokenHalt`, which sweeps the escrow to a clearing address. There is no logic to resume. L2BEAT records `tokenHaltCompleted` for WBTC and SolvBTC, and the live balances agree (§3.2). A `TokenHaltCompleted` on any other bridge means its escrow was emptied.

---

## 6. Detection invariants & gotchas

1. **Join a deposit by `(bridge, nonce)`.** `Deposit.nonce` = `LogMessageToL2.nonce` in the same transaction; `ConsumedMessageToL2.nonce` later confirms that Starknet consumed it. The Starknet transaction hash is not on L1.
2. **A withdrawal has no L1 key.** `Withdrawal(recipient, token, amount)` plus `ConsumedMessageToL1` in the same transaction is all that L1 shows. The `LogMessageToL1` with the same payload came earlier, in a state-update transaction. Match on `(L2 bridge felt, recipient, token, amount)`; repeated identical withdrawals are indistinguishable on L1.
3. **`withdraw` is permissionless.** The caller (`tx.from`) is often a relayer or a batching contract, not the recipient. Use `Withdrawal.recipient`.
4. **Double emission on the legacy classes.** The legacy `deposit(uint256,uint256)` on the `StarknetERC20Bridge_2.0_5` and `StarknetEthBridge_2.0_4` bridges emits `Deposit` **and** `LogDeposit`. Count one.
5. **ETH value is in `msg.value`, not in a Transfer.** An ETH deposit carries `amount + fee`; the fee (wei) moves on to the core. An ETH withdrawal pays the recipient with an internal value transfer. Read the amount from `Deposit.amount` / `Withdrawal.amount`. The ETH `token` field is the marker `0x0000000000000000000000000000000000455448`.
6. **Token deposits carry a fee in `msg.value` too** (at least 10^12 wei on mainnet, at most 10^16 wei). It is not part of the bridged amount.
7. **`sender` can be a contract.** Routers and aggregators call `deposit` (one sample transaction came through an aggregator that moved USDT to an intermediate contract first). `Deposit.sender` is the direct caller.
8. **Paradex looks identical.** The Paradex core and bridges (§3.3) run the same code and emit the same topic0s. In the pinned window every `DepositWithMessage` on Ethereum (9) came from them, not from Starknet. Always filter on the Starknet emitters.
9. **Generic topic0 collisions.** `Deposit(address,address,uint256,uint256,uint256,uint256)` and `Withdrawal(address,address,uint256)` are common signatures. In the pinned window they were emitted on Base, Optimism, Polygon, BNB and Avalanche by contracts that do not answer `identify()` (not StarkWare contracts), and on Ethereum by seven non-StarkGate `Withdrawal` emitters. Never key on topic0 alone.
10. **DAI has two withdrawal paths.** `StarkgateRegistry.getWithdrawalBridges(DAI)` returns the DAI v0 gateway and the current DAI bridge. DAI v0 is paid out of the escrow `0x0437465dfb5B79726e35F08559B0cBea55bb585C`, not out of the gateway; the gateway emits `LogWithdrawal`, not `Withdrawal`.
11. **Admin triggers to monitor:** `ImplementationAdded` (a scheduled upgrade — with delay 0 on most bridges it can execute in the same block), `ImplementationUpgraded`, `SetL2TokenBridge`, `TokenHaltSignalled` / `TokenHaltCompleted`, `WithdrawalLimitEnabled` / `Disabled`, `RoleGranted` / `RoleRevoked`, core `ProgramHashChanged` / `ConfigHashChanged` / `LogOperatorAdded`, and the DAI escrow `Approve`.
12. **EOA upgrade keys.** The LBTC bridge (EOA `0xF689688640E88160c07C6FC5cc63039F29EDe86b`) and the SolvBTC and LUSD bridges (EOA `0x5751a83170BeA11fE7CdA5D599B04153C021f21A`) can be upgraded by a single key with no time lock.
13. **Large-transfer trigger:** `Deposit.amount` and `Withdrawal.amount` per `token` (decimals of the L1 token). For a drain, watch the ERC-20 balance of each bridge in §3.2 and the ETH balance of the ETH bridge.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Starknet core: messaging topics =====
TOPIC_LOG_MESSAGE_TO_L2              = '\xdb80dd488acf86d17c747445b0eabb5d57c541d3bd7b6b87af987858e5066b2b'
TOPIC_CONSUMED_MESSAGE_TO_L1         = '\x7a06c571aa77f34d9706c51e5d8122b5595aebeaa34233bfe866f22befb973b1'
TOPIC_LOG_MESSAGE_TO_L1              = '\x4264ac208b5fde633ccdd42e0f12c3d6d443a4f3779bbf886925b94665b63a22'
TOPIC_CONSUMED_MESSAGE_TO_L2         = '\x9592d37825c744e33fa80c469683bbd04d336241bb600b574758efd182abe26a'
TOPIC_MESSAGE_TO_L2_CANCEL_STARTED   = '\x2e00dccd686fd6823ec7dc3e125582aa82881b6ff5f6b5a73856e1ea8338a3be'
TOPIC_MESSAGE_TO_L2_CANCELED         = '\x8abd2ec2e0a10c82f5b60ea00455fa96c41fd144f225fcc52b8d83d94f803ed8'
TOPIC_LOG_STATE_UPDATE               = '\xd342ddf7a308dec111745b00315c14b7efb2bdae570a6856e088ed0c65a3576c'
TOPIC_PROGRAM_HASH_CHANGED           = '\x600a61c1b32ac42fb2fe76e8fc7582a98106668fc16dcd85567cd3937363e49b'
TOPIC_CONFIG_HASH_CHANGED            = '\x393c6beb5756a944b2967f15f31ff671e312e945d7a84fd3bdcfd6b408b2dc79'
TOPIC_LOG_OPERATOR_ADDED             = '\x50a18c352ee1c02ffe058e15c2eb6e58be387c81e73cc1e17035286e54c19a57'
-- ===== StarkWare proxy =====
TOPIC_IMPLEMENTATION_UPGRADED        = '\xff14288d542bc1c1d15a652cb52af735f065c0c9d70b48e454a203c260733544'
TOPIC_IMPLEMENTATION_ADDED           = '\x723a7080d63c133cf338e44e00705cc1b7b2bde7e88d6218a8d62710a329ce1b'
TOPIC_FINALIZED_IMPLEMENTATION       = '\xc13b75a5f14b69ebdc2431a5d475b3bff371abe251b5064144306fbd9c4de35c'
-- ===== StarkGate bridges =====
TOPIC_SG_DEPOSIT                     = '\x5f971bd00bf3ffbca8a6d72cdd4fd92cfd4f62636161921d1e5a64f0b64ccb6d'
TOPIC_SG_DEPOSIT_WITH_MESSAGE        = '\x2203a49c69f1a46c1164f5e4a30643dd77b7c59c0ff9bc433256048365c247f1'
TOPIC_SG_WITHDRAWAL                  = '\x2717ead6b9200dd235aad468c9809ea400fe33ac69b5bfaa6d3e90fc922b6398'
TOPIC_SG_DEPOSIT_CANCEL_REQUEST      = '\x8f3da3ce93acd45e015b069c8f032d37be93dc9efcaaeda368aa9ca74f64c30a'
TOPIC_SG_DEPOSIT_RECLAIMED           = '\x50485fb0face2cfd73784044ab4191986b4a6713f01854414e2331a6bb41837d'
TOPIC_SG_DEPOSIT_WITH_MSG_RECLAIMED  = '\xa465a02eedf06ceffd1d99159ad98c5d8fa7f17b870eb22e0bfcec06398a8f73'
TOPIC_SG_SET_L2_TOKEN_BRIDGE         = '\x90fc3f39f8e4669d1bf5f9038707949f8af42a973f62988143be0fa7c3997f18'
TOPIC_SG_WITHDRAWAL_LIMIT_ENABLED    = '\xe2deca319add01142d26def2de47e64bf1fdc70e6f90c13a1862a48bdaaa7cfd'
TOPIC_SG_TOKEN_HALT_SIGNALLED        = '\xc7e24f95ec7b87fb2168f2ab0eb1bec907984818a0930c9886f118f94cbc5a39'
TOPIC_SG_TOKEN_HALT_COMPLETED        = '\x86de951cb81f3e6fe625737b6a21bbe80650de4d1cc8a9501d1595d6d14755d1'
TOPIC_ROLE_GRANTED                   = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
-- legacy / DAI v0 / LORDS
TOPIC_SG_LOG_DEPOSIT_LEGACY          = '\x5b5dbc6c64043a15d3fe6943a6e443a826b78755edc257b2ec890c022225dbcf'
TOPIC_LOG_WITHDRAWAL                 = '\xb4214c8c54fc7442f36d3682f59aebaf09358a4431835b30efb29d52cf9e1e91'
TOPIC_DAI_V0_LOG_DEPOSIT             = '\x9dbb0e7dda3e09710ce75b801addc87cf9d9c6c581641b3275fca409ad086c62'
TOPIC_DAI_V0_LOG_CANCEL_DEPOSIT      = '\x27342a36c014a937136f67690b80039f954cc7acd1d6a2f5bca3f3d3e7b94837'
TOPIC_DAI_ESCROW_APPROVE             = '\x6e11fb1b7f119e3f2fa29896ef5fdf8b8a2d0d4df6fe90ba8668e7d8b2ffa25e'

-- ===== Selectors =====
SEL_SG_DEPOSIT                       = '\x0efe6a8b'
SEL_SG_DEPOSIT_WITH_MESSAGE          = '\xbe58b18e'
SEL_SG_DEPOSIT_LEGACY                = '\xe2bbb158'
SEL_SG_WITHDRAW                      = '\x69328dec'
SEL_SG_WITHDRAW_LEGACY               = '\x00f714ce'
SEL_SG_DEPOSIT_CANCEL_REQUEST        = '\xa6d1d6c6'
SEL_SG_DEPOSIT_RECLAIM               = '\x23205c52'
SEL_SG_SET_L2_TOKEN_BRIDGE           = '\x7fc2ab3e'
SEL_SG_COMPLETE_TOKEN_HALT           = '\xb1ed16a4'
SEL_SN_SEND_MESSAGE_TO_L2            = '\x3e3aa6c5'
SEL_SN_CONSUME_MESSAGE_FROM_L2       = '\x2c9dd5c0'
SEL_SN_UPDATE_STATE_KZG_DA           = '\x507ee528'
SEL_SN_SET_PROGRAM_HASH              = '\xe87e7332'
SEL_PROXY_ADD_IMPLEMENTATION         = '\x5e3a97e7'
SEL_PROXY_UPGRADE_TO                 = '\x7147855d'
SEL_IDENTIFY                         = '\xeeb72866'
SEL_REGISTRY_GET_BRIDGE              = '\xf44c7c8f'

-- ===== StarkWare proxy slots =====
STARKWARE_IMPL_SLOT                  = '\x177667240aeeea7e35eabe3a35e18306f336219e1386f7710a6bf8783f761b24'
STARKWARE_UPGRADE_DELAY_SLOT         = '\xc21dbb3089fcb2c4f4c6a67854ab4db2b0f233ea4b21b21f912d52d18fc5db1f'
STARKWARE_FINALIZED_SLOT             = '\x7d433c6f837e8f93009937c466c82efbb5ba621fae36886d0cac433c5d0aa7d2'

-- ===== Starknet ids (felts, 32 bytes) =====
SN_HANDLE_TOKEN_DEPOSIT              = '\x01b64b1b3b690b43b9b514fb81377518f4039cd3e4f4914d8a6bdf01d679fb19'
SN_HANDLE_DEPOSIT_WITH_MESSAGE       = '\x008bce41827dd5484d80312a2e43bc42a896e3fcf75bf84c2b49339168dfa00a'
SN_HANDLE_DEPOSIT_LEGACY             = '\x02d757788a8d8d6f21d1cd40bce38a8222d70654214e96ff95d8086e684fbee5'
SN_L2_MULTI_BRIDGE                   = '\x0616757a151c21f9be8775098d591c2807316d992bbc3bb1a5c1821630589256'
SN_L2_ETH_BRIDGE                     = '\x073314940630fd6dcda0d772d4c972c4e0a9946bef9dabf4ef84eda8ef542b82'
SN_L2_STRK_BRIDGE                    = '\x0594c1582459ea03f77deaf9eb7e3917d6994a03c13405ba42867f83d85f085d'
SN_L2_USDC_BRIDGE                    = '\x05cd48fccbfd8aa2773fe22c217e808319ffcc1c5a6a463f7d8fa2da48218196'
SN_L2_USDT_BRIDGE                    = '\x074761a8d48ce002963002becc6d9c3dd8a2a05b1075d55e5967f42296f16bd0'
STARKGATE_ETH_TOKEN_MARKER           = '\x0000000000000000000000000000000000455448'

-- ===== Ethereum (chain ID 1) =====
ETH_STARKNET_CORE                    = '\xc662c410c0ecf747543f5ba90660f6abebd9c8c4'
ETH_STARKNET_CORE_IMPL               = '\x9961d34d3bae6914635c882e8fe382e14e0f172a'
ETH_STARKGATE_MANAGER                = '\x0c5ae94f8939182f2d06097025324d1e537d5b60'
ETH_STARKGATE_REGISTRY               = '\x1268cc171c54f2000402dff20e93e60df4c96812'
ETH_STARKGATE_MULTI_BRIDGE           = '\xf5b6ee2caeb6769659f6c091d209dfdcaf3f69eb'
ETH_SHARP_VERIFIER                   = '\x47312450b3ac8b5b8e247a6bb6d523e7605bdb60'
ETH_STARKGATE_ETH                    = '\xae0ee0a63a2ce6baeeffe56e7714fb4efe48d419'
ETH_STARKGATE_STRK                   = '\xce5485cfb26914c5dce00b9baf0580364dafc7a4'
ETH_STARKGATE_USDC                   = '\xf6080d9fbeebcd44d89affbfd42f098cbff92816'
ETH_STARKGATE_USDT                   = '\xbb3400f107804dfb482565ff1ec8d8ae66747605'
ETH_STARKGATE_DAI                    = '\xca14057f85f2662257fd2637fdec558626bce554'
ETH_STARKGATE_DAI_V0_GATEWAY         = '\x9f96fe0633ee838d0298e8b8980e6716be81388d'
ETH_STARKGATE_DAI_V0_ESCROW          = '\x0437465dfb5b79726e35f08559b0cbea55bb585c'
ETH_STARKGATE_WSTETH                 = '\xbf67f59d2988a46fbff7ed79a621778a3cd3985b'
ETH_STARKGATE_RETH                   = '\xcf58536d6fab5e59b654228a5a4ed89b13a876c2'
ETH_STARKGATE_UNI                    = '\xf76e6bf9e2df09d0f854f045a3b724074da1236b'
ETH_STARKGATE_FRAX                   = '\xdc687e1e0b85cb589b2da3c47c933de9db3d1ebb'
ETH_STARKGATE_FXS                    = '\x66ba83ba3d3ad296424a2258145d9910e9e40b7c'
ETH_STARKGATE_SFRXETH                = '\xd8e8531fdd446df5298819d3bc9189a5d8948ee8'
ETH_STARKGATE_LUSD                   = '\xf3f62f23df9c1d2c7c63d9ea6b90e8d24c7e3df5'
ETH_STARKGATE_R                      = '\xb27d0dcafd63db302c155c8864886f33bd2a41e5'
ETH_STARKGATE_WBTC                   = '\x283751a21eafbfcd52297820d27c1f1963d9b5b4'
ETH_STARKGATE_SOLVBTC                = '\xa86b9b9c58d4f786f8ea89356c9c9dde9432ab10'
ETH_STARKGATE_LINK                   = '\x9fada9f29492af64a852f35eafd957b790b7ea7e'
ETH_STARKGATE_TBTC                   = '\x2111a49ebb717959059693a3698872a0ae9866b9'
ETH_STARKGATE_AAVE                   = '\x3cde3ee221ad64d096c92e0f750feb8a750519a8'
ETH_STARKGATE_ENA                    = '\xea90d8ae0fe18a8af72e57efddfe819aa96f244e'
ETH_STARKGATE_ZRO                    = '\x52c65b6795216c4d76facacde8b5f4bad2c9b9d7'
ETH_STARKGATE_USR                    = '\x6f3229b9056bc42f147f309b10877cc5919eefd5'
ETH_STARKGATE_PUMPBTC                = '\x9aaa37e5bf214e6446bb7f1690876410c996860e'
ETH_STARKGATE_LBTC                   = '\x96c8ae2ac9a5cd5fc354e375db4d0ca75fc0685e'
ETH_STARKGATE_UNIBTC                 = '\x4ea91ed5a1f5e2be18791f210c52d0fe285744d5'
ETH_STARKGATE_ENZOBTC                = '\x30a155a161f6b5f4c0226c3744c4d69eefdbf483'
ETH_STARKGATE_BRBTC                  = '\x1febb800fa36938fdb6131c643c72dfab91633bb'
ETH_STARKGATE_MRE7BTC                = '\x7a095101ef5c7a66056f801335f8605d3b2452a5'
ETH_STARKGATE_GGMT                   = '\x448acb9f2e57a409a60cf8901ea4123b6e2ec253'
ETH_STARKGATE_EURC                   = '\x00b0466f8dc04b0782dbf1a1dfdce333f0dd082b'
ETH_STARKGATE_EUROP                  = '\x4c4ee256ffe216a23a39827bcd4c5cb0b6cf11f3'
ETH_LORDS_BRIDGE                     = '\x023a2aac5d0fa69e3243994672822ba43e34e5c9'
-- governance
ETH_STARKWARE_SECURITY_COUNCIL       = '\x15e8c684fd095d4796a0c0cf678554f4c1c7c361'
ETH_STARKWARE_DELAYED_EXECUTOR       = '\xca112018feb729458b628aadc8f996f9decbca0c'
ETH_STARKWARE_MULTISIG_1             = '\x83c0a700114101d1283d1405e2c8f21d3f03e988'
ETH_STARKWARE_MULTISIG_2             = '\x015277f49d5dd035a5f3ce34ad5ebfdbaca0c6ec'
ETH_STARKWARE_MULTISIG_4             = '\x77dd0cf03e1ccbdc750c9e5fdc34b8a3671f88c5'
ETH_STARKNET_OPERATOR_EOA            = '\x2c169dfe5fbba12957bdd0ba47d9cedbfe260ca7'
ETH_LBTC_BRIDGE_GOVERNOR_EOA         = '\xf689688640e88160c07c6fc5cc63039f29ede86b'
ETH_SOLVBTC_LUSD_GOVERNOR_EOA        = '\x5751a83170bea11fe7cda5d599b04153c021f21a'
-- look-alikes to EXCLUDE (Paradex, not Starknet)
ETH_PARADEX_CORE                     = '\xf338cad020d506e8e3d9b4854986e0ece6c23640'
ETH_PARADEX_TOKEN_BRIDGE             = '\xe3cbe3a636ab6a754e9e41b12b09d09ce9e53db3'
ETH_PARADEX_ETH_BRIDGE               = '\x45b79622c095ab834b9c8dc71013ed13b39f1b8d'
-- Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain: no Starknet contracts
```

---

## 8. Verification & sources

How the constants were verified (2026-09-29):

- **Topics and selectors:** recomputed as `keccak256(signature)` from the canonical Solidity: `starkgate-contracts` `src/solidity/StarknetTokenBridge.sol`, `LegacyBridge.sol`, `StarknetEthBridge.sol`, `StarknetERC20Bridge.sol`, `StarkgateManager.sol`, `StarkgateRegistry.sol`, `StarkgateConstants.sol`, and its bundled `starkware/solidity` (`upgrade/ProxyV5.sol`, `StorageSlots.sol`, `libraries/AccessControl.sol`, legacy proxy and bridge ABIs); `cairo-lang` `IStarknetMessagingEvents.sol`, `StarknetMessaging.sol`, `Starknet.sol`, `Output.sol`, `components/Governance.sol`, `components/Operator.sol`; MakerDAO `L1DAIBridge.sol`. The deployed ABIs of the core, the bridge classes, the haltable class, the DAI v0 gateway, its escrow and the LORDS bridge were cross-checked against the verified ABIs in L2BEAT's discovery data. Live receipts confirmed `Deposit`, `LogMessageToL2`, `ConsumedMessageToL1`, `Withdrawal`, `LogMessageToL1`, `LogStateUpdate` and `LogStateTransitionFact`.
- **Sample transactions read:** ETH deposit `0x23debd71b0029c5a56e1f4e405204302b31f8859d808fca97151fa294a463fd6` (`deposit(address,uint256,uint256)`, value = amount + fee, `LogMessageToL2` then `Deposit`); STRK deposit `0x4a018f8de0b73d8fb90eaf1ecb8ced365f047415a291e3dd9769e9dcd4c855b8` (STRK `Transfer` user → bridge); USDT deposit through an aggregator `0x98cd791a86d453aac4bf07f4e54733889238c84be2c0e0948f160c68515b0883`; ETH withdrawal `0x24e872ecc1a0aa8e59841591b274b14d354dfb0f2b8034b5fc676354caf58fa8` (`withdraw(address,uint256,address)` sent by a third party; `ConsumedMessageToL1` then `Withdrawal`); state update `0xcfaeaf531c3a686fcf78200692a2d2b49747e9a88544a14e379938ea290b89af` (`updateStateKzgDA` from the operator EOA); Paradex deposits `0x31c11101e04f365e86aa51fa19b99e5e4a81bfc80572a38134a498df32747259` and `0xdcba6104d229cd384c684b4f8210bc8303a5b777ed8d95a37b7f553c31d280a3`.
- **Addresses:** the 32 L1 bridges from the official registry (`bridged_tokens/mainnet.json`, 126 entries); core, Manager, Registry, multi-token bridge and verifier from the Starknet docs; all existence-checked with `eth_getCode`; implementations from the StarkWare slot; versions from `identify()`; governors from `proxyIsGovernor` / `isUpgradeGovernor` / `isSecurityAgent` / `isSecurityAdmin`; `StarkgateRegistry.getBridge` and `getWithdrawalBridges` for USDC, ETH, DAI, STRK, USDT, WETH, EURC, WBTC, SolvBTC; the DAI v0 gateway's `escrow()`, `starkNet()`, `l2DaiBridge()`, `isOpen()`; the LORDS bridge's `starknet()`, `l1Token()`, `l2Bridge()`.
- **Chain coverage:** `eth_getCode` = `0x` (nonce 0) on Base, Arbitrum, Optimism, Polygon, BNB, Avalanche and Robinhood Chain for the core, Manager, Registry, verifier, reward supplier, mint manager, the multi-token bridge and all 32 registry bridges. Every other-chain emitter of a StarkGate topic0 in the pinned window reverted on `identify()`.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Ethereum blocks 26072222–26075812):** core `LogMessageToL2` 15, `ConsumedMessageToL1` 123, `LogMessageToL1` 13, `ConsumedMessageToL2` 13, `LogStateUpdate` 19, `MessageToL2CancellationStarted` 0, `MessageToL2Canceled` 0. Bridges: `Deposit` 12 (ETH 5, STRK 5, USDT 1, UNI 1), `Withdrawal` 123 (ETH 117, STRK 2, multi-token 1, USDC 1, USDT 1, wstETH 1), `DepositWithMessage` 0 from Starknet bridges (9 from Paradex), `DepositReclaimed` 0, `DepositCancelRequest` 0, legacy `LogDeposit` 0, `LogWithdrawal` 0, DAI v0 / LORDS `LogDeposit` 0. The other seven chains: no Starknet emitter exists, so no count applies. The 123 consumptions against 13 registrations in the window reflect a backlog: in the prior Ethereum blocks 26050000–26072221 the counts were `LogMessageToL1` 52, `ConsumedMessageToL1` 60, `LogStateUpdate` 110.

Sources opened:
- [starkware-libs/starkgate-contracts](https://github.com/starkware-libs/starkgate-contracts) (branch `SN-v0.14.2`: `src/solidity/`, `.dep/starkware-solidity-dependencies.tar`)
- [starkware-libs/cairo-lang](https://github.com/starkware-libs/cairo-lang) (`src/starkware/starknet/solidity/`, `src/starkware/solidity/components/`)
- [starknet-io/starknet-addresses](https://github.com/starknet-io/starknet-addresses) (`bridged_tokens/mainnet.json`)
- [makerdao/starknet-dai-bridge](https://github.com/makerdao/starknet-dai-bridge) (`contracts/l1/L1DAIBridge.sol`)
- [Starknet docs — chain info and addresses](https://docs.starknet.io/learn/cheatsheets/chain-info) · [StarkGate functions and events](https://docs.starknet.io/learn/cheatsheets/starkgate-reference)
- [L2BEAT discovery data for Starknet](https://github.com/l2beat/l2beat/blob/main/packages/config/src/projects/starknet/discovered.json) · [L2BEAT Paradex page](https://l2beat.com/scaling/projects/paradex)
- Starknet JSON-RPC `starknet_chainId` (public endpoint) for `SN_MAIN`
