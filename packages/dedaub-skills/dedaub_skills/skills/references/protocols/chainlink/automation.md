# Chainlink Automation (Keepers) — Topics, Selectors, Addresses

**Status:** verified 2026-05-29. All registry/registrar addresses verified via `eth_getCode` (non-empty) + `typeAndVersion()` (`0x181f5a77`); topic0/selectors computed locally (keccak) and cross-checked against live `eth_getLogs` (Ethereum v2.1, Base v2.3) and `eth_call` dispatch.
**Scope:** Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137). LINK token: [link-token.md](link-token.md).

Automation runs user "upkeeps" (conditional, time/cron, or log-triggered). A decentralized network of nodes calls `checkUpkeep`/`checkLog` off-chain and, when it returns true, submits an OCR2 `transmit` to the **registry**, which calls the upkeep's `performUpkeep` (via a per-upkeep `AutomationForwarder` in v2.1+).

**Live version map on these 7 chains (verified):** ETH / BNB / AVAX / ARB / Polygon = **v2.1** (`KeeperRegistry 2.1.0`); Base / Optimism = **v2.3** (`AutomationRegistry 2.3.0`). Chainlink no longer performs pre-v2.1 upkeeps; older registries (v1.x/2.0) are deprecated and not re-listed. The v1.x/2.0 topics below are retained for **historical** log decoding.

---

## 1. Contract types & versions

| Contract | Versions | 1-liner |
|----------|----------|---------|
| `KeeperRegistry` | v1.1 / v1.2 / v1.3 | Original monolithic registry (no proxy); holds upkeeps + LINK balances, performs upkeeps, pays keepers. |
| `KeeperRegistrar` | v1.2 | Registration funnel → registry. |
| `KeeperRegistry2_0` | v2.0 | First OCR2-based registry (`Transmitted`/`ConfigSet`). Logic split into base + `KeeperRegistryLogic2_0`. |
| **`KeeperRegistry 2.1.0`** | **v2.1** | **Master proxy** dispatching via `fallback`→`delegatecall` to three logic contracts (**Logic A/B/C**). Adds log triggers, custom triggers, per-upkeep forwarders, StreamsLookup. |
| `AutomationRegistrar2_1` | v2.1 | Registrar with `triggerType`/`triggerConfig`/`offchainConfig`. |
| `AutomationRegistry 2.2.0` | v2.2 | Adds `ChainModule` (chain-specific gas / L1-fee handling). Same event shapes as v2.1. *(Not on the 7 target chains.)* |
| **`AutomationRegistry 2.3.0`** | **v2.3** | **Multi-token billing** (LINK or native/ERC-20). Adds `UpkeepCharged`, `FeesWithdrawn`, billing-token plumbing. |
| `AutomationRegistrar2_3` | v2.3 | Adds `billingToken` to `RegistrationRequested`. |
| `AutomationForwarder` | v2.1+ | **One per upkeep.** Registry → `forward(uint256,bytes)` → target's `performUpkeep`. Isolates `msg.sender` per upkeep. No single canonical address — resolve via `registry.getForwarder(upkeepId)`. |
| `AutomationCompatibleInterface` | user | `checkUpkeep(bytes)` + `performUpkeep(bytes)` — conditional/time upkeeps. |
| `ILogAutomation` | user (v2.1+) | `checkLog(Log,bytes)` + `performUpkeep(bytes)` — log-triggered. |
| `StreamsLookupCompatibleInterface` | user (v2.1+) | reverts `error StreamsLookup(...)` to pull Data Streams reports off-chain; node re-calls `checkCallback`. |

---

## 2. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 2.1 Version-invariant registry events (same topic0 v1.x → v2.3)

