# Beets (Beethoven X) — Topics, Selectors, Addresses (Optimism)

**Status:** all addresses independently verified on-chain via `cast` against publicnode RPCs (2026-06). Swap topic0 live-confirmed against Optimism Vault logs (block 125173056). No-proxy confirmed on all contracts (EIP-1967 slot = 0x0 on all). Beets-specific WeightedPoolFactory confirmed absent (0x) on Base and BNB only; unrelated contracts exist at the same address on Ethereum (6392B), Arbitrum (3072B), Avalanche (1628B), and Polygon (2776B) — all different bytecode from Optimism's 24476B.
**Scope:** Beets on **Optimism (chain ID 10) only**. Fantom and Sonic deployments are out of scope. The 6 other target chains (Ethereum 1, Base 8453, BNB 56, Avalanche 43114, Arbitrum 42161, Polygon 137) have no Beets-specific deployment — the Vault address is shared with Balancer V2 on those chains (see [`balancer/v2.md`](../balancer/v2.md)).

**Core architecture:** Beets is a Balancer V2 friendly fork. The Vault is the **same** contract as Balancer V2's (`0xBA12222222228d8Ba445958a75a0704d566BF2C8`) — the vanity address is deterministic and identical across all Balancer V2 chains. All Vault event topic0s, function selectors, and the single-Vault custody model are **identical to Balancer V2** — see [`balancer/v2.md`](../balancer/v2.md) §1–§2 for the full topic0 and selector reference. This file documents what is **Beets-specific**: its Optimism pool factory addresses, peripheral contracts, and the Authorizer/governance on that chain.

---

## 1. Topics (chain-agnostic — same as Balancer V2)

All Vault and pool event topic0s are **identical to Balancer V2**. See [`balancer/v2.md`](../balancer/v2.md) §1 for the complete table. Key entries repeated here for quick reference:

### 1.1 Vault events (emitted by `0xBA12222222228d8Ba445958a75a0704d566BF2C8`)

| topic0 | Event |
|--------|-------|
| `0x2170c741c41531aec20e7c107c24eecfdd15e69c9bb0a8dd37b1840b9e0b207b` | `Swap(bytes32 indexed poolId, address indexed tokenIn, address indexed tokenOut, uint256 amountIn, uint256 amountOut)` — **live-confirmed** on Optimism Vault |
| `0xe5ce249087ce04f05a957192435400fd97868dba0e6a4b4c049abf8af80dae78` | `PoolBalanceChanged(bytes32 indexed poolId, address indexed liquidityProvider, address[] tokens, int256[] deltas, uint256[] protocolFeeAmounts)` — joins AND exits |
| `0x3c13bc30b8e878c53fd2a36b679409c073afd75950be43d8858768e956fbc20e` | `PoolRegistered(bytes32 indexed poolId, address indexed poolAddress, uint8 specialization)` |
| `0xf5847d3f2197b16cdcd2098ec95d0905cd1abdaf415f07bb7cef2bba8ac5dec4` | `TokensRegistered(bytes32 indexed poolId, address[] tokens, address[] assetManagers)` |
| `0x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0` | `FlashLoan(address indexed recipient, address indexed token, uint256 amount, uint256 feeAmount)` |
| `0x94b979b6831a51293e2641426f97747feed46f17779fed9cd18d1ecefcfe92ef` | `AuthorizerChanged(address indexed newAuthorizer)` |
| `0x18e1ea4139e68413d7d08aa752e71568e36b2c5bf940893314c2c5b01eaa0c42` | `InternalBalanceChanged(address indexed user, address indexed token, int256 delta)` |
| `0x6edcaf6241105b4c94c2efdbf3a6b12458eb3d07be3a0e81d24b13c44045fe7a` | `PoolBalanceManaged(bytes32 indexed poolId, address indexed assetManager, address indexed token, int256 cashDelta, int256 managedDelta)` |

### 1.2 Pool / factory events

