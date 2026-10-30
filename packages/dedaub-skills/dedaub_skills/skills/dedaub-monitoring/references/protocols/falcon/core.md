# Falcon Finance — Topics, Selectors, Addresses (Ethereum, BNB Smart Chain, Base)

**Status:** verified against live RPC on all nine target chains, Etherscan/Blockscout verified source, Sourcify (BNB), and the official `docs.falcon.finance` contract list on 2026-10-30.
**Scope:** USDf (synthetic dollar), sUSDf (ERC-4626 staking vault), Falcon Position NFTs (Boosted Yield lock), the on-chain mint path (PreCollateralizedMinter + FalconBundler), the rewards distributors, the FF token, sFF / sFF-Prime staking, the USDf-paying Staking Vaults, the Chainlink feeds, and the CCIP pools and bridged tokens. Ethereum (1) is the home chain. BNB Smart Chain (56) has bridged USDf + FF and two Staking Vaults. Base (8453) has bridged USDf only. Topics and selectors are chain-agnostic. Addresses are network-specific.

Falcon is a **custodial, KYC-gated** synthetic-dollar protocol. Users deposit collateral (stablecoins, BTC, ETH, RWAs, etc.) to off-chain custodians through the Falcon app. **There is no on-chain collateral vault and no on-chain redeem contract.** Classic Mint, Innovative Mint, redemptions and claims are settled off-chain. On-chain, the only USDf mint path is `PreCollateralizedMinter.preCollateralizedMint`, which mints against an EIP-712 signature from a `MINTER_ROLE` signer and emits `MintExecuted(collateralRef, …)`. A redemption shows on-chain only as a USDf `Transfer` to a Falcon address. Daily yield is minted as new USDf and pushed into sUSDf through `StakingRewardsDistributor.transferInRewards`.

USDf, sUSDf, the Position NFTs and sFF are **OpenZeppelin v5 TransparentUpgradeableProxies** (793-byte proxy, one `ProxyAdmin` per proxy). FF and every helper contract are immutable. Cross-chain USDf and FF use **Chainlink CCIP** (Lock/Release on Ethereum, Burn/Mint `BurnMintERC20` on BNB and Base). There is no LayerZero OFT. sUSDf and sFF exist on Ethereum only.

---

## 0. Contract families

| Contract | Role | Proxy? | Verified name |
|----------|------|--------|---------------|
| **USDf** | ERC-20 + permit synthetic dollar, 18 dec. `MINTER_ROLE` / `BURNER_ROLE` / admin blacklist (`setRestriction`). | Transparent | `USDf` |
| **sUSDf** | ERC-4626 vault over USDf. Rewards vest linearly over `vestingPeriod` (86 400 s). Optional cooldown via `USDfSilo` (now **off**, `cooldownDuration()=0`). | Transparent | `StakedUSDf` |
| **USDfSilo** | Holds USDf during sUSDf cooldowns. | No | `USDfSilo` |
| **Falcon Position** (`FALCON`) | ERC-721 Boosted-Yield lock: sUSDf locked for a fixed tenure; boosted sUSDf paid at maturity. | Transparent | `FalconPosition` |
| **StakingRewardsDistributor** | Holds `REWARDER_ROLE` on sUSDf; operator calls `transferInRewards`. Pausable. | No | `StakingRewardsDistributor` |
| **PreCollateralizedMinter** | **Sole on-chain USDf minter.** EIP-712 signed mints, nonce bitmap. | No | `PreCollateralizedMinter` |
| **FalconBundler** (v2, live) | `OPERATOR_ROLE` bundles mint → sUSDf → Position NFT. Public `stakeToFalconPosition`. | No | `FalconBundler` |
| **FF** | Governance/utility token. Fixed 10 B supply, no admin, no mint. Deployed by CREATE2 (`0x4e59b448…`). | No | `FF` |
| **sFF** | ERC-4626 vault over FF (same code base as sUSDf). Cooldown **on** (259 200 s = 3 d) via `FFSilo`. | Transparent | `StakedFF` |
| **sFF-Prime** | FalconPosition fork that locks **FF** (`sFalconAsset()` = FF). | Transparent | `FalconPosition` |
| **StakingRewardsDistributorFF** | Rewarder of sFF. | No | `StakingRewardsDistributorFF` |
| **StakingRewards** ("Staking Vaults") | Synthetix-style vaults: stake token X, earn USDf, 180-day lockup + 3-day cooldown. `MANAGER_ROLE` can `pullFunds` the staked tokens. Factory-deployed. | No | `StakingRewards`, `StakingRewardsFactory` |
| **LockReleaseTokenPool** / **BurnMintTokenPool** | Chainlink CCIP v1.5.1 token pools. | No | — |
| **USDf / FF on BNB, USDf on Base** | Chainlink `BurnMintERC20` (roles: `MINTER_ROLE`, `BURNER_ROLE`; `getCCIPAdmin`). | No | `BurnMintERC20` |
| FF claim contracts | `Claim`, `ClaimNoVestFull`, `VestingClaim`, `VestingClaimV2` (Merkle airdrop/vesting of FF). | No | as named |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 USDf (Ethereum proxy) and BurnMintERC20 (BNB/Base USDf, BNB FF)

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — mint = `from=0`, burn = `to=0` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |
| `0xf28feb0f201748ef16ccc442dd23ba17ae3e2957006c4e351a718bcd5f65d516` | `AddressRestrictionSet(address indexed account, bool restricted)` — **USDf blacklist (Ethereum only)** |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` |
| `0x9524c9e4b0b61eb018dd58a1cd856e3e74009528328ab4a613b434fa631d7242` | `CCIPAdminTransferred(address indexed previousAdmin, address indexed newAdmin)` — BurnMintERC20 only |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` |
| `0x0a6387c9ea3628b88a633bb4f3b151770f70085117a15f9bf3787cda53f13d31` | `EIP712DomainChanged()` |

Role ids: `DEFAULT_ADMIN_ROLE` = `0x00…00`; `MINTER_ROLE` = `0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6`; `BURNER_ROLE` = `0x3c11d16cbaffd01df69ce1c404f6340ee057498f5f00246190ea54220576a848`; `REWARDER_ROLE` = `0xbeec13769b5f410b0584f69811bfd923818456d5edcf426b0e31cf90eed7a3f6`; `OPERATOR_ROLE` = `0x97667070c54ef182b0f5858b034beac1b6f3089aa2d3188bb1e8929f4fa9b929`; `PAUSER_ROLE` = `0x65d7a28e3265b37a6474929f336521b332c1681b933f6cb9f3376673440d862a`; `MANAGER_ROLE` = `0x241ecf16d79d0f8dbfb92cbc07fe17840425976cf0667f022fe9877caa831b08`; `DEPLOYER_ROLE` = `0xfc425f2263d0df187444b70e47283d622c70181c5baebb1306a01edba1ce184c`.

### 1.2 PreCollateralizedMinter (the on-chain mint)

| topic0 | Event |
|--------|-------|
| `0xa07df9051bdbcafa9b686a1764ca00a2125ba12e89de80b5045e64cd364c8c41` | `MintExecuted(bytes32 indexed collateralRef, address indexed recipient, uint256 amount, uint256 nonce)` |

