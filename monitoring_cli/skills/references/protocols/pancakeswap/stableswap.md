# PancakeSwap StableSwap — Compressed Reference (BSC, Arbitrum)

**Status:** PARTIAL — event shapes inferred from the Curve-StableSwap lineage and marked for confirmation; addresses not on-chain-verified this run (lower priority than V2/V3). Confirm against a deployed Pancake StableSwap pool / the dev docs before relying on specifics.
**Scope:** PancakeSwap **StableSwap** — Curve-style stable pools (2-pool / 3-pool), primarily on **BSC** (+ some on **Arbitrum**). Other versions: [`v2.md`](v2.md), [`v3.md`](v3.md), [`infinity.md`](infinity.md). Shared CAKE/MasterChef/SmartRouter (StableSwap is routed by SmartRouter): [`v2.md`](v2.md).
**Key fact:** Pancake StableSwap is a **Solidity port of Curve StableSwap**. Its pools use **`uint256` coin indices** (so the `TokenExchange` topic0 matches Curve's crypto/old-tricrypto form, not the `int128` StableSwap form). See `dexes/curve.md` for the full Curve event family.

---

## Topics (chain-agnostic) — Curve-StableSwap-fork shape (CONFIRM vs deployed pool)
```
0xb2e76ae99761dc136e598d4a629bb347eccb9532a5f8bbd72e18467c3c34cc98 -> TokenExchange(address,uint256,uint256,uint256,uint256)   [buyer,sold_id,tokens_sold,bought_id,tokens_bought — uint256 ids; same topic0 as Curve crypto]
# AddLiquidity / RemoveLiquidity / RemoveLiquidityImbalance / RemoveLiquidityOne / RampA / StopRampA / NewFee:
# Pancake's port mirrors Curve StableSwap — see dexes/curve.md §1.1 for the per-N-coin AddLiquidity/RemoveLiquidity topic0s.
# These are UNVERIFIED against Pancake's deployed bytecode (the array widths / field order may differ from Curve's). Confirm before use.
```

---

## Function signatures (chain-agnostic) — Curve-StableSwap-fork shape (CONFIRM)
```
0x5b41b908 -> exchange(uint256,uint256,uint256,uint256) -> uint256    [uint256 i,j — like Curve crypto, not int128]
# add_liquidity(uint256[N],uint256), remove_liquidity(uint256,uint256[N]), get_dy(uint256,uint256,uint256) — confirm arities vs deployed pool
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
- This doc is intentionally PARTIAL/flagged: the StableSwap event topic0s beyond `TokenExchange` and the addresses were **not** verified this run. The `uint256`-id `TokenExchange` topic0 (`0xb2e76ae9…`) is shared with Curve's crypto pools (verified in `dexes/curve.md`).
- To complete: read `pancakeswap/pancake-smart-contracts` StableSwap pool source for exact event arities, then `cast keccak` each; verify factory + pool addresses on BscScan / `cast`.
- Source: [`pancakeswap/pancake-smart-contracts`](https://github.com/pancakeswap/pancake-smart-contracts) (stableswap project) · `dexes/curve.md` for the Curve event family.
