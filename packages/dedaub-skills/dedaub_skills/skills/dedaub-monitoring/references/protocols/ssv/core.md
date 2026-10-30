# SSV Network — Topics, Selectors, Addresses (Ethereum mainnet only)

**Status:** verified against live RPC on all nine target chains and the canonical `ssvlabs/ssv-network` repo (v2.0.0) on 2026-10-30.
**Scope:** SSV Network, the distributed-validator (DVT) staking layer on Ethereum. This file covers SSVNetwork (operator, cluster and validator lifecycle, DAO parameters, effective-balance oracle, SSV staking), SSVNetworkViews, the SSV token, the cSSV staking receipt token, the rewards distributors, and the upgrade path. Topics and selectors are chain-agnostic. Addresses are Ethereum-only. **SSV Network has no deployment on Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain or Arc.**

SSV Network does not take custody of staked ETH. A validator owner splits the validator key into shares for 4, 7, 10 or 13 **operators**, and registers the validator on-chain with `registerValidator`. The 32 ETH goes to the beacon deposit contract `0x00000000219ab540356cbb839cbe05303d7705fa` directly, not to SSV. On-chain, SSV Network holds only the **cluster fee balance** that pays operators and the network. If the balance runs low, anyone can **liquidate** the cluster and take the collateral.

**v2.0.0 (live since the April 2026 upgrade; `getVersion()` = `v2.0.0`)** changed the model. New clusters pay in **ETH**, not SSV. Fees scale with effective balance (vUnits). Four oracles commit Merkle roots of cluster effective balances. SSV holders can **stake SSV for cSSV** and earn ETH from network fees. Legacy SSV-paid clusters still exist and can migrate one way to ETH. Most event signatures did not change, but the **unit of `value` fields changed** (see §8).

SSVNetwork is a **UUPS proxy** (EIP-1967 impl slot, no admin slot). It is also a **module router**: the proxy delegatecalls each function to one of seven module contracts. **Every event comes from the proxy address `0xdd9b…a4e1`**, not from a module.

---

## 0. Contract families & versions

| Component | Address | Pattern | Notes |
|-----------|---------|---------|-------|
| **SSVNetwork** | `0xdd9bc35ae942ef0cfa76930954a156b3ff30a4e1` | UUPS proxy → `SSVNetworkSSVStakingUpgrade` impl + 7 modules | all state changes, all events |
| **SSVNetworkViews** | `0xafe830b6ee262ba11cce5f32fdcd760ffe6a66e4` | UUPS proxy | read-only facade; `ssvNetwork()` = SSVNetwork |
| **SSV token** | `0x9d65ff81a3c488d585bbfb0bfe3c7707c7917f54` | plain ERC-20, `Ownable` mint | owner = DAO treasury Safe |
| **cSSV token** | `0xe018d31f120a637828f46afd6c64ec099d960546` | plain ERC-20 (v2.0.0) | `ssvStaking()` = SSVNetwork; only SSVNetwork mints/burns |
| **Rewards distributors** | `0xe16d…6d9f`, `0xd7de…c522` | not proxies | Merkle `Claimed(address,uint256)` |
| **CDT → SSV upgrader** | `0x2bf73a478cc6a7ba4e6758a3a52abdc8cdba735e` | EIP-1967 Transparent | deprecated |
| **Based Applications (bApps)** | — | — | testnet only (Hoodi); **no mainnet deployment** |

Module IDs (`enum SSVModules`, used by `updateModule` / `ModuleUpgraded`): 0 = SSV_OPERATORS, 1 = SSV_CLUSTERS, 2 = SSV_DAO, 3 = SSV_VIEWS, 4 = SSV_OPERATORS_WHITELIST, 5 = SSV_STAKING, 6 = SSV_VALIDATORS.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All events below are emitted by **SSVNetwork** `0xdd9b…a4e1`. `Cluster` = tuple `(uint32 validatorCount, uint64 networkFeeIndex, uint64 index, bool active, uint256 balance)` (same layout in v1 and v2). **✓** = seen in live mainnet logs on 2026-10-30. **abi** = from the v2.0.0 ABI only.

### 1.1 Validators

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x48a3ea0796746043948f6341d17ff8200937b99262a0b48c2663b951ed7114e5` | `ValidatorAdded(address indexed owner, uint64[] operatorIds, bytes publicKey, bytes shares, Cluster cluster)` | ✓ |
| `0xccf4370403e5fbbde0cd3f13426479dcd8a5916b05db424b7a2c04978cf8ce6e` | `ValidatorRemoved(address indexed owner, uint64[] operatorIds, bytes publicKey, Cluster cluster)` | ✓ |
| `0xb4b20ffb2eb1f020be3df600b2287914f50c07003526d3a9d89a9dd12351828c` | `ValidatorExited(address indexed owner, uint64[] operatorIds, bytes publicKey)` (exit request to operators) | ✓ |

### 1.2 Clusters

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x2bac1912f2481d12f0df08647c06bee174967c62d3a03cbc078eb215dc1bd9a2` | `ClusterDeposited(address indexed owner, uint64[] operatorIds, uint256 value, Cluster cluster)` | ✓ |
| `0x39d1320bbda24947e77f3560661323384aa0a1cb9d5e040e617e5cbf50b6dbe0` | `ClusterWithdrawn(address indexed owner, uint64[] operatorIds, uint256 value, Cluster cluster)` | ✓ |
| `0x1fce24c373e07f89214e9187598635036111dbb363e99f4ce498488cdc66e688` | `ClusterLiquidated(address indexed owner, uint64[] operatorIds, Cluster cluster)` | ✓ |
| `0xc803f8c01343fcdaf32068f4c283951623ef2b3fa0c547551931356f456b6859` | `ClusterReactivated(address indexed owner, uint64[] operatorIds, Cluster cluster)` | abi |
| `0x6dc71e7231318932a8a7f99bac76f94ffe24cac147843e0c285ce4cf290c803a` | `ClusterMigratedToETH(address indexed owner, uint64[] operatorIds, uint256 ethDeposited, uint256 ssvRefunded, uint32 effectiveBalance, Cluster cluster)` (v2, one-way) | abi |
| `0x0cc301d13799ab915796eed462da724756a969f8e05d69ad2405eb3da7036b55` | `ClusterBalanceUpdated(address indexed owner, uint64[] operatorIds, uint64 indexed blockNum, uint32 effectiveBalance, Cluster cluster)` (v2; EB proof applied) | ✓ |

