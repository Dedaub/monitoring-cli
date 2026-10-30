# Aero (MetaDEX03) — Topics, Selectors, Addresses (Base, Ethereum, Optimism, Arbitrum, Robinhood Chain, Arc)

**Status:** verified against live RPC on every listed chain and the canonical `dromos-labs/metadex-public` + `dromos-labs/metadex-slipstream-public` repos (`deployment-addresses/*.json`, release 1.1.0 of 2026-10-21) on 2026-10-30.
**Scope:** **Aero**, the unified DEX that replaces Aerodrome (Base) and Velodrome (Optimism). The code calls it MetaDEX03. This file covers the V2 pools (volatile + stable), the Slipstream concentrated-liquidity (CL) pools, gauges, the sAERO voting escrow, the root Voter and the per-chain LeafVoter, the new AERO token, the Hyperlane messaging layer, the Metarouter, the Relay stack and the Aerodrome/Velodrome migration contracts. Chains: Base (8453, root), Ethereum (1), Optimism (10), Arbitrum One (42161), Robinhood Chain (4663), Arc (5042). Topics and selectors are chain-agnostic. Addresses are network-specific.

Aero is a **new deployment, not an upgrade**. It has a new AERO token (`0x3f5bF3Ed…a4Ee` on Base), new factories, new pools and a new escrow. The legacy Aerodrome contracts ([`amm.md`](amm.md), [`slipstream.md`](slipstream.md)) and the legacy Velodrome contracts ([`../velodrome/`](../velodrome/README.md)) stay on chain, but their gauges are killed (see §0.1). Aero launched on 2026-10-21: the Base factories were configured at block 52,880,042 (02:23 UTC) and the Minter started emissions at `ACTIVATION_TIMESTAMP` 1792627200 (2026-10-22 00:00 UTC).

**Hub-and-spoke model.** Base is the **root** chain. Only Base has the AERO token, the `VotingEscrow` (sAERO), the root `Voter`, the `Minter` and the migration contracts. Every chain, Base included, runs the same **leaf** stack: a `LeafVoter`, pool and gauge factories, a `ReceiptToken` ("xAERO") and a Hyperlane adapter. On Base the leaf adapter calls the root directly. On other chains the root and the leaf exchange messages through Hyperlane. Gauge claims mint canonical AERO on Base and xAERO on the other chains; a holder burns xAERO on the leaf (`redeem`) to get AERO on Base. The root `Voter.chains()` returns 8453, 10, 1, 42161, 57073 (Ink), 4663, 5042. Ink is a leaf chain outside the nine target chains.

**Immutable, clone-based.** No Aero contract is an EIP-1967 proxy (impl and admin slots are `0x0` on every core contract). Pools and gauges are 45 B EIP-1167 clones of a per-chain implementation. Many addresses are identical on all six chains (CreateX deployments). Other addresses come from per-chain deployer nonces, and **the same literal has different roles on different chains** (see §11). Always key on `(chainId, address)`.

---

## 0. Contract families & versions

| Family | Contracts | Chains |
|---|---|---|
| V2 pools | `VolatilePoolFactory`, `StablePoolFactory`, pool implementations, `PoolTape`, fee modules (`CustomFeeModule`, `FlatFeeQuoter`, `PriorityFeeMevTaxModule`, `DiscountRegistry`) | all six |
| CL pools (Slipstream) | `CLFactory`, `CLPool` implementation, `NonfungiblePositionManager` (symbol `AERO-CL`), `SwapRouter`, `Metaquoter`, `DynamicSwapFeeHook`, `CustomUnstakedFeeModule`, `LpMigrator` | all six (+ the 2026-09-15 "lite" CL stack on Arc) |
| Gauges | `GaugeManager`, `V2Gauge` volatile/stable factories, `CLGaugeFactory`, `GovernanceCreationModule`, `VotingRewardsFactory` (one `VotingRewardsManager` per gauge) | all six |
| Leaf governance | `LeafVoter`, `LeafEmissionsHandler`, `ReceiptToken` (xAERO), `FactoryRegistry`, `TokenRegistry` + `TokenNFT`, `LeafMessageOrchestrator`, `HyperlaneAdapter` | all six |
| Root governance | AERO `Token`, `VotingEscrow` (sAERO, ERC-721), `Voter`, `Minter`, `Splitter`, `VoterPaymentsModule`, `RootMessageOrchestrator`, one root adapter per leaf chain | Base only |
| Routing | `Metarouter` (batched swaps, LP, staking, bridging) | all six |
| Relay | `RelayFactory`, `MaxiRelay` / `ProtocolRelay` implementations, `RelayTape`; `RelayLeafModuleDeployer` on leaves | Base (+ leaf deployer elsewhere) |
| Migration | `AerodromeMigration` (Base), `VelodromeMigration` (Optimism) → `VelodromeMigrationEntrypoint` (Base) | Base, Optimism |

**Versions.** `metadex-public` 1.0.0 (2026-09-15) and `metadex-slipstream-public` 1.0.1 were deployed only on Arc ("lite launch": V2 factories, CL factory, NFPM, SwapRouter, Metarouter). Release 1.1.0 (2026-10-21) is the full deployment on all chains. On Arc the lite CL factory stays live and now points at the 1.1.0 `LeafVoter` (see §8).

### 0.1 Legacy Aerodrome / Velodrome status and migration path

- **Gauges killed.** On Base the legacy Aerodrome Voter `0x16613524…80A5` emitted 950 `GaugeKilled` logs in blocks 52,918,274–52,918,331 (2026-10-21 23:38 UTC). A sample of 8 of 2,013 Aerodrome gauges and 8 of 846 Velodrome gauges (Optimism Voter `0x41C914ee…bF3C`) all return `isAlive() = false` on 2026-10-30. Legacy pools get no new emissions.
- **Pools still trade.** The legacy `PoolFactory` contracts are not paused (`isPaused() = false` on Base and Optimism). Legacy pools and CL pools keep their liquidity until LPs withdraw. Keep the legacy topics in a monitor until the liquidity is gone.
- **Token migration.** `AerodromeMigration` `0x22a2F734…6721` (Base) converts legacy AERO `0x940181a9…8631` and veAERO `0xeBf418Fe…e6B4` into new AERO / sAERO at **1:1**. `VelodromeMigration` `0x6daE95FE…66c0` (Optimism) takes VELO `0x9560e827…88Db` and veVELO `0xFAf8FD17…787d`, and sends a Hyperlane message to `VelodromeMigrationEntrypoint` `0x6daE95FE…66c0` (Base), which pays **0.044 AERO per VELO** (`_RATIO_PIPS = 44_000` / 1e6; on chain `paidBasis` 1,616,337,471 VELO ↔ `paid` 71,118,848 AERO). veNFT migration opened at `MIGRATION_OPEN` = 1792620000 (2026-10-21 22:00 UTC); liquid migration opens one epoch later (2026-10-22 00:00 UTC). There is no on-chain end date. The owner can pause the contract and burn the rest (`RemainingBurned`).
- **Exchange windows are not on-chain events.** Exchanges announced their own conversion windows (Coinbase 2026-11-02 to 11-04; Kraken 2026-11-02 to 11-06). Those windows do not change any contract.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 V2 Pool (volatile + stable; each pool clone emits these)
| topic0 | Event |
|---|---|
| `0xb3e2773606abfd36b5bd91394b3a54d1398336c65005baf7bf7a05efeffaf75b` | `Swap(address indexed sender, address indexed to, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out)` — same topic0 as legacy Aerodrome/Velodrome |
| `0x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee` | `Mint(address indexed sender, address indexed to, uint256 amount0, uint256 amount1)` — **new 4-arg layout** (legacy: `Mint(address,uint256,uint256)` `0x4c209b5f…`) |
| `0x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2` | `Burn(address indexed sender, address indexed to, uint256 amount0, uint256 amount1)` |
| `0xcf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a` | `Sync(uint256 reserve0, uint256 reserve1)` |
| `0x112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602` | `Fees(address indexed sender, uint256 amount0, uint256 amount1)` |
| `0xcd5e4f020ddad29434c2200a9edf2f8d7ec30f0d787f03b528ab7279aab0acbe` | `Claim(address indexed caller, address indexed account, address indexed recipient, uint256 amount0, uint256 amount1)` — **new** (legacy 4-arg `0x865ca08d…`) |

### 1.2 Pool factories
| topic0 | Event |
|---|---|
| `0xebbbe9dc3a19d2f959ac76ac0372b4983cdfb945f5d6aef4873c36fabb2ba8aa` | `PoolCreated(address indexed token0, address indexed token1, address pool, uint256)` — **V2 factories; no `bool stable`** (the factory tells you the curve). Legacy `0x2128d88d…` is NOT emitted. |
| `0xab0d57f0df537bb25e80245ef7748fa62353808c54d6e528a9dd20887aed9ac2` | `PoolCreated(address indexed token0, address indexed token1, int24 indexed tickSpacing, address pool)` — CLFactory; same topic0 as legacy Slipstream |

### 1.3 CL Pool (Slipstream) — core events identical to Uniswap V3
| topic0 | Event |
|---|---|
| `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67` | `Swap(address indexed sender, address indexed recipient, int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)` |
| `0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde` | `Mint(address sender, address indexed owner, int24 indexed tickLower, int24 indexed tickUpper, uint128 amount, uint256 amount0, uint256 amount1)` |
| `0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c` | `Burn(address indexed owner, int24 indexed tickLower, int24 indexed tickUpper, uint128 amount, uint256 amount0, uint256 amount1)` |
| `0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0` | `Collect(address indexed owner, address recipient, int24 indexed tickLower, int24 indexed tickUpper, uint128 amount0, uint128 amount1)` |
| `0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633` | `Flash(address indexed sender, address indexed recipient, uint256 amount0, uint256 amount1, uint256 paid0, uint256 paid1)` |
| `0x205860e66845f2bbc0966bfab80db9bf93fca93862ea2b9fcf6945748352b4a3` | `CollectFees(address indexed recipient, uint128 amount0, uint128 amount1)` — gauge fee withdrawal (Slipstream-only) |

