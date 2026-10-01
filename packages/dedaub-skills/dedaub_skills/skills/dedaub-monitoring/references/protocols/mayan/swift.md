# Mayan Swift (v2 and v1) — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche; NOT Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the verified sources on Blockscout (`SwiftSource`, `SwiftDest`, `MayanSwift`), the `mayan-finance/swap-sdk` ABIs and docs.mayan.finance (`architecture/swift`). Topic0 and selector values were recomputed as `keccak256(signature)` from the verified ABIs and matched against live logs and transaction selectors. Addresses were existence-checked with `eth_getCode`.
**Scope:** Swift, the intent route that carries most Mayan orders. Swift v2 splits each chain into a source contract (**SwiftSource**, escrow) and a destination contract (**SwiftDest**, fills and cancels). Swift v1 (**MayanSwift**) is one contract per chain and is retired. Both generations have the same address on each of the seven EVM chains where they exist. Robinhood Chain (4663) has no Swift contract. Topics and selectors are chain-agnostic; addresses are network-specific.

A Swift order has two chains and four steps. (1) On the source chain the user's tokens are locked in SwiftSource: `OrderCreated(key)`. (2) On the destination chain a driver (solver) pays the user from its own funds through SwiftDest: `OrderFulfilled(key, sequence, fulfilledAmount)`. SwiftDest publishes a Wormhole message with the unlock data. (3) Back on the source chain the Wormhole VAA unlocks the escrow to the driver: `OrderUnlocked(key)`. (4) If no driver fills before the deadline, SwiftDest cancels (`OrderCanceled`) and SwiftSource refunds the trader (`OrderRefunded`).

The link key is the order hash `key`. It is on chain on both sides: the same `bytes32` appears in all five events. No Swift event parameter is indexed, so `key` is data word 0. Swift uses **Wormhole chain ids** (Ethereum 2, BNB 4, Polygon 5, Avalanche 6, Arbitrum 23, Optimism 24, Base 30), not EVM chain ids.

---

## 0. Contract families & versions

| Contract | Address (same on every listed chain) | Chains | Role | Upgradeable? |
|----------|--------------------------------------|--------|------|--------------|
| **SwiftSource** (Swift v2 source) | `0x40fFE85A28DC9993541449464d7529a922142960` | ETH, Base, Arb, OP, Poly, BNB, Avax | Escrow. `createOrderWithToken` / `createOrderWithSig` lock the input (ETH input is locked as WETH); `unlockSingle` / `unlockCompressedBatch` pay the driver; `refundOrder` pays the trader. | No (plain contract; guardian-controlled settings) |
| **SwiftDest** (Swift v2 destination) | `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` | same 7 | `fulfillOrder` / `fulfillSimple`: the driver pays the user through this contract; `cancelOrder` after the deadline; `postBatch` sends batched unlock messages; `settleWithPayload` releases payload orders. | No |
| MayanSwift (Swift v1) | `0xC38e4e6A15593f908255214653d3D947CA1c2338` | same 7 | Original one-contract Swift (create, fulfil, unlock, cancel, refund in one contract). Docs: "not supported long term". 0 events in the pinned window. | No |
| Swift fee manager (v2) | `0x54914a963c4197172130c26d496a367bd6609d88` (183-B EIP-1967 proxy) | 7 (the same address on every chain) | `feeManager()` of SwiftSource. Receives protocol, referrer, cancel and refund fees. The v2 constructor on Ethereum set `0x26227ACE40de5671e8355fCAFf65a0522aa7b303`; the guardian later changed it. | — |
| Auction verifier | `0x2cba4739a9703ba57d5f50476d51c3a9bcc86de8` | 7 (3,607 B, one code hash) | `auctionVerifier()` of SwiftDest. Verifies the auction result that `fulfillOrder` needs (auction chain id 42069, auction address `0x0000000000000000000000000000000000000000000000000000000000004155` per the verified constructor). | — |
| Wormhole Core | per chain (§3–§9) | 7 | `wormhole()` of SwiftSource and SwiftDest. Emits `LogMessagePublished` for every unlock, batch and cancel message. | Wormhole's own proxy |

Swift v2 constructor values on Ethereum (verified source): `_refundVerifier` = the Wormhole Core, `_refundEmitterChainId` = 21, `_refundEmitterAddr` = `0x5f96109d347db7d683866283b2eee8a5bf0fe0e8671fbdfb7917e7b9464fc1a5` (the emitter of "fast" refund messages), `_rescueVault` = `0x71b6E467F549B367487a28eF07520147a90a5f3C`, `_weth` = WETH.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Swift events (identical topic0 in SwiftSource, SwiftDest and MayanSwift v1)

The parameter names differ between the verified contracts (`netAmount`, `fulfilledAmount`, `refundedAmount`), but the types are the same, so the topic0 values are shared. **Disambiguate by the emitter.** No parameter is indexed.

