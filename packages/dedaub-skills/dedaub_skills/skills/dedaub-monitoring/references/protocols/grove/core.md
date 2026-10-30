# Grove Finance — Topics, Selectors, Addresses (Ethereum, Base, Avalanche, Robinhood Chain)

**Status:** verified against live RPC on every listed chain and the canonical `grove-labs/grove-alm-controller` and `grove-labs/grove-address-registry` repos on 2026-10-30.
**Scope:** the Grove Liquidity Layer. Grove is a Sky "star" (subDAO) that allocates USDS/USDC into tokenized credit and RWA (Centrifuge JTRSY/JAAA, BlackRock BUIDL, Superstate USTB/USCC, Steakhouse Morpho vaults, Aave, Curve, Ethena). This file covers the `ALMProxy`, `MainnetController` (Ethereum), `ForeignController` (Base, Avalanche, Robinhood Chain), `RateLimits`, the Grove "PAU" (diamond) set and the Grove governance contracts. Chains: Ethereum (1), Base (8453), Avalanche C-Chain (43114), Robinhood Chain (4663). Not deployed on BNB (56), Arbitrum (42161), Optimism (10), Polygon PoS (137) or Arc (5042). Topics and selectors are chain-agnostic. Addresses are network-specific.

Grove's controller code is a **fork of `sparkdotfi/spark-alm-controller`** (the repo says so). The architecture is the same as the Spark Liquidity Layer ([../spark/liquidity-layer.md](../spark/liquidity-layer.md)). The `ALMProxy` holds funds. The controller holds the logic and is the only `CONTROLLER`. `RateLimits` caps each action. **All three are immutable.** Governance upgrades logic by a new controller deployment. The `RateLimits` and `ALMProxy` topics and selectors are byte-identical to Spark's. USDS for Grove is minted from the Sky allocation system (`ALLOCATOR_GROVE_A_VAULT`) — see [../sky/](../sky/).

---

## 0. Contract families & versions

| Component | Role | Pattern |
|-----------|------|---------|
| **ALMProxy** | Custody of all Grove funds. `doCall` for the controller. | Immutable, OZ `AccessControl` |
| **MainnetController** (ETH) | USDS mint/burn (Allocator Vault), LitePSM swaps, CCTP/LayerZero, ERC-4626, ERC-7540 (Centrifuge), Aave, Curve, Uniswap V3, Ethena, Pendle PT. | Immutable |
| **ForeignController** (Base, Avax, Robinhood) | PSM3, CCTP, LayerZero, ERC-4626, ERC-7540, Aave, Curve, Uniswap V3, Pendle. | Immutable |
| **RateLimits** | Same as Spark. | Immutable |
| **PAU set** (ETH) | Diamond generation: `PAU_PROXY`, `PAU_CONTROLLER`, facets (Basin, PSM, Uniswap V3, USDS), `PAU_RATE_LIMITS`, two "Grove Basins" (JTRSY, BUIDL). | Source not public — addresses only |
| **Governance** | `GROVE_PROXY` (Sky subproxy), `GROVE_EXECUTOR` + receiver on each L2, `GROVE_STAR_GUARD`, GROVE token, stGROVE. | — |

---

## 1. Topics (chain-agnostic)

### 1.1 RateLimits (identical to Spark)

| topic0 | Event |
|--------|-------|
| `0x2f9bcbd665fb7984aac3b6a05bb4ac8b303137a34ed4cc5fcd47622f52bdf046` | `RateLimitDecreaseTriggered(bytes32 indexed key, uint256 amountToDecrease, uint256 oldRateLimit, uint256 newRateLimit)` |
| `0xb824249bbde4df2bf5473f603ab3aa717ea2e37b908d9fb4440b962fb656d0ac` | `RateLimitIncreaseTriggered(bytes32 indexed key, uint256 amountToIncrease, uint256 oldRateLimit, uint256 newRateLimit)` |
| `0x356822943b80f809508a684c67d901d5c13b6a22161bf07d510e50a6cb727028` | `RateLimitDataSet(bytes32 indexed key, uint256 maxAmount, uint256 slope, uint256 lastAmount, uint256 lastUpdated)` |

