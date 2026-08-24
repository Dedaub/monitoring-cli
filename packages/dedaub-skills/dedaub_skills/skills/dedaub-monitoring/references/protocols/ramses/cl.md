# Ramses Exchange CL (Concentrated Liquidity) — Topics, Selectors, Addresses (Arbitrum One)

**Status:** Verified — all addresses confirmed via `eth_getCode` on Arbitrum One (42161); absent (0x) on all other target chains (Ethereum 1, Base 8453, BNB 56, Optimism 10, Polygon 137).
**Sources:** [Ramses smart-order-router](https://github.com/RamsesExchange/smart-order-router) · [Ramses v3-contracts](https://github.com/RamsesExchange/ramses-v3-contracts) · live `eth_getLogs` cross-checks on Arbitrum One blocks ~441,981,627 (Burn/Collect), ~271,981,043 (Mint), ~421,981,043 (FeeAdjustment).
**Last verified:** 2026-06-10

---

## 0. Contract families

| Family | Contracts | Role |
|--------|-----------|------|
| **RamsesV2 CL core** | RamsesV2Factory (proxy), RamsesV2FactoryImpl, RamsesV2Pool (per-pair beacon proxy), RamsesV2PoolImpl | Pool creation, fee-tier management, all swap/LP logic |
| **CL periphery** | NonfungiblePositionManager (NFPM, proxy), SwapRouter, QuoterV2, TickLens (proxy) | User-facing LP management and routing |
| **CL gauges** | CLGaugeFactory (proxy), GaugeV3 (per gauge, beacon proxy) | Gauge reward distribution for CL positions |
| **Access & governance** | Voter (proxy), FeeCollector (proxy), ProxyAdmin | Protocol-wide role management and fee collection |

**Architecture notes:**

1. Ramses V2 CL on Arbitrum is the **earlier fee-based version** — `getPool(tokenA, tokenB, uint24 fee)` uses fee (not tickSpacing) as the third key, matching UniV3 exactly. The newer version (deployed on Pharaoh/Avalanche, Ramses HyperEVM) switched to tickSpacing.
2. Pool `Mint` event matches **standard UniV3** (`Mint(address,address,int24,int24,uint128,uint256,uint256)`, topic0 `0x7a53080b…`) — NOT the extended Ramses format with `uint256 index` used by Pharaoh CL.
3. All pools are **EIP-1967 beacon proxies**. The factory (`0xAA2cd7…`) acts as the beacon; `factory.implementation()` returns the pool logic contract (`0x6553aaee…`).
4. The factory, NFPM, Voter, CLGaugeFactory, FeeCollector, TickLens are all behind **standard EIP-1967 transparent proxies** (same 2449-byte proxy shell). The implementation address is stored in the standard EIP-1967 impl slot (`0x360894…382bbc`), confirmed via `eth_getStorageAt`; the admin slot returns the shared ProxyAdmin.
5. **No DLMM** in Ramses V2 CL on Arbitrum (DLMM was added separately in Pharaoh on Avalanche).
6. **Ramses HL** (DeFiLlama "ramses-hl") is the HyperEVM deployment — separate chain, separate addresses; not present on Arbitrum.

---

## 1. Topics

### 1.1 RamsesV2Pool (per-pair CL pool)

Swap topic0 cross-checked live against pool `0x30AFBcF9458c3131A6d051C621E307E6278E4110` (WETH/USDC, fee=500) — 17+ matching Swap logs found within 10k-block windows. Burn and Collect confirmed at block 441,981,766 (tx `0x24a0e66e…`). Mint confirmed at block ~271,981,000+ (tx `0x311a8080…`). FeeAdjustment(uint24,uint24) confirmed at block ~421,981,000+ (data: 250↔500 bps oscillation).

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `Initialize` | `Initialize(uint160,int24)` | `0x98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95` | Emitted once at pool creation |
| `Mint` | `Mint(address,address,int24,int24,uint128,uint256,uint256)` | `0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde` | **Standard UniV3 format** — no `uint256 index`; differs from Pharaoh/newer RamsesV3 (`0xd78218c0…`); verified live |
| `Collect` | `Collect(address,address,int24,int24,uint128,uint128)` | `0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0` | Fee collection from position; verified live |
| `Burn` | `Burn(address,int24,int24,uint128,uint256,uint256)` | `0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c` | Liquidity removal; verified live |
| `Swap` | `Swap(address,address,int256,int256,uint160,uint128,int24)` | `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67` | **Identical to Uniswap V3** — see §6; confirmed live with 17+ logs |
| `Flash` | `Flash(address,address,uint256,uint256,uint256,uint256)` | `0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633` | Flash loan |
| `IncreaseObservationCardinalityNext` | `IncreaseObservationCardinalityNext(uint16,uint16)` | `0xac49e518f90a358f652e4400164f05a5d8f7e35e7747279bc3a93dbf584e125a` | TWAP oracle expansion |
| `SetFeeProtocol` | `SetFeeProtocol(uint8,uint8,uint8,uint8)` | `0x973d8d92bb299f4af6ce49b52a8adb85ae46b9f214c4c4fc06ac77401237b133` | Per-pool protocol fee change |
| `CollectProtocol` | `CollectProtocol(address,address,uint128,uint128)` | `0x596b573906218d3411850b26a6b437d6c4522fdb43d2d2386263f86d50b8b151` | Protocol fee collection |
| `FeeAdjustment` | `FeeAdjustment(uint24,uint24)` | `0x0cba87189055d3b5ab05c96fbd641bc766576c9e7cf0d195bdfb58a0c6a6df24` | **Pool-level** dynamic fee update (oldFee, newFee) — **5–8 hits per 10k blocks live-confirmed** on WETH/USDC pool; data oscillates 250↔500 bps; Ramses-specific (no equivalent in UniV3) |

**Indexed fields:**
- `Mint`: `owner` (idx1), `tickLower` (idx2), `tickUpper` (idx3)
- `Collect`: `owner` (idx1), `tickLower` (idx2), `tickUpper` (idx3)
- `Burn`: `owner` (idx1), `tickLower` (idx2), `tickUpper` (idx3)
- `Swap`: `sender` (idx1), `recipient` (idx2)
- `Flash`: `sender` (idx1), `recipient` (idx2)
- `CollectProtocol`: `sender` (idx1), `recipient` (idx2)

### 1.2 RamsesV2Factory

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `PoolCreated` | `PoolCreated(address,address,uint24,int24,address)` | `0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118` | **Identical to Uniswap V3** factory event — see §6; all pools were created before block 100M (Jan–Jun 2023); publicnode RPC does not serve that range |

**Indexed fields:**
- `PoolCreated`: `token0` (idx1), `token1` (idx2), `fee` (idx3)

**Note:** No `FeeAdjustment(address,uint24)` factory-level event was found in the factory impl bytecode or via `eth_getLogs`. The dynamic-fee oracle signal in this version fires only at the **pool level** (`FeeAdjustment(uint24,uint24)` on each pool), not at the factory level. This contrasts with Pharaoh CL where a factory-level `FeeAdjustment(address,uint24)` also fires.

### 1.3 NonfungiblePositionManager (NFPM)

NFPM is an ERC-721 token; also emits standard ERC-721 events.

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `IncreaseLiquidity` | `IncreaseLiquidity(uint256,uint128,uint256,uint256)` | `0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f` | Confirmed live on NFPM |
| `DecreaseLiquidity` | `DecreaseLiquidity(uint256,uint128,uint256,uint256)` | `0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4` | Confirmed live on NFPM |
| `Collect` | `Collect(uint256,address,uint256,uint256)` | `0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01` | Confirmed live on NFPM; different sig from pool-level Collect |
| `SwitchAttachment` | `SwitchAttachment(uint256,uint256,uint256)` | `0xa2b6a38750bb1e3737c2be167c075c253a8bacf8b30136ab89db8cef52fd7f1c` | Ramses-specific — fires when a position NFT is moved between gauges; confirmed live |
| `Transfer` (ERC-721) | `Transfer(address,address,uint256)` | `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | Confirmed live; NFT position mint/transfer/burn |
| `Approval` (ERC-721) | `Approval(address,address,uint256)` | `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | Confirmed live |
| `ApprovalForAll` (ERC-721) | `ApprovalForAll(address,address,bool)` | `0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31` | Standard ERC-721 |

**Indexed fields:**
- `IncreaseLiquidity`: `tokenId` (idx1)
- `DecreaseLiquidity`: `tokenId` (idx1)
- `Collect`: `tokenId` (idx1)
- `SwitchAttachment`: `tokenId` (idx1); data: `oldAttachmentId`, `newAttachmentId`
- `Transfer`: `from` (idx1), `to` (idx2), `tokenId` (idx3)
- `Approval`: `owner` (idx1), `approved` (idx2), `tokenId` (idx3)

---

## 2. Function signatures

### RamsesV2Factory

| Function | Selector | Notes |
|----------|----------|-------|
| `getPool(address,address,uint24)` | `0x1698ee82` | Third param is **fee (uint24)**, not tickSpacing; reverts with tickSpacing |
| `createPool(address,address,int24,uint160)` | — | Also accepts tickSpacing version; see GitHub source |
| `feeAmountTickSpacing(uint24)` | `0x22afcccb` | Returns tickSpacing for fee tier: 100→1, 500→10, 3000→60, 10000→200 |
| `owner()` | `0x8da5cb5b` | Returns `0x20D630cF…` (Ramses Team Multisig) |
| `implementation()` | `0x5c60da1b` | **Beacon function** — returns current pool implementation `0x6553aaee…` |

### SwapRouter

| Function | Selector | Notes |
|----------|----------|-------|
| `exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))` | `0x414bf389` | Single-hop; 3rd param is **fee (uint24)**, includes deadline; confirmed in bytecode |
| `exactOutputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))` | `0xdb3e2198` | Single-hop exact output; confirmed in bytecode |
| `factory()` | `0xc45a0155` | Returns `0xAA2cd7…` (factory) |
| `WETH9()` | `0x4aa4a4fc` | Returns `0x82aF49…` (Arbitrum WETH) |

### NonfungiblePositionManager (NFPM)

| Function | Selector | Notes |
|----------|----------|-------|
| `positions(uint256)` | `0x99fbab88` | Returns position state; 5th field = `fee (uint24)` (NOT tickSpacing) |
| `mint((address,address,uint24,int24,int24,uint256,uint256,uint256,uint256,address,uint256))` | — | Creates new position NFT; uses fee tier |
| `increaseLiquidity((uint256,uint256,uint256,uint256,uint256))` | — | Add to existing position |
| `decreaseLiquidity((uint256,uint128,uint256,uint256,uint256))` | — | Remove liquidity |
| `collect((uint256,address,uint128,uint128))` | `0xfc6f7865` | Claim fees |
| `burn(uint256)` | `0x42966c68` | Burn empty position NFT |
| `name()` | `0x06fdde03` | Returns `"Ramses V2 Positions NFT-V1"` |
| `symbol()` | `0x95d89b41` | Returns `"RAM-V2-POS"` |
| `totalSupply()` | `0x18160ddd` | 22,085 as of block ~471,991,043 |
| `factory()` | `0xc45a0155` | Returns `0xAA2cd7…` |

---

## 3. Addresses — Arbitrum One (42161)

All addresses verified via `eth_getCode` on Arbitrum One returning non-empty bytecode.

### CL Core

| Contract | Address | Code size (bytes) | Notes |
|----------|---------|-------------------|-------|
| RamsesV2Factory (proxy) | `0xAA2cd7477c451E703f3B9Ba5663334914763edF8` | 2 449 | Transparent proxy + beacon; `implementation()` returns pool impl |
| RamsesV2Factory impl | `0xf896d16fa56a625802b6013f9f9202790ec69908` | 7 535 | Factory registry logic; contains PoolCreated topic0 |
| RamsesV2Pool impl (beacon) | `0x6553aaee5a3a482a7d61bb5e093b05140fe17e21` | 24 303 | Pool logic; used by all per-pair beacon proxies |

### CL Periphery

| Contract | Address | Code size (bytes) | Notes |
|----------|---------|-------------------|-------|
| NonfungiblePositionManager (NFPM, proxy) | `0xAA277CB7914b7e5514946Da92cb9De332Ce610EF` | 2 449 | Transparent proxy; impl `0xac9d1dfa…` (23 635 bytes) |
| SwapRouter (proxy) | `0xAA23611badAFB62D37E7295A682D21960ac85A90` | 2 449 | Proxy; impl `0xda3959ed…` (8 008 bytes); fee-based exactInputSingle |
| QuoterV2 (proxy) | `0xAA20EFF7ad2F523590dE6c04918DaAE0904E3b20` | 2 449 | Proxy; impl `0xff0431d2…` (5 685 bytes); `factory()` = RamsesV2Factory |
| TickLens (proxy) | `0xAA22A15c56e0Dd62eaA30B8C1f9F3eE6D137CeeB` | 2 449 | Proxy; impl `0x0c85af08…` |
| V3Migrator (proxy) | `0xAA27816EFCd7Ad09f8d80E9027a222cCc017Fbc7` | 2 449 | LP migration from V2 to V3; `factory()` = RamsesV2Factory |

### CL Gauges & Governance

| Contract | Address | Code size (bytes) | Notes |
|----------|---------|-------------------|-------|
| CLGaugeFactory (proxy) | `0xAA2fBD0c9393964aF7C66C1513E44A8caAAE4FdA` | 2 449 | Deploys GaugeV3 per pool |
| FeeCollector (proxy) | `0xAA2EF8a3B34B414f8F7b47183971F18E4f367dc4` | 2 449 | Collects protocol fees from pools |
| Voter (proxy) | `0xAAA2564DEb34763E3D05162Ed3f5C2658691F499` | 2 449 | Governance/gauge voting; holds references to factory, NFPM, CLGaugeFactory |

### Access Control & Admin

| Contract | Address | Code size (bytes) | Notes |
|----------|---------|-------------------|-------|
| ProxyAdmin | `0xA388d2dDb9eE3c4d84C04eAa396EaDb3357d052D` | 1 891 | Owner = Ramses Team Multisig; manages all proxy upgrades |
| Ramses Team Multisig | `0x20D630cF1f5628285BfB91DfaC8C89eB9087BE1A` | 171 | Governance |

### Pool Init Code Hash

```
POOL_INIT_CODE_HASH = 0x1565b129f2d1790f12d45301b9b084335626f0c92410bc43130763b69971135d
```

Used by periphery contracts (SwapRouter, Quoter) to compute pool addresses off-chain via CREATE2.

### Known pools (sample)

| Pool | Tokens | Fee | tickSpacing |
|------|--------|-----|-------------|
| `0x30AFBcF9458c3131A6d051C621E307E6278E4110` | WETH / USDC | 500 | 10 |
| `0x2428895370859036b7012F8239AD61082c21bf81` | WETH / USDC | 3000 | 60 |
| `0x7554b87B74F30Cb66AfE12c75c8268D8e39594fb` | WETH / USDC | 10000 | 200 |
| `0x23c6690c352a030Cf0D79963c9Dc0e0759dEDbf0` | WETH / USDT | 500 | 10 |
| `0x6CE9Bc2d8093D32aDdE4695a4530b96558388f7e` | WETH / ARB | 500 | 10 |
| `0x2760cc828b2E4D04F8ec261a5335426BB22D9291` | WETH / WBTC | 500 | 10 |

---

## 4. Cross-chain summary

Ramses Exchange V2 CL is **Arbitrum One only**. Every address in §3 returns `0x` (no bytecode) on all other target chains:

| Chain | Chain ID | RamsesV2Factory | NFPM |
|-------|----------|-----------------|------|
| Arbitrum One | 42161 | `0xAA2cd7…` — **HAS CODE** | `0xAA277C…` — **HAS CODE** |
| Ethereum | 1 | `0x` | `0x` |
| Base | 8453 | `0x` | `0x` |
| BNB Smart Chain | 56 | `0x` | `0x` |
| Optimism | 10 | `0x` | `0x` |
| Polygon PoS | 137 | `0x` | `0x` |

---

## 5. Proxies

| Contract | Pattern | Proxy address | Implementation |
|----------|---------|---------------|----------------|
| RamsesV2Factory | **Ramses transparent proxy** (2449 bytes) | `0xAA2cd7477c451E703f3B9Ba5663334914763edF8` | `0xf896d16fa56a625802b6013f9f9202790ec69908` (factory logic) |
| RamsesV2Pool (×N) | **EIP-1967 beacon proxy** (1491 bytes) | each pool address | beacon = factory `0xAA2cd7…`; `factory.implementation()` = `0x6553aaee…` |
| NFPM | **Ramses transparent proxy** | `0xAA277CB7914b7e5514946Da92cb9De332Ce610EF` | `0xac9d1dfa5483ebb06e623df31547b2a4dc8bf7ca` |
| SwapRouter | **Ramses transparent proxy** | `0xAA23611badAFB62D37E7295A682D21960ac85A90` | `0xda3959ed3039455df8cf8a79bd6dd5651135d13a` |
| QuoterV2 | **Ramses transparent proxy** | `0xAA20EFF7ad2F523590dE6c04918DaAE0904E3b20` | `0xff0431d2c8b64f6dac245279c43fa42555675ac2` |
| TickLens | **Ramses transparent proxy** | `0xAA22A15c56e0Dd62eaA30B8C1f9F3eE6D137CeeB` | `0x0c85af0813094ab73148158734889cc8baf29750` |
| CLGaugeFactory | **Ramses transparent proxy** | `0xAA2fBD0c9393964aF7C66C1513E44A8caAAE4FdA` | `0x8a5df3b02108b533c7e32a62ca985c5873a19cce` |
| FeeCollector | **Ramses transparent proxy** | `0xAA2EF8a3B34B414f8F7b47183971F18E4f367dc4` | `0x4a76a2f26cb26d4d4246470cc95e4da4ab0a0e92` |
| Voter | **Ramses transparent proxy** | `0xAAA2564DEb34763E3D05162Ed3f5C2658691F499` | `0xadf8c1d97ca6d6856407fb01a7856c8295f9323c` |
| GaugeV3 (×N) | **EIP-1967 beacon proxy** (1491 bytes) | each gauge address | beacon = CLGaugeFactory |

**Proxy notes:**
- The Ramses transparent proxy is a 2449-byte contract that uses the **standard EIP-1967 impl slot** (`0x360894…382bbc`) — confirmed non-zero via `eth_getStorageAt` on factory, NFPM, and SwapRouter. Implementations are also readable via `ProxyAdmin.getProxyImplementation(proxy)`. The EIP-1967 admin slot returns the ProxyAdmin (`0xA388d2dD…`).
- Beacon pool proxies: each pool's EIP-1967 beacon slot (`0xa3f0ad74…`) contains the factory address. Calling `factory.implementation()` returns the current pool logic.
- No AccessHub (UUPS) contract was deployed in this version; access control uses `owner()` on factory and voter.

---

## 6. Detection invariants & gotchas

### Topic0 collision with Uniswap V3

| Event | Ramses V2 topic0 | Uniswap V3 topic0 | Collision? |
|-------|-----------------|-------------------|-----------|
| `Swap` | `0xc42079f9…` | `0xc42079f9…` | **YES — identical** |
| `PoolCreated` | `0x783cca1c…` | `0x783cca1c…` | **YES — identical** |
| `Mint` | `0x7a53080b…` | `0x7a53080b…` | **YES — identical** (Ramses V2 uses standard UniV3 Mint, NOT the extended version) |
| `Collect` (pool) | `0x70935338…` | `0x70935338…` | YES — identical |
| `Burn` | `0x0c396cd9…` | `0x0c396cd9…` | YES — identical |
| `Flash` | `0xbdbdb71d…` | `0xbdbdb71d…` | YES — identical |
| `CollectProtocol` | `0x596b5739…` | `0x596b5739…` | YES — identical |

**Disambiguation by emitter address:** Ramses V2 pools are beacon proxies deployed by the factory (`0xAA2cd7…`). Verify emitter against `factory.getPool(token0, token1, fee)`. Do NOT rely on topic0 alone.

### Ramses V2 vs Pharaoh CL (same engine, different versions)

| Attribute | Ramses V2 (Arbitrum) | Pharaoh CL (Avalanche) |
|-----------|---------------------|----------------------|
| Pool key | `fee (uint24)` | `tickSpacing (int24)` |
| `Mint` topic0 | `0x7a53080b…` (standard UniV3) | `0xd78218c0…` (has extra `uint256 index`) |
| NFPM `positions()` returns | `fee` at field 4 | `tickSpacing` at field 4 |
| NFPM name | `"Ramses V2 Positions NFT-V1"` | `"Algebra Positions NFT-V1"` |
| NFPM symbol | `"RAM-V2-POS"` | `"ALGB-POS"` |
| SwapRouter exactInputSingle | `0x414bf389` (8 params, with fee + deadline) | `0xf59a7099` (7 params, tickSpacing, no deadline) |
| Factory FeeAdjustment | Pool-level only | Both pool-level and factory-level |
| DLMM | None | Trader Joe LB v2 fork |
| Pool proxy | EIP-1967 beacon → factory | EIP-1967 beacon → factory |

### FeeAdjustment event disambiguation

The `FeeAdjustment(uint24,uint24)` event on pools (`0x0cba8718…`) is **not indexed** — both old and new fee are in the `data` field. Filter by pool address to scope to a specific pair. The event fires at high frequency (5–8 per 10k blocks on active pools), representing the automated dynamic-fee oracle adjusting spreads based on volatility.

### NFPM SwitchAttachment

`SwitchAttachment(uint256 indexed tokenId, uint256 oldAttachmentId, uint256 newAttachmentId)` (`0xa2b6a387…`) is Ramses-specific. Fires when a user attaches/detaches a position NFT from a gauge for boosted rewards. Not present in UniV3.

---

## 7. Quick-copy detection constants

```python
# ── Ramses V2 CL — RamsesV2Pool ───────────────────────────────────────────────
RAMSES_V2_CL_SWAP          = b"\xc4\x20\x79\xf9\x4a\x63\x50\xd7\xe6\x23\x5f\x29\x17\x49\x24\xf9\x28\xcc\x2a\xc8\x18\xeb\x64\xfe\xd8\x00\x4e\x11\x5f\xbc\xca\x67"
RAMSES_V2_CL_MINT          = b"\x7a\x53\x08\x0b\xa4\x14\x15\x8b\xe7\xec\x69\xb9\x87\xb5\xfb\x7d\x07\xde\xe1\x01\xfe\x85\x48\x8f\x08\x53\xae\x16\x23\x9d\x0b\xde"
RAMSES_V2_CL_BURN          = b"\x0c\x39\x6c\xd9\x89\xa3\x9f\x44\x59\xb5\xfa\x1a\xed\x6a\x9a\x8d\xcd\xbc\x45\x90\x8a\xcf\xd6\x7e\x02\x8c\xd5\x68\xda\x98\x98\x2c"
RAMSES_V2_CL_COLLECT_POOL  = b"\x70\x93\x53\x38\xe6\x97\x75\x45\x6a\x85\xdd\xef\x22\x6c\x39\x5f\xb6\x68\xb6\x3f\xa0\x11\x5f\x5f\x20\x61\x0b\x38\x8e\x6c\xa9\xc0"
RAMSES_V2_CL_FLASH         = b"\xbd\xbd\xb7\x1d\x78\x60\x37\x6b\xa5\x2b\x25\xa5\x02\x8b\xee\xa2\x35\x81\x36\x4a\x40\x52\x2f\x6b\xcf\xb8\x6b\xb1\xf2\xdc\xa6\x33"
RAMSES_V2_CL_INITIALIZE    = b"\x98\x63\x60\x36\xcb\x66\xa9\xc1\x9a\x37\x43\x5e\xfc\x1e\x90\x14\x21\x90\x21\x4e\x8a\xbe\xb8\x21\xbd\xba\x3f\x29\x90\xdd\x4c\x95"
RAMSES_V2_CL_COLLECT_PROTO = b"\x59\x6b\x57\x39\x06\x21\x8d\x34\x11\x85\x0b\x26\xa6\xb4\x37\xd6\xc4\x52\x2f\xdb\x43\xd2\xd2\x38\x62\x63\xf8\x6d\x50\xb8\xb1\x51"
RAMSES_V2_CL_FEE_ADJUSTMENT = b"\x0c\xba\x87\x18\x90\x55\xd3\xb5\xab\x05\xc9\x6f\xbd\x64\x1b\xc7\x66\x57\x6c\x9e\x7c\xf0\xd1\x95\xbd\xfb\x58\xa0\xc6\xa6\xdf\x24"  # pool-level, live-confirmed, 5–8 per 10k blocks

# ── Ramses V2 CL — RamsesV2Factory ────────────────────────────────────────────
RAMSES_V2_FACTORY_POOL_CREATED = b"\x78\x3c\xca\x1c\x04\x12\xdd\x0d\x69\x5e\x78\x45\x68\xc9\x6d\xa2\xe9\xc2\x2f\xf9\x89\x35\x7a\x2e\x8b\x1d\x9b\x2b\x4e\x6b\x71\x18"

# ── Ramses V2 CL — NFPM ───────────────────────────────────────────────────────
RAMSES_V2_NFPM_INCREASE_LIQ     = b"\x30\x67\x04\x8b\xee\xe3\x1b\x25\xb2\xf1\x68\x1f\x88\xda\xc8\x38\xc8\xbb\xa3\x6a\xf2\x5b\xfb\x2b\x7c\xf7\x47\x3a\x58\x47\xe3\x5f"
RAMSES_V2_NFPM_DECREASE_LIQ     = b"\x26\xf6\xa0\x48\xee\x91\x38\xf2\xc0\xce\x26\x6f\x32\x2c\xb9\x92\x28\xe8\xd6\x19\xae\x2b\xff\x30\xc6\x7f\x8d\xcf\x9d\x23\x77\xb4"
RAMSES_V2_NFPM_COLLECT          = b"\x40\xd0\xef\xd1\xa5\x3d\x60\xec\xbf\x40\x97\x1b\x9d\xaf\x7d\xc9\x01\x78\xc3\xaa\xdc\x7a\xab\x17\x65\x63\x27\x38\xfa\x8b\x8f\x01"
RAMSES_V2_NFPM_SWITCH_ATTACH    = b"\xa2\xb6\xa3\x87\x50\xbb\x1e\x37\x37\xc2\xbe\x16\x7c\x07\x5c\x25\x3a\x8b\xac\xf8\xb3\x01\x36\xab\x89\xdb\x8c\xef\x52\xfd\x7f\x1c"
```

**Hex strings for SQL/monitoring queries:**

```
-- CL Swap (topic0, identical to UniV3 — filter by emitter address)
\xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67

-- CL Mint (STANDARD UniV3 — identical to UniV3, differs from Pharaoh CL 0xd78218c0)
\x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde

-- CL FeeAdjustment(uint24,uint24) — pool-level, high-frequency dynamic fee oracle
\x0cba87189055d3b5ab05c96fbd641bc766576c9e7cf0d195bdfb58a0c6a6df24

-- CL PoolCreated on Factory (identical to UniV3 — filter by factory address)
\x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118

-- NFPM IncreaseLiquidity
\x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f

-- NFPM DecreaseLiquidity
\x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4

-- NFPM SwitchAttachment (Ramses-specific, gauge attachment change)
\xa2b6a38750bb1e3737c2be167c075c253a8bacf8b30136ab89db8cef52fd7f1c
```

---

## 8. Verification & sources

### On-chain verification

| Check | Result |
|-------|--------|
| `eth_getCode` — factory, NFPM, SwapRouter, Quoter on Arbitrum 42161 | All non-empty |
| `eth_getCode` — factory, NFPM on Ethereum, Base, BNB, Optimism, Polygon | All `0x` (absent) |
| `factory.getPool(WETH, USDC, 500)` | `0x30AFBcF9…` (non-zero, pool confirmed) ✓ |
| `factory.feeAmountTickSpacing(500)` | `10` (tickSpacing=10 for fee=500) ✓ |
| `factory.implementation()` | `0x6553aaee…` (pool impl, 24 303 bytes) ✓ |
| `ProxyAdmin.getProxyImplementation(factory)` | `0xf896d16f…` (factory logic, 7 535 bytes) ✓ |
| `ProxyAdmin.getProxyImplementation(nfpm)` | `0xac9d1dfa…` (NFPM impl, 23 635 bytes) ✓ |
| `NFPM.name()` | `"Ramses V2 Positions NFT-V1"` ✓ |
| `NFPM.symbol()` | `"RAM-V2-POS"` ✓ |
| `NFPM.totalSupply()` | 22 085 positions ✓ |
| `SwapRouter.factory()` | `0xAA2cd7…` ✓ |
| `SwapRouter.WETH9()` | `0x82aF49…` (Arbitrum WETH) ✓ |
| `QuoterV2.factory()` | `0xAA2cd7…` ✓ |
| `eth_getLogs` — Swap topic0 on WETH/USDC pool, blocks ~471,984,489–471,989,489 | 17 Swap logs with `0xc42079f9…` ✓ |
| `eth_getLogs` — Burn + Collect on WETH/USDC pool, blocks ~441,981,627–441,991,627 | Burn `0x0c396cd9…` + Collect `0x70935338…` confirmed ✓ |
| `eth_getLogs` — Mint on WETH/USDC pool, blocks ~271,981,000–271,991,000 | Mint `0x7a53080b…` (standard UniV3, NOT 0xd78218c0) confirmed ✓ |
| `eth_getLogs` — FeeAdjustment on WETH/USDC pool, blocks ~421,981,000–421,991,000 | `0x0cba8718…` confirmed, 7 events; data oscillates between 250 and 500 bps ✓ |
| `eth_getLogs` — NFPM events, blocks ~271,981,000–271,991,000 | IncreaseLiquidity, DecreaseLiquidity, Collect, Transfer, Approval, SwitchAttachment all confirmed ✓ |
| pool beacon slot `0xa3f0ad74…` on WETH/USDC pool | `0xAA2cd7…` (factory as beacon) ✓ |

### Sources

- Ramses smart-order-router (contains addresses.ts with all Arbitrum addresses): https://github.com/RamsesExchange/smart-order-router
- Ramses v3-contracts (source code): https://github.com/RamsesExchange/ramses-v3-contracts
- Ramses v3-sdk (SDK, uses tickSpacing for newer version): https://github.com/RamsesExchange/v3-sdk
- Pool init code hash from smart-order-router: `RAMSES_POOL_INIT_CODE_HASH = 0x1565b129…`
- Arbitrum One RPC: https://arbitrum-one-rpc.publicnode.com
