# Topaz v3 / Slipstream (Concentrated Liquidity) — Compressed Reference (BNB Chain, id 56)

**Status:** topic0/selectors keccak'd from `topazdex/topaz-slipstream` source; addresses + wiring re-verified on-chain vs `bsc-rpc.publicnode.com` on 2026-06-05.
**Scope:** the **Uniswap-V3-style concentrated-liquidity** product (an **Aerodrome Slipstream fork**): CLFactory, CLPool, CLGauge, NonfungiblePositionManager, SwapRouter, quoters, fee modules. The **ve(3,3) governance is shared** with v2 and documented in [`amm.md`](amm.md) (one `Voter`/`VotingEscrow`/`Minter` back both products). Topaz is BNB-only.
**Key facts:** CL **events are byte-identical to Uniswap V3** — disambiguate Topaz by pool provenance, not topic0. CL keys pools by **`tickSpacing`** (default fee derived), so `PoolCreated` and the struct-bearing selectors (`mint`, `exactInputSingle`, …) **differ from Uniswap V3**. CL pools **and** CLGauges are **EIP-1167 clones**.

---

## 1. Topics (chain-agnostic)

### 1.1 CLPool — core events IDENTICAL to Uniswap V3 (see [`uniswap/v3.md`](../uniswap/v3.md) §1.1)
```
0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67 -> Swap(address sender, address recipient, int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)  ✓live
0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde -> Mint(address sender, address owner, int24 tickLower, int24 tickUpper, uint128 amount, uint256 amount0, uint256 amount1)  ✓live
0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c -> Burn(address owner, int24 tickLower, int24 tickUpper, uint128 amount, uint256 amount0, uint256 amount1)  ✓live
0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0 -> Collect(address owner, address recipient, int24 tickLower, int24 tickUpper, uint128 amount0, uint128 amount1)  ✓live
0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633 -> Flash(address sender, address recipient, uint256 amount0, uint256 amount1, uint256 paid0, uint256 paid1)
0x98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95 -> Initialize(uint160 sqrtPriceX96, int24 tick)
0xac49e518f90a358f652e4400164f05a5d8f7e35e7747279bc3a93dbf584e125a -> IncreaseObservationCardinalityNext(uint16 old, uint16 new)
0x973d8d92bb299f4af6ce49b52a8adb85ae46b9f214c4c4fc06ac77401237b133 -> SetFeeProtocol(uint8,uint8,uint8,uint8)
```

### 1.2 CLPool — Slipstream-specific
```
0x205860e66845f2bbc0966bfab80db9bf93fca93862ea2b9fcf6945748352b4a3 -> CollectFees(address recipient, uint128 amount0, uint128 amount1)   [gauge/unstaked-fee collection — NOT the LP Collect above]
```

### 1.3 CLFactory
```
0xab0d57f0df537bb25e80245ef7748fa62353808c54d6e528a9dd20887aed9ac2 -> PoolCreated(address token0, address token1, int24 tickSpacing, address pool)   [token0,token1,tickSpacing indexed — Slipstream layout, NOT Uni V3's (token0,token1,fee,tickSpacing,pool) 0x783cca1c…]
0xebafae466a4a780a1d87f5fab2f52fad33be9151a7f69d099e8934c8de85b747 -> TickSpacingEnabled(int24 tickSpacing, uint24 fee)   [both indexed]
0xd444e1b10a2a0c61e10ee9f0167820955df343074f16b69614952caef34de21d -> SetCustomFee(address pool, uint24 fee)   [uint24 — distinct from the v2 PoolFactory uint256 SetCustomFee]
0xb532073b38c83145e3e5135377a08bf9aab55bc0fd7c1179cd4fb995d2a5159c -> OwnerChanged(address oldOwner, address newOwner)
0xdf24ed64a7bcd761cf1132e79f94ea269a1d570e7a6ca0ab99a8f5ccd6f5022f -> SwapFeeModuleChanged(address old, address new)
0x6520f404f3831947cee8673060459cdfb181b7332aa7580bcce9bf90ef1f0e20 -> UnstakedFeeModuleChanged(address old, address new)
0x7ae0007229b3333719d97e8ef5829c888f560776012974f87409c158e5b7eb91 -> SwapFeeManagerChanged(address old, address new)
0x3d7ebe96182c99643ca0c997a416a2a3409baab225f85f50c29fcf0591c820c1 -> UnstakedFeeManagerChanged(address old, address new)
0xcbca61144322b913ada4febfb591864cad7617559d7ee0d3e29b48eb93fcc78e -> DefaultUnstakedFeeChanged(uint24 old, uint24 new)
```

