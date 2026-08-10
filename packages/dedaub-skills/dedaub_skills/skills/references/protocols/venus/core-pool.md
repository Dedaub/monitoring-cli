# Venus Core Pool — Topics, Selectors, Addresses (BNB Smart Chain only)

**Status:** verified against live RPC + canonical `VenusProtocol/venus-protocol` repo on 2026-06-08. Every topic0/selector recomputed locally as `keccak256(canonical signature)`; every address existence-checked via `eth_getCode`; every proxy/diamond/delegator slot read live from storage and getters.

**Scope:** the original Venus lending pool — the Compound V2 fork (`VenusProtocol/venus-protocol`): **Unitroller + Comptroller (a DIAMOND behind the Unitroller)**, the per-market **VBep20Delegator** proxies and shared **VBep20Delegate** logic, the native **vBNB** market, **JumpRateModel / WhitePaperInterestRateModel**, **ComptrollerLens**, **VenusLens / SnapshotLens**, and the Core-Pool **Liquidator**. Topics and selectors are chain-agnostic (`keccak256` of the signature); addresses are network-specific. **THE ONE FACT THAT OVERRIDES EVERYTHING: the Venus Core-Pool legacy codebase is deployed on BNB Smart Chain (56) ONLY.** On Ethereum, Base, Avalanche, Arbitrum, Optimism and Polygon there is NO Core Pool — the pool labelled "Core Pool" in the Venus UI on those chains is an **isolated-pools** deployment (different contracts, different events; covered in `isolated-pools.md`). The Unitroller address returns empty `eth_getCode` (`0x`) on all six non-BSC chains.

Venus Core is a faithful Compound V2 fork with renamed types: `cToken` → **vToken**, `CErc20Delegator` → **VBep20Delegator** (per-market proxy), `CErc20Delegate` → **VBep20Delegate** (shared logic), `CEther` → **VBNB** (monolithic native-gas market, NOT a delegator), `Comptroller` behind a **Unitroller**. Four deviations matter for a monitor:

