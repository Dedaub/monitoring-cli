# Relay (relay.link) — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the official repositories `relayprotocol/relay-settlement` (depository source and `packages/networks`), `relayprotocol/relay-depository` (archived; its `addresses.prod.json` lists Robinhood Chain), `relayprotocol/relay-periphery` (router, approval proxy, receiver and their `deployments/*/addresses.json`), the Relay Chains API (`https://api.relay.link/chains`) and docs.relay.link. Every topic0 and selector was recomputed as `keccak256(signature)` and matched against live logs or deployed bytecode. Every address was existence-checked with `eth_getCode`.
**Scope:** the EVM contracts of Relay: the RelayDepository escrow of the settlement protocol (production, staging and dev instances), the periphery that builds deposits and fills (RelayRouter and RelayApprovalProxy, generations v2, v2.1, v3.0 and v3.1), the RelayReceiver native forwarder, the public solver addresses, and the ids that link a deposit to its fill. All eight target chains have the production Depository and the v3.0 periphery at the same addresses. Robinhood Chain (4663) has no RelayReceiver. Topics and selectors are chain-agnostic; addresses are network-specific.

Relay is an intent bridge. The user deposits on the origin chain. A solver fills the request on the destination chain with its own funds. The Oracle then attests the deposit and the fill, and the Hub on Relay Chain (chain id 537713, outside the eight chains) credits the solver. Later the solver withdraws from the origin Depository with a CallRequest that the Allocator (MPC signer on Aurora) signs.

Three facts to know before indexing:

1. **One production Depository, `0x4cD00E387622C35bDDB9b4c962C136462338BC31`, on all eight chains.** It was deployed with CREATE2 through the factory `0x4e59b44847b379578588920ca78fbf26c0b4956c` (salt 1). It is not a proxy and it cannot be upgraded. Its runtime code is 8,628 bytes on every chain, but the code hash differs per chain, because the EIP-712 domain (chain id and address) is cached in immutables.
2. **There is no payout event.** A fill is any action of the solver on the destination: a native transfer, an ERC-20 transfer, or a RelayRouter multicall. The deposit `id` (Relay calls it the `orderId`) is on chain only on the origin. The link from a deposit to its fill is off chain, in the Relay API.
3. **`RelayCallExecuted` is the escrow release to the solver, not a payout to the user.** Its `id` is the EIP-712 struct hash of the CallRequest, not a deposit id. One withdrawal can release the funds of many deposits.

---

## 0. Contract families & versions

| Contract | Address (same on every chain where present) | Chains | Role | Upgradeable? |
|----------|---------------------------------------------|--------|------|--------------|
| **RelayDepository** (production) | `0x4cD00E387622C35bDDB9b4c962C136462338BC31` | all 8 | Escrow. `depositNative` / `depositErc20` take user funds; `execute` releases funds with an allocator signature. | No. Plain contract with solady `Ownable`; the owner can only change the allocator and the ownership. |
| RelayDepository (staging) | `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` | all 8 | The `stag` depository of `relay-settlement/packages/networks`. Same 8,628-byte code, other owner (`0x71d8be89d9f2339f0fe9cba39496c6c9cbff9da6`) and allocator (`0x49103cbe01afa376ed2de1fc5e59c19e0bc53e71`). Emits the same events. | No |
| RelayDepository (dev) | `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299` | see §11 | The `dev` depository of the same config (Ethereum, Base, Arbitrum, Optimism, Polygon only). | No |
| **RelayRouter v3.0** | `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | all 8 | Stateless multicall router. The Chains API names it `erc20Router`. Emits `FundsMovement`, `SolverCallExecuted`, `SolverNativeTransfer`. | No |
| **RelayApprovalProxy v3.0** | `0xccc88a9d1b4ed6b0eaba998850414b24f1c315be` | all 8 | Pulls the user's tokens (approval, ERC-2612, Permit2 or ERC-3009) into the router, then calls `multicall`. The Chains API names it `approvalProxy`. | No. `owner()` can `withdraw` stranded tokens. |
| RelayRouter v3.1 | `0xe6b730e58088884704cdf11cbe95c224d4d34154` | all 8 | Newest router in `relay-periphery` (`VERSION()` = "3.1", recorded 2026-08-28). Not yet in the Chains API. | No |
| RelayApprovalProxy v3.1 | `0x5a0fa369d634f49c76b08dc6c299800c1a2af977` | all 8 | Newest approval proxy. Adds EIP-712 multicall authorization; code hash differs per chain. | No |
| RelayRouter v2.1 / RelayApprovalProxy v2.1 | `0x3ec130b627944cad9b2750300ecb0a695da522b6` / `0x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7` | see §11 | Legacy generation (2025-10). The router emits `SolverCallExecuted` and `SolverNativeTransfer` only. | No |
| RelayRouter v2 / ApprovalProxy v2 | `0xf5042e6ffac5a625d4e7848e0b01373d8eb9e222` / `0xbbbfd134e9b44bfb5123898ba36b01de7ab93d98` | see §11 | Legacy generation (2025-06). | No |
| v1 periphery (historical) | ERC20Router `0xE0B062D028236FA09Fe33dB8019FFEEEe6bF79Ed`, ApprovalProxy `0xfD06C0018318BF78705ccFf2b961Ef8eBC0bacA0`, RelayReceiver v1 `0xa06e1351E2fD2D45b5D35633ca7eCF328684a109` | 7 (not Robinhood) | The expected addresses in the old `relay-periphery` deployer script (`script/BaseDeployer.s.sol` at commit `1957475c95`). Kept for older incidents; their events are not covered here. | No |
| **RelayReceiver** | `0xa5f565650890fba1824ee0f21ebbbf660a179934` | 7 (not Robinhood) | Native-currency forwarder. It sends `msg.value` at once to the immutable `SOLVER` (`0xf70da97812cb96acdf810712aa562db8dfa3dbef`, read from the bytecode) and emits the calldata. It is an origin-side deposit path to the solver, with no escrow. | No |
| Multicaller / OnlyOwnerMulticaller | `0x0000000000002bdbf1bf3279983603ec279cc6df` / `0xb90ed4c123843cbfd66b11411ee7694ef37e6e72` | see §11 | Helper contracts that the Chains API lists (empty for Robinhood Chain). No Relay event; not covered further. | No |
| **Solver** (EOA) | `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | all 8 | The only address in the Chains API `solverAddresses` of every target chain. It fills, withdraws (`execute`) and receives RelayReceiver forwards. | — |

**Settlement contracts outside the eight chains** (from docs.relay.link and `relay-settlement/packages/networks`; not checked on chain here): Hub `0xDDD361727C22A01EB137880678A20b0BEaE69318` and Oracle `0xd4b9fdB83C723c096d7fBE72da252aa23f1387aa` on Relay Chain (537713); Allocator `0x7EdA04920F22ba6A2b9f2573fd9a6F6F1946Ff9f` and Security Council multisig `0xb538ee6515F9d16eBD0BACD0503733815c9b070c` on Aurora.

**RelayGatewayDepository** (Circle Gateway-backed, in `relay-settlement`): the source exists, but no deployment address is in the Chains API, the network config or the deployment files. No deployment was found. §1.2 lists its extra events.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 RelayDepository (production, staging and dev — the same bytecode)

No parameter is indexed. Filter on topic0 and the emitter, then decode the data.

