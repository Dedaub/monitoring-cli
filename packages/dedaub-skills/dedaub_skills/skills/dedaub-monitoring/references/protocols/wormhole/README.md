# Wormhole — reference index

**Wormhole** is a guardian-attested message bus with token products on top. A Core contract on each chain publishes messages (`LogMessagePublished`); 19 guardians sign each one into a VAA; the destination product verifies the VAA on its own chain. Wormhole moves value with several products, each documented in its own file.

**Status:** all constants verified on 2026-09-29 against live RPC on the eight target chains, the canonical `wormhole-foundation/wormhole` and `wormhole-foundation/native-token-transfers` repos, the `wormhole-sdk-ts` address constants, the Executor deployment registry, the Wormholescan NTT API and the Wormhole docs contract-address page. Arc (5042, Wormhole id 71) added 2026-10-05 from `wormhole-sdk-ts` (`chains.ts`, `contracts/core.ts`, `contracts/executor.ts`) and the Executor deployment registry, checked live on `https://rpc.mainnet.arc.io`.

| File | Product | Main contracts | Value model | Chains (of the 8) |
|------|---------|----------------|-------------|-------------------|
| [core.md](core.md) | **Core** (messaging, guardian set, governance) | Core proxy, Guardian Governance, Delegated Guardians, Custom Consistency Level | none (message bus) | **All 8**, Robinhood included; also Arc |
| [token-bridge.md](token-bridge.md) | **Token Bridge** (Portal / Wrapped Token Transfers) | Token Bridge proxy, wrapped tokens, Token Bridge relayers | lock on the origin chain, mint / burn wrapped tokens elsewhere | 7 — **not Robinhood, not Arc** |
| [nft-bridge.md](nft-bridge.md) | **NFT Bridge** | NFT Bridge proxy, wrapped NFTs | ERC-721 lock / mint | 7 — **not Robinhood, not Arc** |
| [relayer.md](relayer.md) | **Wormhole Relayer** (Standard Relayer, being deprecated) and **Executor** | WormholeRelayer, DeliveryProvider, Executor, ExecutorQuoterRouter | fees only (delivery payments) | Relayer 7 (not Robinhood, not Arc); Executor **all 8** and Arc |
| [cctp.md](cctp.md) | **CCTP with Wormhole** (Circle Integration, Circle Relayer, CCTP with Executor) | CircleIntegration proxy, CircleRelayer, CCTPv1/v2WithExecutor | native USDC burn / mint by Circle | 6 — **not BNB, not Robinhood**; Arc has CCTP v2 with Executor only |
| [ntt.md](ntt.md) | **Native Token Transfers** (NTT) | one NttManager + WormholeTransceiver per token per chain; NTT-with-Executor helpers | issuer token locked or burned / unlocked or minted | **All 8**, Robinhood included; Arc has the Executor helpers, no measured manager |

## Wormhole chain ids of the eight target chains

| Chain | EVM chain id | Wormhole chain id | Core |
|-------|--------------|-------------------|------|
| Ethereum | 1 | **2** | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` |
| BNB Smart Chain | 56 | **4** | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` |
| Polygon PoS | 137 | **5** | `0x7A4B5a56256163F07b2C80A7cA55aBE66c4ec4d7` |
| Avalanche C-Chain | 43114 | **6** | `0x54a8e5f9c4CbA08F9943965859F6c34eAF03E26c` |
| Arbitrum One | 42161 | **23** | `0xa5f208e072434bC67592E4C49C1B991BA79BCA46` |
| Optimism | 10 | **24** | `0xEe91C335eab126dF5fDB3797EA9d6aD93aeC9722` |
| Base | 8453 | **30** | `0xbebdb6C8ddC678FfA9f8748f85C815C556Dd8ac6` |
| Robinhood Chain | 4663 | **72** | `0x141fBa8AD5D61bdaB45A047cF60b5Ad9784987FB` |
| Arc | 5042 | **71** | `0xC8aD24fC6063c41cB5C12a8e3851AafC3b3CF027` |

Ids from `core/base/src/constants/chains.ts` of the SDK, confirmed with `chainId()` and `evmChainId()` on each Core. Solana is 1 (the governance chain).

## Cross-cutting facts (read before indexing any file)

1. **One message key for everything:** `(emitterChain, emitterAddress, sequence)` — the Wormhole chain id of the source, the sending contract left-padded to 32 bytes, and the per-sender `sequence` of `LogMessagePublished`. Destination events echo it: Token Bridge `TransferRedeemed`, Circle Integration `Redeemed`, Wormhole Relayer `Delivery` (`sourceChain`, `sequence`), NTT `ReceivedMessage`. NTT adds its own key, the `digest`.
2. **`LogMessagePublished` (`0x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2`) is shared by every application.** Filter on `topic1` = the sending product. In the pinned 12-hour window on Ethereum, the Token Bridge sent 168 of 1,031 messages; Mayan's `SwiftDest` sent 731.
3. **Shared topic0 values across products (key by emitter):** `ContractUpgraded` (`0x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49`) in Core, Token Bridge, NFT Bridge, Relayer and Circle Integration; `TransferRedeemed(uint16,bytes32,uint64)` (`0xcaf280c8cfeba144da67230d9b009c8f868a75bac9a528fa0474be1ba317c169`) in the Token Bridge and two Token Bridge relayers; `Redeemed(uint16,bytes32,uint64)` in the Circle Integration and unrelated integrators; `SwapExecuted` in the legacy relayers and many unrelated contracts.
4. **All core products are EIP-1967 proxies upgraded only by guardian governance VAAs** (emitter chain 1, emitter `0x0000000000000000000000000000000000000000000000000000000000000004`). There is no admin key. Guardian-set rotations, fee changes and `registerChain` emit **no event**; watch the call selectors (core.md §2).
5. **Robinhood Chain (4663, Wormhole id 72):** Core, Executor, NTT-with-Executor v2 and the receive helpers exist; three NTT managers carried traffic in the window. The Token Bridge, NFT Bridge, Wormhole Relayer and every CCTP contract are absent (`eth_getCode` = `0x`, no official listing).
5b. **Arc (5042, Wormhole id 71):** Core, Executor, NTT-with-Executor v2, CCTPv2WithExecutor and the receive helpers exist. The Token Bridge, NFT Bridge, Wormhole Relayer and Circle Integration are absent (`eth_getCode` = `0x`). No log at the Core or the Executor in the ~7 days to 2026-10-05.
6. **Address reuse across chains:** the same literal address can be a different contract on another chain (Polygon Token Bridge = BNB NFT Bridge; several NTT managers, tokens and Circle Integration proxies / implementations). Always key on `(chain, address)`.
7. **Relaying moved to the Executor.** The docs mark the Standard Relayer as being deprecated. In the window, `RequestForExecution` (Executor) appeared 122 times across the eight chains and `SendEvent` (Standard Relayer) 22 times.

Measured activity in the pinned window 2026-09-28 00:00–12:00 UTC (`LogMessagePublished` at the Core): Ethereum 1,031, Base 174, Arbitrum 61, Optimism 9, Polygon 85, BNB 750, Avalanche 62, Robinhood 4. Per-product counts are in each file's Verification section.
