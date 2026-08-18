# Orbiter Finance MDC / Decentralized Arbitration (OB_ReturnCabin) — Topics, Selectors (chain-agnostic)

**Status:** event/function signatures recomputed locally as `keccak256(...)` against the canonical `Orbiter-Finance/OB_ReturnCabin` Solidity sources (interfaces + libraries) on 2026-06-09. **Deployed addresses are NOT published** in the official docs or repo (deploy scripts read them from env), and the public-RPC nodes used here block topic-only `eth_getLogs`, so per-chain deployment presence for this framework could **not** be existence-checked on-chain — see §5. The live, high-volume bridge surface (routers + Maker EOAs + OPool) is documented separately in [core.md](./core.md).
**Scope:** the `OB_ReturnCabin` "Maker Deposit Contract" (MDC) framework — Orbiter's on-chain **optimistic-rollup-style arbitration / margin / challenge** system. Topics + selectors are **chain-agnostic** and verifiable from source; addresses are network-specific and unverified here. This file exists because the MDC contracts are a **clearly separate generation/product line** from the EOA+router bridge.

`OB_ReturnCabin` is Orbiter's **decentralized maker** design: instead of trusting a Maker to pay out, a Maker pre-deposits **margin** into an **MDC (Maker Deposit Contract)**, registers **rules** (which source→dest transfers it serves and at what price), and if it fails to honour a transfer a Sender can **challenge** on-chain. Challenges are resolved by an **EBC (Event Binding Contract)** that computes the expected target tx from the source tx, and an **SPV** (`ORChallengeSpv` + `ORSpvData`) that proves the source tx occurred — historically a ZK-SPV light client. The system is built from:

- **`ORMDCFactory`** — deploys one **`ORMakerDeposit`** (MDC) proxy per Maker via CREATE2 (`createMDC()` → deterministic address from the maker). Emits `MDCCreated(maker, mdc)`.
- **`ORMakerDeposit`** — the per-Maker MDC: holds margin, manages rules roots, SPV/responseMaker config, and the `challenge`/`checkChallenge`/`verifyChallengeSource`/`verifyChallengeDest` dispute lifecycle.
- **`ORManager`** — global registry/governance: chain info, token info, EBC allowlist, SPV-data contract pointer, protocol/challenge fee params.
- **`ORFeeManager`** — dealer/submitter revenue: dealer fee ratios, submitter margin registration, revenue-tree submissions, withdrawals.
- **`ORSpvData`** — stores historical block roots (`HistoryBlocksRootSaved`) used by the SPV proofs.
- **`ORExtraTransfer`** / **EBC** (`IOREventBinding`) / **`ORChallengeSpv`** — helpers / rule-decoding / proof verification.

Per the repo's `ORMDCFactory`, the per-Maker MDCs are **CREATE2 clones** behind the factory's `implementation()`; `ORManager`/`ORFeeManager`/`ORSpvData` are deployed as upgradeable contracts in the Hardhat scripts. **None of these addresses are pinned in the public repo or docs** — treat presence as unconfirmed until an `MDCCreated` log or a factory address is observed on the target chain.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 ORMDCFactory (`IORMDCFactory`)

| topic0 | Event |
|--------|-------|
| `0x9aa4d864969550a6e3ca3ad73ca5b23e37fb87c6817a71a30cebc8fd7cdbd7c6` | `MDCCreated(address maker, address mdc)` |

`MDCCreated` is the **discovery anchor**: each new per-Maker MDC is announced here. Index this topic on the factory address to enumerate all live MDCs.

### 1.2 ORMakerDeposit / MDC (`IORMakerDeposit`)

