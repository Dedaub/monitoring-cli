# Squid Router — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche; Robinhood Chain unlisted)

**Status:** verified on 2026-09-29 to 2026-10-01 against live RPC on all eight target chains, the verified source of the SquidRouter implementation (`contracts/router/SquidRouter.sol`, Solidity 0.8.23) and of `SquidRouterProxy`, the official Squid docs and the Squid API (`/v2/chains`). Topic0 and selectors recomputed as `keccak256(signature)`. Addresses existence-checked with `eth_getCode`. Implementations read from the EIP-1967 slot. Router wiring read with `eth_call`.
**Scope:** the SquidRouter proxy and implementation, SquidMulticall and SquidFeeCollector: the contracts of Squid's Axelar-based cross-chain swaps (`bridgeCall`, `callBridgeCall`), its CCTP and Chainflip entry points and its destination executor. The AxelarGateway, AxelarGasService and ITS are in [`../axelar/core.md`](../axelar/core.md). Squid Intents (Coral) is in [`coral.md`](coral.md). Topics and selectors are chain-agnostic. Addresses are network-specific.

Squid is a router on top of bridges. It has no bridge of its own. On the source chain, the router swaps the user's token into an Axelar gateway token (for example `axlUSDC`) through SquidMulticall, then calls `AxelarGateway.callContractWithToken`. **The router emits no event on the source chain.** The source leg is the gateway's `ContractCallWithToken` with `sender` (topic1) = the SquidRouter. On the destination chain, the Axelar relayer (or an express executor) calls the destination SquidRouter. The router runs the payload's swaps and emits `CrossMulticallExecuted(payloadHash)`.

The link key is `payloadHash = keccak256(payload)`. It is on chain on both sides: topic2 of `ContractCallWithToken` on the source gateway, topic1 of `CrossMulticallExecuted` / `CrossMulticallFailed` on the destination router, and a data field of the express events. It was checked on one real transfer (§7, item 2).

One proxy address, `0xce16F69375520ab01377ce7B88f5BA8C48F8D666`, serves all seven listed chains. Each chain has its own implementation, because the implementation keeps the chain's gateway, ITS, Chainflip Vault, USDC and CCTP addresses as immutables. Each chain has its own owner Safe.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Emits |
|----------|------|--------|-------|
| **SquidRouter** (`SquidRouterProxy` + `SquidRouter` implementation) | Source entry (`callBridgeCall`, `bridgeCall`, `fundAndRunMulticall`, `cctpBridge`), destination executor (`executeWithToken`, `expressExecuteWithToken`, `cfReceive`, ITS) | Axelar `Proxy`: EIP-1967 implementation slot, owner in slot `keccak256("owner")` | Destination events only, plus admin events |
| **SquidMulticall** | Runs the swap calls with its own balance; holds tokens only inside one transaction | No (immutable) | Nothing |
| **SquidFeeCollector** (`SquidFeeCollectorProxy`) | Integrator-fee escrow, called by the multicall inside a route | Axelar `Proxy` style, EIP-1967 slot | `FeeCollected`, `FeeWithdrawn` |
| AxelarGateway, AxelarGasService, ITS | Axelar's message and token layer | see [`../axelar/core.md`](../axelar/core.md) | `ContractCallWithToken`, `NativeGasPaidFor*`, `ContractCallApprovedWithMint`, `ContractCallExecuted` |

The flow of one Axelar route:

| Step | Chain | Contract and event | Value movement in the same tx |
|------|-------|--------------------|-------------------------------|
| Deposit | Source | Gateway `ContractCallWithToken(sender = SquidRouter, destinationChain, destinationContractAddress = SquidRouter, payloadHash, payload, symbol, amount)`; gas service `NativeGasPaidForContractCallWithToken` or `NativeGasPaidForExpressCallWithToken` (sourceAddress = SquidRouter) | ERC-20 `Transfer` user (or integrator contract) → SquidMulticall or router; swaps; then the gateway token router → AxelarGateway (locked, e.g. USDC on Ethereum) or router → `0x0` (burned, e.g. `axlUSDC` on Base). Gas in `msg.value` |
| Express payout (optional) | Destination | Router `ExpressExecutedWithToken` (fields `commandId`, `payloadHash`, `amount`, `expressExecutor`) then `CrossMulticallExecuted(payloadHash)` | Gateway token expressExecutor → router → SquidMulticall → DEX → recipient |
| Normal payout | Destination | Gateway `ContractCallExecuted(commandId)`; router `CrossMulticallExecuted(payloadHash)` | Gateway token minted to (or released to) the router → multicall → recipient |
| Express repayment | Destination | Gateway `ContractCallExecuted(commandId)`; router `ExpressExecutionWithTokenFulfilled` (same `commandId`) | Gateway token minted to the router → expressExecutor. **No user value** |
| Refund | Destination | Router `CrossMulticallFailed(payloadHash, reason, refundRecipient)` | Bridged gateway token router → `refundRecipient` on the destination chain |
| Direct send (64-byte payload) | Destination | No router event | Gateway token router → recipient (`Transfer` only) |

Squid's own names for the target chains, as used in `destinationChain` / `sourceChain` (Axelar chain names, from the Squid API `axelarChainName`): Ethereum `Ethereum`, Base `base`, Arbitrum `Arbitrum`, Optimism `optimism`, Polygon `Polygon`, BNB `binance`, Avalanche `Avalanche`. Robinhood Chain has none.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 SquidRouter — destination and express events (emitter: the SquidRouter proxy)

