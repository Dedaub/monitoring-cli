# Flux Finance — Topics, Selectors, Addresses (Ethereum mainnet only)

**Status:** verified against Ethereum mainnet RPC (`https://ethereum-rpc.publicnode.com`) and the canonical `flux-finance/contracts` repo on 2026-06-08. Every topic0/selector recomputed locally as `keccak256(signature)`; every address existence-checked via `eth_getCode`; proxy wiring read live from `comptrollerImplementation()`/`implementation()` getters and the EIP-1967 slot; sample event topics confirmed against live `eth_getLogs`.
**Scope:** Flux Finance — Ondo Finance's permissioned **Compound V2 fork** lending market. **Deployed on Ethereum mainnet (chain 1) ONLY.** The user asked about 7 chains; Flux is **NOT deployed on Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), or Polygon PoS (137)** — every Flux address returns empty `eth_getCode` on all six (§5). Topics/selectors are chain-agnostic, but since Flux is single-chain they only matter on Ethereum. Addresses are network-specific.

Flux Finance is a **soft fork of Compound V2** (`Comptroller`/`Unitroller` + per-market `CErc20Delegator` markets + per-market `JumpRateModelV2`), built by the Ondo team to run an on-chain Treasury-repo marketplace: lenders supply permissionless stablecoins (USDC/DAI/USDT/FRAX) to earn yield; borrowers pledge **OUSG** (Ondo's tokenized short-term US Treasuries fund) as collateral. The Comptroller and the `contracts/lending/compound/` + `contracts/lending/tokens/cErc20Delegate/` files are **unchanged from Compound's on-chain deployment** — so the Comptroller's events/selectors are byte-for-byte Compound V2. What is *modified* is the cToken: Flux's markets use **`CErc20DelegatorKYC`** (the delegator, file `cErc20ModifiedDelegator.sol`) pointing at **`CTokenModified`** logic, which adds a **KYC allowlist + sanctions gate** on `mint`/`borrow`/`repay`/`transfer`/`seize`. The three things a monitoring engineer must internalize before indexing:

1. **It is the per-block Compound V2 dialect, not the per-timestamp Moonwell dialect.** Interest accrues on `block.number`; the accessors are `borrowRatePerBlock()` / `supplyRatePerBlock()` / `accrualBlockNumber()`. **`AccrueInterest` is the 4-arg form** `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` (topic0 `0x4dec04e7…`) — confirmed live: fUSDC `AccrueInterest` logs carry **128 bytes** (= 4×uint256).

2. **Every fToken is a KYC-gated `CTokenModified`** (not a vanilla `CErc20Delegate`), even the "permissionless" stablecoin markets — all five live markets return `kycRequirementGroup() = 1` and a non-zero `kycRegistry()`. The modified cToken adds two on-token events — `KYCRegistrySet(address,address)` and `KYCRequirementGroupSet(uint256,uint256)` — plus a hardcoded Chainalysis-style `sanctionsList` constant `0x40C57923924B5c5c5455c48D93317139ADDaC8fb`, and reverts `mint`/`borrow`/`repay`/`transfer` for sanctioned or non-KYC'd addresses. The actual allowlist lives in a **separate Ondo `KYCRegistry`** (`0x7ce9…dc70`) whose `KYCAddressesAdded`/`KYCAddressesRemoved` events are the real "who can transact" signal.

3. **Proxies are the Compound delegator pattern, NOT EIP-1967.** The `Unitroller` (Comptroller proxy) and each `CErc20DelegatorKYC` (fToken) store their logic in their own slots and expose it via getters — `comptrollerImplementation()` / `implementation()`. **The EIP-1967 impl slot is empty (`0x0`) on all of them** (verified). Do not read `0x360894…382bbc` to find the logic — call the getter.

---

## 0. Contract families & versions

| Family | Contract(s) | Role | Modified vs Compound? |
|--------|-------------|------|------------------------|
| Risk engine | `Unitroller` (proxy) + `Comptroller` (logic) | Market listing, collateral factors, liquidation params, pause, COMP-distribution plumbing | **Unchanged** (stock Compound V2) |
| Markets | 5× `CErc20DelegatorKYC` (proxy) → per-market `CTokenModified` (logic) | The fTokens (fOUSG, fUSDC, fDAI, fUSDT, fFRAX) | **Modified**: KYC + sanctions gate, KYC events |
| Rates | per-market `JumpRateModelV2` | Interest-rate curve | Unchanged |
| Oracle | `OndoPriceOracleV2` (plain Ownable) | `getUnderlyingPrice(fToken)`; per-fToken oracle-type enum (MANUAL/COMPOUND/CHAINLINK) | **Flux-specific** |
| OUSG feed | `OUSGPriceOracle` (`0x0502c5…6abe`, "OUSG/USD", 18d) | The backing OUSG/USD price feed that the COMPOUND-type path reads for fOUSG | **Flux/Ondo-specific** |
| Lens | `FluxLens` (`0xcA83…acf8`) | Read-only batch view helper (market/account metadata); no state, not in monitoring critical path | Compound Lens variant |
| KYC | Ondo `KYCRegistry` (+ constant `sanctionsList`) | Allowlist that gates OUSG-side activity | **Flux/Ondo-specific** |
| Governance | `GovernorBravoDelegator`→`GovernorBravoDelegate`, `Timelock`, ONDO token | On-chain governance of the market | Compound GovernorBravo (token = ONDO) |

> **fLUSD does not exist on-chain.** The repo's `forge-tests/` exercise an `fLUSD` market, but `Comptroller.getAllMarkets()` returns exactly **5** markets (fOUSG, fUSDC, fDAI, fUSDT, fFRAX) — fLUSD was never listed on mainnet. Do not author an fLUSD monitor.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 fToken / `CTokenModified` (per-market; the workhorse events)

Emitters = the 5 fToken proxies (§3.2). All recomputed locally; `AccrueInterest`/`Mint` additionally confirmed against live fUSDC/fOUSG logs.

| topic0 | Event |
|--------|-------|
| `0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04` | `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` — **4-arg** (128-byte data) |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address minter, uint256 mintAmount, uint256 mintTokens)` |
| `0xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929` | `Redeem(address redeemer, uint256 redeemAmount, uint256 redeemTokens)` |
| `0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80` | `Borrow(address borrower, uint256 borrowAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1` | `RepayBorrow(address payer, address borrower, uint256 repayAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address liquidator, address borrower, uint256 repayAmount, address cTokenCollateral, uint256 seizeTokens)` |
| `0xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5` | `ReservesAdded(address benefactor, uint256 addAmount, uint256 newTotalReserves)` |
| `0x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e` | `ReservesReduced(address admin, uint256 reduceAmount, uint256 newTotalReserves)` |
| `0xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460` | `NewReserveFactor(uint256 oldReserveFactorMantissa, uint256 newReserveFactorMantissa)` |
| `0xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926` | `NewMarketInterestRateModel(address oldIRM, address newIRM)` |
| `0x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d` | `NewComptroller(address oldComptroller, address newComptroller)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` — fToken logic upgrade (delegator) |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` — fToken shares |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` |
| `0x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0` | `Failure(uint256 error, uint256 info, uint256 detail)` — soft-fail; pre-revert legacy path |

**Flux additions on the fToken (KYC):**

| topic0 | Event |
|--------|-------|
| `0x7d25fe3c08dd306579e1d2a5002c9c44f52c27fc3754b43c75ef1e080d454c8a` | `KYCRegistrySet(address oldRegistry, address newRegistry)` — fToken's KYC-registry pointer changed |
| `0xdaffa4de8807a37aaf10d8a67851ece24bdb59211b326eb514393692ddc95832` | `KYCRequirementGroupSet(uint256 oldRequirementGroup, uint256 newRequirementGroup)` — fToken's KYC group changed |

> **`Mint` topic0 `0x4c209b5f…` collides with Uniswap V2's `Mint`** (identical `Mint(address,uint256,uint256)` signature) — disambiguate by emitter. `Transfer`/`Approval` are the universal ERC-20 topic0s. **There is no `NewProtocolSeizeShare`** — `protocolSeizeShareMantissa` is a hardcoded constant `1.75e16` (1.75%), no setter, no event.

### 1.2 Comptroller (behind `Unitroller` — one per market system; stock Compound V2)

| topic0 | Event |
|--------|-------|
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address cToken)` |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address cToken, address account)` |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address cToken, address account)` |
| `0x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9` | `NewCloseFactor(uint256 oldCloseFactorMantissa, uint256 newCloseFactorMantissa)` |
| `0x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5` | `NewCollateralFactor(address cToken, uint256 oldCFMantissa, uint256 newCFMantissa)` |
| `0xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316` | `NewLiquidationIncentive(uint256 oldIncentiveMantissa, uint256 newIncentiveMantissa)` |
| `0xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22` | `NewPriceOracle(address oldPriceOracle, address newPriceOracle)` |
| `0x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e` | `NewPauseGuardian(address oldPauseGuardian, address newPauseGuardian)` |
| `0xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0` | `ActionPaused(string action, bool pauseState)` — global (Transfer/Seize) |
| `0x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0` | `ActionPaused(address cToken, string action, bool pauseState)` — per-market (Mint/Borrow) |
| `0x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6` | `NewBorrowCap(address indexed cToken, uint256 newBorrowCap)` |
| `0xeda98690e518e9a05f8ec6837663e188211b2da8f4906648b323f2c1d4434e29` | `NewBorrowCapGuardian(address oldBorrowCapGuardian, address newBorrowCapGuardian)` |
| `0x2caecd17d02f56fa897705dcc740da2d237c373f70686f4e0d9bd3bf0400ea7a` | `DistributedSupplierComp(address indexed cToken, address indexed supplier, uint256 compDelta, uint256 compSupplyIndex)` |
| `0x1fc3ecc087d8d2d15e23d0032af5a47059c3892d003d8e139fdcb6bb327c99a6` | `DistributedBorrowerComp(address indexed cToken, address indexed borrower, uint256 compDelta, uint256 compBorrowIndex)` |
| `0x20af8e791cc98f74b2d7a391c80980ca8e5aebf3d4060bf581997b6acae2e537` | `CompBorrowSpeedUpdated(address indexed cToken, uint256 newSpeed)` |
| `0xdeafccd0c0b768b2529f7dcbbe58e155d6023059150b7490ed4535cc3744b92d` | `CompSupplySpeedUpdated(address indexed cToken, uint256 newSpeed)` |
| `0x386537fa92edc3319af95f1f904dcf1900021e4f3f4e08169a577a09076e66b3` | `ContributorCompSpeedUpdated(address indexed contributor, uint256 newSpeed)` |
| `0x98b2f82a3a07f223a0be64b3d0f47711c64dccd1feafb94aa28156b38cd9695c` | `CompGranted(address recipient, uint256 amount)` |
| `0x4a5c134e28b537a76546993ea37f3b60d9190476df7356d3842aa40902e20f04` | `CompAccruedAdjusted(address indexed user, uint256 oldCompAccrued, uint256 newCompAccrued)` |
| `0x17fea09d9a7ca41b2f9f9118f18f44848a62e9c70d55dd4385131eb2cf1b7e47` | `CompReceivableUpdated(address indexed user, uint256 oldCompReceivable, uint256 newCompReceivable)` |

