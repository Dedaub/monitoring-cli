# LI.FI Periphery — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, `lifinance/contracts` (`src/Periphery/`, `src/Security/`, `deployments/<network>.json`, `deployments/<network>.diamond.json` → `Periphery`) and the explorer-verified sources of the deployed contracts. Every topic0 and selector was recomputed as `keccak256(signature)`. Every address was existence-checked with `eth_getCode`.
**Scope:** the contracts around the LiFiDiamond: the **destination side** (Executor and the bridge receivers: ReceiverAcrossV3, ReceiverAcrossV4, ReceiverStargateV2, ReceiverChainflip, ReceiverOIF and the legacy Receiver), the **entry helpers** (Permit2Proxy, ERC20Proxy), the **fee contracts** (FeeCollector, FeeForwarder, LiFuelFeeCollector), and the **utilities** (TokenWrapper, GasZipPeriphery, LiFiDEXAggregator, Patcher, OutputValidator, LidoWrapper), plus the **LiFiTimelockController** that owns the diamond. The diamond itself is in [diamond.md](diamond.md). Topics and selectors are chain-agnostic; addresses are network-specific.

The periphery contracts are plain, immutable contracts. Most of them have a different address on each chain, because LI.FI redeploys them with chain-specific constructor arguments (the Executor, the Across spoke pool, the LayerZero endpoint). Always key them on `(chain, address)`.

Three facts to know before indexing:

1. **The destination payout of a plain bridge route is not a LI.FI event.** The underlying bridge pays the receiver directly. LI.FI contracts act on the destination chain only when the route has a destination call (`hasDestinationCall` = true): the bridge delivers to a LI.FI receiver, the receiver hands the tokens to the Executor, and the Executor swaps and pays the receiver.
2. **`LiFiTransferCompleted` (Executor) and `LiFiTransferRecovered` (receivers) carry the source `transactionId` as topic1.** They are the only on-chain destination records that link to the source `LiFiTransferStarted`.
3. **`LiFiTransferRecovered` is a payout, not a refund.** The destination swap failed, so the receiver sent the bridged token itself to the final receiver. No funds return to the source chain.

---

## 0. Contract families & versions

| Contract | Role | Emits | Chains |
|----------|------|-------|--------|
| **Executor** | Destination swaps and calls. `swapAndCompleteBridgeTokens` pulls the bridged token from the calling receiver, runs the swaps and pays the receiver. | `LiFiTransferCompleted`, `AssetSwapped` | all 8 |
| **ReceiverAcrossV4** | Across message handler (`handleV3AcrossMessage`, called only by the Across spoke pool). | `LiFiTransferRecovered` | 7 (not Avalanche) |
| ReceiverAcrossV3 | Older Across message handler, still deployed. | `LiFiTransferRecovered` | ETH·Base·Arb·OP·Poly·BNB |
| **ReceiverStargateV2** | Stargate V2 / LayerZero `lzCompose` handler (called only by the LayerZero endpoint, for a Stargate pool). | `LiFiTransferRecovered` | 7 (not Robinhood Chain) |
| ReceiverChainflip | Chainflip `cfReceive` handler (called only by the Chainflip vault). | `LiFiTransferRecovered` | ETH·Arb |
| ReceiverOIF | Open Intents Framework output settler callback (`outputFilled`). No own event; the Executor emits. | — | all 8 |
| Receiver (legacy) | Stargate V1 `sgReceive` and Connext Amarok `xReceive` handler. Not in the current periphery registry. | `LiFiTransferRecovered` | 7 (not Robinhood Chain) |
| **Permit2Proxy** | Gasless entry: pulls the user's tokens with an EIP-2612 permit or a Permit2 signature, then calls the diamond. | — | all 8 |
| ERC20Proxy | Lets the Executor pull tokens (`transferFrom`) for authorized callers. | `AuthorizationChanged` | all 8 |
| **FeeCollector** | Integrator and LI.FI fee escrow. | `FeesCollected`, `FeesWithdrawn`, `LiFiFeesWithdrawn` | all 8 |
| **FeeForwarder** | Newer fee path: forwards fees straight to the recipients in the same transaction. | `FeesForwarded` | all 8 |
| LiFuelFeeCollector | Legacy destination-gas (LI.FI Fuel) fee collector. | `GasFeesCollected`, `FeesWithdrawn` | 7 (not Robinhood Chain) |
| TokenWrapper | Wraps and unwraps the native token for swap steps. | — | all 8 |
| GasZipPeriphery | Deposits to the Gas.zip router from a swap step. | — | all 8 |
| LiFiDEXAggregator | LI.FI's own swap router (`processRoute`). | `Route` | all 8 |
| Patcher | Patches amounts into calldata at run time for multi-step routes. | `PatchExecuted`, `TokensDeposited` | ETH·Base·Poly·Avax |
| OutputValidator | Checks the output amount of a swap and sends the excess to a wallet. | `OutputValidated` | all 8 |
| LidoWrapper | stETH ↔ wstETH helper. | — | OP only |
| **LiFiTimelockController** | Owner of the diamond (OpenZeppelin TimelockController, 10,800 s minimum delay). | `CallScheduled`, `CallExecuted`, `Cancelled`, `MinDelayChange`, role events | all 8 |

All periphery contracts that inherit `WithdrawablePeriphery` or `TransferrableOwnership` also emit `TokensWithdrawn` and the ownership events (§1.2).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Destination events

| topic0 | Event |
|--------|-------|
| `0xb8c86983f929c6b770461983d1bbde1870408120f07123e9c12d49f35a0b4c4b` | `LiFiTransferCompleted(bytes32 indexed transactionId, address receivingAssetId, address receiver, uint256 amount, uint256 timestamp)` |
| `0x1fbfa988fd46deed0de12c94c7b5dcb537d51b804246d0083f245f7a8997d170` | `LiFiTransferRecovered(bytes32 indexed transactionId, address receivingAssetId, address receiver, uint256 amount, uint256 timestamp)` |
| `0x7bfdfdb5e3a3776976e53cb0607060f54c5312701c8cba1155cc4d5394440b38` | `AssetSwapped(bytes32 transactionId, address dex, address fromAssetId, address toAssetId, uint256 fromAmount, uint256 toAmount, uint256 timestamp)` |

- `LiFiTransferCompleted` (Executor): topic1 `transactionId`; data word 0 `receivingAssetId`, word 1 `receiver`, word 2 `amount`, word 3 `timestamp`. **`receivingAssetId` is the bridged token that entered the Executor, but `amount` is the Executor's balance of the final asset after the swaps.** When a destination swap runs, the two fields refer to different tokens (measured on Base below). Take the paid value from the ERC-20 `Transfer` from the Executor to `receiver` in the same transaction.
- `LiFiTransferRecovered` (receivers): same layout. Here `receivingAssetId` and `amount` are the bridged token and the amount that the receiver sent to `receiver`.
- `AssetSwapped` from the Executor records each destination swap step, with the same `transactionId` in data word 0.

### 1.2 Fee, utility and ownership events

