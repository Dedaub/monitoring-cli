# Fluid (Instadapp) — Lending protocol & Liquidity Layer — Topics, Selectors, Addresses

**Status:** verified against the canonical `Instadapp/fluid-contracts-public` (branch `main`) source and live RPC on every listed chain on 2026-05-29. All topic0/selector hashes computed locally with keccak; all addresses confirmed via `eth_getCode`; proxy slots & per-selector dispatch confirmed via `eth_getStorageAt` / `eth_call`.
**Scope:** Fluid **Lending** ("Lend & Earn": fTokens, the ERC-4626 deposit side) and the **Liquidity Layer** it sits on, on **Ethereum (1), Base (8453), Arbitrum One (42161), Polygon PoS (137), BNB Smart Chain (56)**. Most material is chain-agnostic; addresses are network-specific.

> **Fluid is NOT deployed on Optimism (10) or Avalanche (43114).** The canonical repo's `deployments/` directory contains only `mainnet, arbitrum, base, polygon, bnb, plasma`. The cross-chain Liquidity proxy `0x52Aa…E497` has **no bytecode** on Optimism or Avalanche (verified). Any "Fluid on Optimism/Avalanche/Fantom" claim refers to legacy Instadapp DSA/Avocado infrastructure, not the Fluid Liquidity Layer / Lending protocol.
>
> **Note on BNB:** several analytics dashboards (Messari/Blockworks, as of ~Apr 2026) list Fluid only on Ethereum/Arbitrum/Base/Polygon and omit BNB. BNB is a newer deployment and IS live — verified here on-chain: Liquidity proxy + LendingFactory + 4 fTokens (fU, fUSDC, fUSDT, fWBNB) all have bytecode, with active `LogOperate` traffic. `plasma` also exists in the repo (out of scope for this doc). Treat the on-chain evidence as authoritative over dashboard listings.

## 0. Architecture in one screen

Fluid is several protocols on one shared **Liquidity Layer** that custodies *all* funds. Allow-listed protocols ("users", tracked per `_userClass`) interact with it through a single `operate(...)` entrypoint; every supply/withdraw/borrow/payback emits one `LogOperate`.

- **Liquidity Layer** — central vault. `FluidLiquidityProxy` (an InfiniteProxy, §6) at `0x52Aa…E497` on **every** Fluid chain. Behind it sit implementation *modules* (UserModule = `operate`, AdminModule = governance/config). It never faces end users directly.
- **Lending protocol** (the subject of this doc) = **`FluidLendingFactory`** + the **fTokens** it deploys. fTokens are ERC-20 + **ERC-4626** wrappers that are pure *suppliers* to the Liquidity Layer — they never custody funds (a deposit flows straight through to Liquidity via `liquidityCallback`). Yield (incl. rewards) accrues into the fToken→underlying **exchange price**, not via per-user reward claims.
- **Rewards** = one `FluidLendingRewardsRateModel` per reward program (can drive up to 3 fTokens). It only computes a rate; the fToken folds it into its exchange price.
- **Resolvers** = read-only helpers (`FluidLendingResolver`, `FluidLiquidityResolver`).
- **Vault** (borrow/collateral) and **DEX** (smart-collateral/debt AMM, incl. `SmartLending`/`fSL*`) are **separate products** — out of scope here, addresses labelled clearly where they share a registry.

**Versioning:** there is *no* on-chain v1/v2 of Lending. `FluidLendingFactory` is a plain non-upgradeable `Owned` contract; it extends by registering new `fTokenType` creation codes (SSTORE2) rather than redeploying. fTokens are non-upgradeable **CREATE3** deployments (salt `keccak256(abi.encode(asset, fTokenType))`) — a "new version" of an fToken is simply a new address. The Liquidity Layer is one continuously-governed InfiniteProxy that evolves by swapping per-selector implementation modules (`LogSetImplementation`/`LogRemoveImplementation`), never by redeploying the proxy. The repo's `deployments/<chain>/v1_0_0/` and mainnet `v1_1_0/` are deploy-batch snapshots, not protocol versions (`v1_1_0` mainnet = oracle deployments only).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Liquidity Layer — UserModule (the workhorse; one per supply/withdraw/borrow/payback)

| topic0 | Event |
|--------|-------|
| `0x4d93b232a24e82b284ced7461bf4deacffe66759d5c24513e6f29e571ad78d15` | `LogOperate(address indexed user, address indexed token, int256 supplyAmount, int256 borrowAmount, address withdrawTo, address borrowTo, uint256 totalAmounts, uint256 exchangePricesAndConfig)` |

`supplyAmount > 0` = deposit, `< 0` = withdrawal; `borrowAmount > 0` = borrow, `< 0` = payback. `user` is the *protocol* that triggered it (an fToken for Lending, or the Vault). `totalAmounts` / `exchangePricesAndConfig` are bit-packed storage slots (layout documented inline in source / decoded by `FluidLiquidityResolver`).

### 1.2 Liquidity Layer — AdminModule (governance / config; tuple args expanded for keccak)

| topic0 | Event |
|--------|-------|
| `0xb694cde8b4bf47e7f5845bb4374f98c5b29bbbaa5208ea679121cecb5d8fd3e0` | `LogUpdateAuths((address,bool)[] authsStatus)` |
| `0x530db3bf9b4b0c4f296fe1d9e21620b91db0a8bdcaca4cf1e6dc9844739405c1` | `LogUpdateGuardians((address,bool)[] guardiansStatus)` |
| `0xde3dd47a9a762713b4a9813a037ab6f57e36569d8b0ec4ddb285d8a61878b5b4` | `LogUpdateRevenueCollector(address indexed revenueCollector)` |
| `0xb33384c8a450936b9fba178db857f03fb9865a40d166aa2f9d439a9fdddfbe22` | `LogChangeStatus(uint256 indexed newStatus)` (pause / unpause) |
| `0x9ccbc3483d75ae36da94213ac30ac0a047e1226ef3435d004cd501608e5b388b` | `LogUpdateUserClasses((address,uint256)[] userClasses)` |
| `0xa9d5be7e168dc43b637b924e6cc22c262478dffd9d475fa170b6d4e4ba576460` | `LogUpdateTokenConfigs((address,uint256,uint256,uint256)[] tokenConfigs)` `{token,fee,threshold,maxUtilization}` |
| `0x614e3525ec8c152da9319cd9038950346a4a042d3c6810a7f3ffddc34347bdb0` | `LogUpdateUserSupplyConfigs((address,address,uint8,uint256,uint256,uint256)[])` `{user,token,mode,expandPercent,expandDuration,baseWithdrawalLimit}` |
| `0x4a3d512075def8d38b63e79dacfdab217654f641be2b2f7d638b67b2515df7c0` | `LogUpdateUserBorrowConfigs((address,address,uint8,uint256,uint256,uint256,uint256)[])` `{user,token,mode,expandPercent,expandDuration,baseDebtCeiling,maxDebtCeiling}` |
| `0x6686e5bb0cc56cbc9aa2b434eb18009891bf411d6d3f961fdfe70be336ca4528` | `LogPauseUser(address user, address[] supplyTokens, address[] borrowTokens)` |
| `0xacd30ef49b8fd1b51bbefff95071c5b0257180a7778c9c0fa4eb77a8842e290d` | `LogUnpauseUser(address user, address[] supplyTokens, address[] borrowTokens)` |
| `0x1f953465aa7f3f2478d38b6c2a9cfcfbda846398254e278f614d586d527d902c` | `LogUpdateRateDataV1s((address,uint256,uint256,uint256,uint256)[])` `{token,kink,rateAtUtilizationZero,...Kink,...Max}` |
| `0xf96f9120f802331b6220bac68c2ab90cce6c8a8f9fed548d72dd092ad1899bf9` | `LogUpdateRateDataV2s((address,uint256,uint256,uint256,uint256,uint256,uint256)[])` `{token,kink1,kink2,...Zero,...Kink1,...Kink2,...Max}` |
| `0x7ded56fbc1e1a41c85fd5fb3d0ce91eafc72414b7f06ed356c1d921823d4c37c` | `LogCollectRevenue(address indexed token, uint256 indexed amount)` |
| `0x96c40bed7fc8d0ac41633a3bd47f254f0b0076e5df70975c51d23514bc49d3b8` | `LogUpdateExchangePrices(address indexed token, uint256 indexed supplyExchangePrice, uint256 indexed borrowExchangePrice, uint256 borrowRate, uint256 utilization)` |
| `0xbd618a42c279f25a1d0dd6144f1a1b2ded22549073604bb0774cff6a99ee8428` | `LogUpdateUserWithdrawalLimit(address user, address token, uint256 newLimit)` |

