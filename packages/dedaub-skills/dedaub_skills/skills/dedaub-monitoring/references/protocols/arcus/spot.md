# Arcus Spot (Stock Token router) — Topics, Selectors, Addresses (Robinhood Chain)

**Status:** verified against live RPC on Robinhood Chain (4663) and the official `arcus-xyz/spot-contracts-abis` repo (2026-07-08) on 2026-10-30. Each ABI in the repo matches the live implementation bytecode. The repo is behind the chain: two proxies were upgraded after it was written, the live `SwapExecuted` event has a new signature, and the live executors are newer contracts that the repo does not list (§6).
**Scope:** the Arcus spot router for Stock Tokens and other tokens: `SwapShell` (entry), `ArcusSettlement` (settlement), RFQ executors, and the wrapped-token system (factory, escrow, beacon tokens). **Robinhood Chain (4663) only.** Topics and selectors are chain-agnostic. Addresses are network-specific. The perps side is in [perps.md](perps.md).

A taker calls `SwapShell.swap`. The shell forwards to `ArcusSettlement.execute`, which calls an approved executor (RFQ maker fill, AMM hop, external route) and checks the balance deltas. A "wrapped token" is a stand-in ERC-20 that a whitelisted maker mints when the real Stock Token is not yet delivered. The `WrappedTokenEscrow` locks the taker's payment until the maker settles the real token or the taker reclaims after the deadline.

---

