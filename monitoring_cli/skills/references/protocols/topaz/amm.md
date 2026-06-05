# Topaz v2 (Solidly AMM) + ve(3,3) Governance — Compressed Reference (BNB Chain, id 56)

**Status:** topic0/selectors computed with keccak from `topazdex/topaz-contacts` source; addresses + wiring re-verified on-chain vs `bsc-rpc.publicnode.com` on 2026-06-05.
**Scope:** the **classic Solidly-style AMM** (volatile `xy=k` + stable `x³y+xy³=k` pools) and the **ve(3,3) stack** (Voter, VotingEscrow veTOPAZ, Minter, RewardsDistributor, Gauge, Fees/Bribe rewards) — **shared with the v3/Slipstream product in [`slipstream.md`](slipstream.md)**. Topaz is a **Velodrome V2 fork**; most events/selectors are identical to [`aerodrome/amm.md`](../aerodrome/amm.md). Topaz-only additions: `BonusLock`, `AirdropDistributor`, ERC-2771 `Forwarder`, a growth+decay `Minter`.
**Key facts:** veTOPAZ is an **ERC-721 veNFT** (not ERC-20). Pools are **EIP-1167 clones**. The v2 `Swap` topic0 differs from Uniswap V2; several other topics collide by signature with Uni V2 / Curve / Balancer (see Detection).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Pool (volatile + stable; emitted by each v2 Pool clone)
```
0xb3e2773606abfd36b5bd91394b3a54d1398336c65005baf7bf7a05efeffaf75b -> Swap(address sender, address to, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out)   [sender,to indexed — NOT the Uni V2 layout]  ✓live
0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f -> Mint(address sender, uint256 amount0, uint256 amount1)        [collides w/ Uni V2 / Sushi Mint topic0]
0x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2 -> Burn(address sender, address to, uint256 amount0, uint256 amount1)
0xcf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a -> Sync(uint256 reserve0, uint256 reserve1)                      [collides w/ Sushi Trident Sync]  ✓live
0x112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602 -> Fees(address sender, uint256 amount0, uint256 amount1)         [trading fees pushed to PoolFees]
0x865ca08d59f5cb456e85cd2f7ef63664ea4f73327414e9d8152c4158b0e94645 -> Claim(address sender, address recipient, uint256 amount0, uint256 amount1)
# the Pool is also an ERC-20 LP token -> emits Transfer 0xddf252ad… / Approval 0x8c5be1e5…
```
`Swap`: `amount*In`/`amount*Out` are unsigned; exactly one In and the opposite Out are non-zero per swap. Filter on `topic0` + pool address.

### 1.2 PoolFactory
```
0x2128d88d14c80cb081c1252a5acff7a264671bf199ce226b53788fb26065005e -> PoolCreated(address token0, address token1, bool stable, address pool, uint256 allPoolsLength)   [token0,token1,stable indexed]
0xae468ce586f9a87660fdffc1448cee942042c16ae2f02046b134b5224f31936b -> SetCustomFee(address pool, uint256 fee)    [pool indexed; NOTE uint256 — the CL SetCustomFee is uint24 -> different topic0]
0x5d0517e3a4eabea892d9750138cd21d4a6cf3b935b43d0598df7055f463819b2 -> SetFeeManager(address feeManager)
0xe02efb9e8f0fc21546730ab32d594f62d586e1bbb15bb5045edd0b1878a77b35 -> SetPauser(address pauser)
0x0d76538efc408318a051137c2720a9e82902acdbd46b802d488b74ca3a09a116 -> SetPauseState(bool state)
0xc6ff127433b785c51da9ae4088ee184c909b1a55b9afd82ae6c64224d3bc15d2 -> SetVoter(address voter)
```
Indexing strategy: subscribe to `PoolCreated` once to enumerate every v2 pool. `bool stable` (indexed) distinguishes a stable pool from a volatile pool — a pair can have **both**.

