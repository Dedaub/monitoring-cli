# Native — Credit Pool / Lending (CreditVault + NativeLPToken) — Topics, Selectors, Addresses

**Status:** verified against live RPC on Ethereum(1), BNB Smart Chain(56), Arbitrum One(42161), Base(8453), Avalanche C-Chain(43114), Optimism(10), Polygon PoS(137), and the `Native-org/native-v2-core` repo (`CreditVault.sol`, `NativeLPToken.sol`, `interfaces/ICreditVault.sol`, `libraries/ConstantsLib.sol`) on 2026-06-02.
**Scope:** the **Native Credit Pool** (lending/credit side) only — the `CreditVault` (asset custody + market-maker position/collateral/settlement/liquidation) and the per-asset `NativeLPToken` yield-bearing LP tokens. The **swap side** (NativeRouter V3/V4, NativeRFQPool, NativeBridge) is **out of scope here** and handled by a separate agent — see the boundary note below. Topics + selectors are **chain-agnostic**; addresses are network-specific. **CreditVault is deployed on Ethereum, BNB, Arbitrum, and Base only** — `eth_getCode` returns `0x` for every candidate on Avalanche, Optimism, and Polygon (§ Cross-chain summary).

Native flips on-chain liquidity from *inventory-based* to *credit-based*. Whitelisted private market makers ("traders" / PMMs) borrow assets directly from the `CreditVault` up to a credit limit (computed off-chain) to quote RFQ swaps, instead of pre-funding inventory. The vault holds almost all protocol assets. A trader's net exposure is tracked as a **signed position** `positions[trader][token]` (positive = long, negative = short = borrowed). LPs deposit an underlying asset into its dedicated `NativeLPToken`; the deposit is forwarded **into the CreditVault** (the LP contract holds no underlying), and LP yield comes from **borrowing fees** the traders pay — distributed to LP holders by an off-chain `epochUpdater` calling `epochUpdate` → `distributeYield`, which raises each LP token's exchange rate (capped at +1% per epoch). Traders may also post `NativeLPToken` (or other supported markets) as **collateral**; positions that go underwater are closed by whitelisted **liquidators**.

The whole credit/settlement/liquidation flow is **off-chain-authorized**: `settle`, `removeCollateral`, and `liquidate` each carry an **EIP-712 signature** from a protocol `signer` (the off-chain credit engine), so the on-chain contract is the enforcement layer, not the credit-decision layer. `addCollateral` is the one permissionless entrypoint. The position bookkeeping is the load-bearing state — there is **no ERC-4626 vault, no Chainlink/Pyth oracle contract, no separate liquidation-engine contract** on-chain; pricing and health are off-chain and asserted via the signer's signature.

> **Boundary with the swap side (separate doc):** `CreditVault.swapCallback(address,address,int256,address,int256)` is invoked by whitelisted **credit pools** (the NativeRFQPool / NativeRouter swap contracts, registered via `setCreditPool`) *after* a swap, to mutate `positions[trader][tokenIn/tokenOut]`. So a CreditVault state change can originate from a swap-side tx. The swap contracts themselves (NativeRouter V3/V4, NativeRFQPool, NativeBridge) are **not** documented here. CreditVault's `creditPools` mapping + `CreditPoolUpdated` event are the link.

---

## 0. Contract families

| Contract | Role | Proxy? | Verified name / notes |
|----------|------|--------|------------------------|
| **CreditVault** | Core. Custodies assets; tracks `positions[trader][token]` (int256) and `collateral[trader][token]` (uint256); handles `settle`/`repay`/`addCollateral`/`removeCollateral`/`liquidate`/`epochUpdate`; registers markets (LP tokens), credit pools, traders, liquidators. `EIP712("Native Credit Vault","1")`, `Ownable2Step`, transient reentrancy guard. | **No** — direct deployment (~20 KB on ETH/BNB, ~19.5 KB on ARB/Base; EIP-1967 impl & admin slots empty on all 4 chains). Upgrade = **redeploy**, not proxy swap. | `CreditVault` (solc 0.8.28) |
| **NativeLPToken** | Per-asset yield-bearing LP token. One instance **per underlying** (e.g. `NT-LP-WETH`, `NT-LP-USDC`). `deposit`/`redeem` move underlying **into/out of the CreditVault** (LP holds no underlying); `balanceOf` returns underlying value of shares (rebasing-by-exchange-rate, **not** raw share count). `Ownable2Step`. | **No** — direct deployment (~21 KB; impl slot empty). | `NativeLPToken` (solc 0.8.28). `symbol()` prefix `NT-LP-…` / `NTLP-…` / `NLP-…` (prefix varies by deploy era; not significant). |

There is **no factory contract** — LP tokens are deployed individually and registered on the vault via `supportMarket(NativeLPToken)` (owner-only), which emits `MarketListed`. Discover all LP tokens per chain by walking `allLPTokens(uint256)` until it reverts, or by reading `lpTokens(underlying)`.

**Per-asset LP-token / underlying maps** (read from the live vault, see §3.x). `CreditVault.lpTokens[underlying] → NativeLPToken`, `NativeLPToken.underlying() → ERC-20`, `NativeLPToken.creditVault() → CreditVault`. `CreditVault.supportedMarkets[lpToken] → bool`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally with keccak-256 on 2026-06-02 from the verified source. Tuple params expand to their component types for hashing (e.g. `TokenAmountInt` → `(address,int256)`). **Cross-checked against live `eth_getLogs`** on the Ethereum CreditVault (`Settled`, `Repaid`, `EpochUpdated`, `MarketListed`, `TraderSet`, `CreditPoolUpdated`, `OwnershipTransferred/Started` all observed) and on a live Ethereum LP token (`SharesMinted`, `SharesBurned`, `TransferShares`, `YieldDistributed`, `Transfer`, `TrustedOperatorUpdated`, `RedeemCooldownExemptUpdated` all observed).

### 1.1 CreditVault

