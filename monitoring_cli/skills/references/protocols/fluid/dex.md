# Fluid — DEX (smart collateral / smart debt AMM) — Topics, Selectors, Addresses

**Status:** topic0/selectors computed locally via keccak from `Instadapp/fluid-contracts-public` (`main`); factory + DEX Lite + counts re-verified on-chain **2026-06-05** (publicnode). Covers **DEX V1 (poolT1)** + **DEX Lite** (the next-gen singleton). There is **no separate "DEX V2"** product (see §3).
**Scope:** Fluid **DEX** — an AMM whose liquidity IS the [`liquidity-layer.md`](liquidity-layer.md) (so the same capital can be lending collateral AND DEX liquidity — "smart collateral / smart debt"). Other modules: [`vaults.md`](vaults.md), [`lending.md`](lending.md), [`periphery.md`](periphery.md). Index: [`README.md`](README.md). FLUID/token: [`liquidity-layer.md`](liquidity-layer.md).
**Key fact:** **DEX V1 (poolT1)** pools are deployed by the **DexFactory** `0x91716C4EDA1Fb55e84Bf8b4c7085f84285c19085` (same address on all 5 chains). **DEX Lite** is a separate, gas-optimized **singleton** (all pools in one contract) that is **Ethereum-mainnet-only** today. Both share liquidity with the Liquidity Layer, so DEX liquidity changes also surface as a Liquidity-Layer `LogOperate` in the same tx.

> **Chains:** DexFactory (V1) on ETH(1), Base(8453), Arbitrum(42161), Polygon(137), BNB(56) — CREATE2-deterministic, byte-identical. DEX Lite singleton on **ETH only**. **NOT on Optimism/Avalanche.**

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 DexFactory
Source: `contracts/protocols/dex/factory/main.sol`.

| topic0 | Event |
|--------|-------|
| `0x80d4769bbf5966f1c91cdab7c477bd8f74016bd5f5ed3ad18af6b32e29f6da7f` | `LogDexDeployed(address indexed dex, uint256 indexed dexId)` — a new DEX pool is created |
| `0x48cc5b4660fae22eabe5e803ee595e63572773d114bcd54ecc118c1efa8d75af` | `LogSetDeployer(address indexed deployer, bool indexed allowed)` |
| `0x0a1c6cd77aa2e405e482adf6ee6cf190a27682b6dd1234403f7602e5203c83bb` | `LogSetGlobalAuth(address indexed auth, bool indexed allowed)` |
| `0x6dc7f25a946e48c9a5dec5f836659d8470be4b350e53b78df89037bffcdb2687` | `LogSetDexAuth(address indexed dex, bool indexed allowed, address indexed auth)` |
| `0x862a194379bf36d614b7bbc811097fc33a06ab67366fb58db1f4de91438e369f` | `LogSetDexDeploymentLogic(address indexed deploymentLogic, bool indexed allowed)` |

> Subscribe to `LogDexDeployed` to discover every V1 pool on a chain. (`LogSetDeployer`/`LogSetGlobalAuth` topic0s are shared with the VaultFactory — same canonical signatures.)

### 1.2 DEX V1 — poolT1 coreModule (12 events; the swap/liquidity workhorses)
Source: `contracts/protocols/dex/poolT1/coreModule/events.sol` (all 12 confirmed current 2026-06-05).

