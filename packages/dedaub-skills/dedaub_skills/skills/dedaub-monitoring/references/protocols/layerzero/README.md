# LayerZero — monitoring reference index

Generic cross-chain **messaging** protocol (not a token bridge): it moves arbitrary bytes between chains; token bridging is done by applications built on top (OFT standard). Two coexisting generations. **Status:** verified against live RPC on all 7 target chains + the canonical `LayerZero-Labs` repos and the official deployments metadata registry on 2026-06-09.

| File | Generation | Core contracts | Address model | Status |
|------|-----------|----------------|----------------|--------|
| [v2.md](./v2.md) | **LayerZero V2** (current) | `EndpointV2`, `SendUln302`, `ReceiveUln302`, `ReadLib1002`, `Executor`, `LzExecutor`, `DeadDVN`, `BlockedMessageLib`, `EndpointV2View` | EndpointV2 **deterministic, same on all 7** (`0x1a44…728c`); message libs per-chain | live / primary |
| [v1.md](./v1.md) | **LayerZero V1** (legacy, still live) | `Endpoint`, `UltraLightNodeV2`, `NonceContract`, `SendUln301`/`ReceiveUln301`, `TreasuryV2`, `Relayer`/`RelayerV2` | per-chain; 3 distinct Endpoint literals; heavy address-role collisions | legacy / superseded by V2 |

## Chain coverage (all present on all 7 target chains)

| Chain | ID | V2 eid | V1 chainId | V2 EndpointV2 | V1 Endpoint |
|-------|----|--------|-----------|---------------|-------------|
| Ethereum | 1 | 30101 | 101 | `0x1a44…728c` | `0x66A71D…Cd675` |
| Base | 8453 | 30184 | 184 | `0x1a44…728c` | `0xb631…0dd7` |
| BNB | 56 | 30102 | 102 | `0x1a44…728c` | `0x3c22…cf62` |
| Avalanche | 43114 | 30106 | 106 | `0x1a44…728c` | `0x3c22…cf62` |
| Arbitrum | 42161 | 30110 | 110 | `0x1a44…728c` | `0x3c22…cf62` |
| Optimism | 10 | 30111 | 111 | `0x1a44…728c` | `0x3c22…cf62` |
| Polygon | 137 | 30109 | 109 | `0x1a44…728c` | `0x3c22…cf62` |
| Robinhood Chain | 4663 | 30416 | 416 (deployed, no library registered) | `0x6f475642a6e85809b1c36fa62763669b1b48dd5b` | `0xb6319cc6c8c27a8f5daf0dd3df91ea35c4720dd7` |
| Arc | 5042 | 30417 | 417 (deployed, no library registered) | `0x6f475642a6e85809b1c36fa62763669b1b48dd5b` (same literal as Robinhood) | `0xb6319cc6c8c27a8f5daf0dd3df91ea35c4720dd7` |

**Both V1 and V2 are deployed on all seven older target chains.** **Robinhood Chain (4663)** has V2 at a different EndpointV2 address (`0x6f475642a6e85809b1c36fa62763669b1b48dd5b`, eid 30416, live traffic) and a V1 stack with no registered library (inert) — checked 2026-09-29 ([v2.md](./v2.md) §4.1, [v1.md](./v1.md) §5a). **Arc (5042)** has the same V2 and V1 literals as Robinhood Chain (EndpointV2 `0x6f475642a6e85809b1c36fa62763669b1b48dd5b`, eid 30417, live traffic; V1 eid 417, no library) — checked 2026-10-05 ([v2.md](./v2.md) §4.1a, [v1.md](./v1.md) §5.1a). The EndpointV2 literal alone does not tell Robinhood Chain from Arc: key on the chain id. Major OFT deployments per chain: [v2.md](./v2.md) §4.2; V1 OFT proxies: [v1.md](./v1.md) §5b. LayerZero also connects to ~100+ counterparty chains **outside** the seven (zkSync Era, Linea, Scroll, Blast, Mantle, Metis, Sei, Sonic, Berachain, Aptos, Solana, TON, Hyperliquid, …) — these are recorded in the official registry but are not target chains for this doc set.

## Cross-cutting facts (apply to both files)

1. **Three different chain identifiers.** EVM `chainId` (1, 8453, …); LayerZero **V1 chainId** (`uint16`: 101, 102, …); LayerZero **V2 `eid`** (`uint32`: 30101, 30102, …). They are mutually unrelated — always translate via the registry.
2. **The single outbound event to index** is `Packet(bytes)` on `UltraLightNodeV2` (V1) and `PacketSent(bytes,bytes,address)` on `EndpointV2` (V2). Neither carries indexed destination topics — decode the payload bytes.
3. **`guid` (V2) / packet-payload `nonce` (V1) is the cross-chain join key** between a source send and a destination verify/deliver.
4. **Almost everything is immutable.** EndpointV2 + ULN libraries (V2) and the entire V1 stack have a zero EIP-1967 impl slot. The **only proxies** are the V2 `Executor` and `LzExecutor` (EIP-1967 Transparent, shared ProxyAdmin `0xa367…5ee3` on ETH). "Upgrades" happen by registering a new message library / library version, not by swapping bytecode — watch `LibraryRegistered`/`Default*LibrarySet` (V2) and `NewLibraryVersionAdded`/`Default*VersionSet` (V1).
5. **Shared/colliding addresses are pervasive — key every address on `(chainId, address, role)`.** Notably: V1 `0x66A71D…Cd675` is the Endpoint on ETH, the NonceContract on Base, and the original ULN on the other 5; V2 `0x1322…6e95` is Optimism's SendUln302 and Polygon's ReceiveUln302.
6. **ZRO token** (`0x6985884C4392D348587B19cb9eAAf157F13271cd`, symbol `ZRO`, name `LayerZero`) is a shared-address OFT on all 7 chains; fee-in-ZRO is opt-in per app (EndpointV2 `lzToken()` returns `0x0` on ETH).
7. **BlockedMessageLib** (`0x1ccbf0db9c192d969de57e25b3ff09a25bb1d862`) is the same address on all 7 (V2) and reverts on use — a configured-but-disabled pathway.

## Verification method (both files)

topic0/selectors recomputed locally as `keccak256(signature)` and cross-checked against live `eth_getLogs` (V2 `PacketSent`/`PacketVerified`/`PacketDelivered`/`DVNFeePaid`/`PayloadVerified`; V1 `Packet`/`RelayerParams`) and against deployed-bytecode selector scans on Ethereum. Addresses parsed from the official LayerZero deployments metadata registry and existence-checked via `eth_getCode` on every chain's public RPC (non-empty = present). Proxy classification from live EIP-1967 slot reads. See each file's §"Verification & sources" for the full method and authoritative source links.
