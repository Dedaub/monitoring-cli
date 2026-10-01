# deBridge DLN — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the deBridge "Deployed Contracts" page, the verified implementation sources on Blockscout, and the `debridge-finance/dln-contracts` and `debridge-finance/abis-and-idls` repositories. Topics and selectors recomputed as `keccak256(signature)`; addresses existence-checked with `eth_getCode`; EIP-1967 slots read live.
**Scope:** the deBridge Liquidity Network (DLN): `DlnSource` (order escrow), `DlnDestination` (fill, unlock, cancel), `DeBridgeRouter` (the swap forwarder that explorers label "Crosschain Forwarder"), `DlnExternalCallAdapter` and `ExternalCallExecutor` (hooks). DLN is live on all eight target chains: Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10), Polygon PoS (137), BNB Smart Chain (56), Avalanche C-Chain (43114) and Robinhood Chain (4663). The deBridgeGate message layer that settles DLN is in [dmp.md](dmp.md); the deBridge chain ids are in [README.md](README.md). Topics and selectors are chain-agnostic; addresses are per chain.

DLN is an intent bridge with no pooled liquidity. A maker locks the give tokens in `DlnSource` on the source chain (`CreatedOrder`). A solver (the taker) fills the order on the destination chain from its own funds through `DlnDestination.fulfillOrder`, which moves the take tokens straight to `receiverDst` (`FulfilledOrder`). The solver is repaid later on the source chain: it calls `sendEvmUnlock` (or a batch or Solana variant) on the destination (`SentOrderUnlock`), `DlnDestination` sends a deBridge message through deBridgeGate, and the Gate `claim` on the source chain calls `DlnSource.claimUnlock`, which pays the escrow to the solver (`ClaimedUnlock`).

There is no on-chain expiry. The only refund path is a cancel: the order authority on the destination (`orderAuthorityAddressDst`, or an account with `GOVERNANCE_DELEGATED_ORDER_CANCEL_ROLE` when the order names `allowedCancelBeneficiarySrc`) calls `sendEvmOrderCancel` or `sendSolanaOrderCancel` on an unfilled order (`SentOrderCancel`), and the message makes `DlnSource.claimCancel` return the escrow to the cancel beneficiary (`ClaimedOrderCancel`).

Three facts to know before indexing:

1. **The five DLN addresses are the same literal on seven chains** (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche). Robinhood Chain has the same `DlnSource`, `DlnDestination` and `DeBridgeRouter` addresses, but a different `DlnExternalCallAdapter` and `ExternalCallExecutor` pair, and it uses OpenZeppelin v5 proxies with EOA-owned ProxyAdmins (§8).
2. **No DLN event parameter is indexed.** `orderId` sits in the data of every DLN event. Filter by `(emitter, topic0)` and decode the data. The join key `orderId` is on chain on both sides.
3. **The event schema changed twice on Ethereum.** `CreatedOrder` gained `bytes metadata` at block 18,092,917, and `FulfilledOrder` gained `uint256 actualFulfillAmount` at block 24,447,763 (both through a Safe transaction that upgraded the proxies). Both legacy topics are in §1 for back-fills; the legacy topics had 0 logs in the pinned window.

---

## 0. Contract families & versions

| Contract | Chains | Role | Proxy |
|----------|--------|------|-------|
| **DlnSource** | all 8 | Order escrow on the source chain. Pulls the give tokens, emits `CreatedOrder`, pays the solver on `claimUnlock`, refunds on `claimCancel`. Version string `1.8.0` (live `version()` read). | EIP-1967 transparent |
| **DlnDestination** | all 8 | Fill entrypoint on the destination chain. Emits `FulfilledOrder`, sends the unlock and cancel messages through deBridgeGate. Version string `1.7.1` (live `version()` read). | EIP-1967 transparent |
| **DeBridgeRouter** (explorer label "Crosschain Forwarder Proxy") | all 8 | Swap forwarder that the DLN API uses before `createOrder` and before `fulfillOrder`, and for same-chain swaps. Returns the surplus with `Refund`. | EIP-1967 transparent |
| **DlnExternalCallAdapter** | all 8 (other address on Robinhood) | Holds the take tokens of an order with a hook and runs the hook through the executor. | EIP-1967 transparent |
| **ExternalCallExecutor** | all 8 (other address on Robinhood) | The universal hook: runs the calls of the hook payload with the tokens. | not a proxy |
| deBridgeGate + CallProxy | all 8 | Message layer that carries the unlock and cancel messages. See [dmp.md](dmp.md). | EIP-1967 transparent |

The give side and the take side use deBridge chain ids (`giveChainId`, `takeChainId`), not always the EVM chain id. For the eight target chains they are equal; Solana is `7565164`. See [README.md](README.md).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 DlnSource — source leg, escrow payout, refund

Emitter: `DlnSource` `0xeF4fB24aD0916217251F553c0596F8Edc630EB66` on all eight chains.

| topic0 | Event | Side |
|--------|-------|------|
| `0xfc8703fd57380f9dd234a89dce51333782d49c5902f307b02f03e014d18fe471` | `CreatedOrder((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) order, bytes32 orderId, bytes affiliateFee, uint256 nativeFixFee, uint256 percentFee, uint32 referralCode, bytes metadata)` | **Source leg (deposit).** Current schema. |
| `0x47ef43a379911343a1cc752617be7096d678feac64600f0f94e63062722735af` | `CreatedOrder((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) order, bytes32 orderId, bytes affiliateFee, uint256 nativeFixFee, uint256 percentFee, uint32 referralCode)` | Source leg, **legacy** schema without `metadata`. Ethereum logs from block 16,391,639 to the upgrade at block 18,092,917. |
| `0x33fff3d864e92b6e1ef9e830196fc019c946104ea621b833aaebd3c3e84b2f6f` | `ClaimedUnlock(bytes32 orderId, address beneficiary, uint256 giveAmount, address giveTokenAddress)` | **Escrow pays the solver.** `giveTokenAddress` = `0x0000000000000000000000000000000000000000` for native. |
| `0x7d7d1c5b3eadbe275ceb358e65cd57410b35997187258dbaaae42ab6e1405fd8` | `ClaimedOrderCancel(bytes32 orderId, address beneficiary, uint256 paidAmount, address giveTokenAddress)` | **Refund.** `paidAmount` = `giveAmount + percentFee + affiliate amount`; the fixed native fee goes back in a separate native transfer. |
| `0x9077c15d8bcf2d51f89ed4806cf2fd3d09000b446acd62c04653da6684ee16f0` | `AffiliateFeePaid(bytes32 _orderId, address beneficiary, uint256 affiliateFee, address giveTokenAddress)` | Pair of `ClaimedUnlock` when the order carries an affiliate fee. |
| `0xc65cdb43047b7466a1705cf4c7e88b0c66614ed6da1c1aa7f44026cee8e67626` | `UnexpectedOrderStatusForClaim(bytes32 orderId, uint8 status, address beneficiary)` | Status only: an unlock arrived for an order that is not in state `Created`. No value moves. |
| `0x9302619b5552484dceb0055d13a6b83805ce74ad349b433cf78be991ef30703e` | `UnexpectedOrderStatusForCancel(bytes32 orderId, uint8 status, address beneficiary)` | Status only: a cancel arrived for an order that is not in state `Created`. |
| `0x29af03f84291900300e96b03eed8a02c0db5cdc94a3b15a880a93bfce8c125a2` | `CriticalMismatchChainId(bytes32 orderId, address beneficiary, uint256 takeChainId, uint256 submissionChainIdFrom)` | **Circuit breaker, high severity.** An unlock came from a chain that is not the order's take chain; no payout. |
| `0xf514ec418ee1c6415457f9d409a2f2260e3f0de7810b38d64058832c2c2e1076` | `UnclaimedAffiliateFees(bytes32 orderId, address token, uint256 amount)` | Affiliate transfer failed; the fee stays in the contract. |
| `0x3edbbf5265d88dacff1e41ac68c53694b9e9352c53c0b707f84ea2922d50b75b` | `UnclaimedAffiliateFeePaid(address beneficiary, uint256 amount, address token)` | Later withdrawal of an unclaimed affiliate fee. |
| `0x4f3bc5fae93ae03632b30b624fb1dbfa21466a29216f314d0cfcb269d7c918ff` | `IncreasedGiveAmount(bytes32 orderId, uint256 orderGiveFinalAmount, uint256 finalPercentFee)` | **Legacy.** `patchOrderGive` is not in the current implementation (selector absent from the bytecode). |
| `0x82568678a169f202360005e72d5ab10d95c3c369ddd502057dacb85e9c700759` | `SetDlnDestinationAddress(uint256 chainIdTo, bytes dlnDestinationAddress, uint8 chainEngine)` | Admin: trusted peer per chain (`chainEngine` 1 = EVM, 2 = Solana). |
| `0x036e7dece8303b57678319debe761b27c7298611a5c4e23776a7f1e79c67742a` | `WithdrawnFee(address tokenAddress, uint256 amount, address beneficiary)` | Protocol fee withdrawal. |
| `0x326751b7ae705d9d8353edbd289cc14a323875cf13ddc42f7575ac304e417fc2` | `GlobalFixedNativeFeeUpdated(uint88 oldGlobalFixedNativeFee, uint88 newGlobalFixedNativeFee)` | Admin: flat fee change. |
| `0x013cd5c0fbece94c68f9e668b3ab52cdf65f1ee39fb338ac4c803fe21fe043e0` | `GlobalTransferFeeBpsUpdated(uint16 oldGlobalTransferFeeBps, uint16 newGlobalTransferFeeBps)` | Admin: percent fee change (4 bps on Ethereum, live read). |

