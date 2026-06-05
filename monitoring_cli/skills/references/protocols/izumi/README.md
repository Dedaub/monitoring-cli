# iZUMi Finance — Compressed Reference Index

**Status:** topic0/selectors computed locally with keccak (pycryptodome) from canonical source (`izumiFinance/iZiSwap-core`, `iZiSwap-periphery`, `iZiSwap-farm`, `izumi-uniV3Mining`, `veiZi`); addresses pulled from in-repo `scripts/deployed.js` + the official `developer.izumi.finance` deployed-contracts page, then **re-verified on-chain** via `eth_call`/`eth_getCode`/`eth_getLogs` vs publicnode (2026-06). Core `Swap` and LiquidityManager `DecLiquidity` topic0s + all core/periphery 4-byte selectors were additionally confirmed against **live logs / deployed bytecode** on Base.

**What iZUMi is.** iZUMi Finance is a multi-product "Liquidity-as-a-Service" (LaaS) protocol. Three on-chain products + a governance layer:

| Product | File | What it is |
|---|---|---|
| **iZiSwap** | [`iziswap.md`](iziswap.md) | A **concentrated-liquidity DEX** built on a bespoke **Discretized-Liquidity AMM (DL-AMM)** — liquidity sits on discrete ticks using a **constant-sum formula (x+y=k)** per tick, with **native on-chain limit orders**. NOT a Uniswap-V3 fork (Uni V3 is continuous x·y=k); its own core (pool + 5 delegatecall modules) + periphery. Marketed as **iZiSwap Pro** (order-book-style DEX UX over the *same* contracts — flagship on zkSync Era). The flagship, on **40+ chains**. |
| **LiquidBox** | [`liquidbox.md`](liquidbox.md) | **Programmable liquidity mining** — stake a concentrated-liquidity LP **NFT** to earn rewards. Two engines: `izumi-uniV3Mining` (mines **Uniswap V3** NFTs — iZUMi's original 2021 product) and `iZiSwap-farm` (mines **iZiSwap** NFTs). Strategies: One-Side / Fixed-Range / Dynamic-Range, with optional **veiZi boost**. |
| **veiZi + iZi + iUSD** | [`tokens.md`](tokens.md) | `iZi` ERC-20 governance/reward token, `veiZi` interest-bearing **ERC-721 vote-escrow veNFT** (Ethereum only), `iUSD` = **iZUMi Bond USD** (treasury-backed bond-issued 18-dec stablecoin). |

## ⚠️ Deployment footprint vs. the requested chain list

Requested: **Ethereum, Base, Binance(BNB), Avalanche, Arbitrum, Optimism, Polygon PoS**. On-chain reality (every ✅/❌ below was `eth_getCode`/`eth_call`-verified this run):

| Requested chain | iZiSwap DEX | iZi token | veiZi | LiquidBox |
|---|---|---|---|---|
| **Ethereum** (1) | ✅ factory `0x1502d025…` (24,342 B, live; **absent from the official 0.1 docs** but on-chain real) | ✅ `0x9ad37205…` ("iZi") | ✅ `0xB56A454d…` | ✅ Uniswap-V3 mining |
| **BNB Chain** (56) | ✅ factory `0x93BB94a0…` | ✅ `0x60D01EC2…` | ❌ (mainnet) | ✅ iZiSwap-farm |
| **Arbitrum** (42161) | ✅ factory `0xCFD8A067…` | ✅ `0x60D01EC2…` | ❌ | ✅ UniV3 mining + farm |
| **Polygon PoS** (137) | ✅ factory `0xcA7e2176…` | ✅ `0x60D01EC2…` | ❌ | ✅ UniV3 mining |
| **Base** (8453) | ✅ factory `0x8c7d3063…` | ✅ `0x60D01EC2…` | ❌ | farm-capable |
| **Optimism** (10) | ✅ factory `0x8c7d3063…` (**= Base's entire address set**) | ❌ (not at `0x60D01EC2…`) | ❌ | ❌ |
| **Avalanche** (43114) | ❌ **NOT deployed** (`0x` at the deterministic factory; absent from docs + `deployed.js`) | ❌ | ❌ | ❌ |

**Bottom line: iZiSwap is live on 6 of the 7 requested chains — everything except Avalanche.** veiZi is **Ethereum-only**. The iZi token lives on ETH + the four `0x60D01EC2…` chains. Beyond the requested seven, iZiSwap is deployed on **40+ chains** (Linea, zkSync Era, Mantle, Scroll, Manta, opBNB, Taiko, Merlin, Cronos, Meter, X Layer, BOB, Kava, Core, Gravity, IoTeX, Morph, Plume, Hemi, Klaytn, Aurora, Conflux, Ontology, ETC, Ultron, Telos, ZKFair, Zeta, Mode, Kroma … — full factory list in [`iziswap.md`](iziswap.md)).

## Two deployment generations (key to address handling)

iZiSwap was **not** deployed deterministically everywhere — addresses are **nonce-ordered CREATE**, so they differ per chain and **the same address hosts different contract roles on different chains**:
- **Gen-1 (2022–2023, per-chain unique factory):** Ethereum `0x1502d025…`, BNB `0x93BB94a0…`, Arbitrum `0xCFD8A067…`, Polygon `0xcA7e2176…`, Mantle/Linea `0x45e5F264…`, etc. Each has its own module + periphery set.
- **Gen-2 (later chains, shared factory `0x8c7d3063579BdB0b90997e18A770eaE32E1eBb08`):** Base, **Optimism**, Scroll, opBNB, Manta, Taiko, zkFair, Zeta, BOB, Kava, Core, Gravity, IoTeX, Morph, Plume, Hemi, Kroma, Loot, Over, Memecore … These **share one address set** (Base ≡ Optimism for every contract). Testnets share `0x64c2F1306b4ED3183E7B345158fd01c19C0d8c5E`.

> **Cross-chain role collision (monitoring trap):** `0x1502d025BfA624469892289D45C0352997251728` is the **Ethereum iZiSwapFactory** *and* the **Base/Optimism LimitOrderManager**. `0x2db0AFD0…` is the **Ethereum Swap router** *and* the **Base/OP Quoter**. `0xf4efdb5a…` is the **ETH swapX2YModule** *and* the **Base/OP LiquidityModule**. **Never infer a contract's role from its address across chains — always pin (chainId, address) together.**

## Key facts for monitoring
- **iZiSwap is its own AMM, not a Uniswap fork.** Core `Swap` topic0 = `0x0fe977d6…` (≠ Uniswap V3 `0xc42079f9…`). Liquidity is keyed on integer **points** (ticks) with `leftPoint/rightPoint`; positions are NFTs in `LiquidityManager`.
- **Pool = module-dispatch contract.** Each `iZiSwapPool` `delegatecall`s into 5 shared modules (SwapX2Y, SwapY2X, Liquidity, LimitOrder, Flash) set on the factory — **but all events are emitted under the pool address**, so monitor pools, not modules. Modules hold no state and emit nothing.
- **Native limit orders.** The pool emits `AddLimitOrder`/`DecLimitOrder`/`CollectLimitOrder`; the `LimitOrderManager` periphery wraps them with `NewLimitOrder`/`Claim`.
- **veiZi `Supply` topic0 `0x5e2aa66e…` collides** with Velodrome/Curve/Balancer veToken `Supply`. **LiquidBox `Deposit(address,uint256,uint256)` `0x90890809…` collides** with MasterChef/sJOE/Sushi/Pancake; `Withdraw(address,uint256)` `0x884edad9…` collides with Velodrome gauge / sJOE. Disambiguate by emitter address.
- **No lending, no perps.** iZUMi ships only the DEX (iZiSwap), liquidity mining (LiquidBox), governance (veiZi) and a stablecoin (iUSD).

## Sources
- Code: [`izumiFinance/iZiSwap-core`](https://github.com/izumiFinance/iZiSwap-core), [`iZiSwap-periphery`](https://github.com/izumiFinance/iZiSwap-periphery), [`iZiSwap-farm`](https://github.com/izumiFinance/iZiSwap-farm), [`izumi-uniV3Mining`](https://github.com/izumiFinance/izumi-uniV3Mining), [`veiZi`](https://github.com/izumiFinance/veiZi).
- Addresses: in-repo `scripts/deployed.js`; `developer.izumi.finance/iZiSwap/deployed_contracts/mainnet`; all re-verified on-chain (publicnode).
