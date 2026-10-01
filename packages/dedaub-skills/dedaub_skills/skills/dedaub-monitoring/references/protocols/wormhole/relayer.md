# Wormhole Relayer and Executor — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche; Executor also on Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the relayer sources of `wormhole-foundation/wormhole` (the `relayer/ethereum/contracts/` tree as of commit `932a2e0a2c0e6efc419552456cc0fefeb2124c6e`, the parent of the 2026-01-21 commit that removed it from `main`), `wormholelabs-xyz/example-messaging-executor`, the `wormhole-sdk-ts` constants and the Executor deployment registry. Topics and selectors recomputed as `keccak256(signature)`; addresses existence-checked with `eth_getCode`; implementations read from the EIP-1967 slot and scanned for each topic and selector.
**Scope:** the two automatic-delivery systems of Wormhole. (1) The **Wormhole Relayer** ("Standard Relayer": `WormholeRelayer` + `DeliveryProvider`), deployed on **seven chains, not on Robinhood Chain**; the docs mark it as being deprecated. (2) The **Executor** framework (`Executor`, `ExecutorQuoterRouter`, receive-with-gas-drop-off helpers), its successor, deployed on **all eight chains, Robinhood Chain (4663) included**. Topics and selectors are chain-agnostic; addresses are network-specific. The Executor-based product helpers live in the product files: Token Bridge relayers in [token-bridge.md](token-bridge.md), CCTP helpers in [cctp.md](cctp.md), NTT helpers in [ntt.md](ntt.md).

Neither system moves bridged tokens. They carry a Wormhole message to a destination contract and pay the party that delivers it.

- **Wormhole Relayer, source leg:** an application calls `sendPayloadToEvm` (or `sendToEvm`, `send`, `sendVaasToEvm`) with `msg.value` = the Core fee + the delivery quote + optional extra receiver value. The relayer publishes a delivery instruction through the Core (`LogMessagePublished`, `sender` = relayer), pays the delivery provider's reward address with an internal transfer, and emits **`SendEvent(sequence, deliveryQuote, paymentForExtraReceiverValue)`**.
- **Wormhole Relayer, destination leg:** the delivery provider calls `deliver(...)`. The relayer verifies the VAAs, calls `receiveWormholeMessages` on the target with the requested `receiverValue`, pays refunds (same chain, or a cross-chain refund through a new send), and emits **`Delivery(recipientContract, sourceChain, sequence, deliveryVaaHash, status, gasUsed, refundStatus, ...)`**. A failed target call gives `status` = 1 (`RECEIVER_FAILURE`) and refunds the receiver value. A redelivery is requested with `resendToEvm` / `resend` on the source chain.
- **Link key (Wormhole Relayer):** `SendEvent.sequence` (`topic1`) is the `sequence` of the relayer's own `LogMessagePublished`. On the destination, `Delivery` indexes `sourceChain` (`topic2`) and `sequence` (`topic3`); the emitter is the registered relayer of `sourceChain`. Both sides are on chain.
- **Executor, source leg:** an integrator publishes its own message and calls `requestExecution` with a signed quote. The Executor forwards `msg.value` to the quote's payee in the same call and emits **`RequestForExecution`**. The `requestBytes` field names the message to deliver: `ERV1` + (emitter chain, emitter address, sequence), `ERN1` + (source chain, source NTT manager, message id), `ERC1` + (CCTP v1 source domain, nonce), `ERC2` (CCTP v2, no key) or `ERB1`. **The Executor has no destination event**: the destination logs are the product's own (Token Bridge `TransferRedeemed`, NTT `TransferRedeemed`, CCTP `MintAndWithdraw`).

---

## 0. Contract families

| Contract | Chains | Role | Proxy? |
|----------|--------|------|--------|
| **WormholeRelayer** | ETH, BNB, POLY, AVAX, ARB, OP at `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911`; Base at `0x706f82e9bb5b0813501714ab5974216704980e31` | Send and deliver automatic messages; refunds; replay protection. | EIP-1967 proxy (209 B), upgraded by governance VAA |
| **DeliveryProvider** (default) | ETH, BNB, POLY, AVAX, ARB, OP at `0x7a0a53847776f7e94cc35742971acb2217b0db81`; Base at `0x70b4a48f482956983d8c69d3ae18fe229888638d` | On-chain price quotes, supported chains, reward address. `getDefaultDeliveryProvider()` of the relayer. | EIP-1967 proxy (209 B) |
| **Executor** | all 8 (chain-unique addresses, §4) | Stateless request registry: pays the quoted payee, emits `RequestForExecution`. | No (961 B) |
| **ExecutorQuoterRouter** | all except Robinhood (§4) | On-chain quote resolution (`EQ02`): `quoteExecution` / `requestExecution` for integrators that cannot use signed quotes. | No (2,421 B) |
| **VAA v1 receive-with-gas-drop-off** | all 8 at `0x13b62003C8b126Ec0748376e7ab22F79Fb8bbDF2` | Destination helper that a relay provider calls to deliver a VAA and a native drop-off. | No (749 B) |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 WormholeRelayer — emitter = the relayer proxy

