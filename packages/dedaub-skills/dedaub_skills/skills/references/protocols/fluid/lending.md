# Fluid (Instadapp) — Lending (fTokens) — Topics, Selectors, Addresses

**Status:** verified against the canonical `Instadapp/fluid-contracts-public` (branch `main`) source and live RPC on every listed chain (built 2026-05-29; fTokens re-enumerated via `allTokens()` + counts re-verified **2026-06-05**). All topic0/selector hashes computed locally with keccak; all addresses confirmed via `eth_getCode`. Index: [`README.md`](README.md). Reward/staking periphery: [`periphery.md`](periphery.md).
> **Re-verification 2026-06-05:** live `allTokens()` counts = ETH 7, Base 6, Arbitrum **9** (incl. new **fPYUSD**), Polygon 6, BNB **5** (incl. new **fETH**). Two new fTokens since the original build (added below); all previously-documented fTokens unchanged.
**Scope:** Fluid **Lending** ("Lend & Earn": fTokens, the ERC-4626 deposit side) on **Ethereum (1), Base (8453), Arbitrum One (42161), Polygon PoS (137), BNB Smart Chain (56)**. fTokens are pure suppliers to the shared Liquidity Layer — see [`liquidity-layer.md`](liquidity-layer.md) for the core, `LogOperate`, the InfiniteProxy and per-chain modules. Other modules: [`vaults.md`](vaults.md), [`dex.md`](dex.md).
**Key fact:** an fToken is an ERC-20 + **ERC-4626** wrapper over a Liquidity-Layer supply position — it never custodies funds (a deposit flows straight through to Liquidity via `liquidityCallback`). It emits standard ERC-4626 `Deposit`/`Withdraw`, each mirrored by a Liquidity `LogOperate` in the same tx (`user = fToken address`). Yield (incl. rewards) accrues into the fToken→underlying **exchange price**, not via per-user claim events.

> **Not on Optimism (10) or Avalanche (43114).** The repo's `deployments/` has only `mainnet, arbitrum, base, polygon, bnb, plasma`; no bytecode at the core addresses on OP/Avax (verified).
> **BNB IS live** (some dashboards omit it): LendingFactory + 4 fTokens (fU, fUSDC, fUSDT, fWBNB) all have bytecode with active traffic — verified on-chain. Treat on-chain evidence as authoritative over dashboard listings.

**Versioning:** there is *no* on-chain v1/v2 of Lending. `FluidLendingFactory` is a plain non-upgradeable `Owned` contract; it extends by registering new `fTokenType` creation codes (SSTORE2) rather than redeploying. fTokens are non-upgradeable **CREATE3** deployments (salt `keccak256(abi.encode(asset, fTokenType))`) — a "new version" of an fToken is simply a new address.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 FluidLendingFactory

| topic0 | Event |
|--------|-------|
| `0x60c8487fc242a40cc8d2722cf9b3b5a14b316a50bf4ed30c9f0f1b0126728a36` | `LogTokenCreated(address indexed token, address indexed asset, uint256 indexed count, string fTokenType)` |
| `0x014b54fa6d2080e9aacd1c598c7689a625610d7d684dd41d10407e48aa8b1200` | `LogSetAuth(address indexed auth, bool indexed allowed)` |
| `0x48cc5b4660fae22eabe5e803ee595e63572773d114bcd54ecc118c1efa8d75af` | `LogSetDeployer(address indexed deployer, bool indexed allowed)` |
| `0x93dad940f342b3cd95007806ae0cb0c162dbbfba54d55223bc6d055c62e608e0` | `LogSetFTokenCreationCode(string indexed fTokenType, address indexed creationCodePointer)` |

Subscribe to `LogTokenCreated` from the factory to discover every fToken on a chain. `count` = 1-based index in `allTokens()`. `fTokenType` is `"fToken"` (standard) or `"NativeUnderlying"` (wrapped-native).

### 1.2 fToken (per ERC-4626 lending token)

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

The ERC-4626 `Deposit`/`Withdraw` topic0s are the **standard** ones, shared by every ERC-4626 vault (Morpho MetaMorpho, Yearn v3, etc.) — disambiguate a Fluid fToken by its address (LendingFactory-deployed) or `symbol()` ("f"-prefixed). Normal user activity emits only `Deposit`/`Withdraw`/`Transfer`/`Approval` (verified: a fUSDC window had exactly those four). `LogUpdateRates`/`LogRebalance`/`LogUpdateRewards`/`LogRescueFunds`/`LogUpdateRebalancer` are admin/maintenance events. There is **no** `LogClaimReward` — rewards are not per-user-claimed; they accrue into the exchange price.

### 1.3 FluidLendingRewardsRateModel

