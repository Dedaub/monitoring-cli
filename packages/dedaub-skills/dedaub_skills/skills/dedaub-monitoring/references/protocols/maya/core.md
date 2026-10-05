# Maya Protocol (MAYAChain) — Topics, Selectors, Addresses (Ethereum + Arbitrum; NOT Base, BNB, Avalanche, Optimism, Polygon, Robinhood, Arc)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the MAYANode API (`/mayachain/inbound_addresses`, `/mayachain/vaults/asgard`, `/mayachain/mimir`, `/mayachain/lastblock`, MAYAChain height 18,599,455), the verified router sources (Blockscout: `MAYAChain_Router` on Ethereum, `ArbRouter` on Arbitrum) and `gitlab.com/mayachain/ethereum/eth-router`. Topics and selectors recomputed as `keccak256(sig)`; addresses existence-checked with `eth_getCode`; sample receipts decoded. Halt state, vault set and router activity re-checked on 2026-10-05 (MAYAChain height 18,687,064).
**Scope:** the Maya router contracts and the Asgard vault EOAs on Maya's two EVM chains: Ethereum (1) and Arbitrum One (42161). Base, BNB Smart Chain, Avalanche, OP Mainnet, Polygon, Robinhood Chain (4663) and Arc (5042) have no Maya deployment (`eth_getCode` = `0x` at both router addresses on Robinhood and Arc, 2026-10-05). The other leg of most swaps is a non-EVM chain (Bitcoin, Dash, Zcash, Cardano, THORChain, Radix, Kujira). Topics and selectors are chain-agnostic; addresses are network-specific.

Maya Protocol is a fork of THORChain with the same EVM model: an immutable, ownerless **router** takes the deposit and emits the memo, and threshold-signature **Asgard vault EOAs** hold the funds and sign the payouts. The router is a copy of THORChain Router V4: it keeps ERC-20 tokens itself with a per-vault allowance and forwards native ETH to the vault. Every topic and selector below equals THORChain's V4.1 value (see the `thorchain` reference).

**Maya is live again (halted 2026-08-18 → restarted 2026-09-30).** On 18 August 2026 an exploit drained about 1.7 million USD (CoinDesk, 19 August 2026), and Maya halted its chain: the last pre-halt router events are on 2026-08-18 near 18:00 UTC (Ethereum block 25,783,600, Arbitrum block 495,904,377), and the API still showed `halted: true` with mimir `HALTCHAINGLOBAL = 1` on 2026-09-29. The routers resumed on 2026-09-30: first post-halt Ethereum `Deposit` 2026-09-30 09:47 UTC (block 26,089,493), first Arbitrum `TransferOut` 2026-10-01 (block 510,670,267). On 2026-10-05 the API shows `halted: false` for ETH and ARB, and mimir `HALTCHAINGLOBAL`, `HALTETHCHAIN`, `HALTETHTRADING`, `HALTARBCHAIN`, `HALTARBTRADING`, `HALTSIGNINGETH`, `HALTSIGNINGARB` and `HALTCHURNING` are all 0. A churn to a new vault set followed on 2026-10-03/04 (§3).

---

## 0. Contract families & versions

| Contract | Chain | Role | State on 2026-10-05 |
|----------|-------|------|---------------------|
| **MAYAChain_Router** (header "Router Version: 4.0", solc 0.8.13) | Ethereum `0xe3985E6b61b814F7Cdb188766562ba71b446B46d` | Deposit and payout router; holds ERC-20 tokens; Etherscan label "Maya Protocol: ETH Router v4" | Live router in the API; chain live |
| **ArbRouter** (solc 0.8.9, contract comment "MAYAChain_Router") | Arbitrum `0x700E97ef07219440487840Dc472E7120A7FF11F4` | Same functions and events on Arbitrum | Live router in the API; chain live |
| **Asgard vaults** | 4 EOAs, the same address on Ethereum and Arbitrum (§3) | Hold funds, sign `transferOut` | 2 `ActiveVault`, 2 `RetiringVault` (set rotated 2026-10-03/04) |

