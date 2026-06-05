# iZiSwap — Compressed Reference (Discretized-Liquidity AMM + native limit orders)

**Status:** topic0/selectors computed locally with keccak (pycryptodome) from `izumiFinance/iZiSwap-core` + `iZiSwap-periphery` source; addresses from in-repo `scripts/deployed.js` + `developer.izumi.finance` and **re-verified on-chain** (publicnode, 2026-06). Core `Swap` topic0 confirmed against **376 live Base logs**; LiquidityManager `DecLiquidity` confirmed live; **every core + periphery selector confirmed present in deployed Base bytecode**.
**Scope:** the **iZiSwap DEX** — core (`iZiSwapPool` + `iZiSwapFactory` + 5 delegatecall modules) and periphery (`LiquidityManager` NFT, `LimitOrderManager`, `LimitOrderWithSwapManager`, `Swap` router, `Quoter`/`QuoterWithLim`, `Locker`, `Box`). Liquidity mining = [`liquidbox.md`](liquidbox.md); tokens/governance = [`tokens.md`](tokens.md); index + footprint = [`README.md`](README.md).
**Key fact:** iZiSwap is **iZUMi's own AMM, NOT a Uniswap-V3 fork**. It uses a **Discretized-Liquidity AMM (DL-AMM)**: liquidity and limit orders sit on **discrete integer points (ticks)** trading via a **constant-sum formula (x+y=k)** per tick — distinct from Uniswap V3's *continuous* x·y=k. The pool is a **module-dispatch contract** — it `delegatecall`s 5 shared, stateless modules, but **emits all events under the pool address**. Native limit orders are first-class. It is **one continuously-deployed design — there is no "iZiSwap V2/V3" core**; **iZiSwap Pro** (the order-book DEX, flagship on zkSync Era) is the *same* contracts with an order-book UX. Live on **6 of 7 requested chains (all but Avalanche)** and 40+ total.

---

## Topics (chain-agnostic) — `topic0 -> Event(types)`

### iZiSwapPool — emitted by **every pool** (logic delegatecalled from modules, but `emit` runs in pool context)
```
0x0fe977d619f8172f7fdbe8bb8928ef80952817d96936509f67d66346bc4cd10f -> Swap(address,address,uint24,bool,uint256,uint256,int24)   [tokenX,tokenY,fee(all indexed),sellXEarnY,amountX,amountY,currentPoint]  ✓LIVE  (≠ Uniswap V3 Swap)
0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde -> Mint(address,address,int24,int24,uint128,uint256,uint256)   [sender,owner,leftPt,rightPt(owner+pts indexed),liquidity,amountX,amountY]
0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c -> Burn(address,int24,int24,uint128,uint256,uint256)           [owner,leftPt,rightPt(all indexed),liquidity,amountX,amountY]
0xf69135213cd78fa4cffb855edf80272133f69bd8a6fb3236340a69b4d6e248e3 -> CollectLiquidity(address,address,int24,int24,uint256,uint256) [owner,recipient,leftPt,rightPt — LP fee/withdraw collect]
0xbdbdb71d7860376ba52b25a5028beea23581364a40522f6bcfb86bb1f2dca633 -> Flash(address,address,uint256,uint256,uint256,uint256)        [sender,recipient,amountX,amountY,paidX,paidY]
0x4f4658280ee6d0e8f09b5e436dacaca69ec5dd7c2ba05fb010d5145a3567cdad -> AddLimitOrder(address,uint128,uint128,int24,uint128,uint128,bool)  [owner,addAmount,acquireAmount,point,claimSold,claimEarn,sellXEarnY]
0x3736ba81d13006f6ea2012ba3e287f087169b55d90a9defb5966fe9eb830d7ea -> DecLimitOrder(address,uint128,int24,uint128,uint128,bool)          [owner,decreaseAmount,point,claimSold,claimEarn,sellXEarnY]
0x7d3d0e34c86e56b4dcd993c09bbbf1b04527ab27b4365dffca10e0ded914e071 -> CollectLimitOrder(address,address,int24,uint128,uint128,bool)      [owner,recipient,point,collectDec,collectEarn,sellXEarnY]
```