> The COMP-distribution events are present in the unchanged Compound code but **Flux does not run a COMP-style emission program** — treat the `*Comp*` events as inert plumbing unless logs prove otherwise. `MarketListed`/`NewCollateralFactor`/`ActionPaused`/`NewPriceOracle` are the governance-action signals that matter.

### 1.3 Unitroller (Comptroller proxy — admin/upgrade events)

| topic0 | Event |
|--------|-------|
| `0xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815` | `NewPendingImplementation(address oldPendingImplementation, address newPendingImplementation)` |
| `0xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a` | `NewImplementation(address oldImplementation, address newImplementation)` |
| `0xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9` | `NewPendingAdmin(address oldPendingAdmin, address newPendingAdmin)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address oldAdmin, address newAdmin)` |

> `NewImplementation` topic0 `0xd604de94…` is **shared** between the Unitroller (Comptroller logic upgrade) and each fToken delegator (fToken logic upgrade) — disambiguate by emitter (Unitroller `0x95af…` vs an fToken `0x…`).

### 1.4 OndoPriceOracleV2 (the live Flux oracle — `0xa42e…37ec`)

| topic0 | Event |
|--------|-------|
| `0xaf36f76b16bdf9c6421a4ee1780b00c7cd8d7da1c8e273fecb1e24aa8ba7d020` | `UnderlyingPriceSet(address indexed fToken, uint256 oldPrice, uint256 newPrice)` — MANUAL-type price push |
| `0xc3d9b856b6901b809e94ccc00044ca25890dbe9b94215f7b02a5cab6c0378028` | `FTokenToCTokenSet(address indexed fToken, address oldCToken, address newCToken)` — COMPOUND-type wiring |
| `0x9813efb04d5475db1451f16b1d5d96f90e291b7b8af445cd80d750aaceaf1238` | `CTokenOracleSet(address oldOracle, address newOracle)` — backing cToken oracle changed |
| `0x3feeba8993d4d4d568b00918fea1a44cf50cf94a574da8e538b12941d7830c51` | `PriceCapSet(address indexed fToken, uint256 oldPriceCap, uint256 newPriceCap)` |
| `0xdab65267e2bc09bc0d106209b37c23d51f081db57b4d5544e55f21dd4acf9f25` | `ChainlinkOracleSet(address indexed fToken, address oldOracle, address newOracle, uint256 maxChainlinkOracleTimeDelay)` |
| `0xcbde673f74752d6d4daf268a2618b15bf093c2b023c4fa68ecd68feccaebdd35` | `FTokenToOracleTypeSet(address indexed fToken, uint8 oracleType)` — `OracleType` enum: 0=UNINITIALIZED, 1=MANUAL, 2=COMPOUND, 3=CHAINLINK |