| topic0 | Event |
|--------|-------|
| `0x2c835b8316da89c3b658f57c3b39e7b191fddc4b104beeda23042d5dadf455a9` | `ERC20ProxySet(address indexed proxy)` |
| `0x5fe3a0cb9aeae856eac34445ace9544f3e15c21fa6f9bffeca60d662a690ca1b` | `AuthorizationChanged(address indexed caller, bool authorized)` |
| `0x6337ed398c0e8467698c581374fdce4db14922df487b5a39483079f5f59b60a4` | `TokensWithdrawn(address assetId, address receiver, uint256 amount)` |
| `0x28a87b6059180e46de5fb9ab35eb043e8fe00ab45afcc7789e3934ecbbcde3ea` | `FeesCollected(address indexed _token, address indexed _integrator, uint256 _integratorFee, uint256 _lifiFee)` |
| `0x5e110f8bc8a20b65dcc87f224bdf1cc039346e267118bae2739847f07321ffa8` | `FeesWithdrawn(address indexed _token, address indexed _to, uint256 _amount)` |
| `0xe0ac2a6b74759312758ae3b784411c8e2f3b8bd81fecff40b906d69030af4bfc` | `LiFiFeesWithdrawn(address indexed _token, address indexed _to, uint256 _amount)` |
| `0x3a7029951ba36c1af37954df919ce2f9a95c3f5c2c2e872d5e7fd47c61a6df26` | `FeesForwarded(address indexed token, (address recipient, uint256 amount)[] distributions)` |
| `0x2db5ddd0b42bdbca0d69ea16f234a870a485854ae0d91f16643d6f317d8b8994` | `Route(address indexed from, address to, address indexed tokenIn, address indexed tokenOut, uint256 amountIn, uint256 amountOutMin, uint256 amountOut)` |
| `0x388c63fb82adbdf7c1046e997e85d8e71e98e878c43d0fb81b76254bee16b29a` | `PatchExecuted(address indexed caller, address indexed finalTarget, uint256 value, bool success, uint256 returnDataLength)` |
| `0x8a9c3a4c6eaabdd525bb66ee6069a4cd8dd410208adbb90faed9ecd887c0c4f0` | `TokensDeposited(address indexed caller, address indexed tokenAddress, uint256 amount, address indexed finalTarget)` |
| `0x29991351642fce7de30ac927d88ce3a9cfea9ec0b607b508e6d1060e19221b82` | `OutputValidated(address indexed token, address indexed validationWallet, uint256 excessAmount)` |
| `0x806d08432293677cc7e3e0f9443dcf0459f82567573d5094da6e9e6129dea4ab` | `StargateRouterSet(address indexed router)` |
| `0xcc6aaf791b8b7c6167981db821320441082903e27343e380dca76afd5807577d` | `AmarokRouterSet(address indexed router)` |
| `0x3e3c5e6d5b512eaa5d5a80669846cfbaf8bde70fc6f7a3be9828cffc9ba5f1db` | `ExecutorSet(address indexed executor)` |
| `0xfd178559652d65eca585044f34f8688859896a9bebaa7530dbe97c5c527320d5` | `RecoverGasSet(uint256 indexed recoverGas)` |
| `0x03e28afce33ddcc0ab4ff4b9050c6ff0c323292f46b577db77c1a7281320de56` | `GasFeesCollected(address indexed token, uint256 indexed chainId, address indexed receiver, uint256 feeAmount)` |
| `0xed8889f560326eb138920d842192f0eb3dd22b4f139c87a2c57538e05bae1278` | `OwnershipTransferRequested(address indexed _from, address indexed _to)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |

`StargateRouterSet`, `AmarokRouterSet`, `ExecutorSet` and `RecoverGasSet` belong to the legacy Receiver. `GasFeesCollected` belongs to the legacy LiFuelFeeCollector. `TokensWithdrawn` is the owner's rescue of stranded tokens from any `WithdrawablePeriphery` contract.

### 1.3 LiFiTimelockController (diamond owner)

| topic0 | Event |
|--------|-------|
| `0x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca` | `CallScheduled(bytes32 indexed id, uint256 indexed index, address target, uint256 value, bytes data, bytes32 predecessor, uint256 delay)` |
| `0xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58` | `CallExecuted(bytes32 indexed id, uint256 indexed index, address target, uint256 value, bytes data)` |
| `0x20fda5fd27a1ea7bf5b9567f143ac5470bb059374a27e8f67cb44f946f6d0387` | `CallSalt(bytes32 indexed id, bytes32 salt)` |
| `0xbaa1eb22f2a492ba1a5fea61b8df4d27c6c8b5f3971e63bb58fa14ff72eedb70` | `Cancelled(bytes32 indexed id)` |
| `0x11c24f4ead16507c69ac467fbd5e4eed5fb5c699626d2cc6d66421df253886d5` | `MinDelayChange(uint256 oldDuration, uint256 newDuration)` |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` |
| `0x13b615d4c78f2fc10f9ce5a15d0e540cefe4a3a3f963de10e452b07a2b7568d9` | `DiamondAddressUpdated(address indexed diamond)` |

`CallScheduled` opens the 3-hour window before an admin call on the diamond. Its `data` field is the calldata of that call: a `diamondCut` starts with `0x1f931c1c`, `transferOwnership` with `0xf2fde38b`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Executor

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4f91bc2b` | `swapAndCompleteBridgeTokens(bytes32 _transactionId, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData, address _transferredAssetId, address _receiver)` | Called by a receiver (or by the legacy Receiver). Pulls the bridged token, swaps, pays `_receiver`, emits `LiFiTransferCompleted`. The legacy Receiver has a function with the same selector. |
| `0xa83cbaa3` | `swapAndExecute(bytes32 _transactionId, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData, address _transferredAssetId, address _receiver, uint256 _amount)` | Pulls `_amount` through ERC20Proxy from the caller; same events. |
| `0x01e33667` | `withdrawToken(address assetId, address receiver, uint256 amount)` | Owner only. Emits `TokensWithdrawn`. |

### 2.2 Receivers (entry points called by the underlying bridge)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3a5be8cb` | `handleV3AcrossMessage(address tokenSent, uint256 amount, address, bytes message)` | ReceiverAcrossV3 / ReceiverAcrossV4. Only the Across spoke pool may call. |
| `0xd0a10260` | `lzCompose(address _from, bytes32, bytes _message, address, bytes)` | ReceiverStargateV2. Only the LayerZero endpoint may call; `_from` must be a Stargate pool. |
| `0x4904ac5f` | `cfReceive(uint32, bytes, bytes message, address token, uint256 amount)` | ReceiverChainflip. Only the Chainflip vault may call. |
| `0xc80b0e0f` | `outputFilled(bytes32 token, uint256 amount, bytes executionData)` | ReceiverOIF. Only the trusted output settler may call. |
| `0xab8236f3` | `sgReceive(uint16, bytes, uint256, address _token, uint256 _amountLD, bytes _payload)` | Legacy Receiver (Stargate V1). |
| `0xfd614f41` | `xReceive(bytes32 _transferId, uint256 _amount, address _asset, address, uint32, bytes _callData)` | Legacy Receiver (Connext Amarok). |
| `0x2e144579` | `pullToken(address assetId, address receiver, uint256 amount)` | Owner only on the legacy Receiver and the older receivers. |
| `0x4f91bc2b` | `swapAndCompleteBridgeTokens(bytes32 _transactionId, (address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit)[] _swapData, address assetId, address receiver)` | Legacy Receiver: the same selector as the Executor function of §2.1. Anyone may call it; it takes `msg.value` or the caller's full allowance of `assetId` and calls the Executor. A failed swap pays `receiver` the token itself and emits `LiFiTransferRecovered`. |

