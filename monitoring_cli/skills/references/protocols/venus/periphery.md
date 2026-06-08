# Venus Periphery — Tokens, Governance & Oracle — Topics, Selectors, Addresses (Ethereum, Base, BNB, Arbitrum, Optimism; absent on Avalanche & Polygon)

**Status:** verified against live RPC on every chain with a deployment, the canonical `VenusProtocol/{venus-protocol,oracle,governance-contracts,token-bridge,protocol-reserve}` repos, and each contract's on-chain ABI (parsed from the repo `deployments/<network>/<Contract>.json` artifacts), on 2026-06-08. Every topic0/selector recomputed locally as `keccak256(canonical signature)`; high-frequency topics confirmed against live `eth_getLogs`; proxy slots read live via `eth_getStorageAt`.
**Scope:** the Venus periphery shared across the Core pool (BNB) and the Isolated pools (all chains): **XVS** token + **XVSVault** staking + **XVSBridge** (LayerZero OFT); **VAI** + **VAIController** + **VAIVault**; **VRT** + **VRTConverter**; **Prime** + **PrimeLiquidityProvider**; **Venus Governance** (GovernorBravoDelegator/Delegate + the three Timelocks) and the cross-chain **OmnichainProposalSender** / **OmnichainGovernanceExecutor**; **VTreasury/VTreasuryV8** + **ProtocolShareReserve**; and the **ResilientOracle** stack (ChainlinkOracle, RedStoneOracle, BinanceOracle, PythOracle + BoundValidator). Topics + selectors are **chain-agnostic**; addresses are **network-specific**. The vToken/Comptroller markets themselves are out of scope here (see the Venus Core / Isolated-pools docs).

Venus's canonical home is **BNB Smart Chain (56)** — that is the only chain that runs the Core pool, VAI (the protocol stablecoin), VRT (the legacy reward token), the full **GovernorBravo** governance with its three Timelocks, **OmnichainProposalSender** (the cross-chain proposal relay), and **all four oracle adapters** (Chainlink, RedStone, Binance, Pyth). XVS is **minted on BNB** and **bridged** to the other chains via a LayerZero OFT (`XVSProxyOFTSrc` on BNB locks XVS; `XVSProxyOFTDest` on each remote chain mints/burns the bridged XVS) — **each chain's XVS address is different** (no shared/vanity address). On every non-BNB chain, governance is **executed remotely**: `OmnichainGovernanceExecutor` receives a LayerZero message from BNB, queues it into that chain's local Normal/FastTrack/Critical Timelock, and executes it. **There is no GovernorBravo, no VAI, no VRT, and no on-chain voting on any chain except BNB.**

> **Five chains, two absent.** Venus periphery is deployed on **Ethereum (1), Base (8453), BNB (56), Arbitrum One (42161), Optimism (10)**. It is **NOT deployed on Avalanche C-Chain (43114) or Polygon PoS (137)** — `eth_getCode` returns `0x` for every Venus address on both, and neither has a deployment folder in any Venus repo. Recorded as a finding, not an omission (§N).

> **Most periphery is an upgradeable proxy; classify by three different patterns.** (1) The oracle stack, Prime/PLP, PSR, XVSBridgeAdmin, OmnichainExecutorOwner are **OpenZeppelin TransparentUpgradeableProxy** (EIP-1967 impl+admin slots populated; admin = a `DefaultProxyAdmin`). (2) XVSVaultProxy, GovernorBravoDelegator, VaiUnitroller, VAIVaultProxy, VRTConverterProxy are **Compound-style delegators** — the EIP-1967 slot is empty (`0x0`); the logic address lives in a plain getter (`implementation()` / `vaiControllerImplementation()` / `vaiVaultImplementation()`). (3) XVS (the bridged ERC-20), the two `XVSProxyOFT*` bridge endpoints, `OmnichainProposalSender`/`OmnichainGovernanceExecutor`, **and VTreasury/VTreasuryV8** are **immutable** (no impl slot — VTreasury/V8 are plain `Ownable` non-upgradeable contracts owned directly by the local NormalTimelock, verified: empty EIP-1967 impl+admin slots, no `implementation()` getter, `owner()` = the chain's NormalTimelock). See §N+1.

---

## 0. Contract families & versions

| Family | Contracts | Where |
|--------|-----------|-------|
| **Token** | XVS (ERC-20 / bridged ERC-20), XVSVault (staking + vote escrow), XVSStore (reward vault), XVSVesting (legacy) | XVS+Vault+Store on all 5; XVSVesting BNB-only |
| **Bridge (LayerZero OFT v1)** | XVSProxyOFTSrc (lock), XVSProxyOFTDest (mint/burn), XVSBridgeAdmin (proxy-admin/governance shim) | Src=BNB only; Dest=ETH/Base/Arb/OP; BridgeAdmin all 5 |
| **Stablecoin** | VAI (token), VAIController (mint/repay/liquidate, via VaiUnitroller delegator), VAIVault (stake VAI → XVS) | **BNB only** |
| **Legacy reward** | VRT (token), VRTConverter (VRT→XVS, via VRTConverterProxy), VRTVault | **BNB only** |
| **Prime (membership rewards)** | Prime (soulbound/revocable token + reward accrual), PrimeLiquidityProvider (PLP, funds Prime) | all 5 |
| **Governance** | GovernorBravoDelegate + GovernorBravoDelegator, NormalTimelock / FastTrackTimelock / CriticalTimelock | Bravo+all 3 Timelocks BNB-only; Timelocks ALSO exist on the 4 remote chains (driven by the executor, not Bravo) |
| **Cross-chain governance** | OmnichainProposalSender (BNB→remote relay), OmnichainGovernanceExecutor + OmnichainExecutorOwner | Sender=BNB only; Executor+Owner=ETH/Base/Arb/OP |
| **Treasury / fees** | VTreasury (BNB), VTreasuryV8 (remote chains), ProtocolShareReserve (PSR), ConverterNetwork + SingleTokenConverters + RiskFundV2 | VTreasury BNB / VTreasuryV8 remote; PSR all 5 |
| **Oracle** | ResilientOracle (aggregator), ChainlinkOracle, RedStoneOracle, BinanceOracle, PythOracle (adapters), BoundValidator | ResilientOracle/BoundValidator/RedStone all 5; ChainlinkOracle ETH/Base/BNB; Binance+Pyth BNB-only |

> **RedStoneOracle == ChainlinkOracle (same Solidity contract).** Venus has no separate RedStone Solidity file; the "RedStoneOracle" deployment is an instance of the **`ChainlinkOracle`** contract pointed at RedStone push-feeds (which expose the Chainlink `AggregatorV3Interface`). Both emit the identical `PricePosted` / `TokenConfigAdded` topic0s and have the same selectors. Disambiguate by **emitting address**, not by event.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak from each contract's on-chain ABI. Enum params (`IncomeType`, `Schema`, proposal type) are `uint8`; `proposalType` on the new Governor is `uint8`; `votes`/`balance` on the XVSVault delegate events are `uint256`.

### 1.1 XVS token (ERC-20 on BNB; bridged ERC-20 on remote chains)

The BNB XVS is a classic BEP-20 (`Transfer`/`Approval` only). The **remote-chain XVS** (`XVS.sol`, minted by the bridge) adds mint-cap/blacklist controls.

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | XVS (all chains) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | XVS (all chains) |
| `0x0831a8ba59684daef8a957d2bd2d943e233993771429e9a17b71ddb1cea35cdb` | `MintLimitIncreased(address indexed minter, uint256 newLimit)` | XVS (remote only) |
| `0xbe214d1fa2403a39be9a36c9f4b45125eba30bf27a8b56a619baf00493ad3e61` | `MintLimitDecreased(address indexed minter, uint256 newLimit)` | XVS (remote only) |
| `0x01a85f4ecff52e70907e25b863010bca98a9458d9f2fe9b3efb4c47d197e6448` | `MintCapChanged(address indexed minter, uint256 newCap)` | XVS (remote only) |
| `0x6a12b3df6cba4203bd7fd06b816789f87de8c594299aed5717ae070fac781bac` | `BlacklistUpdated(address indexed user, bool value)` | XVS (remote only) |

### 1.2 XVSVault (staking + vote-escrow; emitter = `XVSVaultProxy`)

| topic0 | Event |
|--------|-------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed user, address indexed rewardToken, uint256 indexed pid, uint256 amount)` |
| `0x88a254a0ef28a0b9e957ff600beae69870f6f924065147f3627c3f814e60ec11` | `RequestedWithdrawal(address indexed user, address indexed rewardToken, uint256 indexed pid, uint256 amount)` |
| `0xe31da05fae6db869f5ea51f4b638aa6884070b6c87f18f63bd2291a12cb2f518` | `ExecutedWithdrawal(address indexed user, address indexed rewardToken, uint256 indexed pid, uint256 amount)` |
| `0x865ca08d59f5cb456e85cd2f7ef63664ea4f73327414e9d8152c4158b0e94645` | `Claim(address indexed user, address indexed rewardToken, uint256 indexed pid, uint256 amount)` |
| `0xd7fa4bff1cd2253c0789c3291a786a6f6b1a3b4569a75af683a15d52abb6a0bf` | `PoolAdded(address indexed rewardToken, uint256 indexed pid, address indexed token, uint256 allocPoints, uint256 rewardPerBlockOrSecond, uint256 lockPeriod)` |
| `0x6ee09c6cb801194690c195c69f465aaf7c80255cbeafaab9600f47ed79de2ca9` | `PoolUpdated(address indexed rewardToken, uint256 indexed pid, uint256 oldAllocPoints, uint256 newAllocPoints)` |
| `0x0cc323ffec3ea49cbcddc0de1480978126d350c6a45dff33ad2f1cda6ae99261` | `DelegateChangedV2(address indexed delegator, address indexed fromDelegate, address indexed toDelegate)` |
| `0x6adb589fed1e8542fb7a6b10f00a85e02265e77f9ae3ca8ff93b22983e1af9a0` | `DelegateVotesChangedV2(address indexed delegate, uint256 previousBalance, uint256 newBalance)` |
| `0xad96cee0d692f0250b98e085504f399da6733854908215f6203fe3c69366d9f5` | `RewardAmountUpdated(address indexed rewardToken, uint256 oldReward, uint256 newReward)` |
| `0x0bcf80c5060ccf99b7a993c57a94b232fc2c5c04bd74c7c7d174595fee6bc31f` | `WithdrawalLockingPeriodUpdated(address indexed rewardToken, uint256 indexed pid, uint256 oldPeriod, uint256 newPeriod)` |
| `0x6bdfd5e51d01475945224d3d37965916fd8df699ef9e8888af4359aa86222160` | `VaultDebtUpdated(address indexed rewardToken, address indexed userAddress, uint256 oldOwedAmount, uint256 newOwedAmount)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` *(delegator pattern — same topic on Bravo/VaiUnitroller)* |

### 1.3 XVSBridge OFT (`XVSProxyOFTSrc` on BNB / `XVSProxyOFTDest` on remote chains — same event set)

| topic0 | Event |
|--------|-------|
| `0xd81fc9b8523134ed613870ed029d6170cbb73aa6a6bc311b9a642689fb9df59a` | `SendToChain(uint16 indexed dstChainId, address indexed from, bytes32 indexed toAddress, uint256 amount)` |
| `0xbf551ec93859b170f9b2141bd9298bf3f64322c6f7beb2543a0cb669834118bf` | `ReceiveFromChain(uint16 indexed srcChainId, address indexed to, uint256 amount)` |
| `0xe183f33de2837795525b4792ca4cd60535bd77c53b7e7030060bfcf5734d6b0c` | `MessageFailed(uint16 srcChainId, bytes srcAddress, uint64 nonce, bytes payload, bytes reason)` |
| `0x48a980eea4ea1c540209e2f9f32a4c2edf51fab37b1d21f453868301ecb6e2ee` | `DropFailedMessage(uint16 srcChainId, bytes srcAddress, uint64 nonce)` |
| `0xfa41487ad5d6728f0b19276fa1eddc16558578f5109fc39d2dc33c3230470dab` | `SetTrustedRemote(uint16 remoteChainId, bytes path)` |
| `0x8c0400cfe2d1199b1a725c78960bcc2a344d869b80590d0f2bd005db15a572ce` | `SetTrustedRemoteAddress(uint16 remoteChainId, bytes remoteAddress)` |
| `0x9d5c7c0b934da8fefa9c7760c98383778a12dfbfc0c3b3106518f43fb9508ac0` | `SetMinDstGas(uint16 dstChainId, uint16 type, uint256 minDstGas)` |
| `0x4dd31065e259d5284e44d1f9265710da72eafcf78dc925e3881189fc3b71f693` | `SetMaxDailyLimit(uint16 chainId, uint256 oldMaxLimit, uint256 newMaxLimit)` |
| `0x7babeac42ccbb33537ee421fedc4db7b5f251b5d2a3fa5c0ff4b35b2d783be87` | `SetMaxSingleTransactionLimit(uint16 chainId, uint256 oldLimit, uint256 newLimit)` |
| `0xf6019ec0a78d156d249a1ec7579e2321f6ac7521d6e1d2eacf90ba4a184dcceb` | `SetWhitelist(address addr, bool whitelisted)` |

> Venus's `SendToChain` is the **custom 4-arg** form `(uint16,address,bytes32,uint256)` (topic0 `0xd81fc9b8…`), **not** the stock LayerZero OFTCore `SendToChain(uint16,bytes32,uint256)`. `XVSBridgeAdmin` (the proxy admin) emits `FunctionRegistryChanged(string,bool)` `0x9d424e54f4d851aabd288f6cc4946e5726d6b5c0e66ea4ef159a3c40bcc470fa`.

### 1.4 VAIController (BNB only; emitter = `VaiUnitroller` `0x0040…FAFE`)

| topic0 | Event |
|--------|-------|
| `0x002e68ab1600fc5e7290e2ceaa79e2f86b4dbaca84a48421e167e0b40409218a` | `MintVAI(address minter, uint256 mintVAIAmount)` |
| `0x1db858e6f7e1a0d5e92c10c6507d42b3dabfe0a4867fe90c5a14d9963662ef7e` | `RepayVAI(address payer, address borrower, uint256 repayVAIAmount)` |
| `0x42d401f96718a0c42e5cea8108973f0022677b7e2e5f4ee19851b2de7a0394e7` | `LiquidateVAI(address liquidator, address borrower, uint256 repayAmount, address vTokenCollateral, uint256 seizeTokens)` |
| `0xb0715a6d41a37c1b0672c22c09a31a0642c1fb3f9efa2d5fd5c6d2d891ee78c6` | `MintFee(address minter, uint256 feeAmount)` |
| `0x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d` | `NewComptroller(address oldComptroller, address newComptroller)` |
| `0x43862b3eea2df8fce70329f3f84cbcad220f47a73be46c5e00df25165a6e1695` | `NewVAIMintCap(uint256 oldMintCap, uint256 newMintCap)` |
| `0x0893f8f4101baaabbeb513f96761e7a36eb837403c82cc651c292a4abdc94ed7` | `NewTreasuryPercent(uint256 oldTreasuryPercent, uint256 newTreasuryPercent)` |

### 1.5 VAIVault (BNB only)

| topic0 | Event |
|--------|-------|
| `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | `Deposit(address indexed user, uint256 amount)` |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | `Withdraw(address indexed user, uint256 amount)` |
| `0xdffada2889ebfab9224c24069d833f3de835d8cf99872d49e7b7ba5fccb7a46f` | `VaultPaused(address indexed admin)` |
| `0xd2619572a1464e0df0bb351d834fd47f3350984d7bfdb1ab69cfcb0b8e421415` | `VaultResumed(address indexed admin)` |

