# Across Protocol — Topics, Selectors, Addresses (Ethereum + Base + BNB + Arbitrum + Optimism + Polygon; NOT Avalanche)

**Status:** verified against Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, and Polygon mainnet RPC, the canonical `across-protocol/contracts` repo (`broadcast/deployed-addresses.json`, `deployments/legacy-addresses.json`) and `across-protocol/constants`, on 2026-06-09. Event topics/selectors recomputed locally as `keccak256(sig)` and cross-checked against live `eth_getLogs`; addresses existence-checked via `eth_getCode`; proxy impls read from the EIP-1967 slot live.
**Scope:** the live Across intent-bridge system — one canonical **HubPool** + supporting contracts on Ethereum L1, plus one **SpokePool** per spoke chain. Of the seven requested chains, six have a SpokePool (Ethereum, Base, BNB, Arbitrum, Optimism, Polygon); **Avalanche C-Chain has no Across deployment** (every Across address returns `0x`). Topics/selectors are chain-agnostic; addresses are network-specific.

Across is a UMA-optimistic-oracle **intent bridge**: a user *deposits* funds into the origin SpokePool specifying an output token/amount/recipient on a destination chain; a **relayer** *fills* the request on the destination chain immediately out of its own inventory, then is reimbursed (plus an LP fee) after the HubPool's UMA-bonded root-bundle settlement clears on L1. There is no per-transfer escrow on the canonical bridge — only the relayer-refund accounting bundled into Merkle roots and disbursed by `executeRelayerRefundLeaf`.

Three architectural facts a monitor must internalize before indexing:

1. **SpokePools are UUPS proxies (ERC-1967 + ERC-1822), one per chain, at *different* addresses on each chain** (no shared vanity). The EIP-1967 impl slot is populated and the admin slot is empty (UUPS keeps upgrade auth in the impl, gated by the cross-domain admin). The HubPool itself is **not** an EIP-1967 proxy — it is a non-upgradeable `Ownable`/`Lockable` contract.
2. **The event schema migrated from address-typed "V3" events to bytes32-typed events.** The current `FundsDeposited`/`FilledRelay` (bytes32 fields, to support non-EVM chains like Solana) **completely replaced** the legacy `V3FundsDeposited`/`FilledV3Relay` (address fields) — the legacy topics emit **zero** logs today (verified). You must index the **new** topics; the legacy ones are historical only.
3. **The "real" user/recipient/depositor live in the *event data and indexed topics*, not in `tx.from`.** Deposits are routed through peripheries (`SpokePoolPeriphery`, `MulticallHandler`) and fills come from relayer bots, so `tx.to`/`tx.from` are almost never the end user. Attribute by the `depositor`/`recipient`/`relayer` event fields, and key cross-chain by `(originChainId, depositId)`.

---

## 0. Contract families & versions

| Contract | Chain(s) | Role | Proxy? |
|----------|----------|------|--------|
| **HubPool** | Ethereum only | L1 hub: LP pool, UMA-bonded root-bundle proposal/dispute/execution, owns/admins all SpokePools, holds liquidity. | **No** (non-upgradeable Ownable) |
| **SpokePool** | each spoke (ETH, Base, BNB, ARB, OP, POLY) | Per-chain deposit/fill entrypoint; emits all transfer-lifecycle events; executes relayer-refund & slow-fill leaves. | **UUPS** (ERC-1967, admin slot empty) |
| **AcrossConfigStore** | Ethereum only | Global + per-token config (rate models, transfer thresholds) read by off-chain dataworker. | No |
| **BondToken** | Ethereum only | The UMA bond token (wrapped, transfer-restricted) posted with root-bundle proposals. | No |
| **LpTokenFactory** | Ethereum only | Mints per-L1-token LP ERC20s for the HubPool. | No |
| **HubPoolStore / AdapterStore** | Ethereum only | Storage helpers for the Universal (storage-proof) adapter path and per-chain messenger/OFT config. | No |
| **PermissionSplitterProxy** | Ethereum only | Splits HubPool admin authority across roles (delegate-specific selectors to delegates). | Custom proxy |
| **chain-adapters** (`Arbitrum_Adapter`, `Optimism_Adapter`, `Polygon_Adapter`, `Base_Adapter`, `Universal_Adapter_56`, …) | Ethereum only | Per-destination L1→L2 message/token-relay adapters the HubPool delegatecalls to forward roots & admin calls. | No (libraries) |
| **SpokePoolVerifier** | all 6 spokes (shared addr) | Helper that safely forwards native-token deposits to the SpokePool. | No (immutable) |
| **MulticallHandler** | all 6 spokes (shared addr) | Destination-side handler that executes arbitrary calls with the bridged output token (composable/"bridge+swap"). | No (immutable) |
| **SpokePoolPeriphery** | all 6 spokes (shared addr) | Swap-and-bridge periphery (deposit with an input swap via the Swap API). | No (immutable) |
| **AdminWithdrawManager / WithdrawImplementation / TransferProxy** | all 6 spokes (shared addr) | Periphery/admin helpers for the Swap API. | mixed |

**Per-chain SpokePool subclasses** (`Ethereum_SpokePool`, `Arbitrum_SpokePool`, `Optimism_SpokePool`/`Ovm_SpokePool`, `Polygon_SpokePool`, `Universal_SpokePool` for BNB) differ only in their `_bridgeTokensToHubPool`/cross-domain-admin plumbing — **all inherit the same `SpokePool` base, so every event topic0 and core selector in §1–§2 is identical across all six chains** (verified live on Ethereum and Arbitrum). BNB runs the **`Universal_SpokePool`** variant whose admin messages arrive via a storage-proof light-client (`SP1Helios` on BNB + `Universal_Adapter_56` on L1), not a native canonical bridge.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 SpokePool — current (bytes32) events — INDEX THESE

Emitter = the SpokePool proxy on each chain (§3+). All verified live: `FundsDeposited` 3919 logs / `FilledRelay` 4315 logs in a 9k-block ETH window; `TokensBridged` 866 / `ExecutedRelayerRefundRoot` 1235 in a 50k ETH window; `FundsDeposited`/`FilledRelay`/`RelayedRootBundle` also confirmed on the Arbitrum SpokePool (identical topic0).

| topic0 | Event |
|--------|-------|
| `0x32ed1a409ef04c7b0227189c3a103dc5ac10e775a15b785dcc510201f7c25ad3` | `FundsDeposited(bytes32 inputToken, bytes32 outputToken, uint256 inputAmount, uint256 outputAmount, uint256 indexed destinationChainId, uint256 indexed depositId, uint32 quoteTimestamp, uint32 fillDeadline, uint32 exclusivityDeadline, bytes32 indexed depositor, bytes32 recipient, bytes32 exclusiveRelayer, bytes message)` |
| `0x44b559f101f8fbcc8a0ea43fa91a05a729a5ea6e14a7c75aa750374690137208` | `FilledRelay(bytes32 inputToken, bytes32 outputToken, uint256 inputAmount, uint256 outputAmount, uint256 repaymentChainId, uint256 indexed originChainId, uint256 indexed depositId, uint32 fillDeadline, uint32 exclusivityDeadline, bytes32 exclusiveRelayer, bytes32 indexed relayer, bytes32 depositor, bytes32 recipient, bytes32 messageHash, (bytes32,bytes32,uint256,uint8) relayExecutionInfo)` |
| `0x3cee3e290f36226751cd0b3321b213890fe9c768e922f267fa6111836ce05c32` | `RequestedSlowFill(bytes32 inputToken, bytes32 outputToken, uint256 inputAmount, uint256 outputAmount, uint256 indexed originChainId, uint256 indexed depositId, uint32 fillDeadline, uint32 exclusivityDeadline, bytes32 exclusiveRelayer, bytes32 depositor, bytes32 recipient, bytes32 messageHash)` |
| `0x45e04bc8f121ba11466985789ca2822a91109f31bb8ac85504a37b7eaf873c26` | `RequestedSpeedUpDeposit(uint256 updatedOutputAmount, uint256 indexed depositId, bytes32 indexed depositor, bytes32 updatedRecipient, bytes updatedMessage, bytes depositorSignature)` |

