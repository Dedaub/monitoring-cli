# Fables — Topics, Selectors, Addresses (Robinhood Chain)

**Status:** verified against live Robinhood Chain RPC on 2026-10-30. Contract names and ABIs come from Sourcify full matches (chain 4663). Every topic0 and selector was recomputed locally as `keccak256(signature)`. The DefiLlama adapter `projects/fables/index.js` supplied the lead addresses.
**Scope:** Fables on **Robinhood Chain (4663)**: the pool registry, the Uniswap v4 hook contracts that hold LP positions, and the ve(3,3) layer (FABLES, veFABLES, voter, minter, epoch distributor, fee forwarders). Topics and selectors are chain-agnostic. Addresses are network-specific.

Fables is a dynamic-fee ve(3,3) DEX **built on the canonical Uniswap v4 PoolManager** of Robinhood Chain (`0x8366a39cc670b4001a1121b8f6a443a643e40951`). Fables deploys no PoolManager, no router and no quoter. Swaps go through the standard Uniswap v4 routers and emit the PoolManager `Swap` event. See [uniswap/v4.md](../uniswap/v4.md) for the PoolManager, Universal Router, PositionManager and StateView topics and selectors.

What Fables adds: each pool has `fee = 0x800000` (the v4 dynamic-fee flag) and a Fables **hook**. The hook sets the fee in `beforeSwap`. The hook also holds the LP liquidity and records each user share as an **ERC-6909 ledger balance** (`id = rangeId`). So LP deposits show as `ModifyLiquidity` with `sender = hook` on the PoolManager, plus a hook `Deposited` event that names the real user. DefiLlama reported about $24.1M TVL and $5.2M of FABLES locked in veFABLES on 2026-10-30.

---

## 0. Contract families

| Component | Contract (Sourcify name) | Role |
|-----------|--------------------------|------|
| Registry | `FablesPoolRegistry` | The list of Fables pools (`PoolKey`, `poolId`, `active`). 83 pools, all active. |
| Hooks | `FablesRamp`, `FablesRampETH`, `FablesRWA`, `FablesRWAETH` | v4 hooks. `Ramp` = crypto pools (autonomous fee + off-chain fee pokes). `RWA` = tokenized-stock pools (trading-session calendar fee). `*ETH` = native-ETH pools (wrap revenue to WETH). 13 hook instances. |
| ve layer | `FablesToken` (FABLES), `VotingEscrowFF` (veFABLES, ERC-721), `FablesVoter`, `FablesMinter`, `FablesEpochDistributor` | Lock, vote per `poolId`, mint emissions, pay rewards by Merkle root. |
| Fees | `FablesFeeForwarder` (2 instances) | Receive hook fee cuts and forward them to the distributor. |
| Access | OpenZeppelin `AccessManager` | One authority for every Fables contract (`authority()`). |

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Live counts are for Robinhood blocks 98,829,428–101,829,428 (about 3M blocks).

### 1.1 Uniswap v4 PoolManager (emitter = PoolManager, filter by `id` = Fables `poolId`)

| topic0 | Event |
|--------|-------|
| `0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f` | `Swap(bytes32 indexed id, address indexed sender, int128 amount0, int128 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick, uint24 fee)` — 17,132 for Fables pools in 400k blocks |
| `0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec` | `ModifyLiquidity(bytes32 indexed id, address indexed sender, int24 tickLower, int24 tickUpper, int256 liquidityDelta, bytes32 salt)` — 10,687 in 400k blocks |
| `0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438` | `Initialize(bytes32 indexed id, address indexed currency0, address indexed currency1, uint24 fee, int24 tickSpacing, address hooks, uint160 sqrtPriceX96, int24 tick)` |

### 1.2 FablesPoolRegistry

| topic0 | Event |
|--------|-------|
| `0x9abe929c400bdc0955113b9179784e2e5d9747937eb4e86dac71829f217c99f5` | `PoolRegistered(bytes32 indexed id, (address,address,uint24,int24,address) key, address indexed hook, uint256 index)` ✓live (13) |
| `0x91d5ed0d1bdfd49e256786ea549cd30e04126c3aee3a4e57ffc47723359719f6` | `PoolDeregistered(bytes32 indexed id)` |
| `0x77294d7b30249fe03623da9c9f9145fab3f4135173e5ec14543307953ba98847` | `PoolReregistered(bytes32 indexed id)` |
| `0x2f658b440c35314f52658ea8a740e05b284cdc84dc9ae01e891f21b8933e7cad` | `AuthorityUpdated(address authority)` (OZ AccessManaged; every Fables contract) |

### 1.3 Hooks — events common to all 13 hooks (counts from the main `FablesRamp` hook `0x08e5…a080`)

