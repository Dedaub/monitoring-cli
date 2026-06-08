# Seamless Leverage Tokens (Morpho-powered ILM) — Topics, Selectors, Addresses (Base + Ethereum)

**Status:** verified against Base + Ethereum mainnet RPC and the canonical `seamless-protocol/leverage-tokens` GitHub repo (source + Foundry broadcasts) on 2026-06-08. Non-obvious claims additionally cross-checked against primary sources — see §9.
**Scope:** Seamless's **current** product — the **Leverage Token** protocol ("Integrated Liquidity Markets" successor), an ERC-20-tokenised leveraged-position factory built on top of **Morpho** lending. Deployed on **Base (8453)** and **Ethereum (1)** only. `eth_getCode` = `0x` for every Leverage-Token contract on **BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137)** (verified 2026-06-08). Topics + selectors are chain-agnostic; addresses are network-specific. The legacy Aave-V3-fork lending market is a separate, deprecated product — see [v1.md](v1.md). The **Seamless Morpho Vaults** (smUSDC/smcbBTC/smWETH) are standard MetaMorpho V1.1 vaults — addresses in §5; their event/selector ABI is the MetaMorpho one in [../morpho/v1.md](../morpho/v1.md).

A Leverage Token is an ERC-20 representing a share of a leveraged position between two assets (collateral vs debt). The **`LeverageManager`** is the singleton core: it creates LeverageTokens permissionlessly and routes user mint/redeem/rebalance, relying only on price data. Each LeverageToken is configured at creation with a **`LendingAdapter`** (here always a **`MorphoLendingAdapter`** — owns the actual Morpho collateral/debt position) and a **`RebalanceAdapter`** (defines rebalance triggers/auction logic). LeverageTokens are deployed as **beacon proxies** by a **`BeaconProxyFactory`** (the beacon is the factory itself), so a single beacon upgrade re-points every LeverageToken atomically. The `LeverageManager`, `RebalanceAdapter` and `BeaconProxyFactory` are upgradeable; everything else (adapters, periphery) is immutable.

> **DEPRECATED / WINDING DOWN (verified 2026-06-08).** On **2026-04-07** Seamless announced an orderly wind-down, explicitly citing **insufficient product-market fit for the Leverage Tokens product** as a primary reason. The web app goes **offline 2026-06-30**; users must withdraw before then (afterward = "manual contract interaction"). The contracts are **live and functional on-chain** (read 2026-06-08) but in withdraw-only twilight. Monitor for redemptions, not growth.

> **Address-reuse trap (verified on-chain 2026-06-08):** the Base and Ethereum deployments were executed with the **same deployer at matching nonces**, so several addresses are **reused across chains with DIFFERENT roles**. E.g. `0x5C37EB148D4a261ACD101e2B997A0F163Fb3E351` is the **LeverageManager PROXY on Ethereum** but the **LeverageManager IMPLEMENTATION on Base**; `0x603Da735780e6bC7D04f3FB85C26dccCd4Ff0a82` is the **LeverageToken factory PROXY on Ethereum** but the **LeverageToken implementation on Base**; `0xfE9101349354E278970489F935a54905DE2E1856` is the **LeverageToken impl on Ethereum** but the **LeverageManager impl on Base**. **Always key on `(chainId, address, role)` — never assume an address means the same thing on both chains.** See §3/§4.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally with keccak on 2026-06-08. Struct params are hashed as tuples: `ActionData = (uint256,uint256,uint256,uint256,uint256)`; `LeverageTokenConfig = (address,address,uint256,uint256)`; `LeverageTokenState = (uint256,uint256,uint256,uint256)`; `RebalanceAction = (uint8,uint256)`; Morpho `MarketParams = (address,address,address,address,uint256)`. `LeverageTokenCreated`, `Mint`, `BeaconProxyCreated` confirmed against live `eth_getLogs` (Base + Ethereum).

### 1.1 LeverageManager (the singleton core — emits all user activity)

| topic0 | Event |
|--------|-------|
| `0xc3f4681fb2a57a13e121c6f24fe319c8572bb001497f2b74712695625ee9028e` | `LeverageTokenCreated(address indexed token, address collateralAsset, address debtAsset, (address,address,uint256,uint256) config)` |
| `0xca0d4a1151cf4e7c20fcffb441cb3e88636d136769402e584ed509f78f896f61` | `Mint(address indexed token, address indexed sender, (uint256,uint256,uint256,uint256,uint256) actionData)` |
| `0x079ed52167e1d2f9d4d371cd2dbc4fd7990aa0d8aa11416205a05bfe19343210` | `Redeem(address indexed token, address indexed sender, (uint256,uint256,uint256,uint256,uint256) actionData)` |
| `0x1ece35fa7611d2dfc7e11d022888a20c4987d6ededbb34a26c93fd53f2073899` | `Rebalance(address indexed token, address indexed sender, (uint256,uint256,uint256,uint256) stateBefore, (uint256,uint256,uint256,uint256) stateAfter, (uint8,uint256)[] actions)` |
| `0xe05417bcb646fc5b895b56d08907b31d5565751b1f2e5a7ded0d071137fe309f` | `LeverageManagerInitialized(address leverageTokenFactory)` |

