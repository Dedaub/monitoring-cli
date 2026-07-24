# Circle CCTP — reference index

**Cross-Chain Transfer Protocol** (CCTP): native USDC movement by **burn-on-source / mint-on-destination**, gated by Circle's off-chain attester signatures. Two generations coexist on-chain; index both.

**Status:** all constants verified against live RPC on the seven requested chains and the canonical `circlefin/evm-cctp-contracts` repo on 2026-06-09.

| File | Generation | Contracts | Proxy pattern | Chains (of the 7) | Status |
|------|-----------|-----------|---------------|-------------------|--------|
| [v1.md](v1.md) | **CCTP v1** (original) | TokenMessenger, MessageTransmitter, TokenMinter | **Direct deployments — NOT proxies** (impl + admin slots `0x0`) | Ethereum, Avalanche, Optimism, Arbitrum, Base, Polygon — **NOT BNB** (6/7) | Live |
| [v2.md](v2.md) | **CCTP v2** (fast transfers + fees + hooks) | TokenMessengerV2, MessageTransmitterV2, TokenMinterV2, MessageV2 (lib) | TokenMessengerV2 + MessageTransmitterV2 = **EIP-1967 transparent proxies**; TokenMinterV2 = direct | All seven, **including BNB** (7/7; BNB USDC-dormant) | Live |

## Cross-cutting facts (read before indexing either file)

1. **A transfer = two transactions on two chains.** Source emits `DepositForBurn` (TokenMessenger) + `MessageSent(bytes)` (MessageTransmitter); destination emits `MessageReceived` (MessageTransmitter) + `MintAndWithdraw` (TokenMessenger). Join the two sides by the **nonce / message hash**.
2. **`MessageSent(bytes)` has the SAME topic0 `0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036` in v1 AND v2.** This is the one event topic shared across generations — **disambiguate strictly by the emitting contract address** (and the version byte inside the message body: 0 = v1, 1 = v2). Every other workhorse topic0 (`DepositForBurn`, `MintAndWithdraw`, `MessageReceived`) differs between v1 and v2.
3. **`receiveMessage(bytes,bytes)` selector `0x57ecfd28` is identical in v1 and v2.** Again, key by contract.
4. **Address shape differs by generation.** v1 = **unique address per chain** (no vanity, non-deterministic). v2 = **one shared vanity address per contract on every chain** (`0x28b5…cf5d` TokenMessengerV2, `0x81d4…4B64` MessageTransmitterV2, `0xfd78…D002` TokenMinterV2). In both cases **key on `(chainId, address)`**; for v2 the address alone never identifies the chain — read `localDomain()`.
5. **CCTP domain IDs ≠ chain IDs.** Ethereum 0, Avalanche 1, OP Mainnet 2, Arbitrum 3, Base 6, Polygon PoS 7, BNB 17. (Non-target counterparties: Noble 4, Solana 5, Sui 8, Aptos 9, Unichain 10, Linea 11, and more — see v2.md §4.1.)
6. **v1 is non-upgradeable; v2 is.** No `Upgraded(address)` on any v1 contract (direct deploys). On v2, watch `Upgraded` `0xbc7cd75a…2d3b` on the two proxy fronts — the deployed v2 messenger impl currently lacks the "min-fee" surface present in master source, so a future upgrade may add `MinFeeSet`/`setMinFee`.
7. **v2 adds fees.** v2 `DepositForBurn` carries `maxFee`; `MintAndWithdraw` carries `feeCollected`; net to user = `amount − feeCollected`. v1 has no protocol fee.
8. **BNB is the asymmetry.** BNB (domain 17) has only the v2 contracts, and they show **zero USDC `DepositForBurn` activity** over a 200k-block scan (Circle lists BNB as "USYC-only"). v1 is entirely absent from BNB.

Token handled on the requested chains: **native USDC** (6-dec) — ETH `0xA0b8…eB48`, Base `0x8335…2913`, Avax `0xB97E…8a6E`, Arb `0xaf88…5831`, OP `0x0b2C…Ff85`, Polygon `0x3c49…3359`. Per-file detail, selectors, proxy impls and the bytea quick-copy blocks live in [v1.md](v1.md) and [v2.md](v2.md).
