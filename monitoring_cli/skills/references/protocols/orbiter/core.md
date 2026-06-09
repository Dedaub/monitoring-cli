# Orbiter Finance Core (Routers + Maker EOAs + OPool) — Topics, Selectors, Addresses (Ethereum, Arbitrum, Optimism, Polygon, BNB, Base)

**Status:** verified against live RPC on all six EVM target chains, the Sourcify-verified `OrbiterXRouter` source on Ethereum mainnet, the `Orbiter-Finance/OB_ReturnCabin` repo (`OBSource.sol` legacy router), and live `eth_getCode`/`eth_getStorageAt` reads on 2026-06-09. The decentralized arbitration / Maker-Deposit-Contract framework is documented separately in [mdc.md](./mdc.md).
**Scope:** the production cross-rollup bridge surface — the on-chain `OrbiterXRouter` (a.k.a. "OrbiterRouterV3"), the legacy `OBSource` router, the `OPool` maker-liquidity pool, and the off-chain **Maker EOAs** that actually receive/send bridged funds. Topics + selectors are **chain-agnostic**; addresses are network-specific. **Not deployed on Avalanche C-Chain** (`eth_getCode` = `0x` for every Orbiter address there).

Orbiter Finance is a **cross-rollup bridge with an optimistic / off-chain-relayer design**. The defining architectural fact a monitoring engineer must internalize: **most Orbiter volume is plain EOA-to-EOA transfers, not contract calls.** A user sends native coin or an ERC-20 *directly to a Maker's externally-owned address* (the explorer-labelled "Orbiter Finance: Bridge N" wallets), encoding the destination chain in the **trailing digits of the transfer amount** (the "identification code", e.g. `…9001` for one chain, `…9002` for another). The Maker's off-chain backend watches its EOA, decodes the destination, and pays out on the target chain from the *same Maker EOA* (or from `OPool`). The on-chain `OrbiterXRouter` is an **optional convenience wrapper**: it forwards the user's funds to the Maker EOA in one call and (for native transfers only) emits a single `Transfer(to, amount)` event; it holds no funds and has no owner. The `data` blob passed to the router carries the destination/identification code so the router transfer is indistinguishable downstream from a direct EOA send.

**Every contract here is immutable and non-upgradeable** — no proxies, no admin/impl slots, no governance on the routers. The router is a CREATE2/plain deploy that is **byte-for-byte identical on all six EVM chains** (runtime sha256 `27f13214…`, 3183 bytes). It has **unique addresses on Ethereum / Arbitrum / Optimism / Polygon** but a **single shared address `0x13e46b2a…` on BNB + Base** (and, off-target, on Scroll/Linea/Mantle/Blast/Polygon-zkEVM). `OPool` exists on **Arbitrum + BNB only**.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Verified name | Where |
|----------|------|--------|---------------|-------|
| **OrbiterXRouter** ("OrbiterRouterV3") | Multicall transfer wrapper: single + batch native and ERC-20 forwards to the Maker. Native path emits `Transfer`; token path does not. | **No** (immutable, 3183 B, no owner) | `OrbiterXRouter` (Sourcify exact-match, solc 0.8.19) | ETH, ARB, OP, POLY, BNB, Base |
| **OBSource** (legacy "V1" router) | Original router: `transfer(address,bytes)` + `transferERC20(...)`. No events. Superseded by OrbiterXRouter. | **No** (immutable) | `OBSource` (in `OB_ReturnCabin/contracts/OBSource.sol`) | historical; same `transfer` selector as V3 |
| **OPool** | Maker **liquidity pool**: makers/managers pay out destination transfers via `outbox`/`outboxBatch` from pooled funds instead of from a bare EOA. `Ownable`. | **No** (immutable, 5454 B) | unverified on Sourcify; bytecode/selector-confirmed | **ARB + BNB only** |
| **Maker EOAs** ("Orbiter Finance: Bridge N") | The actual liquidity-provider wallets that receive user deposits and send payouts. **Plain EOAs** (`eth_getCode` = `0x`), same address re-used across chains. | n/a (EOA) | — | all chains |

