# ether.fi Core (eETH / weETH staking) — Topics, Selectors, Addresses (Ethereum mainnet)

**Status:** verified against live RPC (`https://ethereum-rpc.publicnode.com`) and the verified implementation ABIs of every listed proxy on 2026-10-30. Addresses come from the official ether.fi "Deployed Contracts" page and the canonical `etherfi-protocol/smart-contracts` repo.
**Scope:** the Ethereum staking core: `LiquidityPool`, `eETH`, `weETH`, the withdrawal stack (`WithdrawRequestNFT`, `EtherFiRedemptionManager`, `PriorityWithdrawalQueue`, `WeETHWithdrawAdapter`), validator management (`StakingManager`, `EtherFiNodesManager`, `EtherFiNode` beacon, `AuctionManager`, `NodeOperatorManager`), the oracle (`EtherFiOracle`, `EtherFiAdmin`), membership (`MembershipManager`, `MembershipNFT`), deposits (`Liquifier`, `DepositAdapter`), restaking (`EtherFiRestaker`, AVS operators), rewards, and governance (`RoleRegistry`, timelocks, ETHFI, sETHFI). Topics and selectors are chain-agnostic. Addresses are Ethereum-only: the staking core exists on **Ethereum only**. weETH on other chains is in [weeth-crosschain.md](weeth-crosschain.md).

**What ether.fi core is.** A user deposits ETH into `LiquidityPool` and gets **eETH**, a share-based rebasing token (balance = shares × pooled ETH ÷ total shares). **weETH** wraps eETH into a non-rebasing token. Its rate (`getRate()`, 1.1068 ETH on 2026-10-30) rises at each rebase. A committee of oracle members calls `EtherFiOracle.submitReport()`. At quorum the oracle emits `ReportPublished`. Then `EtherFiAdmin.executeTasks()` applies the report: it calls `LiquidityPool.rebase()` (emits `Rebase` + `ProtocolFeePaid`), finalizes withdrawals and approves validators. One live receipt (tx `0xb1ca5f85…3058`, block 26,299,340) shows the order: `LiquidityPool.Rebase` → `ProtocolFeePaid` → `Deposit` (fee mint) → eETH `Transfer`/`TransferShares` → `EtherFiAdmin.AdminOperationsExecuted`.

**Upgradeability.** Almost every core contract is a **UUPS `ERC1967Proxy`** (845 B, or 142 B / 190 B for newer ones). The EIP-1967 admin slot is empty. The upgrade right is the `UPGRADE_TIMELOCK_ROLE` in `RoleRegistry`, held by the **Upgrade Timelock** `0x9f26…0761` (min delay 864,000 s = 10 days). The same timelock is `RoleRegistry.owner()`. The Operating Timelock `0xcD42…5d7a` (min delay 172,800 s = 2 days) owns the weETH OFT adapter and runs parameter changes. Watch `Upgraded(address)` on every proxy.

---

## 0. Contract families

| Family | Contracts | Notes |
|--------|-----------|-------|
| Staking tokens | LiquidityPool, eETH, weETH | UUPS. eETH emits `TransferShares` next to every `Transfer`. |
| Withdrawals | WithdrawRequestNFT (ERC-721 queue), EtherFiRedemptionManager (instant redeem with fee), PriorityWithdrawalQueue (whitelisted fast queue), WeETHWithdrawAdapter (weETH → NFT request) | UUPS. Two queues share event names with different topic0. |
| Validators | StakingManager, EtherFiNodesManager, EtherFiNode beacon, AuctionManager, NodeOperatorManager, BNFT/TNFT (legacy) | `EtherFiNode` instances are beacon proxies of beacon `0x3c55…c03F` (impl `0x73df4a00…f233`). |
| Oracle | EtherFiOracle, EtherFiAdmin | Daily report → rebase. |
| Deposits | Liquifier (stETH/LST → eETH), DepositAdapter (ETH/WETH/stETH/wstETH → weETH) | UUPS. |
| Restaking (winding down) | EtherFiRestaker, RestakingRewardsRouter, EtherFiAvsOperatorsManager | EigenLayer exit in progress per the official page. |
| Rewards | EtherFiRewardsRouter, CumulativeMerkleRewardsDistributor, KING distributor | Merkle claims. |
| Membership | MembershipManager, MembershipNFT (ERC-1155) | Legacy membership NFT wrapping eETH. |
| Governance | RoleRegistry, Upgrade Timelock, Operating Timelock, Blacklister, RevokeAdmin, EtherFiOperationParameters, AddressProvider, Treasury (Safe) | |
| Tokens | ETHFI (governance ERC20Votes, immutable), sETHFI (Staked ETHFI, BoringVault) | ETHFI cross-chain is in [weeth-crosschain.md](weeth-crosschain.md). |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Every topic below is computed from the verified implementation ABI. Live presence was checked with `eth_getLogs` and explorer log pages on 2026-10-30. The rows marked in the notes column were seen in live logs.

### 1.1 LiquidityPool (`0x3088…F216`)
| topic0 | Event |
|--------|-------|
| `0xa241faf62e66ce518d1934ce4c936d806a02289ba483fac23beb8c15755be90d` | `Deposit(address indexed sender, uint256 amount, uint8 source, address referral)` |
| `0xb9da3f3df62c28aca604806cc6ee9678189d7591ef511a77bb040fa8361e9e02` | `Withdraw(address indexed sender, address recipient, uint256 amount, uint8 source)` |
| `0x11c6bf55864ff83827df712625d7a80e5583eef0264921025e7cd22003a21511` | `Rebase(uint256 totalEthLocked, uint256 totalEEthShares)` |
| `0xafea3ee583ed00355634c0a2f47d947b6af95fda2bc1dbe0ff919c45166789d4` | `ProtocolFeePaid(uint128 protocolFees)` |
| `0x888a2432cd9af74ee23f9ebdf262368f5434dffe681b3c7426880c6639b2a74a` | `EEthSharesBurnedForNonETHWithdrawal(uint256 amountSharesToBurn, uint256 withdrawalValueInETH)` |
| `0x8bef88cac8d05094711d367d04bf4f2fcb4b589ca12a6ed8c8f375000e1e848e` | `ValidatorSpawnerRegistered(address user)` |
| `0x8a5afe4e68ed1b812242442424ef608ee7b0a23b6111c6183e781ac4656e8173` | `ValidatorSpawnerUnregistered(address user)` |
| `0xbf5406678e9fe702eaea01d92d3b62ac5be0a14e1802562e2a428364d30d1b11` | `UpdatedFeeRecipient(address newFeeRecipient)` |
| `0x755134315a797bb3da2a1dd9a4fe4183310c83d99e9b32ca94eb17d356a083e6` | `MinWithdrawAmountSet(uint256 minWithdrawAmount)` |
| `0x25c6dc516485950b29e915125f5dc18ddff8713c81aaa38ce38bea74bedfa425` | `MaxWithdrawAmountSet(uint256 maxWithdrawAmount)` |

> Live (sampled): `Deposit`, `Withdraw`, `Rebase`, `ProtocolFeePaid`, `EEthSharesBurnedForNonETHWithdrawal`. `Rebase(totalEthLocked, totalEEthShares)` fires once per oracle report. The share rate is `totalEthLocked / totalEEthShares`.

### 1.2 eETH (`0x35fA…8ac2`) and weETH (`0xCd5f…b7ee`)
| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x9d9c909296d9c674451c0c24f02cb64981eb3b727f99865939192f880a755dcb` | `TransferShares(address indexed from, address indexed to, uint256 sharesValue)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |

> weETH emits only the standard ERC-20 `Transfer`/`Approval` (wrap = eETH `Transfer` to weETH + weETH mint `Transfer` from `0x0`). Both tokens also emit the shared pause family in §1.9.