1. **Per-block accrual (NOT timestamp).** Venus Core accrues interest on `block.number`. The accessors are `supplyRatePerBlock()` / `borrowRatePerBlock()` (per-block mantissas) and `accrualBlockNumber()` (a block number). This is the *opposite* of the Moonwell fork — do not look for `*PerTimestamp` / `accrualBlockTimestamp` here. Verified live: BSC vUSDT `supplyRatePerBlock()` returns a value.
2. **`AccrueInterest` is the 4-arg form** `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` (topic0 `0x4dec04e7…`). Verified live: BSC vUSDT logs carry **128 bytes** data (= 4×uint256) over 369 recent events.
3. **The Comptroller is a DIAMOND behind the Unitroller, not a single logic contract.** The Unitroller (Compound's slot-2 proxy) points its `comptrollerImplementation` at a **Diamond** contract, which routes per-selector to **five facets**: `MarketFacet`, `PolicyFacet`, `RewardFacet`, `SetterFacet`, `FlashLoanFacet`. `facetAddresses()` returns these 5 live. Facet edits emit a Venus-specific **single-arg** `DiamondCut(IDiamondCut.FacetCut[])` (topic0 `0x2e97860c…`) — NOT the EIP-2535 standard 3-arg `DiamondCut(FacetCut[],address,bytes)`.
4. **Rewards (XVS) are emitted by the Comptroller itself** (via the `RewardFacet`/`XVSRewardsHelper`) as `DistributedSupplierVenus` / `DistributedBorrowerVenus` (both **4-arg**) — there is no separate reward-distributor proxy in the Core Pool. (Isolated pools use a separate `RewardsDistributor`; Core does not.)

The Unitroller `admin` (storage slot 0) is the Venus governance **NormalTimelock** (`0x939bd8d6…`). The Core Pool also hooks a **VAIController** (the VAI stablecoin minting controller, reached via its own `VaiUnitroller`); it is referenced here only by name and selector — VAI itself lives in `periphery.md`.

---

## 0. Contract families & versions

| Family | Contract(s) | Proxy pattern | Notes |
|--------|-------------|---------------|-------|
| Risk engine | **Unitroller** (proxy) → **Diamond** (impl) → 5 facets | Compound Unitroller (slot 2) + EIP-2535-style Diamond | The single risk engine. Point market-policy monitors at the Unitroller. |
| Comptroller facets | MarketFacet, PolicyFacet, RewardFacet, SetterFacet, FlashLoanFacet | plain logic contracts (delegatecall targets) | All five live in `facetAddresses()`. |
| Markets (ERC-20) | **VBep20Delegator** (per market) + **VBep20Delegate** (shared logic) | Compound delegator (`implementation()` getter) | ~47 ERC-20 markets. Enumerate via `getAllMarkets()`. |
| Native market | **vBNB** | **none — monolithic, immutable** | No `implementation()`, no `underlying()`; mint/repay are payable no-arg. |
| Interest rate | **JumpRateModel** / **WhitePaperInterestRateModel** (+ CheckpointView wrappers) | immutable | One per parameter set; read per-market via `interestRateModel()`. |
| Lenses | **ComptrollerLens**, **VenusLens**, **SnapshotLens** | immutable | Off-chain read helpers; ComptrollerLens does liquidity/seize math for the Comptroller. |
| Liquidation | **Liquidator** (proxy) | EIP-1967 transparent | Optional protocol-routed liquidation path with treasury cut. |
| Oracle | live `oracle()` = **ResilientOracle** (proxy) → wraps legacy **VenusChainlinkOracle** | EIP-1967 transparent (ResilientOracle); plain feeder (VenusChainlinkOracle) | Comptroller's `oracle()` returns the ResilientOracle, not the legacy ChainlinkOracle. |
| VAI hook | **VAIController** via **VaiUnitroller** | Compound Unitroller | Referenced by name/selector only; full coverage in `periphery.md`. |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 vToken / VBep20 / vBNB (per-market workhorse events)

| topic0 | Event |
|--------|-------|
| `0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04` | `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` |
| `0xb4c03061fb5b7fed76389d5af8f2e0ddb09f8c70d1333abbb62582835e10accb` | `Mint(address minter, uint256 mintAmount, uint256 mintTokens, uint256 totalSupply)` — **LIVE 4-arg form** (the deployed VBep20Delegate adds a trailing `totalSupply`). Data = 128 B. The stock-Compound 3-arg `Mint(address,uint256,uint256)` (`0x4c209b5f…`) is the **pre-upgrade legacy form** — it no longer fires (0 occurrences in the recent ~1M blocks); keep it only for historical back-fill. |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address minter, uint256 mintAmount, uint256 mintTokens)` — **legacy 3-arg, pre-upgrade only.** Collides with PancakeSwap/Uniswap V2 `Mint` (see note below). |
| `0xa24ddbdf0865ba440d364725c062eac72a908faeedffc33fe64d4640c82e3ab8` | `MintBehalf(address payer, address receiver, uint256 mintAmount, uint256 mintTokens, uint256 totalSupply)` — **LIVE 5-arg form.** Data = 160 B. Old 4-arg `MintBehalf(address,address,uint256,uint256)` (`0x297989b8…`) is pre-upgrade legacy. |
| `0xbd5034ffbd47e4e72a94baa2cdb74c6fad73cb3bcdc13036b72ec8306f5a7646` | `Redeem(address redeemer, uint256 redeemAmount, uint256 redeemTokens, uint256 totalSupply)` — **LIVE 4-arg form.** Data = 128 B. Old 3-arg `Redeem(address,uint256,uint256)` (`0xe5b754fb…`) is pre-upgrade legacy (0 occurrences recently). |
| `0xccf8e53b86a99b7e9ecf796342c165764d66154780f638c08e6241d711fba6d4` | `RedeemFee(address redeemer, uint256 feeAmount, uint256 redeemTokens)` — redeem-fee event on the upgraded VBep20Delegate. |
| `0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80` | `Borrow(address borrower, uint256 borrowAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1` | `RepayBorrow(address payer, address borrower, uint256 repayAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address liquidator, address borrower, uint256 repayAmount, address vTokenCollateral, uint256 seizeTokens)` |
| `0xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5` | `ReservesAdded(address benefactor, uint256 addAmount, uint256 newTotalReserves)` |
| `0x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e` | `ReservesReduced(address admin, uint256 reduceAmount, uint256 newTotalReserves)` |
| `0xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460` | `NewReserveFactor(uint256 oldReserveFactorMantissa, uint256 newReserveFactorMantissa)` |
| `0xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926` | `NewMarketInterestRateModel(address oldIRM, address newIRM)` |
| `0x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d` | `NewComptroller(address oldComptroller, address newComptroller)` |
| `0xf5815f353a60e815cce7553e4f60c533a59d26b1b5504ea4b6db8d60da3e4da2` | `NewProtocolSeizeShare(uint256 oldShare, uint256 newShare)` (newer vToken impls) |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` — VBep20Delegator logic swap |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` — vToken shares |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` — soft-fail (pre-revert legacy path) |

> **The live vToken `Mint` is the 4-arg form `0xb4c03061…`** (added `totalSupply`); the legacy 3-arg `Mint` (`0x4c209b5f…`) no longer fires and is kept only for historical back-fill. The legacy 3-arg topic **collides with Uniswap V2 / PancakeSwap V2 `Mint`** (same `Mint(address,uint256,uint256)`) — on BSC PancakeSwap is the dominant emitter, so if you back-fill the legacy topic you **must filter by emitter (a vToken)**. The new 4-arg `Mint` topic does NOT collide with PancakeSwap. ERC-20 `Transfer`/`Approval` still collide (every token) — always filter those by emitter too.

### 1.2 Comptroller (the Diamond, behind the Unitroller — one per chain)

All emitted by the **Unitroller address** (delegatecall preserves `emit` context).

| topic0 | Event |
|--------|-------|
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address vToken)` |
| `0x302feb03efd5741df80efe7f97f5d93d74d46a542a3d312d0faae64fa1f3e0e9` | `MarketUnlisted(address vToken)` |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address vToken, address account)` |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address vToken, address account)` |
| `0x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9` | `NewCloseFactor(uint256 oldCloseFactorMantissa, uint256 newCloseFactorMantissa)` |
| `0x0d1a615379dc62cec7bc63b7e313a07ed659918f4ad3720b3af8041b305146f2` | `NewCollateralFactor(uint96 indexed poolId, address indexed vToken, uint256 oldCFMantissa, uint256 newCFMantissa)` — **live 4-arg, pool-aware form.** The deployed SetterFacet was upgraded to the multi-pool architecture: Core Pool = `poolId 0`. The stock-Compound 3-arg `NewCollateralFactor(address,uint256,uint256)` (`0x70483e65…`) is **no longer emitted** — its topic/selector are absent from the live SetterFacet bytecode. |
| `0xc1d7bc090f3a87255c2f4e56f66d1b7a49683d279f77921b1701aa5d733ef745` | `NewLiquidationIncentive(uint96 indexed poolId, address indexed vToken, uint256 oldIncentiveMantissa, uint256 newIncentiveMantissa)` — **live 4-arg, pool-aware form** (per-market, not global). The old 2-arg `NewLiquidationIncentive(uint256,uint256)` (`0xaeba5a6c…`, the Moonwell/stock form) is **no longer emitted** by Venus Core. |
| `0xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22` | `NewPriceOracle(address oldOracle, address newOracle)` |
| `0x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6` | `NewBorrowCap(address indexed vToken, uint256 newBorrowCap)` |
| `0xeda98690e518e9a05f8ec6837663e188211b2da8f4906648b323f2c1d4434e29` | `NewBorrowCapGuardian(address oldBorrowCapGuardian, address newBorrowCapGuardian)` |
| `0x9e0ad9cee10bdf36b7fbd38910c0bdff0f275ace679b45b922381c2723d676f8` | `NewSupplyCap(address indexed vToken, uint256 newSupplyCap)` |
| `0xb0d3622c24ac9bd967d8f37a25808b3e668fe7ed4f3075bbe82842d3e287c044` | `NewSupplyCapGuardian(address oldSupplyCapGuardian, address newSupplyCapGuardian)` |
| `0x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e` | `NewPauseGuardian(address oldPauseGuardian, address newPauseGuardian)` |
| `0x35007a986bcd36d2f73fc7f1b73762e12eadb4406dd163194950fd3b5a6a827d` | `ActionPausedMarket(address indexed vToken, uint8 indexed action, bool pauseState)` — **Venus per-market pause** (`action` = `Action` enum) |
| `0xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0` | `ActionPaused(string action, bool pauseState)` — global pause overload |
| `0x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0` | `ActionPaused(address vToken, string action, bool pauseState)` — string overload |
| `0xd7500633dd3ddd74daa7af62f8c8404c7fe4a81da179998db851696bed004b38` | `ActionProtocolPaused(bool state)` |
| `0x0f7eb572d1b3053a0a3a33c04151364cf88d163182a5e4e1088cb8e52321e08a` | `NewComptrollerLens(address oldComptrollerLens, address newComptrollerLens)` |
| `0xe1ddcb2dab8e5b03cfc8c67a0d5861d91d16f7bd2612fd381faf4541d212c9b2` | `NewVAIController(address oldVAIController, address newVAIController)` |
| `0x73747d68b346dce1e932bcd238282e7ac84c01569e1f8d0469c222fdc6e9d5a4` | `NewVAIMintRate(uint256 oldVAIMintRate, uint256 newVAIMintRate)` |

> **Action enum order** (for `ActionPausedMarket` `uint8`): `0=MINT, 1=REDEEM, 2=BORROW, 3=REPAY, 4=SEIZE, 5=LIQUIDATE, 6=TRANSFER, 7=ENTER_MARKET, 8=EXIT_MARKET`.

### 1.3 Comptroller — XVS reward distribution (emitted by the Unitroller; the per-action `Distributed*Venus` events fire from the PolicyFacet accrual hooks, the rest from RewardFacet)

| topic0 | Event |
|--------|-------|
| `0xfa9d964d891991c113b49e3db1932abd6c67263d387119707aafdd6c4010a3a9` | `DistributedSupplierVenus(address indexed vToken, address indexed supplier, uint256 venusDelta, uint256 venusSupplyIndex)` — **4-arg** |
| `0x837bdc11fca9f17ce44167944475225a205279b17e88c791c3b1f66f354668fb` | `DistributedBorrowerVenus(address indexed vToken, address indexed borrower, uint256 venusDelta, uint256 venusBorrowIndex)` — **4-arg** |
| `0xa9ff26899e4982e7634afa9f70115dcfb61a17d6e8cdd91aa837671d0ff40ba6` | `VenusSupplySpeedUpdated(address indexed vToken, uint256 newSpeed)` |
| `0x0c62c1bc89ec4c40dccb4d21543e782c5ba43897c0075d108d8964181ea3c51b` | `VenusBorrowSpeedUpdated(address indexed vToken, uint256 newSpeed)` |
| `0xd7fe674cac9eee3998fe3cbd7a6f93c3bc70509d97ec1550a59364be6438147e` | `VenusGranted(address indexed recipient, uint256 amount)` |
| `0xa82ad8dba07d5fde98bd3f0ef9b20c6426de9d477bb7647d46e0c7e50c7dc1b2` | `VenusSeized(address indexed holder, uint256 amount)` |
| `0xe81d4ac15e5afa1e708e66664eddc697177423d950d133bda8262d8885e6da3b` | `NewVenusVAIVaultRate(uint256 oldVenusVAIVaultRate, uint256 newVenusVAIVaultRate)` |

> **Verified live (BSC):** `DistributedSupplierVenus` 4-arg topic `0xfa9d964d…` had 233 logs (data 64 B = 2×uint256, 3 topics) in a recent 2 000-block window; the 5-arg variant returns **zero** logs and is not used.

### 1.4 Diamond (facet management — emitted by the Unitroller)

| topic0 | Event |
|--------|-------|
| `0x2e97860c6f47eab0292d51fa3ceec7e373c62af1e7eb2a28ae82998b80de6cfd` | `DiamondCut(IDiamondCut.FacetCut[] _diamondCut)` — **Venus single-arg form**, NOT the EIP-2535 3-arg standard |

### 1.5 Unitroller (Compound proxy — admin/impl events)

| topic0 | Event |
|--------|-------|
| `0xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815` | `NewPendingImplementation(address oldPendingImplementation, address newPendingImplementation)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` — Unitroller → new Diamond |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |

### 1.6 Liquidator (Core-Pool protocol liquidation router)

| topic0 | Event |
|--------|-------|
| `0xdd091524d794aecdb5235b2d816620c2598790835e0f3849808504c2dcb4f1a9` | `LiquidateBorrowedTokens(address indexed liquidator, address indexed borrower, uint256 repayAmount, address vTokenBorrowed, address indexed vTokenCollateral, uint256 seizeTokensForTreasury, uint256 seizeTokensForLiquidator)` |
| `0x0e9a1641744b21c49e4183ab9ce941d420e05a05a446c71875fb07814f362c1a` | `NewLiquidationTreasuryPercent(uint256 oldPercent, uint256 newPercent)` |
| `0x614c47c82976e8f145409efb6366fe2cefa323f389ed9354649262e38dbb3589` | `LiquidationRestricted(address indexed borrower)` |
| `0xfe40417b78788808c927141f806ef5082e7bba0f7790f2e85b811621a9109433` | `AllowlistEntryAdded(address indexed borrower, address indexed liquidator)` |
| `0xafec95c8612496c3ecf5dddc71e393528fe29bd145fbaf9c6b496d78d7e2d79b` | `NewProtocolShareReserve(address indexed oldProtocolShareReserve, address indexed newProtocolShareReserves)` |

### 1.7 InterestRateModel (JumpRateModel / WhitePaper)

| topic0 | Event |
|--------|-------|
| `0x6960ab234c7ef4b0c9197100f5393cfcde7c453ac910a27bd2000aa1dd4c068d` | `NewInterestParams(uint256 baseRatePerBlock, uint256 multiplierPerBlock, uint256 jumpMultiplierPerBlock, uint256 kink)` — JumpRateModel (4-arg) |
| `0xf35fa19c15e9ba782633a5df62a98b20217151addc68e3ff2cd623a48d37ec27` | `NewInterestParams(uint256 baseRatePerBlock, uint256 multiplierPerBlock)` — WhitePaperInterestRateModel (2-arg) |

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

Verified against deployed bytecode on BSC. Interface-file `uint` canonicalized to `uint256`.

### 2.1 VBep20 / vToken (per-market, ERC-20 markets)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa0712d68` | `mint(uint256 mintAmount)` | Supply underlying, receive vTokens. Emits `Mint`+`AccrueInterest`+`Transfer`. |
| `0x23323e03` | `mintBehalf(address receiver, uint256 mintAmount)` | Mint on behalf. Emits `MintBehalf`. |
| `0xdb006a75` | `redeem(uint256 redeemTokens)` | Burn vTokens for underlying. |
| `0x852a12e3` | `redeemUnderlying(uint256 redeemAmount)` | |
| `0xc5ebeaec` | `borrow(uint256 borrowAmount)` | Emits `Borrow`. |
| `0x0e752702` | `repayBorrow(uint256 repayAmount)` | `type(uint).max` repays full debt. |
| `0x2608f818` | `repayBorrowBehalf(address borrower, uint256 repayAmount)` | |
| `0xf5e3c462` | `liquidateBorrow(address borrower, uint256 repayAmount, address vTokenCollateral)` | Emits `LiquidateBorrow`. |
| `0xb2a02ff1` | `seize(address liquidator, address borrower, uint256 seizeTokens)` | Cross-market seizure. |
| `0xa6afed95` | `accrueInterest()` | Emits 4-arg `AccrueInterest`. |
| `0xbd6d894d` | `exchangeRateCurrent()` | Accrues then returns rate. |
| `0x182df0f5` | `exchangeRateStored()` | View. |
| `0x17bfdfbc` / `0x95dd9193` | `borrowBalanceCurrent(address)` / `borrowBalanceStored(address)` | |
| `0x3b1d21a2` | `getCash()` | Underlying held by the vToken. |
| `0xae9d70b0` | `supplyRatePerBlock()` | **Per-block** supply mantissa (NOT per-timestamp). |
| `0xf8f9da28` | `borrowRatePerBlock()` | **Per-block** borrow mantissa. |
| `0x6c540baf` | `accrualBlockNumber()` | **Block number** of last accrual (NOT a timestamp). |
| `0x47bd3718` / `0x8f840ddd` / `0xaa5af0fd` | `totalBorrows()` / `totalReserves()` / `borrowIndex()` | |
| `0x173b9904` | `reserveFactorMantissa()` | |
| `0x5fe3b567` | `comptroller()` | Returns the Unitroller. |
| `0xf3fdb15a` | `interestRateModel()` | Per-market IRM (may be a CheckpointView wrapper). |
| `0x6f307dc3` | `underlying()` | Underlying BEP-20. **Reverts/empty on vBNB.** |
| `0x5c60da1b` | `implementation()` | **Read this for the vToken logic** (VBep20Delegate) — NOT the EIP-1967 slot. **Reverts/empty on vBNB** (monolithic). |
| `0x555bcc40` | `_setImplementation(address implementation_, bool allowResign, bytes becomeImplementationData)` | Admin-only delegator logic swap. Emits `NewImplementation`. |
| `0x70a08231` / `0x18160ddd` / `0x313ce567` / `0x95d89b41` | `balanceOf` / `totalSupply` / `decimals` / `symbol` | vTokens: **8 decimals**, symbol `v`+underlying (e.g. `vUSDT`). Verified live. |
| `0xc37f68e2` | `getAccountSnapshot(address)` | `(uint err, uint vTokenBalance, uint borrowBalance, uint exchangeRateMantissa)` |
| `0xfca7820b` / `0xf2b3abbd` | `_setReserveFactor(uint256)` / `_setInterestRateModel(address)` | Admin. |