The `(bytes32,bytes32,uint256,uint8)` tuple in `FilledRelay` is `V3RelayExecutionEventInfo{ updatedRecipient, updatedMessageHash, updatedOutputAmount, FillType fillType }` where `FillType` is `enum{ FastFill=0, ReplacedSlowFill=1, SlowFill=2 }`. **`FundsDeposited.depositId` and `FilledRelay.depositId`/`originChainId` are the cross-chain join key.** `depositId` is `uint256` (was `uint32` in the legacy events).

### 1.2 SpokePool — relayer-refund / root-bundle / admin events

| topic0 | Event |
|--------|-------|
| `0xfa7fa7cf6d7dde5f9be65a67e6a1a747e7aa864dcd2d793353c722d80fbbb357` | `TokensBridged(uint256 amountToReturn, uint256 indexed chainId, uint32 indexed leafId, bytes32 indexed l2TokenAddress, address caller)` — funds returned from spoke to HubPool |
| `0xf4ad92585b1bc117fbdd644990adf0827bc4c95baeae8a23322af807b6d0020e` | `ExecutedRelayerRefundRoot(uint256 amountToReturn, uint256 indexed chainId, uint256[] refundAmounts, uint32 indexed rootBundleId, uint32 indexed leafId, address l2TokenAddress, address[] refundAddresses, bool deferredRefunds, address caller)` |
| `0xc86ba04c55bc5eb2f2876b91c438849a296dbec7b08751c3074d92e04f0a77af` | `RelayedRootBundle(uint32 indexed rootBundleId, bytes32 indexed relayerRefundRoot, bytes32 indexed slowRelayRoot)` |
| `0x7c1af0646963afc3343245b103731965735a893347bfa0d58a5dc77a77ae691c` | `EmergencyDeletedRootBundle(uint256 indexed rootBundleId)` |
| `0x0a21fdd43d0ad0c62689ee7230a47309a050755bcc52eba00310add65297692a` | `EnabledDepositRoute(address indexed originToken, uint256 indexed destinationChainId, bool enabled)` |
| `0xe88463c2f254e2b070013a2dc7ee1e099f9bc00534cbdf03af551dc26ae49219` | `PausedDeposits(bool isPaused)` |
| `0x2d5b62420992e5a4afce0e77742636ca2608ef58289fd2e1baa5161ef6e7e41e` | `PausedFills(bool isPaused)` |
| `0xa9e8c42c9e7fca7f62755189a16b2f5314d43d8fb24e91ba54e6d65f9314e849` | `SetXDomainAdmin(address indexed newAdmin)` |
| `0xa73e8909f8616742d7fe701153d82666f7b7cd480552e23ebb05d358c22fd04e` | `SetWithdrawalRecipient(address indexed newWithdrawalRecipient)` |
| `0x323983f5343e25b2c1396361b1b791be31484841fdfb95b8615cd02d910b1e08` | `SetOFTMessenger(address indexed token, address indexed messenger)` |
| `0x41a941b8313293eca483f41d8faa2498e005e6d7700e2e93f41d3cb7e70a897d` | `AdminExternalCallExecuted(address indexed target, bytes data)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **UUPS impl pointer changed; watch on every SpokePool proxy** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` — ERC-1967 (rarely used here, admin slot empty) |

### 1.3 SpokePool — LEGACY (address-typed "V3") events — DO NOT index for live flow (0 logs today)

Kept for historical backfills only. These were the schema before the bytes32 migration; the live SpokePool no longer emits them.

| topic0 | Event |
|--------|-------|
| `0xa123dc29aebf7d0c3322c8eeb5b999e859f39937950ed31056532713d0de396f` | `V3FundsDeposited(address inputToken, address outputToken, uint256, uint256, uint256 indexed destinationChainId, uint32 indexed depositId, uint32, uint32, uint32, address indexed depositor, address recipient, address exclusiveRelayer, bytes)` |
| `0x571749edf1d5c9599318cdbc4e28a6475d65e87fd3b2ddbe1e9a8d5e7a0f0ff7` | `FilledV3Relay(address, address, uint256, uint256, uint256, uint256 indexed originChainId, uint32 indexed depositId, uint32, uint32, address, address indexed relayer, address, address, bytes, (address,bytes,uint256,uint8))` |
| `0x923794976d026d6b119735adc163cb71decfc903e17c3dc226c00789593c04e1` | `RequestedV3SlowFill(address, address, uint256, uint256, uint256 indexed originChainId, uint32 indexed depositId, uint32, uint32, address, address, address, bytes)` |
| `0xb0a29aed3d389a1041194255878b423f7780be3ed2324d4693508c6ff189845e` | `RequestedSpeedUpV3Deposit(uint256 updatedOutputAmount, uint32 indexed depositId, address indexed depositor, address updatedRecipient, bytes, bytes)` |

### 1.4 HubPool (Ethereum only) — emitter `0xc186fA914353c44b2E33eBE05f21846F1048bEda`

All verified live: `ProposeRootBundle` 55 / `RootBundleExecuted` 995 / `LiquidityAdded` 1 in a 9k-block window.

