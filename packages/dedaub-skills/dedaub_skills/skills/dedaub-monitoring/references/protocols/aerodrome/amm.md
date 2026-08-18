# Aerodrome / Velodrome AMM (Solidly ve(3,3)) — Compressed Reference (Base + Optimism)

**Status:** topic0/selectors via `cast keccak`/`cast sig` (verified, read from `aerodrome-finance/contracts` source); addresses on-chain re-verified with `cast` vs `publicnode` (2026-05).
**Scope:** the classic **Solidly-style AMM** (volatile + stable pools) and the **ve(3,3) governance** stack (Voter, VotingEscrow veNFT, Gauge, AERO/VELO) of **Aerodrome (Base)** and its identical-codebase twin **Velodrome (Optimism)**. The concentrated-liquidity product is in [`slipstream.md`](slipstream.md). **This file holds the shared ve(3,3) governance** (same contracts back both AMM and Slipstream); slipstream.md references it.
**Key facts:** Aerodrome ⇒ **Base only**, Velodrome ⇒ **Optimism only** — same code (Velodrome V2), different addresses + token. The veToken is an **ERC-721 veNFT**, not an ERC-20. The AMM `Swap` topic0 **differs from Uniswap V2** (different arg layout), but several other events collide by signature with Uni V2 / Curve / Balancer / Sushi (see Detection).

---

## Topics (chain-agnostic — shared Aerodrome+Velodrome codebase)

### AMM Pool (volatile + stable; emitted by each Pool)
```
0xb3e2773606abfd36b5bd91394b3a54d1398336c65005baf7bf7a05efeffaf75b -> Swap(address,address,uint256,uint256,uint256,uint256)   [sender,to,amount0In,amount1In,amount0Out,amount1Out — NOT the Uni V2 layout]
0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f -> Mint(address,uint256,uint256)              [collides w/ Uniswap V2 / Sushi Mint topic0]
0x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2 -> Burn(address,address,uint256,uint256)      [sender,to,amount0,amount1]
0xcf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a -> Sync(uint256,uint256)                       [collides w/ Sushi Trident Sync topic0]
0x112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602 -> Fees(address,uint256,uint256)              [trading fees accrued to the fee-reward]
0x865ca08d59f5cb456e85cd2f7ef63664ea4f73327414e9d8152c4158b0e94645 -> Claim(address,address,uint256,uint256)
```

### PoolFactory
```
0x2128d88d14c80cb081c1252a5acff7a264671bf199ce226b53788fb26065005e -> PoolCreated(address,address,bool,address,uint256)   [token0,token1,stable,pool,allPoolsLength]
```
The `bool stable` (indexed) distinguishes a **stable** pool (Solidly x³y+y³x curve) from a **volatile** pool (xy=k). Watch this to enumerate all pools.

### Voter (ve(3,3) gauge voting / emissions direction)
```
0xef9f7d1ffff3b249c6b9bf2528499e935f7d96bb6d6ec4e7da504d1d3c6279e1 -> GaugeCreated(address,address,address,address,address,address,address,address)   [poolFactory,votingRewardsFactory,gaugeFactory,pool,bribeVotingReward,feeVotingReward,gauge,creator]
0x04a5d3f5d80d22d9345acc80618f4a4e7e663cf9e1aed23b57d975acec002ba7 -> GaugeKilled(address)
0xed18e9faa3dccfd8aa45f69c4de40546b2ca9cccc4538a2323531656516db1aa -> GaugeRevived(address)
0x452d440efc30dfa14a0ef803ccb55936af860ec6a6960ed27f129bef913f296a -> Voted(address,address,uint256,uint256,uint256,uint256)        [voter,pool,tokenId,weight,totalWeight,timestamp]
0xadab630928b1d46214641293704a312ee7ad87e03ae14a7fd95e7308b93998df -> Abstained(address,address,uint256,uint256,uint256,uint256)
0xf70d5c697de7ea828df48e5c4573cb2194c659f1901f70110c52b066dcf50826 -> NotifyReward(address,address,uint256)        [Voter]
0x4fa9693cae526341d334e2862ca2413b2e503f1266255f9e0869fb36e6d89b17 -> DistributeReward(address,address,uint256)
```

### VotingEscrow (veAERO / veVELO — ERC-721 veNFT)
```
0x8835c22a0c751188de86681e15904223c054bedd5c68ec8858945b7831290273 -> Deposit(address,uint256,uint8,uint256,uint256,uint256)   [provider,tokenId,depositType(enum),value,locktime,ts — NOT the Curve veCRV layout]
0x02f25270a4d87bea75db541cdfe559334a275b4a233520ed6c0a2429667cca94 -> Withdraw(address,uint256,uint256,uint256)   [provider,tokenId,value,ts]
0x5e2aa66efd74cce82b21852e317e5490d9ecc9e6bb953ae24d90851258cc2f5c -> Supply(uint256,uint256)                     [collides w/ Curve/Balancer veToken Supply topic0]
0x793cb7a30a4bb8669ec607dfcbdc93f5a3e9d282f38191fddab43ccaf79efb80 -> LockPermanent(address,uint256,uint256,uint256)
0x668d293c0a181c1f163fd0d3c757239a9c17bd26c5e483150e374455433b27fa -> UnlockPermanent(address,uint256,uint256,uint256)
# also emits ERC-721 Transfer(address,address,uint256) 0xddf252ad… and Merge/Split/CreateManaged/DepositManaged/WithdrawManaged
```

