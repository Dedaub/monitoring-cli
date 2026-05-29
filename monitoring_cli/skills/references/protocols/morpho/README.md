# Morpho — Protocol Reference Index

Monitoring-grade references for Morpho across **Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137)**. Verified against live RPC + canonical `morpho-org/*` repos + `@morpho-org/blue-sdk` on 2026-05-29.

Morpho is **three generations** of protocol, not a single linear `v1→v2→v3`. One file per generation (each covers its sub-components and follows the house shape):

| File | Generation | Components | Status |
|------|-----------|------------|--------|
| [optimizers.md](optimizers.md) | **Gen 1 — Optimizers** | Morpho-AaveV3 (ETH Optimizer), Morpho-Compound, Morpho-AaveV2 — P2P overlay on Aave/Compound | **Deprecated** (MIP-120). Ethereum only. Upgradeable proxies. |
| [v1.md](v1.md) | **Gen 2 — Morpho V1** | **Morpho Blue** (immutable singleton lending primitive, "Markets V1") + **MetaMorpho** V1.0/V1.1 (ERC-4626 curated vaults, "Vaults V1") + periphery (AdaptiveCurveIRM, PublicAllocator, oracle factory, pre-liquidation, Bundler3, URD, MORPHO token) | **Live, dominant.** All 7 chains. Immutable. |
| [v2.md](v2.md) | **Gen 3 — Morpho V2** | **Vaults V2** (new protocol-agnostic vault standard + adapters + registry) — *live*; **Markets V2 / "Midnight"** (intent-based fixed-rate/fixed-term primitive) — *whitepaper + codebase open-sourced 2026-05-28, not yet on mainnet* | Vaults V2 live on 6/7 chains (not BNB). Midnight rolling out 2026 (Morpho frames it as a new paradigm, not literally "Blue V2"). |

Each file follows the house shape: **Topics** (chain-agnostic `topic0 = keccak256(event sig)`) → **Function signatures** (chain-agnostic 4-byte selectors) → **Addresses** (network-specific, one section per chain) → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## Cross-cutting facts worth knowing before you start

- **Immutability is the headline.** Morpho Blue, MetaMorpho vaults+factories, and Vaults V2 vaults+factories are **all immutable** — no proxy, no admin upgrade, no pause (verified: EIP-1967 impl slot `0x0` everywhere). The *only* upgradeable Morpho contracts are the legacy **Optimizers** (TransparentUpgradeableProxy, shared ProxyAdmin `0x99917ca0…`) and the **transferable MORPHO token** (`0x58D9…`, impl `0x4364fd23…`). You never re-resolve a Blue/MetaMorpho/VaultV2 implementation.
- **The Morpho Blue singleton address is chain-specific** — unlike Aave/Uniswap there is NO single cross-chain address. Only Ethereum + Base share the vanity `0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb`. Per chain: Polygon `0x1bF0c2…25f67`, Arbitrum `0x6c247b…18F5e`, Optimism `0xce95Af…4AF92`, BNB `0x01b0Bd…7a83a`, Avalanche `0x895383…f982C`. **Always key on `(chainId, address)`.**
- **BNB `0xBBBB…` is a decoy.** The Ethereum/Base vanity address *also* has Morpho-Blue bytecode on BNB but a different owner and is NOT the canonical deployment (the app/SDK use `0x01b0Bd…`). Filtering `0xBBBB…` on BNB misses everything. See [v1.md §3.6](v1.md).
- **Topics + selectors are 100% chain-agnostic.** Every `Supply`/`Borrow`/`Liquidate`/`CreateMarket` topic0 is identical on all 7 chains; only the emitting address changes.
- **Market `Id = keccak256(abi.encode(loanToken, collateralToken, oracle, irm, lltv))`** — a `bytes32`, indexed on nearly every Blue event. Markets are immutable post-creation (no risk-param-change events; only `SetFee` ≤25%).
- **Colliding topic0s across components** (disambiguate by emitter): `Deposit`/ERC-4626-`Withdraw` are shared by MetaMorpho **and** Vaults V2; `SetOwner`/`SetCurator`/`SetIsAllocator` recur across Blue/MetaMorpho/Vaults V2; **`AccrueInterest` has three distinct topics** (Blue 4-field-w/id `0x9d9bd501…`, MetaMorpho 2-field `0xf66f28b4…`, Vaults V2 4-field `0x4dec04e7…`); **`SetFee` has three** (Blue/MetaMorpho/PublicAllocator). The `Supplied`/`Repaid`/`Liquidated` Optimizer topics are shared across all three optimizers.
- **Oracle price scale is `1e36`** (`ORACLE_PRICE_SCALE`); the Chainlink oracle adapter's `SCALE_FACTOR` embeds `36 + loanDecimals − collateralDecimals`. LLTV is `1e18`-scaled and is a *liquidation* threshold, not a max-borrow. Positions are stored in **shares** (VIRTUAL_SHARES `1e6`).
- **Attribution:** the position owner is `onBehalf`, not `tx.from` or the event's `caller` (often Bundler3 or a vault). Authorization (`SetAuthorization`) is **global across all markets**, not per-market.

