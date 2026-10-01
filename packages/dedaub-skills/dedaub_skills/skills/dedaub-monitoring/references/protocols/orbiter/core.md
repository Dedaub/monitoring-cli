# Orbiter Finance Core (Routers + Aggregator + Maker EOAs + OPool + Vizing Pad) — Topics, Selectors, Addresses (Ethereum, Arbitrum, Optimism, Polygon, BNB, Base, Avalanche; not Robinhood Chain)

**Status:** verified against live RPC on all six EVM target chains, the Sourcify-verified `OrbiterXRouter` source on Ethereum mainnet, the `Orbiter-Finance/OB_ReturnCabin` repo (`OBSource.sol` legacy router), and live `eth_getCode`/`eth_getStorageAt` reads on 2026-06-09. Extended on 2026-09-29 with the `Aggregator` (Blockscout-verified source), the second-generation `Opool` (Sourcify-verified source), the `VizingPad` message station (`Orbiter-Vizing` sources), the current official maker list, and Robinhood Chain (4663); every new value was re-checked live on the eight target chains. The decentralized arbitration / Maker-Deposit-Contract framework is documented separately in [mdc.md](./mdc.md).
**Scope:** the production cross-rollup bridge surface — the on-chain `OrbiterXRouter` (a.k.a. "OrbiterRouterV3"), the legacy `OBSource` router, the upgradeable `Aggregator` (swap and bridge entry that emits `BridgeExecuted`), both `OPool` maker-liquidity pool generations, the `VizingPad` omni-chain message station, and the off-chain **Maker EOAs** that actually receive/send bridged funds. Topics + selectors are **chain-agnostic**; addresses are network-specific. **Avalanche C-Chain has only the `Aggregator` proxy** (same address, same ProxyAdmin and owner; not in the official Aggregator list); the routers, both OPools and the Vizing Pad return `0x` there. **Robinhood Chain (4663) has no Orbiter contract and is not an Orbiter-supported chain** (§10).

Orbiter Finance is a **cross-rollup bridge with an optimistic / off-chain-relayer design**. The defining architectural fact a monitoring engineer must internalize: **most Orbiter volume is plain EOA-to-EOA transfers, not contract calls.** A user sends native coin or an ERC-20 *directly to a Maker's externally-owned address* (the explorer-labelled "Orbiter Finance: Bridge N" wallets), encoding the destination chain in the **trailing digits of the transfer amount** (the "identification code", e.g. `…9001` for one chain, `…9002` for another). The Maker's off-chain backend watches its EOA, decodes the destination, and pays out on the target chain from the *same Maker EOA* (or from `OPool`). The on-chain `OrbiterXRouter` is an **optional convenience wrapper**: it forwards the user's funds to the Maker EOA in one call and (for native transfers only) emits a single `Transfer(to, amount)` event; it holds no funds and has no owner. The `data` blob passed to the router carries the destination/identification code so the router transfer is indistinguishable downstream from a direct EOA send.

**The routers and both OPool generations are immutable and non-upgradeable** — no proxies, no admin/impl slots, no governance on the routers. **The `Aggregator` (EIP-1967 transparent proxy, ProxyAdmin owned by an EOA) and the `VizingPad` (UUPS, `AccessControl`) are upgradeable** — see §11. The router is a CREATE2/plain deploy that is **byte-for-byte identical on all six EVM chains** (runtime sha256 `27f13214…`, 3183 bytes). It has **unique addresses on Ethereum / Arbitrum / Optimism / Polygon** but a **single shared address `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` on BNB + Base** (and, off-target, on Scroll/Linea/Mantle/Blast/Polygon-zkEVM). `OPool` exists on **Arbitrum + BNB only**.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Verified name | Where |
|----------|------|--------|---------------|-------|
| **OrbiterXRouter** ("OrbiterRouterV3") | Multicall transfer wrapper: single + batch native and ERC-20 forwards to the Maker. Native path emits `Transfer`; token path does not. | **No** (immutable, 3183 B, no owner) | `OrbiterXRouter` (Sourcify exact-match, solc 0.8.19) | ETH, ARB, OP, POLY, BNB, Base |
| **OBSource** (legacy "V1" router) | Original router: `transfer(address,bytes)` + `transferERC20(...)`. No events. Superseded by OrbiterXRouter. | **No** (immutable) | `OBSource` (in `OB_ReturnCabin/contracts/OBSource.sol`) | historical; same `transfer` selector as V3 |
| **OPool** (first generation, `0x6285a466a98f513e1f6be29acad27d173d3b3c59`) | Maker **liquidity pool**: makers/managers pay out destination transfers via `outbox`/`outboxBatch` from pooled funds instead of from a bare EOA. `Ownable`. Emits `Inbox` (6-field) and `Outbox` (§1.3). | **No** (immutable, 5454 B) | unverified on Sourcify; bytecode/selector-confirmed | **ARB + BNB only** |
| **Opool** (second generation, `0x68b5a1c02dea0958388eee5361f021018bd8dbe7`) | Open-token pool of the official OPool page: `inbox` escrows the bridge token and pays the fee to the maker (`Inbox`); a listed maker calls `outbox`/`outboxBatch` on the destination (`Outbox`). `Ownable`, `ReentrancyGuard`. | **No** (immutable, 6486 B) | `Opool` (Sourcify match, solc 0.8.23) | **ETH, ARB, OP, BNB, Base** (same address) |
| **Aggregator** (`0xe530d28960d48708ccf3e62aa7b42a80bc427aef`) | Swap and bridge entry: `executeBridge` sends the input (less an optional commission) to the maker in the same call and emits `BridgeExecuted`; `executeSwap` swaps through the `Execute` executor and emits `SwapExecuted`. `Ownable` + `Pausable`. | **Yes** — EIP-1967 transparent proxy, ProxyAdmin `0x606da564f6a9cc98fcb08e49414b30d3ad9e839d` | `Aggregator` (Blockscout-verified, solc 0.8.28) | **ETH, ARB, OP, POLY, BNB, Base, Avalanche** (same address; Avalanche is not in the official Aggregator list) |
| **Execute** (Aggregator executor) | Runs the swap calls of `executeSwap`; only the Aggregator can call it; blocks `transfer`/`transferFrom` selectors. | No (4919 B, same code on every chain) | `Execute` (bundled with the Aggregator source) | one per chain (§3–§9) |
| **VizingPad** (Vizing message station of Orbiter) | Omni-chain messaging: `Launch` takes `msg.value` and emits `SuccessfulLaunchMessage`; a relayer's `Landing` delivers the value and message and emits `SuccessfulLanding`. The DefiLlama Orbiter bridge adapter counts Pad value as Orbiter volume. | **Yes** — UUPS (ERC-1967 impl slot), `AccessControl` | not on Sourcify; ABI from `Orbiter-Vizing/vizing_npm_package` | ETH, Base, BNB `0x5d77b0c9855f44a8fbef34e670e243e988682a82`; ARB `0xd725bc299a232201984fecb4ff106d84e894193f`; OP `0x523d8b6893d2d0ce2b48e7964432ce19a2c641f2` |
| **Maker EOAs** ("Orbiter Finance: Bridge N") | The actual liquidity-provider wallets that receive user deposits and send payouts. **Plain EOAs** (`eth_getCode` = `0x`), same address re-used across chains. The official maker page lists nine current EVM makers (§3); three of the five makers first listed in this file are struck through (deprecated) there. On Arbitrum two current makers carry a 23-byte EIP-7702 delegation designator. | n/a (EOA) | — | all chains except Robinhood Chain |

> `transfer(address,bytes)` shares the selector `0x29723511` between **OBSource (V1)** and **OrbiterXRouter (V3)** — the canonical signature is identical, so the selector alone does not tell you which router generation you are looking at. Disambiguate by the **contract address** / bytecode.

**Flow, link key and value movement per path** (read from the verified sources and from the sample transactions of §14):