| topic0 | Event |
|--------|-------|
| `0x918554b6bd6e2895ce6553de5de0e1a69db5289aa0e4fe193a0dcd1f14347477` | `OrderCreated(bytes32 key)` — **source leg** (SwiftSource; v1: MayanSwift). No amount: join the ERC-20 `Transfer` into SwiftSource in the same transaction. |
| `0x6ec9b1b5a9f54d929394f18dac4ba1b1cc79823f2266c2d09cab8a3b4700b40b` | `OrderFulfilled(bytes32 key, uint64 sequence, uint256 fulfilledAmount)` — **destination leg / payout** (SwiftDest). `sequence` = the Wormhole sequence of the unlock message, or 0 when the unlock is batched. `fulfilledAmount` = the amount the driver paid (before a payload-type-2 hold). |
| `0x4bdcff348c4d11383c487afb95f732f243d93fbfc478aa736a4981cf6a640911` | `OrderUnlocked(bytes32 key)` — **escrow pays the driver** (SwiftSource). No amount: the net `tokenIn` goes to the unlock receiver in the same call; fees go to the fee manager. |
| `0x45a58de39e77dfc9cd1d63970a706575668048121d822749d2298eb75125123e` | `OrderCanceled(bytes32 key, uint64 sequence)` — **status only** (SwiftDest, after the deadline). No value moves; `sequence` = the Wormhole sequence of the refund message. |
| `0xbff5487f6422ba4acbcde6bd5e0ccb83124c240b9deb6a72e7b5eb8c7b71d6fc` | `OrderRefunded(bytes32 key, uint256 refundedAmount)` — **refund to the trader** (SwiftSource). Amount = net of cancel and refund fees. If the input was ETH, the trader gets native ETH (WETH is unwrapped), so there is no ERC-20 row to the trader. |

### 1.2 Wormhole Core (emitted in Swift transactions; emitter = the chain's Wormhole Core)

| topic0 | Event |
|--------|-------|
| `0x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2` | `LogMessagePublished(address indexed sender, uint64 sequence, uint32 nonce, bytes payload, uint8 consistencyLevel)` — `sender` = SwiftDest for unlock, batch and cancel messages. `sequence` equals `OrderFulfilled.sequence` / `OrderCanceled.sequence`. |

### 1.3 Value row

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — ERC-20. Lock: `msg.sender` → SwiftSource. Fill: driver → SwiftDest → user. Unlock: SwiftSource → driver (and → fee manager). Refund: SwiftSource → trader. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Tuple types (v2): `OrderParams = (uint8 payloadType, bytes32 trader, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, uint8 referrerBps, uint8 auctionMode, bytes32 random)`, `ExtraParams = (uint16 srcChainId, bytes32 tokenIn, uint8 protocolBps, bytes32 customPayloadHash)`, `UnlockParams = (bytes32 recipient, bytes32 driver, bool batch)`, `PermitParams = (uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s)`.

### 2.1 SwiftSource (v2)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa3a30834` | `createOrderWithToken(address tokenIn, uint256 amountIn, (uint8 payloadType, bytes32 trader, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, uint8 referrerBps, uint8 auctionMode, bytes32 random) params, bytes customPayload)` | Pulls `tokenIn` from `msg.sender` (`tokenIn` = zero means WETH). Emits `OrderCreated`. Called by the Forwarder (seen) or directly. |
| `0x6147435b` | `createOrderWithSig(address tokenIn, uint256 amountIn, (uint8 payloadType, bytes32 trader, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, uint8 referrerBps, uint8 auctionMode, bytes32 random) params, bytes customPayload, uint256 submissionFee, bytes signedOrderHash, (uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) permitParams)` | Gasless: a relayer submits with the trader's EIP-712 signature (domain "Mayan Swift"); pulls from the trader. Emits `OrderCreated`. |
| `0x119abf67` | `unlockSingle(bytes encodedVm)` | Wormhole VAA from SwiftDest of the destination chain. Pays the driver. Emits `OrderUnlocked`. |
| `0x2d67b5ea` | `unlockCompressedBatch(bytes encodedVm, bytes encodedPayload, uint16[] indexes)` | Batched unlock (the VAA carries the hash of the packed unlock messages). One `OrderUnlocked` per order. |
| `0xac432e63` | `refundOrder(bytes encodedVm, bool fast)` | Refund VAA: from SwiftDest of the destination chain (`fast` = false) or from the fast-refund emitter (`fast` = true). Emits `OrderRefunded`. |
| `0xdae2fc12` | `rescue(bytes encodedVm)` | **Guardian only**, VAA from the Solana emitter. Can set an order status and move tokens to the rescue vault. No dedicated event. |
| `0xbedb86fb` | `setPause(bool _pause)` | Guardian only. **No event.** |
| `0x472d35b9` | `setFeeManager(address _feeManager)` | Guardian only. **No event.** |
| `0xb365b191` | `setEmitters(uint16[] chainIds, bytes32[] addresses)` | Guardian only. Sets the trusted SwiftDest emitter per Wormhole chain id. **No event.** |
| `0x46963505` | `setRefundVerifier(bytes encodedVm)` | VAA-gated. Changes the fast-refund verifier. **No event.** |
| `0x2fcb4f04` | `changeGuardian(address newGuardian)` | Guardian only; step 1 of 2. **No event.** |
| `0x459656ee` | `claimGuardian()` | The next guardian; step 2 of 2. **No event.** |

Views used in §3–§9: `guardian()` `0x452a9320`, `paused()` `0x5c975abb`, `feeManager()` `0xd0fb0203`, `wormhole()` `0x84acd1bb`, `emitters(uint16)` `0x9e70a740`, `orders(bytes32)` (status, amountIn, destChainId).

