# Paxos PYUSD, USDP, PAXG (+ legacy BUSD) — Topics, Selectors, Addresses (Ethereum, Arbitrum One, Polygon PoS)

**Status:** verified against live RPC on all nine target chains, the `paxosglobal/paxos-token-contracts` and `paxosglobal/pyusd-contract` repos, and the Paxos developer docs on 2026-10-30.
**Scope:** the Paxos tokens that run the shared **`PaxosTokenV2`** build with a separate **`SupplyControl`**: **PYUSD** (Ethereum 1, Arbitrum One 42161, Polygon PoS 137), **USDP** (Ethereum), **PAXG** (Ethereum). **BUSD** (Ethereum) is still on the legacy V1 build and is listed for completeness. USDG has its own file ([usdg.md](usdg.md)). Topics and selectors are chain-agnostic. Addresses are network-specific.

`PaxosTokenV2` is the same code family as USDG but **without** facets and rewards. Pause, freeze, wipe, EIP-2612 and EIP-3009 live in the implementation itself. Supply changes go through `SupplyControl`, as for USDG: a supply controller calls `increaseSupplyToAddress` / `decreaseSupplyFromAddress`, and the token asks `SupplyControl` for a rate-limit and whitelist check. PYUSD cross-chain transfers use a Paxos LayerZero `OFTWrapper` that is a supply controller, so they **burn on the source chain and mint on the destination chain**.

The token proxies on Ethereum and Arbitrum are **old Zeppelin `AdminUpgradeabilityProxy`** contracts. Their implementation and admin live in the **ZeppelinOS slots**, not in the EIP-1967 slots. The Polygon PYUSD proxy uses the EIP-1967 impl slot.

---

## 0. Contract families & versions

| Contract | Build | Chains (of the 9) | Proxy |
|----------|-------|-------------------|-------|
| **PYUSD** (PayPal USD, 6 dec) | `PaxosTokenV2` + `PYUSD.sol` | Ethereum, Arbitrum One, Polygon PoS | ETH/ARB: Zeppelin `AdminUpgradeabilityProxy`. POLY: ERC-1967 proxy |
| **USDP** (Pax Dollar, 18 dec) | `PaxosTokenV2` + `USDP.sol` | Ethereum | Zeppelin `AdminUpgradeabilityProxy` |
| **PAXG** (Paxos Gold, 18 dec) | `PaxosTokenV2` + `PAXG.sol` (V2 upgrade of the 0.4.24 PAXG) | Ethereum | Zeppelin `AdminUpgradeabilityProxy` |
| **BUSD** (18 dec) | Legacy V1 (`archive/PaxosToken.sol` family). `supplyControl()` reverts. | Ethereum | Zeppelin `AdminUpgradeabilityProxy` |
| **SupplyControl** | `SupplyControl.sol` (UUPS) | one per token per chain | ERC-1967 |
| **OFTWrapper** (PYUSD) | `paxosglobal/cross-chain-contracts` | ETH, ARB, POLY | ETH/ARB plain, POLY proxy |