### 1.3 WithdrawRequestNFT (`0x7d57…4E2c`) — ERC-721 withdrawal queue
| topic0 | Event |
|--------|-------|
| `0xe8c5062a529781e00d69c769270eb1f1ae6feb921aa80d238bb7b4b919b1ab22` | `WithdrawRequestCreated(uint32 indexed requestId, uint256 amountOfEEth, uint256 shareOfEEth, address owner)` |
| `0x31712d805743a128cf0ab8cdf453da51797d2e6f674bd1e5d77d92e1518e4921` | `WithdrawRequestClaimed(uint32 indexed requestId, uint256 amountOfEEth, uint256 shareOfEEth, address owner)` |
| `0xd1438bf0c355cea90a9b9659e0a0455232d0e6da85797802b4c73778f1e35f13` | `WithdrawRequestInvalidated(uint32 indexed requestId)` |
| `0x785e8e7d6014e174f050f6e4499adea51c4595e705b1b71f79a290d87a055fb4` | `WithdrawRequestValidated(uint32 indexed requestId)` |
| `0x8f13b46229b7bc68329da7a7aec3a926547f0cbb2e5379d36e1310e81052b8f6` | `WithdrawRequestSeized(uint32 indexed requestId)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 indexed tokenId)` |

### 1.4 PriorityWithdrawalQueue (`0x35e7…45FA`)
| topic0 | Event |
|--------|-------|
| `0x615cd1d10af2a795928a8c024915afa7a5f55a75649c20c229927b7324d583fb` | `WithdrawRequestCreated(bytes32 indexed requestId, address indexed user, uint96 amountOfEEth, uint96 shareOfEEth, uint96 amountWithFee, uint32 nonce, uint32 creationTime)` |
| `0xea76945910833f2b555afc61af3d06074e7852b48692257f97679d06125fe599` | `WithdrawRequestFinalized(bytes32 indexed requestId, address indexed user, uint96 amountOfEEth, uint96 sharesOfEEth, uint32 nonce, uint32 timestamp)` |
| `0x332728ddcc0f3fec463b84f56fa3120c3725819441c4e321bf5b806d0d0527c9` | `WithdrawRequestClaimed(bytes32 indexed requestId, address indexed user, uint96 amountOfETHtoWithdraw, uint96 sharesBurned, uint32 nonce, uint32 timestamp)` |
| `0x7833ee1be0fef5e5f928a052b3365c855063b62f32bf65c99a01cfe85ddddac7` | `WithdrawRequestCancelled(bytes32 indexed requestId, address indexed user, uint96 amountOfEEthReturned, uint96 sharesOfEEth, uint32 nonce, uint32 timestamp)` |
| `0x56a832ab5a64b5938dccf176b62c4567a47582d407b27ac2cc66f136747244c6` | `WithdrawRequestInvalidated(bytes32 indexed requestId, uint96 amountOfEEth, uint96 sharesOfEEth, uint32 nonce, uint32 timestamp)` |
| `0xf93f9a76c1bf3444d22400a00cb9fe990e6abe9dbb333fda48859cfee864543d` | `WhitelistUpdated(address indexed user, bool status)` |

### 1.5 EtherFiRedemptionManager (`0xDadE…7Ae0`) — instant redemption
| topic0 | Event |
|--------|-------|
| `0xc733e5de6c9a33d3ad4494396148842e6b8788ce5161d4d96ff548de6019fc60` | `Redeemed(address indexed receiver, uint256 redemptionAmount, uint256 feeAmountToTreasury, uint256 feeAmountToStakers, address token)` |

### 1.6 Oracle — EtherFiOracle (`0x57Aa…6a41`) and EtherFiAdmin (`0x0EF8…D705`)
| topic0 | Event |
|--------|-------|
| `0xe6f12615b1560447dc4b63bb3fb30c998c4839bbee68d976818a929cb8fd8bba` | `ReportSubmitted(uint32 consensusVersion, uint32 refSlotFrom, uint32 refSlotTo, uint32 refBlockFrom, uint32 refBlockTo, bytes32 indexed hash, address indexed committeeMember)` |
| `0x806d044a61ac7edf13f9a0f3dc1846baec3dd94bddee1c6d9f4e7d4841a546b0` | `ReportPublished(uint32 consensusVersion, uint32 refSlotFrom, uint32 refSlotTo, uint32 refBlockFrom, uint32 refBlockTo, bytes32 indexed hash)` |
| `0x8dc002c973d20ab13619cad899c28edb1048a9d6b4ba5488a32e2d27d0a0acb2` | `ReportUnpublished(bytes32 indexed hash)` |
| `0x0cb38e390fbd334396cf04e29d1374459cd2f2edeb56cf4d68004319aa1575c4` | `CommitteeMemberAdded(address indexed member)` |
| `0xc0cdacae5a1efb347198155da639c5dbd0a4231a08caed21a124471443a2f562` | `CommitteeMemberRemoved(address indexed member)` |
| `0x9dcafe810104fa98c663da717c190f40294d51f77f4d41183a01be882b14af03` | `CommitteeMemberUpdated(address indexed member, bool enabled)` |
| `0x9795472303adc5267a6814dd0c9fc79c467be77de1f44a519881eba38ae7586c` | `QuorumUpdated(uint32 newQuorumSize)` |
| `0xc73ffc0c4d416c755e9eec7e1472715f6329066f395eb71db110c02c5e4f4291` | `ConsensusVersionUpdated(uint32 newConsensusVersion)` |
| `0x55ece5d27fbbf0ce0b355edda10842da266263e329354ea9ed02b24ba969fb79` | `OracleReportPeriodUpdated(uint32 newOracleReportPeriod)` |
| `0x997abd9d07db6cb25b8542e4fe05ddc887fc249d15d5ec7e3089ff385012bd2f` | `AdminOperationsExecuted(address indexed _address, bytes32 indexed _reportHash)` |
| `0x66d8d6f2322f635d706545c54130cfcdad0174e5b87a17ff0571fe3faf657b89` | `ValidatorApprovalTaskCreated(bytes32 indexed _taskHash, bytes32 indexed _reportHash, uint256[] _validators)` |
| `0x759d0a7bacdbec16e0b3bb7baf5119df4901d78801e76103cba9eb675a87e8c1` | `ValidatorApprovalTaskCompleted(bytes32 indexed _taskHash, bytes32 indexed _reportHash, uint256[] _validators)` |
| `0x8d2c72dc240d10c98bedf2b88bfd56ac274f9c17918d90e726a70a46fbe8c1ef` | `ValidatorApprovalTaskInvalidated(bytes32 indexed _taskHash, bytes32 indexed _reportHash, uint256[] _validators)` |
| `0x44734f20d91c4e391841c482f8a511327a6a1a88b72864f0454a170fae3597e9` | `MaxNegativeRebaseBpsUpdated(uint256 bps)` |

