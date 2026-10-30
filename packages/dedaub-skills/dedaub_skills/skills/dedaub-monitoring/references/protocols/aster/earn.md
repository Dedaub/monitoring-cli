# Aster Earn & USDF — Topics, Selectors, Addresses (BNB Smart Chain)

**Status:** verified on 2026-10-30 against live BNB RPC, `eth_getCode` on all nine target chains, the Sourcify-verified sources of every contract listed here, and the official Aster "Smart Contracts", "How USDF Works" and "Fund Custody & Risk Management" pages.
**Scope:** the Aster yield products on BNB Smart Chain (56): the **USDF** stablecoin and its minter `USDFEarn`, staked **asUSDF** and `asUSDFEarn`, the **asBNB** liquid-staking token and `AsBnbMinter`, **asBTC** and its `Earn` minter, **asCAKE** and its `Minter`, and the `WithdrawVault` payout contracts. Topics and selectors are chain-agnostic. Addresses are BNB-only: none of these contracts exist on the other eight target chains (§5).

**USDF is custodial.** A user calls `USDFEarn.deposit(usdtAmount)`. The contract mints USDF 1:1 (less commission) and sends the USDT to a **Ceffu** custody address (`TransferToCeffu`). Ceffu mirrors the funds to Binance for a delta-neutral strategy. Redemption is a two-step queue: `requestWithdraw` → an operator funds a `WithdrawVault` and calls `distributeWithdraw` → the user calls `claimWithdraw`. asUSDF is the staked USDF share; its `exchangePrice()` rises when a `REWARD_ROLE` holder calls `dispatchReward` (1.0699 on 2026-10-30). asBTC uses the same pattern with BTCB through the generic `Earn` contract.

**asBNB is different.** `AsBnbMinter` takes **slisBNB** (Lista) or BNB and mints asBNB at a rate of `totalTokens / asBNB supply`. Rewards compound through a `YieldProxy` (Lista veLISTA / Binance Launchpool rewards). Burns pay slisBNB directly.

Supplies on 2026-10-30: USDF 112.44M (max 500M), asUSDF 5.54M, asBNB 79,658 (backed by 81,849 slisBNB), asCAKE 40,932, asBTC 0.27.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Upgrade / admin |
|----------|------|--------|-----------------|
| **USDF** | LayerZero OFT ERC-20, 18 dp. `mint`/`burn` by `MINTER_AND_BURN_ROLE` (= `USDFEarn`). No LZ peers set on the target chains. | No (18,701 B) | `owner()` and `DEFAULT_ADMIN_ROLE` = Timelock `0xe829…1861` |
| **USDFEarn** | USDT → USDF mint, redemption queue, Ceffu transfer, asUSDF zap (`mintAsUSDF`). | UUPS `ERC1967Proxy` | `DEFAULT_ADMIN_ROLE` = Timelock `0xe829…1861`; `ADMIN_ROLE`/`PAUSE_ROLE` = Safe `0xa8c0…1c3f` |
| **WithdrawVault** (USDF / asUSDF) | Holds USDT for queued redemptions; `transfer` / `transferNative` by the Earn contracts. | UUPS `ERC1967Proxy` | — |
| **asUSDF** | Staked USDF share token. Minted by `asUSDFEarn`. | No (6,014 B) | |
| **asUSDFEarn** | USDF → asUSDF, reward vesting, redemption queue. | UUPS `ERC1967Proxy` | `DEFAULT_ADMIN_ROLE` = Timelock `0xe829…1861`; `ADMIN_ROLE` = Safe `0xa8c0…1c3f` |
| **asBTC** | OFT share token for BTCB. | No (18,938 B) | `owner()` = Timelock `0x3aca…6eda` |
| **Earn** (asBTC minter) | Generic `assToken` minter with signed exchange-rate uploads and Ceffu transfer. | UUPS `ERC1967Proxy` | `DEFAULT_ADMIN_ROLE` = Timelock `0x3aca…6eda` |
| **asBNB** | `Ownable2Step` ERC-20; single `minter()` = `AsBnbMinter`. | No (4,940 B) | `owner()` = Timelock `0xfb85…e43b` |
| **AsBnbMinter** | slisBNB/BNB → asBNB; mint queue; burn; reward compounding; OFT adapter hooks. | UUPS `ERC1967Proxy` (163 B) | `DEFAULT_ADMIN_ROLE` = Timelock `0xfb85…e43b` |
| **YieldProxy** | Reward harvesting for asBNB. | UUPS `ERC1967Proxy` | |
| **asCAKE** (`AssToken`) | ERC-20 share of locked CAKE. | UUPS `ERC1967Proxy` (130 B) | `owner()` = Timelock `0xb834…434b` |
| **asCAKE Minter** + **UniversalProxy** | CAKE → asCAKE (`smartMint` swaps on PancakeSwap or locks into veCAKE through the UniversalProxy). | UUPS `ERC1967Proxy` | |

