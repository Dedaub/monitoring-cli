# Socket v3 / OpenRouter — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the Socket docs (`docs.socket.tech/integrate/contract-addresses`, `/about/chain-support`, `/openrouter-swap-v3-user-reference`, `/integrate/integration-guides/additional-guides/destination-payload`) and the explorer-verified sources of `OpenRouter`, `RFQVaultExecutor`, `BungeeReceiver` and `AllowanceHolder`. Topics and selectors recomputed as `keccak256(signature)` from the verified ABIs; every address existence-checked with `eth_getCode`; sample transactions read on Ethereum and Base.
**Scope:** the current Socket (Bungee) contract set for API routes (`userOps=tx`): the AllowanceHolder entry point, the OpenRouter, the RFQ vault of the Bungee solver route (RFQVaultExecutor), the destination-payload executor (BungeeReceiver) and the reference CalldataExecutor. All of them have the same address on all eight chains, Robinhood Chain included. Topics and selectors are chain-agnostic; addresses are network-specific.

A Socket v3 route is one transaction to the **AllowanceHolder** (`exec`, selector `0x2213bc0b`). The AllowanceHolder grants a one-transaction allowance and calls the **OpenRouter**, which pulls the user's input token, runs an optional swap, pays the integrator fee, and hands the funds to a bridge or to the Bungee RFQ vault. The OpenRouter emits `RequestExecuted(quoteId)`. For the Bungee RFQ route the **RFQVaultExecutor** records the deposit (`ERC20Deposited` / `NativeDeposited`); on the destination chain a solver-signed `fulfil` pays the receiver out of the vault of that chain (`Fulfilled`). A failed route is refunded from the source vault (`Refunded`).

Three facts to know before indexing:

1. **`quoteId` is on chain on both legs of the RFQ route.** Source: `RequestExecuted` topic1 and `ERC20Deposited` / `NativeDeposited` data word 0. Destination: `Fulfilled` data word 0. Refund: `Refunded` data word 0. The RFQ vault events have no indexed field.
2. **The RFQ vault is a liquidity vault, not an escrow per transfer.** Deposits and payouts on one chain are independent flows; one chain's vault pays receivers of transfers that started on other chains. Match the legs by `quoteId`, never by amount or address.
3. **For third-party bridges, the destination is the bridge's own payout.** OpenRouter then emits only `RequestExecuted(quoteId)` on the source chain, beside the bridge's deposit event (for example Across `FundsDeposited`). With a destination payload, BungeeReceiver emits `DestPayloadExecuted(quoteId, success)` on the destination.

---

## 0. Contract families & versions

| Contract | Address (all 8 chains) | Role | Upgradeable? |
|----------|------------------------|------|--------------|
| **AllowanceHolder** | `0x50c4E75a512F2A14A7b304787Adf79C4531A5909` | Entry point and spender of token approvals. A copy of 0x's AllowanceHolder (its constructor pins this address). Functions: `exec` and `transferFrom`, dispatched in the fallback; no events. | No (plain contract, no owner). |
| **OpenRouter** | `0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a` | Pulls the input, swaps, pays fees, calls the bridge; emits `RequestExecuted`. Called through the AllowanceHolder. | No (no owner function in the ABI). |
| **RFQVaultExecutor** | `0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5` | Bungee RFQ liquidity vault: receives deposits, pays fills, pays refunds; every payout needs a solver signature. | No proxy. Owner-managed signer (`setSolverSigner`). |
| **BungeeReceiver** | `0x8a774c1b73998a54ff09341f3cff8a0010bba7f1` | Destination-payload executor: receives bridged tokens and calls the user's `IBungeeExecutor.executeData(quoteId, amount, token, callData)`. | No proxy. Owner and roles. |
| CalldataExecutor | `0xc914815120fa5a7e05748398c9fdf1d1b2729008` | Reference executor that forwards calldata (`CALLDATA_EXECUTOR()` of BungeeReceiver). | No |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Transfer events

