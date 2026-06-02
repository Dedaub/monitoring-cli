# PancakeSwap StableSwap — Compressed Reference (BSC, Arbitrum)

**Status:** PARTIAL — the two-coin pool's core event/selector shapes are verified against the deployed `PancakeStableSwapTwoPool` source (topic0s/selectors recomputed via keccak); N>2 pool arities and individual pool addresses are NOT yet enumerated. Confirm those against a deployed Pancake StableSwap pool / the dev docs before relying on specifics.
**Scope:** PancakeSwap **StableSwap** — Curve-style stable pools (2-pool / 3-pool), primarily on **BSC** (+ some on **Arbitrum**). Other versions: [`v2.md`](v2.md), [`v3.md`](v3.md), [`infinity.md`](infinity.md). Shared CAKE/MasterChef/SmartRouter (StableSwap is routed by SmartRouter): [`v2.md`](v2.md).
**Key fact:** Pancake StableSwap is a **Solidity port of Curve StableSwap**. Its pools use **`uint256` coin indices** (so the `TokenExchange` topic0 matches Curve's crypto/old-tricrypto form, not the `int128` StableSwap form). See `dexes/curve.md` for the full Curve event family.

---

## Topics (chain-agnostic) — Curve-StableSwap-fork shape (CONFIRM vs deployed pool)
```
0xb2e76ae99761dc136e598d4a629bb347eccb9532a5f8bbd72e18467c3c34cc98 -> TokenExchange(address,uint256,uint256,uint256,uint256)   [buyer,sold_id,tokens_sold,bought_id,tokens_bought — uint256 ids; same topic0 as Curve crypto]
# Two-coin pool (verified against the deployed PancakeStableSwapTwoPool source):
0x26f55a85081d24974e85c6c00045d0f0453991e95873f52bff0d21af4079a768 -> AddLiquidity(address,uint256[2],uint256[2],uint256,uint256)         [matches Curve 2-coin AddLiquidity]
0x7c363854ccf79623411f8995b362bce5eddff18c927edc6f5dbbb5e05819a82c -> RemoveLiquidity(address,uint256[2],uint256[2],uint256)             [matches Curve 2-coin RemoveLiquidity]
0x5ad056f2e28a8cec232015406b843668c1e36cda598127ec3b8c59b8c72773a0 -> RemoveLiquidityOne(address,uint256,uint256,uint256)                 [NOTE: 4-field form — matches Curve's crypto/old-tricrypto RemoveLiquidityOne, NOT classic StableSwap's 3-field 0x9e96dd3b…]
0xa2b71ec6df949300b59aab36b55e189697b750119dd349fcfa8c0f779e83c254 -> RampA(uint256,uint256,uint256,uint256)                              [classic StableSwap form]
0x46e22fb3709ad289f62ce63d469248536dbc78d82b84a3d7e74ad606dc201938 -> StopRampA(uint256,uint256)                                          [classic StableSwap form]
# RemoveLiquidityImbalance / NewFee: confirm arities against the deployed pool. For N>2 pools the array widths differ — see dexes/curve.md §1.1 for the per-N-coin topic0s.
```

---

## Function signatures (chain-agnostic) — Curve-StableSwap-fork shape (CONFIRM)
```
0x5b41b908 -> exchange(uint256,uint256,uint256,uint256) -> uint256    [uint256 i,j — like Curve crypto, not int128]
0x556d6e9f -> get_dy(uint256,uint256,uint256) -> uint256              [uint256 i,j]
# add_liquidity(uint256[N],uint256), remove_liquidity(uint256,uint256[N]) — confirm arities vs deployed pool
```

---

## Addresses (network-specific) — NOT verified this run
StableSwap pools/factory live on **BSC** (and some on Arbitrum). The `PancakeStableSwapFactory` / two-pool & three-pool deployers and individual pool addresses are in the PancakeSwap dev docs (`/contracts/stableswap`) and on BscScan (label "PancakeSwap: StableSwap*"). **Enumerate pools via the factory's pool-creation event; verify the factory + a sample pool on-chain (`cast code` + a `coins(0)` call) before wiring into an alert.** Not hard-coded here to avoid shipping unverified addresses.

CAKE / MasterChef / SmartRouter (which routes StableSwap): see [`v2.md`](v2.md).

---

## Proxies
- Pancake StableSwap pools are deployed by a factory/deployer; treat pool logic as immutable per deployment but **confirm the deployment pattern on-chain** (some Pancake periphery uses upgradeable proxies). See `references/proxies.md`.

---

## Verification & sources
- The two-coin pool's event topic0s and function selectors are verified against the deployed `PancakeStableSwapTwoPool` source and recomputed via keccak256. The `uint256`-id `TokenExchange` topic0 (`0xb2e76ae9…`) is shared with Curve's crypto pools (verified in `dexes/curve.md`). Note `RemoveLiquidityOne` here is the 4-field `(address,uint256,uint256,uint256)` form (`0x5ad056f2…`, matching Curve's crypto/old-tricrypto variant), not classic StableSwap's 3-field `0x9e96dd3b…`.
- Pools and the factory are immutable per deployment, not EIP-1967 proxies (the EIP-1967 implementation slot reads `0x0` on the BSC factory and on a sampled LP token).
- Still to complete: read the StableSwap source for N>2 pool event arities and `cast keccak` each; enumerate factory + pool addresses on BscScan / `cast` (BSC is the primary deployment; PancakeSwap also publishes a StableSwap info view for Arbitrum).
- Source: [`pancakeswap/pancake-smart-contracts`](https://github.com/pancakeswap/pancake-smart-contracts) (stableswap project) · `dexes/curve.md` for the Curve event family.