> `UnderlyingPriceSet`/`CTokenOracleSet`/`FTokenToCTokenSet` exist on both the legacy `OndoPriceOracle` (V1) and `OndoPriceOracleV2` (V1 is a subset). `PriceCapSet`/`ChainlinkOracleSet`/`FTokenToOracleTypeSet` are **V2-only**. The live oracle is **V2** (confirmed: `fTokenToOracleType(fToken)` returns a value).

### 1.5 KYCRegistry (Ondo allowlist — `0x7ce9…dc70`; the real "who can transact" signal)

| topic0 | Event |
|--------|-------|
| `0xb99873e1ed2f53a38c4aa6a4b5815ece23096f3aafae3ab358ebce392185422f` | `KYCAddressesAdded(address indexed sender, uint256 indexed kycRequirementGroup, address[] addresses)` — confirmed live |
| `0xf34702d9d673b0be540927fb1d34ca6b5e6e3e98a6c792434c04990bad1ea578` | `KYCAddressesRemoved(address indexed sender, uint256 indexed kycRequirementGroup, address[] addresses)` |
| `0x4c3c676f8dbec03a58e8ddb1ce738eb949be1cb08834e70904c7919ec2af82cd` | `KYCAddressAddViaSignature(address indexed sender, address indexed user, address indexed signer, uint256 kycRequirementGroup, uint256 deadline)` |
| `0x1820f38925ae4ff56a6f627a24f80116489e716918808f52316b3d87cf3afde5` | `RoleAssignedToKYCGroup(uint256 indexed kycRequirementGroup, bytes32 indexed role)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Selectors verified **present** in live fOUSG impl bytecode (`0x159d…2d0a`) where noted. Interface `uint` canonicalized to `uint256`.

### 2.1 fToken / `CTokenModified` (per-market)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa0712d68` | `mint(uint256 mintAmount)` | Supply underlying. Emits `Mint`+`AccrueInterest`+`Transfer`. **Reverts if `msg.sender` sanctioned.** (verified present) |
| `0xdb006a75` | `redeem(uint256 redeemTokens)` | Burn fTokens for underlying. |
| `0x852a12e3` | `redeemUnderlying(uint256 redeemAmount)` | Redeem exact underlying. |
| `0xc5ebeaec` | `borrow(uint256 borrowAmount)` | Emits `Borrow`. **Reverts unless borrower is KYC'd** (`_getKYCStatus`). (verified present) |
| `0x0e752702` | `repayBorrow(uint256 repayAmount)` | `type(uint).max` repays full. **KYC-gated on payer + borrower.** |
| `0x2608f818` | `repayBorrowBehalf(address borrower, uint256 repayAmount)` | |
| `0xf5e3c462` | `liquidateBorrow(address borrower, uint256 repayAmount, address cTokenCollateral)` | Emits `LiquidateBorrow`. (verified present) |
| `0xb2a02ff1` | `seize(address liquidator, address borrower, uint256 seizeTokens)` | Cross-market seizure; sanctions-checks all three. |
| `0xa9059cbb` | `transfer(address dst, uint256 amount)` | fToken shares. **Sanctions-checks src/dst/spender** (the modified `transferTokens`). |
| `0x23b872dd` | `transferFrom(address src, address dst, uint256 amount)` | |
| `0x095ea7b3` | `approve(address spender, uint256 amount)` | |
| `0xa6afed95` | `accrueInterest()` | Emits 4-arg `AccrueInterest`. |
| `0xbd6d894d` | `exchangeRateCurrent()` | Accrues, returns rate (1e18 scaled). |
| `0x182df0f5` | `exchangeRateStored()` | View. |
| `0x17bfdfbc` | `borrowBalanceCurrent(address)` | Accrues then returns debt. |
| `0x95dd9193` | `borrowBalanceStored(address)` | View. |
| `0x3af9e669` | `balanceOfUnderlying(address)` | State-mutating (accrues). |
| `0xc37f68e2` | `getAccountSnapshot(address)` | `(err, fTokenBalance, borrowBalance, exchangeRateMantissa)` |
| `0x73acee98` | `totalBorrowsCurrent()` | |
| `0x3b1d21a2` | `getCash()` | Underlying held by the fToken. |
| `0xf8f9da28` | `borrowRatePerBlock()` | **Per-BLOCK** borrow rate mantissa (NOT per-timestamp). |
| `0xae9d70b0` | `supplyRatePerBlock()` | **Per-BLOCK** supply rate mantissa. |
| `0x6c540baf` | `accrualBlockNumber()` | **Block number** of last accrual (NOT a timestamp). |
| `0x5fe3b567` | `comptroller()` | Returns the Unitroller `0x95af…`. |
| `0xf3fdb15a` | `interestRateModel()` | Per-market JumpRateModelV2. |
| `0x6f307dc3` | `underlying()` | Underlying ERC-20. |
| `0x173b9904` | `reserveFactorMantissa()` | |
| `0x47bd3718` / `0x8f840ddd` / `0xaa5af0fd` | `totalBorrows()` / `totalReserves()` / `borrowIndex()` | |
| `0x5c60da1b` | `implementation()` | **Read this for the fToken logic contract** — NOT the EIP-1967 slot (§7). |
| `0xf851a440` | `admin()` | Returns the Timelock `0x2c58…8d9c`. |
| `0xfe9c44ae` | `isCToken()` | Returns `true` (marker). |
| **`0x4b155b97`** | `kycRegistry()` | **Flux**: the KYC registry this fToken queries. (verified present) |
| **`0x510b751b`** | `kycRequirementGroup()` | **Flux**: the KYC group id (= `1` on all live markets). |
| **`0xec571c6a`** | `sanctionsList()` | **Flux**: returns the constant `0x40C5…c8fb`. (verified present) |
| **`0xc13e9ada`** | `getKYCStatus(uint256 kycRequirementGroup, address account)` | **Flux**: KYC check passthrough. (verified present) |
| **`0x600d2dbc`** | `setKYCRegistry(address)` | **Flux, admin-only.** Emits `KYCRegistrySet`. (verified present) |
| **`0x24f09e9c`** | `setKYCRequirementGroup(uint256)` | **Flux, admin-only.** Emits `KYCRequirementGroupSet`. (verified present) |
| `0x1be19560` | `sweepToken(address)` | Recover non-underlying tokens (admin). |
| `0x555bcc40` | `_setImplementation(address implementation_, bool allowResign, bytes becomeImplementationData)` | fToken logic upgrade (delegator). Emits `NewImplementation`. |
| `0x4576b5db` | `_setComptroller(address)` | Emits `NewComptroller`. |
| `0xfca7820b` | `_setReserveFactor(uint256)` | Emits `NewReserveFactor`. |
| `0xf2b3abbd` | `_setInterestRateModel(address)` | Emits `NewMarketInterestRateModel`. |
| `0xb71d1a0c` / `0xe9c714f2` | `_setPendingAdmin(address)` / `_acceptAdmin()` | |
| `0x601a0bf1` / `0x3e941010` | `_reduceReserves(uint256)` / `_addReserves(uint256)` | |

