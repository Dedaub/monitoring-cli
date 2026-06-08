# LayerBank — Topics, Selectors, Addresses (NOT deployed on any of the 7 requested chains; primary deployments are Linea / Scroll / Mode / Manta etc.)

**Status:** verified against the canonical `layerbank/contracts` (V1) and `layerbank-foundation/v2-contracts` (V2) repos and live RPC on 2026-06-08. Every topic0/selector below was recomputed locally as `keccak256(signature)`; the off-target anchor addresses were `eth_getCode`-checked on Linea and Scroll mainnet; the requested-chain absences were `eth_getCode`-checked on all seven target RPCs.
**Scope:** the seven chains the user asked about — **LayerBank lending is deployed on NONE of them.** Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon PoS (137) have **no** LayerBank `Core`/`LToken`/`PriceCalculator` contracts. This is a recorded finding (§4), not an omission. LayerBank's real footprint is on **Linea, Scroll, Mode, Manta Pacific, Bitlayer, B² (BSquared), BOB, zkLink Nova, Taiko, Mint, Hemi, RSK** and similar L2/alt chains — all outside the requested set. The two largest primary deployments (Linea V1, Scroll) are documented in §5 as **off-target reference anchors** so the doc has real, on-chain-verified constants; they are explicitly outside the 7-chain monitoring scope. Topics/selectors are chain-agnostic and apply to every LayerBank chain; addresses are network-specific.

LayerBank is a **Compound-style money market with its own architecture** — `Core` (the risk engine / Comptroller-analogue) + per-asset `LToken` markets (`lETH`/`lUSDC`/`lWBTC`/`lUSDT`/…) + a single `RateModelSlope` interest-rate model + a `PriceCalculator` oracle + a `Validator` (liquidity/borrow-permission checker) + the `LAB`/`ULAB` governance token with `LABDistributor` (emissions) and `RebateDistributor` (reserve sink). It is **not a Compound `Comptroller`/`Unitroller` + `CErc20Delegator` fork** — there is no Unitroller delegator, no CErc20Delegator per-market proxy, and the events are LayerBank-specific. Two facts dominate monitoring:

1. **Supply/redeem are attributed on `Core`; borrow/repay/liquidate are attributed on the `LToken`.** The `Core` emits only `MarketSupply(user, lToken, uAmount)` and `MarketRedeem(user, lToken, uAmount)` (plus `MarketEntered`/`MarketExited`/`FlashLoan` and admin events). It does **not** emit Market-prefixed borrow/repay/liquidate events. Borrows surface as `LToken.Borrow(account, amount, accountBorrow)`, repays as `LToken.RepayBorrow(payer, borrower, amount, accountBorrow)`, and liquidations as `LToken.LiquidateBorrow(liquidator, borrower, amount, lTokenCollateral, seizeAmount)`. To index all five lending actions you must watch **both** the `Core` (supply/redeem) **and** every `LToken` (mint/borrow/repay/liquidate/redeem). `LToken.Mint(minter, mintAmount)` fires alongside the `Core.MarketSupply` (the lToken share-mint) and `LToken.Redeem(account, underlyingAmount, lTokenAmount)` alongside `Core.MarketRedeem`.
2. **The contracts are deployed as plain (immutable) logic — no EIP-1967 / minimal-proxy.** On Linea and Scroll the `Core` and every `LToken` have an **empty** EIP-1967 impl slot, empty admin slot, empty beacon slot, and their runtime begins with `0x6080604052…` (a normal contract, not a `0x363d3d37…` EIP-1167 clone). "Upgrades" happen by the `owner`/`keeper` re-pointing components (`setPriceCalculator`, `setValidator`, new `RateModelSlope`, `listMarket`/`removeMarket`) — there is no implementation address to track per market. V1 and V2 share byte-for-byte-identical event/function signatures (the V2 `ICore`/`LToken` interfaces are unchanged), so the constants below apply to both.

---

## 0. Contract families

| Family | Role | Emits / keyed events |
|--------|------|----------------------|
| **Core** (1 per chain) | Risk engine / Comptroller-analogue. Entry point for `supply`/`redeem`/`borrow`/`repay`/`liquidate`/`enterMarkets`. | `MarketSupply`, `MarketRedeem`, `MarketEntered`, `MarketExited`, `MarketListed`, `FlashLoan`, admin (`CollateralFactorUpdated`, `SupplyCapUpdated`, `BorrowCapUpdated`, `CloseFactorUpdated`, `LiquidationIncentiveUpdated`, `KeeperUpdated`, `ValidatorUpdated`, …) |
| **LToken** (1 per market) | Interest-bearing market token (Compound `cToken` analogue). 18 decimals; symbol = `l`+asset (`lETH`,`lUSDC`,…) — note some carry the bare asset name (`wstETH`). | `Mint`, `Redeem`, `Borrow`, `RepayBorrow`, `LiquidateBorrow`, `Transfer`, `Approval` |
| **RateModelSlope** (usually 1 shared per chain) | Utilization-kinked interest-rate model. No events. | — |
| **PriceCalculator** (1 per chain) | Oracle aggregator (Chainlink/eOracle/RedStone feeds + keeper-pushed prices). No standard events. | — |
| **Validator** (1 per chain) | Account-liquidity / borrow-permission checker (the policy half of the risk engine). | — |
| **LAB / ULAB token** (1 per chain) | Governance/emission token (per-chain symbol, e.g. `LAB.s` on Scroll). | ERC-20 `Transfer`/`Approval` |
| **LABDistributor** | LAB emission accounting for supply/borrow. | (distribution events; not core to lending detection) |
| **RebateDistributor** | Reserve-factor sink; calls `LToken.withdrawReserves()`. | — |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally with keccak on 2026-06-08 from `layerbank/contracts` (`interfaces/ICore.sol`, `markets/LToken.sol`); `MarketRedeem` / `Redeem` / `RepayBorrow` / `Mint` additionally confirmed against **live Linea & Scroll logs** (data-word layout matches the canonical signatures). The V2 repo declares identical events, so these topic0s are version-agnostic.

