# ApeSwap — Topics, Selectors, Addresses (BNB, Ethereum, Arbitrum, Polygon)

**Status:** verified against BNB (56), Ethereum (1), Arbitrum (42161), and Polygon (137) mainnet RPC on 2026-06-10. Base (8453), Avalanche (43114), and Optimism (10) confirmed absent.
**Scope:** AMM core (Factory + Pairs), Router, BANANA governance token, GNANA staking wrapper, MasterApe V1/V2 farming contracts, BananaSplit fee-sharing pool. Topics + selectors are chain-agnostic; addresses are network-specific.

ApeSwap is a **Uniswap V2 fork** DEX. BNB Smart Chain (BSC) is the primary deployment (6 347 pairs); Polygon has 1 463 pairs; Arbitrum has 94; Ethereum has 15. Arbitrum and Polygon share the **same factory address** (`0xCf083Be4164828f00cAE704EC15a36D711491284`) via deterministic deployment, but each chain compiled its own pair bytecode so the **`INIT_CODE_PAIR_HASH` differs per chain** — see §§3-6. Base, Avalanche, and Optimism have no ApeSwap deployment.

All contracts are **fully immutable** — no proxy pattern detected on any Factory, Router, pair, or farming contract (EIP-1967 logic slot is zero on all). Every core AMM topic0 and function selector is identical to Uniswap V2 (see [uniswap/v2.md](../uniswap/v2.md)); this doc focuses on what is ApeSwap-specific: correct addresses, the BANANA/GNANA token suite, MasterApe farming, and the key distinguishers. ApeSwap LP tokens use `name = "ApeSwapFinance LPs"`, `symbol = "APE-LP"` — **not** `"UNI-V2"`.

ApeSwap pairs use `apeCall(address sender, uint256 amount0, uint256 amount1, bytes data)` (selector `0xbecda363`) as the flash-loan callback interface instead of Uniswap V2's `uniswapV2Call`.

---

## 1. Topics

### 1.1 ApeSwapFactory

| topic0 | Event |
|--------|-------|
| `0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9` | `PairCreated(address indexed token0, address indexed token1, address pair, uint256)` |

Identical signature to Uniswap V2. `token0 < token1` is enforced before the event. The trailing `uint256` is the new `allPairs.length`.

### 1.2 ApeSwapPair (AMM events)