### 1.4 NonfungiblePositionManager (`AERO-CL`)
| topic0 | Event |
|---|---|
| `0x0f8712c47eb813e705bf827a60bdd551e6f2e055b4a1c2004304d52208a5a513` | `IncreaseLiquidity(uint256 indexed tokenId, uint128 liquidity, uint256 amount0, uint256 amount1, int24 tickLower, int24 tickUpper)` — **6 args; differs from Uniswap V3 / legacy Slipstream** `0x3067048b…` |
| `0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4` | `DecreaseLiquidity(uint256 indexed tokenId, uint128 liquidity, uint256 amount0, uint256 amount1)` |
| `0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01` | `Collect(uint256 indexed tokenId, address recipient, uint256 amount0, uint256 amount1)` |

### 1.5 Gauges (`GaugeManager`, `V2Gauge`, `CLGauge`)
| topic0 | Event |
|---|---|
| `0x5f80f043755ffb5732901cef69b9d5b7b1f7ec964176939d229d5f28daee9944` | `GaugeCreated(address indexed target, address indexed gauge, address indexed module, address gaugeFactory, address votingRewardsManager, address creator, bool activated)` — `GaugeManager`; `target` = pool |
| `0x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62` | `Deposit(address indexed caller, address indexed account, uint256 amount)` — V2Gauge (same topic0 as the Velodrome superchain LeafGauge) |
| `0x9b1bfa7fa9ee420a16e124f794c35ac9f90472acc99140eb2f6447c714cad8eb` | `Withdraw(address indexed caller, address indexed account, uint256 amount)` — V2Gauge |
| `0x41a8f9b73fc5b26eed668484bc6e1ca460c33a1be2aaf9cc8d6ae0f6dd67a968` | `EmissionsClaimed(address indexed account, address indexed recipient, uint256 rewardAmount)` — V2Gauge |
| `0xc9817c7b5bf7b2417ea338292b8681857834d37427fbb1899f98e6897f3fe426` | `Deposit(address indexed caller, address indexed user, uint256 indexed tokenId, uint128 liquidityToStake)` — CLGauge |
| `0xac2f121be0a440c47693663f2118f4d3b12cf85696cbe2c7a1b4a35e68a827d2` | `Withdraw(address indexed caller, address indexed user, uint256 indexed tokenId, uint128 liquidityToStake)` — CLGauge |
| `0x7b6bd720815adbeaaaed4fc759e1a535705901f33709fbb33e62ee9a89427bb1` | `EmissionsClaimed(address indexed account, uint256 indexed tokenId, address indexed recipient, uint256 rewardAmount)` — CLGauge |
| `0xbc567d6cbad26368064baa0ab5a757be46aae4d70f707f9203d9d9b6c8ccbfa3` | `ClaimFees(address indexed caller, uint256 claimed0, uint256 claimed1)` — both gauge types |

### 1.6 VotingEscrow (sAERO, ERC-721; Base only)
| topic0 | Event |
|---|---|
| `0xc13ddc6db8fcc061bb7b8ae6a27b66f196765478b3771aca81eebdb10fce052c` | `Deposit(address indexed provider, uint256 indexed tokenId, uint8 indexed depositType, uint128 value, uint256 unstakeTime, uint256 ts)` — differs from legacy veAERO `0x8835c22a…` |
| `0xb110efbb1c6c959f8710077145fec647d8ecc07d3d7c17e9868625a01c057455` | `Withdraw(address indexed provider, uint256 indexed tokenId, uint128 value, uint256 ts)` |
| `0x69251eb8eddb5ee229358aa71344347425044f6ec0d5384ce1fa077709cdd7ae` | `Supply(uint128 supply)` |
| `0xefd7eb052ddecc0a606ba787bdfcc18fa4f9c8440da558f10074598c8f5f0574` | `UpgradeToPermanentStake(address indexed owner, uint256 indexed tokenId, uint128 amount, uint256 ts)` |
| `0xff91f3ddeeed4e835ec3f368603b9298ded77af562ba684fe5ebd67209804cf1` | `DowngradeFromPermanentStake(address indexed owner, uint256 indexed tokenId, uint128 amount, uint256 ts)` |

The escrow also emits ERC-721 `Transfer` `0xddf252ad…` and ERC-4906 `MetadataUpdate`. Merge, split and managed-NFT events are gone.

### 1.7 Voter (root, Base) and LeafVoter (every chain)
| topic0 | Event |
|---|---|
| `0x128d063f0dba053df907ea6edfb37e10e59c4d3c36eb2f59ed3993a54c8eee6f` | `ChainsAllocated(uint256 indexed tokenId, (uint256,uint128,uint256,uint256)[] allocations)` — root |
| `0x66d2690ffceea8f4e6eb97b864441bb120b19e2c50c87420d7e5ca144c71a27e` | `GaugesAllocated(uint256 indexed tokenId, uint256 indexed chainId, (address,uint128,bytes)[] gauges)` — root (the vote) |
| `0x871c9c135204dfaa6a5ebebccc99a16da2bfb11ef83a4511d5c87cab5f7916f8` | `RedeemProcessed(uint256 indexed chainId, address indexed recipient, uint256 amount, uint256 surplusReported)` — root; AERO paid for burnt xAERO |
| `0x51f61861fc6e796ffd63c9c30190bb4a24477325376d9e326d507a75097f89e7` | `ChainRegistered(uint256 indexed chainId)` — root |
| `0x9bbfb5a47a677aa97f9ddeb4201a28211fc12c051145bf688d124b8d4ab86b34` | `ChainStatusSet(uint256 indexed chainId, uint8 status)` — root (suspend / resume a leaf) |
| `0xb13b0fcaf992c63a38992e4eeb65a542452c8366b7d9d8d7ca306ee1293dc2ba` | `GaugesAllocated(uint256 indexed tokenId, (address,uint128,bytes)[] gauges, uint256)` — LeafVoter (different topic0 from the root event) |
| `0x27d4634c833b7622a0acddbf7f746183625f105945e95c723ad1d5a9f2a0b6fc` | `Redeemed(address indexed redeemer, address indexed recipient, uint256 amount)` — LeafVoter (xAERO burnt) |
| `0x9acaadd0523552411c0e34a0160b98573211a163d69962b54a3786be27542f7a` | `EmissionsMinted(address indexed gauge, address[] recipients, uint128[] amounts)` — LeafVoter |
| `0x71f7a61470b5fb5936902836e43304ff5f9381c50b7225094c3769cd266f528d` | `GaugeRegistered(address indexed gauge, bool activated, uint48 registrationCursor)` — LeafVoter |
| `0x200f3718e1e8084712cc23b019926e472f5641917142a11a3a352198faab68af` | `GaugeActivated(address indexed gauge, uint48 activationCursor)` — LeafVoter |

### 1.8 Rewards, Minter, messaging, migration, Metarouter, Relay
| topic0 | Event |
|---|---|
| `0x03b031f5c39fe0dd2d6857f1cfe1a48d30aeddd78cea5fcf92a8f792c77cdc53` | `ClaimFees(uint256 indexed tokenId, address indexed recipient, address indexed token, uint256 amount)` — VotingRewardsManager (voter fee claim) |
| `0x2d491e878db8f327cff1dbcaade1d69ccf5a3dc6bd35acf19a3ed9e1e624c440` | `ClaimIncentives(uint256 indexed tokenId, address indexed recipient, uint256 indexed programId, uint256 amount)` — VotingRewardsManager |
| `0x71ea36aee81224d6ff4b1ae4ad8152480a6519812d2ad880c0f428211a54f9c6` | `IncentiveCreated(uint256 indexed programId, address indexed token, address indexed creator, uint256 amount, uint48 start, uint48 duration)` — incentive (bribe) program |
| `0x25b428dfde728ccfaddad7e29e4ac23c24ed7fd1a6e3e3f91894a9a073f5dfff` | `Minted(address indexed recipient, uint256 amount, uint256 splitterShare)` — Minter |
| `0x9ece25ff2f38a4b95c813c9bde80512c628d5cf29c3922ba549630f856fb5858` | `MessageDispatched(uint256 indexed chainId, uint256 chainNonce, uint8 msgType)` — Root/Leaf orchestrator |
| `0x93353145426252e868e8c3c5aa51e34eeaadf3bd6e61a28c32770f3e5928305a` | `MessageReceived(uint256 indexed chainId, uint256 chainNonce, uint8 msgType)` — Root/Leaf orchestrator |
| `0x9102b9031c3c59d8320bf14d84d7d7a3434366b91032fad1c87579cfc62b2372` | `MessageSent(bytes32 indexed messageId, bytes32 remoteAdapter)` — HyperlaneAdapter |
| `0xd9c26a8129d7a870c63a2a30cbfff89ae6ad16f1949c342160b9d5e2c182ea63` | `LiquidMigrated(address indexed depositor, address indexed recipient, uint256 amountIn, uint256 out)` — migration |
| `0x7189c8333f41695423e354bdab493c3cb377f4c8764d35a31f271b9cd61e84c8` | `VeNFTMigrated(address indexed depositor, address indexed recipient, uint256 indexed v2TokenId, uint256 amount, uint256 out, bool permanent, bool liquid)` — migration |
| `0x19e63f8afc420d7a16bb6278e9c895fdfcc27a62951ad5f310055ac81abdb86a` | `MessageDispatched(uint64 indexed nonce, address indexed recipient)` — VelodromeMigration (Optimism) |
| `0xa729164f5f8c328c28c80843501215b40232dec4d483d2e223d47cc6c886b1ca` | `Migrated(uint64 indexed nonce, address indexed recipient, uint256 tokenAmount, bool isLiquid)` — VelodromeMigrationEntrypoint (Base) |
| `0x428d600ec4013989f1261307f51c15b1a9d75295f72fde5740f1314caef7f60e` | `RemainingBurned(uint256 amount)` — migration wind-down |
| `0x99e0904407d080d7df635d4f68017fa5eb20cfbb1e51c1a6259a218eae490bc1` | `BatchExecuted(address indexed sender)` — Metarouter |
| `0x4b6af83da1aba26809d430706a37d0f341fe734a829d05a74616988a3174e22a` | `RelayCreated(address,uint256,uint8,address,address)` (first two indexed) — RelayFactory |

