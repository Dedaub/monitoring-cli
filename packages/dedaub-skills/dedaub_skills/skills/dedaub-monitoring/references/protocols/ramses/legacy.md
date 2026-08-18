# Ramses Exchange — Legacy AMM Topics, Selectors, Addresses (Arbitrum One)

**Status:** topic0/selectors computed with `cast keccak`; cross-checked against live `eth_getLogs` on Arbitrum One (publicnode, 2026-06). Addresses on-chain verified via `eth_getCode` + view reads (`PairFactory.allPairsLength()` → 311 ✓, `RAM.symbol()` → "RAM" ✓, `VotingEscrow.symbol()` → "veRAM" ✓). EIP-1967 impl slots read for Voter and VotingEscrow. All six other chains confirmed absent (`0x`).
**Scope:** Ramses Exchange **Legacy AMM** — the Solidly/ve(3,3) classic AMM layer on Arbitrum One. Contracts covered: PairFactory, Pair (LP), Router, Voter (EIP-1967 proxy), VotingEscrow/veRAM (EIP-1967 proxy), Minter, GaugeFactory, BribeFactory (EIP-1967 proxy), RewardDistributor, RAM token. The concentrated-liquidity V2/V3 product is separate. Pharaoh Exchange (Avalanche) is a fork of Ramses — architecture is nearly identical; see `pharaoh/legacy.md` for cross-reference.
**Key facts:** Ramses is **Arbitrum One only** — confirmed `0x` on Ethereum, Base, BNB, Avalanche, Optimism, and Polygon. All core contracts use an `0xAAA` vanity prefix (intentional — Ramses deployer used CREATE2). Epoch-based emissions (weekly RAM mint → VotingEscrow). AMM `Swap` topic0 **matches Uniswap V2 layout**. The `PairCreated` event **includes the `bool stable` field** (5-arg form: `PairCreated(address,address,bool,address,uint256)`), unlike the Pharaoh fork which uses a 3-arg form. The ve(3,3) token is veRAM (ERC-721 via VotingEscrow). The Voter and VotingEscrow are behind EIP-1967 transparent proxies sharing a common ProxyAdmin. Voter voting events are **tokenId-based** (`Voted(address,uint256,uint256)`) unlike some forks that use address-based voting.

---

## 1. Topics (chain-agnostic)

### 1.1 PairFactory

```
0xc4805696c66d7cf352fc1d6bb633ad5ee82f6cb577c453024b6e0eb8306c6fc9  PairCreated(address,address,bool,address,uint256)
    [token0 indexed, token1 indexed, stable (non-indexed), pair (non-indexed), allPairsLength (non-indexed)]
    ← confirmed live on Arbitrum (block 70001290+, 311 pairs total ✓)
    ← NOTE: 5-arg form WITH bool-stable field — differs from Pharaoh fork (3-arg)
```

### 1.2 Pair (LP contract — one deployed per pool)

```
0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  Swap(address,uint256,uint256,uint256,uint256,address)
    [sender indexed, amount0In, amount1In, amount0Out, amount1Out, to indexed]
    ← confirmed live on Arbitrum (WETH/USDC pair 0x5513a48F…, block 471985482)
    ← SAME topic0 as Uniswap V2 Swap — disambiguate by emitting contract

0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1  Sync(uint112,uint112)
    [reserve0, reserve1] — same topic0 as Uniswap V2 Sync

0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f  Mint(address,uint256,uint256)
    [sender, amount0, amount1] — same topic0 as Uniswap V2 Mint

0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496  Burn(address,uint256,uint256,address)
    [sender, amount0, amount1, to]

0x112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602  Fees(address,uint256,uint256)
    [sender, amount0, amount1] — Solidly-fork trading-fee distribution event

0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  Transfer(address,address,uint256)     [ERC-20]
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  Approval(address,address,uint256)     [ERC-20]
```

### 1.3 Voter (EIP-1967 proxy at 0xAAA2564D…)