> **`Mint`/`Redeem` here are LeverageManager events, NOT ERC-4626 / ERC-20.** `Mint`'s ActionData carries `(collateral, debt, shares, tokenFee, treasuryFee)`. The `token` (LeverageToken address) is indexed (topic1); `sender` is indexed (topic2). The LeverageToken ERC-20 itself emits the usual `Transfer`/`Approval`. **Attribute to the position via the indexed `token`, and to the user via `sender`** — but note `sender` is often the `LeverageRouter` (flash-loan-wrapped deposits), not the end user.

### 1.2 FeeManager (LeverageManager inherits FeeManager — same emitter address)

| topic0 | Event |
|--------|-------|
| `0x46d6b0f5c0c8ece3cf8b44ea4a05280c3827c74ffa5a3b9e9aad6ecc48505e19` | `ManagementFeeCharged(address indexed leverageToken, uint256 sharesFee)` |
| `0x054728667e9fde2ae95b0b309983329748caba1b3df19081435adb8966c61514` | `ManagementFeeSet(address indexed token, uint256 fee)` |
| `0x9dc95718df096d1d699a19543ccd8b579bc4729ce2021eb4764ff654ed67a5dc` | `LeverageTokenActionFeeSet(address indexed leverageToken, uint8 indexed action, uint256 fee)` |
| `0xbf6d4cf755450e27281b9dae24d323b14e88be4ae9f6d77cf921831fce1573f7` | `DefaultManagementFeeAtCreationSet(uint256 fee)` |
| `0x1a5a0561abf630a6abfef8235e08f578eac64aacb00875dccdea6450f1d4bde5` | `TreasuryActionFeeSet(uint8 indexed action, uint256 fee)` |
| `0x3c864541ef71378c6229510ed90f376565ee42d9c5e0904a984a9e863e6db44f` | `TreasurySet(address treasury)` |

### 1.3 LeverageToken (ERC-20 beacon proxy — one per leveraged position)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x57d9c3176493540cc7a0fba3538e0908b18dfe9468541ad54ba54fd474d33fec` | `LeverageTokenInitialized(string name, string symbol)` | LeverageToken |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | LeverageToken (ERC-20) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | LeverageToken (ERC-20) |

### 1.4 BeaconProxyFactory (= the LeverageToken factory; also the beacon)

| topic0 | Event |
|--------|-------|
| `0xfc6ca44b2e0253d7b333f816a6b6e52e7292a56fd5f38e52946f9dfc812d698b` | `BeaconProxyCreated(address indexed proxy, bytes data, bytes32 baseSalt)` (fires alongside `LeverageTokenCreated`, same block; `proxy` = new LeverageToken) |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` (the beacon's impl swap → upgrades ALL LeverageTokens) |

### 1.5 MorphoLendingAdapter & its factory (per-LeverageToken position owner)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x4936702b8ba221fe23c531f1a2d5ba3022c8e5238de7a4428155d32b367c129c` | `MorphoLendingAdapterInitialized(bytes32 indexed morphoMarketId, (address,address,address,address,uint256) marketParams, address indexed authorizedCreator)` | MorphoLendingAdapter |
| `0xa6df6ca83fcea66b6eed2551b21e0a3f078e6af9eb9dbb02d2312e3d94b5d77b` | `MorphoLendingAdapterUsed()` | MorphoLendingAdapter (flagged in-use; once per adapter) |
| `0x90a228f4b5bc611babf005ecebd48836d9c73714549183b216fec07d3ee4348c` | `MorphoLendingAdapterDeployed(address lendingAdapter)` | MorphoLendingAdapterFactory |

> The actual borrow/collateral motions land as **Morpho Blue** `Supply`/`Borrow`/`Repay`/`Withdraw`/`SupplyCollateral`/`WithdrawCollateral` events on the **Morpho singleton** (`0xBBBB…EEFFCb`), with the `MorphoLendingAdapter` as the `onBehalf`. The adapter does **not** re-emit lending events. To follow the underlying leverage flow, join Leverage `Mint`/`Redeem`/`Rebalance` → the position's `MorphoLendingAdapter` → Morpho Blue events keyed by that adapter. See [../morpho/v1.md](../morpho/v1.md).