The AERO token and xAERO are plain ERC-20s (`Transfer` `0xddf252ad…`, `Approval` `0x8c5be1e5…`). Mint and burn show as `Transfer` from / to `0x0`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

| Selector | Signature | Notes |
|---|---|---|
| `0x022c0d9f` | `swap(uint256,uint256,address,bytes)` | V2 Pool; same selector as Uniswap V2 |
| `0x6a627842` / `0x89afcb44` | `mint(address)` / `burn(address)` | V2 Pool LP mint / burn |
| `0x15a0ea6a` | `claimFees(address)` | V2 Pool |
| `0xe3433615` / `0x531aa03e` | `createPool(address,address)` / `getPool(address,address)` | Volatile / Stable factory (no `bool`) |
| `0x232aa5ac` / `0x28af8d0b` | `createPool(address,address,int24,uint160)` / `getPool(address,address,int24)` | CLFactory |
| `0x128acb08` | `swap(address,bool,int256,uint160,bytes)` | CL Pool; same as Uniswap V3 |
| `0xb6b55f25` / `0x36efd16f` / `0x2e1a7d4d` | `deposit(uint256)` / `depositFor(uint256,address)` / `withdraw(uint256)` | Gauge stake / unstake (amount or tokenId) |
| `0x8ed86282` | `claimEmissions(address,address)` | Gauge (account, recipient) |
| `0x09902477` | `claimEmissions(address,address,uint256[])` | CLGauge, bounded by token IDs |
| `0x5312ea8e` | `emergencyWithdraw(uint256)` | Gauge |
| `0x9cd9c0a5` | `createStake(uint128,uint48,bool)` | VotingEscrow (amount, weeks, permanent) |
| `0xa0409a80` / `0xbd74f571` | `increaseStakeAmount(uint256,uint128)` / `increaseStakingPeriod(uint256,uint48)` | VotingEscrow |
| `0x00f714ce` | `withdraw(uint256,address)` | VotingEscrow |
| `0xe660caac` | `upgradeToPermanentStake(uint256)` | VotingEscrow |
| `0xf02e634e` | `allocate(uint256,(uint256,uint128,uint256,uint256)[],(uint256,uint256,uint256,(address,uint128,bytes)[])[],address)` | Voter: chains + gauges in one call |
| `0x21487d4c` | `allocateChains(uint256,(uint256,uint128,uint256,uint256)[],address)` | Voter |
| `0x5011bf07` | `allocateGauges(uint256,uint256,(address,uint128,bytes)[],uint256,address)` | Voter |
| `0x28b54326` | `claimRewards(uint256,(uint256,uint256,uint256,address,(address,uint256)[],(address,uint256,uint256)[])[],address)` | Voter (cross-chain fee + incentive claim) |
| `0x64e6e450` | `allocateGauges(uint256,(address,uint128,bytes)[])` | LeafVoter (local voting) |
| `0xc706df17` | `redeem(uint256,address,uint256,address)` | LeafVoter: burn xAERO → AERO on Base |
| `0x05ea04d1` | `settleGauge(address)` | LeafVoter |
| `0x781ba9b8` / `0xc0ddab40` | `depositLiquid(uint256,address)` / `depositVeNFT(uint256,address)` | Aerodrome/Velodrome migration |
| `0x5dd00733` | `killGauges(address[])` | AerodromeMigration (owner; legacy wind-down) |
| `0x3593564c` | `execute(bytes,bytes[],uint256)` | Metarouter; **same selector as Uniswap UniversalRouter** |
| `0x94bf804d` | `mint(uint256,address)` | Minter |
| `0x40c10f19` / `0x42966c68` | `mint(address,uint256)` / `burn(uint256)` | AERO token (minter-gated) |

Each selector above was found in the deployed Base bytecode (`PUSH4 <selector>`; `PUSH3` for `0x00f714ce`).

---

## 3. Addresses — shared on all six chains

These literals have the same code size on Base, Optimism, Ethereum, Arbitrum, Robinhood Chain and Arc (`eth_getCode`, 2026-10-30). The code hashes differ only by immutables. Ink (57073) uses the same literals.

| Role | Address | Notes |
|---|---|---|
| **VolatilePoolFactory** | `0x8E6a9FCd1d638CC760Ffba397605Fe3355dE76D2` | 11,002 B. `implementation()` → volatile pool impl |
| **StablePoolFactory** | `0x78589E876edcEbdce72ee3436ab3c9AD3a7cEF2D` | 11,002 B |
| Volatile pool implementation | `0x0526cF035C1156b5C598b0d3c2445e38af2e8bDE` | pools are 45 B clones of it |
| Stable pool implementation | `0xf525988f88B7D8b64631D86070FEC5BFDc50C174` | |
| PoolTape (V2) | `0x34bdD64B19D8631F936c2D07F19AAa6B83515992` | per-pool fee / volume history |
| Volatile / Stable CustomFeeModule | `0x7949DE8d67E4F6b8509Bdbb43FF0503aF1247a7A` / `0x0195fC76Da986D66B2A468133a1be41E90893Da6` | |
| Volatile / Stable FlatFeeQuoter | `0x95F6B665a1a97878353737ecb3D68aa978A5Cb9F` / `0x1B5B7e289FD620EE7c5D1EC9bD030f88D93d1d43` | |
| DiscountRegistry | `0xaA48AAef655FB7CD7Acc04717f66022a4771a345` | V2 and CL |
| **NonfungiblePositionManager** | `0x4857DB576eE0e45F10525eC59527BfD10beeC60b` | 24,516 B; `symbol()` "AERO-CL", `factory()` → the chain's CLFactory |
| **CL SwapRouter** | `0x9Ee35Bf1bd69a03c6F0393582030fCe8Bb93D418` | `factory()` → the chain's CLFactory |
| CL pool implementation | `0x1642634C8CB1C9f1B84c9a1a08534F8c3F4E89f8` | CL pools are 45 B clones of it |
| CLPoolNonSwapPath / CLPoolTape | `0x1AD7A8703eBFf81C0d753190938f228672Ec7e42` / `0x27D5EB73e7406675F6B0CbD037490ec3dba935a4` | |
| DynamicSwapFeeHook | `0xC0ed888AfE87ed1AcF01D9f19bB850159e3ce434` | default CL swap hook (dynamic fee + MEV tax) |
| CustomUnstakedFeeModule | `0xcc421483cd131a8FD6b68c37E46f244dbec4F797` | |
| Metaquoter | `0x1dDfeC5058180C207F55BB77D95AcDd0d8227868` | quotes V2 + CL routes |
| NFT descriptor | `0xf17CD3e4fe528a8280e73acdcb03Cc56024123E7` | |
| LpMigrator | `0x293Ba185d875B5c562B552082cfef630dab57baD` | |
| **CLGaugeFactory** | `0xf437f62053ACB121665b8fDBfeA8F214FB8E589d` | 12,029 B |
| CL gauge implementation / CLGaugeTape | `0x89E91A960154b1ed6c093039a8F0725ab67D14E0` / `0x0575b823C22585f1828BBc133d5e522A8499165C` | |
| **LeafVoter** | `0x382409fad8503FbCdbB27A4211551fa03e884078` | 16,985 B; `voter()` of every CLFactory; `chainStatus()` = 1 on all six |
| **GaugeManager** | `0xbF234b32c5e58868243A4a14831626f3EdE7b183` | emits `GaugeCreated` |
| LeafMessageOrchestrator | `0x7EA1079604af6dA2282B80f4cDc6Cea7b07914fe` | |
| TokenRegistry | `0x564665E023390097f46EA9662a6061a5d700A7E1` | token listing for gauges / incentives |
| **Metarouter** | `0x0fEf9e88A7b76BCDBF451780C6774FE32965Ee98` | 22,172 B; emits `BatchExecuted` |
| Libraries | `0x2b73DF2e7e957C77F1D8C01e0a71aD1fF38D6720` (RewardsLogic), `0x331d17Bee5149d4016cF9E54bDBD8164deD58499` (VotingRewardsFactory), `0xC7E262e848fCa78C3C66Ee3c9835e4E65E3E0398` (LeafAllocation) | no events |

Pool counts on 2026-10-30 (`allPoolsLength()`; volatile / stable / CL): Base 282 / 21 / 522; Optimism 35 / 22 / 45; Ethereum 4 / 1 / 80; Arbitrum 2 / 0 / 39; Robinhood Chain 3 / 0 / 84; Arc 6 / 1 / 7 (+ 35 in the lite CL factory). The CLFactory and V2 factory `owner()` / `poolAdmin()` is `0x42255e3c2d0b71a0b006243148fdf1a71d054ce0` on all six chains.

---

## 4. Addresses — Base (chain ID 8453) — root

All verified via `eth_getCode` and the wiring views on `https://base-rpc.publicnode.com` on 2026-10-30.

**Root-only contracts**

