# RetroBridge — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche; NOT Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the Sourcify-verified `RetroRouter` source (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB; solc 0.8.24), and RetroBridge's own bridge-indexer repository (`retro-bridge/DefiLlamaIndexer`, `src/adapters/retrobridge/index.ts`), which names the hot wallet and the router per chain.
**Scope:** the RetroBridge hot wallet (maker EOA) and the `RetroRouter` contract. Topics and selectors are chain-agnostic. Both addresses are the same on every target chain where RetroBridge is deployed.

RetroBridge is a **maker bridge**. A user creates an order in RetroBridge's backend, then sends the tokens or the native coin to the **hot wallet** `0x009905bf008CcA637185EEaFE8F51BB56dD2ACa7` on the source chain. RetroBridge pays the user from the same hot wallet on the destination chain. The destination chain and the recipient are **not encoded on chain**: they live in the off-chain order. There is no on-chain link key.

`RetroRouter` is an optional entry for integrator contracts ("allowed callers"). It forwards tokens or ETH to its `target` (the hot wallet) and emits `Transferred`. The router holds no funds.

**Status of the service:** on 2026-09-29 every RetroBridge backend host (`backend.retrobridge.io`, `docs.retrobridge.io`, `explorer.retrobridge.io`, `api-docs.retrobridge.io`, `api-journey.retrobridge.io`) failed to connect, and the front end loads without data. In the pinned window the router emitted 0 events and the hot wallet had 0 ERC-20 transfers on Ethereum and Base. Treat the service as inactive (unverified), but keep the hot wallet in monitors.

---

## 0. Components & flow

| Component | Address | Role |
|-----------|---------|------|
| **Hot wallet (maker EOA)** | `0x009905bf008CcA637185EEaFE8F51BB56dD2ACa7` | Receives deposits and sends payouts on every chain. |
| **RetroRouter** | `0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A` | Integrator entry: `transferToken` / `transferEther` move funds to `target` (= the hot wallet) and emit `Transferred`. `Ownable2Step`. |
| RetroRouter (zkSync Era, off-target) | `0x22158e226D68D91378f30Ae42b6F6a039bcCACf8` | listed by the indexer repository |

Flow:

1. **Source:** native transfer (no log) or ERC-20 `Transfer(user → hot wallet)`. Integrators: `RetroRouter.transferToken(sender, token, amount)` (ERC-20 `Transfer(caller → hot wallet)` + `Transferred`) or `transferEther(sender)` (`msg.value` forwarded + `Transferred`).
2. **Destination:** native transfer (no log) or ERC-20 `Transfer(hot wallet → recipient)`.
3. **Refund:** off chain, as a transfer from the hot wallet (unverified).

---

## 1. Topics (chain-agnostic)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x769254a71d2f67d8ac6cb44f2803c0d05cfbcf9effadb6a984f10ff9de3df6c3` | `Transferred(address sender, address target, address token, uint256 amount)` | RetroRouter. **No indexed parameters** (all in data). `sender` is the end user named by the integrator; `token` = `0x0000000000000000000000000000000000000000` for ETH. |
| `0xb1fad345c041edc6d18d00dbcb7122231db4e860bfc1e2ad36b339dd0ba5981c` | `AllowableTokenSet(address token, bool allowed)` | Admin |
| `0xf23be7877938c00dd0c460b58e62a4c4f54d9c054e0b9dbd259850bba0419ac9` | `AllowableCallerSet(address caller, bool allowed)` | Admin |
| `0x814250a3b8c79fcbe2ead2c131c952a278491c8f4322a79fe84b5040a810373e` | `TargetUpdated(address newTarget)` | Admin. **High severity**: redirects all router flow. |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` | Ownable2Step |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Ownable2Step |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20: the only log of a direct deposit or payout |

---

## 2. Function signatures (chain-agnostic)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf5537ede` | `transferToken(address sender, address token, uint256 amount)` | Allowed callers only. `safeTransferFrom(msg.sender → target)`. Emits `Transferred`. |
| `0x6b55e991` | `transferEther(address sender)` | Payable, allowed callers only. Forwards `msg.value` to `target`. Emits `Transferred`. |
| `0xff1f9c7a` | `setAllowedTokens(address[] tokens, bool allowed)` | Owner only. |
| `0x73f9a5d7` | `setAllowedCallers(address[] caller, bool allowed)` | Owner only. |
| `0xea1b495f` | `updateTarget(address newTarget)` | Owner only. Emits `TargetUpdated`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Owner only (two-step). |
| `0x79ba5097` | `acceptOwnership()` | Pending owner. |
| `0xd4b83992` | `target()` | View. Returns the hot wallet (read live on Ethereum and Base). |
| `0xcbe230c3` | `isAllowedToken(address)` | View. |
| `0xa6801258` | `isAllowedCaller(address)` | View. |
| `0x8da5cb5b` | `owner()` | View. |
| `0xe30c3978` | `pendingOwner()` | View. |
| `0xa9059cbb` | `transfer(address to, uint256 value)` | ERC-20 direct deposit to the hot wallet, and hot-wallet payouts. |

