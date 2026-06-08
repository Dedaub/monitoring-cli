# Venus Isolated Pools — Topics, Selectors, Addresses (Ethereum, Arbitrum, Optimism, Base, BNB; absent on Avalanche, Polygon)

**Status:** verified against live RPC on all 7 requested chains on 2026-06-08, and the canonical `VenusProtocol/isolated-pools` repo (Solidity sources + `deployments/<network>_addresses.json`). Every topic0/selector recomputed locally as `keccak256(signature)`; every anchor address existence-checked via `eth_getCode`; every proxy/beacon resolved live from storage + `implementation()`.
**Scope:** the **Venus Isolated Pools** codebase (`VenusProtocol/isolated-pools`) — `PoolRegistry` (the registry/factory), per-pool `Comptroller` (BeaconProxy), the isolated `VToken` (BeaconProxy), `RewardsDistributor` (transparent proxy), and the shared per-chain `ComptrollerBeacon` + `VTokenBeacon`. This codebase powers **every** Venus pool on Ethereum(1), Arbitrum(42161), Optimism(10), Base(8453), **and all NON-core (isolated) pools on BNB(56)**. It is **NOT** deployed on Avalanche(43114) or Polygon(137) — recorded in §6 with `eth_getCode = 0x` evidence. Topics + selectors are chain-agnostic; addresses are network-specific. (Venus **Core Pool** on BNB — the original monolithic `Unitroller`/`vBep20` pool — is a *separate* codebase, `VenusProtocol/venus-protocol`, and is out of scope here.) Venus is also live on zkSync Era(324), opBNB(204) and Unichain(130), which are outside the 7 requested chains; noted only in §4.

Isolated Pools replace Compound V2's single global comptroller with **many small, risk-isolated pools**, each with its own `Comptroller` and its own set of `VToken` markets. A pool's bad debt cannot spill into another pool. The deployment topology is a registry + two beacons per chain:

- **`PoolRegistry`** — one per chain, a `TransparentUpgradeableProxy`. The factory + registry: it deploys/registers each pool's `Comptroller` (emits `PoolRegistered`) and adds each market `VToken` to a pool (emits `MarketAdded`). Enumerate every pool with `getAllPools()` (`0xd88ff1f4`).
- **`ComptrollerBeacon`** + **`VTokenBeacon`** — one of each per chain (OpenZeppelin `UpgradeableBeacon`). Every pool's `Comptroller` is a `BeaconProxy` pointing at `ComptrollerBeacon`; every market's `VToken` is a `BeaconProxy` pointing at `VTokenBeacon`. **A single `Upgraded(address)` on a beacon atomically re-points every pool/every vToken on that chain at once** — this is the protocol-wide upgrade lever and the single most important thing a monitor must watch.
- **`Comptroller`** (per pool) — the risk engine: market listing, collateral factors, liquidation thresholds, caps, pause flags, reward-distributor wiring, account liquidation/healing.
- **`VToken`** (per market) — the interest-bearing receipt token; emits the Compound-derived `Mint`/`Redeem`/`Borrow`/`RepayBorrow`/`LiquidateBorrow`/`AccrueInterest` events (with isolated-pool extras: `BadDebtIncreased`, `HealBorrow`, `ProtocolSeize`, `SpreadReservesReduced`).
- **`RewardsDistributor`** (per pool, often several per pool) — a `TransparentUpgradeableProxy`; all XVS/reward accrual events live here, **not** on the Comptroller (no COMP-style `DistributedSupplierComp` on the comptroller).

> **The non-obvious fact:** the `VTokenImpl`/`ComptrollerImpl` addresses in the repo's `deployments/*.json` are **stale snapshots**. The *live* logic is whatever each beacon's `implementation()` returns right now. On 2026-06-08 the live `VTokenBeacon.implementation()` differed from the JSON on **every** chain (e.g. ETH JSON `0xefdf5C…` vs live `0x33be30b3…`). **Always read the beacon, never trust the JSON `*Impl` field.** (See §7.)

---

## 0. Contract families & versions

