# Swaap Finance V2 — Topics, Selectors, Addresses (Ethereum, Arbitrum, Optimism, Base, Polygon, Avalanche, BNB)

**Status:** event topic0 hashes and function selectors computed locally with `cast keccak` / `cast sig` from canonical signatures read out of `swaap-labs/swaap-v2-monorepo` (GitHub). Addresses from `docs.swaap.finance` and on-chain verification via `cast` against `publicnode` RPCs on all seven chains. Vault `Swap` topic0 confirmed against live `eth_getLogs` on Ethereum Vault. SafeguardPool `Quote` topic0 confirmed against live logs from a deployed pool. See §8.
**Scope:** Swaap V2 — the Vault (Balancer V2 fork), SafeguardFactory, and SafeguardPool contracts. No V1 coverage here.

**Architecture in one sentence:** Swaap V2 uses the **Balancer V2 Vault architecture** verbatim — the Vault is the single token custodian, all swaps/joins/exits flow through it, and the Vault's event signatures are **byte-for-byte identical to Balancer V2**. SafeguardPools are pool contracts (not the Vault) that implement off-chain-oracle-signed RfQ pricing and MEV safeguards. To monitor Swaap V2 trade flow, watch **the Vault** (one address per chain) using the same topic0 constants you use for Balancer V2. Cross-reference [`balancer/v2.md`](../balancer/v2.md) for the full Balancer V2 Vault event/selector catalog.

**Key operational distinction — two Vault addresses:** Five chains (Ethereum, Arbitrum, Optimism, Polygon, Avalanche) use Vault A. Base and BNB use Vault B. Both vaults expose the identical Balancer V2 interface and emit identical events. SafeguardFactory is at the **same address** on all seven chains.

---

## 1. Topics (chain-agnostic)

### 1.1 Vault events (Balancer V2-compatible — identical topic0 to Balancer V2)

> These topic0s are **shared with Balancer V2** (`0xBA12222222228d8Ba445958a75a0704d566BF2C8` on Balancer). When monitoring a chain where both Balancer V2 and Swaap V2 are active, disambiguate by filtering on the Swaap Vault address. Full field documentation is in [`balancer/v2.md §1.1`](../balancer/v2.md).

| topic0 | Event |
|--------|-------|
| `0x2170c741c41531aec20e7c107c24eecfdd15e69c9bb0a8dd37b1840b9e0b207b` | `Swap(bytes32 indexed poolId, address indexed tokenIn, address indexed tokenOut, uint256 amountIn, uint256 amountOut)` |
| `0xe5ce249087ce04f05a957192435400fd97868dba0e6a4b4c049abf8af80dae78` | `PoolBalanceChanged(bytes32 indexed poolId, address indexed liquidityProvider, address[] tokens, int256[] deltas, uint256[] protocolFeeAmounts)` |
| `0x3c13bc30b8e878c53fd2a36b679409c073afd75950be43d8858768e956fbc20e` | `PoolRegistered(bytes32 indexed poolId, address indexed poolAddress, uint8 specialization)` |
| `0x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0` | `FlashLoan(address indexed recipient, address indexed token, uint256 amount, uint256 feeAmount)` |
| `0x94b979b6831a51293e2641426f97747feed46f17779fed9cd18d1ecefcfe92ef` | `AuthorizerChanged(address indexed newAuthorizer)` |

Decoding note: `poolId` is `bytes32` whose **leftmost 20 bytes are the pool (SafeguardPool) address**. `PoolBalanceChanged` covers both joins (positive `deltas`) and exits (negative `deltas`); there is no separate Join/Exit event.

### 1.2 SafeguardFactory events

| topic0 | Event | Source |
|--------|-------|--------|
| `0x83a48fbcfc991335314e74d0496aab6a1987e992ddc85dddbcc4d6dd6ef2e9fc` | `PoolCreated(address indexed pool)` | SafeguardFactory (inherited from Balancer V2 BasePoolFactory) |
| `0x432acbfd662dbb5d8b378384a67159b47ca9d0f1b79f97cf64cf8585fa362d50` | `FactoryDisabled()` | SafeguardFactory |

