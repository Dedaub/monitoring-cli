# Morpho Markets V2 ("Midnight") — Topics, Selectors, Addresses (Ethereum, Base, Robinhood Chain, Arc)

**Status:** verified against live RPC on Ethereum, Base, Robinhood Chain and Arc on 2026-10-30, and the canonical `morpho-org/midnight` repo (commit `7565b9a`, 2026-10-29) and `morpho-org/bundles` repo. Addresses from the `morpho-org/sdks` registry (`packages/morpho-ts/src/addresses.ts`).
**Scope:** the Midnight core contract (fixed-rate, fixed-maturity lending), its on-chain mempool (`Log`), the offer ratifiers, the `EcrecoverAuthorizer`, the `BlueBuyCallbackFactory`, `MidnightBundlesV2`, and the optional periphery (`WhitelistEnterGate`, `BlueFallbackRolling`). Chains: Ethereum (1), Base (8453), Robinhood Chain (4663), Arc (5042). Topics and selectors are chain-agnostic. Addresses are network-specific. Vaults V2 is in [v2.md](v2.md); Morpho Blue is in [v1.md](v1.md); index in [README.md](README.md).

Midnight is a **single immutable singleton per chain** (no proxy; EIP-1967 impl slot `0x0`). Its runtime bytecode is **byte-identical on all four chains** (24557 B, same code hash). Markets are created permissionlessly and are immutable. A market has one loan token, a fixed `maturity`, and 1..N collateral tokens (each with its own LLTV, liquidation cursor and oracle). Lending and borrowing are trades of **credit units / debt units** that settle like zero-coupon bonds at maturity.

Trading is **intent-based**. A maker signs or ratifies an `Offer` off-chain (published through the mempool contract or an off-chain order book). A taker fills it on-chain with `take(...)`, which emits one `Take` log. There is no rate model and no `AccrueInterest`: the price (tick) of the offer sets the fixed rate. Morpho positions Midnight as a new primitive, not a "Blue V2".

Market `id = keccak256(abi.encode(Market))` (`IdLib`). `Market` = `(uint256 chainId, address midnight, address loanToken, (address token, uint256 lltv, uint256 liquidationCursor, address oracle)[] collateralParams, uint256 maturity, uint256 rcfThreshold, address enterGate, address liquidatorGate)`. The `chainId` and `midnight` fields make an id unique per chain.

---

## 0. Contract families

| Contract | Role | Pattern |
|----------|------|---------|
| **Midnight** | Core singleton: markets, `take`, collateral, repay, liquidate, flash loans, fees. All position events. | Immutable |
| Midnight Mempool (`Log`) | Fallback-only contract. It emits `Data(bytes)` with the raw calldata, so makers publish offer payloads on-chain. | Immutable, 120 B |
| EcrecoverRatifier | Validates EIP-712 signed Merkle roots of offers. Maker can `cancelRoot`. | Immutable |
| SetterRatifier | Validates Merkle roots that the maker (or a delegate) ratifies on-chain. | Immutable |
| PriceRatifierV1 / RateRatifierV1 | Like SetterRatifier, plus a price bound / rate bound per offer, and a signature path (`setIsRootRatifiedWithSig`). | Immutable |
| EcrecoverAuthorizer | Sets a Midnight authorization from an EIP-712 signature. | Immutable |
| BlueBuyCallbackFactory | CREATE2 factory for `BlueBuyCallback`: a buy callback that funds Midnight buys from a Morpho Blue supply position. | Immutable |
| MidnightBundlesV2 | Router for maker cancel-and-make and taker flows. It acts on `msg.sender`. No events of its own. | Immutable |
| WhitelistEnterGate(+Factory), BlueFallbackRolling | Optional periphery in the repo. Not in the address registry on 2026-10-30. | — |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Midnight core — user flows

The source names the market-id field `id_` (to avoid indexer clashes). `M` = the `Market` tuple above.

