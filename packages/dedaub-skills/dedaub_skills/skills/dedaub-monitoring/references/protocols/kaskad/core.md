# Kaskad (Aave V3.3 fork) — Topics, Selectors, Addresses (Robinhood Chain)

**Status:** verified against live Robinhood Chain RPC on 2026-10-30. Every address was read on-chain from the `AaveProtocolDataProvider` and the `PoolAddressesProvider`. The DefiLlama protocol entry `kaskad` supplied the DataProvider lead.
**Scope:** Kaskad Lending on **Robinhood Chain (4663)**, the market "Kaskad Lending Robinhood". Kaskad is an **Aave V3 fork at the v3.3 feature level**. Topics and selectors are chain-agnostic and equal to Aave V3 ([aave/v3.md](../aave/v3.md)). Addresses are network-specific.

Kaskad runs the Aave V3 contract set: a `PoolAddressesProvider`, a `Pool` proxy, a `PoolConfigurator` proxy, an `AaveOracle`, an `ACLManager`, a `PriceOracleSentinel` and per-reserve aTokens / variable-debt tokens. `POOL_REVISION()` returns 7. The Pool impl has the v3.3 bad-debt functions (`eliminateReserveDeficit`, `getReserveDeficit`) and no stable-rate functions. It does not have the v3.4 additions (`multicall`, `approvePositionManager`). The market lists WETH, USDG, PONS and the tokenized stocks NVDA and TSLA.

Kaskad's main market is on **Igra** (an EVM L2 anchored to Kaspa), which is outside this reference set. DefiLlama reported about $0.36M supplied (free liquidity) and $0.03M borrowed on Robinhood Chain on 2026-10-30.

---

## 1. Topics (chain-agnostic — identical to Aave V3)

Pool events are emitted from the Pool proxy address. Live Pool logs on Robinhood Chain (blocks 98,828,168–101,828,168; first log at block 99,255,276): `ReserveDataUpdated` 34, `Supply` 18, `ReserveUsedAsCollateralEnabled` 15, `Borrow` 9, `ReserveUsedAsCollateralDisabled` 6, `Withdraw` 5, `Repay` 2.