`PoolCreated` confirmed live on Ethereum: factory `0xCc74BD5d8D2d333D14475e022325555ebA3369B8`, first pool at block 19,982,113. Factory `isDisabled()` returns `false` on all seven chains (verified 2026-06).

### 1.3 SafeguardPool events (emitted by individual pool contracts, not the Vault)

All pools are `ISafeguardPool` instances deployed by SafeguardFactory.

| topic0 | Event |
|--------|-------|
| `0x9b97792d4bc68bb4ac03fb65cd7d887197ae9100c1afea4383f9700cf8637cfb` | `Quote(bytes32 indexed digest, uint256 amountIn18Decimals, uint256 amountOut18Decimals)` |
| `0x0360693e973e0cca2fb4e09d3d517e1bddc4bdbb401a6d120403202ba2b21b52` | `PerformanceUpdated(uint256 targetBalancePerPT0, uint256 targetBalancePerPT1, uint256 performance, uint256 amount0Per1, uint256 time)` |
| `0x67b9340be426386b69cd6d74afa4aec06726970f492cd88855d230cf524d2799` | `InitialTargetBalancesSet(uint256 targetBalancePerPT0, uint256 targetBalancePerPT1)` |
| `0x979f556c9fab717510419ccc86c2e610abdc5191df86a76452fcbe448ff8eada` | `ManagementFeesClaimed(uint256 feesClaimed, uint256 totalSupply, uint256 yearlyRate, uint256 time)` |
| `0xc303899b23ed608b0b3243487562369683a0f22b105947b09bbeaf3f12334f68` | `ManagementFeesUpdated(uint256 yearlyFees)` |
| `0x5719a5656c5cfdaafa148ecf366fd3b0a7fae06449ce2a46225977fb7417e29d` | `SignerChanged(address indexed signer)` |
| `0x5353e2cb47d505ba9b628610daec53fc41f3a4259dab35a757b0f1d5a58bc1c3` | `MustAllowlistLPsSet(bool mustAllowlistLPs)` |
| `0xc5c394480e369b1f18dbaea855a487eb9f83c383456fb556f6e008ccc8e44fd8` | `PegStatesUpdated(bool isPegged0, bool isPegged1)` |
| `0xade7a5f37979c66e55f0d696e105ef163c40331581eca3a3d399c52162c31546` | `FlexibleOracleStatesUpdated(bool isFlexibleOracle0, bool isFlexibleOracle1)` |
| `0x01d8e8b9de4fea0ef606c58397505991dae6d03096bc26958e9bc50f7a25cbda` | `PerfUpdateIntervalChanged(uint256 perfUpdateInterval)` |
| `0x052b55d74a98d63b6659acb8cae5ece25794c9346a8eff9601621afd32783aa1` | `MaxPerfDevChanged(uint256 maxPerfDev)` |
| `0x5613dc35dfd09ba708fb327e31f119dfef93f81873cccc15d42525c3d872bfdc` | `MaxTargetDevChanged(uint256 maxTargetDev)` |
| `0x1eaa1f4c1c4dbcfda59f3015400af158a9032de202bb1edb1f4ed263212da4b9` | `MaxPriceDevChanged(uint256 maxPriceDev)` |

`Quote` is the most important pool-level monitoring event: it fires on every executed swap, recording the signed digest and the normalized (18-decimal) amounts. It is emitted by the **pool contract**, while the corresponding token transfer is recorded by `Swap` on the Vault. `Quote` topic0 (`0x9b97792d...`) confirmed live against pool `0x7ac940038125796a7819652136c3f16db9b5568c` (Swaap WBTC-USDT Safeguard) on Ethereum.

---

## 2. Function selectors (chain-agnostic)

### 2.1 Vault

Struct expansions: `SingleSwap → (bytes32,uint8,address,address,uint256,bytes)`, `FundManagement → (address,bool,address,bool)`, `JoinPoolRequest/ExitPoolRequest → (address[],uint256[],bytes,bool)`.