```
0x48d3c521fd0d5541640f58c6d6381eed7cb2e8c9df421ae165a4f4c2d221ee0d  GaugeCreated(address,address,address,address)
    [pool indexed, gauge indexed, bribeFactory (non-indexed), feeDistributor (non-indexed)]
    ← topic0 confirmed via cast keccak; live events not observed in queried ranges (gauges
      were created at protocol launch, before readily-queryable block ranges)

0xea66f58e474bc09f580000e81f31b334d171db387d0c6098ba47bd897741679b  Voted(address,uint256,uint256)
    [pool indexed, tokenId (non-indexed), weight (non-indexed)]
    ← confirmed live on Arbitrum (block 74900075+, 41 events in sampled 75M range)
    ← NOTE: tokenId-based layout — differs from Pharaoh which uses address-indexed voter

0xa9f3ca5f8a9e1580edb2741e0ba560084ec72e0067ba3423f9e9327a176882db  Abstained(uint256,uint256)
    [tokenId (non-indexed), weight (non-indexed)]
    ← confirmed live on Arbitrum (block 75000286+, 32 events in sampled range)

0x60940192810a6fb3bce3fd3e2e3a13fd6ccc7605e963fb87ee971aba829989bd  Attach(address,address,uint256)
    [token indexed, voter indexed, tokenId (non-indexed)]
    ← confirmed live on Arbitrum (2 events in 75M-80M range); matches 4byte "Attach(address,address,uint256)"

0xae268d9aab12f3605f58efd74fd3801fa812b03fdb44317eb70f46dff0e19e22  Detach(address,address,uint256)
    [token indexed, voter indexed, tokenId (non-indexed)]
    ← confirmed live on Arbitrum (1+ events in sampled range); matches 4byte "Detach(address,address,uint256)"

0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7  Deposit(address,address,uint256,uint256)
    [token indexed, user indexed, tokenId (non-indexed), amount (non-indexed)]
    ← confirmed live on Arbitrum (61 events in 75M range); bribe/gauge reward deposit tracking
    ← collides with ERC-4626 Deposit signature — disambiguate by emitting contract

0xf341246adaac6f497bc2a656f546ab9e182111d630394f0c57c710a59a2cb567  Withdraw(address,address,uint256,uint256)
    [token indexed, user indexed, tokenId (non-indexed), amount (non-indexed)]
    ← confirmed live on Arbitrum (7 events in 75M range); matches 4byte "Withdraw(address,address,uint256,uint256)"

0xf70d5c697de7ea828df48e5c4573cb2194c659f1901f70110c52b066dcf50826  NotifyReward(address,address,uint256)
    [token indexed, gauge indexed, amount] — epoch reward distribution notification

0x4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17  DistributeReward(address,address,uint256)
    [sender indexed, gauge indexed, amount]

0x6661a7108aecd07864384529117d96c319c1163e3010c01390f6b704726e07de  Whitelisted(address,address)
    [whitelister indexed, token indexed]
```

### 1.4 VotingEscrow / veRAM (EIP-1967 proxy at 0xAAA34303…)

```
0xff04ccafc360e16b67d682d17bd9503c4c6b9a131f6be6325762dc9ffc7de624  Deposit(address,uint256,uint256,uint256,uint8,uint256)
    [provider indexed, tokenId indexed, value (non-indexed), locktime (non-indexed),
     depositType (non-indexed), ts (non-indexed)]
    ← confirmed live on Arbitrum (12 events in 75M range, 1 event in 100M range)
    ← 6-param Ramses-specific layout; differs from standard Curve/Aerodrome Deposit layouts

0x5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c  Supply(uint256,uint256)
    [prevSupply, supply] — always paired with Deposit; matches 4byte "Supply(uint256,uint256)"
    ← confirmed live on Arbitrum (12 events in 75M range)

0x02f25270a4d87bea75db541cdfe559334a275b4a233520ed6c0a2429667cca94  Withdraw(address,uint256,uint256,uint256)
    [provider indexed, tokenId (non-indexed), value (non-indexed), ts (non-indexed)]
    ← topic0 confirmed via cast keccak; matches standard veToken Withdraw layout

0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  Transfer(address,address,uint256)     [ERC-721]
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  Approval(address,address,uint256)     [ERC-721]
```