| topic0 | Event |
|--------|-------|
| `0x8be6a6805a6d0644a1441caf6cd521d524d1678f15c122c02382b708b09b525e` | `WithdrawRequested(uint256 requestAmount, uint64 requestTimestamp, address requestToken)` |
| `0x3cb86960d27f10c36827a013566ea74ce60fe0402128cb82d020889177c12429` | `ColumnArrayUpdated(address indexed impl, bytes32 columnArrayHash, address[] dealers, address[] ebcs, uint64[] chainIds)` |
| `0x8f2bbe31353a40442717cf80cfd6882db22eae2e1ca9ffd699967549fd26fafc` | `SpvUpdated(address indexed impl, uint64 chainId, address spv)` |
| `0x0b91b68f980e47803e7858fa5a270c37d18f436399f86db162b14fbd0f376d54` | `ResponseMakersUpdated(address indexed impl, uint256[] responseMakers)` |
| `0x14ebfe1d09c7ff607d095a4d8c41180cfc5ce6a29321b1b0b8ed086408acca4a` | `RulesRootUpdated(address indexed impl, address ebc, (bytes32 root, uint32 version) rootWithVersion)` |
| `0x1cf9b9f121ee5926c69fe70cbd7482b0d10e60431ba4f285fd6ce12b19c0aa0f` | `ChallengeInfoUpdated(bytes32 indexed challengeId, ChallengeStatement statement, ChallengeResult result)` |

> `ChallengeInfoUpdated` is the **dispute lifecycle event** — fires on `challenge`, `checkChallenge`, `verifyChallengeSource`, and `verifyChallengeDest`. `ChallengeStatement` = `(uint256,uint64,address,uint64,uint256,uint256,uint64,uint64,uint64,uint64,uint128)`; `ChallengeResult` = `(address,uint64,uint64,uint64,bytes32)`. Watch this topic on an MDC to catch a Sender disputing an unfulfilled bridge transfer.

### 1.3 ORManager (`IORManager`)

| topic0 | Event |
|--------|-------|
| `0xb503bd02757fd8a8ae859e560bbc7a6b236aba166b403d0ea2c34921070b37cb` | `ChainInfoUpdated(uint64 indexed id, (uint64,uint192,uint64,uint64,uint64,uint64,uint256,address[]) chainInfo)` |
| `0x52482770013d9905a43b78b74a47c7f9d1949c15b715cc5ca2c1c34105d73cf4` | `ChainTokenUpdated(uint64 indexed id, (uint256,address,uint8) tokenInfo)` |
| `0xcbff3ca58b9beaa25c60a25b8918d5f5843eb71b89a913668181999e2e945ae9` | `EbcsUpdated(address[] ebcs, bool[] statuses)` |
| `0x5bbca2dc437948624b3ad08825ce6201cbab5ba6eefc840acc7031080cd31637` | `SpvDataContractUpdated(address spvDataContract)` |

`ORManager` also declares (signatures verifiable from `IORManager.sol`, topics omitted for brevity): `SubmitterFeeUpdated(address)`, `ProtocolFeeUpdated(uint64)`, `MinChallengeRatioUpdated(uint64)`, `ChallengeUserRatioUpdated(uint64)`, `FeeChallengeSecondUpdated(uint64)`, `FeeTakeOnChallengeSecondUpdated(uint64)`, `MaxMDCLimitUpdated(uint64)`, `ExtraTransferContractsUpdated(uint64[],uint256[])`.

### 1.4 ORFeeManager (`IORFeeManager`)

| topic0 | Event |
|--------|-------|
| `0x477dfd24160e8774a01758d43787dbb93ed9a6c79f15f8f640dfee7e0ebe0e85` | `DealerUpdated(address indexed dealer, uint256 feeRatio, bytes extraInfo)` |
| `0x78283e8ede6f0ee246101a5bd1e6a9e86bdb3b44f3142f9caf2f9d149926c931` | `SubmitterRegistered(address indexed submitter, uint256 marginAmount)` |
| `0xb0c9c17767e446fa28426081136370521e93205e6fd5180573080cfac9b69509` | `Withdraw(address indexed user, uint64 chainId, address token, uint256 debt, uint256 amount)` |
| `0xe427c182f349e706d5bd82644a18e14a5fcaf69a93ae9534164984df8cfdc33a` | `ETHDeposit(address indexed sender, uint256 amount)` |

`ORFeeManager` additionally declares `SubmissionUpdated(...)` (multi-field; see `IORFeeManager.sol`).