### 1.3 Operators

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xd839f31c14bd632f424e307b36abff63ca33684f77f28e35dc13718ef338f7f4` | `OperatorAdded(uint64 indexed operatorId, address indexed owner, bytes publicKey, uint256 fee)` | ✓ |
| `0x0e0ba6c2b04de36d6d509ec5bd155c43a9fe862f8052096dd54f3902a74cca3e` | `OperatorRemoved(uint64 indexed operatorId)` | ✓ |
| `0x796204296f2eb56d7432fa85961e9750d0cb21741873ebf7077e28263e327358` | `OperatorFeeDeclared(address indexed owner, uint64 indexed operatorId, uint256 blockNumber, uint256 fee)` | abi |
| `0x5055fa347441172447637c015e80a3ee748b9382212ceb5dca5a3683298fd6f3` | `OperatorFeeDeclarationCancelled(address indexed owner, uint64 indexed operatorId)` | ✓ |
| `0x513e931ff778ed01e676d55880d8db185c29b0094546ff2b3e9f5b6920d16bef` | `OperatorFeeExecuted(address indexed owner, uint64 indexed operatorId, uint256 blockNumber, uint256 fee)` (also fee reductions) | ✓ |
| `0x178bf78bdd8914b8483d640b4a4f84e20943b5eb6b639b7474286364c7651d60` | `OperatorWithdrawn(address indexed owner, uint64 indexed operatorId, uint256 value)` (**ETH since v2; SSV before**) | ✓ |
| `0x8ce3fab60deb285381bb700bc8406adc165eba737126273b52f7dd5280576f91` | `OperatorWithdrawnSSV(address indexed owner, uint64 indexed operatorId, uint256 value)` (v2; legacy SSV earnings) | abi |
| `0x7cae2703330c3f53308fb0fe3a9143f335997ba7e059b9ac8e4417ed8fbddbd3` | `OperatorPrivacyStatusUpdated(uint64[] operatorIds, bool toPrivate)` | abi |
| `0x259235c230d57def1521657e7c7951d3b385e76193378bc87ef6b56bc2ec3548` | `FeeRecipientAddressUpdated(address indexed owner, address recipientAddress)` | ✓ |
| `0x3d5869fa1ed68d6b7b5e2a1f44df8e1e7edd8ea7a6cc240e45c72e2eb3523962` | `OperatorMultipleWhitelistUpdated(uint64[] operatorIds, address[] whitelistAddresses)` | ✓ |
| `0x589a71ef5bb37432c8ce279a4afc32783592f1764c6fcb07e3c437e80c80ab2e` | `OperatorMultipleWhitelistRemoved(uint64[] operatorIds, address[] whitelistAddresses)` | abi |
| `0xf41d8ca981ff900f6db7f71d7e2ae866eae8e4327d23e5c692c13a6c43b39c3d` | `OperatorWhitelistingContractUpdated(uint64[] operatorIds, address whitelistingContract)` | abi |
| `0x29f72634ccb172103f8c542da23de7f6cf9bce724c5bb91bd6f3a516b14c63fe` | `OperatorWhitelistUpdated(uint64 indexed operatorId, address whitelisted)` (**v1 only**; still in ABI) | ✓ |

### 1.4 Effective-balance oracle (v2)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0xc0516bad4be527b56ad33b7087029ffee230e390e2f2d1076597820c9e170b67` | `WeightedRootProposed(bytes32 indexed merkleRoot, uint64 indexed blockNum, uint256 accumulatedWeight, uint256 quorum, uint32 oracleId, address oracle)` (one oracle vote) | ✓ |
| `0x6965b9c8509097ad68ba0eb17fcb9436f4a72a057fe5ac556737580bce80d840` | `RootCommitted(bytes32 indexed merkleRoot, uint64 indexed blockNum)` (quorum reached) | ✓ |
| `0x6113130a2400e4e0980410314b8d41a250e526ca56d039ffd91278aeac44c468` | `OracleReplaced(uint32 indexed oracleId, address indexed oldOracle, address indexed newOracle)` | abi |
| `0x791dc99be5109fa13cd62186968189a4f65235f0a4aea35cdf15c585bbcbfdaf` | `QuorumUpdated(uint16 newQuorum)` | abi |
| `0x8794fa1a5292ace029a96ff5db5c03006669acdf358814c3f716ac098b99092e` | `MinBlocksBetweenUpdatesUpdated(uint32)` | abi |