**Maya chain names for the target chains.** Maya names chains; it has no numeric ids.

| Target chain | Maya chain | Memo short code | State |
|--------------|-----------|-----------------|-------|
| Ethereum (1) | `ETH` | `e` = `ETH.ETH` | live |
| Arbitrum One (42161) | `ARB` | `a` = `ARB.ETH` | live |
| Base, BNB, Avalanche, OP Mainnet, Polygon, Robinhood Chain, Arc | — | — | not supported |

Other Maya short codes: `b` BTC.BTC, `d` DASH.DASH, `z` ZEC.ZEC, `k` KUJI.KUJI, `x` XRD.XRD, `r` THOR.RUNE, `m` MAYA.CACAO. The same letters mean other assets on THORChain (`a` = AVAX.AVAX, `d` = DOGE.DOGE, `x` = XRP.XRP there).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Emitter = the Maya router of each chain. The events are byte-identical to THORChain Router V4.1.

| topic0 | Event | Side |
|--------|-------|------|
| `0xef519b7eb82aaf6ac376a6df2d793843ebfd593de5f1a0601d3cc6ab49ebb395` | `Deposit(address indexed to, address indexed asset, uint256 amount, string memo)` | **Source leg.** `to` = the vault; `asset` = `0x0000000000000000000000000000000000000000` for ETH; the destination is in `memo`. |
| `0xa9cd03aa3c1b4515114539cd53d22085129d495cb9e9f9af77864526240f1bf7` | `TransferOut(address indexed vault, address indexed to, address asset, uint256 amount, string memo)` | **Destination leg** (`memo` = `OUT:<hash>`) and refund (`REFUND:<hash>` in the shared design; not seen in the last 100 router logs). |
| `0x8e5841bcd195b858d53b38bcf91b38d47f3bc800469b6812d35451ab619c6f6c` | `TransferOutAndCall(address indexed vault, address target, uint256 amount, address finalAsset, address to, uint256 amountOutMin, string memo)` | Payout through a whitelisted aggregator (`swapOut`), ETH only. |
| `0x05b90458f953d3fcb2d7fb25616a2fddeca749d0c47cc5c9832d0266b5346eea` | `TransferAllowance(address indexed oldVault, address indexed newVault, address asset, uint256 amount, string memo)` | Churn: moves the ERC-20 allowance between vaults (**status only**; the tokens stay in the router). |
| `0x281daef48d91e5cd3d32db0784f6af69cd8d8d2e8c612a3568dca51ded51e08f` | `VaultTransfer(address indexed oldVault, address indexed newVault, (address asset, uint256 amount)[] coins, string memo)` | `returnVaultAssets` batch; ERC-20 part is an allowance move; `msg.value` goes to the new vault. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | Emitted by the token: user → router on deposit, router → recipient on payout. |

