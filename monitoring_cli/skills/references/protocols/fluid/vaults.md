# Fluid — Vault Protocol (borrowing / liquidations) — Compressed Reference (Ethereum, Arbitrum, Base, Polygon)

**Status:** topic0 via `cast keccak` (verified, from `Instadapp/fluid-contracts-public` Vault T1 source); Ethereum VaultFactory on-chain re-verified with `cast` vs `publicnode` (2026-05).
**Scope:** Fluid **Vault Protocol** — overcollateralized borrowing. Positions are **ERC-721 NFTs** minted by the VaultFactory; each vault is a market (collateral↔debt). Other modules: [`liquidity-layer.md`](liquidity-layer.md) (core; vault balances settle there), [`lending.md`](lending.md), [`dex.md`](dex.md). FLUID/token: [`liquidity-layer.md`](liquidity-layer.md).
**Key fact:** vaults draw/repay liquidity from the Liquidity Layer, so vault `LogOperate`/`LogLiquidate` events are accompanied by a Liquidity-Layer `LogOperate` in the same tx. **`LogLiquidate` is the key security/risk-alert event.** Vault types: **T1** (normal col↔debt), **T2** (smart collateral = DEX LP as collateral), **T3** (smart debt), **T4** (smart col + smart debt) — events below are the T1 core; T2–T4 extend them.

---

## Topics (chain-agnostic) — `topic0 -> Event(types)` (Vault T1 core)
```
0xfef64760e30a41b9d5ba7dd65ff7236a61d89ed8b44c67a29e84db1a67513a1c -> LogOperate(address,uint256,int256,int256,address)
   # user, nftId, newCol (signed), newDebt (signed), to — open/adjust a position
0x80fd9cc6b1821f4a510e45ffce6852ea3404807b5d3d833ffa85664408afcb66 -> LogLiquidate(address,uint256,uint256,address)
   # liquidator, colAmt, debtAmt, to — ** key liquidation/risk event **
0x115609402b8e0707cb9654c5da38e5c0790ccad443a92f71160fe645aa342d04 -> LogAbsorb(uint256,uint256)              # bad-debt absorption (colAbsorbed, debtAbsorbed)
0x9a85dfb89c634cdc63db5d8cedaf8f9cfa4926df888bad563d70b7314a33a0ae -> LogRebalance(int256,int256)             # rebalance col/debt vs Liquidity Layer
0xcde545703e0372175cadfff811d67c32910c3dcb33199679b3271c4106afdf9a -> LogUpdateExchangePrice(uint256,uint256)
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef -> Transfer(address,address,uint256)       # VaultFactory ERC-721 position NFT (tokenId = nftId)
```

---

## Function signatures
```
# Vault.operate(uint256 nftId, int256 newCol, int256 newDebt, address to) -> (uint256,int256,int256)   — open(nftId=0)/adjust/close a position
# Vault.liquidate(uint256 debtAmt, uint256 colPerUnitDebt, address to, bool absorb) -> (...)
# VaultFactory: totalVaults() -> uint256 ; name() -> "Fluid Vault" (ERC-721)
```

---

## Addresses (network-specific)

> Per-chain-specific (NOT deterministic) — L2 addresses from Fluid docs + verify on-chain. ✓ = verified this run.

### Ethereum (1)
```
0x324c5Dc1fC42c7a4D43d92df1eBA58a54d13Bf2d -> VaultFactory (name "Fluid Vault" ✓; totalVaults 169 ✓) — ERC-721; deploys vaults + mints position NFTs
# Individual vault (market) addresses: enumerate via VaultFactory (LogVaultDeployed) / FluidVaultResolver.
```

### Arbitrum / Base / Polygon
VaultFactory + individual vault addresses are per-chain — pull from the Fluid docs contract-addresses page and verify (`cast code` + `totalVaults()`). Liquidity proxy (where vault balances settle) per chain: see [`liquidity-layer.md`](liquidity-layer.md).

---

## Proxies
- Vaults are deployed by the **VaultFactory** (which is also the ERC-721 position-NFT contract). Individual vaults use the Fluid module/proxy pattern (a vault dispatches to admin/secondary implementation modules). Treat vault logic as upgradeable-by-governance per the Fluid module system — confirm on-chain. The position NFT lives on the factory, not per-vault.
- Liquidity-Layer Infinite Proxy: see [`liquidity-layer.md`](liquidity-layer.md).

---

## Detection invariants & gotchas
1. **`LogLiquidate` (`0x80fd9cc6…`) is the priority risk alert** — a liquidation on a Fluid vault. Pair with the vault address + the position `nftId` (from the surrounding `LogOperate`/Transfer) to identify the liquidated position.
2. **Positions are NFTs** — a position is identified by `nftId` (the ERC-721 tokenId minted by the VaultFactory), not an EOA. Transfer of the NFT transfers the debt position.
3. **Every vault op also emits a Liquidity-Layer `LogOperate`** in the same tx (the vault moving col/debt in the shared Liquidity Layer). Correlate by tx hash; the vault event has the user/nftId, the Liquidity event has the token + signed amounts. See [`liquidity-layer.md`](liquidity-layer.md).
4. **`LogAbsorb` = bad-debt socialization** — worth alerting (protocol absorbing underwater debt).
5. **T2/T3/T4 vaults integrate the DEX** (smart collateral / smart debt = a DEX LP position used as col/debt). Those vaults also emit DEX events ([`dex.md`](dex.md)) — a single user action can touch Vault + DEX + Liquidity Layer.

---

## Verification & sources
- topic0: `cast keccak` from `Instadapp/fluid-contracts-public` `contracts/protocols/vault/vaultT1/coreModule/events.sol` (events read verbatim). T1 core; T2–T4 extend.
- Addresses: Ethereum VaultFactory verified on-chain (`name()`="Fluid Vault", `totalVaults()`=169). L2 not verified here.
- Source: [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) · Fluid docs (FluidVaultResolver for live vault enumeration).