| topic0 | Event |
|--------|-------|
| `0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61` | `Supply(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint16 indexed referralCode)` ✓live |
| `0x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7` | `Withdraw(address indexed reserve, address indexed user, address indexed to, uint256 amount)` ✓live |
| `0xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0` | `Borrow(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint8 interestRateMode, uint256 borrowRate, uint16 indexed referralCode)` ✓live |
| `0xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051` | `Repay(address indexed reserve, address indexed user, address indexed repayer, uint256 amount, bool useATokens)` ✓live |
| `0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286` | `LiquidationCall(address indexed collateralAsset, address indexed debtAsset, address indexed user, uint256 debtToCover, uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)` (not seen in the sample window) |
| `0xefefaba5e921573100900a3ad9cf29f222d995fb3b6045797eaea7521bd8d6f0` | `FlashLoan(address indexed target, address initiator, address indexed asset, uint256 amount, uint8 interestRateMode, uint256 premium, uint16 indexed referralCode)` |
| `0x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a` | `ReserveDataUpdated(address indexed reserve, uint256 liquidityRate, uint256 stableBorrowRate, uint256 variableBorrowRate, uint256 liquidityIndex, uint256 variableBorrowIndex)` ✓live |
| `0x00058a56ea94653cdf4f152d227ace22d4c00ad99e2a43f58cb7d9e3feb295f2` | `ReserveUsedAsCollateralEnabled(address indexed reserve, address indexed user)` ✓live |
| `0x44c58d81365b66dd4b1a7f36c25aa97b8c71c361ee4937adc1a00000227db5dd` | `ReserveUsedAsCollateralDisabled(address indexed reserve, address indexed user)` ✓live |
| `0x2bccfb3fad376d59d7accf970515eb77b2f27b082c90ed0fb15583dd5a942699` | `DeficitCreated(address indexed user, address indexed debtAsset, uint256 amountCreated)` (v3.3 bad debt) |
| `0x84b203e49f1a4b553088061534231969a68ad1c81be192205e96d23a206cb26a` | `DeficitCovered(address indexed reserve, address caller, uint256 amountCovered)` (v3.3 bad debt) |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` (Pool / Configurator / token proxies) |

aToken / debt-token `Mint`, `Burn`, `BalanceTransfer`, and the admin events (`ReserveInitialized`, …) are the Aave V3 ones; see [aave/v3.md](../aave/v3.md) §1.

## 2. Function signatures (chain-agnostic — identical to Aave V3)

| Selector | Signature | In the Robinhood Pool impl? |
|----------|-----------|-----------------------------|
| `0x617ba037` | `supply(address,uint256,address,uint16)` | yes |
| `0x02c205f0` | `supplyWithPermit(address,uint256,address,uint16,uint256,uint8,bytes32,bytes32)` | yes |
| `0x69328dec` | `withdraw(address,uint256,address)` | yes |
| `0xa415bcad` | `borrow(address,uint256,uint256,uint16,address)` | yes |
| `0x573ade81` | `repay(address,uint256,uint256,address)` | yes |
| `0x2dad97d4` | `repayWithATokens(address,uint256,uint256)` | yes |
| `0x00a718a9` | `liquidationCall(address,address,address,uint256,bool)` | yes (as `PUSH3 0xa718a9`, because the selector starts with `0x00`) |
| `0xab9c4b5d` / `0x42b0b77c` | `flashLoan(...)` / `flashLoanSimple(...)` | yes |
| `0x5a3b74b9` | `setUserUseReserveAsCollateral(address,bool)` | yes |
| `0x28530a47` | `setUserEMode(uint8)` | yes |
| `0xa1d2f3c4` | `eliminateReserveDeficit(address,uint256)` | yes (v3.3) |
| `0xc952485d` | `getReserveDeficit(address)` | yes (v3.3) |
| `0x9cd19996` | `mintToTreasury(address[])` | yes |
| `0xbf92857c` / `0xd1946dbc` | `getUserAccountData(address)` / `getReservesList()` | yes |
| `0xac9650d8` / `0xb8caa7c5` | `multicall(bytes[])` / `approvePositionManager(address,bool)` | **no** (v3.4 additions) |
| `0x94ba89a2` / `0xcd112382` | `swapBorrowRateMode(…)` / `rebalanceStableBorrowRate(…)` | **no** (stable rate removed in v3.2) |

---

## 3. Addresses — Robinhood Chain (chain ID 4663)

All verified via `eth_getCode` / `eth_call` on `https://robinhood-rpc.publicnode.com` on 2026-10-30. `getMarketId()` = `"Kaskad Lending Robinhood"`.

| Role | Address | Notes |
|------|---------|-------|
| **Pool** (proxy) | `0x91d1d9294a5e735746fa3e68bf88286ca6c485d5` | 1882 B proxy; EIP-1967 impl `0x439a217cb682698f7dfde437e393e4d12a9e4d3b` (22758 B). All user events. |
| PoolConfigurator (proxy) | `0x0d2b0f1ebff46af300c13f58d5d2551fec6c130c` | 1882 B proxy; impl `0xcc4ef4906ba161984ae645b3f0e5098f1244dbb5` (19760 B). |
| PoolAddressesProvider | `0x3e9a28d988ee889b47bf257f0e103960721475d0` | 6989 B. `owner()` = ACL admin = `0x11505259b3ac74c3901cc058c59cafbc931808d1` (an EOA: no code). |
| AaveProtocolDataProvider | `0x9ff935c295925540077416042e3a0e1be5276401` | 9660 B. The address DefiLlama reads; also `getPoolDataProvider()`. |
| AaveOracle | `0x1fb1bb18297467181a0698d2ba332b95cd13fb30` | 2629 B, not a proxy. `getFallbackOracle()` = 0. |
| ACLManager | `0xea7e4d2cffc6bc7289241b3efa026c09e4bc9f65` | 3504 B. |
| PriceOracleSentinel | `0x95eb34aae3ffb1dbfebe6e26b730827da7ab9a88` | 4987 B. `getSequencerOracle()` = 0 (unset); `getGracePeriod()` = 172,800 s. |
| Treasury (aToken `RESERVE_TREASURY_ADDRESS`) | `0xe9585bf5564227a5e919405f2d9ada382969025a` | |

### 3.1 Reserves (5, from `getAllReservesTokens()`)

aToken symbols use the prefix `aRh` (for example `aRhUSDG`). There are no stable-debt tokens. aToken impl (aWETH proxy): `0x8cb2dcf656478603fcd57df755d16eca42bf06b2`.