> `transfer(address,bytes)` shares the selector `0x29723511` between **OBSource (V1)** and **OrbiterXRouter (V3)** — the canonical signature is identical, so the selector alone does not tell you which router generation you are looking at. Disambiguate by the **contract address** / bytecode.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 OrbiterXRouter ("OrbiterRouterV3")

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x69ca02dd4edd7bf0a4abb9ed3b7af3f14778db5d61921c7dc7cd545266326de2` | `Transfer(address indexed to, uint256 amount)` | **Only emitted by the native paths** (`transfer`, `transfers`) — one log per recipient with `to` = Maker EOA, `amount` = native value. **NOT a standard ERC-20 `Transfer`** (that is `0xddf252ad…` with 3 args). |

**The ERC-20 paths (`transferToken`, `transferTokens`) emit NO router event** — they call `token.safeTransferFrom(user → maker)`, so the only on-chain log is the underlying token's own `Transfer(address,address,uint256)` (`0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`). This is why the router's own event is rare in logs even on high-volume chains.

### 1.2 OBSource (legacy router)

No events. `transfer` does a raw `call{value}` and `transferERC20` does a bare `transferFrom`; neither emits.

### 1.3 OPool

No custom events declared; `outbox`/`outboxBatch` move ERC-20s (underlying token `Transfer` only). Ownership changes emit the OZ `OwnershipTransferred(address,address)` (`0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0`).

> **There is no Orbiter-specific bridge event for the dominant flow.** A Maker-EOA deposit is just a native send (no log at all) or an ERC-20 `Transfer` to the Maker. Attribution to "Orbiter" is by **counterparty address** (Maker EOA / router / OPool), not by a topic. See §8.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 OrbiterXRouter ("OrbiterRouterV3") — all 4 functions, all `payable`, `nonReentrant`

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x29723511` | `transfer(address to, bytes data)` | Native single. `payable(to).transfer(msg.value)`; emits `Transfer(to,msg.value)`. `to` = Maker EOA; `data` carries the identification/destination code. |
| `0x52346412` | `transfers(address[] tos, uint256[] values)` | Native batch. Requires `sum(values) == msg.value` exactly; emits `Transfer` per recipient. |
| `0xf9c028ec` | `transferToken(address token, address to, uint256 value, bytes data)` | ERC-20 single. `requires msg.value == 0`; `safeTransferFrom(msg.sender → to)`. **No router event.** |
| `0xd54cefc1` | `transferTokens(address token, address[] tos, uint256[] values)` | ERC-20 batch. **No router event.** |

The four selectors `0x29723511 / 0x52346412 / 0xf9c028ec / 0xd54cefc1` are confirmed present in the live router bytecode on every chain (PUSH4 dispatch scan). The router has **no** `owner()`/`Ownable` (selector `0x8da5cb5b` absent in bytecode) — only a `bool locked` reentrancy guard at storage slot 0.

### 2.2 OBSource (legacy router)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x29723511` | `transfer(address to, bytes ext)` | Native. Raw `to.call{value:msg.value}("")`. **Same selector as V3** `transfer`. |
| `0x46f506ad` | `transferERC20(address token, address to, uint256 amount, bytes ext)` | ERC-20 via `transferFrom`. **Different selector from V3** `transferToken` (`0xf9c028ec`) — the param order/types differ. |