### 1.3 InfiniteProxy (emitted by FluidLiquidityProxy and any other Fluid InfiniteProxy)

| topic0 | Event |
|--------|-------|
| `0xb2396a4169c0fac3eb0713eb7d54220cbe5e21e585a59578ec4de929657c0733` | `LogSetAdmin(address indexed oldAdmin, address indexed newAdmin)` |
| `0x761380f4203cd2fcc7ee1ae32561463bc08bbf6761cb9d5caa925f99a6d54502` | `LogSetDummyImplementation(address indexed oldDummyImplementation, address indexed newDummyImplementation)` |
| `0xd613a4a18e567ee1f2db4d5b528a5fee09f7dff92d6fb708afd6c095070a9c6d` | `LogSetImplementation(address indexed implementation, bytes4[] sigs)` |
| `0xda53aaefabec4c3f8ba693a2e3c67fa0152fbd71c369d51f669e66b28a4a0864` | `LogRemoveImplementation(address indexed implementation)` |

### 1.4 FluidLendingFactory

| topic0 | Event |
|--------|-------|
| `0x60c8487fc242a40cc8d2722cf9b3b5a14b316a50bf4ed30c9f0f1b0126728a36` | `LogTokenCreated(address indexed token, address indexed asset, uint256 indexed count, string fTokenType)` |
| `0x014b54fa6d2080e9aacd1c598c7689a625610d7d684dd41d10407e48aa8b1200` | `LogSetAuth(address indexed auth, bool indexed allowed)` |
| `0x48cc5b4660fae22eabe5e803ee595e63572773d114bcd54ecc118c1efa8d75af` | `LogSetDeployer(address indexed deployer, bool indexed allowed)` |
| `0x93dad940f342b3cd95007806ae0cb0c162dbbfba54d55223bc6d055c62e608e0` | `LogSetFTokenCreationCode(string indexed fTokenType, address indexed creationCodePointer)` |

Subscribe to `LogTokenCreated` from the factory to discover every fToken on a chain. `count` = 1-based index in `allTokens()`. `fTokenType` is `"fToken"` (standard) or `"NativeUnderlying"` (wrapped-native).

### 1.5 fToken (per ERC-4626 lending token)

| topic0 | Event |
|--------|-------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address indexed sender, address indexed owner, uint256 assets, uint256 shares)` *(ERC-4626)* |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address indexed sender, address indexed receiver, address indexed owner, uint256 assets, uint256 shares)` *(ERC-4626)* |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` *(ERC-20)* |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` *(ERC-20)* |
| `0x9dd85e9767d796973b86c6ccf3a294429cfd5e3e93fa23ac388b9277bb8283fd` | `LogUpdateRates(uint256 tokenExchangePrice, uint256 liquidityExchangePrice)` — *maintenance-only, rare* |
| `0xe97ad8b810ae9d9e29aa69dc04d4ac2e3e71d65307830ccb97c8f876dfc43931` | `LogRebalance(uint256 assets)` — rebalancer funds reward gap |
| `0xd14b198a72267efb36b8bbc193eb6d52a00d1f61799029250f6a520ad47be82d` | `LogUpdateRewards(address indexed rewardsRateModel)` |
| `0xdff2a3947bcf9fc0807b142e7c8497066db9183428b7bdbfb1fcd0f55c27a3df` | `LogRescueFunds(address indexed token)` |
| `0xdb94ee7fd8b5bbf8f6d59e76731ff4b4f5a02ab3af1d3e0c774862cf96ff613b` | `LogUpdateRebalancer(address indexed rebalancer)` |

Normal user activity emits only `Deposit` / `Withdraw` / `Transfer` / `Approval` (verified: a fUSDC window had exactly those four and none of the `Log*` events). `LogUpdateRates`/`LogRebalance`/`LogUpdateRewards`/`LogRescueFunds`/`LogUpdateRebalancer` are admin/maintenance events. There is **no** `LogClaimReward` — rewards are not per-user-claimed; they accrue into the exchange price.

### 1.6 FluidLendingRewardsRateModel

| topic0 | Event |
|--------|-------|
| `0xf847e1fc85baf05c769b3bc2f2dc3384d56aca28c9894497717c6c1383b098af` | `LogStartRewards(uint256 rewardAmount, uint256 duration, uint256 startTime)` |
| `0x0ba629f001023d2b4b32157343614f17651d8508c3c6c1bfa5769925cb718c0e` | `LogStopRewards()` |
| `0x68ef2ad282a305bd5b41f780462102ad9fc40964ab6097401fcc6eb0ebefae87` | `LogQueueNextRewards(uint256 rewardAmount, uint256 duration)` |
| `0x13d39d3c3c727cbaa38766164c6fb182ddfb8daaaf4e68d19b0095cd7927a1af` | `LogCancelQueuedRewards()` |
| `0xa27da0b2cea36637915acc9460cc212a1eb5ad386e422cfc9f40e5f4014e222f` | `LogTransitionedToNextRewards(uint256 startTime, uint256 endTime)` |

---

## 2. Function signatures (chain-agnostic)

Selectors = `keccak256(canonical signature)[0:4]`, verified against deployed dispatcher bytecode (fToken, factory) or live per-selector dispatch (Liquidity).