`renounceOwnership()` is overridden to revert.

---

## 3. Addresses — per chain

All existence-checked with `eth_getCode` on 2026-09-29.

| Chain | ID | Hot wallet `0x009905bf008CcA637185EEaFE8F51BB56dD2ACa7` | RetroRouter `0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A` |
|-------|----|------------------------------------------|---------------------------------------------|
| Ethereum | 1 | EOA, nonce 25112 | 3319 B, Sourcify-verified, `target()` = hot wallet |
| Base | 8453 | EOA, nonce 311665 | 3319 B, Sourcify-verified, `target()` = hot wallet |
| Arbitrum One | 42161 | EOA, nonce 305704 | 3319 B, Sourcify-verified |
| Optimism | 10 | EOA, nonce 292609 | 3319 B, Sourcify-verified |
| Polygon PoS | 137 | EOA, nonce 3994 | 3319 B, Sourcify-verified |
| BNB Smart Chain | 56 | EOA, nonce 5883 | 3319 B, Sourcify-verified |
| Avalanche C-Chain | 43114 | EOA, nonce 1116 | 3319 B, same code hash (not on Sourcify) |
| Robinhood Chain | 4663 | **nonce 0, no code** | **`0x` (not deployed)** |

The router has one code hash on all seven chains. Router owner (`owner()` on Ethereum) = EOA `0x385B1b18dEE2322078f8022cBaFB8505E6A9B3b9`, also the deployer (Ethereum deployment block 20,721,574).

---

## 4. Cross-chain summary

| Chain | ID | Hot wallet active | RetroRouter |
|-------|----|-------------------|-------------|
| Ethereum | 1 | yes | `0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A` |
| Base | 8453 | yes | `0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A` |
| Arbitrum One | 42161 | yes | `0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A` |
| Optimism | 10 | yes | `0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A` |
| Polygon PoS | 137 | yes | `0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A` |
| BNB Smart Chain | 56 | yes | `0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A` |
| Avalanche C-Chain | 43114 | yes | `0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A` |
| Robinhood Chain | 4663 | no | — |

The indexer repository also lists the same two addresses on Arbitrum Nova, Linea, Scroll, Polygon zkEVM, Manta, Mantle, Metis, Mode, Blast, Merlin, B², Bitlayer, X Layer, Taiko, zkLink, opBNB, Mint, Zora, Kroma, Gravity and BOB (off-target).

---

## 5. Proxies

None. `RetroRouter` is a plain `Ownable2Step` contract deployed by constructor (full 3319-byte runtime, no EIP-1967 implementation). It has no upgrade path. The owner can change `target`, the token allow-list and the caller allow-list. The hot wallet is an EOA.

---

## 6. Detection invariants & gotchas

1. **The main path has no RetroBridge event.** Deposits and payouts are plain transfers to and from the hot wallet. Capture native transfers and ERC-20 `Transfer` where `to` or `from` = `0x009905bf008CcA637185EEaFE8F51BB56dD2ACa7`.
2. **No on-chain destination, recipient or link key.** The order is in RetroBridge's backend. Do not try to decode the destination from the amount.
3. **`Transferred` is a common, unindexed event signature.** In the pinned window, unrelated contracts emitted it: `0x767fe9edc9e0df98e07454847909b5e959d7ca0e` on Ethereum (263 logs) and `0xe419fd4390792adb552f86c03f51428e347014be` / `0x9ac2a965f3e62a11e858aa69d1dbc96ebd7e424c` on BNB. None is in RetroBridge's lists. Always filter on emitter = the router.
4. **Router `Transferred.sender` is the user named by the integrator, not `tx.from`.** The ERC-20 `Transfer` comes from the integrator contract (`msg.sender`), not from the user.
5. **The hot wallet both receives and pays.** Direction tells deposit from payout. Large transfers out of the hot wallet are payouts or treasury moves.
6. **Admin triggers:** `TargetUpdated` (redirects router flow), `AllowableCallerSet`, `AllowableTokenSet`, `OwnershipTransferStarted` / `OwnershipTransferred`.
7. **Robinhood Chain:** no RetroBridge address has code or nonce there.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_RETRO_TRANSFERRED          = '\x769254a71d2f67d8ac6cb44f2803c0d05cfbcf9effadb6a984f10ff9de3df6c3'
TOPIC_RETRO_TARGET_UPDATED       = '\x814250a3b8c79fcbe2ead2c131c952a278491c8f4322a79fe84b5040a810373e'
TOPIC_RETRO_ALLOWABLE_CALLER_SET = '\xf23be7877938c00dd0c460b58e62a4c4f54d9c054e0b9dbd259850bba0419ac9'
TOPIC_RETRO_ALLOWABLE_TOKEN_SET  = '\xb1fad345c041edc6d18d00dbcb7122231db4e860bfc1e2ad36b339dd0ba5981c'
TOPIC_OWNERSHIP_TRANSFER_STARTED = '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors =====
SEL_RETRO_TRANSFER_TOKEN         = '\xf5537ede'
SEL_RETRO_TRANSFER_ETHER         = '\x6b55e991'
SEL_RETRO_UPDATE_TARGET          = '\xea1b495f'
SEL_RETRO_SET_ALLOWED_CALLERS    = '\x73f9a5d7'
SEL_RETRO_SET_ALLOWED_TOKENS     = '\xff1f9c7a'

