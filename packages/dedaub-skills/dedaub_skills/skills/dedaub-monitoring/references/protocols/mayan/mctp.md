# Mayan MCTP and Fast MCTP — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + Avalanche; NOT BNB, NOT Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the verified sources on Blockscout (`MayanCircle`, `FastMCTP`), the `mayan-finance/swap-sdk` ABIs and docs.mayan.finance (`architecture/mctp`). Topic0 and selector values were recomputed as `keccak256(signature)` from the verified ABIs and matched against live logs and transaction selectors. Addresses were existence-checked with `eth_getCode`.
**Scope:** the two Mayan routes that move USDC over Circle CCTP. **MCTP** (contract `MayanCircle`) uses CCTP v1 plus a Wormhole message for the order data. **Fast MCTP** (contract `FastMCTP`) uses CCTP v2 and puts the order data in the CCTP hook data (no Wormhole message). Both have the same address on each of their six chains. BNB Chain and Robinhood Chain have neither contract (`eth_getCode` = `0x`). Topics and selectors are chain-agnostic; addresses are network-specific.

Both routes follow the same pattern. On the source chain the Mayan contract pulls the user's USDC and burns it through CCTP (`DepositForBurn` with `depositor` = the Mayan contract). There is **no Mayan event on the source chain**. On the destination chain the Circle attestation mints USDC to the Mayan contract. A plain bridge (`redeemWithFee`, `redeem`) forwards the USDC to the recipient and emits **no Mayan event**. A swap order is filled by a driver (`fulfillOrder`: `OrderFulfilled`) or, after the deadline, delivered as USDC (`refund`: `OrderRefunded`). Both Mayan events sit on the destination chain.

The link key is the CCTP pair (source domain, nonce). MCTP (CCTP v1): the `uint64` nonce is on chain on both sides — `DepositForBurn.nonce` (topic1) on the source, `MessageReceived.nonce` (topic2) and the Mayan event on the destination. Fast MCTP (CCTP v2): the `bytes32` nonce is on chain only on the destination (`MessageReceived.nonce`, the Mayan event); the source `MessageSent` carries a zero nonce (§11), so the source side needs Circle's API.

---

## 0. Contract families & versions

| Contract | Address (same on every listed chain) | Chains | Role | Upgradeable? |
|----------|--------------------------------------|--------|------|--------------|
| **MayanCircle** (MCTP) | `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` | ETH, Base, Arb, OP, Poly, Avax | CCTP v1 bridge and swap orders. Source: `bridgeWithFee`, `bridgeWithLockedFee`, `createOrder`. Destination: `redeemWithFee`, `redeemWithLockedFee`, `fulfillOrder`, `refund`. Fee release: `unlockFee`, `unlockFeeRefined`. | No (plain contract; guardian-controlled settings) |
| **FastMCTP** (Fast MCTP) | `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` | ETH, Base, Arb, OP, Poly, Avax | CCTP v2 bridge and swap orders. Source: `bridge`, `createOrder`. Destination: `redeem`, `fulfillOrder`, `refund`. | No |
| CCTP v1 TokenMessenger | per chain (§3–§8) | 6 | `cctpTokenMessenger()` of MayanCircle. Emits `DepositForBurn` (source) and `MintAndWithdraw` (destination). | Circle (see the CCTP reference) |
| CCTP v2 TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | 6 | `cctpTokenMessengerV2()` of FastMCTP (same address on every chain). | Circle proxy |
| MCTP fee manager | `0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523` | 6 (the same address on every chain) | `feeManager()` of MayanCircle. |  — |
| Fast MCTP fee manager | `0x54914a963c4197172130c26d496a367bd6609d88` | 6 (the same address on every chain) | `feeManager()` of FastMCTP; the same contract as the Swift v2 fee manager. | — |

The docs table of MCTP lists BSC (Wormhole chain 4), but `eth_getCode` at `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` on BNB Chain returns `0x`, and `getDomain(4)` on the Ethereum MayanCircle reverts (no CCTP v1 domain for BNB). Treat MCTP as absent on BNB.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 MayanCircle (MCTP) — destination chain only

No parameter is indexed. The event names are the same as in Fast MCTP and Swift, but the types differ, so the topic0 values differ.

| topic0 | Event |
|--------|-------|
| `0xcc5626df3b699006387b64eca775dbdfecd5ae542e2d6ab22923082e1320dfcb` | `OrderFulfilled(uint32 sourceDomain, uint64 sourceNonce, uint256 amount)` — **payout** of a swap order. `(sourceDomain, sourceNonce)` = the CCTP v1 key of the source burn; `amount` = the output token amount the driver's swap produced (referrer and protocol fees are then taken from it). |
| `0x4f7c61703b83b54f1af0ca9b67d73dc13cc2e91262faf81b0a4927cbce924239` | `OrderRefunded(uint32 sourceDomain, uint64 sourceNonce, uint256 amount)` — **payout in USDC on the destination** after the deadline (no driver filled). `amount` = the minted USDC; the recipient gets `amount − redeemFee`. It is not a return to the source chain. |

### 1.2 FastMCTP (Fast MCTP) — destination chain only