| topic0 | Event |
|--------|-------|
| `0xbae366358c023f887e791d7a62f2e4316f1026bd77f6fb49501a917b3bc5d012` | `UpkeepRegistered(uint256 indexed id, uint32 performGas, address admin)` *(param named `executeGas` in v1.x/v2.0 — same types/hash)* |
| `0x91cb3bb75cfbd718bbfccc56b7f53d92d7048ef4ca39a3b7b7c6d4af1f791181` | `UpkeepCanceled(uint256 indexed id, uint64 indexed atBlockHeight)` |
| `0xc24c07e655ce79fba8a589778987d3c015bc6af1632bb20cf9182e02a65d972c` | `UpkeepGasLimitSet(uint256 indexed id, uint96 gasLimit)` |
| `0xb38647142fbb1ea4c000fc4569b37a4e9a9f6313317b84ee3e5326c1a6cd06ff` | `UpkeepMigrated(uint256 indexed id, uint256 remainingBalance, address destination)` |
| `0x74931a144e43a50694897f241d973aecb5024c0e910f9bb80a163ea3c1cf5a71` | `UpkeepReceived(uint256 indexed id, uint256 startingBalance, address importedFrom)` |
| `0xafd24114486da8ebfc32f3626dada8863652e187461aa74d4bfa734891506203` | `FundsAdded(uint256 indexed id, address indexed from, uint96 amount)` |
| `0xf3b5906e5672f3e524854103bcafbbdba80dbdfeca2c35e116127b1060a68318` | `FundsWithdrawn(uint256 indexed id, uint256 amount, address to)` |
| `0x8ab10247ce168c27748e656ecf852b951fcaac790c18106b19aa0ae57a8b741f` | `UpkeepPaused(uint256 indexed id)` *(v1.3+/v2.x)* |
| `0x7bada562044eb163f6b4003c4553e4e62825344c0418eea087bed5ee05a47456` | `UpkeepUnpaused(uint256 indexed id)` *(v1.3+/v2.x)* |

### 2.2 `UpkeepPerformed` — **differs by version** (three distinct topic0)

| topic0 | Version | Event |
|--------|---------|-------|
| `0xcaacad83e47cc45c280d487ec84184eee2fa3b54ebaa393bda7549f13da228f6` | **v1.1/1.2/1.3** | `UpkeepPerformed(uint256 indexed id, bool indexed success, address indexed from, uint96 payment, bytes performData)` |
| `0x29233ba1d7b302b8fe230ad0b81423aba5371b2a6f6b821228212385ee6a4420` | **v2.0** | `UpkeepPerformed(uint256 indexed id, bool indexed success, uint32 checkBlockNumber, uint256 gasUsed, uint256 gasOverhead, uint96 totalPayment)` |
| `0xad8cc9579b21dfe2c2f6ea35ba15b656e46b4f5b0cb424f52739b8ce5cac9c5b` | **v2.1/2.2/2.3** | `UpkeepPerformed(uint256 indexed id, bool indexed success, uint96 totalPayment, uint256 gasUsed, uint256 gasOverhead, bytes trigger)` — most common topic on live ETH v2.1 + Base v2.3 |

### 2.3 OCR2 config / transmit (v2.0+)

| topic0 | Event |
|--------|-------|
| `0xb04e63db38c49950639fa09d29872f21f5d49d614f3a969d8adf3d4b52e41a62` | `Transmitted(bytes32 configDigest, uint32 epoch)` |
| `0x1591690b8638f5fb2dbec82ac741805ac5da8b45dc5263f4875b0496fdce4e05` | `ConfigSet(uint32 previousConfigBlockNumber, bytes32 configDigest, uint64 configCount, address[] signers, address[] transmitters, uint8 f, bytes onchainConfig, uint64 offchainConfigVersion, bytes offchainConfig)` |
| `0xa46de38886467c59be07a0675f14781206a5477d871628af46c2443822fcb725` | `PayeesUpdated(address[] transmitters, address[] payees)` *(v2.x)* |
| `0x056264c94f28bb06c99d13f0446eb96c67c215d8d707bce2655a98ddf1c0b71f` | `KeepersUpdated(address[] keepers, address[] payees)` *(v1.x)* |
| `0x72ce65f0f99e58f1aae41898ec035ed015bdce1037090deacfb4f0285390e5c3` | `ConfigSet(Config)` *(v1.x single-tuple — wholly different from the v2.x OCR `ConfigSet`)* |

