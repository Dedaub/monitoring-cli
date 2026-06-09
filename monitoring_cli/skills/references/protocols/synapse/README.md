# Synapse Protocol — reference index

Monitoring-grade on-chain reference for **Synapse Protocol** across Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137). All topic0s/selectors recomputed locally with keccak256 and cross-checked against live `eth_getLogs`; all addresses existence-checked via `eth_getCode` on each chain's RPC on 2026-06-09; proxy impls read live from the EIP-1967 slot.

Synapse runs **two parallel bridge product lines** plus a Circle-CCTP path. Split into one file per generation:

| File | Component / generation | Status | Chains (of the 7) |
|------|------------------------|--------|--------------------|
| [synapse.md](./synapse.md) | **Classic mint/burn bridge**: `SynapseBridge` (TokenDeposit/Redeem/Mint/Withdraw), `SynapseRouter`, `L1/L2BridgeZap`, `SwapFlashLoan` nUSD/nETH nexus pools, `SynapseCCTP` summary. | Live (mostly destination + CCTP volume) | bridge on **all 7**; CCTP 6/7 (not BNB); zaps 6/7 (not Base) |
| [rfq.md](./rfq.md) | **RFQ / intent bridge**: `FastBridge` (FastBridgeV2), `FastBridgeRouterV2`, `FastBridgeInterceptor`. The current primary path. | Live (primary volume, esp. Base) | **5/7** — ETH, BNB, Arbitrum, Optimism, Base (**NOT Avalanche, Polygon**) |

## Cross-cutting facts

- **Two cross-chain join keys, by product:** classic bridge → `bytes32 kappa` (indexed in destination `TokenMint`/`TokenWithdraw`); RFQ → `bytes32 transactionId` (indexed in every RFQ event). The classic origin events do **not** carry the kappa.
- **Origin vs destination is encoded in the event name, not the contract.** Classic: `*Deposit`/`*Redeem` (origin) vs `*Mint`/`*Withdraw` (destination). RFQ: `BridgeRequested`/`Proof*`/`Deposit*` (origin) vs `BridgeRelayed` (destination).
- **Shared vanity singletons** (same literal address on every chain that has them): `SynapseRouter` `0x7E7A0e20…`, `SynapseBridge` **impl** `0x5b0000258c…00005b`, `SynapseCCTPRouter` `0xd5a5…2F48`, `FastBridge` `0x5523…fB59E`, `FastBridgeRouterV2` `0x00cD…0000`. The **`SynapseBridge` proxy is the only per-chain-unique core address** — key bridge presence on `(chainId, proxy)`.
- **Implementation-drift trap:** every `SynapseBridge` proxy's live EIP-1967 impl is the shared `0x5b00…005b`, which does **not** match the per-chain `SynapseBridge_Implementation.json` in the repo (those are stale). Always read the slot.
- **Recorded chain absences** (`0x` on `eth_getCode`, not gaps): FastBridge — none on Avalanche/Polygon; SynapseCCTP — none on BNB; L2BridgeZap — none on Base; nETH market — none on BNB/Polygon; nUSD pool — none on Base.
- **Counterparty chains outside the seven:** Synapse spans ~25 chains. Classic-bridge `chainId` and RFQ `destChainId` fields routinely reference Fantom, Harmony, Boba, Moonbeam, Moonriver, Aurora, Metis, Cronos, Canto, Klaytn, DFK, Blast, Linea, Scroll, Berachain, HyperEVM, Unichain, Worldchain, etc. An out-of-set destination id is a valid bridge leg, not bad data.
- **Generic topic0 collisions:** the nexus-pool `TokenSwap` (`0xc6c1…f8a36`) is the Saddle-fork canonical topic (shared by every Saddle/StableSwap fork); the proxy `Upgraded`/`RoleGranted` topics are OZ-standard. Always filter on `(chainId, address, topic0)`.

Canonical sources: [`synapsecns/synapse-contracts`](https://github.com/synapsecns/synapse-contracts), [`synapsecns/sanguine`](https://github.com/synapsecns/sanguine), [Synapse docs](https://docs.synapseprotocol.com/reference/contract-addresses).
