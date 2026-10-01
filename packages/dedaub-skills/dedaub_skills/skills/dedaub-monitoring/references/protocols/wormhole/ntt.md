# Wormhole Native Token Transfers (NTT) — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, `wormhole-foundation/native-token-transfers` (`evm/src/` on `main` and the tags `v1.0.0+evm`, `v1.2.0+evm`, `v2.0.0+evm`), `wormholelabs-xyz/example-ntt-with-executor-evm`, the Executor deployment registry and the Wormholescan NTT API (`api.wormholescan.io/api/v1/native-token-transfer/token-list` and `/ntt/token/{chain}/{token}`). Topics and selectors recomputed as `keccak256(signature)`; manager addresses existence-checked with `eth_getCode`; `token()`, `getMode()` and `owner()` read live.
**Scope:** the events and functions that **every NTT token emits** (the `NttManager` and the `WormholeTransceiver`), the NTT-with-Executor helpers, and a list of major NTT tokens with their managers per chain. NTT is live on **all eight target chains, Robinhood Chain (4663) included**. Topics and selectors are chain-agnostic; there is **no single NTT address list**: each token deploys its own manager and transceiver on each chain.

NTT moves a token natively. Each token has one `NttManager` per chain, in **LOCKING** mode (escrow on the token's home chain) or **BURNING** mode (burn on send, mint on receive). The manager sends through one or more **transceivers** (almost always one `WormholeTransceiver`; wstETH also uses an Axelar transceiver with a 2-of-2 threshold).

- **Source leg:** `transfer(...)` on the manager. The manager pulls the tokens from the caller (`Transfer` user → manager), then keeps them (LOCKING) or burns them (`Transfer` manager → `0x0`, BURNING). It emits **`TransferSent(recipient, refundAddress, amount, fee, recipientChain, msgSequence)`** and, in v1.1+ builds, **`TransferSent(digest)`**. The transceiver emits `RelayingInfo` and `SendTransceiverMessage` and calls the Core (`LogMessagePublished`, `sender` = transceiver; or the Wormhole Relayer for legacy relayer mode).
- **Destination leg:** a relayer (Executor provider, standard relayer or the user) calls `receiveMessage(vaa)` on the destination transceiver. It emits **`ReceivedMessage(digest, emitterChainId, emitterAddress, sequence)`**; the manager emits **`MessageAttestedTo(digest, transceiver, index)`** and, at threshold, **`TransferRedeemed(digest)`**, then unlocks (`Transfer` manager → recipient) or mints (`Transfer` `0x0` → recipient).
- **Rate limits, queue and cancel:** an outbound transfer over the limit is queued (`OutboundTransferQueued`, `OutboundTransferRateLimited`) and later completed or cancelled (`OutboundTransferCancelled`, refund to the sender). An inbound transfer over the limit is queued (`InboundTransferQueued`) and completed later by `completeInboundQueuedTransfer` (then `TransferRedeemed`).
- **Link key:** the **digest** = `keccak256(abi.encodePacked(uint16 sourceChainId, encodedNttManagerMessage))`. It is on chain on both sides in v1.1+ builds (`TransferSent(bytes32 indexed digest)` ↔ `TransferRedeemed(bytes32 indexed digest)`). For older builds without the digest event, use the Wormhole key: source `(Wormhole chain, transceiver, LogMessagePublished.sequence)` ↔ destination `ReceivedMessage(digest, emitterChainId, emitterAddress, sequence)`, which maps the key to the digest. The NTT message id (`msgSequence`) is a per-manager counter.

---

## 0. Contract families

| Contract | Deployed by | Role | Proxy? |
|----------|-------------|------|--------|
| **NttManager** | each token issuer, one per chain | Lock / burn, unlock / mint, peers, rate limits, threshold of transceivers, pause. | EIP-1967 proxy (133–209 B); `upgrade(address)` by `owner()` |
| **WormholeTransceiver** | each token issuer, one per manager | Sends and receives the NTT message over Wormhole. | EIP-1967 proxy; `upgrade(address)` by the manager's owner |
| **NttManagerWithExecutor** (v1, v2) | Wormhole, one per chain (§4.2) | Front-end helper: calls `NttManager.transfer` and `Executor.requestExecution` in one call, with a referrer fee. | No |
| **Multi-receive-with-gas-drop-off** | Wormhole (§4.2) | Destination helper for relay providers (several NTT messages + native drop-off). | No |
| **Guardian Governance** | Wormhole ([core.md](core.md) §4.2) | Guardian-signed owner of some managers (W). | No |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 NttManager — value-bearing and link events

| topic0 | Event |
|--------|-------|
| `0xe54e51e42099622516fa3b48e9733581c9dbdcb771cafb093f745a0532a35982` | `TransferSent(bytes32 indexed recipient, bytes32 indexed refundAddress, uint256 amount, uint256 fee, uint16 recipientChain, uint64 msgSequence)` — **source leg** (v1.2+ layout). **The v1.0 layout has the same topic0 with nothing indexed**: `TransferSent(bytes32 recipient, bytes32 refundAddress, uint256 amount, uint256 fee, uint16 recipientChain, uint64 msgSequence)`, 1 topic and 192 data bytes instead of 3 topics and 128 data bytes. `amount` is untrimmed (token decimals); `fee` is the total transceiver quote in native wei. |
| `0x3e6ae56314c6da8b461d872f41c6d0bb69317b9d0232805aaccfa45df1a16fa0` | `TransferSent(bytes32 indexed digest)` — **source link key**; absent in older builds |
| `0x504e6efe18ab9eed10dc6501a417f5b12a2f7f2b1593aed9b89f9bce3cf29a91` | `TransferRedeemed(bytes32 indexed digest)` — **destination leg**; emitted just before the unlock / mint |
| `0xf80e572ae1b63e2449629b6c7d783add85c36473926f216077f17ee002bcfd07` | `OutboundTransferCancelled(uint256 sequence, address recipient, uint256 amount)` — **refund path**: a queued outbound transfer was cancelled and the tokens returned (the source code also emits it for a cancelled inbound path, with `sequence` = the digest) |
| `0x35a2101eaac94b493e0dfca061f9a7f087913fde8678e7cde0aca9897edba0e5` | `MessageAttestedTo(bytes32 digest, address transceiver, uint8 index)` — status; one per transceiver attestation |
| `0x4069dff8c9df7e38d2867c0910bd96fd61787695e5380281148c04932d02bef2` | `MessageAlreadyExecuted(bytes32 indexed sourceNttManager, bytes32 indexed msgHash)` — status (replay ignored) |

### 1.2 NttManager — rate limits and queues (status)

| topic0 | Event |
|--------|-------|
| `0x69add1952a6a6b9cb86f04d05f0cb605cbb469a50ae916139d34495a9991481f` | `OutboundTransferQueued(uint64 queueSequence)` |
| `0xf33512b84e24a49905c26c6991942fc5a9652411769fc1e448f967cdb049f08a` | `OutboundTransferRateLimited(address indexed sender, uint64 sequence, uint256 amount, uint256 currentCapacity)` |
| `0x7f63c9251d82a933210c2b6d0b0f116252c3c116788120e64e8e8215df6f3162` | `InboundTransferQueued(bytes32 digest)` |

### 1.3 NttManager — admin

| topic0 | Event |
|--------|-------|
| `0x1456404e7f41f35c3daac941bb50bad417a66275c3040061b4287d787719599d` | `PeerUpdated(uint16 indexed chainId_, bytes32 oldPeerContract, uint8 oldPeerDecimals, bytes32 peerContract, uint8 peerDecimals)` — **a new peer can mint or unlock here; high severity** |
| `0x7e3b0fc388be9d36273f66210aed83be975df3a9adfffa4c734033f498f362cd` | `OutboundTransferLimitUpdated(uint256 oldLimit, uint256 newLimit)` — v1.2+ |
| `0x739ed886fd81a3ddc9f4b327ab69152e513cd45b26fda0c73660eaca8e119301` | `InboundTransferLimitUpdated(uint16 indexed chainId, uint256 oldLimit, uint256 newLimit)` — v1.2+ |
| `0x2a855b929b9a53c6fb5b5ed248b27e502b709c088e036a5aa17620c8fc5085a9` | `ThresholdChanged(uint8 oldThreshold, uint8 threshold)` |
| `0xf05962b5774c658e85ed80c91a75af9d66d2af2253dda480f90bce78aff5eda5` | `TransceiverAdded(address transceiver, uint256 transceiversNum, uint8 threshold)` |
| `0x697a3853515b88013ad432f29f53d406debc9509ed6d9313dcfe115250fcd18f` | `TransceiverRemoved(address transceiver, uint8 threshold)` |
| `0x0e2fb031ee032dc02d8011dc50b816eb450cf856abd8261680dac74f72165bd2` | `Paused(bool paused)` |
| `0xe11c2112add17fb763d3bd59f63b10429c3e11373da4fb8ef6725107a2fdc4b0` | `NotPaused(bool notPaused)` — unpause |
| `0x51c4874e0f23f262e04a38c51751336dde72126d67f53eb672aaff02996b3ef6` | `PauserTransferred(address indexed oldPauser, address indexed newPauser)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` — also emitted on `migrate()` after an upgrade |
| `0x0b5e7be615a67a819aff3f47c967d1535cead1b98db60fafdcbf22dcaa8fa5a9` | `NewMinter(address previousMinter, address newMinter)` — emitted by an `INttToken` (BURNING-mode token), not the manager |

### 1.4 WormholeTransceiver — emitter = the transceiver proxy

| topic0 | Event |
|--------|-------|
| `0x79376a0dc6cbfe6f6f8f89ad24c262a8c6233f8df181d3fe5abb2e2442e8c738` | `SendTransceiverMessage(uint16 recipientChain, (bytes32 sourceNttManagerAddress, bytes32 recipientNttManagerAddress, bytes nttManagerPayload, bytes transceiverPayload) message)` — source; status |
| `0xc3192e083c87c556db539f071d8a298869f487e951327b5616a6f85ae3da958e` | `RelayingInfo(uint8 relayingType, bytes32 refundAddress, uint256 deliveryPayment)` — source; status |
| `0xf6fc529540981400dc64edf649eb5e2e0eb5812a27f8c81bac2c1d317e71a5f0` | `ReceivedMessage(bytes32 digest, uint16 emitterChainId, bytes32 emitterAddress, uint64 sequence)` — destination; **maps the Wormhole key to the NTT digest** |
| `0xa559263ee060c7a2560843b3a064ff0376c9753ae3e2449b595a3b615d326466` | `SetWormholePeer(uint16 chainId, bytes32 peerContract)` — admin |
| `0xf557dbbb087662f52c815f6c7ee350628a37a51eae9608ff840d996b65f87475` | `ReceivedRelayedMessage(bytes32 digest, uint16 emitterChainId, bytes32 emitterAddress)` — v1.x only (standard-relayer delivery); removed in v2.0 |
| `0x528b18a533e892b5401d1fb63597275df9d2bb45b13e7695c3147cd07b9746c3` | `SetIsWormholeRelayingEnabled(uint16 chainId, bool isRelayingEnabled)` — v1.x admin |
| `0x0fe301480713b2c2072ee91b3bcfcbf2c0014f0447c89046f020f0f80727003c` | `SetIsSpecialRelayingEnabled(uint16 chainId, bool isRelayingEnabled)` — v1.x admin |
| `0x4add57d97a7bf5035340ea1212aeeb3d4d3887eb1faf3821a8224c3a6956a10c` | `SetIsWormholeEvmChain(uint16 chainId, bool isEvm)` — v1.x admin |

### 1.5 NTT message layout (inside `LogMessagePublished.payload` and `SendTransceiverMessage`)

Transceiver message: prefix `0x9945FF10` (4 B), source manager (32 B), recipient manager (32 B), manager payload (length-prefixed), transceiver payload (length-prefixed). Manager payload (`NttManagerMessage`): `id` (32 B = the sequence), `sender` (32 B), payload (length-prefixed). Token payload (`NativeTokenTransfer`): prefix `0x994E5454` ("\x99NTT"), `decimals` (1 B), `amount` (8 B, trimmed to at most 8 decimals), `sourceToken` (32 B), `to` (32 B), `toChain` (2 B), optional additional payload.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 NttManager

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x961b94d0` | `transfer(uint256 amount, uint16 recipientChain, bytes32 recipient)` | Payable (transceiver quote). Source. |
| `0xb293f97f` | `transfer(uint256 amount, uint16 recipientChain, bytes32 recipient, bytes32 refundAddress, bool shouldQueue, bytes encodedInstructions)` | Payable. Source (the Robinhood sample used it). |
| `0x97c35146` | `completeOutboundQueuedTransfer(uint64 queueSequence)` | Sends a queued transfer. |
| `0xf7514fbc` | `cancelOutboundQueuedTransfer(uint64 queueSequence)` | Refund path; emits `OutboundTransferCancelled`. |
| `0x8413bcba` | `completeInboundQueuedTransfer(bytes32 digest)` | Releases a queued inbound transfer. |
| `0x9d782454` | `attestationReceived(uint16 sourceChainId, bytes32 sourceNttManagerAddress, (bytes32 id, bytes32 sender, bytes payload) payload)` | Called by a transceiver. |
| `0xda4856a1` | `executeMsg(uint16 sourceChainId, bytes32 sourceNttManagerAddress, (bytes32 id, bytes32 sender, bytes payload) message)` | Fallback execution after threshold. |
| `0x7c918634` | `setPeer(uint16 peerChainId, bytes32 peerContract, uint8 decimals, uint256 inboundLimit)` | `onlyOwner`; emits `PeerUpdated`. **Admin.** |
| `0x19017175` | `setOutboundLimit(uint256 limit)` | `onlyOwner`. **Admin.** |
| `0x186ce612` | `setInboundLimit(uint256 limit, uint16 chainId)` | `onlyOwner`. **Admin.** |
| `0xe5a98603` | `setThreshold(uint8 threshold)` | `onlyOwner`. **Admin.** |
| `0x203e4a9b` | `setTransceiver(address transceiver)` | `onlyOwner`; emits `TransceiverAdded`. **Admin.** |
| `0x9f86029c` | `removeTransceiver(address transceiver)` | `onlyOwner`. **Admin.** |
| `0x0900f010` | `upgrade(address newImplementation)` | `onlyOwner`; emits `Upgraded`. **Admin.** |
| `0x8456cb59` | `pause()` | Owner or pauser; emits `Paused`. |
| `0x3f4ba83a` | `unpause()` | Owner; emits `NotPaused`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | **Admin.** |
| `0x036de8af` | `transferPauserCapability(address newPauser)` | **Admin.** |
| `0xfc0c546a` | `token()` | View — the managed token. |
| `0x4b4fd03b` | `getMode()` | View — 0 = LOCKING, 1 = BURNING. |
| `0xc128d170` | `getPeer(uint16 chainId_)` | View — `(bytes32 peerAddress, uint8 tokenDecimals)`. |
| `0xb4d591bb` | `getTransceivers()` | View. |
| `0xe75235b8` | `getThreshold()` | View. |
| `0x23d75e31` | `nextMessageSequence()` | View. |
| `0x396c16b7` | `isMessageExecuted(bytes32 digest)` | View. |
| `0xf5cfec18` | `getCurrentOutboundCapacity()` | View. |
| `0x02717250` | `getCurrentInboundCapacity(uint16 chainId)` | View. |
| `0x9057412d` | `quoteDeliveryPrice(uint16 recipientChain, bytes transceiverInstructions)` | View. |

### 2.2 WormholeTransceiver

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf953cec7` | `receiveMessage(bytes encodedMessage)` | Destination entry (VAA); emits `ReceivedMessage`. |
| `0x529dca32` | `receiveWormholeMessages(bytes payload, bytes[] additionalMessages, bytes32 sourceAddress, uint16 sourceChain, bytes32 deliveryHash)` | Standard-relayer delivery (v1.x). |
| `0x7ab56403` | `setWormholePeer(uint16 chainId, bytes32 peerContract)` | **Admin.** |
| `0x935dec07` | `getWormholePeer(uint16 chainId)` | View. |
| `0x694977d7` | `getNttManagerToken()` | View. |
| `0xd8d28418` | `getNttManagerOwner()` | View. |
| `0xa0926b2a` | `getTransceiverType()` | View — `"wormhole"`. |

### 2.3 NTT with Executor helpers

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x39bb39eb` | `transfer(address nttManager, uint256 amount, uint16 recipientChain, bytes32 recipientAddress, bytes32 refundAddress, bytes encodedInstructions, (uint256 value, address refundAddress, bytes signedQuote, bytes instructions) executorArgs, (uint16 dbps, address payee) feeArgs)` | NttManagerWithExecutor v1 |
| `0xbe2fa910` | `transferETH(address nttManager, uint256 amount, uint16 recipientChain, bytes32 recipientAddress, bytes32 refundAddress, bytes encodedInstructions, (uint256 value, address refundAddress, bytes signedQuote, bytes instructions) executorArgs, (uint16 dbps, address payee) feeArgs)` | v1 source; not found in the Ethereum v1 bytecode |
| `0xce972e0e` | `transfer(address nttManager, uint256 amount, uint16 recipientChain, bytes32 recipientAddress, bytes32 refundAddress, bytes encodedInstructions, (uint256 value, address refundAddress, bytes signedQuote, bytes instructions) executorArgs, (uint256 transferTokenFee, uint256 nativeTokenFee, address payee) feeArgs)` | NttManagerWithExecutor v2 |
| `0xe3b1fb0b` | `transferETH(address nttManager, uint256 amount, uint16 recipientChain, bytes32 recipientAddress, bytes32 refundAddress, bytes encodedInstructions, (uint256 value, address refundAddress, bytes signedQuote, bytes instructions) executorArgs, (uint256 transferTokenFee, uint256 nativeTokenFee, address payee) feeArgs)` | v2 |

The helpers emit no event; the manager's `TransferSent` and the Executor's `RequestForExecution` (`requestBytes` = `ERN1` + source chain + source manager + message id) are the logs ([relayer.md](relayer.md)).

---

## 3. Addresses — major NTT tokens (managers per chain)

Managers from the Wormholescan NTT API, confirmed on chain with `token()` (token column) and `getMode()` (L = LOCKING, B = BURNING). "Window" = `TransferSent` / `TransferRedeemed(digest)` count at that manager in the pinned window. A blank chain means no manager listed there.

| Token | Chain | NttManager | Mode | Token address | Window sent / redeemed |
|-------|-------|------------|------|---------------|------------------------|
| **W** (Wormhole) | Ethereum | `0xc072B1AEf336eDde59A049699Ef4e8Fa9D594A48` | B | `0xB0fFa8000886e57F86dd5264b9582b2Ad87b2b91` | 0 / 0 (1 `InboundTransferQueued`) |
| W | Arbitrum | `0x5333d0AcA64a450Add6FeF76D6D1375F726CB484` | B | `0xB0fFa8000886e57F86dd5264b9582b2Ad87b2b91` | 3 / 0 |
| W | Base | `0x5333d0AcA64a450Add6FeF76D6D1375F726CB484` | B | `0xB0fFa8000886e57F86dd5264b9582b2Ad87b2b91` | 1 / 3 |
| W | Optimism | `0x1a4f1a790f23ffb9772966cb6f36dcd658033e13` | B | `0xB0fFa8000886e57F86dd5264b9582b2Ad87b2b91` | 1 / 0 |
| **wstETH** (Lido) | Ethereum | `0xb948a93827d68a82F6513Ad178964Da487fe2BD9` | L | `0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0` | 0 / 0 |
| wstETH | BNB | `0x6981F5621691CBfE3DdD524dE71076b79F0A0278` | B | `0x26c5e01524d2E6280A48F2c50fF6De7e52E9611C` | 0 / 0 |
| **USDS** (Sky, to Solana) | Ethereum | `0x7d4958454a3f520bDA8be764d06591B054B0bf33` | L | `0xdC035D45d973E3EC169d2276DDab16f1e407384F` | 0 / 0 |
| **ETHFI** | Ethereum | `0x344169Cc4abE9459e77bD99D13AA8589b55b6174` | L | `0xFe0c30065B384F05761f15d0CC899D4F9F9Cc0eB` | 0 / 0 |
| ETHFI | Arbitrum | `0x90A82462258F79780498151EF6f663f1D4BE4E3b` | B | `0x7189fb5B6504bbfF6a852B13B7B82a3c118fDc27` | 0 / 0 |
| ETHFI | Base | `0xE87797A1aFb329216811dfA22C87380128CA17d8` | B | `0x6C240DDA6b5c336DF09A4D011139beAAa1eA2Aa2` | 0 / 0 |
| **clBTC** | Ethereum | `0x64E4b81023621CB08f5aC305c2dD6eDaaD717834` | B | `0xE7ae30C03395D66F30A26C49c91edAe151747911` | 0 / 0 |
| clBTC | Arbitrum | `0xFc7f31805ec6F1884AbfD0ED72AB7DA752512DAe` | B | `0x1792865D493FE4DFdD504010D3c0f6da11E8046D` | 0 / 0 |
| clBTC | Optimism | `0x40bb93251cc4691812B5C298dF0c359cBF058424` | B | `0x1792865D493FE4DFdD504010D3c0f6da11E8046D` | 0 / 0 |
| clBTC | Base | `0x429410525068b694160d686Eacf72Ce12B665991` | L | `0x8d2757EA27AaBf172DA4CCa4e5474c76016e3dC5` | 0 / 0 |
| **AVAIL** | Ethereum | `0x2E65520ff593b583A2e5895174eF7F40F78a90BD` | L | `0xEeB4d8400AEefafC1B2953e0094134A887C76Bd8` | 8 / 3 |
| AVAIL | Base | `0x4b3d190ca333a1414376Dd565ACBa58350A36d67` | B | `0xd89d90d26B48940FA8F58385Fe84625d468E057a` | 10 / 11 |
| AVAIL | BNB | `0xD7c5A24b84546A08c49b9F52457754Fa235a1A1c` | B | `0x39702843A6733932ec7CE0dde404e5A6DBd8C989` | 13 / 17 |
| **WCT** (WalletConnect) | Ethereum, Optimism, Base | `0x164Be303480f542336bE0bBe0432A13b85e6FD1b` (same on all three) | B | `0xeF4461891DfB3AC8572cCf7C794664A8DD927945` | ETH 1 / 0, OP 0 / 1, Base 0 / 0 |
| **FOLKS** | Ethereum, Base, Arbitrum, Polygon, BNB, Avalanche | `0xd15274c3910600a8246C86a198DE18618Cd47401` (same on all six) | B | `0xFF7F8F301F7A706E3CfD3D2275f5dc0b9EE8009B` | ETH 0 / 0, Base 10 / 6, ARB 4 / 6, BNB 22 / 24, AVAX 21 / 20 |
| **MUSD** (Mezo USD) | Ethereum | `0x5293158bf7a81ED05418DA497a80F7e6Dbf4477E` | B | `0xdD468A1DDc392dcdbEf6db6e34E89AA338F9F186` | 0 / 0 |
| **osETH** (StakeWise) | Ethereum | `0x896B78FD7e465Fb22e80c34FF8F1c5f62fa2C009` | L | `0xf1C9acDc66974dFB6dEcB12aA385b9cD01190E38` | 0 / 0 |
| osETH | Arbitrum | `0x485F6Ac6a3B97690910C1546842FfE0629582aD3` | B | `0xf7d4e7273E5015C96728A6b02f31C505eE184603` | 0 / 0 |
| **XBG** | Ethereum | `0xa4489105efa4b029485d6bd3A4f52131baAE4B1B` | L | `0xEaE00D6F9B16Deb1BD584c7965e4c7d762f178a1` | 0 / 0 |
| XBG | Arbitrum | `0x7135766f279b9a50f7a7199cff1be284521a0409` | B | `0x93FA0B88C0C78e45980Fa74cdd87469311b7B3E4` | 0 / 3 |
| **GEOD** | Polygon | `0x2006B44684b2A579466fC04FAbC5A535946bC7AB` | L | `0xAC0F66379A6d7801D7726d5a943356A172549Adb` | 15 / 43 |
| **BORG** (SwissBorg) | Ethereum | `0x66a28B080918184851774a89aB94850a41f6a1e5` | L | `0x64d0f55Cd8C7133a9D7102b13987235F486F2224` | 2 / 4 |
| **BID** | Base, BNB | `0xC5103069C3a0b52cddea0f565a4589d54452114C` (same on both) | B | `0xa1832f7F4e534aE557f9B5AB76dE54B1873e498B` | Base 5 / 0, BNB 0 / 5 |
| **CLO** | BNB | `0x68A91E65Fce074A15c862F97E1CE977de2A72255` | B | `0x81D3A238b02827F62B9f390f947D36d4A5bf89D2` | 0 / 57 |
| **M** (M^0) | Ethereum, Arbitrum, Optimism, Base | `0xD925C84b55E4e44a53749fF5F2a5A13F63D128fd` (same on all four) | L on ETH, B elsewhere (per Wormholescan) | `0x866A2BF4E572CbcF37D5071A7a58503Bfb36be1b` | 0 on all four |

`token()` of the M manager returned the M token on Optimism and reverted on Ethereum, Arbitrum and Base (M^0 runs its own NTT-derived "Portal"; its interface differs, unverified beyond Optimism). The address has code on all four chains (225 B EIP-1967 proxy; implementations of 21,196–24,561 B).

### 3.1 Other managers active in the window (measured, token identified with `token()` and `symbol()`)

| Chain | NttManager | Token (symbol) | Mode | Sent / redeemed |
|-------|------------|----------------|------|-----------------|
| Ethereum | `0x6912d024e2b88136c5a586e77b092199963b6083` | `0xdef1b2d939edc0e4d35806c59b3166f790175afe` (INX) | L | 21 / 9 |
| Ethereum | `0xf432b2564cc0e233482a1f2af0eda4832cf435cd` | `0xe7e7e741c23a4767831a56a8c99f522c5ac1e7e7` (EV); same manager on ARB and BNB | B | 6 / 1 |
| Ethereum | `0x755d0e80b038d10a2e44f128276f3f0a8428c4ee` | `0x1f9840a85d5af5bf1d1762f925bdaddc4201f984` (UNI) | L | 5 / 0 |
| Ethereum | `0x447b2c7485a3d6813f8197e605b10bccd8dd8398` | `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` (USDC) | L | 2 / 0 |
| Ethereum | `0xafcfd97d6bf7397f03e4e366ba704dd0b5d9f3b0` | `0xdac17f958d2ee523a2206206994597c13d831ec7` (USDT) | L | 2 / 0 |
| Ethereum | `0x076a2fdfff9c45479c9ca7ae2ae063d2a3795d1c` | `0x140007c65535aa9c3801ea3bbd3f83c378c7f457` (𝕏) — peer of the Robinhood manager | L | 1 / 3 |
| Polygon | `0x8469783edd405210a5438a4568ea4d0dbcc9cf7f` | not read on Polygon (the same address manages BRZ on Base and Arbitrum) | — | 5 / 0 |
| Avalanche | `0x45f55b46689402583073ff227b6ac20520052a24` | `0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7` (WAVAX) | L | 3 / 1 |

---

## 4. Addresses — Robinhood Chain and the Wormhole-run NTT infrastructure

### 4.1 Robinhood Chain (chain ID 4663, Wormhole id 72)

| NttManager | Token (symbol) | Mode | Window sent / redeemed | Note |
|------------|----------------|------|------------------------|------|
| `0x0b6836942755df095721e0aee40145b36be09b55` | `0x1f8be8355dcce39e390bb74b70d70bba514fdeb9` (𝕏) | B | 3 / 1 | `getPeer(2)` = Ethereum manager `0x076a2fdfff9c45479c9ca7ae2ae063d2a3795d1c`; transceiver `0x352874cd039bd2f8e23ed203941c684912009d43` (`getTransceiverType()` = `"wormhole"`); owner `0x1edd9019087a09251bea85d9245712585f14b1fd` |
| `0x45f55b46689402583073ff227b6ac20520052a24` | `0x39dbed3a2bd333467115de45665cc57f813c4571` (PONS) | L | 1 / 0 | sent through the Executor (`RequestForExecution` in the same transaction) |
| `0x72e4fcaffff5b64811a7a49fe67cfb30d64c798f` | `0x51a5853ba953f092c9466516d768ecf056dbc62e` (MOS) | B | 0 / 1 | |

These three are measured, not listed: the Wormholescan token list has no `robinhood` platform for any of the tokens checked. The Core on Robinhood carried 4 messages in the window, all from NTT transceivers.

### 4.2 NTT-with-Executor and receive helpers (Executor registry)

| Chain | NttManagerWithExecutor v1 | NttManagerWithExecutor v2 | Multi-receive-with-gas-drop-off |
|-------|---------------------------|---------------------------|---------------------------------|
| Ethereum | `0xD2D9c936165a85F27a5a7e07aFb974D022B89463` | `0xC079bFA54F348199bA51B2717595fE24e96f1542` | `0xe3cc16Cffa085C78e5D8144C74Fa97e4Fe53d68d` |
| Base | `0x83216747fC21b86173D800E2960c0D5395de0F30` | `0x27db1967D469D89318B7119Ced5609f327095de4` | `0xe3cc16Cffa085C78e5D8144C74Fa97e4Fe53d68d` |
| Arbitrum One | `0x0Af42A597b0C201D4dcf450DcD0c06d55ddC1C77` | `0x5029a23E0EE11f6c9120EAb7eB48a94a49907EC4` | `0xe3cc16Cffa085C78e5D8144C74Fa97e4Fe53d68d` |
| Optimism | `0x85C0129bE5226C9F0Cf4e419D2fefc1c3FCa25cF` | `0xC25396Ce2F6FBE6996374a5527c636C71AD5a757` | `0xe3cc16Cffa085C78e5D8144C74Fa97e4Fe53d68d` |
| Polygon PoS | `0x6762157b73941e36cEd0AEf54614DdE545d0F990` | `0x9d165221c3c68868D15B154c5Aa66C32e044Eb4b` | `0xe3cc16Cffa085C78e5D8144C74Fa97e4Fe53d68d` |
| BNB Smart Chain | `0x39B57Dd9908F8be02CfeE283b67eA1303Bc29fe1` | `0x83f5c7b03BBbE20FE2e39312b957D86dc7C3Dee2` | `0x0E4Eaf9c5c74bec4Cb651394db4847f77700e175` |
| Avalanche C-Chain | `0x4e9Af03fbf1aa2b79A2D4babD3e22e09f18Bb8EE` | `0xf1Aa9693265E0Ba892C4a7AE77591424eEEd5cE9` | `0xe3cc16Cffa085C78e5D8144C74Fa97e4Fe53d68d` |
| **Robinhood Chain** | — | `0x0AdA5f1289Ee5EC07e397Ee86dB6bc861ce0A728` | `0x0E4Eaf9c5c74bec4Cb651394db4847f77700e175` |

All have code (v1 3,559 B, v2 4,163 B, receive helpers 862 B). The Ethereum v1 helper contains `0x39bb39eb`; the v2 helper contains `0xce972e0e` and `0xe3b1fb0b`. Ethereum also has a multi-token NTT helper (`0x03dB430D830601DB368991eE55DAa9A708df7912`, 4,980 B).

---

## 5. Cross-chain summary

| Chain | EVM id | Wormhole id | NTT managers active in the window | `TransferSent` / `TransferRedeemed(digest)` | NTT-with-Executor v2 |
|-------|--------|-------------|-----------------------------------|----------------------------------------------|----------------------|
| Ethereum | 1 | 2 | 21 (+1 queue-only) | 60 / 36 | ✅ |
| Base | 8453 | 30 | 14 | 34 / 41 | ✅ |
| Arbitrum One | 42161 | 23 | 9 | 15 / 21 | ✅ |
| Optimism | 10 | 24 | 2 | 1 / 1 | ✅ |
| Polygon PoS | 137 | 5 | 7 | 24 / 46 | ✅ |
| BNB Smart Chain | 56 | 4 | 14 | 56 / 113 | ✅ |
| Avalanche C-Chain | 43114 | 6 | 2 | 24 / 21 | ✅ |
| **Robinhood Chain** | 4663 | 72 | 3 | 4 / 2 | ✅ |

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **NttManager** | EIP-1967 proxy (`ERC1967Proxy`; 209 B, also 207, 203 and 133 B builds measured); upgrade logic in the implementation (`upgrade(address)` → `_upgrade` → `migrate()`) | Implementation slot populated on every manager read (implementations 23,660–24,529 B) | `owner()` of the manager: an issuer multisig, a Guardian Governance contract (W on ETH, ARB, Base, OP), or unknown |
| **WormholeTransceiver** | EIP-1967 proxy | Implementation slot populated (for example ETH `0x945c21d00ff8d4a8800e8919b2d70263a36a8f51` → 13,533 B; Robinhood `0x352874cd039bd2f8e23ed203941c684912009d43` → 9,694 B) | The manager's owner (`upgrade(address)` on the transceiver) |
| NTT-with-Executor helpers | Not proxies | Implementation slot 0 | Immutable |

Watch `Upgraded` (`0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`) and `OwnershipTransferred` on every manager and transceiver you monitor.

---

## 7. Detection invariants & gotchas

1. **There is no NTT registry on chain.** Find managers by the topics, not by address: any contract that emits `TransferSent` (`0xe54e51e42099622516fa3b48e9733581c9dbdcb771cafb093f745a0532a35982`) and `TransferRedeemed(bytes32)` (`0x504e6efe18ab9eed10dc6501a417f5b12a2f7f2b1593aed9b89f9bce3cf29a91`) is an NTT manager. Confirm with `token()` and `getMode()`.
2. **Two log layouts share one topic0.** `TransferSent` has `recipient` and `refundAddress` indexed in v1.2+ builds and unindexed in v1.0 builds. Measured unindexed layout: AVAIL (ETH, BNB), BORG (ETH), W (ARB, Base, OP), L3 (Base). Decode by topic count (3 vs 1). In the window, every manager with the unindexed layout also emitted **no** `TransferSent(bytes32 digest)`; for those, link by the Wormhole key and `ReceivedMessage`.
3. **Value movement.** LOCKING: `Transfer(user → manager)` stays in the manager (escrow). BURNING: `Transfer(user → manager)` then `Transfer(manager → 0x0)` (sample Robinhood `0xd70f7def815e10b1f9c044a858c04bf6653232acc29839593bef2c577d15e4c5`). Destination: `Transfer(manager → recipient)` (unlock, sample Ethereum `0x357bb46f88dd16f81eaa55b0728044b23832281686faad75ff6b476f092c1cdf`) or `Transfer(0x0 → recipient)` (mint, sample Ethereum `0x5c5744ff8ee150733861659a2fabbe4e146a235c572959cf9a9e83489445ccd6`).
4. **Amounts are trimmed** to at most 8 decimals in the message; `TransferSent.amount` is the untrimmed value; dust below the trim stays with the sender.
5. **`fee` in `TransferSent` is the native-coin delivery quote**, not a token fee. Referrer fees of the NTT-with-Executor helpers move as separate token transfers to the `payee`.
6. **Address reuse across chains is common.** The same address is a different contract on different chains: `0x8b870c6e13e4889a0293cfefc8cdb4b0a03e8ddb` is the INX manager on BNB and the cbDOGE manager on Base; `0x45f55b46689402583073ff227b6ac20520052a24` is the INX token on BNB, the WAVAX manager on Avalanche and the PONS manager on Robinhood. Always key on `(chain, address)`.
7. **The relayer path changes the Core `sender`.** With the Executor, the transceiver publishes (`sender` = transceiver) and the Executor logs `RequestForExecution`. In legacy standard-relayer mode, the Wormhole Relayer publishes (`sender` = relayer) and the destination transceiver emits `ReceivedRelayedMessage`.
8. **`PeerUpdated` is the key admin event.** A wrong peer lets a foreign contract mint or unlock. Also watch `TransceiverAdded`, `ThresholdChanged`, the limit updates, `Paused` and `Upgraded`.
9. **Rate-limit queues are rare.** In the window: 1 `InboundTransferQueued` (W manager, Ethereum), 0 outbound queues or cancellations on the seven chains scanned.
10. **Wormholescan and the chain disagree for W on Base and Optimism.** Wormholescan lists `0x011e5330c4A988B645C5e097179EaAdaD2634B09` as the W peer there; on chain its `token()` is `0x1e69934bf7352fca8a351acd4adf8e7985366e73`, not W. The managers that carried W traffic in the window are the ones in §3.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== NttManager topics (chain-agnostic) =====
TOPIC_NTT_TRANSFER_SENT       = '\xe54e51e42099622516fa3b48e9733581c9dbdcb771cafb093f745a0532a35982'   -- 3 topics (v1.2+) or 1 topic (v1.0)
TOPIC_NTT_TRANSFER_SENT_DIGEST= '\x3e6ae56314c6da8b461d872f41c6d0bb69317b9d0232805aaccfa45df1a16fa0'
TOPIC_NTT_TRANSFER_REDEEMED   = '\x504e6efe18ab9eed10dc6501a417f5b12a2f7f2b1593aed9b89f9bce3cf29a91'
TOPIC_NTT_OUTBOUND_CANCELLED  = '\xf80e572ae1b63e2449629b6c7d783add85c36473926f216077f17ee002bcfd07'
TOPIC_NTT_MESSAGE_ATTESTED    = '\x35a2101eaac94b493e0dfca061f9a7f087913fde8678e7cde0aca9897edba0e5'
TOPIC_NTT_OUTBOUND_QUEUED     = '\x69add1952a6a6b9cb86f04d05f0cb605cbb469a50ae916139d34495a9991481f'
TOPIC_NTT_OUTBOUND_RATE_LIMIT = '\xf33512b84e24a49905c26c6991942fc5a9652411769fc1e448f967cdb049f08a'
TOPIC_NTT_INBOUND_QUEUED      = '\x7f63c9251d82a933210c2b6d0b0f116252c3c116788120e64e8e8215df6f3162'
TOPIC_NTT_PEER_UPDATED        = '\x1456404e7f41f35c3daac941bb50bad417a66275c3040061b4287d787719599d'
TOPIC_NTT_OUTBOUND_LIMIT_UPD  = '\x7e3b0fc388be9d36273f66210aed83be975df3a9adfffa4c734033f498f362cd'
TOPIC_NTT_INBOUND_LIMIT_UPD   = '\x739ed886fd81a3ddc9f4b327ab69152e513cd45b26fda0c73660eaca8e119301'
TOPIC_NTT_THRESHOLD_CHANGED   = '\x2a855b929b9a53c6fb5b5ed248b27e502b709c088e036a5aa17620c8fc5085a9'
TOPIC_NTT_TRANSCEIVER_ADDED   = '\xf05962b5774c658e85ed80c91a75af9d66d2af2253dda480f90bce78aff5eda5'
TOPIC_NTT_PAUSED              = '\x0e2fb031ee032dc02d8011dc50b816eb450cf856abd8261680dac74f72165bd2'
TOPIC_NTT_NOT_PAUSED          = '\xe11c2112add17fb763d3bd59f63b10429c3e11373da4fb8ef6725107a2fdc4b0'
TOPIC_OWNERSHIP_TRANSFERRED   = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== WormholeTransceiver topics =====
TOPIC_NTT_RECEIVED_MESSAGE    = '\xf6fc529540981400dc64edf649eb5e2e0eb5812a27f8c81bac2c1d317e71a5f0'
TOPIC_NTT_SEND_TRANSCEIVER_MSG= '\x79376a0dc6cbfe6f6f8f89ad24c262a8c6233f8df181d3fe5abb2e2442e8c738'
TOPIC_NTT_RELAYING_INFO       = '\xc3192e083c87c556db539f071d8a298869f487e951327b5616a6f85ae3da958e'
TOPIC_NTT_SET_WORMHOLE_PEER   = '\xa559263ee060c7a2560843b3a064ff0376c9753ae3e2449b595a3b615d326466'
TOPIC_NTT_RECEIVED_RELAYED    = '\xf557dbbb087662f52c815f6c7ee350628a37a51eae9608ff840d996b65f87475'

-- ===== Selectors =====
SEL_NTT_TRANSFER              = '\x961b94d0'
SEL_NTT_TRANSFER_FULL         = '\xb293f97f'
SEL_NTT_CANCEL_OUTBOUND       = '\xf7514fbc'
SEL_NTT_COMPLETE_INBOUND      = '\x8413bcba'
SEL_NTT_SET_PEER              = '\x7c918634'
SEL_NTT_UPGRADE               = '\x0900f010'
SEL_NTT_TOKEN                 = '\xfc0c546a'
SEL_NTT_GET_MODE              = '\x4b4fd03b'
SEL_NTT_RECEIVE_MESSAGE       = '\xf953cec7'
SEL_NTT_EXEC_TRANSFER_V1      = '\x39bb39eb'
SEL_NTT_EXEC_TRANSFER_V2      = '\xce972e0e'

-- ===== W managers =====
ETH_NTT_MANAGER_W             = '\xc072b1aef336edde59a049699ef4e8fa9d594a48'
ARB_NTT_MANAGER_W             = '\x5333d0aca64a450add6fef76d6d1375f726cb484'
BASE_NTT_MANAGER_W            = '\x5333d0aca64a450add6fef76d6d1375f726cb484'
OP_NTT_MANAGER_W              = '\x1a4f1a790f23ffb9772966cb6f36dcd658033e13'
-- ===== other major managers =====
ETH_NTT_MANAGER_WSTETH        = '\xb948a93827d68a82f6513ad178964da487fe2bd9'
BNB_NTT_MANAGER_WSTETH        = '\x6981f5621691cbfe3ddd524de71076b79f0a0278'
ETH_NTT_MANAGER_USDS          = '\x7d4958454a3f520bda8be764d06591b054b0bf33'
ETH_NTT_MANAGER_ETHFI         = '\x344169cc4abe9459e77bd99d13aa8589b55b6174'
ETH_NTT_MANAGER_CLBTC         = '\x64e4b81023621cb08f5ac305c2dd6edaad717834'
ETH_NTT_MANAGER_AVAIL         = '\x2e65520ff593b583a2e5895174ef7f40f78a90bd'
BASE_NTT_MANAGER_AVAIL        = '\x4b3d190ca333a1414376dd565acba58350a36d67'
BNB_NTT_MANAGER_AVAIL         = '\xd7c5a24b84546a08c49b9f52457754fa235a1a1c'
ETH_NTT_MANAGER_WCT           = '\x164be303480f542336be0bbe0432a13b85e6fd1b'
ETH_NTT_MANAGER_FOLKS         = '\xd15274c3910600a8246c86a198de18618cd47401'
POLY_NTT_MANAGER_GEOD         = '\x2006b44684b2a579466fc04fabc5a535946bc7ab'
BNB_NTT_MANAGER_CLO           = '\x68a91e65fce074a15c862f97e1ce977de2a72255'
ETH_NTT_MANAGER_INX           = '\x6912d024e2b88136c5a586e77b092199963b6083'
RH_NTT_MANAGER_X              = '\x0b6836942755df095721e0aee40145b36be09b55'
RH_NTT_MANAGER_PONS           = '\x45f55b46689402583073ff227b6ac20520052a24'
RH_NTT_MANAGER_MOS            = '\x72e4fcaffff5b64811a7a49fe67cfb30d64c798f'
-- ===== NTT with Executor v2 helpers =====
ETH_NTT_WITH_EXECUTOR_V2      = '\xc079bfa54f348199ba51b2717595fe24e96f1542'
BASE_NTT_WITH_EXECUTOR_V2     = '\x27db1967d469d89318b7119ced5609f327095de4'
ARB_NTT_WITH_EXECUTOR_V2      = '\x5029a23e0ee11f6c9120eab7eb48a94a49907ec4'
OP_NTT_WITH_EXECUTOR_V2       = '\xc25396ce2f6fbe6996374a5527c636c71ad5a757'
POLY_NTT_WITH_EXECUTOR_V2     = '\x9d165221c3c68868d15b154c5aa66c32e044eb4b'
BNB_NTT_WITH_EXECUTOR_V2      = '\x83f5c7b03bbbe20fe2e39312b957d86dc7c3dee2'
AVAX_NTT_WITH_EXECUTOR_V2     = '\xf1aa9693265e0ba892c4a7ae77591424eeed5ce9'
RH_NTT_WITH_EXECUTOR_V2       = '\x0ada5f1289ee5ec07e397ee86db6bc861ce0a728'
```

---

## 9. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `evm/src/interfaces/INttManager.sol`, `IManagerBase.sol`, `IRateLimiterEvents.sol`, `IWormholeTransceiver.sol`, `IWormholeTransceiverState.sol`, `libraries/PausableUpgradeable.sol`, `libraries/external/OwnableUpgradeable.sol`, `libraries/external/Initializable.sol` and `interfaces/INttToken.sol` (`main`), compared with the tags `v1.0.0+evm`, `v1.2.0+evm` and `v2.0.0+evm` (indexing of `TransferSent`, digest event, limit events, standard-relayer events). The transceiver topics match the topic0 values written in the source comments. Helper selectors from `example-ntt-with-executor-evm/src/v1` and `src/v2`, confirmed in the Ethereum helper bytecode.
- **Addresses:** managers from the Wormholescan NTT API (`token-list`, then `/ntt/token/{chain}/{token}` for the top tokens by value transferred); helpers from the Executor deployment registry (`w7/ntt-manager/*`). Every manager in §3 and §4.1 was read with `token()` and `getMode()`; owners of the W managers with `owner()` (ETH → `0x23Fea5514DFC9821479fBE18BA1D7e1A61f6FfCf`, ARB → `0x36CF4c88FA548c6Ad9fcDc696e1c27Bb3306163F`, Base → `0x838a95B6a3E06B6f11C437e22f3C7561a6ec40F1`, OP → `0x0E09a3081837ff23D2e59B179E0Bc48A349Afbd8`: the Guardian Governance contracts). wstETH on Ethereum: `getTransceivers()` = Wormhole `0xA1ACC1e6edaB281Febd91E3515093F1DE81F25c0` and Axelar `0x723AEAD29acee7E9281C32D11eA4ed0070c41B13`, `getThreshold()` = 2.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):** `TransferSent` (6-field) totals: Ethereum 60, Base 34, Arbitrum 15, Optimism 1, Polygon 24, BNB 56, Avalanche 24, Robinhood 4. `TransferRedeemed(digest)`: Ethereum 36, Base 41, Arbitrum 21, Optimism 1, Polygon 46, BNB 113, Avalanche 21, Robinhood 2. `TransferSent(digest)`: Ethereum 50, Base 21, Arbitrum 12, Optimism 0, BNB 43, Avalanche 24, Robinhood 4 (Polygon not counted). Per-manager counts in §3. The manager list in §3.1 is a measured floor for one 12-hour window, not a complete list.
- **Samples:** Ethereum send `0xb583bb788c8bd3befa12599484618f5b18684b462079d0d2241a251e2caf293d` (INX: token into the manager, `LogMessagePublished` from transceiver `0x945c21d00ff8d4a8800e8919b2d70263a36a8f51`, `RelayingInfo`, `SendTransceiverMessage`, both `TransferSent`); Ethereum receive `0x357bb46f88dd16f81eaa55b0728044b23832281686faad75ff6b476f092c1cdf`; Robinhood send `0xd70f7def815e10b1f9c044a858c04bf6653232acc29839593bef2c577d15e4c5`; Base relayer-mode send `0x12fedaa0d2279d2a37a0f2a0e691d3586f8e1cc4689fefa11765f28d32df5a52`.

