# Blackhole DEX — Classic AMM + Governance (Solidly/ve(3,3)) — Topics, Selectors, Addresses (Avalanche C-Chain)

**Status:** Verified — all addresses confirmed via `eth_getCode` on Avalanche C-Chain (43114); absent (`0x`) on all other target chains (Ethereum 1, Base 8453, BNB 56, Arbitrum 42161, Optimism 10, Polygon 137). Deployment block ~67,000,000 (early 2024). topic0s cross-checked against live `eth_getLogs` on Avalanche.
**Sources:** [Blackhole docs](https://docs.blackhole.xyz) · live `eth_getLogs` and `eth_getTransactionReceipt` cross-checks on Avalanche C-Chain · bytecode analysis · keccak256 computed locally.
**Last verified:** 2026-06-09

---

## 0. Contract families

| Family | Contracts | Role |
|--------|-----------|------|
| **Classic AMM** | PairFactory, Pair (per pair, stable+volatile), RouterV2 | Pool creation, stable/volatile AMM swaps, LP management |
| **Governance** | BLACK (ERC-20 governance token), VotingEscrow (veNFT = veBLACK) | Token + ve-locking |
| **Voter** | VoterV3 (proxy), GaugeManager (proxy) | Epoch voting, gauge weight allocation |
| **Gauges/Bribes** | GaugeFactory, GaugeV2 (per gauge), BribeFactory, Bribe (per gauge) | LP reward farming, vote incentives |
| **Minter** | MinterUpgradeable (proxy) | Weekly BLACK emission via `update_period()` |
| **Distributions** | RewardDistributor | veNFT holders claim protocol yield |
| **Misc** | AutoVotingEscrowManager, BlackClaim, VeArtProxy, GenesisPoolManager | Auto-voting, token claims, NFT art |

**Architecture note:** Blackhole Classic is a ThenaFi fork (BNB Chain) which is itself a Solidly/ve(3,3) fork. Closely resembles Velodrome V1, Pharaoh Legacy AMM, and Camelot V2. Classic pairs have two types (stable=true / stable=false) distinguished by the `stable()` flag on each Pair and by `PairFactory.isPair()`. Gauge rewards flow: `MinterUpgradeable.update_period()` mints weekly BLACK → `GaugeManager.distribute()` → `GaugeV2.notifyRewardAmount()` → staked LP holders claim. veNFT holders earn protocol fees via `RewardDistributor.claim(tokenId)`.

**Proxy pattern:** VoterV3, GaugeManager, MinterUpgradeable are OpenZeppelin `TransparentUpgradeableProxy` with a shared `ProxyAdmin` at `0xd763061cc3015642ca104496107bc69944c74bed` (owned by `0xe3Df22b04F1F788fF025ADc2466638f5AaE588e0`). The EIP-1967 `_IMPLEMENTATION_SLOT` (`0x360894…382bbc`) is **populated** — VoterV3 impl = `0x6bD81E7eaFA4B21d5AD069B452Ab4b8bb40c4525`, GaugeManager impl = `0x66c6650a106e82FC40824077fA501D6f28974091`, MinterUpgradeable impl = `0x86EbA1b766667B99dd4f9a40d01960e36CF753e3` (all verified via `eth_getStorageAt`). VotingEscrow is a non-upgradeable contract (no proxy slots).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 PairFactory
Source: deployment on Avalanche, bytecode + live `eth_getLogs` verification (block 67001851 first `PairCreated`).

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xc4805696c66d7cf352fc1d6bb633ad5ee82f6cb577c453024b6e0eb8306c6fc9` | `PairCreated(address indexed token0, address indexed token1, bool stable, address pair, uint256 count)` | **★ subscribe to discover all Classic pairs.** `stable=true` → stable pair; `false` → volatile. **Param order differs from Uniswap V2**: `bool stable` is 3rd (non-indexed) before the pair address. |

> **PairCreated signature note:** The `bool stable` precedes the pair address in the non-indexed data section. Full signature: `PairCreated(address,address,bool,address,uint256)` → topic0 `0xc4805696…`. This differs from Uniswap V2's `PairCreated(address,address,address,uint256)` (`0x0d3648bd…`). Confirmed on-chain from first pair deployment.

### 1.2 Pair (per-pair AMM)
Source: live `eth_getLogs` on pair `0x495B296c3fc52283Fd9565B421386D36F628d55E` (pair 0, volatile BLACKHOLE/USDC), cross-checked with keccak of Solidly/Uniswap V2 event ABIs.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822` | `Swap(address indexed sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, address indexed to)` | **★ workhorse swap event.** Identical layout to Uniswap V2. Confirmed live. |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address indexed sender, uint256 amount0, uint256 amount1)` | LP deposit. |
| `0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496` | `Burn(address indexed sender, uint256 amount0, uint256 amount1, address indexed to)` | LP withdrawal. |
| `0xcf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a` | `Sync(uint256 reserve0, uint256 reserve1)` | Reserve update (emitted after every swap/mint/burn). |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 LP token transfer. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ERC-20 LP token approval. |
| `0x112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602` | `Fees(address indexed sender, uint256 amount0, uint256 amount1)` | Solidly fee-split event: protocol fees separated from swap fees. |

> Each Pair address is discoverable from `PairFactory.allPairs(index)` or from `PairCreated` events. Stable and volatile pairs share the same event ABIs; distinguish by calling `pair.stable()` → `bool`.

### 1.3 VoterV3 (proxy)
Source: live `eth_getLogs` on VoterV3 proxy, blocks 67,000,000–87,565,432. Only two distinct topic0s observed.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xea66f58e474bc09f580000e81f31b334d171db387d0c6098ba47bd897741679b` | `Voted(address indexed voter, uint256 tokenId, uint256 weight)` | **★ fired when a veNFT votes.** topic1 = `msg.sender` of the vote/poke call (EOA, contract, or AutoVotingEscrowManager — NOT always the VotingEscrow address). |
| `0xa9f3ca5f8a9e1580edb2741e0ba560084ec72e0067ba3423f9e9327a176882db` | `Abstained(uint256 tokenId, uint256 weight)` | **★ fired when a vote is reset or withdrawn.** Often emitted immediately before a new `Voted`. |

