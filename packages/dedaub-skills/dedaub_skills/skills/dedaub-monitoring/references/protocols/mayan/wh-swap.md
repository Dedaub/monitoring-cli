# Mayan Wormhole Swap — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche; NOT Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the `mayan-finance/swap-sdk` ABI (`MayanSwapArtifact`), docs.mayan.finance (`architecture/wh-swap`) and the Mayan chain config (`https://sia.mayan.finance/v10/init`). The contract source is not verified on the explorer, so every selector below was also checked in the deployed bytecode (PUSH4 in the dispatcher) on Ethereum and Base. Topic0 values were recomputed as `keccak256(signature)` and matched against live logs. Addresses were existence-checked with `eth_getCode`.
**Scope:** the original Mayan route: the input moves over the **Wormhole Token Bridge** to Solana, a driver swaps it on Solana, and the output returns over the Token Bridge. The EVM contract is **MayanSwap**. It has the same address on six chains and a different address on Base. Robinhood Chain (4663) has no MayanSwap. Topics and selectors are chain-agnostic; addresses are network-specific.

MayanSwap emits **no event on the source chain**. A source transaction shows two Wormhole Core `LogMessagePublished` logs: one with `sender` = the chain's Token Bridge (the token transfer to Solana) and one with `sender` = MayanSwap (the swap parameters). On the destination chain `redeem` / `redeemAndUnwrap` completes the Token Bridge transfer and pays the recipient. It emits `Redeemed(emitterChainId, emitterAddress, sequence)`, the key of the Token Bridge VAA that it consumed. For an EVM destination that VAA comes from Solana (emitter chain 1), so an EVM-to-EVM swap has **no single on-chain key**: the path crosses Solana.

---

## 0. Contract families & versions