| topic0 | Event |
|--------|-------|
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address indexed sender, uint256 amount0, uint256 amount1)` |
| `0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496` | `Burn(address indexed sender, uint256 amount0, uint256 amount1, address indexed to)` |
| `0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822` | `Swap(address indexed sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, address indexed to)` |
| `0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1` | `Sync(uint112 reserve0, uint112 reserve1)` |

All identical to Uniswap V2; see [uniswap/v2.md](../uniswap/v2.md) for full field semantics.

### 1.3 ApeSwapPair (ERC-20 LP token events)

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |

### 1.4 MasterApe (V1 and V2) farming events

| topic0 | Event |
|--------|-------|
| `0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15` | `Deposit(address indexed user, uint256 indexed pid, uint256 amount)` |
| `0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568` | `Withdraw(address indexed user, uint256 indexed pid, uint256 amount)` |
| `0xbb757047c2b5f3974fe26b7c10f732e7bce710b0952a71082702781e62ae0595` | `EmergencyWithdraw(address indexed user, uint256 indexed pid, uint256 amount)` |

These topic0s are shared by both MasterApe V1 and V2. All three are BNB-only.

---

## 2. Function signatures

All AMM selectors are identical to Uniswap V2; only ApeSwap-specific selectors are listed here. See [uniswap/v2.md](../uniswap/v2.md) for the full Factory + Pair + ERC-20 selector table.

### 2.1 Router (all chains)

| Selector | Signature |
|----------|-----------|
| `0x38ed1739` | `swapExactTokensForTokens(uint256,uint256,address[],address,uint256)` |
| `0x8803dbee` | `swapTokensForExactTokens(uint256,uint256,address[],address,uint256)` |
| `0x7ff36ab5` | `swapExactETHForTokens(uint256,address[],address,uint256)` |
| `0x4a25d94a` | `swapTokensForExactETH(uint256,uint256,address[],address,uint256)` |
| `0x18cbafe5` | `swapExactTokensForETH(uint256,uint256,address[],address,uint256)` |
| `0xfb3bdb41` | `swapETHForExactTokens(uint256,address[],address,uint256)` |
| `0xe8e33700` | `addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)` |
| `0xf305d719` | `addLiquidityETH(address,uint256,uint256,uint256,address,uint256)` |
| `0xbaa2abde` | `removeLiquidity(address,address,uint256,uint256,uint256,address,uint256)` |
| `0x02751cec` | `removeLiquidityETH(address,uint256,uint256,uint256,address,uint256)` |

### 2.2 Factory

| Selector | Signature |
|----------|-----------|
| `0xc9c65396` | `createPair(address tokenA, address tokenB)` |
| `0xe6a43905` | `getPair(address, address)` |
| `0x1e3dd18b` | `allPairs(uint256)` |
| `0x574f2ba3` | `allPairsLength()` |

### 2.3 MasterApe (V1 + V2)

| Selector | Signature |
|----------|-----------|
| `0xe2bbb158` | `deposit(uint256 pid, uint256 amount)` |
| `0x441a3e70` | `withdraw(uint256 pid, uint256 amount)` |
| `0x5312ea8e` | `emergencyWithdraw(uint256 pid)` |

### 2.4 ApeSwap flash-loan callback (ApeSwapPair)

| Selector | Signature |
|----------|-----------|
| `0xbecda363` | `apeCall(address sender, uint256 amount0, uint256 amount1, bytes data)` |

This replaces Uniswap V2's `uniswapV2Call`. Any contract receiving flash-loan callbacks from ApeSwap pairs must implement this selector, not `uniswapV2Call`.

---

## 3. Addresses — BNB (56)

Primary deployment. All addresses verified via live RPC calls.

| Contract | Address | Notes |
|----------|---------|-------|
| Factory | `0x0841BD0B734E4F5853f0dD8d7Ea041c241fb0Da6` | `allPairsLength()` = 6 347. `feeToSetter` = `0x7b26A27af246b4E482f37eF24e9a3f83c3FC7f1C` |
| Router | `0xcF0feBd3f17CEf5b47b0cD257aCf6025c5BFf3b7` | `factory()` → Factory above; `WETH()` = WBNB `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` |
| BANANA token | `0x603c7f932ED1fc6575303D8Fb018fDCBb0f39a95` | `symbol()` = `BANANA`, `name()` = `ApeSwapFinance Banana`, 18 decimals. Note: the widely-cited address `0x603c7f...97662` has **no bytecode** on BSC — that is a documentation error. |
| GNANA token | `0xdDb3Bd8645775F59496c821E4F55A7eA6A6dc299` | `symbol()` = `GNANA`, `name()` = `Golden Banana`, 18 decimals. Staking wrapper; users convert BANANA → GNANA (1.389:1 ratio). |
| MasterApe V1 | `0x5c8D727b265DBAfaba67E050f2f739cAeEB4A6F9` | 221 pools. Emits `Deposit` / `Withdraw` / `EmergencyWithdraw`. `startBlock` = 4 860 914. |
| MasterApe V2 | `0x71354AC3c695dfB1d3f595AfA5D4364e9e06339B` | 68 pools. `masterApe()` → MasterApe V1; `banana()` → BANANA token. |
| BananaSplit | `0x86Ef5e73EDB2Fea111909Fe35aFcC564572AcC06` | `symbol()` = `BANANASPLIT`, `name()` = `BananaSplitBar Token`. Fee-sharing single-staking pool. |
| INIT_CODE_PAIR_HASH | `0xf4ccce374816856d11f00e4069e7cada164065686fbef53c6167a63ec2fd8c5b` | Use for off-chain `CREATE2` pair address derivation on BNB only. |

---

## 4. Addresses — Ethereum (1)

Small deployment (15 pairs). BANANA and GNANA are **not** deployed on Ethereum.

| Contract | Address | Notes |
|----------|---------|-------|
| Factory | `0xBAe5dc9B19004883d0377419FeF3c2C8832d7d7B` | `allPairsLength()` = 15. `feeToSetter` = `0x95989D97e42bd083dBe4c889c2A88Ff3b3ed70D3` |
| Router | `0x5f509a3C3F16dF2Fba7bF84dEE1eFbce6BB85587` | `factory()` → Factory above; `WETH()` = `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` |
| INIT_CODE_PAIR_HASH | `0xe2200989b6f9506f3beca7e9c844741b3ad1a88ad978b6b0973e96d3ca4707aa` | Different from BNB — pair bytecode was recompiled. |

---

## 5. Addresses — Arbitrum (42161)

| Contract | Address | Notes |
|----------|---------|-------|
| Factory | `0xCf083Be4164828f00cAE704EC15a36D711491284` | `allPairsLength()` = 94. `feeToSetter` = `0xe6661d960353CcFEeEbC3EcC6F1F11daec63F602`. Same address as Polygon (deterministic deploy). |
| Router | `0x7d13268144adcdbEBDf94F654085CC15502849Ff` | `factory()` → Factory above; `WETH()` = WETH `0x82aF49447D8a07e3bd95BD0d56f35241523fBab1` |
| INIT_CODE_PAIR_HASH | `0xae7373e804a043c4c08107a81def627eeb3792e211fb4711fcfe32f0e4c45fd5` | Different from Polygon despite same factory address — separate bytecode compilation. |

---

## 6. Addresses — Polygon (137)

| Contract | Address | Notes |
|----------|---------|-------|
| Factory | `0xCf083Be4164828f00cAE704EC15a36D711491284` | `allPairsLength()` = 1 463. `feeToSetter` = `0x2C5fD64A3e27826CAf1A3d0F1bE6f8ED9f8a4f8A`. Same address as Arbitrum (deterministic deploy). |
| Router | `0xC0788A3aD43d79aa53B09c2EaCc313A787d1d607` | `factory()` → Factory above; `WETH()` = WMATIC `0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270` |
| INIT_CODE_PAIR_HASH | `0x511f0f358fe530cda0859ec20becf391718fdf5a329be02f4c95361f3d6a42d8` | Different from Arbitrum despite shared factory address. |

---

## 7. Absent chains

| Chain | Chain ID | Status |
|-------|----------|--------|
| Base | 8453 | Not deployed — `eth_getCode` returns `0x` at all known addresses |
| Avalanche | 43114 | Not deployed |
| Optimism | 10 | Not deployed |

---

## 8. Cross-chain summary

| Chain | Factory | Router | Pairs | BANANA | Farming |
|-------|---------|--------|-------|--------|---------|
| BNB (56) | `0x0841BD0B` | `0xcF0feBd3` | 6 347 | yes | MasterApe V1 + V2 |
| Ethereum (1) | `0xBAe5dc9B` | `0x5f509a3C` | 15 | no | no |
| Arbitrum (42161) | `0xCf083Be4` | `0x7d13268` | 94 | no | no |
| Polygon (137) | `0xCf083Be4` | `0xC0788A3a` | 1 463 | no | no |
| Base / Avax / Optimism | — | — | — | — | — |

Arbitrum and Polygon share `0xCf083Be4164828f00cAE704EC15a36D711491284` as factory — this is a deterministic CREATE2 deployment. However each chain's pair bytecode was compiled independently, so `INIT_CODE_PAIR_HASH` differs (see §§5-6); off-chain pair derivation must use the chain-specific hash.

---

## 9. Proxies

All ApeSwap contracts are **fully immutable**. EIP-1967 logic slot (`0x3608...bbc`) returns `0x00` on every Factory, Router, pair, MasterApe V1/V2, and BananaSplit contract verified above. No upgradeability; no admin key can alter contract logic.

---

## 10. Detection invariants & gotchas

1. **LP token distinguisher.** ApeSwap pairs use `name = "ApeSwapFinance LPs"` and `symbol = "APE-LP"`. Do not confuse with Uniswap V2 (`UNI-V2`), PancakeSwap (`Cake-LP`), or SushiSwap (`SLP`). All emit the same topic0s.
2. **Flash-loan callback.** ApeSwap pairs call `apeCall()` (`0xbecda363`), not `uniswapV2Call()`. Monitor contracts implementing this selector for flash-loan-assisted attacks.
3. **BANANA address correction.** The address `0x603c7f932ED1fc6575303D8Fb018fDEBb0f97662` (last 6 chars `97662`) has **no bytecode** on BSC and is a documentation error that propagates widely. The correct address is `0x603c7f932ED1fc6575303D8Fb018fDCBb0f39a95` (last 6 chars `39a95`), confirmed via `symbol()` and MasterApe `banana()` call.
4. **Factory/Router swap in brief.** `0xcF0feBd3f17CEf5b47b0cD257aCf6025c5BFf3b7` is the **Router** on BNB (its `factory()` call returns the actual factory `0x0841BD0B...`). It is **not** the factory despite appearing labelled as factory in some sources.
5. **Arb/Polygon same factory, different pair hashes.** Same factory bytecode deployed deterministically, but pair bytecode differs — always use the per-chain `INIT_CODE_PAIR_HASH` for CREATE2 derivation.
6. **MasterApe V2 wraps V1.** `MasterApeV2.masterApe()` returns MasterApe V1 at `0x5c8D727b...`. V2 has 68 pools; V1 has 221 pools (both active). Both emit the same Deposit/Withdraw/EmergencyWithdraw topic0s.
7. **BANANA → GNANA rate.** GNANA is not a 1:1 wrapper; users pay a conversion tax. Monitoring large GNANA mints/burns implies BANANA flows through `0xdDb3Bd86...`.
8. **Protocol fees.** ApeSwap charges 0.3 % total swap fee: 0.25 % to LPs, 0.05 % to the `feeTo` treasury address. The fee logic is identical to Uniswap V2 (`kLast`-based LP mint in `mint()`/`burn()` when `feeTo != address(0)`).

---

## 11. Quick-copy constants

```
-- ApeSwap AMM topic0s (BNB + ETH + Arb + Polygon)
'\x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9'  -- PairCreated
'\xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'  -- Swap
'\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'  -- Mint
'\xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496'  -- Burn
'\x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'  -- Sync
'\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'  -- Transfer (ERC-20 / LP)
'\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'  -- Approval

