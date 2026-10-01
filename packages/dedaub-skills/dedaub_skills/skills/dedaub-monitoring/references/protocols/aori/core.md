# Aori — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, BNB live; v0.4.0 proxy also on Polygon and Avalanche; NOT Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the canonical `aori-io/aori` repository (`master` = v0.3.1, branch `v0.4.0`), the official Aori docs, the live Aori API (`https://api.aori.io/chains`) and the Blockscout explorers. Every topic0 and selector was recomputed as `keccak256(signature)`. Every address was existence-checked with `eth_getCode`. The live wiring was read on chain (`ENDPOINT_ID()`, `peers(eid)`, `isSupportedChain(eid)`, `owner()`, `eip712Domain()`).
**Scope:** the Aori intent-settlement contract: one `Aori` contract per chain that holds the source-side escrow and executes the destination-side fill, with LayerZero v2 messages for settlement and cancellation. Live (release 0.3.1): Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10), BNB Smart Chain (56). The next release (0.4.0, UUPS proxy, one CREATE3 address) is deployed and wired on Ethereum, Base, Arbitrum, Optimism, Polygon PoS (137), BNB and Avalanche C-Chain (43114), but it is not in the official list and it emitted no log in the measured window. **Robinhood Chain (4663) has no Aori contract.** Topics and selectors are chain-agnostic. Addresses are network-specific.

Aori is a peer-to-peer intent protocol. A user (the *offerer*) signs an order. On the source chain the order locks the input tokens in the Aori contract (`Deposit`). On the destination chain a whitelisted solver pays the output tokens to the recipient (`Fill`). The solver then sends a LayerZero settlement message from the destination Aori to the source Aori (`SettleSent`). On arrival the source Aori moves the locked input to the solver's internal balance (`Settle`), and the solver takes it out later (`Withdraw`). A same-chain swap uses the same contract and settles at once.

Three facts to know before you index:

1. **The link key is `orderId` = `keccak256(abi.encode(order))`.** The same `bytes32` is topic1 of `Deposit` and `Cancel` on the source chain and topic1 of `Fill`, `DstHookExecuted` and `CancelSent` on the destination chain. It is on chain on both sides. The order tuple in `Deposit` and `Fill` also carries `srcEid` and `dstEid` (LayerZero endpoint ids, not EVM chain ids).
2. **The v0.3.1 contracts are immutable, and each chain has its own address.** Ethereum `0x0736bdc975af0675b9a045384efed91360d25479`, Base / Arbitrum / Optimism `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6`, BNB `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8`. The same literal address can hold a different Aori build on another chain: `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` is the live v0.3.1 contract on BNB but an unwired v0.3.0 build on Base, Arbitrum and Optimism. Always key on `(chain, address)`.
3. **v0.4.0 changes the topic0 of `Deposit`, `Fill` and `Settle`.** A monitor on the v0.3.1 topics sees nothing from the v0.4.0 proxy `0xa041a8f5d796de4ae21da10e90908549c17d1107`. Keep both topic sets.

---

## 0. Contract families & versions

| Generation (EIP-712 version) | Address | Chains | Status | Proxy? |
|---|---|---|---|---|
| **Aori 0.3.1 (live)** | `0x0736bdc975af0675b9a045384efed91360d25479` | Ethereum | In the official docs and the live API. Active. | No (immutable) |
| **Aori 0.3.1 (live)** | `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6` | Base, Arbitrum, Optimism | In the official docs and the live API. Active. | No (immutable) |
| **Aori 0.3.1 (live)** | `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` | BNB (also Plasma, Monad, MegaETH, Stable, Rootstock outside the eight) | In the official docs and the live API. Active. | No (immutable) |
| **Aori 0.4.0 (staged)** | `0xa041a8f5d796de4ae21da10e90908549c17d1107` | Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche | Deployed 2026-05-20 with CREATE3; peers wired; not in the docs or the API; 0 logs in the window. | **UUPS** (ERC-1967) |
| Aori 0.3.0 (unwired) | `0x98ad96ef787ba5180814055039f8e37d98adea63` (Ethereum); `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` (Base, Arbitrum, Optimism) | Ethereum, Base, Arbitrum, Optimism | Same owner as the live mesh; peers only to each other; not in the docs or the API; 0 logs in the window. | No |
| Aori `1` (legacy) | Ethereum `0x5f3cb376fb82402fcf6d917fd729542537b9c6ad`, Base `0xf7c908eaa65fe48b201a5cd809df9d28bdcb2c39`, Arbitrum `0x0e9018eeeba45d70a9087d5d05295843afa3160a`, Optimism `0x684986544162a2c4ce4a6879981a4969b2c19e92` and `0x725b3886ecf20abd1d54227829db125312dbe1e9` | Ethereum, Base, Arbitrum, Optimism | Still named on the docs page "Supported Chains". Owner `0xb4afac168ca0cce40c5b4d4e8e49a1e18a630b40`. Last Ethereum transaction 2025-05-23. 0 logs in the window. | No |

The v0.3.0 build and the legacy `1` build emit the same topic0 for `Deposit`, `Fill`, `Settle`, `Withdraw`, `SettleSent` and `CancelSent` as v0.3.1. The legacy `1` build has no `Cancel(bytes32)` topic in its bytecode, no `depositNative` and a `withdraw(address)` instead of `withdraw(address,uint256)`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Aori v0.3.1 — order lifecycle (INDEX THESE)

Emitter = the Aori contract of the chain (§3 to §8). All confirmed in live logs (§13).

| topic0 | Event | Side / value |
|--------|-------|--------------|
| `0x8e45fa612720ed3142e896a3a29c981f4ca01c25bca19c3a5c203398ee1bc3d7` | `Deposit(bytes32 indexed orderId, (uint128 inputAmount, uint128 outputAmount, address inputToken, address outputToken, uint32 startTime, uint32 endTime, uint32 srcEid, uint32 dstEid, address offerer, address recipient) order)` | **Source leg.** Input locked in the contract. The value moves in the same transaction: ERC-20 `Transfer` offerer to Aori, or native `msg.value` for `depositNative`. |
| `0x86d7c80bc9d060acd32be0a39bbd97538a0e7b1f748c30d4e87b186b1d3589bb` | `SrcHookExecuted(bytes32 indexed orderId, address indexed preferredToken, uint256 amountReceived)` | Source leg with a hook: the input went offerer to hook, and the hook returned `amountReceived` of `preferredToken` to Aori. For a cross-chain order, the locked token and amount are these, not the order's `inputToken` / `inputAmount`. |
| `0x7f80314442bfb82d1f9dfa4f96cbc84ae8fef158c7a93315024778ca3fc16716` | `Fill(bytes32 indexed orderId, (uint128 inputAmount, uint128 outputAmount, address inputToken, address outputToken, uint32 startTime, uint32 endTime, uint32 srcEid, uint32 dstEid, address offerer, address recipient) order)` | **Destination leg.** The solver paid `outputAmount` of `outputToken` to `recipient` in the same transaction (ERC-20 `Transfer` solver to recipient, or native value). |
| `0xd6fb3db9629fef5e875e0d0138b2fb4ae60575aba13837c23c1c9a6aa1e35bac` | `DstHookExecuted(bytes32 indexed orderId, address indexed preferredToken, uint256 amountReceived)` | Destination leg with a hook: the solver paid `preferredToken` to the hook, and Aori paid the recipient from the hook output (Aori to recipient, not solver to recipient). |
| `0xd054cd999785d4c556d1f55b27cc59caba458cd5663063989d47725b97009232` | `SettleSent(uint32 indexed srcEid, address indexed filler, bytes payload, bytes32 guid, uint64 nonce, uint256 fee)` | **Status only.** Emitted on the destination chain. It sends up to `MAX_FILLS_PER_SETTLE` (100) filled order ids of one solver to the source chain. `payload` = the order ids. |
| `0xe82916be8cebf4000a0d08979cca286e4bfe07a019f19c0c930305aceacdcaf6` | `Settle(bytes32 indexed orderId)` | **Status only, internal balance.** Emitted on the source chain when the LayerZero settlement arrives (or at once for a same-chain swap). The offerer's locked balance becomes the solver's unlocked balance. No token moves. |
| `0x9b1bfa7fa9ee420a16e124f794c35ac9f90472acc99140eb2f6447c714cad8eb` | `Withdraw(address indexed holder, address indexed token, uint256 amount)` | **Payout of an unlocked balance** (usually the solver after `Settle`). ERC-20 `Transfer` Aori to holder, or native value (no log). Also emitted by the owner paths `emergencyCancel` and the five-argument `emergencyWithdraw`. |
| `0xe8d9861dbc9c663ed3accd261bbe2fe01e0d3d9e5f51fa38523b265c7757a93a` | `Cancel(bytes32 indexed orderId)` | **Refund.** Emitted on the source chain. The locked input goes back to the offerer in the same transaction (ERC-20 `Transfer` Aori to offerer, or native value). |
| `0x8168c9ac1d18802efe1afee0a6bf2de2b35d9f041a5b42a072b06252ba84fe50` | `CancelSent(bytes32 indexed orderId, bytes32 guid, uint64 nonce, uint256 fee)` | **Status only.** Emitted on the destination chain. It sends a LayerZero cancel message to the source chain. No token moves here. |
| `0xbb563f7e333f32ed0571f8dc4913648b41737753db5df83c58657c6bfcc2ef56` | `settlementFailed(bytes32 indexed orderId, uint32 expectedEid, uint32 submittedEid, string reason)` | Status only. A settlement message came from the wrong endpoint id; the order stays locked. |