> **Observation:** `GaugeCreated`, `WhitelistToken`, `Deposit`, `Withdraw`, `NotifyReward`, `DistributeReward` events appear to be emitted by **GaugeManager** (not VoterV3) in this fork. See §1.4.

### 1.4 GaugeManager (proxy)
Source: live `eth_getLogs` on GaugeManager, blocks 67,000,000–68,050,000.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xa4d97e9e7c65249b4cd01acb82add613adea98af32daf092366982f0a0d4e453` | `GaugeCreated(address indexed creator, address indexed externalBribe, address indexed pair, address gauge, address internalBribe)` | **★ subscribe to discover all gauges.** 3 indexed + 2 non-indexed addresses. Confirmed from block 67001936. |
| `0xf70d5c697de7ea828df48e5c4573cb2194c659f1901f70110c52b066dcf50826` | `NotifyReward(address indexed sender, address indexed reward, uint256 amount)` | Reward token notified to a gauge. |
| `0x4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17` | `DistributeReward(address indexed sender, address indexed gauge, uint256 amount)` | Weekly BLACK distributed to a gauge by Minter/voter. |

### 1.5 GaugeV2 (per gauge)
Source: live `eth_getLogs` on GaugeV2 `0x6dE3Cf0586b964761ad6b6e9C2fEAaBe5802A528` (gauge for pair 0), blocks 67,000,000+.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | `Deposit(address indexed from, uint256 amount)` | **★ LP staked into gauge.** |
| `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | `Withdraw(address indexed from, uint256 amount)` | **★ LP unstaked from gauge.** |
| `0xbc567d6cbad26368064baa0ab5a757be46aae4d70f707f9203d9d9b6c8ccbfa3` | `ClaimFees(address indexed from, uint256 claimed0, uint256 claimed1)` | Swap fees claimed by gauge. |
| `0x9aa05b3d70a9e3e2f004f039648839560576334fb45c81f91b6db03ad9e2efc9` | `ClaimRewards(address indexed from, address indexed reward, uint256 amount)` | Gauge reward claimed by staker. |
| `0xc9695243a805adb74c91f28311176c65b417e842d5699893cef56d18bfa48cba` | `Harvest(address indexed user, uint256 amount)` | Alias/variant of ClaimRewards in this fork. |
| `0xde88a922e0d3b88b24e9623efeb464919c6bf9f66857a65e2bfcf2ce87a9433d` | `RewardAdded(uint256 reward)` | Reward amount added (no indexed; reward rate update). |