### iZiSwapFactory — enumerate all pools
```
0xf04da67755adf58739649e2fb9949a6328518141b7ac9e44aa10320688b04900 -> NewPool(address,address,uint24,uint24,address)   [tokenX,tokenY,fee(all indexed),pointDelta,pool]
```

### LiquidityManager (periphery — ERC-721 LP position NFT; symbol "IZISWAP-LIQUIDITY-NFT")
```
0xf565fdd70b3936f0ae8efc41c2e0822f9de5ecb4dc162b153b129ec4bb9cd93c -> AddLiquidity(uint256,address,uint128,uint256,uint256)   [nftId(indexed),pool,liquidityDelta,amountX,amountY]
0x24f4b91fa7871755148bc2a9e01f85d6fd73ec2a0e6bd9a5717c0d7f5be8c2c3 -> DecLiquidity(uint256,address,uint128,uint256,uint256)   [nftId(indexed),pool,liquidityDelta,amountX,amountY]  ✓LIVE
0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef -> Transfer(address,address,uint256)     [ERC-721 — position NFT mint/move/burn]
0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925 -> Approval(address,address,uint256)
0x17307eab39ab6107e8899845ad3d59bd9653f200f220920489ca2b5937696c31 -> ApprovalForAll(address,address,bool)
```

### LimitOrderManager (periphery — wraps pool limit orders)
```
0x2698353c4d06f732989c559a540266c64c36028530473e5af23b864a413a861f -> NewLimitOrder(address,int24,address,uint128,uint128,uint128,bool)   [pool,point,user,amount,sellingRemain,earn,sellXEarnY]
0x35dbc0879e3456d619a96ce76932eff5c5b51c95db75c6dd2a2ca4aa42560c32 -> Claim(address,int24,address,uint128,uint128,bool)                   [pool,point,user,sold,earn,sellXEarnY]
```

### LimitOrderWithSwapManager (periphery — limit order + instant market swap)
```
0x6074fbb9f5042e9bfa9fef06b19805fb2a7d233f0a8749b5bf70ff90d2c15642 -> MarketSwap(address,address,uint24,uint128,uint128)                   [tokenIn,tokenOut,fee,amountIn,amountOut]
0x985e497292727147b826b1f455108c8fc6d2b15f188a7c2484c469c2c07baa60 -> Cancel(address,address,uint24,int24,uint128,uint128,uint128)         [tokenIn,tokenOut,fee,pt,initAmountIn,remainAmountIn,...]
0x73ffe4fe211f43d09d482e54c4cf7a9be8b373b194ad3cdf203b8a2b37a57570 -> Finish(address,address,uint24,int24,uint128,uint128)                 [tokenIn,tokenOut,fee,pt,initAmountIn,amountOut]
```

### Locker (periphery — lock LP NFTs)
```
0x8738fac4c3f6ded3649d1d6c64679bd1a81c89414e861f2ca28b5fc585c0e33d -> Lock(uint256,address,uint256)                 [nftId,owner,unlockTime]
0x7c1b4124ad365abe54b7b7e4ef5b97f59abb321a4eb86a773c7f733541b9ef8b -> ExtendLockTime(uint256,address,uint256,uint256)
0x8353ffcac0876ad14e226d9783c04540bfebf13871e868157d2a391cad98e918 -> Withdraw(uint256,address)
```

---

## Function signatures (chain-agnostic) — `selector -> name(types) -> returns`
*(all confirmed present in deployed Base bytecode)*

### iZiSwapFactory
```
0x78eda67b -> newPool(address,address,uint24,int24) -> address       [tokenX,tokenY,fee,currentPoint → pool]
0xbecbcc6a -> pool(address,address,uint24) -> address                [tokenX,tokenY,fee → pool (0 if none)]
0x10a17ee8 -> enableFeeAmount(uint24,uint24)                         [fee, pointDelta]
0x3ce8e8db -> fee2pointDelta(uint24) -> int24
0x254ace8f -> swapX2YModule() -> address       0x86df77de -> swapY2XModule() -> address
0x400b6cdc -> liquidityModule() -> address     0x476476e0 -> limitOrderModule() -> address
0x5deef20a -> flashModule() -> address         0xd8cd50e2 -> chargeReceiver() -> address
```

