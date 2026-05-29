# Fluid — Liquidity Layer (core) — Compressed Reference (Ethereum, Arbitrum, Base, Polygon)

**Status:** topic0 via `cast keccak` (verified, from `Instadapp/fluid-contracts-public` source); Ethereum addresses on-chain re-verified with `cast` vs `publicnode` (2026-05).
**Scope:** Fluid's **Liquidity Layer** — the single contract that custodies ALL protocol liquidity and through which every supply/borrow/withdraw/payback (from Vaults, Lending, and the DEX) settles. Plus the **FLUID** governance token. This is the **base file** the other Fluid modules reference: [`vaults.md`](vaults.md), [`lending.md`](lending.md), [`dex.md`](dex.md).
**Key fact:** like Balancer's Vault, Fluid is **Liquidity-Layer-centric** — monitor the one Liquidity proxy per chain and its `LogOperate` event to capture nearly all balance changes across the whole protocol. Fluid is on **Ethereum, Arbitrum, Base, Polygon** (Liquidity/Lending/Vaults on all four; DEX on ETH/Arbitrum/Polygon — see [`dex.md`](dex.md)).

---

## Topics (chain-agnostic) — `topic0 -> Event(types)`
```
0x4d93b232a24e82b284ced7461bf4deacffe66759d5c24513e6f29e571ad78d15 -> LogOperate(address,address,int256,int256,address,address,uint256,uint256)
   # user, token, supplyAmount, borrowAmount, withdrawTo, borrowTo, totalAmounts, exchangePricesAndConfig
   # supplyAmount/borrowAmount are SIGNED: +supply / -withdraw, +borrow / -payback. Emitted by the Liquidity proxy for EVERY protocol that uses it.
```
Admin/config events (`LogUpdateExchangePrices`, user-supply/borrow-config updates, etc.) are declared in the Liquidity **adminModule** (separate file) — not enumerated here.

---

## Function signatures
```
# operate(address token, int256 supplyAmount, int256 borrowAmount, address withdrawTo, address borrowTo, bytes callbackData) -> (uint256,uint256)
#   — the single core entrypoint; callable only by authorized protocols (vaults/fTokens/dex), not end users directly.
# Reads go through periphery Resolver contracts (FluidLiquidityResolver), not the core.
```

---

## Addresses (network-specific)

> Fluid contract addresses are **per-chain-specific (NOT deterministic)** — get the L2 addresses from the Fluid docs (`docs.fluid.instadapp.io/contracts/contract-addresses`) and verify on-chain. ✓ = on-chain verified this run.

### Ethereum (1)
```
0x52Aa899454998Be5b000Ad077a46Bbe360F4e497 -> Liquidity (Infinite-proxy; 4462B ✓) — the core liquidity contract
0x6f40d4A6237C257fff2dB00FA0510DeEECd303eb -> FLUID token (symbol "FLUID" ✓)
```

### FLUID token (other chains)
```
0x61e030a56d33e8260fdd81f03b162a79fe3449cd -> FLUID — Arbitrum
0xf50d05a1402d0adafa880d36050736f9f6ee7dee -> FLUID — Polygon
# Base: FLUID bridged via Chainlink CCIP — confirm address on docs/explorer.
```

### Liquidity proxy on Arbitrum / Base / Polygon
Per-chain-specific addresses — **pull from the Fluid docs contract-addresses page and verify on-chain** (`cast code`). Not hard-coded here to avoid shipping unverified addresses.

---

## Proxies
- **Liquidity is an Instadapp "Infinite Proxy"** — a proxy that dispatches calls to multiple implementation modules (userModule for `operate`, adminModule for config) by function selector. So the Liquidity address has a small proxy bytecode (≈4.5KB) and the real logic lives in implementation contracts it delegatecalls. To resolve implementations, inspect the proxy's `getImplementation(bytes4)` / sigs mapping, not a single EIP-1967 slot.
- See `references/proxies.md` for general proxy detection.

---

## Detection invariants & gotchas
1. **Watch `LogOperate` on the Liquidity proxy = the single highest-signal Fluid event.** Every Vault borrow/repay, fToken deposit/withdraw, and DEX liquidity change ultimately settles as a Liquidity `operate` → one `LogOperate`. This is the Fluid analogue of "watch the Balancer Vault."
2. **`supplyAmount` / `borrowAmount` are signed `int256`:** positive = supply added / borrow taken; negative = withdraw / payback. Sign disambiguates the action.
3. The `token` field is the underlying asset; `user` is the protocol contract (vault/fToken/dex) acting on behalf of the end user — to attribute to the end user, correlate with the per-protocol event ([`vaults.md`](vaults.md) / [`lending.md`](lending.md) / [`dex.md`](dex.md)) in the same tx.
4. `totalAmounts` and `exchangePricesAndConfig` are bit-packed (supply/borrow totals + rate config) — decode per the Fluid `BigMath`/packing layout if you need amounts in token units.
5. Bytea hex literals: 40 chars for addresses, 64 for topics.

---

## Verification & sources
- topic0: `cast keccak` from `Instadapp/fluid-contracts-public` `contracts/liquidity/userModule/events.sol` (`LogOperate` read verbatim).
- Addresses: Ethereum Liquidity proxy (4462B) + FLUID `symbol()`="FLUID" verified on-chain via `cast` vs `publicnode`; VaultFactory/DexFactory/LendingFactory verified in [`vaults.md`](vaults.md)/[`dex.md`](dex.md)/[`lending.md`](lending.md). L2 Liquidity/factory addresses are per-chain and NOT verified here — pull from docs.
- Source: [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) · [Fluid docs — contract addresses](https://docs.fluid.instadapp.io/contracts/contract-addresses.html).
