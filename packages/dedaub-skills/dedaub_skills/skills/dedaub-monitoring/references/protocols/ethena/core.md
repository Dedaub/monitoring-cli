# Ethena — Topics, Selectors, Addresses (Ethereum hub; LayerZero OFTs on Base, BNB, Avalanche, Arbitrum, Optimism, Robinhood Chain)

**Status:** verified against live RPC on all nine target chains, the official key-addresses page (`docs.ethena.fi`), and Sourcify-verified source on 2026-10-30.
**Scope:** the Ethena synthetic-dollar stack: USDe, sUSDe (staking with cooldown), EthenaMinting (signed-order mint/redeem), StakingRewardsDistributor, ENA, sENA, rsENA, USDtb (token, legacy minter, PSM), the USDe PSM on Avalanche, and the LayerZero V2 OFT mesh for USDe, sUSDe and ENA. Topics and selectors are chain-agnostic. Addresses are network-specific.

Ethereum is the only hub. USDe, sUSDe, ENA, sENA, EthenaMinting and USDtb are native on Ethereum only. Every other target chain holds **LayerZero V2 OFT tokens** at three shared literals: USDe `0x5d3a1Ff2…ef34`, sUSDe `0x211Cc4DD…E5d2`, ENA `0x58538e6A…0133`. On Ethereum, the same three literals are the **OFT Adapters** (lockboxes). They lock the native token on send and unlock it on receive. On the other chains, the literal is the token itself: it burns on send and mints on receive (`token()` = itself, `approvalRequired()` = `false`).

USDe, sUSDe, EthenaMinting, StakingRewardsDistributor and every OFT/OFT Adapter are **immutable** (EIP-1967 implementation slot = 0). Only sENA, rsENA and USDtb are proxies. The owner of USDe, sUSDe, EthenaMinting V2, ENA and every OFT is an OpenZeppelin `TimelockController` with a 1-day delay (`getMinDelay()` = 86400), one per chain.

Present: Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Robinhood Chain. **Not deployed: Polygon PoS and Arc.** `eth_getCode` = `0x` for all three OFT literals on both chains, and the Ethereum adapters have `peers(30109)` = 0 and `peers(30417)` = 0.

---

## 0. Contract families

| Contract | Role | Chains | Proxy? |
|----------|------|--------|--------|
| **USDe** | Synthetic dollar ERC-20 (18 dec). A single `minter` (EthenaMinting V2) mints. Holders can burn. | ETH | immutable |
| **EthenaMinting V2** | Whitelisted benefactors sign EIP-712 orders. A MINTER/REDEEMER role submits them. Collateral goes to custodians by the route. Emits `Mint`/`Redeem` with `order_id`. Current `USDe.minter()`. | ETH | immutable |
| EthenaMinting V1 | Legacy minting contract. It is no longer `USDe.minter()`. Old event shapes (no `order_id`). | ETH | immutable |
| **sUSDe** (`StakedUSDeV2`) | ERC-4626 vault over USDe. Rewards vest linearly. Cooldown on: `cooldownAssets/Shares` move USDe to the **USDeSilo**, then `unstake` after `cooldownDuration` (86400 s now). Has FULL/SOFT restriction blacklist. | ETH | immutable |
| USDeSilo | Holds USDe during the sUSDe cooldown. Only sUSDe calls `withdraw`. | ETH | immutable |
| **StakingRewardsDistributor** | Operator calls `transferInRewards` to push USDe rewards into sUSDe. | ETH | immutable |
| **ENA** | Governance token (18 dec). | ETH | immutable |
| **sENA** (`StakedENA`) | ERC-4626 over ENA with a 7-day cooldown (`cooldownDuration` = 604800) and rewards vesting. | ETH | Transparent |
| **rsENA** (`MellowVaultCompat`) | Mellow/Symbiotic restaking vault. `asset()` = ENA. | ETH | Transparent |
| **USDtb** (`AnchorageTokenUSDtb`) | Treasury-backed stablecoin issued with Anchorage. Holders with `MINTER_BURNER_ROLE` call `mint`/`burn` directly. | ETH | Transparent |
| USDtbMinting | Legacy signed-order minter for USDtb. It no longer holds `MINTER_BURNER_ROLE`. | ETH | immutable |
| **USDtb PSM** | `PSM` swap contract with `asset()` = USDtb. | ETH | immutable |
| **USDe PSM** | Same `PSM` family, newer build, with `asset()` = USDe. Funded by the PSM Custodian EOA. | Avax | immutable |
| **USDe / sUSDe / ENA OFT Adapter** | LayerZero V2 lockbox for the native token. Has rate limits per destination EID. | ETH | immutable |
| **USDe / ENA OFT** (`USDeOFT`) | Mint/burn OFT token on the L2. | Base, BNB, Avax, Arb, OP, Robin | immutable |
| **sUSDe OFT** (`StakedUSDeOFT`) | Mint/burn OFT token. Adds a blacklister (`updateBlackList`, `redistributeBlackListedFunds`). | Base, BNB, Avax, Arb, OP, Robin | immutable |
| TimelockController | Owner of the core contracts and the OFTs (one per chain, 15,149 B, 1-day delay). | all 7 present | immutable |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All topic0 values were recomputed locally from the verified ABI. Live `eth_getLogs` matches are marked *(live)*.

### 1.1 EthenaMinting V2 (also USDtbMinting — identical events except `USDtbSet`)