| topic0 | Event |
|--------|-------|
| `0xe2a752598b97815acff854b1d0b6d5c7f33b848bcbb541df9b76038287282467` | `RequestExecuted(bytes32 indexed quoteId)` |
| `0x4794ca0cccec06c04b75a414e5ff1bd4594b69f002410d24a64b80fb2c22d456` | `ERC20Deposited(bytes32 quoteId, address token, uint256 amount)` |
| `0xac7e8d562498c85420402ece84172b01e90e7850d0c5a9e4a8bb3d222a781e84` | `NativeDeposited(bytes32 quoteId, uint256 amount)` |
| `0x91170d66098c018af5b9550ca3307975a6933fc4c2491ea3d53ca41e31397af2` | `Fulfilled(bytes32 quoteId, address token, uint256 amount, address receiver)` |
| `0x684124fe07c7e7d736370cfbc8905ea5ae8cc20708f029683464a4d4e8e0631e` | `Refunded(bytes32 quoteId, address token, uint256 amount, address receiver)` |
| `0x3dc8d383f6fa8bb849751a10c2748f761d7f5324b44a111ae03da9a1a4e1aea6` | `DestPayloadExecuted(bytes32 indexed quoteId, bool success)` |

Emitters: `RequestExecuted` → OpenRouter; `ERC20Deposited`, `NativeDeposited`, `Fulfilled`, `Refunded` → RFQVaultExecutor; `DestPayloadExecuted` → BungeeReceiver.

- `ERC20Deposited`: data word 0 `quoteId`, word 1 `token`, word 2 `amount`. The same transaction holds the `Transfer` OpenRouter → vault. `receiveERC20` pulls from any caller, so the event proves that funds entered the vault; the solver decides off chain whether the quote is valid.
- `Fulfilled` / `Refunded`: data word 0 `quoteId`, word 1 `token`, word 2 `amount`, word 3 `receiver`. The same transaction holds the vault → `receiver` `Transfer` (or a native transfer). The native token is `0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE`.
- `DestPayloadExecuted` is a status event: `success` = false means that the tokens arrived but the user's call failed.

### 1.2 Admin events

| topic0 | Event |
|--------|-------|
| `0x906a1c6bd7e3091ea86693dd029a831c19049ce77f1dce2ce0bab1cacbabce22` | `OwnerNominated(address indexed nominee)` |
| `0xfbe19c9b601f5ee90b44c7390f3fa2319eba01762d34ee372aeafd59b25c7f87` | `OwnerClaimed(address indexed claimer)` |
| `0x8571408339f42cc299c2d129ef0bfd1886efd25a6e69fddee915e25d8f216282` | `SolverSignerUpdated(address indexed newSigner)` |
| `0x2ae6a113c0ed5b78a53413ffbb7679881f11145ccfba4fb92e863dfcd5a1d2f3` | `RoleGranted(bytes32 indexed role, address indexed grantee)` |
| `0x155aaafb6329a2098580462df33ec4b7441b19729b9601c5fc17ae1cf99a8a52` | `RoleRevoked(bytes32 indexed role, address indexed revokee)` |

`OwnerNominated` / `OwnerClaimed` are the two-step ownership transfer of the RFQVaultExecutor and BungeeReceiver. `SolverSignerUpdated` (BungeeReceiver) changes the key that authorizes destination payloads. The RFQVaultExecutor changes its signer with `setSolverSigner` and emits no event: read `solverSigner()`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 AllowanceHolder

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2213bc0b` | `exec(address operator, address token, uint256 amount, address target, bytes data)` | The route transaction. `target` = OpenRouter. Sets a transient allowance for `operator`, then calls `target` with `data`. |
| `0x15dacbea` | `transferFrom(address token, address owner, address recipient, uint256 amount)` | Called back by the operator (OpenRouter) during `exec` to pull the user's tokens. |

### 2.2 OpenRouter

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb18248d5` | `bridge(bytes32 quoteId, (address user, address inputToken, uint256 inputAmount) input, (address receiver, uint256 amount) fee, (address target, address approvalSpender, uint256 value) bridgeData, bytes bridgeCallData)` | Bridge without a source swap. Emits `RequestExecuted`. |
| `0x1bb1a530` | `swap(bytes32 quoteId, uint256 flags, (address user, address inputToken, uint256 inputAmount) input, (address receiver, uint256 amount) fee, (address target, address approvalSpender, address outputToken, uint256 value, uint256 minOutput, uint256 returnDataWordOffset) swapData, bytes swapCallData, address receiver)` | Same-chain swap. Emits `RequestExecuted`. |
| `0x324012e2` | `swapAndBridge(bytes32 quoteId, uint256 flags, (address user, address inputToken, uint256 inputAmount) input, (address receiver, uint256 amount) fee, (address target, address approvalSpender, address outputToken, uint256 value, uint256 minOutput, uint256 returnDataWordOffset) swapData, bytes swapCallData, (address target, address approvalSpender, uint256 value) bridgeData, bytes bridgeCallData)` | Swap, then bridge. Emits `RequestExecuted`. |
| `0x197aa51e` | `performActions(bytes32 quoteId, (uint256 actionInfo, bytes data, uint256[] splices)[] actions)` | Generic action list. Emits `RequestExecuted`. |

