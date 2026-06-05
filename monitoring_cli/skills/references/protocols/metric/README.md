# Metric.exchange (METRIC) — reference index

**Verified 2026-06-05** against Ethereum mainnet RPC + Blockscout + the live `metric.exchange` site.

Metric.exchange does **not** map to a `v{n}.md` versioned protocol — it is a **front-end** (gas-less limit orders) with exactly **one** proprietary on-chain contract (the METRIC token). So this folder uses two purpose files plus this index:

| File | Contents |
|------|----------|
| [`core.md`](core.md) | **The Metric protocol proper.** The verified **METRIC** ERC-20 (topics, selectors, governance/mint surface), the external **0x Protocol + KeeperDAO** settlement layer Metric runs on, the **Ethereum-only / not-a-DODO-fork** facts, detection invariants, quick-copy constants. |
| [`founder-fleet.md`](founder-fleet.md) | **Exhaustive catalog** of the **306 contracts** deployed by Metric's founder EOAs (0xdev0): **Wild Credit** (isolated-pair lending + Uniswap-V3-position collateral, veWILD/xWILD), **UpDown.finance** (binary up/down options), a **Basis Gold** seigniorage fork, vaults, timelocks, test tokens. 60 event topics + ~648 selectors reverse-engineered from bytecode + live logs, keccak-confirmed. All unverified, all Ethereum-only. Includes the full 306-address appendix. |

## TL;DR (read this before monitoring anything "Metric")

1. **Metric = the METRIC token only.** 1,000,000 / 18 dec / verified solc 0.5.17. Deployed mintable but **`governance()` is renounced to `0x0`**, so `mint`/`setGovernance` are permanently bricked → **supply is frozen at 1,000,000**. Address `0xefc1c73a3d8728dc4cf2a18ac5705fe93e5914ac`.
2. **Metric is a front-end, not a protocol.** "Powered by 0x protocol & KeeperDAO" — order settlement is **0x**, gas-less relay is **KeeperDAO/Rook**. No Metric AMM/pool/router/settlement contract exists. **Not a DODO fork.**
3. **Ethereum-only.** Nothing on Base / BNB / Avalanche / Arbitrum / Optimism / Polygon (token bytecode `0x`; founder EOAs have zero contract creations on those chains).
4. **The founder (0xdev0) also built Wild Credit, UpDown.finance and a Basis Gold fork** from the same wallet (306 contracts). These are *separate protocols*, catalogued in `founder-fleet.md` — **do not attribute them to "Metric."**

## Chain coverage

| Chain | ID | METRIC token | Founder fleet | Notes |
|-------|----|-------------|---------------|-------|
| Ethereum | 1 | ✅ `0xefc1…14ac` | ✅ 306 contracts | the entire Metric / 0xdev0 footprint |
| Base / BNB / Avalanche / Arbitrum / Optimism / Polygon | 8453/56/43114/42161/10/137 | ❌ (`0x`) | ❌ (no creations) | not deployed; founder swaps route via 1inch only |