| Role | Address | One-liner |
|---|---|---|
| **AERO token (new)** | `0x3f5bF3EdAc59d650D8fDf9657a71F2f904A3a4Ee` | `symbol()` "AERO", `name()` "Aero", 18 decimals; total supply 2,130,935,509 AERO on 2026-10-30. Base only. |
| **VotingEscrow (sAERO)** | `0xBF7977E1521e9a3032bf7243Ee4712f311f13915` | ERC-721 "sAERO", `VERSION()` 3.0.0; `TOKEN()` → AERO, `VOTER()` → Voter |
| **Voter (root)** | `0x49d7d4f17Ec56Ef8fA04E464AF5D1A4942CC31e6` | `MINTER()`, `ORCHESTRATOR()`, `VOTING_ESCROW()` wired; `chains()` = [8453, 10, 1, 42161, 57073, 4663, 5042] |
| **Minter** | `0x59268A34ba897e82368feE39839FFC661D4f9C97` | per-second emission rate (`emissionRate()`); `SPLITTER()` → Splitter |
| Splitter | `0x9Beb95ccED809C0667bbb6577EE4066aC5cC1156` | team share of emissions |
| VoterPaymentsModule | `0xBe8e5149Dc0fE28d124dE4222b7Fb332De99AA79` | moves stake between sAERO positions |
| RootMessageOrchestrator | `0x4F347Fec2aEb8fdB569045AF4D0806eE7f7F6194` | `MessageDispatched` / `MessageReceived` |
| RootLocalAdapter | `0x8Daa7F020cfbA83D504763089334A572Bdd1eE90` | direct root ↔ Base-leaf calls (also the Base leaf `adapter`) |
| Root Hyperlane adapters | 1 `0x0C54028e2aEFDF6E740513655dCe88Ae63Df96c9`, 10 `0xE82457ff1049F1f63E51d634d2C96993b841B1Cb`, 42161 `0xa365AdDAa935FD97C0815D41a6375dbB483D5C67`, 4663 `0xD9DC65A40e70517dA5F4F5cB1F9E5D4b59AA2910`, 5042 `0x247c86a3bBd88059aeF2E9D3AF0e90D2F3F5C8bf`, 57073 `0x5aD9a3920a25CAA5ABD36CD35F1C57B48793FD03` | one per leaf chain; each 3,258 B; no code at these literals on the leaf chains |
| veArtProxy | `0xa3681Bf451eb7E7B2a36FDC83c3E045Fd96324d5` | |
| **AerodromeMigration** | `0x22a2F7340a3fB4C7C389D91eE954766B12476721` | `V2_TOKEN()` → legacy AERO, `V2_ESCROW()` → legacy veAERO, `V2_VOTER()` → legacy Voter; 1:1 |
| **VelodromeMigrationEntrypoint** | `0x6daE95FE833f190640dB1176F8C8a2e50C6a66c0` | Hyperlane receiver (`OP_DOMAIN()` 10, Mailbox `0xeA87ae93…4F1d`); pays AERO for VELO |
| RelayFactory / RelayFactoryRegistry | `0xA972232e6C1860586E1d66aC690d30Dab843049d` / `0x0dfBE7b949EAE4b826E33146F1df4C0c60c78f99` | `RelayCreated` |
| MaxiRelay / ProtocolRelay impl | `0x3dE62Ff7EAA843ACD85ba4Ee28a4981e890b1F4d` / `0xB3F3B37fBBfF05D1Df12C4022705e9E8552adE9f` | relays are clones |
| RelayTape / RelayVoteAdapter | `0x2d2B0Bed14477a15cE77181cA84f518e75628cb2` / `0xa3198c58eda8Ea74132A5e3c6E5E10C8FBa3e438` | |

**Base leaf stack (chain-specific)**

```
0x9CB220581b91b0C83223012FE69688b92aD07a76 -> CLFactory (voter()→LeafVoter ✓; 522 pools)
0x29F12cE5Be3D88b56D245B7f4E969C518F799a4a -> CL MevTaxModule
0x830D07BDe136752BCefe0B59a14c2C7af07814AF -> Volatile MevTaxModule
0x78ee48646a7e1507B79443a1d5494095D16AF3B8 -> Stable MevTaxModule
0x9FBCf2Df0DC553ce40Ef63963Bff465b76792B7E -> Volatile GaugeFactory   (impl 0xbCE3a68F9c22d18ddFff308Eb77Ce32C31853b03)
0x1e0f776E88649285f99e65Fa599aD6e0f9D97800 -> Stable GaugeFactory     (impl 0x1Be83b2a6B5a967DD9080D4202DC88B068aD4684)
0x8fbAaC4dbF170687ce6c3078f29556d97d197110 -> VotingRewardsFactory
0xD035217F89511eAE97daC11bF9604406EF431D17 -> GovernanceCreationModule
0x9ED69af7cf564D85804486D580c37e0F057dABFa -> GaugeTape
0x7b2A2c12dC5Ea2a31455952a05031C3E4BB28F3E -> FactoryRegistry
0x8C37F30F3c8fd48bEddb14086fa5148291D422C3 -> LeafEmissionsHandler (root variant, 1,458 B)
0x6CdDa0E730744DC6fF67654B35350Adad05EceE7 -> ReceiptToken xAERO (Base copy; claims on Base mint AERO)
0xb6c627DD729C24CcC53b562Bde4324f5EC87B148 -> TokenNFT   (TokenArtProxy 0xd0f9A84b90458c33B9714dC631b65D1cE5bA2c3f)
```

## 5. Addresses — Optimism (chain ID 10)

Verified on `https://optimism-rpc.publicnode.com` on 2026-10-30. Shared literals: §3.
```
0xfeaB42D90055db3a0616249f76B6002D72266778 -> CLFactory (voter()→LeafVoter ✓; 45 pools)
0xee72936bb7BD8b6AAB26cB99764693d959F40D11 -> CL MevTaxModule
0x5De55Ebe5B789bD309809c7969334c2C16e64EAF -> Volatile MevTaxModule
0x789226632665342Fab85feCd312EddF677302E18 -> Stable MevTaxModule
0x1B5D13975371806D699dC616A96D15B8eD26e5Ca -> Volatile GaugeFactory   (impl 0x8F53554044f01608c61cF3bB84523c253462f08E)
0x3924b18EDd37267dab6eDd99a3Bb339bf2b668fD -> Stable GaugeFactory     (impl 0x92602E333C8869A583f7983597dE24092ff7d8C7)
0xa91Cded49F48b7b26F8464339D6E7b39d20a1502 -> VotingRewardsFactory
0x97aBFe52c819AB175F6426eC30BBF2dF29f9E94b -> GovernanceCreationModule
0x1F246123F9385462789f862bC4BA45abaa98cF69 -> GaugeTape
0xb6F9705A631CC1C0E8570FFde48882C95E2Df408 -> FactoryRegistry
0x314BdC685aD3426d586860cf909e4D4f0279bF77 -> HyperlaneAdapter (leaf)
0x1AE1793aa67bB8A234A39ed1071d43B785B001ce -> LeafEmissionsHandler
0xbdEaeA5205d16f34Cb40038052d91235D87B4C54 -> ReceiptToken xAERO ("Aero"/"xAERO" ✓)
0xf1a19C65E90D0B4d4b07F27AD98CF065c575F6c7 -> TokenNFT   (TokenArtProxy 0x629C1846e1Eb9eC9516C7dff07e4660aDcC7055d)
0x1d52180B9049cb16f7db490bF1bB0ABEb992593d -> RelayLeafModuleDeployer
0x6daE95FE833f190640dB1176F8C8a2e50C6a66c0 -> VelodromeMigration (V2_TOKEN()→VELO, V2_ESCROW()→veVELO, ROOT_DOMAIN() 8453; same literal as the Base entrypoint)
```

## 6. Addresses — Ethereum (chain ID 1)

Verified on `https://ethereum-rpc.publicnode.com` on 2026-10-30. Shared literals: §3. **No MEV-tax modules on Ethereum** (`mevTaxModule` = `0x0`).
```
0xF4Fd2E6c5B60c5b365cd1B96DD6245E6D60414c2 -> CLFactory (voter()→LeafVoter ✓; 80 pools)
0x7F83235643181E440433400a027618Cd50879751 -> Volatile GaugeFactory   (impl 0x0FD6cc0e3D1a15f39a197E075b92a3E589EE3FCc)  ← same literal is the Arc CLFactory
0xCCe24256a8a6070A9E308f23E044C87C343F98Cd -> Stable GaugeFactory     (impl 0xC3b16c3F4ACE88FBFa2f5243f2b820b8C48AF215)
0x6BFC9D4C3A1CfD937dE04a5b817eAe424E85Ec2C -> VotingRewardsFactory
0xE14c7d02e02A177bF4693Dbb481a2Fd1E070efD4 -> GovernanceCreationModule
0x2f1ea2c2dEf80FCa460c0dcF205C281a8116834b -> GaugeTape
0xdd1705e23762F4D6e44D8C31BD8Ea80c54612239 -> FactoryRegistry
0x4AaFf8CFB43e2cefBbBF4c133c934DB6BA7E4C14 -> HyperlaneAdapter (leaf)
0xfc6ad3A6512d5D4906525E55c618da8dfFd837E8 -> LeafEmissionsHandler
0x9e148C5716b5aAdCFD3B71cEAE9EE7a9e22C29E2 -> ReceiptToken xAERO ✓
0x9bbCA84bb895A2e8ef94aa4F47071D65e874386b -> TokenNFT   (TokenArtProxy 0xB4CEFDD4C8d80430791CEb68Fdd97473a4b08dCA)
0xBDcB4929b19EBcfEE5eFE100B829c9B35C16d8F8 -> RelayLeafModuleDeployer
```

## 7. Addresses — Arbitrum One (chain ID 42161)

