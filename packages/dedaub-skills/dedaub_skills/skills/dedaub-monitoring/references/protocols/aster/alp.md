# Aster 1001x / ALP (legacy ApolloX diamond) — Topics, Selectors, Addresses (BNB, Arbitrum, Base)

**Status:** verified on 2026-10-30 against live RPC on BNB (56), Arbitrum (42161) and Base (8453), `eth_getCode` on all nine target chains, the Sourcify-verified facet sources of the BNB diamond, the official Aster "Direct Contract Interaction" page, and the DefiLlama `apollox` adapter.
**Scope:** the on-chain perpetuals engine that Aster inherited from ApolloX (the "1001x" / "Simple" mode) and its liquidity pool token **ALP**. It is an EIP-2535 **diamond**, one per chain. Topics and selectors are chain-agnostic. Addresses are network-specific.

**Status of the product.** The BNB diamond `0x1b6F…FEb0` is still named in the official docs. In a 400,000-block sample (about 3.5 days, ending 2026-10-30) it emitted only two events: `UnStake(address,uint256)` and `ClaimApxReward(address,uint256)`. It emitted no trade, ALP mint or ALP burn event. The Arbitrum diamond emitted nothing in 3,000,000 blocks. Treat these diamonds as wind-down pools that still hold funds. On 2026-10-30 the BNB diamond held 446k USDC, 123k USDT, 368 WBNB, 142 ETH and 2.8 BTCB. ALP supply × `alpPrice()` was about 2.84M × $1.867 ≈ $5.3M on BNB.

---

## 0. Contract families

| Contract | Chain | Role | Proxy? |
|----------|-------|------|--------|
| **ApolloX diamond** | BNB `0x1b6F…FEb0` (6,039 B, 29 facets) · Arbitrum `0xb387…0e48` (318 B, 26 facets) · Base `0x9D93…DD57` (318 B, 25 facets) | Trading, limit orders, prediction (up/down), ALP mint/burn, fee manager, vault accounting, internal timelock. Holds the pool assets. | EIP-2535 diamond; upgrade by `diamondCut` |
| **ALP** | BNB `0x4e47…80e5` · Arbitrum `0xbc76…d9c9` · Base `0xc45f…c43e` | LP token, returned by `ALP()` on the diamond. | `ERC1967Proxy` (680–708 B) |
| **APX** | BNB `0x78f5d389f5cdccfc41594abab4b0ed02f31398b3` | Legacy ApolloX governance token (replaced by ASTER). | No |

The Arbitrum and Base diamonds share facets with the BNB diamond (`VaultFacet` `0x8c7d…9773`, `AlpManagerFacet` `0x0890…5739`, `AccessControlEnumerableFacet` `0x01cf…f51c`, `TradingCloseFacet` `0x8eca…2a09` appear in two or three lists).

---

## 1. Topics (chain-agnostic — from the verified facet ABIs)

None of the trading topics below appeared in the 2026-10-30 sample window (see Status). Their signatures come from the Sourcify ABIs of the BNB facets.