| topic0 | Event |
|--------|-------|
| `0x8032066556caf3967d8fec4ad22a2d9e1e9576556b2903a0fcd5b1fd201e3477` | `RelayNativeDeposit(address from, uint256 amount, bytes32 id)` — **source leg, native.** `amount` = `msg.value`; `from` = the credited depositor (the `depositor` argument, or `msg.sender` when it is zero); `id` = the orderId. |
| `0x49fed1d0b752ce30eee63c7a81133f3363b532fec5d4d7dd1ccfd005de4555e1` | `RelayErc20Deposit(address from, address token, uint256 amount, bytes32 id)` — **source leg, ERC-20.** The same transaction has an ERC-20 `Transfer` from `msg.sender` (often the RelayRouter) to the Depository. |
| `0x4be109453ef7e895dc7215c929fff9b76b51483d56a4d04548b4866e9aa7c5ea` | `RelayCallExecuted(bytes32 id, (address to, bytes data, uint256 value, bool allowFailure) call)` — **escrow pays the solver.** One log per successful call of an allocator-signed CallRequest. `id` = EIP-712 struct hash of the CallRequest. For an ERC-20 release, `call.to` is the token and `call.data` is `transfer(solver, amount)`; for a native release, `call.to` is the recipient and `call.value` the amount. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed oldOwner, address indexed newOwner)` — admin (solady `Ownable`; same topic0 as OpenZeppelin). |
| `0xdbf36a107da19e49527a7176a1babf963b4b0ff8cde35ee35d6cd8f1f9ac7e1d` | `OwnershipHandoverRequested(address indexed pendingOwner)` — admin, status only. |
| `0xfa7b8eab7da67f412cc9575ed43464468f9bfbae89d1675917346ca6d8fe3c92` | `OwnershipHandoverCanceled(address indexed pendingOwner)` — admin, status only. |

`setAllocator(address)` emits **no event**. See §13.

### 1.2 RelayGatewayDepository (source only; no deployment found)

It emits `RelayErc20Deposit` and `RelayCallExecuted` with the topic0 values of §1.1, plus:

| topic0 | Event |
|--------|-------|
| `0x4ba112082ec7c5f4560417c7baff6813dfd8babd0f46e63ce2eb897f2d60e90d` | `UsdcInitialized(address usdc)` — admin, status only. |
| `0xeb68b6c7ff0e24f32ff5050ed7cf86fbe6abbdb204f11f97377013888cd5be58` | `DepositsEnabledSet(bool enabled)` — admin, status only (pause switch for deposits). |

### 1.3 RelayRouter and RelayApprovalProxy (v3.0 and v3.1)

| topic0 | Event |
|--------|-------|
| `0xafbab204e8271965231d37baed9b1abca8725b7409c70314455f68bc89142b91` | `FundsMovement(address from, address to, address currency, uint256 amount, bytes metadata)` — a value movement that the periphery performs. The ApprovalProxy emits it when it pulls user tokens into the router; the router emits it when it sends value out (`cleanupErc20s`, `cleanupNative`, `cleanupErc20sViaCall`, `cleanupNativeViaCall`) and when `multicall` receives `msg.value`. `currency` = zero for native. `metadata` is caller-supplied and opaque (§13). |
| `0x93485dcd31a905e3ffd7b012abe3438fa8fa77f98ddc9f50e879d3fa7ccdc324` | `SolverCallExecuted(address to, bytes data, uint256 amount)` — RelayRouter only (also v2 and v2.1): one log per successful call inside `multicall`. Status of the call; the value moves in the call itself. |
| `0xd35467972d1fda5b63c735f59d3974fa51785a41a92aa3ed1b70832836f8dba6` | `SolverNativeTransfer(address to, uint256 amount)` — RelayRouter only (also v2 and v2.1): native currency leaves the router (`cleanupNative`), or the router receives native currency (`to` = the router). |
| `0x7aed1d3e8155a07ccf395e44ea3109a0e2d6c9b29bbbe9f142d9790596f4dc80` | `RouterUpdated(address newRouter)` — ApprovalProxy v2.1 only; admin. |
| `0xaecfd826d6b270962e6ff81f57b75e8527073ef343cbb38af801b8a972c78461` | `Permit2Updated(address newPermit2)` — ApprovalProxy v2.1 only; admin. |

The ApprovalProxy also emits the solady `OwnershipTransferred` / `OwnershipHandover*` events of §1.1.

### 1.4 RelayReceiver

| topic0 | Event |
|--------|-------|
| `0x936c2ca3b35d2d0b24057b0675c459e4515f48fe132d138e213ae59ffab7f53e` | `FundsForwardedWithData(bytes data)` — a native deposit forwarded to the solver. `data` = the calldata of the call (the request id). No amount in the event: the value is the `msg.value` of the call and leaves the receiver in the same call. |

### 1.5 Value row used with these events

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` — ERC-20. Deposits: into the Depository. Withdrawals: from the Depository to the solver. Native deposits and releases have no `Transfer` row. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 RelayDepository

All selectors below are present in the deployed bytecode (PUSH4 in the dispatcher) on Ethereum.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x49290c1c` | `depositNative(address depositor, bytes32 id)` | payable. `depositor` = zero credits `msg.sender`. Emits `RelayNativeDeposit`. |
| `0xe8017952` | `depositErc20(address depositor, address token, uint256 amount, bytes32 id)` | `transferFrom(msg.sender → Depository)`, then emits `RelayErc20Deposit`. |
| `0x5a1ee3ac` | `depositErc20(address depositor, address token, bytes32 id)` | Uses the full allowance of `msg.sender` as the amount. Routers call this form. |
| `0x2d9fb478` | `execute(((address to, bytes data, uint256 value, bool allowFailure)[] calls, uint256 nonce, uint256 expiration) request, bytes signature)` | **Escrow release.** Checks expiration, the allocator signature (ECDSA or ERC-1271) and reuse, marks `callRequests[structHash]`, runs the calls. Emits `RelayCallExecuted` per successful call. Anyone can submit; in practice the solver does. |
| `0xbf83f2a2` | `setAllocator(address _allocator)` | owner-only. **No event.** |
| `0xaa5dcecc` | `allocator()` | view → `address`. |
| `0xd52bfcc8` | `callRequests(bytes32)` | view → `bool` (the struct hash was executed). |
| `0x8da5cb5b` | `owner()` | view → `address`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | owner-only; emits `OwnershipTransferred`. |
| `0x715018a6` | `renounceOwnership()` | owner-only. |
| `0x25692962` | `requestOwnershipHandover()` | solady two-step handover; emits `OwnershipHandoverRequested`. |
| `0xf04e283e` | `completeOwnershipHandover(address pendingOwner)` | owner-only. |
| `0x54d1f13d` | `cancelOwnershipHandover()` | emits `OwnershipHandoverCanceled`. |
| `0xcf5905d7` | `_CALL_TYPEHASH()` | view → `keccak256("Call(address to,bytes data,uint256 value,bool allowFailure)")`. |
| `0xeae335b3` | `_CALL_REQUEST_TYPEHASH()` | view → the CallRequest typehash. |
| `0x84b0196e` | `eip712Domain()` | view. Name `RelayDepository`, version `1`, chain id, verifying contract (read live). |

### 2.2 RelayRouter (v3.0 `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` and v3.1 `0xe6b730e58088884704cdf11cbe95c224d4d34154`; v2 and v2.1 share `multicall` and the cleanup functions)

Tuple `Call3Value = (address target, bool allowFailure, uint256 value, bytes callData)`.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xcd6e13f7` | `multicall((address target, bool allowFailure, uint256 value, bytes callData)[] calls, address refundTo, address nftRecipient, bytes metadata)` | payable. Runs the calls with the router as `msg.sender`; refunds leftover native to `refundTo`. Emits `FundsMovement` for `msg.value`, `SolverCallExecuted` per call. |
| `0x9bb43718` | `cleanupErc20s(address[] tokens, address[] recipients, uint256[] amounts, bytes metadata)` | Sends router ERC-20 balances out (amount 0 = full balance). Emits `FundsMovement`. **A fill that ends here pays the recipient.** |
| `0x73b7bb2f` | `cleanupErc20sViaCall(address[] tokens, address[] tos, bytes[] datas, uint256[] amounts)` | Approves `to` and calls it (for example `depositErc20` on the Depository). Emits `FundsMovement` with empty metadata. |
| `0xa6bd8c96` | `cleanupNative(uint256 amount, address recipient, bytes metadata)` | Sends native currency out. Emits `SolverNativeTransfer` and `FundsMovement`. |
| `0x5d1fe6a2` | `cleanupNativeViaCall(uint256 amount, address to, bytes data)` | Calls `to` with value (for example `depositNative`). Emits `FundsMovement`. |
| `0xffa1ad74` | `VERSION()` | view → `"3.1"`. v3.1 only (absent from the v3.0 bytecode). |

### 2.3 RelayApprovalProxy

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf9e4bab4` | `transferAndMulticall(address[] tokens, uint256[] amounts, (address target, bool allowFailure, uint256 value, bytes callData)[] calls, address refundTo, address nftRecipient, bytes metadata)` | v3.0 + v3.1. Pulls `tokens` from `msg.sender` into the router; emits `FundsMovement`; calls `multicall`. |
| `0xfb68c293` | `permitTransferAndMulticall((address token, address owner, uint256 value, uint256 nonce, uint256 deadline, uint8 v, bytes32 r, bytes32 s)[] permits, (address target, bool allowFailure, uint256 value, bytes callData)[] calls, address refundTo, address nftRecipient, bytes metadata)` | v3.0 only (the permit struct has a `nonce`). |
| `0xbd4967a9` | `permitTransferAndMulticall((address token, address owner, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s)[] permits, (address target, bool allowFailure, uint256 value, bytes callData)[] calls, address refundTo, address nftRecipient, bytes metadata)` | v3.1 only (no `nonce` field). |
| `0x0a2b8f36` | `permit2TransferAndMulticall(address user, ((address token, uint256 amount)[] permitted, uint256 nonce, uint256 deadline) permit, (address target, bool allowFailure, uint256 value, bytes callData)[] calls, address refundTo, address nftRecipient, bytes metadata, bytes permitSignature)` | v3.0 + v3.1. Gasless path: a relayer submits for `user`. Seen for user deposits and for solver fills. |
| `0xf80f00fb` | `permit3009TransferAndMulticall((address from, uint256 value, uint256 validAfter, uint256 validBefore, uint8 v, bytes32 r, bytes32 s)[] permits, address[] tokens, (address target, bool allowFailure, uint256 value, bytes callData)[] calls, address refundTo, address nftRecipient, bytes metadata)` | v3.0 only. |
| `0x745599f3` | `permit3009TransferAndMulticall((address from, uint256 value, uint256 validAfter, uint256 validBefore, uint8 v, bytes32 r, bytes32 s)[] permits, address[] tokens, (address target, bool allowFailure, uint256 value, bytes callData)[] calls, address refundTo, address nftRecipient, bytes metadata, bytes[] multicallSignatures)` | v3.1 only. |
| `0x51cff8d9` | `withdraw(address token)` | v3.0, owner-only rescue of stranded balances. |
| `0xf940e385` | `withdraw(address token, address recipient)` | v3.1, owner-only rescue. |

### 2.4 RelayReceiver

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xd948d468` | `forward(bytes data)` | payable. Sends `msg.value` to `SOLVER` (100,000 gas stipend) and emits `FundsForwardedWithData(data)`. The `fallback` does the same with `msg.data`. |
| `0xdd4ed837` | `makeCalls((address to, bytes data, uint256 value)[] calls)` | `SOLVER` only. Arbitrary calls from the receiver (rescue path). |

---

## 3. Addresses — Ethereum (chain ID 1)

All verified with `eth_getCode` on 2026-09-29. Relay uses the EVM chain id (1) in its API; the settlement config names the chain `ethereum`.

