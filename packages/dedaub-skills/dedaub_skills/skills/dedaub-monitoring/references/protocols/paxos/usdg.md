# Paxos USDG (Global Dollar) — Topics, Selectors, Addresses (Ethereum, Arbitrum One, Robinhood Chain)

**Status:** verified against live RPC on all nine target chains, the `paxosglobal/paxos-token-contracts` and `paxosglobal/usdg-contract` repos, Sourcify-verified source on Robinhood Chain, and the Paxos developer docs on 2026-10-30.
**Scope:** the USDG token proxy, its facets, its `SupplyControl` contract, its LayerZero `OFTWrapper`, and its admin timelock. USDG is live on **Ethereum (1)**, **Arbitrum One (42161)** and **Robinhood Chain (4663)**. USDG is **not deployed** on Base, BNB, Avalanche, Optimism, Polygon PoS or Arc. Topics and selectors are chain-agnostic. Addresses are network-specific.

USDG is a 6-decimal USD stablecoin that Paxos issues. All three deployments run the same **V3 "claimable rewards" build** (`PaxosTokenClaimableRewards` + `USDG.sol`). The token is a **UUPS proxy**. Part of its ABI lives in **facets**: the proxy keeps a `selector → facet` map (`getFacet(bytes4)`) and delegates unknown selectors to the facet. Pause, freeze and wipe live in the `TokenAdminFacet`. Permit and EIP-3009 live in the `TokenExtensionsFacet`. Rewards live in three more facets. All events come from the **token proxy address**, also when a facet runs the code.

Supply goes through a separate **`SupplyControl`** contract. A supply controller calls `increaseSupplyToAddress` / `decreaseSupplyFromAddress` (or `mint` / `burn`) on the token. The token asks `SupplyControl` for a rate-limit and whitelist check. The LayerZero `OFTWrapper` is one of the supply controllers. A bridge transfer therefore **burns on the source chain and mints on the destination chain**. It is not a lock on Ethereum.

The token `DEFAULT_ADMIN_ROLE` holder is a **TimelockController** on each chain (`getMinDelay()` = 86 400 s). The token uses `AccessControlDefaultAdminRules` with `defaultAdminDelay()` = 10 800 s.

---

## 0. Contract families & versions

| Contract | Role | Proxy? |
|----------|------|--------|
| **USDG token** (`USDG` → `PaxosTokenClaimableRewards`) | ERC-20, 6 decimals. Supply, pause, freeze, wipe, rewards. Emits every token event. | UUPS (EIP-1967) |
| **TokenAdminFacet** | `pause`, `unpause`, `freeze*`, `unfreeze*`, `wipeFrozenAddress`, `setSupplyControl`, `reclaimToken`. | Facet (called by delegatecall) |
| **TokenExtensionsFacet** | EIP-2612 `permit`, EIP-3009 `transferWithAuthorization` / `receiveWithAuthorization` / `cancelAuthorization`. | Facet |
| **ClaimableRewardsFacet**, **MultiplierMgmtFacet**, **PayoutGroupFacet** | Opt-in USDG rewards: payout groups, APR multipliers, claims. | Facets |
| **SupplyControl** | Holds `SUPPLY_CONTROLLER_ROLE` set, per-controller rate limit and mint-address whitelist. | UUPS (EIP-1967) |
| **OFTWrapper** | LayerZero OFT. Burns on send and mints on receive through the token. | ETH: plain contract. ARB, Robinhood: EIP-1967 proxy |
| **TimelockController** | `DEFAULT_ADMIN_ROLE` / `owner()` of token and SupplyControl. | Not a proxy (6 754 B) |

Older USDG builds (`contracts/archive/USDGv2.sol`, `PaxosTokenV2`) are replaced on all three chains. `getFacet` answers on all three chains, which proves the V3 build.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Token — supply, pause, freeze, admin

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | Mint = `from` 0x0. Burn and wipe = `to` 0x0. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | |
| `0xf5c174d57843e57fea3c649fdde37f015ef08750759cbee88060390566a98797` | `SupplyIncreased(address indexed to, uint256 value)` | **Mint.** Fires before the mint `Transfer`. Live: 67 in 5 000 ETH blocks. |
| `0x1b7e18241beced0d7f41fbab1ea8ed468732edbcb74ec4420151654ca71c8a63` | `SupplyDecreased(address indexed from, uint256 value)` | **Burn.** Also fires on `wipeFrozenAddress`. Live: 62 in 5 000 ETH blocks. |
| `0x487be0c63489145f3de4a36cd994bf4e0d32c7b76278d82639aef690a9ba6481` | `SupplyControlSet(address indexed supplyControlAddress)` | SupplyControl pointer changed. Critical. |
| `0x6985a02210a168e66602d3235cb6db0e70f92b3ba4d376a33c0f3d9434bff625` | `Pause()` | All transfers stop. Note the name: `Pause`, not `Paused`. |
| `0x7805862f689e2f13df9f062ff482ad3ad112aca9e0847911ed832e158c525b33` | `Unpause()` | |
| `0x1aa660498c83ea285bc55e4cfc00afcaa7120798db87b74f3c0d7c6e001bc392` | `FreezeAddress(address indexed addr)` | Asset-protection freeze. Live: 2 in 5 000 ETH blocks. |
| `0x150465b020dfc06a59269da94ed66db9b65a516cf4fdd5f583b0f12752339bbe` | `UnfreezeAddress(address indexed addr)` | |
| `0xfc5960f1c5a5d2b60f031bf534af053b1bf7d9881989afaeb8b1d164db23aede` | `FrozenAddressWiped(address indexed addr)` | **Seizure.** Followed by `SupplyDecreased` + `Transfer(addr→0x0)` for the full balance. |
| `0xa0617f7f8c7f456232c25e291a9fa28d43b790b6e0886ac5cd080c3ac2736d54` | `RewardsFrozen(address indexed addr, uint32 indexed payoutGroupId, uint256 rewards)` | Freeze of a registered account also freezes its rewards. |
| `0xbcc6cd3a93555662c38ad4d39451e56fd9245c71079160b896011fdff4740d07` | `FrozenRewardsLost(address indexed addr, uint32 indexed payoutGroupId, uint256 rewards)` | Rewards dropped at wipe. |
| `0x59277b34e7bfaca5e93a39d132e8eccf6712605952797722701ea2ae717a914a` | `FacetUpdate(bytes4 indexed selector, address indexed facet)` | **Code change without `Upgraded`.** A facet swap changes behavior of that selector. |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | UUPS impl rotation (token and SupplyControl). |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` | `initializeV3` sets version 3. |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` | |
| `0x3377dc44241e779dd06afab5b788a35ca5f3b778836e2990bdb26a2a4b2e5ed6` | `DefaultAdminTransferScheduled(address indexed newAdmin, uint48 acceptSchedule)` | Admin hand-over starts. |
| `0x8886ebfc4259abdbc16601dd8fb5678e54878f47b3c34836cfc51154a9605109` | `DefaultAdminTransferCanceled()` | |
| `0xf1038c18cf84a56e432fdbfaf746924b7ea511dfe03a6506a0ceba4888788d9b` | `DefaultAdminDelayChangeScheduled(uint48 newDelay, uint48 effectSchedule)` | |
| `0x2b1fa2edafe6f7b9e97c1a9e0c3660e645beb2dcaa2d45bdbf9beaf5472e1ec5` | `DefaultAdminDelayChangeCanceled()` | |

