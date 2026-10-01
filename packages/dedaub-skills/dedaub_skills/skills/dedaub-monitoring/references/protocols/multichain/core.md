# Multichain (Anyswap) Routers — Topics, Selectors, Addresses (Ethereum, Arbitrum, Optimism, Polygon, BNB, Avalanche; not Base or Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the canonical sources (`anyswap/anyswap-v1-core`: `AnyswapV3Router.sol`, `AnyswapV5Router.sol`, `AnyswapV6Router.sol`, `AnyswapV4ERC20.sol` to `AnyswapV6ERC20.sol`; `anyswap/multichain-smart-contracts`: `MultichainV7Router.sol` and its access-control and `SwapInfo` files), the verified explorer source of `AnyswapV4Router`, and the official Router V7 address page.
**Scope:** every Multichain (formerly Anyswap) cross-chain router generation on the target chains: **AnyswapV3Router, AnyswapV4Router, AnyswapV6Router and MultichainV7Router**, plus the anyToken (`AnyswapV4ERC20` to `AnyswapV6ERC20`) events that the old Swapin/Swapout bridge mode emits. Six of the eight target chains have routers: Ethereum (1), Arbitrum One (42161), Optimism (10), Polygon PoS (137), BNB Smart Chain (56) and Avalanche C-Chain (43114). **Base (8453) and Robinhood Chain (4663) have none.** Topics and selectors are chain-agnostic; addresses are network-specific.

**Multichain stopped in July 2023.** On 2023-07-06 about $126M to $130M left the MPC addresses that held the locked assets of its Fantom, Moonriver and Dogechain bridges (CoinDesk, 2023-07-06). Multichain wrote that "the lockup assets on the Multichain MPC address have been moved to an unknown address abnormally" and told users to stop using its services and revoke approvals. The routers were never paused on chain and have no pause function (V3 to V6). Use this file for two jobs: attribution of old flows (2021 to 2023), and monitoring of residual activity, which still happens in 2026 (§12, items 9 to 11).

The routers are **immutable** contracts (no proxy; 17 to 22 kB of full logic). All V3, V4 and V6 routers were created by `0xfA9dA51631268A30Ec3DDd1CcBf46c65FAD99251`, all V7 routers by `0x78C1F761f7b7970bFe5c89E340Fa4e96593f7Ed4`. A router trusts one **MPC address** (`mpc()`), an off-chain threshold-signature key that sends every destination-leg transaction. There is no on-chain proof of the source event: the MPC is the bridge. Multichain uses **EVM chain ids** (`fromChainID`, `toChainID`). There is no shared vanity address for V3 to V6; V7 uses `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` on five target chains and `0x400b971099e0ebFDa2C03a3063739cb5398734A6` on BNB.

---

## 0. Contract families and the transfer flow

| Contract | Role | Proxy? |
|----------|------|--------|
| **AnyswapV3Router** (20,150 B) | Router: out-functions (burn or lock on the source chain) and MPC-only in-functions (mint or release on the destination chain), cross-chain swaps. | No |
| **AnyswapV4Router** (18,508 B) | The same interface as V3 without `anySwapOutNative`, `depositNative` and `withdrawNative`. Verified explorer name `AnyswapV4Router`. | No |
| **AnyswapV6Router** (17,093 B; 17,681 B and 17,737 B variants) | V4 plus string-receiver out-functions (non-EVM chains) and minter management; no permit variants. | No |
| **MultichainV7Router** (22,042 B) | New ids: `swapoutID` (bytes32) and `swapID` (string); swap-and-call through an executor; role pauses; a RouterSecurity contract registers each swap. | No (its RouterSecurity is an EIP-1967 proxy) |
| **anyToken** (`AnyswapV4ERC20` to `AnyswapV6ERC20`, one per token and chain) | Bridged representation (`anyUSDC`, ...). Holds the underlying as the vault of liquidity; the router is its minter. Emits `LogSwapin` / `LogSwapout` in the old bridge mode. | No |
| **MPC address** (EOA) | The only caller of `anySwapIn*`, `changeMPC`, `changeVault`. | — |

One router transfer has two transactions, one per chain:

| Step | Chain | Caller | Function (examples) | Event | Value movement in the same transaction |
|------|-------|--------|---------------------|-------|----------------------------------------|
| Source leg | source | the user | `anySwapOutUnderlying`, `anySwapOut`, `anySwapOutNative`, the permit and trade variants | V3 to V6: `LogAnySwapOut` or `LogAnySwapTradeTokensFor*`; V7: `LogAnySwapOut` (V7 form) | Underlying `Transfer` user to the **anyToken contract**, then anyToken mint to the user and burn (`Transfer` to `0x0`). `anySwapOut` burns the user's anyToken only. Native: `msg.value` is wrapped (`Deposit` on the wrapped-native token) and moved into the anyToken. |
| Destination leg | destination | the **MPC address** | `anySwapInAuto`, `anySwapIn`, `anySwapInUnderlying`, `anySwapInExactTokensFor*` | V3 to V6: `LogAnySwapIn`; V7: `LogAnySwapIn` (V7 form) | anyToken minted to the receiver; when the anyToken holds enough underlying, the anyToken is burned and the underlying is paid from the anyToken contract to the receiver. Otherwise the receiver keeps the anyToken (a claim on the pool). |
| Refund | — | — | none | none | No refund function or event exists. A stuck transfer can only be paid by an MPC-signed `anySwapIn`. V7 records a failed destination call (`LogRetryExecRecord`) and allows `retrySwapinAndExec`. |