### 1.6 Proxy / UUPS upgrade

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` (ERC-1967 — on LeverageManager UUPS proxy, the factory beacon, RebalanceAdapter) |

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

All LeverageManager + MorphoLendingAdapterFactory selectors below verified **present** in the live Base impl bytecode (`0xfE9101…`, `0xDd3341…`) on 2026-06-08.

### 2.1 LeverageManager — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x797f3af6` | `createNewLeverageToken((address,address,uint256,uint256) config, string name, string symbol)` → `address` | Permissionless. Emits `LeverageTokenCreated` + `BeaconProxyCreated`. |
| `0x0efe6a8b` | `deposit(address token, uint256 collateral, uint256 minShares)` → `ActionData` | Emits `Mint`. |
| `0x156e29f6` | `mint(address token, uint256 shares, uint256 maxCollateral)` → `ActionData` | Emits `Mint`. |
| `0x2b83cccd` | `redeem(address token, uint256 shares, uint256 minCollateral)` → `ActionData` | Emits `Redeem`. |
| `0xb5c5f672` | `withdraw(address token, uint256 collateral, uint256 maxShares)` → `ActionData` | Emits `Redeem`. |
| `0x42cff3f8` | `rebalance(address token, (uint8,uint256)[] actions, address tokenIn, address tokenOut, uint256 amountIn, uint256 amountOut)` | **Permissionless** — anyone can rebalance; reverts if post-state isn't better. Emits `Rebalance`. |
| `0xd91ae7e3` | `chargeManagementFee(address token)` | Mints management-fee shares; emits `ManagementFeeCharged`. |

### 2.2 LeverageManager / FeeManager — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x9571d212` | `getLeverageTokenState(address token)` | `(collateralInDebtAsset, debt, equity, collateralRatio)` — `collateralRatio` 8-dec. |
| `0xba3b0f4d` | `getLeverageTokenConfig(address token)` | `LeverageTokenConfig`. |
| `0xa341017c` | `getLeverageTokenLendingAdapter(address token)` | `address` — the MorphoLendingAdapter (owns the Morpho position). |
| `0x9189aad4` | `getLeverageTokenRebalanceAdapter(address token)` | `address`. |
| `0xf3d4510b` | `getLeverageTokenCollateralAsset(address token)` | `address`. |
| `0xa792e3a8` | `getLeverageTokenDebtAsset(address token)` | `address`. |
| `0xa139a2c6` | `getLeverageTokenFactory()` | `address` — the BeaconProxyFactory. |
| `0xb8f82b26` / `0xd1f810a5` / `0xcbe52ae3` | `previewDeposit` / `previewMint` / `previewRedeem (address,uint256)` | `ActionData`. |
| `0x3e5541f1` / `0x50603df3` | `convertToShares` / `convertToAssets (address,uint256)` | `uint256`. |
| `0xfed6a1c7` | `getManagementFee(address token)` | `uint256`. |
| `0x3b19e84a` | `getTreasury()` | `address`. |

### 2.3 LeverageManager / RebalanceAdapter — UUPS upgrade surface

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4f1ef286` | `upgradeToAndCall(address newImpl, bytes data)` | `payable`. Emits `Upgraded`. |
| `0x52d1902d` | `proxiableUUID()` → `bytes32` | EIP-1822. Reverts through the proxy (UUPS `notDelegated`) — that revert is a positive UUPS signal. |

### 2.4 BeaconProxyFactory

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x227fce20` | `createProxy(bytes data, bytes32 baseSalt)` → `address` | Deploys a LeverageToken beacon proxy. Emits `BeaconProxyCreated`. |
| `0x6a0cdb08` | `computeProxyAddress(address sender, bytes data, bytes32 baseSalt)` → `address` | CREATE2 predictor. |
| `0x70bf7497` | `numProxies()` → `uint256` | Count of LeverageTokens created. |
| `0x5c60da1b` | `implementation()` → `address` | Beacon → current LeverageToken impl. |

### 2.5 MorphoLendingAdapterFactory / MorphoLendingAdapter

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0xc4ea1de7` | `deployAdapter(bytes32 morphoMarketId, address authorizedCreator, bytes32 baseSalt)` → `address` | Factory. Emits `MorphoLendingAdapterDeployed`. |
| `0x41b55583` | `computeAddress(address sender, bytes32 baseSalt)` → `address` | Factory (CREATE2 predictor). |
| `0x9b1f3527` | `lendingAdapterLogic()` → `address` | Factory — the clone implementation. |
| `0xe8efbffc` | `morphoMarketId()` → `bytes32` | Adapter — the Morpho market `Id` it manages. |
| `0xd8fbc833` | `morpho()` → `address` | Adapter — the Morpho singleton (`0xBBBB…`). |
| `0x7b9e68f2` | `marketParams()` → `(address,address,address,address,uint256)` | Adapter — Morpho MarketParams. |
| `0x87bfeb91` | `authorizedCreator()` → `address` | Adapter. |
| `0x5ccaf589` | `isUsed()` → `bool` | Adapter — true once bound to a LeverageToken. |

### 2.6 Periphery (LeverageRouter — flash-loan wrapped entry; Velora/Paraswap swap glue)

`LeverageRouter` wraps deposits/redeems with a Morpho flash loan + DEX swap via a `MulticallExecutor`. Its `deposit`/`redeem` take an `IMulticallExecutor.Call[]` swap-call array (selectors are deployment-specific; treat the router as a known address, not a selector to scan). Track router involvement by `tx.to == LeverageRouter`, and the actual position change by the LeverageManager `Mint`/`Redeem` event (where `sender` = the router).

---

## 3. Addresses — Base mainnet (chain ID 8453)

Source: `seamless-protocol/leverage-tokens` README + `script/8453/DeployConstants.sol` + `broadcast/Core.s.sol/8453`. All verified via `eth_getCode` on `https://base-rpc.publicnode.com` (2026-06-08). The current Core deployment landed at Base block **31051780** (Oct 2025).

