# Rocket Pool — Core Protocol (Ethereum mainnet) — Topics, Selectors, Addresses, Versions

**Status:** verified 2026-05-29. Every mainnet address below was resolved **live** from the on-chain `RocketStorage` registry (`getAddress(keccak256("contract.address", name))`) and confirmed to hold code; addresses are independently EIP-55 re-checksummed. Topic0s marked **✓** were observed in live `eth_getLogs` / tx receipts this session; **src** = keccak-256 of the verbatim signature from `rocket-pool/rocketpool` `master` (the Saturn-1 / v1.4 codebase), not log-confirmed this pass. Selectors marked **✓** returned sane values via live `eth_call`.

**Scope:** Rocket Pool's **core protocol is Ethereum-mainnet ONLY** (chain ID 1). Node operators, minipools, megapools, RPL staking, the deposit pool, oracles, rewards and governance all live here. On every other chain Rocket Pool is **only the bridged rETH token** (no staking, no core contracts) — see [l2.md](l2.md). rETH and RPL are also tradable everywhere but minted/burned only via this core.

**What Rocket Pool is.** Decentralised ETH liquid staking. Users deposit ETH → mint **rETH** (non-rebasing, value-accruing). Permissionless **node operators** post an ETH bond + (optionally) **RPL** collateral and run validators; protocol ETH is matched to their bond. Two validator architectures coexist today: legacy **minipools** (one contract per validator) and Saturn **megapools** (one contract per node serving many validators). A trusted-node **oDAO** submits the rETH exchange rate / RPL price oracle reports; the on-chain **pDAO** governs parameters and upgrades.

---

## 0. Architecture — the `RocketStorage` registry (read this first)

Rocket Pool has **no per-contract proxies** for its network contracts. Instead a single immutable hub, **`RocketStorage`** (`0x1d8f8f00cfa6758d7bE78336684788Fb0ee0Fa46`), holds all protocol state as type-segregated maps (`addressStorage`, `uintStorage`, `boolStorage`, `stringStorage`, `bytesStorage`, `intStorage`, `bytes32Storage`). Every logic contract (`RocketBase` subclass) is **stateless-by-convention** and reads/writes RocketStorage.

**Contract lookup** (the canonical pattern — this is how you find any current address):
```solidity
address a = rocketStorage.getAddress(keccak256(abi.encodePacked("contract.address", "rocketDepositPool")));
```
Auxiliary keys: `keccak256("contract.name", address)` → name (reverse), `keccak256("contract.exists", address)` → bool (is a registered network contract), `keccak256("contract.abi", name)` → ABI string. Write access is gated by `onlyLatestRocketNetworkContract` (caller must have `contract.exists == true`).

**Upgrades = re-registration, not proxy impl swaps.** `RocketDAONodeTrustedUpgrade.upgrade(string _type,string _name,string _abi,address _addr)` with `_type ∈ {addContract, upgradeContract, addABI, upgradeABI}` registers a new address under a name and de-registers the old one. Since Saturn-1 (RPIP-60) upgrades carry a **time delay** + **security-council `veto()`**. Consequence: **the address of a logic contract changes when it is upgraded** — never hardcode anything except RocketStorage; resolve via the registry. **Six contracts can NEVER be upgraded** (hard reverts): `rocketVault`, `rocketTokenRETH`, `rocketTokenRPL`, `rocketTokenRPLFixedSupply`, `casperDeposit`, `rocketMinipoolPenalty` — their addresses are permanent.

The named `rocketUpgradeOneDotX` contracts are one-shot batch-upgrade scripts (Redstone→Saturn); they remain registered so historical addresses stay queryable.

---

## 1. Versions / upgrade history

Rocket Pool is one continuously-upgraded deployment (not discrete redeploys). Internal contract versions track named upgrades; the batch-upgrade contract for each is registered in RocketStorage (verified live):

| Ver | Upgrade | Upgrade contract (`rocketUpgrade…`) | Mainnet date | Headline contract-level change |
|-----|---------|-------------------------------------|--------------|--------------------------------|
| v1.0 | **Launch** | — (genesis bootstrap) | 2021-11-09 | RocketStorage + initial suite; 16-ETH minipools; new inflationary RPL + 1:1 swap from fixed-supply RPL |
| v1.1 | **Redstone** | `OneDotOne` `0xC680a22b4F03977f69b51A09f3Dbe922eb77C8FE` | ~2022-08/09 (Merge) | **Smoothing Pool** + **Merkle rewards**: adds `rocketSmoothingPool`, `rocketMerkleDistributorMainnet`, `rocketRewardsPool`, `rocketNodeDistributorFactory/Delegate`. Removes `rocketClaimNode`/`rocketClaimTrustedNode` |
| v1.2 | **Atlas** | `OneDotTwo` `0x9a0b5d3101d111EA0edD573d45ef2208CC97984a` | 2023-04-18 | **LEB8 / 8-ETH bonded minipools**, bond-reduction (`rocketMinipoolBondReducer`), `rocketMinipoolBase`, deposit-credit, solo→minipool migration |
| v1.3 | **Houston** | `OneDotThree` `0x5dC69083B68CDb5c9ca492A0A5eC581e529fb73C` | 2024-06-17 | **Fully on-chain pDAO governance** + security council: adds `rocketDAOProtocolProposal/Verifier`, `rocketDAOSecurity*`, `rocketNetworkVoting`, `rocketNetworkSnapshots`, `linkedListStorage`; separate RPL withdrawal address; time-based oracle |
| v1.3.1 | Houston hotfix | `OneDotThreeDotOne` `0xc2C81454427b1E53Fdf5d3B45561e3c18F90f9eD` | 2024 | post-Houston fix |
| — | **Saturn 0** | — (pDAO param vote) | 2024-10-28 | **No new code.** Removed mandatory RPL bond / collateral floor; RPL becomes optional commission-boost |
| v1.4 | **Saturn 1** | `OneDotFour` `0x5b3B5C76391662e56d0ff72F31B89C409316c8Ba` | 2026-02-18 | **Megapools** (one contract / node, many validators), **4-ETH bond**, **UARS** (Universal Adjustable Revenue Split, RPIP-46) + **RPL fee-switch**, express/standard deposit queues, `beaconStateVerifier` (SSZ proofs). Adds `rocketMegapool*`, `rocketNetworkRevenues`, `rocketNetworkSnapshotsTime`, `rocketDAOSecurityUpgrade`. **Legacy minipool creation disabled** |
| — | **Saturn 2** | *planned, not shipped* | — | bond curve (4→1.5 ETH), forced exits |

> Minipools (pre-Saturn) and megapools (Saturn) **coexist**: existing minipools keep operating; new validators use megapools. Monitor both event families.

---

## 2. Topics (chain-agnostic — `topic0 = keccak256(signature)`)

> **Shared topic0s:** `EtherDeposited(address,uint256,uint256)` (`0xef51b4c8…`) is emitted by **rETH, minipools, and RocketVault-adjacent**; `DepositReceived(address,uint256,uint256)` (`0x7aa1a8eb…`) by **both** `rocketDepositPool` and `rocketNodeDeposit`. Always disambiguate by the **emitting contract address**.

### 2.1 rETH — `rocketTokenRETH`
| topic0 | Event | ✓ |
|--------|-------|---|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` | ✓ |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address,address,uint256)` | ✓ |
| `0xef51b4c870b8b0100eae2072e91db01222a303072af3728e58c9d4d2da33127f` | `EtherDeposited(address indexed from, uint256 amount, uint256 time)` | ✓ |
| `0x6155cfd0fd028b0ca77e8495a60cbe563e8bce8611f0aad6fedbdaafc05d44a2` | `TokensMinted(address indexed to, uint256 amount, uint256 ethAmount, uint256 time)` | ✓ |
| `0x19783b34589160c168487dc7f9c51ae0bcefe67a47d6708fba90f6ce0366d3d1` | `TokensBurned(address indexed from, uint256 amount, uint256 ethAmount, uint256 time)` | ✓ |

