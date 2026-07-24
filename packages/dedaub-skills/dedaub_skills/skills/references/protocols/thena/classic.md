# THENA Finance — Classic AMM + Governance (Solidly/ve(3,3)) — Topics, Selectors, Addresses (BNB Smart Chain)

**Status:** Verified — all addresses confirmed via `eth_getCode` on BNB Smart Chain (chainId 56); absent (`0x`) on all other target chains (Ethereum 1, Base 8453, Arbitrum 42161, Optimism 10, Polygon 137). topic0s cross-checked against live `eth_getLogs` on BNB Smart Chain. Pair events confirmed at block 103552897; VoterV3 Vote/Reset events confirmed at block 103596311; VotingEscrow Deposit/Supply events confirmed at block 103585823; Bribe Staked event confirmed at block 103545653.
**Sources:** [ThenafiBNB/THENA-Contracts](https://github.com/ThenafiBNB/THENA-Contracts) · live `eth_getLogs` and `eth_getStorageAt` cross-checks on BNB Smart Chain · keccak256 computed locally · [THENA docs](https://docs.thena.fi) · THENA contract spreadsheet.
**Last verified:** 2026-06-11

---

## 0. Contract families

| Family | Contracts | Role |
|--------|-----------|------|
| **Classic AMM** | PairFactory (proxy), Pair (per pair, stable+volatile), RouterV2 | Pool creation, stable/volatile AMM swaps, LP management |
| **Governance** | THE (ERC-20 governance token), VotingEscrow (veTHE veNFT) | Token + ve-locking |
| **Voter** | VoterV3 (non-proxy) | Epoch voting, pool weight allocation, gauge management |
| **Epoch Distribution** | EpochDistributorBSC (proxy) | Weekly THE emission distribution to gauges |
| **Gauges/Incentives** | GaugeFactory, GaugeV2 (per gauge), VotingIncentivesFactory, Bribe (per gauge) | LP reward farming, vote incentives |
| **Minter** | MinterUpgradeable (proxy) | Weekly THE emission via `update_period()` |
| **Distributions** | RewardsDistributor | veTHE holders claim protocol yield |
| **Misc** | VeArtProxy, VotingEscrowAttach | NFT art, veTHE attachment utilities |

**Architecture note:** THENA Classic is a Solidly/ve(3,3) fork on BNB Smart Chain — the original that Blackhole (Avalanche) and Ramses (Arbitrum) later forked from. Classic pairs have two types (stable=true / volatile=false) distinguished by the `stable()` flag on each Pair. The deployed VoterV3 (0x8FBB1EC...) uses **modified event signatures** compared to the GitHub VoterV3.sol: the deployed voter emits `Vote` and `Reset` (not `Voted`/`Abstained`), with `(address voter, uint256 indexed tokenId, uint256 epoch)` parameter layout. Gauge creation goes through `GaugeFactory` (0x479cE658), and bribes/voting incentives are managed by `VotingIncentivesFactory` (0x82f144ac). The `EpochDistributorBSC` (0x3005b0d3) is a separate proxy contract that handles weekly gauge reward distribution; it is NOT the Voter.

**Proxy pattern:** MinterUpgradeable and PairFactory are `TransparentUpgradeableProxy` sharing ProxyAdmin `0x8b9ca04656a74e218ecbd444c493872d19533e06` (owner: `0x5d7deb17be6c6243d6d65205b5293edceb676561`). EpochDistributorBSC is a `TransparentUpgradeableProxy` with ProxyAdmin `0xc06cb27ebb868fa197a24f399680ab674de04575` (owner: `0x993ae2b514677c7ac52baecd8871d2b362a9d693`). VoterV3, VotingEscrow, RouterV2, GaugeFactory, VotingIncentivesFactory, and RewardsDistributor are **non-upgradeable**.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 PairFactory
Source: `ThenafiBNB/THENA-Contracts/contracts/factories/PairFactory.sol` + `PairFactoryUpgradeable.sol`. topic0 confirmed in PairFactory implementation bytecode (0x879f8fd3).

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xc4805696c66d7cf352fc1d6bb633ad5ee82f6cb577c453024b6e0eb8306c6fc9` | `PairCreated(address indexed token0, address indexed token1, bool stable, address pair, uint256 count)` | **★ subscribe to discover all Classic pairs.** `stable=true` → stable pair; `false` → volatile. `bool stable` is 3rd (non-indexed) before the pair address. Identical signature to Blackhole/Velodrome V1. |

> **PairCreated signature note:** Full signature `PairCreated(address,address,bool,address,uint256)`. The `bool stable` precedes the pair address in non-indexed data (differs from Uniswap V2's `PairCreated(address,address,address,uint256)`).

### 1.2 Pair (per-pair AMM)
Source: `ThenafiBNB/THENA-Contracts/contracts/Pair.sol`. All topic0s confirmed in PairFactory implementation bytecode (0x879f8fd3); `Fees` and `Sync` confirmed live at block 103552897.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822` | `Swap(address indexed sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, address indexed to)` | **★ workhorse swap event.** Identical layout to Uniswap V2. |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address indexed sender, uint256 amount0, uint256 amount1)` | LP deposit. |
| `0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496` | `Burn(address indexed sender, uint256 amount0, uint256 amount1, address indexed to)` | LP withdrawal. |
| `0xcf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a` | `Sync(uint256 reserve0, uint256 reserve1)` | Reserve update. Confirmed live at block 103552897. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 LP token transfer. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ERC-20 LP token approval. |
| `0x112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602` | `Fees(address indexed sender, uint256 amount0, uint256 amount1)` | Solidly fee-split event: protocol fees separated from swap fees. Confirmed live at block 103552897. |

> Each Pair address is discoverable from `PairFactory.allPairs(index)` (787 pairs total) or from `PairCreated` events. Stable and volatile pairs share the same event ABIs; distinguish by calling `pair.stable()` → `bool`. The pair count can be read via `PairFactory.allPairsLength()`.

### 1.3 VoterV3 (non-proxy)
Source: Deployed contract at `0x8FBB1ECEbb9E9839bC0dE00b9c4C585CabDD0462`. The deployed VoterV3 uses **different event signatures** from the GitHub source — `Vote` and `Reset` replace the GitHub's `Voted` and `Abstained`. Both confirmed live at block 103596311 and 103545653.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xafd3f234c1f8e944129b26b206d98e5752ad3336a4059938b4a3e990e9588530` | `Vote(address voter, uint256 indexed tokenId, uint256 epoch)` | **★ fired for each pool a veNFT votes for.** topic1 = tokenId; data = (voter address, epoch timestamp). Confirmed live at block 103596311. |
| `0xf054db3316438c563ccda1bcd9cc2c2c54b88f26c0248b5cfd017aa2111cf133` | `Reset(address voter, uint256 indexed tokenId, uint256 epoch)` | **★ fired for each pool whose vote is reset before re-voting.** Emitted BEFORE `Vote` in the same tx for each pool. Same data layout as Vote. Confirmed live at block 103596311. |
| `0xd0d5ea94cd49e02322e6b063a8bb973906359789fa370a54261e226b9592b5e2` | `BanPool(address)` | Pool banned from receiving votes. |
| `0x0719c8bc6522957e7735717af2894124fbc9096cf04b5bfaabcff51577908765` | `RemovePool(address)` | Pool removed. |
| `0x1201338058da8a5c7cb6da92ee0dd23d5a813f82564aaa9b8371d36e9f779a07` | `RevivePool(address)` | Banned pool revived. |
| `0x2c0e460d92a73502decde52c29ae030dd8872be648a35b2b71fd47725c3a8c5a` | `SetManagerStatus(address,bool)` | Manager status updated. |