### 2.3 RFQVaultExecutor

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x823b01f9` | `receiveERC20(bytes32 quoteId, address token, uint256 amount)` | Pulls `amount` of `token` from the caller into the vault. Anyone can call it. Emits `ERC20Deposited`. |
| `0x3345e738` | `receiveNative(bytes32 quoteId)` | Payable. Emits `NativeDeposited`. |
| `0x39520192` | `fulfil(bytes32 quoteId, uint256 nonce, address token, uint256 amount, address receiver, bytes signature)` | Solver-signed payout from the vault. Emits `Fulfilled`. |
| `0xc02409ba` | `swapAndFulfil(bytes32 quoteId, uint256 nonce, address approvalToken, address approvalSpender, uint256 approvalAmount, address outputToken, uint256 minOutput, (address target, uint256 value, bytes data) swapAction, address receiver, bytes signature)` | Solver-signed swap of vault inventory, then payout. Emits `Fulfilled`. |
| `0x27963312` | `markForRefund(bytes32 quoteId, uint256 nonce, bytes signature)` | Solver-signed, on the destination chain: marks the quote used so no `fulfil` can follow; the origin-chain `refund` comes after. |
| `0x612406de` | `refund(bytes32 quoteId, uint256 nonce, address token, uint256 amount, address receiver, bytes signature)` | Solver-signed refund from the vault. Emits `Refunded`. |
| `0x875083e2` | `performActions(uint256 nonce, (address target, uint256 value, bytes data)[] actions, bytes signature)` | Solver-signed arbitrary actions of the vault. |
| `0x444eac45` | `setSolverSigner(address _solverSigner)` | Owner only. |
| `0x6ccae054` | `rescueFunds(address token_, address rescueTo_, uint256 amount_)` | Owner only. |
| `0x5b94db27` | `nominateOwner(address nominee_)` | Owner only. Emits `OwnerNominated`. |
| `0x3bd1adec` | `claimOwner()` | Nominee only. Emits `OwnerClaimed`. |

### 2.4 BungeeReceiver

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x2b7ead8b` | `executeDestPayload((uint256 nonce, bytes32 quoteId, address bridgedToken, address target, uint256 outputAmount, uint256 gasLimit) payload, bytes executionCallData, bytes signature)` | Signed payload: calls the target executor with the bridged tokens. Emits `DestPayloadExecuted`. |
| `0x444eac45` | `setSolverSigner(address _solverSigner)` | Owner only. |
| `0x2f2ff15d` | `grantRole(bytes32 role_, address grantee_)` | Owner. Emits `RoleGranted`. |
| `0xd547741f` | `revokeRole(bytes32 role_, address revokee_)` | Owner. Emits `RoleRevoked`. |
| `0x6ccae054` | `rescueFunds(address token, address rescueTo, uint256 amount)` | Owner only. |

---

## 3. Addresses — Ethereum (chain ID 1)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| AllowanceHolder | `0x50c4E75a512F2A14A7b304787Adf79C4531A5909` | 1,469 |
| OpenRouter | `0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a` | 6,140 |
| RFQVaultExecutor | `0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5` | 5,158 |
| BungeeReceiver | `0x8A774c1B73998A54ff09341f3cfF8A0010BbA7f1` | 4,226 |
| CalldataExecutor | `0xC914815120FA5A7e05748398C9fDf1d1b2729008` | 798 |

RFQVaultExecutor `owner()` = `0xF76e73720EC93df7E823b755E10C38A877C34Bd5`; BungeeReceiver `owner()` = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 4. Addresses — Base (chain ID 8453)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| AllowanceHolder | `0x50c4E75a512F2A14A7b304787Adf79C4531A5909` | 1,469 |
| OpenRouter | `0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a` | 6,140 |
| RFQVaultExecutor | `0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5` | 5,158 |
| BungeeReceiver | `0x8A774c1B73998A54ff09341f3cfF8A0010BbA7f1` | 4,226 |
| CalldataExecutor | `0xC914815120FA5A7e05748398C9fDf1d1b2729008` | 798 |