### 1.2 Aori v0.3.1 — admin and LayerZero configuration

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xa7dbeb6ef5cb64125bfb03ac211f1aea3f639de95ceb37b16706d4f0735d1863` | `ChainSupported(uint32 indexed eid)` | Owner added a destination endpoint id. |
| `0x79df5d328757ca456e42d3dc087c02eedd4cf61d984a6aa526cfac31f1542dcd` | `ChainRemoved(uint32 indexed eid)` | Owner removed a destination endpoint id. |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` | LayerZero peer changed. **A new peer can deliver settlements that unlock escrow.** |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Owner change. |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | Owner paused deposits, fills, settles, cancels, withdrawals and `lzReceive`. |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | |
| `0x6ee10e9ed4d6ce9742703a498707862f4b00f1396a87195eb93267b3d7983981` | `DelegateSet(address sender, address delegate)` | Emitted by the LayerZero EndpointV2 (not by Aori) when the Aori delegate changes; the delegate controls the message libraries and DVN configuration. |

`addAllowedSolver`, `removeAllowedSolver`, `addAllowedHook` and `removeAllowedHook` emit **no event** in v0.3.1. Detect them by selector (§2.2).

### 1.3 Aori v0.4.0 (proxy `0xa041a8f5d796de4ae21da10e90908549c17d1107`) — changed and new events

`Cancel`, `CancelSent`, `SettleSent`, `Withdraw`, `ChainSupported`, `ChainRemoved`, `PeerSet`, `OwnershipTransferred`, `Paused` and `Unpaused` keep the v0.3.1 topic0. These change:

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xc22eae27b3f03e352e248c2cab93bf2890048d8a10a3626f7b14320b572b8688` | `Deposit(bytes32 indexed orderId, (uint128 inputAmount, uint128 outputAmount, address inputToken, uint32 startTime, uint32 endTime, uint32 srcEid, address outputToken, uint32 dstEid, address offerer, address recipient, (uint16 feeMbps, uint16 slippageMbps, address feeRecipient, address srcSolver, address dstSolver) options) order, address indexed srcHookTokenOut, uint256 srcHookAmountOut)` | **Source leg.** New field order and an `options` tuple. The hook output is in the event (no separate `SrcHookExecuted`). |
| `0x2bf10746b5979a7ded837e52451fcc5341fe2485928bd737e11b16e1a29b9366` | `Fill(bytes32 indexed orderId, address indexed fillToken, uint256 fillAmount, uint256 fillAmountOut)` | **Destination leg.** No order tuple: the recipient and the output amount are not in the event. Read them from the same transaction's transfer, or from the source `Deposit` by `orderId`. |
| `0xc18da40d564c35147f29dafe66d7f9249a2605f9557e12539fc70006866cde84` | `Settle(bytes32 indexed orderId, address indexed solver, uint256 solverUnlockedAmount, uint256 protocolFee, address feeRecipient, uint256 additionalFee)` | Status only (internal balance), now with the fee split. |
| `0x51aaa3ded9b0cf1010b3e404a268e2fe9025b7e391e8334467dfb197f85164ce` | `SettleFailed(bytes32 indexed orderId)` | Status only. |
| `0x3d272966e8fdc0afe6a7138ee63d4fd52d87cda35e06ad6ba9a2ac865e2a82b4` | `SettlementFailed(bytes32 indexed orderId, uint32 expectedEid, uint32 submittedEid)` | Replaces `settlementFailed`. |
| `0x41f9d09dd5159251f8a8e482bbe097b7c01a5e6f70c5a0ddb494906464fc9dd7` | `SolverAdded(address indexed solver)` | Admin. |
| `0x640e18a2587e1d83e4fdabf70257d0a800ca4b2c1aaad1dfc485a4ad8bbbd6c6` | `SolverRemoved(address indexed solver)` | Admin. |
| `0x28e00134722f84e69c391c81e4fe022ee3e61048222a8ea2f98c9f235f797508` | `HookAdded(address indexed hook)` | Admin. |
| `0x47d0871e905ac6550f54ba266e0d90d2dc8ed67a957c064ca3438eddf4e3fd89` | `HookRemoved(address indexed hook)` | Admin. |
| `0xac6fa858e9350a46cec16539926e0fde25b7629f84b5a72bffaae4df888ae86d` | `OperatorAdded(address indexed operator)` | Admin. |
| `0x80c0b871b97b595b16a7741c1b06fed0c6f6f558639f18ccbce50724325dc40d` | `OperatorRemoved(address indexed operator)` | Admin. |
| `0x15189fb9f7333d3c2ac875339ddb50cd49f554b5ed014b4b06111a437ec0b0c5` | `ProtocolFeeUpdated(uint16 feeMbps)` | Admin (fee in milli-basis points). |
| `0x62ec1b09f9a51deb25c6079f2e0be03553511ca352eb54acfaa11c04ce00ca95` | `MaxFeeUpdated(uint16 maxFeeMbps)` | Admin. |
| `0xb141872ee67913e1bc546464f29b6b07a65159d45c6af64fdecf8b4129157faf` | `ProtocolTreasuryUpdated(address indexed treasury)` | Admin. |
| `0xf0c7a508a88b46791f33a4cdfc61365dc2345576bfc49dac5a2cab385fd07c3c` | `ProtocolFeesClaimed(address indexed token, uint256 amount, address indexed treasury)` | Fee payout to the treasury. |
| `0xe8afd5ec5ee0b24b0622214e340a07c1270a07b7c5e3a760e9c0a5745c338bd3` | `MaxFillsPerSettleSet(uint16 newValue)` | Admin. |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | **UUPS implementation changed.** |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` | Proxy initialization. |

### 1.4 LayerZero EndpointV2 events in the same transactions (context)