### 1.2 MainnetController / ForeignController

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xa613b2b0a8074f0163704e8596561e20fda50f29acee27f8d0bc4c73521034f3` | `CCTPTransferInitiated(uint32 indexed destinationDomain, bytes32 indexed mintRecipient, uint256 usdcAmount)` | **Grove form** (no nonce). Live on ETH. |
| `0x5e7cfea10f05abc55e716d0d5031f3eea4eabbe012e9bf1d56c5034bba4bfa30` | `MintRecipientSet(uint32 indexed destinationDomain, bytes32 mintRecipient)` | |
| `0x6c34eba04bf16b35385ac7487ab08f9023bcd9836a5bd53dc60ec0da331b4543` | `LayerZeroRecipientSet(uint32 indexed destinationEndpointId, bytes32 layerZeroRecipient)` | |
| `0x44cb267bb9745c1d8f9c953d077e0c7f61d15ed326a273995423fa92fe95dbfc` | `CentrifugeRecipientSet(uint16 indexed centrifugeId, bytes32 recipient)` | Grove only |
| `0xd8df93d785f3d0d4294fd7b61e5d749c20eec95a2fed5b6b502a4cad09199ca6` | `MaxSlippageSet(address indexed pool, uint256 maxSlippage)` | |
| `0xfce512ccb77d3237e23e27ae3357b9527a46adbc1faf1367475efd86a2e7aeed` | `MaxExchangeRateSet(address indexed token, uint256 maxExchangeRate)` | |
| `0x10e1f7ce9fd7d1b90a66d13a2ab3cb8dd7f29f3f8d520b143b063ccfbab6906b` | `RelayerRemoved(address indexed relayer)` | Freezer action |
| `0x28f3318dba7e2b4e237ea9e5c2b43e4d0b4dba6b3ac2ec5310207a1f5c064e46` | `UniswapV3PoolMaxTickDeltaSet(address indexed pool, uint24 maxTickDelta)` | Grove only |
| `0x39fcc572b87668289f5fc71805ae64f0ed7e54b0852c093ce7bce7c0b07bea40` | `UniswapV3PoolLowerTickUpdated(address indexed pool, int24 lowerTick)` | Grove only |
| `0x8867fabc4cd418699bdde3de931d6ed002b63c69d19dec1ac7ea878132ce918e` | `UniswapV3PoolUpperTickUpdated(address indexed pool, int24 upperTick)` | Grove only |
| `0x5ae1be944f44ada6e791b973062a26a81f8c26de171bd7660bf67b185c53be9d` | `UniswapV3PoolTwapSecondsAgoUpdated(address indexed pool, uint32 twapSecondsAgo)` | Grove only |
| `0xbc9e8b58187ce04ecbd14accc4063f8db7c03d9ac09cc774c49103adb7d8f304` | `MaxAaveV4SlippageSet(address indexed spoke, uint256 indexed reserveId, uint256 maxSlippage)` | Repo HEAD only (not in deployed controllers) |
| `0xa1de28d87ae1a331bf0d0d1eaaabb283f4437601185e7405fd59aa7d3236e37d` | `MaxAaveV4DeficitSet(address indexed hub, uint16 indexed assetId, uint256 maxDeficit)` | Repo HEAD only |
| `0x9bb98328b033a775e731f99903de63e54604421f841767c590163110a84b0326` | `MidnightMarketConfigSet(bytes32 indexed marketId, uint16 maxBuyTick, uint16 minSellTick, uint16 minBuyYield, uint16 maxSellYield, uint16 maxContinuousFee, uint128 maxLossFactor)` | Repo HEAD only |

### 1.3 Access control

| topic0 | Event |
|--------|-------|
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |

The ALMProxy emits no business events. Track it through ERC-20 `Transfer` logs and the target protocol's events.

---

## 2. Function signatures (chain-agnostic)

ALMProxy and RateLimits selectors are the same as Spark: `doCall(address,bytes)` `0x3aada4d2`, `doCallWithValue(address,bytes,uint256)` `0xd71f93f8`, `doDelegateCall(address,bytes)` `0x8ce4a1f2`, `CONTROLLER()` `0xee0fc121`, `triggerRateLimitDecrease(bytes32,uint256)` `0x3bf076b0`, `triggerRateLimitIncrease(bytes32,uint256)` `0x5c093b74`, `setRateLimitData(bytes32,uint256,uint256,uint256,uint256)` `0xf6a82d1a`. All were found in the live Robinhood ALMProxy and RateLimits bytecode.

### 2.1 Controllers — relayer actions (checked in live bytecode on ETH, Base, Robinhood)

| Selector | Signature | Live on |
|----------|-----------|---------|
| `0x536f6b7e` / `0x96122b62` | `mintUSDS(uint256)` / `burnUSDS(uint256)` | ETH |
| `0x5acb7053` / `0x115c48d5` | `swapUSDSToUSDC(uint256)` / `swapUSDCToUSDS(uint256)` | ETH |
| `0x0d015236` / `0x7b65461c` | `swapUSDSToDAI(uint256)` / `swapDAIToUSDS(uint256)` | ETH |
| `0xbcd7e46c` | `transferUSDCToCCTP(uint256,uint32)` | all |
| `0x203f0e3e` | `transferTokenLayerZero(address,uint256,uint32)` | all |
| `0x439e2e45` | `transferAsset(address,address,uint256)` | all |
| `0x85f4881d` | `depositERC4626(address,uint256)` | all (**2-arg form**) |
| `0x0b372e57` | `withdrawERC4626(address,uint256)` | all |
| `0xd9acb348` | `redeemERC4626(address,uint256)` | all |
| `0xc2be3706` | `requestDepositERC7540(address,uint256)` | all (Centrifuge) |
| `0xe08471fc` | `claimDepositERC7540(address)` | all |
| `0xc95c29d9` | `requestRedeemERC7540(address,uint256)` | all |
| `0x4390e9dd` | `claimRedeemERC7540(address)` | all |
| `0xb2b094a0` | `transferSharesCentrifuge(address,uint128,uint16)` | all |
| `0x2cefff96` / `0x7891c043` | `depositAave(address,uint256)` / `withdrawAave(address,uint256)` | all |
| `0x1eaef443` | `swapCurve(address,uint256,uint256,uint256,uint256)` | all |
| `0x533a5901` / `0x072ef76d` | `addLiquidityCurve(address,uint256[],uint256)` / `removeLiquidityCurve(address,uint256,uint256[])` | all |
| `0xbc206c37` | `swapUniswapV3(address,address,uint256,uint256,uint24)` | all |
| `0x7bac30dd` | `redeemPendlePT(address,uint256,uint256)` | all |
| `0x7a1cd355` / `0xb41b48af` | `depositPSM(address,uint256)` / `withdrawPSM(address,uint256)` | Foreign (Spark PSM3 on Base) |
| `0xb2eae5ad` / `0x0187148f` | `prepareUSDeMint(uint256)` / `prepareUSDeBurn(uint256)` | ETH |
| `0x02a4ea53` / `0xc77d9a52` | `cooldownAssetsSUSDe(uint256)` / `unstakeSUSDe()` | ETH |

`addLiquidityUniswapV3` and `removeLiquidityUniswapV3` take struct arguments (`UniswapV3Lib.Tick`, `TokenAmounts`). Their selectors are not listed. Repo HEAD adds `toggleOperatorMerkl`, `depositAaveV4`/`withdrawAaveV4`, `buyMidnight`/`sellMidnight`/`redeemMidnight` and 3-arg ERC-4626 functions. **None of these are in the deployed controllers** (PUSH4 scan, 2026-10-30).

### 2.2 Controllers — admin / freezer

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x60f0a5ac` | `removeRelayer(address)` | `FREEZER`. |
| `0xb5cbf202` | `setMintRecipient(uint32,bytes32)` | Admin. |
| `0xd3eaf93c` | `setLayerZeroRecipient(uint32,bytes32)` | Admin. |
| `0x73d76dbe` | `setMaxSlippage(address,uint256)` | Admin. |
| `0x7011df99` | `setMaxExchangeRate(address,uint256,uint256)` | Admin. |
| `0xec556889` / `0xf0921594` / `0x04bda262` | `proxy()` / `rateLimits()` / `psm()` | Views. |

