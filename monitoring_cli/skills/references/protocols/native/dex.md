# Native — Swap Engine (NativeRouter V3/V4, NativeRFQPool, NativeBridge) — Topics, Selectors, Addresses

**Status:** verified against live RPC on Ethereum (1), Base (8453), BNB Smart Chain (56), Arbitrum One (42161), Avalanche C-Chain (43114), Optimism (10), Polygon PoS (137), plus Sourcify-verified ABIs and the `Native-org/native-v2-core` repo, on 2026-06-02.

**Scope:** the **Native Swap Engine** (DEX/RFQ side) only — `NativeRouter` (V3 and V4), `NativeRFQPool` ("NativePool" / credit pool), and `NativeBridge`. Topics + selectors are **chain-agnostic**; addresses are network-specific. **Boundary:** the lending / Credit-Pool side (`CreditVault`, `NativeLPToken`) is covered by a separate reference and is intentionally NOT detailed here — but note that every Router/Pool/Bridge in this file points its `vault()` / `treasury()` at the chain's `CreditVault`, which is the seam between the two halves (see §"Detection invariants").

Native is a **request-for-quote (RFQ) / PMM DEX backed by an on-chain credit pool**, not an AMM. There is no constant-product pool, no `PoolCreated` factory, no tick math. Instead: an off-chain market maker signs a firm quote (EIP-712), the swapper submits it to `NativeRouter.tradeRFQT(...)`, the router forwards to a registered `NativeRFQPool` (a "credit pool"), and the pool pulls market-maker inventory out of the `CreditVault` and settles atomically. The pool emits `RFQTrade`; the router itself emits **no** swap event in the base RFQ path (the trade event lives on the pool). V4 adds an **AMM-fallback** path (`externalSwap` → `ExternalSwapped`) and "external swap sources" allowlisting on top of the V3 RFQ-only surface. `NativeBridge` is a separate cross-chain intent/settlement contract (escrow + market-maker fill + refund) wired to the same per-chain Router and CreditVault.

There is **no proxy anywhere in the swap engine** — Router V3, Router V4, NativeRFQPool, and NativeBridge are all **immutable direct deployments** (EIP-1967 impl/admin/beacon slots all empty on every chain). Upgrades happen by deploying a fresh contract and re-pointing (`setRouter`, `setNativePool`), not by `Upgraded(address)`. There is no "Upgraded" topic to watch in this product line.

---

## 0. Contract families

| Contract | Role | Proxy? | Verified on-chain name / EIP-712 domain | Swap event |
|----------|------|--------|------------------------------------------|------------|
| **NativeRouter V4** | RFQ entrypoint **+ AMM fallback** (`externalSwap`) + external-swap-source allowlist. Newer router. | **No** (immutable, 15 637 B) | `NativeRouter` / `"Native Router"` | none on router (RFQ); `ExternalSwapped` for AMM fallback |
| **NativeRouter V3** | RFQ-only entrypoint (no `externalSwap`, no external-source allowlist). Older router, still listed/live. | **No** (immutable, 12 565 B) | `NativeRouter` / `"Native Router"` | none on router |
| **NativeRFQPool** ("NativePool" / credit pool) | Per-asset-set credit pool the router calls; verifies the MM EIP-712 signature, pulls inventory from `CreditVault` (its `treasury()`), settles, emits `RFQTrade`. `isCreditPool()=true`. | **No** (immutable, ~9 478 B) | `NativeRFQPool` / `"Native RFQ Pool"` | **`RFQTrade`** ← the canonical swap event |
| **NativeBridge** | Cross-chain intent escrow: `initiate` (source), `fill` (dest), `claim`/`batchClaim` (MM settlement), `refund*`, plus `externalBridge` (3rd-party bridge router fallback). | **No** (immutable, 23 010 B) | `NativeBridge` / `"Native Bridge"` | `OrderCreated`, `Filled`, `Claimed`, `Refunded` |

`NativeRouter` and `NativeRFQPool` source is **not** in the public `native-v2-core` repo (which only ships `CreditVault.sol` + `NativeLPToken.sol`, the lending side) — ABIs here come from Sourcify-verified deployments and on-chain bytecode/log verification.

**Quote-struct shapes (used across Router/Pool/Bridge).** The 19-field RFQ-T order tuple recurs everywhere:
```
RFQT_ORDER = (address,address,address,address,address,
              uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,
              bytes16, bool, bytes, (address,uint256), bytes)
```
(verified identical in `Router.tradeRFQT`, `Pool.tradeRFQT`, `Bridge.fill`/`initiate`/`claim`). The `bytes16` is the quote/order id; the `(address,uint256)` inner tuple is the widget-fee `(recipient, rate)`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All topic0 below were computed locally (keccak-256) from the Sourcify ABIs and the canonical (no-names, no-`indexed`) signature. `RFQTrade`, `NativePoolUpdated`, and `OrderCreated` were additionally **cross-checked against live `eth_getLogs`** on the real contracts (see §"Verification").

### 1.1 NativeRFQPool — the swap event lives here