### 1.7 Validators — StakingManager (`0x25e8…912d`), EtherFiNodesManager (`0x8B71…916F`), AuctionManager, NodeOperatorManager
| topic0 | Event |
|--------|-------|
| `0x145257af791e94a9baa6d143d80bb91506202de6e8b49814e221785063248a1b` | `validatorCreated(bytes32 indexed pubkeyHash, address indexed etherFiNode, bytes pubkey)` |
| `0x8150d115af2aea30a11022232987b82d5e748d48efba6addc26c07377c399a48` | `validatorConfirmed(bytes32 indexed pubkeyHash, address indexed bnftRecipient, address indexed tnftRecipient, bytes pubkey)` |
| `0x694b36e569cec3c2b5f38987ad85ac588f196dc235cf2610ba2fd737fdea7e41` | `linkLegacyValidatorId(bytes32 indexed pubkeyHash, uint256 indexed legacyId)` |
| `0xbde8d08f7385c18e26cc8055486078ec46f7729adfc0e62c5ae19461f1d4febf` | `ValidatorCreationStatusUpdated((bytes,bytes,bytes32,string) depositData, uint256 bidId, address etherFiNode, bytes32 hashedAllData, uint8 indexed status)` |
| `0x0b43d988cd5ab75ae318de41d6871d4b26efe57c3f3975331873f4dc073041fc` | `ValidatorRegistered(address indexed operator, address indexed bNftOwner, address indexed tNftOwner, uint256 validatorId, bytes validatorPubKey, string ipfsHashForEncryptedValidatorKey)` |
| `0x1a61f990373064e9c18b5f83af4cc59b932ffec1f8034b0aa496c7d896ec8888` | `EtherFiNodeDeployed(address indexed etheFiNode)` |
| `0x8c9a4f13b67cb64d7c6aa1ae0c9bf07694af521a28b93e7060020810ab4bc59f` | `FundsTransferred(address indexed nodeAddress, uint256 amount)` |
| `0x5e525a525cf73653f769c8305dc71a68b85b0e62e3cc5258fe187ff9fd3e5cb9` | `PubkeyLinked(bytes32 indexed pubkeyHash, address indexed nodeAddress, uint256 indexed legacyId, bytes pubkey)` |
| `0xd8f619075b50e017c21d307b22358bf96b63f408c3a58d8cd90339eb6d39b3cd` | `PodDisabled(address indexed nodeAddress, address indexed pod)` |
| `0xc5e91e7c1c052841cfdff96be1fea6a3e62b51af6008c70efcdf792468c90f90` | `ValidatorWithdrawalRequestSent(address indexed pod, bytes32 indexed validatorPubkeyHash, bytes validatorPubkey)` |
| `0x2d51539e2a0ccc5a555c645b3e82907b4a0412d8cc36923ece8ea00cc1213f2e` | `ValidatorConsolidationRequested(address indexed pod, bytes32 indexed sourcePubkeyHash, bytes sourcePubkey, bytes32 targetPubkeyHash, bytes targetPubkey)` |
| `0xac987f8ee9c62279dc3fb735a8ab380827d707ff549cfaddca9f8253bd978525` | `ValidatorSwitchToCompoundingRequested(address indexed pod, bytes32 indexed validatorPubkeyHash, bytes validatorPubkey)` |
| `0x1bb6cfc6cc765f48d6e1b6b8c5e5503c0d2ee684bdd46f53e0785cc966e20fab` | `UserAllowedForwardedEigenpodCallsUpdated(address indexed user, bytes4 indexed selector, bool _allowed)` |
| `0x2a1547b8c4fcc5c564373b299ab7eecb2d5013083f2fe08a64698fe5198e1930` | `UserAllowedForwardedExternalCallsUpdated(address indexed user, bytes4 indexed selector, address indexed _target, bool _allowed)` |
| `0x5ac259179cc7e5e7986fdb545b3ac088788061a3924596f10ee30c42c79fcd4c` | `BidCreated(address indexed bidder, uint256 amountPerBid, uint256[] bidIdArray, uint64[] ipfsIndexArray)` |
| `0xc1546e394b1975212fe013e7e6995653585f44e568c407d1157483f7d4b94581` | `BidCancelled(uint256 indexed bidId)` |
| `0x22137bd9eacb6e69f84549fa6fc9796ea73361a61f30598f9bde073f70a96123` | `BidRevenueForwarded(uint256 indexed bidId, address indexed treasury, uint256 amount)` |
| `0x14b65bf05bae9ffbba84981c0d4ac7830cdd44e4ddd1890bac55ae48b56e084a` | `OperatorRegistered(address operator, uint64 totalKeys, uint64 keysUsed, bytes ipfsHash)` |
| `0xabf7b03b7760121fd43b1c75e8ca8f7631d2142c2158bbd0caff7250e3c88147` | `UpdatedOperatorApprovals(address operator, uint8 source, bool approved)` |
| `0xa850ae9193f515cbae8d35e8925bd2be26627fc91bce650b8652ed254e9cab03` | `AddedToWhitelist(address userAddress)` |
| `0xcdd2e9b91a56913d370075169cefa1602ba36be5301664f752192bb1709df757` | `RemovedFromWhitelist(address userAddress)` |

> `validatorCreated` / `validatorConfirmed` / `linkLegacyValidatorId` start with a lower-case letter in source. Hash the exact case.

### 1.8 Deposits, restaking, rewards, membership
| topic0 | Event |
|--------|-------|
| `0x2c19962a366d611900b92f328f12302cf959ee57063a989a1869fc342220ed50` | `Liquified(address _user, uint256 _toEEthAmount, address _fromToken, bool _isRestaked)` |
| `0x82519d66329d63e603ccc585294982e01a733deb1a52cd22912323b5b8ebb655` | `AdapterDeposit(address indexed sender, uint256 amount, uint8 source, address referral)` |
| `0x3981c3c93633524805c93b00b61aa75cc59cd423c30c502354a7c347b0b22524` | `DustSwept(address indexed token, address indexed to, uint256 amount)` |
| `0xf804fe4e35a7437f9f462453cbe461e3f4da691083cd8be30a342c60fc58b5bd` | `QueuedStEthWithdrawals(uint256[] _reqIds)` |
| `0x1ba4549e6ae292c44478aa74f36dd74de5d8e8885ffef988473df19f29f25c15` | `CompletedStEthQueuedWithdrawals(uint256[] _reqIds)` |
| `0x17e1f8c6562ad4a081a5b2053cc2e79b2c8eb52b7104e2ba564d690fa2e5f166` | `CompletedQueuedWithdrawal(bytes32 _withdrawalRoot)` |
| `0x3a58cd79827a08a20cd91c8a256b4769891ee1a36774089671fd5f0db5a3a6f2` | `ForwardedOperatorCall(uint256 indexed id, address indexed target, bytes4 indexed selector, bytes data, address sender)` |
| `0x4d7b7ceda679acb24213ae2669a7fda45d700eb72145e9c9f7dcc5206529472e` | `CreatedEtherFiAvsOperator(uint256 indexed id, address etherFiAvsOperator)` |
| `0x85177f287940f2f05425a4029951af0e047a7f9c4eaa9a6e6917bcd869f86695` | `EthReceived(address indexed from, uint256 value)` |
| `0xca3a24d155af841a817f7f643338faccb74b7c930ce1a2698d66dc42c3041dd6` | `EthSent(address indexed from, address indexed to, uint256 value)` |
| `0xe44c5e8198c63fb6fe0c0183db9bdcb65e434d9b1adaf9dfef67a1947e328ba0` | `Erc20Sent(address indexed caller, address indexed token, uint256 amount)` |
| `0xf7a40077ff7a04c7e61f6f26fb13774259ddf1b6bce9ecf26a8276cdd3992683` | `Claimed(address indexed token, address indexed account, uint256 amount)` |
| `0x99e39ca67afe143904c8112f120e3ed033cf0e15f34d9694f8788acd3d9cd200` | `PendingMerkleRootUpdated(address indexed token, bytes32 merkleRoot)` |
| `0x597d018d73325772f90a34c5e48b539884b55e10dd9dc9a42bb1290af1f83c23` | `ClaimableMerkleRootUpdated(address indexed token, bytes32 oldMerkleRoot, bytes32 newMerkleRoot, uint256 rewardsCalculatedToBlock)` |
| `0xc3599529beb776b7153526f0276737fb1d2fcc4cc9f60202cae8c7fb6aa14e9c` | `RecipientStatusUpdated(address user, bool isWhitelisted)` |
| `0xcb43834f130e97dd7972589b9d660b525eb3d8e0ab865d956d3421b7c0c5c4fb` | `NftUpdated(uint256 _tokenId, uint128 _amount, uint128 _amountSacrificedForBoostingPoints, uint40 _loyaltyPoints, uint40 _tierPoints, uint8 _tier, uint32 _prevTopUpTimestamp, uint96 _share)` |
| `0x411474e787b53f14ba5c38f00a6d38c5cb58edd2e074070aaef01ae9a34af9a7` | `NftUnwrappedForEEth(address indexed _user, uint256 indexed _tokenId, uint256 _amountOfEEth, uint40 _loyaltyPoints, uint256 _feeAmount)` |
| `0xd59e6529f7552a2ee1911a5840babd154ab239622d1ddba8591e92c8b54dbe32` | `FundsMigrated(address indexed user, uint256 _tokenId, uint256 _amount, uint256 _eapPoints, uint40 _loyaltyPoints, uint40 _tierPoints)` |
| `0xc3d58168c5ae7397731d063d5bbf3d657854427343f4c083240f7aacaa2d0f62` | `TransferSingle(address indexed operator, address indexed from, address indexed to, uint256 id, uint256 value)` |
| `0xf43c632cabf9b23317efd3d40fdd5be89b56d735e96a36181c46684f9f9ea81c` | `TokenLocked(uint256 indexed _tokenId, uint256 until)` |