| Family | Per-chain count | Proxy pattern | Discovers / emits |
|---|---|---|---|
| `PoolRegistry` | 1 | TransparentUpgradeableProxy | `PoolRegistered`, `MarketAdded` — the discovery root |
| `ComptrollerBeacon` | 1 | UpgradeableBeacon (owned by Timelock) | `Upgraded(address)` — re-points all comptrollers |
| `VTokenBeacon` | 1 | UpgradeableBeacon (owned by Timelock) | `Upgraded(address)` — re-points all vTokens |
| `Comptroller` (per pool) | 1..8 | BeaconProxy → ComptrollerBeacon | risk-config + `MarketEntered`/`MarketSupported`/pause/caps |
| `VToken` (per market) | many | BeaconProxy → VTokenBeacon | `Mint`/`Redeem`/`Borrow`/`RepayBorrow`/`LiquidateBorrow`/`AccrueInterest`/bad-debt |
| `RewardsDistributor` (per pool) | 0..many | TransparentUpgradeableProxy | all reward accrual/distribution events |
| `NativeTokenGateway` (per WETH market) | 0..many | plain immutable helper | wraps native ETH ↔ vWETH (no events of its own beyond the vToken's) |

Pools live on 2026-06-08 (`getAllPools()` lengths verified live): **Ethereum 4** (Core, Curve, Ethena, Liquid Staked ETH), **BNB 8** (BTC, DeFi, GameFi, LiquidStakedBNB, LiquidStakedETH, Meme, Stablecoins, Tron), **Arbitrum 2** (Core, Liquid Staked ETH), **Base 1** (Core), **Optimism 1** (Core).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 PoolRegistry (one per chain — the registry/factory; pool & market discovery)

| topic0 | Event |
|--------|-------|
| `0x53ec2a1d9645c4631472dabcf6d255f5f2971baa64321235b1610d91c692928e` | `PoolRegistered(address indexed comptroller, (string,address,address,uint256,uint256) pool)` — `VenusPool=(string name,address creator,address comptroller,uint256 blockPosted,uint256 timestampPosted)` |
| `0x7772c85e68debdf74fad87834e2cc05fa763e74faf14de7096da305290651142` | `MarketAdded(address indexed comptroller, address indexed vTokenAddress)` |
| `0xa01f2b0df2b143bfb23d4b696c103547a6bec8ca1f56e8e8a483611cb4e23a7e` | `PoolNameSet(address indexed comptroller, string oldName, string newName)` |
| `0x8f91f3b5d20b61744ed591c43346d4514ee5c2ffced5fc3795bb13c6f9518147` | `PoolMetadataUpdated(address indexed comptroller, (string,string,string) oldMetadata, (string,string,string) newMetadata)` — `VenusPoolMetaData=(string category,string logoURL,string description)` |

`PoolRegistered` fires once per new pool; `MarketAdded` once per market the registry adds to a pool. **Subscribe to both on the per-chain `PoolRegistry` address (§3.x) to enumerate every comptroller and every vToken** — this is the canonical discovery path (or call `getAllPools()`/`Comptroller.getAllMarkets()`).

### 1.2 Comptroller (one per pool, BeaconProxy; risk engine)

| topic0 | Event |
|--------|-------|
| `0xaf16ad15f9e29d5140e8e81a30a92a755aa8edff3d301053c84392b70c0d09a3` | `MarketSupported(address vToken)` — market listed in this pool |
| `0x302feb03efd5741df80efe7f97f5d93d74d46a542a3d312d0faae64fa1f3e0e9` | `MarketUnlisted(address indexed vToken)` |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address indexed vToken, address indexed account)` |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address indexed vToken, address indexed account)` |
| `0x3b9670cf975d26958e754b57098eaa2ac914d8d2a31b83257997b9f346110fd9` | `NewCloseFactor(uint256 oldCloseFactorMantissa, uint256 newCloseFactorMantissa)` |
| `0x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5` | `NewCollateralFactor(address vToken, uint256 oldCFMantissa, uint256 newCFMantissa)` |
| `0x9e92c7d5fef69846094f3ddcadcb9402c6ba469c461368714f1cabd8ef48b591` | `NewLiquidationThreshold(address vToken, uint256 oldThresholdMantissa, uint256 newThresholdMantissa)` |
| `0xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316` | `NewLiquidationIncentive(uint256 oldIncentiveMantissa, uint256 newIncentiveMantissa)` |
| `0xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22` | `NewPriceOracle(address oldPriceOracle, address newPriceOracle)` |
| `0x35007a986bcd36d2f73fc7f1b73762e12eadb4406dd163194950fd3b5a6a827d` | `ActionPausedMarket(address vToken, uint8 action, bool pauseState)` — `action` = `Action` enum (§8 #5) |
| `0x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6` | `NewBorrowCap(address indexed vToken, uint256 newBorrowCap)` |
| `0x9e0ad9cee10bdf36b7fbd38910c0bdff0f275ace679b45b922381c2723d676f8` | `NewSupplyCap(address indexed vToken, uint256 newSupplyCap)` |
| `0x00b4f4f153ad7f1397564a8830fef092481e8cf6a2cd3ff04f96d10ba51200a5` | `NewMinLiquidatableCollateral(uint256 oldMinLiquidatableCollateral, uint256 newMinLiquidatableCollateral)` |
| `0x066a44d77db1581603d7d8ca1ca494756c0d359c7ffacd9b2c8f78dab7aceae2` | `NewRewardsDistributor(address indexed rewardsDistributor, address indexed rewardToken)` |
| `0xcb20dab7409e4fb972d9adccb39530520b226ce6940d85c9523a499b950b6ea3` | `NewPrimeToken(address oldPrimeToken, address newPrimeToken)` |
| `0x03561d5280ebb02280893b1d60978e4a27e7654a149c5d0e7c2cf65389ce1694` | `IsForcedLiquidationEnabledUpdated(address indexed vToken, bool enable)` |
| `0xcb325b7784f78486e42849c7a50b8c5ee008d00cd90e108a58912c0fcb6288b4` | `DelegateUpdated(address indexed approver, address indexed delegate, bool approved)` |

> `MarketEntered`/`MarketExited` have the **same signature and topic0 as Compound V2 / Moonwell** (`MarketEntered(address,address)` = `0x3ab23ab0…`). Disambiguate by emitting comptroller address.
> Isolated Comptroller uses **only** `ActionPausedMarket(address,uint8,bool)` (`0x35007a98…`) — there is no global `ActionPaused(string,bool)` and no `MarketActionPaused` string overload (unlike the Venus Core BNB pool / Moonwell).

### 1.3 VToken (one per market, BeaconProxy; the workhorse events — Compound-derived, 4-arg variants)

| topic0 | Event |
|--------|-------|
| `0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04` | `AccrueInterest(uint256 cashPrior, uint256 interestAccumulated, uint256 borrowIndex, uint256 totalBorrows)` — **4-arg** form (128-byte data, verified live) |
| `0xb4c03061fb5b7fed76389d5af8f2e0ddb09f8c70d1333abbb62582835e10accb` | `Mint(address indexed minter, uint256 mintAmount, uint256 mintTokens, uint256 accountBalance)` — **4-arg** (extra `accountBalance`) |
| `0xbd5034ffbd47e4e72a94baa2cdb74c6fad73cb3bcdc13036b72ec8306f5a7646` | `Redeem(address indexed redeemer, uint256 redeemAmount, uint256 redeemTokens, uint256 accountBalance)` — **4-arg** |
| `0x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80` | `Borrow(address indexed borrower, uint256 borrowAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1` | `RepayBorrow(address indexed payer, address indexed borrower, uint256 repayAmount, uint256 accountBorrows, uint256 totalBorrows)` |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address indexed liquidator, address indexed borrower, uint256 repayAmount, address indexed vTokenCollateral, uint256 seizeTokens)` |
| `0x3ac0548d62d3fa3c9a817cd33899b9acacd57e8958ebe51bc7d9a79f26a8a5db` | `ProtocolSeize(address indexed from, address indexed to, uint256 amount)` — protocol-share seize (isolated-pool addition) |
| `0x90125ffdb441e57c4f6bf69789206424859f206bea5727f2d81ad2470826ef6a` | `BadDebtIncreased(address indexed borrower, uint256 badDebtDelta, uint256 badDebtOld, uint256 badDebtNew)` |
| `0x9e19ec7d2b8f8a94df8cc0072453ace318d221e3cbb2731d0eaa0baac856520f` | `BadDebtRecovered(uint256 badDebtOld, uint256 badDebtNew)` |
| `0x9fe0294717a8efbc6ace1c151b73a4c89982339b2228a27d1ca21394e348986f` | `HealBorrow(address indexed payer, address indexed borrower, uint256 repayAmount)` |
| `0xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5` | `ReservesAdded(address indexed benefactor, uint256 addAmount, uint256 newTotalReserves)` |
| `0x9cc63bb4ef37ad6a5f5f657dfaf94865531d4234acbc431cc8ac035468f62720` | `SpreadReservesReduced(address indexed protocolShareReserve, uint256 reduceAmount, uint256 newTotalReserves)` |
| `0xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460` | `NewReserveFactor(uint256 oldReserveFactorMantissa, uint256 newReserveFactorMantissa)` |
| `0xf5815f353a60e815cce7553e4f60c533a59d26b1b5504ea4b6db8d60da3e4da2` | `NewProtocolSeizeShare(uint256 oldProtocolSeizeShareMantissa, uint256 newProtocolSeizeShareMantissa)` |
| `0xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926` | `NewMarketInterestRateModel(address indexed oldIRM, address indexed newIRM)` |
| `0x7ac369dbd14fa5ea3f473ed67cc9d598964a77501540ba6751eb0b3decf5870d` | `NewComptroller(address indexed oldComptroller, address indexed newComptroller)` |
| `0x6dbf1ff28f860de5edafa4c6505e37c0aba213288cc4166c5352b6d3776c79ef` | `NewShortfallContract(address indexed oldShortfall, address indexed newShortfall)` |
| `0xafec95c8612496c3ecf5dddc71e393528fe29bd145fbaf9c6b496d78d7e2d79b` | `NewProtocolShareReserve(address indexed oldProtocolShareReserve, address indexed newProtocolShareReserve)` |
| `0xc2ac513cdb57f91eb2bef4db918c285829524f549682b99717c6cb06cc011183` | `NewReduceReservesBlockDelta(uint256 oldReduceReservesBlockOrTimestampDelta, uint256 newReduceReservesBlockOrTimestampDelta)` |
| `0x35ce4c546a473796a8e70ec2d4af4f2031afe357afa7057b6ea7fa340730e1b2` | `SweepToken(address indexed token)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 amount)` — vToken shares (ERC-20) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 amount)` |