| topic0 | Event |
|--------|-------|
| `0xc82975a4eae9f14416813a0bd7312edf547928cd25ae9b8597ee4c92fa6862d2` | `RFQTrade(address,address,address,uint256,uint256,bytes16,address)` — **the swap.** `(seller/MM, sellerToken, buyerToken, sellerAmount, buyerAmount, quoteId, recipient)` (param names approximate; none indexed → all in data). *(verified live on the ETH V4 pool)* |
| `0x3c864541ef71378c6229510ed90f376565ee42d9c5e0904a984a9e863e6db44f` | `TreasurySet(address)` — pool's CreditVault pointer set. |
| `0xfcaa24b1276bfa7dbf77797c0a984b9df924acbeaabd48cd2f1b0eca379b78fa` | `SignerUpdated(address,bool)` — MM signer allowlist toggle. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address,address)` |
| `0x0a6387c9ea3628b88a633bb4f3b151770f70085117a15f9bf3787cda53f13d31` | `EIP712DomainChanged()` |

### 1.2 NativeRouter V4 (superset of V3)

| topic0 | Event | V3 too? |
|--------|-------|---------|
| `0x9f7b0fbb6f2d2fd26353c20e722376e36fbbae212974eb7ca9cd9baffc4e45e8` | `ExternalSwapped(address,address,address,address,uint256,uint256,bytes16)` — AMM-fallback swap (`source`, `recipient`, `sellerToken` indexed). **V4 only.** | no |
| `0x03683b1cc5af1c7a9dd0df6313cb6ea17e008f6acfac353db6d61d844072ff6a` | `ExternalSwapSourceUpdated(address,bool)` — external AMM source allowlist (`source` indexed). **V4 only.** | no |
| `0xfaf49cc693ce3c0463a5ee92d3dd6d6b1ee310fe10c4ccd1e345431f9b62f1cd` | `NativePoolUpdated(address,bool)` — credit-pool registered/de-registered on the router (`pool` indexed). *(verified live on the ETH V4 router)* | **yes** |
| `0x55be346d3a3628b5060716bacd516632c5a911ce5835123ea18a84ea0ff3ea93` | `WidgetFeeTransfer(address,uint256,uint256,address)` — integrator/widget fee paid out. | yes |
| `0xfcaa24b1276bfa7dbf77797c0a984b9df924acbeaabd48cd2f1b0eca379b78fa` | `SignerUpdated(address,bool)` | yes |
| `0xdbdf8eb487847e4c0f22847f5dac07f2d3690f96f581a6ae4b102769917645a8` | `RefundERC20(address,address,uint256)` | yes |
| `0x289360176646a5f99cb4b6300628426dca46b723f40db3c04449d6ed1745a0e7` | `RefundETH(address,uint256)` | yes |
| `0x788ab6452512428d16fe809d92c0dd69b99bc3db368437d73455c5e371638dcf` | `UnwrapWETH9(address,uint256)` (`recipient` indexed) | yes |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address)` | yes |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address)` | yes |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` | yes |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address,address)` | yes |
| `0x0a6387c9ea3628b88a633bb4f3b151770f70085117a15f9bf3787cda53f13d31` | `EIP712DomainChanged()` | yes |

**NativeRouter V3** emits the same set **minus** `ExternalSwapped` and `ExternalSwapSourceUpdated` (V3 has no AMM-fallback / external-source surface). Everything else in §1.2 marked "yes" applies to V3.

### 1.3 NativeBridge

| topic0 | Event |
|--------|-------|
| `0x815eb8f31f063ad6e5dfc30e9904bf56c06c67a0cf04123a24b3707a6b5e1ce1` | `OrderCreated(address,address,bytes16,address,uint256,address,uint256,address,address,uint32)` — source-chain bridge intent created (`swapper`, `recipient`, `quoteId` indexed). *(verified live on the ETH bridge)* |
| `0x5058c2c070ee43aa7920589163f285ff95ba6c223652dcd97080437c9d3d6dba` | `Filled(address,bytes16,address,address,uint256,uint32)` — dest-chain fill by MM (`recipient`, `quoteId`, `settler` indexed). |
| `0xbd951368d43c2e1875fd02dd315c81c7561f8cdbaed467664b48a06e7101dab7` | `Claimed(address,address,uint256,address[],bytes16[])` — MM claims escrowed source funds (`settler`, `token` indexed). |
| `0x6424645453312a97d058f07efffabd2c739263d83d5c4d8a38a2d9e8e9e56755` | `Refunded(address,address,bytes16,address,uint256)` — source refund to user (`user`, `refundTo`, `quoteId` indexed). |
| `0xba6d2931f5936f3abce23702c8bb6462fd7185f176abcbebca603f7480631410` | `ExternalBridged(address,address,address,address,uint256,uint256,uint256,uint256,bytes16)` — routed via a 3rd-party bridge (`bridgeRouter`, `recipient` indexed). |
| `0x0a86f74894e732067ed6b5772d5a1e1fa9351815214f3d71fb0a758d2021befc` | `ExternalBridgeRefunded(address,address,bytes16,address,uint256)` (`initiator`, `user`, `quoteId` indexed). |
| `0x1cdec17edf903de63af98b441f02e1ba4852f1a1b079d5f173e01ca002768390` | `ExternalBridgeRouterUpdated(address,bool)` (`bridgeRouter` indexed). |
| `0xa834f0101ce3509b1bc39a75a825caae7045d16d08c4759b84799e0fd875d248` | `DestinationStatusUpdated(uint32,bool)` — dest chain enabled/disabled (`destChainId` indexed). |
| `0xe57b6bfa2587fb4d95cb816404e883c653c162cf7682728a32ba94b144139854` | `MMSignerUpdated(address,bool)` (`signer` indexed). |
| `0xfcaa24b1276bfa7dbf77797c0a984b9df924acbeaabd48cd2f1b0eca379b78fa` | `SignerUpdated(address,bool)` (`signer` indexed) — **same topic0 as the Router/Pool `SignerUpdated`**; filter by address. |
| `0x02dc5c233404867c793b749c6d644beb2277536d18a7e7974d3f238e4c6f1684` | `RouterUpdated(address,address)` (`oldRouter`, `newRouter` indexed). |
| `0x060744ad36c7e2695965e49629feb4962ad92e4ddd6b3f89508327b09ef8f486` | `RefundExecutorUpdated(address,address)` (`oldExecutor`, `newExecutor` indexed). |
| `0x453d9c1835fbe1dfc18c62b581abf16bce57e9aafda476ecdf245e83a0b29e94` | `RefundBufferUpdated(uint256,uint256)`. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address,address)` |
| `0x0a6387c9ea3628b88a633bb4f3b151770f70085117a15f9bf3787cda53f13d31` | `EIP712DomainChanged()` |