| Selector | Function |
|----------|----------|
| `0x52bbbe29` | `swap((bytes32,uint8,address,address,uint256,bytes),(address,bool,address,bool),uint256,uint256)` |
| `0xb95cac28` | `joinPool(bytes32,address,address,(address[],uint256[],bytes,bool))` |
| `0x8bdb3913` | `exitPool(bytes32,address,address,(address[],uint256[],bytes,bool))` |
| `0x945bcec9` | `batchSwap(uint8,(bytes32,uint256,uint256,uint256,bytes)[],address[],(address,bool,address,bool),int256[],uint256)` |
| `0x5c38449e` | `flashLoan(address,address[],uint256[],bytes)` |
| `0xf6c00927` | `getPool(bytes32)` |
| `0xf94d4668` | `getPoolTokens(bytes32)` |
| `0x8d928af8` | `getVault()(address)` |
| `0x16c38b3c` | `setPaused(bool)` |
| `0x058a628f` | `setAuthorizer(address)` |
| `0x09b2760f` | `registerPool(uint8)` |
| `0x66a9c7d2` | `registerTokens(bytes32,address[],address[])` |
| `0x0e8e3e84` | `manageUserBalance((uint8,address,uint256,address,address)[])` |
| `0xfa6e671d` | `setRelayerApproval(address,address,bool)` |

### 2.2 SafeguardFactory

| Selector | Function |
|----------|----------|
| `0x1e860c13` | `create((string,string,address[],(address,uint256,bool,bool)[],(address,uint256,uint256,uint256,uint256,uint256,bool),bool),bytes32)` |
| `0x8d928af8` | `getVault()(address)` |
| `0x6c57f5a9` | `isDisabled()(bool)` |
| `0x6634b753` | `isPoolFromFactory(address)(bool)` |

### 2.3 SafeguardPool

| Selector | Function |
|----------|----------|
| `0x2a1d0a79` | `onSwap((bytes32,uint8,address,address,uint256,bytes),address,uint256,uint256)` |
| `0xd5c096c4` | `onJoinPool(bytes32,address,address,uint256[],uint256,uint256,bytes)` |
| `0x74f3b009` | `onExitPool(bytes32,address,address,uint256[],uint256,uint256,bytes)` |
| `0x1708a3f1` | `updatePerformance()` |
| `0x63843be4` | `evaluateStablesPegStates()` |
| `0x5c91bba0` | `claimManagementFees()` |
| `0x6c19e783` | `setSigner(address)` |
| `0x6484e410` | `setManagementFees(uint256)` |
| `0x45aafdca` | `setFlexibleOracleStates(bool,bool)` |
| `0x7b749c45` | `setMustAllowlistLPs(bool)` |
| `0x72dde816` | `setPerfUpdateInterval(uint256)` |
| `0xc7e50217` | `setMaxPerfDev(uint256)` |
| `0x68eda8c7` | `setMaxTargetDev(uint256)` |
| `0x5e54841a` | `setMaxPriceDev(uint256)` |

---

## 3. Addresses

### 3.1 Vault A — Ethereum, Arbitrum, Optimism, Polygon, Avalanche

**`0xd315a9C38eC871068FEC378E4Ce78AF528C76293`**