### 1.2 Token — signatures (TokenExtensionsFacet)

| topic0 | Event |
|--------|-------|
| `0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5` | `AuthorizationUsed(address indexed authorizer, bytes32 indexed nonce)` — EIP-3009. Live: 62 in 5 000 ETH blocks. |
| `0x1cdd46ff242716cdaa72d159d339a485b3438398348d68f09d7c8c0a59353d81` | `AuthorizationCanceled(address indexed authorizer, bytes32 indexed nonce)` |
| `0xd309466d0e5c5e3b306abfb2c1e7f3b4318b670dbd1236cc92288848a27384cb` | `AuthorizationAlreadyUsed(address indexed authorizer, bytes32 indexed nonce)` |
| `0x60e6c600b4dc8176ae4c5a9601882377a03221df165888028ff44d163565af78` | `PermitInvalidated(address indexed owner, uint256 newNonce)` |

### 1.3 Token — rewards facets

| topic0 | Event |
|--------|-------|
| `0x997634cd7c2e5ba4311eaa9fabce302a0535d484406da0d670c35f07d8cab0c3` | `MultiplierCreated(uint32 indexed multiplierId, uint256 apr, uint256 timestamp)` |
| `0x9a39defd85f4cb654457e8c57271582616c42b05c6d139d7c4c79395626f25e3` | `MultiplierDeleted(uint32 indexed multiplierId)` |
| `0xb51d41cb1561e9f3a6ca887943afe8feb5e76732f397d4acee6ebf2fc01ebc0d` | `MaturityPeriodSet(uint32 indexed multiplierId, uint256 maturityPeriod)` |
| `0xd45ec4c8b98127d638b26172724c6ebf59d086e75aaa364a517c7cff2a1b148b` | `MultiplierRateScheduled(uint32 indexed multiplierId, uint256 newRate, uint256 scheduledTime)` |
| `0x250cda044478c56f29aad456e3429c3d9cf4897706176ac1e2c23a1156ada1c2` | `ClaimSourceSet(address indexed oldSource, address indexed newSource)` — reward funding wallet changed. |
| `0x425c9028cece781e2348965e7854c1c171e463a0800b9f4a3e575a0f38868fa7` | `RateBoundsSet(uint256 minRate, uint256 maxRate)` |
| `0xbf298eacf7afec7ce8a98803e084cf3e2f0c204c635e3970c5cd9560d262e287` | `ReferenceTimeUpdated(uint40 oldReferenceTime, uint40 newReferenceTime)` |
| `0x67e62f0993b6875ac196752a4ee84d1dfd1f5ff6c0109367a88e549d7a25273b` | `PayoutGroupCreated(uint32 indexed payoutGroupId, address indexed claimer, uint32 indexed multiplierId)` |
| `0x0698c4827d32b15ce9133e5235dd173205c32e6f72fe40e441ad37463973841c` | `PayoutGroupDeleted(uint32 indexed payoutGroupId, address indexed claimer)` |
| `0x959a1da166467336c06a9148d8060d06c4168057a1111bcf3f44ee0c0c888ed3` | `PayoutGroupMultiplierUpdated(uint32 indexed payoutGroupId, address indexed claimer, uint32 oldMultiplierId, uint32 newMultiplierId)` |
| `0x8eed275f694a6e0b390a1fc8113470644f28537fa3b0a9e10e318e9cbc2147a1` | `PayoutClaimerUpdated(uint32 indexed payoutGroupId, address indexed oldClaimer, address indexed newClaimer)` |
| `0x32564c3c51df2fc5de686a9326c16f1b869666139801e697c00d7ab191e3f149` | `PayoutGroupManagerSet(uint32 indexed payoutGroupId, address indexed oldManager, address indexed newManager)` |
| `0x72dcb3ea99ce44f47f9eae92cf0a87d83973d3ab4160771e09219c2298ab9772` | `PayoutGroupDestinationSet(uint32 indexed payoutGroupId, address indexed oldDestination, address indexed newDestination)` |
| `0x54b680c25de641360089080dd69e7331acba8b8b780bf3a9753be6637aaab30a` | `PartnerSignedRegistrationsEnabledSet(bool enabled)` |
| `0x571ca763815c57afa7bc42f0d72b44ea462729b9e7b88c00c851699f582cf1df` | `AccountRegistered(address indexed account, uint32 indexed payoutGroupId, address indexed claimer)` — live: 13 in 5 000 ETH blocks. |
| `0x45816ce7e94486f9466592cd06a3b0bab80654f01f90227665c5bf8d121219c5` | `AccountDeregistered(address indexed account, uint32 indexed payoutGroupId, address indexed claimer)` |
| `0xa2c93e4e3553f7215f05ced06ecf3680ff6492f86ea8efc17aba50703d0101bf` | `RegistrationProposed(address indexed account, uint32 indexed payoutGroupId, address indexed proposer)` |
| `0x087d7e6cb04bd41c3bd8df49dae5fe66af18687851b98a5ad5a6156322d228ff` | `RegistrationAccepted(address indexed account, uint32 indexed payoutGroupId)` |
| `0xc4f65e1557bb45f621bcf3ddd2c9d310307d9777ee5dc50e94fb2892ca86e592` | `RegistrationProposalCancelled(address indexed account, uint32 indexed payoutGroupId, address indexed proposer)` |
| `0x816f875a24baac452f66d9227daaed861604a07d92afb48b4cc5ff47f91f7cdd` | `RewardsClaimed(address indexed account, uint32 indexed payoutGroupId, address indexed recipient, uint256 amount)` |
| `0x0cdba4eda8e3ee829e6161843589bc94134d3ce43735ebab9b8f575eefe3887f` | `RewardsClaimedBatch(uint32 indexed payoutGroupId, address indexed executor, address indexed destination, uint256 totalAmount, uint256 accountCount)` |
| `0x7ee8ddc3497143e7ee6f1bd1775764431bdab617a0b1ac428f7dc57aefef0b8f` | `ClaimAllExecuted(uint32 indexed payoutGroupId, address indexed executor, address indexed destination, uint256 amount)` — live: 35 in 5 000 ETH blocks. |