### 1.5 SSV staking / cSSV (v2)

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d` | `Staked(address indexed user, uint256 amount)` (SSV in, cSSV minted) | ✓ |
| `0x57e41df54512c76148b5ba9b643d149752b0d35e493b969bd017d0a3fe5228cf` | `UnstakeRequested(address indexed user, uint256 amount, uint256 unlockTime)` (cooldown starts; 7 days) | ✓ |
| `0x8fe9b0a74e05eaabda056a095be40fb09405d83f5b2c07d7823d1eb655b927b8` | `UnstakedWithdrawn(address indexed user, uint256 amount)` (SSV out) | ✓ |
| `0x9386d77e0bcb586105f5c2bee7cabc987f85e7c518f34e580fab935df5d3a9c6` | `FeesSynced(uint256 newFeesWei, uint256 accEthPerShare)` | ✓ |
| `0x4e38a3eebabe29eaad79f76c94599208a54f204cbd7d3907ac066df5afcb5057` | `RewardsSettled(address indexed user, uint256 pending, uint256 accrued, uint256 userIndex)` | ✓ |
| `0xfc30cddea38e2bf4d6ea7d3f9ed3b6ad7f176419f4963bd81318067a4aee73fe` | `RewardsClaimed(address indexed user, uint256 amount)` (ETH out) | ✓ |
| `0xe865acf13176ceb6a83a16f925f9f67fd03c94ca1af6160d78a7f8a2914253e2` | `CooldownDurationUpdated(uint64 newCooldownDuration)` | abi |
| `0x8bbfbb5d7fcacf6fc74005cdede0635561638507f576c95f7f294c22141be2e5` | `ERC20Rescued(address indexed token, address indexed to, uint256 amount)` | abi |

### 1.6 DAO parameters and governance

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x8f49a76c5d617bd72673d92d3a019ff8f04f204536aae7a3d10e7ca85603f3cc` | `NetworkFeeUpdated(uint256 oldFee, uint256 newFee)` (**ETH fee since v2; SSV fee before**) | abi |
| `0x67b4581d242b51c956246a35859809bc259dfd07d622b4bc0a9858641a6297fb` | `NetworkFeeUpdatedSSV(uint256 oldFee, uint256 newFee)` (v2) | abi |
| `0x370342c3bb9245e20bffe6dced02ba2fceca979701f881d5adc72d838e83f1c5` | `NetworkEarningsWithdrawn(uint256 value, address recipient)` | ✓ |
| `0xbb018dc682e13c04ee4a5608c89a9f287c402c1aec96588d6dd85478179b4bba` | `OperatorMaximumFeeUpdated(uint256 maxFee)` | abi |
| `0x18d44c1ee4bcb1ecb7d57ca44a74ede64c7c9accda084b97d466e6a0998329b3` | `MinimumOperatorEthFeeUpdated(uint256 minFee)` | abi |
| `0x2fff7e5a48a4befc2c2be4d77e141f6d97907798977ce452429ec55c2658a342` | `OperatorFeeIncreaseLimitUpdated(uint64 value)` | abi |
| `0x5fbd75d987b37490f91aa1909db948e7ff14c6ffb495b2f8e0b2334da9b192f1` | `DeclareOperatorFeePeriodUpdated(uint64 value)` | abi |
| `0xf6b8a2b45d0a60381de51a7b980c4660d9e5b82db6e07a4d342bfc17a6ff96bf` | `ExecuteOperatorFeePeriodUpdated(uint64 value)` | abi |
| `0x42af14411036d7a50e5e92daf825781450fc8fac8fb65cbdb04720ff08efb84f` | `LiquidationThresholdPeriodUpdated(uint64 value)` | abi |
| `0xc968a767c53be943fe324987597efaba682968c894cab4291313662c8b99691d` | `LiquidationThresholdPeriodSSVUpdated(uint64 value)` | abi |
| `0xd363ab4392efaf967a89d8616cba1ff0c6f05a04c2f214671be365f0fab05960` | `MinimumLiquidationCollateralUpdated(uint256 value)` | abi |
| `0xc6e0ba7aedc5595dfb313cf8e5bc03109e9f71dc644c019f9acb86fc054ed454` | `MinimumLiquidationCollateralSSVUpdated(uint256 value)` | abi |
| `0xfdf54bf052398eb41c923eb1bd596351c5e72b99959d1ca529a7f13c0a2503d7` | `ModuleUpgraded(uint8 indexed moduleId, address moduleAddress)` (**logic swap without `Upgraded`**) | abi |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` (SSVNetwork and Views) | abi |
| `0xe733b31bc9141b87ce3fb540e27a03b4711c1214ec06490c8e68daf82bc33911` | `SSVNetworkUpgradeBlock(string version, uint256 blockNumber)` | abi |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` (Ownable2Step) | abi |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` (also SSV token) | abi |

### 1.7 Tokens and distributors

| topic0 | Event | Emitter | ✓ |
|--------|-------|---------|---|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | SSV, cSSV | ✓ |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | SSV, cSSV | ✓ |
| `0xd8138f8a3f377c5259ca548e70e4c2de94f129f5a11036a15b69513cba2b426a` | `Claimed(address account, uint256 amount)` | rewards distributors | ✓ |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

`C` = `(uint32,uint64,uint64,bool,uint256)` (Cluster tuple). All on SSVNetwork unless noted.

### 2.1 Validators and clusters (v2.0.0)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb84319fd` | `registerValidator(bytes,uint64[],bytes,C)` | payable (ETH deposit in `msg.value`) |
| `0xa1b483ca` | `bulkRegisterValidator(bytes[],uint64[],bytes[],C)` | payable |
| `0x12b3fc19` | `removeValidator(bytes,uint64[],C)` | owner |
| `0x5aed1142` | `bulkRemoveValidator(bytes[],uint64[],C)` | owner |
| `0x3877322b` | `exitValidator(bytes,uint64[])` | owner; emits `ValidatorExited` |
| `0x32afd02f` | `bulkExitValidator(bytes[],uint64[])` | owner |
| `0x45f47188` | `deposit(address,uint64[],C)` | payable; anyone can top up |
| `0x686e682c` | `withdraw(uint64[],uint256,C)` | owner |
| `0xea7844ff` | `reactivate(uint64[],C)` | payable |
| `0xbf0f2fb2` | `liquidate(address,uint64[],C)` | permissionless; ETH cluster |
| `0x8c1d3d03` | `liquidateSSV(address,uint64[],C)` | permissionless; legacy SSV cluster |
| `0x36e87b12` | `migrateClusterToETH(uint64[],C)` | payable; one-way |
| `0x4f4d1209` | `updateClusterBalance(uint64,address,uint64[],C,uint32,bytes32[])` | permissionless EB proof |
| `0xdbcdc2cc` | `setFeeRecipientAddress(address)` | validator owner |

