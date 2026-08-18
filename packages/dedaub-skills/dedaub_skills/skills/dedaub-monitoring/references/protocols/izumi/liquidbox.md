# iZUMi LiquidBox — Compressed Reference (programmable liquidity mining)

**Status:** topic0/selectors computed locally with keccak from `izumiFinance/izumi-uniV3Mining` + `iZiSwap-farm` source; instance addresses from in-repo `scripts/deployed.js`, **on-chain spot-verified** (publicnode, 2026-06).
**Scope:** **LiquidBox** = iZUMi's liquidity-mining engine. Stake a **concentrated-liquidity LP NFT** into a per-pool mining contract to earn reward tokens. Two engines:
- **`izumi-uniV3Mining`** — mines **Uniswap V3** position NFTs (`0xC364…` NonfungiblePositionManager). iZUMi's *original* 2021 product ("Programmable LaaS"). Lives on **Ethereum, Polygon, Arbitrum** (+ historical BSC).
- **`iZiSwap-farm`** — mines **iZiSwap** LP NFTs (the `LiquidityManager` from [`iziswap.md`](iziswap.md)). On the iZiSwap chains (BNB, Arbitrum, Mantle, Linea, Scroll, Manta, …).

Three reward strategies, each in a plain (block-based), a **Timestamp** (second-based), and a **veiZi-boosted** variant: **One-Side**, **Fixed-Range**, **Dynamic-Range**. Index + footprint: [`README.md`](README.md). veiZi token: [`tokens.md`](tokens.md).

---

## Topics (chain-agnostic) — `topic0 -> Event(types)`
*Identical event set across both engines and all strategies (the differences are in math, not events). Block-based vs Timestamp variants differ only in the `Modify*` admin events.*

### Mining core (emitted by every mining instance)
```
0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15 -> Deposit(address,uint256,uint256)            [user(indexed),tokenId,nIZI|vLiquidity]  ⚠ COLLIDES (see #1)
0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364 -> Withdraw(address,uint256)                   [user(indexed),tokenId]                  ⚠ COLLIDES (see #1)
0xbc96baf3023d0b9ea3a899e000f15d5f0f7a8b064774c1eed6b4cc63fcbd1b19 -> CollectReward(address,uint256,address,uint256)  [user(indexed),tokenId,token,amount — standard variant]
0x56cc9cf62f5a3a4367575119e524522956236e34a9a06eab7fcf9880b76b81cc -> CollectReward(address,address,uint256)          [user(indexed),token,amount — veiZi-boost variant, NO tokenId]
0xda608212a78120f0e323cf82e77003c28512aa6eae3747c062c459901d793015 -> ModifyProvider(address,address)            [rewardToken(indexed),provider]
```

### Block-based instances (`MiningBase`, `iZiSwap-farm/base/Base`, `BaseWithWrap`)
```
0x6861e667f4625c666d8000dd2fe6b7dde9a3d46381327f9e1330df56969f15be -> ModifyEndBlock(uint256)
0xd9a745381d3899e0a1380f3c7f56ea1bf0fb8331482527ff4984296da9580fab -> ModifyRewardPerBlock(address,uint256)      [rewardToken(indexed),rewardPerBlock]
```

### Timestamp-based instances (`*Timestamp`, `BaseTimestamp`, `BaseWithWrapTimestamp`)
```
0x3763a58d2bb8a5efc62a8597bf938868dcc71eee5f9745c71a12c09659993bb9 -> ModifyEndTime(uint256)
0x7f158314293348b0862e1d84db7dbfdeec0fe804660b5c2406f1194fcde32dba -> ModifyRewardPerSecond(address,uint256)
```

### Archived V1 (`archive/miningFixRange`, deprecated) — extra event
```
WithdrawNoReward(address,uint256)   [user(indexed),tokenId — emergency exit forfeiting rewards; present only on legacy V1 instances]
```

---