### 1.6 Bribe (per gauge — internal and external)
Source: live `eth_getLogs` on bribe `0xAf7c842A03aF407482A9CE59885438d5540AC814` and `0x2Aa4cc824CB12a2E4fb9474eB42D30b14c1f2FBd`, blocks 67,000,000+. Bribe contracts use `tokenId` as the unit of bribe accounting (veNFT-based).

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x925435fa7e37e5d9555bb18ce0d62bb9627d0846942e58e5291e9a2dded462ed` | `Staked(uint256 indexed tokenId, uint256 amount)` | **★ veNFT weight staked into bribe (on vote).** |
| `0x0c875c8d391179c5cf7ad8303d268efd50b8beb78b671f85cd54bfb91eb8ef40` | `Withdrawn(uint256 indexed tokenId, uint256 amount)` | **★ veNFT weight withdrawn from bribe (on reset).** |
| `0x6a6f77044107a33658235d41bedbbaf2fe9ccdceb313143c947a5e76e1ec8474` | `RewardAdded(address indexed rewardToken, uint256 reward, uint256 startTimestamp)` | New bribe incentive added. |

### 1.7 MinterUpgradeable (proxy)
Source: live `eth_getLogs` on Minter, blocks 67,001,000+. Confirmed at block 67,031,512 tx `0x4e63c855…`.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xb4c03061fb5b7fed76389d5af8f2e0ddb09f8c70d1333abbb62582835e10accb` | `Mint(address indexed sender, uint256 weekly, uint256 circulating_emission, uint256 circulating_supply)` | **★ epoch emission.** Fires once per week when `update_period()` is called. `sender` = GaugeManager. |

