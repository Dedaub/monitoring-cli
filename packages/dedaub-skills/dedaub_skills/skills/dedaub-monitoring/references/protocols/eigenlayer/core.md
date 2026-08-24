# EigenLayer Core (restaking) — Topics, Selectors, Addresses (Ethereum mainnet)

**Status:** verified 2026-06-09 against Ethereum mainnet via `eth_getLogs` / `eth_getCode` / `eth_getStorageAt` / `eth_call` on `https://ethereum-rpc.publicnode.com`, the canonical `Layr-Labs/eigenlayer-contracts` source (`src/contracts/interfaces/*` on `main`) + its `script/configs/mainnet/mainnet-addresses.config.json` (lastUpdated `v1.4.1-mainnet-prooftra`, semver `v1.4.1`), and keccak-256 computed locally + cross-checked against live logs.
**Scope:** **EigenLayer's restaking core is deployed only on Ethereum mainnet (chain ID 1).** All of DelegationManager, StrategyManager, EigenPodManager, AVSDirectory, RewardsCoordinator, AllocationManager, PermissionController, the strategies and the EIGEN/bEIGEN tokens are Ethereum-only — **none of these contracts has any code on Base, BNB, Avalanche, Arbitrum, Optimism or Polygon** (all `eth_getCode → 0x`, verified §6). Event `topic0` and function `selector` values are **chain-agnostic** (the same wherever a contract were deployed); addresses below are Ethereum-specific.

**What EigenLayer is.** A restaking layer. Stakers deposit either (a) LSTs into per-collateral **Strategy** contracts via **StrategyManager**, or (b) native ETH by pointing validator withdrawal credentials at an **EigenPod** tracked by **EigenPodManager**. Stakers then **delegate** their restaked shares to an **operator** (DelegationManager). Operators opt into **AVSs** (Actively Validated Services) and, since the 2025 slashing release ("ELIP-002"), allocate slashable magnitude to **operator sets** via **AllocationManager**; misbehaving operators are slashed (`OperatorSlashed`). **RewardsCoordinator** distributes AVS rewards via weekly Merkle roots. **PermissionController** is the new account-abstraction-style admin/appointee layer.

**The non-obvious things an indexer must know:**
1. **The deposit event is the 3-arg `Deposit(address staker, address strategy, uint256 shares)` (`0x5548c837…`)** — the legacy 4-arg form is dead. Note `0x5548c837…` **collides** with the well-known `Deposit(address,address,uint256)` topic0 used by ve(3,3) gauges/Velodrome — disambiguate by emitter (StrategyManager `0x8586…`).
2. **Withdrawals now emit `SlashingWithdrawalQueued`/`SlashingWithdrawalCompleted`, NOT the legacy `WithdrawalQueued`/`WithdrawalCompleted`** — the legacy topics return 0 live. The post-slashing release replaced them.
3. **`OperatorRegistered` is 2-arg `(address operator, address delegationApprover)` (`0xa453db…`)** — an earlier struct form (`OperatorRegistered(address,(address,address,uint32))`) is NOT what the live contract emits.
4. **Each EigenPod is a BeaconProxy** (EIP-1967 beacon slot → `eigenPodBeacon`), one per pod owner, deployed by EigenPodManager; pod events emit from the **pod address**, not the manager.
5. **Pre-deployed LST strategies are TransparentUpgradeableProxy** (EIP-1967 impl + shared `ProxyAdmin`), NOT beacon proxies — only **factory-deployed** strategies (via `StrategyFactory`) are beacon proxies behind a separate beacon.
6. **EIGEN is a wrapped token over bEIGEN** (`EIGEN.bEIGEN()` → `0x83E9…`). EIGEN had transfer restrictions (`setAllowedFrom/To`) at launch; both are ERC-20 + ERC20Votes.

---

## 0. Contract families & versions

| Family | Contracts | Role |
|--------|-----------|------|
| **Delegation & shares** | DelegationManager, StrategyManager, EigenPodManager | Who restaked what, who they delegate to, queue/complete withdrawals |
| **Strategies** | per-collateral Strategy proxies (stETH, rETH, cbETH, …), `beaconChainETHStrategy` sentinel, eigenStrategy (bEIGEN), StrategyFactory + StrategyBeacon | Hold LST deposits; convert tokens↔shares |
| **Native ETH** | EigenPodManager, EigenPod beacon + impl, per-owner EigenPod (BeaconProxy) | Native-ETH restaking via beacon-chain proofs / checkpoints |
| **AVS & slashing (ELIP-002, 2025)** | AVSDirectory (legacy M2 registration), AllocationManager (operator sets + magnitude + slashing), PermissionController | AVS opt-in, slashable allocations, admin/appointee |
| **Rewards** | RewardsCoordinator | Weekly Merkle distribution of AVS rewards |
| **Legacy / inert** | Slasher (deployed, **never used** — slashing is via AllocationManager), DelayedWithdrawalRouter (pre-checkpoint native-ETH withdrawals), eigenLayerPauserReg | |
| **Tokens** | EIGEN (proxy), bEIGEN (backing, proxy) | Governance / restakable token |

**Version note.** Two functional eras coexist in the topic set. **Pre-slashing**: `WithdrawalQueued`/`WithdrawalCompleted`, M2 AVS registration via `AVSDirectory.OperatorAVSRegistrationStatusUpdated`. **Slashing (ELIP-002, live since 2025)**: `SlashingWithdrawalQueued`/`Completed`, operator sets + `AllocationManager`/`OperatorSlashed`, `PermissionController`, EigenPod checkpoint proofs keyed by **`bytes32 pubkeyHash`** (older EigenPod code used `uint40 validatorIndex`). Always prefer the slashing-era topics; the legacy ones are dormant.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

`topic0` is unaffected by `indexed`. **✓** = observed verbatim in live mainnet logs this session; **src** = keccak of the verbatim canonical signature, not log-seen in sampled ranges (rare/admin).

### 1.1 DelegationManager (`0x3905…F37A`) — delegation, shares, withdrawals
| topic0 | Event | ✓ |
|--------|-------|---|
| `0xa453db612af59e5521d6ab9284dc3e2d06af286eb1b1b7b771fce4716c19f2c1` | `OperatorRegistered(address indexed operator, address delegationApprover)` | ✓ |
| `0x773b54c04d756fcc5e678111f7d730de3be98192000799eee3d63716055a87c6` | `DelegationApproverUpdated(address indexed operator, address newDelegationApprover)` | src |
| `0x02a919ed0e2acad1dd90f17ef2fa4ae5462ee1339170034a8531cca4b6708090` | `OperatorMetadataURIUpdated(address indexed operator, string metadataURI)` | src |
| `0xc3ee9f2e5fda98e8066a1f745b2df9285f416fe98cf2559cd21484b3d8743304` | `StakerDelegated(address indexed staker, address indexed operator)` | ✓ |
| `0xfee30966a256b71e14bc0ebfc94315e28ef4a97a7131a9e2b7a310a73af44676` | `StakerUndelegated(address indexed staker, address indexed operator)` | ✓ |
| `0xf0eddf07e6ea14f388b47e1e94a0f464ecbd9eed4171130e0fc0e99fb4030a8a` | `StakerForceUndelegated(address indexed staker, address indexed operator)` | src |
| `0x1ec042c965e2edd7107b51188ee0f383e22e76179041ab3a9d18ff151405166c` | `OperatorSharesIncreased(address indexed operator, address staker, address strategy, uint256 shares)` | ✓ |
| `0x6909600037b75d7b4733aedd815442b5ec018a827751c832aaff64eba5d6d2dd` | `OperatorSharesDecreased(address indexed operator, address staker, address strategy, uint256 shares)` | ✓ |
| `0x8be932bac54561f27260f95463d9b8ab37e06b2842e5ee2404157cc13df6eb8f` | `DepositScalingFactorUpdated(address staker, address strategy, uint256 newDepositScalingFactor)` | ✓ |
| `0x26b2aae26516e8719ef50ea2f6831a2efbd4e37dccdf0f6936b27bc08e793e30` | `SlashingWithdrawalQueued(bytes32 withdrawalRoot, Withdrawal withdrawal, uint256[] sharesToWithdraw)` | ✓ |
| `0x1f40400889274ed07b24845e5054a87a0cab969eb1277aafe61ae352e7c32a00` | `SlashingWithdrawalCompleted(bytes32 withdrawalRoot)` | ✓ |
| `0xdd611f4ef63f4385f1756c86ce1f1f389a9013ba6fa07daba8528291bc2d3c30` | `OperatorSharesSlashed(address indexed operator, address strategy, uint256 totalSlashedShares)` | src |