> **`Deposit(address,uint256)` topic0 `0xe1fffcc4…` is shared by VAIVault, VRTVault, and the legacy XVSVault V1**; the current XVSVault uses the 4-arg `Deposit` `0xdcbc1c05…` (§1.2). Disambiguate by emitter.

### 1.6 Prime + PrimeLiquidityProvider (all 5 chains)

| topic0 | Event | Contract |
|--------|-------|----------|
| `0xdd032f28700d4e4b1719b8fa26918a7d68608b4e36def571ce5fe7a3ecd69f45` | `Mint(address indexed user, bool isIrrevocable)` | Prime |
| `0xe22de1457cb61fb61b60176bc4235a9abd19466126b46692bc14fc573f099249` | `Burn(address indexed user)` | Prime |
| `0xc7edf5cfe443c04a10a60ff6084c847114348c55b257a01d62700326219adbba` | `InterestClaimed(address indexed user, address indexed market, uint256 amount)` | Prime |
| `0x1322eaea77217179bf4ef6084dc2f48c897e0d5a6b8365213804360e4d8ba9a2` | `MarketAdded(address indexed comptroller, address indexed market, uint256 supplyMultiplier, uint256 borrowMultiplier)` | Prime |
| `0x6c52f3e195bdc534883e903e0612c49261a466aacd492501870b0a0ac0b18355` | `MintLimitsUpdated(uint256 indexed oldIrrevocableLimit, uint256 indexed oldRevocableLimit, uint256 indexed newIrrevocableLimit, uint256 newRevocableLimit)` | Prime |
| `0x09d2594e8892daceca055f74be758146a8b8b1167444d0b4ccb96e74168198cc` | `StakedAtUpdated(address indexed user, uint256 timestamp)` | Prime |
| `0x5272e69bcef8da96614ac4a5d1e95ca02c35ea627bf7ecf389ec88d8d78b86bb` | `TokenUpgraded(address indexed user)` | Prime |
| `0xa699df4aa8f89fc1f5408fe78ae114651f18b25ed1601680e4c70c15177d8b1b` | `UserScoreUpdated(address indexed user)` | Prime |
| `0x2a139b40b9bf8c89ae5053746323912620b9d8ea3b076b098b1bc57702abf3a5` | `TokenDistributionSpeedUpdated(address indexed token, uint256 oldSpeed, uint256 newSpeed)` | PLP |
| `0xfe854c4c4e633d5bb31aec1f39f01d9f8f01ad2e0212a0e576825ac986af0589` | `TokensAccrued(address indexed token, uint256 amount)` | PLP |
| `0xa80c25cc8959419d41ee66f93961c567b272badc10e0e117261a0ee31b55c312` | `TokenTransferredToPrime(address indexed token, uint256 amount)` | PLP |
| `0xcf4d0ac7a2f943727f0189dd1f26ba0cde29a1b14f222163ac866d4f5167db94` | `PrimeTokenUpdated(address indexed oldPrimeToken, address indexed newPrimeToken)` | PLP |

### 1.7 GovernorBravo (BNB only; emitter = `GovernorBravoDelegator` `0x2d56…c75a`)

| topic0 | Event |
|--------|-------|
| `0xc8df7ff219f3c0358e14500814d8b62b443a4bebf3a596baa60b9295b1cf1bde` | `ProposalCreated(uint256 id, address proposer, address[] targets, uint256[] values, string[] signatures, bytes[] calldatas, uint256 startBlock, uint256 endBlock, string description, uint8 proposalType)` — **current (Bravo) form** |
| `0x7d84a6263ae0d98d3329bd7b46bb4e8d6f98cd35a7adb45c274c8b7fd5ebd5e0` | `ProposalCreated(…,string description)` — **legacy 9-arg form (no proposalType)**, still in the delegator ABI for old proposals |
| `0xb8e138887d0aa13bab447e82de9d5c1777041ecd21ca36ba824ff1e6c07ddda4` | `VoteCast(address indexed voter, uint256 proposalId, uint8 support, uint256 votes, string reason)` |
| `0x789cf55be980739dad1d0699b93b58e806b51c9d96619bfa8fe0a28abaa7b30c` | `ProposalCanceled(uint256 id)` |
| `0x9a2e42fd6722813d69113e7d0079d3d940171428df7373df9c7f7617cfda2892` | `ProposalQueued(uint256 id, uint256 eta)` |
| `0x712ae1383f79ac853f8d882153778e0260ef8f03b504e2866e0593e04d2b291f` | `ProposalExecuted(uint256 id)` |
| `0xccb45da8d5717e6c4544694297c4ba5cf151d455c9bb0ed4fc7a38411bc05461` | `ProposalThresholdSet(uint256 oldProposalThreshold, uint256 newProposalThreshold)` |
| `0xc565b045403dc03c2eea82b81a0465edad9e2e7fc4d97e11421c209da93d7a93` | `VotingDelaySet(uint256 oldVotingDelay, uint256 newVotingDelay)` |
| `0x7e3f7f0708a84de9203036abaa450dccc85ad5ff52f78c170f3edb55cf5e8828` | `VotingPeriodSet(uint256 oldVotingPeriod, uint256 newVotingPeriod)` |
| `0x99382998f89cd4c8aec7ae5d6deca4b4b0bfa01691740ccd702bf76b6a6816d2` | `SetProposalConfigs(uint256 votingPeriod, uint256 votingDelay, uint256 proposalThreshold)` *(per-route config)* |
| `0xc90c7ad68c13a491443f1c63dafa18b365428ee69170415afe234c16dc6f650d` | `SetValidationParams(uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256)` |
| `0x08fdaf06427a2010e5958f4329b566993472d14ce81d3f16ce7f2a2660da98e3` | `NewGuardian(address oldGuardian, address newGuardian)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` |

> Venus Governor routes proposals by `proposalType` (0=Normal, 1=FastTrack, 2=Critical) into three different Timelocks. `ProposalQueued`/`ProposalExecuted`/`ProposalCanceled` topic0s are **shared** with the remote `OmnichainGovernanceExecutor` (§1.9) — disambiguate by chain+emitter (Bravo is BNB-only).

### 1.8 Timelock (NormalTimelock / FastTrackTimelock / CriticalTimelock — all chains; same event set)