| topic0 | Event |
|--------|-------|
| `0xda8540426b64ece7b164a9dce95448765f0a7263ef3ff85091c9c7361e485364` | `SendEvent(uint64 indexed sequence, uint256 deliveryQuote, uint256 paymentForExtraReceiverValue)` — **source leg**; value = the quote, paid to the provider in the same transaction |
| `0xbccc00b713f54173962e7de6098f643d8ebf53d488d71f4b2a5171496d038f9e` | `Delivery(address indexed recipientContract, uint16 indexed sourceChain, uint64 indexed sequence, bytes32 deliveryVaaHash, uint8 status, uint256 gasUsed, uint8 refundStatus, bytes additionalStatusInfo, bytes overridesInfo)` — **destination leg**; `status` 0 = SUCCESS, 1 = RECEIVER_FAILURE; `refundStatus` 0 REFUND_SENT, 1 REFUND_FAIL, 2 CROSS_CHAIN_REFUND_SENT, 3 CROSS_CHAIN_REFUND_FAIL_PROVIDER_NOT_SUPPORTED, 4 CROSS_CHAIN_REFUND_FAIL_NOT_ENOUGH, 5 NO_REFUND_REQUESTED |
| `0x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49` | `ContractUpgraded(address indexed oldContract, address indexed newContract)` — admin; same topic0 as Core / Token Bridge |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — admin |

In the source, `status` and `refundStatus` are enums (`DeliveryStatus`, `RefundStatus`); the ABI type is `uint8`.

### 1.2 DeliveryProvider — emitter = the provider proxy (all admin / status)

| topic0 | Event |
|--------|-------|
| `0xeaa35dfb768f1ccf1313ea7faae95ecba5820bf18c08a3e58cbdf3aaa4259096` | `ChainSupportUpdated(uint16 targetChain, bool isSupported)` |
| `0x0d18b5fd22306e373229b9439188228edca81207d1667f604daf6cef8aa3ee67` | `OwnershipTransfered(address indexed oldOwner, address indexed newOwner)` — spelled "Transfered" in the source |
| `0x97e1f675f69047e4b663d3b795841c629240f48eb403a6337e5367c4405737e0` | `RewardAddressUpdated(address indexed newAddress)` — **where send payments go** |
| `0xca40221dbf955f8619d86581ec5e380ca9ce15f9083a0ab52909d2383d2249f6` | `TargetChainAddressUpdated(uint16 indexed targetChain, bytes32 indexed newAddress)` |
| `0xa73b3e840df75fb07563bcc4e73041b76e761005717b548d420aee0dbfb82e88` | `DeliverGasOverheadUpdated(uint256 indexed oldGasOverhead, uint256 indexed newGasOverhead)` — the source type `Gas` is a `uint256` value type |
| `0x80ba15fb50f5b4a4de303ae58538112279fb2b00af61c4d38126265bae2944da` | `WormholeRelayerUpdated(address coreRelayer)` |
| `0xaed3d5a75b6e523af32a68084c636eb7880958755291bb890cf7c8abc107a556` | `AssetConversionBufferUpdated(uint16 targetChain, uint16 buffer, uint16 bufferDenominator)` |

### 1.3 Executor framework

| topic0 | Event |
|--------|-------|
| `0xd870d87e4a7c33d0943b0a3d2822b174e239cc55c169af14cc56467a4489e3b5` | `RequestForExecution(address indexed quoterAddress, uint256 amtPaid, uint16 dstChain, bytes32 dstAddr, address refundAddr, bytes signedQuote, bytes requestBytes, bytes relayInstructions)` — emitter = Executor; **source leg**; `amtPaid` = `msg.value`, already paid to the payee |
| `0xaa364c5b6118f7297a47ce8a073345ea9d8c78bfd2f79ac24aa8c14c277f6088` | `OnChainQuote(address implementation)` — emitter = ExecutorQuoterRouter, on an on-chain-quoted request |
| `0xeedb3b08f9d6b31868ba849585a6520456b391ba627b04021952c145f61f1cdd` | `QuoterContractUpdate(address indexed quoterAddress, address implementation)` — ExecutorQuoterRouter admin (quoter governance message) |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 WormholeRelayer