| Role | Address | Proxy? / impl | One-liner |
|------|---------|---------------|-----------|
| **LeverageManager** (proxy) | `0x38Ba21C6Bf31dF1b1798FCEd07B4e9b07C5ec3a8` | ERC-1967 **UUPS**; impl `0xfE9101349354E278970489F935a54905DE2E1856` | Core singleton; emits §1.1/§1.2 events. |
| **BeaconProxyFactory** (LeverageToken factory + beacon) | `0xE0b2e40EDeb53B96C923381509a25a615c1Abe57` | not a 1967 proxy (impl slot `0x`); is the beacon | Deploys LeverageTokens; `implementation()` → LeverageToken impl. |
| LeverageToken implementation | `0x603Da735780e6bC7D04f3FB85C26dccCd4Ff0a82` | impl (beacon target) | Logic for every LeverageToken on Base. *(NB: this same address is the factory PROXY on Ethereum.)* |
| **MorphoLendingAdapterFactory** | `0xDd33419F0c01879a23051edbcdA997A0f9E68e61` | immutable | Deploys per-position MorphoLendingAdapter clones. |
| MorphoLendingAdapter implementation | `0x585cc1c8AF5C8aD79C64ac66D264590A3Ff65C51` | clone logic | |
| RebalanceAdapter implementation | `0xD923b2522E1f369e207d151cFE6A1BCd8EC24912` | impl | Dutch-auction / collateral-ratio rebalance logic. |
| **LeverageRouter** | `0xDbA92fC3dc10a17b96b6E807a908155C389A887C` | immutable | Flash-loan-wrapped deposit/redeem entrypoint. |
| PricingAdapter | `0xce05FbEd9260810Bdded179ADfdaf737BE7ded71` | immutable | Price helper. *(NB: same address = LendingAdapterFactory on Ethereum.)* |
| VeloraAdapter | `0x5C37EB148D4a261ACD101e2B997A0F163Fb3E351` | immutable | Paraswap/Velora swap glue. *(NB: same address = LeverageManager PROXY on Ethereum.)* |
| MulticallExecutor | `0x00c66934EBCa0F2A845812bC368B230F6da11A5C` | immutable | Executes router swap-call arrays. |
| Morpho Blue singleton (lending backend) | `0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb` | external (Morpho) | Where the actual leverage borrow/collateral lives. |
| Treasury / Timelock Short | `0x639d2dD24304aC2e6A691d8c1cFf4a2665925fee` | gov | Fee treasury + governance executor. |
| Guardian | `0xA1b5f2cc9B407177CD8a4ACF1699fa0b99955A22` | multisig | Emergency guardian. |

### 3.1 Base LeverageToken instances (discover live via `BeaconProxyCreated` / `numProxies()`)

| Symbol | LeverageToken (beacon proxy) | LendingAdapter | RebalanceAdapter |
|--------|------------------------------|----------------|------------------|
| **WEETH-WETH-17x** | `0xA2fceEAe99d2cAeEe978DA27bE2d95b0381dBB8c` | `0x9558b339bb03246c44C57fcEE184645DBfaB253f` | `0xA530e6eA09eb118a1549aCA73731379ba546DD32` |

> Only the weETH/WETH 17x LeverageToken was created on the current Base manager (created at block 31052857, the first `LeverageTokenCreated`+`BeaconProxyCreated` pair). Enumerate the full set with `BeaconProxyFactory.numProxies()` / the `BeaconProxyCreated` log — do not assume this is exhaustive over time. (Older pre-migration ILM "LoopStrategy" tokens used a different, now-retired contract set.)

---

## 4. Addresses — Ethereum mainnet (chain ID 1)

Source: `leverage-tokens` README + `script/1/DeployConstants.sol` + `broadcast/Core.s.sol/1`. Verified via `eth_getCode` on `https://ethereum-rpc.publicnode.com` (2026-06-08). Core deployment landed at ETH block **23471226**. **Mind the address-reuse trap (§ intro): roles differ from Base.**