| topic0 | Event | Meaning |
|--------|-------|---------|
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address lpToken)` | New LP-token market listed (`supportMarket`). *(live ✓ ETH)* |
| `0x90e0333a7f11b37e50e152c45bb5ebfc2ce2ace82e290567861d3ae852968874` | `EpochUpdated((address,(address,uint256,uint256)[])[] accruedFundingFees)` | Per-epoch funding/reserve-fee settlement; drives LP yield. *(live ✓ ETH+BNB+Base)* |
| `0xc8aa82285b2a9e22e0bda601a759e4f578e78f18015e543a4f66bb120a726953` | `Repaid(address trader, (address,int256)[] repayments)` | Trader repaid (reduced) short positions. *(live ✓ ETH)* |
| `0x0279bcc316c233db88e8f3e463dcefc7fa661da21bc66eadc60f3835e41bba11` | `Settled(address trader, (address,int256)[] positionUpdates)` | Trader settled positions (EIP-712 signed). *(live ✓ ETH)* |
| `0x770dafe0b413d5c277b5f1a9d1d725e5ebafe92b5a16f3ebaae6e49e43b66499` | `CollateralAdded(address trader, (address,uint256)[] collateralUpdates)` | Collateral deposited (permissionless). |
| `0x455917442c530b052ee826d2556fad794f64a294e455930a63599688abbffa3c` | `CollateralRemoved(address trader, (address,uint256)[] collateralUpdates)` | Collateral withdrawn (EIP-712 signed). |
| `0xb5689a012cf77dd0a99ac07ed6f83009d7fbfca323bca73b34d6ed02bf413ab8` | `Liquidated(address trader, address liquidator, (address,int256)[] positionUpdates, (address,uint256)[] claimCollaterals)` | Underwater trader liquidated (EIP-712 signed, liquidator-only). **The lending-side liquidation signal.** |
| `0x947aca305c9b8d94b31792a7f80d331c9452e743508d61331561378673b50103` | `CreditPoolUpdated(address indexed pool, bool isActive)` | Swap-side credit pool (NativeRFQPool/Router) whitelisted/removed. *(live ✓ ETH)* |
| `0x39ff4a05a64bdf7e1dcb0b2d6b7e35b6a720a9412386a9e193c0e93d29a18470` | `RebalanceCapUpdated(address indexed operator, address indexed token, uint256 limit)` | Daily rebalance cap set for a trader/liquidator+token. |
| `0x2353ec0fe56a376d3269d3e65521f1ce07dc5f544cc5b0ba4eb2ff03f771a4ad` | `TraderSet(address indexed trader, bool isTrader, bool isWhitelistTrader, address settler, address recipient)` | Trader (PMM) permissions/recipient configured. *(live ✓ ETH)* |
| `0x81e020344174972c59f6c11a8f6c90b141866214e3d9b544d030f0b532f5a10f` | `LiquidatorSet(address liquidator, bool status)` | Liquidator whitelisted/removed. |
| `0x9eaa897564d022fb8c5efaf0acdb5d9d27b440b2aad44400b6e1c702e65b9ed3` | `SignerSet(address signer)` | EIP-712 signer (off-chain credit engine) rotated. **Watch this.** |
| `0x538bd377a1e0d2ceca49908f540bafa1d8616cf49a7bcefcd0b479e7531ff8aa` | `EpochUpdaterSet(address epochUpdater)` | Epoch updater rotated. |
| `0x15d0b1a02a4902c4788ceda199eb43e4a753d86c0dbb7412e8ba63feecb070fa` | `FeeWithdrawerSet(address feeWithdrawer)` | Reserve-fee withdrawer rotated. |
| `0xde13184e8cbb6eccbcecfc796bf8820e5ffde0534c01b4fabed4b05982964a44` | `ReserveWithdrawn(address underlying, address recipient, uint256 amount)` | Protocol reserve fees withdrawn. |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` | Ownable2Step handover begun. *(live ✓ ETH)* |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Owner changed. *(live ✓ ETH)* |

**Note:** there is **no event for `swapCallback`** — the swap-side position mutation is silent on the vault (it only changes `positions` storage). To attribute position changes to swaps you must trace the call, not watch a vault event.

### 1.2 NativeLPToken (per-asset; same topic0 on every LP-token instance)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xd9c8415d46bc958abafa67ce0dad25daa34cd66edf0fba6e9bf3cc0fc8bfe1e0` | `SharesMinted(address indexed from, address indexed to, uint256 shares, uint256 underlyingAmount)` | LP deposit. *(live ✓)* |
| `0xdf98f11672c77edcc0f4ed1da404198a75887435a8da9173ef3d22969dcf318c` | `SharesBurned(address indexed from, address indexed to, uint256 shares, uint256 underlyingAmount)` | LP redeem. *(live ✓)* |
| `0x9d9c909296d9c674451c0c24f02cb64981eb3b727f99865939192f880a755dcb` | `TransferShares(address indexed from, address indexed to, uint256 shares)` | Share transfer (fires alongside ERC-20 `Transfer`). *(live ✓)* |
| `0xe8ed0a697f15301f06fd3d30bc896682e7826c5397076a3eda05844cfc356480` | `YieldDistributed(uint256 yieldAmount)` | Borrow-fee yield added to `totalUnderlying` (called by CreditVault during `epochUpdate`). *(live ✓)* |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20. `value` = **underlying-denominated** amount, not shares. *(live ✓)* |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ERC-20. |
| `0xb566d3df2587c9e70b06b6419bdeeeeec8ca8cd60e4c48c6baad0d94c46809c7` | `MinDepositUpdated(uint256 oldAmount, uint256 newAmount)` | |
| `0x4bc7bce1799e8fb5e7c6565f8090db1a4fec630506908c783abacc2a6b6d2f38` | `MinRedeemIntervalUpdated(uint256 newInterval)` | |
| `0x6730dde45b44b81615893b00081ca1865c1512048fef1dc7b3a8ec4f3da0dae6` | `EarlyWithdrawFeeBipsUpdated(uint256 oldFeeBips, uint256 newFeeBips)` | |
| `0x2e4746592fbf3f346fff4993672957b8e58f533eaaca7a25d1676602f1150a03` | `TrustedOperatorUpdated(address indexed account, bool status)` | Operator allowed `depositFor`/`redeemTo`. *(live ✓)* |
| `0xce0277a65558e646cf52d00a8e5a74cc06c339d7a6277d7333af0d81cad38ed4` | `RedeemCooldownExemptUpdated(address indexed account, bool status)` | *(live ✓)* |
| `0x1c40b92055dd2c2d8499b55a470506571b2bf68a1bc75af8a0b314760dd5f1cb` | `EarlyWithdrawFeeWithdrawn(address indexed recipient, uint256 amount)` | |
| `0x35edea304410d4256c657d14535db2c0a3e9c75dcc42c5c9781c4e8171dad7e0` | `DepositPaused()` | |
| `0x8c357fe0f696f2972294914e16a16c64a121f9a529a92b9d87fc7a79ec170f2c` | `DepositUnpaused()` | |
| `0x60b78ed2d882d2d2387ad2b7119495f7c99dd9a9c191d3d02c35982a0750bcc6` | `RedeemPaused()` | |
| `0x687bf6e69dbabcc95e11041b4816a83f36dcf6ef647f6acf63e7469d28f5ea73` | `RedeemUnpaused()` | |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed,address indexed)` | Ownable2Step. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed,address indexed)` | |

**No proxy/upgrade event exists on either contract** — neither is a proxy (§ Proxies). There is no `Upgraded(address)` / `AdminChanged` / `Initialized` to watch; upgrades happen by **redeploying** to a new address and re-listing markets.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 CreditVault — state-changing