| topic0 | Event | Source |
|--------|-------|--------|
| `0x83a48fbcfc991335314e74d0496aab6a1987e992ddc85dddbcc4d6dd6ef2e9fc` | `PoolCreated(address indexed pool)` | every pool factory |
| `0xa9ba3ffe0b6c366b81232caab38605a0699ad5398d6cce76f91ee809e322dafc` | `SwapFeePercentageChanged(uint256 swapFeePercentage)` | pool |
| `0x9e3a5e37224532dea67b89face185703738a228a6e8a23dee546960180d3be64` | `PausedStateChanged(bool paused)` | pool |
| `0x0f3631f9dab08169d1db21c6dc5f32536fb2b0a6b9bb5330d71c52132f968be0` | `GradualWeightUpdateScheduled(uint256 startTime, uint256 endTime, uint256[] startWeights, uint256[] endWeights)` | WeightedPool |
| `0x1835882ee7a34ac194f717a35e09bb1d24c82a3b9d854ab6c9749525b714cdf2` | `AmpUpdateStarted(uint256 startValue, uint256 endValue, uint256 startTime, uint256 endTime)` | StablePool |
| `0xa0d01593e47e69d07e0ccd87bece09411e07dd1ed40ca8f2e7af2976542a0233` | `AmpUpdateStopped(uint256 currentValue)` | StablePool |

---

## 2. Function selectors (chain-agnostic — same as Balancer V2)

See [`balancer/v2.md`](../balancer/v2.md) §2 for the full selector table. Critical Vault entry points:

| Selector | Signature |
|----------|-----------|
| `0x52bbbe29` | `swap((bytes32,uint8,address,address,uint256,bytes),(address,bool,address,bool),uint256,uint256)` |
| `0x945bcec9` | `batchSwap(uint8,(bytes32,uint256,uint256,uint256,bytes)[],address[],(address,bool,address,bool),int256[],uint256)` |
| `0xb95cac28` | `joinPool(bytes32,address,address,(address[],uint256[],bytes,bool))` |
| `0x8bdb3913` | `exitPool(bytes32,address,address,(address[],uint256[],bytes,bool))` |
| `0x5c38449e` | `flashLoan(address,address[],uint256[],bytes)` |
| `0xf94d4668` | `getPoolTokens(bytes32)` → `(address[],uint256[],uint256)` |
| `0xfa2f9282` | `batchSwap` with `FundManagement[]` array (used by Relayer, not the main Vault `batchSwap`) |

---

## 3. Addresses — Optimism (chain ID 10)

All contracts verified on-chain (code size > 0, function call returns correct vault reference). No contract is a proxy (EIP-1967 implementation slot = `0x0` on all).

### 3.1 Core (Balancer V2 Vault — shared code, deployed by Beets on Optimism)

| Role | Address | Bytecode |
|------|---------|----------|
| **Vault** | `0xBA12222222228d8Ba445958a75a0704d566BF2C8` | ~24512 bytes — same code as all Balancer V2 chains; not a proxy, not upgradeable |
| ProtocolFeesCollector | `0xce88686553686DA562CE7Cea497CE749DA109f9F` | ~2880 bytes — `vault()` → Vault confirmed |
| BalancerHelpers | `0x8E9aa87E45e92bad84D5F8DD1bff34Fb92637dE9` | ~3796 bytes — `vault()` → Vault confirmed |
| BalancerQueries | `0xE39B5e3B6D74016b2F6A9673D7d7493B6DF549d5` | shared with Balancer V2 Optimism — `vault()` → Vault confirmed |

### 3.2 Beets-specific: pool factories

| Role | Address | Bytecode |
|------|---------|----------|
| **WeightedPoolFactory** | `0xdAE7e32ADc5d490a43cCba1f0c736033F2b4eFca` | ~24476 bytes — Optimism-only (0x on Base/BNB; unrelated contracts at same address on ETH/Arbitrum/Avalanche/Polygon — different bytecode) |
| **StablePoolFactory** | `0xeb151668006CD04DAdD098AFd0a82e78F77076c3` | ~3399 bytes — `isDisabled()` → false (active); Optimism-only among 7 target chains |

These are Beets's own factory deployments, at different addresses than Balancer V2's Optimism factories (`0x230a59F4…` / `0x4bdCc2fb…`). Both remain active. Watch `PoolCreated` from both factories to enumerate all Beets pools.

### 3.3 Governance

| Role | Address | Notes |
|------|---------|-------|
| Authorizer (initial) | `0xA331D84eC860Bf466b4CdCcFb4aC09a1B43F3aE6` | ~3281 bytes — standard Balancer Authorizer; same address as Balancer V2 Authorizer on most chains |
| Authorizer (current / live) | `0xAcf05BE5134d64d150d153818F8C67EE36996650` | ~770 bytes — returned by `Vault.getAuthorizer()` at time of verification; `AuthorizerChanged` on the Vault marks future changes |

