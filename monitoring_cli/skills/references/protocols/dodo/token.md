# DODO Token, vDODO Governance & DODO Mine — Topics, Selectors, Addresses (Ethereum, BNB, Polygon, Arbitrum, Avalanche, Optimism, Base)

**Status:** verified against live RPC on all 7 chains and the canonical `DODOEX/contractV2` source (`contracts/DODOToken/*`, `contracts/Factory/Registries/DODOMineV3Registry.sol`, `contracts/SmartRoute/proxies/DODOMineV3Proxy.sol`) on 2026-06-02. Every topic0/selector recomputed locally as `keccak256(canonical signature)`; presence/absence existence-checked via `eth_getCode`; proxy patterns read live from storage slots; sample event topic0s confirmed against live `eth_getLogs`.
**Scope:** the DODO governance-token layer — the **DODO ERC-20** (bridged, different address per chain), **vDODO** membership/governance token (+ `DODOCirculationHelper`, `Governance`), the **DODO Mine** liquidity-mining stack (**DODOMineV3** = `ERC20MineV3` clone template + `DODOMineV3Registry` + `DODOMineV3Proxy`; the older **DODOMineV2** = `ERC20Mine`/`DODOMineV2Factory`), and **DODOIncentive** (trade-mining). Topics + selectors are **chain-agnostic** (computed from the canonical signature); addresses are network-specific. This file does **not** cover the DODO AMM/router/V2-pool layer (DVM/DPP/DSP/CP, proxies, approve) — that is a separate reference.

DODO is a **bridged/multichain token with a DIFFERENT address on every chain** and a **different contract implementation per chain**: Ethereum is the canonical immutable 1-billion-supply `DODOToken` (no mint); BNB is an Ownable mint/burn bridge token (`DODOBscToken`); Polygon and Arbitrum are **upgradeable proxy** bridge tokens (Polygon = a Matic PoS `UpgradeabilityProxy`, `proxyType()=2`; Arbitrum = an **EIP-1967 beacon proxy**). vDODO and DODOIncentive exist on **Ethereum + BNB only**. The DODO-Mine registry/proxy/template stack is deployed on **all 7 chains**, but in **two proxy generations**: every chain except Base runs the older `DODOMineV3Proxy` v1 (6-arg `createDODOMineV3`, emits `CreateMineV3(address,address)`); **Base runs the newer v2** (7-arg `createDODOMineV3` with a `platform` field, emits `CreateMineV3(address,address,uint256)`). Individual mining pools are **EIP-1167 minimal-proxy clones** of the `ERC20MineV3`/`ERC20Mine` template, created via the proxy/factory and registered in the registry — discover them from `NewMineV3`/`NewMineV2` events, do not enumerate them. The registry, proxy, templates, vDODO, `DODOCirculationHelper`, `Governance` and `DODOIncentive` are all **plain immutable contracts** — none is an EIP-1967 upgradeable proxy (impl slot reads `0x0` on every chain).

**vDODO event-name gotcha (verified live):** the on-chain events are **`MintVDODO`** and **`RedeemVDODO`** (uppercase `VDODO`), not `MintvDODO`/`RedeemvDODO`. The uppercase `MintVDODO` topic0 `0xb299178f…` (1 870 logs from block 11 891 013) and `RedeemVDODO` topic0 `0x10e8afa8…` were both confirmed live on the Ethereum vDODO contract. The lowercase variants compute to entirely different (wrong) topic0s and will never match.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Chains |
|----------|------|--------|--------|
| **DODO (Ethereum)** `DODOToken` | Canonical ERC-20 gov token, fixed 1 000 000 000 × 10¹⁸ supply, no mint. `Transfer`/`Approval` only. | **No** (immutable, 1 995 B) | ETH |
| **DODO (BNB)** `DODOBscToken` | Ownable mint/burn **bridge** token (BSC-mapped). Adds `Mint`/`Burn`/`Redeem`. | **No** (immutable, 3 773 B) | BNB |
| **DODO (Polygon)** PoS child token | Mintable child behind a **Matic `UpgradeabilityProxy`** (`proxyType()=2`, `proxyOwner()`/`implementation()`/`upgradeTo()`). | **Yes — upgradeable proxy** (custom Matic slot, not EIP-1967) | Polygon |
| **DODO (Arbitrum)** bridge token | ERC-20 behind an **EIP-1967 beacon proxy** (beacon `0xe72b…7333` → impl). | **Yes — beacon proxy** (EIP-1967 beacon slot) | Arbitrum |
| **vDODO** `vDODOToken` | Membership/gov token; stake DODO 1:100 → vDODO; superior-referral staking power; redeem burns + withdraw-fee. | **No** (immutable, 9 904 B ETH / 3 814 B BNB) | ETH, BNB |
| **DODOCirculationHelper** | Computes circulating DODO supply + the vDODO withdraw-fee ratio. | **No** (immutable) | ETH (BNB equiv.) |
| **Governance** | Sums locked vDODO across registered vDODO-mine contracts (`getLockedvDODO`). On ETH the `Governance` slot is `0x0` (unset) in the deploy config. | **No** | (see §gotchas) |
| **DODOMineV3Registry** | Registry of MineV3 pools (`NewMineV3`/`RemoveMineV3`, admin-list). `addMineV3` is admin-only (called by the proxy). | **No** (immutable, 2 844 B everywhere) | all 7 |
| **DODOMineV3Proxy v1** | Create-entry for MineV3 pools — clones template, funds rewards, registers. 6-arg `createDODOMineV3` (no `platform`). | **No** (immutable, 4 177 B) | ETH, BNB, Polygon, Arbitrum, Avalanche, Optimism |
| **DODOMineV3Proxy v2** | Same role, newer ABI: 7-arg `createDODOMineV3` with `platform`; adds `version()`. | **No** (immutable, 4 365 B) | **Base only** |
| **ERC20MineV3** (template) | Single-/multi-reward staking pool; **EIP-1167 clone master**. Pools are 45-B minimal-proxy clones of it. | clone master (immutable) | all 7 |
| **DODOMineV2Factory** | Older mining factory (clones `ERC20Mine`); `NewMineV2`/`RemoveMineV2`; `createDODOMineV2` is owner-only. | **No** (immutable, 3 332 B) | Arbitrum, Optimism, Base |
| **ERC20Mine** (MineV2 template) | Older staking-pool clone master (same `BaseMine` events as V3). | clone master (immutable) | Arbitrum, Optimism, Base |
| **DODOIncentive** | Trade-mining: rewards DODO for swaps routed through `_DODO_PROXY_` (`triggerIncentive`). Now dormant. | **No** (immutable, 3 758 B) | ETH, BNB |

**MineV3 vs MineV2 events are identical** — both `ERC20MineV3` and `ERC20Mine` inherit the same `BaseMine` (`Claim`/`UpdateReward`/`UpdateEndBlock`/`NewRewardToken`/`RemoveRewardToken`/`WithdrawLeftOver`) and add `Deposit`/`Withdraw`. The pools differ only in their factory/registry wiring, not their log signatures.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 DODO ERC-20 token (all chains)

| topic0 | Event | Where |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` | every DODO token (ETH/BNB/Polygon/Arbitrum) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address,address,uint256)` | every DODO token |

### 1.2 DODO (BNB) `DODOBscToken` — extra bridge events

| topic0 | Event |
|--------|-------|
| `0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885` | `Mint(address,uint256)` |
| `0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5` | `Burn(address,uint256)` |
| `0xd12200efa34901b99367694174c3b0d32c99585fdf37c7c26892136ddd0836d9` | `Redeem(address,address,uint256)` (bridge-out: `sender, redeemToEthAccount, value`) |

> Polygon/Arbitrum bridge tokens use their own bridge `Transfer(address(0),…)` mint/burn convention (Matic child / Arbitrum gateway); their canonical ERC-20 topics are the two in §1.1.

### 1.3 vDODO (`vDODOToken`) — ETH + BNB