> Note: there is **no `Upgraded(address)` topic** in this product line — nothing here is a proxy. The "upgrade" signals to watch are `NativePoolUpdated` (router ↔ pool wiring), `RouterUpdated` (bridge → router wiring), and `ExternalSwapSourceUpdated` / `ExternalBridgeRouterUpdated` (3rd-party allowlists).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 NativeRouter V4 (`RFQT_ORDER` = the 19-field tuple in §0)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0947c2d9` | `tradeRFQT((address,address,address,address,address,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,bytes16,bool,bytes,(address,uint256),bytes),uint256,uint256)` | **The RFQ swap.** `(order, amountIn, minAmountOut)`-ish. `payable`. Forwards to a registered `NativeRFQPool`. |
| `0x9f63fad7` | `externalSwap((address,address,address,address,uint256,address,uint256,uint256,bytes16,bytes,bytes))` | **V4 only.** AMM-fallback swap through an allowlisted external source. Emits `ExternalSwapped`. `payable`. |
| `0xac9650d8` | `multicall(bytes[])` | Multi-hop / batched. |
| `0x5ae401dc` | `multicall(uint256,bytes[])` | With deadline. |
| `0x49927653` | `setNativePool(address,bool)` | Owner-only. Register/deregister a credit pool. Emits `NativePoolUpdated`. |
| `0xffc0a059` | `setExternalSwapSource(address,bool)` | **V4 only.** Owner-only. Emits `ExternalSwapSourceUpdated`. |
| `0x31cb6105` | `setSigner(address,bool)` | Owner-only. Emits `SignerUpdated`. |
| `0x14eaf7f4` | `isNativePools(address)` | View: is this a registered credit pool. |
| `0x44281c9c` | `externalSwapSources(address)` | **V4 only.** View: is this an allowlisted AMM source. |
| `0x736c0d5b` | `signers(address)` | View. |
| `0xa1b75446` | `unwrapWETH9(address)` | |
| `0x4bd22766` | `refundETH(address,uint256)` | Emits `RefundETH`. |
| `0x48c44712` | `refundERC20(address,address,uint256)` | Emits `RefundERC20`. |
| `0x8456cb59` | `pause()` / `0x3f4ba83a` `unpause()` / `0x5c975abb` `paused()` | Pausable. |
| `0xfbfa77cf` | `vault()` | **→ chain's `CreditVault`** (lending boundary). |
| `0x4aa4a4fc` | `WETH9()` | Wrapped native. |
| `0x8da5cb5b` | `owner()` / `0xe30c3978` `pendingOwner()` / `0x79ba5097` `acceptOwnership()` / `0xf2fde38b` `transferOwnership(address)` / `0x715018a6` `renounceOwnership()` | Ownable2Step. |
| `0x84b0196e` | `eip712Domain()` | Returns name `"Native Router"`. |

**NativeRouter V3** has the identical surface **minus** `externalSwap` (`0x9f63fad7`), `setExternalSwapSource` (`0xffc0a059`), and `externalSwapSources` (`0x44281c9c`). The presence/absence of `externalSwap` (`0x9f63fad7`) in the dispatcher is the cleanest V4-vs-V3 selector tell.

### 2.2 NativeRFQPool ("NativePool" / credit pool)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xaae6dd92` | `tradeRFQT(uint256,(address,address,address,address,address,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,uint256,bytes16,bool,bytes,(address,uint256),bytes))` | Pool-side RFQ execution. **Different selector & arg order from the Router `tradeRFQT`** (`(amountIn, order)` here vs `(order,uint256,uint256)` on the router). Only callable by the router (`OnlyNativeRouter`). Emits `RFQTrade`. |
| `0xf887ea40` | `router()` | The owning `NativeRouter`. |
| `0x61d027b3` | `treasury()` | **→ `CreditVault`** (lending boundary). |
| `0xbc58f13d` | `isCreditPool()` | Returns `true` for these pools. |
| `0xf0f44260` | `setTreasury(address)` | Owner-only. Emits `TreasurySet`. |
| `0x31cb6105` | `setSigner(address,bool)` | Owner-only. Emits `SignerUpdated`. |
| `0x95fa3bd9` | `rfqSigners(address)` | View: MM signer allowlist. |
| `0x141a468c` | `nonces(uint256)` | Quote-nonce replay guard (`NonceUsed`). |
| `0x06fdde03` | `name()` | EIP-712 domain name. |
| `0x4aa4a4fc` | `WETH9()` | |
| `0x8da5cb5b` | `owner()` / `0xe30c3978` `pendingOwner()` / `0x79ba5097` `acceptOwnership()` / `0xf2fde38b` `transferOwnership(address)` / `0x715018a6` `renounceOwnership()` | Ownable2Step. |
| `0x84b0196e` | `eip712Domain()` | Name `"Native RFQ Pool"`. |

### 2.3 NativeBridge

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc21c3ca6` | `initiate(uint32,uint32,address,(RFQT_ORDER))` | Source-chain: escrow funds + create order. Emits `OrderCreated`. `payable`. |
| `0x383c599f` | `fill((RFQT_ORDER))` | Dest-chain: MM delivers output to recipient. Emits `Filled`. |
| `0xdd8b301a` | `claim(((RFQT_ORDER),address[],bytes16[]))` | MM claims escrowed source funds for a filled order. Emits `Claimed`. |
| `0x6cd3ca1c` | `batchClaim(((RFQT_ORDER),address[],bytes16[])[])` | Batched `claim`. |
| `0x60330682` | `externalBridge((address,address,address,address,address,uint256,uint256,uint256,uint256,uint256,bytes16,bytes,bytes))` | Route via an allowlisted 3rd-party bridge. Emits `ExternalBridged`. `payable`. |
| `0x6013a881` | `refund(bytes16,bytes,bytes)` | User/anyone refunds an unfilled order after the buffer. Emits `Refunded`. |
| `0xd4ba0dbf` | `refundFor(address,bytes16,bytes,bytes)` | Refund on behalf of a user. |
| `0x16a4bfca` | `refundExternalBridge(bytes16,bytes,bytes,address,bytes)` | Emits `ExternalBridgeRefunded`. |
| `0xc0d78655` | `setRouter(address)` | Owner-only. Emits `RouterUpdated`. |
| `0x31cb6105` | `setSigner(address,bool)` | Owner-only. Emits `SignerUpdated`. |
| `0x90238882` | `setMarketMakerSigner(address,bool)` | Owner-only. Emits `MMSignerUpdated`. |
| `0xe159a112` | `setDestinationChains(uint32[],bool[])` | Owner-only. Emits `DestinationStatusUpdated`. |
| `0x2990c432` | `setExternalBridgeRouter(address,bool)` | Owner-only. Emits `ExternalBridgeRouterUpdated`. |
| `0x96158520` | `setRefundExecutor(address)` | Owner-only. Emits `RefundExecutorUpdated`. |
| `0x3399b499` | `setRefundBuffer(uint256)` | Owner-only. Emits `RefundBufferUpdated`. |
| `0xf887ea40` | `router()` | **→ chain's V4 `NativeRouter`.** |
| `0xfbfa77cf` | `vault()` | **→ chain's `CreditVault`.** |
| `0x4aa4a4fc` | `WETH9()` | |
| `0xc212e402` | `refundExecutor()` / `0x283138c2` `refundBuffer()` / `0x14aac67e` `enabledDestination(uint32)` | Views. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` (non-empty) on `https://ethereum-rpc.publicnode.com`. Router/Pool/Bridge are **immutable** (no proxy slot). Live `vault()`/`treasury()`/`router()` cross-checked.