**v1.x selectors (before the v2 upgrade; still found in historical traces):** `registerValidator(bytes,uint64[],bytes,uint256,C)` = `0x06e8fb9c`, `bulkRegisterValidator(bytes[],uint64[],bytes[],uint256,C)` = `0x22f18bf5`, `deposit(address,uint64[],uint256,C)` = `0xbc26e7e5`, `reactivate(uint64[],uint256,C)` = `0x5fec6dd0`, `registerOperator(bytes,uint256)` (v1.0) = `0xff212c5c`. In v1 the SSV amount was an explicit `uint256` argument. In v2 ETH comes in `msg.value`.

### 2.2 Operators

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc9bbc9fa` | `registerOperator(bytes,uint256,bool)` | `(publicKey, fee, setPrivate)` |
| `0x2e168e0e` | `removeOperator(uint64)` | operator owner |
| `0xb317c35f` | `declareOperatorFee(uint64,uint256)` | starts fee-change window |
| `0x8932cee0` | `executeOperatorFee(uint64)` | after declare period |
| `0x23d68a6d` | `cancelDeclaredOperatorFee(uint64)` | |
| `0x190d82e4` | `reduceOperatorFee(uint64,uint256)` | immediate |
| `0x35f63767` | `withdrawOperatorEarnings(uint64,uint256)` | ETH |
| `0x4bc93b64` | `withdrawAllOperatorEarnings(uint64)` | ETH |
| `0x6bf5c92e` | `withdrawOperatorEarningsSSV(uint64,uint256)` | SSV |
| `0x909b1aaa` | `withdrawAllOperatorEarningsSSV(uint64)` | SSV |
| `0x008108d5` | `withdrawAllVersionOperatorEarnings(uint64)` | ETH + SSV |
| `0x5d06ecb4` | `setOperatorsWhitelists(uint64[],address[])` | |
| `0x4b2fd45e` | `removeOperatorsWhitelists(uint64[],address[])` | |
| `0x7dc24d52` | `setOperatorsWhitelistingContract(uint64[],address)` | |
| `0x6a31cf1d` | `removeOperatorsWhitelistingContract(uint64[])` | |
| `0x822124c1` / `0x4ad00e54` | `setOperatorsPrivateUnchecked(uint64[])` / `setOperatorsPublicUnchecked(uint64[])` | |

### 2.3 Staking (cSSV) and oracle

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa694fc3a` | `stake(uint256)` | SSV → cSSV |
| `0x23095721` | `requestUnstake(uint256)` | starts cooldown |
| `0x6fcd112b` | `withdrawUnlocked()` | SSV out after cooldown |
| `0x27596fce` | `claimEthRewards()` | ETH out |
| `0xc54f0916` | `syncFees()` | permissionless |
| `0x3dd704f0` | `onCSSVTransfer(address,address,uint256)` | callback from cSSV only |
| `0x00ebb5f0` | `commitRoot(bytes32,uint64)` | oracle only |