### 1.8 VotingEscrow (veBLACK, ERC-721 veNFT)
Source: live `eth_getLogs` on VotingEscrow, blocks 67,000,000–87,565,432. Bytecode analysis confirmed. VotingEscrow is **non-upgradeable** (no proxy).

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xff04ccafc360e16b67d682d17bd9503c4c6b9a131f6be6325762dc9ffc7de624` | `Deposit(address indexed provider, uint256 tokenId, uint256 value, uint256 indexed locktime, uint8 deposit_type, uint256 ts)` | **★ fired for ALL lock operations** (create, add, withdraw). `deposit_type` (`data[2]`): 0=WITHDRAW, 1=CREATE_LOCK, 2=ADD_TO_LOCK. topic2 = `locktime` (future expiry Unix timestamp): **non-zero for CREATE_LOCK and ADD operations**, zero for WITHDRAW. Confirmed live (4/32 sampled logs had non-zero locktime). |
| `0x02f25270a4d87bea75db541cdfe559334a275b4a233520ed6c0a2429667cca94` | `Withdraw(address indexed provider, uint256 tokenId, uint256 value, uint256 ts)` | Unlock event (lock expired). Has 1 indexed param. |
| `0x5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c` | `Supply(uint256 prevSupply, uint256 supply)` | Total locked token supply change. No indexed params. |
| `0x8303de8187a6102fdc3fe20c756dddd68df0ae027b77e2391c19a855e0821f33` | `Split(uint256 indexed from, uint256 indexed newTokenId1, uint256 indexed newTokenId2, address owner, uint256 oldAmount, uint256 newAmount1, uint256 newAmount2, uint256 lockEnd)` | veNFT split. 3 indexed tokenIds + 5 non-indexed data. Confirmed block 67,005,892. |
| `0x986e3c958e3bdf1f58c2150357fc94624dd4e77b08f9802d8e2e885fa0d6a198` | `Merge(address indexed provider, uint256 indexed fromTokenId, uint256 indexed toTokenId, uint256 fromAmount, uint256 toAmount, uint256 totalAmount, uint256 newAmount, uint256 lockEnd)` | veNFT merge. 3 indexed + 5 non-indexed. Confirmed block 67,001,272. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 indexed tokenId)` | ERC-721 veNFT transfer (3 indexed params, empty data). |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed approved, uint256 indexed tokenId)` | ERC-721 approval. |
| `0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31` | `ApprovalForAll(address indexed owner, address indexed operator, bool approved)` | ERC-721 operator approval. |
| `0xf8e1a15aba9398e019f0b49df1a4fde98ee17ae345cb5f6b5e2c27f5033e8ce7` | `MetadataUpdate(uint256 tokenId)` | EIP-4906 — token URI changed (fired after lock ops). Confirmed via bytecode: stored alongside `Transfer` in the contract's event dispatch table. |

### 1.9 RewardDistributor
Source: live `eth_getLogs` on RewardDistributor, blocks 87,500,000–87,550,000.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xcae2990aa9af8eb1c64713b7eddb3a80bf18e49a94a13fe0d0002b5d61d58f00` | `Claimed(uint256 tokenId, uint256 amount, uint256 claimEpoch, uint256 maxEpoch)` | **★ veNFT holder claims protocol yield.** Confirmed block 87,516,497. |
| `0xce749457b74e10f393f2c6b1ce4261b78791376db5a3f501477a809f03f500d6` | `CheckpointToken(uint256 time, uint256 tokens)` | Token checkpoint (weekly). |

### 1.10 BLACK token (ERC-20)
Standard ERC-20 events only:

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |

---

## 2. Function signatures (chain-agnostic)

### 2.1 RouterV2
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf41766d8` | `swapExactTokensForTokens(uint256 amountIn, uint256 amountOutMin, (address from, address to, bool stable)[] routes, address to, uint256 deadline)` | Token→token swap. |
| `0x505a6daa` | `swapExactAVAXForTokens(uint256 amountOutMin, (address,address,bool)[] routes, address to, uint256 deadline)` | Native AVAX → token. |
| `0x84507b96` | `swapExactTokensForAVAX(uint256 amountIn, uint256 amountOutMin, (address,address,bool)[] routes, address to, uint256 deadline)` | Token → native AVAX. |
| `0x5a47ddc3` | `addLiquidity(address tokenA, address tokenB, bool stable, uint256 amountADesired, uint256 amountBDesired, uint256 amountAMin, uint256 amountBMin, address to, uint256 deadline)` | Add LP. |
| `0xdae25750` | `addLiquidityAVAX(address token, bool stable, uint256 amountTokenDesired, uint256 amountTokenMin, uint256 amountAVAXMin, address to, uint256 deadline)` | Add LP with native AVAX. |
| `0x0dede6c4` | `removeLiquidity(address tokenA, address tokenB, bool stable, uint256 liquidity, uint256 amountAMin, uint256 amountBMin, address to, uint256 deadline)` | Remove LP. |
| `0x9caa2e90` | `removeLiquidityAVAX(address token, bool stable, uint256 liquidity, uint256 amountTokenMin, uint256 amountAVAXMin, address to, uint256 deadline)` | Remove LP + unwrap AVAX. |

### 2.2 PairFactory
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x82dfdce4` | `createPair(address tokenA, address tokenB, bool stable)` | Creates a new stable or volatile pair. Emits `PairCreated`. |

