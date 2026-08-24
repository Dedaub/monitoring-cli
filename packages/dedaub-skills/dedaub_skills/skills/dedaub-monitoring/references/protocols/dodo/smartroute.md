# DODO Smart-Route / Trading-Entry Layer — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon)

**Status:** verified against live RPC on every listed chain and the canonical `DODOEX/contractV2`, `DODOEX/dodo-route-contract`, and `DODOEX/dodo-limit-order` repos on 2026-06-02.
**Scope:** DODO's trading-entry / smart-route infrastructure — the token-allowance layer (DODOApprove, DODOApproveProxy), the swap/route entry contracts (DODOV2Proxy, RouteProxy, DODOFeeRouteProxy + widget variant), the create+liquidity entry contracts (DSPProxy, CpProxy, DPPProxy), the per-venue swap adapters (DODOV1Adapter, DODOV2Adapter, UniAdapter, CurveAdapter), the read-only quoting/aggregation helpers (DODOV2RouteHelper, DODOCalleeHelper, DODOSellHelper, DODOV1PmmHelper, DODOSwapCalcHelper, ERC20Helper, MultiCall, CurveSample), and the limit-order settlement layer (LimitOrder, LimitOrderBot). Covers Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137). Topics and 4-byte selectors are **chain-agnostic** (computed from the canonical signature); **addresses are network-specific**. This file deliberately excludes the AMM pool/factory/template layer and the token/NFT/staking contracts.

Three orientation facts a monitoring engineer must internalise:

1. **The DODO "Proxy" contracts here are NOT EIP-1967 upgradeable proxies.** Despite the name, `DODOV2Proxy`, `RouteProxy`, `DODOFeeRouteProxy`, `DSPProxy`, `CpProxy`, `DPPProxy`, `DODOApprove`, and `DODOApproveProxy` are **immutable router / entry contracts** (the same role as Uniswap's `SwapRouter`). The EIP-1967 implementation slot (`0x360894…bbc`) reads `0x0` on every one of them on every chain — there is no implementation to follow, no `Upgraded` event to watch. To "upgrade" a router DODO deploys a new contract at a new address and registers it (see fact 2). Treat each address as a fixed, version-pinned deployment; track the **set** of router addresses, not an upgrade pointer. (DODO V2 *pools* are EIP-1167 minimal-proxy clones — but pools are out of scope here.)

2. **All token custody flows through one allowance hub: `DODOApprove`.** Users `approve()` the per-chain `DODOApprove` contract (never the routers). `DODOApprove` will only `transferFrom` on behalf of its single registered caller, `_DODO_PROXY_`, which is the per-chain **`DODOApproveProxy`**. `DODOApproveProxy` in turn holds a `mapping(address => bool) _IS_ALLOWED_PROXY_` registry of every router/settlement contract permitted to pull user funds (`DODOV2Proxy`, `RouteProxy`, both `DODOFeeRouteProxy` variants, `DSPProxy`, `DPPProxy`, `LimitOrder`, …). Every swap entrypoint calls `IDODOApproveProxy(_DODO_APPROVE_PROXY_).claimTokens(token, user, dest, amount)` to source the input token. This two-hop design (`DODOApprove` → `DODOApproveProxy` → router) is why a *new* router can be added without users re-approving: only `DODOApproveProxy._IS_ALLOWED_PROXY_` changes (after a 3-day timelock). **Watch `SetDODOProxy` on `DODOApprove` and the timelock state on `DODOApproveProxy` to detect new authorized spenders.**

3. **The single highest-value monitoring topic is `OrderHistory`.** Every user-facing swap entry contract — `DODOV2Proxy`, `RouteProxy`, and `DODOFeeRouteProxy` (+ widget) — emits the identical event `OrderHistory(address fromToken, address toToken, address sender, uint256 fromAmount, uint256 returnAmount)` (all five fields **non-indexed**), with **topic0 `0x92ceb067a9883c85aba061e46b9edf505a0d6e81927c4b966ebed543a5221787`**. Filtering on this one topic0 across the router address-set captures essentially all DODO-routed swap volume per chain. The adapters and the create/liquidity proxies (DSP/Cp/DPP) emit **no** swap event of their own — the route proxy that drove the hop emits the single `OrderHistory`.

---

## 0. Contract families & versions

DODO's route layer accreted over three generations. They coexist on-chain; all are live and all emit the same `OrderHistory` topic0.

| Family | Contract(s) | Role | Token-pull path | Emits |
|--------|-------------|------|-----------------|-------|
| **Allowance hub** | `DODOApprove` | Sole `transferFrom` holder; users approve this. Single registered caller `_DODO_PROXY_` = `DODOApproveProxy`. | — (is the source) | `SetDODOProxy` |
| | `DODOApproveProxy` | Registry of routers allowed to call `DODOApprove`. 3-day timelock to add. | — | (Ownable only) |
| **Gen-1 entry (V2 pairs)** | `DODOV2Proxy` (`DODOV2Proxy02`) | Main legacy entry: `dodoSwapV1/V2*`, `externalSwap`, DVM create + add/remove liquidity, V1 liquidity. Hard-codes DODO V1/V2 pool hops (no adapter abstraction). | `claimTokens` → pool | `OrderHistory` |
| **Gen-2 aggregator (adapters)** | `RouteProxy` (`DODORouteProxy`) | Standalone split aggregator: `mixSwap` (linear) + `dodoMutliSwap` (split). Delegates each hop to an **adapter**. **No fee, no `externalSwap`.** | `claimTokens` → adapter/pool | `OrderHistory` |
| **Gen-3 fee aggregator** | `DODOFeeRouteProxy` | Adapter aggregator **with route fee + broker rebate**: `mixSwap`, `dodoMutliSwap`, `externalSwap`. Charges `routeFeeRate` (default 0.15%) to `routeFeeReceiver` + a per-call broker fee. | `claimTokens` → adapter/pool | `OrderHistory` |
| | `DODOFeeRouteProxy(widget)` | **Byte-identical** code to `DODOFeeRouteProxy` (verified same runtime hash) — a second deployment with a different fee receiver for the DODO Widget integration. | same | `OrderHistory` |
| **Create+LP entry** | `DSPProxy` (`DODODspProxy`) | Create DODO Stable Pool + add liquidity (`createDODOStablePair`, `addDSPLiquidity`). | `claimTokens` → pool | (none) |
| | `CpProxy` (`DODOCpProxy`) | Create CrowdPooling + `bid`. | `claimTokens` → pool | (none) |
| | `DPPProxy` (`DODODppProxy`) | Create + reset DODO Private Pool. | `claimTokens` → pool | (none) |
| **Adapters** (stateless) | `DODOV1Adapter`, `DODOV2Adapter`, `UniAdapter`, `CurveAdapter` | Thin per-venue hop executors used by `RouteProxy`/`DODOFeeRouteProxy`. Common interface `sellBase(address,address,bytes)` / `sellQuote(address,address,bytes)`. | (route proxy pre-funds them) | (none) |
| **Read-only helpers** | `DODOV2RouteHelper`, `DODOCalleeHelper`, `DODOSellHelper`, `DODOV1PmmHelper`, `DODOSwapCalcHelper`, `ERC20Helper`, `MultiCall`, `CurveSample` | Off-chain quoting / pair-detail / sampling / multicall. View-only; **no events**. | — | (none) |
| **Limit orders** | `LimitOrder` (`DODOLimitOrder`) | EIP-712 limit-order settlement. `fillLimitOrder` pulls maker tokens via `DODOApproveProxy`; taker pays directly. | `claimTokens` (maker side) | `LimitOrderFilled`, `AddWhiteList`, `RemoveWhiteList`, `ChangeFeeReceiver` |
| | `LimitOrderBot` (`DODOLimitOrderBot`) | Keeper that calls `LimitOrder.fillLimitOrder` and routes the maker token through a route proxy. | — | `Fill`, `addAdmin`, `removeAdmin`, `changeReceiver` |

**Generation note (deployed bytecode).** The `DODOFeeRouteProxy` listed in the address registry (§3–§9) on **all 7 chains** is the **`dodo-route-contract`** "older" build (≈10 945 B) — `externalSwap`/`mixSwap`/`dodoMutliSwap` *without* an `expReturnAmount` argument, does **not** emit `PositiveSlippage`. `DODOEX/contractV2` contains a **newer** `DODOFeeRouteProxy` variant that adds an `expReturnAmount` parameter to each swap function and a `PositiveSlippage(address,uint256)` event. **That newer build IS deployed on Ethereum** at `0xFe837A3530dD566401d35beFCd55582AF7c4dfFC` (Etherscan-tagged "DODO: Fee Route Proxy", ≈11 202 B, wired to the same `DODOApproveProxy` `0x335aC99…`; the `PositiveSlippage` topic0 is present in its runtime — verified live). So **Ethereum runs both fee-proxy builds** (registry `0x50f9bDe1…` older + `0xFe837A35…` newer). On the other 6 chains only the older build is confirmed at the registry address; a separate newer deployment there (if any) is unconfirmed — probe each chain's fee-route set and watch for `PositiveSlippage`. Selectors for both builds are in §2.5/§2.6.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Swap entry contracts — `OrderHistory` (the workhorse)

Emitted by `DODOV2Proxy`, `RouteProxy`, **and** `DODOFeeRouteProxy` (+ widget). Same signature, same topic0 everywhere.

| topic0 | Event |
|--------|-------|
| `0x92ceb067a9883c85aba061e46b9edf505a0d6e81927c4b966ebed543a5221787` | `OrderHistory(address fromToken, address toToken, address sender, uint256 fromAmount, uint256 returnAmount)` |

All five fields are **non-indexed** → the log has exactly **1 topic** (topic0) and a **160-byte (5-word) data** payload: `fromToken`, `toToken`, `sender`, `fromAmount`, `returnAmount`. `sender` is the EOA/contract that called the entry function (`msg.sender`), `fromAmount` is the gross input, `returnAmount` is the net output delivered to the user (after route + broker fee on `DODOFeeRouteProxy`). `fromToken`/`toToken` use the sentinel `0xEeee…EEeE` for native ETH/gas-token legs. Verified live: present with topic0 above, 1 topic, 5 data words, on the Ethereum `DODOV2Proxy` (`0xa356867f…FdC`), the Ethereum `RouteProxy` (`0xa2398842…D28a`), and the Ethereum `DODOFeeRouteProxy` (`0x50f9bDe1…6194`).

### 1.2 DODOApprove

| topic0 | Event |
|--------|-------|
| `0xd356351ffbb32d7a93878d5fbbd5c39435bbae136f428b0d574242f63bb803cb` | `SetDODOProxy(address indexed oldProxy, address indexed newProxy)` |

`SetDODOProxy` fires when the single authorized caller (`_DODO_PROXY_`, normally `DODOApproveProxy`) is rotated — a **high-severity** security signal (it would re-point the entire allowance hub). Both fields indexed.

### 1.3 LimitOrder (`DODOLimitOrder`)

| topic0 | Event |
|--------|-------|
| `0x30a60b21c24c8f631a1e032527b3ee9a12b7e1fce164b4273c40f5db96415245` | `LimitOrderFilled(address indexed maker, address indexed taker, bytes32 orderHash, uint256 curTakerFillAmount, uint256 curMakerFillAmount)` |
| `0xf8d5f40934646cedded2cab1b5960f020db583f154fabcf831277b87d1803d13` | `AddWhiteList(address addr)` |
| `0x1e17ee0599b7c09bb1d0ff1e8086007909da8bfba5c7d18319cb558e66db37ee` | `RemoveWhiteList(address addr)` |
| `0xfb29108df6ec24f97dfbe39fff6bb9357a54e758efed2c6e7b5fb76b26b30f81` | `ChangeFeeReceiver(address newFeeReceiver)` |

`LimitOrderFilled` verified live on the Ethereum `LimitOrder` (`0x093b68BF…17EB`): 3 topics (sig + indexed `maker`, `taker`) and 3 data words (`orderHash`, `curTakerFillAmount`, `curMakerFillAmount`). **There is no on-chain cancel event** — see §9 gotcha 7. Orders fill incrementally; cumulative fill is tracked in `_FILLED_TAKER_AMOUNT_[orderHash]`.

### 1.4 LimitOrderBot (`DODOLimitOrderBot`)

| topic0 | Event |
|--------|-------|
| `0xcb78302ec72136bfa852ed66b453ff3802e5959bb4df8386cd9695cae88de2e9` | `Fill()` |
| `0x7048027520ecbaa8947764cd502c5c78c2c53bbd902e06b108da1cbdf98c6fc4` | `addAdmin(address admin)` |
| `0x1785f53c768259a7ab38ed67e958aab075b56ff206e3d7f29ea4ca203d1a9774` | `removeAdmin(address admin)` |
| `0x547e3f060aba0f7eec865fc52a952a5148e4903d709e38cde9c93b655ce0b057` | `changeReceiver(address newReceiver)` |

`Fill()` is a zero-arg marker emitted after a bot-driven fill settles. Admin events are non-indexed.

### 1.5 Ownership (InitializableOwnable / OZ Ownable)

`DODOApprove`, `DODOApproveProxy`, `DODOV2Proxy`, `LimitOrder`, and `LimitOrderBot` use DODO's `InitializableOwnable`; `RouteProxy`/`DODOFeeRouteProxy` use OpenZeppelin `Ownable`. Watch these for admin takeover.

| topic0 | Event | Source |
|--------|-------|--------|
| `0xdcf55418cee3220104fef63f979ff3c4097ad240c0c43dcb33ce837748983e62` | `OwnershipTransferPrepared(address indexed previousOwner, address indexed newOwner)` | InitializableOwnable (two-step) |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | InitializableOwnable **and** OZ Ownable (same sig) |

`InitializableOwnable` is two-step: `OwnershipTransferPrepared` (on `transferOwnership`) then `OwnershipTransferred` (on `claimOwnership`). `DODOFeeRouteProxy`/`RouteProxy` (OZ Ownable) emit only `OwnershipTransferred`.

### 1.6 Contracts that emit NO events

`DSPProxy`, `CpProxy`, `DPPProxy`, the four adapters (`DODOV1/V2/Uni/Curve`Adapter), and every read-only helper (`DODOV2RouteHelper`, `DODOCalleeHelper`, `DODOSellHelper`, `DODOV1PmmHelper`, `DODOSwapCalcHelper`, `ERC20Helper`, `MultiCall`, `CurveSample`) declare **no events**. For DSP/Cp/DPP creation, watch the *factory* `NewDSP`/`NewCP`/`NewDPP` events (AMM layer, out of scope) plus the pool's own `BuyShares`/`Bid`; for adapter activity, watch the driving route proxy's `OrderHistory` and the touched pool's swap events.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 DODOApprove

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x0a5ea466` | `claimTokens(address token, address who, address dest, uint256 amount)` | **Only callable by `_DODO_PROXY_`.** `safeTransferFrom(who → dest)`. This is the privileged token-pull. |
| `0x31fa1319` | `getDODOProxy()` | `address` — the single authorized caller (= `DODOApproveProxy`). |
| `0xe54c8033` | `_DODO_PROXY_()` | `address` — same value as `getDODOProxy()` (public storage getter). |
| `0x93773aec` | `_PENDING_DODO_PROXY_()` | `address` — pending rotation target during timelock. |
| `0xb75dbf68` | `_TIMELOCK_()` | `uint256` — unix ts after which `setDODOProxy()` may execute. |
| `0xf09a4016` | `init(address owner, address initProxyAddress)` | One-shot initializer. |
| `0x41c256c1` | `unlockSetProxy(address newDodoProxy)` | Owner-only. Starts 3-day (or 24-h if first) timelock. |
| `0x4f3cef84` | `lockSetProxy()` | Owner-only. Cancels pending. |
| `0x8cdb6574` | `setDODOProxy()` | Owner-only, post-timelock. Emits `SetDODOProxy`, rotates `_DODO_PROXY_`. |

### 2.2 DODOApproveProxy

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x48a4f993` | `isAllowedProxy(address _proxy)` | `bool` — **the authorization oracle.** Returns true for every router/settlement contract allowed to pull funds. |
| `0x3b2f27bb` | `_IS_ALLOWED_PROXY_(address)` | `bool` — same mapping, public storage getter. |
| `0x0a5ea466` | `claimTokens(address token, address who, address dest, uint256 amount)` | Callable only by an allowed proxy; forwards to `DODOApprove.claimTokens`. |
| `0x46e74298` | `_DODO_APPROVE_()` | `address` (immutable) — the `DODOApprove` it fronts. |
| `0x374445b2` | `unlockAddProxy(address newDodoProxy)` | Owner-only. Starts 3-day timelock to add a proxy. |
| `0x556d65a8` | `lockAddProxy()` | Owner-only. Cancels pending add. |
| `0x3e688589` | `addDODOProxy()` | Owner-only, post-timelock. Sets `_IS_ALLOWED_PROXY_[pending] = true`. |
| `0x2c419f2f` | `removeDODOProxy(address oldDodoProxy)` | Owner-only, **immediate** (no timelock). Revokes a proxy. |
| `0xcc646ed4` | `_PENDING_ADD_DODO_PROXY_()` | `address` — pending add target. |
| `0x3c5a3cea` | `init(address owner, address[] proxies)` | One-shot initializer with seed allow-list. |

### 2.3 DODOV2Proxy (`DODOV2Proxy02`) — gen-1 entry

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x0dd4ebd9` | `dodoSwapV1(address fromToken, address toToken, uint256 fromTokenAmount, uint256 minReturnAmount, address[] dodoPairs, uint256 directions, bool, uint256 deadLine)` | `payable`. Routes through DODO **V1** pools. Emits `OrderHistory`. |
| `0x5028bb95` | `dodoSwapV2ETHToToken(address toToken, uint256 minReturnAmount, address[] dodoPairs, uint256 directions, bool, uint256 deadLine)` | `payable`. ETH→token via V2 pools. |
| `0x1e6d24c2` | `dodoSwapV2TokenToETH(address fromToken, uint256 fromTokenAmount, uint256 minReturnAmount, address[] dodoPairs, uint256 directions, bool, uint256 deadLine)` | token→ETH via V2 pools. |
| `0xf87dc1b7` | `dodoSwapV2TokenToToken(address fromToken, address toToken, uint256 fromTokenAmount, uint256 minReturnAmount, address[] dodoPairs, uint256 directions, bool, uint256 deadLine)` | token→token via V2 pools. |
| `0x54bacd13` | `externalSwap(address fromToken, address toToken, address approveTarget, address swapTarget, uint256 fromTokenAmount, uint256 minReturnAmount, bytes callDataConcat, bool, uint256 deadLine)` | `payable`. Calls a whitelisted external router (0x/1inch/paraswap). Emits `OrderHistory`. |
| `0x8b3bb089` | `createDODOVendingMachine(address baseToken, address quoteToken, uint256 baseInAmount, uint256 quoteInAmount, uint256 lpFeeRate, uint256 i, uint256 k, bool isOpenTWAP, uint256 deadLine)` | `payable`. Creates a DVM + seeds liquidity. Returns `(address, uint256)`. |
| `0x674d9422` | `addDVMLiquidity(address dvmAddress, uint256 baseInAmount, uint256 quoteInAmount, uint256 baseMinAmount, uint256 quoteMinAmount, uint8 flag, uint256 deadLine)` | `payable`. Returns `(shares, baseAdj, quoteAdj)`. |
| `0x99882c8f` | `addLiquidityToV1(address pair, uint256 baseAmount, uint256 quoteAmount, uint256 baseMinShares, uint256 quoteMinShares, uint8 flag, uint256 deadLine)` | `payable`. DODO V1 LP. |
| `0xe7cd4a04` | `addWhiteList(address contractAddr)` | Owner-only. Whitelists an `externalSwap` target. |
| `0x2042e5c2` | `removeWhiteList(address contractAddr)` | Owner-only. |
| `0x6f9170f6` | `isWhiteListed(address)` | `bool`. |
| `0x0d4eec8f` | `_WETH_()` | `address` (immutable). |
| `0xeb99be12` | `_DODO_APPROVE_PROXY_()` | `address` (immutable). |
| `0xaf1280b0` | `_DODO_SELL_HELPER_()` | `address` (immutable). |
| `0x69e4e417` | `_DVM_FACTORY_()` | `address` (immutable). |

`mixSwap` is **not** present on `DODOV2Proxy02` (it is commented out in the interface); use `RouteProxy`/`DODOFeeRouteProxy` for adapter-based mixSwap. The trailing `bool` arg in the swap functions is the legacy `isIncentive` flag (ignored by the deployed contract; does not change the selector).

### 2.4 RouteProxy (`DODORouteProxy`) — gen-2 aggregator (no fee)

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0x7617b389` | `mixSwap(address fromToken, address toToken, uint256 fromTokenAmount, uint256 minReturnAmount, address[] mixAdapters, address[] mixPairs, address[] assetTo, uint256 directions, bytes[] moreInfos, uint256 deadLine)` | `payable`. Linear route (one pool per hop). Emits `OrderHistory`. |
| `0x81791788` | `dodoMutliSwap(uint256 fromTokenAmount, uint256 minReturnAmount, uint256[] totalWeight, uint256[] splitNumber, address[] midToken, address[] assetFrom, bytes[] sequence, uint256 deadLine)` | `payable`. Split route (note `mutli` typo is canonical). Emits `OrderHistory`. |
| `0x0d4eec8f` | `_WETH_()` | `address` (immutable). |
| `0xeb99be12` | `_DODO_APPROVE_PROXY_()` | `address` (immutable). |

`RouteProxy` has **no** `externalSwap` and **no** fee logic. (Distinguishes it from `DODOFeeRouteProxy`.) Its `dodoMutliSwap` carries a `uint256[] totalWeight` argument that the fee variants drop.

### 2.5 DODOFeeRouteProxy (+ widget) — gen-3 aggregator with fee (**deployed selectors**)

The deployed build on all 7 chains. `externalSwap`/`mixSwap`/`dodoMutliSwap` take **no** `expReturnAmount`.

| Selector | Signature | Returns / notes |
|----------|-----------|-----------------|
| `0xa8676443` | `externalSwap(address fromToken, address toToken, address approveTarget, address swapTarget, uint256 fromTokenAmount, uint256 minReturnAmount, bytes feeData, bytes callDataConcat, uint256 deadLine)` | `payable`. External router call; `feeData = abi.encode(broker, brokerFeeRate)`. Emits `OrderHistory`. |
| `0x301a3720` | `mixSwap(address fromToken, address toToken, uint256 fromTokenAmount, uint256 minReturnAmount, address[] mixAdapters, address[] mixPairs, address[] assetTo, uint256 directions, bytes[] moreInfos, bytes feeData, uint256 deadLine)` | `payable`. Linear route with fee. Emits `OrderHistory`. |
| `0x94cfab17` | `dodoMutliSwap(uint256 fromTokenAmount, uint256 minReturnAmount, uint256[] splitNumber, address[] midToken, address[] assetFrom, bytes[] sequence, bytes feeData, uint256 deadLine)` | `payable`. Split route with fee. Emits `OrderHistory`. |
| `0xe7cd4a04` | `addWhiteList(address)` | Owner-only. `externalSwap` target allow-list. |
| `0x2042e5c2` | `removeWhiteList(address)` | Owner-only. |
| `0x2a7bc4a8` | `addApproveWhiteList(address)` | Owner-only. `approveTarget` allow-list. |
| `0x4ab75563` | `removeApproveWhiteList(address)` | Owner-only. |
| `0x0c831085` | `changeRouteFeeRate(uint256 newFeeRate)` | Owner-only. Default `1.5e15` (0.15%). |
| `0x5af35118` | `changeRouteFeeReceiver(address)` | Owner-only. |
| `0x3b16827f` | `changeTotalWeight(uint256)` | Owner-only. |
| `0xb1dc7df9` | `superWithdraw(address token)` | Owner-only. Sweeps dust to `routeFeeReceiver`. |
| `0xb887bdac` | `routeFeeRate()` | `uint256`. |
| `0x4f3d2fd7` | `routeFeeReceiver()` | `address` — **differs** between the main and widget deployments. |
| `0x96c82e57` | `totalWeight()` | `uint256` (default 100). |
| `0xbc74f9ff` | `isWhiteListedContract(address)` | `bool`. |
| `0xe22367a4` | `isApproveWhiteListedContract(address)` | `bool`. |
| `0x0d4eec8f` | `_WETH_()` | `address` (immutable). |
| `0xeb99be12` | `_DODO_APPROVE_PROXY_()` | `address` (immutable). |

### 2.6 DODOFeeRouteProxy — newer (contractV2) variant, **deployed on Ethereum** (`0xFe837A35…`)

This variant adds an `expReturnAmount` param to each swap function and emits `PositiveSlippage(address,uint256)` (topic0 `0xd820290de56f193465e6c0b6140e6bedce58ba0d54229b2a57fd4b60d285297c`). It **is live on Ethereum** at `0xFe837A3530dD566401d35beFCd55582AF7c4dfFC` (Etherscan "DODO: Fee Route Proxy", ≈11 202 B; `PositiveSlippage` topic0 confirmed present in its runtime; same `OrderHistory` topic0 as the older build). On the other 6 chains the registry `DODOFeeRouteProxy` is the older build (no `expReturnAmount`, no `PositiveSlippage`); if these selectors / that topic0 appear at any fee-route address there, the newer build has been deployed.

| Selector | Signature |
|----------|-----------|
| `0x2fa11647` | `externalSwap(address, address, address, address, uint256, uint256 expReturnAmount, bytes, bytes, uint256)` |
| `0xff84aafa` | `mixSwap(address, address, uint256, uint256 expReturnAmount, uint256, address[], address[], address[], uint256, bytes[], bytes, uint256)` |
| `0x79b6f086` | `dodoMutliSwap(uint256, uint256 expReturnAmount, uint256, uint256[], address[], address[], bytes[], bytes, uint256)` |

### 2.7 Adapters (`IDODOAdapter` — DODOV1/V2/Uni/Curve)

All four adapters share one interface. Stateless; the route proxy pre-funds the adapter (or the pool) before calling.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x30e6ae31` | `sellBase(address to, address pool, bytes data)` | Sells the base token of `pool`, sends output `to`. `data` is venue-specific (`UniAdapter`: `(fee,denFee)`; `CurveAdapter`: `(bool noLending, fromToken, toToken, int128 i, int128 j)`; DODO adapters: empty). |
| `0x6f7929f2` | `sellQuote(address to, address pool, bytes data)` | Sells the quote token of `pool`. |
| `0xaf1280b0` | `_DODO_SELL_HELPER_()` | `address` — **`DODOV1Adapter` only** (immutable; the V1 pricing helper). |

`DODOV2Adapter` is the minimal case (`pool.sellBase(to)` / `pool.sellQuote(to)`, 496 B of source). `DODOV1Adapter` uses `DODOSellHelper` for V1 quote-side pricing. `UniAdapter` targets Uniswap-V2-style pools. `CurveAdapter` calls `exchange`/`exchange_underlying`.

### 2.8 DSPProxy (`DODODspProxy`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3d59492a` | `createDODOStablePair(address baseToken, address quoteToken, uint256 baseInAmount, uint256 quoteInAmount, uint256 lpFeeRate, uint256 i, uint256 k, bool isOpenTWAP, uint256 deadLine)` | `payable`. Returns `(address newDSP, uint256 shares)`. |
| `0xe24db1ac` | `addDSPLiquidity(address dspAddress, uint256 baseInAmount, uint256 quoteInAmount, uint256 baseMinAmount, uint256 quoteMinAmount, uint8 flag, uint256 deadLine)` | `payable`. Returns `(shares, baseAdj, quoteAdj)`. |
| `0x0d4eec8f` | `_WETH_()` | `address` (immutable). |
| `0xeb99be12` | `_DODO_APPROVE_PROXY_()` | `address` (immutable). |
| `0xfc382437` | `_DSP_FACTORY_()` | `address` (immutable). |

### 2.9 CpProxy (`DODOCpProxy`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x964e4c26` | `createCrowdPooling(address baseToken, address quoteToken, uint256 baseInAmount, uint256[] timeLine, uint256[] valueList, bool[] switches, uint256 deadLine, int256 globalQuota)` | `payable`. Returns `address payable newCP`. |
| `0xdb70b5c7` | `bid(address cpAddress, uint256 quoteAmount, uint8 flag, uint256 deadLine)` | `payable`. Bids into a CrowdPooling. |
| `0x0d4eec8f` | `_WETH_()` | `address` (immutable). |
| `0xeb99be12` | `_DODO_APPROVE_PROXY_()` | `address` (immutable). |
| `0xfaa980e4` | `_CP_FACTORY_()` | `address` (immutable). |

### 2.10 DPPProxy (`DODODppProxy`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x0d9be500` | `createDODOPrivatePool(address baseToken, address quoteToken, uint256 baseInAmount, uint256 quoteInAmount, uint256 lpFeeRate, uint256 i, uint256 k, bool isOpenTwap, uint256 deadLine)` | `payable`. Returns `address newDPP`. |
| `0x12ff148d` | `resetDODOPrivatePool(address dppAddress, uint256[] paramList, uint256[] amountList, uint8 flag, uint256 minBaseReserve, uint256 minQuoteReserve, uint256 deadLine)` | `payable`. Re-parameterizes a DPP (owner of the DPP). |
| `0x0d4eec8f` | `_WETH_()` | `address` (immutable). |
| `0xeb99be12` | `_DODO_APPROVE_PROXY_()` | `address` (immutable). |
| `0xb730d150` | `_DPP_FACTORY_()` | `address` (immutable). |

### 2.11 Read-only helpers

| Selector | Signature | Contract / notes |
|----------|-----------|------------------|
| `0x9d15e3ae` | `getPairDetail(address token0, address token1, address userAddr)` | **DODOV2RouteHelper** — enumerates DVM/DPP/DSP pools for a pair, returns `PairDetail[]` (PMM state + fee rates). |
| `0x69e4e417` | `_DVM_FACTORY_()` | DODOV2RouteHelper getter. |
| `0xb730d150` | `_DPP_FACTORY_()` | DODOV2RouteHelper getter. |
| `0xfc382437` | `_DSP_FACTORY_()` | DODOV2RouteHelper getter. |
| `0xef4a83f8` | `querySellBaseToken(address dodo, uint256 amount)` | **DODOSellHelper** — V1 base→quote quote. |
| `0xca19ebd9` | `querySellQuoteToken(address dodo, uint256 amount)` | **DODOSellHelper** — V1 quote→base quote (re-implements the DODO curve math). |
| `0x2bd8c5ac` | `getPairDetail(address pool)` | **DODOV1PmmHelper** — single-pool V1 `PairDetail[1]`. |
| `0x0683ecd9` | `calcReturnAmountV1(uint256 fromTokenAmount, address[] dodoPairs, uint8[] directions)` | **DODOSwapCalcHelper** — multi-hop V1 return + mid-prices + fee rates. |
| `0xaf1280b0` | `_DODO_SELL_HELPER_()` | DODOSwapCalcHelper getter. |
| `0x2411d338` | `DVMSellShareCall(address payable assetTo, uint256, uint256 baseAmount, uint256 quoteAmount, bytes)` | **DODOCalleeHelper** — pool callback for DVM share redemption. |
| `0x6430f110` | `CPCancelCall(address payable assetTo, uint256 amount, bytes)` | DODOCalleeHelper — CrowdPooling cancel callback. |
| `0x7ceef916` | `CPClaimBidCall(address payable assetTo, uint256 baseAmount, uint256 quoteAmount, bytes)` | DODOCalleeHelper — CrowdPooling claim callback. |
| `0x53c06360` | `NFTRedeemCall(address payable assetTo, uint256 quoteAmount, bytes)` | DODOCalleeHelper — fragment redeem callback. |
| `0x0d4eec8f` | `_WETH_()` | DODOCalleeHelper getter. |
| `0xf1a16c31` | `isERC20(address token, address user, address spender)` | **ERC20Helper** — safe metadata+balance+allowance probe (handles bytes32-name tokens). |
| `0xef9361db` | `judgeERC20(address, address, address)` | ERC20Helper. |
| `0x76cd81e3` | `judgeOldERC20(address, address, address)` | ERC20Helper (bytes32 name/symbol). |
| `0xd84fc88a` | `sampleFromCurve(address curveAddress, int128 fromTokenIdx, int128 toTokenIdx, uint256[] takerTokenAmounts)` | **CurveSample** (contract `CurveSampler`) — Curve `get_dy_underlying` sampler for the router. |
| `0x252dba42` | `aggregate((address target, bytes callData)[] calls)` | **MultiCall** — returns `(uint256 blockNumber, bytes[] returnData)`. Note: **not** Multicall3 (`aggregate3`). |
| `0x4d2301cc` | `getEthBalance(address)` | MultiCall helper. |

### 2.12 LimitOrder (`DODOLimitOrder`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd9df05cf` | `fillLimitOrder((address makerToken, address takerToken, uint256 makerAmount, uint256 takerAmount, address maker, address taker, uint256 expiration, uint256 salt) order, bytes signature, uint256 takerFillAmount, uint256 thresholdTakerAmount, bytes takerInteraction)` | `nonReentrant`. Returns `(curTakerFillAmount, curMakerFillAmount)`. Pulls maker token via `DODOApproveProxy`; taker pays directly. Emits `LimitOrderFilled`. |
| `0xf973a209` | `ORDER_TYPEHASH()` | `bytes32` = `0x9e31ac2990003b5142f3966f6d93f8ee4befc60049bcd8504dce6d014d939c8a` (verified on-chain) = `keccak256("Order(address makerToken,address takerToken,uint256 makerAmount,uint256 takerAmount,address maker,address taker,uint256 expiration,uint256 salt)")`. |
| `0x1068705b` | `_FILLED_TAKER_AMOUNT_(bytes32 orderHash)` | `uint256` — cumulative taker amount filled (orders are partially fillable). |
| `0x6f9170f6` | `isWhiteListed(address)` | `bool` — `takerInteraction` callback allow-list. |
| `0xeb99be12` | `_DODO_APPROVE_PROXY_()` | `address`. |
| `0x7161e0f2` | `_FEE_RECEIVER_()` | `address`. |
| `0xe7cd4a04` | `addWhiteList(address)` | Owner-only. Emits `AddWhiteList`. |
| `0x2042e5c2` | `removeWhiteList(address)` | Owner-only. Emits `RemoveWhiteList`. |
| `0x7c08b964` | `changeFeeReceiver(address)` | Owner-only. Emits `ChangeFeeReceiver`. |
| `0x184b9559` | `init(address owner, address dodoApproveProxy, address feeReceiver)` | One-shot initializer (clone-initialized). |

> **On the deployed bytecode:** the Ethereum `LimitOrder` (`0x093b…17EB`) exposes `fillLimitOrder`, `ORDER_TYPEHASH`, and `_FILLED_TAKER_AMOUNT_` but **`DOMAIN_SEPARATOR()` (`0x3644e515`) reverts and `version()` (`0x54fd4d50`) is absent** — i.e. the deployed contract predates the `version()`/public-`DOMAIN_SEPARATOR` build in the current `dodo-limit-order` source (the EIP-712 domain separator is computed internally). There is **no `cancelLimitOrder`** function (selector `0xf0dbead1` is absent) and **no cancel event** — makers void an order off-chain by letting it expire or by withdrawing the maker-token balance/allowance. Treat fills as the only on-chain signal.

### 2.13 LimitOrderBot (`DODOLimitOrderBot`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x272a16bd` | `fillDODOLimitOrder(bytes callExternalData, address takerToken, uint256 minTakerTokenAmount)` | Admin-only keeper entry. Calls `LimitOrder` then sweeps to `_TOKEN_RECEIVER_`. Emits `Fill`. |
| `0x89143c25` | `doLimitOrderSwap(uint256 curTakerFillAmount, uint256 curMakerFillAmount, address makerToken, address takerToken, address dodoRouteProxy, bytes dodoApiData)` | Callback invoked **by** `LimitOrder` during fill; routes the maker token through a route proxy. Caller must be `_DODO_LIMIT_ORDER_`. |
| `0xae52aae7` | `addAdminList(address)` | Owner-only. Emits `addAdmin`. |
| `0xfd8bd849` | `removeAdminList(address)` | Owner-only. Emits `removeAdmin`. |
| `0xbc2790c8` | `changeTokenReceiver(address)` | Owner-only. Emits `changeReceiver`. |

### 2.14 Shared ownership selectors

| Selector | Signature | Used by |
|----------|-----------|---------|
| `0x8da5cb5b` | `owner()` | OZ Ownable (`RouteProxy`, `DODOFeeRouteProxy`). |
| `0xf2fde38b` | `transferOwnership(address)` | OZ Ownable + InitializableOwnable (1st step). |
| `0x4e71e0c8` | `claimOwnership()` | InitializableOwnable (2nd step). |
| `0x715018a6` | `renounceOwnership()` | OZ Ownable. |
| `0x1626ba7e` | `isValidSignature(bytes32,bytes)` | ERC-1271 — checked by `LimitOrder` when `maker` is a contract wallet. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **DODOApprove** | `0xCB859eA579b28e02B87A1FDE08d087ab9dbE5149` | Allowance hub; users approve this. `_DODO_PROXY_` → DODOApproveProxy (verified). |
| **DODOApproveProxy** | `0x335aC99bb3E51BDbF22025f092Ebc1Cf2c5cC619` | Router allow-list registry. `_DODO_APPROVE_` → DODOApprove (verified). |
| **DODOV2Proxy** (`DODOV2Proxy02`) | `0xa356867fDCEa8e71AEaF87805808803806231FdC` | Gen-1 entry. `isAllowedProxy = true`. Emits `OrderHistory`. |
| **RouteProxy** (`DODORouteProxy`) | `0xa2398842F37465f89540430bDC00219fA9E4D28a` | Gen-2 aggregator (no fee). `isAllowedProxy = true`. Emits `OrderHistory`. |
| **DODOFeeRouteProxy** (older build) | `0x50f9bDe1c76bba997a5d6e7FEFff695ec8536194` | Gen-3 fee aggregator (≈10 945 B, no `PositiveSlippage`). `isAllowedProxy = true`. Emits `OrderHistory`. |
| **DODOFeeRouteProxy** (newer build) | `0xFe837A3530dD566401d35beFCd55582AF7c4dfFC` | **Ethereum-only newer fee proxy** (≈11 202 B, `expReturnAmount` swaps, emits `PositiveSlippage` + `OrderHistory`). Etherscan "DODO: Fee Route Proxy"; wired to the same `DODOApproveProxy`. Add to the router set. |
| **DODOFeeRouteProxy (widget)** | `0x21b9F852534Fb9DdC3A0A7B24f067B50d8AC9a99` | Byte-identical to the older fee proxy; different fee receiver. `isAllowedProxy = true`. |
| **DSPProxy** | `0x4599ed18F34cFE06820E3684bF0aACB8D75c644d` | Stable-pool create + LP. `isAllowedProxy = true`. |
| **CpProxy** | `0x048B8926bb0eE9c52e05D61fDffbCCffbeE06Fc2` | CrowdPooling create + bid. **`isAllowedProxy = false`** on Ethereum (not currently registered — see §9 gotcha 8). |
| **DPPProxy** | `0xfF7C8F518e6f1435957ed3d3E0692C94676dAE7a` | Private-pool create + reset. |
| **DODOV1Adapter** | `0x91E1c84BA8786B1FaE2570202F0126C0b88F6Ec7` | V1 hop adapter (uses DODOSellHelper). |
| **DODOV2Adapter** | `0xe6AafA1c45D9d0C64686c1f1D17B9fe9c7DAB05b` | V2 hop adapter (`sellBase`/`sellQuote` verified). |
| **UniAdapter** | `0x50D148D0908C602A56884B8628A36470a875EEb2` | Uniswap-V2-style hop adapter. |
| **CurveAdapter** | `0x12e599006a5F19819cde6FABceBbd8586688C8ac` | Curve hop adapter. |
| **DODOV2RouteHelper** | `0x6e90797C1caaa81bAEc1cF3351d989A78b2D4E99` | Pair enumerator; factory getters return ETH DVM/DPP/DSP factories (verified). |
| **DODOCalleeHelper** | `0x45a7E2E9D780613E047f7e78a9d3902ff854B522` | Pool redemption/cancel/claim callback helper. |
| **DODOSellHelper** | `0x533da777aedce766ceae696bf90f8541a4ba80eb` | V1 quote-side pricing. |
| **DODOV1PmmHelper** | `0x6373ceB657C83C91088d328622573FB766064Ac4` | V1 single-pool detail. |
| **CurveSample** (`CurveSampler`) | `0x5381382257C761DAc6F1509B1BA1B70dDaa6862a` | Curve sampler. |
| **LimitOrder** | `0x093b68BFe0859D3C857Fc3529952897C30dD17EB` | EIP-712 limit-order fills. `isAllowedProxy = true`. Emits `LimitOrderFilled`. |
| **LimitOrderBot** | `0xD9B825d16E09f28D0c715fe004364046E5524Dbb` | Keeper for limit-order fills. |

> Not deployed on Ethereum (returns `0x`): `DODOSwapCalcHelper`, `ERC20Helper`, `MultiCall` (these route-helper utilities are present only on Base/Avalanche/Arbitrum/Optimism). `DODO`/`vDODO`/factories/templates are out of scope.

---

## 4. Addresses — Base mainnet (chain ID 8453)

All verified via `eth_getCode` on `https://base-rpc.publicnode.com`. **Base is the most divergent chain** in this set.

| Role | Address | One-liner |
|------|---------|-----------|
| **DODOApprove** | `0x89872650fA1A391f58B4E144222bB02e44db7e3B` | Allowance hub. |
| **DODOApproveProxy** | `0x6de4d882a84A98f4CCD5D33ea6b3C99A07BAbeB1` | Router allow-list. |
| **DODOV2Proxy** | `0x4CAD0052524648A7Fa2cfE279997b00239295F33` | Gen-1 entry. Emits `OrderHistory`. |
| **DODOFeeRouteProxy** | `0x987bFBE33c9cF18cAA665B792Db66339a9c16D32` | Gen-3 fee aggregator. Emits `OrderHistory`. |
| **DODOFeeRouteProxy (widget)** | `0xA376762070F7fCE8f3646AAe90e6e375e6daF128` | Widget fee variant. |
| **DSPProxy** | `0x49186E32fEd50fd6B5604A2618c7B0b03Cd41414` | Stable-pool create + LP. |
| **CpProxy** | `0x6B9577b87666af89bd0e144b9b64e8Ed166E303d` | CrowdPooling create + bid. |
| **DPPProxy** | `0x0B1467f71c082D8d410aF4376C685D9A6893cF36` | Private-pool create + reset. |
| **DODOV2Adapter** | `0x66c45FF040e86DC613F239123A5E21FFdC3A3fEC` | **The only adapter on Base.** |
| **DODOV2RouteHelper** | `0xe42A29cB784cD4E1a2C9EE4B01CE70A6E720A160` | Pair enumerator. |
| **DODOCalleeHelper** | `0x44023441f2Bad375b6b5C6354B03c3E9AD01E269` | Callback helper. |
| **DODOSellHelper** | `0x8eA40e8Da3ae64Bad5E77a5f7DB346499F543baC` | V1 pricing. |
| **DODOV1PmmHelper** | `0x17644d3B366273faC75A07996E2F90A99A2946a7` | V1 detail. |
| **DODOSwapCalcHelper** | `0xbcd2FDC3B884Cf0dfD932f55Ec2Fe1fB7e8c62Da` | Multi-hop V1 calc (`calcReturnAmountV1` verified present). |
| **ERC20Helper** | `0xB5c7BA1EAde74800cD6cf5F56b1c4562De373780` | Token metadata probe. |
| **MultiCall** | `0xf5Ec1a19e1570bDf0A3AaA6585274f27027270b1` | Read-side aggregate. |

> **Base divergences (verified):** **no plain `RouteProxy`** (only `DODOV2Proxy` + `DODOFeeRouteProxy` + widget for swaps); **only `DODOV2Adapter`** — `DODOV1Adapter`, `UniAdapter`, `CurveAdapter`, `CurveSample` are **not** deployed; **no `LimitOrder`/`LimitOrderBot`**. All confirmed `0x` from `eth_getCode`.

---

## 5. Addresses — BNB Smart Chain (chain ID 56)

All verified via `eth_getCode` on `https://bsc-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **DODOApprove** | `0xa128Ba44B2738A558A1fdC06d6303d52D3Cef8c1` | Allowance hub. |
| **DODOApproveProxy** | `0xB76de21f04F677f07D9881174a1D8E624276314C` | Router allow-list. |
| **RouteProxy** | `0x6B3D817814eABc984d51896b1015C0b89E9737Ca` | Gen-2 aggregator. `isAllowedProxy = true`. |
| **DODOFeeRouteProxy** | `0x0656fD85364d03b103CEEda192FB2D3906A6ac15` | Gen-3 fee aggregator. `isAllowedProxy = true`. |
| **DODOFeeRouteProxy (widget)** | `0xa8b034301Bb5DD3610db585Def3e7C0d52f2319F` | Widget fee variant. |
| **DSPProxy** | `0x2442A8B5cdf1E659F3F949A7E454Caa554D4E65a` | Stable-pool create + LP. |
| **CpProxy** | `0xA867241cDC8d3b0C07C85cC06F25a0cD3b5474d8` | CrowdPooling create + bid. |
| **DPPProxy** | `0x624FC8368fE11BE00D8B2F3fE0B9D0053BEc21b9` | Private-pool create + reset. |
| **DODOV1Adapter** | `0x8E4842d0570c85Ba3805A9508Dce7C6A458359d0` | V1 hop adapter. |
| **DODOV2Adapter** | `0x165BA87e882208100672b6C56f477eE42502c820` | V2 hop adapter. |
| **UniAdapter** | `0xE223AcD7CBAFabCFfcAfeC5e69877424c4760aC2` | PancakeSwap-V2-style hop adapter. |
| **DODOV2RouteHelper** | `0xb48eE7B874Af8bC0e068036e55e33b5DC91C3a65` | Pair enumerator. |
| **DODOCalleeHelper** | `0x2673E5333620bb22BD1bFB3af9Fc7012008E3b4B` | Callback helper. |
| **DODOV1PmmHelper** | `0x2BBD66fC4898242BDBD2583BBe1d76E8b8f71445` | V1 detail. |
| **LimitOrder** | `0xdc5E86654e768d21f7D298690687eA02db7b2a04` | Limit-order fills. `isAllowedProxy = true`. |
| **LimitOrderBot** | `0x187da347dEbf4221B861EeAFC9808d8Cf89cF5fE` | Keeper. |

> **BSC divergences (verified):** **no `DODOV2Proxy`** (BSC swap entry is `RouteProxy` + `DODOFeeRouteProxy`); `isAllowedProxy(DODOV2Proxy-ETH-addr) = false`. No `CurveAdapter`/`CurveSample`. No `DODOSwapCalcHelper`/`ERC20Helper`/`MultiCall`. No `DODOSellHelper`.

---

## 6. Addresses — Avalanche C-Chain (chain ID 43114)

All verified via `eth_getCode` on `https://avalanche-c-chain-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **DODOApprove** | `0xCFea63e3DE31De53D68780Dd65675F169439e470` | Allowance hub. |
| **DODOApproveProxy** | `0x96a75d73b3de29c009863fA6329D96b2181D3Dc4` | Router allow-list. |
| **DODOV2Proxy** | `0x2cD18557E14aF72DAA8090BcAA95b231ffC9ea26` | Gen-1 entry. `isAllowedProxy = true`. |
| **RouteProxy** | `0x409E377A7AfFB1FD3369cfc24880aD58895D1dD9` | Gen-2 aggregator. `isAllowedProxy = true`. |
| **DODOFeeRouteProxy** | `0x1F076a800005c758a505E759720eb6737136e893` | Gen-3 fee aggregator. `isAllowedProxy = true`. |
| **DODOFeeRouteProxy (widget)** | `0xbce44767af0a53A108b3B7ba4F740E03D228Ec0A` | Widget fee variant. |
| **DSPProxy** | `0xeCEaDe494FD5F913Fd937C5CAc4577236395Dc32` | Stable-pool create + LP. |
| **CpProxy** | `0x9Aa4d70F941b1a72f1CD3852F8aa88Fba77A98fD` | CrowdPooling create + bid. |
| **DPPProxy** | `0xe44F14BFDe673B7339734a28152cCd6b821753C9` | Private-pool create + reset. |
| **DODOV1Adapter** | `0x62F67e305850a2597c46cD5957BdFbe9d04F10Bd` | V1 hop adapter. |
| **DODOV2Adapter** | `0xd72b354BD39f8F11D0cA07bD5724896Bb1a42707` | V2 hop adapter. |
| **UniAdapter** | `0x3a343F2e4e142412c5dD130359edb765a6054965` | Uni-V2-style hop adapter. |
| **DODOV2RouteHelper** | `0xB895FA93537D1C2C68DA39A73b404F02de246107` | Pair enumerator. |
| **DODOCalleeHelper** | `0x4EfF1D851366b8cc51d553a87e2d12dA8Da46F2a` | Callback helper. |
| **DODOV1PmmHelper** | `0x790B4A80Fb1094589A3c0eFC8740aA9b0C1733fB` | V1 detail. |
| **DODOSwapCalcHelper** | `0xAfe0A75DFFb395eaaBd0a7E1BBbd0b11f8609eeF` | Multi-hop V1 calc. |
| **ERC20Helper** | `0xC3528D128CC227fd60793007b5e3FdF7c2945282` | Token metadata probe. |
| **MultiCall** | `0x97f0153E7F5749640aDF3Ff9CFC518b79D6Fe53b` | Read-side aggregate. |

> **Avalanche divergences (verified):** **no `LimitOrder`/`LimitOrderBot`**; no `CurveAdapter`/`CurveSample`; no `DODOSellHelper`.

---

## 7. Addresses — Arbitrum One (chain ID 42161)

All verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com`. Arbitrum has the **fullest** coverage of all 7 chains.

| Role | Address | One-liner |
|------|---------|-----------|
| **DODOApprove** | `0xA867241cDC8d3b0C07C85cC06F25a0cD3b5474d8` | Allowance hub. |
| **DODOApproveProxy** | `0x311E670c3305a0BD55184c1C6580eBeA1FA611F0` | Router allow-list. |
| **DODOV2Proxy** | `0x88CBf433471A0CD8240D2a12354362988b4593E5` | Gen-1 entry. `isAllowedProxy = true`. |
| **RouteProxy** | `0x3B6067D4CAa8A14c63fdBE6318F27A0bBc9F9237` | Gen-2 aggregator. `isAllowedProxy = true`. |
| **DODOFeeRouteProxy** | `0xe05dd51e4eB5636f4f0E8e7Fbe82eA31a2ecef16` | Gen-3 fee aggregator. `isAllowedProxy = true`. |
| **DODOFeeRouteProxy (widget)** | `0xc4A1a152812dE96b2B1861E433f42290CDD7f113` | Widget fee variant. |
| **DSPProxy** | `0x36E5238B4479d1ba0bFE47550B0B8e4f4f500EAA` | Stable-pool create + LP. |
| **CpProxy** | `0x074890524059905096caA0D1A7B5715C6203c155` | CrowdPooling create + bid. |
| **DPPProxy** | `0xE8C9A78725D0451FA19878D5f8A3dC0D55FECF25` | Private-pool create + reset. |
| **DODOV1Adapter** | `0xd5a7E197bacE1F3B26E2760321d6ce06Ad07281a` | V1 hop adapter. |
| **DODOV2Adapter** | `0x8aB2D334cE64B50BE9Ab04184f7ccBa2A6bb6391` | V2 hop adapter. |
| **UniAdapter** | `0x17eBC315760Bb47384224A5f3BF829222fbD3Aa7` | Uni-V2-style hop adapter. |
| **CurveAdapter** | `0x57a046AC05185ba2AbdD3C480567A35bd1Ac9711` | Curve hop adapter (only ETH + Arbitrum). |
| **DODOV2RouteHelper** | `0x7737fd30535c69545deeEa54AB8Dd590ccaEBD3c` | Pair enumerator. |
| **DODOCalleeHelper** | `0xe3B40F8D8346d428EAB28d9Fd672b784d921cfBD` | Callback helper. |
| **DODOV1PmmHelper** | `0x4EE6398898F7FC3e648b3f6bA458310ac29cD352` | V1 detail. |
| **DODOSwapCalcHelper** | `0xd7863Aee0B7A312F2c055B441253d66AFac8d144` | Multi-hop V1 calc. |
| **ERC20Helper** | `0x7C062B9C584fA6eC2504270790D38240A2c5fE72` | Token metadata probe. |
| **MultiCall** | `0xF718F2bd590E5621e53f7b89398e52f7Acced8ca` | Read-side aggregate. |
| **CurveSample** (`CurveSampler`) | `0x17307DA6c27BeAaDCcC1C7Ca7456cA1fBa10b9CF` | Curve sampler (only ETH + Arbitrum). |
| **LimitOrder** | `0x91FbD0C9dbA8C42B7Fa636CC60344c72E7D065c9` | Limit-order fills. |
| **LimitOrderBot** | `0x0F278Ee5FDd139f9aE8c6498Cca0f2c2208684a2` | Keeper. |

> No `DODOSellHelper` standalone on Arbitrum (pricing folded into `DODOSwapCalcHelper` / `DODOV1Adapter`).

---

## 8. Addresses — Optimism (chain ID 10)

All verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`. Adapter group key is `Adpater` (sic) in the registry — same contracts.

| Role | Address | One-liner |
|------|---------|-----------|
| **DODOApprove** | `0xa492d6eABcdc3E204676f15B950bBdD448080364` | Allowance hub. |
| **DODOApproveProxy** | `0x8989A6909fe5af076AaA3D7b18BDe53153DbC348` | Router allow-list. |
| **DODOV2Proxy** | `0xfD9D2827AD469B72B69329dAA325ba7AfbDb3C98` | Gen-1 entry. `isAllowedProxy = true`. |
| **RouteProxy** | `0x7950dC01542eFE1c03aea610472e3b565B53f64a` | Gen-2 aggregator. `isAllowedProxy = true`. |
| **DODOFeeRouteProxy** | `0x716fcc67dcA500A91B4a28c9255262c398D8f971` | Gen-3 fee aggregator. `isAllowedProxy = true`. |
| **DODOFeeRouteProxy (widget)** | `0xc7d7CC1e9f5E823887980c9C51F9c418ee3A3e28` | Widget fee variant. |
| **DSPProxy** | `0x61721e89a498dADa7aD579482BDC2aE60a9C5D54` | Stable-pool create + LP. |
| **CpProxy** | `0x072b3e5391B8bc868934562E510e6B2454163093` | CrowdPooling create + bid. |
| **DODOV1Adapter** | `0xDd0951b69bc0CF9d39111E5037685FB573204c86` | V1 hop adapter. |
| **DODOV2Adapter** | `0x169ae3d5AcC90F0895790F6321eE81CB040E8A6B` | V2 hop adapter. |
| **UniAdapter** | `0x59Bef1EEdfCC26e7c9FD47c22625f81124228FaD` | Uni-V2-style hop adapter. |
| **DODOV2RouteHelper** | `0xC48A8e689a644de96F80786ACb69E6F76D057F25` | Pair enumerator. |
| **DODOCalleeHelper** | `0x0BD7426f008737FeeD575ED8e2aA1bd4Fc49112D` | Callback helper. |
| **DODOSellHelper** | `0x56f8E27B27BFF96B5203c95977e8982f62bE70C2` | V1 pricing. |
| **DODOV1PmmHelper** | `0x6281E0628eb2B37fE9943279EA39725D5f0E0dBe` | V1 detail. |
| **DODOSwapCalcHelper** | `0x2815b0aDdB0bECF86b10982a86A133Ae9d36AB0f` | Multi-hop V1 calc. |
| **ERC20Helper** | `0x42E456ea0dd7538ea103fBb1d0388D14C97bB5b2` | Token metadata probe. |
| **MultiCall** | `0xb98Ac2fEFc8b73aeAE33D02BB00c26E12afCa9Df` | Read-side aggregate. |

> **Optimism divergences (verified):** **no `DPPProxy`**; **no `LimitOrder`/`LimitOrderBot`**; no `CurveAdapter`/`CurveSample`.

---

## 9. Addresses — Polygon PoS (chain ID 137)

All verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **DODOApprove** | `0x6D310348d5c12009854DFCf72e0DF9027e8cb4f4` | Allowance hub. |
| **DODOApproveProxy** | `0x01FEEA29da5Ae41B0b5F6b10b93EE34752eF80d7` | Router allow-list. |
| **DODOV2Proxy** | `0x45894C062E6f4E58B257e0826675355305dfef0d` | Gen-1 entry. `isAllowedProxy = true`. |
| **RouteProxy** | `0x53eE28b9F0A6416857C1e7503032E27e80F52DA0` | Gen-2 aggregator. `isAllowedProxy = true`. |
| **DODOFeeRouteProxy** | `0x39E3e49C99834C9573c9FC7Ff5A4B226cD7B0E63` | Gen-3 fee aggregator. `isAllowedProxy = true`. |
| **DODOFeeRouteProxy (widget)** | `0xA103206E7f19d1C1c0e31eFC4DFc7b299630F100` | Widget fee variant. |
| **DSPProxy** | `0xfDDCA6ffCE24dF5bE3e8AaD32081822f86178048` | Stable-pool create + LP. |
| **CpProxy** | `0x5480B32c03647ff5E5A653F0465E798DBe558B57` | CrowdPooling create + bid. |
| **DPPProxy** | `0xF6f1A1Ef2f5b56bb289993F75C12Eb41e4abC2f7` | Private-pool create + reset. |
| **DODOV1Adapter** | `0xDBFaF391C37339c903503495395Ad7D6B096E192` | V1 hop adapter. |
| **DODOV2Adapter** | `0x6C30bE15d88462B788DEa7c6A860a2CCAF7B2670` | V2 hop adapter. |
| **UniAdapter** | `0xe373DF144a70BCCc10190f97bEDE647D1eD6cfc8` | Uni-V2-style hop adapter. |
| **DODOV2RouteHelper** | `0x6b0C1Ec661b776A819F5d5b2D0B622dE3419fDB0` | Pair enumerator. |
| **DODOCalleeHelper** | `0x261F6cF4dF0e5c1432739cDAFD9299150FEd3dFc` | Callback helper. |
| **DODOV1PmmHelper** | `0x18DFdE99F578A0735410797e949E8D3e2AFCB9D2` | V1 detail. |
| **LimitOrder** | `0x5F43046eAD98012044CfC1C3427A1bcEf921d3f3` | Limit-order fills. |
| **LimitOrderBot** | `0xA7263eb38b9A61B72397c884b5f9bFb5C34A7840` | Keeper. |

> **Polygon divergences (verified):** no `CurveAdapter`/`CurveSample`; no `DODOSwapCalcHelper`/`ERC20Helper`/`MultiCall`; no `DODOSellHelper` standalone.

---

## 10. Cross-chain summary (presence matrix)

`Y` = `eth_getCode` returned non-empty bytecode (verified 2026-06-02); `—` = not deployed (`0x`).

| Contract | ETH (1) | Base (8453) | BNB (56) | AVAX (43114) | ARB (42161) | OP (10) | POL (137) |
|----------|:------:|:-----------:|:--------:|:------------:|:-----------:|:-------:|:---------:|
| DODOApprove | Y | Y | Y | Y | Y | Y | Y |
| DODOApproveProxy | Y | Y | Y | Y | Y | Y | Y |
| DODOV2Proxy | Y | Y | **—** | Y | Y | Y | Y |
| RouteProxy | Y | **—** | Y | Y | Y | Y | Y |
| DODOFeeRouteProxy | Y | Y | Y | Y | Y | Y | Y |
| DODOFeeRouteProxy (widget) | Y | Y | Y | Y | Y | Y | Y |
| DSPProxy | Y | Y | Y | Y | Y | Y | Y |
| CpProxy | Y | Y | Y | Y | Y | Y | Y |
| DPPProxy | Y | Y | Y | Y | Y | **—** | Y |
| DODOV1Adapter | Y | **—** | Y | Y | Y | Y | Y |
| DODOV2Adapter | Y | Y | Y | Y | Y | Y | Y |
| UniAdapter | Y | **—** | Y | Y | Y | Y | Y |
| CurveAdapter | Y | — | — | — | Y | — | — |
| DODOV2RouteHelper | Y | Y | Y | Y | Y | Y | Y |
| DODOCalleeHelper | Y | Y | Y | Y | Y | Y | Y |
| DODOSellHelper | Y | Y | — | — | — | Y | — |
| DODOV1PmmHelper | Y | Y | Y | Y | Y | Y | Y |
| DODOSwapCalcHelper | — | Y | — | Y | Y | Y | — |
| ERC20Helper | — | Y | — | Y | Y | Y | — |
| MultiCall | — | Y | — | Y | Y | Y | — |
| CurveSample | Y | — | — | — | Y | — | — |
| LimitOrder | Y | **—** | Y | **—** | Y | **—** | Y |
| LimitOrderBot | Y | **—** | Y | **—** | Y | **—** | Y |

Key absences to encode in alert config: **DODOV2Proxy ∉ BNB**, **RouteProxy ∉ Base**, **DPPProxy ∉ Optimism**, **LimitOrder/Bot present only on {ETH, BNB, ARB, POL}**, **Base adapter set = {DODOV2Adapter}** only, **CurveAdapter/CurveSample ∈ {ETH, ARB}** only.

`OrderHistory`-emitting router set per chain (the swap detector allow-list):

- **Ethereum / Avalanche / Arbitrum / Optimism / Polygon:** `{DODOV2Proxy, RouteProxy, DODOFeeRouteProxy, DODOFeeRouteProxy(widget)}`
- **Base:** `{DODOV2Proxy, DODOFeeRouteProxy, DODOFeeRouteProxy(widget)}` (no RouteProxy)
- **BNB:** `{RouteProxy, DODOFeeRouteProxy, DODOFeeRouteProxy(widget)}` (no DODOV2Proxy)

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| DODOApprove | **Immutable** entry; `InitializableOwnable`. EIP-1967 impl slot = `0x0` (verified). | `getDODOProxy()` / `SetDODOProxy` event. | `owner` rotates `_DODO_PROXY_` after a 3-day (24-h if first) timelock. |
| DODOApproveProxy | **Immutable**; `InitializableOwnable`; `_DODO_APPROVE_` immutable. Impl slot = `0x0` (verified). | `isAllowedProxy(addr)`. | `owner` adds proxies (3-day timelock) / removes immediately. |
| DODOV2Proxy / RouteProxy / DODOFeeRouteProxy (+widget) / DSPProxy / CpProxy / DPPProxy | **Immutable router/entry contracts — NOT EIP-1967.** Impl slot = `0x0` on every one (verified on ETH; spot-checked across chains). | Track the fixed address-set; emits `OrderHistory` (the three swap proxies). | None. A new router = new address + `DODOApproveProxy.addDODOProxy()`. |
| Adapters (V1/V2/Uni/Curve) | **Immutable, stateless.** No proxy slot, no owner, no events. | Fixed address; referenced as `mixAdapters[]`/`sequence` args to the route proxies. | None — a new adapter is just a new address passed in calldata. |
| Helpers (RouteHelper/Callee/Sell/PmmHelper/SwapCalc/ERC20/MultiCall/CurveSample) | **Immutable, view-only.** No events. | Fixed address. | None. |
| LimitOrder | **Immutable logic, clone-initialized** (`init(owner, approveProxy, feeReceiver)`, `InitializableOwnable`). Impl slot = `0x0` (verified). | `LimitOrderFilled` + `_FILLED_TAKER_AMOUNT_(orderHash)`. | `owner` manages the `takerInteraction` whitelist + fee receiver. **No upgrade, no cancel.** |
| LimitOrderBot | **Immutable, clone-initialized**; `InitializableOwnable`. | `Fill` / admin events. | `owner` manages admin keepers + token receiver. |

**EIP-1967 storage slots** (read these to *confirm* immutability — all of the above return `0x0` for the impl slot):

| Slot | Purpose |
|------|---------|
| `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` | Implementation. `= bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1)`. **`0x0` on every contract in this file.** |
| `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` | Admin. `= bytes32(uint256(keccak256("eip1967.proxy.admin")) - 1)`. |

---

## 12. Detection invariants & gotchas

1. **`OrderHistory` is the swap signal, not a pool event.** It is emitted by the *entry router* (`DODOV2Proxy` / `RouteProxy` / `DODOFeeRouteProxy`), once per top-level swap, after fees. Filter `topic0 = 0x92ceb067…` **+ contract ∈ the chain's router set** (§10). The underlying pool's own swap (`DODOSwap`, AMM layer) fires too but at the pool address — don't double-count. `returnAmount` is the **net** amount delivered to `sender`; on `DODOFeeRouteProxy` it is already net of `routeFeeRate` (0.15% default) and the broker fee.

2. **All five `OrderHistory` fields are non-indexed.** The log has exactly 1 topic; decode the 160-byte data as `(address, address, address, uint256, uint256)`. Do **not** look for indexed `fromToken`/`toToken` — you will match nothing.

3. **Native gas-token legs use the sentinel `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`.** When `fromToken`/`toToken` equals this sentinel, the leg is native ETH/BNB/AVAX/MATIC (wrapped internally to WETH/WBNB/…). Normalise the sentinel to the chain's wrapped-native address when joining to `Transfer` logs.

4. **Token custody is one hop removed from the router.** Users approve `DODOApprove` (per chain). The router calls `DODOApproveProxy.claimTokens` → `DODOApprove.claimTokens` → `token.transferFrom(user → dest)`. So the ERC-20 `Transfer.from` of the *input* leg is the user, but the `approve` spender on file is **`DODOApprove`**, never the router. To audit "who can move a user's funds", read `DODOApproveProxy.isAllowedProxy(x)`, not the router address directly.

5. **`SetDODOProxy` on `DODOApprove` is critical-severity.** It rotates the single contract (`_DODO_PROXY_`) allowed to pull from the entire allowance hub. In normal operation `_DODO_PROXY_` is the per-chain `DODOApproveProxy` (verified: ETH `_DODO_PROXY_` = `0x335aC99…`, and the reverse `DODOApproveProxy._DODO_APPROVE_` = `0xCB859e…`). Any `SetDODOProxy` to an unexpected address = compromise. There is a 3-day (24-h first-time) timelock — watch `unlockSetProxy`/`_PENDING_DODO_PROXY_` to get advance warning.

6. **New routers are added via `DODOApproveProxy`, behind a 3-day timelock.** `unlockAddProxy(x)` starts the clock (read `_PENDING_ADD_DODO_PROXY_` + `_TIMELOCK_`), `addDODOProxy()` finalises (sets `isAllowedProxy(x)=true`). `removeDODOProxy(x)` is **immediate, no timelock**. To enumerate every contract that can currently pull user funds, query `isAllowedProxy` for each known router/settlement address — confirmed `true` for `DODOV2Proxy`, `RouteProxy`, both `DODOFeeRouteProxy` variants, `DSPProxy`, `DPPProxy`, and `LimitOrder`.

7. **DODO limit orders have NO on-chain cancel.** The deployed `LimitOrder` exposes only `fillLimitOrder`; there is **no `cancelLimitOrder` function and no `LimitOrderCancelled` event** (verified: cancel selector `0xf0dbead1` absent from bytecode). Orders are off-chain EIP-712 signatures; a maker "cancels" by letting the order expire (`expiration`), by spending/removing the maker-token balance, or by revoking the `DODOApprove` allowance. The only on-chain order signal is `LimitOrderFilled` (incremental fills) and the cumulative `_FILLED_TAKER_AMOUNT_[orderHash]`. Do not build alerting that waits for a cancel event.

8. **`CpProxy` is NOT in the `isAllowedProxy` set on Ethereum.** Despite calling `claimTokens` in source, the Ethereum `CpProxy` (`0x048B…6Fc2`) returns `isAllowedProxy = false` — so its `createCrowdPooling`/`bid` base-token pulls would revert at the allowance hub (CrowdPooling base deposits are routed/seeded differently, or this proxy is deprecated on ETH). Treat `CpProxy` as a create-helper, not an active user fund-pull path, unless `isAllowedProxy` says otherwise on a given chain. (The other create proxies, `DSPProxy`/`DPPProxy`, **are** allowed.)

9. **Three router generations coexist and all emit the same `OrderHistory` topic0.** `DODOV2Proxy` (hard-coded V1/V2 hops, has `externalSwap` with a trailing `bool`), `RouteProxy` (adapter aggregator, **no fee, no `externalSwap`**), and `DODOFeeRouteProxy` (adapter aggregator **with fee + `externalSwap`**). To tell which router handled a swap, look at `tx.to` / the emitting contract address, not the event (identical). Selectors disambiguate the call: e.g. `externalSwap` is `0x54bacd13` on `DODOV2Proxy` vs `0xa8676443` on `DODOFeeRouteProxy` (gen-1) — different arity.

10. **The `DODOFeeRouteProxy` "widget" is a clone of the main fee proxy with a different fee receiver.** Byte-identical runtime (verified same code hash), so it has the identical selectors and `OrderHistory` topic0. The only on-chain difference is `routeFeeReceiver()`. Include both addresses in the router set; treat them as one logical contract for swap detection.

11. **`dodoMutliSwap` (sic) is the canonical spelling.** The split-route function is misspelled in the ABI (`Mutli`, not `Multi`); its selector (`0x81791788` on `RouteProxy`, `0x94cfab17` on `DODOFeeRouteProxy` gen-1) reflects the typo. Do not "correct" it when computing selectors.

12. **`RouteProxy.dodoMutliSwap` carries an extra `uint256[] totalWeight` argument** that the fee variants drop (the fee proxy moves `totalWeight` into contract storage). This is why the two `dodoMutliSwap` selectors differ. Same idea distinguishes `mixSwap` across generations.

13. **Adapters are passed in calldata, not pinned.** A swap via `RouteProxy`/`DODOFeeRouteProxy` names its adapters in the `mixAdapters[]` / `sequence` arguments. New venues are integrated by deploying a new stateless adapter and passing its address — no on-chain registration, no event. To enumerate adapters in use, decode route-proxy calldata or watch the adapter addresses listed in §3–§9.

14. **`PositiveSlippage` IS emitted — but only by the newer Ethereum fee proxy `0xFe837A35…`.** The registry `DODOFeeRouteProxy` on all 7 chains (the older `dodo-route-contract` build, ETH `0x50f9bDe1…`) does **not** emit it. Ethereum *additionally* runs the newer `contractV2` build at `0xFe837A3530dD566401d35beFCd55582AF7c4dfFC` (≈11 202 B) which emits `PositiveSlippage(address,uint256)` (topic0 `0xd820290d…`) and uses `expReturnAmount` swap selectors — **verified live in its runtime**. Include `0xFe837A35…` in the Ethereum router set. On the other 6 chains, if `0xd820290d…` appears at a fee-route address the newer build has been deployed there too (re-probe).

15. **`MultiCall` here is the MakerDAO-style `aggregate`, not Multicall3.** Selector `0x252dba42` (`aggregate((address,bytes)[])`), distinct from the canonical Multicall3 `aggregate3`. It is a state-changing call (it does generic `.call`s), so it is **not** safe to assume read-only. There is also a `MultiCallWithValid` variant in the registry on some chains.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- Topics (chain-agnostic)
TOPIC_ORDER_HISTORY                   = '\x92ceb067a9883c85aba061e46b9edf505a0d6e81927c4b966ebed543a5221787'
TOPIC_APPROVE_SET_DODO_PROXY          = '\xd356351ffbb32d7a93878d5fbbd5c39435bbae136f428b0d574242f63bb803cb'
TOPIC_LIMITORDER_FILLED               = '\x30a60b21c24c8f631a1e032527b3ee9a12b7e1fce164b4273c40f5db96415245'
TOPIC_LIMITORDER_ADD_WHITELIST        = '\xf8d5f40934646cedded2cab1b5960f020db583f154fabcf831277b87d1803d13'
TOPIC_LIMITORDER_REMOVE_WHITELIST     = '\x1e17ee0599b7c09bb1d0ff1e8086007909da8bfba5c7d18319cb558e66db37ee'
TOPIC_LIMITORDER_CHANGE_FEE_RECEIVER  = '\xfb29108df6ec24f97dfbe39fff6bb9357a54e758efed2c6e7b5fb76b26b30f81'
TOPIC_BOT_FILL                        = '\xcb78302ec72136bfa852ed66b453ff3802e5959bb4df8386cd9695cae88de2e9'
TOPIC_BOT_ADD_ADMIN                   = '\x7048027520ecbaa8947764cd502c5c78c2c53bbd902e06b108da1cbdf98c6fc4'
TOPIC_BOT_REMOVE_ADMIN                = '\x1785f53c768259a7ab38ed67e958aab075b56ff206e3d7f29ea4ca203d1a9774'
TOPIC_BOT_CHANGE_RECEIVER             = '\x547e3f060aba0f7eec865fc52a952a5148e4903d709e38cde9c93b655ce0b057'
TOPIC_OWNERSHIP_PREPARED              = '\xdcf55418cee3220104fef63f979ff3c4097ad240c0c43dcb33ce837748983e62'
TOPIC_OWNERSHIP_TRANSFERRED           = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- newer fee-proxy variant (NOT deployed on these 7 chains; upgrade canary)
TOPIC_POSITIVE_SLIPPAGE               = '\xd820290de56f193465e6c0b6140e6bedce58ba0d54229b2a57fd4b60d285297c'

-- Selectors — DODOApprove
SEL_APPROVE_CLAIM_TOKENS              = '\x0a5ea466'
SEL_APPROVE_GET_DODO_PROXY            = '\x31fa1319'
SEL_APPROVE_DODO_PROXY                = '\xe54c8033'
SEL_APPROVE_SET_DODO_PROXY            = '\x8cdb6574'
SEL_APPROVE_UNLOCK_SET_PROXY          = '\x41c256c1'

-- Selectors — DODOApproveProxy
SEL_APX_IS_ALLOWED_PROXY              = '\x48a4f993'
SEL_APX_CLAIM_TOKENS                  = '\x0a5ea466'
SEL_APX_DODO_APPROVE                  = '\x46e74298'
SEL_APX_ADD_DODO_PROXY                = '\x3e688589'
SEL_APX_UNLOCK_ADD_PROXY              = '\x374445b2'
SEL_APX_REMOVE_DODO_PROXY             = '\x2c419f2f'

-- Selectors — DODOV2Proxy (gen-1 entry)
SEL_V2P_DODO_SWAP_V1                  = '\x0dd4ebd9'
SEL_V2P_SWAP_V2_ETH_TO_TOKEN          = '\x5028bb95'
SEL_V2P_SWAP_V2_TOKEN_TO_ETH          = '\x1e6d24c2'
SEL_V2P_SWAP_V2_TOKEN_TO_TOKEN        = '\xf87dc1b7'
SEL_V2P_EXTERNAL_SWAP                 = '\x54bacd13'
SEL_V2P_CREATE_DVM                    = '\x8b3bb089'
SEL_V2P_ADD_DVM_LIQUIDITY             = '\x674d9422'
SEL_V2P_ADD_LIQUIDITY_TO_V1           = '\x99882c8f'

-- Selectors — RouteProxy (gen-2, no fee)
SEL_RP_MIX_SWAP                       = '\x7617b389'
SEL_RP_DODO_MUTLI_SWAP                = '\x81791788'

-- Selectors — DODOFeeRouteProxy (gen-3, DEPLOYED)
SEL_FRP_EXTERNAL_SWAP                 = '\xa8676443'
SEL_FRP_MIX_SWAP                      = '\x301a3720'
SEL_FRP_DODO_MUTLI_SWAP               = '\x94cfab17'
SEL_FRP_CHANGE_ROUTE_FEE_RATE         = '\x0c831085'
SEL_FRP_CHANGE_ROUTE_FEE_RECEIVER     = '\x5af35118'
SEL_FRP_ROUTE_FEE_RATE                = '\xb887bdac'
SEL_FRP_ROUTE_FEE_RECEIVER            = '\x4f3d2fd7'
-- DODOFeeRouteProxy newer variant (NOT deployed; upgrade canary)
SEL_FRP2_EXTERNAL_SWAP                = '\x2fa11647'
SEL_FRP2_MIX_SWAP                     = '\xff84aafa'
SEL_FRP2_DODO_MUTLI_SWAP              = '\x79b6f086'

-- Selectors — Adapters (IDODOAdapter, all four)
SEL_ADAPTER_SELL_BASE                 = '\x30e6ae31'
SEL_ADAPTER_SELL_QUOTE                = '\x6f7929f2'

-- Selectors — create+LP proxies
SEL_DSP_CREATE_STABLE_PAIR            = '\x3d59492a'
SEL_DSP_ADD_LIQUIDITY                 = '\xe24db1ac'
SEL_CP_CREATE_CROWDPOOLING            = '\x964e4c26'
SEL_CP_BID                            = '\xdb70b5c7'
SEL_DPP_CREATE_PRIVATE_POOL           = '\x0d9be500'
SEL_DPP_RESET_PRIVATE_POOL            = '\x12ff148d'

-- Selectors — helpers (read-only)
SEL_ROUTEHELPER_GET_PAIR_DETAIL       = '\x9d15e3ae'
SEL_SELLHELPER_QUERY_SELL_BASE        = '\xef4a83f8'
SEL_SELLHELPER_QUERY_SELL_QUOTE       = '\xca19ebd9'
SEL_PMMHELPER_GET_PAIR_DETAIL         = '\x2bd8c5ac'
SEL_SWAPCALC_CALC_RETURN_V1           = '\x0683ecd9'
SEL_ERC20HELPER_IS_ERC20              = '\xf1a16c31'
SEL_CURVESAMPLE_SAMPLE_FROM_CURVE     = '\xd84fc88a'
SEL_MULTICALL_AGGREGATE               = '\x252dba42'

-- Selectors — LimitOrder / LimitOrderBot
SEL_LO_FILL_LIMIT_ORDER               = '\xd9df05cf'
SEL_LO_ORDER_TYPEHASH                 = '\xf973a209'
SEL_LO_FILLED_TAKER_AMOUNT            = '\x1068705b'
SEL_LO_ADD_WHITELIST                  = '\xe7cd4a04'
SEL_LO_REMOVE_WHITELIST               = '\x2042e5c2'
SEL_LO_CHANGE_FEE_RECEIVER            = '\x7c08b964'
SEL_BOT_FILL_DODO_LIMIT_ORDER         = '\x272a16bd'
SEL_BOT_DO_LIMIT_ORDER_SWAP           = '\x89143c25'

-- Selectors — shared ownership / ERC-1271
SEL_OWNER                             = '\x8da5cb5b'
SEL_TRANSFER_OWNERSHIP                = '\xf2fde38b'
SEL_CLAIM_OWNERSHIP                   = '\x4e71e0c8'
SEL_IS_VALID_SIGNATURE_1271           = '\x1626ba7e'

-- ===== Ethereum (chain ID 1) =====
ETH_DODO_APPROVE                      = '\xcb859ea579b28e02b87a1fde08d087ab9dbe5149'
ETH_DODO_APPROVE_PROXY                = '\x335ac99bb3e51bdbf22025f092ebc1cf2c5cc619'
ETH_DODO_V2_PROXY                     = '\xa356867fdcea8e71aeaf87805808803806231fdc'
ETH_ROUTE_PROXY                       = '\xa2398842f37465f89540430bdc00219fa9e4d28a'
ETH_FEE_ROUTE_PROXY                   = '\x50f9bde1c76bba997a5d6e7fefff695ec8536194'   -- older build (no PositiveSlippage)
ETH_FEE_ROUTE_PROXY_NEWER             = '\xfe837a3530dd566401d35befcd55582af7c4dffc'   -- ETH-only newer build (emits PositiveSlippage)
ETH_FEE_ROUTE_PROXY_WIDGET            = '\x21b9f852534fb9ddc3a0a7b24f067b50d8ac9a99'
ETH_DSP_PROXY                         = '\x4599ed18f34cfe06820e3684bf0aacb8d75c644d'
ETH_CP_PROXY                          = '\x048b8926bb0ee9c52e05d61fdffbccffbee06fc2'
ETH_DPP_PROXY                         = '\xff7c8f518e6f1435957ed3d3e0692c94676dae7a'
ETH_DODO_V1_ADAPTER                   = '\x91e1c84ba8786b1fae2570202f0126c0b88f6ec7'
ETH_DODO_V2_ADAPTER                   = '\xe6aafa1c45d9d0c64686c1f1d17b9fe9c7dab05b'
ETH_UNI_ADAPTER                       = '\x50d148d0908c602a56884b8628a36470a875eeb2'
ETH_CURVE_ADAPTER                     = '\x12e599006a5f19819cde6fabcebbd8586688c8ac'
ETH_DODO_V2_ROUTE_HELPER              = '\x6e90797c1caaa81baec1cf3351d989a78b2d4e99'
ETH_DODO_CALLEE_HELPER                = '\x45a7e2e9d780613e047f7e78a9d3902ff854b522'
ETH_DODO_SELL_HELPER                  = '\x533da777aedce766ceae696bf90f8541a4ba80eb'
ETH_DODO_V1_PMM_HELPER                = '\x6373ceb657c83c91088d328622573fb766064ac4'
ETH_CURVE_SAMPLE                      = '\x5381382257c761dac6f1509b1ba1b70ddaa6862a'
ETH_LIMIT_ORDER                       = '\x093b68bfe0859d3c857fc3529952897c30dd17eb'
ETH_LIMIT_ORDER_BOT                   = '\xd9b825d16e09f28d0c715fe004364046e5524dbb'

-- ===== Base (chain ID 8453) — NO RouteProxy / only DODOV2Adapter / NO LimitOrder =====
BASE_DODO_APPROVE                     = '\x89872650fa1a391f58b4e144222bb02e44db7e3b'
BASE_DODO_APPROVE_PROXY               = '\x6de4d882a84a98f4ccd5d33ea6b3c99a07babeb1'
BASE_DODO_V2_PROXY                    = '\x4cad0052524648a7fa2cfe279997b00239295f33'
BASE_FEE_ROUTE_PROXY                  = '\x987bfbe33c9cf18caa665b792db66339a9c16d32'
BASE_FEE_ROUTE_PROXY_WIDGET           = '\xa376762070f7fce8f3646aae90e6e375e6daf128'
BASE_DSP_PROXY                        = '\x49186e32fed50fd6b5604a2618c7b0b03cd41414'
BASE_CP_PROXY                         = '\x6b9577b87666af89bd0e144b9b64e8ed166e303d'
BASE_DPP_PROXY                        = '\x0b1467f71c082d8d410af4376c685d9a6893cf36'
BASE_DODO_V2_ADAPTER                  = '\x66c45ff040e86dc613f239123a5e21ffdc3a3fec'
BASE_DODO_V2_ROUTE_HELPER             = '\xe42a29cb784cd4e1a2c9ee4b01ce70a6e720a160'
BASE_DODO_CALLEE_HELPER               = '\x44023441f2bad375b6b5c6354b03c3e9ad01e269'
BASE_DODO_SELL_HELPER                 = '\x8ea40e8da3ae64bad5e77a5f7db346499f543bac'
BASE_DODO_V1_PMM_HELPER               = '\x17644d3b366273fac75a07996e2f90a99a2946a7'
BASE_DODO_SWAP_CALC_HELPER            = '\xbcd2fdc3b884cf0dfd932f55ec2fe1fb7e8c62da'
BASE_ERC20_HELPER                     = '\xb5c7ba1eade74800cd6cf5f56b1c4562de373780'
BASE_MULTICALL                        = '\xf5ec1a19e1570bdf0a3aaa6585274f27027270b1'

-- ===== BNB Smart Chain (chain ID 56) — NO DODOV2Proxy =====
BSC_DODO_APPROVE                      = '\xa128ba44b2738a558a1fdc06d6303d52d3cef8c1'
BSC_DODO_APPROVE_PROXY                = '\xb76de21f04f677f07d9881174a1d8e624276314c'
BSC_ROUTE_PROXY                       = '\x6b3d817814eabc984d51896b1015c0b89e9737ca'
BSC_FEE_ROUTE_PROXY                   = '\x0656fd85364d03b103ceeda192fb2d3906a6ac15'
BSC_FEE_ROUTE_PROXY_WIDGET            = '\xa8b034301bb5dd3610db585def3e7c0d52f2319f'
BSC_DSP_PROXY                         = '\x2442a8b5cdf1e659f3f949a7e454caa554d4e65a'
BSC_CP_PROXY                          = '\xa867241cdc8d3b0c07c85cc06f25a0cd3b5474d8'
BSC_DPP_PROXY                         = '\x624fc8368fe11be00d8b2f3fe0b9d0053bec21b9'
BSC_DODO_V1_ADAPTER                   = '\x8e4842d0570c85ba3805a9508dce7c6a458359d0'
BSC_DODO_V2_ADAPTER                   = '\x165ba87e882208100672b6c56f477ee42502c820'
BSC_UNI_ADAPTER                       = '\xe223acd7cbafabcffcafec5e69877424c4760ac2'
BSC_DODO_V2_ROUTE_HELPER              = '\xb48ee7b874af8bc0e068036e55e33b5dc91c3a65'
BSC_DODO_CALLEE_HELPER                = '\x2673e5333620bb22bd1bfb3af9fc7012008e3b4b'
BSC_DODO_V1_PMM_HELPER                = '\x2bbd66fc4898242bdbd2583bbe1d76e8b8f71445'
BSC_LIMIT_ORDER                       = '\xdc5e86654e768d21f7d298690687ea02db7b2a04'
BSC_LIMIT_ORDER_BOT                   = '\x187da347debf4221b861eeafc9808d8cf89cf5fe'

-- ===== Avalanche C-Chain (chain ID 43114) — NO LimitOrder =====
AVAX_DODO_APPROVE                     = '\xcfea63e3de31de53d68780dd65675f169439e470'
AVAX_DODO_APPROVE_PROXY               = '\x96a75d73b3de29c009863fa6329d96b2181d3dc4'
AVAX_DODO_V2_PROXY                    = '\x2cd18557e14af72daa8090bcaa95b231ffc9ea26'
AVAX_ROUTE_PROXY                      = '\x409e377a7affb1fd3369cfc24880ad58895d1dd9'
AVAX_FEE_ROUTE_PROXY                  = '\x1f076a800005c758a505e759720eb6737136e893'
AVAX_FEE_ROUTE_PROXY_WIDGET           = '\xbce44767af0a53a108b3b7ba4f740e03d228ec0a'
AVAX_DSP_PROXY                        = '\xeceade494fd5f913fd937c5cac4577236395dc32'
AVAX_CP_PROXY                         = '\x9aa4d70f941b1a72f1cd3852f8aa88fba77a98fd'
AVAX_DPP_PROXY                        = '\xe44f14bfde673b7339734a28152ccd6b821753c9'
AVAX_DODO_V1_ADAPTER                  = '\x62f67e305850a2597c46cd5957bdfbe9d04f10bd'
AVAX_DODO_V2_ADAPTER                  = '\xd72b354bd39f8f11d0ca07bd5724896bb1a42707'
AVAX_UNI_ADAPTER                      = '\x3a343f2e4e142412c5dd130359edb765a6054965'
AVAX_DODO_V2_ROUTE_HELPER             = '\xb895fa93537d1c2c68da39a73b404f02de246107'
AVAX_DODO_CALLEE_HELPER               = '\x4eff1d851366b8cc51d553a87e2d12da8da46f2a'
AVAX_DODO_V1_PMM_HELPER               = '\x790b4a80fb1094589a3c0efc8740aa9b0c1733fb'
AVAX_DODO_SWAP_CALC_HELPER            = '\xafe0a75dffb395eaabd0a7e1bbbd0b11f8609eef'
AVAX_ERC20_HELPER                     = '\xc3528d128cc227fd60793007b5e3fdf7c2945282'
AVAX_MULTICALL                        = '\x97f0153e7f5749640adf3ff9cfc518b79d6fe53b'

-- ===== Arbitrum One (chain ID 42161) — fullest coverage; has CurveAdapter+CurveSample =====
ARB_DODO_APPROVE                      = '\xa867241cdc8d3b0c07c85cc06f25a0cd3b5474d8'
ARB_DODO_APPROVE_PROXY                = '\x311e670c3305a0bd55184c1c6580ebea1fa611f0'
ARB_DODO_V2_PROXY                     = '\x88cbf433471a0cd8240d2a12354362988b4593e5'
ARB_ROUTE_PROXY                       = '\x3b6067d4caa8a14c63fdbe6318f27a0bbc9f9237'
ARB_FEE_ROUTE_PROXY                   = '\xe05dd51e4eb5636f4f0e8e7fbe82ea31a2ecef16'
ARB_FEE_ROUTE_PROXY_WIDGET            = '\xc4a1a152812de96b2b1861e433f42290cdd7f113'
ARB_DSP_PROXY                         = '\x36e5238b4479d1ba0bfe47550b0b8e4f4f500eaa'
ARB_CP_PROXY                          = '\x074890524059905096caa0d1a7b5715c6203c155'
ARB_DPP_PROXY                         = '\xe8c9a78725d0451fa19878d5f8a3dc0d55fecf25'
ARB_DODO_V1_ADAPTER                   = '\xd5a7e197bace1f3b26e2760321d6ce06ad07281a'
ARB_DODO_V2_ADAPTER                   = '\x8ab2d334ce64b50be9ab04184f7ccba2a6bb6391'
ARB_UNI_ADAPTER                       = '\x17ebc315760bb47384224a5f3bf829222fbd3aa7'
ARB_CURVE_ADAPTER                     = '\x57a046ac05185ba2abdd3c480567a35bd1ac9711'
ARB_DODO_V2_ROUTE_HELPER              = '\x7737fd30535c69545deeea54ab8dd590ccaebd3c'
ARB_DODO_CALLEE_HELPER                = '\xe3b40f8d8346d428eab28d9fd672b784d921cfbd'
ARB_DODO_V1_PMM_HELPER                = '\x4ee6398898f7fc3e648b3f6ba458310ac29cd352'
ARB_DODO_SWAP_CALC_HELPER             = '\xd7863aee0b7a312f2c055b441253d66afac8d144'
ARB_ERC20_HELPER                      = '\x7c062b9c584fa6ec2504270790d38240a2c5fe72'
ARB_MULTICALL                         = '\xf718f2bd590e5621e53f7b89398e52f7acced8ca'
ARB_CURVE_SAMPLE                      = '\x17307da6c27beaadccc1c7ca7456ca1fba10b9cf'
ARB_LIMIT_ORDER                       = '\x91fbd0c9dba8c42b7fa636cc60344c72e7d065c9'
ARB_LIMIT_ORDER_BOT                   = '\x0f278ee5fdd139f9ae8c6498cca0f2c2208684a2'

-- ===== Optimism (chain ID 10) — NO DPPProxy / NO LimitOrder =====
OP_DODO_APPROVE                       = '\xa492d6eabcdc3e204676f15b950bbdd448080364'
OP_DODO_APPROVE_PROXY                 = '\x8989a6909fe5af076aaa3d7b18bde53153dbc348'
OP_DODO_V2_PROXY                      = '\xfd9d2827ad469b72b69329daa325ba7afbdb3c98'
OP_ROUTE_PROXY                        = '\x7950dc01542efe1c03aea610472e3b565b53f64a'
OP_FEE_ROUTE_PROXY                    = '\x716fcc67dca500a91b4a28c9255262c398d8f971'
OP_FEE_ROUTE_PROXY_WIDGET             = '\xc7d7cc1e9f5e823887980c9c51f9c418ee3a3e28'
OP_DSP_PROXY                          = '\x61721e89a498dada7ad579482bdc2ae60a9c5d54'
OP_CP_PROXY                           = '\x072b3e5391b8bc868934562e510e6b2454163093'
OP_DODO_V1_ADAPTER                    = '\xdd0951b69bc0cf9d39111e5037685fb573204c86'
OP_DODO_V2_ADAPTER                    = '\x169ae3d5acc90f0895790f6321ee81cb040e8a6b'
OP_UNI_ADAPTER                        = '\x59bef1eedfcc26e7c9fd47c22625f81124228fad'
OP_DODO_V2_ROUTE_HELPER               = '\xc48a8e689a644de96f80786acb69e6f76d057f25'
OP_DODO_CALLEE_HELPER                 = '\x0bd7426f008737feed575ed8e2aa1bd4fc49112d'
OP_DODO_SELL_HELPER                   = '\x56f8e27b27bff96b5203c95977e8982f62be70c2'
OP_DODO_V1_PMM_HELPER                 = '\x6281e0628eb2b37fe9943279ea39725d5f0e0dbe'
OP_DODO_SWAP_CALC_HELPER              = '\x2815b0addb0becf86b10982a86a133ae9d36ab0f'
OP_ERC20_HELPER                       = '\x42e456ea0dd7538ea103fbb1d0388d14c97bb5b2'
OP_MULTICALL                          = '\xb98ac2fefc8b73aeae33d02bb00c26e12afca9df'

-- ===== Polygon PoS (chain ID 137) =====
POL_DODO_APPROVE                      = '\x6d310348d5c12009854dfcf72e0df9027e8cb4f4'
POL_DODO_APPROVE_PROXY                = '\x01feea29da5ae41b0b5f6b10b93ee34752ef80d7'
POL_DODO_V2_PROXY                     = '\x45894c062e6f4e58b257e0826675355305dfef0d'
POL_ROUTE_PROXY                       = '\x53ee28b9f0a6416857c1e7503032e27e80f52da0'
POL_FEE_ROUTE_PROXY                   = '\x39e3e49c99834c9573c9fc7ff5a4b226cd7b0e63'
POL_FEE_ROUTE_PROXY_WIDGET            = '\xa103206e7f19d1c1c0e31efc4dfc7b299630f100'
POL_DSP_PROXY                         = '\xfddca6ffce24df5be3e8aad32081822f86178048'
POL_CP_PROXY                          = '\x5480b32c03647ff5e5a653f0465e798dbe558b57'
POL_DPP_PROXY                         = '\xf6f1a1ef2f5b56bb289993f75c12eb41e4abc2f7'
POL_DODO_V1_ADAPTER                   = '\xdbfaf391c37339c903503495395ad7d6b096e192'
POL_DODO_V2_ADAPTER                   = '\x6c30be15d88462b788dea7c6a860a2ccaf7b2670'
POL_UNI_ADAPTER                       = '\xe373df144a70bccc10190f97bede647d1ed6cfc8'
POL_DODO_V2_ROUTE_HELPER              = '\x6b0c1ec661b776a819f5d5b2d0b622de3419fdb0'
POL_DODO_CALLEE_HELPER                = '\x261f6cf4df0e5c1432739cdafd9299150fed3dfc'
POL_DODO_V1_PMM_HELPER                = '\x18dfde99f578a0735410797e949e8d3e2afcb9d2'
POL_LIMIT_ORDER                       = '\x5f43046ead98012044cfc1c3427a1bcef921d3f3'
POL_LIMIT_ORDER_BOT                   = '\xa7263eb38b9a61b72397c884b5f9bfb5c34a7840'

-- EIP-1967 storage slots (impl reads 0x0 on EVERY contract in this file)
EIP1967_IMPL_SLOT                     = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                    = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- Native gas-token sentinel used in OrderHistory fromToken/toToken
DODO_ETH_SENTINEL                     = '\xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
```

---

## 14. Verification & sources

How every constant in this doc was verified:

- **Function selectors and topic0 hashes:** computed locally as `keccak256(canonical signature)[0:4]` / full `keccak256` (pycryptodome `Crypto.Hash.keccak`). Canonical signatures taken from the source of `DODOEX/contractV2` (`contracts/SmartRoute/DODOApprove.sol`, `DODOApproveProxy.sol`, `DODOV2Proxy02.sol`, `proxies/DODORouteProxy.sol`, `proxies/DODOFeeRouteProxy.sol`, `proxies/DODODspProxy.sol`, `proxies/DODOCpProxy.sol`, `proxies/DODODppProxy.sol`, `adapter/*.sol`, `helper/*.sol`, `sampler/CurveSample.sol`, `external/Multicall.sol`), `DODOEX/dodo-route-contract` (the deployed `DODOFeeRouteProxy`/`DODORouteProxy` build), and `DODOEX/dodo-limit-order` (`src/DODOLimitOrder.sol`, `src/DODOLimitOrderBot.sol`).
- **`OrderHistory` topic0 (`0x92ceb067…`):** cross-checked against **live `eth_getLogs`** on Ethereum for the `DODOV2Proxy` (`0xa356867f…FdC`), the `RouteProxy` (`0xa2398842…D28a`), and the `DODOFeeRouteProxy` (`0x50f9bDe1…6194`) — all three return logs with this topic0, 1 topic, and a 5-word (160-byte) data payload, confirming the all-non-indexed 5-field signature.
- **`LimitOrderFilled` topic0 (`0x30a60b21…`):** cross-checked against live `eth_getLogs` on the Ethereum `LimitOrder` (`0x093b…17EB`) — log has 3 topics (sig + indexed maker, taker) and 3 data words, matching the signature. `ORDER_TYPEHASH()` read live = `0x9e31ac29…` and matches `keccak256` of the 8-field `Order` struct.
- **Immutability (NOT EIP-1967):** `eth_getStorageAt(addr, 0x360894…bbc)` returns `0x0` for `DODOV2Proxy`, `RouteProxy`, `DODOFeeRouteProxy`, `DODOApprove`, `DODOApproveProxy`, `DSPProxy`, `CpProxy`, `DPPProxy`, and `LimitOrder` on Ethereum — confirming they are plain immutable contracts, not upgradeable proxies.
- **Allowance wiring:** `eth_call` on Ethereum — `DODOApprove.getDODOProxy()` and `_DODO_PROXY_()` both return `0x335aC99…` (the `DODOApproveProxy`); `DODOApproveProxy._DODO_APPROVE_()` returns `0xCB859e…` (the `DODOApprove`); `DODOApproveProxy.isAllowedProxy(x)` returns **true** for `DODOV2Proxy`, `RouteProxy`, `DODOFeeRouteProxy`, `DODOFeeRouteProxy(widget)`, `DSPProxy`, `DPPProxy`, and `LimitOrder`, and **false** for `CpProxy`. Spot-checked on BNB, Avalanche, and Optimism (`isAllowedProxy` true for the present routers there).
- **Address bytecode existence:** `eth_getCode` on `https://ethereum-rpc.publicnode.com`, `https://base-rpc.publicnode.com`, `https://bsc-rpc.publicnode.com`, `https://avalanche-c-chain-rpc.publicnode.com`, `https://arbitrum-one-rpc.publicnode.com`, `https://optimism-rpc.publicnode.com`, `https://polygon-bor-rpc.publicnode.com` — every address in §3–§9 returns non-empty bytecode on its chain; every `—` in §10 returns `0x`. The 127 in-scope (contract, chain) pairs were checked; zero registry-listed addresses were empty.
- **Fee-proxy build:** the registry `DODOFeeRouteProxy` on all 7 chains is byte-size-identical (10945 B, older `dodo-route-contract` build) and contains the older selectors (`0xa8676443` / `0x301a3720` / `0x94cfab17`); the `expReturnAmount` selectors and the `PositiveSlippage` topic0 are absent from it. **Ethereum additionally runs the newer `contractV2` build at `0xFe837A3530dD566401d35beFCd55582AF7c4dfFC` (11202 B)** — `eth_getCode` confirms the `PositiveSlippage` topic0 `0xd820290d…` in its runtime and the absence of the older `externalSwap` selector `0xa8676443`; `eth_call` confirms `_DODO_APPROVE_PROXY_()` = `0x335aC99…` (same hub). The older build's address `0xFe837A35…` returns empty/unrelated bytecode on the other 6 chains (newer build not found there at this address). The widget variant shares a byte-identical runtime hash with the older fee proxy on Ethereum.
- **Helper identity:** the Ethereum `DODOV2RouteHelper` (`0x6e90797C…`) returns the canonical ETH DVM/DPP/DSP factory addresses from `_DVM_FACTORY_/_DPP_FACTORY_/_DSP_FACTORY_` and contains `getPairDetail` — confirming the registry address (in preference to the older deployment referenced in the deploy config).

Authoritative source repos and references:

- [`DODOEX/contractV2`](https://github.com/DODOEX/contractV2) — `contracts/SmartRoute/*` (DODOApprove, DODOApproveProxy, DODOV2Proxy02, proxies, adapters, helpers, sampler), `contracts/helper/ERC20Helper.sol`, `contracts/external/Multicall.sol`.
- [`DODOEX/dodo-route-contract`](https://github.com/DODOEX/dodo-route-contract) — the deployed `DODORouteProxy` / `DODOFeeRouteProxy` aggregator build + `DODOApprove`/`DODOApproveProxy`.
- [`DODOEX/dodo-limit-order`](https://github.com/DODOEX/dodo-limit-order) — `DODOLimitOrder` / `DODOLimitOrderBot`.
- [`DODOEX/docs`](https://github.com/DODOEX/docs) and the DODO developer docs — address registries per chain.
- Block explorers used for byte-level confirmation: Etherscan, BaseScan, BscScan, SnowTrace, Arbiscan, Optimistic Etherscan, PolygonScan.