| Role | Address | One-liner |
|------|---------|-----------|
| **NativeRouter V4** | `0x8a2ddc0461Fcf96F81a05529Bed540d4f1eb2a00` | 15 637 B. `vault()`=CreditVault, `WETH9()`=WETH. RFQ + `externalSwap`. |
| **NativeRouter V3** | `0xa540ec8C73322200d68E1B86c471A5C850854f22` | 12 565 B. RFQ-only. |
| **NativeRFQPool** (V4 credit pool) | `0xc419e67388df0c0cfad15584fc5fc7e67a234c17` | 9 478 B. `router()`=V4 router, `treasury()`=CreditVault, `isCreditPool()`=true. Source of `RFQTrade`. *(discovered via `NativePoolUpdated`)* |
| **NativeRFQPool** (V3 credit pool) | `0x5d1a34369686ae59ac97ae4e1df5635ffda9ee7c` | `router()`=V3 router, `treasury()`=CreditVault. |
| **NativeBridge** | `0xceBFC5dFBD5CE21694fe2ACefa63aD6f828831d2` | 23 010 B. `router()`=V4 router, `vault()`=CreditVault. |
| *CreditVault (lending boundary — not in scope)* | `0xe3D41d19564922C9952f692C5Dd0563030f5f2EF` | `vault()`/`treasury()` target of every contract above. Documented separately. |
| Protocol admin (`owner()` of all swap contracts) | `0x83fc28e6962e41e38f7854308eff827e3f6b906b` | Ethereum-specific admin. |
| WETH9 | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` | Wrapped native. |

> **Legacy/unlisted:** `0x5C0aBf0F651613696A5c57efafC6ab59A460B32d` is an older verified `NativeRouter` (15 670 B, also immutable) **not** on the current docs addresses page. Its `vault()` = `0xbf5d861d247a3b12ae76ad647c52ad3ad14c7bca` (a *different*, older vault), so it is a prior-generation deployment, not part of the current V3/V4 stack. Watch it only if you index historical Native swaps. The docs' "sample pool" `0x5984C239c08834dBCf80d4fd741B4Ed47fFe3D02` returns `0x` (dead/never-deployed) — do not use.

---

## 4. Addresses — Base mainnet (chain ID 8453)

All verified via `eth_getCode` on `https://base-rpc.publicnode.com`. Routers + bridge deployed **very recently** (~10 k blocks before 2026-06-02) — see §"Detection invariants" #8. No `NativePool` registered on either router yet (no `NativePoolUpdated` in full history) — pool discovery is **deferred** until first registration.

| Role | Address | One-liner |
|------|---------|-----------|
| **NativeRouter V4** | `0xaEC634d949df14Be76dC317504C7b9a6a8A5f576` | 15 637 B. `vault()`=`0x74a4cd02…` CreditVault, `WETH9()`=`0x4200…0006`. |
| **NativeRouter V3** | `0xd547727b926648Af3F31DbB89E3B93E49F78dCb8` | 12 565 B. RFQ-only. |
| **NativeRFQPool** | — | **None registered yet** (no `NativePoolUpdated`). |
| **NativeBridge** | `0xA11f7CdE7402093FF4D24A91FD8cdcc8AA0c96A8` | 23 010 B. `router()`=V4 router, `vault()`=CreditVault. |
| *CreditVault (boundary)* | `0x74a4Cd023e5AfB88369E3f22b02440F2614a1367` | target of `vault()`/`router()`. Separate reference. |
| Protocol admin (`owner()`) | `0x181fb7f2779b23f9f493ff7282f25ad39ac6ba96` | Base-specific admin. |
| WETH | `0x4200000000000000000000000000000000000006` | OP-Stack predeploy. |

---

## 5. Addresses — BNB Smart Chain (chain ID 56)

All verified via `eth_getCode` on `https://bsc-rpc.publicnode.com`. Routers + bridge deployed **extremely recently** (~130 blocks before 2026-06-02). No `NativePool` registered yet.

| Role | Address | One-liner |
|------|---------|-----------|
| **NativeRouter V4** | `0xF064b069Ed18Eb5c61159247C55C5af79B28a968` | 15 637 B. `vault()`=`0xba8db0ca…`, `WETH9()`=WBNB. |
| **NativeRouter V3** | `0x0f9f2366C6157F2aCD3C2bFA45Cd9031c152D2Cf` | 12 565 B. RFQ-only. |
| **NativeRFQPool** | — | **None registered yet.** |
| **NativeBridge** | `0x5B933868f5e710070b146213ED2Cd71628E465C1` | 23 010 B. `router()`=V4 router. |
| *CreditVault (boundary)* | `0xBA8dB0CAf781cAc69b6acf6C848aC148264Cc05d` | Separate reference. |
| Protocol admin (`owner()`) | `0x2f775775e7eb2f8b9a31d10400273308f6deef0a` | BNB-specific admin. |
| WBNB | `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` | Wrapped native. |

---

## 6. Addresses — Arbitrum One (chain ID 42161)

All verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com`. No `NativePool` registered on either router yet.

| Role | Address | One-liner |
|------|---------|-----------|
| **NativeRouter V4** | `0x0FC85a171bD0b53BF0bBace74F04B66170Ae3eAb` | 15 637 B. `vault()`=`0xba1cf8a6…`, `WETH9()`=`0x82af…b1` WETH. |
| **NativeRouter V3** | `0x7d1c4889DF6113B3e4581a8c0484374bdeC3341B` | 12 565 B. RFQ-only. |
| **NativeRFQPool** | — | **None registered yet.** |
| **NativeBridge** | `0x5E65CEa5473fC8977e4DfDe940B2A99a439181cA` | 23 010 B. `router()`=V4 router. |
| *CreditVault (boundary)* | `0xbA1cf8A63227b46575AF823BEB4d83D1025eff09` | Separate reference. |
| Protocol admin (`owner()`) | `0x48d5713904e194a27e5d57eb76dee4ad67b0198a` | Arbitrum-specific admin. |
| WETH | `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` | Wrapped native. |

---

## 7. Addresses — Avalanche (43114), Optimism (10), Polygon PoS (137) — NOT DEPLOYED

The Native Swap Engine is **not deployed** on Avalanche C-Chain, Optimism, or Polygon PoS. `eth_getCode` returns `0x` for **every** Swap-Engine address (V4 router, V3 router, bridge — checked the ETH/Base/BNB/Arb variants of each) on all three chains, verified on `https://avalanche-c-chain-rpc.publicnode.com`, `https://optimism-rpc.publicnode.com`, and `https://polygon-bor-rpc.publicnode.com` on 2026-06-02.