---

## 3. Addresses

All addresses come from `grove-address-registry` `src/<Chain>.sol`. Each one returned non-empty code from `eth_getCode` on 2026-10-30. On every chain the wiring was read live: `controller.proxy()` = ALMProxy, `controller.rateLimits()` = RateLimits, and `hasRole(CONTROLLER, controller)` = true on the ALMProxy and RateLimits. `DEFAULT_ADMIN_ROLE` = the chain's Grove governance address. `RELAYER` = `ALM_RELAYER`. `FREEZER` = `ALM_FREEZER`.

### 3.1 Liquidity Layer

| Chain (ID) | ALMProxy | Controller | RateLimits | Admin | `psm()` |
|------------|----------|------------|------------|-------|---------|
| Ethereum (1) | `0x491EDFB0B8b608044e227225C715981a30F3A44E` (2274 B) | `0xfd9dEA9a8D5B955649579Af482DB7198A392A9F5` Mainnet | `0x5F5cfCB8a463868E37Ab27B5eFF3ba02112dF19a` | `GROVE_PROXY` `0x1369f7b2b38c76B6478c0f0E66D94923421891Ba` | LitePSM `0xf6e72Db5…3042` |
| Base (8453) | `0x9B746dBC5269e1DF6e4193Bcb441C0FbBF1CeCEe` | `0x7f8408eBbBC3504F83eeDa52910dd75Eba92C955` Foreign | `0xAc8BF0669223197ac8B94Cbb53E725e40B3919E8` | `GROVE_EXECUTOR` `0x491EDFB0B8b608044e227225C715981a30F3A44E` | Spark PSM3 `0x1601843c…347E` |
| Avalanche (43114) | `0x7107DD8F56642327945294a18A4280C78e153644` | `0x4236B772BEeEAFF57550Aa392A0f227C0b908Ce7` Foreign | `0x6ba2e6bCCe3d2A31F1e3e1d3e11CDffBaA002A21` | `GROVE_EXECUTOR` `0x4b803781828b76EaBF21AaF02e5ce23596b4d60c` | `0x…deadbeef` (placeholder) |
| Robinhood (4663) | **`0x29626c2d8Ca49A51E4dECEEc5499e52983c42BD5`** (2260 B) | `0x2c10885ddec8d52ecF3Ad2B3833765bf36eD80cf` Foreign (22937 B) | `0xC13e5ff7993c5df911aE562a7736B0eBA12b2010` | `GROVE_EXECUTOR` `0x5ff98717a18833de1A49e11B498866d6Fa1c9296` | `0x0` |