| topic0 | Event |
|--------|-------|
| `0xbd88656d0ee14d32d4f74f814f6ccb5c750a4c542d6fdf83ee00ddca4edebff0` | `Take(address caller, bytes32 offerHash, bytes32 indexed id_, bool offerIsBuy, address indexed maker, bytes32 group, address ratifier, bytes ratifierData, uint256 units, address indexed taker, uint256 buyerAssets, uint256 sellerAssets, uint256 consumed, uint256 buyerPendingFeeIncrease, uint256 sellerPendingFeeDecrease, int256 totalUnitsDelta, address receiver, address payer)` — **the lend/borrow trade** |
| `0x7a5e8e1731f88cf0c25f88fc7d5618e481e87be4d83f614e601850c2ff082fd7` | `Withdraw(address caller, bytes32 indexed id_, uint256 units, address indexed onBehalf, address indexed receiver, uint256 pendingFeeDecrease)` — lender redeems credit |
| `0x8b2d9c5b5a1393c4a278da77a782a77bfd7ef753c26429830b006487d3167088` | `Repay(address indexed caller, bytes32 indexed id_, uint256 units, address indexed onBehalf, address payer)` |
| `0x968f3d07613cff19e0b1a7b034a330cfc3c90e73c1112e14495b79f436a4a074` | `SupplyCollateral(address caller, bytes32 indexed id_, address indexed collateral, uint256 assets, address indexed onBehalf)` |
| `0x626c0b2bb9d8e812f145a6a7bdb09fe8fb92c53781755f343d5fd65c7e27949a` | `WithdrawCollateral(address caller, bytes32 indexed id_, address indexed collateral, uint256 assets, address indexed onBehalf, address receiver)` |
| `0xb137b989b9fd54b984273db8f16364f52f383aaca56076a320c1896e9fc2dad9` | `Liquidate(address caller, bytes32 indexed id_, address indexed collateral, uint256 seizedAssets, uint256 repaidUnits, address indexed borrower, bool postMaturityMode, address receiver, address payer, uint256 badDebt, uint256 latestLossFactor, uint256 latestContinuousFeeCredit)` |
| `0x3a1534fae3196d51e11f8e6ba02e8a834d8eded5eb826d766d3fd048f3c6b83c` | `FlashLoan(address indexed caller, address[] tokens, uint256[] assets, address indexed callback)` |
| `0x8fd212bc8fa18d807a9b47aa2de07104bf036cfcef8ea259157085a1b618a77c` | `UpdatePosition(bytes32 indexed id_, address indexed user, uint256 creditDecrease, uint256 pendingFeeDecrease, uint256 accruedFee)` — loss-factor slashing + continuous-fee accrual on a position |
| `0xdbf3e95a2290945645820c722294f678e0b3522a7dcf3cf2e2870268bf6c9472` | `MarketCreated(M market, bytes32 indexed id_)` — full market params in data |
| `0xbf9d75f869db3f07b85b277c6ef4c58ee36ec3ec222303658012df26a9420d93` | `SetConsumed(address indexed caller, bytes32 indexed group, uint256 amount, address indexed onBehalf)` — maker cancels / caps an offer group |
| `0x50b9eb33249282f66c7ee7f45c0e4f22a839f9b8026310efa855ee7abab13827` | `SetIsAuthorized(address indexed caller, address indexed authorized, bool newIsAuthorized, address indexed onBehalf)` |

### 1.2 Midnight core — admin and fees

| topic0 | Event |
|--------|-------|
| `0x385bc760a35ad4b8b2c11c6a4c6d27daa5e72ce47836b34da36a3f1258ec45ec` | `Constructor(address indexed configurator)` — once, at deploy |
| `0x2b1b0bd62fb5aaaa9f056fbb48d8bcd9d51a528081fc381ab981ce5c0f0b3153` | `SetConfigurator(address indexed configurator)` |
| `0x9993507f53024702e2de1be66f6c48c8957ac708927b86b3bdf4e335f5869470` | `SetFeeSetter(address indexed feeSetter)` |
| `0x95fa75db724442e818e27072c0420043307335fb3e4913b4c371e70cd902c2e2` | `SetFeeClaimer(address indexed feeClaimer)` |
| `0x14bcfba250c945e79a9901378a5d70dbcc7865cac69a6769f3a566efda01aea1` | `SetTickSpacingSetter(address indexed tickSpacingSetter)` |
| `0x297b80e7a896fad470c630f6575072d609bde997260ff3db851939405ec29139` | `EnableLltv(uint256 lltv)` |
| `0xafc3bc0c69f51b1b5ebb2d1dcb58f842f71728ad18fe029e19ac37b9d981a50e` | `EnableLiquidationCursor(uint256 liquidationCursor)` |
| `0x2fdb65e22fe4310a6b7ac73b0733cce84a7b9289fedcef0a7669bb4ea16a5919` | `SetMarketTickSpacing(bytes32 indexed id_, uint256 newTickSpacing)` |
| `0xd316faedf187698c4bd62cf9b5484dd13466d6504d0d98ff5eb0110b2d325e17` | `SetMarketSettlementFee(bytes32 indexed id_, uint256 indexed index, uint256 newSettlementFee)` |
| `0x4a3a913aa0adf6796a2827443c326f4c5e2c345f39314b893d3233751793b824` | `SetDefaultSettlementFee(address indexed loanToken, uint256 indexed index, uint256 newSettlementFee)` |
| `0xbf609558d120b32620da3fe5220a2e268bda00456bf69e25e6a2c517114cce9b` | `SetMarketContinuousFee(bytes32 indexed id_, uint256 newContinuousFee)` |
| `0x57cfac4cdc6c10e16433620e0ab8e58bb0cb760645d7206c700486d8cd3ea769` | `SetDefaultContinuousFee(address indexed loanToken, uint256 newContinuousFee)` |
| `0xd64453ff5184816a23d670b5224717cd441c4a7cd5f4e7dbc30f8511d35f597b` | `ClaimContinuousFee(address indexed caller, bytes32 indexed id_, uint256 amount, address indexed receiver)` |
| `0x9e96510a66432371715fc0021aa4e375a1b788f31ed2732bff0f7b70acaeb8c2` | `ClaimSettlementFee(address indexed caller, address indexed token, uint256 amount, address indexed receiver)` |