RFQVaultExecutor `owner()` = `0xF76e73720EC93df7E823b755E10C38A877C34Bd5`; BungeeReceiver `owner()` = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 5. Addresses — Arbitrum One (chain ID 42161)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| AllowanceHolder | `0x50c4E75a512F2A14A7b304787Adf79C4531A5909` | 1,469 |
| OpenRouter | `0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a` | 6,140 |
| RFQVaultExecutor | `0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5` | 5,158 |
| BungeeReceiver | `0x8A774c1B73998A54ff09341f3cfF8A0010BbA7f1` | 4,226 |
| CalldataExecutor | `0xC914815120FA5A7e05748398C9fDf1d1b2729008` | 798 |

RFQVaultExecutor `owner()` = `0xF76e73720EC93df7E823b755E10C38A877C34Bd5`; BungeeReceiver `owner()` = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 6. Addresses — Optimism (chain ID 10)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| AllowanceHolder | `0x50c4E75a512F2A14A7b304787Adf79C4531A5909` | 1,469 |
| OpenRouter | `0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a` | 6,140 |
| RFQVaultExecutor | `0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5` | 5,158 |
| BungeeReceiver | `0x8A774c1B73998A54ff09341f3cfF8A0010BbA7f1` | 4,226 |
| CalldataExecutor | `0xC914815120FA5A7e05748398C9fDf1d1b2729008` | 798 |

RFQVaultExecutor `owner()` = `0xF76e73720EC93df7E823b755E10C38A877C34Bd5`; BungeeReceiver `owner()` = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 7. Addresses — Polygon PoS (chain ID 137)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| AllowanceHolder | `0x50c4E75a512F2A14A7b304787Adf79C4531A5909` | 1,469 |
| OpenRouter | `0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a` | 6,140 |
| RFQVaultExecutor | `0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5` | 5,158 |
| BungeeReceiver | `0x8A774c1B73998A54ff09341f3cfF8A0010BbA7f1` | 4,226 |
| CalldataExecutor | `0xC914815120FA5A7e05748398C9fDf1d1b2729008` | 798 |

RFQVaultExecutor `owner()` = `0xF76e73720EC93df7E823b755E10C38A877C34Bd5`; BungeeReceiver `owner()` = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 8. Addresses — BNB Smart Chain (chain ID 56)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| AllowanceHolder | `0x50c4E75a512F2A14A7b304787Adf79C4531A5909` | 1,469 |
| OpenRouter | `0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a` | 6,140 |
| RFQVaultExecutor | `0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5` | 5,158 |
| BungeeReceiver | `0x8A774c1B73998A54ff09341f3cfF8A0010BbA7f1` | 4,226 |
| CalldataExecutor | `0xC914815120FA5A7e05748398C9fDf1d1b2729008` | 798 |

RFQVaultExecutor `owner()` = `0xF76e73720EC93df7E823b755E10C38A877C34Bd5`; BungeeReceiver `owner()` = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| AllowanceHolder | `0x50c4E75a512F2A14A7b304787Adf79C4531A5909` | 1,469 |
| OpenRouter | `0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a` | 6,140 |
| RFQVaultExecutor | `0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5` | 5,158 |
| BungeeReceiver | `0x8A774c1B73998A54ff09341f3cfF8A0010BbA7f1` | 4,226 |
| CalldataExecutor | `0xC914815120FA5A7e05748398C9fDf1d1b2729008` | 798 |

RFQVaultExecutor `owner()` = `0xF76e73720EC93df7E823b755E10C38A877C34Bd5`; BungeeReceiver `owner()` = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

## 10. Addresses — Robinhood Chain (chain ID 4663)

Existence-checked with `eth_getCode` on 2026-09-29 (runtime size in bytes).

| Contract | Address | Code |
|----------|---------|------|
| AllowanceHolder | `0x50c4E75a512F2A14A7b304787Adf79C4531A5909` | 1,469 |
| OpenRouter | `0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a` | 6,140 |
| RFQVaultExecutor | `0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5` | 5,158 |
| BungeeReceiver | `0x8A774c1B73998A54ff09341f3cfF8A0010BbA7f1` | 4,226 |
| CalldataExecutor | `0xC914815120FA5A7e05748398C9fDf1d1b2729008` | 798 |