| topic0 | Event | Leg / meaning |
|--------|-------|---------------|
| `0x7c3aa10c5d96985be6de7d2e6fa79bdef95a95a9cb272f4113b3fe1ca89fedae` | `CrossMulticallExecuted(bytes32 indexed payloadHash)` | Destination: the payload's multicall ran; the recipient got the output in this tx. **Payout marker.** |
| `0xdd7b1484db8d21f4fbda2407f2920037dc379dd66e18b0851aa9d6c14ef493b9` | `CrossMulticallFailed(bytes32 indexed payloadHash, bytes reason, address indexed refundRecipient)` | Destination: the multicall reverted; the router sent the bridged token to `refundRecipient` on the destination chain. **Refund.** |
| `0x5844b8bbe3fd2b0354e73f27bfde28d2e6d991f14139c382876ec4360391a47b` | `ExpressExecutedWithToken(bytes32 indexed commandId, string sourceChain, string sourceAddress, bytes32 payloadHash, string symbol, uint256 indexed amount, address indexed expressExecutor)` | Destination, express ("boost") path: `expressExecutor` fronted `amount` of the gateway token; the payload runs in the same tx. **Payout.** |
| `0xdb3db9dfc9262f4fe09dbadef104f799d8181ec565e09275d80ed3355aab68d3` | `ExpressExecutionWithTokenFulfilled(bytes32 indexed commandId, string sourceChain, string sourceAddress, bytes32 payloadHash, string symbol, uint256 indexed amount, address indexed expressExecutor)` | Destination, later: the Axelar-approved message repays `expressExecutor`. Same `commandId` as the express payout. **Repayment, not a user payout.** |
| `0x6e18757e81c44a367109cbaa499add16f2ae7168aab9715c3cdc36b0f7ccce92` | `ExpressExecuted(bytes32 indexed commandId, string sourceChain, string sourceAddress, bytes32 payloadHash, address indexed expressExecutor)` | Express path without a token (`expressExecute`). Squid routes do not use it in practice. |
| `0x8fe61b2d4701a29265508750790e322b2c214399abdf98472158b8908b660d41` | `ExpressExecutionFulfilled(bytes32 indexed commandId, string sourceChain, string sourceAddress, bytes32 payloadHash, address indexed expressExecutor)` | Repayment pair of `ExpressExecuted`. |

### 1.2 SquidRouter — admin events

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed newImplementation)` | Implementation changed (`upgrade`). Admin. |
| `0xd9be0e8e07417e00f2521db636cb53e316fd288f5051f16d2aa2bf0c3938a876` | `OwnershipTransferStarted(address indexed newOwner)` | Two-step owner change proposed. Admin. |
| `0x04dba622d284ed0014ee4b9a6a68386be1a4c08a4913ae272de89199cc686163` | `OwnershipTransferred(address indexed newOwner)` | Owner changed. One-argument Axelar `Ownable`, not the OpenZeppelin two-argument event. Admin. |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` | Router paused: every `whenNotPaused` entry point reverts. Admin. |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` | Router unpaused. Admin. |
| `0x3210edd3f0fc490ffc59a4adae6f48dbda2d8e89afe5b37a0145a54762f3ecf9` | `PauserProposed(address indexed currentPauser, address indexed pendingPauser)` | Pauser change proposed. Admin. |
| `0xa4336c0cb1e245b95ad204faed7e940d6dc999684fd8b5e1ff597a0c4efca8ab` | `PauserUpdated(address indexed newPauser)` | Pauser changed. Admin. |

### 1.3 SquidFeeCollector (emitter: `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x205442d60b70af1203d43cab62352c3b69b94f091be32fe683198057282b5c92` | `FeeCollected(address token, address integrator, uint256 squidFee, uint256 integratorFee)` | Source tx: an integrator fee was taken (the multicall calls `collectFee`). Status only for the bridge; the fee stays in the collector. |
| `0x00ed5939179dc194223f0edd1517ecee2210b22da7f82c8e4b1795e93b9f06aa` | `FeeWithdrawn(address token, address account, uint256 amount)` | An integrator or Squid withdrew accrued fees. |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed newImplementation)` | Fee collector implementation changed. Admin. |

The source-leg topics live on Axelar contracts and are listed in [`../axelar/core.md`](../axelar/core.md) §1.1–§1.2: `ContractCallWithToken`, `NativeGasPaidForContractCallWithToken`, `NativeGasPaidForExpressCallWithToken`, `ContractCallApprovedWithMint`, `ContractCallExecuted`. The `ContractCallWithToken` topic0 is repeated in §9 for convenience only.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

`Call` = `(uint8 callType, address target, uint256 value, bytes callData, bytes payload)`. The destination `payload` is `abi.encode(Call[] calls, address refundRecipient, bytes32 salt)`, or `abi.encode(address recipient, bytes32 salt)` (64 bytes) for a direct send.

