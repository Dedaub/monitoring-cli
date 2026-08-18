# Pike (Pike Markets) — Topics, Selectors, Addresses (Base; +Sonic off-target; relaunch after April-2024 Beta exploit)

**Status:** verified against Base and Sonic mainnet RPC, the canonical `nutsfinance/pike-local-markets` source + `deployments/1.0.0/` JSONs, and the live address registry, on 2026-06-08. Topics/selectors recomputed locally as `keccak256(signature)`; a representative subset additionally confirmed against live `eth_getLogs` on Base. Non-obvious claims cross-checked against primary sources (GitHub, docs, DefiLlama, post-mortems) — see §11.
**Scope:** the live, relaunched **Pike Markets** money-market protocol. The user requested Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon. **Among those seven, the relaunched protocol is deployed on Base (8453) ONLY.** The only other mainnet is **Sonic (146)** — off the requested list but documented in §6 for completeness. **Ethereum, BNB, Avalanche, Arbitrum, Optimism, and Polygon carry NO live Pike Markets contracts** (`eth_getCode = 0x` for every relaunch address). The one Pike-related contract still on a target chain is the **dead, exploited April-2024 Beta spoke on Ethereum** (`0xFC7599…`, permanently pointed at the attacker's implementation) — see §1.4 / §9. Topics + selectors are **chain-agnostic**; addresses are network-specific.

Pike Markets is **NOT an Aave fork and NOT a cross-chain protocol at the contract level.** It is a **Compound-V2-style** money market (cToken-equivalent `pTokens`, a `RiskEngine` = Comptroller-equivalent, per-second interest accrual) restructured onto a **Synthetix-Cannon "static-diamond Router" + beacon-proxy** deployment model. The original **Pike Beta** (a Wormhole-spoke + Circle-CCTP "universal liquidity" design, repo `nutsfinance/pike-protocol`) was **exploited twice in April 2024** (Apr 26: ~299k USDC via a CCTP receiver-spoofing flaw; Apr 30: 99,970 ARB + 64,126 OP + 479 ETH ≈ $1.6M via a storage-layout / `initialized`-slot bug that let the attacker re-upgrade the spokes without admin). That Beta was wound down and its hub/spoke/gateway contracts are **not** the protocol documented here. The relaunch ("Pike Markets", version line **1.0.0 / 1.0.1**) ships per-chain, per-`protocolId` markets and has no in-contract bridging — cross-chain UX (the "POCA" chain-abstraction layer) is off-chain/SDK, not an on-chain message-passing module in the market. **TVL is tiny (~$5k on Base as of 2026-06).**

> **Architecture you must internalize (verified on-chain 2026-06-08):**
> - **Factory** is an **ERC-1967 proxy** (UUPS-upgradeable; live impl `0x2295De6c…` on Base). It deploys **protocols** (`deployProtocol`) and **markets** (`deployMarket`).
> - Every **pToken / RiskEngine / OracleEngine / Timelock instance is a `BeaconProxy`** (~321 B). Its EIP-1967 **beacon slot** points to a per-type beacon (`pTokenBeacon`, `reBeacon`, `oracleEngineBeacon`, `timelockBeacon`). Each beacon's `implementation()` returns a **Router** (e.g. `PTokenRouter`, `RiskEngineRouter`) — a Synthetix-style **static diamond** that `delegatecall`s per-selector into the modules (`PTokenModule`, `RiskEngineModule`, `RBACModule`, `DoubleJumpRateModel`, `UpgradeModule`, `OwnableModule`). So: **instance → beacon → Router(static-diamond) → modules.**
> - There is **no EIP-1967 impl slot on the market instances** (it is `0x`; they are beacon proxies). Resolve their logic via the **beacon slot**, then the beacon's `implementation()`.
> - Upgrades are announced by a **custom `Upgraded(address indexed self, address implementation)`** (topic0 `0x5d611f…`) emitted by the module's `UpgradeModule._upgradeTo`, **NOT** the standard EIP-1967 `Upgraded(address)` (`0xbc7cd7…`). Watch the custom topic.
> - Markets are grouped under a numeric **`protocolId`** (Base has `protocol-1` and `protocol-2`, each with its own RiskEngine / OracleEngine / Timelock). The same underlying (e.g. WETH) appears as a **different pToken per protocolId** — always key on `(chainId, pToken address)`, never on symbol.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally on 2026-06-08. The "live ✓" marks were additionally confirmed by `eth_getLogs` on the Base `protocol-1` market set (deploy window ~block 28,359,135–28,408,135).

### 1.1 pToken (the lending market — Compound-cToken-equivalent, also an ERC-4626 vault) — emitter = each market proxy

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x10a0132d3bf8c82a7fb93a86160f3074ca5c3e5706fa2bcdf0e2b5fd495af09b` | `Borrow(address borrower, address onBehalfOf, uint256 borrowAmount, uint256 accountBorrows, uint256 totalBorrows)` | **Pike-specific shape** — 5 fields incl. `onBehalfOf`. NOT the Compound 4-field `Borrow`. |
| `0x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1` | `RepayBorrow(address payer, address onBehalfOf, uint256 repayAmount, uint256 accountBorrows, uint256 totalBorrows)` | Pike-specific (5 fields, `onBehalfOf`). |
| `0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52` | `LiquidateBorrow(address liquidator, address borrower, uint256 repayAmount, address pTokenCollateral, uint256 seizeTokens)` | Liquidation. |
| `0x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04` | `AccrueInterest(uint256 cashPrior, uint256 totalReserves, uint256 borrowIndex, uint256 totalBorrows)` | live ✓. **4 fields** (Compound V2 had `interestAccumulated`/`borrowIndex`/`totalBorrows` = 3+cash; here it's cash/reserves/index/borrows). |
| `0xa7f7695027ccc863236f85a62b246476837f23e5e3a33f2f51076e695fc0d435` | `NewRiskEngine(address oldRiskEngine, address newRiskEngine)` | RiskEngine pointer change. |
| `0xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460` | `NewReserveFactor(uint256 oldReserveFactorMantissa, uint256 newReserveFactorMantissa)` | |
| `0x343132c776a0be7c01b8c5bf0b77b8d549e9f690fec5429f8537a1cbddfc8211` | `NewBorrowRateMax(uint256 oldBorrowRateMaxMantissa, uint256 newBorrowRateMaxMantissa)` | |
| `0xf5815f353a60e815cce7553e4f60c533a59d26b1b5504ea4b6db8d60da3e4da2` | `NewProtocolSeizeShare(uint256 oldProtocolSeizeShareMantissa, uint256 newProtocolSeizeShareMantissa)` | |
| `0xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5` | `ReservesAdded(address benefactor, uint256 addAmount, uint256 newTotalReserves)` | |
| `0x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e` | `ReservesReduced(address admin, uint256 reduceAmount, uint256 newTotalReserves)` | owner/governor withdraw. |
| `0xb47853100b79d8afa66237bdb4f7f09d96628ee23aa8aac8a8c21a901c67ddb2` | `EmergencyWithdrawn(address caller, uint256 reduceAmount, uint256 newTotalReserves)` | **emergency-guardian reserve drain — high-value risk signal.** |

**ERC-4626 + ERC-20 events on the same pToken** (it `is IERC4626`):

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7` | `Deposit(address sender, address owner, uint256 assets, uint256 shares)` | live ✓. Supply = canonical EIP-4626 `Deposit` (NOT a Compound `Mint`). |
| `0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db` | `Withdraw(address sender, address receiver, address owner, uint256 assets, uint256 shares)` | Redeem = canonical EIP-4626 `Withdraw`. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address from, address to, uint256 value)` | live ✓. pToken share ERC-20. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address owner, address spender, uint256 value)` | |

