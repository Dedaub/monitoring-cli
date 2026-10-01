# Orbiter Finance — reference index

Cross-rollup bridge with an **optimistic / off-chain-relayer** design. Two clearly separate on-chain generations/product lines, one file each.

| File | Component / generation | Status | Chains present (of the 8 targets) |
|------|------------------------|--------|-----------------------------------|
| [core.md](./core.md) | **Live bridge surface** — `OrbiterXRouter` ("RouterV3") multicall transfer wrapper, legacy `OBSource` router, the `Aggregator` swap-and-bridge proxy (`BridgeExecuted`), both `OPool` maker-liquidity pool generations (`Inbox`/`Outbox`), the `VizingPad` message station, and the **Maker EOAs** that actually move funds. | Live; routers and OPools immutable, Aggregator and VizingPad upgradeable | Router: **ETH, ARB, OP, POLY, BNB, Base** (NOT Avalanche). Aggregator `0xe530d28960d48708ccf3e62aa7b42a80bc427aef`: those six **+ Avalanche** (unlisted). OPool gen 1: **ARB + BNB**; Opool gen 2: **ETH, ARB, OP, BNB, Base**. VizingPad: ETH, Base, ARB, OP (+ unlisted BNB). Maker EOAs: all chains incl. Avalanche. **Robinhood Chain (4663): nothing.** |
| [mdc.md](./mdc.md) | **Decentralized arbitration framework** — `OB_ReturnCabin`: `ORMDCFactory` → per-Maker `ORMakerDeposit` (MDC) margin/challenge contracts, `ORManager`, `ORFeeManager`, `ORSpvData`, EBC/SPV. Source-verified signatures; **deployed addresses unpublished/unconfirmed on-chain**. | Code-complete; on-chain presence on the 8 targets unconfirmed | unknown (no published factory address) |

## Cross-cutting facts

- **Most Orbiter volume is plain EOA→EOA**, not contract calls. A user sends native/ERC-20 **directly to a Maker EOA** (explorer label "Orbiter Finance: Bridge N"), encoding the destination chain in the **trailing digits of the amount** (the "identification code"). The Maker pays out on the target chain off-chain. **There is no Orbiter event for this path** — attribute by counterparty address.
- The `OrbiterXRouter` is an **optional wrapper**: native paths emit `Transfer(address indexed to, uint256 amount)` (topic `0x69ca02dd4edd7bf0a4abb9ed3b7af3f14778db5d61921c7dc7cd545266326de2`, **2-arg, not the ERC-20 Transfer**); ERC-20 paths emit **no** router event (only the token's own `Transfer`).
- **Contract source legs** (in addition to the maker-EOA flow): Aggregator `BridgeExecuted` (`recipient` = the maker), OPool `Inbox` (two generations, two topics), VizingPad `SuccessfulLaunchMessage`. **Destination legs:** maker payouts (no event), OPool `Outbox`, VizingPad `SuccessfulLanding`. No path has a refund event.
- **Routers and OPools are immutable; the Aggregator and the VizingPad are not.** The `Aggregator` is an EIP-1967 transparent proxy whose ProxyAdmin owner and `owner()` are one EOA (`0xdd08e0aaaa2e063dafb2df2dee19b5b0dd220ff6`), which can pause it, change its executor and withdraw its balance; the `VizingPad` is a UUPS proxy under `AccessControl`. The OPool owner sets maker/manager/receiver lists. The MDC framework's singletons are upgradeable but their addresses are not published.
- **Router bytecode is byte-identical on all 6 EVM chains** (sha256 `27f13214…`). Addresses are **unique on ETH/ARB/OP/POLY** but **shared `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` on BNB + Base** (and off-target Scroll/Linea/Mantle/Blast/Polygon-zkEVM). `OPool` shares `0x6285a466a98f513e1f6be29acad27d173d3b3c59` on ARB + BNB.
- **Avalanche C-Chain has no router or OPool** (both `0x`); it is reachable via the Maker-EOA flow and through the unlisted Aggregator proxy.
- **Robinhood Chain (4663) has no Orbiter contract and no maker activity**, and no official Orbiter list names it (core.md §10).
- **Counterparty chains outside the eight** are common: zkSync Era, Polygon zkEVM, Scroll, Linea, Mantle, Blast, Arbitrum Nova, Manta, Mode, Taiko, plus non-EVM StarkNet / Solana / TON. Decode the destination from the amount suffix; do not assume the other leg is on a target chain.

Verification methodology and per-chain `eth_getCode`/slot reads are detailed in each file's final section (checks dated 2026-06-09, extended on 2026-09-29).