| topic0 | Event |
|--------|-------|
| `0x76e2796dc3a81d57b0e8504b647febcbeeb5f4af818e164f11eef8131a6a763f` | `QueueTransaction(bytes32 indexed txHash, address indexed target, uint256 value, string signature, bytes data, uint256 eta)` |
| `0xa560e3198060a2f10670c1ec5b403077ea6ae93ca8de1c32b451dc1a943cd6e7` | `ExecuteTransaction(bytes32 indexed txHash, address indexed target, uint256 value, string signature, bytes data, uint256 eta)` |
| `0x2fffc091a501fd91bfbff27141450d3acb40fb8e6d8382b243ec7a812a3aaf87` | `CancelTransaction(bytes32 indexed txHash, address indexed target, uint256 value, string signature, bytes data, uint256 eta)` |
| `0x948b1f6a42ee138b7e34058ba85a37f716d55ff25ff05a763f15bed6a04c8d2c` | `NewDelay(uint256 indexed newDelay)` |
| `0x71614071b88dee5e0b2ae578a9dd7b2ebbe9ae832ba419dc0242cd065a290b6c` | `NewAdmin(address indexed newAdmin)` *(1-arg — distinct from the 2-arg delegator `NewAdmin`)* |
| `0x69d78e38a01985fbb1462961809b4b2d65531bc93b2b94037f3334b82ca4a756` | `NewPendingAdmin(address indexed newPendingAdmin)` *(1-arg)* |

> **Three identical Timelocks per chain.** The only difference is their `delay` and their authorized caller. On BNB the caller is GovernorBravo; on the 4 remote chains the caller is `OmnichainGovernanceExecutor`. Attribute a queued/executed tx to a route by **which of the three Timelock addresses** emitted it (§N addresses).

### 1.9 Cross-chain governance

**OmnichainProposalSender** (BNB only — relays a passed proposal to remote chains over LayerZero):

| topic0 | Event |
|--------|-------|
| `0x95a4fcf4eb9be6f5cf2eb6830782870f8907bccc513f765388a9cb2dae2f3259` | `ExecuteRemoteProposal(uint16 indexed remoteChainId, uint256 proposalId, bytes payload)` |
| `0x6d16111647e03d7f1cb2b71c02eafe3355b97dfc17af3de1b94ef39c8a9ee4d9` | `StorePayload(uint256 indexed proposalId, uint16 indexed remoteChainId, bytes payload, bytes adapterParams, uint256 value, bytes reason)` *(fires when a remote send reverts — held for retry)* |
| `0x2dc7ac5d08fd553243fc66b5f15262e3f3013e27abf660d7bb3fccf133322f6e` | `ClearPayload(uint256 indexed proposalId, bytes32 executionHash)` |
| `0xe84e609c32d71c678382f7c65cc051810a41dcaf660e55c9f8fcffeba4621a32` | `SetTrustedRemoteAddress(uint16 indexed remoteChainId, bytes oldRemoteAddress, bytes newRemoteAddress)` |
| `0x4dd31065e259d5284e44d1f9265710da72eafcf78dc925e3881189fc3b71f693` | `SetMaxDailyLimit(uint16 chainId, uint256 oldMaxLimit, uint256 newMaxLimit)` *(same topic as OFT SetMaxDailyLimit)* |

**OmnichainGovernanceExecutor** (ETH/Base/Arb/OP — receives the LayerZero message, queues into the local Timelock):

| topic0 | Event |
|--------|-------|
| `0xc37d19c9a6a9a568b5071658f9b5082ff8f142df3cf090385c5621ab11938065` | `ProposalReceived(uint256 indexed proposalId, address[] targets, uint256[] values, string[] signatures, bytes[] calldatas, uint8 proposalType)` |
| `0x9a2e42fd6722813d69113e7d0079d3d940171428df7373df9c7f7617cfda2892` | `ProposalQueued(uint256 indexed id, uint256 eta)` *(shared topic w/ Bravo)* |
| `0x712ae1383f79ac853f8d882153778e0260ef8f03b504e2866e0593e04d2b291f` | `ProposalExecuted(uint256 indexed id)` *(shared topic w/ Bravo)* |
| `0x789cf55be980739dad1d0699b93b58e806b51c9d96619bfa8fe0a28abaa7b30c` | `ProposalCanceled(uint256 indexed id)` *(shared topic w/ Bravo)* |
| `0xfc45ae51ac4893a3f843d030fbfd4037c0c196109c9e667645b8f144c83c16ea` | `TimelockAdded(uint8 routeType, address indexed oldTimelock, address indexed newTimelock)` |
| `0x41d73ce7be31a588d59fe9013cdcfe583bc0aab25093d042b64cade0df730656` | `ReceivePayloadFailed(uint16 indexed srcChainId, bytes indexed srcAddress, uint64 nonce, bytes reason)` |
| `0xb17c58d5977290696b6eea77c81c725f3dc83e426252bd9ece6287c1b8d0e968` | `SetSrcChainId(uint16 indexed oldSrcChainId, uint16 indexed newSrcChainId)` |
| `0xfa41487ad5d6728f0b19276fa1eddc16558578f5109fc39d2dc33c3230470dab` | `SetTrustedRemote(uint16 srcChainId, bytes path)` *(same topic as OFT)* |

### 1.10 VTreasury (BNB) / VTreasuryV8 (remote chains)

| topic0 | Event | Contract |
|--------|-------|----------|
| `0xbaa29435fcbb0a4fbf05d1a0c62e83956a0652d287540f94f1f8188352e4722a` | `WithdrawTreasuryBEP20(address indexed tokenAddress, uint256 withdrawAmount, address indexed withdrawAddress)` | VTreasury (BNB) |
| `0x0d2b7d10254463c7f440553256de09db44772bbaa752720e51f018d33b910252` | `WithdrawTreasuryBNB(uint256 withdrawAmount, address indexed withdrawAddress)` | VTreasury (BNB) |
| `0x6d043f5c542a67e836c8f8bdf640d0de840c85d79c130dcbda8d42c9c056980c` | `WithdrawTreasuryToken(address indexed tokenAddress, uint256 withdrawAmount, address indexed withdrawAddress)` | VTreasuryV8 (remote) |
| `0x41448dfa44379fc602c636f8939b0b1b598c481af871c76fbdd8bdfcdaf30dfa` | `WithdrawTreasuryNative(uint256 withdrawAmount, address indexed withdrawAddress)` | VTreasuryV8 (remote) |

### 1.11 ProtocolShareReserve (all 5 chains)

| topic0 | Event |
|--------|-------|
| `0xa46b2431e663cf7b50c9d5129aff85d2394ecfd447b7ccba83986510a9d945ea` | `AssetsReservesUpdated(address indexed comptroller, address indexed asset, uint256 amount, uint8 incomeType, uint8 schema)` |
| `0x09f71e7b22d78540ee9a42f09917a9d62f46735cb0dfa70d6bab27866d9cb500` | `AssetReleased(address indexed destination, address indexed asset, uint8 schema, uint256 percent, uint256 amount)` |
| `0x7d881f3d6246a6a2b97b121b8ba093c17497912c68e8b2bca6108528e91df3ca` | `ReservesUpdated(address indexed comptroller, address indexed asset, uint8 schema, uint256 oldBalance, uint256 newBalance)` |
| `0xc4584834cab3196e27e1b931e874fecbfada0785b639b02ed649d08c8e3ca857` | `DistributionConfigAdded(address indexed destination, uint8 percentage, uint8 schema)` |
| `0x7b9512a7d53862cbbb1d78873d1809728aa9241f63fdf818e3525869ab0d03ce` | `DistributionConfigUpdated(address indexed destination, uint8 oldPercentage, uint8 newPercentage, uint8 schema)` |
| `0x1ac2d5fa1b44dc6086053de4a872e5bcdf9a98e5069a325572aef982a1b743bb` | `DistributionConfigRemoved(address indexed destination, uint8 percentage, uint8 schema)` |
| `0xa87b964d321035d2165e484ff4b722dd6eae30606c0b98887d2ed1a34e594bfe` | `PoolRegistryUpdated(address indexed oldPoolRegistry, address indexed newPoolRegistry)` |

> The config-event params (`percentage`, `incomeType`, `schema`) are **`uint8`/`uint16` enums**, not 256-bit — `DistributionConfigAdded(address,uint8,uint8)`, not `(address,uint16,uint8)`. Recompute with the exact enum width or you get the wrong topic0.

### 1.12 ResilientOracle (the aggregating oracle — all 5 chains)

| topic0 | Event |
|--------|-------|
| `0xa51ad01e2270c314a7b78f0c60fe66c723f2d06c121d63fcdce776e654878fc1` | `TokenConfigAdded(address indexed asset, address indexed mainOracle, address indexed pivotOracle, address fallbackOracle)` |
| `0xea681d3efb830ef032a9c29a7215b5ceeeb546250d2c463dbf87817aecda1bf1` | `OracleSet(address indexed asset, address indexed oracle, uint256 indexed role)` *(role 0=MAIN, 1=PIVOT, 2=FALLBACK)* |
| `0xcf3cad1ec87208efbde5d82a0557484a78d4182c3ad16926a5463bc1f7234b3d` | `OracleEnabled(address indexed asset, uint256 indexed role, bool indexed enable)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` *(OZ Pausable — global pricing pause)* |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |

> **ResilientOracle has no per-update price event.** It does not emit on every `getPrice`; it only emits on config changes (`TokenConfigAdded`/`OracleSet`/`OracleEnabled`) and `Paused`/`Unpaused`. A `Paused` from the ResilientOracle is the highest-severity oracle signal (all Venus pricing halts). To watch live price movement, watch the underlying adapter (`PricePosted`, §1.13) or the upstream Chainlink/Pyth feed.

### 1.13 Oracle adapters

**ChainlinkOracle** (= **RedStoneOracle**, same contract — emitter differs):

| topic0 | Event |
|--------|-------|
| `0x3cc8d9cb9370a23a8b9ffa75efa24cecb65c4693980e58260841adc474983c5f` | `TokenConfigAdded(address indexed asset, address feed, uint256 maxStalePeriod)` |
| `0xa0844d44570b5ec5ac55e9e7d1e7fc8149b4f33b4b61f3c8fc08bacce058faee` | `PricePosted(address indexed asset, uint256 previousPriceMantissa, uint256 newPriceMantissa)` *(only used for manually-set direct prices)* |

**BinanceOracle** (BNB only):

| topic0 | Event |
|--------|-------|
| `0x37839d4a80c5e3f2578f59515c911ee8cce42383d7ebaa1c92afcde9871c4b58` | `MaxStalePeriodAdded(string indexed asset, uint256 maxStalePeriod)` |

**PythOracle** (BNB only — note the **different** TokenConfigAdded signature):

| topic0 | Event |
|--------|-------|
| `0x559091caed5aa983e358fdf18e8cefbc8ea71f64ea252477cf32778ae4c398b2` | `TokenConfigAdded(address indexed vToken, bytes32 indexed pythId, uint64 maxStalePeriod)` |
| `0x004e195fa31ccc70d4b5113711cee69b9f2059118d18832686a27d19e62a953f` | `PythOracleSet(address indexed oldPythOracle, address indexed newPythOracle)` |

> **`TokenConfigAdded` collides across three oracle shapes:** ResilientOracle `(address,address,address,address)` `0xa51ad01e…`; Chainlink/RedStone `(address,address,uint256)` `0x3cc8d9cb…`; Pyth `(address,bytes32,uint64)` `0x559091ca…`. Three distinct topic0s — key on the exact one for the emitter you watch.

**BoundValidator** (the price-deviation guard — all 5 chains):