### 1.2 DlnDestination — destination leg, unlock and cancel messages

Emitter: `DlnDestination` `0xE7351Fd770A37282b91D153Ee690B63579D6dd7f` on all eight chains.

| topic0 | Event | Side |
|--------|-------|------|
| `0xc164aca37b9805a1c9027b6f32260a069723a82926f6e9ece4926e4dd3ea8ecf` | `FulfilledOrder((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) order, bytes32 orderId, uint256 actualFulfillAmount, address sender, address unlockAuthority)` | **Destination leg (payout).** Current schema. `sender` = the caller of `fulfillOrder` (a solver or `DeBridgeRouter`); `unlockAuthority` = the solver that may unlock. |
| `0xd281ee92bab1446041582480d2c0a9dc91f855386bb27ea295faac1e992f7fe4` | `FulfilledOrder((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) order, bytes32 orderId, address sender, address unlockAuthority)` | Destination leg, **legacy** schema. Ethereum logs from block 16,565,438 to the upgrade at block 24,447,763. |
| `0x37a01d7dc38e924008cf4f2fa3d2ec1f45e7ae3c8292eb3e7d9314b7ad10e2fc` | `SentOrderUnlock(bytes32 orderId, bytes beneficiary, bytes32 submissionId)` | Message: unlock sent to the source chain. Status only on this chain (the value moves later on the source chain). `submissionId` = the Gate `Sent.submissionId` in the same transaction. One Gate message can carry many orders. |
| `0xc756fd0227d1d70cec0ead41b16a90a1cac618da1d612cb5d0b72d93301369de` | `SentOrderCancel((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) order, bytes32 orderId, bytes cancelBeneficiary, bytes32 submissionId)` | Message: cancel sent to the source chain. Status only on this chain; the order can no longer be filled. |
| `0x08c645e3c369cf85ec8e864f27821c61ceba80fa78f2f66fb0d042a4b29e794b` | `DecreasedTakeAmount(bytes32 orderId, uint256 orderTakeFinalAmount)` | **Legacy.** `patchOrderTake` is not in the current implementation. |
| `0x1a6f092b051adc658eb15cab830c00ed3eff5b9683f8bf9cf94ada7f53ab20e0` | `SetDlnSourceAddress(uint256 chainIdFrom, bytes dlnSourceAddress, uint8 chainEngine)` | Admin: trusted source per chain. |
| `0x3a2e8bb48b6b66181a226c06b9c44dd5c701a925c5b3274df2fc67ec2a097f47` | `ExternalCallAdapterUpdated(address oldAdapter, address newAdapter)` | Admin: hook adapter rotation. |
| `0x1ee3af6f21510717555493063d6a19e9b4e6c89d1c17661252a7958a20dbe5cc` | `MaxOrderCountPerBatchEvmUnlockChanged(uint256 oldValue, uint256 newValue)` | Admin. |
| `0x9930eaf5503acbebf3b062708c9de948e32ed72a48e59a1cd246b8624e0e89b7` | `MaxOrderCountPerBatchSolanaUnlockChanged(uint256 oldValue, uint256 newValue)` | Admin. |

### 1.3 DeBridgeRouter (Crosschain Forwarder) — swaps around DLN

Emitter: `0x663DC15D3C1aC63ff12E45Ab68FeA3F0a883C251` on all eight chains.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x149635d19f798f6b7c74c74a500d362c89316a0ab808abe5e0c0de45da9b1d2c` | `Refund(address token, uint256 amount, address recipient)` | Swap surplus returned to `recipient`; `token` = `0x0000000000000000000000000000000000000000` for native. Moves value. |
| `0xdde2f3711ab09cdddcfee16ca03e54d21fb8cf3fa647b9797913c950d38ad693` | `SwapExecuted(address router, address tokenIn, uint256 amountIn, address tokenOut, uint256 amountOut)` | The swap before `createOrder` or `fulfillOrder`, and inside same-chain swaps. |
| `0xecfedc7a2bb58de8119427cef1d856aa76747d4a6e13307a7ca485bf8df20904` | `SameChainSwapExecuted(address sender, address recipient, address tokenIn, uint256 amountIn, address tokenOut, uint256 amountOut, uint256 fee, uint256 affiliateFee, uint32 referralCode)` | Same-chain swap, not a bridge. Most Base router traffic. |
| `0x6a0f4594999005114d250d0dce53dea802de70666f009552d1aa0b39e5846361` | `AffiliateFeePaid(address token, uint256 amount, address recipient, uint32 referralCode)` | Router variant; different topic0 from the `DlnSource` event of the same name. |
| `0x5a7af898dfbf9d56c66a7883a2e9229f5c9ff2484d9525f2c80cff815e232827` | `CollectedFee(address token, uint256 amount)` | Swap fee kept by the router. |
| `0x3fc30fe9d1afedc310e6ec6fd5f84b0ae3b800cdc1bcb04b65b986fdd35868f0` | `SupportedRouter(address srcSwapRouter, bool isSupported)` | Admin: swap router allow-list. |
| `0x10d6c00fd9d176c2872e8e72b76641ca85aba29bb682a658aeedbc38814fe45f` | `FeeTreasuryUpdated(address feeTreasury)` | Admin. |
| `0x6b24b4ecbdb33b853813a087738a34121649900030572f4286ddf4ad24586386` | `SwapVariableFeeBpsUpdated(uint16 swapVariableFeeBps)` | Admin. |
| `0x17acbaf0bcb36a981255b884e821edcf811a3b401972432678b01cd1a7f0d500` | `AllowanceAggregatorUpdated(address router, address allowanceAggregator)` | Admin. |

### 1.4 DlnExternalCallAdapter — hooks

Emitter: `0x61eF2e01E603aEB5Cd96F9eC9AE76cc6A68f6cF9` on seven chains; `0xE93356b0b87c71A7F4957DCEBEd05BefA8cB624a` on Robinhood Chain.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xe0320f35b1ebe381c5ff7355f4c6ed81fe49413c4becf1e730b666d199908b69` | `ExternalCallExecuted(bytes32 orderId, bool callSucceeded)` | Emitted after every hook run, also a failed one (then `ExternalCallFailed` follows). The executor sends failed or unused tokens to the fallback address of the hook. |
| `0xfaebec5591353214b140dec3700150f47d7b1296e981c3498df1b37a6b953c23` | `ExternalCallFailed(bytes32 orderId, bytes callResult)` | Status only: the executor reverted; `callResult` is the revert data. |
| `0xcb08fcc129e6e8f0ddd452cbd1380b0451cd7fe881d34a9c9618e66dde77ebb8` | `ExternalCallRegistered(bytes32 callId, bytes32 orderId, address callAuthority, address tokenAddress, uint256 amount, bytes externalCall)` | The hook was stored for later execution; the tokens stay in the adapter. Current spelling. |
| `0x302c1fa26313337086ce999d06b9e355079ef09ed4c18919b069147273033353` | `ExternallCallRegistered(bytes32 callId, bytes32 orderId, address callAuthority, address tokenAddress, uint256 amount, bytes externalCall)` | **Legacy** misspelled event of the older ABI; its topic0 is not in the current implementation bytecode. |
| `0x00dcd3c81b3e3b2f9c553348615a4f541f4d464c7f57a6fa096a27f4b1310ab2` | `ExternalCallCancelled(bytes32 callId, bytes32 orderId, address cancelBeneficiary, address tokenAddress, uint256 amount)` | A stored hook was cancelled; the tokens go to `cancelBeneficiary`. Moves value. |
| `0x0ef3c7eb9dbcf33ddf032f4cce366a07eda85eed03e3172e4a90c4cc16d57886` | `ExecutorUpdated(address oldExecutor, address newExecutor)` | Admin: executor rotation. |

`ExternalCallExecutor` emits only the role events of §1.5.

### 1.5 Admin and proxy events (all DLN contracts)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | `DlnSource`, `DlnDestination`, adapter. Pause needs `GOVMONITORING_ROLE`; unpause needs the admin role. |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | Role ids in §2.6. |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` | |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | **Implementation change on any DLN proxy.** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | ProxyAdmin change. |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` | Emitted on (re)initialization. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Every selector below was found in the current implementation bytecode on Ethereum, except the rows marked legacy.

