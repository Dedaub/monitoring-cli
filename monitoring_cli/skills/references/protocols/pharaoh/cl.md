# Pharaoh CL (Concentrated Liquidity + DLMM) — Topics, Selectors, Addresses (Avalanche C-Chain)

**Status:** Verified — all addresses confirmed via `eth_getCode` on Avalanche C-Chain (43114); absent (0x) on all other target chains (Ethereum 1, Base 8453, BNB 56, Arbitrum 42161, Optimism 10, Polygon 137).
**Sources:** [Pharaoh docs](https://docs.phar.gg/pages/contract-addresses) · [GitHub: PharaohExchange/pharaoh-contracts](https://github.com/PharaohExchange/pharaoh-contracts) · live `eth_getLogs` cross-checks on Avalanche C-Chain block ~87,487,235.
**Last verified:** 2026-06-08

---

## 0. Contract families

| Family | Contracts | Role |
|--------|-----------|------|
| **RamsesV3 CL core** | RamsesV3Factory, RamsesV3PoolDeployer, RamsesV3Pool (per-pair) | Pool creation, tick-spacing/fee management, all swap/LP logic |
| **CL periphery** | RamsesV3PositionManager (NFPM), SwapRouter, UniversalRouter, Quoter, QuoterV2, NonfungibleTokenPositionDescriptor, TickLens | User-facing LP management and routing |
| **CL gauges** | CL GaugeFactory, GaugeV3 (per gauge), FeeCollector | Gauge reward distribution for CL positions |
| **Access control** | AccessHub (UUPS proxy), ProxyAdmin | Protocol-wide role management |
| **DLMM** | DLMMFactory, DLMMRouter, DLMMQuoter, DLMMRewarderFactory, DLMMFeeCollector, DLMMPair (EIP-1167 clones of impl `0xF41253C1258A7A3c291E695158267b173c26d710`) | Discrete bin liquidity — a **Trader Joe Liquidity Book (LB v2) fork**; source not publicly released |

**Architecture note:** Pharaoh CL is a Ramses V3 fork of Uniswap V3. Ramses V3 departs from Uniswap V3 in two critical ways:
1. Pool lookup uses **tickSpacing (int24)** as the third key, not fee (uint24): `getPool(tokenA, tokenB, tickSpacing)`.
2. The `Mint` event carries an extra `uint256 index` parameter (position index), making the Mint topic0 **incompatible** with Uniswap V3 monitors.

The DLMM is a **Trader Joe Liquidity Book (LB v2) fork** with source not publicly released. This is confirmed on-chain: DLMM pairs respond to `getTokenX()`, `getTokenY()`, `getBinStep()`, and `getActiveId()` — the exact Trader Joe LB v2 interface — and the `Swap` event topic0 matches the TJ LB v2 signature `Swap(address,address,uint24,bytes32,bytes32,uint24,bytes32,bytes32)`. Events are identified from on-chain log inspection and 4byte.directory.

---

## 1. Topics

### 1.1 RamsesV3Pool (per-pair CL pool)

All events sourced from `contracts/CL/core/interfaces/pool/IRamsesV3PoolEvents.sol`.
Swap topic0 cross-checked live against pool `0xf01449C0bA930B6e2CaCA3DEF3CCBd7a3E589534` (WAVAX/USDC, tickSpacing=10) — 239 matching logs found.

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `Initialize` | `Initialize(uint160,int24)` | `0x98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95` | Emitted once at pool creation |
| `Mint` | `Mint(address,address,uint256,int24,int24,uint128,uint256,uint256)` | `0xd78218c0d304e8893cb3200abe394bbc8d5b7804d9c51f236df9fdcf481d02d3` | **Ramses-specific** — 3rd param is `uint256 index`; topic0 DIFFERS from Uniswap V3 |
| `Collect` | `Collect(address,address,int24,int24,uint128,uint128)` | `0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0` | Fee collection from position |
| `Burn` | `Burn(address,int24,int24,uint128,uint256,uint256)` | `0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c` | Liquidity removal |
| `Swap` | `Swap(address,address,int256,int256,uint160,uint128,int24)` | `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67` | **Identical to Uniswap V3** — see §6 |
| `Flash` | `Flash(address,address,uint256,uint256,uint256,uint256)` | `0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633` | Flash loan |
| `IncreaseObservationCardinalityNext` | `IncreaseObservationCardinalityNext(uint16,uint16)` | `0xac49e518f90a358f652e4400164f05a5d8f7e35e7747279bc3a93dbf584e125a` | TWAP oracle expansion |
| `SetFeeProtocol` | `SetFeeProtocol(uint8,uint8,uint8,uint8)` | `0x973d8d92bb299f4af6ce49b52a8adb85ae46b9f214c4c4fc06ac77401237b133` | Per-pool protocol fee change |
| `CollectProtocol` | `CollectProtocol(address,address,uint128,uint128)` | `0x596b573906218d3411850b26a6b437d6c4522fdb43d2d2386263f86d50b8b151` | Protocol fee collection |
| `FeeAdjustment` | `FeeAdjustment(uint24,uint24)` | `0x0cba87189055d3b5ab05c96fbd641bc766576c9e7cf0d195bdfb58a0c6a6df24` | **Pool-level** dynamic fee update — **15 hits / 5k blocks live-confirmed** on WAVAX/USDC pool; Ramses-specific (Uniswap V3 has no equivalent) |

**Indexed fields:**
- `Mint`: `owner` (idx1), `tickLower` (idx2), `tickUpper` (idx3)
- `Collect`: `owner` (idx1), `tickLower` (idx2), `tickUpper` (idx3)
- `Burn`: `owner` (idx1), `tickLower` (idx2), `tickUpper` (idx3)
- `Swap`: `sender` (idx1), `recipient` (idx2)
- `Flash`: `sender` (idx1), `recipient` (idx2)
- `CollectProtocol`: `sender` (idx1), `recipient` (idx2)

### 1.2 RamsesV3Factory

All events sourced from `contracts/CL/core/interfaces/IRamsesV3Factory.sol`.

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `PoolCreated` | `PoolCreated(address,address,uint24,int24,address)` | `0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118` | **Identical to Uniswap V3** factory event — see §6 |
| `TickSpacingEnabled` | `TickSpacingEnabled(int24,uint24)` | `0xebafae466a4a780a1d87f5fab2f52fad33be9151a7f69d099e8934c8de85b747` | New tick spacing/fee tier registered |
| `SetFeeProtocol` | `SetFeeProtocol(uint24,uint24)` | `0x67a069e4d951485f3e494a1edfa67d7334e991e8514ba748fd1636270acd1c97` | Global protocol fee change |
| `SetPoolFeeProtocol` | `SetPoolFeeProtocol(address,uint24,uint24)` | `0x1fb49ee35e38c4a757469d4a1c37187e7b3821f994a5556fde452ba2607ee235` | Per-pool protocol fee override |
| `FeeAdjustment` | `FeeAdjustment(address,uint24)` | `0xe4accbaee82fb833ac207d4c4454c5a04e85f5e1e9a20a9e2c98e54e8706ff2b` | Factory-level dynamic fee update (pool address + new fee) — fires at **high frequency** (~10+ per 1000 blocks across all active pools, live-confirmed); this is the per-pool automated fee oracle signal |
| `FeeCollectorChanged` | `FeeCollectorChanged(address,address)` | `0x649c5e3d0ed183894196148e193af316452b0037e77d2ff0fef23b7dc722bed0` | Fee recipient address update |

**Indexed fields:**
- `PoolCreated`: `token0` (idx1), `token1` (idx2), `fee` (idx3)
- `TickSpacingEnabled`: `tickSpacing` (idx1), `fee` (idx2)
- `FeeCollectorChanged`: `oldFeeCollector` (idx1), `newFeeCollector` (idx2)

### 1.3 NonfungiblePositionManager (NFPM)

Sourced from `contracts/CL/periphery/interfaces/INonfungiblePositionManager.sol`. NFPM is an ERC-721 token; also emits standard ERC-721 `Transfer(address,address,uint256)` (`0xddf252ad...`).

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `IncreaseLiquidity` | `IncreaseLiquidity(uint256,uint128,uint256,uint256)` | `0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f` | Confirmed live on NFPM |
| `DecreaseLiquidity` | `DecreaseLiquidity(uint256,uint128,uint256,uint256)` | `0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4` | Confirmed live on NFPM |
| `Collect` | `Collect(uint256,address,uint256,uint256)` | `0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01` | Confirmed live on NFPM; note different sig from pool Collect |
| `Transfer` (ERC-721) | `Transfer(address,address,uint256)` | `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | Confirmed live; NFT position mint/transfer/burn |

**Indexed fields:**
- `IncreaseLiquidity`: `tokenId` (idx1)
- `DecreaseLiquidity`: `tokenId` (idx1)
- `Collect`: `tokenId` (idx1)
- `Transfer`: `from` (idx1), `to` (idx2), `tokenId` (idx3)

### 1.4 DLMM (DLMMPair — EIP-1167 clones)

Pharaoh's DLMM is a **Trader Joe Liquidity Book (LB v2) fork**. Source is not public. Events identified via on-chain `eth_getLogs` across all 14 active DLMM pairs and cross-checked against 4byte.directory.

| Event | Signature | topic0 | Status | Notes |
|-------|-----------|--------|--------|-------|
| `Swap` | `Swap(address,address,uint24,bytes32,bytes32,uint24,bytes32,bytes32)` | `0xad7d6f97abf51ce18e17a38f4d70e975be9c0708474987bb3e26ad21bd93ca70` | Verified live | 2 indexed (sender, recipient); data = 6 × 32 bytes: id (uint24 in bytes32), amountsIn (bytes32), amountsOut (bytes32), volatilityAccumulator (uint24 in bytes32), fees (bytes32), protocolFees (bytes32) |
| `CollectedProtocolFees` | `CollectedProtocolFees(address,bytes32)` | `0x3f41a5ddc53701cc7db577ade4f1fca9838a8ec0b5ea50b9f0f5d17bc4554e32` | Verified live | 1 indexed (feeRecipient); data = 1 × 32 bytes (packed fee amounts) |

**DLMM Factory events:** No factory events observed in the queried range. The factory's `getNumberOfLBPairs()` returns 14; `getLBPairAtIndex(uint256)` enumerates pairs. Factory slot 0 = AccessHub address; slot 3 = DLMMFeeCollector.

**DLMM pool structure:** Each DLMMPair is an EIP-1167 minimal proxy (98-byte clone) pointing to implementation `0xF41253C1258A7A3c291E695158267b173c26d710`. Pairs are NOT proxies of a beacon. Token routing: `getTokenX()` / `getTokenY()` / `getBinStep()` / `getActiveId()`.

### 1.5 GaugeV3 (CL Gauge — per pool)

Sourced from `contracts/CL/gauge/GaugeV3.sol`.

| Event | Signature | topic0 |
|-------|-----------|--------|
| `RewardAdded` | `RewardAdded(address)` | `0xb13fd610fe4e1b384966826794a9b2f6100ad031f352cc5ec6f22667f6074980` |
| `NotifyReward` | `NotifyReward(address,address,uint256,uint256)` | `0x52977ea98a2220a03ee9ba5cb003ada08d394ea10155483c95dc2dc77a7eb24b` |
| `ClaimRewards` | `ClaimRewards(uint256,bytes32,address,address,uint256)` | `0xc8c7ebd754a625a8677ab2031c7674259be1e8c1a7f3521cbf5edbca8f48099c` |
| `RewardRemoved` | `RewardRemoved(address)` | `0x755c47ac85b75fe2251607db5a480aac818b88bb535814bf1e3c4784ae4f6baa` |

**Indexed fields:**
- `RewardAdded`: `token` (idx1)
- `NotifyReward`: `sender` (idx1), `token` (idx2)
- `ClaimRewards`: `period` (idx1), `positionHash` (idx2), `receiver` (idx3)
- `RewardRemoved`: `reward` (idx1)

---

## 2. Function signatures

### RamsesV3Factory

| Function | Selector | Notes |
|----------|----------|-------|
| `getPool(address,address,int24)` | `0x28af8d0b` | Third param is **tickSpacing**, not fee |
| `createPool(address,address,int24)` | `0x7b4f9bb1` | Deploys via RamsesV3PoolDeployer |
| `enableTickSpacing(int24,uint24)` | `0xeee0fdb4` | Governance only |
| `setFeeProtocol(uint24)` | `0x7fe35510` | Global fee |
| `setPoolFeeProtocol(address,uint24)` | `0x7ab4974d` | Per-pool fee override |
| `accessHub()` | — | Returns `0x3176f6E4Be2448C53EDD59C27651EDFaA74bf483` |

### SwapRouter

| Function | Selector | Notes |
|----------|----------|-------|
| `exactInputSingle((address,address,int24,address,uint256,uint256,uint160))` | `0xf59a7099` | Single-hop; 3rd param is tickSpacing |
| `exactInput((bytes,address,uint256,uint256))` | `0xb858183f` | Multi-hop |
| `exactOutputSingle((address,address,int24,address,uint256,uint256,uint160))` | `0xc67fe489` | Single-hop exact output |
| `exactOutput((bytes,address,uint256,uint256))` | `0x09b81346` | Multi-hop exact output |

### NonfungiblePositionManager (NFPM)

| Function | Selector | Notes |
|----------|----------|-------|
| `mint((address,address,int24,int24,int24,uint256,uint256,uint256,uint256,address,uint256))` | `0x6d70c415` | Creates new position NFT |
| `increaseLiquidity((uint256,uint256,uint256,uint256,uint256))` | `0xdbd19848` | Add to existing position |
| `decreaseLiquidity((uint256,uint128,uint256,uint256,uint256))` | `0x0c49ccbe` | Remove liquidity |
| `collect((uint256,address,uint128,uint128))` | `0xfc6f7865` | Claim fees |
| `burn(uint256)` | `0x42966c68` | Burn empty position NFT |
| `positions(uint256)` | `0x99fbab88` | Read position state; note: returns `tickSpacing` not `fee` |
| `tokenOfOwnerByIndex(address,uint256)` | `0x2f745c59` | ERC-721 enumerable |

### DLMMFactory

| Function | Selector | Notes |
|----------|----------|-------|
| `getNumberOfLBPairs()` | — | Returns uint256 (14 pairs as of verification) |
| `getLBPairAtIndex(uint256)` | — | Enumerate all DLMM pairs |

---

## 3. Addresses — Avalanche C-Chain (43114)

All addresses verified via `eth_getCode` returning non-empty bytecode.

### CL Core

| Contract | Address | Code size (bytes) |
|----------|---------|-------------------|
| RamsesV3Factory | `0xAE6E5c62328ade73ceefD42228528b70c8157D0d` | 3 424 |
| RamsesV3PoolDeployer | `0x6a4113ed0915bCf5E48e758e8f4cEBFFC07C66f9` | 23 353 |
| NonfungibleTokenPositionDescriptor | `0x6F17dB548544a19162E82b20c67aBee99960a89a` | 3 469 |
| TickLens | `0x3a7Aeb3c33922073F4F23207D0ff247e9694A100` | 1 060 |
| UniswapInterfaceMulticall | `0xf296bb0EAeAB6703d876b1BFe9d5693eF302B855` | — |

### CL Periphery

| Contract | Address | Code size (bytes) |
|----------|---------|-------------------|
| RamsesV3PositionManager (NFPM) | `0x0B4478e810D48B5882D4019D435A2f864Bab4F39` | 18 279 |
| SwapRouter | `0xc8B8fCbDb5C019D7802fFb0b39603395D7d3915c` | 8 098 |
| UniversalRouter | `0x5AcC35397D2ce81Ac54A4B1c6D9e1FB29F8EC6C6` | 15 003 |
| Quoter | `0xAdAe75447D112cfC401C952744de3E6d32456465` | 3 314 |
| QuoterV2 | `0xB7297301b7CC659BB96D51754643A0Df6eEA2138` | 5 824 |
| MixedRouteQuoterV1 | `0x3265d621c7d993151C8EB2aCd4902CdA0499A8a0` | — |

### CL Gauges

| Contract | Address | Code size (bytes) |
|----------|---------|-------------------|
| CL GaugeFactory | `0xE565310BAa582C768a77a3BB7F86a892eF07D04e` | 15 719 |
| FeeCollector (CL) | `0x1e1e2a861205767D69A51edf03cf5e3a278437bc` | 3 232 |

### Access Control & Admin

| Contract | Address | Notes |
|----------|---------|-------|
| AccessHub | `0x3176f6E4Be2448C53EDD59C27651EDFaA74bf483` | EIP-1967 UUPS proxy; impl `0x97301276a873207d34ccdf0eb6584c8189d0dd44` |
| ProxyAdmin | `0x3B91972c1Ff63296cb824a30997C7e4a982B7ee6` | Owner = Pharaoh Team Multisig |
| Pharaoh Team Multisig | `0xd1b27ccAF2A4dDcA0Ac32181374C70282492d843` | Governance |
| Pharaoh Timelock | `0x12d54ad6daf65d55b029df1b34b260c68fc0ddcf` | Governance timelock |

### DLMM

| Contract | Address | Code size (bytes) |
|----------|---------|-------------------|
| DLMMFactory | `0xEb480050b016f6c6d45203D2346B68bDDDa23D4D` | 13 909 |
| DLMMRouter | `0xff2BEFC4ff86CB0f3e8D3d9D6200B7A05BF5D93d` | 12 545 |
| DLMMQuoter | `0xDdaE0aA4E93be4936c1BcC12d3001b35C75fEF40` | 5 403 |
| DLMMRewarderFactory | `0xd28467eDe84cEde6B05070779E39Eaff4988548C` | 3 186 |
| DLMMFeeCollector | `0x684b340014556d15D754b812EF7d1b134b42289c` | 3 132 |
| DLMMPair impl | `0xF41253C1258A7A3c291E695158267b173c26d710` | 21 234 |

**Known DLMM pairs (as of block 87,487,317):**

| Index | Address | Tokens (X/Y) | BinStep |
|-------|---------|--------------|---------|
| 0 | `0x795f23F1ca0d81ECaB942E533893Ac937D032D19` | WAVAX / USDC | 10 |
| 1 | `0x16888EE58E706C253b821EAA637ae9b2cFeA255C` | (active) | — |
| 2 | `0x8aC5707f8D4BDe1d771d34c7AfD81c3922b73379` | WAVAX / USDC | 5 |
| 3–13 | via `getLBPairAtIndex(i)` | — | — |

---

## 4. Cross-chain summary

Pharaoh Exchange is **Avalanche C-Chain only**. Every address in §3 returns `0x` (no bytecode) on all other target chains, verified individually:

| Chain | Chain ID | RamsesV3Factory | DLMMFactory | NFPM |
|-------|----------|-----------------|-------------|------|
| Avalanche C-Chain | 43114 | `0xAE6E5c...` — **HAS CODE** | `0xEb4800...` — **HAS CODE** | `0x0B4478...` — **HAS CODE** |
| Ethereum | 1 | `0x` | `0x` | `0x` |
| Base | 8453 | `0x` | `0x` | `0x` |
| BNB Smart Chain | 56 | `0x` | `0x` | `0x` |
| Arbitrum One | 42161 | `0x` | `0x` | `0x` |
| Optimism | 10 | `0x` | `0x` | `0x` |
| Polygon PoS | 137 | `0x` | `0x` | `0x` |

---

## 5. Proxies

| Contract | Pattern | Proxy address | Implementation |
|----------|---------|---------------|----------------|
| AccessHub | **EIP-1967 UUPS** | `0x3176f6E4Be2448C53EDD59C27651EDFaA74bf483` | `0x97301276a873207d34ccdf0eb6584c8189d0dd44` (49 080-byte impl, has code) |
| DLMMPair (×14) | **EIP-1167 minimal proxy** (clone) | each pair address | `0xF41253C1258A7A3c291E695158267b173c26d710` |
| RamsesV3Factory | Not a proxy | `0xAE6E5c62328ade73ceefD42228528b70c8157D0d` | N/A — EIP-1967 impl slot = 0x0 |
| NFPM | Not a proxy | `0x0B4478e810D48B5882D4019D435A2f864Bab4F39` | N/A — EIP-1967 impl slot = 0x0 |
| CL GaugeFactory | Not a proxy | `0xE565310BAa582C768a77a3BB7F86a892eF07D04e` | N/A |
| DLMMFactory | Not a proxy | `0xEb480050b016f6c6d45203D2346B68bDDDa23D4D` | N/A |

**AccessHub UUPS notes:**
- EIP-1967 impl slot (`0x3608...bbc`) = `0x97301276a873207d34ccdf0eb6584c8189d0dd44`
- EIP-1967 admin slot = `0x0` (zero address, consistent with UUPS — no external admin)
- EIP-1967 beacon slot = `0x0` (not a beacon proxy)
- `ProxyAdmin` (`0x3B91972c...`) owner = Pharaoh Team Multisig (`0xd1b27cc...`)
- Upgrades to AccessHub go through governance, not an external ProxyAdmin

**DLMMPair EIP-1167 clone bytes (first pair):**
```
0x363d3d373d3d3d3d61002c806035363936013d73
f41253c1258a7a3c291e695158267b173c26d710  ← implementation
5af43d3d93803e603357fd5bf3
```

---

## 6. Detection invariants & gotchas

### Topic0 collision with Uniswap V3

| Event | Pharaoh topic0 | Uniswap V3 topic0 | Collision? |
|-------|---------------|-------------------|-----------|
| `Swap` | `0xc42079f9...` | `0xc42079f9...` | **YES — identical** |
| `PoolCreated` | `0x783cca1c...` | `0x783cca1c...` | **YES — identical** |
| `Mint` | `0xd78218c0...` | `0x7a53080b...` | No — Ramses adds `uint256 index` |
| `Collect` (pool) | `0x70935338...` | `0x70935338...` | YES — identical |
| `Burn` | `0x0c396cd9...` | `0x0c396cd9...` | YES — identical |
| `Flash` | `0xbdbdb71d...` | `0xbdbdb71d...` | YES — identical |
| `CollectProtocol` | `0x596b5739...` | `0x596b5739...` | YES — identical |

**Disambiguation by emitter address:** Because Pharaoh CL pools are deployed by RamsesV3PoolDeployer (`0x6a4113...`), every CL pool address can be verified against the factory's `getPool()` mapping. Do NOT rely on topic0 alone to identify Pharaoh vs. Uniswap V3 events — filter by `address` in `eth_getLogs`.

### How Ramses CL differs from Uniswap V3

1. **Mint event** has an extra `uint256 index` at position 3 (after `owner`). Any monitor decoding Uniswap V3 Mint data will misparse Pharaoh Mint data.
2. **Pool lookup** key is `tickSpacing (int24)` not `fee (uint24)`. `getPool(A, B, 10)` finds the 1-bp pool; `getPool(A, B, 200)` finds the 2% pool.
3. **Fee protocol** is `uint24` (not `uint8` as in Uniswap V3). Factory `SetFeeProtocol` topic0 differs.
4. **Access control** is via `AccessHub` rather than `owner()`. The factory returns its `accessHub()` address, not an `owner()`.
5. **NFPM positions()** returns `tickSpacing` (not `fee`) as the 3rd return value.

### DLMM vs CL pool disambiguation

- CL pools: deployed by `RamsesV3PoolDeployer` (`0x6a4113...`); verified via `RamsesV3Factory.getPool()`; emit Uniswap-V3-compatible Swap topic0 (`0xc42079f9...`).
- DLMM pairs: EIP-1167 clones of `0xF41253C1...`; enumerated via `DLMMFactory.getLBPairAtIndex()`; emit custom Swap topic0 (`0xad7d6f97...`).
- The two Swap topic0s do NOT collide; routing by topic0 is sufficient to distinguish CL from DLMM swaps.
- DLMM amounts are packed as `bytes32` (bin-level packed uint128 pairs); decoding requires bit-shifting.

### FeeProtocol event ambiguity

Both `RamsesV3Factory.SetFeeProtocol(uint24,uint24)` and `RamsesV3Pool.SetFeeProtocol(uint8,uint8,uint8,uint8)` exist but have **different topic0s** (`0x67a069e4` vs `0x973d8d92`). No collision.

---

## 7. Quick-copy detection constants

```python
# ── Pharaoh CL — RamsesV3Pool ──────────────────────────────────────────────
PHARAOH_CL_SWAP          = b"\xc4\x20\x79\xf9\x4a\x63\x50\xd7\xe6\x23\x5f\x29\x17\x49\x24\xf9\x28\xcc\x2a\xc8\x18\xeb\x64\xfe\xd8\x00\x4e\x11\x5f\xbc\xca\x67"
PHARAOH_CL_MINT          = b"\xd7\x82\x18\xc0\xd3\x04\xe8\x89\x3c\xb3\x20\x0a\xbe\x39\x4b\xbc\x8d\x5b\x78\x04\xd9\xc5\x1f\x23\x6d\xf9\xfd\xcf\x48\x1d\x02\xd3"
PHARAOH_CL_BURN          = b"\x0c\x39\x6c\xd9\x89\xa3\x9f\x44\x59\xb5\xfa\x1a\xed\x6a\x9a\x8d\xcd\xbc\x45\x90\x8a\xcf\xd6\x7e\x02\x8c\xd5\x68\xda\x98\x98\x2c"
PHARAOH_CL_COLLECT_POOL  = b"\x70\x93\x53\x38\xe6\x97\x75\x45\x6a\x85\xdd\xef\x22\x6c\x39\x5f\xb6\x68\xb6\x3f\xa0\x11\x5f\x5f\x20\x61\x0b\x38\x8e\x6c\xa9\xc0"
PHARAOH_CL_FLASH         = b"\xbd\xbd\xb7\x1d\x78\x60\x37\x6b\xa5\x2b\x25\xa5\x02\x8b\xee\xa2\x35\x81\x36\x4a\x40\x52\x2f\x6b\xcf\xb8\x6b\xb1\xf2\xdc\xa6\x33"
PHARAOH_CL_INITIALIZE    = b"\x98\x63\x60\x36\xcb\x66\xa9\xc1\x9a\x37\x43\x5e\xfc\x1e\x90\x14\x21\x90\x21\x4e\x8a\xbe\xb8\x21\xbd\xba\x3f\x29\x90\xdd\x4c\x95"
PHARAOH_CL_COLLECT_PROTO = b"\x59\x6b\x57\x39\x06\x21\x8d\x34\x11\x85\x0b\x26\xa6\xb4\x37\xd6\xc4\x52\x2f\xdb\x43\xd2\xd2\x38\x62\x63\xf8\x6d\x50\xb8\xb1\x51"

# ── Pharaoh CL — RamsesV3Factory ───────────────────────────────────────────
PHARAOH_FACTORY_POOL_CREATED   = b"\x78\x3c\xca\x1c\x04\x12\xdd\x0d\x69\x5e\x78\x45\x68\xc9\x6d\xa2\xe9\xc2\x2f\xf9\x89\x35\x7a\x2e\x8b\x1d\x9b\x2b\x4e\x6b\x71\x18"
PHARAOH_POOL_FEE_ADJUSTMENT    = b"\x0c\xba\x87\x18\x90\x55\xd3\xb5\xab\x05\xc9\x6f\xbd\x64\x1b\xc7\x66\x57\x6c\x9e\x7c\xf0\xd1\x95\xbd\xfb\x58\xa0\xc6\xa6\xdf\x24"  # FeeAdjustment(uint24,uint24) — pool-level, live-confirmed
PHARAOH_FACTORY_FEE_ADJUSTMENT = b"\xe4\xac\xcb\xae\xe8\x2f\xb8\x33\xac\x20\x7d\x4c\x44\x54\xc5\xa0\x4e\x85\xf5\xe1\xe9\xa2\x0a\x9e\x2c\x98\xe5\x4e\x87\x06\xff\x2b"  # FeeAdjustment(address,uint24) — factory-level, high-frequency (automated dynamic fee oracle)
PHARAOH_FACTORY_FEE_COLLECTOR  = b"\x64\x9c\x5e\x3d\x0e\xd1\x83\x89\x41\x96\x14\x8e\x19\x3a\xf3\x16\x45\x2b\x00\x37\xe7\x7d\x2f\xf0\xfe\xf2\x3b\x7d\xc7\x22\xbe\xd0"

# ── Pharaoh CL — NFPM ──────────────────────────────────────────────────────
PHARAOH_NFPM_INCREASE_LIQ = b"\x30\x67\x04\x8b\xee\xe3\x1b\x25\xb2\xf1\x68\x1f\x88\xda\xc8\x38\xc8\xbb\xa3\x6a\xf2\x5b\xfb\x2b\x7c\xf7\x47\x3a\x58\x47\xe3\x5f"
PHARAOH_NFPM_DECREASE_LIQ = b"\x26\xf6\xa0\x48\xee\x91\x38\xf2\xc0\xce\x26\x6f\x32\x2c\xb9\x92\x28\xe8\xd6\x19\xae\x2b\xff\x30\xc6\x7f\x8d\xcf\x9d\x23\x77\xb4"
PHARAOH_NFPM_COLLECT      = b"\x40\xd0\xef\xd1\xa5\x3d\x60\xec\xbf\x40\x97\x1b\x9d\xaf\x7d\xc9\x01\x78\xc3\xaa\xdc\x7a\xab\x17\x65\x63\x27\x38\xfa\x8b\x8f\x01"

# ── Pharaoh DLMM — DLMMPair ────────────────────────────────────────────────
PHARAOH_DLMM_SWAP           = b"\xad\x7d\x6f\x97\xab\xf5\x1c\xe1\x8e\x17\xa3\x8f\x4d\x70\xe9\x75\xbe\x9c\x07\x08\x47\x49\x87\xbb\x3e\x26\xad\x21\xbd\x93\xca\x70"
PHARAOH_DLMM_COLLECT_PROTO  = b"\x3f\x41\xa5\xdd\xc5\x37\x01\xcc\x7d\xb5\x77\xad\xe4\xf1\xfc\xa9\x83\x8a\x8e\xc0\xb5\xea\x50\xb9\xf0\xf5\xd1\x7b\xc4\x55\x4e\x32"
```

**Hex strings for SQL/monitoring queries:**

```
-- CL Swap (topic0, identical to Uniswap V3 — filter by emitter address)
\xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67

-- CL Mint (Ramses-specific, different from Uniswap V3)
\xd78218c0d304e8893cb3200abe394bbc8d5b7804d9c51f236df9fdcf481d02d3

-- CL Pool PoolCreated on Factory (identical to Uniswap V3 — filter by factory address)
\x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118

-- CL NFPM IncreaseLiquidity
\x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f

-- CL NFPM DecreaseLiquidity
\x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4

-- DLMM Swap (distinct from CL Swap — no address filter needed)
\xad7d6f97abf51ce18e17a38f4d70e975be9c0708474987bb3e26ad21bd93ca70

-- DLMM CollectedProtocolFees
\x3f41a5ddc53701cc7db577ade4f1fca9838a8ec0b5ea50b9f0f5d17bc4554e32
```

---

## 8. Verification & sources

### On-chain verification

| Check | Result |
|-------|--------|
| `eth_getCode` — all CL + DLMM addresses, Avalanche 43114 | All non-empty |
| `eth_getCode` — factory, NFPM, DLMMFactory on Ethereum, Base, BNB, Arbitrum, Optimism, Polygon | All `0x` (absent) |
| `eth_getLogs` — Swap topic0 on WAVAX/USDC pool `0xf01449...`, blocks 87485235–87487235 | 239 Swap logs with topic0 `0xc42079f9...` ✓ |
| `eth_getLogs` — NFPM `0x0B4478...`, blocks 87482317–87487317 | IncreaseLiquidity, DecreaseLiquidity, Collect, ERC-721 Transfer all confirmed ✓ |
| `eth_getLogs` — DLMM pairs, blocks 87482317–87487317 | Swap (`0xad7d6f97...`) and CollectedProtocolFees (`0x3f41a5dd...`) confirmed ✓ |
| EIP-1967 impl slot on AccessHub | `0x97301276a873207d34ccdf0eb6584c8189d0dd44` (non-zero, UUPS confirmed) |
| `factory.accessHub()` | Returns `0x3176f6E4...` (AccessHub proxy) ✓ |
| `DLMMFactory.getNumberOfLBPairs()` | 14 ✓ |
| NFPM `totalSupply()` | 101,857 positions minted |
| EIP-1167 clone check on DLMM pair `0x795f23...` | Impl `0xF41253...` extracted from bytecode ✓ |

### Sources

- Pharaoh official contract addresses: https://docs.phar.gg/pages/contract-addresses
- GitHub repository: https://github.com/PharaohExchange/pharaoh-contracts
- Pool events interface: `contracts/CL/core/interfaces/pool/IRamsesV3PoolEvents.sol`
- Factory interface: `contracts/CL/core/interfaces/IRamsesV3Factory.sol`
- NFPM interface: `contracts/CL/periphery/interfaces/INonfungiblePositionManager.sol`
- GaugeV3: `contracts/CL/gauge/GaugeV3.sol`
- DLMM event identification: 4byte.directory cross-check + live `eth_getLogs` on Avalanche
- Avalanche C-Chain RPC: https://avalanche-c-chain-rpc.publicnode.com