### iZiSwapPool (core — entrypoints + state; X→Y means selling tokenX)
```
0x857f812f -> swapX2Y(address,uint128,int24,bytes) -> (uint256,uint256)            [recipient,amount,lowPt,data]
0x2c481252 -> swapY2X(address,uint128,int24,bytes) -> (uint256,uint256)            [recipient,amount,highPt,data]
0x59dd1436 -> swapX2YDesireY(address,uint128,int24,bytes) -> (uint256,uint256)     [exact-output sell X]
0xf094685a -> swapY2XDesireX(address,uint128,int24,bytes) -> (uint256,uint256)     [exact-output sell Y]
0x3c8a7d8d -> mint(address,int24,int24,uint128,bytes) -> (uint256,uint256)         [recipient,leftPt,rightPt,liquidDelta,data]
0xa34123a7 -> burn(int24,int24,uint128) -> (uint256,uint256)                       [leftPt,rightPt,liquidDelta]
0x872d1f15 -> collect(address,int24,int24,uint256,uint256) -> (uint256,uint256)    [recipient,leftPt,rightPt,xLim,yLim]
0xff12504e -> addLimOrderWithX(address,int24,uint128,bytes) -> (uint128,uint128)
0x0e1552f0 -> addLimOrderWithY(address,int24,uint128,bytes) -> (uint128,uint128)
0x4cd70e91 -> decLimOrderWithX(int24,uint128) -> uint128       0x62c944ca -> decLimOrderWithY(int24,uint128) -> uint128
0x6ad1718f -> collectLimOrder(address,int24,uint128,uint128,bool) -> (uint128,uint128)
0x490e6cbc -> flash(address,uint256,uint256,bytes)
0xc19d93fb -> state() -> (uint160,int24,uint16,uint16,uint16,bool,uint128,uint128)   [sqrtPrice_96,currentPoint,observationCurrentIndex,…,liquidity,liquidityX]
0x58c51ce6 -> pointDelta() -> int24
```

### LiquidityManager (periphery — `MintParam`/`AddLiquidityParam` are tuples)
```
0x96f639ed -> mint((address,address,address,uint24,int24,int24,uint128,uint128,uint128,uint128,uint256)) -> (uint256,uint128,uint256,uint256)
              [MintParam{miner,tokenX,tokenY,fee,pl,pr,xLim,yLim,amountXMin,amountYMin,deadline} → lid,liquidity,amountX,amountY]
0xcbd89416 -> addLiquidity((uint256,uint128,uint128,uint128,uint128,uint256)) -> (uint128,uint256,uint256)   [lid,xLim,yLim,amountXMin,amountYMin,deadline]
0x15feae51 -> decLiquidity(uint256,uint128,uint256,uint256,uint256) -> (uint256,uint256)   [lid,liquidDelta,amountXMin,amountYMin,deadline]
0xa0e4eb3c -> collect(address,uint256,uint128,uint128) -> (uint256,uint256)                [recipient,lid,amountXLim,amountYLim]
0x42966c68 -> burn(uint256) -> bool                                                        [lid — only when liquidity==0]
```

### Swap router / LimitOrderManager (periphery)
```
0x75ceafe6 -> swapAmount((bytes,address,uint128,uint256,uint256)) -> (uint256,uint256)   [SwapParams{path,recipient,amount,minAcquired,deadline} — exact-input multi-hop]
0x115ff67e -> swapDesire((bytes,address,uint128,uint256,uint256)) -> (uint256,uint256)   [exact-output multi-hop]
0x5ddf5745 -> newLimOrder(uint256,(address,address,uint24,int24,uint128,bool,uint256)) -> (uint128,uint128)   [idx, AddLimOrderParam{tokenX,tokenY,fee,pt,amount,sellXEarnY,deadline}]
0x1490d44b -> decLimOrder(uint256,uint128,uint256) -> uint128            [orderIdx,amount,deadline]
0x8f159451 -> collectLimOrder(address,uint256,uint128,uint128) -> (uint256,uint256)   [recipient,orderIdx,collectDec,collectEarn]
0x21d85d69 -> updateOrder(uint256) -> (uint256,uint256)
```

---

## Addresses (network-specific)

> ✓ = verified on-chain this run (factory `swapX2YModule()`/`chargeReceiver()` getters, periphery `factory()`, NFT `symbol()`). Fee tiers seen on-chain: **500 / 3000 / 10000** (fee in 1e-6; iZiSwap also enables 100/400/2000). Pool bytecode ≈ 17.5 KB, identical across pools; `pool()` returns 0 if a (tokenX,tokenY,fee) pool doesn't exist.

