# Chainlink VRF (v1, v2, v2.5) — Topics, Selectors, Addresses

**Status:** verified 2026-05-29. Topic0/selectors computed locally (keccak) from canonical `smartcontractkit/chainlink` interfaces; coordinator/wrapper addresses verified via `eth_getCode` (non-empty) on each chain's publicnode RPC.
**Scope:** Chainlink VRF on Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137). LINK token: [link-token.md](link-token.md).

VRF returns verifiable on-chain randomness. Three generations coexist:

| Version | Coordinator | Funding model | `subId` type | Status |
|---------|-------------|---------------|--------------|--------|
| **v1** | `VRFCoordinator` | Per-request, pay LINK via `transferAndCall` (no subscriptions) | n/a | **Deprecated 2024-11-29.** Historical only. |
| **v2** | `VRFCoordinatorV2` | Subscription (prepay LINK) **or** direct funding via `VRFV2Wrapper` | `uint64` | Legacy, still live |
| **v2.5** | `VRFCoordinatorV2_5` | Subscription **or** direct funding; payable in **native gas token OR LINK** (chosen per request via `extraArgs`) | `uint256` | Current |

Helpers: **`BlockhashStore`** / **`BatchBlockhashStore`** store historical blockhashes so the coordinator can verify proofs beyond the 256-block EVM window. **`VRFV2Wrapper`** / **`VRFV2PlusWrapper`** provide direct-funding (pay-per-request) without managing a subscription.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 VRF v1 (`VRFCoordinator`)

| topic0 | Event |
|--------|-------|
| `0x56bd374744a66d531874338def36c906e3a6cf31176eb1e9afd9f1de69725d51` | `RandomnessRequest(bytes32 keyHash, uint256 seed, bytes32 indexed jobID, address sender, uint256 fee, bytes32 requestID)` |
| `0xa2e7a402243ebda4a69ceeb3dfb682943b7a9b3ac66d6eefa8db65894009611c` | `RandomnessRequestFulfilled(bytes32 requestId, uint256 output)` |

### 1.2 VRF v2 (`VRFCoordinatorV2`)

| topic0 | Event |
|--------|-------|
| `0x63373d1c4696214b898952999c9aaec57dac1ee2723cec59bea6888f489a9772` | `RandomWordsRequested(bytes32 indexed keyHash, uint256 requestId, uint256 preSeed, uint64 indexed subId, uint16 minimumRequestConfirmations, uint32 callbackGasLimit, uint32 numWords, address indexed sender)` |
| `0x7dffc5ae5ee4e2e4df1651cf6ad329a73cebdb728f37ea0187b9b17e036756e4` | `RandomWordsFulfilled(uint256 indexed requestId, uint256 outputSeed, uint96 payment, bool success)` |
| `0x464722b4166576d3dcbba877b999bc35cf911f4eaf434b7eba68fa113951d0bf` | `SubscriptionCreated(uint64 indexed subId, address owner)` |
| `0xd39ec07f4e209f627a4c427971473820dc129761ba28de8906bd56f57101d4f8` | `SubscriptionFunded(uint64 indexed subId, uint256 oldBalance, uint256 newBalance)` |
| `0x43dc749a04ac8fb825cbd514f7c0e13f13bc6f2ee66043b76629d51776cff8e0` | `SubscriptionConsumerAdded(uint64 indexed subId, address consumer)` |
| `0x182bff9831466789164ca77075fffd84916d35a8180ba73c27e45634549b445b` | `SubscriptionConsumerRemoved(uint64 indexed subId, address consumer)` |
| `0xe8ed5b475a5b5987aa9165e8731bb78043f39eee32ec5a1169a89e27fcd49815` | `SubscriptionCanceled(uint64 indexed subId, address to, uint256 amount)` |
| `0xe729ae16526293f74ade739043022254f1489f616295a25bf72dfb4511ed73b8` | `ProvingKeyRegistered(bytes32 keyHash, address indexed oracle)` |
| `0xc21e3bd2e0b339d2848f0dd956947a88966c242c0c0c582a33137a5c1ceb5cb2` | `ConfigSet(uint16 minimumRequestConfirmations, uint32 maxGasLimit, uint32 stalenessSeconds, uint32 gasAfterPaymentCalculation, int256 fallbackWeiPerUnitLink, (uint32,uint32,uint32,uint32,uint32,uint24,uint24,uint24,uint24) feeConfig)` |