| Selector | Signature | Auth / notes |
|----------|-----------|--------------|
| `0x9be41fdb` | `settle((uint256,uint256,address,(address,int256)[]),bytes)` | trader/settler + EIP-712 sig. Emits `Settled`. |
| `0x81377bfd` | `repay((address,int256)[],address)` | trader/settler. Emits `Repaid`. |
| `0xb6bdff03` | `addCollateral((address,uint256)[],address)` | **permissionless** (anyone funds any whitelisted trader). Emits `CollateralAdded`. |
| `0x4e293ee9` | `removeCollateral((uint256,uint256,address,(address,uint256)[]),bytes)` | trader/settler + EIP-712 sig. Emits `CollateralRemoved`. |
| `0x12411772` | `liquidate((uint256,uint256,address,(address,int256)[],(address,uint256)[]),bytes)` | **liquidator-only** + EIP-712 sig. Emits `Liquidated`. |
| `0x98221e94` | `epochUpdate((address,(address,uint256,uint256)[])[])` | epochUpdater-only. Emits `EpochUpdated` + per-token `YieldDistributed`. |
| `0x7362ecbe` | `swapCallback(address,address,int256,address,int256)` | **credit-pool-only** (swap side). Mutates `positions`; **emits nothing**. |
| `0xc4076876` | `pay(address,uint256)` | LP-token-only. Vault → recipient underlying transfer (backs LP redeem / early-fee withdraw). |
| `0xcab4f84c` | `supportMarket(address)` | owner. Lists an LP token. Emits `MarketListed`. |
| `0xae1914f8` | `withdrawReserve(address,address,uint256)` | feeWithdrawer. Emits `ReserveWithdrawn`. |
| `0xabb49f19` | `setCreditPool(address,bool)` | owner. Emits `CreditPoolUpdated`. |
| `0x1e777ad3` | `setAllowance((address,uint256)[],address)` | owner. Approves a credit pool to pull vault underlying. |
| `0x097a8ec4` | `setRebalanceCap(address,address,uint256)` | owner. Emits `RebalanceCapUpdated`. |
| `0xc2b73076` | `setTrader(address,address,address,bool,bool)` | owner. Emits `TraderSet`. |
| `0x47de43e2` | `setLiquidator(address,address,bool)` | owner. Emits `LiquidatorSet`. |
| `0x6c19e783` | `setSigner(address)` | owner. Emits `SignerSet`. |
| `0x73eb5133` | `setEpochUpdater(address)` | owner. Emits `EpochUpdaterSet`. |
| `0x00fc59c0` | `setFeeWithdrawer(address)` | owner. Emits `FeeWithdrawerSet`. |
| `0x79ba5097` | `acceptOwnership()` | Ownable2Step. |

### 2.2 CreditVault — views / public mappings

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x4bd21445` | `positions(address,address)` | `int256` — trader net position (signed; negative = borrowed). **Core state.** |
| `0xcc218ece` | `collateral(address,address)` | `uint256` — trader collateral per token. |
| `0xb17b658d` | `lpTokens(address)` | `address` — LP token for an underlying. |
| `0x20761fc4` | `supportedMarkets(address)` | `bool` — is this address a listed LP token. |
| `0x9246261c` | `allLPTokens(uint256)` | `address` — enumerate markets (reverts past end). |
| `0x92a88fa2` | `traders(address)` | `bool` |
| `0xf90cdb36` | `liquidators(address)` | `bool` |
| `0x0dfbe91b` | `creditPools(address)` | `bool` — is this a whitelisted swap-side pool. |
| `0x464b38bc` | `reserveFees(address)` | `uint256` — accumulated protocol reserve fees per token. |
| `0xb7477674` | `rebalanceCaps(address,address)` | `(uint256 limit,uint256 used,uint256 lastDay)` |
| `0x0d2a7ae8` | `traderToSettler(address)` | `address` |
| `0x422e0af0` | `traderToRecipient(address)` | `address` |
| `0xf6d95efd` | `liquidatorToRecipient(address)` | `address` |
| `0x41b1fa76` | `whitelistTraders(address)` | `bool` — bypasses credit check. |
| `0x141a468c` | `nonces(uint256)` | `bool` — EIP-712 replay guard. |
| `0xb0ab63ec` | `lastEpochUpdateTimestamp(address)` | `uint256` |
| `0x238ac933` | `signer()` | `address` — EIP-712 credit signer. |
| `0x32b4fa6b` | `feeWithdrawer()` | `address` |
| `0x4f487eb8` | `epochUpdater()` | `address` |
| `0x8da5cb5b` | `owner()` | `address` |
| `0xe30c3978` | `pendingOwner()` | `address` |

### 2.3 NativeLPToken — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb6b55f25` | `deposit(uint256)` | Mint LP; underlying → CreditVault. Emits `SharesMinted`. **Same selector as Aave V2 `deposit(uint256)` — disambiguate by address.** |
| `0x2f4f21e2` | `depositFor(address,uint256)` | trusted-operator only. |
| `0xdb006a75` | `redeem(uint256)` | Burn LP; CreditVault.pay → caller. Emits `SharesBurned`. |
| `0x52c08bb4` | `redeemTo(uint256,address)` | trusted-operator only. |
| `0x8fcb4e5b` | `transferShares(address,uint256)` | Transfer raw shares. Emits `TransferShares` + `Transfer`. |
| `0xc8cc5cd8` | `distributeYield(uint256)` | **CreditVault-only.** Adds yield to `totalUnderlying`. Emits `YieldDistributed`. |
| `0xa9059cbb` | `transfer(address,uint256)` | ERC-20 (amount = underlying-denominated). |
| `0x095ea7b3` | `approve(address,uint256)` | ERC-20. |
| `0x8fcc9cfb` | `setMinDeposit(uint256)` | owner. |
| `0x86b6541d` | `setMinRedeemInterval(uint256)` | owner. |
| `0x16a1075a` | `setEarlyWithdrawFeeBips(uint256)` | owner (≤ 1000 = 10%). |
| `0x9b76f184` | `setTrustedOperator(address[],bool[])` | owner. |
| `0xeb8aa818` | `setRedeemCooldownExempt(address[],bool[])` | owner. |
| `0x7e1b22ee` | `withdrawEarlyFees(address)` | owner. |
| `0x69026e88` / `0x5157ced5` | `pauseDeposit()` / `unpauseDeposit()` | owner. |
| `0x32ec84d2` / `0xaf3345d1` | `pauseRedeem()` / `unpauseRedeem()` | owner. |
| `0x79ba5097` | `acceptOwnership()` | Ownable2Step. |