Verified on `https://arbitrum-one-rpc.publicnode.com` on 2026-10-30. Shared literals: §3. Arbitrum uses the `Arb*` gauge and hook variants (CL gauge impl 17,850 B vs 17,738 B elsewhere; they read the L2 block number from `ArbSys`).
```
0x88a60ee77392577c355C0acb2A8d476D5a4EC03a -> CLFactory (voter()→LeafVoter ✓; 39 pools)
0xce015007D03f3E3964938f11c29F24bDB0b945aB -> CL MevTaxModule
0xd724433C0C637c7e273Ac623427D806Ef396c50a -> Volatile MevTaxModule
0x8173816c3638650343B0a67E688AbB966C458130 -> Stable MevTaxModule
0xBbdDdd5ac17a672B360D2dBAa996468aDBEF8692 -> Volatile GaugeFactory   (impl 0x6E3b800DCC9a7e6b91239FEf0f8141F430EBCf84)
0x94AF9F874e92F05F42aE55FfC793b9F4f5FFc135 -> Stable GaugeFactory     (impl 0xe3557CD2De1B87dAaE2118401fCB4F635053BBC6)
0x5614AA98a8DAF9Ec71c3829ccbE8A365A742f5Cd -> VotingRewardsFactory
0xb6F9705A631CC1C0E8570FFde48882C95E2Df408 -> GovernanceCreationModule  ← same literal is the Optimism FactoryRegistry
0xD2b29e8058F74932446bD87a2D7D5914E9beC451 -> GaugeTape
0x9E635b2c689fC52201DF7eF1C9FA607c2F58f666 -> FactoryRegistry
0xe7eB27bf93a7a3cAa8B483Ec5f5EE6588bfD3886 -> HyperlaneAdapter (leaf)
0x3e8C5273795AaEdAb5C638a19D24EA245968bD3a -> LeafEmissionsHandler
0x436a085B2751cB87db270FFa66f8d698F87bEC82 -> ReceiptToken xAERO ✓
0x90eAE515Bf8CEAd8e90a2B1394e31Fd01378489C -> TokenNFT   (TokenArtProxy 0xF7B81Ac95eB5E41B69cCD1CCfe6811d68f99fe58)
0xCD4d7D9475Ed44ac3Bf61f9EdD9dC9928D69Ea7d -> RelayLeafModuleDeployer
```

## 8. Addresses — Robinhood Chain (chain ID 4663)

Verified on `https://robinhood-rpc.publicnode.com` on 2026-10-30. These are the real contracts, not the 2,109 B stubs that sit at many canonical literals on this chain: every code size matches the other chains (e.g. CLFactory 9,547 B, NFPM 24,516 B), and the views return the expected wiring (CLFactory `voter()` → LeafVoter, NFPM `factory()` → CLFactory, xAERO `symbol()` "xAERO"). Shared literals: §3. Like Arbitrum, Robinhood Chain uses the `Arb*` gauge and hook variants. **No MEV-tax modules** (`mevTaxModule` = `0x0`).
```
0xc63d7338c178e805c544B8f897066bD3BBcBE136 -> CLFactory (voter()→LeafVoter ✓; 84 pools)
0xCCe24256a8a6070A9E308f23E044C87C343F98Cd -> Volatile GaugeFactory   (impl 0xC3b16c3F4ACE88FBFa2f5243f2b820b8C48AF215)  ← Ethereum Stable GaugeFactory literal
0x1733cD126a227066963E9B636Ad49898d1224741 -> Stable GaugeFactory     (impl 0x2Ef99BB2EA373ab11832cc5644FB1d24683A1B13)
0x7F83235643181E440433400a027618Cd50879751 -> VotingRewardsFactory    ← Arc CLFactory / Ethereum Volatile GaugeFactory literal
0x2f1ea2c2dEf80FCa460c0dcF205C281a8116834b -> GovernanceCreationModule  ← Ethereum GaugeTape literal
0x2419270B247f1837f92e511d10b6A87A7b49637E -> GaugeTape
0xdd1705e23762F4D6e44D8C31BD8Ea80c54612239 -> FactoryRegistry          (same literal as Ethereum)
0x4AaFf8CFB43e2cefBbBF4c133c934DB6BA7E4C14 -> HyperlaneAdapter (leaf)  (same literal as Ethereum)
0xfc6ad3A6512d5D4906525E55c618da8dfFd837E8 -> LeafEmissionsHandler     (same literal as Ethereum)
0x9e148C5716b5aAdCFD3B71cEAE9EE7a9e22C29E2 -> ReceiptToken xAERO ✓     (same literal as Ethereum)
0x9bbCA84bb895A2e8ef94aa4F47071D65e874386b -> TokenNFT   (TokenArtProxy 0xB4CEFDD4C8d80430791CEb68Fdd97473a4b08dCA)
0xBDcB4929b19EBcfEE5eFE100B829c9B35C16d8F8 -> RelayLeafModuleDeployer
```

## 9. Addresses — Arc (chain ID 5042)

Verified on `https://arc-rpc.publicnode.com` on 2026-10-30. Shared literals: §3. Arc has **two CL factories**: the 1.1.0 factory and the 2026-09-15 "lite" factory. Both have `voter()` → LeafVoter `0x382409fa…4078` and share the `FactoryRegistry`. The lite V2 factories have no pools.

**Release 1.1.0**
```
0x7F83235643181E440433400a027618Cd50879751 -> CLFactory (voter()→LeafVoter ✓; 7 pools)
0xd9eF1acdca62010e93370f5932E3deD127E65396 -> CL MevTaxModule
0xcE660Ae96c979D5644D1c84a366Df8F92F80263E -> Volatile MevTaxModule
0x8FEce412833652dc8b261Ae4324aEbA77E26cadC -> Stable MevTaxModule
0x8f365E3Be968767192cCEbd9b07fcB608037A883 -> DiscountRegistry (Arc pool-modules copy; the shared 0xaA48AAef… also exists)
0xBDcB4929b19EBcfEE5eFE100B829c9B35C16d8F8 -> Volatile GaugeFactory   (impl 0xEa9eB1e343f4C29649D4DfA0C115Fd62a5919ED0)
0x9520C671C767B170c9f04e523B4e68c5d537779b -> Stable GaugeFactory     (impl 0x1e32799435b68C05240F946921a916B1a5BfAA94)
0x0c6bad5CaACD26aF5B6E2013D9F8bF9589d5ad1a -> VotingRewardsFactory
0xc00641CEc5c33E5Cc8A9CfE1876e52c07e09e2e9 -> GovernanceCreationModule
0xe2522a6FD510681196EDDFA7f012C1E58961B77F -> GaugeTape
0xCe44907DC45D3BFa3f5f6035B0e6E8B22D780A42 -> FactoryRegistry (shared with the lite stack)
0x56632394f866761Fd86873E96A567720cE865682 -> HyperlaneAdapter (leaf)
0x6BF28FdC8CDf34C59235B55DD6fA4d082F76B0fC -> LeafEmissionsHandler
0x20077cC0d5E385A0Fe9C91bbC7DC744f51559307 -> ReceiptToken xAERO ✓
0xFE649cbb1d950c3A29e129049DfC58978d16F004 -> TokenNFT   (TokenArtProxy 0xE07512ce27aA7C24303438aa76055A71B8353a1f)
0x9E635b2c689fC52201DF7eF1C9FA607c2F58f666 -> RelayLeafModuleDeployer  ← Arbitrum FactoryRegistry literal
```

**Lite launch (metadex 1.0.0 / slipstream 1.0.1, 2026-09-15) + gauge upgrade — still live**
```
0xb89Df768aF2CFE637ceB352c587Fe8edAf491d03 -> CLFactory "lite" (voter()→LeafVoter ✓; 35 pools; poolImplementation 0x0Df9fc8730eeC048e9832B31B4bFf4351158e19B)
0xc84bB45D43CD25D02b83B4C085eaA4e08da8f473 -> NonfungiblePositionManager (symbol "AERO-CL", factory()→lite CLFactory ✓)
0xb4702E1375F712da2e0d5F534c30c0c1513EdB2B -> CL SwapRouter (factory()→lite CLFactory ✓)
0x61d0Aa4a814a68F3119019f9f17ACa517FEa6D49 -> Metaquoter (lite)
0xaAf164008441F112eB2858d9F7A2dB1B84b1E415 -> DynamicSwapFeeHook (lite)
0xa02d1F4E4243ff0d350F478c44B0Fd37c7bF848C -> CLGaugeFactory (lite upgrade; impl 0x16F866688A306494C612149B48c2fE70CCBE3872)
0x7943664Ae6F61a689A35cf6D90A279F46c092580 -> LpMigrator (lite upgrade)
0x9bc8b3F60D349d687Fb44A018967025E3741F9a5 -> VolatilePoolFactory "lite" (0 pools; impl 0x8B64A0B590815d54C11a4B49A82b0133c7f53f0E)
0xaEd253F1aD84d99f2165256D701b2b481DD4CC16 -> StablePoolFactory "lite" (0 pools; impl 0x37D232368a22126a9584C7FF7643f26B2E276Ac8)
0x7275fA44c67bba8D921422e600b4Ed396209C886 -> Metarouter "lite" (21,984 B)
```

## 10. Not deployed — BNB Smart Chain (56), Avalanche (43114), Polygon PoS (137)

`eth_getCode` returns `0x` for the VolatilePoolFactory, StablePoolFactory, LeafVoter, NFPM, Metarouter and AERO literals on all three chains (2026-10-30). The new AERO token, the VotingEscrow and the root Voter have no code on any chain except Base.

---

## 11. Cross-chain summary

| Chain (ID) | Role | CLFactory | V2 factories | LeafVoter / NFPM / Metarouter | ReceiptToken (xAERO) | AERO / sAERO / Voter |
|---|---|---|---|---|---|---|
| Base (8453) | root + leaf | `0x9CB22058…7a76` | shared ✓ | shared ✓ | `0x6CdDa0E7…EceE7` | ✓ (only here) |
| Optimism (10) | leaf | `0xfeaB42D9…6778` | shared ✓ | shared ✓ | `0xbdEaeA52…4C54` | — |
| Ethereum (1) | leaf | `0xF4Fd2E6c…14c2` | shared ✓ | shared ✓ | `0x9e148C57…29E2` | — |
| Arbitrum (42161) | leaf | `0x88a60ee7…C03a` | shared ✓ | shared ✓ | `0x436a085B…EC82` | — |
| Robinhood Chain (4663) | leaf | `0xc63d7338…E136` | shared ✓ | shared ✓ | `0x9e148C57…29E2` | — |
| Arc (5042) | leaf | `0x7F832356…9751` + lite `0xb89Df768…1d03` | shared ✓ (+ lite, empty) | shared ✓ (+ lite NFPM / Metarouter) | `0x20077cC0…9307` | — |
| BNB (56) / Avalanche (43114) / Polygon (137) | — | — | — | — | — | — |