### 1.3 Voter (ve(3,3) gauge voting / emissions direction — SHARED by v2 + v3)
```
0xef9f7d1ffff3b249c6b9bf2528499e935f7d96bb6d6ec4e7da504d1d3c6279e1 -> GaugeCreated(address poolFactory, address votingRewardsFactory, address gaugeFactory, address pool, address bribeVotingReward, address feeVotingReward, address gauge, address creator)   [first 3 indexed]
0x04a5d3f5d80d22d9345acc80618f4a4e7e663cf9e1aed23b57d975acec002ba7 -> GaugeKilled(address gauge)
0xed18e9faa3dccfd8aa45f69c4de40546b2ca9cccc4538a2323531656516db1aa -> GaugeRevived(address gauge)
0x452d440efc30dfa14a0ef803ccb55936af860ec6a6960ed27f129bef913f296a -> Voted(address voter, address pool, uint256 tokenId, uint256 weight, uint256 totalWeight, uint256 timestamp)   [voter,pool,tokenId indexed]  ✓live
0xadab630928b1d46214641293704a312ee7ad87e03ae14a7fd95e7308b93998df -> Abstained(address voter, address pool, uint256 tokenId, uint256 weight, uint256 totalWeight, uint256 timestamp)  ✓live
0xf70d5c697de7ea828df48e5c4573cb2194c659f1901f70110c52b066dcf50826 -> NotifyReward(address sender, address reward, uint256 amount)        [Voter 3-arg variant]
0x4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17 -> DistributeReward(address sender, address gauge, uint256 amount)
0x44948130cf88523dbc150908a47dd6332c33a01a3869d7f2fa78e51d5a5f9c57 -> WhitelistToken(address whitelister, address token, bool _bool)
0x8a6ff732c8641e1e34d771e1f8b1673e988c1abdfb694ebdf6c910a5e3d0d853 -> WhitelistNFT(address whitelister, uint256 tokenId, bool _bool)
```

### 1.4 VotingEscrow (veTOPAZ — ERC-721 veNFT; SHARED)
```
0x8835c22a0c751188de86681e15904223c054bedd5c68ec8858945b7831290273 -> Deposit(address provider, uint256 tokenId, uint8 depositType, uint256 value, uint256 locktime, uint256 ts)   [provider,tokenId,depositType indexed; enum DepositType encodes as uint8 — NOT the Curve veCRV layout]  ✓live
0x02f25270a4d87bea75db541cdfe559334a275b4a233520ed6c0a2429667cca94 -> Withdraw(address provider, uint256 tokenId, uint256 value, uint256 ts)
0x5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c -> Supply(uint256 prevSupply, uint256 supply)        [collides w/ Curve/Balancer veToken Supply]  ✓live
0x793cb7a30a4bb8669ec607dfcbdc93f5a3e9d282f38191fddab43ccaf79efb80 -> LockPermanent(address _owner, uint256 _tokenId, uint256 amount, uint256 _ts)
0x668d293c0a181c1f163fd0d3c757239a9c17bd26c5e483150e374455433b27fa -> UnlockPermanent(address _owner, uint256 _tokenId, uint256 amount, uint256 _ts)  ✓live
0x986e3c958e3bdf1f58c2150357fc94624dd4e77b08f9802d8e2e885fa0d6a198 -> Merge(address _sender, uint256 _from, uint256 _to, uint256 _amountFrom, uint256 _amountTo, uint256 _amountFinal, uint256 _locktime, uint256 _ts)  ✓live
0x8303de8187a6102fdc3fe20c756dddd68df0ae027b77e2391c19a855e0821f33 -> Split(uint256 _from, uint256 _tokenId1, uint256 _tokenId2, address _sender, uint256 _splitAmount1, uint256 _splitAmount2, uint256 _locktime, uint256 _ts)  ✓live
0xae65a147ec014982132ce8b32019735e3c5f41457848d2ce2e2c3e0cbc9df7bc -> CreateManaged(address _to, uint256 _mTokenId, address _from, address _lockedManagedReward, address _freeManagedReward)
0xf7757ce35992f4ee014dee2e0c97ed6245758960a6ecc9e124897a5fb7b01423 -> DepositManaged(address _owner, uint256 _tokenId, uint256 _mTokenId, uint256 _weight, uint256 _ts)
0x5319474ec1e9d118585a40e615ea37be254007e6bb5b039756c3813c2d135489 -> WithdrawManaged(address _owner, uint256 _tokenId, uint256 _mTokenId, uint256 _weight, uint256 _ts)
0xf1aa2a9e40138176a3ee6099df056f5c175f8511a0d8b8275d94d1ea5de46773 -> DelegateChanged(address delegator, uint256 fromDelegate, uint256 toDelegate)
0xdec2bacdd2f05b59de34da9b523dff8be42e5e38e818c82fdb0bae774387a724 -> DelegateVotesChanged(address delegate, uint256 previousBalance, uint256 newBalance)
# also ERC-721 Transfer 0xddf252ad… (✓live) / Approval 0x8c5be1e5… (✓live) / ApprovalForAll 0x17307eab…, and ERC-4906 MetadataUpdate 0xf8e1a15a… (✓live)
```

