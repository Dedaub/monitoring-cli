# DOOAR (DooarSwap) — Compressed Deployment Reference

**Solana out of scope.** DooarSwap runs a separate Solana AMM (Program ID `Dooar9JkhdZ7J3LHN3A7YCuoGRUggXhQaG4kijfLGU2j`); this file covers **EVM only**.

**Status:** Addresses on-chain verified via `cast` + publicnode RPCs (2026-06). topic0s via `cast keccak`; selectors via `cast sig`.
**Scope:** DooarSwap (the STEPN-ecosystem AMM, built by Find Satoshi Lab) — a minimal Uniswap V2 fork on **Ethereum (1)** and **BNB Smart Chain (56)**. All other 5 EVM target chains have no deployment (confirmed `eth_getCode` = `0x`).
**Key fact:** DooarSwap is a Uniswap V2 fork → **topic0s and 4-byte selectors are IDENTICAL to Uniswap V2**; the main discriminators are the factory addresses, LP token symbol `"DOOAR"` and LP token name `"DooarSwap V2"` (Uniswap V2 pairs use symbol `"UNI-V2"` / name `"Uniswap V2"`). Very small DEX — 9 pairs on Ethereum, 3 pairs on BSC, all STEPN ecosystem tokens (GST, GMT) plus WETH/WBNB and USDC.

---

## Topics (chain-agnostic) — `topic0 -> Event(types)`

### AMM (Uniswap V2 fork — topic0 IDENTICAL to Uniswap V2)
```
0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9 -> PairCreated(address,address,address,uint256)           [Factory]
0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822 -> Swap(address,uint256,uint256,uint256,uint256,address)   [Pair]
0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f -> Mint(address,uint256,uint256)                          [Pair]
0xd3986fdc78865c06fb072387efddb45772a87fe2105e598db99f085be3d05b84 -> Burn(address,address,uint256,uint256,address)          [Pair]
0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1 -> Sync(uint112,uint112)                                  [Pair]
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef -> Transfer(address,address,uint256)                      [Pair LP / ERC-20]
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925 -> Approval(address,address,uint256)
```

---

## Function signatures (chain-agnostic) — `selector -> name(types)`

> Router and factory selectors are identical to Uniswap V2. Key ones:
```
0x38ed1739 -> swapExactTokensForTokens(uint256,uint256,address[],address,uint256) -> uint256[]   [Router]
0x18cbafe5 -> swapExactTokensForETH(uint256,uint256,address[],address,uint256) -> uint256[]       [Router]
0x7ff36ab5 -> swapExactETHForTokens(uint256,address[],address,uint256) -> uint256[]               [Router]
0xe8e33700 -> addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)       [Router]
0xf305d719 -> addLiquidityETH(address,uint256,uint256,uint256,address,uint256)                    [Router]
0xe6a43905 -> getPair(address,address) -> address                                                  [Factory]
0x574f2ba3 -> allPairsLength() -> uint256                                                          [Factory]
0xc9c65396 -> createPair(address,address) -> address                                               [Factory]
0x0dfe1681 -> token0() -> address                                                                   [Pair]
0xd21220a7 -> token1() -> address                                                                   [Pair]
0x0902f1ac -> getReserves() -> (uint112,uint112,uint32)                                            [Pair]
```

---

## Addresses (network-specific)

> **Shared across Ethereum and BSC:** the same deployer (`0x0F9e90e32F65C482C3786De6F62dd90e2DF5f18C`) deployed identical contract addresses on both chains — factory `0x1e895bFe59E3A5103e8B7dA3897d1F2391476f3c` and router `0x53e0e51b5ed9202110d7ecd637a4581db8b9879f` appear at the same address on both chains. EIP-1967 proxy slots are zero on both — contracts are **immutable**. ✓ = on-chain verified this run.

### Ethereum (1)
```
0x1e895bFe59E3A5103e8B7dA3897d1F2391476f3c -> DooarSwapV2Factory  (allPairsLength=9 ✓; feeTo=0x91B24d9DEb67d12591C830df19Da4285235Afa5C ✓)
0x53e0e51b5ed9202110d7ecd637a4581db8b9879f -> DooarSwapV2Router02 (factory()→0x1e895bFe…476f3c ✓; WETH()→0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 ✓)
```