### 1.4 CLGauge (per CL pool, EIP-1167 clone, created by Voter via CLGaugeFactory)
```
0x1c8ab8c7f45390d58f58f1d655213a82cca5d12179761a87c16f098813b8f211 -> Deposit(address user, uint256 tokenId, uint128 liquidityToStake)   [all 3 indexed]  ✓live
0x8903a5b5d08a841e7f68438387f1da20c84dea756379ed37e633ff3854b99b84 -> Withdraw(address user, uint256 tokenId, uint128 liquidityToStake)  ✓live
0x095667752957714306e1a6ad83495404412df6fdb932fca6dc849a7ee910d4c1 -> NotifyReward(address from, uint256 amount)       [SAME sig as v2 Gauge]
0xbc567d6cbad26368064baa0ab5a757be46aae4d70f707f9203d9d9b6c8ccbfa3 -> ClaimFees(address from, uint256 claimed0, uint256 claimed1)
0x1f89f96333d3133000ee447473151fa9606543368f02271c9d95ae14f13bcc67 -> ClaimRewards(address from, uint256 amount)       [SAME sig as v2 Gauge]  ✓live
```

### 1.5 NonfungiblePositionManager (CL position NFT — events IDENTICAL to Uniswap V3 NPM)
```
0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f -> IncreaseLiquidity(uint256 tokenId, uint128 liquidity, uint256 amount0, uint256 amount1)
0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4 -> DecreaseLiquidity(uint256 tokenId, uint128 liquidity, uint256 amount0, uint256 amount1)
0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01 -> Collect(uint256 tokenId, address recipient, uint256 amount0, uint256 amount1)
0x9a72f60932a1a6a1e1ceaa7a7dc51efcfe37685b729d8a680ab939f4612455a6 -> TokenDescriptorChanged(address tokenDescriptor)
0xcfaaa26691e16e66e73290fc725eee1a6b4e0e693a1640484937aac25ffb55a4 -> TransferOwnership(address owner)
# + ERC-721 Transfer 0xddf252ad… / Approval 0x8c5be1e5… / ApprovalForAll 0x17307eab…, and ERC-4906 MetadataUpdate 0xf8e1a15a… / BatchMetadataUpdate 0x6bd5c950…
```

### 1.6 Fee modules (DynamicSwapFeeModule / CustomSwapFeeModule / CustomUnstakedFeeModule)
```
0x131bae2509aa4feb31f43358185932f36716d304cd2d819278a8f27017913a74 -> DynamicFeeConfigured(address pool, uint24 baseFee, uint64 ...)
0xc468f70535e94886b35ff615ecae1df3a7149178689eb6db7d69861cd9247d05 -> DynamicFeeReset(address pool)
0xd444e1b10a2a0c61e10ee9f0167820955df343074f16b69614952caef34de21d -> SetCustomFee(address pool, uint24 fee)
0x580e5cae1c3e7e91049a0dce5893866a73af11163fd52389d95c2117d8df053b -> FeeCapSet(address pool, uint256 cap)
0x7e32f98c3f8b49356115aabb08e354ae2bd994c337ff1ea63ad3e8424b346fd2 -> DefaultFeeCapSet(uint256 cap)
0x30c247ef0dda66710b7fde1079bd6f5194755e8f285b64fb79d8124f7e421830 -> ScalingFactorSet(address pool, uint256 factor)
0x7a30af0ec8d2cdbaa589a5d6743a47a62b12f68a8d8df30747c7fcc9c69436ad -> SecondsAgoSet(uint32 secondsAgo)
0xee3dd15d73f7ef85ed01fc28ee4377bc8f2f8ef1c7d184a76232198b5a36033a -> DiscountedRegistered(address pool, uint24 fee)
0xe8221b863d410fc656f2cf857231979f0e9df138aea7aadc275b1e4613311d2e -> DiscountedDeregistered(address pool)
```