### 1.3 Periphery

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x0b76c48be4e2908f4c9d4eabaf7538e91577fd9ae26db46693fa8d861c6a42fb` | `Data(bytes data)` | Midnight Mempool (`Log`) |
| `0x89c061a730f0adcf72de39ebd2a6b128c09e2d856105ef252fffed026c27c5e3` | `CancelRoot(address indexed caller, address indexed maker, bytes32 indexed root)` | EcrecoverRatifier |
| `0x1b3c916383c77df46e76904b45e2acbf60ada4dc6992cfcd731c5e0944800efe` | `SetIsRootRatified(address indexed caller, address indexed maker, bytes32 indexed root, bool newIsRootRatified)` | SetterRatifier, PriceRatifierV1, RateRatifierV1 (same topic0) |
| `0x65821b6e07b03552d964956187851e89c7ed7c4f84356d3257677f60a71eeb79` | `SetIsRootRatifiedWithSig(address caller, address indexed signer, address indexed maker, bytes32 indexed root, uint256 height, bool newIsRootRatified, uint128 signatureNonce, uint128 previousNonce)` | PriceRatifierV1, RateRatifierV1 |
| `0xc48491714b06e8b9f3fb4738d303f217f2fcfa160c3758e804adf1a97ba7b5f5` | `SetIsAuthorized(address indexed caller, address indexed authorizer, address indexed authorized, bool isAuthorized, uint256 nonce, address signer)` | EcrecoverAuthorizer (differs from the core `SetIsAuthorized`) |
| `0x9a14a5e9769934a317b11aa27b66105a356e741f91b4745b0ee909a02db8e019` | `CreateBlueBuyCallback(address indexed caller, address indexed owner, bytes32 salt, address callback)` | BlueBuyCallbackFactory |
| `0xbae999fc435f6200224444d8535f1936f9abd69060fcaec680f690f1810ae36a` | `SetAuthorizationWithSig(address indexed caller, uint256 nonce)` | BlueBuyCallback |
| `0x2ae72b44f59d038340fca5739135a1d51fc5ab720bb02d983e4c5ff4119ca7b8` | `Skim(address indexed caller, address indexed token, uint256 assets)` | BlueBuyCallback |
| `0xa37096a1760ff17750908a93592ea27190c55acede86ffc22cd09b926f132524` | `CreateWhitelistEnterGate(address indexed caller, address indexed gate, address creditRoleSetter, address debtRoleSetter, bool creditOpen, bool debtOpen, bytes32 preSalt)` | WhitelistEnterGateFactory |
| `0xf2f57b1f321dbf6c17fddf67d5b6fea1f65d1b69eef6e844ab06de020cfae20d` | `SetIsWhitelisted(address indexed whitelister, bool creditSide, address indexed account, bool newIsWhitelisted)` | WhitelistEnterGate |
| `0x5a688e1dd9756a8fb6f9121f5bfb867eb485cf594652cab2a837f25c3e43d0d7` | `SetConfig(address caller, address indexed user, bytes32 indexed midnightId, bytes32 indexed blueId, uint256 start, uint256 end, uint256 incentiveAtStart, uint256 incentiveAtEnd, uint256 minRollableAssets, bool enabled)` | BlueFallbackRolling |
| `0x48b0106d0e5756564fec4b993afdd2145168802e7122df03495d5155fb5aa31e` | `Roll(address caller, address indexed user, bytes32 indexed midnightId, bytes32 indexed blueId, bytes32 configId, uint256 debtAssets, uint256 collateralAssets, uint256 incentiveAssets)` | BlueFallbackRolling |

`WhitelistEnterGate` also emits `Constructor(address,address,bool,bool)` `0x90c78884…`, `SetRoleSetter(bool,address)` `0x4919ee79…`, `SetIsWhitelister(bool,address,bool)` `0x61a131d1…` and `SetIsWhitelistedWithSig(…)` `0xa5ca8c32…`.

---

## 2. Function signatures (chain-agnostic)

`M` = `(uint256,address,address,(address,uint256,uint256,address)[],uint256,uint256,address,address)`.
`Offer` = `(M,bool,address,uint256,uint256,uint256,bytes32,address,bytes,address,address,bool,uint128,uint128,uint256)` = `(market, buy, maker, start, expiry, tick, group, callback, callbackData, receiverIfMakerIsSeller, ratifier, reduceOnly, maxUnits, maxAssets, continuousFeeCap)`.

### 2.1 Midnight core — entry points

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6a14c9ef` | `take(Offer offer, bytes ratifierData, uint256 units, address taker, address receiverIfTakerIsSeller, address takerCallback, bytes takerCallbackData)` | `(uint256 buyerAssets, uint256 sellerAssets)`. Fills an offer; emits `Take`. Calls the offer's ratifier (`isRatified`) and optional callbacks. |
| `0xa6db1750` | `withdraw(M market, uint256 units, address onBehalf, address receiver)` | Lender withdraws matured / withdrawable credit. |
| `0x6b210f9e` | `repay(M market, uint256 units, address onBehalf, address callback, bytes data)` | Optional `onRepay` callback. |
| `0x32292d96` | `supplyCollateral(M market, uint256 collateralIndex, uint256 assets, address onBehalf)` | |
| `0xa121e2a9` | `withdrawCollateral(M market, uint256 collateralIndex, uint256 assets, address onBehalf, address receiver)` | |
| `0x9e580092` | `liquidate(M market, uint256 collateralIndex, uint256 seizedAssets, uint256 repaidUnits, address borrower, bool postMaturityMode, address receiver, address callback, bytes data)` | `(uint256 seized, uint256 repaidUnits)`. Optional `onLiquidate` callback. |
| `0x4f80fe10` | `flashLoan(address[] tokens, uint256[] assets, address callback, bytes data)` | Multi-token flash loan; `onFlashLoan` callback. |
| `0xf01fc06c` | `setConsumed(bytes32 group, uint128 amount, address onBehalf)` | Maker cancels / caps an offer group. |
| `0xb78212ab` | `setIsAuthorized(address authorized, bool newIsAuthorized, address onBehalf)` | |
| `0xa3330aa3` | `touchMarket(M market)` | `(bytes32 id)`. Creates the market if new; emits `MarketCreated`. |
| `0x545e513a` | `updatePosition(M market, address user)` | Applies loss factor + continuous fee; emits `UpdatePosition`. |
| `0xac9650d8` | `multicall(bytes[] calls)` | |