| topic0 | Event |
|--------|-------|
| `0x1101ae99036692e99100b857ab62c3fcdac65cfdc42b08739812e2e2bbaec38a` | `Deposited(address indexed owner, uint256 indexed rangeId, uint128 liquidity)` ✓ 6,605 |
| `0x07b03e311473c1939a1fefecdf08517eedbe848e20a7d5f4ac265ec4bae8c7a0` | `Withdrawn(address indexed owner, uint256 indexed rangeId, uint128 liquidity)` ✓ 4,407 |
| `0x5f1526e127c2ae64abea3117909f2c3ba68d66b293ec1256c0c0025cf7ade21a` | `Staked(address indexed owner, uint256 indexed rangeId, uint128 shares)` ✓ 5,831 |
| `0x3f58555a19e04d0ac05f036e483136cdab4628e29210be59809a5184983057b6` | `Unstaked(address indexed owner, uint256 indexed rangeId, uint128 shares)` ✓ 4,228 |
| `0xd49b328847f240dd41d9f8a97b5334cb8d06f55e51ce78bacd364d5c62136d77` | `FeesClaimed(address indexed owner, uint256 indexed rangeId, uint256 amount0, uint256 amount1)` ✓ 986 |
| `0x7f46856fb5c40ab4d199da368381e12a4f3f4a36b31979b75fb0857d75d5ea7d` | `FeesForgone(address indexed owner, uint256 indexed rangeId, uint256 amount0, uint256 amount1)` ✓ 4,990 |
| `0x9e834ab6101f9c499217a2a750235dc43735a65c69369e5f54810a468df96309` | `FeesCollected(uint256 indexed rangeId, uint256 fee0, uint256 fee1, uint256 stakedCut0, uint256 stakedCut1, uint256 accStaked0X128, uint256 accStaked1X128, uint256 feeGrowthInside0X128, uint256 feeGrowthInside1X128, uint128 totalShares, uint128 totalStaked, uint64 collectionSeq, uint64 resetSeq)` ✓ 9,951 |
| `0x1b3d7edb2e9c0b0e7c525b20aaaef0f5940d2ed71663c7d39266ecafac728859` | `Transfer(address caller, address indexed from, address indexed to, uint256 indexed id, uint256 amount)` (ERC-6909 LP share) ✓ 12,234 |
| `0xb3fd5071835887567a0671151121894ddccc2842f1d10bedad13e0d17cace9a7` | `Approval(address indexed owner, address indexed spender, uint256 indexed id, uint256 amount)` (ERC-6909) ✓ 530 |
| `0xceb576d9f15e4e200fdb5096d64d5dfd667e16def20c1eefd14256d8e3faa267` | `OperatorSet(address indexed owner, address indexed operator, bool approved)` (ERC-6909) |
| `0x8433fc399fe390949e8c0e579efdbdbe6d00502e208f6aaa46e22036e0808664` | `ClaimFeeSwept(address indexed currency, address indexed recipient, uint256 amount)` ✓ 32 |
| `0x3f9fbb29ea290941cbe721706cd11b2bc9fc665269cf4d992c1cdd0168a82cb8` | `DistributorSwept(address indexed currency, address indexed distributor, uint256 amount)` ✓ 26 |
| `0x18cc76435a425170cbce2e796e856f6d0e03afce7351c7cad2368098d79df921` | `PausedSet(uint256 pausedUntil)` (global hook pause) |
| `0xb8fae5f44b3e1ea6cb10a6d677d5a9441301da4f60509c3ecccf8c67d34a50cb` | `PokeCleared(bytes32 indexed poolId)` |
| `0x86719c518c7d99ac94b3d405d462ea876ba5cd0a978461dc9a7c9862a9485886` | `DistributorSet(address distributor)` |
| `0x479dc00e1bc56599c64530e9d4b65a83aeec94a50320dcc036d4e6c656d06834` | `FFFeeSinkSet(address sink)` |
| `0xc80643d3134fd859c3f5fd2eccd8829c819d3d91c4fe8b44fd79a1b549b2f6ba` | `BallotGateSet(address gate)` |

### 1.4 Hooks — variant-specific events

The hook versions differ. The same event name can have two signatures. Match on topic0, not on the name.