`Vault.getAuthorizer()` is the canonical source of truth for the live Authorizer. The `AuthorizerChanged` event (`topic0 0x94b979b6…`) tracks all future changes.

**No BEETS token or veSystem on Optimism.** The BEETS token and veSystem (fBEETS/sfBEETS) are on Sonic/Fantom and are out of scope for this file.

---

## 4. Chain coverage confirmation

| Chain | ID | Vault | Beets WeightedPoolFactory `0xdAE7…` | Result |
|-------|----|-------|--------------------------------------|--------|
| **Optimism** | **10** | `0xBA12…F2C8` ✓ | 24476 bytes ✓ | **Beets deployed** |
| Ethereum | 1 | `0xBA12…F2C8` (Balancer) | unrelated contract (~6392 bytes) | Not Beets |
| Arbitrum | 42161 | `0xBA12…F2C8` (Balancer) | unrelated contract (~3072 bytes) | Not Beets |
| Base | 8453 | `0xBA12…F2C8` (Balancer) | **0x** | Not Beets |
| BNB | 56 | `0xBA12…F2C8` (Balancer) | **0x** | Not Beets |
| Avalanche | 43114 | `0xBA12…F2C8` (Balancer) | unrelated contract (~1628 bytes) | Not Beets |
| Polygon | 137 | `0xBA12…F2C8` (Balancer) | unrelated contract (~2776 bytes) | Not Beets |

The Vault address `0xBA12222222228d8Ba445958a75a0704d566BF2C8` on the non-Optimism chains is the Balancer V2 Vault, not a Beets deployment.

---

## 5. Proxies

- **Vault**: monolithic singleton, not a proxy. EIP-1967 implementation slot = `0x0`. Not upgradeable; only the Authorizer address is swappable (via `AuthorizerChanged`).
- **WeightedPoolFactory, StablePoolFactory, Authorizer, ProtocolFeesCollector, BalancerHelpers**: all non-proxy. EIP-1967 implementation slot = `0x0` on all.
- **Pools** deployed by factories: full contracts (not EIP-1167 clones). Logic is immutable; support pause and recovery mode but no code upgrade.

---

## 6. Detection notes

1. **Monitor the Vault, not the pools.** `Swap`, `PoolBalanceChanged`, and `FlashLoan` all emit from `0xBA12222222228d8Ba445958a75a0704d566BF2C8` on Optimism. One address captures all Beets pool activity.
2. **`poolId` encodes pool address.** The leftmost 20 bytes of the 32-byte `poolId` field in every Vault event are the pool contract address — no lookup needed.
3. **`PoolBalanceChanged` is both joins and exits.** Positive `deltas` = join (tokens in), negative = exit. There is no separate Join/Exit event.
4. **`batchSwap` emits one `Swap` per hop** from the Vault. A single user trade across N pools = N `Swap` logs in the same tx.
5. **Two active pool factories.** `PoolCreated` events from both `0xdAE7…` (WeightedPoolFactory) and `0xeb15…` (StablePoolFactory) register new Beets pools. Both also surface as `PoolRegistered` on the Vault.
6. **Authorizer address can change.** `Vault.getAuthorizer()` is authoritative; `AuthorizerChanged` tracks transitions. The known live authorizer (`0xAcf0…`) differs from the initial one (`0xA331…`).
7. **No Beets-specific token monitoring needed on Optimism.** The BEETS token is on Sonic/Fantom (out of scope); Optimism activity is purely pool-based.
8. **The Vault is shared code with Balancer V2.** Any monitoring query for the Vault on Optimism will also capture Balancer V2 Optimism pools (Balancer also has its own factories on Optimism). Filter by `poolId` prefix if you need Beets-only pools (all Beets pools have their pool address in the poolId, and were created by the Beets factories at `0xdAE7…` / `0xeb15…`).

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Beets / Beethoven X — Optimism (chain ID 10) =====
-- Vault events: identical topic0 as Balancer V2 (see balancer/v2.md §13 for full list)
BEETS_OP_VAULT_SWAP              = '\x2170c741c41531aec20e7c107c24eecfdd15e69c9bb0a8dd37b1840b9e0b207b'  -- live-confirmed block 125173056
BEETS_OP_VAULT_POOL_BALANCE_CHG  = '\xe5ce249087ce04f05a957192435400fd97868dba0e6a4b4c049abf8af80dae78'  -- joins + exits
BEETS_OP_VAULT_POOL_REGISTERED   = '\x3c13bc30b8e878c53fd2a36b679409c073afd75950be43d8858768e956fbc20e'
BEETS_OP_VAULT_FLASH_LOAN        = '\x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0'
BEETS_OP_AUTHORIZER_CHANGED      = '\x94b979b6831a51293e2641426f97747feed46f17779fed9cd18d1ecefcfe92ef'
-- Factory events
BEETS_OP_POOL_CREATED            = '\x83a48fbcfc991335314e74d0496aab6a1987e992ddc85dddbcc4d6dd6ef2e9fc'  -- PoolCreated(address indexed pool)
-- Pool events
BEETS_OP_SWAP_FEE_CHANGED        = '\xa9ba3ffe0b6c366b81232caab38605a0699ad5398d6cce76f91ee809e322dafc'
BEETS_OP_AMP_UPDATE_STARTED      = '\x1835882ee7a34ac194f717a35e09bb1d24c82a3b9d854ab6c9749525b714cdf2'