### 1.1 Core / CoreAdmin (the risk engine — one per chain)

| topic0 | Event |
|--------|-------|
| `0x2bbccc947c61d8ee81518a7f91c8e99f62691dbacce3401d6ab09fb692fbe173` | `MarketSupply(address user, address lToken, uint256 uAmount)` |
| `0xda2fcb771cce6a80cd6c0101db394f4fd1f8755def9185535cc97509f3e03cdd` | `MarketRedeem(address user, address lToken, uint256 uAmount)` ← **confirmed live (Linea Core, 3 data words)** |
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address lToken)` |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address lToken, address account)` |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address lToken, address account)` |
| `0x3659d15bd4bb92ab352a8d35bc3119ec6e7e0ab48e4d46201c8a28e02b6a8a86` | `FlashLoan(address indexed target, address indexed initiator, address indexed asset, uint256 amount, uint256 premium)` |
| `0xd88469f5aa8525dce9ae07fa2d8df83e2ec766fc060483b66a0082ff36d6582d` | `CloseFactorUpdated(uint256 newCloseFactor)` |
| `0x275d6207ccd4271a12c584febf2bcf32254205dfb4639ce1a9184d2e2609e2d0` | `CollateralFactorUpdated(address lToken, uint256 newCollateralFactor)` |
| `0x6791c9b68799eda502f8f7808e4ab556a632237eea58a66c4f7e4e6f94574d0d` | `LiquidationIncentiveUpdated(uint256 newLiquidationIncentive)` |
| `0x638a463c59949a284e093291dedfbadcb32ebf9007e649767344e67346ab8829` | `SupplyCapUpdated(address indexed lToken, uint256 newSupplyCap)` |
| `0x84d2db42497fc6f1882756be420935d982025ad8a2a903dfb83638a09e49a775` | `BorrowCapUpdated(address indexed lToken, uint256 newBorrowCap)` |
| `0x0425bcd291db1d48816f2a98edc7ecaf6dd5c64b973d9e4b3b6b750763dc6c2e` | `KeeperUpdated(address newKeeper)` |
| `0xb3a3a56265020415cf2f7ff198e2052a6e1d43d7eb127450af725829e40e08c2` | `ValidatorUpdated(address newValidator)` |
| `0x2351f252c60252e548e93df4d785886faa1d88410325b8bce69d624a25583ae7` | `LABDistributorUpdated(address newLABDistributor)` |
| `0x827daa11640de0eb908d0b06593ffb3f2b5e14e83d678fb922e512075f1d36f0` | `RebateDistributorUpdated(address newRebateDistributor)` |
| `0x21887d3c26545972adeaf9e44bd9aa5b527cd2b60b24cce6171828a07c564ea9` | `LeveragerUpdated(address newLeverager)` |

> `MarketEntered`/`MarketExited` topic0s **collide with Compound/Moonwell's** `MarketEntered(address,address)`/`MarketExited(address,address)` (same canonical sig) and `MarketListed` collides with Compound's `MarketListed(address)`. The **argument order differs** (LayerBank = `(lToken, account)`, Compound = `(mToken, account)` — same types, so same hash) — disambiguate by **emitter address** (the LayerBank `Core`, never a Compound Comptroller). `MarketSupply`/`MarketRedeem`/`FlashLoan`/the `*Updated` events are LayerBank-specific topic0s.

### 1.2 LToken (per-market — the workhorse borrow/repay/liquidate events)

| topic0 | Event |
|--------|-------|
| `0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885` | `Mint(address minter, uint256 mintAmount)` ← **confirmed live (Scroll lUSDC, 2 data words)** |
| `0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929` | `Redeem(address account, uint256 underlyingAmount, uint256 lTokenAmount)` ← **confirmed live (Linea lETH, 3 data words)** |
| `0xe1979fe4c35e0cef342fef5668e2c8e7a7e9f5d5d1ca8fee0ac6c427fa4153af` | `Borrow(address account, uint256 amount, uint256 accountBorrow)` |
| `0xa9a154237a69922f8860321d1fec1624a5dbe8a8af89a3dd3d7a759f6c8080d8` | `RepayBorrow(address payer, address borrower, uint256 amount, uint256 accountBorrow)` ← **confirmed live (Scroll lUSDC, 4 data words)** |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address liquidator, address borrower, uint256 amount, address lTokenCollateral, uint256 seizeAmount)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` — lToken shares (ERC-20) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` |

> **`LToken.Mint(address,uint256)` topic0 `0x0f6798a5…` is the same as Compound `cToken.Mint(address,uint256,uint256)`? — NO.** Compound's `Mint` is 3-arg (`0x4c209b5f…`); LayerBank's is **2-arg** (`mintAmount` only, the share count is not in the event), giving a distinct topic0. **`LiquidateBorrow` topic0 `0x298637f6…` IS identical to Compound/Moonwell** `LiquidateBorrow(address,address,uint256,address,uint256)` (same 5-arg sig) — disambiguate by emitter (a LayerBank `LToken`) and by the fact LayerBank liquidations are driven via `Core.liquidateBorrow`. **`Redeem` topic0 `0xe5b754fb…` ALSO collides with Compound/Moonwell** `Redeem(address,uint256,uint256)` — same disambiguation. The LayerBank `Borrow`/`RepayBorrow` topic0s differ from Compound's 4-/5-arg forms (LayerBank uses shorter 3-/4-arg variants).

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

Recomputed locally on 2026-06-08 from the V1/V2 sources. `redeemUnderlying`, `priceCalculator`, `validator`, `rebateDistributor`, `allMarkets`, `getRateModel` confirmed by live `eth_call` against the Linea/Scroll `Core`/`LToken`. Interface `uint` canonicalized to `uint256`.

### 2.1 Core — state-changing (the lending entry points)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc2998238` | `enterMarkets(address[] lTokens)` | Use markets as collateral. Emits `MarketEntered`. Same selector as Compound. |
| `0xede4edd0` | `exitMarket(address lToken)` | Emits `MarketExited`. Same selector as Compound. |
| `0xf2b9fdb8` | `supply(address lToken, uint256 uAmount)` | **payable.** Supply underlying (msg.value for native lETH). Emits `Core.MarketSupply` + `LToken.Mint`. |
| `0xbba61578` | `supplyBehalf(address account, address lToken, uint256 uAmount)` | payable. Supply on behalf of `account`. |
| `0x830cbbbd` | `redeemToken(address lToken, uint256 lAmount)` | Burn lTokens for underlying. Emits `MarketRedeem` + `LToken.Redeem`. |
| `0x96294178` | `redeemUnderlying(address lToken, uint256 uAmount)` | Redeem an exact underlying amount. **Confirmed: this selector is the tx `to`+data on a live Scroll redeem.** |
| `0x4b8a3529` | `borrow(address lToken, uint256 amount)` | Emits `LToken.Borrow`. |
| `0x33f9c876` | `borrowBehalf(address borrower, address lToken, uint256 amount)` | |
| `0xabdb5ea8` | `repayBorrow(address lToken, uint256 amount)` | payable. `type(uint).max` repays full. Emits `LToken.RepayBorrow`. |
| `0xe61604cf` | `liquidateBorrow(address lTokenBorrowed, address lTokenCollateral, address borrower, uint256 amount)` | payable. Emits `LToken.LiquidateBorrow`. |
| `0x7f0927f2` | `claimLab()` | Claim LAB emissions (all markets). |
| `0xeefc5947` | `claimLab(address market)` | Single market. |
| `0x34e115be` | `compoundLab(uint256 lockDuration)` | Claim + lock LAB into the Locker. |
| `0x68155ec1` | `transferTokens(address spender, address src, address dst, uint256 amount)` | lToken transfer routed through Core (collateral-aware). |