**Literal collisions (key on `(chainId, address)`):** `0x7F832356…9751` = Arc CLFactory, Ethereum Volatile GaugeFactory, Robinhood VotingRewardsFactory. `0xCCe24256…98Cd` = Ethereum Stable GaugeFactory, Robinhood Volatile GaugeFactory, Ink VotingRewardsFactory. `0xBDcB4929…16d8F8` = Arc Volatile GaugeFactory, RelayLeafModuleDeployer on Ethereum / Robinhood / Ink. `0x9E635b2c…f666` = Arbitrum FactoryRegistry, Arc RelayLeafModuleDeployer. `0xb6F9705A…F408` = Optimism FactoryRegistry, Arbitrum GovernanceCreationModule. `0x2f1ea2c2…834b` = Ethereum GaugeTape, Robinhood GovernanceCreationModule. `0xd9eF1acd…7E65396` = Arc CL MevTaxModule, Ink Stable GaugeFactory. `0x6daE95FE…66c0` = VelodromeMigration on Optimism, VelodromeMigrationEntrypoint on Base.

---

## 12. Proxies

- **No upgradeable proxies.** The EIP-1967 implementation and admin slots read `0x0` on Base for the AERO token, VotingEscrow, Voter, Minter, Splitter, VoterPaymentsModule, RootMessageOrchestrator, LeafVoter, LeafMessageOrchestrator, GaugeManager, TokenRegistry, ReceiptToken, both migration contracts, the V2 and CL factories, the NFPM, the Metarouter and the RelayFactory (2026-10-30). The source has no UUPS / Transparent / Beacon proxy.
- **EIP-1167 clones.** V2 pools (clone of the volatile / stable implementation), CL pools (`Clones.cloneDeterministic(poolImplementation, keccak256(token0, token1, tickSpacing))`), V2 and CL gauges and relays are 45 B minimal proxies. The implementation address is inlined in the clone bytecode (`0x363d3d373d3d3d363d73<impl>5af4…`). Each gauge gets a full `VotingRewardsManager` (22,368 B on Base), not a clone.
- **Change of behavior without an upgrade.** Owners can swap modules: fee module, MEV-tax module, pool tape, discount registry (`SetFeeModule`, `SetMevTaxModule`, `SetPoolTape`, `SetDiscountRegistry` on the V2 factories; `DefaultSwapHookChanged`, `PoolSwapHookChanged`, `UnstakedFeeModuleChanged` on the CLFactory). Watch these events, not an `Upgraded` topic.

---

## 13. Detection invariants & gotchas

1. **Aero is a separate deployment.** Do not reuse the legacy Aerodrome / Velodrome factory, Voter or token addresses for Aero. The new AERO is `0x3f5bF3Ed…a4Ee` (Base only); the legacy AERO `0x940181a9…8631` and VELO `0x9560e827…88Db` still exist and still move during the migration.
2. **V2 `PoolCreated` has a new topic0.** Aero V2 factories emit `PoolCreated(address,address,address,uint256)` `0xebbbe9dc…`. The legacy `0x2128d88d…` (with `bool stable`) is not emitted. The curve type comes from the emitter: Volatile factory `0x8E6a9FCd…` or Stable factory `0x78589E87…`.
3. **V2 pool `Mint` and `Claim` changed.** `Mint` is 4-arg (`0x2f00e3cd…`) and `Claim` is 5-arg (`0xcd5e4f02…`). `Swap`, `Burn`, `Sync`, `Fees` keep the legacy topic0s. A monitor keyed on the legacy `Mint` topic `0x4c209b5f…` misses every Aero LP add.
4. **NFPM `IncreaseLiquidity` changed.** Aero NFPM emits the 6-arg `0x0f8712c4…` (with `tickLower`, `tickUpper`). The Uniswap V3 / legacy Slipstream `0x3067048b…` is not emitted.
5. **CL core events equal Uniswap V3.** CL `Swap`/`Mint`/`Burn`/`Collect`/`Flash` topic0s are the Uniswap V3 values. Filter by pool address (pools from the CLFactory `PoolCreated`) to separate Aero from other V3 forks.
6. **Gauge `Deposit(address,address,uint256)` `0x5548c837…` collides** with the Velodrome superchain LeafGauge `Deposit`. Disambiguate by emitter (gauges from `GaugeCreated` `0x5f80f043…`).
7. **Two `GaugesAllocated` topics.** Root Voter `0x66d2690f…` has `(tokenId, chainId, gauges)`; LeafVoter `0xb13b0fca…` has `(tokenId, gauges, uint256)`. A vote on Base produces the root event; the leaf event fires when the message lands.
8. **Emissions are lazy.** The Minter mints AERO only when a gauge claim settles (`Minted` on the Minter; `EmissionsMinted` on the LeafVoter). On non-Base chains a claim mints **xAERO** (ReceiptToken), not AERO. A holder burns xAERO with `redeem` (`Redeemed` on the leaf) and receives AERO on Base (`RedeemProcessed` on the root Voter). Count AERO supply on Base only.
9. **No weekly epochs, no rebase.** Votes change at any time. sAERO positions get no rebase; emissions go to gauges and to the Splitter. Do not look for a weekly `NotifyReward` or `DistributeReward` pattern.
10. **Unallocated voting power parks on `CHAIN0`** (root) or `ZERO_GAUGE` (leaf). `ParkedOnChain0` is not an emission target.
11. **Same literal, different role per chain** (§11). The deployer used the same nonces on several chains. Never key on the address alone.
12. **Metarouter `execute(bytes,bytes[],uint256)` `0x3593564c` = Uniswap UniversalRouter `execute`.** Scope by `to` address. The real user is `BatchExecuted.sender`, not the pool `Swap.sender` (that is the Metarouter or the SwapRouter).
13. **Arc and Robinhood Chain are real here.** Code sizes equal the other chains and the views return the expected wiring. On Arc, watch both CL factories (1.1.0 and lite). On Arc, USDC is the native coin; the source lists Arc caveats for `refundETH()` and the voting-rewards wrapper.
14. **No MEV-tax module on Ethereum and Robinhood Chain.** The pool factories hold `mevTaxModule = 0x0` there, so swaps carry no priority-fee tax.
15. **Migration events.** `LiquidMigrated` / `VeNFTMigrated` on Base (`AerodromeMigration`) and on Optimism (`VelodromeMigration`); the Optimism side also emits `MessageDispatched(uint64,address)` and the Base entrypoint emits `Migrated` on settlement. Expect a delay between the two (Hyperlane).

---