### 2.2 Comptroller (behind Unitroller; stock Compound V2)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc2998238` | `enterMarkets(address[] cTokens)` | Use markets as collateral. Emits `MarketEntered`. |
| `0xede4edd0` | `exitMarket(address cToken)` | Emits `MarketExited`. |
| `0x5ec88c79` | `getAccountLiquidity(address)` | `(err, liquidity, shortfall)`. shortfall>0 ⇒ liquidatable. |
| `0x4e79238f` | `getHypotheticalAccountLiquidity(address,address,uint256,uint256)` | What-if check. |
| `0xabfceffc` | `getAssetsIn(address)` | Markets the account entered. |
| `0x929fe9a1` | `checkMembership(address account, address cToken)` | |
| `0xb0772d0b` | `getAllMarkets()` | All listed fTokens — **returns 5** (re-read rather than hardcoding). |
| `0x8e8f294b` | `markets(address cToken)` | `(bool isListed, uint collateralFactorMantissa, bool isComped)` |
| `0x7dc0d1d0` | `oracle()` | The OndoPriceOracleV2 address. |
| `0xe8755446` | `closeFactorMantissa()` | = `0.5e18` (live). |
| `0x4ada90af` | `liquidationIncentiveMantissa()` | = `1.05e18` (live). |
| `0x4a584432` | `borrowCaps(address)` | Per-market borrow cap. |
| `0xc488847b` | `liquidateCalculateSeizeTokens(address,address,uint256)` | |
| `0x4ef4c3e1` / `0xda3d454c` | `mintAllowed(address,address,uint256)` / `borrowAllowed(address,address,uint256)` | Policy hooks. |
| `0xbdcdc258` / `0xd02f7351` | `transferAllowed(...)` / `seizeAllowed(...)` | Policy hooks. |
| `0xa76b3fda` | `_supportMarket(address)` | Admin. Emits `MarketListed`. |
| `0xe4028eee` | `_setCollateralFactor(address,uint256)` | Admin. Emits `NewCollateralFactor`. |
| `0x317b0b77` / `0x4fd42e17` | `_setCloseFactor(uint256)` / `_setLiquidationIncentive(uint256)` | |
| `0x55ee1fe1` | `_setPriceOracle(address)` | Emits `NewPriceOracle`. |
| `0x5f5af1aa` | `_setPauseGuardian(address)` | Emits `NewPauseGuardian`. |
| `0x3bcf7ec1` / `0x18c882a5` | `_setMintPaused(address,bool)` / `_setBorrowPaused(address,bool)` | Emit `ActionPaused(address,string,bool)`. |
| `0x8ebf6364` / `0x2d70db78` | `_setTransferPaused(bool)` / `_setSeizePaused(bool)` | Emit `ActionPaused(string,bool)`. |
| `0x607ef6c1` / `0x391957d7` | `_setMarketBorrowCaps(address[],uint256[])` / `_setBorrowCapGuardian(address)` | |
| `0xe9af0292` | `claimComp(address)` | Inert unless emissions ever enabled. |
| `0xbb82aa5e` | `comptrollerImplementation()` | **Unitroller: read this for live Comptroller logic.** |
| `0xdcfbc0c7` | `pendingComptrollerImplementation()` | |
| `0xe992a041` / `0xc1e80334` | `_setPendingImplementation(address)` / `_acceptImplementation()` | Unitroller upgrade. |

### 2.3 OndoPriceOracleV2

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfc57d4df` | `getUnderlyingPrice(address fToken)` | Comptroller's pricing entry point. Price mantissa scaled to `36 − underlyingDecimals`. |
| `0xe6e0c01e` | `fTokenToOracleType(address)` | Per-fToken oracle source (enum) — **the V2 discriminator**. |
| `0x778a97df` | `fTokenToUnderlyingPriceCap(address)` | Per-fToken price cap. |
| `0xb8428ee7` | `fTokenToChainlinkOracle(address)` | Chainlink feed assoc (CHAINLINK type). |
| `0x00e4768b` | `setPrice(address fToken, uint256 price)` | MANUAL-type push (owner). Emits `UnderlyingPriceSet`. |
| `0x931f9009` | `setFTokenToOracleType(address fToken, uint8 oracleType)` | Owner. Emits `FTokenToOracleTypeSet`. |
| `0xec802777` | `setPriceCap(address fToken, uint256 value)` | Owner. Emits `PriceCapSet`. |
| `0xa2b23dee` | `setFTokenToChainlinkOracle(address fToken, address newChainlinkOracle, uint256 maxChainlinkOracleTimeDelay)` | Owner. Emits `ChainlinkOracleSet`. |
| `0x3c07ad26` | `setFTokenToCToken(address fToken, address cToken)` | Owner. Emits `FTokenToCTokenSet`. |
| `0x7adbf973` | `setOracle(address newOracle)` | Sets the backing cToken oracle. Emits `CTokenOracleSet`. |

### 2.4 KYCRegistry

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc13e9ada` | `getKYCStatus(uint256 kycRequirementGroup, address account)` → `bool` | Whether `account` is KYC'd for that group. |
| `0x359a6cad` | `addKYCAddresses(uint256, address[])` | Allowlist add (role-gated). Emits `KYCAddressesAdded`. |
| `0x8aeeff95` | `removeKYCAddresses(uint256, address[])` | Allowlist remove. Emits `KYCAddressesRemoved`. |

> The on-chain registry is the canonical Ondo `KYCRegistry` (not in `flux-finance/contracts`); the `add/removeKYCAddresses` selectors above are recomputed locally as `keccak256(sig)[0:4]`. Detect registry changes by the **event topics** in §1.5, which are confirmed live.

---

## 3. Addresses — Ethereum mainnet (chain ID 1)  *[the ONLY deployment]*

All verified via `eth_getCode` (non-empty) / `eth_call` on `https://ethereum-rpc.publicnode.com` on 2026-06-08. Market list is `Comptroller.getAllMarkets()` (= 5). Each fToken's `comptroller()` → the Unitroller; `Unitroller.oracle()` → OndoPriceOracleV2; `Unitroller.admin()` → Timelock.

### 3.1 Core system