| topic0 | Event |
|--------|-------|
| `0x29ee92e51cda311463f5c9ef98c54824a4bebe45e689c37da35edc774585d437` | `Mint(string indexed order_id, address indexed benefactor, address indexed beneficiary, address minter, address collateral_asset, uint256 collateral_amount, uint256 usde_amount)` *(live: 24 in 50k ETH blocks)* |
| `0x0ea36c5b7b274f8fe58654fe884bb9307dec1899e0312f40ae10d9b3d100cc0c` | `Redeem(string indexed order_id, address indexed benefactor, address indexed beneficiary, address redeemer, address collateral_asset, uint256 collateral_amount, uint256 usde_amount)` *(live: 17 in 50k ETH blocks)* |
| `0x90c5d8794dcf7c60ab2d20912d5228389b28f74d32af01e40894a784a90b9ac2` | `CustodyTransfer(address indexed wallet, address indexed asset, uint256 amount)` — collateral moved to a custodian |
| `0xed6a1f03e365a374bf7e9fe68b09cf74960528af699108cb461241efc5ded909` | `DelegatedSignerAdded(address indexed signer, address indexed delegator)` |
| `0x769c75d94dacde64c18415b5a72f6d26e7f62b356387f8da812c4b0aa66a0f25` | `DelegatedSignerInitiated(address indexed signer, address indexed delegator)` |
| `0x97b59d736dc70ae61c6b68295c19a1311cc4a48cbb9eb25c4dabf18c7f650a8a` | `DelegatedSignerRemoved(address indexed signer, address indexed delegator)` |
| `0xfbd30b5bdd51f5de989170dc23d65aac2de0a6099f5d9d200bc5779d883abcd4` | `CustodianAddressAdded(address indexed custodian)` |
| `0x75567811df62a6b68bd5ee394d5808ad7282e19541858be466bc789cad9d4dfb` | `CustodianAddressRemoved(address indexed custodian)` |
| `0x2fbec2225160ba8b27d83182d706920f1170182d15934f2122fd744049140ae2` | `BenefactorAdded(address indexed benefactor)` |
| `0xf0ebdfe9729215cc867dca3785f752df456766a9ce4b178ad1bca9919ca4a650` | `BenefactorRemoved(address indexed benefactor)` |
| `0xbb39c36a7502b7256e1a687254146a9a2ea7b146c77cb9e40eb0e2b8793781e1` | `BeneficiaryAdded(address indexed benefactor, address indexed beneficiary)` |
| `0x1a6590bd0cabbfcc7c86bef99e1034054e179905cfcc294598fcd426c0922442` | `BeneficiaryRemoved(address indexed benefactor, address indexed beneficiary)` |
| `0x0e3c58ebfb2e7465fbb1c32e6b4f40c3c4f5ca77e8218a386aff8617831260d7` | `AssetAdded(address indexed asset)` |
| `0x37803e2125c48ee96c38ddf04e826daf335b0e1603579040fd275aba6d06b6fc` | `AssetRemoved(address indexed asset)` |
| `0x82414669d8803616fdb8fe48ecd5b28a500e077ce5cfc4b57066463847aa7824` | `TokenTypeSet(address indexed token, uint256 tokenType)` |
| `0x13e2041fca7db19db36c1bbb93af5fa29559068bc0e162f0bf34c53945eeae10` | `MaxMintPerBlockChanged(uint256 oldMaxMintPerBlock, uint256 newMaxMintPerBlock, address indexed asset)` |
| `0xd9ee404b97bf8fc636668dbeac99021346d69983ff8571279d36ed5de8e1ae85` | `MaxRedeemPerBlockChanged(uint256 oldMaxRedeemPerBlock, uint256 newMaxRedeemPerBlock, address indexed asset)` |
| `0x72fb0d31878f6e7247733418a2aeabf201fddda56677167f041e9bb10ffd5c9e` | `USDeSet(address indexed USDe)` |
| `0x88a5966d370b9919b20f3e2c13ff65706f196a4e32cc2c12bf57088f88525874` | `Received(address, uint256)` — ETH received |
| `0xefdcbba819467e00b0262c12892dda980bac68580b72178e57a162368b808766` | `AdminTransferRequested(address indexed oldAdmin, address indexed newAdmin)` (also sUSDe, sENA, USDtb, PSM) |
| `0xf8ccb027dfcd135e000e9d45e6cc2d662578a8825d4c45b5e32e0adf67e79ec6` | `AdminTransferred(address indexed oldAdmin, address indexed newAdmin)` (also sUSDe, sENA, USDtb, PSM) |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |

USDtbMinting only: `0xd4895cbd33d675923f62ac80e5ecf41ab1f609aae6dd326eb3d2cc2743fd3b70` `USDtbSet(address indexed USDtb)`, `0x7b199bc414fa21a5f39d29338e7c4665dada25b6e55322a386a3070c9f798955` `DisableMintRedeem(address indexed sender)`, `0x78c4ec308d1eaf4b158d257ffd929348ece25e1495a99c12ca4a67aae92db319` `GlobalMaxMintPerBlock(address indexed sender, uint128)`, `0x0f08f24f84f8190442aea27ae7ea6a46a9bd89d440cd9d0f7468f171ccf4e7b0` `GlobalMaxRedeemPerBlock(address indexed sender, uint128)`.

### 1.2 EthenaMinting V1 (legacy — different shapes)

| topic0 | Event |
|--------|-------|
| `0xf114ca9eb82947af39f957fa726280fd3d5d81c3d7635a4aeb5c302962856eba` | `Mint(address indexed minter, address indexed benefactor, address indexed beneficiary, address collateral_asset, uint256 collateral_amount, uint256 usde_amount)` |
| `0x18fd144d7dbcbaa6f00fd47a84adc7dc3cc64a326ffa2dc7691a25e3837dba03` | `Redeem(address indexed redeemer, address indexed benefactor, address indexed beneficiary, address collateral_asset, uint256 collateral_amount, uint256 usde_amount)` |
| `0xb4a832eb73ba0066dc45acd0d1f4454cdee155b17bdb1ccbabb428cc39750ad1` | `MaxMintPerBlockChanged(uint256 oldMaxMintPerBlock, uint256 newMaxMintPerBlock)` |
| `0x6fd3eacad9328fdc902c323518cfef3a2f6a9da89c40a7b82428adc2370114c3` | `MaxRedeemPerBlockChanged(uint256 oldMaxRedeemPerBlock, uint256 newMaxRedeemPerBlock)` |

V1 shares the `CustodyTransfer`, `DelegatedSigner*`, `CustodianAddress*`, `Asset*` and `USDeSet` topics of §1.1.