---

## 2. Function signatures (chain-agnostic) — `selector -> name(types)`

> Slipstream structs key on **`tickSpacing` (int24)** instead of Uni V3's `fee (uint24)`, and `mint`/`exactInputSingle` append a `sqrtPriceX96`/`tickSpacing` field → **selectors differ from Uni V3**. Verified vs deployed bytecode.

### 2.1 CLFactory (`0x73DC984D9490286E735548f61dfCCec67Af82ed9`)
```
0x232aa5ac -> createPool(address tokenA, address tokenB, int24 tickSpacing, uint160 sqrtPriceX96) -> address pool
0x28af8d0b -> getPool(address tokenA, address tokenB, int24 tickSpacing) -> address pool
0xcefa7799 -> poolImplementation() -> address      [→ CLPool clone master]
0x35458dcc -> getSwapFee(address pool) -> uint24    [pips; resolves module/custom/default]
0x48cf7a43 -> getUnstakedFee(address pool) -> uint24
0x380dc1c2 -> tickSpacingToFee(int24 tickSpacing) -> uint24
0xeee0fdb4 -> enableTickSpacing(int24 tickSpacing, uint24 fee)
0x41d1de97 -> allPools(uint256) -> address  ·  0xefde4e64 -> allPoolsLength() -> uint256   [=50 this run]
0x46c96aac -> voter()  ·  0x3bf0c9fb -> factoryRegistry()  ·  0xe2824832 -> defaultUnstakedFee() -> uint24  [=100000]
```

### 2.2 CLPool (impl `0x18e6…8AF7`; each pool is a clone)
```
0x128acb08 -> swap(address recipient, bool zeroForOne, int256 amountSpecified, uint160 sqrtPriceLimitX96, bytes data) -> (int256,int256)
0x3c8a7d8d -> mint(address recipient, int24 tickLower, int24 tickUpper, uint128 amount, bytes data) -> (uint256,uint256)
0xa34123a7 -> burn(int24 tickLower, int24 tickUpper, uint128 amount) -> (uint256,uint256)
0x4f1eb3d8 -> collect(address recipient, int24 tickLower, int24 tickUpper, uint128 amount0Requested, uint128 amount1Requested) -> (uint128,uint128)
0x490e6cbc -> flash(address recipient, uint256 amount0, uint256 amount1, bytes data)
0x3850c7bd -> slot0() -> (uint160 sqrtPriceX96, int24 tick, uint16 obsIndex, uint16 obsCardinality, uint16 obsCardinalityNext, bool unlocked)
0x1a686502 -> liquidity() -> uint128  ·  0x3ab04b20 -> stakedLiquidity() -> uint128  ·  0xa6f19c84 -> gauge() -> address
0xd0c93a7c -> tickSpacing() -> int24  ·  0xddca3f43 -> fee() -> uint24  ·  0x0dfe1681 -> token0()  ·  0xd21220a7 -> token1()
```

### 2.3 NonfungiblePositionManager (`0xf8c30c3C362941C23025f2eA30B066A73C982f63`)  — "Topaz CL Position" / `TOPAZ-CL-POS`
```
0xb5007d1f -> mint((address token0, address token1, int24 tickSpacing, int24 tickLower, int24 tickUpper, uint256 amount0Desired, uint256 amount1Desired, uint256 amount0Min, uint256 amount1Min, address recipient, uint256 deadline, uint160 sqrtPriceX96)) -> (uint256 tokenId, uint128 liquidity, uint256 amount0, uint256 amount1)   [payable; ≠ Uni V3 mint 0x88316456]
0x219f5d17 -> increaseLiquidity((uint256 tokenId, uint256 amount0Desired, uint256 amount1Desired, uint256 amount0Min, uint256 amount1Min, uint256 deadline)) -> (uint128,uint256,uint256)   [payable]
0x0c49ccbe -> decreaseLiquidity((uint256 tokenId, uint128 liquidity, uint256 amount0Min, uint256 amount1Min, uint256 deadline)) -> (uint256,uint256)
0xfc6f7865 -> collect((uint256 tokenId, address recipient, uint128 amount0Max, uint128 amount1Max)) -> (uint256,uint256)
0x42966c68 -> burn(uint256 tokenId)
0x99fbab88 -> positions(uint256 tokenId) -> 12-tuple (…, address token0, address token1, int24 tickSpacing, int24 tickLower, int24 tickUpper, uint128 liquidity, …)   [tickSpacing slot, not fee]
0xc45a0155 -> factory() -> address [→ CLFactory]  ·  0x5a9d7a68 -> tokenDescriptor() -> address  ·  0x4aa4a4fc -> WETH9() -> address [→ WBNB]
```