### 1.9 Governance and shared admin events
| topic0 | Event |
|--------|-------|
| `0xaddc47d7e02c95c00ec667676636d772a589ffbf0663cfd7cd4dd3d4758201b8` | `RoleSet(address indexed holder, uint256 indexed role, bool indexed active)` |
| `0x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca` | `CallScheduled(bytes32 indexed id, uint256 indexed index, address target, uint256 value, bytes data, bytes32 predecessor, uint256 delay)` |
| `0xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58` | `CallExecuted(bytes32 indexed id, uint256 indexed index, address target, uint256 value, bytes data)` |
| `0xbaa1eb22f2a492ba1a5fea61b8df4d27c6c8b5f3971e63bb58fa14ff72eedb70` | `Cancelled(bytes32 indexed id)` |
| `0x11c24f4ead16507c69ac467fbd5e4eed5fb5c699626d2cc6d66421df253886d5` | `MinDelayChange(uint256 oldDuration, uint256 newDuration)` |
| `0x7f8b7dc89dae85811a7a85800b892b5816ad5d381c856f1b56490f8fc470c9cb` | `UserBlacklisted(address user)` |
| `0x5ffe8aa215ff509a8b962d6db75a6ad3024ef4d9a4ffa79612eafcd44ef0f52b` | `UserBlacklistedUntil(address user, uint256 until)` |
| `0x0e8627d8a3ba37f2a00b3ae4503c200e696f351225f168df1d3e84eed8009ff9` | `UserUnblacklisted(address user)` |
| `0xeffeabe69bd77252ee0c88a8e8f327e94557947b36d874c4737f9b2cb0ca8627` | `LimiterCreated(bytes32 indexed id, uint256 capacity, uint256 refillRate)` |
| `0x3f787c393cc011fbdf9c74ba5890a2e15f27943415f6697701a84f731bf9b709` | `CapacityUpdated(bytes32 indexed id, uint256 capacity)` |
| `0x3899a5c49ff87ba8fe254881d520a8cea77bf88ed5abe04d348eb96798fcee10` | `RefillRateUpdated(bytes32 indexed id, uint256 refillRate)` |
| `0x9ea039f832396fb1558adb4946a8b537bc46860a915d5e2e1780123e650edd85` | `RemainingUpdated(bytes32 indexed id, uint256 remaining)` |
| `0xac110b6c42e90d104e568e73f953649d7a04fb9d419998f39536c08be8a1d7c4` | `ConsumerUpdated(bytes32 indexed id, address indexed consumer, bool allowed)` |
| `0x478472ae68cd2ee2f27b7b2fd87796df3842c93689f7b4eeb814074d8fcd22df` | `UpdatedKeyValue(string tag, string key, string old_value, string new_value)` |
| `0x307f93ff30cf479b6f97913709eb42551f8e66576f32986b31a730bbbb10053b` | `UpdatedAdmin(string tag, address admin, bool allowed)` |
| `0x8b00ce48db245d0eb08e3afe42da49e72928dad89be0632e978e09be3f882a1e` | `PausedUntil(uint256 pausedUntil)` |
| `0x8784fe0ae276e6908b62d50821d4284cd661571cc8f5f8a44210ab80aee9f247` | `UnpausedUntil()` |
| `0x6ade74774117652c2866b462cae5a6e9e143be90c9e243e1f05013400006a241` | `PauseUntilDurationSet(uint256 pauseUntilDuration)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |

> The pause family (`PausedUntil`, `UnpausedUntil`, `PauseUntilDurationSet`) and `Paused`/`Unpaused`/`Upgraded` are emitted by **every** core proxy. Key them on the emitter address.

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

### 2.1 LiquidityPool
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xd0e30db0` | `deposit()` | payable -> (uint256) |
| `0xf340fa01` | `deposit(address)` | payable -> (uint256) |
| `0xf9609f08` | `deposit(address,address)` | payable -> (uint256) |
| `0xb46a130e` | `depositToRecipient(address,uint256,address)` | -> (uint256) |
| `0x397a1b28` | `requestWithdraw(address,uint256)` | -> (uint256) |
| `0x03dcfbdc` | `requestWithdrawWithPermit(address,uint256,(uint256,uint256,uint8,bytes32,bytes32))` | -> (uint256) |
| `0xf3fef3a3` | `withdraw(address,uint256)` | -> (uint256) |
| `0xb42f1320` | `rebase(int128,uint128)` | -> () |
| `0x1ee665c4` | `batchRegister((bytes,bytes,bytes32,string)[],uint256[],address)` | -> () |
| `0xbaaff116` | `confirmAndFundBeaconValidators((bytes,bytes,bytes32,string)[],uint256)` | -> () |
| `0xe74b981b` | `setFeeRecipient(address)` | -> () |
| `0x37cfdaca` | `getTotalPooledEther()` | view -> (uint256) |
| `0x561bddf8` | `amountForShare(uint256)` | view -> (uint256) |
| `0x3a53acb0` | `sharesForAmount(uint256)` | view -> (uint256) |
| `0x7c90fbf0` | `totalValueInLp()` | view -> (uint128) |
| `0x456a23a6` | `totalValueOutOfLp()` | view -> (uint128) |

### 2.2 eETH / weETH
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x528c198a` | `mintShares(address,uint256)` | -> () |
| `0xee7a7c04` | `burnShares(address,uint256)` | -> () |
| `0xea598cb0` | `wrap(uint256)` | -> (uint256) |
| `0x2c04709e` | `wrapWithPermit(uint256,(uint256,uint256,uint8,bytes32,bytes32))` | -> (uint256) |
| `0xde0e9a3e` | `unwrap(uint256)` | -> (uint256) |
| `0x679aefce` | `getRate()` | view -> (uint256) |
| `0x94626044` | `getEETHByWeETH(uint256)` | view -> (uint256) |
| `0xd044fe9b` | `getWeETHByeETH(uint256)` | view -> (uint256) |

### 2.3 Withdrawals
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xb8e38c2a` | `requestWithdraw(uint96,uint96,address)` | -> (uint256) |
| `0xb13acedd` | `claimWithdraw(uint256)` | -> () |
| `0x24fccdcf` | `batchClaimWithdraw(uint256[])` | -> () |
| `0x54768571` | `finalizeRequests(uint256)` | -> () |
| `0xb9907174` | `invalidateRequest(uint256)` | -> () |
| `0xe27d067b` | `validateRequest(uint256)` | -> () |
| `0x554e34f7` | `seizeInvalidRequest(uint256,address)` | -> () |
| `0x6dcc078e` | `redeemEEth(uint256,address,address)` | -> () |
| `0x50cd3742` | `redeemWeEth(uint256,address,address)` | -> () |
| `0x091ecfce` | `redeemEEthWithPermit(uint256,address,(uint256,uint256,uint8,bytes32,bytes32),address)` | -> () |
| `0xb6185713` | `redeemWeEthWithPermit(uint256,address,(uint256,uint256,uint8,bytes32,bytes32),address)` | -> () |
| `0x47de9bb8` | `requestWithdraw(uint96,uint96)` | -> (bytes32) |
| `0x27957a42` | `requestWithdrawWithWeETH(uint96,uint96)` | -> (bytes32) |
| `0x49ffec05` | `claimWithdraw((address,uint96,uint96,uint96,uint32,uint32))` | -> () |
| `0x493e0362` | `fulfillRequests((address,uint96,uint96,uint96,uint32,uint32)[])` | -> () |
| `0xd5e625f5` | `cancelWithdraw((address,uint96,uint96,uint96,uint32,uint32))` | -> (bytes32) |
| `0xccc143b8` | `requestWithdraw(uint256,address)` | -> (uint256) |

