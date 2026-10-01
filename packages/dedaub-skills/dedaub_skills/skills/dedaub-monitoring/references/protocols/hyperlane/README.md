# Hyperlane — reference index

**Hyperlane** is a permissionless interchain messaging protocol. A **Mailbox** on each chain dispatches and delivers messages; **warp routes** are the token bridges built on it (lock and release, burn and mint, or USDC through CCTP). Index both layers: the Mailbox carries the link key, the warp route carries the token movement.

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, `hyperlane-xyz/hyperlane-registry` (commit `09aa8356`) and `hyperlane-xyz/hyperlane-monorepo` (commit `c52b7280`).

| File | Layer | Contracts | Proxy pattern | Chains (of the 8) | Status |
|------|-------|-----------|---------------|-------------------|--------|
| [core.md](core.md) | Messaging core | Mailbox, MerkleTreeHook, InterchainGasPaymaster, ProtocolFee, default hooks and ISMs, PausableHook / PausableIsm, ValidatorAnnounce, ProxyAdmin, InterchainAccountRouter | Mailbox and IGP = TransparentUpgradeableProxy; the rest are plain contracts or clones | **All eight**, including Robinhood Chain (registry `robinhood`, domain 4663) | Live (Avalanche: 0 dispatches in the pinned window) |
| [warp_routes.md](warp_routes.md) | Token bridges | Collateral, Synthetic, Native, xERC20, xERC20 lockbox, CrossCollateralRouter, CCTP routes | EIP-1967 proxies per route (a few plain contracts) | Registry routes on the seven chains other than Robinhood Chain; Robinhood Chain has no registry route (one unlisted route observed) | Live (Avalanche routes idle in the pinned window) |

## Cross-cutting facts (read before indexing either file)

1. **A transfer = two transactions on two chains, joined by `messageId`.** Source: `SentTransferRemote` (route) + `Dispatch` + `DispatchId` (Mailbox). Destination: `Process` + `ProcessId` (Mailbox) + `ReceivedTransferRemote` (route). `messageId` is topic1 of `DispatchId` and of `ProcessId`; the warp events carry no id.
2. **Hyperlane domain = chain id on all eight target chains** (1, 8453, 42161, 10, 137, 56, 43114, 4663), read live from `Mailbox.localDomain()`. Other domains differ (Solana 1399811149).
3. **No shared address.** Every core contract has a different address per chain, and one literal address can be different contracts on different chains (`0xeA87ae93Fa0019a82A727bfd3eBd1cFCa8f64f1D` = Base Mailbox and Robinhood Chain ProxyAdmin). Key on `(chain, address)`.
4. **Permissionless means look-alikes.** Independent Mailboxes and unlisted routes emit the same topics. On Polygon in the pinned window an independent Mailbox (`0x599899e6b3b1362ba2460d125756a738ec1592d6`) dispatched 8,190 messages against 85 for the registry Mailbox. Filter on the registry addresses, or classify each emitter with `mailbox()`.
5. **No refund path.** An undelivered message stays pending; there is no cancel or expiry event in the core or in the warp routes.
6. **Governance.** Mailbox owners: Safes on Ethereum, Base, Optimism, Arbitrum and BNB (Arbitrum upgrades behind a 7-day timelock); interchain accounts (controlled by messages from another chain) on Polygon, Avalanche and Robinhood Chain. The gas paymaster owner is one EOA on every chain.

Event signatures, selectors, per-chain addresses, proxies and the bytea quick-copy blocks live in [core.md](core.md) and [warp_routes.md](warp_routes.md). USDC that a CCTP route moves is also visible as a Circle CCTP transfer: see [../cctp/README.md](../cctp/README.md).