### 2.1 Liquidity Layer (UserModule + InfiniteProxy admin/getters)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xad967e15` | `operate(address token, int256 supplyAmount, int256 borrowAmount, address withdrawTo, address borrowTo, bytes callbackData)` | Sole user entrypoint. Returns `(uint256 memVar1, uint256 memVar2)`. Emits `LogOperate`. Live dispatch → UserModule (read it, don't assume). |
| `0x6e9960c3` | `getAdmin()` | proxy admin (governance). |
| `0x908bfe5e` | `getDummyImplementation()` | the EIP-1967-impl-slot value (ABI stub). |
| `0xa5fcc8bc` | `getSigsImplementation(bytes4 sig_)` | **the authoritative selector→implementation lookup.** |
| `0x89396dc8` | `getImplementationSigs(address impl_)` | `bytes4[]` registered for an impl. |
| `0xb5c736e4` | `readFromStorage(bytes32 slot_)` | raw `sload`. |
| `0x704b6c02` | `setAdmin(address)` | onlyAdmin. Emits `LogSetAdmin`. |
| `0xc39aa07d` | `setDummyImplementation(address)` | onlyAdmin. |
| `0xf0c01b42` | `addImplementation(address, bytes4[])` | onlyAdmin. Emits `LogSetImplementation`. |
| `0x22175a32` | `removeImplementation(address)` | onlyAdmin. Emits `LogRemoveImplementation`. |

### 2.2 FluidLendingFactory

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe78e049a` | `createToken(address asset, string fTokenType, bool isNativeUnderlying)` | onlyDeployers. Returns `address token`. CREATE3. Emits `LogTokenCreated`. |
| `0xbb4a64d3` | `computeToken(address asset, string fTokenType)` | deterministic address (off-chain reproducible). |
| `0x6ff97f1d` | `allTokens()` | `address[]` of every fToken. |
| `0xdd179e3b` | `fTokenTypes()` | `string[]` of registered types. |
| `0xc949aea6` | `fTokenCreationCode(string fTokenType)` | `bytes` (read from SSTORE2). |
| `0xf6015079` | `setFTokenCreationCode(string, bytes)` | onlyAuths. Emits `LogSetFTokenCreationCode`. |
| `0x0b44a218` | `setAuth(address, bool)` | onlyOwner. Emits `LogSetAuth`. |
| `0xa34b5ee8` | `setDeployer(address, bool)` | onlyOwner. Emits `LogSetDeployer`. |
| `0x2520e7ff` | `isAuth(address)` | |
| `0x50c358a4` | `isDeployer(address)` | |
| `0x2861c7d1` | `LIQUIDITY()` | the immutable Liquidity address bound at deploy. |

### 2.3 fToken (ERC-4626 + Fluid extensions; standard `"fToken"` type)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6e553f65` | `deposit(uint256 assets, address receiver)` | ERC-4626. Returns `shares`. |
| `0xbc157ac1` | `deposit(uint256 assets, address receiver, uint256 minAmountOut)` | slippage-guarded. |
| `0x94bf804d` | `mint(uint256 shares, address receiver)` | ERC-4626. |
| `0x836a1040` | `mint(uint256 shares, address receiver, uint256 maxAssets)` | |
| `0xb460af94` | `withdraw(uint256 assets, address receiver, address owner)` | ERC-4626. |
| `0xa318c1a4` | `withdraw(uint256 assets, address receiver, address owner, uint256 maxSharesBurn)` | |
| `0xba087652` | `redeem(uint256 shares, address receiver, address owner)` | ERC-4626. |
| `0x9f40a7b3` | `redeem(uint256 shares, address receiver, address owner, uint256 minAmountOut)` | |
| `0x635c31c2` | `depositWithSignature(uint256 assets, address receiver, uint256 minAmountOut, ((address,uint160,uint48,uint48),address,uint256) permit, bytes signature)` | Permit2 `PermitSingle`. |
| `0x8c87483a` | `mintWithSignature(uint256 shares, address receiver, uint256 maxAssets, ((address,uint160,uint48,uint48),address,uint256) permit, bytes signature)` | Permit2. |
| `0x50cc0f8f` | `withdrawWithSignature(uint256 sharesToPermit, uint256 assets, address receiver, address owner, uint256 maxSharesBurn, uint256 deadline, bytes signature)` | EIP-2612 on fToken shares. |
| `0x740c955e` | `redeemWithSignature(uint256 shares, address receiver, address owner, uint256 minAmountOut, uint256 deadline, bytes signature)` | EIP-2612. |
| `0x3bc5de30` | `getData()` | 9-tuple: liquidity, lendingFactory, rewardsRateModel, permit2, rebalancer, rewardsActive, liquidityBalance, liquidityExchangePrice, tokenExchangePrice. |
| `0x01e1d114` | `totalAssets()` | |
| `0x38d52e0f` | `asset()` | underlying. |
| `0x41b3d185` | `minDeposit()` | |
| `0x3c3821f4` | `updateRates()` | anyone. Writes exchange prices; emits `LogUpdateRates`. Returns `(tokenExchangePrice, liquidityExchangePrice)`. |
| `0x7d7c2a1c` | `rebalance()` | `payable`, rebalancer-only. Funds the gap as rewards (no shares minted). Emits `LogRebalance`. |
| `0x5fd61965` | `updateRewards(address rewardsRateModel)` | LendingFactory auth. Emits `LogUpdateRewards`. |
| `0xb046a449` | `updateRebalancer(address)` | LendingFactory auth. Emits `LogUpdateRebalancer`. |
| `0xe53b2017` | `rescueFunds(address token)` | LendingFactory auth. Emits `LogRescueFunds`. |
| `0xad207501` | `liquidityCallback(address token, uint256 amount, bytes data)` | Liquidity-only; pulls underlying from original depositor. |

Plus standard ERC-4626 views `convertToShares 0xc6e6f592`, `convertToAssets 0x07a2d13a`, `previewDeposit 0xef8b30f7`, `previewMint 0xb3d7f6b9`, `previewWithdraw 0x0a28a477`, `previewRedeem 0x4cdad506`, `maxDeposit 0x402d267d`, `maxMint 0xc63d75b6`, `maxWithdraw 0xce96cb77`, `maxRedeem 0xd905777e`, and ERC-20 `transfer/approve/...`.

### 2.4 fTokenNativeUnderlying (wrapped-native fTokens: fWETH, fWPOL, fWBNB)