Emitter = EndpointV2 `0x1a44076050125825900e736c501f859c50fe728c` on Ethereum, Base, Arbitrum, Optimism, Polygon, BNB and Avalanche.

| topic0 | Event | Where |
|--------|-------|-------|
| `0x1ab700d4ced0c005b164c0f789fd09fcbb0156d4c2041b8a3bfbcd961cd1567f` | `PacketSent(bytes encodedPayload, bytes options, address sendLibrary)` | Same transaction as `SettleSent` / `CancelSent`. |
| `0x3cd5e48f9730b129dc7550f0fcea9c767b7be37837cd10e55eb35f734f4bca04` | `PacketDelivered((uint32 srcEid, bytes32 sender, uint64 nonce) origin, address receiver)` | Same transaction as `Settle` / `Cancel` that arrive by message. `origin.nonce` = the `nonce` of `SettleSent` / `CancelSent`. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Aori v0.3.1 — deposit, fill, settle, cancel, withdraw

All confirmed as `PUSH4` constants in the live Ethereum bytecode.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x996628a0` | `deposit((uint128 inputAmount, uint128 outputAmount, address inputToken, address outputToken, uint32 startTime, uint32 endTime, uint32 srcEid, uint32 dstEid, address offerer, address recipient) order, bytes signature)` | `onlySolver`. Pulls `inputAmount` from the **offerer** (EIP-712 signature) with `transferFrom`. `tx.from` is the solver, not the user. Emits `Deposit`. |
| `0x555c3898` | `deposit((uint128 inputAmount, uint128 outputAmount, address inputToken, address outputToken, uint32 startTime, uint32 endTime, uint32 srcEid, uint32 dstEid, address offerer, address recipient) order, bytes signature, (address hookAddress, address preferredToken, uint256 minPreferedTokenAmountOut, bytes instructions) hook)` | `onlySolver`. Input goes offerer to hook; emits `SrcHookExecuted` then `Deposit` (cross-chain) or `Settle` (same-chain). |
| `0x1c0166aa` | `depositNative((uint128 inputAmount, uint128 outputAmount, address inputToken, address outputToken, uint32 startTime, uint32 endTime, uint32 srcEid, uint32 dstEid, address offerer, address recipient) order)` | `payable`. Called by the offerer (`msg.sender == offerer`), `msg.value == inputAmount`, `inputToken` = `0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee`. Emits `Deposit`. |
| `0x7ce5e33e` | `fill((uint128 inputAmount, uint128 outputAmount, address inputToken, address outputToken, uint32 startTime, uint32 endTime, uint32 srcEid, uint32 dstEid, address offerer, address recipient) order)` | `onlySolver`, `payable`. Solver pays the recipient directly. Emits `Fill`. |
| `0xa9a683ba` | `fill((uint128 inputAmount, uint128 outputAmount, address inputToken, address outputToken, uint32 startTime, uint32 endTime, uint32 srcEid, uint32 dstEid, address offerer, address recipient) order, (address hookAddress, address preferredToken, bytes instructions, uint256 preferedDstInputAmount) hook)` | `onlySolver`, `payable`. Hook converts; Aori pays the recipient and returns the surplus to the solver. Emits `DstHookExecuted` and `Fill`. |
| `0x2c85455b` | `settle(uint32 srcEid, address filler, bytes extraOptions)` | `onlySolver`, `payable` (LayerZero fee). Emits `SettleSent`. |
| `0xc4d252f5` | `cancel(bytes32 orderId)` | Source-chain cancel, same-chain orders only (solver, or offerer after expiry). Emits `Cancel` and refunds. |
| `0x983f7fd1` | `cancel(bytes32 orderId, (uint128 inputAmount, uint128 outputAmount, address inputToken, address outputToken, uint32 startTime, uint32 endTime, uint32 srcEid, uint32 dstEid, address offerer, address recipient) orderToCancel, bytes extraOptions)` | Destination-chain cancel of a cross-chain order (solver any time before settlement; offerer or recipient after expiry). `payable`. Emits `CancelSent`. |
| `0xf3fef3a3` | `withdraw(address token, uint256 amount)` | Takes the caller's unlocked balance (`amount` 0 = all). Emits `Withdraw`. |
| `0x13137d65` | `lzReceive((uint32 srcEid, bytes32 sender, uint64 nonce) origin, bytes32 guid, bytes message, address executor, bytes extraData)` | Called by the EndpointV2 only. Runs the settlement (`Settle`) or cancellation (`Cancel`). |

### 2.2 Aori v0.3.1 — owner functions (single owner, see §10)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8456cb59` | `pause()` | Emits `Paused`. |
| `0x3f4ba83a` | `unpause()` | Emits `Unpaused`. |
| `0x595490c8` | `addAllowedSolver(address solver)` | **No event.** |
| `0x1e2c273e` | `removeAllowedSolver(address solver)` | **No event.** |
| `0xedb25d81` | `addAllowedHook(address hook)` | **No event.** |
| `0x6b624fdb` | `removeAllowedHook(address hook)` | **No event.** |
| `0x50964586` | `addSupportedChain(uint32 eid)` | Emits `ChainSupported`. |
| `0xb8f480c6` | `addSupportedChains(uint32[] eids)` | Emits `ChainSupported` per id. |
| `0xc15c4b37` | `removeSupportedChain(uint32 eid)` | Emits `ChainRemoved`. |
| `0xe898841f` | `emergencyCancel(bytes32 orderId, address recipient)` | Returns a locked order to **any** recipient. Emits `Cancel` and `Withdraw(recipient, token, amount)`. |
| `0x95ccea67` | `emergencyWithdraw(address token, uint256 amount)` | **Drain path with no event:** sends the whole native balance and `amount` of `token` to `owner()`. Only the ERC-20 `Transfer` (or a native trace) shows it. |
| `0x2d7c615a` | `emergencyWithdraw(address token, uint256 amount, address user, bool isLocked, address recipient)` | Takes from a user's locked or unlocked balance to `recipient`. Emits `Withdraw(user, token, amount)`, the same topic as a normal withdrawal. |
| `0x3400288b` | `setPeer(uint32 eid, bytes32 peer)` | Emits `PeerSet`. |
| `0xca5eb5e1` | `setDelegate(address delegate)` | EndpointV2 emits `DelegateSet`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Emits `OwnershipTransferred`. |
| `0x715018a6` | `renounceOwnership()` | |

### 2.3 Aori v0.3.1 — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x2cee9acd` | `ENDPOINT_ID()` | `uint32` — this chain's LayerZero eid (30101 on Ethereum, 30184 Base, 30110 Arbitrum, 30111 Optimism, 30102 BNB). |
| `0x44ae20c3` | `MAX_FILLS_PER_SETTLE()` | `uint16` — 100 on every live contract. |
| `0x2dff692d` | `orderStatus(bytes32 orderId)` | `uint8` — 0 Unknown, 1 Active, 2 Filled, 3 Cancelled, 4 Settled. |
| `0x9c3f1e90` | `orders(bytes32 orderId)` | The stored order (source side). |
| `0xb410f122` | `hash((uint128 inputAmount, uint128 outputAmount, address inputToken, address outputToken, uint32 startTime, uint32 endTime, uint32 srcEid, uint32 dstEid, address offerer, address recipient) order)` | `bytes32` — the `orderId`. |
| `0x05ef94ba` | `getLockedBalances(address offerer, address token)` | `uint256`. |
| `0xe86dfbbf` | `getUnlockedBalances(address offerer, address token)` | `uint256`. |
| `0x59f429a4` | `isSupportedChain(uint32 eid)` | `bool`. |
| `0x7de63734` | `isAllowedSolver(address solver)` | `bool`. |
| `0x344ba6fd` | `isAllowedHook(address hook)` | `bool`. |
| `0x0c89a13d` | `srcEidToFillerFills(uint32 srcEid, address filler, uint256 index)` | `bytes32` — filled order ids waiting for `settle`. |
| `0xcd774887` | `quote(uint32 _dstEid, uint8 _msgType, bytes _options, bool _payInLzToken, uint32 _srcEid, address _filler)` | `uint256` — LayerZero fee. |
| `0xbb0b6a53` | `peers(uint32 eid)` | `bytes32` — the remote Aori (read it to list the wired chains). |
| `0x5e280f11` | `endpoint()` | `address` — EndpointV2. |
| `0x8da5cb5b` | `owner()` | `address`. |
| `0x5c975abb` | `paused()` | `bool`. |
| `0x84b0196e` | `eip712Domain()` | Name `Aori` and version (`0.3.1`, `0.4.0`, `0.3.0` or `1`). |