-- ===== Function selectors (chain-agnostic; same as Balancer V2) =====
BEETS_SEL_SWAP                   = '\x52bbbe29'
BEETS_SEL_BATCH_SWAP             = '\x945bcec9'
BEETS_SEL_JOIN_POOL              = '\xb95cac28'
BEETS_SEL_EXIT_POOL              = '\x8bdb3913'
BEETS_SEL_FLASH_LOAN             = '\x5c38449e'

-- ===== Addresses — Optimism (chain ID 10) =====
BEETS_OP_VAULT                   = '\xba12222222228d8ba445958a75a0704d566bf2c8'  -- Balancer V2 Vault (same code, deployed by Beets)
BEETS_OP_WEIGHTED_POOL_FACTORY   = '\xdae7e32adc5d490a43ccba1f0c736033f2b4efca'  -- Beets-specific; 0x on Base/BNB; unrelated contracts at same addr on ETH/ARB/AVAX/POLY
BEETS_OP_STABLE_POOL_FACTORY     = '\xeb151668006cd04dadd098afd0a82e78f77076c3'  -- Beets-specific
BEETS_OP_PROTOCOL_FEES_COLLECTOR = '\xce88686553686da562ce7cea497ce749da109f9f'
BEETS_OP_BALANCER_HELPERS        = '\x8e9aa87e45e92bad84d5f8dd1bff34fb92637de9'
BEETS_OP_BALANCER_QUERIES        = '\xe39b5e3b6d74016b2f6a9673d7d7493b6df549d5'
BEETS_OP_AUTHORIZER_INITIAL      = '\xa331d84ec860bf466b4cdccfb4ac09a1b43f3ae6'
BEETS_OP_AUTHORIZER_CURRENT      = '\xacf05be5134d64d150d153818f8c67ee36996650'  -- as of 2026-06; check Vault.getAuthorizer()
```

---

## 8. Sources

- **Contracts and addresses**: [`beethovenxio/beethovenx-contracts`](https://github.com/beethovenxio/beethovenx-contracts), [`balancer/balancer-deployments`](https://github.com/balancer/balancer-deployments), [Beets docs](https://docs.beets.fi/technicals/deployments).
- **Event signatures and selectors**: [`balancer/balancer-v2-monorepo`](https://github.com/balancer/balancer-v2-monorepo) (`pkg/interfaces/contracts/vault/IVault.sol`, `pkg/pool-weighted`, `pkg/pool-stable`). All topic0s and selectors computed with `cast keccak` / `cast sig`; Vault `Swap` topic0 live-confirmed on-chain.
- **On-chain verification**: all addresses re-verified via `cast` against `optimism-rpc.publicnode.com`; cross-chain absence confirmed on `ethereum-rpc.publicnode.com`, `arbitrum-one-rpc.publicnode.com`, `base-rpc.publicnode.com`, `bsc-rpc.publicnode.com`; Avalanche/Polygon non-empty but confirmed unrelated contracts (2026-06).
- **Shared Vault**: the Balancer V2 Vault architecture (single-Vault custody model, `poolId` encoding, join/exit semantics) is documented in detail in [`balancer/v2.md`](../balancer/v2.md).