| topic0 | Event |
|--------|-------|
| `0x3185fa6fac8e91dc65e7424a8081c73353151d2715bddb71db0982c1fe4c0fd4` | `ProposeRootBundle(uint32 challengePeriodEndTimestamp, uint8 poolRebalanceLeafCount, uint256[] bundleEvaluationBlockNumbers, bytes32 indexed poolRebalanceRoot, bytes32 indexed relayerRefundRoot, bytes32 slowRelayRoot, address indexed proposer)` |
| `0xf652dd63b1aedbf9e740f3152fb67b0d94d069cf1182811ebd88921850d93567` | `RootBundleExecuted(uint256 groupIndex, uint256 indexed leafId, uint256 indexed chainId, address[] l1Tokens, uint256[] bundleLpFees, int256[] netSendAmounts, int256[] runningBalances, address indexed caller)` |
| `0x15951cb2ef6993bc23a55912e7d0bcac13e4797c432aaa334816aed6914a7a90` | `RootBundleDisputed(address indexed disputer, uint256 requestTime)` — **a dispute is a high-severity signal** |
| `0x0cfbbf45ab7f5225663454de7117b1b0ed5a7c133b61f54ccf367dcf8b6d4d59` | `RootBundleCanceled(address indexed disputer, uint256 requestTime)` |
| `0x993cba33f9b140c9ce20ba10d7eda92128d5beb6df856f064916108a11647a73` | `EmergencyRootBundleDeleted(bytes32 indexed poolRebalanceRoot, bytes32 indexed relayerRefundRoot, bytes32 slowRelayRoot, address indexed proposer)` |
| `0x3c69701a61c79a92ef9692903aaa0068bce8771361ecb09547391e4fb4df8537` | `LiquidityAdded(address indexed l1Token, uint256 amount, uint256 lpTokensMinted, address indexed liquidityProvider)` |
| `0xcda1185f28599e6bd14ab8a68b3c30a11e1dce4256b5e67e94dd3fd846a6c589` | `LiquidityRemoved(address indexed l1Token, uint256 amount, uint256 lpTokensBurnt, address indexed liquidityProvider)` |
| `0x234e7af08f77827792cc909447f27d2e6a3e2d839b04e26b50b71704a131c8a8` | `SetPoolRebalanceRoute(uint256 indexed destinationChainId, address indexed l1Token, address indexed destinationToken)` |
| `0xb7d00a563842efb2c121a0eb02b7bb7ba1a34625bbc3d65057f1f0dbec0ec2a1` | `SetEnableDepositRoute(uint256 indexed originChainId, uint256 indexed destinationChainId, address indexed originToken, bool depositsEnabled)` |
| `0x36050d958750e6ac3aa674ac7bbe8d0ae6a2f7d4b808e8c2c42c1f22fc9fc4bb` | `CrossChainContractsSet(uint256 l2ChainId, address adapter, address spokePool)` — **maps chainId → (adapter, spokePool); use to enumerate spokes** |
| `0xbfa9a96010167e98ce8c004f718932cbbfd33a58d681c752e693be7d457a1b3b` | `BondSet(address indexed newBondToken, uint256 newBondAmount)` |
| `0x04dd1d84d387f404568a7954b5e398518bdd716e1a8f4a790be9a1a225ad9347` | `LivenessSet(uint256 newLiveness)` |
| `0xf45367c278fcceff23d601ce4bdd191e5bd61687ff9f29dc7276a08fe54c0c5d` | `IdentifierSet(bytes32 newIdentifier)` |
| `0x04e291c80180d65a57b5bf1bed775777ec0d6f283ef34bcf130712714d8bb7f7` | `L1TokenEnabledForLiquidityProvision(address l1Token, address lpToken)` |
| `0xac111b3b527b307393c94d98f26140effb71411054466818be97912d2d65f776` | `L2TokenDisabledForLiquidityProvision(address l1Token, address lpToken)` |
| `0x218987b934c2f6bc596136829fbf43a5fef4d6fafce41f3f6254d9a870c2deec` | `SpokePoolAdminFunctionTriggered(uint256 indexed chainId, bytes message)` — **cross-chain admin call dispatched to a spoke** |
| `0xc1993b89fd79a19ece7beb067ddc8534ca26d29c0ff94ea2f53b4a508d1eedc9` | `ProtocolFeeCaptureSet(address indexed newProtocolFeeCaptureAddress, uint256 indexed newProtocolFeeCapturePct)` |
| `0x74740239d7d696c84422b720e125e1f47c4138c66d1f4d2a48e99f4197cdb79c` | `ProtocolFeesCapturedClaimed(address indexed l1Token, uint256 indexed accumulatedFees)` |
| `0x0e2fb031ee032dc02d8011dc50b816eb450cf856abd8261680dac74f72165bd2` | `Paused(bool indexed isPaused)` |

### 1.5 AcrossConfigStore (Ethereum only) — `0x3B03509645713718B78951126E0A6de6f10043f5`

| topic0 | Event |
|--------|-------|
| `0x2170feb790d9bf809ba50947096322ec651593149b6f78e673e51c1c67cfe3fd` | `UpdatedTokenConfig(address indexed key, string value)` |
| `0x84c11a81ce8e8060e814e03c4606fe325e7a24ecc22ef7001254e27de3762f49` | `UpdatedGlobalConfig(bytes32 indexed key, string value)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 SpokePool — deposit / fill (state-changing)

Tuple types: `V3RelayData = (bytes32 depositor, bytes32 recipient, bytes32 exclusiveRelayer, bytes32 inputToken, bytes32 outputToken, uint256 inputAmount, uint256 outputAmount, uint256 originChainId, uint256 depositId, uint32 fillDeadline, uint32 exclusivityDeadline, bytes message)`; `V3RelayDataLegacy` = same with all `address`/`uint32 depositId`; `V3SlowFill = (V3RelayData, uint256 chainId, uint256 updatedOutputAmount)`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xad5425c6` | `deposit(bytes32,bytes32,bytes32,bytes32,uint256,uint256,uint256,bytes32,uint32,uint32,uint32,bytes)` | **Current deposit entrypoint** (depositor, recipient, inputToken, outputToken, inputAmount, outputAmount, destChainId, exclusiveRelayer, quoteTimestamp, fillDeadline, exclusivityParameter, message). Emits `FundsDeposited`. |
| `0x7b939232` | `depositV3(address,address,address,address,uint256,uint256,uint256,address,uint32,uint32,uint32,bytes)` | Legacy address-typed wrapper; internally casts to bytes32 and calls `deposit`. Still emits the **new** `FundsDeposited`. |
| `0x8b15788e` | `unsafeDeposit(bytes32,bytes32,bytes32,bytes32,uint256,uint256,uint256,bytes32,uint256 depositNonce,uint32,uint32,uint32,bytes)` | Caller-supplied nonce → deterministic "unsafe" depositId (`keccak(msg.sender,depositor,nonce)`). |
| `0xea86bd46` | `depositNow(bytes32,bytes32,bytes32,bytes32,uint256,uint256,uint256,bytes32,uint32 fillDeadlineOffset,uint32,bytes)` | Uses `getCurrentTime()` for quoteTimestamp. |
| `0xbabb6aac` | `speedUpDeposit(bytes32 depositor,uint256 depositId,uint256 updatedOutputAmount,bytes32 updatedRecipient,bytes,bytes depositorSignature)` | Emits `RequestedSpeedUpDeposit`. |
| `0x4e0fb8f5` | `speedUpV3Deposit(address,uint32,uint256,address,bytes,bytes)` | Legacy speed-up. |
| `0xdeff4b24` | `fillRelay((...)V3RelayData,uint256 repaymentChainId,bytes32 repaymentAddress)` | **Current fill entrypoint.** Emits `FilledRelay`. |
| `0x2e378115` | `fillV3Relay((...)V3RelayDataLegacy,uint256 repaymentChainId)` | Legacy address-typed fill. |
| `0x97943aa9` | `fillRelayWithUpdatedDeposit((...)V3RelayData,uint256,bytes32,uint256 updatedOutputAmount,bytes32 updatedRecipient,bytes,bytes depositorSignature)` | Fill honoring a speed-up. |
| `0x2e63e59a` | `requestSlowFill((...)V3RelayData)` | Emits `RequestedSlowFill`. |
| `0x1fab657c` | `executeSlowRelayLeaf((...)V3SlowFill,uint32 rootBundleId,bytes32[] proof)` | Pays out a slow fill from a settled root. |
| `0x1b3d5559` | `executeRelayerRefundLeaf(uint32 rootBundleId,(uint256,uint256,uint256[],uint32,address,address[]) relayerRefundLeaf,bytes32[] proof)` | **Disburses relayer refunds; emits `ExecutedRelayerRefundRoot` (+`TokensBridged` when returning to HubPool).** |
| `0x493a4f84` | `relayRootBundle(bytes32 relayerRefundRoot,bytes32 slowRelayRoot)` | Admin-only; emits `RelayedRootBundle`. |
| `0x8a7860ce` | `emergencyDeleteRootBundle(uint256 rootBundleId)` | Admin-only. |
| `0xde7eba78` | `setCrossDomainAdmin(address)` | Admin-only; emits `SetXDomainAdmin`. |
| `0xfc8a584f` | `setWithdrawalRecipient(address)` | Admin-only. |
| `0x738b62e5` | `pauseDeposits(bool)` | Emits `PausedDeposits`. |
| `0x99cc2968` | `pauseFills(bool)` | Emits `PausedFills`. |

