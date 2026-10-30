# Polymarket CTF Exchange V2 + pUSD — Topics, Selectors, Addresses (Polygon PoS)

**Status:** verified against live Polygon RPC and the canonical `Polymarket/ctf-exchange-v2` repo on 2026-10-30.
**Scope:** CTF Exchange V2, NegRisk CTF Exchange V2, the pUSD collateral token (`CollateralToken`), its on/off ramps, and the two CTF collateral adapters on Polygon PoS (137). Topics and selectors are chain-agnostic. Addresses are network-specific. **Polygon-only.** None of these addresses has code on the other eight chains (§4).

CTF Exchange V2 is the **main trading venue** on 2026-10-30. It took over from the V1 exchanges around May 2026. In a sample of the last 40 Polygon blocks, the two V2 exchanges emitted about 2,700 `OrderFilled` logs. The V1 exchanges emitted none.

V2 settles in **pUSD** ("Polymarket USD", `CollateralToken`, 6 decimals). pUSD wraps native USDC and USDC.e 1:1. The backing is held in a separate vault. Outcome tokens are still the Gnosis CTF tokens at `0x4d97…6045`, with **USDC.e** (binary) or **WCOL** (neg-risk) as CTF collateral. The exchanges reach the CTF through a collateral adapter (`getOutcomeTokenFactory()`). The adapter unwraps pUSD to USDC.e before a CTF split, and wraps it back after a merge or redeem.

The exchanges, ramps and adapters are **immutable**. pUSD is a **UUPS proxy** (Solady ERC-1967).

---

## 0. Contract families & versions

| Contract | Role | Proxy? |
|----------|------|--------|
| **CTFExchangeV2** | Binary-market CLOB settlement in pUSD. | Immutable |
| **NegRiskCtfExchangeV2** | Neg-risk CLOB settlement. Same bytecode family as CTFExchangeV2. | Immutable |
| **CollateralToken (pUSD)** | ERC-20 collateral. Wraps USDC / USDC.e. Minter and wrapper roles. | UUPS (ERC-1967) |
| **CollateralOnramp** / **CollateralOfframp** | Public wrap (asset → pUSD) / unwrap (pUSD → asset). | Immutable |
| **PermissionedRamp** | Wrap / unwrap gated by EIP-712 witness signatures. | Immutable |
| **CtfCollateralAdapter** | pUSD ↔ CTF split / merge / redeem for binary markets. | Immutable |
| **NegRiskCtfCollateralAdapter** | pUSD ↔ NegRiskAdapter split / merge / convert / redeem. | Immutable |
| pUSD backing vault | Holds the USDC.e / USDC behind pUSD. | ERC-1967 proxy |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 CTFExchangeV2 / NegRiskCtfExchangeV2
| topic0 | Event |
|--------|-------|
| `0x55bb3cade9d43b798a4fe5ffdd05024b2d7870df53920673bfc7e68047cd0ab1` | `FeeCharged(address indexed, uint256)` |
| `0x27aae5db36d94179909d019ae0b1ac7c16d96d953148f63c0f6a0a9c8ead79ee` | `FeeReceiverUpdated(address indexed)` |
| `0xe380d7c3967dd06cc7c01db8b17332a1d806fd18f63206dcbd12aaef455c7ff2` | `MaxFeeRateUpdated(uint256)` |
| `0xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc` | `NewAdmin(address indexed, address indexed)` |
| `0xf1e04d73c4304b5ff164f9d10c7473e2a1593b740674a6107975e2a7001c1e5c` | `NewOperator(address indexed, address indexed)` |
| `0xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee` | `OrderFilled(bytes32 indexed, address indexed, address indexed, uint8, uint256, uint256, uint256, uint256, bytes32, bytes32)` |
| `0xb766aa470f20b094f26a9a14ea5bf63a60af51703c15776e2e739b6a0428adf6` | `OrderPreapprovalInvalidated(bytes32 indexed)` |
| `0xe92c22722d9c284034b6c9f5aaec018edb3e593c0e084900b6b9d390a1182a0b` | `OrderPreapproved(bytes32 indexed)` |
| `0x174b3811690657c217184f89418266767c87e4805d09680c39fc9c031c0cab7c` | `OrdersMatched(bytes32 indexed, address indexed, uint8, uint256, uint256, uint256)` |
| `0x787a2e12f4a55b658b8f573c32432ee11a5e8b51677d1e1e937aaf6a0bb5776e` | `RemovedAdmin(address indexed, address indexed)` |
| `0xf7262ed0443cc211121ceb1a80d69004f319245615a7488f951f1437fd91642c` | `RemovedOperator(address indexed, address indexed)` |
| `0x203c4bd3e526634f661575359ff30de3b0edaba6c2cb1eac60f730b6d2d9d536` | `TradingPaused(address indexed)` |
| `0xa1e8a54850dbd7f520bcc09f47bff152294b77b2081da545a7adf531b7ea283b` | `TradingUnpaused(address indexed)` |
| `0x8c8acf678b7cd311e3b5768c92794d63943684862fdea390856e14d9e2a9ef88` | `UserPauseBlockIntervalUpdated(uint256, uint256)` |
| `0xa3e76126f19eb25001b29726d2a9502b6377938633d2d6a955107dd442e7a14a` | `UserPaused(address indexed, uint256)` |
| `0x1419d4111b5c8636aecff843bf618525f4f8e1aa6898a14357021d68dde8af12` | `UserUnpaused(address indexed)` |