## Verification methodology

- **Topic0 / selectors:** computed locally with keccak-256 (pycryptodome) from canonical `morpho-org/*` source signatures (`MarketParams`→`(address,address,address,address,uint256)`); validated against live `eth_getLogs` on Ethereum Morpho Blue (`Supply` 14406, `Withdraw` 13982, `Borrow` 1814, `Repay` 1711, `SupplyCollateral` 1777, `Liquidate` 60, `CreateMarket` 16, `AccrueInterest` 28970), the IRM (`BorrowRateUpdate` 29013), oracle factory (`CreateMorphoChainlinkOracleV2` 11), Vaults V2 factory (`CreateVaultV2` 14), and the AaveV3-Optimizer (`Supplied` at block 18.0M). Bundler3 `multicall`/`reenter` selectors confirmed in deployed bytecode.
- **Addresses:** parsed from `@morpho-org/blue-sdk` `packages/blue-sdk/src/addresses.ts` (chainId-keyed `addressesRegistry`) and existence-checked via `eth_getCode` on each chain's publicnode RPC; bytecode sizes are identical per generation (Blue 15623 B ETH/Base vs 15582 B on the 2025 chains). Singleton owners read via `owner()`; immutability confirmed by reading the EIP-1967 slot. Avalanche (absent from that SDK snapshot) taken from `docs.morpho.org` and confirmed on-chain.

## Coverage caveats (read these)

- **Per-market / per-vault addresses are not enumerated** — Morpho is permissionless; markets and vaults number in the thousands. Discover them via factory events: `CreateMarket` (Morpho Blue), `CreateMetaMorpho` (MetaMorpho factories), `CreateVaultV2` (VaultV2Factory), `CreatePreLiquidation`, `UrdCreated`. The docs list per-component singletons/factories, not instances.
- **MORPHO token OFT addresses** vary per chain (LayerZero OFT, MIP-113) and are governance-side, not lending-critical; [v1.md](v1.md) lists Ethereum's full set (legacy/transferable/wrapper/OFT adapter) + Base/Arbitrum, and notes the model.
- **Avalanche** is a newer/partial deployment (not in the SDK snapshot): Blue + IRM + oracle/pre-liquidation factories + Vaults V2 confirmed on-chain; a MetaMorpho V1.1 factory / PublicAllocator / Bundler3 were not confirmed there — verify against live docs before relying on V1-vault tooling on Avalanche.
- **Markets V2 / "Midnight"** has no finalized mainnet addresses yet (phased 2026 rollout) — [v2.md §5](v2.md) is a placeholder to fill in once live.
- **Optimizers** are deprecated (MIP-120) with ~zero new activity; kept for historical position/event decoding only.