### 2.2 SpokePool — views (verified present in live ETH impl bytecode via `eth_call`)

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x5285e058` | `crossDomainAdmin()` | `address` — the cross-domain admin (returns HubPool `0xc186fA91…` on Ethereum; the canonical-bridge alias on L2s). |
| `0x17fcb39b` | `wrappedNativeToken()` | `address` — wrapped native (WETH on ETH `0xC02a…56Cc2`). |
| `0xa1244c67` | `numberOfDeposits()` | `uint256` — monotonically increasing deposit counter (next `depositId`). |
| `0x29cb924d` | `getCurrentTime()` | `uint256` — block timestamp (Ethereum_SpokePool inherits a settable timer for tests). |
| `0x9a8a0592` | `chainId()` | `uint256` — the spoke's own chain id. |
| `0x57f6dcb8` | `depositQuoteTimeBuffer()` | `uint32` (3600 on ETH). |
| `0x079bd2c7` | `fillDeadlineBuffer()` | `uint32` (21600 on ETH). |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | UUPS upgrade entrypoint; emits `Upgraded`. Auth = cross-domain admin. |
| `0x52d1902d` | `proxiableUUID()` | `bytes32` = the EIP-1967 impl slot (reverts through the proxy — itself a UUPS tell). |

### 2.3 HubPool (Ethereum only)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8bda0c00` | `proposeRootBundle(uint256[] bundleEvaluationBlockNumbers,uint8 poolRebalanceLeafCount,bytes32 poolRebalanceRoot,bytes32 relayerRefundRoot,bytes32 slowRelayRoot)` | Posts a UMA-bonded root bundle; emits `ProposeRootBundle`. |
| `0x80c09a82` | `executeRootBundle(uint256 chainId,uint256 groupIndex,uint256[] bundleLpFees,int256[] netSendAmounts,int256[] runningBalances,uint8 leafId,address[] l1Tokens,bytes32[] proof)` | Executes a pool-rebalance leaf post-liveness; emits `RootBundleExecuted`. |
| `0x22395aaa` | `disputeRootBundle()` | Bonds a dispute → UMA; emits `RootBundleDisputed`. **High-severity.** |
| `0xe460e35c` | `setCrossChainContracts(uint256 l2ChainId,address adapter,address spokePool)` | Registers a spoke; emits `CrossChainContractsSet`. |
| `0x10b99527` | `setPoolRebalanceRoute(uint256 destinationChainId,address l1Token,address destinationToken)` | Emits `SetPoolRebalanceRoute`. |
| `0x33dc09ca` | `setBond(address newBondToken,uint256 newBondAmount)` | Emits `BondSet`. |
| `0x56688700` | `addLiquidity(address l1Token,uint256 l1TokenAmount)` | LP deposit; emits `LiquidityAdded`. |
| `0x0ee28a88` | `removeLiquidity(address l1Token,uint256 lpTokenAmount,bool sendEth)` | Emits `LiquidityRemoved`. |
| `0xb60c2d7d` | `enableL1TokenForLiquidityProvision(address l1Token)` | Mints an LP token via LpTokenFactory. |
| `0xdd70e5e8` | `relaySpokePoolAdminFunction(uint256 chainId,bytes functionData)` | Forwards an admin call to a spoke; emits `SpokePoolAdminFunctionTriggered`. |
| `0xe0f339e3` | `exchangeRateCurrent(address l1Token)` | LP exchange rate (accrues fees). |
| `0xa5841194` | `sync(address l1Token)` | Pulls utilized liquidity / updates accounting. |
| `0x26205d80` | `haircutReserves(address l1Token,int256 haircutAmount)` | Owner-only reserve adjustment. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Ethereum is the **only** chain with the HubPool and the L1-hub contracts. Wiring confirmed live: `SpokePool.crossDomainAdmin()` → HubPool; `HubPool.owner()` = `0xb524735356985d2f267fa010d681f061dff03715`.

### 3.1 Core hub & L1 contracts

| Role | Address | One-liner |
|------|---------|-----------|
| **HubPool** | `0xc186fA914353c44b2E33eBE05f21846F1048bEda` | L1 hub; LP pool + UMA root-bundle settlement; owns/admins all spokes. ~19.5 kB, **not a proxy**. |
| **Ethereum SpokePool** (proxy) | `0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5` | The L1 spoke (deposits *from* Ethereum). UUPS, impl `0x5e5b726c81f43b953a62ad87e2835c85c4d9dd3b`. |
| **AcrossConfigStore** | `0x3B03509645713718B78951126E0A6de6f10043f5` | Global/per-token config (rate models, thresholds). |
| **BondToken** | `0xee1DC6BCF1Ee967a350e9aC6CaaAA236109002ea` | UMA proposal bond token. |
| **LpTokenFactory** | `0x7dB69eb9F52eD773E9b03f5068A1ea0275b2fD9d` | Mints per-L1-token LP ERC20s. |
| **HubPoolStore** | `0x1Ace3BbD69b63063F859514Eca29C9BDd8310E61` | Storage helper for the Universal (storage-proof) adapter path. |
| **AdapterStore** | `0x42df4D71f35ffBD28ae217d52E83C1DA0007D63b` | Per-chain messenger/OFT messenger registry. |
| **PermissionSplitterProxy** | `0x0Bf07B2e415F02711fFBB32491f8ec9e5489B2e7` | Splits HubPool admin authority across delegate roles. |
| AcrossMerkleDistributor | `0xE50b2cEAC4f60E840Ae513924033E753e2366487` | ACX/airdrop & referral-reward distributor. |
| HubPool owner (Across DAO Safe/Timelock) | `0xb524735356985d2f267fa010d681f061dff03715` | `owner()` of HubPool **and** AcrossConfigStore. |

### 3.2 L1 chain-adapters (delegatecall targets used by HubPool to message each spoke)

| Destination | Adapter | Destination | Adapter |
|---|---|---|---|
| Arbitrum | `0xc0b6d2f794cc787C71f2cA5ceCD57102C32379B3` | Optimism | `0x3562e309C6C79626E5F0Cf746FB5Bf4f6b8EebE5` |
| Polygon | `0x537abE038C223066B50312474409924487D2E655` | Base | `0x799BDC55d91864b14B2eD63A34DeF5d502AA897f` |
| Ethereum (self) | `0x527E872a5c3f0C7c24Fe33F2593cFB890a285084` | Linea | `0x5A44A32c13e2C43416bFDE5dDF5DCb3880c42787` |
| zkSync Era | `0xA374585E6062517Ee367ee5044946A6fBe17724f` | Blast | `0xF2bEf5E905AAE0295003ab14872F811E914EdD81` |
| Scroll | `0x2DA799c2223c6ffB595e578903AE6b95839160d8` | Mode | `0xf1B59868697f3925b72889ede818B9E7ba0316d0` |
| Lisk | `0xF039AdCC74936F90fE175e8b3FE0FdC8b8E0c73b` | Zora | `0x024F2fC31CBDD8de17194b1892c834f98Ef5169b` |
| World Chain | `0xA8399e221a583A57F54Abb5bA22f31b5D6C09f32` | Solana | `0x9F788694934fD2Ed34D5340B9a76EB34f2bFD7B3` |
| **Universal_Adapter_56 (→ BNB)** | `0x6f1C9d3bcDF51316E7b515a62C02F601500b084b` | Lens | `0x5e0B7e20a77BDf11812837D30F1326068Bcf24Cf` |