-- ===== Hot wallet (EOA, same on the seven chains) =====
ETH_RETRO_HOT_WALLET_EOA         = '\x009905bf008cca637185eeafe8f51bb56dd2aca7'
BASE_RETRO_HOT_WALLET_EOA        = '\x009905bf008cca637185eeafe8f51bb56dd2aca7'
ARB_RETRO_HOT_WALLET_EOA         = '\x009905bf008cca637185eeafe8f51bb56dd2aca7'
OP_RETRO_HOT_WALLET_EOA          = '\x009905bf008cca637185eeafe8f51bb56dd2aca7'
POLY_RETRO_HOT_WALLET_EOA        = '\x009905bf008cca637185eeafe8f51bb56dd2aca7'
BNB_RETRO_HOT_WALLET_EOA         = '\x009905bf008cca637185eeafe8f51bb56dd2aca7'
AVAX_RETRO_HOT_WALLET_EOA        = '\x009905bf008cca637185eeafe8f51bb56dd2aca7'

-- ===== RetroRouter (same address on the seven chains) =====
ETH_RETRO_ROUTER                 = '\xdcd3979c23b0a375e276f33c65c70b4199d0af5a'
BASE_RETRO_ROUTER                = '\xdcd3979c23b0a375e276f33c65c70b4199d0af5a'
ARB_RETRO_ROUTER                 = '\xdcd3979c23b0a375e276f33c65c70b4199d0af5a'
OP_RETRO_ROUTER                  = '\xdcd3979c23b0a375e276f33c65c70b4199d0af5a'
POLY_RETRO_ROUTER                = '\xdcd3979c23b0a375e276f33c65c70b4199d0af5a'
BNB_RETRO_ROUTER                 = '\xdcd3979c23b0a375e276f33c65c70b4199d0af5a'
AVAX_RETRO_ROUTER                = '\xdcd3979c23b0a375e276f33c65c70b4199d0af5a'
ETH_RETRO_ROUTER_OWNER_EOA       = '\x385b1b18dee2322078f8022cbafb8505e6a9b3b9'
-- Robinhood Chain (4663): nothing deployed
```

---

## 8. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(sig)` from the Sourcify-verified `src/RetroRouter.sol` (Ethereum `0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A`, deployed by `0x385B1b18dEE2322078f8022cBaFB8505E6A9B3b9`) and the bundled OpenZeppelin `Ownable2Step`.
- **Addresses:** hot wallet and router from RetroBridge's own indexer repository (and the matching DefiLlama adapter). Existence-checked with `eth_getCode` on all eight chains. `target()` read live on Ethereum and Base; `owner()` read on Ethereum.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):** `Transferred` at the router: 0 on all seven chains (the 263 Ethereum and 5 BNB `Transferred` logs in the window came from the unrelated emitters of §6 item 3). ERC-20 transfers to or from the hot wallet on Ethereum and Base: 0. Native transfers were not counted (no logs). The hot-wallet nonces in §3 show heavy past use on the L2s.
- **Service availability:** HTTP connection attempts to the backend, docs and explorer hosts on 2026-09-29 all failed.

Authoritative sources:
- Repository — [retro-bridge/DefiLlamaIndexer](https://github.com/retro-bridge/DefiLlamaIndexer) (`src/adapters/retrobridge/index.ts`) · [retro-bridge/audit](https://github.com/retro-bridge/audit) (November 2023 audit)
- Verified source — Sourcify `RetroRouter` on chains 1, 8453, 42161, 10, 137, 56
- Third-party cross-check — [DefiLlama bridges-server RetroBridge adapter](https://github.com/DefiLlama/bridges-server/blob/master/src/adapters/retrobridge/index.ts)
- Explorers — [Etherscan hot wallet](https://etherscan.io/address/0x009905bf008CcA637185EEaFE8F51BB56dD2ACa7) · [Etherscan RetroRouter](https://etherscan.io/address/0xDcD3979c23B0A375e276f33c65c70b4199d0AF5A#code)