### 2.1 SquidRouter — source entry points

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x846a1bc6` | `callBridgeCall(address token, uint256 amount, (uint8 callType, address target, uint256 value, bytes callData, bytes payload)[] calls, string bridgedTokenSymbol, string destinationChain, string destinationAddress, bytes payload, address gasRefundRecipient, bool enableExpress)` | **Main source entry.** Pulls `token` from `msg.sender` to SquidMulticall (or takes `msg.value`), swaps to the Axelar token, pays gas, calls the gateway. Payable. |
| `0x21477960` | `bridgeCall(string bridgedTokenSymbol, uint256 amount, string destinationChain, string destinationAddress, bytes payload, address gasRefundRecipient, bool enableExpress)` | Source entry without a source swap: pulls the Axelar token itself to the router. Payable (gas). |
| `0x58181a80` | `fundAndRunMulticall(address token, uint256 amount, (uint8 callType, address target, uint256 value, bytes callData, bytes payload)[] calls)` | Pulls `token` to SquidMulticall and runs `calls`. Same-chain swaps, and the deposit step of routes that leave through another bridge (CCTP, Chainflip, intents). Payable. |
| `0x10816d95` | `permitFundAndRunMulticall((uint8 callType, address target, uint256 value, bytes callData, bytes payload)[] calls, address from, ((address token, uint256 amount) permitted, uint256 nonce, uint256 deadline) permit, bytes signature)` | Same, funded by a Permit2 signature of `from`. |
| `0xb45e7ffb` | `cctpBridge(uint256 amount, uint32 destinationDomain, bytes32 destinationAddress, bytes32 destinationCaller)` | Pulls USDC and calls CCTP v1 `depositForBurnWithCaller`; CCTP emits `DepositForBurn` with `depositor` = SquidRouter. |
| `0xd9a004bb` | `permitCctpBridge(uint32 destinationDomain, bytes32 destinationAddress, bytes32 destinationCaller, address from, ((address token, uint256 amount) permitted, uint256 nonce, uint256 deadline) permit, bytes signature)` | Same, funded by Permit2. |

### 2.2 SquidRouter — destination entry points

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1a98b2e0` | `executeWithToken(bytes32 commandId, string sourceChain, string sourceAddress, bytes payload, string tokenSymbol, uint256 amount)` | Axelar relayer delivery. Consumes the gateway approval; runs the payload, or repays the express executor. |
| `0xe4a974cc` | `expressExecuteWithToken(bytes32 commandId, string sourceChain, string sourceAddress, bytes payload, string symbol, uint256 amount)` | Express executor fronts `amount` before the Axelar approval. Emits `ExpressExecutedWithToken`. |
| `0x49160658` | `execute(bytes32 commandId, string sourceChain, string sourceAddress, bytes payload)` | GMP delivery without a token. The router has no handler for it (`_execute` is empty). |
| `0x65657636` | `expressExecute(bytes32 commandId, string sourceChain, string sourceAddress, bytes payload)` | Express without a token. |
| `0x29241502` | `executeWithInterchainToken(bytes32 commandId, string sourceChain, bytes sourceAddress, bytes data, bytes32 tokenId, address token, uint256 amount)` | Axelar ITS delivery; runs the payload. |
| `0x77c79025` | `expressExecuteWithInterchainToken(bytes32 commandId, string sourceChain, bytes sourceAddress, bytes data, bytes32 tokenId, address token, uint256 amount)` | ITS express delivery. |
| `0x4904ac5f` | `cfReceive(uint32 srcChain, bytes srcAddress, bytes message, address token, uint256 amount)` | Chainflip Vault delivery (`msg.sender` must be `chainflipVault()`); runs the payload. |

### 2.3 SquidRouter — admin

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa3499c73` | `upgrade(address newImplementation, bytes32 newImplementationCodeHash, bytes params)` | Owner only. Emits `Upgraded`. |
| `0x8456cb59` | `pause()` | Pauser only. Emits `Paused`. |
| `0x3f4ba83a` | `unpause()` | Pauser only. Emits `Unpaused`. |
| `0x6ccae054` | `rescueFunds(address token, address to, uint256 amount)` | Owner only. Moves any balance held by the router. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Owner only, one step. |
| `0x710bf322` | `proposeOwnership(address newOwner)` | Owner only, step 1 of 2. |
| `0x79ba5097` | `acceptOwnership()` | Pending owner, step 2 of 2. |
| `0x554bab3c` | `updatePauser(address newPauser)` | Pauser only, step 1 of 2. |
| `0x167a6f90` | `acceptPauser()` | Pending pauser, step 2 of 2. |
| `0xc3b3960d` | `approveCctpTokenMessenger()` | Owner only. Unlimited USDC approval to the CCTP TokenMessenger. |

### 2.4 SquidRouter — views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8da5cb5b` | `owner()` | `address`. Also readable from storage slot `keccak256("owner")`. |
| `0x9fd0506d` | `pauser()` | `address`. |
| `0x5c975abb` | `paused()` | `bool`. |
| `0x5c60da1b` | `implementation()` | `address`. The EIP-1967 implementation slot. |
| `0x8291286c` | `contractId()` | `bytes32` = `keccak256("squid-router")` = `0xc097d45e5a99ca772ab5ec2e5457c2e249760944b95b0b97cbb6b03ec55bae84`. |
| `0x116191b6` | `gateway()` | `address` of the AxelarGateway that this chain's router trusts. |
| `0x59ce62e9` | `squidMulticall()` | `address`. |
| `0x09c6bed9` | `interchainTokenService()` | `address`. |
| `0x7766d1ed` | `chainflipVault()` | `address`, zero where Chainflip is not wired. |
| `0x3e413bee` | `usdc()` | `address`, zero where CCTP is not wired. |
| `0x9748cf7c` | `cctpTokenMessenger()` | `address` (CCTP v1 TokenMessenger), zero where not wired. |
| `0x545614cc` | `axelarGasService()` | `address`. |
| `0x12261ee7` | `permit2()` | `address`, zero where not wired. |