### Ethereum (1) — Gen-1, **undocumented in 0.1 docs but live on-chain**
```
0x1502d025BfA624469892289D45C0352997251728 -> iZiSwapFactory            (24,342 B ✓; ALSO = Base/OP LimitOrderManager — role differs by chain!)
0xf4efDB5A1E852f78e807fAE7100B1d38351e38c7 -> SwapX2YModule
0xe96526e92ee57bBD468DA1721987aa988b008768 -> SwapY2XModule
0xbD6abA1Ef82A4cD6e15CB05e95f433ef48dfb5df -> LiquidityModule
0x8c7d3063579BdB0b90997e18A770eaE32E1eBb08 -> LimitOrderModule          (= the Gen-2 factory address on other chains!)
0x110dE362cc436D7f54210f96b8C7652C2617887D -> FlashModule               (= Base/OP LiquidityManager on other chains!)
0x19b683A2F45012318d9B2aE1280d68d3eC54D663 -> LiquidityManager          (ERC-721, symbol "IZISWAP-LIQUIDITY-NFT" ✓, factory()→factory ✓)
0x2db0AFD0045F3518c77eC6591a542e326Befd3D7 -> Swap (router)             (factory()→factory ✓; = Base/OP Quoter on other chains!)
0x0481b236f191877619523ee309c82b3574214597 -> chargeReceiver (fee treasury)
0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 -> WETH (pool wrap token)
```
*ETH appears to be a **minimal deployment** (factory + modules + LiquidityManager + Swap). No separate LimitOrderManager/Quoter in `deployed.js` — but the core **limitOrderModule is set**, so pools can still emit `AddLimitOrder`/`DecLimitOrder`/`CollectLimitOrder` directly.*

### BNB Chain (56) — Gen-1 (docs 2023.07.17)
```
0x93BB94a0d5269cb437A1F71FF3a77AB753844422 -> iZiSwapFactory            (swapX2YModule()→0x759424dd ✓)
0x759424DD2d409b4d6B39A83199177d07dc257ad7 -> SwapX2YModule
0xb922af73b899a4F0B9761b0c4407F1250FdD05be -> SwapY2XModule
0x1eaa949444F5a4BeE40D25d31039ECDDda0EEb19 -> LiquidityModule
0x2e2AbBFB7913669B930A4Ecfe130863c524A8810 -> LimitOrderModule
0x20804C62079569E1491fa948db005f93FA9a383d -> FlashModule
0xBF55ef05412f1528DbD96ED9E7181f87d8C9F453 -> LiquidityManager (NFT)
0x72fAfc28bFf27BB7a5cf70585CA1A5185AD2f201 -> LimitOrderManager
0xedf2021f41AbCfE2dEA4427E1B61f4d0AA5aA4b8 -> Swap (router)
0x0e79C263EeBc37977038F26fb86Dfa84636cFE84 -> Quoter (no limit)
0xDCe9a4ACC59E69ECcC0cdA2E82fe601fdB726542 -> QuoterWithLim (≤10000 ticks)
0xA1189a420662105bef5Be444B8b1E0a7D8279672 -> Multicall
0x195bb56eae9832cf9dfc5e5982b11eb379a1cb7d -> chargeReceiver (fee treasury) ✓
0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c -> WBNB
```

### Arbitrum One (42161) — Gen-1 (docs 2023.07.17)
```
0xCFD8A067e1fa03474e79Be646c5f6b6A27847399 -> iZiSwapFactory            (swapX2YModule()→0xac9788cf ✓)
0xAC9788cfea201950db91d7db6f28c448cf3a4b29 -> SwapX2YModule
0x93C22Fbeff4448F2fb6e432579b0638838Ff9581 -> SwapY2XModule
0x9Bf8399c9f5b777cbA2052F83E213ff59e51612B -> LiquidityModule
0x12a76434182c8cAF7856CE1410cD8abfC5e2639F -> LimitOrderModule
0xBd3bd95529e0784aD973FD14928eEDF3678cfad8 -> FlashModule
0xAD1F11FBB288Cd13819cCB9397E59FAAB4Cdc16F -> LiquidityManager (NFT)
0xE78e7447223aaED59301b44513D1d3A892ECF212 -> LimitOrderManager
0x01fDea353849cA29F778B2663BcaCA1D191bED0e -> Swap (router)
0x96539F87cA176c9f6180d65Bc4c10fca264aE4A5 -> Quoter (no limit)
0x64b005eD986ed5D6aeD7125F49e61083c46b8e02 -> QuoterWithLim
0x844A47ad42187F255e5523D4d3Be33f6e94786f8 -> Multicall
0x82af49447d8a07e3bd95bd0d56f35241523fbab1 -> WETH
```