> **Voting note:** `vote(uint256 tokenId, address[] poolVote, uint256[] weights)` first resets all previous votes for `tokenId` (emitting `Reset` per old pool), then casts new votes (emitting `Vote` per new pool). A voter with no prior votes only emits `Vote`. Subscribe to both topic0s on VoterV3 to track all vote changes. The `epoch` field in the data is the active epoch start timestamp.

> **Gauge discovery note:** The VoterV3 (deployed version) does NOT emit a `GaugeCreated` event. Use `VoterV3.gaugeForPool(pool)` to look up gauge addresses, or enumerate pools via `VoterV3.pools()` (returns all 186 registered pools). `VoterV3.poolsLength()` returns the count.

### 1.4 EpochDistributorBSC (proxy — NOT the VoterV3)
Source: Deployed at `0x3005b0d329141d75b62CCeEe57BF00153fE26074`, impl `0xe84a0Ab90cd7825357a62418cc71277f8c8887a7`. This contract handles weekly gauge reward distribution; it is **not** the voting contract. Events are identified from bytecode PUSH32 patterns but no recent live confirmation (requires epoch boundary).

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17` | `DistributeReward(address indexed sender, address indexed gauge, uint256 amount)` | Weekly THE distributed to a gauge. |
| `0xf70d5c697de7ea828df48e5c4573cb2194c659f1901f70110c52b066dcf50826` | `NotifyReward(address indexed sender, address indexed reward, uint256 amount)` | Reward token notified. |

### 1.5 GaugeV2 (per gauge)
Source: `ThenafiBNB/THENA-Contracts/contracts/GaugeV2.sol`. Confirmed in deployed gauge bytecode.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | `Deposit(address indexed user, uint256 amount)` | **★ LP staked into gauge.** Note: parameter is `user` (not `from` as in Uniswap-derived variants). |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | `Withdraw(address indexed user, uint256 amount)` | **★ LP unstaked from gauge.** |
| `0xc9695243a805adb74c91f28311176c65b417e842d5699893cef56d18bfa48cba` | `Harvest(address indexed user, uint256 reward)` | Gauge reward claimed by staker. |
| `0xbc567d6cbad26368064baa0ab5a757be46aae4d70f707f9203d9d9b6c8ccbfa3` | `ClaimFees(address indexed from, uint256 claimed0, uint256 claimed1)` | Swap fees claimed by gauge. |
| `0xde88a922e0d3b88b24e9623efeb464919c6bf9f66857a65e2bfcf2ce87a9433d` | `RewardAdded(uint256 reward)` | Reward amount added (no indexed params; reward rate update). |

### 1.6 Bribe / VotingIncentives (per gauge)
Source: `ThenafiBNB/THENA-Contracts/contracts/Bribes.sol`. Confirmed live at block 103545653 (Staked event from both internal bribe 0x21e409... and external bribe 0xB6c78D...).

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x925435fa7e37e5d9555bb18ce0d62bb9627d0846942e58e5291e9a2dded462ed` | `Staked(uint256 indexed tokenId, uint256 amount)` | **★ veNFT weight staked into bribe (on vote).** Confirmed live at block 103545653. |
| `0x0c875c8d391179c5cf7ad8303d268efd50b8beb78b671f85cd54bfb91eb8ef40` | `Withdrawn(uint256 indexed tokenId, uint256 amount)` | **★ veNFT weight withdrawn from bribe (on reset).** |
| `0x6a6f77044107a33658235d41bedbbaf2fe9ccdceb313143c947a5e76e1ec8474` | `RewardAdded(address indexed rewardToken, uint256 reward, uint256 startTimestamp)` | New bribe incentive added. |
| `0x540798df468d7b23d11f156fdb954cb19ad414d150722a7b6d55ba369dea792e` | `RewardPaid(address indexed user, address indexed rewardsToken, uint256 reward)` | Bribe reward paid to claimant. |