| topic0 | Event | Emitted by |
|--------|-------|-----------|
| `0x3b158a8283be40bf4eb77d5d4ede4264472c14a6904cf6161876e3e32c98ce28` | `FeePoked(bytes32 indexed poolId, uint24 fee0For1, uint24 fee1For0, uint40 expiry)` ✓ 3,572 | Ramp, RampETH, newer RWA |
| `0xcb123ffca193ebeb3d5c30d267785371dd417ff0084b636bff5d03f87a2c8e04` | `FeePoked(bytes32 indexed poolId, uint24 fee, uint40 expiry)` | older RWA (`0x70a9…`, `0x6662…`, `0x67d8…`, `0x7957…`, `0xa0e8…`) |
| `0x4ef23c92213fa77da668c26624a4b496ed797ab0096546cdf20fa4cb58a1fee1` | `ClaimFeeAccrued(uint256 indexed rangeId, bytes32 indexed poolId, uint256 cut0, uint256 cut1, uint16 feeBps)` ✓ 1,628 | Ramp, RampETH, newer RWA |
| `0xea03c9bf61fc7370359a829e51d04655e8f14f3050893234528a8beee9085ad9` | `ClaimFeeSet(bytes32 indexed poolId, uint16 bps, address recipient)` ✓ 12 | per-pool claim fee hooks |
| `0x0b65005dca60b48350109d190e3b76d743e84c39c00cc378a5a9af1770570c87` | `ClaimFeeSet(uint16 bps, address recipient)` | single-pool RWA hooks |
| `0x0cd5d07754e72da6a4377b10c0e71af087f26ee3d83fe1477267deb81b4a9fd5` | `PoolConfigured(bytes32 indexed poolId, uint24 floorPips, uint24 flatPips, uint24 maxFee)` ✓ 13 | Ramp, RampETH |
| `0x2e9273ab7229fcfc198610765943b0b1e1c7ad733c971f27143736d7e210dd2d` | `PoolConfigured(bytes32 indexed poolId, (uint24,uint24,uint24,uint8,uint24,uint32,uint24,uint32,uint32) config, uint24 maxFee)` | RWA, RWAETH |
| `0x36922399b38aaeb027c5fb2231292adf37f11b1eabe65fccbc495b366247c250` | `PoolAsymmetrySet(bytes32 indexed poolId, uint24 premiumPips, bool premiumZeroForOne)` ✓ 4 | Ramp, RampETH, newer RWA |
| `0x22caacf1c576838290098917f488ecf641a5562cc4011a665c97370a5121ea46` | `PoolPausedSet(bytes32 indexed poolId, uint256 pausedUntil)` | Ramp, RampETH, newer RWA |
| `0x7dbc129f8fa132d69d0cce2c71382c1d1790ee0c5d6da4c96dba6421e64f5cd8` / `0xc499af564f2e96f7faf73e76a93ed5556b7ab16625001f103b97c3f503479598` | `SessionHoursSet(bytes32 indexed poolId, uint32 openSec, uint32 closeSec)` / `SessionHoursSet(uint32,uint32)` | multi-pool RWA / single-pool RWA |
| `0x7ee217ba7939dd2377368ab32115877fec94476d981711560e7b2ef413d230d2` / `0xe7265b39a4a53e8652bdbd7577f2f10449d3874f62e791d61366078732046929` | `DayOverridesSet(bytes32 indexed poolId, uint256 indexed yearMonth, uint64 packed)` / `DayOverridesSet(uint256 indexed yearMonth, uint64 packed)` | multi-pool RWA / single-pool RWA |
| `0x874f6d6183599062bc3c38b7a06820baae673a9307def6cdcbec7a29cb9de72b` / `0xb8d4add2ca9beaea86202e9751902c310f503b481d19557a5797a49584eb0769` | `DstModeSet(bytes32 indexed poolId, uint8 mode)` / `DstModeSet(uint8 mode)` | multi-pool RWA / single-pool RWA |
| `0x71464d15f1f91b439ff0bffe131c2fc118a7170647c7e120ca8c77e2be2f0cde` | `EarlyCloseSet(bytes32 indexed poolId, uint256 y, uint256 m, uint256 d, uint32 closeSec)` | multi-pool RWA |
| `0xa9386908a432ae7823cdf0214a4381c3d80c5707f3edeb94416a11d1b1653d96` | `NativeClaimFeeWrappedToWeth(address indexed recipient, address indexed weth, uint256 amount)` | RampETH, RWAETH |
| `0xb915276e16976fd3b4e49e091fe1539cab0a415c09ff28c734fb2170badc546e` | `NativeRevenueWrappedToWeth(address indexed distributor, address indexed weth, uint256 amount)` | RampETH, RWAETH |

### 1.5 ve layer