### 2.4 Aori v0.4.0 — changed selectors

The v0.4.0 order tuple is `(uint128 inputAmount, uint128 outputAmount, address inputToken, uint32 startTime, uint32 endTime, uint32 srcEid, address outputToken, uint32 dstEid, address offerer, address recipient, (uint16 feeMbps, uint16 slippageMbps, address feeRecipient, address srcSolver, address dstSolver) options)`. `settle`, `cancel(bytes32)`, `withdraw`, `pause`, `unpause`, `setPeer` and the solver, hook and chain setters keep their v0.3.1 selectors.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xbe9bef4e` | `deposit((uint128 inputAmount, uint128 outputAmount, address inputToken, uint32 startTime, uint32 endTime, uint32 srcEid, address outputToken, uint32 dstEid, address offerer, address recipient, (uint16 feeMbps, uint16 slippageMbps, address feeRecipient, address srcSolver, address dstSolver) options) order, bytes signature)` | Source leg (solver-submitted). |
| `0x6014ff6a` | `deposit((uint128 inputAmount, uint128 outputAmount, address inputToken, uint32 startTime, uint32 endTime, uint32 srcEid, address outputToken, uint32 dstEid, address offerer, address recipient, (uint16 feeMbps, uint16 slippageMbps, address feeRecipient, address srcSolver, address dstSolver) options) order, bytes signature, (address hookAddress, address preferredToken, uint256 minPreferredTokenAmountOut, bytes instructions) hook)` | Source leg with a hook. |
| `0x66dd929b` | `depositNative((uint128 inputAmount, uint128 outputAmount, address inputToken, uint32 startTime, uint32 endTime, uint32 srcEid, address outputToken, uint32 dstEid, address offerer, address recipient, (uint16 feeMbps, uint16 slippageMbps, address feeRecipient, address srcSolver, address dstSolver) options) order, (address hookAddress, address preferredToken, uint256 minPreferredTokenAmountOut, bytes instructions) srcHook, bytes quoteSignature)` | Native source leg. |
| `0x0166331d` | `depositWithPermit2((uint128 inputAmount, uint128 outputAmount, address inputToken, uint32 startTime, uint32 endTime, uint32 srcEid, address outputToken, uint32 dstEid, address offerer, address recipient, (uint16 feeMbps, uint16 slippageMbps, address feeRecipient, address srcSolver, address dstSolver) options) order, uint256 nonce, uint256 deadline, bytes signature)` | Source leg through Permit2. |
| `0x46160d55` | `depositWithPermit2((uint128 inputAmount, uint128 outputAmount, address inputToken, uint32 startTime, uint32 endTime, uint32 srcEid, address outputToken, uint32 dstEid, address offerer, address recipient, (uint16 feeMbps, uint16 slippageMbps, address feeRecipient, address srcSolver, address dstSolver) options) order, (address hookAddress, address preferredToken, uint256 minPreferredTokenAmountOut, bytes instructions) hook, uint256 nonce, uint256 deadline, bytes signature)` | Permit2 with a hook. |
| `0x62996b8b` | `fill((uint128 inputAmount, uint128 outputAmount, address inputToken, uint32 startTime, uint32 endTime, uint32 srcEid, address outputToken, uint32 dstEid, address offerer, address recipient, (uint16 feeMbps, uint16 slippageMbps, address feeRecipient, address srcSolver, address dstSolver) options) order)` | Destination leg. |
| `0xde1b7f1f` | `fill((uint128 inputAmount, uint128 outputAmount, address inputToken, uint32 startTime, uint32 endTime, uint32 srcEid, address outputToken, uint32 dstEid, address offerer, address recipient, (uint16 feeMbps, uint16 slippageMbps, address feeRecipient, address srcSolver, address dstSolver) options) order, (address hookAddress, address preferredToken, bytes instructions, uint256 preferredDstInputAmount) hook)` | Destination leg with a hook. |
| `0xf9331b34` | `cancel(bytes32 orderId, (uint128 inputAmount, uint128 outputAmount, address inputToken, uint32 startTime, uint32 endTime, uint32 srcEid, address outputToken, uint32 dstEid, address offerer, address recipient, (uint16 feeMbps, uint16 slippageMbps, address feeRecipient, address srcSolver, address dstSolver) options) orderToCancel, bytes extraOptions)` | Destination-chain cancel. |
| `0x551512de` | `emergencyWithdraw(address token, uint256 amount, address recipient)` | Owner drain path. |
| `0x338f71d3` | `emergencyWithdrawFromBalance(address token, uint256 amount, address user, bool isLocked, address recipient)` | Owner path on a user balance. |
| `0x69ce6d47` | `claimProtocolFees(address token)` | Emits `ProtocolFeesClaimed`. |
| `0xe4467f35` | `setProtocolFee(uint16 feeMbps)` | Emits `ProtocolFeeUpdated`. |
| `0xae3b1f81` | `setMaxFee(uint16 maxFeeMbps)` | Emits `MaxFeeUpdated`. |
| `0x0c5a61f8` | `setProtocolTreasury(address treasury)` | Emits `ProtocolTreasuryUpdated`. |
| `0x9870d7fe` | `addOperator(address operator)` | Emits `OperatorAdded`. |
| `0xac8a584a` | `removeOperator(address operator)` | Emits `OperatorRemoved`. |
| `0x20122db8` | `setMaxFillsPerSettle(uint16 maxFills)` | Emits `MaxFillsPerSettleSet`. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | UUPS upgrade; owner only. Emits `Upgraded`. |
| `0x52d1902d` | `proxiableUUID()` | UUPS marker. |
| `0xb03a5388` | `initialize(address _owner, uint16 _maxFillsPerSettle, address[] _initialSolvers, address[] _initialHooks, uint32[] _supportedChains, address[] _initialOperators)` | One-time proxy initialization. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

LayerZero eid 30101. All verified with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **Aori 0.3.1 (live)** | `0x0736bdc975af0675b9a045384efed91360d25479` | 22,960 B, immutable, verified as `Aori` on Blockscout. Created in block 23,097,471 by the owner EOA. Peers: Base, Arbitrum, Optimism `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6`; BNB `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8`. |
| Aori 0.4.0 proxy (staged) | `0xa041a8f5d796de4ae21da10e90908549c17d1107` | ERC-1967 UUPS proxy (130 B). Implementation `0xa38fca792cd722208ad367853c8cfd7c7ac1c36e`. |
| Aori 0.3.0 (unwired) | `0x98ad96ef787ba5180814055039f8e37d98adea63` | 23,714 B. Peers only to `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` on Base, Arbitrum and Optimism. |
| Aori `1` (legacy) | `0x5f3cb376fb82402fcf6d917fd729542537b9c6ad` | 23,850 B. Owner `0xb4afac168ca0cce40c5b4d4e8e49a1e18a630b40`. Last transaction 2025-05-23. |
| Aori `1` (legacy, second Ethereum peer) | `0x3c5ee8ec2e0174ce1b34f140f37c032e43ef41b6` | 23,832 B. Ethereum peer of the legacy Optimism contract `0x684986544162a2c4ce4a6879981a4969b2c19e92`. |
| Owner of the live and 0.4.0 contracts (EOA) | `0x941327e206b8d8cfe1014a8a95b05e1536dfd00d` | `eth_getCode` = `0x`, nonce 505. |
| Whitelisted solver (EOA) | `0x95dd8db1c0c066eba8c37cd1c6b4c895500b20f2` | `isAllowedSolver` = true on Ethereum, Base, Arbitrum, Optimism and BNB. Nonce 125,611. Fills, settles, cancels and withdraws in the samples. |
| LayerZero EndpointV2 | `0x1a44076050125825900e736c501f859c50fe728c` | `endpoint()` of every Aori contract here. |
| Aori CREATE3 factory | `0x2dfcc7415d89af828cbef005f0d072d8b3f23183` | Deploys the 0.4.0 proxy and implementation at one address on every chain. |

## 4. Addresses — Base (chain ID 8453)

LayerZero eid 30184.

| Role | Address | One-liner |
|------|---------|-----------|
| **Aori 0.3.1 (live)** | `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6` | 22,960 B, immutable. Peers: Ethereum `0x0736bdc975af0675b9a045384efed91360d25479`, Arbitrum `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6`, BNB `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8`. |
| Aori 0.4.0 proxy (staged) | `0xa041a8f5d796de4ae21da10e90908549c17d1107` | Same address and implementation address as on Ethereum. |
| Aori 0.3.0 (unwired) | `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` | 23,714 B. **Not the live contract on this chain.** Ethereum peer `0x98ad96ef787ba5180814055039f8e37d98adea63`. |
| Aori `1` (legacy) | `0xf7c908eaa65fe48b201a5cd809df9d28bdcb2c39` | 23,850 B. 0 logs in the window. |

## 5. Addresses — Arbitrum One (chain ID 42161)

LayerZero eid 30110.

| Role | Address | One-liner |
|------|---------|-----------|
| **Aori 0.3.1 (live)** | `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6` | 22,960 B, immutable. Same address as Base and Optimism, own immutables (`ENDPOINT_ID` 30110). |
| Aori 0.4.0 proxy (staged) | `0xa041a8f5d796de4ae21da10e90908549c17d1107` | Six test `deposit` calls; the last on 2026-07-02. |
| Aori 0.3.0 (unwired) | `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` | 23,714 B. Not the live contract on this chain. |
| Aori `1` (legacy) | `0x0e9018eeeba45d70a9087d5d05295843afa3160a` | 23,850 B. 0 logs in the window. |

## 6. Addresses — Optimism (chain ID 10)

LayerZero eid 30111.

| Role | Address | One-liner |
|------|---------|-----------|
| **Aori 0.3.1 (live)** | `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6` | 22,960 B, immutable (`ENDPOINT_ID` 30111). |
| Aori 0.4.0 proxy (staged) | `0xa041a8f5d796de4ae21da10e90908549c17d1107` | ERC-1967 UUPS proxy. |
| Aori 0.3.0 (unwired) | `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` | 23,714 B. Not the live contract on this chain. |
| Aori `1` (legacy) | `0x684986544162a2c4ce4a6879981a4969b2c19e92` | 23,832 B. The address on the docs page "Supported Chains". Its Ethereum peer is `0x3c5ee8ec2e0174ce1b34f140f37c032e43ef41b6`. |
| Aori `1` (legacy) | `0x725b3886ecf20abd1d54227829db125312dbe1e9` | 23,850 B. The Optimism peer of the legacy Ethereum contract `0x5f3cb376fb82402fcf6d917fd729542537b9c6ad`. |

## 7. Addresses — BNB Smart Chain (chain ID 56)

LayerZero eid 30102.

| Role | Address | One-liner |
|------|---------|-----------|
| **Aori 0.3.1 (live)** | `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` | 22,960 B, immutable (`ENDPOINT_ID` 30102). Peers: Ethereum `0x0736bdc975af0675b9a045384efed91360d25479`, Arbitrum and Base `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6`. Same address as on Plasma, Monad, MegaETH, Stable and Rootstock. |
| Aori 0.4.0 proxy (staged) | `0xa041a8f5d796de4ae21da10e90908549c17d1107` | ERC-1967 UUPS proxy. |

## 8. Addresses — Polygon PoS (chain ID 137) and Avalanche C-Chain (chain ID 43114)

LayerZero eids 30109 (Polygon) and 30106 (Avalanche). **No live Aori contract.** The live contracts have no peer for 30109 or 30106, and `isSupportedChain` returns false. The official list and the API do not name these chains.

| Role | Address | One-liner |
|------|---------|-----------|
| Aori 0.4.0 proxy (staged) | `0xa041a8f5d796de4ae21da10e90908549c17d1107` | The only Aori contract on Polygon and on Avalanche. The Ethereum 0.4.0 proxy has these chains as supported peers. 0 logs in the window. |

### 8.1 Robinhood Chain (chain ID 4663) — NO Aori deployment

LayerZero lists Robinhood Chain as eid 30416 (EndpointV2 `0x6f475642a6e85809b1c36fa62763669b1b48dd5b`). `eth_getCode` returns `0x` at every Aori address of this doc on Robinhood Chain. No Aori contract has a peer for 30416, and the official list and the API do not name the chain.

---

## 9. Cross-chain summary

| Chain | ID | LayerZero eid | Aori 0.3.1 (live) | Aori 0.4.0 proxy `0xa041a8f5d796de4ae21da10e90908549c17d1107` | Older builds |
|-------|----|---------------|-------------------|------------------|--------------|
| Ethereum | 1 | 30101 | `0x0736bdc975af0675b9a045384efed91360d25479` | ✓ (staged) | 0.3.0 `0x98ad96ef787ba5180814055039f8e37d98adea63`; `1` `0x5f3cb376fb82402fcf6d917fd729542537b9c6ad`, `0x3c5ee8ec2e0174ce1b34f140f37c032e43ef41b6` |
| Base | 8453 | 30184 | `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6` | ✓ (staged) | 0.3.0 `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8`; `1` `0xf7c908eaa65fe48b201a5cd809df9d28bdcb2c39` |
| Arbitrum One | 42161 | 30110 | `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6` | ✓ (staged, test deposits) | 0.3.0 `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8`; `1` `0x0e9018eeeba45d70a9087d5d05295843afa3160a` |
| Optimism | 10 | 30111 | `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6` | ✓ (staged) | 0.3.0 `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8`; `1` `0x684986544162a2c4ce4a6879981a4969b2c19e92`, `0x725b3886ecf20abd1d54227829db125312dbe1e9` |
| Polygon PoS | 137 | 30109 | — (`0x`) | ✓ (staged) | — |
| BNB Smart Chain | 56 | 30102 | `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` | ✓ (staged) | — |
| Avalanche C-Chain | 43114 | 30106 | — (`0x`) | ✓ (staged) | — |
| Robinhood Chain | 4663 | 30416 | — (`0x`) | — (`0x`) | — |

**Chains outside the eight** (official list, same live address `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8`): Plasma (9745, eid 30383), Monad (143, eid 30390), MegaETH (4326, eid 30398); the docs also list Stable (988, eid 30396) and Rootstock (30, eid 30333), which the live API does not return. The live Ethereum contract has a peer for all five.

---

## 10. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade / admin authority |
|----------|---------|-----------|---------------------------|
| **Aori 0.3.1** (all live addresses) | **Not a proxy** (immutable) | EIP-1967 implementation slot = `0x0` (read live on Ethereum); full 22,960 B runtime; LayerZero `OApp` + `Ownable` + `Pausable`. | Redeploy only. `owner()` = EOA `0x941327e206b8d8cfe1014a8a95b05e1536dfd00d` on Ethereum, Base, Arbitrum, Optimism and BNB. The owner can pause, whitelist solvers and hooks (no event), set peers, `emergencyCancel` and `emergencyWithdraw`. |
| **Aori 0.4.0** `0xa041a8f5d796de4ae21da10e90908549c17d1107` | **UUPS** (ERC-1967 proxy, 130 B) | Implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` = `0xa38fca792cd722208ad367853c8cfd7c7ac1c36e` on all seven chains; admin slot empty; `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. | `upgradeToAndCall` by `owner()` = the same EOA `0x941327e206b8d8cfe1014a8a95b05e1536dfd00d` (read on Ethereum and Arbitrum). |
| Aori 0.3.0 and Aori `1` | Not proxies | Full runtime bytecode, no implementation slot. | 0.3.0: the same owner EOA; `1`: EOA `0xb4afac168ca0cce40c5b4d4e8e49a1e18a630b40`. |

**A single EOA owns every live Aori contract.** Watch `OwnershipTransferred`, `PeerSet`, `Paused`, `DelegateSet` (on the EndpointV2) and, for 0.4.0, `Upgraded`. Watch the owner-only selectors `0x95ccea67`, `0x2d7c615a`, `0xe898841f`, `0x595490c8` and `0xedb25d81` in transaction input, because some of them emit no event.

---

## 11. Detection invariants & gotchas

1. **Source leg = `Deposit` on the source Aori; destination leg = `Fill` on the destination Aori; join on `orderId` (topic1).** `order.srcEid` and `order.dstEid` are LayerZero eids (§9), not chain ids. In the measured window, every chain had both `Deposit` and `Fill` logs.
2. **`Settle` moves no token.** It only moves the offerer's locked balance to the solver's internal balance. The escrow pays the solver later with `Withdraw` and an ERC-20 `Transfer` from Aori (or native value). One `settle` call carries up to 100 order ids; the sample on Ethereum delivered 8 `Settle` logs in one transaction.
3. **`tx.from` is rarely the user.** ERC-20 deposits are submitted by a whitelisted solver (`onlySolver`) and pull the tokens from `order.offerer` by signature. Attribute the source by `order.offerer` in the `Deposit` data, and the destination by `order.recipient` in the `Fill` data. Only `depositNative` is called by the offerer.
4. **Much of the value is native.** `depositNative` carries the value in `msg.value` with no transfer log. A native `fill` forwards `msg.value` to the recipient, a hook fill that outputs native ETH pays the recipient from Aori, and a native `withdraw` pays the solver: all as trace-only value. Read native transfers (traces) for these.
5. **Hook orders change the locked asset.** With a source hook, `Deposit` still shows the signed `inputToken` / `inputAmount`, but the contract locks `SrcHookExecuted.preferredToken` / `amountReceived`. With a destination hook, the solver pays `preferredToken` to the hook, and Aori pays the recipient; the surplus goes back to the solver.
6. **Same-chain swaps use the same contract.** `deposit` with a hook and `srcEid == dstEid` emits `SrcHookExecuted` and `Settle` without `Deposit`; `fill` of a same-chain order emits `Settle` instead of `Fill`. A plain same-chain `deposit` still emits `Deposit`. For bridge flow, keep only `Deposit` rows with `order.srcEid != order.dstEid`.
7. **Refund path.** A cross-chain order is cancelled from the destination chain: `CancelSent` there (status only), then `Cancel` plus the refund transfer to the offerer on the source chain when the LayerZero message arrives. A same-chain order is cancelled on the source chain with `cancel(bytes32)`. `emergencyCancel` (owner) can send the refund to any recipient; it emits `Cancel` and `Withdraw(recipient, token, amount)`.
8. **LayerZero link for settlement and cancel.** `SettleSent.nonce` / `CancelSent.nonce` on the destination chain equals `PacketDelivered.origin.nonce` on the source chain, with `origin.sender` = the destination Aori (as `bytes32`) and `receiver` = the source Aori.
9. **`Withdraw(address,address,uint256)` is a common signature.** In the window it came from 24 different emitters on Ethereum and 25 on Base, most of them not Aori. Always filter by the Aori address.
10. **The same literal address is a different contract on different chains.** `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` is live 0.3.1 on BNB and unwired 0.3.0 on Base, Arbitrum and Optimism. `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6` has no code on Ethereum or BNB.
11. **The Aori docs contradict themselves.** The "Deployments" page and the live API name the 0.3.1 addresses. The "Supported Chains" page and the API reference still show the legacy `1` build for Ethereum, Base, Arbitrum and Optimism (0 logs in the window). Trust the API and the on-chain peers.
12. **Prepare for 0.4.0 now.** Its proxy is wired on seven of the eight chains (including Polygon and Avalanche, which 0.3.1 does not serve). Its `Deposit`, `Fill` and `Settle` topics differ (§1.3), and its `Fill` has no recipient field. It emitted 0 logs in the window.
13. **Admin actions without events (0.3.1).** Solver and hook whitelist changes and the two-argument `emergencyWithdraw` (whole native balance plus a token amount to the owner) emit nothing from Aori. Key on the selectors and on transfers out of the Aori address to the owner EOA.

---

## 12. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Aori 0.3.1 topics (live) =====
TOPIC_AORI_DEPOSIT               = '\x8e45fa612720ed3142e896a3a29c981f4ca01c25bca19c3a5c203398ee1bc3d7'
TOPIC_AORI_SRC_HOOK_EXECUTED     = '\x86d7c80bc9d060acd32be0a39bbd97538a0e7b1f748c30d4e87b186b1d3589bb'
TOPIC_AORI_FILL                  = '\x7f80314442bfb82d1f9dfa4f96cbc84ae8fef158c7a93315024778ca3fc16716'
TOPIC_AORI_DST_HOOK_EXECUTED     = '\xd6fb3db9629fef5e875e0d0138b2fb4ae60575aba13837c23c1c9a6aa1e35bac'
TOPIC_AORI_SETTLE_SENT           = '\xd054cd999785d4c556d1f55b27cc59caba458cd5663063989d47725b97009232'
TOPIC_AORI_SETTLE                = '\xe82916be8cebf4000a0d08979cca286e4bfe07a019f19c0c930305aceacdcaf6'
TOPIC_AORI_WITHDRAW              = '\x9b1bfa7fa9ee420a16e124f794c35ac9f90472acc99140eb2f6447c714cad8eb'
TOPIC_AORI_CANCEL                = '\xe8d9861dbc9c663ed3accd261bbe2fe01e0d3d9e5f51fa38523b265c7757a93a'
TOPIC_AORI_CANCEL_SENT           = '\x8168c9ac1d18802efe1afee0a6bf2de2b35d9f041a5b42a072b06252ba84fe50'
TOPIC_AORI_SETTLEMENT_FAILED     = '\xbb563f7e333f32ed0571f8dc4913648b41737753db5df83c58657c6bfcc2ef56'
TOPIC_AORI_CHAIN_SUPPORTED       = '\xa7dbeb6ef5cb64125bfb03ac211f1aea3f639de95ceb37b16706d4f0735d1863'
TOPIC_AORI_CHAIN_REMOVED         = '\x79df5d328757ca456e42d3dc087c02eedd4cf61d984a6aa526cfac31f1542dcd'
TOPIC_PEER_SET                   = '\x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b'
TOPIC_OWNERSHIP_TRANSFERRED      = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_PAUSED                     = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                   = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_LZ_DELEGATE_SET            = '\x6ee10e9ed4d6ce9742703a498707862f4b00f1396a87195eb93267b3d7983981'
TOPIC_LZ_PACKET_SENT             = '\x1ab700d4ced0c005b164c0f789fd09fcbb0156d4c2041b8a3bfbcd961cd1567f'
TOPIC_LZ_PACKET_DELIVERED        = '\x3cd5e48f9730b129dc7550f0fcea9c767b7be37837cd10e55eb35f734f4bca04'
-- ===== Aori 0.4.0 topics (changed or new) =====
TOPIC_AORI_V040_DEPOSIT          = '\xc22eae27b3f03e352e248c2cab93bf2890048d8a10a3626f7b14320b572b8688'
TOPIC_AORI_V040_FILL             = '\x2bf10746b5979a7ded837e52451fcc5341fe2485928bd737e11b16e1a29b9366'
TOPIC_AORI_V040_SETTLE           = '\xc18da40d564c35147f29dafe66d7f9249a2605f9557e12539fc70006866cde84'
TOPIC_AORI_V040_SETTLE_FAILED    = '\x51aaa3ded9b0cf1010b3e404a268e2fe9025b7e391e8334467dfb197f85164ce'
TOPIC_AORI_V040_SETTLEMENT_FAILED= '\x3d272966e8fdc0afe6a7138ee63d4fd52d87cda35e06ad6ba9a2ac865e2a82b4'
TOPIC_AORI_V040_SOLVER_ADDED     = '\x41f9d09dd5159251f8a8e482bbe097b7c01a5e6f70c5a0ddb494906464fc9dd7'
TOPIC_AORI_V040_HOOK_ADDED       = '\x28e00134722f84e69c391c81e4fe022ee3e61048222a8ea2f98c9f235f797508'
TOPIC_AORI_V040_OPERATOR_ADDED   = '\xac6fa858e9350a46cec16539926e0fde25b7629f84b5a72bffaae4df888ae86d'
TOPIC_AORI_V040_FEES_CLAIMED     = '\xf0c7a508a88b46791f33a4cdfc61365dc2345576bfc49dac5a2cab385fd07c3c'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors (0.3.1) =====
SEL_AORI_DEPOSIT                 = '\x996628a0'
SEL_AORI_DEPOSIT_HOOK            = '\x555c3898'
SEL_AORI_DEPOSIT_NATIVE          = '\x1c0166aa'
SEL_AORI_FILL                    = '\x7ce5e33e'
SEL_AORI_FILL_HOOK               = '\xa9a683ba'
SEL_AORI_SETTLE                  = '\x2c85455b'
SEL_AORI_CANCEL_SRC              = '\xc4d252f5'
SEL_AORI_CANCEL_DST              = '\x983f7fd1'
SEL_AORI_WITHDRAW                = '\xf3fef3a3'
SEL_AORI_EMERGENCY_CANCEL        = '\xe898841f'
SEL_AORI_EMERGENCY_WITHDRAW      = '\x95ccea67'
SEL_AORI_EMERGENCY_WITHDRAW_USER = '\x2d7c615a'
SEL_AORI_ADD_SOLVER              = '\x595490c8'
SEL_AORI_ADD_HOOK                = '\xedb25d81'
SEL_AORI_PAUSE                   = '\x8456cb59'
SEL_SET_PEER                     = '\x3400288b'
SEL_SET_DELEGATE                 = '\xca5eb5e1'
SEL_LZ_RECEIVE                   = '\x13137d65'
SEL_AORI_PEERS                   = '\xbb0b6a53'
SEL_AORI_ENDPOINT_ID             = '\x2cee9acd'
-- ===== Selectors (0.4.0, changed) =====
SEL_AORI_V040_DEPOSIT            = '\xbe9bef4e'
SEL_AORI_V040_DEPOSIT_HOOK       = '\x6014ff6a'
SEL_AORI_V040_DEPOSIT_NATIVE     = '\x66dd929b'
SEL_AORI_V040_DEPOSIT_PERMIT2    = '\x0166331d'
SEL_AORI_V040_FILL               = '\x62996b8b'
SEL_AORI_V040_FILL_HOOK          = '\xde1b7f1f'
SEL_AORI_V040_CANCEL_DST         = '\xf9331b34'
SEL_AORI_V040_EMERGENCY_WITHDRAW = '\x551512de'
SEL_UPGRADE_TO_AND_CALL          = '\x4f1ef286'

-- ===== Addresses — live 0.3.1 (network-specific) =====
ETH_AORI                         = '\x0736bdc975af0675b9a045384efed91360d25479'
BASE_AORI                        = '\xc6868edf1d2a7a8b759856cb8afa333210dfeda6'
ARB_AORI                         = '\xc6868edf1d2a7a8b759856cb8afa333210dfeda6'
OP_AORI                          = '\xc6868edf1d2a7a8b759856cb8afa333210dfeda6'
BNB_AORI                         = '\xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8'
-- ===== Aori 0.4.0 proxy (same address on ETH BASE ARB OP POLY BNB AVAX; 0x on Robinhood) =====
ETH_AORI_V040_PROXY              = '\xa041a8f5d796de4ae21da10e90908549c17d1107'
BASE_AORI_V040_PROXY             = '\xa041a8f5d796de4ae21da10e90908549c17d1107'
ARB_AORI_V040_PROXY              = '\xa041a8f5d796de4ae21da10e90908549c17d1107'
OP_AORI_V040_PROXY               = '\xa041a8f5d796de4ae21da10e90908549c17d1107'
POLY_AORI_V040_PROXY             = '\xa041a8f5d796de4ae21da10e90908549c17d1107'
BNB_AORI_V040_PROXY              = '\xa041a8f5d796de4ae21da10e90908549c17d1107'
AVAX_AORI_V040_PROXY             = '\xa041a8f5d796de4ae21da10e90908549c17d1107'
ETH_AORI_V040_IMPL               = '\xa38fca792cd722208ad367853c8cfd7c7ac1c36e'
-- ===== Older builds (0 logs in the window; keep for backfills) =====
ETH_AORI_V030                    = '\x98ad96ef787ba5180814055039f8e37d98adea63'
BASE_AORI_V030                   = '\xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8'
ARB_AORI_V030                    = '\xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8'
OP_AORI_V030                     = '\xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8'
ETH_AORI_LEGACY                  = '\x5f3cb376fb82402fcf6d917fd729542537b9c6ad'
ETH_AORI_LEGACY_2                = '\x3c5ee8ec2e0174ce1b34f140f37c032e43ef41b6'
BASE_AORI_LEGACY                 = '\xf7c908eaa65fe48b201a5cd809df9d28bdcb2c39'
ARB_AORI_LEGACY                  = '\x0e9018eeeba45d70a9087d5d05295843afa3160a'
OP_AORI_LEGACY                   = '\x684986544162a2c4ce4a6879981a4969b2c19e92'
OP_AORI_LEGACY_2                 = '\x725b3886ecf20abd1d54227829db125312dbe1e9'
-- ===== Admin, solver and LayerZero =====
ETH_AORI_OWNER_EOA               = '\x941327e206b8d8cfe1014a8a95b05e1536dfd00d'   -- same EOA owns the live and 0.4.0 contracts on every chain
ETH_AORI_SOLVER_EOA              = '\x95dd8db1c0c066eba8c37cd1c6b4c895500b20f2'   -- whitelisted on ETH BASE ARB OP BNB
ETH_AORI_LEGACY_OWNER_EOA        = '\xb4afac168ca0cce40c5b4d4e8e49a1e18a630b40'
ETH_AORI_CREATE3_FACTORY         = '\x2dfcc7415d89af828cbef005f0d072d8b3f23183'
ETH_LZ_ENDPOINT_V2               = '\x1a44076050125825900e736c501f859c50fe728c'   -- same on BASE ARB OP POLY BNB AVAX
AORI_NATIVE_TOKEN                = '\xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'   -- native-token sentinel in inputToken / outputToken
-- Robinhood Chain (4663): no Aori contract; LayerZero eid 30416
```

