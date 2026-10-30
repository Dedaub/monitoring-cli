# Pyth Entropy (randomness) — Topics, Selectors, Addresses (Base, Arbitrum, Optimism)

**Status:** verified against live RPC on all nine target chains, the Fortuna chain API and the canonical `pyth-network/pyth-crosschain` repo on 2026-10-30.
**Scope:** the Pyth **Entropy** commit-reveal random-number contract (`EntropyUpgradable`, `version() = 2.0.0`). Deployed on Base (8453), Arbitrum One (42161) and Optimism (10) only. **Not deployed** on Ethereum, BNB, Avalanche, Polygon, Robinhood Chain or Arc. Topics and selectors are chain-agnostic. Addresses are network-specific.

A user contract calls `requestV2` (or the v1 `requestWithCallback`) with a fee. A provider (default `0x52DeaA1c84233F7bb8C8A45baeDE41091c616506`, run by the Fortuna keeper) later calls `revealWithCallback`. Entropy computes the random number and calls `entropyCallback` on the user contract. The fee is split between the provider and Pyth.

**The live contract emits two logs for each action:** the v1 event (struct-carrying) and the v2 event. A request gives `RequestedWithCallback` (v1) **and** `Requested` (v2). A reveal gives `RevealedWithCallback` (v1) **and** `Revealed` (v2). Count one family only, or you double-count.

---

## 1. Topics (chain-agnostic)

`REQ` = `(address provider, uint64 sequenceNumber, uint32 numHashes, bytes32 commitment, uint64 blockNumber, address requester, bool useBlockhash, bool isRequestWithCallback)`.
`PI` = `(uint128,uint128,bytes32,uint64,bytes,bytes,uint64,uint64,bytes32,uint64,address,uint32)` (ProviderInfo).

### 1.1 Request / reveal (v2 — preferred)
| topic0 | Event |
|--------|-------|
| `0x209bbfee3369097c31c36ce42994bdcac394866c881f603fb6296f240d6c37db` | `Requested(address indexed provider, address indexed caller, uint64 indexed sequenceNumber, bytes32 userContribution, uint32 gasLimit, bytes extraArgs)` |
| `0x2231996cc9de260d163cd345089fea7819252b40215c738556aa144a0a11ed47` | `Revealed(address indexed provider, address indexed caller, uint64 indexed sequenceNumber, bytes32 randomNumber, bytes32 userContribution, bytes32 providerContribution, bool callbackFailed, bytes callbackReturnValue, uint32 callbackGasUsed, bytes extraArgs)` |

### 1.2 Request / reveal (v1 — still emitted)
| topic0 | Event |
|--------|-------|
| `0xa4c85ab66677ced5caabbbba151714887944b9e0fee05f320e42a1b13a01fbc6` | `RequestedWithCallback(address indexed provider, address indexed requestor, uint64 indexed sequenceNumber, bytes32 userRandomNumber, REQ request)` |
| `0x40be225f151772416d8785647e5641a0b53507623d0ee3fb88802b7d6bdbf728` | `RevealedWithCallback(REQ request, bytes32 userRandomNumber, bytes32 providerRevelation, bytes32 randomNumber)` |
| `0x20e2c2fc72b2cb9fbae9d7d8fd4bdf5bdcc4579043e1e9854e2baf045b6a31d3` | `Requested(REQ request)` — v1 non-callback `request()` |
| `0x39c729f66b0c8aa543d92bc83fb7e0914c9701326b96365b593f28ba706976e4` | `Revealed(REQ request, bytes32 userRevelation, bytes32 providerRevelation, bytes32 blockHash, bytes32 randomNumber)` — v1 `reveal()` |
| `0xc73c4cbf6f2bace8893b1283ee0e044c059ef9b80765820f4cc22b5ace139b5b` | `CallbackFailed(address indexed provider, address indexed requestor, uint64 indexed sequenceNumber, bytes32 userRandomNumber, bytes32 providerRevelation, bytes32 randomNumber, bytes errorCode)` |