| topic0 | Event | Contract |
|--------|-------|----------|
| `0xd815d089ba93cb7069ced8c0b3849ca417b44735e6c0aa9bf217a8161c08d44d` | `Locked(uint256 indexed tokenId, address indexed owner, uint128 amount, uint64 unlock)` ✓ 146 | veFABLES |
| `0xbb9dfc6e029e2067a2f500c8741eac58bc4a98f98531274b95c22ff80facf76e` | `AmountIncreased(uint256 indexed tokenId, uint128 added)` ✓ 344 | veFABLES |
| `0xb5b0df70e0f6baaed19a599e1fff13cff144032650517c51d04d1203fe0a1981` | `DepositedFor(uint256 indexed tokenId, address indexed from, uint128 added)` ✓ 234 | veFABLES |
| `0x6546e7442217f0a987e7c46ca6eb93a6c175429ba2a00b7fd369d4007c87d36e` | `UnlockExtended(uint256 indexed tokenId, uint64 unlock)` ✓ 33 | veFABLES |
| `0x42c1d882168103cddea25afc01d2cd3ff5ce7bc41a3f40a81402194e2f046204` | `Merged(uint256 indexed from, uint256 indexed to, uint128 amount)` ✓ 23 | veFABLES |
| `0xa8fd4d72a84ed56a19d17cf9519f191d360e6c5026fa38bca2c361e46e144194` | `Split(uint256 indexed from, uint256 indexed to, uint128 amount)` | veFABLES |
| `0xb93f113f5e0a7c68a43c460680b35445bae4edb7ec7cf0b850491f990efd254e` | `Withdrawn(uint256 indexed tokenId, address indexed owner, uint128 amount)` | veFABLES |
| `0x5bb4a0f5a67f7c49cfc7820adfab4690a3752cf969544ddd8445b970d3643e89` | `VoterSet(address indexed voter)` | veFABLES |
| `0xff548e1baccbb09b8bc1f9082e496bd6717a4c9dd2c54b2866895280d41a8da8` | `Voted(uint256 indexed tokenId, address indexed owner, uint128 amount, uint64 unlock, bytes32[] pools, uint16[] weightsBps, uint256 at, uint64 seq)` ✓ 535 | FablesVoter |
| `0x3c2753b24120ef1a266cc5f004c411586205014eb30cb6fed172a3a7fadc4e31` | `Poked(uint256 indexed tokenId, address indexed owner, uint128 amount, uint64 unlock, bytes32[] pools, uint16[] weightsBps, uint256[] slopes, uint256 at, uint64 seq)` ✓ 366 | FablesVoter |
| `0x9940993d1d628ca7a08ce839b82443df78752e85a7073b9c2cfbd3b8e3be94c2` | `GaugeCheckpoint(bytes32 indexed poolId, uint256 indexed epoch, uint256 votes)` ✓ 2,481 | FablesVoter |
| `0xf71f3a7088d3a085c853d905fd7f5efe186dcf95651772202c4223f19ad99831` | `BallotReset(uint256 indexed tokenId, uint256 at, uint64 seq)` ✓ 24 | FablesVoter |
| `0x6766e4e3ef04a01c8adfa5c8eef504888ac3ab1d0b815e52d884ae40da21cb79` | `GaugeAdded(bytes32 indexed poolId, uint8 class_)` | FablesVoter |
| `0xc1b22c712ff20bd2e228a5a78fbd47016a48975475df48e019946baabacbd9a4` | `GaugeEmergencyKilled(bytes32 indexed poolId, uint256 fromEpoch)` | FablesVoter |
| `0x3e1c0ef999eb564514e3f9d03e829907316fbc21719b272fe8e7a787234f9d2f` | `GaugeRetired(bytes32 indexed poolId, uint256 fromEpoch)` | FablesVoter |
| `0x4eac61fdb0ff5f7e682c98740974ea91081deb1b92673fcc89ed0ef87391a354` | `GaugeRevived(bytes32 indexed poolId, uint256 fromEpoch)` | FablesVoter |
| `0x3c864541ef71378c6229510ed90f376565ee42d9c5e0904a984a9e863e6db44f` | `TreasurySet(address treasury)` | FablesVoter |
| `0xbb1f7005d47915944d6441dc76099cd374cb2db487876e339c35b6629256c086` | `Minted(uint8 indexed allocation, address indexed to, uint256 amount, address indexed by)` ✓ 2,432 | FablesMinter |
| `0x75f19c4249d67363a189402d4276bf08d70b75288fe32dea6430169e8125ca11` | `MintScheduled(uint256 indexed id, uint8 indexed allocation, address indexed to, uint256 amount, uint256 readyAt)` | FablesMinter |
| `0x378d1092e9c40008a0c34a362b617f864c8f470eabd74ba1958e40286f2ea274` | `MinterAdded(uint8 indexed allocation, address indexed minter)` | FablesMinter |
| `0xba9bda665753f9ab44e20a116466bb90eff7f637c55943e05b6379779f963c47` | `MinterChangeScheduled(uint8 indexed allocation, address indexed minter, uint256 readyAt)` | FablesMinter |
| `0x726b590ef91a8c76ad05bbe91a57ef84605276528f49cd47d787f558a4e755b6` | `MinterSet(address indexed minter)` | FablesToken |
| `0xce3bcb6e219596cf26007ffdfaae8953bc3f76e3f36c0a79b23e28020da3222e` | `Claimed(uint256 indexed epoch, address indexed account, address indexed token, uint256 amount)` ✓ 2,068 | FablesEpochDistributor |
| `0xd42cf87b4a9a9e20b382a226cdc71f4718f4099c8b55d79a0916ccaf0e821800` | `RootPosted(uint256 indexed epoch, bytes32 root)` ✓ 1 | FablesEpochDistributor |
| `0x9736ce24c60a887deab06513ee89b9e324496e545bcc950b8a2174daa8fc701c` | `AllotmentSet(uint256 indexed epoch, address indexed token, uint256 amount)` ✓ 54 | FablesEpochDistributor |
| `0xa9ec7c036797807fad56efa080fe0aef194aebe10d0843ef02c3741293ba0a13` | `RescueProposed(address indexed token, uint256 readyAt, uint256 snapshot)` | FablesEpochDistributor |
| `0x74f603fb464a7177372afe9b800015416c6089058a9bb9317ac0234bf8c0bae6` | `ExcessRescued(address indexed token, address indexed to, uint256 amount)` | FablesEpochDistributor |
| `0x0571d85fc9cce8d2ebf18e983becef6cc884e37503f377f9b6383d65850f96d2` | `Forwarded(address indexed token, address indexed distributor, uint256 amount)` | FablesFeeForwarder |