### 2.2 SwiftDest (v2)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x19535a54` | `fulfillOrder(uint256 fulfillAmount, bytes encodedVm, (uint8 payloadType, bytes32 trader, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, uint8 referrerBps, uint8 auctionMode, bytes32 random) params, (uint16 srcChainId, bytes32 tokenIn, uint8 protocolBps, bytes32 customPayloadHash) extraParams, (bytes32 recipient, bytes32 driver, bool batch) unlockParams, (uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) permit)` | payable. The auction winner pulls `tokenOut` from itself and pays `destAddr` (native: `msg.value`). Emits `OrderFulfilled` (+ `LogMessagePublished` unless `batch`). |
| `0xf5568823` | `fulfillSimple(uint256 fulfillAmount, bytes32 orderHash, (uint8 payloadType, bytes32 trader, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, uint8 referrerBps, uint8 auctionMode, bytes32 random) params, (uint16 srcChainId, bytes32 tokenIn, uint8 protocolBps, bytes32 customPayloadHash) extraParams, (bytes32 recipient, bytes32 driver, bool batch) unlockParams, (uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) permit)` | payable. Limit orders (`auctionMode` = 1) without an auction VAA. Emits `OrderFulfilled`. |
| `0x843bb559` | `cancelOrder(bytes32 orderHash, (uint8 payloadType, bytes32 trader, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, uint8 referrerBps, uint8 auctionMode, bytes32 random) params, (uint16 srcChainId, bytes32 tokenIn, uint8 protocolBps, bytes32 customPayloadHash) extraParams, bytes32 canceler)` | payable (Wormhole fee). Only after the deadline. Emits `OrderCanceled` + `LogMessagePublished` (refund message). |
| `0x4a85d788` | `postBatch(bytes32[] orderHashes)` | payable. Publishes one compressed unlock message for batched fills. **No Swift event** (only `LogMessagePublished`). |
| `0xb3f34dc7` | `settleWithPayload((uint8 payloadType, bytes32 trader, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, uint8 referrerBps, uint8 auctionMode, bytes32 random) params, (uint16 srcChainId, bytes32 tokenIn, uint8 protocolBps, bytes32 customPayloadHash) extraParams)` | Called by `destAddr` for payload orders (`payloadType` = 2). Pays the held amount. **No event.** |
| `0xdae2fc12` | `rescue(bytes encodedVm)` | Guardian only; moves tokens to the rescue vault. |
| `0x814aa669` | `setAuctionConfig(address _auctionVerifier, uint16 _auctionChainId, bytes32 _auctionAddr)` | Guardian only. **No event.** |
| `0x538ee295` | `setConsistencyLevel(uint8 _consistencyLevel)` | Guardian only. **No event.** |
| `0xb365b191` | `setEmitters(uint16[] chainIds, bytes32[] addresses)` | Guardian only. **No event.** |
| `0xbedb86fb` | `setPause(bool _pause)` | Guardian only. **No event.** |
| `0x2fcb4f04` | `changeGuardian(address newGuardian)` | Guardian only. |
| `0x459656ee` | `claimGuardian()` | Next guardian. |

### 2.3 MayanSwift (v1)