### 1.3 VRF v2.5 (`VRFCoordinatorV2_5`) — `subId` widened to `uint256`; native-or-LINK fields added

| topic0 | Event |
|--------|-------|
| `0xeb0e3652e0f44f417695e6e90f2f42c99b65cd7169074c5a654b16b9748c3a4e` | `RandomWordsRequested(bytes32 indexed keyHash, uint256 requestId, uint256 preSeed, uint256 indexed subId, uint16 minimumRequestConfirmations, uint32 callbackGasLimit, uint32 numWords, bytes extraArgs, address indexed sender)` |
| `0xaeb4b4786571e184246d39587f659abf0e26f41f6a3358692250382c0cdb47b7` | `RandomWordsFulfilled(uint256 indexed requestId, uint256 outputSeed, uint256 indexed subId, uint96 payment, bool nativePayment, bool success, bool onlyPremium)` |
| `0x1d3015d7ba850fa198dc7b1a3f5d42779313a681035f77c8c03764c61005518d` | `SubscriptionCreated(uint256 indexed subId, address owner)` |
| `0x1ced9348ff549fceab2ac57cd3a9de38edaaab274b725ee82c23e8fc8c4eec7a` | `SubscriptionFunded(uint256 indexed subId, uint256 oldBalance, uint256 newBalance)` |
| `0x7603b205d03651ee812f803fccde89f1012e545a9c99f0abfea9cedd0fd8e902` | `SubscriptionFundedWithNative(uint256 indexed subId, uint256 oldNativeBalance, uint256 newNativeBalance)` |
| `0x1e980d04aa7648e205713e5e8ea3808672ac163d10936d36f91b2c88ac1575e1` | `SubscriptionConsumerAdded(uint256 indexed subId, address consumer)` |
| `0x32158c6058347c1601b2d12bc696ac6901d8a9a9aa3ba10c27ab0a983e8425a7` | `SubscriptionConsumerRemoved(uint256 indexed subId, address consumer)` |
| `0x8c74ce8b8cf87f5eb001275c8be27eb34ea2b62bfab6814fcc62192bb63e81c4` | `SubscriptionCanceled(uint256 indexed subId, address to, uint256 amountLink, uint256 amountNative)` |
| `0x9b911b2c240bfbef3b6a8f7ed6ee321d1258bb2a3fe6becab52ac1cd3210afd3` | `ProvingKeyRegistered(bytes32 keyHash, uint64 maxGas)` |
| `0x2c6b6b12413678366b05b145c5f00745bdd00e739131ab5de82484a50c9d78b6` | `ConfigSet(uint16 minimumRequestConfirmations, uint32 maxGasLimit, uint32 stalenessSeconds, uint32 gasAfterPaymentCalculation, int256 fallbackWeiPerUnitLink, uint32 fulfillmentFlatFeeNativePPM, uint32 fulfillmentFlatFeeLinkDiscountPPM, uint8 nativePremiumPercentage, uint8 linkPremiumPercentage)` |

> v2 → v2.5 event differences that bite indexers: (a) `subId` goes `uint64`→`uint256` so **every topic0 changes**; (b) `RandomWordsRequested` gains `extraArgs` (ABI-encoded `nativePayment` flag); (c) `RandomWordsFulfilled` gains `nativePayment`/`onlyPremium`; (d) new `SubscriptionFundedWithNative`; (e) `SubscriptionCanceled` splits the refund into `amountLink` + `amountNative`. The v2.5 `ConfigSet`/`ProvingKeyRegistered` shapes above are the canonical `VRFCoordinatorV2_5` build — verify against deployed bytecode if you hit a coordinator on an unusual release.

---

## 2. Function signatures (chain-agnostic)

### 2.1 VRF v2 (`VRFCoordinatorV2`)