Tuple types: `VaaKey = (uint16 chainId, bytes32 emitterAddress, uint64 sequence)`; `MessageKey = (uint8 keyType, bytes encodedKey)`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8fecdd02` | `sendPayloadToEvm(uint16 targetChain, address targetAddress, bytes payload, uint256 receiverValue, uint256 gasLimit)` | Payable; the common entry. Emits `SendEvent`. |
| `0x4b5ca6f4` | `sendPayloadToEvm(uint16 targetChain, address targetAddress, bytes payload, uint256 receiverValue, uint256 gasLimit, uint16 refundChain, address refundAddress)` | With refund target. |
| `0x329a2be7` | `sendVaasToEvm(uint16 targetChain, address targetAddress, bytes payload, uint256 receiverValue, uint256 gasLimit, (uint16 chainId, bytes32 emitterAddress, uint64 sequence)[] vaaKeys)` | Delivers extra VAAs too. |
| `0x32b2fc0e` | `sendVaasToEvm(uint16 targetChain, address targetAddress, bytes payload, uint256 receiverValue, uint256 gasLimit, (uint16 chainId, bytes32 emitterAddress, uint64 sequence)[] vaaKeys, uint16 refundChain, address refundAddress)` | |
| `0x3a2c767d` | `sendToEvm(uint16 targetChain, address targetAddress, bytes payload, uint256 receiverValue, uint256 paymentForExtraReceiverValue, uint256 gasLimit, uint16 refundChain, address refundAddress, address deliveryProviderAddress, (uint16 chainId, bytes32 emitterAddress, uint64 sequence)[] vaaKeys, uint8 consistencyLevel)` | |
| `0xc055120e` | `sendToEvm(uint16 targetChain, address targetAddress, bytes payload, uint256 receiverValue, uint256 paymentForExtraReceiverValue, uint256 gasLimit, uint16 refundChain, address refundAddress, address deliveryProviderAddress, (uint8 keyType, bytes encodedKey)[] messageKeys, uint8 consistencyLevel)` | `MessageKey` variant (for example CCTP keys). |
| `0xc81fb7fe` | `send(uint16 targetChain, bytes32 targetAddress, bytes payload, uint256 receiverValue, uint256 paymentForExtraReceiverValue, bytes encodedExecutionParameters, uint16 refundChain, bytes32 refundAddress, address deliveryProviderAddress, (uint16 chainId, bytes32 emitterAddress, uint64 sequence)[] vaaKeys, uint8 consistencyLevel)` | Generic (non-EVM target). |
| `0xcee4bda0` | `send(uint16 targetChain, bytes32 targetAddress, bytes payload, uint256 receiverValue, uint256 paymentForExtraReceiverValue, bytes encodedExecutionParameters, uint16 refundChain, bytes32 refundAddress, address deliveryProviderAddress, (uint8 keyType, bytes encodedKey)[] messageKeys, uint8 consistencyLevel)` | |
| `0x8b0301b1` | `resendToEvm((uint16 chainId, bytes32 emitterAddress, uint64 sequence) deliveryVaaKey, uint16 targetChain, uint256 newReceiverValue, uint256 newGasLimit, address newDeliveryProviderAddress)` | Redelivery request; emits `SendEvent`. |
| `0xb686d089` | `resend((uint16 chainId, bytes32 emitterAddress, uint64 sequence) deliveryVaaKey, uint16 targetChain, uint256 newReceiverValue, bytes newEncodedExecutionParameters, address newDeliveryProviderAddress)` | |
| `0xa60eb4c8` | `deliver(bytes[] encodedVMs, bytes encodedDeliveryVAA, address relayerRefundAddress, bytes deliveryOverrides)` | Payable; destination. Emits `Delivery`. |
| `0xc23ee3c3` | `quoteEVMDeliveryPrice(uint16 targetChain, uint256 receiverValue, uint256 gasLimit)` | View — `(nativePriceQuote, targetChainRefundPerGasUnused)`. |
| `0x80ebabd0` | `quoteEVMDeliveryPrice(uint16 targetChain, uint256 receiverValue, uint256 gasLimit, address deliveryProviderAddress)` | View. |
| `0xa79629d8` | `quoteDeliveryPrice(uint16 targetChain, uint256 receiverValue, bytes encodedExecutionParameters, address deliveryProviderAddress)` | View. |
| `0x24320c9f` | `getDefaultDeliveryProvider()` | View. |
| `0x3e8267e7` | `getRegisteredWormholeRelayerContract(uint16 chainId)` | View — peer relayer (bytes32). |
| `0xd0625a19` | `deliveryAttempted(bytes32 deliveryHash)` | View. |
| `0x40984f08` | `deliverySuccessBlock(bytes32 deliveryHash)` | View. |
| `0x5a3b92e8` | `deliveryFailureBlock(bytes32 deliveryHash)` | View. |
| `0x5cb8cae2` | `submitContractUpgrade(bytes encodedVm)` | Governance VAA. **Admin.** |
| `0x3ed334df` | `registerWormholeRelayerContract(bytes encodedVm)` | Governance VAA. **Admin.** |
| `0x28b1d852` | `setDefaultDeliveryProvider(bytes encodedVm)` | Governance VAA. **Admin.** |
| `0x529dca32` | `receiveWormholeMessages(bytes payload, bytes[] additionalMessages, bytes32 sourceAddress, uint16 sourceChain, bytes32 deliveryHash)` | Implemented by every target contract (`IWormholeReceiver`), for example legacy NTT transceivers. |

### 2.2 Executor framework

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc513d437` | `requestExecution(uint16 dstChain, bytes32 dstAddr, address refundAddr, bytes signedQuoteBytes, bytes requestBytes, bytes relayInstructions)` | Executor; payable; emits `RequestForExecution`. |
| `0x36db3131` | `ourChain()` | Executor view — the Wormhole chain id (immutable). |
| `0xff74877a` | `requestExecution(uint16 dstChain, bytes32 dstAddr, address refundAddr, address quoterAddr, bytes requestBytes, bytes relayInstructions)` | ExecutorQuoterRouter; payable; emits `OnChainQuote` and the Executor's `RequestForExecution`. |
| `0x8efd6449` | `quoteExecution(uint16 dstChain, bytes32 dstAddr, address refundAddr, address quoterAddr, bytes requestBytes, bytes relayInstructions)` | ExecutorQuoterRouter view. |
| `0x0aad8b63` | `updateQuoterContract(bytes gov)` | ExecutorQuoterRouter; signed quoter governance. **Admin.** |

