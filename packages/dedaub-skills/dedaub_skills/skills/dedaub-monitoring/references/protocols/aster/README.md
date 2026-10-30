# Aster — Protocol Reference Index

Monitoring-grade references for Aster (the merger of ApolloX and Astherus) across **Ethereum (1), Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), Robinhood Chain (4663), Arc (5042)**. Verified on 2026-10-30 against live RPC, Sourcify-verified sources, the official Aster docs (`docs.asterdex.com`) and the DefiLlama `astherus*` and `apollox` adapters.

Aster is a perpetuals exchange. Its main product (Aster Pro) is an **off-chain order book**: on chain you see only custody deposits and operator-paid withdrawals. Around that custody layer Aster runs a family of yield tokens on BNB and a legacy on-chain perp engine inherited from ApolloX. One file per product line:

| File | Product line | Components | Chains | Status |
|------|--------------|------------|--------|--------|
| [bridge.md](bridge.md) | **Aster Deposit Bridge + legacy ApolloX treasuries** | `AstherusVault` (UUPS), `AstherusTimelock`, `AsterWithdrawValidator`, `ApolloxExchangeTreasury` (v1/v2) | BNB, Ethereum, Arbitrum | **Live.** About $290M (BNB), $120M (Ethereum) and $47M (Arbitrum) in the vaults; about $40M (BNB) and $26M (Ethereum) still in legacy treasuries. |
| [earn.md](earn.md) | **USDF + Aster Earn** | USDF / USDFEarn / WithdrawVault, asUSDF / asUSDFEarn, asBNB / AsBnbMinter / YieldProxy, asBTC / Earn, asCAKE / Minter | BNB only | **Live.** USDF supply 112.4M (Ceffu-custodied USDT backing); asBNB 79.7k. |
| [alp.md](alp.md) | **1001x / ALP diamond (legacy ApolloX)** | EIP-2535 diamond (29 facets on BNB), ALP token | BNB, Arbitrum, Base | **Wind-down.** No trades in the sample window; still holds pool assets. |

Each file follows the same layout: **Topics** → **Function signatures** → **Addresses** → **Cross-chain summary** → **Proxies** → **Detection invariants & gotchas** → **Quick-copy bytea constants** → **Verification & sources**.

## Chain coverage

| Chain (ID) | Deposit vault | Legacy treasury | Earn / USDF | 1001x diamond |
|------------|---------------|-----------------|-------------|---------------|
| BNB (56) | `0x1284…7974` | `0xcEF2…66A4` (v2), `0xe2e9…cd99` (v1) | all of earn.md | `0x1b6F…FEb0` |
| Ethereum (1) | `0x604D…736E` | `0xb40E…c786` | — | — |
| Arbitrum (42161) | `0x9E36…E1d5` | `0xbad4…44ef` | — | `0xb387…0e48` |
| Base (8453) | — | — | — | `0x9D93…DD57` (small) |
| Avalanche, Optimism, Polygon, Robinhood Chain, Arc | — | — | — | — |

Aster also lists Solana and Sui deposit vaults and runs its own Aster Chain; those are not EVM targets. The **ASTER** token is `0x000ae314e2a2172a039b26378814c252734f556a` on BNB (`AsterToken`, non-proxy, supply 8,000,000,000). That address has no code on the other eight target chains.

## Cross-cutting facts worth knowing before you start

- **Key on `(chain, address)`.** The deployer reused nonces across chains. `0x604D…736E`, `0x9E36…E1d5`, `0xb40E…c786`, `0xbad4…44ef`, `0x9D93…DD57`, `0xb387…0e48` and `0xe2e9…cd99` each hold **different, unrelated code** on other chains (code hashes differ). Only the chain named in the docs holds the Aster contract.
- **Shared topic0s.** `Deposit(address,address,bool,uint256,uint256)` `0x18081cde…` is emitted by every `AstherusVault` **and** by the BNB v2 and Arbitrum ApolloX treasuries. The Earn contracts share `RequestWithdraw` / `DistributeWithdraw` / `ClaimWithdraw` / `AddToken`. The USDF `WithdrawVault` emits a non-indexed `Transfer(address,address,uint256)` with the ERC-20 `Transfer` topic0.
- **Native sentinel.** Vault events log native BNB/ETH as `0xfdae1ba7c826abdc4c99903c8056f82a1a04a615` (= `bytes20(keccak256("NATIVE"))`).
- **Governance pattern.** Upgrades go through OpenZeppelin-style timelocks with a **6-hour** minimum delay (`getMinDelay()` = 21,600). Operational admin sits in 4-of-7 Safes: `0xa8c0…1c3f` (BNB and Arbitrum vaults, Earn), `0x1fe3…ecea` (Ethereum vault), `0x60ed…544c` (ApolloX treasuries and diamonds); `0x9b7c…bbec` (3-of-6) owns the Ethereum ApolloX treasury.
- **Withdrawals are signature-gated and rate-limited.** Vault payouts need user, business and ledger signatures (`AsterWithdrawValidator`). An hourly USD cap ($30M BNB/ETH, $20M ARB) auto-pauses the vault (`WithdrawPaused` + `Paused`).
- **USDF is custodial.** Its USDT backing leaves the chain to Ceffu (`TransferToCeffu`). There is no on-chain collateral to reconcile against.

## Verification methodology

- **Topic0 / selectors:** recomputed locally with keccak-256 from Sourcify ABIs. Live presence confirmed with `eth_getLogs` on BNB (publicnode), Ethereum and Arbitrum (Tenderly gateways); counts are in each file.
- **Addresses:** official "Smart Contracts" page + DefiLlama adapters, then on-chain getters (`TIMELOCK_ADDRESS()`, `WITHDRAW_VALIDATOR()`, `USDF_EARN()`, `ASBNB_MINTER()`, `WITHDRAW_VAULT()`, `ceffuAddress()`, `ALP()`, `facetAddresses()`), `getRoleMember`, Safe `getThreshold()` / `getOwners()`, and EIP-1967 slot reads.
- **Chain coverage:** batched `eth_getCode` for 26 addresses on all nine chains, with size and hash comparison.

Sources: [docs.asterdex.com — Smart Contracts](https://docs.asterdex.com/overview/smart-contracts) · [DefiLlama-Adapters](https://github.com/DefiLlama/DefiLlama-Adapters) (`projects/astherus`, `astherus-asBNB`, `astherus-basis-trading`, `astherus-asbtc`, `apollox`) · [Sourcify](https://sourcify.dev/) · [BscScan](https://bscscan.com) · [Etherscan](https://etherscan.io) · [Arbiscan](https://arbiscan.io) · [Basescan](https://basescan.org)
