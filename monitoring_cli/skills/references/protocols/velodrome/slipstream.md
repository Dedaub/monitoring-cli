# Velodrome Slipstream (Concentrated Liquidity) — Compressed Reference (Optimism + Superchain)

**Status:** topic0/selectors via local keccak from `velodrome-finance/slipstream` + `superchain-slipstream` source; addresses from each repo's `deployment-addresses/`/`script/constants/output/` re-verified on-chain (publicnode/drpc, 2026-06) — NFPM `symbol()` = "VELO-CL-POS".
**Scope:** **Slipstream** — Velodrome's concentrated-liquidity AMM (a **Uniswap-V3 fork** with ve(3,3) gauge integration). Classic AMM + shared ve(3,3) governance (Voter, VotingEscrow, VELO, gauges) are in [`v2.md`](v2.md) — Slipstream pools plug into that same governance.
**Key fact:** Slipstream CL pool events are a Uniswap-V3 fork → **core pool event topic0s are IDENTICAL to Uniswap V3** ([`uniswap/v3.md`](../uniswap/v3.md)); the differences are a Slipstream-specific **`CollectFees`** (gauge fee withdrawal), a **tickSpacing-based `PoolCreated`** (no fee tiers), and pools indexed by **tickSpacing** not fee.

---

## Topics (chain-agnostic)

### CL Pool — core events IDENTICAL to Uniswap V3 (see `uniswap/v3.md` §1.1)
```
0x98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95 -> Initialize(uint160,int24)
0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67 -> Swap(address,address,int256,int256,uint160,uint128,int24)
0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde -> Mint(address,address,int24,int24,uint128,uint256,uint256)
0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c -> Burn(address,int24,int24,uint128,uint256,uint256)
0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0 -> Collect(address,address,int24,int24,uint128,uint128)
0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633 -> Flash(address,address,uint256,uint256,uint256,uint256)
```

### CL Pool — Slipstream-specific
```
0x205860e66845f2bbc0966bfab80db9bf93fca93862ea2b9fcf6945748352b4a3 -> CollectFees(address,uint128,uint128)   [protocol/gauge fees withdrawn by the gauge — no Uni V3 equivalent]
```

### CLFactory
```
0xab0d57f0df537bb25e80245ef7748fa62353808c54d6e528a9dd20887aed9ac2 -> PoolCreated(address,address,int24,address)   [token0,token1,tickSpacing,pool — tickSpacing-indexed, NOT Uni V3's (token0,token1,fee,tickSpacing,pool)]
```

### NonfungiblePositionManager (CL position NFT) — events IDENTICAL to Uniswap V3 NPM
```
0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f -> IncreaseLiquidity(uint256,uint128,uint256,uint256)
0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4 -> DecreaseLiquidity(uint256,uint128,uint256,uint256)
0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01 -> Collect(uint256,address,uint256,uint256)
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef -> Transfer(address,address,uint256)   [ERC-721 position NFT]
```

---

## Function signatures (chain-agnostic)
> CL pool/router/NFPM selectors are Uniswap-V3-shaped — full lists in `uniswap/v3.md` §2. Slipstream-specific:
```
0x128acb08 -> swap(address,bool,int256,uint160,bytes) -> (int256,int256)   [CL Pool; = Uni V3]
0x28af8d0b -> getPool(address,address,int24) -> address                    [CLFactory; tickSpacing arg, not fee]
```

---

## Addresses (network-specific)

> ✓ = on-chain verified this run. Shared ve(3,3) governance (Voter/VotingEscrow/VELO): see [`v2.md`](v2.md).

### Velodrome Slipstream — Optimism (chain ID 10) — TWO live CL deployments

**Primary / dominant deployment** (3.8M positions minted — by far the most liquidity):
```
0xCc0bDDB707055e04e497aB22a59c2aF4391cd12F -> CLFactory (voter()→Velodrome Voter ✓)
0x416b433906b1B72FA758e166e239c43d68dC6F29 -> NonfungiblePositionManager (symbol "VELO-CL-POS" ✓; totalSupply ~3.80M ✓)
```

**Secondary deployment** (repo-canonical `DeployCL-Optimism.json`, ~125k positions — also live, voter→same Voter):
```
0xe13Dd1fbA721Aa81a1826D9523AC9BC7d260c879 -> PoolFactory/CLFactory (voter()→Velodrome Voter ✓)
0xf7f8ccce99Ca2896eC75D3A399D152dB96808399 -> NonfungiblePositionManager (symbol "VELO-CL-POS" ✓; totalSupply ~125k ✓)
0xf7f8ccce99Ca2896eC75D3A399D152dB96808399 -> NFPM; descriptor 0xe5e47ac4b5389cf4A2df66315d57F4f62Ae80f9f
0xbA3aEe516399388C779463183d00bB579f5041Ca -> SwapRouter
0xAd432b2ca49965266133F2bd4c17dc1Ec12f5DEB -> Quoter
0x21fcc0C421Ae0a5F6919535EcF000688a0413b92 -> MixedQuoter   (0xE5Db7C27…=V2, 0xAf6EBdf4…=V3)
0x9b23957290d8e4709fb1E1512EDc29E17C17DC99 -> GaugeFactory (CL gauges)   (impl 0xb5f7bd1C…)
0x11B234946F28A3905710922138C65FBbe7496b4C -> PoolImplementation
0xbf571c205f45d29a99a9B5f0485E131D7E943f1c -> DynamicSwapFeeModule   (UnstakedFeeModule 0x2B2A6209…)
0xeE03E08107755BC34412E78377B971ECc7153590 -> LpMigrator
```
> Both deployments are real and active — monitor **both** factories/NFPMs. The `0xCc0bDDB7`/`0x416b4339` pair holds the vast majority of liquidity; the `0xe13Dd1fb`/`0xf7f8ccce` pair is the repo's latest deployment output.