| Selector | Signature |
|----------|-----------|
| `0x5d3b1d30` | `requestRandomWords(bytes32 keyHash, uint64 subId, uint16 minimumRequestConfirmations, uint32 callbackGasLimit, uint32 numWords)` → `uint256 requestId` |
| `0xa21a23e4` | `createSubscription()` → `uint64 subId` |
| `0xa47c7696` | `getSubscription(uint64 subId)` → `(uint96 balance, uint64 reqCount, address owner, address[] consumers)` |
| `0x7341c10c` | `addConsumer(uint64 subId, address consumer)` |
| `0x9f87fad7` | `removeConsumer(uint64 subId, address consumer)` |
| `0xd7ae1d30` | `cancelSubscription(uint64 subId, address to)` |
| `0xafc69b53` | `fundSubscription(uint64 subId, uint96 amount)` *(helper; on-coordinator funding is via `LINK.transferAndCall(coordinator, amount, abi.encode(subId))`)* |
| `0x38ba4614` | `fulfillRandomWords(uint256 requestId, uint256[] randomWords)` *(consumer callback, `VRFConsumerBaseV2`)* |
| `0x00012291` | `getRequestConfig()` → `(uint16, uint32, bytes32[])` |
| `0xc3f909d4` | `getConfig()` |
| `0x689c4517` | `BLOCKHASH_STORE()` |
| `0x1b6b6d23` | `LINK()` |

### 2.2 VRF v2.5 (`VRFCoordinatorV2_5`) — single-struct request, native path

| Selector | Signature |
|----------|-----------|
| `0x9b1c385e` | `requestRandomWords((bytes32 keyHash, uint256 subId, uint16 requestConfirmations, uint32 callbackGasLimit, uint32 numWords, bytes extraArgs))` → `uint256 requestId` |
| `0xa21a23e4` | `createSubscription()` → `uint256 subId` |
| `0xdc311dd3` | `getSubscription(uint256 subId)` → `(uint96 balance, uint96 nativeBalance, uint64 reqCount, address owner, address[] consumers)` |
| `0xbec4c08c` | `addConsumer(uint256 subId, address consumer)` |
| `0xcb631797` | `removeConsumer(uint256 subId, address consumer)` |
| `0x0ae09540` | `cancelSubscription(uint256 subId, address to)` |
| `0x95b55cfc` | `fundSubscriptionWithNative(uint256 subId)` *(payable)* |
| `0x38ba4614` | `fulfillRandomWords(uint256 requestId, uint256[] randomWords)` *(consumer callback, `VRFConsumerBaseV2Plus`)* |
| `0x689c4517` | `BLOCKHASH_STORE()` |
| `0x1b6b6d23` | `LINK()` |

`extraArgs` is `abi.encodeWithSelector(VRFV2PlusClient.EXTRA_ARGS_V1_TAG, (bool nativePayment))` — set `nativePayment = true` to pay in the gas token, `false` for LINK. LINK funding of a v2.5 sub is still `LINK.transferAndCall(coordinator, amount, abi.encode(subId))`.

### 2.3 Wrapper (direct funding)

| Selector | Signature | Wrapper |
|----------|-----------|---------|
| `0x9cfc058e` | `requestRandomWordsInNative(uint32 callbackGasLimit, uint16 requestConfirmations, uint32 numWords, bytes extraArgs)` | `VRFV2PlusWrapper` |
| — | LINK direct-funding request is `LINK.transferAndCall(wrapper, price, abi.encode(callbackGasLimit, requestConfirmations, numWords, extraArgs))` | both wrappers |

---

## 3. Coordinator addresses per chain

All verified via `eth_getCode` (non-empty) on 2026-05-29.