### 1.3 sUSDf (`StakedUSDf`) and sFF (`StakedFF`) — ERC-4626

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` | both |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` | both (also on `cooldownShares`/`cooldownAssets`, receiver = silo) |
| `0xbb28dd7cd6be6f61828ea9158a04c5182c716a946a6d2f31f4864edb87471aa6` | `RewardsReceived(uint256 amount)` | **sUSDf** — daily yield |
| `0x6c92b9512d53b42df0b05c7bdce22ab2261502217045a2ab747d4a67e2fff305` | `RewardsReceived(uint256 amount, uint256 totalSupply, uint256 timestamp)` | **sFF** |
| `0xd8654fcc8cf5b36d30b3f5e4688fc78118e6d68de60b9994e09902268b57c3e3` | `Unstaked(address indexed user, address indexed receiver, uint256 assets)` | sFF only (sUSDf `unstake` emits no event of its own) |
| `0xcfcd6e6f74be0389df7022cddfe9391e6f9ed2b105d4a6772fe10b4a80833f5c` | `RestrictedStatusSet(address indexed account, bool status)` | both — vault blacklist |
| `0x54362a1d0d75ed86b296ea97890ad3d6fcb0530b163d6fd8da67693b8fabae7f` | `LockedAmountRedistributed(address indexed from, bool sharesBurned, uint256 amount)` | sUSDf — **admin seizure** of a restricted holder |
| `0x2a53a05a26bcb02fdc30c037c7b04d4551e7dce313c6c7d3e77d98b8f68bf0dc` | `LockedAmountRedistributed(address indexed from, bool sharesBurned, uint256 amount, uint256 siloAmount)` | sFF |
| `0x180eacdf7dbaeecaa983d93173b4285db2f2c0de0044697e1f932bbbb73dcaa6` | `CooldownDurationUpdated(uint24 previousDuration, uint24 newDuration)` | both (+ StakingRewards) |
| `0xca15e5ed47adc0bc51eea03f0213c75641684d69b7e7a0037351e41b7f42199f` | `VestingPeriodUpdated(uint32 previousPeriod, uint32 newPeriod)` | both |
| `0xddf252ad…3ef` / `0x8c5be1e5…925` | `Transfer` / `Approval` (share token) | both |

### 1.4 Falcon Position NFT and sFF-Prime (`FalconPosition`, ERC-721)

| topic0 | Event | Note |
|--------|-------|------|
| `0x860a7f444abeeac636e14426419bf48578cd6ce60a51ed3d48fcaf6a9412aba4` | `PositionMinted(uint256 indexed tokenId, address indexed owner, uint256 principal, uint256 duration)` | lock opened |
| `0x3120c845c5d2c39308641201562a412527c1e7aff294f09c0c936f1c60a1b067` | `PositionClosed(uint256 indexed tokenId, address indexed owner, uint256 principal, uint256 duration)` | matured lock withdrawn |
| `0x49d512bf9cb224241c05691e73eb9fab078cf350c7dbcbcf66788f1fc0cc8b0b` | `FeesCollected(uint256 indexed tokenId, uint256 amount)` | boosted yield collected |
| `0x2bf7c36e0ae64012f8b71df84b7ce0dbae8c54f1b95d2301a6911b073c653864` | `MaturityProcessed(uint256 duration, uint256 timestamp, uint256 totalLiquidity, uint256 feeGrowthX128)` | |
| `0x8ad0c4905aa5603107e860e0c2b1a78e23eba312c30f8114a70d94d9e187f5af` | `RewardsDeposited(uint256 duration, uint256 amount)` | **Falcon Position (USDf)** impl |
| `0x4493e620e31d81e9ed14e103e5e83d91de350612d388eb64cf016543b2100979` | `RewardsDeposited(uint256 duration, uint256 amount, uint256 totalLiquidity, uint256 timestamp)` | **sFF-Prime** impl |
| `0x042addcdd52fa9f4a2ea6f461e37db659bbf93ed7c05362efbb83469baa813b6` | `DurationUpdated(uint256 duration, bool isSupported, bool mintEnabled)` | admin |
| `0x479b41c95ccf33c642fd444ee4db3b4fb4328ba42aff9de79cb942f646e8fda3` | `YieldCollectionChanged(bool oldEnabled, bool newEnabled)` | admin |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 indexed tokenId)` | ERC-721: **4 topics** (tokenId indexed) vs ERC-20's 3 |

### 1.5 StakingRewardsDistributor / StakingRewardsDistributorFF

| topic0 | Event |
|--------|-------|
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0x77023e19c7343ad491fd706c36335ca0e738340a91f29b1fd81e2673d44896c4` | `TokensRescued(address indexed token, address indexed to, uint256 amount)` |

`transferInRewards` emits nothing on the distributor. Watch `RewardsReceived` on the vault.

### 1.6 StakingRewards (Staking Vaults)

| topic0 | Event |
|--------|-------|
| `0x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d` | `Staked(address indexed user, uint256 amount)` |
| `0x8a05f911d8ab7fc50fec37ef4ba7f9bfcb1a3c191c81dcd824ad0946c4e20d65` | `Cooldown(address indexed user, uint256 amount)` |
| `0x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5` | `Withdrawn(address indexed user, uint256 amount)` |
| `0xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486` | `RewardPaid(address indexed user, uint256 reward)` (USDf) |
| `0xde88a922e0d3b88b24e9623efeb464919c6bf9f66857a65e2bfcf2ce87a9433d` | `RewardAdded(uint256 reward)` |
| `0x1a6b3ffc38e569eb77b736c56f6d826b44ad9f3df5f63ec4eac3dcb444668ea5` | `FundsPulled(address indexed caller, uint256 amount)` — **manager removes staked tokens** |
| `0x1bea8e4d5ccd747c424b73410162228ac62d71ac01b299b3e7fc55ddf6e694e9` | `FundsPut(address indexed caller, uint256 amount)` |
| `0xfff3b3844276f57024e0b42afec1a37f75db36511e43819a4f2a63ab7862b648` | `Recovered(address indexed tokenAddress, address indexed to, uint256 amount)` |
| `0xd3636070a5893c88088ab04180c3c0fe9be316dbea031e03a4aadbd688bf553a` | `CapUpdated(uint256 previousCap, uint256 newCap)` |
| `0xf0c0ed119c959dec5d731961641e2eaae4d8e1c77a315a7d7d298cfcfab8235a` | `LockupDurationUpdated(uint256 previousDuration, uint256 newDuration)` |
| `0xd20a04eb2807bde8cbdf16ef27a46d94a3162d81818f1781c0fe4ed9194ca391` | `RewardsDurationUpdated(uint256 previousDuration, uint256 newDuration)` |
| `0x1c794a043683a294127c95bc365bae91b63b651eb9884a2c9120afee2bb690b4` | `RewardsDistributionUpdated(address indexed _rewardsDistribution)` |

`Staked`/`Withdrawn`/`RewardPaid`/`RewardAdded` are the classic Synthetix topics. Filter by vault address.

### 1.7 CCIP token pools (LockRelease on Ethereum, BurnMint on BNB/Base; v1.5.1)