| Chain | ID | RPC | NativeRouter V4 | NativeRouter V3 | NativeRFQPool | NativeBridge |
|-------|----|-----|-----------------|-----------------|---------------|--------------|
| Avalanche C-Chain | 43114 | avalanche-c-chain-rpc.publicnode.com | `0x` | `0x` | `0x` | `0x` |
| Optimism | 10 | optimism-rpc.publicnode.com | `0x` | `0x` | `0x` | `0x` |
| Polygon PoS | 137 | polygon-bor-rpc.publicnode.com | `0x` | `0x` | `0x` | `0x` |

The Native docs addresses page also lists only Ethereum, BNB, Arbitrum, and Base — consistent with the on-chain absence on the other three.

> **CREATE2 caveat (do not be fooled):** a *handful* of the documented Native addresses happen to also contain unrelated bytecode at the same address on *other* chains (e.g. the Arbitrum V4-router address `0x0FC8…3eAb` has code on Ethereum and BNB too, of different byte length). These are **coincidental address reuse by unrelated contracts**, NOT Native deployments — the bytecode/length and `vault()`/`eip712Domain()` differ. Native routers are **not** CREATE2-identical across chains: each chain's router has the same *role* and source but a *different* deployed bytecode (chain-specific immutable args ⇒ same byte-length per role but different sha256). Always confirm identity by `eip712Domain()`name + `vault()` target, never by address presence alone.

---

## Cross-chain summary (presence matrix)

| Chain | ID | Router V4 | Router V3 | NativeRFQPool | NativeBridge | CreditVault (boundary) |
|-------|----|-----------|-----------|---------------|--------------|------------------------|
| Ethereum | 1 | ✓ | ✓ | ✓ (V4 + V3 pools live) | ✓ | `0xe3D41d19…` |
| Base | 8453 | ✓ | ✓ | — (none registered yet) | ✓ | `0x74a4Cd02…` |
| BNB | 56 | ✓ | ✓ | — (none registered yet) | ✓ | `0xBA8dB0CA…` |
| Arbitrum | 42161 | ✓ | ✓ | — (none registered yet) | ✓ | `0xbA1cf8A6…` |
| Avalanche | 43114 | ✗ | ✗ | ✗ | ✗ | ✗ |
| Optimism | 10 | ✗ | ✗ | ✗ | ✗ | ✗ |
| Polygon | 137 | ✗ | ✗ | ✗ | ✗ | ✗ |

- **Routers are NOT CREATE2-identical** across chains (same role, same byte-length per role, different bytecode hash & different deployed address). The per-chain admin (`owner()`) also differs.
- Only Ethereum currently has live `NativeRFQPool`(s). On Base/BNB/Arbitrum the routers/bridge are deployed and functional but **no credit pool is registered yet** (no `NativePoolUpdated`) — discover pools dynamically by indexing `NativePoolUpdated` on each router going forward.

---

## Proxies (old & new)

**There are no proxies in the Native Swap Engine.** Every Swap-Engine contract on every deployed chain is an **immutable direct deployment**:

| Contract | EIP-1967 impl slot `0x360894…bbc` | admin slot `0xb53127…6103` | beacon slot `0xa3f0ad…3d50` | Verdict |
|----------|-----------------------------------|-----------------------------|------------------------------|---------|
| NativeRouter V4 (all chains) | empty (`0x000…0`) | empty | empty | immutable, not a proxy |
| NativeRouter V3 (all chains) | empty | empty | empty | immutable, not a proxy |
| NativeRFQPool (ETH) | empty | empty | empty | immutable, not a proxy |
| NativeBridge (all chains) | empty | empty | empty | immutable, not a proxy |

(Read with `eth_getStorageAt(addr, 0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc)` etc. — all return `0x0` on every chain.)

Consequences for monitoring:
- **No `Upgraded(address)` topic to watch.** "Upgrades" are done by deploying a new contract and re-pointing wiring. The wiring-change events to watch instead are: `NativePoolUpdated` (router↔pool), `RouterUpdated` (bridge→router), `TreasurySet` (pool→CreditVault), `ExternalSwapSourceUpdated` / `ExternalBridgeRouterUpdated` (3rd-party allowlists), and `SignerUpdated` / `MMSignerUpdated` (MM signer rotation).
- The docs page labels the entry point "NativeRouter (Proxy)", but that is **stale/generic** — the V3/V4 routers verified here are not proxies. Treat the docs label as informational, the storage-slot evidence as authoritative.
- The CreditVault on the lending side *may* be a proxy — that is out of scope here and covered by the separate lending reference.

---

## Detection invariants & gotchas