### 2.4 Report events — **v2.0 (id only) vs v2.1+ (id + trigger bytes)**

| topic0 | Version | Event |
|--------|---------|-------|
| `0x7895fdfe292beab0842d5beccd078e85296b9e17a30eaee4c261a2696b84eb96` | v2.0 | `InsufficientFundsUpkeepReport(uint256 indexed id)` |
| `0x561ff77e59394941a01a456497a9418dea82e2a39abb3ecebfb1cef7e0bfdc13` | v2.0 | `ReorgedUpkeepReport(uint256 indexed id)` |
| `0x5aa44821f7938098502bff537fbbdc9aaaa2fa655c10740646fce27e54987a89` | v2.0 | `StaleUpkeepReport(uint256 indexed id)` |
| `0xd84831b6a3a7fbd333f42fe7f9104a139da6cca4cc1507aef4ddad79b31d017f` | v2.0 | `CancelledUpkeepReport(uint256 indexed id)` |
| `0x377c8b0c126ae5248d27aca1c76fac4608aff85673ee3caf09747e1044549e02` | v2.1+ | `InsufficientFundsUpkeepReport(uint256 indexed id, bytes trigger)` |
| `0x6aa7f60c176da7af894b384daea2249497448137f5943c1237ada8bc92bdc301` | v2.1+ | `ReorgedUpkeepReport(uint256 indexed id, bytes trigger)` |
| `0x405288ea7be309e16cfdf481367f90a413e1d4634fcdaf8966546db9b93012e8` | v2.1+ | `StaleUpkeepReport(uint256 indexed id, bytes trigger)` |
| `0xc3237c8807c467c1b39b8d0395eff077313e691bf0a7388106792564ebfd5636` | v2.1+ | `CancelledUpkeepReport(uint256 indexed id, bytes trigger)` |

### 2.5 v2.1+ extra registry events (confirmed in live ETH/Base logs)

| topic0 | Event |
|--------|-------|
| `0xa4a4e334c0e330143f9437484fe516c13bc560b86b5b0daf58e7084aaac228f2` | `DedupKeyAdded(bytes32 indexed dedupKey)` |
| `0xcba2d5723b2ee59e53a8e8a82a4a7caf4fdfe70e9f7c582950bf7e7a5c24e83d` | `UpkeepCheckDataSet(uint256 indexed id, bytes newCheckData)` |
| `0x3e8740446213c8a77d40e08f79136ce3f347d13ed270a6ebdf57159e0faf4850` | `UpkeepOffchainConfigSet(uint256 indexed id, bytes offchainConfig)` |
| `0x2b72ac786c97e68dbab71023ed6f2bdbfc80ad9bb7808941929229d71b7d5664` | `UpkeepTriggerConfigSet(uint256 indexed id, bytes triggerConfig)` |
| `0x2fd8d70753a007014349d4591843cc031c2dd7a260d7dd82eca8253686ae7769` | `UpkeepPrivilegeConfigSet(uint256 indexed id, bytes privilegeConfig)` |
| `0xb1cbb2c4b8480034c27e06da5f096b8233a8fd4497028593a41ff6df79726b35` | `UpkeepAdminTransferRequested(uint256 indexed id, address indexed from, address indexed to)` |
| `0x1d07d0b0be43d3e5fee41a80b579af370affee03fa595bf56d5d4c19328162f1` | `OwnerFundsWithdrawn(uint96 amount)` |

### 2.6 v2.3-only billing events (confirmed in live Base v2.3 logs)