## 1. Topics (chain-agnostic)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x824a7dbfc9f746ced98e93f691f8e5c68d0a549b6999eeaa16192f903e39aa27` | `SwapExecuted(address indexed taker, address indexed tokenIn, address indexed tokenOut, uint256 minAmountOut, uint256 amountIn, uint256 quotedAmountIn, uint256 quotedAmountOut, uint256 amountOut, uint256 tokenInBenchmarkPrice, uint256 tokenOutBenchmarkPrice, address router, bytes32 routeTag, string, bool success, string reason)` | SwapShell — **live version** (18,013 logs in blocks 99.83 M–101.83 M). The name of the extra `string` field is not public. |
| `0x4b02af496e764b30261032ae2ad58e4f96e73563c59fe32f8401e76531c1a95e` | `SwapExecuted(address indexed taker, address indexed tokenIn, address indexed tokenOut, uint256 minAmountOut, uint256 amountIn, uint256 quotedAmountIn, uint256 quotedAmountOut, uint256 amountOut, uint256 tokenInBenchmarkPrice, uint256 tokenOutBenchmarkPrice, address router, bytes32 routeTag, bool success, string reason)` | SwapShell — version in the ABI repo; not in the live implementation. |
| `0xc0f798d210b2499788857cf350af0f270c83bf310e9f48c4c37a92d6ad025d7a` | `RouterApproval(address indexed router, bool allowed)` | SwapShell |
| `0xdb5598d3123cb9e3dff060521ffda3b5680064f4438b7cc10f4cbce6fff281c2` | `OperatorApproval(address indexed operator, bool allowed)` | SwapShell, ArcusSettlement |
| `0x7dd364aabd6940e14edb6962bd52e62067ca86415fbb3168c541c0efcb514ff8` | `TakerIntentExecuted(address indexed taker, address indexed submitter, address takerSellToken, address takerBuyToken, uint256 sellAmount, uint256 buyAmount, bool wrappedToken)` | ArcusSettlement (14,502 logs in the same window) |
| `0x60e59a94f2e1252cf84fb7981327e680726390b3303455cddfd0e5d4de5f8511` | `ExecutorApproval(address indexed executor, bool allowed)` | ArcusSettlement — **new execution path** |
| `0xa42e52fd0906ecd4cf9c82e35524357bfe7322a6f4cfd693deb521a3c65e04ec` | `WrappedTokenFactorySet(address indexed factory)` | ArcusSettlement |
| `0x811a1093257d19f2157af705ca123673a523e19058164b0b471eca0991ef044f` | `ArcusRfqFilled(bytes32 indexed quoteId, address indexed maker, address indexed taker, address makerBuyToken, address makerSellToken, uint256 makerBuyAmount, uint256 makerSellAmount)` | RFQ executors |
| `0xfc6c5bcd7e5f998a86b0d3860162e921c0384a72412e92b86b0f5faf8289307e` | `WrappedTokenMinted(bytes32 indexed orderId, address indexed maker, address indexed taker, address underlying, address wrappedToken, address takerSellToken, uint256 wrappedTokenAmount, uint256 lockedSellAmount, uint256 settlementDeadline)` | WrappedTokenEscrow |
| `0x20bc356afc11061310969cda248573c18dbfdc77f1b4a6f2bfb5e693d55728a6` | `WrappedTokenSettled(bytes32 indexed orderId, address indexed maker, address indexed taker, address caller, address takerSellToken, uint256 wrappedTokenAmount, uint256 releasedSellAmount)` | WrappedTokenEscrow |
| `0xbf098c8db9ce468b1c5a2b118dc0f2a858e7d7c742a0207d6b9f1f7f0eb7c176` | `WrappedTokenReclaimed(bytes32 indexed orderId, address indexed maker, address indexed taker, address caller, address takerSellToken, uint256 wrappedTokenAmount, uint256 returnedSellAmount)` | WrappedTokenEscrow — **maker failed to deliver** |
| `0xbd9644d3d29ad9dc8e704295dcb10df081f6985328e54317469a6e5b71e93bac` | `IssuerApproval(address indexed maker, bool approved)` | WrappedTokenEscrow |
| `0x2d6b2ea4980612abae02cd41cb8bf93b2a9ad662cdd0c3111bb2373eeb5c27e7` | `MintageCapSet(address indexed wrappedToken, address indexed maker, address indexed caller, uint256 cap)` | WrappedTokenEscrow |
| `0xba02abffa5250169e449403b905da1c93de465b9544be0c1ef7d06397aca4568` | `SettlementOperatorAllowed(address indexed operator, bool allowed)` | WrappedTokenEscrow |
| `0x3e3c5e6d5b512eaa5d5a80669846cfbaf8bde70fc6f7a3be9828cffc9ba5f1db` | `ExecutorSet(address indexed executor)` | WrappedTokenEscrow |
| `0x7eaef3db6130a1d90b5e60fefcf6bf1f83de58e4a7a7f6f4ac2e09961499a08d` | `SettlementWindowSet(uint256 settlementWindow)` | WrappedTokenEscrow |
| `0x5684977defe28de2532e8f9131f32665535ef5a327a76e352cff2bf988585004` | `GlobalReclaimWindowSet(uint256 globalReclaimWindow)` | WrappedTokenEscrow |
| `0x47cdbd9ccb21e8c42b64c67901cd6369386d9c327365e6af6d4e479add31095e` | `WrappedTokenCreated(address indexed underlying, address indexed wrappedToken)` | WrappedTokenFactory |
| `0xa585aec3a6cb0e1a084ed18c7638024e40cc3e3ea815166e2cb6fc17d7f1392b` | `EscrowSet(address indexed escrow)` | WrappedTokenFactory |
| `0x3b539a862335f9eb33dd4373bea36cd6248d982fae531a257a09ec3242c15f60` | `DeliveryAuthorized(address indexed authority, address indexed taker, uint256 amount)` | each WrappedToken |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | every proxy + beacon |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | every owned contract |

Live sample, blocks 99.83 M–101.83 M: WrappedTokenEscrow `WrappedTokenMinted` 1,773 and `WrappedTokenSettled` 1,772.