### 2.2 vBNB (native-gas market — distinct payable selectors)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1249c58b` | `mint()` | **Payable, no-arg** (amount = `msg.value`). |
| `0x4e4d9fea` | `repayBorrow()` | **Payable, no-arg.** |
| `0xaae40a2a` | `liquidateBorrow(address borrower, address vTokenCollateral)` | **Payable, no-arg repay** (repay = `msg.value`). |
| `0xc5ebeaec` / `0xdb006a75` / `0x852a12e3` | `borrow` / `redeem` / `redeemUnderlying` | Same selectors as ERC-20 vTokens. |

> vBNB has **no `mint(uint256)`, no `implementation()`, no `underlying()`** — it is the monolithic Compound `CEther` analog.

### 2.3 Comptroller (Diamond — selectors route to facets)

| Selector | Signature | Facet | Notes |
|----------|-----------|-------|-------|
| `0xc2998238` | `enterMarkets(address[] vTokens)` | **Market** | Emits `MarketEntered`. (Routes to MarketFacet `0x7397B6bc…`, not Policy — verified live via `facetAddress`.) |
| `0xede4edd0` | `exitMarket(address vToken)` | **Market** | Emits `MarketExited`. (MarketFacet, verified live.) |
| `0x5ec88c79` | `getAccountLiquidity(address)` | Policy | `(err, liquidity, shortfall)`. Shortfall>0 ⇒ liquidatable. (PolicyFacet `0x1CcDaf39…`, verified live.) |
| `0x4e79238f` | `getHypotheticalAccountLiquidity(address,address,uint256,uint256)` | Policy | (PolicyFacet, verified live.) |
| `0xabfceffc` | `getAssetsIn(address)` | Market | |
| `0xb0772d0b` | `getAllMarkets()` | **MarketFacet** | All listed vTokens. Verified routes to `0x7397B6bc…`. Re-read live; do not hardcode. |
| `0x8e8f294b` | `markets(address vToken)` | Market | **Live multi-pool shape (7 fields):** `(bool isListed, uint256 collateralFactorMantissa, bool isVenus, uint256 liquidationThresholdMantissa, uint256 liquidationIncentiveMantissa, uint96 poolId, bool isBorrowAllowed)`. Core Pool markets have `poolId == 0`. The old 3-field Compound shape `(isListed, collateralFactorMantissa, isVenus)` is stale — decoders that stop at 3 fields silently mis-read collateral factor only (still correct) but miss the per-market liquidation threshold/incentive. |
| `0x7dc0d1d0` | `oracle()` | — | Returns the **ResilientOracle** (not the legacy ChainlinkOracle). |
| `0xe8755446` | `closeFactorMantissa()` | — | |
| `0x4ada90af` | `liquidationIncentiveMantissa()` | — | |
| `0x4a584432` / `0x02c3bcbb` | `borrowCaps(address)` / `supplyCaps(address)` | — | |
| `0xc488847b` | `liquidateCalculateSeizeTokens(address,address,uint256)` | **Market** | Delegates math to ComptrollerLens. (MarketFacet, verified live.) |
| `0xd3270f99` | `comptrollerLens()` | — | Returns ComptrollerLens. |
| `0x9254f5e5` | `vaiController()` | — | Returns the VaiUnitroller (VAI hook). |
| `0xa76b3fda` | `_supportMarket(address)` | Market | Admin. Emits `MarketListed`. |
| `0x5cc4fdeb` | `setCollateralFactor(address vToken, uint256 newCollateralFactorMantissa, uint256 newLiquidationThresholdMantissa)` | Setter | **Live deployed form (multi-pool upgrade): 3-arg, no leading underscore.** Operates on Core Pool (`poolId 0`). Emits the 4-arg `NewCollateralFactor`. There is also `setCollateralFactor(uint96,address,uint256,uint256)` = `0x9159b177` for explicit pool selection. The stock-Compound `_setCollateralFactor(address,uint256)` (`0xe4028eee`) is **NOT in the live diamond** (`facetAddress` returns `0x0`). |
| `0x9bd8f6e8` | `setLiquidationIncentive(address vToken, uint256 newLiquidationIncentiveMantissa)` | Setter | **Live deployed form: per-market** (multi-pool upgrade). Emits the 4-arg `NewLiquidationIncentive`. The stock `_setLiquidationIncentive(uint256)` (`0x4fd42e17`) is absent. |
| `0x607ef6c1` / `0x51a485e4` | `_setMarketBorrowCaps(address[],uint256[])` / `_setMarketSupplyCaps(address[],uint256[])` | Setter | Emit `NewBorrowCap`/`NewSupplyCap`. |
| `0x2b5d790c` | `_setActionsPaused(address[] markets, uint8[] actions, bool paused)` | **SetterFacet** | Venus pause path. Verified routes to `0x4a45FBAf…`. Emits `ActionPausedMarket`. |
| `0x55ee1fe1` | `_setPriceOracle(address)` | Setter | Emits `NewPriceOracle`. |
| `0xadcd5fb9` | `claimVenus(address holder)` | **RewardFacet** | Verified routes to `0xfac00Dc8…`. |
| `0x86df31ee` | `claimVenus(address holder, address[] vTokens)` | Reward | |
| `0x8a7dc165` | `venusAccrued(address)` | Reward | |
| `0xbb82aa5e` | `comptrollerImplementation()` | Unitroller | **Read this for the live Diamond impl** (storage slot 2). |
| `0xdcfbc0c7` | `pendingComptrollerImplementation()` | Unitroller | Slot 3. |
| `0x1f931c1c` | `diamondCut((address,uint8,bytes4[])[],address,bytes)` | Diamond | EIP-2535 standard selector (Venus's own cut fn is `0xe57e69c6`, see below). |
| `0xe57e69c6` | `diamondCut((address,uint8,bytes4[])[])` | Diamond | **Venus single-arg cut fn.** Emits `DiamondCut`. |
| `0x7a0ed627` | `facets()` | Diamond | `(facetAddress, bytes4[] selectors)[]`. |
| `0x52ef6b2c` | `facetAddresses()` | Diamond | Returns the 5 facet addresses. |
| `0xadfca15e` | `facetFunctionSelectors(address)` | Diamond | |
| `0xcdffacc6` | `facetAddress(bytes4)` | Diamond | Which facet handles a selector. |

### 2.4 Unitroller

| Selector | Signature |
|----------|-----------|
| `0xe992a041` | `_setPendingImplementation(address)` |
| `0xc1e80334` | `_acceptImplementation()` |
| `0xb71d1a0c` | `_setPendingAdmin(address)` |
| `0xe9c714f2` | `_acceptAdmin()` |

### 2.5 Liquidator

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x64fd7078` | `liquidateBorrow(address vToken, address borrower, uint256 repayAmount, address vTokenCollateral)` | **Payable.** Emits `LiquidateBorrowedTokens`. |
| `0x89a2bc25` | `setTreasuryPercent(uint256)` | Emits `NewLiquidationTreasuryPercent`. |

### 2.6 Oracle (ResilientOracle / VenusChainlinkOracle)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfc57d4df` | `getUnderlyingPrice(address vToken)` | Comptroller's pricing entry point. Returns mantissa scaled to `36 − underlyingDecimals`. Verified live on `0x6592b5DE…`. |

---

## 3. Addresses — BNB Smart Chain (chain ID 56)  *[the ONLY Core-Pool chain]*

All verified via `eth_getCode` (non-empty) on `https://bsc-rpc.publicnode.com` on 2026-06-08. Proxy/diamond/delegator wiring read live (see §6).

### 3.1 Core system

| Role | Address | One-liner |
|------|---------|-----------|
| **UNITROLLER** (Comptroller proxy) | `0xfD36E2c2a6789Db23113685031d7F16329158384` | The risk engine. `comptrollerImplementation()`→ Diamond; `oracle()`→ ResilientOracle; `getAllMarkets()`=48; admin (slot 0)= NormalTimelock `0x939bd8d6…`. **Point all market-policy + reward monitors here.** |
| **DIAMOND** (Comptroller impl) | `0x82cA18785BBbacBeD1C4f482921E2B2E989D8C08` | The Diamond contract behind the Unitroller (= `Unitroller_Implementation`). Routes selectors to the 5 facets. |
| MarketFacet | `0x7397B6bcFA9332Cc8791c886F339B4D114651719` | `getAllMarkets`, `getAssetsIn`, `markets`, `_supportMarket`, **`enterMarkets`/`exitMarket`** (these route here, not Policy), `liquidateCalculateSeizeTokens`. |
| PolicyFacet | `0x1CcDaf39085bae4e27c3Ba100561b1AD1B5A6b80` | `getAccountLiquidity`/`getHypotheticalAccountLiquidity`, `mintAllowed`/`borrowAllowed`/etc. hooks (which emit the `DistributedSupplier/BorrowerVenus` XVS-reward events during accrual). |
| RewardFacet | `0xFaC00Dc856F454BB674c8588d4CC16Edef9dc28b` | `claimVenus`, `venusAccrued`, reward bookkeeping. (Note: the per-action `DistributedSupplier/BorrowerVenus` events are actually emitted from the policy hooks in PolicyFacet — all surface from the Unitroller address either way.) |
| SetterFacet | `0x4a45FBAf2A736bdF025DEd1D0Af3dF80070EDac0` | All admin parameter setters + `_setActionsPaused`. |
| FlashLoanFacet | `0x7F00af2f30a55e79311392C98fBBfA629D19b3A5` | Comptroller-level flash loan (later addition). |
| **VBep20Delegate** (shared vToken logic) | `0xb25b57599BA969c4829699F7E4Fc4076D14745E1` | Logic for every ERC-20 vToken delegator. |
| **ComptrollerLens** | `0x75A71Ad878f6f24616A2AE21d046C0C8E72f67F8` | Liquidity/seize math helper used by the Comptroller. |
| **VenusLens** | `0x344cD779C5aAF3436795B49f7C375E716A20f527` | Off-chain read aggregator. |
| SnapshotLens | `0xDE876091531c92BFED078af29CAaD3dbd4157f7a` | Account snapshot helper. |
| **Liquidator** (proxy) | `0x0870793286aada55d39ce7f82fb2766e8004cf43` | EIP-1967 transparent proxy. |
| Liquidator_Implementation | `0xD65297007411694aA18c2941a5EB2b6ed4E0b819` | Liquidator logic. |
| **ResilientOracle** (live `oracle()`) | `0x6592b5DE802159F3E74B2486b091D11a8256ab8A` | EIP-1967 proxy (impl `0x90d840…`). The address the Comptroller actually prices through. |
| VenusChainlinkOracle (legacy) | `0x7FabdD617200C9CB4dcf3dd2C41273e60552068A` | Legacy non-proxy Chainlink feeder; now a sub-feeder behind the ResilientOracle — **not** the value returned by `oracle()`. |
| VBNBAdmin (proxy) | `0x9A7890534d9d91d473F28cB97962d176e2B65f1d` | EIP-1967 proxy (impl `0xae2713Fb…`); admin wrapper that holds vBNB reserves/ProtocolShareReserve routing. |
| VAIController via VaiUnitroller | `0x004065D34C6b18cE4370ced1CeBDE94865DbFAFE` | VAI mint/repay hook (Compound Unitroller). Covered in `periphery.md`. |
| VTreasury | `0xF322942f644A996A617BD29c16bd7d231d9F35E9` | Reserve treasury. |
| NormalTimelock (Unitroller admin) | `0x939bd8d64c0a9583a7dcea9933f7b21697ab6396` | Governance admin of the Unitroller & vTokens (read live from slot 0). |

### 3.2 vToken markets — `symbol` is `v`+underlying, **8 decimals**, enumerate via `getAllMarkets()` (48 live)

The named markets in the canonical registry (a separately-deployed `VBep20Delegator` each — addresses are NOT derivable):

| vToken | Address | | vToken | Address |
|--------|---------|-|--------|---------|
| **vBNB** (native) | `0xA07c5b74C9B40447a954e1466938b865b6BBea36` | | vUSDT | `0xfD5840Cd36d94D7229439859C0112a4185BC0255` |
| vUSDC | `0xecA88125a5ADbe82614ffC12D0DB554E2e2867C8` | | vBUSD | `0x95c78222B3D6e262426483D42CfA53685A67Ab9D` |
| vBTC | `0x882C173bC7Ff3b7786CA16dfeD3DFFfb9Ee7847B` | | vETH | `0xf508fCD89b8bd15579dc79A6827cB4686A3592c8` |
| vDAI | `0x334b3eCB4DCa3593BCCC3c7EBD1A1C1d1780FBF1` | | vLINK | `0x650b940a1033B8A1b1873f78730FcFC73ec11f1f` |
| vXVS | `0x151B1e2635A717bcDc836ECd6FbB62B674FE3E1D` | | vLTC | `0x57A5297F2cB2c0AaC9D554660acd6D385Ab50c6B` |
| vADA | `0x9A0AF7FDb2065Ce470D72664DE73cAE409dA28Ec` | | vDOT | `0x1610bc33319e9398de5f57B33a5b184c806aD217` |
| vDOGE | `0xec3422Ef92B2fb59e84c8B02Ba73F1fE84Ed8D71` | | vFIL | `0xf91d58b5aE142DAcC749f58A49FCBac340Cb0343` |
| vBCH | `0x5F0388EBc2B94FA8E123F404b79cCF5f40b29176` | | vSXP | `0x2fF3d0F6990a40261c66E1ff2017aCBc282EB6d0` |
| vTRX | `0xC5D3466aA484B040eE977073fcF337f2c00071c1` | | vTRXOLD | `0x61eDcFe8Dd6bA3c891CB9bEc2dc7657B3B422E93` |
| vTUSD | `0xBf762cd5991cA1DCdDaC9ae5C638F5B5Dc3Bee6E` | | vTUSDOLD | `0x08CEB3F4a7ed3500cA0982bcd0FC7816688084c3` |
| vMATIC | `0x5c9476FcD6a4F9a3654139721c949c2233bBbBc8` | | vUNI | `0x27FF564707786720C71A2e5c1490A63266683612` |
| vCAKE | `0x86aC3974e2BD0d60825230fa6F355fF11409df5c` | | vAAVE | `0x26DA28954763B92139ED49283625ceCAf52C6f94` |
| vBETH | `0x972207A639CC1B374B893cc33Fa251b55CEB7c07` | | vWBETH | `0x6CFdEc747f37DAf3b87a35a1D9c8AD3063A1A8A0` |
| vFDUSD | `0xC4eF4229FEc74Ccfe17B2bdeF7715fAC740BA0ba` | | vTWT | `0x4d41a36D04D97785bcEA57b057C412b278e6Edcc` |
| vSOL | `0xBf515bA4D1b52FFdCeaBF20d31D705Ce789F2cEC` | | vXRP | `0xB248a295732e0225acd3337607cc01068e3b9c10` |
| vTHE | `0x86e06EAfa6A1eA631Eab51DE500E3D474933739f` | | vUSDe | `0x74ca6930108F775CC667894EEa33843e691680d7` |
| vSolvBTC | `0xf841cb62c19fCd4fF5CD0AaB5939f3140BaaC3Ea` | | vWBNB | `0x6bCa74586218dB34cdB402295796b79663d816e9` |
| vUSD1 | `0x0C1DA220D301155b87318B90692Da8dc43B67340` | | vU | `0x3d5E269787d562b74aCC55F18Bd26C5D09Fa245E` |
| vXAUM | `0x92e6Ea74a1A3047DabF4186405a21c7D63a0612A` | | vLUNA (deprecated) | `0xb91A659E88B51474767CD97EF3196A3e7cEDD2c8` |
| vUST (deprecated) | `0x78366446547D062f45b4c0f320cDaa6d710D87bb` | | vPT-* (Pendle PT markets) | several — enumerate live |

> The full `getAllMarkets()` array returns **48** addresses (some PT/`OLD`/deprecated markets remain in the array, Compound-style — they are never removed). **Always re-read `getAllMarkets()` rather than hardcoding this list.** Each vToken is an independently-deployed `VBep20Delegator` (no CREATE2 salt); addresses are not derivable.

### 3.3 Interest rate models

Each market reads its IRM via `vToken.interestRateModel()`. Venus deploys one `JumpRateModel` (or `WhitePaperInterestRateModel`) per parameter set, named in the registry as `JumpRateModel_base<bps>_slope<bps>_jump<bps>_kink<bps>_bpy<blocksPerYear>` (e.g. `JumpRateModel_base0bps_slope1000bps_jump25000bps_kink8000bps_bpy10512000 = 0x62A8919C…`). Recent re-parameterizations route through `CheckpointView` wrappers (which proxy to a base IRM and may revert on raw `baseRatePerBlock()` static-calls). **There are dozens of IRMs** — do not enumerate; read each market's live model. All are **immutable, per-block** (`bpy` = blocks-per-year; per-block rate accrual, consistent with §intro point 1).

---

## 4. Chains with NO Venus Core Pool

**Ethereum (1), Base (8453), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon PoS (137): the Venus Core-Pool legacy codebase is NOT deployed.** Triangulated three ways and recorded as a finding, not an omission:

1. **`eth_getCode` of the BSC Unitroller `0xfD36E2c2…` returns `0x`** on all six chains (checked live on each publicnode RPC, 2026-06-08).
2. The canonical `VenusProtocol/venus-protocol` per-chain `deployments/<chain>_addresses.json` files for `ethereum` and `basemainnet` contain **no** `Unitroller`, `Comptroller`, `Unitroller_Implementation`, or `VBep20Delegate` keys — only isolated-pools contracts.
3. On those chains the Venus UI's "Core Pool" is an **isolated-pools** `Comptroller` (a `ComptrollerBeacon`-backed beacon-proxy with `RewardsDistributor` contracts and a different event set). That is a separate codebase — see `isolated-pools.md`. Do not author Core-Pool monitors (vBNB, VBep20Delegate, Diamond facets, `DistributedSupplierVenus`) for these six chains.

---

## 5. Cross-chain summary

| Chain | ID | Core Pool? | Unitroller | Diamond (Comptroller impl) | VBep20Delegate | vBNB | Markets |
|-------|----|-----------|-----------|---------------------------|----------------|------|---------|
| **BNB Smart Chain** | 56 | ✅ | `0xfD36E2c2…8384` | `0x82cA1878…8C08` | `0xb25b5759…45E1` | `0xA07c5b74…ea36` | 48 (`getAllMarkets()`) |
| Ethereum | 1 | ❌ (isolated pools only) | — | — | — | — | 0 |
| Base | 8453 | ❌ (isolated pools only) | — | — | — | — | 0 |
| Avalanche | 43114 | ❌ (not deployed) | — | — | — | — | 0 |
| Arbitrum One | 42161 | ❌ (isolated pools only) | — | — | — | — | 0 |
| Optimism | 10 | ❌ (isolated pools only) | — | — | — | — | 0 |
| Polygon PoS | 137 | ❌ (isolated pools only) | — | — | — | — | 0 |

Patterns to internalize:
1. **Core Pool = BSC singleton.** There is exactly one Unitroller, one Diamond, 5 facets, one Liquidator, one ResilientOracle — all on BSC. No cross-chain address reuse exists because there are no other Core deployments.
2. **Markets are enumerated, not derived** — re-read `getAllMarkets()` (48 and growing) rather than hardcoding.
3. **The Diamond emits all Comptroller events from the Unitroller address** (delegatecall) — point Comptroller monitors at the Unitroller, never at the facet addresses.

---

## 6. Proxies (old & new)

Venus Core mixes **four** proxy/upgrade families. Getting them wrong is the #1 integration error.

| Contract | Pattern | How to read the impl | Verified (BSC, 2026-06-08) |
|----------|---------|----------------------|----------------------------|
| **Unitroller** (Comptroller) | **Compound Unitroller** — NOT EIP-1967. Impl in **storage slot 2** (`comptrollerImplementation`), pending in slot 3; `admin` slot 0, `pendingAdmin` slot 1. | `comptrollerImplementation()` (`0xbb82aa5e`) or `eth_getStorageAt(slot 2)`. | slot0=`…939bd8d6…` (NormalTimelock=admin) ✓; slot2=`…82ca1878…8c08`=Diamond ✓; EIP-1967 impl slot = `0x0` ✓ |
| **Diamond** (Comptroller impl) | **EIP-2535-style Diamond** sitting *behind* the Unitroller. Per-selector dispatch via internal `selectorToFacetAndPosition` mapping. | `facetAddresses()` (`0x52ef6b2c`) / `facetAddress(bytes4)` (`0xcdffacc6`). | `facetAddresses()` = 5 facets ✓; `facetAddress(getAllMarkets)`→MarketFacet ✓, `facetAddress(claimVenus)`→RewardFacet ✓, `facetAddress(_setActionsPaused)`→SetterFacet ✓ |
| **vToken** (VBep20Delegator) | **Compound delegator** — NOT EIP-1967. `implementation` is a plain storage var; swapped via `_setImplementation(address,bool,bytes)`. | `implementation()` (`0x5c60da1b`). | vUSDT `implementation()`=`0xb25b5759…45E1`=VBep20Delegate ✓; EIP-1967 impl slot = `0x0` ✓; `comptroller()`→Unitroller ✓ |
| **vBNB** | **Immutable / monolithic** — no proxy, no delegator. | n/a. | `implementation()`→`0x` (reverts) ✓; `underlying()`→`0x` (native) ✓ |
| **Liquidator** | **EIP-1967 transparent proxy** (OpenZeppelin). | EIP-1967 impl slot `0x360894…bbc`. | impl slot=`0xD65297…0B819`=Liquidator_Implementation ✓ |
| **ResilientOracle** | **EIP-1967 transparent proxy**. | EIP-1967 impl slot. | impl slot=`0x90d840f4…865c` ✓; `getUnderlyingPrice(vUSDT)` returns live price ✓ |
| **VBNBAdmin** | **EIP-1967 transparent proxy**. | EIP-1967 impl slot. | impl slot=`0xae2713Fb…c275` ✓ |
| **VenusChainlinkOracle** (legacy) | **Plain non-proxy** feeder. | n/a. | EIP-1967 impl slot = `0x0` (not a proxy) ✓ |
| **JumpRateModel / WhitePaperInterestRateModel** | **Immutable.** | n/a (read params via getters; some wrapped by CheckpointView). | per-market `interestRateModel()` returns a fixed address. |

```
Unitroller storage layout (Compound):
  slot 0 = admin                      (= NormalTimelock 0x939bd8d6…)
  slot 1 = pendingAdmin
  slot 2 = comptrollerImplementation  ← the Diamond (live Comptroller logic)
  slot 3 = pendingComptrollerImplementation
EIP-1967 impl slot  = 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc  (empty on Unitroller, vTokens, vBNB; used by Liquidator/ResilientOracle/VBNBAdmin)
EIP-1967 admin slot = 0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103
```

---

## 7. Detection invariants & gotchas

1. **Per-block, not timestamp.** `accrualBlockNumber()` is a **block number**; rates are `supplyRatePerBlock()`/`borrowRatePerBlock()` (per-block, ~3 s blocks on BSC). APY uses `bpy` ≈ 10 512 000 historically (re-parameterized over time). Calling `*PerTimestamp`/`accrualBlockTimestamp` reverts. (Opposite of the Moonwell fork.)
2. **`AccrueInterest` is 4-arg** (`0x4dec04e7…`, 128-byte data). Verified live on BSC vUSDT. Stock-Compound 3-arg decoders mis-parse it.
3. **The live `Mint`/`Redeem`/`MintBehalf` events carry an extra `totalSupply` field** (the deployed VBep20Delegate upgrade). Live forms: `Mint(address,uint256,uint256,uint256)`=`0xb4c03061…` (128 B), `Redeem(address,uint256,uint256,uint256)`=`0xbd5034ff…` (128 B), `MintBehalf(address,address,uint256,uint256,uint256)`=`0xa24ddbdf…` (160 B). The stock-Compound 3/4-arg forms (`0x4c209b5f…`/`0xe5b754fb…`/`0x297989b8…`) **no longer fire** (0 occurrences in the recent ~1M blocks) — keep them only for pre-upgrade historical back-fill. A monitor keyed only on the old `Mint`/`Redeem` topics catches **nothing** for current activity. Bonus: the **new** 4-arg `Mint` no longer collides with PancakeSwap/Uniswap V2 `Mint`; only the legacy 3-arg topic does (filter by emitter when back-filling it). ERC-20 `Transfer`/`Approval` still collide with every token — filter by emitter.
4. **The Comptroller is a Diamond behind the Unitroller.** All Comptroller events (`MarketListed`, `NewCollateralFactor`, `ActionPausedMarket`, `DistributedSupplierVenus`, …) are emitted from the **Unitroller address**, not the facets. Watch the Unitroller. The five facet addresses are pure logic — they emit nothing on their own.
5. **`DiamondCut` is Venus's single-arg form** (`0x2e97860c…`, `DiamondCut(FacetCut[])`), NOT the EIP-2535 3-arg standard (`0x8faa7087…`). A facet swap is the highest-severity admin action — watch this topic on the Unitroller.
6. **XVS rewards are emitted by the Comptroller itself** as 4-arg `DistributedSupplierVenus`/`DistributedBorrowerVenus` (`0xfa9d964d…`/`0x837bdc11…`) — there is **no** separate Core-Pool reward distributor proxy (isolated pools differ). The 5-arg variant is unused.
7. **Venus pause path is `ActionPausedMarket(address indexed vToken, uint8 indexed action, bool)`** (`0x35007a98…`) — `action` is the `Action` enum (`0=MINT … 5=LIQUIDATE …`), **indexed**, so filter by topic2 for a specific action. The Compound string-overloads (`0xef159d9a…`, `0x71aec636…`) also exist but the live Venus governance path uses `_setActionsPaused` → `ActionPausedMarket`.
8. **vBNB is special.** It is monolithic (no delegator, no `implementation()`/`underlying()`), and uses **payable no-arg** `mint()` / `repayBorrow()` (`0x1249c58b`/`0x4e4d9fea`) and `liquidateBorrow(address,address)` (`0xaae40a2a`) — different selectors from the ERC-20 vTokens. The `VBNBAdmin` proxy wraps reserve management for it.
9. **`oracle()` returns the ResilientOracle, not the legacy ChainlinkOracle.** The registry's `VenusChainlinkOracle` (`0x7Fabdd…`) is now a sub-feeder; price monitoring keys on `getUnderlyingPrice` against the live `oracle()` (`0x6592b5DE…`).
10. **Liquidations have two paths.** Direct: `vToken.liquidateBorrow(...)` → `LiquidateBorrow` on the borrowed vToken + a vToken-share `Transfer` to the liquidator. Protocol-routed: the **Liquidator** contract's `liquidateBorrow(address,address,uint256,address)` (`0x64fd7078`) → `LiquidateBorrowedTokens` (`0xdd091524…`, splits seize between treasury and liquidator). Watch both.
11. **Markets are enumerated, not derived** — read `getAllMarkets()` (48 incl. `OLD`/deprecated/PT markets, never removed). Distinguish deprecated (`vTRXOLD`, `vTUSDOLD`, `vLUNA`, `vUST`) by address.
12. **Core Pool is BSC-only.** On the other six chains, "Venus Core Pool" is an isolated-pools deployment — never aim Core-Pool monitors there. The BSC Unitroller address returns `0x` everywhere else.
13. **The live Comptroller is the multi-pool-upgraded SetterFacet — collateral-factor / liquidation-incentive events are now 4-arg, pool-aware.** `NewCollateralFactor` is `(uint96 indexed poolId, address indexed vToken, uint256 old, uint256 new)` → topic `0x0d1a6153…` (Core Pool = `poolId 0`), and `NewLiquidationIncentive` is the analogous 4-arg per-market form → topic `0xc1d7bc09…`. The stock-Compound 3-arg `NewCollateralFactor` (`0x70483e65…`) and 2-arg `NewLiquidationIncentive` (`0xaeba5a6c…`) are **no longer emitted** — confirmed absent from the live SetterFacet bytecode. The governance setters are `setCollateralFactor(address,uint256,uint256)` (`0x5cc4fdeb`) / `setLiquidationIncentive(address,uint256)` (`0x9bd8f6e8`) — note: **no leading underscore**, unlike the old Compound `_set…` names, which are not in the live diamond.
14. **`enterMarkets`/`exitMarket`/`liquidateCalculateSeizeTokens` live in the MarketFacet, not the PolicyFacet.** Only `getAccountLiquidity`/`getHypotheticalAccountLiquidity` (and the `*Allowed` hooks) sit in PolicyFacet. This only matters when reading `facetAddress(selector)` or tracing per-facet upgrades — all events still surface from the Unitroller.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- vToken / VBep20 / vBNB
TOPIC_ACCRUE_INTEREST        = '\x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04'  -- 4-arg!
TOPIC_MINT                   = '\xb4c03061fb5b7fed76389d5af8f2e0ddb09f8c70d1333abbb62582835e10accb'  -- LIVE 4-arg Mint(addr,u,u,totalSupply); no Pancake collision
TOPIC_MINT_LEGACY3           = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'  -- pre-upgrade 3-arg only; collides w/ Pancake/UniV2 Mint
TOPIC_MINT_BEHALF            = '\xa24ddbdf0865ba440d364725c062eac72a908faeedffc33fe64d4640c82e3ab8'  -- LIVE 5-arg
TOPIC_MINT_BEHALF_LEGACY4    = '\x297989b84a5f5b82d2ee0c266504c19bd9b10b410f187dc72ca4b0f0faecb345'  -- pre-upgrade 4-arg only
TOPIC_REDEEM                 = '\xbd5034ffbd47e4e72a94baa2cdb74c6fad73cb3bcdc13036b72ec8306f5a7646'  -- LIVE 4-arg Redeem(addr,u,u,totalSupply)
TOPIC_REDEEM_LEGACY3         = '\xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929'  -- pre-upgrade 3-arg only
TOPIC_REDEEM_FEE             = '\xccf8e53b86a99b7e9ecf796342c165764d66154780f638c08e6241d711fba6d4'  -- RedeemFee (rare)
TOPIC_BORROW                 = '\x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'
TOPIC_REPAY_BORROW           = '\x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1'
TOPIC_LIQUIDATE_BORROW       = '\x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
TOPIC_RESERVES_ADDED         = '\xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5'
TOPIC_RESERVES_REDUCED       = '\x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e'
TOPIC_NEW_RESERVE_FACTOR     = '\xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460'
TOPIC_NEW_MARKET_IRM         = '\xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926'
TOPIC_VTOKEN_NEW_IMPL        = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'
TOPIC_ERC20_TRANSFER         = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- Comptroller (emitted by the Unitroller)
TOPIC_MARKET_LISTED          = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_MARKET_UNLISTED        = '\x302feb03efd5741df80efe7f97f5d93d74d46a542a3d312d0faae64fa1f3e0e9'
TOPIC_MARKET_ENTERED         = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'
TOPIC_MARKET_EXITED          = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_NEW_CLOSE_FACTOR       = '\x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9'
TOPIC_NEW_COLLATERAL_FACTOR  = '\x0d1a615379dc62cec7bc63b7e313a07ed659918f4ad3720b3af8041b305146f2'  -- LIVE 4-arg (uint96 poolId, address vToken, u, u); old 3-arg 0x70483e65 no longer emitted
TOPIC_NEW_LIQ_INCENTIVE      = '\xc1d7bc090f3a87255c2f4e56f66d1b7a49683d279f77921b1701aa5d733ef745'  -- LIVE 4-arg per-market; old 2-arg 0xaeba5a6c no longer emitted
TOPIC_NEW_PRICE_ORACLE       = '\xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22'
TOPIC_NEW_BORROW_CAP         = '\x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6'
TOPIC_NEW_SUPPLY_CAP         = '\x9e0ad9cee10bdf36b7fbd38910c0bdff0f275ace679b45b922381c2723d676f8'
TOPIC_NEW_PAUSE_GUARDIAN     = '\x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e'
TOPIC_ACTION_PAUSED_MARKET   = '\x35007a986bcd36d2f73fc7f1b73762e12eadb4406dd163194950fd3b5a6a827d'  -- (address,uint8,bool) Venus
TOPIC_ACTION_PAUSED_GLOBAL   = '\xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0'  -- (string,bool)
TOPIC_ACTION_PAUSED_STR      = '\x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0'  -- (address,string,bool)
TOPIC_ACTION_PROTOCOL_PAUSED = '\xd7500633dd3ddd74daa7af62f8c8404c7fe4a81da179998db851696bed004b38'
TOPIC_NEW_COMPTROLLER_LENS   = '\x0f7eb572d1b3053a0a3a33c04151364cf88d163182a5e4e1088cb8e52321e08a'
TOPIC_NEW_VAI_CONTROLLER     = '\xe1ddcb2dab8e5b03cfc8c67a0d5861d91d16f7bd2612fd381faf4541d212c9b2'
-- Comptroller XVS rewards
TOPIC_DIST_SUPPLIER_VENUS    = '\xfa9d964d891991c113b49e3db1932abd6c67263d387119707aafdd6c4010a3a9'  -- 4-arg
TOPIC_DIST_BORROWER_VENUS    = '\x837bdc11fca9f17ce44167944475225a205279b17e88c791c3b1f66f354668fb'  -- 4-arg
TOPIC_VENUS_SUPPLY_SPEED     = '\xa9ff26899e4982e7634afa9f70115dcfb61a17d6e8cdd91aa837671d0ff40ba6'
TOPIC_VENUS_BORROW_SPEED     = '\x0c62c1bc89ec4c40dccb4d21543e782c5ba43897c0075d108d8964181ea3c51b'
TOPIC_VENUS_GRANTED          = '\xd7fe674cac9eee3998fe3cbd7a6f93c3bc70509d97ec1550a59364be6438147e'
TOPIC_VENUS_SEIZED           = '\xa82ad8dba07d5fde98bd3f0ef9b20c6426de9d477bb7647d46e0c7e50c7dc1b2'
-- Diamond
TOPIC_DIAMOND_CUT            = '\x2e97860c6f47eab0292d51fa3ceec7e373c62af1e7eb2a28ae82998b80de6cfd'  -- single-arg Venus form
-- Unitroller
TOPIC_NEW_IMPLEMENTATION     = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'
TOPIC_NEW_PENDING_IMPL       = '\xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815'
-- Liquidator
TOPIC_LIQ_BORROWED_TOKENS    = '\xdd091524d794aecdb5235b2d816620c2598790835e0f3849808504c2dcb4f1a9'
TOPIC_LIQ_NEW_TREASURY_PCT   = '\x0e9a1641744b21c49e4183ab9ce941d420e05a05a446c71875fb07814f362c1a'
-- InterestRateModel
TOPIC_NEW_INTEREST_PARAMS_J  = '\x6960ab234c7ef4b0c9197100f5393cfcde7c453ac910a27bd2000aa1dd4c068d'  -- JumpRate 4-arg
TOPIC_NEW_INTEREST_PARAMS_W  = '\xf35fa19c15e9ba782633a5df62a98b20217151addc68e3ff2cd623a48d37ec27'  -- WhitePaper 2-arg

-- ===== Selectors =====
SEL_MINT                     = '\xa0712d68'   -- mint(uint256)  (ERC-20 vToken)
SEL_MINT_BEHALF              = '\x23323e03'   -- mintBehalf(address,uint256)
SEL_VBNB_MINT                = '\x1249c58b'   -- mint()  (payable, vBNB)
SEL_VBNB_REPAY               = '\x4e4d9fea'   -- repayBorrow()  (payable, vBNB)
SEL_VBNB_LIQUIDATE           = '\xaae40a2a'   -- liquidateBorrow(address,address)  (payable, vBNB)
SEL_REDEEM                   = '\xdb006a75'
SEL_REDEEM_UNDERLYING        = '\x852a12e3'
SEL_BORROW                   = '\xc5ebeaec'
SEL_REPAY_BORROW             = '\x0e752702'
SEL_REPAY_BORROW_BEHALF      = '\x2608f818'
SEL_LIQUIDATE_BORROW         = '\xf5e3c462'   -- liquidateBorrow(address,uint256,address)
SEL_SEIZE                    = '\xb2a02ff1'
SEL_EXCHANGE_RATE_STORED     = '\x182df0f5'
SEL_SUPPLY_RATE_PER_BLOCK    = '\xae9d70b0'   -- per-BLOCK (not timestamp)
SEL_BORROW_RATE_PER_BLOCK    = '\xf8f9da28'
SEL_ACCRUAL_BLOCK_NUMBER     = '\x6c540baf'
SEL_GET_CASH                 = '\x3b1d21a2'
SEL_UNDERLYING               = '\x6f307dc3'   -- reverts on vBNB
SEL_VTOKEN_IMPLEMENTATION    = '\x5c60da1b'   -- implementation()  (delegator; reverts on vBNB)
SEL_SET_IMPLEMENTATION       = '\x555bcc40'
SEL_COMPTROLLER_IMPL         = '\xbb82aa5e'   -- comptrollerImplementation()  (Unitroller slot 2 = Diamond)
SEL_GET_ALL_MARKETS          = '\xb0772d0b'
SEL_GET_ACCOUNT_LIQUIDITY    = '\x5ec88c79'
SEL_ENTER_MARKETS            = '\xc2998238'
SEL_EXIT_MARKET              = '\xede4edd0'
SEL_ORACLE                   = '\x7dc0d1d0'
SEL_GET_UNDERLYING_PRICE     = '\xfc57d4df'
SEL_CLAIM_VENUS              = '\xadcd5fb9'   -- claimVenus(address)
SEL_SET_ACTIONS_PAUSED       = '\x2b5d790c'   -- _setActionsPaused(address[],uint8[],bool)
SEL_SET_COLLATERAL_FACTOR    = '\x5cc4fdeb'   -- setCollateralFactor(address,uint256,uint256)  LIVE (NOT _setCollateralFactor 0xe4028eee)
SEL_SET_LIQ_INCENTIVE        = '\x9bd8f6e8'   -- setLiquidationIncentive(address,uint256)  LIVE
SEL_VAI_CONTROLLER           = '\x9254f5e5'
SEL_COMPTROLLER_LENS         = '\xd3270f99'
-- Diamond
SEL_DIAMOND_CUT_VENUS        = '\xe57e69c6'   -- diamondCut((address,uint8,bytes4[])[])  single-arg
SEL_DIAMOND_CUT_2535         = '\x1f931c1c'   -- diamondCut((address,uint8,bytes4[])[],address,bytes)
SEL_FACETS                   = '\x7a0ed627'
SEL_FACET_ADDRESSES          = '\x52ef6b2c'
SEL_FACET_ADDRESS            = '\xcdffacc6'   -- facetAddress(bytes4)
-- Liquidator
SEL_LIQUIDATOR_LIQUIDATE     = '\x64fd7078'   -- liquidateBorrow(address,address,uint256,address)

-- ===== BNB Smart Chain (chain 56) — the ONLY Core-Pool chain =====
BSC_UNITROLLER               = '\xfd36e2c2a6789db23113685031d7f16329158384'
BSC_DIAMOND_COMPTROLLER_IMPL = '\x82ca18785bbbacbed1c4f482921e2b2e989d8c08'
BSC_FACET_MARKET             = '\x7397b6bcfa9332cc8791c886f339b4d114651719'
BSC_FACET_POLICY             = '\x1ccdaf39085bae4e27c3ba100561b1ad1b5a6b80'
BSC_FACET_REWARD             = '\xfac00dc856f454bb674c8588d4cc16edef9dc28b'
BSC_FACET_SETTER             = '\x4a45fbaf2a736bdf025ded1d0af3df80070edac0'
BSC_FACET_FLASHLOAN          = '\x7f00af2f30a55e79311392c98fbbfa629d19b3a5'
BSC_VBEP20_DELEGATE          = '\xb25b57599ba969c4829699f7e4fc4076d14745e1'
BSC_COMPTROLLER_LENS         = '\x75a71ad878f6f24616a2ae21d046c0c8e72f67f8'
BSC_VENUS_LENS               = '\x344cd779c5aaf3436795b49f7c375e716a20f527'
BSC_LIQUIDATOR               = '\x0870793286aada55d39ce7f82fb2766e8004cf43'
BSC_LIQUIDATOR_IMPL          = '\xd65297007411694aa18c2941a5eb2b6ed4e0b819'
BSC_RESILIENT_ORACLE         = '\x6592b5de802159f3e74b2486b091d11a8256ab8a'
BSC_VENUS_CHAINLINK_ORACLE   = '\x7fabdd617200c9cb4dcf3dd2c41273e60552068a'
BSC_VBNB_ADMIN               = '\x9a7890534d9d91d473f28cb97962d176e2b65f1d'
BSC_VAI_UNITROLLER           = '\x004065d34c6b18ce4370ced1cebde94865dbfafe'
BSC_NORMAL_TIMELOCK          = '\x939bd8d64c0a9583a7dcea9933f7b21697ab6396'
-- vToken markets (subset; enumerate via getAllMarkets())
BSC_VBNB                     = '\xa07c5b74c9b40447a954e1466938b865b6bbea36'
BSC_VUSDT                    = '\xfd5840cd36d94d7229439859c0112a4185bc0255'
BSC_VUSDC                    = '\xeca88125a5adbe82614ffc12d0db554e2e2867c8'
BSC_VBTC                     = '\x882c173bc7ff3b7786ca16dfed3dfffb9ee7847b'
BSC_VETH                     = '\xf508fcd89b8bd15579dc79a6827cb4686a3592c8'
BSC_VBUSD                    = '\x95c78222b3d6e262426483d42cfa53685a67ab9d'
BSC_VXVS                     = '\x151b1e2635a717bcdc836ecd6fbb62b674fe3e1d'

-- EIP-1967 slots (used by Liquidator/ResilientOracle/VBNBAdmin; EMPTY on Unitroller/vTokens/vBNB)
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT           = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
```

---

## 9. Verification & sources

- **topic0 / selectors:** all computed locally as `keccak256(canonical signature)` / `[0:4]`. Spot-matched against known Compound selectors (`mint`=`0xa0712d68`, `borrow`=`0xc5ebeaec`, `getAllMarkets`=`0xb0772d0b`, `getUnderlyingPrice`=`0xfc57d4df`) and ERC-20 (`Transfer`=`0xddf252ad…`). Event/fn signatures taken from `VenusProtocol/venus-protocol` source: `contracts/Tokens/VTokens/VTokenInterfaces.sol` (`AccrueInterest` 4-arg, line ~200), `contracts/Comptroller/Diamond/Diamond.sol` (`DiamondCut(FacetCut[])`), `contracts/Comptroller/Diamond/interfaces/IDiamondCut.sol` (`FacetCut(address,uint8,bytes4[])`, `FacetCutAction{Add,Replace,Remove}`), `contracts/Comptroller/Diamond/facets/XVSRewardsHelper.sol` (`DistributedSupplierVenus`/`DistributedBorrowerVenus` 4-arg), `contracts/Comptroller/ComptrollerInterface.sol` (`Action` enum order), `contracts/Liquidator/Liquidator.sol` (`LiquidateBorrowedTokens`, `liquidateBorrow(address,address,uint256,address)`).
- **Live event confirmation (BSC):** `AccrueInterest` 4-arg topic `0x4dec04e7…` confirmed against recent vUSDT logs (data = 128 B = 4×uint256). `DistributedSupplierVenus`/`DistributedBorrowerVenus` confirmed as the **4-arg** forms (`0xfa9d964d…`/`0x837bdc11…`, 64-B data, 3 topics; 294 logs in a recent 2 000-block window on the Unitroller); the 5-arg variant returned **zero** logs. **Workhorse vToken events are the upgraded forms:** the deployed VBep20Delegate emits `Mint(addr,u,u,totalSupply)`=`0xb4c03061…` (128 B), `Redeem(addr,u,u,totalSupply)`=`0xbd5034ff…` (128 B), `MintBehalf(addr,addr,u,u,totalSupply)`=`0xa24ddbdf…` (160 B); the legacy 3/4-arg Compound forms (`0x4c209b5f…`/`0xe5b754fb…`/`0x297989b8…`) returned **0 logs over the recent ~1M blocks** (and the legacy 3-arg `Mint` topic is absent from the live VBep20Delegate bytecode). `Borrow`(128 B)/`RepayBorrow`/`LiquidateBorrow`(5-arg) topics are unchanged.
- **Diamond confirmation (BSC):** Unitroller `comptrollerImplementation()` = `0x82cA1878…` (the Diamond); `facetAddresses()` returns the 5 facets; `facetAddress(0xb0772d0b)`→MarketFacet, `facetAddress(0xadcd5fb9)`→RewardFacet, `facetAddress(0x2b5d790c)`→SetterFacet — confirming per-selector dispatch. `facetAddress(0xc2998238 enterMarkets)`/`(0xede4edd0 exitMarket)`/`(0xc488847b liquidateCalculateSeizeTokens)` all → **MarketFacet** (not Policy); `facetAddress(0x5ec88c79 getAccountLiquidity)`/`(0x4e79238f)` → PolicyFacet.
- **Multi-pool / upgraded-facet confirmation (BSC):** the deployed SetterFacet (`0x4a45FBAf…`) routes `setCollateralFactor(address,uint256,uint256)`=`0x5cc4fdeb` and `setLiquidationIncentive(address,uint256)`=`0x9bd8f6e8`; the old `_setCollateralFactor(address,uint256)`=`0xe4028eee` resolves to `0x0` (not in diamond). Its bytecode contains the 4-arg `NewCollateralFactor`=`0x0d1a6153…` and 4-arg `NewLiquidationIncentive`=`0xc1d7bc09…` and **not** the legacy 3-arg/2-arg topics. `markets(vUSDT)` returns 7 fields `(isListed, collateralFactorMantissa, isVenus, liquidationThresholdMantissa, liquidationIncentiveMantissa, poolId=0, isBorrowAllowed)` — matching the `Market` struct in `contracts/Comptroller/ComptrollerStorage.sol`. Sources: `contracts/Comptroller/Diamond/facets/SetterFacet.sol` (`setCollateralFactor`/`setLiquidationIncentive` + 4-arg events), `contracts/Tokens/VTokens/VTokenInterfaces.sol` (`Mint`/`Redeem`/`MintBehalf` with trailing `uint256 totalSupply`, `RedeemFee`).
- **Proxy wiring (live, BSC):** Unitroller slot 0 (admin)=`0x939bd8d6…` (NormalTimelock), slot 2 (impl)=`0x82cA1878…` (Diamond), EIP-1967 impl slot empty. vUSDT `implementation()`=`0xb25b5759…` (VBep20Delegate), `comptroller()`=Unitroller, `symbol()`="vUSDT", `decimals()`=8, EIP-1967 impl slot empty. vBNB `implementation()`/`underlying()` revert (monolithic). Liquidator EIP-1967 impl slot=`0xD65297…`. ResilientOracle EIP-1967 impl slot=`0x90d840…`, `getUnderlyingPrice(vUSDT)` returns a live price. VBNBAdmin EIP-1967 impl slot=`0xae2713Fb…`. VenusChainlinkOracle EIP-1967 slot empty (non-proxy). Comptroller `oracle()`=`0x6592b5DE…` (ResilientOracle, ≠ the legacy ChainlinkOracle).
- **Accrual model:** BSC vUSDT `supplyRatePerBlock()` returns a live value → per-block accrual confirmed.
- **Non-deployment:** the BSC Unitroller `0xfD36E2c2…` returns empty `eth_getCode` (`0x`) on Ethereum, Base, Avalanche, Arbitrum, Optimism and Polygon (checked live on each publicnode RPC). The `ethereum`/`basemainnet` `deployments/*_addresses.json` files contain no Core-Pool keys (`Unitroller`/`Comptroller`/`VBep20Delegate`) — those chains run isolated pools only.

Authoritative sources:
- [`VenusProtocol/venus-protocol`](https://github.com/VenusProtocol/venus-protocol) — `contracts/` (Comptroller/Diamond + facets, Tokens/VTokens, Liquidator, InterestRateModels, Lens) + `deployments/<chain>_addresses.json` address registry.
- [docs.venus.io](https://docs.venus.io) — Core-Pool documentation (BNB Chain).
- [Compound V2](https://github.com/compound-finance/compound-protocol) — fork ancestor (cToken/Comptroller/Unitroller).
- [EIP-2535 Diamonds](https://eips.ethereum.org/EIPS/eip-2535) — for the standard (3-arg) `DiamondCut`/`diamondCut` that Venus deviates from.
- RPCs: publicnode (`bsc-rpc`, plus `ethereum-rpc`, `base-rpc`, `avalanche-c-chain-rpc`, `arbitrum-one-rpc`, `optimism-rpc`, `polygon-bor-rpc` for the non-deployment checks).