### 2.2 Midnight core — admin and views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x9f5f86ae` | `setConfigurator(address)` | Configurator-only. |
| `0xb19805af` | `setFeeSetter(address)` | Configurator-only. |
| `0xc3accd48` | `setFeeClaimer(address)` | Configurator-only. |
| `0xf3ad575e` | `setTickSpacingSetter(address)` | Configurator-only. |
| `0x4d98a93b` | `enableLltv(uint256)` | Configurator-only. |
| `0x8fd76a21` | `enableLiquidationCursor(uint256)` | Configurator-only. |
| `0xf37e9ba4` | `setMarketTickSpacing(bytes32,uint256)` | Tick-spacing setter. |
| `0x9e3ff40a` | `setMarketSettlementFee(bytes32,uint256,uint256)` | Fee setter. |
| `0x5f59ebd8` | `setDefaultSettlementFee(address,uint256,uint256)` | Fee setter. |
| `0x462e59b4` | `setMarketContinuousFee(bytes32,uint256)` | Fee setter. |
| `0x21559e6b` | `setDefaultContinuousFee(address,uint256)` | Fee setter. |
| `0x2abdc15e` | `claimSettlementFee(address token, uint256 amount, address receiver)` | Fee claimer. |
| `0x575272a8` | `claimContinuousFee(M market, uint256 amount, address receiver)` | Fee claimer. |
| `0x93c52062` | `position(bytes32 id, address user)` | `(credit, pendingFee, lastLossFactor, lastAccrual, debt, collateralBitmap)` — all `uint128`. |
| `0xead29b0b` | `marketState(bytes32 id)` | `(totalUnits, lossFactor, withdrawable, continuousFeeCredit, 7× settlementFeeCbp, continuousFee, tickSpacing)`. |
| `0xfc20106c` | `toMarket(bytes32 id)` | `(M)` — resolve an id to its params. |
| `0x5ce648dc` | `isHealthy(M market, bytes32 id, address borrower)` | `(bool)`. |
| `0x2b507df8` / `0x87cf3ef4` / `0x81cbd3ea` / `0x98285e82` | `configurator()` / `feeSetter()` / `feeClaimer()` / `tickSpacingSetter()` | Role views. |
| `0x65e4ad9e` | `isAuthorized(address authorizer, address authorized)` | `(bool)`. |

### 2.3 Periphery