`Withdrawal` tuple = `(address staker, address delegatedTo, address withdrawer, uint256 nonce, uint32 startBlock, address[] strategies, uint256[] scaledShares)`.

> **Legacy (dormant, do not key on):** `WithdrawalQueued(bytes32,(…))` = `0x9009ab153e8014fbfb02f2217f5cde7aa7f9ad734ae85ca3ee3f4ca2fdd499f9` and `WithdrawalCompleted(bytes32)` = `0xc97098c2f658800b4df29001527f7324bcdffcf6e8751a699ab920a1eced5b1d` returned **0** live — replaced by the Slashing* forms above.

### 1.2 StrategyManager (`0x8586…075A`) — LST deposits
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62` | `Deposit(address staker, address strategy, uint256 shares)` | ✓ |
| `0x4264275e593955ff9d6146a51a4525f6ddace2e81db9391abcc9d1ca48047d29` | `StrategyWhitelisterChanged(address previousAddress, address newAddress)` | src |
| `0x0c35b17d91c96eb2751cd456e1252f42a386e524ef9ff26ecc9950859fdc04fe` | `StrategyAddedToDepositWhitelist(address strategy)` | src |
| `0x4074413b4b443e4e58019f2855a8765113358c7c72e39509c6af45fc0f5ba030` | `StrategyRemovedFromDepositWhitelist(address strategy)` | src |
| `0x5f5209798bbac45a16d2dc3bc67319fab26ee00153916d6f07b69f8a134a1e8b` | `BurnOrRedistributableSharesIncreased((address,uint32) operatorSet, uint256 slashId, address strategy, uint256 shares)` | src |
| `0xe6413aa0c789e437b0a06bf64b20926584f066c79a2d8b80a759c85472f7b0af` | `BurnOrRedistributableSharesDecreased((address,uint32) operatorSet, uint256 slashId, address strategy, uint256 shares)` | src |
| `0xd9d082c3ec4f3a3ffa55c324939a06407f5fbcb87d5e0ce3b9508c92c84ed839` | `BurnableSharesDecreased(address strategy, uint256 shares)` (pre-redistribution slash path) | src |

> **`Deposit` = the LST stake.** topic0 `0x5548c837…` is shared with `Deposit(address,address,uint256)` emitted by ve(3,3) gauges (Velodrome/Aerodrome/Topaz) — **disambiguate by the StrategyManager emitter**. The 4-arg `Deposit(address,address,address,uint256)` (`0x7cfff908…`) is the **old** form and returns 0 live.

### 1.3 EigenPodManager (`0x91E6…A338`) — native-ETH shares
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x21c99d0db02213c32fff5b05cf0a718ab5f858802b91498f80d82270289d856a` | `PodDeployed(address indexed eigenPod, address indexed podOwner)` | ✓ |
| `0x35a85cabc603f48abb2b71d9fbd8adea7c449d7f0be900ae7a2986ea369c3d0d` | `BeaconChainETHDeposited(address indexed podOwner, uint256 amount)` | src |
| `0x4e2b791dedccd9fb30141b088cabf5c14a8912b52f59375c95c010700b8c6193` | `PodSharesUpdated(address indexed podOwner, int256 sharesDelta)` | ✓ |
| `0xd4def76d6d2bed6f14d5cd9af73cc2913d618d00edde42432e81c09bfe077098` | `NewTotalShares(address indexed podOwner, int256 newTotalShares)` | src |
| `0xa6bab1d55a361fcea2eee2bc9491e4f01e6cf333df03c9c4f2c144466429f7d6` | `BeaconChainETHWithdrawalCompleted(address indexed podOwner, uint256 shares, uint96 nonce, address delegatedAddress, address withdrawer, bytes32 withdrawalRoot)` | src |
| `0xb160ab8589bf47dc04ea11b50d46678d21590cea2ed3e454e7bd3e41510f98cf` | `BeaconChainSlashingFactorDecreased(address staker, uint64 prevBeaconChainSlashingFactor, uint64 newBeaconChainSlashingFactor)` | src |
| `0x1ed04b7fd262c0d9e50fa02957f32a81a151f03baaa367faeedc7521b001c4a4` | `BurnableETHSharesIncreased(uint256 shares)` | src |

### 1.4 EigenPod (logic = `eigenPodImplementation`; emitted by each per-owner pod BeaconProxy)
| topic0 | Event | ✓ |
|--------|-------|---|
| `0xa01003766d3cd97cf2ade5429690bf5d206be7fb01ef9d3a0089ecf67bc11219` | `EigenPodStaked(bytes32 pubkeyHash)` | src |
| `0x101790c2993f6a4d962bd17c786126823ba1c4cf04ff4cccb2659d50fb20aee8` | `ValidatorRestaked(bytes32 pubkeyHash)` | src |
| `0xcdae700d7241bc027168c53cf6f889763b0a2c88a65d77fc13a8a9fef0d8605f` | `ValidatorBalanceUpdated(bytes32 pubkeyHash, uint64 balanceTimestamp, uint64 newValidatorBalanceGwei)` | src |
| `0x575796133bbed337e5b39aa49a30dc2556a91e0c6c2af4b7b886ae77ebef1076` | `CheckpointCreated(uint64 indexed checkpointTimestamp, bytes32 indexed beaconBlockRoot, uint256 validatorCount)` | src |
| `0x525408c201bc1576eb44116f6478f1c2a54775b19a043bcfdc708364f74f8e44` | `CheckpointFinalized(uint64 indexed checkpointTimestamp, int256 totalShareDeltaWei)` | src |
| `0xe4866335761a51dcaff766448ab0af6064291ee5dc94e68492bb9cd757c1e350` | `ValidatorCheckpointed(uint64 indexed checkpointTimestamp, bytes32 indexed pubkeyHash)` | src |
| `0x5ce0aa04ae51d52da6e680fbe0336d2e2432f7c3dc2d4f3193204c57b9072107` | `ValidatorWithdrawn(uint64 indexed checkpointTimestamp, bytes32 indexed pubkeyHash)` | src |
| `0x8947fd2ce07ef9cc302c4e8f0461015615d91ce851564839e91cc804c2f49d8e` | `RestakedBeaconChainETHWithdrawn(address indexed recipient, uint256 amount)` | src |
| `0x6fdd3dbdb173299608c0aa9f368735857c8842b581f8389238bf05bd04b3bf49` | `NonBeaconChainETHReceived(uint256 amountReceived)` | src |
| `0xfb8129080a19d34dceac04ba253fc50304dc86c729bd63cdca4a969ad19a5eac` | `ProofSubmitterUpdated(address prevProofSubmitter, address newProofSubmitter)` | src |
| `0xc97b965b92ae7fd20095fe8eb7b99f81f95f8c4adffb22a19116d8eb2846b016` | `SwitchToCompoundingRequested(bytes32 indexed validatorPubkeyHash)` (Pectra) | src |
| `0x42f9c9db2ca443e9ec62f4588bd0c9b241065c02c2a8001ac164ae1282dc7b94` | `ConsolidationRequested(bytes32 indexed sourcePubkeyHash, bytes32 indexed targetPubkeyHash)` (Pectra) | src |
| `0x60d8ca014d4765a2b8b389e25714cb1cef83b574222911a01d90c1bd69d2d320` | `ExitRequested(bytes32 indexed validatorPubkeyHash)` (Pectra) | src |
| `0x8b2737bb64ab2f2dc09552dfa1c250399e6a42c7ea9f0e1c658f5d65d708ec05` | `WithdrawalRequested(bytes32 indexed validatorPubkeyHash, uint64 withdrawalAmountGwei)` (Pectra) | src |