## 2. Function signatures (chain-agnostic)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xccaca780` | `swap((address,address,address,address,uint256,uint256,uint256,uint256,uint256,uint256,bytes32),(address,uint256,uint256,uint8,bytes32,bytes32)[],bytes)` | SwapShell entry. `(uint256)`. Present in the live implementation. |
| `0xc3c64674` / `0x558a7297` | `setRouter(address,bool)` / `setOperator(address,bool)` | SwapShell owner. |
| `0xe155403b` | `execute((address,address,address,uint256,uint256,bool,uint256,uint256),bytes,(address,address,uint256,address,uint256,bytes)[])` | ArcusSettlement. `(uint256)`. |
| `0x1e1bff3f` | `setExecutor(address,bool)` | ArcusSettlement owner. |
| `0xdff11d77` | `setWrappedTokenFactory(address)` | ArcusSettlement owner. |
| `0xb68a5f04` | `execute(address,address,uint256,address,uint256,bytes)` | RFQ executors. `(uint256)`. |
| `0x0d2e1f94` | `mintWrappedTokens(bytes32,address,address,address,address,uint256,uint256,address)` | Escrow. `(uint256)`. |
| `0xcf633cae` | `settleWrappedToken(bytes32,uint256,uint256,bytes)` | Escrow. Maker delivers the real token. |
| `0xff50af38` | `reclaimSellToken(bytes32)` | Escrow. Taker reclaims after the deadline. |
| `0x1c788c1a` / `0xc413d2dc` / `0x2dc2e424` | `setApprovedIssuer(address,bool)` / `setMintageCap(address,address,uint256)` / `setOwnMintageCap(address,uint256)` | Escrow admin / maker. |
| `0xebeeabbd` / `0x1c3c0ea8` / `0x403bfbf7` / `0x5e6e9a6b` | `setSettlementOperator(address,bool)` / `setExecutor(address)` / `setSettlementWindow(uint256)` / `setGlobalReclaimWindow(uint256)` | Escrow owner. |
| `0x4f9215c4` / `0xc10c3546` | `createWrappedToken(address)` / `setEscrow(address)` | WrappedTokenFactory. |
| `0x40c10f19` / `0x9dc29fac` / `0x74fdcf61` | `mint(address,uint256)` / `burn(address,uint256)` / `authorizeDelivery(address,uint256)` | WrappedToken (escrow only). |
| `0x3659cfe6` | `upgradeTo(address)` | WrappedToken beacon owner. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | UUPS proxies. |

## 3. Addresses — Robinhood Chain (chain ID 4663)

All verified with `eth_getCode` on 2026-10-30. Owner of every listed proxy and of the beacon = Safe 2-of-5 `0x81b80499c396a9931b9e44953425a82c1b2541bd` (the same Safe that administers pTokens).

| Role | Address | Pattern / current implementation |
|------|---------|----------------------------------|
| **SwapShell** | `0x4262efBd176F02824af27010bEa218429c33c7E8` | ERC1967 (130 B) → `0x2b66ec2f62ec618dec1d83cc7af1b5c815e45966` |
| **ArcusSettlement** | `0x006102b16A04c20306A28b652745D3973D7D24fa` | ERC1967 → `0xdfe851005a37107209d30f9b124467807f3aa86f` |
| RfqExecutor (repo) | `0xf4da3c42D9c9F494d4688A0112a9DB3C9b18a914` | Not a proxy (2,688 B). No logs in the sample. |
| WrappedTokenRfqExecutor | `0x43cF43056C33128329B54F66CA3649CF2975f1A6` | ERC1967 → `0x4829d52f7099537e38ee0b08c133f96810df67e2`. No logs in the sample. |
| **WrappedTokenFactory** | `0x8bc71aE8EaC8B25F30c2990930Cc3A80E72e169e` | ERC1967 → `0xd3fd212d087e084b748ff4d00d936a9f1e8936a9` |
| **WrappedTokenEscrow** | `0x6d56Ab475069B7E93886b3D3F06c5435B87Ba158` | ERC1967 → `0xcc31b65f43672a4151b30a6e181e0e8c1b1bc9b2` |
| WrappedToken beacon | `0x27fEB332759F8d2f351D7fC72D29af37664ffd77` | `UpgradeableBeacon` → `0x95b58BF6C2b1d5f4D1786f1B0dEa42e80132833E` |

Executors approved on ArcusSettlement (`ExecutorApproval(…, true)` logs; none revoked). The last five are not in the ABI repo:

| Executor | Pattern | Live topic (blocks 101.33 M–101.83 M) |
|----------|---------|----------------------------------------|
| `0xf4da3c42d9c9f494d4688a0112a9db3c9b18a914` | immutable | — |
| `0x43cf43056c33128329b54f66ca3649cf2975f1a6` | ERC1967 | — |
| `0x988965b218613c9d01aef5b9a4ed9b4c213b7ce9` | immutable (1,620 B) | — |
| `0x73318e03ba5293ae754d377868f60949e0a7475a` | ERC1967 → `0xf92f6e94…6116` | `ArcusRfqFilled` 1,777 — **the live RFQ executor** |
| `0x040234dfd2d32336e3cd9534fa1909adab002cea` | ERC1967 → `0x677bec1b…5a44` | `0xaf5645b54e3df0b3ea864b2a5b218650fd9e52030be2d2a8e563730b63009dcd` 719 (name not public) |
| `0x7e0aab35a05e63381e7e89f34cbb9df1f5f1baa9` | ERC1967 → `0xc3dd348d…c99c` | `UniswapHopFilled(address,address,address,uint8,uint24,uint256,uint256)` `0x81e1ab9bf6385fd30011247cac2113b08f5a3a722b6ae04fb8b507e7cc73a351` 1,340 |
| `0x2706364aacd925c04061eaba5b3496359d4e2b62` | ERC1967 → `0xe84e24f9…93b1` | — |
| `0xd3fd4a5eda2704a98bdf579008557d4f0272c456` | ERC1967 → `0x9f69523c…7e40` | `FeePaid(address,address,address,uint256)` `0x1b37fcc57f4b6029ca7b3a70af0104811f67c72fe73e8043575f03a01e056631` 4,169; `FeeHopFilled(address,address,uint256,uint256)` `0xb5f6cb09d7c7067c664796642d6a7a3fbeffafd3ea11170af575c19c6f225f38` 3,509 |