| Role | Address | Code / note |
|------|---------|-------------|
| **RelayDepository** (production) | `0x4cD00E387622C35bDDB9b4c962C136462338BC31` | 8,628 B. `owner()` = `0xf61a305199fa1135d76ffab3752d42f55cbd775a` (EOA), `allocator()` = `0x63c1d3e9c646184529c5694630a01c00df171b56` (EOA, nonce 0). |
| RelayDepository (staging) | `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` | 8,628 B. Owner `0x71d8be89d9f2339f0fe9cba39496c6c9cbff9da6`, allocator `0x49103cbe01afa376ed2de1fc5e59c19e0bc53e71`. |
| RelayDepository (dev) | `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299` | 8,628 B (own owner and allocator; not read). |
| **RelayRouter v3.0** | `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | 4,720 B (same hash on all eight chains). |
| **RelayApprovalProxy v3.0** | `0xccc88a9d1b4ed6b0eaba998850414b24f1c315be` | 7,746 B (same hash on all eight). `owner()` = `0x463cb782c8dd0a1887b77336dff74d60f006f56e` (EOA; the canonical owner named in `relay-periphery`). |
| RelayRouter v3.1 | `0xe6b730e58088884704cdf11cbe95c224d4d34154` | 5,373 B. |
| RelayApprovalProxy v3.1 | `0x5a0fa369d634f49c76b08dc6c299800c1a2af977` | 10,923 B (hash differs per chain). |
| RelayRouter v2.1 | `0x3ec130b627944cad9b2750300ecb0a695da522b6` | 4,153 B. |
| RelayApprovalProxy v2.1 | `0x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7` | 7,076 B. |
| RelayRouter v2 | `0xf5042e6ffac5a625d4e7848e0b01373d8eb9e222` | 8,925 B. |
| RelayApprovalProxy v2 | `0xbbbfd134e9b44bfb5123898ba36b01de7ab93d98` | 11,652 B. |
| **RelayReceiver** | `0xa5f565650890fba1824ee0f21ebbbf660a179934` | 1,102 B. `SOLVER` = `0xf70da97812cb96acdf810712aa562db8dfa3dbef`. |
| Multicaller | `0x0000000000002bdbf1bf3279983603ec279cc6df` | 697 B. |
| OnlyOwnerMulticaller | `0xb90ed4c123843cbfd66b11411ee7694ef37e6e72` | 1,357 B. |
| **Solver** (EOA) | `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | No code; nonce 4,895,029. |
| CREATE2 factory used for the deployments | `0x4e59b44847b379578588920ca78fbf26c0b4956c` | 69 B (the Arachnid deterministic deployer). |

## 4. Addresses — Base (chain ID 8453)

All verified with `eth_getCode` on 2026-09-29. Relay uses the EVM chain id (8453); the settlement config names the chain `base`. The addresses are the same literal addresses as on Ethereum.

| Role | Address | Code / note |
|------|---------|-------------|
| **RelayDepository** (production) | `0x4cD00E387622C35bDDB9b4c962C136462338BC31` | 8,628 B. Same `owner()` and `allocator()` as on Ethereum. |
| RelayDepository (staging) | `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` | 8,628 B. |
| RelayDepository (dev) | `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299` | 8,628 B. |
| **RelayRouter v3.0** | `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | 4,720 B. |
| **RelayApprovalProxy v3.0** | `0xccc88a9d1b4ed6b0eaba998850414b24f1c315be` | 7,746 B. Same `owner()` as on Ethereum. |
| RelayRouter v3.1 | `0xe6b730e58088884704cdf11cbe95c224d4d34154` | 5,373 B. |
| RelayApprovalProxy v3.1 | `0x5a0fa369d634f49c76b08dc6c299800c1a2af977` | 10,923 B. |
| RelayRouter v2.1 / RelayApprovalProxy v2.1 | `0x3ec130b627944cad9b2750300ecb0a695da522b6` / `0x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7` | 4,153 B / 7,076 B. |
| RelayRouter v2 / RelayApprovalProxy v2 | `0xf5042e6ffac5a625d4e7848e0b01373d8eb9e222` / `0xbbbfd134e9b44bfb5123898ba36b01de7ab93d98` | 8,925 B / 11,652 B. |
| **RelayReceiver** | `0xa5f565650890fba1824ee0f21ebbbf660a179934` | 1,102 B. |
| Multicaller / OnlyOwnerMulticaller | `0x0000000000002bdbf1bf3279983603ec279cc6df` / `0xb90ed4c123843cbfd66b11411ee7694ef37e6e72` | 697 B / 1,357 B. |
| **Solver** (EOA) | `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | No code; nonce 17,068,594. |

Pinned window 2026-09-28 00:00–12:00 UTC: `RelayErc20Deposit` 9,822, `RelayNativeDeposit` 6,939, `RelayCallExecuted` 767 (all at the production Depository); `FundsMovement` 29,468 (router v3.0 18,818; ApprovalProxy v3.0 10,650); `FundsForwardedWithData` 0; 3 `RelayErc20Deposit` at the staging depository.

## 5. Addresses — Arbitrum One (chain ID 42161)

All verified with `eth_getCode` on 2026-09-29. Relay uses the EVM chain id (42161); the settlement config names the chain `arbitrum`. The addresses are the same literal addresses as on Ethereum.

| Role | Address | Code / note |
|------|---------|-------------|
| **RelayDepository** (production) | `0x4cD00E387622C35bDDB9b4c962C136462338BC31` | 8,628 B. Same `owner()` and `allocator()` as on Ethereum. |
| RelayDepository (staging) | `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` | 8,628 B. |
| RelayDepository (dev) | `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299` | 8,628 B. |
| **RelayRouter v3.0** | `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | 4,720 B. |
| **RelayApprovalProxy v3.0** | `0xccc88a9d1b4ed6b0eaba998850414b24f1c315be` | 7,746 B. Same `owner()` as on Ethereum. |
| RelayRouter v3.1 | `0xe6b730e58088884704cdf11cbe95c224d4d34154` | 5,373 B. |
| RelayApprovalProxy v3.1 | `0x5a0fa369d634f49c76b08dc6c299800c1a2af977` | 10,923 B. |
| RelayRouter v2.1 / RelayApprovalProxy v2.1 | `0x3ec130b627944cad9b2750300ecb0a695da522b6` / `0x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7` | 4,153 B / 7,076 B. |
| RelayRouter v2 / RelayApprovalProxy v2 | `0xf5042e6ffac5a625d4e7848e0b01373d8eb9e222` / `0xbbbfd134e9b44bfb5123898ba36b01de7ab93d98` | 8,925 B / 11,652 B. |
| **RelayReceiver** | `0xa5f565650890fba1824ee0f21ebbbf660a179934` | 1,102 B. |
| Multicaller / OnlyOwnerMulticaller | `0x0000000000002bdbf1bf3279983603ec279cc6df` / `0xb90ed4c123843cbfd66b11411ee7694ef37e6e72` | 697 B / 1,357 B. |
| **Solver** (EOA) | `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | No code; nonce 10,892,774. |

Pinned window 2026-09-28 00:00–12:00 UTC: `RelayErc20Deposit` 1,854, `RelayNativeDeposit` 1,319, `RelayCallExecuted` 503 (all at the production Depository); `FundsMovement` 1,952 (router v3.0 1,335; ApprovalProxy v3.0 617); `FundsForwardedWithData` 0; 0 at the staging depository.

## 6. Addresses — Optimism (chain ID 10)

All verified with `eth_getCode` on 2026-09-29. Relay uses the EVM chain id (10); the settlement config names the chain `optimism`. The addresses are the same literal addresses as on Ethereum.

| Role | Address | Code / note |
|------|---------|-------------|
| **RelayDepository** (production) | `0x4cD00E387622C35bDDB9b4c962C136462338BC31` | 8,628 B. Same `owner()` and `allocator()` as on Ethereum. |
| RelayDepository (staging) | `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` | 8,628 B. |
| RelayDepository (dev) | `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299` | 8,628 B. |
| **RelayRouter v3.0** | `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | 4,720 B. |
| **RelayApprovalProxy v3.0** | `0xccc88a9d1b4ed6b0eaba998850414b24f1c315be` | 7,746 B. Same `owner()` as on Ethereum. |
| RelayRouter v3.1 | `0xe6b730e58088884704cdf11cbe95c224d4d34154` | 5,373 B. |
| RelayApprovalProxy v3.1 | `0x5a0fa369d634f49c76b08dc6c299800c1a2af977` | 10,923 B. |
| RelayRouter v2.1 / RelayApprovalProxy v2.1 | `0x3ec130b627944cad9b2750300ecb0a695da522b6` / `0x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7` | 4,153 B / 7,076 B. |
| RelayRouter v2 / RelayApprovalProxy v2 | `0xf5042e6ffac5a625d4e7848e0b01373d8eb9e222` / `0xbbbfd134e9b44bfb5123898ba36b01de7ab93d98` | 8,925 B / 11,652 B. |
| **RelayReceiver** | `0xa5f565650890fba1824ee0f21ebbbf660a179934` | 1,102 B. |
| Multicaller / OnlyOwnerMulticaller | `0x0000000000002bdbf1bf3279983603ec279cc6df` / `0xb90ed4c123843cbfd66b11411ee7694ef37e6e72` | 697 B / 1,357 B. |
| **Solver** (EOA) | `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | No code; nonce 9,972,403. |