**Link key.** V3 to V6: `LogAnySwapIn.txhash` (topic1) = the source-chain transaction hash; the source event has no id, so join on (source transaction hash, `token`, `to`, `amount`, `fromChainID`). A batch `anySwapOut` puts several transfers in one source transaction. V7: `swapoutID` (topic1 of the source `LogAnySwapOut`, topic1 of the destination `LogAnySwapIn`) on both sides; the destination `swapID` string is `"<fromChainID>:<source tx hash>:<log index>"` (measured: `"56:0xe4f1fe248959ae0f9990f4bf42e7e40e610f7b65f39b32d366fa6acf9cd24353:2"`).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 AnyswapV3Router, AnyswapV4Router, AnyswapV6Router — transfer events

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x97116cf6cd4f6412bb47914d6db18da9e16ab2142f543b86e207c24fbd16b23a` | `LogAnySwapOut(address indexed token, address indexed from, address indexed to, uint256 amount, uint256 fromChainID, uint256 toChainID)` | **Source leg, V3 to V6.** `token` is the anyToken, not the underlying. Emitted by `anySwapOut`, `anySwapOutUnderlying`, `anySwapOutNative`, the permit variants and the batch `anySwapOut`. Verified live. |
| `0x409e0ad946b19f77602d6cf11d59e1796ddaa4828159a0b4fb7fa2ff6b161b79` | `LogAnySwapOut(address indexed token, address indexed from, string to, uint256 amount, uint256 fromChainID, uint256 toChainID)` | **Source leg, V6 only**, to a non-EVM or string receiver. Verified live on Avalanche. |
| `0xaac9ce45fe3adf5143598c4f18a369591a20a3384aedaf1b525d29127e1fcd55` | `LogAnySwapIn(bytes32 indexed txhash, address indexed token, address indexed to, uint256 amount, uint256 fromChainID, uint256 toChainID)` | **Destination leg, V3 to V6.** `txhash` = the source-chain transaction hash (the link key). Sent by the MPC address. Verified live. |
| `0xfea6abdf4fd32f20966dff7619354cd82cd43dc78a3bee479f04c74dbfc585b3` | `LogAnySwapTradeTokensForTokens(address[] path, address indexed from, address indexed to, uint256 amountIn, uint256 amountOutMin, uint256 fromChainID, uint256 toChainID)` | Source leg of a cross-chain swap (V3 to V6): the out-function burns `path[0]` and the destination swaps. From source; not seen in the sampled windows. |
| `0x278277e0209c347189add7bd92411973b5f6b8644f7ac62ea1be984ce993f8f4` | `LogAnySwapTradeTokensForNative(address[] path, address indexed from, address indexed to, uint256 amountIn, uint256 amountOutMin, uint256 fromChainID, uint256 toChainID)` | The same, with a native-asset output. From source; not seen in the sampled windows. |

### 1.2 MultichainV7Router — transfer events

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x0d969ae475ff6fcaf0dcfa760d4d8607244e8d95e9bf426f8d5d69f9a3e525af` | `LogAnySwapOut(bytes32 indexed swapoutID, address indexed token, address indexed from, string receiver, uint256 amount, uint256 toChainID)` | **Source leg, V7.** `swapoutID` is the link key. Verified live. |
| `0x968608314ec29f6fd1a9f6ef9e96247a4da1a683917569706e2d2b60ca7c0a6d` | `LogAnySwapOutAndCall(bytes32 indexed swapoutID, address indexed token, address indexed from, string receiver, uint256 amount, uint256 toChainID, string anycallProxy, bytes data)` | Source leg, V7, with a destination call. |
| `0x164f647883b52834be7a5219336e455a23a358be27519d0442fc0ee5e1b1ce2e` | `LogAnySwapIn(string swapID, bytes32 indexed swapoutID, address indexed token, address indexed receiver, uint256 amount, uint256 fromChainID)` | **Destination leg, V7.** `swapID` = `"<fromChainID>:<source tx hash>:<log index>"`. Verified live. |
| `0x603ea9944a12c4ef108a97399c705891f182d169a361b6aa6455d14aa1cdd258` | `LogAnySwapInAndExec(string swapID, bytes32 indexed swapoutID, address indexed token, address indexed receiver, uint256 amount, uint256 fromChainID, bool success, bytes result)` | Destination leg, V7, with the call result. |
| `0x2d044017b61f24f5423ce5e0c62f9ead27cb38f1615069e703ba521d0b04696b` | `LogRetryExecRecord(string swapID, bytes32 swapoutID, address token, address receiver, uint256 amount, uint256 fromChainID, address anycallProxy, bytes data)` | V7: a failed destination call is recorded for retry (status only). |
| `0x4024f72e00ae47f03ed1dd3ab595d04dabdc9d1f95f8c039bca61946d9da0eb3` | `LogRetrySwapInAndExec(string swapID, bytes32 swapoutID, address token, address receiver, uint256 amount, uint256 fromChainID, bool dontExec, bool success, bytes result)` | V7: the retry of a failed call; with `dontExec = true` the receiver gets the tokens without the call. |

### 1.3 Router admin events (status only, no value moves)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xcda32bc39904597666dfa9f9c845714756e1ffffad55b52e0d344673a2198121` | `LogChangeMPC(address indexed oldMPC, address indexed newMPC, uint256 indexed effectiveTime, uint256 chainID)` | V3 to V6 router: the MPC (the only payout signer) changes. **High-severity admin event.** The same signature is used by other bridges (see §12). |
| `0x7eefe162042d50d604dca716bef4ff4c5e318a056f712c0195d016f78089955a` | `LogChangeRouter(address indexed oldRouter, address indexed newRouter, uint256 chainID)` | V3 to V5 router (declared; V6 removed it). |
| `0x581f388e3dd32e1bbf62a290f509c8245f9d0b71ef82614fb2b967ad0a10d5b9` | `LogChangeMPC(address indexed oldMPC, address indexed newMPC, uint256 effectiveTime)` | V7 router (`MPCManageable`): a new MPC is pending. |
| `0x8d32c9dd498e08090b44a0f77fe9ec0278851f9dffc4b430428411243e7df076` | `LogApplyMPC(address indexed oldMPC, address indexed newMPC, uint256 applyTime)` | V7 router: the pending MPC takes effect. |
| `0xcf9b665e0639e0b81a8db37b60ac7ddf45aeb1b484e11adeb7dff4bf4a3a6258` | `ChangeAdmin(address indexed _old, address indexed _new)` | V7 router: the pause admin changes. |
| `0x0cb09dc71d57eeec2046f6854976717e4874a3cf2d6ddeddde337e5b6de6ba31` | `Paused(bytes32 role)` | V7 router: a role (`Swapin_Paused_ROLE`, `Swapout_Paused_ROLE`, `Call_Paused_ROLE`, `Exec_Paused_ROLE`, `Retry_Paused_ROLE`) is paused. |
| `0xd05bfc2250abb0f8fd265a54c53a24359c5484af63cad2e4ce87c78ab751395a` | `Unpaused(bytes32 role)` | V7 router. |

### 1.4 anyToken events (emitter: any anyToken contract; the old Swapin/Swapout bridge mode)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x05d0634fe981be85c22e2942a880821b70095d84e152c3ea3c17a4e4250d9d61` | `LogSwapin(bytes32 indexed txhash, address indexed account, uint256 amount)` | anyToken (V4 to V6 ERC-20) `Swapin`: the MPC mints bridged tokens; `txhash` is the source deposit. Also emitted by `ProxySwapAsset` contracts. Verified live. |
| `0x6b616089d04950dc06c45c6dd787d657980543f89651aec47924752c7d16c888` | `LogSwapout(address indexed account, address indexed bindaddr, uint256 amount)` | anyToken `Swapout`: the holder burns to `bindaddr` on the other chain (old bridge mode, not a router). Verified live. |
| `0x5c364079e7102c27c608f9b237c735a1b7bfa0b67f27c2ad26bad447bf965cac` | `LogChangeVault(address indexed oldVault, address indexed newVault, uint256 indexed effectiveTime)` | anyToken: the vault (minter) changes. |
| `0x1d065115f314fb9bad9557bd5460b9e3c66f7223b1dd04e73e828f0bb5afe89f` | `LogChangeMPCOwner(address indexed oldOwner, address indexed newOwner, uint256 indexed effectiveHeight)` | anyToken V4 and V5. |
| `0xff9be4a5a0b9027fd253167d4c170ef1bbf8403af21bf06a0ed87ac8c8ecb5c6` | `LogAddAuth(address indexed auth, uint256 timestamp)` | anyToken V4 and V5: a new minter. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Count from source: V3 and V5 have 14 `anySwapOut*` and 6 `anySwapIn*` functions; V4 has 13 out (no `anySwapOutNative`) and the same 6 in. Of the V4 out-functions, 5 emit `LogAnySwapOut` and 8 emit `LogAnySwapTradeTokensForTokens` or `LogAnySwapTradeTokensForNative`.