### 2.4 SwapRouter (`0x9B63CA87919617d042A89663492dB3c8686e0CaE`)
```
0xa026383e -> exactInputSingle((address tokenIn, address tokenOut, int24 tickSpacing, address recipient, uint256 deadline, uint256 amountIn, uint256 amountOutMinimum, uint160 sqrtPriceLimitX96)) -> uint256   [payable; ≠ Uni V3 0x04e45aaf]
0xc04b8d59 -> exactInput((bytes path, address recipient, uint256 deadline, uint256 amountIn, uint256 amountOutMinimum)) -> uint256   [path = token(20)‖tickSpacing(3)‖token(20)… — NOT fee bytes]
0xc714e838 -> exactOutputSingle((address tokenIn, address tokenOut, int24 tickSpacing, address recipient, uint256 deadline, uint256 amountOut, uint256 amountInMaximum, uint160 sqrtPriceLimitX96)) -> uint256
0xf28c0498 -> exactOutput((bytes path, address recipient, uint256 deadline, uint256 amountOut, uint256 amountInMaximum)) -> uint256
0xc45a0155 -> factory() [→ CLFactory]  ·  0x4aa4a4fc -> WETH9() [→ WBNB]
```

### 2.5 CLGauge (impl `0xc2f7…8b97`; each gauge is a clone)
```
0xb6b55f25 -> deposit(uint256 tokenId)          [stake a CL position NFT; SAME selector as v2 Gauge deposit(uint256)]
0x2e1a7d4d -> withdraw(uint256 tokenId)
0x1c4b774b -> getReward(uint256 tokenId)  ·  0xc00007b0 -> getReward(address account)
0x3e491d47 -> earned(address account, uint256 tokenId) -> uint256  ·  0xa6f19c84-style rewardToken/rollover/etc.
```

---

## 3. Addresses (BNB Smart Chain, id 56)

> ✓ = `eth_getCode` non-empty + wiring confirmed this run. Shared ve(3,3) core (Voter/VE/Minter/RewardsDistributor/FactoryRegistry) is in [`amm.md`](amm.md) §3.1.
```
0x73DC984D9490286E735548f61dfCCec67Af82ed9 -> CLFactory                  createPool/getPool(a,b,tickSpacing); allPoolsLength=50; poolImplementation()→CLPool impl; voter()→Voter ✓
0x18e68051d1b1fB44cb539cA4436F112D28577AF7 -> CLPool (impl)              EIP-1167 clone master for every CL pool — do NOT call directly ✓
0xeD2ED418f104E18B1D11eA5C26236A1caa675839 -> CLGaugeFactory            deploys CLGauge clones (called by Voter); implementation()→CLGauge impl ✓
0xc2f777a2e9f54f195212a5a2d394399252958b97 -> CLGauge (impl)            EIP-1167 clone master for every CL gauge ✓
0xf8c30c3C362941C23025f2eA30B066A73C982f63 -> NonfungiblePositionManager  CL position NFT "TOPAZ-CL-POS"; factory()→CLFactory; WETH9()→WBNB ✓
0x9B63CA87919617d042A89663492dB3c8686e0CaE -> SwapRouter                exactInput[Single]/exactOutput[Single]; factory()→CLFactory ✓
0x7CCB89bB9BdEF68688F39a2c22d249fD1D9759f1 -> QuoterV2                  quote v3 swaps (revert-and-decode, non-view) ✓
0x47c3570b90e7234FE695Ad5F1bE69E21fe1a9ee2 -> MixedRouteQuoterV1        quote routes mixing v2 (stable/volatile) + v3 hops ✓
0x81aCc35240D19948a56b8b68BcC8706F90baBAb5 -> NFTPositionDescriptor (V1)  LIVE — NPM.tokenDescriptor() returns THIS ✓
0xBa4C4f5Ca809C21286ff1a872b3c0CFb57AfE904 -> NFTPositionDescriptor (new) deployed (updated art) but NPM not (yet) repointed to it ✓
0x50f9756f631266686b9A7EBDF55998dB3dA5ca0a -> NFTDescriptor (library) ✓
0x21C9257dFCdf04154D34dF5A2204B9402Ef31d9a -> NFTSVG (library) ✓
0xA0462a52af4f8cbF7766Efbba75355B30b6BCCe2 -> CustomSwapFeeModule       per-pool flat swap-fee override (MAX_FEE 30000 pips = 3%) ✓
0x3bad7F96cd1b51CE86e12C42541Ac7d559A78582 -> CustomUnstakedFeeModule   unstaked-position fee override (MAX 500000 pips=50%; default 100000=10%) ✓
0x656cf5d2f1A70177E011e2c27DeafBeE4C7B0541 -> DynamicSwapFeeModule      TWAP-volatility-scaled swap fees ✓
```