The `UniswapHopFilled`, `FeePaid` and `FeeHopFilled` names come from the public signature database; their `indexed` flags are not known.

## 4. Cross-chain summary

The spot contracts exist on **Robinhood Chain (4663) only**. `eth_getCode` returns `0x` for SwapShell, ArcusSettlement, WrappedTokenEscrow and WrappedTokenFactory on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon and Arc (2026-10-30).

## 5. Proxies — upgrade history (`Upgraded` block → implementation)

| Proxy | History |
|-------|---------|
| SwapShell | 50,527 `0x1d482c4a45c7db200cf01f6e1b101fe697c788c4` → 159,183 `0x8b4420fb0b3c366d1661b88466613f161d619f34` (repo value) → 9,871,610 `0xe96f5e6bc61f5a669e14e7bc490b2e9b831e039e` → 18,388,023 `0x6747b4986e7d184ef45e532c0ea26c3a6fda3ee3` → 64,677,027 `0x2b66ec2f62ec618dec1d83cc7af1b5c815e45966` |
| ArcusSettlement | 50,528 `0x28fe3236da3cea9afdf1045c19e1139a7da89457` (repo value) → 17,624,134 `0x1cf818fbb2f51d03c3f57cdc562fd0f29f945fef` → 18,388,023 `0xf31022dd374221b220b619c6d8eddb3d4ee968b4` → 35,489,018 `0xdf8df96a28cc5a99dd3fdd82f67eecf796531c79` → 52,175,800 `0xdfe851005a37107209d30f9b124467807f3aa86f` |
| WrappedTokenEscrow | 50,534 `0x1b20f2e457ebcc7a9cafa2e25c80c8becd514e51` → 159,195 `0xcc31b65f43672a4151b30a6e181e0e8c1b1bc9b2` |
| WrappedTokenRfqExecutor / WrappedTokenFactory / WrappedToken beacon | one `Upgraded` each at deployment (50,533–50,534) |

Upgrade auth: UUPS `upgradeToAndCall` and beacon `upgradeTo`, owner-gated; owner = Safe `0x81b8…41bd`.

## 6. Detection invariants & gotchas