| Contract | Address | Chains | Role | Upgradeable? |
|----------|---------|--------|------|--------------|
| **MayanSwap** | `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | ETH, Arb, OP, Poly, BNB, Avax | Source: `swap`, `wrapAndSwapETH` (Token Bridge transfer to Solana + Mayan message). Destination: `redeem`, `redeemAndUnwrap`. | No proxy (EIP-1967 implementation slot empty); guardian-controlled pause. |
| **MayanSwap (Base)** | `0x11AA521C888d84f374B63823d9b873CAa3591f55` | Base only | The Base deployment (docs.mayan.finance lists this address for Base). 13,972 B; the same selectors as MayanSwap. | No proxy |
| Wormhole Token Bridge | per chain (§3–§9) | 7 | `tokenBridgeAddress` of the Mayan chain config. Emits `TransferRedeemed` on the destination and publishes the transfer message on the source. | Wormhole proxy |
| Wormhole Core | per chain (§3–§9) | 7 | Emits `LogMessagePublished`. | Wormhole proxy |

`eth_getCode` at `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` on Base returns `0x`, although the Mayan chain config (`sia.mayan.finance/v10/init`) names it as the Base `mayanContractAddress`. The docs table and the chain agree on `0x11AA521C888d84f374B63823d9b873CAa3591f55` for Base.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 MayanSwap (destination chain only)

| topic0 | Event |
|--------|-------|
| `0xf02867db6908ee5f81fd178573ae9385837f0a0a72553f8c08306759a7e0f00e` | `Redeemed(uint16 indexed emitterChainId, bytes32 indexed emitterAddress, uint64 indexed sequence)` — **destination leg / payout.** All three fields are indexed and equal the key of the Token Bridge VAA (`TransferRedeemed` of the same transaction). The amounts are in the `Transfer` rows: Token Bridge → MayanSwap, then MayanSwap → relayer (fee) and → recipient. |

### 1.2 Wormhole events of the same transactions (emitters are Wormhole contracts)

| topic0 | Event |
|--------|-------|
| `0x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2` | `LogMessagePublished(address indexed sender, uint64 sequence, uint32 nonce, bytes payload, uint8 consistencyLevel)` — **source leg markers** (Wormhole Core): one with `sender` = Token Bridge, one with `sender` = MayanSwap. |
| `0xcaf280c8cfeba144da67230d9b009c8f868a75bac9a528fa0474be1ba317c169` | `TransferRedeemed(uint16 indexed emitterChainId, bytes32 indexed emitterAddress, uint64 indexed sequence)` — Token Bridge, destination; same key as `Redeemed`. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — ERC-20 value rows (source: user → MayanSwap → Token Bridge; destination: Token Bridge → MayanSwap → recipient). |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Tuple types: `RelayerFees = (uint64 swapFee, uint64 redeemFee, uint64 refundFee)`, `Recepient = (bytes32 mayanAddr, uint16 mayanChainId, bytes32 auctionAddr, bytes32 destAddr, uint16 destChainId, bytes32 referrer, bytes32 refundAddr)`, `Criteria = (uint256 transferDeadline, uint64 swapDeadline, uint64 amountOutMin, bool unwrap, uint64 gasDrop, bytes customPayload)`. All selectors below are present in the bytecode of `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` (Ethereum) and `0x11AA521C888d84f374B63823d9b873CAa3591f55` (Base).

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6111ad25` | `swap((uint64 swapFee, uint64 redeemFee, uint64 refundFee) relayerFees, (bytes32 mayanAddr, uint16 mayanChainId, bytes32 auctionAddr, bytes32 destAddr, uint16 destChainId, bytes32 referrer, bytes32 refundAddr) recipient, bytes32 tokenOutAddr, uint16 tokenOutChainId, (uint256 transferDeadline, uint64 swapDeadline, uint64 amountOutMin, bool unwrap, uint64 gasDrop, bytes customPayload) criteria, address tokenIn, uint256 amountIn)` | payable (Wormhole fees). **Source leg, ERC-20.** Chain ids are Wormhole chain ids. |
| `0x1eb1cff0` | `wrapAndSwapETH((uint64 swapFee, uint64 redeemFee, uint64 refundFee) relayerFees, (bytes32 mayanAddr, uint16 mayanChainId, bytes32 auctionAddr, bytes32 destAddr, uint16 destChainId, bytes32 referrer, bytes32 refundAddr) recipient, bytes32 tokenOutAddr, uint16 tokenOutChainId, (uint256 transferDeadline, uint64 swapDeadline, uint64 amountOutMin, bool unwrap, uint64 gasDrop, bytes customPayload) criteria)` | payable. **Source leg, native** (wrapped, then bridged). |
| `0x9945e3d3` | `redeem(bytes encodedVm)` | payable. **Destination leg.** Emits `Redeemed`. |
| `0xc0e6d169` | `redeemAndUnwrap(bytes encodedVm)` | **Destination leg**, unwraps to native. Emits `Redeemed`. |
| `0xbedb86fb` | `setPause(bool _pause)` | Guardian only. **No event.** `isPaused()` `0xb187bd26` reads the flag. |
| `0xdf2ab5bb` | `sweepToken(address token, uint256 amount, address to)` | **Guardian only; moves any token out. No event.** |
| `0x580094b7` | `sweepEth(uint256 amount, address to)` | Guardian only. No event. |
| `0x2fcb4f04` | `changeGuardian(address newGuardian)` | Guardian only. |
| `0x459656ee` | `claimGuardian()` | Next guardian. |

---

## 3. Addresses — Ethereum (chain ID 1, Wormhole chain ID 2)