### tickSpacing → default fee (verified on-chain via `tickSpacingToFee`; pips, 1e-6)
```
1    -> 100   (0.01%)   tightly-correlated stables (USDC/USDT)
50   -> 500   (0.05%)   low-volatility
100  -> 1000  (0.10%)   moderate
200  -> 3000  (0.30%)   high vol (BNB/USDT, ETH/USDC)
2000 -> 10000 (1.00%)   exotic
```
Per-pool overrides via the fee modules; read live with `CLFactory.getSwapFee(pool)` / `getUnstakedFee(pool)` rather than assuming the default.

---

## 4. Proxies

- **CL Pools: EIP-1167 minimal-proxy clones** of `CLPool (impl) 0x18e6…8AF7`, CREATE2-deployed by `CLFactory` (salt = `keccak256(token0,token1,tickSpacing)`). Verified live: pool `0xd4ba…adda` code = `363d3d373d3d3d363d73⟨18e6…8af7⟩5af43d82803e903d91602b57fd5bf3`. Immutable.
- **CLGauges: EIP-1167 clones** of `CLGauge (impl) 0xc2f7…8b97`, created by `Voter` via `CLGaugeFactory` (verified: live CL gauge `0x66f9…9cd3` is the 45-byte stub embedding the impl). *(Contrast v2 Gauges, which are full deploys — see [`amm.md`](amm.md) §4.)*
- **CLFactory, NPM, SwapRouter, quoters, fee modules, descriptor libs: plain immutable deploys** — no EIP-1967/UUPS/beacon proxy.
- **Upgrade path = `FactoryRegistry` (shared with v2):** `CLFactory` is registered in `FactoryRegistry`; a new CL factory generation can be approved by the admin without migrating existing CL pools — so "old vs new" appears as coexisting factory generations, not impl-slot upgrades. See [`amm.md`](amm.md) §4.
- **"Old vs new" descriptor nuance:** `NPM.tokenDescriptor()` currently returns the **V1** descriptor `0x81aCc…bAb5`; an updated descriptor `0xBa4C…E904` is deployed but the owner has not repointed NPM to it via `setTokenDescriptor` (would emit `TokenDescriptorChanged 0x9a72f609…`). Cosmetic only (affects `tokenURI` art, not accounting).

See `references/proxies.md` for EIP-1167 detection.

---

## 5. Detection invariants & gotchas