### 2.4 DAO / owner-only and upgrade

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1f1f9fd5` | `updateNetworkFee(uint256)` | ETH network fee |
| `0x71513214` | `updateNetworkFeeSSV(uint256)` | SSV network fee |
| `0x6535f740` | `withdrawNetworkSSVEarnings(uint256)` | DAO SSV earnings |
| `0x6f4b158d` | `updateMaximumOperatorFee(uint256)` | |
| `0xe9d232cd` | `updateMinimumOperatorEthFee(uint256)` | |
| `0x3631983f` | `updateOperatorFeeIncreaseLimit(uint64)` | |
| `0x79e3e4e4` / `0xeb608022` | `updateDeclareOperatorFeePeriod(uint64)` / `updateExecuteOperatorFeePeriod(uint64)` | |
| `0x6512447d` / `0xe567ed58` | `updateLiquidationThresholdPeriod(uint64)` / `updateLiquidationThresholdPeriodSSV(uint64)` | |
| `0xb4c9c408` / `0x9f5c1307` | `updateMinimumLiquidationCollateral(uint256)` / `updateMinimumLiquidationCollateralSSV(uint256)` | |
| `0x5d756b1d` | `replaceOracle(uint32,address)` | |
| `0x9ba0e700` | `updateQuorumBps(uint16)` | |
| `0x11dff249` | `updateMinBlocksBetweenUpdates(uint32)` | |
| `0xbe2270dd` | `updateUnstakeCooldownDuration(uint64)` | |
| `0xb2118a8d` | `rescueERC20(address,address,uint256)` | |
| `0xe3e324b0` | `updateModule(uint8,address)` | **swaps a module** |
| `0x3659cfe6` / `0x4f1ef286` | `upgradeTo(address)` / `upgradeToAndCall(address,bytes)` | UUPS (Network and Views) |
| `0xf2fde38b` / `0x79ba5097` | `transferOwnership(address)` / `acceptOwnership()` | Ownable2Step |
| `0x0d8e6e2c` | `getVersion()` | `"v2.0.0"` |

### 2.5 SSVNetworkViews (read-only)

| Selector | Signature |
|----------|-----------|
| `0xbe3f058e` | `getOperatorById(uint64)` |
| `0x9ad3c745` | `getOperatorFee(uint64)` |
| `0x03b3d436` | `getOperatorDeclaredFee(uint64)` |
| `0x6d0db0e4` / `0x214c217b` | `getOperatorEarnings(uint64)` / `getOperatorEarningsSSV(uint64)` |
| `0xeb8ecfa7` / `0xcd48b554` | `getBalance(address,uint64[],C)` / `getBalanceSSV(address,uint64[],C)` |
| `0xca162e5e` | `getBurnRate(address,uint64[],C)` |
| `0x16cff008` / `0x2f822680` | `isLiquidatable(address,uint64[],C)` / `isLiquidatableSSV(address,uint64[],C)` |
| `0xa694695b` | `isLiquidated(address,uint64[],C)` |
| `0x648e4714` | `getClusterAssetType(address,uint64[])` (ETH vs SSV cluster) |
| `0x8905bd7c` | `getEffectiveBalance(address,uint64[],C)` |
| `0x3e2ec160` | `getValidator(address,bytes)` |
| `0xfc043830` / `0xe4dc4cb3` | `getNetworkFee()` / `getNetworkFeeSSV()` |
| `0x777915cb` / `0xce7e0113` | `getNetworkEarnings()` / `getNetworkEarningsSSV()` |
| `0x9568f9d9` | `getNetworkValidatorsCount()` |
| `0x817b1cd2` | `totalStaked()` |
| `0x16765391` | `stakedBalanceOf(address)` |
| `0x37f332eb` | `previewClaimableEth(address)` |
| `0x9cbaaf0a` | `getCommittedRoot(uint64)` |

### 2.6 SSV and cSSV tokens

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address,uint256)` | SSV: owner only. cSSV: SSVNetwork only |
| `0x9dc29fac` | `burn(address,uint256)` | cSSV; SSVNetwork only |
| `0x42966c68` / `0x79cc6790` | `burn(uint256)` / `burnFrom(address,uint256)` | SSV |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` (non-empty) on `https://ethereum-rpc.publicnode.com` on 2026-10-30.

| Role | Address | One-liner |
|------|---------|-----------|
| **SSVNetwork** (proxy) | `0xdd9bc35ae942ef0cfa76930954a156b3ff30a4e1` | `ssvnetwork.eth`; 680-byte ERC1967Proxy; 57,314 validators on 2026-10-30 |
| **SSVNetworkViews** (proxy) | `0xafe830b6ee262ba11cce5f32fdcd760ffe6a66e4` | `views.ssvnetwork.eth` |
| **SSV token** | `0x9d65ff81a3c488d585bbfb0bfe3c7707c7917f54` | `ssv.ssvnetwork.eth`; supply 17,361,673.6 |
| **cSSV token** | `0xe018d31f120a637828f46afd6c64ec099d960546` | `cssv.ssvnetwork.eth`; `totalStaked()` = 4,724,517.3 SSV |
| **SSV DAO Treasury** (Safe) | `0xb35096b074fdb9bbac63e3adae0bbde512b2e6b6` | `owner()` of SSVNetwork, Views and SSV token |
| SSV DAO Foundation (Safe) | `0xec29418bc30fed20de85706f32c7d77da0be7afb` | |
| Rewards Distributor #1 | `0xe16d6138b1d2ad4fd6603acdb329ad1a6cd26d9f` | Merkle SSV incentives |
| Rewards Distributor #2 | `0xd7de1a7f07d5cf5766d8f9c67b036f6ab554c522` | Merkle SSV incentives |
| CDT → SSV upgrader (deprecated) | `0x2bf73a478cc6a7ba4e6758a3a52abdc8cdba735e` | Transparent proxy (admin `0xaf8a…50bed`) |
| Beacon deposit contract (not SSV) | `0x00000000219ab540356cbb839cbe05303d7705fa` | where validator ETH actually goes |

### 3.1 v2.0.0 implementation and modules (from `deployments/mainnet/deploy-result.v2.0.0.json`, all existence-checked)

| Item | Address |
|------|---------|
| SSVNetwork impl (`SSVNetworkSSVStakingUpgrade`) | `0xa72a8f31163d74d708664493d09167dfa13008e9` (= impl slot) |
| SSVNetworkViews impl | `0xadeb99eb2307f874d72b1f814fca106f6bfaa8e9` (= impl slot) |
| Module 0 SSVOperators | `0x38daa3fc4b1e5c02742b67f241b27dceb8bffa45` |
| Module 1 SSVClusters | `0x5dd8980c3c8b48bace3a2ec481bd61f7de1523a9` |
| Module 2 SSVDAO | `0x94ef691daa32cc2d31897ae8767e02988f1add4f` |
| Module 3 SSVViews | `0xf73954ad8c96647c2238e6b7a435557def23c19f` |
| Module 4 SSVOperatorsWhitelist | `0xe8ceac3f59ef0214c957fd72f003bc9671a7196b` |
| Module 5 SSVStaking | `0x238c9c4f6026924c7b51400fa63452faff8e959a` |
| Module 6 SSVValidators | `0xcfa765f971b1d10b7bf989aad80cab817b92fe1e` |
| EB oracles 1–4 (config) | `0xc61f7bd9ee5a3d011caf47aa0e5411f720593920`, `0xc07332e05cec1c4896555a6d10361233fdf14422`, `0x28bea5b242362974d5ddb8f17a1e0e525446960b`, `0x3a98ee5f80268ed91f8a5880d93468b76a9f3bb4` (quorum 75 %) |