### 2.5 SquidMulticall and SquidFeeCollector

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf87ef800` | `run((uint8 callType, address target, uint256 value, bytes callData, bytes payload)[] calls)` | SquidMulticall. Runs the calls with the multicall's own balance. Emits no event. |
| `0x369261b1` | `collectFee(address token, uint256 amountToTax, address integratorAddress, uint256 integratorFee)` | SquidFeeCollector. Called inside a route. Emits `FeeCollected`. |
| `0x1ac3ddeb` | `withdrawFee(address token)` | SquidFeeCollector. Emits `FeeWithdrawn`. |

---

## 3. Addresses — Ethereum (chain ID 1)

| Role | Address | One-liner |
|------|---------|-----------|
| **SquidRouter** (proxy) | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` | 1,690 B proxy; implementation `0xd1373e7ffc30486079f7215b90c49c2251c0d8f8` (20,062 B) |
| Router owner and pauser | `0x7178d1a731a245f7620daa6db6111ef531a91d0d` | Safe proxy (171 B); `getThreshold()` = 2, four owners |
| **SquidMulticall** (current) | `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` | `squidMulticall()` of the router on all seven chains |
| SquidMulticall (older) | `0xEa749Fd6bA492dbc14c24FE8A3d08769229b896c` | Verified `SquidMulticall`, 3,488 B; not wired into the current router |
| SquidMulticall (oldest) | `0x4fd39C9E151e50580779bd04B1f7eCc310079fd3` | Verified `SquidMulticall` (Solidity 0.8.17), 3,549 B; not wired |
| **SquidFeeCollector** (proxy) | `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` | Implementation `0x4e6c9bfd2829901805f579bb678e49060a7846a9` |
| Router wiring | gateway `0x4F4495243837681061C4743b74B3eEdf548D56A5`, Chainflip Vault `0xF5e10380213880111522dd0efD3dbb45b9f62Bcc`, USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`, CCTP v1 TokenMessenger `0xBd3fa81B58Ba92a82136038B25aDec7066af3155` | Read live from the router views |

## 4. Addresses — Base (chain ID 8453)

| Role | Address | One-liner |
|------|---------|-----------|
| **SquidRouter** (proxy) | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` | Implementation `0x05ca80239d4006aa3cabf6fc2efd6d6adba6b2e2` |
| Router owner and pauser | `0x25de76a4df4fd9fe5be6457213f339c6a542f4f7` | Safe proxy (171 B); `getThreshold()` = 1 |
| SquidMulticall / FeeCollector | `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` / `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` | Collector implementation `0xfa03a541567c39e8cb8e66612356db11449859b0` |
| Router wiring | gateway `0xe432150cce91c13a887f7D836923d5597adD8E31`, USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, CCTP v1 TokenMessenger `0x1682Ae6375C4E4A97e4B583BC394c861A46D8962` | No Chainflip Vault; `permit2()` = zero, so the Permit2 entry points revert here |

## 5. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **SquidRouter** (proxy) | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` | Implementation `0xdbe6fa600ab5468ccc23538070b9d74acf4e1dc0` |
| Router owner and pauser | `0x87f8db6400a7e174551da85e508a20b4c33bb97c` | Safe proxy (171 B) |
| SquidMulticall / FeeCollector | `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` / `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` | Collector implementation `0x3e4abdc5f4e2baa3189f9aaa004aedc7ffe98e43` |
| Router wiring | gateway `0xe432150cce91c13a887f7D836923d5597adD8E31`, Chainflip Vault `0x79001a5e762f3bEFC8e5871b42F6734e00498920`, USDC `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`, CCTP v1 TokenMessenger `0x19330d10D9Cc8751218eaf51E8885D058642E08A` | |

## 6. Addresses — Optimism, Polygon PoS, BNB Smart Chain, Avalanche C-Chain

The router, SquidMulticall and FeeCollector have the same addresses as on Ethereum. Per-chain values:

| Chain | ID | Router implementation | Owner / pauser (Safe proxy, 171 B) | Gateway | CCTP v1 TokenMessenger | FeeCollector implementation |
|-------|----|-----------------------|-----------------------------------|---------|------------------------|-----------------------------|
| Optimism | 10 | `0x7a84a04e086fd1b931b6dbc40d1b0f070dbaac2b` | `0x3d7caf0de27420e44b7817c98de30d5f6bd290ea` | `0xe432150cce91c13a887f7D836923d5597adD8E31` | `0x2B4069517957735bE00ceE0fadAE88a26365528f` | `0x643267ed200effddf75501377ee5a61920321388` |
| Polygon PoS | 137 | `0xf46cfea9481fb6b0d84953e956d51a6ea7b5658d` | `0xffea68f72655c4acc1d1f9523aeb6e65a6d8e8ac` | `0x6f015F16De9fC8791b234eF68D486d2bF203FBA8` | `0x9daF8c91AEFAE50b9c0E69629D3F6Ca40cA3B3FE` | `0xad993c31aa9b2e6e8977822ca800e1727442c464` |
| BNB Smart Chain | 56 | `0x9e5a4832ce8c48b2235707149a2e71c967af5f3d` | `0x44a0d096d3820607fce018e48d791ca282ff5e01` | `0x304acf330bbE08d1e512eefaa92F6a57871fD895` | none (`cctpTokenMessenger()` and `usdc()` = zero) | `0x5689df162ac387f534f4eea340d5f9a8e535f2e8` |
| Avalanche C-Chain | 43114 | `0x3451f8e4ce62c51821bfbc15194cd2338958a489` | `0x2f39d85df6e5501d95aa8db11032ee1570347838` | `0x5029C0EFf6C34351a0CEc334542cDb22c7928f78` | `0x6B25532e1060CE10cc3B0A99e5683b91BFDe6982` | `0xaf9a6ae4bfab881f6e396c91b8b35189559c187b` |

No Chainflip Vault on these four (`chainflipVault()` = zero).

## 7. Addresses — Robinhood Chain (chain ID 4663) — deployed, not listed