1. **CL core events are byte-identical to Uniswap V3** (`Swap 0xc42079f9…`, `Mint 0x7a53080b…`, `Burn 0x0c396cd9…`, `Collect 0x70935338…`, `Flash`, `Initialize`). **Disambiguate Topaz CL by pool provenance** — a clone of `CLPool impl 0x18e6…8AF7`, created by `CLFactory 0x73DC…2ed9` — never by topic0 alone.
2. **CL `PoolCreated 0xab0d57f0…` (token0,token1,tickSpacing,pool) ≠ Uni V3 `0x783cca1c…` (token0,token1,fee,tickSpacing,pool).** Slipstream keys by `tickSpacing`; the default fee is derived (`tickSpacingToFee`).
3. **Slipstream struct selectors differ from Uni V3:** `mint 0xb5007d1f` (vs `0x88316456`), `exactInputSingle 0xa026383e` (vs `0x04e45aaf`), `exactOutputSingle 0xc714e838`. But `exactInput 0xc04b8d59` / `exactOutput 0xf28c0498` collide with Uni V3 (same struct shape) — the **path bytes differ**: `token‖tickSpacing(3 bytes)‖token`, not `token‖fee‖token`.
4. **`CollectFees 0x205860e6…` (Slipstream gauge-fee collection) ≠ LP `Collect 0x70935338…`.**
5. **CLGauge `Deposit 0x1c8ab8c7…` / `Withdraw 0x8903a5b5…` carry `uint128 liquidityToStake`** — distinct topics from the v2 Gauge `Deposit 0x5548c837…` / `Withdraw 0x884edad9…`. But CLGauge `NotifyReward 0x09566775…` / `ClaimRewards 0x1f89f96…` share topics with the v2 Gauge — disambiguate by gauge address.
6. **CL `SetCustomFee(address,uint24) 0xd444e1b1…` ≠ v2 `SetCustomFee(address,uint256) 0xae468ce5…`.**
7. **CL position NFTs are an ERC-721** (`NonfungiblePositionManager`, symbol `TOPAZ-CL-POS`) — positions keyed by `tokenId`; `positions(tokenId)` exposes `tickSpacing` (not `fee`).
8. **Bytea hex literals need an even digit count** (40 addr / 64 topic).

---

## 6. Quick-copy (Postgres `bytea`-ready)
```
swap_cl       = '\xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
mint_cl       = '\x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde'
burn_cl       = '\x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c'
collect_cl    = '\x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0'
poolcreated_cl= '\xab0d57f0df537bb25e80245ef7748fa62353808c54d6e528a9dd20887aed9ac2'
clgauge_deposit = '\x1c8ab8c7f45390d58f58f1d655213a82cca5d12179761a87c16f098813b8f211'
clfactory = '\x73dc984d9490286e735548f61dfccec67af82ed9'
clpool_impl = '\x18e68051d1b1fb44cb539ca4436f112d28577af7'
npm       = '\xf8c30c3c362941c23025f2ea30b066a73c982f63'
swaprouter= '\x9b63ca87919617d042a89663492db3c8686e0cae'
```

## 7. Verification & sources
- topic0/selectors: keccak (pycryptodome) over canonical signatures parsed from [`topazdex/topaz-slipstream`](https://github.com/topazdex/topaz-slipstream); cross-validated against `uniswap/v3.md` (identical CL core: `swap 0x128acb08`, `decreaseLiquidity 0x0c49ccbe`, `collect 0xfc6f7865`) and `aerodrome/slipstream.md`.
- on-chain (BSC, 2026-06-05): all §3 addresses have bytecode; `CLFactory.poolImplementation→CLPool impl`, `voter→Voter`, `allPoolsLength=50`, `tickSpacingToFee` map; `NPM.factory→CLFactory`, `name="Topaz CL Position"`, `symbol="TOPAZ-CL-POS"`, `WETH9→WBNB`, `tokenDescriptor→V1 0x81aCc…`; `SwapRouter.factory→CLFactory`; CL pool & CL gauge clone bytecode embed their impls; live `eth_getLogs` saw `Swap`/`Mint`/`Burn`/`Collect` (pool) and `Deposit`/`Withdraw`/`ClaimRewards` (CL gauge). `PoolCreated` rare → verified by canonical-source keccak (node prunes old logs).
- Addresses cross-checked vs [`agent-skill/references/addresses.md`](https://github.com/topazdex/agent-skill) + [docs.topazdex.com/docs/contracts](https://topazdex.com/docs/contracts).
- Audit: [Shieldify Security — Topaz DEX Security Review](https://github.com/shieldify-security/audits-portfolio/blob/main/reports/Topaz-Dex-Security-Review.pdf) (incl. the Slipstream CL modules). No known Topaz exploit/incident as of 2026-06-05.