| topic0 | Event | Facet |
|--------|-------|-------|
| `0xa858fcdefab65cbd1997932d8ac8aa1a9a8c46c90b20947575525d9a2a437f8c` | `OpenMarketTrade(address indexed user,bytes32 indexed tradeHash,(address,uint32,uint64,address,address,uint96,uint64,uint64,uint24,bool,uint96,int256,uint96,uint40,uint80,uint40,uint256) ot)` | TradingOpenFacet |
| `0x7064b82c073f138da0ec7646ebb51d4a0061d647accb4670bc564edf0bfac41d` | `MarketPendingTrade(address indexed user,bytes32 indexed tradeHash,(address,bool,address,uint96,uint80,uint64,uint64,uint64,uint24) trade)` | TradingPortalFacet |
| `0x664a65d3a62405ef2c683493b52778675085be44db1631414b5a2918e4f538b2` | `CloseTradeSuccessful(address indexed user,bytes32 indexed tradeHash,(uint64,int96,uint96,int96,uint96) closeInfo)` | TradingCloseFacet |
| `0xcba626e584622d7022d4d4d3fd92d648efa11355ffdccb027ffbae68632c438a` | `ExecuteCloseSuccessful(address indexed user,bytes32 indexed tradeHash,uint8 executionType,(uint64,int96,uint96,int96,uint96) closeInfo)` | TradingCloseFacet (TP/SL/liquidation) |
| `0x82982650e85330c501b1cfb68b1ae3e06d6be2048d4378a018d8b84da6d5c959` | `CloseTradeReceived(address indexed user,bytes32 indexed tradeHash,address indexed token,uint256 amount)` | TradingCloseFacet — payout |
| `0x0bbf7f655caf5ea43b545960e1290a320e5bafffd6036b4afa424f84c266bd19` | `MintAlp(address indexed account,address indexed tokenIn,uint256 amountIn,uint256 alpOut)` | AlpManagerFacet |
| `0x81826951fa1e84c412ecde63e7fa200ad8b39dafd7c8bedf5c5faa5a0f77166b` | `BurnAlp(address indexed account,address indexed receiver,address indexed tokenOut,uint256 alpAmount,uint256 amountOut)` | AlpManagerFacet |
| `0xe38afd60cfd7b6452216d6f6135a7bb7e59af7a977232075081582207b6ac35a` | `OpenLimitOrder(address indexed user,bytes32 indexed orderHash,(address,bool,address,uint96,uint80,uint64,uint64,uint64,uint24) data)` | LimitOrderFacet |
| `0x8b98dca183cef44feaa5052f7f02dc5203ea63fe2425f6388b2608a00b7029ae` | `UpdateMargin(address indexed user,bytes32 indexed tradeHash,uint256 beforeMargin,uint256 margin)` | TradingPortalFacet |
| `0x282511c899c366580a39dc3dc661f74be32e03147f49f11885a2b111b4abde10` | `OpenFee(address indexed token,uint256 totalFee,uint256 daoAmount,uint24 brokerId,uint256 brokerAmount,uint256 alpPoolAmount)` | FeeManagerFacet |
| `0xed23951826835a2eca8093d18f8db8e21bef0d3e23fb913fbe8b4693d656b26b` | `CloseFee(address indexed token,uint256 totalFee,uint256 daoAmount,uint24 brokerId,uint256 brokerAmount,uint256 alpPoolAmount)` | FeeManagerFacet |
| `0xe1a77ab138e1ed19318ed96fba93ce987fc5b9a37da45d74ebfc271df971d352` | `WithdrawRevenue(address indexed token,address indexed operator,uint256 amount)` | FeeManagerFacet — **revenue sweep** |
| `0x44160ac06ba9060cff7716fce0acd00feff72930a9f3fdd93e19f66cd8e946a3` | `PredictAndBet(address indexed user,uint256 indexed id,(address,uint96,address,uint96,address,uint96,uint32,uint64,uint40,uint24,bool,uint8) op)` | PredictUpDownFacet |
| `0x6150d0a8fb8c88106db5aaf79cbc73741c167f0bf6a74238d6eca20693f605f7` | `SettlePredictionSuccessful(uint256 indexed id,bool win,uint256 endPrice,address token,uint256 profitOrLoss,uint256 closeFee)` | PredictUpDownFacet |
| `0xb24546d975e2628748efc9aced80665e0fad66272033e5c0ea25fd3afac99795` | `UnStake(address,uint256)` | unverified facet `0x3b71…0422` — **live** (1) |
| `0xd7b5b22e75cc5ce21f71dbb51d8a76e5a9b5211d5e53cb4cb194871fbb7efff5` | `ClaimApxReward(address,uint256)` | unverified facet — **live** (1); name from the openchain.xyz signature database |
| `0x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673` | `DiamondCut((address,uint8,bytes4[])[] _diamondCut,address _init,bytes _calldata)` | DiamondCutFacet — **code change** |
| `0xcf3dc0cd0432ab33321e3dd2b96d805cd7cff230cbf139a6168f571da0a77d5d` | `QueueTransaction(bytes32 indexed transactionHash,string functionSignature,bytes data)` | TimeLockFacet |
| `0xef9d8cdf871686f540056b412c18c767afeb6ec3fe4040634ad43b192643103a` | `ExecuteTransaction(bytes32 indexed transactionHash)` | TimeLockFacet |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | PausableFacet / AlpManagerFacet |