| topic0 | Event | Pool |
|--------|-------|------|
| `0x9f1ec8c880f76798e7b793325d625e9b60e4082a553c98f42b6cda368dd60008` | `Locked(address indexed sender, uint256 amount)` | LockRelease — outbound from Ethereum |
| `0x2d87480f50083e2b2759522a8fdda59802650a8055e609a7772cf70c07748f52` | `Released(address indexed sender, address indexed recipient, uint256 amount)` | LockRelease — inbound to Ethereum |
| `0x696de425f79f4a40bc6d2122ca50507f0efbeabbff86a84871b7196ab8ea8df7` | `Burned(address indexed sender, uint256 amount)` | BurnMint — outbound from BNB/Base |
| `0x9d228d69b5fdb8d273a2336f8fb8612d039631024ea9bf09c424a9503aa078f0` | `Minted(address indexed sender, address indexed recipient, uint256 amount)` | BurnMint — inbound to BNB/Base |
| `0xc17cea59c2955cb181b03393209566960365771dbba9dc3d510180e7cb312088` | `LiquidityAdded(address indexed provider, uint256 indexed amount)` | LockRelease |
| `0xc2c3f06e49b9f15e7b4af9055e183b0d73362e033ad82a07dec9bf9840171719` | `LiquidityRemoved(address indexed provider, uint256 indexed amount)` | LockRelease |
| `0x6fa7abcf1345d1d478e5ea0da6b5f26a90eadb0546ef15ed3833944fbfd1db62` | `LiquidityTransferred(address indexed from, uint256 amount)` | LockRelease |
| `0x8d340f17e19058004c20453540862a9c62778504476f6756755cb33bcd6c38c2` | `ChainAdded(uint64,bytes,(bool,uint128,uint128),(bool,uint128,uint128))` | both |
| `0x0350d63aa5f270e01729d00d627eeb8f3429772b1818c016c66a588a864f912b` | `ChainConfigured(uint64,(bool,uint128,uint128),(bool,uint128,uint128))` | both — rate-limit change |
| `0x5204aec90a3c794d8e90fded8b46ae9c7c552803e7e832e0c1d358396d859916` | `ChainRemoved(uint64 remoteChainSelector)` | both |
| `0x7d628c9a1796743d365ab521a8b2a4686e419b3269919dc9145ea2ce853b54ea` | `RemotePoolAdded(uint64 indexed remoteChainSelector, bytes remotePoolAddress)` | both |
| `0x52d00ee4d9bd51b40168f2afc5848837288ce258784ad914278791464b3f4d76` | `RemotePoolRemoved(uint64 indexed remoteChainSelector, bytes remotePoolAddress)` | both |
| `0x1871cdf8010e63f2eb8384381a68dfa7416dc571a5517e66e88b2d2d0c0a690a` | `TokensConsumed(uint256 tokens)` | rate limiter |
| `0x02dc5c233404867c793b749c6d644beb2277536d18a7e7974d3f238e4c6f1684` | `RouterUpdated(address oldRouter, address newRouter)` | both |

### 1.8 Chainlink feeds, proxies, FF claims

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f` | `AnswerUpdated(int256 indexed current, uint256 indexed roundId, uint256 updatedAt)` | the **underlying aggregator** (§3), not the EACAggregatorProxy |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | every Transparent proxy |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | Transparent proxy |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed, address indexed)` | ProxyAdmin, CCIP pools, claim contracts |
| `0xacdf21ae0911c6449c8bf4e02f7714b2bff5cc157c05ac1a766ad776a788de8a` | `Claimed(uint256 index, address indexed account, uint256 amount, uint256 claimAmount, uint256 stakeAmount, uint256 vestAmount, uint8 option)` | FF `Claim` |
| `0x4a94c2c356e29a6583071e731bdacf2ca56565ba5efebcff6936eb7923b51721` | `VestingClaimed(address indexed account, uint256 amount, uint256 timestamp)` | `VestingClaimV2` |
| `0xffe903c0abe6b2dbb2f3474ef43d7a3c1fca49e5a774453423ca8e1952aabffa` | `TokensWithdrawn(address indexed account, uint256 amount, uint256 timestamp)` | `VestingClaimV2` |
| `0x90004c04698bc3322499a575ed3752dd4abf33e0a7294c06a787a0fe01bea941` | `MerkleRootUpdated(bytes32 newRoot)` | `VestingClaimV2` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 USDf (Ethereum)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address,uint256)` | `MINTER_ROLE` only. Held by PreCollateralizedMinter. |
| `0x9dc29fac` | `burn(address,uint256)` | `BURNER_ROLE` only. Burns from any account (no allowance). |
| `0xd7b4206a` | `setRestriction(address,bool)` | `DEFAULT_ADMIN_ROLE`. Blacklist. Emits `AddressRestrictionSet`. |
| `0xc01bc982` | `isRestricted(address)` | `bool` |
| `0x2f2ff15d` / `0xd547741f` / `0x36568abe` | `grantRole(bytes32,address)` / `revokeRole(bytes32,address)` / `renounceRole(bytes32,address)` | AccessControl |
| `0x91d14854` | `hasRole(bytes32,address)` | view |
| `0xd505accf` | `permit(address,address,uint256,uint256,uint8,bytes32,bytes32)` | EIP-2612 |
| `0xa9059cbb` / `0x23b872dd` / `0x095ea7b3` | `transfer` / `transferFrom` / `approve` | ERC-20 |
| `0xc4d66de8` | `initialize(address)` | one-shot |

### 2.2 BurnMintERC20 (USDf BNB/Base, FF BNB)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address,uint256)` | `MINTER_ROLE` (the CCIP pool) |
| `0x9dc29fac` | `burn(address,uint256)` | `BURNER_ROLE` |
| `0x42966c68` | `burn(uint256)` | `BURNER_ROLE` (pool burns its own balance) |
| `0x79cc6790` | `burnFrom(address,uint256)` | `BURNER_ROLE` |
| `0xc630948d` | `grantMintAndBurnRoles(address)` | admin |
| `0xa8fa343c` | `setCCIPAdmin(address)` | admin. Emits `CCIPAdminTransferred`. |
| `0x8fd6a6ac` | `getCCIPAdmin()` | view |
| `0xd5abeb01` | `maxSupply()` | view (0 = uncapped; BNB FF = 10 B) |

### 2.3 PreCollateralizedMinter and FalconBundler

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5cec23e7` | `preCollateralizedMint((bytes32,address,uint256,uint256,uint256),bytes)` | Params = `(collateralRef, recipient, amount, nonce, expiry)`. Anyone may submit; signer must hold `MINTER_ROLE` on the minter. Emits `MintExecuted` + USDf `Transfer(0→recipient)`. |
| `0x5d00bb12` | `isNonceUsed(uint256)` | view |
| `0xb249b35d` | `USDF()` | view |
| `0xc0c721e8` | `mintToStakedUSDf((bytes32,address,uint256,uint256,uint256),bytes)` | Bundler, `OPERATOR_ROLE`. Mint → deposit to sUSDf for recipient. |
| `0x9f299cf9` | `mintToFalconPosition((bytes32,address,uint256,uint256,uint256),uint256,bytes)` | Bundler, `OPERATOR_ROLE`. Mint → sUSDf → Position NFT. |
| `0xdd832897` | `stakeToFalconPosition(uint256,uint256,address)` | Bundler, **public**. USDf → sUSDf → Position NFT. |

### 2.4 sUSDf / sFF (ERC-4626 + cooldown)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6e553f65` | `deposit(uint256,address)` | stake. Emits `Deposit`. |
| `0x94bf804d` | `mint(uint256,address)` | stake by shares |
| `0xb460af94` | `withdraw(uint256,address,address)` | only when cooldown is **off** (sUSDf today) |
| `0xba087652` | `redeem(uint256,address,address)` | only when cooldown is off |
| `0xa2af4900` | `cooldownShares(uint256,address)` | only when cooldown is **on** (sFF today). Moves assets to silo. |
| `0xd50655b0` | `cooldownAssets(uint256,address)` | same |
| `0xf2888dbb` | `unstake(address)` | claim from silo after cooldown |
| `0xc80ef110` | `transferInRewards(uint256)` | `REWARDER_ROLE`. Emits `RewardsReceived`. |
| `0xa883de5c` | `setRestrictedStatus(address,bool)` | admin blacklist |
| `0xee327147` | `redistributeLockedAmount(address,bool)` | admin: burn or move a restricted holder's shares to `TREASURY` |
| `0xce23eb3c` | `setCooldownDuration(uint24)` | admin |
| `0xa43957c4` | `setVestingPeriod(uint32)` | admin |
| `0x07a2d13a` | `convertToAssets(uint256)` | exchange rate (2026-10-30: 1 sUSDf = 1.14047 USDf; 1 sFF = 1.00900 FF) |
| `0x01e1d114` | `totalAssets()` | view |
| `0xe7c2a608` | `getUnvestedAmount()` | view |
| `0x35269315` | `cooldownDuration()` | view |
| `0x01320fe2` | `cooldowns(address)` | `(uint104 cooldownEnd, uint152 underlyingAmount)` |
| `0xeb3beb29` | `silo()` | view |
| `0x2d2c5565` | `TREASURY()` | view |

