# Native (native.org) — Protocol Reference Index

**Status:** verified against live RPC and the `Native-org/native-v2-core` repo + Native docs on 2026-06-02.

Native is an on-chain liquidity platform built from **two interlocking product lines** rather than
linear versions. It is an **RFQ / PMM DEX backed by an on-chain credit pool**, not an AMM: off-chain
market makers (PMMs) sign firm EIP-712 quotes, and instead of pre-funding inventory they *borrow* it
from a shared credit vault on demand. The two halves are split into one file each.

| File | Product line | Core contracts | Generation |
|------|--------------|----------------|------------|
| [dex.md](dex.md) | **Native Swap Engine** (DEX/RFQ + cross-chain) | NativeRouter V4, NativeRouter V3, NativeRFQPool ("credit pool"), NativeBridge | V3 + V4 routers live |
| [lending.md](lending.md) | **Native Credit Pool** (lending/credit) | CreditVault, per-asset NativeLPToken | single generation (v2-core) |

## How the two halves connect

- A swap enters at **`NativeRouter.tradeRFQT`** → forwards to a registered **`NativeRFQPool`** → the pool
  pulls market-maker inventory out of the **`CreditVault`** and settles. The pool emits **`RFQTrade`**
  (the canonical swap event); the router emits nothing on the base RFQ path.
- The seam is the **`CreditVault`** address: every Router (`vault()`), Pool (`treasury()`), and Bridge
  (`vault()`) points at the chain's CreditVault. On the lending side, those swap pools are whitelisted via
  `setCreditPool` → **`CreditPoolUpdated`**, and they mutate trader positions through
  **`CreditVault.swapCallback`** (which emits *no* event — position changes from swaps are silent).
- Per-chain CreditVault: ETH `0xe3D41d19…`, BNB `0xBA8dB0CA…`, Arbitrum `0xbA1cf8A6…`, Base `0x74a4Cd02…`.

## Cross-cutting facts (true for both halves)

- **Nothing is a proxy.** Routers, RFQ pools, bridge, CreditVault, and all NativeLPTokens are **immutable
  direct deployments** (EIP-1967 impl/admin/beacon slots empty on every chain). There is **no
  `Upgraded(address)` topic** anywhere in Native — "upgrades" are fresh deployments + re-pointing wiring.
  The docs label "NativeRouter (Proxy)" is stale; storage-slot evidence is authoritative.
- **Off-chain authorization.** Credit limits, pricing, and liquidation eligibility live off-chain behind
  an EIP-712 `signer` (`0x0b89c5eb…` on all four chains). There is **no on-chain oracle, no ERC-4626 vault,
  no factory, no separate liquidation engine.** `SignerSet` rotation is a security-critical event to watch.
- **Chain coverage (4 of the 7 targets).** Both halves are deployed on **Ethereum (1), BNB (56),
  Arbitrum (42161), Base (8453)** and **absent on Avalanche (43114), Optimism (10), Polygon PoS (137)**
  (`eth_getCode = 0x`, re-confirmed 2026-06-02).
- **Address reuse is a trap.** Routers are *not* CREATE2-identical across chains (same byte-length per role,
  different bytecode + address). Several **NativeLPToken addresses collide across ETH/BNB** (same address,
  different underlying). Always key on **`(chainId, address)`** and confirm identity via `eip712Domain()` /
  `underlying()`, never by `eth_getCode` non-emptiness alone.

## Presence matrix (key contracts)

| Chain | ID | Router V4 | Router V3 | NativeRFQPool | NativeBridge | CreditVault | LP tokens |
|-------|----|-----------|-----------|---------------|--------------|-------------|-----------|
| Ethereum | 1 | ✓ | ✓ | ✓ (V4+V3 live) | ✓ | `0xe3D41d19…` | 27 |
| BNB Smart Chain | 56 | ✓ | ✓ | — (none registered yet) | ✓ | `0xBA8dB0CA…` | 44 |
| Arbitrum One | 42161 | ✓ | ✓ | — (none registered yet) | ✓ | `0xbA1cf8A6…` | 5 |
| Base | 8453 | ✓ | ✓ | — (none registered yet) | ✓ | `0x74a4Cd02…` | 5 |
| Avalanche C-Chain | 43114 | ✗ | ✗ | ✗ | ✗ | ✗ | — |
| Optimism | 10 | ✗ | ✗ | ✗ | ✗ | ✗ | — |
| Polygon PoS | 137 | ✗ | ✗ | ✗ | ✗ | ✗ | — |

> Only Ethereum currently has live `NativeRFQPool`(s). On BNB/Arbitrum/Base the routers + bridge are
> deployed and functional but **no credit pool is registered yet** (no `NativePoolUpdated` in their short
> history) — discover pools dynamically by indexing `NativePoolUpdated` per router going forward.

## Sources

- Docs: [docs.native.org](https://docs.native.org) · [Addresses](https://docs.native.org/native-dev/resources/addresses) · [Audits](https://docs.native.org/native-dev/resources/audits)
- GitHub: [Native-org/native-v2-core](https://github.com/Native-org/native-v2-core) (lending side; router/pool source is closed)
- DefiLlama: [native](https://defillama.com/protocol/native)
- Explorers: [Etherscan](https://etherscan.io/address/0xe3D41d19564922C9952f692C5Dd0563030f5f2EF) · [BscScan](https://bscscan.com/address/0xBA8dB0CAf781cAc69b6acf6C848aC148264Cc05d) · [Arbiscan](https://arbiscan.io/address/0xbA1cf8A63227b46575AF823BEB4d83D1025eff09) · [Basescan](https://basescan.org/address/0x74a4Cd023e5AfB88369E3f22b02440F2614a1367)