## 2. Function signatures

| Selector | Signature | Facet / notes |
|----------|-----------|---------------|
| `0x703085c7` | `openMarketTrade((address,bool,address,uint96,uint80,uint64,uint64,uint64,uint24))` | TradingPortalFacet |
| `0xb7aeae66` | `openMarketTradeBNB((address,bool,address,uint96,uint80,uint64,uint64,uint64,uint24))` | payable |
| `0x5177fd3b` / `0xd8eb6e91` | `closeTrade(bytes32)` / `batchCloseTrade(bytes32[])` | |
| `0x29d9ddce` | `addMargin(bytes32,uint96)` | |
| `0xc375f765` / `0x08cdd3a3` | `mintAlp(address,uint256,uint256,bool)` / `mintAlpBNB(uint256,bool)` | AlpManagerFacet |
| `0x48276b6f` / `0x63810c0d` | `burnAlp(address,uint256,uint256,address)` / `burnAlpBNB(uint256,uint256,address)` | AlpManagerFacet |
| `0xe6e83661` | `withdrawRevenue(address[])` | FeeManagerFacet |
| `0x1f931c1c` | `diamondCut((address,uint8,bytes4[])[],address,bytes)` | DiamondCutFacet |
| `0x52ef6b2c` | `facetAddresses()` | DiamondLoupeFacet |
| `0x4c8564cd` / `0xea64f5dc` | `ALP()` / `alpPrice()` | views; price has 8 decimals |

## 3. Addresses

| Chain (ID) | Diamond | ALP | Admin (`DEFAULT_ADMIN_ROLE`) |
|------------|---------|-----|------------------------------|
| BNB (56) | `0x1b6F2d3844C6ae7D56ceb3C3643b9060ba28FEb0` | `0x4e47057f45adf24ba41375a175da0357cb3480e5` (impl `0x96cbcd9bbd63c8568dec83a991ef05f29058767d`) | Safe `0x60ede4402a34762d608ad9ba7bd3797f5bfe544c` (4-of-7) |
| Arbitrum (42161) | `0xb3879e95a4b8e3ee570c232b19d520821f540e48` | `0xbc76b3fd0d18c7496c0b04aea0fe7c3ed0e4d9c9` (impl `0x00806829b38133341f3dc385b5cecdabc1a2fb95`) | Safe `0x60ede4402a34762d608ad9ba7bd3797f5bfe544c` |
| Base (8453) | `0x9D93e5B2364070bC9837e91833F162430246DD57` | `0xc45fa4880864ad93b52c579b08e73ccd7e80c43e` (impl `0x5292c9b2be74fbf89429a566ed2e4ddb1e9d0a72`) | — |
| Ethereum, Avalanche, Optimism, Polygon, Robinhood, Arc | — | — | — |

Balances on 2026-10-30: Arbitrum diamond 33k USDT, 5.9 WETH, 0.25 WBTC (ALP supply 60.6k). Base diamond 1.4k USDbC, 0.67 WETH (ALP supply 1.4k). DefiLlama also lists opBNB, zkSync Era and Manta diamonds; those chains are out of scope.

**Same-address traps.** `0x9D93…DD57` is the Base diamond, but on Arbitrum the same address is a facet of the Arbitrum diamond, and on BNB it holds another 10 kB contract. `0xb387…0e48` and `0xbc76…d9c9` also hold unrelated code on Base. Key on `(chain, address)`.

## 4. Proxies & gotchas

1. **Diamond upgrades** happen through `diamondCut` and emit `DiamondCut` (`0x8faa7087…`). There is no EIP-1967 slot on the diamond (impl slot empty). Re-read `facetAddresses()` after each cut.
2. **ALP tokens are `ERC1967Proxy`** (impl slot values in §3). Watch `Upgraded` (`0xbc7cd75a…`).
3. **The diamond holds the pool.** A large `ERC-20 Transfer` out of the diamond outside `CloseTradeReceived` / `BurnAlp` / `WithdrawRevenue` is anomalous, more so because trading is idle.
4. The legacy ApolloX treasuries (custody for the old order-book product) are in `bridge.md`.