### 2.1 Source-leg functions (V3 to V7)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x241dc2df` | `anySwapOut(address token, address to, uint256 amount, uint256 toChainID)` | V3 to V6. Burns `amount` of the anyToken from the caller. Emits `LogAnySwapOut`. |
| `0xedbdf5e2` | `anySwapOutUnderlying(address token, address to, uint256 amount, uint256 toChainID)` | V3 to V6. Pulls the underlying into the anyToken contract, then mints and burns the anyToken. Emits `LogAnySwapOut`. |
| `0xa5e56571` | `anySwapOutNative(address token, address to, uint256 toChainID)` | `payable`; V3, V5, V6 (not V4). Wraps `msg.value` into the anyToken's underlying. Emits `LogAnySwapOut`. |
| `0x8d7d3eea` | `anySwapOutUnderlyingWithPermit(address from, address token, address to, uint256 amount, uint256 deadline, uint8 v, bytes32 r, bytes32 s, uint256 toChainID)` | V3 to V5. Takes the underlying from `from` with a permit, or with an existing approval when the token has no permit. See §12, item 10. |
| `0x1b91a934` | `anySwapOutUnderlyingWithTransferPermit(address from, address token, address to, uint256 amount, uint256 deadline, uint8 v, bytes32 r, bytes32 s, uint256 toChainID)` | V3 to V5. |
| `0xdcfb77b1` | `anySwapOut(address[] tokens, address[] to, uint256[] amounts, uint256[] toChainIDs)` | V3 to V6, batch. One `LogAnySwapOut` per item, all with the same transaction hash. |
| `0xc604b0b8` | `anySwapOut(address token, string to, uint256 amount, uint256 toChainID)` | V6 and V7: string receiver. V6 emits the string `LogAnySwapOut`; V7 emits the V7 `LogAnySwapOut`. |
| `0x049b4e7e` | `anySwapOutUnderlying(address token, string to, uint256 amount, uint256 toChainID)` | V6 and V7. |
| `0x540dd52c` | `anySwapOutNative(address token, string to, uint256 toChainID)` | `payable`; V6 and V7. |
| `0x0bb57203` | `anySwapOutExactTokensForTokens(uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline, uint256 toChainID)` | V3 to V6. Emits `LogAnySwapTradeTokensForTokens`. |
| `0xd8b9f610` | `anySwapOutExactTokensForTokensUnderlying(uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline, uint256 toChainID)` | V3 to V6. |
| `0x99cd84b5` | `anySwapOutExactTokensForTokensUnderlyingWithPermit(address from, uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline, uint8 v, bytes32 r, bytes32 s, uint256 toChainID)` | V3 to V5. |
| `0x9aa1ac61` | `anySwapOutExactTokensForTokensUnderlyingWithTransferPermit(address from, uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline, uint8 v, bytes32 r, bytes32 s, uint256 toChainID)` | V3 to V5. |
| `0x65782f56` | `anySwapOutExactTokensForNative(uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline, uint256 toChainID)` | V3 to V6. Emits `LogAnySwapTradeTokensForNative`. |
| `0x6a453972` | `anySwapOutExactTokensForNativeUnderlying(uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline, uint256 toChainID)` | V3 to V6. |
| `0x4d93bb94` | `anySwapOutExactTokensForNativeUnderlyingWithPermit(address from, uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline, uint8 v, bytes32 r, bytes32 s, uint256 toChainID)` | V3 to V5. |
| `0xc8e174f6` | `anySwapOutExactTokensForNativeUnderlyingWithTransferPermit(address from, uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline, uint8 v, bytes32 r, bytes32 s, uint256 toChainID)` | V3 to V5. |

### 2.2 Destination-leg functions, V3 to V6 (MPC only)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x825bb13c` | `anySwapIn(bytes32 txs, address token, address to, uint256 amount, uint256 fromChainID)` | MPC only, V3 to V6. Mints the anyToken to `to`. Emits `LogAnySwapIn`. |
| `0x3f88de89` | `anySwapInUnderlying(bytes32 txs, address token, address to, uint256 amount, uint256 fromChainID)` | MPC only, V3 to V6. Mints, burns and pays the underlying from the anyToken contract. |
| `0x0175b1c4` | `anySwapInAuto(bytes32 txs, address token, address to, uint256 amount, uint256 fromChainID)` | MPC only, V3 to V6. Pays the underlying when the anyToken holds enough; else leaves the anyToken with `to`. |
| `0x25121b76` | `anySwapIn(bytes32[] txs, address[] tokens, address[] to, uint256[] amounts, uint256[] fromChainIDs)` | MPC only, V3 to V6, batch. |
| `0x2fc1e728` | `anySwapInExactTokensForTokens(bytes32 txs, uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline, uint256 fromChainID)` | MPC only, V3 to V6: destination leg of a cross-chain swap. |
| `0x52a397d5` | `anySwapInExactTokensForNative(bytes32 txs, uint256 amountIn, uint256 amountOutMin, address[] path, address to, uint256 deadline, uint256 fromChainID)` | MPC only, V3 to V6. |
| `0x701bb891` | `depositNative(address token, address to)` | `payable`; V3, V5, V6: wraps native into the anyToken. |
| `0x832e9492` | `withdrawNative(address token, uint256 amount, address to)` | V3, V5, V6: unwraps to native. |

### 2.3 MultichainV7Router — call variants and destination functions

`SwapInfo` = `(bytes32 swapoutID, address token, address receiver, uint256 amount, uint256 fromChainID)`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6b4b4376` | `anySwapOutAndCall(address token, string to, uint256 amount, uint256 toChainID, string anycallProxy, bytes data)` | V7. Emits `LogAnySwapOutAndCall`. |
| `0xe0e9048e` | `anySwapOutUnderlyingAndCall(address token, string to, uint256 amount, uint256 toChainID, string anycallProxy, bytes data)` | V7. |
| `0xea0c968b` | `anySwapOutNativeAndCall(address token, string to, uint256 toChainID, string anycallProxy, bytes data)` | `payable`; V7. |
| `0x8fef8489` | `anySwapIn(string swapID, (bytes32 swapoutID, address token, address receiver, uint256 amount, uint256 fromChainID) swapInfo)` | MPC only, V7. Emits the V7 `LogAnySwapIn`. |
| `0x9ff1d3e8` | `anySwapInUnderlying(string swapID, (bytes32 swapoutID, address token, address receiver, uint256 amount, uint256 fromChainID) swapInfo)` | MPC only, V7. |
| `0x5de26385` | `anySwapInNative(string swapID, (bytes32 swapoutID, address token, address receiver, uint256 amount, uint256 fromChainID) swapInfo)` | MPC only, V7: pays native. |
| `0x81aa7a81` | `anySwapInAuto(string swapID, (bytes32 swapoutID, address token, address receiver, uint256 amount, uint256 fromChainID) swapInfo)` | MPC only, V7. |
| `0xf9ca3a5d` | `anySwapInAndExec(string swapID, (bytes32 swapoutID, address token, address receiver, uint256 amount, uint256 fromChainID) swapInfo, address anycallProxy, bytes data)` | MPC only, V7. Emits `LogAnySwapInAndExec`. |
| `0xcc95060a` | `anySwapInUnderlyingAndExec(string swapID, (bytes32 swapoutID, address token, address receiver, uint256 amount, uint256 fromChainID) swapInfo, address anycallProxy, bytes data)` | MPC only, V7. |
| `0x872acd04` | `retrySwapinAndExec(string swapID, (bytes32 swapoutID, address token, address receiver, uint256 amount, uint256 fromChainID) swapInfo, address anycallProxy, bytes data, bool dontExec)` | V7. Emits `LogRetrySwapInAndExec`. |

### 2.4 Admin functions and views (routers)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf75c2664` | `mpc()` | `address`: the current MPC. Read it on each router (§3 to §8). |
| `0x5b7b018c` | `changeMPC(address newMPC)` | MPC only. Emits `LogChangeMPC`. **Admin trigger.** |
| `0xb63b38d0` | `applyMPC()` | V7: the pending MPC applies the change. Emits `LogApplyMPC`. |
| `0x456862aa` | `changeVault(address token, address newVault)` | MPC only, all versions: moves the anyToken's vault (minter) role. **Admin trigger.** |
| `0x9f122d6c` | `setMinter(address token, address _auth)` | MPC only, V6. |
| `0xd9e35bb2` | `applyMinter(address token)` | MPC only, V6. |
| `0x87bafe5f` | `revokeMinter(address token, address _auth)` | MPC only, V6. |
| `0x87cc6e2f` | `anySwapFeeTo(address token, uint256 amount)` | MPC only: mints fee to the MPC and withdraws the underlying. |
| `0x085c6d5e` | `setEnableSwapTrade(bool enable)` | MPC only, V6. |
| `0xa66ec443` | `setRouterSecurity(address _routerSecurity)` | MPC only, V7. |
| `0xa413387a` | `routerSecurity()` | V7: the RouterSecurity contract that registers swap ids. |
| `0xd2c7dfcc` | `anycallExecutor()` | V7: the executor of destination calls. |
| `0x99a2f2d7` | `cID()` | V3 to V6: the chain id. |
| `0xed56531a` | `pause(bytes32 role)` | V7, admin only. Emits `Paused`. |
| `0x2f4dae9f` | `unpause(bytes32 role)` | V7, admin only. Emits `Unpaused`. |