> **Supply/redeem are EIP-4626 `Deposit`/`Withdraw`, not Compound `Mint`/`Redeem`.** `Deposit`/`Withdraw` topic0s are **identical to every other 4626 vault** — always filter on `(chainId, pToken address, topic0)`, never topic0 alone.

### 1.2 RiskEngine (Comptroller-equivalent: collateral/liquidity/caps/e-mode/pause) — emitter = each `protocolId` RiskEngine proxy

| topic0 | Event |
|--------|-------|
| `0xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f` | `MarketListed(address pToken)` (live ✓) |
| `0x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5` | `MarketEntered(address pToken, address account)` (live ✓) |
| `0xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d` | `MarketExited(address pToken, address account)` |
| `0xb6096f872da1c7cac11fa0cdc6821167b7a7bf4ff7311bd6c75ed6bf6cd94c8a` | `NewMarketConfiguration(address pToken, (uint256,uint256,uint256) oldConfig, (uint256,uint256,uint256) newConfig)` — config = `(collateralFactor, liquidationThreshold, liquidationIncentive)` mantissas. |
| `0x1a0021cca023e9811a0a964f30d2da6bb1965942ae513f7bb832201afeba1ac9` | `NewEModeConfiguration(uint8 categoryId, (uint256,uint256,uint256) oldConfig, (uint256,uint256,uint256) newConfig)` |
| `0xf983bd49b5b2e7a360b78748957ecf7825d00682b5fe568cff5bd7ad517559e1` | `EModeUpdated(uint8 categoryId, address pToken, bool allowed, bool collateralStatus, bool borrowStatus)` |
| `0x1d4c404354f452297c7f1bb8afdc53b2b8d8da2770642a6c67a85ab510369e78` | `EModeSwitched(address account, uint8 oldCategory, uint8 newCategory)` |
| `0x9b3997c824f3d09376e362107b8dca151da2934a4e7e4be420bd56657d088b8d` | `NewOracleEngine(address oldOracleEngine, address newOracleEngine)` |
| `0xce695d31b2630bb932e37a4559701b4b0bc915604a8e33d885d0731a0b851a93` | `NewReserveShares(uint256 newOwnerShareMantissa, uint256 newConfiguratorShareMantissa)` |
| `0x1f536152953482a0667405c822665e8b8adfb105836e7f77a9553329b4a183a0` | `NewCloseFactor(address indexed pToken, uint256 oldCloseFactorMantissa, uint256 newCloseFactorMantissa)` |
| `0x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6` | `NewBorrowCap(address indexed pToken, uint256 newBorrowCap)` |
| `0x9e0ad9cee10bdf36b7fbd38910c0bdff0f275ace679b45b922381c2723d676f8` | `NewSupplyCap(address indexed pToken, uint256 newSupplyCap)` |
| `0xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0` | `ActionPaused(string action, bool pauseState)` — **global pause.** |
| `0x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0` | `ActionPaused(address indexed pToken, string action, bool pauseState)` — **per-market pause** (different topic0 — overloaded name, disambiguated by arity). |
| `0xcb325b7784f78486e42849c7a50b8c5ee008d00cd90e108a58912c0fcb6288b4` | `DelegateUpdated(address indexed approver, address indexed delegate, bool approved)` — borrow/redeem delegation. |

> **`ActionPaused` is overloaded** (global `(string,bool)` vs per-market `(address,string,bool)`) → **two distinct topic0s**. Both are pause signals; the per-market one carries `pToken` indexed.

### 1.3 Factory & OracleEngine & RBAC

**Factory** (emitter = Factory proxy `0xaF912C96…` on Base):

| topic0 | Event |
|--------|-------|
| `0x0f7d42df10be499af5f3fe1f1e1586e5a0d78001fa24b1a34d308d1528c93b06` | `ProtocolDeployed(uint256 indexed protocolId, address indexed riskEngine, address indexed timelock, address oracleEngine, address initialGovernor, address emergencyExecutor)` |
| `0x99ecb6d103aad630c7cfaf1e4740d66de70c4b3ba8b1ed0c12cd8518d103b8d6` | `PTokenDeployed(uint256 indexed protocolId, uint256 indexed index, address indexed pToken, address timelock)` (live ✓ — fired for pUSDC/pWETH/pwstETH at block 28,359,318–319) |

**OracleEngine** (emitter = each `protocolId` OracleEngine proxy):

| topic0 | Event |
|--------|-------|
| `0x9ec48f3eba657ecf35433ba16b16477b0c8953da6aed6c106ecd6588c4e03747` | `AssetConfigSet(address indexed asset, address mainOracle, address fallbackOracle, uint256 lowerBoundRatio, uint256 upperBoundRatio)` — dual-oracle (primary + fallback) with sanity bounds. |

**RBACModule** (access control on every Router instance — Factory/RiskEngine/pToken/Oracle):

| topic0 | Event |
|--------|-------|
| `0x6f5b794a7ab7ff229b8295cd19ae4b5c92bce69238df1ad84eb47f9c9dcd4cd3` | `PermissionGranted(bytes32 permission, address target)` |
| `0x93f50f299c97f9dbc6c8c8193bc0d1072f9ed27d38a021fc70fb48f6c86dcc61` | `PermissionRevoked(bytes32 permission, address target)` |
| `0x19e1e66f8a3583a426c5b9158ae001518c778903588a97f7de9730a630a823fa` | `NestedPermissionGranted(bytes32 permission, address nestedAddress, address target)` |
| `0x9d8ca82c123be539d081ee2857821e29e873b7bc7d05a5dbca13586ba304b46b` | `NestedPermissionRevoked(bytes32 permission, address nestedAddress, address target)` |

**Upgrade / ownership** (Synthetix-style modules — fired by every Router instance and the Factory):

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x5d611f318680d00598bb735d61bacf0c514c6b50e1e5ad30040a4df2b12791c7` | `Upgraded(address indexed self, address implementation)` | **WATCH THIS — custom upgrade event (Router impl swap), NOT EIP-1967 `Upgraded(address)`.** |
| `0xb532073b38c83145e3e5135377a08bf9aab55bc0fd7c1179cd4fb995d2a5159c` | `OwnerChanged(address oldOwner, address newOwner)` | Synthetix `OwnableModule`. |
| `0x906a1c6bd7e3091ea86693dd029a831c19049ce77f1dce2ce0bab1cacbabce22` | `OwnerNominated(address newOwner)` | two-step ownership. |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` | OZ `Initializable` — beacon/proxy init heartbeat. |

### 1.4 Dead Beta (exploited April 2024 — DO NOT treat as live)

The pre-relaunch **Pike Beta** (cross-chain spoke + Wormhole + CCTP) used a different contract set (repo `nutsfinance/pike-protocol`). Its **spoke** `0xFC7599cfFea9De127a9f9C748CCb451a34d2F063` is an ERC-1967 proxy that is **still on Ethereum mainnet** with its impl slot **permanently set to the attacker contract `0x1da4bc596bfb1087f2f7999b0340fcba03c47fbd`** (the malicious Apr-30 upgrade). Attacker EOA: `0x19066f7431df29A0910d287C8822936Bb7D89E23`. **No relaunch events/selectors below apply to it.** Treat any activity from `0xFC7599…` as historical/exploit forensics, never live protocol traffic.