| Path | Source leg (user funds in) | Destination leg (payout) | Link key | Value movement in the source transaction |
|---|---|---|---|---|
| Maker EOA direct | native send (no log) or ERC-20 `Transfer` to a maker | native or ERC-20 `Transfer` from a maker (or OPool `Outbox`) on the target chain | none on chain; the last four digits of the amount carry the destination "identification code" | the transfer itself |
| OrbiterXRouter | `Transfer(address indexed to, uint256 amount)` (native paths only) | maker payout as above | none on chain | `msg.value` forwarded to the maker; ERC-20 `transferFrom` user → maker (no router event) |
| Aggregator `executeBridge` | `BridgeExecuted` (`recipient` = the maker) | maker payout as above | none on chain; `extData` is hex of a URL query: `c=` target chain as a plain EVM chain id, `t=` target recipient | native: `call{value}` Aggregator → maker (no log); ERC-20: `transferFrom` user → maker; optional commission to `feeRecipient` (`CommissionTransferred`) |
| Opool (second generation) | `Inbox` | `Outbox`, called by a listed maker | `Outbox.data` carries the source transaction id (partly verified, §12) | ERC-20 `Transfer` user → pool (or the token's receiver) and fee → maker; native in `msg.value` |
| OPool (first generation) | `Inbox` (6-field) | `Outbox` | the `c=90xx` code in `Inbox.data`; no source id observed | ERC-20 `Transfer` user → pool; native fee in `msg.value` |
| VizingPad | `SuccessfulLaunchMessage` (`nonce` indexed) | `SuccessfulLanding` (`messageId` indexed) | `SuccessfulLanding.params` carries `srcChainid`, `srcTxHash` and `srcChainNonce` (= the launch `nonce`) — on chain on both sides | `msg.value` into the Pad; `Landing` forwards `value` to the destination contract |

**Refund path:** none of these contracts has a refund or expiry event. Per the official bridge-protocol page, a sender whose payout does not arrive can start arbitration against the maker's margin in the MDC framework ([mdc.md](./mdc.md), `ChallengeInfoUpdated`), whose addresses are unpublished. **Status-only events:** `SwapExecuted` (a same-chain swap, not a bridge leg), `CommissionTransferred`, and every admin event of §1.4–§1.5.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 OrbiterXRouter ("OrbiterRouterV3")

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x69ca02dd4edd7bf0a4abb9ed3b7af3f14778db5d61921c7dc7cd545266326de2` | `Transfer(address indexed to, uint256 amount)` | **Only emitted by the native paths** (`transfer`, `transfers`) — one log per recipient with `to` = Maker EOA, `amount` = native value. **NOT a standard ERC-20 `Transfer`** (that is `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` with 3 args). |

**The ERC-20 paths (`transferToken`, `transferTokens`) emit NO router event** — they call `token.safeTransferFrom(user → maker)`, so the only on-chain log is the underlying token's own `Transfer(address,address,uint256)` (`0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`). This is why the router's own event is rare in logs even on high-volume chains.

### 1.2 OBSource (legacy router)

No events. `transfer` does a raw `call{value}` and `transferERC20` does a bare `transferFrom`; neither emits.

### 1.3 OPool (both generations)

Correction (2026-09-29): both OPool generations do emit events. The first-generation pool `0x6285a466a98f513e1f6be29acad27d173d3b3c59` carries the `Outbox` topic and a 6-field `Inbox` topic in its bytecode, and Arbitrum Blockscout shows 45 `Inbox` and 5 `Outbox` logs in its latest 50. The second-generation `Opool` source is verified on Sourcify. Ownership changes emit the OZ `OwnershipTransferred(address,address)` (`0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0`).

| topic0 | Event | Emitter / notes |
|--------|-------|-----------------|
| `0x2b949f65b3c31db2d422b7946dd04ba24c90ce95fe272b92dfd6b3a89742f658` | `Inbox(address indexed bridgeReceiver, address indexed bridgeToken, address indexed feeReceiver, address feeToken, uint256 feeAmount, uint256 bridgeAmount, bytes data)` | Second-generation **source leg**. `bridgeReceiver` = the pool itself unless `tokenReceivers[token]` is set; `feeReceiver` = the maker; `data` = hex of `t=<target recipient>&c=<target EVM chain id>&...`. |
| `0xd617ac92b22579a90e8584a9f590f1e0b8d58ccc04fac6c3b4f9c41bbaa403bc` | `Inbox(address indexed maker, address indexed token, address sender, address receiver, uint256 amount, bytes data)` | First-generation **source leg**. Parameter names inferred from a decoded sample (source not verified): topic1 = the OPOOL maker, topic2 = the bridged token, `receiver` = the pool, `data` = `c=90xx`. |
| `0x94a52be301a8d5e17bb003f96e429ff5b1c6e1838e0e8adf2b00dcab2d726d41` | `Outbox(address indexed token, address to, uint256 amount, bytes data)` | **Destination leg** of both generations (one log per recipient in `outboxBatch`). `to` = the user; `data` = the source transaction id (§12). |

### 1.4 Aggregator (`0xe530d28960d48708ccf3e62aa7b42a80bc427aef`, `IAggregatorEvents`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x783c31b20881b105b9b6e1bb8515e9e5816b2dbd62ba77aea928f463f12c2629` | `BridgeExecuted(address indexed sender, address indexed recipient, address inputToken, address outputToken, uint256 inputAmount, bytes extData)` | **Source leg.** `sender` = the user; `recipient` = the maker EOA; `inputToken` `0x0` or `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE` = native; `inputAmount` is net of the commission; `extData` = hex of `t=...&c=...&m=...`. |
| `0xe256398f708e8937c16a21cadd2cc58b7766662cdf76b3dfcf1e3eb3dc6cbd16` | `SwapExecuted(address indexed sender, address indexed recipient, address inputToken, address outputToken, uint256 inputAmount, uint256 outputAmount, bytes extData)` | Same-chain swap (status of a swap, not a bridge leg, in the samples read). |
| `0x6c4932eb246c92f633ab70f9aadf3a6e79f40f4189b15be420b418205f7a7760` | `CommissionTransferred(address indexed token, address indexed recipient, uint256 amount)` | Commission paid to the integrator's `feeRecipient` in the same call. |
| `0x0ef3c7eb9dbcf33ddf032f4cce366a07eda85eed03e3172e4a90c4cc16d57886` | `ExecutorUpdated(address indexed oldExecutor, address indexed newExecutor)` | Admin: swap executor changed. |
| `0xec9fc77409b3224e46d50b2e92ab7ae0b43f0cb85d9743888276f56d73ed6b51` | `WethAddressUpdated(address _oldAddress, address _newAddress)` | Admin. |
| `0xe2d55444a35ed24928e620ac5be0c7f11f17b38d1a7d746fb4327b081d3fd0af` | `MaxCommissionRateUpdated(uint256 oldRate, uint256 newRate)` | Admin. |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | OZ `PausableUpgradeable` — **bridge and swap halted**. |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | OZ. |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | EIP-1967 — implementation swap on the proxy. |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` | EIP-1967 — ProxyAdmin replaced. |

### 1.5 VizingPad (Vizing `IMessageEvent`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xef6cc763bf0623d44a08595d2d459bb3b0c6a31123b132d8b33b57a377406546` | `SuccessfulLaunchMessage(uint32 indexed nonce, uint64 earliestArrivalTimestamp, uint64 latestArrivalTimestamp, address relayer, address sender, address srcContract, uint256 value, uint64 destChainid, bytes additionParams, bytes message)` | **Source leg.** `value` = native amount to deliver; `destChainid` = a plain EVM chain id. |
| `0x54eb62a77fb8b5bfecbcaf246702c30b71c610898d475629b345bebfa5c85598` | `SuccessfulLaunchMultiMessages(uint32[] indexed nonce, uint64 earliestArrivalTimestamp, uint64 latestArrivalTimestamp, address relayer, address sender, address srcContract, uint256[] value, uint64[] destChainid, bytes[] additionParams, bytes[] message)` | Source leg, several destinations. The indexed `uint32[]` topic1 is the keccak of the array, not a value. |
| `0xab71ef78f87843dcbe693ff9d486051b58c4a8a04a0c3c56380a67979c218e4b` | `SuccessfulLanding(bytes32 indexed messageId, (bytes32 messageId, uint64 earliestArrivalTimestamp, uint64 latestArrivalTimestamp, uint64 srcChainid, bytes32 srcTxHash, uint256 srcContract, uint32 srcChainNonce, uint256 sender, uint256 value, bytes additionParams, bytes message) params)` | **Destination leg.** The tuple is `landingParams`; `srcContract` and `sender` are `uint256` (non-EVM safe). |
| `0x9dba95668a3b2897545e9f8cf74f368af9957cee5aaf19b9b10e7ec9cced0ab3` | `EngineStateRefreshing(bool indexed isPause)` | Admin: pause / resume of the station. |
| `0xc42198387755d1905bd3c5b3ed34925a52f21b418fa2f083c6f95932bb7615df` | `PaymentSystemChanging(address indexed gasSystemAddress)` | Admin: fee system changed. |
| `0x17040713250ec5f668a1c39e7939900e78558350dbaff0ebef34268dfa8ea4ac` | `WithdrawRequest(address indexed to, uint256 amount)` | Admin withdrawal of Pad fees. |

All six VizingPad topics and `Upgraded` occur in the implementation bytecode `0x248dd200e77d59f582c5a2bd39b716211996fed4` (PUSH32 scan).

> **There is no Orbiter-specific bridge event for the dominant flow.** A Maker-EOA deposit is just a native send (no log at all) or an ERC-20 `Transfer` to the Maker. Attribution to "Orbiter" is by **counterparty address** (Maker EOA / router / OPool), not by a topic. See §8. The contract paths that do emit are the router `Transfer` (native), the Aggregator `BridgeExecuted`, the OPool `Inbox`/`Outbox` and the VizingPad launch/landing events.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 OrbiterXRouter ("OrbiterRouterV3") — all 4 functions, all `payable`, `nonReentrant`

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x29723511` | `transfer(address to, bytes data)` | Native single. `payable(to).transfer(msg.value)`; emits `Transfer(to,msg.value)`. `to` = Maker EOA; `data` carries the identification/destination code. |
| `0x52346412` | `transfers(address[] tos, uint256[] values)` | Native batch. Requires `sum(values) == msg.value` exactly; emits `Transfer` per recipient. |
| `0xf9c028ec` | `transferToken(address token, address to, uint256 value, bytes data)` | ERC-20 single. `requires msg.value == 0`; `safeTransferFrom(msg.sender → to)`. **No router event.** |
| `0xd54cefc1` | `transferTokens(address token, address[] tos, uint256[] values)` | ERC-20 batch. **No router event.** |

The four selectors `0x29723511 / 0x52346412 / 0xf9c028ec / 0xd54cefc1` are confirmed present in the live router bytecode on every chain (PUSH4 dispatch scan). The router has **no** `owner()`/`Ownable` (selector `0x8da5cb5b` absent in bytecode) — only a `bool locked` reentrancy guard at storage slot 0.

### 2.2 OBSource (legacy router)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x29723511` | `transfer(address to, bytes ext)` | Native. Raw `to.call{value:msg.value}("")`. **Same selector as V3** `transfer`. |
| `0x46f506ad` | `transferERC20(address token, address to, uint256 amount, bytes ext)` | ERC-20 via `transferFrom`. **Different selector from V3** `transferToken` (`0xf9c028ec`) — the param order/types differ. |

### 2.3 OPool (maker liquidity pool — `Ownable`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc86238d3` | `outbox(address token, address to, uint256 amount, bytes data)` | Maker payout of a single destination transfer from pool liquidity. |
| `0x809bb9cd` | `outboxBatch(address token, address[] to, uint256[] amounts, bytes[] data)` | Batched maker payouts. |
| `0xf3fef3a3` | `withdraw(address token, uint256 amount)` | Pull liquidity out of the pool. |
| `0xb22b6094` | `setMakerList(address[] makers, bool[] statuses)` | Owner: authorise/deauthorise maker addresses. |
| `0x0a7bf733` | `setManagerList(address[] managers, address[] ...)` | Owner: manager roles. |
| `0xc21b47fb` | `setTokenReceiver(address[] tokens, address[] receivers)` | Owner: per-token receiver routing. |
| `0x7e22e3a6` | `makerList(address)` → `bool/...` | View: maker authorisation. |
| `0xa59be4c7` | `managerList(address)` → `...` | View: manager. |
| `0x19096f0c` | `tokenReceivers(address)` → `address` | View: per-token receiver. |
| `0x8da5cb5b` | `owner()` → `address` | OZ `Ownable`; live value `0x09053d505447191060b0e0720a8b255a00aaedd8` (same on ARB + BNB). |
| `0xf2fde38b` / `0x715018a6` | `transferOwnership(address)` / `renounceOwnership()` | OZ `Ownable`. |

Three further dispatch selectors (`0x884ae7d4`, `0xb155b156`, `0x3146104a`) appear in the OPool bytecode but were not resolvable against the public signature database; they are minor view/admin helpers (OPool source is not verified on a public registry). Treat the verified `outbox`/`outboxBatch`/`withdraw`/`setMakerList` set as the monitoring surface.

Correction (2026-09-29): `0x884ae7d4` resolves to the first-generation **source-leg** function below (public signature database, and the calldata of Arbitrum transaction `0xb433831ad9c4448dcf830b2de8a7a40228ea49d878565bc8b796d49c359c45da`). `0xb155b156` and `0x3146104a` do not occur in the Arbitrum or BNB OPool bytecode (PUSH4 scan).

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x884ae7d4` | `inbox(address maker, address token, uint256 amount, bytes data)` | First-generation source leg; `payable` (native fee in `msg.value`); emits the 6-field `Inbox`. Parameter names inferred from calldata. |

### 2.4 Opool (second generation, `0x68b5a1c02dea0958388eee5361f021018bd8dbe7`; Sourcify-verified)

Same `outbox` / `outboxBatch` / `withdraw` / `setMakerList` / `setManagerList` / `setTokenReceiver` / `makerList` / `managerList` / `tokenReceivers` / `owner` selectors as §2.3 (verified in the source and the bytecode), plus:

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf23b971c` | `inbox(address feeReceiver, address feeToken, uint256 feeAmount, address bridgeToken, uint256 bridgeAmount, bytes data)` | **Source leg**, `payable`, `nonReentrant`. Pays the fee to `feeReceiver` (the maker), moves `bridgeAmount` to the pool (or `tokenReceivers[token]`), emits `Inbox`. |

`outbox`/`outboxBatch` require `makerList[msg.sender]` (the OPOOL maker `0x732efacd14b0355999aebb133585787921aba3a9` reads `true` on Ethereum); `withdraw` requires the owner or the token's manager.

### 2.5 Aggregator (`Aggregator`, Blockscout-verified; all in the implementation bytecode)

Struct encodings from `contracts/library/Types.sol`: `BridgeRequest = (address recipient, address inputToken, uint256 inputAmount, bytes extData, bool unwrapped, address feeRecipient, uint256 feeAmount)`; `SwapRequest = (address recipient, address inputToken, address outputToken, uint256 inputAmount, uint256 minOutputAmount, bytes extData, bool unwrapped, address feeRecipient, uint256 feeAmount)`; `Call = (address target, uint256 value, bytes data)`. The field order of the official docs page differs from the verified source; the selectors below follow the source.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x5a2c71cd` | `executeBridge((address recipient, address inputToken, uint256 inputAmount, bytes extData, bool unwrapped, address feeRecipient, uint256 feeAmount) request)` | **Source leg**, `payable`, `whenNotPaused`. Emits `BridgeExecuted`. |
| `0x1725dc9b` | `executeSwap((address recipient, address inputToken, address outputToken, uint256 inputAmount, uint256 minOutputAmount, bytes extData, bool unwrapped, address feeRecipient, uint256 feeAmount) request, (address target, uint256 value, bytes data)[] calls)` | Same-chain swap through the executor. Emits `SwapExecuted`. |
| `0x8456cb59` | `pause()` | `onlyOwner`; emits OZ `Paused`. |
| `0x3f4ba83a` | `unpause()` | `onlyOwner`; emits OZ `Unpaused`. |
| `0x1c3c0ea8` | `setExecutor(address _executor)` | `onlyOwner`; emits `ExecutorUpdated`. |
| `0x01e33667` | `withdrawToken(address token, address to, uint256 amount)` | `onlyOwner` — moves any balance out of the Aggregator. |
| `0xb78b5e41` | `setMaxCommissionRate(uint256 _maxCommissionRate)` | `onlyOwner`. |
| `0x5b769f3c` | `setWETH(address _WETH)` | `onlyOwner`. |
| `0xc34c08e5` | `executor()` | View: current `Execute` contract. |
| `0x5c975abb` | `paused()` | View; `false` on all seven chains on 2026-09-29. |

### 2.6 VizingPad (Vizing `IMessageChannel`; all in the implementation bytecode)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x209afe56` | `Launch(uint64 earliestArrivalTimestamp, uint64 latestArrivalTimestamp, address relayer, address sender, uint256 value, uint64 destChainid, bytes additionParams, bytes message)` | **Source leg**, `payable`. Emits `SuccessfulLaunchMessage`. |
| `0xb14280ea` | `launchMultiChain((uint64 earliestArrivalTimestamp, uint64 latestArrivalTimestamp, address relayer, address sender, uint256[] value, uint64[] destChainid, bytes[] additionParams, bytes[] message) params)` | Several destinations. Emits `SuccessfulLaunchMultiMessages`. |
| `0xd443a1f2` | `Landing((bytes32 messageId, uint64 earliestArrivalTimestamp, uint64 latestArrivalTimestamp, uint64 srcChainid, bytes32 srcTxHash, uint256 srcContract, uint32 srcChainNonce, uint256 sender, uint256 value, bytes additionParams, bytes message)[] params, bytes[][] proofs)` | **Destination leg**, relayer role only, `payable`. Emits `SuccessfulLanding`. |
| `0xc0490913` | `LandingSpecifiedGas((bytes32 messageId, uint64 earliestArrivalTimestamp, uint64 latestArrivalTimestamp, uint64 srcChainid, bytes32 srcTxHash, uint256 srcContract, uint32 srcChainNonce, uint256 sender, uint256 value, bytes additionParams, bytes message)[] params, uint24 gasLimit, bytes[][] proofs)` | Same with a gas limit. |
| `0x85fdd542` | `estimateGas(uint256 value, uint64 destChainid, bytes additionParams, bytes message)` | View: fee quote. |
| `0x92b85cdf` | `GetNonceLaunch(uint64 chainId, address sender)` | View: next launch nonce of a sender. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | UUPS upgrade entry (admin role). |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0xc741900276cd598060b0fe6594fbe977392928f4` | Verified `OrbiterXRouter`, solc 0.8.19; immutable; deployer `0x8a700FdB6121A57C59736041D9aa21dfd8820660`. 3183 B. |
| Maker EOAs ("Bridge N") | `0x80c67432656d59144ceff962e8faf8926599bcf8` (Bridge 1) · `0xe4edb277e41dc89ab076a1f049f4a3efa700bce8` (Bridge 2) · `0x41d3d33156ae7c62c094aae2995003ae63f587b3` · `0xacc517ea627ceb71cf25e002adaa9761623837b9` (Bridge 4) · `0x9c6750d463ad17deec97a630af766f0a78f95127` (Bridge 5) | **Plain EOAs** (`eth_getCode`=`0x`). Same addresses re-used on ARB/OP/Base/etc. The real source/sink of bridged funds. **2026-09-29:** the official maker page strikes through (deprecates) Bridge 1 `0x80c67432656d59144ceff962e8faf8926599bcf8`, Bridge 2 `0xe4edb277e41dc89ab076a1f049f4a3efa700bce8` and `0x41d3d33156ae7c62c094aae2995003ae63f587b3`; Bridge 4 and Bridge 5 are current (USDC and USDT). |
| Maker EOAs — current official list (2026-09-29) | `0x3bdb03ad7363152dfbc185ee23ebc93f0cf93fd1` (ETH) · `0xacc517ea627ceb71cf25e002adaa9761623837b9` (USDC) · `0x9c6750d463ad17deec97a630af766f0a78f95127` (USDT) · `0x095d2918b03b2e86d68551dcf11302121fb626c9` · `0x1c84daa159cf68667a54beb412cdb8b2c193fb32` · `0xab0c8fbec583f20c97f9fda6a2af647b94c8e54d` · `0x732efacd14b0355999aebb133585787921aba3a9` (OPOOL) · `0x34723b92ae9708ba33843120a86035d049da7dfa` · `0xed01d58fe6433a5fe69720a0aa0ab1d1fdb15212` (ALL-TOKEN) | All nine are EOAs on Ethereum (nonces 89435, 5188, 3262, 1256, 79, 1, 1782, 913, 43). Token labels are the official page's. `0x732efacd14b0355999aebb133585787921aba3a9` is the maker that calls the OPools' `outbox` and receives the `inbox` fee. |
| **OPool** (first generation) | — | **Not deployed on Ethereum** (`0x6285a466a98f513e1f6be29acad27d173d3b3c59` returns `0x` here). |
| **Opool** (second generation) | `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` | 6486 B, immutable, Sourcify match; `owner()` = EOA `0x09053d505447191060b0e0720a8b255a00aaedd8`. Emits `Inbox` / `Outbox`. |
| **Aggregator** (proxy) | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | 1159 B transparent proxy → implementation `0xcfb2a37258ca53e002fbc830afee30d9642191e1` (9786 B); ProxyAdmin `0x606da564f6a9cc98fcb08e49414b30d3ad9e839d`; `owner()` = EOA `0xdd08e0aaaa2e063dafb2df2dee19b5b0dd220ff6`; `executor()` = `0xce4b0e43abafb8cef6b805696d6e3ecab7e6f8e8`. Deployed by EOA `0xbc50d0e58e90c579f1320ccea978d1e46f5b6163`. |
| **VizingPad** (proxy) | `0x5d77b0c9855f44a8fbef34e670e243e988682a82` | 142 B UUPS proxy → implementation `0x248dd200e77d59f582c5a2bd39b716211996fed4` (21977 B); `DEFAULT_ADMIN_ROLE` held by EOA `0xaebfe1ec47002d6b131060acfa969479aa37f611` (`hasRole` read live). Listed in the Vizing docs for Ethereum. |

---

## 4. Addresses — Arbitrum One (chain ID 42161)

Verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0x6a065083886ec63d274b8e1fe19ae2ddf498bfdd` | Identical bytecode to ETH (sha `27f13214…`). Unique per-chain address. |
| **OPool** | `0x6285a466a98f513e1f6be29acad27d173d3b3c59` | Maker liquidity pool, 5454 B; `owner()` = `0x09053d505447191060b0e0720a8b255a00aaedd8`. Shared CREATE2 address with BNB. |
| Maker EOAs | same as §3 (`0x80c67432656d59144ceff962e8faf8926599bcf8`, `0xe4edb277e41dc89ab076a1f049f4a3efa700bce8`, …) | EOAs. **2026-09-29:** the current makers `0x3bdb03ad7363152dfbc185ee23ebc93f0cf93fd1` and `0xacc517ea627ceb71cf25e002adaa9761623837b9` return 23 bytes of code here: the EIP-7702 designator `0xef0100` + delegate `0x63c0c19a282a1b52b07dd5a65b58948a07dae32b`. They are still EOAs. |
| **Opool** (second generation) | `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` | 6486 B, same code as Ethereum; `owner()` = `0x09053d505447191060b0e0720a8b255a00aaedd8`. |
| **Aggregator** (proxy) | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | Same proxy code → implementation `0x513570657eb3f4ff1935c6f93f552a1cee44a1ed` (same code hash as Ethereum's); same ProxyAdmin and owner; `executor()` = `0xdb09916571bb6aa6625444f1461a3faa848052bd`. |
| **VizingPad** (proxy) | `0xd725bc299a232201984fecb4ff106d84e894193f` | 170 B UUPS proxy → implementation `0x248dd200e77d59f582c5a2bd39b716211996fed4`. Listed in the Vizing docs for Arbitrum-One. The Ethereum Pad literal `0x5d77b0c9855f44a8fbef34e670e243e988682a82` returns `0x` here. |

---

## 5. Addresses — Optimism (chain ID 10)

Verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0x3191f40de6991b1bb1f61b7cec43d62bb337786b` | Identical bytecode; unique per-chain address. |
| **OPool** | — | **Not deployed** (`0x6285a466a98f513e1f6be29acad27d173d3b3c59` = `0x`). |
| Maker EOAs | same as §3 | EOAs. |
| **Opool** (second generation) | `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` | 6486 B, same code as Ethereum; `owner()` = `0x09053d505447191060b0e0720a8b255a00aaedd8`. |
| **Aggregator** (proxy) | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | Same proxy code → implementation `0xc4653436e617e4e62738972fcf97ead7d8edd8bc`; same ProxyAdmin and owner; `executor()` = `0xbe3f1b3ec613197a421db6cb619059c20e13fc30`. |
| **VizingPad** (proxy) | `0x523d8b6893d2d0ce2b48e7964432ce19a2c641f2` | 170 B UUPS proxy → implementation `0x248dd200e77d59f582c5a2bd39b716211996fed4`. Listed in the Vizing docs for Optimism. On Ethereum, Base and Arbitrum the same literal holds a 23057-byte non-proxy contract with the Pad code; it is not the listed Pad there. |

---

## 6. Addresses — Polygon PoS (chain ID 137)

Verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0x653f25dc641544675338cb47057f8ea530c69b78` | Identical bytecode; unique per-chain address. |
| **OPool** | — | **Not deployed** (`0x6285a466a98f513e1f6be29acad27d173d3b3c59` = `0x`). |
| Maker EOAs | same as §3 | EOAs. The deprecated Bridge 1 `0x80c67432656d59144ceff962e8faf8926599bcf8` returns a 23-byte EIP-7702 designator here (2026-09-29). |
| **Opool** (second generation) | — | **Not deployed** (`0x68b5a1c02dea0958388eee5361f021018bd8dbe7` = `0x`; not in the official OPool list for Polygon). |
| **Aggregator** (proxy) | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | Same proxy code → implementation `0x61ec5096bee792b3f24b27cf663028ffc8b8ae7e`; same ProxyAdmin and owner; `executor()` = `0xd4910d28e5a43a06ceb771f708a9e92a9ba7a286`. |
| **VizingPad** | — | **Not deployed** (all three Pad literals return `0x`). |

---

## 7. Addresses — BNB Smart Chain (chain ID 56)

Verified via `eth_getCode` on `https://bsc-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` | **Shared CREATE2 address with Base** (and off-target Scroll/Linea/Mantle/Blast/Polygon-zkEVM). Identical bytecode. |
| **OPool** | `0x6285a466a98f513e1f6be29acad27d173d3b3c59` | Maker liquidity pool; `owner()` = `0x09053d505447191060b0e0720a8b255a00aaedd8`. Shared address with Arbitrum. |
| Maker EOAs | same as §3 | EOAs. |
| **Opool** (second generation) | `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` | 6486 B, same code as Ethereum; `owner()` = `0x09053d505447191060b0e0720a8b255a00aaedd8`. |
| **Aggregator** (proxy) | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | Same proxy code → implementation `0xc4653436e617e4e62738972fcf97ead7d8edd8bc`; same ProxyAdmin and owner; `executor()` = `0xbe3f1b3ec613197a421db6cb619059c20e13fc30`. |
| **VizingPad** (proxy, unlisted) | `0x5d77b0c9855f44a8fbef34e670e243e988682a82` | 142 B UUPS proxy → implementation `0xa366ea26eb8f8f95d4e669b091b65f08a375012c` (21977 B, other code hash, same Vizing topics and selectors). **Not in the Vizing docs list** — treat as unverified. |

---

## 8. Addresses — Base (chain ID 8453)

Verified via `eth_getCode` on `https://base-rpc.publicnode.com`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OrbiterXRouter** (V3) | `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` | **Shared CREATE2 address with BNB.** Identical bytecode. |
| **OPool** | — | **Not deployed** (`0x6285a466a98f513e1f6be29acad27d173d3b3c59` = `0x`). |
| Maker EOAs | same as §3 | EOAs. `0x095d2918b03b2e86d68551dcf11302121fb626c9` and `0x1c84daa159cf68667a54beb412cdb8b2c193fb32` have nonce 0 here (never sent on Base). |
| **Opool** (second generation) | `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` | 6486 B, same code as Ethereum; `owner()` = `0x09053d505447191060b0e0720a8b255a00aaedd8`. |
| **Aggregator** (proxy) | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | Same proxy code → implementation `0xcfb2a37258ca53e002fbc830afee30d9642191e1` (same address as Ethereum); same ProxyAdmin and owner; `executor()` = `0xce4b0e43abafb8cef6b805696d6e3ecab7e6f8e8`. |
| **VizingPad** (proxy) | `0x5d77b0c9855f44a8fbef34e670e243e988682a82` | 142 B UUPS proxy → implementation `0x248dd200e77d59f582c5a2bd39b716211996fed4`; `DEFAULT_ADMIN_ROLE` = EOA `0xaebfe1ec47002d6b131060acfa969479aa37f611`; role `0x28983de5890b6a39bb18ef1563c0a347573aecdcced4457ef756c40e13bdf418` was granted at block 14448582 to EOA `0x5f00d70c1715dcbe40df52c784745bd0a6987768`, the sender of the sampled `Landing` calls on Base and Ethereum. Listed in the Vizing docs for Base. |

---

## 9. Addresses — Avalanche C-Chain (chain ID 43114) — Aggregator only

Verified via `eth_getCode` on `https://avalanche-c-chain-rpc.publicnode.com`: **every** Orbiter address — the four router literals (`0xc741900276cd598060b0fe6594fbe977392928f4`, `0x6a065083886ec63d274b8e1fe19ae2ddf498bfdd`, `0x3191f40de6991b1bb1f61b7cec43d62bb337786b`, `0x653f25dc641544675338cb47057f8ea530c69b78`, `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172`) and `OPool` (`0x6285a466a98f513e1f6be29acad27d173d3b3c59`) — returns `0x`. **Orbiter has no on-chain core contracts on Avalanche.** Avalanche C-Chain is supported by Orbiter only via the **Maker-EOA flow** (a user sends to the Maker EOA directly; there is no router to wrap it).

**Correction (2026-09-29):** the `Aggregator` proxy is deployed on Avalanche, although the official Aggregator list does not name the chain. The second-generation Opool and every VizingPad literal return `0x`. Avalanche is in the official supported-chains list (maker flow).

| Role | Address | One-liner |
|------|---------|-----------|
| **Aggregator** (proxy) | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | Same 1159 B proxy code as the other six chains → implementation `0x61ec5096bee792b3f24b27cf663028ffc8b8ae7e` (same address and code hash as Polygon's); same ProxyAdmin `0x606da564f6a9cc98fcb08e49414b30d3ad9e839d` and owner `0xdd08e0aaaa2e063dafb2df2dee19b5b0dd220ff6`; `executor()` = `0xd4910d28e5a43a06ceb771f708a9e92a9ba7a286`. Treat as Orbiter's (same admin and owner), but it is unlisted. |
| Maker EOAs | `0x3bdb03ad7363152dfbc185ee23ebc93f0cf93fd1` (nonce 985) · `0xacc517ea627ceb71cf25e002adaa9761623837b9` (772) · `0x9c6750d463ad17deec97a630af766f0a78f95127` (258) · `0x34723b92ae9708ba33843120a86035d049da7dfa` (1) | EOAs. The other five current makers have nonce 0 on Avalanche. |

---

## 10. Cross-chain summary

| Chain | ID | OrbiterXRouter (V3) | OPool (gen 1) | Opool (gen 2) | Aggregator (proxy) | VizingPad | Maker EOAs |
|---|---|---|---|---|---|---|---|
| Ethereum | 1 | `0xc741900276cd598060b0fe6594fbe977392928f4` | ✗ | `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | `0x5d77b0c9855f44a8fbef34e670e243e988682a82` | ✓ (same set) |
| Arbitrum One | 42161 | `0x6a065083886ec63d274b8e1fe19ae2ddf498bfdd` | `0x6285a466a98f513e1f6be29acad27d173d3b3c59` | `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | `0xd725bc299a232201984fecb4ff106d84e894193f` | ✓ (two with EIP-7702 designators) |
| Optimism | 10 | `0x3191f40de6991b1bb1f61b7cec43d62bb337786b` | ✗ | `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | `0x523d8b6893d2d0ce2b48e7964432ce19a2c641f2` | ✓ |
| Polygon PoS | 137 | `0x653f25dc641544675338cb47057f8ea530c69b78` | ✗ | ✗ | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | ✗ | ✓ |
| BNB Smart Chain | 56 | `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` ⟂ | `0x6285a466a98f513e1f6be29acad27d173d3b3c59` | `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | `0x5d77b0c9855f44a8fbef34e670e243e988682a82` (unlisted) | ✓ |
| Base | 8453 | `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` ⟂ | ✗ | `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` | `0x5d77b0c9855f44a8fbef34e670e243e988682a82` | ✓ |
| **Avalanche** | 43114 | **✗ (0x)** | **✗ (0x)** | ✗ (0x) | `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` (unlisted) | ✗ (0x) | ✓ (EOA only) |
| **Robinhood Chain** | 4663 | ✗ (0x) | ✗ (0x) | ✗ (0x) | ✗ (0x) | ✗ (0x) | ✗ (nonce 0) |

**Robinhood Chain (4663) — no deployment (2026-09-29).** `eth_getCode` on `https://rpc.mainnet.chain.robinhood.com` returns `0x` for the five router literals, both OPools, the Aggregator, its ProxyAdmin and the four executors, and the three VizingPad literals. The twelve maker addresses (the nine current makers and deprecated Bridge 1, Bridge 2 and `0x41d3d33156ae7c62c094aae2995003ae63f587b3`) have nonce 0 and no code. The chain is not in the official supported-chains list, the Aggregator list, the OPool list or the Vizing Pad list. In the pinned window 2026-09-28 00:00–12:00 UTC (blocks 74350994–74780331) the router `Transfer`, `BridgeExecuted` and the three Vizing launch/landing topics had 0 logs from any emitter.

⟂ = the **shared** router address `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` (BNB + Base; also off-target Scroll/Linea/Mantle/Blast/Polygon-zkEVM). ETH/ARB/OP/POLY each have a **unique** router address but **identical bytecode** (runtime sha256 `27f13214…`). `OPool` (`0x6285a466a98f513e1f6be29acad27d173d3b3c59`) is **ARB + BNB only**.

**Vanity / tell:** there is no protocol-wide vanity prefix; the only address-level tell is the **shared CREATE2 router `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172`** and **shared OPool `0x6285a466a98f513e1f6be29acad27d173d3b3c59`**. The Maker EOAs are explorer-labelled "Orbiter Finance: Bridge N" and are the highest-signal attribution anchor. Since 2026-09-29 this file also records three more shared literals: the Aggregator proxy `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` (seven chains, one ProxyAdmin, per-chain implementations), the second-generation Opool `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` (five chains), and the VizingPad `0x5d77b0c9855f44a8fbef34e670e243e988682a82` (Ethereum, Base, BNB), whose Arbitrum and Optimism Pads sit at other addresses.

**Counterparty chains OUTSIDE the seven (this is a finding, not an omission):** Orbiter is a 40+-chain bridge. Beyond the seven targets it connects (with the same router on most): **zkSync Era (324), Polygon zkEVM (1101), Scroll, Linea, Mantle, Blast (81457), Arbitrum Nova, Manta, Mode, Taiko, Zora, Kroma, ZKFair, zkLink Nova, Merlin, BEVM, BOB, Core, Bitlayer, Fraxtal, Fuse, Gravity, Zircuit, Cyber, Mint, Optopia** and non-EVM **StarkNet** (Cairo `StarknetOrbiterRouter` at `0x058680be0cf3f29c7a33474a218e5fed1ad213051cb2e9eac501a26852d64ca2`), plus partially-supported **Solana / TON / Immutable X / Loopring / ZKSpace**. A transfer from one of the seven target chains very often has its **counterparty on an off-target chain** — decode the destination from the amount's identification-code suffix, do not assume the other leg is on a target chain.

---

## 11. Proxies (old & new)

**There are none** among the routers and OPools: each is an immutable, non-upgradeable deployment. **Correction (2026-09-29):** the `Aggregator` and the `VizingPad` are proxies (rows below).

| Contract | Pattern | Detection (2026-06-09) | Upgrade auth |
|----------|---------|------------------------|--------------|
| OrbiterXRouter (all 6 chains) | **Immutable, non-proxy** | EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` = `0x0` on ETH/ARB/OP/POLY/BNB/Base; no `owner()` selector in bytecode; 3183 B full contract. | none (no owner, no admin). |
| OBSource (legacy) | **Immutable, non-proxy** | full contract; no admin. | none. |
| OPool (ARB, BNB) | **Immutable, non-proxy** | EIP-1967 impl slot = `0x0`; 5454 B full contract; has `owner()` (Ownable) but **no upgrade path**. | `owner()` = `0x09053d505447191060b0e0720a8b255a00aaedd8` (param-setting only: maker/manager/receiver lists; **cannot** swap implementation). |
| Opool gen 2 (ETH, ARB, OP, BNB, Base) | **Immutable, non-proxy** (2026-09-29) | EIP-1967 impl slot empty; 6486 B; verified source has no upgrade path. | `owner()` = EOA `0x09053d505447191060b0e0720a8b255a00aaedd8` on all five chains (maker/manager/receiver lists; `withdraw` of any pool balance). |
| **Aggregator** (7 chains) | **EIP-1967 transparent proxy** (2026-09-29; Blockscout labels it `TransparentUpgradeableProxy`) | 1159 B proxy; impl slot → ETH/Base `0xcfb2a37258ca53e002fbc830afee30d9642191e1`, ARB `0x513570657eb3f4ff1935c6f93f552a1cee44a1ed`, OP/BNB `0xc4653436e617e4e62738972fcf97ead7d8edd8bc`, POLY/AVAX `0x61ec5096bee792b3f24b27cf663028ffc8b8ae7e` (one code hash, 9786 B); admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` → ProxyAdmin `0x606da564f6a9cc98fcb08e49414b30d3ad9e839d` (1063 B, same on all seven). | ProxyAdmin `owner()` = EOA `0xdd08e0aaaa2e063dafb2df2dee19b5b0dd220ff6`, which is also the Aggregator `owner()` (pause, executor, commission cap, `withdrawToken`). |
| **VizingPad** (ETH, Base, ARB, OP, BNB) | **UUPS** (2026-09-29) | 142 B (ETH, Base, BNB) or 170 B (ARB, OP) proxy; impl slot → `0x248dd200e77d59f582c5a2bd39b716211996fed4` (ETH, Base, ARB, OP) or `0xa366ea26eb8f8f95d4e669b091b65f08a375012c` (BNB); the implementation holds `upgradeToAndCall` `0x4f1ef286` and `proxiableUUID` `0x52d1902d`. | `AccessControl`; `DEFAULT_ADMIN_ROLE` = EOA `0xaebfe1ec47002d6b131060acfa969479aa37f611` (`hasRole` true on Base and Ethereum). |
| Execute (Aggregator executor) | Immutable, non-proxy | 4919 B, one code hash on all seven chains. | `Ownable` (withdraw, selector blocklist); replaced through `setExecutor`. |
| Maker EOAs | n/a (EOA) | `eth_getCode` = `0x`. | controlled by the off-chain Maker keypair. |

There is **no `Upgraded(address)` event to watch** on the routers or OPools (none are proxies). **Watch `Upgraded(address)` `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` and `AdminChanged` on the Aggregator proxy on all seven chains, and `Upgraded` on each VizingPad proxy.** The other governance actions are the `OPool` owners calling `setMakerList`/`setManagerList`/`setTokenReceiver` (and possible `transferOwnership`, topic `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0`), and the Aggregator owner calling `pause`, `setExecutor` or `withdrawToken`.

---

## 12. Detection invariants & gotchas

1. **The dominant flow is EOA→EOA, with NO Orbiter event and often NO log at all.** A native deposit to a Maker EOA produces zero logs; an ERC-20 deposit produces only the *token's* `Transfer`. **Attribute to Orbiter by counterparty address** (Maker EOA, router, or OPool) — there is no "bridge" topic to filter on for the main path.
2. **The destination chain is encoded in the trailing digits of the amount** (the "identification code", typically the last 4 digits, e.g. `…9001`/`…9002`/`…9014`). The real transferred value is `amount` minus that suffix's information. Do not treat the raw amount as the user's intended round number; the suffix is intentional.
3. **The `to` in the router `Transfer` event is the Maker EOA, not the end-user.** The end-user is `tx.from` / `msg.sender`. For ERC-20 paths there is no router event at all; read the user from the token `Transfer.from` and the maker from `Transfer.to`.
4. **`transfer(address,bytes)` selector `0x29723511` is shared by OBSource (V1) and OrbiterXRouter (V3).** Same canonical signature ⇒ same selector. Disambiguate the generation by the **contract address**, never by the selector.
5. **ERC-20 router selectors differ between generations:** V3 `transferToken` = `0xf9c028ec`; V1 `transferERC20` = `0x46f506ad`. If you key the legacy path on `0xf9c028ec` you will miss old OBSource flows and vice-versa.
6. **The router `Transfer` topic `0x69ca02dd4edd7bf0a4abb9ed3b7af3f14778db5d61921c7dc7cd545266326de2` is NOT the ERC-20 `Transfer` topic `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef`.** Different arg count (2 vs 3). Both may appear in the same tx (router event + token event); key the router event on the router address.
7. **Token-path transfers (`transferToken`/`transferTokens`, `OPool.outbox*`) emit no Orbiter event.** Indexing only on the router `Transfer` topic captures *native* flows only and silently drops every ERC-20 bridge. Cover ERC-20 by watching token `Transfer` logs where `to` ∈ {Maker EOAs, OPool}.
8. **`OPool` is the maker-pays-from-pool variant** (ARB + BNB only). A payout via `outbox`/`outboxBatch` originates from `0x6285a466a98f513e1f6be29acad27d173d3b3c59`, not from a Maker EOA — include OPool as a payout source/sink alongside the Maker EOAs. **2026-09-29:** the second-generation Opool `0x68b5a1c02dea0958388eee5361f021018bd8dbe7` does the same on ETH, ARB, OP, BNB and Base, and both generations emit `Outbox` (`0x94a52be301a8d5e17bb003f96e429ff5b1c6e1838e0e8adf2b00dcab2d726d41`) per payout — key the payout on that topic at the two pool addresses.
9. **Same router bytecode, different addresses.** ETH/ARB/OP/POLY have unique router addresses; BNB+Base share `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172`. **Always key on `(chainId, address)`** — `0x13e46b2a3f8512ed4682a8fb8b560589fe3c2172` is the same literal on BNB, Base, and several off-target chains.
10. **`OPool` shares `0x6285a466a98f513e1f6be29acad27d173d3b3c59` on ARB + BNB**, and its `owner()` is the same `0x09053d505447191060b0e0720a8b255a00aaedd8` on both — but they are independent deployments; key on `(chainId, address)`.
11. **Avalanche has no Orbiter contract.** Any "Orbiter on Avalanche" activity is a direct Maker-EOA send; do not look for a router/OPool there (`0x` everywhere). **Correction (2026-09-29):** the Aggregator proxy `0xe530d28960d48708ccf3e62aa7b42a80bc427aef` is live on Avalanche with the same ProxyAdmin and owner as on the listed chains, although the official Aggregator list omits Avalanche.
12. **Maker EOAs are reused across chains** (`0x80c67432656d59144ceff962e8faf8926599bcf8` is "Bridge 1" on ETH, ARB, OP, …). The full live Maker set rotates over time and is best sourced from the explorer "Orbiter Finance: Bridge N" labels; treat the §3 list as a seed, not exhaustive. **2026-09-29:** the official maker page now names nine current EVM makers (§3) and strikes through nine older ones, among them Bridge 1, Bridge 2 and `0x41d3d33156ae7c62c094aae2995003ae63f587b3`. Keep the deprecated makers in historical backfills only.
13. **No proxies, no `Upgraded` event, no liquidation/borrow semantics.** This is a bridge router, not a lending or AMM protocol — the only state-changing admin action on-chain is `OPool` owner list-setting. **Correction (2026-09-29):** the Aggregator (transparent proxy) and the VizingPad (UUPS) are upgradeable, and the Aggregator owner can pause it, change its executor and withdraw its balance (§11).
14. **The on-chain decentralized arbitration system (ORMDCFactory / ORManager / ORMakerDeposit) is a SEPARATE framework** — see [mdc.md](./mdc.md). It is *not* in the dominant transfer path; the live bridge runs on the EOA + router model documented here.
15. **`BridgeExecuted.recipient` is the maker, not the user.** The user is `sender` (topic1) and the target recipient is `t=` in `extData`. The Aggregator pays the maker inside the same call (native: an internal `call`, no log; ERC-20: `transferFrom` user → maker). In the sampled bridge the amount carried no four-digit code (`1638000000000000`); the destination was `c=42161` in `extData`, a plain EVM chain id. Decode `extData` as hex of a URL query.
16. **The router topic `0x69ca02dd4edd7bf0a4abb9ed3b7af3f14778db5d61921c7dc7cd545266326de2` is not unique to Orbiter.** In the pinned window it came only from other contracts: `ERC20Reserve` `0xb27132625173f813085e438ee19c011867063073` (Ethereum, 2 logs) and `GaleBridge` `0xa2c1ec79872d2c961cbd33ef750659e3b2439647` (Polygon, 3 logs). Always filter it by the router address.
17. **Two different `Inbox` topics.** First-generation `0xd617ac92b22579a90e8584a9f590f1e0b8d58ccc04fac6c3b4f9c41bbaa403bc` (6 fields, maker and token indexed) and second-generation `0x2b949f65b3c31db2d422b7946dd04ba24c90ce95fe272b92dfd6b3a89742f658` (7 fields, receiver, token and fee receiver indexed). Key each on its own pool address.
18. **`Outbox.data` is the source transaction id — partly verified.** On Base the Outbox `data` values read are the ASCII of base58 Solana signatures. On Ethereum and Arbitrum they are 32-byte values; seven such values (four Ethereum payouts, three Arbitrum payouts) were not found as transactions on the other target chains checked (Ethereum, Base, Arbitrum, BNB, Optimism); the sampled routes, such as SOPH, start on chains outside the eight. Treat `data` as the link key to the source transaction, and confirm it per route before matching.
19. **The VizingPad is Orbiter's messaging station, not the maker path.** The sampled launches came from Vizing token apps (an ERC-20 burn plus a message) and the landings from relayer EOA `0x5f00d70c1715dcbe40df52c784745bd0a6987768`. Link a landing to its launch by `params.srcChainid` + `params.srcTxHash` (or `srcChainNonce` = the launch `nonce`). Blockscout shows the last Pad logs at Ethereum block 21434578 and Base block 33911430.
20. **Pad literals collide across chains.** `0x523d8b6893d2d0ce2b48e7964432ce19a2c641f2` is the Optimism Pad proxy but a 23057-byte non-proxy contract with Pad code on Ethereum, Base and Arbitrum; `0x176baa4c563985209c159f3ecc7d9f09d3914de0` (the Vizing Pad of off-target Taiko and Blast) is likewise a non-proxy on Ethereum and Arbitrum. The BNB Pad `0x5d77b0c9855f44a8fbef34e670e243e988682a82` is not in the Vizing list. Key on `(chainId, address)` from §3–§8.
21. **EIP-7702 makers.** On Arbitrum the current makers `0x3bdb03ad7363152dfbc185ee23ebc93f0cf93fd1` and `0xacc517ea627ceb71cf25e002adaa9761623837b9` (and on Polygon the deprecated Bridge 1) return a 23-byte delegation designator from `eth_getCode`. A rule "code size > 0 means contract" misclassifies them; test for the `0xef0100` prefix.
22. **Measured idle, not proven dead.** In the pinned window all Orbiter paths were idle on all eight chains (§14). The makers' last outgoing transactions on Blockscout are 2026-08-21 to 2026-08-24 (ETH maker) and 2026-09-07 (USDC maker); the Aggregator's last Ethereum `BridgeExecuted` in Blockscout's list is at block 25818544 and Base `SwapExecuted` continued to block 50741101. Keep the rules: an idle maker can still receive stolen funds.
23. **Robinhood Chain (4663) is not supported.** No Orbiter address has code or a nonce there, and no official list names it (§10).

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- OrbiterXRouter native-path event (2-arg; NOT the ERC-20 Transfer)
TOPIC_ORBITER_TRANSFER        = '\x69ca02dd4edd7bf0a4abb9ed3b7af3f14778db5d61921c7dc7cd545266326de2'
-- underlying ERC-20 Transfer (the only log on the token path)
TOPIC_ERC20_TRANSFER          = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
-- OPool / OZ Ownable
TOPIC_OWNERSHIP_TRANSFERRED   = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- OPool source and destination legs (2026-09-29)
TOPIC_OPOOL_INBOX             = '\x2b949f65b3c31db2d422b7946dd04ba24c90ce95fe272b92dfd6b3a89742f658'   -- second generation
TOPIC_OPOOL_V1_INBOX          = '\xd617ac92b22579a90e8584a9f590f1e0b8d58ccc04fac6c3b4f9c41bbaa403bc'   -- first generation
TOPIC_OPOOL_OUTBOX            = '\x94a52be301a8d5e17bb003f96e429ff5b1c6e1838e0e8adf2b00dcab2d726d41'   -- both generations
-- Aggregator
TOPIC_AGG_BRIDGE_EXECUTED     = '\x783c31b20881b105b9b6e1bb8515e9e5816b2dbd62ba77aea928f463f12c2629'
TOPIC_AGG_SWAP_EXECUTED       = '\xe256398f708e8937c16a21cadd2cc58b7766662cdf76b3dfcf1e3eb3dc6cbd16'
TOPIC_AGG_COMMISSION          = '\x6c4932eb246c92f633ab70f9aadf3a6e79f40f4189b15be420b418205f7a7760'
TOPIC_AGG_EXECUTOR_UPDATED    = '\x0ef3c7eb9dbcf33ddf032f4cce366a07eda85eed03e3172e4a90c4cc16d57886'
TOPIC_AGG_WETH_UPDATED        = '\xec9fc77409b3224e46d50b2e92ab7ae0b43f0cb85d9743888276f56d73ed6b51'
TOPIC_AGG_MAX_COMMISSION      = '\xe2d55444a35ed24928e620ac5be0c7f11f17b38d1a7d746fb4327b081d3fd0af'
TOPIC_OZ_PAUSED               = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_OZ_UNPAUSED             = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_UPGRADED                = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED           = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
-- VizingPad
TOPIC_VIZING_LAUNCH           = '\xef6cc763bf0623d44a08595d2d459bb3b0c6a31123b132d8b33b57a377406546'
TOPIC_VIZING_LAUNCH_MULTI     = '\x54eb62a77fb8b5bfecbcaf246702c30b71c610898d475629b345bebfa5c85598'
TOPIC_VIZING_LANDING          = '\xab71ef78f87843dcbe693ff9d486051b58c4a8a04a0c3c56380a67979c218e4b'
TOPIC_VIZING_ENGINE_STATE     = '\x9dba95668a3b2897545e9f8cf74f368af9957cee5aaf19b9b10e7ec9cced0ab3'
TOPIC_VIZING_PAYMENT_SYSTEM   = '\xc42198387755d1905bd3c5b3ed34925a52f21b418fa2f083c6f95932bb7615df'
TOPIC_VIZING_WITHDRAW_REQUEST = '\x17040713250ec5f668a1c39e7939900e78558350dbaff0ebef34268dfa8ea4ac'

-- ===== Selectors — OrbiterXRouter (V3) =====
SEL_TRANSFER                  = '\x29723511'   -- transfer(address,bytes)  [shared with OBSource V1]
SEL_TRANSFERS                 = '\x52346412'   -- transfers(address[],uint256[])
SEL_TRANSFER_TOKEN            = '\xf9c028ec'   -- transferToken(address,address,uint256,bytes)
SEL_TRANSFER_TOKENS           = '\xd54cefc1'   -- transferTokens(address,address[],uint256[])
-- OBSource (legacy V1)
SEL_OBSOURCE_TRANSFER_ERC20   = '\x46f506ad'   -- transferERC20(address,address,uint256,bytes)
-- OPool
SEL_OPOOL_OUTBOX              = '\xc86238d3'   -- outbox(address,address,uint256,bytes)
SEL_OPOOL_OUTBOX_BATCH        = '\x809bb9cd'   -- outboxBatch(address,address[],uint256[],bytes[])
SEL_OPOOL_WITHDRAW            = '\xf3fef3a3'   -- withdraw(address,uint256)
SEL_OPOOL_SET_MAKER_LIST      = '\xb22b6094'   -- setMakerList(address[],bool[])
SEL_OPOOL_SET_MANAGER_LIST    = '\x0a7bf733'   -- setManagerList(address[],address[])
SEL_OPOOL_SET_TOKEN_RECEIVER  = '\xc21b47fb'   -- setTokenReceiver(address[],address[])
SEL_OWNER                     = '\x8da5cb5b'   -- owner()
SEL_TRANSFER_OWNERSHIP        = '\xf2fde38b'   -- transferOwnership(address)
SEL_OPOOL_V1_INBOX            = '\x884ae7d4'   -- inbox(address,address,uint256,bytes)  [first generation]
SEL_OPOOL_INBOX               = '\xf23b971c'   -- inbox(address,address,uint256,address,uint256,bytes)  [second generation]
-- Aggregator
SEL_AGG_EXECUTE_BRIDGE        = '\x5a2c71cd'   -- executeBridge((address,address,uint256,bytes,bool,address,uint256))
SEL_AGG_EXECUTE_SWAP          = '\x1725dc9b'   -- executeSwap((...9 fields...),(address,uint256,bytes)[])
SEL_AGG_PAUSE                 = '\x8456cb59'   -- pause()
SEL_AGG_UNPAUSE               = '\x3f4ba83a'   -- unpause()
SEL_AGG_SET_EXECUTOR          = '\x1c3c0ea8'   -- setExecutor(address)
SEL_AGG_WITHDRAW_TOKEN        = '\x01e33667'   -- withdrawToken(address,address,uint256)
SEL_AGG_SET_MAX_COMMISSION    = '\xb78b5e41'   -- setMaxCommissionRate(uint256)
SEL_AGG_SET_WETH              = '\x5b769f3c'   -- setWETH(address)
-- VizingPad
SEL_VIZING_LAUNCH             = '\x209afe56'   -- Launch(uint64,uint64,address,address,uint256,uint64,bytes,bytes)
SEL_VIZING_LAUNCH_MULTI       = '\xb14280ea'   -- launchMultiChain((uint64,uint64,address,address,uint256[],uint64[],bytes[],bytes[]))
SEL_VIZING_LANDING            = '\xd443a1f2'   -- Landing((landingParams)[],bytes[][])
SEL_VIZING_LANDING_GAS        = '\xc0490913'   -- LandingSpecifiedGas((landingParams)[],uint24,bytes[][])
SEL_UPGRADE_TO_AND_CALL       = '\x4f1ef286'   -- upgradeToAndCall(address,bytes)

-- ===== Proxy slots (routers and OPools read 0x0 -> NOT proxies; Aggregator and VizingPad are proxies) =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT            = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses — OrbiterXRouter (V3) per chain =====
ETH_ROUTER_V3                 = '\xc741900276cd598060b0fe6594fbe977392928f4'
ARB_ROUTER_V3                 = '\x6a065083886ec63d274b8e1fe19ae2ddf498bfdd'
OP_ROUTER_V3                  = '\x3191f40de6991b1bb1f61b7cec43d62bb337786b'
POLY_ROUTER_V3                = '\x653f25dc641544675338cb47057f8ea530c69b78'
BNB_ROUTER_V3                 = '\x13e46b2a3f8512ed4682a8fb8b560589fe3c2172'   -- shared with Base
BASE_ROUTER_V3                = '\x13e46b2a3f8512ed4682a8fb8b560589fe3c2172'   -- shared with BNB
-- AVAX: no router (0x)
-- RH (Robinhood Chain 4663): no Orbiter contract, no maker activity

-- ===== Addresses — OPool (ARB + BNB only) =====
ARB_OPOOL                     = '\x6285a466a98f513e1f6be29acad27d173d3b3c59'
BNB_OPOOL                     = '\x6285a466a98f513e1f6be29acad27d173d3b3c59'
OPOOL_OWNER_EOA               = '\x09053d505447191060b0e0720a8b255a00aaedd8'   -- owner of both OPool generations

-- ===== Addresses — Opool second generation (same address on 5 chains) =====
ETH_OPOOL_V2                  = '\x68b5a1c02dea0958388eee5361f021018bd8dbe7'
BASE_OPOOL_V2                 = '\x68b5a1c02dea0958388eee5361f021018bd8dbe7'
ARB_OPOOL_V2                  = '\x68b5a1c02dea0958388eee5361f021018bd8dbe7'
OP_OPOOL_V2                   = '\x68b5a1c02dea0958388eee5361f021018bd8dbe7'
BNB_OPOOL_V2                  = '\x68b5a1c02dea0958388eee5361f021018bd8dbe7'

-- ===== Addresses — Aggregator proxy (same address on 7 chains; AVAX unlisted) =====
ETH_AGGREGATOR                = '\xe530d28960d48708ccf3e62aa7b42a80bc427aef'
BASE_AGGREGATOR               = '\xe530d28960d48708ccf3e62aa7b42a80bc427aef'
ARB_AGGREGATOR                = '\xe530d28960d48708ccf3e62aa7b42a80bc427aef'
OP_AGGREGATOR                 = '\xe530d28960d48708ccf3e62aa7b42a80bc427aef'
POLY_AGGREGATOR               = '\xe530d28960d48708ccf3e62aa7b42a80bc427aef'
BNB_AGGREGATOR                = '\xe530d28960d48708ccf3e62aa7b42a80bc427aef'
AVAX_AGGREGATOR               = '\xe530d28960d48708ccf3e62aa7b42a80bc427aef'
ETH_AGGREGATOR_IMPL           = '\xcfb2a37258ca53e002fbc830afee30d9642191e1'   -- also Base
ARB_AGGREGATOR_IMPL           = '\x513570657eb3f4ff1935c6f93f552a1cee44a1ed'
OP_AGGREGATOR_IMPL            = '\xc4653436e617e4e62738972fcf97ead7d8edd8bc'   -- also BNB
POLY_AGGREGATOR_IMPL          = '\x61ec5096bee792b3f24b27cf663028ffc8b8ae7e'   -- also Avalanche
ETH_AGG_PROXY_ADMIN           = '\x606da564f6a9cc98fcb08e49414b30d3ad9e839d'   -- same ProxyAdmin on all 7 chains
AGG_OWNER_EOA                 = '\xdd08e0aaaa2e063dafb2df2dee19b5b0dd220ff6'   -- owns the Aggregator and its ProxyAdmin
ETH_AGG_EXECUTOR              = '\xce4b0e43abafb8cef6b805696d6e3ecab7e6f8e8'   -- also Base
ARB_AGG_EXECUTOR              = '\xdb09916571bb6aa6625444f1461a3faa848052bd'
OP_AGG_EXECUTOR               = '\xbe3f1b3ec613197a421db6cb619059c20e13fc30'   -- also BNB
POLY_AGG_EXECUTOR             = '\xd4910d28e5a43a06ceb771f708a9e92a9ba7a286'   -- also Avalanche

-- ===== Addresses — VizingPad (UUPS proxies) =====
ETH_VIZING_PAD                = '\x5d77b0c9855f44a8fbef34e670e243e988682a82'
BASE_VIZING_PAD               = '\x5d77b0c9855f44a8fbef34e670e243e988682a82'
BNB_VIZING_PAD                = '\x5d77b0c9855f44a8fbef34e670e243e988682a82'   -- not in the Vizing list
ARB_VIZING_PAD                = '\xd725bc299a232201984fecb4ff106d84e894193f'
OP_VIZING_PAD                 = '\x523d8b6893d2d0ce2b48e7964432ce19a2c641f2'
ETH_VIZING_PAD_IMPL           = '\x248dd200e77d59f582c5a2bd39b716211996fed4'   -- also Base, ARB, OP
BNB_VIZING_PAD_IMPL           = '\xa366ea26eb8f8f95d4e669b091b65f08a375012c'
VIZING_PAD_ADMIN_EOA          = '\xaebfe1ec47002d6b131060acfa969479aa37f611'   -- DEFAULT_ADMIN_ROLE (Base, ETH)
VIZING_RELAYER_EOA            = '\x5f00d70c1715dcbe40df52c784745bd0a6987768'   -- sender of the sampled Landing calls

-- ===== Maker EOAs — current official list (2026-09-29), reused across chains =====
MAKER_ETH_EOA                 = '\x3bdb03ad7363152dfbc185ee23ebc93f0cf93fd1'   -- ETH maker (EIP-7702 designator on ARB)
MAKER_USDC_EOA                = '\xacc517ea627ceb71cf25e002adaa9761623837b9'   -- = Bridge 4 (EIP-7702 designator on ARB)
MAKER_USDT_EOA                = '\x9c6750d463ad17deec97a630af766f0a78f95127'   -- = Bridge 5
MAKER_095D2918_EOA            = '\x095d2918b03b2e86d68551dcf11302121fb626c9'
MAKER_1C84DAA1_EOA            = '\x1c84daa159cf68667a54beb412cdb8b2c193fb32'
MAKER_AB0C8FBE_EOA            = '\xab0c8fbec583f20c97f9fda6a2af647b94c8e54d'
MAKER_OPOOL_EOA               = '\x732efacd14b0355999aebb133585787921aba3a9'   -- calls OPool outbox, takes the inbox fee
MAKER_34723B92_EOA            = '\x34723b92ae9708ba33843120a86035d049da7dfa'
MAKER_ALL_TOKEN_EOA           = '\xed01d58fe6433a5fe69720a0aa0ab1d1fdb15212'

-- ===== Maker EOAs ("Orbiter Finance: Bridge N") — first listed here =====
MAKER_BRIDGE_1_EOA            = '\x80c67432656d59144ceff962e8faf8926599bcf8'   -- deprecated in the official list
MAKER_BRIDGE_2_EOA            = '\xe4edb277e41dc89ab076a1f049f4a3efa700bce8'   -- deprecated in the official list
MAKER_BRIDGE_3_EOA            = '\x41d3d33156ae7c62c094aae2995003ae63f587b3'   -- deprecated in the official list
MAKER_BRIDGE_4_EOA            = '\xacc517ea627ceb71cf25e002adaa9761623837b9'   -- current (USDC)
MAKER_BRIDGE_5_EOA            = '\x9c6750d463ad17deec97a630af766f0a78f95127'   -- current (USDT)

-- ===== Deployers =====
ROUTER_DEPLOYER_EOA           = '\x8a700fdb6121a57c59736041d9aa21dfd8820660'
AGG_DEPLOYER_EOA              = '\xbc50d0e58e90c579f1320ccea978d1e46f5b6163'   -- deployed the Ethereum Aggregator proxy
```

---

## 14. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors** recomputed locally as `keccak256(canonical signature)` (and `[0:4]` for selectors) and cross-checked against the **Sourcify-verified `OrbiterXRouter` ABI** (Ethereum mainnet, exact runtime match, solc 0.8.19+commit.7dd6d404) and the four dispatch selectors observed in the live router bytecode (PUSH4 scan): `0x29723511`, `0x52346412`, `0xf9c028ec`, `0xd54cefc1`. OPool selectors recomputed locally and cross-checked against the public 4-byte signature database (`outbox`, `outboxBatch`, `withdraw`, `setMakerList`, `setManagerList`, `setTokenReceiver`) and the live OPool bytecode.
- **OrbiterXRouter source** read from Sourcify v2 (`/v2/contract/1/0xc741900276cd598060b0fe6594fbe977392928f4928f4?fields=abi,sources`): confirms `event Transfer(address indexed to, uint256 amount)`, the four `payable nonReentrant` functions, the `bool locked` guard, and that the native paths emit while the token paths do not. `OBSource.sol` (legacy router) read from the same source bundle.
- **Addresses** parsed from the official `docs.orbiter.finance` Smart Contract mainnet table and existence-checked via `eth_getCode` on each chain's publicnode RPC. Router runtime bytecode is byte-identical across all six EVM chains (sha256 `27f13214…`, 3183 bytes). OPool present only on Arbitrum + BNB (5454 bytes); absent (`0x`) on ETH/OP/Polygon/Base/Avax. **Every** Orbiter address returns `0x` on Avalanche C-Chain.
- **Proxy classification** by reading the EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` live on each router and on OPool — all return `0x0`, confirming **non-proxy / immutable**. The router additionally has no `owner()` selector in bytecode (no Ownable). OPool `owner()` read live via `eth_call(0x8da5cb5b)` = `0x09053d505447191060b0e0720a8b255a00aaedd8` on both ARB and BNB.
- **Maker EOAs** confirmed as plain EOAs (`eth_getCode` = `0x` on ETH/OP/ARB) and matched to the explorer "Orbiter Finance: Bridge N" labels.

Additions of 2026-09-29 / 2026-10-01:

- **Aggregator:** source verified on Blockscout (`Aggregator`, solc 0.8.28; `IAggregatorEvents`, `contracts/library/Types.sol`); every topic and selector of §1.4/§2.5 recomputed with `keccak256`. Proxy, implementation, ProxyAdmin, `owner()`, `executor()` and `paused()` read live on the seven chains of §10.
- **Opool (second generation):** Sourcify-verified source; **OPool (first generation)** `Inbox`/`inbox` decoded from Arbitrum calldata and logs (parameter names inferred). **VizingPad:** ABI from `Orbiter-Vizing/vizing_npm_package`; topics and selectors confirmed in the implementation bytecode (PUSH32/PUSH4 scan); proxies and `hasRole` read live.
- **Makers:** the current list from the official maker page (2026-09-29); `eth_getCode` and nonces read on all eight chains (EIP-7702 designators found on Arbitrum and Polygon).
- **Measured activity** (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):
  - Aggregator `BridgeExecuted`, the three VizingPad launch/landing topics: 0 logs from any emitter on all eight chains.
  - Router `Transfer(address,uint256)`: 0 logs from an Orbiter router; 2 (Ethereum) and 3 (Polygon) from unrelated contracts (§12, item 16).
  - Opool (second generation) `Inbox` / `Outbox` at `0x68b5a1c02dea0958388eee5361f021018bd8dbe7`: Ethereum 0/0, Base 0/0, Arbitrum 0/0, Optimism 0/0, BNB 0/0.
  - OPool (first generation) `Inbox` / `Outbox` at `0x6285a466a98f513e1f6be29acad27d173d3b3c59`: Arbitrum 0/0, BNB 0/0.
  - Maker EOA transfers were not counted (plain EOA transfers carry no Orbiter topic); see §12, item 22 for the makers' last activity.
- **Samples** (read with `eth_getTransactionReceipt`):
  - Aggregator bridge, Ethereum `0xc2cee23d3875fef80c4e2a0bb3cd9b3bc97376efb409364db3e10ca62c46afa0` (block 25,818,544): `executeBridge` (`0x5a2c71cd`) with 0.001638 ETH in `msg.value`; the only log is `BridgeExecuted` with `sender` = the user and `recipient` = the ETH maker `0x3bdb03ad7363152dfbc185ee23ebc93f0cf93fd1`; the native payment to the maker has no log (§12, item 15).
  - VizingPad landing, Ethereum `0xb807d066a9ec0fdd9e1d3787be69273fd0afe566a64142f79a5a23945789cd4f` (block 21,434,578): relayer `0x5f00d70c1715dcbe40df52c784745bd0a6987768` calls `Landing` (`0xd443a1f2`) with value; the destination app logs, then `SuccessfulLanding`. Base landing `0x59cac9b9edeb8bf2fa7cc1c3f3ef6cb563ec7d29b1180e261e3332c4652774c9` (block 33,911,430).
  - First-generation OPool `inbox`, Arbitrum `0xb433831ad9c4448dcf830b2de8a7a40228ea49d878565bc8b796d49c359c45da` (§2.3).
- **Robinhood Chain:** §10 lists the addresses and makers read on 2026-09-29 (no code, nonce 0).
- Sources added: [Orbiter Aggregator docs](https://docs.orbiter.finance/developer/smart-contract) · [Sourcify `Opool`](https://sourcify.dev/) · [`Orbiter-Vizing/vizing_npm_package`](https://github.com/Orbiter-Vizing/vizing_npm_package) · Blockscout explorers for Ethereum, Base and Arbitrum.

Authoritative sources:
- Official docs — [Smart Contract addresses](https://docs.orbiter.finance/developer/smart-contract) · [Orbiter Router](https://docs.orbiter.finance/developer/smart-contract/orbiter-router) · [Bridge Protocol](https://docs.orbiter.finance/welcome/bridge-protocol)
- Verified source — Sourcify `OrbiterXRouter` (chain 1, `0xc741900276cd598060b0fe6594fbe977392928f4`); `Orbiter-Finance/OB_ReturnCabin` repo (`contracts/OBSource.sol`).
- Explorers — [Etherscan router](https://etherscan.io/address/0xc741900276cd598060b0fe6594fbe977392928f4) · [Arbiscan OPool](https://arbiscan.io/address/0x6285a466a98f513e1f6be29acad27d173d3b3c59) · [Etherscan "Orbiter Finance: Bridge"](https://etherscan.io/address/0x80c67432656d59144ceff962e8faf8926599bcf8)