| topic0 | Event | Meaning |
|--------|-------|---------|
| `0xb299178f92646282937cbe7c9e854594cb5ef6330e03b43946086e9dc0ca9ecd` | `MintVDODO(address user, address superior, uint256 mintDODO)` | DODO staked → vDODO minted. **Confirmed live (ETH).** |
| `0x10e8afa8e2aa45e6f179fcaa8538c699a53e253cda2b304d7fa46174527cedc3` | `RedeemVDODO(address user, uint256 receiveDODO, uint256 burnDODO, uint256 feeDODO)` | vDODO redeemed → DODO (with burn + withdraw fee). **Confirmed live (ETH).** |
| `0x3ed260d8e11a4e325861a1b184d8389e34339a456bc04d53f111e5d99ae22ac1` | `DonateDODO(address user, uint256 donateDODO)` | DODO donated to raise `alpha` (boosts all stakers). |
| `0xdee982458f84113ac3e32d44595820a6fa60cfbe80a1bdd444c26599ee5b7dd5` | `PreDeposit(uint256 dodoAmount)` | Pre-funded block-reward DODO. |
| `0xeca81e4b546cfbc80883349ef5bdaca1c02dc7cb0bdb9e1183cb7698f90bbb85` | `ChangePerReward(uint256 dodoPerBlock)` | Owner changed staking emission rate. |
| `0xff3692e8e3336aaee232986626f21d80be86e891d2122581acf795123af3e8a3` | `UpdateDODOFeeBurnRatio(uint256 dodoFeeBurnRatio)` | Owner changed the burn share of the withdraw fee. |
| `0x8faf67cb6de7f4aed6e2791474b60016b6cb2b4e756529701e7863892e468694` | `SetCantransfer(bool allowed)` | Owner toggled vDODO transferability. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` | vDODO ERC-20 transfer (only when `_CAN_TRANSFER_`). |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address,address,uint256)` | vDODO ERC-20 approval. |

> **Do NOT use** lowercase `MintvDODO` (`0x50b992cc…`) / `RedeemvDODO` (`0xc694aa60…`) — those are wrong signatures and never appear on-chain. The deployed contract emits the **uppercase** `VDODO` forms above (verified live).

### 1.4 Governance (vDODO lock registry)

| topic0 | Event |
|--------|-------|
| `0xa76ac1a4fabc693f63d84fd19178974552a165bad13617158ebd0583d6432f1a` | `AddMineContract(address mineContract)` |
| `0x79ae063e729116d1171752e357397faa6caeb747d9daa2b4479106a54ad84901` | `RemoveMineContract(address mineContract)` |

### 1.5 DODOMineV3 / DODOMineV2 staking pool (`BaseMine`, identical for V3 + V2 clones)

| topic0 | Event |
|--------|-------|
| `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | `Deposit(address indexed user, uint256 amount)` |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | `Withdraw(address indexed user, uint256 amount)` |
| `0x3ed1528b0fdc7c5207c1bf935e34a667e13656b9ed165260c522be0bc544f303` | `Claim(uint256 indexed i, address indexed user, uint256 reward)` |
| `0xbcabeac7f89430597dc942c3264f28fd08010c3b2e19ecf95c6e690f9820b2a4` | `UpdateReward(uint256 indexed i, uint256 rewardPerBlock)` |
| `0x7283eac7a9c64d862e3560a616651ea06b57add3efe966190156d8862c10efd4` | `UpdateEndBlock(uint256 indexed i, uint256 endBlock)` |
| `0xf164ae823f4542cc5c8fce1671fabc0d21159bf75d4fc92d697be0f1e7488526` | `NewRewardToken(uint256 indexed i, address rewardToken)` *(confirmed live on a real ETH clone)* |
| `0x36bd04094fa067bb9471a8fbdb0a6e8a43424a2566ad3a740c88973fa40a3118` | `RemoveRewardToken(address rewardToken)` *(MineV2 only — V3 has no removeRewardToken)* |
| `0x6b769350ff403947f8ca4f54b35b9747d58b4b2676c957c460c1d5e4ba64342e` | `WithdrawLeftOver(address owner, uint256 i)` |

### 1.6 RewardVault (one per reward token, created by each pool)

| topic0 | Event |
|--------|-------|
| `0xed9a567f42e0ef8986598c5257db7be662f4eaae3892286b03c5ba3a1ddf399b` | `DepositReward(uint256 totalReward, uint256 inputReward, uint256 rewardReserve)` |

### 1.7 DODOMineV3Registry

| topic0 | Event |
|--------|-------|
| `0xcf56b383d806db5e104b5e0ebc881b831f4f726cda7570a1656ca7ee6a25bda7` | `NewMineV3(address mine, address stakeToken, bool isLpToken)` *(confirmed live, ETH)* |
| `0xb59b87a6a27c0ff2f92d7cf00a2fb00b181015191f9df6320d2ec53d4316127a` | `RemoveMineV3(address mine, address stakeToken)` |
| `0x7048027520ecbaa8947764cd502c5c78c2c53bbd902e06b108da1cbdf98c6fc4` | `addAdmin(address admin)` *(lowercase event name — keep as written)* |
| `0x1785f53c768259a7ab38ed67e958aab075b56ff206e3d7f29ea4ca203d1a9774` | `removeAdmin(address admin)` |

### 1.8 DODOMineV3Proxy

| topic0 | Event | Where |
|--------|-------|-------|
| `0xfc795fb7ea3731f56c3ef03f7a51e847fe2d51efd971158498cd281a9ee612d9` | `CreateMineV3(address account, address mineV3)` — **v1** | ETH, BNB, Polygon, Arbitrum, Avalanche, Optimism *(confirmed live, ETH)* |
| `0x2f1b9211ee426c8b408242846001bde46fbdf05fc5bb1f1e8bb0fe41801bbc16` | `CreateMineV3(address account, address mineV3, uint256 platform)` — **v2** | **Base only** |
| `0xf222562df009371dbc94492bddff6e9f6ff435cfb999d5ce9684439db9cbb936` | `DepositRewardToVault(address mine, address rewardToken, uint256 amount)` | both |
| `0x7a506082d4953902efacb789163082daef78c65e6691afe805dd3985b181f645` | `DepositRewardToMine(address mine, address rewardToken, uint256 amount)` | both |
| `0x96dd01a7d9a55f807382e4595daefc9b059147fc9960188979c714c093f2e218` | `ChangeMineV3Template(address mineV3)` | both |

### 1.9 DODOMineV2Factory (Arbitrum, Optimism, Base)

| topic0 | Event |
|--------|-------|
| `0x75b4120ec016f3e27a322dd03424f3dd0ea42ee4dc8f70d70d511b462399d9a3` | `NewMineV2(address mine, address stakeToken)` |
| `0xd3ab54ac9fd01106f83a3a5cbd89011c011d6a5e06f1da848995cbefdcf8e6eb` | `RemoveMineV2(address mine, address stakeToken)` |

### 1.10 DODOIncentive (ETH + BNB)

| topic0 | Event |
|--------|-------|
| `0xd427e26a570fafcb4e8c2c61fde4ef99010612127e4bb6d5f5972eeb12e9f508` | `Incentive(address user, uint256 reward)` *(confirmed live, ETH)* |
| `0x74b543c60303faed44bb045354be4eb79338e531e623b117526453fe53bfc83c` | `SetBoost(address token, uint256 boostRate)` |
| `0x62fd8906333154736b37f9fdf6bed424263e7f41e1b25f523762334c4fc30567` | `SetNewProxy(address dodoProxy)` |
| `0x2bce70618b82fe2049061f3d5eb5044d9b66101ff8ff7c1f18404026cb806b9e` | `SetPerReward(uint256 dodoPerBlock)` *(confirmed live, ETH)* |
| `0xd384a9907ee9e07e400554d68090a36fd75614b27c8b5e9206176ed6353885a8` | `SetDefaultRate(uint256 defaultRate)` |

### 1.11 InitializableOwnable (registry, proxy, vDODO, helper, incentive, MineV2Factory)

| topic0 | Event |
|--------|-------|
| `0xdcf55418cee3220104fef63f979ff3c4097ad240c0c43dcb33ce837748983e62` | `OwnershipTransferPrepared(address previousOwner, address newOwner)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address previousOwner, address newOwner)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 DODO ERC-20 (all chains) + BNB extras

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa9059cbb` | `transfer(address,uint256)` | |
| `0x23b872dd` | `transferFrom(address,address,uint256)` | |
| `0x095ea7b3` | `approve(address,uint256)` | |
| `0x70a08231` | `balanceOf(address)` | |
| `0xdd62ed3e` | `allowance(address,address)` | |
| `0x18160ddd` | `totalSupply()` | ETH = `1e9 × 1e18` (fixed); others vary with bridge supply. |
| `0x313ce567` | `decimals()` | 18 on every chain (verified). |
| `0x95d89b41` | `symbol()` | `"DODO"`. |
| `0x06fdde03` | `name()` | `"DODO bird"`. |
| `0x40c10f19` | `mint(address,uint256)` | **BNB only** (`DODOBscToken`, owner-only). Emits `Mint` + `Transfer(0,user)`. |
| `0x9dc29fac` | `burn(address,uint256)` | **BNB only** (owner-only). Emits `Burn` + `Transfer(user,0)`. |
| `0x7bde82f2` | `redeem(uint256,address)` | **BNB only** — bridge-out (`value, redeemToEthAccount`). Emits `Redeem`. |

> Polygon DODO additionally exposes the Matic proxy surface: `implementation()=0x5c60da1b`, `proxyType()=0x4555d5c9` (returns 2), `proxyOwner()=0x025313a2`, `transferProxyOwnership(address)=0xf1739cae`, `upgradeTo(address)=0x025b22bc`, `upgradeToAndCall(address,bytes)=0xd88ca2c8`. Arbitrum DODO is a bare EIP-1967 beacon proxy (no public proxy getters; read the beacon slot).

### 2.2 vDODO (`vDODOToken`)

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x94bf804d` | `mint(uint256 dodoAmount,address superiorAddress)` | Stake DODO → vDODO. Emits `MintVDODO`. |
| `0xd65a06b0` | `redeem(uint256 vdodoAmount,bool all)` | Redeem vDODO → DODO. Emits `RedeemVDODO`. |
| `0xf14faf6f` | `donate(uint256 dodoAmount)` | Raise `alpha`. Emits `DonateDODO`. |
| `0x5400e36f` | `preDepositedBlockReward(uint256 dodoAmount)` | Emits `PreDeposit`. |
| `0x96153967` | `dodoBalanceOf(address)` | DODO value of an account's vDODO. |
| `0x25d998bb` | `availableBalanceOf(address)` | vDODO not locked in Governance. |
| `0xf9eaa5df` | `getLatestAlpha()` | `(newAlpha,curDistribution)`. |
| `0xbcb86052` | `getWithdrawResult(uint256)` | `(dodoReceive,burnDodoAmount,withdrawFeeDodoAmount)`. |
| `0xdb90c318` | `getDODOWithdrawFeeRatio()` | current withdraw-fee ratio (from helper). |
| `0x443355e5` | `getSuperior(address)` | referral superior. |
| `0xdb1d0fd5` | `alpha()` | global accumulator (`uint112`). |
| `0x34cf1332` | `_DODO_TOKEN_()` | underlying DODO (ETH read = `0x43Df…`; **reverts on BNB deployment**). |
| `0xb88c4f33` | `_DODO_TEAM_()` | referral root (= dodoTeam multisig). |
| `0x5de65173` | `_DOOD_GOV_()` | Governance address (note misspelling `_DOOD_`). |
| `0xeec2cc50` | `_DODO_CIRCULATION_HELPER_()` | circulation helper. |
| `0xc39eabf5` | `_CAN_TRANSFER_()` | transfer toggle. |
| `0x300773cd` | `changePerReward(uint256)` | owner-only. Emits `ChangePerReward`. |
| `0xb420901a` | `updateDODOFeeBurnRatio(uint256)` | owner-only. Emits `UpdateDODOFeeBurnRatio`. |
| `0xf3a37cd2` | `setCantransfer(bool)` | owner-only. Emits `SetCantransfer`. |
| `0xe401b5ba` | `updateDODOCirculationHelper(address)` | owner-only. |
| `0xb2561263` | `updateGovernance(address)` | owner-only. |
| `0xdb2e21bc` | `emergencyWithdraw()` | owner-only. |
| `0x18160ddd` | `totalSupply()` / `0x70a08231` `balanceOf(address)` / `0xa9059cbb` `transfer` / `0x095ea7b3` `approve` / `0x23b872dd` `transferFrom` / `0xdd62ed3e` `allowance` | ERC-20 surface (transfers gated by `_CAN_TRANSFER_`). |