---

## 2. Function signatures (chain-agnostic — `keccak256(sig)[0:4]`)

Selectors recomputed locally 2026-06-08. Because every instance is a beacon → Router static-diamond, **all of these resolve through the Router dispatcher** (the per-selector facet map), so a raw PUSH4 scan of the 321-byte instance proxy will NOT find them — verify presence by calling the view or by the Router's selector map, not by scanning the proxy bytecode.

### 2.1 pToken — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6e553f65` | `deposit(uint256 assets, address receiver)` → `uint256` | EIP-4626 supply. Emits `Deposit`. |
| `0x94bf804d` | `mint(uint256 shares, address receiver)` → `uint256` | EIP-4626 share-exact supply. (Note: arg order is `(amount, receiver)`, Pike-specific.) |
| `0xba087652` | `redeem(uint256 shares, address receiver, address owner)` → `uint256` | Emits `Withdraw`. |
| `0xb460af94` | `withdraw(uint256 assets, address receiver, address owner)` → `uint256` | Emits `Withdraw`. |
| `0xc5ebeaec` | `borrow(uint256 borrowAmount)` | Emits `Borrow`. |
| `0x70dc4f28` | `borrowOnBehalfOf(address onBehalfOf, uint256 borrowAmount)` | Delegated borrow → `Borrow.onBehalfOf`. |
| `0x0e752702` | `repayBorrow(uint256 repayAmount)` | Emits `RepayBorrow`. |
| `0x05fed2e7` | `repayBorrowOnBehalfOf(address onBehalfOf, uint256 repayAmount)` | |
| `0xf5e3c462` | `liquidateBorrow(address borrower, uint256 repayAmount, address pTokenCollateral)` | Emits `LiquidateBorrow`. |
| `0xb2a02ff1` | `seize(address liquidator, address borrower, uint256 seizeTokens)` | Cross-market seize (called by the paired pToken during liquidation). |
| `0xa6afed95` | `accrueInterest()` | Per-**second** accrual. Emits `AccrueInterest`. |
| `0x7821a514` | `addReserves(uint256 addAmount)` | Emits `ReservesAdded`. |
| `0x3659cfe6` | `upgradeTo(address newImplementation)` | Router/UUPS impl swap → custom `Upgraded(self,impl)`. |

### 2.2 pToken — views (per-second model; `accrualBlockTimestamp`, not block number)

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0x38d52e0f` | `asset()` | underlying ERC-20 (EIP-4626). |
| `0x92b888ae` | `riskEngine()` | owning RiskEngine. |
| `0xbd6d894d` | `exchangeRateCurrent()` | accrues then returns rate (1e18). |
| `0x182df0f5` | `exchangeRateStored()` | rate w/o accrual. |
| `0x17bfdfbc` | `borrowBalanceCurrent(address account)` | accrued debt. |
| `0x3b1d21a2` | `getCash()` | underlying held. |
| `0x01e1d114` | `totalAssets()` | EIP-4626 total underlying. |
| `0x47bd3718` | `totalBorrows()` | outstanding borrows (verified live). |
| `0x52609750` | `borrowRatePerSecond()` | per-second borrow rate (DoubleJumpRateModel; verified live). |
| `0xb1d38974` | `supplyRatePerSecond()` | per-second supply rate (verified live). |
| `0xcfa99201` | `accrualBlockTimestamp()` | last accrual unix timestamp (per-second model; verified live = 2025 ts). |

### 2.3 RiskEngine

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc2998238` | `enterMarkets(address[] pTokens)` → `uint256[]` | Emits `MarketEntered`. |
| `0xede4edd0` | `exitMarket(address pTokenAddress)` | Emits `MarketExited`. |
| `0x09eb6b50` | `switchEMode(uint8 newCategoryId)` | Emits `EModeSwitched`. |
| `0xddbf54fd` | `updateDelegate(address delegate, bool approved)` | Emits `DelegateUpdated`. |
| `0xcab4f84c` | `supportMarket(address pToken)` | Emits `MarketListed`. |
| `0x993f59cb` | `setCloseFactor(address pToken, uint256 newCloseFactorMantissa)` | |
| `0xd14a0983` | `setBorrowCap(address pToken, uint256 newBorrowCap)` | |
| `0x571f03e5` | `setSupplyCap(address pToken, uint256 newSupplyCap)` | |
| `0x5ec88c79` | `getAccountLiquidity(address account)` → `(Error, liquidity, shortfall)` | shortfall>0 = liquidatable. |
| `0x4d4ace3c` | `getAccountBorrowLiquidity(address account)` | |
| `0x0ef332ca` | `liquidateCalculateSeizeTokens(address borrower, address pTokenBorrowed, address pTokenCollateral, uint256 actualRepayAmount)` → `(Error, uint256)` | |

### 2.4 Factory & OracleEngine

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x3f66b5fe` | `deployProtocol(address governor, address guardian, uint256 ownerShareMantissa, uint256 configuratorShareMantissa)` → `(riskEngine, oracleEngine, governorTimelock)` | Factory — emits `ProtocolDeployed`. |
| `0x92537b2c` | `deployMarket((uint256,address,uint256,uint256,uint256,uint256,string,string,uint8))` | Factory — `PTokenSetup` struct → emits `PTokenDeployed`. |
| `0xfc57d4df` | `getUnderlyingPrice(address pToken)` → `uint256` | OracleEngine — USD price scaled to 1e(36-decimals). |
| `0x41976e09` | `getPrice(address asset)` → `uint256` | OracleEngine. |
| `0xaaf10f42` | `getImplementation()` → `address` | every Router instance (Synthetix). |
| `0x5c60da1b` | `implementation()` → `address` | the beacons (resolve instance logic). |

---

## 3. Addresses — Base mainnet (chain ID 8453) — the ONLY live deployment among the 7 requested chains

Source: `nutsfinance/pike-local-markets/deployments/1.0.0/base-mainnet/` (+ per-protocol `deploymentData.json`). All verified via `eth_getCode` / `eth_call` on `https://base-rpc.publicnode.com` on 2026-06-08. Wiring confirmed: `pUSDC.asset() = 0x8335…2913` (native Base USDC), `pUSDC.riskEngine() = 0x4c37…1633`, `pTokenBeacon.implementation() = PTokenRouter 0x77df…8005`, `Factory.owner() = 0xE80b…a2a1`.

> **Two factories exist on Base.** The **production** Factory that actually deployed the live markets is **`0xaF912C968830f0D74927471B231213C0aD908AA3`** (a 176-byte ERC-1967 proxy; impl `0x2295De6c…`). The repo top-level `Factory.json` records that **impl** address `0x2295De6c853fBE8bB0FD73d5D55a33E2cf192cA7` (10,869 B logic) directly — both are present on-chain; **the proxy `0xaF912…` is the one to monitor.**

### 3.1 Core / shared infrastructure (Base)

