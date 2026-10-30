# Pyth Network — Protocol Reference Index

Monitoring-grade references for Pyth on Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Robinhood Chain (4663) and Arc (5042). Verified on 2026-10-30 against live RPC, the `pyth-network/pyth-crosschain` repo (`contract_manager/src/store/`) and docs.pyth.network.

Pyth is an oracle suite, not one versioned contract. One file for each product:

| File | Product | Key contracts | Chains |
|------|---------|---------------|--------|
| [core.md](core.md) | **Pyth Core** price feeds (pull oracle), Core Compatible, Pyth-operated Wormhole receivers, governance Executor | Pyth Core proxy, Core Compatible proxy, `WormholeReceiver`, `Executor` | Core on **all 9**; Core Compatible on ETH, Base, BNB, Arb, OP, Poly |
| [pro.md](pro.md) | **Pyth Pro** (formerly Lazer) signed-price verifier | `PythLazer` at `0xACeA761c27A909d4D3895128EBe6370FDE2dF481` | ETH, Base, BNB, Arb, Poly, Robin, Arc (OP has an old unlisted build; not Avax) |
| [entropy.md](entropy.md) | **Entropy** randomness (commit-reveal with callback) | `EntropyUpgradable` v2.0.0 | Base, Arb, OP only |

## Products not on the target chains

- **Express Relay:** wound down by Pyth governance decision OP-PIP-124. The EVM contracts are gone from the `pyth-network/per` repo, and the contract store has no EVM Express Relay entry. No target chain has it.
- **Pulse / Scheduler / Echo:** source exists in `pyth-crosschain`, but the contract store lists no mainnet deployment on a target chain.

## Cross-cutting facts

- **Pull model.** Prices reach the chain only when someone calls `updatePriceFeeds` (Core) or `verifyUpdate` (Pro). Core logs `PriceFeedUpdate` (`0xd06a6b7f…`). Pro logs nothing on use.
- **Two signature systems.** Core trusts Wormhole-guardian VAAs, checked by a **Pyth-operated Wormhole receiver** (not the canonical Wormhole Core; see [../wormhole/core.md](../wormhole/core.md)). Pro trusts Pyth signer keys set by `updateTrustedSigner`.
- **Governance.** Pyth Core has `owner() = 0` and acts on governance VAAs from Solana emitter `0x5635979a…2e9e` (`executeGovernanceInstruction`). Pro and Entropy are owned by the per-chain **Executor**, which acts on governance VAAs (`execute(bytes)`).
- **All contracts are EIP-1967 UUPS proxies.** The admin slot is empty everywhere. Watch `Upgraded(address)` (`0xbc7cd75a…`) and Pyth's own `ContractUpgraded(address,address)` (`0x2e4cc16c…`).
- **Address reuse across chains and roles.** Pyth deploys from one key, so one literal can be a different contract on each chain (`0x6E7D74FA…81Bb` is Entropy, Core Compatible, Executor or a receiver). Key every rule by `(chain_id, address)`.
- **Robinhood / Arc lead resolved.** `0x2880aB155794e7179c9eE2e38200202908C17B43` (1,067 B) is a Wormhole-receiver `ReceiverSetup` helper, not a price feed and not an EIP-1967 proxy. The Pyth Core address on Robinhood and Arc is `0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a`.

## Verification methodology

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the canonical Solidity sources. Each was matched as a constant in the live implementation bytecode. Key topics were seen in live `eth_getLogs`.
- **Addresses:** from the `contract_manager` store JSON files and the docs address page. Each was checked with `eth_getCode`, the EIP-1967 slots and characteristic views (`version()`, `owner()`, `wormhole()`, `getDefaultProvider()`, `getCurrentGuardianSetIndex()`) on all nine chains.
- **Gaps:** upgrade history and old implementations were not read (no archive log access on the public RPCs).