> rETH **mint = `TokensMinted` / burn = `TokensBurned`** (both carry `ethAmount` at the exchange rate of that block). Plain `Transfer` from/to `0x0` also occurs.

### 2.2 RPL — `rocketTokenRPL` (new, inflationary) & `rocketTokenRPLFixedSupply` (old)
| topic0 | Event | ✓ |
|--------|-------|---|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` (both tokens) | ✓ |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address,address,uint256)` | ✓ |
| `0x4374b0955b3a09853fddeb2fd614040864f97881e39b7cf2f6edea1ec9415177` | `RPLInflationLog(address sender, uint256 value, uint256 inflationCalcTime)` | src |
| `0x6baaa7e377675e56cf5b72632742a306ea2dbb4df3aed1c5fb884af8ee436cff` | `RPLFixedSupplyBurn(address indexed from, uint256 amount, uint256 time)` (old→new swap burns) | src |

### 2.3 Deposit pool — `rocketDepositPool`
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x7aa1a8eb998c779420645fc14513bf058edb347d95c2fc2e6845bdc22f888631` | `DepositReceived(address indexed from, uint256 amount, uint256 time)` | ✓ |
| `0x3a6614e80d02b57255cbb1f8305fbeca53d7e05a4b779d406279196608512925` | `DepositRecycled(address indexed from, uint256 amount, uint256 time)` | ✓ |
| `0xa1811054b7d96716259cff0d366c2f6405951e0efe00c8db3e237cbf77fe7be9` | `DepositAssigned(address indexed minipool, uint256 amount, uint256 time)` (legacy minipool path) | src |
| `0x992f462cfb62e164bd03bf07baf2cffce83fbd9370cae10635842b2020012120` | `ExcessWithdrawn(address indexed to, uint256 amount, uint256 time)` | src |
| `0x4040156d881bd2ba289490b90281b228e6c221621274ce90999669f12d74ddfb` | `FundsRequested(address indexed receiver, uint256 validatorId, uint256 amount, bool expressQueue, uint256 time)` (Saturn megapool queue) | ✓ |
| `0x21d4fea1e00248ceff22105d25fec21f17b7134ab4881761ab27ac2d4249fdee` | `FundsAssigned(address indexed receiver, uint256 amount, uint256 time)` (Saturn) | ✓ |
| `0x795bf47f48111f2d01d87912d6b77fa833a62f0c4e2221ae9ecd474ec50d8b33` | `QueueExited(address indexed nodeAddress, uint256 time)` (Saturn) | ✓ |
| `0x77982616940619ddbda4afe3675280fff7c605d31503336add3633fbea69d8ba` | `CreditWithdrawn(address indexed nodeAddress, uint256 amount, uint256 time)` (Saturn) | ✓ |

### 2.4 Node deposit — `rocketNodeDeposit`
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x7aa1a8eb998c779420645fc14513bf058edb347d95c2fc2e6845bdc22f888631` | `DepositReceived(address indexed from, uint256 amount, uint256 time)` | ✓ |
| `0x93fa5225d22d9e30472233fc2b47735b2b138382fe4884fd10cfca52ba203491` | `MultiDepositReceived(address indexed from, uint256 numberOfValidators, uint256 totalBond, uint256 time)` (Saturn batch) | ✓ |
| `0x512d56e1f791d3bc07b8085104584ec42faefbefed34bbc0b881d8da16a8ebe1` | `DepositFor(address indexed nodeAddress, address indexed from, uint256 amount, uint256 time)` | ✓ |
| `0xc2b4a290c20fb28939d29f102514fbffd2b73c059ffba8b78250c94161d5fcc6` | `Withdrawal(address indexed nodeAddress, address indexed to, uint256 amount, uint256 time)` | src |

### 2.5 Node manager — `rocketNodeManager`
| topic0 | Event | ✓ |
|--------|-------|---|
| `0xf773bca07d020a1bc1fdd45ea3db573da547dd27180143afaf075c158a847594` | `NodeRegistered(address indexed node, uint256 time)` | ✓ |
| `0xed2d3ca39683fb0f50a70ed75c33a19bfe200e529d99e6f7518453b3fc4e9be4` | `NodeSmoothingPoolStateChanged(address indexed node, bool state)` | ✓ |
| `0xbb0b10d06b6fa081d0905e789877ce0321fafa4702ffeacaaff6e2d38063616a` | `NodeTimezoneLocationSet(address indexed node, uint256 time)` | src |
| `0x7c50987deec06761094239e9ff28caa9cfdd305f9c65011c284a0e40cbf4cfdc` | `NodeRewardNetworkChanged(address indexed node, uint256 network)` | src |
| `0x18702dcdad68e2a2d4350dc9f33402b58fd397352dd47a45312fccd5ff1e52a6` | `NodeRPLWithdrawalAddressSet(address indexed node, address indexed withdrawalAddress, uint256 time)` | src |
| `0xb62e03dab231209df2b46d49d4aa960deab93ff886a706653b5fc6b7ab57073f` | `NodeRPLWithdrawalAddressUnset(address indexed node, uint256 time)` | src |
| `0x9c5fd75ac09188c6d2033333e931eab1904109845a954b3c34e316c1f6a2bdb4` | `NodeUnclaimedRewardsAdded(address indexed node, uint256 amount, uint256 time)` | src |
| `0xf0f51ea0476a2f8619da054830fa16ff654d3fe5ab02e59256684c9d256b0874` | `NodeUnclaimedRewardsClaimed(address indexed node, uint256 amount, uint256 time)` | src |