### 2.3 DODOCirculationHelper

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xbf151cb8` | `getCirculation()` | circulating DODO (`1e9·1e18` − locked balances). ETH read ≈ 711 M DODO. |
| `0xdef0d15d` | `getDodoWithdrawFeeRatio()` | vDODO withdraw fee. ETH read = `0.15e18` (15 %, max). |
| `0x2358dbc0` | `geRatioValue(uint256)` | fee curve (15 %→5 %). |
| `0xa82d6930` | `addLockedContractAddress(address)` | owner-only. |
| `0x188f4012` | `removeLockedContractAddress(address)` | owner-only. |

### 2.4 Governance

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2f781638` | `getLockedvDODO(address)` | sum of vDODO locked across registered mines. |
| `0x70b689ff` | `addMineContract(address[])` | owner-only. Emits `AddMineContract`. |
| `0x75f85a91` | `removeMineContract(address)` | owner-only. Emits `RemoveMineContract`. |

### 2.5 DODOMineV3 / DODOMineV2 staking pool (`ERC20MineV3`/`ERC20Mine` + `BaseMine`)

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xb6b55f25` | `deposit(uint256 amount)` | stake. Emits `Deposit`. |
| `0x2e1a7d4d` | `withdraw(uint256 amount)` | unstake. Emits `Withdraw`. |
| `0xae169a50` | `claimReward(uint256 i)` | claim reward token `i`. Emits `Claim`. |
| `0x0b83a727` | `claimAllRewards()` | claim every reward token. |
| `0x999ffd97` | `getPendingReward(address user,uint256 i)` | pending reward for token `i`. |
| `0x00b68f08` | `getPendingRewardByToken(address,address)` | pending by reward-token address. |
| `0xa7c3e4e5` | `addRewardToken(address,uint256,uint256,uint256)` | owner-only (proxy/factory calls it). Emits `NewRewardToken`. |
| `0x1abbeb54` | `setEndBlock(uint256,uint256)` | owner-only. Emits `UpdateEndBlock`. |
| `0xa47bd496` | `setReward(uint256,uint256)` | owner-only. Emits `UpdateReward`. |
| `0xd895fff1` | `withdrawLeftOver(uint256,uint256)` | owner-only. Emits `WithdrawLeftOver`. |
| `0x3d509c97` | `removeRewardToken(address)` | **MineV2 only**. Emits `RemoveRewardToken`. |
| `0xbdd37dc6` | `directTransferOwnership(address)` | **MineV3 only** (proxy uses it). |
| `0x92e3200b` | `_TOKEN_()` | the staked token (`0x0` on the uninitialized template). |
| `0xf09a4016` | `init(address owner,address token)` | one-shot init (called on the clone). |
| `0x5ae9a549` | `getRewardNum()` | number of reward tokens. |
| `0x697d86a2` | `getRewardTokenById(uint256)` | reward-token address by index. |
| `0xa2a54bee` | `getIdByRewardToken(address)` | index by reward-token. |
| `0xe513eb15` | `getVaultByRewardToken(address)` | the RewardVault for a reward token. |
| `0x16048bc4` | `_OWNER_()` | pool owner (`InitializableOwnable`). |

### 2.6 DODOMineV3Registry

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x146204d2` | `addMineV3(address mine,bool isLpToken,address stakeToken)` | **admin-listed callers only** (the proxy). Emits `NewMineV3`. |
| `0x2805172f` | `removeMineV3(address,bool,address)` | owner-only. Emits `RemoveMineV3`. |
| `0xae52aae7` | `addAdminList(address)` | owner-only. Emits `addAdmin`. |
| `0xfd8bd849` | `removeAdminList(address)` | owner-only. Emits `removeAdmin`. |
| `0x1822c0c0` | `isAdminListed(address)` | `bool` (ETH proxy reads `true`). |
| `0x468c8d23` | `_MINE_REGISTRY_(address)` | mine → stakeToken. |
| `0x06e6a8da` | `_LP_REGISTRY_(address,uint256)` | LP-token → mine[]. |
| `0xa3116529` | `_SINGLE_REGISTRY_(address,uint256)` | single-token → mine[]. |

### 2.7 DODOMineV3Proxy

| Selector | Signature | Where / notes |
|----------|-----------|---------------|
| `0xb9b1135c` | `createDODOMineV3(address stakeToken,bool isLpToken,address[] rewardTokens,uint256[] rewardPerBlock,uint256[] startBlock,uint256[] endBlock)` — **v1** | ETH/BNB/Polygon/Arbitrum/Avalanche/Optimism. Clones template, funds, registers. Emits `CreateMineV3(address,address)`. |
| `0x94852c61` | `createDODOMineV3(address stakeToken,bool isLpToken,uint256 platform,address[] rewardTokens,uint256[] rewardPerBlock,uint256[] startBlock,uint256[] endBlock)` — **v2** | **Base only**. Emits `CreateMineV3(address,address,uint256)`. |
| `0x9cb297cd` | `depositRewardToVault(address mineV3,address rewardToken,uint256 amount)` | top up a pool's RewardVault. |
| `0xe17ff361` | `depositRewardToMine(address mineV3,address rewardToken,uint256 amount)` | send rewards straight to a pool. |
| `0x59e1100b` | `updateMineV3Template(address)` | owner-only. Emits `ChangeMineV3Template`. |
| `0x54fd4d50` | `version()` | **v2/Base only** → `"MineV3Proxy 0.0.1"`; **reverts on v1**. Use this to tell the generations apart. |