---

## 13. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `contracts/IAori.sol` and `contracts/Aori.sol` of `aori-io/aori` (`master`, version 0.3.1), from `contracts/interfaces/IAori.sol` and `contracts/types/AoriTypes.sol` of the `v0.4.0` branch, and from the verified 0.4.0 implementation ABI on Blockscout. Every 0.3.1 selector of §2.1 to §2.3 was found as a `PUSH4` constant in the live Ethereum bytecode, and every 0.3.1 topic of §1.1 and §1.2 was found in the same bytecode. The legacy `1` build has no `Cancel(bytes32)` topic, no `depositNative` (`0x1c0166aa`), no `withdraw(address,uint256)` (`0xf3fef3a3`) and no `emergencyCancel` (`0xe898841f`); it has `withdraw(address)` (`0x51cff8d9`).
- **Addresses and wiring:** the live set comes from the Aori docs "Deployments" page and the live API `https://api.aori.io/chains`. On chain: `ENDPOINT_ID()` = 30101 / 30184 / 30110 / 30111 / 30102; `peers(eid)` of the live Ethereum contract gives Base, Arbitrum and Optimism `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6` and BNB, Plasma, Monad, Stable, MegaETH and Rootstock `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8`; the peers for 30106, 30109 and 30416 are zero; the Base and BNB contracts point back to `0x0736bdc975af0675b9a045384efed91360d25479`. `eip712Domain()` gives the version of each build (0.3.1, 0.4.0, 0.3.0, `1`). The 0.4.0 proxy was found through the owner EOA's transactions (a CREATE3 deployment on 2026-05-20 through `0x2dfcc7415d89af828cbef005f0d072d8b3f23183`) and matches the `v0.4.0` branch (`deploy/DEPLOY.md`: CREATE3, one address on every chain).
- **Chain coverage:** `eth_getCode` at `0x0736bdc975af0675b9a045384efed91360d25479`, `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6` and `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8` on all eight chains: code only where §9 shows it; `0x` on Polygon, Avalanche and Robinhood. The 0.4.0 proxy has code on seven chains and `0x` on Robinhood.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC** (all logs of each address):
  - Ethereum `0x0736bdc975af0675b9a045384efed91360d25479`: 42 logs — `Deposit` 11, `Fill` 10, `Settle` 10, `DstHookExecuted` 5, `Withdraw` 3, `SrcHookExecuted` 1, `Cancel` 1, `CancelSent` 1.
  - Base `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6`: 117 — `Settle` 38, `Deposit` 25, `Fill` 20, `SrcHookExecuted` 18, `DstHookExecuted` 11, `Withdraw` 4, `SettleSent` 1.
  - Arbitrum `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6`: 147 — `Settle` 65, `Deposit` 28, `Fill` 24, `DstHookExecuted` 16, `SettleSent` 5, `Withdraw` 4, `SrcHookExecuted` 3, `Cancel` 2.
  - Optimism `0xc6868edf1d2a7a8b759856cb8afa333210dfeda6`: 38 — `Settle` 16, `Deposit` 8, `Fill` 5, `DstHookExecuted` 5, `SrcHookExecuted` 2, `Withdraw` 2.
  - BNB `0xffe691a6ddb5d2645321e0a920c2e7bdd00dd3d8`: 104 — `Settle` 51, `Deposit` 17, `Fill` 17, `DstHookExecuted` 8, `SettleSent` 7, `Withdraw` 3, `SrcHookExecuted` 1.
  - 0.4.0 proxy `0xa041a8f5d796de4ae21da10e90908549c17d1107`: 0 on each of Ethereum, Base, Arbitrum, Optimism, Polygon, BNB and Avalanche. The 0.3.0 and `1` builds: 0 on every address checked. The same query returned the counts above for the live contracts (positive control).