Adds native-coin entrypoints. `0xEeee…EEeE` is the Liquidity NATIVE token sentinel.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x33bb7f91` | `depositNative(address receiver)` | `payable`. |
| `0x02279b4a` | `depositNative(address receiver, uint256 minAmountOut)` | `payable`. |
| `0x80541187` | `mintNative(uint256 shares, address receiver, uint256 maxAssets)` | `payable`. |
| `0x2126e91e` | `withdrawNative(uint256 assets, address receiver, address owner)` | |
| `0xeb26620c` | `withdrawNative(uint256 assets, address receiver, address owner, uint256 maxSharesBurn)` | |
| `0x3badef91` | `redeemNative(uint256 shares, address receiver, address owner)` | |
| `0x2ae06214` | `redeemNative(uint256 shares, address receiver, address owner, uint256 minAmountOut)` | |
| `0xf5a35aaa` | `withdrawWithSignatureNative(uint256 sharesToPermit, uint256 assets, address receiver, address owner, uint256 maxSharesBurn, uint256 deadline, bytes signature)` | |
| `0xe3597548` | `redeemWithSignatureNative(uint256 shares, address receiver, address owner, uint256 minAmountOut, uint256 deadline, bytes signature)` | |
| `0xdf2ebdbb` | `NATIVE_TOKEN_ADDRESS()` | returns `0xEeee…EEeE`. |

> `mintNative(uint256,address)` (2-arg, selector `0x00acb736`) is declared in current `main` source but is **not present** in the deployed mainnet fWETH bytecode (only the 3-arg `mintNative` `0x80541187` is) — a version drift between the live deployment and HEAD. Treat the 3-arg form as canonical for the deployed contracts.

### 2.5 FluidLendingRewardsRateModel

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x57764094` | `getRate(uint256 totalAssets)` | `(rate, ended, startTime)`. 1e12 = 1%. |
| `0xc3f909d4` | `getConfig()` | `(duration, startTime, endTime, startTvl, maxRate, rewardAmount, initiator)`. |
| `0x6283311d` | `startRewards(uint256 rewardAmount, uint256 duration, uint256 startTime)` | onlyConfigurator. Emits `LogStartRewards`. |
| `0x797008c6` | `stopRewards()` | onlyConfigurator. Emits `LogStopRewards`. |
| `0x06786dd1` | `queueNextRewards(uint256 rewardAmount, uint256 duration)` | onlyConfigurator. Emits `LogQueueNextRewards`. |
| `0x0aa9a12b` | `cancelQueuedRewards()` | onlyConfigurator. |
| `0xad759a92` | `transitionToNextRewards()` | callable by anyone. Emits `LogTransitionedToNextRewards`. |

---

## 3. Addresses — shared across all Fluid chains (deterministic CREATE3)

These core addresses are **identical on Ethereum, Base, Arbitrum, Polygon, BNB** (verified `eth_getCode` non-empty on each). Per-chain divergence (modules, dummy impl, admin, fTokens) is in §4–§5.

| Role | Address | One-liner |
|------|---------|-----------|
| **Liquidity (FluidLiquidityProxy)** | `0x52Aa899454998Be5b000Ad077a46Bbe360F4e497` | Core Liquidity Layer (InfiniteProxy). All Lending/Vault/DEX liquidity routes through it. `code=4462 B` on every chain. |
| **FluidLendingFactory** | `0x54B91A0D94cb471F37f949c60F7Fa7935b551D03` | Deploys fTokens (CREATE3). Non-upgradeable `Owned`. `code=8305 B`. |
| **FluidLendingResolver** | `0x48D32f49aFeAEC7AE66ad7B9264f446fc11a1569` | Read helper for fTokens/lending. `code=10757 B`. |
| **FluidLiquidityResolver** | `0xca13A15de31235A37134B4717021C35A3CF25C60` | Decodes packed Liquidity storage. `code=12803 B`. |
| **RevenueResolver** | `0x0A84741D50B4190B424f57425b09FAe60C330F32` | Revenue/reserve read resolver. |
| **ReserveContractProxy** | `0x264786EF916af64a1DB19F513F24a3681734ce92` | Reserve & governance auth / revenue collector. Minimal proxy (`code=190 B`). The fToken rebalancer. |
| SmartLendingResolver | `0x3E69A3Af4305b65598b228d3da70786Bd9cfeB0e` | DEX-backed "smart lending" resolver. On ETH/Base/Arb/Polygon only — **BNB uses `0x1446dEc487B4411DE222547ADbC3b3e01933787f`** instead. |
| VaultFactory *(Vault, not Lending)* | `0x324c5Dc1fC42c7a4D43d92df1eBA58a54d13Bf2d` | Deploys Fluid Vaults. |
| DexFactory *(DEX, not Lending)* | `0x91716C4EDA1Fb55e84Bf8b4c7085f84285c19085` | Deploys Fluid DEX pools. |

Deployer/owner (all chains): `0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e`. Team/governance multisig (Liquidity constructor arg): `0xCA5E9219e1007931FD5d938C1815a90ef08f1584`.

---

## 4. Per-chain Liquidity-Layer modules, dummy impl & admin

The proxy address is shared, but its **EIP-1967 dummy-impl slot, admin slot, and registered modules differ per chain** — read them live, don't assume. Values below verified via `eth_getStorageAt` / live `getSigsImplementation(operate)` on 2026-05-29.

| Chain | Proxy admin (governance) `getAdmin()` | DummyImpl (impl slot) | Live `operate` impl (UserModule) |
|-------|----------------------------------------|------------------------|----------------------------------|
| Ethereum (1) | `0x2386dc45added673317ef068992f19421b481f4c` | `0xcc331daf69752bece3dc98dbc63eacd5092266a2` | `0x4bdc8816f2f56914b66ebf3786d78872d3a73ab7` |
| Base (8453) | `0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e` | `0xa57D7CeF617271F4cEa4f665D33ebcFcBA4929f6` | `0x3c06514287e74ede035d293362a2369bDa60E642` |
| Arbitrum (42161) | `0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e` | `0xa57D7CeF617271F4cEa4f665D33ebcFcBA4929f6` | `0x3c06514287e74ede035d293362a2369bDa60E642` |
| Polygon (137) | `0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e` | `0xa57D7CeF617271F4cEa4f665D33ebcFcBA4929f6` | `0x3c06514287e74ede035d293362a2369bDa60E642` |
| BNB (56) | `0x1c0fc15e0db6960a9a688dda8ee2cfdd54f45cc0` | `0x3560a1d1E9F30b61cd0E24349f7a23890f6261D9` | `0x3c06514287e74ede035d293362a2369bDa60E642` |

`0xa57D7CeF…4929f6` is the originally-deployed `LiquidityDummyImpl`. **Mainnet has since upgraded** its dummy impl to `0xcc331daf…` (its admin is also the governance multisig, not the deployer) — a real signal that mainnet is the most-governed instance. AdminModule addresses from the deploy registry: ETH `0x53EFFA0e612d88f39Ab32eb5274F2fae478d261C`, Base/Arb `0x48eeDDF09565338B62126214c5a85E863C197e4D`, Polygon `0xb74EbF69fe16292df8943964507c59f99765AEd9`, BNB `0xE1CCc6E5FB4684Abb23b71ce6F44f76ffe3a33B0`. (Registry UserModule on mainnet `0x2e40…46aD` is stale vs the live `operate` impl `0x4bdc88…3ab7`.) Mainnet also has a `ZircuitTransferModule` `0x9191b9539DD588dB81076900deFDd79Cb1115f72`.

---

## 5. fTokens & rewards-rate-models — per chain

All fToken addresses verified `eth_getCode` non-empty. Standard `"fToken"` runtime = **19617 B**; native-underlying = **21098 B** (a clean way to tell them apart on-chain).

### 5.1 Ethereum (1)