### 2.1 DlnSource

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfbe16ca7` | `createOrder((address giveTokenAddress, uint256 giveAmount, bytes takeTokenAddress, uint256 takeAmount, uint256 takeChainId, bytes receiverDst, address givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes externalCall, bytes allowedCancelBeneficiarySrc) _orderCreation, bytes _affiliateFee, uint32 _referralCode, bytes _permitEnvelope)` | Payable. Pulls `giveAmount` from the caller; `msg.value` carries the flat fee (plus `giveAmount` for native). Emits `CreatedOrder`. |
| `0xb9303701` | `createSaltedOrder((address giveTokenAddress, uint256 giveAmount, bytes takeTokenAddress, uint256 takeAmount, uint256 takeChainId, bytes receiverDst, address givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes externalCall, bytes allowedCancelBeneficiarySrc) _orderCreation, uint64 _salt, bytes _affiliateFee, uint32 _referralCode, bytes _permitEnvelope, bytes _metadata)` | Payable. The order nonce is the salt (deterministic `orderId`). The entrypoint the API uses. |
| `0xafbfe366` | `createSaltedOrderForIntent((address giveTokenAddress, uint256 giveAmount, bytes takeTokenAddress, uint256 takeAmount, uint256 takeChainId, bytes receiverDst, address givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes externalCall, bytes allowedCancelBeneficiarySrc) _orderCreation, uint64 _salt, uint32 _referralCode, uint256 _giveTokenFeeAmount, bytes _metadata)` | Payable. `INTENT_MANAGER_ROLE` only; the fee is taken in the give token. |
| `0xbaa0d37f` | `createSaltedOrderForIntent((address giveTokenAddress, uint256 giveAmount, bytes takeTokenAddress, uint256 takeAmount, uint256 takeChainId, bytes receiverDst, address givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes externalCall, bytes allowedCancelBeneficiarySrc) _orderCreation, address _maker, uint64 _salt, uint32 _referralCode, uint256 _giveTokenFeeAmount, bytes _metadata)` | Payable. Order on behalf of `_maker` (intent manager role). |
| `0x5886d8d2` | `claimUnlock(bytes32 _orderId, address _beneficiary)` | Only the CallProxy of deBridgeGate, with a message from the trusted `DlnDestination`. Emits `ClaimedUnlock`. |
| `0x6abd4ea7` | `claimBatchUnlock(bytes32[] _orderIds, address _beneficiary)` | Batch form; one `ClaimedUnlock` per order. |
| `0xd48b0146` | `claimCancel(bytes32 _orderId, address _beneficiary)` | Only the CallProxy. Emits `ClaimedOrderCancel`. |
| `0x924a062c` | `claimBatchCancel(bytes32[] _orderIds, address _beneficiary)` | Batch form. |
| `0x30bb0911` | `setDlnDestinationAddress(uint256 _chainIdTo, bytes _dlnDestinationAddress, uint8 _chainEngine)` | Admin. |
| `0x6ac89fa2` | `updateGlobalFee(uint88 _globalFixedNativeFee, uint16 _globalTransferFeeBps)` | Admin. |
| `0x8456cb59` | `pause()` | `GOVMONITORING_ROLE`. |
| `0x3f4ba83a` | `unpause()` | Admin. |
| `0x169770cb` | `withdrawCollectedFees(address[] _tokens)` | Fee collector role. |
| `0x1c8de947` | `withdrawUnclaimedAffiliateFees(address[] _tokens, address _beneficiary)` | |
| `0x50e95591` | `getOrderId((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) _order)` | Pure. `orderId` = `keccak256` of the packed order (the hook enters as its hash). |
| `0xb2a453f8` | `giveOrders(bytes32)` | View: order state on the source chain (status 1 = Created, 2 = ClaimedUnlock, 3 = ClaimedCancel). |
| `0xdf21dc1d` | `masterNonce(address)` | View: next non-salted nonce of a maker. |
| `0x35087f0a` | `globalFixedNativeFee()` | View: 0.001 ETH on Ethereum (live read). |
| `0x5c837198` | `globalTransferFeeBps()` | View: 4 on Ethereum (live read). |
| `0xca777fbf` | `deBridgeGate()` | View: the Gate that carries the messages (Base returns `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF`). |
| `0x14bb1361` | `dlnDestinationAddresses(uint256)` | View: trusted destination per chain id. |
| `0xb5bbf6e1` | `patchOrderGive((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) _order, uint256 _addGiveAmount, bytes _permitEnvelope)` | **Legacy** (older ABI). Not in the current bytecode. |

### 2.2 DlnDestination

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc358547e` | `fulfillOrder((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) _order, uint256 _fulFillAmount, bytes32 _orderId, bytes _permitEnvelope, address _unlockAuthority)` | Payable. Moves the take token from the caller to `receiverDst` (or to the adapter for a hook). Emits `FulfilledOrder`. |
| `0x0ebcd2f6` | `fulfillOrder((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) _order, uint256 _fulFillAmount, bytes32 _orderId, bytes _permitEnvelope, address _unlockAuthority, address _externalCallRewardBeneficiary)` | Payable. Hook-aware form. |
| `0xb41100b3` | `sendEvmUnlock(bytes32 _orderId, address _beneficiary, uint256 _executionFee)` | Payable. Only the `unlockAuthority`. Emits `SentOrderUnlock` and a Gate `Sent`. |
| `0x5b5a646e` | `sendBatchEvmUnlock(bytes32[] _orderIds, address _beneficiary, uint256 _executionFee)` | Payable. One Gate message for many orders. |
| `0xa6a5ae52` | `sendSolanaUnlock((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) _order, bytes32 _beneficiary, uint256 _executionFee, uint64 _initWalletIfNeededInstructionReward, uint64 _claimUnlockInstructionReward)` | Payable. Unlock of an order that came from Solana. |
| `0x40968794` | `sendBatchSolanaUnlock((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall)[] _orders, bytes32 _beneficiary, uint256 _executionFee, uint64 _initWalletIfNeededInstructionReward, uint64 _claimUnlockInstructionReward)` | Payable. Batch Solana unlock. |
| `0xd38d9626` | `sendEvmOrderCancel((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) _order, address _cancelBeneficiary, uint256 _executionFee)` | Payable. Only `orderAuthorityAddressDst` or the delegated cancel role. Emits `SentOrderCancel`. |
| `0x9327145d` | `sendSolanaOrderCancel((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) _order, bytes32 _cancelBeneficiary, uint256 _executionFee, uint64 _initWalletIfNeededInstructionReward, uint64 _claimCancelInstructionReward)` | Payable. Cancel of a Solana-origin order. |
| `0xe04542ce` | `setDlnSourceAddress(uint256 _chainIdFrom, bytes _dlnSourceAddress, uint8 _chainEngine)` | Admin. |
| `0xde5eff0a` | `setExternalCallAdapter(address _externalCallAdapter)` | Admin. |
| `0xf733f65e` | `setMaxOrderCountsPerBatch(uint256 _newEvmCount, uint256 _newSolanaCount)` | Admin. |
| `0x5b2f30e9` | `takeOrders(bytes32)` | View: fill state and unlock authority of an order on the destination. |
| `0x85d8e978` | `dlnSourceAddresses(uint256)` | View: trusted source per chain id. |
| `0x51f228b4` | `patchOrderTake((uint64 makerOrderNonce, bytes makerSrc, uint256 giveChainId, bytes giveTokenAddress, uint256 giveAmount, uint256 takeChainId, bytes takeTokenAddress, uint256 takeAmount, bytes receiverDst, bytes givePatchAuthoritySrc, bytes orderAuthorityAddressDst, bytes allowedTakerDst, bytes allowedCancelBeneficiarySrc, bytes externalCall) _order, uint256 _newSubtrahend)` | **Legacy** (older ABI). Not in the current bytecode. |