| Role | Address | One-liner |
|------|---------|-----------|
| **Factory** (ERC-1967 proxy) | `0xaF912C968830f0D74927471B231213C0aD908AA3` | Deploys protocols + markets; emits `ProtocolDeployed`/`PTokenDeployed`. |
| Factory impl (UUPS logic) | `0x2295De6c853fBE8bB0FD73d5D55a33E2cf192cA7` | 10,869 B logic behind the Factory proxy. |
| **pTokenBeacon** | `0x7647ed486D5CaAdb43BBd4BEc61ef4D5A54879bA` | Beacon for every pToken proxy → `implementation()` = PTokenRouter. |
| **PTokenRouter** (static diamond) | `0x77df165efc8115c89e851c7fbc44d50f5a878005` | pToken module dispatcher. |
| **reBeacon** (RiskEngine beacon) | `0xe306253438ac6f787e4924aCfDc481CC7096B8a6` | Beacon for every RiskEngine proxy. |
| **RiskEngineRouter** | `0x57c5ce7a3617eae4963cbcf036322ebd656e5017` | RiskEngine module dispatcher. |
| **oracleEngineBeacon** | `0xF8A9ec45037B1Ad7636fD804DB7fa8dF19DAeD9f` | Beacon for OracleEngine proxies. |
| **timelockBeacon** | `0xA13a352bbD90C65a07bA1a03a28Dd3957a81dD16` | Beacon for Timelock proxies. |
| PTokenModule | `0x92E8a47C642e69c697a6ee34caE7823e252EC3Ab` | pToken logic module. |
| RiskEngineModule | `0x3011bB0b680288CFa60c360202e2808Ba667116c` | RiskEngine logic module. |
| RBACModule | `0x3A6c10D205Cd5Ad333BA958ADb10550911fD27ce` | Access-control module (RBAC permissions). |
| DoubleJumpRateModel | `0x1e65051E8d4Ddc57d15ADed66cf3A58F0bF2C884` | Per-second double-jump IRM module. |
| InitialModuleBeacon | `0x3450822d04bb4F62fe599474783e4aA66810b52f` | Bootstrap module/beacon. |
| ChainlinkOracleProvider | `0xAB8FE0aFaD9D1872aAa9d006D0E004Aac30d8608` | Chainlink price source (UUPS proxy). |
| ChainlinkOracleComposite | `0x90352dC31FF6cE51E92C3d5e3ED75E00fa024feE` | Composite (LST/LP) Chainlink source. |
| PythOracleProvider | `0x4E2664B17352719bd7Ea3DFbE198fE7eed873dB7` | Pyth price source (UUPS proxy). |
| Protocol owner / initialGovernor | `0xE80bbcAB9E20fc193Ef768B68d69F363a7f9a2a1` | `owner()` of Factory + every RiskEngine; Timelock governor. |

> The repo also publishes "global" `OracleEngine.json` (`0xa62E4C74…`), `Timelock.json` (`0x4453…aB06`), `RiskEngineModule`-set, etc. — these are the **template/default** singletons; the **per-protocol live instances** are in §3.2/§3.3.

### 3.2 protocol-1 (Base) — primary market set

| Role | Address |
|------|---------|
| **RiskEngine** (beacon proxy) | `0x4c3774aA26f01d36E728016C26b3730537051633` |
| **OracleEngine** (beacon proxy) | `0xec4E0D97C5bE3A66e4712ae77938f8CDA945F8E0` |
| **Timelock** (beacon proxy) | `0x554EA2e4b5DccFE79bD772C175CB16754Db9704e` |

| Symbol | pToken (market proxy) | Underlying |
|--------|-----------------------|-----------|
| **pUSDC** | `0x20F2A7e0397b31c2E10c6589C2F706F508D4B6D3` | USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| pWETH | `0x3c07bD02168EAB139F13b208A1762AC9ac73f84f` | WETH `0x4200000000000000000000000000000000000006` |
| pweETH | `0xBeD0F3ef6D77C34b68DC6C53F2B90E3FF20935fC` | weETH `0x04C0599Ae5A44757c0af6F9eC3b93da8976c150A` |
| pwstETH | `0x9DbecA1819e88E2DE95168E8971EdebB41fF7e7E` | wstETH `0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452` |
| pWETHwstETH | `0xdEc254D13cd995793D03513F4bBE12b3120444A8` | `0x8453aabFF7d2A7B91953b62820806EE7Ab88864A` (paired-collateral token) |
| pwstETHweETH | `0xCf27c860d74a14f4021091f8476C9DCA8AE77Fab` | `0xD628F04b67FfeD935e8aFCf944D0791ABe345972` (paired-collateral token) |

### 3.3 protocol-2 (Base) — second market set (separate RiskEngine/Oracle/Timelock)

| Role | Address |
|------|---------|
| **RiskEngine** | `0x1d2Fd1DDA993dd874577D971062fc46E8a4083C6` |
| **OracleEngine** | `0x639a47a7a371d54e0A06c3a0f62772a583447dfc` |
| **Timelock** | `0x993B917C8A23a0a5E60f03a05c25A9580Bdd6939` |

| Symbol | pToken | Underlying |
|--------|--------|-----------|
| pWETH | `0xaBA720dB10134404a4D4D8Fee4C2e7F2Be043e58` | WETH `0x4200…0006` |
| pweETH | `0x21eeb4Bea6f638E8E6eB28dcC40e72e71933341f` | weETH `0x04C0…150A` |
| pwstETH | `0xE37de9807d60649d943F42ddCf6C498fCDb6e71C` | wstETH `0xc1CB…e452` |
| pWETHwstETH | `0x6AF0EEC07cedbD188d930772bd97099cb1c80B7A` | `0x8453…864A` |
| pwstETHweETH | `0x8B8860f826433569895e3F9921123406a1EA7e37` | `0xD628…5972` |

> **Same underlying, two pTokens.** e.g. WETH = `0x3c07bD02…` (protocol-1) **and** `0xaBA720dB…` (protocol-2). The two protocols are independent risk silos with independent governors/oracles. Never aggregate by symbol — key on the pToken address.

---

## 4. Addresses — every other requested chain: NO Pike Markets (verified absent)

`eth_getCode` returned `0x` for **all** relaunch addresses (Factory proxy/impl, pTokenBeacon, RiskEngine, pUSDC, OracleEngine, Timelock) on each of:

| Chain | ID | Pike Markets? | Note |
|---|---|---|---|
| **Ethereum** | 1 | ❌ none live | **Only** the dead, exploited **Beta spoke `0xFC7599…`** (impl = attacker `0x1da4…7fbd`) remains — §1.4/§9. |
| **BNB Smart Chain** | 56 | ❌ none | no Pike contracts of any kind. |
| **Avalanche C-Chain** | 43114 | ❌ none | no Pike contracts. |
| **Arbitrum One** | 42161 | ❌ none | Beta was here in 2024 (exploited, wound down); relaunch absent. DefiLlama lists Arbitrum as "configured" but TVL = 0 and code = `0x`. |
| **Optimism** | 10 | ❌ none | same as Arbitrum — Beta exploited & gone, relaunch absent. |
| **Polygon PoS** | 137 | ❌ none | no Pike contracts. |

> **Documentation/DefiLlama drift to be aware of:** Pike's site and DefiLlama still list "Ethereum, Base, Optimism, Arbitrum." **On-chain, only Base is live** (plus off-list Sonic). Treat ETH/OP/ARB Pike Markets claims as outdated/aspirational until `eth_getCode` says otherwise.

---

## 5. Addresses — Sonic mainnet (chain ID 146) — OFF the requested 7-chain list (documented for completeness)