The VAA v1 receive-with-gas-drop-off helper was called with selector `0x6dffc391` in the sampled delivery `0x809fce8dd7396d8593821a2dfbb0a37a8f693183f9c3ebefd8487c5498b60c22` (present in its 749 B bytecode). Its signature is not in the repositories read (unverified).

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All existence-checked with `eth_getCode` on 2026-09-29. Wormhole chain id **2**.

| Role | Address | One-liner |
|------|---------|-----------|
| **WormholeRelayer** (proxy) | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | 209 B proxy; implementation `0x90995dbd1aae85872451b50a569de947d34ac4ee` (17,750 B). |
| **DeliveryProvider** (default, proxy) | `0x7a0a53847776f7e94cc35742971acb2217b0db81` | `getDefaultDeliveryProvider()`; implementation `0x9db2f72b8e5aafa88f62852a0658f0b9249f6454` (7,564 B). |
| **Executor** | `0x84EEe8dBa37C36947397E1E11251cA9A06Fc6F8a` | `ourChain()` = 2. |
| **ExecutorQuoterRouter** | `0xF22F1c0A3a8Cb42F695601731974784C499C4EF3` | Not a proxy (implementation slot 0). |
| VAA v1 receive-with-gas-drop-off | `0x13b62003C8b126Ec0748376e7ab22F79Fb8bbDF2` | Same address on all eight chains. |

---

## 4. Addresses — the other seven chains

### 4.1 Wormhole Relayer and default DeliveryProvider

| Chain | EVM id | Wormhole id | WormholeRelayer (proxy) | Relayer implementation | Default DeliveryProvider |
|-------|--------|-------------|-------------------------|------------------------|--------------------------|
| Ethereum | 1 | 2 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | `0x90995dbd1aae85872451b50a569de947d34ac4ee` | `0x7a0a53847776f7e94cc35742971acb2217b0db81` |
| Base | 8453 | 30 | `0x706f82e9bb5b0813501714ab5974216704980e31` | `0x231ca706096427bd674bfaec28b34d8fca26e2a1` | `0x70b4a48f482956983d8c69d3ae18fe229888638d` |
| Arbitrum One | 42161 | 23 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | `0x27c472d1db89afd6f41a61eec0f4db996800f8cd` | `0x7a0a53847776f7e94cc35742971acb2217b0db81` |
| Optimism | 10 | 24 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | `0x1efa946b0ac2e3357a38124fd1baa7139048d689` | `0x7a0a53847776f7e94cc35742971acb2217b0db81` |
| Polygon PoS | 137 | 5 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | `0xe4451e8479115cea6b785bf71c1cd4ada963991c` | `0x7a0a53847776f7e94cc35742971acb2217b0db81` |
| BNB Smart Chain | 56 | 4 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | `0xb6134890a64e9ffc54ecc2702bdf41deedd4999c` | `0x7a0a53847776f7e94cc35742971acb2217b0db81` |
| Avalanche C-Chain | 43114 | 6 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | `0x27c472d1db89afd6f41a61eec0f4db996800f8cd` | `0x7a0a53847776f7e94cc35742971acb2217b0db81` |
| **Robinhood Chain** | 4663 | 72 | ❌ `0x` | — | ❌ `0x` |