1. **Use the live `SwapExecuted` topic `0x824a7dbf…`.** The ABI repo still lists `0x4b02af49…`, which the live SwapShell does not emit. The live event has one more `string` before `success`.
2. **`success = false` swaps still emit `SwapExecuted`.** Filter on the `success` field and read `reason`.
3. **New executors appear by `ExecutorApproval`.** The settlement contract trusts any approved executor with token balances during `execute`. Alert on `ExecutorApproval(executor, true)`.
4. **Wrapped tokens are IOUs.** `WrappedTokenMinted` locks the taker's payment. `WrappedTokenSettled` releases it to the maker. `WrappedTokenReclaimed` means the maker did not deliver. Wrapped tokens cannot be transferred by holders.
5. **`OperatorApproval` topic0 is shared** by SwapShell and ArcusSettlement. Key on emitter.
6. **The repo's `RfqExecutor` and `WrappedTokenRfqExecutor` show no logs in the sample.** The live RFQ fills come from `0x7331…475a`.

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_SPOT_SWAP_EXECUTED_LIVE     = '\x824a7dbfc9f746ced98e93f691f8e5c68d0a549b6999eeaa16192f903e39aa27'
TOPIC_SPOT_SWAP_EXECUTED_REPO     = '\x4b02af496e764b30261032ae2ad58e4f96e73563c59fe32f8401e76531c1a95e'
TOPIC_SPOT_TAKER_INTENT_EXECUTED  = '\x7dd364aabd6940e14edb6962bd52e62067ca86415fbb3168c541c0efcb514ff8'
TOPIC_SPOT_EXECUTOR_APPROVAL      = '\x60e59a94f2e1252cf84fb7981327e680726390b3303455cddfd0e5d4de5f8511'
TOPIC_SPOT_ROUTER_APPROVAL        = '\xc0f798d210b2499788857cf350af0f270c83bf310e9f48c4c37a92d6ad025d7a'
TOPIC_SPOT_ARCUS_RFQ_FILLED       = '\x811a1093257d19f2157af705ca123673a523e19058164b0b471eca0991ef044f'
TOPIC_SPOT_WT_MINTED              = '\xfc6c5bcd7e5f998a86b0d3860162e921c0384a72412e92b86b0f5faf8289307e'
TOPIC_SPOT_WT_SETTLED             = '\x20bc356afc11061310969cda248573c18dbfdc77f1b4a6f2bfb5e693d55728a6'
TOPIC_SPOT_WT_RECLAIMED           = '\xbf098c8db9ce468b1c5a2b118dc0f2a858e7d7c742a0207d6b9f1f7f0eb7c176'
TOPIC_SPOT_WT_CREATED             = '\x47cdbd9ccb21e8c42b64c67901cd6369386d9c327365e6af6d4e479add31095e'
TOPIC_SPOT_ISSUER_APPROVAL        = '\xbd9644d3d29ad9dc8e704295dcb10df081f6985328e54317469a6e5b71e93bac'
-- ===== Selectors (chain-agnostic) =====
SEL_SPOT_SWAP                     = '\xccaca780'
SEL_SPOT_SETTLEMENT_EXECUTE       = '\xe155403b'
SEL_SPOT_SET_EXECUTOR             = '\x1e1bff3f'
SEL_SPOT_SETTLE_WRAPPED_TOKEN     = '\xcf633cae'
SEL_SPOT_RECLAIM_SELL_TOKEN       = '\xff50af38'
-- ===== Addresses (Robinhood Chain 4663) =====
RH_ARCUS_SWAP_SHELL               = '\x4262efbd176f02824af27010bea218429c33c7e8'
RH_ARCUS_SETTLEMENT               = '\x006102b16a04c20306a28b652745d3973d7d24fa'
RH_ARCUS_RFQ_EXECUTOR_LIVE        = '\x73318e03ba5293ae754d377868f60949e0a7475a'
RH_ARCUS_WT_ESCROW                = '\x6d56ab475069b7e93886b3d3f06c5435b87ba158'
RH_ARCUS_WT_FACTORY               = '\x8bc71ae8eac8b25f30c2990930cc3a80e72e169e'
RH_ARCUS_WT_BEACON                = '\x27feb332759f8d2f351d7fc72d29af37664ffd77'
RH_ARCUS_ADMIN_SAFE               = '\x81b80499c396a9931b9e44953425a82c1b2541bd'
```

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed as `keccak256(signature)` from the official ABIs and matched against the live implementation bytecode (all selectors present; the repo `SwapExecuted` is the only repo event absent from the live SwapShell). The live `SwapExecuted` signature was rebuilt from a sample log layout and matched by `keccak256`. Executor event names come from the public signature database.
- **Addresses:** from the official `deployments.json`; implementations, owners and executors read live (EIP-1967 slot, `owner()`, `ExecutorApproval` logs). Upgrade history from `Upgraded` logs over the full chain range.
- **Chain coverage:** `eth_getCode` on the other seven target chains and Arc returned `0x`.

Sources:
- [arcus-xyz/spot-contracts-abis](https://github.com/arcus-xyz/spot-contracts-abis)
- [Arcus docs — Spot Router](https://docs.arcus.xyz/concepts/spot-router.md) · [Spot RFQ](https://docs.arcus.xyz/concepts/spot-rfq.md) · [Wrapped tokens](https://docs.arcus.xyz/concepts/wrapped-tokens.md)
- Explorer: [Robinhood Chain Blockscout — SwapShell](https://robinhoodchain.blockscout.com/address/0x4262efBd176F02824af27010bEa218429c33c7E8)