| topic0 | Event |
|--------|-------|
| `0x99e766e06bd9dc43c056e2b2fc007c5b9e73c190b2daeb448fa24530d97c18e6` | `OrderFulfilled(uint32 sourceDomain, bytes32 sourceNonce, uint256 amount)` — **payout** of a swap order; `sourceNonce` = the CCTP v2 nonce; `amount` = the output token amount paid to `destAddr`. |
| `0xb4d4578bf8a1f3c5aa81fae0b333ea7abc62f085e359d86631f63809319bd025` | `OrderRefunded(uint32 sourceDomain, bytes32 sourceNonce, uint256 amount)` — **payout in USDC on the destination** (after the deadline, or at once when the order's output token is USDC). The recipient gets `amount − refundFee`. |

### 1.3 CCTP and Wormhole events of the same transactions (emitters are Circle and Wormhole contracts)

| topic0 | Event |
|--------|-------|
| `0x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0` | `DepositForBurn(uint64 indexed nonce, address indexed burnToken, uint256 amount, address indexed depositor, bytes32 mintRecipient, uint32 destinationDomain, bytes32 destinationTokenMessenger, bytes32 destinationCaller)` — **MCTP source leg** (CCTP v1 TokenMessenger); filter `depositor` (topic3) = MayanCircle. |
| `0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5` | `DepositForBurn(address indexed burnToken, uint256 amount, address indexed depositor, bytes32 mintRecipient, uint32 destinationDomain, bytes32 destinationTokenMessenger, bytes32 destinationCaller, uint256 maxFee, uint32 indexed minFinalityThreshold, bytes hookData)` — **Fast MCTP source leg** (TokenMessengerV2); filter `depositor` (topic2) = FastMCTP. `hookData` = the Mayan bridge or order payload. |
| `0x58200b4c34ae05ee816d710053fff3fb75af4395915d3d2a771b24aa10e3cc5d` | `MessageReceived(address indexed caller, uint32 sourceDomain, uint64 indexed nonce, bytes32 sender, bytes messageBody)` — CCTP v1 destination (MessageTransmitter). |
| `0xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c` | `MessageReceived(address indexed caller, uint32 sourceDomain, bytes32 indexed nonce, bytes32 sender, uint32 indexed finalityThresholdExecuted, bytes messageBody)` — CCTP v2 destination (MessageTransmitterV2). |
| `0x1b2a7ff080b8cb6ff436ce0372e399692bbfb6d4ae5766fd8d58a7b8cc6142e6` | `MintAndWithdraw(address indexed mintRecipient, uint256 amount, address indexed mintToken)` — CCTP v1 mint to MayanCircle. |
| `0x50c55e915134d457debfa58eb6f4342956f8b0616d51a89a3659360178e1ab63` | `MintAndWithdraw(address indexed mintRecipient, uint256 amount, address indexed mintToken, uint256 feeCollected)` — CCTP v2 mint to FastMCTP. |
| `0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036` | `MessageSent(bytes message)` — CCTP source message (v1 and v2 share this topic0). |
| `0x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2` | `LogMessagePublished(address indexed sender, uint64 sequence, uint32 nonce, bytes payload, uint8 consistencyLevel)` — Wormhole Core; `sender` = MayanCircle for `bridgeWithFee`, `createOrder`, `redeemWithLockedFee` and `refineFee` (the payload is a hash of the Mayan parameters). FastMCTP publishes no Wormhole message. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — USDC and output tokens (value rows). |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 MayanCircle (MCTP)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2072197f` | `bridgeWithFee(address tokenIn, uint256 amountIn, uint64 redeemFee, uint64 gasDrop, bytes32 destAddr, uint32 destDomain, uint8 payloadType, bytes customPayload)` | payable (Wormhole fee). **Source, plain bridge.** Pulls USDC, CCTP v1 burn, Wormhole message. |
| `0x9be95bb4` | `bridgeWithLockedFee(address tokenIn, uint256 amountIn, uint64 gasDrop, uint256 redeemFee, uint32 destDomain, bytes32 destAddr)` | **Source, plain bridge.** The relayer fee stays locked in MayanCircle (`feeStorage[cctpNonce]`) until `unlockFee`. |
| `0x1c59b7fc` | `createOrder((address tokenIn, uint256 amountIn, uint64 gasDrop, bytes32 destAddr, uint16 destChain, bytes32 tokenOut, uint64 minAmountOut, uint64 deadline, uint64 redeemFee, bytes32 referrerAddr, uint8 referrerBps) params)` | payable. **Source, swap order.** CCTP burn + Wormhole message with the order hash. `destChain` is a Wormhole chain id. |
| `0xe2de2a03` | `redeemWithFee(bytes cctpMsg, bytes cctpSigs, bytes encodedVm, (uint8 payloadType, bytes32 destAddr, uint64 gasDrop, uint64 redeemFee, uint64 burnAmount, bytes32 burnToken, bytes32 customPayload) bridgeParams)` | payable (gas drop). **Destination, plain bridge**: USDC to `destAddr` minus `redeemFee`. **No Mayan event.** |
| `0x853d2c83` | `redeemWithLockedFee(bytes cctpMsg, bytes cctpSigs, bytes32 unlockerAddr)` | payable. Destination of `bridgeWithLockedFee`; publishes the fee-unlock message. No Mayan event. |
| `0x79292167` | `refineFee(uint32 cctpNonce, uint32 cctpDomain, bytes32 destAddr, bytes32 unlockerAddr)` | payable. Adjusts a locked fee. |
| `0x40e66b16` | `unlockFee(bytes encodedVm, (uint8 action, uint8 payloadType, uint64 cctpNonce, uint32 cctpDomain, bytes32 unlockerAddr, uint64 gasDrop) unlockMsg)` | Source chain: releases the locked fee to the relayer. |
| `0x9b9490d4` | `unlockFeeRefined(bytes encodedVm1, bytes encodedVm2, (uint8 action, uint8 payloadType, uint64 cctpNonce, uint32 cctpDomain, bytes32 unlockerAddr, uint64 gasDrop) unlockMsg, (uint8 action, uint8 payloadType, uint64 cctpNonce, uint32 cctpDomain, bytes32 unlockerAddr, uint64 gasDrop, bytes32 destAddr) refinedMsg)` | Source chain: releases a refined fee. |
| `0xa0883526` | `fulfillOrder(bytes cctpMsg, bytes cctpSigs, bytes encodedVm, (bytes32 destAddr, uint16 destChainId, bytes32 tokenOut, uint64 promisedAmount, uint64 gasDrop, uint64 redeemFee, uint64 deadline, bytes32 referrerAddr, uint8 referrerBps, uint8 protocolBps, bytes32 driver) params, address swapProtocol, bytes swapData)` | payable. **Destination, swap fill** by the driver (auction VAA from Solana). Emits `OrderFulfilled`. |
| `0x3f46e914` | `refund(bytes encodedVm, bytes cctpMsg, bytes cctpSigs, (address tokenIn, uint256 amountIn, uint64 gasDrop, bytes32 destAddr, uint16 destChain, bytes32 tokenOut, uint64 minAmountOut, uint64 deadline, uint64 redeemFee, bytes32 referrerAddr, uint8 referrerBps) orderParams, (bytes32 trader, uint16 sourceChainId, uint8 protocolBps) extraParams)` | payable. **Destination, after the deadline**: USDC to `destAddr`. Emits `OrderRefunded`. |
| `0xf8a67a62` | `rescueToken(address token, uint256 amount, address to)` | **Guardian only; moves any token out. No event.** |
| `0xb25ea8fb` | `rescueEth(uint256 amount, address to)` | Guardian only. No event. |
| `0xbedb86fb` | `setPause(bool _pause)` | Guardian only. No event. |
| `0x472d35b9` | `setFeeManager(address _feeManager)` | Guardian only. No event. |
| `0x93166d0c` | `setDomains(uint16[] chainIds, uint32[] domains)` | Guardian only. Wormhole chain id → CCTP domain map. |
| `0x375ef75e` | `setDomainCallers(uint32 domain, bytes32 caller)` | Guardian only. |
| `0x3441b139` | `setEmitter(uint16 chainId, bytes32 emitter)` | Guardian only. |
| `0xe21e2d88` | `setMintRecipient(uint32 destDomain, address tokenIn, bytes32 mintRecipient)` | Guardian only. |
| `0x538ee295` | `setConsistencyLevel(uint8 _consistencyLevel)` | Guardian only. |
| `0x2fcb4f04` | `changeGuardian(address newGuardian)` | Guardian only. |
| `0x459656ee` | `claimGuardian()` | Next guardian. |

Views: `getDomain(uint16)` `0x58de7fb4` (Wormhole chain id → CCTP domain; reverts when unset), `localDomain()` `0x8d3638f4`, `cctpTokenMessenger()` `0x9748cf7c`, `guardian()` `0x452a9320`, `paused()` `0x5c975abb`, `feeManager()` `0xd0fb0203`.

### 2.2 FastMCTP (Fast MCTP)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf58b6de8` | `bridge(address tokenIn, uint256 amountIn, uint64 redeemFee, uint256 circleMaxFee, uint64 gasDrop, bytes32 destAddr, uint32 destDomain, bytes32 referrerAddress, uint8 referrerBps, uint8 payloadType, uint32 minFinalityThreshold, bytes customPayload)` | **Source, plain bridge** (payload type 1 or 2). CCTP v2 `depositForBurnWithHook`. |
| `0x2337e236` | `createOrder(address tokenIn, uint256 amountIn, uint256 circleMaxFee, uint32 destDomain, uint32 minFinalityThreshold, (uint8 payloadType, bytes32 destAddr, bytes32 tokenOut, uint64 amountOutMin, uint64 gasDrop, uint64 redeemFee, uint64 refundFee, uint64 deadline, bytes32 referrerAddr, uint8 referrerBps) orderPayload)` | **Source, swap order** (payload type 3). |
| `0xe5c1bf6e` | `redeem(bytes cctpMsg, bytes cctpSigs)` | payable. **Destination, plain bridge.** USDC to the recipient (minus redeem, referrer and protocol fees). **No Mayan event.** |
| `0xdccedc74` | `fulfillOrder(bytes cctpMsg, bytes cctpSigs, address swapProtocol, bytes swapData)` | payable. **Destination, swap fill** (whitelisted `msg.sender` and swap protocol). Emits `OrderFulfilled`. |
| `0xdcee57ff` | `refund(bytes cctpMsg, bytes cctpSigs)` | payable. **Destination, USDC delivery** after the deadline. Emits `OrderRefunded`. |
| `0x75f50997` | `rescueRedeem(bytes cctpMsg, bytes cctpSigs)` | **Guardian only**: receives a CCTP message into the contract without the Mayan payout. |
| `0xf8a67a62` | `rescueToken(address token, uint256 amount, address to)` | **Guardian only; no event.** |
| `0xb25ea8fb` | `rescueEth(uint256 amount, address to)` | Guardian only. |
| `0xbedb86fb` | `setPause(bool _pause)` | Guardian only. No event. |
| `0x472d35b9` | `setFeeManager(address _feeManager)` | Guardian only. |
| `0x375ef75e` | `setDomainCallers(uint32 domain, bytes32 caller)` | Guardian only. |
| `0xe21e2d88` | `setMintRecipient(uint32 destDomain, address tokenIn, bytes32 mintRecipient)` | Guardian only. |
| `0x4fd416d1` | `setWhitelistedMsgSenders(address sender, bool isWhitelisted)` | Guardian only (who may call `fulfillOrder`). |
| `0xcfa1167d` | `setWhitelistedSwapProtocols(address protocol, bool isWhitelisted)` | Guardian only. |
| `0x2fcb4f04` | `changeGuardian(address newGuardian)` | Guardian only. |
| `0x459656ee` | `claimGuardian()` | Next guardian. |

---

## 3. Addresses — Ethereum (chain ID 1, Wormhole chain ID 2, CCTP domain 0)

Verified with `eth_getCode` on 2026-09-29. Same literal Mayan addresses as on the other MCTP chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanCircle** (MCTP) | `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` | 24,542 B. `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA); `feeManager()` = `0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523`. |
| **FastMCTP** | `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` | 14,581 B (one code hash on all six chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| CCTP v1 TokenMessenger | `0xBd3fa81B58Ba92a82136038B25aDec7066af3155` | `cctpTokenMessenger()` of MayanCircle; emitter of the MCTP `DepositForBurn`. |
| CCTP v2 TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | `cctpTokenMessengerV2()` of FastMCTP. |
| Wormhole Core | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` | `wormhole()` of MayanCircle. |

Pinned window 2026-09-28 00:00–12:00 UTC: MCTP — 25 CCTP v1 `DepositForBurn` with `depositor` = MayanCircle, 10 `OrderFulfilled`, 6 `OrderRefunded`; Fast MCTP — 149 CCTP v2 `DepositForBurn` with `depositor` = FastMCTP, 9 `OrderFulfilled`, 4 `OrderRefunded`.

## 4. Addresses — Base (chain ID 8453, Wormhole chain ID 30, CCTP domain 6)

Verified with `eth_getCode` on 2026-09-29. Same literal Mayan addresses as on the other MCTP chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanCircle** (MCTP) | `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` | 24,542 B. `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA); `feeManager()` = `0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523`. |
| **FastMCTP** | `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` | 14,581 B (one code hash on all six chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| CCTP v1 TokenMessenger | `0x1682Ae6375C4E4A97e4B583BC394c861A46D8962` | `cctpTokenMessenger()` of MayanCircle; emitter of the MCTP `DepositForBurn`. |
| CCTP v2 TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | `cctpTokenMessengerV2()` of FastMCTP. |
| Wormhole Core | `0xbebdb6C8ddC678FfA9f8748f85C815C556Dd8ac6` | `wormhole()` of MayanCircle. |

Pinned window 2026-09-28 00:00–12:00 UTC: MCTP — 22 CCTP v1 `DepositForBurn` with `depositor` = MayanCircle, 4 `OrderFulfilled`, 2 `OrderRefunded`; Fast MCTP — 85 CCTP v2 `DepositForBurn` with `depositor` = FastMCTP, 145 `OrderFulfilled`, 63 `OrderRefunded`.

## 5. Addresses — Arbitrum One (chain ID 42161, Wormhole chain ID 23, CCTP domain 3)

Verified with `eth_getCode` on 2026-09-29. Same literal Mayan addresses as on the other MCTP chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanCircle** (MCTP) | `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` | 24,542 B. `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA); `feeManager()` = `0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523`. |
| **FastMCTP** | `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` | 14,581 B (one code hash on all six chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| CCTP v1 TokenMessenger | `0x19330d10D9Cc8751218eaf51E8885D058642E08A` | `cctpTokenMessenger()` of MayanCircle; emitter of the MCTP `DepositForBurn`. |
| CCTP v2 TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | `cctpTokenMessengerV2()` of FastMCTP. |
| Wormhole Core | `0xa5f208e072434bC67592E4C49C1B991BA79BCA46` | `wormhole()` of MayanCircle. |

Pinned window 2026-09-28 00:00–12:00 UTC: MCTP — 10 CCTP v1 `DepositForBurn` with `depositor` = MayanCircle, 1 `OrderFulfilled`, 0 `OrderRefunded`; Fast MCTP — 58 CCTP v2 `DepositForBurn` with `depositor` = FastMCTP, 5 `OrderFulfilled`, 1 `OrderRefunded`.

## 6. Addresses — Optimism (chain ID 10, Wormhole chain ID 24, CCTP domain 2)

Verified with `eth_getCode` on 2026-09-29. Same literal Mayan addresses as on the other MCTP chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanCircle** (MCTP) | `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` | 24,542 B. `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA); `feeManager()` = `0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523`. |
| **FastMCTP** | `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` | 14,581 B (one code hash on all six chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| CCTP v1 TokenMessenger | `0x2B4069517957735bE00ceE0fadAE88a26365528f` | `cctpTokenMessenger()` of MayanCircle; emitter of the MCTP `DepositForBurn`. |
| CCTP v2 TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | `cctpTokenMessengerV2()` of FastMCTP. |
| Wormhole Core | `0xEe91C335eab126dF5fDB3797EA9d6aD93aeC9722` | `wormhole()` of MayanCircle. |

Pinned window 2026-09-28 00:00–12:00 UTC: MCTP — 1 CCTP v1 `DepositForBurn` with `depositor` = MayanCircle, 1 `OrderFulfilled`, 0 `OrderRefunded`; Fast MCTP — 9 CCTP v2 `DepositForBurn` with `depositor` = FastMCTP, 19 `OrderFulfilled`, 0 `OrderRefunded`.

## 7. Addresses — Polygon PoS (chain ID 137, Wormhole chain ID 5, CCTP domain 7)

Verified with `eth_getCode` on 2026-09-29. Same literal Mayan addresses as on the other MCTP chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanCircle** (MCTP) | `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` | 24,542 B. `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA); `feeManager()` = `0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523`. |
| **FastMCTP** | `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` | 14,581 B (one code hash on all six chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| CCTP v1 TokenMessenger | `0x9daF8c91AEFAE50b9c0E69629D3F6Ca40cA3B3FE` | `cctpTokenMessenger()` of MayanCircle; emitter of the MCTP `DepositForBurn`. |
| CCTP v2 TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | `cctpTokenMessengerV2()` of FastMCTP. |
| Wormhole Core | `0x7A4B5a56256163F07b2C80A7cA55aBE66c4ec4d7` | `wormhole()` of MayanCircle. |

Pinned window 2026-09-28 00:00–12:00 UTC: MCTP — 6 CCTP v1 `DepositForBurn` with `depositor` = MayanCircle, 1 `OrderFulfilled`, 0 `OrderRefunded`; Fast MCTP — 44 CCTP v2 `DepositForBurn` with `depositor` = FastMCTP, 32 `OrderFulfilled`, 5 `OrderRefunded`.

## 8. Addresses — Avalanche C-Chain (chain ID 43114, Wormhole chain ID 6, CCTP domain 1)

Verified with `eth_getCode` on 2026-09-29. Same literal Mayan addresses as on the other MCTP chains.

| Role | Address | Code / note |
|------|---------|-------------|
| **MayanCircle** (MCTP) | `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` | 24,542 B. `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` (EOA); `feeManager()` = `0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523`. |
| **FastMCTP** | `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` | 14,581 B (one code hash on all six chains). `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8`; `feeManager()` = `0x54914a963c4197172130c26d496a367bd6609d88`. |
| CCTP v1 TokenMessenger | `0x6B25532e1060CE10cc3B0A99e5683b91BFDe6982` | `cctpTokenMessenger()` of MayanCircle; emitter of the MCTP `DepositForBurn`. |
| CCTP v2 TokenMessengerV2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | `cctpTokenMessengerV2()` of FastMCTP. |
| Wormhole Core | `0x54a8e5f9c4CbA08F9943965859F6c34eAF03E26c` | `wormhole()` of MayanCircle. |

Pinned window 2026-09-28 00:00–12:00 UTC: MCTP — 11 CCTP v1 `DepositForBurn` with `depositor` = MayanCircle, 0 `OrderFulfilled`, 0 `OrderRefunded`; Fast MCTP — 32 CCTP v2 `DepositForBurn` with `depositor` = FastMCTP, 20 `OrderFulfilled`, 1 `OrderRefunded`.

---

## 9. Cross-chain summary

| Chain | EVM ID | Wormhole ID | CCTP domain | MayanCircle `0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` | FastMCTP `0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` |
|-------|-------:|------------:|------------:|:--:|:--:|
| Ethereum | 1 | 2 | 0 | ✅ | ✅ |
| Base | 8453 | 30 | 6 | ✅ | ✅ |
| Arbitrum One | 42161 | 23 | 3 | ✅ | ✅ |
| Optimism | 10 | 24 | 2 | ✅ | ✅ |
| Polygon PoS | 137 | 5 | 7 | ✅ | ✅ |
| **BNB Smart Chain** | 56 | 4 | — | ❌ `0x` (docs list BSC) | ❌ `0x` |
| Avalanche C-Chain | 43114 | 6 | 1 | ✅ | ✅ |
| **Robinhood Chain** | 4663 | — | — | ❌ `0x` | ❌ `0x` |

Counterparties outside the eight chains: Solana (CCTP domain 5; MCTP program `dkpZqrxHFrhziEMQ931GLtfy11nFkCsfMftH9u6QwBU`, Fast MCTP program `Gx9rivpS3YR8pBFwMuP6omYqVxunpLvLkNn7ubNyuZZ5`), Sui (domain 8; MCTP only), Unichain, and for Fast MCTP also Linea, HyperEVM and Monad (docs). The sample Fast MCTP burn on Ethereum went to CCTP domain 15.

---

## 10. Proxies (old & new)

| Contract | Pattern | Detection | Admin authority |
|----------|---------|-----------|-----------------|
| **MayanCircle**, **FastMCTP** | **Not proxies.** | EIP-1967 implementation and beacon slots empty on all six chains; full runtime (24,542 / 14,581 B). | `guardian()` = `0x933e3922e04d47a466e60a20e486b372b64f1ea8` on every chain read (an EOA on all seven EVM chains). Two-step change. `rescueToken`, `rescueEth` and (FastMCTP) `rescueRedeem` can move any balance; no admin function emits an event. |
| MCTP fee manager `0x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523` | Not a proxy (3,690 B, slots empty on Ethereum). | — | — |
| Fast MCTP fee manager (the Swift v2 fee manager) | **EIP-1967 proxy** (183 B; implementation `0x25858b08b6d45be7705c5e85528bd962f73a3c3f` on Ethereum). | Admin slot empty; the upgrade check sits in the implementation (not verified). | Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. |
| CCTP TokenMessenger / TokenMessengerV2 / MessageTransmitter(V2) | Circle's contracts (v1 direct, v2 EIP-1967). | See the CCTP reference. | Circle. |

---

## 11. Detection invariants & gotchas

1. **The source chain has no Mayan event.** Detect the MCTP source leg as a CCTP v1 `DepositForBurn` (`0x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0`) with topic3 (`depositor`) = MayanCircle, and the Fast MCTP source leg as a CCTP v2 `DepositForBurn` (`0x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5`) with topic2 (`depositor`) = FastMCTP. The value path is user (or Forwarder) → Mayan contract → Circle TokenMinter → burn to `0x0`.
2. **MCTP link key: `(sourceDomain, nonce)`, exact on both sides.** Source: `DepositForBurn.nonce` (topic1, `uint64`). Destination: `MessageReceived.nonce` (topic2) and, for swap orders, `OrderFulfilled` / `OrderRefunded` `(sourceDomain, sourceNonce)`. Sample: MCTP `OrderFulfilled` on Ethereum with `(sourceDomain 5, sourceNonce 747,492)` = a Solana-origin order.
3. **Fast MCTP link key: `(sourceDomain, bytes32 nonce)`, on chain only on the destination.** In CCTP v2 the source `MessageSent` carries a zero nonce: the sample Ethereum burn `0x4c52db35b050ea69d3d127fc45bb547a9570d60b463dd857c562f3bd458796ac` (42,471.19 USDC to domain 15) had `nonce` = `0x0000000000000000000000000000000000000000000000000000000000000000` in its message header. Circle's attestation service assigns the nonce. Join the two sides through Circle's API, or through the message fields (source domain, sender, recipient, amount, hook data).
4. **Plain bridges emit no Mayan event on the destination either.** `redeemWithFee` / `redeemWithLockedFee` (MCTP) and `redeem` (Fast MCTP) only produce the CCTP `MessageReceived` + `MintAndWithdraw` and the USDC `Transfer` from the Mayan contract to the recipient. The Mayan events cover swap orders only.
5. **`OrderRefunded` is a payout, not a return.** It fires on the **destination** chain when no driver filled the swap before the deadline (Fast MCTP also when the ordered output is USDC); the recipient receives USDC minus the refund or redeem fee. Nothing goes back to the source chain.
6. **Three `OrderFulfilled` / `OrderRefunded` signatures exist in Mayan.** MCTP `(uint32, uint64, uint256)`, Fast MCTP `(uint32, bytes32, uint256)` and Swift `(bytes32, …)` have different topic0 values; filter on the emitter as well.
7. **`amount` differs per event.** `OrderFulfilled.amount` is the output token amount after the driver's swap (MCTP takes referrer and protocol fees from it afterwards; Fast MCTP pays it in full). `OrderRefunded.amount` is the minted USDC before the relayer fee.
8. **Fills are permissioned.** MCTP `fulfillOrder` requires `msg.sender` = the driver named in the auction VAA (from Solana). FastMCTP `fulfillOrder` requires a whitelisted `msg.sender` and swap protocol. The driver and relayer addresses are ordinary accounts; in the Ethereum samples `0x04d9634df20aa66b23f114d37c45fa6c6ab76d56` submitted the fills.
9. **Locked relayer fees (MCTP).** `bridgeWithLockedFee` keeps the fee inside MayanCircle on the source chain until `unlockFee` / `unlockFeeRefined` pays it to the relayer, after a Wormhole message from the destination. These are `Transfer` rows out of MayanCircle on the **source** chain with no Mayan event.
10. **Admin changes emit no event.** Watch `rescueToken` `0xf8a67a62`, `rescueEth` `0xb25ea8fb`, `rescueRedeem` `0x75f50997`, `setPause` `0xbedb86fb`, `setMintRecipient` `0xe21e2d88`, `setDomainCallers` `0x375ef75e`, `setDomains` `0x93166d0c`, `setEmitter` `0x3441b139`, `setWhitelistedMsgSenders` `0x4fd416d1`, `setWhitelistedSwapProtocols` `0xcfa1167d`, `setFeeManager` `0x472d35b9`, `changeGuardian` `0x2fcb4f04`. A changed `mintRecipient` redirects future mints.
11. **BNB and Robinhood Chain have neither route.** The docs MCTP table lists BSC, but the address has no code there and `getDomain(4)` reverts on the Ethereum MayanCircle.

---

## 12. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_MCTP_ORDER_FULFILLED       = '\xcc5626df3b699006387b64eca775dbdfecd5ae542e2d6ab22923082e1320dfcb'
TOPIC_MCTP_ORDER_REFUNDED        = '\x4f7c61703b83b54f1af0ca9b67d73dc13cc2e91262faf81b0a4927cbce924239'
TOPIC_FAST_MCTP_ORDER_FULFILLED  = '\x99e766e06bd9dc43c056e2b2fc007c5b9e73c190b2daeb448fa24530d97c18e6'
TOPIC_FAST_MCTP_ORDER_REFUNDED   = '\xb4d4578bf8a1f3c5aa81fae0b333ea7abc62f085e359d86631f63809319bd025'
TOPIC_CCTP_V1_DEPOSIT_FOR_BURN   = '\x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0'
TOPIC_CCTP_V2_DEPOSIT_FOR_BURN   = '\x0c8c1cbdc5190613ebd485511d4e2812cfa45eecb79d845893331fedad5130a5'
TOPIC_CCTP_V1_MESSAGE_RECEIVED   = '\x58200b4c34ae05ee816d710053fff3fb75af4395915d3d2a771b24aa10e3cc5d'
TOPIC_CCTP_V2_MESSAGE_RECEIVED   = '\xff48c13eda96b1cceacc6b9edeedc9e9db9d6226afbc30146b720c19d3addb1c'
TOPIC_CCTP_V1_MINT_AND_WITHDRAW  = '\x1b2a7ff080b8cb6ff436ce0372e399692bbfb6d4ae5766fd8d58a7b8cc6142e6'
TOPIC_CCTP_V2_MINT_AND_WITHDRAW  = '\x50c55e915134d457debfa58eb6f4342956f8b0616d51a89a3659360178e1ab63'
TOPIC_CCTP_MESSAGE_SENT          = '\x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036'
TOPIC_WORMHOLE_LOG_MESSAGE_PUBLISHED = '\x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2'

-- ===== Selectors (chain-agnostic) =====
-- MayanCircle (MCTP)
SEL_MCTP_BRIDGE_WITH_FEE         = '\x2072197f'
SEL_MCTP_BRIDGE_WITH_LOCKED_FEE  = '\x9be95bb4'
SEL_MCTP_CREATE_ORDER            = '\x1c59b7fc'
SEL_MCTP_REDEEM_WITH_FEE         = '\xe2de2a03'
SEL_MCTP_REDEEM_WITH_LOCKED_FEE  = '\x853d2c83'
SEL_MCTP_FULFILL_ORDER           = '\xa0883526'
SEL_MCTP_REFUND                  = '\x3f46e914'
SEL_MCTP_UNLOCK_FEE              = '\x40e66b16'
SEL_MCTP_UNLOCK_FEE_REFINED      = '\x9b9490d4'
SEL_MCTP_SET_DOMAINS             = '\x93166d0c'
SEL_MCTP_SET_EMITTER             = '\x3441b139'
-- FastMCTP
SEL_FAST_MCTP_BRIDGE             = '\xf58b6de8'
SEL_FAST_MCTP_CREATE_ORDER       = '\x2337e236'
SEL_FAST_MCTP_REDEEM             = '\xe5c1bf6e'
SEL_FAST_MCTP_FULFILL_ORDER      = '\xdccedc74'
SEL_FAST_MCTP_REFUND             = '\xdcee57ff'
SEL_FAST_MCTP_RESCUE_REDEEM      = '\x75f50997'
SEL_FAST_MCTP_SET_WHITELISTED_MSG_SENDERS = '\x4fd416d1'
SEL_FAST_MCTP_SET_WHITELISTED_SWAP_PROTOCOLS = '\xcfa1167d'
-- shared admin
SEL_MAYAN_RESCUE_TOKEN           = '\xf8a67a62'
SEL_MAYAN_RESCUE_ETH             = '\xb25ea8fb'
SEL_MAYAN_SET_MINT_RECIPIENT     = '\xe21e2d88'
SEL_MAYAN_SET_DOMAIN_CALLERS     = '\x375ef75e'
SEL_MAYAN_SET_PAUSE              = '\xbedb86fb'
SEL_MAYAN_SET_FEE_MANAGER        = '\x472d35b9'
SEL_MAYAN_CHANGE_GUARDIAN        = '\x2fcb4f04'

-- ===== Addresses (network-specific; MayanCircle and FastMCTP have the same literal address on all six chains) =====
-- Ethereum (1)
ETH_MAYAN_CIRCLE             = '\x875d6d37ec55c8cf220b9e5080717549d8aa8eca'
ETH_FAST_MCTP                = '\xc1062b7c5dc8e4b1df9f200fe360cdc0ed6e7741'
ETH_CCTP_V1_TOKEN_MESSENGER  = '\xbd3fa81b58ba92a82136038b25adec7066af3155'
ETH_CCTP_V2_TOKEN_MESSENGER  = '\x28b5a0e9c621a5badaa536219b3a228c8168cf5d'
ETH_MCTP_FEE_MANAGER         = '\x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523'
ETH_FAST_MCTP_FEE_MANAGER    = '\x54914a963c4197172130c26d496a367bd6609d88'
ETH_MAYAN_GUARDIAN_EOA       = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- Base (8453)
BASE_MAYAN_CIRCLE            = '\x875d6d37ec55c8cf220b9e5080717549d8aa8eca'
BASE_FAST_MCTP               = '\xc1062b7c5dc8e4b1df9f200fe360cdc0ed6e7741'
BASE_CCTP_V1_TOKEN_MESSENGER = '\x1682ae6375c4e4a97e4b583bc394c861a46d8962'
BASE_CCTP_V2_TOKEN_MESSENGER = '\x28b5a0e9c621a5badaa536219b3a228c8168cf5d'
BASE_MCTP_FEE_MANAGER        = '\x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523'
BASE_FAST_MCTP_FEE_MANAGER   = '\x54914a963c4197172130c26d496a367bd6609d88'
BASE_MAYAN_GUARDIAN_EOA      = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- Arbitrum One (42161)
ARB_MAYAN_CIRCLE             = '\x875d6d37ec55c8cf220b9e5080717549d8aa8eca'
ARB_FAST_MCTP                = '\xc1062b7c5dc8e4b1df9f200fe360cdc0ed6e7741'
ARB_CCTP_V1_TOKEN_MESSENGER  = '\x19330d10d9cc8751218eaf51e8885d058642e08a'
ARB_CCTP_V2_TOKEN_MESSENGER  = '\x28b5a0e9c621a5badaa536219b3a228c8168cf5d'
ARB_MCTP_FEE_MANAGER         = '\x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523'
ARB_FAST_MCTP_FEE_MANAGER    = '\x54914a963c4197172130c26d496a367bd6609d88'
ARB_MAYAN_GUARDIAN_EOA       = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- Optimism (10)
OP_MAYAN_CIRCLE              = '\x875d6d37ec55c8cf220b9e5080717549d8aa8eca'
OP_FAST_MCTP                 = '\xc1062b7c5dc8e4b1df9f200fe360cdc0ed6e7741'
OP_CCTP_V1_TOKEN_MESSENGER   = '\x2b4069517957735be00cee0fadae88a26365528f'
OP_CCTP_V2_TOKEN_MESSENGER   = '\x28b5a0e9c621a5badaa536219b3a228c8168cf5d'
OP_MCTP_FEE_MANAGER          = '\x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523'
OP_FAST_MCTP_FEE_MANAGER     = '\x54914a963c4197172130c26d496a367bd6609d88'
OP_MAYAN_GUARDIAN_EOA        = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- Polygon PoS (137)
POLY_MAYAN_CIRCLE            = '\x875d6d37ec55c8cf220b9e5080717549d8aa8eca'
POLY_FAST_MCTP               = '\xc1062b7c5dc8e4b1df9f200fe360cdc0ed6e7741'
POLY_CCTP_V1_TOKEN_MESSENGER = '\x9daf8c91aefae50b9c0e69629d3f6ca40ca3b3fe'
POLY_CCTP_V2_TOKEN_MESSENGER = '\x28b5a0e9c621a5badaa536219b3a228c8168cf5d'
POLY_MCTP_FEE_MANAGER        = '\x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523'
POLY_FAST_MCTP_FEE_MANAGER   = '\x54914a963c4197172130c26d496a367bd6609d88'
POLY_MAYAN_GUARDIAN_EOA      = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- Avalanche C-Chain (43114)
AVAX_MAYAN_CIRCLE            = '\x875d6d37ec55c8cf220b9e5080717549d8aa8eca'
AVAX_FAST_MCTP               = '\xc1062b7c5dc8e4b1df9f200fe360cdc0ed6e7741'
AVAX_CCTP_V1_TOKEN_MESSENGER = '\x6b25532e1060ce10cc3b0a99e5683b91bfde6982'
AVAX_CCTP_V2_TOKEN_MESSENGER = '\x28b5a0e9c621a5badaa536219b3a228c8168cf5d'
AVAX_MCTP_FEE_MANAGER        = '\x6b4d38ed0a555d4516ae81c6c8d9b19f4365b523'
AVAX_FAST_MCTP_FEE_MANAGER   = '\x54914a963c4197172130c26d496a367bd6609d88'
AVAX_MAYAN_GUARDIAN_EOA      = '\x933e3922e04d47a466e60a20e486b372b64f1ea8'
-- BNB Smart Chain (56) and Robinhood Chain (4663): no MayanCircle, no FastMCTP (eth_getCode = 0x)
```

---

## 13. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified ABIs of `MayanCircle` (Blockscout, compiler 0.8.4) and `FastMCTP` (0.8.28). The four Mayan topic0 values were matched against decoded live logs; the sampled fills and refunds used `fulfillOrder` `0xa0883526` (MCTP) and `0xdccedc74` (Fast MCTP). The CCTP topic0 values are the ones in the CCTP v1 and v2 references and were seen in the same samples.
- **Addresses:** from docs.mayan.finance "MCTP / Fast MCTP"; every address was existence-checked with `eth_getCode` on all eight chains, and the EIP-1967 slots were read. `guardian()`, `feeManager()`, `cctpTokenMessenger()`, `cctpTokenMessengerV2()`, `localDomain()` and `getDomain(uint16)` were read with `eth_call`.
- **Samples read in full (Ethereum):** `0x45a3baf4d5e0ddc25c6fa2e4cc68fea46ad7ff36e78426f74dc85ad0a45878c8` (MCTP `fulfillOrder`: CCTP v1 mint to MayanCircle, swap, output to the recipient, `OrderFulfilled(5, 747492, …)`), `0x2c981f156fb8d18c894c4e94ccf6fd64319520168dc1ac432fd317455033ae7e` (MCTP `refund`: USDC to the recipient on the destination, `OrderRefunded(3, …)`), `0x66172371a37055809c97bad8c1be5402263e4dc0462004a7ff3efde202d9883b` (Fast MCTP `fulfillOrder` from domain 6), `0xb68a81a2a99f2968eecd50db052ffeee905acc5dfe3218a68e9f1446dd6f8c04` (Fast MCTP `refund`), `0x4c52db35b050ea69d3d127fc45bb547a9570d60b463dd857c562f3bd458796ac` (Fast MCTP source burn through the Forwarder; zero nonce in `MessageSent`).
- **Activity:** pinned 12-hour window 2026-09-28 00:00–12:00 UTC, `eth_getLogs` per emitter; the burn counts filter `DepositForBurn` on the `depositor` topic (counts in §3–§8). A 0 is a measurement of this window only.

Authoritative sources (opened for this document):
- Docs — [MCTP / Fast MCTP](https://docs.mayan.finance/architecture/mctp) (source `mayan-finance/docs`, `architecture/mctp.mdx`) · [Chains & Contracts](https://docs.mayan.finance/resources/chains-contracts)
- Repositories — [mayan-finance/swap-sdk](https://github.com/mayan-finance/swap-sdk) (`src/evm/MayanCircleArtifact.ts`, `src/evm/MayanFastMctpArtifact.ts`, `src/cctp.ts`) · [mayan-finance/example-tx-parser](https://github.com/mayan-finance/example-tx-parser) (`abis/mctp.ts`, `abis/fast-mctp.ts`)
- Verified sources — `https://eth.blockscout.com/api/v2/smart-contracts/0x875d6d37EC55c8cF220B9E5080717549d8Aa8EcA` (MayanCircle) · `https://eth.blockscout.com/api/v2/smart-contracts/0xC1062b7C5Dc8E4b1Df9F200fe360cDc0eD6e7741` (FastMCTP)