Pinned window 2026-09-28 00:00–12:00 UTC: `RelayErc20Deposit` 181, `RelayNativeDeposit` 323, `RelayCallExecuted` 38 (all at the production Depository); `FundsMovement` 1,566 (router v3.0 1,045; ApprovalProxy v3.0 521); `FundsForwardedWithData` 0; 0 at the staging depository.

## 7. Addresses — Polygon PoS (chain ID 137)

All verified with `eth_getCode` on 2026-09-29. Relay uses the EVM chain id (137); the settlement config names the chain `polygon`. The addresses are the same literal addresses as on Ethereum.

| Role | Address | Code / note |
|------|---------|-------------|
| **RelayDepository** (production) | `0x4cD00E387622C35bDDB9b4c962C136462338BC31` | 8,628 B. Same `owner()` and `allocator()` as on Ethereum. |
| RelayDepository (staging) | `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` | 8,628 B. |
| RelayDepository (dev) | `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299` | 8,628 B. |
| **RelayRouter v3.0** | `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | 4,720 B. |
| **RelayApprovalProxy v3.0** | `0xccc88a9d1b4ed6b0eaba998850414b24f1c315be` | 7,746 B. Same `owner()` as on Ethereum. |
| RelayRouter v3.1 | `0xe6b730e58088884704cdf11cbe95c224d4d34154` | 5,373 B. |
| RelayApprovalProxy v3.1 | `0x5a0fa369d634f49c76b08dc6c299800c1a2af977` | 10,923 B. |
| RelayRouter v2.1 / RelayApprovalProxy v2.1 | `0x3ec130b627944cad9b2750300ecb0a695da522b6` / `0x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7` | 4,153 B / 7,076 B. |
| RelayRouter v2 / RelayApprovalProxy v2 | `0xf5042e6ffac5a625d4e7848e0b01373d8eb9e222` / `0xbbbfd134e9b44bfb5123898ba36b01de7ab93d98` | 8,925 B / 11,652 B. |
| **RelayReceiver** | `0xa5f565650890fba1824ee0f21ebbbf660a179934` | 1,102 B. |
| Multicaller / OnlyOwnerMulticaller | `0x0000000000002bdbf1bf3279983603ec279cc6df` / `0xb90ed4c123843cbfd66b11411ee7694ef37e6e72` | 697 B / 1,357 B. |
| **Solver** (EOA) | `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | No code; nonce 3,211,062. |

Pinned window 2026-09-28 00:00–12:00 UTC: `RelayErc20Deposit` 6,509, `RelayNativeDeposit` 2, `RelayCallExecuted` 868 (all at the production Depository); `FundsMovement` 4,483 (router v3.0 2,587; ApprovalProxy v3.0 1,896); `FundsForwardedWithData` 0; 0 at the staging depository.

## 8. Addresses — BNB Smart Chain (chain ID 56)

All verified with `eth_getCode` on 2026-09-29. Relay uses the EVM chain id (56); the settlement config names the chain `bnb`. The addresses are the same literal addresses as on Ethereum.

| Role | Address | Code / note |
|------|---------|-------------|
| **RelayDepository** (production) | `0x4cD00E387622C35bDDB9b4c962C136462338BC31` | 8,628 B. Same `owner()` and `allocator()` as on Ethereum. |
| RelayDepository (staging) | `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` | 8,628 B. |
| **RelayRouter v3.0** | `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | 4,720 B. |
| **RelayApprovalProxy v3.0** | `0xccc88a9d1b4ed6b0eaba998850414b24f1c315be` | 7,746 B. Same `owner()` as on Ethereum. |
| RelayRouter v3.1 | `0xe6b730e58088884704cdf11cbe95c224d4d34154` | 5,373 B. |
| RelayApprovalProxy v3.1 | `0x5a0fa369d634f49c76b08dc6c299800c1a2af977` | 10,923 B. |
| RelayRouter v2.1 / RelayApprovalProxy v2.1 | `0x3ec130b627944cad9b2750300ecb0a695da522b6` / `0x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7` | 4,153 B / 7,076 B. |
| RelayRouter v2 / RelayApprovalProxy v2 | `0xf5042e6ffac5a625d4e7848e0b01373d8eb9e222` / `0xbbbfd134e9b44bfb5123898ba36b01de7ab93d98` | 8,925 B / 11,652 B. |
| **RelayReceiver** | `0xa5f565650890fba1824ee0f21ebbbf660a179934` | 1,102 B. |
| Multicaller / OnlyOwnerMulticaller | `0x0000000000002bdbf1bf3279983603ec279cc6df` / `0xb90ed4c123843cbfd66b11411ee7694ef37e6e72` | 697 B / 1,357 B. |
| **Solver** (EOA) | `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | No code; nonce 5,899,937. |

**Not deployed here**: the dev depository `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299` (not in the config for this chain; `eth_getCode` = `0x`).

Pinned window 2026-09-28 00:00–12:00 UTC: `RelayErc20Deposit` 19,946, `RelayNativeDeposit` 4,652, `RelayCallExecuted` 1,500 (all at the production Depository); `FundsMovement` 62,526 (router v3.0 31,961; ApprovalProxy v3.0 30,565); `FundsForwardedWithData` 0; 0 at the staging depository.

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

All verified with `eth_getCode` on 2026-09-29. Relay uses the EVM chain id (43114); the settlement config names the chain `avalanche`. The addresses are the same literal addresses as on Ethereum.

| Role | Address | Code / note |
|------|---------|-------------|
| **RelayDepository** (production) | `0x4cD00E387622C35bDDB9b4c962C136462338BC31` | 8,628 B. Same `owner()` and `allocator()` as on Ethereum. |
| RelayDepository (staging) | `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` | 8,628 B. |
| **RelayRouter v3.0** | `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | 4,720 B. |
| **RelayApprovalProxy v3.0** | `0xccc88a9d1b4ed6b0eaba998850414b24f1c315be` | 7,746 B. Same `owner()` as on Ethereum. |
| RelayRouter v3.1 | `0xe6b730e58088884704cdf11cbe95c224d4d34154` | 5,373 B. |
| RelayApprovalProxy v3.1 | `0x5a0fa369d634f49c76b08dc6c299800c1a2af977` | 10,923 B. |
| RelayRouter v2.1 / RelayApprovalProxy v2.1 | `0x3ec130b627944cad9b2750300ecb0a695da522b6` / `0x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7` | 4,153 B / 7,076 B. |
| RelayRouter v2 / RelayApprovalProxy v2 | `0xf5042e6ffac5a625d4e7848e0b01373d8eb9e222` / `0xbbbfd134e9b44bfb5123898ba36b01de7ab93d98` | 8,925 B / 11,652 B. |
| **RelayReceiver** | `0xa5f565650890fba1824ee0f21ebbbf660a179934` | 1,102 B. |
| Multicaller / OnlyOwnerMulticaller | `0x0000000000002bdbf1bf3279983603ec279cc6df` / `0xb90ed4c123843cbfd66b11411ee7694ef37e6e72` | 697 B / 1,357 B. |
| **Solver** (EOA) | `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | No code; nonce 757,600. |

**Not deployed here**: the dev depository `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299` (not in the config for this chain; `eth_getCode` = `0x`).

Pinned window 2026-09-28 00:00–12:00 UTC: `RelayErc20Deposit` 383, `RelayNativeDeposit` 1, `RelayCallExecuted` 24 (all at the production Depository); `FundsMovement` 776 (router v3.0 518; ApprovalProxy v3.0 258); `FundsForwardedWithData` 0; 0 at the staging depository.

## 10. Addresses — Robinhood Chain (chain ID 4663)

All verified with `eth_getCode` on 2026-09-29. Relay uses the EVM chain id (4663); the settlement config names the chain `robinhood`. The addresses are the same literal addresses as on Ethereum.