`OrderFilled` and `OrdersMatched` keep their V1 names but have **new signatures and new topic0** (`side` and one `tokenId` replace `makerAssetId` / `takerAssetId`; `builder` and `metadata` are new). `FeeCharged` is also new (`address,uint256`). A V1 topic0 filter does not match V2 logs.

### 1.2 CollateralToken (pUSD)
| topic0 | Event |
|--------|-------|
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed, address indexed, uint256)` |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64)` |
| `0xfa7b8eab7da67f412cc9575ed43464468f9bfbae89d1675917346ca6d8fe3c92` | `OwnershipHandoverCanceled(address indexed)` |
| `0xdbf36a107da19e49527a7176a1babf963b4b0ff8cde35ee35d6cd8f1f9ac7e1d` | `OwnershipHandoverRequested(address indexed)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed, address indexed)` |
| `0x3af790fafda720819b2fc6e15090606e81154e0ac9a92d38ecad006d99d20ecc` | `Rescued(address indexed, address indexed, uint256)` |
| `0x715ad5ce61fc9595c7b415289d59cf203f23a94fa06f04af7e489a0a76e1fe26` | `RolesUpdated(address indexed, uint256 indexed)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed, address indexed, uint256)` |
| `0x18b42b684d0b621cc609f4d888916e5ed9e934a476259ec1c11ec116f2b9aa7f` | `Unwrapped(address indexed, address indexed, address indexed, uint256)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed)` |
| `0xc00a5c84859ae82a7f5e6a2773283fb525335d5b3195f61174aa1ecc7e15dd84` | `Wrapped(address indexed, address indexed, address indexed, uint256)` |

The current implementation adds `Rescued` to the original V2 implementation. All other events are unchanged.

### 1.3 Ramps and adapters (Solady `OwnableRoles` + `Pausable`)
| topic0 | Event |
|--------|-------|
| `0xfa7b8eab7da67f412cc9575ed43464468f9bfbae89d1675917346ca6d8fe3c92` | `OwnershipHandoverCanceled(address indexed)` |
| `0xdbf36a107da19e49527a7176a1babf963b4b0ff8cde35ee35d6cd8f1f9ac7e1d` | `OwnershipHandoverRequested(address indexed)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed, address indexed)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address)` |
| `0x715ad5ce61fc9595c7b415289d59cf203f23a94fa06f04af7e489a0a76e1fe26` | `RolesUpdated(address indexed, uint256 indexed)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address)` |

Onramp, Offramp, PermissionedRamp, CtfCollateralAdapter and NegRiskCtfCollateralAdapter emit only these admin events. The money movement shows as pUSD `Wrapped` / `Unwrapped` and ERC-20 `Transfer` on the pUSD contract, and as CTF / NegRiskAdapter split, merge and redeem events (see `v1.md`).

### 1.4 topic0 collisions
- `NewAdmin`, `RemovedAdmin`, `NewOperator`, `RemovedOperator`, `TradingPaused`, `TradingUnpaused` are the same topic0 as V1. Filter by emitter.
- `OrderFilled` / `OrdersMatched` / `FeeCharged` V2 topic0 are shared with the PositionManager `Exchange` (`position_manager.md`). Filter by emitter.
- `Paused(address)` / `Unpaused(address)` here are Solady-style with the **target** as argument (the adapters pause per-asset). They share topic0 with OpenZeppelin `Paused(address account)`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

