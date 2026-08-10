# THENA Finance — Concentrated Liquidity (CL) AMM — Topics, Selectors, Addresses (BNB Smart Chain)

**Status:** Verified — all addresses confirmed via `eth_getCode` on BNB Smart Chain (chain 56); pool Swap/Burn/Collect event topic0s confirmed via `eth_getLogs` on the live USDT/WBNB pool; absent (`0x`) on all other target chains.
**Sources:** [THENA Finance](https://thena.fi) · [THENA GitHub](https://github.com/ThenafiBNB/THENA-Contracts) · live `eth_getLogs` and `eth_getTransactionReceipt` cross-checks on BNB Smart Chain (blocks ~103,542,437–103,592,396) · bytecode PUSH32 analysis · 4byte.directory event-signature lookups.
**Last verified:** 2026-06-11

---

## 0. Contract families

| Family | Contracts | Role |
|--------|-----------|------|
| **CL core** | AlgebraFactory, AlgebraPoolDeployer, AlgebraPool (per-pair, deployed via PoolDeployer) | Pool creation, dynamic fee management, all swap/LP logic |
| **CL periphery** | SwapRouter, Quoter, NonfungiblePositionManager (NFPM), V3Migrator | User-facing LP management and routing |
| **CL farming** | FarmingCenter, AlgebraEternalFarming, AlgebraLimitFarming | Native Algebra farming for staked CL positions |
| **CL gauges** | GaugeFactoryV2_CL, GaugeV2_CL (per-pool clones) | THENA-native gauge rewards for LP token staking |

**Architecture note:** THENA CL is built on **Algebra V1** (not Algebra Integral). This is an important distinction from forks like Blackhole (which uses Algebra Integral): the THENA pool does NOT expose `plugin()` or `communityVault()` and does NOT emit `SwapFee` or `BurnFee` events. The Algebra Integral-specific 9-parameter Swap event (`0x3ebd5203…`) is not used; the pool emits the standard **7-parameter Swap** (`0xc42079f9…`) identical to Algebra V1 and Uniswap V3. The NFPM is named "Algebra Positions NFT-V1" (vs "NFT-V2" in Integral). The `Fee` event fires before each swap (dynamic fee update). The factory uses `poolByPair(tokenA, tokenB)` — `computePoolAddress` always reverts and should not be used. Alongside the native Algebra farming system (FarmingCenter/AlgebraEternalFarming), THENA runs a protocol-level gauge system (GaugeV2_CL) for additional THE token rewards.

Pool lookup: `AlgebraFactory.poolByPair(address tokenA, address tokenB)` returns the pool address for any order of tokenA/tokenB. `computePoolAddress` is not implemented (reverts) — use `poolByPair` exclusively.

---

## 1. Topics

### 1.1 AlgebraPool (per-pair CL pool)

All standard events confirmed via live `eth_getLogs` on pool `0xD405b976Ac01023c9064024880999fC450A8668b` (token0: USDT `0x55d398326f99059fF775485246999027B3197955`, token1: WBNB `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c`) and bytecode PUSH32 analysis.
Swap topic0 confirmed live: multiple Swap logs observed, all with `0xc42079f9…` (7-parameter, 160-byte data).

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `Initialize` | `Initialize(uint160,int24)` | `0x98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95` | Emitted once at pool creation; bytecode-confirmed |
| `Mint` | `Mint(address,address,int24,int24,uint128,uint256,uint256)` | `0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde` | Standard Algebra V1 / Uniswap V3 Mint — bytecode-confirmed |
| `Collect` | `Collect(address,address,int24,int24,uint128,uint128)` | `0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0` | Fee collection from pool position — live-confirmed |
| `Burn` | `Burn(address,int24,int24,uint128,uint256,uint256)` | `0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c` | Liquidity removal — live-confirmed |
| `Swap` | `Swap(address,address,int256,int256,uint160,uint128,int24)` | `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67` | **7-parameter form, identical to Algebra V1 / Uniswap V3** — live-confirmed; filter by emitter to disambiguate |
| `Flash` | `Flash(address,address,uint256,uint256,uint256,uint256)` | `0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633` | Flash loan; bytecode-confirmed |
| `Fee` | `Fee(uint16)` | `0x598b9f043c813aa6be3426ca60d1c65d17256312890be5118dab55b0775ebe2a` | Dynamic fee update — fires **before** each swap; data = `uint16` fee value; live-confirmed |

> **SwapFee / BurnFee:** These events exist in Blackhole's fork of Algebra Integral but are **absent** from THENA CL (Algebra V1). Neither topic0 (`0x9443903d…` / `0x1a25098b…`) appears in pool bytecode or live logs.

> **CollectProtocol, CommunityVault, PluginConfig, TickSpacing, Skim:** These are Algebra Integral-era events. THENA CL (Algebra V1) does not emit them. The pool does not expose `communityVault()` or `plugin()`.

**Indexed fields:**
- `Initialize`: none
- `Mint`: `sender` (idx1), `owner` (idx2), `bottomTick` (idx3), `topTick` (idx4)
- `Collect`: `owner` (idx1), `recipient` (idx2), `bottomTick` (idx3), `topTick` (idx4)
- `Burn`: `owner` (idx1), `bottomTick` (idx2), `topTick` (idx3)
- `Swap`: `sender` (idx1), `recipient` (idx2)

### 1.2 AlgebraFactory

Events sourced via bytecode PUSH32 analysis.

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `Pool` | `Pool(address,address,address)` | `0x91ccaa7a278130b65168c3a0c8d3bcae84cf5e43704342bd3ec0b59e59c036db` | Pool creation — **Algebra V1 naming** (not `PoolCreated`); indexed: `token0`, `token1`; data: pool address |

> **AccessControl events absent:** Unlike Blackhole's Integral factory, THENA's Algebra V1 factory does not use OpenZeppelin AccessControl. It uses simple owner-based access (`owner()` / `setOwner()`). No `RoleGranted` / `RoleRevoked` events.

**Indexed fields:**
- `Pool`: `token0` (idx1), `token1` (idx2); data: `address pool`

### 1.3 NonfungiblePositionManager (NFPM)

Events confirmed via bytecode PUSH32 analysis on NFPM `0xa51adb08cbe6ae398046a23bec013979816b77ab`.
NFPM is an ERC-721 token; also emits standard ERC-721 events.

> **Algebra V1 difference:** `IncreaseLiquidity` adds 2 extra parameters vs Uniswap V3 NFPM — `liquidityBefore (uint128)` is inserted at position 2, and `pool (address)` is appended. Full signature: `IncreaseLiquidity(uint256,uint128,uint128,uint256,uint256,address)`. This is identical to Blackhole's NFPM and produces 160-byte data payloads.

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `IncreaseLiquidity` | `IncreaseLiquidity(uint256,uint128,uint128,uint256,uint256,address)` | `0x8a82de7fe9b33e0e6bca0e26f5bd14a74f1164ffe236d50e0a36c3ea70f2b814` | **Algebra V1-specific** — 6 params vs Uniswap V3's 4; last param is pool address; bytecode-confirmed |
| `DecreaseLiquidity` | `DecreaseLiquidity(uint256,uint128,uint256,uint256)` | `0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4` | Bytecode-confirmed |
| `Collect` | `Collect(uint256,address,uint256,uint256)` | `0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01` | Bytecode-confirmed; different signature from pool Collect |
| `Transfer` (ERC-721) | `Transfer(address,address,uint256)` | `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | Bytecode-confirmed; NFT position mint/transfer/burn |
| `ApprovalForAll` (ERC-721) | `ApprovalForAll(address,address,bool)` | `0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31` | Bytecode-confirmed |
| `Approval` (ERC-721) | `Approval(address,address,uint256)` | `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | Bytecode-confirmed |

**Indexed fields:**
- `IncreaseLiquidity`: `tokenId` (idx1)
- `DecreaseLiquidity`: `tokenId` (idx1)
- `Collect`: `tokenId` (idx1)
- `Transfer`: `from` (idx1), `to` (idx2), `tokenId` (idx3)
- `ApprovalForAll`: `owner` (idx1), `operator` (idx2)
- `Approval`: `owner` (idx1), `approved` (idx2), `tokenId` (idx3)

**NFPM state:** `totalSupply()` = 15,317 positions minted as of block 103,592,396.

### 1.4 GaugeV2_CL (THENA CL Gauge — per pool)

Events sourced from GaugeFactoryV2_CL bytecode (`0x0248fdfba1e2815c9a2adf10fd6f5cf3cda36c73`) — confirmed via bytecode PUSH32 analysis. The source matches the `GaugeV2_CL.sol` contract in the THENA GitHub repository.

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `Deposit` | `Deposit(address,uint256)` | `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | LP NFT stake into gauge; bytecode-confirmed |
| `Withdraw` | `Withdraw(address,uint256)` | `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | LP NFT unstake; bytecode-confirmed |
| `Harvest` | `Harvest(address,uint256)` | `0xc9695243a805adb74c91f28311176c65b417e842d5699893cef56d18bfa48cba` | THE reward claim; bytecode-confirmed |
| `ClaimFees` | `ClaimFees(address,uint256,uint256)` | `0xbc567d6cbad26368064baa0ab5a757be46aae4d70f707f9203d9d9b6c8ccbfa3` | Protocol fee claim; bytecode-confirmed |
| `RewardAdded` | `RewardAdded(uint256)` | `0xde88a922e0d3b88b24e9623efeb464919c6bf9f66857a65e2bfcf2ce87a9433d` | Reward notification to gauge; bytecode-confirmed |
| `EmergencyActivated` | `EmergencyActivated(address,uint256)` | `0x774b57c3410c76d04ea4d51b0c15a9bac99b0e70f28fd88b53d702b5427fd318` | Emergency mode activation; source-confirmed |
| `EmergencyDeactivated` | `EmergencyDeactivated(address,uint256)` | `0xa30763a9bc0d8e121a6e721624965cae68010ece74128b4ae5b01b8dc22c00f8` | Emergency mode deactivation; source-confirmed |

### 1.5 AlgebraEternalFarming

Events sourced via bytecode PUSH32 analysis on `0x2308bd5b1f66c32cc482254b4ee99cc7708d2e41`, cross-checked against 4byte.directory.

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `EternalFarmingCreated` | `EternalFarmingCreated(address,address,address,address,uint256,uint256,uint256,uint256,(uint256,uint256,uint256,uint32,uint32,uint32),address,uint24)` | `0x0402a2abfe823f7036d0b24f3e7c00b60362a9e8214880b0fa5a74d6b216caf3` | New eternal farm created; bytecode-confirmed |
| `FarmEntered` | `FarmEntered(uint256,bytes32,uint128,uint256)` | `0x4a9757f8f71efdde4b041ff384e461c5707a95d74463b60892bd1f7b9c34a289` | Position staked into farming; bytecode-confirmed |
| `IncentiveAttached` | `IncentiveAttached(address,address,address,address,uint256,uint256)` | `0x6d3b554600fa5af9295315554801e6206cbdb85866f653f9488e5875c06a6b64` | Incentive attached to pool; bytecode-confirmed |
| `IncentiveDetached` | `IncentiveDetached(address,address,address,address,uint256,uint256)` | `0x0ab9cc241fe819ccf1100504defd5fe1366c71aba48092174547ccd7191f3d06` | Incentive detached from pool; bytecode-confirmed |
| `RewardsCollected` | `RewardsCollected(uint256,bytes32,uint256,uint256)` | `0x15b2e0f32b50efdbbdee9ec7884ed3c61e6209b1b395e5762011a6734b86f7b5` | Rewards harvested from farm; bytecode-confirmed |
| `RewardsRatesChanged` | `RewardsRatesChanged(uint128,uint128,bytes32)` | `0x1864e4cc903d98e44820faebd48409c410a2ad20adb3173984ba41ae2828805e` | Farm reward rates updated; bytecode-confirmed |

---

## 2. Function signatures

### AlgebraFactory

| Function | Selector | Notes |
|----------|----------|-------|
| `poolByPair(address,address)` | `0xd9a641e1` | **Use this for pool lookup** — works with any token order; returns pool address |
| `computePoolAddress(address,address)` | `0xd8ed2241` | Always reverts — not implemented in Algebra V1; do NOT use |
| `poolDeployer()` | `0x3119049a` | Returns `0xc89f69baa3ff17a842ab2de89e5fc8a8e2cc7358` |
| `owner()` | `0x8da5cb5b` | Returns `0x993Ae2b514677c7AC52bAeCd8871d2b362A9D693` (Thena: Deployer) |
| `vaultAddress()` | `0x430bf08a` | Returns `0x46f99291eedf25fd5c6ae56bbfd6679d0ea3630b` (protocol fee vault) |
| `farmingAddress()` | `0x8a2ade58` | Returns `0xfbc41acdf542752e2295024c9e0f8a6fb6276e1f` (FarmingCenter) |
| `setOwner(address)` | `0x13af4035` | Owner transfer |
| `setVaultAddress(address)` | `0x85535cc5` | Update fee vault |
| `setFarmingAddress(address)` | `0xb001f618` | Update farming center |
| `setBaseFeeConfiguration(uint16,uint16,uint32,uint32,uint16,uint16,uint32,uint16,uint16)` | `0x5d6d7e93` | Configure dynamic fee parameters |

### SwapRouter

| Function | Selector | Notes |
|----------|----------|-------|
| `exactInputSingle((address,address,address,uint256,uint256,uint256,uint160))` | `0xbc651188` | Single-hop exact input; no fee param (Algebra V1 style) |
| `exactInput((bytes,address,uint256,uint256,uint256))` | `0xc04b8d59` | Multi-hop exact input |
| `exactOutputSingle((address,address,address,uint256,uint256,uint256,uint160))` | `0x61d4d5b3` | Single-hop exact output |
| `exactOutput((bytes,address,uint256,uint256,uint256))` | `0xf28c0498` | Multi-hop exact output |
| `algebraSwapCallback(int256,int256,bytes)` | `0x2c8958f6` | Pool callback (not called directly) |
| `multicall(bytes[])` | `0xac9650d8` | Batch router calls |
| `factory()` | — | Returns `0x306F06C147f064A010530292A1EB6737c3e378e4` |

### NonfungiblePositionManager (NFPM)

| Function | Selector | Notes |
|----------|----------|-------|
| `mint((address,address,uint24,int24,int24,uint256,uint256,uint256,uint256,address,uint256))` | `0x88316456` | Creates new position NFT; includes `uint24 fee` for pool lookup |
| `increaseLiquidity((uint256,uint256,uint256,uint256,uint256))` | `0xdbd19848` | Add liquidity to existing position |
| `decreaseLiquidity((uint256,uint128,uint256,uint256,uint256))` | `0x0c49ccbe` | Remove liquidity |
| `collect((uint256,address,uint128,uint128))` | `0xfc6f7865` | Claim fees |
| `burn(uint256)` | `0x42966c68` | Burn empty position NFT |
| `positions(uint256)` | `0x99fbab88` | Read position state |
| `name()` | — | Returns `"Algebra Positions NFT-V1"` |
| `symbol()` | — | Returns `"ALGB-POS"` |
| `totalSupply()` | — | Returns 15,317 (as of block 103,592,396) |
| `factory()` | — | Returns `0x306F06C147f064A010530292A1EB6737c3e378e4` |
| `algebraMintCallback(uint256,uint256,bytes)` | `0x3dd657c5` | Pool callback (not called directly) |

---

## 3. Addresses — BNB Smart Chain (56)

All addresses verified via `eth_getCode` returning non-empty bytecode.

### CL Core

| Contract | Address | Code size (bytes) |
|----------|---------|-------------------|
| AlgebraFactory | `0x306F06C147f064A010530292A1EB6737c3e378e4` | 13,227 |
| AlgebraPoolDeployer | `0xc89f69baa3ff17a842ab2de89e5fc8a8e2cc7358` | 22,957 |
| AlgebraPool (example: token0=USDT `0x55d398…`, token1=WBNB `0xbb4cdb…`) | `0xD405b976Ac01023c9064024880999fC450A8668b` | 21,810 |

### CL Periphery

| Contract | Address | Code size (bytes) |
|----------|---------|-------------------|
| SwapRouter | `0x327Dd3208f0bCF590A66110aCB6e5e6941A4EfA0` | 12,697 |
| Quoter | `0xeA68020D6A9532EeC42D4dB0f92B83580c39b2cA` | 5,011 |
| NonfungiblePositionManager (NFPM) | `0xa51adb08cbe6ae398046a23bec013979816b77ab` | 24,098 |
| V3Migrator | `0x2ac5617f1c04641393bd3246f38521ede0fc9011` | 7,616 |
| NonfungibleTokenPositionDescriptor (proxy) | `0xc64f46d8cd1f36eb4b7f1db3dc99022996e831d6` | 2,486 |
| NonfungibleTokenPositionDescriptor (impl) | `0x9356934eb3fbae6274eae6efc905b292f04f0122` | — |

### CL Farming (Algebra Native)

| Contract | Address | Code size (bytes) |
|----------|---------|-------------------|
| FarmingCenter | `0xfbc41acdf542752e2295024c9e0f8a6fb6276e1f` | 24,062 |
| AlgebraEternalFarming | `0x2308bd5b1f66c32cc482254b4ee99cc7708d2e41` | 22,735 |
| AlgebraLimitFarming | `0x7fb6b676b7f7eaf8f60b057697e6e1b108189036` | 22,716 |

### CL Gauges (THENA Protocol)

| Contract | Address | Code size (bytes) | Notes |
|----------|---------|-------------------|-|
| GaugeFactoryV2_CL | `0x0248fdfba1e2815c9a2adf10fd6f5cf3cda36c73` | 22,333 | Contains GaugeV2_CL logic; deployed April 2023 |

### Governance / Protocol Addresses

| Role | Address | Notes |
|------|---------|-------|
| Protocol owner / deployer | `0x993Ae2b514677c7AC52bAeCd8871d2b362A9D693` | Owner of AlgebraFactory; labeled "Thena: Deployer" |
| Protocol fee vault | `0x46f99291eedf25fd5c6ae56bbfd6679d0ea3630b` | Receives protocol fees; referenced as `vaultAddress()` in factory |
| CL deployer (periphery) | `0x4AFA1e99c916d57f4bdfc22b3b55316853464c7C` | Deployed all periphery contracts on 2023-02-27 |

---

## 4. Cross-chain summary

THENA Finance is **BNB Smart Chain only**. Every address in §3 returns `0x` (no bytecode) on all other target chains:

| Chain | Chain ID | AlgebraFactory | NFPM |
|-------|----------|----------------|------|
| BNB Smart Chain | 56 | `0x306F06C1…` — **HAS CODE** | `0xa51adb08…` — **HAS CODE** |
| Ethereum | 1 | `0x` | `0x` |
| Base | 8453 | `0x` | `0x` |
| Arbitrum One | 42161 | `0x` | `0x` |
| Optimism | 10 | `0x` | `0x` |
| Polygon PoS | 137 | `0x` | `0x` |

---

## 5. Proxies

| Contract | Pattern | Proxy address | Implementation |
|----------|---------|---------------|----------------|
| NonfungibleTokenPositionDescriptor | **EIP-1967 upgradeable proxy** (custom) | `0xc64f46d8cd1f36eb4b7f1db3dc99022996e831d6` | `0x9356934eb3fbae6274eae6efc905b292f04f0122` |
| AlgebraFactory | Not a proxy | `0x306F06C147f064A010530292A1EB6737c3e378e4` | N/A — EIP-1967 impl slot = `0x0` |
| NFPM | Not a proxy | `0xa51adb08cbe6ae398046a23bec013979816b77ab` | N/A — EIP-1967 impl slot = `0x0` |
| SwapRouter | Not a proxy | `0x327Dd3208f0bCF590A66110aCB6e5e6941A4EfA0` | N/A — EIP-1967 impl slot = `0x0` |
| Quoter | Not a proxy | `0xeA68020D6A9532EeC42D4dB0f92B83580c39b2cA` | N/A — EIP-1967 impl slot = `0x0` |
| GaugeFactoryV2_CL | Not a proxy | `0x0248fdfba1e2815c9a2adf10fd6f5cf3cda36c73` | N/A — EIP-1967 impl slot = `0x0` |

---

## 6. Detection invariants & gotchas

### THENA CL is Algebra V1, not Algebra Integral

THENA CL was deployed on 2023-02-27 using Algebra V1 — the same base as QuickSwap V3. It does NOT include Algebra Integral features: no `plugin()`, no `communityVault()`, no `SwapFee`/`BurnFee` events, no `TickSpacing`/`Skim` events. Blackhole DEX (Avalanche) forked from THENA but upgraded to Algebra Integral and added the `SwapFee`/`BurnFee` events — those are Blackhole-specific and absent here.

### Pool Swap topic0 is identical to Uniswap V3

The THENA CL pool `Swap` topic0 (`0xc42079f9…`) is the same as Uniswap V3 and Algebra V1. Disambiguation by emitter address is required. All THENA CL pools are deployed via `AlgebraPoolDeployer` (`0xc89f69…`); verify any pool address using `AlgebraFactory.poolByPair(tokenA, tokenB)`.

### Use poolByPair — not computePoolAddress

Unlike Algebra Integral deployments, `computePoolAddress(tokenA, tokenB)` reverts in THENA's Algebra V1 factory. Use `poolByPair(tokenA, tokenB)` instead — it accepts tokens in any order and returns the pool address if deployed, or `address(0)` if not.

### Fee event fires before each Swap

The `Fee(uint16)` event (`0x598b9f04…`) fires immediately before every `Swap` in the same transaction (dynamic fee update). It is NOT the swap fee paid — it is the current fee tier of the pool at the time of the swap. When monitoring for swaps, expect to see `Fee` → `Swap` pairs.

### NFPM IncreaseLiquidity has 6 params (not 4)

THENA NFPM `IncreaseLiquidity` emits `(uint256 indexed tokenId, uint128 liquidityBefore, uint128 liquidityAfter, uint256 amount0, uint256 amount1, address pool)` — the last word of the 160-byte data payload is the pool address. A Uniswap V3 decoder (expecting 4 params, 128 bytes) will misparse this event.

### Two distinct reward systems for CL liquidity

1. **Algebra native farming** (`FarmingCenter` / `AlgebraEternalFarming`): NFPM positions are deposited directly into the FarmingCenter; `FarmEntered` / `RewardsCollected` events track staking and harvesting.
2. **THENA gauge system** (`GaugeV2_CL`): A separate gauge layer for THE token rewards; `Deposit` / `Withdraw` / `Harvest` events track LP positions staked in gauges.

Both systems accept NFPM token IDs as the staked asset.

### Swap vs Algebra Integral Swap disambiguation

| Variant | Swap topic0 | Params | Data bytes |
|---------|------------|--------|------------|
| THENA CL (this protocol) | `0xc42079f9…` | 7 | 160 |
| Algebra Integral 9-param | `0x3ebd5203…` | 9 | 224 |
| Uniswap V3 | `0xc42079f9…` | 7 | 160 |

Filter by emitter address (`poolByPair(tokenA, tokenB)`) when topic0 = `0xc42079f9…`.

---

## 7. Quick-copy detection constants

```python
# ── THENA CL — AlgebraPool ────────────────────────────────────────────────
TH_POOL_SWAP              = b"\xc4\x20\x79\xf9\x4a\x63\x50\xd7\xe6\x23\x5f\x29\x17\x49\x24\xf9\x28\xcc\x2a\xc8\x18\xeb\x64\xfe\xd8\x00\x4e\x11\x5f\xbc\xca\x67"
TH_POOL_MINT              = b"\x7a\x53\x08\x0b\xa4\x14\x15\x8b\xe7\xec\x69\xb9\x87\xb5\xfb\x7d\x07\xde\xe1\x01\xfe\x85\x48\x8f\x08\x53\xae\x16\x23\x9d\x0b\xde"
TH_POOL_BURN              = b"\x0c\x39\x6c\xd9\x89\xa3\x9f\x44\x59\xb5\xfa\x1a\xed\x6a\x9a\x8d\xcd\xbc\x45\x90\x8a\xcf\xd6\x7e\x02\x8c\xd5\x68\xda\x98\x98\x2c"
TH_POOL_COLLECT           = b"\x70\x93\x53\x38\xe6\x97\x75\x45\x6a\x85\xdd\xef\x22\x6c\x39\x5f\xb6\x68\xb6\x3f\xa0\x11\x5f\x5f\x20\x61\x0b\x38\x8e\x6c\xa9\xc0"
TH_POOL_FLASH             = b"\xbd\xbd\xb7\x1d\x78\x60\x37\x6b\xa5\x2b\x25\xa5\x02\x8b\xee\xa2\x35\x81\x36\x4a\x40\x52\x2f\x6b\xcf\xb8\x6b\xb1\xf2\xdc\xa6\x33"
TH_POOL_INITIALIZE        = b"\x98\x63\x60\x36\xcb\x66\xa9\xc1\x9a\x37\x43\x5e\xfc\x1e\x90\x14\x21\x90\x21\x4e\x8a\xbe\xb8\x21\xbd\xba\x3f\x29\x90\xdd\x4c\x95"
TH_POOL_FEE               = b"\x59\x8b\x9f\x04\x3c\x81\x3a\xa6\xbe\x34\x26\xca\x60\xd1\xc6\x5d\x17\x25\x63\x12\x89\x0b\xe5\x11\x8d\xab\x55\xb0\x77\x5e\xbe\x2a"

# ── THENA CL — AlgebraFactory ─────────────────────────────────────────────
TH_FACTORY_POOL           = b"\x91\xcc\xaa\x7a\x27\x81\x30\xb6\x51\x68\xc3\xa0\xc8\xd3\xbc\xae\x84\xcf\x5e\x43\x70\x43\x42\xbd\x3e\xc0\xb5\x9e\x59\xc0\x36\xdb"

# ── THENA CL — NFPM ───────────────────────────────────────────────────────
TH_NFPM_INCREASE_LIQ      = b"\x8a\x82\xde\x7f\xe9\xb3\x3e\x0e\x6b\xca\x0e\x26\xf5\xbd\x14\xa7\x4f\x11\x64\xff\xe2\x36\xd5\x0e\x0a\x36\xc3\xea\x70\xf2\xb8\x14"
TH_NFPM_DECREASE_LIQ      = b"\x26\xf6\xa0\x48\xee\x91\x38\xf2\xc0\xce\x26\x6f\x32\x2c\xb9\x92\x28\xe8\xd6\x19\xae\x2b\xff\x30\xc6\x7f\x8d\xcf\x9d\x23\x77\xb4"
TH_NFPM_COLLECT           = b"\x40\xd0\xef\xd1\xa5\x3d\x60\xec\xbf\x40\x97\x1b\x9d\xaf\x7d\xc9\x01\x78\xc3\xaa\xdc\x7a\xab\x17\x65\x63\x27\x38\xfa\x8b\x8f\x01"

# ── THENA CL — GaugeV2_CL ─────────────────────────────────────────────────
TH_GAUGE_DEPOSIT          = b"\xe1\xff\xfc\xc4\x92\x3d\x04\xb5\x59\xf4\xd2\x9a\x8b\xfc\x6c\xda\x04\xeb\x5b\x0d\x3c\x46\x07\x51\xc2\x40\x2c\x5c\x5c\xc9\x10\x9c"
TH_GAUGE_WITHDRAW         = b"\x88\x4e\xda\xd9\xce\x6f\xa2\x44\x0d\x8a\x54\xcc\x12\x34\x90\xeb\x96\xd2\x76\x84\x79\xd4\x9f\xf9\xc7\x36\x61\x25\xa9\x42\x43\x64"
TH_GAUGE_HARVEST          = b"\xc9\x69\x52\x43\xa8\x05\xad\xb7\x4c\x91\xf2\x83\x11\x17\x6c\x65\xb4\x17\xe8\x42\xd5\x69\x98\x93\xce\xf5\x6d\x18\xbf\xa4\x8c\xba"
TH_GAUGE_REWARD_ADDED     = b"\xde\x88\xa9\x22\xe0\xd3\xb8\x8b\x24\xe9\x62\x3e\xfe\xb4\x64\x91\x9c\x6b\xf9\xf6\x68\x57\xa6\x5e\x2b\xfc\xf2\xce\x87\xa9\x43\x3d"
TH_GAUGE_CLAIM_FEES       = b"\xbc\x56\x7d\x6c\xba\xd2\x63\x68\x06\x4b\xaa\x0a\xb5\xa7\x57\xbe\x46\xaa\xe4\xd7\x0f\x70\x7f\x92\x03\xd9\xd9\xb6\xc8\xcc\xbf\xa3"

# ── THENA CL — AlgebraEternalFarming ──────────────────────────────────────
TH_FARM_ENTERED           = b"\x4a\x97\x57\xf8\xf7\x1e\xfd\xde\x4b\x04\x1f\xf3\x84\xe4\x61\xc5\x70\x7a\x95\xd7\x44\x63\xb6\x08\x92\xbd\x1f\x7b\x9c\x34\xa2\x89"
TH_REWARDS_COLLECTED      = b"\x15\xb2\xe0\xf3\x2b\x50\xef\xdb\xbd\xee\x9e\xc7\x88\x4e\xd3\xc6\x1e\x62\x09\xb1\xb3\x95\xe5\x76\x20\x11\xa6\x73\x4b\x86\xf7\xb5"
```

**Hex strings for SQL/monitoring queries:**

```
-- Pool Swap (identical to Uniswap V3 — filter by emitter address)
\xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67

-- Pool Mint (identical to Algebra V1 / Uniswap V3)
\x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde

-- Pool Burn
\x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c

-- Pool Fee (fires before each Swap — NOT SwapFee)
\x598b9f043c813aa6be3426ca60d1c65d17256312890be5118dab55b0775ebe2a

-- Factory Pool creation
\x91ccaa7a278130b65168c3a0c8d3bcae84cf5e43704342bd3ec0b59e59c036db

-- NFPM IncreaseLiquidity (Algebra V1 6-param — DIFFERS from Uniswap V3)
\x8a82de7fe9b33e0e6bca0e26f5bd14a74f1164ffe236d50e0a36c3ea70f2b814

-- NFPM DecreaseLiquidity
\x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4

-- NFPM Collect
\x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01

-- Gauge Deposit
\xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c

-- Gauge Harvest
\xc9695243a805adb74c91f28311176c65b417e842d5699893cef56d18bfa48cba

-- AlgebraEternalFarming FarmEntered
\x4a9757f8f71efdde4b041ff384e461c5707a95d74463b60892bd1f7b9c34a289
```

---

## 8. Verification & sources

### On-chain verification

| Check | Result |
|-------|--------|
| `eth_getCode` — AlgebraFactory, NFPM, SwapRouter, Quoter, FarmingCenter, EternalFarming, LimitFarming — BNB 56 | All non-empty (code sizes 5,011–24,098 bytes) |
| `eth_getCode` — AlgebraFactory + NFPM on Ethereum, Base, Arbitrum, Optimism, Polygon | All `0x` (absent) |
| `AlgebraFactory.poolDeployer()` | Returns `0xc89f69baa3ff17a842ab2de89e5fc8a8e2cc7358` ✓ |
| `AlgebraFactory.owner()` | Returns `0x993Ae2b514677c7AC52bAeCd8871d2b362A9D693` ✓ |
| `AlgebraFactory.vaultAddress()` | Returns `0x46f99291eedf25fd5c6ae56bbfd6679d0ea3630b` ✓ |
| `AlgebraFactory.farmingAddress()` | Returns `0xfbc41acdf542752e2295024c9e0f8a6fb6276e1f` (FarmingCenter) ✓ |
| `AlgebraFactory.poolByPair(USDT, WBNB)` | Returns `0xD405b976Ac01023c9064024880999fC450A8668b` ✓ |
| `AlgebraFactory.computePoolAddress(…)` | Reverts — not implemented in Algebra V1 ✓ |
| `pool.token0()` | Returns `0x55d398326f99059fF775485246999027B3197955` (USDT) ✓ |
| `pool.token1()` | Returns `0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c` (WBNB) ✓ |
| `pool.communityVault()` | Reverts — Algebra V1, no communityVault ✓ |
| `pool.plugin()` | Reverts — Algebra V1, no plugin ✓ |
| `SwapRouter.factory()` | Returns `0x306F06C147f064A010530292A1EB6737c3e378e4` ✓ |
| `Quoter.factory()` | Returns `0x306F06C147f064A010530292A1EB6737c3e378e4` ✓ |
| `FarmingCenter.nonfungiblePositionManager()` | Returns `0xa51adb08cbe6ae398046a23bec013979816b77ab` ✓ |
| `NFPM.name()` | Returns `"Algebra Positions NFT-V1"` ✓ |
| `NFPM.symbol()` | Returns `"ALGB-POS"` ✓ |
| `NFPM.factory()` | Returns `0x306F06C147f064A010530292A1EB6737c3e378e4` ✓ |
| `NFPM.totalSupply()` | 15,317 positions (as of block 103,592,396) ✓ |
| `eth_getLogs` — Swap topic0 on pool, blocks 103,542,437–103,592,396 | Multiple Swap logs, all with topic0 `0xc42079f9…` (7-param, 160-byte data) ✓ |
| `eth_getLogs` — SwapFee topic0 (`0x9443903d…`) on pool | Zero logs — **SwapFee absent** ✓ |
| `eth_getLogs` — BurnFee topic0 (`0x1a25098b…`) on pool | Zero logs — **BurnFee absent** ✓ |
| `eth_getLogs` — Burn + Collect on pool | Multiple logs confirmed — `0x0c396cd9…` (Burn), `0x70935338…` (Collect) ✓ |
| Pool bytecode PUSH32: SwapFee (`0x9443903d…`) | Not present ✓ |
| Pool bytecode PUSH32: BurnFee (`0x1a25098b…`) | Not present ✓ |
| NFPM bytecode PUSH32: IncreaseLiquidity 6-param | `0x8a82de7f…` present ✓ |
| EIP-1967 impl slot on AlgebraFactory, NFPM, SwapRouter, Quoter, GaugeFactoryV2_CL | `0x0` on all (not proxies) ✓ |

### Confirmed event topic0s

| Event | topic0 | Status |
|-------|--------|--------|
| Pool `Swap` (7-param) | `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67` | **Live-confirmed** |
| Pool `Burn` | `0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c` | **Live-confirmed** |
| Pool `Collect` | `0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0` | **Live-confirmed** |
| Pool `Fee` | `0x598b9f043c813aa6be3426ca60d1c65d17256312890be5118dab55b0775ebe2a` | **Live-confirmed** (fires before each Swap) |
| Pool `SwapFee` | n/a — **ABSENT** | Not in bytecode or live logs |
| Pool `BurnFee` | n/a — **ABSENT** | Not in bytecode or live logs |
| Pool `Mint` | `0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde` | **Bytecode-confirmed** (PUSH32) |
| Pool `Initialize` | `0x98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95` | **Bytecode-confirmed** |
| Pool `Flash` | `0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633` | **Bytecode-confirmed** |
| Factory `Pool` | `0x91ccaa7a278130b65168c3a0c8d3bcae84cf5e43704342bd3ec0b59e59c036db` | **Bytecode-confirmed** (PUSH32) |
| NFPM `IncreaseLiquidity` (6-param) | `0x8a82de7fe9b33e0e6bca0e26f5bd14a74f1164ffe236d50e0a36c3ea70f2b814` | **Bytecode-confirmed** |
| NFPM `DecreaseLiquidity` | `0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4` | **Bytecode-confirmed** |
| NFPM `Collect` | `0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01` | **Bytecode-confirmed** |
| GaugeV2_CL events (5 core) | see §1.4 | **Bytecode-confirmed** (GaugeFactoryV2_CL) |
| AlgebraEternalFarming events (6) | see §1.5 | **Bytecode-confirmed** + 4byte.directory |

### Sources

- THENA Finance: https://thena.fi
- THENA GitHub contracts: https://github.com/ThenafiBNB/THENA-Contracts
- AlgebraFactory on BscScan: https://bscscan.com/address/0x306f06c147f064a010530292a1eb6737c3e378e4
- Algebra V1 protocol reference: https://algebra.finance
- RPC: https://bsc-rpc.publicnode.com (BNB Smart Chain, chain ID 56)
- Event signatures cross-checked: https://www.4byte.directory/event-signatures/