1. **The swap event is `RFQTrade` on the `NativeRFQPool`, not on the router.** A base RFQ swap (`Router.tradeRFQT`) emits **nothing on the router** — the only swap log is `RFQTrade` (`0xc82975a4…`) on the pool. To catch all RFQ swaps, index `RFQTrade` across the set of registered pools (discovered via `NativePoolUpdated`), not the router address.
2. **Two different `tradeRFQT` selectors.** Router `tradeRFQT(order,uint256,uint256)` = `0x0947c2d9`; Pool `tradeRFQT(uint256,order)` = `0xaae6dd92`. Different arg order, different selector. The router-level call is what swappers submit; the pool-level call is the internal forward (only callable by the router — `OnlyNativeRouter`).
3. **V4 vs V3 tell:** V4 has `externalSwap` (`0x9f63fad7`) + `ExternalSwapped` (`0x9f7b0fbb…`) + `ExternalSwapSourceUpdated` (`0x03683b1c…`); V3 has none of these. Probe the dispatcher for `0x9f63fad7` to classify a router. The AMM-fallback path (`externalSwap`) is the **only** swap that emits a router-level event.
4. **`vault()`/`treasury()` is the boundary to the lending side.** Every Router (`vault()`), Pool (`treasury()`), and Bridge (`vault()`) points at the chain's `CreditVault` (ETH `0xe3D41d19…`, Base `0x74a4Cd02…`, BNB `0xBA8dB0CA…`, Arb `0xbA1cf8A6…`). Those four addresses are the seam — they belong to the separate `CreditVault`/`NativeLPToken` reference, not this one. The CreditVault is also the pools' inventory source: RFQ settlement pulls MM inventory out of CreditVault, so a swap will not show a simple `pool→user` ERC-20 transfer chain.
5. **`SignerUpdated` topic0 is shared** by Router, Pool, and Bridge (`0xfcaa24b1…`). Always filter `(chainId, contract address, topic0)`, never topic0 alone. Same for the Ownable/Pausable/EIP712 topics.
6. **No factory, no `PoolCreated`, no CREATE2 pool derivation.** Native is RFQ, not AMM. Pools are registered administratively via `setNativePool` (→ `NativePoolUpdated`), not deployed deterministically. You cannot compute a pool address off-chain — you must read `NativePoolUpdated` history (and `isNativePools(addr)` to confirm current status).
7. **`quoteId` (`bytes16`) is the cross-event correlation key.** It threads `RFQTrade` (pool), `ExternalSwapped` (router), and the bridge `OrderCreated`/`Filled`/`Claimed`/`Refunded`. Key bridge lifecycles on `(chainId, quoteId)`; the full cross-chain bridge flow is `OrderCreated`(source) → `Filled`(dest) → `Claimed`(source MM settlement), with `Refunded` as the timeout branch.
8. **Base / BNB / Arbitrum routers are freshly deployed (as of 2026-06-02) with NO pool registered yet.** Binary-searched deploy blocks: Base ~46.79 M (~10 k blocks old), BNB ~101.85 M (~130 blocks old), Arbitrum ~461.89 M. They respond to `vault()`/`owner()`/`WETH9()` correctly (genuine NativeRouters) but emit no `NativePoolUpdated` in their full history. Expect pools to appear later — index `NativePoolUpdated` forward. Do **not** record "no pool" as permanent.
9. **Coincidental address reuse across chains.** Some Native addresses contain *unrelated* contract bytecode on chains where Native isn't deployed (different byte-length, different `eip712Domain`). Confirm identity by `eip712Domain()` name (`"Native Router"` / `"Native RFQ Pool"` / `"Native Bridge"`) and `vault()` target, never by `eth_getCode` non-emptiness alone.
10. **Legacy router `0x5C0aBf0F…` (ETH) is out-of-list.** Older `NativeRouter` pointing at an older vault (`0xbf5d861d…`). Not on the current docs page; include only for historical swap indexing.
11. **`externalSwap`/`externalBridge` route through allowlisted 3rd-party DEX/bridge routers.** Expect nested calls to non-Native routers inside `externalSwap` txs; the `source`/`bridgeRouter` field identifies which. Allowlist changes fire `ExternalSwapSourceUpdated` / `ExternalBridgeRouterUpdated`.
12. **Multicall wraps multi-hop.** `multicall(bytes[])` = `0xac9650d8` and `multicall(uint256,bytes[])` = `0x5ae401dc` (deadline variant) batch several `tradeRFQT`/refund/unwrap calls; a single tx can emit several `RFQTrade`s across pools.

---

## Quick-copy detection constants (Postgres `\x` bytea literals, lowercase)