### 1.5 Gauge (v2 per-pool LP staking → TOPAZ emissions; FULL deploy, not a clone)
```
0x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62 -> Deposit(address from, address to, uint256 amount)        [3-arg — differs from the 2-arg Deposit in older Velodrome docs]
0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364 -> Withdraw(address from, uint256 amount)                    [collides w/ Curve/Balancer gauge Withdraw]
0x095667752957714306e1a6ad83495404412df6fdb932fca6dc849a7ee910d4c1 -> NotifyReward(address from, uint256 amount)               [Gauge 2-arg variant; SAME sig used by CLGauge]
0xbc567d6cbad26368064baa0ab5a757be46aae4d70f707f9203d9d9b6c8ccbfa3 -> ClaimFees(address from, uint256 claimed0, uint256 claimed1)
0x1f89f96333d3133000ee447473151fa9606543368f02271c9d95ae14f13bcc67 -> ClaimRewards(address from, uint256 amount)                 [SAME sig used by CLGauge]  ✓live
```

### 1.6 FeesVotingReward + BribeVotingReward (per-gauge; voters' fee + bribe claims; full deploys)
```
0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15 -> Deposit(address from, uint256 tokenId, uint256 amount)
0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568 -> Withdraw(address from, uint256 tokenId, uint256 amount)
0x52977ea98a2220a03ee9ba5cb003ada08d394ea10155483c95dc2dc77a7eb24b -> NotifyReward(address from, address reward, uint256 epoch, uint256 amount)   [Reward 4-arg variant]
0x9aa05b3d70a9e3e2f004f039648839560576334fb45c81f91b6db03ad9e2efc9 -> ClaimRewards(address from, address reward, uint256 amount)
```

### 1.7 Minter (weekly TOPAZ emissions; SHARED) — Topaz growth+decay variant
```
0xcd2127828092f586df56003faf212897e901bb47f89a227e1acd3a0738f1fe5f -> Mint(address _sender, uint256 _weekly, uint256 _circulating_supply, bool _tail)   [_sender,_tail indexed]
0xeaf2fed4f7f20988cb8090e5cb6ca6867a5e85be3d3a2b70691e8329ae96d618 -> DistributeLocked(address _destination, uint256 _amount, uint256 _tokenId)
0xad55b70c3adab3ed0dbd5a6924908c58a5c6f7ef36086ea57a46ecbea914bf92 -> DistributeLiquid(address _destination, uint256 _amount)
0x89f7f67bc867b6d7eefd5bd92b0df77051c2507700c7994efc25cfc679a0c526 -> Nudge(uint256 _period, uint256 _oldRate, uint256 _newRate)     [tail-rate governance]
0xe25466fe8250322bee73bc230e10775fe0da57be723ebdabfdc8b62b4ba0d10c -> AcceptTeam(address _newTeam)
```
Emission schedule (from source): `weekly` starts `10,000,000e18`; `WEEKLY_DECAY=9900/1e4` (−1%/wk) or `WEEKLY_GROWTH=10300/1e4` (+3%/wk) until `weekly < TAIL_START=8,969,150e18`, then flat `tailEmissionRate=67` bps (nudge-adjustable 1…100). `teamRate=500` bps (5%).

### 1.8 RewardsDistributor (veTOPAZ rebase; SHARED)
```
0xce749457b74e10f393f2c6b1ce4261b78791376db5a3f501477a809f03f500d6 -> CheckpointToken(uint256 time, uint256 tokens)
0xcae2990aa9af8eb1c64713b7eddb3a80bf18e49a94a13fe0d0002b5d61d58f00 -> Claimed(uint256 tokenId, uint256 epochStart, uint256 epochEnd, uint256 amount)   [tokenId,epochStart,epochEnd indexed]
```

