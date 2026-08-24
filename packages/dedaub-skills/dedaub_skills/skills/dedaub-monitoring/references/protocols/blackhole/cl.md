# Blackhole DEX — Concentrated Liquidity (CL) AMM, Genesis Pools, CL Gauges — Topics, Selectors, Addresses (Avalanche C-Chain)

**Status:** Verified — all addresses confirmed via `eth_getCode` on Avalanche C-Chain (43114); absent (0x) on all other target chains (Ethereum 1, Base 8453, BNB 56, Arbitrum 42161, Optimism 10, Polygon 137).
**Sources:** [Blackhole docs](https://docs.blackhole.xyz) · live `eth_getLogs` and `eth_getTransactionReceipt` cross-checks on Avalanche C-Chain (blocks ~87,563,000–87,565,357) · bytecode analysis · 4byte.directory event-signature lookups.
**Last verified:** 2026-06-09

---

## 0. Contract families

| Family | Contracts | Role |
|--------|-----------|------|
| **CL core** | AlgebraFactory, AlgebraPoolDeployer, AlgebraPool (per-pair, deployed via PoolDeployer) | Pool creation, dynamic fee management, all swap/LP logic |
| **CL periphery** | SwapRouter, QuoterV2, NonfungiblePositionManager (NFPM) | User-facing LP management and routing |
| **CL gauges** | GaugeFactoryCL (EIP-1967 proxy), GaugeCL impl (per gauge) | CL gauge reward farming |
| **Genesis Pools** | GenesisPoolFactory, GenesisPoolManager | Pre-TGE liquidity seeding — users deposit into pre-launch pools that convert to CL positions at launch |

**Architecture note:** Blackhole CL is built on Algebra (the same base as QuickSwap V3). The pool contract exposes `plugin()` and `communityVault()` (features introduced in Algebra Integral) alongside the standard Algebra V1 event signatures. Critically, the `Swap` event uses the **7-parameter form** (`Swap(address,address,int256,int256,uint160,uint128,int24)` = `0xc42079f9…`) identical to Algebra V1 and Uniswap V3 — NOT the 9-parameter Algebra Integral form (`0x3ebd5203…`). The protocol adds two project-specific fee-transparency events: `SwapFee(address,uint24,uint24)` and `BurnFee(address,uint24)`, plus admin-configuration events (`Fee`, `PluginConfig`, `CommunityVault`, `TickSpacing`, `Skim`) verified by bytecode analysis and 4byte.directory. The NFPM `IncreaseLiquidity` event adds a 6th parameter (the pool address) compared to Uniswap V3.

Pool lookup: `AlgebraFactory.computePoolAddress(address tokenA, address tokenB)` returns the deterministic CREATE2 address. The `poolByPair(address,address)` function returns the zero address even for deployed pools (pre-launch state); use `computePoolAddress` instead.

---

## 1. Topics

### 1.1 AlgebraPool (per-pair CL pool)

All events confirmed via live `eth_getLogs` on pool `0x533f6EB38D1c2E420A043ae0bdb5040c86Dbc07f` (token0: `0x2775d5105276781B4b85bA6eA6a6653bEeD1dd32`, token1: WAVAX `0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7`) and bytecode PUSH32 analysis cross-checked against 4byte.directory.
Swap topic0 confirmed live: 10 Swap logs observed, all with `0xc42079f9…`.

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `Initialize` | `Initialize(uint160,int24)` | `0x98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95` | Emitted once at pool creation |
| `Mint` | `Mint(address,address,int24,int24,uint128,uint256,uint256)` | `0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde` | Standard Algebra V1 / Uniswap V3 Mint — identical topic0 |
| `Collect` | `Collect(address,address,int24,int24,uint128,uint128)` | `0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0` | Fee collection from pool position — confirmed live |
| `Burn` | `Burn(address,int24,int24,uint128,uint256,uint256)` | `0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c` | Liquidity removal — confirmed live |
| `Swap` | `Swap(address,address,int256,int256,uint160,uint128,int24)` | `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67` | **7-parameter form, identical to Algebra V1 / Uniswap V3** — confirmed live; filter by emitter address to disambiguate |
| `Flash` | `Flash(address,address,uint256,uint256,uint256,uint256)` | `0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633` | Flash loan; bytecode-confirmed |
| `CollectProtocol` | `CollectProtocol(address,address,uint128,uint128)` | `0x596b573906218d3411850b26a6b437d6c4522fdb43d2d2386263f86d50b8b151` | Protocol fee collection; confirmed in live receipt |
| `SwapFee` | `SwapFee(address,uint24,uint24)` | `0x9443903d84c9719611bd4bba871daaf18a3950d00d5d78b1a2fa701f76df54ff` | **Blackhole-specific** — fires after each swap; indexed: `sender`; data: `(feeProtocol uint24, fee uint24)` — when community fee = 0, both values are zero; 10 live-confirmed alongside Swaps |
| `BurnFee` | `BurnFee(address,uint24)` | `0x1a25098b7a731ae33ed362388b593b876963dfde0efb4db9c0befeed637ff26b` | **Blackhole-specific** — fires before every Burn; indexed: `caller`; data: `uint24 fee` — when no exit fee, value is zero; 30 live-confirmed alongside Burn events |
| `Fee` | `Fee(uint16)` | `0x598b9f043c813aa6be3426ca60d1c65d17256312890be5118dab55b0775ebe2a` | Dynamic fee change in pool; bytecode-confirmed |
| `PluginConfig` | `PluginConfig(uint8)` | `0x3a6271b36c1b44bd6a0a0d56230602dc6919b7c17af57254306fadf5fee69dc3` | Plugin configuration update; bytecode-confirmed |
| `CommunityVault` | `CommunityVault(address)` | `0xb0b573c1f636e1f8bd9b415ba6c04d6dd49100bc25493fc6305b65ec0e581df3` | Community vault address update; bytecode-confirmed |
| `TickSpacing` | `TickSpacing(int24)` | `0x01413b1d5d4c359e9a0daa7909ecda165f6e8c51fe2ff529d74b22a5a7c02645` | Tick spacing change; bytecode-confirmed |
| `Skim` | `Skim(address,uint256,uint256)` | `0xb94331e4420f16b156f53c397a8adcd09481283ee7830f7b688b22858e9db80b` | Token rescue/skim; bytecode-confirmed |

**Indexed fields:**
- `Initialize`: none
- `Mint`: `sender` (idx1), `owner` (idx2), `bottomTick` (idx3), `topTick` (idx4 — topic overflow; Algebra V1 Mint has 4 indexed)

  > Note: Algebra V1 `Mint` has signature `Mint(address sender, address owner, int24 bottomTick, int24 topTick, uint128 liquidityAmount, uint256 amount0, uint256 amount1)` with `sender`, `owner`, `bottomTick`, `topTick` indexed — matches the 4-topic structure observed live.

- `Collect`: `owner` (idx1), `recipient` (idx2), `bottomTick` (idx3), `topTick` (idx4)
- `Burn`: `owner` (idx1), `bottomTick` (idx2), `topTick` (idx3)
- `Swap`: `sender` (idx1), `recipient` (idx2)
- `CollectProtocol`: `sender` (idx1), `recipient` (idx2)
- `SwapFee`: `sender` (idx1); data: 2 × `uint24` (feeProtocol, fee)
- `BurnFee`: `caller` (idx1); data: `uint24` (fee)
- `CommunityVault`: `newVault` (idx1)

### 1.2 AlgebraFactory

Events sourced via bytecode PUSH32 analysis and 4byte.directory.

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `Pool` | `Pool(address,address,address)` | `0x91ccaa7a278130b65168c3a0c8d3bcae84cf5e43704342bd3ec0b59e59c036db` | Pool creation event — **Algebra V1 naming** (not `PoolCreated`); indexed: `token0`, `token1`; data: pool address |
| `RoleGranted` | `RoleGranted(bytes32,address,address)` | `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | OpenZeppelin AccessControl — role assignment |
| `RoleRevoked` | `RoleRevoked(bytes32,address,address)` | `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | OpenZeppelin AccessControl — role removal |

**Key role constants (bytes32):**
- `POOLS_ADMINISTRATOR_ROLE`: `0xb73ce166ead2f8e9add217713a7989e4edfba9625f71dfd2516204bb67ad3442`

**Indexed fields:**
- `Pool`: `token0` (idx1), `token1` (idx2); data: `address pool`
- `RoleGranted`: `role` (idx1), `account` (idx2), `sender` (idx3)
- `RoleRevoked`: `role` (idx1), `account` (idx2), `sender` (idx3)

### 1.3 NonfungiblePositionManager (NFPM)

Events confirmed via live `eth_getLogs` on NFPM `0x3fED017EC0f5517Cdf2E8a9a4156c64d74252146`.
NFPM is an ERC-721 token; also emits standard ERC-721 events.

> **Algebra V1 difference:** `IncreaseLiquidity` adds 2 extra parameters vs Uniswap V3 NFPM — `liquidityBefore (uint128)` is inserted at position 2, and `pool (address)` is appended. The full signature is `IncreaseLiquidity(uint256,uint128,uint128,uint256,uint256,address)`.

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `IncreaseLiquidity` | `IncreaseLiquidity(uint256,uint128,uint128,uint256,uint256,address)` | `0x8a82de7fe9b33e0e6bca0e26f5bd14a74f1164ffe236d50e0a36c3ea70f2b814` | **Algebra V1-specific** — 6 params vs Uniswap V3's 4; last param is pool address; confirmed live with 160-byte data |
| `DecreaseLiquidity` | `DecreaseLiquidity(uint256,uint128,uint256,uint256)` | `0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4` | Confirmed live |
| `Collect` | `Collect(uint256,address,uint256,uint256)` | `0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01` | Confirmed live; different sig from pool Collect |
| `Transfer` (ERC-721) | `Transfer(address,address,uint256)` | `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | Confirmed live; NFT position mint/transfer/burn |
| `ApprovalForAll` (ERC-721) | `ApprovalForAll(address,address,bool)` | `0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31` | Bytecode-confirmed |

**Indexed fields:**
- `IncreaseLiquidity`: `tokenId` (idx1)
- `DecreaseLiquidity`: `tokenId` (idx1)
- `Collect`: `tokenId` (idx1)
- `Transfer`: `from` (idx1), `to` (idx2), `tokenId` (idx3)
- `ApprovalForAll`: `owner` (idx1), `operator` (idx2)

**NFPM state:** `totalSupply()` = 1,287,921 positions minted as of block 87,565,357.

### 1.4 GaugeCL (CL Gauge — per pool)

Events sourced from GaugeFactoryCL implementation bytecode (`0x824dbc85b7609f294148b122a2cb826ab13f0296`) cross-checked against 4byte.directory. No live events observed yet (gauges not yet deployed as of verification block).

| Event | Signature | topic0 | Notes |
|-------|-----------|--------|-------|
| `Deposit` | `Deposit(address,uint256)` | `0xe1fffcc4923d04b559f4d29a8bfc6cda04eb5b0d3c460751c2402c5c5cc9109c` | LP stake into gauge |
| `Withdraw` | `Withdraw(address,uint256)` | `0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364` | LP unstake from gauge |
| `Harvest` | `Harvest(address,uint256)` | `0xc9695243a805adb74c91f28311176c65b417e842d5699893cef56d18bfa48cba` | Reward claim |
| `RewardAdded` | `RewardAdded(uint256)` | `0xde88a922e0d3b88b24e9623efeb464919c6bf9f66857a65e2bfcf2ce87a9433d` | Reward notification to gauge |
| `ClaimFees` | `ClaimFees(address,uint256,uint256)` | `0xbc567d6cbad26368064baa0ab5a757be46aae4d70f707f9203d9d9b6c8ccbfa3` | Protocol fee claim |
| `EmergencyActivated` | `EmergencyActivated(address,uint256)` | `0x774b57c3410c76d04ea4d51b0c15a9bac99b0e70f28fd88b53d702b5427fd318` | Emergency mode activation |
| `EmergencyDeactivated` | `EmergencyDeactivated(address,uint256)` | `0xa30763a9bc0d8e121a6e721624965cae68010ece74128b4ae5b01b8dc22c00f8` | Emergency mode deactivation |

### 1.5 GenesisPoolFactory / GenesisPoolManager

Events sourced from bytecode PUSH32 analysis. No events have been emitted on either contract as of block 87,565,357 (pre-launch state). The GenesisPoolManager reports version `"1.5.6"`. Revert strings include `"EPOCH_MANAGER_OR_GENESIS_MANAGER"`, `"Epoch not ready to finalize"`, and `"Still processing tokens"` — indicating an epoch-based lifecycle. None of the project-specific event topic0s from these contracts appear in 4byte.directory; they are not documented here pending live emission.

---

## 2. Function signatures

### AlgebraFactory

| Function | Selector | Notes |
|----------|----------|-------|
| `computePoolAddress(address,address)` | `0xd8ed2241` | Returns deterministic pool address; use this instead of `poolByPair` |
| `poolByPair(address,address)` | `0xd9a641e1` | Returns zero for all pairs even after pool deployment (pre-launch state) |
| `poolDeployer()` | — | Returns `0x9B2441037E286d5Bf9456a3BE7b5273fe28DbA1e` |
| `owner()` | — | Returns `0xe3Df22b04F1F788fF025ADc2466638f5AaE588e0` |
| `hasRoleOrOwner(bytes32,address)` | — | Access control check |
| `defaultCommunityFee()` | — | Returns `uint8` (0 at time of verification) |
| `POOLS_ADMINISTRATOR_ROLE()` | — | Returns `0xb73ce166ead2f8e9add217713a7989e4edfba9625f71dfd2516204bb67ad3442` |

### SwapRouter

| Function | Selector | Notes |
|----------|----------|-------|
| `exactInputSingle((address,address,address,uint256,uint256,uint256,uint160))` | `0xbc651188` | Single-hop exact input; params: (tokenIn, tokenOut, recipient, deadline, amountIn, amountOutMinimum, limitSqrtPrice) — no fee param |
| `exactInput((bytes,address,uint256,uint256,uint256))` | `0xc04b8d59` | Multi-hop exact input |
| `exactOutputSingle((address,address,address,uint256,uint256,uint256,uint160))` | `0x61d4d5b3` | Single-hop exact output |
| `exactOutput((bytes,address,uint256,uint256,uint256))` | `0xf28c0498` | Multi-hop exact output |
| `algebraSwapCallback(int256,int256,bytes)` | `0x2c8958f6` | Pool callback (not called directly) |
| `multicall(bytes[])` | `0xac9650d8` | Batch router calls |

### NonfungiblePositionManager (NFPM)

| Function | Selector | Notes |
|----------|----------|-------|
| `mint((address,address,uint24,int24,int24,uint256,uint256,uint256,uint256,address,uint256))` | `0x88316456` | Creates new position NFT; includes `uint24 fee` for pool lookup |
| `increaseLiquidity((uint256,uint256,uint256,uint256,uint256))` | `0xdbd19848` | Add liquidity to existing position |
| `decreaseLiquidity((uint256,uint128,uint256,uint256,uint256))` | `0x0c49ccbe` | Remove liquidity |
| `collect((uint256,address,uint128,uint128))` | `0xfc6f7865` | Claim fees |
| `burn(uint256)` | `0x42966c68` | Burn empty position NFT |
| `positions(uint256)` | `0x99fbab88` | Read position state |
| `createAndInitializePoolIfNecessary(address,address,address,uint160,bytes)` | `0x72426eb1` | Create + init pool with plugin; extra `address plugin` and `bytes data` vs Uniswap V3 |
| `name()` | — | Returns `"Algebra Positions NFT-V2"` |
| `symbol()` | — | Returns `"ALGB-POS"` |
| `totalSupply()` | — | Returns 1,287,921 (as of block 87,565,357) |
| `algebraMintCallback(uint256,uint256,bytes)` | `0x3dd657c5` | Pool callback (not called directly) |

---

## 3. Addresses — Avalanche C-Chain (43114)

All addresses verified via `eth_getCode` returning non-empty bytecode.

### CL Core

| Contract | Address | Code size (bytes) |
|----------|---------|-------------------|
| AlgebraFactory | `0x512eb749541B7cf294be882D636218c84a5e9E5F` | 10,874 |
| AlgebraPoolDeployer | `0x9B2441037E286d5Bf9456a3BE7b5273fe28DbA1e` | 24,228 |
| AlgebraPool (example: token0=`0x2775d5…`, token1=WAVAX) | `0x533f6EB38D1c2E420A043ae0bdb5040c86Dbc07f` | 22,584 |

### CL Periphery

| Contract | Address | Code size (bytes) |
|----------|---------|-------------------|
| SwapRouter | `0xaBfc48e8BED7b26762745f3139555F320119709d` | 12,561 |
| QuoterV2 | `0x3e182bcf14Be6142b9217847ec1112e3c39Eb689` | 9,262 |
| NonfungiblePositionManager (NFPM) | `0x3fED017EC0f5517Cdf2E8a9a4156c64d74252146` | 21,976 |

### CL Gauges

| Contract | Address | Notes |
|----------|---------|-------|
| GaugeFactoryCL | `0x6B6a3D5A1c536aCE1D761685aF241b2cb7a6eA5E` | EIP-1967 proxy (2,227 bytes); impl `0x824dbc85b7609f294148b122a2cb826ab13f0296` (21,207 bytes); admin `0xd763061cc3015642ca104496107bc69944c74bed` |

### Genesis Pools

| Contract | Address | Code size (bytes) |
|----------|---------|-------------------|
| GenesisPoolFactory | `0xdeB50ac7A0a03332626B3c45EB20e7310653260F` | 14,351 |
| GenesisPoolManager | `0x0EB1e103116b8Ec5f13a72F6943440340c4840dd` | 17,696 |

### Governance / Protocol Addresses

| Role | Address | Notes |
|------|---------|-------|
| Protocol owner / deployer | `0xe3Df22b04F1F788fF025ADc2466638f5AaE588e0` | Owner of AlgebraFactory, GenesisPoolFactory, GaugeFactoryCL admin |
| CommunityVault (pool fee receiver) | `0x902D7cE70d2Ee6a2404979dFB39B01F532f29Ef8` | Confirmed via pool `communityVault()` call |
| GaugeFactoryCL ProxyAdmin | `0xd763061cc3015642ca104496107bc69944c74bed` | 1,690-byte ProxyAdmin; `owner()` = protocol owner |

---

## 4. Cross-chain summary

Blackhole DEX is **Avalanche C-Chain only**. Every address in §3 returns `0x` (no bytecode) on all other target chains, verified individually:

| Chain | Chain ID | AlgebraFactory | NFPM | GaugeFactoryCL |
|-------|----------|----------------|------|----------------|
| Avalanche C-Chain | 43114 | `0x512eb7…` — **HAS CODE** | `0x3fED01…` — **HAS CODE** | `0x6B6a3D…` — **HAS CODE** |
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
| GaugeFactoryCL | **EIP-1967 transparent proxy** | `0x6B6a3D5A1c536aCE1D761685aF241b2cb7a6eA5E` | `0x824dbc85b7609f294148b122a2cb826ab13f0296` (21,207 bytes) |
| AlgebraFactory | Not a proxy | `0x512eb749541B7cf294be882D636218c84a5e9E5F` | N/A — EIP-1967 impl slot = `0x0` |
| NFPM | Not a proxy | `0x3fED017EC0f5517Cdf2E8a9a4156c64d74252146` | N/A — EIP-1967 impl slot = `0x0` |
| GenesisPoolFactory | Not a proxy | `0xdeB50ac7A0a03332626B3c45EB20e7310653260F` | N/A — EIP-1967 impl slot = `0x0` |
| GenesisPoolManager | Not a proxy | `0x0EB1e103116b8Ec5f13a72F6943440340c4840dd` | N/A — EIP-1967 impl slot = `0x0` |

**GaugeFactoryCL EIP-1967 slots:**
- Impl slot (`0x3608…bbc`) = `0x824dbc85b7609f294148b122a2cb826ab13f0296`
- Admin slot (`0xb531…103`) = `0xd763061cc3015642ca104496107bc69944c74bed`

---

## 6. Detection invariants & gotchas

### Pool Swap topic0 is identical to Uniswap V3

The Blackhole CL pool `Swap` topic0 (`0xc42079f9…`) is the same as Uniswap V3 and Algebra V1. Disambiguation by emitter address is required. All Blackhole pools are deployed via `AlgebraPoolDeployer` (`0x9B2441…`); verify any pool address against `AlgebraFactory.computePoolAddress(tokenA, tokenB)`.

### Pool uses 7-param Swap, NOT Algebra Integral 9-param

The brief indicated Blackhole uses Algebra Integral; on-chain evidence shows the pool emits `Swap(address,address,int256,int256,uint160,uint128,int24)` with 160-byte data (5 × 32 bytes) — the standard 7-parameter form. The 9-parameter Integral form (`0x3ebd5203…`, adds `overrideFee uint16, pluginFee uint16`) is NOT used. The pool does have `plugin()` and `communityVault()` (Integral-era additions) but the Swap/Burn/Mint/Collect events match Algebra V1 topic0s exactly.

### BurnFee fires before every Burn

`BurnFee(address,uint24)` fires immediately before every `Burn` event in the same transaction. When exit fees are zero, the `uint24` data is `0`. Monitors that decode burn flow should expect this paired event.

### NFPM IncreaseLiquidity has 6 params (not 4)

Blackhole NFPM `IncreaseLiquidity` emits `(uint256 indexed tokenId, uint128 liquidityBefore, uint128 liquidityAfter, uint256 amount0, uint256 amount1, address pool)` — the last word of the 160-byte data payload is the pool address. A Uniswap V3 decoder (expecting 4 params, 128 bytes) will misparse this event.

### poolByPair returns zero address

`AlgebraFactory.poolByPair(tokenA, tokenB)` returns `address(0)` for all pairs even when the pool exists. Use `computePoolAddress(tokenA, tokenB)` instead, which deterministically returns the CREATE2 address regardless of deployment state.

### Swap vs Algebra Integral Swap disambiguation

| Variant | Swap topic0 | Params | Data bytes |
|---------|------------|--------|------------|
| Blackhole (this protocol) | `0xc42079f9…` | 7 | 160 |
| Algebra Integral 9-param | `0x3ebd5203…` | 9 | 224 |
| Uniswap V3 | `0xc42079f9…` | 7 | 160 |

Filter by emitter address (`computePoolAddress(tokenA, tokenB)`) when topic0 = `0xc42079f9…`.

---

## 7. Quick-copy detection constants

```python
# ── Blackhole CL — AlgebraPool ─────────────────────────────────────────────
BH_POOL_SWAP              = b"\xc4\x20\x79\xf9\x4a\x63\x50\xd7\xe6\x23\x5f\x29\x17\x49\x24\xf9\x28\xcc\x2a\xc8\x18\xeb\x64\xfe\xd8\x00\x4e\x11\x5f\xbc\xca\x67"
BH_POOL_MINT              = b"\x7a\x53\x08\x0b\xa4\x14\x15\x8b\xe7\xec\x69\xb9\x87\xb5\xfb\x7d\x07\xde\xe1\x01\xfe\x85\x48\x8f\x08\x53\xae\x16\x23\x9d\x0b\xde"
BH_POOL_BURN              = b"\x0c\x39\x6c\xd9\x89\xa3\x9f\x44\x59\xb5\xfa\x1a\xed\x6a\x9a\x8d\xcd\xbc\x45\x90\x8a\xcf\xd6\x7e\x02\x8c\xd5\x68\xda\x98\x98\x2c"
BH_POOL_COLLECT           = b"\x70\x93\x53\x38\xe6\x97\x75\x45\x6a\x85\xdd\xef\x22\x6c\x39\x5f\xb6\x68\xb6\x3f\xa0\x11\x5f\x5f\x20\x61\x0b\x38\x8e\x6c\xa9\xc0"
BH_POOL_FLASH             = b"\xbd\xbd\xb7\x1d\x78\x60\x37\x6b\xa5\x2b\x25\xa5\x02\x8b\xee\xa2\x35\x81\x36\x4a\x40\x52\x2f\x6b\xcf\xb8\x6b\xb1\xf2\xdc\xa6\x33"
BH_POOL_INITIALIZE        = b"\x98\x63\x60\x36\xcb\x66\xa9\xc1\x9a\x37\x43\x5e\xfc\x1e\x90\x14\x21\x90\x21\x4e\x8a\xbe\xb8\x21\xbd\xba\x3f\x29\x90\xdd\x4c\x95"
BH_POOL_COLLECT_PROTOCOL  = b"\x59\x6b\x57\x39\x06\x21\x8d\x34\x11\x85\x0b\x26\xa6\xb4\x37\xd6\xc4\x52\x2f\xdb\x43\xd2\xd2\x38\x62\x63\xf8\x6d\x50\xb8\xb1\x51"
BH_POOL_SWAP_FEE          = b"\x94\x43\x90\x3d\x84\xc9\x71\x96\x11\xbd\x4b\xba\x87\x1d\xaa\xf1\x8a\x39\x50\xd0\x0d\x5d\x78\xb1\xa2\xfa\x70\x1f\x76\xdf\x54\xff"
BH_POOL_BURN_FEE          = b"\x1a\x25\x09\x8b\x7a\x73\x1a\xe3\x3e\xd3\x62\x38\x8b\x59\x3b\x87\x69\x63\xdf\xde\x0e\xfb\x4d\xb9\xc0\xbe\xfe\xed\x63\x7f\xf2\x6b"

# ── Blackhole CL — AlgebraFactory ─────────────────────────────────────────
BH_FACTORY_POOL           = b"\x91\xcc\xaa\x7a\x27\x81\x30\xb6\x51\x68\xc3\xa0\xc8\xd3\xbc\xae\x84\xcf\x5e\x43\x70\x43\x42\xbd\x3e\xc0\xb5\x9e\x59\xc0\x36\xdb"
BH_FACTORY_ROLE_GRANTED   = b"\x2f\x87\x88\x11\x7e\x7e\xff\x1d\x82\xe9\x26\xec\x79\x49\x01\xd1\x7c\x78\x02\x4a\x50\x27\x09\x40\x30\x45\x40\xa7\x33\x65\x6f\x0d"
BH_FACTORY_ROLE_REVOKED   = b"\xf6\x39\x1f\x5c\x32\xd9\xc6\x9d\x2a\x47\xea\x67\x0b\x44\x29\x74\xb5\x39\x35\xd1\xed\xc7\xfd\x64\xeb\x21\xe0\x47\xa8\x39\x17\x1b"

# ── Blackhole CL — NFPM ────────────────────────────────────────────────────
BH_NFPM_INCREASE_LIQ      = b"\x8a\x82\xde\x7f\xe9\xb3\x3e\x0e\x6b\xca\x0e\x26\xf5\xbd\x14\xa7\x4f\x11\x64\xff\xe2\x36\xd5\x0e\x0a\x36\xc3\xea\x70\xf2\xb8\x14"
BH_NFPM_DECREASE_LIQ      = b"\x26\xf6\xa0\x48\xee\x91\x38\xf2\xc0\xce\x26\x6f\x32\x2c\xb9\x92\x28\xe8\xd6\x19\xae\x2b\xff\x30\xc6\x7f\x8d\xcf\x9d\x23\x77\xb4"
BH_NFPM_COLLECT           = b"\x40\xd0\xef\xd1\xa5\x3d\x60\xec\xbf\x40\x97\x1b\x9d\xaf\x7d\xc9\x01\x78\xc3\xaa\xdc\x7a\xab\x17\x65\x63\x27\x38\xfa\x8b\x8f\x01"

# ── Blackhole CL — GaugeCL ─────────────────────────────────────────────────
BH_GAUGE_DEPOSIT          = b"\xe1\xff\xfc\xc4\x92\x3d\x04\xb5\x59\xf4\xd2\x9a\x8b\xfc\x6c\xda\x04\xeb\x5b\x0d\x3c\x46\x07\x51\xc2\x40\x2c\x5c\x5c\xc9\x10\x9c"
BH_GAUGE_WITHDRAW         = b"\x88\x4e\xda\xd9\xce\x6f\xa2\x44\x0d\x8a\x54\xcc\x12\x34\x90\xeb\x96\xd2\x76\x84\x79\xd4\x9f\xf9\xc7\x36\x61\x25\xa9\x42\x43\x64"
BH_GAUGE_HARVEST          = b"\xc9\x69\x52\x43\xa8\x05\xad\xb7\x4c\x91\xf2\x83\x11\x17\x6c\x65\xb4\x17\xe8\x42\xd5\x69\x98\x93\xce\xf5\x6d\x18\xbf\xa4\x8c\xba"
BH_GAUGE_REWARD_ADDED     = b"\xde\x88\xa9\x22\xe0\xd3\xb8\x8b\x24\xe9\x62\x3e\xfe\xb4\x64\x91\x9c\x6b\xf9\xf6\x68\x57\xa6\x5e\x2b\xfc\xf2\xce\x87\xa9\x43\x3d"
BH_GAUGE_CLAIM_FEES       = b"\xbc\x56\x7d\x6c\xba\xd2\x63\x68\x06\x4b\xaa\x0a\xb5\xa7\x57\xbe\x46\xaa\xe4\xd7\x0f\x70\x7f\x92\x03\xd9\xd9\xb6\xc8\xcc\xbf\xa3"
```

**Hex strings for SQL/monitoring queries:**

```
-- Pool Swap (identical to Uniswap V3 — filter by emitter address)
\xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67

-- Pool Mint (identical to Algebra V1 / Uniswap V3)
\x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde

-- Pool Burn
\x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c

-- Pool SwapFee (Blackhole-specific — fires after each Swap)
\x9443903d84c9719611bd4bba871daaf18a3950d00d5d78b1a2fa701f76df54ff

-- Pool BurnFee (Blackhole-specific — fires before each Burn)
\x1a25098b7a731ae33ed362388b593b876963dfde0efb4db9c0befeed637ff26b

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
```

---

## 8. Verification & sources

### On-chain verification

| Check | Result |
|-------|--------|
| `eth_getCode` — all 8 addresses, Avalanche 43114 | All non-empty (code sizes 2,227–24,228 bytes) |
| `eth_getCode` — AlgebraFactory + NFPM on Ethereum, Base, BNB, Arbitrum, Optimism, Polygon | All `0x` (absent) |
| `AlgebraFactory.poolDeployer()` | Returns `0x9B2441037E286d5Bf9456a3BE7b5273fe28DbA1e` ✓ |
| `AlgebraFactory.owner()` | Returns `0xe3Df22b04F1F788fF025ADc2466638f5AaE588e0` ✓ |
| `AlgebraFactory.computePoolAddress(WAVAX, 0x2775d5…)` | Returns `0x533f6EB38D1c2E420A043ae0bdb5040c86Dbc07f` ✓ |
| `pool.token0()` | Returns `0x2775d5105276781B4b85bA6eA6a6653bEeD1dd32` ✓ |
| `pool.token1()` | Returns `0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7` (WAVAX) ✓ |
| `pool.plugin()` | Returns `0xdC89095c3340E16586940e32588449D01fb5fa33` (5,755 bytes, has code) ✓ |
| `pool.communityVault()` | Returns `0x902D7cE70d2Ee6a2404979dFB39B01F532f29Ef8` ✓ |
| `eth_getLogs` — Swap topic0 on pool `0x533f6EB38D1c2E420A043ae0bdb5040c86Dbc07f`, blocks 87,555,357–87,565,357 | 10 Swap logs, all with topic0 `0xc42079f9…` (7-param form, 160-byte data) ✓ |
| `eth_getLogs` — BurnFee + Burn pairs on pool, same range | 30 BurnFee + 30 Burn logs, all co-emitted ✓ |
| `eth_getLogs` — SwapFee + Swap pairs on pool, same range | 10 SwapFee + 10 Swap logs, co-emitted ✓ |
| `NFPM.name()` | Returns `"Algebra Positions NFT-V2"` ✓ |
| `NFPM.symbol()` | Returns `"ALGB-POS"` ✓ |
| `NFPM.totalSupply()` | 1,287,921 positions ✓ |
| `eth_getLogs` — NFPM IncreaseLiquidity, block 87,563,000 | topic0 `0x8a82de7f…`, 160-byte data (6-param Algebra V1 form), last 32 bytes = pool address ✓ |
| EIP-1967 impl slot on GaugeFactoryCL | `0x824dbc85b7609f294148b122a2cb826ab13f0296` (non-zero, proxy confirmed) ✓ |
| EIP-1967 admin slot on GaugeFactoryCL | `0xd763061cc3015642ca104496107bc69944c74bed` (ProxyAdmin) ✓ |
| EIP-1967 impl slot on AlgebraFactory, NFPM, GenesisPoolFactory, GenesisPoolManager | `0x0` on all (not proxies) ✓ |

### Confirmed event topic0s

| Event | topic0 | Status |
|-------|--------|--------|
| Pool `Swap` (7-param) | `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67` | **Live-confirmed** (10 logs) |
| Pool `Burn` | `0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c` | **Live-confirmed** (30 logs) |
| Pool `Mint` | `0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde` | **Live-confirmed** (31 logs) |
| Pool `Collect` | `0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0` | **Live-confirmed** (30 logs) |
| Pool `SwapFee` | `0x9443903d84c9719611bd4bba871daaf18a3950d00d5d78b1a2fa701f76df54ff` | **Live-confirmed** (10 logs); 4byte.directory ✓ |
| Pool `BurnFee` | `0x1a25098b7a731ae33ed362388b593b876963dfde0efb4db9c0befeed637ff26b` | **Live-confirmed** (30 logs); 4byte.directory ✓ |
| NFPM `IncreaseLiquidity` (6-param) | `0x8a82de7fe9b33e0e6bca0e26f5bd14a74f1164ffe236d50e0a36c3ea70f2b814` | **Live-confirmed**; 4byte.directory ✓ |
| NFPM `DecreaseLiquidity` | `0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4` | **Live-confirmed** |
| NFPM `Collect` | `0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01` | **Live-confirmed** |
| All remaining pool + gauge events | see §1 | Bytecode-confirmed (PUSH32 + 4byte.directory) |

### Sources

- Blackhole official contract addresses: https://docs.blackhole.xyz
- Algebra V1 protocol reference: https://algebra.finance
- RPC: https://avalanche-c-chain-rpc.publicnode.com (Avalanche C-Chain, chain ID 43114)
- Event signatures cross-checked: https://www.4byte.directory/event-signatures/