> **Current EigenPod keys validator events by `bytes32 pubkeyHash`** (older code used `uint40 validatorIndex` → different topic0s). Each pod also emits proxy `Initialized` (`0x7f26…`) + `BeaconUpgraded` (`0x1cf3…`) at deploy (live-confirmed).

### 1.5 AVSDirectory (`0x135D…F5AF`) — legacy M2 AVS registration
| topic0 | Event | ✓ |
|--------|-------|---|
| `0xf0952b1c65271d819d39983d2abb044b9cace59bcc4d4dd389f586ebdcb15b41` | `OperatorAVSRegistrationStatusUpdated(address indexed operator, address indexed avs, uint8 status)` (status: 0=UNREGISTERED,1=REGISTERED) | ✓ |
| `0xa89c1dc243d8908a96dd84944bcc97d6bc6ac00dd78e20621576be6a3c943713` | `AVSMetadataURIUpdated(address indexed avs, string metadataURI)` | src |

> AVSDirectory is the **pre-slashing (M2)** AVS opt-in surface; new AVS integration uses operator sets on **AllocationManager** (§1.6). Both remain live.

### 1.6 AllocationManager (`0x948a…bc39`) — operator sets, magnitude, slashing (ELIP-002)
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x31629285ead2335ae0933f86ed2ae63321f7af77b4e6eaabc42c057880977e6c` | `OperatorSetCreated((address avs,uint32 id) operatorSet)` | ✓ |
| `0x43232edf9071753d2321e5fa7e018363ee248e5f2142e6c08edd3265bfb4895e` | `OperatorAddedToOperatorSet(address indexed operator, (address,uint32) operatorSet)` | ✓ |
| `0xad34c3070be1dffbcaa499d000ba2b8d9848aefcac3059df245dd95c4ece14fe` | `OperatorRemovedFromOperatorSet(address indexed operator, (address,uint32) operatorSet)` | src |
| `0x7ab260fe0af193db5f4986770d831bda4ea46099dc817e8b6716dcae8af8e88b` | `StrategyAddedToOperatorSet((address,uint32) operatorSet, address strategy)` | src |
| `0x7b4b073d80dcac55a11177d8459ad9f664ceeb91f71f27167bb14f8152a7eeee` | `StrategyRemovedFromOperatorSet((address,uint32) operatorSet, address strategy)` | src |
| `0x1487af5418c47ee5ea45ef4a93398668120890774a9e13487e61e9dc3baf76dd` | `AllocationUpdated(address operator, (address,uint32) operatorSet, address strategy, uint64 magnitude, uint32 effectBlock)` | ✓ |
| `0xacf9095feb3a370c9cf692421c69ef320d4db5c66e6a7d29c7694eb02364fc55` | `EncumberedMagnitudeUpdated(address operator, address strategy, uint64 encumberedMagnitude)` | ✓ |
| `0x1c6458079a41077d003c11faf9bf097e693bd67979e4e6500bac7b29db779b5c` | `MaxMagnitudeUpdated(address operator, address strategy, uint64 maxMagnitude)` | src |
| `0x80969ad29428d6797ee7aad084f9e4a42a82fc506dcd2ca3b6fb431f85ccebe5` | `OperatorSlashed(address operator, (address,uint32) operatorSet, address[] strategies, uint256[] wadSlashed, string description)` | ✓ |
| `0x4e85751d6331506c6c62335f207eb31f12a61e570f34f5c17640308785c6d4db` | `AllocationDelaySet(address operator, uint32 delay, uint32 effectBlock)` | src |
| `0x2ae945c40c44dc0ec263f95609c3fdc6952e0aefa22d6374e44f2c997acedf85` | `AVSRegistrarSet(address avs, address registrar)` | src |
| `0x3873f29d7a65a4d75f5ba28909172f486216a1420e77c3c2720815951a6b4f57` | `SlasherUpdated((address,uint32) operatorSet, address slasher, uint32 effectBlock)` | src |
| `0xf0c8fc7d71f647bd3a88ac369112517f6a4b8038e71913f2d20f71f877dfc725` | `SlasherMigrated((address,uint32) operatorSet, address slasher)` | src |
| `0x90a6fa2a9b79b910872ebca540cf3bd8be827f586e6420c30d8836e30012907e` | `RedistributionAddressSet((address,uint32) operatorSet, address redistributionRecipient)` | src |
| `0x1bb5d701d48020629535b7da25feae994ff1d548db8e212f71ce058272fe11b5` | `RedistributionOperatorSetCreated((address,uint32) operatorSet, address redistributionRecipient)` | src |

> **`OperatorSlashed` (`0x8096…`) is the slashing event** — log-confirmed live (rare). `OperatorSetCreated`, `OperatorAddedToOperatorSet`, `AllocationUpdated`, `EncumberedMagnitudeUpdated` all live-confirmed.

### 1.7 RewardsCoordinator (`0x7750…adda`) — AVS rewards
`RewardsSubmission` tuple = `((address strategy,uint96 multiplier)[] strategiesAndMultipliers, address token, uint256 amount, uint32 startTimestamp, uint32 duration)`.

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x450a367a380c4e339e5ae7340c8464ef27af7781ad9945cfe8abd828f89e6281` | `AVSRewardsSubmissionCreated(address indexed avs, uint256 indexed submissionNonce, bytes32 indexed rewardsSubmissionHash, RewardsSubmission rewardsSubmission)` | ✓ |
| `0x51088b8c89628df3a8174002c2a034d0152fce6af8415d651b2a4734bf270482` | `RewardsSubmissionForAllCreated(address indexed submitter, uint256 indexed submissionNonce, bytes32 indexed rewardsSubmissionHash, RewardsSubmission rewardsSubmission)` | src |
| `0x5251b6fdefcb5d81144e735f69ea4c695fd43b0289ca53dc075033f5fc80068b` | `RewardsSubmissionForAllEarnersCreated(address indexed tokenHopper, uint256 indexed submissionNonce, bytes32 indexed rewardsSubmissionHash, RewardsSubmission rewardsSubmission)` | src |
| `0xfc8888bffd711da60bc5092b33f677d81896fe80ecc677b84cfab8184462b6e0` | `OperatorDirectedAVSRewardsSubmissionCreated(address indexed caller, address indexed avs, bytes32 indexed operatorDirectedRewardsSubmissionHash, uint256 submissionNonce, OperatorDirectedRewardsSubmission submission)` | ✓ |
| `0xecd866c3c158fa00bf34d803d5f6023000b57080bcb48af004c2b4b46b3afd08` | `DistributionRootSubmitted(uint32 indexed rootIndex, bytes32 indexed root, uint32 indexed rewardsCalculationEndTimestamp, uint32 activatedAt)` (≈ weekly) | ✓ |
| `0xd850e6e5dfa497b72661fa73df2923464eaed9dc2ff1d3cb82bccbfeabe5c41e` | `DistributionRootDisabled(uint32 indexed rootIndex)` | src |
| `0x9543dbd55580842586a951f0386e24d68a5df99ae29e3b216588b45fd684ce31` | `RewardsClaimed(bytes32 root, address indexed earner, address indexed claimer, address indexed recipient, address token, uint256 claimedAmount)` | ✓ |
| `0xbab947934d42e0ad206f25c9cab18b5bb6ae144acfb00f40b4e3aa59590ca312` | `ClaimerForSet(address indexed earner, address indexed oldClaimer, address indexed claimer)` | src |
| `0xaf557c6c02c208794817a705609cfa935f827312a1adfdd26494b6b95dd2b4b3` | `ActivationDelaySet(uint32 oldActivationDelay, uint32 newActivationDelay)` | src |
| `0x237b82f438d75fc568ebab484b75b01d9287b9e98b490b7c23221623b6705dbb` | `RewardsUpdaterSet(address indexed oldRewardsUpdater, address indexed newRewardsUpdater)` | src |