### 2.4 NativeLPToken — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x70a08231` | `balanceOf(address)` | **underlying value** of the account's shares (rebasing), NOT share count. |
| `0xf5eb42dc` | `sharesOf(address)` | raw share count. |
| `0xce7c2ac2` | `shares(address)` | raw shares (public mapping). |
| `0x18160ddd` | `totalSupply()` | = `totalUnderlying()` (underlying-denominated). |
| `0xc70920bc` | `totalUnderlying()` | total underlying backing all shares. |
| `0x3a98ef39` | `totalShares()` | total shares outstanding. |
| `0x3ba0b9a9` | `exchangeRate()` | `totalUnderlying*1e18/totalShares` (1e18 = 1:1). |
| `0xbfcd2542` | `getUnderlyingByShares(uint256)` | shares → underlying. |
| `0x761487e0` | `getSharesByUnderlying(uint256)` | underlying → shares. |
| `0x6f307dc3` | `underlying()` | underlying ERC-20 address. |
| `0xe2498f72` | `creditVault()` | the CreditVault this LP token funds. |
| `0x313ce567` | `decimals()` | matches underlying decimals. |
| `0x416f4059` | `earlyWithdrawFeeBips()` | |
| `0xd1781c39` | `accEarlyWithdrawFee()` | |
| `0x3d37a45d` | `minRedeemInterval()` | |
| `0x41b3d185` | `minDeposit()` | |
| `0x02befd24` / `0xb235d468` | `depositPaused()` / `redeemPaused()` | |
| `0xb4317d53` | `trustedOperators(address)` | `bool` |
| `0x655d8dec` | `lastDepositTimestamp(address)` | `uint256` |
| `0x877ce6d7` | `redeemCooldownExempt(address)` | `bool` |
| `0x8da5cb5b` | `owner()` | `address` |

---

## 3. Addresses per chain

`CreditVault` is the same vanity-ish prefix per chain but **NOT** a CREATE2-identical address across chains (each chain has a distinct CreditVault address). LP-token addresses **do collide across chains** in several cases (same address, different underlying) because they were deployed by the same EOA at the same nonce — **always key on `(chainId, address)`**, never address alone. All verified via `eth_getCode` / `eth_call` on the per-chain publicnode RPC on 2026-06-02.

**Shared across ETH + BNB + Base** (not Arbitrum): `owner()` = `0x4df7557734b382eb542bea6c74786d398df4cc19`. **Arbitrum owner differs:** `0xd085195edabf4b9f0673b8b8b7da077c292967cd`. **Signer is identical on all four chains:** `0x0b89c5eb76b15a4b09b05b01c953e19dedf80a5e`.

### 3.1 Ethereum (chain ID 1) — CreditVault `0xe3D41d19564922C9952f692C5Dd0563030f5f2EF` · **27 LP tokens**

owner `0x4df7…cc19` · signer `0x0b89…0a5e` · ~20 KB, not a proxy.

| LP token | symbol | dec | underlying |
|----------|--------|-----|------------|
| `0x5994258ec80cc6853e2b6f047ec6d213fe89b24b` | NT-LP-WETH | 18 | WETH `0xc02aaa39…756cc2` |
| `0xf2ab5792bd09444c89e0142cfbffd9b192ad049c` | NT-LP-WBTC | 8 | WBTC `0x2260fac5…2c599` |
| `0x4e041b2e9a366cd80b8fa01bb7bebb8eb4c1243d` | NT-LP-USDT | 6 | USDT `0xdac17f95…31ec7` |
| `0x91f70f89915f8e5fc9fdd8078685067a49cc6c28` | NT-LP-USDC | 6 | USDC `0xa0b86991…06eb48` |
| `0x319fc7782936895cbe5dcd850806cb9f32aadfea` | NT-LP-WUSD | 18 | WUSD `0x7cd017ca…898c41` |
| `0x2dad22cac847dcb840697dbc2af330d2cc205e5d` | NT-LP-STONE | 18 | STONE `0x71229856…145bd3c` |
| `0x66550d6453dbb70103b96fac81052f106d4fffeb` | NT-LP-STO | 18 | STO `0x1d88713b…b4534d` |
| `0xb3c455dd8e45524264cad476195aa7c4bd27d2a8` | NT-LP-DODO | 18 | DODO `0x43dfc415…7d4ddd` |
| `0xdd3dc634c127c999643c99b115eca98fa14b7958` | NT-LP-MANTA | 18 | MANTA `0x95cef134…c544e5` |
| `0x2aeae5768ee738bc9d9e9213230f52759ddef2b0` | NT-LP-PLUME | 18 | PLUME `0x4c1746a8…4ea5f1` |
| `0xef312bd7966cbfaf6bff39e8b5db18cb868f3e85` | NT-LP-RDO | 18 | RDO `0x57240c3e…34a334` |
| `0x6266845c903258a882b1edff2ce2caa7d99f9250` | NT-LP-SOPH | 18 | SOPH `0x6b7774cb…ddd3f0` |
| `0x1ba406ee00676982b2e03a5293f98ddbab005134` | NT-LP-stETH | 18 | stETH `0xae7ab965…d7fe84` |
| `0x59bf9bf6ce452ee559a19dc49bb438316b8bed94` | NT-LP-SKATE | 18 | SKATE `0x61dbbbb5…cef285` |
| `0xa2efe8e37f247cb51c2a48692301335292ccb630` | NTLP-WLFI | 18 | WLFI `0xda5e1988…7cbef6` |
| `0xa28b752bb407e26bfae5b8684716680a3984d7ef` | NTLP-LINEA | 18 | LINEA `0x1789e004…afbb04` |
| `0x716338b2298586455097a0717b8891782dd025a9` | NTLP-USDe | 18 | USDe `0x4c9edd58…1e68b3` |
| `0xe0ded29b7d5bc1f0227064c03cda3e17acd2c129` | NTLP-LINK | 18 | LINK `0x51491077…f986ca` |
| `0xa6f3e1e5f3cdac4e3cbbc47839d5558ab33abd09` | NTLP-ENA | 18 | ENA `0x57e114b6…1e6061` |
| `0x014b16e50eab39657e18c66c1dd744ad2b6362aa` | NTLP-wstETH | 18 | wstETH `0x7f39c581…35e2ca0` |
| `0x24b6b8e99f92fbbc0aa5b49a23a65e2e1bcc8527` | NLP-STONEUSD | 18 | STONEUSD `0x6a6e3a43…38721e` |
| `0x3cf346f0003689aca41faf4d88d57b7d2abba441` | NLP-nBRIDGE | 18 | nBRIDGE `0xfb38835e…1b5848` |
| `0x6ea0daa532d368c38d73eb27ecfc23e3ee9fc4f7` | NLP-cbBTC | 8 | cbBTC `0xcbb7c000…ed33bf` |
| `0xb2655c3e9c1fb6372b6b9b6b73bcee0bf1de7655` | NLP-USAT | 6 | USAT `0x07041776…72a8b68` |
| `0xb4e72ab89d945a552a5f87101e7ad6fa9b2f13d0` | NLP-BARD | 18 | BARD `0xf0db65d1…6e9754` |
| `0xeea56d9b036ae933d4e6cdaf1ca3a46fa0d7a480` | NLP-TSLAon | 18 | TSLAon `0xf6b1117e…21103f` |
| `0x79292d171531673ff97035315fda568189c3c8a5` | NLP-TSLAx | 18 | TSLAx `0x8ad3c73f…eb7cf0` |

### 3.2 BNB Smart Chain (chain ID 56) — CreditVault `0xBA8dB0CAf781cAc69b6acf6C848aC148264Cc05d` · **44 LP tokens**