### 2.6 Node staking (RPL) — `rocketNodeStaking`
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x27061f46a0d88c20b00223c4cabb9f6d02edcb48e4d61d72de015b4432f97647` | `RPLStaked(address indexed node, address from, uint256 amount, uint256 time)` (Saturn 4-arg) | ✓ |
| `0x4e3bcb61bb8e63cb9ed2c46d47eeb6ae847c629e909fbb32b9d17874affb4a89` | `RPLStaked(address indexed from, uint256 amount, uint256 time)` (legacy 3-arg) | src |
| `0xaa4c88f0b9828cd8487d897217facaaca2a112ead081957e1f7fc52f92149a04` | `RPLUnstaked(address indexed from, uint256 amount, uint256 time)` | ✓ |
| `0x0178232f2971603b3ffe89ab52d074a471507d935a7fee7477b636f72a645831` | `RPLLegacyUnstaked(address indexed to, uint256 amount, uint256 time)` | ✓ |
| `0x9947063f70b076145616018b82ed1dd5585e15b7ae0a0b17a8b06bec4c4c31e2` | `RPLWithdrawn(address indexed to, uint256 amount, uint256 time)` | ✓ |
| `0x38a2777b6a84fdb3fc375fe8ade69fdad1afdcdd93c79e7ae2319b806a626c4d` | `RPLSlashed(address indexed node, uint256 amount, uint256 ethValue, uint256 time)` | src |
| `0xb8502fe170368d1312ca3c9feac7aba9cd92406753d7eca9f11df9757081aec5` | `StakeRPLForAllowed(address indexed node, address indexed caller, bool allowed, uint256 time)` | src |
| `0x6b33e987d80ef301261d0265922ffe70da2b332f0e097034ce01dbb998cbd013` | `RPLLockingAllowed(address indexed node, bool allowed, uint256 time)` | src |
| `0xce4a5a05852c75132c79a7a41af76ced563f8391e69eea41a0b38214c4e847cf` | `RPLLocked(address indexed from, uint256 amount, uint256 time)` | src |
| `0x95f42213e171837caaa6cc7f589ef03a30179b7b85e386dfb146a30c5b10cfa9` | `RPLUnlocked(address indexed from, uint256 amount, uint256 time)` | src |
| `0x3bf4a4ef95ccf3119f6977afa759933d4edd361281f5c3b91203f43104fa3432` | `RPLTransferred(address indexed from, address indexed to, uint256 amount, uint256 time)` | src |
| `0x7a3b7812b93ab45ed01ea9fc22b37301461966d61ca09bc0859a84ca07298b12` | `RPLBurned(address indexed from, uint256 amount, uint256 time)` | src |

### 2.7 Network oracles — `rocketNetworkBalances` / `rocketNetworkPrices`
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x9b240d5b912ab6df93782930ae851a85b25e5a419c05cbb84d1b9e4b86a3c573` | `BalancesSubmitted(address indexed from, uint256 block, uint256 slotTimestamp, uint256 totalEth, uint256 stakingEth, uint256 rethSupply, uint256 blockTimestamp)` (per oDAO member) | ✓ |
| `0xdd27295717c4fbd48b1840f846e18be6f0b7bd6b55608e697e53b15848cecdf9` | `BalancesUpdated(uint256 indexed block, uint256 slotTimestamp, uint256 totalEth, uint256 stakingEth, uint256 rethSupply, uint256 blockTimestamp)` (consensus → drives rETH rate) | ✓ |
| `0x6a2507f84d6af44d2a9c355a7f1e3c4691b146051ce9501b429d8447ba9531c3` | `PricesSubmitted(address indexed from, uint256 block, uint256 slotTimestamp, uint256 rplPrice, uint256 time)` | ✓ |
| `0x6ef2ff813efc9efc76792366c4aca2677b755a5a13affc54d96ef35dc8e9bb73` | `PricesUpdated(uint256 indexed block, uint256 slotTimestamp, uint256 rplPrice, uint256 time)` (consensus → RPL/ETH price) | ✓ |

### 2.8 Minipool manager — `rocketMinipoolManager`
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x08b4b91bafaf992145c5dd7e098dfcdb32f879714c154c651c2758a44c7aeae4` | `MinipoolCreated(address indexed minipool, address indexed node, uint256 time)` | src |
| `0x3097cb0f536cd88115b814915d7030d2fe958943357cd2b1a9e1dba8a673ec69` | `MinipoolDestroyed(address indexed minipool, address indexed node, uint256 time)` | src |
| `0xebae778aeca850cfad423220d7978598785ef5905b868c482e03011b53808678` | `BeginBondReduction(address indexed minipool, uint256 time)` | src |
| `0x7cfaf8cd5e8153c2679a1100841445ab9926ef98867f41bd6e6afa9e3f09068e` | `CancelReductionVoted(address indexed minipool, address indexed member, uint256 time)` | src |
| `0xf5248f3aef129e8fd5ee9f0bd6dc051e7a9f3ad64e171a0acfb396298683bc24` | `ReductionCancelled(address indexed minipool, uint256 time)` | src |

### 2.9 Minipool (logic = `rocketMinipoolDelegate`, emitted by each minipool instance)
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x26725881c2a4290b02cd153d6599fd484f0d4e6062c361e740fbbe39e7ad6142` | `StatusUpdated(uint8 indexed status, uint256 time)` (0=Init,1=Prelaunch,2=Staking,3=Withdrawable,4=Dissolved) | src |
| `0xc038496c9b2fce7ae180c60886062197d0411e3c5d249053f188423280778a83` | `ScrubVoted(address indexed member, uint256 time)` | src |
| `0x90e131460b9acb17565f1719b9ebc49998aec6b07a4743a09b1b700545769eb6` | `BondReduced(uint256 previousBondAmount, uint256 newBondAmount, uint256 time)` | src |
| `0xac58888447082d81defc760f4bd30b6196d9309777e161bce72c280a12a6ea68` | `MinipoolScrubbed(uint256 time)` | src |
| `0x889f738426ec48d04c92bdcce1bc71c7aab6ba5296a4e92cc28a58c680b0a4ae` | `MinipoolPrestaked(bytes validatorPubkey, bytes validatorSignature, bytes32 depositDataRoot, uint256 amount, bytes withdrawalCredentials, uint256 time)` | src |
| `0xa5c869f853c40dbf5557240b202402a69e253565e0eb171fa239d8e95b1b1c2e` | `MinipoolPromoted(uint256 time)` | src |
| `0xf7cb92de8d4b074aafcfa9bdb83842b1ef40f49087a9eb04996d68a012de105c` | `MinipoolVacancyPrepared(uint256 bondAmount, uint256 currentBalance, uint256 time)` | src |
| `0xef51b4c870b8b0100eae2072e91db01222a303072af3728e58c9d4d2da33127f` | `EtherDeposited(address indexed from, uint256 amount, uint256 time)` (shared topic0 w/ rETH) | ✓ |
| `0xd5ca65e1ec4f4864fea7b9c5cb1ec3087a0dbf9c74641db3f6458edf445c4051` | `EtherWithdrawn(address indexed to, uint256 amount, uint256 time)` | src |
| `0x3422b68c7062367a3ae581f8bf64158ddb63f02294a0abe7f32491787076f1b7` | `EtherWithdrawalProcessed(address indexed executed, uint256 nodeAmount, uint256 userAmount, uint256 totalBalance, uint256 time)` | src |