### 2.3 Permit2Proxy

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd7a08473` | `callDiamondWithEIP2612Signature(address tokenAddress, uint256 amount, uint256 deadline, uint8 v, bytes32 r, bytes32 s, bytes diamondCalldata)` | The permit signer must be `msg.sender`. |
| `0x0193b9fc` | `callDiamondWithPermit2(bytes _diamondCalldata, ((address token, uint256 amount) permitted, uint256 nonce, uint256 deadline) _permit, bytes _signature)` | Anyone may send it; the Permit2 signature authorizes the transfer. |
| `0x4561136e` | `callDiamondWithPermit2Witness(bytes _diamondCalldata, address _signer, ((address token, uint256 amount) permitted, uint256 nonce, uint256 deadline) _permit, bytes _signature)` | The witness binds the diamond address and the calldata hash. |

### 2.4 ERC20Proxy, fee contracts and utilities

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x15dacbea` | `transferFrom(address tokenAddress, address from, address to, uint256 amount)` | Authorized callers only (the Executor). |
| `0x454bbd29` | `setAuthorizedCaller(address caller, bool authorized)` | Owner only. Emits `AuthorizationChanged`. |
| `0xeedd56e1` | `collectTokenFees(address tokenAddress, uint256 integratorFee, uint256 lifiFee, address integratorAddress)` | Emits `FeesCollected`. |
| `0xe0cbc5f2` | `collectNativeFees(uint256 integratorFee, uint256 lifiFee, address integratorAddress)` | Payable. Emits `FeesCollected`. |
| `0xbd0b380b` | `withdrawIntegratorFees(address tokenAddress)` | Integrator withdraws its fees. Emits `FeesWithdrawn`. |
| `0xe5d64766` | `batchWithdrawIntegratorFees(address[] tokenAddresses)` | Emits `FeesWithdrawn` per token. |
| `0x461ad4f5` | `withdrawLifiFees(address tokenAddress)` | Owner only. Emits `LiFiFeesWithdrawn`. |
| `0x64bc5be1` | `batchWithdrawLifiFees(address[] tokenAddresses)` | Owner only. Emits `LiFiFeesWithdrawn` per token. |
| `0x332d746b` | `forwardERC20Fees(address _token, (address recipient, uint256 amount)[] _distributions)` | Emits `FeesForwarded`. |
| `0x0e8ae67f` | `forwardNativeFees((address recipient, uint256 amount)[] _distributions)` | Payable. Emits `FeesForwarded`. |
| `0xd0e30db0` | `deposit()` | TokenWrapper: native → wrapped. |
| `0x3ccfd60b` | `withdraw()` | TokenWrapper: wrapped → native. |
| `0x8b71ae6c` | `depositToGasZipERC20((address callTo, address approveTo, address sendingAssetId, address receivingAssetId, uint256 fromAmount, bytes callData, bool requiresDeposit) _swapData, (bytes32 receiverAddress, uint256 destinationChains) _gasZipData)` | GasZipPeriphery: swap an ERC-20 to native, then deposit to Gas.zip. |
| `0xc4af5a74` | `depositToGasZipNative((bytes32 receiverAddress, uint256 destinationChains) _gasZipData, uint256 _amount)` | GasZipPeriphery: native deposit to Gas.zip. |
| `0x2646478b` | `processRoute(address tokenIn, uint256 amountIn, address tokenOut, uint256 amountOutMin, address to, bytes route)` | LiFiDEXAggregator: emits `Route`. |
| `0x93b3774c` | `transferValueAndprocessRoute(address transferValueTo, uint256 amountValueTransfer, address tokenIn, uint256 amountIn, address tokenOut, uint256 amountOutMin, address to, bytes route)` | LiFiDEXAggregator: emits `Route`. |
| `0x8456cb59` | `pause()` | Owner or privileged. |
| `0x046f7da2` | `resume()` | Owner. |
| `0xefae576b` | `executeWithDynamicPatches(address valueSource, bytes valueGetter, address finalTarget, uint256 value, bytes data, uint256[] offsets, bool delegateCall)` | Patcher: emits `PatchExecuted`. |
| `0x922c8daa` | `depositAndExecuteWithDynamicPatches(address tokenAddress, address valueSource, bytes valueGetter, address finalTarget, uint256 value, bytes data, uint256[] offsets, bool delegateCall)` | Patcher: emits `TokensDeposited`, `PatchExecuted`. |
| `0x4d914979` | `executeWithMultiplePatches(address[] valueSources, bytes[] valueGetters, address finalTarget, uint256 value, bytes data, uint256[][] offsetGroups, bool delegateCall)` | Patcher. |
| `0xb7c52777` | `depositAndExecuteWithMultiplePatches(address tokenAddress, address[] valueSources, bytes[] valueGetters, address finalTarget, uint256 value, bytes data, uint256[][] offsetGroups, bool delegateCall)` | Patcher. |
| `0x27444dab` | `validateERC20Output(address tokenAddress, uint256 expectedAmount, address validationWalletAddress)` | Emits `OutputValidated`. |
| `0x5d865df2` | `validateNativeOutput(uint256 expectedAmount, address validationWalletAddress)` | Payable. Emits `OutputValidated`. |
| `0x24dd6483` | `wrapStETHToWstETH(uint256 _amount)` | OP only. |
| `0xa816ca92` | `unwrapWstETHToStETH(uint256 _amount)` | OP only. |
| `0x1eacd35f` | `collectTokenGasFees(address tokenAddress, uint256 feeAmount, uint256 chainId, address receiver)` | Legacy LiFuelFeeCollector. Emits `GasFeesCollected`. |
| `0x74ef98d9` | `collectNativeGasFees(uint256 feeAmount, uint256 chainId, address receiver)` | Legacy LiFuelFeeCollector. Payable. |