| topic0 | Event |
|--------|-------|
| `0xdc004dbca4ef9c966218431ee5d9133d337ad018dd5b5c5493722803f75c64f7` | `Swap(bool swap0to1, uint256 amountIn, uint256 amountOut, address to)` — **★ workhorse swap** |
| `0x255672effa3d8ba46e409fc964ae332b84d3107ba3a5096b22734606519528a3` | `LogDepositPerfectColLiquidity(uint256,uint256,uint256)` |
| `0x6f837572c1ef6e010a841ff938d593ec054984fefe29df2a0634bbf01f4db35b` | `LogWithdrawPerfectColLiquidity(uint256,uint256,uint256)` |
| `0x486d991947a88580130ff5acd9ec54dc37fb8da4bf6ab78871d5cd6fa5816df7` | `LogBorrowPerfectDebtLiquidity(uint256,uint256,uint256)` |
| `0x03b77b44c2fe8816d55a2e4f90a87538c48d4148e35224c07049fd2304fa3a30` | `LogPaybackPerfectDebtLiquidity(uint256,uint256,uint256)` |
| `0xbfea92097a2487d6a5ccf7b7adc36b6002238f3106568ba4359770f4b67365a4` | `LogDepositColLiquidity(uint256,uint256,uint256)` |
| `0xb61c7f3b23fe9335cc6c6a6e7036457758470877e61a19a5b4924e1ff8289624` | `LogWithdrawColLiquidity(uint256,uint256,uint256)` |
| `0x7f81427bed699dc7e687c5ddae6061932938818f79fc0e68903d55ef75ca4561` | `LogBorrowDebtLiquidity(uint256,uint256,uint256)` |
| `0xb69f152a70520703fe7ab4872a0cb3928386b68cf3c6c83c5d1fc08d196991e8` | `LogPaybackDebtLiquidity(uint256,uint256,uint256)` |
| `0xc98f37914e06db36c18654484db85c4bb864575a1b9f8181133ff33dea2d34f3` | `LogWithdrawColInOneToken(uint256,uint256,uint256)` |
| `0x97dfa84cbffcf65b8d034f057439472bc93868a66cc0e728c2faffb00f8b4923` | `LogPaybackDebtInOneToken(uint256,uint256,uint256)` |
| `0x063def03d41a2957d43156b97c271f3e4adea600722defb2cf6ebf9a27650056` | `LogArbitrage(int256,uint256)` |

### 1.3 DEX Lite — singleton (Ethereum-only; bit-packed, all non-indexed)
Source: `contracts/protocols/dexLite/{other,adminModule}/events.sol`. Struct args expanded to ABI tuples (`DexKey=(address token0,address token1,bytes32 salt)`). **All Lite events are non-indexed — everything is in `data`.**

| topic0 | Event |
|--------|-------|
| `0xfbce846c23a724e6e61161894819ec46c90a8d3dd96e90e7342c6ef49ffb539c` | `LogSwap(uint256 swapData, uint256 dexVariables)` — **★ Lite swap** (bit-packed; ≠ V1 `Swap`) |
| `0x5215e0d1b2a71023436cdb272e4954aec234cb46d793100d02d1e955820badcf` | `LogDeposit((address,address,bytes32),bytes8,uint256,uint256,uint256)` |
| `0xc3f541673644e6c18d377e885be08b51d0d95367f2b038b3e83ecac980a77fba` | `LogWithdraw((address,address,bytes32),bytes8,uint256,uint256,uint256)` |
| `0x0f3c8652ed6961216fd2437ded3dd9abbdf4661d9c3e37fad5e62e335d99f682` | `LogInitialize((address,address,bytes32),bytes8,uint256,uint256,(...))` — a new Lite pool (15-field `InitializeParams`) |
| `0xc5811e82a3e001f10b79bea9e9d8744e42416fd0328aa30af018fa3351f34343` | `LogUpdateFeeAndRevenueCut((address,address,bytes32),bytes8,uint256,uint256,uint256)` |
| `0x7f2be73aa0d4fdbdb0f05733e6bf6aea23fc4ff062e20fa3b5a8118083589426` | `LogUpdateRebalancingStatus((address,address,bytes32),bytes8,uint256,bool)` |
| `0x35c6dac8e06d7b162f4bd26386a89b1632a5f59830c7ffa4a45220db8b68ce48` | `LogUpdateRangePercents((address,address,bytes32),bytes8,uint256,uint256,uint256,uint256,uint256)` |
| `0x376f9eadf790d01bd6a33e0d48bd73376b113fe21a2ea4b267bf3c81047f81bc` | `LogUpdateShiftTime((address,address,bytes32),bytes8,uint256,uint256)` |
| `0x0e0abfebb6263ebebbb763cf6b606b7b2d7ebee45238589e982a1737831e3878` | `LogUpdateCenterPriceLimits((address,address,bytes32),bytes8,uint256,uint256,uint256)` |
| `0xab364b1339c5d754b249cb39f82ef00a3881d1d97bdc631b109a10e2d8845e36` | `LogUpdateThresholdPercent((address,address,bytes32),bytes8,uint256,uint256,uint256,uint256,uint256)` |
| `0x30642295ea4176e23cf68fd310f4a94e617b45ad97f54e541157229e634a6184` | `LogUpdateCenterPriceAddress((address,address,bytes32),bytes8,uint256,uint256,uint256,uint256,uint256)` |
| `0xb873643b3104ddd26927dec7f9a08aa22d03ac20ada0295a2de7e1a6c60f2a51` | `LogUpdateAuth(address,bool)` |
| `0x1d5b4b04795ebb3901db9b61da375220c34f0661b7f6068a43831ce89d14df10` | `LogCollectRevenue(address[],uint256[],address)` |
| `0x116a7728df267da3fd3e4d5a3943585553ba46e2416287dbc49e275ac20f3c26` | `LogUpdateExtraDataAddress(address)` |