| Role | Address | Proxy? / impl | One-liner |
|------|---------|---------------|-----------|
| **LeverageManager** (proxy) | `0x5C37EB148D4a261ACD101e2B997A0F163Fb3E351` | ERC-1967 **UUPS**; impl `0x9D04f65b58cED1fddef50AEc8b0b3d64fE64220E` | Core singleton (141-B proxy). |
| **LeverageToken factory** (BeaconProxyFactory) | `0x603Da735780e6bC7D04f3FB85C26dccCd4Ff0a82` | beacon factory | |
| LeverageToken implementation | `0xfE9101349354E278970489F935a54905DE2E1856` | impl | |
| **MorphoLendingAdapterFactory** | `0xce05FbEd9260810Bdded179ADfdaf737BE7ded71` | immutable | |
| MorphoLendingAdapter implementation | `0x00c66934EBCa0F2A845812bC368B230F6da11A5C` | clone logic | |
| DutchAuction+PreLiquidation+CollateralRatios RebalanceAdapter impl | `0x1d0c191a0fe2917e244826D3a8d0a64503efAec8` | impl | |
| **LeverageRouter** | `0xb0764dE7eeF0aC69855C431334B7BC51A96E6DbA` | immutable | |
| MulticallExecutor | `0x16D02Ebd89988cAd1Ce945807b963aB7A9Fd22E1` | immutable | |
| VeloraAdapter | `0xc4E5812976279cBcec943A6a148C95eAAC7Db6BA` | immutable | |
| PricingAdapter | `0x44CCEBEA0dAc17105e91a59E182f65f8D176c88f` | immutable | |
| LeverageTokenDeploymentBatcher | `0x4466D52b714Ef32657db89ec61FAB1b7E30A0352` | immutable | Batches LT + adapter creation. |
| Morpho Blue singleton (lending backend) | `0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb` | external (Morpho) | |
| Guardian | `0x90E8C75e2917E3C2F284F6922Df6c16F7C03123c` | multisig | |

### 4.1 Ethereum LeverageToken instances (sample; discover live)

LeverageTokens created on the ETH manager per the `CreateLeverageToken.*` broadcasts — e.g. **RLP-USDC-6.75x**, **wstETH-ETH-25x**, **siUSD-USDC-11x**, **sUSDS-USDT-25x**, **PT-RLP-4DEC2025-USDC-2x**. First `LeverageTokenCreated` confirmed at block 23471750 (token `0x10041DFf…`). Enumerate live via `BeaconProxyFactory.numProxies()` / `BeaconProxyCreated`.

---

## 5. Seamless Morpho Vaults (Base only) — MetaMorpho V1.1, immutable

The "Earn" side of Seamless 2.0 is three **standard MetaMorpho V1.1 curated vaults** (curator **Gauntlet** `0x9e33…0585`, `MORPHO()` = the Base Morpho Blue singleton). They are **immutable** (EIP-1967 impl slot `0x`), not part of the Leverage-Token contracts, and share the ERC-4626 + MetaMorpho ABI in [../morpho/v1.md](../morpho/v1.md). **Base only** (`0x` on all other chains). Being wound down (Gauntlet pulling funds → APY 0%).

| Vault | Address | asset / symbol |
|-------|---------|----------------|
| Seamless USDC Vault | `0x616a4E1db48e22028f6bbf20444Cd3b8e3273738` | USDC `0x8335…2913` / `smUSDC`, fee 15% |
| Seamless cbBTC Vault | `0x5a47C803488FE2BB0A0EAaf346b420e4dF22F3C7` | cbBTC / `smcbBTC` |
| Seamless WETH Vault | `0x27D8c7273fd3fcC6956a0B370cE5Fd4A7fc65c18` | WETH / `smWETH` |

ERC-4626 `Deposit`/`Withdraw` topics (`0xdcbc1c05…` / `0xfbde797d…`) and MetaMorpho admin events fire here — filter by the specific vault address (these topics are generic across all 4626/MetaMorpho vaults). Vault `Deposit` confirmed live (25 logs at ~b25.0M).

---

## 6. Cross-chain summary

| Chain | ID | LeverageManager | LeverageToken factory | Morpho Vaults |
|---|---|---|---|---|
| **Base** | 8453 | ✅ `0x38Ba…c3a8` (proxy) | ✅ `0xE0b2…be57` | ✅ smUSDC/smcbBTC/smWETH |
| **Ethereum** | 1 | ✅ `0x5C37…E351` (proxy) | ✅ `0x603D…0a82` | ❌ (Base-only) |
| BNB | 56 | ❌ | ❌ | ❌ |
| Avalanche | 43114 | ❌ | ❌ | ❌ |
| Arbitrum | 42161 | ❌ | ❌ | ❌ |
| Optimism | 10 | ❌ | ❌ | ❌ |
| Polygon PoS | 137 | ❌ | ❌ | ❌ |

**Vanity / address-reuse tell:** Base and Ethereum reuse the deployer's nonce-aligned addresses, so the SAME address denotes DIFFERENT contracts per chain (§ intro / §3 / §4). Always key on `(chainId, address)`.

---