| fToken | Address | Underlying | Underlying addr | RewardsRateModel |
|--------|---------|-----------|-----------------|------------------|
| fUSDC | `0x9Fb7b4477576Fe5B32be4C1843aFB1e55F251B33` | USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | `0xb75Ec31fd7ad0D823A801be8740B9Fad299ce6d6` |
| fUSDT | `0x5C20B550819128074FD538Edf79791733ccEdd18` | USDT | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | `0x19147A180D271d90dC12Da2BFFC636F54Cf7C241` |
| fWETH *(native)* | `0x90551c1795392094FE6D29B758EcCD233cFAa260` | WETH/ETH | `0xC02aaA39…C756Cc2` | — |
| fwstETH | `0x2411802D8BEA09be0aF8fD8D08314a63e706b29C` | wstETH | `0x7f39C581…35E2Ca0` | — |
| fGHO | `0x6A29A46E21C730DcA1d8b23d637c101cec605C5B` | GHO | `0x40D16FC0…28aE6C2f` | `0x95755A4552690a53d7360B7e16155867868ae964` |
| fsUSDS | `0x2BBE31d63E6813E3AC858C04dae43FB2a72B0D11` | sUSDS | `0xa3931d71…Fec27fbD` | — |
| fUSDtb | `0x15e8c742614b5D8Db4083A41Df1A14F5D2bFB400` | USDtb | `0xC139190F…8b18aC1C` | — |

### 5.2 Base (8453)

| fToken | Address | Underlying | RewardsRateModel |
|--------|---------|-----------|------------------|
| fUSDC | `0xf42f5795D9ac7e9D757dB633D693cD548Cfd9169` | USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | `0xFB10c86A7E9d93105f291968E83dA0b54e2Ef5f0` |
| fWETH *(native)* | `0x9272D6153133175175Bc276512B2336BE3931CE9` | WETH `0x4200…0006` | — |
| fwstETH | `0x896E39f0E9af61ECA9dD2938E14543506ef2c2b5` | wstETH `0xc1CBa3fC…0ee452` | — |
| fEURC | `0x1943FA26360f038230442525Cf1B9125b5DCB401` | EURC `0x60a3E35C…b1adb42` | `0xA4a5f550c16f53d4F463832d16F428Cdc4017Bfb` |
| fGHO | `0x8DdbfFA3CFda2355a23d6B11105AC624BDbE3631` | GHO `0x6Bb7a212…8da10Ee` | — |
| fsUSDS | `0xf62e339f21d8018940f188F6987Bcdf02A849619` | sUSDS `0x5875eEE1…675467a` | — |

### 5.3 Arbitrum One (42161)

| fToken | Address | Underlying | RewardsRateModel |
|--------|---------|-----------|------------------|
| fUSDC | `0x1A996cb54bb95462040408C06122D45D6Cdb6096` | USDC `0xaf88d065…68e5831` | `0xFC41281d62dd25C446b26dB7C8f33Ec6c55239e4` |
| fUSDT | `0x4A03F37e7d3fC243e3f99341d36f4b829BEe5E03` | USDT `0xFd086bC7…9FCbb9` | `0xf5cd56Cbe9753534F54bdc3DC90170A437Cc323a` |
| fWETH *(native)* | `0x45Df0656F8aDf017590009d2f1898eeca4F0a205` | WETH `0x82aF4944…23fBab1` | — |
| fwstETH | `0x66C25Cd75EBdAA7E04816F643d8E46cecd3183c9` | wstETH `0x5979D7b5…A4800529` | — |
| fweETH | `0x0D00C4A2f766b7AFE2cc8F6467E296400A32B239` | weETH `0x35751007…2cf4dbe` | — |
| fARB | `0xbE3860FD4c3facDf8ad57Aa8c1A36D6dc4390a49` | ARB `0x912CE591…49E6548` | — |
| fGHO | `0x037dFf1C12805707d7c29F163E0F09fC9102657A` | GHO `0x7dfF7269…7c8B33` | — |
| fsUSDS | `0x3459fcc94390C3372c0F7B4cD3F8795F0E5aFE96` | sUSDS `0xdDb46999…16d7610` | — |

### 5.4 Polygon PoS (137)

| fToken | Address | Underlying | RewardsRateModel |
|--------|---------|-----------|------------------|
| fAUSD | `0xd70dD80Bc39d56E21A4475F72021BC6C5B0E4518` | AUSD `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` | — |
| fUSDC | `0x571d456b578fDC34E26E6D636736ED7c0CDB9d89` | USDC `0x3c499c54…3d5c3359` | — |
| fUSDT | `0x6f5e34eFf43D9ab7c977512509C53840B5EfBA85` | USDT `0xc2132D05…B58e8F` | — |
| fWETH | `0xD3154535E4D0e179583ad694859E4e876EB12d24` | WETH `0x7ceB23fD…1b9f619` | — |
| fWPOL *(native)* | `0x41b8B33A413681CB7d869D287E99C30c6DF775b9` | WPOL/WMATIC `0x0d500B1d…3ADf1270` | — |
| fwstETH | `0x8C618d33463f10DDAeCbA2739fCfb25d58C23243` | wstETH `0x03b54A6e…3B3bCCD` | — |

*(No per-fToken RewardsRateModel deployed on Polygon at time of writing.)*

### 5.5 BNB Smart Chain (56)

| fToken | Address | Underlying | RewardsRateModel |
|--------|---------|-----------|------------------|
| fU | `0x007df53Cda786450Cf8145a73B2748B241a0069c` | U `0xcE24439F…B666666` | `0xbaFe938aEE7b0E1efe7D488905710F3C99eCb36A` |
| fUSDC | `0xfE60462E93cee34319F48Cfc6AcFbc13c2882Df9` | USDC `0x8AC76a51…32Cd580d` | `0x149747813e1A5b04B5F17869b9d6603022B591fd` |
| fUSDT | `0xA5b8FCa32E5252B0B58EAbf1A8c79d958F8EE6A2` | USDT(BSC-USD) `0x55d39832…3197955` | `0xBE02b3DA446BF1B5CB271553F162A0f7C92E90bD` |
| fWBNB *(native)* | `0x527C2a0B8A3eDD9696B4A9443ef66Ec30fD7B84a` | WBNB `0xbb4CdB9C…73bc095c` | — |

BNB RewardsRateModel runtime is larger (`5547 B` vs `1820 B` on other chains) — a newer model build; same `getRate`/`getConfig` interface.

---

## 6. Proxies — the Fluid "InfiniteProxy" (read carefully)

`FluidLiquidityProxy` (and Vault/DEX cores) use Fluid's **InfiniteProxy** (`contracts/infiniteProxy/proxy.sol`), a multi-implementation delegatecall router. **fTokens, the LendingFactory, resolvers and the RewardsRateModels are NOT proxies** — they are plain CREATE3/normal contracts (fToken "upgrade" = new address).