> Note: `core()` selector is `0xf2f4eb26`, but the LToken does **not** expose it (reverts) — the lToken→Core mapping was recovered by tracing a live redeem tx (`tx.to` = the Core), not by calling `core()`.

### 2.2 Core / CoreAdmin — admin & views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x375a7cba` | `allMarkets()` → `address[]` | **Enumerate lTokens here** — they are individually deployed, not derivable. |
| `0x5189e110` | `marketListOf(address account)` → `address[]` | Markets an account has entered. |
| `0x929fe9a1` | `checkMembership(address account, address lToken)` | Same selector as Compound. |
| `0xf8982e7a` | `accountLiquidityOf(address account)` | `(collateralInUSD, supplyInUSD, borrowInUSD)`. `borrow > collateral` ⇒ liquidatable. |
| `0x05308b9f` | `closeFactor()` | Linea = `0.9e18` (90%). |
| `0x8c765e94` | `liquidationIncentive()` | Linea = `1.4e18`. |
| `0x8b95e335` | `priceCalculator()` | → the oracle contract. |
| `0x3a5381b5` | `validator()` | → the Validator. |
| `0x59341a1a` | `rebateDistributor()` | |
| `0x8da5cb5b` | `owner()` | **Governance/multisig** (Linea Core+lETH owner = `0x76e1bafa…c449`). |
| `0xaced1661` | `keeper()` | Operational keeper (oracle pushes, market ops). |
| `0x12348e96` | `setCloseFactor(uint256)` | onlyKeeper. Emits `CloseFactorUpdated`. |
| `0xc04f31ff` | `setCollateralFactor(address lToken, uint256)` | Emits `CollateralFactorUpdated`. |
| `0xa8431081` | `setLiquidationIncentive(uint256)` | |
| `0xd136af44` | `setMarketSupplyCaps(address[], uint256[])` | Emits `SupplyCapUpdated`. |
| `0x186db48f` | `setMarketBorrowCaps(address[], uint256[])` | Emits `BorrowCapUpdated`. |
| `0xd9452b04` | `listMarket(address lToken, uint256 supplyCap, uint256 borrowCap, uint256 collateralFactor)` | Emits `MarketListed`. **The "add a market" event.** |
| `0xdb913236` | `removeMarket(address lToken)` | Delists a market. |
| `0x6922d7b6` | `setPriceCalculator(address)` | Oracle re-point (the closest thing to an "upgrade"). |
| `0x748747e6` | `setKeeper(address)` / `0x1327d3d8 setValidator(address)` / `0x66ae0209 setLABDistributor(address)` / `0xde02d642 setRebateDistributor(address)` / `0xf187186c setLeverager(address)` | Component re-points. Emit the matching `*Updated` events. |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | onlyKeeper. |