### 1.9 BonusLock (Topaz-only — tiered lock-bonus campaign that mints/extends veTOPAZ)
```
0xfb03bb25073b56b1dd262abd1d406cd50fd9739ce0bfa39d3efa19ee5dbdec5e -> BonusLocked(address user, uint256 tokenId, uint256 userAmount, uint256 bonusAmount)
0x5f330753205563c33af0bd73a2f252b69f4657042cee5c57aa7149598ef6577d -> BonusLockedWithExisting(address user, uint256 tokenId, uint256 freshAmount, uint256 bonusAmount)
0xfd8f543ded1a9cbd18242f9027c8c0d5c9fc74b89c8e4b104a522a6d4ea42e88 -> VeNFTDeposited(uint256 tokenId, uint256 amount)
0xe5470b12660f61163a89c0ea446b4ef240e06646703fa4666d4bc8003e04188d -> VeNFTWithdrawn(uint256 tokenId, address recipient)
0xcdff85cec09feec736e3fd3cd14be3e9739159d5ae15f1132e2c2374eecd557a -> BonusPercentageUpdated(uint256 oldPercentage, uint256 newPercentage)
0x7754b90a7dadcfd77d1d5197b8cd5aad8a7a244816c34b50e43d22b2d475798e -> TokenRecovered(uint256 tokenId, address recipient)
# + Paused 0x62e78cea… / Unpaused 0x5db9ee0a…
```

### 1.10 AirdropDistributor (Topaz-only — initial veNFT airdrop)
```
0xada993ad066837289fe186cd37227aa338d27519a8a1547472ecb9831486d272 -> Airdrop(address _wallet, uint256 _amount, uint256 _tokenId)   [_wallet indexed]
```

---

## 2. Function signatures (chain-agnostic) — `selector -> name(types)`

Verified against deployed dispatcher bytecode (and on-chain `eth_call` for the lookups). `Route` = `(address from,address to,bool stable,address factory)`.

### 2.1 Router  (`0x1E98c8226e7d452e1888e3d3d2F929346321c6c3`)
```
0xcac88ea9 -> swapExactTokensForTokens(uint256 amountIn, uint256 amountOutMin, Route[] routes, address to, uint256 deadline) -> uint256[]
0x88cd821e -> swapExactTokensForTokensSupportingFeeOnTransferTokens(uint256,uint256,Route[],address,uint256)
0x903638a4 -> swapExactETHForTokens(uint256 amountOutMin, Route[] routes, address to, uint256 deadline) -> uint256[]   [payable]
0xc6b7f1b6 -> swapExactTokensForETH(uint256,uint256,Route[],address,uint256) -> uint256[]
0x5a47ddc3 -> addLiquidity(address tokenA, address tokenB, bool stable, uint256 amountADesired, uint256 amountBDesired, uint256 amountAMin, uint256 amountBMin, address to, uint256 deadline)
0x0dede6c4 -> removeLiquidity(address tokenA, address tokenB, bool stable, uint256 liquidity, uint256 amountAMin, uint256 amountBMin, address to, uint256 deadline)
0xd4b6846d -> defaultFactory() -> address        [→ PoolFactory]
0xd5fb4b8b -> getAmountsOut(uint256 amountIn, Route[] routes) -> uint256[]
0xabfb3969 -> zapIn(address tokenIn, uint256 amountInA, uint256 amountInB, Zap zapInPool, Route[] routesA, Route[] routesB, address to, bool stake)
```

### 2.2 PoolFactory (`0x65E6cD0eF5D3467030103cf3d433034E570b5784`) & Pool (impl `0xdC94…3678`)
```
0x36bf95a0 -> createPool(address tokenA, address tokenB, bool stable) -> address pool
0x79bc57d5 -> getPool(address tokenA, address tokenB, bool stable) -> address     [the `bool stable` selector]
0x41d1de97 -> allPools(uint256 index) -> address
0xefde4e64 -> allPoolsLength() -> uint256          [=20 this run]
0x5b16ebb7 -> isPool(address) -> bool
0xcc56b2c5 -> getFee(address pool, bool stable) -> uint256     [pips; 0 ⇒ default volatileFee=30 / stableFee=5]
0xd49466a8 -> setCustomFee(address pool, uint256 fee)
0x5c60da1b -> implementation() -> address           [→ Pool clone master]
0x46c96aac -> voter() -> address
# Pool (per-pair clone): 0x022c0d9f swap(uint256,uint256,address,bytes) · 0x6a627842 mint(address) · 0x89afcb44 burn(address) · 0x0902f1ac getReserves()->(uint256,uint256,uint256) · 0xf140a35a getAmountOut(uint256,address) · 0x22be3de1 stable()->bool · 0x392f37e9 metadata() · 0xd294f093 claimFees() · 0x0dfe1681 token0() · 0xd21220a7 token1()
```