> **`LogSwap` (Lite, `0xfbce846c…`) ≠ `Swap` (V1, `0xdc004dbc…`)** — both are Fluid DEX swaps but distinct topic0 AND distinct args. V1 `Swap(bool,uint256,uint256,address)` is per-pool; Lite `LogSwap(uint256 swapData, uint256 dexVariables)` is bit-packed on the singleton (`swapData` packs dexId | swap0To1 | amountIn | amountOut — decode via `libraries/dexLiteSlotsLink.sol`). Disambiguate by **emitting address** (a poolT1 pool vs the single FluidDexLite). `dexId` = `bytes8(keccak256(abi.encode(DexKey)))`.

---

## 2. Function signatures (chain-agnostic)

### 2.1 DexFactory
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x87339817` | `deployDex(address dexDeploymentLogic, bytes dexDeploymentData)` | deployer-gated. Emits `LogDexDeployed`. |
| `0x93656c17` | `totalDexes()` | `uint256` count. |
| `0x12e366aa` | `getDexAddress(uint256 dexId)` | deterministic pool addr. |
| `0x4502d063` | `isGlobalAuth(address)` | |
| `0xfbeeca2c` | `isDexAuth(address dex, address auth)` | |

### 2.2 DEX V1 — poolT1
```
swapIn(bool swap0to1, uint256 amountIn, uint256 amountOutMin, address to) -> uint256 amountOut
swapOut(bool swap0to1, uint256 amountOut, uint256 amountInMax, address to) -> uint256 amountIn
# deposit/withdraw/borrow/payback perfect + single-sided variants mirror the Log* events in §1.2
```

### 2.3 DEX Lite — singleton (core swaps + admin via delegatecall)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7fc9d4ad` | `swapSingle((address,address,bytes32),bool,int256,uint256,address,bool,bytes,bytes)` | single-hop |
| `0x5bb49959` | `swapHop(address[],(address,address,bytes32)[],int256,uint256[],(address,bool))` | multi-hop |
| `0xba53454c` | `initialize(((address,address,bytes32),uint256,uint256,bool,uint256×11))` | create a Lite pool (admin, delegatecall) |
| `0x34196c64` | `deposit((address,address,bytes32),uint256,uint256,uint256,uint256)` | |
| `0xab1ffc02` | `withdraw((address,address,bytes32),uint256,uint256,address,uint256,uint256)` | |
| `0xcb710d45` | `collectRevenue(address[],uint256[],address)` | |
| `0xe9c771b2` | `updateAuth(address,bool)` | |
| `0xb5c736e4` | `readFromStorage(bytes32)` | raw sload |