Verified with `eth_getCode` on 2026-09-29.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanSwap** | `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | 13,890 B (one code hash on all six chains). |
| Wormhole Token Bridge | `0x3ee18B2214AFF97000D974cf647E7C347E8fa585` | `tokenBridgeAddress` of the Mayan chain config. 680-B EIP-1967 proxy. |
| Wormhole Core | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | Emits `LogMessagePublished`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `Redeemed` 5; `LogMessagePublished` with `sender` = MayanSwap 8.

## 4. Addresses — Base (chain ID 8453, Wormhole chain ID 30)

Verified with `eth_getCode` on 2026-09-29.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanSwap** | `0x11AA521C888d84f374B63823d9b873CAa3591f55` | 13,972 B (Base only; `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` has no code on Base). |
| Wormhole Token Bridge | `0x8d2de8d2f73F1F4cAB472AC9A881C9b123C79627` | `tokenBridgeAddress` of the Mayan chain config. 680-B EIP-1967 proxy. |
| Wormhole Core | `0xbebdb6C8ddC678FfA9f8748f85C815C556Dd8ac6` | Emits `LogMessagePublished`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `Redeemed` 0; `LogMessagePublished` with `sender` = MayanSwap 0.

## 5. Addresses — Arbitrum One (chain ID 42161, Wormhole chain ID 23)

Verified with `eth_getCode` on 2026-09-29.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanSwap** | `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | 13,890 B (one code hash on all six chains). |
| Wormhole Token Bridge | `0x0b2402144Bb366A632D14B83F244D2e0e21bD39c` | `tokenBridgeAddress` of the Mayan chain config. 680-B EIP-1967 proxy. |
| Wormhole Core | `0xa5f208e072434bC67592E4C49C1B991BA79BCA46` | Emits `LogMessagePublished`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `Redeemed` 0; `LogMessagePublished` with `sender` = MayanSwap 0.

## 6. Addresses — Optimism (chain ID 10, Wormhole chain ID 24)

Verified with `eth_getCode` on 2026-09-29.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanSwap** | `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | 13,890 B (one code hash on all six chains). |
| Wormhole Token Bridge | `0x1D68124e65faFC907325e3EDbF8c4d84499DAa8b` | `tokenBridgeAddress` of the Mayan chain config. 680-B EIP-1967 proxy. |
| Wormhole Core | `0xEe91C335eab126dF5fDB3797EA9d6aD93aeC9722` | Emits `LogMessagePublished`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `Redeemed` 0; `LogMessagePublished` with `sender` = MayanSwap 0.

## 7. Addresses — Polygon PoS (chain ID 137, Wormhole chain ID 5)

Verified with `eth_getCode` on 2026-09-29.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanSwap** | `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | 13,890 B (one code hash on all six chains). |
| Wormhole Token Bridge | `0x5a58505a96D1dbf8dF91cB21B54419FC36e93fdE` | `tokenBridgeAddress` of the Mayan chain config. 729-B EIP-1967 proxy. |
| Wormhole Core | `0x7A4B5a56256163F07b2C80A7cA55aBE66c4ec4d7` | Emits `LogMessagePublished`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `Redeemed` 0; `LogMessagePublished` with `sender` = MayanSwap not measured.

## 8. Addresses — BNB Smart Chain (chain ID 56, Wormhole chain ID 4)

Verified with `eth_getCode` on 2026-09-29.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanSwap** | `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | 13,890 B (one code hash on all six chains). |
| Wormhole Token Bridge | `0xB6F6D86a8f9879A9c87f643768d9efc38c1Da6E7` | `tokenBridgeAddress` of the Mayan chain config. 729-B EIP-1967 proxy. |
| Wormhole Core | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | Emits `LogMessagePublished`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `Redeemed` 0; `LogMessagePublished` with `sender` = MayanSwap 0.

## 9. Addresses — Avalanche C-Chain (chain ID 43114, Wormhole chain ID 6)

Verified with `eth_getCode` on 2026-09-29.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanSwap** | `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | 13,890 B (one code hash on all six chains). |
| Wormhole Token Bridge | `0x0e082F06FF657D94310cB8cE8B0D9a04541d8052` | `tokenBridgeAddress` of the Mayan chain config. 680-B EIP-1967 proxy. |
| Wormhole Core | `0x54a8e5f9c4CbA08F9943965859F6c34eAF03E26c` | Emits `LogMessagePublished`. |

