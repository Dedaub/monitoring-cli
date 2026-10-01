# deBridge — reference index

deBridge has two product lines on the same chains. **DLN** (deBridge Liquidity Network) is an intent bridge: a maker locks tokens in an order escrow, a solver pays the receiver on the destination chain, and the escrow repays the solver later. **DMP** (deBridge Messaging Protocol, `DeBridgeGate`) is a validator-signed lock-and-mint bridge and message layer; DLN uses it to carry its unlock and cancel messages. Index both.

**Status:** all constants verified on 2026-09-29 against live RPC on the eight target chains, the deBridge deployed-contracts pages, and the verified sources (`debridge-finance/dln-contracts`, `debridge-finance/debridge-contracts-v1`, Blockscout).

| File | Product | Contracts | Proxy pattern | Chains (of the 8) | Status |
|------|---------|-----------|---------------|-------------------|--------|
| [dln.md](dln.md) | **DLN** (orders, fills, unlocks, cancels, hooks) | DlnSource, DlnDestination, DeBridgeRouter (Crosschain Forwarder), DlnExternalCallAdapter, ExternalCallExecutor | EIP-1967 transparent (OpenZeppelin v4; v5 on Robinhood Chain) | **All 8**, same main literals | Live on all 8 |
| [dmp.md](dmp.md) | **DMP** (deBridgeGate, dePort deAssets) | DeBridgeGate, CallProxy, SignatureVerifier, DeBridgeTokenDeployer, DeBridgeToken, WethGate | EIP-1967 transparent; deAssets are beacon proxies | **All 8**; the Gate has its own address on Base | Live on all 8 |

## Chain ids (deBridge "Internal Chain ID")

DLN orders (`giveChainId`, `takeChainId`) and Gate messages (`chainIdTo`, `chainIdFrom`) carry deBridge chain ids. For the eight target chains they equal the EVM chain id:

| Chain | EVM chain id | deBridge chain id | Flat fee per order or message (docs) |
|-------|-------------:|------------------:|--------------------------------------|
| Ethereum | 1 | 1 | 0.001 ETH |
| Base | 8453 | 8453 | 0.001 ETH |
| Arbitrum One | 42161 | 42161 | 0.001 ETH |
| Optimism | 10 | 10 | 0.001 ETH |
| Polygon PoS | 137 | 137 | 0.5 MATIC |
| BNB Smart Chain | 56 | 56 | 0.005 BNB |
| Avalanche C-Chain | 43114 | 43114 | 0.05 AVAX |
| Robinhood Chain | 4663 | 4663 | 0.001 ETH |

Other chains of the deBridge network (not targets): Solana `7565164` (`0x736f6c`, non-EVM), Linea 59144, Arc 5042, and chains whose deBridge id differs from their EVM chain id: Story 1514 → `100000013`, Cronos 25 → `100000019`, HyperEVM 999 → `100000022`, TRON 728126428 → `100000026`, Injective 1776 → `100000029`, Monad 143 → `100000030`, MegaETH 4326 → `100000031`. `DlnSource.getChainId()` on Robinhood Chain returns 4663 (live read).

## Cross-cutting facts

1. **One transfer, two link keys.** DLN: `orderId` joins `CreatedOrder` (source) → `FulfilledOrder` (destination) → `SentOrderUnlock` (destination) → `ClaimedUnlock` (source). DMP: `submissionId` joins `Sent` (source chain of the message) → `Claimed` (destination chain of the message). A DLN unlock carries both: `SentOrderUnlock.submissionId` = `Sent.submissionId`. Both keys are on chain on both sides.
2. **No DLN event parameter is indexed.** Filter DLN logs by `(emitter, topic0)` and decode `orderId` from the data. The Gate indexes `debridgeId`, `chainIdTo` / `chainIdFrom` and `receiver`, but not `submissionId`.
3. **Who pays whom.** DLN source leg: maker → `DlnSource` (escrow). DLN destination leg: solver (or `DeBridgeRouter`) → receiver, with no transfer out of `DlnDestination`. Escrow payout: `DlnSource` → solver (`ClaimedUnlock`). Refund: `DlnSource` → cancel beneficiary (`ClaimedOrderCancel`). DMP: lock into the Gate or burn of a deAsset; release from the Gate or mint of a deAsset.
4. **Most Gate traffic is DLN settlement.** 65 of the 67 Ethereum `Sent` logs in the pinned window came from `DlnDestination` with amount 0. Classify by `Sent.nativeSender` before counting Gate transfers.
5. **Same literal, different role per chain — key on `(chain, address)`.** `0x43dE2d77BF8027e25dBD179B491e8d64f38398aA` is the Gate on seven chains and a ProxyAdmin on Base; `0xc1656B63D9EEBa6d114f6bE19565177893e5bCBF` is the Gate on Base and a DeBridgeToken contract elsewhere; `0xe4427af3555cd9303d728c491364fadfdd7494fe` is the Gate ProxyAdmin on seven chains and the Gate implementation on Base.
6. **Robinhood Chain is deployed but governed differently.** DLN and the Gate are live there (207 `CreatedOrder`, 309 `FulfilledOrder`, 44 Gate `Sent` in the pinned window). The hooks use `0xE93356b0b87c71A7F4957DCEBEd05BefA8cB624a` (adapter) and `0x05bD82Dbb7c5C2Cf571112bD1ad4e7c02E10eBEA` (executor), the proxies are OpenZeppelin v5 with one ProxyAdmin each, and every ProxyAdmin there is owned by an EOA (5-threshold Safes on the seven other chains).
7. **Two event schemas in DLN history.** `CreatedOrder` gained `bytes metadata` at Ethereum block 18,092,917 and `FulfilledOrder` gained `uint256 actualFulfillAmount` at Ethereum block 24,447,763. Both legacy topic0 values are in [dln.md](dln.md) §1.

All topic0 values and selectors in both files were recomputed with `keccak256`, and each selector was found in the implementation bytecode. Addresses were existence-checked with `eth_getCode` on all eight chains, and the proxy slots and owners were read live.