| Selector | Signature | Contract |
|----------|-----------|----------|
| `0x223c4ed6` | `isRatified(Offer offer, bytes ratifierData, address taker)` | All ratifiers (view; called by `take`). |
| `0xbb1f12aa` | `cancelRoot(address maker, bytes32 root)` | EcrecoverRatifier. |
| `0x2fd0e45d` | `setIsRootRatified(address maker, bytes32 root, bool newIsRootRatified)` | SetterRatifier, PriceRatifierV1, RateRatifierV1. |
| `0xb8704f5a` | `setIsRootRatifiedWithSig(address,bytes32,uint256,bool,uint128,uint256,uint8,bytes32,bytes32)` | PriceRatifierV1, RateRatifierV1. |
| `0xda0024bc` | `setIsAuthorized((address,address,bool,uint256,uint256),(uint8,bytes32,bytes32))` | EcrecoverAuthorizer. |
| `0xe4544b6f` | `createBlueBuyCallback(address owner, bytes32 salt)` | BlueBuyCallbackFactory. |
| `0xb19cab0b` | `createWhitelistEnterGate(address,address,bool,bool,bytes32)` | WhitelistEnterGateFactory. |
| `0x1c0bb54d` / `0x6cf21842` | `onBuy(bytes32,M,uint256,uint256,uint256,address,bytes)` / `onSell(bytes32,M,uint256,uint256,uint256,address,address,bytes)` | Callback interface that Midnight calls. |
| `0xdc400c12` | `MIDNIGHT()` | Periphery view: the Midnight address it is bound to. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` on 2026-10-30. Sizes are identical on all four chains.

| Role | Address | Size | Registry deploy block |
|------|---------|------|-----------------------|
| **Midnight** | `0x471686c42792F93528B000beF54bC10E3aa2045f` | 24557 B | 25,798,183 |
| Midnight Mempool (`Log`) | `0xde2d62449301a09A51EbF9326EA60d2e8BF4A8F7` | 120 B | 25,798,183 |
| EcrecoverRatifier | `0xAC439c81CAA6ef4C7B7E8F0110F8CE63A4b6D43e` | 4139 B | 25,798,183 |
| SetterRatifier | `0xb72c416382c8A6399D0765CebfB032F040B00B3c` | 2713 B | 25,798,183 |
| PriceRatifierV1 | `0x5A7CbC4458344fd11E1ED81D7834082a1138f975` | 5234 B | 26,046,045 |
| RateRatifierV1 | `0x14A4cd3D7a28d90D37fd0917EDeaa496E5931095` | 5819 B | 26,046,045 |
| EcrecoverAuthorizer | `0xfC3303119E46AF831CacdBDB6e1A04C9C369ffF7` | 1276 B | 25,798,183 |
| BlueBuyCallbackFactory | `0x172d1FdC5f79bFe1ED46448f18541E591E5c93a7` | 6472 B | 25,798,272 |
| MidnightBundlesV2 | `0x78edB268D228529715744211E11A5d50fd2BDbA4` | 20185 B | 26,133,585 |

Midnight `configurator()` = `0xcba28b38103307ec8da98377fff9816c164f9afa` (the Morpho DAO owner). `feeSetter()` and `feeClaimer()` = `0x0` on 2026-10-30.

## 4. Addresses — Base (chain ID 8453)

| Role | Address | Registry deploy block |
|------|---------|-----------------------|
| **Midnight** | `0xAdedD8ab6dE832766Fedf0FaC4992E5C4D3EA18A` | 48,286,884 |
| Midnight Mempool (`Log`) | `0xdD6DCE32e21f7b020898a8258dA37355b4017993` | 48,286,884 |
| EcrecoverRatifier | `0xd6e70365C8E8DDa9a4ca662C07bbE663b017755E` | 48,286,884 |
| SetterRatifier | `0x800B5F12A61B8198a5a6EfD794Cac6699B294d63` | 48,286,884 |
| PriceRatifierV1 | `0x08a0e69772315652165921D722B3caAea4C326e6` | 51,724,088 |
| RateRatifierV1 | `0x3B2FbA901C88f026BF50A12c8B28484Cd81F9526` | 51,724,088 |
| EcrecoverAuthorizer | `0x292bEa9f1443d54E0E509120c919106765c6a493` | 48,286,884 |
| BlueBuyCallbackFactory | `0x7337f119Eca028bD39E0e543cEf71631D2333425` | 49,544,552 |
| MidnightBundlesV2 | `0x0bF30B530f816a619C3F28a3b9f44C441122555D` | 52,251,677 |

Midnight `configurator()` = `0xcba28b38103307ec8da98377fff9816c164f9afa`.

## 5. Addresses — Robinhood Chain (chain ID 4663)

| Role | Address | Registry deploy block |
|------|---------|-----------------------|
| **Midnight** | `0x6120765Ba5336150BbdDdD0Cd9108B5bFD369632` | 65,366,296 |
| Midnight Mempool (`Log`) | `0xcEF685D4796FA80F71a97e803D2c0b6719F1b4E2` | 65,366,296 |
| EcrecoverRatifier | `0x90B800999e4ACd1bD20283BD450bBd2e06D91F7C` | 65,366,296 |
| SetterRatifier | `0x708d6Bf6F847202a0755bb5636bE663B174242ea` | 65,366,296 |
| PriceRatifierV1 | `0xF65E0be166AAF2F8993e617189beFB452bf38DB1` | 71,228,891 |
| RateRatifierV1 | `0xDd0588d7D3Aaa76a33A7d054B0b107eB3bCD3F11` | 71,228,891 |
| EcrecoverAuthorizer | `0x75FCdD113fe33a8bEd3CD3C35955DE094Bd2bdf8` | 65,366,296 |
| BlueBuyCallbackFactory | `0x53cbCd884CABA07762c72F43283D3fa72de42D4f` | 65,391,242 |
| MidnightBundlesV2 | `0xf2032F94025C921E8b31511650AfA60094ceD32b` | 81,659,699 |

Midnight `configurator()` = `0x060595638692de6ccd47ca04094f1772d3d39728` (the same owner as Morpho Blue on this chain, [v1.md](v1.md) §3.8).

## 6. Addresses — Arc (chain ID 5042)

| Role | Address | Registry deploy block |
|------|---------|-----------------------|
| **Midnight** | `0x208786922BE56fDE2D1Fa60e6b9eC5D723e8d7b0` | 20,320,779 |
| Midnight Mempool (`Log`) | `0x26bded5Fb01373CE875dEa14E52799D04C839C1A` | 20,320,779 |
| EcrecoverRatifier | `0xA3B53aDe6668b6ceC03a9E56a993B47034F43715` | 20,320,779 |
| SetterRatifier | `0x3915156EBFC246Ee9aC3236af561546B7D9D924c` | 20,320,779 |
| PriceRatifierV1 | `0x55163660Ff35955712339d465dc6D9D583dA8ac2` | 22,490,623 |
| RateRatifierV1 | `0x9b11e691E79d6978c78BF8de8B898CDeb89bEADf` | 22,490,623 |
| EcrecoverAuthorizer | `0xe1dccAdc10c35AE9e2207059B233fE5c634CF20f` | 20,320,779 |
| BlueBuyCallbackFactory | `0x9bD11e1EC7bf3520896F8e3e63d4B70f8d6d177E` | 20,322,111 |
| MidnightBundlesV2 | `0xEC9FE35d70E770De5f55392Cc0E8D3125f225f91` | 24,566,124 |

Midnight `configurator()` = `0xcab782bb6a811727b89f09d9b290acba66223ddd` (the same owner as Morpho Blue on this chain, [v1.md](v1.md) §3.9).

---

## 7. Cross-chain summary

| Chain | ID | Midnight | Mempool | Ratifiers (Ecrecover / Setter / Price / Rate) | Bundles |
|-------|----|----------|---------|-----------------------------------------------|---------|
| Ethereum | 1 | `0x471686…2045f` | `0xde2d62…4A8F7` | ✓ ✓ ✓ ✓ | ✓ |
| Base | 8453 | `0xAdedD8…EA18A` | `0xdD6DCE…17993` | ✓ ✓ ✓ ✓ | ✓ |
| Robinhood Chain | 4663 | `0x612076…69632` | `0xcEF685…1b4E2` | ✓ ✓ ✓ ✓ | ✓ |
| Arc | 5042 | `0x208786…8d7b0` | `0x26bded…39C1A` | ✓ ✓ ✓ ✓ | ✓ |
| BNB / Avalanche / Arbitrum / Optimism / Polygon | — | — | — | — | — |

There is **no shared vanity address**: each chain has its own Midnight address. The `morpho-org/sdks` registry lists no Midnight contracts for BNB, Avalanche, Arbitrum, Optimism or Polygon on 2026-10-30 (it lists one more chain outside this scope, Tempo).

---

## 8. Proxies

| Contract | Upgradeable? | Evidence |
|----------|--------------|----------|
| Midnight (all four chains) | **NO** | EIP-1967 impl slot `0x0` on all four chains; identical runtime code hash. Admin power is limited to the role setters (`configurator`, `feeSetter`, `feeClaimer`, `tickSpacingSetter`), LLTV / liquidation-cursor allow-lists and fees. |
| Mempool, ratifiers, EcrecoverAuthorizer, BlueBuyCallbackFactory, MidnightBundlesV2 | **NO** | Plain deployments bound to `MIDNIGHT()` as an immutable. |

There is no `Upgraded(address)` to watch. Watch `SetConfigurator`, `SetFeeSetter`, `SetFeeClaimer`, `SetTickSpacingSetter`, `EnableLltv` and `EnableLiquidationCursor` for governance changes.

---

## 9. Detection invariants & gotchas

1. **No interest accrual event.** The rate is fixed at `take` time by the offer tick. To get rate and size, decode `Take` (`units`, `buyerAssets`, `sellerAssets`). The buyer of units is the lender; the seller is the borrower.
2. **`Take` has three indexed fields only: `id_`, `maker`, `taker`.** `offerIsBuy` tells which side the maker is on. `receiver` and `payer` are in data.
3. **`caller` is often a router.** `MidnightBundlesV2` and callbacks act for users. Attribute to `onBehalf` / `maker` / `taker` / `borrower`, not to `caller` or `tx.from`.
4. **Markets are created lazily.** `MarketCreated` fires on the first `touchMarket` (also called inside entry points). Resolve any `id_` with `toMarket(bytes32)`.
5. **Multi-collateral.** `SupplyCollateral`, `WithdrawCollateral` and `Liquidate` index the `collateral` token. One borrower can hold several collaterals in one market.
6. **Bad debt is socialized by a loss factor.** `Liquidate.badDebt` > 0 raises the market `lossFactor`; lenders see it later as `UpdatePosition.creditDecrease`. Alert on `badDebt > 0`.
7. **`postMaturityMode`** in `Liquidate` marks a liquidation of a borrower who did not repay by maturity, not a health-based liquidation.
8. **Two `SetIsAuthorized` topics.** Core `0x50b9eb33…` (4 fields) vs EcrecoverAuthorizer `0xc4849171…` (6 fields). Filter on the emitter.
9. **The Mempool emits only `Data(bytes)`**, with the raw offer payload. It is high-volume and holds no funds. Exclude it from fund-flow alerts.
10. **`SetIsRootRatified` has one topic0 for three ratifiers.** Filter on the emitter address.
11. **Gates.** A non-zero `enterGate` or `liquidatorGate` in the market tuple restricts who can enter or liquidate (for example a `WhitelistEnterGate`).

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Midnight core topics (chain-agnostic) =====
TOPIC_MID_TAKE                 = '\xbd88656d0ee14d32d4f74f814f6ccb5c750a4c542d6fdf83ee00ddca4edebff0'
TOPIC_MID_WITHDRAW             = '\x7a5e8e1731f88cf0c25f88fc7d5618e481e87be4d83f614e601850c2ff082fd7'
TOPIC_MID_REPAY                = '\x8b2d9c5b5a1393c4a278da77a782a77bfd7ef753c26429830b006487d3167088'
TOPIC_MID_SUPPLY_COLLATERAL    = '\x968f3d07613cff19e0b1a7b034a330cfc3c90e73c1112e14495b79f436a4a074'
TOPIC_MID_WITHDRAW_COLLATERAL  = '\x626c0b2bb9d8e812f145a6a7bdb09fe8fb92c53781755f343d5fd65c7e27949a'
TOPIC_MID_LIQUIDATE            = '\xb137b989b9fd54b984273db8f16364f52f383aaca56076a320c1896e9fc2dad9'
TOPIC_MID_FLASHLOAN            = '\x3a1534fae3196d51e11f8e6ba02e8a834d8eded5eb826d766d3fd048f3c6b83c'
TOPIC_MID_UPDATE_POSITION      = '\x8fd212bc8fa18d807a9b47aa2de07104bf036cfcef8ea259157085a1b618a77c'
TOPIC_MID_MARKET_CREATED       = '\xdbf3e95a2290945645820c722294f678e0b3522a7dcf3cf2e2870268bf6c9472'
TOPIC_MID_SET_CONSUMED         = '\xbf9d75f869db3f07b85b277c6ef4c58ee36ec3ec222303658012df26a9420d93'
TOPIC_MID_SET_IS_AUTHORIZED    = '\x50b9eb33249282f66c7ee7f45c0e4f22a839f9b8026310efa855ee7abab13827'
TOPIC_MID_SET_CONFIGURATOR     = '\x2b1b0bd62fb5aaaa9f056fbb48d8bcd9d51a528081fc381ab981ce5c0f0b3153'
TOPIC_MID_SET_FEE_SETTER       = '\x9993507f53024702e2de1be66f6c48c8957ac708927b86b3bdf4e335f5869470'
TOPIC_MID_SET_FEE_CLAIMER      = '\x95fa75db724442e818e27072c0420043307335fb3e4913b4c371e70cd902c2e2'
TOPIC_MID_ENABLE_LLTV          = '\x297b80e7a896fad470c630f6575072d609bde997260ff3db851939405ec29139'
TOPIC_MID_CLAIM_SETTLEMENT_FEE = '\x9e96510a66432371715fc0021aa4e375a1b788f31ed2732bff0f7b70acaeb8c2'
TOPIC_MID_CLAIM_CONTINUOUS_FEE = '\xd64453ff5184816a23d670b5224717cd441c4a7cd5f4e7dbc30f8511d35f597b'
-- ===== Periphery topics =====
TOPIC_MID_MEMPOOL_DATA         = '\x0b76c48be4e2908f4c9d4eabaf7538e91577fd9ae26db46693fa8d861c6a42fb'
TOPIC_MID_CANCEL_ROOT          = '\x89c061a730f0adcf72de39ebd2a6b128c09e2d856105ef252fffed026c27c5e3'
TOPIC_MID_SET_ROOT_RATIFIED    = '\x1b3c916383c77df46e76904b45e2acbf60ada4dc6992cfcd731c5e0944800efe'
TOPIC_MID_ECRECOVER_AUTHORIZED = '\xc48491714b06e8b9f3fb4738d303f217f2fcfa160c3758e804adf1a97ba7b5f5'
TOPIC_MID_CREATE_BLUE_BUY_CB   = '\x9a14a5e9769934a317b11aa27b66105a356e741f91b4745b0ee909a02db8e019'
-- ===== Selectors (chain-agnostic) =====
SEL_MID_TAKE                   = '\x6a14c9ef'
SEL_MID_WITHDRAW               = '\xa6db1750'
SEL_MID_REPAY                  = '\x6b210f9e'
SEL_MID_SUPPLY_COLLATERAL      = '\x32292d96'
SEL_MID_WITHDRAW_COLLATERAL    = '\xa121e2a9'
SEL_MID_LIQUIDATE              = '\x9e580092'
SEL_MID_FLASHLOAN              = '\x4f80fe10'
SEL_MID_SET_CONSUMED           = '\xf01fc06c'
SEL_MID_TOUCH_MARKET           = '\xa3330aa3'
SEL_MID_TO_MARKET              = '\xfc20106c'
-- ===== Addresses (network-specific) =====
ETH_MIDNIGHT                   = '\x471686c42792f93528b000bef54bc10e3aa2045f'
ETH_MIDNIGHT_MEMPOOL           = '\xde2d62449301a09a51ebf9326ea60d2e8bf4a8f7'
ETH_MIDNIGHT_BUNDLES_V2        = '\x78edb268d228529715744211e11a5d50fd2bdba4'
BASE_MIDNIGHT                  = '\xadedd8ab6de832766fedf0fac4992e5c4d3ea18a'
BASE_MIDNIGHT_MEMPOOL          = '\xdd6dce32e21f7b020898a8258da37355b4017993'
BASE_MIDNIGHT_BUNDLES_V2       = '\x0bf30b530f816a619c3f28a3b9f44c441122555d'
ROBIN_MIDNIGHT                 = '\x6120765ba5336150bbdddd0cd9108b5bfd369632'
ROBIN_MIDNIGHT_MEMPOOL         = '\xcef685d4796fa80f71a97e803d2c0b6719f1b4e2'
ROBIN_MIDNIGHT_BUNDLES_V2      = '\xf2032f94025c921e8b31511650afa60094ced32b'
ARC_MIDNIGHT                   = '\x208786922be56fde2d1fa60e6b9ec5d723e8d7b0'
ARC_MIDNIGHT_MEMPOOL           = '\x26bded5fb01373ce875dea14e52799d04c839c1a'
ARC_MIDNIGHT_BUNDLES_V2        = '\xec9fe35d70e770de5f55392cc0e8d3125f225f91'
```