### 1.5 ORSpvData (`IORSpvData`)

| topic0 | Event |
|--------|-------|
| `0xa0931ef79bb27304f1e23de0015fa57daf588e65d343788faa6415a3cdd7fd37` | `HistoryBlocksRootSaved(uint256 indexed startBlockNumber, bytes32 blocksRoot, uint256 blockInterval)` |
| `0x0411a4c5f1ca9d6be36cb6a46f7bc31bd7661cd5f696c372b7d50bb3497a0cc9` | `BlockIntervalUpdated(uint64 blockInterval)` |
| `0x410ee710833ae831ae659691f03ec28e9dc5793a8f36e2ce69437e26dc8ff7cf` | `InjectOwnerUpdated(address injectOwner)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 ORMDCFactory

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0693288d` | `createMDC()` | Deploys the caller's per-Maker MDC (CREATE2). Emits `MDCCreated`. |
| `0xc596c28f` | `predictMDCAddress()` → `address` | Deterministic MDC address for the caller. |
| `0xc5e8cf25` | `mdcCreatedTotal()` → `uint256` | Count of MDCs created. |
| — | `manager()` → `address` / `implementation()` → `address` | Factory wiring (selectors per ABI). |

### 2.2 ORMakerDeposit (MDC)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc4d66de8` | `initialize(address owner_)` | One-shot proxy init (OZ). |
| `0x47e7ef24` | `deposit(address token, uint256 amount)` | `payable`. Add margin to the MDC. |
| `0x1dbe6d89` | `withdrawRequest(address requestToken, uint256 requestAmount)` | Start a margin withdrawal (timelock). Emits `WithdrawRequested`. |
| `0x51cff8d9` | `withdraw(address token)` | Complete a margin withdrawal after the request matures. |
| `0x9f73019f` | `updateRulesRoot(uint64,address,(...)[],(bytes32,uint32),uint64[],uint256[])` | Set/replace the Maker's rules merkle root. Emits `RulesRootUpdated`. |
| `0x4fdea68e` | `challenge(uint64 sourceTxTime, uint64 sourceChainId, uint64 sourceTxBlockNum, uint64 sourceTxIndex, bytes32 sourceTxHash, bytes32 ruleKeyHash, address freezeToken, uint256 freezeAmount1, uint256 parentNodeNumOfTargetNode)` | `payable`. Sender disputes an unfulfilled transfer. Emits `ChallengeInfoUpdated`. |
| `0x55027e75` | `checkChallenge(uint64 sourceChainId, bytes32 sourceTxHash, address[] challengers)` | Resolve/abort a challenge. |
| — | `verifyChallengeSource(...)` / `verifyChallengeDest(...)` | SPV-proof verification legs of the dispute. |
| — | `updateSpvs(uint64,address[],uint64[])` / `updateResponseMakers(uint64,bytes[])` / `updateColumnArray(uint64,address[],address[],uint64[])` | Maker config (emit `SpvUpdated` / `ResponseMakersUpdated` / `ColumnArrayUpdated`). |

### 2.3 ORManager / ORFeeManager / ORSpvData

State-changing setters mirror their events (e.g. `ORManager.updateChainInfo*`, `registerEbcs`, `updateSpvDataContract`; `ORFeeManager.updateDealer`, `registerSubmitter`, `submit`, `withdraw`; `ORSpvData.saveHistoryBlocksRoots`). Compute exact selectors from `contracts/interface/IORManager.sol`, `IORFeeManager.sol`, `IORSpvData.sol` if a specific setter must be monitored.

---

## 3. Proxies & deployment pattern

| Contract | Pattern (per repo) | Notes |
|----------|--------------------|-------|
| **ORMakerDeposit (MDC)** | **CREATE2 minimal/clone behind `ORMDCFactory.implementation()`** | One per Maker; `initialize(owner_)` sets the Maker. Address = `predictMDCAddress()` (deterministic from maker). Verify the impl/clone pattern on the live deployment before assuming EIP-1167 vs EIP-1967. |
| **ORManager / ORFeeManager / ORSpvData** | Upgradeable (Hardhat deploy scripts use upgradeable patterns) | EIP-1967 impl slot `0x3608…2bbc` should be read live once an address is known; watch `Upgraded(address)` (`0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`). |
| **OrbiterXRouter / OPool / Maker EOAs** | (separate — [core.md](./core.md)) | Not part of this framework. |