### 1.4 SupplyControl

| topic0 | Event |
|--------|-------|
| `0xcf08d9c60bf75a87f915d1f62a8e5b60875469e6028860b969cf17bbdadb3c26` | `SupplyControllerAdded(address indexed newSupplyController, uint256 limitCapacity, uint256 refillPerSecond, address[] mintAddressWhitelist, bool allowAnyMintAndBurnAddress)` — **new minter.** |
| `0xbef3e51271d83375b825aac948002d0e0f566ec012b8939ddec68201ce6f00f6` | `SupplyControllerRemoved(address indexed oldSupplyController)` |
| `0x2a92a9859049106ef4ecbc9a8259d8514994cbe533fab8d7b64020fd2037eb10` | `LimitConfigUpdated(address indexed supplyController, (uint256,uint256) newLimitConfig, (uint256,uint256) oldLimitConfig)` — `(limitCapacity, refillPerSecond)`. |
| `0x655668ebb9d503c12fddfb0f06df9b5d5cdc79b7ac8d0adb23b066f7d11a27c0` | `AllowAnyMintAndBurnAddressUpdated(address indexed supplyController, bool newAllowAnyMintAndBurnAddress, bool oldAllowAnyMintAndBurnAddress)` |
| `0xf03ae459ca1082dbfa96d80d1ca78e7dea8d82cc8b51ee915544cd48a60bbaa0` | `MintAddressAddedToWhitelist(address indexed supplyController, address indexed mintAddress)` |
| `0x2faa07c0335a8ebb1e86a429ab8be591db3911703a6e2fb9f1f933acc0901e5f` | `MintAddressRemovedFromWhitelist(address indexed supplyController, address indexed mintAddress)` |

SupplyControl also emits the OpenZeppelin `RoleGranted` / `RoleRevoked` / `Upgraded` topics from §1.1.

### 1.5 OFTWrapper (LayerZero v2)

| topic0 | Event |
|--------|-------|
| `0x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a` | `OFTSent(bytes32 indexed guid, uint32 dstEid, address indexed fromAddress, uint256 amountSentLD, uint256 amountReceivedLD)` — live: 95 in 10 000 ETH blocks. |
| `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c` | `OFTReceived(bytes32 indexed guid, uint32 srcEid, address indexed toAddress, uint256 amountReceivedLD)` — live: 103 in 10 000 ETH blocks. |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |

The full LayerZero OApp event set is in the LayerZero v2 reference.

### 1.6 Role hashes (`bytes32`, topic1 of `RoleGranted` / `RoleRevoked`)