---

## 11. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from `src/libraries/EventsLib.sol`, `src/interfaces/IMidnight.sol` and the periphery interfaces. All 24 runtime core topic0s and all core selectors occur as `PUSH32` / `PUSH4` constants in the deployed Ethereum bytecode (`Constructor` fires only in init code). Live `eth_getLogs` on the Ethereum Midnight contract (recent 10k blocks) returned only documented topics: `UpdatePosition` 178, `Take` 97, `SupplyCollateral` 52, `WithdrawCollateral` 49, `Repay` 48, `Withdraw` 40, `SetIsAuthorized` 20, `SetConsumed` 8, `MarketCreated` 3. Base (recent 10k blocks) showed the same set. Robinhood Chain (300,000 blocks to 101,793,758, via `https://rpc.mainnet.chain.robinhood.com`) showed the same set plus one `Liquidate` (`0xb137b989…`).
- **Addresses:** from `morpho-org/sdks` `packages/morpho-ts/src/addresses.ts` (keys `midnight`, `midnightMempool`, `midnightBundlesV2`, `midnightBlueBuyCallbackFactory`, `ecrecoverRatifier`, `ecrecoverAuthorizer`, `setterRatifier`, `priceRatifierV1`, `rateRatifierV1`; deploy blocks from the same file). Existence-checked via `eth_getCode` on all four chains: identical sizes per contract. `configurator()` read live; EIP-1967 impl slot read live.
- **Chain coverage:** the registry is the source for absence on BNB, Avalanche, Arbitrum, Optimism and Polygon.

Authoritative sources:
- [`morpho-org/midnight`](https://github.com/morpho-org/midnight) — core + periphery source, audits.
- [`morpho-org/bundles`](https://github.com/morpho-org/bundles) — `MidnightBundlesV2`.
- [`morpho-org/sdks` addresses.ts](https://github.com/morpho-org/sdks/blob/main/packages/morpho-ts/src/addresses.ts)
- [Midnight whitepaper](https://morpho.org/whitepapers/midnight-whitepaper.pdf) · [docs.morpho.org addresses](https://docs.morpho.org/get-started/resources/addresses)
- Explorers: [Etherscan](https://etherscan.io/address/0x471686c42792F93528B000beF54bC10E3aa2045f) · [Basescan](https://basescan.org/address/0xAdedD8ab6dE832766Fedf0FaC4992E5C4D3EA18A)