### 2.3 Voter (`0x2F80F810a114223AC69E34E84E735CaD515dAD67`) — SHARED v2+v3
```
0x7ac09bf7 -> vote(uint256 tokenId, address[] poolVote, uint256[] weights)
0x310bd74b -> reset(uint256 tokenId)
0x32145f90 -> poke(uint256 tokenId)
0x794cea3c -> createGauge(address poolFactory, address pool) -> address gauge      [works for BOTH PoolFactory and CLFactory]
0xb9a09fd5 -> gauges(address pool) -> address gauge        [0x0 if none]
0x06d6a1b2 -> poolForGauge(address gauge) -> address pool
0xc4f08165 -> gaugeToFees(address gauge) -> address FeesVotingReward
0x929c8dcd -> gaugeToBribe(address gauge) -> address BribeVotingReward
0x1703e5f9 -> isAlive(address gauge) -> bool
0x7715ee75 -> claimBribes(address[] bribes, address[][] tokens, uint256 tokenId)
0x666256aa -> claimFees(address[] fees, address[][] tokens, uint256 tokenId)
0x6138889b -> distribute(address[] gauges)
0x992a7933 -> killGauge(address) · 0x9f06247b -> reviveGauge(address)
0x1f850716 -> ve() -> address  ·  0x07546172 -> minter() -> address  ·  0x3bf0c9fb -> factoryRegistry() -> address
```

### 2.4 VotingEscrow / veTOPAZ (`0xe951aC65EFE86682311ab0d8995E7A58750c5eB3`)
```
0xb52c05fe -> createLock(uint256 value, uint256 lockDuration) -> uint256 tokenId
0xec32e6df -> createLockFor(uint256 value, uint256 lockDuration, address to) -> uint256 tokenId
0xb2383e55 -> increaseAmount(uint256 tokenId, uint256 value)
0x9d507b8b -> increaseUnlockTime(uint256 tokenId, uint256 lockDuration)
0x2e1a7d4d -> withdraw(uint256 tokenId)        [after unlock]
0xd1c2babb -> merge(uint256 from, uint256 to)
0x4b19becc -> split(uint256 from, uint256 amount)
0xe75b1c2e -> lockPermanent(uint256 tokenId) · 0x35b0f6bd -> unlockPermanent(uint256 tokenId)
0x0ec84dda -> depositFor(uint256 tokenId, uint256 value)
0xe7e242d4 -> balanceOfNFT(uint256 tokenId) -> uint256     [current voting power]
0x6352211e -> ownerOf(uint256) · 0xfc0c546a -> token() -> address  [→ TOPAZ]
```

### 2.5 Gauge (v2) / Reward / Minter / RewardsDistributor / BonusLock
```
# Gauge (v2):
0xb6b55f25 -> deposit(uint256 amount) · 0x6e553f65 -> deposit(uint256 amount, address recipient)
0x2e1a7d4d -> withdraw(uint256 amount) · 0xc00007b0 -> getReward(address account)
0x3c6b16ab -> notifyRewardAmount(uint256 amount) · 0x008cc262 -> earned(address) · 0x72f702f3 -> stakingToken() · 0xf7c618c1 -> rewardToken()
# FeesVotingReward / BribeVotingReward:
0xf5f8d365 -> getReward(uint256 tokenId, address[] tokens) · 0xb66503cf -> notifyRewardAmount(address token, uint256 amount) · 0x3e491d47 -> earned(address token, uint256 tokenId) · 0xe2bbb158 -> deposit(uint256 amount, uint256 tokenId)
# Minter:  0xa83627de -> updatePeriod() -> uint256 period   ·   0x9008a642 -> nudge()
# RewardsDistributor:  0x379607f5 -> claim(uint256 tokenId) -> uint256   ·   0x925489a8 -> claimMany(uint256[] tokenIds) -> bool
# BonusLock (Topaz):  0xdd467064 -> lock(uint256 amount)   ·   0x088a2f02 -> lockWithExisting(uint256 tokenId, uint256 amount)   ·   0x6081f5cb -> calculateBonus(uint256 amount)   ·   0x813d6c9a -> bonusPercentage()
```

---

## 3. Addresses (BNB Smart Chain, id 56 — the only chain)

