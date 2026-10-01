# Squid — reference index

Squid is a cross-chain swap router. It has no bridge of its own: it routes through Axelar (most volume), Circle CCTP, Chainflip and, for intents, its own CORAL / Squid Intents settlement.

**Status:** all constants verified on 2026-09-29 to 2026-10-01 against live RPC on the eight target chains, verified contract source (Blockscout) and the Squid docs and API.

| File | Component | Contracts | Proxy pattern | Chains (of the 8) | Status |
|------|-----------|-----------|---------------|-------------------|--------|
| [router.md](router.md) | **SquidRouter** (Axelar `bridgeCall` / `callBridgeCall` paths, CCTP, Chainflip, destination executor), SquidMulticall, SquidFeeCollector | `0xce16F69375520ab01377ce7B88f5BA8C48F8D666` on the seven listed chains; `0x2B4d4Cf15dAD79D3426D19674Bd237C1dc9144aa` on Robinhood Chain (unlisted, no Axelar wiring) | Axelar `Proxy` (EIP-1967 slot), per-chain implementation, per-chain owner Safe | ETH, Base, Arb, OP, Poly, BNB, Avax; Robinhood partial | Live |
| [coral.md](coral.md) | **Squid Intents / CORAL**: V1 Spokes (`OrderCreated`, `OrderFilled`, `TokensReleased`) with a Hub on Fantom; V2 TEE-settled intents | Six verified Spokes, one address each on all seven chains | Immutable | ETH, Base, Arb, OP, Poly, BNB, Avax; not Robinhood | V1 dormant (0 events in the pinned window); V2 has no contract events |

## Cross-cutting facts

1. **Squid emits no source-chain event on its Axelar path.** The source leg is the AxelarGateway's `ContractCallWithToken` with `sender` = the SquidRouter. Gateway topics and per-chain gateway addresses are in [`../axelar/core.md`](../axelar/core.md).
2. **Link keys.** Axelar path: `payloadHash = keccak256(payload)`, on chain on both sides (gateway topic2 on the source, router topic1 on the destination). Express path: `commandId` ties the express payout to the later repayment on the destination chain. Coral V1: `orderHash`, on chain on both sides. Coral V2: Squid `quoteId`, off chain only (Squid status API).
3. **Squid's chain ids are Axelar chain names** in the router path (`Ethereum`, `base`, `Arbitrum`, `optimism`, `Polygon`, `binance`, `Avalanche`). Coral V1 orders use EVM chain ids. The Coral V1 Hub is on Fantom (Axelar name `Fantom`, LayerZero eid `30112`).
4. **One router address, seven implementations.** The proxy address is the same on the seven listed chains; each chain has its own implementation (constructor immutables) and its own owner Safe. Robinhood Chain has a router at the docs' "alternate" address with placeholder Axelar addresses and an EOA owner; Squid does not list the chain.
5. **Shared topic0 with other Axelar apps.** `ExpressExecutedWithToken`, `ExpressExecutionWithTokenFulfilled` and the other express events are generic Axelar express-executable events. Filter on the emitter.
6. **Count each transfer once.** An express transfer has a payout (`ExpressExecutedWithToken` + `CrossMulticallExecuted`) and a later repayment to the express executor (`ExpressExecutionWithTokenFulfilled`). A Coral V1 order has a payout (`OrderFilled`) and a later release to the solver (`TokensReleased`).
