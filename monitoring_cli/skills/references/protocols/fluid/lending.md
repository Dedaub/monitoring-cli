# Fluid — Lending (fTokens) — Compressed Reference (Ethereum, Arbitrum, Base, Polygon)

**Status:** topic0 via `cast keccak` (verified); Ethereum LendingFactory on-chain re-verified with `cast` vs `publicnode` (2026-05).
**Scope:** Fluid **Lending** — passive supply via **fTokens** (ERC-4626 vaults; e.g. fUSDC, fUSDT, fWETH). fTokens deposit user funds into the [`liquidity-layer.md`](liquidity-layer.md) and accrue lending yield. Other modules: [`vaults.md`](vaults.md), [`dex.md`](dex.md). FLUID/token: [`liquidity-layer.md`](liquidity-layer.md).
**Key fact:** an fToken is a standard **ERC-4626** wrapper over a Liquidity-Layer supply position → it emits the standard ERC-4626 `Deposit`/`Withdraw`, and each is mirrored by a Liquidity-Layer `LogOperate` in the same tx. fTokens are deployed by the **LendingFactory**.

---

## Topics (chain-agnostic) — `topic0 -> Event(types)`
```
0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7 -> Deposit(address,address,uint256,uint256)            # ERC-4626: sender,owner,assets,shares
0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db -> Withdraw(address,address,address,uint256,uint256)   # ERC-4626: sender,receiver,owner,assets,shares
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef -> Transfer(address,address,uint256)                   # fToken share ERC-20
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925 -> Approval(address,address,uint256)
# LendingFactory emits a token-created event (LogTokenCreated / similar) on fToken deployment — confirm exact name/types vs source before use.
```

> The ERC-4626 `Deposit`/`Withdraw` topic0s above are the **standard** ones — shared by every ERC-4626 vault (Fluid fTokens, Morpho MetaMorpho, Yearn v3, etc.). Disambiguate Fluid fTokens by the contract address (an fToken deployed by the Fluid LendingFactory).

---

## Function signatures (ERC-4626 standard)
```
0x6e553f65 -> deposit(uint256 assets,address receiver) -> uint256 shares
0xb460af94 -> withdraw(uint256 assets,address receiver,address owner) -> uint256 shares
0xba087652 -> redeem(uint256 shares,address receiver,address owner) -> uint256 assets
0x07a2d13a -> convertToAssets(uint256) -> uint256   ;   0xc6e6f592 -> convertToShares(uint256) -> uint256
```

---

## Addresses (network-specific)

> Per-chain-specific (NOT deterministic) — L2 from Fluid docs + verify on-chain. ✓ = verified this run.

### Ethereum (1)
```
0x54B91A0D94cb471F37f949c60F7Fa7935b551D03 -> LendingFactory (8305B ✓) — deploys fTokens
# Individual fTokens (fUSDC/fUSDT/fWETH/...): enumerate via the LendingFactory / FluidLendingResolver, or read each fToken's symbol() ("fUSDC" etc.).
```

### Arbitrum / Base / Polygon
LendingFactory + individual fToken addresses are per-chain — pull from the Fluid docs contract-addresses page and verify (`cast code` + `symbol()`/`asset()`). The Liquidity proxy fTokens supply into is in [`liquidity-layer.md`](liquidity-layer.md).

---

## Proxies
- fTokens are deployed by the **LendingFactory**; the LendingFactory and the rewards logic follow Fluid's module pattern. fToken share logic is ERC-4626. Confirm upgradeability per contract on-chain.

---

## Detection invariants & gotchas
1. **fToken `Deposit`/`Withdraw` use the standard ERC-4626 topic0s** — not Fluid-specific. Identify a Fluid fToken by address (LendingFactory-deployed) or `symbol()` ("f"-prefixed).
2. **Each fToken deposit/withdraw is mirrored by a Liquidity-Layer `LogOperate`** in the same tx (the fToken supplying/withdrawing into the shared Liquidity Layer). See [`liquidity-layer.md`](liquidity-layer.md).
3. fTokens accrue yield via the Liquidity Layer's exchange price (no rebasing of shares) — `convertToAssets` reflects accrued interest.

---

## Verification & sources
- topic0: `cast keccak` — ERC-4626 `Deposit`/`Withdraw` are the standard signatures (confirmed). The LendingFactory token-created event wasn't read from source this run — marked to confirm.
- Addresses: Ethereum LendingFactory verified on-chain (8305B). L2 + individual fTokens not enumerated here.
- Source: [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) (`contracts/protocols/lending`) · Fluid docs (FluidLendingResolver).