Authoritative sources:
- [wormhole-foundation/native-token-transfers](https://github.com/wormhole-foundation/native-token-transfers) — `evm/src/` (main and tags `v1.0.0+evm`, `v1.2.0+evm`, `v2.0.0+evm`)
- [wormholelabs-xyz/example-ntt-with-executor-evm](https://github.com/wormholelabs-xyz/example-ntt-with-executor-evm)
- [Wormholescan API](https://wormholescan.io/#/developers/api-doc) — `native-token-transfer/token-list`, `ntt/token/{chain}/{token}`
- Docs — [Query NTT data with Wormholescan](https://wormhole.com/docs/products/messaging/guides/wormholescan-api/) · [Integrate NTT with Executor](https://wormhole.com/docs/protocol/infrastructure-guides/ntt-executor/) · [NTT transceivers (EVM)](https://wormhole.com/docs/products/token-transfers/native-token-transfers/reference/transceivers/evm/) · [Contract addresses (Guardian Governance)](https://wormhole.com/docs/reference/contract-addresses/)
- Explorers — [Etherscan W NttManager](https://etherscan.io/address/0xc072b1aef336edde59a049699ef4e8fa9d594a48) · [Robinhood Chain Blockscout NttManager](https://robinhoodchain.blockscout.com/address/0x0b6836942755df095721e0aee40145b36be09b55)