owner `0x4df7…cc19` · signer `0x0b89…0a5e` · ~20 KB, not a proxy. Largest deployment by market count. (Full per-token list omitted for length — enumerate live via `allLPTokens`.) Representative / notable markets:

| LP token | symbol | dec | underlying |
|----------|--------|-----|------------|
| `0xea91132e79559be0fcd6b1237ded28a31a226644` | NT-LP-WBNB | 18 | WBNB `0xbb4cdb9c…3bc095c` |
| `0xa921077a331f36d80e44f914a7ab1b3c9ea48a4a` | NT-LP-ETH | 18 | ETH `0x2170ed08…f933f8` |
| `0x5994258ec80cc6853e2b6f047ec6d213fe89b24b` | NT-LP-USDT | 18 | USDT `0x55d39832…197955` |
| `0xf2ab5792bd09444c89e0142cfbffd9b192ad049c` | NT-LP-USDC | 18 | USDC `0x8ac76a51…cd580d` |
| `0x4e041b2e9a366cd80b8fa01bb7bebb8eb4c1243d` | NT-LP-BTCB | 18 | BTCB `0x7130d2a1…3ead9c` |
| `0xca4f5090ba400cd7ccfe4ca0ff811bc307cd689e` | NT-LP-DOGE | 8 | DOGE `0xba2ae424…744c43` |
| `0xd547727b926648af3f31dbb89e3b93e49f78dcb8` | NT-LP-USD1 | 18 | USD1 `0x8d0d000e…f08b0d` |
| `0xa11f7cde7402093ff4d24a91fd8cdcc8aa0c96a8` | NLP-sQQQ | 18 | sQQQ `0x7ade93a8…ccf7ce` |
| … (44 total: incl. PARTI, SHELL, HAEDAL, BANK, DOOD, SIGN, SOON, RDO, SKATE, USDV, SAHARA, KOGE, WLFI, MTP, U, nBRIDGE, STONEUSD, plus many `sXXX` tokenized-equity markets: sAAPL, sBMNR, sALTS, sNVDA, sTSLA, sCOIN, sCRCL, sSBET, sGLXY, sBNC, sINTC, sCOPX, sBLSH; and wrapped `wNLP-*` markets) | | | |

> **Note:** several BNB LP-token addresses **collide with Ethereum LP tokens** (`0x5994258e…` = NT-LP-USDT on BNB but NT-LP-WETH on ETH; `0xf2ab5792…` = NT-LP-USDC on BNB but NT-LP-WBTC on ETH; `0x4e041b2e…`, `0x014b16e5…`, `0xa2efe8e3…`, `0x3cf346f0…`, `0xd547727b…`, `0xa11f7cde…` also recur). Same address, **different underlying / different chain** — never resolve an LP token by address alone.

### 3.3 Arbitrum One (chain ID 42161) — CreditVault `0xbA1cf8A63227b46575AF823BEB4d83D1025eff09` · **5 LP tokens**

owner `0xd085…67cd` (**differs from ETH/BNB/Base**) · signer `0x0b89…0a5e` · ~19.5 KB, not a proxy.

| LP token | symbol | dec | underlying |
|----------|--------|-----|------------|
| `0x8a5fca5429f5d572f71959bfec41495420528ce2` | NT-LP-WETH | 18 | WETH `0x82af4944…3fbab1` |
| `0xc6ab8b93d2c5477b887aea4b66977d6e37bbcf97` | NT-LP-USDC | 6 | USDC `0xaf88d065…8e5831` |
| `0xc9452fa182b0f8201f2e15700671570699aa10b5` | NT-LP-USDT | 6 | USD₮0 `0xfd086bc7…9fcbb9` |
| `0xe50ac1132062055d8472c58cb8430b619e5d385e` | NTLP-WBTC | 8 | WBTC `0x2f2a2543…fc5b0f` |
| `0xbe131fa991aa1871bbf01f0a89fb0be641875751` | NLP-nBRIDGE | 18 | nBRIDGE `0xfb38835e…1b5848` |

### 3.4 Base (chain ID 8453) — CreditVault `0x74a4Cd023e5AfB88369E3f22b02440F2614a1367` · **5 LP tokens**

owner `0x4df7…cc19` · signer `0x0b89…0a5e` · ~19.5 KB, not a proxy.

| LP token | symbol | dec | underlying |
|----------|--------|-----|------------|
| `0x7f1bcc60ed3c80da906fd91a2ec63ec71442430a` | NT-LP-WETH | 18 | WETH `0x42000000…000006` |
| `0x6833e3e3f2a048df8d5dfdef466b73936b2224e6` | NT-LP-USDC | 6 | USDC `0x833589fc…a02913` |
| `0x96a068b3936bffd6b29ca7d451206ad5c5049080` | NT-LP-USDT | 6 | USDT `0xfde4c96c…99bb2` |
| `0xca135c6520dd03f7e25fbb44c63f7b51e5ad86de` | NTLP-cbBTC | 8 | cbBTC `0xcbb7c000…ed33bf` |
| `0x5593ddb6e5a1a0cf71a3e0bc7f0f936a06aa9f0b` | NLP-nBRIDGE | 18 | nBRIDGE `0xfb38835e…1b5848` |

### 3.5 Avalanche (43114), Optimism (10), Polygon PoS (137) — **NOT DEPLOYED**