> **BNB is reached via the `Universal_Adapter_56` (storage-proof / SP1Helios light client), not a native bridge adapter** — and there is **no `Avalanche_Adapter`** in the HubPool deployment, consistent with Avalanche having no SpokePool. PolygonTokenBridger `0x0330E9b4D0325cCfF515E81DFbc7754F2a02ac57` (also deployed on Polygon) handles the Polygon PoS token-bridge two-step.

### 3.3 Periphery / handlers on Ethereum (shared deterministic addresses — see §4)

| Role | Address |
|------|---------|
| SpokePoolVerifier | `0x3Fb9cED51E968594C87963a371Ed90c39519f65A` |
| MulticallHandler | `0x0F7Ae28dE1C8532170AD4ee566B5801485c13a0E` |
| SpokePoolPeriphery (current) | `0x10D8b8DaA26d307489803e10477De69C0492B610` |
| SpokePoolPeriphery (legacy, still deployed) | `0x767e4c20F521a829dE4Ffc40C25176676878147f` |
| AdminWithdrawManager | `0xe7de86ECD99918384FcbA79EaeF23eFAAF10e43E` |
| MulticallHandler (CCTP/permissioned) | `0x64a43393866DBA0044879979fAa7AD3d000622e9` |

---

## 4. Addresses — the five other live spoke chains

Each spoke has **one SpokePool proxy at a chain-unique address** plus the **shared deterministic** periphery/handler cluster (same literal address on all six chains, deployed via deterministic factory). All verified via `eth_getCode` on each chain's publicnode RPC on 2026-06-09; impls read from the EIP-1967 slot.

### 4.1 Per-chain SpokePool proxies (unique addresses, no shared vanity)

| Chain | ID | SpokePool (proxy) | Live impl (EIP-1967) | Variant |
|-------|----|--------------------|----------------------|---------|
| Ethereum | 1 | `0x5c7BCd6E7De5423a257D81B442095A1a6ced35C5` | `0x5e5b726c81f43b953a62ad87e2835c85c4d9dd3b` | Ethereum_SpokePool |
| Base | 8453 | `0x09aea4b2242abC8bb4BB78D537A67a245A7bEC64` | `0x77aa19d49484cc88c2ca1c8527226e891c5c72d8` | Ovm_SpokePool (OP-stack) |
| BNB | 56 | `0x4e8E101924eDE233C13e2D8622DC8aED2872d505` | `0xe8ff2a3d5cc19ddcbd93328371e1dd8995e7afaa` | **Universal_SpokePool** (storage-proof admin) |
| Arbitrum One | 42161 | `0xe35e9842fceaCA96570B734083f4a58e8F7C5f2A` | `0xae54d52223c34e4102927516900cc3c562afe02e` | Arbitrum_SpokePool |
| Optimism | 10 | `0x6f26Bf09B1C792e3228e5467807a900A503c0281` | `0x0966f5034261cc50926fb9d5c1603a5034ffa81c` | Ovm_SpokePool (OP-stack) |
| Polygon PoS | 137 | `0x9295ee1d8C5b022Be115A2AD3c30C72E34e7F096` | `0x4a84a43274f5f99e94aa0ebef53bc06af8bc3dfb` | Polygon_SpokePool |

`crossDomainAdmin()` returns the HubPool `0xc186fA914353c44b2E33eBE05f21846F1048bEda` on all six (on L2s this is the L1 admin whose messages arrive via the canonical bridge / storage proof).

### 4.2 Shared deterministic infra (identical literal address on ALL six spoke chains)

| Role | Address (same on ETH/Base/BNB/ARB/OP/POLY) | Present on Avalanche? |
|------|---------------------------------------------|------------------------|
| SpokePoolVerifier | `0x3Fb9cED51E968594C87963a371Ed90c39519f65A` | **No (0x)** |
| MulticallHandler | `0x0F7Ae28dE1C8532170AD4ee566B5801485c13a0E` | **No (0x)** |
| SpokePoolPeriphery | `0x10D8b8DaA26d307489803e10477De69C0492B610` | **No (0x)** |
| AdminWithdrawManager | `0xe7de86ECD99918384FcbA79EaeF23eFAAF10e43E` | **No (0x)** |
| WithdrawImplementation | `0x679D43e1d304001538Bf083D421484fD67c00a45` | **No (0x)** |
| TransferProxy | `0x03743372098Aa51E1fCe537D51025F08b55C4144` | **No (0x)** |

Polygon also carries `PolygonTokenBridger 0x0330E9b4D0325cCfF515E81DFbc7754F2a02ac57` (same address as on L1) and `MintableERC1155 0xA15a90E7936A2F8B70E181E955760860D133e56B`. BNB also carries `SP1Helios 0x19256DCEa4B63c56B3EFc8708cd62F595B2d1922` (the storage-proof light client that authenticates L1 admin messages for the Universal spoke).

### 4.3 Avalanche C-Chain (chain ID 43114) — **NO Across deployment**

Verified `eth_getCode = 0x` on `https://avalanche-c-chain-rpc.publicnode.com` for the HubPool, the SpokePoolVerifier/MulticallHandler shared addresses, and the Ethereum SpokePool literal. Avalanche appears in `across-protocol/constants` `MAINNET_CHAIN_IDs` (43114) as a *known* chain, but it has **no `avalanche` deployment directory** in the contracts repo, **no entry** in `broadcast/deployed-addresses.json` or `legacy-addresses.json`, and **no `Avalanche_Adapter`** registered on the HubPool. **Across does not bridge to/from Avalanche C-Chain as of 2026-06-09.**

---

## 5. Cross-chain summary

| Chain | ID | SpokePool | HubPool | Verifier/MulticallHandler/Periphery | Other |
|-------|----|-----------|---------|--------------------------------------|-------|
| Ethereum | 1 | ✅ `0x5c7B…35C5` | ✅ `0xc186…BEda` | ✅ shared cluster | ConfigStore, BondToken, LpTokenFactory, all L1 adapters |
| Base | 8453 | ✅ `0x09ae…EC64` | ❌ | ✅ shared cluster | — |
| BNB | 56 | ✅ `0x4e8E…d505` | ❌ | ✅ shared cluster | SP1Helios (storage-proof) |
| Arbitrum One | 42161 | ✅ `0xe35e…5f2A` | ❌ | ✅ shared cluster | — |
| Optimism | 10 | ✅ `0x6f26…0281` | ❌ | ✅ shared cluster | — |
| Polygon PoS | 137 | ✅ `0x9295…F096` | ❌ | ✅ shared cluster | PolygonTokenBridger, MintableERC1155 |
| **Avalanche** | 43114 | ❌ `0x` | ❌ | ❌ `0x` | **nothing — not a connected chain** |

**Counterparty chains OUTSIDE the seven** (registered on the HubPool / have spokes, per `setCrossChainContracts` + L1 adapters): zkSync Era (324), Linea, Blast (81457), Scroll, Mode, Lisk, Zora, World Chain, Lens, Boba, Ink, Cher, Soneium, Plasma, HyperEVM, Monad, **Solana** (non-EVM — the very reason for the bytes32 event migration), and others. Record these as findings: Across is a ~25+-chain bridge; only six of the seven requested chains carry a SpokePool, and the seventh (Avalanche) carries none.