### 1.3 Provider management (v2 / v1 pairs)
| v2 topic0 (`…, bytes extraArgs`, provider indexed) | v1 topic0 | Event |
|----|----|----|
| `0xb5ca2dfb0bd25603299b76fefa9fbe3abdc9f951bdfb7ffd208f93ab7f8e203c` | `0x641f45ac488304746c653e2635855e73663a6e524de1194447d678a58f084012` | `Registered(address indexed, bytes)` / `Registered(PI)` |
| `0x2b876e4a8eb641937e15aa02b7b90d376ce4661b51337661d76d330d23aed536` | `0x40873158a9e1446599b5dee14bfd652e53a6f48605dab5aaac3b8a12a56c7fce` | `ProviderFeeUpdated(address,uint128,uint128[,bytes])` |
| `0x92ec5e11b09fd199655525004a1861acf5dd00f3a672ea8c750ec8bbf7ef6190` | `0xeb28196cc9984ca7d8c99b41fa943501351706fda54b50f983e60fdc08aa94a0` | `ProviderDefaultGasLimitUpdated(address,uint32,uint32[,bytes])` |
| `0x61e70b9f3f2fcdff8071ea3b7dba108a38e7c1e59d0d9ddf60462a6c4cee85ea` | `0x1efad1d69168ff2e29c45661eed77d2de2b8c95f412cd22a65b15a38e24f7088` | `ProviderUriUpdated(address,bytes,bytes[,bytes])` |
| `0xbdb4fa4c43ffef3ac259c0c209d3cecacc9579c559ec0273193f24d416c64377` | `0x2c0fa560a1e6d11854f3f965d262e756c1b6d23d2bfe8f0e54b7807dd79b946b` | `ProviderFeeManagerUpdated(address,address,address[,bytes])` |
| `0x506807cbd0dcbf141d2ec9b63b6891a27db1eb2d769dffe38cce227ff6a704f4` | `0x6a5a36f1400b17f2daef49faa26a5133cbcc952cffc0e7f426f3c84d6d207f60` | `ProviderMaxNumHashesAdvanced(address,uint32,uint32[,bytes])` |
| `0x1df589989558acb66e48be55ae76b555f1075333b1ced9e827a685ae2821967f` | `0x02128911bc7070fd6c100b116c2dd9a3bb6bf132d5259a65ca8d0c86ccd78f49` | `Withdrawal(address provider, address recipient, uint128 withdrawnAmount[,bytes])` — provider fee withdrawal |

### 1.4 Governance / admin
| topic0 | Event |
|--------|-------|
| `0xb73e06a6ae37bdd616d5087ef40ccc7ca25ea84e7cfa93dbf9a2815e2cdde674` | `PythFeeSet(uint256 oldPythFee, uint256 newPythFee)` |
| `0x3db81271b05fbf6a656114a99415fdfd27fadb1a34c9a139eb029fba4f6dfdb0` | `DefaultProviderSet(address oldDefaultProvider, address newDefaultProvider)` — high signal |
| `0xed2d93e7985747cd1a4a093c2cc3bb73d0f177b81bdfd26020e8f20a97e8112e` | `NewAdminProposed(address oldAdmin, address newAdmin)` |
| `0x30aa44298c9615f6e2b6a1ca5e3802ca71d535856c686bb638c161636da6fde7` | `NewAdminAccepted(address oldAdmin, address newAdmin)` |
| `0x78473f3f373f7673597f4f0fa5873cb4d375fea6d4339ad6b56dbd411513cb3f` | `FeeWithdrawn(address targetAddress, uint256 amount)` — Pyth fee withdrawal; same topic0 as Pyth Core |
| `0x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49` | `ContractUpgraded(address oldImplementation, address newImplementation)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed, address indexed)` |

## 2. Function signatures (chain-agnostic)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7b43155d` | `requestV2()` | payable; default provider, default gas limit |
| `0x0bed189f` | `requestV2(uint32)` | payable; gas limit |
| `0x0e33da29` | `requestV2(address,uint32)` | payable; provider, gas limit |
| `0xf77b45e1` | `requestV2(address,bytes32,uint32)` | payable; provider, user random number, gas limit |
| `0x19cb825f` | `requestWithCallback(address,bytes32)` | payable; v1 |
| `0x93cbf217` | `request(address,bytes32,bool)` | payable; v1, no callback |
| `0x3d30bc0e` | `revealWithCallback(address,uint64,bytes32,bytes32)` | provider keeper; runs the user callback |
| `0x9371df51` | `reveal(address,uint64,bytes32,bytes32)` | v1, no callback |
| `0x8204b67a` | `getFeeV2()` | view (also `0xca1642e1` `getFeeV2(uint32)`, `0x7ab2ac36` `getFeeV2(address,uint32)`) |
| `0xb88c9148` | `getFee(address)` | view, v1 |
| `0x82ee990c` | `getDefaultProvider()` | view |
| `0x754a3600` | `getRequestV2(address,uint64)` | view |
| `0x2f9b787b` | `getProviderInfoV2(address)` | view |
| `0xc970835c` | `getAccruedPythFees()` | view |
| `0x38b049c6` | `register(uint128,bytes32,bytes,uint64,bytes)` | provider registration |
| `0x02387a7b` | `withdraw(uint128)` | provider withdraws fees |
| `0x308fe218` | `withdrawAsFeeManager(address,uint128)` | provider fee manager withdraws |
| `0xace63a7e` / `0xc03c035d` | `setProviderFee(uint128)` / `setProviderFeeAsFeeManager(address,uint128)` | provider |
| `0xb469f1c9` / `0x472d35b9` / `0x84a96f7e` / `0x524b6f70` | `setProviderUri(bytes)` / `setFeeManager(address)` / `setMaxNumHashes(uint32)` / `setDefaultGasLimit(uint32)` | provider |
| `0x96f0d6e4` | `advanceProviderCommitment(address,uint64,bytes32)` | provider |
| `0xe15dbddc` | `setPythFee(uint128)` | owner or admin |
| `0xde4478ec` | `setDefaultProvider(address)` | owner or admin |
| `0xf1ef21c3` | `withdrawFee(address,uint128)` | owner or admin; Pyth fees out |
| `0x147bf6c4` / `0x0e18b681` | `proposeAdmin(address)` / `acceptAdmin()` | admin handover |
| `0x6e9960c3` | `getAdmin()` | view |
| `0x3659cfe6` / `0x4f1ef286` | `upgradeTo(address)` / `upgradeToAndCall(address,bytes)` | owner only (UUPS) |
| `0xcd3474d7` | `entropyUpgradableMagic()` | view |