| Role | Value | Where |
|------|-------|-------|
| `DEFAULT_ADMIN_ROLE` | `0x0000000000000000000000000000000000000000000000000000000000000000` | token, SupplyControl |
| `PAUSE_ROLE` | `0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d` | token |
| `ASSET_PROTECTION_ROLE` | `0xe3e4f9d7569515307c0cdec302af069a93c9e33f325269bac70e6e22465a9796` | token (freeze / wipe) |
| `MULT_ADMIN_ROLE` | `0xf87083816642e3d7d4c29c8bd120d38d20e635cf3accc9943b0756f540e63540` | token rewards |
| `MULT_RATE_ROLE` | `0x14682d1851e1b102da952c0c155677821e8e89b896948538617aeba3934d06d0` | token rewards |
| `PAYOUT_GROUP_REGISTRAR_ROLE` | `0xf5c39a02a674f3b0c47512a808c655a0c55648b86b6692986c44c50338bc017b` | token rewards |
| `PAYOUT_GROUP_ADMIN_ROLE` | `0x2a0ee64a69dc50e5023a090c1c7c133118b1a3e330e9b8e053b6b63523a91a9d` | token rewards |
| `CLAIM_OPERATOR_ROLE` | `0x36dc7495d0ae0bc2a620bf292049e4d4e5f800043895b13c08a1977d3a3297f5` | token rewards |
| `CLAIM_ADMIN_ROLE` | `0xb552f1bea17e2734c4b1d253bbc784c04b883a78e93589442d4b5d6e6a2f73bd` | token rewards |
| `SUPPLY_CONTROLLER_MANAGER_ROLE` | `0x5d3e9f1ecbcdad7b0da30e7d29c9eddaef83a4502dafe3d2dd85cfdb12e4af10` | SupplyControl |
| `SUPPLY_CONTROLLER_ROLE` | `0x9c00d6f280439b1dfa4da90321e0a3f3c2e87280f4d07fea9fa43ff2cf02df2b` | SupplyControl (minters) |
| `TOKEN_CONTRACT_ROLE` | `0xd32fd1ee5f4f111da6f27444787e5200ec57a8849509c00ef2998467052b32a3` | SupplyControl (the token) |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Token — supply and admin

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x076bdc36` | `increaseSupplyToAddress(uint256,address)` | Supply controller mint. Emits `SupplyIncreased` + `Transfer`. The OFTWrapper mints with this call. |
| `0xb921e163` | `increaseSupply(uint256)` | Mint to `msg.sender`. |
| `0x40c10f19` | `mint(address,uint256)` | Alias of `increaseSupplyToAddress`. |
| `0x1f17c083` | `decreaseSupplyFromAddress(uint256,address)` | Supply controller burn. The OFTWrapper burns with this call. |
| `0x98e52f9a` | `decreaseSupply(uint256)` | Burn from `msg.sender`. |
| `0x42966c68` | `burn(uint256)` | Alias of `decreaseSupply`. |
| `0x8456cb59` | `pause()` | `PAUSE_ROLE`. Facet. |
| `0x3f4ba83a` | `unpause()` | `PAUSE_ROLE`. Facet. |
| `0x5c975abb` | `paused()` | view. Facet. |
| `0x8d1fdf2f` | `freeze(address)` | `ASSET_PROTECTION_ROLE`. Facet. |
| `0x4cfd7a57` | `freezeBatch(address[])` | `ASSET_PROTECTION_ROLE`. Facet. |
| `0x45c8b1a6` | `unfreeze(address)` | `ASSET_PROTECTION_ROLE`. Facet. |
| `0xfd89d324` | `unfreezeBatch(address[])` | `ASSET_PROTECTION_ROLE`. Facet. |
| `0xe2f72f03` | `wipeFrozenAddress(address)` | `ASSET_PROTECTION_ROLE`. Burns the full balance of a frozen address. Facet. |
| `0xe5839836` | `isFrozen(address)` | view. Facet. |
| `0xd7d4db3d` | `getFrozenData(address)` | view. Facet. |
| `0x52e5a050` | `setSupplyControl(address)` | `DEFAULT_ADMIN_ROLE`. Facet. |
| `0x4a254dfe` | `supplyControl()` | view → SupplyControl address. |
| `0xfff28137` | `reclaimToken()` | `DEFAULT_ADMIN_ROLE`. Sweeps USDG held by the token contract. |
| `0x3dc23d0c` | `setFacet(bytes4,address)` | `DEFAULT_ADMIN_ROLE`. Emits `FacetUpdate`. |
| `0x4b2422da` | `batchSetFacet((address,bytes4[])[])` | `DEFAULT_ADMIN_ROLE`. |
| `0x112b6a67` | `getFacet(bytes4)` | view → facet for a selector. |
| `0x3659cfe6` | `upgradeTo(address)` | UUPS, `DEFAULT_ADMIN_ROLE`. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | UUPS, `DEFAULT_ADMIN_ROLE`. |
| `0x2f2ff15d` | `grantRole(bytes32,address)` | |
| `0xd547741f` | `revokeRole(bytes32,address)` | |
| `0x634e93da` | `beginDefaultAdminTransfer(address)` | |
| `0xcefc1429` | `acceptDefaultAdminTransfer()` | |
| `0x84ef8ffc` | `defaultAdmin()` | view. Same value as `owner()` `0x8da5cb5b`. |

### 2.2 Token — transfers and signatures

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa9059cbb` | `transfer(address,uint256)` | Reverts when paused or when either side is frozen. |
| `0x23b872dd` | `transferFrom(address,address,uint256)` | |
| `0xba1b7e76` | `transferFromBatch(address[],address[],uint256[])` | Batch pull. |
| `0x095ea7b3` | `approve(address,uint256)` | |
| `0xd73dd623` | `increaseApproval(address,uint256)` | |
| `0x66188463` | `decreaseApproval(address,uint256)` | |
| `0xd505accf` | `permit(address,address,uint256,uint256,uint8,bytes32,bytes32)` | EIP-2612. Facet. |
| `0x9fd5a6cf` | `permit(address,address,uint256,uint256,bytes)` | Signature-bytes form. Facet. |
| `0x5659abed` | `cancelPermits(uint256)` | Emits `PermitInvalidated`. |
| `0xe3ee160e` | `transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)` | EIP-3009. Facet. |
| `0xcf092995` | `transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,bytes)` | |
| `0xef55bec6` | `receiveWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)` | |
| `0x88b7ab63` | `receiveWithAuthorization(address,address,uint256,uint256,uint256,bytes32,bytes)` | |
| `0x5a049a70` | `cancelAuthorization(address,bytes32,uint8,bytes32,bytes32)` | |

### 2.3 Token — rewards facets (key entries)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x72da5bcb` | `claimAll(uint32)` | Pays a payout group. Emits `ClaimAllExecuted`. |
| `0x3680df99` | `claimAllTo(uint32,address)` | |
| `0x40d14d5f` | `claimForAddresses(uint32,address[])` | |
| `0x9dbae0d7` | `claimForAddressesTo(uint32,address[],address)` | |
| `0x5373d7f1` | `createMultiplier(uint256)` | `MULT_ADMIN_ROLE`. |
| `0xb7cdb86e` | `setMultiplierRateByAPR(uint32,uint256)` | `MULT_ADMIN_ROLE`. |
| `0xbb49d2fd` | `scheduleNextMultRateByAPR(uint32,uint256,uint32)` | `MULT_RATE_ROLE`. |
| `0x4d3b18e4` | `setClaimSource(address)` | `MULT_ADMIN_ROLE`. |
| `0x5a14b3b9` | `setRateBoundsByAPR(uint256,uint256)` | `MULT_ADMIN_ROLE`. |
| `0x7776b616` | `createPayoutGroup(uint32,address)` | `PAYOUT_GROUP_REGISTRAR_ROLE`. |
| `0x8e12e8b6` | `registrarRegisterRewardAddress(uint32,address)` | |
| `0x9421f1d9` | `registerRewardAddress(uint32,address,bytes32,uint256,bytes)` | Partner-signed registration. |
| `0x462a5ef7` | `unregisterRewardAddress(uint32,address)` | |
| `0xa54c2732` | `availableRewardsOf(address)` | view. |
| `0xb04647e9` | `payoutGroupIdOf(address)` | view. |
| `0x89e89d43` | `getCurrentAPY(uint32)` | view. |