- **Sample transactions (receipts read):** Ethereum `depositNative` `0x2fe319dd55af7417fb0f8d45894cdab467b62d063fe52a55914df32d1df45332` (block 26,072,227; 0.040469388039549396 ETH in `msg.value`; one `Deposit` log, no transfer log). Base hook `fill` `0x59d9d89b5b02d58b294a85e9727378e0418ecfca84b23f7f0bddab24c4bf3c27` (solver USDC to the hook, swap, WETH `Withdrawal`, `DstHookExecuted`, `Fill`; the native payout to the recipient has no log). Ethereum settlement `0x4613517432997eded58d09fa2c36b30732a4c8b612ce85596f3dc602c1106e5e` (8 `Settle` logs and one `PacketDelivered`, no transfer). Ethereum `withdraw` `0x1d62ef92bf196227f05aa0a2f1f16ea9e4124ae43e95186df5b787a24d21a189` (solver takes native ETH; one `Withdraw` log). Ethereum `Cancel` `0x109b4f4d6504ef7d77880e92b613ff5185622bac85ebc735b0b93363f1d0e6b3` (USDC `Transfer` Aori to offerer, `Cancel`, `PacketDelivered`). Ethereum `CancelSent` `0x67faebb2b5054d55ea2d4a2070ab1563f09002a45df02601a246ed802a2f2427` and Base `SettleSent` `0x29683f547094a5cc332d8d4cc0c662af74f703f88937bb71ce2e1a508588b650` (`srcEid` 30102; `PacketSent` in the same transaction).
- **Proxy and admin:** EIP-1967 implementation slot of `0x0736bdc975af0675b9a045384efed91360d25479` = 0 (not a proxy); implementation slot of the 0.4.0 proxy = `0xa38fca792cd722208ad367853c8cfd7c7ac1c36e` on seven chains, admin slot = 0 (UUPS). `owner()` = `0x941327e206b8d8cfe1014a8a95b05e1536dfd00d` on every live contract and on the 0.4.0 proxy (Ethereum and Arbitrum read); `eth_getCode` of the owner = `0x` on all eight chains (an EOA). `paused()` = false everywhere. `MAX_FILLS_PER_SETTLE()` = 100.