> ✓ = `eth_getCode` non-empty + wiring confirmed this run. All immutable (non-upgradeable) deploys.

### 3.1 Token + ve(3,3) core (shared with v3)
```
0xdf002282C1474C9592780618Adda7EaA99998Abd -> TOPAZ                 ERC-20 emissions token (symbol "TOPAZ", 18 dec) ✓
0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c -> WBNB                  wrapped native (Router/SwapRouter WETH9) ✓
0xe951aC65EFE86682311ab0d8995E7A58750c5eB3 -> VotingEscrow         veTOPAZ ERC-721 (token()→TOPAZ, symbol "veTOPAZ", 4y max lock) ✓
0x2F80F810a114223AC69E34E84E735CaD515dAD67 -> Voter                vote/createGauge/distribute (ve()→VE, minter()→Minter) ✓
0x606794d37991A426a189fD9FA8664D339A77f8ae -> Minter               weekly emissions; updatePeriod() (voter()→Voter) ✓
0x85e15e7Ad4f20d5ca3A1104B1c2CcE72f5F683dB -> RewardsDistributor   veTOPAZ rebase; claim(tokenId) ✓
0x268d1C8a538Ecf6628838C11d581e1EABD13D6A4 -> FactoryRegistry      whitelists factory tuples; poolFactories()→[PoolFactory,CLFactory] ✓
0xE79EB7c4D06ff38e6483921DE8e85A37eC7c731b -> Forwarder            ERC-2771 meta-tx forwarder (Voter.forwarder()) ✓
0x9612305fe63DFb84Da8f6d6261169F6B85026601 -> VeArtProxy           on-chain veTOPAZ NFT art ✓
0x7B1d8745079C85af80Ff7A7eA7C2C4769Eab5348 -> AirdropDistributor   initial veNFT airdrop (Topaz-only) ✓
0xeF6724ad68Fd2f8526765e08afa6627850c8a589 -> BalanceLogicLibrary  linked library (VE) ✓
0xCb24e31896d7476EFB7B76A366566cfbcf375033 -> DelegationLogicLibrary linked library (VE) ✓
```
> **Admin / governance = one team multisig** `0xf407739e81574a3C9a3195bcb85ee694C94E540c` (small contract, ~171 B). Verified on-chain it holds **all** of: `Voter.governor()`, `Voter.epochGovernor()`, `Voter.emergencyCouncil()`, `VotingEscrow.team()`, `VotingEscrow.allowedManager()`, and `Minter.team()`. The repo ships `EpochGovernor`/`ProtocolGovernor`/`VetoGovernor` contracts (events `ProposalCreated 0x7d84a6…`, `VoteCast 0x02ecdb7f…`, `ProposalExecuted 0x712ae1…`, `ProposalVetoed 0xde0cea…`, `ProposalCanceled 0x789cf5…`) but the live deployment currently routes those roles through the multisig — **no separate on-chain Governor is wired yet**. `VotingEscrow.distributor()` = RewardsDistributor (✓), `TOPAZ.minter()` = Minter (✓).
> A **`BonusLock`** contract (tiered lock-bonus campaign — see the live "Tier N of 7, 75% lock bonus" promo) is referenced by the app but is **not** in the published address list — discover it as the `msg.sender` of `BonusLocked`/`VeNFTDeposited` events, or as an approved operator on the veNFT.

### 3.2 v2 AMM
```
0x65E6cD0eF5D3467030103cf3d433034E570b5784 -> PoolFactory          createPool/getPool(a,b,stable); allPoolsLength=20; implementation()→Pool impl ✓
0xdC942D8e37cC20BCf9aD1Fe0111eE6c5908f3678 -> Pool (impl)           EIP-1167 clone master for every v2 pool — do NOT call directly ✓
0x1E98c8226e7d452e1888e3d3d2F929346321c6c3 -> Router               v2 swaps + add/removeLiquidity + zap (defaultFactory()→PoolFactory) ✓
0xFc080D1EcD7c332022cebf942AEb62d5E1d4Cb08 -> GaugeFactory         deploys v2 Gauge per pool (full deploy, not a clone) ✓
0x4C303f7af7b8b05226440e4e12FF9a82F513716c -> VotingRewardsFactory deploys the paired FeesVotingReward + BribeVotingReward ✓
0xe4b23F13b24232C1E68AD0575191216152AA9480 -> ManagedRewardsFactory deploys Free/LockedManagedReward (managed-NFT system) ✓
```
v2 fee defaults (read live): `volatileFee()=30` (0.30%), `stableFee()=5` (0.05%), `MAX_FEE()=300` (3%). Per-pool override via `setCustomFee`; read with `getFee(pool, stable)`.