v1 tuple `OrderParams = (bytes32 trader, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, uint8 referrerBps, uint8 auctionMode, bytes32 random)`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb866e173` | `createOrderWithEth((bytes32 trader, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, uint8 referrerBps, uint8 auctionMode, bytes32 random) params)` | payable; native input. Emits `OrderCreated`. |
| `0x8e8d142b` | `createOrderWithToken(address tokenIn, uint256 amountIn, (bytes32 trader, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, uint8 referrerBps, uint8 auctionMode, bytes32 random) params)` | Emits `OrderCreated`. |
| `0x3a30b37f` | `createOrderWithSig(address tokenIn, uint256 amountIn, (bytes32 trader, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, uint8 referrerBps, uint8 auctionMode, bytes32 random) params, uint256 submissionFee, bytes signedOrderHash, (uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) permitParams)` | Gasless create. |
| `0x488c3591` | `fulfillOrder(uint256 fulfillAmount, bytes encodedVm, bytes32 recepient, bool batch)` | payable. Destination fill (auction VAA from Solana). Emits `OrderFulfilled`. |
| `0x7226f4e0` | `fulfillSimple(uint256 fulfillAmount, bytes32 orderHash, uint16 srcChainId, bytes32 tokenIn, uint8 protocolBps, (bytes32 trader, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, uint8 referrerBps, uint8 auctionMode, bytes32 random) params, bytes32 recepient, bool batch)` | payable. Limit-order fill. |
| `0x119abf67` | `unlockSingle(bytes encodedVm)` | Emits `OrderUnlocked`. |
| `0x97b6e003` | `unlockBatch(bytes encodedVm)` | Batched unlock. |
| `0x526bb865` | `cancelOrder(bytes32 tokenIn, (bytes32 trader, bytes32 tokenOut, uint64 minAmountOut, uint64 gasDrop, uint64 cancelFee, uint64 refundFee, uint64 deadline, bytes32 destAddr, uint16 destChainId, bytes32 referrerAddr, uint8 referrerBps, uint8 auctionMode, bytes32 random) params, uint16 srcChainId, uint8 protocolBps, bytes32 canceler)` | payable. Emits `OrderCanceled`. |
| `0xfeea83f1` | `refundOrder(bytes encodedVm)` | Emits `OrderRefunded`. |
| `0x4a85d788` | `postBatch(bytes32[] orderHashes)` | Same selector as v2. |
| `0xbedb86fb` | `setPause(bool _pause)` | Guardian only. |
| `0x472d35b9` | `setFeeManager(address _feeManager)` | Guardian only. |
| `0x538ee295` | `setConsistencyLevel(uint8 _consistencyLevel)` | Guardian only. |

---

## 3. Addresses — Ethereum (chain ID 1, Wormhole chain ID 2)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on every other Swift chain.

| Role | Address | Code / note |
|------|---------|-------------|
| **SwiftSource** (v2) | `0x40fFE85A28DC9993541449464d7529a922142960` | 22,153 B. `guardian()` = `0xb4cdc16e6afcca48b6fade7302b6590c664dca5a`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| **SwiftDest** (v2) | `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` | 18,148 B. `auctionVerifier()` = `0x2cba4739a9703ba57d5f50476d51c3a9bcc86de8`. |
| MayanSwift (v1) | `0xC38e4e6A15593f908255214653d3D947CA1c2338` | 23,669 B. Retired. |
| Wormhole Core | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | `wormhole()` of SwiftSource. |

Pinned window 2026-09-28 00:00–12:00 UTC: `OrderCreated` 789, `OrderUnlocked` 786, `OrderRefunded` 16 (SwiftSource); `OrderFulfilled` 722, `OrderCanceled` 9 (SwiftDest); 0 events at MayanSwift v1.

## 4. Addresses — Base (chain ID 8453, Wormhole chain ID 30)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on every other Swift chain.

| Role | Address | Code / note |
|------|---------|-------------|
| **SwiftSource** (v2) | `0x40fFE85A28DC9993541449464d7529a922142960` | 22,153 B. `guardian()` = `0xb4cdc16e6afcca48b6fade7302b6590c664dca5a`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| **SwiftDest** (v2) | `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` | 18,148 B. `auctionVerifier()` = `0x2cba4739a9703ba57d5f50476d51c3a9bcc86de8`. |
| MayanSwift (v1) | `0xC38e4e6A15593f908255214653d3D947CA1c2338` | 23,669 B. Retired. |
| Wormhole Core | `0xbebdb6C8ddC678FfA9f8748f85C815C556Dd8ac6` | `wormhole()` of SwiftSource. |

Pinned window 2026-09-28 00:00–12:00 UTC: `OrderCreated` 831, `OrderUnlocked` 821, `OrderRefunded` 11 (SwiftSource); `OrderFulfilled` 500, `OrderCanceled` 0 (SwiftDest); 0 events at MayanSwift v1.

## 5. Addresses — Arbitrum One (chain ID 42161, Wormhole chain ID 23)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on every other Swift chain.

| Role | Address | Code / note |
|------|---------|-------------|
| **SwiftSource** (v2) | `0x40fFE85A28DC9993541449464d7529a922142960` | 22,153 B. `guardian()` = `0xb4cdc16e6afcca48b6fade7302b6590c664dca5a`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| **SwiftDest** (v2) | `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` | 18,148 B. `auctionVerifier()` = `0x2cba4739a9703ba57d5f50476d51c3a9bcc86de8`. |
| MayanSwift (v1) | `0xC38e4e6A15593f908255214653d3D947CA1c2338` | 23,669 B. Retired. |
| Wormhole Core | `0xa5f208e072434bC67592E4C49C1B991BA79BCA46` | `wormhole()` of SwiftSource. |

Pinned window 2026-09-28 00:00–12:00 UTC: `OrderCreated` 322, `OrderUnlocked` 316, `OrderRefunded` 5 (SwiftSource); `OrderFulfilled` 159, `OrderCanceled` 2 (SwiftDest); 0 events at MayanSwift v1.

## 6. Addresses — Optimism (chain ID 10, Wormhole chain ID 24)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on every other Swift chain.

| Role | Address | Code / note |
|------|---------|-------------|
| **SwiftSource** (v2) | `0x40fFE85A28DC9993541449464d7529a922142960` | 22,153 B. `guardian()` = `0xb4cdc16e6afcca48b6fade7302b6590c664dca5a`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| **SwiftDest** (v2) | `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` | 18,148 B. `auctionVerifier()` = `0x2cba4739a9703ba57d5f50476d51c3a9bcc86de8`. |
| MayanSwift (v1) | `0xC38e4e6A15593f908255214653d3D947CA1c2338` | 23,669 B. Retired. |
| Wormhole Core | `0xEe91C335eab126dF5fDB3797EA9d6aD93aeC9722` | `wormhole()` of SwiftSource. |

Pinned window 2026-09-28 00:00–12:00 UTC: `OrderCreated` 258, `OrderUnlocked` 265, `OrderRefunded` 0 (SwiftSource); `OrderFulfilled` 47, `OrderCanceled` 0 (SwiftDest); 0 events at MayanSwift v1.

## 7. Addresses — Polygon PoS (chain ID 137, Wormhole chain ID 5)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on every other Swift chain.

| Role | Address | Code / note |
|------|---------|-------------|
| **SwiftSource** (v2) | `0x40fFE85A28DC9993541449464d7529a922142960` | 22,153 B. `guardian()` = `0xb4cdc16e6afcca48b6fade7302b6590c664dca5a`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| **SwiftDest** (v2) | `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` | 18,148 B. `auctionVerifier()` = `0x2cba4739a9703ba57d5f50476d51c3a9bcc86de8`. |
| MayanSwift (v1) | `0xC38e4e6A15593f908255214653d3D947CA1c2338` | 23,669 B. Retired. |
| Wormhole Core | `0x7A4B5a56256163F07b2C80A7cA55aBE66c4ec4d7` | `wormhole()` of SwiftSource. |

Pinned window 2026-09-28 00:00–12:00 UTC: `OrderCreated` 317, `OrderUnlocked` 329, `OrderRefunded` 1 (SwiftSource); `OrderFulfilled` 157, `OrderCanceled` 1 (SwiftDest); 0 events at MayanSwift v1.

## 8. Addresses — BNB Smart Chain (chain ID 56, Wormhole chain ID 4)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on every other Swift chain.

| Role | Address | Code / note |
|------|---------|-------------|
| **SwiftSource** (v2) | `0x40fFE85A28DC9993541449464d7529a922142960` | 22,153 B. `guardian()` = `0xb4cdc16e6afcca48b6fade7302b6590c664dca5a`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| **SwiftDest** (v2) | `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` | 18,148 B. `auctionVerifier()` = `0x2cba4739a9703ba57d5f50476d51c3a9bcc86de8`. |
| MayanSwift (v1) | `0xC38e4e6A15593f908255214653d3D947CA1c2338` | 23,669 B. Retired. |
| Wormhole Core | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | `wormhole()` of SwiftSource. |

Pinned window 2026-09-28 00:00–12:00 UTC: `OrderCreated` 1,979, `OrderUnlocked` 1,957, `OrderRefunded` 15 (SwiftSource); `OrderFulfilled` 2,179, `OrderCanceled` 10 (SwiftDest); 0 events at MayanSwift v1.

## 9. Addresses — Avalanche C-Chain (chain ID 43114, Wormhole chain ID 6)

Verified with `eth_getCode` on 2026-09-29. Same literal addresses as on every other Swift chain.

| Role | Address | Code / note |
|------|---------|-------------|
| **SwiftSource** (v2) | `0x40fFE85A28DC9993541449464d7529a922142960` | 22,153 B. `guardian()` = `0xb4cdc16e6afcca48b6fade7302b6590c664dca5a`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| **SwiftDest** (v2) | `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` | 18,148 B. `auctionVerifier()` = `0x2cba4739a9703ba57d5f50476d51c3a9bcc86de8`. |
| MayanSwift (v1) | `0xC38e4e6A15593f908255214653d3D947CA1c2338` | 23,669 B. Retired. |
| Wormhole Core | `0x54a8e5f9c4CbA08F9943965859F6c34eAF03E26c` | `wormhole()` of SwiftSource. |

Pinned window 2026-09-28 00:00–12:00 UTC: `OrderCreated` 48, `OrderUnlocked` 38, `OrderRefunded` 1 (SwiftSource); `OrderFulfilled` 55, `OrderCanceled` 0 (SwiftDest); 0 events at MayanSwift v1.

---

## 10. Cross-chain summary

| Chain | EVM ID | Wormhole ID | SwiftSource `0x40fFE85A28DC9993541449464d7529a922142960` | SwiftDest `0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` | MayanSwift v1 `0xC38e4e6A15593f908255214653d3D947CA1c2338` | `OrderCreated` / `OrderFulfilled` in the pinned window |
|-------|-------:|------------:|:--:|:--:|:--:|------:|
| Ethereum | 1 | 2 | ✅ | ✅ | ✅ | 789 / 722 |
| Base | 8453 | 30 | ✅ | ✅ | ✅ | 831 / 500 |
| Arbitrum One | 42161 | 23 | ✅ | ✅ | ✅ | 322 / 159 |
| Optimism | 10 | 24 | ✅ | ✅ | ✅ | 258 / 47 |
| Polygon PoS | 137 | 5 | ✅ | ✅ | ✅ | 317 / 157 |
| BNB Smart Chain | 56 | 4 | ✅ | ✅ | ✅ | 1,979 / 2,179 |
| Avalanche C-Chain | 43114 | 6 | ✅ | ✅ | ✅ | 48 / 55 |
| **Robinhood Chain** | 4663 | — | ❌ | ❌ | ❌ | — (not a Mayan chain) |

Swift counterparties outside the eight chains (docs "Swift", same EVM addresses; not checked here): Solana (Wormhole 1; program `mayan34VedncxdK2XobtvWFDXQASUTBXhUVzt2kKgny`, v1 `BLZRi6frs4X4DNLw56V4EXai1b6QVESN1BhHBTYM9VcY`), Linea (38), Unichain (44), HyperEVM (47), Monad (48). On Ethereum, `SwiftSource.emitters(1)` = `0xffcec24e0f2cdeade143c339b81a2e8861c0bffcb7e46dfb705e28d6dff9d8cf` (the Solana emitter) and `emitters(21)` (Sui) = 0.

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Admin authority |
|----------|---------|-----------|-----------------|
| **SwiftSource**, **SwiftDest**, **MayanSwift v1** | **Not proxies.** | EIP-1967 implementation and beacon slots empty on all seven chains; full runtime code (22,153 / 18,148 / 23,669 B). | `guardian()`: `0xb4cdc16e6afcca48b6fade7302b6590c664dca5a` for v2 (an EOA on Ethereum, nonce 10) and `0x95d50ebee133c14e2355c7a72b254b3b6eeed6bc` for v1 (an EOA on Ethereum). Two-step change (`changeGuardian` + `claimGuardian`). No admin function emits an event. |
| Swift v2 fee manager | **EIP-1967 proxy** (183 B) | Implementation slot populated (`0x25858b08b6d45be7705c5e85528bd962f73a3c3f` on Ethereum); admin slot empty, so the upgrade check sits in the implementation (not verified; `owner()` and `guardian()` revert). | Upgradeable: watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` on it. It sets the protocol fee (`calcSwiftProtocolBps`) and holds the collected fees. |
| Wormhole Core | Wormhole's own upgradeable proxy (680 B on Ethereum) | — | Wormhole governance (see a Wormhole reference). |