RFQVaultExecutor `owner()` = `0xF76e73720EC93df7E823b755E10C38A877C34Bd5`; BungeeReceiver `owner()` = `0xB0BBff6311B7F245761A7846d3Ce7B1b100C1836`.

---

## 11. Cross-chain summary

| Chain | ID | AllowanceHolder | OpenRouter | RFQVaultExecutor | BungeeReceiver | CalldataExecutor |
|-------|----|-----------------|------------|------------------|----------------|------------------|
| Ethereum | 1 | ✓ | ✓ | ✓ | ✓ | ✓ |
| Base | 8453 | ✓ | ✓ | ✓ | ✓ | ✓ |
| Arbitrum One | 42161 | ✓ | ✓ | ✓ | ✓ | ✓ |
| Optimism | 10 | ✓ | ✓ | ✓ | ✓ | ✓ |
| Polygon PoS | 137 | ✓ | ✓ | ✓ | ✓ | ✓ |
| BNB Smart Chain | 56 | ✓ | ✓ | ✓ | ✓ | ✓ |
| Avalanche C-Chain | 43114 | ✓ | ✓ | ✓ | ✓ | ✓ |
| Robinhood Chain | 4663 | ✓ | ✓ | ✓ | ✓ | ✓ |

✓ = code at the shared address (checked with `eth_getCode` on 2026-09-29). The official address list names the AllowanceHolder and the OpenRouter on all eight chains (Robinhood Chain is on the chain-support page). The RFQVaultExecutor and BungeeReceiver addresses come from their explorer-verified sources and from the measured events; the docs describe BungeeReceiver as "the same address on all supported chains via CREATE3".

---

## 12. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| AllowanceHolder, OpenRouter, CalldataExecutor | Immutable | EIP-1967 implementation slot empty; no owner function. | None |
| RFQVaultExecutor | Immutable, owned | EIP-1967 implementation slot empty. `owner()` = `0xf76e73720ec93df7e823b755e10c38a877c34bd5`, which is also its `solverSigner()`: an EOA (no code; nonce 221 on Ethereum). | The owner EOA: `setSolverSigner`, `rescueFunds`. The signer key authorizes `fulfil`, `refund`, `markForRefund` and `performActions`. Two-step ownership (`nominateOwner` / `claimOwner`). |
| BungeeReceiver | Immutable, owned, role-based | EIP-1967 implementation slot empty. `owner()` = `0xb0bbff6311b7f245761a7846d3ce7b1b100c1836`, an EOA (no code; nonce 909 on Ethereum). `SOLVER_SIGNER()` = `0xf76e73720ec93df7e823b755e10c38a877c34bd5` on Ethereum and Base, `0xb0bbff6311b7f245761a7846d3ce7b1b100c1836` on Robinhood Chain. | Owner EOA and roles (`grantRole` / `revokeRole`); `setSolverSigner`. |

---

## 13. Detection invariants & gotchas