`OperatorDirectedRewardsSubmission` tuple = `((address,uint96)[] strategiesAndMultipliers, address token, (address operator,uint256 amount)[] operatorRewards, uint32 startTimestamp, uint32 duration, string description)`.

> **`RewardsClaimed` is the 6-arg form (`0x9543dbd5…`)** — the 5-arg/`PaymentClaimed` legacy forms are absent. `DistributionRootSubmitted` fires roughly weekly.

### 1.8 PermissionController (`0x25E5…f0E5`) — admin/appointee layer
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x037f03a2ad6b967df4a01779b6d2b4c85950df83925d9e31362b519422fc0169` | `AppointeeSet(address indexed account, address indexed appointee, address target, bytes4 selector)` | src |
| `0x18242326b6b862126970679759169f01f646bd55ec5bfcab85ba9f337a74e0c6` | `AppointeeRemoved(address indexed account, address indexed appointee, address target, bytes4 selector)` | src |
| `0xbf265e8326285a2747e33e54d5945f7111f2b5edb826eb8c08d4677779b3ff97` | `AdminSet(address indexed account, address indexed admin)` | src |
| `0xb14b9a3d448c5b04f0e5b087b6f5193390db7955482a6ffb841e7b3ba61a460c` | `PendingAdminAdded(address indexed account, address admin)` | src |
| `0xd706ed7ae044d795b49e54c9f519f663053951011985f663a862cd9ee72a9ac7` | `PendingAdminRemoved(address indexed account, address admin)` | src |
| `0xdb9d5d31320daf5bc7181d565b6da4d12e30f0f4d5aa324a992426c14a1d19ce` | `AdminRemoved(address indexed account, address admin)` | src |

### 1.9 Strategy (`StrategyBase` / `StrategyBaseTVLLimits`) — one per collateral
| topic0 | Event | ✓ |
|--------|-------|---|
| `0xd2494f3479e5da49d386657c292c610b5b01df313d07c62eb0cfa49924a31be8` | `ExchangeRateEmitted(uint256 rate)` | src |
| `0x1c540707b00eb5427b6b774fc799d756516a54aee108b64b327acc55af557507` | `StrategyTokenSet(address token, uint8 decimals)` | src |

### 1.10 Tokens — EIGEN / bEIGEN (ERC-20 + ERC20Votes)
| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address,address,uint256)` |

> ERC20Votes also emits `DelegateChanged`/`DelegateVotesChanged`/`DelegateVotesChanged` (standard OZ topic0s). EIGEN is a wrapper over bEIGEN — wrap/unwrap moves bEIGEN via its `Transfer` and mints/burns EIGEN.

### 1.11 Common proxy / lifecycle topics (TransparentUpgradeableProxy + Pausable)
| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **the impl-swap watch event** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |
| `0x1cf3b03a6cf19fa2baba4df148e9dcabedea7f8a5c07840e207e5c089be95d3e` | `BeaconUpgraded(address indexed beacon)` (EigenPods, factory strategies) |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` |
| `0xab40a374bc51de372200a8bc981af8c9ecdc08dfdaef0bb6e09f88f3c616ef3d` | `Paused(address indexed account, uint256 newPausedStatus)` |
| `0x3582d1828e26bf56bd801502bc021ac0bc8afb57c826e4986b45593c8fad389c` | `Unpaused(address indexed account, uint256 newPausedStatus)` |

---

## 2. Function signatures (chain-agnostic — `selector = keccak256(signature)[0:4]`)

**bytecode** = confirmed present in the live deployed implementation (PUSH4 scan; proxies resolved to impl first).

### 2.1 DelegationManager
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2aa6d888` | `registerAsOperator(address initDelegationApprover, uint32 allocationDelay, string metadataURI)` | bytecode |
| `0x54b7c96c` | `modifyOperatorDetails(address operator, address newDelegationApprover)` | bytecode |
| `0xeea9064b` | `delegateTo(address operator, (bytes signature,uint256 expiry) approverSignatureAndExpiry, bytes32 approverSalt)` | bytecode — **delegate** |
| `0xda8be864` | `undelegate(address staker)` | bytecode — queues full withdrawal |
| `0x0dd8dd02` | `queueWithdrawals((address[] strategies,uint256[] depositShares,address __deprecated_withdrawer)[] params)` | bytecode |
| `0xe4cc3f90` | `completeQueuedWithdrawal((…) withdrawal, address[] tokens, bool receiveAsTokens)` | bytecode |
| `0x90041347` | `getOperatorShares(address operator, address[] strategies)` → `uint256[]` | bytecode |
| `0x778e55f3` | `operatorShares(address operator, address strategy)` → `uint256` | bytecode |

### 2.2 StrategyManager
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe7a050aa` | `depositIntoStrategy(address strategy, address token, uint256 amount)` → `uint256 shares` | bytecode — **LST deposit** |
| `0x32e89ace` | `depositIntoStrategyWithSignature(address strategy, address token, uint256 amount, address staker, uint256 expiry, bytes signature)` | bytecode |
| `0xfe243a17` | `stakerDepositShares(address user, address strategy)` → `uint256` | bytecode |
| `0x663c1de4` | `strategyIsWhitelistedForDeposit(address strategy)` → `bool` | bytecode |
| `0x5de08ff2` | `addStrategiesToDepositWhitelist(address[] strategies)` | bytecode |

### 2.3 EigenPodManager / EigenPod
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x84d81062` | `createPod()` → `address pod` | EPM bytecode — deploys the BeaconProxy |
| `0x9b4e4634` | `stake(bytes pubkey, bytes signature, bytes32 depositDataRoot)` (payable) | EPM bytecode — native-ETH deposit |
| `0xa38406a3` | `getPod(address podOwner)` → `address` | EPM bytecode |
| `0x9ba06275` | `ownerToPod(address podOwner)` → `address` | EPM bytecode |
| `0xd48e8894` | `podOwnerDepositShares(address podOwner)` → `int256` | EPM bytecode |
| `0x88676cad` | `startCheckpoint(bool revertIfNoBalance)` | EigenPod — begins a checkpoint proof |
| `0x3f65cf19` | `verifyWithdrawalCredentials(uint64 beaconTimestamp, (bytes32,bytes) stateRootProof, uint40[] validatorIndices, bytes[] proofs, bytes32[][] validatorFields)` | EigenPod |

### 2.4 AVSDirectory
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9926ee7d` | `registerOperatorToAVS(address operator, (bytes signature,bytes32 salt,uint256 expiry) operatorSignature)` | bytecode (M2) |
| `0xa98fb355` | `updateAVSMetadataURI(string metadataURI)` | bytecode |

### 2.5 AllocationManager (ELIP-002)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x36352057` | `slashOperator(address avs, (address operator,uint32 operatorSetId,address[] strategies,uint256[] wadsToSlash,string description) params)` | bytecode — **slash** |
| `0x952899ee` | `modifyAllocations(address operator, ((address,uint32) operatorSet,address[] strategies,uint64[] newMagnitudes)[] params)` | bytecode |
| `0x261f84e0` | `createOperatorSets(address avs, (uint32 operatorSetId,address[] strategies)[] params)` | bytecode (live V1 form; the `…,address slasher` V2 form `0x3dff8e7d` is NOT yet in impl) |
| `0xadc2e3d9` | `registerForOperatorSets(address operator, (address avs,uint32[] operatorSetIds,bytes data) params)` | bytecode |