### 3.2 Operators (Safe multisigs, same address on every chain)

| Role | Address |
|------|---------|
| `ALM_RELAYER` (holds `RELAYER`) | `0x0eEC86649E756a23CBc68d9EFEd756f16aD5F85f` |
| `ALM_FREEZER` (holds `FREEZER`) | `0xB0113804960345fd0a245788b3423319c86940e5` |
| Secondary relayer operator (`ALM_RELAYER_2` on Base) | `0x9187807e07112359C481870feB58f0c117a29179` |
| Primary relayer operator (ETH) | `0x4364D17B578b0eD1c42Be9075D774D1d6AeAFe96` |

### 3.3 Governance and cross-chain receivers

| Chain | Contract | Address |
|-------|----------|---------|
| Ethereum | `GROVE_PROXY` (Sky subproxy, admin of the ETH SLL) | `0x1369f7b2b38c76B6478c0f0E66D94923421891Ba` |
| Ethereum | `GROVE_STAR_GUARD` | `0xfc51CAa049E8894bEcFfB68c61095C3F3Ec8a880` |
| Ethereum | GROVE token / stGROVE / GROVE farm | `0xB30FE1Cf884B48a22a50D22a9282004F2c5E9406` / `0xF3Ddcaa3BD5D04ba08beC69cf34D9d9C9c112d14` / `0x4E41488C19cD35EB4de3083Fc3e204854c75c86a` |
| Ethereum | `ALLOCATOR_GROVE_A_VAULT` / `ALLOCATOR_GROVE_A_BUFFER` (Sky) | `0xf739a30c74927dc6cFA3B67E4933872a1FC5F4EB` / `0x436DABce608f73BeA2b75fba35bffe72739697d5` |
| Ethereum | `ALLOCATOR_BLOOM_A_VAULT` / `ALLOCATOR_BLOOM_A_BUFFER` (Sky, legacy "Bloom") | `0x26512A41C8406800f21094a7a7A0f980f6e25d43` / `0x629aD4D779F46B8A1491D3f76f7E97Cb04D8b1Cd` |
| Base | `GROVE_RECEIVER` (OP-stack receiver) | `0x5F5cfCB8a463868E37Ab27B5eFF3ba02112dF19a` |
| Avalanche | `GROVE_CCTP_V1_RECEIVER` / `GROVE_CCTP_V2_RECEIVER` | `0x26e9512547feC1906C55256e491DfB6673D8C23f` / `0x8Ea8Dff8c29f568eA1E716E2C3AfbD003EB83cfA` |
| Robinhood | `GROVE_RECEIVER` (Arbitrum-style receiver, 830 B) | `0xa02eC279eEA9E56F4E14449a07C5ca5FDAAdc51d` |

### 3.4 PAU (diamond) set — Ethereum only