### 2.3 VoterV3 (proxy → impl `0x6bD81E7eaFA4B21d5AD069B452Ab4b8bb40c4525`)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7ac09bf7` | `vote(uint256 tokenId, address[] poolVote, uint256[] weights)` | Cast votes for gauges with a veNFT. |
| `0x310bd74b` | `reset(uint256 tokenId)` | Reset all votes for a veNFT. Emits `Abstained`. |
| `0x63453ae1` | `distribute(address gauge)` | Trigger reward distribution to a specific gauge. |
| `0xdcd9e47a` | `createGauge(address pair, uint256 gaugeType)` | Create gauge for a pair. |
| `0x7715ee75` | `claimBribes(address[] bribes, address[][] tokens, uint256 tokenId)` | Claim bribe rewards. |
| `0x666256aa` | `claimFees(address[] fees, address[][] tokens, uint256 tokenId)` | Claim internal bribe (swap fee) rewards. |
| `0x20b1cb6f` | `claimRewards(address[] gauges, address[][] tokens)` | Claim gauge rewards for LP stakers. |

### 2.4 VotingEscrow
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x65fc3873` | `create_lock(uint256 value, uint256 lockDuration)` | Create a new veNFT lock. |
| `0xa183af52` | `increase_amount(uint256 tokenId, uint256 value)` | Add to an existing lock. |
| `0xa4d855df` | `increase_unlock_time(uint256 tokenId, uint256 lockDuration)` | Extend lock duration. |
| `0x2e1a7d4d` | `withdraw(uint256 tokenId)` | Withdraw expired lock. |
| `0xd1c2babb` | `merge(uint256 from, uint256 to)` | Merge two veNFTs. |

### 2.5 GaugeV2 (per gauge)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe2bbb158` | `deposit(uint256 amount, uint256 tokenId)` | Stake LP tokens into gauge. |
| `0x2e1a7d4d` | `withdraw(uint256 amount)` | Unstake LP tokens. |
| `0x31279d3d` | `getReward(address account, address[] tokens)` | Claim gauge rewards. |

### 2.6 MinterUpgradeable (proxy → impl `0x86EbA1b766667B99dd4f9a40d01960e36CF753e3`)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xed29fc11` | `update_period()` | Advance epoch, mint weekly BLACK emission. Callable by anyone once per week. |

