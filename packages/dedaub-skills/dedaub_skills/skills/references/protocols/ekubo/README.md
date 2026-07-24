# Ekubo Protocol (EVM) — reference index

Ekubo Protocol is a **singleton, ownerless, immutable** concentrated-liquidity AMM (the EVM port of Ekubo-on-Starknet, by Moody Salem — ex-Uniswap V3 lead). Architecturally it is closest to **Uniswap V4**: one `Core` contract holds every pool's state and all tokens; pools are storage, not contracts; behaviour is attached via **extensions** (Ekubo's "hooks"); all operations settle through a `lock()` flash-accounting callback. Its defining quirk for monitoring: **swaps emit an anonymous `log0` with no `topic0`** — you cannot filter them by event signature.

EVM deployments are **versioned** (a new version = a brand-new contract set, never a proxy upgrade):

| Version | File | Status | Chains | Naming |
|---------|------|--------|--------|--------|
| **V3** | [`v3.md`](./v3.md) | **current** (release v3.1.1, 2026-05-03) | Ethereum, Base, BNB, Arbitrum, Optimism, Polygon (+ MegaETH, Monad, Ink, Unichain). **NOT Avalanche.** | `MEVCapture` |
| **V2** | [`v2.md`](./v2.md) | **deprecated** | Ethereum + Sepolia only | `MEVResist` |

> There is no public **V1** EVM mainnet deployment; the EVM line begins at V2 (the numbering tracks the Starknet protocol generations). V2 and V3 differ at the **event-signature level** (V2 uses explicit `(salt, bounds)` position-key tuples; V3 packs a `PositionId` bytes32 and adds `PoolState`/`PoolBalanceUpdate`), so do **not** reuse V2 topics for V3.

## What's where

- **Topics / selectors** are chain-agnostic and live in each version file (`§1`/`§2`). V3 Core has 5 named events (all data, none indexed) + 4 anonymous `log0` streams (swap, oracle, TWAMM, boosted-fees).
- **Addresses** are network-specific but **byte-identical across chains** (CREATE2 vanity); per-chain availability tables are in `v3.md §4`/`§5`.
- **Proxies:** none — every contract is immutable (`v3.md §6`).

## Cross-protocol gotchas (start here before indexing Ekubo)

1. **Swaps have no topic.** `address == Core AND topics == [] AND length(data) == 116` (V3). See `v3.md §1.2`, `§7.1`.
2. **`swap` and the lock callback both have selector `0x00000000`** (mined names). `v3.md §2.1`.
3. **Native token = `address(0)`**, first-class; no per-swap ERC-20 `Transfer`. `v3.md §7`.
4. **Avalanche is not deployed; BNB/OP/Polygon lack TWAMM + the Positions/Orders NFT managers.** `v3.md §5`.
5. **Requires EIP-7939 (`CLZ`, Fusaka/Osaka EVM)** on the target chain — gates *functionality*, not just deployment. As of 2026-06-05 only **Ethereum** had meaningful V3 volume; Base/BNB/Arb/OP/Polygon `Core` were deployed but ~dormant (OP-Stack chains still awaiting CLZ). Treat `eth_getCode ✓` as "deployed," not "trading." `v3.md §3`, `§7` (#13).

See also: [`../uniswap/v4.md`](../uniswap/v4.md) (the closest architectural sibling — singleton + hooks + flash accounting).