Live proof of the build: `supplyControl()` answers on PYUSD (all three chains), USDP and PAXG. It reverts on BUSD. `getFacet(bytes4)` reverts on all four, so none of them has the USDG facet layer.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Token (`PaxosTokenV2`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | Mint = `from` 0x0. Burn and wipe = `to` 0x0. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | |
| `0xf5c174d57843e57fea3c649fdde37f015ef08750759cbee88060390566a98797` | `SupplyIncreased(address indexed to, uint256 value)` | **Mint.** Live: 14 in 3 000 ETH blocks (PYUSD). |
| `0x1b7e18241beced0d7f41fbab1ea8ed468732edbcb74ec4420151654ca71c8a63` | `SupplyDecreased(address indexed from, uint256 value)` | **Burn.** Live on PYUSD (ETH, ARB) and PAXG. |
| `0x487be0c63489145f3de4a36cd994bf4e0d32c7b76278d82639aef690a9ba6481` | `SupplyControlSet(address supplyControlAddress)` | Not indexed here (address in `data`). |
| `0x6985a02210a168e66602d3235cb6db0e70f92b3ba4d376a33c0f3d9434bff625` | `Pause()` | |
| `0x7805862f689e2f13df9f062ff482ad3ad112aca9e0847911ed832e158c525b33` | `Unpause()` | |
| `0x1aa660498c83ea285bc55e4cfc00afcaa7120798db87b74f3c0d7c6e001bc392` | `FreezeAddress(address indexed addr)` | V2 freeze. Live: 2 in 10 000 ETH blocks (USDP). |
| `0x150465b020dfc06a59269da94ed66db9b65a516cf4fdd5f583b0f12752339bbe` | `UnfreezeAddress(address indexed addr)` | |
| `0xfc5960f1c5a5d2b60f031bf534af053b1bf7d9881989afaeb8b1d164db23aede` | `FrozenAddressWiped(address indexed addr)` | Seizure. Followed by `SupplyDecreased`. Same topic in V1. |
| `0xdfa7b90e12da6c1d36ebcce07fb8616a51f8a0071d1a5f5e03c50617021afa28` | `SanctionedAddressListUpdate(address newSanctionedAddress)` | Declared in V2 source. |
| `0x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5` | `AuthorizationUsed(address indexed authorizer, bytes32 indexed nonce)` | EIP-3009. Live: 46 in 3 000 ETH blocks (PYUSD). |
| `0x1cdd46ff242716cdaa72d159d339a485b3438398348d68f09d7c8c0a59353d81` | `AuthorizationCanceled(address indexed authorizer, bytes32 indexed nonce)` | |
| `0x60e6c600b4dc8176ae4c5a9601882377a03221df165888028ff44d163565af78` | `PermitInvalidated(address indexed owner, uint256 newNonce)` | |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | V2 uses `AccessControlDefaultAdminRules`. |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | |
| `0x3377dc44241e779dd06afab5b788a35ca5f3b778836e2990bdb26a2a4b2e5ed6` | `DefaultAdminTransferScheduled(address indexed newAdmin, uint48 acceptSchedule)` | |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address implementation)` | Emitted by the proxy. Not indexed in the Zeppelin proxy. Same topic0 as the indexed form. |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | Zeppelin proxy admin change. |

### 1.2 Legacy V1 token (BUSD now; PYUSD, USDP, PAXG before their V2 upgrade)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x90811a8edd3b3c17eeaefffc17f639cc69145d41a359c9843994dc2538203690` | `AddressFrozen(address indexed addr)` | V1 freeze. Live on BUSD: 2 in 10 000 ETH blocks. |
| `0xc3776b472ebf54114339eec9e4dc924e7ce307a97f5c1ee72b6d474e6e5e8b7c` | `AddressUnfrozen(address indexed addr)` | |
| `0x40d53b0b666e4424f29d55244e7e171a1dc332acc11d04ed4abd884629d8cc97` | `SupplyControllerSet(address indexed oldSupplyController, address indexed newSupplyController)` | V1 single-minter change. |
| `0xd0c36a0ac0fe0d375386bd568fa2947a2dae7523a0a0cfdab20b7532a105bd1b` | `AssetProtectionRoleSet(address indexed oldAssetProtectionRole, address indexed newAssetProtectionRole)` | |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed oldOwner, address indexed newOwner)` | |
| `0xf4e75b79500ab730f8a026ed3cba6d55331bcb64c9e9f60c548e371356e5e3c0` | `OwnershipTransferProposed(address indexed currentOwner, address indexed proposedOwner)` | |
| `0xf228de527fc1b9843baac03b9a04565473a263375950e63435d4138464386f46` | `FeeCollected(address indexed from, address indexed to, uint256 value)` | PAXG V1 transfer fee. No longer emitted (0 in 3 000 recent ETH blocks). |

`Pause()`, `Unpause()`, `FrozenAddressWiped`, `SupplyIncreased`, `SupplyDecreased`, `Transfer` and `Approval` are the same in V1 and V2. Only the freeze topics change. A freeze monitor must match **both** `FreezeAddress` and `AddressFrozen` for full history.

### 1.3 SupplyControl and OFTWrapper

SupplyControl emits the same events as for USDG: `SupplyControllerAdded` `0xcf08d9c6…3c26`, `SupplyControllerRemoved` `0xbef3e512…00f6`, `LimitConfigUpdated` `0x2a92a985…eb10`, `AllowAnyMintAndBurnAddressUpdated` `0x655668eb…27c0`, `MintAddressAddedToWhitelist` `0xf03ae459…baa0`, `MintAddressRemovedFromWhitelist` `0x2faa07c0…1e5f`, plus `RoleGranted` / `Upgraded`. The OFTWrapper emits `OFTSent` `0x85496b76…e59a` and `OFTReceived` `0xefed6d35…fd9c`. Full values are in [usdg.md §1.4–§1.5](usdg.md).

### 1.4 Role hashes

`PAUSE_ROLE` `0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d`, `ASSET_PROTECTION_ROLE` `0xe3e4f9d7569515307c0cdec302af069a93c9e33f325269bac70e6e22465a9796`, `DEFAULT_ADMIN_ROLE` `0x00…00`. SupplyControl roles are in [usdg.md §1.6](usdg.md).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 `PaxosTokenV2`

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x076bdc36` | `increaseSupplyToAddress(uint256,address)` | Supply controller mint. |
| `0xb921e163` | `increaseSupply(uint256)` | Mint to `msg.sender`. Same selector in V1. |
| `0x40c10f19` | `mint(address,uint256)` | Alias of `increaseSupplyToAddress`. |
| `0x1f17c083` | `decreaseSupplyFromAddress(uint256,address)` | Supply controller burn. |
| `0x98e52f9a` | `decreaseSupply(uint256)` | Same selector in V1. |
| `0x42966c68` | `burn(uint256)` | Alias of `decreaseSupply`. |
| `0x8456cb59` | `pause()` | `PAUSE_ROLE` (V1: owner). |
| `0x3f4ba83a` | `unpause()` | |
| `0x8d1fdf2f` | `freeze(address)` | `ASSET_PROTECTION_ROLE`. Same selector in V1. |
| `0x4cfd7a57` | `freezeBatch(address[])` | V2 only. |
| `0x45c8b1a6` | `unfreeze(address)` | |
| `0xfd89d324` | `unfreezeBatch(address[])` | V2 only. |
| `0xe2f72f03` | `wipeFrozenAddress(address)` | Burns the frozen balance. Same selector in V1. |
| `0xe5839836` | `isFrozen(address)` | view. |
| `0x52e5a050` | `setSupplyControl(address)` | `DEFAULT_ADMIN_ROLE`. |
| `0x4a254dfe` | `supplyControl()` | view. Reverts on V1 (BUSD). |
| `0xfff28137` | `reclaimToken()` | `DEFAULT_ADMIN_ROLE`. |
| `0xba1b7e76` | `transferFromBatch(address[],address[],uint256[])` | |
| `0xd505accf` | `permit(address,address,uint256,uint256,uint8,bytes32,bytes32)` | EIP-2612. |
| `0xe3ee160e` | `transferWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)` | EIP-3009. |
| `0xef55bec6` | `receiveWithAuthorization(address,address,uint256,uint256,uint256,bytes32,uint8,bytes32,bytes32)` | EIP-3009. |
| `0x84ef8ffc` | `defaultAdmin()` | view. Same value as `owner()` `0x8da5cb5b`. |