| Asset | Underlying | aToken | variableDebtToken | Oracle source (`getSourceOfAsset`) |
|-------|-----------|--------|-------------------|-----------------------------------|
| WETH | `0x0bd7d308f8e1639fab988df18a8011f41eacad73` | `0x6ce05a90f0a9266fb98e4db271f11675c889f3c8` | `0x64f082e571b585f8e2b26ebf08b44aa6c82235b9` | `0x78f3556b67e17df817d51ef5a990cdaf09e8d3a9` ("ETH / USD") |
| USDG | `0x5fc5360d0400a0fd4f2af552add042d716f1d168` | `0x297b91f20db44c9063133c5bd27b42f24b1872ff` | `0xffa4b31fc68a37c8fc1fdccb50d4004a8057c6ee` | `0x61b7e5650328764b076a108eff5fa7282a1b9ad2` ("USDG / USD") |
| PONS | `0x39dbed3a2bd333467115de45665cc57f813c4571` | `0x8a14a3241acb7a292610f154b8f97d71792f4de0` | `0x9a4f43a514682499124fc8e105daf3072fce3912` | `0x724a8014c37de5f646e517a521a7c35d96afb649` ("PONS/USD", 2707 B custom feed) |
| NVDA | `0xd0601ce157db5bdc3162bbac2a2c8af5320d9eec` | `0x78ec2da07700e8c220e3afb724b4534d1335b23d` | `0xcee66feef74b69f88e8e46abd01a52bb93acab85` | `0x379ec4f7c378f34a1b47e4f3cbebcbac3e8e9f15` ("RHNVDA / USD") |
| TSLA | `0x322f0929c4625ed5bad873c95208d54e1c003b2d` | `0x63d456cea2f2ca0a9046604f4344f6485641661d` | `0x916058a579f7cfb63d2284297400582b0280712a` | `0x4a1166a659a55625345e9515b32adecea5547c38` ("RHTSLA / USD") |

---

## 4. Cross-chain summary

| Chain | ID | Kaskad Pool |
|-------|----|-------------|
| Robinhood Chain | 4663 | `0x91d1d929…c485d5` |
| Ethereum / Base / BNB / Avalanche / Arbitrum / Optimism / Polygon / Arc | — | — (the DataProvider, AddressesProvider and Pool addresses return `0x` on all eight) |
| Igra (off-target) | — | Kaskad's main market; not enumerated here |

## 5. Proxies

| Contract | Pattern | Upgrade auth |
|----------|---------|--------------|
| Pool, PoolConfigurator | Aave `InitializableImmutableAdminUpgradeabilityProxy` (EIP-1967 impl slot set; admin slot empty, admin = the PoolAddressesProvider) | `PoolAddressesProvider.setPoolImpl()` / `setPoolConfiguratorImpl()`, owner `0x11505259…` (EOA) |
| aTokens, debt tokens | Aave token proxies (per reserve) | PoolConfigurator |
| PoolAddressesProvider, DataProvider, AaveOracle, ACLManager, PriceOracleSentinel | Not proxies (impl slot = 0) | — |

Watch `Upgraded(address)` (`0xbc7cd75a…2d3b`) on the Pool and PoolConfigurator.

## 6. Detection invariants & gotchas