| topic0 | Event |
|--------|-------|
| `0x28e2d96bdcf74fe6203e40d159d27ec2e15230239c0aee4a0a914196c550e6d1` | `ValidateConfigAdded(address indexed asset, uint256 upperBoundRatio, uint256 lowerBoundRatio)` |

### 1.14 Common proxy / access-control topics (every Transparent-proxy contract above)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` *(EIP-1967 — emitted on every impl swap of the oracle stack / Prime / PLP / PSR / XVSBridgeAdmin / OmnichainExecutorOwner; NOT VTreasury/VTreasuryV8, which are non-upgradeable Ownable contracts)* |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |
| `0x66fd58e82f7b31a2a5c30e0888f3093efe4e111b00cd2b0c31fe014601293aa0` | `NewAccessControlManager(address oldAccessControlManager, address newAccessControlManager)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |

> Venus's permissioning is centralized in an **AccessControlManager (ACM)**. Most "setX" admin calls are gated by the ACM, not by `onlyOwner`. A `NewAccessControlManager` event from any periphery contract is a governance-level signal.

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

State-changing entrypoints a monitor keys on, plus a few load-bearing views. All confirmed present in deployed implementation bytecode unless marked.

### 2.1 Tokens & staking

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x0efe6a8b` | `deposit(address rewardToken, uint256 pid, uint256 amount)` | XVSVault |
| `0x115b512f` | `requestWithdrawal(address rewardToken, uint256 pid, uint256 amount)` | XVSVault |
| `0x7ac92456` | `executeWithdrawal(address rewardToken, uint256 pid)` | XVSVault |
| `0x996cba68` | `claim(address account, address rewardToken, uint256 pid)` | XVSVault |
| `0x5c19a95c` | `delegate(address delegatee)` | XVSVault |
| `0x782d6fe1` | `getPriorVotes(address account, uint256 blockNumber)` | XVSVault (view) |
| `0x695ef6bf` | `sendFrom(address from, uint16 dstChainId, bytes32 toAddress, uint256 amount, (address,address,bytes) callParams)` | XVSProxyOFT (Src/Dest) |
| `0x2a205e3d` | `estimateSendFee(uint16, bytes, uint256, bool, bytes)` | XVSProxyOFT (view) |

### 2.2 VAI / VRT / Prime (BNB-only for VAI/VRT; Prime all 5)

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x4712ee7d` | `mintVAI(uint256 amount)` | VAIController |
| `0x6fe74a21` | `repayVAI(uint256 amount)` | VAIController |
| `0x11b3d5e7` | `liquidateVAI(address borrower, uint256 repayAmount, address vTokenCollateral)` | VAIController |
| `0x3785d1d6` | `getMintableVAI(address minter)` | VAIController (view) |
| `0xb6b55f25` | `deposit(uint256 _amount)` | VAIVault |
| `0x2e1a7d4d` | `withdraw(uint256 _amount)` | VAIVault |
| `0x4e71d92d` | `claim()` | VAIVault / Prime |
| `0x88d742c2` | `claimInterest(address vToken)` | Prime |
| `0xba437c68` | `claimInterest(address vToken, address user)` | Prime |
| `0x7dafcd89` | `issue(bool isIrrevocable, address[] users)` | Prime (admin) |
| `0x89afcb44` | `burn(address user)` | Prime (admin) |
| `0x37f23cd3` | `xvsUpdated(address user)` | Prime (called by XVSVault) |
| `0x8aadf799` | `accrueTokens(address token)` | PrimeLiquidityProvider |
| `0x192e7a7b` | `releaseFunds(address token)` | PrimeLiquidityProvider |

### 2.3 Governance & cross-chain

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x164a1ab1` | `propose(address[] targets, uint256[] values, string[] signatures, bytes[] calldatas, string description, uint8 proposalType)` | GovernorBravoDelegate |
| `0xda95691a` | `propose(address[], uint256[], string[], bytes[], string)` | GovernorBravoDelegate (legacy 5-arg) |
| `0x56781388` | `castVote(uint256 proposalId, uint8 support)` | GovernorBravoDelegate |
| `0x7b3c71d3` | `castVoteWithReason(uint256, uint8, string)` | GovernorBravoDelegate |
| `0xddf0b009` | `queue(uint256 proposalId)` | GovernorBravoDelegate |
| `0xfe0d94c1` | `execute(uint256 proposalId)` | GovernorBravoDelegate / OmnichainGovernanceExecutor |
| `0x40e58ee5` | `cancel(uint256 proposalId)` | GovernorBravoDelegate / OmnichainGovernanceExecutor |
| `0x3e4f49e6` | `state(uint256 proposalId)` | GovernorBravoDelegate (view) |
| `0x3a66f901` | `queueTransaction(address target, uint256 value, string signature, bytes data, uint256 eta)` | Timelock |
| `0x0825f38f` | `executeTransaction(address, uint256, string, bytes, uint256)` | Timelock (`payable`) |
| `0x591fcdfe` | `cancelTransaction(address, uint256, string, bytes, uint256)` | Timelock |
| `0x3fd9d7ef` | `execute(uint16 remoteChainId, bytes payload, bytes adapterParams, address zroPaymentAddress)` | OmnichainProposalSender (`payable`) |
| `0x001d3567` | `lzReceive(uint16 srcChainId, bytes srcAddress, uint64 nonce, bytes payload)` | OmnichainGovernanceExecutor |
| `0x94a14a34` | `queueProposal(uint256 proposalId)` | OmnichainGovernanceExecutor |

### 2.4 Treasury, PSR & oracle

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xb38d5d8b` | `withdrawTreasuryBEP20(address tokenAddress, uint256 withdrawAmount, address withdrawAddress)` | VTreasury (BNB) |
| `0xfb9e6b8e` | `withdrawTreasuryBNB(uint256 withdrawAmount, address withdrawAddress)` | VTreasury (BNB) |
| `0x74c17a35` | `withdrawTreasuryToken(address, uint256, address)` | VTreasuryV8 (remote) |
| `0xfed7036e` | `withdrawTreasuryNative(uint256, address)` | VTreasuryV8 (remote) |
| `0x16faecec` | `updateAssetsState(address comptroller, address asset, uint8 incomeType)` | ProtocolShareReserve |
| `0xfc31116a` | `releaseFunds(address comptroller, address[] assets)` | ProtocolShareReserve |
| `0x41976e09` | `getPrice(address asset)` | ResilientOracle / ChainlinkOracle / BinanceOracle (view) |
| `0xfc57d4df` | `getUnderlyingPrice(address vToken)` | ResilientOracle (view — Compound-shaped) |
| `0xa6b1344a` | `setOracle(address asset, address oracle, uint8 role)` | ResilientOracle |
| `0x4b932b8f` | `enableOracle(address asset, uint8 role, bool enable)` | ResilientOracle |
| `0x636b999a` | `setMaxStalePeriod(string symbol, uint256 maxStalePeriod)` | BinanceOracle |
| `0x09a8acb0` | `setDirectPrice(address asset, uint256 price)` | ChainlinkOracle |

---

## 3. Addresses — BNB Smart Chain (chain ID 56)

**The canonical home. All verified via `eth_getCode` on `https://bsc-rpc.publicnode.com` on 2026-06-08 (non-empty bytecode).** This is the only chain with VAI, VRT, GovernorBravo, OmnichainProposalSender, BinanceOracle and PythOracle.

| Role | Address |
|------|---------|
| **XVS** (BEP-20, native) | `0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63` |
| **XVSVaultProxy** (staking) | `0x051100480289e704d20e9DB4804837068f3f9204` → impl `0x74c8a97BE672db3e9a224648bE566AdA5F43B378` |
| XVSStore | `0x1e25CF968f12850003Db17E0Dba32108509C4359` |
| XVSVesting (legacy) | `0xb28Dec7C7Ac80f4D0B6a1B711c39e444cDE8B2cE` (proxy) |
| vXVS (Core market) | `0x151B1e2635A717bcDc836ECd6FbB62B674FE3E1D` |
| **XVSBridgeAdmin** | `0x70d644877b7b73800E9073BCFCE981eAaB6Dbc21` → impl `0xb085926fa310b4af85B499162B96e30E5c0E6fAC` |
| **XVSProxyOFTSrc** (lock side) | `0xf8F46791E3dB29a029Ec6c9d946226f3c613e854` *(immutable)* |
| **VAI** (stablecoin) | `0x4BD17003473389A42DAF6a0a729f6Fdb328BbBd7` |
| **VaiUnitroller** (VAIController proxy) | `0x004065D34C6b18cE4370ced1CeBDE94865DbFAFE` → impl `0x8a7d8589A597619a7842D3bC284b9a5a276FAE56` (via `vaiControllerImplementation()`) |
| **VAIVaultProxy** | `0x0667Eed0a0aAb930af74a3dfeDD263A73994f216` → impl `0xa52f2a56abb7cbDD378bc36c6088fafEAf9aC423` (via `vaiVaultImplementation()`) |
| **VRT** (legacy token) | `0x5f84ce30dc3cf7909101c69086c50de191895883` |
| **VRTConverterProxy** | `0x92572fB60f4874d37917C53599cAe5b085B9Facd` → impl `0x3192d0fb11c15629c403a6416abfcd7587b180b7` |
| VRTVaultProxy | `0x98bF4786D72AAEF6c714425126Dd92f149e3F334` |
| **Prime** | `0xBbCD063efE506c3D42a0Fa2dB5C08430288C71FC` → impl `0x1a6660059E61e88402bD34FC96C2332c5EeAF195` |
| **PrimeLiquidityProvider** | `0x23c4F844ffDdC6161174eB32c770D4D8C07833F2` → impl `0x46BED43b29D73835fF075bBa1A0002A1eD1E4de8` |
| **GovernorBravoDelegator** | `0x2d56dC077072B53571b8252008C60e945108c75a` → impl (Delegate) `0x9aa19E4585aC12F0087aa6468DF5587C88B4495b` |
| GovernorBravoDelegate (logic) | `0x9aa19E4585aC12F0087aa6468DF5587C88B4495b` |
| GovernorAlpha / GovernorAlpha2 (sunset) | `0x406f48f47D25E9caa29f17e7Cfbd1dc6878F078f` / `0x388313BfEFEE8ddfeAD55b585F62812293Cf3A60` |
| **NormalTimelock** | `0x939bD8d64c0A9583A7Dcea9933f7b21697ab6396` |
| **FastTrackTimelock** | `0x555ba73dB1b006F3f2C7dB7126d6e4343aDBce02` |
| **CriticalTimelock** | `0x213c446ec11e45b15a6E29C1C1b402B8897f606d` |
| **OmnichainProposalSender** | `0x36a69dE601381be7b0DcAc5D5dD058825505F8f6` *(immutable)* |
| **VTreasury** | `0xF322942f644A996A617BD29c16bd7d231d9F35E9` |
| **ProtocolShareReserve** | `0xCa01D5A9A248a830E9D93231e791B1afFed7c446` → impl `0x4ec6d748a2647000895b455c408f85602a144ed6` (live; the registry `ProtocolShareReserve_Implementation` field `0xDF41C420…` is **stale** — the proxy was upgraded past the recorded artifact, read the EIP-1967 slot) |
| RiskFundV2 / RiskFundConverter / ConverterNetwork | `0xdF31a28D68A2AB381D42b380649Ead7ae2A76E42` / `0xA5622D276CcbB8d9BBE3D1ffd1BB11a0032E53F0` / `0xF7Caad5CeB0209165f2dFE71c92aDe14d0F15995` |
| **ResilientOracle** | `0x6592b5DE802159F3E74B2486b091D11a8256ab8A` → impl `0x90d840f463c4E341e37B1D51b1aB16Bc5b34865C` |
| **ChainlinkOracle** | `0x1B2103441A0A108daD8848D8F5d790e4D402921F` → impl `0x219cFfEFB1afA9F34695C7fACD9B98d1b3291C8b` |
| **RedStoneOracle** (= ChainlinkOracle contract) | `0x8455EFA4D7Ff63b8BFD96AdD889483Ea7d39B70a` |
| **BinanceOracle** | `0x594810b741d136f1960141C0d8Fb4a91bE78A820` → impl `0x201C72986d391A5a8E1713ac5a42CEAf90556a1b` |
| **PythOracle** | `0xb893E38162f55fb80B18Aa44da76FaDf8E9B2262` → impl `0x1b8dE8fe17735B80E30e1bAbcD78A20F573a3e9e` |
| **BoundValidator** | `0x6E332fF0bB52475304494E4AE5063c1051c7d735` → impl `0xbE4176749a74320641e24102B2Af2Ca37FAF2DF1` |