### 1.5 Minter (0xAAAA0b6B…)

```
0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f  Mint(address,uint256,uint256)
    [sender indexed, weekly, circulating_supply] — collides with Uniswap V2 Mint
    Note: RAM.minter() → Minter ✓; Minter.weekly() ≈ 2.61e23 RAM ✓
    No Mint events observed in queried ranges — protocol may be in reduced-emission phase
    or emit at infrequent epoch-flip intervals.
```

### 1.6 Gauge (one deployed per pool — example: 0xDBA865F1…)

```
0x9aa05b3d70a9e3e2f004f039648839560576334fb45c81f91b6db03ad9e2efc9  ClaimRewards(address,address,uint256)
    [user indexed, reward_token indexed, amount (non-indexed)]
    ← confirmed live on Arbitrum (2 events in 75M range on WETH/RAM gauge 0xDBA865F1…)
    ← matches 4byte "ClaimRewards(address,address,uint256)"
```

### 1.7 RewardDistributor (0xAAA86B90…)

```
0xcae2990aa9af8eb1c64713b7eddb3a80bf18e49a94a13fe0d0002b5d61d58f00  Claimed(uint256,uint256,uint256,uint256)
    [tokenId (non-indexed), epoch (non-indexed), claimAmount (non-indexed), claimTotal (non-indexed)]
    ← confirmed live on Arbitrum (1 event in 100M range); matches 4byte "Claimed(uint256,uint256,uint256,uint256)"
    ← distributor.token() → RAM ✓; distributor.voting_escrow() → VotingEscrow ✓

0xce749457b74e10f393f2c6b1ce4261b78791376db5a3f501477a809f03f500d6  CheckpointToken(uint256,uint256)
    [time (non-indexed), tokens (non-indexed)] — periodic RAM balance checkpoint
```

### 1.8 RAM token (0xAAA6C1E3… — ERC-20)

```
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  Transfer(address,address,uint256)
    ← confirmed live on Arbitrum (300+ events in 75M range)
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  Approval(address,address,uint256)
```

---

## 2. Function signatures

### PairFactory
```
0x82dfdce4  createPair(address,address,bool)
0x574f2ba3  allPairsLength()
0x6801cc30  getPair(address,address,bool)
0x1e3dd18b  allPairs(uint256)
0x46c96aac  voter()
```

### Pair (LP)
```
0x0902f1ac  getReserves()
0x562e19df  swap(uint256,uint256,uint256,uint256,address)
0x6a627842  mint(address)
0x89afcb44  burn(address)
0x22be3de1  stable()
```

### Router
```
0xf41766d8  swapExactTokensForTokens(uint256,uint256,(address,address,bool)[],address,uint256)
0x5a47ddc3  addLiquidity(address,address,bool,uint256,uint256,uint256,uint256,address,uint256)
0x0dede6c4  removeLiquidity(address,address,bool,uint256,uint256,uint256,address,uint256)
0x5e1e6325  getAmountOut(uint256,address,address)
0x98a0fb3c  quoteAddLiquidity(address,address,bool,uint256,uint256)   -- 5-arg (no factory param)
```

### Voter
```
0xe4ff5c2f  vote(address,address[],uint256[])
0x6b8ab97d  reset(address)
0xb1a997ac  poke(address)
0x794cea3c  createGauge(address,address)
0x63453ae1  distribute(address)
0xb66503cf  notifyRewardAmount(address,uint256)
0x02fc77fe  claimBribes(address[],address[][],address)
0x0c025d1c  claimFees(address[],address[][],address)
```