Source: `deployments/1.0.0/sonic-mainnet/`. Verified live on `https://sonic-rpc.publicnode.com` (chainId 146). **Same architecture and same topic0s/selectors as Base** (chain-agnostic). Listed because it is the only other live mainnet — exclude from the 7-chain monitoring scope unless Sonic is added.

| Role | Address |
|------|---------|
| Factory impl | `0xBA1a5B3685F3C71de164291CF02F91639D23211e` |
| pTokenBeacon | `0xB26eee8606Ec913b8e14A473486524a48a8F6D87` |
| PTokenRouter | `0xf9d55142257dc6ffb42bf6ed5a97a3e7334a21a6` |
| reBeacon | `0xF8A9ec45037B1Ad7636fD804DB7fa8dF19DAeD9f` |
| RiskEngineRouter | `0x231724576d523c7b82d2f2bb536c0469afb0d9b3` |
| **protocol-1 RiskEngine** | `0x9d6c337D4a2f5179c03c26B9d909C2ac6a150979` |
| protocol-1 OracleEngine | `0xcef149051bDeD77bCc73353bb268418a5C70f086` |
| protocol-1 Timelock | `0x6825d84350754Cfe64028f6D738A2E92a5De3bdE` |
| pwS (wS market) | `0x639D9dD66EB95655E5eB154CC2498fF9A78f8EB5` → underlying `0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38` |
| pstS | `0x9F1864cFBCDf6d10A403aE79b820Fa0153919a5E` → `0xE5DA20F15420aD15DE0fa650600aFc998bbE3955` |
| pwOS | `0x9ed3eab6Df6b6b07601717eC336DfFD97A8fdE98` → `0x9F0dF7799f6FdAd409300080cfF680f5A23df4b1` |
| pwSstS | `0x016E759c1144499af34Db367C34A8D2c5347Aa43` → `0x9afD6A2923a0F9369d07E9392cf1B4148391b419` |
| pwSwOS | `0xD6a631850CB6395dBb07FaAd2BDecFD88eF927e0` → `0xc71bbbf481fb6dDbEe3389a0e4676eccCdb08e5c` |

Protocol owner = `0xE80bbcAB9E20fc193Ef768B68d69F363a7f9a2a1` (same EOA as Base). Sonic Timelock template `0x1e65051E…` reuses the literal Base used for its DoubleJumpRateModel — **key every address on `(chainId, address)`.**

---

## 6. Cross-chain summary

| Chain | ID | Pike Markets live? | Factory (proxy) | Notes |
|---|---|---|---|---|
| **Base** | 8453 | ✅ yes (protocol-1 + protocol-2) | `0xaF912C96…` | only live market among the 7; ~$5k TVL. |
| Sonic | 146 | ✅ yes (off-list) | impl `0xBA1a5B36…` | not in requested scope. |
| Ethereum | 1 | ❌ | — | dead Beta spoke `0xFC7599…` only. |
| Arbitrum One | 42161 | ❌ | — | Beta exploited 2024, gone. |
| Optimism | 10 | ❌ | — | Beta exploited 2024, gone. |
| BNB | 56 | ❌ | — | nothing. |
| Avalanche | 43114 | ❌ | — | nothing. |
| Polygon PoS | 137 | ❌ | — | nothing. |

**Vanity-address tell:** none of the Base/Sonic addresses are vanity. The same protocol-owner EOA `0xE80b…a2a1` and reused literals across chains (e.g. `0xF8A9ec45…` is `reBeacon` on Base but `oracleEngineBeacon` on Sonic; `0x1e65051E…` is Timelock-template on Sonic but DoubleJumpRateModel on Base) make **`(chainId, address)` keying mandatory.**

**Three things to internalize:**
1. **Base is the whole monitorable footprint** (of the 7). Two independent risk silos (`protocol-1`, `protocol-2`).
2. **Compound-V2 semantics, EIP-4626 surface, Synthetix-router/beacon plumbing.** Supply/redeem = `Deposit`/`Withdraw`; borrow/repay/liquidate = Pike's 5-field `Borrow`/`RepayBorrow`/`LiquidateBorrow`; accrual is **per-second** with a **4-field `AccrueInterest`**.
3. **Upgrades use the custom `Upgraded(self,impl)` topic** `0x5d611f…`, not EIP-1967, and instances are **beacon proxies with empty impl slots.**

---

## 7. Proxies (old & new)

EIP-1967 slots — impl `0x360894…382bbc`, beacon `0xa3f0ad…133d50`, admin `0xb53127…5d6103`.

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Factory** | **ERC-1967 / UUPS proxy** | impl slot non-empty: Base `0xaF912…` → `0x2295De6c…` (live, read 2026-06-08). | `upgradeTo` gated by protocol owner `0xE80b…a2a1`. |
| **pToken** (every market) | **BeaconProxy** | impl slot = **`0x`**; **beacon slot** = `0x7647ed48…` (Base). Resolve logic via `beacon.implementation()` = PTokenRouter `0x77df…8005`. | beacon swap (owner) + per-instance `upgradeTo` via Router. |
| **RiskEngine** (every protocolId) | **BeaconProxy** | beacon slot = `reBeacon 0xe3062534…` (Base). | beacon/owner. |
| **OracleEngine** | **BeaconProxy** | beacon slot = `oracleEngineBeacon 0xF8A9ec45…` (Base). | beacon/owner. |
| **Timelock** | **BeaconProxy** | beacon slot = `timelockBeacon 0xA13a352b…` (Base). | governor. |
| **PTokenRouter / RiskEngineRouter** | **Static diamond (Synthetix Cannon Router)** | per-selector `delegatecall` to modules; not EIP-1967. | replaced by deploying a new Router + beacon swap. |
| ChainlinkOracleProvider / PythOracleProvider / ChainlinkOracleComposite | **ERC-1967 / UUPS proxy** | repo ships `*.InitialProxy.json` + `*.Proxy.json`; impl slot non-empty. | owner. |
| **Modules** (PTokenModule, RiskEngineModule, RBACModule, DoubleJumpRateModel) | **immutable logic** | plain contracts; impl slot = `0x`; only ever `delegatecall`-target of a Router. | n/a (redeploy). |
| **Beacons** (pTokenBeacon, reBeacon, …) | **UpgradeableBeacon** | expose `implementation()` (`0x5c60da1b`); they hold the Router address. | owner. |

**Upgrade topic to watch:** the **custom** `Upgraded(address indexed self, address implementation)` = `0x5d611f318680d00598bb735d61bacf0c514c6b50e1e5ad30040a4df2b12791c7` (fired by `UpgradeModule._upgradeTo` on a Router instance). The standard EIP-1967 `Upgraded(address)` (`0xbc7cd7…`) is what the **Factory** ERC-1967 proxy and the oracle UUPS proxies emit. Confirm any upgrade by reading the impl/beacon slot at the event block.

**Dead Beta proxy:** `0xFC7599…` on Ethereum is an ERC-1967 proxy whose impl slot is the attacker contract `0x1da4bc59…` — a permanent record of the malicious Apr-2024 upgrade, not a live Pike contract.

---

## 8. Decimals & math