Ethereum pairs (all LP: symbol="DOOAR", name="DooarSwap V2"):
```
0x9c2DC3D5ffcEcF61312C5F4C00660695B32fB3D1 -> pair[0] USDC/WETH
0xAeAca8C32039A466FB32Bde6F566130A1f49D21e -> pair[1] USDC/GMT
0x770cBFfF3c47134a878D513921AC59a1fD24e514 -> pair[2] GST/USDC
0x09D614845450c1002D04213b68c386A747D0A65A -> pair[3] GST/WETH
0x7D05aa560aB9C56A2961e78f1D848315192cD04f -> pair[4] GST/USDC  (GST = 0x7f025b904A1c6C81E3411CefeE691Dd3132F6697)
0xda976b2aE2e1E14A4194b5AD238F6b8958697228 -> pair[5] GST/GMT
0x67D4A7fc986E1B41bd077F9Cc22758B02Df261D8 -> pair[6] GST/APE
0x1d24c75C0Bd7021A04b2264fDc0004a3A398E593 -> pair[7] GST2/GST  (GST2=0x0000000000b3F879cb30FE243b4Dfee438691c04 / Gastoken.io)
0x5840103Ec5d738A150dde0d6bD6621772Fd7a526 -> pair[8] USDC/GST2
```

### BNB Smart Chain (56)
```
0x1e895bFe59E3A5103e8B7dA3897d1F2391476f3c -> DooarSwapV2Factory  (allPairsLength=3 ✓; feeTo=0x91B24d9DEb67d12591C830df19Da4285235Afa5C ✓; feeToSetter=0xCB25adc0a0e9c604816B4a402dDc75ad6d2fED23 ✓)
0x53e0e51b5ed9202110d7ecd637a4581db8b9879f -> DooarSwapV2Router02 (factory()→0x1e895bFe…476f3c ✓; WETH()→0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c=WBNB ✓)
```

BSC pairs (all LP: symbol="DOOAR", name="DooarSwap V2"):
```
0x5f5d385397095AaED4daffe336F9815AC598DFf5 -> pair[0] USDC/WBNB  (USDC=0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d / WBNB=0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c)
0xba5Ae86960FE468fF02d83022c0079670BD8F6a9 -> pair[1] GST/USDC   (GST=0x4a2c860cEC6471b9F5F5a336eB4F38bb21683c98)
0x17DB7a395BCC1eC828e732A014dD2A7C43eD30F0 -> pair[2] GMT/USDC   (GMT=0x3019BF2a2eF8040C242C9a4c5c4BD4C81678b2A1)
```

### Base (8453), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137)
```
0x0  -> not deployed (eth_getCode = 0x on all five chains ✓)
```

---

## LP Token Branding (key discriminator)

DooarSwap pair contracts are byte-for-byte Uniswap V2 pair bytecode **except** for the embedded LP token metadata:

| Field    | DooarSwap  | Uniswap V2  |
|----------|------------|-------------|
| `symbol()` | `"DOOAR"` | `"UNI-V2"` |
| `name()`   | `"DooarSwap V2"` | `"Uniswap V2"` |

This is the only on-chain discriminator between a DooarSwap LP token and a Uniswap V2 LP token. Verified on BSC pair[0] `0x5f5d…DFf5` and all three BSC pairs ✓; confirmed on Ethereum pair[0] `0x9c2D…3D1` ✓.

---

## Proxies

**No proxies.** Factory, Router, and all Pair contracts are immutable (EIP-1967 impl slot = `0x00…00` on factory and router, both chains ✓). Pairs are CREATE2-deployed by the factory. The `pairCodeHash()` view reverts (not exposed), so the init code hash is not publicly readable on-chain; it must be derived from the verified pair bytecode on BSCScan/Etherscan if needed for off-chain pair address derivation.

---

## Verification & sources

- topic0s: `cast keccak` this session. UniV2-identical — cross-checked against `uniswap/v2.md`.
- Addresses: BSCScan (factory labelled "DooarSwapV2Factory", router labelled "DOOAR: Router02"), Etherscan (factory labelled "STEPN: DOOAR Factory", router labelled "STEPN: DOOAR Router"), DefiLlama adapter (`DefiLlama-Adapters/projects/dooar/index.js` — uses `getUniTVL` with BSC factory, confirms UniV2-style). On-chain verified via `cast` + publicnode this session: factory `allPairsLength()` (ETH=9, BSC=3 ✓), router `factory()` and `WETH()` (both chains ✓), LP `name()`/`symbol()` (all 3 BSC pairs + ETH pair[0] ✓), EIP-1967 proxy slots zero on factory+router (both chains ✓), `eth_getCode` = `0x` on all 5 non-deployed chains ✓.
- Same deployer (`0x0F9e90e32F65C482C3786De6F62dd90e2DF5f18C`) on both chains; same contract addresses on both chains.
- Sources: [BSCScan factory](https://bscscan.com/address/0x1e895bfe59e3a5103e8b7da3897d1f2391476f3c), [BSCScan router](https://bscscan.com/address/0x53e0e51b5ed9202110d7ecd637a4581db8b9879f), [DefiLlama adapter](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/dooar/index.js).