---

## 4. Detection invariants & gotchas

1. **This is NOT the dominant flow.** The live, high-volume Orbiter bridge runs on Maker EOAs + `OrbiterXRouter` ([core.md](./core.md)). The MDC/arbitration system is the *decentralized-maker* design; on-chain activity for it is sparse-to-absent on the seven target chains unless/until a factory is found there.
2. **Discover MDCs via `MDCCreated`** (`0x9aa4d864…`) on the factory, then index each MDC for `deposit`/`withdrawRequest`/`withdraw`/`ChallengeInfoUpdated`. There is no single global event stream.
3. **`ChallengeInfoUpdated` (`0x1cf9b9f1…`) is the risk signal** — a fired challenge means a Sender alleges an unfulfilled bridge transfer (margin at stake). Its struct args (`ChallengeStatement`/`ChallengeResult`) are exact as in §1.2; a wrong struct ⇒ wrong topic0.
4. **Tuple-event topics depend on exact struct field order/types.** `ChainInfoUpdated`, `ChainTokenUpdated`, `RulesRootUpdated`, `ChallengeInfoUpdated` were computed from the repo's `BridgeLib`/`RuleLib`/`IORMakerDeposit` structs — re-derive if the deployed version differs.
5. **Addresses unconfirmed.** Do not hard-code an MDC/factory/manager address from this doc — none are published. Obtain the factory from an `MDCCreated` emitter or the team, then `eth_getCode`-verify and read the EIP-1967 slot for the upgradeable singletons.
6. **`deposit(address,uint256)` selector `0x47e7ef24` collides** with countless other "deposit" functions across DeFi — only meaningful when the `to` is a known MDC. Key on `(chainId, mdc_address, selector)`.

---