| topic0 | Event |
|--------|-------|
| `0xf847e1fc85baf05c769b3bc2f2dc3384d56aca28c9894497717c6c1383b098af` | `LogStartRewards(uint256 rewardAmount, uint256 duration, uint256 startTime)` |
| `0x0ba629f001023d2b4b32157343614f17651d8508c3c6c1bfa5769925cb718c0e` | `LogStopRewards()` |
| `0x68ef2ad282a305bd5b41f780462102ad9fc40964ab6097401fcc6eb0ebefae87` | `LogQueueNextRewards(uint256 rewardAmount, uint256 duration)` |
| `0x13d39d3c3c727cbaa38766164c6fb182ddfb8daaaf4e68d19b0095cd7927a1af` | `LogCancelQueuedRewards()` |
| `0xa27da0b2cea36637915acc9460cc212a1eb5ad386e422cfc9f40e5f4014e222f` | `LogTransitionedToNextRewards(uint256 startTime, uint256 endTime)` |

---

## 2. Function signatures (chain-agnostic)

Selectors = `keccak256(canonical signature)[0:4]`, verified against deployed dispatcher bytecode (fToken, factory).

### 2.1 FluidLendingFactory

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

### 2.2 fToken (ERC-4626 + Fluid extensions; standard `"fToken"` type)

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

### 2.3 fTokenNativeUnderlying (wrapped-native fTokens: fWETH, fWPOL, fWBNB)

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

> `mintNative(uint256,address)` (2-arg, selector `0x00acb736`) is declared in current `main` source but is **not present** in the deployed mainnet fWETH bytecode (only the 3-arg `mintNative` `0x80541187` is) — version drift between the live deployment and HEAD. Treat the 3-arg form as canonical for the deployed contracts.

### 2.4 FluidLendingRewardsRateModel

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

## 3. Addresses

### 3.1 Shared across all Fluid chains (deterministic CREATE3)

Identical on **Ethereum, Base, Arbitrum, Polygon, BNB** (verified `eth_getCode` non-empty on each).

| Role | Address | One-liner |
|------|---------|-----------|
| **FluidLendingFactory** | `0x54B91A0D94cb471F37f949c60F7Fa7935b551D03` | Deploys fTokens (CREATE3). Non-upgradeable `Owned`. `code=8305 B`. |
| **FluidLendingResolver** | `0x48D32f49aFeAEC7AE66ad7B9264f446fc11a1569` | Read helper for fTokens/lending. `code=10757 B`. |
| ReserveContractProxy | `0x264786EF916af64a1DB19F513F24a3681734ce92` | The fToken rebalancer / revenue collector. Minimal proxy (`code=190 B`). |
| SmartLendingResolver | `0x3E69A3Af4305b65598b228d3da70786Bd9cfeB0e` | DEX-backed "smart lending" resolver. ETH/Base/Arb/Polygon — **BNB uses `0x1446dEc487B4411DE222547ADbC3b3e01933787f`**. |

Deployer/owner (all chains): `0x4F6F977aCDD1177DCD81aB83074855EcB9C2D49e`. The shared Liquidity proxy and InfiniteProxy detail live in [`liquidity-layer.md`](liquidity-layer.md).

### 3.2 fTokens & rewards-rate-models — per chain

All fToken addresses verified `eth_getCode` non-empty. Standard `"fToken"` runtime = **19617 B**; native-underlying = **21098 B** (a clean way to tell them apart on-chain).

#### Ethereum (1)

| fToken | Address | Underlying | Underlying addr | RewardsRateModel |
|--------|---------|-----------|-----------------|------------------|
| fUSDC | `0x9Fb7b4477576Fe5B32be4C1843aFB1e55F251B33` | USDC | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | `0xb75Ec31fd7ad0D823A801be8740B9Fad299ce6d6` |
| fUSDT | `0x5C20B550819128074FD538Edf79791733ccEdd18` | USDT | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | `0x19147A180D271d90dC12Da2BFFC636F54Cf7C241` |
| fWETH *(native)* | `0x90551c1795392094FE6D29B758EcCD233cFAa260` | WETH/ETH | `0xC02aaA39…C756Cc2` | — |
| fwstETH | `0x2411802D8BEA09be0aF8fD8D08314a63e706b29C` | wstETH | `0x7f39C581…35E2Ca0` | — |
| fGHO | `0x6A29A46E21C730DcA1d8b23d637c101cec605C5B` | GHO | `0x40D16FC0…28aE6C2f` | `0x95755A4552690a53d7360B7e16155867868ae964` |
| fsUSDS | `0x2BBE31d63E6813E3AC858C04dae43FB2a72B0D11` | sUSDS | `0xa3931d71…Fec27fbD` | — |
| fUSDtb | `0x15e8c742614b5D8Db4083A41Df1A14F5D2bFB400` | USDtb | `0xC139190F…8b18aC1C` | — |

