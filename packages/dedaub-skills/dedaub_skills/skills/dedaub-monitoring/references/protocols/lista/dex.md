# Lista DEX (ListaV3 / ListaV2) — Topics, Selectors, Addresses (BNB Chain, Ethereum)

**Status:** verified against live RPC on BNB Chain (56) and Ethereum (1) and the canonical `lista-dao/lista-v3` and `lista-dao/lista-v2` repos on 2026-10-30.
**Scope:** Lista's own AMMs. **ListaV3** is a concentrated-liquidity DEX that is a byte-level Uniswap V3 fork (factory, pools, NonfungiblePositionManager, SwapRouter, QuoterV2). **ListaV2** is a Uniswap V2 fork (factory, router). Topics and selectors are chain-agnostic and **identical to Uniswap V3/V2**. Addresses are network-specific. The Smart Lending StableSwap pools are in [lending.md](lending.md) §1.6.

Pools and the factory are immutable. The factory `owner()` is a `ListaV3FactoryOwner` proxy. Only the NonfungiblePositionManager is upgradeable (OZ Transparent proxy). Pools are low-fee stable and LST pairs that serve Moolah liquidations and the lisUSD peg.

ListaV3 exists on **BNB Chain and Ethereum**. ListaV2 exists on BNB Chain only. Neither is on Base, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain or Arc (factory addresses return `0x`).

---

## 1. Topics (chain-agnostic) — same as Uniswap V3 / V2

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118` | `PoolCreated(address indexed token0, address indexed token1, uint24 indexed fee, int24 tickSpacing, address pool)` | ListaV3Factory |
| `0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67` | `Swap(address indexed sender, address indexed recipient, int256 amount0, int256 amount1, uint160 sqrtPriceX96, uint128 liquidity, int24 tick)` | ListaV3Pool |
| `0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde` | `Mint(address sender, address indexed owner, int24 indexed tickLower, int24 indexed tickUpper, uint128 amount, uint256 amount0, uint256 amount1)` | ListaV3Pool |
| `0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c` | `Burn(address indexed owner, int24 indexed tickLower, int24 indexed tickUpper, uint128 amount, uint256 amount0, uint256 amount1)` | ListaV3Pool |
| `0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0` | `Collect(address indexed owner, address recipient, int24 indexed tickLower, int24 indexed tickUpper, uint128 amount0, uint128 amount1)` | ListaV3Pool |
| `0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633` | `Flash(address indexed sender, address indexed recipient, uint256 amount0, uint256 amount1, uint256 paid0, uint256 paid1)` | ListaV3Pool |
| `0x98636036cb66a9c19a37435efc1e90142190214e8abeb821bdba3f2990dd4c95` | `Initialize(uint160 sqrtPriceX96, int24 tick)` | ListaV3Pool |
| `0x3067048beee31b25b2f1681f88dac838c8bba36af25bfb2b7cf7473a5847e35f` | `IncreaseLiquidity(uint256 indexed tokenId, uint128 liquidity, uint256 amount0, uint256 amount1)` | NonfungiblePositionManager |
| `0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4` | `DecreaseLiquidity(uint256 indexed tokenId, uint128 liquidity, uint256 amount0, uint256 amount1)` | NonfungiblePositionManager |
| `0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01` | `Collect(uint256 indexed tokenId, address recipient, uint256 amount0, uint256 amount1)` | NonfungiblePositionManager |
| `0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9` | `PairCreated(address indexed token0, address indexed token1, address pair, uint256)` | ListaV2Factory |
| `0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822` | `Swap(address indexed sender, uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out, address indexed to)` | ListaV2 pair |
| `0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1` | `Sync(uint112 reserve0, uint112 reserve1)` | ListaV2 pair |
| `0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f` / `0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496` | `Mint(address indexed sender, uint256, uint256)` / `Burn(address indexed sender, uint256, uint256, address indexed to)` | ListaV2 pair |

## 2. Function signatures (chain-agnostic) — same as Uniswap V3 / V2

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x128acb08` | `swap(address,bool,int256,uint160,bytes)` | ListaV3Pool. |
| `0xa1671295` | `createPool(address,address,uint24)` | ListaV3Factory. |
| `0x414bf389` | `exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))` | SwapRouter (V1 router struct with `deadline`). |
| `0x88316456` | `mint((address,address,uint24,int24,int24,uint256,uint256,uint256,uint256,address,uint256))` | NonfungiblePositionManager. |
| `0x022c0d9f` | `swap(uint256,uint256,address,bytes)` | ListaV2 pair. |