### Polygon PoS (137) — Gen-1 (docs 2023.07.17)
```
0xcA7e21764CD8f7c1Ec40e651E25Da68AeD096037 -> iZiSwapFactory            (swapX2YModule()→0x77ab297d ✓)
0x77aB297Da4f3667059ef0C32F5bc657f1006cBB0 -> SwapX2YModule
0x6a7CDD0CC87ec02ed85c196e57BaBe1bc0Acd6f2 -> SwapY2XModule
0x4a41EbEa62E7aB70413356D30DF73cA803aaE41c -> LiquidityModule
0x45e5F26451CDB01B0fA1f8582E0aAD9A6F27C218 -> LimitOrderModule
0x611575eE1fbd4F7915D0eABCC518eD396fF78F0c -> FlashModule
0x1CB60033F61e4fc171c963f0d2d3F63Ece24319c -> LiquidityManager (NFT)
0x25C030116Feb2E7BbA054b9de0915E5F51b03e31 -> LimitOrderManager
0x032b241De86a8660f1Ae0691a4760B426EA246d7 -> Swap (router)
0xe6805638db944eA605e774e72c6F0D15Fb6a1347 -> Quoter (no limit)
0xe4A0b241D8345d86FB140D40c87C5fbDd685B9dd -> QuoterWithLim
0x48dA26C7645e98f6764E8E1f4A87112a2BD10F19 -> Multicall
0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270 -> WMATIC/WPOL
0x0481b236f191877619523ee309c82b3574214597 -> chargeReceiver
```

### Base (8453) **≡** Optimism (10) — Gen-2, **IDENTICAL address set on both chains** (verified each on its own chain)
```
0x8c7d3063579BdB0b90997e18A770eaE32E1eBb08 -> iZiSwapFactory            (✓ on Base AND OP; swapX2YModule()→0x4d467374 ✓ both)
0x4d4673745AAC664eFB9758fdd571F40d78a87bfe -> SwapX2YModule
0x32D02Fc7722E81F6Ac60B87ea8B4b63a52Ad2b55 -> SwapY2XModule
0xF4efDB5A1E852f78e807fAE7100B1d38351e38c7 -> LiquidityModule
0xe96526e92ee57bBD468DA1721987aa988b008768 -> LimitOrderModule
0xbD6abA1Ef82A4cD6e15CB05e95f433ef48dfb5df -> FlashModule
0x110dE362cc436D7f54210f96b8C7652C2617887D -> LiquidityManager (NFT)    (factory()→0x8c7d3063 on OP ✓; live DecLiquidity on Base ✓)
0x1502d025BfA624469892289D45C0352997251728 -> LimitOrderManager         (factory()→0x8c7d3063 on OP ✓; = ETH Factory on Ethereum!)
0x02F55D53DcE23B4AA962CC68b0f685f26143Bdb2 -> Swap (router)             (factory()→0x8c7d3063 on OP ✓)
0x2db0AFD0045F3518c77eC6591a542e326Befd3D7 -> Quoter (no limit)         (factory()→0x8c7d3063 on OP ✓; = ETH Swap on Ethereum!)
0x3EF68D3f7664b2805D4E88381b64868a56f88bC4 -> QuoterWithLim
0x7a524c7e82874226F0b51aade60A1BE4D430Cf0F -> Multicall
0x4200000000000000000000000000000000000006 -> WETH (both)
chargeReceiver: Base 0x195bb56eae9832cf9dfc5e5982b11eb379a1cb7d ✓ | Optimism 0x0481b236f191877619523ee309c82b3574214597 ✓
```

### Avalanche C-Chain (43114) — **NOT deployed** (`0x` at `0x8c7d3063…`; absent from docs + `deployed.js`).