Pinned window 2026-09-28 00:00–12:00 UTC: `Redeemed` 0; `LogMessagePublished` with `sender` = MayanSwap 0.

---

## 10. Cross-chain summary

| Chain | EVM ID | Wormhole ID | MayanSwap | Token Bridge | `Redeemed` / source messages in the pinned window |
|-------|-------:|------------:|-----------|--------------|------:|
| Ethereum | 1 | 2 | ✅ `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | ✅ `0x3ee18B2214AFF97000D974cf647E7C347E8fa585` | 5 / 8 |
| Base | 8453 | 30 | ✅ `0x11AA521C888d84f374B63823d9b873CAa3591f55` (`0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` has no code there) | ✅ `0x8d2de8d2f73F1F4cAB472AC9A881C9b123C79627` | 0 / 0 |
| Arbitrum One | 42161 | 23 | ✅ `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | ✅ `0x0b2402144Bb366A632D14B83F244D2e0e21bD39c` | 0 / 0 |
| Optimism | 10 | 24 | ✅ `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | ✅ `0x1D68124e65faFC907325e3EDbF8c4d84499DAa8b` | 0 / 0 |
| Polygon PoS | 137 | 5 | ✅ `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | ✅ `0x5a58505a96D1dbf8dF91cB21B54419FC36e93fdE` | 0 / not measured |
| BNB Smart Chain | 56 | 4 | ✅ `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | ✅ `0xB6F6D86a8f9879A9c87f643768d9efc38c1Da6E7` | 0 / 0 |
| Avalanche C-Chain | 43114 | 6 | ✅ `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4` | ✅ `0x0e082F06FF657D94310cB8cE8B0D9a04541d8052` | 0 / 0 |
| **Robinhood Chain** | 4663 | — | ❌ (no code at either address) | — | — |

The swap itself runs on Solana (Mayan program `FC4eXxkyrMPTjiYUpp4EAnkmwMbQyZ6NDCh1kfLn6vsf`, Wormhole chain 1), outside the eight chains.

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Admin authority |
|----------|---------|-----------|-----------------|
| **MayanSwap** (both addresses) | **Not a proxy.** | EIP-1967 implementation and beacon slots empty; full runtime (13,890 / 13,972 B). | A guardian (two-step `changeGuardian` + `claimGuardian`; no `guardian()` getter in the SDK ABI) can pause and `sweepToken` / `sweepEth`. No admin function emits an event. |
| Wormhole Token Bridge, Wormhole Core | Wormhole's own EIP-1967 proxies (680 B on Ethereum). | Implementation slot populated. | Wormhole governance (see a Wormhole reference). |

---

## 12. Detection invariants & gotchas

1. **The source leg has no MayanSwap event.** A Wormhole-swap source transaction has two `LogMessagePublished` logs from the Wormhole Core: `sender` = the Token Bridge (the transfer to Solana) and `sender` = MayanSwap (the swap parameters). Sample (Ethereum, through the Forwarder `forwardEth`): Token Bridge sequence 691,249 and MayanSwap sequence 85,519 in `0xcbdd595d35fa2f6e14581f7c605ab78efbecde570d9ebd0a59dc8f5d1ee76a0a`. Count the source leg as `LogMessagePublished` with topic1 = MayanSwap.
2. **`Redeemed` repeats the Token Bridge key.** `(emitterChainId, emitterAddress, sequence)` of `Redeemed` equals that of the Token Bridge `TransferRedeemed` in the same transaction. For an EVM destination the emitter is the Solana Token Bridge (chain 1, emitter `0xec7372995d5cc8732397fb0ad35c0121e0eaa90d26f828a534cab54391b3a4f5` in the sample), so the key belongs to the Solana → destination hop.
3. **EVM → EVM has no single on-chain key.** The source VAA (source Token Bridge → Solana) and the destination VAA (Solana → destination) are different messages; the link runs through the Mayan program on Solana. Only a Solana-origin swap links directly (`Redeemed` key = the Solana Token Bridge VAA).
4. **The payout goes through two transfers.** On the destination the Token Bridge releases (or mints wrapped) tokens to MayanSwap, then MayanSwap pays the relayer fee and the recipient (`redeemAndUnwrap` sends native currency by call, with no ERC-20 row to the recipient).
5. **Wrapped assets.** A token that is not native to the destination arrives as a Wormhole-wrapped token minted by the Token Bridge (a `Transfer` from `0x0`), not as the canonical token.
6. **Low activity.** In the pinned window the only `Redeemed` logs were 5 on Ethereum. The source messages (`LogMessagePublished` with `sender` = MayanSwap) were 8 on Ethereum and 0 on Base, Arbitrum, Optimism, BNB and Avalanche; Polygon was not measured (its log query did not finish). Do not treat a 0 as proof that the route is closed.
7. **Base uses another address.** `0x11AA521C888d84f374B63823d9b873CAa3591f55`; the Mayan chain config still names `0xBF5f3f65102aE745A48BD521d10BaB5BF02A9eF4`, which has no code on Base.
8. **Admin changes emit no event.** Watch `setPause` `0xbedb86fb`, `sweepToken` `0xdf2ab5bb`, `sweepEth` `0x580094b7`, `changeGuardian` `0x2fcb4f04`, `claimGuardian` `0x459656ee`.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_MAYAN_SWAP_REDEEMED        = '\xf02867db6908ee5f81fd178573ae9385837f0a0a72553f8c08306759a7e0f00e'
TOPIC_WORMHOLE_LOG_MESSAGE_PUBLISHED = '\x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2'
TOPIC_WORMHOLE_TRANSFER_REDEEMED = '\xcaf280c8cfeba144da67230d9b009c8f868a75bac9a528fa0474be1ba317c169'
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors (chain-agnostic) =====
SEL_MAYAN_SWAP                   = '\x6111ad25'
SEL_MAYAN_WRAP_AND_SWAP_ETH      = '\x1eb1cff0'
SEL_MAYAN_SWAP_REDEEM            = '\x9945e3d3'
SEL_MAYAN_SWAP_REDEEM_AND_UNWRAP = '\xc0e6d169'
SEL_MAYAN_SWAP_SWEEP_TOKEN       = '\xdf2ab5bb'
SEL_MAYAN_SWAP_SWEEP_ETH         = '\x580094b7'
SEL_MAYAN_SET_PAUSE              = '\xbedb86fb'
SEL_MAYAN_IS_PAUSED              = '\xb187bd26'

-- ===== Addresses (network-specific) =====
-- Ethereum (1)
ETH_MAYAN_SWAP             = '\xbf5f3f65102ae745a48bd521d10bab5bf02a9ef4'
ETH_WORMHOLE_TOKEN_BRIDGE  = '\x3ee18b2214aff97000d974cf647e7c347e8fa585'
ETH_WORMHOLE_CORE          = '\x98f3c9e6e3face36baad05fe09d375ef1464288b'
-- Base (8453)
BASE_MAYAN_SWAP            = '\x11aa521c888d84f374b63823d9b873caa3591f55'
BASE_WORMHOLE_TOKEN_BRIDGE = '\x8d2de8d2f73f1f4cab472ac9a881c9b123c79627'
BASE_WORMHOLE_CORE         = '\xbebdb6c8ddc678ffa9f8748f85c815c556dd8ac6'
-- Arbitrum One (42161)
ARB_MAYAN_SWAP             = '\xbf5f3f65102ae745a48bd521d10bab5bf02a9ef4'
ARB_WORMHOLE_TOKEN_BRIDGE  = '\x0b2402144bb366a632d14b83f244d2e0e21bd39c'
ARB_WORMHOLE_CORE          = '\xa5f208e072434bc67592e4c49c1b991ba79bca46'
-- Optimism (10)
OP_MAYAN_SWAP              = '\xbf5f3f65102ae745a48bd521d10bab5bf02a9ef4'
OP_WORMHOLE_TOKEN_BRIDGE   = '\x1d68124e65fafc907325e3edbf8c4d84499daa8b'
OP_WORMHOLE_CORE           = '\xee91c335eab126df5fdb3797ea9d6ad93aec9722'
-- Polygon PoS (137)
POLY_MAYAN_SWAP            = '\xbf5f3f65102ae745a48bd521d10bab5bf02a9ef4'
POLY_WORMHOLE_TOKEN_BRIDGE = '\x5a58505a96d1dbf8df91cb21b54419fc36e93fde'
POLY_WORMHOLE_CORE         = '\x7a4b5a56256163f07b2c80a7ca55abe66c4ec4d7'
-- BNB Smart Chain (56)
BNB_MAYAN_SWAP             = '\xbf5f3f65102ae745a48bd521d10bab5bf02a9ef4'
BNB_WORMHOLE_TOKEN_BRIDGE  = '\xb6f6d86a8f9879a9c87f643768d9efc38c1da6e7'
BNB_WORMHOLE_CORE          = '\x98f3c9e6e3face36baad05fe09d375ef1464288b'
-- Avalanche C-Chain (43114)
AVAX_MAYAN_SWAP            = '\xbf5f3f65102ae745a48bd521d10bab5bf02a9ef4'
AVAX_WORMHOLE_TOKEN_BRIDGE = '\x0e082f06ff657d94310cb8ce8b0d9a04541d8052'
AVAX_WORMHOLE_CORE         = '\x54a8e5f9c4cba08f9943965859f6c34eaf03e26c'
-- Robinhood Chain (4663): no MayanSwap
```

