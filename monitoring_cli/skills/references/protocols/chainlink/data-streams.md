# Chainlink Data Streams — Topics, Selectors, Addresses

**Status:** addresses verified via `eth_getCode` (non-empty) on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon mainnet on 2026-05-29. Topic0/selectors computed locally (keccak) and cross-checked against deployed `VerifierProxy 2.0.0` bytecode (Arbitrum) and live logs. Topics/selectors are chain-agnostic; addresses are network-specific.

Data Streams is a **pull-based** (consumer-initiated) low-latency oracle. Off-chain OCR3 reports are fetched via the Streams API/SDK, then verified on-chain by calling `VerifierProxy.verify()`. The proxy routes the report to the correct `Verifier` (by config digest), and — on fee-enabled chains — bills LINK/native via the `FeeManager`. There is **no continuous on-chain price feed**; events fire only when a consumer verifies a report.

## Data Streams — contract types

| Contract | Role |
|----------|------|
| `VerifierProxy` | Stable entrypoint. `verify(bytes,bytes)` / `verifyBulk`. Routes a report to the right `Verifier` by config digest and triggers billing. `typeAndVersion` on the live ARB contract = `VerifierProxy 2.0.0`. |
| `Verifier` | Verifies the OCR3 report signatures/config for a given feed/config digest. Registered on the proxy via `setVerifier`/`unsetVerifier`. Emits `ReportVerified`, `ConfigSet`, `FeedActivated`/`FeedDeactivated`. |
| `FeeManager` | Computes & collects the per-verification fee (LINK or native, with optional surcharge/discount). Address read live from proxy `s_feeManager()` (ARB = `0xd2f8e6e47A0661e2C0Ec7e12B8d455a33c2Fd497`). |
| `RewardManager` | Distributes collected fees to the pool of node operators/recipients. |
| `ChannelConfigStore` | Stores channel/stream configuration (DDM — Decentralized Data Model) used by report generation. |

## Data Streams — event signatures (exact)