- **Per-second interest** (`accrueInterest` uses `accrualBlockTimestamp`, not block number). `borrowIndex` grows each accrual; `AccrueInterest` carries `(cashPrior, totalReserves, borrowIndex, totalBorrows)`.
- Mantissas are **1e18** (`collateralFactorMantissa`, `liquidationThresholdMantissa`, `liquidationIncentiveMantissa`, `reserveFactorMantissa`, `closeFactorMantissa`, `protocolSeizeShareMantissa`).
- pToken `exchangeRate` is 1e18-scaled. pToken is EIP-4626: `convertToShares`/`convertToAssets`/`totalAssets` follow vault math.
- **OracleEngine `getUnderlyingPrice(pToken)` returns USD scaled to `1e(36 - underlyingDecimals)`** (Compound-style; verified `getUnderlyingPrice(pUSDC)` returns a 1e30-ish value for 6-dec USDC). Dual-oracle: primary + fallback with `lowerBoundRatio`/`upperBoundRatio` sanity bounds.
- Underlyings: USDC 6-dec; WETH/weETH/wstETH/wS/OS 18-dec.

---

## 9. Detection invariants & gotchas

1. **Base is the only live deployment among the 7 requested chains.** Ethereum/BNB/Avalanche/Arbitrum/Optimism/Polygon have **no live Pike Markets** (`eth_getCode = 0x`). The only Pike contract on a target chain is the **dead exploited Beta spoke `0xFC7599…` on Ethereum** — exclude it from live detection.
2. **NOT an Aave/Compound clone in topic terms.** Supply/redeem are **EIP-4626 `Deposit`/`Withdraw`** (collide with every 4626 vault). Borrow/repay/liquidate are **Pike's own 5-field events** (different topic0s from Compound and Aave). Always filter `(chainId, pToken address, topic0)`.
3. **`AccrueInterest` is 4-field and per-second** (`cashPrior, totalReserves, borrowIndex, totalBorrows`) — topic0 `0x4dec04e7…` is unique to Pike (≠ Compound/Moonwell). Accrual indexed on timestamp, not block.
4. **Two independent protocols on Base (`protocol-1`, `protocol-2`)**, each with its own RiskEngine/OracleEngine/Timelock and its own pToken for the same underlying. **Never aggregate by symbol; key on the pToken address.**
5. **Beacon-proxy instances have an empty EIP-1967 impl slot.** To resolve a market's logic: read the **beacon slot** (`0xa3f0ad…`) → call `beacon.implementation()` (= a Router) → the Router is a static diamond dispatching to modules. A PUSH4 scan of the 321-byte instance proxy finds **none** of the §2 selectors.
6. **Watch the CUSTOM upgrade event** `Upgraded(address indexed self, address implementation)` (`0x5d611f…`) on Router instances — the storage-layout/upgrade class of bug is exactly what killed the Beta. The EIP-1967 `Upgraded(address)` only appears on the Factory/oracle UUPS proxies. Also watch `OwnerChanged`/`OwnerNominated` (`0xb532073b…`/`0x906a1c6b…`).
7. **`onBehalfOf` ≠ `tx.from`.** `Borrow`/`RepayBorrow` carry an explicit `onBehalfOf`; `borrowOnBehalfOf`/`repayBorrowOnBehalfOf` + the RiskEngine `DelegateUpdated` delegation mean the position owner is in the event, not the sender.
8. **`EmergencyWithdrawn` (`0xb478531…`) and the two `ActionPaused` topics are top-tier risk signals** — an emergency guardian can pull reserves and pause actions globally or per-market outside the normal governance path. Monitor alongside `Upgraded`.
9. **`ActionPaused` is overloaded** → two topic0s (global `(string,bool)` `0xef159d9a…`; per-market `(address,string,bool)` `0x71aec636…`). Track both.
10. **Liquidations: detect by `LiquidateBorrow` (`0x298637f6…`)**, with the cross-market `seize` and `LiquidateBorrow.pTokenCollateral` naming the seized market. `RiskEngine.liquidateCalculateSeizeTokens` computes the seize amount via the OracleEngine.
11. **Reused address literals across chains and across roles** (e.g. `0xF8A9ec45…`, `0x1e65051E…`) — **`(chainId, address)` keying is mandatory.** The same owner EOA `0xE80b…a2a1` controls Base + Sonic.
12. **Two factories on Base:** monitor the **proxy `0xaF912C96…`** (it emits `ProtocolDeployed`/`PTokenDeployed`), not the bare impl `0x2295De6c…`.
13. **`mint(uint256,address)` arg order is `(amount, receiver)`** — Pike's `mint` is a supply (4626-ish) helper, not an ERC-721/Compound-cToken mint; selector `0x94bf804d`.
14. **Watch `PTokenDeployed`/`ProtocolDeployed` for new markets/silos** — new markets are added by the Factory at runtime (the live ones were created Apr 2025).

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== pToken events (chain-agnostic) =====
TOPIC_BORROW                 = '\x10a0132d3bf8c82a7fb93a86160f3074ca5c3e5706fa2bcdf0e2b5fd495af09b'  -- 5-field, onBehalfOf
TOPIC_REPAY_BORROW           = '\x1a2a22cb034d26d1854bdc6666a5b91fe25efbbb5dcad3b0355478d6f5c362a1'
TOPIC_LIQUIDATE_BORROW       = '\x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52'
TOPIC_ACCRUE_INTEREST        = '\x4dec04e750ca11537cabcd8a9eab06494de08da3735bc8871cd41250e190bc04'  -- 4-field, per-second
TOPIC_NEW_RISK_ENGINE        = '\xa7f7695027ccc863236f85a62b246476837f23e5e3a33f2f51076e695fc0d435'
TOPIC_NEW_RESERVE_FACTOR     = '\xaaa68312e2ea9d50e16af5068410ab56e1a1fd06037b1a35664812c30f821460'
TOPIC_NEW_PROTOCOL_SEIZE     = '\xf5815f353a60e815cce7553e4f60c533a59d26b1b5504ea4b6db8d60da3e4da2'
TOPIC_RESERVES_ADDED         = '\xa91e67c5ea634cd43a12c5a482724b03de01e85ca68702a53d0c2f45cb7c1dc5'
TOPIC_RESERVES_REDUCED       = '\x3bad0c59cf2f06e7314077049f48a93578cd16f5ef92329f1dab1420a99c177e'
TOPIC_EMERGENCY_WITHDRAWN    = '\xb47853100b79d8afa66237bdb4f7f09d96628ee23aa8aac8a8c21a901c67ddb2'  -- guardian reserve drain
-- EIP-4626 supply/redeem (collide with all 4626 vaults — filter by address)
TOPIC_DEPOSIT_4626           = '\xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7'
TOPIC_WITHDRAW_4626          = '\xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db'
TOPIC_ERC20_TRANSFER         = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- ===== RiskEngine events =====
TOPIC_MARKET_LISTED          = '\xcf583bb0c569eb967f806b11601c4cb93c10310485c67add5f8362c2f212321f'
TOPIC_MARKET_ENTERED         = '\x3ab23ab0d51cccc0c3085aec51f99228625aa1a922b3a8ca89a26b0f2027a1a5'
TOPIC_MARKET_EXITED          = '\xe699a64c18b07ac5b7301aa273f36a2287239eb9501d81950672794afba29a0d'
TOPIC_NEW_MARKET_CONFIG      = '\xb6096f872da1c7cac11fa0cdc6821167b7a7bf4ff7311bd6c75ed6bf6cd94c8a'
TOPIC_NEW_EMODE_CONFIG       = '\x1a0021cca023e9811a0a964f30d2da6bb1965942ae513f7bb832201afeba1ac9'
TOPIC_EMODE_UPDATED          = '\xf983bd49b5b2e7a360b78748957ecf7825d00682b5fe568cff5bd7ad517559e1'
TOPIC_EMODE_SWITCHED         = '\x1d4c404354f452297c7f1bb8afdc53b2b8d8da2770642a6c67a85ab510369e78'
TOPIC_NEW_ORACLE_ENGINE      = '\x9b3997c824f3d09376e362107b8dca151da2934a4e7e4be420bd56657d088b8d'
TOPIC_NEW_RESERVE_SHARES     = '\xce695d31b2630bb932e37a4559701b4b0bc915604a8e33d885d0731a0b851a93'
TOPIC_NEW_CLOSE_FACTOR       = '\x1f536152953482a0667405c822665e8b8adfb105836e7f77a9553329b4a183a0'
TOPIC_NEW_BORROW_CAP         = '\x6f1951b2aad10f3fc81b86d91105b413a5b3f847a34bbc5ce1904201b14438f6'
TOPIC_NEW_SUPPLY_CAP         = '\x9e0ad9cee10bdf36b7fbd38910c0bdff0f275ace679b45b922381c2723d676f8'
TOPIC_ACTION_PAUSED_GLOBAL   = '\xef159d9a32b2472e32b098f954f3ce62d232939f1c207070b584df1814de2de0'
TOPIC_ACTION_PAUSED_MARKET   = '\x71aec636243f9709bb0007ae15e9afb8150ab01716d75fd7573be5cc096e03b0'
TOPIC_DELEGATE_UPDATED       = '\xcb325b7784f78486e42849c7a50b8c5ee008d00cd90e108a58912c0fcb6288b4'
-- ===== Factory / Oracle / RBAC / upgrade =====
TOPIC_PROTOCOL_DEPLOYED      = '\x0f7d42df10be499af5f3fe1f1e1586e5a0d78001fa24b1a34d308d1528c93b06'
TOPIC_PTOKEN_DEPLOYED        = '\x99ecb6d103aad630c7cfaf1e4740d66de70c4b3ba8b1ed0c12cd8518d103b8d6'
TOPIC_ASSET_CONFIG_SET       = '\x9ec48f3eba657ecf35433ba16b16477b0c8953da6aed6c106ecd6588c4e03747'
TOPIC_PERMISSION_GRANTED     = '\x6f5b794a7ab7ff229b8295cd19ae4b5c92bce69238df1ad84eb47f9c9dcd4cd3'
TOPIC_PERMISSION_REVOKED     = '\x93f50f299c97f9dbc6c8c8193bc0d1072f9ed27d38a021fc70fb48f6c86dcc61'
TOPIC_UPGRADED_CUSTOM        = '\x5d611f318680d00598bb735d61bacf0c514c6b50e1e5ad30040a4df2b12791c7'  -- Upgraded(self,impl) — Router swap
TOPIC_UPGRADED_EIP1967       = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'  -- Factory/oracle UUPS proxy
TOPIC_OWNER_CHANGED          = '\xb532073b38c83145e3e5135377a08bf9aab55bc0fd7c1179cd4fb995d2a5159c'