**Slots (standard EIP-1967 — reused):**
- Admin: `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` (`keccak256("eip1967.proxy.admin")-1`).
- Dummy implementation: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` (`keccak256("eip1967.proxy.implementation")-1`). **Holds only an ABI-stub "dummy" impl** so explorers can introspect — it is *not* what `delegatecall` actually targets.
- Per-selector base: `_SIG_SLOT_BASE = 0x000000003ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` (the impl slot with the top 4 bytes zeroed). The implementation for a selector lives at `_SIG_SLOT_BASE | bytes4(selector)` (selector occupies the top 4 bytes).

**Dispatch:** `fallback()` reads `msg.sig`, ORs it into `_SIG_SLOT_BASE`, `sload`s the impl address from that slot, and `delegatecall`s it (reverts if zero). There is **no** central mapping struct — the selector→impl map *is* the storage layout. Two helper-slot families: `keccak256(abi.encode("eip1967.proxy.implementation", impl))` stores the `bytes4[]` registered for an impl; `_SIG_SLOT_BASE | sig` stores the impl for a selector.

**Read which impl serves a call:** `getSigsImplementation(bytes4)` (`0xa5fcc8bc`) — e.g. `getSigsImplementation(0xad967e15)` → UserModule. `getImplementationSigs(address)` (`0x89396dc8`) for the reverse. `getDummyImplementation()`/`getAdmin()` for the EIP-1967 slots.

**ReserveContractProxy** `0x264786…ce92` is a *separate*, tiny minimal proxy (`code=190 B`), not an InfiniteProxy.

---

## 7. Detection invariants & gotchas

1. **One `LogOperate` per Lending action, emitted by the Liquidity proxy — not by the fToken.** A user deposit into fUSDC emits: fUSDC `Deposit` + fUSDC `Transfer` (mint) + Liquidity `LogOperate` (with `user = fUSDC address`, `supplyAmount > 0`). To attribute Liquidity flows to Lending, map `LogOperate.user ∈ allTokens()`.
2. **`LogOperate.user` is the protocol, never the end user.** The end user is in the fToken `Deposit.owner` / the underlying-token `Transfer.from`. For Vault flows `user` is the Vault; same topic, different protocol — disambiguate by which contract `user` is.
3. **fTokens never hold the underlying.** Underlying flows depositor → Liquidity directly via `liquidityCallback`. Don't expect the fToken's underlying balance to track deposits (it's ~0); use `totalAssets()` / `getData()`.
4. **Yield & rewards accrue into the exchange price**, not via claim events. `tokenExchangePrice` (fToken→underlying) rises over time. There is no `LogClaimReward` and no per-user reward event. The only reward-program events are on the `FluidLendingRewardsRateModel` (`LogStartRewards` etc.) and the fToken `LogUpdateRewards` (model address change).
5. **`LogUpdateRates`/`LogRebalance` are rare maintenance events**, not per-deposit. A normal fToken window emits only ERC-4626 `Deposit/Withdraw` + ERC-20 `Transfer/Approval`. Don't rely on `LogUpdateRates` to track APY — read exchange prices via `getData()`/resolver.
6. **The Liquidity proxy address is identical on every Fluid chain** (`0x52Aa…E497`), but its admin, dummy impl, and live module set differ per chain — always resolve modules with `getSigsImplementation`, never hardcode a module address.
7. **`getDummyImplementation()` ≠ the executing implementation.** The EIP-1967 impl slot holds an ABI stub. Tools that read that slot to "find the logic" get the wrong contract for InfiniteProxies — use the per-selector slot instead.
8. **Native vs standard fToken is detectable by bytecode size** (21098 B native-underlying vs 19617 B standard) and by the presence of `depositNative`/`NATIVE_TOKEN_ADDRESS`. The wrapped-native fToken on each chain is fWETH (ETH/Base/Arb), fWPOL (Polygon), fWBNB (BNB).
9. **fToken address is deterministic** = CREATE3 of `salt = keccak256(abi.encode(asset, fTokenType))` from the factory — reproducible off-chain via `computeToken(asset, fTokenType)`.
10. **Live deployments can lag HEAD source.** Mainnet fWETH lacks the 2-arg `mintNative` that's in current `main`; mainnet's dummy impl and `operate` module differ from the deploy-registry snapshot. When a selector/module matters, verify against the live contract, not the repo file.
11. **Fluid is not on Optimism or Avalanche.** Don't index `0x52Aa…E497` there — no code.
12. **`AddressBool[]`/struct-array admin events**: topic0s in §1.2 were computed with the tuple types *expanded* (e.g. `LogUpdateAuths((address,bool)[])`). Using the Solidity struct name instead of the expanded tuple gives a wrong hash.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- Liquidity UserModule
TOPIC_LIQ_OPERATE                = '\x4d93b232a24e82b284ced7461bf4deacffe66759d5c24513e6f29e571ad78d15'
-- Liquidity AdminModule
TOPIC_ADMIN_UPDATE_AUTHS         = '\xb694cde8b4bf47e7f5845bb4374f98c5b29bbbaa5208ea679121cecb5d8fd3e0'
TOPIC_ADMIN_UPDATE_GUARDIANS     = '\x530db3bf9b4b0c4f296fe1d9e21620b91db0a8bdcaca4cf1e6dc9844739405c1'
TOPIC_ADMIN_UPDATE_REVENUE_COLL  = '\xde3dd47a9a762713b4a9813a037ab6f57e36569d8b0ec4ddb285d8a61878b5b4'
TOPIC_ADMIN_CHANGE_STATUS        = '\xb33384c8a450936b9fba178db857f03fb9865a40d166aa2f9d439a9fdddfbe22'
TOPIC_ADMIN_UPDATE_USER_CLASSES  = '\x9ccbc3483d75ae36da94213ac30ac0a047e1226ef3435d004cd501608e5b388b'
TOPIC_ADMIN_UPDATE_TOKEN_CONFIGS = '\xa9d5be7e168dc43b637b924e6cc22c262478dffd9d475fa170b6d4e4ba576460'
TOPIC_ADMIN_UPDATE_SUPPLY_CFG    = '\x614e3525ec8c152da9319cd9038950346a4a042d3c6810a7f3ffddc34347bdb0'
TOPIC_ADMIN_UPDATE_BORROW_CFG    = '\x4a3d512075def8d38b63e79dacfdab217654f641be2b2f7d638b67b2515df7c0'
TOPIC_ADMIN_PAUSE_USER           = '\x6686e5bb0cc56cbc9aa2b434eb18009891bf411d6d3f961fdfe70be336ca4528'
TOPIC_ADMIN_UNPAUSE_USER         = '\xacd30ef49b8fd1b51bbefff95071c5b0257180a7778c9c0fa4eb77a8842e290d'
TOPIC_ADMIN_UPDATE_RATE_DATA_V1  = '\x1f953465aa7f3f2478d38b6c2a9cfcfbda846398254e278f614d586d527d902c'
TOPIC_ADMIN_UPDATE_RATE_DATA_V2  = '\xf96f9120f802331b6220bac68c2ab90cce6c8a8f9fed548d72dd092ad1899bf9'
TOPIC_ADMIN_COLLECT_REVENUE      = '\x7ded56fbc1e1a41c85fd5fb3d0ce91eafc72414b7f06ed356c1d921823d4c37c'
TOPIC_ADMIN_UPDATE_EXCH_PRICES   = '\x96c40bed7fc8d0ac41633a3bd47f254f0b0076e5df70975c51d23514bc49d3b8'
TOPIC_ADMIN_UPDATE_USER_WD_LIMIT = '\xbd618a42c279f25a1d0dd6144f1a1b2ded22549073604bb0774cff6a99ee8428'
-- InfiniteProxy
TOPIC_PROXY_SET_ADMIN            = '\xb2396a4169c0fac3eb0713eb7d54220cbe5e21e585a59578ec4de929657c0733'
TOPIC_PROXY_SET_DUMMY_IMPL       = '\x761380f4203cd2fcc7ee1ae32561463bc08bbf6761cb9d5caa925f99a6d54502'
TOPIC_PROXY_SET_IMPL             = '\xd613a4a18e567ee1f2db4d5b528a5fee09f7dff92d6fb708afd6c095070a9c6d'
TOPIC_PROXY_REMOVE_IMPL          = '\xda53aaefabec4c3f8ba693a2e3c67fa0152fbd71c369d51f669e66b28a4a0864'
-- LendingFactory
TOPIC_LF_TOKEN_CREATED           = '\x60c8487fc242a40cc8d2722cf9b3b5a14b316a50bf4ed30c9f0f1b0126728a36'
TOPIC_LF_SET_AUTH                = '\x014b54fa6d2080e9aacd1c598c7689a625610d7d684dd41d10407e48aa8b1200'
TOPIC_LF_SET_DEPLOYER            = '\x48cc5b4660fae22eabe5e803ee595e63572773d114bcd54ecc118c1efa8d75af'
TOPIC_LF_SET_FTOKEN_CODE         = '\x93dad940f342b3cd95007806ae0cb0c162dbbfba54d55223bc6d055c62e608e0'
-- fToken
TOPIC_FT_DEPOSIT                 = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_FT_WITHDRAW                = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_ERC20_APPROVAL             = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_FT_UPDATE_RATES            = '\x9dd85e9767d796973b86c6ccf3a294429cfd5e3e93fa23ac388b9277bb8283fd'
TOPIC_FT_REBALANCE               = '\xe97ad8b810ae9d9e29aa69dc04d4ac2e3e71d65307830ccb97c8f876dfc43931'
TOPIC_FT_UPDATE_REWARDS          = '\xd14b198a72267efb36b8bbc193eb6d52a00d1f61799029250f6a520ad47be82d'
TOPIC_FT_RESCUE_FUNDS            = '\xdff2a3947bcf9fc0807b142e7c8497066db9183428b7bdbfb1fcd0f55c27a3df'
TOPIC_FT_UPDATE_REBALANCER       = '\xdb94ee7fd8b5bbf8f6d59e76731ff4b4f5a02ab3af1d3e0c774862cf96ff613b'
-- RewardsRateModel
TOPIC_RR_START                   = '\xf847e1fc85baf05c769b3bc2f2dc3384d56aca28c9894497717c6c1383b098af'
TOPIC_RR_STOP                    = '\x0ba629f001023d2b4b32157343614f17651d8508c3c6c1bfa5769925cb718c0e'
TOPIC_RR_QUEUE_NEXT              = '\x68ef2ad282a305bd5b41f780462102ad9fc40964ab6097401fcc6eb0ebefae87'
TOPIC_RR_CANCEL_QUEUED           = '\x13d39d3c3c727cbaa38766164c6fb182ddfb8daaaf4e68d19b0095cd7927a1af'
TOPIC_RR_TRANSITIONED            = '\xa27da0b2cea36637915acc9460cc212a1eb5ad386e422cfc9f40e5f4014e222f'

-- ===== Selectors =====
SEL_LIQ_OPERATE                  = '\xad967e15'
SEL_PROXY_GET_SIGS_IMPL          = '\xa5fcc8bc'
SEL_PROXY_GET_IMPL_SIGS          = '\x89396dc8'
SEL_PROXY_GET_ADMIN              = '\x6e9960c3'
SEL_PROXY_GET_DUMMY_IMPL         = '\x908bfe5e'
SEL_PROXY_READ_FROM_STORAGE      = '\xb5c736e4'
SEL_LF_CREATE_TOKEN              = '\xe78e049a'
SEL_LF_COMPUTE_TOKEN             = '\xbb4a64d3'
SEL_LF_ALL_TOKENS                = '\x6ff97f1d'
SEL_LF_FTOKEN_TYPES              = '\xdd179e3b'
SEL_LF_SET_FTOKEN_CODE           = '\xf6015079'
SEL_FT_DEPOSIT                   = '\x6e553f65'
SEL_FT_DEPOSIT_MIN               = '\xbc157ac1'
SEL_FT_MINT                      = '\x94bf804d'
SEL_FT_WITHDRAW                  = '\xb460af94'
SEL_FT_REDEEM                    = '\xba087652'
SEL_FT_DEPOSIT_WITH_SIG          = '\x635c31c2'
SEL_FT_MINT_WITH_SIG             = '\x8c87483a'
SEL_FT_WITHDRAW_WITH_SIG         = '\x50cc0f8f'
SEL_FT_REDEEM_WITH_SIG           = '\x740c955e'
SEL_FT_GET_DATA                  = '\x3bc5de30'
SEL_FT_TOTAL_ASSETS              = '\x01e1d114'
SEL_FT_UPDATE_RATES              = '\x3c3821f4'
SEL_FT_REBALANCE                 = '\x7d7c2a1c'
SEL_FT_UPDATE_REWARDS            = '\x5fd61965'
SEL_FT_UPDATE_REBALANCER         = '\xb046a449'
SEL_FT_RESCUE_FUNDS              = '\xe53b2017'
SEL_FT_LIQUIDITY_CALLBACK        = '\xad207501'
SEL_FT_DEPOSIT_NATIVE            = '\x33bb7f91'
SEL_FT_DEPOSIT_NATIVE_MIN        = '\x02279b4a'
SEL_FT_MINT_NATIVE3              = '\x80541187'
SEL_FT_WITHDRAW_NATIVE           = '\x2126e91e'
SEL_FT_REDEEM_NATIVE             = '\x3badef91'
SEL_FT_NATIVE_TOKEN_ADDRESS      = '\xdf2ebdbb'
SEL_RR_GET_RATE                  = '\x57764094'
SEL_RR_GET_CONFIG                = '\xc3f909d4'
SEL_RR_START_REWARDS             = '\x6283311d'
SEL_RR_STOP_REWARDS              = '\x797008c6'

-- ===== Shared addresses (ALL Fluid chains: ETH, Base, Arbitrum, Polygon, BNB) =====
FLUID_LIQUIDITY                  = '\x52aa899454998be5b000ad077a46bbe360f4e497'
FLUID_LENDING_FACTORY            = '\x54b91a0d94cb471f37f949c60f7fa7935b551d03'
FLUID_LENDING_RESOLVER           = '\x48d32f49afeaec7ae66ad7b9264f446fc11a1569'
FLUID_LIQUIDITY_RESOLVER         = '\xca13a15de31235a37134b4717021c35a3cf25c60'
FLUID_REVENUE_RESOLVER           = '\x0a84741d50b4190b424f57425b09fae60c330f32'
FLUID_RESERVE_CONTRACT_PROXY     = '\x264786ef916af64a1db19f513f24a3681734ce92'
FLUID_DEPLOYER                   = '\x4f6f977acdd1177dcd81ab83074855ecb9c2d49e'
FLUID_TEAM_MULTISIG              = '\xca5e9219e1007931fd5d938c1815a90ef08f1584'

-- ===== fTokens — Ethereum (1) =====
ETH_FUSDC                        = '\x9fb7b4477576fe5b32be4c1843afb1e55f251b33'
ETH_FUSDT                        = '\x5c20b550819128074fd538edf79791733ccedd18'
ETH_FWETH                        = '\x90551c1795392094fe6d29b758eccd233cfaa260'
ETH_FWSTETH                      = '\x2411802d8bea09be0af8fd8d08314a63e706b29c'
ETH_FGHO                         = '\x6a29a46e21c730dca1d8b23d637c101cec605c5b'
ETH_FSUSDS                       = '\x2bbe31d63e6813e3ac858c04dae43fb2a72b0d11'
ETH_FUSDTB                       = '\x15e8c742614b5d8db4083a41df1a14f5d2bfb400'
-- ===== fTokens — Base (8453) =====
BASE_FUSDC                       = '\xf42f5795d9ac7e9d757db633d693cd548cfd9169'
BASE_FWETH                       = '\x9272d6153133175175bc276512b2336be3931ce9'
BASE_FWSTETH                     = '\x896e39f0e9af61eca9dd2938e14543506ef2c2b5'
BASE_FEURC                       = '\x1943fa26360f038230442525cf1b9125b5dcb401'
BASE_FGHO                        = '\x8ddbffa3cfda2355a23d6b11105ac624bdbe3631'
BASE_FSUSDS                      = '\xf62e339f21d8018940f188f6987bcdf02a849619'
-- ===== fTokens — Arbitrum One (42161) =====
ARB_FUSDC                        = '\x1a996cb54bb95462040408c06122d45d6cdb6096'
ARB_FUSDT                        = '\x4a03f37e7d3fc243e3f99341d36f4b829bee5e03'
ARB_FWETH                        = '\x45df0656f8adf017590009d2f1898eeca4f0a205'
ARB_FWSTETH                      = '\x66c25cd75ebdaa7e04816f643d8e46cecd3183c9'
ARB_FWEETH                       = '\x0d00c4a2f766b7afe2cc8f6467e296400a32b239'
ARB_FARB                         = '\xbe3860fd4c3facdf8ad57aa8c1a36d6dc4390a49'
ARB_FGHO                         = '\x037dff1c12805707d7c29f163e0f09fc9102657a'
ARB_FSUSDS                       = '\x3459fcc94390c3372c0f7b4cd3f8795f0e5afe96'
-- ===== fTokens — Polygon PoS (137) =====
POL_FAUSD                        = '\xd70dd80bc39d56e21a4475f72021bc6c5b0e4518'
POL_FUSDC                        = '\x571d456b578fdc34e26e6d636736ed7c0cdb9d89'
POL_FUSDT                        = '\x6f5e34eff43d9ab7c977512509c53840b5efba85'
POL_FWETH                        = '\xd3154535e4d0e179583ad694859e4e876eb12d24'
POL_FWPOL                        = '\x41b8b33a413681cb7d869d287e99c30c6df775b9'
POL_FWSTETH                      = '\x8c618d33463f10ddaecba2739fcfb25d58c23243'
-- ===== fTokens — BNB Smart Chain (56) =====
BNB_FU                           = '\x007df53cda786450cf8145a73b2748b241a0069c'
BNB_FUSDC                        = '\xfe60462e93cee34319f48cfc6acfbc13c2882df9'
BNB_FUSDT                        = '\xa5b8fca32e5252b0b58eabf1a8c79d958f8ee6a2'
BNB_FWBNB                        = '\x527c2a0b8a3edd9696b4a9443ef66ec30fd7b84a'

-- ===== InfiniteProxy storage slots =====
SLOT_EIP1967_ADMIN               = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
SLOT_EIP1967_IMPL_DUMMY          = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
SLOT_SIG_BASE                    = '\x000000003ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
```