### 2.2 Legacy V1 (BUSD)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x52875bc3` | `setSupplyController(address)` | Owner. Single minter. |
| `0xe7ba1012` | `supplyController()` | view. |
| `0x8ceed9cb` | `setAssetProtectionRole(address)` | Owner. |

### 2.3 Zeppelin `AdminUpgradeabilityProxy` (ETH/ARB token proxies)

`upgradeTo(address)` `0x3659cfe6`, `upgradeToAndCall(address,bytes)` `0x4f1ef286`, `changeAdmin(address)` `0x8f283970`. Only the proxy admin can call them.

SupplyControl selectors are in [usdg.md §2.4](usdg.md).

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified with `eth_getCode` on `https://ethereum-rpc.publicnode.com` on 2026-10-30. Impl and admin come from the ZeppelinOS slots.

| Role | Address | One-liner |
|------|---------|-----------|
| **PYUSD** | `0x6c3ea9036406852006290770BEdFcAbA0e23A0e8` | 1 506 B proxy. Impl `0x8c35caa5fd5bdc64b6b11344ad57594a3676256a`. Proxy admin `0xc94bcf6e1d8b3558e3b62e743630d50497e3851c`. `totalSupply` 1 872.07 M. |
| PYUSD SupplyControl | `0x31d9bDEa6F104606C954f8FE6ba614F1BD347Ec3` | 708 B ERC-1967. Impl `0xfab5891ed867a1195303251912013b92c4fc3a1d`. |
| PYUSD OFTWrapper | `0xa2C323fE5A74aDffAd2bf3E007E36bb029606444` | Plain contract. A supply controller. |
| **USDP** | `0x8E870D67F660D95d5be530380D0eC0bd388289E1` | 1 506 B proxy. Impl `0xf459ff5ec7d1f371cb34754bda5fe5fce2c9054d`. Admin `0xc94bcf6e…`. `totalSupply` 20.80 M. |
| USDP SupplyControl | `0xDc55B5F0f2d441C1116DcC3b9D56314Da7f5496D` | 708 B ERC-1967. Impl `0xc896c7777f85cf8edf9dcb2ee40274b7307da488`. |
| **PAXG** | `0x45804880De22913dAFE09f4980848ECE6EcbAf78` | 1 506 B proxy. Impl `0x7da4c5d9eca180a03765a6d27196f2a0380fa543`. Admin `0x4a515afe11581fd87ba90d6459dc93db6591f5e3`. `owner()` `0x6d8b8f7ebd9860e80694665f05033df06ddc3acc`. `totalSupply` 442 892.74 PAXG. |
| PAXG SupplyControl | `0xbe62db8ed4838e10e1318593ac9e3eb9ccfb2dc7` | 170 B ERC-1967. Impl `0xbb9f637fae6972ea9adeb2ac717c16590cec33e3`. Read from `PAXG.supplyControl()`. |
| **BUSD** (legacy V1) | `0x4Fabb145d64652a948d72533023f6E7A623C7C53` | 1 506 B proxy. Impl `0x2a3f1a37c04f82aa274f5353834b2d002db91015`. Admin `0xc94bcf6e…`. `totalSupply` 34.42 M. Redemption-only. |