### VotingEscrow (veRAM)
```
0xb52c05fe  createLock(uint256,uint256)
0xa183af52  increase_amount(uint256,uint256)
0xa4d855df  increase_unlock_time(uint256,uint256)
0x2e1a7d4d  withdraw(uint256)
0xd1c2babb  merge(uint256,uint256)
0xe7e242d4  balanceOfNFT(uint256)
0xb45a3c0e  locked(uint256)
```

### Minter
```
0xed29fc11  update_period()
0xaf14052c  rebase()
```

### RewardDistributor
```
0x379607f5  claim(uint256)
0x1f1db043  claim_many(uint256[])
0x811a40fe  checkpoint_token()
```

---

## 3. Addresses — Arbitrum One (42161)

> All verified via `eth_getCode` (non-zero bytecode) on publicnode Arbitrum RPC, 2026-06. All contracts show ~4900 bytes for proxies; implementations are full-size contracts.

### Tokens
```
0xAAA6C1E32C55A7Bfa8066A6FAE9b42650F262418  RAM token         (symbol "RAM" ✓; name "Ramses" ✓; totalSupply ~8.51e26 ✓; minter()→Minter ✓)
```

### AMM Core
```
0xAAA20D08e59F6561f242b08513D36266C5A29415  PairFactory       (allPairsLength() → 311 ✓; voter()→Voter ✓; first pair at block 70001290)
0xAAA87963EFeB6f7E0a2711F397663105Acb1805e  Router            (legacy AMM swaps)
```

### Governance & Emissions
```
0xAAA2564DEb34763E3d05162ed3f5C2658691f499  Voter             (EIP-1967 proxy; impl 0xadf8c1d9…; proxy-admin 0xa388d2dd…)
0xAAA343032aA79eE9a6897Dab03bef967c3289a06  VotingEscrow      (EIP-1967 proxy; impl 0xdd4ede1d…; proxy-admin 0xa388d2dd…; veRAM NFT)
0xAAAA0b6BaefaeC478eB2d1337435623500AD4594  Minter            (RAM weekly emissions; _ve()→VotingEscrow ✓; weekly()≈2.61e23 RAM ✓)
0xAAA86B908A3B500A0DE661301ea63966923a97b1  RewardDistributor (Minter._rewards_distributor() ✓; token()→RAM ✓; voting_escrow()→VotingEscrow ✓)
```

### Factories
```
0xAAA35aaEa18B0187E82A3A7f2996C9ee7Bad9696  GaugeFactory      (Voter.gaugefactory() ✓)
0xAAA95622f8570389a9b62bF2ae541f3a313f93e3  BribeFactory      (EIP-1967 proxy; Voter slot 4; impl 0xab8941d3…; proxy-admin 0xa388d2dd…)
```

### Access Control & Admin
```
0xa388d2ddb9ee3c4d84c04eaa396eadb3357d052d  ProxyAdmin        (controls Voter, VotingEscrow, BribeFactory; owner()→Governor ✓)
0x20D630cF1f5628285BfB91DfaC8C89eB9087BE1A  Governor / Emergency Council
```

### Notable LP Pairs (examples)
```
0x5513a48F3692Df1d9C793eeaB1349146B2140386  WETH/USDC volatile pair   (getPair(WETH,USDC,false) ✓; stable()→false ✓; Swap confirmed live)
0x1E50482e9185D9DAC418768D14b2F2AC2b4DAF39  RAM/WETH volatile pair    (allPairs(0) ✓; token0=WETH ✓; token1=RAM ✓)
```

### Notable Gauges (examples)
```
0xafE267681312ED76f0B7aEdFe54C8b200Ec32cFA  RAM/WETH Gauge    (Voter.gauges(RAM/WETH pair) ✓)
0xDBA865F11bb0a9Cd803574eDd782d8B26Ee65767  WETH/USDC Gauge   (Voter.gauges(WETH/USDC pair) ✓; ClaimRewards confirmed live)
```

---

## 4. Cross-chain summary

