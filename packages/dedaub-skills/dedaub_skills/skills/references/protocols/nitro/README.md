# Router Nitro (Router Protocol) — monitoring reference index

Verified against live RPC on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon and the canonical `router-protocol/router-contracts` repo on 2026-06-09.

Router Nitro is an **intent-style cross-chain bridge** built on Router Chain. EVM activity splits into two layers, documented in one file each:

| File | Component | What it covers | Status / chains |
|------|-----------|----------------|-----------------|
| [core.md](./core.md) | **AssetForwarder** (Nitro bridge) | `iDeposit`/`iRelay` + message variants; `FundsDeposited` (source) / `FundsPaid` (destination). The primary liquidity-bridge contract. | **Active.** Forwarder live on ETH, Base, BNB, Avalanche, Arbitrum, Optimism. **Polygon forwarder address unverified** (the two known address literals are Gateway-role there). |
| [gateway.md](./gateway.md) | **Gateway** (Router Chain messaging) + **AssetBridge / Voyager** (legacy mint-burn token bridge) | `iSend`/`iReceive`/`iAck`/`updateValset` + `ISendEvent`; AssetBridge `transferToken`/`Execute`/`TokenTransfer`. | Gateway live on **all 7** chains. AssetBridge live on **ETH / Avalanche / Arbitrum only**. |

## Cross-cutting facts every indexer must know

1. **Address-role collision (the #1 trap).** Router reused two address literals with **opposite roles per chain**:

   | Address | ETH | Base | BNB | Avalanche | Arbitrum | Optimism | Polygon |
   |---------|-----|------|-----|-----------|----------|----------|---------|
   | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | **Forwarder** | **Forwarder** | **Forwarder** | Gateway | Gateway | **Forwarder** | Gateway logic |
   | `0x21c1E74CAaDf990E237920d5515955a024031109` | — (`0x`) | **Forwarder** | **Forwarder** | **Forwarder** | **Forwarder** | **Forwarder** | Gateway |
   | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | Gateway | Gateway | Gateway | Gateway impl | Gateway impl | Gateway | — (`0x`) |
   | `0xf0773508c585246bd09bfb401aa18b72685b03f9` | AssetBridge | — | — | AssetBridge | AssetBridge | — | — |

   **Confirm role per chain before trusting an address:** `depositNonce()` answers on an AssetForwarder, `currentVersion()` answers on a Gateway, `transferToken`/`TokenTransfer` identify an AssetBridge. Key everything on `(chainId, address, role)`.

2. **Two AssetForwarder generations coexist** (`0xC21e4ebD…` and `0x21c1E74C…`) — both live on Base/BNB/Optimism. Index both.

3. **A completed bridge spans two chains and two forwarders:** `FundsDeposited` (source) + `FundsPaid` (destination), joined by `(srcChainId, depositId)` and the recomputed `messageHash`. `FundsPaid.forwarder` is the off-chain liquidity provider, not the user; the user is the deposit's `recipient`.

4. **The AssetForwarder is immutable** (no proxy, no `Upgraded`); the **Gateway is upgradeable** (UUPS — watch `Upgraded(address)` `0xbc7cd75a…` + `ValsetUpdatedEvent` `0x20d5dcc8…`).

5. **`recipient`/`destToken` are `bytes`, `destChainIdBytes`/`srcChainId` are `bytes32`** — because counterparty chains include non-EVM networks. Don't cast to `address`/`uint`.

## Counterparty chains outside the seven targets

Router Nitro bridges to many chains beyond the requested seven (recorded as findings, not omissions): canonical L1 anchoring is on **Ethereum**, but the network also connects **zkSync Era, Linea, Blast, Scroll, Polygon zkEVM, Mantle, Manta** and others on the EVM side, plus **non-EVM** counterparties **NEAR, Solana, Tron, Bitcoin, and Cosmos/Osmosis (IBC)** — which is why deposit `recipient`/`destToken` fields are `bytes` and chain ids are `bytes32`-encoded strings. The Router Chain (a Cosmos appchain) is the settlement hub; the EVM Gateway is its on-chain endpoint.

## Authoritative sources
- Canonical contracts: [`router-protocol/router-contracts`](https://github.com/router-protocol/router-contracts)
- SDK (topic constants, pathfinder endpoints): [`@routerprotocol/asset-transfer-sdk-ts`](https://www.npmjs.com/package/@routerprotocol/asset-transfer-sdk-ts)
- Docs: [docs.routerprotocol.com — Asset transfer via Nitro](https://docs.routerprotocol.com/develop/asset-transfer-via-nitro/)
- Live per-chain forwarder registry (incl. Polygon): pathfinder API `https://api-beta.pathfinder.routerprotocol.com/api`