`topic0 = keccak256(signature)`.

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x58ca9502e98a536e06e72d680fcc251e5d10b72291a281665a2c2dc0ac30fcc5` | `ReportVerified(bytes32 indexed feedId, address requester)` | Verifier |
| `0xeaf504ec99a82134f214ffee2408a2198688a63d507342a735e83f8fb47a7997` | `ConfigSet(bytes32 configDigest, uint32 previousConfigBlockNumber, bytes32 configDigest, ...)` — **UNVERIFIED arg tuple** (Verifier OCR3 ConfigSet; the full struct varies by Verifier version, recompute against target bytecode before relying on it) | Verifier |
| `0xf438564f793525caa89c6e3a26d41e16aa39d1e589747595751e3f3df75cb2b4` | `FeedActivated(bytes32 indexed feedId)` | Verifier |
| `0xfc4f79b8c65b6be1773063461984c0974400d1e99654c79477a092ace83fd061` | `FeedDeactivated(bytes32 indexed feedId)` | Verifier |
| `0xbeb513e532542a562ac35699e7cd9ae7d198dcd3eee15bada6c857d28ceaddcf` | `VerifierSet(bytes32 oldConfigDigest, bytes32 newConfigDigest, address verifierAddress)` | VerifierProxy |
| `0x11dc15c4b8ac2b183166cc8427e5385a5ece8308217a4217338c6a7614845c4c` | `VerifierUnset(bytes32 configDigest, address verifierAddress)` | VerifierProxy |
| `0x04628abcaa6b1674651352125cb94b65b289145bc2bc4d67720bb7d966372f03` | `FeeManagerSet(address oldFeeManager, address newFeeManager)` | VerifierProxy |
| `0x08f7c0d17932ddb8523bc06754d42ff19ebc77d76a8b9bfde02c28ab1ed3d639` | `NativeSurchargeUpdated(uint64 newSurcharge)` | FeeManager |
| `0x5eba5a8afa39780f0f99b6cbeb95f3da6a7040ca00abd46bdc91a0a060134139` | `SubscriberDiscountUpdated(address subscriber, bytes32 feedId, address token, uint64 discount)` | FeeManager |

> `ReportVerified` is the workhorse detection event but is **sparse** (only on consumer-initiated verification; no logs in a random 10k-block ARB window). The OCR3 `ConfigSet` struct differs across Verifier releases — treat the tuple above as a placeholder and recompute topic0 against the actual deployed Verifier if you need to decode it. `FeedActivated`/`FeedDeactivated`/`VerifierSet`/`VerifierUnset` topics are computed from the canonical single-/triple-arg sigs.

## Data Streams — function signatures (exact)

4-byte selectors. **bold = confirmed present in live `VerifierProxy 2.0.0` bytecode (Arbitrum)**.

| selector | Function | On |
|----------|----------|----|
| **`0xf7e83aee`** | `verify(bytes payload, bytes parameterPayload) payable returns (bytes)` | VerifierProxy |
| **`0xf873a61c`** | `verifyBulk(bytes[] payloads, bytes parameterPayload) payable returns (bytes[])` | VerifierProxy |
| **`0x472d35b9`** | `setFeeManager(address feeManager)` | VerifierProxy |
| **`0x38416b5b`** | `s_feeManager() returns (address)` | VerifierProxy |
| **`0xeeb7b248`** | `getVerifier(bytes32 configDigest) returns (address)` | VerifierProxy |
| **`0x6e914094`** | `unsetVerifier(bytes32 configDigest)` | VerifierProxy |
| **`0x8c2a4d53`** | `initializeVerifier(address verifierAddress)` | VerifierProxy |
| `0xfa8305bc` | `setVerifier(bytes32,bytes32,(uint32,address)[])` — **NOT present in v2.0.0 proxy bytecode**; this is the older v0.4 ABI. The v2.0.0 `setVerifier` arg tuple was not matched by common guesses — **flag UNVERIFIED**, confirm against target bytecode. | VerifierProxy |

### V3 Report struct (crypto streams schema — verified from docs)

```solidity
struct ReportV3 {
  bytes32 feedId;                // stream/feed identifier
  uint32  validFromTimestamp;    // earliest applicable ts
  uint32  observationsTimestamp; // observation ts
  uint192 nativeFee;             // verification fee in native (wei)
  uint192 linkFee;               // verification fee in LINK (juels)
  uint32  expiresAt;             // report expiry
  int192  price;                 // 18-decimal median price
  int192  bid;                   // 18-decimal simulated buy
  int192  ask;                   // 18-decimal simulated sell
}
```
The on-chain `verify()` return is ABI-encoded; decode into the schema matching the report version byte in `feedId` (V2 = no bid/ask; V3 = crypto with bid/ask; V4 = RWA with `marketStatus`).

## Data Streams — VerifierProxy addresses per chain

All verified non-empty bytecode, 2026-05-29 (Ethereum/ARB/Base/OP/AVAX ≈ 14020 B; the shared **BNB+Polygon** proxy is a different, smaller build at 7009 B).

| Chain | chainId | VerifierProxy | Verified |
|-------|---------|---------------|----------|
| Ethereum | 1 | `0x5A1634A86e9b7BfEf33F0f3f3EA3b1aBBc4CC85F` | yes |
| Arbitrum One | 42161 | `0x478Aa2aC9F6D65F84e09D9185d126c3a17c2a93C` | yes |
| Base | 8453 | `0xDE1A28D87Afd0f546505B28AB50410A5c3a7387a` | yes |
| Optimism (OP) | 10 | `0xEBA4789A88C89C18f4657ffBF47B13A3abC7EB8D` | yes |
| Avalanche C-Chain | 43114 | `0x79BAa65505C6682F16F9b2C7F8afEBb1821BE3f6` | yes |
| BNB Smart Chain | 56 | `0xF276a4BC8Da323EA3E8c3c195a4E2E7615a898d1` | yes |
| Polygon PoS | 137 | `0xF276a4BC8Da323EA3E8c3c195a4E2E7615a898d1` | yes |

> **BNB and Polygon share the same VerifierProxy address** (`0xF276…98d1`) — this is the value in Chainlink's canonical `StreamsNetworksData.ts` for both chains (deterministic deployment). Both verified independently on their respective RPCs.
> Fee-enabled chains (FeeManager deployed, payment required): Arbitrum, Avalanche, Base, Optimism, and most L2s. On those, `verify()` must be funded (LINK approval or `msg.value` native).

## Quick-copy bytea constants (Postgres)

```
-- topic0
ReportVerified  '\x58ca9502e98a536e06e72d680fcc251e5d10b72291a281665a2c2dc0ac30fcc5'
FeedActivated   '\xf438564f793525caa89c6e3a26d41e16aa39d1e589747595751e3f3df75cb2b4'
FeedDeactivated '\xfc4f79b8c65b6be1773063461984c0974400d1e99654c79477a092ace83fd061'
VerifierSet     '\xbeb513e532542a562ac35699e7cd9ae7d198dcd3eee15bada6c857d28ceaddcf'
VerifierUnset   '\x11dc15c4b8ac2b183166cc8427e5385a5ece8308217a4217338c6a7614845c4c'
FeeManagerSet   '\x04628abcaa6b1674651352125cb94b65b289145bc2bc4d67720bb7d966372f03'
-- selectors
verify(bytes,bytes)  '\xf7e83aee'
verifyBulk           '\xf873a61c'
```