### 2.6 RewardsCoordinator
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfce36c7d` | `createAVSRewardsSubmission(((address,uint96)[],address,uint256,uint32,uint32)[] rewardsSubmissions)` | bytecode |
| `0x3441f481` | *(absent)* `processClaim((uint32,uint32,bytes,(uint8,bytes32),uint32,(address,uint256)[],bytes,bytes),address)` | **NOT live** — superseded |
| `0x3ccc861d` | `processClaim((uint32 rootIndex,uint32 earnerIndex,bytes earnerTreeProof,(address earner,bytes32 earnerTokenRoot) earnerLeaf,uint32[] tokenIndices,bytes[] tokenTreeProofs,(address token,uint256 cumulativeEarnings)[] tokenLeaves) claim, address recipient)` | bytecode — **claim rewards** |
| `0x3efe1db6` | `submitRoot(bytes32 root, uint32 rewardsCalculationEndTimestamp)` | bytecode |

### 2.7 PermissionController
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x950d806e` | `setAppointee(address account, address appointee, address target, bytes4 selector)` | bytecode |
| `0xdf595cb8` | `canCall(address account, address caller, address target, bytes4 selector)` → `bool` | bytecode |
| `0xeb5a4e87` | `addPendingAdmin(address account, address admin)` | bytecode |