FABLES and veFABLES also emit the standard ERC-20 / ERC-721 `Transfer` (`0xddf252ad…`) and `Approval` (`0x8c5be1e5…`).

## 2. Function signatures (chain-agnostic)

### 2.1 Hooks (user and admin entry points)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x36a9ca1a` | `deposit((address,address,uint24,int24,address),int24,int24,uint128,uint128,uint128,uint256)` | Add liquidity. `payable` on ETH hooks. Emits `Deposited` + ERC-6909 `Transfer`. |
| `0xa2ba1fc8` | `withdraw((address,address,uint24,int24,address),int24,int24,uint128,address,uint128,uint128,uint256)` | Remove liquidity. Emits `Withdrawn`. |
| `0x289a2a15` | `withdrawAndClaim(…,uint16)` | Ramp / RampETH / newer RWA only. |
| `0x6fa9f5ca` / `0x5ca34469` | `stake(key,int24,int24,uint128,uint256)` / `stake(key,int24,int24,uint128)` | Two shapes by hook version. Emits `Staked`. |
| `0xdaf58566` | `unstake((address,address,uint24,int24,address),int24,int24,uint128)` | Emits `Unstaked`. |
| `0x4e8d0048` | `claimFees((address,address,uint24,int24,address),int24,int24,address,uint16)` | Emits `FeesClaimed`. |
| `0x095bcdb6` / `0xfe99049a` | `transfer(address,uint256,uint256)` / `transferFrom(address,address,uint256,uint256)` | ERC-6909 LP-share moves. |
| `0x3f740010` / `0x8aebf0c1` | `pokeFee(bytes32,uint24,uint24,uint40)` / `pokeFee(bytes32,uint24,uint40)` | Off-chain fee override (authority-gated). |
| `0x4dc4b5c9` / `0xe8fe08b8` | `setPoolConfig(key,uint24,uint24,uint24)` / `setPoolConfig(key,(…9 fields…),uint24)` | Fee-curve change (admin). |
| `0x51789ea2` / `0x136439dd` / `0x016b937e` | `setPaused(uint256)` / `pause(uint256)` / `pausePool(key,uint256)` | Pause (admin). |
| `0xd0ba2baa` / `0x26f5ef52` | `setDistributor(address[],address)` / `setFFFeeSink(address[],address)` | Revenue routing change (admin). |
| `0xab9e5bfd` / `0xbdde80c6` | `sweepClaimFee(address)` / `sweepDistributor(address)` | Move accrued fee cuts out of the hook. |
| `0x575e24b4` / `0xdc98354e` | `beforeSwap(…)` / `beforeInitialize(…)` | Called by the PoolManager only. |
| `0x91dd7346` | `unlockCallback(bytes)` | Called by the PoolManager only. |

### 2.2 Registry, ve layer

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x2247b655` / `0x20813154` / `0xcde5f9fc` | `register(key)` / `deregister(bytes32)` / `reregister(bytes32)` | Registry (admin) |
| `0x52f72fe6` / `0xc5c63e65` / `0xf525cb68` | `activePools()` / `allPools()` / `poolCount()` | Registry (views) |
| `0x3527d1c0` / `0x2fbb4fb0` | `createLock(uint128,uint256)` / `createLockFor(address,uint128,uint256)` | veFABLES |
| `0x143b40de` / `0xb1dc6dc0` | `createPermanentLock(uint128)` / `createPermanentLockFor(address,uint128)` | veFABLES |
| `0x929edf45` / `0xdb53f731` / `0xc041999d` | `increaseAmount(uint256,uint128)` / `depositFor(uint256,uint128)` / `extendUnlock(uint256,uint256)` | veFABLES |
| `0xd1c2babb` / `0xc05c2ffc` / `0x2e1a7d4d` | `merge(uint256,uint256)` / `split(uint256,uint128)` / `withdraw(uint256)` | veFABLES |
| `0xe75b1c2e` / `0x35b0f6bd` | `lockPermanent(uint256)` / `unlockPermanent(uint256)` | veFABLES |
| `0xf5892f6b` / `0x310bd74b` | `vote(uint256,bytes32[],uint16[])` / `reset(uint256)` | FablesVoter |
| `0x4fc82135` / `0x5506394f` / `0x06ef3ed2` / `0x591e5582` | `addGauge(bytes32,uint8)` / `emergencyKillGauge(bytes32)` / `retireGauge(bytes32)` / `reviveGauge(bytes32)` | FablesVoter (admin) |
| `0xeebab8ef` / `0x9f5152af` / `0x27d6adc7` / `0xe7a486fb` | `mint(uint8,address,uint256)` / `mintEmission(address,uint256)` / `scheduleMint(uint8,address,uint256)` / `executeMint(uint256)` | FablesMinter |
| `0xf0f7df9c` / `0x11d7eb61` | `claim(uint256,address,address,uint256,bytes32[])` / `postRoot(uint256,bytes32,address[],uint256[],(bytes32,address,uint256)[])` | FablesEpochDistributor |
| `0x101e8952` / `0x72e3a303` | `forward(address)` / `sweepAndForward(address[],address,bool)` | FablesFeeForwarder |
| `0x7a9e5e4b` | `setAuthority(address)` | every Fables contract |

---

## 3. Addresses — Robinhood Chain (chain ID 4663)

All verified via `eth_getCode` on `https://robinhood-rpc.publicnode.com` on 2026-10-30. Names are the Sourcify contract names. None of the contracts is a proxy (EIP-1967 impl slot empty).