### 2.3 LToken (per-market)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd49187b3` | `getRateModel()` | → the `RateModelSlope`. **Confirmed live** (Linea all 4 markets share `0x2c4cbd05…`; Scroll lETH = `0x37097a6c…`). |
| `0xa1088459` | `rateModel()` | Alias getter (same value live). |
| `0x6f307dc3` | `underlying()` | Underlying ERC-20; returns **`0x0` for the native (lETH) market**. |
| `0x3ba0b9a9` | `exchangeRate()` | lToken↔underlying rate (1e18-scaled). |
| `0x8b9db037` | `accruedExchangeRate()` | State-mutating (accrues then returns). |
| `0xd88c3f22` | `getAccInterestIndex()` | Accumulated interest index. |
| `0x3b1d21a2` | `getCash()` | Underlying held by the market. |
| `0x8285ef40` | `totalBorrow()` / `0x4c68df67 totalReserve()` / `0x4322b714 reserveFactor()` | |
| `0x935a8b84` | `underlyingBalanceOf(address)` / `0x374c49b4 borrowBalanceOf(address)` | Per-user supply/debt in underlying. |
| `0x014a296f` | `accountSnapshot(address)` / `0x92fa4e8e accruedAccountSnapshot(address)` | Snapshot (view / accruing). |
| `0xb2a02ff1` | `seize(address liquidator, address borrower, uint256 lAmount)` | onlyCore — collateral seizure (same selector as Compound `seize`). |
| `0x26d5f641` | `withdrawReserves()` | onlyRebateDistributor — sweep reserves. |
| `0x70a08231` / `0x18160ddd` / `0x313ce567` / `0x95d89b41` / `0x06fdde03` | `balanceOf`/`totalSupply`/`decimals`/`symbol`/`name` | **lTokens are 18 decimals**; `symbol()` = `lETH`/`lUSDC`/… (some markets carry the bare asset name, e.g. `wstETH`). |

### 2.4 RateModelSlope

| Selector | Signature |
|----------|-----------|
| `0x15f24053` | `getBorrowRate(uint256 cash, uint256 borrows, uint256 reserves)` |
| `0xb8168816` | `getSupplyRate(uint256 cash, uint256 borrows, uint256 reserves, uint256 reserveFactor)` |
| `0x6e71e2d8` | `utilizationRate(uint256 cash, uint256 borrows, uint256 reserves)` |

### 2.5 PriceCalculator (oracle)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfc57d4df` | `getUnderlyingPrice(address lToken)` | Compound-compatible selector. |
| `0x48a1371b` | `getUnderlyingPrices(address[] lTokens)` | Batch. |
| `0xb95ed06f` | `priceOf(address asset)` | Price by underlying asset address. |
| `0xc910710c` | `valueOfUnderlying(address asset, uint256 amount)` | USD value of an amount. |
| `0x87ef019a` | `setTokenFeed(address asset, address feed)` | onlyKeeper — map asset→Chainlink/eOracle feed. |
| `0x782661bc` | `setPrices(address[] assets, uint256[] prices, uint256 timestamp)` | onlyKeeper — **keeper-pushed prices** (validated to within ~5 min of block time). |

---

## 3. Addresses — the 7 requested chains

There is **no LayerBank deployment on any of them** — see §4. (No per-chain address tables exist because there are no contracts to list.)

---

## 4. Chains with NO LayerBank deployment (all seven requested chains)

**Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137): LayerBank is NOT deployed.** Triangulated three ways:

1. **DeFiLlama** (`api.llama.fi/protocol/layerbank`) lists TVL only on Mint, Hemi, Nibiru, BOB, Linea, Scroll, Manta, Plume, Morph, BSquared, Bitlayer, Taiko, Mode, RSK, zkLink. A nominal `"Binance"` key appears with **zero TVL and no contract addresses** (a placeholder, not a live BSC lending market). None of Base / Avalanche / Arbitrum / Optimism / Polygon / Ethereum appears with lending TVL. The DeFiLlama address registry for the protocol lists only a **Linea** address.
2. **Official docs** (`docs.layerbank.finance`) enumerate L2/alt chains; none of the seven targets has a lending market (the V2 docs mention "Base" aspirationally but no live contracts exist — `eth_getCode` empty, no TVL).
3. **`eth_getCode` on all seven target RPCs** returned empty (`0x`) for every candidate LayerBank `Core`/`LAB` address (the Linea Core `0x009a…3833`, Scroll Core `0xEC53…89Aa`, Manta Core `0x72f7…3Ea6`, and Linea LAB `0xB97F…f75d`). LayerBank uses **different addresses per chain** (not CREATE2-shared), so a single address being empty is not sufficient — but **all** candidate addresses being empty on **all** seven chains, combined with (1) and (2), confirms absence.

Any contract claiming to be "LayerBank" on these seven chains is a different protocol or a fork. Do **not** author LayerBank monitors for Ethereum/Base/BSC/Avalanche/Arbitrum/Optimism/Polygon.

---

## 5. Primary deployment (off-target reference — outside the 7-chain monitoring scope)

These anchors are provided so the doc has real, on-chain-verified constants. **They are NOT on the requested chains** and exist only for cross-reference. All addresses below were `eth_getCode`-confirmed live on 2026-06-08 unless flagged docs-sourced.

### 5.1 Linea (chain ID 59144) — V1, the original/primary deployment

Source: Linea V1 docs + on-chain `Core.allMarkets()` enumeration. `Core` owner = `0x76e1bafa3c3271c7f3b1b247efbe9e52a9a8c449`. closeFactor `0.9e18`, liquidationIncentive `1.4e18`.

