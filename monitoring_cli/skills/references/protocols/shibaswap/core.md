# ShibaSwap — Topics, Selectors, Addresses (Ethereum-only)

**Status:** verified against Ethereum mainnet RPC (`https://ethereum-rpc.publicnode.com`) on 2026-06-10. All six non-Ethereum chains (Base 8453, BNB 56, Avalanche 43114, Arbitrum 42161, Optimism 10, Polygon 137) return `eth_getCode = 0x` for all ShibaSwap addresses — protocol is **Ethereum-only**.
**Scope:** full ShibaSwap protocol — UniV2-style DEX (Factory + Router + SSLP pairs), BONE governance token, TopDog farming (MasterChef-style), Bury staking (xSHIB / xLEASH / tBONE), and BoneLocker vesting.

ShibaSwap is a Uniswap V2 fork. **All AMM event `topic0`s are identical to Uniswap V2.** The pair LP token is branded `symbol = "SSLP"` (not `"UNI-V2"`), `name = "ShibaSwap LP Token"`. The pair `init code hash` is `0x65d1a3b1…` — **different** from UniV2's `0x96e8ac42…`. All core contracts are immutable (no EIP-1967 proxy slot set). `TopDog` is the BONE.owner and mints BONE as farming rewards; `BoneLocker` holds team/dev BONE vesting (~4.08 M BONE locked). The "Bury" mechanism is xSushi-style single-asset staking: depositing SHIB → mints xSHIB, depositing LEASH → mints xLEASH, depositing BONE → mints tBONE. The "Fetch" contract (`feeTo` on Factory) collects the 1/6-of-fee protocol cut from pair `mint`/`burn`. BONE max supply ≈ 250 M (current circulating ≈ 250 M). SHIB supply ≈ 1 quadrillion (18 decimals). LEASH supply ≈ 1.75 × 10¹⁷ raw units (18 decimals).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 ShibaSwapFactory

| topic0 | Event |
|--------|-------|
| `0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9` | `PairCreated(address indexed token0, address indexed token1, address pair, uint256)` |

Identical to UniV2. `token0 < token1` enforced. `pair` and pair-count are in `data`. 1 041 pairs as of verification.

### 1.2 ShibaSwap Pair (AMM events — identical topic0s to UniV2)

| topic0 | Event |
|--------|-------|
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` | `Mint(address indexed sender, uint256 amount0, uint256 amount1)` |
| `0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496` | `Burn(address indexed sender, uint256 amount0, uint256 amount1, address indexed to)` |
| `0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822` | `Swap(address indexed sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, address indexed to)` |
| `0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1` | `Sync(uint112 reserve0, uint112 reserve1)` |

All four verified live against the SHIB/WETH pair (`0xCF6dAAB9…`). No custom `Fees` event — the protocol fee cut is taken as LP minted inside `mint`/`burn` and tracked only via the standard `Transfer` event. `Swap` sender in `topic1` is the Router address or the direct caller.

### 1.3 ShibaSwap Pair (ERC-20 LP token — "SSLP")

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` |

`Transfer(0x0 → user)` = liquidity add; `Transfer(user → 0x0)` = liquidity remove. LP token: `name = "ShibaSwap LP Token"`, `symbol = "SSLP"`, 18 decimals.

### 1.4 TopDog (farming / MasterChef)

| topic0 | Event |
|--------|-------|
| `0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15` | `Deposit(address indexed user, uint256 indexed pid, uint256 amount)` |
| `0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568` | `Withdraw(address indexed user, uint256 indexed pid, uint256 amount)` |
| `0xbb757047c2b5f3974fe26b7c10f732e7bce710b0952a71082702781e62ae0595` | `EmergencyWithdraw(address indexed user, uint256 indexed pid, uint256 amount)` |

`Deposit` and `Withdraw` verified live from block 12 987 012 onwards. `EmergencyWithdraw` is rare. `pid` is the pool index (0–51; 52 pools total). `amount` in `data`; `user` and `pid` are indexed (`topic1`, `topic2`).

### 1.5 Bury staking — xSHIB (BuryShib), xLEASH (BuryLeash), tBONE

The Bury contracts are xSushi-style receipt tokens. They do **not** emit custom `Enter`/`Leave` events — staking and unstaking emit only standard ERC-20 `Transfer` events:

| topic0 | Meaning |
|--------|---------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(0x0 → user)` = staking (enter); `Transfer(user → 0x0)` = unstaking (leave) |

Filter on the specific Bury contract address + `Transfer` topic0 + `topic1 = 0x0000…0` (mint) or `topic2 = 0x0000…0` (burn) to isolate stake/unstake flows.

### 1.6 BoneLocker

| topic0 | Event |
|--------|-------|
| `0x2d8847c3ea1c4b6f02609bff2ac1776bc3663d31a747102d5722bdffcc2e3721` | `LockingPeriod(address indexed user, uint256 newLockingPeriod, uint256 newDevLockingPeriod)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |

BoneLocker holds BONE for developer/team vesting. BONE balance verified as ≈ 4.08 M BONE locked.

---

## 2. Function signatures (Ethereum, chain-agnostic)

### 2.1 ShibaSwapFactory

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc9c65396` | `createPair(address tokenA, address tokenB)` | Returns `address pair`. Emits `PairCreated`. CREATE2 with init code hash `0x65d1a3b1…`. |
| `0xe6a43905` | `getPair(address, address)` | Symmetric mapping. Returns `address(0)` if no pair. |
| `0x1e3dd18b` | `allPairs(uint256)` | Array of all pairs; 1 041 entries. |
| `0x574f2ba3` | `allPairsLength()` | `uint256` count. Returns `1041`. |
| `0x017e7e58` | `feeTo()` | Returns Fetch contract `0x00e82E98…` — protocol fee recipient. |
| `0x094b7415` | `feeToSetter()` | `address` — governance control. |
| `0x9aab9248` | `pairCodeHash()` | Returns `0x65d1a3b1e46c6e4f1be1ad5f99ef14dc488ae0549dc97db9b30afe2241ce1c7a` — pure. |

### 2.2 ShibaSwap Pair (AMM core — identical to UniV2)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0902f1ac` | `getReserves()` | `(uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast)` |
| `0xc45a0155` | `factory()` | ShibaSwap Factory address. |
| `0x0dfe1681` | `token0()` | Lower-address token. |
| `0xd21220a7` | `token1()` | Higher-address token. |
| `0x6a627842` | `mint(address to)` | Returns `uint256 liquidity`. Tokens must be sent to pair first. |
| `0x89afcb44` | `burn(address to)` | Returns `(uint256 amount0, uint256 amount1)`. LP must be sent to pair first. |
| `0x022c0d9f` | `swap(uint256 amount0Out, uint256 amount1Out, address to, bytes data)` | Flash-loan capable (non-empty `data` triggers callback). |
| `0xbc25cf77` | `skim(address to)` | Rebalances excess. |
| `0xfff6cae9` | `sync()` | Forces reserves to current balances. |

### 2.3 ShibaSwap Pair (ERC-20 LP "SSLP")

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x06fdde03` | `name()` | `"ShibaSwap LP Token"` |
| `0x95d89b41` | `symbol()` | `"SSLP"` |
| `0x313ce567` | `decimals()` | `uint8 = 18` |
| `0x18160ddd` | `totalSupply()` | `uint256` |
| `0x70a08231` | `balanceOf(address)` | `uint256` |
| `0x095ea7b3` | `approve(address, uint256)` | Returns `bool`. |
| `0xa9059cbb` | `transfer(address, uint256)` | Returns `bool`. |
| `0x23b872dd` | `transferFrom(address, address, uint256)` | Returns `bool`. |
| `0xd505accf` | `permit(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s)` | ERC-2612 gasless approve. |

### 2.4 ShibaSwap Router

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc45a0155` | `factory()` | Immutable. |
| `0xad5c4648` | `WETH()` | Returns `0xC02aaA39…` (WETH9). Immutable. |
| `0xe8e33700` | `addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)` | Returns `(amountA, amountB, liquidity)`. |
| `0xf305d719` | `addLiquidityETH(address,uint256,uint256,uint256,address,uint256)` | `payable`. |
| `0xbaa2abde` | `removeLiquidity(address,address,uint256,uint256,uint256,address,uint256)` | Returns `(amountA, amountB)`. |
| `0x02751cec` | `removeLiquidityETH(address,uint256,uint256,uint256,address,uint256)` | Returns `(amountToken, amountETH)`. |
| `0x38ed1739` | `swapExactTokensForTokens(uint256,uint256,address[],address,uint256)` | Returns `uint256[] amounts`. |
| `0x8803dbee` | `swapTokensForExactTokens(uint256,uint256,address[],address,uint256)` | |
| `0x7ff36ab5` | `swapExactETHForTokens(uint256,address[],address,uint256)` | `payable`. |
| `0x4a25d94a` | `swapTokensForExactETH(uint256,uint256,address[],address,uint256)` | |
| `0x18cbafe5` | `swapExactTokensForETH(uint256,uint256,address[],address,uint256)` | |
| `0xfb3bdb41` | `swapETHForExactTokens(uint256,address[],address,uint256)` | `payable`. |
| `0x5c11d795` | `swapExactTokensForTokensSupportingFeeOnTransferTokens(uint256,uint256,address[],address,uint256)` | FOT-safe. |
| `0xb6f9de95` | `swapExactETHForTokensSupportingFeeOnTransferTokens(uint256,address[],address,uint256)` | `payable`. FOT-safe. |
| `0x791ac947` | `swapExactTokensForETHSupportingFeeOnTransferTokens(uint256,uint256,address[],address,uint256)` | FOT-safe. |