| Role | Address | Size | Notes |
|------|---------|------|-------|
| **FablesPoolRegistry** | `0x159a113e012593d9b3cc63ad45e30f0467e13ef3` | 3726 B | `poolCount()` = 83; all 83 active. |
| **FablesRamp** (main hook) | `0x08e52564bad99e05a694b4809f397edca417a080` | 32997 B | 51 pools (USDG / frxUSD pairs). |
| FablesRampETH | `0x594e8e6281edf2d363a0293a50004cf868e7a080` | 34326 B | 10 native-ETH pools. `weth()` = `0x0bd7d308…` |
| FablesRampETH | `0x06a889870c8f83640d6816319f72e2aa579b6080` | 28189 B | ETH/USDG. The largest `ModifyLiquidity` sender. |
| FablesRWA (multi-pool) | `0x5eb87f69be00df39981622fd60a8de4b7837e080` | 42039 B | 11 stock pools (AMZN, COIN, PLTR, MSTR, …). |
| FablesRWAETH | `0xca89f079af00f752bfd3c345358dc38d4d73e080` | 43368 B | ETH/SPY, ETH/AMC. |
| FablesRWA (single-pool) | `0x8af95932ec4484fb10c641a4cbcf19a798cb2080` (META), `0xa4570c37590e45f0b06898123d4de16307a32080` (SPY/GLD), `0xb608a78761f179f7c56f15e7d13921b92f00a080` (GLD) | 35868 B | |
| FablesRWA (single-pool, older) | `0x70a9a88402989226847ec122043ce5e7ff462080` (AAPL), `0x79576fbad6e83915630bbb5d5658483f05532080` (SPY/NVDA), `0x67d86050d22d574df046f3d90f722045f714e080` (TSLA) | 34388 B | |
| FablesRWA (single-pool, older) | `0x66622f77b797d506e5376f7798b67ab288966080` (NVDA), `0xa0e8fbff13e24af2b5e61a72800e08a161bde080` (SPY/USDG) | 33070 B | |
| **FablesToken** (FABLES) | `0xb63d07cef74be747231d601bb2faa6b252c68106` | 4490 B | 18 dec; supply 142.2M on 2026-10-30. `minter()` = FablesMinter. |
| **VotingEscrowFF** (veFABLES) | `0xc1d5adc963a57d24adaf63aae1bfbecab95f6edd` | 14062 B | ERC-721 locks. `voter()` = FablesVoter. |
| **FablesVoter** | `0x71570b34d9200ffe5c3066f5a204f91229e7338e` | 15760 B | Gauges keyed by `poolId` (no gauge contracts). `gaugeCount()` = 49. `treasury()` = `0x385bc909…` |
| FablesMinter | `0x3c1672c615ef1f966a1cbcc37f924586a5a3d422` | 9928 B | |
| FablesEpochDistributor | `0x498506256215702f0da01c0f9ab0c765488acd07` | 14103 B | Hook `distributor()`. Merkle claims. |
| FablesFeeForwarder (FF fee sink) | `0x85f3af4780fabdc54b54ecd5fe7045cd5627c52f` | 2183 B | Hook `ffFeeSink()`. |
| FablesFeeForwarder (claim-fee recipient) | `0x71ec190f76762f824407aeb2d244dc120c48262d` | 2183 B | Hook `claimFeeRecipient()`. |
| AccessManager | `0xa362d98b33a7bb5b5e2180a05f995a70fb404f30` | 10458 B | `authority()` of every contract above. |
| Voter treasury | `0x385bc909ca7efd34788216ea97346d3ba75c94de` | 123 B | Safe-style proxy (`masterCopy()` = `0xedd160fe…`). |
| Uniswap v4 PoolManager (shared) | `0x8366a39cc670b4001a1121b8f6a443a643e40951` | — | Read from every hook `poolManager()`. Not a Fables contract. |

The DefiLlama adapter reads TVL through the shared Uniswap v4 StateView `0xF3334192D15450CdD385c8B70e03f9A6bD9E673b`.

## 4. Cross-chain summary

| Chain | ID | Fables |
|-------|----|--------|
| Robinhood Chain | 4663 | ✓ all contracts in §3 |
| Ethereum / Base / BNB / Avalanche / Arbitrum / Optimism / Polygon / Arc | — | — (the registry, hook, FABLES, veFABLES and voter addresses return `0x` on all eight) |