```
-- ===== Proxy slots (all EMPTY on every Native swap contract — no proxies) =====
EIP1967_IMPL_SLOT                 = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Topics (chain-agnostic) =====
-- NativeRFQPool
TOPIC_RFQ_TRADE                   = '\xc82975a4eae9f14416813a0bd7312edf547928cd25ae9b8597ee4c92fa6862d2'
TOPIC_TREASURY_SET                = '\x3c864541ef71378c6229510ed90f376565ee42d9c5e0904a984a9e863e6db44f'
-- NativeRouter (V4 superset; V3 = same minus the two External* topics)
TOPIC_EXTERNAL_SWAPPED            = '\x9f7b0fbb6f2d2fd26353c20e722376e36fbbae212974eb7ca9cd9baffc4e45e8'  -- V4 only
TOPIC_EXTERNAL_SWAP_SOURCE_UPD    = '\x03683b1cc5af1c7a9dd0df6313cb6ea17e008f6acfac353db6d61d844072ff6a'  -- V4 only
TOPIC_NATIVE_POOL_UPDATED         = '\xfaf49cc693ce3c0463a5ee92d3dd6d6b1ee310fe10c4ccd1e345431f9b62f1cd'
TOPIC_WIDGET_FEE_TRANSFER         = '\x55be346d3a3628b5060716bacd516632c5a911ce5835123ea18a84ea0ff3ea93'
TOPIC_REFUND_ERC20                = '\xdbdf8eb487847e4c0f22847f5dac07f2d3690f96f581a6ae4b102769917645a8'
TOPIC_REFUND_ETH                  = '\x289360176646a5f99cb4b6300628426dca46b723f40db3c04449d6ed1745a0e7'
TOPIC_UNWRAP_WETH9                = '\x788ab6452512428d16fe809d92c0dd69b99bc3db368437d73455c5e371638dcf'
-- Shared across Router/Pool/Bridge — filter by address!
TOPIC_SIGNER_UPDATED              = '\xfcaa24b1276bfa7dbf77797c0a984b9df924acbeaabd48cd2f1b0eca379b78fa'
TOPIC_PAUSED                      = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                    = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_OWNERSHIP_TRANSFERRED       = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_OWNERSHIP_TRANSFER_STARTED  = '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'
TOPIC_EIP712_DOMAIN_CHANGED       = '\x0a6387c9ea3628b88a633bb4f3b151770f70085117a15f9bf3787cda53f13d31'
-- NativeBridge
TOPIC_ORDER_CREATED               = '\x815eb8f31f063ad6e5dfc30e9904bf56c06c67a0cf04123a24b3707a6b5e1ce1'
TOPIC_FILLED                      = '\x5058c2c070ee43aa7920589163f285ff95ba6c223652dcd97080437c9d3d6dba'
TOPIC_CLAIMED                     = '\xbd951368d43c2e1875fd02dd315c81c7561f8cdbaed467664b48a06e7101dab7'
TOPIC_REFUNDED                    = '\x6424645453312a97d058f07efffabd2c739263d83d5c4d8a38a2d9e8e9e56755'
TOPIC_EXTERNAL_BRIDGED            = '\xba6d2931f5936f3abce23702c8bb6462fd7185f176abcbebca603f7480631410'
TOPIC_EXTERNAL_BRIDGE_REFUNDED    = '\x0a86f74894e732067ed6b5772d5a1e1fa9351815214f3d71fb0a758d2021befc'
TOPIC_EXTERNAL_BRIDGE_ROUTER_UPD  = '\x1cdec17edf903de63af98b441f02e1ba4852f1a1b079d5f173e01ca002768390'
TOPIC_DESTINATION_STATUS_UPDATED  = '\xa834f0101ce3509b1bc39a75a825caae7045d16d08c4759b84799e0fd875d248'
TOPIC_MM_SIGNER_UPDATED           = '\xe57b6bfa2587fb4d95cb816404e883c653c162cf7682728a32ba94b144139854'
TOPIC_ROUTER_UPDATED              = '\x02dc5c233404867c793b749c6d644beb2277536d18a7e7974d3f238e4c6f1684'
TOPIC_REFUND_EXECUTOR_UPDATED     = '\x060744ad36c7e2695965e49629feb4962ad92e4ddd6b3f89508327b09ef8f486'
TOPIC_REFUND_BUFFER_UPDATED       = '\x453d9c1835fbe1dfc18c62b581abf16bce57e9aafda476ecdf245e83a0b29e94'

-- ===== Selectors =====
-- NativeRouter
SEL_ROUTER_TRADE_RFQT             = '\x0947c2d9'   -- tradeRFQT(order,uint256,uint256)
SEL_ROUTER_EXTERNAL_SWAP          = '\x9f63fad7'   -- V4 only; also the V4-vs-V3 tell
SEL_MULTICALL                     = '\xac9650d8'
SEL_MULTICALL_DEADLINE            = '\x5ae401dc'
SEL_SET_NATIVE_POOL               = '\x49927653'
SEL_SET_EXTERNAL_SWAP_SOURCE      = '\xffc0a059'   -- V4 only
SEL_IS_NATIVE_POOLS               = '\x14eaf7f4'
SEL_ROUTER_VAULT                  = '\xfbfa77cf'   -- -> CreditVault (boundary)
-- NativeRFQPool
SEL_POOL_TRADE_RFQT               = '\xaae6dd92'   -- tradeRFQT(uint256,order)
SEL_POOL_ROUTER                   = '\xf887ea40'
SEL_POOL_TREASURY                 = '\x61d027b3'   -- -> CreditVault (boundary)
SEL_POOL_IS_CREDIT_POOL           = '\xbc58f13d'
SEL_POOL_SET_TREASURY             = '\xf0f44260'
-- shared
SEL_SET_SIGNER                    = '\x31cb6105'
SEL_PAUSE                         = '\x8456cb59'
SEL_UNPAUSE                       = '\x3f4ba83a'
SEL_OWNER                         = '\x8da5cb5b'
SEL_WETH9                         = '\x4aa4a4fc'
SEL_EIP712_DOMAIN                 = '\x84b0196e'
-- NativeBridge
SEL_BRIDGE_INITIATE               = '\xc21c3ca6'
SEL_BRIDGE_FILL                   = '\x383c599f'
SEL_BRIDGE_CLAIM                  = '\xdd8b301a'
SEL_BRIDGE_BATCH_CLAIM            = '\x6cd3ca1c'
SEL_BRIDGE_EXTERNAL_BRIDGE        = '\x60330682'
SEL_BRIDGE_REFUND                 = '\x6013a881'
SEL_BRIDGE_REFUND_FOR             = '\xd4ba0dbf'
SEL_BRIDGE_SET_ROUTER             = '\xc0d78655'
SEL_BRIDGE_SET_MM_SIGNER          = '\x90238882'
SEL_BRIDGE_SET_DEST_CHAINS        = '\xe159a112'
SEL_BRIDGE_SET_EXT_BRIDGE_ROUTER  = '\x2990c432'

-- ===== Ethereum (chain ID 1) =====
ETH_NATIVE_ROUTER_V4              = '\x8a2ddc0461fcf96f81a05529bed540d4f1eb2a00'
ETH_NATIVE_ROUTER_V3              = '\xa540ec8c73322200d68e1b86c471a5c850854f22'
ETH_NATIVE_RFQ_POOL_V4            = '\xc419e67388df0c0cfad15584fc5fc7e67a234c17'
ETH_NATIVE_RFQ_POOL_V3            = '\x5d1a34369686ae59ac97ae4e1df5635ffda9ee7c'
ETH_NATIVE_BRIDGE                 = '\xcebfc5dfbd5ce21694fe2acefa63ad6f828831d2'
ETH_CREDIT_VAULT_BOUNDARY         = '\xe3d41d19564922c9952f692c5dd0563030f5f2ef'
ETH_NATIVE_ROUTER_LEGACY          = '\x5c0abf0f651613696a5c57efafc6ab59a460b32d'  -- unlisted, older
ETH_ADMIN_OWNER                   = '\x83fc28e6962e41e38f7854308eff827e3f6b906b'
ETH_WETH9                         = '\xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'

-- ===== Base (chain ID 8453) — no pool registered yet =====
BASE_NATIVE_ROUTER_V4             = '\xaec634d949df14be76dc317504c7b9a6a8a5f576'
BASE_NATIVE_ROUTER_V3             = '\xd547727b926648af3f31dbb89e3b93e49f78dcb8'
BASE_NATIVE_BRIDGE                = '\xa11f7cde7402093ff4d24a91fd8cdcc8aa0c96a8'
BASE_CREDIT_VAULT_BOUNDARY        = '\x74a4cd023e5afb88369e3f22b02440f2614a1367'
BASE_ADMIN_OWNER                  = '\x181fb7f2779b23f9f493ff7282f25ad39ac6ba96'
BASE_WETH                         = '\x4200000000000000000000000000000000000006'

-- ===== BNB Smart Chain (chain ID 56) — no pool registered yet =====
BNB_NATIVE_ROUTER_V4              = '\xf064b069ed18eb5c61159247c55c5af79b28a968'
BNB_NATIVE_ROUTER_V3              = '\x0f9f2366c6157f2acd3c2bfa45cd9031c152d2cf'
BNB_NATIVE_BRIDGE                 = '\x5b933868f5e710070b146213ed2cd71628e465c1'
BNB_CREDIT_VAULT_BOUNDARY         = '\xba8db0caf781cac69b6acf6c848ac148264cc05d'
BNB_ADMIN_OWNER                   = '\x2f775775e7eb2f8b9a31d10400273308f6deef0a'
BNB_WBNB                          = '\xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c'

-- ===== Arbitrum One (chain ID 42161) — no pool registered yet =====
ARB_NATIVE_ROUTER_V4              = '\x0fc85a171bd0b53bf0bbace74f04b66170ae3eab'
ARB_NATIVE_ROUTER_V3              = '\x7d1c4889df6113b3e4581a8c0484374bdec3341b'
ARB_NATIVE_BRIDGE                 = '\x5e65cea5473fc8977e4dfde940b2a99a439181ca'
ARB_CREDIT_VAULT_BOUNDARY         = '\xba1cf8a63227b46575af823beb4d83d1025eff09'
ARB_ADMIN_OWNER                   = '\x48d5713904e194a27e5d57eb76dee4ad67b0198a'
ARB_WETH                          = '\x82af49447d8a07e3bd95bd0d56f35241523fbab1'

-- ===== NOT deployed: Avalanche (43114), Optimism (10), Polygon (137) =====
```

---

## Verification & sources

How every constant was verified (2026-06-02):