1. **Same topics as Aave V3, different emitter.** Filter on `(4663, 0x91d1d929…)`. LayerBank V3 ([layerbank/v3.md](../layerbank/v3.md)) is another Aave V3 fork on Robinhood Chain with the same topics and some of the same underlyings (WETH, USDG, NVDA).
2. **The admin is a single EOA.** `0x11505259…` owns the AddressesProvider and is the ACL admin. An impl swap or a reserve change needs no timelock.
3. **The PONS oracle reverts.** `getAssetPrice(PONS)` reverted with `0x158767e7` on 2026-10-30. Any action that prices PONS (borrow, withdraw, liquidation for PONS holders) can fail until the feed recovers.
4. **No sequencer oracle.** The PriceOracleSentinel has no sequencer feed set, so the L2-downtime grace period does not take effect.
5. **Tokenized-stock collateral.** NVDA and TSLA prices move with stock-market hours. Watch oracle staleness outside trading hours.
6. **`liquidationCall` is a PUSH3 in bytecode.** Its selector `0x00a718a9` starts with a zero byte. A `PUSH4` scan of the impl misses it. Use the `LiquidationCall` topic for detection.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic, = Aave V3) =====
TOPIC_KSK_SUPPLY             = '\x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61'
TOPIC_KSK_WITHDRAW           = '\x3115d1449a7b732c986cba18244e897a450f61e1bb8d589cd2e69e6c8924f9f7'
TOPIC_KSK_BORROW             = '\xb3d084820fb1a9decffb176436bd02558d15fac9b0ddfed8c465bc7359d7dce0'
TOPIC_KSK_REPAY              = '\xa534c8dbe71f871f9f3530e97a74601fea17b426cae02e1c5aee42c96c784051'
TOPIC_KSK_LIQUIDATION_CALL   = '\xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286'
TOPIC_KSK_FLASHLOAN          = '\xefefaba5e921573100900a3ad9cf29f222d995fb3b6045797eaea7521bd8d6f0'
TOPIC_KSK_RESERVE_DATA_UPD   = '\x804c9b842b2748a22bb64b345453a3de7ca54a6ca45ce00d415894979e22897a'
TOPIC_KSK_DEFICIT_CREATED    = '\x2bccfb3fad376d59d7accf970515eb77b2f27b082c90ed0fb15583dd5a942699'
TOPIC_KSK_DEFICIT_COVERED    = '\x84b203e49f1a4b553088061534231969a68ad1c81be192205e96d23a206cb26a'
TOPIC_KSK_UPGRADED           = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
-- ===== Selectors =====
SEL_KSK_SUPPLY               = '\x617ba037'
SEL_KSK_WITHDRAW             = '\x69328dec'
SEL_KSK_BORROW               = '\xa415bcad'
SEL_KSK_REPAY                = '\x573ade81'
SEL_KSK_LIQUIDATION_CALL     = '\x00a718a9'
-- ===== Robinhood Chain (4663) =====
ROBIN_KSK_POOL               = '\x91d1d9294a5e735746fa3e68bf88286ca6c485d5'
ROBIN_KSK_POOL_CONFIGURATOR  = '\x0d2b0f1ebff46af300c13f58d5d2551fec6c130c'
ROBIN_KSK_ADDRESSES_PROVIDER = '\x3e9a28d988ee889b47bf257f0e103960721475d0'
ROBIN_KSK_DATA_PROVIDER      = '\x9ff935c295925540077416042e3a0e1be5276401'
ROBIN_KSK_ORACLE             = '\x1fb1bb18297467181a0698d2ba332b95cd13fb30'
ROBIN_KSK_ACL_MANAGER        = '\xea7e4d2cffc6bc7289241b3efa026c09e4bc9f65'
ROBIN_KSK_SENTINEL           = '\x95eb34aae3ffb1dbfebe6e26b730827da7ab9a88'
ROBIN_KSK_ADMIN              = '\x11505259b3ac74c3901cc058c59cafbc931808d1'
```

## 8. Verification & sources

- **Addresses:** `ADDRESSES_PROVIDER()` on the DataProvider, then `getPool()`, `getPoolConfigurator()`, `getPriceOracle()`, `getACLManager()`, `getACLAdmin()`, `getPriceOracleSentinel()`, `getPoolDataProvider()`, `owner()`, `getMarketId()` read live; reserves from `getAllReservesTokens()` and `getReserveTokensAddresses(asset)`; aToken `symbol()`; oracle `getSourceOfAsset()` and feed `description()`. Proxy impls from the EIP-1967 slot.
- **Selectors:** `PUSH4` / `PUSH3` constants in the Pool impl bytecode. `POOL_REVISION()` = 7.
- **Topics:** recomputed locally; Pool logs read with `eth_getLogs` via `https://rpc.mainnet.chain.robinhood.com` (the publicnode endpoint rejects log ranges).
- **Chain coverage:** `eth_getCode` on all nine public RPCs.
- **TVL:** `api.llama.fi/protocol/kaskad` (Robinhood Chain 355,669 USD; borrowed 30,571 USD on 2026-10-30).

Sources:
- [DefiLlama Kaskad](https://defillama.com/protocol/kaskad) · [Kaskad](https://kaskad.app) · [`Kaskad-Lending` on GitHub](https://github.com/Kaskad-Lending) (audit report by Sherlock, 2026-04-30)
- [`aave-dao/aave-v3-origin`](https://github.com/aave-dao/aave-v3-origin) — upstream signatures.