### 2.10 Megapool (logic = `rocketMegapoolDelegate`, emitted by each megapool instance — Saturn)
| topic0 | Event | ✓ |
|--------|-------|---|
| `0x84b1b88115e84a1fe7f6aaad47a1d81d157c1ffc935548b21938ef3fbe696742` | `MegapoolValidatorEnqueued(uint256 indexed validatorId, uint256 time)` | ✓ |
| `0x03d2c6a900a8c2cfa1ac2b53629ccb3eac74f62cbae1ecc55a573c8ede337efe` | `MegapoolValidatorAssigned(uint256 indexed validatorId, uint256 time)` | ✓ |
| `0x91ade294eb3539e6fd4619324d40554e9db58857d06c1146ec0ac65645c64de5` | `MegapoolValidatorDequeued(uint256 indexed validatorId, uint256 time)` | src |
| `0x56ca8e01180cf71ca803ec95e3031a2c073dd627584a2987c00764ee33786300` | `MegapoolValidatorStaked(uint256 indexed validatorId, uint256 time)` | src |
| `0xbf4adfbfea0b3f07507ca1f6443b2cdfe688395253382abaaabc98e4323de6a6` | `MegapoolValidatorExited(uint32 indexed validatorId, uint256 time)` | src |
| `0x6e88e4e99452a51de0713c7389a6560ef4add87eb8c1f10ac142f2a09968b2a7` | `MegapoolValidatorExiting(uint256 indexed validatorId, uint256 time)` | src |
| `0x981470e3cfb4e4f090303837354bf5cb659a78f7aca03cc5914fbaa6f6272f37` | `MegapoolValidatorLocked(uint256 indexed validatorId, uint256 time)` | src |
| `0x65592ea0c3784f0d107857fd0ff2ba0f9f6f5e66a7b1b15ba50f29b6746998e3` | `MegapoolValidatorUnlocked(uint256 indexed validatorId, uint256 time)` | src |
| `0x7ff16245f17c8a4c78f1d07ba7ed00f74de75e5e0ace04861782de20b84e88ef` | `MegapoolValidatorDissolved(uint256 indexed validatorId, uint256 time)` | src |
| `0x7c2820e4291f03279f1e20dd15e1a40dae472fd64a910ae142ee11c0910f2fa5` | `MegapoolPenaltyApplied(uint256 amount, uint256 time)` | src |
| `0x3ad88db561c10d71049c6c0cf839070c4bb2187a7a0b988fdfbf51b170fe6a21` | `MegapoolDebtIncreased(uint256 amount, uint256 time)` | src |
| `0xc10045b78b6e6e9c98cfbae96361428c57abf1659755c7308234d8bba48bbfea` | `MegapoolDebtReduced(uint256 amount, uint256 time)` | src |
| `0x1bee82a0a43d4962b443e3025410bea9d902cd174c7347bce0e9aab7069d347a` | `MegapoolBondReduced(uint256 amount, uint256 time)` | src |
| `0xdfc66b0192dcfa0b3073892ad434e2714583b8afbf55182f82177b18d735a746` | `RewardsDistributed(uint256 nodeAmount, uint256 voterAmount, uint256 rethAmount, uint256 protocolDaoAmount, uint256 time)` (UARS split) | src |
| `0x38be9b012e428704c0fb2b81dfd53444b76ac4cd45c46cfd2d661f73d97cf47b` | `RewardsClaimed(uint256 amount, uint256 time)` (megapool — ≠ merkle distributor's) | src |

### 2.11 Rewards — `rocketRewardsPool` / `rocketMerkleDistributorMainnet`
`RewardSubmission` tuple = `(uint256 rewardIndex, uint256 executionBlock, uint256 consensusBlock, bytes32 merkleRoot, uint256 intervalsPassed, uint256 smoothingPoolETH, uint256 treasuryRPL, uint256 treasuryETH, uint256 userETH, uint256[] trustedNodeRPL, uint256[] nodeRPL, uint256[] nodeETH)`.

| topic0 | Event | ✓ |
|--------|-------|---|
| `0x60e3a6abeddae923bd65a9a5dcd11f9a8e38f12f885eef210b91203f3ca872b1` | `RewardSnapshotSubmitted(address indexed from, uint256 indexed rewardIndex, RewardSubmission submission, uint256 time)` | src |
| `0xcdc52a6101e59cdabb15ba2e286593326138db03833e45895356994d978d28f9` | `RewardSnapshot(uint256 indexed rewardIndex, RewardSubmission submission, uint256 intervalStartTime, uint256 intervalEndTime, uint256 time)` (≈ every 28 days) | src |
| `0x9db3f9087833aefdb2001771fb0fb203e141ba030cf295e8e4e99e8fc5eae8c2` | `RewardsClaimed(address indexed claimer, (uint256,uint256,uint256,uint256,bytes32[])[] )` (merkle distributor; Saturn struct-array form) | ✓ |

### 2.12 Auction — `rocketAuctionManager` (slashed-RPL Dutch auctions)
| topic0 | Event | ✓ |
|--------|-------|---|
| `0xa294be04865e7dbddbcedbb2dae8a4cffaae032aed7fc50a116463cfa23d2d76` | `LotCreated(uint256 indexed lotIndex, address indexed by, uint256 rplAmount, uint256 time)` | src |
| `0x51db8e23b3f4479b162fd48823b8402895442b8f6cfd94f66239391881ec7b6f` | `BidPlaced(uint256 indexed lotIndex, address indexed by, uint256 bidAmount, uint256 time)` | src |
| `0x25b6f7daa93beca7a95af59cfd1bf8e2039f834754cd34d1069a0dd1f72b2f0b` | `BidClaimed(uint256 indexed lotIndex, address indexed by, uint256 bidAmount, uint256 rplAmount, uint256 time)` | src |
| `0xcc1fa0e0974716b15b153109d0c222999771cafbff0e6e6c5957cccd8147f6af` | `RPLRecovered(uint256 indexed lotIndex, address indexed by, uint256 rplAmount, uint256 time)` | src |

### 2.13 Vault — `rocketVault` (holds all protocol ETH + tokens)
| topic0 | Event | ✓ |
|--------|-------|---|
| `0xbf25d6cb74c97a403cfab1c4c0abc9ffe3edd964de9924de0565f5ffe3d6ca79` | `EtherDeposited(string indexed by, uint256 amount, uint256 time)` | ✓ |
| `0xfc06bd2dc22238bad571c0432cfc04aee3d074be8cd974c9a9151e99df57e72b` | `EtherWithdrawn(string indexed by, uint256 amount, uint256 time)` | ✓ |
| `0x14c4e7cf1c77c463baf4198cf43a79854a178a5641b6e59a109d7ed539f410aa` | `TokenDeposited(bytes32 indexed key, address indexed tokenAddress, uint256 amount, uint256 time)` | src |
| `0xacd47105acf174819374e9d73c4c60bdaee9d4c7939b88a4cebb4dfe0500fbd8` | `TokenWithdrawn(bytes32 indexed key, address indexed tokenAddress, uint256 amount, uint256 time)` | src |

> **Governance events** (oDAO `rocketDAOProposal`, pDAO `rocketDAOProtocolProposal`, security `rocketDAOSecurityProposals`) — proposal/vote/execute signatures vary by DAO; pull the live ABI from the registered contract before alerting rather than hardcoding.

---

## 3. Function signatures (chain-agnostic — 4-byte selectors)

**✓** = confirmed via live `eth_call`. Others = keccak-256 of the verbatim `master` signature.

### 3.1 RocketStorage / upgrades
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x21f8a721` | `getAddress(bytes32)` → `address` | **The registry resolver.** key = `keccak256("contract.address",name)` |
| `0xca446dd9` | `setAddress(bytes32,address)` | gated to network contracts |
| `0x7ae1cfca` / `0xbd02d0f5` / `0x986e791a` | `getBool/getUint/getString(bytes32)` | typed getters |
| `0xaccd7d45` | `upgrade(string _type,string _name,string _abi,address _addr)` | on `rocketDAONodeTrustedUpgrade`; `_type ∈ addContract/upgradeContract/addABI/upgradeABI` |

### 3.2 rETH — `rocketTokenRETH`
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe6aa216c` | `getExchangeRate()` → `uint256` | ✓ ETH per 1 rETH (1e18) — live = 1.1644 |
| `0x8b32fa23` | `getEthValue(uint256 _rethAmount)` → `uint256` | rETH → ETH |
| `0x4346f03e` | `getRethValue(uint256 _ethAmount)` → `uint256` | ETH → rETH |
| `0xd6eb5910` | `getTotalCollateral()` → `uint256` | ETH held for instant burns |
| `0x852185fc` | `getCollateralRate()` → `uint256` | |
| `0x42966c68` | `burn(uint256 _rethAmount)` | redeem rETH → ETH |
| `0x94bf804d` | `mint(uint256 _ethAmount, address _to)` | internal (deposit pool only) |
| `0x6c985a88` / `0x188e0dc6` | `depositExcess()` / `depositExcessCollateral()` | ETH inflow / push excess to deposit pool |

### 3.3 RPL — `rocketTokenRPL`
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfe784eaa` | `swapTokens(uint256 _amount)` | **old fixed-supply RPL → new RPL, 1:1, no deadline** |
| `0x08824003` | `inflationMintTokens()` → `uint256` | mints RPL inflation to `rocketRewardsPool` |
| `0xee96d774` | `getInflationIntervalRate()` → `uint256` | ✓ live = 1.0001336…e18 |
| `0x7f79e64a` / `0xc32c367a` | `getInflationCalcTime()` / `getInflationRewardsContractAddress()` | |

### 3.4 Deposit pool — `rocketDepositPool`
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd0e30db0` | `deposit()` (payable) | **user stake → mint rETH** |
| `0x12065fe0` | `getBalance()` → `uint256` | ✓ live = 19.7 ETH |
| `0x1e35fed8` / `0xb7013dc1` / `0x888b042f` | `getNodeBalance()` / `getUserBalance()→int256` / `getExcessBalance()` | |
| `0x1eddb626` | `getMaximumDepositAmount()` → `uint256` | deposit cap |
| `0x1666f5e2` | `assignDeposits(uint256 _max)` | assign queued ETH to validators |
| `0x9a8dd16f` | `requestFunds(uint256 _bondAmount,uint32 _validatorId,uint256 _amount,bool _expressQueue)` | megapool only |
| `0x7d9d6074` | `exitQueue(address _nodeAddress,uint32 _validatorId,bool _expressQueue)` | megapool only |
| `0xef6f886a` | `withdrawCredit(uint256 _amount)` | node credit |

### 3.5 Node deposit — `rocketNodeDeposit`
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2cb47306` | `deposit(uint256 _bondAmount,bool _useExpressTicket,bytes _validatorPubkey,bytes _validatorSignature,bytes32 _depositDataRoot)` (payable) | **Saturn megapool validator** |
| `0xe75574d6` | `depositWithCredit(uint256,bool,bytes,bytes,bytes32)` (payable) | as above, spending node credit |
| `0xeee3f07a` / `0x1b9a91a4` | `depositEthFor(address)` / `withdrawEth(address,uint256)` | node ETH balance |

### 3.6 Node staking — `rocketNodeStaking`
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3e200d4b` | `stakeRPL(uint256 _amount)` | |
| `0xcb1c8321` | `stakeRPLFor(address _nodeAddress,uint256 _amount)` | |
| `0xed2fde70` | `unstakeRPL(uint256 _amount)` | Saturn |
| `0x33621a76` | `withdrawRPL()` | |
| `0x245395a6` | `slashRPL(address _nodeAddress,uint256 _ethSlashAmount)` | |
| `0xc601bf78` / `0x2c177a53` | `lockRPL(address,uint256)` / `unlockRPL(address,uint256)` | governance bonds |
| `0x73897be8` | `getNodeStakedRPL(address)` → `uint256` | |

### 3.7 Node manager — `rocketNodeManager`
| Selector | Signature |
|----------|-----------|
| `0x27c6f43e` | `registerNode(string _timezoneLocation)` |
| `0xa7e6e8b3` | `setTimezoneLocation(string)` |
| `0x99283f8b` | `setSmoothingPoolRegistrationState(bool)` |
| `0xf5b17b42` | `setRPLWithdrawalAddress(address,address,bool _confirm)` |
| `0x3a643648` / `0x2a7968eb` | `confirmRPLWithdrawalAddress(address)` / `unsetRPLWithdrawalAddress(address)` |

### 3.8 Minipool delegate — `rocketMinipoolDelegate` (called on a minipool instance)
| Selector | Signature |
|----------|-----------|
| `0xf7ae36d1` | `stake(bytes _validatorSignature,bytes32 _depositDataRoot)` |
| `0x13dc01dc` | `promote()` |
| `0x54efc6e5` | `distributeBalance(bool _rewardsOnly)` |
| `0xf09fa332` / `0x590e1ae3` | `beginUserDistribute()` / `refund()` |
| `0x3bef8a3a` / `0x43d726d6` / `0xa4399263` | `dissolve()` / `close()` / `finalise()` |
| `0xe117d192` / `0xd191ea9c` | `voteScrub()` / `reduceBondAmount()` |

### 3.9 Megapool delegate — `rocketMegapoolDelegate` (called on a megapool instance — Saturn)
| Selector | Signature |
|----------|-----------|
| `0x94a67ef9` | `newValidator(uint256 _bondAmount,bool _useExpressTicket,bytes _validatorPubkey,bytes _validatorSignature,bytes32 _depositDataRoot)` |
| `0x7fcfb7c2` / `0xc310ee63` | `stake(uint32 _validatorId)` / `dequeue(uint32)` |
| `0x687fe439` | `dissolveValidator(uint32)` |
| `0x1b99d9d6` / `0xe4fc6b6d` / `0x4e71d92d` | `repayDebt()` / `distribute()` / `claim()` |
| `0x96c212e8` | `reduceBond(uint256)` |

### 3.10 Misc
| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x1d3d3538` / `0x9979ef45` / `0x21113057` / `0x767a6d2f` | `createLot()` / `placeBid(uint256)` / `claimBid(uint256)` / `recoverUnclaimedRPL(uint256)` | `rocketAuctionManager` |
| `0xf07f75ab` / `0xf21c150c` | `submitRewardSnapshot(RewardSubmission)` / `getRewardIndex()` ✓(=49) | `rocketRewardsPool` |
| `0x12c5f9e3`-ish | `submitBalances(uint256,uint256,uint256,uint256,uint256)` | `rocketNetworkBalances` (oDAO report) |

---

## 4. Addresses — Ethereum mainnet (chain ID 1)

All resolved **live** from `RocketStorage` 2026-05-29 and confirmed to hold code (except where noted). Registry name = the string used in `keccak256("contract.address", name)`.

### 4.1 Core / tokens / infra (⛔ = never upgradeable)
| Registry name | Address | One-liner |
|------|---------|-----------|
| `rocketStorage` | `0x1d8f8f00cfa6758d7bE78336684788Fb0ee0Fa46` | ⛔ Eternal-storage hub + registry; the one safe entry point |
| `rocketVault` ⛔ | `0x3bDC69C4E5e13E52A65f5583c23EFB9636b469d6` | Holds all protocol ETH + tokens |
| `rocketTokenRETH` ⛔ | `0xae78736Cd615f374D3085123A210448E74Fc6393` | rETH — non-rebasing LST |
| `rocketTokenRPL` ⛔ | `0xD33526068D116cE69F19A9ee46F0bd304F21A51f` | RPL — inflationary governance/collateral token |
| `rocketTokenRPLFixedSupply` ⛔ | `0xb4efd85c19999d84251304bda99e90b92300bd93` | Old fixed-supply RPL (swap source) |
| `casperDeposit` ⛔ | `0x00000000219ab540356cBB839Cbe05303d7705Fa` | Beacon-chain ETH2 deposit contract (registered alias) |
| `rocketMinipoolPenalty` ⛔ | `0xE64AC47b6e2FEcfCDEA35147Fe61af9894A06ba6` | Minipool penalty rate |
| `addressQueueStorage` | `0x44E31944E1A6F3b8F805E105B130F8bdb7E2EBd8` | Utility: queues |
| `addressSetStorage` | `0xD4ae2511dF21F367792bA4D67c6eb032171c6a16` | Utility: sets |
| `linkedListStorage` | `0x52590E8aaC140E2020f8F51695719922ebcCb6D6` | Utility: deposit queues (Houston) |
| `beaconStateVerifier` | `0xE9a114c50f26001443B91079Ab5573a90D2D8469` | SSZ Beacon-state proof verifier (Saturn) |
| *(periphery, not in registry)* `RocketSwapRouter` | `0x16D5A408e807db8eF7c578279BEeEe6b228f1c1C` | rETH/RPL swap aggregator (Balancer+Uniswap). **Resolved via getCode, NOT RocketStorage** |

### 4.2 Deposits / nodes / minipools
| Registry name | Address | One-liner |
|------|---------|-----------|
| `rocketDepositPool` | `0xCE15294273CFb9D9b628F4D61636623decDF4fdC` | User ETH → rETH; queue/assignment |
| `rocketNodeDeposit` | `0x6B13698c306a297Fee1383cdC2c65d63781D2D47` | Node operator validator deposits |
| `rocketNodeManager` | `0xcf2d76A7499d3acB5A22ce83c027651e8d76e250` | Node registration / settings |
| `rocketNodeStaking` | `0xedFc7DCaE43fF954577a2875a9D805874490eE3E` | RPL stake / unstake |
| `rocketNodeDistributorFactory` | `0xe228017f77B3E0785e794e4c0a8A6b935bB4037C` | Deploys per-node fee distributors |
| `rocketNodeDistributorDelegate` | `0x35A85d4c115801395e6E3abAa784Fb05826f129D` | Node distributor logic (delegate) |
| `rocketMinipoolManager` | `0xe54B8C641fd96dE5D6747f47C19964c6b824D62C` | Creates/tracks minipools |
| `rocketMinipoolDelegate` | `0x03d30466d199Ef540823fe2a22CAE2E3b9343bb0` | Minipool logic (delegate) |
| `rocketMinipoolBase` | `0x560656C8947564363497E9C78A8BDEff8d3EFF33` | Minipool proxy base + delegate-upgrade |
| `rocketMinipoolBondReducer` | `0xDe8Ab526b19FCA2D5a57c4A78b698041717BE591` | 16→8 bond reduction + oDAO scrub |
| `rocketMinipoolFactory` | `0x7B8c48256CaF462670f84c7e849cab216922B8D3` | Minipool CREATE2 factory |
| `rocketMinipoolQueue` | `0x9e966733e3E9BFA56aF95f762921859417cF6FaA` | Legacy minipool assignment queue |
| `rocketMinipoolStatus` | `0xa52451b9d25EEf02BE42B3A8161A18f947F8A6a5` | oDAO minipool status updates |

### 4.3 Megapools (Saturn 1)
| Registry name | Address | One-liner |
|------|---------|-----------|
| `rocketMegapoolFactory` | `0xD5bffeaa9f373B9C367132772FAA0b88e3F0E38b` | Deploys per-node megapool clones (CREATE2) |
| `rocketMegapoolProxy` | `0x1B389D76a04d01026c5f5B0a125D4CCF26F9cd51` | **Clone target** for every node's megapool; delegatecalls the delegate |
| `rocketMegapoolDelegate` | `0xca3DD4bee7C174903dBF66c3897c27E9ADaAEBdD` | Megapool logic (force-upgradeable delegate) |
| `rocketMegapoolManager` | `0xf2CCd522Ba5fFEda28fe0389963845D61F342034` | Megapool/validator management |
| `rocketMegapoolPenalties` | `0xa2afC3C2d8ea4eBdbE925cADe17c29517630e6aB` | Megapool penalty consensus |

### 4.4 Network / oracles
| Registry name | Address | One-liner |
|------|---------|-----------|
| `rocketNetworkBalances` | `0x1D9F14C6Bfd8358b589964baD8665AdD248E9473` | oDAO total-balance reports → **rETH rate** |
| `rocketNetworkPrices` | `0x25E54Bf48369b8FB25bB79d3a3Ff7F3BA448E382` | oDAO **RPL price** reports |
| `rocketNetworkFees` | `0xf824e2d69dc7e7c073162C2bdE87dA4746d27a0f` | Node commission curve |
| `rocketNetworkPenalties` | `0xeD0493DE30e82bE7C16C8925C7204CE9D1136B3a` | Minipool penalty consensus |
| `rocketNetworkVoting` | `0x994A9C49230FEC0c127B8F42D6c5288F02610AeD` | On-chain voting power (Houston) |
| `rocketNetworkSnapshots` | `0xe37F2d9dFb7397caF671DF5190a5dFB601028f17` | Checkpoint snapshots (Houston) |
| `rocketNetworkSnapshotsTime` | `0x569F5b3024054AB4049A50df223a747AFE18a891` | Time-based snapshots (Saturn) |
| `rocketNetworkRevenues` | `0x9D9708dA8E0200Dd8Dd9ad09e0AAf184Ad260842` | UARS revenue-split accounting (Saturn) |

### 4.5 Rewards
| Registry name | Address | One-liner |
|------|---------|-----------|
| `rocketRewardsPool` | `0xCba5951fc706Fc783b7C142DaE8576Ebe29c41FD` | Rewards-interval orchestration (index = 49) |
| `rocketSmoothingPool` | `0xd4E96eF8eee8678dBFf4d535E033Ed1a4F7605b7` | Collects priority fees + MEV (Redstone) |
| `rocketMerkleDistributorMainnet` | `0xE4E2612EE8d7fdc8518Faea85770A3b9c886E2f5` | Merkle RPL+ETH reward claims |
| `rocketClaimDAO` | `0xfB2F2Ab63DCf412ced6cdE5f4f809215ed0c81aa` | pDAO treasury spends |

### 4.6 oDAO (trusted node DAO) — `rocketDAONodeTrusted*`
| Registry name | Address |
|------|---------|
| `rocketDAONodeTrusted` | `0xb8e783882b11Ff4f6Cef3C501EA0f4b960152cc9` |
| `rocketDAONodeTrustedActions` | `0x029d946F28F93399a5b0D09c879FC8c94E596AEb` |
| `rocketDAONodeTrustedProposals` | `0xb0ec3F657ef43A615aB480FA8D5A53BF2c2f05d5` |
| `rocketDAONodeTrustedUpgrade` | `0x9290AA076a2F1418a4E414E3D83AE03cA8E1ad10` |
| `rocketDAONodeTrustedSettingsMembers` | `0xdA1AB39e62E0A5297AF44C7064E501b0613f0D01` |
| `rocketDAONodeTrustedSettingsProposals` | `0xAD038f8994a6bd51C8A72D3721CEd83401D4d2b0` |
| `rocketDAONodeTrustedSettingsMinipool` | `0xE535fA45e12d748393C117C6D8EEBe1a7D124d95` |
| `rocketDAONodeTrustedSettingsRewards` | `0x7322c24752f79c05FFD1E2a6FCB97020C1C264F1` |
| `rocketDAOProposal` | `0x1e94e6131Ba5B4F193d2A1067517136C52ddF102` |

### 4.7 pDAO (protocol DAO) — `rocketDAOProtocol*`
| Registry name | Address |
|------|---------|
| `rocketDAOProtocol` | `0xCaC25e88276A333cF9d4196d112D93af67ef809A` |
| `rocketDAOProtocolProposals` | `0xcf7F6E23cD8189B7F56b14F66e11241C8ac0F03b` |
| `rocketDAOProtocolProposal` | `0x2D627A50Dc1C4EDa73E42858E8460b0eCF300b25` |
| `rocketDAOProtocolVerifier` | `0xd1f7e573cdC64FC0B201ca37aB50bC7Dd880040A` |
| `rocketDAOProtocolActions` | `0xB50d513de40eE70A662c39207b4382a693f9e08D` ⚠ 136 B (stub) |
| `rocketDAOProtocolSettingsAuction` | `0x364F989A3C9a1F66cB51b9043680974eA08C0d18` |
| `rocketDAOProtocolSettingsDeposit` | `0x227BE8dD01DF8ad9BED0178e4F8cEC2996C5c365` |
| `rocketDAOProtocolSettingsInflation` | `0x1d4AAEaE7C8b75a8e5ab589a84516853DBDdd735` |
| `rocketDAOProtocolSettingsMinipool` | `0xaeF94C3650AA13d7A2456477fc374a16b94B9152` |
| `rocketDAOProtocolSettingsNetwork` | `0x67Fd03a5095197D1aD1F932BC55E022C420b1153` |
| `rocketDAOProtocolSettingsNode` | `0xb02B883303e658Ddcd58D3871Dc4Ca0C91f0fc9D` |
| `rocketDAOProtocolSettingsRewards` | `0x8857610Ba0A7caFD4dBE1120bfF03E9c74fc4124` |
| `rocketDAOProtocolSettingsProposals` | `0xf6ad771dfB1cd10c66F688E251b5E5c21cbfDF81` |
| `rocketDAOProtocolSettingsSecurity` | `0xC9D771AaF504F33bB3C8a7E67eA9f1881F837cFf` |
| `rocketDAOProtocolSettingsMegapool` | `0x40628FAAc22383327b9f7bBc86CD1857050A2dCe` |

### 4.8 Security council (Houston) — `rocketDAOSecurity*`
| Registry name | Address |
|------|---------|
| `rocketDAOSecurity` | `0x84aE6D61Df5c6ba7196b5C76Bcb112B8a689aD37` |
| `rocketDAOSecurityActions` | `0xeaa442dF4Bb5394c66C8024eFb4979bEc89Eb59a` |
| `rocketDAOSecurityProposals` | `0x334B9B1a6F9d7531efb13746482ff40f1c2a0c4e` |
| `rocketDAOSecurityUpgrade` | `0x950BaF0358164339114914169BF16754789B5Dc4` |

### 4.9 Upgrade contracts (historical, still registered) & governance multisigs
| Name | Address | Maps to |
|------|---------|---------|
| `rocketUpgradeOneDotOne` | `0xC680a22b4F03977f69b51A09f3Dbe922eb77C8FE` | Redstone |
| `rocketUpgradeOneDotTwo` | `0x9a0b5d3101d111EA0edD573d45ef2208CC97984a` | Atlas |
| `rocketUpgradeOneDotThree` | `0x5dC69083B68CDb5c9ca492A0A5eC581e529fb73C` | Houston |
| `rocketUpgradeOneDotThreeDotOne` | `0xc2C81454427b1E53Fdf5d3B45561e3c18F90f9eD` | Houston hotfix |
| `rocketUpgradeOneDotFour` | `0x5b3B5C76391662e56d0ff72F31B89C409316c8Ba` | Saturn 1 |
| GMC Safe (off-registry) | `0x6efD08303F42EDb68F2D6464BCdCA0824e1C813a` | Grants committee multisig |
| IMC Safe (off-registry) | `0xb867EA3bBC909954d737019FEf5AB25dFDb38CB9` | Incentives committee multisig |

### 4.10 Deprecated / replaced addresses (de-registered by upgrades)
Old logic addresses leave the registry on `upgradeContract`. Reconstruct any contract's full history from `ContractUpgraded`/`ContractAdded` events on `rocketDAONodeTrustedUpgrade`. Documented chain for the deposit pool:
| Version | Old `rocketDepositPool` address | Replaced by |
|---------|-------------------|-------------|
| v1.0 (launch) | `0x4D05E3d48a938db4b7a9A59A802D5b45011BDe58` | Redstone |
| v1.1 (Redstone) | `0x2cac916b2A963Bf162f076C0a8a4a8200BCFBfb4` | Atlas |
| v1.2 (Atlas) | `0xDD3f50F8A6CafbE9b31a427582963f465E745AF8` | later upgrade |
| current | `0xCE15294273CFb9D9b628F4D61636623decDF4fdC` | live (§4.2) |

Also fully removed in Redstone: `rocketClaimNode`, `rocketClaimTrustedNode` (replaced by the Merkle distributor).

---

## 5. Proxies (old & new) — Rocket Pool is NOT EIP-1967

| Pattern | Where | How it works |
|---------|-------|--------------|
| **Registry "upgrade by re-registration"** | All network contracts (§4.2–4.8) | No proxy. Logic is a plain contract; `RocketStorage` maps name→address. Upgrade = register new address + de-register old (delayed + veto since Saturn). **Address changes on upgrade.** EIP-1967 impl slot is irrelevant/empty. |
| **Minipool delegatecall proxy** | Each minipool instance | `RocketMinipoolBase` proxy stores its delegate (`rocketMinipoolDelegate`) and `delegatecall`s it. Node operators opt into delegate upgrades (`delegateUpgrade`). |
| **Node fee-distributor proxy** | Each node's distributor | `RocketNodeDistributor` proxy → `delegatecall` `rocketNodeDistributorDelegate`. |
| **Megapool: EIP-1167 clone → proxy → delegate** (Saturn) | Each node's megapool | `rocketMegapoolFactory` deploys a **45-byte EIP-1167 minimal-proxy clone of `rocketMegapoolProxy` (`0x1B389D76…`)**. `RocketMegapoolProxy` then `delegatecall`s the registry-resolved `rocketMegapoolDelegate`, enabling **pDAO-forced delegate upgrades** (RPIP-47). Decoded clone runtime: `363d3d373d3d3d363d73 1b389d76a04d01026c5f5b0a125d4ccf26f9cd51 5af43d82803e903d91602b57fd5bf3`. |
| **Immutable (⛔)** | rETH, RPL, fixed-supply RPL, Vault, casperDeposit, MinipoolPenalty | Hard-coded reverts in the upgrade path — addresses are permanent. |

> To find a node's megapool: `rocketMegapoolFactory.getExpectedAddress(node)` / `getMegapoolDeployed(node)`. Megapool **events emit from the clone address**, not the factory/manager.

---

## 6. Detection invariants & gotchas

1. **Resolve, don't hardcode.** Only `RocketStorage 0x1d8f…0Fa46` is permanent (+ the six ⛔ contracts). Every other address can change on upgrade — read it from the registry at the block you care about.
2. **rETH rate lives in `rocketNetworkBalances`.** `BalancesUpdated` (consensus) is the rebase-equivalent: rETH never rebases, the rate (`getExchangeRate`) steps up when this fires (~daily). Per-member `BalancesSubmitted` precedes it.
3. **Two validator worlds coexist.** Legacy minipools (`MinipoolCreated`, `StatusUpdated`, one contract/validator) **and** Saturn megapools (`MegapoolValidator*`, one contract/node). New minipool creation is **disabled** post-Saturn — new validators are megapool-only (`rocketNodeDeposit.deposit/depositWithCredit`, `MultiDepositReceived`).
4. **Shared topic0s** — `EtherDeposited(address,uint256,uint256)` (`0xef51b4c8…`) and `DepositReceived(address,uint256,uint256)` (`0x7aa1a8eb…`) are each emitted by multiple contracts. **Filter by emitting address.**
5. **rETH mint/burn = `TokensMinted`/`TokensBurned`** (not just `Transfer` from/to 0x0); both carry the `ethAmount`.
6. **Two RPL tokens.** New inflationary `0xD335…A51f` vs old fixed-supply `0xb4ef…bd93`; `swapTokens` migrates 1:1 forever. Saturn flips RPL toward an ETH revenue-share (`rocketNetworkRevenues`, megapool `RewardsDistributed`).
7. **`RPLStaked` has two forms** — Saturn 4-arg (`0x27061f46…`, live) and legacy 3-arg (`0x4e3bcb61…`). Index both for full history. Likewise `RPLUnstaked` (new) vs `RPLLegacyUnstaked`.
8. **Oracle reports are time-based since Houston** — submissions carry a `slotTimestamp` + `blockTimestamp` (hence the 7-arg `BalancesSubmitted` / 5-arg `PricesSubmitted`).
9. **Rewards snapshots are ~28-day** (`RewardSnapshot`, rewardIndex=49 now); claims via merkle distributor `RewardsClaimed` (Saturn struct-array form `0x9db3f908…`, **different** from the megapool `RewardsClaimed(uint256,uint256)`).
10. **All protocol funds sit in `rocketVault`** — watch its `EtherDeposited`/`EtherWithdrawn(string,uint256,uint256)` (string key = the owning contract name).
11. **No core protocol off Ethereum.** Any rETH on an L2 is bridged (see [l2.md](l2.md)); there is no minipool/megapool/staking anywhere but mainnet.

---

## 7. Quick-copy constants (bytea-ready for Postgres)

```
-- Registry + resolver
ROCKET_STORAGE              = '\x1d8f8f00cfa6758d7be78336684788fb0ee0fa46'
SEL_GET_ADDRESS             = '\x21f8a721'   -- getAddress(bytes32); key=keccak256("contract.address",name)

-- Tokens (immutable)
RETH                        = '\xae78736cd615f374d3085123a210448e74fc6393'
RPL                         = '\xd33526068d116ce69f19a9ee46f0bd304f21a51f'
RPL_FIXED_SUPPLY            = '\xb4efd85c19999d84251304bda99e90b92300bd93'
ROCKET_VAULT                = '\x3bdc69c4e5e13e52a65f5583c23efb9636b469d6'

-- Hot contracts
DEPOSIT_POOL                = '\xce15294273cfb9d9b628f4d61636623decdf4fdc'
NODE_DEPOSIT                = '\x6b13698c306a297fee1383cdc2c65d63781d2d47'
NODE_MANAGER                = '\xcf2d76a7499d3acb5a22ce83c027651e8d76e250'
NODE_STAKING                = '\xedfc7dcae43ff954577a2875a9d805874490ee3e'
NETWORK_BALANCES            = '\x1d9f14c6bfd8358b589964bad8665add248e9473'
NETWORK_PRICES              = '\x25e54bf48369b8fb25bb79d3a3ff7f3ba448e382'
MINIPOOL_MANAGER            = '\xe54b8c641fd96de5d6747f47c19964c6b824d62c'
MEGAPOOL_PROXY_TEMPLATE     = '\x1b389d76a04d01026c5f5b0a125d4ccf26f9cd51'
MEGAPOOL_DELEGATE           = '\xca3dd4bee7c174903dbf66c3897c27e9adaaebdd'
MERKLE_DISTRIBUTOR          = '\xe4e2612ee8d7fdc8518faea85770a3b9c886e2f5'

-- rETH topics
TOPIC_RETH_TOKENS_MINTED    = '\x6155cfd0fd028b0ca77e8495a60cbe563e8bce8611f0aad6fedbdaafc05d44a2'
TOPIC_RETH_TOKENS_BURNED    = '\x19783b34589160c168487dc7f9c51ae0bcefe67a47d6708fba90f6ce0366d3d1'
TOPIC_ETHER_DEPOSITED       = '\xef51b4c870b8b0100eae2072e91db01222a303072af3728e58c9d4d2da33127f'
-- Deposit pool
TOPIC_DEPOSIT_RECEIVED      = '\x7aa1a8eb998c779420645fc14513bf058edb347d95c2fc2e6845bdc22f888631'
TOPIC_FUNDS_REQUESTED       = '\x4040156d881bd2ba289490b90281b228e6c221621274ce90999669f12d74ddfb'
TOPIC_FUNDS_ASSIGNED        = '\x21d4fea1e00248ceff22105d25fec21f17b7134ab4881761ab27ac2d4249fdee'
-- Node deposit / staking
TOPIC_MULTI_DEPOSIT_RECVD   = '\x93fa5225d22d9e30472233fc2b47735b2b138382fe4884fd10cfca52ba203491'
TOPIC_RPL_STAKED            = '\x27061f46a0d88c20b00223c4cabb9f6d02edcb48e4d61d72de015b4432f97647'
TOPIC_RPL_UNSTAKED          = '\xaa4c88f0b9828cd8487d897217facaaca2a112ead081957e1f7fc52f92149a04'
-- Oracles
TOPIC_BALANCES_UPDATED      = '\xdd27295717c4fbd48b1840f846e18be6f0b7bd6b55608e697e53b15848cecdf9'
TOPIC_PRICES_UPDATED        = '\x6ef2ff813efc9efc76792366c4aca2677b755a5a13affc54d96ef35dc8e9bb73'
-- Minipool / megapool
TOPIC_MINIPOOL_CREATED      = '\x08b4b91bafaf992145c5dd7e098dfcdb32f879714c154c651c2758a44c7aeae4'
TOPIC_MINIPOOL_STATUS       = '\x26725881c2a4290b02cd153d6599fd484f0d4e6062c361e740fbbe39e7ad6142'
TOPIC_MEGAPOOL_ENQUEUED     = '\x84b1b88115e84a1fe7f6aaad47a1d81d157c1ffc935548b21938ef3fbe696742'
TOPIC_MEGAPOOL_ASSIGNED     = '\x03d2c6a900a8c2cfa1ac2b53629ccb3eac74f62cbae1ecc55a573c8ede337efe'
TOPIC_MEGAPOOL_STAKED       = '\x56ca8e01180cf71ca803ec95e3031a2c073dd627584a2987c00764ee33786300'
-- Rewards
TOPIC_REWARD_SNAPSHOT       = '\xcdc52a6101e59cdabb15ba2e286593326138db03833e45895356994d978d28f9'
TOPIC_REWARDS_CLAIMED_MERKLE= '\x9db3f9087833aefdb2001771fb0fb203e141ba030cf295e8e4e99e8fc5eae8c2'
```

---

## 8. Verification & sources

- **Addresses (live):** all §4 registry entries resolved via `RocketStorage.getAddress(keccak256("contract.address",name))` on `ethereum-rpc.publicnode.com` (2026-05-29, block ~25,200,909), confirmed non-empty `eth_getCode`, EIP-55 re-checksummed locally. Periphery/old/multisig addresses confirmed via direct `eth_getCode`.
- **Topics (✓):** observed in live `eth_getLogs` (rETH, RPL, deposit pool, node deposit/manager/staking, network balances/prices, merkle distributor) and in tx receipts `0x638100cf…`/`0x4bab98c7…` (megapool `MegapoolValidatorEnqueued`/`MegapoolValidatorAssigned`, vault Ether events). Others (**src**) are keccak-256 of verbatim signatures from `rocket-pool/rocketpool` `master`; the 24 high-frequency ✓ topics were also keccak-recomputed and matched on-chain byte-for-byte (incl. via the openchain signature DB).
- **Selectors:** keccak-256 of `master` signatures; `getExchangeRate`, `getInflationIntervalRate`, `getBalance`, `getLotCount`, `getRewardIndex` confirmed live via `eth_call`.
- **Versions / upgrade-contract mapping:** confirmed live (`rocketUpgradeOneDot{One..Four}` + `…ThreeDotOne` all registered) and cross-checked against the official upgrade docs.

Sources: [`rocket-pool/rocketpool`](https://github.com/rocket-pool/rocketpool) (`contracts/contract/**`, `contracts/types/RewardSubmission.sol`) · [docs.rocketpool.net — contract addresses & upgrades](https://docs.rocketpool.net/) · [RPIPs](https://rpips.rocketpool.net/) (31/32/33/35, 42/46/47, 58/59/60/61/65) · live `RocketStorage` on Ethereum mainnet. L2/bridged rETH in [l2.md](l2.md).