1. **Source leg = `RequestExecuted` at the OpenRouter.** It is emitted once per route, for every bridge and for same-chain swaps too (`swap`). Classify with the called function (`bridge`, `swapAndBridge`, `swap`) or with the next hop of the funds in the same transaction.
2. **Bungee RFQ route = `ERC20Deposited` / `NativeDeposited` + `RequestExecuted` with the same `quoteId`.** In the pinned window `NativeDeposited` had 0 logs on all eight chains: native input is swapped or wrapped before the vault.
3. **`Fulfilled` is the payout; `Refunded` is the refund.** Both are emitted by the vault of the chain where the money leaves; `Fulfilled` happens on the destination chain, `Refunded` on the source chain.
4. **`tx.to` is the AllowanceHolder and `tx.from` may be a solver.** Destination payouts (`fulfil`) are sent by solver EOAs; source routes by the user or by the user's smart wallet.
5. **Fees move inside the route.** OpenRouter sends the fee (`fee.receiver`, `fee.amount`) as a separate `Transfer` in the source transaction, before the bridge call.
6. **Same addresses on all eight chains.** Key on `(chain, address)` anyway: the vault balances and the signer settings are per chain (the BungeeReceiver signer differs on Robinhood Chain).
7. **Single-key administration.** The owners of the RFQVaultExecutor and BungeeReceiver are EOAs, and one EOA both owns the vault and signs its payouts. A signed `performActions` can move any vault balance.
8. **Admin triggers.** `OwnerNominated`, `OwnerClaimed`, `SolverSignerUpdated`, `RoleGranted`, `RoleRevoked` at the vault and at BungeeReceiver; calls of `setSolverSigner` (`0x444eac45`), `rescueFunds` (`0x6ccae054`) and `performActions` (`0x875083e2`) on the vault.

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_OPENROUTER_REQUEST_EXECUTED    = '\xe2a752598b97815acff854b1d0b6d5c7f33b848bcbb541df9b76038287282467'
TOPIC_RFQ_VAULT_ERC20_DEPOSITED      = '\x4794ca0cccec06c04b75a414e5ff1bd4594b69f002410d24a64b80fb2c22d456'
TOPIC_RFQ_VAULT_NATIVE_DEPOSITED     = '\xac7e8d562498c85420402ece84172b01e90e7850d0c5a9e4a8bb3d222a781e84'
TOPIC_RFQ_VAULT_FULFILLED            = '\x91170d66098c018af5b9550ca3307975a6933fc4c2491ea3d53ca41e31397af2'
TOPIC_RFQ_VAULT_REFUNDED             = '\x684124fe07c7e7d736370cfbc8905ea5ae8cc20708f029683464a4d4e8e0631e'
TOPIC_BUNGEE_DEST_PAYLOAD_EXECUTED   = '\x3dc8d383f6fa8bb849751a10c2748f761d7f5324b44a111ae03da9a1a4e1aea6'
TOPIC_BUNGEE_SOLVER_SIGNER_UPDATED   = '\x8571408339f42cc299c2d129ef0bfd1886efd25a6e69fddee915e25d8f216282'
TOPIC_SOCKET_OWNER_NOMINATED         = '\x906a1c6bd7e3091ea86693dd029a831c19049ce77f1dce2ce0bab1cacbabce22'
TOPIC_SOCKET_OWNER_CLAIMED           = '\xfbe19c9b601f5ee90b44c7390f3fa2319eba01762d34ee372aeafd59b25c7f87'

-- ===== Selectors (chain-agnostic) =====
SEL_ALLOWANCE_HOLDER_EXEC           = '\x2213bc0b'
SEL_OPENROUTER_BRIDGE               = '\xb18248d5'
SEL_OPENROUTER_SWAP                 = '\x1bb1a530'
SEL_OPENROUTER_SWAP_AND_BRIDGE      = '\x324012e2'
SEL_OPENROUTER_PERFORM_ACTIONS      = '\x197aa51e'
SEL_RFQ_RECEIVE_ERC20               = '\x823b01f9'
SEL_RFQ_RECEIVE_NATIVE              = '\x3345e738'
SEL_RFQ_FULFIL                      = '\x39520192'
SEL_RFQ_SWAP_AND_FULFIL             = '\xc02409ba'
SEL_RFQ_MARK_FOR_REFUND             = '\x27963312'
SEL_RFQ_REFUND                      = '\x612406de'
SEL_RFQ_SET_SOLVER_SIGNER           = '\x444eac45'
SEL_BUNGEE_EXECUTE_DEST_PAYLOAD     = '\x2b7ead8b'