> Each gauge has one internal bribe and one external bribe. Both emit `Staked` when a veNFT votes for the associated pool. Discover bribe addresses from `VoterV3.votingIncentivesForPool(pool)` or from the pool's gauge storage.

### 1.7 MinterUpgradeable (proxy)
Source: `ThenafiBNB/THENA-Contracts/contracts/MinterUpgradeable.sol`. Confirmed in Minter implementation bytecode (`0x6c1a357f`). Mint events fire once per week when `update_period()` is called (after the active epoch expires).

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xb4c03061fb5b7fed76389d5af8f2e0ddb09f8c70d1333abbb62582835e10accb` | `Mint(address indexed sender, uint256 weekly, uint256 circulating_supply, uint256 circulating_emission)` | **★ epoch emission.** Fires once per week. `sender` = caller of `update_period()`. Parameter order: `weekly`, then `circulating_supply`, then `circulating_emission` (note: differs from some Solidly forks where `circulating_emission` comes before `circulating_supply`). |

### 1.8 VotingEscrow (veTHE, ERC-721 veNFT)
Source: `ThenafiBNB/THENA-Contracts/contracts/VotingEscrow.sol`. Confirmed live: Deposit at block 103585823, Supply at block 103585823. VotingEscrow is **non-upgradeable**.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xff04ccafc360e16b67d682d17bd9503c4c6b9a131f6be6325762dc9ffc7de624` | `Deposit(address indexed provider, uint256 tokenId, uint256 value, uint256 indexed locktime, uint8 deposit_type, uint256 ts)` | **★ fired for ALL lock operations** (create, add, withdraw). topic1 = provider address. topic2 = locktime (future expiry Unix timestamp): **non-zero for CREATE_LOCK and ADD_TO_LOCK**, zero for WITHDRAW. `deposit_type` (data byte 2): 0=WITHDRAW, 1=CREATE_LOCK, 2=ADD_TO_LOCK. Confirmed live at block 103585823 (topic1 = RewardsDistributor 0xa6e0e731, topic2 = non-zero locktime). |
| `0x02f25270a4d87bea75db541cdfe559334a275b4a233520ed6c0a2429667cca94` | `Withdraw(address indexed provider, uint256 tokenId, uint256 value, uint256 ts)` | Unlock event (lock expired). |
| `0x5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c` | `Supply(uint256 prevSupply, uint256 supply)` | Total locked THE supply change. No indexed params. Confirmed live at block 103585823. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 indexed tokenId)` | ERC-721 veNFT transfer (3 indexed params, empty data). |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed approved, uint256 indexed tokenId)` | ERC-721 approval. |
| `0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31` | `ApprovalForAll(address indexed owner, address indexed operator, bool approved)` | ERC-721 operator approval. |