| Contract | Address |
|----------|---------|
| `PAU_PROXY` | `0x0DcD9298e163dFD3c0B5b00F0d9093C36e40A153` |
| `PAU_CONTROLLER` | `0xbf83F5974B932c7D842254042717D6A2706CE5eE` |
| `PAU_RATE_LIMITS` | `0xE016Ae733A77Ba77E7907aAA749394Fc5e75C0e1` |
| `PAU_ACCESS_CONTROLS` / `PAU_ADMINISTERED_AGENT` | `0x4F6d1704700cd494DD4cd9bF59c0C39DA1Bc9164` / `0xdBD17832df0e57b1732cE1C84c652E820e549BAa` |
| `PAU_BEACON` / `PAU_FACTORY` / `PAU_DEFAULT_ASSEMBLER` | `0x829dC2b7E94B1954F0764E573f2E0d45Afa28199` / `0x69A5d548830AC2A4Ba90A44a2C75BDA71f97fc66` / `0xc812aAD3FaE2D3511C664374B601a9BeBFeCCa2E` |
| Facets: Basin / PSM / Uniswap V3 / USDS | `0xC84825BCD13AEddc372400239499380376a44A39` / `0xE4A5dAc768a310cc2316f258901b32E499653064` / `0x445D9Dc752F269Be48250f1A180CAC4c61cE4bab` / `0x1221CC4B85Ab260660aD21C2829e0EB516dffBc7` |
| Grove Basins: JTRSY / BUIDL | `0xf08943f817e1F902dEbC884c7B19Ea5764594Ac9` / `0xCBa428fB052B365557DAf52b744DFfF20d5FbEdD` |

### 3.5 Main allocation targets (third-party, for context)

| Chain | Target | Address |
|-------|--------|---------|
| Robinhood | Grove x Steakhouse USDG vault (Morpho Vault V2, 21808 B) | `0xBEEff039907422219Fb367e525954DDC092854d9` |
| Robinhood | USDG (Paxos, 170 B proxy) | `0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168` |
| Ethereum | Grove x Steakhouse USDC / USDC-HY V2 / AUSD V2 / RLUSD V2 / USDG V2 / PYUSD V2 | `0xBEEf2B5FD3D94469b7782aeBe6364E6e6FB1B709` / `0xBeefF08dF54897e7544aB01d0e86f013DA354111` / `0xBEEfF0d672ab7F5018dFB614c93981045D4aA98a` / `0xBeEff4fD39F8e48b6a6e475445D650cb11e9599F` / `0xbeef05061FE51eA482BD1b68041353490b3a5934` / `0xbeef08Db223ad823164A4B13CBD6bd8b5d507b41` |
| Ethereum | Centrifuge JTRSY-USDC / JAAA-USDC / ACRDX-USDC (ERC-7540) | `0xFE6920eB6C421f1179cA8c8d4170530CDBdfd77A` / `0x4880799eE5200fC58DA299e965df644fBf46780B` / `0x74A739EA1Dc67c5a0179ebad665D1D3c4b80B712` |
| Base | Grove x Steakhouse USDC (V1 / V2) | `0xBeEf2d50B428675a1921bC6bBF4bfb9D8cF1461A` / `0xbeef0786756810478b88982DE00F3CD7fdB8e7c7` |
| Avalanche | Centrifuge JAAA / JTRSY | `0x1121F4e21eD8B9BC1BB9A2952cDD8639aC897784` / `0xFE6920eB6C421f1179cA8c8d4170530CDBdfd77A` |

On 2026-10-30 the Robinhood ALMProxy held 12,535,607 USDG and 2.58M shares of the Steakhouse USDG vault (≈ 2.58M USDG). Total ≈ 15.1M USD. See [../morpho/v2.md](../morpho/v2.md) for the vault topics.

---

## 4. Cross-chain summary

| Chain | ALMProxy | Controller | RateLimits | PAU | Executor |
|-------|----------|------------|------------|-----|----------|
| Ethereum (1) | `0x491E…A44E` | `0xfd9d…A9F5` | `0x5F5c…F19a` | ✓ | `GROVE_PROXY` `0x1369…91Ba` |
| Base (8453) | `0x9B74…CeEe` | `0x7f84…C955` | `0xAc8B…19E8` | — | `0x491E…A44E` |
| Avalanche (43114) | `0x7107…3644` | `0x4236…8Ce7` | `0x6ba2…2A21` | — | `0x4b80…d60c` |
| Robinhood (4663) | `0x2962…2BD5` | `0x2c10…80cf` | `0xC13e…2010` | — | `0x5ff9…9296` |
| BNB / Arbitrum / Optimism / Polygon / Arc | — | — | — | — | — |

