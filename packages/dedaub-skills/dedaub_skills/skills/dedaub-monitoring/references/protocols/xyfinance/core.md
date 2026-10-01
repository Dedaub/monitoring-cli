# XY Finance (yBridge, XSwapper, YBridgeVault, XY Router) — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche; NOT Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the official XY Finance docs (contract address pages per chain, "Integrate YBridge Contract", "Latest Upgrade (2024/07/17)"), the verified legacy `XSwapper` source on Blockscout, the DefiLlama `xy-finance` bridge adapter, and sample receipts. Every topic0 and selector was recomputed as `keccak256(signature)`. Every address was existence-checked with `eth_getCode`; EIP-1967 slots, `paused()`, `acceptSwapRequest()` and `chainId()` were read live. The current YBridge and YBridgeVault implementations are **not verified on any explorer**; their events and functions were confirmed as constants in the deployed bytecode.
**Scope:** yBridge (v3), XY Finance's own liquidity bridge: one **YBridge** proxy per chain (formerly XSwapper), one **YBridgeVault** per pool token per chain (formerly YPoolVault; USDT, USDC, ETH), the **Supervisor** (validator signatures), and the **XY Router** (the bridge-aggregator entry). Also the legacy XSwapper on Ethereum. Topics and selectors are chain-agnostic. Addresses are network-specific.

**Flow.** On the source chain the user calls `swapWithReferrer` on the YBridge: the input token is swapped to a vault token (USDT, USDC or ETH) and held by the YBridge, and `SwapRequested` records the request with a **`swapId`** and the destination chain. On the destination chain an XY worker calls the YBridge, which pulls the vault token from the YBridgeVault (`TransferTo` on the vault), swaps it if asked, and pays the receiver (`SwappedForUser`, plus `CloseSwapCompleted(result, srcChainId, srcChainSwapId)`). Later the source chain's YBridge settles to its vault with validator signatures. An expired or invalid request is refunded on the source chain (`SwapRefunded`).

