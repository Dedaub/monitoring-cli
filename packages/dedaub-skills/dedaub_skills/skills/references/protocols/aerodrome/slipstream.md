# Aerodrome / Velodrome Slipstream (Concentrated Liquidity) — Compressed Reference (Base + Optimism)

**Status:** topic0/selectors via `cast keccak`/`cast sig` (verified, read from `aerodrome-finance/slipstream` source); addresses on-chain re-verified with `cast` vs `publicnode` (2026-05) — NFPM `symbol()` = "AERO-CL-POS" / "VELO-CL-POS".
**Scope:** **Slipstream** — the concentrated-liquidity AMM of **Aerodrome (Base)** and **Velodrome (Optimism)**, a Uniswap-V3-based core with ve(3,3) gauge integration. The classic Solidly AMM + the shared **ve(3,3) governance** (Voter, VotingEscrow, AERO/VELO, gauges) are in [`amm.md`](amm.md) — Slipstream pools plug into that same governance.
**Key fact:** Slipstream's CL pool events are a **Uniswap-V3 fork → core pool event topic0s are IDENTICAL to Uniswap V3** (`uniswap/v3.md`); differences are: a Slipstream-specific **`CollectFees`** (gauge fee withdrawal), a **tickSpacing-based `PoolCreated`** (no fee tiers), and pools indexed by **tickSpacing** rather than fee.

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
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef -> Transfer(address,address,uint256)   [ERC-721]
```

---

## Function signatures (chain-agnostic)
> CL pool/router/NFPM selectors are Uniswap-V3-shaped — full lists in `uniswap/v3.md` §2. Key Slipstream-specific:
```
0x128acb08 -> swap(address,bool,int256,uint160,bytes) -> (int256,int256)   [CL Pool; = Uni V3]
0x28af8d0b -> getPool(address,address,int24) -> address                    [CLFactory; tickSpacing arg, not fee]
```

---

## Addresses (network-specific)

> ✓ = on-chain verified this run. Shared ve(3,3) governance (Voter/VotingEscrow/AERO/VELO): see [`amm.md`](amm.md).

### Aerodrome Slipstream — Base (chain ID 8453)
```
0x5e7BB104d84c7CB9B682AaC2F3d509f5F406809A -> CLFactory (voter()→Aerodrome Voter ✓)
0x827922686190790b37229fd06084350E74485b72 -> NonfungiblePositionManager (symbol "AERO-CL-POS" ✓)
0xBE6D8f0d05cC4be24d5167a3eF062215bE6D18a5 -> CL SwapRouter (factory()→CLFactory ✓)
```

### Velodrome Slipstream — Optimism (chain ID 10)
```
0xCc0bDDB707055e04e497aB22a59c2aF4391cd12F -> CLFactory (voter()→Velodrome Voter ✓)
0x416b433906b1B72FA758e166e239c43d68dC6F29 -> NonfungiblePositionManager (symbol "VELO-CL-POS" ✓)
```

---

## Proxies

- **CL Pools: NO upgradeable proxy.** Slipstream pools are CREATE2-deployed by the CLFactory (Uniswap-V3-style), keyed by `(token0, token1, tickSpacing)`; pool logic is immutable. Enumerate via `PoolCreated`.
- Like Uniswap V3, the NFPM's token (SVG) descriptor may sit behind an EIP-1967 proxy — verify per deployment.
- ve(3,3) governance contracts: see [`amm.md`](amm.md).

---

## Detection invariants & gotchas

1. **Core CL events share Uniswap V3 topic0s** — a Slipstream `Swap` is indistinguishable from a Uniswap-V3 / Sushi-V3 `Swap` by topic0 alone; disambiguate by the **pool/factory address** (CLFactory above).
2. **`CollectFees` (`0x205860e6…`) is Slipstream-only** — gauge withdrawal of accrued pool fees; no Uniswap V3 equivalent. Useful to attribute fee flow to the ve(3,3) gauge.
3. **Pools are tickSpacing-keyed, not fee-tier-keyed.** `PoolCreated` (`0xab0d57f0…`) carries `tickSpacing` and differs from Uniswap V3's `PoolCreated` topic0; `getPool` takes `int24 tickSpacing`, not `uint24 fee`.
4. **CL LP fees route to gauges**, not just the LP — Slipstream integrates emissions/fees with the ve(3,3) Voter (see [`amm.md`](amm.md)).

---

## Verification & sources

- topic0/selectors: `cast keccak`/`cast sig` this session; core CL events re-confirmed identical to verified `uniswap/v3.md`; `CollectFees` + tickSpacing `PoolCreated` read from `aerodrome-finance/slipstream` (`contracts/core/interfaces/pool/ICLPoolEvents.sol`).
- Addresses: on-chain verified via `cast` vs `publicnode` — CLFactory `voter()` (→ the chain's Voter), NFPM `symbol()` ("AERO-CL-POS" / "VELO-CL-POS"), Aerodrome SwapRouter `factory()` (→ CLFactory).
- Source: [`aerodrome-finance/slipstream`](https://github.com/aerodrome-finance/slipstream) · [`velodrome-finance/slipstream`](https://github.com/velodrome-finance/slipstream). AMM + governance: [`amm.md`](amm.md).