### Other chains — `iZiSwapFactory` only (40+ deployments; periphery follows the Gen it belongs to)
```
Gen-2 shared factory 0x8c7d3063579BdB0b90997e18A770eaE32E1eBb08:
   Scroll, opBNB, Manta, zkFair, Zeta, Taiko, BOB, Kava, Core, Gravity, IoTeX, Morph, Plume, Hemi, Kroma, Loot, overProtocol, memecore
Gen-1 unique factories:
   Mantle 0x45e5F26451CDB01B0fA1f8582E0aAD9A6F27C218   Linea 0x45e5F26451CDB01B0fA1f8582E0aAD9A6F27C218
   Cronos 0x3EF68D3f7664b2805D4E88381b64868a56f88bC4    Aurora 0xce326A82913EAb09f7ec899C4508Cbe0E6526A74
   Conflux eSpace 0x77aB297Da4f3667059ef0C32F5bc657f1006cBB0   Ontology 0x032b241De86a8660f1Ae0691a4760B426EA246d7
   Ethereum Classic 0x79D175eF5fBe31b5D84B3ee359fcbBB466153E39   Meter 0xed31C5a9C764761C3A699E2732183ba5d6EAcC35
   Telos 0x6a7CDD0CC87ec02ed85c196e57BaBe1bc0Acd6f2    Ultron 0xd7de110Bd452AAB96608ac3750c3730A17993DE0   hashKey 0x110dE362cc436D7f54210f96b8C7652C2617887D
Testnets share factory 0x64c2F1306b4ED3183E7B345158fd01c19C0d8c5E.
```

---