### 2.4 SupplyControl

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x49005a32` | `addSupplyController(address,uint256,uint256,address[],bool)` | `SUPPLY_CONTROLLER_MANAGER_ROLE`. |
| `0x1b03a29a` | `removeSupplyController(address)` | |
| `0x19d39126` | `updateLimitConfig(address,uint256,uint256)` | |
| `0x29acfb43` | `updateAllowAnyMintAndBurnAddress(address,bool)` | |
| `0xe66a4323` | `addMintAddressToWhitelist(address,address)` | |
| `0xccc51ea9` | `removeMintAddressFromWhitelist(address,address)` | |
| `0x6190bfb0` | `getAllSupplyControllerAddresses()` | view → `address[]`. |
| `0xc248f7d6` | `getSupplyControllerConfig(address)` | view. |
| `0xcf7e6100` | `getRemainingMintAmount(address,uint256)` | view. |
| `0x5ce0a033` | `canMintToAddress(address,uint256,address)` | Called by the token on each mint (`TOKEN_CONTRACT_ROLE`). |
| `0xa8bb78c4` | `canBurnFromAddress(address,address)` | view. Called by the token on each burn. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified with `eth_getCode` on `https://ethereum-rpc.publicnode.com` on 2026-10-30.

| Role | Address | One-liner |
|------|---------|-----------|
| **USDG token** | `0xe343167631d89B6Ffc58B88d6b7fB0228795491D` | 708 B ERC-1967 proxy. Impl `0xfacd5ff359adf87822374275699dd518aaf9a65f`. `totalSupply` 360.83 M USDG. |
| **SupplyControl** | `0x9a7164112029b81c07636AB7b59fA813E0883BBF` | 708 B ERC-1967 proxy. Impl `0x9e12c058a20c5b0eebaa00e44a712ec54b838971`. |
| **OFTWrapper** | `0x147BdE4F997f0d4C7544ED0C55eAcf1E5E6bf9c4` | 12 678 B plain contract. `token()` = USDG. `owner()` `0x3af3e85f4f97de7ad0f000b724fb77fe5ffc024b`. |
| **TimelockController** (admin) | `0x9036566eaa5f83e0b9e1161c6c602b0adf997654` | `defaultAdmin()` / `owner()` of token and SupplyControl. `getMinDelay()` 86 400. |
| TokenAdminFacet | `0xe90c0e2fecd06c5875b50f6b13f3b8dbdb4ce946` | `getFacet(freeze)`. |
| TokenExtensionsFacet | `0x7569ae2be6ac51ed7f92f8167090b52615f86497` | `getFacet(transferWithAuthorization)`. |
| ClaimableRewardsFacet | `0x2fe2faef627a56e811e09b4e1b810b59f38f3a81` | `getFacet(claimAll)`. |
| MultiplierMgmtFacet | `0x018a090fb8d50376bf8464922ffda935a1fe2859` | `getFacet(createMultiplier)`. |
| PayoutGroupFacet | `0x77fe0365db15a1ec05833b7c1802d68356a363df` | `getFacet(createPayoutGroup)`. |

Supply controllers (`getAllSupplyControllerAddresses()`): `0xf845a0a05cbd91ac15c3e59d126de5dfbc2aabb7` (EOA), `0x2fb074fa59c9294c71246825c1c9a0c7782d41a4` (EOA), `0x147bde4f…` (OFTWrapper), `0x835e20da02d830d6074ca2341e2928f438121691` (EOA), `0x40d16a860e295fb4e096cdb5e99c32721194add4` (170 B proxy).

## 4. Addresses — Arbitrum One (chain ID 42161)

Verified with `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com` and `https://arb1.arbitrum.io/rpc` on 2026-10-30. Native issuance (not a bridged representation).

| Role | Address | One-liner |
|------|---------|-----------|
| **USDG token** | `0x004B506865409877C9fA29bfb1ebA929984B9bbC` | 170 B ERC-1967 proxy. Impl `0x031610e2d186d78d3defbf907f56d1eac843d9de`. `totalSupply` 51.64 M USDG. |
| **SupplyControl** | `0x359a1Ee087abD3042151b93eC8EA462D6B27bcb6` | 170 B ERC-1967 proxy. Impl `0xc5c897656dec8161de64120d54ad937d7ec7de29`. |
| **OFTWrapper** | `0xC3274Ec3f772D8534575EaAd5231cf250a48b6b6` | 708 B ERC-1967 proxy. Impl `0xb01e831c57b1dfb9b217595251919903ec51e8ce`. `token()` = USDG. |
| **TimelockController** (admin) | `0x6c9e821ade9efc1bcda763f9942dd7822d6e86b4` | `getMinDelay()` 86 400. |
| TokenAdminFacet | `0x83442a9b6d51d8a125aa91f44787f16b311aca27` | |
| TokenExtensionsFacet | `0xce517f3b818d7552b4bd5944fbfaab9a07afc0b6` | |
| ClaimableRewardsFacet | `0xbe00bfff3833883d966801751f84165f0a2a2e76` | |
| MultiplierMgmtFacet | `0x0219fce1c5cc06eb7de6d8cb13b7b01ccceb306a` | |
| PayoutGroupFacet | `0x94b7de346afaff550f393335acaf4a2b9ffee72b` | |

Supply controllers: `0xf845a0a0…`, `0x2fb074fa…`, `0xc3274ec3…` (OFTWrapper), `0x835e20da…`.

**Decoy:** the Ethereum USDG literal `0xe343…491D` has code on Arbitrum. That contract is **"Flux USD" (`FLX`)**, a different token with `totalSupply` 0. Do not use it as USDG on Arbitrum.

## 5. Addresses — Robinhood Chain (chain ID 4663)