### 1.3 USDe and ENA (Ethereum native tokens)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | all tokens. Mint = from `0x0`, burn = to `0x0`. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | all tokens |
| `0x1cf2de25c5bf439ac0287061c3a0fa69b3b02867d0ccfd2ded34e42577050b73` | `MinterUpdated(address indexed newMinter, address indexed oldMinter)` | USDe — **critical: the minter swap** |
| `0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885` | `Mint(address indexed to, uint256 amount)` | ENA (owner mint) |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` | USDe, ENA, OFTs, SRD |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | USDe, ENA, OFTs, SRD |

### 1.4 sUSDe (`StakedUSDeV2`) and sENA (`StakedENA`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` | stake *(live: sUSDe, sENA)* |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` | With cooldown on, `receiver` = the silo (sUSDe) or the contract (sENA). *(live)* |
| `0xbb28dd7cd6be6f61828ea9158a04c5182c716a946a6d2f31f4864edb87471aa6` | `RewardsReceived(uint256 amount)` | yield top-up *(live: sUSDe)* |
| `0x180eacdf7dbaeecaa983d93173b4285db2f2c0de0044697e1f932bbbb73dcaa6` | `CooldownDurationUpdated(uint24 previousDuration, uint24 newDuration)` | 0 = cooldown off (plain ERC-4626 withdraw) |
| `0xb8ef21f2b52f8ca740012254a6b10f17d2fd6e589f97ebf401fde0e8b9218937` | `LockedAmountRedistributed(address indexed from, address indexed to, uint256 amount)` | sUSDe — blacklisted balance moved/burned |
| `0xa4b3d92c67ba96e840c4888c41c81bb378420dfa35fbdcec3c0581372fb06068` | `CooldownStarted(address indexed cooler, uint256 assets, uint256 shares)` | sENA only *(live)* |
| `0x390b1276974b9463e5d66ab10df69b6f3d7b930eb066a0e66df327edd2cc811c` | `Unstake(address indexed unstaker, address indexed receiver, uint256 amount)` | sENA only *(live)*. sUSDe `unstake` emits only a USDe `Transfer` from the silo. |
| `0x876c16d00405860345e61598200d0bca4ba4a4aadc6de7a752860eed93f6d8c4` | `StakedENARedistributed(address indexed from, address indexed to, uint256 amount)` | sENA |
| `0x1d5e587d799342f659bb468470d4b37b49fc0509536bf48b24518a193af53872` | `VestingDurationUpdated(uint24 previousDuration, uint24 newDuration)` | sENA |
| `0x77023e19c7343ad491fd706c36335ca0e738340a91f29b1fd81e2673d44896c4` | `TokensRescued(address indexed token, address indexed to, uint256 amount)` | sENA, StakingRewardsDistributor |

### 1.5 StakingRewardsDistributor

| topic0 | Event |
|--------|-------|
| `0xfbe5b6cbafb274f445d7fed869dc77a838d8243a22c460de156560e8857cad03` | `OperatorUpdated(address indexed newOperator, address indexed previousOperator)` |
| `0x125ff1248e44c8fcb7ecacec5cbe30f1a41a8b86ed5844a881d0d111de565d5e` | `MintingContractUpdated(address indexed newMintingContract, address indexed previousMintingContract)` |

### 1.6 LayerZero OFT and OFT Adapter (all Ethena OFTs)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a` | `OFTSent(bytes32 indexed guid, uint32 dstEid, address indexed fromAddress, uint256 amountSentLD, uint256 amountReceivedLD)` | source leg *(live: ETH adapter, Robinhood OFT)* |
| `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c` | `OFTReceived(bytes32 indexed guid, uint32 srcEid, address indexed toAddress, uint256 amountReceivedLD)` | destination leg *(live: ETH adapter)* |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` | re-peering — high severity |
| `0xe888347665897e637801f36c5129f510657276178c89022bc5fa0246dbc19de1` | `RateLimitsChanged((uint32,uint256,uint256)[] rateLimitConfigs)` | `(dstEid, limit, window)` |
| `0x3881bcae1b79d28312da310a8d211e93a9d6ea5a30e04f43bca54b0768e5b3e7` | `RateLimiterSet(address indexed rateLimiter)` | |
| `0xbe4864a8e820971c0247f5992e2da559595f7bf076a21cb5928d443d2a13b674` | `EnforcedOptionSet((uint32,uint16,bytes)[] _enforcedOptions)` | |
| `0xf0be4f1e87349231d80c36b33f9e8639658eeaf474014dee15a3e6a4d4414197` | `MsgInspectorSet(address inspector)` | |
| `0xd48d879cef83a1c0bdda516f27b13ddb1b3f8bbac1c9e1511bb2a659c2427760` | `PreCrimeSet(address preCrimeAddress)` | |
| `0x0baadf7b35b83c7d3a00874b5406dca58c60d0ff7d8c825ad02ec55484beb455` | `BlackListUpdated(address indexed user, bool isBlackListed)` | sUSDe OFT only |
| `0x1d55e46d23d0d6e41dd1a27f7b583ec87c2d853eb8f571f518c8eea4b06684c2` | `RedistributeFunds(address indexed user, uint256 amount)` | sUSDe OFT only |
| `0x85ec649c3f86591e3b286677a06d313facd750294cc2d3de1978c92bced5868d` | `BlackListerSet(address indexed blackLister)` | sUSDe OFT only |

`guid` is the cross-chain join key (`OFTSent.guid` on the source = `OFTReceived.guid` on the destination). The LayerZero endpoint also emits `PacketSent` `0x1ab700d4…567f` in the same transaction; see [../layerzero/v2.md](../layerzero/v2.md).

### 1.7 PSM (USDtb PSM on Ethereum; USDe PSM on Avalanche)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x907f78e92aac9234fbd4c1ff8c47706974b6c47d390122ad766b87cb9851f2bc` | `SwapExecuted(address indexed orderExecutor, address indexed benefactor, address indexed beneficiary, (bool,uint120,uint128,uint256,address,address,address,uint128,uint128) order, uint128 amountOut, uint128 quotedFeeAmount, uint128 appliedFeeAmount)` | **Avalanche USDe PSM** *(live: 87 in 200k blocks)* |
| `0x15b92345f3ead624d82ae7a06769cdcf0e6514cc18ab02e39feb37ff8edb69c8` | `SwapExecuted(address indexed orderExecutor, address indexed benefactor, address indexed beneficiary, (bool,uint120,uint128,uint256,address,address,address,uint128,uint128) order, uint128 amountOut, uint128 feeAmount)` | **Ethereum USDtb PSM** (older build) |
| `0xcfcf26267df24bc1f0016b08af4a4fc7352e0dfd4b602139f44ccd12556625e6` | `OraclePriceValidated(address indexed collateral, uint256 price)` | one per swap *(live: Avax)* |
| `0x8a486357baaca80d0f89c23dadb76fa5257e728259fe3fa52f82337097eed78c` | `CollateralAdded(address indexed collateral, (address,address,address,uint128,uint128,uint128,uint128,uint256,bool,uint8,uint16,uint16,uint128,uint128) config)` | |
| `0x22109695bbcd04ef738944120f755bf4af0d36c8e1d5251a6e4b27c9dd2c69ea` | `CollateralConfigUpdated(address indexed collateral, (…same tuple…) config)` | *(live: Avax)* |
| `0x192895f9a14975ce177e9612fd4f4459e31169d79cb650596bcce0622bd70a92` | `CollateralDisabled(address indexed collateral)` | |
| `0xd89d2ee68ab04dca0193f48a4aff55e20fa5ec0429a8a8c1c51b8dad6178a593` | `CollateralRemoved(address indexed collateral)` | |
| `0xde74e8620646dab58026910daf41220a351a98edc9bee3d8d63771590561b5d6` | `PegPriceUpdated(uint128 oldPrice, uint128 newPrice)` | |
| `0x0a4f9ef21a3f2d279073474702eab63d142b2a13bad81a6a9e36d450a559a516` | `SwapDisabled()` | kill switch |
| `0x41c787961cb389554b90a8dbfb700790a3f278f50ba1d330c0b555d884789b5a` | `SwapEnabled()` | |
| `0xb08543f71a5722ce609191f41be33ae95042919e7e4b1b337417e7ca90a93517` | `AssetSendCustodianUpdated(address indexed oldCustodian, address indexed newCustodian)` | |
| `0xb38c81923e206187e2e991137f33da149e63af3cc92e2eabf018e41c7652c496` | `AssetReceiveCustodianUpdated(address indexed oldCustodian, address indexed newCustodian)` | |
| `0xa2f44af5de9375a1fb1b56eb6b54d4cb162a4ac5fbf380115096ccad5d351abf` | `RescueFunds(address indexed recipient, address indexed token, uint128 amount)` | |
| `0xd041322712e2362f86614d7afbe332deb2f82ad7a6ef08ed24a304d8b31a36c5` | `EpochLimitsUpdated(uint128,uint128,uint128,uint128)` | |
| `0x98a2e208799de2b345483665e698afc58929f8cc6e8d8d94a74286c286ca2bbe` | `PeriodLimitsUpdated(uint128,uint128,uint128,uint128)` | |