Squid does not list Robinhood Chain: it is absent from the contracts page and from the Squid API `/v2/chains` answer (81 chains, read 2026-09-29). The standard router address `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` has no code here (nonce 0). The "alternate" router address of the docs has code here:

| Role | Address | Evidence |
|------|---------|----------|
| SquidRouter (proxy, alternate address) | `0x2B4d4Cf15dAD79D3426D19674Bd237C1dc9144aa` | Same 1,690-byte proxy code hash as on the other chains; `contractId()` = `keccak256("squid-router")`; implementation `0xa96495fce38a6020fc7edaee111216f6e6c0ca53` (20,062 B) |
| SquidMulticall | `0x073e81d92bd8b39562106819d12346240606f04a` | `squidMulticall()` of that router; same code hash as `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` |
| Router owner and pauser (EOA) | `0xb5e6C16Cb726bb24075075E0993971Aa8D73f764` | No code, nonce 4. The same account deployed SquidMulticall `0xEa749Fd6bA492dbc14c24FE8A3d08769229b896c` on Ethereum and Base |

`gateway()`, `interchainTokenService()` and `axelarGasService()` return the placeholder `0x1000000000000000000000000000000000000000`; `usdc()`, `cctpTokenMessenger()` and `chainflipVault()` return zero. So only `fundAndRunMulticall` can work here: no Axelar, CCTP or Chainflip leg. The router emitted 0 logs in the pinned window. SquidMulticall `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` and FeeCollector `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` have no code here. `0xEa749Fd6bA492dbc14c24FE8A3d08769229b896c` holds unrelated 1,835-byte code here (not identified).

---

## 8. Cross-chain summary