| Chain | Chain ID | Status |
|-------|----------|--------|
| Arbitrum One | 42161 | **DEPLOYED** — all contracts verified ✓ |
| Ethereum | 1 | absent — `eth_getCode` returns `0x` for RAM token |
| Base | 8453 | absent — `0x` |
| BNB Smart Chain | 56 | absent — `0x` |
| Avalanche C-Chain | 43114 | absent — `0x` |
| Optimism | 10 | absent — `0x` |
| Polygon PoS | 137 | absent — `0x` |

Ramses is **Arbitrum-exclusive**. Any address appearing in these contracts on other chains is coincidence or a different protocol.

---

## 5. Proxies

| Contract | Address | Pattern | Implementation | Proxy Admin |
|----------|---------|---------|----------------|-------------|
| Voter | 0xAAA2564D… | EIP-1967 transparent | 0xadf8c1d9… | 0xa388d2dd… |
| VotingEscrow | 0xAAA34303… | EIP-1967 transparent | 0xdd4ede1d… | 0xa388d2dd… |
| BribeFactory | 0xAAA95622… | EIP-1967 transparent | 0xab8941d3… | 0xa388d2dd… |
| PairFactory | 0xAAA20D08… | **immutable** — no impl slot | — | — |
| Minter | 0xAAAA0b6B… | **immutable** — no impl slot | — | — |
| GaugeFactory | 0xAAA35aae… | **immutable** — no impl slot | — | — |
| RewardDistributor | 0xAAA86B90… | **immutable** — no impl slot | — | — |
| Pairs (LP) | per-pool | CREATE2 immutable | — | — |
| Gauges | per-pool | immutable | — | — |

**Key upgrade path:** A single ProxyAdmin `0xa388d2dd…` (owned by Governor `0x20D630…`) controls Voter, VotingEscrow, and BribeFactory — a single key controls the three most sensitive contracts. Contrast with Pharaoh, which uses separate proxy admin contracts.

**Proxy detection:** All three proxies share the same ProxyAdmin. Calls to the implementation addresses directly will revert on stateful functions (storage lives on proxy). Always target the proxy address.

---

## 6. Detection invariants & gotchas

1. **AMM `Swap` topic0 (`0xd78ad95f…`) matches Uniswap V2.** Ramses pairs use the standard Solidly swap signature identical to Uni V2 — disambiguate exclusively by emitting contract address (compare against `PairFactory.getPair()`).

2. **`PairCreated` is the 5-arg form** — `PairCreated(address,address,bool,address,uint256)` (`0xc4805696…`), which INCLUDES the `bool stable` field in the event data. This differs from Pharaoh (3-arg form, no bool stable). The stable flag is decodeable directly from the event without a follow-up `Pair.stable()` call.

3. **Voter voting is tokenId-based.** `Voted(address,uint256,uint256)` has the pool address as the only indexed topic, with `tokenId` and `weight` in non-indexed data. Compare to `Pharaoh/Velodrome V2` which index the voter address instead.

4. **Abstained has no indexed fields.** `Abstained(uint256,uint256)` = `(tokenId, weight)` — neither is indexed. Filtering requires decoding event data.

5. **`Sync` topic0 (`0x1c411e9a…`) = `Sync(uint112,uint112)`**, identical to Uniswap V2. Ramses pairs inherit this from the Solidly pair base.

6. **Voter is a proxy — calling the implementation directly will revert** on most functions. Storage (gauges map, pool lists, vote weights) lives on the proxy. Always target `0xAAA2564D…`.

7. **VotingEscrow is also a proxy** (`0xAAA34303…`). The veNFT is ERC-721; lock positions are `tokenId`-based. The `Deposit` event uses a 6-param layout specific to Ramses, unlike Curve veCRV or Aerodrome/Velodrome ve.

8. **GaugeCreated events not observed in queried ranges.** All gauge creation for legacy AMM pools occurred at protocol launch (block ~70000205, March 2023). Any future `createGauge()` calls will emit `GaugeCreated(address indexed pool, address indexed gauge, address bribeFactory, address feeDistributor)`.