### 3.3 Per-gauge contracts are dynamic (look up, don't hard-code)
```
gauge       = Voter.gauges(pool)            // 0x0 if no gauge
feeReward   = Voter.gaugeToFees(gauge)      // FeesVotingReward (trading fees → voters)
bribeReward = Voter.gaugeToBribe(gauge)     // BribeVotingReward (external incentives → voters)
pool        = Voter.poolForGauge(gauge)     // reverse
alive       = Voter.isAlive(gauge)          // false if killed
```
Same lookup works for v2 pools **and** v3 CL pools — the gauge type is fixed at `createGauge(factory, pool)` time. (Example live wiring: v2 pool `0xfd687f1a…bdb7a` → gauge `0x36006de2…f0d8` (full deploy) → fees `0xfb27e4a4…7809` / bribe `0xf737f14c…a879`.)

---

## 4. Proxies

- **v2 Pools: EIP-1167 minimal-proxy clones** of `Pool (impl) 0xdC94…3678`, CREATE2-deployed by `PoolFactory` (salt = `keccak256(token0,token1,stable)`). A pool's `eth_getCode` is the 45-byte stub `363d3d373d3d3d363d73⟨dc94…3678⟩5af43d82803e903d91602b57fd5bf3` (verified). Clones are **immutable** — the impl can't be upgraded; enumerate via `PoolCreated`.
- **v2 Gauges: full deploys** (`new Gauge(...)` via `GaugeFactory`), **not clones** (live gauge `0x3600…f0d8` is ~6 KB of real code). `FeesVotingReward`/`BribeVotingReward` are likewise full deploys (~5.3 KB).
- **ve(3,3) core (Voter, VotingEscrow, Minter, RewardsDistributor, Router, factories, registry, Forwarder, VeArtProxy, AirdropDistributor): plain immutable deploys — NO EIP-1967 transparent/UUPS/beacon proxy anywhere.** `implementation()`/`poolImplementation()` on the factories return clone *masters*, not proxy impls. The team confirms Pool/Gauge/VotingEscrow/Voter/Minter/RewardsDistributor/Governors are *not upgradable*.
- **Upgrade path = `FactoryRegistry`, not in-place proxy upgrades** (this is the protocol's only "old vs new" axis). The admin multisig can approve **new factory generations** (a `(poolFactory, votingRewardsFactory, gaugeFactory)` tuple) in `FactoryRegistry`; new pools/gauges then deploy from the new factory while existing pools/positions are **not** force-migrated. Today `FactoryRegistry.poolFactories()` = `[PoolFactory 0x65E6…5784, CLFactory 0x73DC…2ed9]` (one generation each). Detection: enumerate factory generations via `FactoryRegistry`, then `PoolCreated` per factory — don't expect impl-slot upgrades. (v3/Slipstream pool & gauge clones are in [`slipstream.md`](slipstream.md).)

See `references/proxies.md` for EIP-1167 detection details.

---

## 5. Detection invariants & gotchas

1. **BNB Chain (56) only.** No Topaz on ETH/Base/Arb/OP/Avax/Polygon (verified empty bytecode).
2. **v2 `Swap` topic0 `0xb3e27736…` ≠ Uniswap V2 `Swap` `0xd78ad95f…`** — different arg layout (`amount0In,amount1In,amount0Out,amount1Out`). Don't reuse the Uni V2 constant.
3. **Same-name topic0 collisions** (disambiguate by emitting contract): `Mint(address,uint256,uint256)` `0x4c209b5f…` = Uni V2/Sushi Mint; `Sync(uint256,uint256)` `0xcf2aa508…` = Sushi Trident; veNFT `Supply` `0x5e2aa66e…` = Curve/Balancer; Gauge `Withdraw(address,uint256)` `0x884edad9…` = Curve/Balancer gauge.
4. **Three different `NotifyReward` topics:** Voter `(address,address,uint256)` `0xf70d5c69…`; Gauge/CLGauge `(address,uint256)` `0x09566775…`; Fees/Bribe Reward `(address,address,uint256,uint256)` `0x52977ea9…`. Don't conflate.
5. **`ClaimRewards(address,uint256)` `0x1f89f96…` is shared by v2 Gauge and CLGauge** — disambiguate by gauge address (is it `poolForGauge` a v2 or CL pool?).
6. **veTOPAZ is an ERC-721 NFT** — locks/votes keyed by `tokenId`; escrow emits ERC-721 `Transfer`/`Approval`/`ApprovalForAll` + ERC-4906 `MetadataUpdate`. `Deposit`'s `depositType` is an **enum → encoded `uint8`** (topic `0x8835c22a…`); using `DepositType` literally gives a wrong hash.
7. **`bool stable` everywhere** (`PoolCreated`, `getPool`, `getFee`) separates stable (`x³y+xy³`) from volatile (`xy=k`) pools — a pair can have both.
8. **v2 `SetCustomFee(address,uint256)` `0xae468ce5…` ≠ CL `SetCustomFee(address,uint24)` `0xd444e1b1…`** — different types → different topic0.
9. **Bytea hex literals need an even digit count** (40 for addresses, 64 for topics).

---

## 6. Quick-copy (Postgres `bytea`-ready)
```
-- v2 Pool Swap / Sync
swap_v2   = '\xb3e2773606abfd36b5bd91394b3a54d1398336c65005baf7bf7a05efeffaf75b'
sync_v2   = '\xcf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a'
poolcreated_v2 = '\x2128d88d14c80cb081c1252a5acff7a264671bf199ce226b53788fb26065005e'
-- ve(3,3)
voted     = '\x452d440efc30dfa14a0ef803ccb55936af860ec6a6960ed27f129bef913f296a'
ve_deposit= '\x8835c22a0c751188de86681e15904223c054bedd5c68ec8858945b7831290273'
gaugecreated = '\xef9f7d1ffff3b249c6b9bf2528499e935f7d96bb6d6ec4e7da504d1d3c6279e1'
distrib_reward = '\x4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17'
-- key addresses
topaz   = '\xdf002282c1474c9592780618adda7eaa99998abd'
voter   = '\x2f80f810a114223ac69e34e84e735cad515dad67'
ve      = '\xe951ac65efe86682311ab0d8995e7a58750c5eb3'
minter  = '\x606794d37991a426a189fd9fa8664d339a77f8ae'
poolfactory = '\x65e6cd0ef5d3467030103cf3d433034e570b5784'
router  = '\x1e98c8226e7d452e1888e3d3d2f929346321c6c3'
```

## 7. Verification & sources
- topic0/selectors: keccak (pycryptodome) over canonical signatures parsed from [`topazdex/topaz-contacts`](https://github.com/topazdex/topaz-contacts) interfaces; pipeline cross-validated against already-verified `aerodrome/amm.md` (`swapExactTokensForTokens 0xcac88ea9`, `getPool 0x79bc57d5`, `vote 0x7ac09bf7`) and `uniswap` (`swap 0x022c0d9f`).
- on-chain (BSC, `bsc-rpc.publicnode.com`, 2026-06-05): all §3 addresses have bytecode; `TOPAZ.symbol/decimals`, `VotingEscrow.token/voter/symbol`, `Voter.ve/minter/factoryRegistry/forwarder`, `Minter.voter`, `PoolFactory.implementation/voter/allPoolsLength`, `Router.defaultFactory/voter`, `FactoryRegistry.poolFactories` all confirmed; v2 pool clone bytecode embeds `Pool impl`; live `eth_getLogs` saw `Swap`/`Sync` (pool), `Voted`/`Abstained` (Voter), `Deposit`(enum)/`Supply`/`Merge`/`Split`/`UnlockPermanent`/`Transfer` (VE), `ClaimRewards` (gauge). Rare creation/emission events (`PoolCreated`, `GaugeCreated`, `Minter.Mint`) verified by canonical-source keccak (public node prunes old logs).
- Addresses cross-checked against [`agent-skill/references/addresses.md`](https://github.com/topazdex/agent-skill) and [docs.topazdex.com/docs/contracts](https://topazdex.com/docs/contracts) (BscScan-verified).
- Audit: [Shieldify Security — Topaz DEX Security Review](https://github.com/shieldify-security/audits-portfolio/blob/main/reports/Topaz-Dex-Security-Review.pdf) (ve(3,3) lock/voting, gauge factory, bribe markets, fee distribution, Slipstream CL). No known Topaz exploit/incident as of 2026-06-05.