---

## 14. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the SDK ABI `MayanSwapArtifact` (struct types `MayanSwap.RelayerFees`, `MayanSwap.Recepient`, `MayanSwap.Criteria`). MayanSwap is not verified on the explorer, so every selector was checked as a PUSH4 in the deployed bytecode of both addresses. `Redeemed` and `TransferRedeemed` were matched against the decoded sample below.
- **Addresses:** MayanSwap from docs.mayan.finance "Wormhole Swap"; the Token Bridge addresses from the Mayan chain config (`tokenBridgeAddress`); the Wormhole Core from `wormhole()` of the Swift contracts. Every address was existence-checked with `eth_getCode` on all eight chains.
- **Samples read in full (Ethereum):** `0x054fcd0d83bbe377056e0d9d3028a417c1fc82800dcdb5eedd881ce8fede316a` (`Redeemed(1, 0xec7372995d5cc8732397fb0ad35c0121e0eaa90d26f828a534cab54391b3a4f5, 1,426,218)`: WETH from the Token Bridge to MayanSwap, then to the relayer and the recipient), `0xcbdd595d35fa2f6e14581f7c605ab78efbecde570d9ebd0a59dc8f5d1ee76a0a` (source leg through the Forwarder).
- **Activity:** pinned 12-hour window 2026-09-28 00:00–12:00 UTC, `eth_getLogs` (the source-message count filters `LogMessagePublished` on topic1 = MayanSwap). A 0 is a measurement of this window only.

Authoritative sources (opened for this document):
- Docs — [Wormhole Swap](https://docs.mayan.finance/architecture/wh-swap) (source `mayan-finance/docs`, `architecture/wh-swap.mdx`) · Mayan chain config `https://sia.mayan.finance/v10/init`
- Repository — [mayan-finance/swap-sdk](https://github.com/mayan-finance/swap-sdk) (`src/evm/MayanSwapArtifact.ts`, `src/evm/evmSwap.ts`, `src/wormhole.ts`)