### 2.8 Strategy (StrategyBase) & Tokens
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2495a599` | `underlyingToken()` → `address` | Strategy bytecode |
| `0x3a98ef39` | `totalShares()` → `uint256` | Strategy bytecode |
| `0x7a8b2637` | `sharesToUnderlyingView(uint256 shares)` → `uint256` | Strategy bytecode |
| `0x553ca5f8` | `userUnderlyingView(address user)` → `uint256` | Strategy bytecode |
| `0xea598cb0` | `wrap(uint256 amount)` | EIGEN — bEIGEN → EIGEN (same selector as Lido wstETH `wrap`) |
| `0xde0e9a3e` | `unwrap(uint256 amount)` | EIGEN — EIGEN → bEIGEN |
| `0x3f4da4c6` | `bEIGEN()` → `address` | EIGEN — returns backing token `0x83E9…` (live-confirmed) |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All addresses below hold code (verified `eth_getCode`). Source = `Layr-Labs/eigenlayer-contracts` `script/configs/mainnet/mainnet-addresses.config.json` (`v1.4.1`), each cross-checked on-chain. Deployment block of core = `22434239`. **Proxy legend:** `TUP` = TransparentUpgradeableProxy (EIP-1967 impl + `eigenLayerProxyAdmin`); `Beacon` = UpgradeableBeacon target; `BeaconProxy` = per-instance beacon proxy; `—` = non-proxy.

### 3.1 Core managers (all TransparentUpgradeableProxy → `eigenLayerProxyAdmin 0x8b95…2444`)
| Role | Proxy | Live impl | One-liner |
|------|-------|-----------|-----------|
| **DelegationManager** | `0x39053D51B77DC0d36036Fc1fCc8Cb819df8Ef37A` | `0xe7022a128acd4c6cad7aff6fa874d61f984bce75` | Delegation + operators + slashing-era withdrawals; §1.1 |
| **StrategyManager** | `0x858646372CC42E1A627fcE94aa7A7033e7CF075A` | `0x88582996b70fdd7c4f16e3fde7b53858fce0d394` | LST deposits → shares; §1.2 |
| **EigenPodManager** | `0x91E677b07F7AF907ec9a428aafA9fc14a0d3A338` | `0xd22dd829779adbf3869fb224f703452f7f95e9db` | Native-ETH restaking shares; deploys EigenPods; §1.3 |
| **AVSDirectory** | `0x135DDa560e946695d6f155dACaFC6f1F25C1F5AF` | `0xcd35cef328b496fa9d70a8d7c34ef3434614862b` | Legacy M2 AVS registration; §1.5 |
| **AllocationManager** | `0x948a420b8CC1d6BFd0B6087C2E7c344a2CD0bc39` | `0xda2a68d318a571dd550f2ecbcb09bf50497e97c4` | Operator sets + magnitude + slashing (ELIP-002); §1.6 |
| **RewardsCoordinator** | `0x7750d328b314EfFa365A0402CcfD489B80B0adda` | `0xa0673c53980665a706352412d2538ba005403c26` | Weekly Merkle AVS rewards; §1.7 |
| **PermissionController** | `0x25E5F8B1E7aDf44518d35D5B2271f114e081f0E5` | `0x36dd260abf606172875e6b5b7a96b435dc74eed2` | Admin/appointee ACL; §1.8 |
| **Slasher** (legacy, inert) | `0xD92145c07f8Ed1D392c1B88017934E301CC1c3Cd` | `0xf3234220163a757edf1e11a8a085638d9b236614` | Deployed but **never used** — slashing is via AllocationManager |
| DelayedWithdrawalRouter (legacy) | `0x7Fe7E9CC0F274d2435AD5d56D5fa73E47F6A23D8` | `0x4bb6731b02314d40abbffbc4540f508874014226` | Pre-checkpoint native-ETH withdrawal router |

### 3.2 EigenPod system
| Role | Address | Pattern | One-liner |
|------|---------|---------|-----------|
| **eigenPodBeacon** | `0x5a2a4F2F3C18f09179B6703e63D9eDD165909073` | UpgradeableBeacon | `implementation()` → `0x53cc2d82e08370fe1e44a96f69cec7d5b54ae868` (live) |
| **eigenPodImplementation** | `0xe2E2dB234b0FFB9AFe41e52dB7d3c2B8585646c3` | — (logic; config snapshot) | EigenPod logic — live beacon impl drifts (read beacon) |
| *(per owner)* EigenPod | *deterministic, via `getPod(owner)`* | **BeaconProxy** → eigenPodBeacon | One per pod owner; emits §1.4 from its own address |
| beaconOracle | `0x343907185b71aDF0eBa9567538314396aa985442` | — | Beacon-chain block-root oracle (EIP-4788 reads) |

### 3.3 Strategies (one per LST; all TransparentUpgradeableProxy → `eigenLayerProxyAdmin`)
12 pre-deployed LST strategies + the EIGEN strategy. `baseStrategyImplementation` = `0x0EC17ef9c00F360DB28CA8008684a4796b11E456`.

| Collateral | Strategy address | Underlying |
|-----------|------------------|-----------|
| stETH | `0x93c4b944D05dfe6df7645A86cd2206016c51564D` | `0xae7ab9…fe84` (stETH, live-confirmed) |
| rETH | `0x1BeE69b7dFFfA4E2d53C2a2Df135C388AD25dCD2` | rETH |
| cbETH | `0x54945180dB7943c0ed0FEE7EdaB2Bd24620256bc` | cbETH |
| ETHx | `0x9d7eD45EE2E8FC5482fa2428f15C971e6369011d` | ETHx |
| ankrETH | `0x13760F50a9d7377e4F20CB8CF9e4c26586c658ff` | ankrETH |
| oETH | `0xa4C637e0F704745D182e4D38cAb7E7485321d059` | oETH |
| osETH | `0x57ba429517c3473B6d34CA9aCd56c0e735b94c02` | osETH |
| swETH | `0x0Fe4F44beE93503346A3Ac9EE5A26b130a5796d6` | swETH |
| wBETH | `0x7CA911E83dabf90C90dD3De5411a10F1A6112184` | wBETH |
| sfrxETH | `0x8CA7A5d6f3acd3A7A8bC468a8CD0FB14B6BD28b6` | sfrxETH |
| lsETH | `0xAe60d8180437b5C34bB956822ac2710972584473` | lsETH |
| mETH | `0x298aFB19A105D59E74658C4C334Ff360BadE6dd2` | mETH |
| **eigenStrategy** (EIGEN restaking) | `0xaCB55C530Acdb2849e6d4f36992Cd8c9D50ED8F7` | `0x83E9…` (bEIGEN, live-confirmed) — impl `0x509aadb99487182b21ff4e9e7eb362a9ea8e8f40` |

| **beaconChainETHStrategy** (sentinel, NOT a contract) | `0xbeaC0eeEeeeeEEeEeEEEEeeEEeEeeeEeeEEBEaC0` | Virtual strategy address used to denote native-ETH shares in DelegationManager/EigenPodManager accounting — **no code**. Read live from `EigenPodManager.beaconChainETHStrategy()` (`0x9104c319`); note the `beac0…eebeac0` bookend (NOT all-`e`) |

### 3.4 Strategy factory (permissionless new strategies use beacon proxies)
| Role | Address | Pattern |
|------|---------|---------|
| StrategyFactory | `0x5e4C39Ad7A3E881585e383dB9827EB4811f6F647` | TUP → impl `0x315bcd0f31ef8b1124382f3acab3913f791c09e7` |
| strategyFactoryBeacon | `0x0ed6703C298d28aE0878d1b28e88cA87F9662fE9` | UpgradeableBeacon; `implementation()` → `0x8f6be4a906376bb4481e78cbf6fc783cc0f8d1ce` (live) |
| strategyFactoryBeaconImplementation | `0x0EC17ef9c00F360DB28CA8008684a4796b11E456` | StrategyBase logic (= `baseStrategyImplementation`) |

> Strategies created via the factory are **BeaconProxy** (→ strategyFactoryBeacon). The 12 pre-deployed LST strategies above are instead **TUP** under `eigenLayerProxyAdmin`.

### 3.5 Tokens
| Role | Proxy | Live impl | Proxy admin |
|------|-------|-----------|-------------|
| **EIGEN** | `0xec53bF9167f50cDEB3Ae105f56099aaaB9061F83` | `0x2c4a81e257381f87f5a5c4bd525116466d972e50` (live) | `eigenLayerProxyAdmin 0x8b95…2444` (admin slot read live) |
| **bEIGEN** (backing) | `0x83E9115d334D248Ce39a6f36144aEaB5b3456e75` | `0xf2b225815f70c9b327dc9db758a36c92a4279b17` (live) | `tokenProxyAdmin 0x3f5Ab2D4…` |
| tokenProxyAdmin | `0x3f5Ab2D4418d38568705bFd6672630fCC3435CC9` | — | Separate ProxyAdmin for **bEIGEN only** (EIGEN is admined by `eigenLayerProxyAdmin`) |

> **Live EIGEN impl drift:** the config snapshot lists `EIGENImpl 0x17f56E91…` but the live EIP-1967 impl slot reads `0x2c4a81e2…` — the token was upgraded after the config snapshot. **Read the impl slot live.** Only **bEIGEN** uses `tokenProxyAdmin`; **EIGEN's** admin slot reads `eigenLayerProxyAdmin 0x8b95…2444` — read each token's admin slot, they differ.

### 3.6 Admin / governance / infra
| Role | Address | One-liner |
|------|---------|-----------|
| **eigenLayerProxyAdmin** | `0x8b9566AdA63B64d1E1dcF1418b43fd1433b72444` | ProxyAdmin owning all §3.1/§3.3 (LST) proxies — the upgrade key |
| eigenLayerPauserReg | `0x0c431C66F4dE941d089625E5B423D00707977060` | Pauser registry (pause/unpause auth) |
| emptyContract | `0x1f96861fEFa1065a5A96F20Deb6D8DC3ff48F7f9` | Bootstrap impl for not-yet-initialized proxies |
| timelock | `0xA6Db1A8C5a981d1536266D2a393c5F8dDb210EAF` | Governance timelock |
| executorMultisig | `0x369e6F597e22EaB55fFb173C6d9cD234BD699111` | Executes timelocked upgrades (ProxyAdmin owner) |
| communityMultisig | `0xFEA47018D632A77bA579846c840d5706705Dc598` | Community-controlled multisig |
| operationsMultisig | `0xBE1685C81aA44FF9FB319dD389addd9374383e90` | Ops multisig |
| pauserMultisig | `0x5050389572f2d220ad927CcbeA0D406831012390` | Pause multisig |

---

## 4. Cross-chain summary

EigenLayer restaking core is **Ethereum-mainnet-only**. Every key contract is **absent** on all six other targets (verified `eth_getCode → 0x`, §6).

| Chain (ID) | DelegationManager | StrategyManager | EigenPodManager | AllocationManager | EIGEN (`0xec53…`) | bEIGEN (`0x83E9…`) |
|------------|:-----------------:|:---------------:|:---------------:|:-----------------:|:-----------------:|:------------------:|
| **Ethereum (1)** | `0x3905…F37A` | `0x8586…075A` | `0x91E6…A338` | `0x948a…bc39` | `0xec53…1F83` | `0x83E9…6e75` |
| Base (8453) | — | — | — | — | — | — |
| BNB (56) | — | — | — | — | — | — |
| Avalanche (43114) | — | — | — | — | — | — |
| Arbitrum (42161) | — | — | — | — | —¹ | — |
| Optimism (10) | — | — | — | — | — | — |
| Polygon (137) | — | — | — | — | — | — |

¹ **Arbitrum decoy:** `0x9fcc9b73b0614c33c26038f5850c29e89728dc47` is a **45-byte EIP-1167 clone** with **symbol `EIGEN`** but **name "EigenLayer World Builders"** (an unrelated game/airdrop token) — it is **NOT** the canonical restaking EIGEN (`name() = "Eigen"`). Do not treat symbol collisions as the EigenLayer token; key on the canonical Ethereum address.

> The canonical EIGEN at `0xec53…` is a single Ethereum-mainnet deployment. EIGEN is *designed* to be cross-chain-portable (ERC20Votes + intended LayerZero OFT bridging), but as of this verification **no bridged restaking-EIGEN deployment of the foundation token exists at the canonical address on any of the six other targets**, and the only EIGEN-symbol token found on a target L2 is the unrelated decoy above. Verify any future bridged representation by address + `name()` before indexing.

---

## 5. Proxies (old & new)

| Contract(s) | Pattern | Detection | Upgrade authority |
|-------------|---------|-----------|-------------------|
| **All core managers** (DelegationManager, StrategyManager, EigenPodManager, AVSDirectory, AllocationManager, RewardsCoordinator, PermissionController, Slasher, DelayedWithdrawalRouter) + **the 12 LST strategies** + eigenStrategy + StrategyFactory | **TransparentUpgradeableProxy (EIP-1967)** | impl slot `0x3608…2bbc` non-zero; admin slot `0xb531…6103` = `eigenLayerProxyAdmin 0x8b95…2444` | `eigenLayerProxyAdmin` (owner = executorMultisig via timelock); watch `Upgraded(address)` `0xbc7cd75a…` |
| **EIGEN** | TransparentUpgradeableProxy | impl slot non-zero; admin slot = `eigenLayerProxyAdmin 0x8b95…2444` | `eigenLayerProxyAdmin` (same as core) |
| **bEIGEN** | TransparentUpgradeableProxy | impl slot non-zero; admin slot = `tokenProxyAdmin 0x3f5A…5CC9` | **separate** `tokenProxyAdmin` |
| **eigenPodBeacon, strategyFactoryBeacon** | **UpgradeableBeacon** | `implementation()` (`0x5c60da1b`), not a storage slot | beacon owner |
| **Per-owner EigenPod, factory-created strategies** | **BeaconProxy (EIP-1967 beacon slot)** | beacon slot `0xa3f0…133d50` = the beacon address | upgrade the beacon to upgrade all instances |
| beaconOracle, eigenLayerPauserReg, emptyContract, `beaconChainETHStrategy` sentinel | **non-proxy** (sentinel has no code) | impl slot `0x` | n/a |

**Two ProxyAdmins.** Core + strategies + **EIGEN** → `eigenLayerProxyAdmin 0x8b95…2444`. Only **bEIGEN** → `tokenProxyAdmin 0x3f5A…5CC9`. **Read the live impl slot for every contract** — EigenLayer upgrades in place (EIGEN's live impl already drifted from the config snapshot, §3.5). The pre-deployed LST strategies are **TUP**, not beacon proxies; only **factory-deployed** strategies are beacon proxies.

---

## 6. Detection invariants & gotchas

1. **LST deposit = `StrategyManager.Deposit(address,address,uint256)` 3-arg (`0x5548c837…`).** The 4-arg legacy `Deposit` is gone. **topic0 `0x5548c837…` collides** with ve(3,3) gauge `Deposit(address,address,uint256)` (Velodrome/Aerodrome/Topaz) — disambiguate by the StrategyManager emitter `0x8586…075A`.
2. **Withdrawals use the Slashing* events.** Key on `SlashingWithdrawalQueued` (`0x26b2aae…`) / `SlashingWithdrawalCompleted` (`0x1f40400…`). The legacy `WithdrawalQueued`/`WithdrawalCompleted` topics are **dormant (0 live)**.
3. **`OperatorRegistered` is 2-arg `(address,address)` (`0xa453db…`)** — not the struct form. Delegation is `StakerDelegated`/`StakerUndelegated`.
4. **Native-ETH restaking is the EigenPod flow, not StrategyManager.** No LST `Deposit`; instead `EigenPodManager.PodDeployed` + `BeaconChainETHDeposited` + `PodSharesUpdated`, and per-pod `EigenPodStaked`/`CheckpointCreated`/`CheckpointFinalized`. Native-ETH shares are tracked against the **sentinel strategy `0xbeaC0e…EBEaC0`** (no code).
5. **EigenPods are BeaconProxies emitting from their own address.** To enumerate pods, read `PodDeployed` on EigenPodManager (`topic1` = pod, `topic2` = owner). Pod-level events won't appear in EigenPodManager logs.
6. **Current EigenPod validator events key on `bytes32 pubkeyHash`** (older code: `uint40 validatorIndex`) → different topic0s. Use the bytes32 forms in §1.4. Pectra events (`SwitchToCompoundingRequested`, `ConsolidationRequested`, `ExitRequested`, `WithdrawalRequested`) were added with the Pectra upgrade.
7. **Slashing is on AllocationManager, not Slasher.** `Slasher` (`0xD921…`) is deployed but inert. The real slash event is `AllocationManager.OperatorSlashed` (`0x8096…`, live-confirmed, rare). `OperatorSharesSlashed` on DelegationManager mirrors the share reduction.
8. **AVS opt-in has two surfaces:** legacy M2 `AVSDirectory.OperatorAVSRegistrationStatusUpdated` (live) and the new operator-set model on `AllocationManager` (`OperatorSetCreated`, `OperatorAddedToOperatorSet`, `AllocationUpdated`). Both are active.
9. **`RewardsClaimed` is the 6-arg form (`0x9543dbd5…`)**; `DistributionRootSubmitted` (`0xecd866c3…`) fires ~weekly. The reward token is in the event, not always EIGEN.
10. **Two ProxyAdmins + live-impl drift.** Only **bEIGEN** uses `tokenProxyAdmin 0x3f5A…`; **EIGEN** and everything else use `eigenLayerProxyAdmin 0x8b95…` (read each proxy's admin slot — don't assume tokens share an admin). Never trust the config's `*Implementation` fields for the live impl (EIGEN, AllocationManager, PermissionController, StrategyFactory have all drifted) — **read the EIP-1967 impl slot live**. Watch `Upgraded(address)` `0xbc7cd75a…` on all proxies.
11. **EIGEN ≠ bEIGEN.** EIGEN (`0xec53…`) is a wrapper over bEIGEN (`0x83E9…`); `EIGEN.wrap`/`unwrap` (`0xea598cb0`/`0xde0e9a3e` — same selectors as Lido wstETH) move bEIGEN. The eigenStrategy's underlying is **bEIGEN**, not EIGEN.
12. **Ethereum-only.** Any "EigenLayer" contract claimed on Base/BNB/Avalanche/Arbitrum/Optimism/Polygon is **not the protocol** (all `eth_getCode → 0x`). The Arbitrum `EIGEN`-symbol token is a decoy (§4 note 1).

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- DelegationManager
TOPIC_OPERATOR_REGISTERED      = '\xa453db612af59e5521d6ab9284dc3e2d06af286eb1b1b7b771fce4716c19f2c1'
TOPIC_STAKER_DELEGATED         = '\xc3ee9f2e5fda98e8066a1f745b2df9285f416fe98cf2559cd21484b3d8743304'
TOPIC_STAKER_UNDELEGATED       = '\xfee30966a256b71e14bc0ebfc94315e28ef4a97a7131a9e2b7a310a73af44676'
TOPIC_OPERATOR_SHARES_INCREASED= '\x1ec042c965e2edd7107b51188ee0f383e22e76179041ab3a9d18ff151405166c'
TOPIC_OPERATOR_SHARES_DECREASED= '\x6909600037b75d7b4733aedd815442b5ec018a827751c832aaff64eba5d6d2dd'
TOPIC_SLASHING_WD_QUEUED        = '\x26b2aae26516e8719ef50ea2f6831a2efbd4e37dccdf0f6936b27bc08e793e30'
TOPIC_SLASHING_WD_COMPLETED     = '\x1f40400889274ed07b24845e5054a87a0cab969eb1277aafe61ae352e7c32a00'
TOPIC_OPERATOR_SHARES_SLASHED   = '\xdd611f4ef63f4385f1756c86ce1f1f389a9013ba6fa07daba8528291bc2d3c30'
-- StrategyManager
TOPIC_DEPOSIT_3ARG             = '\x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62'  -- COLLIDES w/ ve(3,3) gauge Deposit; key on StrategyManager
TOPIC_STRAT_ADDED_WHITELIST    = '\x0c35b17d91c96eb2751cd456e1252f42a386e524ef9ff26ecc9950859fdc04fe'
-- EigenPodManager / EigenPod
TOPIC_POD_DEPLOYED             = '\x21c99d0db02213c32fff5b05cf0a718ab5f858802b91498f80d82270289d856a'
TOPIC_POD_SHARES_UPDATED       = '\x4e2b791dedccd9fb30141b088cabf5c14a8912b52f59375c95c010700b8c6193'
TOPIC_BEACON_ETH_DEPOSITED     = '\x35a85cabc603f48abb2b71d9fbd8adea7c449d7f0be900ae7a2986ea369c3d0d'
TOPIC_EIGENPOD_STAKED          = '\xa01003766d3cd97cf2ade5429690bf5d206be7fb01ef9d3a0089ecf67bc11219'
TOPIC_CHECKPOINT_CREATED       = '\x575796133bbed337e5b39aa49a30dc2556a91e0c6c2af4b7b886ae77ebef1076'
TOPIC_CHECKPOINT_FINALIZED     = '\x525408c201bc1576eb44116f6478f1c2a54775b19a043bcfdc708364f74f8e44'
-- AVSDirectory / AllocationManager
TOPIC_AVS_REG_STATUS_UPDATED   = '\xf0952b1c65271d819d39983d2abb044b9cace59bcc4d4dd389f586ebdcb15b41'
TOPIC_OPERATOR_SET_CREATED     = '\x31629285ead2335ae0933f86ed2ae63321f7af77b4e6eaabc42c057880977e6c'
TOPIC_OPERATOR_ADDED_TO_SET    = '\x43232edf9071753d2321e5fa7e018363ee248e5f2142e6c08edd3265bfb4895e'
TOPIC_ALLOCATION_UPDATED       = '\x1487af5418c47ee5ea45ef4a93398668120890774a9e13487e61e9dc3baf76dd'
TOPIC_OPERATOR_SLASHED         = '\x80969ad29428d6797ee7aad084f9e4a42a82fc506dcd2ca3b6fb431f85ccebe5'
-- RewardsCoordinator
TOPIC_AVS_REWARDS_SUBMISSION   = '\x450a367a380c4e339e5ae7340c8464ef27af7781ad9945cfe8abd828f89e6281'
TOPIC_OP_DIRECTED_AVS_REWARDS  = '\xfc8888bffd711da60bc5092b33f677d81896fe80ecc677b84cfab8184462b6e0'
TOPIC_DISTRIBUTION_ROOT        = '\xecd866c3c158fa00bf34d803d5f6023000b57080bcb48af004c2b4b46b3afd08'
TOPIC_REWARDS_CLAIMED          = '\x9543dbd55580842586a951f0386e24d68a5df99ae29e3b216588b45fd684ce31'
-- Tokens / proxy lifecycle
TOPIC_TRANSFER                 = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_UPGRADED                 = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors =====
SEL_DELEGATE_TO                = '\xeea9064b'   -- delegateTo(address,(bytes,uint256),bytes32)
SEL_REGISTER_AS_OPERATOR       = '\x2aa6d888'   -- registerAsOperator(address,uint32,string)
SEL_UNDELEGATE                 = '\xda8be864'   -- undelegate(address)
SEL_QUEUE_WITHDRAWALS          = '\x0dd8dd02'   -- queueWithdrawals((address[],uint256[],address)[])
SEL_COMPLETE_QUEUED_WD         = '\xe4cc3f90'   -- completeQueuedWithdrawal(...)
SEL_DEPOSIT_INTO_STRATEGY      = '\xe7a050aa'   -- depositIntoStrategy(address,address,uint256)
SEL_CREATE_POD                 = '\x84d81062'   -- createPod()
SEL_EPM_STAKE                  = '\x9b4e4634'   -- stake(bytes,bytes,bytes32)
SEL_START_CHECKPOINT           = '\x88676cad'   -- startCheckpoint(bool)
SEL_SLASH_OPERATOR             = '\x36352057'   -- AllocationManager.slashOperator(...)
SEL_MODIFY_ALLOCATIONS         = '\x952899ee'   -- modifyAllocations(...)
SEL_CREATE_OPERATOR_SETS       = '\x261f84e0'   -- createOperatorSets(address,(uint32,address[])[])
SEL_PROCESS_CLAIM              = '\x3ccc861d'   -- RewardsCoordinator.processClaim(...)
SEL_CREATE_AVS_REWARDS         = '\xfce36c7d'   -- createAVSRewardsSubmission(...)

-- ===== Ethereum mainnet (chain ID 1) =====
DELEGATION_MANAGER             = '\x39053d51b77dc0d36036fc1fcc8cb819df8ef37a'
STRATEGY_MANAGER               = '\x858646372cc42e1a627fce94aa7a7033e7cf075a'
EIGENPOD_MANAGER               = '\x91e677b07f7af907ec9a428aafa9fc14a0d3a338'
AVS_DIRECTORY                  = '\x135dda560e946695d6f155dacafc6f1f25c1f5af'
ALLOCATION_MANAGER             = '\x948a420b8cc1d6bfd0b6087c2e7c344a2cd0bc39'
REWARDS_COORDINATOR            = '\x7750d328b314effa365a0402ccfd489b80b0adda'
PERMISSION_CONTROLLER          = '\x25e5f8b1e7adf44518d35d5b2271f114e081f0e5'
SLASHER_LEGACY                 = '\xd92145c07f8ed1d392c1b88017934e301cc1c3cd'
EIGENPOD_BEACON                = '\x5a2a4f2f3c18f09179b6703e63d9edd165909073'
STRATEGY_FACTORY               = '\x5e4c39ad7a3e881585e383db9827eb4811f6f647'
STRATEGY_FACTORY_BEACON        = '\x0ed6703c298d28ae0878d1b28e88ca87f9662fe9'
STRATEGY_STETH                 = '\x93c4b944d05dfe6df7645a86cd2206016c51564d'
STRATEGY_EIGEN                 = '\xacb55c530acdb2849e6d4f36992cd8c9d50ed8f7'
BEACONCHAIN_ETH_STRATEGY       = '\xbeac0eeeeeeeeeeeeeeeeeeeeeeeeeeeeeebeac0'  -- sentinel, no code
EIGEN_TOKEN                    = '\xec53bf9167f50cdeb3ae105f56099aaab9061f83'
BEIGEN_TOKEN                   = '\x83e9115d334d248ce39a6f36144aeab5b3456e75'
EIGENLAYER_PROXY_ADMIN         = '\x8b9566ada63b64d1e1dcf1418b43fd1433b72444'
TOKEN_PROXY_ADMIN              = '\x3f5ab2d4418d38568705bfd6672630fcc3435cc9'
EIP1967_IMPL_SLOT              = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_BEACON_SLOT            = '\xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50'
```