### 2.5 anyToken functions

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xec126c77` | `Swapin(bytes32 txhash, address account, uint256 amount)` | anyToken, minter (`onlyAuth`) only. Emits `LogSwapin`. |
| `0x628d6cba` | `Swapout(uint256 amount, address bindaddr)` | anyToken: burn to `bindaddr` on the other chain. Emits `LogSwapout`. |
| `0x40c10f19` | `mint(address to, uint256 amount)` | anyToken, minter (router) only. |
| `0x9dc29fac` | `burn(address from, uint256 amount)` | anyToken, minter (router) only. |
| `0x6f307dc3` | `underlying()` | anyToken: the underlying ERC-20 (`0x0` for a pure bridged token). |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified with `eth_getCode` on 2026-09-29; names from verified explorer source; `mpc()` read live. No EIP-1967 implementation slot on any router.

| Role | Address | One-liner |
|------|---------|-----------|
| **AnyswapV4Router** ("Router V4") | `0x6b7a87899490EcE95443e979cA9485CBE7E71522` | 18,508 B. `mpc()` = `0x2a038e100f8b85df21e4d44121bdbfe0c288a869`. |
| **AnyswapV4Router** (second instance) | `0x765277EebeCA2e31912C9946eAe1021199B39C61` | 18,508 B. `mpc()` = `0x647dc1366da28f8a64eb831fc8e9f05c90d1ea5a`. |
| **AnyswapV3Router** | `0xe95fD76CF16008c12FF3b3a937CB16Cd9Cc20284` | 20,150 B. `mpc()` = `0xf39fee2fdfe7db022591f4a82e3537fa0b55fb9c`. |
| **AnyswapV6Router** | `0xBa8Da9dcF11B50B03fd5284f164Ef5cdEF910705` | 17,093 B. `mpc()` = `0x2a038e100f8b85df21e4d44121bdbfe0c288a869`. |
| **MultichainV7Router** | `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` | 22,042 B. `mpc()` = `0x5608b26cc2996351c4d1289b867888081a9d4244`; `admin()` = `0x78C1F761f7b7970bFe5c89E340Fa4e96593f7Ed4`. |
| V7 RouterSecurity (EIP-1967 proxy) | `0x9303e7b16ef03c22b657e7ba37c8ca88379c1a76` | 2,083 B; implementation `0x810001169388b674b0ca264e0c0f38c458126558`. `routerSecurity()` of the V7 router. |
| V7 AnycallExecutor | `0x38264fccb88da59ca4609c729031bfa8e7db24ef` | 3,702 B. `anycallExecutor()` of the V7 router. |
| MPC (EOA) | `0x2a038e100f8b85df21e4d44121bdbfe0c288a869` | Nonce 209,957. MPC of the V4 and V6 routers. |
| MPC (EOA) | `0xf39fee2fdfe7db022591f4a82e3537fa0b55fb9c` | Nonce 12,456. MPC of the V3 router. |
| MPC (EOA) | `0x647dc1366da28f8a64eb831fc8e9f05c90d1ea5a` | Nonce 33,313. MPC of the second V4 router. |
| MPC (EOA) | `0x5608b26cc2996351c4d1289b867888081a9d4244` | Nonce 150. MPC of the V7 router. |
| **Fantom bridge MPC address (EOA)** | `0xC564EE9f21Ed8A2d8E7e76c085740d5e4c5FaFbE` | Nonce 134,639. Held the Ethereum side of the Fantom bridge; **source of the 2023-07-06 outflows** (§12, item 8). |
| Moonriver bridge MPC address (EOA) | `0x10c6b61DbF44a083Aec3780aCF769C77BE747E23` | Nonce 21,840. Listed as the Moonriver bridge address in Multichain's `bridges-server` adapter. |
| Router deployer (EOA) | `0xfA9dA51631268A30Ec3DDd1CcBf46c65FAD99251` | Created every V3, V4 and V6 router and many anyTokens. |
| V7 deployer and admin (EOA) | `0x78C1F761f7b7970bFe5c89E340Fa4e96593f7Ed4` | Created every V7 router. |

## 4. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **AnyswapV4Router** | `0xC931f61B1534EB21D8c11B24f3f5Ab2471d4aB50` | 18,508 B. `mpc()` = `0x2a038e100f8b85df21e4d44121bdbfe0c288a869`. |
| **AnyswapV3Router** | `0x0caE51e1032e8461f4806e26332c030E34De3aDb` | 20,150 B. `mpc()` = `0x647dc1366da28f8a64eb831fc8e9f05c90d1ea5a`. |
| **AnyswapV6Router** | `0x650Af55D5877F289837c30b94af91538a7504b76` | 17,737 B. `mpc()` = `0x2a038e100f8b85df21e4d44121bdbfe0c288a869`. |
| **MultichainV7Router** | `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` | 22,042 B. `mpc()` = `0x5608b26cc2996351c4d1289b867888081a9d4244`. |

At `0x6b7a87899490EcE95443e979cA9485CBE7E71522` Arbitrum has an anyToken (verified `AnyswapV5ERC20`, 10,660 B), not a router.

## 5. Addresses — Optimism (chain ID 10)

| Role | Address | One-liner |
|------|---------|-----------|
| **AnyswapV6Router** | `0xDC42728B0eA910349ed3c6e1c9Dc06b5FB591f98` | 17,093 B. `mpc()` = `0x2a038e100f8b85df21e4d44121bdbfe0c288a869`. |
| **AnyswapV6Router** (second instance) | `0x80A16016cC4A2E6a2CACA8a4a498b1699fF0f844` | 17,093 B, verified `AnyswapV6Router`, same deployer. `mpc()` = `0x647dc1366da28f8a64eb831fc8e9f05c90d1ea5a`. |
| **MultichainV7Router** | `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` | 22,042 B. |

At `0x6b7a87899490EcE95443e979cA9485CBE7E71522` Optimism has an anyToken (verified `AnyswapV6ERC20`, 7,558 B) whose `mpc()` is the second V6 router. No V3 or V4 router was found on Optimism.

## 6. Addresses — Polygon PoS (chain ID 137)

| Role | Address | One-liner |
|------|---------|-----------|
| **AnyswapV4Router** | `0x4f3Aff3A747fCADe12598081e80c6605A8be192F` | 18,508 B. `mpc()` = `0x2a038e100f8b85df21e4d44121bdbfe0c288a869`. |
| **AnyswapV3Router** | `0xAFAace7138ab3c2BCb2DB4264F8312e1Bbb80653` | 20,150 B. `mpc()` = `0xf39fee2fdfe7db022591f4a82e3537fa0b55fb9c`. |
| **AnyswapV6Router** | `0x2eF4A574b72E1f555185AfA8A09c6d1A8AC4025C` | 17,093 B. `mpc()` = `0xf39fee2fdfe7db022591f4a82e3537fa0b55fb9c`. |
| **MultichainV7Router** | `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` | 22,042 B. |

At `0x6b7a87899490EcE95443e979cA9485CBE7E71522` Polygon has an anyToken (verified `AnyswapV4ERC20`, 10,622 B).

## 7. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | One-liner |
|------|---------|-----------|
| **AnyswapV4Router** | `0xABd380327Fe66724FFDa91A87c772FB8D00bE488` | 18,508 B. `mpc()` = `0x647dc1366da28f8a64eb831fc8e9f05c90d1ea5a`. |
| **AnyswapV3Router** | `0xf9736ec3926703e85C843FC972BD89A7f8E827C0` | 20,150 B. `mpc()` = `0xf39fee2fdfe7db022591f4a82e3537fa0b55fb9c`. |
| **AnyswapV6Router** | `0xe1d592c3322f1F714Ca11f05B6bC0eFEf1907859` | 17,093 B. `mpc()` = `0xe19105463d6fe2f2bd86c69ad478f4b76ce49c53`. |
| **MultichainV7Router** | `0x400b971099e0ebFDa2C03a3063739cb5398734A6` | 22,042 B. **Not the shared V7 literal** (`0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` has no code on BNB). `mpc()` = `0x5608b26cc2996351c4d1289b867888081a9d4244`. |
| V7 RouterSecurity (EIP-1967 proxy) | `0x78aa42f4770f6b53df9c2ea1d723010825a229c3` | Implementation `0xa15c6e65d90392414c62ab577bb3b286a2ecccca`. |
| V7 AnycallExecutor | `0xb61a105123fede32cccbbc08f43bee81c0353efe` | 3,702 B. |

## 8. Addresses — Avalanche C-Chain (chain ID 43114)

| Role | Address | One-liner |
|------|---------|-----------|
| **AnyswapV4Router** | `0xB0731d50C681C45856BFc3f7539D5f61d4bE81D8` | 18,508 B. `mpc()` = `0x2a038e100f8b85df21e4d44121bdbfe0c288a869`. |
| **AnyswapV3Router** | `0x9b17bAADf0f21F03e35249e0e59723F34994F806` | 20,150 B. `mpc()` = `0xf39fee2fdfe7db022591f4a82e3537fa0b55fb9c`. |
| **AnyswapV6Router** | `0x833F307aC507D47309fD8CDD1F835BeF8D702a93` | 17,093 B. `mpc()` = `0xf39fee2fdfe7db022591f4a82e3537fa0b55fb9c`. |
| **AnyswapV6Router** (second instance) | `0x05f024C6F5a94990d32191D6f36211E3Ee33504e` | 17,681 B; V6 selectors in the bytecode; emitted the string `LogAnySwapOut` (§14). `mpc()` = `0x98c89980d1eae247ada3636ae27648f78e66e121`. |
| **MultichainV7Router** | `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` | 22,042 B. |

## 9. Base (chain ID 8453) and Robinhood Chain (chain ID 4663) — no deployment

`eth_getCode` returns `0x` on both chains at all 21 router literals of §3 to §8. Base launched in August 2023 and Robinhood Chain in 2026, after Multichain stopped. The official V7 page lists neither chain.

---

## 10. Cross-chain summary

| Chain | ID | V3 router | V4 router | V6 router | V7 router |
|-------|----|-----------|-----------|-----------|-----------|
| Ethereum | 1 | `0xe95fD76CF16008c12FF3b3a937CB16Cd9Cc20284` | `0x6b7a87899490EcE95443e979cA9485CBE7E71522`, `0x765277EebeCA2e31912C9946eAe1021199B39C61` | `0xBa8Da9dcF11B50B03fd5284f164Ef5cdEF910705` | `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` |
| Base | 8453 | — | — | — | — |
| Arbitrum One | 42161 | `0x0caE51e1032e8461f4806e26332c030E34De3aDb` | `0xC931f61B1534EB21D8c11B24f3f5Ab2471d4aB50` | `0x650Af55D5877F289837c30b94af91538a7504b76` | `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` |
| Optimism | 10 | — | — | `0xDC42728B0eA910349ed3c6e1c9Dc06b5FB591f98`, `0x80A16016cC4A2E6a2CACA8a4a498b1699fF0f844` | `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` |
| Polygon PoS | 137 | `0xAFAace7138ab3c2BCb2DB4264F8312e1Bbb80653` | `0x4f3Aff3A747fCADe12598081e80c6605A8be192F` | `0x2eF4A574b72E1f555185AfA8A09c6d1A8AC4025C` | `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` |
| BNB Smart Chain | 56 | `0xf9736ec3926703e85C843FC972BD89A7f8E827C0` | `0xABd380327Fe66724FFDa91A87c772FB8D00bE488` | `0xe1d592c3322f1F714Ca11f05B6bC0eFEf1907859` | `0x400b971099e0ebFDa2C03a3063739cb5398734A6` |
| Avalanche C-Chain | 43114 | `0x9b17bAADf0f21F03e35249e0e59723F34994F806` | `0xB0731d50C681C45856BFc3f7539D5f61d4bE81D8` | `0x833F307aC507D47309fD8CDD1F835BeF8D702a93`, `0x05f024C6F5a94990d32191D6f36211E3Ee33504e` | `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` |
| Robinhood Chain | 4663 | — | — | — | — |

Chains outside the eight with Multichain routers include Fantom, Moonriver, Moonbeam, Gnosis, Celo, Cronos, Harmony, Dogechain and many more; the official V7 page lists Fantom at the shared V7 literal. **The list above is the floor of the known routers:** the router list of Multichain's own `bridges-server` adapter, the official V7 page, and the second Optimism V6 router (found as the `mpc()` of an anyToken). Multichain deployed other routers for single projects that may be missing.

---

## 11. Proxies (old and new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| AnyswapV3Router, AnyswapV4Router, AnyswapV6Router | **Immutable** | Full bytecode (17 to 20 kB); EIP-1967 implementation slot empty; no EIP-1167 target. | None. The MPC controls everything through `changeMPC` and `changeVault`. |
| MultichainV7Router | **Immutable** | 22,042 B; implementation slot empty. `wNATIVE` and `anycallExecutor` are immutables. | None. MPC (`changeMPC` then `applyMPC`) and admin (`pause`, `unpause`, `changeAdmin`). |
| V7 RouterSecurity | EIP-1967 proxy | Implementation slot set (§3, §7). | Its admin. Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`. |
| anyToken | Immutable | Plain ERC-20 with vault and minter roles. | The vault (MPC or router) can change the vault and minters (`LogChangeVault`). |