## 7. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **LeverageManager** | ERC-1967 **UUPS** | EIP-1967 impl slot set, admin slot `0x`; impl exposes `upgradeToAndCall`/`proxiableUUID`; watch `Upgraded`. Base impl `0xfE9101…`, ETH impl `0x9D04f6…`. | Timelock Short / Guardian. |
| **BeaconProxyFactory** (LT factory) | UpgradeableBeacon (not a 1967 proxy itself) | impl slot `0x`; `implementation()` returns current LeverageToken impl; emits `Upgraded` (the beacon swap) → **upgrades every LeverageToken at once**. | Timelock Short / Guardian. |
| **LeverageToken** (each instance) | **Beacon proxy** | EIP-1967 **beacon** slot `0xa3f0…` = the factory address (`0xE0b2…`/`0x603D…`); impl slot `0x`. | follows the factory beacon. |
| **RebalanceAdapter** | UUPS (per LeverageToken) | impl slot set; `upgradeToAndCall`. | Timelock Short. |
| **MorphoLendingAdapter** | minimal clone (CREATE2) | deployed by `MorphoLendingAdapterFactory`; immutable; not upgradeable. | n/a |
| **LeverageRouter / MulticallExecutor / Pricing/Velora adapters** | immutable | full bytecode, impl slot `0x`. | n/a |
| **Seamless Morpho Vaults** | immutable (MetaMorpho V1.1) | impl slot `0x`. | n/a (curator/owner roles only). |

EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; beacon slot `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50`. Read live; never hard-code impls.

---

## 8. Detection invariants & gotchas

1. **Deployed on Base + Ethereum only.** `0x` on BNB/Avalanche/Arbitrum/Optimism/Polygon (verified 2026-06-08).
2. **Address-reuse across chains with different roles** — the headline trap. `0x5C37…E351` = LeverageManager proxy on ETH but VeloraAdapter on Base; `0x603D…0a82` = factory proxy on ETH but LeverageToken impl on Base; `0xfE9101…` = LeverageToken impl on ETH but LeverageManager impl on Base. Always key on `(chainId, address, role)`.
3. **`Mint`/`Redeem` are LeverageManager events, not ERC-20/4626.** Topic0s `0xca0d4a11…` / `0x079ed521…`; the LeverageToken position is indexed (topic1). The LeverageToken ERC-20 separately emits standard `Transfer`. Don't confuse the two.
4. **`sender` in `Mint`/`Redeem` is usually the LeverageRouter**, not the end user (flash-loan-wrapped deposits). Attribute the human via the tx originator if needed; attribute the position via the indexed LeverageToken.
5. **`rebalance` is permissionless** — anyone can call it (keepers/MEV bots), and it reverts unless post-state improves. `Rebalance` events come from third parties, not the position owner. The actual swaps go through external DEXs / the MulticallExecutor.
6. **Underlying lending lives on Morpho Blue, not here.** Each LeverageToken's `MorphoLendingAdapter` is the `onBehalf` of Morpho Blue `Borrow`/`SupplyCollateral` etc. To see real debt/collateral, follow `getLeverageTokenLendingAdapter(token)` → Morpho Blue events (`0xBBBB…`). The adapter itself only emits init/used events.
7. **LeverageTokens are beacon proxies; one beacon upgrade re-points all of them.** Watch `Upgraded` on the factory (`0xE0b2…` Base / `0x603D…` ETH), not on each token.
8. **Discover instances via factory events, not a static list.** `BeaconProxyCreated` (factory) / `LeverageTokenCreated` (manager) carry the new LeverageToken; `numProxies()` gives the count. The set grows/changes over time.
9. **Deprecated / winding down** (app offline 2026-06-30) — the product never found PMF; treat activity as redemptions/wind-down, not growth. Morpho Vaults being drained by Gauntlet; stkSEAM yield off.
10. **Seamless Morpho Vaults ≠ Leverage Tokens.** smUSDC/smcbBTC/smWETH are vanilla MetaMorpho V1.1 (Base-only, immutable) — decode them with the MetaMorpho ABI ([../morpho/v1.md](../morpho/v1.md)), and filter the generic 4626 topics by the specific vault address.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- LeverageManager (core)
TOPIC_LT_CREATED             = '\xc3f4681fb2a57a13e121c6f24fe319c8572bb001497f2b74712695625ee9028e'
TOPIC_LT_MINT                = '\xca0d4a1151cf4e7c20fcffb441cb3e88636d136769402e584ed509f78f896f61'
TOPIC_LT_REDEEM              = '\x079ed52167e1d2f9d4d371cd2dbc4fd7990aa0d8aa11416205a05bfe19343210'
TOPIC_LT_REBALANCE           = '\x1ece35fa7611d2dfc7e11d022888a20c4987d6ededbb34a26c93fd53f2073899'
TOPIC_LM_INITIALIZED         = '\xe05417bcb646fc5b895b56d08907b31d5565751b1f2e5a7ded0d071137fe309f'
-- FeeManager (same emitter as LeverageManager)
TOPIC_MGMT_FEE_CHARGED       = '\x46d6b0f5c0c8ece3cf8b44ea4a05280c3827c74ffa5a3b9e9aad6ecc48505e19'
TOPIC_MGMT_FEE_SET           = '\x054728667e9fde2ae95b0b309983329748caba1b3df19081435adb8966c61514'
TOPIC_LT_ACTION_FEE_SET      = '\x9dc95718df096d1d699a19543ccd8b579bc4729ce2021eb4764ff654ed67a5dc'
TOPIC_TREASURY_SET           = '\x3c864541ef71378c6229510ed90f376565ee42d9c5e0904a984a9e863e6db44f'
-- LeverageToken / BeaconProxyFactory
TOPIC_LT_INITIALIZED         = '\x57d9c3176493540cc7a0fba3538e0908b18dfe9468541ad54ba54fd474d33fec'
TOPIC_BEACON_PROXY_CREATED   = '\xfc6ca44b2e0253d7b333f816a6b6e52e7292a56fd5f38e52946f9dfc812d698b'
-- MorphoLendingAdapter (+ factory)
TOPIC_ADAPTER_INITIALIZED    = '\x4936702b8ba221fe23c531f1a2d5ba3022c8e5238de7a4428155d32b367c129c'
TOPIC_ADAPTER_USED           = '\xa6df6ca83fcea66b6eed2551b21e0a3f078e6af9eb9dbb02d2312e3d94b5d77b'
TOPIC_ADAPTER_DEPLOYED       = '\x90a228f4b5bc611babf005ecebd48836d9c73714549183b216fec07d3ee4348c'
-- Proxy
TOPIC_UPGRADED               = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- generic ERC-4626 (Seamless Morpho Vaults — filter by vault address)
TOPIC_4626_DEPOSIT           = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_4626_WITHDRAW          = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'