9. **Voter Deposit/Withdraw events are internal bribe accounting.** The Voter contract emits `Deposit(address indexed token, address indexed user, uint256 tokenId, uint256 amount)` and `Withdraw(address indexed token, address indexed user, uint256 tokenId, uint256 amount)` when users interact with bribes/rewards through the Voter. The `token` topic is a reward token address (not a standard ERC-20 emitter).

10. **`Attach/Detach` are NFT-to-gauge attachment signals.** `Attach(address,address,uint256)` and `Detach(address,address,uint256)` are emitted by the Voter when a veRAM NFT is attached to / detached from a gauge for boosting. They appear infrequently (2–3 events per sampled 9000-block window).

11. **All `0xAAA` addresses are intentional vanity contracts.** The `0xAAA` prefix on all core contracts is a CREATE2 deployment artifact — not a clue about contract type. Do not confuse with standard ERC-20 or protocol addresses.

12. **Single ProxyAdmin controls three critical contracts.** Any admin compromise of `0xa388d2dd…` (owned by `0x20D630…`) allows simultaneous upgrade of Voter, VotingEscrow, and BribeFactory.

---

## 7. Quick-copy detection constants

```
-- PairFactory
\xc4805696c66d7cf352fc1d6bb633ad5ee82f6cb577c453024b6e0eb8306c6fc9  -- PairCreated(address,address,bool,address,uint256)

-- Pair (AMM pool)
\xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  -- Swap(address,uint256,uint256,uint256,uint256,address)
\x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1  -- Sync(uint112,uint112)
\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f  -- Mint(address,uint256,uint256)
\xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496  -- Burn(address,uint256,uint256,address)
\x112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602  -- Fees(address,uint256,uint256)
\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  -- Transfer(address,address,uint256)

-- Voter
\x48d3c521fd0d5541640f58c6d6381eed7cb2e8c9df421ae165a4f4c2d221ee0d  -- GaugeCreated(address,address,address,address)
\xea66f58e474bc09f580000e81f31b334d171db387d0c6098ba47bd897741679b  -- Voted(address,uint256,uint256)
\xa9f3ca5f8a9e1580edb2741e0ba560084ec72e0067ba3423f9e9327a176882db  -- Abstained(uint256,uint256)
\x60940192810a6fb3bce3fd3e2e3a13fd6ccc7605e963fb87ee971aba829989bd  -- Attach(address,address,uint256)
\xae268d9aab12f3605f58efd74fd3801fa812b03fdb44317eb70f46dff0e19e22  -- Detach(address,address,uint256)
\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7  -- Deposit(address,address,uint256,uint256)
\xf341246adaac6f497bc2a656f546ab9e182111d630394f0c57c710a59a2cb567  -- Withdraw(address,address,uint256,uint256)
\xf70d5c697de7ea828df48e5c4573cb2194c659f1901f70110c52b066dcf50826  -- NotifyReward(address,address,uint256)
\x4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17  -- DistributeReward(address,address,uint256)
\x6661a7108aecd07864384529117d96c319c1163e3010c01390f6b704726e07de  -- Whitelisted(address,address)

-- VotingEscrow (veRAM)
\xff04ccafc360e16b67d682d17bd9503c4c6b9a131f6be6325762dc9ffc7de624  -- Deposit(address,uint256,uint256,uint256,uint8,uint256)
\x5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c  -- Supply(uint256,uint256)
\x02f25270a4d87bea75db541cdfe559334a275b4a233520ed6c0a2429667cca94  -- Withdraw(address,uint256,uint256,uint256)

-- Gauge (per-pool)
\x9aa05b3d70a9e3e2f004f039648839560576334fb45c81f91b6db03ad9e2efc9  -- ClaimRewards(address,address,uint256)

-- RewardDistributor
\xcae2990aa9af8eb1c64713b7eddb3a80bf18e49a94a13fe0d0002b5d61d58f00  -- Claimed(uint256,uint256,uint256,uint256)
\xce749457b74e10f393f2c6b1ce4261b78791376db5a3f501477a809f03f500d6  -- CheckpointToken(uint256,uint256)

-- RAM token
\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  -- Transfer(address,address,uint256)
```