## 3. Addresses

All checked with `eth_getCode` on 2026-10-30. `getDefaultProvider()` returns `0x52DeaA1c84233F7bb8C8A45baeDE41091c616506` on all three.

| Chain | ID | Entropy | Implementation | `owner()` (= Pyth Executor) |
|-------|----|---------|----------------|-----------------------------|
| Base | 8453 | `0x6E7D74FA7d5c90FEF9F0512987605a6d546181Bb` | `0x4ced698548f7d068f2f6e92d66f404a8a10db83b` | `0xf0a1b566B55e0A0CB5BeF52Eb2a57142617Bee67` |
| Arbitrum | 42161 | `0x7698E925FfC29655576D0b361D75Af579e20AdAc` | `0x5ee2d7398ce35a591c30d736007feda8f4cfec95` | `0x24654078A8E043e8985D962a5100CDfA2026f92C` |
| Optimism | 10 | `0xdF21D137Aadc95588205586636710ca2890538d5` | `0x16392b49ea47d4a21bb17f69aa9e7ad570284838` | `0x6E7D74FA7d5c90FEF9F0512987605a6d546181Bb` |

**Absent:** Ethereum, BNB, Avalanche, Polygon, Robinhood Chain and Arc have no Entropy contract. Neither `EvmEntropyContracts.json` nor the Fortuna `/v1/chains` API lists them. The Entropy literals on those chains are empty or hold other Pyth contracts (see gotcha 3).

## 4. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Entropy** | EIP-1967 UUPS (708 B proxy) | impl slot non-zero; admin slot empty; implementation 23,925 B | `owner()` = the chain's Pyth Executor (governance VAA). A separate `admin` can set fees and the default provider. Upgrade emits `ContractUpgraded` + `Upgraded`. |

## 5. Detection invariants & gotchas