**No shared vanity** among SpokePools — each chain's proxy is a distinct address (unlike the periphery cluster). Always key SpokePool detection on `(chainId, address)`.

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **SpokePool** (all 6 chains) | **UUPS** (ERC-1967 + ERC-1822) | EIP-1967 impl slot `0x360894…bbc` **populated** (per-chain impl, §4.1); admin slot `0xb53127…6103` **empty**; impl exposes `upgradeToAndCall(0x4f1ef286)` + `proxiableUUID(0x52d1902d)`; `Upgraded(address)` topic `0xbc7cd75a…`. | cross-domain admin (the HubPool's message via the chain's canonical bridge / SP1Helios for BNB). |
| **HubPool** | **Not a proxy** (immutable `Ownable`/`Lockable`) | EIP-1967 impl slot returns `0x0` (confirmed live); ~19.5 kB full bytecode. Upgrades = redeploy + `setCrossChainContracts`. | `owner()` = DAO Safe/Timelock `0xb524…3715`. |
| AcrossConfigStore / BondToken / LpTokenFactory / HubPoolStore / AdapterStore | Not proxies | impl slot `0x0`; full bytecode. | `owner()` (ConfigStore/HubPool share owner). |
| **SpokePoolVerifier / MulticallHandler / SpokePoolPeriphery / WithdrawImplementation / TransferProxy** | Immutable (no proxy) | impl slot `0x0`; deployed deterministically (same address all six chains). | none (immutable). |
| PermissionSplitterProxy | Custom permission-splitting proxy | routes selectors to per-role delegates; not a standard EIP-1967 logic proxy. | HubPool owner. |