> **`AccrueInterest` 4-arg** (`0x4dec04e7…`, 128-byte data) is identical to Moonwell's 4-arg form and is **NOT** stock Compound's 3-arg `AccrueInterest(uint256,uint256,uint256)` (`0x875352fb…`). The Venus *Core* BNB pool (separate codebase) emits the legacy 3-arg `AccrueInterest`. Disambiguate isolated vs core by data length (128 vs 96 bytes) and by emitter.
> **`Borrow`/`RepayBorrow`/`LiquidateBorrow`/`MarketEntered`/`Transfer`/`Approval` topic0s are byte-identical to Compound V2 and Moonwell** (shared signatures). **`Mint`/`Redeem`/`AccrueInterest` differ from stock Compound** (4-arg here) but **match Moonwell's `AccrueInterest`** while differing on `Mint`/`Redeem` (Moonwell uses the 3-arg `Mint(address,uint256,uint256)` `0x4c209b5f…`). Always key on emitter.

### 1.4 RewardsDistributor (per pool, transparent proxy; all reward accrual)

| topic0 | Event |
|--------|-------|
| `0x9563ff6035b973f2e4514ad9315010c220eb74b0c33a782a18118a199a97e442` | `DistributedSupplierRewardToken(address indexed vToken, address indexed supplier, uint256 rewardTokenDelta, uint256 rewardTokenTotal, uint256 rewardTokenSupplyIndex)` |
| `0x510d7612da9ca257889eabdfbe0366aaea10020be46f7810f4afb2111d80aa93` | `DistributedBorrowerRewardToken(address indexed vToken, address indexed borrower, uint256 rewardTokenDelta, uint256 rewardTokenTotal, uint256 rewardTokenBorrowIndex)` |
| `0x6a7b996800070d8bc0f9a3ddcb0a4b09bc1653f76381d745444956366afd423a` | `RewardTokenSupplyIndexUpdated(address indexed vToken)` |
| `0xbfeed4eb85c013b0e466fdfdbaa785159ff7986078247dc95f1c717a5bd6bca2` | `RewardTokenBorrowIndexUpdated(address indexed vToken, (uint256) marketBorrowIndex)` — arg is `Exp{uint256 mantissa}`, encoded as a 1-tuple (verified live) |
| `0x24741480445e83baea9eb28086e16a4377ebb4f003c773e386496fd90b3ed04e` | `RewardTokenSupplySpeedUpdated(address indexed vToken, uint256 newSpeed)` |
| `0x2091432bbf4aa40f4785b469e931d32c5f5c6ba66dcf702a99cbe776df729c3c` | `RewardTokenBorrowSpeedUpdated(address indexed vToken, uint256 newSpeed)` |
| `0x251909abf904fc80eac3f0d4c25e5c800441ea19fda63c6f0df08e4f24f926f9` | `RewardTokenGranted(address indexed recipient, uint256 amount)` |
| `0x4882c0217331870166b5d239c9f7be7801bab4be26560cd2f8789145d0fd3af4` | `ContributorRewardTokenSpeedUpdated(address indexed contributor, uint256 newSpeed)` |
| `0x38fe05baf9dc12e4e3bfda3daba26419e9930bf26ee6227f407ca46f8c9c29bc` | `ContributorRewardsUpdated(address indexed contributor, uint256 rewardAccrued)` |
| `0xfe6944646a362be70b0925ea999b3d9f755589a63ffcd89e4fb2b0affd252c71` | `MarketInitialized(address indexed vToken)` |
| `0x41b697bf2627e0a03f253382759baaab2469897004cc619465a3d8f4bb6b3fec` | `SupplyLastRewardingBlockUpdated(address indexed vToken, uint32 newBlock)` |
| `0x4163eb203170b7facecc8d7307e3f8affa8826d4df30fc722f8f8ce17988eb91` | `BorrowLastRewardingBlockUpdated(address indexed vToken, uint32 newBlock)` |
| `0x0e68f65b8654c09acfdc448a42c8a0d72697206fd0c23c357022fa1cd1626861` | `SupplyLastRewardingBlockTimestampUpdated(address indexed vToken, uint256 newTimestamp)` — time-based chains |
| `0x7aefe759bc95e5c94c6d919eef378c410527d0d85f409986ec8d54a99ea8395e` | `BorrowLastRewardingBlockTimestampUpdated(address indexed vToken, uint256 newTimestamp)` |

> Reward token is XVS on most pools (ETH RewardsDistributor `rewardToken()` = `0xd3cc9d8f…` = XVS), but each distributor can emit any ERC-20 — read `rewardToken()` (`0xf7c618c1`). A pool can have **multiple** RewardsDistributors (ETH Core has 3); enumerate via `Comptroller.getRewardDistributors()` (`0x61252fd1`) or by the comptroller's `NewRewardsDistributor` logs.

### 1.5 Beacons & proxy admin (upgrade signals)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | `ComptrollerBeacon`, `VTokenBeacon` (re-points all instances on the chain), **and** every TransparentProxy (PoolRegistry, RewardsDistributor) |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | beacons + ownable contracts |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | TransparentUpgradeableProxy (PoolRegistry, RewardsDistributor) |
| `0x1cf3b03a6cf19fa2baba4df148e9dcabedea7f8a5c07840e207e5c089be95d3e` | `BeaconUpgraded(address indexed beacon)` | each BeaconProxy at construction (Comptroller/VToken) |

> **`Upgraded(address)` on a `ComptrollerBeacon` or `VTokenBeacon` is the highest-severity monitoring signal in this codebase** — one log silently re-points the logic of every pool / every market on that chain. Watch the two beacon addresses (§3.x) directly.

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