---

## 12. Detection invariants & gotchas

1. **The link key is the order hash `key`, on chain on both sides.** `key = keccak256(encodeKey(Key))`, where `Key` holds the trader, both chain ids, both tokens, the amounts, the fees, the deadline, the referrer and a random salt. The same `bytes32` is data word 0 of `OrderCreated` (source), `OrderFulfilled` and `OrderCanceled` (destination), and `OrderUnlocked` and `OrderRefunded` (source). Sample: key `0xf9a82889612be5e2404eb757d0839d487e22ff7bd8282bb96c5bb59c0c61a5ca` was created on Ethereum in block 26,072,222 and unlocked on Ethereum in block 26,072,250 after its fill on the destination chain.
2. **`OrderCreated` has no amount.** Join the ERC-20 `Transfer` into SwiftSource in the same transaction. Its sender is usually not the user: in the samples it was the Forwarder (reached through the LI.FI diamond `0x1231deb6f5749ef6ce6943a275a1d3e7486f4eae` or an ERC-4337 EntryPoint). Follow the earlier transfers of the transaction back to the user. v2 has no native entry: ETH is locked as WETH (`tokenIn` = zero means WETH), so the user's ETH is the call value to the Forwarder or aggregator.
3. **Do not use `OrderFulfilled.sequence` as a key.** It is the Wormhole sequence of the unlock message, and it is **0 for batched fills**: the unlock data is stored and published later by `postBatch` (no Swift event, only `LogMessagePublished` from SwiftDest), then consumed by `unlockCompressedBatch`.
4. **Payload orders are paid later.** For `payloadType` = 2, SwiftDest keeps the output (`pendingAmounts`) and pays only when `destAddr` calls `settleWithPayload`, which emits **no event**. The `OrderFulfilled` row and the transfer to the user can be in different transactions.
5. **Native payouts are internal calls.** ETH output and gas drops (`gasDrop`) leave SwiftDest by `call`, so they have no ERC-20 row; use the call trace or balance deltas. The same holds for refunds of ETH-origin orders (WETH is unwrapped and sent as ETH).
6. **`OrderUnlocked` pays the driver, not the user.** The escrow on the source chain goes to `unlockReceiver` (the driver's address) minus the referrer and protocol fees, which go to the fee manager. The driver was paid on the destination before, from its own funds.
7. **The refund path has two steps on two chains.** After the deadline, `cancelOrder` on SwiftDest emits `OrderCanceled` (status only) and a Wormhole refund message; `refundOrder` on SwiftSource then pays the trader (net of `cancelFee` to the canceler and `refundFee` to the submitter) and emits `OrderRefunded`. With `fast` = true, SwiftSource also accepts a refund VAA from the emitter on Wormhole chain 21 (`refundEmitterChainId`).
8. **v1 and v2 share every topic0.** MayanSwift v1 emitted 0 events on all seven chains in the pinned window, but it still has code; always filter on the emitter.
9. **A duplicate order can refund in `createOrderWithToken`.** If an order hash already exists with a smaller amount and status CREATED, SwiftSource sends the old amount back to the trader before it records the new one. This is a `Transfer` out of SwiftSource with no `OrderUnlocked` / `OrderRefunded`.
10. **`rescue(bytes)` is the most powerful admin path.** The guardian, with a VAA from the Solana emitter, can set any order status and move escrowed tokens to the rescue vault (`0x71b6E467F549B367487a28eF07520147a90a5f3C` on Ethereum). It emits no Swift event: watch selector `0xdae2fc12` on SwiftSource and SwiftDest.
11. **Admin changes emit no event.** Watch the selectors instead: `setPause` `0xbedb86fb`, `setFeeManager` `0x472d35b9`, `setEmitters` `0xb365b191`, `setRefundVerifier` `0x46963505`, `setAuctionConfig` `0x814aa669`, `setConsistencyLevel` `0x538ee295`, `changeGuardian` `0x2fcb4f04`, `claimGuardian` `0x459656ee`. The v2 `feeManager()` was changed after deployment (constructor `0x26227ACE40de5671e8355fCAFf65a0522aa7b303`, now `0x54914a963c4197172130c26d496a367bd6609d88`), which shows that such changes happen silently.
12. **Chain ids in orders are Wormhole ids** (Ethereum 2, BNB 4, Polygon 5, Avalanche 6, Arbitrum 23, Optimism 24, Base 30, Solana 1).
13. **BNB carries the most Swift orders in the pinned window** (1,979 created, 2,179 fulfilled), then Base and Ethereum.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; shared by SwiftSource, SwiftDest and MayanSwift v1) =====
TOPIC_SWIFT_ORDER_CREATED        = '\x918554b6bd6e2895ce6553de5de0e1a69db5289aa0e4fe193a0dcd1f14347477'
TOPIC_SWIFT_ORDER_FULFILLED      = '\x6ec9b1b5a9f54d929394f18dac4ba1b1cc79823f2266c2d09cab8a3b4700b40b'
TOPIC_SWIFT_ORDER_UNLOCKED       = '\x4bdcff348c4d11383c487afb95f732f243d93fbfc478aa736a4981cf6a640911'
TOPIC_SWIFT_ORDER_CANCELED       = '\x45a58de39e77dfc9cd1d63970a706575668048121d822749d2298eb75125123e'
TOPIC_SWIFT_ORDER_REFUNDED       = '\xbff5487f6422ba4acbcde6bd5e0ccb83124c240b9deb6a72e7b5eb8c7b71d6fc'
TOPIC_WORMHOLE_LOG_MESSAGE_PUBLISHED = '\x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2'
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors (chain-agnostic) =====
-- SwiftSource (v2)
SEL_SWIFT_CREATE_ORDER_WITH_TOKEN = '\xa3a30834'
SEL_SWIFT_CREATE_ORDER_WITH_SIG  = '\x6147435b'
SEL_SWIFT_UNLOCK_SINGLE          = '\x119abf67'
SEL_SWIFT_UNLOCK_COMPRESSED_BATCH = '\x2d67b5ea'
SEL_SWIFT_REFUND_ORDER           = '\xac432e63'
SEL_SWIFT_SET_REFUND_VERIFIER    = '\x46963505'
-- SwiftDest (v2)
SEL_SWIFT_FULFILL_ORDER          = '\x19535a54'
SEL_SWIFT_FULFILL_SIMPLE         = '\xf5568823'
SEL_SWIFT_CANCEL_ORDER           = '\x843bb559'
SEL_SWIFT_POST_BATCH             = '\x4a85d788'
SEL_SWIFT_SETTLE_WITH_PAYLOAD    = '\xb3f34dc7'
SEL_SWIFT_SET_AUCTION_CONFIG     = '\x814aa669'
-- MayanSwift (v1)
SEL_SWIFT_V1_CREATE_ORDER_WITH_ETH = '\xb866e173'
SEL_SWIFT_V1_CREATE_ORDER_WITH_TOKEN = '\x8e8d142b'
SEL_SWIFT_V1_FULFILL_ORDER       = '\x488c3591'
SEL_SWIFT_V1_UNLOCK_BATCH        = '\x97b6e003'
SEL_SWIFT_V1_REFUND_ORDER        = '\xfeea83f1'
SEL_SWIFT_V1_CANCEL_ORDER        = '\x526bb865'
-- shared admin
SEL_MAYAN_RESCUE                 = '\xdae2fc12'
SEL_MAYAN_SET_PAUSE              = '\xbedb86fb'
SEL_MAYAN_SET_FEE_MANAGER        = '\x472d35b9'
SEL_MAYAN_SET_EMITTERS           = '\xb365b191'
SEL_MAYAN_SET_CONSISTENCY_LEVEL  = '\x538ee295'
SEL_MAYAN_CHANGE_GUARDIAN        = '\x2fcb4f04'
SEL_MAYAN_CLAIM_GUARDIAN         = '\x459656ee'