### 2.5 FalconPosition (Position NFT and sFF-Prime)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1b2ef1ca` | `mint(uint256,uint256)` | `(amount, duration)` → tokenId. Emits `PositionMinted`. |
| `0x2e1a7d4d` | `withdraw(uint256)` | tokenId; after maturity. Emits `PositionClosed`. |
| `0xce3f865f` | `collect(uint256)` | collect boosted yield. Emits `FeesCollected`. |
| `0xbdd071fb` | `depositRewards(uint256,uint256)` | `REWARDER_ROLE` |
| `0xf21b3b44` | `mature(uint256,uint256)` | process a maturity bucket |
| `0x809ad7f3` | `updateDurationSettings(uint256,bool,bool)` | admin |
| `0xcf0981ed` | `setYieldCollectionEnabled(bool)` | admin |
| `0xeb02c301` | `getPosition(uint256)` | `(uint256,uint40,uint40,uint40,uint256,uint256)` |
| `0xc14f7f09` | `sFalconAsset()` | locked asset (sFF-Prime → FF; reverts on the USDf Position impl) |
| `0xd0b17de1` | `initializeV2(uint256[],uint256[])` | sFF-Prime impl only |

### 2.6 Distributors

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc80ef110` | `transferInRewards(uint256)` | `OPERATOR_ROLE` → calls the vault |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | `PAUSER_ROLE` |
| `0xcea9d26f` | `rescueTokens(address,address,uint256)` | admin |
| `0xd3bfe76a` | `revokeApproval(address,address)` | admin |
| `0x398387c1` / `0x2fa15b58` / `0xf296f703` | `STAKING_VAULT()` / `USDF_TOKEN()` / `FF_TOKEN()` | views |

### 2.7 StakingRewards and StakingRewardsFactory

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa694fc3a` | `stake(uint256)` | Emits `Staked`. Cap enforced. |
| `0xda276040` | `cooldown(uint256)` | after lockup. Emits `Cooldown`. |
| `0x2def6620` | `unstake()` | after cooldown. Emits `Withdrawn`. |
| `0x2e1a7d4d` | `withdraw(uint256)` | only when cooldown off + lockup elapsed |
| `0x3d18b912` | `getReward()` | Emits `RewardPaid` (USDf) |
| `0xe9fad8ee` | `exit()` | withdraw + getReward |
| `0x3c6b16ab` | `notifyRewardAmount(uint256)` | `rewardsDistribution` only |
| `0xec8d8777` | `pullFunds(uint256)` | **`MANAGER_ROLE` takes staked tokens out** |
| `0x6124e1ac` | `putFunds(uint256)` | `MANAGER_ROLE` returns them |
| `0x1171bda9` | `recoverERC20(address,address,uint256)` | admin |
| `0x47786d37` / `0xe7a1107f` / `0xce23eb3c` / `0xcc1a378f` / `0x19762143` | `setCap` / `setLockupDuration` / `setCooldownDuration` / `setRewardsDuration` / `setRewardsDistribution` | admin |
| `0x72f702f3` / `0xf7c618c1` | `stakingToken()` / `rewardToken()` | views |
| `0xa3246ad3` | `getRoleMembers(bytes32)` | enumerable roles |
| `0x56ff9836` | `deploy(address,address,address,address,address,uint256,uint24,uint256,uint256)` | **Factory**, `DEPLOYER_ROLE`. Emits no event; vaults are plain `CREATE`. |

### 2.8 CCIP pools, Chainlink feeds, proxies

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9a4575b9` | `lockOrBurn((bytes,uint64,address,uint256,address))` | OnRamp only |
| `0x39077537` | `releaseOrMint((bytes,uint64,address,uint256,address,bytes,bytes,bytes))` | OffRamp only |
| `0xeb521a4c` / `0x0a861f2a` / `0x66320087` | `provideLiquidity(uint256)` / `withdrawLiquidity(uint256)` / `transferLiquidity(address,uint256)` | LockRelease rebalancer/owner |
| `0xe8a1da17` | `applyChainUpdates(uint64[],(uint64,bytes[],bytes,(bool,uint128,uint128),(bool,uint128,uint128))[])` | owner |
| `0xc4bffe2b` / `0xb7946580` / `0xa42a7b8b` | `getSupportedChains()` / `getRemoteToken(uint64)` / `getRemotePools(uint64)` | views |
| `0xfeaf968c` / `0x50d25bcd` / `0x245a7bfc` | `latestRoundData()` / `latestAnswer()` / `aggregator()` | Chainlink proxy views |
| `0x9623609d` | `upgradeAndCall(address,address,bytes)` | **ProxyAdmin** (OZ v5), owner-only |
| `0x8c302292` | `claim(uint256,address,uint256,bytes32[],uint8,uint256)` | FF `Claim` |
| `0xb71aa541` | `claimVesting(uint256,address,uint256,bytes32[])` | `VestingClaimV2` |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` on `https://ethereum-rpc.publicnode.com` on 2026-10-30. Impl = EIP-1967 implementation slot. Deploy blocks from the creation transactions.