-- ===== Selectors — pToken =====
SEL_DEPOSIT_4626             = '\x6e553f65'   -- deposit(uint256,address)
SEL_MINT_4626               = '\x94bf804d'   -- mint(uint256,address) (amount,receiver)
SEL_REDEEM                  = '\xba087652'   -- redeem(uint256,address,address)
SEL_WITHDRAW                = '\xb460af94'   -- withdraw(uint256,address,address)
SEL_BORROW                  = '\xc5ebeaec'   -- borrow(uint256)
SEL_BORROW_ON_BEHALF        = '\x70dc4f28'
SEL_REPAY_BORROW            = '\x0e752702'
SEL_REPAY_BORROW_ON_BEHALF  = '\x05fed2e7'
SEL_LIQUIDATE_BORROW        = '\xf5e3c462'   -- liquidateBorrow(address,uint256,address)
SEL_SEIZE                   = '\xb2a02ff1'
SEL_ACCRUE_INTEREST         = '\xa6afed95'
SEL_ADD_RESERVES            = '\x7821a514'
SEL_UPGRADE_TO              = '\x3659cfe6'
-- ===== Selectors — RiskEngine / Factory / Oracle =====
SEL_ENTER_MARKETS           = '\xc2998238'
SEL_EXIT_MARKET             = '\xede4edd0'
SEL_SWITCH_EMODE            = '\x09eb6b50'
SEL_UPDATE_DELEGATE         = '\xddbf54fd'
SEL_SUPPORT_MARKET          = '\xcab4f84c'
SEL_SET_CLOSE_FACTOR        = '\x993f59cb'
SEL_SET_BORROW_CAP          = '\xd14a0983'
SEL_SET_SUPPLY_CAP          = '\x571f03e5'
SEL_GET_ACCOUNT_LIQUIDITY   = '\x5ec88c79'
SEL_LIQ_CALC_SEIZE          = '\x0ef332ca'   -- liquidateCalculateSeizeTokens(address,address,address,uint256)
SEL_DEPLOY_PROTOCOL         = '\x3f66b5fe'
SEL_DEPLOY_MARKET           = '\x92537b2c'
SEL_GET_UNDERLYING_PRICE    = '\xfc57d4df'
SEL_GET_IMPLEMENTATION      = '\xaaf10f42'
SEL_BEACON_IMPLEMENTATION   = '\x5c60da1b'