(Plus per-pool admin setters `updateFeeAndRevenueCut`/`updateRebalancingStatus`/`updateRangePercents`/`updateShiftTime`/`updateCenterPriceLimits`/`updateThresholdPercent`/`updateCenterPriceAddress`/`updateExtraDataAddress` — all `_onlyDelegateCall` into the singleton.)

---

## 3. Addresses

### 3.1 DexFactory (DEX V1) — shared across all 5 chains (CREATE2-deterministic)
`0x91716C4EDA1Fb55e84Bf8b4c7085f84285c19085` — deploys poolT1 pools; byte-identical bytecode on every chain. Individual pool addresses are per-chain — enumerate via `LogDexDeployed` / `FluidDexResolver` (see [`periphery.md`](periphery.md)).

**`totalDexes()` per chain (verified on-chain 2026-06-05):**

| Chain | totalDexes (V1) |
|-------|-----------------|
| Ethereum (1) | **45** |
| Arbitrum (42161) | **21** |
| Base (8453) | **18** |
| Polygon (137) | **8** |
| BNB (56) | **5** |

### 3.2 DEX Lite — Ethereum-mainnet only (singleton; verify before assuming on L2)
| Role | Address | One-liner |
|------|---------|-----------|
| **FluidDexLite** (singleton core) | `0xBbcb91440523216e2b87052A99F69c604A7b6e00` | All Lite pools in one contract, keyed by `dexId`. `code=16412 B`. **ETH only** (empty on Base/Arb/Polygon/BNB). |
| FluidDexLiteAdminModule | `0x305be0eAC8e3B118c358747de863A5779B26Dc5a` | delegatecall target for Lite admin/pool-init. ETH only. |
| FluidDexLiteResolver | `0x12a47cEB96A952E8D4A6eA9FE3b40b79bbaeb4e9` | reads Lite state. ETH only. |

> DEX Lite has **no factory and no `totalDexes`** — pools are created by `initialize(...)` directly on the singleton; enumerate off-chain via `LogInitialize` or the resolver.

---

## 4. "DEX V2" — does not exist (clarification)
There is **no `poolT2` / SmartDex / DEX V2** factory in the repo or `deployments.md`. The `dex/` tree has only `poolT1/` (V1 cores) and `smartLending/`. **`smartLending` is NOT a new AMM** — it's a set of ERC-4626 wrapper tokens (`fSL*`, deployed by a `SmartLendingFactory`) layered over existing T1 pools. The actual next-gen AMM is **DEX Lite** (§3.2), which plays the role people sometimes call "V2". See [`periphery.md`](periphery.md) for `SmartLendingResolver`.

---

## 5. Proxies
- DEX V1 pools are deployed by the **DexFactory** (Fluid module pattern). A pool does NOT custody its own reserves — liquidity is held in the Liquidity Layer, so a swap moves balances there (also visible as Liquidity `LogOperate`).
- **DEX Lite** delegatecalls its AdminModule from the singleton's storage context — on-chain you'll see admin calls hitting `0xBbcb9144…` (the singleton), not the admin module address directly.
- Liquidity-Layer InfiniteProxy: see [`liquidity-layer.md`](liquidity-layer.md).

---

## 6. Detection invariants & gotchas
1. **`Swap(bool,uint256,uint256,address)` (`0xdc004dbc…`) is the V1 workhorse** — `swap0to1` direction, then `amountIn`, `amountOut`, `to`. Fluid-specific layout (NOT Uniswap/Velodrome `Swap`).
2. **DEX V1 ≠ DEX Lite at the topic0 level.** Lite swaps are `LogSwap` (`0xfbce846c…`) on the singleton, bit-packed, non-indexed. To catch all Fluid DEX swaps, watch BOTH topic0s; to attribute, filter by emitting address.
3. **DEX liquidity ops mirror into the Liquidity Layer.** A V1 deposit/borrow also emits a Liquidity `LogOperate` (same tx). See [`liquidity-layer.md`](liquidity-layer.md).
4. **Smart collateral / smart debt:** the same capital can be a Vault's col/debt AND DEX liquidity (T2/T3/T4 vaults — see [`vaults.md`](vaults.md)). A single user action can emit Vault + DEX + Liquidity events.
5. **DEX Lite is Ethereum-only today** — don't index `0xBbcb9144…` on L2s (returns empty). Lite has no on-chain pool count; enumerate via `LogInitialize`.