| Chain (id) | Version | Contract | Address |
|------------|---------|----------|---------|
| Ethereum (1) | v1 | VRFCoordinator | `0xf0d54349aDdcf704F77AE15b96510dEA15cb7952` |
| Ethereum (1) | v2 | VRFCoordinatorV2 | `0x271682DEB8C4E0901D1a1550aD2e64D568E69909` |
| Ethereum (1) | v2.5 | VRFCoordinatorV2_5 | `0xD7f86b4b8Cae7D942340FF628F82735b7a20893a` |
| BNB (56) | v1 | VRFCoordinator | `0x747973a5A2a4Ae1D3a8fDF5479f1514F65Db9C31` |
| BNB (56) | v2 | VRFCoordinatorV2 | `0xc587d9053cd1118f25F645F9E08BB98c9712A4EE` |
| BNB (56) | v2.5 | VRFCoordinatorV2_5 | `0xd691f04bc0C9a24Edb78af9E005Cf85768F694C9` |
| Polygon (137) | v1 | VRFCoordinator | `0x3d2341ADb2D31f1c5530cDC622016af293177AE0` |
| Polygon (137) | v2 | VRFCoordinatorV2 | `0xAE975071Be8F8eE67addBC1A82488F1C24858067` |
| Polygon (137) | v2.5 | VRFCoordinatorV2_5 | `0xec0Ed46f36576541C75739E915ADbCb3DE24bD77` |
| Avalanche (43114) | v2 | VRFCoordinatorV2 | `0xd5D517aBE5cF79B7e95eC98dB0f0277788aFF634` |
| Avalanche (43114) | v2.5 | VRFCoordinatorV2_5 | `0xE40895D055bccd2053dD0638C9695E326152b1A4` |
| Arbitrum One (42161) | v2 | VRFCoordinatorV2 | `0x41034678D6C633D8a95c75e1138A360a28bA15d1` |
| Arbitrum One (42161) | v2.5 | VRFCoordinatorV2_5 | `0x3C0Ca683b403E37668AE3DC4FB62F4B29B6f7a3e` |
| Optimism (10) | v2.5 | VRFCoordinatorV2_5 | `0x5FE58960F730153eb5A84a47C51BD4E58302E1c8` |
| Base (8453) | v2.5 | VRFCoordinatorV2_5 | `0xd5D517aBE5cF79B7e95eC98dB0f0277788aFF634` |

**Version availability (verified):**
- **v1** exists only on Ethereum, BNB, Polygon. (Not on AVAX/ARB/OP/Base.)
- **Optimism & Base** launched VRF directly at **v2.5** — no mainnet v2 coordinator there.
- ⚠️ **Address collision (real, not an error):** `0xd5D517aBE5cF79B7e95eC98dB0f0277788aFF634` is the **v2 coordinator on Avalanche** *and* independently the **v2.5 coordinator on Base** — the same CREATE2 address on two different chains (different bytecode: 24103 B on AVAX vs 24129 B on Base, both verified live). **Always key VRF lookups by `(chainId, version)`, never by address alone.**

---

## 4. Wrapper + BlockhashStore addresses

Wrappers (direct funding), all verified live:

| Chain | v2 `VRFV2Wrapper` | v2.5 `VRFV2PlusWrapper` |
|-------|-------------------|-------------------------|
| Ethereum | `0x5A861794B927983406fCE1D062e00b9368d97Df6` | `0x02aae1A04f9828517b3007f83f6181900CaD910c` |
| BNB | `0x721DFbc5Cfe53d32ab00A9bdFa605d3b8E1f3f42` | `0x471506e6ADED0b9811D05B8cAc8Db25eE839Ac94` |
| Polygon | `0x4e42f0adEB69203ef7AaA4B7c414e5b1331c14dc` | `0xc8F13422c49909F4Ec24BF65EDFBEbe410BB9D7c` |
| Avalanche | `0x721DFbc5Cfe53d32ab00A9bdFa605d3b8E1f3f42` | `0x62Fb87c10A917580cA99AB9a86E213Eb98aa820C` |
| Arbitrum | `0x2D159AE3bFf04a10A355B608D22BDEC092e934fa` | `0x14632CD5c12eC5875D41350B55e825c54406BaaB` |
| Optimism | — | `0x6A39cE9604FAD060B32bc35BE2e0D3825B2b8D4B` |
| Base | — | `0xb0407dbe851f8318bd31404A49e658143C982F23` |

> The AVAX v2 wrapper shares its address with the BNB v2 wrapper (`0x721DFbc5…`) — another deterministic-deploy collision; verified live on **both** AVAX (8168 B) and BNB.

**BlockhashStore (Ethereum):** `0xaA25602bcCf3bBdE8E2F0F09F3a1F6dE54593C0` — shared by the v2 and v2.5 coordinators (read live from `BLOCKHASH_STORE()` = `0x689c4517` on both). For other chains, call `BLOCKHASH_STORE()` on that chain's coordinator and `eth_getCode`-verify.

---

## 5. Detection invariants & gotchas