Authoritative sources:
- [aori-io/aori](https://github.com/aori-io/aori) — `contracts/Aori.sol`, `contracts/IAori.sol` (v0.3.1); branch [`v0.4.0`](https://github.com/aori-io/aori/tree/v0.4.0) — `contracts/interfaces/IAori.sol`, `contracts/types/AoriTypes.sol`, `deploy/DEPLOY.md`.
- Aori docs — [Deployments](https://docs.aori.io/protocol/deployments) · [Supported Chains](https://docs.aori.io/developers/chains) · [/chains reference](https://docs.aori.io/reference/chains); live API [`https://api.aori.io/chains`](https://api.aori.io/chains).
- [LayerZero deployments metadata](https://metadata.layerzero-api.com/v1/metadata/deployments) — endpoint ids, including Robinhood Chain 30416.
- Explorers — [Blockscout Aori (Ethereum)](https://eth.blockscout.com/address/0x0736bdc975af0675b9a045384efed91360d25479) · [Blockscout 0.4.0 proxy (Ethereum)](https://eth.blockscout.com/address/0xa041a8f5d796de4ae21da10e90908549c17d1107) · [Blockscout 0.4.0 proxy (Arbitrum)](https://arbitrum.blockscout.com/address/0xa041a8f5d796de4ae21da10e90908549c17d1107) · [Blockscout owner (Polygon)](https://polygon.blockscout.com/address/0x941327e206b8d8cfe1014a8a95b05e1536dfd00d).