### 2.4 Oracle and admin
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xcaf0216d` | `submitReport((uint32,uint32,uint32,uint32,uint32,int128,uint128,uint256[],uint32,uint128))` | -> (bool) |
| `0x1956761e` | `unpublishReport((uint32,uint32,uint32,uint32,uint32,int128,uint128,uint256[],uint32,uint128),address[])` | -> () |
| `0xa699ab2e` | `addCommitteeMember(address,uint32)` | -> () |
| `0xa1875df2` | `removeCommitteeMember(address,uint32)` | -> () |
| `0xdd05ddde` | `setQuorumSize(uint32)` | -> () |
| `0x2e03931e` | `executeTasks((uint32,uint32,uint32,uint32,uint32,int128,uint128,uint256[],uint32,uint128))` | -> () |
| `0x317627e3` | `executeValidatorApprovalTask(bytes32,uint256[],bytes[],bytes[])` | -> () |
| `0xa4aa71e7` | `setMaxNegativeRebaseBps(uint256)` | -> () |
| `0x0e2e65f6` | `updateAcceptableRebaseApr(int32)` | -> () |

### 2.5 Validators, deposits, restaking
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xb71205d4` | `createBeaconValidators((bytes,bytes,bytes32,string)[],uint256[],address)` | payable -> () |
| `0xf8ac3872` | `registerBeaconValidators((bytes,bytes,bytes32,string)[],uint256[],address)` | -> () |
| `0xbaaff116` | `confirmAndFundBeaconValidators((bytes,bytes,bytes32,string)[],uint256)` | payable -> () |
| `0xaeeb9556` | `instantiateEtherFiNode(bool)` | -> (address) |
| `0x49370974` | `upgradeEtherFiNode(address)` | -> () |
| `0x297fdfe4` | `forwardEigenPodCall(address[],bytes[])` | -> (bytes[]) |
| `0x9fab3743` | `forwardExternalCall(address[],bytes[],address)` | -> (bytes[]) |
| `0xc390d8f5` | `requestExecutionLayerTriggeredWithdrawal((bytes,uint64)[])` | payable -> () |
| `0x6691954e` | `requestConsolidation((bytes,bytes)[])` | payable -> () |
| `0x03f49be8` | `queueETHWithdrawal(address,uint256)` | -> (bytes32) |
| `0x0fe28908` | `sweepFunds(address)` | -> () |
| `0x2990b9ef` | `depositWithERC20(address,uint256,uint256,address)` | -> (uint256) |
| `0x81a4090d` | `depositWithERC20WithPermit(address,uint256,uint256,address,(uint256,uint256,uint8,bytes32,bytes32))` | -> (uint256) |
| `0x48b40210` | `sendToEtherFiRestaker(address,uint256)` | -> () |
| `0xef54591d` | `depositETHForWeETH(address)` | payable -> (uint256) |
| `0xe5ce314c` | `depositWETHForWeETH(uint256,address)` | -> (uint256) |
| `0xc951ccf0` | `depositStETHForWeETHWithPermit(uint256,uint256,address,(uint256,uint256,uint8,bytes32,bytes32))` | -> (uint256) |
| `0xa0d43d8d` | `depositWstETHForWeETHWithPermit(uint256,uint256,address,(uint256,uint256,uint8,bytes32,bytes32))` | -> (uint256) |
| `0x04cb66f4` | `stEthRequestWithdrawal(uint256)` | -> (uint256[]) |
| `0x8e97dff1` | `stEthClaimWithdrawals(uint256[],uint256[])` | -> () |
| `0xd7b10412` | `queueWithdrawals(address,uint256)` | -> (bytes32[]) |
| `0xeea9064b` | `delegateTo(address,(bytes,uint256),bytes32)` | -> () |
| `0x92ab89bb` | `undelegate()` | -> (bytes32[]) |

