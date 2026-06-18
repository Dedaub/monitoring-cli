# Biswap — Compressed Reference (BNB Smart Chain; ETH/Base/Arb token-only)

**Status:** Addresses, topic0s, selectors on-chain verified via `cast` + publicnode RPCs (2026-06).
**Scope:** Biswap complete protocol — V2 AMM, V3 AMM (iZiSwap-style), SmartRouter, MasterChef farming, BSW token, bridged BSW OFT.
**Key fact:** Biswap V2 is a Uniswap V2 fork → **AMM topic0s and selectors are IDENTICAL to Uniswap V2** (`uniswap/v2.md`). The DEX (AMM, liquidity, farming) lives **exclusively on BNB Smart Chain (56)**. ETH (1), Base (8453), and Arbitrum (42161) carry only the bridged BSW token (LayerZero OFT EIP-1167 minimal proxy). Avalanche, Optimism, and Polygon have **no Biswap contracts** at all (codesize 0 confirmed).

**Biswap discriminators vs other UniV2 forks:**
- Per-pair configurable `swapFee` (default 2‰ = 0.2%) and `devFee` (3‰ by default on WBNB/BSW pair) stored on the pair — confirmed live: `swapFee()→2`, `devFee()→3`.
- No dedicated on-chain `SwapFee` event emitted by the pair contract — fee accounting is internal. The `Swap` topic0 is identical to UniV2. Disambiguate Biswap pairs solely by **factory/pair address**.
- V3 uses an iZiSwap-derived AMM (not Uniswap V3 Concentrated Liquidity) with `uint16` fees and a `BiswapFactoryV3`.
- SmartRouter aggregates V2 + V3 pools.

---

## Topics (chain-agnostic)

### V2 AMM — IDENTICAL to Uniswap V2
```
0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9  PairCreated(address,address,address,uint256)              [BiswapFactory]
0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  Swap(address,uint256,uint256,uint256,uint256,address)     [BiswapPair]
0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f  Mint(address,uint256,uint256)                            [BiswapPair]
0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496  Burn(address,uint256,uint256,address)                    [BiswapPair]
0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1  Sync(uint112,uint112)                                    [BiswapPair]
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  Transfer(address,address,uint256)                        [BiswapPair LP / BSW ERC-20]
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  Approval(address,address,uint256)                        [BiswapPair LP / BSW ERC-20]
```

### V3 AMM (BiswapV3 / iZiSwap-derived) — BNB only
```
0xe857b53ada03b8d88fd7546e77c34d3b68996e6ce330f0edee6e813b7daea099  NewPool(address,address,uint16,uint24,address)            [BiswapFactoryV3]
0x02056c71782e4e19f67281cae3c0b15b41b8ed2a84ff14b089102dee5fc05168  NewFeeEnabled(uint16,uint24)                              [BiswapFactoryV3]
0x68d951b90a07a8c0c7c7d544a3cb052236f41ca892c19f04ccc8970c58798a4c  FeeDeltaChanged(uint16,uint16,uint16)                     [BiswapFactoryV3]
```
V3 pool-level events (iZiSwap pattern):
```
0xf6aab4825b1e549235f75c4fd96487a1d7f77e293b9535a5aca741c7714708e3  Swap(address,address,int256,int256,uint160,uint128,int24,uint16,address)  [V3 Pool]
0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde  Mint(address,address,int24,int24,uint128,uint256,uint256)                 [V3 Pool]
0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c  Burn(address,int24,int24,uint128,uint256,uint256)                         [V3 Pool]
0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0  Collect(address,address,int24,int24,uint128,uint128)                      [V3 Pool]
0x98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95  Initialize(uint160,int24)                                                 [V3 Pool]
```

### MasterChef (BSW farming) — BNB only
```
0x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15  Deposit(address,uint256,uint256)           [MasterChef — collides w/ PancakeSwap/Sushi MasterChef]
0xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568  Withdraw(address,uint256,uint256)          [** collides w/ Curve/Balancer/Sushi Withdraw **]
0xbb757047c2b5f3974fe26b7c10f732e7bce710b0952a71082702781e62ae0595  EmergencyWithdraw(address,uint256,uint256)
```