## 5. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic; from OB_ReturnCabin source) =====
TOPIC_MDC_CREATED             = '\x9aa4d864969550a6e3ca3ad73ca5b23e37fb87c6817a71a30cebc8fd7cdbd7c6'
TOPIC_WITHDRAW_REQUESTED      = '\x8be6a6805a6d0644a1441caf6cd521d524d1678f15c122c02382b708b09b525e'
TOPIC_COLUMN_ARRAY_UPDATED    = '\x3cb86960d27f10c36827a013566ea74ce60fe0402128cb82d020889177c12429'
TOPIC_SPV_UPDATED             = '\x8f2bbe31353a40442717cf80cfd6882db22eae2e1ca9ffd699967549fd26fafc'
TOPIC_RESPONSE_MAKERS_UPDATED = '\x0b91b68f980e47803e7858fa5a270c37d18f436399f86db162b14fbd0f376d54'
TOPIC_RULES_ROOT_UPDATED      = '\x14ebfe1d09c7ff607d095a4d8c41180cfc5ce6a29321b1b0b8ed086408acca4a'
TOPIC_CHALLENGE_INFO_UPDATED  = '\x1cf9b9f121ee5926c69fe70cbd7482b0d10e60431ba4f285fd6ce12b19c0aa0f'
TOPIC_CHAIN_INFO_UPDATED      = '\xb503bd02757fd8a8ae859e560bbc7a6b236aba166b403d0ea2c34921070b37cb'
TOPIC_CHAIN_TOKEN_UPDATED     = '\x52482770013d9905a43b78b74a47c7f9d1949c15b715cc5ca2c1c34105d73cf4'
TOPIC_EBCS_UPDATED            = '\xcbff3ca58b9beaa25c60a25b8918d5f5843eb71b89a913668181999e2e945ae9'
TOPIC_SPV_DATA_CONTRACT_UPD   = '\x5bbca2dc437948624b3ad08825ce6201cbab5ba6eefc840acc7031080cd31637'
TOPIC_FEE_DEALER_UPDATED      = '\x477dfd24160e8774a01758d43787dbb93ed9a6c79f15f8f640dfee7e0ebe0e85'
TOPIC_FEE_SUBMITTER_REGISTERED= '\x78283e8ede6f0ee246101a5bd1e6a9e86bdb3b44f3142f9caf2f9d149926c931'
TOPIC_FEE_WITHDRAW            = '\xb0c9c17767e446fa28426081136370521e93205e6fd5180573080cfac9b69509'
TOPIC_FEE_ETH_DEPOSIT         = '\xe427c182f349e706d5bd82644a18e14a5fcaf69a93ae9534164984df8cfdc33a'
TOPIC_SPV_HISTORY_ROOT_SAVED  = '\xa0931ef79bb27304f1e23de0015fa57daf588e65d343788faa6415a3cdd7fd37'
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Selectors =====
SEL_CREATE_MDC                = '\x0693288d'   -- createMDC()
SEL_PREDICT_MDC_ADDRESS       = '\xc596c28f'   -- predictMDCAddress()
SEL_MDC_DEPOSIT               = '\x47e7ef24'   -- deposit(address,uint256)
SEL_MDC_WITHDRAW_REQUEST      = '\x1dbe6d89'   -- withdrawRequest(address,uint256)
SEL_MDC_WITHDRAW              = '\x51cff8d9'   -- withdraw(address)
SEL_MDC_UPDATE_RULES_ROOT     = '\x9f73019f'   -- updateRulesRoot(uint64,address,(...)[],(bytes32,uint32),uint64[],uint256[])
SEL_MDC_CHALLENGE             = '\x4fdea68e'   -- challenge(uint64,uint64,uint64,uint64,bytes32,bytes32,address,uint256,uint256)
SEL_MDC_CHECK_CHALLENGE       = '\x55027e75'   -- checkChallenge(uint64,bytes32,address[])
SEL_MDC_INITIALIZE            = '\xc4d66de8'   -- initialize(address)

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT            = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
```

---

## 6. Verification & sources

How constants were verified (2026-06-09):

- **Topic0 / selectors** recomputed locally as `keccak256(canonical signature)` (and `[0:4]`) from the exact event/function declarations in the canonical `Orbiter-Finance/OB_ReturnCabin` repo: `contracts/interface/{IORMDCFactory,IORMakerDeposit,IORManager,IORFeeManager,IORSpvData}.sol`, with tuple types resolved from `contracts/library/{BridgeLib,RuleLib}.sol` (`ChainInfo`, `TokenInfo`, `RootWithVersion`) and the `ChallengeStatement`/`ChallengeResult` structs in `IORMakerDeposit.sol`. Field order/types were read directly from source so tuple-event topics are byte-exact for that repo revision.
- **Addresses: NOT verified.** The repo's deploy scripts (`scripts/deploy.ts`, `.env.example` `OR_MANAGER_ADDRESS`/`OR_MDC_FACTORY_ADDRESS`) read addresses from environment; no mainnet address is committed, and the official docs do not list MDC/factory/manager addresses. The public RPC nodes used for [core.md](./core.md) reject topic-only `eth_getLogs` (require an address), so an `MDCCreated`-based discovery scan could not be run here. **Per-chain presence of this framework on the seven targets is therefore UNCONFIRMED.**
- **Proxy pattern** inferred from `ORMDCFactory` (CREATE2 clone of `implementation()`) and the upgradeable Hardhat deploy scripts; **read the live EIP-1967 slot once a concrete address is known.**

Authoritative sources:
- Repo — [`Orbiter-Finance/OB_ReturnCabin`](https://github.com/Orbiter-Finance/OB_ReturnCabin) (`contracts/`, `contracts/interface/`, `contracts/library/`, `scripts/deploy.ts`).
- Docs — [Bridge Protocol](https://docs.orbiter.finance/welcome/bridge-protocol) (MDC / EBC / SPV roles, dealer/submitter/maker definitions).
