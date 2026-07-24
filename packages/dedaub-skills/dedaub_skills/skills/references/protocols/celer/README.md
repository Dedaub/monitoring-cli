# Celer cBridge / IM — Reference Index

Monitoring-grade on-chain reference for the Celer cross-chain stack (the `celer-network/sgn-v2-contracts` deployment). Verified against live RPC on Ethereum, BNB, Avalanche, Arbitrum, Optimism, Polygon, and Base, plus the canonical repo, on 2026-06-09.

| File | Component / generation | Pattern | Chains present (of the 7 targets) | Status |
|------|------------------------|---------|-----------------------------------|--------|
| [core.md](./core.md) | **Liquidity-pool cBridge** (`Bridge`/`Pool`) + **Celer IM `MessageBus`** | Bridge = immutable singleton; MessageBus = Transparent EIP-1967 proxy | Bridge: ETH, BNB, Avax, Arb, OP, Polygon, **Base** (all 7). MessageBus: same 6 **minus Base** | Active |
| [pegged.md](./pegged.md) | **Pegged-token bridge** — `OriginalTokenVault`/`V2` (lock) + `PeggedTokenBridge`/`V2` (mint/burn) | All four immutable singletons (no proxy) | ETH, BNB, Avax, Arb, OP, Polygon (**NOT Base**) | Live but low-volume / winding down |

## Cross-cutting facts

- **Two settlement models.** cBridge (`core.md`) is a **liquidity-network** bridge: `send` on the source chain, `relay` (SGN-signed) pays out from the destination pool. Pegged (`pegged.md`) is **lock-and-mint**: `deposit` locks the original in a vault, `mint` issues a wrapped token on the far chain; `burn` + `withdraw` reverse it.
- **Off-chain attestation, no on-chain src↔dst link.** Both models depend on the off-chain **State Guardian Network (SGN)** to sign cross-chain proofs. Source and destination events are on different chains and are correlated only by a deterministic id (`transferId` / `depositId` / `burnId` / `refId`). Never expect a matching pair in one transaction or on one chain.
- **`Bridge` is the `sigsVerifier`** for the pegged contracts — they all call back into the chain's pool `Bridge.verifySigs`. The `MessageBus` stores pointers (`liquidityBridge`/`pegBridge`/`pegVault`/`pegBridgeV2`/`pegVaultV2`) to all of them.
- **Most contracts are immutable** (`Bridge`, all four pegged contracts: both EIP-1967 slots = `0x0`). **Only `MessageBus` is upgradeable** (Transparent proxy; watch `Upgraded(address)` `0xbc7cd75a…`). A pegged-contract "upgrade" = a fresh deploy + a `Peg*Updated` event on the MessageBus, not an in-place swap.
- **No events are `indexed`-rich.** `Send`/`Relay`/`Deposited`/`Withdrawn`/`Mint`/`Burn` carry all params in `data` (topics length 1). `MessageBus` `Message`/`Executed` index only `sender`/`receiver`. Filter `(address, topic0)` then ABI-decode.
- **Address-literal reuse across chains (NOT CREATE2 vanity).** Several literals name *different contracts* on different chains (e.g. `0x88DCDC47…` = Polygon Bridge AND Avalanche PeggedTokenBridge; `0x5427…1820` = Ethereum Bridge AND Avalanche OriginalTokenVault v1, while the Avalanche Bridge is the different literal `0xef3c714c…e5d4`). **Always key on `(chainId, address)`.**
- **Governance:** `Bridge.owner()` on ETH and Base = `0xf380166f8490f24af32bf47d1aa217fba62b6575`; `MessageBus` upgraded by a per-chain `ProxyAdmin` (see core.md §11).
- **Counterparty chains beyond the 7.** Celer also runs cBridge/MessageBus on Linea (MessageBus `0x6F2bD3De…`), Polygon zkEVM (`0x9Bb46D51…`), zkSync Era (`0x9a98a376…`), and many more, plus non-EVM peg routes (Aptos, Sui, etc.). A `Send`/`Burn` with a `dstChainId`/`toChainId` outside {1, 56, 137, 43114, 42161, 10, 8453} is a valid out-of-scope route, not an anomaly.