All four timelocks are `Timelock` (OpenZeppelin `TimelockController`) with `getMinDelay()` = 21,600 s (6 h).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

"Live" = seen in `eth_getLogs` on BNB blocks head−200,000…head (2026-10-30).

### 1.1 USDFEarn / asUSDFEarn / Earn (shared redemption-queue topics — disambiguate by emitter)

| topic0 | Event | Emitter / live |
|--------|-------|----------------|
| `0x4366b54e61e348284316fa2721e0ad6845719007c1cea02e35561f46cc517a5b` | `MintUSDF(address indexed sender,address indexed USDT,address indexed USDF,uint256 amountIn,uint256 USDFAmount)` | USDFEarn ✅ (14) |
| `0xd560b537bb03a2e10775ff1c5992f0ba20cf0bdacefb10c30c86fc69e9d6fc82` | `TransferToCeffu(address indexed token,uint256 USDTAmount,address ceffuAddress)` | USDFEarn ✅ (9), Earn — **funds leave the chain to custody** |
| `0x3d049c685010061396ccb788b984289782a932f0fcf3321a0dccde30f43f3cd1` | `RequestWithdraw(address indexed sender,address indexed token,uint256 amount,uint256 requestWithdrawNo,bool emergency)` | USDFEarn ✅ (18), asUSDFEarn ✅ (2), Earn |
| `0x051fd1ff7b2b4fc684c771fea49f105616b277782f1b76f0dfb7aeba85322699` | `DistributeWithdraw(address indexed withdrawToken,address indexed receiveToken,uint256 withdrawAmount,uint256 receiveAmount,uint256 requestWithdrawNo)` | asUSDFEarn ✅ (2), USDFEarn, Earn |
| `0xb143cbc1b45edd3fe39b60a0bb8aafb1e1d42da89e96e1aff4449ebdc37e48f2` | `ClaimWithdraw(address indexed sender,address indexed withdrawToken,address indexed receiveToken,uint256 withdrawAmount,uint256 receiveAmount,uint256 requestWithdrawNo)` | USDFEarn ✅ (4), asUSDFEarn ✅ (2), Earn |
| `0xc161cafde4f1ca20584d73742a7353f00b052c7c0ab7626baec68fbf35ac11be` | `MintasUSDF(address indexed sender,address indexed USDFAddress,address indexed asUSDFAddress,uint256 amountIn,uint256 asUSDFAmount,uint256 exchangePrice)` | asUSDFEarn ✅ (1) |
| `0x788448e32ff4408de40ea93cdb828754d4033100f53ea9b8a04fb45f5cdfca03` | `RewardDispatched(uint256 amount,uint256 startTime,uint256 period)` | asUSDFEarn ✅ (3) |
| `0xdc3f9f32b7ca52cfc67f1424b7cbe4b03f56ef295e7fedea895aec6ae7436ada` | `MintAssXXX(address indexed sender,address indexed sourceTokenAddress,address indexed assTokenAddress,uint256 amountIn,uint256 assXXXAmount,uint256 assToSourceExchangeRate)` | Earn (asBTC) |
| `0x7e8886d8ada06aa154830d9afa9d83014f99e4b16b1578d06bd5802d666c4315` | `UploadExchangeRate(address indexed assTokenAddress,uint256 assToSourceExchangeRate,uint256 exchangeRateExpiredTimestamp)` | Earn — rate oracle |
| `0x52f891905af4a2ab087cfd1309ad3557576bbe561b3dc36afca86aa82ea70ba0` | `UpdateCeffuAddress(address oldCeffuAddress,address newCeffuAddress)` | USDFEarn — **custody address changed** |
| `0xeb78f913240d3d5506b97f49778e167fc54a607569256ca09d974c9a437d79f2` | `UpdateCeffuAddress(address ceffuAddress,bool enable)` | USDFEarn |
| `0xafef0c18004dea071236bb971e116c885cd7e4816842197e0169fba876230848` | `UpdateCeffuAddress(address indexed assTokenAddress,address oldCeffuAddress,address newCeffuAddress)` | Earn |
| `0x6230b1999cd6d4ac7d3cff7b8bc0557c8e52bbdc0e1f096beae8c6a1660b2ee3` | `UpdateUSDFMaxSupply(uint256 oldUSDFMaxSupply,uint256 newUSDFMaxSupply)` | USDFEarn |
| `0xe912795a13342c21b46ca582ea76273fb5d5e221ebe09b49094f8a380e26042c` | `AddEmergencyWithdrawWhitelist(address indexed sender,address indexed user)` | USDFEarn, asUSDFEarn |
| `0xbb4879b588c051d62e1c2d8df192de7452776a5e87bf175cb6e0e79309314e8a` | `UpdateEmergencyWithdrawEnabled(bool oldValue,bool newValue)` | USDFEarn, asUSDFEarn |
| `0x935169502e37bf7086b6a43f94f9b855ee8320b72962953cd0de3aff900f6d75` | `UpdateWithdrawEnabled(bool oldValue,bool newValue)` | USDFEarn, asUSDFEarn — **redemptions toggled** |
| `0x771d7deea9597b8aeb7fc2011871081b6ed3512854a0fe8b45cc77472b3c3c0b` | `UpdateUSDTDepositEnabled(bool oldUSDTDepositEnabled,bool newUSDTDepositEnabled)` | USDFEarn |
| `0x67fb2216d844c3553cf557bffa85f0fde0294999f808e61dcae1773d50d5e150` | `UpdateCommissionRate(uint256 oldCommissionRate,uint256 newCommissionRate)` | USDFEarn |
| `0xdbf34b45b47a653cf4940cccbec765f72d4d63de3237306905bfc0ee28832362` | `AddToken(address indexed,address indexed)` | asUSDFEarn, Earn, AsBnbMinter, asCAKE Minter (same topic0) |