### 2.6 Governance
| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x5978cd29` | `setRole(address,uint256,bool)` | payable -> () |
| `0x2f2ff15d` | `grantRole(bytes32,address)` | -> () |
| `0xd547741f` | `revokeRole(bytes32,address)` | -> () |
| `0x01d5062a` | `schedule(address,uint256,bytes,bytes32,bytes32,uint256)` | -> () |
| `0x8f2a0bb0` | `scheduleBatch(address[],uint256[],bytes[],bytes32,bytes32,uint256)` | -> () |
| `0x134008d3` | `execute(address,uint256,bytes,bytes32,bytes32)` | payable -> () |
| `0xe38335e5` | `executeBatch(address[],uint256[],bytes[],bytes32,bytes32)` | payable -> () |
| `0xc4d252f5` | `cancel(bytes32)` | -> () |
| `0x3659cfe6` | `upgradeTo(address)` | -> () |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | payable -> () |
| `0x7e3db158` | `pauseUntil()` | -> () |
| `0x25ae2781` | `unpauseUntil()` | -> () |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified with `eth_getCode` (non-empty) on 2026-10-30. "UUPS" = `ERC1967Proxy` with an empty admin slot. The impl column is the live EIP-1967 implementation slot.

| Role | Address | Pattern → impl (2026-10-30) |
|------|---------|-----------------------------|
| **LiquidityPool** | `0x308861A430be4cce5502d0A12724771Fc6DaF216` | UUPS → `0x17a16747d03006c9754548ac0d0aff48783a4a45` |
| **eETH** | `0x35fA164735182de50811E8e2E824cFb9B6118ac2` | UUPS → `0xd1901dd36cbf4a81386d0162df2707f7ddb60527` |
| **weETH** | `0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee` | UUPS → `0xa6ca0607190d03cf16fe6f2865cf40c3d160ccf3` |
| **WithdrawRequestNFT** | `0x7d5706f6ef3F89B3951E23e557CDFBC3239D4E2c` | UUPS → `0x41617d01362770ebaac10311ab899fbc8a4e4a7e` |
| **EtherFiRedemptionManager** | `0xDadEf1fFBFeaAB4f68A9fD181395F68b4e4E7Ae0` | UUPS → `0x5d53b303d62a7861f88650045b8d5deb59dfb3dc` |
| **PriorityWithdrawalQueue** | `0x35e7D6feF6f72aDd3c3e39dEc6d9CCc29e3345FA` | UUPS → `0x77b929befe793367712c0c28ca8e857bf23a2296` |
| WeETHWithdrawAdapter | `0xFbfe6b9cEe0E555Bad7e2E7309EFFC75200cBE38` | UUPS → `0xbe386b1fb51ffacae0522a5da099371cd4a2aaea` |
| EtherFiRateLimiter | `0x6C7c54cfC2225fA985cD25F04d923B93c60a02F8` | UUPS → `0x9ea4d0fd09b628e23b1998f2153e27e5261b1b67` |
| **EtherFiOracle** | `0x57AaF0004C716388B21795431CD7D5f9D3Bb6a41` | UUPS → `0x0565c8ea133ff27ba9d471330a52068a268a2b9e` |
| **EtherFiAdmin** | `0x0EF8fa4760Db8f5Cd4d993f3e3416f30f942D705` | UUPS → `0x841fa691aa6e30e97c817608f90111701a3d0ac8` |
| **StakingManager** | `0x25e821b7197B146F7713C3b89B6A4D83516B912d` | UUPS → `0x6515b41bdcf83be5543b88591bc0bc34d844c9c2` |
| **EtherFiNodesManager** | `0x8B71140AD2e5d1E7018d2a7f8a288BD3CD38916F` | UUPS → `0x020016fa077515451975712595eb3e984907ad3b` |
| EtherFiNode beacon | `0x3c55986Cfee455E2533F4D29006634EcF9B7c03F` | `UpgradeableBeacon` (owner = StakingManager) → `0x73df4a005332525fb0a0b2cf067352a9b706f233` |
| NodeOperatorManager | `0xd5edf7730ABAd812247F6F54D7bd31a52554e35E` | UUPS → `0x2474d68d6e9f7be77c9a343ce21dbe16f0743bd3` |
| AuctionManager | `0x00C452aFFee3a17d9Cecc1Bcd2B8d5C7635C4CB9` | UUPS → `0x3311c72a04d2779f4425c036dbc40d14fec0162b` |
| EtherFiAvsOperatorsManager | `0x2093Bbb221f1d8C7c932c32ee28Be6dEe4a37A6a` | UUPS → `0xa4c83200e0c9a61296c63333f2bd22559058852e` |
| EtherFiRestaker | `0x1B7a4C3797236A1C37f8741c0Be35c2c72736fFf` | UUPS → `0x51357a700b309637f109a897a6479a563d5afb8e` |
| RestakingRewardsRouter | `0x89E45081437c959A827d2027135bC201Ab33a2C8` | UUPS → `0x6bf6acd4b22795080c719d987baa8f4fcb1ab3f8` |
| Liquifier | `0x9FFDF407cDe9a93c47611799DA23924Af3EF764F` | UUPS → `0x263a74e56eb07c2a2a84fd510615a17b66e10e70` |
| DepositAdapter | `0xcfC6d9Bd7411962Bfe7145451A7EF71A24b6A7A2` | UUPS → `0xe774e19f087523ea316fccb4b156169153f18b9d` |
| EtherFiRewardsRouter | `0x73f7b1184B5cD361cC0f7654998953E2a251dd58` | UUPS → `0xcb9614b005f11f7781e92ff2b4a9aebfaeb33e76` |
| CumulativeMerkleRewardsDistributor | `0x9A8c5046a290664Bf42D065d33512fe403484534` | UUPS → `0x9eb91bd087ff6381e2497e54fd796c6a166e6a8a` |
| KING distributor (`CumulativeMerkleDrop`) | `0x6Db24Ee656843E3fE03eb8762a54D86186bA6B64` | UUPS → `0x5e226b1de8b0f387d7c77f78cba2571d2a1be511` |
| MembershipManager | `0x3d320286E014C3e1ce99Af6d6B00f0C1D63E3000` | UUPS → `0xa9dbe5c7c8172ef83a30c143892e0010420e6307` |
| MembershipNFT | `0xb49e4420eA6e35F98060Cd133842DbeA9c27e479` | UUPS → `0xd43d99df3d42675ce126a7cff8f7dff037620851` |
| **RoleRegistry** | `0x62247D29B4B9BECf4BB73E0c722cf6445cfC7cE9` | UUPS → `0x3b44a093b9736af765f98f3245998f63bc757970`; `owner()` = Upgrade Timelock |
| **Upgrade Timelock** | `0x9f26d4C958fD811A1F59B01B86Be7dFFc9d20761` | OZ `TimelockController` (`EtherFiTimelock`), min delay 10 days |
| **Operating Timelock** | `0xcD425f44758a08BaAB3C4908f3e3dE5776e45d7a` | OZ `TimelockController`, min delay 2 days |
| Blacklister | `0x5585996E7cFE95f2D99e61168B8b35C66Ff99B18` | UUPS → `0xbc870c47c6eb10009a0720e76f166f104c124ecf` |
| RevokeAdmin | `0x4A84BA0b5e716b37C78D0F5094757205626C7C1e` | UUPS → `0x5a765826700cf3a918eb713b3a7978e9333085df` |
| EtherFiOperationParameters | `0xD0Ff8996DB4bDB46870b7E833b7532f484fEad1A` | UUPS → `0xd6e217bf5083e4af4046979e926dc486bafd1c6a` |
| EtherFiViewer (read helper) | `0x2ecd155405cA52a5ca0e552981fF44A8252FAb81` | UUPS → `0x19c10a7e39d5457c4a3cb2c8909297d6020594d7` |
| AddressProvider | `0x8487c5F8550E3C3e7734Fe7DCF77DB2B72E4A848` | immutable registry (`ContractAdded`/`ContractRemoved`) |
| Treasury | `0x0c83EAe1FE72c390A02E426572854931EefF93BA` | Safe proxy |
| BNFT / TNFT (legacy) | `0x6599861e55abd28b91dd9d86A826eC0cC8D72c2c` / `0x7B5ae07E2AF1C861BcC4736D23f5f66A61E0cA5e` | UUPS (ERC-721 per validator) |
| Early Adopter Pool (legacy) | `0x7623e9DC0DA6FF821ddb9EbABA794054E078f8c4` | immutable |
| **ETHFI** | `0xFe0c30065B384F05761f15d0CC899D4F9F9Cc0eB` | immutable `ERC20Votes` (7,889 B) |
| sETHFI (Staked ETHFI) | `0x86B5780b606940Eb59A062aA85a07959518c0161` | immutable `BoringGovernance` (BoringVault family: `Enter`/`Exit`). Same literal on Base/Arbitrum/OP (see [liquid.md](liquid.md)) |

---

## 4. Cross-chain summary

| Chain | ID | Staking core (LiquidityPool, eETH, oracle, validators, withdrawals) | weETH |
|-------|----|---------------------------------------------------------------------|-------|
| Ethereum | 1 | ✓ (this file) | native `0xCd5f…b7ee` |
| Base / BNB / Avalanche / Arbitrum / Optimism / Robinhood Chain / Arc | 8453 / 56 / 43114 / 42161 / 10 / 4663 / 5042 | — (every §3 literal checked with `eth_getCode`; two non-matching collisions, see §6 item 11) | bridged; see [weeth-crosschain.md](weeth-crosschain.md) |
| Polygon PoS | 137 | — | — (no weETH deployment; no literal from the official list has code) |

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| LiquidityPool, eETH, weETH, withdrawal stack, oracle, admin, StakingManager, NodesManager, AuctionManager, NodeOperatorManager, Liquifier, DepositAdapter, Restaker, rewards, RateLimiter, Blacklister, RevokeAdmin | UUPS `ERC1967Proxy` | impl slot set, admin slot `0x0` | `_authorizeUpgrade` uses `onlyUpgradeTimelock`: the caller must hold `UPGRADE_TIMELOCK_ROLE` in RoleRegistry (the Upgrade Timelock `0x9f26…0761`, which is also `RoleRegistry.owner()`) |
| MembershipManager, MembershipNFT, BNFT, TNFT, EtherFiAvsOperatorsManager | UUPS `ERC1967Proxy` | impl slot set | Ownable: `owner()` = Upgrade Timelock `0x9f26…0761` (read live) |
| KING distributor, EtherFiOperationParameters, EtherFiViewer | UUPS `ERC1967Proxy` | impl slot set | Ownable: `owner()` = `0xa000244b…cd52`, `0x2aca7102…8adc` (L1 controller Safe), `0xf8a86ea1…421e` |
| EtherFiNode instances | Beacon proxy | beacon `0x3c55…c03F` | `StakingManager.upgradeEtherFiNode(address)` (beacon owner = StakingManager) |
| Upgrade / Operating Timelock | immutable | impl slot `0x0` | self-governed (`updateDelay`) |
| ETHFI, AddressProvider, Early Adopter Pool, sETHFI | immutable | impl slot `0x0` | — |

Watch topic `Upgraded(address)` = `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` on every proxy, and `BeaconUpgraded`/`Upgraded` on the node beacon. A new `CallScheduled` on the Upgrade Timelock gives 10 days of warning.

---

## 6. Detection invariants & gotchas

1. **Two `WithdrawRequestCreated` and two `WithdrawRequestClaimed` topics.** WithdrawRequestNFT uses `uint32 indexed requestId` (`0xe8c5…ab22`, `0x3171…4921`). PriorityWithdrawalQueue uses `bytes32 indexed requestId` (`0x615c…83fb`, `0x3327…27c9`). Key on the emitter.
2. **eETH balances move without `Transfer`.** A rebase changes every balance but emits only `LiquidityPool.Rebase`. Track shares with `TransferShares` and convert with `amountForShare()`.
3. **A rebase can be negative.** `rebase(int128,uint128)` takes a signed accrual. `EtherFiAdmin.setMaxNegativeRebaseBps` caps it. Alert on a drop of `totalEthLocked/totalEEthShares` between two `Rebase` events.
4. **The oracle report hash links the flow.** `ReportSubmitted(…, hash, committeeMember)` per member → `ReportPublished(…, hash)` at quorum → `AdminOperationsExecuted(caller, reportHash)`. A `ReportUnpublished` is a rare admin action.
5. **`Deposit` topic0 collides.** `LiquidityPool.Deposit(address,uint256,uint8,address)` is unique, but `Deposit` names recur in the L2 sync pools, Liquid tellers and Cash. Key on the emitter.
6. **Instant redemption drains the pool buffer.** `Redeemed(receiver, amount, feeToTreasury, feeToStakers, token)` on the RedemptionManager draws ETH (or stETH) from `LiquidityPool`. Watch large values and the `EtherFiRateLimiter` `RemainingUpdated` values.
7. **The pause family is shared.** `PausedUntil`/`UnpausedUntil`/`PauseUntilDurationSet` have one topic0 on every core contract. `pauseUntil()` is a time-boxed pause by a pauser role. A full `pause()` emits OZ `Paused(address)`.
8. **`AdminOperationsExecuted` is from `EtherFiAdmin`, not the oracle.** The oracle only reaches consensus. The admin contract executes.
9. **Validator flow (post-Pectra).** `StakingManager.createBeaconValidators` → `validatorCreated` → oracle approval (`ValidatorApprovalTaskCreated/Completed`) → `confirmAndFundBeaconValidators` → `validatorConfirmed`. `EtherFiNodesManager.requestExecutionLayerTriggeredWithdrawal` emits `ValidatorWithdrawalRequestSent` (EIP-7002 exits).
10. **Restaking is winding down.** The official page marks EigenLayer contracts as "winding down". `EtherFiRestaker.QueuedStEthWithdrawals` / `CompletedStEthQueuedWithdrawals` show the stETH exit.
11. **No core contract exists on the other eight chains.** Every §3 literal was checked on all eight. Two literals have unrelated code: Optimism `0x3088…F216` (LiquidityPool literal) holds a 145 B stub with one function `0xe4085d67`. Base `0x3d32…3000` (MembershipManager literal) holds a 16,738 B uninitialised OFT-style token (`name()` empty, `owner()` = 0). Neither is ether.fi core. A weETH balance on an L2 is a bridged token. It never emits `Rebase`. The L2 rate comes from an exchange-rate provider (see [weeth-crosschain.md](weeth-crosschain.md)).

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_LP_DEPOSIT                 = '\xa241faf62e66ce518d1934ce4c936d806a02289ba483fac23beb8c15755be90d'
TOPIC_LP_WITHDRAW                = '\xb9da3f3df62c28aca604806cc6ee9678189d7591ef511a77bb040fa8361e9e02'
TOPIC_LP_REBASE                  = '\x11c6bf55864ff83827df712625d7a80e5583eef0264921025e7cd22003a21511'
TOPIC_LP_PROTOCOL_FEE_PAID       = '\xafea3ee583ed00355634c0a2f47d947b6af95fda2bc1dbe0ff919c45166789d4'
TOPIC_EETH_TRANSFER_SHARES       = '\x9d9c909296d9c674451c0c24f02cb64981eb3b727f99865939192f880a755dcb'
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_WRNFT_REQUEST_CREATED      = '\xe8c5062a529781e00d69c769270eb1f1ae6feb921aa80d238bb7b4b919b1ab22'
TOPIC_WRNFT_REQUEST_CLAIMED      = '\x31712d805743a128cf0ab8cdf453da51797d2e6f674bd1e5d77d92e1518e4921'
TOPIC_WRNFT_REQUEST_INVALIDATED  = '\xd1438bf0c355cea90a9b9659e0a0455232d0e6da85797802b4c73778f1e35f13'
TOPIC_WRNFT_REQUEST_SEIZED       = '\x8f13b46229b7bc68329da7a7aec3a926547f0cbb2e5379d36e1310e81052b8f6'
TOPIC_PWQ_REQUEST_CREATED        = '\x615cd1d10af2a795928a8c024915afa7a5f55a75649c20c229927b7324d583fb'
TOPIC_PWQ_REQUEST_FINALIZED      = '\xea76945910833f2b555afc61af3d06074e7852b48692257f97679d06125fe599'
TOPIC_PWQ_REQUEST_CLAIMED        = '\x332728ddcc0f3fec463b84f56fa3120c3725819441c4e321bf5b806d0d0527c9'
TOPIC_REDEMPTION_REDEEMED        = '\xc733e5de6c9a33d3ad4494396148842e6b8788ce5161d4d96ff548de6019fc60'
TOPIC_ORACLE_REPORT_SUBMITTED    = '\xe6f12615b1560447dc4b63bb3fb30c998c4839bbee68d976818a929cb8fd8bba'
TOPIC_ORACLE_REPORT_PUBLISHED    = '\x806d044a61ac7edf13f9a0f3dc1846baec3dd94bddee1c6d9f4e7d4841a546b0'
TOPIC_ORACLE_REPORT_UNPUBLISHED  = '\x8dc002c973d20ab13619cad899c28edb1048a9d6b4ba5488a32e2d27d0a0acb2'
TOPIC_ORACLE_QUORUM_UPDATED      = '\x9795472303adc5267a6814dd0c9fc79c467be77de1f44a519881eba38ae7586c'
TOPIC_ADMIN_OPS_EXECUTED         = '\x997abd9d07db6cb25b8542e4fe05ddc887fc249d15d5ec7e3089ff385012bd2f'
TOPIC_ADMIN_MAX_NEG_REBASE       = '\x44734f20d91c4e391841c482f8a511327a6a1a88b72864f0454a170fae3597e9'
TOPIC_SM_VALIDATOR_CREATED       = '\x145257af791e94a9baa6d143d80bb91506202de6e8b49814e221785063248a1b'
TOPIC_SM_VALIDATOR_CONFIRMED     = '\x8150d115af2aea30a11022232987b82d5e748d48efba6addc26c07377c399a48'
TOPIC_NM_WITHDRAWAL_REQUEST_SENT = '\xc5e91e7c1c052841cfdff96be1fea6a3e62b51af6008c70efcdf792468c90f90'
TOPIC_NM_FUNDS_TRANSFERRED       = '\x8c9a4f13b67cb64d7c6aa1ae0c9bf07694af521a28b93e7060020810ab4bc59f'
TOPIC_LIQUIFIER_LIQUIFIED        = '\x2c19962a366d611900b92f328f12302cf959ee57063a989a1869fc342220ed50'
TOPIC_ADAPTER_DEPOSIT            = '\x82519d66329d63e603ccc585294982e01a733deb1a52cd22912323b5b8ebb655'
TOPIC_MERKLE_CLAIMED             = '\xf7a40077ff7a04c7e61f6f26fb13774259ddf1b6bce9ecf26a8276cdd3992683'
TOPIC_ROLE_SET                   = '\xaddc47d7e02c95c00ec667676636d772a589ffbf0663cfd7cd4dd3d4758201b8'
TOPIC_TIMELOCK_CALL_SCHEDULED    = '\x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca'
TOPIC_TIMELOCK_CALL_EXECUTED     = '\xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58'
TOPIC_BLACKLISTED_UNTIL          = '\x5ffe8aa215ff509a8b962d6db75a6ad3024ef4d9a4ffa79612eafcd44ef0f52b'
TOPIC_PAUSED_UNTIL               = '\x8b00ce48db245d0eb08e3afe42da49e72928dad89be0632e978e09be3f882a1e'
TOPIC_PAUSED                     = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors (chain-agnostic) =====
SEL_LP_DEPOSIT                   = '\xd0e30db0'
SEL_LP_DEPOSIT_REFERRAL          = '\xf340fa01'
SEL_LP_REQUEST_WITHDRAW          = '\x397a1b28'
SEL_LP_REBASE                    = '\xb42f1320'
SEL_WEETH_WRAP                   = '\xea598cb0'
SEL_WEETH_UNWRAP                 = '\xde0e9a3e'
SEL_WEETH_GET_RATE               = '\x679aefce'
SEL_WRNFT_CLAIM                  = '\xb13acedd'
SEL_WRNFT_FINALIZE               = '\x54768571'
SEL_REDEEM_EETH                  = '\x6dcc078e'
SEL_REDEEM_WEETH                 = '\x50cd3742'
SEL_ORACLE_SUBMIT_REPORT         = '\xcaf0216d'
SEL_ADMIN_EXECUTE_TASKS          = '\x2e03931e'
SEL_PAUSE_UNTIL                  = '\x7e3db158'
SEL_UPGRADE_TO_AND_CALL          = '\x4f1ef286'
-- ===== Addresses (Ethereum, chain ID 1) =====
ETH_ETHERFI_LIQUIDITY_POOL       = '\x308861a430be4cce5502d0a12724771fc6daf216'
ETH_ETHERFI_EETH                 = '\x35fa164735182de50811e8e2e824cfb9b6118ac2'
ETH_ETHERFI_WEETH                = '\xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee'
ETH_ETHERFI_WITHDRAW_REQUEST_NFT = '\x7d5706f6ef3f89b3951e23e557cdfbc3239d4e2c'
ETH_ETHERFI_REDEMPTION_MANAGER   = '\xdadef1ffbfeaab4f68a9fd181395f68b4e4e7ae0'
ETH_ETHERFI_PRIORITY_WQ          = '\x35e7d6fef6f72add3c3e39dec6d9ccc29e3345fa'
ETH_ETHERFI_WEETH_WITHDRAW_ADPT  = '\xfbfe6b9cee0e555bad7e2e7309effc75200cbe38'
ETH_ETHERFI_ORACLE               = '\x57aaf0004c716388b21795431cd7d5f9d3bb6a41'
ETH_ETHERFI_ADMIN                = '\x0ef8fa4760db8f5cd4d993f3e3416f30f942d705'
ETH_ETHERFI_STAKING_MANAGER      = '\x25e821b7197b146f7713c3b89b6a4d83516b912d'
ETH_ETHERFI_NODES_MANAGER        = '\x8b71140ad2e5d1e7018d2a7f8a288bd3cd38916f'
ETH_ETHERFI_NODE_BEACON          = '\x3c55986cfee455e2533f4d29006634ecf9b7c03f'
ETH_ETHERFI_AUCTION_MANAGER      = '\x00c452affee3a17d9cecc1bcd2b8d5c7635c4cb9'
ETH_ETHERFI_NODE_OPERATOR_MGR    = '\xd5edf7730abad812247f6f54d7bd31a52554e35e'
ETH_ETHERFI_LIQUIFIER            = '\x9ffdf407cde9a93c47611799da23924af3ef764f'
ETH_ETHERFI_DEPOSIT_ADAPTER      = '\xcfc6d9bd7411962bfe7145451a7ef71a24b6a7a2'
ETH_ETHERFI_RESTAKER             = '\x1b7a4c3797236a1c37f8741c0be35c2c72736fff'
ETH_ETHERFI_REWARDS_ROUTER       = '\x73f7b1184b5cd361cc0f7654998953e2a251dd58'
ETH_ETHERFI_MERKLE_DISTRIBUTOR   = '\x9a8c5046a290664bf42d065d33512fe403484534'
ETH_ETHERFI_MEMBERSHIP_MANAGER   = '\x3d320286e014c3e1ce99af6d6b00f0c1d63e3000'
ETH_ETHERFI_MEMBERSHIP_NFT       = '\xb49e4420ea6e35f98060cd133842dbea9c27e479'
ETH_ETHERFI_RATE_LIMITER         = '\x6c7c54cfc2225fa985cd25f04d923b93c60a02f8'
ETH_ETHERFI_ROLE_REGISTRY        = '\x62247d29b4b9becf4bb73e0c722cf6445cfc7ce9'
ETH_ETHERFI_UPGRADE_TIMELOCK     = '\x9f26d4c958fd811a1f59b01b86be7dffc9d20761'
ETH_ETHERFI_OPERATING_TIMELOCK   = '\xcd425f44758a08baab3c4908f3e3de5776e45d7a'
ETH_ETHERFI_BLACKLISTER          = '\x5585996e7cfe95f2d99e61168b8b35c66ff99b18'
ETH_ETHERFI_TREASURY             = '\x0c83eae1fe72c390a02e426572854931eeff93ba'
ETH_ETHERFI_ETHFI                = '\xfe0c30065b384f05761f15d0cc899d4f9f9cc0eb'
ETH_ETHERFI_SETHFI               = '\x86b5780b606940eb59a062aa85a07959518c0161'
```