The legacy single-feed oracle `VenusChainlinkOracle` `0x7FabdD617200C9CB4dcf3dd2C41273e60552068A` predates ResilientOracle; the Core pool reads through ResilientOracle today.

## 4. Addresses — Ethereum (chain ID 1)

All verified via `eth_getCode` on `https://ethereum-rpc.publicnode.com` on 2026-06-08. **No VAI, VRT, GovernorBravo, BinanceOracle, PythOracle, OmnichainProposalSender** (those are BNB-only). XVS here is **bridged** (mint/burn by `XVSProxyOFTDest`).

| Role | Address |
|------|---------|
| XVS (bridged) | `0xd3CC9d8f3689B83c91b7B59cAB4946B063EB894A` *(immutable)* |
| XVSProxyOFTDest (mint/burn side) | `0x888E317606b4c590BBAD88653863e8B345702633` *(immutable)* |
| XVSBridgeAdmin | `0x9C6C95632A8FB3A74f2fB4B7FfC50B003c992b96` → impl `0x83aBB808bb291FED8593e953c6489d29aFa0c5Ca` |
| XVSVaultProxy | `0xA0882C2D5DF29233A092d2887A258C2b90e9b994` → impl `0x437042777255A1f25BE60eD25C814Dea6E43bC28` |
| XVSStore | `0x1Db646E1Ab05571AF99e47e8F909801e5C99d37B` |
| Prime | `0x14C4525f47A7f7C984474979c57a2Dccb8EACB39` → impl `0xf039d6cF87E5D0315f3Eb286Bbeb39A7B3fe30df` |
| PrimeLiquidityProvider | `0x8ba6aFfd0e7Bcd0028D1639225C84DdCf53D8872` → impl `0xB41ff563c043f9e7825B6ED6D9233995aD65F3FD` |
| NormalTimelock | `0xd969E79406c35E80750aAae061D402Aab9325714` |
| FastTrackTimelock | `0x8764F50616B62a99A997876C2DEAaa04554C5B2E` |
| CriticalTimelock | `0xeB9b85342c34F65af734C7bd4a149c86c472bC00` |
| OmnichainGovernanceExecutor | `0xd70ffB56E4763078b8B814C0B48938F35D83bE0C` *(immutable)* |
| OmnichainExecutorOwner | `0x87Ed3Fd3a25d157637b955991fb1B41B566916Ba` → impl `0xfCaFda9672a120a55E98E1fDd96AC0402c71b4bB` |
| VTreasuryV8 | `0xFD9B071168bC27DBE16406eC3Aba050Ce8Eb22FA` |
| ProtocolShareReserve | `0x8c8c8530464f7D95552A11eC31Adbd4dC4AC4d3E` → impl `0xfD6Ef8B67f82a0ddA8E078954E04B749a75cE326` |
| ResilientOracle | `0xd2ce3fb018805ef92b8C5976cb31F84b4E295F94` → impl `0x582d6d131e93D81676e82f032B2Dfa638F4E3275` |
| ChainlinkOracle | `0x94c3A2d6B7B2c051aDa041282aec5B0752F8A1F2` → impl `0x36EFe8716fa2ff9f59D528d154D89054581866A5` |
| RedStoneOracle | `0x0FC8001B2c9Ec90352A46093130e284de5889C86` → impl `0xa3b4A56bf47a93459293CFA5E3D20c4f49C8643C` |
| BoundValidator | `0x1Cd5f336A1d28Dff445619CC63d3A0329B4d8a58` → impl `0x955c01a8307618Ac3e5Fc08a7444f5cB6bD7d71e` |

DefaultProxyAdmin (ETH, admin of every Transparent proxy above) = `0x567e4cc5e085d09f66f836fa8279f38b4e5866b9`. **No `ChainlinkOracle` per se is needed for asset coverage that RedStone serves; BinanceOracle/PythOracle are absent on ETH.**

## 5. Addresses — Base (chain ID 8453)

All verified via `eth_getCode` on `https://base-rpc.publicnode.com` on 2026-06-08. Same shape as Ethereum (bridged XVS + Prime + oracle stack + remote governance).

| Role | Address |
|------|---------|
| XVS (bridged) | `0xebB7873213c8d1d9913D8eA39Aa12d74cB107995` |
| XVSProxyOFTDest | `0x3dD92fB51a5d381Ae78E023dfB5DD1D45D2426Cd` |
| XVSBridgeAdmin | `0x6303FEcee7161bF959d65df4Afb9e1ba5701f78e` → impl `0x358691eB7CC06ac512d9068a71Ea3bc2893F50Ed` |
| XVSVaultProxy | `0x708B54F2C3f3606ea48a8d94dab88D9Ab22D7fCd` → impl `0x322F1a2E03F089F8ce510855e793970D6f0EFcF9` |
| XVSStore | `0x11b084Cfa559a82AAC0CcD159dBea27899c7955A` |
| Prime | `0xD2e84244f1e9Fca03Ff024af35b8f9612D5d7a30` → impl `0xdFCDD96A355991C313503Afc0291b74f133d30b6` |
| PrimeLiquidityProvider | `0xcB293EB385dEFF2CdeDa4E7060974BB90ee0B208` → impl `0x646dF53c39e9220dDEB4a72F2C3a8Bd50fbefa11` |
| NormalTimelock | `0x21c12f2946a1a66cBFf7eb997022a37167eCf517` |
| FastTrackTimelock | `0x209F73Ee2Fa9A72aF3Fa6aF1933A3B58ed3De5D7` |
| CriticalTimelock | `0x47F65466392ff2aE825d7a170889F7b5b9D8e60D` |
| OmnichainGovernanceExecutor | `0xE7C56EaA4b6eafCe787B3E1AB8BCa0BC6CBDDb9e` |
| OmnichainExecutorOwner | `0x8BA591f72a90fb379b9a82087b190d51b226F0a9` |
| VTreasuryV8 | `0xbefD8d06f403222dd5E8e37D2ba93320A97939D1` |
| ProtocolShareReserve | `0x3565001d57c91062367C3792B74458e3c6eD910a` → impl `0x74487c1cBDa7f1Abc0d4d8652941e41CCc0F6c0E` |
| ResilientOracle | `0xcBBf58bD5bAdE357b634419B70b215D5E9d6FbeD` → impl `0x2632b7b2b34C80B7F854722CEB6b54714476C0A6` |
| ChainlinkOracle | `0x6F2eA73597955DB37d7C06e1319F0dC7C7455dEb` → impl `0xdA079597acD9eda0c7638534fDB43F06393Fe507` |
| RedStoneOracle | `0xd101Bf51937A6718F402dA944CbfdcD12bB6a6eb` → impl `0x08482c78427c2E83aA2EeedF06338E05a71bf925` |
| BoundValidator | `0x66dDE062D3DC1BB5223A0096EbB89395d1f11DB0` → impl `0xc92eefCE80e7Ca529a060C485F462C90416cA38A` |

## 6. Addresses — Arbitrum One (chain ID 42161)

All verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com` on 2026-06-08. **No ChainlinkOracle** here (asset coverage via RedStone + Chainlink-feed sequencer oracle); has `SequencerChainlinkOracle` `0x9cd9Fcc7E3dEDA360de7c080590AaD377ac9F113` for the L2 sequencer uptime check.

| Role | Address |
|------|---------|
| XVS (bridged) | `0xc1Eb7689147C81aC840d4FF0D298489fc7986d52` |
| XVSProxyOFTDest | `0x20cEa49B5F7a6DBD78cAE772CA5973eF360AA1e6` |
| XVSBridgeAdmin | `0xf5d81C6F7DAA3F97A6265C8441f92eFda22Ad784` → impl `0xC57f35500f4F5B2B31c5250bF8BCcf8058835a9B` |
| XVSVaultProxy | `0x8b79692AAB2822Be30a6382Eb04763A74752d5B4` → impl `0x4C4BedC003e4E2f3A057DeC35aeF26F64Cb07384` |
| XVSStore | `0x507D9923c954AAD8eC530ed8Dedb75bFc893Ec5e` |
| Prime | `0xFE69720424C954A2da05648a0FAC84f9bf11Ef49` → impl `0x62822989F8De6b2Eb8d972e1B0e77E8a3286dBBc` |
| PrimeLiquidityProvider | `0x86bf21dB200f29F21253080942Be8af61046Ec29` → impl `0x920079Ffedbcc627A9d690c34C9206555E903Dd6` |
| NormalTimelock | `0x4b94589Cc23F618687790036726f744D602c4017` |
| FastTrackTimelock | `0x2286a9B2a5246218f2fC1F380383f45BDfCE3E04` |
| CriticalTimelock | `0x181E4f8F21D087bF02Ea2F64D5e550849FBca674` |
| OmnichainGovernanceExecutor | `0xc1858cCE6c28295Efd3eE742795bDa316D7c7526` |
| OmnichainExecutorOwner | `0xf72C1Aa0A1227B4bCcB28E1B1015F0616E2db7fD` |
| VTreasuryV8 | `0x8a662ceAC418daeF956Bc0e6B2dd417c80CDA631` |
| ProtocolShareReserve | `0xF9263eaF7eB50815194f26aCcAB6765820B13D41` → impl `0xFde46857B36881d69F742D44Aa5bF81e8f8dcF94` |
| ResilientOracle | `0xd55A98150e0F9f5e3F6280FC25617A5C93d96007` → impl `0x6B85803c8a2FE134AC1964879Bafd319E1279ff8` |
| RedStoneOracle | `0xF792C4D3BdeF534D6d1dcC305056D00C95453dD6` → impl `0x5cfCC7F674DbC64f21E66FdDE921B4467aB79aB2` |
| BoundValidator | `0x2245FA2420925Cd3C2D889Ddc5bA1aefEF0E14CF` → impl `0x20Fb908a61C000431C4FCb4A51FcB67b73a8A526` |

## 7. Addresses — Optimism (chain ID 10)

All verified via `eth_getCode` on `https://optimism-rpc.publicnode.com` on 2026-06-08. **No ChainlinkOracle** (RedStone + `SequencerChainlinkOracle` `0x1076e5A60F1aC98e6f361813138275F1179BEb52`).