### 2.3 OPool (maker liquidity pool — `Ownable`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc86238d3` | `outbox(address token, address to, uint256 amount, bytes data)` | Maker payout of a single destination transfer from pool liquidity. |
| `0x809bb9cd` | `outboxBatch(address token, address[] to, uint256[] amounts, bytes[] data)` | Batched maker payouts. |
| `0xf3fef3a3` | `withdraw(address token, uint256 amount)` | Pull liquidity out of the pool. |
| `0xb22b6094` | `setMakerList(address[] makers, bool[] statuses)` | Owner: authorise/deauthorise maker addresses. |
| `0x0a7bf733` | `setManagerList(address[] managers, address[] ...)` | Owner: manager roles. |
| `0xc21b47fb` | `setTokenReceiver(address[] tokens, address[] receivers)` | Owner: per-token receiver routing. |
| `0x7e22e3a6` | `makerList(address)` → `bool/...` | View: maker authorisation. |
| `0xa59be4c7` | `managerList(address)` → `...` | View: manager. |
| `0x19096f0c` | `tokenReceivers(address)` → `address` | View: per-token receiver. |
| `0x8da5cb5b` | `owner()` → `address` | OZ `Ownable`; live value `0x09053d505447191060b0e0720a8b255a00aaedd8` (same on ARB + BNB). |
| `0xf2fde38b` / `0x715018a6` | `transferOwnership(address)` / `renounceOwnership()` | OZ `Ownable`. |

Three further dispatch selectors (`0x884ae7d4`, `0xb155b156`, `0x3146104a`) appear in the OPool bytecode but were not resolvable against the public signature database; they are minor view/admin helpers (OPool source is not verified on a public registry). Treat the verified `outbox`/`outboxBatch`/`withdraw`/`setMakerList` set as the monitoring surface.

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0xc741900276cd598060b0fe6594fbe977392928f4` | Verified `OrbiterXRouter`, solc 0.8.19; immutable; deployer `0x8a700FdB6121a57c59736041d9aa21dFd8820660`. 3183 B. |
| Maker EOAs ("Bridge N") | `0x80c67432656d59144ceff962e8faf8926599bcf8` (Bridge 1) · `0xe4edb277e41dc89ab076a1f049f4a3efa700bce8` (Bridge 2) · `0x41d3d33156ae7c62c094aae2995003ae63f587b3` · `0xacc517ea627ceb71cf25e002adaa9761623837b9` (Bridge 4) · `0x9c6750d463ad17deec97a630af766f0a78f95127` (Bridge 5) | **Plain EOAs** (`eth_getCode`=`0x`). Same addresses re-used on ARB/OP/Base/etc. The real source/sink of bridged funds. |
| **OPool** | — | **Not deployed on Ethereum** (`0x6285a466…` returns `0x` here). |

---

## 4. Addresses — Arbitrum One (chain ID 42161)

Verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0x6a065083886ec63d274b8e1fe19ae2ddf498bfdd` | Identical bytecode to ETH (sha `27f13214…`). Unique per-chain address. |
| **OPool** | `0x6285a466a98f513e1f6be29acad27d173d3b3c59` | Maker liquidity pool, 5454 B; `owner()` = `0x09053d50…aaedd8`. Shared CREATE2 address with BNB. |
| Maker EOAs | same as §3 (`0x80c67432…`, `0xe4edb277…`, …) | EOAs. |

---

## 5. Addresses — Optimism (chain ID 10)

Verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0x3191f40de6991b1bb1f61b7cec43d62bb337786b` | Identical bytecode; unique per-chain address. |
| **OPool** | — | **Not deployed** (`0x6285a466…` = `0x`). |
| Maker EOAs | same as §3 | EOAs. |

---

## 6. Addresses — Polygon PoS (chain ID 137)

Verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0x653f25dc641544675338cb47057f8ea530c69b78` | Identical bytecode; unique per-chain address. |
| **OPool** | — | **Not deployed** (`0x6285a466…` = `0x`). |
| Maker EOAs | same as §3 | EOAs. |

---

## 7. Addresses — BNB Smart Chain (chain ID 56)

Verified via `eth_getCode` on `https://bsc-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` | **Shared CREATE2 address with Base** (and off-target Scroll/Linea/Mantle/Blast/Polygon-zkEVM). Identical bytecode. |
| **OPool** | `0x6285a466a98f513e1f6be29acad27d173d3b3c59` | Maker liquidity pool; `owner()` = `0x09053d50…aaedd8`. Shared address with Arbitrum. |
| Maker EOAs | same as §3 | EOAs. |