| Role | Address | Code / note |
|------|---------|-------------|
| **RelayDepository** (production) | `0x4cD00E387622C35bDDB9b4c962C136462338BC31` | 8,628 B. Same `owner()` and `allocator()` as on Ethereum. |
| RelayDepository (staging) | `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` | 8,628 B. |
| **RelayRouter v3.0** | `0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f` | 4,720 B. |
| **RelayApprovalProxy v3.0** | `0xccc88a9d1b4ed6b0eaba998850414b24f1c315be` | 7,746 B. Same `owner()` as on Ethereum. |
| RelayRouter v3.1 | `0xe6b730e58088884704cdf11cbe95c224d4d34154` | 5,373 B. |
| RelayApprovalProxy v3.1 | `0x5a0fa369d634f49c76b08dc6c299800c1a2af977` | 10,923 B. |
| **Solver** (EOA) | `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | No code; nonce 2,163,640. |

**Not deployed here** (`eth_getCode` = `0x`, nonce 0): RelayReceiver `0xa5f565650890fba1824ee0f21ebbbf660a179934` (the Chains API field `relayReceiver` is empty for chain 4663), the v2 and v2.1 periphery (`0xf5042e6ffac5a625d4e7848e0b01373d8eb9e222`, `0xbbbfd134e9b44bfb5123898ba36b01de7ab93d98`, `0x3ec130b627944cad9b2750300ecb0a695da522b6`, `0x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7`), Multicaller and OnlyOwnerMulticaller, and the dev depository `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299`.

Pinned window 2026-09-28 00:00–12:00 UTC: `RelayErc20Deposit` 44,012, `RelayNativeDeposit` 12,476, `RelayCallExecuted` 1,427 (all at the production Depository); `FundsMovement` 230,287 (router v3.0 123,452; ApprovalProxy v3.0 106,834); `FundsForwardedWithData` 0; 0 at the staging depository.

---

## 11. Cross-chain summary

✅ = code at the address (checked with `eth_getCode` on 2026-09-29); ❌ = `eth_getCode` returns `0x`. Every contract has the **same literal address** on each chain where it exists (CREATE2 through `0x4e59b44847b379578588920ca78fbf26c0b4956c`), so always key on `(chain id, address)`.

| Chain | ID | Depository (prod) `0x4cD00E387622C35bDDB9b4c962C136462338BC31` | Depository (staging) `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` | Depository (dev) `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299` | Router + ApprovalProxy v3.0 | v3.1 pair | v2 / v2.1 pairs | RelayReceiver `0xa5f565650890fba1824ee0f21ebbbf660a179934` | Solver `0xf70da97812cb96acdf810712aa562db8dfa3dbef` |
|-------|----|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Ethereum | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | EOA |
| Base | 8453 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | EOA |
| Arbitrum One | 42161 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | EOA |
| Optimism | 10 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | EOA |
| Polygon PoS | 137 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | EOA |
| BNB Smart Chain | 56 | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | EOA |
| Avalanche C-Chain | 43114 | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | EOA |
| **Robinhood Chain** | 4663 | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | EOA |

**Chains outside the eight.** The Chains API lists 60 chains (EVM and others). Relay uses EVM chain ids for EVM chains and its own ids for the others, for example Solana `792703809` (seen as `destinationChainId` in the status API) and Bitcoin `8253038` (in the Chains API list). Some EVM chains use another Depository address (for example `0x59916da825d2d2ec1bf878d71c88826f6633ecca` on Cronos, Metis, Linea, Mantle and Taiko per the docs address table); none of those is one of the eight chains.

### 11.1 Solver addresses published by the Chains API

The Chains API field `solverAddresses` (2026-09-29) lists 42 distinct addresses over the eight chains. Transactions from these addresses are fills, refunds or withdrawals. All 42 are EOAs (no code) on every chain where the API lists them (`eth_getCode`, 2026-09-29). Only `0xf70da97812cb96acdf810712aa562db8dfa3dbef` is listed on all eight chains.

| Address | Listed on | `eth_getCode` on the listed chains |
|---------|-----------|-------------------------------------|
| `0xf70da97812cb96acdf810712aa562db8dfa3dbef` | ETH, Base, Arb, OP, Poly, BNB, Avax, Robin | EOA on every listed chain |
| `0x18dd3c14e34c1bc379f7538068c59160d9f68e25` | ETH, Base, Poly, BNB, Robin | EOA on every listed chain |
| `0x331d9a049d496385998067abf6cbb6371c8d2466` | ETH, Base, Poly, BNB, Robin | EOA on every listed chain |
| `0x370a7e2d300c14d79d4a7ee07aaca46c4b3012cf` | ETH, Base, Poly, BNB, Robin | EOA on every listed chain |
| `0x56c262027e0de4aea31d2489529cb25d23e58a8b` | ETH, Base, Poly, BNB, Robin | EOA on every listed chain |
| `0xa5a5491bca93dd4c076e4906e79e7673f4a5a142` | ETH, Base, Poly, BNB, Robin | EOA on every listed chain |
| `0xa67d7eb4dc68fa6ce8e34ef8cadaf075b9893fbb` | ETH, Base, Poly, BNB, Robin | EOA on every listed chain |
| `0xabb2acd3be814a80e502575d6c1dc5f789e9cd10` | ETH, Base, Poly, BNB, Robin | EOA on every listed chain |
| `0xada5bb90d0de0bd1b6f3938708f49295a8d1f7cb` | ETH, Base, Poly, BNB, Robin | EOA on every listed chain |
| `0xca7ded7e4f4ba8ab3b10009236ae6d1b95094589` | ETH, Base, Poly, BNB, Robin | EOA on every listed chain |
| `0x2bb27b73c602643f42471d4751fe4fc4eebefbd1` | Base, Poly, BNB, Robin | EOA on every listed chain |
| `0x0ec4e45f9ce3020024c0418a74cd31fbc487038f` | Base, BNB, Robin | EOA on every listed chain |
| `0xcc4bc7882d5ec4a3716e589ab3d816b61ae47a1a` | Base, BNB, Robin | EOA on every listed chain |
| `0x059df16bdcf8a6bd20bb4814518ff6a2df3c7b11` | Base, Robin | EOA on every listed chain |
| `0x1cd9d560440aab96f7b0a007ced7c2191cac5baf` | Base, Robin | EOA on every listed chain |
| `0x344daadde53a81f95bcc46a99d39107a509251a1` | Base, Robin | EOA on every listed chain |
| `0x4381045063b19a615a272733fa6b5f169b622646` | Base, Robin | EOA on every listed chain |
| `0x511808449be470efaf4131838b2d4998500a6f72` | Base, Robin | EOA on every listed chain |
| `0x6085932878d587332419ac976fc13d98eba6fdab` | Base, Robin | EOA on every listed chain |
| `0x67d698a325f29e17a9477f28ba4fe50f1cec60e4` | Base, Robin | EOA on every listed chain |
| `0x69374f8233a4069d48f8994d84052ecae6277ef5` | Base, Robin | EOA on every listed chain |
| `0x698dd6c03b50c3d4af12932a0388338bcdd3aaed` | Base, Robin | EOA on every listed chain |
| `0x728f51950ff096dc03a48f5e83f45ac8bb75f500` | Base, Robin | EOA on every listed chain |
| `0x81adf99fcc6073157008e25010967d307875c13c` | Base, Robin | EOA on every listed chain |
| `0x919968a4238a54b381f022a360260ef5d7e015ac` | Base, Robin | EOA on every listed chain |
| `0x9bc462bce2acd6fbe2ef5470d55b439453451083` | Base, Robin | EOA on every listed chain |
| `0xd460b4182ed80992d498290bcbc6b60e95de181b` | Base, Robin | EOA on every listed chain |
| `0xd782268f600403843484b70710daee6846fc0db8` | Base, Robin | EOA on every listed chain |
| `0xd9497b53abcd6972b6370cb195b6bfd6b280e607` | Base, Robin | EOA on every listed chain |
| `0xe209e0047731aa494289e1af9a0d03da19c5ef08` | Base, Robin | EOA on every listed chain |
| `0xf42b73d2e4d3912eade2a5f7ab39b54064c2acec` | Base, Robin | EOA on every listed chain |
| `0x035239dd57a4716e14e4a00f84b8fa7ee03e152e` | Base | EOA on every listed chain |
| `0x53939cb0b8b5d8ebc8f8208273a04a12f21c7346` | Base | EOA on every listed chain |
| `0x59a2c9bd639226012d59bba67b6990743193af78` | Base | EOA on every listed chain |
| `0x6d0a66df5f4a32be3656f63750e0253eb59d9399` | Base | EOA on every listed chain |
| `0x744dce9a9e94ac1d124bec9f2a02a9b3ec68507d` | Base | EOA on every listed chain |
| `0x850ae73e224780aff70d46157e7acc1038d9ceb6` | Base | EOA on every listed chain |
| `0x8583297605d996da21b5f47d69bf56a0f7fb74f4` | Base | EOA on every listed chain |
| `0xc1a6e71c0f69ad498aa4029bdf9f8cdba79f9678` | Poly | EOA on every listed chain |
| `0xeb81da7ac500267f62d9f93a03a0a5fb86864b2a` | Base | EOA on every listed chain |
| `0xf57519ebc17347af5a6eb3df2eab68204b1df4e1` | Base | EOA on every listed chain |
| `0xfdee58cc140e170d72aba75f29b23d7bcc05da0c` | Base | EOA on every listed chain |

---

## 12. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade / admin authority |
|----------|---------|-----------|---------------------------|
| **RelayDepository** (prod, staging, dev) | **Not a proxy; immutable logic.** | EIP-1967 implementation and beacon slots empty on all eight chains; full 8,628-byte runtime; docs: "Each contract is non-upgradable". | `owner()` (`0xf61a305199fa1135d76ffab3752d42f55cbd775a` on all eight chains, an EOA) can only `setAllocator`, transfer or renounce ownership. The docs describe the owner as the Security Council multisig, but on these chains the address has no code. |
| RelayRouter (all generations) | Not a proxy; no owner. | Implementation slot empty. | None. `cleanup*` functions are permissionless by design (the router holds no balance at rest). |
| RelayApprovalProxy (all generations) | Not a proxy; solady `Ownable`. | Implementation slot empty. `ROUTER` and `PERMIT2` are immutables (v3.x). | `owner()` = `0x463cb782c8dd0a1887b77336dff74d60f006f56e` (EOA, the canonical owner named in `relay-periphery`) for v3.0; the owner can only `withdraw` stranded balances. |
| RelayReceiver | Not a proxy. | Implementation slot empty; `SOLVER` immutable in the bytecode. | None (only `SOLVER` may call `makeCalls`). |

There is no `Upgraded(address)` event to watch. The privileged changes are `setAllocator` (no event), `OwnershipTransferred` and the handover events on the Depository and the ApprovalProxy.

---

## 13. Detection invariants & gotchas

1. **The deposit `id` is the orderId, not the requestId.** Relay has two ids. The `orderId` is the `bytes32 id` of `RelayNativeDeposit` / `RelayErc20Deposit` (readable on chain). The `requestId` is the Relay-API id of the whole intent; the docs say that it "is not derivable from on-chain data alone". The public status endpoint (`GET /intents/status/v2?requestId=`) answered `unknown` for every deposit `id` that was tried, and `success` (with the origin and destination transaction hashes) for a requestId. A lookup by orderId needs the authenticated requests API (`/requests/v3`, `x-api-key`).
2. **No on-chain record on the eight chains ties a deposit to its payout.** The destination fill carries no orderId in any event. `FundsMovement.metadata` is opaque: in the samples read it was a 33-byte value that matched neither the orderId nor the requestId. In two samples where a Relay relayer submitted the origin transaction through Multicall3 `aggregate3Value`, the requestId was appended after the ABI-encoded calldata; in a user-submitted `transferAndMulticall` sample the appended word was the orderId. The requestId appears in no event, and a direct `depositNative` carries only the orderId. The settlement record (Oracle attestation, Hub transfer) is on Relay Chain (537713), outside the eight chains. Record Relay deposits as evidence; do not match them to payouts on amount and time.
3. **`RelayCallExecuted` pays the solver, in bulk.** Solvers withdraw their Hub balance when they choose, so one `execute` can release the funds of many deposits. Sample (Ethereum): the solver `0xf70da97812cb96acdf810712aa562db8dfa3dbef` called `execute` and received 25,032.58 USDC in one `transfer`. `RelayCallExecuted.id` is the EIP-712 struct hash of the CallRequest (also the key of `callRequests(bytes32)`), never an orderId.
4. **The payout is whatever the solver does.** On the destination look for: a native or ERC-20 transfer from a solver address (§11.1), or a RelayRouter multicall that ends with `FundsMovement(from = router, to = recipient)` / `SolverNativeTransfer`. Sample (Base): the solver pulled USDC through `permit2TransferAndMulticall` on the ApprovalProxy, the router swapped it and paid the recipient; the router's `FundsMovement` named the recipient and the output token. `FundsMovement` also fires on the **source** side (the ApprovalProxy pulling user tokens, the router forwarding them to the Depository), so decode `from` / `to` before you call it a payout.
5. **No Relay event parameter is indexed.** Filter on topic0 + emitter and decode the data. Topic0 alone is not enough: `SolverNativeTransfer(address,uint256)` also had 18 logs from an unrelated contract (`0xbe139dd142823119dff7222f3da22eb923aeb875`) on Base in the pinned window.
6. **`from` in the deposit events is the credited depositor, not the payer.** Routers call `depositErc20(depositor, token, id)` with the user as `depositor`; the token `Transfer` into the Depository then comes from the router. With `depositor` = zero, `from` = `msg.sender`. Native deposits have no ERC-20 row: the amount is `msg.value` (equal to the event `amount`).
7. **Three depositories emit the same events.** Production `0x4cD00E387622C35bDDB9b4c962C136462338BC31`, staging `0x9ddC6a541e8F8B50B0996786A3eC275AB4d3A76C` (1 deposit on Ethereum and 3 on Base in the pinned window) and dev `0x5CB1De3603A71Ac2f67b12bFbF095013FE4Ac299`. The staging and dev instances have their own owner and allocator. Key on the production address unless you want test traffic.
8. **`setAllocator` emits nothing.** A change of the allocator (the only key that can release escrowed funds) is visible only as a transaction with selector `0xbf83f2a2` to the Depository, or by polling `allocator()` (`0x63c1d3e9c646184529c5694630a01c00df171b56` on all eight chains on 2026-09-29).
9. **Robinhood Chain is the busiest chain in the pinned window** (44,012 ERC-20 and 12,476 native deposits; 230,287 `FundsMovement`). The Robinhood Chain and Arbitrum deposit samples read here came through ERC-4337 bundles (`handleOps` on `0x4337084d9e255ff0702461cf8895ce9e3b5ff108` and on `0x0000000071727de22e5e9d8baf0edac6f37da032`), so `tx.from` was a bundler, not the user.
10. **The RelayReceiver is a deposit path, not a payout path.** `forward` / `fallback` send the native value straight to the solver and log the calldata (the request id). It is not an escrow and has no Robinhood Chain deployment. `FundsForwardedWithData` had 0 logs in the pinned window.
11. **Two periphery generations are live at the same time.** The Chains API returns v3.0 (`0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f`, `0xccc88a9d1b4ed6b0eaba998850414b24f1c315be`); `relay-periphery` already records v3.1 (`0xe6b730e58088884704cdf11cbe95c224d4d34154`, `0x5a0fa369d634f49c76b08dc6c299800c1a2af977`), which had 0 `FundsMovement` logs on all eight chains in the pinned window. The v3.0 and v3.1 ApprovalProxy selectors differ for `permitTransferAndMulticall`, `permit3009TransferAndMulticall` and `withdraw` (§2.3).
12. **The Depository code hash differs per chain** (same 8,628-byte size) because the EIP-712 domain is cached in immutables. A code-hash match across chains fails; match on the address, the size and the selectors instead. The v3.1 ApprovalProxy has the same property; the routers, the v3.0 ApprovalProxy and the RelayReceiver have one hash on every chain.
13. **Admin actions to alert on:** `OwnershipTransferred` / `OwnershipHandoverRequested` on the Depository or the ApprovalProxy; a transaction to the Depository with selector `0xbf83f2a2` (`setAllocator`); `withdraw` on an ApprovalProxy; a `RelayCallExecuted` whose `call.to` is not a token or a known solver (a release to an unexpected address).

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_RELAY_NATIVE_DEPOSIT        = '\x8032066556caf3967d8fec4ad22a2d9e1e9576556b2903a0fcd5b1fd201e3477'
TOPIC_RELAY_ERC20_DEPOSIT         = '\x49fed1d0b752ce30eee63c7a81133f3363b532fec5d4d7dd1ccfd005de4555e1'
TOPIC_RELAY_CALL_EXECUTED         = '\x4be109453ef7e895dc7215c929fff9b76b51483d56a4d04548b4866e9aa7c5ea'
TOPIC_FUNDS_MOVEMENT              = '\xafbab204e8271965231d37baed9b1abca8725b7409c70314455f68bc89142b91'
TOPIC_SOLVER_CALL_EXECUTED        = '\x93485dcd31a905e3ffd7b012abe3438fa8fa77f98ddc9f50e879d3fa7ccdc324'
TOPIC_SOLVER_NATIVE_TRANSFER      = '\xd35467972d1fda5b63c735f59d3974fa51785a41a92aa3ed1b70832836f8dba6'
TOPIC_FUNDS_FORWARDED_WITH_DATA   = '\x936c2ca3b35d2d0b24057b0675c459e4515f48fe132d138e213ae59ffab7f53e'
TOPIC_OWNERSHIP_TRANSFERRED       = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_OWNERSHIP_HANDOVER_REQUESTED = '\xdbf36a107da19e49527a7176a1babf963b4b0ff8cde35ee35d6cd8f1f9ac7e1d'
TOPIC_OWNERSHIP_HANDOVER_CANCELED = '\xfa7b8eab7da67f412cc9575ed43464468f9bfbae89d1675917346ca6d8fe3c92'
TOPIC_ROUTER_UPDATED              = '\x7aed1d3e8155a07ccf395e44ea3109a0e2d6c9b29bbbe9f142d9790596f4dc80'
TOPIC_PERMIT2_UPDATED             = '\xaecfd826d6b270962e6ff81f57b75e8527073ef343cbb38af801b8a972c78461'
TOPIC_USDC_INITIALIZED            = '\x4ba112082ec7c5f4560417c7baff6813dfd8babd0f46e63ce2eb897f2d60e90d'
TOPIC_DEPOSITS_ENABLED_SET        = '\xeb68b6c7ff0e24f32ff5050ed7cf86fbe6abbdb204f11f97377013888cd5be58'
TOPIC_ERC20_TRANSFER              = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors (chain-agnostic) =====
SEL_DEPOSIT_NATIVE                = '\x49290c1c'
SEL_DEPOSIT_ERC20                 = '\xe8017952'
SEL_DEPOSIT_ERC20_ALLOWANCE       = '\x5a1ee3ac'
SEL_EXECUTE                       = '\x2d9fb478'
SEL_SET_ALLOCATOR                 = '\xbf83f2a2'
SEL_ALLOCATOR                     = '\xaa5dcecc'
SEL_CALL_REQUESTS                 = '\xd52bfcc8'
SEL_OWNER                         = '\x8da5cb5b'
SEL_TRANSFER_OWNERSHIP            = '\xf2fde38b'
SEL_COMPLETE_OWNERSHIP_HANDOVER   = '\xf04e283e'
SEL_MULTICALL                     = '\xcd6e13f7'
SEL_CLEANUP_ERC20S                = '\x9bb43718'
SEL_CLEANUP_ERC20S_VIA_CALL       = '\x73b7bb2f'
SEL_CLEANUP_NATIVE                = '\xa6bd8c96'
SEL_CLEANUP_NATIVE_VIA_CALL       = '\x5d1fe6a2'
SEL_TRANSFER_AND_MULTICALL        = '\xf9e4bab4'
SEL_PERMIT_TRANSFER_AND_MULTICALL_V30 = '\xfb68c293'
SEL_PERMIT_TRANSFER_AND_MULTICALL_V31 = '\xbd4967a9'
SEL_PERMIT2_TRANSFER_AND_MULTICALL = '\x0a2b8f36'
SEL_PERMIT3009_TRANSFER_AND_MULTICALL_V30 = '\xf80f00fb'
SEL_PERMIT3009_TRANSFER_AND_MULTICALL_V31 = '\x745599f3'
SEL_APPROVAL_PROXY_WITHDRAW_V30   = '\x51cff8d9'
SEL_APPROVAL_PROXY_WITHDRAW_V31   = '\xf940e385'
SEL_RECEIVER_FORWARD              = '\xd948d468'
SEL_RECEIVER_MAKE_CALLS           = '\xdd4ed837'

-- ===== Addresses (network-specific; the same literal address on every chain where present) =====
-- Ethereum (1)
ETH_RELAY_DEPOSITORY            = '\x4cd00e387622c35bddb9b4c962c136462338bc31'
ETH_RELAY_DEPOSITORY_STAGING    = '\x9ddc6a541e8f8b50b0996786a3ec275ab4d3a76c'
ETH_RELAY_DEPOSITORY_DEV        = '\x5cb1de3603a71ac2f67b12bfbf095013fe4ac299'
ETH_RELAY_ROUTER_V30            = '\xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f'
ETH_RELAY_APPROVAL_PROXY_V30    = '\xccc88a9d1b4ed6b0eaba998850414b24f1c315be'
ETH_RELAY_ROUTER_V31            = '\xe6b730e58088884704cdf11cbe95c224d4d34154'
ETH_RELAY_APPROVAL_PROXY_V31    = '\x5a0fa369d634f49c76b08dc6c299800c1a2af977'
ETH_RELAY_ROUTER_V21            = '\x3ec130b627944cad9b2750300ecb0a695da522b6'
ETH_RELAY_APPROVAL_PROXY_V21    = '\x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7'
ETH_RELAY_ROUTER_V2             = '\xf5042e6ffac5a625d4e7848e0b01373d8eb9e222'
ETH_RELAY_APPROVAL_PROXY_V2     = '\xbbbfd134e9b44bfb5123898ba36b01de7ab93d98'
ETH_RELAY_RECEIVER              = '\xa5f565650890fba1824ee0f21ebbbf660a179934'
ETH_RELAY_SOLVER_EOA            = '\xf70da97812cb96acdf810712aa562db8dfa3dbef'
ETH_RELAY_DEPOSITORY_OWNER_EOA  = '\xf61a305199fa1135d76ffab3752d42f55cbd775a'
ETH_RELAY_ALLOCATOR_EOA         = '\x63c1d3e9c646184529c5694630a01c00df171b56'
-- Base (8453)
BASE_RELAY_DEPOSITORY           = '\x4cd00e387622c35bddb9b4c962c136462338bc31'
BASE_RELAY_DEPOSITORY_STAGING   = '\x9ddc6a541e8f8b50b0996786a3ec275ab4d3a76c'
BASE_RELAY_DEPOSITORY_DEV       = '\x5cb1de3603a71ac2f67b12bfbf095013fe4ac299'
BASE_RELAY_ROUTER_V30           = '\xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f'
BASE_RELAY_APPROVAL_PROXY_V30   = '\xccc88a9d1b4ed6b0eaba998850414b24f1c315be'
BASE_RELAY_ROUTER_V31           = '\xe6b730e58088884704cdf11cbe95c224d4d34154'
BASE_RELAY_APPROVAL_PROXY_V31   = '\x5a0fa369d634f49c76b08dc6c299800c1a2af977'
BASE_RELAY_ROUTER_V21           = '\x3ec130b627944cad9b2750300ecb0a695da522b6'
BASE_RELAY_APPROVAL_PROXY_V21   = '\x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7'
BASE_RELAY_ROUTER_V2            = '\xf5042e6ffac5a625d4e7848e0b01373d8eb9e222'
BASE_RELAY_APPROVAL_PROXY_V2    = '\xbbbfd134e9b44bfb5123898ba36b01de7ab93d98'
BASE_RELAY_RECEIVER             = '\xa5f565650890fba1824ee0f21ebbbf660a179934'
BASE_RELAY_SOLVER_EOA           = '\xf70da97812cb96acdf810712aa562db8dfa3dbef'
BASE_RELAY_DEPOSITORY_OWNER_EOA = '\xf61a305199fa1135d76ffab3752d42f55cbd775a'
BASE_RELAY_ALLOCATOR_EOA        = '\x63c1d3e9c646184529c5694630a01c00df171b56'
-- Arbitrum One (42161)
ARB_RELAY_DEPOSITORY            = '\x4cd00e387622c35bddb9b4c962c136462338bc31'
ARB_RELAY_DEPOSITORY_STAGING    = '\x9ddc6a541e8f8b50b0996786a3ec275ab4d3a76c'
ARB_RELAY_DEPOSITORY_DEV        = '\x5cb1de3603a71ac2f67b12bfbf095013fe4ac299'
ARB_RELAY_ROUTER_V30            = '\xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f'
ARB_RELAY_APPROVAL_PROXY_V30    = '\xccc88a9d1b4ed6b0eaba998850414b24f1c315be'
ARB_RELAY_ROUTER_V31            = '\xe6b730e58088884704cdf11cbe95c224d4d34154'
ARB_RELAY_APPROVAL_PROXY_V31    = '\x5a0fa369d634f49c76b08dc6c299800c1a2af977'
ARB_RELAY_ROUTER_V21            = '\x3ec130b627944cad9b2750300ecb0a695da522b6'
ARB_RELAY_APPROVAL_PROXY_V21    = '\x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7'
ARB_RELAY_ROUTER_V2             = '\xf5042e6ffac5a625d4e7848e0b01373d8eb9e222'
ARB_RELAY_APPROVAL_PROXY_V2     = '\xbbbfd134e9b44bfb5123898ba36b01de7ab93d98'
ARB_RELAY_RECEIVER              = '\xa5f565650890fba1824ee0f21ebbbf660a179934'
ARB_RELAY_SOLVER_EOA            = '\xf70da97812cb96acdf810712aa562db8dfa3dbef'
ARB_RELAY_DEPOSITORY_OWNER_EOA  = '\xf61a305199fa1135d76ffab3752d42f55cbd775a'
ARB_RELAY_ALLOCATOR_EOA         = '\x63c1d3e9c646184529c5694630a01c00df171b56'
-- Optimism (10)
OP_RELAY_DEPOSITORY             = '\x4cd00e387622c35bddb9b4c962c136462338bc31'
OP_RELAY_DEPOSITORY_STAGING     = '\x9ddc6a541e8f8b50b0996786a3ec275ab4d3a76c'
OP_RELAY_DEPOSITORY_DEV         = '\x5cb1de3603a71ac2f67b12bfbf095013fe4ac299'
OP_RELAY_ROUTER_V30             = '\xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f'
OP_RELAY_APPROVAL_PROXY_V30     = '\xccc88a9d1b4ed6b0eaba998850414b24f1c315be'
OP_RELAY_ROUTER_V31             = '\xe6b730e58088884704cdf11cbe95c224d4d34154'
OP_RELAY_APPROVAL_PROXY_V31     = '\x5a0fa369d634f49c76b08dc6c299800c1a2af977'
OP_RELAY_ROUTER_V21             = '\x3ec130b627944cad9b2750300ecb0a695da522b6'
OP_RELAY_APPROVAL_PROXY_V21     = '\x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7'
OP_RELAY_ROUTER_V2              = '\xf5042e6ffac5a625d4e7848e0b01373d8eb9e222'
OP_RELAY_APPROVAL_PROXY_V2      = '\xbbbfd134e9b44bfb5123898ba36b01de7ab93d98'
OP_RELAY_RECEIVER               = '\xa5f565650890fba1824ee0f21ebbbf660a179934'
OP_RELAY_SOLVER_EOA             = '\xf70da97812cb96acdf810712aa562db8dfa3dbef'
OP_RELAY_DEPOSITORY_OWNER_EOA   = '\xf61a305199fa1135d76ffab3752d42f55cbd775a'
OP_RELAY_ALLOCATOR_EOA          = '\x63c1d3e9c646184529c5694630a01c00df171b56'
-- Polygon PoS (137)
POLY_RELAY_DEPOSITORY           = '\x4cd00e387622c35bddb9b4c962c136462338bc31'
POLY_RELAY_DEPOSITORY_STAGING   = '\x9ddc6a541e8f8b50b0996786a3ec275ab4d3a76c'
POLY_RELAY_DEPOSITORY_DEV       = '\x5cb1de3603a71ac2f67b12bfbf095013fe4ac299'
POLY_RELAY_ROUTER_V30           = '\xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f'
POLY_RELAY_APPROVAL_PROXY_V30   = '\xccc88a9d1b4ed6b0eaba998850414b24f1c315be'
POLY_RELAY_ROUTER_V31           = '\xe6b730e58088884704cdf11cbe95c224d4d34154'
POLY_RELAY_APPROVAL_PROXY_V31   = '\x5a0fa369d634f49c76b08dc6c299800c1a2af977'
POLY_RELAY_ROUTER_V21           = '\x3ec130b627944cad9b2750300ecb0a695da522b6'
POLY_RELAY_APPROVAL_PROXY_V21   = '\x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7'
POLY_RELAY_ROUTER_V2            = '\xf5042e6ffac5a625d4e7848e0b01373d8eb9e222'
POLY_RELAY_APPROVAL_PROXY_V2    = '\xbbbfd134e9b44bfb5123898ba36b01de7ab93d98'
POLY_RELAY_RECEIVER             = '\xa5f565650890fba1824ee0f21ebbbf660a179934'
POLY_RELAY_SOLVER_EOA           = '\xf70da97812cb96acdf810712aa562db8dfa3dbef'
POLY_RELAY_DEPOSITORY_OWNER_EOA = '\xf61a305199fa1135d76ffab3752d42f55cbd775a'
POLY_RELAY_ALLOCATOR_EOA        = '\x63c1d3e9c646184529c5694630a01c00df171b56'
-- BNB Smart Chain (56)
BNB_RELAY_DEPOSITORY            = '\x4cd00e387622c35bddb9b4c962c136462338bc31'
BNB_RELAY_DEPOSITORY_STAGING    = '\x9ddc6a541e8f8b50b0996786a3ec275ab4d3a76c'
BNB_RELAY_ROUTER_V30            = '\xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f'
BNB_RELAY_APPROVAL_PROXY_V30    = '\xccc88a9d1b4ed6b0eaba998850414b24f1c315be'
BNB_RELAY_ROUTER_V31            = '\xe6b730e58088884704cdf11cbe95c224d4d34154'
BNB_RELAY_APPROVAL_PROXY_V31    = '\x5a0fa369d634f49c76b08dc6c299800c1a2af977'
BNB_RELAY_ROUTER_V21            = '\x3ec130b627944cad9b2750300ecb0a695da522b6'
BNB_RELAY_APPROVAL_PROXY_V21    = '\x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7'
BNB_RELAY_ROUTER_V2             = '\xf5042e6ffac5a625d4e7848e0b01373d8eb9e222'
BNB_RELAY_APPROVAL_PROXY_V2     = '\xbbbfd134e9b44bfb5123898ba36b01de7ab93d98'
BNB_RELAY_RECEIVER              = '\xa5f565650890fba1824ee0f21ebbbf660a179934'
BNB_RELAY_SOLVER_EOA            = '\xf70da97812cb96acdf810712aa562db8dfa3dbef'
BNB_RELAY_DEPOSITORY_OWNER_EOA  = '\xf61a305199fa1135d76ffab3752d42f55cbd775a'
BNB_RELAY_ALLOCATOR_EOA         = '\x63c1d3e9c646184529c5694630a01c00df171b56'
-- Avalanche C-Chain (43114)
AVAX_RELAY_DEPOSITORY           = '\x4cd00e387622c35bddb9b4c962c136462338bc31'
AVAX_RELAY_DEPOSITORY_STAGING   = '\x9ddc6a541e8f8b50b0996786a3ec275ab4d3a76c'
AVAX_RELAY_ROUTER_V30           = '\xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f'
AVAX_RELAY_APPROVAL_PROXY_V30   = '\xccc88a9d1b4ed6b0eaba998850414b24f1c315be'
AVAX_RELAY_ROUTER_V31           = '\xe6b730e58088884704cdf11cbe95c224d4d34154'
AVAX_RELAY_APPROVAL_PROXY_V31   = '\x5a0fa369d634f49c76b08dc6c299800c1a2af977'
AVAX_RELAY_ROUTER_V21           = '\x3ec130b627944cad9b2750300ecb0a695da522b6'
AVAX_RELAY_APPROVAL_PROXY_V21   = '\x58cc3e0aa6cd7bf795832a225179ec2d848ce3e7'
AVAX_RELAY_ROUTER_V2            = '\xf5042e6ffac5a625d4e7848e0b01373d8eb9e222'
AVAX_RELAY_APPROVAL_PROXY_V2    = '\xbbbfd134e9b44bfb5123898ba36b01de7ab93d98'
AVAX_RELAY_RECEIVER             = '\xa5f565650890fba1824ee0f21ebbbf660a179934'
AVAX_RELAY_SOLVER_EOA           = '\xf70da97812cb96acdf810712aa562db8dfa3dbef'
AVAX_RELAY_DEPOSITORY_OWNER_EOA = '\xf61a305199fa1135d76ffab3752d42f55cbd775a'
AVAX_RELAY_ALLOCATOR_EOA        = '\x63c1d3e9c646184529c5694630a01c00df171b56'
-- Robinhood Chain (4663)
RH_RELAY_DEPOSITORY             = '\x4cd00e387622c35bddb9b4c962c136462338bc31'
RH_RELAY_DEPOSITORY_STAGING     = '\x9ddc6a541e8f8b50b0996786a3ec275ab4d3a76c'
RH_RELAY_ROUTER_V30             = '\xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f'
RH_RELAY_APPROVAL_PROXY_V30     = '\xccc88a9d1b4ed6b0eaba998850414b24f1c315be'
RH_RELAY_ROUTER_V31             = '\xe6b730e58088884704cdf11cbe95c224d4d34154'
RH_RELAY_APPROVAL_PROXY_V31     = '\x5a0fa369d634f49c76b08dc6c299800c1a2af977'
RH_RELAY_SOLVER_EOA             = '\xf70da97812cb96acdf810712aa562db8dfa3dbef'
RH_RELAY_DEPOSITORY_OWNER_EOA   = '\xf61a305199fa1135d76ffab3752d42f55cbd775a'
RH_RELAY_ALLOCATOR_EOA          = '\x63c1d3e9c646184529c5694630a01c00df171b56'
```