**Topic collisions.** THORChain's routers, THORChain's stagenet routers and `Harbor_RouterV5` (`0x1f21d09c65bc8af92634dcd5a100b6d04f0c81c3` on Ethereum) emit the same topics. In the pinned (halt-time) window every Ethereum `Deposit` and `TransferOut` came from THORChain or Harbor, none from Maya. Always filter on the Maya router address.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Same selectors on both routers.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x44bc937b` | `depositWithExpiry(address vault, address asset, uint256 amount, string memo, uint256 expiration)` | **User entry.** Payable; reverts after `expiration`. Emits `Deposit`. |
| `0x1fece7b4` | `deposit(address vault, address asset, uint256 amount, string memo)` | ETH sent to `vault` with `send`; ERC-20 pulled into the router (`transferFrom(user, router)`). Emits `Deposit`. |
| `0x574da717` | `transferOut(address to, address asset, uint256 amount, string memo)` | **Payout**, called by a vault EOA. ERC-20: router → `to`. ETH: `msg.value` to `to` with 2,300 gas; on failure it bounces to the vault and the event still fires. |
| `0x4039fd4b` | `transferOutAndCall(address target, address finalToken, address to, uint256 amountOutMin, string memo)` | Aggregator payout. Emits `TransferOutAndCall`. |
| `0x1b738b32` | `transferAllowance(address router, address newVault, address asset, uint256 amount, string memo)` | Churn or router migration. |
| `0x2923e82e` | `returnVaultAssets(address router, address asgard, (address asset, uint256 amount)[] coins, string memo)` | Batch vault return. Emits `VaultTransfer`. |
| `0x03b6a673` | `vaultAllowance(address vault, address token)` | View: ERC-20 amount the router holds for `vault`. |
| `0x48c314f4` | `swapOut(address finalToken, address to, uint256 amountOutMin)` | Callback the router calls on the aggregator `target`. |

---

## 3. Addresses — Ethereum (chain ID 1)

Router verified via `eth_getCode` on 2026-09-29. Vault set from `/mayachain/inbound_addresses` and `/mayachain/vaults/asgard` on 2026-10-05 (all `eth_getCode` = `0x`, nonces read the same day). Vaults rotate at every churn: re-read `/mayachain/vaults/asgard` before you key an alert on a vault address.

| Role | Address | One-liner |
|------|---------|-----------|
| **MAYAChain_Router** | `0xe3985E6b61b814F7Cdb188766562ba71b446B46d` | 8,466 B; immutable; holds the ETH-chain ERC-20 pool. |
| Asgard vault (active, current inbound) | `0x522c1f808051d6864385f7c1bc44f038e84eb10f` | EOA, nonce 16. |
| Asgard vault (active) | `0xd978d31701290079d440805541d0a0538b8dddd4` | EOA, nonce 1. |
| Asgard vault (retiring) | `0xc361fce3f5be675da662633b7ec15d62f65dd90a` | EOA, nonce 101. |
| Asgard vault (retiring) | `0xffe34eb4575c8ced78f34d74595696d3dca6f81b` | EOA, nonce 106. |
| Former vaults (retired; absent from `/mayachain/vaults/asgard` on 2026-10-05) | `0x8c92a5bc08f91a4f8b8a723acab1ed0393c0e79f`, `0x728ac02dbfe50554a1ad7a9e5a1cbd4937e5cbfb`, `0x847168b8399776483e433c5dcf941e63bd4c67a5`, `0x6fe0bd875d439c4960ce09dc3fb38eeb1c3353ee` | The 2026-09-29 vault set; keep only for history queries. |

## 4. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **ArbRouter** | `0x700E97ef07219440487840Dc472E7120A7FF11F4` | 6,752 B; immutable; same ABI as the Ethereum router. |
| Asgard vaults | the four EOAs of §3 (same addresses; current inbound `0x522c1f808051d6864385f7c1bc44f038e84eb10f` on ARB too) | Nonces on Arbitrum (2026-10-05): `0x522c1f808051d6864385f7c1bc44f038e84eb10f` 5, `0xd978d31701290079d440805541d0a0538b8dddd4` 3, `0xc361fce3f5be675da662633b7ec15d62f65dd90a` 79, `0xffe34eb4575c8ced78f34d74595696d3dca6f81b` 85. The four former vaults of §3 are retired on Arbitrum as well. |

---

## 5. Cross-chain summary

| Chain | ID | Router | Vault EOAs | `Deposit` / `TransferOut` at the router since the 2026-09-30 restart (to 2026-10-05) |
|-------|----|--------|------------|-----------------------------------------------|
| Ethereum | 1 | `0xe3985E6b61b814F7Cdb188766562ba71b446B46d` | 4 (nonces > 0) | 127 / 686 (+2,113 `TransferAllowance`, churn) |
| Arbitrum One | 42161 | `0x700E97ef07219440487840Dc472E7120A7FF11F4` | 4 (nonces > 0) | 49 / 357 (+4,228 `TransferAllowance`, churn) |
| Base | 8453 | — (`0x` at both router addresses) | nonce 0 | — |
| BNB Smart Chain | 56 | — | nonce 0 | — |
| Avalanche C-Chain | 43114 | — | nonce 0 | — |
| OP Mainnet | 10 | — | nonce 0 | — |
| Polygon PoS | 137 | — | nonce 0 | — |
| Robinhood Chain | 4663 | — | nonce 0 | — |
| Arc | 5042 | — (`0x` at both router addresses) | — | — |

The two routers are at different addresses; the vault EOAs share one address on both chains (one key).

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| MAYAChain_Router, ArbRouter | **Immutable**, no proxy | Verified source has no owner, admin or upgrade function; EIP-1967 slot empty | None on chain. A router change is a new deployment announced through the MAYANode API (`router` field). |
| Asgard vaults | EOAs (TSS keys) | `eth_getCode` = `0x`, nonce > 0 | Rotated at each churn by MAYAChain. |

Admin control lives on MAYAChain mimir: `HALTCHAINGLOBAL`, `HALT<CHAIN>CHAIN`, `HALT<CHAIN>TRADING`, `HALTSIGNING<CHAIN>`, `HALTCHURNING`. Read them at `/mayachain/mimir`.

---

## 7. Detection invariants & gotchas

1. **Filter on the Maya router address.** The topics collide with THORChain, THORChain stagenet and Harbor routers.
2. **Link key = the memo hash.** Payout memo `OUT:<HASH>` (64 upper-case hex characters, no `0x`) = the inbound transaction hash on the source chain; lower-case it and add `0x` for an EVM source. Decoded sample: Arbitrum payout `0xd49ab39037b0fef5837f16ab64f555b8c196e2212f06787a487ea8c641cc5cad` carries `OUT:A275D628F8A5C316E5E48CE3198CD03FD1B559DD68065FB594B2EF2E0F14C568`.
3. **`Deposit.to` is the vault.** The depositor is `tx.from` or the ERC-20 `Transfer.from`; aggregators often stand between (the sample Ethereum deposit `0xd055694c0485a3fb8c7eb6899fd20b44cefceecee63f0352d245253c25dccb7d` came through `0x9f87361621cdf7a5cdc8b194aaeb1e1800fb5fd8`, which pulled USDT from the user and paid an affiliate fee). Because vaults rotate, key alerts on the router address, not on `Deposit.to`.
4. **Custody.** ERC-20 tokens sit in the router, not in the vaults: user → router on deposit, router → recipient on payout. ETH goes to the vault EOA, and a vault pays ETH through `transferOut` with `msg.value`.
5. **Native deposits can skip the router** (the shared THORChain design: the observer also tracks native transfers to a vault EOA with the memo in the input). Watch plain ETH transfers into the vault EOAs.
6. **Memos are not all exits.** In the last 50 logs of each router: Ethereum `=` 30, `TRADE+` 8; Arbitrum `=` 2, `TRADE+`/`trade+` 5, `+` (add liquidity) 1. `TRADE+` credits a MAYAChain trade account and has no payout.
7. **Short codes are Maya-specific.** `a` = ARB.ETH, `d` = DASH.DASH, `x` = XRD.XRD, `z` = ZEC.ZEC; the sample deposit memo `=:z:t1ZkzR72J5JsnPrv5iyVQgN3w5bdiVhoA2N:...` is a swap of USDT to a Zcash address.
8. **Halt state.** Read mimir before you interpret flow. While `HALTCHAINGLOBAL` (or `HALT<CHAIN>CHAIN`) = 1, a new `Deposit` at a Maya router is an anomaly worth an alert: the funds are not swapped. Any `TransferOut` or vault outflow during a halt is also an anomaly (signing should be stopped). All these flags were 0 on 2026-10-05.
9. **Vault rotation (churn).** Funds move from `RetiringVault` to `ActiveVault` EOAs (`TransferAllowance`, `VaultTransfer`, plain ETH transfers); the 2026-10-03/04 churn emitted 2,113 (Ethereum) and 4,228 (Arbitrum) `TransferAllowance` events. These are not exits.
10. **Large-transfer and drain triggers.** `TransferOut.amount` per `asset` at both routers, ERC-20 balance drops at the routers, and ETH outflows from the vault EOAs that do not go through the router.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Router topics (same as THORChain V4.1) =====
TOPIC_DEPOSIT                    = '\xef519b7eb82aaf6ac376a6df2d793843ebfd593de5f1a0601d3cc6ab49ebb395'
TOPIC_TRANSFER_OUT               = '\xa9cd03aa3c1b4515114539cd53d22085129d495cb9e9f9af77864526240f1bf7'
TOPIC_TRANSFER_OUT_AND_CALL      = '\x8e5841bcd195b858d53b38bcf91b38d47f3bc800469b6812d35451ab619c6f6c'
TOPIC_TRANSFER_ALLOWANCE         = '\x05b90458f953d3fcb2d7fb25616a2fddeca749d0c47cc5c9832d0266b5346eea'
TOPIC_VAULT_TRANSFER             = '\x281daef48d91e5cd3d32db0784f6af69cd8d8d2e8c612a3568dca51ded51e08f'
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors =====
SEL_DEPOSIT_WITH_EXPIRY          = '\x44bc937b'
SEL_DEPOSIT                      = '\x1fece7b4'
SEL_TRANSFER_OUT                 = '\x574da717'
SEL_TRANSFER_OUT_AND_CALL        = '\x4039fd4b'
SEL_TRANSFER_ALLOWANCE           = '\x1b738b32'
SEL_RETURN_VAULT_ASSETS          = '\x2923e82e'
SEL_VAULT_ALLOWANCE              = '\x03b6a673'
SEL_SWAP_OUT                     = '\x48c314f4'

-- ===== Ethereum (1) ===== (vault set of 2026-10-05; vaults rotate at each churn)
ETH_MAYA_ROUTER                  = '\xe3985e6b61b814f7cdb188766562ba71b446b46d'
ETH_MAYA_VAULT_ACTIVE_1_EOA      = '\x522c1f808051d6864385f7c1bc44f038e84eb10f'
ETH_MAYA_VAULT_ACTIVE_2_EOA      = '\xd978d31701290079d440805541d0a0538b8dddd4'
ETH_MAYA_VAULT_RETIRING_1_EOA    = '\xc361fce3f5be675da662633b7ec15d62f65dd90a'
ETH_MAYA_VAULT_RETIRING_2_EOA    = '\xffe34eb4575c8ced78f34d74595696d3dca6f81b'
-- retired (2026-09-29 set, gone by 2026-10-05): '\x8c92a5bc08f91a4f8b8a723acab1ed0393c0e79f'
--   '\x728ac02dbfe50554a1ad7a9e5a1cbd4937e5cbfb' '\x847168b8399776483e433c5dcf941e63bd4c67a5' '\x6fe0bd875d439c4960ce09dc3fb38eeb1c3353ee'

-- ===== Arbitrum One (42161) =====
ARB_MAYA_ROUTER                  = '\x700e97ef07219440487840dc472e7120a7ff11f4'
-- vault EOAs on Arbitrum: the same four addresses as on Ethereum
ARB_MAYA_VAULT_ACTIVE_1_EOA      = '\x522c1f808051d6864385f7c1bc44f038e84eb10f'
ARB_MAYA_VAULT_ACTIVE_2_EOA      = '\xd978d31701290079d440805541d0a0538b8dddd4'
ARB_MAYA_VAULT_RETIRING_1_EOA    = '\xc361fce3f5be675da662633b7ec15d62f65dd90a'
ARB_MAYA_VAULT_RETIRING_2_EOA    = '\xffe34eb4575c8ced78f34d74595696d3dca6f81b'
-- Base, BNB, Avalanche, OP Mainnet, Polygon, Robinhood Chain, Arc: no Maya contract
```