## 5. Proxies & admin

| Contract | Pattern | Upgrade / admin auth |
|----------|---------|----------------------|
| All Fables contracts | Immutable (EIP-1967 impl slot = 0) | Config changes are gated by the OZ `AccessManager` `0xa362…4f30` |
| AccessManager `ADMIN_ROLE` (role 0) | — | Granted to `0x359856655934338d798f9cce1f181486301d36a5` (an EIP-7702 delegated EOA, 23 B code) at block 37,250,998 |

Other roles were granted to EOAs (role 1 → `0xb9e8db60…`, `0x1b6a8808…`, `0x014f37fa…`; role 3/7 → `0x77c7634a…`; role 13 → `0x215f1598…`, a 123 B Safe-style proxy). Watch `RoleGranted` `0xf98448b987f1428e0e230e1f3c6e2ce15b5693eaf31827fbd0b1ec4b424ae7cf` on the AccessManager.

## 6. Detection invariants & gotchas

1. **Swaps are on the PoolManager, not on Fables.** Filter PoolManager `Swap` by `topic1 ∈ {Fables poolIds}` (from `activePools()` or `PoolRegistered`). The hook emits no swap event.
2. **The real LP is in the hook event.** PoolManager `ModifyLiquidity.sender` is the hook. Use hook `Deposited` / `Withdrawn` (`owner` = user). Some LPs bypass the hook through the standard v4 PositionManager (`0x58da…4fA7`, 393 of 10,687 `ModifyLiquidity` in 400k blocks). The hooks only set `beforeInitialize` + `beforeSwap` flags, so they do not gate liquidity.
3. **LP shares are ERC-6909 tokens on the hook.** The hook `Transfer` (`0x1b3d7edb…`) has a 5-field layout. It is not the ERC-20 `Transfer`.
4. **Same name, different topic0.** `FeePoked`, `PoolConfigured`, `ClaimFeeSet`, `SessionHoursSet`, `DayOverridesSet` and `DstModeSet` have two signatures each across hook versions. Track both.
5. **Fee is dynamic.** Every `PoolKey.fee` is `0x800000`. The real fee is in the PoolManager `Swap.fee` field. RWA hooks raise fees outside stock-market sessions (calendar, DST and early-close overrides).
6. **Gauges have no contract.** `FablesVoter` keys gauges by `poolId`. Rewards pay out through Merkle roots on the `FablesEpochDistributor` (`RootPosted`, `Claimed`).
7. **Single admin key.** The AccessManager admin is one EIP-7702 EOA. A `setDistributor` / `setFFFeeSink` call can redirect all hook revenue. Alert on those selectors and on `DistributorSet` / `FFFeeSinkSet`.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_V4_SWAP                  = '\x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f'
TOPIC_V4_MODIFY_LIQUIDITY      = '\xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec'
TOPIC_FAB_POOL_REGISTERED      = '\x9abe929c400bdc0955113b9179784e2e5d9747937eb4e86dac71829f217c99f5'
TOPIC_FAB_DEPOSITED            = '\x1101ae99036692e99100b857ab62c3fcdac65cfdc42b08739812e2e2bbaec38a'
TOPIC_FAB_WITHDRAWN            = '\x07b03e311473c1939a1fefecdf08517eedbe848e20a7d5f4ac265ec4bae8c7a0'
TOPIC_FAB_STAKED               = '\x5f1526e127c2ae64abea3117909f2c3ba68d66b293ec1256c0c0025cf7ade21a'
TOPIC_FAB_UNSTAKED             = '\x3f58555a19e04d0ac05f036e483136cdab4628e29210be59809a5184983057b6'
TOPIC_FAB_FEES_CLAIMED         = '\xd49b328847f240dd41d9f8a97b5334cb8d06f55e51ce78bacd364d5c62136d77'
TOPIC_FAB_6909_TRANSFER        = '\x1b3d7edb2e9c0b0e7c525b20aaaef0f5940d2ed71663c7d39266ecafac728859'
TOPIC_FAB_FEE_POKED_2          = '\x3b158a8283be40bf4eb77d5d4ede4264472c14a6904cf6161876e3e32c98ce28'
TOPIC_FAB_FEE_POKED_1          = '\xcb123ffca193ebeb3d5c30d267785371dd417ff0084b636bff5d03f87a2c8e04'
TOPIC_FAB_DISTRIBUTOR_SET      = '\x86719c518c7d99ac94b3d405d462ea876ba5cd0a978461dc9a7c9862a9485886'
TOPIC_FAB_FF_FEE_SINK_SET      = '\x479dc00e1bc56599c64530e9d4b65a83aeec94a50320dcc036d4e6c656d06834'
TOPIC_FAB_PAUSED_SET           = '\x18cc76435a425170cbce2e796e856f6d0e03afce7351c7cad2368098d79df921'
TOPIC_VEFAB_LOCKED             = '\xd815d089ba93cb7069ced8c0b3849ca417b44735e6c0aa9bf217a8161c08d44d'
TOPIC_VEFAB_WITHDRAWN          = '\xb93f113f5e0a7c68a43c460680b35445bae4edb7ec7cf0b850491f990efd254e'
TOPIC_FAB_VOTED                = '\xff548e1baccbb09b8bc1f9082e496bd6717a4c9dd2c54b2866895280d41a8da8'
TOPIC_FAB_MINTED               = '\xbb1f7005d47915944d6441dc76099cd374cb2db487876e339c35b6629256c086'
TOPIC_FAB_EPOCH_CLAIMED        = '\xce3bcb6e219596cf26007ffdfaae8953bc3f76e3f36c0a79b23e28020da3222e'
TOPIC_FAB_ROOT_POSTED          = '\xd42cf87b4a9a9e20b382a226cdc71f4718f4099c8b55d79a0916ccaf0e821800'
TOPIC_AM_ROLE_GRANTED          = '\xf98448b987f1428e0e230e1f3c6e2ce15b5693eaf31827fbd0b1ec4b424ae7cf'
-- ===== Selectors =====
SEL_FAB_DEPOSIT                = '\x36a9ca1a'
SEL_FAB_WITHDRAW               = '\xa2ba1fc8'
SEL_FAB_CLAIM_FEES             = '\x4e8d0048'
SEL_FAB_SET_DISTRIBUTOR        = '\xd0ba2baa'
SEL_FAB_SET_FF_FEE_SINK        = '\x26f5ef52'
SEL_VEFAB_CREATE_LOCK          = '\x3527d1c0'
SEL_FAB_VOTE                   = '\xf5892f6b'
-- ===== Robinhood Chain (4663) =====
ROBIN_FAB_REGISTRY             = '\x159a113e012593d9b3cc63ad45e30f0467e13ef3'
ROBIN_FAB_HOOK_RAMP            = '\x08e52564bad99e05a694b4809f397edca417a080'
ROBIN_FAB_HOOK_RAMP_ETH        = '\x594e8e6281edf2d363a0293a50004cf868e7a080'
ROBIN_FAB_HOOK_RAMP_ETH_USDG   = '\x06a889870c8f83640d6816319f72e2aa579b6080'
ROBIN_FAB_HOOK_RWA_MULTI       = '\x5eb87f69be00df39981622fd60a8de4b7837e080'
ROBIN_FAB_HOOK_RWA_ETH         = '\xca89f079af00f752bfd3c345358dc38d4d73e080'
ROBIN_FAB_TOKEN                = '\xb63d07cef74be747231d601bb2faa6b252c68106'
ROBIN_FAB_VE                   = '\xc1d5adc963a57d24adaf63aae1bfbecab95f6edd'
ROBIN_FAB_VOTER                = '\x71570b34d9200ffe5c3066f5a204f91229e7338e'
ROBIN_FAB_MINTER               = '\x3c1672c615ef1f966a1cbcc37f924586a5a3d422'
ROBIN_FAB_EPOCH_DISTRIBUTOR    = '\x498506256215702f0da01c0f9ab0c765488acd07'
ROBIN_FAB_ACCESS_MANAGER       = '\xa362d98b33a7bb5b5e2180a05f995a70fb404f30'
ROBIN_V4_POOL_MANAGER          = '\x8366a39cc670b4001a1121b8f6a443a643e40951'
```

The ten single-pool RWA hooks are in §3. Build the full hook list from `activePools()` (`PoolKey.hooks`) or from `PoolRegistered.hook`.

## 8. Verification & sources

- **Contracts:** names and ABIs from Sourcify full matches (creation + runtime) for every address in §3 except the treasury Safe. Wiring read live: hook `poolManager()`, `authority()`, `distributor()`, `distributorFF()`, `ffFeeSink()`, `claimFeeRecipient()`, `ballotGate()`, `weth()`; `VotingEscrowFF.voter()`; `FablesVoter.ve()`, `treasury()`, `gaugeCount()`; `FablesToken.minter()`; registry `activePools()` / `allPools()` / `poolCount()`.
- **Topics / selectors:** recomputed locally from the Sourcify ABIs. Live `eth_getLogs` via `https://rpc.mainnet.chain.robinhood.com` (the publicnode endpoint rejects log ranges). Fables pool `Swap` / `ModifyLiquidity` counted on the PoolManager with a `poolId` topic filter.
- **Chain coverage:** `eth_getCode` on all nine public RPCs; code only on Robinhood Chain.
- **TVL:** `api.llama.fi/protocol/fables` (Robinhood Chain 24,071,617 USD; staking 5,162,766 USD on 2026-10-30).

Sources:
- [Sourcify](https://sourcify.dev) — verified sources for chain 4663.
- [DefiLlama adapter `projects/fables/index.js`](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/fables/index.js) · [DefiLlama Fables](https://defillama.com/protocol/fables)
- [Fables](https://www.fables.fi/) · [IQ.wiki Fables](https://iq.wiki/wiki/fables)
- [`Uniswap/v4-core`](https://github.com/Uniswap/v4-core) — PoolManager signatures.