-- ===== Selectors (LeverageManager) =====
SEL_CREATE_NEW_LT            = '\x797f3af6'
SEL_LT_DEPOSIT               = '\x0efe6a8b'
SEL_LT_MINT                  = '\x156e29f6'
SEL_LT_REDEEM                = '\x2b83cccd'
SEL_LT_WITHDRAW              = '\xb5c5f672'
SEL_LT_REBALANCE             = '\x42cff3f8'
SEL_CHARGE_MGMT_FEE          = '\xd91ae7e3'
SEL_GET_LT_STATE             = '\x9571d212'
SEL_GET_LT_CONFIG            = '\xba3b0f4d'
SEL_GET_LT_LENDING_ADAPTER   = '\xa341017c'
SEL_GET_LT_FACTORY           = '\xa139a2c6'
-- factories / adapters
SEL_CREATE_PROXY             = '\x227fce20'
SEL_NUM_PROXIES              = '\x70bf7497'
SEL_BEACON_IMPLEMENTATION    = '\x5c60da1b'
SEL_DEPLOY_ADAPTER           = '\xc4ea1de7'
SEL_ADAPTER_MARKET_ID        = '\xe8efbffc'
SEL_ADAPTER_MARKET_PARAMS    = '\x7b9e68f2'
-- UUPS
SEL_UPGRADE_TO_AND_CALL      = '\x4f1ef286'
SEL_PROXIABLE_UUID           = '\x52d1902d'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_BEACON_SLOT          = '\xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50'

-- ===== Base (chain ID 8453) =====
BASE_LEVERAGE_MANAGER        = '\x38ba21c6bf31df1b1798fced07b4e9b07c5ec3a8'   -- impl 0xfe910134…
BASE_LT_FACTORY              = '\xe0b2e40edeb53b96c923381509a25a615c1abe57'   -- beacon
BASE_LT_IMPL                 = '\x603da735780e6bc7d04f3fb85c26dcccd4ff0a82'   -- NB: factory PROXY on ETH
BASE_LENDING_ADAPTER_FACTORY = '\xdd33419f0c01879a23051edbcda997a0f9e68e61'
BASE_LENDING_ADAPTER_IMPL    = '\x585cc1c8af5c8ad79c64ac66d264590a3ff65c51'
BASE_REBALANCE_ADAPTER_IMPL  = '\xd923b2522e1f369e207d151cfe6a1bcd8ec24912'
BASE_LEVERAGE_ROUTER         = '\xdba92fc3dc10a17b96b6e807a908155c389a887c'
BASE_MORPHO                  = '\xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
BASE_LT_WEETH_WETH_17X       = '\xa2fceeae99d2caeee978da27be2d95b0381dbb8c'
BASE_VAULT_smUSDC            = '\x616a4e1db48e22028f6bbf20444cd3b8e3273738'
BASE_VAULT_smcbBTC           = '\x5a47c803488fe2bb0a0eaaf346b420e4df22f3c7'
BASE_VAULT_smWETH            = '\x27d8c7273fd3fcc6956a0b370ce5fd4a7fc65c18'