## Function signatures (chain-agnostic) — *from source; entrypoints vary slightly by strategy/engine*
```
0xe2bbb158 -> deposit(uint256,uint256) -> uint256                 [tokenId, numIZI(boost) → vLiquidity]   (non-boost variants take deposit(uint256))
0xa32413a6 -> depositWithuniToken(address,uint256,uint256,uint256,uint256)   [uni-mint-and-stake helper]
0x2e1a7d4d -> withdraw(uint256)                                   (some variants: withdraw(uint256 tokenId, bool noReward))
0xbd3507da -> collectReward(uint256)                              [tokenId — claim accrued reward for one staked NFT]
0x457dbdfa -> collectAllTokens(uint256)
```
*The Deposit/Withdraw/CollectReward **events** above are the reliable monitoring surface; selectors differ between One-Side / Fixed-Range / Dynamic-Range and boost variants — confirm against the specific instance's bytecode before keying on a selector.*

---

## Addresses (network-specific)

> LiquidBox is **per-pool**: each incentivized pool gets its **own** mining contract (named `<STRATEGY>_<tokenA>_<tokenB>_<fee>` in `deployed.js`, e.g. `ONESIDE_WETH9_IZI_3000`). There is **no singleton registry / factory event** — enumerate instances by the deployer EOA or by their `Deposit`/`CollectReward` logs. Most listed programs are **historical (ended)** but the contracts remain on-chain. Examples below are `eth_getCode`-verified live this run.

### Ethereum (1) — `izumi-uniV3Mining` (mines **Uniswap V3** NFTs: factory `0x1F98431c…`, nftManager `0xC36442b4…`)
```
0xbE138aD5D41FDc392AE0B61b09421987C1966CC3 -> ONESIDE_WETH9_IZI_3000        (One-Side mining, 20,336 B ✓)
0x8981c60ff02CDBbF2A6AC1a9F150814F9cF68f62 -> FIXRANGE_USDC_USDT_100        (Fixed-Range mining, 13,534 B ✓)
0x57AFF370686043B5d21fDd76aE4b513468B9fb3C -> ONESIDE_WETH9_YIN_3000
0x99CC0A41F8006385f42aed747e2d3642a226d06E -> ONESIDE_V2_USDC_DEVT_3000
0x3599A414B4365b118766479600c0fD135177C2D5 -> CHARGE_RECEIVER (mining fee receiver, ETH/Polygon/Arbitrum)
```

### Polygon PoS (137) — `izumi-uniV3Mining`
```
0x99CC0A41F8006385f42aed747e2d3642a226d06E -> ONESIDE_ETHT_IZIT_3000
0x8984901cEaff81b45396a13D8DcD4F153e62A429 -> FIXRANGE_USDC6_USDT6_500
0x01Cc44fc1246D17681B325926865cDB6242277A5 -> FIXRANGE_V2_USDC_USDT_500
0x28d7BFf13c5A1227aEe2E892F8d22d8A1a84A0D4 -> ONESIDE_V2_USDC_ACY_3000
0xafd5f7a790041761f33bfbf3df1b54df272f2576 -> DYNRANGE_V2_ETH_DDAO_3000
```

### Arbitrum One (42161) — `izumi-uniV3Mining` + `iZiSwap-farm`
```
0x5B0bb2e0A6B0cab625d885DfBe95fC67E50E5F3c -> iZi_PROVIDER (reward provider)
# iZiSwap-farm instances target the iZiSwap LiquidityManager 0x611575eE1fbd4F7915D0eABCC518eD396fF78F0c
```

### BNB Chain (56) — `iZiSwap-farm` (mines iZiSwap LP NFTs via LiquidityManager `0x93C22Fbeff…`)
*Per-pool farm instances for iZi / iUSD / partner tokens; deployed ad hoc, not in a fixed registry. Reward tokens incl. iZi `0x60D01EC2…`, iUSD `0x0a3bb08b…`, BUSD/USDT and many partner tokens. Enumerate via `Deposit`/`CollectReward` logs.*

> **iZiSwap-farm has no Ethereum deployment** (ETH LiquidBox = the Uniswap-V3 mining engine above). iZiSwap-farm `liquidityManager` targets per chain: BNB `0x93C22Fbeff4448F2fb6e432579b0638838Ff9581`, Arbitrum/Mantle `0x611575eE1fbd4F7915D0eABCC518eD396fF78F0c`, Linea `0x1CB60033F61e4fc171c963f0d2d3F63Ece24319c`, Scroll `0x1502d025BfA624469892289D45C0352997251728`, Manta/Cyber/Klaytn/Flow/IoTeX/Over `0x19b683A2F45012318d9B2aE1280d68d3eC54D663`.