### SwapFeeReward — BNB only
```
0x4f2387711860ea50b6a0e4e7e3a1aadf0685d1c9261c203c2e6a48b2004fd977  Rewarded(address,address,address,uint256,uint256)  [SwapFeeReward — account,input,output,amount,qty]
0x884edad9ce6fa2440d8a54cc123490eb96d2768479d49ff9c7366125a9424364  Withdraw(address,uint256)                          [SwapFeeReward claim]
```

### BSW OFT (LayerZero bridged token — ETH, Base, Arb)
```
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef  Transfer(address,address,uint256)                [standard ERC-20]
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925  Approval(address,address,uint256)               [standard ERC-20]
```

### Timelock — BNB only
```
0x2fffc091a501fd91bfbff27141450d3acb40fb8e6d8382b243ec7a812a3aaf87  CancelTransaction(bytes32,address,uint256,string,bytes,uint256)
0xa560e3198060a2f10670c1ec5b403077ea6ae93ca8de1c32b451dc1a943cd6e7  ExecuteTransaction(bytes32,address,uint256,string,bytes,uint256)
0x76e2796dc3a81d57b0e8504b647febcbeeb5f4af818e164f11eef8131a6a763f  QueueTransaction(bytes32,address,uint256,string,bytes,uint256)
0x71614071b88dee5e0b2ae578a9dd7b2ebbe9ae832ba419dc0242cd065a290b6c  NewAdmin(address)
0x69d78e38a01985fbb1462961809b4b2d65531bc93b2b94037f3334b82ca4a756  NewPendingAdmin(address)
0x948b1f6a42ee138b7e34058ba85a37f716d55ff25ff05a763f15bed6a04c8d2c  NewDelay(uint256)
```

---

## Function selectors

### BiswapFactory (V2)
```
0x574f2ba3  allPairsLength() → uint256
0x1e3dd18b  allPairs(uint256) → address
0xe6a43905  getPair(address,address) → address
0xc9c65396  createPair(address,address) → address
0xef0bc993  setDevFee(address,uint8)          [feeToSetter only; sets devFee on pair]
0x9e68ceb8  setSwapFee(address,uint32)        [feeToSetter only; sets swapFee on pair]
```

### BiswapRouter02 (V2 Router)
```
0x38ed1739  swapExactTokensForTokens(uint256,uint256,address[],address,uint256) → uint256[]
0x8803dbee  swapTokensForExactTokens(uint256,uint256,address[],address,uint256) → uint256[]
0x7ff36ab5  swapExactETHForTokens(uint256,address[],address,uint256) → uint256[]
0x18cbafe5  swapExactTokensForETH(uint256,uint256,address[],address,uint256) → uint256[]
0xe8e33700  addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)
0xf305d719  addLiquidityETH(address,uint256,uint256,uint256,address,uint256)
0xbaa2abde  removeLiquidity(address,address,uint256,uint256,uint256,address,uint256)
0x02751cec  removeLiquidityETH(address,uint256,uint256,uint256,address,uint256)
0x5c11d795  swapExactTokensForTokensSupportingFeeOnTransferTokens(uint256,uint256,address[],address,uint256)
0xb6f9de95  swapExactETHForTokensSupportingFeeOnTransferTokens(uint256,address[],address,uint256)
0x791ac947  swapExactTokensForETHSupportingFeeOnTransferTokens(uint256,uint256,address[],address,uint256)
```

### SmartRouter (V2+V3 aggregator)
```
0x68e0d4e1  factoryV2() → address             [returns 0x858E3312...]
0x1d5f45f5  factoryV3() → address             [returns 0x7C3d5360...]
0x8dd95002  WBNB() → address
0xa3ddb30b  swapFeeReward() → address
0x8d1f83e6  getAmountsOut(uint128,address[],uint16[]) → uint256[]
0x2f61c6c8  swapInfoMultiple(address,(uint256,bytes)[])  [multi-hop V2+V3 swap — confirmed in bytecode]
```

### BiswapFactoryV3
```
0x658afc97  newPool(address,address,uint16,uint160) → address
0xe0744068  enableFeeAmount(uint16,int24)
0xd8cd50e2  chargeReceiver() → address
0x59950c86  defaultFeeChargePercent() → uint8
0x915fd94c  setFarmsContract(address)
0x126bf9d3  setDiscount(address,uint8)
```