| Chain | ID | SquidRouter | SquidMulticall | FeeCollector | Axelar leg | CCTP leg | Chainflip leg |
|-------|----|-------------|----------------|--------------|------------|----------|---------------|
| Ethereum | 1 | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` | `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` | `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` | yes | wired | yes |
| Base | 8453 | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` | `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` | `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` | yes | wired | no |
| Arbitrum One | 42161 | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` | `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` | `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` | yes | wired | yes |
| Optimism | 10 | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` | `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` | `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` | yes | wired | no |
| Polygon PoS | 137 | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` | `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` | `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` | yes | wired | no |
| BNB Smart Chain | 56 | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` | `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` | `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` | yes | no | no |
| Avalanche C-Chain | 43114 | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` | `0xaD6Cea45f98444a922a2b4fE96b8C90F0862D2F4` | `0x19cd4F3820E7BBed45762a30BFA37dFC6c9C145b` | yes | wired | no |
| Robinhood Chain | 4663 | `0x2B4d4Cf15dAD79D3426D19674Bd237C1dc9144aa` (unlisted) | `0x073e81d92bd8b39562106819d12346240606f04a` | — (no code) | no (placeholder) | no | no |

"Wired" means a non-zero `cctpTokenMessenger()`. The `cctpBridge` path produced 0 `DepositForBurn` logs with `depositor` = SquidRouter in the pinned window on all six wired chains (§11).

---

## 9. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **SquidRouter** | Axelar `Proxy` (`SquidRouterProxy`, Solidity 0.8.17). Implementation in the EIP-1967 slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; owner in slot `0x02016836a56b71f0d02689e69e326f4f4c1b9057164ef592671cf0d37c8040c0` (`keccak256("owner")`). The proxy's `receive()` reverts; payable calls go through the fallback | Slot read live on all eight chains; `implementation()` agrees | `upgrade(address,bytes32,bytes)` on the implementation, `onlyOwner`; emits `Upgraded`. The owner is a per-chain Safe (§3–§6); an EOA on Robinhood Chain |
| SquidFeeCollector | Same Axelar proxy style, EIP-1967 slot | Implementation per chain (§3–§6) | `upgrade`, owner only |
| SquidMulticall (all three) | Immutable | No implementation slot; plain runtime code | none |

The router implementations differ by chain only because of the constructor immutables (gateway, ITS, Chainflip Vault, USDC, CCTP messenger, gas service, Permit2). The verified ABI is identical on Ethereum and Base. Pause: `pause()` by the pauser stops every `whenNotPaused` entry point (all source entry points). The destination entry points have no pause guard. `paused()` was `false` on all eight chains.

---

## 10. Detection invariants & gotchas

1. **No source event from Squid.** Key the source leg on the gateway's `ContractCallWithToken` (`0x7e50569d26be643bda7757722291ec66b1be66d8283474ae3fab5a98f878a7a2`) with topic1 = the SquidRouter padded to 32 bytes. Use the per-chain gateway address (§3–§6, and [`../axelar/core.md`](../axelar/core.md) §4). The gas-service event carries the same `payloadHash`.
2. **Link key = `payloadHash`, checked on a real transfer.** BNB tx `0xd63ab900603ee3e09dc8d022df8af3dff0d81aae94d01cee1fbdd2e65ee17324` emitted `ContractCallWithToken(sender = SquidRouter, payloadHash = 0x7673221aedd6d3f3c1036593922e59f946ce7e9c22abc0ae59cb1b38f9d0efff)`. Base tx `0x5cd86af91c93b1b1410f5069a630013cf34ced9c9d6a97ee75f4266c9b848046` emitted `ExpressExecutedWithToken` (sourceChain `binance`, the same payloadHash, 27,965,110 `axlUSDC` units) and `CrossMulticallExecuted` with the same payloadHash. Base tx `0x317bdcc8d5dabe8085a3d1e068f7c6f82c10e58250dc45ee4e96c2123210bca4` later repaid the express executor with `ExpressExecutionWithTokenFulfilled` and the same `commandId`.
3. **Do not count an express transfer twice.** An express transfer gives `ExpressExecutedWithToken` + `CrossMulticallExecuted` (user payout) first and `ExpressExecutionWithTokenFulfilled` (executor repayment) later. Only the first pair is a user payout.
4. **`payloadHash` is not unique by construction.** The payload carries a `salt` so that two identical payloads hash differently, but nothing on chain enforces uniqueness. For an exact join, use the gateway's `ContractCallApprovedWithMint` on the destination, which carries `sourceTxHash` and `sourceEventIndex`.
5. **A direct-send payload has no router event at the destination.** A 64-byte payload makes the router transfer the token to the recipient with only an ERC-20 `Transfer`. Use the gateway's `ContractCallApprovedWithMint` / `ContractCallExecuted` for these.
6. **Refunds happen on the destination chain.** `CrossMulticallFailed` sends the bridged gateway token (for example `axlUSDC`) to `refundRecipient` on the destination chain, not back to the source chain.
7. **`tx.from` and `tx.to` are often not the user.** Integrators call the router from their own contracts (for example a LI.FI diamond tx on Base, `0x23886f55ffa87adf77ef8d6382fb9b9e50ed3a088c949786155adadfdc0ce8ba`). Express payouts come from the express executor, normal payouts from the Axelar relayer. The recipient is inside the payload's calls.
8. **Topic0 collisions.** `ExpressExecuted`, `ExpressExecutedWithToken`, `ExpressExecutionFulfilled` and `ExpressExecutionWithTokenFulfilled` are the generic Axelar express-executable events: ITS and other apps emit the same topic0. In the pinned window, `ExpressExecutedWithToken` also came from `0x1f1d37a3bf840e35c6a860c7c2da71fe555123ca` (Ethereum) and `0x77accd23cc3ccc5e36a543cedcd03764bf6ad401` (Base), which are not Squid. Filter on the emitter. `Upgraded` and `Paused()` are generic too.
9. **Amounts.** `ExpressExecutedWithToken.amount` is indexed (topic2) and is in the gateway token's decimals. The router's `CrossMulticallExecuted` has no amount; take it from the `Transfer` logs of the same tx.
10. **Other exits through the same router.** `cctpBridge` emits only CCTP's `DepositForBurn` (`depositor` = SquidRouter); see [`../cctp/v1.md`](../cctp/v1.md). Chainflip deliveries arrive through `cfReceive` from the Chainflip Vault and end in `CrossMulticallExecuted`. `fundAndRunMulticall` is also the deposit step of Squid Intents (see [`coral.md`](coral.md)).
11. **Robinhood Chain uses another address.** The router there is `0x2B4d4Cf15dAD79D3426D19674Bd237C1dc9144aa`, owned by an EOA, with no Axelar wiring. A filter on `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` sees nothing on chain 4663.
12. **Admin triggers.** Watch `Upgraded`, `Paused()`, `OwnershipTransferred(address)`, `PauserUpdated` and calls to `rescueFunds` (`0x6ccae054`) on the router proxy of every chain.

---

## 11. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_CROSS_MULTICALL_EXECUTED          = '\x7c3aa10c5d96985be6de7d2e6fa79bdef95a95a9cb272f4113b3fe1ca89fedae'
TOPIC_CROSS_MULTICALL_FAILED            = '\xdd7b1484db8d21f4fbda2407f2920037dc379dd66e18b0851aa9d6c14ef493b9'
TOPIC_EXPRESS_EXECUTED_WITH_TOKEN       = '\x5844b8bbe3fd2b0354e73f27bfde28d2e6d991f14139c382876ec4360391a47b'
TOPIC_EXPRESS_EXEC_WITH_TOKEN_FULFILLED = '\xdb3db9dfc9262f4fe09dbadef104f799d8181ec565e09275d80ed3355aab68d3'
TOPIC_EXPRESS_EXECUTED                  = '\x6e18757e81c44a367109cbaa499add16f2ae7168aab9715c3cdc36b0f7ccce92'
TOPIC_EXPRESS_EXECUTION_FULFILLED       = '\x8fe61b2d4701a29265508750790e322b2c214399abdf98472158b8908b660d41'
TOPIC_UPGRADED                          = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_OWNERSHIP_TRANSFERRED_1ARG        = '\x04dba622d284ed0014ee4b9a6a68386be1a4c08a4913ae272de89199cc686163'
TOPIC_OWNERSHIP_TRANSFER_STARTED        = '\xd9be0e8e07417e00f2521db636cb53e316fd288f5051f16d2aa2bf0c3938a876'
TOPIC_PAUSED_NOARG                      = '\x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752'
TOPIC_UNPAUSED_NOARG                    = '\xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933'
TOPIC_PAUSER_UPDATED                    = '\xa4336c0cb1e245b95ad204faed7e940d6dc999684fd8b5e1ff597a0c4efca8ab'
TOPIC_FEE_COLLECTED                     = '\x205442d60b70af1203d43cab62352c3b69b94f091be32fe683198057282b5c92'
TOPIC_FEE_WITHDRAWN                     = '\x00ed5939179dc194223f0edd1517ecee2210b22da7f82c8e4b1795e93b9f06aa'
-- source leg, emitted by the AxelarGateway (see ../axelar/core.md); filter topic1 = SquidRouter
TOPIC_AXELAR_CONTRACT_CALL_WITH_TOKEN   = '\x7e50569d26be643bda7757722291ec66b1be66d8283474ae3fab5a98f878a7a2'

-- ===== Selectors (chain-agnostic) =====
SEL_CALL_BRIDGE_CALL                    = '\x846a1bc6'
SEL_BRIDGE_CALL                         = '\x21477960'
SEL_FUND_AND_RUN_MULTICALL              = '\x58181a80'
SEL_PERMIT_FUND_AND_RUN_MULTICALL       = '\x10816d95'
SEL_CCTP_BRIDGE                         = '\xb45e7ffb'
SEL_PERMIT_CCTP_BRIDGE                  = '\xd9a004bb'
SEL_EXECUTE_WITH_TOKEN                  = '\x1a98b2e0'
SEL_EXPRESS_EXECUTE_WITH_TOKEN          = '\xe4a974cc'
SEL_EXECUTE_WITH_INTERCHAIN_TOKEN       = '\x29241502'
SEL_CF_RECEIVE                          = '\x4904ac5f'
SEL_UPGRADE                             = '\xa3499c73'
SEL_PAUSE                               = '\x8456cb59'
SEL_UNPAUSE                             = '\x3f4ba83a'
SEL_RESCUE_FUNDS                        = '\x6ccae054'
SEL_TRANSFER_OWNERSHIP                  = '\xf2fde38b'
SEL_MULTICALL_RUN                       = '\xf87ef800'
SEL_COLLECT_FEE                         = '\x369261b1'

-- ===== Addresses =====
ETH_SQUID_ROUTER                        = '\xce16f69375520ab01377ce7b88f5ba8c48f8d666'
BASE_SQUID_ROUTER                       = '\xce16f69375520ab01377ce7b88f5ba8c48f8d666'
ARB_SQUID_ROUTER                        = '\xce16f69375520ab01377ce7b88f5ba8c48f8d666'
OP_SQUID_ROUTER                         = '\xce16f69375520ab01377ce7b88f5ba8c48f8d666'
POLY_SQUID_ROUTER                       = '\xce16f69375520ab01377ce7b88f5ba8c48f8d666'
BNB_SQUID_ROUTER                        = '\xce16f69375520ab01377ce7b88f5ba8c48f8d666'
AVAX_SQUID_ROUTER                       = '\xce16f69375520ab01377ce7b88f5ba8c48f8d666'
RH_SQUID_ROUTER                         = '\x2b4d4cf15dad79d3426d19674bd237c1dc9144aa'
ETH_SQUID_MULTICALL                     = '\xad6cea45f98444a922a2b4fe96b8c90f0862d2f4'
BASE_SQUID_MULTICALL                    = '\xad6cea45f98444a922a2b4fe96b8c90f0862d2f4'
ARB_SQUID_MULTICALL                     = '\xad6cea45f98444a922a2b4fe96b8c90f0862d2f4'
OP_SQUID_MULTICALL                      = '\xad6cea45f98444a922a2b4fe96b8c90f0862d2f4'
POLY_SQUID_MULTICALL                    = '\xad6cea45f98444a922a2b4fe96b8c90f0862d2f4'
BNB_SQUID_MULTICALL                     = '\xad6cea45f98444a922a2b4fe96b8c90f0862d2f4'
AVAX_SQUID_MULTICALL                    = '\xad6cea45f98444a922a2b4fe96b8c90f0862d2f4'
RH_SQUID_MULTICALL                      = '\x073e81d92bd8b39562106819d12346240606f04a'
ETH_SQUID_MULTICALL_OLD                 = '\xea749fd6ba492dbc14c24fe8a3d08769229b896c'
ETH_SQUID_MULTICALL_OLDEST              = '\x4fd39c9e151e50580779bd04b1f7ecc310079fd3'
ETH_SQUID_FEE_COLLECTOR                 = '\x19cd4f3820e7bbed45762a30bfa37dfc6c9c145b'
BASE_SQUID_FEE_COLLECTOR                = '\x19cd4f3820e7bbed45762a30bfa37dfc6c9c145b'
ETH_SQUID_ROUTER_OWNER_SAFE             = '\x7178d1a731a245f7620daa6db6111ef531a91d0d'
BASE_SQUID_ROUTER_OWNER_SAFE            = '\x25de76a4df4fd9fe5be6457213f339c6a542f4f7'
ARB_SQUID_ROUTER_OWNER_SAFE             = '\x87f8db6400a7e174551da85e508a20b4c33bb97c'
OP_SQUID_ROUTER_OWNER_SAFE              = '\x3d7caf0de27420e44b7817c98de30d5f6bd290ea'
POLY_SQUID_ROUTER_OWNER_SAFE            = '\xffea68f72655c4acc1d1f9523aeb6e65a6d8e8ac'
BNB_SQUID_ROUTER_OWNER_SAFE             = '\x44a0d096d3820607fce018e48d791ca282ff5e01'
AVAX_SQUID_ROUTER_OWNER_SAFE            = '\x2f39d85df6e5501d95aa8db11032ee1570347838'
RH_SQUID_ROUTER_OWNER_EOA               = '\xb5e6c16cb726bb24075075e0993971aa8d73f764'
-- the gateway that each router trusts (gateway() view); full Axelar list in ../axelar/core.md
ETH_AXELAR_GATEWAY                      = '\x4f4495243837681061c4743b74b3eedf548d56a5'
BASE_AXELAR_GATEWAY                     = '\xe432150cce91c13a887f7d836923d5597add8e31'
ARB_AXELAR_GATEWAY                      = '\xe432150cce91c13a887f7d836923d5597add8e31'
OP_AXELAR_GATEWAY                       = '\xe432150cce91c13a887f7d836923d5597add8e31'
POLY_AXELAR_GATEWAY                     = '\x6f015f16de9fc8791b234ef68d486d2bf203fba8'
BNB_AXELAR_GATEWAY                      = '\x304acf330bbe08d1e512eefaa92f6a57871fd895'
AVAX_AXELAR_GATEWAY                     = '\x5029c0eff6c34351a0cec334542cdb22c7928f78'
-- proxy slots
EIP1967_IMPL_SLOT                       = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
AXELAR_OWNER_SLOT                       = '\x02016836a56b71f0d02689e69e326f4f4c1b9057164ef592671cf0d37c8040c0'
```