---

## 8. Addresses — Base (chain ID 8453)

Verified via `eth_getCode` on `https://base-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` | **Shared CREATE2 address with BNB.** Identical bytecode. |
| **OPool** | — | **Not deployed** (`0x6285a466…` = `0x`). |
| Maker EOAs | same as §3 | EOAs. |

---

## 9. Addresses — Avalanche C-Chain (chain ID 43114) — NOT DEPLOYED

Verified via `eth_getCode` on `https://avalanche-c-chain-rpc.publicnode.com`: **every** Orbiter address — the four router literals (`0xc741…`, `0x6a06…`, `0x3191…`, `0x653f…`, `0x13e46b…`) and `OPool` (`0x6285a466…`) — returns `0x`. **Orbiter has no on-chain core contracts on Avalanche.** Avalanche C-Chain is supported by Orbiter only via the **Maker-EOA flow** (a user sends to the Maker EOA directly; there is no router to wrap it).

---

## 10. Cross-chain summary

| Chain | ID | OrbiterXRouter (V3) | OPool | Maker EOAs |
|---|---|---|---|---|
| Ethereum | 1 | `0xc741900276cd598060b0fe6594fbe977392928f4` | ✗ | ✓ (same set) |
| Arbitrum One | 42161 | `0x6a065083886ec63d274b8e1fe19ae2ddf498bfdd` | `0x6285a466…3b3c59` | ✓ |
| Optimism | 10 | `0x3191f40de6991b1bb1f61b7cec43d62bb337786b` | ✗ | ✓ |
| Polygon PoS | 137 | `0x653f25dc641544675338cb47057f8ea530c69b78` | ✗ | ✓ |
| BNB Smart Chain | 56 | `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` ⟂ | `0x6285a466…3b3c59` | ✓ |
| Base | 8453 | `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` ⟂ | ✗ | ✓ |
| **Avalanche** | 43114 | **✗ (0x)** | **✗ (0x)** | ✓ (EOA only) |

⟂ = the **shared** router address `0x13e46b2a…` (BNB + Base; also off-target Scroll/Linea/Mantle/Blast/Polygon-zkEVM). ETH/ARB/OP/POLY each have a **unique** router address but **identical bytecode** (runtime sha256 `27f13214…`). `OPool` (`0x6285a466…`) is **ARB + BNB only**.

**Vanity / tell:** there is no protocol-wide vanity prefix; the only address-level tell is the **shared CREATE2 router `0x13e46b2a…`** and **shared OPool `0x6285a466…`**. The Maker EOAs are explorer-labelled "Orbiter Finance: Bridge N" and are the highest-signal attribution anchor.

**Counterparty chains OUTSIDE the seven (this is a finding, not an omission):** Orbiter is a 40+-chain bridge. Beyond the seven targets it connects (with the same router on most): **zkSync Era (324), Polygon zkEVM (1101), Scroll, Linea, Mantle, Blast (81457), Arbitrum Nova, Manta, Mode, Taiko, Zora, Kroma, ZKFair, zkLink Nova, Merlin, BEVM, BOB, Core, Bitlayer, Fraxtal, Fuse, Gravity, Zircuit, Cyber, Mint, Optopia** and non-EVM **StarkNet** (Cairo `StarknetOrbiterRouter` at `0x058680be0cf3f29c7a33474a218e5fed1ad213051cb2e9eac501a26852d64ca2`), plus partially-supported **Solana / TON / Immutable X / Loopring / ZKSpace**. A transfer from one of the seven target chains very often has its **counterparty on an off-target chain** — decode the destination from the amount's identification-code suffix, do not assume the other leg is on a target chain.

---

## 11. Proxies (old & new)

**There are none.** Every Orbiter core contract is an immutable, non-upgradeable deployment.