| Role | Address | Impl / note |
|------|---------|-------------|
| **USDf** | `0xfa2b947eec368f42195f24f36d2af29f7c24cec2` | impl `0x3adf34c09dac24e4baefb1b1df4c2992edc2b789`; ProxyAdmin `0x3ef1127fdf81b553066dae0faea58785a2aa6e14`. Supply 1.728 B. Block 21 818 184. |
| **sUSDf** | `0xc8cf6d7991f15525488b2a83df53468d682ba4b0` | impl `0x0d132bee412e6619a4863aeedad97541bfda3f34`; ProxyAdmin `0x16a2605c026bfe4f4b7f4471933714d9b2149ace` |
| USDfSilo | `0xeb1a55f406c1dc08f017ce8f424b178a5b0667e7` | sUSDf cooldown escrow |
| **Falcon Position NFT** (live) | `0x8407e9864f42374cb9dacfdede0e6962d634edcb` | impl `0x76f9fd81c5d199011b503e33843e4cb592ddd18a`; ProxyAdmin `0xa9657206789c036007168e6c39588930c6180dd2` |
| Falcon Position NFT (v1, superseded) | `0x2a382c429668fcf4fd85371fc690fd27ddf5562e` | impl `0x84f376d2d797b0ae19410c625aa0e12fc24e92f7`; 7 NFTs left. Not on the docs list. |
| **StakingRewardsDistributor** (sUSDf) | `0x8af2efa47efb2095b80d82577c597186ea2fffea` | holds `REWARDER_ROLE` on sUSDf |
| **PreCollateralizedMinter** | `0x3a4f41dac6000a59b79669b9356b5eb71bf4cc59` | holds `MINTER_ROLE` on USDf |
| FalconBundler (live) | `0xb9e43b20962adffba088732ae194b7e91711924e` | → live Position NFT |
| FalconBundler (v1) | `0x2919a6255a697e9ba0550aa573a0c47e0c9c043d` | → v1 Position NFT |
| **FF** | `0xfa1c09fc8b491b6a4d3ff53a10cad29381b3f949` | immutable, 10 B supply |
| **sFF** | `0x1a0c3ffcbd101c6f2f6650ded9964c4a568c4d72` | impl `0x80216d0218d4cee3cbc65068ab29c0e973cd896c`; ProxyAdmin `0xa9a7e62b67a4f2dd2755af21dd766790714302bd`. Block 23 466 161. |
| FFSilo | `0x25faec314e00c9704d85c8a563355077bc17b1bd` | sFF cooldown escrow |
| StakingRewardsDistributorFF | `0x0c36526f412ea008994669b3406a856463abb41f` | holds `REWARDER_ROLE` on sFF |
| **sFF-Prime** | `0x41ff52dc7b12b18a65558962849187a2cc6ee6c0` | impl `0x4bf80e78916e14b2c2154b5d7a754869a0646fa6`; ProxyAdmin `0xc1d8927d80a14f55726a73ae94eea9a95e391b45`. Block 24 168 704. |
| StakingRewardsFactory | `0x759b632ddc6ea6238da73acc6a21fc22170138be` | same address on BNB |
| **FF Staking Vault** | `0x1e7ffb2cc2b0d9672b3e615dd5669c06f8673cae` | stake FF → earn USDf; factory nonce 1 |
| XAUt Staking Vault | `0x11d13fce0858050ffa1aa8784b96cd244e2bbf84` | stake XAUt (`0x68749665…2f38`) → earn USDf; factory nonce 2. Not on the docs list. |
| **CCIP LockReleaseTokenPool — USDf** | `0xecf61d6faa3b9fae7195af3bc9891450c1733f78` | registered pool in TokenAdminRegistry; owner = USDf Safe. Lanes: BNB, Base, XDC, Solana. |
| CCIP LockReleaseTokenPool — USDf (unused) | `0xadeee0871b2bdd25bd69f0da736b001eef626334` | no lanes, not registered |
| **CCIP LockReleaseTokenPool — FF** | `0x05ddab21b57d0dca8c3955c366526a229577558e` | registered; owner = FF Safe; lane: BNB |
| USDf/USD Chainlink feed (proxy) | `0xb177857a1799aa5f7feb5799fdf12cbe8fdf78b1` | `description()="USDF / USD"`, 8 dec; aggregator `0x05581918dad3f026169593863f7a52bbbe08ef5e` |
| sUSDf/USDf Chainlink feed (proxy) | `0xe471bc940aa9831a0aea21e6f40c1a1236eb4bb3` | `"sUSDf / USDf Exchange Rate"`, 18 dec; aggregator `0x80c1b1ee029f05889e3a693fd8c5f76f9b9fe194` |
| FF Claim / ClaimNoVestFull | `0x1178c6a8e2600f0e9bafbc5e5677fe10805f05e3` / `0xc78d8097862723a66baab6a84716745e2ffdb2b4` | FF TGE claim (Sep 2025) |
| VestingClaim / VestingClaimV2 | `0x9e330c463a5b576f63d4ac92c6d54711d180e108` / `0x5c3acd262ea9a91fb784394c26c93bc2ce31d606` | FF vesting |
| Perryverse Perry Egg / Perry NFT | `0xb0ae9dd22a2e1211f813b081098581dd0ff5b981` / `0x383b5123b55f5ef823080c0c9e9bb58ffefd2c5e` | Transparent proxies (Miles program); ProxyAdmin owner `0x4a570d00c2036c5a6d2cf4264a9dfd3034ea165e` |

**Governance addresses (Ethereum):**

| Holder | Address | Powers |
|--------|---------|--------|
| USDf Safe (4 signers) | `0x1e482b60bf19cb1cc859389e0ea3ded153f16bd7` | `DEFAULT_ADMIN_ROLE` on USDf, sUSDf, Position NFT, SRD, PreCollateralizedMinter, Bundler; `PAUSER_ROLE` on SRD; owner of the USDf/sUSDf/Position ProxyAdmins; owner of the USDf CCIP pools on all chains; `TREASURY()` of sUSDf |
| FF/sFF Safe | `0x808b96f3e6dc2213a2198bd832fd22f21809cffe` | `DEFAULT_ADMIN_ROLE` on sFF and sFF-Prime; owner of their ProxyAdmins; `TREASURY()` of sFF |
| FF CCIP Safe | `0xaa7cbfc360df28c8417f4dfaa7b61e032ca5baf5` | owner of FF pools (ETH, BNB); CCIP admin + admin of BNB FF |
| Staking-vault Safe | `0x3115840ab10899534cbdf52f761f21f15b018791` | `DEFAULT_ADMIN_ROLE` on every StakingRewards vault + factory (ETH and BNB) |
| Vault manager (EOA) | `0x7313e2be11d843482e7d10fe3b04d2abf72e8839` | `MANAGER_ROLE` (`pullFunds`/`putFunds`) on every vault |
| Vault rewards distributor (EOA) | `0x86784f8da3c7ca986c3004567a75601ea6973346` | `rewardsDistribution` on every vault |
| sUSDf rewards operator (EOA, observed caller) | `0x482d74fdf4e33773735c2f53a8b5f47af1f5c8aa` | sends the daily `transferInRewards` to StakingRewardsDistributor |
| sFF distributor operator (EOA) | `0xbb5e1337a2ac59f0f63120d38aa865cf12844153` | `OPERATOR_ROLE` + `PAUSER_ROLE` on StakingRewardsDistributorFF; deployer of the FF stack |

---

## 4. Addresses — BNB Smart Chain (chain ID 56)

Verified via `eth_getCode` on `https://bsc-rpc.publicnode.com`. Source from Sourcify.

| Role | Address | One-liner |
|------|---------|-----------|
| **USDf** (BurnMintERC20) | `0xb3b02e4a9fb2bd28cc2ff97b0ab3f6b3ec1ee9d2` | 114.7 M supply; admin + CCIP admin = USDf Safe `0x1e482b60…` |
| **USDf BurnMintTokenPool** | `0x4b66431f9e5f5cd026ae48e617902207b43048d4` | holds MINTER+BURNER on USDf; lane to Ethereum only |
| **FF** (BurnMintERC20) | `0xac23b90a79504865d52b49b327328411a23d4db2` | 373.8 M supply; `maxSupply` 10 B; admin + CCIP admin = `0xaa7cbfc3…` |
| **FF BurnMintTokenPool** | `0x470ed414d305d2c784501cc68e086e3b59d6e51e` | holds MINTER+BURNER on FF; lane to Ethereum only |
| ESPORTS Staking Vault | `0x58895856a8996e1db467f91850043e5b2a304356` | stake ESPORTS (`0xf39e4b21…8e48`) → earn USDf |
| VELVET Staking Vault | `0x2704b216a42b8ed40ae9f4ab4072151a8eb257a7` | stake VELVET (`0x8b194370…1488`) → earn USDf |
| ESPORTS Staking Vault (empty, factory nonce 1) | `0x1e7ffb2cc2b0d9672b3e615dd5669c06f8673cae` | **same address as the Ethereum FF vault**, but a different, empty ESPORTS vault |
| StakingRewardsFactory | `0x759b632ddc6ea6238da73acc6a21fc22170138be` | same address as Ethereum |

**Not on BNB:** sUSDf, sFF, Position NFTs, PreCollateralizedMinter, distributors, Chainlink USDf feeds from this doc.

## 5. Addresses — Base (chain ID 8453)

| Role | Address | One-liner |
|------|---------|-----------|
| **USDf** (BurnMintERC20) | `0x8210c0634ab8f273806e4b7866e9db353773c44b` | 0.95 M supply. Admin = USDf Safe `0x1e482b60…`. **CCIP admin = EOA `0x50fad3de9f0c113312065cb50c267fceb59a76cb`** (the pool deployer). Same address as XDC USDf. Not on the docs list. |
| **USDf BurnMintTokenPool** | `0x33570299e0d73f07c82d005de75de54cf4582fcc` | owner USDf Safe; lane to Ethereum only |

