# Butter Network (MAP Protocol) — reference index

**Status:** verified against live RPC on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon and the canonical `butternetwork/butter-router-contracts` + `butternetwork/butter-mos-contracts` repos on 2026-06-09.

Butter Network is an **omnichain swap + bridge aggregator built on top of the MAP Protocol relay chain** (MAPO, EVM chainId **22776**). Every cross-chain transfer is a *hub-and-spoke* flow: a user calls a **ButterRouter** on the source chain, which calls the **MAP Omnichain Service (MOS)** bridge; MOS emits a `MessageOut`, a MAP-relay light-client verifies the source-chain proof on the relay (`BridgeAndRelay`), settles value out of per-token vaults, and re-emits a `MessageRelay`/`MessageIn` to the destination chain where the destination MOS + **Receiver** complete the swap. There is **no direct chain-to-chain trust**: the MAP relay chain is always in the middle.

This protocol splits cleanly into a **bridge layer** (MOS, two generations) and a **router layer** (ButterRouter, four versions). One file per generation/component:

| File | Component | Generation / status | Canonical contract(s) | Key shared address (all 7 chains) |
|------|-----------|---------------------|----------------------|-----------------------------------|
| [mos-v3.md](mos-v3.md) | MAP Omnichain Service **V3** (current bridge) | **live, primary** — all activity flows here | `Bridge` (spoke) / `BridgeAndRelay` (relay) / `FeeService` / `AuthorityManager` / `TokenRegisterV3` / `VaultTokenV3` | bridgeProxy `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` |
| [mos-v2.md](mos-v2.md) | MAP Omnichain Service **V2** (legacy bridge) | **deprecated** — deployed but ~0 recent activity | `MAPOmnichainServiceV2` / `MAPOmnichainServiceRelayV2` / `TokenRegisterV2` | mosProxy `0xfeB2b97e4Efce787c08086dC16Ab69E063911380` |
| [router.md](router.md) | ButterRouter V2 / V3 / V31 / V4 + Receiver/ReceiverV2 + SwapAdapter | **V3/V31/V4 live, V2 legacy** | `ButterRouterV3/V31/V4`, `ReceiverV2`, `SwapAggregator` | ButterRouterV3 `0xEE030ec6F4307411607E55aCD08e628Ae6655B86` |

## Cross-cutting facts

1. **Deterministic shared addresses.** The MOS V3 bridge, every router version, the FeeService, and the AuthorityManager use the **same address on every EVM chain** (CREATE2/CREATE3-style deterministic deploy). The vanity bridge address `0x0000317Bec…` (leading zeros) is the single strongest tell. **Always key on `(chainId, address)`** — the same literal is a different deployment per chain.

2. **Per-chain implementation behind a shared proxy.** Although the MOS V3 proxy address is identical everywhere, its EIP-1967 implementation differs per chain (spokes run `Bridge`, the MAP relay runs `BridgeAndRelay`). See mos-v3.md §Proxies.

3. **The "real user" is `initiator`/`from`, not `msg.sender`.** Routers forward to MOS, MOS forwards to Receiver; the relayer/router is the immediate caller. Attribute to the `initiator`/`from`/`referrer` fields in the events.

4. **`orderId` (bytes32) is the cross-chain join key.** A single transfer emits `SwapAndBridge` (router) + `MessageOut` (source MOS) sharing one tx, then `MessageRelay`/`DepositIn` (relay) and `MessageIn` + `RemoteSwapAndCall` (destination) — all carry the same `orderId`.

5. **Avalanche has a partial footprint.** Of the routers, only **ButterRouterV31 + Receiver + SwapAdapterV3** are deployed on Avalanche (no V2/V3/V4 router, no MOS V2); MOS V3 is fully present. Recorded per-chain in each file.

6. **Counterparty chains outside the seven targets.** Butter bridges to many chains the seven targets connect *to* but that are not in the target set: the **MAP relay chain (MAPO, 22776)** itself, plus zkSync Era (324), Linea, Scroll, Mantle, Blast (81457), Merlin, B2, Bevm, AINN, Conflux, Klaytn/Kaia, X Layer, Unichain, zkLink, Monad, **Tron** (non-EVM addresses), **NEAR** (separate Rust contracts), Bitcoin and Solana (vault-token denominated). These are recorded as findings where relevant.

## Authoritative sources

- Router repo: <https://github.com/butternetwork/butter-router-contracts> (`deployments/deploy.json`, `contracts/`)
- Bridge repo: <https://github.com/butternetwork/butter-mos-contracts> (`evmv3/`, `evmv2/`, `near/`)
- Docs: <https://docs.butternetwork.io> · MAP Protocol developer docs: <https://docs.mapprotocol.io>
- Explorers: Etherscan, Basescan, BscScan, Snowscan, Arbiscan, Optimistic Etherscan, Polygonscan; MAP relay explorer <https://maposcan.io>
