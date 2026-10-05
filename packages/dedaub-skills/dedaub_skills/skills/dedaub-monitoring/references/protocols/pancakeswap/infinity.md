# PancakeSwap Infinity (V4) — Compressed Reference (BSC, Base, Arc)

**Status:** CL event topic0s recomputed as `keccak256(sig)` from `pancakeswap/infinity-core` `ICLPoolManager.sol` and matched against live BSC logs (2026-10); core addresses existence-checked via `eth_getCode` on BSC, Base and Arc (2026-10). Bin-pool event topic0s still UNVERIFIED — see §Verification.
**Scope:** PancakeSwap **Infinity** (its "V4" — a singleton + hooks architecture; BSC mainnet launch **April 28, 2025**, Base deployment **July 22, 2025**). Two AMM types share one accounting **Vault**: **CLPoolManager** (concentrated liquidity) and **BinPoolManager** (liquidity-book / bins). Deployed on **BSC and Base** (full CL + Bin set) and on **Arc (5042)** (CL only; no BinPoolManager, checked 2026-10). Other versions: [`v2.md`](v2.md), [`v3.md`](v3.md), [`stableswap.md`](stableswap.md). Shared CAKE/router: [`v2.md`](v2.md).
**Key facts:** Singleton design (like Uniswap V4) — pools are **not** separate contracts; they live inside the PoolManagers, keyed by a `PoolId` (bytes32). All swap/liquidity events emit from the **CLPoolManager / BinPoolManager**, and token settlement flows through the **Vault** (transient accounting, EIP-1153). Per-pool **hooks** are supported. Pancake's events differ from Uniswap V4's (different field layouts) → Pancake-specific topic0s.

---

## Topics (chain-agnostic) — CLPoolManager (verified from infinity-core source)
```
0x426cc62fe6a33a40ba2788c2c87a9c34ee4582b95bc9fa5a7bb7ae70b750b99c -> Initialize(bytes32,address,address,address,uint24,bytes32,uint160,int24)   [id,currency0,currency1,hooks,fee,parameters,sqrtPriceX96,tick]
0x04206ad2b7c0f463bff3dd4f33c5735b0f2957a351e4f79763a4fa9e775dd237 -> Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24,uint16)   [id,sender,amount0,amount1,sqrtPriceX96,liquidity,tick,fee,protocolFee] — the only Swap topic0 the BSC CLPoolManager emits (7,557 in 2,000 blocks, 2026-10-05)
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

> ✓ = on-chain verified (2026-10). Core addresses are the **same on every Infinity chain**. Infinity is on **BSC, Base and Arc** (not Ethereum/Arbitrum/Robinhood: `eth_getCode` = `0x` on Robinhood, 2026-10).

### BSC (56)
```
0xa0FfB9c1CE1Fe56963B0321B32E7A0302114058b -> CLPoolManager (20885B code ✓; vault()→Vault below ✓)
0x238a358808379702088667322f80aC48bAd5e6c4 -> Vault (8347B ✓; resolved via CLPoolManager.vault() ✓)
0xC697d2898e0D09264376196696c51D7aBbbAA4a9 -> BinPoolManager (23821B ✓; vault()→Vault ✓)
0x55f4c8abA71A1e923edC303eb4fEfF14608cC226 -> CLPositionManager (24004B ✓; clPoolManager()→CLPoolManager ✓)
0x3D311D6283Dd8aB90bb0031835C8e606349e2850 -> BinPositionManager (17435B ✓; binPoolManager()→BinPoolManager ✓)
0xd9C500DfF816a1Da21A48A732d3498Bf09dC9AEB -> Universal Router 2 (24350B ✓; also routes Infinity)
```

### Base (8453)
```
0xa0FfB9c1CE1Fe56963B0321B32E7A0302114058b -> CLPoolManager (20885B ✓)
0x238a358808379702088667322f80aC48bAd5e6c4 -> Vault (8347B ✓)
0xC697d2898e0D09264376196696c51D7aBbbAA4a9 -> BinPoolManager (23821B ✓; vault()→Vault ✓)
0x55f4c8abA71A1e923edC303eb4fEfF14608cC226 -> CLPositionManager (24004B ✓)
0x3D311D6283Dd8aB90bb0031835C8e606349e2850 -> BinPositionManager (17435B ✓)
0xd9C500DfF816a1Da21A48A732d3498Bf09dC9AEB -> Universal Router 2 (24350B ✓)
```

### Arc (5042)
```
0xa0FfB9c1CE1Fe56963B0321B32E7A0302114058b -> CLPoolManager (20885B ✓, bytecode identical to BSC; vault()→Vault ✓; 64 Swap 0x04206ad2… logs in ~28h, 2026-10-05)
0x238a358808379702088667322f80aC48bAd5e6c4 -> Vault (9260B ✓ — a different build from the 8347B BSC/Base Vault; Arc gas is native USDC)
0x55f4c8abA71A1e923edC303eb4fEfF14608cC226 -> CLPositionManager (24004B ✓; vault()→Vault ✓)
0xd9C500DfF816a1Da21A48A732d3498Bf09dC9AEB -> Universal Router 2 (23542B ✓)
# BinPoolManager 0xC697d289… / BinPositionManager 0x3D311D62… : eth_getCode = 0x on Arc (CL only). V2/V3/SmartRouter: also 0x on Arc.
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
4. CL `Swap` amounts are **`int128`** and it carries `fee` (uint24, LP+protocol) + `protocolFee` (**uint16**) inline. The `int256`/`uint24,uint24` form (`0x616cf9d5…`) is never emitted — a monitor on it misses every Infinity CL swap.

---

## Verification & sources
- CL topic0s: `keccak256(sig)` from `pancakeswap/infinity-core` `src/pool-cl/interfaces/ICLPoolManager.sol`; Swap/ModifyLiquidity/Initialize matched against live BSC `eth_getLogs` (2026-10).
- Addresses: `eth_getCode` + `vault()`/`clPoolManager()`/`binPoolManager()` getters on BSC, Base and Arc (2026-10). Bin-pool event topic0s are **NOT verified** — compute from `BinPoolManager.sol` before relying on them.
- Source: [`pancakeswap/infinity-core`](https://github.com/pancakeswap/infinity-core) · [`pancakeswap/infinity-periphery`](https://github.com/pancakeswap/infinity-periphery) · dev docs `/contracts/infinity/resources/addresses` (Cloudflare-gated).