---

## 9. Verification & sources

How every constant here was verified (2026-05-29):

- **Topic0 / selector hashes:** computed locally as `keccak256(canonical signature)` / `[0:4]` (pycryptodome). Canonical signatures taken verbatim from `Instadapp/fluid-contracts-public` (`main`): `contracts/infiniteProxy/events.sol`, `contracts/liquidity/userModule/events.sol`, `contracts/liquidity/adminModule/{events,structs}.sol`, `contracts/protocols/lending/{lendingFactory,fToken,lendingRewardsRateModel}/events.sol`, and interfaces `iFToken.sol`/`iLendingFactory.sol`/`iLendingRewardsRateModel.sol`. Struct-array event args expanded to tuples before hashing.
- **Address bytecode existence:** `eth_getCode` non-empty on `ethereum-rpc.publicnode.com`, `base-rpc.publicnode.com`, `arbitrum-one-rpc.publicnode.com`, `polygon-bor-rpc.publicnode.com`, `bsc-rpc.publicnode.com` for every listed contract. fToken/factory/resolver runtime sizes recorded (fToken 19617 B / native 21098 B; factory 8305 B; LendingResolver 10757 B; LiquidityResolver 12803 B; RewardsRateModel 1820 B, BNB 5547 B).
- **Selectors in bytecode:** confirmed present in deployed fUSDC, fWETH (native), and LendingFactory bytecode (e.g. `createToken`, `computeToken`, `deposit`, `redeem`, `getData`, `rebalance`, `updateRates`, `updateRewards`, `liquidityCallback`, `depositNative`, `NATIVE_TOKEN_ADDRESS`, `getRate`, `getConfig`). `operate` confirmed via live per-selector dispatch.
- **Live topics:** `eth_getLogs` (address-scoped) confirmed `LogOperate` on the Liquidity proxy (ETH/BNB/Polygon) and ERC-4626 `Deposit`/`Withdraw` on fUSDC; a full topic0 tally of a recent fUSDC window showed exactly `Transfer/Deposit/Withdraw/Approval` (confirming `LogUpdateRates`/`LogRebalance` are maintenance-only).
- **Proxy slots & dispatch:** `eth_getStorageAt` for the EIP-1967 admin + dummy-impl slots (per-chain values in §4); `getSigsImplementation(0xad967e15)` returned the per-chain UserModule (ETH `0x4bdc88…`, others `0x3c0651…`), confirming the per-selector dispatch model.
- **Not on Optimism/Avalanche:** confirmed by absence of `deployments/optimism|avalanche` in the repo and no bytecode at `0x52Aa…E497` on either chain.

**Authoritative sources:**
- [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) — all source + `deployments/<chain>/v1_0_0/*.json` artifacts (fToken addresses + constructor args = canonical address registry).
- [docs.fluid.io](https://docs.fluid.io) — protocol docs (its Deployments page redirects to the repo).
- Explorers: Etherscan / BaseScan / Arbiscan / PolygonScan / BscScan for spot confirmation.