1. **Dual emission.** Each request logs v1 `RequestedWithCallback` and v2 `Requested`. Each reveal logs v1 `RevealedWithCallback` and v2 `Revealed`. Live on Base: 403 requests and 402 reveals in 20,000 blocks, each in matched pairs.
2. **Name collisions across versions.** `Requested`, `Revealed`, `Registered`, `ProviderFeeUpdated` and `Withdrawal` each have two topic0s (v1 and v2). Pick by topic0, not by name.
3. **Address reuse.** `0x6E7D74FA…81Bb` is Entropy on Base but the Executor on Optimism, Core Compatible on Polygon and a Wormhole receiver on BNB. `0xdF21D137…38d5` is Entropy on Optimism but Core Compatible on BNB. Key by `(chain_id, address)`.
4. **Callback failure is not a revert.** In v2, `Revealed.callbackFailed = true` marks a failed user callback. v1 logs `CallbackFailed` instead.
5. **`caller` is the consumer contract.** In v2 `Requested` / `Revealed`, `caller` (topic2) is the contract that asked for randomness. `tx.from` of a reveal is the provider keeper.
6. **Provider exposure.** `DefaultProviderSet` changes who every `requestV2()` call trusts. Treat it as critical.

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics =====
TOPIC_ENTROPY_REQUESTED_V2          = '\x209bbfee3369097c31c36ce42994bdcac394866c881f603fb6296f240d6c37db'
TOPIC_ENTROPY_REVEALED_V2           = '\x2231996cc9de260d163cd345089fea7819252b40215c738556aa144a0a11ed47'
TOPIC_ENTROPY_REQUESTED_WITH_CB_V1  = '\xa4c85ab66677ced5caabbbba151714887944b9e0fee05f320e42a1b13a01fbc6'
TOPIC_ENTROPY_REVEALED_WITH_CB_V1   = '\x40be225f151772416d8785647e5641a0b53507623d0ee3fb88802b7d6bdbf728'
TOPIC_ENTROPY_CALLBACK_FAILED_V1    = '\xc73c4cbf6f2bace8893b1283ee0e044c059ef9b80765820f4cc22b5ace139b5b'
TOPIC_ENTROPY_PROVIDER_FEE_UPDATED_V2 = '\x2b876e4a8eb641937e15aa02b7b90d376ce4661b51337661d76d330d23aed536'
TOPIC_ENTROPY_WITHDRAWAL_V2         = '\x1df589989558acb66e48be55ae76b555f1075333b1ced9e827a685ae2821967f'
TOPIC_ENTROPY_PYTH_FEE_SET          = '\xb73e06a6ae37bdd616d5087ef40ccc7ca25ea84e7cfa93dbf9a2815e2cdde674'
TOPIC_ENTROPY_DEFAULT_PROVIDER_SET  = '\x3db81271b05fbf6a656114a99415fdfd27fadb1a34c9a139eb029fba4f6dfdb0'
TOPIC_ENTROPY_NEW_ADMIN_ACCEPTED    = '\x30aa44298c9615f6e2b6a1ca5e3802ca71d535856c686bb638c161636da6fde7'
TOPIC_CONTRACT_UPGRADED             = '\x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49'
-- ===== Selectors =====
SEL_ENTROPY_REQUEST_V2              = '\x7b43155d'
SEL_ENTROPY_REQUEST_V2_GAS          = '\x0bed189f'
SEL_ENTROPY_REQUEST_V2_PROV_GAS     = '\x0e33da29'
SEL_ENTROPY_REQUEST_V2_FULL         = '\xf77b45e1'
SEL_ENTROPY_REQUEST_WITH_CALLBACK   = '\x19cb825f'
SEL_ENTROPY_REVEAL_WITH_CALLBACK    = '\x3d30bc0e'
SEL_ENTROPY_SET_DEFAULT_PROVIDER    = '\xde4478ec'
SEL_ENTROPY_WITHDRAW_FEE            = '\xf1ef21c3'
-- ===== Addresses =====
BASE_PYTH_ENTROPY   = '\x6e7d74fa7d5c90fef9f0512987605a6d546181bb'
ARB_PYTH_ENTROPY    = '\x7698e925ffc29655576d0b361d75af579e20adac'
OP_PYTH_ENTROPY     = '\xdf21d137aadc95588205586636710ca2890538d5'
PYTH_ENTROPY_DEFAULT_PROVIDER = '\x52deaa1c84233f7bb8c8a45baede41091c616506'
```

## 7. Verification & sources

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `EntropyEvents.sol`, `EntropyEventsV2.sol`, `EntropyStructs.sol`, `IEntropy.sol`, `IEntropyV2.sol` and `EntropyGovernance.sol`. All selectors and all topics except `RequestedWithCallback` were found as constants in the live Base implementation. `RequestedWithCallback`, `Requested` (v2), `RevealedWithCallback`, `Revealed` (v2) and both `ProviderFeeUpdated` topics were seen in live Base logs (latest at block 53,286,392).
- **Addresses:** from `contract_manager/src/store/contracts/EvmEntropyContracts.json` and the Fortuna API `https://fortuna.dourolabs.app/v1/chains/configs`. Checked with `eth_getCode`, the EIP-1967 slot, `version()`, `owner()` and `getDefaultProvider()`.

Sources:
- [pyth-network/pyth-crosschain — entropy_sdk/solidity](https://github.com/pyth-network/pyth-crosschain/tree/main/target_chains/ethereum/entropy_sdk/solidity) and [contracts/entropy](https://github.com/pyth-network/pyth-crosschain/tree/main/target_chains/ethereum/contracts/contracts/entropy)
- [Pyth docs — Entropy chainlist](https://docs.pyth.network/entropy/chainlist)
- Explorers: [Basescan](https://basescan.org/address/0x6E7D74FA7d5c90FEF9F0512987605a6d546181Bb) · [Arbiscan](https://arbiscan.io/address/0x7698E925FfC29655576D0b361D75Af579e20AdAc) · [Optimistic Etherscan](https://optimistic.etherscan.io/address/0xdF21D137Aadc95588205586636710ca2890538d5)