### 2.5 LiFiTimelockController

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x01d5062a` | `schedule(address target, uint256 value, bytes data, bytes32 predecessor, bytes32 salt, uint256 delay)` | Proposer role. Emits `CallScheduled`. |
| `0x8f2a0bb0` | `scheduleBatch(address[] targets, uint256[] values, bytes[] payloads, bytes32 predecessor, bytes32 salt, uint256 delay)` | Proposer role. Emits `CallScheduled` per call. |
| `0x134008d3` | `execute(address target, uint256 value, bytes payload, bytes32 predecessor, bytes32 salt)` | Executor role, after the delay. Emits `CallExecuted`. |
| `0xe38335e5` | `executeBatch(address[] targets, uint256[] values, bytes[] payloads, bytes32 predecessor, bytes32 salt)` | Executor role, after the delay. Used for both `DiamondCut` transactions of [diamond.md](diamond.md) §12. |
| `0xc4d252f5` | `cancel(bytes32 id)` | Canceller role. Emits `Cancelled`. |
| `0x64d62353` | `updateDelay(uint256 newDelay)` | Only through the timelock itself. Emits `MinDelayChange`. |
| `0x2f2ff15d` | `grantRole(bytes32 role, address account)` | Admin role. Emits `RoleGranted`. |
| `0xd547741f` | `revokeRole(bytes32 role, address account)` | Admin role. Emits `RoleRevoked`. |
| `0x2fc487ae` | `unpauseDiamond(address[] _blacklist)` | TIMELOCK_ADMIN_ROLE: unpauses the diamond with no delay. |
| `0x26eb8b06` | `setDiamondAddress(address _diamond)` | TIMELOCK_ADMIN_ROLE. Emits `DiamondAddressUpdated`. |
| `0xf27a0c92` | `getMinDelay()` | View: 10,800 on all eight chains. |

---

## 3. Addresses — Ethereum (chain ID 1)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code | Notes |
|----------|---------|------|-------|
| Executor | `0xd9B2Da9C45b118e4e93A004FB1452bCDB6cC0E88` | 7,732 |  |
| ReceiverAcrossV4 | `0x07Cc0a0b41641D349240e1988169Fa11b31FC24E` | 4,179 | `SPOKEPOOL()` = `0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5`; `EXECUTOR()` = the Executor above. |
| ReceiverAcrossV3 | `0x81F35E762B6792Eea8781fC52F72e62235A5C416` | 4,086 |  |
| ReceiverStargateV2 | `0xB539B40793171211DCA8834da044fC14bCe64BDC` | 7,312 | `executor()` = the Executor above. |
| ReceiverChainflip | `0x543733e09D7DD158Ee85024f7e95ff1460ef21D6` | 4,562 |  |
| ReceiverOIF | `0xe6ee2a573047598B2452a879F2188B31d0442dbF` | 3,843 |  |
| Receiver (legacy) | `0x050e198E36A73a1e32F15C3afC58C4506d82f657` | 9,116 | Not in the current periphery registry. |
| Permit2Proxy | `0x89c6340B1a1f4b25D36cd8B063D49045caF3f818` | 8,185 |  |
| ERC20Proxy | `0x68E1Acfa805dcA813116Ed6507E01c38D44318f0` | 2,552 |  |
| FeeCollector | `0x3Ef238c36035880EfbDfa239d218186b79Ad1d6F` | 4,717 |  |
| FeeForwarder | `0xCE40449B773a3E6E5e769ADb4e567179d4828cbd` | 3,037 |  |
| LiFuelFeeCollector (legacy) | `0xc02FFcdD914DbA646704439c6090BAbaD521d04C` | 5,763 | Legacy; not in the current periphery registry. |
| TokenWrapper | `0x5c57Cf61E473aE865E733A3A23fbB7618b4621F6` | 2,692 |  |
| GasZipPeriphery | `0x363d698649cd04f9692Ab86e8365b227c1ee859d` | 5,016 |  |
| LiFiDEXAggregator | `0x8189AFcC5B73Dc90600FeE92e5267Aff1D192884` | 20,392 |  |
| Patcher | `0x98dE828723F8aC654B79b8A1BB8E1E5D737F4F42` | 5,333 |  |
| OutputValidator | `0xFafE4c4CEc5Ed070A4aFDc0f92826c5Ba276Cb80` | 3,247 |  |
| LiFiTimelockController | `0x55117ECcC867Db72aEb25f728CCf57C3C3B4faEe` | 10,254 | Owner of the diamond. |

Not deployed on Ethereum: LidoWrapper.

## 4. Addresses — Base (chain ID 8453)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code | Notes |
|----------|---------|------|-------|
| Executor | `0x4DaC9d1769b9b304cb04741DCDEb2FC14aBdF110` | 9,446 |  |
| ReceiverAcrossV4 | `0x33b255b5db44A78c34381f89f1a454bc0Ef49871` | 4,230 | `SPOKEPOOL()` = `0x09aea4b2242abC8bb4BB78D537A67a245A7bEC64`; `EXECUTOR()` = the Executor above. |
| ReceiverAcrossV3 | `0xca6e6B692F568055adA0bF72A06D1EBbC938Fb23` | 3,977 |  |
| ReceiverStargateV2 | `0x1493e7B8d4DfADe0a178dAD9335470337A3a219A` | 7,367 | `executor()` = the Executor above. |
| ReceiverOIF | `0xe6ee2a573047598B2452a879F2188B31d0442dbF` | 3,843 |  |
| Receiver (legacy) | `0xeC03B65CbDc5f8858b02F44EBa54C90664249fb1` | 9,116 | Not in the current periphery registry. |
| Permit2Proxy | `0x89c6340B1a1f4b25D36cd8B063D49045caF3f818` | 8,185 |  |
| ERC20Proxy | `0x74a55CaDb12501A3707E9F3C5dfd8b563C6A5940` | 2,963 |  |
| FeeCollector | `0x0A6d96E7f4D7b96CFE42185DF61E64d255c12DFf` | 7,218 |  |
| FeeForwarder | `0xCE40449B773a3E6E5e769ADb4e567179d4828cbd` | 3,037 |  |
| LiFuelFeeCollector (legacy) | `0xc02FFcdD914DbA646704439c6090BAbaD521d04C` | 5,763 | Legacy; not in the current periphery registry. |
| TokenWrapper | `0x5215E9fd223BC909083fbdB2860213873046e45d` | 1,168 |  |
| GasZipPeriphery | `0x363d698649cd04f9692Ab86e8365b227c1ee859d` | 5,016 |  |
| LiFiDEXAggregator | `0x8189AFcC5B73Dc90600FeE92e5267Aff1D192884` | 20,392 |  |
| Patcher | `0x98dE828723F8aC654B79b8A1BB8E1E5D737F4F42` | 5,333 |  |
| OutputValidator | `0xFafE4c4CEc5Ed070A4aFDc0f92826c5Ba276Cb80` | 3,247 |  |
| LiFiTimelockController | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | 10,522 | Owner of the diamond. |

Not deployed on Base: ReceiverChainflip, LidoWrapper.

## 5. Addresses — Arbitrum One (chain ID 42161)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code | Notes |
|----------|---------|------|-------|
| Executor | `0x2dfaDAB8266483beD9Fd9A292Ce56596a2D1378D` | 9,446 |  |
| ReceiverAcrossV4 | `0x33b255b5db44A78c34381f89f1a454bc0Ef49871` | 4,230 |  |
| ReceiverAcrossV3 | `0xca6e6B692F568055adA0bF72A06D1EBbC938Fb23` | 3,977 |  |
| ReceiverStargateV2 | `0x1493e7B8d4DfADe0a178dAD9335470337A3a219A` | 7,367 |  |
| ReceiverChainflip | `0x37F584941242C8eada60bd6D8480cC0B6E36a0Cf` | 4,562 |  |
| ReceiverOIF | `0xe6ee2a573047598B2452a879F2188B31d0442dbF` | 3,843 |  |
| Receiver (legacy) | `0x050e198E36A73a1e32F15C3afC58C4506d82f657` | 9,116 | Not in the current periphery registry. |
| Permit2Proxy | `0x89c6340B1a1f4b25D36cd8B063D49045caF3f818` | 8,185 |  |
| ERC20Proxy | `0x5741A7FfE7c39Ca175546a54985fA79211290b51` | 2,963 |  |
| FeeCollector | `0xB0210dE78E28e2633Ca200609D9f528c13c26cD9` | 5,760 |  |
| FeeForwarder | `0xCE40449B773a3E6E5e769ADb4e567179d4828cbd` | 3,037 |  |
| LiFuelFeeCollector (legacy) | `0xc02FFcdD914DbA646704439c6090BAbaD521d04C` | 5,763 | Legacy; not in the current periphery registry. |
| TokenWrapper | `0x5215E9fd223BC909083fbdB2860213873046e45d` | 1,168 |  |
| GasZipPeriphery | `0x363d698649cd04f9692Ab86e8365b227c1ee859d` | 5,016 |  |
| LiFiDEXAggregator | `0x8189AFcC5B73Dc90600FeE92e5267Aff1D192884` | 20,392 |  |
| OutputValidator | `0xFafE4c4CEc5Ed070A4aFDc0f92826c5Ba276Cb80` | 3,247 |  |
| LiFiTimelockController | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | 10,522 | Owner of the diamond. |

Not deployed on Arbitrum: Patcher, LidoWrapper.

## 6. Addresses — Optimism (chain ID 10)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code | Notes |
|----------|---------|------|-------|
| Executor | `0xC9E66aa9b08EB667e450e072E96F7086AD9f2c91` | 7,884 |  |
| ReceiverAcrossV4 | `0xe417AD5eb9e919567620A48B3757cc182cCdf9e4` | 4,230 |  |
| ReceiverAcrossV3 | `0x28C7ef3789cF91C918cf86e5eF4b40FEBE24dAD3` | 4,086 |  |
| ReceiverStargateV2 | `0x556701899905f2f83AcA2977D3202Ee3a80f37b7` | 7,390 |  |
| ReceiverOIF | `0xe6ee2a573047598B2452a879F2188B31d0442dbF` | 3,843 |  |
| Receiver (legacy) | `0x050e198E36A73a1e32F15C3afC58C4506d82f657` | 9,116 | Not in the current periphery registry. |
| Permit2Proxy | `0x89c6340B1a1f4b25D36cd8B063D49045caF3f818` | 8,185 |  |
| ERC20Proxy | `0x314bE5fcf0A204837896e6028C47A9e1FC2919c7` | 2,552 |  |
| FeeCollector | `0x271970eE66c03c9D62d8e8c718b9841f2Ea7D817` | 4,717 |  |
| FeeForwarder | `0xCE40449B773a3E6E5e769ADb4e567179d4828cbd` | 3,037 |  |
| LiFuelFeeCollector (legacy) | `0xc02FFcdD914DbA646704439c6090BAbaD521d04C` | 5,763 | Legacy; not in the current periphery registry. |
| TokenWrapper | `0x6A300c0974212D8074f7ff20C6859623D8B7bce6` | 2,692 |  |
| GasZipPeriphery | `0x363d698649cd04f9692Ab86e8365b227c1ee859d` | 5,016 |  |
| LiFiDEXAggregator | `0xdEE54e0fC8b28b6b80fdb11fC74B9329A4de5220` | 17,804 |  |
| OutputValidator | `0xFafE4c4CEc5Ed070A4aFDc0f92826c5Ba276Cb80` | 3,247 |  |
| LidoWrapper | `0x071e340577Ad1123cF72fe098BF0b5E62a7ae07E` | 3,283 |  |
| LiFiTimelockController | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | 10,522 | Owner of the diamond. |

Not deployed on Optimism: ReceiverChainflip, Patcher.

## 7. Addresses — Polygon PoS (chain ID 137)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code | Notes |
|----------|---------|------|-------|
| Executor | `0x2dfaDAB8266483beD9Fd9A292Ce56596a2D1378D` | 9,446 |  |
| ReceiverAcrossV4 | `0x33b255b5db44A78c34381f89f1a454bc0Ef49871` | 4,230 |  |
| ReceiverAcrossV3 | `0xca6e6B692F568055adA0bF72A06D1EBbC938Fb23` | 3,977 |  |
| ReceiverStargateV2 | `0x1493e7B8d4DfADe0a178dAD9335470337A3a219A` | 7,367 |  |
| ReceiverOIF | `0xe6ee2a573047598B2452a879F2188B31d0442dbF` | 3,843 |  |
| Receiver (legacy) | `0x050e198E36A73a1e32F15C3afC58C4506d82f657` | 9,116 | Not in the current periphery registry. |
| Permit2Proxy | `0x89c6340B1a1f4b25D36cd8B063D49045caF3f818` | 8,185 |  |
| ERC20Proxy | `0x5741A7FfE7c39Ca175546a54985fA79211290b51` | 2,963 |  |
| FeeCollector | `0xbD6C7B0d2f68c2b7805d88388319cfB6EcB50eA9` | 5,760 |  |
| FeeForwarder | `0xCE40449B773a3E6E5e769ADb4e567179d4828cbd` | 3,037 |  |
| LiFuelFeeCollector (legacy) | `0xc02FFcdD914DbA646704439c6090BAbaD521d04C` | 5,763 | Legacy; not in the current periphery registry. |
| TokenWrapper | `0x5215E9fd223BC909083fbdB2860213873046e45d` | 1,168 |  |
| GasZipPeriphery | `0x363d698649cd04f9692Ab86e8365b227c1ee859d` | 5,016 |  |
| LiFiDEXAggregator | `0x8189AFcC5B73Dc90600FeE92e5267Aff1D192884` | 20,392 |  |
| Patcher | `0x98dE828723F8aC654B79b8A1BB8E1E5D737F4F42` | 5,333 |  |
| OutputValidator | `0xFafE4c4CEc5Ed070A4aFDc0f92826c5Ba276Cb80` | 3,247 |  |
| LiFiTimelockController | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | 10,522 | Owner of the diamond. |

Not deployed on Polygon: ReceiverChainflip, LidoWrapper.

## 8. Addresses — BNB Smart Chain (chain ID 56)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code | Notes |
|----------|---------|------|-------|
| Executor | `0x2dfaDAB8266483beD9Fd9A292Ce56596a2D1378D` | 9,446 |  |
| ReceiverAcrossV4 | `0x33b255b5db44A78c34381f89f1a454bc0Ef49871` | 4,230 |  |
| ReceiverAcrossV3 | `0x22713FA768c255fd7A6186ad39896126EDCF7946` | 4,086 |  |
| ReceiverStargateV2 | `0x1493e7B8d4DfADe0a178dAD9335470337A3a219A` | 7,367 |  |
| ReceiverOIF | `0xe6ee2a573047598B2452a879F2188B31d0442dbF` | 3,843 |  |
| Receiver (legacy) | `0x050e198E36A73a1e32F15C3afC58C4506d82f657` | 9,116 | Not in the current periphery registry. |
| Permit2Proxy | `0x89c6340B1a1f4b25D36cd8B063D49045caF3f818` | 8,185 |  |
| ERC20Proxy | `0x5741A7FfE7c39Ca175546a54985fA79211290b51` | 2,963 |  |
| FeeCollector | `0xbD6C7B0d2f68c2b7805d88388319cfB6EcB50eA9` | 5,760 |  |
| FeeForwarder | `0xCE40449B773a3E6E5e769ADb4e567179d4828cbd` | 3,037 |  |
| LiFuelFeeCollector (legacy) | `0xc02FFcdD914DbA646704439c6090BAbaD521d04C` | 5,763 | Legacy; not in the current periphery registry. |
| TokenWrapper | `0x5215E9fd223BC909083fbdB2860213873046e45d` | 1,168 |  |
| GasZipPeriphery | `0x363d698649cd04f9692Ab86e8365b227c1ee859d` | 5,016 |  |
| LiFiDEXAggregator | `0x8189AFcC5B73Dc90600FeE92e5267Aff1D192884` | 20,392 |  |
| OutputValidator | `0xFafE4c4CEc5Ed070A4aFDc0f92826c5Ba276Cb80` | 3,247 |  |
| LiFiTimelockController | `0x55117ECcC867Db72aEb25f728CCf57C3C3B4faEe` | 10,254 | Owner of the diamond. |

Not deployed on BNB: ReceiverChainflip, Patcher, LidoWrapper.

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code | Notes |
|----------|---------|------|-------|
| Executor | `0x2dfaDAB8266483beD9Fd9A292Ce56596a2D1378D` | 9,446 |  |
| ReceiverStargateV2 | `0x1493e7B8d4DfADe0a178dAD9335470337A3a219A` | 7,367 |  |
| ReceiverOIF | `0xa2712aEecbff8a1542c78Cf49C4fE4CE4B09E1dB` | 3,843 |  |
| Receiver (legacy) | `0x050e198E36A73a1e32F15C3afC58C4506d82f657` | 9,116 | Not in the current periphery registry. |
| Permit2Proxy | `0x89c6340B1a1f4b25D36cd8B063D49045caF3f818` | 8,185 |  |
| ERC20Proxy | `0x5741A7FfE7c39Ca175546a54985fA79211290b51` | 2,963 |  |
| FeeCollector | `0xB0210dE78E28e2633Ca200609D9f528c13c26cD9` | 5,760 |  |
| FeeForwarder | `0xCE40449B773a3E6E5e769ADb4e567179d4828cbd` | 3,037 |  |
| LiFuelFeeCollector (legacy) | `0xc02FFcdD914DbA646704439c6090BAbaD521d04C` | 5,763 | Legacy; not in the current periphery registry. |
| TokenWrapper | `0x5215E9fd223BC909083fbdB2860213873046e45d` | 1,168 |  |
| GasZipPeriphery | `0x1e5637e6bE93D50bB8eFa70D219d06291dcF5284` | 5,016 |  |
| LiFiDEXAggregator | `0x6140b987d6B51Fd75b66C3B07733Beb5167c42fc` | 15,651 |  |
| Patcher | `0x98dE828723F8aC654B79b8A1BB8E1E5D737F4F42` | 5,333 |  |
| OutputValidator | `0xFafE4c4CEc5Ed070A4aFDc0f92826c5Ba276Cb80` | 3,247 |  |
| LiFiTimelockController | `0x5604A94A3438C3074EFFF803fab14B7244fe4E29` | 10,522 | Owner of the diamond. |

Not deployed on Avalanche: ReceiverAcrossV4, ReceiverAcrossV3, ReceiverChainflip, LidoWrapper.

## 10. Addresses — Robinhood Chain (chain ID 4663)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code | Notes |
|----------|---------|------|-------|
| Executor | `0x464fC28B9CbC1781286c8626B6E925275c8C14F1` | 7,732 |  |
| ReceiverAcrossV4 | `0x90dd81bD07763f39dF31D0089B61520461557D71` | 4,179 | `SPOKEPOOL()` = `0xd29C85F15DF544bA632C9E25829fd29d767d7978`; `EXECUTOR()` = the Executor above. |
| ReceiverOIF | `0xc1DcE9F7F5a7477CaE473D262e47b05bF2E712a3` | 3,843 |  |
| Permit2Proxy | `0x8eABB4E117fB70b346592e013855f6d825F50af1` | 8,037 |  |
| ERC20Proxy | `0xfb3973800ADf5B997E910F2DD90158924370612A` | 2,552 |  |
| FeeCollector | `0xAD257784C6D50640d1EFa31cfB3e75bD566f63BA` | 4,717 |  |
| FeeForwarder | `0xF4BFFE4dfC693f37715A47c15BdA8af9ed8f7Cf1` | 3,037 |  |
| TokenWrapper | `0x0d0E59aCdc126fA8791C00507b2Ce8DdB4036cbE` | 2,997 |  |
| GasZipPeriphery | `0x9F80FDADcA03a6e062B13BAe1B5e5c0B2A166049` | 4,866 |  |
| LiFiDEXAggregator | `0x6A330d43F40CA4E21842685aEE7692a6a9d4c0C8` | 22,427 |  |
| OutputValidator | `0x321E5015072eB568B24F46e5A92FFcc4316056AB` | 3,185 |  |
| LiFiTimelockController | `0x6E9Beb6997dAE04122f1f8f8980f3dc8225443F3` | 10,254 | Owner of the diamond. |

Not deployed on Robinhood Chain: ReceiverAcrossV3, ReceiverStargateV2, ReceiverChainflip, Receiver (legacy), LiFuelFeeCollector (legacy), Patcher, LidoWrapper.

---

## 11. Cross-chain summary

| Contract | ETH | Base | Arb | OP | Poly | BNB | Avax | RH (4663) |
|----------|-----|------|-----|----|------|-----|------|-----------|
| Executor | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ReceiverAcrossV4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| ReceiverAcrossV3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| ReceiverStargateV2 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| ReceiverChainflip | ✓ | — | ✓ | — | — | — | — | — |
| ReceiverOIF | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Receiver (legacy) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Permit2Proxy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ERC20Proxy | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| FeeCollector | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| FeeForwarder | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| LiFuelFeeCollector (legacy) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| TokenWrapper | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| GasZipPeriphery | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| LiFiDEXAggregator | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Patcher | ✓ | ✓ | — | — | ✓ | — | ✓ | — |
| OutputValidator | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| LidoWrapper | — | — | — | ✓ | — | — | — | — |
| LiFiTimelockController | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

✓ = deployed at the address of §3–§10. — = not deployed (no entry in `deployments/<network>.json`; where an address of another chain was probed, `eth_getCode` returned `0x` or unrelated code). Robinhood Chain has its own address for every contract.

---

## 12. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| All periphery contracts | Immutable, no proxy | The EIP-1967 implementation slot is empty on every address checked (§15). Receivers hold `EXECUTOR` / `executor` and the bridge endpoint as immutables. | None. A new version is a new address; the diamond's PeripheryRegistryFacet records it (`PeripheryContractRegistered`). |
| LiFiTimelockController | Not a proxy | Plain contract. | Its own roles: proposers schedule, executors execute after `getMinDelay()`, cancellers cancel. |

---

## 13. Detection invariants & gotchas

1. **Destination = the underlying bridge first, then (maybe) LI.FI.** In the Base sample of §15 the Across `FilledRelay` pays ReceiverAcrossV4, the receiver moves the USDC to the Executor, the Executor swaps it, pays the user and emits `LiFiTransferCompleted`. For routes without a destination call, stop at the bridge's own payout event.
2. **`LiFiTransferCompleted.amount` is not in `receivingAssetId` units after a swap** (§1.1). In the Base sample, `receivingAssetId` is USDC and `amount` is 749.26 AERO (18 decimals).
3. **`LiFiTransferRecovered` = destination swap failed, bridged token delivered.** In the Base sample the receiver sent 0.0152 WETH to the final receiver. Count it as a payout.
4. **A receiver only accepts its bridge.** ReceiverAcrossV4 checks `msg.sender == SPOKEPOOL`, ReceiverStargateV2 checks the LayerZero endpoint and the Stargate pool, ReceiverChainflip checks the Chainflip vault, ReceiverOIF checks the output settler. A receiver call from any other sender is an attack attempt and reverts.
5. **Permit2Proxy hides the user in `tx.from`.** For `callDiamondWithPermit2` and `callDiamondWithPermit2Witness` a relayer can send the transaction; the user is the permit signer, and the token `Transfer` goes user → Permit2Proxy → diamond.
6. **Fees move in the source transaction.** FeeCollector keeps fees for later withdrawal (`FeesCollected`, then `FeesWithdrawn` / `LiFiFeesWithdrawn`). FeeForwarder sends them out at once (`FeesForwarded`). Both appear in the diamond's transaction as a fee-step `AssetSwapped` ([diamond.md](diamond.md) §13).
7. **LiFiDEXAggregator `Route` is a same-chain swap.** It is not a bridge event.
8. **Admin triggers.** Timelock: `CallScheduled` (any pending admin call), `MinDelayChange`, `RoleGranted`, `RoleRevoked`, `Cancelled`. Periphery: `OwnershipTransferred`, `TokensWithdrawn`, `AuthorizationChanged` (ERC20Proxy), `ERC20ProxySet`.

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_LIFI_TRANSFER_COMPLETED            = '\xb8c86983f929c6b770461983d1bbde1870408120f07123e9c12d49f35a0b4c4b'
TOPIC_LIFI_TRANSFER_RECOVERED            = '\x1fbfa988fd46deed0de12c94c7b5dcb537d51b804246d0083f245f7a8997d170'
TOPIC_ASSET_SWAPPED                      = '\x7bfdfdb5e3a3776976e53cb0607060f54c5312701c8cba1155cc4d5394440b38'
TOPIC_FEES_COLLECTED                     = '\x28a87b6059180e46de5fb9ab35eb043e8fe00ab45afcc7789e3934ecbbcde3ea'
TOPIC_FEES_WITHDRAWN                     = '\x5e110f8bc8a20b65dcc87f224bdf1cc039346e267118bae2739847f07321ffa8'
TOPIC_LIFI_FEES_WITHDRAWN                = '\xe0ac2a6b74759312758ae3b784411c8e2f3b8bd81fecff40b906d69030af4bfc'
TOPIC_FEES_FORWARDED                     = '\x3a7029951ba36c1af37954df919ce2f9a95c3f5c2c2e872d5e7fd47c61a6df26'
TOPIC_DEX_AGGREGATOR_ROUTE               = '\x2db5ddd0b42bdbca0d69ea16f234a870a485854ae0d91f16643d6f317d8b8994'
TOPIC_OUTPUT_VALIDATED                   = '\x29991351642fce7de30ac927d88ce3a9cfea9ec0b607b508e6d1060e19221b82'
TOPIC_PATCH_EXECUTED                     = '\x388c63fb82adbdf7c1046e997e85d8e71e98e878c43d0fb81b76254bee16b29a'
TOPIC_TOKENS_WITHDRAWN                   = '\x6337ed398c0e8467698c581374fdce4db14922df487b5a39483079f5f59b60a4'
TOPIC_ERC20_PROXY_AUTH_CHANGED           = '\x5fe3a0cb9aeae856eac34445ace9544f3e15c21fa6f9bffeca60d662a690ca1b'
TOPIC_ERC20_PROXY_SET                    = '\x2c835b8316da89c3b658f57c3b39e7b191fddc4b104beeda23042d5dadf455a9'
TOPIC_LIFUEL_GAS_FEES_COLLECTED          = '\x03e28afce33ddcc0ab4ff4b9050c6ff0c323292f46b577db77c1a7281320de56'
TOPIC_TIMELOCK_CALL_SCHEDULED            = '\x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca'
TOPIC_TIMELOCK_CALL_EXECUTED             = '\xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58'
TOPIC_TIMELOCK_CANCELLED                 = '\xbaa1eb22f2a492ba1a5fea61b8df4d27c6c8b5f3971e63bb58fa14ff72eedb70'
TOPIC_TIMELOCK_MIN_DELAY_CHANGE          = '\x11c24f4ead16507c69ac467fbd5e4eed5fb5c699626d2cc6d66421df253886d5'
TOPIC_TIMELOCK_ROLE_GRANTED              = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_TIMELOCK_ROLE_REVOKED              = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'

-- ===== Selectors (chain-agnostic) =====
SEL_EXECUTOR_SWAP_AND_COMPLETE           = '\x4f91bc2b'
SEL_EXECUTOR_SWAP_AND_EXECUTE            = '\xa83cbaa3'
SEL_HANDLE_V3_ACROSS_MESSAGE             = '\x3a5be8cb'
SEL_LZ_COMPOSE                           = '\xd0a10260'
SEL_CF_RECEIVE                           = '\x4904ac5f'
SEL_OUTPUT_FILLED                        = '\xc80b0e0f'
SEL_SG_RECEIVE                           = '\xab8236f3'
SEL_X_RECEIVE                            = '\xfd614f41'
SEL_CALL_DIAMOND_EIP2612                 = '\xd7a08473'
SEL_CALL_DIAMOND_PERMIT2                 = '\x0193b9fc'
SEL_CALL_DIAMOND_PERMIT2_WITNESS         = '\x4561136e'
SEL_WITHDRAW_TOKEN                       = '\x01e33667'
SEL_TIMELOCK_SCHEDULE_BATCH              = '\x8f2a0bb0'
SEL_TIMELOCK_EXECUTE_BATCH               = '\xe38335e5'
SEL_TIMELOCK_UPDATE_DELAY                = '\x64d62353'

-- ===== Addresses (network-specific) =====
-- TokenWrapper, Patcher, OutputValidator and LidoWrapper: see the tables of §3-§10
ETH_LIFI_EXECUTOR                        = '\xd9b2da9c45b118e4e93a004fb1452bcdb6cc0e88'
ETH_LIFI_RECEIVER_ACROSS_V4              = '\x07cc0a0b41641d349240e1988169fa11b31fc24e'
ETH_LIFI_RECEIVER_ACROSS_V3              = '\x81f35e762b6792eea8781fc52f72e62235a5c416'
ETH_LIFI_RECEIVER_STARGATE_V2            = '\xb539b40793171211dca8834da044fc14bce64bdc'
ETH_LIFI_RECEIVER_CHAINFLIP              = '\x543733e09d7dd158ee85024f7e95ff1460ef21d6'
ETH_LIFI_RECEIVER_OIF                    = '\xe6ee2a573047598b2452a879f2188b31d0442dbf'
ETH_LIFI_RECEIVER_LEGACY                 = '\x050e198e36a73a1e32f15c3afc58c4506d82f657'
ETH_LIFI_PERMIT2_PROXY                   = '\x89c6340b1a1f4b25d36cd8b063d49045caf3f818'
ETH_LIFI_ERC20_PROXY                     = '\x68e1acfa805dca813116ed6507e01c38d44318f0'
ETH_LIFI_FEE_COLLECTOR                   = '\x3ef238c36035880efbdfa239d218186b79ad1d6f'
ETH_LIFI_FEE_FORWARDER                   = '\xce40449b773a3e6e5e769adb4e567179d4828cbd'
ETH_LIFI_LIFUEL_FEE_COLLECTOR            = '\xc02ffcdd914dba646704439c6090babad521d04c'
ETH_LIFI_GASZIP_PERIPHERY                = '\x363d698649cd04f9692ab86e8365b227c1ee859d'
ETH_LIFI_DEX_AGGREGATOR                  = '\x8189afcc5b73dc90600fee92e5267aff1d192884'
ETH_LIFI_TIMELOCK                        = '\x55117eccc867db72aeb25f728ccf57c3c3b4faee'
BASE_LIFI_EXECUTOR                       = '\x4dac9d1769b9b304cb04741dcdeb2fc14abdf110'
BASE_LIFI_RECEIVER_ACROSS_V4             = '\x33b255b5db44a78c34381f89f1a454bc0ef49871'
BASE_LIFI_RECEIVER_ACROSS_V3             = '\xca6e6b692f568055ada0bf72a06d1ebbc938fb23'
BASE_LIFI_RECEIVER_STARGATE_V2           = '\x1493e7b8d4dfade0a178dad9335470337a3a219a'
BASE_LIFI_RECEIVER_OIF                   = '\xe6ee2a573047598b2452a879f2188b31d0442dbf'
BASE_LIFI_RECEIVER_LEGACY                = '\xec03b65cbdc5f8858b02f44eba54c90664249fb1'
BASE_LIFI_PERMIT2_PROXY                  = '\x89c6340b1a1f4b25d36cd8b063d49045caf3f818'
BASE_LIFI_ERC20_PROXY                    = '\x74a55cadb12501a3707e9f3c5dfd8b563c6a5940'
BASE_LIFI_FEE_COLLECTOR                  = '\x0a6d96e7f4d7b96cfe42185df61e64d255c12dff'
BASE_LIFI_FEE_FORWARDER                  = '\xce40449b773a3e6e5e769adb4e567179d4828cbd'
BASE_LIFI_LIFUEL_FEE_COLLECTOR           = '\xc02ffcdd914dba646704439c6090babad521d04c'
BASE_LIFI_GASZIP_PERIPHERY               = '\x363d698649cd04f9692ab86e8365b227c1ee859d'
BASE_LIFI_DEX_AGGREGATOR                 = '\x8189afcc5b73dc90600fee92e5267aff1d192884'
BASE_LIFI_TIMELOCK                       = '\x5604a94a3438c3074efff803fab14b7244fe4e29'
ARB_LIFI_EXECUTOR                        = '\x2dfadab8266483bed9fd9a292ce56596a2d1378d'
ARB_LIFI_RECEIVER_ACROSS_V4              = '\x33b255b5db44a78c34381f89f1a454bc0ef49871'
ARB_LIFI_RECEIVER_ACROSS_V3              = '\xca6e6b692f568055ada0bf72a06d1ebbc938fb23'
ARB_LIFI_RECEIVER_STARGATE_V2            = '\x1493e7b8d4dfade0a178dad9335470337a3a219a'
ARB_LIFI_RECEIVER_CHAINFLIP              = '\x37f584941242c8eada60bd6d8480cc0b6e36a0cf'
ARB_LIFI_RECEIVER_OIF                    = '\xe6ee2a573047598b2452a879f2188b31d0442dbf'
ARB_LIFI_RECEIVER_LEGACY                 = '\x050e198e36a73a1e32f15c3afc58c4506d82f657'
ARB_LIFI_PERMIT2_PROXY                   = '\x89c6340b1a1f4b25d36cd8b063d49045caf3f818'
ARB_LIFI_ERC20_PROXY                     = '\x5741a7ffe7c39ca175546a54985fa79211290b51'
ARB_LIFI_FEE_COLLECTOR                   = '\xb0210de78e28e2633ca200609d9f528c13c26cd9'
ARB_LIFI_FEE_FORWARDER                   = '\xce40449b773a3e6e5e769adb4e567179d4828cbd'
ARB_LIFI_LIFUEL_FEE_COLLECTOR            = '\xc02ffcdd914dba646704439c6090babad521d04c'
ARB_LIFI_GASZIP_PERIPHERY                = '\x363d698649cd04f9692ab86e8365b227c1ee859d'
ARB_LIFI_DEX_AGGREGATOR                  = '\x8189afcc5b73dc90600fee92e5267aff1d192884'
ARB_LIFI_TIMELOCK                        = '\x5604a94a3438c3074efff803fab14b7244fe4e29'
OP_LIFI_EXECUTOR                         = '\xc9e66aa9b08eb667e450e072e96f7086ad9f2c91'
OP_LIFI_RECEIVER_ACROSS_V4               = '\xe417ad5eb9e919567620a48b3757cc182ccdf9e4'
OP_LIFI_RECEIVER_ACROSS_V3               = '\x28c7ef3789cf91c918cf86e5ef4b40febe24dad3'
OP_LIFI_RECEIVER_STARGATE_V2             = '\x556701899905f2f83aca2977d3202ee3a80f37b7'
OP_LIFI_RECEIVER_OIF                     = '\xe6ee2a573047598b2452a879f2188b31d0442dbf'
OP_LIFI_RECEIVER_LEGACY                  = '\x050e198e36a73a1e32f15c3afc58c4506d82f657'
OP_LIFI_PERMIT2_PROXY                    = '\x89c6340b1a1f4b25d36cd8b063d49045caf3f818'
OP_LIFI_ERC20_PROXY                      = '\x314be5fcf0a204837896e6028c47a9e1fc2919c7'
OP_LIFI_FEE_COLLECTOR                    = '\x271970ee66c03c9d62d8e8c718b9841f2ea7d817'
OP_LIFI_FEE_FORWARDER                    = '\xce40449b773a3e6e5e769adb4e567179d4828cbd'
OP_LIFI_LIFUEL_FEE_COLLECTOR             = '\xc02ffcdd914dba646704439c6090babad521d04c'
OP_LIFI_GASZIP_PERIPHERY                 = '\x363d698649cd04f9692ab86e8365b227c1ee859d'
OP_LIFI_DEX_AGGREGATOR                   = '\xdee54e0fc8b28b6b80fdb11fc74b9329a4de5220'
OP_LIFI_TIMELOCK                         = '\x5604a94a3438c3074efff803fab14b7244fe4e29'
POLY_LIFI_EXECUTOR                       = '\x2dfadab8266483bed9fd9a292ce56596a2d1378d'
POLY_LIFI_RECEIVER_ACROSS_V4             = '\x33b255b5db44a78c34381f89f1a454bc0ef49871'
POLY_LIFI_RECEIVER_ACROSS_V3             = '\xca6e6b692f568055ada0bf72a06d1ebbc938fb23'
POLY_LIFI_RECEIVER_STARGATE_V2           = '\x1493e7b8d4dfade0a178dad9335470337a3a219a'
POLY_LIFI_RECEIVER_OIF                   = '\xe6ee2a573047598b2452a879f2188b31d0442dbf'
POLY_LIFI_RECEIVER_LEGACY                = '\x050e198e36a73a1e32f15c3afc58c4506d82f657'
POLY_LIFI_PERMIT2_PROXY                  = '\x89c6340b1a1f4b25d36cd8b063d49045caf3f818'
POLY_LIFI_ERC20_PROXY                    = '\x5741a7ffe7c39ca175546a54985fa79211290b51'
POLY_LIFI_FEE_COLLECTOR                  = '\xbd6c7b0d2f68c2b7805d88388319cfb6ecb50ea9'
POLY_LIFI_FEE_FORWARDER                  = '\xce40449b773a3e6e5e769adb4e567179d4828cbd'
POLY_LIFI_LIFUEL_FEE_COLLECTOR           = '\xc02ffcdd914dba646704439c6090babad521d04c'
POLY_LIFI_GASZIP_PERIPHERY               = '\x363d698649cd04f9692ab86e8365b227c1ee859d'
POLY_LIFI_DEX_AGGREGATOR                 = '\x8189afcc5b73dc90600fee92e5267aff1d192884'
POLY_LIFI_TIMELOCK                       = '\x5604a94a3438c3074efff803fab14b7244fe4e29'
BNB_LIFI_EXECUTOR                        = '\x2dfadab8266483bed9fd9a292ce56596a2d1378d'
BNB_LIFI_RECEIVER_ACROSS_V4              = '\x33b255b5db44a78c34381f89f1a454bc0ef49871'
BNB_LIFI_RECEIVER_ACROSS_V3              = '\x22713fa768c255fd7a6186ad39896126edcf7946'
BNB_LIFI_RECEIVER_STARGATE_V2            = '\x1493e7b8d4dfade0a178dad9335470337a3a219a'
BNB_LIFI_RECEIVER_OIF                    = '\xe6ee2a573047598b2452a879f2188b31d0442dbf'
BNB_LIFI_RECEIVER_LEGACY                 = '\x050e198e36a73a1e32f15c3afc58c4506d82f657'
BNB_LIFI_PERMIT2_PROXY                   = '\x89c6340b1a1f4b25d36cd8b063d49045caf3f818'
BNB_LIFI_ERC20_PROXY                     = '\x5741a7ffe7c39ca175546a54985fa79211290b51'
BNB_LIFI_FEE_COLLECTOR                   = '\xbd6c7b0d2f68c2b7805d88388319cfb6ecb50ea9'
BNB_LIFI_FEE_FORWARDER                   = '\xce40449b773a3e6e5e769adb4e567179d4828cbd'
BNB_LIFI_LIFUEL_FEE_COLLECTOR            = '\xc02ffcdd914dba646704439c6090babad521d04c'
BNB_LIFI_GASZIP_PERIPHERY                = '\x363d698649cd04f9692ab86e8365b227c1ee859d'
BNB_LIFI_DEX_AGGREGATOR                  = '\x8189afcc5b73dc90600fee92e5267aff1d192884'
BNB_LIFI_TIMELOCK                        = '\x55117eccc867db72aeb25f728ccf57c3c3b4faee'
AVAX_LIFI_EXECUTOR                       = '\x2dfadab8266483bed9fd9a292ce56596a2d1378d'
AVAX_LIFI_RECEIVER_STARGATE_V2           = '\x1493e7b8d4dfade0a178dad9335470337a3a219a'
AVAX_LIFI_RECEIVER_OIF                   = '\xa2712aeecbff8a1542c78cf49c4fe4ce4b09e1db'
AVAX_LIFI_RECEIVER_LEGACY                = '\x050e198e36a73a1e32f15c3afc58c4506d82f657'
AVAX_LIFI_PERMIT2_PROXY                  = '\x89c6340b1a1f4b25d36cd8b063d49045caf3f818'
AVAX_LIFI_ERC20_PROXY                    = '\x5741a7ffe7c39ca175546a54985fa79211290b51'
AVAX_LIFI_FEE_COLLECTOR                  = '\xb0210de78e28e2633ca200609d9f528c13c26cd9'
AVAX_LIFI_FEE_FORWARDER                  = '\xce40449b773a3e6e5e769adb4e567179d4828cbd'
AVAX_LIFI_LIFUEL_FEE_COLLECTOR           = '\xc02ffcdd914dba646704439c6090babad521d04c'
AVAX_LIFI_GASZIP_PERIPHERY               = '\x1e5637e6be93d50bb8efa70d219d06291dcf5284'
AVAX_LIFI_DEX_AGGREGATOR                 = '\x6140b987d6b51fd75b66c3b07733beb5167c42fc'
AVAX_LIFI_TIMELOCK                       = '\x5604a94a3438c3074efff803fab14b7244fe4e29'
RH_LIFI_EXECUTOR                         = '\x464fc28b9cbc1781286c8626b6e925275c8c14f1'
RH_LIFI_RECEIVER_ACROSS_V4               = '\x90dd81bd07763f39df31d0089b61520461557d71'
RH_LIFI_RECEIVER_OIF                     = '\xc1dce9f7f5a7477cae473d262e47b05bf2e712a3'
RH_LIFI_PERMIT2_PROXY                    = '\x8eabb4e117fb70b346592e013855f6d825f50af1'
RH_LIFI_ERC20_PROXY                      = '\xfb3973800adf5b997e910f2dd90158924370612a'
RH_LIFI_FEE_COLLECTOR                    = '\xad257784c6d50640d1efa31cfb3e75bd566f63ba'
RH_LIFI_FEE_FORWARDER                    = '\xf4bffe4dfc693f37715a47c15bda8af9ed8f7cf1'
RH_LIFI_GASZIP_PERIPHERY                 = '\x9f80fdadca03a6e062b13bae1b5e5c0b2a166049'
RH_LIFI_DEX_AGGREGATOR                   = '\x6a330d43f40ca4e21842685aee7692a6a9d4c0c8'
RH_LIFI_TIMELOCK                         = '\x6e9beb6997dae04122f1f8f8980f3dc8225443f3'
```