### 2.5 TopDog (farming)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe2bbb158` | `deposit(uint256 pid, uint256 amount)` | Stakes `amount` LP in pool `pid`; harvests pending BONE. Emits `Deposit`. |
| `0x441a3e70` | `withdraw(uint256 pid, uint256 amount)` | Withdraws LP + harvests BONE. Emits `Withdraw`. |
| `0x5312ea8e` | `emergencyWithdraw(uint256 pid)` | Withdraws all LP, forfeits BONE reward. Emits `EmergencyWithdraw`. |
| `0x081e3eda` | `poolLength()` | Returns `uint256 = 52`. |
| `0x1526fe27` | `poolInfo(uint256 pid)` | Returns pool tuple starting with LP token address. |
| `0x74849c53` | `pendingBone(uint256 pid, address user)` | View — accrued unharvested BONE. |

### 2.6 Bury staking — xSHIB, xLEASH, tBONE

All three contracts share the same xSushi-style interface:

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa59f3e0c` | `enter(uint256 amount)` | Stake underlying token; mints receipt token to caller. |
| `0x67dfd4c9` | `leave(uint256 share)` | Burns receipt token; returns underlying proportionally. |

For xSHIB: `enter` stakes SHIB → mints xSHIB; `leave` burns xSHIB → returns SHIB.
For xLEASH: `enter` stakes LEASH → mints xLEASH; `leave` burns xLEASH → returns LEASH.
For tBONE: `enter` stakes BONE → mints tBONE; `leave` burns tBONE → returns BONE.

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` (non-empty) on `https://ethereum-rpc.publicnode.com`.

| Role | Address | Verification |
|------|---------|-------------|
| **BONE** (governance token) | `0x9813037ee2218799597d83D4a5B6F3b6778218d9` | `symbol() = "BONE"`, `totalSupply() ≈ 250 M`, `owner() = TopDog` |
| **SHIB** (Shiba Inu) | `0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE` | `symbol() = "SHIB"`, supply ≈ 999.98 T, 18 dec |
| **LEASH** (Doge Killer) | `0x27C70Cd1946795B66Be9d954418546998b546634` | `symbol() = "LEASH"`, `name() = "DOGE KILLER"`, 18 dec |
| **xSHIB** (BuryShib) | `0xb4A81261b16b92af0B9F7C4a83f1E885132D81e4` | `symbol() = "xSHIB"`, holds SHIB. `shib() = 0x95aD61b…` |
| **xLEASH** (BuryLeash) | `0xa57d319b3cf3ad0e4d19770f71e63cf847263a0b` | `symbol() = "xLEASH"`, holds LEASH (≈ 1.567 × 10¹⁶ LEASH) |
| **tBONE** (staked BONE) | `0xf7A0383750feF5AbACE57cc4C9ff98E3790202b3` | `symbol() = "tBONE"`, holds BONE (≈ 7.08 M BONE) |
| **ShibaSwapFactory** | `0x115934131916C8b277DD010Ee02de363c09d037c` | `allPairsLength() = 1041`, `pairCodeHash() = 0x65d1a3b1…` |
| **ShibaSwapRouter** | `0x03f7724180AA6b939894b5Ca4314783B0b36b329` | `WETH() = 0xC02aaA39…`, `factory() = ShibaSwapFactory` |
| **TopDog** (farming/MasterChef) | `0x94235659cF8b805B2c658f9ea2D6d6DDbb17C8d7` | `bone() = BONE`, `poolLength() = 52`, `boneLocker() = BoneLocker` |
| **BoneLocker** | `0xa404f66b9278c4ab8428225014266b4b239bcdc7` | Holds ≈ 4.08 M BONE; referenced at TopDog storage slot 3 |
| **Fetch** (fee distributor, `feeTo`) | `0x00e82E98a2119Aa175eab206706efE0Df2c7D51D` | Set as `feeTo` in Factory; collects 1/6-of-fee LP cut |
| **WETH9** | `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2` | Canonical wrapped ETH |