| Chain | Chain ID | Bytecode | WETH | Authorizer | ProtocolFeesCollector |
|-------|----------|----------|------|------------|-----------------------|
| Ethereum | 1 | 24,563 B | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` | `0xCA19Ed3182E6e591207E959de633a14825Cc123c` | `0xa0cC39203c048277E658FF861fafeD8E30E7bd18` |
| Arbitrum | 42161 | 24,563 B | `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` | `0xCA19Ed3182E6e591207E959de633a14825Cc123c` | `0xa0cC39203c048277E658FF861fafeD8E30E7bd18` |
| Optimism | 10 | 24,563 B | `0x4200000000000000000000000000000000000006` | `0xCA19Ed3182E6e591207E959de633a14825Cc123c` | `0xa0cC39203c048277E658FF861fafeD8E30E7bd18` |
| Polygon | 137 | 24,563 B | `0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270` (WMATIC) | `0xCA19Ed3182E6e591207E959de633a14825Cc123c` | `0xa0cC39203c048277E658FF861fafeD8E30E7bd18` |
| Avalanche | 43114 | 24,563 B | `0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7` (WAVAX) | `0xCA19Ed3182E6e591207E959de633a14825Cc123c` | `0xa0cC39203c048277E658FF861fafeD8E30E7bd18` |

Active swap activity confirmed: Ethereum (active), Optimism (active), Polygon (active). Arbitrum and Avalanche: code deployed and verified, zero recent swap events in sampled windows (may have lower activity).

### 3.2 Vault B — Base, BNB

**`0x03C01Acae3D0173a93d819efDc832C7C4F153B06`**

| Chain | Chain ID | Bytecode | WETH | Authorizer | ProtocolFeesCollector |
|-------|----------|----------|------|------------|-----------------------|
| Base | 8453 | 24,563 B | `0x4200000000000000000000000000000000000006` | `0xd315a9C38eC871068FEC378E4Ce78AF528C76293`* | `0x9892e3E984760e97dAEB30EacFb9f794DA8622B4` |
| BNB | 56 | 24,563 B | `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` (WBNB) | `0xCA19Ed3182E6e591207E959de633a14825Cc123c` | `0x9892e3E984760e97dAEB30EacFb9f794DA8622B4` |

*On Base the Authorizer contract happens to share the same address as Vault A on other chains (`0xd315a9C...`), but is a distinct deployment (Authorizer bytecode, ~3,281 B vs Vault's 24,563 B). Vault A address produces zero Swap events on Base. Both Vault B chains confirmed active (17 and 20 Swap events in sampled windows).

### 3.3 SafeguardFactory — all 7 chains

**`0xCc74BD5d8D2d333D14475e022325555ebA3369B8`** — same address on all 7 chains, confirmed.

| Chain | Bytecode | getVault() | isDisabled() |
|-------|----------|------------|--------------|
| Ethereum | 4,028 B | `0xd315a9C3…` (Vault A) | false |
| Arbitrum | 4,028 B | `0xd315a9C3…` (Vault A) | false |
| Optimism | 4,028 B | `0xd315a9C3…` (Vault A) | false |
| Polygon | 4,028 B | `0xd315a9C3…` (Vault A) | false |
| Avalanche | 4,028 B | `0xd315a9C3…` (Vault A) | false |
| Base | 4,028 B | `0x03C01Aca…` (Vault B) | false |
| BNB | 4,028 B | `0x03C01Aca…` (Vault B) | false |

### 3.4 Auxiliary contracts (Ethereum — Vault A chains share same addresses)

| Contract | Address | Notes |
|----------|---------|-------|
| Authorizer | `0xCA19Ed3182E6e591207E959de633a14825Cc123c` | Same on ETH/ARB/OP/POLY/AVAX and BNB |
| ProtocolFeesCollector (A) | `0xa0cC39203c048277E658FF861fafeD8E30E7bd18` | ETH/ARB/OP/POLY/AVAX; `vault()` → Vault A |
| ProtocolFeesCollector (B) | `0x9892e3E984760e97dAEB30EacFb9f794DA8622B4` | Base and BNB |

---

## 4. Proxy / upgradability

All Swaap V2 contracts are **immutable**. EIP-1967 implementation slot (`0x3608...bbc`) and admin slot (`0xb531...103`) both return `0x0` on Vault A (Ethereum, verified). SafeguardFactory EIP-1967 slot also returns `0x0`. The README states: *"All core smart contracts are immutable, and cannot be upgraded."* SafeguardPool instances are also immutable — deployed via factory CREATE2 with a salt.

---

## 5. Pool ID encoding

A Swaap V2 pool ID is a `bytes32` following the Balancer V2 convention:
- Bytes 0–19 (leftmost): pool contract address
- Bytes 20–21: pool specialization (SafeguardPools use `TWO_TOKEN = 2`)
- Bytes 22–31: sequential nonce assigned by the Vault at registration

Example: `0x5906fad82b9f9e9c90ed42ac6f163b2ea3538e41` `0002` `00000000000000000024` → pool `0x5906fAD82b9f9e9c90Ed42Ac6F163b2ea3538E41`, TWO_TOKEN, nonce 36.

All current SafeguardPools are **two-token pools** (enforced in `SafeguardPool` constructor with `_NUM_TOKENS = 2`).

---

## 6. Monitoring strategy

**Trade flow:** watch the Vault address for `Swap` (topic0 `0x2170c741…`) and optionally `PoolBalanceChanged` (topic0 `0xe5ce2490…`). Filter `poolId` to scope to specific Swaap pools; decode the pool address from the first 20 bytes of `poolId`.

**New pool detection:** watch SafeguardFactory (`0xCc74BD5d8D2d333D14475e022325555ebA3369B8`) for `PoolCreated` (topic0 `0x83a48fbc…`). The pool address is `topics[1]` (as a 32-byte left-padded address).

**Per-pool state monitoring:** watch individual SafeguardPool addresses for:
- `Quote` (`0x9b97792d…`) — every executed quote/swap, includes normalized amounts and signed digest
- `PerformanceUpdated` (`0x0360693e…`) — periodic rebalancing signal
- `ManagementFeesClaimed` (`0x979f556c…`) — fee extraction
- `SignerChanged` (`0x5719a565…`) — signer rotation (critical security event)

**MEV safeguards:** SafeguardPool validates that swaps are accompanied by a valid off-chain signed quote (via `SignatureSafeguard`). The `Quote` event records the digest of each accepted signature. `MaxPriceDevChanged`, `MaxPerfDevChanged`, `MaxTargetDevChanged` events record changes to the protection parameters.

---

## 7. Quick-copy bytea (topic0 / selector hex)

```
-- Vault events (Balancer V2-compatible)
SWAP_VAULT            = 0x2170c741c41531aec20e7c107c24eecfdd15e69c9bb0a8dd37b1840b9e0b207b
POOL_BALANCE_CHANGED  = 0xe5ce249087ce04f05a957192435400fd97868dba0e6a4b4c049abf8af80dae78
POOL_REGISTERED       = 0x3c13bc30b8e878c53fd2a36b679409c073afd75950be43d8858768e956fbc20e
FLASH_LOAN            = 0x0d7d75e01ab95780d3cd1c8ec0dd6c2ce19e3a20427eec8bf53283b6fb8e95f0
AUTHORIZER_CHANGED    = 0x94b979b6831a51293e2641426f97747feed46f17779fed9cd18d1ecefcfe92ef