| Contract | Pattern | Detection (2026-06-09) | Upgrade auth |
|----------|---------|------------------------|--------------|
| OrbiterXRouter (all 6 chains) | **Immutable, non-proxy** | EIP-1967 impl slot `0x3608…2bbc` = `0x000…0` on ETH/ARB/OP/POLY/BNB/Base; no `owner()` selector in bytecode; 3183 B full contract. | none (no owner, no admin). |
| OBSource (legacy) | **Immutable, non-proxy** | full contract; no admin. | none. |
| OPool (ARB, BNB) | **Immutable, non-proxy** | EIP-1967 impl slot = `0x000…0`; 5454 B full contract; has `owner()` (Ownable) but **no upgrade path**. | `owner()` = `0x09053d50…aaedd8` (param-setting only: maker/manager/receiver lists; **cannot** swap implementation). |
| Maker EOAs | n/a (EOA) | `eth_getCode` = `0x`. | controlled by the off-chain Maker keypair. |

There is **no `Upgraded(address)` event to watch** on any core contract (none are proxies). The only governance-ish on-chain action is `OPool` owner calling `setMakerList`/`setManagerList`/`setTokenReceiver` (and possible `transferOwnership`, topic `0x8be0079c…`).

---

## 12. Detection invariants & gotchas

1. **The dominant flow is EOA→EOA, with NO Orbiter event and often NO log at all.** A native deposit to a Maker EOA produces zero logs; an ERC-20 deposit produces only the *token's* `Transfer`. **Attribute to Orbiter by counterparty address** (Maker EOA, router, or OPool) — there is no "bridge" topic to filter on for the main path.
2. **The destination chain is encoded in the trailing digits of the amount** (the "identification code", typically the last 4 digits, e.g. `…9001`/`…9002`/`…9014`). The real transferred value is `amount` minus that suffix's information. Do not treat the raw amount as the user's intended round number; the suffix is intentional.
3. **The `to` in the router `Transfer` event is the Maker EOA, not the end-user.** The end-user is `tx.from` / `msg.sender`. For ERC-20 paths there is no router event at all; read the user from the token `Transfer.from` and the maker from `Transfer.to`.
4. **`transfer(address,bytes)` selector `0x29723511` is shared by OBSource (V1) and OrbiterXRouter (V3).** Same canonical signature ⇒ same selector. Disambiguate the generation by the **contract address**, never by the selector.
5. **ERC-20 router selectors differ between generations:** V3 `transferToken` = `0xf9c028ec`; V1 `transferERC20` = `0x46f506ad`. If you key the legacy path on `0xf9c028ec` you will miss old OBSource flows and vice-versa.
6. **The router `Transfer` topic `0x69ca02dd…` is NOT the ERC-20 `Transfer` topic `0xddf252ad…`.** Different arg count (2 vs 3). Both may appear in the same tx (router event + token event); key the router event on the router address.
7. **Token-path transfers (`transferToken`/`transferTokens`, `OPool.outbox*`) emit no Orbiter event.** Indexing only on the router `Transfer` topic captures *native* flows only and silently drops every ERC-20 bridge. Cover ERC-20 by watching token `Transfer` logs where `to` ∈ {Maker EOAs, OPool}.
8. **`OPool` is the maker-pays-from-pool variant** (ARB + BNB only). A payout via `outbox`/`outboxBatch` originates from `0x6285a466…`, not from a Maker EOA — include OPool as a payout source/sink alongside the Maker EOAs.
9. **Same router bytecode, different addresses.** ETH/ARB/OP/POLY have unique router addresses; BNB+Base share `0x13e46b2a…`. **Always key on `(chainId, address)`** — `0x13e46b2a…` is the same literal on BNB, Base, and several off-target chains.
10. **`OPool` shares `0x6285a466…` on ARB + BNB**, and its `owner()` is the same `0x09053d50…aaedd8` on both — but they are independent deployments; key on `(chainId, address)`.
11. **Avalanche has no Orbiter contract.** Any "Orbiter on Avalanche" activity is a direct Maker-EOA send; do not look for a router/OPool there (`0x` everywhere).
12. **Maker EOAs are reused across chains** (`0x80c67432…` is "Bridge 1" on ETH, ARB, OP, …). The full live Maker set rotates over time and is best sourced from the explorer "Orbiter Finance: Bridge N" labels; treat the §3 list as a seed, not exhaustive.
13. **No proxies, no `Upgraded` event, no liquidation/borrow semantics.** This is a bridge router, not a lending or AMM protocol — the only state-changing admin action on-chain is `OPool` owner list-setting.
14. **The on-chain decentralized arbitration system (ORMDCFactory / ORManager / ORMakerDeposit) is a SEPARATE framework** — see [mdc.md](./mdc.md). It is *not* in the dominant transfer path; the live bridge runs on the EOA + router model documented here.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- OrbiterXRouter native-path event (2-arg; NOT the ERC-20 Transfer)
TOPIC_ORBITER_TRANSFER        = '\x69ca02dd4edd7bf0a4abb9ed3b7af3f14778db5d61921c7dc7cd545266326de2'
-- underlying ERC-20 Transfer (the only log on the token path)
TOPIC_ERC20_TRANSFER          = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- OPool / OZ Ownable
TOPIC_OWNERSHIP_TRANSFERRED   = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'