See [../uniswap/v3.md](../uniswap/v3.md) and [../uniswap/v2.md](../uniswap/v2.md) for the full selector sets. They apply unchanged.

## 3. Addresses

All verified via `eth_getCode` on 2026-10-30.

| Role | BNB Chain (56) | Ethereum (1) |
|------|----------------|--------------|
| **ListaV3Factory** | `0xcb010ed373523942706F730b89792aA1C1597b20` (23945 B) | `0x956920F97690Bdd76a6a10C7ba931DEC14f61169` (23945 B) |
| ListaV3FactoryOwner | `0x2BBa5BdED4DD4A597f7BAdC256005C9Aa662Df06` (proxy) | `0x08Bd226913b95f405A27079A0B3314AFa6E376aA` (proxy) |
| NonfungiblePositionManager | `0x31677537685EBDF1B695eDa46eC385845395f5dD` (TP, ProxyAdmin `0x97458aE48Fc8362077c30930bc6C004B46a9312f`) | `0xfd0524a86976DE0e8A51f892F3f6283e127d8980` (TP, ProxyAdmin `0xcF8c35Ffb8D388201C604dfC88091140eD81dbca`) |
| SwapRouter | `0xc43D58722f29390e683c0721285A6c11B8aCD4DE` | `0x667939BEf1812A58D65db51011A26332628b63e5` |
| QuoterV2 | `0x6B61a2C67c45B40d754e4e7c1c565590685C03E2` | `0xE043af034c0c920994f8e3eE9aFa1173Fe8403DB` |
| ListaV2Factory | `0x28F5E6C71C7541b1C6523351AE331CcAfC443626` | — |
| ListaV2Router02 | `0x3CcbB50C93ffCdA64e58Cc9E299791Fd85A41941` | — |

**BNB V3 pools:** WBNB/slisBNB 1 bp `0xd50154428912A887d9a405Bb515d2Ef11307228d` · slisBNB/WBNB 5 bp `0x9f0E53D3aC0dc7aEaAF36866cD1A9EEbE16Bf4a1` · USDT/USDC `0x46eE2C5F2b9De7C6e08Ffe3Bde8Dd88A46D6f568` · lisUSD/USDT 1 bp `0x8b94363fbBbBcdae25832807BE39e8e2c60a6e15` · USDT/USDC 0.5 bp `0x3B6ED4E0CA494002398169b7A5D1a83323541526` · USDT/U `0xd2BD33Be34d8Eb1123AAeA23CA0aFD68bcC14Da1` · USDT/USD1 `0x6a7e6Dd58BB719819f285aEab8EE9079D0948f2f` · lisUSD/USDC `0xb20c03c6422408398f7b9E5C613f324ab6c601bE`.
**Ethereum V3 pools:** USDT/USDC `0xdCF7612fcA2093a607e797238f47f804eCa25728` · USDS/USDT `0xa9Fb8118Ad28c90A142F45aA0DE231320D5817e8` · USDT/USDe `0x5B326A9C17Fe5502339EdEdd7A55Cc7bf29fd217`.
Discover new pools with `PoolCreated` on the factory.

## 4. Proxies