On every chain read, `getRegisteredWormholeRelayerContract(2)` returned `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` and `getRegisteredWormholeRelayerContract(30)` returned `0x706f82e9bb5b0813501714ab5974216704980e31`. All implementations are 17,750 B and contain `SendEvent`, `Delivery`, `ContractUpgraded`, `sendPayloadToEvm` and `deliver`. Arbitrum and Avalanche use the same implementation address with different bytecode (code hashes `0x96f8efd4e7ae383953b83451eef8ca431face54c8429707da88b1e6efa287328` and `0x7975d8d4dce175cbf5a65c46525525371acca2c850b47ca3f5b18a23dc80a479`).

### 4.2 Executor framework

| Chain | Executor | `ourChain()` | ExecutorQuoterRouter | VAA v1 receive-with-gas-drop-off |
|-------|----------|--------------|----------------------|----------------------------------|
| Ethereum | `0x84EEe8dBa37C36947397E1E11251cA9A06Fc6F8a` | 2 | `0xF22F1c0A3a8Cb42F695601731974784C499C4EF3` | `0x13b62003C8b126Ec0748376e7ab22F79Fb8bbDF2` |
| Base | `0x9E1936E91A4a5AE5A5F75fFc472D6cb8e93597ea` | 30 | `0x265fd0500a430d65d6D79Cd8707F24C048604658` | `0x13b62003C8b126Ec0748376e7ab22F79Fb8bbDF2` |
| Arbitrum One | `0x3980f8318fc03d79033Bbb421A622CDF8d2Eeab4` | 23 | `0x32eec14c963c23176bd8951f192292006756bDcC` | `0x13b62003C8b126Ec0748376e7ab22F79Fb8bbDF2` |
| Optimism | `0x85B704501f6AE718205C0636260768C4e72ac3e7` | 24 | `0xa3B6551cCbB5Fe1dc33b71EE3590B1Df22ae75B3` | `0x13b62003C8b126Ec0748376e7ab22F79Fb8bbDF2` |
| Polygon PoS | `0x0B23efA164aB3eD08e9a39AC7aD930Ff4F5A5e81` | 5 | `0x2a856931603930B827B1A4352FB4D66fA029F123` | `0x13b62003C8b126Ec0748376e7ab22F79Fb8bbDF2` |
| BNB Smart Chain | `0xeC8cCCD058DbF28e5D002869Aa9aFa3992bf4ee0` | 4 | `0xc921F293c27F332D47283174b11C872295624Edb` | `0x13b62003C8b126Ec0748376e7ab22F79Fb8bbDF2` |
| Avalanche C-Chain | `0x4661F0E629E4ba8D04Ee90080Aee079740B00381` | 6 | `0xA3a2A615774d34c6a4dF443C488B084eacaBd2D0` | `0x13b62003C8b126Ec0748376e7ab22F79Fb8bbDF2` |
| **Robinhood Chain** | `0xd19aAd5a69F7D35Cee169D9D90e1BbCB795ABB38` | 72 | — (not in the registry) | `0x13b62003C8b126Ec0748376e7ab22F79Fb8bbDF2` |

Every Executor is 961 B and contains `RequestForExecution` and `requestExecution`. The Executor addresses agree between `executor.ts` of the SDK and the Executor deployment registry; the docs moved the Executor list to the Executor Explorer, which reads the same registry.

---

## 5. Cross-chain summary