The PSM also emits `BenefactorAdded/Removed`, `BeneficiaryRemoved`, `DelegatedSignerAdded/Removed` (same topic0 as §1.1), plus `BenefactorEnabled` `0x1b2f1e20…3144`, `BenefactorDisabled` `0xcba0904f…ae76`, `BeneficiaryApproved` `0x067bef57…78f8`, `DelegatedSignerConfirmed` `0xe95f2c15…107a`, and per-benefactor limit/fee events.

### 1.8 USDtb (`AnchorageTokenUSDtb`)

| topic0 | Event |
|--------|-------|
| `0x5444f9841c04ce78987f28701fa07fc4c112840c1c8439e8f52bda50c3788a87` | `AccountsBlocked(address[] accounts)` |
| `0x4a637dd1cd99ae43d353009d0ffbc16b05cc69808b819ebf852c68ea47b34dd4` | `AccountsUnblocked(address[] accounts)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |

USDtb mint/burn has no dedicated event. Use the zero-address `Transfer`.

### 1.9 Governance and proxies

| topic0 | Event |
|--------|-------|
| `0x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca` | `CallScheduled(bytes32 indexed id, uint256 indexed index, address target, uint256 value, bytes data, bytes32 predecessor, uint256 delay)` — TimelockController. Gives a 1-day warning. |
| `0xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58` | `CallExecuted(bytes32 indexed id, uint256 indexed index, address target, uint256 value, bytes data)` |
| `0xbaa1eb22f2a492ba1a5fea61b8df4d27c6c8b5f3971e63bb58fa14ff72eedb70` | `Cancelled(bytes32 indexed id)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — sENA, rsENA, USDtb |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |

rsENA (Mellow `MellowVaultCompat`) emits ERC-4626 `Deposit`/`Withdraw` plus `ReferralDeposit` `0x0f33e518e0001973b4f02d7cef360e8c9290e9ebd0b48695c935af9bac850213`, `SymbioticPushed` `0xb53c38f4658baac1058d6b81869ed82ea19a0b0123b440e23e9b54cd98d4720d`, `RewardsPushed` `0x12d8e9280ac85b1633cd74c52f9458f73459aecd6eb0f2d99e2ed27c3fa27e99`, `DepositPauseSet` `0x917e249a9d1439adce72cf39ffef9f3ae18f5b7b37a942393522093db79826c4`, `WithdrawalPauseSet` `0x100e52ba225b1d864d8b4e3725311b44dc3d490024db41251211c87c20da20a7`, `LimitSet` `0x085b30415f63cd5f875aa6df7b116b64821bdea341dabcb10c94f1cc997138d9`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Order tuple (V2 and USDtbMinting): `(string order_id, uint8 order_type, uint120 expiry, uint128 nonce, address benefactor, address beneficiary, address collateral_asset, uint128 collateral_amount, uint128 usde_amount)`. Route: `(address[] addresses, uint128[] ratios)`. Signature: `(uint8 signature_type, bytes signature_bytes)`.

### 2.1 EthenaMinting V2 (USDtbMinting shares every selector except `setUSDtbToken` `0xd199001f`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x96eea750` | `mint((string,uint8,uint120,uint128,address,address,address,uint128,uint128),(address[],uint128[]),(uint8,bytes))` | MINTER_ROLE. Emits `Mint`. |
| `0x00d87483` | `mintWETH((string,uint8,uint120,uint128,address,address,address,uint128,uint128),(address[],uint128[]),(uint8,bytes))` | MINTER_ROLE, WETH collateral. |
| `0x75c890dc` | `redeem((string,uint8,uint120,uint128,address,address,address,uint128,uint128),(uint8,bytes))` | REDEEMER_ROLE. Emits `Redeem`. |
| `0x2da09621` | `transferToCustody(address,address,uint128)` | COLLATERAL_MANAGER. Emits `CustodyTransfer`. |
| `0x53863613` | `setDelegatedSigner(address)` | benefactor starts delegation |
| `0x157a4028` | `confirmDelegatedSigner(address)` | signer confirms |
| `0x40e49216` | `removeDelegatedSigner(address)` | |
| `0x4be7a64b` / `0x4ba87af9` | `addCustodianAddress(address)` / `removeCustodianAddress(address)` | admin |
| `0x16255c43` / `0x8db940e0` | `addWhitelistedBenefactor(address)` / `removeWhitelistedBenefactor(address)` | admin |
| `0xb58f203d` | `setApprovedBeneficiary(address,bool)` | benefactor |
| `0x7cfbc42f` / `0x1c46bc6f` | `addSupportedAsset(address,(uint8,bool,uint128,uint128))` / `removeSupportedAsset(address)` | admin |
| `0xc5ff38bd` | `disableMintRedeem()` | GATEKEEPER kill switch |
| `0x6c2cd30f` / `0x936e2248` | `setGlobalMaxMintPerBlock(uint128)` / `setGlobalMaxRedeemPerBlock(uint128)` | |
| `0x12a4a10e` / `0xe0770202` | `setMaxMintPerBlock(uint128,address)` / `setMaxRedeemPerBlock(uint128,address)` | per asset |
| `0x54f1e126` / `0x532c3f82` / `0x7274c25c` | `removeMinterRole(address)` / `removeRedeemerRole(address)` / `removeCollateralManagerRole(address)` | GATEKEEPER |
| `0x2f2ff15d` / `0xd547741f` | `grantRole(bytes32,address)` / `revokeRole(bytes32,address)` | |
| `0x75829def` / `0x0e18b681` | `transferAdmin(address)` / `acceptAdmin()` | two-step admin |
| `0x0fd761e0` | `usde()` | view |
| `0xa7c1abe0` | `globalConfig()` | view `(uint128 globalMaxMintPerBlock, uint128 globalMaxRedeemPerBlock)` |
| `0x1cf58ff2` / `0xe3a17ff9` | `isCustodianAddress(address)` / `isWhitelistedBenefactor(address)` | views |
| `0xcf9cc766` | `delegatedSigner(address,address)` | view, status enum |

V1 legacy selectors: `mint` `0xd48c03e5`, `mintWETH` `0xf5c42eb3`, `redeem` `0x95165e8b`, `transferToCustody(address,address,uint256)` `0xe0f3fc9f`, `addSupportedAsset(address)` `0xfac09e87`, `setMaxMintPerBlock(uint256)` `0x9cd29136`, `setMaxRedeemPerBlock(uint256)` `0xd8369d75` (order tuple `(uint8,uint256,uint256,address,address,address,uint256,uint256)`).