| Contract | Pattern | Upgrade auth |
|----------|---------|--------------|
| ListaV3Factory, pools, SwapRouter, QuoterV2, ListaV2Factory, Router02 | immutable (impl slot `0x0`) | — |
| NonfungiblePositionManager | OZ v4 TransparentUpgradeableProxy (2048 B) | BNB ProxyAdmin owner = TimelockController `0x07d274…5253` |
| ListaV3FactoryOwner (BNB, ETH) | ERC-1967 proxy (135 B) | holds factory `owner()` |

## 5. Detection invariants & gotchas

1. **Topic0 collision with Uniswap V3/V2 and every fork.** `Swap`/`Mint`/`Burn`/`PoolCreated`/`PairCreated` match Uniswap, PancakeSwap V2 and many others. Only the emitter (a pool created by the ListaV3/ListaV2 factory) identifies Lista.
2. **Not a PancakeSwap V3 fork.** The pool `Swap` is the 7-field Uniswap topic `0xc42079f9…`, not the PancakeSwap V3 9-field topic `0x19b47279…`.
3. **Factory ownership.** `ListaV3Factory.owner()` is the `ListaV3FactoryOwner` proxy, not an EOA. Fee-tier changes (`FeeAmountEnabled`) go through it.

## 6. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_V3_POOL_CREATED             = '\x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118'
TOPIC_V3_SWAP                     = '\xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
TOPIC_V3_MINT                     = '\x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde'
TOPIC_V3_BURN                     = '\x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c'
TOPIC_V2_PAIR_CREATED             = '\x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9'
TOPIC_V2_SWAP                     = '\xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'
-- ===== Addresses (network-specific) =====
BSC_LISTA_V3_FACTORY              = '\xcb010ed373523942706f730b89792aa1c1597b20'
BSC_LISTA_V3_NPM                  = '\x31677537685ebdf1b695eda46ec385845395f5dd'
BSC_LISTA_V3_ROUTER               = '\xc43d58722f29390e683c0721285a6c11b8acd4de'
BSC_LISTA_V2_FACTORY              = '\x28f5e6c71c7541b1c6523351ae331ccafc443626'
BSC_POOL_WBNB_SLISBNB_1BP         = '\xd50154428912a887d9a405bb515d2ef11307228d'
BSC_POOL_LISUSD_USDT_1BP          = '\x8b94363fbbbbcdae25832807be39e8e2c60a6e15'
ETH_LISTA_V3_FACTORY              = '\x956920f97690bdd76a6a10c7ba931dec14f61169'
ETH_LISTA_V3_NPM                  = '\xfd0524a86976de0e8a51f892f3f6283e127d8980'
ETH_LISTA_V3_ROUTER               = '\x667939bef1812a58d65db51011a26332628b63e5'
```

## 7. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0:** recomputed locally as `keccak256(signature)`. Each V3 topic was found as a `PUSH32` constant in the live BNB pool bytecode (WBNB/slisBNB pool, 21642 B) and the factory. The V2 topics were found in the ListaV2Factory bytecode (it embeds the pair creation code). NPM topics were found in the NPM implementation `0xda274d99…`. Live `eth_getLogs` on the WBNB/slisBNB pool returned 5 `Swap` logs in a 50k-block window.
- **Addresses:** parsed from the docs pages "DEX — Smart Contract (BSC)" and "Smart Contract (Ethereum)", then existence-checked with `eth_getCode`. Proxy slots and ProxyAdmin `owner()` were read live.
- **Chain coverage:** ListaV3Factory addresses return `0x` on the seven other target chains.

Authoritative sources:
- [lista-dao/lista-v3](https://github.com/lista-dao/lista-v3) · [lista-dao/lista-v2](https://github.com/lista-dao/lista-v2)
- [Lista docs — DEX smart contracts (BSC)](https://docs.bsc.lista.org/for-developer/dex/smart-contract) · [Ethereum](https://docs.bsc.lista.org/for-developer/dex/smart-contract-ethereum)