V2 order struct: `Order = (uint256 salt, address maker, address signer, uint256 tokenId, uint256 makerAmount, uint256 takerAmount, uint8 side, uint8 signatureType, uint256 timestamp, bytes32 metadata, bytes32 builder, bytes signature)`. Below it is written as `ORDER2`. V2 drops `taker`, `expiration`, `nonce` and `feeRateBps`. It adds `timestamp`, `metadata` and `builder`.

### 2.1 CTFExchangeV2 / NegRiskCtfExchangeV2
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3c2b4399` | `matchOrders(bytes32,(uint256,address,address,uint256,uint256,uint256,uint8,uint8,uint256,bytes32,bytes32,bytes),(uint256,address,address,uint256,uint256,uint256,uint8,uint8,uint256,bytes32,bytes32,bytes)[],uint256,uint256[],uint256,uint256[])` | `matchOrders(conditionId, ORDER2 taker, ORDER2[] makers, takerFill, makerFills[], takerFee, makerFees[])`. Operator only. The only settlement entry point (no `fillOrder`). |
| `0xe3a5ced5` | `preapproveOrder((uint256,address,address,uint256,uint256,uint256,uint8,uint8,uint256,bytes32,bytes32,bytes))` | Emits `OrderPreapproved`. |
| `0x437f1994` | `invalidatePreapprovedOrder(bytes32)` | Emits `OrderPreapprovalInvalidated`. |
| `0xc0c3132c` | `pauseUser()` | Caller self-pause. Emits `UserPaused`. Takes effect after `userPauseBlockInterval`. |
| `0x4cce30c9` | `unpauseUser()` | Emits `UserUnpaused`. |
| `0x1031e36e` | `pauseTrading()` | Admin. Emits `TradingPaused`. |
| `0x456068d2` | `unpauseTrading()` | Admin. Emits `TradingUnpaused`. |
| `0xefdcd974` | `setFeeReceiver(address)` | Admin. Emits `FeeReceiverUpdated`. |
| `0x8cda96de` | `setMaxFeeRate(uint256)` | Admin. Emits `MaxFeeRateUpdated`. |
| `0xcd4d8cb4` | `setUserPauseBlockInterval(uint256)` | Admin. Emits `UserPauseBlockIntervalUpdated`. |
| `0x9870d7fe` | `addOperator(address)` | Admin. Emits `NewOperator`. |
| `0xac8a584a` | `removeOperator(address)` | Admin. Emits `RemovedOperator`. |
| `0x70480275` | `addAdmin(address)` | Admin. Emits `NewAdmin`. |
| `0x1785f53c` | `removeAdmin(address)` | Admin. Emits `RemovedAdmin`. |
| `0x3d6d3598` | `renounceOperatorRole()` | Caller drops its operator role. |
| `0x3d861a4d` | `hashOrder((uint256,address,address,uint256,uint256,uint256,uint8,uint8,uint256,bytes32,bytes32,bytes))` | view |
| `0x46423aa7` | `getOrderStatus(bytes32)` | view |
| `0x5c1548fb` | `getCollateral()` | view. pUSD. |
| `0x3b521d78` | `getCtf()` | view. CTF `0x4d97…6045` on both exchanges. |
| `0x03cee3df` | `getCtfCollateral()` | view. USDC.e (binary) or WCOL (neg-risk). |
| `0x29cf67f2` | `getOutcomeTokenFactory()` | view. The collateral adapter. |
| `0xe8a35392` | `getFeeReceiver()` | view |
| `0x4a2a11f5` | `getMaxFeeRate()` | view |
| `0x58d8b6bb` | `getProxyWalletAddress(address)` | view |
| `0x70bf48e5` | `getSafeWalletAddress(address)` | view |
| `0x28872101` | `isUserPaused(address)` | view |
| `0x6d70f7ae` | `isOperator(address)` | view |

### 2.2 CollateralToken (pUSD)
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x62355638` | `wrap(address,address,uint256)` | Wrapper role (ramps). `wrap(asset, to, amount)`. Emits `Wrapped`. |
| `0x8cc7104f` | `unwrap(address,address,uint256)` | Wrapper role. Emits `Unwrapped`. |
| `0xb97b57c7` | `wrap(address,address,uint256,address,bytes)` | Legacy 5-argument overload (callback ignored). Used by the deployed ramps and adapters. |
| `0xd600875d` | `unwrap(address,address,uint256,address,bytes)` | Legacy 5-argument overload. |
| `0x40c10f19` | `mint(address,uint256)` | Minter role. |
| `0x42966c68` | `burn(uint256)` | Minter role. |
| `0x983b2d56` | `addMinter(address)` | Owner. Emits `RolesUpdated`. |
| `0x3092afd5` | `removeMinter(address)` | Owner. |
| `0x26b09c29` | `addWrapper(address)` | Owner. Emits `RolesUpdated`. |
| `0xe914d494` | `removeWrapper(address)` | Owner. |
| `0xb252d405` | `rescue(address[],address[],uint256[])` | Owner. Emits `Rescued`. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | Owner. Emits `Upgraded`. |
| `0xf2fde38b` | `transferOwnership(address)` | Owner. |