| Role | Address | Notes |
|------|---------|-------|
| **Core** | `0x009a0b7C38B542208936F1179151CD08E2943833` | Risk engine. `allMarkets()`=4. code 18.4 KB, no EIP-1967 slot. |
| **PriceCalculator** | `0x35a8c6050591c2f65b3e926b4b2ef825e3766bd6` | from `Core.priceCalculator()` (live). |
| **Validator** | `0xb5b25d9192f582568363243677dd25a939fe7112` | from `Core.validator()` (live). |
| **RebateDistributor** | `0x048a6ccb63f4dffac23b8dc724fc4e1a2268d20a` | from `Core.rebateDistributor()` (live). |
| **RateModelSlope** (shared by all 4 markets) | `0x2c4cbd05f01e4870197b4bd1fd70538efbf60999` | from each lToken's `getRateModel()` (live). |
| **LAB token** | `0xB97F21D1f2508fF5c73E7B5AF02847640B1ff75d` | governance/emission token (verified present). |
| LABDistributor | `0x5D06067f86946620C326713b846DdC8B97470957` | docs-sourced. |
| lETH (native ETH market) | `0xc7D8489DaE3D2EbEF075b1dB2257E2c231C9D231` | `underlying()`=`0x0`; symbol `lETH`; 18 dec. |
| lUSDC | `0x2aD69A0Cf272B9941c7dDcaDa7B0273E9046C4B0` | underlying `0x176211869cA2b568f2A7D4EE941E073a821EE1ff` (USDC). |
| lWBTC | `0xEa0F73296a6147FB56bAE29306Aae0FFAfF9De5F` | underlying `0x3aAB2285ddcDdaD8edf438C1bAB47e1a9D05a9b4` (WBTC). |
| wstETH market | `0xe33520c74bAc3c537BFEEe0F65e80471F3d564b9` | underlying `0xB5beDd42000b71FDdE22D3eE8a79Bd49A568fC8F` (wstETH); symbol `wstETH` (no `l` prefix). |

### 5.2 Scroll (chain ID 534352)

Source: on-chain. `Core` discovered by tracing a live redeem tx; `allMarkets()`=13. `Core` owner = `0xc69db8646ebb786631f4bc357977eae9f66c353c`.

| Role | Address | Notes |
|------|---------|-------|
| **Core** | `0xEC53c830f4444a8a56455C6836b5D2aa794289Aa` | code 18.9 KB, no EIP-1967 slot. |
| **PriceCalculator** | `0xe3168c8d1bcf6aaf5e090f61be619c060f3ad508` | from `Core.priceCalculator()` (live). |
| **Validator** | `0x746a0693ee5a1c4c7020775a4e715ff9982909a0` | from `Core.validator()` (live). |
| **RebateDistributor** | `0x50609fe6a078eb201077b9856392b158a15611de` | from `Core.rebateDistributor()` (live). |
| **LAB token** (`LAB.s`) | `0x2a00647F45047f05BDed961Eb8ECABc42780e604` | symbol `LAB.s` (verified). |
| lETH | `0x274C3795dadfEBf562932992bF241ae087e0a98C` | `underlying()`=`0x0`; symbol `lETH`. rateModel `0x37097a6c…`. |
| lUSDC | `0x0d8F8e271DD3f2fC58e5716d3Ff7041dBe3F0688` | underlying `0x06eFdBFf2a14a7c8E15944D1f4A48F9F95F663A4`. |
| lUSDT | `0xe0CeE49cc3c9d047C0b175943aB6FcC3C4F40FB0` | underlying `0xf55BEC9cafDbE8730f096Aa55dad6D22d44099Df`. |
| lWBTC | `0xc40D6957B8110EC55F0f1A20d7d3430E1d8aA4cf` | underlying `0x3C1BCa5a656e69edCD0D4E36BEbb3FcDAcA60Cf1`. |
| wstETH | `0xb6966083C7b68175b4Bf77511608Aee9A80d2cA4` | symbol `wstETH`. |
| lwrsETH / lpufETH / lSTONE / luniETH / lSolvBTCm / lSolvBTCb / lweETH / lUSDe | `0xec0ad3…`, `0x576d20…`, `0xe5c40a…`, `0xbd1d62…`, `0x0f67e8…`, `0xe4a759…`, `0x3335db…`, `0x0eb776…` | additional Scroll markets (full set via `allMarkets()`). |

### 5.3 Other primary chains (docs/explorer-sourced; not RPC-verified here — off the target RPC set)

| Chain | Core | Notes |
|-------|------|-------|
| Mode (34443) | `0x4Ac518DbF0CC730A1c880739CFa98fe0bB284959` | docs-sourced. lETH `0xb666582F612692525C4027d2a8280Ac06a055a95`, lUSDC `0xBa6e89c9cDa3d72B7D8D5B05547a29f9BdBDBaec`. |
| Manta Pacific (169) | `0x72f7a8eb9F83dE366AE166DC50F16074076C3Ea6` | docs-sourced. lETH `0x53bda0574BE207745f5Ce72706f4DDF59f0d6139`, lUSDC `0xBa6e89c9cDa3d72B7D8D5B05547a29f9BdBDBaec`, lBTC `0xAaC19657558DcF4b3724231aC790FD22A6Dd5BEd`. |

> LayerBank also runs on Bitlayer, B²/BSquared, BOB, zkLink Nova, Taiko, Mint, Hemi, Nibiru, Plume, Morph, RSK — all outside the requested set and not enumerated here.

---

## 6. Cross-chain summary

| Chain | ID | LayerBank lending? | Core |
|-------|----|--------------------|------|
| Ethereum | 1 | ❌ not deployed | — |
| Base | 8453 | ❌ not deployed | — |
| BNB Smart Chain | 56 | ❌ not deployed (DeFiLlama "Binance" = zero-TVL placeholder, no contracts) | — |
| Avalanche | 43114 | ❌ not deployed | — |
| Arbitrum One | 42161 | ❌ not deployed | — |
| Optimism | 10 | ❌ not deployed | — |
| Polygon PoS | 137 | ❌ not deployed | — |
| *Linea (off-target)* | 59144 | ✅ V1 (primary) | `0x009a0b7C…2943833` |
| *Scroll (off-target)* | 534352 | ✅ | `0xEC53c830…94289Aa` |
| *Mode / Manta / Bitlayer / B² / BOB / zkLink / Taiko / … (off-target)* | — | ✅ | per-chain |

Patterns to internalize:
1. **Nothing to monitor on the 7 target chains.** Any LayerBank work targets Linea/Scroll/Mode/Manta/etc.
2. **Addresses are per-chain unique** (not CREATE2-shared) — except a couple of incidental literal reuses (e.g. the same lUSDC address `0xBa6e89c9…` appears on both Mode and Manta). Always key on `(chainId, address)`.
3. **lTokens are individually deployed** — enumerate via `Core.allMarkets()`, never derive.

