# Allbridge — reference index

Allbridge ships **two distinct, coexisting bridge products** with separate codebases, contracts, addresses, and event sets. One file per product line.

| File | Product / generation | Architecture | Status | Chains (of the 7 requested) |
|------|----------------------|--------------|--------|------------------------------|
| [core.md](core.md) | **Allbridge Core** (current) | vUSD liquidity-pool bridge: `Bridge`(=Router) + per-token `Pool`s + `Messenger`/`WormholeMessenger` + `GasOracle`, plus bundled CCTP v1 / CCTP v2 / OFT adapters. All **immutable** (no proxies). | **Active via adapters only** — CCTP v1/v2, xReserve and OFT; the vUSD pool path (Bridge + Pools) was discontinued after the July 2026 security incident (official contracts page; every pool's `router()` = the admin, read 2026-10-05). | ETH, BNB, Polygon, Avalanche, Arbitrum, Optimism, Base — **all 7** carry a (deprecated) Bridge; live adapters on all except BNB. |
| [classic.md](classic.md) | **Allbridge Classic** (legacy) | Lock/burn-and-unlock bridge: one immutable `Bridge` contract per chain at a shared vanity address; validator-signed `unlock`. | **Deprecated, sunsetting mid-2026** (still live) | Bridge on **ETH, BNB, Polygon, Avalanche only**. Arbitrum/Base = a non-bridge sweeper at the vanity addr; Optimism = `0x`. |

**Robinhood Chain (4663):** no Allbridge contract of either product. `eth_getCode` returns `0x` at the Classic vanity address and at every Core address checked, and neither official contract list names the chain (checked 2026-09-29). **Arc (5042):** the official Core contract page lists no Arc entry (checked 2026-10-05).

## Cross-cutting facts

- **Two products, different addressing schemes.** Core uses **unrelated per-chain addresses** (shared invariant = the owner `0x01a494079dcb715f622340301463ce50cd69a4d0`, not the address). Classic uses **one cross-chain vanity literal** `0xBBbD1BbB4f9b936C3604906D7592A644071dE884` (matching the Solana program `BBbD1WSj…`).
- **Nothing in Allbridge is a proxy.** Every contract in both products is **immutable** — the EIP-1967 impl slot reads `0x0` everywhere. "Upgrades" = redeploy + owner-only re-pointing. There is **no `Upgraded(address)` event to watch**; instead watch owner-only setters and (Core) `SecondaryValidatorsSet` validator rotations.
- **`TokensSent`/`Received`/`MessageSent` topic0s collide by name across contracts and across the two products.** Always key on `(topic0, emitter)`. See core.md §12 / classic.md §6 for the full disambiguation.
- **Counterparty chains outside the seven** (recorded as bridge destinations, not omissions): Core → Tron, Solana, Celo, Sui. Classic → NEAR, Solana, Stacks, Stellar, XRPL, Tezos, Terra, HECO, Fantom, Celo.
- **Verification:** all topic0s/selectors recomputed locally as `keccak256(sig)` from the canonical `allbridge-io` Solidity/ABI sources and cross-checked against live `eth_getLogs`; all addresses existence-checked via `eth_getCode`; proxy/immutability confirmed by reading the EIP-1967 slot live. Details in each file's "Verification & sources" section.

_Last verified: 2026-06-09; Core status re-checked 2026-10-05._