-- ===== Ethereum (chain ID 1) — roles DIFFER from Base, mind the reuse =====
ETH_LEVERAGE_MANAGER         = '\x5c37eb148d4a261acd101e2b997a0f163fb3e351'   -- impl 0x9d04f65b…  (NB: VeloraAdapter on Base)
ETH_LT_FACTORY               = '\x603da735780e6bc7d04f3fb85c26dcccd4ff0a82'   -- (NB: LT impl on Base)
ETH_LT_IMPL                  = '\xfe9101349354e278970489f935a54905de2e1856'   -- (NB: LeverageManager impl on Base)
ETH_LENDING_ADAPTER_FACTORY  = '\xce05fbed9260810bdded179adfdaf737be7ded71'
ETH_LEVERAGE_ROUTER          = '\xb0764de7eef0ac69855c431334b7bc51a96e6dba'
ETH_MORPHO                   = '\xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb'
```

---

## 10. Verification & sources

How every constant was verified (2026-06-08):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from the `seamless-protocol/leverage-tokens` Solidity interfaces (`ILeverageManager`, `ILeverageToken`, `IFeeManager`, `IMorphoLendingAdapter(Factory)`, `IBeaconProxyFactory`) with struct params expanded to tuples (`ActionData`/`LeverageTokenConfig`/`LeverageTokenState`/`RebalanceAction`/Morpho `MarketParams`). **Live-validated:** `LeverageTokenCreated` + `BeaconProxyCreated` at Base block 31052857 (token `0xA2fceE…`) and ETH block 23471750 (token `0x10041DFf…`); `Mint` confirmed in a recent Base window. LeverageManager + adapter-factory selectors (`deposit`/`mint`/`redeem`/`withdraw`/`rebalance`/`createNewLeverageToken`/`deployAdapter`/`upgradeToAndCall`/`proxiableUUID`) confirmed **present** in the live Base impl bytecode (`0xfE9101…` 24,261 B; `0xDd3341…`).
- **Addresses:** taken from the repo README + `script/{1,8453}/DeployConstants.sol` + Foundry broadcasts (`Core.s.sol`, `DeployLeverageManagerImplementation`, `CreateLeverageToken.*`); existence-checked via `eth_getCode` on each chain. Base LeverageManager wiring read live (impl `0xfE9101…` via EIP-1967 slot; weETH/WETH-17x beacon slot = factory `0xE0b2…`).
- **Proxy classification:** EIP-1967 impl/beacon/admin slots read live — LeverageManager = UUPS (impl set, admin `0x`); BeaconProxyFactory = beacon (impl slot `0x`, `implementation()` callable); each LeverageToken = beacon proxy (beacon slot = factory); MorphoLendingAdapter/Router/adapters = immutable (impl slot `0x`); Seamless Morpho Vaults = immutable MetaMorpho V1.1 (impl slot `0x`, `MORPHO()` = `0xBBBB…`, curator = Gauntlet).
- **Chain absence:** `eth_getCode` = `0x` for the LeverageManager, factory, adapter factory and vaults on BNB, Avalanche, Arbitrum, Optimism, Polygon.

### Independent fact-check (2026-06-08)

- **"Leverage Tokens are Morpho-powered (Seamless 2.0), not a new Aave fork"** — *confirmed.* The only `LendingAdapter` is `MorphoLendingAdapter`; `morpho()` / vault `MORPHO()` = the canonical Base/ETH Morpho Blue singleton `0xBBBB…EEFFCb`.
- **"Deployed on Base AND Ethereum"** — *confirmed.* Both chains have a live UUPS LeverageManager proxy + factory; `LeverageTokenCreated` fired on each.
- **"Same addresses, different roles across chains"** — *confirmed* by reading EIP-1967 slots: `0x5C37…E351` is a 141-B UUPS proxy on ETH but a 2,730-B impl/adapter on Base, etc.
- **"Each LeverageToken is a beacon proxy whose beacon is the factory"** — *confirmed.* weETH/WETH-17x beacon slot = `0xE0b2…be57` (the factory).
- **"Product is deprecated / winding down (PMF failure)"** — *confirmed.* 2026-04-07 wind-down statement names Leverage Tokens' lack of product-market fit; app offline 2026-06-30; Morpho Vaults drained by curator Gauntlet; stkSEAM yield off.

Authoritative sources:
- GitHub: `seamless-protocol/leverage-tokens` (README, `src/`, `script/`, `broadcast/`)
- Morpho reference: [../morpho/v1.md](../morpho/v1.md) (Morpho Blue + MetaMorpho ABI), `docs.morpho.org`
- Official docs: `docs.seamlessprotocol.com`; Seamless 2.0 / wind-down announcements
- Explorers: BaseScan (`basescan.org`), Etherscan (`etherscan.io`)