### 2.3 DeBridgeRouter (Crosschain Forwarder)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4d8160ba` | `strictlySwapAndCall(address _srcTokenIn, uint256 _srcAmountIn, bytes _srcTokenInPermitEnvelope, address _srcSwapRouter, bytes _srcSwapCalldata, address _srcTokenOut, uint256 _srcTokenExpectedAmountOut, address _srcTokenRefundRecipient, address _target, bytes _targetData)` | Payable. Source side: swap, then call `_target` (usually `DlnSource`). Emits `SwapExecuted` and `Refund`. |
| `0xc7a76969` | `strictlySwapAndCallDln(address _srcTokenIn, uint256 _srcAmountIn, bytes _srcTokenInPermitEnvelope, (address swapRouter, bytes swapCalldata, address tokenOut, uint256 tokenOutMinAmount, address tokenOutRefundRecipient) _swapDetails, address _target, bytes _targetData, bytes32 _orderId)` | Payable. Destination side: a solver swaps, then calls `DlnDestination.fulfillOrder`. The payout transfer then comes from the router. |
| `0x6391c75b` | `fillCrossChain(address _tokenIn, uint256 _amountIn, (address swapRouter, bytes swapCalldata, address tokenOut, uint256 tokenOutMinAmount, address tokenOutRefundRecipient) _swapDetails, bytes _dlnDestinationCalldata, uint256 _maxDlnFulfillAmount)` | Payable. Swap-and-fill. |
| `0x258c16ee` | `swap(address _tokenIn, uint256 _amountIn, bytes _tokenInPermitEnvelope, (address allowanceAggregator, address swapRouter, bytes swapCalldata, address tokenOut, uint256 tokenOutMinAmount, uint16 surplusShareBps, bytes affiliateFeeEnvelope, address recipient) _swapDetails, uint32 _referralCode)` | Payable. Same-chain swap; emits `SameChainSwapExecuted`. |
| `0x6ccae054` | `rescueFunds(address token, address recipient, uint256 amount)` | **Admin: moves any balance of the router.** |
| `0xd33f532e` | `updateSupportedRouter(address _srcSwapRouter, bool _isSupported)` | Admin. |
| `0x8fca8a02` | `updateSwapVariableFeeBps(uint16 _swapVariableFeeBps)` | Admin. |
| `0xd4a0d4c6` | `updateFeeTreasury(address _feeTreasury)` | Admin. |
| `0xab804a47` | `updateAllowanceAggregator(address _router, address _allowanceAggregator)` | Admin. |
| `0x1624eaf3` | `sendV2(address _srcTokenIn, uint256 _srcAmountIn, bytes _srcTokenInPermitEnvelope, (uint256 chainId, address receiver, bool useAssetFee, uint32 referralCode, bytes autoParams) _gateParams)` | **Legacy** forwarder (older ABI, sends through deBridgeGate). Not in the current bytecode. |
| `0xcbe51902` | `sendV3(address _srcTokenIn, uint256 _srcAmountIn, bytes _srcTokenInPermitEnvelope, uint256 _affiliateFeeAmount, address _affiliateFeeRecipient, (uint256 chainId, address receiver, bool useAssetFee, uint32 referralCode, bytes autoParams) _gateParams)` | **Legacy.** |
| `0x5dfd9bc3` | `swapAndSendV2(address _srcTokenIn, uint256 _srcAmountIn, bytes _srcTokenInPermitEnvelope, address _srcSwapRouter, bytes _srcSwapCalldata, address _srcTokenOut, (uint256 chainId, address receiver, bool useAssetFee, uint32 referralCode, bytes autoParams) _gateParams)` | **Legacy.** |
| `0x5c5c5701` | `swapAndSendV3(address _srcTokenIn, uint256 _srcAmountIn, bytes _srcTokenInPermitEnvelope, uint256 _affiliateFeeAmount, address _affiliateFeeRecipient, address _srcSwapRouter, bytes _srcSwapCalldata, address _srcTokenOut, (uint256 chainId, address receiver, bool useAssetFee, uint32 referralCode, bytes autoParams) _gateParams)` | **Legacy.** |

### 2.4 DlnExternalCallAdapter and ExternalCallExecutor

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xef35accb` | `receiveCall(bytes32 _orderId, address _callAuthority, address _tokenAddress, uint256 _transferredAmount, bytes _externalCall, address _externalCallRewardBeneficiary)` | Adapter. Only `DlnDestination`. Runs or stores the hook. |
| `0x529c02d5` | `executeCall(bytes32 _orderId, address _callAuthority, address _tokenAddress, uint256 _tokenAmount, bytes _externalCall, address _rewardBeneficiary)` | Adapter. Runs a stored hook. |
| `0x78de8697` | `cancelCall(bytes32 _orderId, address _callAuthority, address _tokenAddress, uint256 _tokenAmount, address _recipient, bytes32 _externalCallHash)` | Adapter. Cancels a stored hook; emits `ExternalCallCancelled`. |
| `0x74936c16` | `updateExecutor(address _newExecutor)` | Adapter. Admin. |
| `0x7cbf7a55` | `onERC20Received(bytes32, address _token, uint256 _transferredAmount, address _fallbackAddress, bytes _payload)` | Executor. Hook with ERC-20. |
| `0x3d266812` | `onEtherReceived(bytes32, address _fallbackAddress, bytes _payload)` | Executor. Hook with native value. |
| `0x6ccae054` | `rescueFunds(address _token, address _recipient, uint256 _amount)` | Executor. Admin. Same selector as the router function. |

### 2.5 Proxy administration

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9623609d` | `upgradeAndCall(address proxy, address implementation, bytes data)` | ProxyAdmin (OpenZeppelin v4 and v5). Emits `Upgraded` at the proxy. |
| `0x99a88ec4` | `upgrade(address proxy, address implementation)` | ProxyAdmin v4 only (seven chains). Not in the v5 ProxyAdmins of Robinhood Chain. |
| `0x7eff275e` | `changeProxyAdmin(address proxy, address newAdmin)` | ProxyAdmin v4 only. Emits `AdminChanged`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | ProxyAdmin ownership change. |
| `0x2f2ff15d` | `grantRole(bytes32 role, address account)` | Access control on every DLN contract. |
| `0xd547741f` | `revokeRole(bytes32 role, address account)` | |
| `0x91d14854` | `hasRole(bytes32 role, address account)` | View. |

### 2.6 Role ids (AccessControl `bytes32`, not topics)

| Role | Value | Power |
|------|-------|-------|
| `DEFAULT_ADMIN_ROLE` | `0x0000000000000000000000000000000000000000000000000000000000000000` | Admin setters, unpause, role grants. |
| `GOVMONITORING_ROLE` | `0x2b36fa99e118fa8485d488becf749a974743fbeb6a7aa57e663893bf5d69a3c1` | Pause. |
| `GOVERNANCE_DELEGATED_ORDER_CANCEL_ROLE` | `0x01bd451848033b83db2d5c21b44e19dc2cf0e3067ae17fafefe1ac665572eeb3` | Cancel on `DlnDestination` any unfilled order that names `allowedCancelBeneficiarySrc` (auto-cancel). Granted on Ethereum to `0x0746E7E4D15f30885616b4ac3D274393354e80C0` at block 24,447,763; `hasRole` returns true (live read). |
| `FEE_COLLECTOR_ROLE` | `0x2dca0f5ce7e75a4b43fe2b0d6f5d0b7a2bf92ecf89f8f0aa17b8308b67038821` | Withdraw collected fees. |
| `INTENT_MANAGER_ROLE` | `0xa9b1eae7c8b7c72093bc47a90b3ed7fc095a355afd9f411e17e6cb1325a3d571` | Both `createSaltedOrderForIntent` forms (orders on behalf of a maker). |
| `ADAPTER_ROLE` | `0xdbeb657137b1822b3d5418bea6fd641226d964b4c3871ef23546db2622258871` | On `ExternalCallExecutor`: the adapter that may call `onERC20Received` and `onEtherReceived`. |
| `DEBRIDGE_GATE_ROLE` | `0xd5a6101e940ba33e226d2395b16238ab3063d7ee83d7b3ff59cb92988b395437` | On CallProxy: the Gate that may call it (see [dmp.md](dmp.md)). |

---

## 3. Addresses — Ethereum (chain ID 1)

All verified with `eth_getCode` on 2026-09-29. Wiring checked live: `DlnSource.deBridgeGate()` returns `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA`.

| Role | Address | One-liner |
|------|---------|-----------|
| **DlnSource** (proxy) | `0xeF4fB24aD0916217251F553c0596F8Edc630EB66` | Order escrow. Implementation `0x2b426a0ac391490e88d15b304436e7a84df78611` (22,952 bytes). |
| **DlnDestination** (proxy) | `0xE7351Fd770A37282b91D153Ee690B63579D6dd7f` | Fill and messages. Implementation `0xd9b4f9cacffb59f2b982ad3c45096e3aa4b4020e` (23,205 bytes). |
| **DeBridgeRouter** (proxy) | `0x663DC15D3C1aC63ff12E45Ab68FeA3F0a883C251` | Swap forwarder. Implementation `0xce56012e880851baa234cd092af516a0fca9cfe3` (17,691 bytes). |
| **DlnExternalCallAdapter** (proxy) | `0x61eF2e01E603aEB5Cd96F9eC9AE76cc6A68f6cF9` | Hook engine. Implementation `0xe143dbaec892cef2af836db49870a0bcf9d5e6a1` (9,663 bytes). |
| **ExternalCallExecutor** | `0xAE0361b1C3454b297129e01046057F1D294c7974` | Universal hook; 6,213 bytes, not a proxy. |
| ProxyAdmin (DLN contracts and adapter) | `0xa7b88a746fa457578d5abd6234471f07d895f46b` | Owner `0x6bec1faf33183e1bc316984202ecc09d46ac92d5` (Safe, threshold 5). |
| ProxyAdmin (DeBridgeRouter) | `0xc86ab72dc6da7ef91a96650f3bc23125cd997130` | Owner `0x6bec1faf33183e1bc316984202ecc09d46ac92d5`. |
| Safe (upgrade authority) | `0x6bec1faf33183e1bc316984202ecc09d46ac92d5` | Safe proxy (171 bytes); `getThreshold()` = 5. Executed both schema upgrades. |

## 4. Addresses — the other six chains with the Ethereum literals