`owner()` / `defaultAdmin()` of PYUSD, USDP, BUSD and the PYUSD/USDP SupplyControls is `0x3af3e85f4f97de7ad0f000b724fb77fe5ffc024b` (no code).

Supply controllers: PYUSD `0xa2c323fe…` (OFTWrapper), `0x2fb074fa59c9294c71246825c1c9a0c7782d41a4`, `0xf845a0a05cbd91ac15c3e59d126de5dfbc2aabb7`, `0x835e20da02d830d6074ca2341e2928f438121691`, `0x40d16a860e295fb4e096cdb5e99c32721194add4`. USDP `0x2fb074fa…`, `0xf845a0a0…`. PAXG `0xf845a0a0…`, `0x2fb074fa…`, `0xd09ede557ef195983c9544a5724046fbd6e8a3c6` (708 B proxy), `0x40d16a86…`.

## 4. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **PYUSD** | `0x46850aD61C2B7d64d08c9C754F45254596696984` | 2 050 B Zeppelin proxy. Impl `0x9ce23fc2c05034a878411ebbf926664670f1c831`. Admin `0xc94bcf6e…` (same literal as ETH). `totalSupply` 314.09 M. Native issuance. |
| PYUSD SupplyControl | `0x19eD5C631EDD34AC776368C377A855C42bc1876A` | 708 B ERC-1967. Impl `0xb071515976bcfc69ca1f57babbb8f974b2c6867e`. `owner()` `0xc94bcf6e…`. |
| PYUSD OFTWrapper | `0xFaB5891ED867a1195303251912013b92c4fc3a1D` | 12 678 B plain contract. A supply controller. |