Selectors recomputed locally; interface `uint`→`uint256`. All state-changing selectors live in the **implementation** bytecode (the on-chain proxy bytecode is the tiny BeaconProxy/Transparent stub, so a `grep` of the proxy's `eth_getCode` will not find them — resolve the impl/beacon first).

### 2.1 PoolRegistry

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd88ff1f4` | `getAllPools()` | `VenusPool[]` — enumerate every pool (verified live: ETH 4, BNB 8, ARB 2, Base 1, OP 1) |
| `0x7aee632d` | `getPoolByComptroller(address)` | `VenusPool` |
| `0x266e0a7f` | `getVTokenForAsset(address comptroller, address asset)` | `address` vToken |
| `0xc79f6362` | `getPoolsSupportedByMarket(address vToken)` | `address[]` |
| `0x74f79308` | `addMarket((address,uint256,uint256,uint256,address,uint256,uint256,uint256,uint256))` | adds a market → emits `MarketAdded` (admin/ACM) |
| `0x4d6cda14` | `createRegistryPool(string,address,uint256,uint256,uint256,address,uint256,address)` | creates a pool → emits `PoolRegistered` (admin/ACM) |

### 2.2 Comptroller (per pool)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb0772d0b` | `getAllMarkets()` | `VToken[]` — every market in this pool |
| `0x8e8f294b` | `markets(address)` | `(bool isListed, uint256 collateralFactorMantissa, bool isVenus)` (isolated layout) |
| `0xc2998238` | `enterMarkets(address[])` | user opt-in as collateral |
| `0xede4edd0` | `exitMarket(address)` | |
| `0xcab4f84c` | `supportMarket(address)` | ACM — emits `MarketSupported` |
| `0x5cc4fdeb` | `setCollateralFactor(address,uint256,uint256)` | (vToken, CF, liqThreshold) — emits `NewCollateralFactor` + `NewLiquidationThreshold` |
| `0xa8431081` | `setLiquidationIncentive(uint256)` | |
| `0xd136af44` | `setMarketSupplyCaps(address[],uint256[])` | |
| `0x186db48f` | `setMarketBorrowCaps(address[],uint256[])` | |
| `0x24aaa220` | `setActionsPaused(address[],uint8[],bool)` | emits `ActionPausedMarket` per (market,action) |
| `0x56aaee2d` | `addRewardsDistributor(address)` | wires a RewardsDistributor → emits `NewRewardsDistributor` |
| `0x61252fd1` | `getRewardDistributors()` | `RewardsDistributor[]` (ETH Core = 3) |
| `0x92136395` | `healAccount(address)` | socializes bad debt → vToken `HealBorrow`/`BadDebtIncreased` |
| `0x2bce219c` | `liquidateAccount(address,(address,address,uint256)[])` | batch full-account liquidation |

### 2.3 VToken (per market)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa0712d68` | `mint(uint256)` | → `Mint` + `AccrueInterest` |
| `0x23323e03` | `mintBehalf(address,uint256)` | mint to another account |
| `0xdb006a75` | `redeem(uint256)` | → `Redeem` |
| `0x852a12e3` | `redeemUnderlying(uint256)` | |
| `0xc5ebeaec` | `borrow(uint256)` | → `Borrow` |
| `0x0e752702` | `repayBorrow(uint256)` | → `RepayBorrow` |
| `0x2608f818` | `repayBorrowBehalf(address,uint256)` | |
| `0xf5e3c462` | `liquidateBorrow(address,uint256,address)` | (borrower, repayAmount, vTokenCollateral) → `LiquidateBorrow` |
| `0x8bbdb6db` | `forceLiquidateBorrow(address,address,uint256,address,bool)` | comptroller-only; `isForcedLiquidationEnabled` markets |
| `0x44fe6ffe` | `healBorrow(address,address,uint256)` | comptroller-only → `HealBorrow` |
| `0x896b9f48` | `badDebtRecovered(uint256,uint256)` | shortfall-only → `BadDebtRecovered` |
| `0xa6afed95` | `accrueInterest()` | public; → `AccrueInterest` |
| `0x07e27959` | `reduceReserves(uint256)` | → `SpreadReservesReduced` |
| `0x107568df` | `setProtocolShareReserve(address)` | → `NewProtocolShareReserve` |
| `0x182df0f5` / `0x5fe3b567` / `0x6f307dc3` | `exchangeRateStored()` / `comptroller()` / `underlying()` | views |

### 2.4 RewardsDistributor / Beacon / NativeTokenGateway

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x04caeb10` | `claimRewardToken(address holder, address[] vTokens)` | RewardsDistributor |
| `0xf7c618c1` | `rewardToken()` | RewardsDistributor (e.g. XVS) |
| `0x5c60da1b` | `implementation()` | UpgradeableBeacon — **read this to get live logic** |
| `0x3659cfe6` | `upgradeTo(address)` | UpgradeableBeacon / proxy — emits `Upgraded` |
| `0xa86f8221` | `wrapAndSupply(address)` | NativeTokenGateway (native ETH → vWETH) |
| `0x85ceb1e4` | `redeemUnderlyingAndUnwrap(uint256)` | NativeTokenGateway |
| `0x9cc60d44` | `borrowAndUnwrap(uint256)` | NativeTokenGateway |

---

## 3. Addresses

All `eth_getCode`-checked on each chain's `publicnode` RPC on 2026-06-08 (PoolRegistry/beacon bytecode present). **PoolRegistry + both beacons + the proxy admin are distinct addresses on every chain** (no CREATE2 reuse — each chain deployed independently). Per-pool comptrollers and per-market vTokens are also per-chain. The `*Impl` columns below are the **stale JSON snapshot**; the **live** impl (read from the beacon's `implementation()` on 2026-06-08) is given separately in §7.

### 3.1 Ethereum mainnet (chain ID 1) — 4 pools

| Role | Address |
|------|---------|
| **PoolRegistry** (transparent proxy) | `0x61CAff113CCaf05FFc6540302c37adcf077C5179` |
| PoolRegistry impl | `0x08A2577611Ae63d1ba40188035eD6Ad21F8502A9` |
| **ComptrollerBeacon** | `0xAE2C3F21896c02510aA187BdA0791cDA77083708` |
| **VTokenBeacon** | `0xfc08aADC7a1A93857f6296C3fb78aBA1d286533a` |
| DefaultProxyAdmin (owns PoolRegistry + RewardsDistributors) | `0x567e4cc5e085d09f66f836fa8279f38b4e5866b9` |
| Comptroller — Core | `0x687a01ecF6d3907658f7A7c714749fAC32336D1B` |
| Comptroller — Curve | `0x67aA3eCc5831a65A5Ba7be76BED3B5dc7DB60796` |
| Comptroller — Ethena | `0x562d2b6FF1dbf5f63E233662416782318cC081E4` |
| Comptroller — Liquid Staked ETH | `0xF522cd0360EF8c2FF48B648d53EA1717Ec0F3Ac3` |
| RewardsDistributor (Core, busy; XVS) | `0x134bfDEa7e68733921Bc6A87159FB0d68aBc6Cf8` |
| NativeTokenGateway (vWETH Core) | `0x044dd75b9E043ACFD2d6EB56b6BB814df2a9c809` |

### 3.2 Arbitrum One (chain ID 42161) — 2 pools

| Role | Address |
|------|---------|
| **PoolRegistry** | `0x382238f07Bc4Fe4aA99e561adE8A4164b5f815DA` |
| PoolRegistry impl | `0xc9A9594e774F9454e4665126C72Eb62643253aB0` |
| **ComptrollerBeacon** | `0x8b6c2E8672504523Ca3a29a5527EcF47fC7d43FC` |
| **VTokenBeacon** | `0xE9381D8CA7006c12Ae9eB97890575E705996fa66` |
| DefaultProxyAdmin | `0xF6fF3e9459227f0cDE8B102b90bE25960317b216` |
| Comptroller — Core | `0x317c1A5739F39046E20b08ac9BeEa3f10fD43326` |
| Comptroller — Liquid Staked ETH | `0x52bAB1aF7Ff770551BD05b9FC2329a0Bf5E23F16` |
| NativeTokenGateway (vWETH Core) | `0xc8e51418cadc001157506b306C6d0b878f1ff755` |

### 3.3 Optimism (chain ID 10) — 1 pool

| Role | Address |
|------|---------|
| **PoolRegistry** | `0x147780799840d541C1d7c998F0cbA996d11D62bb` |
| PoolRegistry impl | `0x6a166fcd39BA9c4ACc1b98eC45Adcdc4926E7967` |
| **ComptrollerBeacon** | `0x64f9306496ccF7b7369d02d68D6abcA2Edfb871d` |
| **VTokenBeacon** | `0xd550Bdfa9402e215De0BabCb99F7294BE0268367` |
| DefaultProxyAdmin | `0xeaF9490cBEA6fF9bA1D23671C39a799CeD0DCED2` |
| Comptroller — Core | `0x5593FF68bE84C966821eEf5F0a988C285D5B7CeC` |
| NativeTokenGateway (vWETH Core) | `0x5B1b7465cfDE450e267b562792b434277434413c` |

### 3.4 Base mainnet (chain ID 8453) — 1 pool

| Role | Address |
|------|---------|
| **PoolRegistry** | `0xeef902918DdeCD773D4B422aa1C6e1673EB9136F` |
| PoolRegistry impl | `0x88eF9Fd7004f81c1B1CA59375178425C97A7eE68` |
| **ComptrollerBeacon** | `0x1b6dE1C670db291bcbF793320a42dbBD858E67aC` |
| **VTokenBeacon** | `0x87a6476510368c4Bfb70d04A3B0e5a881eC7f0d1` |
| DefaultProxyAdmin | `0x7B06EF6b68648C61aFE0f715740fE3950B90746B` |
| Comptroller — Core | `0x0C7973F9598AA62f9e03B94E92C967fD5437426C` |
| NativeTokenGateway (vWETH Core) | `0x8e890ca3829c740895cdEACd4a3BE36ff9343643` |

### 3.5 BNB Smart Chain (chain ID 56) — 8 isolated pools (non-core)

> These are the **isolated** pools. The Venus **Core** pool on BNB (the original `Unitroller` + `vBep20`) is a *different* codebase and is **not** listed here.

| Role | Address |
|------|---------|
| **PoolRegistry** | `0x9F7b01A536aFA00EF10310A162877fd792cD0666` |
| PoolRegistry impl | `0xc4953e157D057941A9a71273B0aF4d4477ED2770` |
| **ComptrollerBeacon** | `0x38B4Efab9ea1bAcD19dC81f19c4D1C2F9DeAe1B2` |
| **VTokenBeacon** | `0x2b8A1C539ABaC89CbF7E2Bc6987A0A38A5e660D4` |
| DefaultProxyAdmin | `0x6beb6D2695B67FEb73ad4f172E8E2975497187e4` |
| Comptroller — BTC | `0x9DF11376Cf28867E2B0741348044780FbB7cb1d6` |
| Comptroller — DeFi | `0x3344417c9360b963ca93A4e8305361AEde340Ab9` |
| Comptroller — GameFi | `0x1b43ea8622e76627B81665B1eCeBB4867566B963` |
| Comptroller — LiquidStakedBNB | `0xd933909A4a2b7A4638903028f44D1d38ce27c352` |
| Comptroller — LiquidStakedETH | `0xBE609449Eb4D76AD8545f957bBE04b596E8fC529` |
| Comptroller — Meme | `0x33B6fa34cd23e5aeeD1B112d5988B026b8A5567d` |
| Comptroller — Stablecoins | `0x94c1495cD4c557f1560Cbd68EAB0d197e6291571` |
| Comptroller — Tron | `0x23b4404E4E5eC5FF5a6FFb70B7d14E3FabF237B0` |

### 3.6 Per-market vTokens

vTokens are discovered, not hardcoded: call `Comptroller.getAllMarkets()` (`0xb0772d0b`) on each pool comptroller, or scan `PoolRegistry.MarketAdded`. Verified live: **ETH Core pool = 23 markets** (e.g. first market `0x8716554364f20bca783cb2baa744d39361fd1d8d`). Per-pool counts shift as markets are added — never freeze a vToken list; re-enumerate.

---

## 4. Cross-chain summary

| Chain | ID | PoolRegistry | ComptrollerBeacon | VTokenBeacon | Pools | Deployed? |
|---|---|---|---|---|---|---|
| Ethereum | 1 | `0x61CAff…C5179` | `0xAE2C3F…83708` | `0xfc08aA…6533a` | 4 | ✓ |
| Arbitrum One | 42161 | `0x382238…815DA` | `0x8b6c2E…d43FC` | `0xE9381D…6fa66` | 2 | ✓ |
| Optimism | 10 | `0x147780…D62bb` | `0x64f930…871d` | `0xd550Bd…68367` | 1 | ✓ |
| Base | 8453 | `0xeef902…9136F` | `0x1b6dE1…67aC` | `0x87a647…f0d1` | 1 | ✓ |
| BNB | 56 | `0x9F7b01…0666` | `0x38B4Ef…e1B2` | `0x2b8A1C…60D4` | 8 (isolated) | ✓ |
| Avalanche | 43114 | — | — | — | 0 | **✗ (0x)** |
| Polygon PoS | 137 | — | — | — | 0 | **✗ (0x)** |

Also live but **outside the 7 requested chains** (same codebase): **zkSync Era (324)**, **opBNB (204)**, **Unichain (130)** — each with its own PoolRegistry + beacons.

**Three things to internalize:**
1. **No shared addresses across chains.** Every PoolRegistry/beacon/comptroller/vToken is a fresh per-chain deployment — there is no Morpho-style vanity and no CREATE2 address reuse. Always key on `(chainId, address)`.
2. **Topics + selectors are 100% chain-agnostic.** A `Mint`/`Borrow`/`LiquidateBorrow`/`MarketAdded`/`Upgraded` topic0 is identical on all 5 deployed chains; only the emitting address changes.
3. **Governance is per-chain.** The two beacons + the DefaultProxyAdmin are each owned by that chain's Venus governance contract (the "Normal Timelock" of Venus's omnichain governance). On Ethereum the ComptrollerBeacon owner and DefaultProxyAdmin owner are both `0xd969e79406c35e80750aaae061d402aab9325714`; each other chain has its own local owner (verified live: BNB `0x939bd8…6396`, ARB `0x4b9458…4017`, Base `0x21c12f…f517`, OP `0x0c6f1e…c04b`).

---

## 5. Absence on Avalanche & Polygon (recorded finding, not omission)

Isolated Pools are **not deployed** on Avalanche C-Chain (43114) or Polygon PoS (137). The repo has **no** `deployments/avalanche*` or `deployments/polygon*` directory, and `eth_getCode` returns `0x` (0 bytes) on **both** chains for **every** anchor address from each deployed chain — checked across 6 addresses each (PoolRegistry on ETH/BNB/ARB, both beacons, a comptroller):

```
avax (43114): PoolRegistry 0x61CAff… → 0 | ComptrollerBeacon 0xAE2C3F… → 0 | VTokenBeacon 0xfc08aA… → 0
              Comptroller 0x687a01… → 0 | BNB PoolRegistry 0x9F7b01… → 0 | ARB PoolRegistry 0x382238… → 0
pol (137):    PoolRegistry 0x61CAff… → 0 | ComptrollerBeacon 0xAE2C3F… → 0 | VTokenBeacon 0xfc08aA… → 0
              Comptroller 0x687a01… → 0 | BNB PoolRegistry 0x9F7b01… → 0 | ARB PoolRegistry 0x382238… → 0
```

There is no Venus deployment of any kind (core or isolated) on Avalanche or Polygon as of 2026-06-08.

---

## 6. Proxies — registry/admin = transparent, pools/markets = beacon

| Contract | Pattern | Upgrade auth | Impl detection |
|----------|---------|--------------|----------------|
| **PoolRegistry** | TransparentUpgradeableProxy | DefaultProxyAdmin → Timelock | EIP-1967 impl slot `0x360894…382bbc` (populated); admin slot `0xb53127…5d6103` = DefaultProxyAdmin |
| **ComptrollerBeacon** | UpgradeableBeacon (not a proxy itself) | `owner()` = Timelock | call `implementation()` `0x5c60da1b` |
| **VTokenBeacon** | UpgradeableBeacon | `owner()` = Timelock | call `implementation()` `0x5c60da1b` |
| **Comptroller** (per pool) | BeaconProxy → ComptrollerBeacon | via the beacon (one `Upgraded` upgrades all) | EIP-1967 **beacon slot** `0xa3f0ad74…133d50` = ComptrollerBeacon (impl slot is empty) |
| **VToken** (per market) | BeaconProxy → VTokenBeacon | via the beacon | EIP-1967 beacon slot = VTokenBeacon |
| **RewardsDistributor** (per pool) | TransparentUpgradeableProxy | DefaultProxyAdmin → Timelock | EIP-1967 impl slot populated; admin slot = DefaultProxyAdmin |
| **NativeTokenGateway** | plain immutable | — | no impl slot |

EIP-1967 slots: impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` · admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` · beacon `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50`.

Verified live on 2026-06-08:
- PoolRegistry (ETH) impl slot → `0x08A2577611Ae63d1ba40188035eD6Ad21F8502A9`; admin slot → `0x567e4cc5…866b9` (= DefaultProxyAdmin). Transparent proxy confirmed.
- Comptroller_Core (ETH) beacon slot → `0xAE2C3F…83708` (= ComptrollerBeacon). BeaconProxy confirmed. Two BeaconProxy bytecode builds coexist: an older ≈ 849 B build and a newer ≈ 332 B build. **The split is by deploy era, NOT by chain** — both sizes appear on the *same* chain (ETH: Core/Curve/LST-ETH = 849 B, Ethena = 332 B; BNB: DeFi/GameFi/LSBNB/Stable/Tron = 849 B, BTC/LSETH/Meme = 332 B). Every OP/Base/Arbitrum comptroller happens to be the newer 332 B build. All are confirmed BeaconProxies (beacon slot = ComptrollerBeacon); the 332 B variant is just a leaner OZ BeaconProxy.
- RewardsDistributor (ETH `0x134bfde…`) impl slot → `0x972f10e3…944f`; admin slot → `0x567e4cc5…866b9`. Transparent proxy confirmed.

### 6.1 **Live beacon implementations (read 2026-06-08) — the JSON `*Impl` is stale**

The `ComptrollerBeacon.implementation()` matches the JSON `ComptrollerImpl` on every chain. The **`VTokenBeacon.implementation()` does NOT match the JSON `VTokenImpl` on any chain except BNB** — the VToken logic has been upgraded since the JSON snapshot. **Resolve logic from the beacon, live, every time.**

| Chain | ComptrollerBeacon.impl (live) | VTokenBeacon.impl (live) | JSON VTokenImpl (STALE) |
|---|---|---|---|
| Ethereum | `0xC910F2B196C516253e88b2097ba5D7d5fC9fa84e` | `0x33be30b31f07c8a2bfb705fbce55e983c47ba864` | `0xefdf5CcC12d8cff4a7ed4e421b95F8f69Cf2F766` |
| Arbitrum | `0x4b256a7836415e09DabA40541eE78602Bc6B24bF` | `0x1986fb53535953711265d5fd329cd7a690411669` | `0xfC0df4d5b0FCEb410985a13fC2be7df793453649` |
| Optimism | `0x4D3f690A33A365Fc131777ea6e0f5B8821eb755b` | `0xbeb9ee824a0096c0fb606b070c028cb55b6f21e7` | `0x5794a3D0238E18AA6de78e9095fF6a9A188A128d` |
| Base | `0x93177BFDBc5dAf7B0fF4A09478eF90FF6e28E04A` | `0x107ba74c87e75b6cc291510d3a85d0c8eaa73e82` | `0x15976Af57CBDEA05aB1c338822E397519f096C67` |
| BNB | `0x7B586Aed00C85d7E32B463DCE094B1faCA7e7e7c` | `0x228ea224d62D14a2e2cb9B43083aE43954C39B67` | `0x228Ea224d62D14a2e2cb9B43083aE43954C39B67` (matches) |

---

## 7. Detection invariants & gotchas

1. **Discovery is two-level: PoolRegistry → Comptroller → vTokens.** `PoolRegistry.getAllPools()`/`PoolRegistered` gives comptrollers; `Comptroller.getAllMarkets()`/`PoolRegistry.MarketAdded` gives vTokens. Never hardcode a vToken set — markets are added over time (ETH Core = 23 and growing).
2. **`Upgraded(address)` on a beacon = chain-wide logic swap.** A single `Upgraded` on `ComptrollerBeacon` or `VTokenBeacon` (`0xbc7cd75a…`) re-points **every** pool / **every** market on that chain at once. This is the top-severity admin event. Watch both beacon addresses (§3.x) directly. (TransparentProxy `Upgraded` on PoolRegistry/a RewardsDistributor affects only that one instance.)
3. **The repo JSON `VTokenImpl`/`ComptrollerImpl` are stale.** Resolve live logic via `beacon.implementation()` (`0x5c60da1b`); on 2026-06-08 the live VToken impl differed from the JSON on ETH/ARB/OP/Base (§6.1). For a per-instance impl, read the BeaconProxy's beacon slot → then the beacon's `implementation()`.
4. **`AccrueInterest` is the 4-arg form** (`0x4dec04e7…`, 128-byte data: `cashPrior, interestAccumulated, borrowIndex, totalBorrows`). The Venus **Core BNB** pool (separate codebase) uses the legacy **3-arg** `AccrueInterest` (`0x875352fb…`, 96-byte data). Distinguish by data length + emitter. `Mint`/`Redeem` here are 4-arg (`…, accountBalance`) → topic0s differ from stock Compound's 3-arg.
5. **`ActionPausedMarket(address,uint8,bool)` — the `uint8` is the `Action` enum:** `0=MINT, 1=REDEEM, 2=BORROW, 3=REPAY, 4=SEIZE, 5=LIQUIDATE, 6=TRANSFER, 7=ENTER_MARKET, 8=EXIT_MARKET`. `pauseState=true` means paused. There is no global string-based `ActionPaused` event in isolated pools.
6. **Bad-debt is isolated and explicit.** When a position is fully seized, the comptroller calls `healAccount`/`liquidateAccount`, and the vToken emits `BadDebtIncreased(borrower, delta, old, new)` + `HealBorrow`. Bad debt is later auctioned by the Shortfall contract → `BadDebtRecovered`. Unlike Aave there is no per-reserve "deficit" event; track `BadDebtIncreased` per market. Bad debt **cannot cross pool boundaries** — that is the entire point of isolation.
7. **`ProtocolSeize(from,to,amount)` is a protocol-share cut on every liquidation** (the protocol's slice of the seized collateral, sent to the ProtocolShareReserve). It rides alongside `LiquidateBorrow`; do not double-count seized collateral.
8. **Rewards live on RewardsDistributor, not the comptroller.** No COMP-style `DistributedSupplierComp` on the comptroller. A pool can have several RewardsDistributors (ETH Core = 3); enumerate via `getRewardDistributors()` (`0x61252fd1`) or the comptroller's `NewRewardsDistributor` logs. Reward token is per-distributor (`rewardToken()` `0xf7c618c1`; usually XVS `0xd3cc9d8f…` on ETH but not guaranteed).
9. **`RewardTokenBorrowIndexUpdated(address,(uint256))`** — the 2nd arg is the `Exp{uint256 mantissa}` struct, ABI-encoded as a 1-element tuple. Topic0 is `0xbfeed4eb…` (verified live), **not** the flattened `(address,uint256)` form (`0x77747b02…`). `RewardTokenSupplyIndexUpdated(address)` carries no data words.
10. **Topic0 collisions with Compound V2 / Moonwell / Venus Core.** `Borrow` `0x13ed6866…`, `RepayBorrow` `0x1a2a22cb…`, `LiquidateBorrow` `0x298637f6…`, `MarketEntered` `0x3ab23ab0…`, `Transfer`/`Approval`, and several `New*` config events are byte-identical across all Compound forks. **Always scope getLogs by the emitting vToken/comptroller address** (and `(chainId,address)`), never by topic0 alone. `AccrueInterest` `0x4dec04e7…` collides with **Moonwell** (same 4-arg form) but not with Venus Core (3-arg).
11. **`onBehalf`/payer ≠ borrower.** `RepayBorrow(payer, borrower, …)` and `HealBorrow(payer, borrower, …)` separate the payer from the debt owner; `mintBehalf`/`repayBorrowBehalf` let a third party act. Attribute positions to `borrower`/the account, not `tx.from`.
12. **BeaconProxy bytecode is a stub.** `eth_getCode` on a Comptroller/VToken returns the tiny BeaconProxy (~849 B older build, ~332 B newer build) — a 4-byte selector `grep` of that bytecode will NOT find `mint`/`borrow`/etc. The selectors live in the beacon's `implementation()`. The 849 B vs 332 B size is a **deploy-era** difference, not a per-chain one: both sizes coexist on ETH and BNB (e.g. ETH Core = 849 B, ETH Ethena = 332 B); OP/Base/Arbitrum comptrollers are all the newer 332 B build.
13. **publicnode getLogs caps:** ~50k-block range; topic-only filters (no `address`) silently return `[]` — always pass `address`. BNB publicnode prunes old history ("History has been pruned") so pool-launch events (`PoolRegistered`) may be unreachable there — scan via an archive node or read `getAllPools()` instead.
14. **NOT on Avalanche or Polygon** (§5) — every anchor returns `0x`. Do not hardcode any address as "the Venus address" on those chains.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== PoolRegistry (per chain; discovery root) =====
TOPIC_PR_POOLREGISTERED       = '\x53ec2a1d9645c4631472dabcf6d255f5f2971baa64321235b1610d91c692928e'
TOPIC_PR_MARKETADDED          = '\x7772c85e68debdf74fad87834e2cc05fa763e74faf14de7096da305290651142'
TOPIC_PR_POOLNAMESET          = '\xa01f2b0df2b143bfb23d4b696c103547a6bec8ca1f56e8e8a483611cb4e23a7e'
TOPIC_PR_POOLMETADATAUPDATED  = '\x8f91f3b5d20b61744ed591c43346d4514ee5c2ffced5fc3795bb13c6f9518147'
-- ===== Comptroller (per pool) =====
TOPIC_C_MARKETSUPPORTED       = '\xaf16ad15f9e29d5140e8e81a30a92a755aa8edff3d301053c84392b70c0d09a3'
TOPIC_C_MARKETUNLISTED        = '\x302feb03efd5741df80efe7f97f5d93d74d46a542a3d312d0faae64fa1f3e0e9'
TOPIC_C_MARKETENTERED         = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'  -- shared w/ Compound/Moonwell
TOPIC_C_MARKETEXITED          = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_C_NEWCOLLATERALFACTOR   = '\x70483e6592cd5182d45ac970e05bc62cdcc90e9d8ef2c2dbe686cf383bcd7fc5'
TOPIC_C_NEWLIQTHRESHOLD       = '\x9e92c7d5fef69846094f3ddcadcb9402c6ba469c461368714f1cabd8ef48b591'
TOPIC_C_NEWLIQINCENTIVE       = '\xaeba5a6c40a8ac138134bff1aaa65debf25971188a58804bad717f82f0ec1316'
TOPIC_C_NEWBORROWCAP          = '\x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6'
TOPIC_C_NEWSUPPLYCAP          = '\x9e0ad9cee10bdf36b7fbd38910c0bdff0f275ace679b45b922381c2723d676f8'
TOPIC_C_ACTIONPAUSEDMARKET    = '\x35007a986bcd36d2f73fc7f1b73762e12eadb4406dd163194950fd3b5a6a827d'
TOPIC_C_NEWREWARDSDISTRIBUTOR = '\x066a44d77db1581603d7d8ca1ca494756c0d359c7ffacd9b2c8f78dab7aceae2'
TOPIC_C_NEWPRICEORACLE        = '\xd52b2b9b7e9ee655fcb95d2e5b9e0c9f69e7ef2b8e9d2d0ea78402d576d22e22'
-- ===== VToken (per market) =====
TOPIC_VT_ACCRUEINTEREST       = '\x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04'  -- 4-arg (Moonwell-shared)
TOPIC_VT_MINT                 = '\xb4c03061fb5b7fed76389d5af8f2e0ddb09f8c70d1333abbb62582835e10accb'  -- 4-arg
TOPIC_VT_REDEEM               = '\xbd5034ffbd47e4e72a94baa2cdb74c6fad73cb3bcdc13036b72ec8306f5a7646'  -- 4-arg
TOPIC_VT_BORROW               = '\x13ed6866d4e1ee6da46f845c46d7e54120883d75c5ea9a2dacc1c4ca8984ab80'  -- shared w/ Compound/Moonwell
TOPIC_VT_REPAYBORROW          = '\x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1'  -- shared
TOPIC_VT_LIQUIDATEBORROW      = '\x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'  -- shared
TOPIC_VT_PROTOCOLSEIZE        = '\x3ac0548d62d3fa3c9a817cd33899b9acacd57e8958ebe51bc7d9a79f26a8a5db'
TOPIC_VT_BADDEBTINCREASED     = '\x90125ffdb441e57c4f6bf69789206424859f206bea5727f2d81ad2470826ef6a'
TOPIC_VT_BADDEBTRECOVERED     = '\x9e19ec7d2b8f8a94df8cc0072453ace318d221e3cbb2731d0eaa0baac856520f'
TOPIC_VT_HEALBORROW           = '\x9fe0294717a8efbc6ace1c151b73a4c89982339b2228a27d1ca21394e348986f'
TOPIC_VT_RESERVESADDED        = '\xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5'
TOPIC_VT_SPREADRESERVESREDUCED= '\x9cc63bb4ef37ad6a5f5f657dfaf94865531d4234acbc431cc8ac035468f62720'
TOPIC_VT_NEWMARKETIRM         = '\xedffc32e068c7c95dfd4bdfd5c4d939a084d6b11c4199eac8436ed234d72f926'
-- ===== RewardsDistributor (per pool) =====
TOPIC_RD_DISTSUPPLIER         = '\x9563ff6035b973f2e4514ad9315010c220eb74b0c33a782a18118a199a97e442'
TOPIC_RD_DISTBORROWER         = '\x510d7612da9ca257889eabdfbe0366aaea10020be46f7810f4afb2111d80aa93'
TOPIC_RD_SUPPLYINDEXUPDATED   = '\x6a7b996800070d8bc0f9a3ddcb0a4b09bc1653f76381d745444956366afd423a'
TOPIC_RD_BORROWINDEXUPDATED   = '\xbfeed4eb85c013b0e466fdfdbaa785159ff7986078247dc95f1c717a5bd6bca2'  -- arg is Exp tuple
TOPIC_RD_SUPPLYSPEEDUPDATED   = '\x24741480445e83baea9eb28086e16a4377ebb4f003c773e386496fd90b3ed04e'
TOPIC_RD_BORROWSPEEDUPDATED   = '\x2091432bbf4aa40f4785b469e931d32c5f5c6ba66dcf702a99cbe776df729c3c'
TOPIC_RD_REWARDTOKENGRANTED   = '\x251909abf904fc80eac3f0d4c25e5c800441ea19fda63c6f0df08e4f24f926f9'
-- ===== Beacons / proxy admin =====
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'  -- beacon = chain-wide swap
TOPIC_OWNERSHIPTRANSFERRED    = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_ADMINCHANGED            = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_BEACONUPGRADED          = '\x1cf3b03a6cf19fa2baba4df148e9dcabedea7f8a5c07840e207e5c089be95d3e'

-- ===== Selectors =====
SEL_PR_GETALLPOOLS            = '\xd88ff1f4'
SEL_PR_GETVTOKENFORASSET      = '\x266e0a7f'
SEL_C_GETALLMARKETS           = '\xb0772d0b'
SEL_C_GETREWARDDISTRIBUTORS   = '\x61252fd1'
SEL_C_SETACTIONSPAUSED        = '\x24aaa220'
SEL_C_LIQUIDATEACCOUNT        = '\x2bce219c'
SEL_C_HEALACCOUNT             = '\x92136395'
SEL_VT_MINT                   = '\xa0712d68'
SEL_VT_REDEEM                 = '\xdb006a75'
SEL_VT_REDEEMUNDERLYING       = '\x852a12e3'
SEL_VT_BORROW                 = '\xc5ebeaec'
SEL_VT_REPAYBORROW            = '\x0e752702'
SEL_VT_LIQUIDATEBORROW        = '\xf5e3c462'
SEL_VT_FORCELIQUIDATEBORROW   = '\x8bbdb6db'
SEL_VT_HEALBORROW             = '\x44fe6ffe'
SEL_VT_ACCRUEINTEREST         = '\xa6afed95'
SEL_BEACON_IMPLEMENTATION     = '\x5c60da1b'
SEL_BEACON_UPGRADETO          = '\x3659cfe6'
SEL_RD_CLAIMREWARDTOKEN       = '\x04caeb10'
SEL_NTG_WRAPANDSUPPLY         = '\xa86f8221'

-- ===== PoolRegistry per chain =====
ETH_POOLREGISTRY   = '\x61caff113ccaf05ffc6540302c37adcf077c5179'  -- chain 1
ARB_POOLREGISTRY   = '\x382238f07bc4fe4aa99e561ade8a4164b5f815da'  -- chain 42161
OP_POOLREGISTRY    = '\x147780799840d541c1d7c998f0cba996d11d62bb'  -- chain 10
BASE_POOLREGISTRY  = '\xeef902918ddecd773d4b422aa1c6e1673eb9136f'  -- chain 8453
BNB_POOLREGISTRY   = '\x9f7b01a536afa00ef10310a162877fd792cd0666'  -- chain 56 (isolated pools only)
-- ComptrollerBeacon per chain
ETH_COMPTROLLERBEACON  = '\xae2c3f21896c02510aa187bda0791cda77083708'
ARB_COMPTROLLERBEACON  = '\x8b6c2e8672504523ca3a29a5527ecf47fc7d43fc'
OP_COMPTROLLERBEACON   = '\x64f9306496ccf7b7369d02d68d6abca2edfb871d'
BASE_COMPTROLLERBEACON = '\x1b6de1c670db291bcbf793320a42dbbd858e67ac'
BNB_COMPTROLLERBEACON  = '\x38b4efab9ea1bacd19dc81f19c4d1c2f9deae1b2'
-- VTokenBeacon per chain
ETH_VTOKENBEACON   = '\xfc08aadc7a1a93857f6296c3fb78aba1d286533a'
ARB_VTOKENBEACON   = '\xe9381d8ca7006c12ae9eb97890575e705996fa66'
OP_VTOKENBEACON    = '\xd550bdfa9402e215de0babcb99f7294be0268367'
BASE_VTOKENBEACON  = '\x87a6476510368c4bfb70d04a3b0e5a881ec7f0d1'
BNB_VTOKENBEACON   = '\x2b8a1c539abac89cbf7e2bc6987a0a38a5e660d4'
-- EIP-1967 slots
EIP1967_IMPL_SLOT   = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT  = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
EIP1967_BEACON_SLOT = '\xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50'
```

---

## 9. Verification & sources

- **Event topic0:** computed locally as `keccak256(canonical signature)` (no param names; `uint`→`uint256`; structs as nested tuples — `VenusPool`→`(string,address,address,uint256,uint256)`, `VenusPoolMetaData`→`(string,string,string)`, `Exp`→`(uint256)`), then verified against live `eth_getLogs`. On the ETH Core vToken `0x8716554364f20bca783cb2baa744d39361fd1d8d` (~50k-block window): `AccrueInterest` present with **128-byte data** (4-arg confirmed), `Mint`, `Redeem`, `ProtocolSeize`, `Transfer`. On the ETH Core RewardsDistributor `0x134bfDEa…`: `DistributedSupplierRewardToken` 37, `RewardTokenSupplyIndexUpdated` 30, `RewardTokenBorrowIndexUpdated` 17 (**struct-tuple form `0xbfeed4eb…` confirmed**, flat form absent), `DistributedBorrowerRewardToken` 15. `MarketAdded` confirmed live on the ETH PoolRegistry near block 20.15M.
- **Function selectors:** `keccak256(sig)[0:4]`; `getAllPools()` `0xd88ff1f4` and `getAllMarkets()` `0xb0772d0b` confirmed by live `eth_call` (ETH 4 pools / 23 Core markets; BNB 8 pools; ARB 2; Base 1; OP 1). `getRewardDistributors()` `0x61252fd1` confirmed (ETH Core = 3 distributors). State-changing selectors live in the impl bytecode (proxies are stubs).
- **Addresses:** parsed from `VenusProtocol/isolated-pools` `deployments/<network>_addresses.json` (`ethereum`, `arbitrumone`, `opmainnet`, `basemainnet`, `bscmainnet`) and existence-checked via `eth_getCode` on each chain's publicnode RPC. The repo has **no** Avalanche or Polygon deployment directory; `eth_getCode` returns `0x` on both chains for all 6 anchors tested (§5).
- **Proxies/beacons:** EIP-1967 impl slot read live for PoolRegistry + RewardsDistributor (populated, transparent), beacon slot read for Comptroller_Core (= ComptrollerBeacon, BeaconProxy). Beacon `implementation()` read live on all 5 chains — the `ComptrollerBeacon` impl matches the JSON, the `VTokenBeacon` impl **differs** from the JSON on ETH/ARB/OP/Base (§6.1; the JSON is a stale snapshot). Beacon `owner()`/DefaultProxyAdmin `owner()` read live (ETH = `0xd969e7…5714`; each chain has its own Timelock owner).

Authoritative sources:
- [`VenusProtocol/isolated-pools`](https://github.com/VenusProtocol/isolated-pools) — `contracts/Pool/PoolRegistry.sol` + `PoolRegistryInterface.sol`, `contracts/Comptroller.sol`, `contracts/VToken.sol` + `VTokenInterfaces.sol`, `contracts/Rewards/RewardsDistributor.sol`, `contracts/Comptroller/ComptrollerInterface.sol` (the `Action` enum), and `deployments/<network>_addresses.json` (canonical address registry).
- [Venus docs — Isolated Pools](https://docs-v4.venus.io/) and [`VenusProtocol`](https://github.com/VenusProtocol) org (the separate `venus-protocol` repo holds the BNB Core pool + shared infra: ResilientOracle, ProtocolShareReserve, AccessControlManager, Shortfall, XVS).
- Explorers: [Etherscan](https://etherscan.io/address/0x61CAff113CCaf05FFc6540302c37adcf077C5179) · [Arbiscan](https://arbiscan.io/address/0x382238f07Bc4Fe4aA99e561adE8A4164b5f815DA) · [Optimism](https://optimistic.etherscan.io/address/0x147780799840d541C1d7c998F0cbA996d11D62bb) · [Basescan](https://basescan.org/address/0xeef902918DdeCD773D4B422aa1C6e1673EB9136F) · [BscScan](https://bscscan.com/address/0x9F7b01A536aFA00EF10310A162877fd792cD0666).