### Gauge (per-pool LP staking → AERO/VELO emissions)
```
0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c -> Deposit(address,uint256)        [collides w/ Curve/Balancer gauge Deposit topic0]
0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364 -> Withdraw(address,uint256)       [collides w/ Curve/Balancer gauge Withdraw topic0]
0x095667752957714306e1a6ad83495404412df6fdb932fca6dc849a7ee910d4c1 -> NotifyReward(address,uint256)   [Gauge variant — 2-arg, distinct from Voter's 3-arg NotifyReward]
0x1f89f96333d3133000ee447473151fa9606543368f02271c9d95ae14f13bcc67 -> ClaimRewards(address,uint256)
```

---

## Function signatures (chain-agnostic) — `selector -> name(types) -> returns`
```
0xcac88ea9 -> swapExactTokensForTokens(uint256,uint256,(address,address,bool,address)[],address,uint256) -> uint256[]   [Router; Route{from,to,stable,factory}[]]
0x79bc57d5 -> getPool(address,address,bool) -> address       [PoolFactory; note the `bool stable`]
0x7ac09bf7 -> vote(uint256,address[],uint256[])              [Voter: tokenId, pools, weights]
```

---

## Addresses (network-specific)

> ✓ = on-chain verified this run. The two deployments share code; only addresses + token differ.

### Aerodrome — Base (chain ID 8453)
```
0x940181a94A35A4569E4529A3CDfB74e38FD98631 -> AERO token (symbol "AERO" ✓)
0x420DD381b31aEf6683db6B902084cB0FFECe40Da -> PoolFactory (allPoolsLength 27708 ✓)
0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43 -> Router (defaultFactory()→PoolFactory ✓)
0x16613524e02ad97eDfeF371bC883F2F5d6C480A5 -> Voter (ve()→VotingEscrow ✓)
0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4 -> VotingEscrow / veAERO (token()→AERO ✓)
0xeB018363F0a9Af8f91F06FEe6613a751b2A33FE5 -> Minter (AERO emissions; 7403B code ✓)
```

### Velodrome — Optimism (chain ID 10)
```
0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db -> VELO token (symbol "VELO" ✓)
0xF1046053aa5682b4F9a81b5481394DA16BE5FF5a -> PoolFactory (allPoolsLength 1354 ✓)
0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858 -> Router (defaultFactory()→PoolFactory ✓)
0x41C914ee0c7E1A5edCD0295623e6dC557B5aBf3C -> Voter (ve()→VotingEscrow ✓)
0xFAf8FD17D9840595845582fCB047DF13f006787d -> VotingEscrow / veVELO (token()→VELO ✓)
```

Slipstream (CL) addresses for both chains are in [`slipstream.md`](slipstream.md).

---

## Proxies

- **AMM Pools: NO upgradeable proxy.** PoolFactory CREATE2-deploys each Pool (salt from `(token0, token1, stable)`); pool logic is immutable. Enumerate via `PoolCreated`.
- **Governance (Voter, VotingEscrow, Gauge, Minter, token): immutable** Velodrome-V2/Aerodrome deploys (not behind upgrade proxies). Gauges are created per-pool by the Voter via gauge factories (fresh deploys, not 1167 clones).
- (Slipstream CL pools are CREATE2-deployed Uni-V3-style — see [`slipstream.md`](slipstream.md).) See `references/proxies.md` for general detection.

---

## Detection invariants & gotchas

1. **AMM `Swap` topic0 (`0xb3e27736…`) ≠ Uniswap V2 `Swap` (`0xd78ad95f…`).** Different arg layout (`amount0In,amount1In,amount0Out,amount1Out` vs Uni V2's order). Don't reuse the Uni V2 constant.
2. **Same-name topic0 collisions** (disambiguate by emitting contract): `Mint(address,uint256,uint256)` `0x4c209b5f…` = Uniswap V2 / Sushi V2 Mint; `Sync(uint256,uint256)` `0xcf2aa508…` = Sushi Trident Sync; veNFT `Supply` `0x5e2aa66e…` = Curve/Balancer veToken Supply; Gauge `Deposit` `0xe1fffcc4…` / `Withdraw` `0x884edad9…` = Curve/Balancer gauge Deposit/Withdraw.
3. **veToken is an ERC-721 NFT** (veNFT), so locks/votes are keyed by `tokenId`, and the escrow emits ERC-721 `Transfer`. `Deposit` carries a `depositType` enum — its topic0 (`0x8835c22a…`) differs from Curve's veCRV `Deposit`.
4. **`stable` bool in `PoolCreated` / `getPool`** separates stable (Solidly curve) from volatile (xy=k) pools — a token pair can have BOTH. Condition pool lookups on `(token0, token1, stable)`.
5. **Two `NotifyReward` events**: Voter's is `(address,address,uint256)` (`0xf70d5c69…`); Gauge's is `(address,uint256)` (`0x09566775…`). Different topic0 — don't conflate.
6. **Bytea hex literals must have even digit count** (40 for addresses, 64 for topics).

---

## Verification & sources

- topic0/selectors: `cast keccak`/`cast sig` this session, from `aerodrome-finance/contracts` source (`Pool`, `interfaces/IVotingEscrow`, `interfaces/IVoter`) — Velodrome shares this codebase.
- Addresses: on-chain verified via `cast` vs `publicnode` — AERO/VELO `symbol()`, PoolFactory `allPoolsLength()` (Base 27708 / OP 1354), Router `defaultFactory()`, Voter `ve()`, VotingEscrow `token()`, Minter code. All cross-reference consistently.
- Source: [`aerodrome-finance/contracts`](https://github.com/aerodrome-finance/contracts) · [`velodrome-finance/contracts`](https://github.com/velodrome-finance/contracts). Concentrated liquidity: [`slipstream.md`](slipstream.md).