Non-target chain: Plume (ALMProxy `0x1DB91ad50446a671e2231f77e00948E68876F812`). Not covered here.

---

## 5. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| ALMProxy | **Immutable** | EIP-1967 impl slot `0x0` on all four chains | None. Logic moves by `CONTROLLER` role rotation. |
| Main/ForeignController | **Immutable** | impl slot `0x0` | Replaced by a new deployment. Watch `RoleGranted(CONTROLLER, …)` on the ALMProxy. |
| RateLimits | **Immutable** | impl slot `0x0` | Admin data changes only (`RateLimitDataSet`). |
| stGROVE | EIP-1967 proxy (808 B) | impl slot = `0x5a0dc8e7…9cfe` | Grove governance. |
| Operator multisigs | Safe proxies (171 B) | — | Safe owners. |

---

## 6. Detection invariants & gotchas

1. **Same fork, different CCTP topic.** Grove emits the 3-field `CCTPTransferInitiated` (`0xa613b2b0…`). Spark's deployed controllers emit the 4-field form with a nonce (`0x805a2d8b…`). Live ETH logs confirm both. Do not reuse one filter for both stars.
2. **Same RateLimits topics as Spark.** `RateLimitDecreaseTriggered` (`0x2f9bcbd6…`) fires for both stars. Disambiguate by emitter: Grove ETH `0x5F5cfCB8…`, Spark ETH `0x7A5FD5cf…`.
3. **Rate-limit keys are hashed.** A per-target key is `keccak256(abi.encode(keccak256("LIMIT_X"), target))`. Example (verified on Robinhood): the 827,674 USDG deposits into the Steakhouse vault use key `keccak256(abi.encode(LIMIT_4626_DEPOSIT, 0xBEEff039…54d9))`. Unlimited keys emit no `RateLimit*` event.
4. **Address reuse with a different role.** `0x491EDFB0…A44E` is the **ALMProxy on Ethereum** and the **GROVE_EXECUTOR on Base**. `0x5F5cfCB8…F19a` is the **RateLimits on Ethereum** and the **GROVE_RECEIVER on Base**. `0x7f8408eB…C955` is the **controller on Base** and the RateLimits on Plume. On Robinhood, `0x4b803781…` and `0xAc8BF066…` (Grove addresses on other chains) hold unrelated 1359 B contracts. **Key on `(chainId, address)`.**
5. **Deployed code lags the repo.** The repo HEAD has 3-arg ERC-4626 calls, Aave V4, Midnight and Merkl. The deployed controllers use the 2-arg ERC-4626 selectors (`0x85f4881d` …) and do not have the others. Filter on deployed selectors.
6. **Grove uses Spark's PSM3 on Base.** The Grove Base controller `psm()` = `0x1601843c…347E` (Spark PSM3). Grove `depositPSM` calls show as PSM3 `Deposit` events with `user` = Grove ALMProxy `0x9B746dBC…CeEe`.
7. **Avalanche `psm()` is a placeholder** (`0x00000000000000000000000000000000deadbeef`). The Avalanche controller cannot use a PSM. The Avalanche RateLimits emitted no event in the last 600k blocks.
8. **Robinhood lead.** The Robinhood ALMProxy `0x29626c2d…2BD5` has the same 2260 B size as the Spark Robinhood ALMProxy `0xfD2fD4B0…dB24`. The two are separate stars. Read `controller.proxy()` to attribute.
9. **PAU and Basin source is not public.** Their events are not documented here.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_RATE_LIMIT_DECREASE      = '\x2f9bcbd665fb7984aac3b6a05bb4ac8b303137a34ed4cc5fcd47622f52bdf046'
TOPIC_RATE_LIMIT_INCREASE      = '\xb824249bbde4df2bf5473f603ab3aa717ea2e37b908d9fb4440b962fb656d0ac'
TOPIC_RATE_LIMIT_DATA_SET      = '\x356822943b80f809508a684c67d901d5c13b6a22161bf07d510e50a6cb727028'
TOPIC_GROVE_CCTP_TRANSFER      = '\xa613b2b0a8074f0163704e8596561e20fda50f29acee27f8d0bc4c73521034f3'
TOPIC_MINT_RECIPIENT_SET       = '\x5e7cfea10f05abc55e716d0d5031f3eea4eabbe012e9bf1d56c5034bba4bfa30'
TOPIC_LZ_RECIPIENT_SET         = '\x6c34eba04bf16b35385ac7487ab08f9023bcd9836a5bd53dc60ec0da331b4543'
TOPIC_CENTRIFUGE_RECIPIENT_SET = '\x44cb267bb9745c1d8f9c953d077e0c7f61d15ed326a273995423fa92fe95dbfc'
TOPIC_MAX_SLIPPAGE_SET         = '\xd8df93d785f3d0d4294fd7b61e5d749c20eec95a2fed5b6b502a4cad09199ca6'
TOPIC_MAX_EXCHANGE_RATE_SET    = '\xfce512ccb77d3237e23e27ae3357b9527a46adbc1faf1367475efd86a2e7aeed'
TOPIC_RELAYER_REMOVED          = '\x10e1f7ce9fd7d1b90a66d13a2ab3cb8dd7f29f3f8d520b143b063ccfbab6906b'
TOPIC_UNIV3_MAX_TICK_DELTA_SET = '\x28f3318dba7e2b4e237ea9e5c2b43e4d0b4dba6b3ac2ec5310207a1f5c064e46'
TOPIC_ROLE_GRANTED             = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED             = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
-- ===== Roles =====
ROLE_CONTROLLER                = '\x70546d1c92f8c2132ae23a23f5177aa8526356051c7510df99f50e012d221529'
ROLE_RELAYER                   = '\xab4f864e5201b0fde9b5ee3e4cf96384802b0ffdfcf7f9de4699ce21a30afc4f'
ROLE_FREEZER                   = '\x0ac42a08299cbc4428ec38ad4a8e7d7440779fbbb20ea90bd10c094a406cfa6f'
LIMIT_4626_DEPOSIT             = '\xc80e541ae8dbb00d82e12edc8dbc29e6ae9ebed737088df9145797f7edca3b42'
LIMIT_7540_REQUEST_DEPOSIT     = '\x654122ca0be3469b54c44eafeb834d28e9d810cea17fbdc5d6b7acda96f9a2c8'
LIMIT_USDS_MINT                = '\xcb0537d5e5dba65a8edbac12555995860e5b8e1b70996011edb1ca8173e56d3c'
-- ===== Selectors (chain-agnostic) =====
SEL_DO_CALL                    = '\x3aada4d2'
SEL_MINT_USDS                  = '\x536f6b7e'
SEL_BURN_USDS                  = '\x96122b62'
SEL_SWAP_USDS_TO_USDC          = '\x5acb7053'
SEL_TRANSFER_USDC_TO_CCTP      = '\xbcd7e46c'
SEL_TRANSFER_TOKEN_LZ          = '\x203f0e3e'
SEL_TRANSFER_ASSET             = '\x439e2e45'
SEL_DEPOSIT_ERC4626_2ARG       = '\x85f4881d'
SEL_WITHDRAW_ERC4626_2ARG      = '\x0b372e57'
SEL_REDEEM_ERC4626_2ARG        = '\xd9acb348'
SEL_REQUEST_DEPOSIT_ERC7540    = '\xc2be3706'
SEL_REQUEST_REDEEM_ERC7540     = '\xc95c29d9'
SEL_TRANSFER_SHARES_CENTRIFUGE = '\xb2b094a0'
SEL_SWAP_UNISWAP_V3            = '\xbc206c37'
SEL_REDEEM_PENDLE_PT           = '\x7bac30dd'
SEL_DEPOSIT_PSM                = '\x7a1cd355'
SEL_REMOVE_RELAYER             = '\x60f0a5ac'
-- ===== Addresses (network-specific) =====
ETH_GROVE_ALM_PROXY            = '\x491edfb0b8b608044e227225c715981a30f3a44e'
ETH_GROVE_ALM_CONTROLLER       = '\xfd9dea9a8d5b955649579af482db7198a392a9f5'
ETH_GROVE_ALM_RATE_LIMITS      = '\x5f5cfcb8a463868e37ab27b5eff3ba02112df19a'
ETH_GROVE_PROXY                = '\x1369f7b2b38c76b6478c0f0e66d94923421891ba'
ETH_GROVE_PAU_PROXY            = '\x0dcd9298e163dfd3c0b5b00f0d9093c36e40a153'
ETH_GROVE_PAU_CONTROLLER       = '\xbf83f5974b932c7d842254042717d6a2706ce5ee'
ETH_GROVE_ALLOCATOR_VAULT      = '\xf739a30c74927dc6cfa3b67e4933872a1fc5f4eb'
BASE_GROVE_ALM_PROXY           = '\x9b746dbc5269e1df6e4193bcb441c0fbbf1cecee'
BASE_GROVE_ALM_CONTROLLER      = '\x7f8408ebbbc3504f83eeda52910dd75eba92c955'
BASE_GROVE_ALM_RATE_LIMITS     = '\xac8bf0669223197ac8b94cbb53e725e40b3919e8'
BASE_GROVE_EXECUTOR            = '\x491edfb0b8b608044e227225c715981a30f3a44e'
AVAX_GROVE_ALM_PROXY           = '\x7107dd8f56642327945294a18a4280c78e153644'
AVAX_GROVE_ALM_CONTROLLER      = '\x4236b772beeeaff57550aa392a0f227c0b908ce7'
AVAX_GROVE_ALM_RATE_LIMITS     = '\x6ba2e6bcce3d2a31f1e3e1d3e11cdffbaa002a21'
AVAX_GROVE_EXECUTOR            = '\x4b803781828b76eabf21aaf02e5ce23596b4d60c'
ROBIN_GROVE_ALM_PROXY          = '\x29626c2d8ca49a51e4deceec5499e52983c42bd5'
ROBIN_GROVE_ALM_CONTROLLER     = '\x2c10885ddec8d52ecf3ad2b3833765bf36ed80cf'
ROBIN_GROVE_ALM_RATE_LIMITS    = '\xc13e5ff7993c5df911ae562a7736b0eba12b2010'
ROBIN_GROVE_EXECUTOR           = '\x5ff98717a18833de1a49e11b498866d6fa1c9296'
ROBIN_GROVE_STEAKHOUSE_USDG    = '\xbeeff039907422219fb367e525954ddc092854d9'
ALL_GROVE_ALM_RELAYER          = '\x0eec86649e756a23cbc68d9efed756f16ad5f85f'
ALL_GROVE_ALM_FREEZER          = '\xb0113804960345fd0a245788b3423319c86940e5'
```

---

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `grove-alm-controller` (commit `53abf7b`, 2026-10-23). Live `eth_getLogs` confirmed `RateLimitDecreaseTriggered`/`RateLimitIncreaseTriggered` on the ETH (105 logs in about 10k blocks), Base (29) and Robinhood (3) RateLimits, and the 3-field `CCTPTransferInitiated` on the ETH controller (30). Controller selectors were confirmed by a PUSH4 scan of the live ETH, Base and Robinhood controllers.
- **Addresses:** parsed from `grove-address-registry` (`src/Ethereum.sol`, `Base.sol`, `Avalanche.sol`, `Robinhood.sol`). Each address was checked with `eth_getCode`. The EIP-1967 slot was read for each. `proxy()`, `rateLimits()`, `psm()` and `hasRole` (CONTROLLER, DEFAULT_ADMIN, RELAYER, FREEZER) were read live on all four chains. Robinhood ALMProxy balances were read with `balanceOf`.
- **Chain coverage:** the registry has no BNB, Arbitrum, Optimism, Polygon or Arc file. `eth_getCode` on Arc returned `0x` for every Grove key address. Polygon and BNB returned code only at three Spark addresses (an unrelated sweep contract), none at Grove addresses.
- **Not verified:** PAU/Basin topics and selectors (source not public). Uniswap V3 add/remove-liquidity selectors (struct arguments, not computed).

Authoritative sources:
- [grove-labs/grove-alm-controller](https://github.com/grove-labs/grove-alm-controller) — source of truth for signatures (fork of `sparkdotfi/spark-alm-controller`).
- [grove-labs/grove-address-registry](https://github.com/grove-labs/grove-address-registry) — addresses for each chain.
- [Grove website](https://grove.finance)
- Explorers: [Etherscan](https://etherscan.io/address/0x491EDFB0B8b608044e227225C715981a30F3A44E) · [Basescan](https://basescan.org/address/0x9B746dBC5269e1DF6e4193Bcb441C0FbBF1CeCEe) · [Snowtrace](https://snowtrace.io/address/0x7107DD8F56642327945294a18A4280C78e153644) · [Robinhood Chain Blockscout](https://robinhoodchain.blockscout.com/address/0x29626c2d8Ca49A51E4dECEEc5499e52983c42BD5)
