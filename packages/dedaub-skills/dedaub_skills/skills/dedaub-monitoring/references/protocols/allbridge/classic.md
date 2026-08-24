# Allbridge Classic — Topics, Selectors, Addresses (Ethereum, BNB, Polygon, Avalanche; NOT Arbitrum/Optimism/Base)

**Status:** verified against live RPC on all seven requested chains and the canonical `allbridge-io/allbridge-contract-docs` ABI on 2026-06-09. Topic0s/selectors recomputed locally as `keccak256(signature)` and cross-checked against live `eth_getLogs`; the one vanity address existence-checked via `eth_getCode` on every chain.
**Scope:** Allbridge **Classic** — the original lock/burn-and-unlock token bridge (predecessor to [Core](core.md)). One Solidity Bridge contract per chain at a shared vanity address. Topics + selectors are **chain-agnostic**; the address is one cross-chain vanity literal but only carries real bridge bytecode on four of the seven chains. **Allbridge Classic is deprecated and scheduled to stop in mid-2026** (per the official docs) — but it is **still live** (verified recent `lock`/`unlock` activity on Ethereum).

Classic is a **classic lock/unlock bridge**, not a liquidity-pool bridge. To send: call `lock` (ERC-20) or `lockBase` (native), which transfers the token to the Bridge and **locks it** (native tokens) or **burns** the wrapped representation, emitting `Sent`. An off-chain validator signs a confirmation; the recipient calls `unlock` on the destination Bridge with that signature, which **releases** the locked token (or **mints** the wrapped one), emitting `Received`. There are no pools, no vUSD, no LP tokens, no per-token contracts — a single Bridge contract handles every supported token via a `tokenInfos` registry.

**Single cross-chain vanity address:** `0xBBbD1BbB4f9b936C3604906D7592A644071dE884` (the `BBbD1` prefix matches the Solana program `BBbD1WSjbHKfyE3TSFWF6vx1JV51c8msKSQy4ess6pXp` and account `bb1XfNoER5QC3rhVDaVz3AJp9oFKoHNHG6PHfZLcCjj`). The Bridge is **immutable** (EIP-1967 impl slot reads `0x0`); access control is via dedicated role getters (`validator()`, `unlockSigner()`, `feeCollector()`, `feeOracle()`), **not** OpenZeppelin Ownable — there is no `owner()`.

**Critical chain-coverage finding:** of the seven requested chains, the vanity address carries the real 19,273-byte Bridge **only on Ethereum, BNB, Polygon, and Avalanche.** On **Arbitrum and Base** the same address holds a tiny **777-byte `Ownable` sweeper** (selectors `withdraw()`/`owner()`/`transferOwnership(address)`/`renounceOwnership()` — NOT a bridge), and on **Optimism it is empty (`0x`).** Classic never deployed to Arbitrum/Optimism/Base as a bridge (its blockchain-ID table predates those L2s — see §6).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Classic Bridge (single contract per chain — §3)

| topic0 | Event | Meaning |
|--------|-------|---------|
| `0x884a8def17f0d5bbb3fef53f3136b5320c9b39f75afb8985eeab9ea1153ee56d` | `Sent(bytes4 tokenSource, bytes32 tokenSourceAddress, address sender, bytes32 indexed recipient, uint256 amount, uint128 indexed lockId, bytes4 destination)` | **Source-chain lock/burn.** `lockId` (indexed) is the cross-chain key; `destination` is a 4-byte UTF-8 chain id (§6). *(verified live on ETH)* |
| `0xeeff8dc309b75f785752dd67594b2d8a3a9fd4ff6ecd65fcfe670cee0d851ce4` | `Received(address indexed recipient, address token, uint256 amount, uint128 indexed lockId, bytes4 source)` | **Destination-chain unlock/mint.** Matches a `Sent` on the source chain by `lockId` + `source`. *(verified live on ETH — recent unlocks)* |

There are exactly **two** events. No ownership/admin events are emitted (roles are plain storage, mutated by non-eventing setters). Disambiguate `Sent` vs `Received` purely by topic0; both share the `lockId` indexed key.