pUSD views: `USDC()` = `0x89a30271`, `USDCE()` = `0x195187e1`, `VAULT()` = `0x411557d1`.

### 2.3 Ramps
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5f02639c` | `wrap(address,address,uint256,uint256,uint256,bytes)` | PermissionedRamp. Needs a witness signature. |
| `0x117211b1` | `unwrap(address,address,uint256,uint256,uint256,bytes)` | PermissionedRamp. Needs a witness signature. |
| `0x59e26be1` | `addWitness(address)` | Admin. |
| `0xee2f13cd` | `removeWitness(address)` | Admin. |
| `0x76a67a51` | `pause(address)` | Admin. Pauses one asset. Emits `Paused`. |
| `0x57b001f9` | `unpause(address)` | Admin. Emits `Unpaused`. |

CollateralOnramp: `wrap(address,address,uint256)` = `0x62355638`. CollateralOfframp: `unwrap(address,address,uint256)` = `0x8cc7104f`. Both are public and pausable per asset.

### 2.4 CtfCollateralAdapter / NegRiskCtfCollateralAdapter
| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x72ce4275` | `splitPosition(address,bytes32,bytes32,uint256[],uint256)` | Both adapters. pUSD in → CTF tokens out. |
| `0x9e7212ad` | `mergePositions(address,bytes32,bytes32,uint256[],uint256)` | Both adapters. CTF tokens in → pUSD out. |
| `0x01b7037c` | `redeemPositions(address,bytes32,bytes32,uint256[])` | Both adapters. |
| `0xa3d7da1d` | `splitPosition(bytes32,uint256)` | NegRisk adapter only. |
| `0xb10c5c17` | `mergePositions(bytes32,uint256)` | NegRisk adapter only. |
| `0xc64748c4` | `convertPositions(bytes32,uint256,uint256)` | NegRisk adapter only. |
| `0xdbeccb23` | `redeemPositions(bytes32,uint256[])` | NegRisk adapter only. |
| `0x76a67a51` | `pause(address)` | Admin. |

---

## 3. Addresses — Polygon PoS (chain ID 137)

All verified with `eth_getCode` (non-empty) on `https://polygon-bor-rpc.publicnode.com` on 2026-10-30. Wiring read live.