Supply controllers: `0x2fb074fa…`, `0xf845a0a0…`, `0xfab5891e…` (OFTWrapper), `0x835e20da…`.

## 5. Addresses — Polygon PoS (chain ID 137)

| Role | Address | One-liner |
|------|---------|-----------|
| **PYUSD** | `0x99aF3EeA856556646C98c8B9b2548Fe815240750` | 855 B ERC-1967 proxy. Impl `0xd5d13b5b6c2caac5e8ea1485cec6f690dbfab69b`. `totalSupply` 10.43 M. |
| PYUSD SupplyControl | `0x6F607843520585A9acED70e262a36f49b398a8C8` | 855 B ERC-1967. Impl `0xc4e7ab65ca49c8637710ccda1ae47b2d8721fada`. |
| PYUSD OFTWrapper | `0x2292E82E7a53B1d055A64e4bdeC4e9f91318D377` | 708 B ERC-1967 proxy. A supply controller. |

Supply controllers: `0x2fb074fa…`, `0x2292e82e…` (OFTWrapper), `0xf845a0a0…`.

## 6. Chains with no Paxos V2 token

Every address above returns `0x` on **Base, BNB, Avalanche, Optimism, Robinhood Chain and Arc**. USDP, PAXG and BUSD are Ethereum-only of the nine. The Paxos docs list PYUSD also on Solana, Stellar, Stable and X Layer (outside the targets). "PYUSD0" tokens on other chains are LayerZero-issued representations, not Paxos `PaxosTokenV2` contracts, and are not covered here.

---

## 7. Cross-chain summary

| Chain | ID | PYUSD | USDP | PAXG | BUSD |
|-------|----|-------|------|------|------|
| Ethereum | 1 | `0x6c3e…A0e8` | `0x8E87…89E1` | `0x4580…Af78` | `0x4Fab…7C53` (V1) |
| Arbitrum One | 42161 | `0x4685…6984` | — | — | — |
| Polygon PoS | 137 | `0x99aF…0750` | — | — | — |
| Base · BNB · Avalanche · Optimism · Robinhood · Arc | — | — | — | — | — |

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| PYUSD (ETH, ARB), USDP, PAXG, BUSD | Zeppelin `AdminUpgradeabilityProxy` | Impl at `0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3`, admin at `0x10d6a54a4754c8869d6886b5f5d7fbfa5b4522237ea5c60d11bc4e7a1ff9390b`. EIP-1967 slots are empty. | Proxy admin `0xc94bcf6e…` (PAXG: `0x4a515afe…`). |
| PYUSD (POLY) | ERC-1967 proxy | EIP-1967 impl slot set, admin slot empty. | Token admin. |
| SupplyControl (all) | UUPS (ERC-1967) | Impl slot set, admin slot empty. | `DEFAULT_ADMIN_ROLE`. |

The ZeppelinOS slot readings on 2026-10-30 are the impl values in §3–§4. Watch `Upgraded` `0xbc7cd75a…2d3b` and `AdminChanged` `0x7e644d79…798f` on each token proxy.

---

## 9. Detection invariants & gotchas