**Not on Base:** FF, sUSDf, sFF, vaults, minter. Press reports of "$2.1 B USDf on Base" do not match on-chain supply.

## 6. Other chains

Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137), Robinhood Chain (4663), Arc (5042): **no Falcon deployment.** Every address in this doc returns `eth_getCode = 0x` there. The USDf CCIP pool on Ethereum has lanes only to BNB, Base, XDC (non-target) and Solana (non-EVM, mint `9ksrtYx1vnRxr4X5YqmGxqRMRBhgsc6FfQwWjB1KZq2x`).

---

## 7. Cross-chain summary

| Chain (ID) | USDf | sUSDf | FF | sFF | Position NFTs | Staking Vaults | CCIP pool(s) |
|-----------|------|-------|----|-----|---------------|----------------|--------------|
| Ethereum (1) | `0xfa2b947e…` (home) | `0xc8cf6d79…` | `0xfa1c09fc…` | `0x1a0c3ffc…` | `0x8407e986…`, sFF-Prime `0x41ff52dc…` | FF, XAUt | LockRelease USDf `0xecf61d6f…`, FF `0x05ddab21…` |
| BNB (56) | `0xb3b02e4a…` | — | `0xac23b90a…` | — | — | ESPORTS, VELVET | BurnMint USDf `0x4b66431f…`, FF `0x470ed414…` |
| Base (8453) | `0x8210c063…` | — | — | — | — | — | BurnMint USDf `0x33570299…` |
| Avax / Arb / OP / Poly / Robin / Arc | — | — | — | — | — | — | — |

CCIP chain selectors used by the pools: Ethereum `5009297550715157269`, BNB `11344663589394136015`, Base `15971525489660198786`, XDC `17673274061779414707`, Solana `124615329519749607`.

## 8. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| USDf, sUSDf, Position NFT (both), sFF, sFF-Prime, Perry NFTs | OZ v5 TransparentUpgradeableProxy (793 B) | EIP-1967 impl + admin slots set; admin = a dedicated `ProxyAdmin` (879 B) | `ProxyAdmin.owner()` → USDf Safe (USDf, sUSDf, Positions) / FF Safe `0x808b96f3…` (sFF, sFF-Prime) |
| FF, USDfSilo, FFSilo, distributors, PreCollateralizedMinter, Bundlers, StakingRewards, Factory, CCIP pools, BurnMintERC20s, claim contracts | Immutable | impl slot = 0 | none; config only through roles/owner |
| Chainlink feeds | EACAggregatorProxy | `aggregator()` | Chainlink multisig `0x21f73d42eb58ba49ddb685dc29d3bf5c0f0373ca` (`owner()`) |

Watch `Upgraded(address)` on each proxy and `upgradeAndCall` (`0x9623609d`) on each ProxyAdmin. In OZ v5 the ProxyAdmin is created by the proxy constructor, so the proxy's admin slot never changes without an `AdminChanged` event.

---

## 9. Detection invariants & gotchas