### 1.2 WithdrawVault

| topic0 | Event | Note |
|--------|-------|------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address receipt,address token,uint256 amount)` | **No indexed fields.** Same topic0 as ERC-20 `Transfer` but only 1 topic and 96 bytes of data ✅ (6) |
| `0xaaa330f73f343ed3da9c3ff8366ebc8dc13ab7f7c9edcf6d2a1774a81f717349` | `TransferNative(address receipt,uint256 amount)` | |

### 1.3 AsBnbMinter / asBNB

| topic0 | Event | Live |
|--------|-------|------|
| `0x85997415bd3414b806458681ef3ae6f42455f982932d9fcf6b4519755a7f6e0d` | `AsBnbMinted(address indexed user,uint256 amountIn,uint256 amountOut)` | ✅ (12) |
| `0xaa5365e70e35ac0430a743a2d1ea62eae7e2ded652dca247005ea6a9d9a89ed6` | `AsBnbBurned(address indexed user,uint256 amountToBurn,uint256 releaseTokenAmount)` | ✅ (45) |
| `0x2ef1c913ea52422566670cf24875ff59bd82fd354a5c6656a1090d87a6de3dff` | `TokenMintReqQueued(uint256 indexed index,address indexed user,uint256 amountIn)` | queue |
| `0xdab5d37eed6f043a680b5789c6af5afbb16231fa0d1f54fc087129e0b5eee1d7` | `TokenMintReqProcessed(uint256 indexed index,address indexed user,uint256 amountIn,uint256 amountToMint)` | queue |
| `0xacec20606267f4013e2a5269f8a7e64d82bb5d31dda275d267e55ecaae7b1c58` | `TokenMintReqCancelled(uint256 indexed index,address indexed user,uint256 amountOut)` | queue |
| `0x3f49f3b24a9f74ee36ca0198167b495c188b73e08c7e5754302b97c33bbc8442` | `RewardsCompounded(address indexed sender,uint256 amountIn,uint256 lockAmount,uint256 fee)` | rate increase |
| `0x45abe80e1ccfdfb2be4680ea7a5d3a3a210f24b5e10dc89ea8c4eed1506e6b47` | `CanDepositUpdated(address indexed sender,bool canDeposit)` | admin |
| `0x9749b84f2ef83e4723b9c02b2957ee738f95576e915e0d99c1ff9991729c08fb` | `CanWithdrawUpdated(address indexed sender,bool canWithdraw)` | **burns toggled** |
| `0x00ed5939179dc194223f0edd1517ecee2210b22da7f82c8e4b1795e93b9f06aa` | `FeeWithdrawn(address indexed sender,address recipient,uint256 amount)` | AsBnbMinter, asCAKE Minter |
| `0xcec52196e972044edde8689a1b608e459c5946b7f3e5c8cd3d6d8e126d422e1c` | `SetMinter(address indexed _address)` | asBNB, asCAKE — **minter swapped** |
| `0x5b1d826fd7e7f12fa45125328dfff125c797345f1d4ab6e733d233eeb6285e7d` | `AsBnbOFTAdapterUpdated(uint32 indexed eid,address adapter)` | none set on target eids |

### 1.4 asCAKE Minter

| topic0 | Event |
|--------|-------|
| `0x9830f2cadccec20a9d5cc02bc357bbfb8f527bde15dda72202883704bac7ccb7` | `SmartMinted(address indexed user,uint256 cakeInput,uint256 obtainedAssCake)` |
| `0xe1e70db006000f1913537da7c12f017b7ed0396160d11b49a2b48fb7087c5da2` | `RewardsCompounded(address indexed sender,uint256 compoundAmount,uint256 fee)` |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | `Withdraw(address indexed sender,uint256 amount)` |

### 1.5 USDF / asBTC token (OFT)

Standard `Transfer` (`0xddf252ad…`, mint = from `0x0`) plus LayerZero `OFTSent` `0x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a`, `OFTReceived` `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c`, `PeerSet` `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` and `TransferLimitChanged` `0xc936000a38158a6358900260524fb98fda54e21b1fb66f53d6eae161af6a8e1a`. All Earn contracts also emit `Upgraded`, `Paused`, `Unpaused`, `RoleGranted` and `RoleRevoked` (topics in `bridge.md` §1.1).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

| Selector | Signature | Contract / notes |
|----------|-----------|------------------|
| `0xb6b55f25` | `deposit(uint256)` | USDFEarn (USDT in → USDF), asUSDFEarn (USDF in → asUSDF). |
| `0x48c32e3c` | `mintAsUSDF(uint256)` | USDFEarn; USDT → USDF → asUSDF. |
| `0x745400c9` | `requestWithdraw(uint256)` | USDFEarn, asUSDFEarn. |
| `0x4660a19d` | `requestEmergencyWithdraw(uint256)` | whitelisted users only. |
| `0x3a9b0a74` | `distributeWithdraw((address,uint256,address)[])` | `BOT_ROLE`; marks requests claimable. |
| `0xeb9259ef` | `claimWithdraw(uint256[])` | user; pays from `WITHDRAW_VAULT`. |
| `0xbab3a707` / `0x46891db7` | `transferToCeffu()` / `transferToCeffu(address,uint256)` | USDFEarn; `BOT_ROLE`. |
| `0x03191983` | `updateCeffuAddress(address)` | USDFEarn admin. |
| `0xc944496f` | `updateUSDFMaxSupply(uint256)` | USDFEarn admin. |
| `0x195ac6db` | `dispatchReward(uint256)` | asUSDFEarn `REWARD_ROLE`; raises `exchangePrice()` (`0x9e65741e`). |
| `0x47e7ef24` / `0xdb6b5246` | `deposit(address,uint256)` / `depositNative()` | Earn (asBTC). |
| `0x397a1b28` | `requestWithdraw(address,uint256)` | Earn. |
| `0x130e295b` | `uploadExchangeRate(bytes,bytes)` | Earn; signed rate. |
| `0x3c3f1a1a` | `transferToCeffu(address[])` | Earn. |
| `0x40c10f19` / `0x9dc29fac` | `mint(address,uint256)` / `burn(address,uint256)` | USDF, asUSDF, asBTC, asBNB, asCAKE (role- or minter-gated). |
| `0x0eb78661` | `mintAsBnb()` | AsBnbMinter; payable BNB. |
| `0x0d88a1eb` | `mintAsBnb(uint256)` | AsBnbMinter; slisBNB in. |
| `0x7b6751dd` / `0xfe26c5b1` | `mintAsBnbFor(address)` / `mintAsBnbFor(uint256,address)` | AsBnbMinter (used by the vault zap). |
| `0x50f816d8` / `0xaffa88ad` | `mintAsBnbToChain(...)` | AsBnbMinter; mint + OFT send. |
| `0xe03b6dbc` | `burnAsBnb(uint256)` | AsBnbMinter; pays slisBNB. |
| `0x656c579f` | `compoundRewards(uint256)` | AsBnbMinter; `YieldProxy` only. |
| `0xc45d238f` / `0x2b08a8c2` | `processMintQueue(uint256)` / `cancelMintRequests(uint256[])` | AsBnbMinter. |
| `0x2d18a7bb` / `0xc4cfc197` | `toggleCanDeposit()` / `toggleCanWithdraw()` | AsBnbMinter `MANAGER`. |
| `0xfca3b5aa` | `setMinter(address)` | asBNB / asCAKE owner. |
| `0x7d0b901b` | `smartMint(uint256,uint256,uint256)` | asCAKE Minter. |
| `0xbeabacc8` / `0x7d2e90c2` | `transfer(address,address,uint256)` / `transferNative(address,uint256)` | WithdrawVault. |
| `0x7e1c0c09` / `0xfc0c546a` | `totalTokens()` / `token()` | AsBnbMinter views (backing / slisBNB). |

---

## 3. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | One-liner |
|------|---------|-----------|
| **USDF** | `0x5A110fC00474038f6c02E89C707D638602EA44B5` | Official list. Non-proxy OFT. |
| **USDFEarn** (USDF minting) | `0xC271fc70dD9E678ac1AB632f797894fe4BE2C345` | Official "USDF Minting Contract". Impl `0x9be60400d043864a99a8fe1be479c9eb299198c1`. |
| WithdrawVault (USDF/asUSDF) | `0xad4836bbf3671ebd4f2e1f49119c1184655e47ca` | Impl `0x1a63fdbd396465a319b7aea1dd9c0bf0a339bf89`. Held 577k USDT. |
| Ceffu custody (USDFEarn `ceffuAddress()`) | `0xb277db0221a26af14320ab0d06ba991c78aa2d6b` | EOA; also `CEFFU_ROLE`. |
| **asUSDF** | `0x917AF46B3C3c6e1Bb7286B9F59637Fb7C65851Fb` | Official list. |
| **asUSDFEarn** (asUSDF minting) | `0xdB57a53C428a9faFcbFefFB6dd80d0f427543695` | Impl `0x29f30635431426363d130aa163816ead1101662f`. |
| **asBTC** | `0x184b72289c0992BDf96751354680985a7C4825d6` | Official list. 18 dp. |
| **Earn** (asBTC minting) | `0x8a3C77E6c6A488d26CD44F403b95e44675f46e6A` | Impl `0x5da1fd30a0004b2ef566fadb807aae149572adfa`. Own WithdrawVault `0xcb378a8a4afa40ba8c7e80f1b7e993c3c1ad6efb`. |
| **asBNB** | `0x77734e70b6E88b4d82fE632a168EDf6e700912b6` | Official list. |
| **AsBnbMinter** (asBNB minting) | `0x2F31ab8950c50080E77999fa456372f276952fD8` | Impl `0x7f52773065fd350b5a935ce2b293fdb16551a6fc`. |
| YieldProxy (asBNB) | `0xe861dd4b0ab6f3a42943e6ef441c3c611cd1bec2` | Impl `0x1b04834f51574ffdef7511e271c09d4070de1b1a`. |
| slisBNB (underlying, Lista) | `0xb0b84d294e0c75a6abe60171b70edeb2efd14a1b` | External. |
| **asCAKE** | `0x9817F4c9f968a553fF6caEf1a2ef6cF1386F16F7` | Impl `0xa4e080829a95a77d9a7994068d2c6ac5b611f9e2`. |
| **asCAKE Minter** | `0x1A81A28482Edd40ff1689CB3D857c3dAdF11D502` | Impl `0xabefff811361cde18954bad71bc12f4e22ba4627`. |
| UniversalProxy (veCAKE locker) | `0x8E6Ce60cbC6402B8b780AdCfc069A00c177D2B18` | Impl `0x1abdb9b3022cf343697cb38ff2765ccfd3e1c8e1`. |
| Timelock (USDF, USDFEarn, asUSDFEarn) | `0xe829a87f4dfa41b032d8b6feca6c2213d6ee1861` | 6 h. |
| Timelock (asBNB, AsBnbMinter) | `0xfb85485ab3bbc1ef56928f9d714cec4bd3dee43b` | 6 h. |
| Timelock (asBTC, Earn) | `0x3acabb3f66b10dee9643336891f7328387f06eda` | 6 h. |
| Timelock (asCAKE) | `0xb83446f74cad1e9f9a367f9222c0785dd670434b` | `owner()` of asCAKE. |
| Admin Safe (4-of-7) | `0xa8c0c6ee62f5ad95730fe23ccf37d1c1ffaa1c3f` | `ADMIN_ROLE` on USDFEarn, asUSDFEarn, Earn; `PAUSE_ROLE` on USDFEarn. |

USDFEarn roles: `BOT_ROLE` = `0xf68e…fafe`, `0xb4aa…d8ae`, `0xf517…3777`; `CEFFU_ROLE` = `0xb277…2d6b`.

## 4. Proxies

| Contract | Pattern | Upgrade auth |
|----------|---------|--------------|
| USDFEarn, asUSDFEarn, Earn, WithdrawVaults, AsBnbMinter, YieldProxy, asCAKE, asCAKE Minter, UniversalProxy | UUPS `ERC1967Proxy` (855 B / 163 B / 130 B). Impl slot values in §3. | Timelock in §3 via `DEFAULT_ADMIN_ROLE` or `TIMELOCK_ADDRESS`. Watch `Upgraded` (`0xbc7cd75a…`) and the timelock `CallScheduled`. |
| USDF, asUSDF, asBTC, asBNB | not proxies (impl slot empty) | Immutable code; mint authority is a role or `minter()`. Watch `RoleGranted` with `MINTER_AND_BURN_ROLE` = `0x144dc67236c5b8b129f92a31bb5cba2a9c107df2d9bcedef0515ca3f60ecb794`, and `SetMinter`. |

## 5. Other target chains

`eth_getCode` returns `0x` for every address in §3 on Ethereum, Base, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain and Arc. `USDF.peers(eid)` and `asBTC.peers(eid)` return zero for the Ethereum, Arbitrum, Base, Avalanche, Optimism, Polygon and Robinhood eids. `AsBnbMinter.asBnbOFTAdapters(eid)` is zero for the same eids.

## 6. Detection invariants & gotchas

1. **USDF backing is off chain.** USDT leaves through `TransferToCeffu` to `0xb277…2d6b`. On-chain USDF supply is not matched by an on-chain USDT balance. Monitor `MintUSDF` vs `TransferToCeffu` and USDF `totalSupply` vs `USDFMaxSupply()`.
2. **A USDF mint outside `USDFEarn` is an incident.** Only `USDFEarn` holds `MINTER_AND_BURN_ROLE` on 2026-10-30. Alert on any USDF `Transfer` from `0x0` whose transaction does not call `USDFEarn`, and on `RoleGranted` for that role.
3. **WithdrawVault `Transfer` collides with ERC-20 `Transfer`.** It has topic0 `0xddf252ad…` but one topic and three data words `(receipt, token, amount)`. A naive ERC-20 decoder breaks. Filter by emitter and topic count.
4. **Shared topics across the Earn family.** `RequestWithdraw`, `DistributeWithdraw`, `ClaimWithdraw`, `AddToken` and `TransferToCeffu` have the same topic0 on several contracts, with different parameter meaning. Key on emitter.
5. **Redemptions are delayed.** `RequestWithdraw` locks the share. Payment comes later as `ClaimWithdraw` from the WithdrawVault. A spike in `RequestWithdraw` with no `DistributeWithdraw` is the stress signal.
6. **asBNB rate.** `convertToTokens(1e18)` = `totalTokens()` / asBNB supply (about 1.0275 on 2026-10-30). A drop of `totalTokens()` without `AsBnbBurned` is a loss event.
7. **The vault zaps call these contracts.** `AstherusVault.depositUSDF` and `depositAsBNB` on BNB call `USDFEarn` and `AsBnbMinter` in the same transaction. Do not count those mints as separate user flows.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_USDF_MINT_USDF               = '\x4366b54e61e348284316fa2721e0ad6845719007c1cea02e35561f46cc517a5b'
TOPIC_USDF_TRANSFER_TO_CEFFU       = '\xd560b537bb03a2e10775ff1c5992f0ba20cf0bdacefb10c30c86fc69e9d6fc82'
TOPIC_EARN_REQUEST_WITHDRAW        = '\x3d049c685010061396ccb788b984289782a932f0fcf3321a0dccde30f43f3cd1'
TOPIC_EARN_DISTRIBUTE_WITHDRAW     = '\x051fd1ff7b2b4fc684c771fea49f105616b277782f1b76f0dfb7aeba85322699'
TOPIC_EARN_CLAIM_WITHDRAW          = '\xb143cbc1b45edd3fe39b60a0bb8aafb1e1d42da89e96e1aff4449ebdc37e48f2'
TOPIC_ASUSDF_MINT                  = '\xc161cafde4f1ca20584d73742a7353f00b052c7c0ab7626baec68fbf35ac11be'
TOPIC_ASUSDF_REWARD_DISPATCHED     = '\x788448e32ff4408de40ea93cdb828754d4033100f53ea9b8a04fb45f5cdfca03'
TOPIC_EARN_MINT_ASSXXX             = '\xdc3f9f32b7ca52cfc67f1424b7cbe4b03f56ef295e7fedea895aec6ae7436ada'
TOPIC_EARN_UPLOAD_EXCHANGE_RATE    = '\x7e8886d8ada06aa154830d9afa9d83014f99e4b16b1578d06bd5802d666c4315'
TOPIC_USDF_UPDATE_CEFFU_ADDRESS    = '\x52f891905af4a2ab087cfd1309ad3557576bbe561b3dc36afca86aa82ea70ba0'
TOPIC_USDF_UPDATE_MAX_SUPPLY       = '\x6230b1999cd6d4ac7d3cff7b8bc0557c8e52bbdc0e1f096beae8c6a1660b2ee3'
TOPIC_EARN_UPDATE_WITHDRAW_ENABLED = '\x935169502e37bf7086b6a43f94f9b855ee8320b72962953cd0de3aff900f6d75'
TOPIC_ASBNB_MINTED                 = '\x85997415bd3414b806458681ef3ae6f42455f982932d9fcf6b4519755a7f6e0d'
TOPIC_ASBNB_BURNED                 = '\xaa5365e70e35ac0430a743a2d1ea62eae7e2ded652dca247005ea6a9d9a89ed6'
TOPIC_ASBNB_REWARDS_COMPOUNDED     = '\x3f49f3b24a9f74ee36ca0198167b495c188b73e08c7e5754302b97c33bbc8442'
TOPIC_ASBNB_CAN_WITHDRAW_UPDATED   = '\x9749b84f2ef83e4723b9c02b2957ee738f95576e915e0d99c1ff9991729c08fb'
TOPIC_ASS_SET_MINTER               = '\xcec52196e972044edde8689a1b608e459c5946b7f3e5c8cd3d6d8e126d422e1c'
TOPIC_ASCAKE_SMART_MINTED          = '\x9830f2cadccec20a9d5cc02bc357bbfb8f527bde15dda72202883704bac7ccb7'
TOPIC_WITHDRAW_VAULT_TRANSFER_NAT  = '\xaaa330f73f343ed3da9c3ff8366ebc8dc13ab7f7c9edcf6d2a1774a81f717349'
TOPIC_OFT_SENT                     = '\x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a'
TOPIC_OFT_RECEIVED                 = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
ROLE_MINTER_AND_BURN               = '\x144dc67236c5b8b129f92a31bb5cba2a9c107df2d9bcedef0515ca3f60ecb794'
-- ===== Selectors (chain-agnostic) =====
SEL_EARN_DEPOSIT_UINT              = '\xb6b55f25'
SEL_USDF_MINT_AS_USDF              = '\x48c32e3c'
SEL_EARN_REQUEST_WITHDRAW          = '\x745400c9'
SEL_EARN_DISTRIBUTE_WITHDRAW       = '\x3a9b0a74'
SEL_EARN_CLAIM_WITHDRAW            = '\xeb9259ef'
SEL_USDF_TRANSFER_TO_CEFFU         = '\xbab3a707'
SEL_USDF_UPDATE_CEFFU_ADDRESS      = '\x03191983'
SEL_ASUSDF_DISPATCH_REWARD         = '\x195ac6db'
SEL_ASBNB_MINT_NATIVE              = '\x0eb78661'
SEL_ASBNB_MINT                     = '\x0d88a1eb'
SEL_ASBNB_BURN                     = '\xe03b6dbc'
SEL_ASS_SET_MINTER                 = '\xfca3b5aa'
SEL_TOKEN_MINT                     = '\x40c10f19'
-- ===== Addresses (BNB, chain 56) =====
BNB_USDF                           = '\x5a110fc00474038f6c02e89c707d638602ea44b5'
BNB_USDF_EARN                      = '\xc271fc70dd9e678ac1ab632f797894fe4be2c345'
BNB_USDF_WITHDRAW_VAULT            = '\xad4836bbf3671ebd4f2e1f49119c1184655e47ca'
BNB_USDF_CEFFU                     = '\xb277db0221a26af14320ab0d06ba991c78aa2d6b'
BNB_ASUSDF                         = '\x917af46b3c3c6e1bb7286b9f59637fb7c65851fb'
BNB_ASUSDF_EARN                    = '\xdb57a53c428a9fafcbfeffb6dd80d0f427543695'
BNB_ASBTC                          = '\x184b72289c0992bdf96751354680985a7c4825d6'
BNB_ASBTC_EARN                     = '\x8a3c77e6c6a488d26cd44f403b95e44675f46e6a'
BNB_ASBNB                          = '\x77734e70b6e88b4d82fe632a168edf6e700912b6'
BNB_ASBNB_MINTER                   = '\x2f31ab8950c50080e77999fa456372f276952fd8'
BNB_ASBNB_YIELD_PROXY              = '\xe861dd4b0ab6f3a42943e6ef441c3c611cd1bec2'
BNB_ASCAKE                         = '\x9817f4c9f968a553ff6caef1a2ef6cf1386f16f7'
BNB_ASCAKE_MINTER                  = '\x1a81a28482edd40ff1689cb3d857c3dadf11d502'
BNB_ASCAKE_UNIVERSAL_PROXY         = '\x8e6ce60cbc6402b8b780adcfc069a00c177d2b18'
BNB_EARN_TIMELOCK_USDF             = '\xe829a87f4dfa41b032d8b6feca6c2213d6ee1861'
BNB_EARN_TIMELOCK_ASBNB            = '\xfb85485ab3bbc1ef56928f9d714cec4bd3dee43b'
BNB_EARN_TIMELOCK_ASBTC            = '\x3acabb3f66b10dee9643336891f7328387f06eda'
```

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the Sourcify ABIs of every token and implementation in §3. Ten topics were seen in live BNB logs (counts in §1).
- **Addresses:** token and minter addresses are from the official "Smart Contracts" page and the DefiLlama `astherus-asBNB`, `astherus-basis-trading` and `astherus-asbtc` adapters. Support contracts (WithdrawVaults, Ceffu address, YieldProxy, timelocks) were read from on-chain getters. `MINTER_AND_BURN_ROLE` holders were checked with `hasRole`.
- **Chain coverage:** batched `eth_getCode` on all nine target chains and LayerZero `peers(eid)` reads.
- **Not confirmed:** the asBTC mint authority. `Earn` does not hold `MINTER_AND_BURN_ROLE` on asBTC under that role id.

Authoritative sources:
- [Aster docs — Smart Contracts](https://docs.asterdex.com/overview/smart-contracts) · [How USDF Works](https://docs.asterdex.com/usdf-stablecoin/overview/how-usdf-works) · [Fund Custody & Risk Management](https://docs.asterdex.com/usdf-stablecoin/overview/fund-custody-and-risk-management) · [Mint asBNB](https://docs.asterdex.com/earn/overview/mint-asbnb)
- [DefiLlama-Adapters `projects/astherus-asBNB`](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/astherus-asBNB/index.js) · [`projects/astherus-basis-trading`](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/astherus-basis-trading/index.js)
- [Sourcify](https://sourcify.dev/) (BNB verified sources) · [BscScan](https://bscscan.com/address/0x5A110fC00474038f6c02E89C707D638602EA44B5)