1. **Read the ZeppelinOS slots, not EIP-1967,** for PYUSD (ETH, ARB), USDP, PAXG and BUSD. The EIP-1967 slots return 0 and look like "not a proxy".
2. **Freeze has two topic0s over time.** V2 emits `FreezeAddress` `0x1aa66049…`. V1 (BUSD today; the other tokens before their upgrade) emits `AddressFrozen` `0x90811a8e…`. Match both.
3. **`SupplyControlSet` is not indexed** in `PaxosTokenV2`. In USDG V3 it is indexed. Same topic0.
4. **Mint and burn emit two events each** (`SupplyIncreased` + `Transfer`, `SupplyDecreased` + `Transfer`). A wipe emits `FrozenAddressWiped` + `SupplyDecreased` + `Transfer`.
5. **PYUSD bridging burns and mints.** The OFTWrapper is a supply controller on each of the three chains. There is no lockbox.
6. **The same supply controller EOAs** (`0xf845a0a0…`, `0x2fb074fa…`, `0x835e20da…`) serve PYUSD, USDP, PAXG and USDG.
7. **PAXG is 18 decimals and gold-denominated.** The V1 fee (`FeeCollected`) no longer fires after the V2 upgrade.
8. **BUSD is redemption-only.** Expect burns, freezes and wipes, not mints.
9. **Address reuse across chains.** `0xfab5891e…` is the PYUSD SupplyControl impl on Ethereum and the PYUSD OFTWrapper on Arbitrum. `0xc94bcf6e…` is the proxy admin on Ethereum and Arbitrum. Always key on `(chainId, address)`.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_TRANSFER                   = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_SUPPLY_INCREASED           = '\xf5c174d57843e57fea3c649fdde37f015ef08750759cbee88060390566a98797'
TOPIC_SUPPLY_DECREASED           = '\x1b7e18241beced0d7f41fbab1ea8ed468732edbcb74ec4420151654ca71c8a63'
TOPIC_SUPPLY_CONTROL_SET         = '\x487be0c63489145f3de4a36cd994bf4e0d32c7b76278d82639aef690a9ba6481'
TOPIC_PAUSE                      = '\x6985a02210a168e66602d3235cb6db0e70f92b3ba4d376a33c0f3d9434bff625'
TOPIC_UNPAUSE                    = '\x7805862f689e2f13df9f062ff482ad3ad112aca9e0847911ed832e158c525b33'
TOPIC_FREEZE_ADDRESS             = '\x1aa660498c83ea285bc55e4cfc00afcaa7120798db87b74f3c0d7c6e001bc392'
TOPIC_UNFREEZE_ADDRESS           = '\x150465b020dfc06a59269da94ed66db9b65a516cf4fdd5f583b0f12752339bbe'
TOPIC_FROZEN_ADDRESS_WIPED       = '\xfc5960f1c5a5d2b60f031bf534af053b1bf7d9881989afaeb8b1d164db23aede'
TOPIC_AUTHORIZATION_USED         = '\x98de503528ee59b575ef0c0a2576a82497bfc029a5685b209e9ec333479b10a5'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED              = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_V1_ADDRESS_FROZEN          = '\x90811a8edd3b3c17eeaefffc17f639cc69145d41a359c9843994dc2538203690'
TOPIC_V1_ADDRESS_UNFROZEN        = '\xc3776b472ebf54114339eec9e4dc924e7ce307a97f5c1ee72b6d474e6e5e8b7c'
TOPIC_V1_SUPPLY_CONTROLLER_SET   = '\x40d53b0b666e4424f29d55244e7e171a1dc332acc11d04ed4abd884629d8cc97'
TOPIC_V1_FEE_COLLECTED           = '\xf228de527fc1b9843baac03b9a04565473a263375950e63435d4138464386f46'
-- ===== Selectors (chain-agnostic) =====
SEL_INCREASE_SUPPLY_TO_ADDRESS   = '\x076bdc36'
SEL_DECREASE_SUPPLY_FROM_ADDRESS = '\x1f17c083'
SEL_FREEZE                       = '\x8d1fdf2f'
SEL_UNFREEZE                     = '\x45c8b1a6'
SEL_WIPE_FROZEN_ADDRESS          = '\xe2f72f03'
SEL_PAUSE                        = '\x8456cb59'
SEL_SET_SUPPLY_CONTROL           = '\x52e5a050'
SEL_UPGRADE_TO                   = '\x3659cfe6'
SEL_UPGRADE_TO_AND_CALL          = '\x4f1ef286'
-- ===== Addresses (network-specific) =====
ETH_PYUSD                        = '\x6c3ea9036406852006290770bedfcaba0e23a0e8'
ETH_PYUSD_SUPPLY_CONTROL         = '\x31d9bdea6f104606c954f8fe6ba614f1bd347ec3'
ETH_PYUSD_OFT_WRAPPER            = '\xa2c323fe5a74adffad2bf3e007e36bb029606444'
ETH_USDP                         = '\x8e870d67f660d95d5be530380d0ec0bd388289e1'
ETH_USDP_SUPPLY_CONTROL          = '\xdc55b5f0f2d441c1116dcc3b9d56314da7f5496d'
ETH_PAXG                         = '\x45804880de22913dafe09f4980848ece6ecbaf78'
ETH_PAXG_SUPPLY_CONTROL          = '\xbe62db8ed4838e10e1318593ac9e3eb9ccfb2dc7'
ETH_BUSD                         = '\x4fabb145d64652a948d72533023f6e7a623c7c53'
ETH_PAXOS_PROXY_ADMIN            = '\xc94bcf6e1d8b3558e3b62e743630d50497e3851c'
ARB_PYUSD                        = '\x46850ad61c2b7d64d08c9c754f45254596696984'
ARB_PYUSD_SUPPLY_CONTROL         = '\x19ed5c631edd34ac776368c377a855c42bc1876a'
ARB_PYUSD_OFT_WRAPPER            = '\xfab5891ed867a1195303251912013b92c4fc3a1d'
POLY_PYUSD                       = '\x99af3eea856556646c98c8b9b2548fe815240750'
POLY_PYUSD_SUPPLY_CONTROL        = '\x6f607843520585a9aced70e262a36f49b398a8c8'
POLY_PYUSD_OFT_WRAPPER           = '\x2292e82e7a53b1d055a64e4bdec4e9f91318d377'
```

---

## 11. Verification & sources

How constants in this doc were verified (2026-10-30):

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `paxosglobal/paxos-token-contracts` (`PaxosTokenV2.sol`, `SupplyControl.sol`, `archive/PaxosToken.sol`, `archive/PAXGImplementation.sol`). Live `eth_getLogs` confirmed `SupplyIncreased`, `SupplyDecreased` and `AuthorizationUsed` on Ethereum PYUSD, `SupplyDecreased` on Arbitrum PYUSD and PAXG, `FreezeAddress` on USDP, and V1 `AddressFrozen` on BUSD. Polygon PYUSD had no logs in a 20 000-block window.
- **Addresses:** taken from the Paxos docs PYUSD and USDP mainnet pages and existence-checked with `eth_getCode` on all nine chains. PAXG SupplyControl was read from `PAXG.supplyControl()`. OFTWrappers were read from each `getAllSupplyControllerAddresses()` and cross-checked with the LayerZero OFT registry.
- **Proxies:** ZeppelinOS and EIP-1967 slots read live with `eth_getStorageAt`.
- **Chain coverage:** every literal returns `0x` on Base, BNB, Avalanche, Optimism, Robinhood Chain and Arc.

Authoritative sources:
- [paxosglobal/paxos-token-contracts](https://github.com/paxosglobal/paxos-token-contracts) (incl. `docs/PAXG_V2_UPGRADE.md`) · [paxosglobal/pyusd-contract](https://github.com/paxosglobal/pyusd-contract) · [paxosglobal/busd-contract](https://github.com/paxosglobal/busd-contract).
- [Paxos docs — PYUSD on Main Networks](https://docs.paxos.com/guides/stablecoin/pyusd/mainnet) · [USDP on Main Networks](https://docs.paxos.com/guides/stablecoin/usdp/mainnet).
- Explorers: [Etherscan PYUSD](https://etherscan.io/token/0x6c3ea9036406852006290770BEdFcAbA0e23A0e8) · [Arbiscan PYUSD](https://arbiscan.io/token/0x46850aD61C2B7d64d08c9C754F45254596696984) · [Polygonscan PYUSD](https://polygonscan.com/token/0x99aF3EeA856556646C98c8B9b2548Fe815240750).