The five DLN addresses of §3 hold code on each chain below (same proxy literal; same implementation address unless noted). Implementation code hashes match Ethereum except where noted.

### 4.1 Base (chain ID 8453)

| Role | Address / value |
|------|-----------------|
| DlnSource, DlnDestination, DeBridgeRouter, DlnExternalCallAdapter, ExternalCallExecutor | Same literals as §3. Proxy code 2,112 bytes (DeBridgeRouter 2,733 bytes). |
| Implementations | Same addresses as §3; the `DlnSource` and `DlnDestination` implementation code hashes differ from Ethereum (same size, same event topics in the bytecode). |
| ProxyAdmins | `0xa7b88a746fa457578d5abd6234471f07d895f46b` (DLN) and `0xc86ab72dc6da7ef91a96650f3bc23125cd997130` (router); owner Safe `0xf0a9d50f912d64d1105b276526e21881bf48a29e` (threshold 5). |
| deBridgeGate wired in | `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` (live `deBridgeGate()` read). Not the Ethereum Gate literal. |

### 4.2 Arbitrum One (chain ID 42161)

| Role | Address / value |
|------|-----------------|
| All five DLN contracts | Same literals and implementations as §3 (proxy code hashes identical to Ethereum). |
| ProxyAdmins | `0xa7b88a746fa457578d5abd6234471f07d895f46b`, `0xc86ab72dc6da7ef91a96650f3bc23125cd997130`; owner Safe `0xa52842cd43fa8c4b6660e443194769531d45b265` (threshold 5). |

### 4.3 Optimism (chain ID 10)

| Role | Address / value |
|------|-----------------|
| All five DLN contracts | Same literals and implementations as §3 (DeBridgeRouter proxy code 2,733 bytes). |
| ProxyAdmins | Same two addresses; owner Safe `0xa52842cd43fa8c4b6660e443194769531d45b265` (threshold 5). |

### 4.4 Polygon PoS (chain ID 137)

| Role | Address / value |
|------|-----------------|
| All five DLN contracts | Same literals and implementations as §3. |
| ProxyAdmins | Same two addresses; owner Safe `0xa52842cd43fa8c4b6660e443194769531d45b265` (threshold 5). |

### 4.5 BNB Smart Chain (chain ID 56)

| Role | Address / value |
|------|-----------------|
| All five DLN contracts | Same literals and implementations as §3. |
| ProxyAdmins | Same two addresses; owner Safe `0xa52842cd43fa8c4b6660e443194769531d45b265` (threshold 5). |

### 4.6 Avalanche C-Chain (chain ID 43114)

| Role | Address / value |
|------|-----------------|
| All five DLN contracts | Same literals and implementations as §3. |
| ProxyAdmins | Same two addresses; owner Safe `0x8ac842e8f3be6bf67ccfdc87ce3f98d635008ef0` (threshold 5). |

## 5. Addresses — Robinhood Chain (chain ID 4663)

Listed in the deBridge deployed-contracts table and verified with `eth_getCode` on `https://rpc.mainnet.chain.robinhood.com`. `getChainId()` on `DlnSource` returns 4663. The proxies are OpenZeppelin v5 transparent proxies (1,159 bytes); each has its own ProxyAdmin, and each ProxyAdmin is owned by an EOA.

| Role | Address | One-liner |
|------|---------|-----------|
| **DlnSource** (proxy) | `0xeF4fB24aD0916217251F553c0596F8Edc630EB66` | Implementation `0x5cd55233c3302f2a3b137d458e00bd232998903d` (22,952 bytes; own code hash). |
| **DlnDestination** (proxy) | `0xE7351Fd770A37282b91D153Ee690B63579D6dd7f` | Implementation `0x223e1c3cec6d1179137ef023e74b98b739657644` (code hash identical to the Ethereum implementation). |
| **DeBridgeRouter** (proxy) | `0x663DC15D3C1aC63ff12E45Ab68FeA3F0a883C251` | Implementation `0x42ac5bc3c01378e8cf6905bade700fddb881b076` (code hash identical to Ethereum). |
| **DlnExternalCallAdapter** (proxy) | `0xE93356b0b87c71A7F4957DCEBEd05BefA8cB624a` | Implementation `0x35367bfb350974a206f3bee2fa6431157e046854` (code hash identical to Ethereum). **Not** `0x61eF2e01E603aEB5Cd96F9eC9AE76cc6A68f6cF9`, which has no code here (nonce 0). |
| **ExternalCallExecutor** | `0x05bD82Dbb7c5C2Cf571112bD1ad4e7c02E10eBEA` | 6,394 bytes, not a proxy. `0xAE0361b1C3454b297129e01046057F1D294c7974` has no code here. |
| ProxyAdmin of DlnSource | `0x1d0e490aff2d6ab6495298385cc618e4b4e43475` | Owner EOA `0xbda458dfc28021debd72060671fc350fa5cb39e5` (nonce 60). |
| ProxyAdmin of DlnDestination | `0x4308753b09005224188c3b2d20bdad3d2d6f6e28` | Owner EOA `0xbda458dfc28021debd72060671fc350fa5cb39e5`. |
| ProxyAdmin of DeBridgeRouter | `0x27014043522edcf5227b54e64be668af75169b3e` | Owner EOA `0xfd830dd9b446c9b880b32a03fb9a750aae4a68aa` (nonce 19). |
| ProxyAdmin of the adapter | `0x0e42d9f52ef8feedf8f6792d9fb9766e0caf0b26` | Owner EOA `0xbda458dfc28021debd72060671fc350fa5cb39e5`. |

The same `0xE93356b0b87c71A7F4957DCEBEd05BefA8cB624a` / `0x05bD82Dbb7c5C2Cf571112bD1ad4e7c02E10eBEA` pair is listed for Arc, Story, Cronos, HyperEVM, Injective, Monad and MegaETH (outside the eight targets).

---

## 6. Cross-chain summary

| Chain | ID | DlnSource | DlnDestination | DeBridgeRouter | DlnExternalCallAdapter | ExternalCallExecutor | Proxy flavor / upgrade owner |
|-------|----|-----------|----------------|----------------|------------------------|----------------------|------------------------------|
| Ethereum | 1 | ✓ §3 literal | ✓ §3 literal | ✓ §3 literal | ✓ `0x61eF2e01E603aEB5Cd96F9eC9AE76cc6A68f6cF9` | ✓ `0xAE0361b1C3454b297129e01046057F1D294c7974` | OZ v4 / Safe, 5 signatures |
| Base | 8453 | ✓ | ✓ | ✓ | ✓ same | ✓ same | OZ v4 / Safe, 5 signatures |
| Arbitrum One | 42161 | ✓ | ✓ | ✓ | ✓ same | ✓ same | OZ v4 / Safe, 5 signatures |
| Optimism | 10 | ✓ | ✓ | ✓ | ✓ same | ✓ same | OZ v4 / Safe, 5 signatures |
| Polygon PoS | 137 | ✓ | ✓ | ✓ | ✓ same | ✓ same | OZ v4 / Safe, 5 signatures |
| BNB Smart Chain | 56 | ✓ | ✓ | ✓ | ✓ same | ✓ same | OZ v4 / Safe, 5 signatures |
| Avalanche C-Chain | 43114 | ✓ | ✓ | ✓ | ✓ same | ✓ same | OZ v4 / Safe, 5 signatures |
| **Robinhood Chain** | 4663 | ✓ | ✓ | ✓ | ✓ **`0xE93356b0b87c71A7F4957DCEBEd05BefA8cB624a`** | ✓ **`0x05bD82Dbb7c5C2Cf571112bD1ad4e7c02E10eBEA`** | **OZ v5 / EOA owners** |

§3 literals: `DlnSource` `0xeF4fB24aD0916217251F553c0596F8Edc630EB66`, `DlnDestination` `0xE7351Fd770A37282b91D153Ee690B63579D6dd7f`, `DeBridgeRouter` `0x663DC15D3C1aC63ff12E45Ab68FeA3F0a883C251`. DLN is present on all eight target chains. Counterparty chains outside the eight: Solana (deBridge id 7565164), TRON, Linea, Arc, Story, Cronos, HyperEVM, Injective, Monad and MegaETH (see [README.md](README.md)).

---

## 7. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| DlnSource, DlnDestination, DlnExternalCallAdapter (7 chains) | EIP-1967 transparent (OpenZeppelin v4, 2,112-byte proxy) | Implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` populated; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` = ProxyAdmin `0xa7b88a746fa457578d5abd6234471f07d895f46b` | ProxyAdmin owner: a 5-threshold Safe per chain (§3–§4) |
| DeBridgeRouter (7 chains) | EIP-1967 transparent (2,141-byte proxy; 2,733 bytes on Base and Optimism) | Admin slot = `0xc86ab72dc6da7ef91a96650f3bc23125cd997130` | Same Safe per chain |
| All four DLN proxies on Robinhood Chain | EIP-1967 transparent (OpenZeppelin v5, 1,159 bytes; one ProxyAdmin per proxy) | Admin slot = the per-proxy ProxyAdmin of §5 | **EOA owners** (§5) |
| ExternalCallExecutor | Not a proxy | Implementation slot empty; 6,213 bytes (6,394 on Robinhood Chain) | none |