Live parameters on 2026-10-30: `getNetworkFee()` = 3,366,600,000 wei/block (ETH), `getNetworkFeeSSV()` = 2,423,010,000,000. Unstake cooldown 604,800 s (7 days).

---

## 4. Other target chains — not deployed

`eth_getCode` returns `0x` for SSVNetwork, SSVNetworkViews, SSV and cSSV on Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137), Robinhood Chain (4663) and Arc (5042). The official contract list names only Ethereum mainnet and the Hoodi testnet. No canonical bridged SSV exists on the target chains. A token named "SSV" on another chain is not the SSV Network token unless the SSV DAO publishes it.

---

## 5. Cross-chain summary

| Chain (ID) | SSVNetwork | Views | SSV | cSSV |
|------------|-----------|-------|-----|------|
| Ethereum (1) | `0xdd9b…a4e1` | `0xafe8…66e4` | `0x9d65…7f54` | `0xe018…0546` |
| Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood, Arc | — | — | — | — |

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **SSVNetwork** | UUPS (ERC1967Proxy, 680 B) + module router | impl slot = `0xa72a…08e9`; admin slot = 0 | `owner()` = DAO Treasury Safe `0xb350…e6b6` via `upgradeTo` / `upgradeToAndCall`, and per module via `updateModule` |
| **SSVNetworkViews** | UUPS (680 B) | impl slot = `0xadeb…a8e9`; admin slot = 0 | same owner |
| SSV token | not a proxy | impl/admin slots = 0 | `Ownable` mint by Treasury Safe |
| cSSV token | not a proxy | impl/admin slots = 0 | mint/burn by SSVNetwork only |
| Rewards distributors | not proxies | impl/admin slots = 0 | — |
| CDT upgrader | EIP-1967 Transparent | impl `0x2e98…5db9`, admin `0xaf8a…50bed` | deprecated |

Watch both `Upgraded(address)` (`0xbc7cd75a…2d3b`) and `ModuleUpgraded(uint8,address)` (`0xfdf54bf0…03d7`) on SSVNetwork. A module swap changes logic **without** an `Upgraded` event and **without** an impl-slot change. Owner calls come from a Safe with no on-chain timelock.

---

## 7. Detection invariants & gotchas