### 1.9 RewardsDistributor
Source: `ThenafiBNB/THENA-Contracts/contracts/RewardsDistributor.sol`. topic0s confirmed in RewardsDistributor bytecode at `0xa6e0e731cb1e99aede0f9c9128d04f948e18727d`.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xcae2990aa9af8eb1c64713b7eddb3a80bf18e49a94a13fe0d0002b5d61d58f00` | `Claimed(uint256 tokenId, uint256 amount, uint256 claim_epoch, uint256 max_epoch)` | **★ veTHE holder claims protocol yield.** No indexed params. |
| `0xce749457b74e10f393f2c6b1ce4261b78791376db5a3f501477a809f03f500d6` | `CheckpointToken(uint256 time, uint256 tokens)` | Token checkpoint (weekly). |

### 1.10 THE token (ERC-20)
Standard ERC-20 events only:

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |

---

## 2. Function signatures (chain-agnostic)

### 2.1 RouterV2
Native token on BNB = BNB (not AVAX/ETH). Selectors confirmed in RouterV2 bytecode (0xd4ae6eca).

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf41766d8` | `swapExactTokensForTokens(uint256 amountIn, uint256 amountOutMin, (address from, address to, bool stable)[] routes, address to, uint256 deadline)` | Token→token swap. |
| `0x67ffb66a` | `swapExactETHForTokens(uint256 amountOutMin, (address,address,bool)[] routes, address to, uint256 deadline)` | Native BNB → token. |
| `0x18a13086` | `swapExactTokensForETH(uint256 amountIn, uint256 amountOutMin, (address,address,bool)[] routes, address to, uint256 deadline)` | Token → native BNB. |
| `0x6cc1ae13` | `swapExactTokensForTokensSupportingFeeOnTransferTokens(uint256,uint256,(address,address,bool)[],address,uint256)` | FOT token swap. |
| `0x76c72751` | `swapExactETHForTokensSupportingFeeOnTransferTokens(uint256,(address,address,bool)[],address,uint256)` | BNB → FOT token. |
| `0x7af728c8` | `swapExactTokensForETHSupportingFeeOnTransferTokens(uint256,uint256,(address,address,bool)[],address,uint256)` | FOT token → BNB. |
| `0x5a47ddc3` | `addLiquidity(address tokenA, address tokenB, bool stable, uint256 amountADesired, uint256 amountBDesired, uint256 amountAMin, uint256 amountBMin, address to, uint256 deadline)` | Add LP. |
| `0xb7e0d4c0` | `addLiquidityETH(address token, bool stable, uint256 amountTokenDesired, uint256 amountTokenMin, uint256 amountETHMin, address to, uint256 deadline)` | Add LP with native BNB. |
| `0x0dede6c4` | `removeLiquidity(address tokenA, address tokenB, bool stable, uint256 liquidity, uint256 amountAMin, uint256 amountBMin, address to, uint256 deadline)` | Remove LP. |
| `0xd7b0e0a5` | `removeLiquidityETH(address token, bool stable, uint256 liquidity, uint256 amountTokenMin, uint256 amountETHMin, address to, uint256 deadline)` | Remove LP + unwrap BNB. |