| Role | Address | One-liner |
|------|---------|-----------|
| **CTFExchangeV2** | `0xe111180000d2663c0091e4f400237545b87b996b` | `getCtfCollateral()` = USDC.e, `getOutcomeTokenFactory()` = CtfCollateralAdapter. |
| **NegRiskCtfExchangeV2** | `0xe2222d279d744050d28e00520010520000310f59` | `getCtfCollateral()` = WCOL, `getOutcomeTokenFactory()` = NegRiskCtfCollateralAdapter. |
| **CollateralToken (pUSD)** proxy | `0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb` | `name()` = Polymarket USD, `symbol()` = pUSD, 6 decimals. Supply ≈ 484.1M on 2026-10-30. |
| pUSD implementation (current) | `0xce84e053301a82937f90ee2c2c1889cab1db25de` | From the EIP-1967 slot. |
| pUSD implementation (original) | `0x6bbcef9f7ef3b6c592c99e0f206a0de94ad0925f` | Listed in the `ctf-exchange-v2` README. Replaced. |
| pUSD backing vault | `0xc417fd8e9661c0d2120b64a04bb3278c17e99db1` | `VAULT()`. ERC-1967 proxy (impl `0xd206ac7fef53d83ed4563e770b28dba90d0d9ec8`). Held ≈ 486.8M USDC.e and ≈ 313 USDC. |
| **CollateralOnramp** | `0x93070a847efef7f70739046a929d47a521f5b8ee` | Public wrap. |
| **CollateralOfframp** | `0x2957922eb93258b93368531d39facca3b4dc5854` | Public unwrap. |
| **PermissionedRamp** | `0xebc2459ec962869ca4c0bd1e06368272732bcb08` | Witness-signed wrap / unwrap. |
| **CtfCollateralAdapter** | `0xada100874d00e3331d00f2007a9c336a65009718` | Binary outcome-token factory. |
| **NegRiskCtfCollateralAdapter** | `0xada200001000ef00d07553cee7006808f895c6f1` | Neg-risk outcome-token factory. |
| Fee receiver (both exchanges) | `0x115f48dc2a731aa16251c6d6e1befc42f92accc9` | `getFeeReceiver()`. A 171-byte contract. |
| pUSD owner | `0x47ebfac3353314c788b96cdcbf41daadfe03629c` | `owner()`. Also owns the PositionManager system. |
| USDC (native) | `0x3c499c542cef5e3811e1192ce70d8cc03d5c3359` | `USDC()`. |
| USDC.e | `0x2791bca1f2de4661ed88a30c99a7a9449aa84174` | `USDCE()`. |

Shared with V1 (see `v1.md`): CTF `0x4d97…6045`, NegRiskAdapter `0xd91e…5296`, WCOL `0x3a3b…02e2`, ProxyWalletFactory `0xab45…4052`, SafeProxyFactory `0xaacf…541b`.

---

## 4. Cross-chain summary

| Chain (ID) | Exchanges V2 | pUSD | Ramps / adapters |
|------------|--------------|------|------------------|
| Ethereum (1) | — | — | — |
| Base (8453) | — | — | — |
| BNB (56) | — | — | — |
| Avalanche (43114) | — | — | — |
| Arbitrum (42161) | — | — | — |
| Optimism (10) | — | — | — |
| **Polygon (137)** | ✓ | ✓ | ✓ |
| Robinhood Chain (4663) | — | — | — |
| Arc (5042) | — | — | — |

`—` = `eth_getCode` returned `0x` for every address in §3 on 2026-10-30. The vanity prefixes (`0xe1111…`, `0xe2222…`, `0xada1…`, `0xada2…`) are CREATE2 salts, not a cross-chain deployment.

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **CollateralToken (pUSD)** | UUPS, Solady ERC-1967 minimal proxy (61-byte runtime) | impl slot `0x3608…2bbc` = `0xce84…25de` | `owner()` `0x47eb…629c`. Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. Old impl `0x6bbc…925f`. |
| pUSD vault | ERC-1967 proxy | impl slot = `0xd206…9ec8` | Not documented in the repo. |
| CTFExchangeV2, NegRiskCtfExchangeV2, ramps, adapters | **Immutable** | EIP-1967 slots zero | None. Rotation = redeploy. |

---

## 6. Detection invariants & gotchas

