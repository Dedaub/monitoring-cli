# QuickSwap — Reference Index

QuickSwap is a Polygon-origin DEX whose "versions" are **three different AMM engines**, not a linear version bump. One file per engine:

| File | Engine | Chains (of the 7 requested) | Identity markers |
|------|--------|------------------------------|------------------|
| [`v2.md`](v2.md) | **Uniswap V2 fork** (classic constant-product AMM) | Polygon PoS, Base | init hash == Uniswap `0x96e8ac42…`; LP `symbol()="UNI-V2"` |
| [`v3.md`](v3.md) | **Algebra V1** (dynamic-fee concentrated liquidity) | Polygon PoS only | factory `Pool(token0,token1,pool)` (no fee), `Fee(uint16)` event, NFPM "Algebra Positions NFT-V1" / `ALGB-POS`, init hash `0x6ec6c9c8…` |
| [`v4.md`](v4.md) | **Algebra Integral** (plugin-based concentrated liquidity) | Base only | Swap `0x121cb44e…` (+overrideFee/+pluginFee), NFPM "Algebra Positions NFT-V2" / `ALGB-POS`, per-deployment init hash (Base `0xa18736c3…`) |

**Cross-cutting facts**
- **Among the 7 requested chains** (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon PoS), QuickSwap AMMs exist **only on Polygon PoS (V2+V3) and Base (V2+V4)**. NOT on Ethereum, BNB, Avalanche, Arbitrum, Optimism (factory `eth_getCode = 0x`). Ethereum L1 = Orbs Liquidity-Hub aggregator + QuickPerps perps (non-AMM).
- **Shared governance key `0xa08dac76e6b8f940895d71e0ddef56964bbfe153`** is the V2 `feeToSetter` (Polygon+Base) and the Algebra V3/V4 factory `owner()` — one admin across all versions/chains.
- **Topic-collision trap:** Algebra V1 (V3) Swap/Mint/Burn/Collect/Initialize topic0s coincide with Uniswap V3. Algebra Integral (V4) on Base **does not** (its Swap/Burn carry plugin fees → unique topics). Always condition on `(chainId, factory/pool address)`.
- Beyond these 7 chains QuickSwap also runs on Polygon zkEVM, Dogechain, Manta, Astar zkEVM, Immutable zkEVM, X Layer, Soneium, Somnia, Mantra (out of scope here).

All addresses + topic0/selectors verified on-chain (publicnode RPC, keccak via pycryptodome) on 2026-06-05; init code hashes CREATE2-round-trip-verified. See each file's "Verification & sources" section.