### 2.2 PairFactory
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x82dfdce4` | `createPair(address tokenA, address tokenB, bool stable)` | Creates a new stable or volatile pair. Emits `PairCreated`. |

### 2.3 VoterV3 (non-proxy)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7ac09bf7` | `vote(uint256 tokenId, address[] poolVote, uint256[] weights)` | Cast votes for pools with a veTHE NFT. Emits `Reset` per old pool then `Vote` per new pool. |
| `0x310bd74b` | `reset(uint256 tokenId)` | Reset all votes for a veTHE NFT. Emits `Reset` per voted pool; also emits `Withdrawn` from bribes. |
| `0x32145f90` | `poke(uint256 tokenId)` | Refresh vote weights (re-vote with same pools). |
| `0x7715ee75` | `claimBribes(address[] bribes, address[][] tokens, uint256 tokenId)` | Claim bribe rewards for a veNFT. |
| `0x666256aa` | `claimFees(address[] fees, address[][] tokens, uint256 tokenId)` | Claim internal bribe (swap fee) rewards. |
| `0x20b1cb6f` | `claimRewards(address[] gauges, address[][] tokens)` | Claim gauge rewards for LP stakers. |
| `0xdcd9e47a` | `createGauge(address pool, uint256 gaugeType)` | Create gauge for a pool. No `GaugeCreated` event is emitted by this deployed version. |
| `0x63453ae1` | `distribute(address gauge)` | Trigger reward distribution to a specific gauge. |

### 2.4 VotingEscrow
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x65fc3873` | `create_lock(uint256 value, uint256 lockDuration)` | Create a new veTHE lock. |
| `0xa183af52` | `increase_amount(uint256 tokenId, uint256 value)` | Add to an existing lock. |
| `0xa4d855df` | `increase_unlock_time(uint256 tokenId, uint256 lockDuration)` | Extend lock duration. |
| `0x2e1a7d4d` | `withdraw(uint256 tokenId)` | Withdraw expired lock. |
| `0xd1c2babb` | `merge(uint256 from, uint256 to)` | Merge two veTHE NFTs. |
| `0x56afe744` | `split(uint256[] amounts, uint256 tokenId)` | Split a veTHE NFT. |

### 2.5 GaugeV2 (per gauge)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe2bbb158` | `deposit(uint256 amount, uint256 tokenId)` | Stake LP tokens into gauge. |
| `0x2e1a7d4d` | `withdraw(uint256 amount)` | Unstake LP tokens. |
| `0x31279d3d` | `getReward(address account, address[] tokens)` | Claim gauge rewards. |
| `0xb66503cf` | `notifyRewardAmount(address token, uint256 amount)` | Add reward to gauge. |

