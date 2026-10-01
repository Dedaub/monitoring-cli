# Socket / Bungee — reference index (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche + Robinhood Chain)

**Socket** (the product was called **Bungee** for most of its life; `docs.bungee.exchange` now serves the Socket docs) is a bridge aggregator and intent router. It moves value across chains through third-party bridges (Across, CCTP, Stargate, Mayan, Relay, native rollup bridges and others) and through its own solver network. Three contract generations are on chain; each has its own events and its own link key.

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the official docs (`docs.socket.tech`: contract addresses, chain support, OpenRouter reference, destination payload guide), the `SocketDotTech/bungee-contracts-public` repository (SocketGateway sources and `deployments/<network>.json`), and the explorer-verified sources of the deployed contracts. Topics and selectors recomputed as `keccak256(signature)`; every address existence-checked with `eth_getCode`.

| File | Generation | Contracts | Link key | Chains (of the 8) | Activity in the pinned window |
|------|-----------|-----------|----------|-------------------|-------------------------------|
| [openrouter.md](openrouter.md) | **Socket v3 / OpenRouter** (current API routes) | AllowanceHolder, OpenRouter, RFQVaultExecutor, BungeeReceiver, CalldataExecutor | `quoteId` (the request hash) | all 8, same addresses | 2,315 `RequestExecuted` on the eight chains |
| [gateway.md](gateway.md) | **SocketGateway** (Socket v2, "legacy routes") | SocketGateway, route implementations, SocketDeployFactory | none on chain (the underlying bridge's id) | 7 (not Robinhood Chain) | 270 `SocketBridge` on the seven chains |
| [bungee-auto.md](bungee-auto.md) | **Bungee Auto** (inbox and solver auctions) | BungeeInbox, BungeeGateway, request routers, Switchboard | `requestHash` | 7 (not Robinhood Chain) | 0 logs; last logs on Ethereum 2026-08-27 (BungeeGateway) and 2026-08-25 (BungeeInbox) |

## The flow per generation

| Generation | Source leg (funds enter) | Destination leg (payout) | Refund / cancel |
|------------|--------------------------|--------------------------|-----------------|
| OpenRouter, Bungee RFQ route | AllowanceHolder `exec` → OpenRouter pulls the user's token → optional swap → fee transfer → RFQVaultExecutor `receiveERC20` / `receiveNative`: `ERC20Deposited` / `NativeDeposited` (vault) and `RequestExecuted` (OpenRouter) | The solver calls `fulfil` / `swapAndFulfil` on the RFQVaultExecutor of the destination chain: vault → receiver `Transfer`, `Fulfilled(quoteId, token, amount, receiver)` | `markForRefund`, then `refund` on the source-chain vault: vault → user `Transfer`, `Refunded(quoteId, token, amount, receiver)` |
| OpenRouter, third-party bridge | Same entry; OpenRouter calls the bridge (for example an Across deposit or a CCTP burn) and emits `RequestExecuted(quoteId)` | The bridge's own payout event. With a destination payload, BungeeReceiver emits `DestPayloadExecuted(quoteId, success)` | The bridge's own refund |
| SocketGateway | A call with a route id (`executeRoute` or the route-id fallback) → the route (by `DELEGATECALL`) calls the bridge → `SocketBridge` at the gateway | The bridge's own payout event. No Socket event. | The bridge's own refund |
| Bungee Auto | `BungeeInbox.createRequest` (`SingleOutputRequestCreated`) or a signed Permit2 request; the winning solver extracts the funds on the source BungeeGateway (`RequestExtracted`) | The solver pays on the destination BungeeGateway (`RequestFulfilled`); later the source side settles to the solver (`RequestSettled`) | `SingleOutputRequestWithdrawn` (inbox), `RequestCancelled`, `WithdrawOnDestination` |

## Link keys

- **OpenRouter:** `quoteId` (`bytes32`). The Socket docs define it as the on-chain request hash of an OpenRouter route and the key of `GET /v3/swap/status?quoteId=`. It is topic1 of `RequestExecuted` and data word 0 of the RFQ vault events, so the Bungee RFQ route is linked on chain on both sides (`ERC20Deposited` on the source, `Fulfilled` on the destination, `Refunded` back on the source).
- **Bungee Auto:** `requestHash` (`bytes32`, topic1 of the inbox and gateway request events) on both sides.
- **SocketGateway:** no Socket id on chain. `SocketBridge` records `amount`, `token`, `toChainId`, `bridgeName`, `sender`, `receiver` and a `metadata` word. Link the legs with the underlying bridge's own id from the same transaction.

## Chain ids

Socket uses EVM chain ids on the eight chains (1, 8453, 42161, 10, 137, 56, 43114, 4663). For other chains the Socket docs list: Solana `89999`, Tron `728126428`, Sui `1110006`, Stellar `1110002`, Hypercore `1337`, Citrea `4114`, Tempo `4217`, Arc `5042`.

## Addresses at a glance

| Contract | Address | Chains |
|----------|---------|--------|
| AllowanceHolder (`tx.to` of OpenRouter routes) | `0x50c4E75a512F2A14A7b304787Adf79C4531A5909` | ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| OpenRouter | `0x50cFe7c1938dB66A1a6D2e86D36F39FBef3d5c4a` | ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| RFQVaultExecutor | `0x97caCa78AC2a94c67643d07843F85AFAa44a3ea5` | ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| BungeeReceiver | `0x8a774c1b73998a54ff09341f3cff8a0010bba7f1` | ETH·Base·Arb·OP·Poly·BNB·Avax·RH |
| SocketGateway | `0x3a23F943181408EAC424116Af7b7790c94Cb97a5` | ETH·Base·Arb·OP·Poly·BNB·Avax |
| BungeeInbox | `0x5e0f8e7337c8955d2124b8e85ca74af884b3e124` | ETH·Base·Arb·OP·Poly·BNB·Avax |
| BungeeGateway | one address per chain | see [bungee-auto.md](bungee-auto.md) |

## Cross-cutting facts

1. **Robinhood Chain has only the OpenRouter generation.** SocketGateway and the Bungee Auto contracts have no code there; OpenRouter, the RFQ vault and BungeeReceiver are deployed and active.
2. **`tx.from` is often not the user.** OpenRouter routes arrive through the AllowanceHolder (`tx.to`), and payouts are sent by solver accounts; SocketGateway calls are often made by integrator contracts. Take the user from the event fields and the token transfers (`SocketBridge.sender`, the `input.user` of the OpenRouter call, the source of the `Transfer` into the OpenRouter).
3. **Same address, different contract on another chain.** Bungee Auto deployments reuse deployer nonces per chain, so one address can be, for example, the BungeeGateway on Base and the SwapExecutor on Optimism. Always key on `(chain, address)`.
4. **Admin signals.** SocketGateway: `NewRouteAdded`, `RouteDisabled`, `OwnerNominated`, `OwnerClaimed`. OpenRouter family: `OwnerNominated`, `OwnerClaimed`, `SolverSignerUpdated`, `RoleGranted`, `RoleRevoked`. Bungee Auto: `ImplAdded`, `ImplRemoved`, `RoleGranted`, `RoleRevoked`.