EIP-1967 slots: impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`, admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. **Watch `Upgraded(address)` `0xbc7cd75a…` on every SpokePool proxy** — the impls in §4.1 are point-in-time; always read the live slot.

---

## 7. Detection invariants & gotchas

1. **Index the NEW bytes32 events, never the legacy V3 ones.** `FundsDeposited` (`0x32ed1a40…`) and `FilledRelay` (`0x44b559f1…`) are the live workhorses (thousands of logs / 9k blocks). The legacy `V3FundsDeposited` (`0xa123dc29…`) and `FilledV3Relay` (`0x571749ed…`) emit **zero** logs today — they are historical only. A monitor keyed on the V3 topics will see nothing.
2. **Cross-chain join key = `(originChainId, depositId)`.** A bridge transfer = `FundsDeposited` on the origin SpokePool (`destinationChainId`, `depositId`) → `FilledRelay` on the destination SpokePool (`originChainId`, `depositId`). `depositId` is now `uint256` (legacy was `uint32`); `numberOfDeposits()` is the origin's counter. `unsafeDeposit` produces a hashed (non-sequential) `depositId`.
3. **The depositor/recipient/relayer live in event fields, not `tx.from`/`tx.to`.** Deposits arrive via `SpokePoolPeriphery`/`SpokePoolVerifier`/`MulticallHandler`/aggregators; fills come from relayer bot EOAs. Attribute by `FundsDeposited.depositor`/`recipient` and `FilledRelay.relayer`. The fields are bytes32 (left-padded EVM addresses on EVM chains; full 32-byte for Solana/SVM recipients).
4. **A "fill" is not a settlement.** `FilledRelay` means a relayer fronted the funds on the destination; the relayer is only reimbursed later when the HubPool's `RootBundleExecuted` + the spoke's `ExecutedRelayerRefundRoot`/`TokensBridged` clear. Don't treat fill ≠ refund. Relayer risk lives between fill and refund.
5. **`FilledRelay.fillType` (the `uint8` in the trailing tuple) distinguishes FastFill(0) / ReplacedSlowFill(1) / SlowFill(2).** A `SlowFill` is the protocol-paid fallback (via `executeSlowRelayLeaf`) when no relayer filled; a `RequestedSlowFill` precedes it.
6. **HubPool `RootBundleDisputed` / `RootBundleCanceled` / `EmergencyRootBundleDeleted` are the highest-severity signals.** A dispute bonds against the UMA optimistic oracle and pauses settlement — monitor these on `0xc186…BEda`. `Paused(true)` (`0x0e2fb031…`) halts the hub.
7. **`SpokePoolAdminFunctionTriggered` (HubPool) → admin message dispatched to a spoke; `SetXDomainAdmin`/`Upgraded`/`PausedDeposits`/`PausedFills` (SpokePool) are the spoke-side admin events.** A SpokePool `Upgraded` is a UUPS impl swap — treat as a privileged change.
8. **Avalanche is genuinely absent.** Every Across address returns `0x` on chain 43114 and there is no `Avalanche_Adapter`. Don't infer an Avalanche spoke from the chain appearing in the SDK's chain-id enum.
9. **BNB is the odd spoke out: `Universal_SpokePool` + storage-proof admin.** Its admin messages are authenticated by `SP1Helios` (`0x19256DCE…` on BNB) against the `Universal_Adapter_56` + `HubPoolStore` on L1, not a native canonical bridge. The deposit/fill event schema is still identical.
10. **`TokensBridged` exists in two schemas; only the bytes32 one (`0xfa7fa7cf…`, l2TokenAddress as bytes32) is live.** An older `TokensBridged(uint256,uint256,uint32,address,address)` (`0x828fc203…`) is historical. Same migration story as the deposit/fill events.
11. **Periphery cluster shares one literal address across all six chains** (`SpokePoolVerifier 0x3Fb9cED5…`, `MulticallHandler 0x0F7Ae28d…`, `SpokePoolPeriphery 0x10D8b8Da…`). The **SpokePools do not** — key SpokePool monitoring on `(chainId, address)`, and don't assume the periphery address implies a spoke at the same address.
12. **Two SpokePoolPeriphery addresses are live on each chain** (`0x10D8b8Da…` current and `0x767e4c20…` legacy). The current `deployed-addresses.json` points to `0x10D8b8Da…`; both have bytecode. Index both if back-filling Swap-API flow.
13. **`message` payloads drive composability.** A non-empty `FundsDeposited.message`/`FilledRelay.messageHash` means the fill triggers a downstream call via `MulticallHandler` (bridge+swap / cross-chain action). The bridged token may immediately move again inside the same tx.
14. **HubPool is the registry.** To enumerate the current spoke set + adapters, read `CrossChainContractsSet` history (`0x36050d95…`) or `crossChainContracts(chainId)` — don't hard-code; new spokes are added by governance.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== SpokePool topics (current bytes32 schema — chain-agnostic) =====
TOPIC_FUNDS_DEPOSITED            = '\x32ed1a409ef04c7b0227189c3a103dc5ac10e775a15b785dcc510201f7c25ad3'
TOPIC_FILLED_RELAY               = '\x44b559f101f8fbcc8a0ea43fa91a05a729a5ea6e14a7c75aa750374690137208'
TOPIC_REQUESTED_SLOW_FILL        = '\x3cee3e290f36226751cd0b3321b213890fe9c768e922f267fa6111836ce05c32'
TOPIC_REQUESTED_SPEEDUP_DEPOSIT  = '\x45e04bc8f121ba11466985789ca2822a91109f31bb8ac85504a37b7eaf873c26'
TOPIC_TOKENS_BRIDGED             = '\xfa7fa7cf6d7dde5f9be65a67e6a1a747e7aa864dcd2d793353c722d80fbbb357'
TOPIC_EXECUTED_REFUND_ROOT       = '\xf4ad92585b1bc117fbdd644990adf0827bc4c95baeae8a23322af807b6d0020e'
TOPIC_RELAYED_ROOT_BUNDLE        = '\xc86ba04c55bc5eb2f2876b91c438849a296dbec7b08751c3074d92e04f0a77af'
TOPIC_EMERGENCY_DELETED_BUNDLE   = '\x7c1af0646963afc3343245b103731965735a893347bfa0d58a5dc77a77ae691c'
TOPIC_ENABLED_DEPOSIT_ROUTE      = '\x0a21fdd43d0ad0c62689ee7230a47309a050755bcc52eba00310add65297692a'
TOPIC_PAUSED_DEPOSITS            = '\xe88463c2f254e2b070013a2dc7ee1e099f9bc00534cbdf03af551dc26ae49219'
TOPIC_PAUSED_FILLS               = '\x2d5b62420992e5a4afce0e77742636ca2608ef58289fd2e1baa5161ef6e7e41e'
TOPIC_SET_XDOMAIN_ADMIN          = '\xa9e8c42c9e7fca7f62755189a16b2f5314d43d8fb24e91ba54e6d65f9314e849'
TOPIC_SET_WITHDRAWAL_RECIPIENT   = '\xa73e8909f8616742d7fe701153d82666f7b7cd480552e23ebb05d358c22fd04e'
TOPIC_SET_OFT_MESSENGER          = '\x323983f5343e25b2c1396361b1b791be31484841fdfb95b8615cd02d910b1e08'
TOPIC_ADMIN_EXTERNAL_CALL        = '\x41a941b8313293eca483f41d8faa2498e005e6d7700e2e93f41d3cb7e70a897d'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- legacy SpokePool topics (historical only — 0 logs today) --
TOPIC_V3_FUNDS_DEPOSITED         = '\xa123dc29aebf7d0c3322c8eeb5b999e859f39937950ed31056532713d0de396f'
TOPIC_FILLED_V3_RELAY            = '\x571749edf1d5c9599318cdbc4e28a6475d65e87fd3b2ddbe1e9a8d5e7a0f0ff7'
TOPIC_REQUESTED_V3_SLOW_FILL     = '\x923794976d026d6b119735adc163cb71decfc903e17c3dc226c00789593c04e1'
TOPIC_REQ_SPEEDUP_V3_DEPOSIT     = '\xb0a29aed3d389a1041194255878b423f7780be3ed2324d4693508c6ff189845e'

-- ===== HubPool topics (Ethereum only) =====
TOPIC_PROPOSE_ROOT_BUNDLE        = '\x3185fa6fac8e91dc65e7424a8081c73353151d2715bddb71db0982c1fe4c0fd4'
TOPIC_ROOT_BUNDLE_EXECUTED       = '\xf652dd63b1aedbf9e740f3152fb67b0d94d069cf1182811ebd88921850d93567'
TOPIC_ROOT_BUNDLE_DISPUTED       = '\x15951cb2ef6993bc23a55912e7d0bcac13e4797c432aaa334816aed6914a7a90'
TOPIC_ROOT_BUNDLE_CANCELED       = '\x0cfbbf45ab7f5225663454de7117b1b0ed5a7c133b61f54ccf367dcf8b6d4d59'
TOPIC_EMERGENCY_ROOT_DELETED     = '\x993cba33f9b140c9ce20ba10d7eda92128d5beb6df856f064916108a11647a73'
TOPIC_LIQUIDITY_ADDED            = '\x3c69701a61c79a92ef9692903aaa0068bce8771361ecb09547391e4fb4df8537'
TOPIC_LIQUIDITY_REMOVED          = '\xcda1185f28599e6bd14ab8a68b3c30a11e1dce4256b5e67e94dd3fd846a6c589'
TOPIC_SET_POOL_REBALANCE_ROUTE   = '\x234e7af08f77827792cc909447f27d2e6a3e2d839b04e26b50b71704a131c8a8'
TOPIC_CROSSCHAIN_CONTRACTS_SET   = '\x36050d958750e6ac3aa674ac7bbe8d0ae6a2f7d4b808e8c2c42c1f22fc9fc4bb'
TOPIC_SPOKE_ADMIN_FN_TRIGGERED   = '\x218987b934c2f6bc596136829fbf43a5fef4d6fafce41f3f6254d9a870c2deec'
TOPIC_BOND_SET                   = '\xbfa9a96010167e98ce8c004f718932cbbfd33a58d681c752e693be7d457a1b3b'
TOPIC_HUBPOOL_PAUSED             = '\x0e2fb031ee032dc02d8011dc50b816eb450cf856abd8261680dac74f72165bd2'
-- ConfigStore --
TOPIC_UPDATED_TOKEN_CONFIG       = '\x2170feb790d9bf809ba50947096322ec651593149b6f78e673e51c1c67cfe3fd'
TOPIC_UPDATED_GLOBAL_CONFIG      = '\x84c11a81ce8e8060e814e03c4606fe325e7a24ecc22ef7001254e27de3762f49'

-- ===== Selectors =====
-- SpokePool deposit/fill
SEL_DEPOSIT                      = '\xad5425c6'
SEL_DEPOSIT_V3                   = '\x7b939232'
SEL_UNSAFE_DEPOSIT               = '\x8b15788e'
SEL_DEPOSIT_NOW                  = '\xea86bd46'
SEL_SPEEDUP_DEPOSIT              = '\xbabb6aac'
SEL_FILL_RELAY                   = '\xdeff4b24'
SEL_FILL_V3_RELAY                = '\x2e378115'
SEL_FILL_RELAY_UPDATED_DEPOSIT   = '\x97943aa9'
SEL_REQUEST_SLOW_FILL            = '\x2e63e59a'
SEL_EXECUTE_SLOW_RELAY_LEAF      = '\x1fab657c'
SEL_EXECUTE_REFUND_LEAF          = '\x1b3d5559'
SEL_RELAY_ROOT_BUNDLE            = '\x493a4f84'
SEL_EMERGENCY_DELETE_ROOT_BUNDLE = '\x8a7860ce'
SEL_SET_CROSS_DOMAIN_ADMIN       = '\xde7eba78'
SEL_PAUSE_DEPOSITS               = '\x738b62e5'
SEL_PAUSE_FILLS                  = '\x99cc2968'
SEL_NUMBER_OF_DEPOSITS           = '\xa1244c67'
SEL_CROSS_DOMAIN_ADMIN           = '\x5285e058'
SEL_UPGRADE_TO_AND_CALL          = '\x4f1ef286'
SEL_PROXIABLE_UUID               = '\x52d1902d'
-- HubPool
SEL_PROPOSE_ROOT_BUNDLE          = '\x8bda0c00'
SEL_EXECUTE_ROOT_BUNDLE          = '\x80c09a82'
SEL_DISPUTE_ROOT_BUNDLE          = '\x22395aaa'
SEL_SET_CROSSCHAIN_CONTRACTS     = '\xe460e35c'
SEL_SET_POOL_REBALANCE_ROUTE     = '\x10b99527'
SEL_SET_BOND                     = '\x33dc09ca'
SEL_ADD_LIQUIDITY                = '\x56688700'
SEL_REMOVE_LIQUIDITY             = '\x0ee28a88'
SEL_RELAY_SPOKE_ADMIN_FN         = '\xdd70e5e8'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT                = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT               = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Ethereum (chain ID 1) — hub + L1 contracts =====
ETH_HUBPOOL                      = '\xc186fa914353c44b2e33ebe05f21846f1048beda'
ETH_SPOKEPOOL                    = '\x5c7bcd6e7de5423a257d81b442095a1a6ced35c5'
ETH_SPOKEPOOL_IMPL               = '\x5e5b726c81f43b953a62ad87e2835c85c4d9dd3b'
ETH_CONFIG_STORE                 = '\x3b03509645713718b78951126e0a6de6f10043f5'
ETH_BOND_TOKEN                   = '\xee1dc6bcf1ee967a350e9ac6caaaa236109002ea'
ETH_LP_TOKEN_FACTORY             = '\x7db69eb9f52ed773e9b03f5068a1ea0275b2fd9d'
ETH_HUBPOOL_STORE                = '\x1ace3bbd69b63063f859514eca29c9bdd8310e61'
ETH_ADAPTER_STORE                = '\x42df4d71f35ffbd28ae217d52e83c1da0007d63b'
ETH_PERMISSION_SPLITTER          = '\x0bf07b2e415f02711ffbb32491f8ec9e5489b2e7'
ETH_HUBPOOL_OWNER                = '\xb524735356985d2f267fa010d681f061dff03715'

-- ===== Per-chain SpokePool proxies (UNIQUE per chain — no shared vanity) =====
BASE_SPOKEPOOL                   = '\x09aea4b2242abc8bb4bb78d537a67a245a7bec64'   -- impl 0x77aa19d4…
BNB_SPOKEPOOL                    = '\x4e8e101924ede233c13e2d8622dc8aed2872d505'   -- impl 0xe8ff2a3d… (Universal)
ARB_SPOKEPOOL                    = '\xe35e9842fceaca96570b734083f4a58e8f7c5f2a'   -- impl 0xae54d522…
OP_SPOKEPOOL                     = '\x6f26bf09b1c792e3228e5467807a900a503c0281'   -- impl 0x0966f503…
POLY_SPOKEPOOL                   = '\x9295ee1d8c5b022be115a2ad3c30c72e34e7f096'   -- impl 0x4a84a432…

-- ===== Shared deterministic infra (SAME address on all 6 spoke chains; 0x on Avalanche) =====
ACROSS_SPOKEPOOL_VERIFIER        = '\x3fb9ced51e968594c87963a371ed90c39519f65a'
ACROSS_MULTICALL_HANDLER         = '\x0f7ae28de1c8532170ad4ee566b5801485c13a0e'
ACROSS_SPOKEPOOL_PERIPHERY       = '\x10d8b8daa26d307489803e10477de69c0492b610'
ACROSS_SPOKEPOOL_PERIPHERY_LEGACY= '\x767e4c20f521a829de4ffc40c25176676878147f'
-- BNB storage-proof light client:
BNB_SP1_HELIOS                   = '\x19256dcea4b63c56b3efc8708cd62f595b2d1922'
-- Avalanche (43114): NO Across contracts — every address above returns 0x
```