| Chain | EVM id | Wormhole id | WormholeRelayer | DeliveryProvider | Executor | Quoter router |
|-------|--------|-------------|-----------------|------------------|----------|---------------|
| Ethereum | 1 | 2 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | ✅ | `0x84EEe8dBa37C36947397E1E11251cA9A06Fc6F8a` | ✅ |
| Base | 8453 | 30 | `0x706f82e9bb5b0813501714ab5974216704980e31` | ✅ | `0x9E1936E91A4a5AE5A5F75fFc472D6cb8e93597ea` | ✅ |
| Arbitrum One | 42161 | 23 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | ✅ | `0x3980f8318fc03d79033Bbb421A622CDF8d2Eeab4` | ✅ |
| Optimism | 10 | 24 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | ✅ | `0x85B704501f6AE718205C0636260768C4e72ac3e7` | ✅ |
| Polygon PoS | 137 | 5 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | ✅ | `0x0B23efA164aB3eD08e9a39AC7aD930Ff4F5A5e81` | ✅ |
| BNB Smart Chain | 56 | 4 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | ✅ | `0xeC8cCCD058DbF28e5D002869Aa9aFa3992bf4ee0` | ✅ |
| Avalanche C-Chain | 43114 | 6 | `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` | ✅ | `0x4661F0E629E4ba8D04Ee90080Aee079740B00381` | ✅ |
| **Robinhood Chain** | 4663 | 72 | ❌ | ❌ | `0xd19aAd5a69F7D35Cee169D9D90e1BbCB795ABB38` | ❌ |

**Vanity address:** the relayer shares `0x27428DD2d3DD32A4D7f7C497eAaa23130d894911` on six chains; Base alone uses `0x706f82e9bb5b0813501714ab5974216704980e31` (the vanity address has no code on Base). The Executors have chain-unique addresses.

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **WormholeRelayer** | EIP-1967 proxy (209 B); upgrade logic in `WormholeRelayerGovernance` | Implementation slot populated (§4.1); admin slot 0 on every chain read | Guardian governance VAA (`submitContractUpgrade`), emitter chain 1, emitter `0x0000000000000000000000000000000000000000000000000000000000000004` |
| **DeliveryProvider** | EIP-1967 proxy (209 B) | Implementation slot populated (ETH `0x9db2f72b8e5aafa88f62852a0658f0b9249f6454`, Base `0x3715d5ede1f3ffcb7694abd04baa16ca564f7476`, ARB `0xea445c026e44921604c799122b69ca717886c25d`, OP and BNB `0x33294e78b22a865d94ead382c466568efa6b71c7`, POLY `0xe1fdb69f81a18d20ae307684e270df767e48fcd4`, AVAX `0xbc8ce52393993458040f33d486300d0c397308fd`) | The provider's owner (`OwnershipTransfered` event) |
| Executor, ExecutorQuoterRouter, VAA v1 receive helper | Not proxies | Implementation slot 0; full bytecode | Immutable; the router accepts signed quoter-registration messages |

---

## 7. Detection invariants & gotchas

1. **The relayer publishes the NTT or application message itself.** For a legacy NTT transceiver in relayer mode, the Core's `LogMessagePublished` has `sender` = the Wormhole Relayer, not the transceiver (sample Base `0x12fedaa0d2279d2a37a0f2a0e691d3586f8e1cc4689fefa11765f28d32df5a52`: token burn at the NTT manager, `LogMessagePublished` from the relayer, `SendEvent`, then the NTT events).
2. **`SendEvent` and `Delivery` are status events.** The value in the source transaction is a fee, paid to the provider's reward address by an internal transfer. The bridged value moves in the target's own events inside the `deliver` transaction (sample Ethereum `0x5c5744ff8ee150733861659a2fabbe4e146a235c572959cf9a9e83489445ccd6`: NTT `TransferRedeemed`, a mint, then `Delivery`).
3. **`Delivery.status = 1` is a failed delivery.** The target call reverted; the receiver value was refunded and the application message was not executed. It can be redelivered later (`resendToEvm` on the source chain, a new `SendEvent`).
4. **Deprecation.** The docs say the Standard Relayer is being deprecated and ask integrators to move to the Executor. Traffic in the window was small (below), and the NTT and Token Bridge routes now request the Executor.
5. **`RequestForExecution` is a payment plus a request, not a transfer.** `amtPaid` goes to the quote's payee in the same call. Decode `requestBytes` to find the message: its first 4 bytes are the type (`ERV1`, `ERN1`, `ERC1`, `ERC2`, `ERB1`). For `ERV1` the next 42 bytes are the VAA key.
6. **The Executor has no destination event.** Match the request to the product event on the destination chain: `ERV1` to Token Bridge `TransferRedeemed` (same key), `ERN1` to NTT `TransferRedeemed(digest)` via the NTT message id, `ERC1` to CCTP v1 `MessageReceived(sourceDomain, nonce)`.
7. **Robinhood has the Executor but no Wormhole Relayer.** All Robinhood automatic deliveries go through the Executor (1 `RequestForExecution` in the window).

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_SEND_EVENT              = '\xda8540426b64ece7b164a9dce95448765f0a7263ef3ff85091c9c7361e485364'
TOPIC_DELIVERY                = '\xbccc00b713f54173962e7de6098f643d8ebf53d488d71f4b2a5171496d038f9e'
TOPIC_CONTRACT_UPGRADED       = '\x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49'
TOPIC_REWARD_ADDRESS_UPDATED  = '\x97e1f675f69047e4b663d3b795841c629240f48eb403a6337e5367c4405737e0'
TOPIC_CHAIN_SUPPORT_UPDATED   = '\xeaa35dfb768f1ccf1313ea7faae95ecba5820bf18c08a3e58cbdf3aaa4259096'
TOPIC_REQUEST_FOR_EXECUTION   = '\xd870d87e4a7c33d0943b0a3d2822b174e239cc55c169af14cc56467a4489e3b5'
TOPIC_ON_CHAIN_QUOTE          = '\xaa364c5b6118f7297a47ce8a073345ea9d8c78bfd2f79ac24aa8c14c277f6088'
TOPIC_QUOTER_CONTRACT_UPDATE  = '\xeedb3b08f9d6b31868ba849585a6520456b391ba627b04021952c145f61f1cdd'