1. **Topic0 changed from V1.** Use `0xd543adfd…` (`OrderFilled`) and `0x174b3811…` (`OrdersMatched`) for V2. The V1 `0xd0a08e8c…` / `0x63bf4d16…` topics are silent since mid-2026.
2. **One `tokenId` plus `side`.** V2 `OrderFilled` has `side` (0 = BUY, 1 = SELL) and one `tokenId`. For BUY, `makerAmountFilled` is pUSD and `takerAmountFilled` is shares. For SELL it is the reverse.
3. **`fee` is in the fill.** V2 `OrderFilled` carries `fee`. `FeeCharged(receiver, amount)` is the total sent to the fee receiver per match. Do not double count.
4. **`builder` and `metadata`** (bytes32) tag the order source (builder attribution). Group by `builder` to split flow by front end.
5. **Collateral is pUSD, not USDC.e.** Track USD flow on pUSD `Transfer`. Track deposits / withdrawals on pUSD `Wrapped` / `Unwrapped`. The real USDC.e moves between the user, the pUSD contract and the vault `0xc417…9db1`.
6. **Supply vs backing.** pUSD `totalSupply()` must stay ≤ vault USDC + USDC.e balance. On 2026-10-30: 484.1M supply vs 486.8M backing.
7. **Minter role is powerful.** `RolesUpdated` on pUSD that adds a minter, `Upgraded` on pUSD, and `OwnershipTransferred` / `OwnershipHandoverRequested` on pUSD are critical admin alerts.
8. **CTF events still fire.** A V2 match that mints or merges complete sets calls the adapter. The adapter calls the CTF (or NegRiskAdapter). So CTF `PositionSplit` / `PositionsMerge` appear with the adapter as `stakeholder`.
9. **User self-pause.** `UserPaused(user, effectiveBlock)` stops matching of that user's orders after a delay. It is a user safety switch, not an admin action.
10. **Preapproved orders** (`OrderPreapproved`) let a maker skip a signature check at match time. Watch `OrderPreapprovalInvalidated` for revocations.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_V2_ORDER_FILLED               = '\xd543adfd945773f1a62f74f0ee55a5e3b9b1a28262980ba90b1a89f2ea84d8ee'
TOPIC_V2_ORDERS_MATCHED             = '\x174b3811690657c217184f89418266767c87e4805d09680c39fc9c031c0cab7c'
TOPIC_V2_FEE_CHARGED                = '\x55bb3cade9d43b798a4fe5ffdd05024b2d7870df53920673bfc7e68047cd0ab1'
TOPIC_V2_FEE_RECEIVER_UPDATED       = '\x27aae5db36d94179909d019ae0b1ac7c16d96d953148f63c0f6a0a9c8ead79ee'
TOPIC_V2_MAX_FEE_RATE_UPDATED       = '\xe380d7c3967dd06cc7c01db8b17332a1d806fd18f63206dcbd12aaef455c7ff2'
TOPIC_V2_ORDER_PREAPPROVED          = '\xe92c22722d9c284034b6c9f5aaec018edb3e593c0e084900b6b9d390a1182a0b'
TOPIC_V2_ORDER_PREAPPROVAL_INVALID  = '\xb766aa470f20b094f26a9a14ea5bf63a60af51703c15776e2e739b6a0428adf6'
TOPIC_V2_USER_PAUSED                = '\xa3e76126f19eb25001b29726d2a9502b6377938633d2d6a955107dd442e7a14a'
TOPIC_V2_USER_UNPAUSED              = '\x1419d4111b5c8636aecff843bf618525f4f8e1aa6898a14357021d68dde8af12'
TOPIC_V2_USER_PAUSE_INTERVAL        = '\x8c8acf678b7cd311e3b5768c92794d63943684862fdea390856e14d9e2a9ef88'
TOPIC_NEW_OPERATOR                  = '\xf1e04d73c4304b5ff164f9d10c7473e2a1593b740674a6107975e2a7001c1e5c'
TOPIC_NEW_ADMIN                     = '\xf9ffabca9c8276e99321725bcb43fb076a6c66a54b7f21c4e8146d8519b417dc'
TOPIC_TRADING_PAUSED                = '\x203c4bd3e526634f661575359ff30de3b0edaba6c2cb1eac60f730b6d2d9d536'
TOPIC_PUSD_WRAPPED                  = '\xc00a5c84859ae82a7f5e6a2773283fb525335d5b3195f61174aa1ecc7e15dd84'
TOPIC_PUSD_UNWRAPPED                = '\x18b42b684d0b621cc609f4d888916e5ed9e934a476259ec1c11ec116f2b9aa7f'
TOPIC_PUSD_RESCUED                  = '\x3af790fafda720819b2fc6e15090606e81154e0ac9a92d38ecad006d99d20ecc'
TOPIC_ERC20_TRANSFER                = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_ROLES_UPDATED                 = '\x715ad5ce61fc9595c7b415289d59cf203f23a94fa06f04af7e489a0a76e1fe26'
TOPIC_OWNERSHIP_TRANSFERRED         = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_OWNERSHIP_HANDOVER_REQUESTED  = '\xdbf36a107da19e49527a7176a1babf963b4b0ff8cde35ee35d6cd8f1f9ac7e1d'
TOPIC_UPGRADED                      = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_PAUSED                        = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                      = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
-- ===== Selectors (chain-agnostic) =====
SEL_V2_MATCH_ORDERS                 = '\x3c2b4399'
SEL_V2_PREAPPROVE_ORDER             = '\xe3a5ced5'
SEL_V2_SET_FEE_RECEIVER             = '\xefdcd974'
SEL_V2_SET_MAX_FEE_RATE             = '\x8cda96de'
SEL_PUSD_WRAP                       = '\x62355638'
SEL_PUSD_UNWRAP                     = '\x8cc7104f'
SEL_PUSD_WRAP_LEGACY                = '\xb97b57c7'
SEL_PUSD_UNWRAP_LEGACY              = '\xd600875d'
SEL_PUSD_MINT                       = '\x40c10f19'
SEL_PUSD_ADD_MINTER                 = '\x983b2d56'
SEL_PUSD_RESCUE                     = '\xb252d405'
SEL_UPGRADE_TO_AND_CALL             = '\x4f1ef286'
-- ===== Addresses (Polygon 137) =====
POLY_CTF_EXCHANGE_V2                = '\xe111180000d2663c0091e4f400237545b87b996b'
POLY_NEGRISK_CTF_EXCHANGE_V2        = '\xe2222d279d744050d28e00520010520000310f59'
POLY_PUSD                           = '\xc011a7e12a19f7b1f670d46f03b03f3342e82dfb'
POLY_PUSD_VAULT                     = '\xc417fd8e9661c0d2120b64a04bb3278c17e99db1'
POLY_COLLATERAL_ONRAMP              = '\x93070a847efef7f70739046a929d47a521f5b8ee'
POLY_COLLATERAL_OFFRAMP             = '\x2957922eb93258b93368531d39facca3b4dc5854'
POLY_PERMISSIONED_RAMP              = '\xebc2459ec962869ca4c0bd1e06368272732bcb08'
POLY_CTF_COLLATERAL_ADAPTER         = '\xada100874d00e3331d00f2007a9c336a65009718'
POLY_NEGRISK_CTF_COLLATERAL_ADAPTER = '\xada200001000ef00d07553cee7006808f895c6f1'
POLY_V2_FEE_RECEIVER                = '\x115f48dc2a731aa16251c6d6e1befc42f92accc9'
POLY_USDC                           = '\x3c499c542cef5e3811e1192ce70d8cc03d5c3359'
POLY_USDCE                          = '\x2791bca1f2de4661ed88a30c99a7a9449aa84174'
```

---

## 8. Verification & sources

How constants in this doc were verified (2026-10-30):
- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the `ctf-exchange-v2` sources (struct types expanded to tuples). Each topic0 was found as a `PUSH32` operand, and each selector as a `PUSH4` operand, in the live bytecode of the contract that lists it.
- **Live events:** a 40-block `eth_getLogs` sample (blocks 96,445,769–96,445,809) showed `OrderFilled` (`0xd543…`), `OrdersMatched` (`0x174b…`) and `FeeCharged` (`0x55bb…`) on both V2 exchanges, and `Wrapped` / `Unwrapped` / `Transfer` on pUSD. Older windows place the V1 → V2 cutover between blocks 86.0M and 86.3M (late April to early May 2026).
- **Addresses:** from the `ctf-exchange-v2` README and the `clob-client-v2` / `py-clob-client-v2` contract config (chain 137). Each was existence-checked with `eth_getCode`. Wiring read live (`getCollateral`, `getCtf`, `getCtfCollateral`, `getOutcomeTokenFactory`, `getFeeReceiver`, `USDC`, `USDCE`, `VAULT`, `owner`).
- **Proxies:** EIP-1967 slots read for every address. Only pUSD and its vault are proxies.
- **Chain coverage:** every §3 address returned `0x` from `eth_getCode` on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Robinhood Chain and Arc.

Authoritative sources:
- [Polymarket/ctf-exchange-v2](https://github.com/Polymarket/ctf-exchange-v2) — source, deployed addresses, Quantstamp audit (March 2026).
- [Polymarket/clob-client-v2](https://github.com/Polymarket/clob-client-v2) — `src/config.ts` contract config.
- [docs.polymarket.com](https://docs.polymarket.com) — contract address pages.
- Explorer: [Polygonscan](https://polygonscan.com).