| topic0 | Event |
|--------|-------|
| `0x801ba6ed51146ffe3e99d1dbd9dd0f4de6292e78a9a34c39c0183de17b3f40fc` | `UpkeepCharged(uint256 indexed id, (uint96 gasChargeInBillingToken, uint96 premiumInBillingToken, uint96 gasReimbursementInJuels, uint96 premiumInJuels, address billingToken, uint96 linkUSD, uint96 nativeUSD, uint96 billingUSD) receipt)` |
| `0x5e110f8bc8a20b65dcc87f224bdf1cc039346e267118bae2739847f07321ffa8` | `FeesWithdrawn(address indexed assetAddress, address indexed recipient, uint256 amount)` |

### 2.7 Registrar events

| topic0 | Version | Event |
|--------|---------|-------|
| `0xc3f5df4aefec026f610a3fcb08f19476492d69d2cb78b1c2eba259a8820e6a78` | v1.2 | `RegistrationRequested(bytes32 indexed hash, string name, bytes encryptedEmail, address indexed upkeepContract, uint32 gasLimit, address adminAddress, bytes checkData, uint96 amount, uint8 indexed source)` |
| `0x7684390ebb103102f7f48c71439c2408713f8d437782a6fab2756acc0e42c1b7` | v2.1/2.2 | `RegistrationRequested(bytes32 indexed hash, string name, bytes encryptedEmail, address indexed upkeepContract, uint32 gasLimit, address adminAddress, uint8 triggerType, bytes triggerConfig, bytes offchainConfig, bytes checkData, uint96 amount)` |
| `0xd178af9fe30387562e61bb997b245b7f49c26aad1e50c39d7b438ffa6c41b306` | v2.3 | `RegistrationRequested(…, uint96 amount, address billingToken)` |
| `0xb9a292fb7e3edd920cd2d2829a3615a640c43fd7de0a0820aa0668feb4c37d4b` | all | `RegistrationApproved(bytes32 indexed hash, string displayName, uint256 indexed upkeepId)` |

---

## 3. Function signatures (chain-agnostic)

| Selector | Signature | Where |
|----------|-----------|-------|
| `0x6e04ff0d` | `checkUpkeep(bytes)` | target contract |
| `0x4585e33b` | `performUpkeep(bytes)` | target; also called via forwarder |
| `0x40691db4` | `checkLog((uint256,uint256,bytes32,uint256,bytes32,address,bytes32[],bytes), bytes)` | `ILogAutomation` |
| `0x71791aa0` | `checkUpkeep(uint256, bytes)` | registry off-chain sim (id + triggerData), v2.1+ |
| `0xf7d334ba` | `checkUpkeep(uint256)` | registry off-chain sim (id only), v2.1+ |
| `0xaed2e929` | `simulatePerformUpkeep(uint256, bytes)` | registry — present in v2.1 master bytecode |
| `0xb1dc65a4` | `transmit(bytes32[3], bytes, bytes32[], bytes32[], bytes32)` | OCR2 transmit — present in master bytecode |
| `0x948108f7` | `addFunds(uint256, uint96)` | via fallback→logic |
| `0xc8048022` | `cancelUpkeep(uint256)` | via fallback→logic |
| `0x8765ecbe` | `pauseUpkeep(uint256)` | via fallback→logic |
| `0x5165f2f5` | `unpauseUpkeep(uint256)` | via fallback→logic |
| `0x744bfe61` | `withdrawFunds(uint256, address)` | via fallback→logic |
| `0xc7c3a19a` | `getUpkeep(uint256)` | via fallback→logic |
| `0x1865c57d` | `getState()` | verified live via `eth_call` through fallback dispatch |
| `0x06e3b632` | `getActiveUpkeepIDs(uint256, uint256)` | via fallback→logic |
| `0x79ea9943` | `getForwarder(uint256)` | v2.1+; resolves the upkeep's `AutomationForwarder` |
| `0xa72aa27e` | `setUpkeepGasLimit(uint256, uint32)` | via fallback→logic |
| `0x28f32f38` | `registerUpkeep(address, uint32, address, uint8, bytes, bytes, bytes)` | registry direct-register (v2.1+) |
| `0x8933a516` | `registerUpkeep((string,address,uint32,address,uint8,bytes,bytes,bytes,uint96))` | **Registrar** `RegistrationParams` entry (v2.1) |
| `0x79188d16` | `forward(uint256, bytes)` | `AutomationForwarder` |
| `0xf00e6a2a` | `getTarget()` | `AutomationForwarder` |
| `0x181f5a77` | `typeAndVersion()` | all registries/registrars — the version oracle |