#### Base (8453)

| fToken | Address | Underlying | RewardsRateModel |
|--------|---------|-----------|------------------|
| fUSDC | `0xf42f5795D9ac7e9D757dB633D693cD548Cfd9169` | USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | `0xFB10c86A7E9d93105f291968E83dA0b54e2Ef5f0` |
| fWETH *(native)* | `0x9272D6153133175175Bc276512B2336BE3931CE9` | WETH `0x4200…0006` | — |
| fwstETH | `0x896E39f0E9af61ECA9dD2938E14543506ef2c2b5` | wstETH `0xc1CBa3fC…0ee452` | — |
| fEURC | `0x1943FA26360f038230442525Cf1B9125b5DCB401` | EURC `0x60a3E35C…b1adb42` | `0xA4a5f550c16f53d4F463832d16F428Cdc4017Bfb` |
| fGHO | `0x8DdbfFA3CFda2355a23d6B11105AC624BDbE3631` | GHO `0x6Bb7a212…8da10Ee` | — |
| fsUSDS | `0xf62e339f21d8018940f188F6987Bcdf02A849619` | sUSDS `0x5875eEE1…675467a` | — |

#### Arbitrum One (42161)

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
| fPYUSD *(new 2026-06)* | `0x24bb6c093e15658acE2c34bee9aC16f0A6ED2b01` | PYUSD `0x46850aD61C2B7d64d08c9C754F45254596696984` | — |

#### Polygon PoS (137)

| fToken | Address | Underlying | RewardsRateModel |
|--------|---------|-----------|------------------|
| fAUSD | `0xd70dD80Bc39d56E21A4475F72021BC6C5B0E4518` | AUSD `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` | — |
| fUSDC | `0x571d456b578fDC34E26E6D636736ED7c0CDB9d89` | USDC `0x3c499c54…3d5c3359` | — |
| fUSDT | `0x6f5e34eFf43D9ab7c977512509C53840B5EfBA85` | USDT `0xc2132D05…B58e8F` | — |
| fWETH | `0xD3154535E4D0e179583ad694859E4e876EB12d24` | WETH `0x7ceB23fD…1b9f619` | — |
| fWPOL *(native)* | `0x41b8B33A413681CB7d869D287E99C30c6DF775b9` | WPOL/WMATIC `0x0d500B1d…3ADf1270` | — |
| fwstETH | `0x8C618d33463f10DDAeCbA2739fCfb25d58C23243` | wstETH `0x03b54A6e…3B3bCCD` | — |

*(No per-fToken RewardsRateModel deployed on Polygon at time of writing.)*

#### BNB Smart Chain (56)

| fToken | Address | Underlying | RewardsRateModel |
|--------|---------|-----------|------------------|
| fU | `0x007df53Cda786450Cf8145a73B2748B241a0069c` | U `0xcE24439F…B666666` | `0xbaFe938aEE7b0E1efe7D488905710F3C99eCb36A` |
| fUSDC | `0xfE60462E93cee34319F48Cfc6AcFbc13c2882Df9` | USDC `0x8AC76a51…32Cd580d` | `0x149747813e1A5b04B5F17869b9d6603022B591fd` |
| fUSDT | `0xA5b8FCa32E5252B0B58EAbf1A8c79d958F8EE6A2` | USDT(BSC-USD) `0x55d39832…3197955` | `0xBE02b3DA446BF1B5CB271553F162A0f7C92E90bD` |
| fWBNB *(native)* | `0x527C2a0B8A3eDD9696B4A9443ef66Ec30fD7B84a` | WBNB `0xbb4CdB9C…73bc095c` | — |
| fETH *(new 2026-06)* | `0x8d711Fc6cc96B94F32c3F8eEEb6e75a765fbcfe6` | Binance-Peg ETH `0x2170Ed0880ac9A755fd29B2688956BD959F933F8` | — |

BNB RewardsRateModel runtime is larger (`5547 B` vs `1820 B` elsewhere) — a newer model build; same `getRate`/`getConfig` interface.

---

## 4. Proxies

fTokens, the LendingFactory, resolvers and the RewardsRateModels are **NOT proxies** — they are plain CREATE3 / normal contracts (an fToken "upgrade" = a new address; the factory is a non-upgradeable `Owned`). The only proxy in the Lending path is the shared **Liquidity** InfiniteProxy that fTokens supply into — see [`liquidity-layer.md`](liquidity-layer.md). `ReserveContractProxy` `0x264786…ce92` is a separate, tiny minimal proxy (`code=190 B`), not an InfiniteProxy.

---

## 5. Detection invariants & gotchas