| Role | Address |
|------|---------|
| XVS (bridged) | `0x4a971e87ad1F61f7f3081645f52a99277AE917cF` |
| XVSProxyOFTDest | `0xbBe46bAec851355c3FC4856914c47eB6Cea0B8B4` |
| XVSBridgeAdmin | `0x3c307DF1Bf3198a2417d9CA86806B307D147Ddf7` → impl `0xc8A17E5394aeB0A0E227E0f27F922dc60300e80B` |
| XVSVaultProxy | `0x133120607C018c949E91AE333785519F6d947e01` → impl `0x8B8651EEB002a7991F2287500B17a395E8cfe7d9` |
| XVSStore | `0xFE548630954129923f63113923eF5373E10589d3` |
| Prime | `0xE76d2173546Be97Fa6E18358027BdE9742a649f7` → impl `0x7DCF81746fFA44C4469eBA2F6Db86AE3d5f92b10` |
| PrimeLiquidityProvider | `0x6412f6cd58D0182aE150b90B5A99e285b91C1a12` → impl `0xF3B8d6b1778548F975D6eBebD8a8e515832Cfb0a` |
| NormalTimelock | `0x0C6f1E6B4fDa846f63A0d5a8a73EB811E0e0C04b` |
| FastTrackTimelock | `0x508bD9C31E8d6760De04c70fe6c2b24B3cDea7E7` |
| CriticalTimelock | `0xB82479bc345CAA7326D7d21306972033226fC185` |
| OmnichainGovernanceExecutor | `0x09b11b1CAdC08E239970A8993783f0f8EeC60ABf` |
| OmnichainExecutorOwner | `0xe6d9Eb3A07a1dc4496fc71417D7A7b9d5666BaA3` |
| VTreasuryV8 | `0x104c01EB7b4664551BE6A9bdB26a8C5c6Be7d3da` |
| ProtocolShareReserve | `0x735ed037cB0dAcf90B133370C33C08764f88140a` → impl `0x72672A4f9d2EF78eC98cF8Fd4b3544beBC3fea9E` |
| ResilientOracle | `0x21FC48569bd3a6623281f55FC1F8B48B9386907b` → impl `0xB4E073C5abB056D94f14f0F8748B6BFcb418fFe6` |
| RedStoneOracle | `0x7478e4656F6CCDCa147B6A7314fF68d0C144751a` → impl `0x5e448421aB3c505AdF0E5Ee2D2fCCD80FDe08a43` |
| BoundValidator | `0x37A04a1eF784448377a19F2b1b67cD40c09eA505` → impl `0xc04C8dFF5a91f82f5617Ee9Bd83f6d96de0eb39C` |

## 8. Addresses — Avalanche (43114) & Polygon (137) — NOT DEPLOYED