-- ===== Addresses (network-specific; the Swift contracts have the same literal address on all seven chains) =====
-- Ethereum (1)
ETH_SWIFT_SOURCE            = '\x40ffe85a28dc9993541449464d7529a922142960'
ETH_SWIFT_DEST              = '\xd78d199f8c402e7b5cc2abe278df0412400a3bae'
ETH_SWIFT_V1                = '\xc38e4e6a15593f908255214653d3d947ca1c2338'
ETH_SWIFT_FEE_MANAGER       = '\x54914a963c4197172130c26d496a367bd6609d88'
ETH_SWIFT_AUCTION_VERIFIER  = '\x2cba4739a9703ba57d5f50476d51c3a9bcc86de8'
ETH_WORMHOLE_CORE           = '\x98f3c9e6e3face36baad05fe09d375ef1464288b'
ETH_SWIFT_GUARDIAN_EOA      = '\xb4cdc16e6afcca48b6fade7302b6590c664dca5a'
ETH_SWIFT_V1_GUARDIAN_EOA   = '\x95d50ebee133c14e2355c7a72b254b3b6eeed6bc'
ETH_SWIFT_RESCUE_VAULT      = '\x71b6e467f549b367487a28ef07520147a90a5f3c'
-- Base (8453)
BASE_SWIFT_SOURCE           = '\x40ffe85a28dc9993541449464d7529a922142960'
BASE_SWIFT_DEST             = '\xd78d199f8c402e7b5cc2abe278df0412400a3bae'
BASE_SWIFT_V1               = '\xc38e4e6a15593f908255214653d3d947ca1c2338'
BASE_SWIFT_FEE_MANAGER      = '\x54914a963c4197172130c26d496a367bd6609d88'
BASE_SWIFT_AUCTION_VERIFIER = '\x2cba4739a9703ba57d5f50476d51c3a9bcc86de8'
BASE_WORMHOLE_CORE          = '\xbebdb6c8ddc678ffa9f8748f85c815c556dd8ac6'
BASE_SWIFT_GUARDIAN_EOA     = '\xb4cdc16e6afcca48b6fade7302b6590c664dca5a'
-- Arbitrum One (42161)
ARB_SWIFT_SOURCE            = '\x40ffe85a28dc9993541449464d7529a922142960'
ARB_SWIFT_DEST              = '\xd78d199f8c402e7b5cc2abe278df0412400a3bae'
ARB_SWIFT_V1                = '\xc38e4e6a15593f908255214653d3d947ca1c2338'
ARB_SWIFT_FEE_MANAGER       = '\x54914a963c4197172130c26d496a367bd6609d88'
ARB_SWIFT_AUCTION_VERIFIER  = '\x2cba4739a9703ba57d5f50476d51c3a9bcc86de8'
ARB_WORMHOLE_CORE           = '\xa5f208e072434bc67592e4c49c1b991ba79bca46'
ARB_SWIFT_GUARDIAN_EOA      = '\xb4cdc16e6afcca48b6fade7302b6590c664dca5a'
-- Optimism (10)
OP_SWIFT_SOURCE             = '\x40ffe85a28dc9993541449464d7529a922142960'
OP_SWIFT_DEST               = '\xd78d199f8c402e7b5cc2abe278df0412400a3bae'
OP_SWIFT_V1                 = '\xc38e4e6a15593f908255214653d3d947ca1c2338'
OP_SWIFT_FEE_MANAGER        = '\x54914a963c4197172130c26d496a367bd6609d88'
OP_SWIFT_AUCTION_VERIFIER   = '\x2cba4739a9703ba57d5f50476d51c3a9bcc86de8'
OP_WORMHOLE_CORE            = '\xee91c335eab126df5fdb3797ea9d6ad93aec9722'
OP_SWIFT_GUARDIAN_EOA       = '\xb4cdc16e6afcca48b6fade7302b6590c664dca5a'
-- Polygon PoS (137)
POLY_SWIFT_SOURCE           = '\x40ffe85a28dc9993541449464d7529a922142960'
POLY_SWIFT_DEST             = '\xd78d199f8c402e7b5cc2abe278df0412400a3bae'
POLY_SWIFT_V1               = '\xc38e4e6a15593f908255214653d3d947ca1c2338'
POLY_SWIFT_FEE_MANAGER      = '\x54914a963c4197172130c26d496a367bd6609d88'
POLY_SWIFT_AUCTION_VERIFIER = '\x2cba4739a9703ba57d5f50476d51c3a9bcc86de8'
POLY_WORMHOLE_CORE          = '\x7a4b5a56256163f07b2c80a7ca55abe66c4ec4d7'
POLY_SWIFT_GUARDIAN_EOA     = '\xb4cdc16e6afcca48b6fade7302b6590c664dca5a'
-- BNB Smart Chain (56)
BNB_SWIFT_SOURCE            = '\x40ffe85a28dc9993541449464d7529a922142960'
BNB_SWIFT_DEST              = '\xd78d199f8c402e7b5cc2abe278df0412400a3bae'
BNB_SWIFT_V1                = '\xc38e4e6a15593f908255214653d3d947ca1c2338'
BNB_SWIFT_FEE_MANAGER       = '\x54914a963c4197172130c26d496a367bd6609d88'
BNB_SWIFT_AUCTION_VERIFIER  = '\x2cba4739a9703ba57d5f50476d51c3a9bcc86de8'
BNB_WORMHOLE_CORE           = '\x98f3c9e6e3face36baad05fe09d375ef1464288b'
BNB_SWIFT_GUARDIAN_EOA      = '\xb4cdc16e6afcca48b6fade7302b6590c664dca5a'
-- Avalanche C-Chain (43114)
AVAX_SWIFT_SOURCE           = '\x40ffe85a28dc9993541449464d7529a922142960'
AVAX_SWIFT_DEST             = '\xd78d199f8c402e7b5cc2abe278df0412400a3bae'
AVAX_SWIFT_V1               = '\xc38e4e6a15593f908255214653d3d947ca1c2338'
AVAX_SWIFT_FEE_MANAGER      = '\x54914a963c4197172130c26d496a367bd6609d88'
AVAX_SWIFT_AUCTION_VERIFIER = '\x2cba4739a9703ba57d5f50476d51c3a9bcc86de8'
AVAX_WORMHOLE_CORE          = '\x54a8e5f9c4cba08f9943965859f6c34eaf03e26c'
AVAX_SWIFT_GUARDIAN_EOA     = '\xb4cdc16e6afcca48b6fade7302b6590c664dca5a'
-- Robinhood Chain (4663): no Swift contract (eth_getCode = 0x at all three addresses)
```

---

## 14. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified ABIs of `SwiftSource` and `SwiftDest` (Blockscout, compiler 0.8.28, verified 2026-03) and `MayanSwift` (0.8.4, verified 2024-10). The five Swift topic0 values were matched against decoded live logs; the selectors of the sampled transactions matched (`unlockCompressedBatch` `0x2d67b5ea`, `refundOrder` `0xac432e63`, `cancelOrder` `0x843bb559`).
- **Addresses:** from docs.mayan.finance "Swift" (source and destination tables, v1 table) and the swap SDK; every address was existence-checked with `eth_getCode` on all eight chains, and the EIP-1967 slots were read with `eth_getStorageAt`. `guardian()`, `feeManager()`, `wormhole()`, `auctionVerifier()` and `emitters(uint16)` were read with `eth_call`.
- **Samples read in full (Ethereum):** `0x2d727bbaf5837eb6e3f3bbba9ec6a9dc9e6ebb5a3dd7528f9d27746848ecb371` (Forwarder `swapAndForwardERC20` → USDC into SwiftSource → `OrderCreated`), `0xf482ba099d431df401a070a24a683f9a286b10a066088e4b4f10b94511aad359` (driver fill: driver contract → SwiftDest → user, `LogMessagePublished` sequence 250,572 = `OrderFulfilled.sequence`), `0xc95a494230d8093f497e04a8e3c5025e1dc474ef66e443d88bd8cd453bc380f1` (`unlockCompressedBatch`: WETH and USDC from SwiftSource to the driver, 8 `OrderUnlocked`), `0xe7546a7780a18bbaef87ac7f79fa5c01d49aa6ed8d73166ca9fc41ccb0b59cbe` (`refundOrder`: WETH unwrapped, ETH to the trader), `0x15e39f08dd44aec08ae2b80e41afcf8ced166774befdc2320b822d3d1de63234` (`cancelOrder`).
- **Activity:** pinned 12-hour window 2026-09-28 00:00–12:00 UTC, `eth_getLogs` per emitter (counts in §3–§9 and §10). Robinhood Chain: 0 logs of any Swift topic0 from any emitter. A 0 is a measurement of this window only.

Authoritative sources (opened for this document):
- Docs — [Swift](https://docs.mayan.finance/architecture/swift) (source `mayan-finance/docs`, `architecture/swift.mdx`) · [Chains & Contracts](https://docs.mayan.finance/resources/chains-contracts)
- Repositories — [mayan-finance/swap-sdk](https://github.com/mayan-finance/swap-sdk) (`src/evm/MayanSwiftArtifact.ts`, `src/evm/MayanSwiftV2Artifact.ts`, `src/evm/evmSwift.ts`) · [mayan-finance/example-tx-parser](https://github.com/mayan-finance/example-tx-parser) (`abis/swift.ts`)
- Verified sources — `https://eth.blockscout.com/api/v2/smart-contracts/0x40fFE85A28DC9993541449464d7529a922142960` (SwiftSource) · `https://eth.blockscout.com/api/v2/smart-contracts/0xD78D199f8C402e7B5Cc2abE278dF0412400a3BAe` (SwiftDest) · `https://eth.blockscout.com/api/v2/smart-contracts/0xC38e4e6A15593f908255214653d3D947CA1c2338` (MayanSwift)

