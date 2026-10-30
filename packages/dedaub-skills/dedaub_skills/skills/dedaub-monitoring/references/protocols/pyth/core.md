# Pyth Core (price feeds) — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain, Arc)

**Status:** verified against live RPC on all nine target chains and the canonical `pyth-network/pyth-crosschain` repo on 2026-10-30.
**Scope:** the Pyth **pull-oracle price-feed contract** (Pyth Core), the second "Core Compatible" contract, the Pyth-operated **Wormhole receivers** that verify the update VAAs, and the governance **Executor**. Chains: Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Robinhood Chain (4663), Arc (5042). Topics and selectors are chain-agnostic. Addresses are network-specific.

Pyth is a **pull oracle**. Prices are not pushed on a schedule. Any caller submits a signed update (`bytes[] updateData`) with a fee to `updatePriceFeeds`. The contract verifies the Wormhole-signed Merkle root, then stores each price that is newer than the stored one. One `PriceFeedUpdate` log is emitted for each stored price. Consumers read with `getPriceNoOlderThan` / `getPriceUnsafe`, which emit nothing.

Every contract in this file is an **EIP-1967 UUPS proxy** (680 B or 177 B proxy code). Pyth Core has `owner() = 0`. It is upgraded only by a **governance VAA** from the Pyth governance data source (Wormhole chain 1 = Solana, emitter `0x5635979a221c34931e32620b9293a463065555ea71fe97cd6237ade875b12e9e`), sent through `executeGovernanceInstruction`. Pyth upgraded Core in place on 2026-08-26; integrations kept their address. Since that upgrade, Core verifies updates through a new Pyth-operated Wormhole receiver per chain, **not** the canonical Wormhole Core contract.

---

## 0. Contract families

| Contract | Role | Chains | Version (live) |
|----------|------|--------|----------------|
| **Pyth Core** (`PythUpgradable`) | Main price-feed contract. Stores prices. Emits `PriceFeedUpdate`. | all 9 | `1.4.6` (Robinhood: `1.4.5-alpha.1`) |
| **Pyth Core Compatible** | Second Core contract, same interface. Deployed before the 2026-08-26 upgrade so integrators could move early. | ETH, Base, BNB, Arb, OP, Poly | `1.4.5-alpha.1` |
| **Wormhole receiver, "pro-compatible"** (`WormholeReceiver` → `ReceiverImplementation`) | Verifies the update VAAs for Core / Core Compatible today. Guardian-set index 1. | ETH, Base, BNB, Arb, OP, Poly, Robin, Arc | — |
| **Wormhole receiver, "stable"** | Earlier Pyth-operated receiver. Guardian-set index 7. Still used by Avalanche Core. | all 9 | — |
| **Executor** (`ExecutorUpgradable`) | Executes Pyth governance VAAs. Owns Pyth Pro and Entropy. Owns itself. | ETH, Base, BNB, Arb, OP, Poly, Robin, Arc | `0.1.1` |