---

## 9. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` / `[0:4]` from the verified router sources (`Coin` written as `(address,uint256)`). The GitLab `eth-router` `contracts/MAYAChain_Router.sol` equals the Ethereum verified source except for a trailing newline. That repository's README lists an older event set (`Deposit(address asset, uint value, string memo)`); the deployed code does not use it.
- **Addresses:** router and vaults from `/mayachain/inbound_addresses` and `/mayachain/vaults/asgard` (two active, two retiring vaults; vault set re-read 2026-10-05 after the churn; routers ETH `0xe3985E6b61b814F7Cdb188766562ba71b446B46d`, ARB `0x700E97ef07219440487840Dc472E7120A7FF11F4`). Each address checked with `eth_getCode` on all eight chains: router code only on its own chain; vault EOAs with nonces > 0 only on Ethereum and Arbitrum. No earlier Maya EVM router appears in the vault data; earlier routers, if any, are unverified.
- **Halt (2026-09-29):** API `halted: true` on every chain; mimir `HALTCHAINGLOBAL` = 1, `HALTETHTRADING` = 1; `/mayachain/lastblock` last observed inbounds ETH 25,783,602 and ARB 495,904,377; latest pre-halt router logs on Blockscout at Ethereum block 25,783,600 (2026-08-18 17:54:47 UTC) and Arbitrum block 495,904,377 (2026-08-18 17:59:39 UTC).
- **Restart (2026-10-05):** API `halted: false` for ETH and ARB; the mimir halt keys listed above are 0; `/mayachain/lastblock` last observed inbounds ETH 26,124,142 and ARB 511,863,770. Router logs after the halt block, read from indexed chain data: Ethereum `Deposit` 127 (first block 26,089,493, 2026-09-30 09:47 UTC), `TransferOut` 686, `TransferAllowance` 2,113 (2026-10-03/04); Arbitrum `Deposit` 49, `TransferOut` 357 (first block 510,670,267, 2026-10-01), `TransferAllowance` 4,228.
- **Activity during the halt (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):** `Deposit` and `TransferOut` from any emitter: Ethereum 687 and 1,128, none from the Maya router (THORChain V4.1 and Harbor only); Arbitrum 0 and 0. `TransferAllowance` and `VaultTransfer`: 0 on both chains.
- **Sample receipts** (pre-halt; both vaults now retired): Ethereum deposit `0xd055694c0485a3fb8c7eb6899fd20b44cefceecee63f0352d245253c25dccb7d` (USDT 246.048260 user → aggregator → router; `Deposit.to` = vault `0x8c92a5bc08f91a4f8b8a723acab1ed0393c0e79f`); Arbitrum payout `0xd49ab39037b0fef5837f16ab64f555b8c196e2212f06787a487ea8c641cc5cad` (vault `0x728ac02dbfe50554a1ad7a9e5a1cbd4937e5cbfb` calls `transferOut`; USDC 381.551614 router → recipient).