---

## 4. Registry + Registrar addresses per chain (all verified via `typeAndVersion()`)

| Chain (id) | Version | Registry | Registrar |
|------------|---------|----------|-----------|
| Ethereum (1) | v2.1 | `0x6593c7De001fC8542bB1703532EE1E5aA0D458fD` | `0x6B0B234fB2f380309D47A7E9391E29E9a179395a` |
| Base (8453) | v2.3 | `0xf4bAb6A129164aBa9B113cB96BA4266dF49f8743` | `0xE28Adc50c7551CFf69FCF32D45d037e5F6554264` |
| BNB (56) | v2.1 | `0xDc21E279934fF6721CaDfDD112DAfb3261f09A2C` | `0xf671F60bCC964B309D22424886FF202807381B32` |
| Avalanche (43114) | v2.1 | `0x7f00a3Cd4590009C349192510D51F8e6312E08CB` | `0x5Cb7B29e621810Ce9a04Bee137F8427935795d00` |
| Arbitrum One (42161) | v2.1 | `0x37D9dC70bfcd8BC77Ec2858836B923c560E891D1` | `0x86EFBD0b6736Bed994962f9797049422A3A8E8Ad` |
| Optimism (10) | v2.3 | `0x4F70c323b8B72AeffAF633Aa4D5e8B6Be5df4AEf` | `0xe96057F85510292231e2C759752f012C87A8c8dd` |
| Polygon PoS (137) | v2.1 | `0x08a8eea76D2395807Ce7D1FC942382515469cCA1` | `0x0Bc5EDC7219D272d9dEDd919CE2b4726129AC02B` |

No live v1.x/v2.0/v2.2 registry on these 7 chains. `AutomationForwarder` addresses are **per-upkeep** — resolve via `registry.getForwarder(upkeepId)` (`0x79ea9943`); there is no single canonical forwarder address.

---

## 5. Detection invariants & gotchas

1. **`KeeperRegistry 2.1.0` is a master+logic delegatecall dispatcher, NOT EIP-1967.** Only `transmit` (`0xb1dc65a4`) and `simulatePerformUpkeep` (`0xaed2e929`) appear as literal selectors in the master bytecode; everything else routes through the `fallback`→Logic A/B/C. **The EIP-1967 impl slot `0x360894…` does not apply** — read the version via `typeAndVersion()` instead. **Detect activity by events, not by selector-in-bytecode scans.**
2. **`UpkeepPerformed` has three version-specific topic0s** (§2.2). Pick the one matching the registry's `typeAndVersion()`, or index all three.
3. **v2.0 vs v2.1+ report events differ by an extra `bytes trigger`** — different topic0 (§2.4). Same for `RegistrationRequested` (§2.7).
4. **v2.3 introduces multi-token billing** — watch `UpkeepCharged` (`0x801ba6ed…`) for the actual fee + `billingToken`; on v2.1 fees are LINK-only via `UpkeepPerformed.totalPayment`.
5. **The forwarder isolates `msg.sender`** — your upkeep's `performUpkeep` is called by its `AutomationForwarder`, not the registry directly (v2.1+). Validate `msg.sender == forwarder`.
6. **Registrar `RegistrationRequested` ≠ registry `UpkeepRegistered`** — request is the funnel (may auto-approve or await admin); `UpkeepRegistered` (+ `RegistrationApproved`) is the actual mint.