---

## 12. Verification & sources

How the constants were verified (2026-09-29 to 2026-10-01):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified ABI of the SquidRouter implementation (Ethereum `0xd1373e7ffc30486079f7215b90c49c2251c0d8f8`, Base `0x05ca80239d4006aa3cabf6fc2efd6d6adba6b2e2`; the two ABIs are identical), of SquidMulticall and of SquidFeeCollector. The selectors `0x846a1bc6`, `0xe4a974cc` and `0x1a98b2e0` match the input of the sample transactions below. A route quote from the Squid API (Arbitrum USDC to Base USDC) returned `transactionRequest.target` = the router, with calldata that starts with `0x846a1bc6` (`callBridgeCall`).
- **Addresses:** the router, SquidMulticall and alternate router from the Squid contracts page; the fee collector from the Squid fee docs. Each address existence-checked with `eth_getCode` on all eight chains. Router wiring (`gateway`, `squidMulticall`, `interchainTokenService`, `chainflipVault`, `usdc`, `cctpTokenMessenger`, `axelarGasService`, `permit2`, `owner`, `pauser`, `paused`, `implementation`, `contractId`) read with `eth_call` on every chain. Owners: 171-byte Safe proxies on the seven listed chains (`getThreshold()` = 2 on Ethereum with four owners, 1 on Base; not read elsewhere); EOA on Robinhood Chain.
- **Measured activity**, pinned 12-hour window 2026-09-28 00:00–12:00 UTC, emitter = the router (or the gateway with topic1 = router), with `eth_getLogs`:

| Event | Ethereum | Base | Arbitrum | Optimism | Polygon | BNB | Avalanche | Robinhood |
|-------|---------:|-----:|---------:|---------:|--------:|----:|----------:|----------:|
| Gateway `ContractCallWithToken`, sender = router (source) | 22 | 22 | 6 | 5 | 17 | 25 | 7 | n/a (no gateway) |
| `CrossMulticallExecuted` (payout) | 37 | 48 | 23 | 4 | 7 | 36 | 6 | 0 |
| `ExpressExecutedWithToken` (express payout) | 4 | 25 | 14 | 3 | 3 | 14 | 3 | 0 |
| `ExpressExecutionWithTokenFulfilled` (repayment) | 4 | 22 | 15 | 3 | 4 | 14 | 3 | 0 |
| `CrossMulticallFailed` (refund) | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| CCTP v1 `DepositForBurn`, depositor = router | 0 | 0 | 0 | 0 | 0 | not wired | 0 | not wired |

  Positive control for the CCTP row: the same TokenMessengers emitted `DepositForBurn` from any depositor 106 times (Ethereum) and 52 times (Base) in the window. Robinhood row: the router `0x2B4d4Cf15dAD79D3426D19674Bd237C1dc9144aa` emitted 0 logs of any topic. These counts are one 12-hour window; they say nothing about other periods.
- **Sample transactions read** (`eth_getTransactionReceipt`): source Ethereum `0xf1fa0012d68f0a5f36eb348369a9e1f9ae32531b6bcf56b56d611525c3dd0033` (`callBridgeCall` with ETH, swap to USDC, USDC router → gateway, express gas paid, `ContractCallWithToken`); source Base `0x23886f55ffa87adf77ef8d6382fb9b9e50ed3a088c949786155adadfdc0ce8ba` (through an integrator, `axlUSDC` burned router → `0x0`); BNB → Base transfer of §10 item 2; refund Ethereum `0x2a70d77f49176d212edcf6a86aa9d94227bc3b69c6b8353aaea522d9ff144e91` (USDC gateway → router → refund recipient, `CrossMulticallFailed`).
- **Chain coverage:** the seven listed chains carry the router at the standard address (proxy code hash identical). Robinhood Chain: standard address empty (nonce 0); alternate address deployed but not listed by Squid.

Sources:
- [Squid docs — Contracts](https://docs.squidrouter.com/additional-resources/contracts) · [Fee collector contract addresses](https://docs.squidrouter.com/api-and-sdk-integration/key-concepts/collect-fees-1/fee-collector-contract-addresses) · [Architecture](https://docs.squidrouter.com/additional-resources/architecture) · [Squid API `/v2/chains`](https://v2.api.squidrouter.com/v2/chains)
- [0xsquid/squid-types](https://github.com/0xsquid/squid-types) (route and bridge types) · [0xsquid/examples](https://github.com/0xsquid/examples) · [0xsquid/audits](https://github.com/0xsquid/audits)
- Verified source: [Blockscout Ethereum, SquidRouter implementation](https://eth.blockscout.com/address/0xd1373e7ffc30486079f7215b90c49c2251c0d8f8) · [Blockscout Base, SquidRouterProxy](https://base.blockscout.com/address/0xce16F69375520ab01377ce7B88f5BA8C48F8D666) · [Etherscan, router](https://etherscan.io/address/0xce16f69375520ab01377ce7b88f5ba8c48f8d666)
- Axelar contracts: [`../axelar/core.md`](../axelar/core.md); CCTP: [`../cctp/v1.md`](../cctp/v1.md)