### 2.2 USDe / ENA

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address,uint256)` | USDe: only `minter`. ENA: owner. |
| `0xfca3b5aa` | `setMinter(address)` | USDe owner. Emits `MinterUpdated`. |
| `0x07546172` | `minter()` | view. Now EthenaMinting V2. |
| `0x42966c68` / `0x79cc6790` | `burn(uint256)` / `burnFrom(address,uint256)` | |
| `0xf2fde38b` / `0x79ba5097` | `transferOwnership(address)` / `acceptOwnership()` | Ownable2Step |
| `0xa9059cbb` / `0x23b872dd` / `0x095ea7b3` / `0xd505accf` | `transfer` / `transferFrom` / `approve` / `permit` | ERC-20 / ERC-2612 |

### 2.3 sUSDe (sENA shares the starred lines)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6e553f65` | `deposit(uint256,address)` * | stake |
| `0x94bf804d` | `mint(uint256,address)` * | |
| `0xcdac52ed` | `cooldownAssets(uint256)` * | starts cooldown. Emits `Withdraw` to the silo. |
| `0x9343d9e1` | `cooldownShares(uint256)` * | |
| `0xf2888dbb` | `unstake(address)` * | after cooldown. Silo pays USDe. |
| `0xb460af94` / `0xba087652` | `withdraw(uint256,address,address)` / `redeem(uint256,address,address)` * | revert while cooldown > 0 |
| `0xc80ef110` | `transferInRewards(uint256)` * | REWARDER. Emits `RewardsReceived`. |
| `0xce23eb3c` | `setCooldownDuration(uint24)` * | admin. Emits `CooldownDurationUpdated`. |
| `0xf298f42c` / `0xc336a084` | `addToBlacklist(address,bool)` / `removeFromBlacklist(address,bool)` | sUSDe (bool = full restriction). sENA: `addToBlacklist(address)` `0x44337ea1` / `removeFromBlacklist(address)` `0x537df3b6`. |
| `0xa0776b82` | `redistributeLockedAmount(address,address)` * | moves a blacklisted balance |
| `0xb37fd190` | `rescueTokens(address,uint256,address)` * | |
| `0x01320fe2` | `cooldowns(address)` * | view `(uint104 cooldownEnd, uint152 underlyingAmount)` |
| `0x35269315` / `0xeb3beb29` / `0x01e1d114` | `cooldownDuration()` / `silo()` / `totalAssets()` | views |
| `0x8593d033` | `updateVestingPeriod(uint24)` | sENA only |
| `0xf3fef3a3` | `withdraw(address,uint256)` | USDeSilo, sUSDe-only caller |