### 2.8 DODOMineV2Factory (Arbitrum, Optimism, Base)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x61175cd2` | `createDODOMineV2(address stakeToken,address[] rewardTokens,uint256[] rewardPerBlock,uint256[] startBlock,uint256[] endBlock)` | **owner-only**. Emits `NewMineV2`. |
| `0x30c1cad8` | `updateMineV2Template(address)` | owner-only. |
| `0x9e988ee3` | `updateDefaultMaintainer(address)` | owner-only. |
| `0xe9b1660b` | `addByAdmin(address mine,address stakeToken)` | owner-only. Emits `NewMineV2`. |
| `0x6defeb31` | `removeByAdmin(address,address)` | owner-only. Emits `RemoveMineV2`. |
| `0x468c8d23` | `_MINE_REGISTRY_(address)` | mine → stakeToken. |
| `0x283e4275` | `_STAKE_REGISTRY_(address)` | stakeToken → mine. |

### 2.9 DODOIncentive (ETH + BNB)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x188aa964` | `triggerIncentive(address fromToken,address toToken,address assetTo)` | **only callable by `_DODO_PROXY_`**. Emits `Incentive`. |
| `0x46748bc9` | `changeBoost(address,uint256)` | owner-only. Emits `SetBoost`. |
| `0x300773cd` | `changePerReward(uint256)` | owner-only. Emits `SetPerReward`. |
| `0x106b8e8b` | `changeDefaultRate(uint256)` | owner-only. Emits `SetDefaultRate`. |
| `0xb56afe75` | `changeDODOProxy(address)` | owner-only. Emits `SetNewProxy`. |
| `0xf54651de` | `emptyReward(address)` | owner-only sweep. |
| `0x2ced893b` | `incentiveStatus(address,address)` | view: `(reward,baseRate,totalRate,curTotalReward,perBlockReward)`. |
| `0xfdabc986` | `boosts(address)` | per-token boost rate. |
| `0x8af70336` | `dodoPerBlock()` | emission rate. |

### 2.10 InitializableOwnable surface (registry, proxy, vDODO, helper, incentive, MineV2Factory)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf2fde38b` | `transferOwnership(address)` | begin handover. Emits `OwnershipTransferPrepared`. |
| `0x4e71e0c8` | `claimOwnership()` | complete handover. Emits `OwnershipTransferred`. (Also on `DODOBscToken`.) |
| `0x16048bc4` | `_OWNER_()` | current owner. |
| `0x0d009297` | `initOwner(address)` | one-shot init. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

Verified via `eth_getCode` on `https://ethereum-rpc.publicnode.com`. All immutable (EIP-1967 impl slot = `0x0`).

| Role | Address | One-liner |
|------|---------|-----------|
| **DODO** (`DODOToken`) | `0x43Dfc4159D86F3A37A5A4B3D4580b888ad7d4DDd` | Canonical ERC-20, fixed 1 B supply, no mint. `Transfer`/`Approval` only. |
| **vDODO** (`vDODOToken`) | `0xc4436fBAE6eBa5d95bf7d53Ae515F8A707Bd402A` | Membership/gov token. `_DODO_TOKEN_()`=`0x43Df…`, `symbol()`="vDODO". |
| **DODOCirculationHelper** | `0x357c5e9cfa8b834edcef7c7aabd8f9db09119d11` | Circulating supply + vDODO withdraw-fee curve. |
| **Governance** | `0x0000000000000000000000000000000000000000` | **Unset** in the deploy config (vDODO `_DOOD_GOV_` may point elsewhere — read it live). |
| **dodoTeam / multisig** (`_DODO_TEAM_`) | `0x95C4F5b83aA70810D4f142d58e5F7242Bd891CB0` | Gnosis Safe (singleton `0x34cf…3f5f`). Referral root; protocol owner. |
| **ERC20MineV3** (template) | `0xD57f29B297e33c977e2186a751414BFeD6A38c5a` | EIP-1167 clone master for MineV3 pools (`_TOKEN_()`=0). |
| **DODOMineV3Registry** | `0xf8ab09b3D2d5EfA603f4646E5a8A12588E852195` | Pool registry; `NewMineV3` confirmed live. Proxy is admin-listed. |
| **DODOMineV3Proxy** (v1) | `0x0d9685D4037580F68D9F77B08971f17E1000bBdc` | Create-entry; 6-arg `createDODOMineV3`; emits `CreateMineV3(address,address)`. `version()` reverts. |
| **DODOIncentive** | `0x989DcAA95801C527C5B73AA65d3962dF9aCe1b0C` | Trade-mining; `Incentive`/`SetPerReward` confirmed live (now dormant). |

*Example discovered pool (do not hard-code — enumerate from `NewMineV3`): clone `0xa264dee4cbb7b3db3a7d5daa221c83209a0d31ac` (45 B EIP-1167 proxy of the template, `_TOKEN_()`=`0x4916…6b5d`).*

---

## 4. Addresses — BNB Smart Chain (chain ID 56)

Verified via `eth_getCode` on `https://bsc-rpc.publicnode.com`. All immutable.

| Role | Address | One-liner |
|------|---------|-----------|
| **DODO** (`DODOBscToken`) | `0x67ee3Cb086F8a16f34beE3ca72FAD36F7Db929e2` | Ownable mint/burn **bridge** token; `_OWNER_()`=`0xcaa4…638b`. Adds `Mint`/`Burn`/`Redeem`. |
| **vDODO** (`vDODOToken`) | `0x4D6A41C682874E5dd1BBD58184eE8FF145C89202` | `symbol()`="vDODO". (`_DODO_TOKEN_()` getter reverts on this deployment.) |
| **ERC20MineV3** (template) | `0xBA428FC3c5ce457c236869787c26f725Ff5168D8` | Clone master (identical bytecode to ETH template). |
| **DODOMineV3Registry** | `0x2A5aa99095E3724b8955BF7b5E47dbe2730dabD8` | Pool registry. |
| **DODOMineV3Proxy** (v1) | `0x3c39dCb3630D305530a30419b3DEEcea629597AC` | 6-arg create; `CreateMineV3(address,address)`. |
| **DODOIncentive** | `0x4EE6398898F7FC3e648b3f6bA458310ac29cD352` | Trade-mining. |

`DODOCirculationHelper`/`Governance`/`dodoTeam` are **empty** in the BNB deploy config (vDODO on BNB references the ETH-side helper indirectly). BNB has **no** DODOMineV2 layer.

---

## 5. Addresses — Polygon PoS (chain ID 137)

Verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **DODO** (PoS child token) | `0xe4Bf2864ebeC7B7fDf6Eeca9BaCAe7cDfDAffe78` | **Upgradeable Matic `UpgradeabilityProxy`** — `proxyType()`=2, `proxyOwner()`=`0x355b…343f`, `implementation()`=`0x641a7567e18e4a1d94845b448125e7ef684bb573` (14 214 B child). |
| **ERC20MineV3** (template) | `0xda59427Bd9d4827Ec9f751719eb79b0a3e74FA4D` | Clone master. |
| **DODOMineV3Registry** | `0x27566bf9504466F6f3a1571E1863Da42fff4D25E` | Pool registry. |
| **DODOMineV3Proxy** (v1) | `0x47a65e74dd6b6B5E3243dBb01EDEd9D55ba234Ad` | 6-arg create; `CreateMineV3(address,address)`. |

**No vDODO, no DODOIncentive, no DODOMineV2** on Polygon (`eth_getCode` = `0x` for the ETH vDODO/Incentive addresses here).

---

## 6. Addresses — Arbitrum One (chain ID 42161)

Verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **DODO** (bridge token) | `0x69Eb4FA4a2fbd498C257C57Ea8b7655a2559A581` | **Upgradeable EIP-1967 beacon proxy** (760 B) — beacon `0xe72ba9418b5f2ce0a6a40501fe77c6839aa37333` → impl `0x3f770ac673856f105b586bb393d122721265ad46`. |
| **ERC20MineV2** (template) | `0xe91067189C71dB0696bD6fBC14535CB159F98b5C` | Older clone master (`_TOKEN_()`=0). |
| **ERC20MineV3** (template) | `0x973CAB76C35BB1da47e044A63546c69A8Ac1143c` | MineV3 clone master. |
| **DODOMineV2Factory** | `0x5a2E2278A0fACcf224cEd1ce809eC4e4b1708759` | Older mining factory; `NewMineV2`. |
| **DODOMineV3Registry** | `0x2B40bC6c9C12c18787436aa1E2B761f684F42999` | Pool registry. |
| **DODOMineV3Proxy** (v1) | `0x9A74B169798bE874EF1C23b4092e5689969eF45E` | 6-arg create; `CreateMineV3(address,address)`. |