Verified with `eth_getCode` on `https://rpc.mainnet.chain.robinhood.com` on 2026-10-30. Source is Sourcify-verified (`contracts/stablecoins/USDG.sol:USDG`, solc 0.8.28).

| Role | Address | One-liner |
|------|---------|-----------|
| **USDG token** | `0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168` | 170 B ERC-1967 proxy. Impl `0x68184c449e1a8f34fa18d289737129fd27b66f8f`. `totalSupply` 687.64 M USDG. Main quote asset on Robinhood Chain. |
| **SupplyControl** | `0xdf5FfF9cb88B3cAb50572FAE73E2EB08599D25D4` | 170 B ERC-1967 proxy. Impl `0xa83de9d4f4116b9699bab8c70cb8ce9634c3ae24`. |
| **OFTWrapper** | `0x0d54755f5106BfdB43f7a35f5D49a23F940628d1` | 708 B ERC-1967 proxy. Impl `0x0e0cdcd065d885a36586a0706bdeab31a5c09150`. `token()` = USDG. |
| **TimelockController** (admin) | `0xcfa0388f5ddf905fdc08c45c716c15dc10a14c6f` | `getMinDelay()` 86 400. |
| TokenAdminFacet | `0x58cab81e3d8468a0e90df8cbfacb34535e1de942` | |
| TokenExtensionsFacet | `0x780d30b6a89bc9eef953a543aa288c3b05b01309` | |
| ClaimableRewardsFacet | `0xc5dc7ec334414900632275b92858860c4c4688d7` | |
| MultiplierMgmtFacet | `0xa295a2661c02aea11a2b34d412fadd3507660dab` | |
| PayoutGroupFacet | `0xdc3ef8ab3eb30d62e04dbe8a804d232573aa1fe5` | |

Supply controllers: `0xf845a0a0…`, `0x2fb074fa…`, `0x0d54755f…` (OFTWrapper, added block 33 411), `0x835e20da…` (added block 66 440 401).

Role history (full `RoleGranted` back-fill, blocks 0–101.8 M): `PAUSE_ROLE`, `ASSET_PROTECTION_ROLE`, `MULT_ADMIN_ROLE`, `PAYOUT_GROUP_ADMIN_ROLE`, `CLAIM_ADMIN_ROLE` and SupplyControl `SUPPLY_CONTROLLER_MANAGER_ROLE` → `0x3af3e85f4f97de7ad0f000b724fb77fe5ffc024b` (no code; the same address is owner of PYUSD and USDP on Ethereum). `MULT_RATE_ROLE` → `0x4e4336d068df68000d6d6ab326feef9ad4faeef8`. `PAYOUT_GROUP_REGISTRAR_ROLE` → `0x55f78e37adb9d1f6931c1da7314b374558ae9684`. `CLAIM_OPERATOR_ROLE` → `0x5fd949b0fd3a994a6d7e364c82e43be23de22e38`. No `RoleRevoked`. The token emitted 238 `FacetUpdate` (all at initialization) and **27 `FreezeAddress`** events in that range.

## 6. Chains with no USDG

`eth_getCode` returns `0x` for every USDG, SupplyControl and OFTWrapper literal above on **Base, BNB, Avalanche, Optimism and Arc**. On **Polygon PoS**, the Ethereum literal `0xe343…491D` holds an unrelated 17 396 B contract whose `token()` returns PYUSD. It is not USDG. The Paxos docs also list Ink, Mantle, X Layer and Solana. Those chains are outside the nine targets.

---

## 7. Cross-chain summary

| Chain | ID | USDG token | SupplyControl | OFTWrapper | Admin timelock |
|-------|----|-----------|---------------|------------|----------------|
| Ethereum | 1 | `0xe343…491D` | `0x9a71…3BBF` | `0x147B…f9c4` | `0x9036…7654` |
| Arbitrum One | 42161 | `0x004B…9bbC` | `0x359a…bcb6` | `0xC327…b6b6` | `0x6c9e…86b4` |
| Robinhood Chain | 4663 | `0x5fc5…d168` | `0xdf5F…25D4` | `0x0d54…28d1` | `0xcfa0…4c6f` |
| Base · BNB · Avalanche · Optimism · Polygon · Arc | — | — | — | — | — |

The token address is different on each chain. No vanity pattern exists. Supply controllers `0xf845a0a0…`, `0x2fb074fa…` and `0x835e20da…` are the same EOAs on all three chains.

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **USDG token** | UUPS (ERC-1967) + selector facets | EIP-1967 impl slot set, admin slot empty. ETH proxy 708 B, ARB / Robinhood 170 B. | `upgradeTo` / `upgradeToAndCall` by `DEFAULT_ADMIN_ROLE` (timelock). `setFacet` / `batchSetFacet` by the same role. |
| **SupplyControl** | UUPS (ERC-1967) | Impl slot set, admin slot empty. | `DEFAULT_ADMIN_ROLE` (timelock). |
| **OFTWrapper — ETH** | Not a proxy | Impl slot empty. 12 678 B. | Replace by a new deploy plus a SupplyControl role change. |
| **OFTWrapper — ARB, Robinhood** | ERC-1967 proxy (`OFTWrapperUpgradeable`) | Impl slot set. | Owner. |
| **TimelockController** | Not a proxy | 6 754 B on all three chains. | Self-governed. |

Watch `Upgraded(address)` `0xbc7cd75a…2d3b` **and** `FacetUpdate(bytes4,address)` `0x59277b34…914a` on the token. A facet change alters `pause`, `freeze` or permit logic with no `Upgraded` event.

---

## 9. Detection invariants & gotchas