### 2.6 MinterUpgradeable (proxy → impl `0x6c1a357f0d737a889ea6b0321257d6d4ca664dfe`)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xed29fc11` | `update_period()` | Advance epoch, mint weekly THE emission. Callable by anyone once per week. `active_period()` returns the current epoch start (currently `0x6a29fa80` = ~June 11 2026). |

### 2.7 RewardsDistributor
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x379607f5` | `claim(uint256 tokenId)` | Claim accumulated protocol yield for a veTHE NFT. |
| `0x1f1db043` | `claim_many(uint256[] tokenIds)` | Batch claim for multiple veTHE NFTs. |

---

## 3. Addresses

### 3.1 BNB Smart Chain (chainId 56) — **only deployed chain**

| Contract | Address | Notes |
|----------|---------|-------|
| **THE token** | `0xF4C8E32EaDEC4BFe97E0F595AdD0f4450a863a11` | `name()="THENA"`, `symbol()="THE"`. ERC-20. Non-upgradeable. `minter()` = MinterUpgradeable. |
| **RouterV2** | `0xd4ae6eCA985340Dd434D38F470aCCce4DC78d109` | Non-upgradeable. `factory()` = PairFactory. |
| **PairFactory** | `0xAFD89d21BdB66d00817d4153E055830B1c2B3970` | **Proxy** (TransparentUpgradeableProxy). Impl: `0x879f8Fd307Ba4442E22e77d47683f35313760dC8`. Admin: `0x8b9ca04656a74e218ecbd444c493872d19533e06`. `allPairsLength()=787`. `stableFee()=1` bp, `volatileFee()=20` bp. |
| **VotingEscrow** (veTHE) | `0xfBBF371C9B0B994EebFcC977CEf603F7f31c070D` | `name()="veThena"`, `symbol()="veTHE"`. ERC-721 veNFT. **Non-upgradeable** (no proxy slots). `token()` = THE. `supply()` = total locked THE. `epoch()` = `0x542d3` (current). |
| **VoterV3** | `0x8FBB1ECEbb9E9839bC0dE00b9c4C585CabDD0462` | **Non-upgradeable.** The primary active voter. `minter()` = MinterUpgradeable. `ve()` = VotingEscrow. `poolsLength()` = 186. `pools()` returns all registered pools. `gaugeForPool(pool)` returns gauge address. `attach()` = VotingEscrowAttach. |
| **EpochDistributorBSC** | `0x3005b0d329141d75b62CCeEe57BF00153fE26074` | **Proxy** (TransparentUpgradeableProxy). Impl: `0xe84a0Ab90cd7825357a62418cc71277f8c8887a7`. Admin: `0xc06cb27ebb868fa197a24f399680ab674de04575`. Handles weekly gauge reward distribution; NOT the voting contract. `voter()` = VoterV3. `token()` = THE. |
| **MinterUpgradeable** | `0x86069FEb223EE303085a1A505892c9D4BdBEE996` | **Proxy** (TransparentUpgradeableProxy). Impl: `0x6c1a357f0d737a889ea6b0321257d6d4ca664dfe`. Admin: `0x8b9ca04656a74e218ecbd444c493872d19533e06`. `active_period()=0x6a29fa80` (~June 11, 2026). `weekly()` = current weekly emission. |
| **GaugeFactory** | `0x479cE658DD4195556C60Ea9fdE92cF0F42EA8692` | **Non-upgradeable.** Creates GaugeV2 contracts via `createGaugeV2(...)`. Role-based access control (CREATE_ROLE, CLAIMER_ROLE). |
| **VotingIncentivesFactory** | `0x82f144accf4779ca8c49928be28fac5fa157d218` | **Non-upgradeable.** Creates Bribe/VotingIncentives contracts via `createBribe(...)`. Functions as BribeFactory. `createVotingIncentives` deploys per-pool bribe contracts. |
| **RewardsDistributor** | `0xa6e0e731cb1e99aede0f9c9128d04f948e18727d` | **Non-upgradeable.** Distributes protocol yield to veTHE holders. `token()` = THE. `voting_escrow()` = VotingEscrow. `depositor()` = MinterUpgradeable. `start_time()` = `0x6542e680`. |
| **VeArtProxy** | `0xb2b37c4221dabfff5b34883e95d88d498f03e516` | **Non-upgradeable.** Returns veTHE SVG art. `artProxy()` on VotingEscrow. |
| **VotingEscrowAttach** | `0x8aEBEd1f28a8ae1Eb6479DDd8b1148da0E05B58D` | **Non-upgradeable.** Manages veTHE attachment states. `ve()` = VotingEscrow. Called `attach()` on VoterV3. |
| **ProxyAdmin (Minter/PairFactory)** | `0x8b9ca04656a74e218ecbd444c493872d19533e06` | Admin for MinterUpgradeable and PairFactory. `owner()=0x5d7deb17be6c6243d6d65205b5293edceb676561`. |
| **ProxyAdmin (EpochDist)** | `0xc06cb27ebb868fa197a24f399680ab674de04575` | Admin for EpochDistributorBSC. `owner()=0x993ae2b514677c7ac52baecd8871d2b362a9d693` (THENA multisig). |

> **Pair and gauge discovery:** Use `PairFactory.allPairs(index)` (index 0…786) to enumerate all 787 Classic pairs. Use `VoterV3.gaugeForPool(pairAddress)` to get the GaugeV2 for any pool. `VoterV3.votingIncentivesForPool(pairAddress)` returns the voting incentives (bribe) contract. Subscribe to `PairCreated` (topic0 `0xc4805696…`) on PairFactory to discover new pairs.

### 3.2 All other target chains — absent

| Chain | chainId | All THENA Classic contracts |
|-------|---------|----------------------------|
| Ethereum | 1 | `0x` — not deployed |
| Base | 8453 | `0x` — not deployed |
| Arbitrum One | 42161 | `0x` — not deployed |
| Optimism | 10 | `0x` — not deployed |
| Polygon PoS | 137 | `0x` — not deployed |

Verified: `eth_getCode` on THE token (`0xF4C8E32E…`) returns `0x` on all five chains above.

---

## 4. Quick-copy bytea block

```
-- PairFactory: new pair created
\x c4805696c66d7cf352fc1d6bb633ad5ee82f6cb577c453024b6e0eb8306c6fc9