-- ===== Base mainnet (chain ID 8453) — the only live deployment of the 7 =====
PIKE_BASE_FACTORY_PROXY      = '\xaf912c968830f0d74927471b231213c0ad908aa3'
PIKE_BASE_FACTORY_IMPL       = '\x2295de6c853fbe8bb0fd73d5d55a33e2cf192ca7'
PIKE_BASE_PTOKEN_BEACON      = '\x7647ed486d5caadb43bbd4bec61ef4d5a54879ba'
PIKE_BASE_PTOKEN_ROUTER      = '\x77df165efc8115c89e851c7fbc44d50f5a878005'
PIKE_BASE_RE_BEACON          = '\xe306253438ac6f787e4924acfdc481cc7096b8a6'
PIKE_BASE_RE_ROUTER          = '\x57c5ce7a3617eae4963cbcf036322ebd656e5017'
PIKE_BASE_OWNER              = '\xe80bbcab9e20fc193ef768b68d69f363a7f9a2a1'
-- protocol-1
PIKE_BASE_P1_RISK_ENGINE     = '\x4c3774aa26f01d36e728016c26b3730537051633'
PIKE_BASE_P1_ORACLE_ENGINE   = '\xec4e0d97c5be3a66e4712ae77938f8cda945f8e0'
PIKE_BASE_P1_TIMELOCK        = '\x554ea2e4b5dccfe79bd772c175cb16754db9704e'
PIKE_BASE_P1_PUSDC           = '\x20f2a7e0397b31c2e10c6589c2f706f508d4b6d3'
PIKE_BASE_P1_PWETH           = '\x3c07bd02168eab139f13b208a1762ac9ac73f84f'
PIKE_BASE_P1_PWEETH          = '\xbed0f3ef6d77c34b68dc6c53f2b90e3ff20935fc'
PIKE_BASE_P1_PWSTETH         = '\x9dbeca1819e88e2de95168e8971edebb41ff7e7e'
-- protocol-2
PIKE_BASE_P2_RISK_ENGINE     = '\x1d2fd1dda993dd874577d971062fc46e8a4083c6'
PIKE_BASE_P2_ORACLE_ENGINE   = '\x639a47a7a371d54e0a06c3a0f62772a583447dfc'
PIKE_BASE_P2_TIMELOCK        = '\x993b917c8a23a0a5e60f03a05c25a9580bdd6939'
PIKE_BASE_P2_PWETH           = '\xaba720db10134404a4d4d8fee4c2e7f2be043e58'
-- DEAD exploited Beta spoke on ETHEREUM (do NOT treat as live)
PIKE_BETA_SPOKE_ETH_DEAD     = '\xfc7599cffea9de127a9f9c748ccb451a34d2f063'
PIKE_BETA_ATTACKER_IMPL      = '\x1da4bc596bfb1087f2f7999b0340fcba03c47fbd'
-- Universal
EIP1967_IMPL_SLOT            = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_BEACON_SLOT          = '\xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50'
```

---

## 11. Verification & sources

How constants in this doc were verified (2026-06-08):

- **Event topic0 / selectors:** all recomputed locally as `keccak256(signature)` (canonical form: no names, `uint`→`uint256`, struct as `(type,…)` — `BaseConfiguration` flattened to `(uint256,uint256,uint256)`). The following were additionally confirmed against **live `eth_getLogs`** on the Base `protocol-1` market set (deploy window ~block 28,359,135+): `AccrueInterest`, `Deposit(4626)`, `Transfer` on **pUSDC `0x20F2A7e0…`**; `MarketListed`, `MarketEntered` on the **RiskEngine `0x4c3774aA…`**; `PTokenDeployed` on the **Factory `0xaF912C96…`** (3 logs at block 28,359,318–319 with indexed `protocolId=1`, `index=0/1/2`, and pToken addresses matching pUSDC/pWETH/pwstETH). `Borrow`/`RepayBorrow`/`LiquidateBorrow`/`ProtocolDeployed` are source-derived (sparse on-chain at this TVL; `pWETH.totalBorrows()` is non-zero, confirming borrow flow occurred).
- **Architecture:** read EIP-1967 **impl/beacon slots live**: pUSDC/RiskEngine impl slot = `0x` and **beacon slot** = pTokenBeacon `0x7647ed48…` / reBeacon `0xe3062534…`; `pTokenBeacon.implementation()` = PTokenRouter `0x77df…8005`; Factory `0xaF912…` impl slot = `0x2295De6c…`. Verified `pUSDC.asset()` (native Base USDC), `pUSDC.riskEngine()`, `pUSDC.symbol()` = "pUSDC", `Factory.owner()`/`RiskEngine.owner()` = `0xE80b…a2a1`, and `OracleEngine.getUnderlyingPrice(pUSDC)` returns a non-zero USD price.
- **Addresses:** parsed from `nutsfinance/pike-local-markets/deployments/1.0.0/{base-mainnet,sonic-mainnet}/` JSONs (top-level + per-`protocol-N/deploymentData.json`) and existence-checked via `eth_getCode` on the correct chain.
- **Chain coverage:** `eth_getCode` run for the Factory proxy/impl, pTokenBeacon, proto-1 RiskEngine, pUSDC, OracleEngine, and Timelock on **all seven requested chains** — **present only on Base**; `0x` on Ethereum, BNB, Avalanche, Arbitrum, Optimism, Polygon. The repo has mainnet deploy dirs only for `base-mainnet` and `sonic-mainnet` (the rest are testnets: arb-sepolia, base-sepolia, op-sepolia, unichain-sepolia, monad-testnet, bera-bepolia, sonic-testnet). The **dead Beta spoke `0xFC7599…`** is present on Ethereum with impl slot = attacker `0x1da4bc59…` (verified live).

Authoritative sources:

- [`nutsfinance/pike-local-markets`](https://github.com/nutsfinance/pike-local-markets) — canonical relaunch source (`src/Factory.sol`, `src/pike-market/modules/**`, `src/oracles/**`, `src/governance/Timelock.sol`, interfaces, and `deployments/1.0.0/**` address JSONs).
- [`nutsfinance/pike-protocol`](https://github.com/nutsfinance/pike-protocol) — the **deprecated Beta** (cross-chain spoke/CCTP design; exploited Apr 2024).
- [Pike docs](https://docs.pike.finance/) (developer-docs/smart-contracts: factory, risk-engine, ptokens, oracle-engine, timelock) and the linked [address registry](https://address-registry.vercel.app/).
- [DefiLlama — Pike](https://defillama.com/protocol/pike) (chains/TVL).
- Explorers: [BaseScan — Factory](https://basescan.org/address/0xaF912C968830f0D74927471B231213C0aD908AA3) · [BaseScan — pUSDC](https://basescan.org/address/0x20F2A7e0397b31c2E10c6589C2F706F508D4B6D3) · [SonicScan — Factory impl](https://sonicscan.org/address/0xBA1a5B3685F3C71de164291CF02F91639D23211e).
- Post-mortems (Beta exploit): Halborn, CertiK, QuillAudits, MerkleScience, Rekt — Apr 26 & 30, 2024.

### Independent fact-check (2026-06-08)

| Claim | Verdict | Basis |
|---|---|---|
| Relaunch is live only on Base among the 7 requested chains | **confirmed** | `eth_getCode` present on Base, `0x` on the other six; repo has only base/sonic mainnet dirs; DefiLlama shows TVL only on Base. |
| Docs/DefiLlama also list ETH/OP/Arbitrum | **confirmed but on-chain-absent** | listed as "configured" but `eth_getCode = 0x` and TVL = 0 → treat as outdated/aspirational. |
| Pike Markets is Compound-V2-style, not an Aave fork | **confirmed** | `RiskEngine` = Comptroller, `pToken`, `liquidateBorrow`/`seize`/`closeFactor`/`enterMarkets`, per-second `accrueInterest` — Compound semantics; but supply/redeem are EIP-4626. |
| Supply/redeem emit EIP-4626 `Deposit`/`Withdraw` (not Compound `Mint`/`Redeem`) | **confirmed** | `IPToken is IERC4626`; live `Deposit` log on pUSDC; topic0 matches 4626. |
| Instances are beacon proxies; logic via Synthetix Router static diamond | **confirmed** | live beacon-slot reads + `beacon.implementation()` = Router; empty impl slot on instances. |
| Upgrade event is custom `Upgraded(self,impl)` not EIP-1967 | **confirmed** | source `UpgradeModule._upgradeTo`/`IUpgrade`; topic0 `0x5d611f…` ≠ `0xbc7cd7…`. |
| April-2024 Beta exploit: ~$1.9M over Apr 26 + Apr 30; storage-layout/`initialized` upgrade bug + CCTP receiver spoofing | **confirmed** | multiple post-mortems (Halborn/CertiK/QuillAudits/Rekt) + Pike's own announcement (99,970 ARB / 64,126 OP / 479 ETH). |
| Exploited Beta spoke `0xFC7599…` still on Ethereum, impl = attacker contract | **confirmed** | live `eth_getCode` (177 B proxy) + impl-slot read = `0x1da4bc59…` (attacker contract from post-mortems). |
| Cross-chain messaging is NOT in the relaunched on-chain market | **confirmed** | no Wormhole/CCTP module in `src/`; markets are single-chain; chain abstraction (POCA) is off-chain/SDK. |