Pyth Pro is in [pro.md](pro.md). Entropy is in [entropy.md](entropy.md).

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Pyth Core / Core Compatible
| topic0 | Event |
|--------|-------|
| `0xd06a6b7f4918494b3719217d1802786c1f5112a6c1d88fe2cfec00b4584f6aec` | `PriceFeedUpdate(bytes32 indexed id, uint64 publishTime, int64 price, uint64 conf)` — one log per stored price |
| `0x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49` | `ContractUpgraded(address oldImplementation, address newImplementation)` — governance upgrade |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — EIP-1967, fires with `ContractUpgraded` |
| `0x6bce23ef3d34e51710fe4700b43ba5f1733a6215c883f384671a4ece3ea8aa20` | `GovernanceDataSourceSet((uint16,bytes32) oldDataSource, (uint16,bytes32) newDataSource, uint64 initialSequence)` |
| `0xd451e0fcb7c5b9e13de533604d158069dad159841c45f39f09d379bfc423080d` | `DataSourcesSet((uint16,bytes32)[] oldDataSources, (uint16,bytes32)[] newDataSources)` |
| `0x74dbbbe280ef27b79a8a0c449d5ae2ba7a31849103241d0f98df70bbc9d03e37` | `FeeSet(uint256 oldFee, uint256 newFee)` — per-update fee |
| `0x5ac11e113c4b7116e6d04c95bd9f5ec9109fc1199331c882f5a0b63c9b33ac2b` | `TransactionFeeSet(uint256 oldFee, uint256 newFee)` |
| `0xcdb88a22f82ddd76115ab7c66cf08eb1e40afe80c9b31017eb2cbdb1570b33ae` | `ValidPeriodSet(uint256 oldValidPeriod, uint256 newValidPeriod)` |
| `0xd495c4e5b386d59bccca38a2277b5d70a0f5e47d7b6587a45a6f5aca221a3125` | `WormholeAddressSet(address oldWormholeAddress, address newWormholeAddress)` — verifier swap, high signal |
| `0x78473f3f373f7673597f4f0fa5873cb4d375fea6d4339ad6b56dbd411513cb3f` | `FeeWithdrawn(address targetAddress, uint256 fee)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed, address indexed)` — init only |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8)` — init only |

Declared but **not emitted** by the deployed `1.4.6` code (the topic is absent from the implementation bytecode):
`0xd8b7774079faf4ab389d4e48b46d54e2bb8b66dd0de0d718f61730a9f3c92977` `TwapPriceFeedUpdate(bytes32 indexed id, uint64 startTime, uint64 endTime, int64 twapPrice, uint64 twapConf, uint32 downSlotsRatio)`.

Legacy (removed from source in March 2024, commit `8843d0f8`; not checked live because no archive log access):
`0x943f0e8a16c19895fb87cbeb1a349ed86d7f31923089dd36c1a1ed5e300f267b` `BatchPriceFeedUpdate(uint16 chainId, uint64 sequenceNumber)` ·
`0xef1f4c97783da7fc718b0334ca9b16bb0c5d1da6db75e96012b3613bb12707a0` `PriceFeedUpdate(bytes32 indexed id, bool fresh, uint16 chainId, uint64 sequenceNumber, uint64 lastPublishTime, uint64 publishTime, int64 price, uint64 conf)`.

### 1.2 Executor
| topic0 | Event |
|--------|-------|
| `0x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49` | `ContractUpgraded(address,address)` — same topic0 as Core |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed)` |

`execute(bytes)` emits no event of its own. Watch the call, or the events of the target contract.

### 1.3 Wormhole receivers
The receiver implementations hold **no event topics** in their bytecode. A guardian-set change (`submitNewGuardianSet`) leaves no log. Watch the call selector, or poll `getCurrentGuardianSetIndex()`.

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

### 2.1 Pyth Core / Core Compatible
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xef9e5e28` | `updatePriceFeeds(bytes[])` | payable; main write; emits `PriceFeedUpdate` for each fresher price |
| `0xb9256d28` | `updatePriceFeedsIfNecessary(bytes[],bytes32[],uint64[])` | payable; reverts with `NoFreshUpdate` when stored prices are already new enough |
| `0x4716e9c5` | `parsePriceFeedUpdates(bytes[],bytes32[],uint64,uint64)` | payable; returns `PriceFeed[]`; **does not store, does not emit** |
| `0xaccca7f9` | `parsePriceFeedUpdatesUnique(bytes[],bytes32[],uint64,uint64)` | payable; as above, rejects non-first updates |
| `0x3a229d18` | `parsePriceFeedUpdatesWithConfig(bytes[],bytes32[],uint64,uint64,bool,bool,bool)` | payable; stores and emits only when the last bool (`storeUpdatesIfFresh`) is true |
| `0xeb942158` | `parseTwapPriceFeedUpdates(bytes[],bytes32[])` | payable; TWAP; no store, no event |
| `0xd47eed45` | `getUpdateFee(bytes[])` | view |
| `0x5f674e35` | `getTwapUpdateFee(bytes[])` | view |
| `0xa4ae35e0` | `getPriceNoOlderThan(bytes32,uint256)` | view → `(int64 price, uint64 conf, int32 expo, uint256 publishTime)` |
| `0x96834ad3` | `getPriceUnsafe(bytes32)` | view, no staleness check |
| `0x711a2e28` | `getEmaPriceNoOlderThan(bytes32,uint256)` | view |
| `0x9474f45b` | `getEmaPriceUnsafe(bytes32)` | view |
| `0x31d98b3f` / `0xb5dcc911` | `getPrice(bytes32)` / `getEmaPrice(bytes32)` | deprecated views (still in bytecode) |
| `0xcaaf43f1` | `queryPriceFeed(bytes32)` | view |
| `0xb5ec0261` | `priceFeedExists(bytes32)` | view |
| `0xe18910a3` | `getValidTimePeriod()` | view (120 s on ETH, 60 s on Robinhood and Arc) |
| `0x48b6404d` | `singleUpdateFeeInWei()` | view (0 on ETH, Robinhood, Arc on 2026-10-30) |
| `0x978a800d` | `transactionFeeInWei()` | view |
| `0x84acd1bb` | `wormhole()` | view → the VAA verifier in use |
| `0x426234e4` | `governanceDataSource()` | view → `(uint16 chainId, bytes32 emitter)` |
| `0xa38d81c6` | `validDataSources()` | view |
| `0x437209a7` | `isValidDataSource(uint16,bytes32)` | view |
| `0x586d3cf8` | `lastExecutedGovernanceSequence()` | view |
| `0x9a8a0592` | `chainId()` | view (Wormhole chain id) |
| `0x54fd4d50` | `version()` | view |
| `0xe3795cc1` | `pythUpgradableMagic()` | view, returns `0x97a6f304` |
| `0xb6ed701e` | `executeGovernanceInstruction(bytes)` | **governance** (upgrade, fee, data source, valid period, wormhole address, withdraw fee) |
| `0x3659cfe6` / `0x4f1ef286` | `upgradeTo(address)` / `upgradeToAndCall(address,bytes)` | UUPS; `onlyOwner` and owner is 0, so they always revert |
| `0x8da5cb5b` | `owner()` | returns 0 |

### 2.2 Executor
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x09c5eabe` | `execute(bytes)` | payable; runs one governance VAA call on a target contract |
| `0xdf15ed7f` | `getOwnerChainId()` | view |
| `0x9ae6121e` | `getOwnerEmitterAddress()` | view |
| `0x905e35e7` | `getLastExecutedSequence()` | view |
| `0xcd3474d7` | `entropyUpgradableMagic()` | view (the Executor reuses this name) |