### MasterChef
```
0xe2bbb158  deposit(uint256,uint256)
0x441a3e70  withdraw(uint256,uint256)
0x5312ea8e  emergencyWithdraw(uint256)
0x081e3eda  poolLength() → uint256
0x295315bf  pendingBSW(uint256,address) → uint256
0x93f1a40b  userInfo(uint256,address) → (uint256,uint256)
0x1526fe27  poolInfo(uint256)
0x51eb05a6  updatePool(uint256)
0x630b5ba1  massUpdatePools()
```

### BSW OFT (LayerZero — ETH/Base/Arb proxy)
```
0x05cf3089  sendFrom(address,uint16,bytes,uint256,(address,address,bytes))
0x2a205e3d  estimateSendFee(uint16,bytes,uint256,bool,bytes)
```

---

## Addresses

> ✓ = on-chain verified this run.

### BNB Smart Chain (56) — DEX home chain
```
0x965F527D9159dCe6288a2219DB51fc6Eef120dD1  BSW token            (symbol "BSW" ✓, decimals 18, totalSupply ~700M ✓)
0x858E3312ed3A876947EA49d572A7C42DE08af7EE  BiswapFactory V2     (allPairsLength 3451 ✓, 15785B ✓)
0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8  BiswapRouter02       (24073B ✓)
0x0eB6949e725A295Ecb3BEacFc3766610BC970BEF  SmartRouter V2+V3    (16527B ✓; factoryV2→0x858E33 ✓, factoryV3→0x7C3d53 ✓)
0x7C3d53606f9c03e7f54abdDFFc3868E1C5466863  BiswapFactoryV3      (5308B ✓; owner→Timelock ✓; deployed 2023-06-27)
0xDbc1A13490deeF9c3C12b44FE77b503c1B061739  MasterChef           (12270B ✓; poolLength 139 ✓; owner→Timelock ✓)
0xf5D6fed0f4735Ff2036cE4be535bD32e77dAE9fe  Timelock             (7034B ✓; is MasterChef owner and V3 factory owner)
```

Notable pairs (BNB):
```
0xDA8ceb724A06819c0A5cDb4304ea0cB27F8304cF  USDT/BUSD pair  (pair #0; swapFee=1, devFee=3 ✓)
0x46492B26639Df0cda9b2769429845cb991591E0A  WBNB/BSW pair   (swapFee=2 ✓, devFee=3 ✓)
```

### Ethereum (1) — BSW token only
```
0x66e09ec17629574A0CC8abc480b0c2572fcd6985  BSW OFT (LayerZero EIP-1167 proxy, symbol "BSW" ✓, name "Biswap" ✓, decimals 18 ✓; impl→0x7f9f70da4af54671a6abac58e705b5634cac8819 7240B)
```

### Base (8453) — BSW token only
```
0x66e09ec17629574A0CC8abc480b0c2572fcd6985  BSW OFT (same address, symbol "BSW" ✓)
```

### Arbitrum (42161) — BSW token only
```
0x66e09ec17629574A0CC8abc480b0c2572fcd6985  BSW OFT (same address, symbol "BSW" ✓)
```

### Avalanche (43114), Optimism (10), Polygon (137)
```
No Biswap contracts — codesize 0 confirmed for BiswapFactory and BSW OFT address on all three chains.
```

---

## Proxies
- **BiswapFactory V2, BiswapRouter02, BiswapFactoryV3, MasterChef:** EIP-1967 implementation slot = `0x000…0` (confirmed) — all are **immutable** (no proxy).
- **SmartRouter:** EIP-1967 slot = `0x000…0` — immutable.
- **BSW OFT (ETH/Base/Arb):** EIP-1167 minimal proxy (`0x363d3d37…5af4…5bf3`). Implementation on Ethereum: `0x7f9f70da4af54671a6abac58e705b5634cac8819` (7240B). The proxy delegates all calls (including `Transfer`, `Approval`) to the implementation.
- **BSW token (BNB):** Not a proxy — direct ERC-20.

---