---

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- version-invariant
UPKEEP_REGISTERED       = '\xbae366358c023f887e791d7a62f2e4316f1026bd77f6fb49501a917b3bc5d012'
UPKEEP_CANCELED         = '\x91cb3bb75cfbd718bbfccc56b7f53d92d7048ef4ca39a3b7b7c6d4af1f791181'
FUNDS_ADDED             = '\xafd24114486da8ebfc32f3626dada8863652e187461aa74d4bfa734891506203'
-- UpkeepPerformed (pick by version)
UPKEEP_PERFORMED_V1     = '\xcaacad83e47cc45c280d487ec84184eee2fa3b54ebaa393bda7549f13da228f6'
UPKEEP_PERFORMED_V20    = '\x29233ba1d7b302b8fe230ad0b81423aba5371b2a6f6b821228212385ee6a4420'
UPKEEP_PERFORMED_V21    = '\xad8cc9579b21dfe2c2f6ea35ba15b656e46b4f5b0cb424f52739b8ce5cac9c5b'
-- v2.3 billing
UPKEEP_CHARGED          = '\x801ba6ed51146ffe3e99d1dbd9dd0f4de6292e78a9a34c39c0183de17b3f40fc'
-- OCR2
OCR2_TRANSMITTED        = '\xb04e63db38c49950639fa09d29872f21f5d49d614f3a969d8adf3d4b52e41a62'
OCR2_CONFIG_SET         = '\x1591690b8638f5fb2dbec82ac741805ac5da8b45dc5263f4875b0496fdce4e05'
-- registrar
REGISTRATION_REQUESTED_V21 = '\x7684390ebb103102f7f48c71439c2408713f8d437782a6fab2756acc0e42c1b7'
REGISTRATION_APPROVED   = '\xb9a292fb7e3edd920cd2d2829a3615a640c43fd7de0a0820aa0668feb4c37d4b'
-- selectors
SEL_CHECK_UPKEEP        = '\x6e04ff0d'
SEL_PERFORM_UPKEEP      = '\x4585e33b'
SEL_CHECK_LOG           = '\x40691db4'
SEL_TRANSMIT            = '\xb1dc65a4'
SEL_TYPE_AND_VERSION    = '\x181f5a77'
SEL_GET_FORWARDER       = '\x79ea9943'
```

---

## 7. Verification & sources

- **Topic0 / selectors:** computed locally (keccak); the v2.1/v2.3 set cross-checked against live `eth_getLogs` on the Ethereum v2.1 registry (`0x6593…`) and Base v2.3 registry (`0xf4bA…`) — `UpkeepPerformed`, `StaleUpkeepReport`, `UpkeepCharged`, `DedupKeyAdded`, `UpkeepTriggerConfigSet`, etc. observed live. `getState()` confirmed callable through the master's fallback despite the selector being absent from master bytecode (proving the logic-dispatch architecture).
- **Addresses:** `eth_getCode` (non-empty) + `typeAndVersion()` returning the exact `"KeeperRegistry 2.1.0"` / `"AutomationRegistry 2.3.0"` / `"AutomationRegistrar …"` strings.
- Sources: [Automation supported networks](https://docs.chain.link/chainlink-automation/overview/supported-networks) · [Automation contracts](https://docs.chain.link/chainlink-automation/reference/automation-contracts) · [Automation interfaces](https://docs.chain.link/chainlink-automation/reference/automation-interfaces) · [Migrate to v2.1](https://docs.chain.link/chainlink-automation/guides/migrate-to-v2) · `smartcontractkit/chainlink` `contracts/src/v0.8/automation/` (tag `contracts-v1.3.0`).