Watch `Upgraded(address)` on the four proxies and `AdminChanged(address,address)` on each chain. The implementations in §3–§5 are point-in-time values: read the slot live.

---

## 8. Detection invariants & gotchas

1. **Link key = `orderId` (bytes32), in the data of every DLN event.** `CreatedOrder` (data word 1, after the offset of the order tuple), `FulfilledOrder` (data word 1), `SentOrderUnlock` (word 0), `ClaimedUnlock` (word 0), `SentOrderCancel` (word 1), `ClaimedOrderCancel` (word 0). It is on chain on both sides. Worked example: order `0x400643333a540ebce4b6915960dff3ea25198a21b198d78ce89e740ee5aedd69` was created on Ethereum at block 26,072,229, filled on Base at block 51,882,185, unlocked on Base at block 51,882,189, and paid out to the solver on Ethereum at block 26,072,236 (0.434826 ETH), all in the pinned window.
2. **The second link key is the Gate `submissionId`.** `SentOrderUnlock.submissionId` and `SentOrderCancel.submissionId` equal the `Sent.submissionId` of the Gate in the same transaction, and the Gate `Claimed.submissionId` on the source chain (see [dmp.md](dmp.md)). One unlock message can carry many orders (`sendBatchEvmUnlock`, `sendBatchSolanaUnlock`): 7 `SentOrderUnlock` logs shared one `submissionId` in the sampled Ethereum batch.
3. **Source-leg value.** An ERC-20 order moves `giveAmount + percentFee + affiliate amount` from the maker (or from `DeBridgeRouter`) to `DlnSource`; `order.giveAmount` in the event is net of the fees. A native order sends `msg.value` = input + flat fee; there is no ERC-20 row. Sample: `msg.value` 0.436 ETH = `giveAmount` 0.434826 + `percentFee` 0.000174 (4 bps) + `nativeFixFee` 0.001.
4. **Destination-leg value comes from the solver, not from `DlnDestination`.** `fulfillOrder` transfers the take token from `msg.sender` straight to `receiverDst`. When a solver routes through `DeBridgeRouter.strictlySwapAndCallDln`, the transfer's `from` is the router. A native payout is an internal call with no log. Join `FulfilledOrder` to the take-token transfer to `receiverDst` in the same transaction, from any sender.
5. **Hooks change the recipient.** For an order with `externalCall`, the take tokens go to `DlnExternalCallAdapter`, then to `ExternalCallExecutor`, then to the hook target (sample: Avalanche, one `ExternalCallExecuted` in the window). `receiverDst` then gets nothing directly; the fallback address gets the tokens when the hook fails.
6. **The escrow payout is `ClaimedUnlock`, not `FulfilledOrder`.** `ClaimedUnlock.beneficiary` is the solver. It arrives through the Gate `claim`, executed by a keeper EOA, via CallProxy `0x8a0C79F5532f3b2a16AD1E4282A5DAF81928a824` (see [dmp.md](dmp.md)).
7. **Cancel is the only refund.** Orders have no deadline. The delegated cancel role works only on orders that name `allowedCancelBeneficiarySrc`, so the refund goes to that preset address. `ClaimedOrderCancel.paidAmount` = give amount + percent fee + affiliate amount, and the flat fee returns as a separate native transfer. On Ethereum the delegated cancel role belongs to `0x0746E7E4D15f30885616b4ac3D274393354e80C0` (an EOA with an EIP-7702 delegation; 23 bytes of code), which sent the sampled `SentOrderCancel`.
8. **`CriticalMismatchChainId` is a security signal.** It fires when an unlock message claims to come from a chain that is not the order's take chain. `UnexpectedOrderStatusForClaim` and `UnexpectedOrderStatusForCancel` mean a duplicate or late message; no value moves.
9. **Use both schemas for history.** `CreatedOrder` without `metadata` (legacy topic) before Ethereum block 18,092,917; `FulfilledOrder` without `actualFulfillAmount` (legacy topic) before Ethereum block 24,447,763. The upgrade blocks on the other chains were not measured; watch both topics when back-filling there.
10. **`DeBridgeRouter` is mostly same-chain swaps.** In the window, Base had 7,905 `SameChainSwapExecuted` logs against 95 `FulfilledOrder` logs. Do not count router swaps as bridge transfers. Router `Refund` is surplus return; it is not a DLN refund.
11. **Two different `AffiliateFeePaid` events.** `DlnSource` (`bytes32,address,uint256,address`) and `DeBridgeRouter` (`address,uint256,address,uint32`) have different topic0 values; key on the emitter.
12. **Robinhood Chain diverges.** Hooks use `0xE93356b0b87c71A7F4957DCEBEd05BefA8cB624a` and `0x05bD82Dbb7c5C2Cf571112bD1ad4e7c02E10eBEA`; the proxies are OpenZeppelin v5 with EOA-owned ProxyAdmins. A monitor on upgrades there should watch `Upgraded` and `OwnershipTransferred` at the five ProxyAdmins.
13. **Shared literal, other role.** `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` is the Gate on Base but a DeBridgeToken implementation on the other chains; `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` is the Gate on seven chains but a ProxyAdmin on Base (see [dmp.md](dmp.md)). Key every address on `(chain, address)`.
14. **Monitor triggers.** Large transfers: `CreatedOrder.order.giveAmount` and `FulfilledOrder.actualFulfillAmount` priced per token. Drains: `ClaimedUnlock` or `ClaimedOrderCancel` without a matching order, and `CriticalMismatchChainId`. Admin: `Upgraded`, `AdminChanged`, `RoleGranted` / `RoleRevoked`, `Paused` / `Unpaused`, `SetDlnDestinationAddress`, `SetDlnSourceAddress`, `ExternalCallAdapterUpdated`, `ExecutorUpdated`, router `rescueFunds` calls.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== DlnSource topics =====
TOPIC_DLN_CREATED_ORDER            = '\xfc8703fd57380f9dd234a89dce51333782d49c5902f307b02f03e014d18fe471'
TOPIC_DLN_CREATED_ORDER_LEGACY     = '\x47ef43a379911343a1cc752617be7096d678feac64600f0f94e63062722735af'
TOPIC_DLN_CLAIMED_UNLOCK           = '\x33fff3d864e92b6e1ef9e830196fc019c946104ea621b833aaebd3c3e84b2f6f'
TOPIC_DLN_CLAIMED_ORDER_CANCEL     = '\x7d7d1c5b3eadbe275ceb358e65cd57410b35997187258dbaaae42ab6e1405fd8'
TOPIC_DLN_AFFILIATE_FEE_PAID       = '\x9077c15d8bcf2d51f89ed4806cf2fd3d09000b446acd62c04653da6684ee16f0'
TOPIC_DLN_UNEXPECTED_STATUS_CLAIM  = '\xc65cdb43047b7466a1705cf4c7e88b0c66614ed6da1c1aa7f44026cee8e67626'
TOPIC_DLN_UNEXPECTED_STATUS_CANCEL = '\x9302619b5552484dceb0055d13a6b83805ce74ad349b433cf78be991ef30703e'
TOPIC_DLN_CRITICAL_MISMATCH_CHAIN  = '\x29af03f84291900300e96b03eed8a02c0db5cdc94a3b15a880a93bfce8c125a2'
TOPIC_DLN_INCREASED_GIVE_AMOUNT    = '\x4f3bc5fae93ae03632b30b624fb1dbfa21466a29216f314d0cfcb269d7c918ff'
TOPIC_DLN_SET_DESTINATION_ADDRESS  = '\x82568678a169f202360005e72d5ab10d95c3c369ddd502057dacb85e9c700759'
-- ===== DlnDestination topics =====
TOPIC_DLN_FULFILLED_ORDER          = '\xc164aca37b9805a1c9027b6f32260a069723a82926f6e9ece4926e4dd3ea8ecf'
TOPIC_DLN_FULFILLED_ORDER_LEGACY   = '\xd281ee92bab1446041582480d2c0a9dc91f855386bb27ea295faac1e992f7fe4'
TOPIC_DLN_SENT_ORDER_UNLOCK        = '\x37a01d7dc38e924008cf4f2fa3d2ec1f45e7ae3c8292eb3e7d9314b7ad10e2fc'
TOPIC_DLN_SENT_ORDER_CANCEL        = '\xc756fd0227d1d70cec0ead41b16a90a1cac618da1d612cb5d0b72d93301369de'
TOPIC_DLN_DECREASED_TAKE_AMOUNT    = '\x08c645e3c369cf85ec8e864f27821c61ceba80fa78f2f66fb0d042a4b29e794b'
TOPIC_DLN_SET_SOURCE_ADDRESS       = '\x1a6f092b051adc658eb15cab830c00ed3eff5b9683f8bf9cf94ada7f53ab20e0'
TOPIC_DLN_ADAPTER_UPDATED          = '\x3a2e8bb48b6b66181a226c06b9c44dd5c701a925c5b3274df2fc67ec2a097f47'
-- ===== DeBridgeRouter topics =====
TOPIC_DBR_ROUTER_REFUND            = '\x149635d19f798f6b7c74c74a500d362c89316a0ab808abe5e0c0de45da9b1d2c'
TOPIC_DBR_ROUTER_SWAP_EXECUTED     = '\xdde2f3711ab09cdddcfee16ca03e54d21fb8cf3fa647b9797913c950d38ad693'
TOPIC_DBR_ROUTER_SAME_CHAIN_SWAP   = '\xecfedc7a2bb58de8119427cef1d856aa76747d4a6e13307a7ca485bf8df20904'
TOPIC_DBR_ROUTER_AFFILIATE_FEE     = '\x6a0f4594999005114d250d0dce53dea802de70666f009552d1aa0b39e5846361'
-- ===== DlnExternalCallAdapter topics =====
TOPIC_DLN_EXT_CALL_EXECUTED        = '\xe0320f35b1ebe381c5ff7355f4c6ed81fe49413c4becf1e730b666d199908b69'
TOPIC_DLN_EXT_CALL_FAILED          = '\xfaebec5591353214b140dec3700150f47d7b1296e981c3498df1b37a6b953c23'
TOPIC_DLN_EXT_CALL_REGISTERED      = '\xcb08fcc129e6e8f0ddd452cbd1380b0451cd7fe881d34a9c9618e66dde77ebb8'
TOPIC_DLN_EXT_CALL_REGISTERED_OLD  = '\x302c1fa26313337086ce999d06b9e355079ef09ed4c18919b069147273033353'
TOPIC_DLN_EXT_CALL_CANCELLED       = '\x00dcd3c81b3e3b2f9c553348615a4f541f4d464c7f57a6fa096a27f4b1310ab2'
TOPIC_DLN_EXECUTOR_UPDATED         = '\x0ef3c7eb9dbcf33ddf032f4cce366a07eda85eed03e3172e4a90c4cc16d57886'
-- ===== Admin / proxy topics =====
TOPIC_PAUSED_ADDRESS               = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED_ADDRESS             = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_ROLE_GRANTED                 = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED                 = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
TOPIC_UPGRADED                     = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED                = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'