---

## 8. Verification & sources

How the constants were verified (2026-10-30):
- **Topic0 / selectors:** computed locally as `keccak256(signature)` from the verified implementation ABI of each proxy (impl address read from the EIP-1967 slot, ABI from the Blockscout verified-source API). Live presence was confirmed from explorer log pages (≤150 most recent logs per contract) and `eth_getLogs`: LiquidityPool (`Deposit` 64, `Withdraw` 60, `Rebase` 12, `ProtocolFeePaid` 12), oracle (`ReportSubmitted` 112, `ReportPublished` 38), EtherFiAdmin (`AdminOperationsExecuted` 125), StakingManager (`ValidatorCreationStatusUpdated` 147), WithdrawRequestNFT (`WithdrawRequestCreated` 48, `WithdrawRequestClaimed` 27), PriorityWithdrawalQueue (`WithdrawRequestFinalized` 50), RedemptionManager (`Redeemed` 148). Every observed topic0 decoded against the ABI with no unknowns.
- **Addresses:** the official Deployed Contracts list, existence-checked with `eth_getCode`. Impl/admin/beacon slots read with `eth_getStorageAt`. `RoleRegistry.owner()` and timelock `getMinDelay()` read with `eth_call`.
- **Chain coverage:** every §3 literal was checked on the other eight chains. None has staking-core code there.

Authoritative sources:
- [etherfi-protocol/smart-contracts](https://github.com/etherfi-protocol/smart-contracts) — source of truth for signatures.
- [ether.fi Deployed Contracts](https://etherfi.gitbook.io/etherfi/developers/contracts-and-integrations/deployed-contracts) · [Integration Guide](https://etherfi.gitbook.io/etherfi/developers/contracts-and-integrations/integration-guide)
- Explorers: [Etherscan](https://etherscan.io) · [Blockscout (Ethereum)](https://eth.blockscout.com)