- **Addresses (docs):** [docs.native.org/native-dev/resources/addresses](https://docs.native.org/native-dev/resources/addresses) — lists NativeRouter V4, NativeRouter V3, CreditVault, NativeBridge for Ethereum, BNB, Arbitrum, Base. NativeRFQPool is **not** on the docs page; it was discovered on-chain via `NativePoolUpdated`.
- **Bytecode existence + proxy slots:** `eth_getCode` and `eth_getStorageAt` (EIP-1967 impl `0x360894…bbc`, admin `0xb53127…6103`, beacon `0xa3f0ad…3d50`) on each chain's publicnode RPC. Result: all four contract types are immutable (all slots `0x0`); byte-lengths V4 router 15 637 B, V3 router 12 565 B, NativeRFQPool 9 478 B, NativeBridge 23 010 B (same length per role across deployed chains, but **different sha256** ⇒ same source, chain-specific immutables, NOT CREATE2-identical). `0x` for every Swap-Engine address on Avalanche / Optimism / Polygon.
- **Contract names + ABIs:** Sourcify-verified (`NativeRouter` V4 = 57 ABI items on ETH/BNB/Base; `NativeRouter` V3 = 49 items on Base; `NativeRFQPool` = 34 items on ETH; `NativeBridge` = 78 items on BNB/Arb). Other chains' V3/bridge ABIs were not on Sourcify but bytecode length + `eip712Domain()` confirm the same contracts. `Native-org/native-v2-core` README confirms NativeRouter/NativeRFQPool source is not public and CreditVault/NativeLPToken are the (separate) lending side.
- **Topic0 + selectors:** computed locally as `keccak256(canonical signature)` / `[0:4]` (pycryptodome) from the Sourcify ABIs.
- **Live topic0 cross-checks (`eth_getLogs`):** `RFQTrade` (`0xc82975a4…`) confirmed on ETH V4 pool `0xc419e673…` (e.g. tx `0x68ab8866…`); `NativePoolUpdated` (`0xfaf49cc6…`) confirmed on ETH V4 router; `OrderCreated` (`0x815eb8f3…`) confirmed on ETH bridge (e.g. tx `0xf55ccfd2…`).
- **Live state (`eth_call`):** every Router `vault()`, Pool `treasury()`, and Bridge `vault()` resolves to the chain's documented `CreditVault`; pools' `router()` resolve to the matching router; pools' `isCreditPool()`=true; `eip712Domain()` names = `"Native Router"` / `"Native RFQ Pool"` / `"Native Bridge"`; per-chain `owner()` distinct.
- **Deploy blocks (binary-searched `eth_getCode`):** ETH V4 router ≈ 23 624 157, ETH V3 router ≈ 23 189 574, ETH bridge ≈ 24 338 646; Base routers ≈ 46.79 M; BNB routers ≈ 101.85 M; Arbitrum routers ≈ 461.89 M.

Authoritative sources:
- Native docs: [addresses](https://docs.native.org/native-dev/resources/addresses) · [llms-full.txt](https://docs.native.org/native-dev/llms-full.txt)
- GitHub: [Native-org/native-v2-core](https://github.com/Native-org/native-v2-core) (lending side only)
- Sourcify: `https://sourcify.dev/server/v2/contract/<chainId>/<address>`
- Explorers: [Etherscan](https://etherscan.io/address/0x8a2ddc0461Fcf96F81a05529Bed540d4f1eb2a00) · [Basescan](https://basescan.org/address/0xaEC634d949df14Be76dC317504C7b9a6a8A5f576) · [BscScan](https://bscscan.com/address/0xF064b069Ed18Eb5c61159247C55C5af79B28a968) · [Arbiscan](https://arbiscan.io/address/0x0FC85a171bD0b53BF0bBace74F04B66170Ae3eAb)

### Verification.1 Independent fact-check (2026-06-02) — ✅ all swap-side claims confirmed, no corrections

6 non-obvious claims were cross-checked against the official docs addresses page, the `Native-org`
GitHub org, DefiLlama, and block explorers. Verdicts:

1. **Swap-side contract set is complete (Router V4/V3, RFQPool, Bridge).** — ✅ confirmed. The docs
   addresses page lists exactly NativeRouter V4, NativeRouter V3, CreditVault, NativeBridge for the four
   chains; no additional swap-side contract (no separate aggregator, widget, or quoter contract) is
   published. The `Native-org` org has only two public repos (`native-v2-core`, `public-lists`).
2. **No standalone Native governance/token/staking contract exists** to add to the swap doc. — ✅ confirmed
   (no `NATIVE`/`N` ERC-20, airdrop, or staking contract found in docs, GitHub, or search).
3. **Routers/Pool/Bridge are immutable (not proxies).** — ✅ confirmed (EIP-1967 slots empty; re-read live).
4. **`RFQTrade` is emitted by the pool, not the router.** — ✅ confirmed (live `eth_getLogs` on the ETH pool).
5. **All listed ETH/BNB/Arb/Base addresses are current** (match the live docs page verbatim). — ✅ confirmed.
6. **Chain coverage = ETH/BNB/Arb/Base only among our 7 targets; absent on Avalanche/Optimism/Polygon.**
   — ✅ confirmed. ⚠️ *Scope note (not a correction):* DefiLlama has historically attributed Native
   **dexVolume** to **Mantle, Monad, ZetaChain, and zkLink Nova** as well. Those chains are **outside the
   seven target chains** of this reference and are **not** in Native's official docs addresses page, so
   they are out of scope here — but if monitoring expands beyond the seven chains, re-check Mantle/Monad
   for a NativeRouter/NativeBridge deployment (DefiLlama volume there may be Native's *aggregator routing*
   rather than a native deployment; unverified).

**Net corrections folded in:** none — all swap-side claims confirmed. Added the Mantle/Monad/ZetaChain/zkLink
out-of-scope note above.

### UNVERIFIED / open items

- **NativeRFQPool addresses on Base / BNB / Arbitrum** are not yet determinable: routers are deployed but no `NativePoolUpdated` has fired in their (short) history as of 2026-06-02. Re-scan `NativePoolUpdated` forward to capture pools when registered.
- **`RFQTrade` exact field names** (seller/buyer token ordering, `recipient` placement) are inferred from arg types + context; the topic0 and arity are exact, the human labels are approximate (the ABI has no param names exposed via Sourcify for some fields).
- **V3/Bridge ABIs on BNB/Arb/Base/ETH** that Sourcify did not return were validated by byte-length + `eip712Domain()` identity, not by re-fetching full source; signatures are taken from the chains where the ABI *was* verified (same contract family).
