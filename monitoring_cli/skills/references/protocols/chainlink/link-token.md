# Chainlink LINK Token (ERC-677) — Topics, Selectors, Addresses

**Status:** verified 2026-05-29. Addresses verified via `eth_getCode` (non-empty) + `symbol()` on each chain's publicnode RPC; topic0/selectors computed locally (keccak).
**Scope:** LINK on Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137).

LINK is an **ERC-677** token — ERC-20 plus `transferAndCall(address, uint256, bytes)`, which transfers and then calls `onTokenTransfer` on the recipient in one tx. Every Chainlink service that bills in LINK (VRF subscriptions, Automation funding, CCIP fees, Functions, Data Streams) is funded via `transferAndCall`, not `approve`+`transferFrom`. So to attribute LINK funding flows you must watch the **4-arg `Transfer(address,address,uint256,bytes)`** event, not just the standard 3-arg ERC-20 `Transfer`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | standard ERC-20 |
| `0xe19260aff97b920c7df27010903aeb9c8d2be5d310a2c67824cf3f15396e4c16` | `Transfer(address indexed from, address indexed to, uint256 value, bytes data)` | **ERC-677** — emitted by `transferAndCall`; the `data` carries the service payload (e.g. VRF `subId`) |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ERC-20 |

---

## 2. Function signatures (chain-agnostic)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4000aea0` | `transferAndCall(address to, uint256 value, bytes data)` → `bool` | **ERC-677** — the Chainlink funding primitive |
| `0xa4c0ed36` | `onTokenTransfer(address sender, uint256 value, bytes data)` | recipient-side callback (implemented by coordinators/registries) |
| `0xa9059cbb` | `transfer(address, uint256)` | ERC-20 |
| `0x23b872dd` | `transferFrom(address, address, uint256)` | ERC-20 |
| `0x095ea7b3` | `approve(address, uint256)` | ERC-20 |
| `0x70a08231` | `balanceOf(address)` | ERC-20 |
| `0xdd62ed3e` | `allowance(address, address)` | ERC-20 |
| `0xd73dd623` | `increaseApproval(address, uint256)` | LINK uses the legacy `increase/decreaseApproval`, **not** EIP-2612 `permit` |
| `0x313ce567` | `decimals()` → `18` | |

---

## 3. LINK addresses per chain

All verified via `eth_getCode` + `symbol()`.

| Chain (id) | LINK address | symbol | Type |
|------------|--------------|--------|------|
| Ethereum (1) | `0x514910771AF9Ca656af840dff83E8264EcF986CA` | LINK | canonical native ERC-677 |
| Base (8453) | `0x88Fb150BDc53A65fe94Dea0c9BA0a6dAf8C6e196` | LINK | native (CCIP-issued ERC-677) |
| BNB (56) | `0x404460C6A5EdE2D891e8297795264fDe62ADBB75` | LINK | official ERC-677 *(the bridge-LINK variant is NOT 677-compatible — use PegSwap)* |
| Avalanche (43114) | `0x5947BB275c521040051D82396192181b413227A3` | **LINK.e** | bridged (Avalanche Bridge `.e`), ERC-677-compatible, used by Chainlink services |
| Arbitrum One (42161) | `0xf97f4df75117a78c1A5a0DBb814Af92458539FB4` | LINK | native (Arbitrum gateway) |
| Optimism (10) | `0x350a791Bfc2C21F9Ed5d10980Dad2e2638ffa7f6` | LINK | native |
| Polygon PoS (137) | `0xb0897686c545045aFc77CF20eC7A532E3120E0F1` | LINK | ERC-677 (canonical for Chainlink) |

---

## 4. PegSwap (bridged-LINK → ERC-677 LINK, 1:1)

On chains where the canonical bridge produces a **non-ERC-677** LINK, Chainlink services require the ERC-677 token; **PegSwap** swaps 1:1.

| Chain | PegSwap | Verified |
|-------|---------|----------|
| BNB (56) | `0x1FCc3B22955e76Ca48bF025f1A6993685975Bb9e` | ✅ (6846 B) |
| Polygon PoS (137) | `0xAA1DC356dc4B18f30C347798FD5379F3D77ABC5b` | ✅ (6846 B) |

> **Polygon has two LINK tokens.** The Chainlink-canonical one is the **ERC-677** token `0xb0897686c545045aFc77CF20eC7A532E3120E0F1` (table above). The **Polygon PoS-bridge LINK** `0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39` (also symbol LINK, also deployed) is **NOT** 677-compatible — bridge it through PegSwap before funding Chainlink services. Same pattern on BNB.

---

## 5. Detection invariants & gotchas

1. **Funding = `transferAndCall`, not `approve`.** Watch the 4-arg `Transfer` (`0xe19260af…`) to/from a Chainlink coordinator/registry/router to attribute VRF/Automation/CCIP/Functions funding. The `data` field decodes to the service-specific payload (e.g. `abi.encode(subId)` for VRF).
2. **Both `Transfer` topics fire on a `transferAndCall`?** No — ERC-677 LINK emits **only** the 4-arg `Transfer`; a plain `transfer()` emits the 3-arg one. Index both topic0s to capture all movement.
3. **LINK has no EIP-2612 `permit`** — it predates it. It exposes `increaseApproval`/`decreaseApproval`. Don't expect `permit`/`DOMAIN_SEPARATOR`.
4. **`LINK.e` (Avalanche) and bridged LINK differ from native LINK by address** — always key by `(chainId, address)`; never assume the Ethereum address.
5. **PegSwap is required on BNB & Polygon** if a user holds the wrong LINK variant — a common "why won't my VRF sub fund" support issue.

---

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- topics
TRANSFER_ERC20   = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TRANSFER_ERC677  = '\xe19260aff97b920c7df27010903aeb9c8d2be5d310a2c67824cf3f15396e4c16'
APPROVAL         = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
-- selectors
SEL_TRANSFER_AND_CALL = '\x4000aea0'
SEL_ON_TOKEN_TRANSFER = '\xa4c0ed36'
-- LINK addresses
ETH_LINK   = '\x514910771af9ca656af840dff83e8264ecf986ca'
BASE_LINK  = '\x88fb150bdc53a65fe94dea0c9ba0a6daf8c6e196'
BNB_LINK   = '\x404460c6a5ede2d891e8297795264fde62adbb75'
AVAX_LINK  = '\x5947bb275c521040051d82396192181b413227a3'
ARB_LINK   = '\xf97f4df75117a78c1a5a0dbb814af92458539fb4'
OP_LINK    = '\x350a791bfc2c21f9ed5d10980dad2e2638ffa7f6'
POL_LINK   = '\xb0897686c545045afc77cf20ec7a532e3120e0f1'
-- pegswap
BNB_PEGSWAP = '\x1fcc3b22955e76ca48bf025f1a6993685975bb9e'
POL_PEGSWAP = '\xaa1dc356dc4b18f30c347798fd5379f3d77abc5b'
```

---

## 7. Verification & sources

- **Addresses:** `eth_getCode` (non-empty) + `symbol()` on the 7 publicnode RPCs; PegSwap verified (6846 B on both BNB and Polygon).
- **Topic0 / selectors:** computed locally (keccak); `transferAndCall` `0x4000aea0` and the 4-arg `Transfer` `0xe19260af…` are the canonical ERC-677 values.
- Sources: [LINK token contracts](https://docs.chain.link/resources/link-token-contracts) · `smartcontractkit/chainlink` `contracts/src/v0.8/shared/token/ERC677/`.