-- ===== Selectors =====
SEL_SEND_PAYLOAD_TO_EVM       = '\x8fecdd02'
SEL_SEND_PAYLOAD_TO_EVM_REFUND= '\x4b5ca6f4'
SEL_SEND_TO_EVM_VAAKEYS       = '\x3a2c767d'
SEL_SEND_TO_EVM_MSGKEYS       = '\xc055120e'
SEL_RESEND_TO_EVM             = '\x8b0301b1'
SEL_DELIVER                   = '\xa60eb4c8'
SEL_RECEIVE_WORMHOLE_MESSAGES = '\x529dca32'
SEL_RELAYER_UPGRADE           = '\x5cb8cae2'
SEL_SET_DEFAULT_PROVIDER      = '\x28b1d852'
SEL_REQUEST_EXECUTION         = '\xc513d437'
SEL_ROUTER_REQUEST_EXECUTION  = '\xff74877a'

-- ===== Wormhole Relayer per chain (no Robinhood) =====
ETH_WORMHOLE_RELAYER          = '\x27428dd2d3dd32a4d7f7c497eaaa23130d894911'
BNB_WORMHOLE_RELAYER          = '\x27428dd2d3dd32a4d7f7c497eaaa23130d894911'
POLY_WORMHOLE_RELAYER         = '\x27428dd2d3dd32a4d7f7c497eaaa23130d894911'
AVAX_WORMHOLE_RELAYER         = '\x27428dd2d3dd32a4d7f7c497eaaa23130d894911'
ARB_WORMHOLE_RELAYER          = '\x27428dd2d3dd32a4d7f7c497eaaa23130d894911'
OP_WORMHOLE_RELAYER           = '\x27428dd2d3dd32a4d7f7c497eaaa23130d894911'
BASE_WORMHOLE_RELAYER         = '\x706f82e9bb5b0813501714ab5974216704980e31'
ETH_DELIVERY_PROVIDER         = '\x7a0a53847776f7e94cc35742971acb2217b0db81'
BASE_DELIVERY_PROVIDER        = '\x70b4a48f482956983d8c69d3ae18fe229888638d'

