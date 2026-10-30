# Metric — reference index (Metric.exchange + Metric V1)

**Verified 2026-06-05** against Ethereum mainnet RPC + Blockscout + the live `metric.exchange` site. Re-checked on 2026-10-30: added [`v1.md`](v1.md) for the unrelated **Metric (metric.xyz) V1** oracle-guided AMM, live on 7 chains including Robinhood Chain.

> **Two different protocols share the name "Metric".** `core.md` and `founder-fleet.md` cover **Metric.exchange** (the 2021 METRIC token front-end, Ethereum-only). `v1.md` covers **Metric (metric.xyz)**, a 2026 oracle-guided DEX (`MetricOmmPoolFactory` `0x2a53…8f32`). No on-chain link between them was found. Pick the file by the address you see.

Metric.exchange does **not** map to a `v{n}.md` versioned protocol — it is a **front-end** (gas-less limit orders) with exactly **one** proprietary on-chain contract (the METRIC token). So this folder uses two purpose files plus this index:

| File | Contents |
|------|----------|
| [`core.md`](core.md) | **The Metric protocol proper.** The verified **METRIC** ERC-20 (topics, selectors, governance/mint surface), the external **0x Protocol + KeeperDAO** settlement layer Metric runs on, the **Ethereum-only / not-a-DODO-fork** facts, detection invariants, quick-copy constants. |
| [`v1.md`](v1.md) | **Metric (metric.xyz) V1** — a separate, 2026 oracle-guided AMM ("Active Pools"). `MetricOmmPoolFactory` (current, 2026-09-15) and the retired factory (2026-09-22), pool / factory / router topics and selectors, periphery, extensions, oracle layer. Same address on ETH, Base, BNB, Avax, Arb, Polygon and Robinhood Chain; not on OP or Arc. |
| [`founder-fleet.md`](founder-fleet.md) | **Exhaustive catalog** of the **306 contracts** deployed by Metric's founder EOAs (0xdev0): **Wild Credit** (isolated-pair lending + Uniswap-V3-position collateral, veWILD/xWILD), **UpDown.finance** (binary up/down options), a **Basis Gold** seigniorage fork, vaults, timelocks, test tokens. 60 event topics + ~648 selectors reverse-engineered from bytecode + live logs, keccak-confirmed. All unverified, all Ethereum-only. Includes the full 306-address appendix. |

## TL;DR (read this before monitoring anything "Metric")

1. **Metric.exchange = the METRIC token only.** 1,000,000 / 18 dec / verified solc 0.5.17. Deployed mintable but **`governance()` is renounced to `0x0`**, so `mint`/`setGovernance` are permanently bricked → **supply is frozen at 1,000,000**. Address `0xefc1c73a3d8728dc4cf2a18ac5705fe93e5914ac`.
2. **Metric.exchange is a front-end, not a protocol.** "Powered by 0x protocol & KeeperDAO" — order settlement is **0x**, gas-less relay is **KeeperDAO/Rook**. No Metric AMM/pool/router/settlement contract exists. **Not a DODO fork.**
3. **Metric.exchange is Ethereum-only.** Nothing on Base / BNB / Avalanche / Arbitrum / Optimism / Polygon (token bytecode `0x`; founder EOAs have zero contract creations on those chains).
4. **The founder (0xdev0) also built Wild Credit, UpDown.finance and a Basis Gold fork** from the same wallet (306 contracts). These are *separate protocols*, catalogued in `founder-fleet.md` — **do not attribute them to "Metric."**

## Chain coverage

| Chain | ID | METRIC token | Founder fleet | Notes |
|-------|----|-------------|---------------|-------|
| Ethereum | 1 | ✅ `0xefc1…14ac` | ✅ 306 contracts | the entire Metric / 0xdev0 footprint |
| Base / BNB / Avalanche / Arbitrum / Optimism / Polygon | 8453/56/43114/42161/10/137 | ❌ (`0x`) | ❌ (no creations) | not deployed; founder swaps route via 1inch only |
| Robinhood Chain / Arc | 4663/5042 | ❌ (`0x`) | ❌ | not deployed |

Metric (metric.xyz) V1 coverage is separate: ETH, Base, BNB, Avax, Arb, Polygon, Robinhood Chain — see [`v1.md`](v1.md) §4.