1. **Mint = `SupplyIncreased` + `Transfer(0x0 → to)`. Burn = `SupplyDecreased` + `Transfer(from → 0x0)`.** Both pairs come from the token proxy in the same transaction. Key supply alerts on `SupplyIncreased` / `SupplyDecreased`. They carry the real recipient or source.
2. **Wipe is a burn.** `wipeFrozenAddress` emits `FrozenAddressWiped`, then `SupplyDecreased` and `Transfer(addr → 0x0)` for the full balance. A supply monitor that ignores `FrozenAddressWiped` will see an unexplained burn.
3. **Event names are `Pause()` / `Unpause()`.** The OpenZeppelin `Paused(address)` topic never fires on USDG.
4. **`SupplyControlSet` has two shapes with one topic0.** The V3 token indexes the address (2 topics). The older `PaxosTokenV2` build does not index it (address in `data`). Decode both shapes.
5. **Facets emit through the proxy.** `FreezeAddress`, `AuthorizationUsed` and rewards events have the token proxy as emitter. Never filter on facet addresses.
6. **Bridge flows are burn/mint, not lock/unlock.** The OFTWrapper is a supply controller on every chain, Ethereum included. An `OFTSent` on chain A pairs with a burn on A. The matching `OFTReceived` on chain B pairs with a mint on B. Join on `guid`.
7. **The OFTWrapper is rate-limited by SupplyControl.** A sudden `LimitConfigUpdated` or `SupplyControllerAdded` for an unknown address is a high-signal supply event.
8. **Admin actions go through a 1-day timelock.** Watch the timelock (`CallScheduled` etc.) for advance notice of upgrades, facet swaps and role grants. `DefaultAdminTransferScheduled` gives at least 3 h notice of an admin change.
9. **Rewards do not change balances on transfer.** USDG rewards accrue off-balance per payout group and are paid by `claimAll*` as normal transfers from the claim source. `balanceOf` does not rebase.
10. **Decoys:** the Ethereum literal on Arbitrum is "Flux USD". The same literal on Polygon is a PYUSD-related contract. Always key on `(chainId, address)`.
11. **Decimals are 6** on all three chains.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_TRANSFER                       = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_SUPPLY_INCREASED               = '\xf5c174d57843e57fea3c649fdde37f015ef08750759cbee88060390566a98797'
TOPIC_SUPPLY_DECREASED               = '\x1b7e18241beced0d7f41fbab1ea8ed468732edbcb74ec4420151654ca71c8a63'
TOPIC_SUPPLY_CONTROL_SET             = '\x487be0c63489145f3de4a36cd994bf4e0d32c7b76278d82639aef690a9ba6481'
TOPIC_PAUSE                          = '\x6985a02210a168e66602d3235cb6db0e70f92b3ba4d376a33c0f3d9434bff625'
TOPIC_UNPAUSE                        = '\x7805862f689e2f13df9f062ff482ad3ad112aca9e0847911ed832e158c525b33'
TOPIC_FREEZE_ADDRESS                 = '\x1aa660498c83ea285bc55e4cfc00afcaa7120798db87b74f3c0d7c6e001bc392'
TOPIC_UNFREEZE_ADDRESS               = '\x150465b020dfc06a59269da94ed66db9b65a516cf4fdd5f583b0f12752339bbe'
TOPIC_FROZEN_ADDRESS_WIPED           = '\xfc5960f1c5a5d2b60f031bf534af053b1bf7d9881989afaeb8b1d164db23aede'
TOPIC_REWARDS_FROZEN                 = '\xa0617f7f8c7f456232c25e291a9fa28d43b790b6e0886ac5cd080c3ac2736d54'
TOPIC_FACET_UPDATE                   = '\x59277b34e7bfaca5e93a39d132e8eccf6712605952797722701ea2ae717a914a'
TOPIC_UPGRADED                       = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ROLE_GRANTED                   = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED                   = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
TOPIC_DEFAULT_ADMIN_XFER_SCHEDULED   = '\x3377dc44241e779dd06afab5b788a35ca5f3b778836e2990bdb26a2a4b2e5ed6'
TOPIC_AUTHORIZATION_USED             = '\x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5'
TOPIC_CLAIM_SOURCE_SET               = '\x250cda044478c56f29aad456e3429c3d9cf4897706176ac1e2c23a1156ada1c2'
TOPIC_MULTIPLIER_RATE_SCHEDULED      = '\xd45ec4c8b98127d638b26172724c6ebf59d086e75aaa364a517c7cff2a1b148b'
TOPIC_ACCOUNT_REGISTERED             = '\x571ca763815c57afa7bc42f0d72b44ea462729b9e7b88c00c851699f582cf1df'
TOPIC_CLAIM_ALL_EXECUTED             = '\x7ee8ddc3497143e7ee6f1bd1775764431bdab617a0b1ac428f7dc57aefef0b8f'
TOPIC_REWARDS_CLAIMED                = '\x816f875a24baac452f66d9227daaed861604a07d92afb48b4cc5ff47f91f7cdd'
TOPIC_SUPPLY_CONTROLLER_ADDED        = '\xcf08d9c60bf75a87f915d1f62a8e5b60875469e6028860b969cf17bbdadb3c26'
TOPIC_SUPPLY_CONTROLLER_REMOVED      = '\xbef3e51271d83375b825aac948002d0e0f566ec012b8939ddec68201ce6f00f6'
TOPIC_LIMIT_CONFIG_UPDATED           = '\x2a92a9859049106ef4ecbc9a8259d8514994cbe533fab8d7b64020fd2037eb10'
TOPIC_ALLOW_ANY_MINT_BURN_UPDATED    = '\x655668ebb9d503c12fddfb0f06df9b5d5cdc79b7ac8d0adb23b066f7d11a27c0'
TOPIC_MINT_ADDR_WHITELISTED          = '\xf03ae459ca1082dbfa96d80d1ca78e7dea8d82cc8b51ee915544cd48a60bbaa0'
TOPIC_OFT_SENT                       = '\x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a'
TOPIC_OFT_RECEIVED                   = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
-- ===== Role hashes =====
ROLE_PAUSE                           = '\x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d'
ROLE_ASSET_PROTECTION                = '\xe3e4f9d7569515307c0cdec302af069a93c9e33f325269bac70e6e22465a9796'
ROLE_SUPPLY_CONTROLLER               = '\x9c00d6f280439b1dfa4da90321e0a3f3c2e87280f4d07fea9fa43ff2cf02df2b'
ROLE_SUPPLY_CONTROLLER_MANAGER       = '\x5d3e9f1ecbcdad7b0da30e7d29c9eddaef83a4502dafe3d2dd85cfdb12e4af10'
-- ===== Selectors (chain-agnostic) =====
SEL_INCREASE_SUPPLY_TO_ADDRESS       = '\x076bdc36'
SEL_DECREASE_SUPPLY_FROM_ADDRESS     = '\x1f17c083'
SEL_MINT                             = '\x40c10f19'
SEL_BURN                             = '\x42966c68'
SEL_PAUSE                            = '\x8456cb59'
SEL_UNPAUSE                          = '\x3f4ba83a'
SEL_FREEZE                           = '\x8d1fdf2f'
SEL_FREEZE_BATCH                     = '\x4cfd7a57'
SEL_UNFREEZE                         = '\x45c8b1a6'
SEL_WIPE_FROZEN_ADDRESS              = '\xe2f72f03'
SEL_SET_SUPPLY_CONTROL               = '\x52e5a050'
SEL_SET_FACET                        = '\x3dc23d0c'
SEL_BATCH_SET_FACET                  = '\x4b2422da'
SEL_UPGRADE_TO                       = '\x3659cfe6'
SEL_UPGRADE_TO_AND_CALL              = '\x4f1ef286'
SEL_TRANSFER_WITH_AUTHORIZATION      = '\xe3ee160e'
SEL_CLAIM_ALL                        = '\x72da5bcb'
SEL_ADD_SUPPLY_CONTROLLER            = '\x49005a32'
SEL_UPDATE_LIMIT_CONFIG              = '\x19d39126'
-- ===== Addresses (network-specific) =====
ETH_USDG                             = '\xe343167631d89b6ffc58b88d6b7fb0228795491d'
ETH_USDG_SUPPLY_CONTROL              = '\x9a7164112029b81c07636ab7b59fa813e0883bbf'
ETH_USDG_OFT_WRAPPER                 = '\x147bde4f997f0d4c7544ed0c55eacf1e5e6bf9c4'
ETH_USDG_TIMELOCK                    = '\x9036566eaa5f83e0b9e1161c6c602b0adf997654'
ARB_USDG                             = '\x004b506865409877c9fa29bfb1eba929984b9bbc'
ARB_USDG_SUPPLY_CONTROL              = '\x359a1ee087abd3042151b93ec8ea462d6b27bcb6'
ARB_USDG_OFT_WRAPPER                 = '\xc3274ec3f772d8534575eaad5231cf250a48b6b6'
ARB_USDG_TIMELOCK                    = '\x6c9e821ade9efc1bcda763f9942dd7822d6e86b4'
RH_USDG                              = '\x5fc5360d0400a0fd4f2af552add042d716f1d168'
RH_USDG_SUPPLY_CONTROL               = '\xdf5fff9cb88b3cab50572fae73e2eb08599d25d4'
RH_USDG_OFT_WRAPPER                  = '\x0d54755f5106bfdb43f7a35f5d49a23f940628d1'
RH_USDG_TIMELOCK                     = '\xcfa0388f5ddf905fdc08c45c716c15dc10a14c6f'
```

---

## 11. Verification & sources

How constants in this doc were verified (2026-10-30):

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `paxosglobal/paxos-token-contracts` (`PaxosTokenClaimableRewards.sol`, `TokenAdminEvents.sol`, `ClaimableRewardsEvents.sol`, `SupplyControl.sol`, `facets/*.sol`, `lib/Roles.sol`). The Robinhood Chain USDG impl ABI on Sourcify matches the same event set. Live `eth_getLogs` confirmed `SupplyIncreased`, `SupplyDecreased`, `FreezeAddress`, `AuthorizationUsed`, `AccountRegistered` and `ClaimAllExecuted` on the Ethereum token (blocks 26 301 337–26 306 337), `SupplyIncreased` / `SupplyDecreased` on the Arbitrum token, and `OFTSent` / `OFTReceived` on the Ethereum OFTWrapper. On Robinhood Chain the full admin history (blocks 0–101.8 M) was back-filled: `RoleGranted`, `FacetUpdate`, `FreezeAddress`, `Upgraded`, `SupplyControlSet` and `SupplyControllerAdded` all occur. Role hashes match the constants in `lib/Roles.sol` and `SupplyControl.sol`.
- **Addresses:** taken from the Paxos docs "USDG on Main Networks" page and existence-checked with `eth_getCode` on all nine chains. `supplyControl()`, `token()`, `defaultAdmin()`, `getAllSupplyControllerAddresses()`, `getMinDelay()`, `defaultAdminDelay()` and `getFacet(bytes4)` were read live.
- **Proxies:** EIP-1967 impl and admin slots read live. All token and SupplyControl proxies have the impl slot set and the admin slot empty (UUPS).
- **Chain coverage:** every literal returns `0x` on Base, BNB, Avalanche, Optimism and Arc. The Ethereum literal on Arbitrum and Polygon holds unrelated contracts (§4, §6).

Authoritative sources:
- [paxosglobal/paxos-token-contracts](https://github.com/paxosglobal/paxos-token-contracts) — token, facets, SupplyControl, roles.
- [paxosglobal/usdg-contract](https://github.com/paxosglobal/usdg-contract) · [paxosglobal/cross-chain-contracts](https://github.com/paxosglobal/cross-chain-contracts) (OFTWrapper).
- [Paxos docs — USDG on Main Networks](https://docs.paxos.com/stablecoin/usdg/mainnet).
- Sourcify: `https://sourcify.dev/server/v2/contract/4663/0x68184c449e1a8f34fa18d289737129fd27b66f8f`.
- Explorers: [Etherscan](https://etherscan.io/token/0xe343167631d89B6Ffc58B88d6b7fB0228795491D) · [Arbiscan](https://arbiscan.io/token/0x004B506865409877C9fA29bfb1ebA929984B9bbC) · [Robinhood Chain Blockscout](https://robinhoodchain.blockscout.com/token/0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168).