### 2.3 Wormhole receivers
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc0fd8bde` | `parseAndVerifyVM(bytes)` | view; called by Core on each update |
| `0x6606b4e0` | `submitNewGuardianSet(bytes)` | **guardian-set rotation** |
| `0x1cfe7951` | `getCurrentGuardianSetIndex()` | view |
| `0xf951975a` | `getGuardianSet(uint32)` | view |
| `0x9a8a0592` | `chainId()` | view |
| `0xfbe3c2cd` / `0xb172b222` | `governanceChainId()` / `governanceContract()` | view |

## 3. Addresses — all chains

All addresses below return non-empty code from `eth_getCode` on 2026-10-30. Implementation = EIP-1967 slot read live.

### 3.1 Pyth Core (the address integrators use)
| Chain | ID | Pyth Core | Implementation | `wormhole()` |
|-------|----|-----------|----------------|--------------|
| Ethereum | 1 | `0x4305FB66699C3B2702D4d05CF36551390A4c69C6` | `0x3f38404a2e3cb949bcdfa19a5c3bdf3fe375feb0` | `0x3a2DD09B4739D905183D503d594c8FB3e3D41820` |
| Base | 8453 | `0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a` | `0x30dc7d7ce20d5fe2b365cf23901ea327eb28a86f` | `0x581aaF059CC83A353fc51aDC9a0480FbeDFc6c55` |
| BNB | 56 | `0x4D7E825f80bDf85e913E0DD2A2D54927e9dE1594` | `0xf77705a55aa859a80f60b8d8c4a03d7f69d2d7ba` | `0x6E7D74FA7d5c90FEF9F0512987605a6d546181Bb` |
| Avalanche | 43114 | `0x4305FB66699C3B2702D4d05CF36551390A4c69C6` | `0x41c9e39574f40ad34c79f1c99b66a45efb830d4c` | `0x41955476936DdA8d0fA98b8d1778172F7E4fCcA1` (stable) |
| Arbitrum | 42161 | `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C` | `0x8391e5e91d27d1d89139bc94b27ed8b67a17a6cb` | `0x8d289CdD60E7F73F352F42c8524a06Ef1ad746f8` |
| Optimism | 10 | `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C` | `0xacfadacb95974c7729f3c910176a66ea88e32a80` | `0x237b7aFF1Af5d9F311f830234792d429355A58F3` |
| Polygon | 137 | `0xff1a0f4744e8582DF1aE09D5611b887B6a12925C` | `0x0402833a00e734821f74fa4bbded2f1759540519` | `0xf0a1b566B55e0A0CB5BeF52Eb2a57142617Bee67` |
| Robinhood | 4663 | `0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a` | `0x66e9cba5529824a03b5bc9931d9c63637101d0f7` | `0xb27e5ca259702f209a29225d0eDdC131039C9933` |
| Arc | 5042 | `0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a` | `0x66e9cba5529824a03b5bc9931d9c63637101d0f7` | `0xb27e5ca259702f209a29225d0eDdC131039C9933` |

Avalanche Core is live (version `1.4.6`, listed in the `EvmPriceFeedContracts.json` store). The docs page does not list Avalanche. Avalanche Core still uses the "stable" receiver.

### 3.2 Pyth Core Compatible
| Chain | Core Compatible | Implementation | `wormhole()` |
|-------|-----------------|----------------|--------------|
| Ethereum | `0x14b9932cc9AC8Ee03301665a8644A753f46D8552` | `0xe15357fb7ab31e091583b9c4b4135bb2f176f38e` | `0x3a2DD09B…1820` |
| Base | `0xbC16aee60f64864882BC6C4E428e148Fc0E272F5` | `0xd3add3fcbe708182ece01b732f52c76f866aad8e` | `0x581aaF05…6c55` |
| BNB | `0xdF21D137Aadc95588205586636710ca2890538d5` | `0x4374e5a8b9c22271e9eb878a2aa31de97df15daf` | `0x6E7D74FA…81Bb` |
| Arbitrum | `0xe15357fB7ab31E091583b9c4b4135BB2f176f38e` | `0x3a2dd09b4739d905183d503d594c8fb3e3d41820` | `0x8d289CdD…46f8` |
| Optimism | `0xa78951b6bADC9F4740f6f456E9144705D5C5E4B2` | `0x438b5a03f6460ccffa62d62f4ab554a740cfde9c` | `0x237b7aFF…58F3` |
| Polygon | `0x6E7D74FA7d5c90FEF9F0512987605a6d546181Bb` | `0xfa25e653b44586dbbe27ee9d252192f0e4956683` | `0xf0a1b566…Bee67` |

Not deployed on Avalanche, Robinhood Chain or Arc.

### 3.3 Wormhole receivers (Pyth-operated)
| Chain | Pro-compatible receiver (in use) | Stable receiver (earlier) |
|-------|----------------------------------|---------------------------|
| Ethereum | `0x3a2DD09B4739D905183D503d594c8FB3e3D41820` | `0x74f09cb3c7e2A01865f424FD14F6dc9A14E3e94E` |
| Base | `0x581aaF059CC83A353fc51aDC9a0480FbeDFc6c55` | `0x87047526937246727E4869C5f76A347160e08672` |
| BNB | `0x6E7D74FA7d5c90FEF9F0512987605a6d546181Bb` | `0x41955476936DdA8d0fA98b8d1778172F7E4fCcA1` |
| Avalanche | — | `0x41955476936DdA8d0fA98b8d1778172F7E4fCcA1` (in use by Core) |
| Arbitrum | `0x8d289CdD60E7F73F352F42c8524a06Ef1ad746f8` | `0xEbe57e8045F2F230872523bbff7374986E45C486` |
| Optimism | `0x237b7aFF1Af5d9F311f830234792d429355A58F3` | `0x87047526937246727E4869C5f76A347160e08672` |
| Polygon | `0xf0a1b566B55e0A0CB5BeF52Eb2a57142617Bee67` | `0x35a58BeeE77a2Ad547FcDed7e8CB1c6e19746b13` |
| Robinhood | `0xb27e5ca259702f209a29225d0eDdC131039C9933` | `0x87047526937246727E4869C5f76A347160e08672` |
| Arc | `0xb27e5ca259702f209a29225d0eDdC131039C9933` | `0x87047526937246727E4869C5f76A347160e08672` |

Live reads: pro-compatible receivers return `getCurrentGuardianSetIndex() = 1`; stable receivers return `7` (Avalanche, Robinhood). The receivers report Pyth's own chain ids: ETH 2, Avalanche 6, **Robinhood 60101, Arc 60102**. Governance chain = 1 (Solana).

### 3.4 Executor (governance)
| Chain | Executor | Implementation |
|-------|----------|----------------|
| Ethereum | `0xCcD7e24e71ba746CBc758C39CBAb11f4E0dfc46F` | `0x395921b642ba511d421ae834fef56ac886735ca2` |
| Base | `0xf0a1b566B55e0A0CB5BeF52Eb2a57142617Bee67` | `0x5d289ad1ce59fcc25b6892e7a303dfff3a9f7167` |
| BNB | `0x26DD80569a8B23768A1d80869Ed7339e07595E85` | `0x0708325268df9f66270f1401206434524814508b` |
| Arbitrum | `0x24654078A8E043e8985D962a5100CDfA2026f92C` | `0x4821932d0cdd71225a6d914706a621e0389d7061` |
| Optimism | `0x6E7D74FA7d5c90FEF9F0512987605a6d546181Bb` | `0xfa25e653b44586dbbe27ee9d252192f0e4956683` |
| Polygon | `0xEbe57e8045F2F230872523bbff7374986E45C486` | `0x41c9e39574f40ad34c79f1c99b66a45efb830d4c` |
| Robinhood | `0x0708325268dF9F66270F1401206434524814508b` | `0xebe57e8045f2f230872523bbff7374986e45c486` |
| Arc | `0x0708325268dF9F66270F1401206434524814508b` | `0xebe57e8045f2f230872523bbff7374986e45c486` |

No Executor is listed for Avalanche. Each Executor returns `owner() =` its own address.

## 4. Cross-chain summary

| Chain | Core | Core Compatible | Pro-compat. receiver | Executor | `PriceFeedUpdate` activity (2026-10-30) |
|-------|------|-----------------|----------------------|----------|------------------------------------------|
| Ethereum (1) | `0x4305…69C6` | `0x14b9…8552` | `0x3a2D…1820` | `0xCcD7…c46F` | 12 logs / 2,000 blocks |
| Base (8453) | `0x8250…487a` | `0xbC16…72F5` | `0x581a…6c55` | `0xf0a1…Bee67` | 21 / 2,000 |
| BNB (56) | `0x4D7E…1594` | `0xdF21…38d5` | `0x6E7D…81Bb` | `0x26DD…5E85` | 0 / 20,000 |
| Avalanche (43114) | `0x4305…69C6` | — | — (stable `0x4195…cCA1`) | — | 0 / 50,000 |
| Arbitrum (42161) | `0xff1a…925C` | `0xe153…f38e` | `0x8d28…46f8` | `0x2465…f92C` | 216 / 20,000 |
| Optimism (10) | `0xff1a…925C` | `0xa789…E4B2` | `0x237b…58F3` | `0x6E7D…81Bb` | 330 / 2,000 |
| Polygon (137) | `0xff1a…925C` | `0x6E7D…81Bb` | `0xf0a1…Bee67` | `0xEbe5…C486` | 0 / 20,000 |
| Robinhood (4663) | `0x8250…487a` | — | `0xb27e…9933` | `0x0708…508b` | 0 / 400,000 |
| Arc (5042) | `0x8250…487a` | — | `0xb27e…9933` | `0x0708…508b` | 0 / 100,000 |

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Pyth Core** | EIP-1967 UUPS (`ERC1967Proxy`, 680 B; 177 B on Robinhood and Arc) | impl slot `0x3608…2bbc` non-zero; admin slot empty | Governance VAA from Solana emitter `0x5635…2e9e` via `executeGovernanceInstruction`; emits `ContractUpgraded` + `Upgraded`. `owner() = 0`. |
| **Core Compatible** | EIP-1967 UUPS (177 B) | same | same as Core |
| **Wormhole receiver** | EIP-1967 proxy (177 B pro-compatible / 842 B stable) → `ReceiverImplementation` | same | Receiver governance VAAs (guardian sets) |
| **Executor** | EIP-1967 UUPS (177 B / 708 B) | same | Self-owned; upgraded by its own governance VAA |

The admin slot `0xb531…6103` is empty on every contract above. All are UUPS, not Transparent. Upgrade history (old implementations) was not read: the public RPCs refuse archive `eth_getLogs`.

## 6. Detection invariants & gotchas

1. **`0x2880aB155794e7179c9eE2e38200202908C17B43` is not a Pyth price feed on any target chain.** On Robinhood and Arc it holds 1,067 B with one function, `setup(address,address[],uint16,uint16,bytes32)` (`0x34a5fcd4`). That is the Wormhole-receiver `ReceiverSetup` helper used at deploy time. A 1,302 B variant sits at the same literal on Ethereum, Base and Optimism. It has no EIP-1967 slot. The real Core on Robinhood and Arc is `0x8250…487a`.
2. **Same literal, different role per chain.** `0x6E7D74FA…81Bb` is Entropy (Base), Core Compatible (Polygon), Executor (Optimism) and a Wormhole receiver (BNB). `0xdF21D137…38d5` is Entropy (Optimism) and Core Compatible (BNB). `0xf0a1b566…Bee67` is the Executor (Base) and a receiver (Polygon). `0xEbe57e80…C486` is the Executor (Polygon) and a stable receiver (Arbitrum). Always key by `(chain_id, address)`.
3. **Decoys at Core literals.** `0xff1a…925C` on Ethereum is a 680 B proxy with `version() = 0.1.0`, `owner() = 0xc42e9476b0a458097087336e2395dbf45b0bdc12`, `wormhole()` = Wormhole Core `0x98f3…288B`. It is not in any Pyth list and showed no logs. `0x4305…69C6` on BNB (15,427 B) and `0xff1a…925C` on Avalanche (15,473 B) are non-proxy implementation-type code with `version() = 0.1.0`. `0x8250…487a` on BNB and Avalanche is a 9,928 B receiver implementation; on Polygon it is the 1,302 B setup helper.
4. **`PriceFeedUpdate` fires only for fresher prices.** A stale update in `updatePriceFeeds` costs gas and fee but logs nothing for that id. The `parsePriceFeedUpdates*` paths log nothing unless `storeUpdatesIfFresh = true`.
5. **`price` and `conf` are raw integers.** The exponent (`expo`, `int32`) is not in the log. Read it with `getPriceUnsafe(id)`. Most USD feeds use `expo = -8`.
6. **Price ids are chain-agnostic `bytes32`.** For example, ETH/USD = `0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace` and BTC/USD = `0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43`. Filter `topic1` on these.
7. **The updater is not the consumer.** `tx.from` / `msg.sender` of `updatePriceFeeds` is a keeper, relayer or the protocol itself. Attribute use by the contract that reads the price in the same transaction.
8. **Two Core contracts on six chains.** A protocol can use Core or Core Compatible. Watch both for `PriceFeedUpdate`.
9. **The VAA verifier is a Pyth-operated receiver, not Wormhole Core.** A `WormholeAddressSet` log, or a `submitNewGuardianSet` call on the receiver, changes what signatures Core accepts. Treat both as critical. The receiver chain ids (Robinhood 60101, Arc 60102) differ from the Wormhole Core ids (72, 71).
10. **Governance is VAA-driven.** There is no owner key. Watch `executeGovernanceInstruction` calls and the events in §1.1. On the Executor, watch `execute(bytes)` calls.
11. **Robinhood and Arc show no use yet.** No `PriceFeedUpdate` log in the scanned windows (400,000 and 100,000 blocks). BNB, Polygon and Avalanche were also silent in the scanned windows. A first log on these chains is a useful "first integration" signal.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_PRICE_FEED_UPDATE          = '\xd06a6b7f4918494b3719217d1802786c1f5112a6c1d88fe2cfec00b4584f6aec'
TOPIC_CONTRACT_UPGRADED          = '\x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_GOVERNANCE_DATA_SOURCE_SET = '\x6bce23ef3d34e51710fe4700b43ba5f1733a6215c883f384671a4ece3ea8aa20'
TOPIC_DATA_SOURCES_SET           = '\xd451e0fcb7c5b9e13de533604d158069dad159841c45f39f09d379bfc423080d'
TOPIC_FEE_SET                    = '\x74dbbbe280ef27b79a8a0c449d5ae2ba7a31849103241d0f98df70bbc9d03e37'
TOPIC_TRANSACTION_FEE_SET        = '\x5ac11e113c4b7116e6d04c95bd9f5ec9109fc1199331c882f5a0b63c9b33ac2b'
TOPIC_VALID_PERIOD_SET           = '\xcdb88a22f82ddd76115ab7c66cf08eb1e40afe80c9b31017eb2cbdb1570b33ae'
TOPIC_WORMHOLE_ADDRESS_SET       = '\xd495c4e5b386d59bccca38a2277b5d70a0f5e47d7b6587a45a6f5aca221a3125'
TOPIC_FEE_WITHDRAWN              = '\x78473f3f373f7673597f4f0fa5873cb4d375fea6d4339ad6b56dbd411513cb3f'
TOPIC_BATCH_PRICE_FEED_UPDATE_LEGACY = '\x943f0e8a16c19895fb87cbeb1a349ed86d7f31923089dd36c1a1ed5e300f267b'
TOPIC_PRICE_FEED_UPDATE_LEGACY   = '\xef1f4c97783da7fc718b0334ca9b16bb0c5d1da6db75e96012b3613bb12707a0'
-- ===== Selectors (chain-agnostic) =====
SEL_UPDATE_PRICE_FEEDS           = '\xef9e5e28'
SEL_UPDATE_PRICE_FEEDS_IF_NEC    = '\xb9256d28'
SEL_PARSE_PRICE_FEED_UPDATES     = '\x4716e9c5'
SEL_PARSE_PRICE_FEED_UPDATES_UNIQUE = '\xaccca7f9'
SEL_PARSE_WITH_CONFIG            = '\x3a229d18'
SEL_PARSE_TWAP                   = '\xeb942158'
SEL_GET_PRICE_NO_OLDER_THAN      = '\xa4ae35e0'
SEL_GET_PRICE_UNSAFE             = '\x96834ad3'
SEL_EXECUTE_GOVERNANCE_INSTR     = '\xb6ed701e'
SEL_EXECUTOR_EXECUTE             = '\x09c5eabe'
SEL_RECEIVER_SUBMIT_GUARDIAN_SET = '\x6606b4e0'
SEL_RECEIVER_SETUP               = '\x34a5fcd4'
-- ===== Addresses: Pyth Core =====
ETH_PYTH_CORE   = '\x4305fb66699c3b2702d4d05cf36551390a4c69c6'
BASE_PYTH_CORE  = '\x8250f4af4b972684f7b336503e2d6dfedeb1487a'
BNB_PYTH_CORE   = '\x4d7e825f80bdf85e913e0dd2a2d54927e9de1594'
AVAX_PYTH_CORE  = '\x4305fb66699c3b2702d4d05cf36551390a4c69c6'
ARB_PYTH_CORE   = '\xff1a0f4744e8582df1ae09d5611b887b6a12925c'
OP_PYTH_CORE    = '\xff1a0f4744e8582df1ae09d5611b887b6a12925c'
POLY_PYTH_CORE  = '\xff1a0f4744e8582df1ae09d5611b887b6a12925c'
ROBIN_PYTH_CORE = '\x8250f4af4b972684f7b336503e2d6dfedeb1487a'
ARC_PYTH_CORE   = '\x8250f4af4b972684f7b336503e2d6dfedeb1487a'
-- ===== Addresses: Pyth Core Compatible =====
ETH_PYTH_CORE_COMPAT  = '\x14b9932cc9ac8ee03301665a8644a753f46d8552'
BASE_PYTH_CORE_COMPAT = '\xbc16aee60f64864882bc6c4e428e148fc0e272f5'
BNB_PYTH_CORE_COMPAT  = '\xdf21d137aadc95588205586636710ca2890538d5'
ARB_PYTH_CORE_COMPAT  = '\xe15357fb7ab31e091583b9c4b4135bb2f176f38e'
OP_PYTH_CORE_COMPAT   = '\xa78951b6badc9f4740f6f456e9144705d5c5e4b2'
POLY_PYTH_CORE_COMPAT = '\x6e7d74fa7d5c90fef9f0512987605a6d546181bb'
-- ===== Addresses: Wormhole receivers (pro-compatible, in use) =====
ETH_PYTH_WH_RECEIVER   = '\x3a2dd09b4739d905183d503d594c8fb3e3d41820'
BASE_PYTH_WH_RECEIVER  = '\x581aaf059cc83a353fc51adc9a0480fbedfc6c55'
BNB_PYTH_WH_RECEIVER   = '\x6e7d74fa7d5c90fef9f0512987605a6d546181bb'
AVAX_PYTH_WH_RECEIVER  = '\x41955476936dda8d0fa98b8d1778172f7e4fcca1'
ARB_PYTH_WH_RECEIVER   = '\x8d289cdd60e7f73f352f42c8524a06ef1ad746f8'
OP_PYTH_WH_RECEIVER    = '\x237b7aff1af5d9f311f830234792d429355a58f3'
POLY_PYTH_WH_RECEIVER  = '\xf0a1b566b55e0a0cb5bef52eb2a57142617bee67'
ROBIN_PYTH_WH_RECEIVER = '\xb27e5ca259702f209a29225d0eddc131039c9933'
ARC_PYTH_WH_RECEIVER   = '\xb27e5ca259702f209a29225d0eddc131039c9933'
-- ===== Addresses: Executor =====
ETH_PYTH_EXECUTOR   = '\xccd7e24e71ba746cbc758c39cbab11f4e0dfc46f'
BASE_PYTH_EXECUTOR  = '\xf0a1b566b55e0a0cb5bef52eb2a57142617bee67'
BNB_PYTH_EXECUTOR   = '\x26dd80569a8b23768a1d80869ed7339e07595e85'
ARB_PYTH_EXECUTOR   = '\x24654078a8e043e8985d962a5100cdfa2026f92c'
OP_PYTH_EXECUTOR    = '\x6e7d74fa7d5c90fef9f0512987605a6d546181bb'
POLY_PYTH_EXECUTOR  = '\xebe57e8045f2f230872523bbff7374986e45c486'
ROBIN_PYTH_EXECUTOR = '\x0708325268df9f66270f1401206434524814508b'
ARC_PYTH_EXECUTOR   = '\x0708325268df9f66270f1401206434524814508b'
-- ===== Decoy (NOT a price feed) =====
ROBIN_ARC_RECEIVER_SETUP_DECOY = '\x2880ab155794e7179c9ee2e38200202908c17b43'
```