-- ===== Selectors — OrbiterXRouter (V3) =====
SEL_TRANSFER                  = '\x29723511'   -- transfer(address,bytes)  [shared with OBSource V1]
SEL_TRANSFERS                 = '\x52346412'   -- transfers(address[],uint256[])
SEL_TRANSFER_TOKEN            = '\xf9c028ec'   -- transferToken(address,address,uint256,bytes)
SEL_TRANSFER_TOKENS           = '\xd54cefc1'   -- transferTokens(address,address[],uint256[])
-- OBSource (legacy V1)
SEL_OBSOURCE_TRANSFER_ERC20   = '\x46f506ad'   -- transferERC20(address,address,uint256,bytes)
-- OPool
SEL_OPOOL_OUTBOX              = '\xc86238d3'   -- outbox(address,address,uint256,bytes)
SEL_OPOOL_OUTBOX_BATCH        = '\x809bb9cd'   -- outboxBatch(address,address[],uint256[],bytes[])
SEL_OPOOL_WITHDRAW            = '\xf3fef3a3'   -- withdraw(address,uint256)
SEL_OPOOL_SET_MAKER_LIST      = '\xb22b6094'   -- setMakerList(address[],bool[])
SEL_OPOOL_SET_MANAGER_LIST    = '\x0a7bf733'   -- setManagerList(address[],address[])
SEL_OPOOL_SET_TOKEN_RECEIVER  = '\xc21b47fb'   -- setTokenReceiver(address[],address[])
SEL_OWNER                     = '\x8da5cb5b'   -- owner()
SEL_TRANSFER_OWNERSHIP        = '\xf2fde38b'   -- transferOwnership(address)

-- ===== Proxy slots (all read 0x0 -> NOT proxies) =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT            = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses — OrbiterXRouter (V3) per chain =====
ETH_ROUTER_V3                 = '\xc741900276cd598060b0fe6594fbe977392928f4'
ARB_ROUTER_V3                 = '\x6a065083886ec63d274b8e1fe19ae2ddf498bfdd'
OP_ROUTER_V3                  = '\x3191f40de6991b1bb1f61b7cec43d62bb337786b'
POLY_ROUTER_V3                = '\x653f25dc641544675338cb47057f8ea530c69b78'
BNB_ROUTER_V3                 = '\x13e46b2a3f8512ed4682a8fb8b560589fe3c2172'   -- shared with Base
BASE_ROUTER_V3                = '\x13e46b2a3f8512ed4682a8fb8b560589fe3c2172'   -- shared with BNB
-- AVAX: no router (0x)

-- ===== Addresses — OPool (ARB + BNB only) =====
ARB_OPOOL                     = '\x6285a466a98f513e1f6be29acad27d173d3b3c59'
BNB_OPOOL                     = '\x6285a466a98f513e1f6be29acad27d173d3b3c59'
OPOOL_OWNER                   = '\x09053d505447191060b0e0720a8b255a00aaedd8'