| Role | Address | One-liner |
|------|---------|-----------|
| **UNITROLLER** (Comptroller proxy) | `0x95af143a021df745bc78e845b54591c53a8b3a51` | The risk engine. `comptrollerImplementation()`→ COMPTROLLER; `oracle()`→ ORACLE_V2; `getAllMarkets()`=5; `admin()`→ TIMELOCK. Point all market-policy monitors here. |
| COMPTROLLER (logic) | `0xdc7b90593cafe7a919d22b903fed21bf27da9719` | Comptroller logic behind the Unitroller. |
| **ORACLE** (OndoPriceOracleV2) | `0xa42e17f72aefc6ae585a08e6058a38ec036d37ec` | Live Flux price oracle (V2). Plain Ownable, not a proxy. `Unitroller.oracle()` returns this (confirmed live). |
| OUSG_ORACLE (OUSG/USD feed) | `0x0502c5ae08E7CD64fe1AEDA7D6e229413eCC6abe` | The backing OUSG/USD price feed (18d, `description()`="OUSG/USD") read by the COMPOUND-type path for fOUSG. Listed on docs.fluxfinance.com/addresses as "OUSG Oracle". |
| LENS (FluxLens) | `0xcA83471CE9B0E7E6f628FA2A95Ae97198780acf8` | Read-only batch view helper (market/account metadata). Off the monitoring critical path. |
| **KYC_REGISTRY** (Ondo) | `0x7ce91291846502d50d635163135b2d40a602dc70` | Allowlist gating OUSG-side activity. `KYCAddressesAdded`/`KYCAddressesRemoved` source. |
| SANCTIONS_LIST (constant in CTokenModified) | `0x40C57923924B5c5c5455c48D93317139ADDaC8fb` | Chainalysis-style sanctions oracle; hardcoded, queried on mint/borrow/repay/transfer/seize. |
| JUMP_RATE_MODEL_A (shared by 4 markets) | `0xfd3ffbb58bc27406bbe51918be3c6b2e48380570` | JumpRateModelV2 — live IRM of **fOUSG, fUSDC, fDAI, fUSDT** (confirmed each market's `interestRateModel()`). |
| JUMP_RATE_MODEL_B (fFRAX) | `0x15adf6047845348317771288736514778c2076bf` | A **second** JumpRateModelV2 — live IRM of **fFRAX** only. Always re-read each market's `interestRateModel()`. |
| PAUSE_GUARDIAN | `0x118919e891d0205a7492650ad32e727617fa9452` | Comptroller pause guardian (Safe multisig, ~171-byte proxy). |

### 3.2 fToken markets (5) — `CErc20DelegatorKYC` proxies, **8 decimals**, symbol = `f`+underlying

| fToken | Address | Logic impl | Underlying | Underlying addr |
|--------|---------|-----------|-----------|-----------------|
| **fOUSG** | `0x1dD7950c266fB1be96180a8FDb0591F70200E018` | `0x159d359b55a6d0cbe9b306862d13515fa1992d0a` | OUSG (18d) | `0x1B19C19393e2d034D8Ff31ff34c81252FCBbee92` |
| **fUSDC** | `0x465a5a630482f3abD6d3b84B39B29b07214d19e5` | `0xb521dcf5b12e878811e079c2159ec56d5edafbc5` | USDC (6d) | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| **fDAI** | `0xe2bA8693cE7474900A045757fe0efCa900F6530b` | `0x690ef7cd8af50179fbbd09abc4017e59c2ae7d82` | DAI (18d) | `0x6B175474E89094C44Da98b954EedeAC495271d0F` |
| **fUSDT** | `0x81994b9607e06ab3d5cF3AffF9a67374f05F27d7` | `0x48a56c40ec7458252b4fdcd7772463278bfbe6bf` | USDT (6d) | `0xdAC17F958D2ee523a2206206994597C13D831ec7` |
| **fFRAX** | `0x1C9A2d6b33B4826757273D47ebEe0e2DDDcD978B` | `0x89ca67eccc2f4046bba7d12a688696637bec17f6` | FRAX (18d) | `0x853d955aCEf822Db058eb8505911ED77F175b99e` |

> Each fToken delegator points at its **own** logic deploy (the five impls above all differ) — they are separately-deployed `CErc20DelegatorKYC` instances, not CREATE2 clones, so addresses cannot be derived. Enumerate via `getAllMarkets()`. fOUSG collateral factor = `0.92e18`; all 5 markets `isListed=true` and `kycRequirementGroup()=1`.

### 3.3 Governance

| Role | Address | One-liner |
|------|---------|-----------|
| **TIMELOCK** | `0x2c5898da4df1d45eab2b7b192a361c3b9eb18d9c` | `admin` of the Unitroller + every fToken; `delay()` = 86400s (1 day). Admin-action monitoring watches this. Its `admin()` → GOVERNOR_BRAVO. |
| GOVERNOR_BRAVO (delegator) | `0x336505ec1bcc1a020eede459f57581725d23465a` | `GovernorBravoDelegator` → impl `0x8886…9c8e`; `admin()` → TIMELOCK; voting token (`comp()`) = ONDO. |
| GOVERNOR_BRAVO (logic) | `0x8886344a1b9b840bed590f2ef7379dd37e169c8e` | GovernorBravoDelegate logic. |
| ONDO (governance/voting token) | `0xfaba6f8e4a5e8ab82f62fe7c39859fa577269be3` | `symbol()="ONDO"`, `name()="Ondo"`. The vote token wired into GovernorBravo. |

> The **ONDO token at `0xfaba…9be3`** is the governance token used by Flux's GovernorBravo (`comp()` getter returns it). It is the canonical Ondo Finance ONDO ERC-20.

---

## 4. Cross-chain summary

| Chain | ID | Flux deployed? | Unitroller | Markets |
|-------|----|---------------|-----------|---------|
| **Ethereum** | 1 | ✅ (the only deployment) | `0x95af143a021df745bc78e845b54591c53a8b3a51` | 5 (fOUSG, fUSDC, fDAI, fUSDT, fFRAX) |
| Base | 8453 | ❌ not deployed | — | 0 |
| BNB Smart Chain | 56 | ❌ not deployed | — | 0 |
| Avalanche C-Chain | 43114 | ❌ not deployed | — | 0 |
| Arbitrum One | 42161 | ❌ not deployed | — | 0 |
| Optimism | 10 | ❌ not deployed | — | 0 |
| Polygon PoS | 137 | ❌ not deployed | — | 0 |

---

## 5. Chains with NO Flux deployment (recorded findings, verified)

`eth_getCode` for the Unitroller `0x95af…`, fUSDC `0x465a…`, fOUSG `0x1dD7…`, OracleV2 `0xa42e…`, KYC_REGISTRY `0x7ce9…`, and ONDO `0xfaba…` returns **empty (`0x`) on Base, BNB, Avalanche, Arbitrum, Optimism, and Polygon PoS** (checked 2026-06-08). **Flux Finance is Ethereum-mainnet-only** — consistent with the protocol design (OUSG collateral and the KYC/Treasury-repo model live on Ethereum). Do not author Flux monitors for any non-Ethereum chain.

> **Decoy / address-collision note:** on **BNB Smart Chain** the *literal* fOUSG address `0x1dD7950c266fB1be96180a8FDb0591F70200E018` has non-empty code (**1,492 bytes**; `eth_getCode` returns a 2,986-char hex string) — but it is an **unrelated contract** (no `symbol()`, no `comptroller()`; both revert), i.e. a coincidental same-address deploy, NOT a Flux fToken. Always key on `(chainId=1, address)` and verify `comptroller()` returns `0x95af…` before treating any address as a Flux market.

---

## 6. Decimals & math (Compound V2 conventions)

- fTokens are **8-decimal**; underlyings keep their own decimals (USDC/USDT = 6, DAI/FRAX/OUSG = 18).
- Indices `borrowIndex` and the exchange rate are 1e18-mantissa; `exchangeRateStored × fTokenBalance / 1e18` = underlying (with the underlying-decimal adjustment baked into the rate).
- `getAccountLiquidity` returns `(err, liquidity, shortfall)` in 1e18-USD terms; `shortfall > 0` ⇒ liquidatable.
- Oracle `getUnderlyingPrice(fToken)` returns a mantissa scaled to `36 − underlyingDecimals` (Compound convention) — e.g. fUSDC price ≈ `1e30` for a $1 6-decimal asset.
- `closeFactorMantissa = 0.5e18` (≤50% of debt repayable per liquidation); `liquidationIncentiveMantissa = 1.05e18` (5% liquidator bonus); `protocolSeizeShareMantissa = 1.75e16` (1.75%, constant).

---

## 7. Proxies (Compound delegator pattern — NOT EIP-1967)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Unitroller** (`0x95af…`) | Compound Unitroller delegator | EIP-1967 impl slot = **`0x0`** (verified); read logic via `comptrollerImplementation()` (= `0xdc7b…9719`) | Timelock via `_setPendingImplementation`+`_acceptImplementation`; emits `NewPendingImplementation`/`NewImplementation` |
| **fTokens** (5× `CErc20DelegatorKYC`) | Compound CErc20Delegator | EIP-1967 impl slot = **`0x0`** (verified on fOUSG, fUSDC); read logic via `implementation()` (`0x5c60da1b`) | Timelock via `_setImplementation(address,bool,bytes)`; emits `NewImplementation` |
| **OndoPriceOracleV2** (`0xa42e…`) | **Not a proxy** — plain Ownable logic | EIP-1967 impl slot = `0x0`; no delegatecall | Replaced wholesale via `Comptroller._setPriceOracle` (emits `NewPriceOracle`); per-feed via owner setters |
| **KYCRegistry** (`0x7ce9…`) | EIP-1967 impl slot = `0x0` (read live) | Confirmed not an EIP-1967 transparent/UUPS proxy by empty slot | Ondo-controlled (role-gated `add/removeKYCAddresses`) |
| **GovernorBravo** (`0x3365…`) | Compound GovernorBravoDelegator | `implementation()` → `0x8886…9c8e`; EIP-1967 slot `0x0` | Timelock (`admin()`) |

EIP-1967 implementation slot probed: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` — **empty on every Flux contract.** The `Upgraded(address)` EIP-1967 topic (`0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`) is **NOT used** here; fToken/Comptroller logic upgrades fire the Compound `NewImplementation(address,address)` topic `0xd604de94…` instead.

---

## 8. Detection invariants & gotchas

1. **Ethereum only.** Flux has exactly one deployment (chain 1). Every other requested chain returns empty `eth_getCode` (§5). Treat any "Flux on L2" claim as false; the BNB fOUSG-address collision (§5) is an unrelated contract.
2. **It's the per-BLOCK Compound V2 dialect.** Use `borrowRatePerBlock`/`supplyRatePerBlock`/`accrualBlockNumber` — there is **no** `…PerTimestamp`/`accrualBlockTimestamp` (that's the Moonwell dialect). `AccrueInterest` is the **4-arg** form (128-byte data) — confirmed live.
3. **Every fToken is KYC-gated `CTokenModified`** (even the stablecoin markets: all `kycRequirementGroup()=1`). `mint`/`borrow`/`repay`/`transfer`/`seize` revert for sanctioned or non-KYC'd addresses. A *failed* user action is invisible on-chain; the positive signal that someone became transactable is the **KYCRegistry** `KYCAddressesAdded`/`KYCAddressesRemoved` (§1.5), not anything on the fToken.
4. **`Mint` topic0 `0x4c209b5f…` collides with Uniswap V2's `Mint`** — disambiguate by emitter (one of the five fToken addresses). `Transfer`/`Approval` are universal ERC-20.
5. **`NewImplementation` topic0 `0xd604de94…` is shared** by the Unitroller (Comptroller upgrade) and every fToken delegator (fToken-logic upgrade). Disambiguate by emitter: Unitroller `0x95af…` vs an fToken.
6. **Proxies are NOT EIP-1967.** Reading slot `0x360894…382bbc` returns `0x0` everywhere — call `comptrollerImplementation()` / `implementation()` to find logic. Hardcoding the EIP-1967 slot here yields "no proxy", which is wrong.
7. **Admin of everything = the Timelock `0x2c58…8d9c`** (1-day delay), itself governed by GovernorBravo `0x3365…` voting with the **ONDO** token. Admin-action monitoring watches the Timelock's queue/execute and the Comptroller/fToken `New*`/`MarketListed`/`ActionPaused` events.
8. **fLUSD is test-only — not deployed.** `getAllMarkets()` = 5 (no fLUSD). Don't index it.
9. **Oracle is V2 with a per-fToken source enum.** OUSG is priced via the COMPOUND-type path (oracle-type `2`, confirmed live: `fTokenToOracleType(fOUSG)=2`), which reads a backing OUSG/USD feed — the **OUSG_ORACLE `0x0502c5…6abe`** (18d, `description()`="OUSG/USD"); stablecoins use MANUAL (`fTokenToOracleType(fUSDC)=1`, confirmed). Watch `FTokenToOracleTypeSet`/`UnderlyingPriceSet`/`ChainlinkOracleSet`/`PriceCapSet` on `0xa42e…` as oracle-risk signals, plus the OUSG feed `0x0502c5…` itself for OUSG repricing. The oracle is replaceable wholesale via `Comptroller._setPriceOracle` (`NewPriceOracle`).
10. **COMP-distribution events are inert.** The Comptroller carries Compound's `DistributedSupplierComp`/`…Borrower…`/`Comp*SpeedUpdated` events but Flux runs no COMP emission — don't treat them as a rewards stream unless logs prove otherwise. There is no separate rewards distributor contract.
11. **`protocolSeizeShareMantissa` is a constant (1.75%), no setter/event** — unlike later Compound forks, do not scan for `NewProtocolSeizeShare`.
12. **Attribute by the event's actor field, not `tx.from`.** `RepayBorrow` carries both `payer` and `borrower`; `LiquidateBorrow` carries `liquidator` and `borrower`. Liquidations/repays can be relayed.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- fToken / CTokenModified
TOPIC_ACCRUE_INTEREST        = '\x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04'
TOPIC_MINT                   = '\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'
TOPIC_REDEEM                 = '\xe5b754fb1abb7f01b499791d0b820ae3b6af3424ac1c59768edb53f4ec31a929'
TOPIC_BORROW                 = '\x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'
TOPIC_REPAY_BORROW           = '\x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1'
TOPIC_LIQUIDATE_BORROW       = '\x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
TOPIC_RESERVES_ADDED         = '\xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5'
TOPIC_RESERVES_REDUCED       = '\x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e'
TOPIC_NEW_RESERVE_FACTOR     = '\xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460'
TOPIC_NEW_MARKET_IRM         = '\xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926'
TOPIC_NEW_COMPTROLLER        = '\x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d'
TOPIC_NEW_IMPLEMENTATION     = '\xd604de94d45953f9138079ec1b82d533cb2160c906d1076d1f7ed54befbca97a'
TOPIC_TRANSFER               = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_APPROVAL               = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_FAILURE                = '\x45b96fe442630264581b197e84bbada861235052c5a1aadfff9ea4e40a969aa0'
-- KYC (on fToken)
TOPIC_KYC_REGISTRY_SET       = '\x7d25fe3c08dd306579e1d2a5002c9c44f52c27fc3754b43c75ef1e080d454c8a'
TOPIC_KYC_REQ_GROUP_SET      = '\xdaffa4de8807a37aaf10d8a67851ece24bdb59211b326eb514393692ddc95832'
-- Comptroller
TOPIC_MARKET_LISTED          = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_MARKET_ENTERED         = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'
TOPIC_MARKET_EXITED          = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_NEW_CLOSE_FACTOR       = '\x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9'
TOPIC_NEW_COLLATERAL_FACTOR  = '\x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5'
TOPIC_NEW_LIQ_INCENTIVE      = '\xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316'
TOPIC_NEW_PRICE_ORACLE       = '\xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22'
TOPIC_NEW_PAUSE_GUARDIAN     = '\x0613b6ee6a04f0d09f390e4d9318894b9f6ac7fd83897cd8d18896ba579c401e'
TOPIC_ACTION_PAUSED_GLOBAL   = '\xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0'
TOPIC_ACTION_PAUSED_MARKET   = '\x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0'
TOPIC_NEW_BORROW_CAP         = '\x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6'
TOPIC_NEW_BORROW_CAP_GUARD   = '\xeda98690e518e9a05f8ec6837663e188211b2da8f4906648b323f2c1d4434e29'
-- Unitroller
TOPIC_NEW_PENDING_IMPL       = '\xe945ccee5d701fc83f9b8aa8ca94ea4219ec1fcbd4f4cab4f0ea57c5c3e1d815'
TOPIC_NEW_ADMIN              = '\xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc'
TOPIC_NEW_PENDING_ADMIN      = '\xca4f2f25d0898edd99413412fb94012f9e54ec8142f9b093e7720646a95b16a9'
-- OndoPriceOracleV2
TOPIC_UNDERLYING_PRICE_SET   = '\xaf36f76b16bdf9c6421a4ee1780b00c7cd8d7da1c8e273fecb1e24aa8ba7d020'
TOPIC_FTOKEN_TO_CTOKEN_SET   = '\xc3d9b856b6901b809e94ccc00044ca25890dbe9b94215f7b02a5cab6c0378028'
TOPIC_CTOKEN_ORACLE_SET      = '\x9813efb04d5475db1451f16b1d5d96f90e291b7b8af445cd80d750aaceaf1238'
TOPIC_PRICE_CAP_SET          = '\x3feeba8993d4d4d568b00918fea1a44cf50cf94a574da8e538b12941d7830c51'
TOPIC_CHAINLINK_ORACLE_SET   = '\xdab65267e2bc09bc0d106209b37c23d51f081db57b4d5544e55f21dd4acf9f25'
TOPIC_FTOKEN_ORACLE_TYPE_SET = '\xcbde673f74752d6d4daf268a2618b15bf093c2b023c4fa68ecd68feccaebdd35'
-- KYCRegistry
TOPIC_KYC_ADDRESSES_ADDED    = '\xb99873e1ed2f53a38c4aa6a4b5815ece23096f3aafae3ab358ebce392185422f'
TOPIC_KYC_ADDRESSES_REMOVED  = '\xf34702d9d673b0be540927fb1d34ca6b5e6e3e98a6c792434c04990bad1ea578'
TOPIC_KYC_ADD_VIA_SIGNATURE  = '\x4c3c676f8dbec03a58e8ddb1ce738eb949be1cb08834e70904c7919ec2af82cd'
TOPIC_ROLE_ASSIGNED_TO_GROUP = '\x1820f38925ae4ff56a6f627a24f80116489e716918808f52316b3d87cf3afde5'

-- ===== Selectors (chain-agnostic) =====
SEL_MINT                     = '\xa0712d68'
SEL_REDEEM                   = '\xdb006a75'
SEL_REDEEM_UNDERLYING        = '\x852a12e3'
SEL_BORROW                   = '\xc5ebeaec'
SEL_REPAY_BORROW             = '\x0e752702'
SEL_REPAY_BORROW_BEHALF      = '\x2608f818'
SEL_LIQUIDATE_BORROW         = '\xf5e3c462'
SEL_SEIZE                    = '\xb2a02ff1'
SEL_ACCRUE_INTEREST          = '\xa6afed95'
SEL_BORROW_RATE_PER_BLOCK    = '\xf8f9da28'
SEL_SUPPLY_RATE_PER_BLOCK    = '\xae9d70b0'
SEL_ACCRUAL_BLOCK_NUMBER     = '\x6c540baf'
SEL_KYC_REGISTRY             = '\x4b155b97'
SEL_KYC_REQUIREMENT_GROUP    = '\x510b751b'
SEL_SANCTIONS_LIST           = '\xec571c6a'
SEL_GET_KYC_STATUS           = '\xc13e9ada'
SEL_SET_KYC_REGISTRY         = '\x600d2dbc'
SEL_SET_KYC_REQ_GROUP        = '\x24f09e9c'
SEL_ADD_KYC_ADDRESSES        = '\x359a6cad'
SEL_REMOVE_KYC_ADDRESSES     = '\x8aeeff95'
SEL_SET_IMPLEMENTATION       = '\x555bcc40'
SEL_ENTER_MARKETS            = '\xc2998238'
SEL_EXIT_MARKET              = '\xede4edd0'
SEL_GET_ACCOUNT_LIQUIDITY    = '\x5ec88c79'
SEL_GET_ALL_MARKETS          = '\xb0772d0b'
SEL_SUPPORT_MARKET           = '\xa76b3fda'
SEL_SET_COLLATERAL_FACTOR    = '\xe4028eee'
SEL_SET_PRICE_ORACLE         = '\x55ee1fe1'
SEL_SET_MINT_PAUSED          = '\x3bcf7ec1'
SEL_SET_BORROW_PAUSED        = '\x18c882a5'
SEL_COMPTROLLER_IMPL         = '\xbb82aa5e'
SEL_ORACLE_GET_UND_PRICE     = '\xfc57d4df'
SEL_ORACLE_SET_PRICE         = '\x00e4768b'
SEL_ORACLE_SET_TYPE          = '\x931f9009'

-- ===== Addresses (network-specific; Ethereum chainId 1) =====
ETH_UNITROLLER               = '\x95af143a021df745bc78e845b54591c53a8b3a51'
ETH_COMPTROLLER_IMPL         = '\xdc7b90593cafe7a919d22b903fed21bf27da9719'
ETH_ORACLE_V2                = '\xa42e17f72aefc6ae585a08e6058a38ec036d37ec'
ETH_OUSG_ORACLE              = '\x0502c5ae08e7cd64fe1aeda7d6e229413ecc6abe'
ETH_LENS                     = '\xca83471ce9b0e7e6f628fa2a95ae97198780acf8'
ETH_KYC_REGISTRY             = '\x7ce91291846502d50d635163135b2d40a602dc70'
ETH_SANCTIONS_LIST           = '\x40c57923924b5c5c5455c48d93317139addac8fb'
ETH_JUMP_RATE_MODEL_A        = '\xfd3ffbb58bc27406bbe51918be3c6b2e48380570'
ETH_JUMP_RATE_MODEL_B        = '\x15adf6047845348317771288736514778c2076bf'
ETH_PAUSE_GUARDIAN           = '\x118919e891d0205a7492650ad32e727617fa9452'
ETH_FOUSG                    = '\x1dd7950c266fb1be96180a8fdb0591f70200e018'
ETH_FUSDC                    = '\x465a5a630482f3abd6d3b84b39b29b07214d19e5'
ETH_FDAI                     = '\xe2ba8693ce7474900a045757fe0efca900f6530b'
ETH_FUSDT                    = '\x81994b9607e06ab3d5cf3afff9a67374f05f27d7'
ETH_FFRAX                    = '\x1c9a2d6b33b4826757273d47ebee0e2dddcd978b'
ETH_OUSG                     = '\x1b19c19393e2d034d8ff31ff34c81252fcbbee92'
ETH_TIMELOCK                 = '\x2c5898da4df1d45eab2b7b192a361c3b9eb18d9c'
ETH_GOVERNOR_BRAVO           = '\x336505ec1bcc1a020eede459f57581725d23465a'
ETH_GOVERNOR_BRAVO_IMPL      = '\x8886344a1b9b840bed590f2ef7379dd37e169c8e'
ETH_ONDO_TOKEN               = '\xfaba6f8e4a5e8ab82f62fe7c39859fa577269be3'
```

---

## 10. Verification & sources

- **Canonical source:** `flux-finance/contracts` (GitHub) — `contracts/lending/`. Modified cToken: `contracts/lending/tokens/cToken/{CTokenModified.sol,CTokenInterfacesModified.sol}` + the delegator `contracts/lending/tokens/cErc20ModifiedDelegator.sol` (`CErc20DelegatorKYC`). Oracle: `contracts/lending/{OndoPriceOracleV2.sol,IOndoPriceOracleV2.sol}` (V1 in `OndoPriceOracle.sol`/`IOndoPriceOracle.sol`). Comptroller/Unitroller/governance unchanged in `contracts/lending/compound/`. KYC event ABI cross-checked against `forge-tests/helpers/{TestKYCRegistryEvents.sol,IKYCRegistry.sol}`.
- **Topics/selectors:** every value recomputed locally as `keccak256(canonical signature)` (param names stripped, `uint`→`uint256`). `AccrueInterest` (4-arg, 128-byte data) and `Mint` (96-byte data, topic0 `0x4c209b5f…`) confirmed against live `eth_getLogs` on fUSDC (`0x465a…`) and fOUSG (`0x1dD7…`). `KYCAddressesAdded` (`0xb99873e1…`) confirmed against live logs on the KYCRegistry (`0x7ce9…`). fToken selectors `mint`/`borrow`/`liquidateBorrow`/`kycRegistry`/`getKYCStatus`/`sanctionsList`/`setKYCRegistry`/`setKYCRequirementGroup` confirmed present in the live fOUSG impl bytecode (`0x159d…2d0a`).
- **Addresses:** discovered from `Comptroller.getAllMarkets()` (5 markets) and each fToken's `comptroller()`/`underlying()`/`implementation()`/`symbol()`/`interestRateModel()` read live; Unitroller `comptrollerImplementation()`/`oracle()`/`admin()` read live; Timelock `admin()`/`delay()` and GovernorBravo `implementation()`/`comp()`(=ONDO) read live. All existence-checked via `eth_getCode` on `ethereum-rpc.publicnode.com` (2026-06-08).
- **Single-chain claim:** `eth_getCode` for the Unitroller, fUSDC, fOUSG, OracleV2, KYCRegistry, and ONDO returns `0x` on Base / BNB / Avalanche / Arbitrum / Optimism / Polygon (all six target chains). The lone non-empty hit — the fOUSG *address* on BNB — is an unrelated contract (`symbol()`/`comptroller()` both revert), recorded as an address collision, not a Flux deployment.
- **Proxy classification:** EIP-1967 impl slot `0x360894…382bbc` read live = `0x0` on Unitroller, fOUSG, fUSDC, OracleV2, KYCRegistry → confirms the Compound delegator pattern (logic via getters), not EIP-1967.
- **Explorers:** Etherscan labels fOUSG (`0x1dD7…`) as "Flux Finance: fOUSG Token" / `CErc20DelegatorKYC`; fUSDC `0x465a…`, fUSDT `0x8199…`, fDAI `0xe2bA…`. Protocol docs: docs.ondo.finance/protocols/flux; app: fluxfinance.com; governance: forum.fluxfinance.com (FIP-07 OUSG oracle upgrade).
- **Official address registry:** docs.fluxfinance.com/addresses lists the 5 fTokens, Comptroller `0x95Af…`, Timelock `0x2c58…`, Governance `0x3365…`, plus a **Lens** `0xcA83…acf8` and an **OUSG Oracle** `0x0502c5…6abe` (both folded into §3.1 here; both existence-checked via `eth_getCode`). The page does **not** list fLUSD (consistent with `getAllMarkets()`=5).