-- Pair: swap
\x d78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822
-- Pair: mint (LP deposit)
\x 4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f
-- Pair: burn (LP withdrawal)
\x dccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496
-- Pair: sync (reserve update) [confirmed block 103552897]
\x cf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a
-- Pair: fees (protocol fee split) [confirmed block 103552897]
\x 112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602

-- VoterV3: vote cast for a pool [confirmed block 103596311]
\x afd3f234c1f8e944129b26b206d98e5752ad3336a4059938b4a3e990e9588530
-- VoterV3: vote reset for a pool [confirmed block 103596311]
\x f054db3316438c563ccda1bcd9cc2c2c54b88f26c0248b5cfd017aa2111cf133

-- GaugeV2: LP staked
\x e1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c
-- GaugeV2: LP unstaked
\x 884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364
-- GaugeV2: reward harvested
\x c9695243a805adb74c91f28311176c65b417e842d5699893cef56d18bfa48cba

-- EpochDistributorBSC: distribute reward to gauge
\x 4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17
-- EpochDistributorBSC: notify reward
\x f70d5c697de7ea828df48e5c4573cb2194c659f1901f70110c52b066dcf50826

-- Bribe/VotingIncentives: veNFT weight staked (on vote) [confirmed block 103545653]
\x 925435fa7e37e5d9555bb18ce0d62bb9627d0846942e58e5291e9a2dded462ed
-- Bribe/VotingIncentives: veNFT weight withdrawn (on reset)
\x 0c875c8d391179c5cf7ad8303d268efd50b8beb78b671f85cd54bfb91eb8ef40