-- ===== Maker EOAs ("Orbiter Finance: Bridge N") — reused across chains =====
MAKER_BRIDGE_1                = '\x80c67432656d59144ceff962e8faf8926599bcf8'
MAKER_BRIDGE_2                = '\xe4edb277e41dc89ab076a1f049f4a3efa700bce8'
MAKER_BRIDGE_3               = '\x41d3d33156ae7c62c094aae2995003ae63f587b3'
MAKER_BRIDGE_4                = '\xacc517ea627ceb71cf25e002adaa9761623837b9'
MAKER_BRIDGE_5                = '\x9c6750d463ad17deec97a630af766f0a78f95127'

-- ===== Deployer =====
ROUTER_DEPLOYER               = '\x8a700fdb6121a57c59736041d9aa21dfd8820660'
```

---

## 14. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors** recomputed locally as `keccak256(canonical signature)` (and `[0:4]` for selectors) and cross-checked against the **Sourcify-verified `OrbiterXRouter` ABI** (Ethereum mainnet, exact runtime match, solc 0.8.19+commit.7dd6d404) and the four dispatch selectors observed in the live router bytecode (PUSH4 scan): `0x29723511`, `0x52346412`, `0xf9c028ec`, `0xd54cefc1`. OPool selectors recomputed locally and cross-checked against the public 4-byte signature database (`outbox`, `outboxBatch`, `withdraw`, `setMakerList`, `setManagerList`, `setTokenReceiver`) and the live OPool bytecode.
- **OrbiterXRouter source** read from Sourcify v2 (`/v2/contract/1/0xc741…928f4?fields=abi,sources`): confirms `event Transfer(address indexed to, uint256 amount)`, the four `payable nonReentrant` functions, the `bool locked` guard, and that the native paths emit while the token paths do not. `OBSource.sol` (legacy router) read from the same source bundle.
- **Addresses** parsed from the official `docs.orbiter.finance` Smart Contract mainnet table and existence-checked via `eth_getCode` on each chain's publicnode RPC. Router runtime bytecode is byte-identical across all six EVM chains (sha256 `27f13214…`, 3183 bytes). OPool present only on Arbitrum + BNB (5454 bytes); absent (`0x`) on ETH/OP/Polygon/Base/Avax. **Every** Orbiter address returns `0x` on Avalanche C-Chain.
- **Proxy classification** by reading the EIP-1967 implementation slot `0x3608…2bbc` live on each router and on OPool — all return `0x000…0`, confirming **non-proxy / immutable**. The router additionally has no `owner()` selector in bytecode (no Ownable). OPool `owner()` read live via `eth_call(0x8da5cb5b)` = `0x09053d50…aaedd8` on both ARB and BNB.
- **Maker EOAs** confirmed as plain EOAs (`eth_getCode` = `0x` on ETH/OP/ARB) and matched to the explorer "Orbiter Finance: Bridge N" labels.

Authoritative sources:
- Official docs — [Smart Contract addresses](https://docs.orbiter.finance/developer/smart-contract) · [Orbiter Router](https://docs.orbiter.finance/developer/smart-contract/orbiter-router) · [Bridge Protocol](https://docs.orbiter.finance/welcome/bridge-protocol)
- Verified source — Sourcify `OrbiterXRouter` (chain 1, `0xc741900276cd598060b0fe6594fbe977392928f4`); `Orbiter-Finance/OB_ReturnCabin` repo (`contracts/OBSource.sol`).
- Explorers — [Etherscan router](https://etherscan.io/address/0xc741900276cd598060b0fe6594fbe977392928f4) · [Arbiscan OPool](https://arbiscan.io/address/0x6285a466a98f513e1f6be29acad27d173d3b3c59) · [Etherscan "Orbiter Finance: Bridge"](https://etherscan.io/address/0x80c67432656d59144ceff962e8faf8926599bcf8)