## 5. Quick-copy detection constants (bytea-ready for PG)

```
TOPIC_APX_OPEN_MARKET_TRADE   = '\xa858fcdefab65cbd1997932d8ac8aa1a9a8c46c90b20947575525d9a2a437f8c'
TOPIC_APX_CLOSE_TRADE_OK      = '\x664a65d3a62405ef2c683493b52778675085be44db1631414b5a2918e4f538b2'
TOPIC_APX_EXECUTE_CLOSE_OK    = '\xcba626e584622d7022d4d4d3fd92d648efa11355ffdccb027ffbae68632c438a'
TOPIC_APX_CLOSE_TRADE_RECV    = '\x82982650e85330c501b1cfb68b1ae3e06d6be2048d4378a018d8b84da6d5c959'
TOPIC_APX_MINT_ALP            = '\x0bbf7f655caf5ea43b545960e1290a320e5bafffd6036b4afa424f84c266bd19'
TOPIC_APX_BURN_ALP            = '\x81826951fa1e84c412ecde63e7fa200ad8b39dafd7c8bedf5c5faa5a0f77166b'
TOPIC_APX_WITHDRAW_REVENUE    = '\xe1a77ab138e1ed19318ed96fba93ce987fc5b9a37da45d74ebfc271df971d352'
TOPIC_APX_UNSTAKE             = '\xb24546d975e2628748efc9aced80665e0fad66272033e5c0ea25fd3afac99795'
TOPIC_DIAMOND_CUT             = '\x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673'
SEL_APX_OPEN_MARKET_TRADE     = '\x703085c7'
SEL_APX_CLOSE_TRADE           = '\x5177fd3b'
SEL_APX_MINT_ALP              = '\xc375f765'
SEL_APX_BURN_ALP              = '\x48276b6f'
SEL_DIAMOND_CUT               = '\x1f931c1c'
BNB_APX_DIAMOND               = '\x1b6f2d3844c6ae7d56ceb3c3643b9060ba28feb0'
BNB_APX_ALP                   = '\x4e47057f45adf24ba41375a175da0357cb3480e5'
ARB_APX_DIAMOND               = '\xb3879e95a4b8e3ee570c232b19d520821f540e48'
ARB_APX_ALP                   = '\xbc76b3fd0d18c7496c0b04aea0fe7c3ed0e4d9c9'
BASE_APX_DIAMOND              = '\x9d93e5b2364070bc9837e91833f162430246dd57'
BASE_APX_ALP                  = '\xc45fa4880864ad93b52c579b08e73ccd7e80c43e'
BNB_APX_ADMIN_SAFE            = '\x60ede4402a34762d608ad9ba7bd3797f5bfe544c'
```

## 6. Verification & sources

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the Sourcify ABIs of 28 of the 29 BNB facets (facet `0x3b7158eaf6d219b6c5f03c29374891bb0d470422` is unverified). The two live topics were matched in the openchain.xyz signature database.
- **Addresses:** diamonds from the official docs and the DefiLlama `apollox` adapter. ALP addresses from `ALP()` on each diamond. Facets from `facetAddresses()`. Admin from `getRoleMember`.
- **Chain coverage:** batched `eth_getCode` on all nine target chains, with code-hash comparison.

Sources: [Aster docs — Direct Contract Interaction](https://docs.asterdex.com/trading/1001x/direct-contract-interaction) · [Aster ALP](https://docs.asterdex.com/earn/overview/aster-alp) · [DefiLlama-Adapters `projects/apollox`](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/apollox/index.js) · [Louper diamond inspector (BNB)](https://louper.dev/diamond/0x1b6F2d3844C6ae7D56ceb3C3643b9060ba28FEb0?network=bsc) · [Sourcify](https://sourcify.dev/)