## 14. Quick-copy detection constants (bytea-ready for PG)
```
-- ===== Topics (chain-agnostic) =====
TOPIC_POOL_SWAP                   = '\xb3e2773606abfd36b5bd91394b3a54d1398336c65005baf7bf7a05efeffaf75b'
TOPIC_POOL_MINT                   = '\x2f00e3cdd69a77be7ed215ec7b2a36784dd158f921fca79ac29deffa353fe6ee'
TOPIC_POOL_BURN                   = '\x5d624aa9c148153ab3446c1b154f660ee7701e549fe9b62dab7171b1c80e6fa2'
TOPIC_POOL_SYNC                   = '\xcf2aa50876cdfbb541206f89af0ee78d44a2abf8d328e37fa4917f982149848a'
TOPIC_POOL_FEES                   = '\x112c256902bf554b6ed882d2936687aaeb4225e8cd5b51303c90ca6cf43a8602'
TOPIC_POOL_CLAIM                  = '\xcd5e4f020ddad29434c2200a9edf2f8d7ec30f0d787f03b528ab7279aab0acbe'
TOPIC_V2_POOL_CREATED             = '\xebbbe9dc3a19d2f959ac76ac0372b4983cdfb945f5d6aef4873c36fabb2ba8aa'
TOPIC_CL_POOL_CREATED             = '\xab0d57f0df537bb25e80245ef7748fa62353808c54d6e528a9dd20887aed9ac2'
TOPIC_CL_SWAP                     = '\xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
TOPIC_CL_MINT                     = '\x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde'
TOPIC_CL_BURN                     = '\x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c'
TOPIC_CL_COLLECT                  = '\x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0'
TOPIC_CL_COLLECT_FEES             = '\x205860e66845f2bbc0966bfab80db9bf93fca93862ea2b9fcf6945748352b4a3'
TOPIC_CL_FLASH                    = '\xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633'
TOPIC_NFPM_INCREASE_LIQ           = '\x0f8712c47eb813e705bf827a60bdd551e6f2e055b4a1c2004304d52208a5a513'
TOPIC_NFPM_DECREASE_LIQ           = '\x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4'
TOPIC_NFPM_COLLECT                = '\x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01'
TOPIC_GAUGE_CREATED               = '\x5f80f043755ffb5732901cef69b9d5b7b1f7ec964176939d229d5f28daee9944'
TOPIC_V2_GAUGE_DEPOSIT            = '\x5548c837ab068cf56a2c2479df0882a4922fd203edb7517321831d95078c5f62'
TOPIC_V2_GAUGE_WITHDRAW           = '\x9b1bfa7fa9ee420a16e124f794c35ac9f90472acc99140eb2f6447c714cad8eb'
TOPIC_V2_GAUGE_EMISSIONS_CLAIMED  = '\x41a8f9b73fc5b26eed668484bc6e1ca460c33a1be2aaf9cc8d6ae0f6dd67a968'
TOPIC_CL_GAUGE_DEPOSIT            = '\xc9817c7b5bf7b2417ea338292b8681857834d37427fbb1899f98e6897f3fe426'
TOPIC_CL_GAUGE_WITHDRAW           = '\xac2f121be0a440c47693663f2118f4d3b12cf85696cbe2c7a1b4a35e68a827d2'
TOPIC_CL_GAUGE_EMISSIONS_CLAIMED  = '\x7b6bd720815adbeaaaed4fc759e1a535705901f33709fbb33e62ee9a89427bb1'
TOPIC_GAUGE_CLAIM_FEES            = '\xbc567d6cbad26368064baa0ab5a757be46aae4d70f707f9203d9d9b6c8ccbfa3'
TOPIC_VE_DEPOSIT                  = '\xc13ddc6db8fcc061bb7b8ae6a27b66f196765478b3771aca81eebdb10fce052c'
TOPIC_VE_WITHDRAW                 = '\xb110efbb1c6c959f8710077145fec647d8ecc07d3d7c17e9868625a01c057455'
TOPIC_VE_SUPPLY                   = '\x69251eb8eddb5ee229358aa71344347425044f6ec0d5384ce1fa077709cdd7ae'
TOPIC_VE_UPGRADE_PERMANENT        = '\xefd7eb052ddecc0a606ba787bdfcc18fa4f9c8440da558f10074598c8f5f0574'
TOPIC_VE_DOWNGRADE_PERMANENT      = '\xff91f3ddeeed4e835ec3f368603b9298ded77af562ba684fe5ebd67209804cf1'
TOPIC_VOTER_CHAINS_ALLOCATED      = '\x128d063f0dba053df907ea6edfb37e10e59c4d3c36eb2f59ed3993a54c8eee6f'
TOPIC_VOTER_GAUGES_ALLOCATED      = '\x66d2690ffceea8f4e6eb97b864441bb120b19e2c50c87420d7e5ca144c71a27e'
TOPIC_VOTER_REDEEM_PROCESSED      = '\x871c9c135204dfaa6a5ebebccc99a16da2bfb11ef83a4511d5c87cab5f7916f8'
TOPIC_VOTER_CHAIN_REGISTERED      = '\x51f61861fc6e796ffd63c9c30190bb4a24477325376d9e326d507a75097f89e7'
TOPIC_VOTER_CHAIN_STATUS_SET      = '\x9bbfb5a47a677aa97f9ddeb4201a28211fc12c051145bf688d124b8d4ab86b34'
TOPIC_LEAF_GAUGES_ALLOCATED       = '\xb13b0fcaf992c63a38992e4eeb65a542452c8366b7d9d8d7ca306ee1293dc2ba'
TOPIC_LEAF_REDEEMED               = '\x27d4634c833b7622a0acddbf7f746183625f105945e95c723ad1d5a9f2a0b6fc'
TOPIC_LEAF_EMISSIONS_MINTED       = '\x9acaadd0523552411c0e34a0160b98573211a163d69962b54a3786be27542f7a'
TOPIC_LEAF_GAUGE_REGISTERED       = '\x71f7a61470b5fb5936902836e43304ff5f9381c50b7225094c3769cd266f528d'
TOPIC_LEAF_GAUGE_ACTIVATED        = '\x200f3718e1e8084712cc23b019926e472f5641917142a11a3a352198faab68af'
TOPIC_VRM_CLAIM_FEES              = '\x03b031f5c39fe0dd2d6857f1cfe1a48d30aeddd78cea5fcf92a8f792c77cdc53'
TOPIC_VRM_CLAIM_INCENTIVES        = '\x2d491e878db8f327cff1dbcaade1d69ccf5a3dc6bd35acf19a3ed9e1e624c440'
TOPIC_INCENTIVE_CREATED           = '\x71ea36aee81224d6ff4b1ae4ad8152480a6519812d2ad880c0f428211a54f9c6'
TOPIC_MINTER_MINTED               = '\x25b428dfde728ccfaddad7e29e4ac23c24ed7fd1a6e3e3f91894a9a073f5dfff'
TOPIC_MSG_DISPATCHED              = '\x9ece25ff2f38a4b95c813c9bde80512c628d5cf29c3922ba549630f856fb5858'
TOPIC_MSG_RECEIVED                = '\x93353145426252e868e8c3c5aa51e34eeaadf3bd6e61a28c32770f3e5928305a'
TOPIC_HL_MESSAGE_SENT             = '\x9102b9031c3c59d8320bf14d84d7d7a3434366b91032fad1c87579cfc62b2372'
TOPIC_MIG_LIQUID                  = '\xd9c26a8129d7a870c63a2a30cbfff89ae6ad16f1949c342160b9d5e2c182ea63'
TOPIC_MIG_VENFT                   = '\x7189c8333f41695423e354bdab493c3cb377f4c8764d35a31f271b9cd61e84c8'
TOPIC_MIG_VELO_DISPATCHED         = '\x19e63f8afc420d7a16bb6278e9c895fdfcc27a62951ad5f310055ac81abdb86a'
TOPIC_MIG_VELO_SETTLED            = '\xa729164f5f8c328c28c80843501215b40232dec4d483d2e223d47cc6c886b1ca'
TOPIC_MIG_REMAINING_BURNED        = '\x428d600ec4013989f1261307f51c15b1a9d75295f72fde5740f1314caef7f60e'
TOPIC_METAROUTER_BATCH            = '\x99e0904407d080d7df635d4f68017fa5eb20cfbb1e51c1a6259a218eae490bc1'
TOPIC_RELAY_CREATED               = '\x4b6af83da1aba26809d430706a37d0f341fe734a829d05a74616988a3174e22a'
-- ===== Selectors (chain-agnostic) =====
SEL_POOL_SWAP                 = '\x022c0d9f'
SEL_POOL_MINT                 = '\x6a627842'
SEL_POOL_BURN                 = '\x89afcb44'
SEL_POOL_CLAIM_FEES           = '\x15a0ea6a'
SEL_V2_CREATE_POOL            = '\xe3433615'
SEL_V2_GET_POOL               = '\x531aa03e'
SEL_CL_CREATE_POOL            = '\x232aa5ac'
SEL_CL_GET_POOL               = '\x28af8d0b'
SEL_CL_SWAP                   = '\x128acb08'
SEL_GAUGE_DEPOSIT             = '\xb6b55f25'
SEL_GAUGE_DEPOSIT_FOR         = '\x36efd16f'
SEL_GAUGE_WITHDRAW            = '\x2e1a7d4d'
SEL_GAUGE_CLAIM_EMISSIONS     = '\x8ed86282'
SEL_CL_GAUGE_CLAIM_EMISSIONS  = '\x09902477'
SEL_GAUGE_EMERGENCY_WITHDRAW  = '\x5312ea8e'
SEL_VE_CREATE_STAKE           = '\x9cd9c0a5'
SEL_VE_INCREASE_AMOUNT        = '\xa0409a80'
SEL_VE_INCREASE_PERIOD        = '\xbd74f571'
SEL_VE_WITHDRAW               = '\x00f714ce'
SEL_VE_UPGRADE_PERMANENT      = '\xe660caac'
SEL_VOTER_ALLOCATE            = '\xf02e634e'
SEL_VOTER_ALLOCATE_CHAINS     = '\x21487d4c'
SEL_VOTER_ALLOCATE_GAUGES     = '\x5011bf07'
SEL_VOTER_CLAIM_REWARDS       = '\x28b54326'
SEL_LEAF_ALLOCATE_GAUGES      = '\x64e6e450'
SEL_LEAF_REDEEM               = '\xc706df17'
SEL_LEAF_SETTLE_GAUGE         = '\x05ea04d1'
SEL_MIG_DEPOSIT_LIQUID        = '\x781ba9b8'
SEL_MIG_DEPOSIT_VENFT         = '\xc0ddab40'
SEL_MIG_KILL_GAUGES           = '\x5dd00733'
SEL_METAROUTER_EXECUTE        = '\x3593564c'
SEL_MINTER_MINT               = '\x94bf804d'
SEL_TOKEN_MINT                = '\x40c10f19'
SEL_TOKEN_BURN                = '\x42966c68'
-- ===== Addresses — shared on Base / OP / ETH / ARB / Robinhood / Arc =====
ALL_VOLATILE_POOL_FACTORY     = '\x8e6a9fcd1d638cc760ffba397605fe3355de76d2'
ALL_STABLE_POOL_FACTORY       = '\x78589e876edcebdce72ee3436ab3c9ad3a7cef2d'
ALL_NFPM                      = '\x4857db576ee0e45f10525ec59527bfd10beec60b'
ALL_CL_SWAP_ROUTER            = '\x9ee35bf1bd69a03c6f0393582030fce8bb93d418'
ALL_CL_GAUGE_FACTORY          = '\xf437f62053acb121665b8fdbfea8f214fb8e589d'
ALL_LEAF_VOTER                = '\x382409fad8503fbcdbb27a4211551fa03e884078'
ALL_GAUGE_MANAGER             = '\xbf234b32c5e58868243a4a14831626f3ede7b183'
ALL_LEAF_MSG_ORCHESTRATOR     = '\x7ea1079604af6da2282b80f4cdc6cea7b07914fe'
ALL_TOKEN_REGISTRY            = '\x564665e023390097f46ea9662a6061a5d700a7e1'
ALL_METAROUTER                = '\x0fef9e88a7b76bcdbf451780c6774fe32965ee98'
ALL_DYNAMIC_SWAP_FEE_HOOK     = '\xc0ed888afe87ed1acf01d9f19bb850159e3ce434'
-- ===== Base (8453) — root =====
BASE_AERO                     = '\x3f5bf3edac59d650d8fdf9657a71f2f904a3a4ee'
BASE_VOTING_ESCROW            = '\xbf7977e1521e9a3032bf7243ee4712f311f13915'
BASE_VOTER                    = '\x49d7d4f17ec56ef8fa04e464af5d1a4942cc31e6'
BASE_MINTER                   = '\x59268a34ba897e82368fee39839ffc661d4f9c97'
BASE_SPLITTER                 = '\x9beb95cced809c0667bbb6577ee4066ac5cc1156'
BASE_VOTER_PAYMENTS_MODULE    = '\xbe8e5149dc0fe28d124de4222b7fb332de99aa79'
BASE_ROOT_MSG_ORCHESTRATOR    = '\x4f347fec2aeb8fdb569045af4d0806ee7f7f6194'
BASE_AERODROME_MIGRATION      = '\x22a2f7340a3fb4c7c389d91ee954766b12476721'
BASE_VELO_MIGRATION_ENTRY     = '\x6dae95fe833f190640db1176f8c8a2e50c6a66c0'
BASE_RELAY_FACTORY            = '\xa972232e6c1860586e1d66ac690d30dab843049d'
BASE_CL_FACTORY               = '\x9cb220581b91b0c83223012fe69688b92ad07a76'
BASE_RECEIPT_TOKEN            = '\x6cdda0e730744dc6ff67654b35350adad05ecee7'
BASE_VOLATILE_GAUGE_FACTORY   = '\x9fbcf2df0dc553ce40ef63963bff465b76792b7e'
BASE_STABLE_GAUGE_FACTORY     = '\x1e0f776e88649285f99e65fa599ad6e0f9d97800'
BASE_FACTORY_REGISTRY         = '\x7b2a2c12dc5ea2a31455952a05031c3e4bb28f3e'
-- ===== Optimism (10) =====
OP_CL_FACTORY                 = '\xfeab42d90055db3a0616249f76b6002d72266778'
OP_RECEIPT_TOKEN              = '\xbdeaea5205d16f34cb40038052d91235d87b4c54'
OP_VOLATILE_GAUGE_FACTORY     = '\x1b5d13975371806d699dc616a96d15b8ed26e5ca'
OP_STABLE_GAUGE_FACTORY       = '\x3924b18edd37267dab6edd99a3bb339bf2b668fd'
OP_FACTORY_REGISTRY           = '\xb6f9705a631cc1c0e8570ffde48882c95e2df408'
OP_HL_ADAPTER                 = '\x314bdc685ad3426d586860cf909e4d4f0279bf77'
OP_VELODROME_MIGRATION        = '\x6dae95fe833f190640db1176f8c8a2e50c6a66c0'
-- ===== Ethereum (1) =====
ETH_CL_FACTORY                = '\xf4fd2e6c5b60c5b365cd1b96dd6245e6d60414c2'
ETH_RECEIPT_TOKEN             = '\x9e148c5716b5aadcfd3b71ceae9ee7a9e22c29e2'
ETH_VOLATILE_GAUGE_FACTORY    = '\x7f83235643181e440433400a027618cd50879751'
ETH_STABLE_GAUGE_FACTORY      = '\xcce24256a8a6070a9e308f23e044c87c343f98cd'
ETH_FACTORY_REGISTRY          = '\xdd1705e23762f4d6e44d8c31bd8ea80c54612239'
ETH_HL_ADAPTER                = '\x4aaff8cfb43e2cefbbbf4c133c934db6ba7e4c14'
-- ===== Arbitrum (42161) =====
ARB_CL_FACTORY                = '\x88a60ee77392577c355c0acb2a8d476d5a4ec03a'
ARB_RECEIPT_TOKEN             = '\x436a085b2751cb87db270ffa66f8d698f87bec82'
ARB_VOLATILE_GAUGE_FACTORY    = '\xbbdddd5ac17a672b360d2dbaa996468adbef8692'
ARB_STABLE_GAUGE_FACTORY      = '\x94af9f874e92f05f42ae55ffc793b9f4f5ffc135'
ARB_FACTORY_REGISTRY          = '\x9e635b2c689fc52201df7ef1c9fa607c2f58f666'
ARB_HL_ADAPTER                = '\xe7eb27bf93a7a3caa8b483ec5f5ee6588bfd3886'
-- ===== Robinhood Chain (4663) =====
ROBIN_CL_FACTORY              = '\xc63d7338c178e805c544b8f897066bd3bbcbe136'
ROBIN_RECEIPT_TOKEN           = '\x9e148c5716b5aadcfd3b71ceae9ee7a9e22c29e2'
ROBIN_VOLATILE_GAUGE_FACTORY  = '\xcce24256a8a6070a9e308f23e044c87c343f98cd'
ROBIN_STABLE_GAUGE_FACTORY    = '\x1733cd126a227066963e9b636ad49898d1224741'
ROBIN_FACTORY_REGISTRY        = '\xdd1705e23762f4d6e44d8c31bd8ea80c54612239'
ROBIN_HL_ADAPTER              = '\x4aaff8cfb43e2cefbbbf4c133c934db6ba7e4c14'
-- ===== Arc (5042) =====
ARC_CL_FACTORY                = '\x7f83235643181e440433400a027618cd50879751'
ARC_CL_FACTORY_LITE           = '\xb89df768af2cfe637ceb352c587fe8edaf491d03'
ARC_NFPM_LITE                 = '\xc84bb45d43cd25d02b83b4c085eaa4e08da8f473'
ARC_SWAP_ROUTER_LITE          = '\xb4702e1375f712da2e0d5f534c30c0c1513edb2b'
ARC_METAROUTER_LITE           = '\x7275fa44c67bba8d921422e600b4ed396209c886'
ARC_RECEIPT_TOKEN             = '\x20077cc0d5e385a0fe9c91bbc7dc744f51559307'
ARC_VOLATILE_GAUGE_FACTORY    = '\xbdcb4929b19ebcfee5efe100b829c9b35c16d8f8'
ARC_STABLE_GAUGE_FACTORY      = '\x9520c671c767b170c9f04e523b4e68c5d537779b'
ARC_FACTORY_REGISTRY          = '\xce44907dc45d3bfa3f5f6035b0e6e8b22d780a42'
ARC_HL_ADAPTER                = '\x56632394f866761fd86873e96a567720ce865682'
```