-- SafeguardFactory events
FACTORY_POOL_CREATED  = 0x83a48fbcfc991335314e74d0496aab6a1987e992ddc85dddbcc4d6dd6ef2e9fc
FACTORY_DISABLED      = 0x432acbfd662dbb5d8b378384a67159b47ca9d0f1b79f97cf64cf8585fa362d50

-- SafeguardPool events
QUOTE                 = 0x9b97792d4bc68bb4ac03fb65cd7d887197ae9100c1afea4383f9700cf8637cfb
PERFORMANCE_UPDATED   = 0x0360693e973e0cca2fb4e09d3d517e1bddc4bdbb401a6d120403202ba2b21b52
MGMT_FEES_CLAIMED     = 0x979f556c9fab717510419ccc86c2e610abdc5191df86a76452fcbe448ff8eada
MGMT_FEES_UPDATED     = 0xc303899b23ed608b0b3243487562369683a0f22b105947b09bbeaf3f12334f68
SIGNER_CHANGED        = 0x5719a5656c5cfdaafa148ecf366fd3b0a7fae06449ce2a46225977fb7417e29d
MUST_ALLOWLIST_SET    = 0x5353e2cb47d505ba9b628610daec53fc41f3a4259dab35a757b0f1d5a58bc1c3
PEG_STATES_UPDATED    = 0xc5c394480e369b1f18dbaea855a487eb9f83c383456fb556f6e008ccc8e44fd8
MAX_PRICE_DEV_CHANGED = 0x1eaa1f4c1c4dbcfda59f3015400af158a9032de202bb1edb1f4ed263212da4b9
MAX_PERF_DEV_CHANGED  = 0x052b55d74a98d63b6659acb8cae5ece25794c9346a8eff9601621afd32783aa1
MAX_TARGET_DEV_CHANGED= 0x5613dc35dfd09ba708fb327e31f119dfef93f81873cccc15d42525c3d872bfdc
INIT_TARGET_BALANCES  = 0x67b9340be426386b69cd6d74afa4aec06726970f492cd88855d230cf524d2799