---

## 9. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` (no param names, `uint`→`uint256`, structs as `(type,…)`, `enum`→`uint8`, dynamic arrays `type[]`) from the canonical Solidity. Struct encodings taken verbatim from `contracts/interfaces/V3SpokePoolInterface.sol` (`V3RelayData`, `V3RelayDataLegacy`, `V3SlowFill`, `V3RelayExecutionEventInfo`, `FillType`) and `contracts/interfaces/SpokePoolInterface.sol` (`RelayerRefundLeaf`). Cross-checked against **live `eth_getLogs`**: on the Ethereum SpokePool (`0x5c7B…35C5`, ~block 25,279,247) `FundsDeposited` `0x32ed1a40…` = 3919 logs and `FilledRelay` `0x44b559f1…` = 4315 logs in a 9k-block window, `TokensBridged` `0xfa7fa7cf…` = 866 and `ExecutedRelayerRefundRoot` `0xf4ad9258…` = 1235 in a 50k window; on the Arbitrum SpokePool (`0xe35e…5f2A`) `FundsDeposited`/`FilledRelay`/`RelayedRootBundle` all confirmed with the same topic0; on the HubPool (`0xc186…BEda`) `ProposeRootBundle` `0x3185fa6f…` = 55, `RootBundleExecuted` `0xf652dd63…` = 995, `LiquidityAdded` `0x3c69701a…` = 1. The legacy `V3FundsDeposited`/`FilledV3Relay` topics returned **0** logs — confirming the bytes32 migration. SpokePool view selectors (`numberOfDeposits 0xa1244c67`, `crossDomainAdmin 0x5285e058`, `wrappedNativeToken 0x17fcb39b`, `getCurrentTime 0x29cb924d`, `chainId 0x9a8a0592`) confirmed dispatchable via `eth_call`.
- **Addresses:** parsed from `across-protocol/contracts` `broadcast/deployed-addresses.json` (current source of truth) and `deployments/legacy-addresses.json`, then existence-checked via `eth_getCode` on each chain's publicnode RPC. All six SpokePools = 680-byte ERC-1967 proxy bytecode; HubPool = ~19.5 kB non-proxy; periphery cluster present at one shared address on all six spokes. Avalanche: `eth_getCode = 0x` for HubPool, the shared infra addresses, and the ETH SpokePool literal — no `avalanche` directory, no deployed-addresses entry, no `Avalanche_Adapter`.
- **Proxy classification:** EIP-1967 impl slot read live per chain (populated, distinct impl per chain — §4.1); admin slot read live = empty on every SpokePool → UUPS (auth in impl, gated by cross-domain admin). HubPool impl slot = `0x0` → not a proxy. `crossDomainAdmin()` = HubPool on all six; `HubPool.owner()` / `ConfigStore.owner()` = `0xb524…3715`.
- **Chain coverage:** the seven requested chains each probed for the SpokePool, HubPool, and shared infra; counterparty chains outside the seven enumerated from the L1 chain-adapters list + `MAINNET_CHAIN_IDs`.

Authoritative sources:
- Canonical repo — [across-protocol/contracts](https://github.com/across-protocol/contracts) (`broadcast/deployed-addresses.json`, `deployments/legacy-addresses.json`, `contracts/spoke-pools/SpokePool.sol`, `contracts/hub-pool/HubPool.sol`, `contracts/interfaces/V3SpokePoolInterface.sol`, `contracts/interfaces/SpokePoolInterface.sol`)
- [across-protocol/constants](https://github.com/across-protocol/constants) (`src/networks.ts` — `MAINNET_CHAIN_IDs`)
- Docs — [Across contract addresses](https://docs.across.to/reference/contract-addresses) · [Ethereum addresses](https://docs.across.to/reference/contract-addresses/mainnet-chain-id-1)
- Explorers — [Etherscan HubPool](https://etherscan.io/address/0xc186fa914353c44b2e33ebe05f21846f1048beda) · [Etherscan SpokePool](https://etherscan.io/address/0x5c7bcd6e7de5423a257d81b442095a1a6ced35c5) · [Arbiscan SpokePool](https://arbiscan.io/address/0xe35e9842fceaca96570b734083f4a58e8f7c5f2a) · [Basescan SpokePool](https://basescan.org/address/0x09aea4b2242abc8bb4bb78d537a67a245a7bec64)
