# zkBridge (Polyhedra) — Reference Index

Polyhedra's zkBridge is a **zk-light-client cross-chain stack** with two distinct product lines, each in its own file. Topics/selectors are chain-agnostic; addresses are network-specific. All constants verified against live RPC on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon and Etherscan-verified source on **2026-06-09**.

| File | Component / generation | Key contracts | Status | Chains (of the 7 targets) |
|------|------------------------|---------------|--------|---------------------------|
| [messaging.md](./messaging.md) | **Native zkBridge messaging** (`send`/`validateTransactionProof`) | `ZKBridge` entrypoint, `*BlockUpdater` light clients, `MptVerifier` | live (V2-style, single entrypoint) | **all 7** (entrypoint present on every one) |
| [lightclient.md](./lightclient.md) | **zkLightClient on LayerZero** (Polyhedra as LayerZero oracle/DVN) | `ZkBridgeOracle` (LZ V1), `ZkBridgeOracleV2` (LZ V2 DVN) | live (V2 active; V1 legacy) | **all 7** (both present on every one) |

## Cross-cutting facts (true for both files)

- **One shared ProxyAdmin** `0xe16d201ca134345601631d327a971a3741646b0d` (same literal on all 7 chains) is the EIP-1967 admin of **every** zkBridge proxy: the messaging entrypoint, the proxied BlockUpdaters, the LZ V1 Oracle, and the LZ V2 DVN. A single `Upgraded`/`AdminChanged` source.
- **Deterministic core addresses** (same literal on all 7 chains):
  - `ZKBridge` entrypoint `0xa8a4547Be2eCe6Dde2Dd91b4A5adFe4A043b21C7` (impl `0x6eab43…d43b`, shared)
  - LZ V1 Oracle `0xE014fe8c4d5C23EDB7AC4011F226e869ac7Ef5CC` (impl `0x161d3815…`, shared)
  - LZ V2 DVN `0x8ddF05F9A5c488b4973897E278B58895bF87Cb24` (impl **per-chain**)
- **Three separate chain-id namespaces — never cross-map them:**
  1. **EVM chainId** (1, 56, 137, 43114, 10, 42161, 8453).
  2. **zkBridge-internal id** in the native messaging events/mappings: ETH=2, BSC=3, Polygon=4, Avax=5, OP=7, Arb=8, Base=22 (messaging.md §0).
  3. **LayerZero chainId (v1 `uint16`) / EID (v2 `uint32`)** in the lightclient events.
- **`Upgraded` topic0** to watch on every proxy: `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b`.
- **`OracleNotified` collides by name** between LZ V1 (`0xdaebd99b…`) and LZ V2 (`0x915615b4…`) — different signatures → different topic0s; disambiguate by emitter.
- **No canonical Polyhedra token/NFT bridge contract.** Token/NFT transfers are integrator apps on top of the messaging `send`/`zkReceive`; the Polyhedra Network ERC-20 (`0xc71b5f63…`, on-chain `symbol()` = `ZK`, `name()` = `Polyhedra Network`; `ZKJ` is the older CEX ticker) is governance, not a bridge.
- **Counterparty chains outside the 7:** opBNB, Linea, Scroll, Mantle, Celo, Core, Fantom, Moonbeam, Metis, Gnosis, Manta, Mode, Klaytn, X Layer, Flare, Merlin, Sei, Cyber, Arbitrum Nova (LayerZero side); **Blast** (distinct V2 DVN proxy `0x0ff4cc28…`); plus **Bitcoin** and Polyhedra's **EXPchain** on the native side.
