# Fluid — DEX (smart collateral / smart debt AMM) — Compressed Reference (Ethereum, Base, Arbitrum, Polygon, BNB Chain)

**Status:** topic0 via `cast keccak` (verified, from `Instadapp/fluid-contracts-public` DEX poolT1 source); Ethereum DexFactory on-chain re-verified with `cast` vs `publicnode` (2026-05).
**Scope:** Fluid **DEX** — an AMM whose liquidity IS the [`liquidity-layer.md`](liquidity-layer.md) (so the same capital can be lending collateral AND DEX liquidity — "smart collateral / smart debt"). Other modules: [`vaults.md`](vaults.md), [`lending.md`](lending.md). FLUID/token: [`liquidity-layer.md`](liquidity-layer.md).
**Key fact:** Fluid DEX is deployed on **Ethereum, Base, Arbitrum, Polygon, and BNB Chain** (the same DexFactory `0x91716C4EDA1Fb55e84Bf8b4c7085f84285c19085` is live on all five — verified on-chain 2026-06; `deployments.md` also lists Plasma). Pools are created by the **DexFactory**. This doc covers **DEX V1 (poolT1)**; Fluid also has **DEX V2** and **DEX Lite** (newer, separate contracts with different events) — confirm those from the docs if needed. DEX liquidity changes also surface as Liquidity-Layer `LogOperate` (same tx).

---

## Topics (chain-agnostic) — `topic0 -> Event(types)` (DEX V1 / poolT1)
```
0xdc004dbca4ef9c966218431ee5d9133d337ad018dd5b5c5493722803f75c64f7 -> Swap(bool,uint256,uint256,address)        # swap0to1, amountIn, amountOut, to  ** workhorse swap event **
0x255672effa3d8ba46e409fc964ae332b84d3107ba3a5096b22734606519528a3 -> LogDepositPerfectColLiquidity(uint256,uint256,uint256)
0x6f837572c1ef6e010a841ff938d593ec054984fefe29df2a0634bbf01f4db35b -> LogWithdrawPerfectColLiquidity(uint256,uint256,uint256)
0x486d991947a88580130ff5acd9ec54dc37fb8da4bf6ab78871d5cd6fa5816df7 -> LogBorrowPerfectDebtLiquidity(uint256,uint256,uint256)
0x03b77b44c2fe8816d55a2e4f90a87538c48d4148e35224c07049fd2304fa3a30 -> LogPaybackPerfectDebtLiquidity(uint256,uint256,uint256)
0xbfea92097a2487d6a5ccf7b7adc36b6002238f3106568ba4359770f4b67365a4 -> LogDepositColLiquidity(uint256,uint256,uint256)
0xb61c7f3b23fe9335cc6c6a6e7036457758470877e61a19a5b4924e1ff8289624 -> LogWithdrawColLiquidity(uint256,uint256,uint256)
0x7f81427bed699dc7e687c5ddae6061932938818f79fc0e68903d55ef75ca4561 -> LogBorrowDebtLiquidity(uint256,uint256,uint256)
0xb69f152a70520703fe7ab4872a0cb3928386b68cf3c6c83c5d1fc08d196991e8 -> LogPaybackDebtLiquidity(uint256,uint256,uint256)
0xc98f37914e06db36c18654484db85c4bb864575a1b9f8181133ff33dea2d34f3 -> LogWithdrawColInOneToken(uint256,uint256,uint256)
0x97dfa84cbffcf65b8d034f057439472bc93868a66cc0e728c2faffb00f8b4923 -> LogPaybackDebtInOneToken(uint256,uint256,uint256)
0x063def03d41a2957d43156b97c271f3e4adea600722defb2cf6ebf9a27650056 -> LogArbitrage(int256,uint256)
```

---

## Function signatures
```
# swapIn(bool swap0to1, uint256 amountIn, uint256 amountOutMin, address to) -> uint256 amountOut
# swapOut(bool swap0to1, uint256 amountOut, uint256 amountInMax, address to) -> uint256 amountIn
# deposit/withdraw/borrow/payback perfect + single-sided variants (mirror the Log* events above)
# DexFactory: totalDexes() -> uint256
```

---

## Addresses (network-specific)

> Per-chain-specific — L2 from Fluid docs + verify on-chain. The DexFactory itself is CREATE2-deterministic (same address on every chain); individual pool addresses are not. DEX is live on Ethereum, Base, Arbitrum, Polygon, and BNB Chain. ✓ = verified this run.

### Ethereum (1)
```
0x91716C4EDA1Fb55e84Bf8b4c7085f84285c19085 -> DexFactory (totalDexes 45 ✓) — deploys Fluid DEX pools
# Individual DEX pool (poolT1) addresses: enumerate via DexFactory (LogDexDeployed) / FluidDexResolver.
```

### Base (8453) / Arbitrum (42161) / Polygon (137) / BNB Chain (56)
The DexFactory is deployed at the **same CREATE2-deterministic address `0x91716C4EDA1Fb55e84Bf8b4c7085f84285c19085`** on every chain (bytecode byte-identical to Ethereum). `totalDexes()` per chain (verified on-chain 2026-06): Base 18 ✓, Arbitrum 20 ✓, Polygon 8 ✓, BNB Chain 5 ✓. Individual pool addresses are per-chain — enumerate via `LogDexDeployed` / FluidDexResolver + verify (`cast code` + `totalDexes()`). The Liquidity proxy the DEX shares liquidity with: see [`liquidity-layer.md`](liquidity-layer.md).

---

## Proxies
- DEX pools are deployed by the **DexFactory** (Fluid module pattern). A Fluid DEX pool does NOT custody its own reserves — liquidity is held in the Liquidity Layer, so a swap moves balances there (also visible as Liquidity `LogOperate`). Confirm pool upgradeability on-chain.

---

## Detection invariants & gotchas
1. **`Swap(bool,uint256,uint256,address)` (`0xdc004dbc…`) is the workhorse** — `swap0to1` (bool) gives direction, then `amountIn`, `amountOut`, `to`. Note this is a Fluid-specific signature (NOT the Uniswap/Velodrome Swap layouts).
2. **DEX liquidity ops mirror into the Liquidity Layer.** A Fluid DEX deposit/borrow also emits a Liquidity-Layer `LogOperate` (same tx) — correlate by tx. See [`liquidity-layer.md`](liquidity-layer.md).
3. **Smart collateral / smart debt:** the same capital can be a Vault's collateral/debt AND DEX liquidity (T2/T3/T4 vaults — see [`vaults.md`](vaults.md)). A single user action can emit Vault + DEX + Liquidity events together.
4. **DEX V1 vs V2 vs Lite:** this doc is DEX V1 (poolT1). V2 and Lite are separate contracts with different event sets — do not assume these topic0s apply to them.

---

## Verification & sources
- topic0: `cast keccak` from `Instadapp/fluid-contracts-public` `contracts/protocols/dex/poolT1/coreModule/events.sol` (all 12 events read verbatim).
- Addresses: DexFactory (CREATE2-deterministic, same address on all chains) verified on-chain via `totalDexes()` — Ethereum 45, Base 18, Arbitrum 20, Polygon 8, BNB Chain 5. Individual pools not enumerated here. `deployments.md` also lists the factory on Plasma.
- Source: [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) · Fluid docs (FluidDexResolver; DEX V2 / DEX Lite integration pages).