---

## 15. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified sources: `RelayDepository.sol` and `RelayGatewayDepository.sol` (`relayprotocol/relay-settlement`), `RelayRouter.sol`, `RelayApprovalProxy.sol`, `common/Multicall3.sol`, `receiver/RelayReceiver.sol` (`relayprotocol/relay-periphery`, head = v3.1 and commit `cc6808ba97` = v3.0 and v2.1). Every selector of §2.1–§2.4 was found as a PUSH4 in the deployed bytecode on Ethereum (the v3.0/v3.1 differences in §2.3 were confirmed both ways: present in one generation, absent in the other). The deposit, call-executed, `FundsMovement`, `SolverCallExecuted` and `SolverNativeTransfer` topic0 values were matched against decoded live logs (sample transactions below).
- **Addresses:** from the Chains API (`protocol.v2.depository`, `contracts.erc20Router`, `contracts.approvalProxy`, `contracts.relayReceiver`, `contracts.multicaller`, `contracts.onlyOwnerMulticaller`, `solverAddresses`), `relay-settlement/packages/networks/src/networks/*.ts` (prod, staging and dev depositories), `relay-settlement` and `relay-depository` `deployments/addresses.prod.json`, and `relay-periphery/deployments/v3/addresses.json` (v3.1 at head; v3.0 at commit `af89497577`), `deployments/v2.1/addresses.json` and `deployments/v2/addresses.json` (history). Every address was existence-checked with `eth_getCode` on all eight chains; EIP-1967 slots were read with `eth_getStorageAt`. `owner()`, `allocator()` and the EIP-712 domain were read with `eth_call` on every chain.
- **Samples read in full (receipt and calldata):** Ethereum `0xa8f7e404487f603c9bd3aae90a430d61bae6f1395a219dced2dfe413088121a0` (relayer Multicall3 → ApprovalProxy → router swap → `depositErc20`; requestId appended to the calldata), Base `0x2eed0d5a2bae6905eec187c5a1f5c4baf34f63d907bd972317ee3f35ff149d0c` (`transferAndMulticall` → router → `cleanupNativeViaCall` → `depositNative`), Base `0x7383d9f40579ad06ace22c30f80322285699e0e586c50397d7be588c7212a038` (direct `depositNative`), Ethereum `0x70cdf7b40bde1e5282fd91464acf68ee3ae4adfd00436c463d078c86cb9ae640` (`execute` → 25,032.58 USDC to the solver), Base `0x3582fc3420dca9a70bdcffdadc82a2d5c2096a69c0f59406284aceaf639497ac` (solver fill through `permit2TransferAndMulticall`), Ethereum `0xc29c4c29944545d6b4e496e576489e4c80fef7330c95fa44ccbf68c761720304` and Base `0xffdc6d4a142b29d3e135543d6999c0c647139fb5ff66f149a59c390b3a82e6fd` (deposits at the staging depository).
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, `eth_getLogs` per emitter):**