---

## 7. Proxies

LayerBank V1/V2 core contracts are deployed as **plain immutable logic** — **not** behind EIP-1967 / Transparent / UUPS / Beacon proxies and **not** EIP-1167 minimal-proxy clones.

| Contract | Pattern | Detection (verified on Linea + Scroll, 2026-06-08) | Upgrade authority |
|----------|---------|----------------------------------------------------|-------------------|
| Core | **Immutable logic** | EIP-1967 impl slot (`0x360894…382bbc`) = `0x` (empty); admin slot = `0x`; beacon slot = `0x`; runtime begins `0x6080604052…` (not `0x363d3d37…`). | none for code; **`owner()`/`keeper()` re-point components** (`setPriceCalculator`/`setValidator`/`listMarket`/`removeMarket`). |
| LToken (each) | **Immutable logic** | Same — all slots empty on Linea lETH/lUSDC and Scroll lETH. No `implementation()` getter (LToken is not a delegator). | `listMarket`/`removeMarket` on the Core add/remove markets; the LToken bytecode itself is fixed. |
| PriceCalculator | **Immutable logic** | EIP-1967 impl slot empty on Linea. | swapped wholesale via `Core.setPriceCalculator`. |
| Validator | **Immutable logic** | EIP-1967 impl slot empty on Linea. | swapped via `Core.setValidator`. |
| RateModelSlope | **Immutable logic** | new model deployed + attached per market. | per-market re-point. |

**There is no `Upgraded(address)` topic to monitor** (no upgradeable proxy). The functional equivalent of an upgrade is a **component re-point**: watch `Core` for `ValidatorUpdated`, `LABDistributorUpdated`, `RebateDistributorUpdated`, `LeveragerUpdated`, `KeeperUpdated`, `MarketListed`, plus `setPriceCalculator`/`setCollateralFactor`/`setMarketBorrowCaps`/`setMarketSupplyCaps` calls. (Note: some LayerBank chains may use an OZ `TransparentUpgradeableProxy` for newer V2 deployments — always read the EIP-1967 impl slot per chain before assuming immutability; on Linea + Scroll it is confirmed empty.)

---

## 8. Detection invariants & gotchas