-- MinterUpgradeable: epoch mint (weekly THE emission)
\x b4c03061fb5b7fed76389d5af8f2e0ddb09f8c70d1333abbb62582835e10accb

-- VotingEscrow: Deposit (create/add/withdraw — all share this topic0; topic2=locktime, non-zero for CREATE_LOCK/ADD) [confirmed block 103585823]
\x ff04ccafc360e16b67d682d17bd9503c4c6b9a131f6be6325762dc9ffc7de624
-- VotingEscrow: withdraw expired lock
\x 02f25270a4d87bea75db541cdfe559334a275b4a233520ed6c0a2429667cca94
-- VotingEscrow: total supply change [confirmed block 103585823]
\x 5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c

-- RewardsDistributor: yield claimed by veTHE holder
\x cae2990aa9af8eb1c64713b7eddb3a80bf18e49a94a13fe0d0002b5d61d58f00
-- RewardsDistributor: token checkpoint
\x ce749457b74e10f393f2c6b1ce4261b78791376db5a3f501477a809f03f500d6

-- ERC-20 / ERC-721 standard (THE, LP tokens, veTHE)
\x ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  -- Transfer
\x 8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  -- Approval
\x 17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31  -- ApprovalForAll
```

---

## 5. Notes / architectural differences vs forks

- **VoterV3 events differ from GitHub source:** The deployed VoterV3 (`0x8FBB1EC…`) does NOT emit `Voted(address indexed voter, uint256 tokenId, uint256 weight)` or `Abstained(uint256 tokenId, uint256 weight)` as shown in the repo. Instead it emits `Vote(address voter, uint256 indexed tokenId, uint256 epoch)` (`0xafd3f234`) and `Reset(address voter, uint256 indexed tokenId, uint256 epoch)` (`0xf054db33`). The epoch field encodes the active epoch start timestamp, not a weight. **Do not use Blackhole/Ramses VoterV3 topic0s for THENA.**

- **No GaugeCreated event:** Neither VoterV3 nor GaugeFactory emits a `GaugeCreated` event in the deployed version. Use `VoterV3.pools()` + `VoterV3.gaugeForPool(pool)` to enumerate all 186 gauges on-chain.

- **EpochDistributorBSC ≠ VoterV3:** The address `0x3005b0d3…` (originally passed as "Voter") is actually EpochDistributorBSC — a distribution helper proxy. The true Voter is `0x8FBB1EC…`. Both have `minter()` returning the Minter and reference VoterV3 internally.

- **VotingEscrow `Deposit` event — topic2 is `locktime`:** Same as Blackhole: `deposit_type` field in data `[2]`: 0=WITHDRAW (zero locktime), 1=CREATE_LOCK (non-zero locktime), 2=ADD_TO_LOCK (non-zero locktime). Monitor on `topic0=0xff04ccaf` + address=VotingEscrow and filter on data[2] for specific operation type.

- **VoterV3 Vote ordering:** In the same `vote()` transaction, `Reset` events fire BEFORE the corresponding `Vote` events (old votes cleared first, then new votes set). Between each Reset and its corresponding Vote: the bribe `Withdrawn` event fires (clearing old bribe stake), then VotingEscrowAttach emits, then VoterV3 `Vote` fires, then `Staked` events fire in each bribe for the new pool.

- **Bribe per-pool discovery:** Each pool registered in VoterV3 has two associated bribe contracts (internal = swap fees, external = external incentives). Both emit `Staked(uint256 indexed tokenId, uint256 amount)` = `0x925435fa…` when a veNFT votes for the pool.

- **Minter epoch:** `active_period()` returns the start of the current epoch (Unix timestamp). As of verification date (2026-06-11), `active_period = 0x6a29fa80` (~June 11, 2026). Mint events have not fired since the current epoch was set; they will fire when `update_period()` is called after epoch expiry.