Authoritative sources:
- MAYANode API — [inbound_addresses](https://mayanode.mayachain.info/mayachain/inbound_addresses) · [vaults/asgard](https://mayanode.mayachain.info/mayachain/vaults/asgard) · [mimir](https://mayanode.mayachain.info/mayachain/mimir) · [lastblock](https://mayanode.mayachain.info/mayachain/lastblock)
- Repositories — [mayachain/ethereum/eth-router](https://gitlab.com/mayachain/ethereum/eth-router) · [mayanode](https://gitlab.com/mayachain/mayanode) · docs repository [one-stop-shop](https://gitlab.com/mayachain/docs/one-stop-shop) (`concepts/transaction-memos.md`, `concepts/memo-length-reduction.md`)
- Docs — [EVM Chains](https://docs.mayaprotocol.com/mayachain-dev-docs/protocol-development/chain-clients/evm-chains)
- Explorers — [Etherscan router](https://etherscan.io/address/0xe3985e6b61b814f7cdb188766562ba71b446b46d) · [Blockscout Ethereum](https://eth.blockscout.com/address/0xe3985E6b61b814F7Cdb188766562ba71b446B46d) · [Blockscout Arbitrum](https://arbitrum.blockscout.com/address/0x700E97ef07219440487840Dc472E7120A7FF11F4)
- Halt report — [CoinDesk, 2026-08-19](https://www.coindesk.com/markets/2026/08/19/maya-protocol-exploit-drains-bitcoin-and-other-assets-as-pool-value-drops-usd11-million)