1. **One `LogOperate` per Lending action, emitted by the Liquidity proxy — not by the fToken.** A user deposit into fUSDC emits: fUSDC `Deposit` + fUSDC `Transfer` (mint) + Liquidity `LogOperate` (with `user = fUSDC address`, `supplyAmount > 0`). To attribute Liquidity flows to Lending, map `LogOperate.user ∈ allTokens()`. See [`liquidity-layer.md`](liquidity-layer.md).
2. **fToken `Deposit`/`Withdraw` use the standard ERC-4626 topic0s** — not Fluid-specific. Identify a Fluid fToken by address (LendingFactory-deployed) or `symbol()` ("f"-prefixed).
3. **fTokens never hold the underlying.** Underlying flows depositor → Liquidity directly via `liquidityCallback`. Don't expect the fToken's underlying balance to track deposits (it's ~0); use `totalAssets()` / `getData()`.
4. **Yield & rewards accrue into the exchange price**, not via claim events. `tokenExchangePrice` (fToken→underlying) rises over time. There is no `LogClaimReward` and no per-user reward event. The only reward-program events are on `FluidLendingRewardsRateModel` (`LogStartRewards` etc.) and the fToken `LogUpdateRewards` (model address change).
5. **`LogUpdateRates`/`LogRebalance` are rare maintenance events**, not per-deposit. A normal fToken window emits only ERC-4626 `Deposit/Withdraw` + ERC-20 `Transfer/Approval`. Don't rely on `LogUpdateRates` to track APY — read exchange prices via `getData()`/resolver.
6. **Native vs standard fToken is detectable by bytecode size** (21098 B native-underlying vs 19617 B standard) and by the presence of `depositNative`/`NATIVE_TOKEN_ADDRESS`. The wrapped-native fToken is fWETH (ETH/Base/Arb), fWPOL (Polygon), fWBNB (BNB).
7. **fToken address is deterministic** = CREATE3 of `salt = keccak256(abi.encode(asset, fTokenType))` from the factory — reproducible off-chain via `computeToken(asset, fTokenType)`.
8. **Live deployments can lag HEAD source.** Mainnet fWETH lacks the 2-arg `mintNative` that's in current `main`. When a selector matters, verify against the live contract, not the repo file.
9. **Not on Optimism or Avalanche** — no LendingFactory/fToken bytecode there.

---

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics =====
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
FLUID_LENDING_FACTORY            = '\x54b91a0d94cb471f37f949c60f7fa7935b551d03'
FLUID_LENDING_RESOLVER           = '\x48d32f49afeaec7ae66ad7b9264f446fc11a1569'
FLUID_RESERVE_CONTRACT_PROXY     = '\x264786ef916af64a1db19f513f24a3681734ce92'
FLUID_DEPLOYER                   = '\x4f6f977acdd1177dcd81ab83074855ecb9c2d49e'

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
ARB_FPYUSD                       = '\x24bb6c093e15658ace2c34bee9ac16f0a6ed2b01'  -- new 2026-06
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
BNB_FETH                         = '\x8d711fc6cc96b94f32c3f8eeeb6e75a765fbcfe6'  -- new 2026-06
```

---

## 7. Verification & sources

How every constant here was verified (2026-05-29):

- **Topic0 / selector hashes:** computed locally as `keccak256(canonical signature)` / `[0:4]`. Canonical signatures taken verbatim from `Instadapp/fluid-contracts-public` (`main`): `contracts/protocols/lending/{lendingFactory,fToken,lendingRewardsRateModel}/events.sol`, interfaces `iFToken.sol`/`iLendingFactory.sol`/`iLendingRewardsRateModel.sol`.
- **Address bytecode existence:** `eth_getCode` non-empty on `ethereum-rpc.publicnode.com`, `base-rpc.publicnode.com`, `arbitrum-one-rpc.publicnode.com`, `polygon-bor-rpc.publicnode.com`, `bsc-rpc.publicnode.com` for every listed contract. Runtime sizes recorded (fToken 19617 B / native 21098 B; factory 8305 B; LendingResolver 10757 B; RewardsRateModel 1820 B, BNB 5547 B).
- **Selectors in bytecode:** confirmed present in deployed fUSDC, fWETH (native), and LendingFactory bytecode.
- **Live topics:** a full topic0 tally of a recent fUSDC window showed exactly `Transfer/Deposit/Withdraw/Approval` (confirming `LogUpdateRates`/`LogRebalance` are maintenance-only).
- **Not on Optimism/Avalanche:** confirmed by absence of `deployments/optimism|avalanche` in the repo and no bytecode at the core addresses.

**Authoritative sources:**
- [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) — all source + `deployments/<chain>/v1_0_0/*.json` artifacts (fToken addresses + constructor args = canonical address registry).
- [docs.fluid.io](https://docs.fluid.io) — protocol docs (its Deployments page redirects to the repo).
- Explorers: Etherscan / BaseScan / Arbiscan / PolygonScan / BscScan for spot confirmation.
