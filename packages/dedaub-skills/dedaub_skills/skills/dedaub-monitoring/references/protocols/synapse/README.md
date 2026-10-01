# Synapse Protocol — reference index

Monitoring-grade on-chain reference for **Synapse Protocol** across Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137). All topic0s/selectors recomputed locally with keccak256 and cross-checked against live `eth_getLogs`; all addresses existence-checked via `eth_getCode` on each chain's RPC on 2026-06-09; proxy impls read live from the EIP-1967 slot.

Synapse runs **two parallel bridge product lines** plus a Circle-CCTP path. Split into one file per generation:

| File | Component / generation | Status | Chains (of the 7) |
|------|------------------------|--------|--------------------|
| [synapse.md](./synapse.md) | **Classic mint/burn bridge**: `SynapseBridge` (TokenDeposit/Redeem/RedeemV2/Mint/Withdraw), the `SynapseBridgeAdapter` (LayerZero V2 transport, `TokenSent`/`TokenReceived`), `SynapseRouter`, `L1/L2BridgeZap`, `SwapFlashLoan` nUSD/nETH nexus pools, `SynapseCCTP` summary. | Live (adapter-routed transfers + CCTP volume) | bridge and adapter on **all 7**; CCTP 6/7 (not BNB); zaps 6/7 (not Base); **not on Robinhood (4663)** |
| [rfq.md](./rfq.md) | **RFQ / intent bridge**: `FastBridge` (FastBridgeV2), `FastBridgeRouterV2`, `FastBridgeInterceptor`. The current primary path. | Live (primary volume, esp. Base) | **5/7** — ETH, BNB, Arbitrum, Optimism, Base (**NOT Avalanche, Polygon, Robinhood**) |

## Cross-cutting facts

- **Two cross-chain join keys, by product:** classic bridge → `bytes32 kappa` (indexed in destination `TokenMint`/`TokenWithdraw`); RFQ → `bytes32 transactionId` (indexed in every RFQ event). The classic origin events do **not** carry the kappa. On the adapter path the kappa is the LayerZero `guid`, which the source `TokenSent` and the destination `TokenReceived` carry in their data.
- **The classic bridge now moves through the `SynapseBridgeAdapter`** (`0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA` on all 7, LayerZero V2). Its source leg emits only the adapter's `TokenSent` (the bridge emits no `TokenDeposit`/`TokenRedeem`); its destination leg emits `TokenReceived` in the same transaction as the bridge's `TokenMint`/`TokenWithdraw`. In the pinned 12-hour window of 2026-09-28 every destination leg on the seven chains came through the adapter.
- **Robinhood Chain (4663): no Synapse deployment.** `eth_getCode` is `0x` at every Synapse address, and 4663 is not in the SDK chain list (synapse.md §4.7).
- **Origin vs destination is encoded in the event name, not the contract.** Classic: `*Deposit`/`*Redeem` (origin) vs `*Mint`/`*Withdraw` (destination). RFQ: `BridgeRequested`/`Proof*`/`Deposit*` (origin) vs `BridgeRelayed` (destination).
- **Shared vanity singletons** (same literal address on every chain that has them): `SynapseRouter` `0x7E7A0e201FD38d3ADAA9523Da6C109a07118C96a`, `SynapseBridgeAdapter` `0x5Ba000Bb06230E0582e111F08e1f2F2F200005BA`, `SynapseBridge` **impl** `0x5b0000258c622551a1c7c45b9f860ef90200005b`, `SynapseCCTPRouter` `0xd5a597d6e7ddf373a92C8f477DAAA673b0902F48`, `FastBridge` `0x5523D3c98809DdDB82C686E152F5C58B1B0fB59E`, `FastBridgeRouterV2` `0x00cD000000003f7F682BE4813200893d4e690000`. The **`SynapseBridge` proxy is the only per-chain-unique core address** — key bridge presence on `(chainId, proxy)`.
- **Implementation-drift trap:** every `SynapseBridge` proxy's live EIP-1967 impl is the shared `0x5b00…005b`, which does **not** match the per-chain `SynapseBridge_Implementation.json` in the repo (those are stale). Always read the slot.
- **Recorded chain absences** (`0x` on `eth_getCode`, not gaps): FastBridge — none on Avalanche/Polygon; SynapseCCTP — none on BNB; L2BridgeZap — none on Base; nETH market — none on BNB/Polygon; nUSD pool — none on Base.
- **Counterparty chains outside the seven:** Synapse spans ~25 chains. Classic-bridge `chainId` and RFQ `destChainId` fields routinely reference Fantom, Harmony, Boba, Moonbeam, Moonriver, Aurora, Metis, Cronos, Canto, Klaytn, DFK, Blast, Linea, Scroll, Berachain, HyperEVM, Unichain, Worldchain, etc. An out-of-set destination id is a valid bridge leg, not bad data.
- **Generic topic0 collisions:** the nexus-pool `TokenSwap` (`0xc6c1…f8a36`) is the Saddle-fork canonical topic (shared by every Saddle/StableSwap fork); the proxy `Upgraded`/`RoleGranted` topics are OZ-standard. Always filter on `(chainId, address, topic0)`.

Canonical sources: [`synapsecns/synapse-contracts`](https://github.com/synapsecns/synapse-contracts), [`synapsecns/sanguine`](https://github.com/synapsecns/sanguine), [Synapse docs](https://docs.synapseprotocol.com/reference/contract-addresses).