-- ===== Selectors =====
SEL_DLN_CREATE_ORDER               = '\xfbe16ca7'
SEL_DLN_CREATE_SALTED_ORDER        = '\xb9303701'
SEL_DLN_CREATE_FOR_INTENT          = '\xafbfe366'
SEL_DLN_CREATE_FOR_INTENT_MAKER    = '\xbaa0d37f'
SEL_DLN_CLAIM_UNLOCK               = '\x5886d8d2'
SEL_DLN_CLAIM_BATCH_UNLOCK         = '\x6abd4ea7'
SEL_DLN_CLAIM_CANCEL               = '\xd48b0146'
SEL_DLN_CLAIM_BATCH_CANCEL         = '\x924a062c'
SEL_DLN_FULFILL_ORDER              = '\xc358547e'
SEL_DLN_FULFILL_ORDER_HOOK         = '\x0ebcd2f6'
SEL_DLN_SEND_EVM_UNLOCK            = '\xb41100b3'
SEL_DLN_SEND_BATCH_EVM_UNLOCK      = '\x5b5a646e'
SEL_DLN_SEND_SOLANA_UNLOCK         = '\xa6a5ae52'
SEL_DLN_SEND_BATCH_SOLANA_UNLOCK   = '\x40968794'
SEL_DLN_SEND_EVM_ORDER_CANCEL      = '\xd38d9626'
SEL_DLN_SEND_SOLANA_ORDER_CANCEL   = '\x9327145d'
SEL_DLN_PAUSE                      = '\x8456cb59'
SEL_DLN_UNPAUSE                    = '\x3f4ba83a'
SEL_DBR_STRICTLY_SWAP_AND_CALL     = '\x4d8160ba'
SEL_DBR_STRICTLY_SWAP_AND_CALL_DLN = '\xc7a76969'
SEL_DBR_FILL_CROSS_CHAIN           = '\x6391c75b'
SEL_DBR_SWAP                       = '\x258c16ee'
SEL_DBR_RESCUE_FUNDS               = '\x6ccae054'
SEL_DLN_ADAPTER_RECEIVE_CALL       = '\xef35accb'
SEL_DLN_ADAPTER_EXECUTE_CALL       = '\x529c02d5'
SEL_DLN_ADAPTER_CANCEL_CALL        = '\x78de8697'
SEL_PROXYADMIN_UPGRADE_AND_CALL    = '\x9623609d'
SEL_PROXYADMIN_UPGRADE             = '\x99a88ec4'

-- ===== Role ids (bytes32) =====
ROLE_GOVMONITORING                 = '\x2b36fa99e118fa8485d488becf749a974743fbeb6a7aa57e663893bf5d69a3c1'
ROLE_DELEGATED_ORDER_CANCEL        = '\x01bd451848033b83db2d5c21b44e19dc2cf0e3067ae17fafefe1ac665572eeb3'

