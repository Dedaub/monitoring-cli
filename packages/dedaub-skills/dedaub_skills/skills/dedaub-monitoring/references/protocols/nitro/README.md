# Router Nitro (Router Protocol) — monitoring reference index

Verified against live RPC on Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon and the canonical `router-protocol/router-contracts` repo on 2026-06-09; extended with the official forwarder list and the Robinhood Chain (4663) check on 2026-10-01.

Router Nitro is an **intent-style cross-chain bridge** built on Router Chain. EVM activity splits into two layers, documented in one file each:

| File | Component | What it covers | Status / chains |
|------|-----------|----------------|-----------------|
| [core.md](./core.md) | **AssetForwarder** (Nitro bridge) | `iDeposit`/`iRelay` + message variants; `FundsDeposited` (source) / `FundsPaid` (destination). The primary liquidity-bridge contract. | **Live code, idle in the pinned window of 2026-09-28.** The official forwarder of each chain (core.md §0.1): ETH `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9`, Base `0x0Fa205c0446cD9EeDCc7538c9E24BC55AD08207f`, OP `0x8201c02d4AB2214471E8C3AD6475C8b0CD9F2D06`, BNB `0x260687eBC6C55DAdd578264260f9f6e968f7B2A5`, Polygon `0x1396F41d89b96Eaf29A7Ef9EE01ad36E452235aE`, Arbitrum `0xEF300Fb4243a0Ff3b90C8cCfa1264D78182AdaA4`, Avalanche `0xF9f4C3dC7ba8f56737a92d74Fd67230c38AF51f2`; two older generations as well. **Not on Robinhood (4663).** |
| [gateway.md](./gateway.md) | **Gateway** (Router Chain messaging) + **AssetBridge / Voyager** (legacy mint-burn token bridge) | `iSend`/`iReceive`/`iAck`/`updateValset` + `ISendEvent`; AssetBridge `transferToken`/`Execute`/`TokenTransfer`. | Gateway live on **all 7** chains (not Robinhood). AssetBridge live on **ETH / Avalanche / Arbitrum only**. |

## Cross-cutting facts every indexer must know

1. **Address-role collision (the #1 trap).** Router reused two address literals with **opposite roles per chain**:

   | Address | ETH | Base | BNB | Avalanche | Arbitrum | Optimism | Polygon |
   |---------|-----|------|-----|-----------|----------|----------|---------|
   | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | **Forwarder** | **Forwarder** | **Forwarder** | Gateway | Gateway | **Forwarder** | Gateway logic |
   | `0x21c1E74CAaDf990E237920d5515955a024031109` | — (`0x`) | **Forwarder** | **Forwarder** | **Forwarder** | **Forwarder** | **Forwarder** | Gateway |
   | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | Gateway | Gateway | Gateway | Gateway impl | Gateway impl | Gateway | — (`0x`) |
   | `0xf0773508c585246bd09bfb401aa18b72685b03f9` | AssetBridge | — | — | AssetBridge | AssetBridge | — | — |

   **Confirm role per chain before trusting an address:** `depositNonce()` answers on an AssetForwarder, `currentVersion()` answers on a Gateway, `transferToken`/`TokenTransfer` identify an AssetBridge. Key everything on `(chainId, address, role)`.

2. **Three AssetForwarder generations coexist.** The official one per chain (core.md §0.1, the bulk of the deposits) plus the older `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` and `0x21c1E74CAaDf990E237920d5515955a024031109` (both on Base/BNB/Optimism). Index all of them. The current generation also has a USDC-over-CCTP path: `iDepositUSDC` → `iUSDCDeposited` (`0x297a8bc8b87367a63661d6429dbab51be5cefd71ce6a3050fa900a8f276d66d9`), paid out by Circle's mint with no Nitro event.

3. **A completed bridge spans two chains and two forwarders:** `FundsDeposited` (source) + `FundsPaid` (destination), joined by `(srcChainId, depositId)` and the recomputed `messageHash`. `FundsPaid.forwarder` is the off-chain liquidity provider, not the user; the user is the deposit's `recipient`.

4. **The AssetForwarder is immutable** (no proxy, no `Upgraded`); the **Gateway is upgradeable** (UUPS — watch `Upgraded(address)` `0xbc7cd75a…` + `ValsetUpdatedEvent` `0x20d5dcc8…`).

5. **`recipient`/`destToken` are `bytes`, `destChainIdBytes`/`srcChainId` are `bytes32`** — because counterparty chains include non-EVM networks. Don't cast to `address`/`uint`.
6. **Robinhood Chain (4663): no Router contract** at any forwarder, Gateway or AssetBridge address, and no row in the official supported-chains table.

## Counterparty chains outside the seven targets

Router Nitro bridges to many chains beyond the requested seven (recorded as findings, not omissions): canonical L1 anchoring is on **Ethereum**, but the network also connects **zkSync Era, Linea, Blast, Scroll, Polygon zkEVM, Mantle, Manta** and others on the EVM side, plus **non-EVM** counterparties **NEAR, Solana, Tron, Bitcoin, and Cosmos/Osmosis (IBC)** — which is why deposit `recipient`/`destToken` fields are `bytes` and chain ids are `bytes32`-encoded strings. The Router Chain (a Cosmos appchain) is the settlement hub; the EVM Gateway is its on-chain endpoint.

## Authoritative sources
- Canonical contracts: [`router-protocol/router-contracts`](https://github.com/router-protocol/router-contracts)
- SDK (topic constants, pathfinder endpoints): [`@routerprotocol/asset-transfer-sdk-ts`](https://www.npmjs.com/package/@routerprotocol/asset-transfer-sdk-ts)
- Docs: [docs.routerprotocol.com — Asset transfer via Nitro](https://docs.routerprotocol.com/develop/asset-transfer-via-nitro/)
- Live per-chain forwarder registry (incl. Polygon): pathfinder API `https://api-beta.pathfinder.routerprotocol.com/api`