**Verified absent on 2026-06-08:** every Venus address above returns `eth_getCode = "0x"` on both `https://avalanche-c-chain-rpc.publicnode.com` and `https://polygon-bor-rpc.publicnode.com`. Neither chain has a `deployments/` folder in any Venus repo (`venus-protocol`, `oracle`, `governance-contracts`, `token-bridge`, `protocol-reserve`). There is **no XVS, no Prime, no ResilientOracle, no governance** on Avalanche or Polygon. (Venus's other live chains beyond the 5 here — opBNB, zkSync Era, Unichain — are out of scope for this 7-chain audit but follow the same remote pattern.)

---

## N. Cross-chain summary

| Contract | ETH (1) | Base (8453) | BNB (56) | Arb (42161) | OP (10) | Avax (43114) | Pol (137) |
|---|---|---|---|---|---|---|---|
| XVS | bridged `0xd3CC…94A` | bridged `0xebB7…995` | **native** `0xcF6B…C63` | bridged `0xc1Eb…d52` | bridged `0x4a97…7cF` | — | — |
| XVSVaultProxy | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| XVSProxyOFT | Dest | Dest | **Src** | Dest | Dest | — | — |
| Prime / PLP | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| VAI / VAIController / VAIVault | — | — | **✓** | — | — | — | — |
| VRT / VRTConverter | — | — | **✓** | — | — | — | — |
| GovernorBravo (Delegator+Delegate) | — | — | **✓** | — | — | — | — |
| Normal/FastTrack/Critical Timelock | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| OmnichainProposalSender | — | — | **✓** | — | — | — | — |
| OmnichainGovernanceExecutor (+Owner) | ✓ | ✓ | — | ✓ | ✓ | — | — |
| VTreasury / VTreasuryV8 | V8 | V8 | **VTreasury** | V8 | V8 | — | — |
| ProtocolShareReserve | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| ResilientOracle / BoundValidator | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| ChainlinkOracle | ✓ | ✓ | ✓ | — | — | — | — |
| RedStoneOracle | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| BinanceOracle | — | — | **✓** | — | — | — | — |
| PythOracle | — | — | **✓** | — | — | — | — |

**Internalize:**
1. **BNB is the hub.** VAI, VRT, GovernorBravo, OmnichainProposalSender, BinanceOracle and PythOracle exist *only* on BNB. On the other 4 chains there is no on-chain voting — governance arrives as a LayerZero message and is executed by `OmnichainGovernanceExecutor` into the local Timelock.
2. **Every XVS address is different per chain** (no vanity/shared address). XVS is native only on BNB; elsewhere it's the bridged token whose supply is mint/burned by `XVSProxyOFTDest`. Always key XVS on `(chainId, address)`.
3. **Topics + selectors are 100% chain-agnostic.** A `Deposit`/`Claim`/`OracleSet`/`ProposalReceived` topic0 is identical on every chain; only the emitting address changes.
4. **LayerZero v1 endpoint IDs** (used in `SendToChain`/cross-chain governance, `uint16`): Ethereum=101, BNB=102, Arbitrum=110, Optimism=111, Base=184. (These are LayerZero chain IDs, not EVM chain IDs.)

---

## N+1. Proxies — three patterns, classify before resolving

EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. All slot reads below taken live on 2026-06-08.

| Contract | Pattern | How to read the logic | Upgrade auth |
|----------|---------|------------------------|--------------|
| ResilientOracle, ChainlinkOracle, RedStoneOracle, BinanceOracle, PythOracle, BoundValidator | **Transparent (EIP-1967)** | impl slot populated (e.g. ETH ResilientOracle `0x582d6d13…`); `Upgraded(address)` topic `0xbc7cd75a…` | admin = DefaultProxyAdmin (ETH `0x567e4cc5…`; BNB oracle admin `0x1bb765b7…`), owned by governance |
| Prime, PrimeLiquidityProvider, ProtocolShareReserve, XVSBridgeAdmin, OmnichainExecutorOwner | **Transparent (EIP-1967)** | impl slot populated (PSR BNB live impl `0x4ec6d748…`, **not** the stale registry `0xDF41C420…`) | DefaultProxyAdmin / governance |
| **XVSVaultProxy** | **Compound delegator** | EIP-1967 slot = `0x0`; read `implementation()` (`0x5c60da1b`) → e.g. BNB `0x74c8a97B…` | `_setPendingImplementation`+`_acceptImplementation`; emits `NewImplementation(address,address)` `0xd604de94…` |
| **GovernorBravoDelegator** | **Compound delegator** | EIP-1967 slot = `0x0`; `implementation()` → BNB `0x9aa19E45…` (= GovernorBravoDelegate) | `_setImplementation`; `NewImplementation` |
| **VaiUnitroller** | **Compound Unitroller** | EIP-1967 slot = `0x0`; `vaiControllerImplementation()` (`0x003b5884`) → BNB `0x8a7d8589…` (note: the registry `VaiUnitroller_Implementation` field `0xFD754b…` is **stale**) | `_setPendingImplementation`+`_acceptImplementation` |
| **VAIVaultProxy** | **Compound delegator** | EIP-1967 slot = `0x0`; `vaiVaultImplementation()` (`0xf661bb86`) → BNB `0xa52f2a56…` | delegator setters |
| **VRTConverterProxy** | **Compound delegator** | EIP-1967 slot = `0x0`; `implementation()` → BNB `0x3192d0fb…` | delegator setters |
| **XVS (bridged), XVSProxyOFTSrc, XVSProxyOFTDest, OmnichainProposalSender, OmnichainGovernanceExecutor** | **Immutable** | EIP-1967 slot = `0x0` and **no** `implementation()` getter — the address *is* the logic | none (new version = new address) |
| **VTreasury (BNB), VTreasuryV8 (remote)** | **Immutable `Ownable`** | EIP-1967 impl+admin slots both `0x0`; **no** `implementation()` getter (reverts); not a proxy at all | `owner()` = the chain's NormalTimelock (e.g. ETH `0xd969E794…`); non-upgradeable — a new treasury = new address |

**Practical takeaway:** for the oracle stack / Prime / PSR you can read the live impl from the EIP-1967 slot; for XVSVault / Bravo / VAI you must call the Compound-style getter (the EIP-1967 slot is empty and would falsely read as "not a proxy"); the bridge endpoints and cross-chain governance executors are permanently immutable.

---

## N+2. Detection invariants & gotchas

1. **`TokenConfigAdded` has THREE distinct shapes/topic0s** (§1.12–1.13): ResilientOracle `(address,address,address,address)` `0xa51ad01e…`; Chainlink/RedStone `(address,address,uint256)` `0x3cc8d9cb…`; Pyth `(address,bytes32,uint64)` `0x559091ca…`. A monitor that keys on one will miss the others. Same applies to `OracleSet`/`OracleEnabled` — those are ResilientOracle-only.
2. **ResilientOracle emits NO price-update event.** Watching `getPrice`/`getUnderlyingPrice` returns nothing in logs (they're views). The only oracle logs are config changes and `Paused`/`Unpaused`. **A `Paused` `0x62e78cea…` from the ResilientOracle is a protocol-wide pricing halt — top-severity alert.** For live price movement watch the underlying Chainlink/Pyth/Binance feed (or `PricePosted` for direct prices), not Venus's oracle.
3. **`Deposit(address,uint256)` `0xe1fffcc4…` collides** across VAIVault, VRTVault and legacy XVSVault V1; the **current** XVSVault uses the 4-arg `Deposit` `0xdcbc1c05…`. Always disambiguate by emitter.
4. **`SendToChain` is the custom 4-arg Venus form** `(uint16,address,bytes32,uint256)` `0xd81fc9b8…`, NOT the stock LayerZero `(uint16,bytes32,uint256)`. To track XVS leaving BNB watch `SendToChain` on `XVSProxyOFTSrc` `0xf8F4…e854`; to track XVS arriving watch `ReceiveFromChain` `0xbf551ec9…` on each chain's `XVSProxyOFTDest`. (XVS total supply across chains is conserved: lock on BNB = mint on remote.)
5. **`ProposalQueued`/`ProposalExecuted`/`ProposalCanceled` topic0s are shared** by BNB GovernorBravo and the remote OmnichainGovernanceExecutor. They are *different contracts on different chains*: on BNB they come from the Delegator `0x2d56…c75a`; on remote chains from the executor (e.g. ETH `0xd70f…bE0C`). Key on chain+emitter. The **votes** (`VoteCast`) only ever happen on BNB.
6. **Three Timelocks per chain, identical ABI.** A `QueueTransaction`/`ExecuteTransaction` carries no route label — the route (Normal/FastTrack/Critical) is encoded purely by *which Timelock address* emitted it. On the 4 remote chains these Timelocks are driven by the OmnichainGovernanceExecutor, not by a local Governor.
7. **PSR config events use narrow enum widths.** `DistributionConfigAdded(address,uint8,uint8)`, `DistributionConfigUpdated(address,uint8,uint8,uint8)`, `AssetsReservesUpdated(address,address,uint256,uint8,uint8)` — the `percentage`/`schema`/`incomeType` are `uint8`/`uint16`, not `uint256`. Recompute topic0 with the exact width.
8. **VTreasury (BNB) vs VTreasuryV8 (remote) emit different withdrawal events.** BNB uses `WithdrawTreasuryBEP20` + `WithdrawTreasuryBNB`; remote uses `WithdrawTreasuryToken` + `WithdrawTreasuryNative`. A treasury-drain monitor must include both pairs.
9. **RedStoneOracle == ChainlinkOracle contract.** Identical events/selectors; the only difference is the address and the feeds it points at. Don't treat them as separate event schemas.
10. **Most admin setters are ACM-gated, not `onlyOwner`.** Authority lives in the AccessControlManager; `owner()` on a periphery contract is often the ProxyAdmin, not the governor. A `NewAccessControlManager` event is a governance-grade change. The ultimate authority is the BNB GovernorBravo, propagated cross-chain.
11. **Compound-delegator impl reads.** XVSVault / Bravo / VAIController / VAIVault / VRTConverter have an **empty EIP-1967 slot** — do not conclude "immutable." Read the Compound getter (`implementation()` / `vaiControllerImplementation()` / `vaiVaultImplementation()`). The registry's `*_Implementation` JSON field can be stale (confirmed for VaiUnitroller) — trust the on-chain getter.
12. **publicnode `eth_getLogs` caps the block range at 50000** and returns `[]` for address-less (topic-only) filters — always pass the contract `address` and chunk into ≤49k-block windows. Governance/oracle-config events are sparse (cluster at deploy + around proposals); scan from the deploy block, not the head.
13. **Avalanche & Polygon have zero Venus footprint** (§8) — do not assume parity with the other chains.

---

## N+3. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== XVS token =====
TOPIC_XVS_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_XVS_APPROVAL             = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_XVS_MINTCAPCHANGED       = '\x01a85f4ecff52e70907e25b863010bca98a9458d9f2fe9b3efb4c47d197e6448'
TOPIC_XVS_BLACKLISTUPDATED     = '\x6a12b3df6cba4203bd7fd06b816789f87de8c594299aed5717ae070fac781bac'
-- ===== XVSVault (XVSVaultProxy) =====
TOPIC_XVSVAULT_DEPOSIT         = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'  -- 4-arg
TOPIC_XVSVAULT_REQWITHDRAWAL   = '\x88a254a0ef28a0b9e957ff600beae69870f6f924065147f3627c3f814e60ec11'
TOPIC_XVSVAULT_EXECWITHDRAWAL  = '\xe31da05fae6db869f5ea51f4b638aa6884070b6c87f18f63bd2291a12cb2f518'
TOPIC_XVSVAULT_CLAIM           = '\x865ca08d59f5cb456e85cd2f7ef63664ea4f73327414e9d8152c4158b0e94645'
TOPIC_XVSVAULT_POOLADDED       = '\xd7fa4bff1cd2253c0789c3291a786a6f6b1a3b4569a75af683a15d52abb6a0bf'
TOPIC_XVSVAULT_DELEGCHANGEDV2  = '\x0cc323ffec3ea49cbcddc0de1480978126d350c6a45dff33ad2f1cda6ae99261'
TOPIC_XVSVAULT_DELEGVOTESCHGV2 = '\x6adb589fed1e8542fb7a6b10f00a85e02265e77f9ae3ca8ff93b22983e1af9a0'
-- ===== XVSBridge OFT =====
TOPIC_OFT_SENDTOCHAIN          = '\xd81fc9b8523134ed613870ed029d6170cbb73aa6a6bc311b9a642689fb9df59a'  -- (uint16,address,bytes32,uint256)
TOPIC_OFT_RECEIVEFROMCHAIN     = '\xbf551ec93859b170f9b2141bd9298bf3f64322c6f7beb2543a0cb669834118bf'
TOPIC_OFT_MESSAGEFAILED        = '\xe183f33de2837795525b4792ca4cd60535bd77c53b7e7030060bfcf5734d6b0c'
-- ===== VAIController (BNB) =====
TOPIC_VAI_MINTVAI             = '\x002e68ab1600fc5e7290e2ceaa79e2f86b4dbaca84a48421e167e0b40409218a'
TOPIC_VAI_REPAYVAI            = '\x1db858e6f7e1a0d5e92c10c6507d42b3dabfe0a4867fe90c5a14d9963662ef7e'
TOPIC_VAI_LIQUIDATEVAI        = '\x42d401f96718a0c42e5cea8108973f0022677b7e2e5f4ee19851b2de7a0394e7'
TOPIC_VAI_MINTFEE            = '\xb0715a6d41a37c1b0672c22c09a31a0642c1fb3f9efa2d5fd5c6d2d891ee78c6'
-- ===== VAIVault (BNB) =====
TOPIC_VAIVAULT_DEPOSIT        = '\xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'  -- shared w/ VRTVault
TOPIC_VAIVAULT_WITHDRAW       = '\x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364'
-- ===== Prime + PLP =====
TOPIC_PRIME_MINT             = '\xdd032f28700d4e4b1719b8fa26918a7d68608b4e36def571ce5fe7a3ecd69f45'
TOPIC_PRIME_BURN             = '\xe22de1457cb61fb61b60176bc4235a9abd19466126b46692bc14fc573f099249'
TOPIC_PRIME_INTERESTCLAIMED  = '\xc7edf5cfe443c04a10a60ff6084c847114348c55b257a01d62700326219adbba'
TOPIC_PRIME_MARKETADDED      = '\x1322eaea77217179bf4ef6084dc2f48c897e0d5a6b8365213804360e4d8ba9a2'
TOPIC_PLP_TOKENSACCRUED      = '\xfe854c4c4e633d5bb31aec1f39f01d9f8f01ad2e0212a0e576825ac986af0589'
TOPIC_PLP_DISTSPEEDUPDATED   = '\x2a139b40b9bf8c89ae5053746323912620b9d8ea3b076b098b1bc57702abf3a5'
-- ===== GovernorBravo (BNB) =====
TOPIC_GOV_PROPOSALCREATED    = '\xc8df7ff219f3c0358e14500814d8b62b443a4bebf3a596baa60b9295b1cf1bde'  -- 10-arg (current)
TOPIC_GOV_PROPOSALCREATED_OLD= '\x7d84a6263ae0d98d3329bd7b46bb4e8d6f98cd35a7adb45c274c8b7fd5ebd5e0'  -- 9-arg legacy
TOPIC_GOV_VOTECAST           = '\xb8e138887d0aa13bab447e82de9d5c1777041ecd21ca36ba824ff1e6c07ddda4'
TOPIC_GOV_PROPOSALQUEUED     = '\x9a2e42fd6722813d69113e7d0079d3d940171428df7373df9c7f7617cfda2892'  -- shared w/ executor
TOPIC_GOV_PROPOSALEXECUTED   = '\x712ae1383f79ac853f8d882153778e0260ef8f03b504e2866e0593e04d2b291f'  -- shared w/ executor
TOPIC_GOV_PROPOSALCANCELED   = '\x789cf55be980739dad1d0699b93b58e806b51c9d96619bfa8fe0a28abaa7b30c'  -- shared w/ executor
-- ===== Timelock (all chains) =====
TOPIC_TL_QUEUETX             = '\x76e2796dc3a81d57b0e8504b647febcbeeb5f4af818e164f11eef8131a6a763f'
TOPIC_TL_EXECUTETX           = '\xa560e3198060a2f10670c1ec5b403077ea6ae93ca8de1c32b451dc1a943cd6e7'
TOPIC_TL_CANCELTX            = '\x2fffc091a501fd91bfbff27141450d3acb40fb8e6d8382b243ec7a812a3aaf87'
TOPIC_TL_NEWDELAY            = '\x948b1f6a42ee138b7e34058ba85a37f716d55ff25ff05a763f15bed6a04c8d2c'
-- ===== Cross-chain governance =====
TOPIC_OPS_EXECUTEREMOTEPROP  = '\x95a4fcf4eb9be6f5cf2eb6830782870f8907bccc513f765388a9cb2dae2f3259'
TOPIC_OPS_STOREPAYLOAD       = '\x6d16111647e03d7f1cb2b71c02eafe3355b97dfc17af3de1b94ef39c8a9ee4d9'
TOPIC_OGE_PROPOSALRECEIVED   = '\xc37d19c9a6a9a568b5071658f9b5082ff8f142df3cf090385c5621ab11938065'
TOPIC_OGE_TIMELOCKADDED      = '\xfc45ae51ac4893a3f843d030fbfd4037c0c196109c9e667645b8f144c83c16ea'
TOPIC_OGE_RECVPAYLOADFAILED  = '\x41d73ce7be31a588d59fe9013cdcfe583bc0aab25093d042b64cade0df730656'
-- ===== Treasury / PSR =====
TOPIC_VTREASURY_WD_BEP20     = '\xbaa29435fcbb0a4fbf05d1a0c62e83956a0652d287540f94f1f8188352e4722a'
TOPIC_VTREASURY_WD_BNB       = '\x0d2b7d10254463c7f440553256de09db44772bbaa752720e51f018d33b910252'
TOPIC_VTREASURYV8_WD_TOKEN   = '\x6d043f5c542a67e836c8f8bdf640d0de840c85d79c130dcbda8d42c9c056980c'
TOPIC_VTREASURYV8_WD_NATIVE  = '\x41448dfa44379fc602c636f8939b0b1b598c481af871c76fbdd8bdfcdaf30dfa'
TOPIC_PSR_ASSETSRESERVESUPD  = '\xa46b2431e663cf7b50c9d5129aff85d2394ecfd447b7ccba83986510a9d945ea'
TOPIC_PSR_ASSETRELEASED      = '\x09f71e7b22d78540ee9a42f09917a9d62f46735cb0dfa70d6bab27866d9cb500'
TOPIC_PSR_DISTCONFIGADDED    = '\xc4584834cab3196e27e1b931e874fecbfada0785b639b02ed649d08c8e3ca857'
-- ===== Oracle =====
TOPIC_RO_TOKENCONFIGADDED    = '\xa51ad01e2270c314a7b78f0c60fe66c723f2d06c121d63fcdce776e654878fc1'  -- ResilientOracle (4-addr)
TOPIC_RO_ORACLESET           = '\xea681d3efb830ef032a9c29a7215b5ceeeb546250d2c463dbf87817aecda1bf1'
TOPIC_RO_ORACLEENABLED       = '\xcf3cad1ec87208efbde5d82a0557484a78d4182c3ad16926a5463bc1f7234b3d'
TOPIC_RO_PAUSED              = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'  -- protocol-wide pricing halt
TOPIC_RO_UNPAUSED            = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_CL_TOKENCONFIGADDED    = '\x3cc8d9cb9370a23a8b9ffa75efa24cecb65c4693980e58260841adc474983c5f'  -- Chainlink/RedStone (addr,addr,uint256)
TOPIC_CL_PRICEPOSTED         = '\xa0844d44570b5ec5ac55e9e7d1e7fc8149b4f33b4b61f3c8fc08bacce058faee'
TOPIC_PYTH_TOKENCONFIGADDED  = '\x559091caed5aa983e358fdf18e8cefbc8ea71f64ea252477cf32778ae4c398b2'  -- Pyth (addr,bytes32,uint64)
TOPIC_BINANCE_MAXSTALEADDED  = '\x37839d4a80c5e3f2578f59515c911ee8cce42383d7ebaa1c92afcde9871c4b58'
TOPIC_BV_VALIDATECONFIGADDED = '\x28e2d96bdcf74fe6203e40d159d27ec2e15230239c0aee4a0a914196c550e6d1'
-- ===== Common proxy / ACM =====
TOPIC_UPGRADED               = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_NEWIMPLEMENTATION      = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'  -- Compound delegator
TOPIC_NEWACCESSCONTROLMGR    = '\x66fd58e82f7b31a2a5c30e0888f3093efe4e111b00cd2b0c31fe014601293aa0'

-- ===== Selectors =====
SEL_XVSVAULT_DEPOSIT         = '\x0efe6a8b'
SEL_XVSVAULT_REQWITHDRAWAL   = '\x115b512f'
SEL_XVSVAULT_EXECWITHDRAWAL  = '\x7ac92456'
SEL_XVSVAULT_CLAIM           = '\x996cba68'
SEL_OFT_SENDFROM             = '\x695ef6bf'   -- sendFrom(address,uint16,bytes32,uint256,(address,address,bytes))
SEL_VAI_MINTVAI              = '\x4712ee7d'
SEL_VAI_REPAYVAI             = '\x6fe74a21'
SEL_VAI_LIQUIDATEVAI         = '\x11b3d5e7'
SEL_PRIME_CLAIMINTEREST      = '\x88d742c2'
SEL_GOV_PROPOSE              = '\x164a1ab1'   -- 6-arg (with proposalType)
SEL_GOV_CASTVOTE             = '\x56781388'
SEL_GOV_QUEUE                = '\xddf0b009'
SEL_GOV_EXECUTE              = '\xfe0d94c1'   -- shared w/ executor.execute
SEL_GOV_CANCEL               = '\x40e58ee5'
SEL_TL_QUEUETX               = '\x3a66f901'
SEL_TL_EXECUTETX             = '\x0825f38f'
SEL_OPS_EXECUTE              = '\x3fd9d7ef'   -- OmnichainProposalSender.execute (payable)
SEL_OGE_LZRECEIVE            = '\x001d3567'
SEL_PSR_UPDATEASSETSSTATE    = '\x16faecec'
SEL_PSR_RELEASEFUNDS         = '\xfc31116a'
SEL_RO_GETPRICE              = '\x41976e09'
SEL_RO_GETUNDERLYINGPRICE    = '\xfc57d4df'
SEL_VTREASURY_WD_BEP20       = '\xb38d5d8b'
SEL_VTREASURYV8_WD_TOKEN     = '\x74c17a35'

-- ===== Key addresses (lowercase) =====
BNB_XVS                = '\xcf6bb5389c92bdda8a3747ddb454cb7a64626c63'
ETH_XVS                = '\xd3cc9d8f3689b83c91b7b59cab4946b063eb894a'
BASE_XVS               = '\xebb7873213c8d1d9913d8ea39aa12d74cb107995'
ARB_XVS                = '\xc1eb7689147c81ac840d4ff0d298489fc7986d52'
OP_XVS                 = '\x4a971e87ad1f61f7f3081645f52a99277ae917cf'
BNB_OFT_SRC            = '\xf8f46791e3db29a029ec6c9d946226f3c613e854'
ETH_OFT_DEST           = '\x888e317606b4c590bbad88653863e8b345702633'
BNB_VAI                = '\x4bd17003473389a42daf6a0a729f6fdb328bbbd7'
BNB_VAIUNITROLLER      = '\x004065d34c6b18ce4370ced1cebde94865dbfafe'
BNB_VAIVAULT           = '\x0667eed0a0aab930af74a3dfedd263a73994f216'
BNB_VRT                = '\x5f84ce30dc3cf7909101c69086c50de191895883'
BNB_GOVBRAVODELEGATOR  = '\x2d56dc077072b53571b8252008c60e945108c75a'
BNB_NORMALTIMELOCK     = '\x939bd8d64c0a9583a7dcea9933f7b21697ab6396'
BNB_FASTTRACKTIMELOCK  = '\x555ba73db1b006f3f2c7db7126d6e4343adbce02'
BNB_CRITICALTIMELOCK   = '\x213c446ec11e45b15a6e29c1c1b402b8897f606d'
BNB_OMNI_PROPSENDER    = '\x36a69de601381be7b0dcac5d5dd058825505f8f6'
ETH_OMNI_GOVEXECUTOR   = '\xd70ffb56e4763078b8b814c0b48938f35d83be0c'
BNB_RESILIENTORACLE    = '\x6592b5de802159f3e74b2486b091d11a8256ab8a'
ETH_RESILIENTORACLE    = '\xd2ce3fb018805ef92b8c5976cb31f84b4e295f94'
BASE_RESILIENTORACLE   = '\xcbbf58bd5bade357b634419b70b215d5e9d6fbed'
ARB_RESILIENTORACLE    = '\xd55a98150e0f9f5e3f6280fc25617a5c93d96007'
OP_RESILIENTORACLE     = '\x21fc48569bd3a6623281f55fc1f8b48b9386907b'
BNB_BINANCEORACLE      = '\x594810b741d136f1960141c0d8fb4a91be78a820'
BNB_PYTHORACLE         = '\xb893e38162f55fb80b18aa44da76fadf8e9b2262'
BNB_PROTOCOLSHARERSV   = '\xca01d5a9a248a830e9d93231e791b1affed7c446'
EIP1967_IMPL_SLOT      = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## N+4. Verification & sources

- **Event topic0 / selectors:** computed locally as `keccak256(canonical signature)` from each contract's **on-chain ABI** (parsed from the canonical repo `deployments/<network>/<Contract>.json` artifacts — the authoritative param widths, e.g. `proposalType uint8`, PSR `percentage uint8`, Pyth `pythId bytes32`/`maxStalePeriod uint64`, OFT `toAddress bytes32`). High-frequency topics confirmed against live `eth_getLogs` (≤49k-block windows): XVSVault `Deposit` (9) + `Claim` (16) on BNB; PSR `AssetsReservesUpdated` (19) on BNB; Prime `InterestClaimed` (4) on BNB; OmnichainGovernanceExecutor `ProposalReceived` (≥1) on ETH; XVS `Transfer` (51) + OFT `ReceiveFromChain` (≥1) on ETH. Sparse governance/oracle-config events are recomputed from the deployed ABI (authoritative); their topic0s match the standard Compound-Bravo / Venus-oracle signatures.
- **Selectors confirmed in deployed implementation bytecode** (PUSH4 scan): OFT `sendFrom` `0x695ef6bf`; VAIController `mintVAI`/`repayVAI`; ResilientOracle `getPrice`/`getUnderlyingPrice`; GovernorBravoDelegate `execute`/`castVote`/`propose(uint8)`; XVSVault `deposit`/`claim`; PSR `updateAssetsState`.
- **Addresses:** taken from the canonical `VenusProtocol/{venus-protocol,oracle,governance-contracts,token-bridge,protocol-reserve}` `deployments/<network>_addresses.json` registries and **existence-checked via `eth_getCode`** on each chain's publicnode RPC on 2026-06-08 (non-empty bytecode). Avalanche (43114) and Polygon (137) verified **absent** (`0x` for every address; no deployment folder in any repo).
- **Proxies:** EIP-1967 impl+admin slots read live via `eth_getStorageAt`. Oracle stack / Prime / PLP / PSR / XVSBridgeAdmin / OmnichainExecutorOwner = Transparent (impl slot populated; ETH admin `0x567e4cc5…`, BNB oracle admin `0x1bb765b7…` = the canonical `DefaultProxyAdmin`). PSR on BNB live impl `0x4ec6d748…` (the registry `ProtocolShareReserve_Implementation` field `0xDF41C420…` is stale — the proxy was upgraded past the recorded artifact; both impls have code). XVSVaultProxy / GovernorBravoDelegator / VaiUnitroller / VAIVaultProxy / VRTConverterProxy = Compound-delegator (EIP-1967 slot `0x0`; logic via `implementation()`/`vaiControllerImplementation()`/`vaiVaultImplementation()` — VaiUnitroller live impl `0x8a7d8589…` ≠ stale registry field `0xFD754b…`). XVS / XVSProxyOFT(Src/Dest) / OmnichainProposalSender / OmnichainGovernanceExecutor = immutable (impl slot `0x0`, no getter). **VTreasury (BNB) / VTreasuryV8 (remote) are NOT proxies** — plain non-upgradeable `Ownable` contracts (impl+admin slots `0x0`, no `implementation()` getter, `owner()` = the chain's NormalTimelock; confirmed on ETH/Base/Arb/OP and BNB).

Authoritative sources:
- [`VenusProtocol/venus-protocol`](https://github.com/VenusProtocol/venus-protocol) — XVS, XVSVault, VAI/VAIController, VAIVault, VRT/VRTConverter, Prime, PrimeLiquidityProvider; `deployments/<network>_addresses.json`.
- [`VenusProtocol/oracle`](https://github.com/VenusProtocol/oracle) — ResilientOracle, ChainlinkOracle (= RedStoneOracle), BinanceOracle, PythOracle, BoundValidator.
- [`VenusProtocol/governance-contracts`](https://github.com/VenusProtocol/governance-contracts) — GovernorBravoDelegate/Delegator, the 3 Timelocks, OmnichainProposalSender, OmnichainGovernanceExecutor, OmnichainExecutorOwner.
- [`VenusProtocol/token-bridge`](https://github.com/VenusProtocol/token-bridge) — XVS (remote), XVSBridgeAdmin, XVSProxyOFTSrc/Dest.
- [`VenusProtocol/protocol-reserve`](https://github.com/VenusProtocol/protocol-reserve) — ProtocolShareReserve, ConverterNetwork, RiskFundV2.
- [Venus docs — contract addresses](https://docs-v4.venus.io/) · explorers: [BscScan](https://bscscan.com/address/0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63) · [Etherscan](https://etherscan.io/address/0xd3CC9d8f3689B83c91b7B59cAB4946B063EB894A) · [Basescan](https://basescan.org/address/0xebB7873213c8d1d9913D8eA39Aa12d74cB107995) · [Arbiscan](https://arbiscan.io/address/0xc1Eb7689147C81aC840d4FF0D298489fc7986d52) · [Optimism](https://optimistic.etherscan.io/address/0x4a971e87ad1F61f7f3081645f52a99277AE917cF).