1. **Request → fulfill pairing:** `RandomWordsRequested.requestId` matches `RandomWordsFulfilled.requestId`. In v2 `requestId = keccak(keyHash, preSeed)` semantics; just join on `requestId`.
2. **v2 vs v2.5 topics fully differ** — `subId` width change alters every event hash. Index both sets; disambiguate by emitter (coordinator) + version, not by event name.
3. **Native vs LINK payment** is only observable in v2.5: `RandomWordsFulfilled.nativePayment` and the `SubscriptionFundedWithNative` event. v2 is LINK-only.
4. **Subscription funding via LINK is an ERC-677 `transferAndCall`**, not a coordinator method call — to attribute funding, also watch LINK `Transfer(...,bytes)` (`0xe19260af…`) to the coordinator with `data = abi.encode(subId)`. The `fundSubscription` selector is a wrapper/helper convenience.
5. **`fulfillRandomWords` runs in the consumer**, called by the coordinator — the random words are delivered to your contract's callback, not emitted in full in the coordinator event (only `outputSeed`).
6. **v1 is deprecated** (2024-11-29) — present only for historical log decoding.

---

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- v2 topics
VRF2_RANDOM_WORDS_REQUESTED = '\x63373d1c4696214b898952999c9aaec57dac1ee2723cec59bea6888f489a9772'
VRF2_RANDOM_WORDS_FULFILLED = '\x7dffc5ae5ee4e2e4df1651cf6ad329a73cebdb728f37ea0187b9b17e036756e4'
VRF2_SUBSCRIPTION_CREATED   = '\x464722b4166576d3dcbba877b999bc35cf911f4eaf434b7eba68fa113951d0bf'
-- v2.5 topics
VRF25_RANDOM_WORDS_REQUESTED= '\xeb0e3652e0f44f417695e6e90f2f42c99b65cd7169074c5a654b16b9748c3a4e'
VRF25_RANDOM_WORDS_FULFILLED= '\xaeb4b4786571e184246d39587f659abf0e26f41f6a3358692250382c0cdb47b7'
VRF25_SUB_FUNDED_NATIVE     = '\x7603b205d03651ee812f803fccde89f1012e545a9c99f0abfea9cedd0fd8e902'
-- v1 topics
VRF1_RANDOMNESS_REQUEST     = '\x56bd374744a66d531874338def36c906e3a6cf31176eb1e9afd9f1de69725d51'
-- selectors
SEL_VRF2_REQUEST            = '\x5d3b1d30'
SEL_VRF25_REQUEST_STRUCT    = '\x9b1c385e'
SEL_CREATE_SUBSCRIPTION     = '\xa21a23e4'
SEL_REQUEST_RANDOM_NATIVE   = '\x9cfc058e'

-- coordinators (chain-specific; see §3 for full table)
ETH_VRF_V2_5  = '\xd7f86b4b8cae7d942340ff628f82735b7a20893a'
ETH_VRF_V2    = '\x271682deb8c4e0901d1a1550ad2e64d568e69909'
ETH_VRF_V1    = '\xf0d54349addcf704f77ae15b96510dea15cb7952'
ETH_BLOCKHASH_STORE = '\xaa25602bccf3bbde8e2f0f09f3a1f6de54593c0'
```

---

## 7. Verification & sources

- **Topic0 / selectors:** computed locally (pycryptodome keccak) from the canonical `VRFCoordinatorV2`/`VRFCoordinatorV2_5`/`VRFCoordinator` (v1) event & function signatures. The v2.5 single-struct `requestRandomWords` selector `0x9b1c385e` was computed against the `VRFV2PlusClient.RandomWordsRequest` tuple.
- **Addresses:** `eth_getCode` (non-empty) on the 7 publicnode RPCs; the `0xd5D517…` collision confirmed on both AVAX (24103 B) and Base (24129 B); the `0x721DFbc5…` v2 wrapper confirmed on both BNB and AVAX (8168 B).
- Sources: [VRF v2.5 supported networks](https://docs.chain.link/vrf/v2-5/supported-networks) · [VRF v2 subscription](https://docs.chain.link/vrf/v2/subscription/supported-networks) · [VRF v2 direct funding](https://docs.chain.link/vrf/v2/direct-funding/supported-networks) · [VRF v1 (deprecated)](https://docs.chain.link/vrf/v1/supported-networks) · `smartcontractkit/chainlink` `contracts/src/v0.8/vrf/`.