### 2.7 RewardDistributor
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x379607f5` | `claim(uint256 tokenId)` | Claim accumulated yield for a veNFT. Confirmed from tx `0x364e029f…`. |

---

## 3. Addresses

### 3.1 Avalanche C-Chain (chainId 43114) — **only deployed chain**

| Contract | Address | Notes |
|----------|---------|-------|
| **BLACK token** | `0xcd94a87696FAC69Edae3a70fE5725307Ae1c43f6` | `name()="BLACKHOLE"`, `symbol()="BLACK"`. ERC-20. Non-upgradeable. |
| **RouterV2** | `0xe946A9f39312E2346BA79DAb865B0e9A74f2F981` | Non-upgradeable. |
| **PairFactory** | `0xfE926062Fb99CA5653080d6C14fE945Ad68c265C` | Non-upgradeable. `allPairsLength()=87`. `stableFee()=5` bp, `volatileFee()=70` bp. `0x36610013…` dispatch prefix. |
| **VotingEscrow** (veBLACK) | `0xEac562811cc6abDbB2c9EE88719eCA4eE79Ad763` | `name()="veBlack"`, `symbol()="veBLACK"`. ERC-721 veNFT. **Non-upgradeable** (no proxy admin). |
| **VoterV3** | `0xE30D0C8532721551a51a9FeC7FB233759964d9e3` | **Proxy** (TransparentUpgradeableProxy). Impl: `0x6bD81E7eaFA4B21d5AD069B452Ab4b8bb40c4525`. Admin: `0xd763061cc3015642ca104496107bc69944c74bed` (ProxyAdmin). |
| **GaugeManager** | `0x59aa177312Ff6Bdf39C8Af6F46dAe217bf76CBf6` | **Proxy** (TransparentUpgradeableProxy). Impl: `0x66c6650a106e82FC40824077fA501D6f28974091`. Admin: same ProxyAdmin. |
| **GaugeFactory** | `0x9E95eF7D8b87708641923C48C4eB298ED7CA6552` | Non-upgradeable. `0x36610013…` dispatch. |
| **MinterUpgradeable** | `0xAcc34Ad51457930989fB5050C2Dce6339F06479B` | **Proxy** (TransparentUpgradeableProxy). Impl: `0x86EbA1b766667B99dd4f9a40d01960e36CF753e3`. Admin: same ProxyAdmin. `active_period()=1780531200`. |
| **BribeFactory** | `0xfE842861b9F79Bb77CCb6043731D433D63B365dF` | Non-upgradeable. `0x36610013…` dispatch. |
| **RewardDistributor** | `0x7c7BD86BaF240dB3DbCc3f7a22B35c5bAa83bA28` | Non-upgradeable. Distributes protocol yield to veNFT holders. |
| **AutoVotingEscrowManager** | `0x3755DF8a937e9505aF7B14D8b13E83f133Ed11c3` | Non-upgradeable. `0x36610013…` dispatch. |
| **BlackClaim** | `0x91B8C8c51A11a7033C34257C3768035EfF4F7736` | Non-upgradeable. Token distribution contract. |
| **VeArtProxy** | `0xcA756Ef397b8F039d04b4ff967F43417B723aFdE` | Non-upgradeable. `0x36610013…` dispatch. Returns veNFT SVG art. |
| **GenesisPoolManager** | `0x0EB1e103116b8Ec5f13a72F6943440340c4840dd` | Non-upgradeable. |
| **ProxyAdmin** | `0xd763061cc3015642ca104496107bc69944c74bed` | Admin for VoterV3, GaugeManager, MinterUpgradeable. `owner()=0xe3Df22b04F1F788fF025ADc2466638f5AaE588e0`. |

> **Pair and gauge discovery:** Use `PairFactory.allPairs(index)` (index 0…86) to enumerate all 87 Classic pairs. Use `GaugeManager.gauges(pairAddress)` to get the GaugeV2 for any pair. `GaugeManager.internal_bribes(pairAddress)` and `GaugeManager.external_bribes(pairAddress)` return the bribe contracts. Subscribe to `PairCreated` (topic0 `0xc4805696…`) on PairFactory and `GaugeCreated` (topic0 `0xa4d97e9e…`) on GaugeManager to discover new deployments.

### 3.2 All other target chains — absent

| Chain | chainId | All Blackhole Classic contracts |
|-------|---------|--------------------------------|
| Ethereum | 1 | `0x` — not deployed |
| Base | 8453 | `0x` — not deployed |
| BNB Smart Chain | 56 | `0x` — not deployed |
| Arbitrum One | 42161 | `0x` — not deployed |
| Optimism | 10 | `0x` — not deployed |
| Polygon PoS | 137 | `0x` — not deployed |

Verified: `eth_getCode` on BLACK token (`0xcd94a87696…`) and PairFactory (`0xfE926062…`) returns `0x` on all six chains above.

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
-- Pair: sync (reserve update)
\x cf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a
-- Pair: fees (protocol fee split)
\x 112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602

-- GaugeManager: new gauge created
\x a4d97e9e7c65249b4cd01acb82add613adea98af32daf092366982f0a0d4e453
-- GaugeManager: notify reward
\x f70d5c697de7ea828df48e5c4573cb2194c659f1901f70110c52b066dcf50826
-- GaugeManager: distribute reward
\x 4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17

-- GaugeV2: LP staked
\x e1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c
-- GaugeV2: LP unstaked
\x 884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364
-- GaugeV2: reward claimed
\x 9aa05b3d70a9e3e2f004f039648839560576334fb45c81f91b6db03ad9e2efc9

-- Bribe: veNFT weight staked (on vote)
\x 925435fa7e37e5d9555bb18ce0d62bb9627d0846942e58e5291e9a2dded462ed
-- Bribe: veNFT weight withdrawn (on reset)
\x 0c875c8d391179c5cf7ad8303d268efd50b8beb78b671f85cd54bfb91eb8ef40

-- MinterUpgradeable: epoch mint (weekly BLACK emission)
\x b4c03061fb5b7fed76389d5af8f2e0ddb09f8c70d1333abbb62582835e10accb

-- VoterV3: voted
\x ea66f58e474bc09f580000e81f31b334d171db387d0c6098ba47bd897741679b
-- VoterV3: abstained / vote reset
\x a9f3ca5f8a9e1580edb2741e0ba560084ec72e0067ba3423f9e9327a176882db

-- VotingEscrow: Deposit (create/add/withdraw — all share this topic0; topic2=locktime, non-zero for CREATE_LOCK/ADD)
\x ff04ccafc360e16b67d682d17bd9503c4c6b9a131f6be6325762dc9ffc7de624
-- VotingEscrow: withdraw expired lock
\x 02f25270a4d87bea75db541cdfe559334a275b4a233520ed6c0a2429667cca94
-- VotingEscrow: total supply change
\x 5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c
-- VotingEscrow: NFT merge
\x 986e3c958e3bdf1f58c2150357fc94624dd4e77b08f9802d8e2e885fa0d6a198
-- VotingEscrow: NFT split
\x 8303de8187a6102fdc3fe20c756dddd68df0ae027b77e2391c19a855e0821f33
-- VotingEscrow: metadata update (EIP-4906)
\x f8e1a15aba9398e019f0b49df1a4fde98ee17ae345cb5f6b5e2c27f5033e8ce7

-- RewardDistributor: yield claimed by veNFT holder
\x cae2990aa9af8eb1c64713b7eddb3a80bf18e49a94a13fe0d0002b5d61d58f00
-- RewardDistributor: token checkpoint
\x ce749457b74e10f393f2c6b1ce4261b78791376db5a3f501477a809f03f500d6

-- ERC-20 / ERC-721 standard (BLACK, LP tokens, veNFT)
\x ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  -- Transfer
\x 8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  -- Approval
\x 17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31  -- ApprovalForAll
```