1. **LayerBank is on none of the 7 requested chains** (§4). The whole detection set below applies only to off-target chains (Linea/Scroll/Mode/Manta/…).
2. **Supply/redeem are on the `Core`; borrow/repay/liquidate are on the `LToken`.** To capture all five lending primitives you must index **both** the single `Core` (`MarketSupply`/`MarketRedeem`) **and** every `LToken` (`Mint`/`Redeem`/`Borrow`/`RepayBorrow`/`LiquidateBorrow`). A supply produces **two** logs (`Core.MarketSupply` + `LToken.Mint`); a redeem produces `Core.MarketRedeem` + `LToken.Redeem` — dedupe by tx if you only want one row per action.
3. **It is NOT a Compound `Comptroller`/`Unitroller` fork.** No Unitroller delegator, no `CErc20Delegator`, no `comptrollerImplementation()`, no 3-arg `Mint`/4-arg `AccrueInterest`. Don't reuse the Compound/Moonwell detection set wholesale.
4. **Topic0 collisions with Compound/Moonwell:** `LiquidateBorrow` (`0x298637f6…`), `Redeem` (`0xe5b754fb…`), `MarketEntered`/`MarketExited`/`MarketListed` are byte-identical to Compound's. **Disambiguate by emitter** — a LayerBank `Core`/`LToken`, never a Compound Comptroller/cToken. LayerBank's `Borrow`/`RepayBorrow`/`Mint` topic0s differ from Compound's (shorter arg lists).
5. **`Mint` carries only `mintAmount` (underlying), not the share count.** To get lTokens minted, read `Transfer`/`exchangeRate()` — the `Mint` event alone is incomplete. (`Borrow` carries `accountBorrow` = the borrower's post-action total debt, not the delta beyond `amount`.)
6. **Native-asset market (`lETH`) has `underlying() == 0x0`** and supply/repay are `payable` (msg.value). Don't expect an ERC-20 underlying for it.
7. **`*Behalf` functions break naive sender attribution.** `supplyBehalf`/`borrowBehalf` credit/debit a different account than `msg.sender`. Attribute to the **event's `user`/`account`/`borrower` field**, not `tx.from`. Liquidations attribute the seized collateral to `borrower` and the repaid debt to `liquidator` from the `LiquidateBorrow` event.
8. **Liquidations route through `Core.liquidateBorrow` (selector `0xe61604cf`), then the `LToken` emits `LiquidateBorrow`** and calls `seize` (`0xb2a02ff1`) on the collateral lToken. Detect by the **`LiquidateBorrow` event topic0** (on the borrowed-asset lToken), and read `lTokenCollateral`/`seizeAmount` from the event.
9. **Oracle is keeper-pushed for some assets.** `PriceCalculator.setPrices(address[],uint256[],uint256)` (`0x782661bc`) lets the keeper push prices (validated ≤ ~5 min stale). A misbehaving/compromised keeper is an oracle risk vector — monitor `setPrices`/`setTokenFeed`/`setKeeper` calls and the `KeeperUpdated` event.
10. **Immutable contracts, component re-points instead of upgrades** (§7). The "admin action" surface is `Core` `*Updated` events + `MarketListed`/`removeMarket` + cap/collateral-factor setters — watch these, there is **no `Upgraded(address)`**.
11. **LAB token symbol is per-chain** (`LAB` on Linea, `LAB.s` on Scroll, `ULAB` is the V2 omni-token brand). Don't assume a single canonical LAB address across chains.
12. **Markets are added/removed over time** — re-read `Core.allMarkets()` rather than hardcoding the lToken set (Linea=4, Scroll=13 as of 2026-06-08).
13. **`Borrow`/`LiquidateBorrow` may be rare in a short live window** (LayerBank activity is concentrated on a few chains and several markets are quiet/winding-down). The topic0s here are recomputed from canonical source and the related events (`MarketSupply`/`MarketRedeem`/`Redeem`/`RepayBorrow`/`Mint`) were confirmed live — treat the two unsampled ones as source-verified.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) — Core =====
TOPIC_MARKET_SUPPLY            = '\x2bbccc947c61d8ee81518a7f91c8e99f62691dbacce3401d6ab09fb692fbe173'
TOPIC_MARKET_REDEEM            = '\xda2fcb771cce6a80cd6c0101db394f4fd1f8755def9185535cc97509f3e03cdd'
TOPIC_MARKET_LISTED            = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_MARKET_ENTERED           = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'
TOPIC_MARKET_EXITED            = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_FLASHLOAN                = '\x3659d15bd4bb92ab352a8d35bc3119ec6e7e0ab48e4d46201c8a28e02b6a8a86'
TOPIC_CLOSE_FACTOR_UPDATED     = '\xd88469f5aa8525dce9ae07fa2d8df83e2ec766fc060483b66a0082ff36d6582d'
TOPIC_COLLATERAL_FACTOR_UPD    = '\x275d6207ccd4271a12c584febf2bcf32254205dfb4639ce1a9184d2e2609e2d0'
TOPIC_LIQ_INCENTIVE_UPDATED    = '\x6791c9b68799eda502f8f7808e4ab556a632237eea58a66c4f7e4e6f94574d0d'
TOPIC_SUPPLY_CAP_UPDATED       = '\x638a463c59949a284e093291dedfbadcb32ebf9007e649767344e67346ab8829'
TOPIC_BORROW_CAP_UPDATED       = '\x84d2db42497fc6f1882756be420935d982025ad8a2a903dfb83638a09e49a775'
TOPIC_KEEPER_UPDATED           = '\x0425bcd291db1d48816f2a98edc7ecaf6dd5c64b973d9e4b3b6b750763dc6c2e'
TOPIC_VALIDATOR_UPDATED        = '\xb3a3a56265020415cf2f7ff198e2052a6e1d43d7eb127450af725829e40e08c2'
TOPIC_LABDISTRIBUTOR_UPDATED   = '\x2351f252c60252e548e93df4d785886faa1d88410325b8bce69d624a25583ae7'
TOPIC_REBATEDISTRIB_UPDATED    = '\x827daa11640de0eb908d0b06593ffb3f2b5e14e83d678fb922e512075f1d36f0'
TOPIC_LEVERAGER_UPDATED        = '\x21887d3c26545972adeaf9e44bd9aa5b527cd2b60b24cce6171828a07c564ea9'
-- ===== Topics (chain-agnostic) — LToken =====
TOPIC_LT_MINT                  = '\x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'
TOPIC_LT_REDEEM                = '\xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929'
TOPIC_LT_BORROW                = '\xe1979fe4c35e0cef342fef5668e2c8e7a7e9f5d5d1ca8fee0ac6c427fa4153af'
TOPIC_LT_REPAY_BORROW          = '\xa9a154237a69922f8860321d1fec1624a5dbe8a8af89a3dd3d7a759f6c8080d8'
TOPIC_LT_LIQUIDATE_BORROW      = '\x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
TOPIC_TRANSFER                 = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_APPROVAL                 = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
-- ===== Selectors (chain-agnostic) — Core =====
SEL_SUPPLY                     = '\xf2b9fdb8'
SEL_SUPPLY_BEHALF              = '\xbba61578'
SEL_REDEEM_TOKEN               = '\x830cbbbd'
SEL_REDEEM_UNDERLYING          = '\x96294178'
SEL_BORROW                     = '\x4b8a3529'
SEL_BORROW_BEHALF              = '\x33f9c876'
SEL_REPAY_BORROW               = '\xabdb5ea8'
SEL_LIQUIDATE_BORROW           = '\xe61604cf'
SEL_ENTER_MARKETS              = '\xc2998238'
SEL_EXIT_MARKET                = '\xede4edd0'
SEL_LIST_MARKET                = '\xd9452b04'
SEL_REMOVE_MARKET              = '\xdb913236'
SEL_SET_PRICE_CALCULATOR       = '\x6922d7b6'
SEL_SET_VALIDATOR              = '\x1327d3d8'
SEL_SET_COLLATERAL_FACTOR      = '\xc04f31ff'
SEL_SET_CLOSE_FACTOR           = '\x12348e96'
SEL_SET_SUPPLY_CAPS            = '\xd136af44'
SEL_SET_BORROW_CAPS            = '\x186db48f'
SEL_PAUSE                      = '\x8456cb59'
SEL_UNPAUSE                    = '\x3f4ba83a'
SEL_ALL_MARKETS                = '\x375a7cba'
SEL_ACCOUNT_LIQUIDITY_OF       = '\xf8982e7a'
-- ===== Selectors (chain-agnostic) — LToken / oracle =====
SEL_LT_GET_RATE_MODEL          = '\xd49187b3'
SEL_LT_UNDERLYING              = '\x6f307dc3'
SEL_LT_EXCHANGE_RATE           = '\x3ba0b9a9'
SEL_LT_SEIZE                   = '\xb2a02ff1'
SEL_PC_GET_UNDERLYING_PRICE    = '\xfc57d4df'
SEL_PC_SET_PRICES              = '\x782661bc'
SEL_PC_SET_TOKEN_FEED          = '\x87ef019a'
-- ===== Addresses — OFF-TARGET ANCHORS ONLY (NOT on any of the 7 requested chains) =====
LINEA_CORE                     = '\x009a0b7c38b542208936f1179151cd08e2943833'
LINEA_PRICE_CALCULATOR         = '\x35a8c6050591c2f65b3e926b4b2ef825e3766bd6'
LINEA_VALIDATOR                = '\xb5b25d9192f582568363243677dd25a939fe7112'
LINEA_RATE_MODEL               = '\x2c4cbd05f01e4870197b4bd1fd70538efbf60999'
LINEA_LAB                      = '\xb97f21d1f2508ff5c73e7b5af02847640b1ff75d'
LINEA_LETH                     = '\xc7d8489dae3d2ebef075b1db2257e2c231c9d231'
LINEA_LUSDC                    = '\x2ad69a0cf272b9941c7ddcada7b0273e9046c4b0'
LINEA_LWBTC                    = '\xea0f73296a6147fb56bae29306aae0ffaff9de5f'
LINEA_WSTETH_MKT               = '\xe33520c74bac3c537bfeee0f65e80471f3d564b9'
SCROLL_CORE                    = '\xec53c830f4444a8a56455c6836b5d2aa794289aa'
SCROLL_PRICE_CALCULATOR        = '\xe3168c8d1bcf6aaf5e090f61be619c060f3ad508'
SCROLL_VALIDATOR               = '\x746a0693ee5a1c4c7020775a4e715ff9982909a0'
SCROLL_LAB                     = '\x2a00647f45047f05bded961eb8ecabc42780e604'
SCROLL_LETH                    = '\x274c3795dadfebf562932992bf241ae087e0a98c'
SCROLL_LUSDC                   = '\x0d8f8e271dd3f2fc58e5716d3ff7041dbe3f0688'
SCROLL_LUSDT                   = '\xe0cee49cc3c9d047c0b175943ab6fcc3c4f40fb0'
SCROLL_LWBTC                   = '\xc40d6957b8110ec55f0f1a20d7d3430e1d8aa4cf'
```

---

## 10. Verification & sources

- **Canonical source:** `github.com/layerbank/contracts` (V1: `Core.sol`, `CoreAdmin.sol`, `interfaces/ICore.sol`, `markets/LToken.sol`, `markets/interest/RateModelSlope.sol`, `calculator/PriceCalculator.sol`) and `github.com/layerbank-foundation/v2-contracts` (V2: same file layout; `ICore`/`LToken` event+function declarations are byte-for-byte identical to V1 → topic0s/selectors are version-agnostic). Official docs: `docs.layerbank.finance`; Linea V1 docs: `docs.linea.layerbank.finance`.
- **Topic0s / selectors:** every value recomputed locally as `keccak256(canonical signature)` (param names stripped, `uint`→`uint256`). Cross-checked against live logs:
  - `Core.MarketRedeem` `0xda2fcb77…` — **18 logs** in a recent 50k-block window on the live Linea `Core` (`0x009a…3833`), each 3 data words = `(user, lToken, uAmount)`; `word[1]` = Linea lUSDC, confirming arg order.
  - `Core.MarketSupply` `0x2bbccc94…` — **observed live** on the Linea `Core`, 3 data words = `(user, lToken, uAmount)` (rare in recent windows; found on a wider back-scan, confirming arg layout).
  - `LToken.Redeem` `0xe5b754fb…` — found on live Linea `lETH`, 3 data words = `(account, underlyingAmount, lTokenAmount)`.
  - `LToken.RepayBorrow` `0xa9a15423…` — found on live Scroll `lUSDC`, **4 data words** = `(payer, borrower, amount, accountBorrow)`.
  - `LToken.Mint` `0x0f6798a5…` — found on live Scroll `lUSDC`, **2 data words** = `(minter, mintAmount)` (distinct from Compound's 3-arg `Mint`).
  - `Borrow` / `LiquidateBorrow` topic0s recomputed from source but **not observed** in the sampled live windows (low recent activity / wind-down on the sampled markets) — source-verified only.
- **Addresses & wiring (off-target anchors):** Linea `Core.allMarkets()` (4 markets) + `priceCalculator()`/`validator()`/`rebateDistributor()`/`closeFactor()`/`liquidationIncentive()` read live; each lToken's `getRateModel()`/`underlying()`/`symbol()` read live. Scroll `Core` discovered by tracing a live `redeemUnderlying` tx (`to` = `0xEC53…89Aa`, selector `0x96294178`), then `allMarkets()` (13 markets) + wiring read live. `eth_getCode` confirmed code present (no EIP-1967 impl/admin/beacon slot; runtime prefix `0x6080604052…`, not `0x363d3d37…`).
- **Absence on the 7 requested chains:** `eth_getCode` empty (`0x`) for the Linea/Scroll/Manta `Core` and Linea `LAB` addresses on all of `ethereum-rpc`, `base-rpc`, `bsc-rpc`, `avalanche-c-chain-rpc`, `arbitrum-one-rpc`, `optimism-rpc`, `polygon-bor-rpc.publicnode.com`. Corroborated by DeFiLlama (`api.llama.fi/protocol/layerbank`) showing no lending TVL on any of the seven (the `"Binance"` chain key carries zero TVL and no contract addresses) and by the official docs listing only L2/alt chains.
- **Proxy classification:** EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`, admin slot `0xb53127…5d6103`, beacon slot `0xa3f0ad74…133d50`, and OZ legacy slot all read **empty** on Linea `Core`/`lETH`/`lUSDC`/`PriceCalculator`/`Validator` and Scroll `lETH` → immutable logic, not proxied.
- **Explorers:** LineaScan (`lineascan.build`), Scrollscan (`scrollscan.com`) for cross-reference of the lToken symbols/underlyings.