**Link key:** `(source chainId, swapId)`. On chain on both sides: `SwapRequested._swapId` on the source chain, and `CloseSwapCompleted._srcChainId` + `_srcChainSwapId` on the destination chain; `getEverClosed(srcChainId, swapId)` returns true once closed. XY uses **EVM chain ids** (the sample's `dstChainId` 81,457 is Blast).

**Status (measured).** In the pinned window (2026-09-28 00:00–12:00 UTC) no YBridge, vault, XY Router or aggregator event was emitted on any chain. The last YBridge logs are from November 2025 (Ethereum 2025-11-26, Base 2025-11-13, Arbitrum 2025-11-03) and the last vault log on Ethereum is from 2025-12-01. **The XY Router is paused on all six chains read.** The YBridge contracts are not paused and still accept requests (`acceptSwapRequest()` = true). Third-party summaries state that the XY service and its liquidity pools were sunset, with manual withdrawals by ticket until 2026-02-05; no such notice is in the XY docs (unverified).

---

## 0. Contract families & versions

| Contract | Role | Proxy? |
|----------|------|--------|
| **YBridge** (v3, from 2023-11-22; upgraded 2024-07-17) | Source: `swapWithReferrer` (`SwapRequested`). Destination: close swap and pay (`SwappedForUser`, `CloseSwapCompleted`). Refund (`SwapRefunded`). Same-chain swaps (`AggregatorSwapped`). | **UUPS** (EIP-1967, 680 B proxy). One implementation `0x22c3709560f5f0810e258025218a78f3907cc2c2` on all seven chains (unverified). |
| **YBridgeVault** (USDT, USDC, ETH) | Liquidity per token; LP `deposit` / `withdraw` with worker fulfilment; pays the YBridge on the destination chain (`TransferTo`). | **UUPS** (EIP-1967). Implementation `0x590c9322a3eb5f96ee9b03227e2091702d5f9b04` on Ethereum, `0x91f77b8d6b21aab3ad23930280b9d5882c819d84` elsewhere (unverified). |
| xyUSDT / xyUSDC / xyETH | LP share tokens of the vaults. | No (3,752 B) |
| **Supervisor (YBridge)** | Validator set that signs claims, refunds and locks. | No |
| **XY Router** | Bridge aggregator entry (`XYRouterRequested`); routes to yBridge or third-party bridges. | Transparent proxy (EIP-1967). **Paused.** |
| xSyncAggregator `0xcf446713ddf0e83f7527a260047f8ae89efae3e5` | Newer aggregator entry (same address on all seven chains): `AggregatorRequested`; it calls the YBridge in the source sample. | EIP-1967 proxy (implementation unverified) |
| **XSwapper (legacy)** | Ethereum `0x47f704c91c7edaac125ba451c0f98cbd64c78340`, verified `XSwapper`: the v2 contract with its own event schema. | No |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 YBridge v3 (current implementation)

| topic0 | Event |
|--------|-------|
| `0xdf401b5720b8e9ac0b277fde8caae18ad0bddfccab6ac9d7dde794bd4499995b` | `SwapRequested(uint256 _swapId, address indexed _aggregatorAdaptor, address _sender, (uint32 dstChainId, address dstChainToken, address dstAggregatorAdaptor, uint256 expectedDstChainTokenAmount, uint32 slippage) _dstChainDesc, address _srcToken, address indexed _vaultToken, uint256 _vaultTokenAmount, address _receiver, uint256 _srcTokenAmount, uint256 _expressFeeAmount, address indexed _referrer)` |
| `0xee823aedb9f54993693aeaca62918fd9eeaf9d0416276706739088c10ceaf2b8` | `CloseSwapCompleted(uint8 _swapResult, uint32 _srcChainId, uint256 _srcChainSwapId)` |
| `0x99a830bc8dc28151ad5e29ed2c1b05d46849b76a341bf8e0947a46775ba6b4f9` | `SwappedForUser(address indexed _aggregatorAdaptor, address indexed _srcToken, uint256 _srcTokenAmount, address _dstToken, uint256 _dstTokenAmountOut, address _receiver)` |
| `0x2cfcf2accac369b8df64d9aecfec291a41535b96cc7d2fb2aa889da3a65632f0` | `SwapRefunded(uint256 _swapId, address _receiver, address _gasFeeReceiver, address _vaultToken, uint256 _refundAmount, uint256 _refundGasFee)` |
| `0x011e3eda8bce024b20c679a923ff817d511e6262dc98d959ee032d6f07ff2027` | `AggregatorSwapped(address indexed aggregator, address sender, address srcToken, address dstToken, address receiver, uint256 srcTokenAmount, uint256 dstTokenAmount, address indexed referrer)` |
| `0xbb15c9609377fc3c4e8bad789b00c4a2bcbffb5a72c2cf5cae3c33e93b5365bc` | `YBridgeVaultSet(address _supportedToken, address _vault, bool _isSet)` |
| `0xddb2d5e2010e584b0d2ead420a90d3915d2bb30a13fb9b880b4844b8d941f0f7` | `AggregatorAdaptorSet(address _aggregator, bool _isSet)` |
| `0xec57dfb25ceb91824ddcccf9134e3dec0e7de69251394efb93c925315aa32f30` | `AggregatorSet(address _aggregator, bool _isSet)` |
| `0xe9c79a92bfc6f0b53c87557fd9c5905d04c4bea7fb8852af1477e25590d330a5` | `AcceptSwapRequestSet(bool _isSet)` |

- `SwapRequested` (`0xdf401b5720b8e9ac0b277fde8caae18ad0bddfccab6ac9d7dde794bd4499995b` is the topic the live contracts emit) — **source leg.** `_swapId` is the link key with the source chain id. `_vaultTokenAmount` of `_vaultToken` (topic2; `0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee` = native) stays with the YBridge; the user's `_srcTokenAmount` of `_srcToken` moved in the same transaction (ERC-20 `Transfer` user to YBridge, or native value). `_receiver` is the destination recipient. The third field (named `_sender` here) held the calling aggregator `0xcf446713ddf0e83f7527a260047f8ae89efae3e5` in the sample; its name is not documented (inferred).
- `SwappedForUser` + `CloseSwapCompleted` — **destination leg.** `_receiver` gets `_dstTokenAmountOut` of `_dstToken` (ERC-20 `Transfer` from the YBridge, or native value with no log). `_swapResult`: 0 Success, 1 Failed (vault token paid instead), 2 Locked (closed without payout), 3 NonSwapped (vault token paid as is) — the order of the verified legacy `CloseSwapResult` enum.
- `SwapRefunded` — **refund** on the source chain to `_receiver`, minus `_refundGasFee` to `_gasFeeReceiver`.
- `AggregatorSwapped` — same-chain swap; not a bridge transfer.

The XY docs show `SwapRequested` without the third address field; the documented topic0 values are listed in §1.4. The current implementation bytecode contains only `0xdf401b5720b8e9ac0b277fde8caae18ad0bddfccab6ac9d7dde794bd4499995b`.

### 1.2 YBridgeVault (USDT, USDC, ETH)

Parameter names are inferred from the sample data (the implementation is unverified); the signatures are confirmed by the public signature database and the bytecode.

| topic0 | Event |
|--------|-------|
| `0xd70645d60a6465bb7b8c93d33a3bd06236ce6a6b1ea6111401bb4724dbaaefef` | `TransferTo(address to, address token, uint256 amount)` |
| `0xd07b88bc5333ca866820627716b1c6c09d5e43515f6b3a4a980ce147bd6d0047` | `CloseSwapGasFeesCollected(address token, address receiver, uint256 amount)` |
| `0x827893a5f98dbfaba92dbe0bb2cafe8b9fd5573711d9768ce5cd4e2af44601ac` | `DepositRequested(address sender, uint256 depositId, uint256 amount, uint256 fee)` |
| `0x823f0e221d1509d3ab923032e7f0f46943d22de228379fd5579aa72355c1b7ab` | `DepositFulfilled(address recipient, uint256 depositId, uint256 shares)` |
| `0x38e3d972947cfef94205163d483d6287ef27eb312e20cb8e0b13a49989db232e` | `WithdrawalRequested(address sender, uint256 withdrawId, uint256 shares, uint256 fee)` |
| `0x567289124f980c60ab6be9d631895db98cf8d567e8ef80f55d8be6474ad2d0a6` | `WithdrawalFulfilled(address recipient, uint256 withdrawId, uint256 amount, uint256 fee)` |
| `0xbdde72a6d8d8b42770c9899945ccdce09d0c5c794d3326cdb2d2cca61b12a9fc` | `MinDepositAmountSet(uint256 amount)` |

`TransferTo` is the vault paying out (to the YBridge on a destination close, or to an XY operator); the value is the token `Transfer` (or native value) in the same transaction. Two further vault topics, `0xbc359805a1f83708f841b85187109db860f6fc8760d013fe295720e591042ac7` (data: token, recipient, amount) and `0xc57d4c70cc028d6e4ebdb81c2e039c09a90a0b03877111761326c1311da50a46` (data: address, value), appear in fee-collection transactions and have no public signature (unresolved).

### 1.3 XY Router and xSyncAggregator

| topic0 | Event |
|--------|-------|
| `0xcfdc06da1b80f541716b9dc11dba02141fbc401b0d152e9286df44c79b9d4000` | `XYRouterRequested(uint256 xyRouterRequestId, address indexed sender, address srcToken, uint256 amountIn, address indexed bridgeAddress, address bridgeToken, uint256 bridgeAmount, uint256 dstChainId, bytes bridgeAssetReceiver, ((bool hasTip, address tipReceiver) tipInfo, (bool hasDstChainSwap, ((address srcToken, address dstToken, uint256 minReturnAmount, address receiver) swapRequest, address dexAddress, address approveToAddress, bytes dexCalldata) swapAction) dstChainSwapInfo, (bool hasIM, address xApp, address refundReceiver, bytes message) imInfo) dstChainAction, address indexed affiliate)` |
| `0x848a418b4c38d4f38e611651849223f402d2bc961e2dec3180307ee2d7514abe` | `AffiliateCommissionCharged(address affiliate, uint256 amount, uint256 fee, address token)` |
| `0x57de676645d2e2072714410ba6a7e5cd212c5485ba49cb6633ed4628e4c215b9` | `AggregatorRequested(uint256 requestId, address sender, bytes32 srcToken, (bytes32 a, bytes32 b, uint32 c, uint256 d, bytes32 e, bytes32 f, bytes32 g) dstInfo, address bridgeAddress, (uint32 dstChainId, uint256 amount, address token, address receiver, bytes data) bridgeInfo, uint256 amountIn, uint256 amountOut, uint256 fee, bytes32 refId, address refundReceiver, address affiliate)` |

`XYRouterRequested` names the bridge used (`bridgeAddress`; the YBridge or a third-party bridge) and the destination; it is a second record of the same exit. `AggregatorRequested` (xSyncAggregator): the type list is from the public signature database; the parameter names are placeholders (unverified).

### 1.4 Documented and legacy `SwapRequested` variants (no log from the current implementation)

| topic0 | Event |
|--------|-------|
| `0xb0e9a29a6096a927bd389ba0d0d1a15f82df21a331d23a33eeb7de1cf7ab2684` | `SwapRequested(uint256 _swapId, address indexed _aggregatorAdaptor, (uint32 dstChainId, address dstChainToken, address dstAggregatorAdaptor, uint256 expectedDstChainTokenAmount, uint32 slippage) _dstChainDesc, address _srcToken, address indexed _vaultToken, uint256 _vaultTokenAmount, address _receiver, uint256 _srcTokenAmount, uint256 _expressFeeAmount, address indexed _referrer)` |
| `0x40218dc7047d6a284746d042d62140b3629db83daefcd944659e90b4c74b7eb0` | `SwapRequested(uint256 _swapId, address indexed _aggregatorAdaptor, (uint32 dstChainId, address dstChainToken, uint256 expectedDstChainTokenAmount, uint32 slippage) _dstChainDesc, address _srcToken, address indexed _vaultToken, uint256 _vaultTokenAmount, address _receiver, uint256 _srcTokenAmount, uint256 _expressFeeAmount, address indexed _referrer)` |
| `0x7ab36fa3be61b88675b434febef4e25ce3b3f32d121b1c6d11bb0520910e1f45` | `SwapRequested(uint256 _swapId, address indexed _aggregatorAdaptor, (uint32 toChainId, address toChainToken, uint256 expectedToChainTokenAmount, uint32 slippage) _toChainDesc, address _fromToken, address indexed _YPoolToken, uint256 _YPoolTokenAmount, address _receiver, uint256 _xyFee, uint256 _gasFee)` |
| `0x7cf616e580913e39d7ffeeb739823ba0799bc2948b9b6043f5127cad95b655c8` | `SwapCompleted(uint8 _closeType, (uint32 toChainId, uint256 swapId, address receiver, address sender, uint256 YPoolTokenAmount, uint256 xyFee, uint256 gasFee, address YPoolToken, uint8 status) _swapRequest)` |
| `0xf1e53a62d5935afca4762c943ac543a520fbf358eafaac6024bcb3f053f32071` | `YPoolVaultSet(address _supportedToken, address _vault, bool _isSet)` |

- `0xb0e9a29a6096a927bd389ba0d0d1a15f82df21a331d23a33eeb7de1cf7ab2684` — the event named in the docs "Latest Upgrade (2024/07/17)"; not in the current bytecode.
- `0x40218dc7047d6a284746d042d62140b3629db83daefcd944659e90b4c74b7eb0` — the pre-2024-07-17 v3 event; not in the current bytecode.
- `0x7ab36fa3be61b88675b434febef4e25ce3b3f32d121b1c6d11bb0520910e1f45`, `SwapCompleted`, `YPoolVaultSet` — the verified legacy XSwapper `0x47f704c91c7edaac125ba451c0f98cbd64c78340` (v2). `SwapCompleted._closeType`: 0 Claimed, 1 FreeClaimed, 2 Refunded.

### 1.5 Proxy and role events

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 YBridge v3

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2aac3cac` | `swapWithReferrer(address aggregatorAdaptor, (address srcToken, address dstToken, address receiver, uint256 amount, uint256 minReturnAmount) swapDesc, bytes aggregatorData, (uint32 dstChainId, address dstChainToken, uint256 expectedDstChainTokenAmount, uint32 slippage) dstChainDesc, address referrer)` | Source leg (old interface, kept). Emits `SwapRequested`. |
| `0xcdc65927` | `swapWithReferrer(address aggregatorAdaptor, (address srcToken, address dstToken, address receiver, uint256 amount, uint256 minReturnAmount) swapDesc, bytes aggregatorData, (uint32 dstChainId, address dstChainToken, address dstAggregatorAdaptor, uint256 expectedDstChainTokenAmount, uint32 slippage) dstChainDesc, address referrer)` | Source leg (2024-07-17 interface; charges native fees, refunds extra `msg.value`). Emits `SwapRequested`. |
| `0xbb7f50ea` | `singleChainSwapWithReferrer(address aggregator, (address srcToken, address dstToken, address receiver, uint256 amount, uint256 minReturnAmount) swapDesc, bytes aggregatorData, address referrer)` | Same-chain swap. Emits `AggregatorSwapped`. |
| `0x131ea36a` | not public | **Destination close by the XY worker** (every recent direct YBridge transaction on Ethereum, Base, Arbitrum and Polygon uses it); emits `SwappedForUser` and `CloseSwapCompleted`. Signature not in any public database (unverified). |
| `0xf281de9e` | `getEverClosed(uint32 _srcChainId, uint256 _srcChainSwapId)` | `bool` — the destination-side check of the link key. |
| `0xf54738ef` | `swapId()` | `uint256` — next source `swapId`. |
| `0x9a8a0592` | `chainId()` | `uint32` — this chain's EVM chain id. |
| `0x54192e37` | `acceptSwapRequest()` | `bool`. |
| `0xa1153112` | `setAcceptSwapRequest(bool _isSet)` | Admin. Emits `AcceptSwapRequestSet`. |
| `0x5daf3440` | `setYBridgeVault(address _supportedToken, address _vault, bool _isSet)` | Admin. Emits `YBridgeVaultSet`. |
| `0x6c3f3917` | `rescue(address[] tokens)` | **Admin; moves any token balance out of the YBridge.** |
| `0x8456cb59` | `pause()` | Emits `Paused`. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | UUPS upgrade. Emits `Upgraded`. |
| `0x3659cfe6` | `upgradeTo(address newImplementation)` | UUPS upgrade. |
| `0x2f2ff15d` | `grantRole(bytes32 role, address account)` | Emits `RoleGranted`. |

### 2.2 Legacy XSwapper (verified, Ethereum `0x47f704c91c7edaac125ba451c0f98cbd64c78340`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4039c8d0` | `swap(address aggregatorAdaptor, (address fromToken, address toToken, address receiver, uint256 amount, uint256 minReturnAmount) swapDesc, bytes aggregatorData, (uint32 toChainId, address toChainToken, uint256 expectedToChainTokenAmount, uint32 slippage) toChainDesc)` | v2 source leg. |
| `0xb0747516` | `closeSwap(address aggregatorAdaptor, (address fromToken, address toToken, address receiver, uint256 amount, uint256 minReturnAmount) swapDesc, bytes aggregatorData, uint32 fromChainId, uint256 fromSwapId)` | v2 destination leg (worker). |
| `0x00501e28` | `claim(uint256 _swapId, bytes[] signatures)` | v2 settlement to the vault. |
| `0x8fc3ab8b` | `batchClaim(uint256[] _swapIds, address _YPoolToken, bytes[] signatures)` | v2 settlement. |
| `0xe251975e` | `refund(uint256 _swapId, address gasFeeReceiver, bytes[] signatures)` | v2 refund. |
| `0x6aa4d6b5` | `lockCloseSwap(uint32 fromChainId, uint256 fromSwapId, bytes[] signatures)` | v2 lock of an expired request. |

### 2.3 YBridgeVault and XY Router

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb6b55f25` | `deposit(uint256 vaultTokenAmount)` | LP deposit request; emits `DepositRequested`; a worker completes it (`DepositFulfilled`). |
| `0x2e1a7d4d` | `withdraw(uint256 shareAmount)` | LP withdrawal request; emits `WithdrawalRequested`, then `WithdrawalFulfilled`. |
| `0xa5f2a152` | `transferTo(address to, address token, uint256 amount)` | Vault payout (role-gated); emits `TransferTo`. |
| `0xa2f827e7` | `isDepositCompleted(uint256 depositId)` | `bool`. |
| `0xfbb36501` | `isWithdrawCompleted(uint256 withdrawId)` | `bool`. |
| `0x5c975abb` | `paused()` | `bool` — `true` on the XY Router on all six chains read. |

---

## 3. Addresses — per chain (official XY docs; all verified with `eth_getCode`)

| Contract | Ethereum (1) | Base (8453) | Arbitrum One (42161) | Optimism (10) |
|----------|--------------|-------------|----------------------|---------------|
| **YBridge** (proxy) | `0x4315f344a905dc21a08189a117efd6e1fca37d57` | `0x73ce60416035b8d7019f6399778c14ccf5c9c7a1` | `0x33383265290421c704c6b09f4bf27ce574dc4203` | `0x7a6e01880693093abaccf442fcbed9e0435f1030` |
| Supervisor (YBridge) | `0x778c974568e376146dbc64ff12ad55b2d1c4133f` | `0x1b0789910027c3cc58af2391de7228d973c5c46e` | `0x73ce60416035b8d7019f6399778c14ccf5c9c7a1` | `0x1b0789910027c3cc58af2391de7228d973c5c46e` |
| USDT YBridgeVault | `0x8e921191a9dc6832c1c360c7c7b019efb7c29b2d` | — | `0x7a483730ad5a845ed2962c49de38be1661d47341` | `0xf526efc174b512e66243cb52524c1be720144e8d` |
| USDC YBridgeVault | `0xdd8b0995cc92c7377c7bce2a097ec70f45a192d5` | `0xa5cb30e5d30a9843b6481ffd8d8d35dded3a3251` | `0x680ab543acd0e52035e9d409014dd57861fa1edf` | `0x1e4992e1be86c9d8ed7dcbfcf3665fe568de98ab` |
| ETH YBridgeVault | `0x57ea46759fed1b47c200a9859e576239a941df76` | `0xd195070107d853e55dad9a2e6e7e970c400e67b8` | `0xd1ae4594e47c153ae98f09e0c9267fb74447fea3` | `0x91474fe836bbbe63ef72de2846244928860bce1b` |
| XY Router (proxy, paused) | `0xffb9faf89165585ad4b25f81332ead96986a2681` | `0x6acd0ec9405ccb701c57a88849c4f1cd85a3f3ab` | `0x062b1db694f6a437e3c028fc60dd6fea7444308c` | `0xf8d342db903f266de73b10a1e46601bb08a3c195` |
| Legacy XSwapper | `0x47f704c91c7edaac125ba451c0f98cbd64c78340` | — | — | — |

| Contract | Polygon PoS (137) | BNB Smart Chain (56) | Avalanche C-Chain (43114) |
|----------|-------------------|----------------------|---------------------------|
| **YBridge** (proxy) | `0x0c988b66edef267d04f100a879db86cdb7b9a34f` | `0x7d26f09d4e2d032efa0729fc31a4c2db8a2394b1` | `0x2c86f0ff75673d489b7d72d9986929a2b0ed596c` |
| Supervisor (YBridge) | `0x1b0789910027c3cc58af2391de7228d973c5c46e` | `0x1b0789910027c3cc58af2391de7228d973c5c46e` | `0xfdf54f6f232dd5a6daf067628ba045a1b5a6724d` |
| USDT YBridgeVault | `0x3243278e0f93cd6f88fc918e0714baf7169afab8` | `0xd195070107d853e55dad9a2e6e7e970c400e67b8` | `0x3d2d1ce29b8bc997733d318170b68e63150c6586` |
| USDC YBridgeVault | `0xf4137e5d07b476e5a30f907c3e31f9faab00716b` | `0x27c12bcb4538b12fdf29acb968b71df7867b3f64` | `0x21ae3e63e06d80c69b09d967d88ed9a98c07b4e4` |
| ETH YBridgeVault | `0x29d91854b1ee21604119ddc02e4e3690b9100017` | `0xa0ffc7edb9daa9c0831cdf35b658e767ace33939` | `0xefaaf68a9a8b7d93bb15d29c8b77fce87fcc91b8` |
| XY Router (proxy, paused) | `0xa1fb1f1e5382844ee2d1bd69ef07d5a6abcbd388` | `0xdf921bc47aa6ecdb278f8c259d6a7fef5702f1a9` | `0xa0c0f962decd78d7cde5707895603cba74c02989` |

The xSyncAggregator `0xcf446713ddf0e83f7527a260047f8ae89efae3e5` has code on all seven chains. The LP share tokens (xyUSDT, xyUSDC, xyETH) are on the XY docs pages; Ethereum: `0x3243278e0f93cd6f88fc918e0714baf7169afab8`, `0x2f6ccc4a900ee42f822892b8c024aaa08af89701`, `0x60c779b8348c0a0517f8e2b0489a88ceaf87822f`.

**Same address, other roles.** XY reuses literal addresses for different contracts across chains: `0x73ce60416035b8d7019f6399778c14ccf5c9c7a1` is the YBridge on Base but the Supervisor on Arbitrum and the Gas Price Consumer on Optimism; `0x8e921191a9dc6832c1c360c7c7b019efb7c29b2d` is the USDT vault on Ethereum but xyETH on Base and xyUSDT on BNB; `0xd195070107d853e55dad9a2e6e7e970c400e67b8` is the ETH vault on Base and the USDT vault on BNB. `0x4315f344a905dc21a08189a117efd6e1fca37d57` has other code on Optimism and BNB. Always key on `(chain, address)`.

### 3.1 Robinhood Chain (4663) — NO XY deployment

`eth_getCode` returns `0x` at the YBridge addresses of Ethereum and Base, the Supervisor `0x1b0789910027c3cc58af2391de7228d973c5c46e`, the xSyncAggregator and XY Refuel `0x6829bb7edd1360255b7fc6aecbbac029f47feeb3` on Robinhood Chain, and the XY docs do not list the chain.

---

## 4. Cross-chain summary

| Chain | ID | YBridge | Vaults | XY Router | Last YBridge log | Window events |
|-------|----|---------|--------|-----------|------------------|---------------|
| Ethereum | 1 | ✓ | USDT, USDC, ETH | ✓ (paused) | 2025-11-26 | 0 |
| Base | 8453 | ✓ | USDC, ETH | ✓ (paused) | 2025-11-13 | 0 |
| Arbitrum One | 42161 | ✓ | USDT, USDC, ETH | ✓ (paused) | 2025-11-03 | 0 |
| Optimism | 10 | ✓ | USDT, USDC, ETH | ✓ (paused) | not read | 0 |
| Polygon PoS | 137 | ✓ | USDT, USDC, ETH | ✓ | 2025-11-04 | 0 |
| BNB Smart Chain | 56 | ✓ | USDT, USDC, ETH | ✓ (paused) | not read | 0 |
| Avalanche C-Chain | 43114 | ✓ | USDT, USDC, ETH | ✓ (paused) | not read | 0 |
| Robinhood Chain | 4663 | — (`0x`) | — | — | — | — |

**Outside the eight (XY docs):** Cronos, KCC, Astar, Kaia, zkSync Era, Polygon zkEVM, Linea, Mantle, Scroll, Blast, X Layer, Taiko, Cronos zkEVM, Abstract, Berachain, Numbers; suspended: Fantom, ThunderCore, Moonriver.

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade authority |
|----------|---------|-----------|-------------------|
| YBridge (all seven chains) | **UUPS** (EIP-1967, 680 B proxy) | Implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` = `0x22c3709560f5f0810e258025218a78f3907cc2c2` on every chain; implementation exposes `upgradeTo` / `upgradeToAndCall` / `proxiableUUID`; `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. | Role-based (`ROLE_OWNER`, `ROLE_MANAGER`, `ROLE_STAFF`, `ROLE_YPOOL_WORKER` in the bytecode; `RoleGranted` events). Role holders not read. |
| YBridgeVault (USDT, USDC, ETH) | **UUPS** (EIP-1967) | Implementation `0x590c9322a3eb5f96ee9b03227e2091702d5f9b04` (Ethereum), `0x91f77b8d6b21aab3ad23930280b9d5882c819d84` (Base, Arbitrum, Optimism, BNB, Avalanche). | Role-based. |
| XY Router | EIP-1967 proxy | Implementation per chain (Ethereum `0x89695c6e5cd30362649dab71fd5bd9c12d59ea75`; Base `0x73730a31eb4f04241ac603c87435c80b6d8cbf5d`). | Not read. |
| Supervisor, legacy XSwapper, LP tokens | Not proxies | Full runtime bytecode, no implementation slot. | — |

---

## 6. Detection invariants & gotchas

1. **Index `0xdf401b5720b8e9ac0b277fde8caae18ad0bddfccab6ac9d7dde794bd4499995b` for `SwapRequested`.** The docs name `0xb0e9a29a6096a927bd389ba0d0d1a15f82df21a331d23a33eeb7de1cf7ab2684`, and older integrations use `0x40218dc7047d6a284746d042d62140b3629db83daefcd944659e90b4c74b7eb0`; the live YBridge implementation emits only `0xdf401b5720b8e9ac0b277fde8caae18ad0bddfccab6ac9d7dde794bd4499995b` (it has an extra address field after `_swapId`). The legacy XSwapper emits `0x7ab36fa3be61b88675b434febef4e25ce3b3f32d121b1c6d11bb0520910e1f45`. Keep all four for backfills.
2. **Join source and destination on `(srcChainId, swapId)`.** `SwapRequested._swapId` on the source YBridge (its chain id is `chainId()`) = `CloseSwapCompleted._srcChainSwapId` with `_srcChainId` on the destination YBridge. `getEverClosed` confirms the close.
3. **The destination payout comes from the YBridge, funded by the vault.** In one destination transaction: vault `TransferTo` (vault to YBridge), the swap, then `SwappedForUser` and `CloseSwapCompleted`, and the token `Transfer` to `_receiver` (native ETH payouts have no log). The worker EOA in the Ethereum sample was `0xb35f9aac007666cacd0520b68d59d682262db7da`.
4. **`CloseSwapCompleted` with `_swapResult` 1 or 3 pays the vault token, not the requested token.** Result 2 (Locked) pays nothing; the source then refunds (`SwapRefunded`).
5. **Aggregator records duplicate the exit.** `XYRouterRequested` and `AggregatorRequested` name the bridge used; when it is the YBridge, the value is already in `SwapRequested`. Count once.
6. **Activity has stopped (measured).** No XY event in the pinned window on any chain; last YBridge logs in November 2025; XY Router paused everywhere. The YBridges are not paused: a new `SwapRequested` today is unexpected and worth an alert.
7. **Admin actions:** `Upgraded` on any YBridge or vault, `RoleGranted` (especially the worker and owner roles), `AcceptSwapRequestSet`, `YBridgeVaultSet` (redirects liquidity), and `rescue` (selector `0x6c3f3917`; moves all listed token balances).
8. **Same literal address, different contracts across chains** (§3). A per-address monitor must carry the chain.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== YBridge v3 topics =====
TOPIC_XY_SWAP_REQUESTED             = '\xdf401b5720b8e9ac0b277fde8caae18ad0bddfccab6ac9d7dde794bd4499995b'
TOPIC_XY_SWAP_REQUESTED_DOCS        = '\xb0e9a29a6096a927bd389ba0d0d1a15f82df21a331d23a33eeb7de1cf7ab2684'
TOPIC_XY_SWAP_REQUESTED_PRE2024     = '\x40218dc7047d6a284746d042d62140b3629db83daefcd944659e90b4c74b7eb0'
TOPIC_XY_SWAP_REQUESTED_XSWAPPER    = '\x7ab36fa3be61b88675b434febef4e25ce3b3f32d121b1c6d11bb0520910e1f45'
TOPIC_XY_CLOSE_SWAP_COMPLETED       = '\xee823aedb9f54993693aeaca62918fd9eeaf9d0416276706739088c10ceaf2b8'
TOPIC_XY_SWAPPED_FOR_USER           = '\x99a830bc8dc28151ad5e29ed2c1b05d46849b76a341bf8e0947a46775ba6b4f9'
TOPIC_XY_SWAP_REFUNDED              = '\x2cfcf2accac369b8df64d9aecfec291a41535b96cc7d2fb2aa889da3a65632f0'
TOPIC_XY_SWAP_COMPLETED_XSWAPPER    = '\x7cf616e580913e39d7ffeeb739823ba0799bc2948b9b6043f5127cad95b655c8'
TOPIC_XY_AGGREGATOR_SWAPPED         = '\x011e3eda8bce024b20c679a923ff817d511e6262dc98d959ee032d6f07ff2027'
TOPIC_XY_YBRIDGE_VAULT_SET          = '\xbb15c9609377fc3c4e8bad789b00c4a2bcbffb5a72c2cf5cae3c33e93b5365bc'
TOPIC_XY_ACCEPT_SWAP_REQUEST_SET    = '\xe9c79a92bfc6f0b53c87557fd9c5905d04c4bea7fb8852af1477e25590d330a5'
-- ===== Vault, router, aggregator topics =====
TOPIC_XY_VAULT_TRANSFER_TO          = '\xd70645d60a6465bb7b8c93d33a3bd06236ce6a6b1ea6111401bb4724dbaaefef'
TOPIC_XY_VAULT_DEPOSIT_REQUESTED    = '\x827893a5f98dbfaba92dbe0bb2cafe8b9fd5573711d9768ce5cd4e2af44601ac'
TOPIC_XY_VAULT_WITHDRAWAL_REQUESTED = '\x38e3d972947cfef94205163d483d6287ef27eb312e20cb8e0b13a49989db232e'
TOPIC_XY_ROUTER_REQUESTED           = '\xcfdc06da1b80f541716b9dc11dba02141fbc401b0d152e9286df44c79b9d4000'
TOPIC_XY_AGGREGATOR_REQUESTED       = '\x57de676645d2e2072714410ba6a7e5cd212c5485ba49cb6633ed4628e4c215b9'
TOPIC_UPGRADED                      = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ROLE_GRANTED                  = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_PAUSED                        = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
-- ===== Selectors =====
SEL_XY_SWAP_WITH_REFERRER_OLD       = '\x2aac3cac'
SEL_XY_SWAP_WITH_REFERRER           = '\xcdc65927'
SEL_XY_CLOSE_SWAP_V3                = '\x131ea36a'
SEL_XY_GET_EVER_CLOSED              = '\xf281de9e'
SEL_XY_RESCUE                       = '\x6c3f3917'
SEL_XY_VAULT_TRANSFER_TO            = '\xa5f2a152'
SEL_XY_XSWAPPER_SWAP                = '\x4039c8d0'
SEL_XY_XSWAPPER_CLOSE_SWAP          = '\xb0747516'
-- ===== YBridge (network-specific) =====
ETH_XY_YBRIDGE                      = '\x4315f344a905dc21a08189a117efd6e1fca37d57'
BASE_XY_YBRIDGE                     = '\x73ce60416035b8d7019f6399778c14ccf5c9c7a1'
ARB_XY_YBRIDGE                      = '\x33383265290421c704c6b09f4bf27ce574dc4203'
OP_XY_YBRIDGE                       = '\x7a6e01880693093abaccf442fcbed9e0435f1030'
POLY_XY_YBRIDGE                     = '\x0c988b66edef267d04f100a879db86cdb7b9a34f'
BNB_XY_YBRIDGE                      = '\x7d26f09d4e2d032efa0729fc31a4c2db8a2394b1'
AVAX_XY_YBRIDGE                     = '\x2c86f0ff75673d489b7d72d9986929a2b0ed596c'
ETH_XY_XSWAPPER_LEGACY              = '\x47f704c91c7edaac125ba451c0f98cbd64c78340'
-- ===== YBridgeVaults =====
ETH_XY_VAULT_USDT                   = '\x8e921191a9dc6832c1c360c7c7b019efb7c29b2d'
ETH_XY_VAULT_USDC                   = '\xdd8b0995cc92c7377c7bce2a097ec70f45a192d5'
ETH_XY_VAULT_ETH                    = '\x57ea46759fed1b47c200a9859e576239a941df76'
BASE_XY_VAULT_USDC                  = '\xa5cb30e5d30a9843b6481ffd8d8d35dded3a3251'
BASE_XY_VAULT_ETH                   = '\xd195070107d853e55dad9a2e6e7e970c400e67b8'
ARB_XY_VAULT_USDT                   = '\x7a483730ad5a845ed2962c49de38be1661d47341'
ARB_XY_VAULT_USDC                   = '\x680ab543acd0e52035e9d409014dd57861fa1edf'
ARB_XY_VAULT_ETH                    = '\xd1ae4594e47c153ae98f09e0c9267fb74447fea3'
OP_XY_VAULT_USDT                    = '\xf526efc174b512e66243cb52524c1be720144e8d'
OP_XY_VAULT_USDC                    = '\x1e4992e1be86c9d8ed7dcbfcf3665fe568de98ab'
OP_XY_VAULT_ETH                     = '\x91474fe836bbbe63ef72de2846244928860bce1b'
POLY_XY_VAULT_USDT                  = '\x3243278e0f93cd6f88fc918e0714baf7169afab8'
POLY_XY_VAULT_USDC                  = '\xf4137e5d07b476e5a30f907c3e31f9faab00716b'
POLY_XY_VAULT_ETH                   = '\x29d91854b1ee21604119ddc02e4e3690b9100017'
BNB_XY_VAULT_USDT                   = '\xd195070107d853e55dad9a2e6e7e970c400e67b8'
BNB_XY_VAULT_USDC                   = '\x27c12bcb4538b12fdf29acb968b71df7867b3f64'
BNB_XY_VAULT_ETH                    = '\xa0ffc7edb9daa9c0831cdf35b658e767ace33939'
AVAX_XY_VAULT_USDT                  = '\x3d2d1ce29b8bc997733d318170b68e63150c6586'
AVAX_XY_VAULT_USDC                  = '\x21ae3e63e06d80c69b09d967d88ed9a98c07b4e4'
AVAX_XY_VAULT_ETH                   = '\xefaaf68a9a8b7d93bb15d29c8b77fce87fcc91b8'
-- ===== XY Router (paused) and aggregator =====
ETH_XY_ROUTER                       = '\xffb9faf89165585ad4b25f81332ead96986a2681'
BASE_XY_ROUTER                      = '\x6acd0ec9405ccb701c57a88849c4f1cd85a3f3ab'
ARB_XY_ROUTER                       = '\x062b1db694f6a437e3c028fc60dd6fea7444308c'
OP_XY_ROUTER                        = '\xf8d342db903f266de73b10a1e46601bb08a3c195'
POLY_XY_ROUTER                      = '\xa1fb1f1e5382844ee2d1bd69ef07d5a6abcbd388'
BNB_XY_ROUTER                       = '\xdf921bc47aa6ecdb278f8c259d6a7fef5702f1a9'
AVAX_XY_ROUTER                      = '\xa0c0f962decd78d7cde5707895603cba74c02989'
XY_XSYNC_AGGREGATOR                 = '\xcf446713ddf0e83f7527a260047f8ae89efae3e5'   -- same address on ETH BASE ARB OP POLY BNB AVAX
ETH_XY_WORKER_EOA                   = '\xb35f9aac007666cacd0520b68d59d682262db7da'
-- Robinhood (4663): no XY contract
```

---

## 8. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)`. YBridge v3: events from the XY docs ("Integrate YBridge Contract", "Latest Upgrade (2024/07/17)") and the live logs; `SwapRequested` `0xdf401b5720b8e9ac0b277fde8caae18ad0bddfccab6ac9d7dde794bd4499995b` decoded from a live Ethereum log (12 data words, three indexed fields); every v3 event of §1.1 and the selectors of §2.1 found as constants in the implementation `0x22c3709560f5f0810e258025218a78f3907cc2c2` (the 2024 doc topic `0xb0e9a29a6096a927bd389ba0d0d1a15f82df21a331d23a33eeb7de1cf7ab2684`, the pre-2024 `0x40218dc7047d6a284746d042d62140b3629db83daefcd944659e90b4c74b7eb0` and the v2 `claim` / `refund` / `closeSwap` selectors are absent). Vault events: resolved from the implementation's `PUSH32` constants with the public signature database. Legacy XSwapper: verified source on Blockscout. XY Router: the DefiLlama adapter ABI, and both topics found in the Ethereum router implementation.
- **Addresses:** XY docs pages per chain (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche), cross-checked with the DefiLlama adapter (`YBridgeContractAddress`, `YBridgeVaultsTokenContractAddress`, `XYRouterContractAddress`); `eth_getCode` on all eight chains; implementation slots read live; `paused()` = true on all six XY Routers read (Ethereum, Base, Arbitrum, Optimism, BNB, Avalanche) and false on the YBridges; `acceptSwapRequest()` = true; `chainId()` = the EVM chain id.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC:** 0 logs of every `SwapRequested` variant, `CloseSwapCompleted`, `SwappedForUser`, `SwapRefunded` and `XYRouterRequested` from any emitter on all eight chains; vault `TransferTo` 0 on Ethereum, Base, Arbitrum, Optimism and Avalanche (2 on BNB, from `0xba44cde8c418c435c668d39ff269127c664da42a`, not an XY address); `AggregatorRequested` 0 on Ethereum, Base, Arbitrum, Optimism, BNB and Avalanche. Last activity from Blockscout logs: YBridge Ethereum 2025-11-26, Base 2025-11-13, Arbitrum 2025-11-03, Polygon 2025-11-04; USDT vault Ethereum 2025-12-01; XY Router Ethereum 2025-01-09.
- **Sample transactions (receipts read, Ethereum):** source `0x01e85d75bbaafd31f804c4f6b645623c078b0f58ea4f7b0aa14129674080358a` (block 23,885,241; the xSyncAggregator calls the YBridge with 0.000184483092365075 ETH; `SwapRequested` with `dstChainId` 81,457; `AggregatorRequested`). Destination `0x7929ca5fc4f171d3beb54126fc8ac404d78f85d5ed8bf2bd47efa0dd2f2930b3` (worker `0xb35f9aac007666cacd0520b68d59d682262db7da`, selector `0x131ea36a`; ETH vault `TransferTo`, `SwappedForUser`, `CloseSwapCompleted`).
- **Unverified:** the parameter names of the vault events, of `AggregatorRequested`, and of the third `SwapRequested` field; the signature of `0x131ea36a`; the role holders; the service sunset (third-party summaries only).

Authoritative sources:
- XY docs — [Addresses](https://docs.xy.finance/smart-contract/addresses) (per-chain pages) · [Integrate YBridge Contract](https://docs.xy.finance/single-bridge-integration/ybridge-contract-integration/integrate-ybridge-contract) · [Latest Upgrade (2024/07/17)](https://docs.xy.finance/single-bridge-integration/ybridge-contract-integration/integrate-ybridge-contract/latest-upgrade-2024-07-17) · [(Legacy) Integrate X Swap Contract](https://docs.xy.finance/single-bridge-integration/ybridge-contract-integration/smart-contract).
- [DefiLlama bridges-server adapter `xy-finance`](https://github.com/DefiLlama/bridges-server/tree/master/src/adapters/xy-finance).
- Explorers — [XSwapper (verified)](https://eth.blockscout.com/address/0x47f704c91c7edaac125ba451c0f98cbd64c78340) · [YBridge Ethereum](https://etherscan.io/address/0x4315f344a905dc21a08189a117efd6e1fca37d57) · [YBridge Base](https://base.blockscout.com/address/0x73ce60416035b8d7019f6399778c14ccf5c9c7a1) · [YBridge Arbitrum](https://arbitrum.blockscout.com/address/0x33383265290421c704c6b09f4bf27ce574dc4203).