## 8. Verification & sources

How the constants were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the canonical Solidity sources. Each Core selector and topic was found as a `PUSH4` / `PUSH32` constant in the live Base Core implementation `0x30dc…a86f`. `PriceFeedUpdate` was seen in live `eth_getLogs` on Ethereum, Base, Arbitrum and Optimism. `TwapPriceFeedUpdate` is absent from the implementation bytecode.
- **Addresses:** parsed from `contract_manager/src/store/contracts/EvmPriceFeedContracts.json`, `EvmWormholeContracts.json` and `EvmExecutorContracts.json`, and from the docs contract-address page. Each address was checked with `eth_getCode`, the EIP-1967 slots, and the views `version()`, `owner()`, `wormhole()`, `governanceDataSource()`, `getCurrentGuardianSetIndex()` and `chainId()`.
- **Chain coverage:** every Core literal was checked on all nine chains. Absences and decoys are listed in §6. Robinhood logs were read from `https://rpc.mainnet.chain.robinhood.com`. Arbitrum logs were read from `https://arb1.arbitrum.io/rpc`.
- **Not verified:** old implementations and upgrade dates (no archive log access); the legacy topics in §1.1.

Authoritative sources:
- [pyth-network/pyth-crosschain](https://github.com/pyth-network/pyth-crosschain) — `target_chains/ethereum/contracts/contracts/pyth/`, `.../wormhole-receiver/`, `.../executor/`, `target_chains/ethereum/sdk/solidity/IPyth.sol`, `IPythEvents.sol`, `contract_manager/src/store/`.
- [Pyth docs — EVM contract addresses](https://docs.pyth.network/price-feeds/contract-addresses/evm) (Pyth Pro / Pyth Core / Pyth Core Compatible columns; 2026-08-26 upgrade note).
- [Pyth price feed ids](https://docs.pyth.network/price-feeds/price-feeds).
- Explorers: [Etherscan](https://etherscan.io/address/0x4305FB66699C3B2702D4d05CF36551390A4c69C6) · [Basescan](https://basescan.org/address/0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a) · [BscScan](https://bscscan.com/address/0x4D7E825f80bDf85e913E0DD2A2D54927e9dE1594) · [Snowtrace](https://snowtrace.io/address/0x4305FB66699C3B2702D4d05CF36551390A4c69C6) · [Arbiscan](https://arbiscan.io/address/0xff1a0f4744e8582DF1aE09D5611b887B6a12925C) · [Optimistic Etherscan](https://optimistic.etherscan.io/address/0xff1a0f4744e8582DF1aE09D5611b887B6a12925C) · [Polygonscan](https://polygonscan.com/address/0xff1a0f4744e8582DF1aE09D5611b887B6a12925C).
