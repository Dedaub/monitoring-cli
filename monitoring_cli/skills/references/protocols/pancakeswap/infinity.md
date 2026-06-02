# PancakeSwap Infinity (V4) — Compressed Reference (BSC, Base)

**Status:** CL event topic0s via `cast keccak` from `pancakeswap/infinity-core` source (verified); core addresses on-chain re-verified with `cast` vs `publicnode` (2026-05). Bin-pool events + non-BSC addresses partly sourced/UNVERIFIED — see §Verification.
**Scope:** PancakeSwap **Infinity** (its "V4" — a singleton + hooks architecture; BSC mainnet launch **April 28, 2025**, Base deployment **July 22, 2025**). Two AMM types share one accounting **Vault**: **CLPoolManager** (concentrated liquidity) and **BinPoolManager** (liquidity-book / bins). Deployed on **BSC and Base**. Other versions: [`v2.md`](v2.md), [`v3.md`](v3.md), [`stableswap.md`](stableswap.md). Shared CAKE/router: [`v2.md`](v2.md).
**Key facts:** Singleton design (like Uniswap V4) — pools are **not** separate contracts; they live inside the PoolManagers, keyed by a `PoolId` (bytes32). All swap/liquidity events emit from the **CLPoolManager / BinPoolManager**, and token settlement flows through the **Vault** (transient accounting, EIP-1153). Per-pool **hooks** are supported. Pancake's events differ from Uniswap V4's (different field layouts) → Pancake-specific topic0s.

---

## Topics (chain-agnostic) — CLPoolManager (verified from infinity-core source)
```
0x426cc62fe6a33a40ba2788c2c87a9c34ee4582b95bc9fa5a7bb7ae70b750b99c -> Initialize(bytes32,address,address,address,uint24,bytes32,uint160,int24)   [id,currency0,currency1,hooks,fee,parameters,sqrtPriceX96,tick]
0x616cf9d5fac4bdb02d289a94b5abf269a41b80c3273f57f560639a5b0e0f1e12 -> Swap(bytes32,address,int256,int256,uint160,uint128,int24,uint24,uint24)   [id,sender,amount0,amount1,sqrtPriceX96,liquidity,tick,swapFee,protocolFee]
0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec -> ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)   [id,sender,tickLower,tickUpper,liquidityDelta,salt]
0xbe708911656ae186ac3fc26a794e5f1319609ce340a14c63524f985fee4bc841 -> Donate(bytes32,address,uint256,uint256,int24)
0x14b2b80e0d62303dc85494859f35a84579160aafbd650180ddf526b1ab547bd6 -> DynamicLPFeeUpdated(bytes32,uint24)
```

> **BinPoolManager** emits an analogous set (`Initialize`, `Swap`, `Mint`/`Burn` for bins, `Donate`) but with **bin-specific fields** (active bin id, bin reserves) → different topic0s. Those were **not** computed this run — read `infinity-core/src/pool-bin/BinPoolManager.sol` and `cast keccak` each before relying on them. The **Vault** emits accounting events on settle/take.

---

## Function signatures
```
# Swaps/liquidity go through the Router/Universal Router which call the PoolManagers via the Vault's lock/settle pattern.
# CLPoolManager.vault() -> address (verified getter). Direct PoolManager calls are gated by the Vault lock.
```

---

## Addresses (network-specific)

> ✓ = on-chain verified this run. Infinity is on **BSC and Base** (not Ethereum/Arbitrum as of 2026-05 — confirm before assuming).

### BSC (56)
```
0xa0FfB9c1CE1Fe56963B0321B32E7A0302114058b -> CLPoolManager (20885B code ✓; vault()→Vault below ✓)
0x238a358808379702088667322f80aC48bAd5e6c4 -> Vault (resolved via CLPoolManager.vault() ✓)
# BinPoolManager, Position Managers (CL/Bin), Infinity Universal Router, Quoter -> in dev docs / infinity-core deploy config; not verified here.
0xd9C500DfF816a1Da21A48A732d3498Bf09dC9AEB -> Universal Router 2 (also routes Infinity)
```

### Base (8453)
```
# Infinity Vault + CLPoolManager + BinPoolManager addresses -> PancakeSwap dev docs (/contracts/infinity/resources/addresses); not verified here.
```

---

## Proxies
- **Singleton, not per-pool contracts.** Pools live inside CLPoolManager/BinPoolManager (no per-pool address); identify a pool by its `PoolId` (bytes32) in event topic/data, not by a contract address.
- The Vault ↔ PoolManager use a **lock/settle transient-accounting** pattern (EIP-1153). Per-pool **hooks** are external contracts called around swaps/liquidity (a swap tx touches the PoolManager + Vault + optionally a hook).
- Whether the Vault/PoolManagers sit behind upgrade proxies: confirm on-chain (`cast code` + EIP-1967 slot) per deployment.

---

## Detection invariants & gotchas
1. **No per-pool addresses** — monitor the CLPoolManager / BinPoolManager (one address each per chain) and filter by `PoolId`. This is the V4/Infinity analogue of "watch the Balancer Vault."
2. **Pancake Infinity events ≠ Uniswap V4 events** (different field layouts) — the topic0s above are Pancake-specific.
3. **Two AMM types** (CL + Bin) under one Vault — CL is Uniswap-V3-like (ticks); Bin is a liquidity-book (discrete bins). Their `Swap` events differ.
4. CL `Swap` carries `swapFee` + `protocolFee` (both uint24) inline.

---

## Verification & sources
- CL topic0s: `cast keccak` from `pancakeswap/infinity-core` `src/pool-cl/CLPoolManager.sol` (events confirmed present in source).
- Addresses: BSC CLPoolManager `0xa0FfB9c1…` (20885B) + Vault `0x238a3588…` verified on-chain (`vault()` getter). BinPoolManager, position managers, Base addresses, and Bin-pool event topic0s are **NOT verified this run** — complete from `infinity-core` deploy config + the dev docs + explorer.
- Source: [`pancakeswap/infinity-core`](https://github.com/pancakeswap/infinity-core) · [`pancakeswap/infinity-periphery`](https://github.com/pancakeswap/infinity-periphery) · dev docs `/contracts/infinity/resources/addresses` (Cloudflare-gated).