---

## 15. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` / `[0:4]` from the explorer-verified ABIs of the deployed periphery contracts, and cross-checked against `lifinance/contracts` `src/Periphery/*.sol`, `src/Security/LiFiTimelockController.sol`, `src/Interfaces/ILiFi.sol` and `archive/src/Periphery/Receiver.sol`.
- **Addresses:** from `deployments/<network>.json` and the `Periphery` block of `deployments/<network>.diamond.json` for the eight networks; each existence-checked with `eth_getCode` on its chain (§3–§10). The code sizes are in §3–§10.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):**

  | Event (Executor address scan) | ETH | Base | Arb | OP | Poly | BNB | Avax | RH |
  |---|---|---|---|---|---|---|---|---|
  | `LiFiTransferCompleted` | 1 | 87 | 11 | 2 | 9 | 479 | 0 | 298 |
  | `AssetSwapped` | 1 | 87 | 11 | 2 | 9 | 479 | 0 | 298 |

  - `LiFiTransferRecovered` (topic scan, any emitter): Ethereum 1 (1 ReceiverStargateV2); Base 8 (7 ReceiverAcrossV4, 1 ReceiverStargateV2); Arbitrum 1 (1 ReceiverAcrossV4); Optimism 0; Polygon 2 (2 ReceiverAcrossV4); BNB 77 (77 ReceiverAcrossV4); Avalanche 0; Robinhood Chain 6 (6 ReceiverAcrossV4).
  - `LiFiTransferCompleted` (topic scan, any emitter): Ethereum 1 (1 Executor); Base 87 (87 Executor); Arbitrum 11 (11 Executor); Optimism 2 (2 Executor); Polygon 9 (9 Executor); BNB 479 (479 Executor); Avalanche 0; Robinhood Chain 298 (298 Executor).
