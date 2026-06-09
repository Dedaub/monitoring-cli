# Orbiter Finance — reference index

Cross-rollup bridge with an **optimistic / off-chain-relayer** design. Two clearly separate on-chain generations/product lines, one file each.

| File | Component / generation | Status | Chains present (of the 7 targets) |
|------|------------------------|--------|-----------------------------------|
| [core.md](./core.md) | **Live bridge surface** — `OrbiterXRouter` ("RouterV3") multicall transfer wrapper, legacy `OBSource` router, `OPool` maker-liquidity pool, and the **Maker EOAs** that actually move funds. This carries the volume. | Live, immutable (no proxies) | Router: **ETH, ARB, OP, POLY, BNB, Base** (NOT Avalanche). OPool: **ARB + BNB only**. Maker EOAs: all chains incl. Avalanche. |
| [mdc.md](./mdc.md) | **Decentralized arbitration framework** — `OB_ReturnCabin`: `ORMDCFactory` → per-Maker `ORMakerDeposit` (MDC) margin/challenge contracts, `ORManager`, `ORFeeManager`, `ORSpvData`, EBC/SPV. Source-verified signatures; **deployed addresses unpublished/unconfirmed on-chain**. | Code-complete; on-chain presence on the 7 targets unconfirmed | unknown (no published factory address) |

## Cross-cutting facts

- **Most Orbiter volume is plain EOA→EOA**, not contract calls. A user sends native/ERC-20 **directly to a Maker EOA** (explorer label "Orbiter Finance: Bridge N"), encoding the destination chain in the **trailing digits of the amount** (the "identification code"). The Maker pays out on the target chain off-chain. **There is no Orbiter event for this path** — attribute by counterparty address.
- The `OrbiterXRouter` is an **optional wrapper**: native paths emit `Transfer(address indexed to, uint256 amount)` (topic `0x69ca02dd…`, **2-arg, not the ERC-20 Transfer**); ERC-20 paths emit **no** router event (only the token's own `Transfer`).
- **Nothing here is a proxy.** Routers + OPool are immutable; the only on-chain admin action is `OPool` owner setting maker/manager/receiver lists. The MDC framework's singletons are upgradeable but their addresses are not published.
- **Router bytecode is byte-identical on all 6 EVM chains** (sha256 `27f13214…`). Addresses are **unique on ETH/ARB/OP/POLY** but **shared `0x13e46b2a…` on BNB + Base** (and off-target Scroll/Linea/Mantle/Blast/Polygon-zkEVM). `OPool` shares `0x6285a466…` on ARB + BNB.
- **Avalanche C-Chain has no Orbiter contract** (router + OPool both `0x`); it is reachable only via the Maker-EOA flow.
- **Counterparty chains outside the seven** are common: zkSync Era, Polygon zkEVM, Scroll, Linea, Mantle, Blast, Arbitrum Nova, Manta, Mode, Taiko, plus non-EVM StarkNet / Solana / TON. Decode the destination from the amount suffix; do not assume the other leg is on a target chain.

Verification methodology and per-chain `eth_getCode`/slot reads are detailed in each file's final section (all checks dated 2026-06-09).