-- MasterApe farming topic0s (BNB only)
'\x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15'  -- Deposit
'\xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568'  -- Withdraw
'\xbb757047c2b5f3974fe26b7c10f732e7bce710b0952a71082702781e62ae0595'  -- EmergencyWithdraw

-- BNB addresses
'\x0841BD0B734E4F5853f0dD8d7Ea041c241fb0Da6'  -- Factory (BNB)
'\xcF0feBd3f17CEf5b47b0cD257aCf6025c5BFf3b7'  -- Router (BNB)
'\x603c7f932ED1fc6575303D8Fb018fDCBb0f39a95'  -- BANANA token (BNB)
'\xdDb3Bd8645775F59496c821E4F55A7eA6A6dc299'  -- GNANA token (BNB)
'\x5c8D727b265DBAfaba67E050f2f739cAeEB4A6F9'  -- MasterApe V1 (BNB)
'\x71354AC3c695dfB1d3f595AfA5D4364e9e06339B'  -- MasterApe V2 (BNB)
'\x86Ef5e73EDB2Fea111909Fe35aFcC564572AcC06'  -- BananaSplit (BNB)

-- ETH addresses
'\xBAe5dc9B19004883d0377419FeF3c2C8832d7d7B'  -- Factory (ETH)
'\x5f509a3C3F16dF2Fba7bF84dEE1eFbce6BB85587'  -- Router (ETH)