### 3.1 Notable pairs

| Pair | Address | Tokens |
|------|---------|--------|
| SHIB / WETH | `0xCF6dAAB95c476106ECa715D48DE4b13287ffDEAa` | `token0 = SHIB`, `token1 = WETH`; `allPairs(0)` |

### 3.2 Sanity-check constants

| Constant | Value |
|----------|-------|
| Pair init code hash | `0x65d1a3b1e46c6e4f1be1ad5f99ef14dc488ae0549dc97db9b30afe2241ce1c7a` — **different from UniV2** (`0x96e8ac42…`) |
| LP token symbol | `"SSLP"` (not `"UNI-V2"`) — confirmed via `allPairs(0).symbol()` |
| BONE.owner | `0x94235659…` (TopDog) — confirmed via `BONE.owner()` |
| TopDog.bone | `0x9813037e…` (BONE) — confirmed via `TopDog.bone()` |
| Router.WETH | `0xC02aaA39…` — confirmed via `Router.WETH()` |

---

## 4. Cross-chain deployment status

ShibaSwap is **Ethereum-only**. `eth_getCode` returns `0x` for all ShibaSwap contract addresses on every other chain:

| Chain | Chain ID | ShibaSwap deployed? |
|-------|----------|---------------------|
| Ethereum | 1 | **Yes** — all contracts above |
| Base | 8453 | No — `0x` |
| BNB Smart Chain | 56 | No — `0x` |
| Avalanche C-Chain | 43114 | No — `0x` |
| Arbitrum One | 42161 | No — `0x` |
| Optimism | 10 | No — `0x` |
| Polygon PoS | 137 | No — `0x` |

---

## 5. Quick-copy bytea block

```
-- ShibaSwap Factory
\x115934131916c8b277dd010ee02de363c09d037c
-- ShibaSwap Router
\x03f7724180aa6b939894b5ca4314783b0b36b329
-- TopDog (farming/MasterChef)
\x94235659cf8b805b2c658f9ea2d6d6ddbb17c8d7
-- BoneLocker
\xa404f66b9278c4ab8428225014266b4b239bcdc7
-- Fetch (fee distributor)
\x00e82e98a2119aa175eab206706efe0df2c7d51d
-- BONE token
\x9813037ee2218799597d83d4a5b6f3b6778218d9
-- SHIB token
\x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce
-- LEASH token
\x27c70cd1946795b66be9d954418546998b546634
-- xSHIB (BuryShib)
\xb4a81261b16b92af0b9f7c4a83f1e885132d81e4
-- xLEASH (BuryLeash)
\xa57d319b3cf3ad0e4d19770f71e63cf847263a0b
-- tBONE (staked BONE)
\xf7a0383750fef5abace57cc4c9ff98e3790202b3
-- SHIB/WETH pair (allPairs[0])
\xcf6daab95c476106eca715d48de4b13287ffdeaa

-- topic0: PairCreated (Factory)
\x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9
-- topic0: Mint (Pair)
\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f
-- topic0: Burn (Pair)
\xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496
-- topic0: Swap (Pair)
\xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822
-- topic0: Sync (Pair)
\x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1
-- topic0: Transfer (ERC-20)
\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef
-- topic0: Approval (ERC-20)
\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925
-- topic0: Deposit (TopDog)
\x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15
-- topic0: Withdraw (TopDog)
\xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568
-- topic0: EmergencyWithdraw (TopDog)
\xbb757047c2b5f3974fe26b7c10f732e7bce710b0952a71082702781e62ae0595
-- topic0: LockingPeriod (BoneLocker)
\x2d8847c3ea1c4b6f02609bff2ac1776bc3663d31a747102d5722bdffcc2e3721
```