`eth_getCode` = `0x` for all four candidate CreditVault addresses on each of these three chains (2026-06-02). The official addresses page lists Credit Pool/CreditVault only for Ethereum, BNB, Arbitrum, and Base. **No Native Credit Pool on Avalanche, Optimism, or Polygon.** (Native's swap-side products may differ — out of scope.)

---

## Cross-chain summary

| Chain | ID | RPC verified | CreditVault | LP tokens | owner | not a proxy |
|-------|----|--------------|-------------|-----------|-------|-------------|
| Ethereum | 1 | ✓ | `0xe3D41d19…f5f2EF` | 27 | `0x4df7…cc19` | ✓ |
| BNB Smart Chain | 56 | ✓ | `0xBA8dB0CA…4Cc05d` | 44 | `0x4df7…cc19` | ✓ |
| Arbitrum One | 42161 | ✓ | `0xbA1cf8A6…25eff09` | 5 | `0xd085…67cd` | ✓ |
| Base | 8453 | ✓ | `0x74a4Cd02…14a1367` | 5 | `0x4df7…cc19` | ✓ |
| Avalanche C-Chain | 43114 | ✓ | **absent** (`0x`) | — | — | — |
| Optimism | 10 | ✓ | **absent** (`0x`) | — | — | — |
| Polygon PoS | 137 | ✓ | **absent** (`0x`) | — | — | — |

CreditVault addresses are **distinct per chain** (no CREATE2 identity). LP-token addresses **partially collide** between ETH and BNB (same deployer/nonce, different underlying). Signer `0x0b89…0a5e` is shared across all four deployed chains; owner is shared on ETH/BNB/Base but distinct on Arbitrum.

---

## Proxies (old & new)

**Neither contract is a proxy.** Verified on every deployed chain:

| Evidence | Result |
|----------|--------|
| `eth_getStorageAt(CreditVault, 0x360894…bbc)` (EIP-1967 impl) | `0x000…000` (empty) on ETH/BNB/ARB/Base |
| `eth_getStorageAt(CreditVault, 0xb53127…6103)` (EIP-1967 admin) | `0x000…000` (empty) on ETH/BNB/ARB/Base |
| `eth_getStorageAt(NativeLPToken, 0x360894…bbc)` | `0x000…000` (empty) |
| Bytecode size | CreditVault ~20 KB (ETH/BNB) / ~19.5 KB (ARB/Base); LP token ~21 KB — full logic contracts, not minimal forwarders |
| Source | `CreditVault is ICreditVault, EIP712, Ownable2Step, ReentrancyGuardTransient` — no `UUPSUpgradeable`/`Initializable`/proxy imports; `constructor()` sets EIP712 domain (a proxy would use an initializer) |

**Implication:** there is **no `Upgraded(address)` / `AdminChanged` / `Initialized` event to monitor, and no impl slot to read.** A "version upgrade" = a **brand-new CreditVault deployment at a new address** + new LP tokens + re-listing (`MarketListed`) + owner re-pointing the swap-side credit pools. To catch an upgrade, watch for a **new CreditVault address** appearing in the docs / a new `MarketListed` cluster, and for `OwnershipTransferStarted/Transferred` and `SignerSet` on the live vault. The only "delegated authority" surfaces are off-chain roles: `signer` (EIP-712 credit engine), `epochUpdater`, `feeWithdrawer`, plus the `creditPools` whitelist linking to the swap side.

---

## Detection invariants & gotchas

1. **Liquidation = the `Liquidated` event (topic0 `0xb5689a01…`), liquidator-only + EIP-712 signed.** There is no Aave-style `liquidationCall` health-factor read on-chain; the off-chain `signer` authorizes it. `request.claimCollaterals` is the seized collateral; `request.positionUpdates` is the debt closure. Attribute the liquidator from the event's second field (and `liquidatorToRecipient[liquidator]` for where funds go).
2. **Position is a signed int, not a debt balance.** `positions[trader][token]` < 0 means the trader is **short/borrowing** that token; > 0 means long. `settle`/`repay`/`liquidate` move a position **toward zero without flipping its sign** (enforced in `_updatePositions`). There is no separate "debt token."
3. **`addCollateral` is permissionless; the other three trader ops are signed.** Anyone can `addCollateral` for any whitelisted trader, but `settle`/`removeCollateral`/`liquidate` require a fresh `signer` signature (nonce + deadline, replay-guarded by `nonces`). A `SignerSet` event is a security-critical rotation — **monitor it**.
4. **Per-asset LP tokens, one per underlying.** Every market is its own `NativeLPToken` contract; the same event topic0 fires on dozens of addresses per chain. **Always filter LP events by `(chainId, lpToken address)`**, and resolve the underlying via `underlying()` — never assume from the symbol.
5. **LP-token addresses collide across chains** (ETH `0x5994258e…` = NT-LP-WETH; BNB `0x5994258e…` = NT-LP-USDT). Key on `(chainId, address)`.
6. **LP `Transfer.value` and `balanceOf` are underlying-denominated, not shares.** This is a rebasing-by-exchange-rate token: `balanceOf = shares * totalUnderlying / totalShares`. For accounting use `sharesOf()` / `shares()`, exactly like stETH. `totalSupply()` returns `totalUnderlying`, which *grows on every `YieldDistributed`* with no `Transfer`/mint event — do not treat supply growth as a mint.
7. **Yield has no token transfer.** `YieldDistributed` just bumps `totalUnderlying` (the underlying is already in the vault from borrow fees). Don't expect an ERC-20 transfer into the LP contract — it never holds underlying; the vault does.
8. **Deposits/redeems move underlying via the CreditVault, not the LP token.** `deposit` does `underlying.transferFrom(user → CreditVault)`; `redeem` calls `CreditVault.pay(to, amount)`. So a user deposit shows an ERC-20 `Transfer` to the **CreditVault** address, not the LP token. The `pay` selector `0xc4076876` on the vault is LP-token-only.
9. **`swapCallback` mutates vault state silently (no event).** Swap-side credit pools call `swapCallback` to change `positions` after a swap. Position changes therefore originate from *two* sources: explicit lending ops (which emit events) and swaps (which don't). To fully reconstruct positions you must trace `swapCallback` calls or watch the swap-side contracts (separate doc). The `creditPools` whitelist + `CreditPoolUpdated` event identify which addresses can do this.
10. **`EpochUpdated` is the funding-fee heartbeat** (8-hour `EPOCH_UPDATE_INTERVAL`, enforced per trader). It both charges traders' positions (`positions[trader][token] -= fee`) and credits LPs (`distributeYield`). The exchange-rate increase per epoch is capped at **+1%** (`ExchangeRateIncreaseTooMuch` revert) — a useful sanity bound.
11. **`deposit(uint256)` selector `0xb6b55f25` is identical to Aave V2's `deposit(uint256)`** and other single-arg deposit fns. Always disambiguate by the emitting/target address being a known `NativeLPToken`.
12. **No oracle / no ERC-4626 / no factory contract on-chain.** Pricing and credit health live off-chain behind the `signer`. Do not look for a Native price-feed, ERC-4626 vault, or LP-token factory — none exist. LP tokens are deployed standalone and registered via `supportMarket` → `MarketListed`.
13. **Not a proxy → upgrades are redeploys.** No `Upgraded`/`Initialized` events. A migration appears as a new CreditVault address + new `MarketListed` events on a new contract. Track the docs addresses page and `OwnershipTransferred`/`SignerSet` on the live vault.
14. **Arbitrum has a different `owner()`** (`0xd085…67cd`) than the ETH/BNB/Base owner (`0x4df7…cc19`). Don't assume a single global admin.
15. **Activity is concentrated on Ethereum + BNB.** Base/Arbitrum CreditVaults are live but lower-volume (Base showed a single `EpochUpdated` in a 3.6M-block scan). Absence of recent `Liquidated`/`CollateralAdded` logs ≠ wrong topic0 — the signatures are source-verified and the family is confirmed live on Ethereum.

---

## Quick-copy detection constants (Postgres `\x` bytea, lowercase)

```
-- ===== CreditVault event topic0 =====
TOPIC_CV_MARKET_LISTED          = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_CV_EPOCH_UPDATED          = '\x90e0333a7f11b37e50e152c45bb5ebfc2ce2ace82e290567861d3ae852968874'
TOPIC_CV_REPAID                 = '\xc8aa82285b2a9e22e0bda601a759e4f578e78f18015e543a4f66bb120a726953'
TOPIC_CV_SETTLED                = '\x0279bcc316c233db88e8f3e463dcefc7fa661da21bc66eadc60f3835e41bba11'
TOPIC_CV_COLLATERAL_ADDED       = '\x770dafe0b413d5c277b5f1a9d1d725e5ebafe92b5a16f3ebaae6e49e43b66499'
TOPIC_CV_COLLATERAL_REMOVED     = '\x455917442c530b052ee826d2556fad794f64a294e455930a63599688abbffa3c'
TOPIC_CV_LIQUIDATED             = '\xb5689a012cf77dd0a99ac07ed6f83009d7fbfca323bca73b34d6ed02bf413ab8'
TOPIC_CV_CREDIT_POOL_UPDATED    = '\x947aca305c9b8d94b31792a7f80d331c9452e743508d61331561378673b50103'
TOPIC_CV_REBALANCE_CAP_UPDATED  = '\x39ff4a05a64bdf7e1dcb0b2d6b7e35b6a720a9412386a9e193c0e93d29a18470'
TOPIC_CV_TRADER_SET             = '\x2353ec0fe56a376d3269d3e65521f1ce07dc5f544cc5b0ba4eb2ff03f771a4ad'
TOPIC_CV_LIQUIDATOR_SET         = '\x81e020344174972c59f6c11a8f6c90b141866214e3d9b544d030f0b532f5a10f'
TOPIC_CV_SIGNER_SET             = '\x9eaa897564d022fb8c5efaf0acdb5d9d27b440b2aad44400b6e1c702e65b9ed3'
TOPIC_CV_EPOCH_UPDATER_SET      = '\x538bd377a1e0d2ceca49908f540bafa1d8616cf49a7bcefcd0b479e7531ff8aa'
TOPIC_CV_FEE_WITHDRAWER_SET     = '\x15d0b1a02a4902c4788ceda199eb43e4a753d86c0dbb7412e8ba63feecb070fa'
TOPIC_CV_RESERVE_WITHDRAWN      = '\xde13184e8cbb6eccbcecfc796bf8820e5ffde0534c01b4fabed4b05982964a44'

-- ===== NativeLPToken event topic0 =====
TOPIC_LP_SHARES_MINTED          = '\xd9c8415d46bc958abafa67ce0dad25daa34cd66edf0fba6e9bf3cc0fc8bfe1e0'
TOPIC_LP_SHARES_BURNED          = '\xdf98f11672c77edcc0f4ed1da404198a75887435a8da9173ef3d22969dcf318c'
TOPIC_LP_TRANSFER_SHARES        = '\x9d9c909296d9c674451c0c24f02cb64981eb3b727f99865939192f880a755dcb'
TOPIC_LP_YIELD_DISTRIBUTED      = '\xe8ed0a697f15301f06fd3d30bc896682e7826c5397076a3eda05844cfc356480'
TOPIC_LP_TRUSTED_OPERATOR_UPD   = '\x2e4746592fbf3f346fff4993672957b8e58f533eaaca7a25d1676602f1150a03'
TOPIC_LP_REDEEM_COOLDOWN_EXEMPT = '\xce0277a65558e646cf52d00a8e5a74cc06c339d7a6277d7333af0d81cad38ed4'
TOPIC_LP_EARLY_FEE_WITHDRAWN    = '\x1c40b92055dd2c2d8499b55a470506571b2bf68a1bc75af8a0b314760dd5f1cb'
-- shared ERC-20 / Ownable2Step
TOPIC_TRANSFER                  = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_APPROVAL                  = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_OWNERSHIP_TRANSFER_STARTED= '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'
TOPIC_OWNERSHIP_TRANSFERRED     = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'

-- ===== CreditVault selectors =====
SEL_CV_SETTLE                   = '\x9be41fdb'
SEL_CV_REPAY                    = '\x81377bfd'
SEL_CV_ADD_COLLATERAL           = '\xb6bdff03'
SEL_CV_REMOVE_COLLATERAL        = '\x4e293ee9'
SEL_CV_LIQUIDATE                = '\x12411772'
SEL_CV_EPOCH_UPDATE             = '\x98221e94'
SEL_CV_SWAP_CALLBACK            = '\x7362ecbe'
SEL_CV_PAY                      = '\xc4076876'
SEL_CV_SUPPORT_MARKET           = '\xcab4f84c'
SEL_CV_WITHDRAW_RESERVE         = '\xae1914f8'
SEL_CV_SET_CREDIT_POOL          = '\xabb49f19'
SEL_CV_SET_TRADER               = '\xc2b73076'
SEL_CV_SET_LIQUIDATOR           = '\x47de43e2'
SEL_CV_SET_SIGNER               = '\x6c19e783'
SEL_CV_POSITIONS                = '\x4bd21445'
SEL_CV_COLLATERAL               = '\xcc218ece'
SEL_CV_LP_TOKENS                = '\xb17b658d'
SEL_CV_ALL_LP_TOKENS            = '\x9246261c'
SEL_CV_SIGNER                   = '\x238ac933'

-- ===== NativeLPToken selectors =====
SEL_LP_DEPOSIT                  = '\xb6b55f25'
SEL_LP_DEPOSIT_FOR              = '\x2f4f21e2'
SEL_LP_REDEEM                   = '\xdb006a75'
SEL_LP_REDEEM_TO                = '\x52c08bb4'
SEL_LP_TRANSFER_SHARES          = '\x8fcb4e5b'
SEL_LP_DISTRIBUTE_YIELD         = '\xc8cc5cd8'
SEL_LP_SHARES_OF                = '\xf5eb42dc'
SEL_LP_EXCHANGE_RATE            = '\x3ba0b9a9'
SEL_LP_UNDERLYING               = '\x6f307dc3'
SEL_LP_CREDIT_VAULT             = '\xe2498f72'
SEL_LP_TOTAL_UNDERLYING         = '\xc70920bc'
SEL_LP_TOTAL_SHARES             = '\x3a98ef39'

-- ===== Proxy slots (both empty on all deployments — NOT proxies) =====
EIP1967_IMPL_SLOT               = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT              = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Roles (across deployed chains) =====
NATIVE_SIGNER_ALL_CHAINS        = '\x0b89c5eb76b15a4b09b05b01c953e19dedf80a5e'
NATIVE_OWNER_ETH_BNB_BASE       = '\x4df7557734b382eb542bea6c74786d398df4cc19'
NATIVE_OWNER_ARBITRUM           = '\xd085195edabf4b9f0673b8b8b7da077c292967cd'

-- ===== CreditVault addresses =====
ETH_CREDIT_VAULT                = '\xe3d41d19564922c9952f692c5dd0563030f5f2ef'   -- 27 LP tokens
BNB_CREDIT_VAULT                = '\xba8db0caf781cac69b6acf6c848ac148264cc05d'   -- 44 LP tokens
ARB_CREDIT_VAULT                = '\xba1cf8a63227b46575af823beb4d83d1025eff09'   -- 5 LP tokens
BASE_CREDIT_VAULT               = '\x74a4cd023e5afb88369e3f22b02440f2614a1367'   -- 5 LP tokens
-- NOT deployed on Avalanche(43114) / Optimism(10) / Polygon(137): eth_getCode = 0x

-- ===== Sample LP tokens (enumerate full set via allLPTokens per chain) =====
ETH_NTLP_WETH                   = '\x5994258ec80cc6853e2b6f047ec6d213fe89b24b'
ETH_NTLP_USDC                   = '\x91f70f89915f8e5fc9fdd8078685067a49cc6c28'
ETH_NTLP_USDT                   = '\x4e041b2e9a366cd80b8fa01bb7bebb8eb4c1243d'
ETH_NTLP_WBTC                   = '\xf2ab5792bd09444c89e0142cfbffd9b192ad049c'
BASE_NTLP_WETH                  = '\x7f1bcc60ed3c80da906fd91a2ec63ec71442430a'
BASE_NTLP_USDC                  = '\x6833e3e3f2a048df8d5dfdef466b73936b2224e6'
ARB_NTLP_WETH                   = '\x8a5fca5429f5d572f71959bfec41495420528ce2'
ARB_NTLP_USDC                   = '\xc6ab8b93d2c5477b887aea4b66977d6e37bbcf97'
BNB_NTLP_WBNB                   = '\xea91132e79559be0fcd6b1237ded28a31a226644'
BNB_NTLP_USDT                   = '\x5994258ec80cc6853e2b6f047ec6d213fe89b24b'   -- collides w/ ETH NT-LP-WETH addr
```

---

## Verification & sources

How every constant was verified (2026-06-02):

- **Source:** `github.com/Native-org/native-v2-core` (cloned `main`, depth 1) — `src/CreditVault.sol`, `src/NativeLPToken.sol`, `src/interfaces/ICreditVault.sol`, `src/libraries/ConstantsLib.sol`. solc 0.8.28. Both contracts are `Ownable2Step` + transient `ReentrancyGuard`; CreditVault is also `EIP712("Native Credit Vault","1")`. **No proxy/upgradeable base classes** in either inheritance chain.
- **Topic0 / selectors:** computed locally with `pycryptodome` keccak-256 from the canonical signatures (tuples expanded; `uint`→`uint256`; no names/spaces; `indexed` dropped for hashing).
- **Live topic0 cross-check (`eth_getLogs`):** on the **Ethereum** CreditVault — observed `Settled` (21), `Repaid` (18), `EpochUpdated` (94), `MarketListed` (6), `TraderSet` (2), `CreditPoolUpdated` (2), `OwnershipTransferred`, `OwnershipTransferStarted` in a recent ~1.2M-block window; `EpochUpdated` also observed live on BNB and Base. On an **Ethereum** LP token (`NT-LP-USDC` `0x91f70f89…`) — observed `SharesMinted` (54), `SharesBurned` (32), `TransferShares` (23), `YieldDistributed` (101), `Transfer` (23), `TrustedOperatorUpdated`, `RedeemCooldownExemptUpdated`. This proves the computed signatures appear in real logs.
- **Addresses + LP-token enumeration:** `eth_call` `allLPTokens(uint256)` walked to revert on each chain (ETH 27, BNB 44, ARB 5, Base 5); each LP token's `symbol()`/`underlying()`/`decimals()`/`creditVault()` read live; vault `owner()`/`signer()` read live.
- **Deployment presence:** `eth_getCode` non-empty on ETH/BNB/ARB/Base CreditVaults (~19.5–20 KB) and on sampled LP tokens (~21 KB); `0x` for all four candidate addresses on Avalanche/Optimism/Polygon.
- **Proxy classification:** `eth_getStorageAt` EIP-1967 impl slot `0x360894…bbc` and admin slot `0xb53127…6103` both `0x000…000` on every CreditVault and on the sampled LP token → **not proxies**; corroborated by source (no UUPS/initializer) and by the large full-logic bytecode.
- **Docs:** [`docs.native.org/native-dev/resources/addresses`](https://docs.native.org/native-dev/resources/addresses) (CreditVault listed for Ethereum, BNB, Arbitrum, Base only) · [Native Credit Pool](https://docs.native.org/native-dev/solution/native-credit-pool) · repo `README.md`.

### Verification.1 Deep-research fact-check (2026-06-02) — ✅ all lending-side claims confirmed, no corrections

6 non-obvious claims were cross-checked against the official docs, the `Native-org/native-v2-core` repo,
DefiLlama, and block explorers. Verdicts:

1. **Lending-side contract set is complete (CreditVault + per-asset NativeLPToken; no oracle/factory/4626).**
   — ✅ confirmed. `native-v2-core` ships only `CreditVault.sol` + `NativeLPToken.sol`; the org has just two
   public repos. No separate oracle, liquidation-engine, or ERC-4626 contract is published or referenced.
2. **No Native governance/token/staking contract** belongs in this doc. — ✅ confirmed (no `NATIVE`/`N`
   ERC-20, airdrop, or staking contract found in docs, GitHub, or search as of 2026-06-02).
3. **CreditVault is credit-based: MMs borrow up to an off-chain credit limit, EIP-712 `signer`-authorized,
   no on-chain oracle.** — ✅ confirmed from verified source (no oracle import; `signer` gates
   settle/removeCollateral/liquidate).
4. **CreditVault + all NativeLPTokens are immutable (not proxies).** — ✅ confirmed (EIP-1967 slots empty;
   re-read live on ETH CreditVault).
5. **NativeLPToken is a rebasing exchange-rate token, yield from borrow fees.** — ✅ confirmed (source +
   live `YieldDistributed` with no `Transfer`).
6. **CreditVault addresses (ETH/BNB/Arb/Base) are current**; absent on Avalanche/Optimism/Polygon.
   — ✅ confirmed (match the live docs page verbatim; `eth_getCode = 0x` re-confirmed on the 3 absent
   chains, incl. a fresh re-check of the ETH vault returning bytecode and the Avalanche candidate returning
   `0x`). ⚠️ *Scope note:* DefiLlama historically also lists Native volume on **Mantle/Monad/ZetaChain/
   zkLink Nova** — all **outside the seven target chains** and **not** in Native's docs; out of scope here.

**Net corrections folded in:** none — all lending-side claims confirmed.

Authoritative sources:
- GitHub: [Native-org/native-v2-core](https://github.com/Native-org/native-v2-core)
- Docs: [Addresses](https://docs.native.org/native-dev/resources/addresses) · [Audits](https://docs.native.org/native-dev/resources/audits)
- Explorers: [Etherscan CreditVault](https://etherscan.io/address/0xe3D41d19564922C9952f692C5Dd0563030f5f2EF) · [BscScan](https://bscscan.com/address/0xBA8dB0CAf781cAc69b6acf6C848aC148264Cc05d) · [Arbiscan](https://arbiscan.io/address/0xbA1cf8A63227b46575AF823BEB4d83D1025eff09) · [Basescan](https://basescan.org/address/0x74a4Cd023e5AfB88369E3f22b02440F2614a1367)
</content>
</invoke>