**Universal Router (Optimism)** — Velodrome's unified V2+Slipstream swap router:
```
0x01D40099fCD87C018969B0e8D4aB1633Fb34763C -> UniversalRouter
0x494bbD8A3302AcA833D307D11838f18DbAdA9C25 -> Permit2
```

### Superchain Slipstream CL — root (Optimism) + ALL leaf chains (deterministic, shared addresses)

> `superchain-slipstream` — the cross-chain CL layer. Root factory on Optimism; leaf factory + full periphery share **identical addresses on every leaf chain** (Mode/Lisk/Soneium/Unichain/…).
```
# Root (Optimism)
0x718E46d0962A66942E233760a8bd6038Ce54EdCD -> rootPoolFactory (CL)
0x21dd3D2fe97ACD3bD4E597b515e572373f1C895D -> rootGaugeFactory (CL)
0x5270d75326b0dD0607E4c8d8648A7f8CA7bFc003 -> rootPoolImplementation (CL)
0x846B5Cec4B4C3f7B95b3321D01e38a72D358F5C0 -> mixedRouteQuoterV2 (also on Base)

# Leaf (SAME on every leaf chain — Mode/Lisk/Soneium/Unichain/Metal/Ink/Fraxtal/Celo/Superseed/Swell)
0x718E46d0962A66942E233760a8bd6038Ce54EdCD -> leafPoolFactory (CL)
0x21dd3D2fe97ACD3bD4E597b515e572373f1C895D -> leafGaugeFactory (CL)
0x5270d75326b0dD0607E4c8d8648A7f8CA7bFc003 -> leafPoolImplementation (CL)
0xefD0f78F93f578036AE34D52A813a4BE7D8D2D52 -> NonfungiblePositionManager (CL position NFT)   (descriptor 0xDb142C1f…)
0xc58C8aC11b62D9f649Ba6EBA19d6b70FcbBb2E80 -> SwapRouter (CL)
0x426ef6F781bA0Fbc1A7b0D3399D6FA6548464C85 -> Quoter
0x6Fb85c9dF1cd5B04227852997a47A97FD674d57e -> MixedQuoter   (V2 0x150C4336…, V3 0x910c8871…)
0xF3a2a7168438792f6C688AE5374bE852C7ed0F35 -> swapFeeModule    (unstakedFeeModule 0x151ff9D2…)
0xbA3aEe516399388C779463183d00bB579f5041Ca -> slipstreamSugar (lens)
0xCE7420BaF8E3C4EDb3B27Be6425FA1304E0d09fE -> LpMigrator
```

**Base note:** `superchain-slipstream/base.json` contains only `mixedRouteQuoterV2` — there is **no Velodrome CL AMM on Base** (Aerodrome's Slipstream serves Base — see [`aerodrome/slipstream.md`](../aerodrome/slipstream.md)).

---

## Proxies

- **CL Pools: NO upgradeable proxy.** Slipstream pools are CREATE2-deployed by the CLFactory (Uniswap-V3-style), keyed by `(token0, token1, tickSpacing)`; pool logic is immutable (cloned from `PoolImplementation`). Enumerate via `PoolCreated`.
- Like Uniswap V3, the NFPM's SVG token descriptor may sit behind an EIP-1967 proxy — verify per deployment.
- ve(3,3) governance contracts: see [`v2.md`](v2.md).

---

## Detection invariants & gotchas

1. **Core CL events share Uniswap V3 topic0s** — a Slipstream `Swap`/`Mint`/`Burn` is indistinguishable from Uni-V3/Sushi-V3 by topic0 alone; **disambiguate by pool/factory address**.
2. **`CollectFees` (`0x205860e6…`) is Slipstream-only** — gauge withdrawal of accrued pool fees; no Uni V3 equivalent. Useful to attribute fee flow to the ve(3,3) gauge.
3. **Pools are tickSpacing-keyed, not fee-tier-keyed.** `PoolCreated` (`0xab0d57f0…`) carries `tickSpacing`; `getPool` takes `int24 tickSpacing`.
4. **Two live OP CL deployments** (`0xCc0bDDB7` and `0xe13Dd1fb`) — a complete monitor watches both CLFactories + both NFPMs.
5. **CL LP fees route to gauges**, integrating emissions/fees with the ve(3,3) Voter (see [`v2.md`](v2.md)).

---

## Verification & sources
- topic0/selectors: local keccak this session; core CL events re-confirmed identical to verified `uniswap/v3.md`; `CollectFees` + tickSpacing `PoolCreated` from `velodrome-finance/slipstream` (`contracts/core/interfaces/pool/ICLPoolEvents.sol`).
- Addresses: OP CLFactory `voter()` (→ Velodrome Voter), NFPM `symbol()`="VELO-CL-POS" + `totalSupply()` (3.80M vs 125k); superchain-slipstream `deployment-addresses/*.json` (root-optimism + leaf, deterministic).
- Source: [`velodrome-finance/slipstream`](https://github.com/velodrome-finance/slipstream) · [`velodrome-finance/superchain-slipstream`](https://github.com/velodrome-finance/superchain-slipstream) · [`velodrome-finance/universal-router`](https://github.com/velodrome-finance/universal-router). AMM+governance: [`v2.md`](v2.md). Cross-chain: [`superchain.md`](superchain.md).