-- ===== Executor per chain =====
ETH_EXECUTOR                  = '\x84eee8dba37c36947397e1e11251ca9a06fc6f8a'
BASE_EXECUTOR                 = '\x9e1936e91a4a5ae5a5f75ffc472d6cb8e93597ea'
ARB_EXECUTOR                  = '\x3980f8318fc03d79033bbb421a622cdf8d2eeab4'
OP_EXECUTOR                   = '\x85b704501f6ae718205c0636260768c4e72ac3e7'
POLY_EXECUTOR                 = '\x0b23efa164ab3ed08e9a39ac7ad930ff4f5a5e81'
BNB_EXECUTOR                  = '\xec8cccd058dbf28e5d002869aa9afa3992bf4ee0'
AVAX_EXECUTOR                 = '\x4661f0e629e4ba8d04ee90080aee079740b00381'
RH_EXECUTOR                   = '\xd19aad5a69f7d35cee169d9d90e1bbcb795abb38'
ETH_EXECUTOR_QUOTER_ROUTER    = '\xf22f1c0a3a8cb42f695601731974784c499c4ef3'
RH_VAA_V1_RECEIVE_GAS_DROP    = '\x13b62003c8b126ec0748376e7ab22f79fb8bbdf2'   -- same address on all eight chains
```

---

## 9. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `relayer/ethereum/contracts/interfaces/relayer/IWormholeRelayer.sol`, `relayer/wormholeRelayer/WormholeRelayerGovernance.sol`, `relayer/deliveryProvider/DeliveryProviderGovernance.sol` (commit `932a2e0a2c0e6efc419552456cc0fefeb2124c6e`), and `evm/src/Executor.sol`, `ExecutorQuoterRouter.sol`, `libraries/ExecutorMessages.sol` of the Executor repo. Relayer implementations scanned for `SendEvent`, `Delivery`, `ContractUpgraded` (`PUSH32`) and `sendPayloadToEvm`, `deliver` (`PUSH4`) on seven chains; Executors for `RequestForExecution` and `requestExecution` on all eight; the Ethereum quoter router for `requestExecution`, `quoteExecution`, `OnChainQuote` and `QuoterContractUpdate`.
- **Addresses:** `relayer.ts` and `executor.ts` of the SDK, and the Executor deployment registry (`registry-api.wormholelabs.xyz/v1/public/deployments`, namespaces `w7/executor`, `w7/on-chain-quoter/quoter-router`, `w7/vaa-v1-receiver/vaa-v1-receive-with-gas-drop`). All existence-checked with `eth_getCode`; `getDefaultDeliveryProvider()`, `getRegisteredWormholeRelayerContract(2)`, `getRegisteredWormholeRelayerContract(30)` and `ourChain()` read live. Robinhood: `eth_getCode` = `0x` for the relayer, both delivery providers and the Ethereum quoter router address.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):** `SendEvent`: Ethereum 1, Base 8, Arbitrum 2, Optimism 0, Polygon 5, BNB 6, Avalanche 0 (Robinhood: no relayer). `Delivery`: Ethereum 2, Base 8, Arbitrum 4, Optimism 0, Polygon 0, BNB 8, Avalanche 0. `RequestForExecution`: Ethereum 51, Base 12, Arbitrum 20, Optimism 1, Polygon 12, BNB 19, Avalanche 6, Robinhood 1. On the six chains with a sender split, every `SendEvent` matched one `LogMessagePublished` with `sender` = relayer.
- **Samples:** Ethereum `SendEvent` `0xc311e14e6fbc0b0ebc9730edb52b4fa9aac9a1a1726466b91b5de881cecc3ec1`; Ethereum `Delivery` `0x5c5744ff8ee150733861659a2fabbe4e146a235c572959cf9a9e83489445ccd6`; Ethereum `RequestForExecution` through the CCTP v2 helper `0xa88a6694cc976107e8268fd609a611d9af5feb7f956cf04f79c739be5a3f708f` (`msg.value` 129,280,658,916,604 wei paid with the request).

Authoritative sources:
- [wormhole-foundation/wormhole @ 932a2e0a2c0e6efc419552456cc0fefeb2124c6e](https://github.com/wormhole-foundation/wormhole/tree/932a2e0a2c0e6efc419552456cc0fefeb2124c6e/relayer/ethereum/contracts) — Wormhole Relayer and DeliveryProvider
- [wormholelabs-xyz/example-messaging-executor](https://github.com/wormholelabs-xyz/example-messaging-executor) — `evm/src/`
- [wormhole-foundation/wormhole-sdk-ts](https://github.com/wormhole-foundation/wormhole-sdk-ts) — `core/base/src/constants/contracts/relayer.ts`, `executor.ts`, `executorQuoter.ts`
- Docs — [Relayers overview](https://wormhole.com/docs/protocol/infrastructure/relayers/relayer/) · [Executor framework](https://wormhole.com/docs/protocol/infrastructure/relayers/executor-framework/) · [Standard Relayer to Executor migration](https://wormhole.com/docs/protocol/infrastructure/relayers/executor-vs-sr/) · [Executor addresses](https://wormhole.com/docs/reference/executor-addresses/)
- [Executor Explorer](https://wormholelabs-xyz.github.io/executor-explorer/) (registry feed) · Explorers — [Etherscan relayer](https://etherscan.io/address/0x27428dd2d3dd32a4d7f7c497eaaa23130d894911) · [Robinhood Chain Blockscout Executor](https://robinhoodchain.blockscout.com/address/0xd19aAd5a69F7D35Cee169D9D90e1BbCB795ABB38)