---

## 8. Verification & sources

**On-chain verification (Arbitrum One, 2026-06):**
- `eth_getCode` non-zero confirmed for all 11 core addresses
- `PairFactory.allPairsLength()` → 311 ✓
- `RAM.symbol()` → "RAM"; `RAM.name()` → "Ramses"; `RAM.minter()` → Minter ✓
- `VotingEscrow.symbol()` → "veRAM"; `VotingEscrow.name()` → "veRAM" ✓
- `Voter.factory()` → PairFactory ✓; `Voter.gaugefactory()` → GaugeFactory ✓; `Voter.minter()` → Minter ✓
- `Voter.governor()` → `0x20D630…` ✓; `Voter.emergencyCouncil()` → `0x20D630…` ✓
- `Minter._ve()` → VotingEscrow ✓; `Minter._rewards_distributor()` → RewardDistributor ✓; `Minter.weekly()` ≈ 2.61e23 ✓
- `RewardDistributor.token()` → RAM ✓; `RewardDistributor.voting_escrow()` → VotingEscrow ✓
- `ProxyAdmin.owner()` → Governor `0x20D630…` ✓
- EIP-1967 impl slot: Voter → `0xadf8c1d9…`; VotingEscrow → `0xdd4ede1d…`; BribeFactory → `0xab8941d3…`
- EIP-1967 admin slot: Voter, VotingEscrow, BribeFactory all → same ProxyAdmin `0xa388d2dd…`
- Swap (`0xd78ad95f…`) confirmed live on WETH/USDC pair (block 471985482)
- PairCreated (`0xc4805696…`) confirmed live on PairFactory (block 70001290+, 5-arg form with bool stable)
- Voter events confirmed live: Voted (`0xea66f58e…`), Abstained (`0xa9f3ca5f…`), Attach (`0x60940192…`), Detach (`0xae268d9a…`), Deposit (`0xdcbc1c05…`), Withdraw (`0xf341246a…`)
- VotingEscrow events confirmed: Deposit (`0xff04ccaf…`), Supply (`0x5e2aa66e…`), Transfer (`0xddf252ad…`)
- Gauge ClaimRewards (`0x9aa05b3d…`) confirmed live on WETH/USDC gauge (block 75006492)
- RewardDistributor Claimed (`0xcae2990a…`) confirmed live (block 100002162)
- 6-chain absence: `eth_getCode` → `0x` for RAM on Ethereum, Base, BNB, Avalanche, Optimism, Polygon

**Unconfirmed in live logs:**
- `GaugeCreated` (`0x48d3c521…`) — topic0 verified via `cast keccak`; live events not observed (gauges created at protocol launch ~block 70000205, pre-dating readily-queryable windows); Voter.gauges(pair) returns valid gauge addresses confirming prior createGauge calls
- `NotifyReward`, `DistributeReward`, `Whitelisted` — topic0s match Pharaoh fork signatures confirmed via `cast keccak`; not found in sampled 9000-block windows (these are infrequent epoch/admin events)
- `VotingEscrow.Withdraw` — topic0 confirmed via `cast keccak`; not observed in sampled ranges

**Sources:**
- Contract addresses: on-chain verified from Voter storage slots + view calls
- Codebase lineage: Ramses Exchange ← Velodrome V1 ← Solidly (Andre Cronje); Pharaoh Exchange is a fork of Ramses
- Topic0 resolution: `cast keccak` + live `eth_getLogs` on Arbitrum One publicnode + [4byte.directory](https://www.4byte.directory) event-signatures API
- RPC: `https://arbitrum-one-rpc.publicnode.com` (verified 2026-06, latest block ~471 988 431)
- Reference fork: [`pharaoh/legacy.md`](../pharaoh/legacy.md) (Pharaoh Exchange — Ramses fork on Avalanche, same architecture)