-- Arbitrum addresses
'\xCf083Be4164828f00cAE704EC15a36D711491284'  -- Factory (Arb + Polygon, same address)
'\x7d13268144adcdbEBDf94F654085CC15502849Ff'  -- Router (Arb)

-- Polygon addresses
'\xC0788A3aD43d79aa53B09c2EaCc313A787d1d607'  -- Router (Polygon)

-- INIT_CODE_PAIR_HASHes (chain-specific — use for CREATE2 pair derivation)
'\xf4ccce374816856d11f00e4069e7cada164065686fbef53c6167a63ec2fd8c5b'  -- BNB
'\xe2200989b6f9506f3beca7e9c844741b3ad1a88ad978b6b0973e96d3ca4707aa'  -- ETH
'\xae7373e804a043c4c08107a81def627eeb3792e211fb4711fcfe32f0e4c45fd5'  -- Arbitrum
'\x511f0f358fe530cda0859ec20becf391718fdf5a329be02f4c95361f3d6a42d8'  -- Polygon
```

---

## 12. Verification & sources

All addresses, topic0s, and selectors were verified via direct RPC calls (publicnode endpoints) on 2026-06-10:
- BNB Factory `allPairsLength()` → 6 347 ✓
- BNB Router `factory()` → `0x0841BD0B...` ✓
- BANANA `symbol()` → `"BANANA"`, `name()` → `"ApeSwapFinance Banana"` ✓
- GNANA `symbol()` → `"GNANA"`, `name()` → `"Golden Banana"` ✓
- MasterApe V1 `poolLength()` → 221; V2 `poolLength()` → 68; V2 `masterApe()` → V1 address ✓
- ETH Factory `allPairsLength()` → 15; Router `factory()` → ETH factory ✓
- Arb Factory `allPairsLength()` → 94; Router `factory()` → Arb factory ✓
- Polygon Factory `allPairsLength()` → 1 463; Router `factory()` → Polygon factory ✓
- Base / Avalanche / Optimism: `eth_getCode` returns `0x` on all candidate addresses ✓
- EIP-1967 proxy slot = `0x00` on all core contracts ✓
- APE-LP `name()` / `symbol()` verified on BNB pair `0x51e6D27F...`, ETH pair `0x31bd914d...`, Polygon pair `0x019011032...`, Arb pair `0xC53e453E...` ✓
- `INIT_CODE_PAIR_HASH` read from Factory on each chain ✓

External sources:
- ApeSwap GitHub: https://github.com/ApeSwapFinance/apeswap-swap-core, https://github.com/ApeSwapFinance/apeswap-swap-periphery
- ApeSwap docs: https://apeswap.gitbook.io/apeswap-finance/where-dev/smart-contracts
- BSCScan: https://bscscan.com/address/0x0841BD0B734E4F5853f0dD8d7Ea041c241fb0Da6