**No vDODO, no DODOIncentive** on Arbitrum.

---

## 7. Addresses — Avalanche C-Chain (chain ID 43114)

Verified via `eth_getCode` on `https://avalanche-c-chain-rpc.publicnode.com`. **No DODO token, no vDODO, no DODOIncentive, no DODOMineV2** here — only the MineV3 stack.

| Role | Address | One-liner |
|------|---------|-----------|
| **ERC20MineV3** (template) | `0xF31162ef57b61D2FBA4f64dBbaC536bFc782D37c` | Clone master. |
| **DODOMineV3Registry** | `0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4` | Pool registry. |
| **DODOMineV3Proxy** (v1) | `0x5D6e6A0BFB2176AFCc4FB809822D8e009216b245` | 6-arg create; `CreateMineV3(address,address)`. |

---

## 8. Addresses — Optimism (chain ID 10)

Verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`. **No DODO token, no vDODO, no DODOIncentive** here.

| Role | Address | One-liner |
|------|---------|-----------|
| **ERC20MineV2** (template) | `0x056927aC73e764247D9D2C41B8C321eA82ee468A` | Older clone master. |
| **ERC20MineV3** (template) | `0x34229d00fB972e295359107c718eB621335Fa596` | MineV3 clone master (12 639 B — minor build variant). |
| **DODOMineV2Factory** | `0xA36b345d087C14161D0B3fE1b96fD1CC551CE0C9` | Older mining factory. |
| **DODOMineV3Registry** | `0x9eD110c929A1F9E4AE4Fa8a88f7Be5c2292d2a7F` | Pool registry. |
| **DODOMineV3Proxy** (v1) | `0xaEdbD08D92ECccaA9A93b1A8D66D1d356e470c78` | 6-arg create; `CreateMineV3(address,address)`. |

---

## 9. Addresses — Base (chain ID 8453)

Verified via `eth_getCode` on `https://base-rpc.publicnode.com`. **No DODO token, no vDODO, no DODOIncentive.** Base is the **only** chain on the **v2** MineV3Proxy.

| Role | Address | One-liner |
|------|---------|-----------|
| **ERC20MineV2** (template) | `0xEAC4BFef7D1c872Ed705B01856af7f9802adC596` | Older clone master. |
| **ERC20MineV3** (template) | `0x04f7BaE2A4c05cd567F762E33450deBCebdC89EA` | MineV3 clone master (11 647 B variant). |
| **DODOMineV2Factory** | `0xFD2b7994f91c08aAa5e013E899334A2DBb500DF1` | Older mining factory. |
| **DODOMineV3Registry** | `0x8dD0Fea5FA2f7df535F87f312641Cc15d8B151BA` | Pool registry. |
| **DODOMineV3Proxy** (**v2**) | `0x2F66C5aAF006Bd9c51615D617589C16c0ed35fD3` | **7-arg** `createDODOMineV3` with `platform`; emits `CreateMineV3(address,address,uint256)`; `version()`=`"MineV3Proxy 0.0.1"`. |

---

## 10. Cross-chain summary

| Chain | ID | DODO token | vDODO | DODOIncentive | MineV3 Registry | MineV3 Proxy | MineV3 template | MineV2 Factory + template |
|---|---|---|---|---|---|---|---|---|
| Ethereum | 1 | ✓ `0x43Df…` (immutable) | ✓ `0xc443…` | ✓ `0x989D…` | ✓ `0xf8ab…` | ✓ v1 `0x0d96…` | ✓ `0xD57f…` | — |
| BNB | 56 | ✓ `0x67ee…` (immutable, mint/burn) | ✓ `0x4D6A…` | ✓ `0x4EE6…` | ✓ `0x2A5a…` | ✓ v1 `0x3c39…` | ✓ `0xBA42…` | — |
| Polygon | 137 | ✓ `0xe4Bf…` (**proxy**, Matic) | — | — | ✓ `0x2756…` | ✓ v1 `0x47a6…` | ✓ `0xda59…` | — |
| Arbitrum | 42161 | ✓ `0x69Eb…` (**beacon proxy**) | — | — | ✓ `0x2B40…` | ✓ v1 `0x9A74…` | ✓ `0x973C…` | ✓ `0x5a2E…` / `0xe910…` |
| Avalanche | 43114 | — | — | — | ✓ `0x0fe2…` | ✓ v1 `0x5D6e…` | ✓ `0xF311…` | — |
| Optimism | 10 | — | — | — | ✓ `0x9eD1…` | ✓ v1 `0xaEdb…` | ✓ `0x3422…` | ✓ `0xA36b…` / `0x0569…` |
| Base | 8453 | — | — | — | ✓ `0x8dD0…` | ✓ **v2** `0x2F66…` | ✓ `0x04f7…` | ✓ `0xFD2b…` / `0xEAC4…` |

DODO token: 4 chains. vDODO + DODOIncentive: 2 chains (ETH/BNB). MineV3 registry/proxy/template: all 7. MineV2: 3 chains (Arbitrum/Optimism/Base).

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **DODO — Ethereum** | Immutable | 1 995 B full contract; EIP-1967 impl slot empty. | n/a (fixed supply). |
| **DODO — BNB** (`DODOBscToken`) | Immutable, Ownable | 3 773 B; impl slot empty; exposes `mint`/`burn`/`claimOwnership`. | `_OWNER_()`=`0xcaa4…638b` (mint/burn = bridge). |
| **DODO — Polygon** | **Matic `UpgradeabilityProxy`** (`proxyType()=2`) — *not* EIP-1967 | 2 949 B proxy; `implementation()`/`proxyOwner()`/`upgradeTo()` present; impl=`0x641a7567…`. | `proxyOwner()`=`0x355b…343f`. |
| **DODO — Arbitrum** | **EIP-1967 beacon proxy** | 760 B; **beacon slot** `0xa3f0ad74…133d50` set → beacon `0xe72b…7333`; read beacon's `implementation()`=`0x3f77…ad46`. Impl/admin slots empty. | beacon owner. |
| **vDODO / DODOCirculationHelper / Governance / DODOIncentive** | Immutable (`InitializableOwnable`) | full contract; EIP-1967 impl slot empty. | `_OWNER_()`. |
| **DODOMineV3Registry** | Immutable | 2 844 B on every chain; impl slot empty (verified all 7). | `_OWNER_()`. |
| **DODOMineV3Proxy** | Immutable; **two ABI generations** | 4 177 B = **v1** (`createDODOMineV3` `0xb9b1135c`, `version()` reverts); 4 365 B = **v2** Base (`0x94852c61`, `version()`→string). Impl slot empty. | `_OWNER_()`. |
| **ERC20MineV3 / ERC20Mine templates** | Immutable **clone masters** | full contract; `_TOKEN_()`=0 (uninitialized); impl slot empty. | n/a. |
| **MineV3/V2 pools** | **EIP-1167 minimal-proxy clones** | ~45 B clone bytecode (`363d3d…`); delegates to the template; discover from `NewMineV3`/`NewMineV2`. | pool `_OWNER_()` (the pool creator; proxy `directTransferOwnership`s it to `msg.sender`). |
| **DODOMineV2Factory** | Immutable | 3 332 B; impl slot empty. | `_OWNER_()`. |

EIP-1967 slots used: impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`, admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`, **beacon `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50`** (Arbitrum DODO uses the beacon slot).

---

## 12. Detection invariants & gotchas