- **Sample transactions read:** Base `0x7a0c00d617e4668b7915ec3cd5df00b5cc79e97f5c7af66528d1d083bc3ba304` (Across fill from Polygon: `FilledRelay` → 630.64 USDC to ReceiverAcrossV4 `0x33b255b5db44A78c34381f89f1a454bc0Ef49871` → Executor `0x4DaC9d1769b9b304cb04741DCDEb2FC14aBdF110` → swap to AERO → `Transfer` of 749.26 AERO to the receiver → `LiFiTransferCompleted` with `receivingAssetId` = USDC and `amount` = 749256988150143394551); Base `0xacb8ed7f8fb91846b8857b996310ae16bd2bd70b11d95c7ee8fc03ee6d5f7c77` (Across fill from Robinhood Chain, origin chain id 4663: WETH to ReceiverAcrossV4, the Executor call fails, 15173003224019732 WETH to the receiver, `LiFiTransferRecovered`).

No periphery address listed above is an EIP-1967 proxy: the implementation slot read by the code check returned zero for every one of them.

Authoritative sources:
- [lifinance/contracts](https://github.com/lifinance/contracts) (`src/Periphery/`, `src/Security/LiFiTimelockController.sol`, `archive/src/Periphery/Receiver.sol`, `deployments/`)
- [LI.FI docs index](https://docs.li.fi/llms.txt) · [status tracking](https://docs.li.fi/introduction/user-flows-and-examples/status-tracking)
- Explorers (verified sources) — [Etherscan Executor](https://etherscan.io/address/0xd9b2da9c45b118e4e93a004fb1452bcdb6cc0e88) · [Basescan Executor](https://basescan.org/address/0x4dac9d1769b9b304cb04741dcdeb2fc14abdf110) · [Blockscout Ethereum](https://eth.blockscout.com) · [Blockscout Base](https://base.blockscout.com) · [Robinhood Chain Blockscout](https://robinhoodchain.blockscout.com)