-- ===== Addresses: the same literal on the chains listed =====
ETH_DLN_SOURCE                     = '\xef4fb24ad0916217251f553c0596f8edc630eb66'
BASE_DLN_SOURCE                    = '\xef4fb24ad0916217251f553c0596f8edc630eb66'
ARB_DLN_SOURCE                     = '\xef4fb24ad0916217251f553c0596f8edc630eb66'
OP_DLN_SOURCE                      = '\xef4fb24ad0916217251f553c0596f8edc630eb66'
POLY_DLN_SOURCE                    = '\xef4fb24ad0916217251f553c0596f8edc630eb66'
BNB_DLN_SOURCE                     = '\xef4fb24ad0916217251f553c0596f8edc630eb66'
AVAX_DLN_SOURCE                    = '\xef4fb24ad0916217251f553c0596f8edc630eb66'
RH_DLN_SOURCE                      = '\xef4fb24ad0916217251f553c0596f8edc630eb66'
ETH_DLN_DESTINATION                = '\xe7351fd770a37282b91d153ee690b63579d6dd7f'
BASE_DLN_DESTINATION               = '\xe7351fd770a37282b91d153ee690b63579d6dd7f'
ARB_DLN_DESTINATION                = '\xe7351fd770a37282b91d153ee690b63579d6dd7f'
OP_DLN_DESTINATION                 = '\xe7351fd770a37282b91d153ee690b63579d6dd7f'
POLY_DLN_DESTINATION               = '\xe7351fd770a37282b91d153ee690b63579d6dd7f'
BNB_DLN_DESTINATION                = '\xe7351fd770a37282b91d153ee690b63579d6dd7f'
AVAX_DLN_DESTINATION               = '\xe7351fd770a37282b91d153ee690b63579d6dd7f'
RH_DLN_DESTINATION                 = '\xe7351fd770a37282b91d153ee690b63579d6dd7f'
ETH_DBR_ROUTER                     = '\x663dc15d3c1ac63ff12e45ab68fea3f0a883c251'
BASE_DBR_ROUTER                    = '\x663dc15d3c1ac63ff12e45ab68fea3f0a883c251'
ARB_DBR_ROUTER                     = '\x663dc15d3c1ac63ff12e45ab68fea3f0a883c251'
OP_DBR_ROUTER                      = '\x663dc15d3c1ac63ff12e45ab68fea3f0a883c251'
POLY_DBR_ROUTER                    = '\x663dc15d3c1ac63ff12e45ab68fea3f0a883c251'
BNB_DBR_ROUTER                     = '\x663dc15d3c1ac63ff12e45ab68fea3f0a883c251'
AVAX_DBR_ROUTER                    = '\x663dc15d3c1ac63ff12e45ab68fea3f0a883c251'
RH_DBR_ROUTER                      = '\x663dc15d3c1ac63ff12e45ab68fea3f0a883c251'
ETH_DLN_EXT_CALL_ADAPTER           = '\x61ef2e01e603aeb5cd96f9ec9ae76cc6a68f6cf9'
BASE_DLN_EXT_CALL_ADAPTER          = '\x61ef2e01e603aeb5cd96f9ec9ae76cc6a68f6cf9'
ARB_DLN_EXT_CALL_ADAPTER           = '\x61ef2e01e603aeb5cd96f9ec9ae76cc6a68f6cf9'
OP_DLN_EXT_CALL_ADAPTER            = '\x61ef2e01e603aeb5cd96f9ec9ae76cc6a68f6cf9'
POLY_DLN_EXT_CALL_ADAPTER          = '\x61ef2e01e603aeb5cd96f9ec9ae76cc6a68f6cf9'
BNB_DLN_EXT_CALL_ADAPTER           = '\x61ef2e01e603aeb5cd96f9ec9ae76cc6a68f6cf9'
AVAX_DLN_EXT_CALL_ADAPTER          = '\x61ef2e01e603aeb5cd96f9ec9ae76cc6a68f6cf9'
RH_DLN_EXT_CALL_ADAPTER            = '\xe93356b0b87c71a7f4957dcebed05befa8cb624a'
ETH_DLN_EXT_CALL_EXECUTOR          = '\xae0361b1c3454b297129e01046057f1d294c7974'
BASE_DLN_EXT_CALL_EXECUTOR         = '\xae0361b1c3454b297129e01046057f1d294c7974'
ARB_DLN_EXT_CALL_EXECUTOR          = '\xae0361b1c3454b297129e01046057f1d294c7974'
OP_DLN_EXT_CALL_EXECUTOR           = '\xae0361b1c3454b297129e01046057f1d294c7974'
POLY_DLN_EXT_CALL_EXECUTOR         = '\xae0361b1c3454b297129e01046057f1d294c7974'
BNB_DLN_EXT_CALL_EXECUTOR          = '\xae0361b1c3454b297129e01046057f1d294c7974'
AVAX_DLN_EXT_CALL_EXECUTOR         = '\xae0361b1c3454b297129e01046057f1d294c7974'
RH_DLN_EXT_CALL_EXECUTOR           = '\x05bd82dbb7c5c2cf571112bd1ad4e7c02e10ebea'
-- ProxyAdmins and upgrade owners
ETH_DLN_PROXY_ADMIN                = '\xa7b88a746fa457578d5abd6234471f07d895f46b'
ETH_DBR_ROUTER_PROXY_ADMIN         = '\xc86ab72dc6da7ef91a96650f3bc23125cd997130'
ETH_DEBRIDGE_SAFE                  = '\x6bec1faf33183e1bc316984202ecc09d46ac92d5'
BASE_DEBRIDGE_SAFE                 = '\xf0a9d50f912d64d1105b276526e21881bf48a29e'
ARB_DEBRIDGE_SAFE                  = '\xa52842cd43fa8c4b6660e443194769531d45b265'
AVAX_DEBRIDGE_SAFE                 = '\x8ac842e8f3be6bf67ccfdc87ce3f98d635008ef0'
RH_DLN_SOURCE_PROXY_ADMIN          = '\x1d0e490aff2d6ab6495298385cc618e4b4e43475'
RH_DLN_DESTINATION_PROXY_ADMIN     = '\x4308753b09005224188c3b2d20bdad3d2d6f6e28'
RH_DBR_ROUTER_PROXY_ADMIN          = '\x27014043522edcf5227b54e64be668af75169b3e'
RH_DLN_ADAPTER_PROXY_ADMIN         = '\x0e42d9f52ef8feedf8f6792d9fb9766e0caf0b26'
RH_DLN_UPGRADE_OWNER_EOA           = '\xbda458dfc28021debd72060671fc350fa5cb39e5'
RH_DBR_ROUTER_UPGRADE_OWNER_EOA    = '\xfd830dd9b446c9b880b32a03fb9a750aae4a68aa'
ETH_DLN_DELEGATED_CANCEL_EOA       = '\x0746e7e4d15f30885616b4ac3d274393354e80c0'
```

---

## 10. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 and selectors:** recomputed as `keccak256` of the canonical signature, from the verified implementation ABIs on Blockscout (`DlnSource` `0x2b426a0ac391490e88d15b304436e7a84df78611`, `DlnDestination` `0xd9b4f9cacffb59f2b982ad3c45096e3aa4b4020e`, `DeBridgeRouter` `0xce56012e880851baa234cd092af516a0fca9cfe3`, `DlnExternalCallAdapter` `0xe143dbaec892cef2af836db49870a0bcf9d5e6a1`, `ExternalCallExecutor` `0xAE0361b1C3454b297129e01046057F1D294c7974`; compiler 0.8.28 and 0.8.17) and from the older ABIs of `debridge-finance/abis-and-idls` for the legacy rows. Each current selector was found as a `PUSH4` in the Ethereum implementation bytecode; the legacy selectors were not. The main topic0 values were found in the implementation bytecode on Ethereum, Base, Optimism and Robinhood Chain, and in live logs.
- **Schema switch blocks:** logs of both `CreatedOrder` topics around Ethereum block 18,092,917 and both `FulfilledOrder` topics around block 24,447,763 (the `Upgraded` transactions of the Ethereum Safe); first legacy logs from the Blockscout log index.
- **Addresses:** the deBridge "Deployed Contracts" page (DLN table, including the Robinhood row), then `eth_getCode` on each of the eight chains for every address; EIP-1967 implementation and admin slots read live; ProxyAdmin `owner()` and Safe `getThreshold()` read live. The Robinhood ProxyAdmin owners have no code (EOAs, nonces 60 and 19).
- **Value movement:** receipts read for `CreatedOrder` (Ethereum `0x5a40e704b943c069d56891003133566d3084dddf4fd2e65b70a73c6d4fcd2d6f`; Robinhood `0xe1d5879a2c64e412ab97862c78e9fbb22c4d90e426c2425b49190c09c98d2e9b`), `FulfilledOrder` (Ethereum `0xd481d0ed384b53a1cb7c53c4c1da7ccfc430f591edb49bd3685c9a0590cf2c71`; Base `0x35ed8f0ffd5291751e6b188f9461f2fa303f7375c3a7b77da2995a58c7c79ae2`), `SentOrderUnlock` (Ethereum `0xe017722ca5480bac09e269802a4a0fbb3cd9e752264ca5355c33dae326ce57d1`), `ClaimedUnlock` (Ethereum `0xe086fae384441c8fbf67f06cd568320833b3a2bbf81118f5027ea6543a4231ff`), `SentOrderCancel` (Ethereum `0x166f7e84959764a00b82838f2d8f2574f854dcfb16bb8410db7999252c0572eb`), `ClaimedOrderCancel` (Ethereum `0x3d2d5dd78d15ad8049f47a513e8da551e3f8c99f00b3ba107cc5a4e05b2703df`) and `ExternalCallExecuted` (Avalanche `0x60bb78509653a6f3380d0fd576e9cfad7e308a631332d25f572299a61420aed7`).
- **Activity**, pinned 12-hour window 2026-09-28 00:00–12:00 UTC, all logs of the DLN addresses per chain:

| Event (emitter) | Ethereum | Base | Arbitrum | Optimism | Polygon | BNB | Avalanche | Robinhood |
|-----------------|---------:|-----:|---------:|---------:|--------:|----:|----------:|----------:|
| `CreatedOrder` (DlnSource) | 242 | 104 | 100 | 14 | 40 | 194 | 6 | 207 |
| `FulfilledOrder` (DlnDestination, current) | 433 | 95 | 102 | 7 | 22 | 185 | 7 | 309 |
| `SentOrderUnlock` (DlnDestination) | 447 | 98 | 139 | 0 | 17 | 194 | 10 | 315 |
| `ClaimedUnlock` (DlnSource) | 273 | 102 | 83 | 20 | 40 | 193 | 11 | 215 |
| `SentOrderCancel` (DlnDestination) | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| `ClaimedOrderCancel` (DlnSource) | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| `ExternalCallExecuted` (adapter) | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |
| `Refund` (DeBridgeRouter) | 467 | 72 | 25 | 4 | 37 | 338 | 7 | 440 |
| `SameChainSwapExecuted` (DeBridgeRouter) | 114 | 7,905 | 72 | 26 | 11 | 95 | 4 | 568 |

Block ranges of the window: Ethereum 26,072,222–26,075,812; Base 51,882,127–51,903,726; Arbitrum 509,539,969–509,698,804; Optimism 157,477,412–157,499,011; Polygon 94,565,640–94,594,439; BNB 124,425,013–124,520,982; Avalanche 96,289,260–96,322,019; Robinhood 74,350,994–74,780,331. The legacy topics, `IncreasedGiveAmount`, `DecreasedTakeAmount` and the adapter registration events had 0 logs in the window. A zero says what the window held, not that a contract is dead.

Sources:
- deBridge docs — [DLN deployed contracts](https://docs.debridge.com/dln-details/overview/deployed-contracts) · [DLN fees and supported chains](https://docs.debridge.com/dln-details/overview/fees-supported-chains) · [Supported chains](https://docs.debridge.com/home/architecture/supported-chains)
- [debridge-finance/dln-contracts](https://github.com/debridge-finance/dln-contracts) (`contracts/DLN/DlnSource.sol`, `DlnDestination.sol`, `contracts/libraries/DlnOrderLib.sol`, `contracts/adapters/`) · [debridge-finance/abis-and-idls](https://github.com/debridge-finance/abis-and-idls) (`abis/`)
- Explorers — [Etherscan DlnSource](https://etherscan.io/address/0xef4fb24ad0916217251f553c0596f8edc630eb66) · [Etherscan DlnDestination](https://etherscan.io/address/0xe7351fd770a37282b91d153ee690b63579d6dd7f) · [Blockscout verified DlnDestination implementation](https://eth.blockscout.com/address/0xd9b4f9cacffb59f2b982ad3c45096e3aa4b4020e) · [Robinhood Chain Blockscout](https://robinhoodchain.blockscout.com/address/0xeF4fB24aD0916217251F553c0596F8Edc630EB66)