---

## Proxies
- **No upgradeable proxies.** Mining instances are **plain immutable contracts**, each deployed per pool. No EIP-1967 slot, no `Upgraded`. "Upgrades" happen by deploying a **new instance** (note the `V1`→`V2`→`V3` suffixes in names) and migrating incentives.
- The `Modify*` admin events (`ModifyEndBlock`/`ModifyEndTime`/`ModifyRewardPerBlock`/`ModifyRewardPerSecond`/`ModifyProvider`) are the governance surface — they re-parameterize an existing instance (extend program, change emission rate / reward provider).

## Detection invariants & gotchas
1. **`Deposit(address,uint256,uint256)` `0x90890809…` and `Withdraw(address,uint256)` `0x884edad9…` are massive collisions.** Same topic0 as **MasterChef / Trader-Joe sJOE / Sushi / PancakeSwap** `Deposit`, and Velodrome gauge / sJOE `Withdraw`. **Disambiguate strictly by the mining-instance address** (or confirm `CollectReward` `0xbc96baf3…`/`0x56cc9cf6…`, which are LiquidBox-specific).
2. **Two `CollectReward` shapes:** standard `(address,uint256,address,uint256)` `0xbc96baf3…` (carries `tokenId`) vs veiZi-boost `(address,address,uint256)` `0x56cc9cf6…` (no `tokenId`). The veiZi variant means the instance reads boost from veiZi ([`tokens.md`](tokens.md)).
3. **Block-based vs Timestamp-based** instances coexist — `ModifyEndBlock`/`ModifyRewardPerBlock` (`0x6861e667…`/`0xd9a74538…`) vs `ModifyEndTime`/`ModifyRewardPerSecond` (`0x3763a58d…`/`0x7f158314…`). Pick the matching pair per instance.
4. **Two NFT substrates:** `izumi-uniV3Mining` stakes **Uniswap V3** NFTs; `iZiSwap-farm` stakes **iZiSwap** NFTs. The staked-NFT `Transfer` will originate from `0xC36442b4…` (Uni V3) or the iZiSwap `LiquidityManager` respectively.
5. **No factory / no `PoolCreated`-style event** — instances are independent deploys. Discover by deployer or by event scan; don't expect a registry.

## Quick-copy bytea-ready constants (Postgres `'\x…'`)
```
mining_deposit       = '\x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15'   # COLLIDES w/ MasterChef
mining_withdraw      = '\x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364'   # COLLIDES w/ gauge/sJOE
collect_reward_std   = '\xbc96baf3023d0b9ea3a899e000f15d5f0f7a8b064774c1eed6b4cc63fcbd1b19'
collect_reward_veizi = '\x56cc9cf62f5a3a4367575119e524522956236e34a9a06eab7fcf9880b76b81cc'
modify_end_block     = '\x6861e667f4625c666d8000dd2fe6b7dde9a3d46381327f9e1330df56969f15be'
modify_end_time      = '\x3763a58d2bb8a5efc62a8597bf938868dcc71eee5f9745c71a12c09659993bb9'
modify_provider      = '\xda608212a78120f0e323cf82e77003c28512aa6eae3747c062c459901d793015'
```

## Verification & sources
- topic0/selectors: local keccak from `izumi-uniV3Mining` (`base/MiningBase.sol`, `base/MiningBaseVeiZi.sol`) and `iZiSwap-farm` (`base/Base.sol`, `base/BaseTimestamp.sol`). `Deposit`/`Withdraw`/`Modify*` topic0s are byte-identical across both engines.
- Addresses: in-repo `scripts/deployed.js`; ETH instances `ONESIDE_WETH9_IZI_3000` (20,336 B) and `FIXRANGE_USDC_USDT_100` (13,534 B) confirmed live via `eth_getCode`.
- Source: [`izumiFinance/izumi-uniV3Mining`](https://github.com/izumiFinance/izumi-uniV3Mining), [`iZiSwap-farm`](https://github.com/izumiFinance/iZiSwap-farm). DEX = [`iziswap.md`](iziswap.md); tokens/veiZi = [`tokens.md`](tokens.md).