1. **One emitter.** Every operator, cluster, validator, staking and DAO event comes from SSVNetwork `0xdd9b…a4e1`. Module addresses never emit.
2. **A cluster is `(owner, sorted operatorIds)`.** The storage key is `keccak256(abi.encodePacked(owner, operatorIds))`. There is no cluster ID in events. Build the key from `owner` + `operatorIds` in each event. The `cluster` tuple in each event is the new post-state.
3. **Unit change at the v2 upgrade (April 2026).** Before v2, `ClusterDeposited.value`, `ClusterWithdrawn.value`, `OperatorWithdrawn.value` and `NetworkFeeUpdated` were in **SSV**. After v2, they are in **ETH** for ETH clusters. Legacy SSV paths use `OperatorWithdrawnSSV` and `NetworkFeeUpdatedSSV`. For `ClusterDeposited` / `ClusterWithdrawn` / `ClusterLiquidated` after v2, read `getClusterAssetType(owner, operatorIds)` or check the transaction value to know the asset.
4. **Selectors changed, topics did not.** v2 dropped the explicit `amount` argument from `registerValidator`, `bulkRegisterValidator`, `deposit` and `reactivate` (ETH is `msg.value`). Monitors that key on v1 selectors (`0x06e8fb9c`, `0xbc26e7e5`, …) see nothing after the upgrade. Event topics did not change.
5. **Liquidation is permissionless and pays the caller.** `ClusterLiquidated` with a liquidator ≠ owner (check `tx.from`) moves the cluster collateral to the liquidator. Large or clustered liquidations are a risk signal for operators and stakers.
6. **`ValidatorExited` is a request, not an exit.** It tells operators to sign a voluntary exit. The beacon-chain exit happens later. `ValidatorRemoved` stops operator duties (and fees), but the validator can stay active on the beacon chain.
7. **Effective-balance oracle.** Each oracle vote emits `WeightedRootProposed`. Only a quorum (75 %) emits `RootCommitted`. Then anyone can apply a cluster proof with `updateClusterBalance` (`ClusterBalanceUpdated`). The proof can auto-liquidate an under-collateralized ETH cluster in the same call. `OracleReplaced` / `QuorumUpdated` change who controls fee accounting.
8. **Fee changes are timelocked per operator.** `OperatorFeeDeclared` → wait the declare period (7 days) → `OperatorFeeExecuted` within the execute window. `reduceOperatorFee` emits `OperatorFeeExecuted` directly. A fee increase is capped by `OperatorFeeIncreaseLimit`.
9. **Packed amounts.** On-chain ETH amounts are stored /100,000 (`ETH_DEDUCTED_DIGITS`). SSV amounts are stored /10,000,000. Event values are already unpacked to wei. Fees must be divisible by those units.
10. **cSSV is a receipt.** cSSV `Transfer` calls back `onCSSVTransfer` on SSVNetwork to settle ETH rewards for both sides (`RewardsSettled`). A cSSV mint is `Transfer(0x0 → user)` from `stake`. Unstaking burns cSSV at `requestUnstake`, and SSV leaves at `withdrawUnlocked` after the 7-day cooldown.
11. **`OperatorWhitelistUpdated` is the v1 whitelist event.** v1.2+ uses `OperatorMultipleWhitelistUpdated` / `OperatorWhitelistingContractUpdated`.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; emitter = SSVNetwork) =====
TOPIC_VALIDATOR_ADDED               = '\x48a3ea0796746043948f6341d17ff8200937b99262a0b48c2663b951ed7114e5'
TOPIC_VALIDATOR_REMOVED             = '\xccf4370403e5fbbde0cd3f13426479dcd8a5916b05db424b7a2c04978cf8ce6e'
TOPIC_VALIDATOR_EXITED              = '\xb4b20ffb2eb1f020be3df600b2287914f50c07003526d3a9d89a9dd12351828c'
TOPIC_CLUSTER_DEPOSITED             = '\x2bac1912f2481d12f0df08647c06bee174967c62d3a03cbc078eb215dc1bd9a2'
TOPIC_CLUSTER_WITHDRAWN             = '\x39d1320bbda24947e77f3560661323384aa0a1cb9d5e040e617e5cbf50b6dbe0'
TOPIC_CLUSTER_LIQUIDATED            = '\x1fce24c373e07f89214e9187598635036111dbb363e99f4ce498488cdc66e688'
TOPIC_CLUSTER_REACTIVATED           = '\xc803f8c01343fcdaf32068f4c283951623ef2b3fa0c547551931356f456b6859'
TOPIC_CLUSTER_MIGRATED_TO_ETH       = '\x6dc71e7231318932a8a7f99bac76f94ffe24cac147843e0c285ce4cf290c803a'
TOPIC_CLUSTER_BALANCE_UPDATED       = '\x0cc301d13799ab915796eed462da724756a969f8e05d69ad2405eb3da7036b55'
TOPIC_OPERATOR_ADDED                = '\xd839f31c14bd632f424e307b36abff63ca33684f77f28e35dc13718ef338f7f4'
TOPIC_OPERATOR_REMOVED              = '\x0e0ba6c2b04de36d6d509ec5bd155c43a9fe862f8052096dd54f3902a74cca3e'
TOPIC_OPERATOR_FEE_DECLARED         = '\x796204296f2eb56d7432fa85961e9750d0cb21741873ebf7077e28263e327358'
TOPIC_OPERATOR_FEE_CANCELLED        = '\x5055fa347441172447637c015e80a3ee748b9382212ceb5dca5a3683298fd6f3'
TOPIC_OPERATOR_FEE_EXECUTED         = '\x513e931ff778ed01e676d55880d8db185c29b0094546ff2b3e9f5b6920d16bef'
TOPIC_OPERATOR_WITHDRAWN            = '\x178bf78bdd8914b8483d640b4a4f84e20943b5eb6b639b7474286364c7651d60'
TOPIC_OPERATOR_WITHDRAWN_SSV        = '\x8ce3fab60deb285381bb700bc8406adc165eba737126273b52f7dd5280576f91'
TOPIC_FEE_RECIPIENT_UPDATED         = '\x259235c230d57def1521657e7c7951d3b385e76193378bc87ef6b56bc2ec3548'
TOPIC_OPERATOR_WHITELIST_MULTI      = '\x3d5869fa1ed68d6b7b5e2a1f44df8e1e7edd8ea7a6cc240e45c72e2eb3523962'
TOPIC_WEIGHTED_ROOT_PROPOSED        = '\xc0516bad4be527b56ad33b7087029ffee230e390e2f2d1076597820c9e170b67'
TOPIC_ROOT_COMMITTED                = '\x6965b9c8509097ad68ba0eb17fcb9436f4a72a057fe5ac556737580bce80d840'
TOPIC_ORACLE_REPLACED               = '\x6113130a2400e4e0980410314b8d41a250e526ca56d039ffd91278aeac44c468'
TOPIC_QUORUM_UPDATED                = '\x791dc99be5109fa13cd62186968189a4f65235f0a4aea35cdf15c585bbcbfdaf'
TOPIC_STAKED                        = '\x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d'
TOPIC_UNSTAKE_REQUESTED             = '\x57e41df54512c76148b5ba9b643d149752b0d35e493b969bd017d0a3fe5228cf'
TOPIC_UNSTAKED_WITHDRAWN            = '\x8fe9b0a74e05eaabda056a095be40fb09405d83f5b2c07d7823d1eb655b927b8'
TOPIC_FEES_SYNCED                   = '\x9386d77e0bcb586105f5c2bee7cabc987f85e7c518f34e580fab935df5d3a9c6'
TOPIC_REWARDS_SETTLED               = '\x4e38a3eebabe29eaad79f76c94599208a54f204cbd7d3907ac066df5afcb5057'
TOPIC_REWARDS_CLAIMED               = '\xfc30cddea38e2bf4d6ea7d3f9ed3b6ad7f176419f4963bd81318067a4aee73fe'
TOPIC_NETWORK_FEE_UPDATED           = '\x8f49a76c5d617bd72673d92d3a019ff8f04f204536aae7a3d10e7ca85603f3cc'
TOPIC_NETWORK_FEE_UPDATED_SSV       = '\x67b4581d242b51c956246a35859809bc259dfd07d622b4bc0a9858641a6297fb'
TOPIC_NETWORK_EARNINGS_WITHDRAWN    = '\x370342c3bb9245e20bffe6dced02ba2fceca979701f881d5adc72d838e83f1c5'
TOPIC_MODULE_UPGRADED               = '\xfdf54bf052398eb41c923eb1bd596351c5e72b99959d1ca529a7f13c0a2503d7'
TOPIC_UPGRADED                      = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_UPGRADE_BLOCK                 = '\xe733b31bc9141b87ce3fb540e27a03b4711c1214ec06490c8e68daf82bc33911'
TOPIC_OWNERSHIP_TRANSFERRED         = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_ERC20_TRANSFER                = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_DISTRIBUTOR_CLAIMED           = '\xd8138f8a3f377c5259ca548e70e4c2de94f129f5a11036a15b69513cba2b426a'
-- ===== Selectors (chain-agnostic) =====
SEL_REGISTER_VALIDATOR              = '\xb84319fd'
SEL_BULK_REGISTER_VALIDATOR         = '\xa1b483ca'
SEL_REGISTER_VALIDATOR_V1           = '\x06e8fb9c'
SEL_REMOVE_VALIDATOR                = '\x12b3fc19'
SEL_EXIT_VALIDATOR                  = '\x3877322b'
SEL_DEPOSIT                         = '\x45f47188'
SEL_DEPOSIT_V1                      = '\xbc26e7e5'
SEL_WITHDRAW                        = '\x686e682c'
SEL_LIQUIDATE                       = '\xbf0f2fb2'
SEL_LIQUIDATE_SSV                   = '\x8c1d3d03'
SEL_REACTIVATE                      = '\xea7844ff'
SEL_MIGRATE_CLUSTER_TO_ETH          = '\x36e87b12'
SEL_UPDATE_CLUSTER_BALANCE          = '\x4f4d1209'
SEL_REGISTER_OPERATOR               = '\xc9bbc9fa'
SEL_REMOVE_OPERATOR                 = '\x2e168e0e'
SEL_DECLARE_OPERATOR_FEE            = '\xb317c35f'
SEL_EXECUTE_OPERATOR_FEE            = '\x8932cee0'
SEL_WITHDRAW_OPERATOR_EARNINGS      = '\x35f63767'
SEL_STAKE                           = '\xa694fc3a'
SEL_REQUEST_UNSTAKE                 = '\x23095721'
SEL_WITHDRAW_UNLOCKED               = '\x6fcd112b'
SEL_CLAIM_ETH_REWARDS               = '\x27596fce'
SEL_COMMIT_ROOT                     = '\x00ebb5f0'
SEL_UPDATE_NETWORK_FEE              = '\x1f1f9fd5'
SEL_UPDATE_MODULE                   = '\xe3e324b0'
SEL_UPGRADE_TO                      = '\x3659cfe6'
SEL_UPGRADE_TO_AND_CALL             = '\x4f1ef286'
-- ===== Addresses (Ethereum only) =====
ETH_SSV_NETWORK                     = '\xdd9bc35ae942ef0cfa76930954a156b3ff30a4e1'
ETH_SSV_NETWORK_VIEWS               = '\xafe830b6ee262ba11cce5f32fdcd760ffe6a66e4'
ETH_SSV_TOKEN                       = '\x9d65ff81a3c488d585bbfb0bfe3c7707c7917f54'
ETH_CSSV_TOKEN                      = '\xe018d31f120a637828f46afd6c64ec099d960546'
ETH_SSV_DAO_TREASURY                = '\xb35096b074fdb9bbac63e3adae0bbde512b2e6b6'
ETH_SSV_DAO_FOUNDATION              = '\xec29418bc30fed20de85706f32c7d77da0be7afb'
ETH_SSV_REWARDS_DISTRIBUTOR_1       = '\xe16d6138b1d2ad4fd6603acdb329ad1a6cd26d9f'
ETH_SSV_REWARDS_DISTRIBUTOR_2       = '\xd7de1a7f07d5cf5766d8f9c67b036f6ab554c522'
ETH_SSV_NETWORK_IMPL_V2             = '\xa72a8f31163d74d708664493d09167dfa13008e9'
ETH_SSV_VIEWS_IMPL_V2               = '\xadeb99eb2307f874d72b1f814fca106f6bfaa8e9'
```

---

## 9. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** computed locally as `keccak256(signature)` from the committed v2.0.0 ABIs (`abis/SSVNetwork.json`, `SSVNetworkViews.json`, `CSSVToken.json`, `SSVToken.json`). Tuple types were expanded to canonical form. v1 selectors were computed from the v1.x signatures. Topics marked ✓ were matched to live SSVNetwork logs with `eth_getLogs` (publicnode, latest 10,000 blocks) and the Blockscout logs API (history from block 17.5M).
- **Addresses:** from the official contract list (docs.ssv.network) and `deployments/mainnet/*.json`. Each was existence-checked with `eth_getCode`. Views `ssvNetwork()`, cSSV `ssvStaking()`, `owner()` and `getVersion()` were read live.
- **Proxies:** EIP-1967 impl and admin slots read live. Impl slots match the v2.0.0 deploy result.
- **Chain coverage:** the four core literals return `0x` on all eight other target chains.
- **Not verified:** topics marked **abi** were not seen in the sampled ranges. bApps has no mainnet address in the bApps repo or docs.

Authoritative sources:
- [ssvlabs/ssv-network](https://github.com/ssvlabs/ssv-network) — source, ABIs, `docs/SPEC.md`, `RELEASE_NOTES.md`, `deployments/mainnet/`.
- [SSV docs — smart contracts](https://docs.ssv.network/developers/smart-contracts) — official address list.
- [ssvlabs/based-applications](https://github.com/ssvlabs/based-applications) — bApps (testnet only).
- Explorer: [Etherscan SSVNetwork](https://etherscan.io/address/0xdd9bc35ae942ef0cfa76930954a156b3ff30a4e1) · [SSV token](https://etherscan.io/token/0x9d65ff81a3c488d585bbfb0bfe3c7707c7917f54).