---

## 8. Verification & sources

- **keccak-256:** every topic0 and selector recomputed locally as `keccak256(canonical signature)` and cross-checked against known ERC-20 `Transfer`/`Approval` topic0s before use.
- **Topics (✓):** observed verbatim in live `eth_getLogs` over recent block windows on `https://ethereum-rpc.publicnode.com`. Confirmed counts: `StakerDelegated`, `OperatorRegistered`, `OperatorSharesIncreased/Decreased`, `DepositScalingFactorUpdated`, `SlashingWithdrawalQueued/Completed`, `Deposit` (3-arg), `PodDeployed`, `PodSharesUpdated`, `DistributionRootSubmitted` (weekly), `RewardsClaimed`, `AVSRewardsSubmissionCreated`, `OperatorDirectedAVSRewardsSubmissionCreated`, `OperatorAVSRegistrationStatusUpdated`, `OperatorSetCreated`, `OperatorAddedToOperatorSet`, `AllocationUpdated`, `EncumberedMagnitudeUpdated`, and **`OperatorSlashed`** (found 7 in a ~270k-block-old window). Legacy `WithdrawalQueued`/`WithdrawalCompleted` and 4-arg `Deposit` confirmed **0 live**. Admin/rare events marked `src` (keccak of the verbatim canonical signature).
- **Selectors (bytecode):** PUSH4-presence scan of each live implementation (proxies resolved via EIP-1967 impl slot read). `createOperatorSets` and `processClaim` corrected after the first struct guesses were absent — the live forms (`0x261f84e0`, `0x3ccc861d`) confirmed present.
- **Addresses:** `Layr-Labs/eigenlayer-contracts` `script/configs/mainnet/mainnet-addresses.config.json` (`v1.4.1`), every entry existence-checked via `eth_getCode` and proxy slots read live (impl `0x3608…2bbc`, admin `0xb531…6103`, beacon `0xa3f0…133d50`). `EIGEN.bEIGEN()` and strategy `underlyingToken()`/`symbol()` confirmed via `eth_call`. **EIGEN live impl differs from the config snapshot** (read live).
- **Cross-chain:** `eth_getCode` for DelegationManager / StrategyManager / EigenPodManager / EIGEN / bEIGEN on all 7 target RPCs — present only on Ethereum, `0x` on the other six. The Arbitrum `EIGEN`-symbol decoy (`0x9fcc…dc47`, name "EigenLayer World Builders", 45-byte EIP-1167 clone) identified by `name()`/`symbol()`/code-length.

Authoritative sources:

- [`Layr-Labs/eigenlayer-contracts`](https://github.com/Layr-Labs/eigenlayer-contracts) — `src/contracts/interfaces/{IDelegationManager,IStrategyManager,IEigenPodManager,IEigenPod,IAVSDirectory,IAllocationManager,IRewardsCoordinator}.sol`, `libraries/OperatorSetLib.sol`, and `script/configs/mainnet/mainnet-addresses.config.json`.
- [EigenLayer docs](https://docs.eigencloud.xyz/eigenlayer/) (formerly docs.eigenlayer.xyz).
- Explorers: [Etherscan EIGEN](https://etherscan.io/address/0xec53bf9167f50cdeb3ae105f56099aaab9061f83), [DelegationManager](https://etherscan.io/address/0x39053D51B77DC0d36036Fc1fCc8Cb819df8Ef37A).