-- ===== Addresses (same on all eight chains) =====
ETH_SOCKET_ALLOWANCE_HOLDER          = '\x50c4e75a512f2a14a7b304787adf79c4531a5909'
ETH_SOCKET_OPENROUTER                = '\x50cfe7c1938db66a1a6d2e86d36f39fbef3d5c4a'
ETH_SOCKET_RFQ_VAULT_EXECUTOR        = '\x97caca78ac2a94c67643d07843f85afaa44a3ea5'
ETH_SOCKET_BUNGEE_RECEIVER           = '\x8a774c1b73998a54ff09341f3cff8a0010bba7f1'
ETH_SOCKET_CALLDATA_EXECUTOR         = '\xc914815120fa5a7e05748398c9fdf1d1b2729008'
BASE_SOCKET_ALLOWANCE_HOLDER         = '\x50c4e75a512f2a14a7b304787adf79c4531a5909'
BASE_SOCKET_OPENROUTER               = '\x50cfe7c1938db66a1a6d2e86d36f39fbef3d5c4a'
BASE_SOCKET_RFQ_VAULT_EXECUTOR       = '\x97caca78ac2a94c67643d07843f85afaa44a3ea5'
BASE_SOCKET_BUNGEE_RECEIVER          = '\x8a774c1b73998a54ff09341f3cff8a0010bba7f1'
BASE_SOCKET_CALLDATA_EXECUTOR        = '\xc914815120fa5a7e05748398c9fdf1d1b2729008'
ARB_SOCKET_ALLOWANCE_HOLDER          = '\x50c4e75a512f2a14a7b304787adf79c4531a5909'
ARB_SOCKET_OPENROUTER                = '\x50cfe7c1938db66a1a6d2e86d36f39fbef3d5c4a'
ARB_SOCKET_RFQ_VAULT_EXECUTOR        = '\x97caca78ac2a94c67643d07843f85afaa44a3ea5'
ARB_SOCKET_BUNGEE_RECEIVER           = '\x8a774c1b73998a54ff09341f3cff8a0010bba7f1'
ARB_SOCKET_CALLDATA_EXECUTOR         = '\xc914815120fa5a7e05748398c9fdf1d1b2729008'
OP_SOCKET_ALLOWANCE_HOLDER           = '\x50c4e75a512f2a14a7b304787adf79c4531a5909'
OP_SOCKET_OPENROUTER                 = '\x50cfe7c1938db66a1a6d2e86d36f39fbef3d5c4a'
OP_SOCKET_RFQ_VAULT_EXECUTOR         = '\x97caca78ac2a94c67643d07843f85afaa44a3ea5'
OP_SOCKET_BUNGEE_RECEIVER            = '\x8a774c1b73998a54ff09341f3cff8a0010bba7f1'
OP_SOCKET_CALLDATA_EXECUTOR          = '\xc914815120fa5a7e05748398c9fdf1d1b2729008'
POLY_SOCKET_ALLOWANCE_HOLDER         = '\x50c4e75a512f2a14a7b304787adf79c4531a5909'
POLY_SOCKET_OPENROUTER               = '\x50cfe7c1938db66a1a6d2e86d36f39fbef3d5c4a'
POLY_SOCKET_RFQ_VAULT_EXECUTOR       = '\x97caca78ac2a94c67643d07843f85afaa44a3ea5'
POLY_SOCKET_BUNGEE_RECEIVER          = '\x8a774c1b73998a54ff09341f3cff8a0010bba7f1'
POLY_SOCKET_CALLDATA_EXECUTOR        = '\xc914815120fa5a7e05748398c9fdf1d1b2729008'
BNB_SOCKET_ALLOWANCE_HOLDER          = '\x50c4e75a512f2a14a7b304787adf79c4531a5909'
BNB_SOCKET_OPENROUTER                = '\x50cfe7c1938db66a1a6d2e86d36f39fbef3d5c4a'
BNB_SOCKET_RFQ_VAULT_EXECUTOR        = '\x97caca78ac2a94c67643d07843f85afaa44a3ea5'
BNB_SOCKET_BUNGEE_RECEIVER           = '\x8a774c1b73998a54ff09341f3cff8a0010bba7f1'
BNB_SOCKET_CALLDATA_EXECUTOR         = '\xc914815120fa5a7e05748398c9fdf1d1b2729008'
AVAX_SOCKET_ALLOWANCE_HOLDER         = '\x50c4e75a512f2a14a7b304787adf79c4531a5909'
AVAX_SOCKET_OPENROUTER               = '\x50cfe7c1938db66a1a6d2e86d36f39fbef3d5c4a'
AVAX_SOCKET_RFQ_VAULT_EXECUTOR       = '\x97caca78ac2a94c67643d07843f85afaa44a3ea5'
AVAX_SOCKET_BUNGEE_RECEIVER          = '\x8a774c1b73998a54ff09341f3cff8a0010bba7f1'
AVAX_SOCKET_CALLDATA_EXECUTOR        = '\xc914815120fa5a7e05748398c9fdf1d1b2729008'
RH_SOCKET_ALLOWANCE_HOLDER           = '\x50c4e75a512f2a14a7b304787adf79c4531a5909'
RH_SOCKET_OPENROUTER                 = '\x50cfe7c1938db66a1a6d2e86d36f39fbef3d5c4a'
RH_SOCKET_RFQ_VAULT_EXECUTOR         = '\x97caca78ac2a94c67643d07843f85afaa44a3ea5'
RH_SOCKET_BUNGEE_RECEIVER            = '\x8a774c1b73998a54ff09341f3cff8a0010bba7f1'
RH_SOCKET_CALLDATA_EXECUTOR          = '\xc914815120fa5a7e05748398c9fdf1d1b2729008'
ETH_SOCKET_SOLVER_SIGNER_EOA         = '\xf76e73720ec93df7e823b755e10c38a877c34bd5'
```

---

## 15. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` / `[0:4]` from the explorer-verified ABIs (OpenRouter, RFQVaultExecutor, BungeeReceiver) and from the verified AllowanceHolder source (`IAllowanceHolder.exec` and `transferFrom`, dispatched in the fallback).
- **Addresses:** from the Socket docs (AllowanceHolder and OpenRouter on every chain; CREATE3 note for BungeeReceiver), from `BungeeReceiver.CALLDATA_EXECUTOR()` (the docs show only a shortened CalldataExecutor address), and from the emitters of the measured events. Each existence-checked with `eth_getCode` on all eight chains.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, address-wide log scans of each contract):**

  | Event (address-wide scan) | ETH | Base | Arb | OP | Poly | BNB | Avax | RH |
  |---|---|---|---|---|---|---|---|---|
  | `RequestExecuted` | 321 | 554 | 347 | 57 | 153 | 335 | 44 | 504 |
  | `ERC20Deposited` | 177 | 261 | 201 | 0 | 76 | 157 | 0 | 404 |
  | `NativeDeposited` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
  | `Fulfilled` | 121 | 345 | 210 | 0 | 57 | 298 | 0 | 283 |
  | `Refunded` | 0 | 7 | 2 | 0 | 0 | 4 | 0 | 2 |
  | `DestPayloadExecuted` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

  Other emitters of `RequestExecuted` in the same window (topic scan from any emitter): Ethereum 15 from `0x559B33F816Fb4d6b24731D77eDB5C5b2f5F5B624`; Ethereum 1 from `0x089068A2Dc4E5B901Cb431F4136168984715B985`; Base 2 from `0x559B33F816Fb4d6b24731D77eDB5C5b2f5F5B624`; BNB 2 from `0x559B33F816Fb4d6b24731D77eDB5C5b2f5F5B624`. These two addresses are verified as `GatewayRouter` ("Forwarding proxy for Gateway-related contracts", event `RequestExecuted(bytes32 indexed orderId)`, called through an AllowanceHolder). They are not in the Socket address lists, and this work did not attribute them to Socket: filter `RequestExecuted` by the OpenRouter address.