-- Vault addresses
VAULT_A = 0xd315a9C38eC871068FEC378E4Ce78AF528C76293  -- ETH/ARB/OP/POLY/AVAX
VAULT_B = 0x03C01Acae3D0173a93d819efDc832C7C4F153B06  -- Base/BNB

-- SafeguardFactory (all 7 chains)
FACTORY = 0xCc74BD5d8D2d333D14475e022325555ebA3369B8

-- Vault selectors
swap        = 0x52bbbe29
joinPool    = 0xb95cac28
exitPool    = 0x8bdb3913
batchSwap   = 0x945bcec9
flashLoan   = 0x5c38449e

-- Factory selector
create      = 0x1e860c13
```

---

## 8. On-chain verification log

All checks performed with `cast` against `publicnode` RPCs (2026-06).

| Check | Result |
|-------|--------|
| Vault A bytecode on ETH/ARB/OP/POLY/AVAX | 49,128 hex chars = 24,563 B ✓ |
| Vault B bytecode on Base/BNB | 49,128 hex chars = 24,563 B ✓ |
| SafeguardFactory bytecode on all 7 chains | 8,058 hex chars = 4,028 B ✓ |
| Vault A EIP-1967 impl slot (Ethereum) | `0x0` — immutable ✓ |
| Vault A EIP-1967 admin slot (Ethereum) | `0x0` — immutable ✓ |
| Factory EIP-1967 slot (Ethereum) | `0x0` — immutable ✓ |
| Vault A `WETH()` Ethereum | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` ✓ |
| Vault A `getProtocolFeesCollector()` (5 chains) | `0xa0cC39203c048277E658FF861fafeD8E30E7bd18` (same) ✓ |
| Vault A `getAuthorizer()` (5 chains) | `0xCA19Ed3182E6e591207E959de633a14825Cc123c` (same) ✓ |
| Vault B `getAuthorizer()` Base | `0xd315a9C38eC871068FEC378E4Ce78AF528C76293` (Authorizer, not Vault A on Base) ✓ |
| Vault B `getAuthorizer()` BNB | `0xCA19Ed3182E6e591207E959de633a14825Cc123c` ✓ |
| Factory `getVault()` Ethereum | `0xd315a9C38eC871068FEC378E4Ce78AF528C76293` (Vault A) ✓ |
| Factory `getVault()` Base | `0x03C01Acae3D0173a93d819efDc832C7C4F153B06` (Vault B) ✓ |
| Factory `isDisabled()` all 7 chains | `false` ✓ |
| `Swap` topic0 `0x2170c741…` live on Eth Vault | confirmed (≥10 events in ~500-block window) ✓ |
| `Quote` topic0 `0x9b97792d…` live on pool `0x7ac940…` | confirmed (27 events in ~5,000-block window) ✓ |
| `PoolCreated` topic0 `0x83a48fbc…` from Factory Eth | confirmed (block 19,982,113, pool `0xac4e8d8b…`) ✓ |

**Sources:** `swaap-labs/swaap-v2-monorepo` (GitHub), `docs.swaap.finance`, Chainsecurity/Quantstamp audit reports (referenced in monorepo `audits/` folder).