## Quick-copy bytea
```
-- BNB Chain: V2 AMM events (identical to UniV2)
'\x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9'  -- PairCreated
'\xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'  -- Swap (V2)
'\x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f'  -- Mint
'\xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496'  -- Burn
'\x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1'  -- Sync
'\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'  -- Transfer
-- V3 Factory
'\xe857b53ada03b8d88fd7546e77c34d3b68996e6ce330f0edee6e813b7daea099'  -- NewPool (V3)
-- MasterChef
'\x90890809c654f11d6e72a28fa60149770a0d11ec6c92319d6ceb2bb0a4ea1a15'  -- Deposit
'\xf279e6a1f5e320cca91135676d9cb6e44ca8a08c0b88342bcdb1144f6511b568'  -- Withdraw
'\xbb757047c2b5f3974fe26b7c10f732e7bce710b0952a71082702781e62ae0595'  -- EmergencyWithdraw
-- SwapFeeReward
'\x4f2387711860ea50b6a0e4e7e3a1aadf0685d1c9261c203c2e6a48b2004fd977'  -- Rewarded
```

---

## Detection invariants & gotchas
1. **No dedicated SwapFee event.** The `Swap` topic0 on BiswapPair is identical to UniV2. Fee configuration (`swapFee`, `devFee`) is stored as state variables on each pair but is NOT emitted per-swap. Disambiguate Biswap pairs from other UniV2 forks solely by factory/pair address.
2. **Per-pair configurable fees.** `swapFee` and `devFee` are `uint32`; the factory owner calls `setSwapFee` / `setDevFee` per pair. Default observed: swapFee=2, devFee=3 (on WBNB/BSW; USDT/BUSD: swapFee=1, devFee=3). Fee units are per-mille (‰) — i.e., fee = `amount * swapFee / 1000`.
3. **V2 topic0s collide with all Uniswap V2 forks** (Uniswap, Sushi, PancakeSwap, etc.). Use contract addresses as the discriminator.
4. **MasterChef `Withdraw(address,uint256,uint256)` (`0xf279e6a1…`)** collides with Curve/Balancer/Sushi Withdraw — disambiguate by contract address.
5. **DEX is BNB-only.** No V2 or V3 factory exists on ETH/Base/Arb/Avax/Optimism/Polygon — don't mistake the bridged BSW OFT (`0x66e09ec1…`, same address on ETH/Base/Arb) for a DEX deployment.
6. **V3 uses `uint16` fees** (iZiSwap lineage), not `uint24` (Uniswap V3). `NewPool` emits `fee` as `uint16` and `pointDelta` as `uint24`.
7. **SmartRouter routes across both V2 and V3** — its `factoryV2` and `factoryV3` are both confirmed live on-chain.
8. **Timelock is admin** of MasterChef and BiswapFactoryV3 (owner = `0xf5D6fed0…` on both ✓).

---

## Verification & sources
- Addresses: `cast call` / `cast codesize` via publicnode BSC/ETH/Base/Arb/Avax/Optimism/Polygon RPCs.
- BSW symbol ✓ on BNB (`"BSW"`, 18 dec, ~700M totalSupply) and ETH/Base/Arb OFT (`"BSW"`, `"Biswap"`).
- BiswapFactory `allPairsLength()→3451 ✓`; SmartRouter `factoryV2`/`factoryV3` cross-checked ✓.
- MasterChef `poolLength()→139 ✓`; BSWPerBlock `1e18 ✓`; owner→Timelock ✓.
- EIP-1967 slots: all zero (immutable contracts) ✓.
- BSW OFT EIP-1167 bytecode prefix confirmed: `363d3d373d3d3d363d73…5af43d82803e903d91602b57fd5bf3`; impl `0x7f9f70da…` 7240B ✓.
- topic0s: `cast keccak` (all signatures); V2 cross-matched against `uniswap/v2.md`.
- Source: [`biswap-org/core`](https://github.com/biswap-org/core), [`biswap-org/swap-fee-reward`](https://github.com/biswap-org/swap-fee-reward), [`biswap-org/periphery`](https://github.com/biswap-org/periphery), [docs.biswap.org](https://docs.biswap.org), BSCScan verified ABIs.