- **Sample transactions read:** Ethereum `0x91496022d3f6c37a9774dd6f215b9f83526f2efc752dcd222447c7c7b2f3359f` (`exec` on the AllowanceHolder; 5,000 USDT user → OpenRouter, swap to USDC, 12.498485 USDC fee transfer, 4,986.892472 USDC OpenRouter → RFQVaultExecutor, `ERC20Deposited` and `RequestExecuted` with the same `quoteId` `0xe58881883600402f8cbbc7748a3272b18cfb42a804375053d07398a49d8408c7`); Base `0x6a2c85332f723737255e203b3ca8047e85d3dd183de5ccd3bde440062e55e16c` (a solver calls `fulfil`; 19.201587 USDC vault → receiver, `Fulfilled`); Base `0x12364a25be3017113f77e99eab62678c6e40e50819f3fd6ad8cdb7aa30969509` (`refund`; 0.074527 USDC vault → user, `Refunded`).

Authoritative sources:
- Socket docs — [contract addresses](https://docs.socket.tech/integrate/contract-addresses) · [chain support](https://docs.socket.tech/about/chain-support) · [OpenRouter swap v3 reference](https://docs.socket.tech/openrouter-swap-v3-user-reference) · [destination payload execution](https://docs.socket.tech/integrate/integration-guides/additional-guides/destination-payload) · [docs index](https://docs.socket.tech/llms.txt)
- Explorers (verified sources) — [OpenRouter on Etherscan](https://etherscan.io/address/0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a) · [RFQVaultExecutor on Blockscout](https://eth.blockscout.com/address/0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5) · [BungeeReceiver on Blockscout](https://eth.blockscout.com/address/0x8a774c1b73998a54ff09341f3cff8a0010bba7f1) · [AllowanceHolder on Blockscout](https://eth.blockscout.com/address/0x50c4E75a512F2A14A7b304787Adf79C4531A5909) · [Robinhood Chain Blockscout](https://robinhoodchain.blockscout.com/address/0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a)