> **Topic0 name-collision warning:** the literal `Received(...)` topic0 here (`0xeeff8dc3…`, the 5-arg unlock event) is **not** the same as the various `Received(address,uint256)` gas events in Allbridge Core (`0x88a5966d…`). Different signatures → different topic0s. And the Classic `Received` is the **unlock** event, not a gas-receipt event.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Classic Bridge — single-validator ABI (`allbridge-abi.json`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7bacc91e` | `lock(uint128 lockId, address tokenAddress, bytes32 recipient, bytes4 destination, uint256 amount)` | ERC-20 send. `lockId` first byte must be `0x01` (bridge version). Emits `Sent`. |
| `0x5e3b0f9e` | `lockBase(uint128 lockId, address wrappedBaseTokenAddress, bytes32 recipient, bytes4 destination)` | `payable` — native-token send (pass WETH/WBNB/WMATIC/WAVAX addr). Emits `Sent`. |
| `0x14b824e0` | `unlock(uint128 lockId, address recipient, uint256 amount, bytes4 lockSource, bytes4 tokenSource, bytes32 tokenSourceAddress, bytes signature)` | Single-validator release/mint. Emits `Received`. |
| `0x3a5381b5` | `validator()` → `address` | The signing validator. ETH = `0x93746538d4519c809827205bd1c2c7a0e15bd74b`. |
| `0x00c45c54` | `unlockSigner()` → `address` | Signer authorized to unlock. ETH = `0x83f53c07…0c5e`. |
| `0xc415b95c` | `feeCollector()` → `address` | Fee sink. ETH = `0x83f53c07…0c5e`. |
| `0x500b19e7` | `feeOracle()` → `address` | Fee oracle. ETH = `0xba6d8de0…e1f6`. |
| `0xba46ae72` | `tokenInfos(address)` | Per-token config (isWrapped, precision, min fee, …). |
| `0x64cd2af3` | `tokenSourceMap(bytes4,bytes32)` → `address` | Maps a `(sourceChain, sourceTokenAddr)` to the local token. |

### 2.2 Classic Bridge — multisig (Stellar-route) ABI (`allbridge-multisig-abi.json`)

The multisig variant is identical except `unlock` takes a **second** signature (two-of-N for the Stellar integration):

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb43d20c3` | `unlock(uint128 lockId, address recipient, uint256 amount, bytes4 lockSource, bytes4 tokenSource, bytes32 tokenSourceAddress, bytes signature, bytes secondarySignature)` | **8-arg — distinct selector from the 7-arg `unlock`.** Used on the Stellar multisig bridge route. |

`lock` / `lockBase` / `Sent` / `Received` are identical across both ABIs.

---

## 3. Addresses — all chains

The Classic Bridge lives at one vanity literal `0xBBbD1BbB4f9b936C3604906D7592A644071dE884`. Verified via `eth_getCode` on each chain's publicnode RPC on 2026-06-09.

| Chain | ID | `eth_getCode` at `0xBBbD1Bbb…dE884` | What's there |
|---|---|---|---|
| **Ethereum** | 1 | **19,273 B** | ✅ Classic Bridge (active). |
| **BNB** | 56 | **19,273 B** | ✅ Classic Bridge (identical bytecode). |
| **Polygon** | 137 | **19,273 B** | ✅ Classic Bridge. |
| **Avalanche** | 43114 | **19,273 B** | ✅ Classic Bridge. |
| **Arbitrum** | 42161 | **777 B** | ⚠️ **NOT a bridge** — a minimal `Ownable` sweeper (`withdraw()` 0x3ccfd60b, `owner()`, `transferOwnership`, `renounceOwnership`). No `lock`/`unlock`/`Sent`/`Received`. |
| **Base** | 8453 | **777 B** | ⚠️ Same sweeper as Arbitrum. NOT a Classic bridge. |
| **Optimism** | 10 | **`0x` (0 B)** | ❌ Not deployed at all. |

### 3.1 Ethereum role addresses (read live)

| Role | Address |
|------|---------|
| **Bridge** | `0xBBbD1BbB4f9b936C3604906D7592A644071dE884` |
| `validator()` | `0x93746538d4519c809827205bd1c2c7a0e15bd74b` |
| `unlockSigner()` | `0x83f53c078bf81f6d8b79e01e2ed36c473a960c5e` |
| `feeCollector()` | `0x83f53c078bf81f6d8b79e01e2ed36c473a960c5e` (= unlockSigner) |
| `feeOracle()` | `0xba6d8de08f13a3d22fcec54752812dd4dcf2e1f6` |

(Read role getters per-chain on BNB/Polygon/Avax for those chains' validator/signer set; the same getters apply.)

### 3.2 Non-EVM counterparty addresses (NOT in the seven; record as bridge destinations)

| Network | Address |
|---|---|
| NEAR | `bridge.a11bd.near` |
| Solana (account / program) | `bb1XfNoER5QC3rhVDaVz3AJp9oFKoHNHG6PHfZLcCjj` / `BBbD1WSjbHKfyE3TSFWF6vx1JV51c8msKSQy4ess6pXp` |
| Stacks | `SP3Y2ZSH8P7D50B0VBTSX11S7XSG24M1VB9YFQA4K.bridge` (legacy `SP31MH65V85NDTM30FJBKP4JNC39HR1ZX3CRW9Z97.bridge`) |
| Stellar | `GALLBRBQHAPW5FOVXXHYWR6J4ZDAQ35BMSNADYGBW25VOUHUYRZM4XIL` |
| XRPL | `r4w1LrneWZqX5RrgFPx2gto66dwo2Zymqy` |

---

## 4. Cross-chain summary

| Chain | ID | Classic Bridge | Note |
|---|---|---|---|
| Ethereum | 1 | ✅ `0xBBbD1Bbb…dE884` (19,273 B) | active despite deprecation |
| BNB | 56 | ✅ `0xBBbD1Bbb…dE884` | |
| Polygon | 137 | ✅ `0xBBbD1Bbb…dE884` | |
| Avalanche | 43114 | ✅ `0xBBbD1Bbb…dE884` | |
| Arbitrum | 42161 | ❌ (777-B sweeper at the vanity addr, not a bridge) | |
| Base | 8453 | ❌ (777-B sweeper at the vanity addr) | |
| Optimism | 10 | ❌ (`0x`) | |

Vanity tell: the bridge address `0xBBbD1Bbb…` and the Solana program `BBbD1WSj…` share the `BBbD1` prefix. **But the same literal also carries a non-bridge sweeper on Arbitrum/Base** — never assume "address has code ⇒ Classic bridge"; gate on bytecode size (≈19,273 B) or the presence of the `Sent`/`Received` topic0s.

---

## 5. Proxies (old & new)

**No proxy. The Classic Bridge is immutable.** EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` reads `0x000…000` on Ethereum, BNB, Polygon, and Avalanche (confirmed live). There is no `Upgraded(address)` event and no `owner()` — role rotation happens via non-eventing setters guarded by the on-chain roles (`validator`/`unlockSigner`). The 777-B Arbitrum/Base sweeper is likewise a plain non-proxy `Ownable`.

| Contract | Pattern | Detection | Auth |
|----------|---------|-----------|------|
| Classic Bridge (ETH/BNB/Polygon/Avax) | **Immutable (no proxy)** | impl slot = `0x0`; full 19,273-B runtime in-account; exposes `lock`/`unlock`/`validator`. | role getters (`validator`/`unlockSigner`), no Ownable. |
| Vanity-address sweeper (Arb/Base) | Immutable `Ownable` (777 B) | selectors `0x3ccfd60b withdraw()`, `0x8da5cb5b owner()`; impl slot `0x0`. | `owner()`. |

---

## 6. Detection invariants & gotchas

1. **Classic ≠ Core.** Classic is a lock/unlock bridge with two events (`Sent`/`Received`) at one vanity address; Core is a vUSD pool bridge ([core.md](core.md)) with separate Bridge/Pool/Messenger contracts at unrelated addresses. They are different products that coexist (Classic deprecated, sunsetting mid-2026).
2. **Bridge present on only 4 of the 7 chains.** ETH/BNB/Polygon/Avax = real bridge; Arbitrum/Base = a 777-B sweeper at the same address (NOT a bridge); Optimism = `0x`. Gate on bytecode size or topic0 presence — the vanity address alone is misleading.
3. **`lockId` is the cross-chain key**, indexed in both `Sent` and `Received`. Its **first byte is the bridge version (`0x01`)**. Match a destination `Received` to its source `Sent` by `lockId` + the `source`/`destination` chain-id bytes.
4. **`destination`/`source` are 4-byte UTF-8 chain ids,** not numeric chain IDs: `ETH`, `BSC`, `POL`, `AVA`, `CELO`, `FTM`, `HECO`, `SOL`, `TRA`, `TEZ` (trailing zero-padded to 4 bytes — e.g. `0x42534300` = `BSC`). Don't confuse with EVM `chainId`.
5. **`recipient` is `bytes32`,** right-zero-padded for chains with shorter addresses; for EVM the 20-byte address sits in the high bytes (left). For non-EVM destinations it is the full native address.
6. **Two `unlock` selectors.** Single-validator `unlock(...,bytes)` = `0x14b824e0`; Stellar-multisig `unlock(...,bytes,bytes)` = `0xb43d20c3`. The extra `bytes` is the secondary signature. Both emit the same `Received` topic0.
7. **No Ownable, no admin events.** Access control is `validator()`/`unlockSigner()`/`feeCollector()`/`feeOracle()` getters; there is no `owner()` and no ownership/role event — monitor these by reading the getters, not by log subscription.
8. **Wrapped vs native tokens behave differently on lock.** Native tokens are *locked* in the bridge (balance grows); wrapped representations are *burned* (no balance change). `tokenInfos(token)` distinguishes them. Don't infer "TVL change" from `Sent` alone.
9. **Still live despite "deprecated."** Recent `lock`/`unlock` activity confirmed on Ethereum (2026-06). Keep indexing it until the official mid-2026 shutdown.
10. **Counterparty chains span far outside EVM** — NEAR, Solana, Stacks, Stellar, XRPL, Tezos, Terra, HECO, Fantom, Celo (§3.2 / §6). A `Sent` with `destination = SOL`/`NEAR`/`XRP` is normal; the recipient is a non-EVM address in `bytes32`.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_CLASSIC_SENT            = '\x884a8def17f0d5bbb3fef53f3136b5320c9b39f75afb8985eeab9ea1153ee56d'
TOPIC_CLASSIC_RECEIVED        = '\xeeff8dc309b75f785752dd67594b2d8a3a9fd4ff6ecd65fcfe670cee0d851ce4'

-- ===== Selectors =====
SEL_CLASSIC_LOCK              = '\x7bacc91e'   -- lock(uint128,address,bytes32,bytes4,uint256)
SEL_CLASSIC_LOCK_BASE         = '\x5e3b0f9e'   -- lockBase(uint128,address,bytes32,bytes4)
SEL_CLASSIC_UNLOCK            = '\x14b824e0'   -- unlock(...,bytes)  single validator
SEL_CLASSIC_UNLOCK_MULTISIG   = '\xb43d20c3'   -- unlock(...,bytes,bytes)  Stellar multisig
SEL_CLASSIC_VALIDATOR         = '\x3a5381b5'
SEL_CLASSIC_UNLOCK_SIGNER     = '\x00c45c54'
SEL_CLASSIC_FEE_COLLECTOR     = '\xc415b95c'
SEL_CLASSIC_FEE_ORACLE        = '\x500b19e7'

-- ===== Proxy slot (reads 0x0 — immutable) =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'

-- ===== Addresses =====
-- Classic Bridge vanity (real bridge ONLY on ETH/BNB/Polygon/Avax; sweeper on Arb/Base; absent on OP)
CLASSIC_BRIDGE                = '\xbbbd1bbb4f9b936c3604906d7592a644071de884'
-- Ethereum roles
ETH_CLASSIC_VALIDATOR         = '\x93746538d4519c809827205bd1c2c7a0e15bd74b'
ETH_CLASSIC_UNLOCK_SIGNER     = '\x83f53c078bf81f6d8b79e01e2ed36c473a960c5e'
ETH_CLASSIC_FEE_COLLECTOR     = '\x83f53c078bf81f6d8b79e01e2ed36c473a960c5e'
ETH_CLASSIC_FEE_ORACLE        = '\xba6d8de08f13a3d22fcec54752812dd4dcf2e1f6'
```

---

## 8. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from the canonical `allbridge-io/allbridge-contract-docs` ABIs (`allbridge-abi.json`, `allbridge-multisig-abi.json`) — `Sent`/`Received` field types and `indexed` flags taken verbatim.
- **Live event cross-check (`eth_getLogs`):** on Ethereum the Classic Bridge `0xBBbD1Bbb…` emits `Received 0xeeff8dc3…` (recent unlocks, e.g. window blocks 25,269,761–25,279,261) and `Sent 0x884a8def…` (a lock at window 25,193,805–25,203,305) — both topic0s match the locally-computed values.
- **Addresses:** the single vanity Bridge address parsed from the official Classic contracts page (`docs.allbridge.io/allbridge-overview/bridge-contracts`). `eth_getCode` run on all seven chains → 19,273 B bridge on ETH/BNB/Polygon/Avax; 777 B non-bridge sweeper on Arbitrum/Base (selectors `withdraw()`/`owner()`/`transferOwnership`/`renounceOwnership`); `0x` on Optimism.
- **Roles:** `validator()`/`unlockSigner()`/`feeCollector()`/`feeOracle()` read via `eth_call` on Ethereum (returned non-zero addresses); there is no `owner()` (call returns empty).
- **Immutability:** EIP-1967 impl slot read live = `0x0` on ETH/BNB/Polygon/Avax → not a proxy.

**Authoritative sources:**
- Canonical ABI/docs: [`github.com/allbridge-io/allbridge-contract-docs`](https://github.com/allbridge-io/allbridge-contract-docs)
- Official docs: [`docs.allbridge.io`](https://docs.allbridge.io) · Classic contracts [`/allbridge-overview/bridge-contracts`](https://docs.allbridge.io/allbridge-overview/bridge-contracts)
- Explorer: [Etherscan Classic Bridge](https://etherscan.io/address/0xBBbD1BbB4f9b936C3604906D7592A644071dE884)