---

## 12. Detection invariants and gotchas

1. **Index the source and destination legs by version.** V3 to V6 use `LogAnySwapOut` `0x97116cf6cd4f6412bb47914d6db18da9e16ab2142f543b86e207c24fbd16b23a` (and the V6 string form `0x409e0ad946b19f77602d6cf11d59e1796ddaa4828159a0b4fb7fa2ff6b161b79`) and `LogAnySwapIn` `0xaac9ce45fe3adf5143598c4f18a369591a20a3384aedaf1b525d29127e1fcd55`. V7 uses `0x0d969ae475ff6fcaf0dcfa760d4d8607244e8d95e9bf426f8d5d69f9a3e525af` and `0x164f647883b52834be7a5219336e455a23a358be27519d0442fc0ee5e1b1ce2e`. A rule on one version misses the others, and a rule on one out-function sees 1 of 13 or 14.
2. **Do not forget the trade events.** Cross-chain swaps emit `LogAnySwapTradeTokensForTokens` or `LogAnySwapTradeTokensForNative` instead of `LogAnySwapOut` on the source chain; the destination still emits `LogAnySwapIn`.
3. **`token` in the router events is the anyToken, not the underlying.** Resolve `underlying()` on the anyToken (for example `0x7ea2be2df7ba6e54b1a9c70676f668455e329d29` is anyUSDC on Ethereum with USDC as underlying).
4. **The value sits in the anyToken contract, not in the router.** `anySwapOutUnderlying` moves the underlying from the user to the anyToken; the router holds nothing. The destination payout comes from the anyToken contract to the receiver. A balance monitor must watch the anyTokens.
5. **Link key.** V3 to V6: `LogAnySwapIn.txhash` = the source transaction hash; it is not unique per transfer when a batch `anySwapOut` puts several transfers in one transaction. V7: `swapoutID` on both sides. Both sides are on chain; only the MPC connects them.
6. **The destination sender is the MPC address.** `tx.from` of every `anySwapIn*` is the router's `mpc()`. The receiver is `to` (topic3, V3 to V6) or `receiver` (topic3, V7); `tx.from` of the source leg is usually the user. V7 receivers are strings.
7. **`LogChangeMPC(address,address,uint256,uint256)` is not unique to Multichain.** In the pinned window, `TransparentUpgradeableProxy` contracts with a `BridgeV2` implementation of another bridge emitted it on Ethereum, Base, Arbitrum, Optimism, Polygon, Avalanche, BNB and Robinhood Chain (for example `0x5523985926aa12ba58dc5ad00ddca99678d7227e`). Filter by the router addresses.
8. **The July 2023 outflow.** On Ethereum, the Fantom bridge MPC EOA `0xC564EE9f21Ed8A2d8E7e76c085740d5e4c5FaFbE` sent 1,023.8 WBTC to `0x622e5f32e9ed5318d3a05ee2932fd3e118347ba0`, 7,214 WETH to `0x418ed2554c010a0c63024d1da3a93b4dc26e5bb7`, and 27,653,471 USDC and 30,138,618 USDC to `0x027f1571aca57354223276722dc7b572a5b05cd8` and `0xefeef8e968a0db92781ac7b3b7c821909ef10c88`, in blocks 17,636,491 to 17,636,642 (2023-07-06). These are plain ERC-20 transfers from an EOA: no router event marks them. The Moonriver and Dogechain outflows are not itemized here.
9. **Residual deposits with no payout.** The routers still accept out-calls. Examples: V7 `anySwapOutNative` on Ethereum until block 18,744,460 (2023-12-08); V3 router `anySwapOutUnderlying` at block 24,212,340 (2026-01-11); second V4 router `anySwapOutUnderlying` at block 25,794,608 (2026-08-20). No MPC pays them: treat a post-July-2023 `LogAnySwapOut` as funds that stay locked, not as a bridge transfer.
10. **Residual drains through stale approvals.** Block 25,882,636 (2026) on Ethereum: a contract (`0xf1d1aba8bd488c0f0b1ea4d2085b243091f9d410`, the caller and the "token") made the V4 router emit `LogAnySwapOut` with itself as `token`, and WETH moved from a wallet that had approved the router (`0x20f3b73d8521dcf7b60c7951ea407cb04d29f044`) to the caller. A `LogAnySwapOut` whose `token` is not an anyToken is not a bridge transfer: here it came with a WETH transfer out of a third-party wallet, the pattern of a drain of a stale router approval (inferred from this one transaction; the victim's approval was not read).
11. **Destination-leg events stop at the collapse.** The last V7 `LogAnySwapIn` on Ethereum in the explorer log list is at block 17,636,142 (2023-07-06). In the pinned window 2026-09-28 00:00 to 12:00 UTC, no Multichain router or anyToken topic was emitted on any of the eight chains (§14).
12. **One literal, different contracts.** `0x6b7a87899490EcE95443e979cA9485CBE7E71522` is the Ethereum V4 router but an anyToken on Arbitrum, Optimism and Polygon. `0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3` is the V7 router on five target chains and empty on BNB, where V7 is `0x400b971099e0ebFDa2C03a3063739cb5398734A6`. Key on `(chainId, address)`.
13. **Old bridge mode (not routers).** Tokens bridged by the Swapin/Swapout model emit `LogSwapout` (burn on the token chain) and `LogSwapin` (MPC mint, `txhash` = the deposit transaction on the other chain); the deposit side was often a plain transfer to an MPC EOA such as `0xC564EE9f21Ed8A2d8E7e76c085740d5e4c5FaFbE`, with no event.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Router topics V3 to V6 =====
TOPIC_LOG_ANY_SWAP_OUT              = '\x97116cf6cd4f6412bb47914d6db18da9e16ab2142f543b86e207c24fbd16b23a'
TOPIC_LOG_ANY_SWAP_OUT_STRING_V6    = '\x409e0ad946b19f77602d6cf11d59e1796ddaa4828159a0b4fb7fa2ff6b161b79'
TOPIC_LOG_ANY_SWAP_IN               = '\xaac9ce45fe3adf5143598c4f18a369591a20a3384aedaf1b525d29127e1fcd55'
TOPIC_LOG_TRADE_TOKENS_FOR_TOKENS   = '\xfea6abdf4fd32f20966dff7619354cd82cd43dc78a3bee479f04c74dbfc585b3'
TOPIC_LOG_TRADE_TOKENS_FOR_NATIVE   = '\x278277e0209c347189add7bd92411973b5f6b8644f7ac62ea1be984ce993f8f4'
TOPIC_LOG_CHANGE_MPC                = '\xcda32bc39904597666dfa9f9c845714756e1ffffad55b52e0d344673a2198121'
-- ===== Router topics V7 =====
TOPIC_V7_LOG_ANY_SWAP_OUT           = '\x0d969ae475ff6fcaf0dcfa760d4d8607244e8d95e9bf426f8d5d69f9a3e525af'
TOPIC_V7_LOG_ANY_SWAP_OUT_AND_CALL  = '\x968608314ec29f6fd1a9f6ef9e96247a4da1a683917569706e2d2b60ca7c0a6d'
TOPIC_V7_LOG_ANY_SWAP_IN            = '\x164f647883b52834be7a5219336e455a23a358be27519d0442fc0ee5e1b1ce2e'
TOPIC_V7_LOG_ANY_SWAP_IN_AND_EXEC   = '\x603ea9944a12c4ef108a97399c705891f182d169a361b6aa6455d14aa1cdd258'
TOPIC_V7_LOG_RETRY_EXEC_RECORD      = '\x2d044017b61f24f5423ce5e0c62f9ead27cb38f1615069e703ba521d0b04696b'
TOPIC_V7_LOG_RETRY_SWAPIN_AND_EXEC  = '\x4024f72e00ae47f03ed1dd3ab595d04dabdc9d1f95f8c039bca61946d9da0eb3'
TOPIC_V7_LOG_CHANGE_MPC             = '\x581f388e3dd32e1bbf62a290f509c8245f9d0b71ef82614fb2b967ad0a10d5b9'
TOPIC_V7_LOG_APPLY_MPC              = '\x8d32c9dd498e08090b44a0f77fe9ec0278851f9dffc4b430428411243e7df076'
TOPIC_V7_PAUSED                     = '\x0cb09dc71d57eeec2046f6854976717e4874a3cf2d6ddeddde337e5b6de6ba31'
-- ===== anyToken topics =====
TOPIC_LOG_SWAPIN                    = '\x05d0634fe981be85c22e2942a880821b70095d84e152c3ea3c17a4e4250d9d61'
TOPIC_LOG_SWAPOUT                   = '\x6b616089d04950dc06c45c6dd787d657980543f89651aec47924752c7d16c888'
TOPIC_LOG_CHANGE_VAULT              = '\x5c364079e7102c27c608f9b237c735a1b7bfa0b67f27c2ad26bad447bf965cac'

-- ===== Selectors =====
SEL_ANY_SWAP_OUT                    = '\x241dc2df'
SEL_ANY_SWAP_OUT_UNDERLYING         = '\xedbdf5e2'
SEL_ANY_SWAP_OUT_NATIVE             = '\xa5e56571'
SEL_ANY_SWAP_OUT_UNDERLYING_PERMIT  = '\x8d7d3eea'
SEL_ANY_SWAP_OUT_STRING             = '\xc604b0b8'
SEL_ANY_SWAP_OUT_UNDERLYING_STRING  = '\x049b4e7e'
SEL_ANY_SWAP_OUT_NATIVE_STRING      = '\x540dd52c'
SEL_ANY_SWAP_IN                     = '\x825bb13c'
SEL_ANY_SWAP_IN_UNDERLYING          = '\x3f88de89'
SEL_ANY_SWAP_IN_AUTO                = '\x0175b1c4'
SEL_ANY_SWAP_OUT_AND_CALL_V7        = '\x6b4b4376'
SEL_CHANGE_MPC                      = '\x5b7b018c'
SEL_CHANGE_VAULT                    = '\x456862aa'
SEL_MPC                             = '\xf75c2664'

-- ===== Routers (per chain) =====
ETH_ROUTER_V3                       = '\xe95fd76cf16008c12ff3b3a937cb16cd9cc20284'
ETH_ROUTER_V4                       = '\x6b7a87899490ece95443e979ca9485cbe7e71522'
ETH_ROUTER_V4_B                     = '\x765277eebeca2e31912c9946eae1021199b39c61'
ETH_ROUTER_V6                       = '\xba8da9dcf11b50b03fd5284f164ef5cdef910705'
ETH_ROUTER_V7                       = '\x1633d66ca91ce4d81f63ea047b7b19beb92df7f3'
ARB_ROUTER_V3                       = '\x0cae51e1032e8461f4806e26332c030e34de3adb'
ARB_ROUTER_V4                       = '\xc931f61b1534eb21d8c11b24f3f5ab2471d4ab50'
ARB_ROUTER_V6                       = '\x650af55d5877f289837c30b94af91538a7504b76'
ARB_ROUTER_V7                       = '\x1633d66ca91ce4d81f63ea047b7b19beb92df7f3'
OP_ROUTER_V6                        = '\xdc42728b0ea910349ed3c6e1c9dc06b5fb591f98'
OP_ROUTER_V6_B                      = '\x80a16016cc4a2e6a2caca8a4a498b1699ff0f844'
OP_ROUTER_V7                        = '\x1633d66ca91ce4d81f63ea047b7b19beb92df7f3'
POLY_ROUTER_V3                      = '\xafaace7138ab3c2bcb2db4264f8312e1bbb80653'
POLY_ROUTER_V4                      = '\x4f3aff3a747fcade12598081e80c6605a8be192f'
POLY_ROUTER_V6                      = '\x2ef4a574b72e1f555185afa8a09c6d1a8ac4025c'
POLY_ROUTER_V7                      = '\x1633d66ca91ce4d81f63ea047b7b19beb92df7f3'
BNB_ROUTER_V3                       = '\xf9736ec3926703e85c843fc972bd89a7f8e827c0'
BNB_ROUTER_V4                       = '\xabd380327fe66724ffda91a87c772fb8d00be488'
BNB_ROUTER_V6                       = '\xe1d592c3322f1f714ca11f05b6bc0efef1907859'
BNB_ROUTER_V7                       = '\x400b971099e0ebfda2c03a3063739cb5398734a6'
AVAX_ROUTER_V3                      = '\x9b17baadf0f21f03e35249e0e59723f34994f806'
AVAX_ROUTER_V4                      = '\xb0731d50c681c45856bfc3f7539d5f61d4be81d8'
AVAX_ROUTER_V6                      = '\x833f307ac507d47309fd8cdd1f835bef8d702a93'
AVAX_ROUTER_V6_B                    = '\x05f024c6f5a94990d32191d6f36211e3ee33504e'
AVAX_ROUTER_V7                      = '\x1633d66ca91ce4d81f63ea047b7b19beb92df7f3'
-- ===== V7 helpers =====
ETH_V7_ROUTER_SECURITY              = '\x9303e7b16ef03c22b657e7ba37c8ca88379c1a76'
ETH_V7_ANYCALL_EXECUTOR             = '\x38264fccb88da59ca4609c729031bfa8e7db24ef'
BNB_V7_ROUTER_SECURITY              = '\x78aa42f4770f6b53df9c2ea1d723010825a229c3'
BNB_V7_ANYCALL_EXECUTOR             = '\xb61a105123fede32cccbbc08f43bee81c0353efe'
-- ===== MPC and bridge EOAs (Ethereum) =====
ETH_MPC_V4_V6_EOA                   = '\x2a038e100f8b85df21e4d44121bdbfe0c288a869'
ETH_MPC_V3_EOA                      = '\xf39fee2fdfe7db022591f4a82e3537fa0b55fb9c'
ETH_MPC_V4_B_EOA                    = '\x647dc1366da28f8a64eb831fc8e9f05c90d1ea5a'
ETH_MPC_V7_EOA                      = '\x5608b26cc2996351c4d1289b867888081a9d4244'
ETH_FANTOM_BRIDGE_MPC_EOA           = '\xc564ee9f21ed8a2d8e7e76c085740d5e4c5fafbe'
ETH_MOONRIVER_BRIDGE_MPC_EOA        = '\x10c6b61dbf44a083aec3780acf769c77be747e23'
-- ===== July 2023 outflow receivers (Ethereum EOAs) =====
ETH_JUL2023_WBTC_RECEIVER_EOA       = '\x622e5f32e9ed5318d3a05ee2932fd3e118347ba0'
ETH_JUL2023_WETH_RECEIVER_EOA       = '\x418ed2554c010a0c63024d1da3a93b4dc26e5bb7'
ETH_JUL2023_USDC_RECEIVER_A_EOA     = '\x027f1571aca57354223276722dc7b572a5b05cd8'
ETH_JUL2023_USDC_RECEIVER_B_EOA     = '\xefeef8e968a0db92781ac7b3b7c821909ef10c88'
-- Base (8453) and Robinhood Chain (4663): no Multichain router (eth_getCode = 0x at all 21 router literals)
```

---

## 14. Verification and sources

How the constants were verified (2026-09-29):

- **Topic0 and selectors:** recomputed as `keccak256(canonical signature)` from `AnyswapV3Router.sol`, `AnyswapV5Router.sol`, `AnyswapV6Router.sol`, `AnyswapV4ERC20.sol`, `AnyswapV5ERC20.sol`, `AnyswapV6ERC20.sol` (`anyswap/anyswap-v1-core`), `MultichainV7Router.sol`, `MPCManageable.sol`, `MPCAdminControl.sol`, `PausableControl.sol`, `SwapInfo.sol` (`anyswap/multichain-smart-contracts`), and the verified `AnyswapV4Router` source of `0x6b7a87899490EcE95443e979cA9485CBE7E71522` (its interface equals `AnyswapV5Router.sol` without `anySwapOutNative`, `depositNative` and `withdrawNative`). The verified `AnyswapV3Router` source of `0xe95fD76CF16008c12FF3b3a937CB16Cd9Cc20284` has the same interface as the repository file.
- **Router versions:** each router was classified by its verified explorer name (Ethereum, Arbitrum, Optimism, Polygon) and, on every chain, by version-specific selectors found in its bytecode (`anySwapOutAndCall` and `setRouterSecurity` for V7; `setMinter` and the string `anySwapOut` for V6; `anySwapOutUnderlyingWithPermit` for V3 and V4) and by `mpc()`.
- **Live logs (positive controls):** Ethereum V4 router, blocks 14,006,710 to 14,011,709 (January 2022): 343 `LogAnySwapOut`, 203 `LogAnySwapIn`. Ethereum V6 router, blocks 17,162,287 to 17,167,286 (May 2023): 89 / 400; V7 router in the same range: 1 V7 `LogAnySwapIn`. Ethereum V3 router and second V4 router, blocks 15,053,226 to 15,058,225: 23 / 11 and 71 / 37. 10,000-block windows from 2023-05-01: Arbitrum V6 9 / 8, Arbitrum V4 15 / 19; Optimism V6 38 / 26, second V6 0 / 6; Polygon V6 4 / 3, V4 137 / 64; Avalanche V6 4 / 4, V4 30 / 8, second V6 17 `LogAnySwapIn` and 7 string `LogAnySwapOut`; the V7 router had 0 logs in these four windows. anyToken topics on Ethereum, blocks 14,006,710 to 14,011,709: 14 `LogSwapin`, 220 `LogSwapout`.
- **Sample transactions read with `eth_getTransactionReceipt` (Ethereum):** `0x739802f7611f31e532bd893602107adb12ffc91fdeaac56cf5eaad121bf29b47` (`anySwapOutUnderlying`, 22,674.9 USDC from the user to anyUSDC, anyUSDC mint and burn, `LogAnySwapOut`); `0xe514c2da10555d5e206a63c84368324fc48b30a21b4a98b0ddaabdec3c6f80d5` (`anySwapInAuto` from the MPC, anyToken mint and burn, underlying paid from the anyToken contract, `LogAnySwapIn`); `0xb6a084788a5cf47ebaabea6db6d3a425b60636bd33d9059e15d15ca1e50ac128` (V7 `anySwapOutNative`, 0.039 ETH wrapped and moved to the anyToken, V7 `LogAnySwapOut` to chain 56); `0xed52c1f04a2072c7f406e9dd4640e2a137dfc00be5fb274c9c4f7088885298bd` (V7 `anySwapIn` from the V7 MPC, USDC paid to the receiver); `0x63406b9c5790f4c8e9a7ee02a2a0c0dc250911226096220bf95ca36ba35d9dd7` (the 2026 approval drain of §12, item 10); `0x448f2a6a6c071cdce254937e06305a033538e1aeb9339227d0e59e0458e6185c`, `0xda80a8c8d5a8fdf0208a6fd01c39af018e400763b1d08f3543f52353345fe62e`, `0xbd29fe07555c28527fb0207aa0ac2b67d4afef0426793c35b76d005613477fc4`, `0xb9f52d5eb0d67c1038debe8e0f60ed265bd4937db0cfe5ef15b3f1fa28f31f8d` (the July 2023 outflows of §12, item 8).
- **Pinned 12-hour window 2026-09-28 00:00 to 12:00 UTC:** one pass per chain over the 19 router and anyToken topics of §13 (OR filter, any emitter). Every Multichain router topic and every anyToken topic: Ethereum 0, Base 0, Arbitrum 0, Optimism 0, Polygon 0, BNB 0, Avalanche 0, Robinhood 0. The only hits were one `LogChangeMPC` per chain from emitters of another bridge (§12, item 7).
- **Addresses:** the router list of Multichain's `anyswap/bridges-server` adapter (`src/adapters/multichain/index.ts`), the official Router V7 mainnet page, and `mpc()` of the anyToken at `0x6b7a87899490EcE95443e979cA9485CBE7E71522` on Optimism (which pointed to the second Optimism V6 router). Every address was checked with `eth_getCode`; EOAs by nonce. The MPC EOAs were checked on Ethereum, Arbitrum, Optimism, Polygon, BNB and Avalanche (no code on any; nonces from 0 to 737,567); the bridge EOAs on Ethereum.
- **Not verified:** the Dogechain bridge address; routers that Multichain deployed outside the adapter list; the BNB history (the public BNB endpoints refuse archive log queries); the trade events and the V7 call variants were not seen in the sampled windows.

Sources:
- [anyswap/anyswap-v1-core](https://github.com/anyswap/anyswap-v1-core) (`contracts/AnyswapV3Router.sol`, `contracts/AnyswapV5Router.sol`, `contracts/AnyswapV6Router.sol`, `contracts/AnyswapV4ERC20.sol`, `contracts/AnyswapV5ERC20.sol`, `contracts/AnyswapV6ERC20.sol`)
- [anyswap/multichain-smart-contracts](https://github.com/anyswap/multichain-smart-contracts) (`contracts/router/MultichainV7Router.sol`, `contracts/router/interfaces/SwapInfo.sol`, `contracts/access/MPCManageable.sol`, `contracts/access/PausableControl.sol`)
- [anyswap/bridges-server: `src/adapters/multichain/index.ts`](https://github.com/anyswap/bridges-server/blob/master/src/adapters/multichain/index.ts) (router and bridge-EOA list per chain)
- [Multichain docs: Bridge funds and anyCall (Router V7), Mainnet](https://docs.multichain.org/developer-guide/bridge-funds-and-anycall-router-v7/mainnet) · [Cross-Chain Router](https://docs.multichain.org/getting-started/how-it-works/cross-chain-router)
- [CoinDesk, 2023-07-06: "Multichain Bridges Exploited for Nearly $130M Across Fantom, Moonriver and Dogechain"](https://www.coindesk.com/business/2023/07/06/multichain-bridges-experience-unannounced-outflows-of-over-130m-in-crypto)
- Explorers: [Blockscout Router V4 (Ethereum)](https://eth.blockscout.com/address/0x6b7a87899490EcE95443e979cA9485CBE7E71522) · [Blockscout Router V7 (Ethereum)](https://eth.blockscout.com/address/0x1633D66Ca91cE4D81F63Ea047B7B19Beb92dF7f3) · [Blockscout Router V6 (Ethereum)](https://eth.blockscout.com/address/0xBa8Da9dcF11B50B03fd5284f164Ef5cdEF910705) · [Optimism explorer, second V6 router](https://explorer.optimism.io/address/0x80A16016cC4A2E6a2CACA8a4a498b1699fF0f844) · [Arbitrum Blockscout](https://arbitrum.blockscout.com/address/0x650Af55D5877F289837c30b94af91538a7504b76) · [Polygon Blockscout](https://polygon.blockscout.com/address/0x4f3Aff3A747fCADe12598081e80c6605A8be192F)