---

## 5. Unresolved / notes

- **VotingEscrow `Deposit` event — topic2 is `locktime`:** The event is `Deposit(address indexed provider, uint256 tokenId, uint256 value, uint256 indexed locktime, uint8 deposit_type, uint256 ts)`. topic2 (`locktime`) = future expiry Unix timestamp — **non-zero for CREATE_LOCK and ADD_TO_LOCK** (confirmed live: 4/32 sampled events had non-zero locktime), **zero for WITHDRAW**. `deposit_type` (`data[2]`): 0=WITHDRAW, 1=CREATE_LOCK, 2=ADD_TO_LOCK. Monitor on `topic0=0xff04ccaf` address=VotingEscrow and filter on `data[2]` for specific operation type.

- **VoterV3 Voted event:** The source declares `Voted(address indexed voter, ...)` where `voter` = `msg.sender` of the vote/poke call (can be an EOA, contract, or the AutoVotingEscrowManager). To filter votes subscribe with address=VoterV3 and topic0=`0xea66f58e…`; do not assume topic1 is the VotingEscrow address.

- **PairCreated parameter order:** The `bool stable` parameter comes BEFORE the pair address in this fork (unlike Uniswap V2 where pair address comes before count). The signature is `PairCreated(address,address,bool,address,uint256)` not `PairCreated(address,address,address,bool,uint256)`.