---

## 15. Verification & sources

How the constants in this file were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the interface source of `metadex-public` (`V3/src/interfaces/**`) and `metadex-slipstream-public` (`contracts/**/interfaces`); structs flattened to tuples, enums to `uint8`. Confirmed live with `eth_getLogs` on Base: V2 factories `PoolCreated` `0xebbbe9dc…` (first at block 52,884,700), CLFactory `PoolCreated` `0xab0d57f0…`, NFPM `IncreaseLiquidity` `0x0f8712c4…`, V2 pool `Swap`/`Mint`/`Claim`/`Sync`/`Fees`, CL pool core events + `CollectFees`, V2 / CL gauge `Deposit`/`Withdraw`/`EmissionsClaimed`, `GaugeCreated` (292 since launch), VotingRewardsManager `ClaimFees`/`ClaimIncentives`, sAERO `Deposit`/`Supply`, root Voter `ChainsAllocated`/`GaugesAllocated`/`RedeemProcessed`, LeafVoter `Redeemed`/`EmissionsMinted`, Minter `Minted`, orchestrator `MessageDispatched`/`MessageReceived`, migration `LiquidMigrated`/`VeNFTMigrated`/`Migrated`, Metarouter `BatchExecuted`. Every selector in §2 was found as a `PUSH4`/`PUSH3` operand in the deployed Base bytecode.
- **Addresses:** parsed from `deployment-addresses/*.json` of both repos (the files listed in each repo's `VERSIONS`) and existence-checked with `eth_getCode` on all six chains (every listed address has code; the root adapters have no code on leaves, as expected). Code sizes match per role across chains. Wiring read live: CLFactory `voter()`/`poolImplementation()`/`positionManager()`/`owner()`, V2 factory `implementation()`/`factoryRegistry()`/`isPaused()`, LeafVoter `RECEIPT_TOKEN()`/`FACTORY_REGISTRY()`/`ORCHESTRATOR()`/`chainStatus()`, NFPM `symbol()`/`factory()`, SwapRouter `factory()`, xAERO `symbol()`, AERO `symbol()`/`totalSupply()`, VotingEscrow `TOKEN()`/`VOTER()`/`VERSION()`, Voter `MINTER()`/`chains()`, Minter `ACTIVATION_TIMESTAMP()`, migration `V2_TOKEN()`/`V3_TOKEN()`/`MIGRATION_OPEN()`/`paid()`/`paidBasis()`.
- **Proxies:** EIP-1967 impl and admin slots read live (all `0x0`); clone bytecode read on Robinhood Chain (pool `0x76159260…9750` → impl `0x1642634c…`).
- **Legacy status:** `GaugeKilled` logs on the Base Aerodrome Voter; `isAlive()` on sampled Aerodrome and Velodrome gauges; legacy `PoolFactory.isPaused()`.
- **Chain coverage:** Base, Optimism, Ethereum, Arbitrum, Robinhood Chain, Arc present; BNB, Avalanche, Polygon absent (`eth_getCode` = `0x`).
- **Not verified:** event history on Robinhood Chain and Optimism (the public RPCs refuse `eth_getLogs` beyond recent blocks); topics were confirmed on Base, where the code is identical. The Ink (57073) leaf was not checked on chain.

Authoritative sources:
- [`dromos-labs/metadex-public`](https://github.com/dromos-labs/metadex-public) — V2 pools, gauges, voting, messaging, migration, Metarouter, Relay; `deployment-addresses/`, `VERSIONS`, `audits/sherlock-contest-auditor-guide.md`.
- [`dromos-labs/metadex-slipstream-public`](https://github.com/dromos-labs/metadex-slipstream-public) — CL pools, CL gauges, NFPM, SwapRouter; `deployment-addresses/`.
- [aero.xyz](https://aero.xyz) — app.
- Merger and migration news: [The Defiant](https://thedefiant.io/news/defi/dromos-labs-merges-aerodrome-and-velodrome-into-new-dex-aero) · [Crypto Briefing (Coinbase window)](https://cryptobriefing.com/coinbase-aero-velo-token-migration/) · [Kraken notice](https://support.kraken.com/articles/aero-migration).
- Explorers: [Basescan](https://basescan.org) · [Etherscan](https://etherscan.io) · [Optimistic Etherscan](https://optimistic.etherscan.io) · [Arbiscan](https://arbiscan.io).