---

## 7. Quick-copy detection constants (bytea-ready for PG)
```
-- ===== Topics =====
TOPIC_DEXF_DEX_DEPLOYED          = '\x80d4769bbf5966f1c91cdab7c477bd8f74016bd5f5ed3ad18af6b32e29f6da7f'
TOPIC_DEXF_SET_DEX_AUTH          = '\x6dc7f25a946e48c9a5dec5f836659d8470be4b350e53b78df89037bffcdb2687'
-- DEX V1 poolT1
TOPIC_DEX_SWAP                   = '\xdc004dbca4ef9c966218431ee5d9133d337ad018dd5b5c5493722803f75c64f7'
TOPIC_DEX_ARBITRAGE              = '\x063def03d41a2957d43156b97c271f3e4adea600722defb2cf6ebf9a27650056'
-- DEX Lite (singleton, ETH only)
TOPIC_DEXLITE_SWAP               = '\xfbce846c23a724e6e61161894819ec46c90a8d3dd96e90e7342c6ef49ffb539c'
TOPIC_DEXLITE_INITIALIZE         = '\x0f3c8652ed6961216fd2437ded3dd9abbdf4661d9c3e37fad5e62e335d99f682'
TOPIC_DEXLITE_DEPOSIT            = '\x5215e0d1b2a71023436cdb272e4954aec234cb46d793100d02d1e955820badcf'
TOPIC_DEXLITE_WITHDRAW           = '\xc3f541673644e6c18d377e885be08b51d0d95367f2b038b3e83ecac980a77fba'

-- ===== Selectors =====
SEL_DEXF_DEPLOY_DEX              = '\x87339817'
SEL_DEXF_TOTAL_DEXES             = '\x93656c17'
SEL_DEXLITE_SWAP_SINGLE          = '\x7fc9d4ad'
SEL_DEXLITE_SWAP_HOP             = '\x5bb49959'

-- ===== Addresses =====
FLUID_DEX_FACTORY                = '\x91716c4eda1fb55e84bf8b4c7085f84285c19085'  -- all 5 chains
FLUID_DEX_LITE                   = '\xbbcb91440523216e2b87052a99f69c604a7b6e00'  -- ETH only
FLUID_DEX_LITE_ADMIN            = '\x305be0eac8e3b118c358747de863a5779b26dc5a'  -- ETH only
FLUID_DEX_LITE_RESOLVER          = '\x12a47ceb96a952e8d4a6ea9fe3b40b79bbaeb4e9'  -- ETH only
```

---

## 8. Verification & sources
- **topic0/selector:** computed locally via keccak from `Instadapp/fluid-contracts-public` (`main`) `contracts/protocols/dex/{factory,poolT1}/...events.sol` and `contracts/protocols/dexLite/{other,adminModule}/events.sol` (struct args expanded). Spot-checked (`LogDexDeployed`, `LogSwap`, `totalDexes`) locally.
- **Addresses/counts:** DexFactory `eth_call totalDexes()` (`0x93656c17`) per chain (2026-06-05): ETH 45, Arb 21, Base 18, Polygon 8, BNB 5. DEX Lite singleton `0xBbcb9144…` has code on ETH (`getCode` len 32826 hex), empty on the other four chains.
- **Source:** [`Instadapp/fluid-contracts-public`](https://github.com/Instadapp/fluid-contracts-public) · `deployments/deployments.md` · Fluid docs (`FluidDexResolver`, `FluidDexLiteResolver`).