1. **Mint/redeem is off-chain.** Do not look for a collateral `deposit` contract. Track supply through USDf `Transfer` from `0x0` (mint) and to `0x0` (burn). Every legitimate Ethereum mint today has a matching `MintExecuted` in the same tx from `0x3a4f41da…`. A USDf mint **without** `MintExecuted` means a new `MINTER_ROLE` holder — alert on it. Daily yield also goes through the minter: `MintExecuted` with `recipient` = StakingRewardsDistributor `0x8af2efa4…`, then a separate tx from operator EOA `0x482d74fd…` calls `transferInRewards` (sUSDf `RewardsReceived`). Example pair: mint tx `0x7f32a3f9549aba8c2df0d982f5218064dcd83143a0876b1cb6a2e4cd07649a2c` (block 26 298 372), reward tx `0x3df89879b523e09cb12e18f989296d650a584442eea302bb77044db92fb7a154` (block 26 298 378).
2. **`collateralRef` (bytes32, indexed)** in `MintExecuted` is the off-chain collateral reference. It is the only on-chain link between a mint and its collateral.
3. **Blacklists:** USDf `AddressRestrictionSet` blocks both send and receive (including mint/burn). sUSDf/sFF `RestrictedStatusSet` blocks vault entry/exit; `LockedAmountRedistributed` is an admin seizure (burn or move to `TREASURY`). BurnMintERC20 tokens on BNB/Base have **no** blacklist.
4. **USDf `burn(address,uint256)` needs no allowance.** Any `BURNER_ROLE` holder can burn from any wallet. No contract held `BURNER_ROLE` among the checked candidates on 2026-10-30. Watch `RoleGranted` with the BURNER role id.
5. **sUSDf cooldown is off** (`cooldownDuration()=0`). Users exit by plain `redeem`/`withdraw` → `Withdraw` event. **sFF cooldown is on** (3 days): exit = `cooldownShares` (`Withdraw` with receiver = FFSilo) then `unstake` (`Unstaked`). A cooldown flip changes which path is live; watch `CooldownDurationUpdated`.
6. **Same topic, different payload.** `RewardsReceived`, `LockedAmountRedistributed` and `RewardsDeposited` have two signatures each (sUSDf vs sFF; Position vs sFF-Prime). Use the topic that matches the emitter.
7. **`Deposit`/`Withdraw`/`Staked`/`Withdrawn`/`RewardPaid` are generic topics** (EIP-4626 and Synthetix). Always filter on `(chain, address, topic0)`.
8. **ERC-721 vs ERC-20 `Transfer`.** Position NFTs share topic0 `0xddf252ad…` with ERC-20. Tell them apart by topic count (4 vs 3).
9. **Staking Vault custody.** `FundsPulled` means the `MANAGER_ROLE` EOA `0x7313e2be…` took staked user tokens out for strategies. A large `FundsPulled` without later `FundsPut` is the main custody signal for the vaults.
10. **BNB address collision.** `0x1e7ffb2c…` is the FF vault on Ethereum, but on BNB the same factory nonce holds an **empty ESPORTS vault**. The live ESPORTS vault on BNB is `0x58895856…`. Never assume a vault's staking token from its address; read `stakingToken()`.
11. **Two USDf LockRelease pools on Ethereum.** Only `0xecf61d6f…` is registered in the CCIP TokenAdminRegistry (`0xb22764f98dd05c789929716d677382df22c05cb6`). `0xadeee087…` has no lanes. Bridged USDf supply on BNB + Base should equal the USDf balance of `0xecf61d6f…` (minus XDC/Solana shares).
12. **Base USDf CCIP admin is an EOA** (`0x50fad3de…`). It can re-point the token's pool in the registry. Watch `CCIPAdminTransferred` and the registry's pool events for Base USDf.
13. **Chainlink feeds.** The proxy addresses are stable. `AnswerUpdated` is emitted by the aggregator, so update the aggregator address when `aggregator()` changes. USDf/USD has 8 decimals; sUSDf/USDf has 18 decimals.
14. **Old v1 Position NFT and Bundler** (`0x2a382c42…`, `0x2919a625…`) are still live code with a few open NFTs. Include them for completeness of `PositionClosed` history.
15. **FF is immutable** with a fixed 10 B supply on Ethereum. BNB FF is minted only by its CCIP pool. Any BNB FF `Transfer(0x0→X)` that does not come from `0x470ed414…` is abnormal.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_TRANSFER                    = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_USDF_ADDRESS_RESTRICTION    = '\xf28feb0f201748ef16ccc442dd23ba17ae3e2957006c4e351a718bcd5f65d516'
TOPIC_ROLE_GRANTED                = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED                = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
TOPIC_CCIP_ADMIN_TRANSFERRED      = '\x9524c9e4b0b61eb018dd58a1cd856e3e74009528328ab4a613b434fa631d7242'
TOPIC_MINT_EXECUTED               = '\xa07df9051bdbcafa9b686a1764ca00a2125ba12e89de80b5045e64cd364c8c41'
TOPIC_4626_DEPOSIT                = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_4626_WITHDRAW               = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_SUSDF_REWARDS_RECEIVED      = '\xbb28dd7cd6be6f61828ea9158a04c5182c716a946a6d2f31f4864edb87471aa6'
TOPIC_SFF_REWARDS_RECEIVED        = '\x6c92b9512d53b42df0b05c7bdce22ab2261502217045a2ab747d4a67e2fff305'
TOPIC_SFF_UNSTAKED                = '\xd8654fcc8cf5b36d30b3f5e4688fc78118e6d68de60b9994e09902268b57c3e3'
TOPIC_RESTRICTED_STATUS_SET       = '\xcfcd6e6f74be0389df7022cddfe9391e6f9ed2b105d4a6772fe10b4a80833f5c'
TOPIC_SUSDF_LOCKED_REDISTRIBUTED  = '\x54362a1d0d75ed86b296ea97890ad3d6fcb0530b163d6fd8da67693b8fabae7f'
TOPIC_SFF_LOCKED_REDISTRIBUTED    = '\x2a53a05a26bcb02fdc30c037c7b04d4551e7dce313c6c7d3e77d98b8f68bf0dc'
TOPIC_COOLDOWN_DURATION_UPDATED   = '\x180eacdf7dbaeecaa983d93173b4285db2f2c0de0044697e1f932bbbb73dcaa6'
TOPIC_VESTING_PERIOD_UPDATED      = '\xca15e5ed47adc0bc51eea03f0213c75641684d69b7e7a0037351e41b7f42199f'
TOPIC_POSITION_MINTED             = '\x860a7f444abeeac636e14426419bf48578cd6ce60a51ed3d48fcaf6a9412aba4'
TOPIC_POSITION_CLOSED             = '\x3120c845c5d2c39308641201562a412527c1e7aff294f09c0c936f1c60a1b067'
TOPIC_POSITION_FEES_COLLECTED     = '\x49d512bf9cb224241c05691e73eb9fab078cf350c7dbcbcf66788f1fc0cc8b0b'
TOPIC_POSITION_REWARDS_DEPOSITED  = '\x8ad0c4905aa5603107e860e0c2b1a78e23eba312c30f8114a70d94d9e187f5af'
TOPIC_SFFPRIME_REWARDS_DEPOSITED  = '\x4493e620e31d81e9ed14e103e5e83d91de350612d388eb64cf016543b2100979'
TOPIC_PAUSED                      = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                    = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_TOKENS_RESCUED              = '\x77023e19c7343ad491fd706c36335ca0e738340a91f29b1fd81e2673d44896c4'
TOPIC_VAULT_STAKED                = '\x9e71bc8eea02a63969f509818f2dafb9254532904319f9dbda79b67bd34a5f3d'
TOPIC_VAULT_COOLDOWN              = '\x8a05f911d8ab7fc50fec37ef4ba7f9bfcb1a3c191c81dcd824ad0946c4e20d65'
TOPIC_VAULT_WITHDRAWN             = '\x7084f5476618d8e60b11ef0d7d3f06914655adb8793e28ff7f018d4c76d505d5'
TOPIC_VAULT_REWARD_PAID           = '\xe2403640ba68fed3a2f88b7557551d1993f84b99bb10ff833f0cf8db0c5e0486'
TOPIC_VAULT_FUNDS_PULLED          = '\x1a6b3ffc38e569eb77b736c56f6d826b44ad9f3df5f63ec4eac3dcb444668ea5'
TOPIC_VAULT_FUNDS_PUT             = '\x1bea8e4d5ccd747c424b73410162228ac62d71ac01b299b3e7fc55ddf6e694e9'
TOPIC_CCIP_LOCKED                 = '\x9f1ec8c880f76798e7b793325d625e9b60e4082a553c98f42b6cda368dd60008'
TOPIC_CCIP_RELEASED               = '\x2d87480f50083e2b2759522a8fdda59802650a8055e609a7772cf70c07748f52'
TOPIC_CCIP_BURNED                 = '\x696de425f79f4a40bc6d2122ca50507f0efbeabbff86a84871b7196ab8ea8df7'
TOPIC_CCIP_MINTED                 = '\x9d228d69b5fdb8d273a2336f8fb8612d039631024ea9bf09c424a9503aa078f0'
TOPIC_CCIP_LIQUIDITY_REMOVED      = '\xc2c3f06e49b9f15e7b4af9055e183b0d73362e033ad82a07dec9bf9840171719'
TOPIC_CCIP_CHAIN_CONFIGURED       = '\x0350d63aa5f270e01729d00d627eeb8f3429772b1818c016c66a588a864f912b'
TOPIC_CHAINLINK_ANSWER_UPDATED    = '\x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED               = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
-- ===== Role ids =====
ROLE_MINTER                       = '\x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6'
ROLE_BURNER                       = '\x3c11d16cbaffd01df69ce1c404f6340ee057498f5f00246190ea54220576a848'
ROLE_REWARDER                     = '\xbeec13769b5f410b0584f69811bfd923818456d5edcf426b0e31cf90eed7a3f6'
ROLE_MANAGER                      = '\x241ecf16d79d0f8dbfb92cbc07fe17840425976cf0667f022fe9877caa831b08'
-- ===== Selectors (chain-agnostic) =====
SEL_MINT                          = '\x40c10f19'
SEL_BURN_FROM_ADDR                = '\x9dc29fac'
SEL_SET_RESTRICTION               = '\xd7b4206a'
SEL_PRE_COLLATERALIZED_MINT       = '\x5cec23e7'
SEL_BUNDLER_MINT_TO_SUSDF         = '\xc0c721e8'
SEL_BUNDLER_MINT_TO_POSITION      = '\x9f299cf9'
SEL_BUNDLER_STAKE_TO_POSITION     = '\xdd832897'
SEL_4626_DEPOSIT                  = '\x6e553f65'
SEL_4626_REDEEM                   = '\xba087652'
SEL_4626_WITHDRAW                 = '\xb460af94'
SEL_COOLDOWN_SHARES               = '\xa2af4900'
SEL_UNSTAKE_ADDR                  = '\xf2888dbb'
SEL_TRANSFER_IN_REWARDS           = '\xc80ef110'
SEL_SET_RESTRICTED_STATUS         = '\xa883de5c'
SEL_REDISTRIBUTE_LOCKED           = '\xee327147'
SEL_POSITION_MINT                 = '\x1b2ef1ca'
SEL_POSITION_WITHDRAW             = '\x2e1a7d4d'
SEL_VAULT_STAKE                   = '\xa694fc3a'
SEL_VAULT_PULL_FUNDS              = '\xec8d8777'
SEL_PROXYADMIN_UPGRADE_AND_CALL   = '\x9623609d'
SEL_GRANT_ROLE                    = '\x2f2ff15d'
-- ===== Addresses — Ethereum (1) =====
ETH_USDF                          = '\xfa2b947eec368f42195f24f36d2af29f7c24cec2'
ETH_SUSDF                         = '\xc8cf6d7991f15525488b2a83df53468d682ba4b0'
ETH_USDF_SILO                     = '\xeb1a55f406c1dc08f017ce8f424b178a5b0667e7'
ETH_FALCON_POSITION               = '\x8407e9864f42374cb9dacfdede0e6962d634edcb'
ETH_FALCON_POSITION_V1            = '\x2a382c429668fcf4fd85371fc690fd27ddf5562e'
ETH_SUSDF_REWARDS_DISTRIBUTOR     = '\x8af2efa47efb2095b80d82577c597186ea2fffea'
ETH_PRE_COLLATERALIZED_MINTER     = '\x3a4f41dac6000a59b79669b9356b5eb71bf4cc59'
ETH_FALCON_BUNDLER                = '\xb9e43b20962adffba088732ae194b7e91711924e'
ETH_FALCON_BUNDLER_V1             = '\x2919a6255a697e9ba0550aa573a0c47e0c9c043d'
ETH_FF                            = '\xfa1c09fc8b491b6a4d3ff53a10cad29381b3f949'
ETH_SFF                           = '\x1a0c3ffcbd101c6f2f6650ded9964c4a568c4d72'
ETH_FF_SILO                       = '\x25faec314e00c9704d85c8a563355077bc17b1bd'
ETH_SFF_REWARDS_DISTRIBUTOR       = '\x0c36526f412ea008994669b3406a856463abb41f'
ETH_SFF_PRIME                     = '\x41ff52dc7b12b18a65558962849187a2cc6ee6c0'
ETH_STAKING_REWARDS_FACTORY       = '\x759b632ddc6ea6238da73acc6a21fc22170138be'
ETH_FF_STAKING_VAULT              = '\x1e7ffb2cc2b0d9672b3e615dd5669c06f8673cae'
ETH_XAUT_STAKING_VAULT            = '\x11d13fce0858050ffa1aa8784b96cd244e2bbf84'
ETH_CCIP_POOL_USDF                = '\xecf61d6faa3b9fae7195af3bc9891450c1733f78'
ETH_CCIP_POOL_USDF_UNUSED         = '\xadeee0871b2bdd25bd69f0da736b001eef626334'
ETH_CCIP_POOL_FF                  = '\x05ddab21b57d0dca8c3955c366526a229577558e'
ETH_FEED_USDF_USD                 = '\xb177857a1799aa5f7feb5799fdf12cbe8fdf78b1'
ETH_FEED_USDF_USD_AGGREGATOR      = '\x05581918dad3f026169593863f7a52bbbe08ef5e'
ETH_FEED_SUSDF_USDF               = '\xe471bc940aa9831a0aea21e6f40c1a1236eb4bb3'
ETH_FEED_SUSDF_USDF_AGGREGATOR    = '\x80c1b1ee029f05889e3a693fd8c5f76f9b9fe194'
ETH_PROXYADMIN_USDF               = '\x3ef1127fdf81b553066dae0faea58785a2aa6e14'
ETH_PROXYADMIN_SUSDF              = '\x16a2605c026bfe4f4b7f4471933714d9b2149ace'
ETH_PROXYADMIN_POSITION           = '\xa9657206789c036007168e6c39588930c6180dd2'
ETH_PROXYADMIN_SFF                = '\xa9a7e62b67a4f2dd2755af21dd766790714302bd'
ETH_PROXYADMIN_SFF_PRIME          = '\xc1d8927d80a14f55726a73ae94eea9a95e391b45'
ETH_SAFE_USDF_ADMIN               = '\x1e482b60bf19cb1cc859389e0ea3ded153f16bd7'
ETH_SAFE_FF_ADMIN                 = '\x808b96f3e6dc2213a2198bd832fd22f21809cffe'
ETH_SAFE_FF_CCIP                  = '\xaa7cbfc360df28c8417f4dfaa7b61e032ca5baf5'
ETH_SAFE_VAULT_ADMIN              = '\x3115840ab10899534cbdf52f761f21f15b018791'
ETH_VAULT_MANAGER_EOA             = '\x7313e2be11d843482e7d10fe3b04d2abf72e8839'
-- ===== Addresses — BNB (56) =====
BNB_USDF                          = '\xb3b02e4a9fb2bd28cc2ff97b0ab3f6b3ec1ee9d2'
BNB_CCIP_POOL_USDF                = '\x4b66431f9e5f5cd026ae48e617902207b43048d4'
BNB_FF                            = '\xac23b90a79504865d52b49b327328411a23d4db2'
BNB_CCIP_POOL_FF                  = '\x470ed414d305d2c784501cc68e086e3b59d6e51e'
BNB_ESPORTS_STAKING_VAULT         = '\x58895856a8996e1db467f91850043e5b2a304356'
BNB_VELVET_STAKING_VAULT          = '\x2704b216a42b8ed40ae9f4ab4072151a8eb257a7'
BNB_ESPORTS_VAULT_EMPTY           = '\x1e7ffb2cc2b0d9672b3e615dd5669c06f8673cae'
-- ===== Addresses — Base (8453) =====
BASE_USDF                         = '\x8210c0634ab8f273806e4b7866e9db353773c44b'
BASE_CCIP_POOL_USDF               = '\x33570299e0d73f07c82d005de75de54cf4582fcc'
```

---

## 11. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Live logs:** `MintExecuted`, sUSDf `RewardsReceived`/`Deposit`/`Withdraw`, sFF `Unstaked`, Position `PositionClosed`/`FeesCollected` and CCIP `Locked` were each seen in Ethereum logs from the last 60 000 blocks before 2026-10-30.
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the verified ABIs of every listed implementation (Etherscan/Blockscout verified source for Ethereum, Sourcify for BNB `BurnMintERC20`). Role ids recomputed as `keccak256("<NAME>_ROLE")`.
- **Addresses:** the docs list (USDf, sUSDf, Position NFT, distributor, two feeds, FF, sFF, sFF-Prime, FF vault, Perry NFTs, BNB USDf/FF/vaults) was extended by the deployer histories of `0x804016c3…` (USDf stack) and `0xbb5e1337…` (FF stack), the factory's `CREATE` nonces, and the CCIP `TokenAdminRegistry.getPool` plus each pool's `getSupportedChains` / `getRemoteToken` / `getRemotePools`. Every address was existence-checked with `eth_getCode`.
- **Proxies and roles:** EIP-1967 impl and admin slots read live; `ProxyAdmin.owner()` read live; role holders confirmed by `hasRole` against the candidate set and by `getRoleMembers` on the enumerable vaults. The full historical `RoleGranted` log set was not enumerated, so an unlisted role holder is possible.
- **Chain coverage:** all addresses checked on all nine chains. Only Ethereum, BNB and Base return code for Falcon contracts. Robinhood Chain and Arc return `0x` for every address.
- **Live values:** USDf supply 1 728 094 732; sUSDf rate 1.14047; sFF cooldown 259 200 s; sUSDf cooldown 0; vault lockup 15 552 000 s (180 d), cooldown 259 200 s.

Not verified: a Chainlink Proof-of-Reserve feed for USDf (announced by Chainlink; address not confirmed); XDC and Solana deployments (out of scope); any further BNB Staking Vault not on the docs list or at factory nonces 1–12.

Authoritative sources:
- [Falcon docs — Smart Contracts](https://docs.falcon.finance/resources/smart-contracts) · [Perryverse contracts](https://docs.falcon.finance/perryverse-nft/smart-contracts) · [Staking Vaults](https://docs.falcon.finance/earn/staking-vaults) · [sUSDf yield distribution](https://docs.falcon.finance/earn/susdf-yield-distribution) · [Audits (Zellic, Pashov)](https://docs.falcon.finance/resources/audits)
- [Chainlink CCIP directory — USDf](https://docs.chain.link/ccip/directory/mainnet/token/USDf)
- Explorers: [Etherscan USDf](https://etherscan.io/token/0xFa2B947eEc368f42195f24F36d2aF29f7c24CeC2) · [Blockscout Ethereum](https://eth.blockscout.com) · [BscScan](https://bscscan.com/token/0xb3b02e4a9fb2bd28cc2ff97b0ab3f6b3ec1ee9d2) · [Basescan](https://basescan.org/token/0x8210c0634ab8f273806e4b7866e9db353773c44b) · [Sourcify](https://sourcify.dev)