### 2.4 OFT / OFT Adapter

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc7c7f5b3` | `send((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address)` | bridge entry, payable. Emits `OFTSent`. |
| `0x13137d65` | `lzReceive((uint32,bytes32,uint64),bytes32,bytes,address,bytes)` | Endpoint only. Emits `OFTReceived`. |
| `0x3b6f743b` / `0x0d35b415` | `quoteSend(...)` / `quoteOFT(...)` | views |
| `0x3400288b` | `setPeer(uint32,bytes32)` | owner |
| `0x46f943e9` | `setRateLimits((uint32,uint256,uint256)[])` | owner |
| `0xf018d7c0` | `setRateLimiter(address)` | owner |
| `0xb98bd070` / `0x6fc1b31e` / `0xd4243885` / `0xca5eb5e1` | `setEnforcedOptions` / `setMsgInspector` / `setPreCrime` / `setDelegate` | owner |
| `0xfc2eb889` | `updateBlackList(address,bool)` | sUSDe OFT, blacklister |
| `0xe680c422` | `redistributeBlackListedFunds(address,uint256)` | sUSDe OFT |
| `0x78b0b814` | `setBlackLister(address)` | sUSDe OFT, owner |
| `0xbb0b6a53` / `0xfc0c546a` / `0x5e280f11` / `0x9f68b964` | `peers(uint32)` / `token()` / `endpoint()` / `approvalRequired()` | views |
| `0xab99095d` / `0x53d4fe33` | `rateLimits(uint32)` / `rateLimiter()` | views |

### 2.5 PSM, USDtb, governance

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x61912b0c` | `swap((bool,uint120,uint128,uint256,address,address,address,uint128,uint128))` | PSM swap (both builds). Emits `SwapExecuted`. |
| `0x8a1f0709` | `getQuote(address,address,uint128,bool)` | PSM quote |
| `0xfd5b9026` / `0x29691448` | `disableSwap()` / `enableSwap()` | PSM |
| `0xcef9bcf7` | `setPegPrice(uint128)` | PSM |
| `0x2a913659` | `rescueFunds(address,address,uint128)` | PSM |
| `0x40c10f19` / `0x9dc29fac` | `mint(address,uint256)` / `burn(address,uint256)` | USDtb, `MINTER_BURNER_ROLE` |
| `0x6abf7081` / `0xfaed47fd` | `blockAccounts(address[])` / `unblockAccounts(address[])` | USDtb |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | USDtb |
| `0x01d5062a` / `0x134008d3` | `schedule(address,uint256,bytes,bytes32,bytes32,uint256)` / `execute(address,uint256,bytes,bytes32,bytes32)` | TimelockController |

---

## 3. Addresses — Ethereum mainnet (chain ID 1, LZ EID 30101)

All verified via `eth_getCode` on `https://ethereum-rpc.publicnode.com` on 2026-10-30.

| Role | Address | One-liner |
|------|---------|-----------|
| **USDe** | `0x4c9EDD5852cd905f086C759E8383e09bff1E68B3` | 7,567 B. `minter()` = EthenaMinting V2. `owner()` = Timelock. |
| **EthenaMinting V2** | `0xe3490297a08d6fC8Da46Edb7B6142E4F461b62D3` | 24,027 B. Current minter. |
| EthenaMinting V1 | `0x2CC440b721d2CaFd6D64908D6d8C4aCC57F8Afc3` | 16,688 B. Legacy. `owner()` = Dev Safe. |
| **sUSDe** (`StakedUSDeV2`) | `0x9D39A5DE30e57443BfF2A8307A4256c8797A3497` | 17,299 B. `cooldownDuration()` = 86400. ~1.18 B USDe `totalAssets`. |
| USDeSilo | `0x7FC7c91D556B400AFa565013E3F32055a0713425` | 534 B. `sUSDe.silo()`. |
| **StakingRewardsDistributor** | `0xf2fa332bd83149c66b09b45670bce64746c6b439` | 6,157 B. `operator()` = `0xe3880b792f6f0f8795cbaacd92e7ca78f5d3646e`. |
| sUSDe Payout Fund | `0x71e4f98e8f20c88112489de3dded4489802a3a87` | Safe (171 B). Rewards source. |
| **ENA** | `0x57e114B691Db790C35207b2e685D4A43181e6061` | 7,713 B. |
| **sENA** | `0x8bE3460A480c80728a8C4D7a5D5303c85ba7B3b9` | Transparent proxy. `cooldownDuration()` = 604800. |
| rsENA | `0xc65433845ecd16688eda196497fa9130d6c47bd8` | Transparent proxy (Mellow). `asset()` = ENA. |
| **USDtb** | `0xC139190F447e929f090Edeb554D95AbB8b18aC1C` | Transparent proxy. |
| USDtb PSM | `0x73E35C5c35A274E34AdE6EB13cC7f62aEE323728` | 24,530 B. `asset()` = USDtb. |
| USDtbMinting (legacy) | `0xa3DDBf92077b850E29C4805Df0a2459Ae048416a` | 21,949 B. No `MINTER_BURNER_ROLE` on USDtb now. |
| **USDe OFT Adapter** | `0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34` | 12,470 B. `token()` = USDe. Lockbox. |
| **sUSDe OFT Adapter** | `0x211Cc4DD073734dA055fbF44a2b4667d5E5fE5d2` | 12,865 B. `token()` = sUSDe. |
| **ENA OFT Adapter** | `0x58538e6A46E07434d7E7375Bc268D3cb839C0133` | 12,470 B. `token()` = ENA. |
| TimelockController | `0xe8dc0fab349ea169283c48ccfd09d797e6db7c94` | Owner of USDe, sUSDe, V2, ENA, adapters, sENA. |
| Dev Safe | `0x3b0aaf6e6fcd4a7ceef8c92c32dfea9e64dc1862` | Owner of V1, StakingRewardsDistributor, sENA ProxyAdmin. |
| Reserve Fund | `0x2b5ab59163a6e93b4486f6055d33ca4a115dd4d5` | Docs-listed multisig. |
| USDe PSM Custodian | `0xD7fCaDe52aFb60FbF0E1E5F72A683F43820f56A0` | EOA (no code on any chain). Same address on every PSM chain. |
| LayerZero EndpointV2 | `0x1a44076050125825900e736c501f859c50fe728c` | Not an Ethena contract. |

## 4. Addresses — L2 OFT chains

The same three literals are the OFT tokens on every present L2. `token()` = self. `approvalRequired()` = `false`. `sharedDecimals()` = 6. `oftVersion()` = `(0x02e49c2c, 1)`. The Ethereum adapter's `peers(eid)` = the same literal for every eid below.

| Chain | ID | LZ EID | USDe OFT | sUSDe OFT | ENA OFT | OFT `owner()` (Timelock) | Endpoint |
|-------|----|--------|----------|-----------|---------|------------------------|----------|
| Base | 8453 | 30184 | `0x5d3a…ef34` (13,886 B) | `0x211C…E5d2` (15,007 B) | `0x5853…0133` (13,886 B) | `0xd896f26f76ed089a1711284a00af497b19d65171` | `0x1a44…728c` |
| BNB | 56 | 30102 | ✓ (13,886 B) | ✓ (15,007 B) | ✓ (13,886 B) | `0x89bad41d3307072cfd3118b5fd08101e23b2e129` | `0x1a44…728c` |
| Avalanche | 43114 | 30106 | ✓ (13,639 B) | ✓ (14,756 B) | ✓ (13,639 B) | `0x33038a97ed7e407914e23b67234728a965645cd4` | `0x1a44…728c` |
| Arbitrum | 42161 | 30110 | ✓ (13,886 B) | ✓ (15,007 B) | ✓ (13,886 B) | `0x89bad41d3307072cfd3118b5fd08101e23b2e129` | `0x1a44…728c` |
| Optimism | 10 | 30111 | ✓ (13,886 B) | ✓ (15,007 B) | ✓ (13,886 B) | `0xbb4db1dd2851a4c06afbc2c115de874d103090b4` | `0x1a44…728c` |
| Robinhood Chain | 4663 | 30416 | ✓ (11,267 B) | ✓ (12,227 B) | ✓ (11,267 B) | `0x5b29acbb51a1290ebda7f6a7a209aa08caa35901` | `0x6f475642a6e85809b1c36fa62763669b1b48dd5b` |

**Avalanche only — USDe PSM:** `0xa774f30bf4228a7de3ca4592b6032dc530d0e9e9` (24,565 B, immutable). `asset()` = USDe OFT. Swaps take USDt (`0x9702230a8ea53601f5cd2dc00fdbc13d4df4a8c7`) in and pay USDe from the PSM Custodian EOA (~8.9 M USDe held on 2026-10-30).

Docs-listed multisigs (not owners of the OFTs): Arbitrum and BNB `0xc9647361742Eb964965B461C44Bdf5c4Bc3c406d`, Optimism `0xc66bbBf821f2cfB3a85683acF0326EAC92C160Bd`, Base `0xbC89D10EB486b6591583F218acB9545087dBF293`.

## 5. Cross-chain summary

| Chain | USDe | sUSDe | ENA | Minting / staking | PSM |
|-------|------|-------|-----|-------------------|-----|
| Ethereum (1) | native `0x4c9E…` + adapter `0x5d3a…` | native `0x9D39…` + adapter `0x211C…` | native `0x57e1…` + adapter `0x5853…` | V1, V2, sUSDe, sENA, rsENA, SRD | USDtb PSM |
| Base (8453) | OFT | OFT | OFT | — | — |
| BNB (56) | OFT | OFT | OFT | — | — |
| Avalanche (43114) | OFT | OFT | OFT | — | **USDe PSM** |
| Arbitrum (42161) | OFT | OFT | OFT | — | — |
| Optimism (10) | OFT | OFT | OFT | — | — |
| Polygon PoS (137) | — | — | — | — | — |
| Robinhood Chain (4663) | OFT | OFT | OFT | — | — |
| Arc (5042) | — | — | — | — | — |

USDtb, sENA, rsENA and EthenaMinting are Ethereum-only (`0x` on the other eight chains). Supply snapshot (2026-10-30): USDe OFT `totalSupply()` ≈ 357.8 M on Robinhood Chain and ≈ 353.6 M on Base.

## 6. Proxies

| Contract | Pattern | Evidence | Upgrade auth |
|----------|---------|----------|--------------|
| sENA | EIP-1967 Transparent | impl `0x7fd57b46ae1a7b14f6940508381877ee03e1018b` (`StakedENA`); admin `0xf849d7792ff9b30a57656ee10a2776bcb49f4fe4` | ProxyAdmin owned by the Dev Safe |
| USDtb | EIP-1967 Transparent | impl `0x9d6d77a21702b9afcf924983fbfb84aaaae79589` (`AnchorageTokenUSDtb`); admin `0x3c405f68d5c6ece868e5646cac926679839acd68` | ProxyAdmin owner `0xd93826bb299765c87d13aeba2a7e5d9b27a03956` |
| rsENA | EIP-1967 Transparent | impl `0x09bba67c316e59840699124a8dc0bbda6a2a9d59` (`MellowVaultCompat`); admin `0xa59b36aca119a30c527eddaa386eb130bcf1939f` | admin owner `0x27a907d1f809e8c03d806dc31c8e0c545a3187fc` |
| USDe, sUSDe, EthenaMinting V1/V2, SRD, ENA, USDtbMinting, both PSMs, all OFTs/adapters | immutable | EIP-1967 impl and admin slots = 0 on every chain | Config via Timelock (1-day delay) or role holders. A new contract plus `setMinter` / `setPeer` replaces logic. |

Watch `Upgraded` `0xbc7cd75a…2d3b` on the three proxies. Watch `CallScheduled` on each Timelock.

## 7. Detection invariants & gotchas

1. **One literal, two roles.** `0x5d3a1Ff2…ef34` is the USDe **adapter** on Ethereum (holds locked USDe, has no `totalSupply`) and the USDe **token** on L2s. The Ethereum USDe token is `0x4c9EDD58…68B3`. Key on `(chain_id, address)`.
2. **Mint key.** V2 `Mint`/`Redeem` index `order_id` as a `string`. topic1 is `keccak256(order_id)`, not the string. Read the string from calldata.
3. **USDe supply changes on Ethereum** come only from `minter` (V2) mints and holder burns. A USDe `Transfer` from `0x0` whose tx `to` is not V2 means a minter change. Alert on `MinterUpdated`.
4. **sUSDe cooldown has no own event.** `cooldownAssets/Shares` emit ERC-4626 `Withdraw` with `receiver` = USDeSilo `0x7FC7…3425`. `unstake` emits only a USDe `Transfer` from the silo. sENA has explicit `CooldownStarted` and `Unstake`.
5. **sUSDe `withdraw`/`redeem` revert while `cooldownDuration` > 0.** `CooldownDurationUpdated` to 0 turns sUSDe into an instant-exit vault.
6. **Rewards.** The StakingRewardsDistributor calls `sUSDe.transferInRewards`. It emits `RewardsReceived` on sUSDe. Rewards vest linearly (`getUnvestedAmount`, `vestingAmount`).
7. **Bridge legs.** Source = `OFTSent` on the adapter/OFT; destination = `OFTReceived`. Join on `guid`. On L2s, the OFT also emits a zero-address `Transfer` (burn/mint). On Ethereum, a USDe `Transfer` to/from the adapter. Count one family only.
8. **Rate limits** are per destination EID (`rateLimits(uint32)`). A `RateLimitsChanged` that raises limits precedes large flows.
9. **sUSDe OFT has its own blacklist** (`BlackListUpdated`, `RedistributeFunds`). USDe and ENA OFTs have none.
10. **Avalanche decoy.** `0x4c9EDD58…68B3` (the Ethereum USDe literal) has code on Avalanche, but it is an unwired OFT with `symbol()` = ENA, `totalSupply()` = 0, no Ethereum peer, and owner EOA `0x8de54b1cefedeab1766b947c7d9a9963436e8fae`. It is not an Ethena contract.
11. **Robinhood Chain is genuine.** The OFTs are smaller builds (11,267 B / 12,227 B) and use EndpointV2 `0x6f47…dd5b`. `symbol()`, `endpoint()`, `peers(30101)` and supply all confirm them. They are not the fund-recovery forwarder decoy.
12. **Two PSM `SwapExecuted` topics.** Ethereum USDtb PSM uses `0x15b92345…`. Avalanche USDe PSM uses `0x907f78e9…` (adds `appliedFeeAmount`). The PSM custodian EOA, not the PSM, holds the USDe inventory. On Avalanche, the custodian also bridges USDe out with `send`.
13. **USDtb mints bypass USDtbMinting.** Live mints come from `mint(address,uint256)` called by EOA `0x364366a7164fb518eafaa42af0c86eddab78e6f3`. Detect them by zero-address `Transfer` on USDtb.
14. **Polygon PoS and Arc have no Ethena deployment.** Third-party bridged USDe on other chains is not in scope.

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_MINT_V2                 = '\x29ee92e51cda311463f5c9ef98c54824a4bebe45e689c37da35edc774585d437'
TOPIC_REDEEM_V2               = '\x0ea36c5b7b274f8fe58654fe884bb9307dec1899e0312f40ae10d9b3d100cc0c'
TOPIC_MINT_V1                 = '\xf114ca9eb82947af39f957fa726280fd3d5d81c3d7635a4aeb5c302962856eba'
TOPIC_REDEEM_V1               = '\x18fd144d7dbcbaa6f00fd47a84adc7dc3cc64a326ffa2dc7691a25e3837dba03'
TOPIC_CUSTODY_TRANSFER        = '\x90c5d8794dcf7c60ab2d20912d5228389b28f74d32af01e40894a784a90b9ac2'
TOPIC_DELEGATED_SIGNER_ADDED  = '\xed6a1f03e365a374bf7e9fe68b09cf74960528af699108cb461241efc5ded909'
TOPIC_DELEGATED_SIGNER_INIT   = '\x769c75d94dacde64c18415b5a72f6d26e7f62b356387f8da812c4b0aa66a0f25'
TOPIC_DELEGATED_SIGNER_REMOVED= '\x97b59d736dc70ae61c6b68295c19a1311cc4a48cbb9eb25c4dabf18c7f650a8a'
TOPIC_CUSTODIAN_ADDED         = '\xfbd30b5bdd51f5de989170dc23d65aac2de0a6099f5d9d200bc5779d883abcd4'
TOPIC_CUSTODIAN_REMOVED       = '\x75567811df62a6b68bd5ee394d5808ad7282e19541858be466bc789cad9d4dfb'
TOPIC_MINTER_UPDATED          = '\x1cf2de25c5bf439ac0287061c3a0fa69b3b02867d0ccfd2ded34e42577050b73'
TOPIC_TRANSFER                = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_4626_DEPOSIT            = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_4626_WITHDRAW           = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_REWARDS_RECEIVED        = '\xbb28dd7cd6be6f61828ea9158a04c5182c716a946a6d2f31f4864edb87471aa6'
TOPIC_COOLDOWN_DURATION_UPD   = '\x180eacdf7dbaeecaa983d93173b4285db2f2c0de0044697e1f932bbbb73dcaa6'
TOPIC_LOCKED_AMOUNT_REDIST    = '\xb8ef21f2b52f8ca740012254a6b10f17d2fd6e589f97ebf401fde0e8b9218937'
TOPIC_SENA_COOLDOWN_STARTED   = '\xa4b3d92c67ba96e840c4888c41c81bb378420dfa35fbdcec3c0581372fb06068'
TOPIC_SENA_UNSTAKE            = '\x390b1276974b9463e5d66ab10df69b6f3d7b930eb066a0e66df327edd2cc811c'
TOPIC_OFT_SENT                = '\x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a'
TOPIC_OFT_RECEIVED            = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
TOPIC_PEER_SET                = '\x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b'
TOPIC_RATE_LIMITS_CHANGED     = '\xe888347665897e637801f36c5129f510657276178c89022bc5fa0246dbc19de1'
TOPIC_SUSDE_OFT_BLACKLIST     = '\x0baadf7b35b83c7d3a00874b5406dca58c60d0ff7d8c825ad02ec55484beb455'
TOPIC_PSM_SWAP_AVAX_USDE      = '\x907f78e92aac9234fbd4c1ff8c47706974b6c47d390122ad766b87cb9851f2bc'
TOPIC_PSM_SWAP_ETH_USDTB      = '\x15b92345f3ead624d82ae7a06769cdcf0e6514cc18ab02e39feb37ff8edb69c8'
TOPIC_PSM_SWAP_DISABLED       = '\x0a4f9ef21a3f2d279073474702eab63d142b2a13bad81a6a9e36d450a559a516'
TOPIC_PSM_PEG_PRICE_UPDATED   = '\xde74e8620646dab58026910daf41220a351a98edc9bee3d8d63771590561b5d6'
TOPIC_USDTB_ACCOUNTS_BLOCKED  = '\x5444f9841c04ce78987f28701fa07fc4c112840c1c8439e8f52bda50c3788a87'
TOPIC_TIMELOCK_SCHEDULED      = '\x4cf4410cc57040e44862ef0f45f3dd5a5e02db8eb8add648d4b0e236f1d07dca'
TOPIC_TIMELOCK_EXECUTED       = '\xc2617efa69bab66782fa219543714338489c4e9e178271560a91b82c3f612b58'
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors (chain-agnostic) =====
SEL_MINT_V2                   = '\x96eea750'
SEL_MINT_WETH_V2              = '\x00d87483'
SEL_REDEEM_V2                 = '\x75c890dc'
SEL_TRANSFER_TO_CUSTODY_V2    = '\x2da09621'
SEL_SET_DELEGATED_SIGNER      = '\x53863613'
SEL_DISABLE_MINT_REDEEM       = '\xc5ff38bd'
SEL_SET_MINTER                = '\xfca3b5aa'
SEL_COOLDOWN_ASSETS           = '\xcdac52ed'
SEL_COOLDOWN_SHARES           = '\x9343d9e1'
SEL_UNSTAKE                   = '\xf2888dbb'
SEL_TRANSFER_IN_REWARDS       = '\xc80ef110'
SEL_SET_COOLDOWN_DURATION     = '\xce23eb3c'
SEL_OFT_SEND                  = '\xc7c7f5b3'
SEL_SET_PEER                  = '\x3400288b'
SEL_SET_RATE_LIMITS           = '\x46f943e9'
SEL_PSM_SWAP                  = '\x61912b0c'
-- ===== Addresses (network-specific) =====
ETH_USDE                      = '\x4c9edd5852cd905f086c759e8383e09bff1e68b3'
ETH_ETHENA_MINTING_V2         = '\xe3490297a08d6fc8da46edb7b6142e4f461b62d3'
ETH_ETHENA_MINTING_V1         = '\x2cc440b721d2cafd6d64908d6d8c4acc57f8afc3'
ETH_SUSDE                     = '\x9d39a5de30e57443bff2a8307a4256c8797a3497'
ETH_USDE_SILO                 = '\x7fc7c91d556b400afa565013e3f32055a0713425'
ETH_STAKING_REWARDS_DISTRIB   = '\xf2fa332bd83149c66b09b45670bce64746c6b439'
ETH_ENA                       = '\x57e114b691db790c35207b2e685d4a43181e6061'
ETH_SENA                      = '\x8be3460a480c80728a8c4d7a5d5303c85ba7b3b9'
ETH_RSENA                     = '\xc65433845ecd16688eda196497fa9130d6c47bd8'
ETH_USDTB                     = '\xc139190f447e929f090edeb554d95abb8b18ac1c'
ETH_USDTB_PSM                 = '\x73e35c5c35a274e34ade6eb13cc7f62aee323728'
ETH_USDTB_MINTING_LEGACY      = '\xa3ddbf92077b850e29c4805df0a2459ae048416a'
ETH_TIMELOCK                  = '\xe8dc0fab349ea169283c48ccfd09d797e6db7c94'
ETH_USDE_OFT_ADAPTER          = '\x5d3a1ff2b6bab83b63cd9ad0787074081a52ef34'
ETH_SUSDE_OFT_ADAPTER         = '\x211cc4dd073734da055fbf44a2b4667d5e5fe5d2'
ETH_ENA_OFT_ADAPTER           = '\x58538e6a46e07434d7e7375bc268d3cb839c0133'
L2_USDE_OFT                   = '\x5d3a1ff2b6bab83b63cd9ad0787074081a52ef34'  -- Base, BNB, Avax, Arb, OP, Robinhood
L2_SUSDE_OFT                  = '\x211cc4dd073734da055fbf44a2b4667d5e5fe5d2'  -- same six chains
L2_ENA_OFT                    = '\x58538e6a46e07434d7e7375bc268d3cb839c0133'  -- same six chains
AVAX_USDE_PSM                 = '\xa774f30bf4228a7de3ca4592b6032dc530d0e9e9'
PSM_CUSTODIAN_EOA             = '\xd7fcade52afb60fbf0e1e5f72a683f43820f56a0'
AVAX_DECOY_ENA_OFT            = '\x4c9edd5852cd905f086c759e8383e09bff1e68b3'  -- NOT Ethena
```

## 9. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the Sourcify-verified ABI of each contract (EthenaMinting V1/V2, StakedUSDeV2, USDe, ENA, StakedENA impl, AnchorageTokenUSDtb impl, MellowVaultCompat impl, USDtbMinting, both PSMs, StakingRewardsDistributor, USDeOFTAdapter, StakedUSDeOFTAdapter, ENAOFTAdapter, USDeOFT on Base and Robinhood Chain, StakedUSDeOFT on Base). Live `eth_getLogs` matched: V2 `Mint`/`Redeem` (50k ETH blocks); sUSDe `Deposit`/`Withdraw`/`RewardsReceived`; sENA `CooldownStarted`/`Unstake`; ETH USDe adapter `OFTSent`/`OFTReceived`; Robinhood USDe OFT `OFTSent` (200k blocks); Avalanche PSM `SwapExecuted` `0x907f78e9…` and `OraclePriceValidated`. The Robinhood sUSDe OFT is not verified on Sourcify; its OFT and blacklist selectors were confirmed by PUSH4 scan of the runtime code.
- **Addresses:** from the official key-addresses page, then checked with `eth_getCode` and characteristic views (`symbol()`, `token()`, `endpoint()`, `owner()`, `peers(eid)`, `minter()`, `silo()`, `asset()`). The Avalanche USDe PSM was found from the PSM Custodian's USDe transfers (tx `0xfcb177bc…502f`, `swap` call).
- **Proxies:** EIP-1967 implementation and admin slots read live on every listed contract.
- **Chain coverage:** Polygon PoS and Arc return `0x` for every literal, and the Ethereum adapters hold no peer for EID 30109 or 30417. A USDe PSM on Ethereum was not found. The custodian EOA has 30 transactions on Ethereum, so an Ethereum PSM address is unverified. A sENA OFT on L2s was not found and not searched further.

Authoritative sources:
- [Ethena key addresses](https://docs.ethena.fi/solution-design/key-addresses)
- [ethena-labs GitHub](https://github.com/ethena-labs)
- [Sourcify](https://sourcify.dev) verified sources for the contracts above
- Explorers: [Etherscan](https://etherscan.io/address/0xe3490297a08d6fC8Da46Edb7B6142E4F461b62D3) · [Basescan](https://basescan.org/address/0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34) · [Snowtrace](https://snowtrace.io/address/0xa774f30bf4228a7de3ca4592b6032dc530d0e9e9) · [Arbiscan](https://arbiscan.io/address/0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34) · [Robinhood Chain explorer](https://explorer.chain.robinhood.com/address/0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34)