## Cross-chain summary
- **iZiSwap DEX on 6/7 requested chains** (ETH, BNB, Arbitrum, Polygon, Base, Optimism) — **not Avalanche**. Plus 40+ other chains.
- **Aggregator/universal-router layer (periphery `universal/` + `TapProxy`):** beyond the core `Swap` router, iZUMi ships `UniversalSwapRouter`/`UniversalV3SwapRouter` + `iZiSwapRouter`/`iZiSwapV3Router`/`ClassicSwapRouter` that **route across iZiSwap (DL-AMM) + Uniswap-V3-forks + Uniswap-V2-style ("Classic") pools**, plus `TapProxy` (wraps PancakeSwap/Uniswap routers). Deployed per-chain via the multi-step script (addresses vary, not in the one-command set) — these are routing wrappers that ultimately trigger the **pool `Swap`** event, so they add no new topic0; monitor the pool, not the router.
- **Two deployment generations**: Gen-1 = per-chain unique factories (ETH/BNB/Arb/Polygon/Mantle/Linea/…); Gen-2 = shared factory `0x8c7d3063…` (Base, Optimism, Scroll, Manta, Taiko, …). **Base and Optimism are byte-for-byte the same address set** (only `chargeReceiver` differs).
- **Addresses are nonce-ordered CREATE, not deterministic by role** → the same address means different things on different chains (see Detection #5).

## Proxies
- **No upgradeable proxies anywhere in iZiSwap.** Factory, Pool, modules, and all periphery are **plain immutable contracts** — no EIP-1967 impl slot, no `Upgraded` events.
- **Pools are full CREATE-deployed contracts** (not EIP-1167 clones). Enumerate via `NewPool`; look up via `factory.pool(tokenX,tokenY,fee)`.
- **Upgradeability is via the factory's module pointers**: `swapX2YModule()/…/flashModule()` can in principle be re-pointed by the factory owner, changing pool logic without redeploying pools (the pool reads the module from the factory at call time). Watch the factory owner for module swaps. (Modules themselves are immutable, stateless, emit nothing.)

## Detection invariants & gotchas
1. **iZiSwap `Swap` topic0 `0x0fe977d6…` ≠ Uniswap V3 `Swap` `0xc42079f9…`.** Different AMM, different layout (`tokenX,tokenY,fee` are the indexed topics; no `sender`/`recipient` indexed). Don't reuse Uni constants.
2. **Events are emitted by the POOL, not the modules.** The 5 modules (SwapX2Y/SwapY2X/Liquidity/LimitOrder/Flash) are delegatecall targets — they hold no state and emit nothing. Monitor pool addresses (and `LiquidityManager`/`LimitOrderManager` for NFT/limit-order wrappers).
3. **Two liquidity surfaces:** range liquidity (`Mint`/`Burn`/`CollectLiquidity` on pool; `AddLiquidity`/`DecLiquidity` on `LiquidityManager`) **and** limit orders (`AddLimitOrder`/`DecLimitOrder`/`CollectLimitOrder` on pool; `NewLimitOrder`/`Claim` on `LimitOrderManager`). A position can be either.
4. **`fee` is in 1e-6 units** (e.g. `3000` = 0.3%). `pointDelta` (tick spacing) is derived via `fee2pointDelta(fee)`. Pool key = `(tokenX, tokenY, fee)` with `tokenX < tokenY`.
5. **Address ≠ role across chains (nonce collisions).** `0x1502d025…` = ETH **Factory** but Base/OP **LimitOrderManager**. `0x2db0AFD0…` = ETH **Swap** but Base/OP **Quoter**. `0xf4efDB5A…`/`0x110dE362…` flip between ETH **module** and Base/OP **periphery**. **Always key on (chainId, address).**
6. **`LiquidityManager` ERC-721 `Transfer`/`Approval`/`ApprovalForAll`** share the standard topic0s — disambiguate the LP-NFT by the manager address.
7. **Bytea hex literals need even digit count** (40 for addresses, 64 for topics).

## Quick-copy bytea-ready constants (Postgres `'\x…'`)
```
swap            = '\x0fe977d619f8172f7fdbe8bb8928ef80952817d96936509f67d66346bc4cd10f'
mint            = '\x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde'
burn            = '\x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c'
collect_liq     = '\xf69135213cd78fa4cffb855edf80272133f69bd8a6fb3236340a69b4d6e248e3'
add_lim_order   = '\x4f4658280ee6d0e8f09b5e436dacaca69ec5dd7c2ba05fb010d5145a3567cdad'
dec_lim_order   = '\x3736ba81d13006f6ea2012ba3e287f087169b55d90a9defb5966fe9eb830d7ea'
collect_lim     = '\x7d3d0e34c86e56b4dcd993c09bbbf1b04527ab27b4365dffca10e0ded914e071'
new_pool        = '\xf04da67755adf58739649e2fb9949a6328518141b7ac9e44aa10320688b04900'
add_liquidity   = '\xf565fdd70b3936f0ae8efc41c2e0822f9de5ecb4dc162b153b129ec4bb9cd93c'
dec_liquidity   = '\x24f4b91fa7871755148bc2a9e01f85d6fd73ec2a0e6bd9a5717c0d7f5be8c2c3'
new_limit_order = '\x2698353c4d06f732989c559a540266c64c36028530473e5af23b864a413a861f'
lo_claim        = '\x35dbc0879e3456d619a96ce76932eff5c5b51c95db75c6dd2a2ca4aa42560c32'
```

## Verification & sources
- topic0/selectors: local keccak (pycryptodome) this session from `iZiSwap-core` (`interfaces/IiZiSwapPool.sol`, `IiZiSwapFactory.sol`) and `iZiSwap-periphery` (`LiquidityManager.sol`, `LimitOrderManager.sol`, `LimitOrderWithSwapManager.sol`, `Swap.sol`, `Locker.sol`). Periphery tuple-selectors recomputed from the exact `MintParam`/`AddLiquidityParam`/`SwapParams`/`AddLimOrderParam` structs.
- On-chain (publicnode): factory `swapX2YModule()`/`swapY2XModule()`/…/`chargeReceiver()` on all 7 chains; periphery `factory()` on ETH + OP; `LiquidityManager.symbol()` = "IZISWAP-LIQUIDITY-NFT"; `Swap` topic0 confirmed on 376 live Base logs (pool `0x4cfd5ba4…` WETH/USDC fee 500); `DecLiquidity` confirmed live on Base `LiquidityManager`; **all core + periphery selectors confirmed present in deployed Base bytecode**.
- Source: [`izumiFinance/iZiSwap-core`](https://github.com/izumiFinance/iZiSwap-core), [`iZiSwap-periphery`](https://github.com/izumiFinance/iZiSwap-periphery). Mining = [`liquidbox.md`](liquidbox.md); tokens = [`tokens.md`](tokens.md); index = [`README.md`](README.md).