1. **DODO is a different address AND a different contract on every chain.** Always key on `(chainId, token address)`. The four token addresses: ETH `0x43Df…`, BNB `0x67ee…`, Polygon `0xe4Bf…`, Arbitrum `0x69Eb…`. **Avalanche, Optimism, Base have no DODO token** (`0x` bytecode at every candidate address).
2. **Two of the four DODO tokens are upgradeable proxies.** Polygon = Matic `UpgradeabilityProxy` (`proxyType()=2`, read `implementation()`); Arbitrum = **EIP-1967 beacon proxy** (read the **beacon slot** `0xa3f0ad74…`, then the beacon's `implementation()`). ETH and BNB are immutable. Watch the impl/beacon for upgrades on Polygon/Arbitrum.
3. **vDODO events are `MintVDODO`/`RedeemVDODO` (uppercase `VDODO`).** Topic0s `0xb299178f…` / `0x10e8afa8…` (both confirmed live, ETH). The lowercase `MintvDODO`/`RedeemvDODO` (`0x50b992cc…`/`0xc694aa60…`) are wrong signatures and never fire.
4. **vDODO is ETH + BNB only.** No vDODO on Polygon/Arbitrum/Avalanche/Optimism/Base. On BNB, the `_DODO_TOKEN_()` getter reverts (different build) — identify the contract by `symbol()`="vDODO" and the event topic0s, not by that getter.
5. **vDODO redeem leaves NO net `Transfer` to the user equal to their stake.** `redeem` pays `dodoReceive`, **burns** `burnDodoAmount` via `Transfer(holder, address(0))`, and the withdraw fee stays in-contract (raising `alpha`). Track DODO economics via `RedeemVDODO` (it carries `receiveDODO`/`burnDODO`/`feeDODO`), not raw transfers.
6. **vDODO `Transfer` only fires when `_CAN_TRANSFER_` is true.** Most of vDODO's life it is non-transferable; `balanceOf` is derived (`dodoBalanceOf/100`), not a stored balance.
7. **MineV3 and MineV2 pools share identical event signatures** (both inherit `BaseMine`). A `Deposit`/`Claim`/`NewRewardToken` topic0 alone does not tell you V2 vs V3 — distinguish by which registry/factory created the pool (`NewMineV3` vs `NewMineV2`).
8. **Mining pools are EIP-1167 clones — never enumerate them.** Discover MineV3 pools from `DODOMineV3Registry.NewMineV3` (mine, stakeToken, isLpToken — all non-indexed, parse from `data`); MineV2 pools from `DODOMineV2Factory.NewMineV2`. A real ETH MineV3 clone (`0xa264dee4…`, 45 B) was confirmed to emit `NewRewardToken` and expose `_TOKEN_()`.
9. **`CreateMineV3` has two shapes.** Base (MineV3Proxy v2) emits `CreateMineV3(address,address,uint256)` = `0x2f1b9211…`; **all other chains** (v1) emit `CreateMineV3(address,address)` = `0xfc795fb7…`. Match the topic0 to the chain, or you will miss pool creations. `createDODOMineV3` likewise differs: v1 selector `0xb9b1135c` (6 args), v2 `0x94852c61` (7 args, adds `platform`). Probe `version()` (reverts on v1) to disambiguate the proxy generation.
10. **`addMineV3` on the registry is admin-listed, not public.** Only callers in `isAdminListed` (the MineV3Proxy) may register. `removeMineV3`/`addAdminList` are owner-only. The proxy is the admin-listed creator on every chain (ETH `isAdminListed(proxy)`=true).
11. **`createDODOMineV2` is owner-only** (unlike MineV3 which anyone can call through the proxy). MineV2 pools are seeded by the DODO admin only.
12. **The registry/proxy/templates/vDODO/helper/incentive are all immutable** — none is an EIP-1967 upgradeable proxy. The registry impl slot was read empty on all 7 chains. Don't expect `Upgraded(address)` from any of them. (The *tokens* on Polygon/Arbitrum are the only upgradeable pieces here.)
13. **`triggerIncentive` is access-restricted to `_DODO_PROXY_`** — only the DODO router can mint trade-mining rewards. The `Incentive`/`SetPerReward` topics were confirmed live on ETH (active early 2021; the program is now dormant — expect few/no recent logs).
14. **BNB DODO can mint/burn** (`Mint`/`Burn`/`Redeem(sender,redeemToEthAccount,value)`), gated by `_OWNER_()`=`0xcaa4…638b` (the bridge custodian). ETH DODO has a fixed supply and **cannot** mint. Polygon/Arbitrum mint/burn through their respective bridge mechanisms (child-token deposit / gateway), surfacing as `Transfer` from/to `address(0)`.
15. **`Governance` is `0x0` in the ETH deploy config** — the on-chain `Governance.sol` may be deployed at a different address or vDODO's `_DOOD_GOV_` may be unset (so `availableBalanceOf` == `balanceOf`). Read vDODO `_DOOD_GOV_()` live before assuming a lock contract exists.
16. **Some MineV3 templates have slightly different byte sizes per chain** (ETH/BNB/Polygon/Arbitrum/Avalanche ≈ 12 351 B; Optimism 12 639; Base 11 647) — minor compiler/build differences. The selectors and event topic0s are identical; do not treat the size delta as a different contract.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- DODO ERC-20 (all chains)
TOPIC_TRANSFER                    = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_APPROVAL                    = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
-- DODO (BNB) bridge extras
TOPIC_DODO_MINT                   = '\x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'
TOPIC_DODO_BURN                   = '\xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'
TOPIC_DODO_REDEEM                 = '\xd12200efa34901b99367694174c3b0d32c99585fdf37c7c26892136ddd0836d9'
-- vDODO (ETH + BNB)
TOPIC_MINT_VDODO                  = '\xb299178f92646282937cbe7c9e854594cb5ef6330e03b43946086e9dc0ca9ecd'
TOPIC_REDEEM_VDODO                = '\x10e8afa8e2aa45e6f179fcaa8538c699a53e253cda2b304d7fa46174527cedc3'
TOPIC_DONATE_DODO                 = '\x3ed260d8e11a4e325861a1b184d8389e34339a456bc04d53f111e5d99ae22ac1'
TOPIC_PREDEPOSIT                  = '\xdee982458f84113ac3e32d44595820a6fa60cfbe80a1bdd444c26599ee5b7dd5'
TOPIC_CHANGE_PER_REWARD_VDODO     = '\xeca81e4b546cfbc80883349ef5bdaca1c02dc7cb0bdb9e1183cb7698f90bbb85'
TOPIC_UPDATE_FEE_BURN_RATIO       = '\xff3692e8e3336aaee232986626f21d80be86e891d2122581acf795123af3e8a3'
TOPIC_SET_CANTRANSFER             = '\x8faf67cb6de7f4aed6e2791474b60016b6cb2b4e756529701e7863892e468694'
-- Governance
TOPIC_ADD_MINE_CONTRACT           = '\xa76ac1a4fabc693f63d84fd19178974552a165bad13617158ebd0583d6432f1a'
TOPIC_REMOVE_MINE_CONTRACT        = '\x79ae063e729116d1171752e357397faa6caeb747d9daa2b4479106a54ad84901'
-- MineV3/MineV2 pool (BaseMine)
TOPIC_MINE_DEPOSIT                = '\xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c'
TOPIC_MINE_WITHDRAW               = '\x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364'
TOPIC_MINE_CLAIM                  = '\x3ed1528b0fdc7c5207c1bf935e34a667e13656b9ed165260c522be0bc544f303'
TOPIC_MINE_UPDATE_REWARD          = '\xbcabeac7f89430597dc942c3264f28fd08010c3b2e19ecf95c6e690f9820b2a4'
TOPIC_MINE_UPDATE_END_BLOCK       = '\x7283eac7a9c64d862e3560a616651ea06b57add3efe966190156d8862c10efd4'
TOPIC_MINE_NEW_REWARD_TOKEN       = '\xf164ae823f4542cc5c8fce1671fabc0d21159bf75d4fc92d697be0f1e7488526'
TOPIC_MINE_REMOVE_REWARD_TOKEN    = '\x36bd04094fa067bb9471a8fbdb0a6e8a43424a2566ad3a740c88973fa40a3118'
TOPIC_MINE_WITHDRAW_LEFTOVER      = '\x6b769350ff403947f8ca4f54b35b9747d58b4b2676c957c460c1d5e4ba64342e'
TOPIC_REWARDVAULT_DEPOSIT_REWARD  = '\xed9a567f42e0ef8986598c5257db7be662f4eaae3892286b03c5ba3a1ddf399b'
-- DODOMineV3Registry
TOPIC_NEW_MINE_V3                 = '\xcf56b383d806db5e104b5e0ebc881b831f4f726cda7570a1656ca7ee6a25bda7'
TOPIC_REMOVE_MINE_V3              = '\xb59b87a6a27c0ff2f92d7cf00a2fb00b181015191f9df6320d2ec53d4316127a'
TOPIC_REGISTRY_ADD_ADMIN          = '\x7048027520ecbaa8947764cd502c5c78c2c53bbd902e06b108da1cbdf98c6fc4'
TOPIC_REGISTRY_REMOVE_ADMIN       = '\x1785f53c768259a7ab38ed67e958aab075b56ff206e3d7f29ea4ca203d1a9774'
-- DODOMineV3Proxy
TOPIC_CREATE_MINE_V3_V1           = '\xfc795fb7ea3731f56c3ef03f7a51e847fe2d51efd971158498cd281a9ee612d9'  -- (address,address) — all chains except Base
TOPIC_CREATE_MINE_V3_V2           = '\x2f1b9211ee426c8b408242846001bde46fbdf05fc5bb1f1e8bb0fe41801bbc16'  -- (address,address,uint256) — Base only
TOPIC_DEPOSIT_REWARD_TO_VAULT     = '\xf222562df009371dbc94492bddff6e9f6ff435cfb999d5ce9684439db9cbb936'
TOPIC_DEPOSIT_REWARD_TO_MINE      = '\x7a506082d4953902efacb789163082daef78c65e6691afe805dd3985b181f645'
TOPIC_CHANGE_MINE_V3_TEMPLATE     = '\x96dd01a7d9a55f807382e4595daefc9b059147fc9960188979c714c093f2e218'
-- DODOMineV2Factory (Arb/Op/Base)
TOPIC_NEW_MINE_V2                 = '\x75b4120ec016f3e27a322dd03424f3dd0ea42ee4dc8f70d70d511b462399d9a3'
TOPIC_REMOVE_MINE_V2              = '\xd3ab54ac9fd01106f83a3a5cbd89011c011d6a5e06f1da848995cbefdcf8e6eb'
-- DODOIncentive (ETH + BNB)
TOPIC_INCENTIVE                   = '\xd427e26a570fafcb4e8c2c61fde4ef99010612127e4bb6d5f5972eeb12e9f508'
TOPIC_INCENTIVE_SET_BOOST         = '\x74b543c60303faed44bb045354be4eb79338e531e623b117526453fe53bfc83c'
TOPIC_INCENTIVE_SET_NEW_PROXY     = '\x62fd8906333154736b37f9fdf6bed424263e7f41e1b25f523762334c4fc30567'
TOPIC_INCENTIVE_SET_PER_REWARD    = '\x2bce70618b82fe2049061f3d5eb5044d9b66101ff8ff7c1f18404026cb806b9e'
TOPIC_INCENTIVE_SET_DEFAULT_RATE  = '\xd384a9907ee9e07e400554d68090a36fd75614b27c8b5e9206176ed6353885a8'
-- InitializableOwnable
TOPIC_OWNERSHIP_TRANSFER_PREPARED = '\xdcf55418cee3220104fef63f979ff3c4097ad240c0c43dcb33ce837748983e62'
TOPIC_OWNERSHIP_TRANSFERRED       = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'

-- ===== Selectors =====
-- DODO ERC-20 (BNB extras)
SEL_DODO_MINT                     = '\x40c10f19'   -- mint(address,uint256)  (BNB)
SEL_DODO_BURN                     = '\x9dc29fac'   -- burn(address,uint256)  (BNB)
SEL_DODO_REDEEM_BRIDGE            = '\x7bde82f2'   -- redeem(uint256,address) (BNB)
-- vDODO
SEL_VDODO_MINT                    = '\x94bf804d'   -- mint(uint256,address)
SEL_VDODO_REDEEM                  = '\xd65a06b0'   -- redeem(uint256,bool)
SEL_VDODO_DONATE                  = '\xf14faf6f'   -- donate(uint256)
SEL_VDODO_PREDEPOSIT              = '\x5400e36f'   -- preDepositedBlockReward(uint256)
SEL_VDODO_DODO_BALANCE_OF         = '\x96153967'   -- dodoBalanceOf(address)
SEL_VDODO_DODO_TOKEN              = '\x34cf1332'   -- _DODO_TOKEN_()
-- DODOCirculationHelper
SEL_GET_CIRCULATION               = '\xbf151cb8'   -- getCirculation()
SEL_GET_WITHDRAW_FEE_RATIO        = '\xdef0d15d'   -- getDodoWithdrawFeeRatio()
-- Governance
SEL_GET_LOCKED_VDODO              = '\x2f781638'   -- getLockedvDODO(address)
-- MineV3/MineV2 pool
SEL_MINE_DEPOSIT                  = '\xb6b55f25'   -- deposit(uint256)
SEL_MINE_WITHDRAW                 = '\x2e1a7d4d'   -- withdraw(uint256)
SEL_MINE_CLAIM_REWARD             = '\xae169a50'   -- claimReward(uint256)
SEL_MINE_CLAIM_ALL                = '\x0b83a727'   -- claimAllRewards()
SEL_MINE_GET_PENDING_REWARD       = '\x999ffd97'   -- getPendingReward(address,uint256)
SEL_MINE_ADD_REWARD_TOKEN         = '\xa7c3e4e5'   -- addRewardToken(address,uint256,uint256,uint256)
SEL_MINE_TOKEN                    = '\x92e3200b'   -- _TOKEN_()
SEL_MINE_INIT                     = '\xf09a4016'   -- init(address,address)
-- DODOMineV3Registry
SEL_REGISTRY_ADD_MINE_V3          = '\x146204d2'   -- addMineV3(address,bool,address)
SEL_REGISTRY_REMOVE_MINE_V3       = '\x2805172f'   -- removeMineV3(address,bool,address)
SEL_REGISTRY_IS_ADMIN_LISTED      = '\x1822c0c0'   -- isAdminListed(address)
SEL_REGISTRY_MINE_REGISTRY        = '\x468c8d23'   -- _MINE_REGISTRY_(address)
-- DODOMineV3Proxy
SEL_CREATE_MINE_V3_V1             = '\xb9b1135c'   -- createDODOMineV3(address,bool,address[],uint256[],uint256[],uint256[])  (all except Base)
SEL_CREATE_MINE_V3_V2             = '\x94852c61'   -- createDODOMineV3(address,bool,uint256,address[],uint256[],uint256[],uint256[])  (Base)
SEL_PROXY_DEPOSIT_TO_VAULT        = '\x9cb297cd'   -- depositRewardToVault(address,address,uint256)
SEL_PROXY_DEPOSIT_TO_MINE         = '\xe17ff361'   -- depositRewardToMine(address,address,uint256)
SEL_PROXY_VERSION                 = '\x54fd4d50'   -- version()  (reverts on v1; returns on Base v2)
-- DODOMineV2Factory
SEL_CREATE_MINE_V2                = '\x61175cd2'   -- createDODOMineV2(address,address[],uint256[],uint256[],uint256[])
SEL_FACTORY_STAKE_REGISTRY        = '\x283e4275'   -- _STAKE_REGISTRY_(address)
-- DODOIncentive
SEL_TRIGGER_INCENTIVE             = '\x188aa964'   -- triggerIncentive(address,address,address)
SEL_INCENTIVE_CHANGE_BOOST        = '\x46748bc9'   -- changeBoost(address,uint256)
SEL_INCENTIVE_STATUS              = '\x2ced893b'   -- incentiveStatus(address,address)
-- InitializableOwnable
SEL_TRANSFER_OWNERSHIP            = '\xf2fde38b'   -- transferOwnership(address)
SEL_CLAIM_OWNERSHIP               = '\x4e71e0c8'   -- claimOwnership()
SEL_OWNER                         = '\x16048bc4'   -- _OWNER_()

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT                 = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
EIP1967_BEACON_SLOT               = '\xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50'  -- Arbitrum DODO

-- ===== Ethereum (chain ID 1) =====
ETH_DODO                          = '\x43dfc4159d86f3a37a5a4b3d4580b888ad7d4ddd'
ETH_VDODO                         = '\xc4436fbae6eba5d95bf7d53ae515f8a707bd402a'
ETH_DODO_CIRCULATION_HELPER       = '\x357c5e9cfa8b834edcef7c7aabd8f9db09119d11'
ETH_DODO_TEAM_MULTISIG            = '\x95c4f5b83aa70810d4f142d58e5f7242bd891cb0'
ETH_ERC20_MINE_V3_TEMPLATE        = '\xd57f29b297e33c977e2186a751414bfed6a38c5a'
ETH_DODO_MINE_V3_REGISTRY         = '\xf8ab09b3d2d5efa603f4646e5a8a12588e852195'
ETH_DODO_MINE_V3_PROXY            = '\x0d9685d4037580f68d9f77b08971f17e1000bbdc'  -- v1
ETH_DODO_INCENTIVE                = '\x989dcaa95801c527c5b73aa65d3962df9ace1b0c'

-- ===== BNB Smart Chain (chain ID 56) =====
BSC_DODO                          = '\x67ee3cb086f8a16f34bee3ca72fad36f7db929e2'  -- DODOBscToken (mint/burn)
BSC_VDODO                         = '\x4d6a41c682874e5dd1bbd58184ee8ff145c89202'
BSC_ERC20_MINE_V3_TEMPLATE        = '\xba428fc3c5ce457c236869787c26f725ff5168d8'
BSC_DODO_MINE_V3_REGISTRY         = '\x2a5aa99095e3724b8955bf7b5e47dbe2730dabd8'
BSC_DODO_MINE_V3_PROXY            = '\x3c39dcb3630d305530a30419b3deecea629597ac'  -- v1
BSC_DODO_INCENTIVE                = '\x4ee6398898f7fc3e648b3f6ba458310ac29cd352'

-- ===== Polygon PoS (chain ID 137) =====
POLY_DODO                         = '\xe4bf2864ebec7b7fdf6eeca9bacae7cdfdaffe78'  -- Matic UpgradeabilityProxy (impl 0x641a7567…)
POLY_ERC20_MINE_V3_TEMPLATE       = '\xda59427bd9d4827ec9f751719eb79b0a3e74fa4d'
POLY_DODO_MINE_V3_REGISTRY        = '\x27566bf9504466f6f3a1571e1863da42fff4d25e'
POLY_DODO_MINE_V3_PROXY           = '\x47a65e74dd6b6b5e3243dbb01eded9d55ba234ad'  -- v1

-- ===== Arbitrum One (chain ID 42161) =====
ARB_DODO                          = '\x69eb4fa4a2fbd498c257c57ea8b7655a2559a581'  -- EIP-1967 beacon proxy (beacon 0xe72ba941…)
ARB_ERC20_MINE_V2_TEMPLATE        = '\xe91067189c71db0696bd6fbc14535cb159f98b5c'
ARB_ERC20_MINE_V3_TEMPLATE        = '\x973cab76c35bb1da47e044a63546c69a8ac1143c'
ARB_DODO_MINE_V2_FACTORY          = '\x5a2e2278a0faccf224ced1ce809ec4e4b1708759'
ARB_DODO_MINE_V3_REGISTRY         = '\x2b40bc6c9c12c18787436aa1e2b761f684f42999'
ARB_DODO_MINE_V3_PROXY            = '\x9a74b169798be874ef1c23b4092e5689969ef45e'  -- v1

-- ===== Avalanche C-Chain (chain ID 43114) — no DODO token / vDODO / incentive =====
AVAX_ERC20_MINE_V3_TEMPLATE       = '\xf31162ef57b61d2fba4f64dbbac536bfc782d37c'
AVAX_DODO_MINE_V3_REGISTRY        = '\x0fe261aee0d1c4dfddee4102e82dd425999065f4'
AVAX_DODO_MINE_V3_PROXY           = '\x5d6e6a0bfb2176afcc4fb809822d8e009216b245'  -- v1

-- ===== Optimism (chain ID 10) — no DODO token / vDODO / incentive =====
OP_ERC20_MINE_V2_TEMPLATE         = '\x056927ac73e764247d9d2c41b8c321ea82ee468a'
OP_ERC20_MINE_V3_TEMPLATE         = '\x34229d00fb972e295359107c718eb621335fa596'
OP_DODO_MINE_V2_FACTORY           = '\xa36b345d087c14161d0b3fe1b96fd1cc551ce0c9'
OP_DODO_MINE_V3_REGISTRY          = '\x9ed110c929a1f9e4ae4fa8a88f7be5c2292d2a7f'
OP_DODO_MINE_V3_PROXY             = '\xaedbd08d92ecccaa9a93b1a8d66d1d356e470c78'  -- v1

-- ===== Base (chain ID 8453) — no DODO token / vDODO / incentive; v2 proxy =====
BASE_ERC20_MINE_V2_TEMPLATE       = '\xeac4bfef7d1c872ed705b01856af7f9802adc596'
BASE_ERC20_MINE_V3_TEMPLATE       = '\x04f7bae2a4c05cd567f762e33450debcebdc89ea'
BASE_DODO_MINE_V2_FACTORY         = '\xfd2b7994f91c08aaa5e013e899334a2dbb500df1'
BASE_DODO_MINE_V3_REGISTRY        = '\x8dd0fea5fa2f7df535f87f312641cc15d8b151ba'
BASE_DODO_MINE_V3_PROXY           = '\x2f66c5aaf006bd9c51615d617589c16c0ed35fd3'  -- v2 (platform field)

-- ===== Arbitrum DODO beacon (read impl from here) =====
ARB_DODO_BEACON                   = '\xe72ba9418b5f2ce0a6a40501fe77c6839aa37333'
```

---

## 14. Verification & sources

How every constant was verified (2026-06-02):

- **Canonical signatures:** `DODOEX/contractV2` source — `contracts/DODOToken/DODOToken.sol`, `DODOBscToken.sol`, `vDODOToken.sol`, `DODOCirculationHelper.sol`, `Governance.sol`, `DODOIncentive.sol`, `DODOMineV3/{BaseMine,ERC20MineV3,RewardVault}.sol`, `DODOMineV2/{BaseMine,ERC20Mine}.sol`, `Factory/Registries/DODOMineV3Registry.sol`, `Factory/DODOMineV2Factory.sol`, `SmartRoute/proxies/DODOMineV3Proxy.sol`. The deployed **v1** MineV3Proxy signature was taken from the historical source (commit `aebf0275bb`, 2021-06-09: 6-arg `createDODOMineV3`, `CreateMineV3(address,address)`); the **v2** form from `main`.
- **topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` (pycryptodome) — no param names, `uint`→`uint256`, `indexed` ignored.
- **Existence + proxy patterns:** `eth_getCode` and `eth_getStorageAt` on each chain's publicnode RPC. DODO token: ETH 1 995 B / BNB 3 773 B / Polygon 2 949 B / Arbitrum 760 B (beacon). EIP-1967 impl slot empty on vDODO, helper, incentive, registry (all 7), proxy (all 7), templates. Polygon `proxyType()`=2 / `implementation()`=`0x641a7567…`; Arbitrum **beacon slot** `0xa3f0ad74…` → beacon `0xe72b…7333` → impl `0x3f77…ad46`.
- **Live event cross-checks (`eth_getLogs`):** Ethereum vDODO — `MintVDODO` `0xb299178f…` (1 870 logs from block 11 891 013) and `RedeemVDODO` `0x10e8afa8…` confirmed (proves uppercase `VDODO` signatures). Ethereum registry — `NewMineV3` `0xcf56b383…` (block 13 169 792). Ethereum MineV3Proxy — `CreateMineV3(address,address)` `0xfc795fb7…` (block 13 169 792, 2-word data → the 2-arg v1 form). Ethereum DODOIncentive — `Incentive` `0xd427e26a…` + `SetPerReward` `0x2bce7061…` (active early 2021). A discovered ETH MineV3 clone (`0xa264dee4…`, 45 B EIP-1167) emitted `NewRewardToken` `0xf164ae82…`.
- **Live views (`eth_call`):** ETH DODO `decimals`=18, `symbol`="DODO", `totalSupply`=`1e9·1e18`; ETH/BNB vDODO `symbol`="vDODO"; ETH vDODO `_DODO_TOKEN_`=`0x43Df…`; CirculationHelper `getCirculation`≈711 M DODO, `getDodoWithdrawFeeRatio`=0.15e18; registry `isAdminListed(proxy)`=true; MineV3Proxy generation split confirmed by `createDODOMineV3` selector presence (`0x94852c61` Base / `0xb9b1135c` elsewhere) and `version()` (reverts off-Base).
- **Per-chain presence:** verified from the canonical deploy configs (`{eth,bsc,matic,arb,optimism,avax,base}-config.js`) and confirmed on-chain. DODO token on ETH/BNB/Polygon/Arbitrum only; vDODO + DODOIncentive on ETH/BNB only; MineV3 registry/proxy/template on all 7; MineV2 on Arbitrum/Optimism/Base.

Authoritative sources:
- [`DODOEX/contractV2`](https://github.com/DODOEX/contractV2) (`contracts/DODOToken/*`, `contracts/Factory/*`, `contracts/SmartRoute/proxies/DODOMineV3Proxy.sol`) · [DODO docs](https://docs.dodoex.io) · the DODO public address API.
- Explorers: [Etherscan DODO](https://etherscan.io/address/0x43Dfc4159D86F3A37A5A4B3D4580b888ad7d4DDd) · [Etherscan vDODO](https://etherscan.io/address/0xc4436fBAE6eBa5d95bf7d53Ae515F8A707Bd402A) · [BscScan DODO](https://bscscan.com/address/0x67ee3Cb086F8a16f34beE3ca72FAD36F7Db929e2) · [PolygonScan DODO](https://polygonscan.com/address/0xe4Bf2864ebeC7B7fDf6Eeca9BaCAe7cDfDAffe78) · [Arbiscan DODO](https://arbiscan.io/address/0x69Eb4FA4a2fbd498C257C57Ea8b7655a2559A581).