| Event (emitter) | Ethereum | Base | Arbitrum | Optimism | Polygon | BNB | Avalanche | Robinhood |
|-----------------|---------:|-----:|---------:|---------:|--------:|----:|----------:|----------:|
| `RelayErc20Deposit` (prod Depository) | 9,105 | 9,822 | 1,854 | 181 | 6,509 | 19,946 | 383 | 44,012 |
| `RelayNativeDeposit` (prod Depository) | 8,467 | 6,939 | 1,319 | 323 | 2 | 4,652 | 1 | 12,476 |
| `RelayCallExecuted` (prod Depository) | 1,353 | 767 | 503 | 38 | 868 | 1,500 | 24 | 1,427 |
| `FundsMovement` (router v3.0 + ApprovalProxy v3.0) | 26,802 | 29,468 | 1,952 | 1,566 | 4,483 | 62,526 | 776 | 230,287 |
| `SolverNativeTransfer` (router v3.0) | 3,647 | 6,848 | 757 | 143 | 826 | 3,614 | 314 | 7,136 |
| `FundsForwardedWithData` (RelayReceiver) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | not deployed |

  A 0 is a measurement of this window only; it does not prove that a contract is dead.

Authoritative sources (opened for this document):
- Docs — [How it works](https://docs.relay.link/references/protocol/how-it-works.md) · [EVM Depository](https://docs.relay.link/references/protocol/contracts/evm-depository) · [Contract addresses](https://docs.relay.link/references/protocol/depository/addresses) · docs source `relayprotocol/relay-docs` (`references/protocol/guides/for-apps.mdx` "orderId vs. requestId", `references/protocol/components/depository.mdx`, `references/api/api_guides/migrating-to-requests-v3.mdx`)
- API — [Chains API](https://api.relay.link/chains) · `https://api.relay.link/intents/status/v2?requestId=`
- Repositories — [relayprotocol/relay-settlement](https://github.com/relayprotocol/relay-settlement) · [relayprotocol/relay-depository](https://github.com/relayprotocol/relay-depository) (archived) · [relayprotocol/relay-periphery](https://github.com/relayprotocol/relay-periphery)

