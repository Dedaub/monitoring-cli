# 1sec (OneSec) — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum; NOT Optimism, Polygon, BNB, Avalanche, Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the verified `Locker` and `Token` sources on the Blockscout explorers, the DefiLlama 1sec adapters (bridge volume and TVL) and sample receipts. Every topic0 and selector was recomputed as `keccak256(signature)`. Every address was existence-checked with `eth_getCode`; `token()`, `owner()`, `minAmount()`, `symbol()` and `decimals()` were read live.
**Scope:** 1sec (OneSec, `1sec.to`), a bridge between the Internet Computer (ICP) and EVM chains. Its EVM side is two small contract types and one wallet per chain: a **Locker** per EVM-native token (USDC, USDT, cbBTC), a **Token** per ICP-native asset (ICP, ckBTC, BOB, GLDT, CHAT), and the **1sec wallet** `0x70ae25592209b57f62b3a3e832ab356228a2192c`, which owns every Locker and Token, receives every lock and sends every unlock. Deployed on Ethereum (1), Base (8453) and Arbitrum One (42161). Topics and selectors are chain-agnostic. Addresses are network-specific.

There is no bridge contract that holds funds. The flows:

- **EVM-native token to ICP (lock):** the user calls `lock1..lock4` on the token's Locker. The Locker pulls the tokens **straight to the 1sec wallet** (ERC-20 `Transfer` user to wallet) and emits `Lock1..Lock4(from, amount, data1..data4)`. `data1..data4` is the encoded ICP recipient. The canister then credits the wrapped token on ICP.
- **ICP to EVM-native token (unlock / payout):** the 1sec wallet sends the token to the recipient: a plain ERC-20 `transfer` from the wallet, or the Locker's owner-only `transfer` / `batchTransfer`. **No 1sec event.** The only trace is the ERC-20 `Transfer` from `0x70ae25592209b57f62b3a3e832ab356228a2192c`.
- **ICP-native token to EVM (mint / payout):** the 1sec wallet calls `mint` / `batchMint` on the Token: ERC-20 `Transfer` from `0x0` to the recipient. **No 1sec event.**
- **EVM back to ICP for an ICP-native token (burn):** the user calls `burn1..burn4` on the Token: ERC-20 `Transfer` to `0x0` and `Burn1..Burn4(from, amount, data1..data4)`.

**The link key is off chain.** An EVM leg carries only the encoded ICP account in `data1..data4`; the pairing with the ICP leg is in the 1sec API (`https://1sec.to/api/transactions`, the source of the DefiLlama volume adapter). There is no refund event: a failed or reversed transfer is again a plain transfer from the 1sec wallet.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Owner |
|----------|------|--------|-------|
| **Locker** (verified `Locker`, solc 0.8.30) | One per EVM-native token per chain. `lock1..4` move the token from the user to `owner()` (the 1sec wallet) and emit `Lock1..4`. Owner-only `transfer` / `batchTransfer` pay out from the owner's balance (the owner must approve the Locker). | No (immutable; `token` is immutable) | 1sec wallet (one stray cbBTC Locker on Base and Arbitrum: the deployer EOA) |
| **Token** (verified `Token`, solc 0.8.30) | One per ICP-native asset per chain: ERC-20 + ERC-2612 permit, 8 decimals. `burn1..4` burn and emit `Burn1..4`; owner-only `mint` / `batchMint`. | No (immutable) | 1sec wallet |
| **1sec wallet** `0x70ae25592209b57f62b3a3e832ab356228a2192c` | Holds all locked EVM-native tokens and pays all unlocks; owner of every Locker and Token. Called `LOCKER` in the DefiLlama TVL adapter. An EOA: `eth_getCode` = `0x`. Controlled by the 1sec ICP canister `5okwm-giaaa-aaaar-qbn6a-cai` (per the 1sec design and the TVL adapter; the key control was not verified on chain). | EOA | — |
| Deployer `0xb5b011282b4c522dd2a5aae20ae0582313358fd8` | Deployed the Lockers and the ICP, BOB and ckBTC Tokens; owner of the stray Locker. EOA. | EOA | — |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Locker — source leg, EVM-native token to ICP

| topic0 | Event |
|--------|-------|
| `0x85c3cf6917296ddb89c2e5316ef1cc1e23ebe9cd67c7201ec7ded85f4b1e49c5` | `Lock1(address from, uint256 amount, bytes32 data1)` |
| `0xbc91e09e82371b47e6098d1c84e259e636dad3e4dd629e163e00b2b5460cfca2` | `Lock2(address from, uint256 amount, bytes32 data1, bytes32 data2)` |
| `0x37746866c49223197da6c3e074cb876dcbbe30acbe87afaee535b9bfa78544bf` | `Lock3(address from, uint256 amount, bytes32 data1, bytes32 data2, bytes32 data3)` |
| `0x21f77af1148e013f333d21fef9f9d5025728f4dcae8ad59101279de04f5a5fe4` | `Lock4(address from, uint256 amount, bytes32 data1, bytes32 data2, bytes32 data3, bytes32 data4)` |

No parameter is indexed. `from` is the user (`msg.sender`), `amount` is in the Locker's token units. The value moves in the same transaction: ERC-20 `Transfer(from, 0x70ae25592209b57f62b3a3e832ab356228a2192c, amount)` on `token()`. The token is not in the event: read it from the Locker address (§3).

### 1.2 Token — source leg, ICP-native token back to ICP

| topic0 | Event |
|--------|-------|
| `0xed1db57c560d9b44b3a8cf360b26548a23a4e105692d7703066b849fc3bdefff` | `Burn1(address from, uint256 amount, bytes32 data1)` |
| `0xa382b8eff3dda34ba4c010e0cfa8e201251808e9cb03327816cdbf8625c5972a` | `Burn2(address from, uint256 amount, bytes32 data1, bytes32 data2)` |
| `0x9f1e7104038f2ab412b1929810742a156d55951346186dc8aa6a506312fa4f19` | `Burn3(address from, uint256 amount, bytes32 data1, bytes32 data2, bytes32 data3)` |
| `0x91ca8da2bd72ad589e2f56500dfead055a55279b60844e7b95f890afb520f35b` | `Burn4(address from, uint256 amount, bytes32 data1, bytes32 data2, bytes32 data3, bytes32 data4)` |

Emitter = the Token. In the same transaction: ERC-20 `Transfer(from, 0x0, amount)`.

### 1.3 Destination leg and admin (no 1sec-specific event)

| topic0 | Event |
|--------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |

- **Payout of an EVM-native token:** `Transfer` on USDC / USDT / cbBTC with `from` = `0x70ae25592209b57f62b3a3e832ab356228a2192c`.
- **Payout of an ICP-native token:** `Transfer` on a 1sec Token with `from` = `0x0` (the transaction sender is the 1sec wallet, selector `mint` or `batchMint`).
- **Admin:** `OwnershipTransferred` on a Locker or Token (`updateOwner`, `transferOwnership`). The new owner controls minting (Token) or the destination of every lock (Locker). **Critical.**

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Locker

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x3455fccc` | `lock1(uint256 amount, bytes32 data1)` | Requires `amount >= minAmount`. `transferFrom(user, owner(), amount)`; emits `Lock1`. |
| `0x00e76bdc` | `lock2(uint256 amount, bytes32 data1, bytes32 data2)` | Emits `Lock2`. |
| `0xe1a1ef50` | `lock3(uint256 amount, bytes32 data1, bytes32 data2, bytes32 data3)` | Emits `Lock3`. |
| `0xcee28dff` | `lock4(uint256 amount, bytes32 data1, bytes32 data2, bytes32 data3, bytes32 data4)` | Emits `Lock4`. |
| `0xa9059cbb` | `transfer(address recipient, uint256 amount)` | **Owner only, `payable`.** Pays `amount` of the token from the caller to `recipient` and forwards `msg.value`. Same selector as ERC-20 `transfer`. |
| `0x1ef690c4` | `batchTransfer(address[] recipients, uint256[] amounts, uint256[] ethAmounts)` | Owner only, `payable`. Batched payout. |
| `0x880cdc31` | `updateOwner(address _owner)` | Owner only. Emits `OwnershipTransferred`; **redirects all future locks.** |
| `0xff897dbd` | `updateMinAmount(uint256 _minAmount)` | Owner only. |
| `0xa158657c` | `withdrawEth(uint256 amount, address to)` | Owner only. |
| `0xfc0c546a` | `token()` | `address` — the locked ERC-20. |
| `0x9b2cb5d8` | `minAmount()` | `uint256`. |
| `0x893d20e8` | `getOwner()` | `address`. |
| `0xcfc7e2da` | `getMinAmount()` | `uint256`. |

### 2.2 Token

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x34c80b1e` | `burn1(uint256 amount, bytes32 data1)` | Requires `amount >= minAmount`. Burns; emits `Burn1`. |
| `0x894b268f` | `burn2(uint256 amount, bytes32 data1, bytes32 data2)` | Emits `Burn2`. |
| `0xaa678ce4` | `burn3(uint256 amount, bytes32 data1, bytes32 data2, bytes32 data3)` | Emits `Burn3`. |
| `0x2feef60e` | `burn4(uint256 amount, bytes32 data1, bytes32 data2, bytes32 data3, bytes32 data4)` | Emits `Burn4`. |
| `0x40c10f19` | `mint(address to, uint256 amount)` | **Owner only, `payable`.** The payout path; emits only `Transfer(0x0, to, amount)`. |
| `0xd559f05b` | `batchMint(address[] recipients, uint256[] amounts, uint256[] ethAmounts)` | Owner only. Batched payout. |
| `0x880cdc31` | `updateOwner(address _owner)` | Owner only. **Changes the mint authority.** |
| `0xff897dbd` | `updateMinAmount(uint256 _minAmount)` | Owner only. |
| `0xa158657c` | `withdrawEth(uint256 amount, address to)` | Owner only. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

| Role | Address | One-liner |
|------|---------|-----------|
| **Locker USDC** | `0xae2351b15cff68b5863c6690dca58dce383bf45a` | `token()` = USDC `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48`; `minAmount` 1 USDC; owner = 1sec wallet. |
| **Locker USDT** | `0xc5ac945a0af0768929301a27d6f2a7770995faeb` | `token()` = USDT `0xdac17f958d2ee523a2206206994597c13d831ec7`; `minAmount` 1 USDT; owner = 1sec wallet. Ethereum only. |
| **Locker cbBTC** | `0x7744c6a83e4b43921f27d3c94a742bf9cd24c062` | `token()` = cbBTC `0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf`; `minAmount` 0.00001 cbBTC; owner = 1sec wallet. |
| **Token ICP** | `0x00f3c42833c3170159af4e92dbb451fb3f708917` | 8 decimals; `minAmount` 1 ICP; supply 669,525.57 at the read. |
| **Token BOB** | `0xecc5f868add75f4ff9fd00bbbde12c35ba2c9c89` | 8 decimals. |
| **Token ckBTC** | `0x919a41ea07c26f0001859bc5dcb8754068718fb7` | 8 decimals; supply 0 at the read. |
| **Token GLDT** | `0x86856814e74456893cfc8946bedcbb472b5fa856` | 8 decimals; deployed by `0x475c65f3f34b069d3e8382090e6e17859b194a5e`. |
| **Token CHAT** | `0xdb95092c454235e7e666c4e226dbbbcdeb499d25` | 8 decimals; supply 0 at the read; deployed by `0xe4757f07b8b28776c8850805ff478b1470333f08`. |
| **1sec wallet (EOA)** | `0x70ae25592209b57f62b3a3e832ab356228a2192c` | Receives all locks, pays all unlocks, owns every Locker and Token. Nonce 1,775. |
| Deployer (EOA) | `0xb5b011282b4c522dd2a5aae20ae0582313358fd8` | Nonce 59. |

## 4. Addresses — Base (chain ID 8453) and Arbitrum One (chain ID 42161)

The Tokens and the USDC and cbBTC Lockers use the **same addresses as on Ethereum** (same deployer and nonces). The code differs per chain only in the immutables (the Locker's `token`, the Token's name in the EIP-712 domain), so the "different code" at the same address is the same contract type.

| Role | Base | Arbitrum One |
|------|------|--------------|
| Locker USDC (`0xae2351b15cff68b5863c6690dca58dce383bf45a`) | `token()` = USDC `0x833589fcd6edb6e08f4c7c32d4f71b54bda02913` | `token()` = USDC `0xaf88d065e77c8cc2239327c5edb3a432268e5831` |
| Locker cbBTC (`0x7744c6a83e4b43921f27d3c94a742bf9cd24c062`) | `token()` = cbBTC `0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf` | `token()` = cbBTC `0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf` |
| Stray Locker (`0xc5ac945a0af0768929301a27d6f2a7770995faeb`) | **cbBTC, not USDT**; owner = deployer EOA `0xb5b011282b4c522dd2a5aae20ae0582313358fd8`; `minAmount` 10,000 | Same as Base. Not in the 1sec token list; a lock here pays the deployer, not the 1sec wallet. |
| Tokens ICP, BOB, ckBTC, GLDT, CHAT | Same addresses; owner = 1sec wallet; 8 decimals | Same addresses; owner = 1sec wallet; 8 decimals |
| 1sec wallet (EOA) | `0x70ae25592209b57f62b3a3e832ab356228a2192c` (nonce 2,095) | `0x70ae25592209b57f62b3a3e832ab356228a2192c` (nonce 330) |

### 4.1 Optimism, Polygon, BNB, Avalanche, Robinhood — NO 1sec deployment

`eth_getCode` returns `0x` at all three Lockers and all five Tokens on Optimism (10), Polygon PoS (137), BNB Smart Chain (56), Avalanche C-Chain (43114) and Robinhood Chain (4663), and the 1sec wallet and the deployer have nonce 0 there. The DefiLlama adapters list only Ethereum, Arbitrum and Base.

---

## 5. Cross-chain summary

| Chain | ID | Lockers | Tokens | 1sec wallet active |
|-------|----|---------|--------|--------------------|
| Ethereum | 1 | USDC, USDT, cbBTC | ICP, BOB, ckBTC, GLDT, CHAT | ✓ (nonce 1,775) |
| Base | 8453 | USDC, cbBTC (+ stray) | ICP, BOB, ckBTC, GLDT, CHAT | ✓ (nonce 2,095) |
| Arbitrum One | 42161 | USDC, cbBTC (+ stray) | ICP, BOB, ckBTC, GLDT, CHAT | ✓ (nonce 330) |
| Optimism | 10 | — (`0x`) | — | — |
| Polygon PoS | 137 | — (`0x`) | — | — |
| BNB Smart Chain | 56 | — (`0x`) | — | — |
| Avalanche C-Chain | 43114 | — (`0x`) | — | — |
| Robinhood Chain | 4663 | — (`0x`) | — | — |

The other side is the Internet Computer (canister `5okwm-giaaa-aaaar-qbn6a-cai`; 1sec bridged-USDC ledger `53nhb-haaaa-aaaar-qbn5q-cai`). 1sec has no chain-id scheme on chain; the EVM chain is implied by the contract's chain.

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Authority |
|----------|---------|-----------|-----------|
| Lockers, Tokens | **Not proxies** (immutable) | Full runtime bytecode (Locker 3,430 B, Token 6,542 B); no EIP-1967 implementation slot. Verified source has no upgrade path. | `owner()` = 1sec wallet EOA `0x70ae25592209b57f62b3a3e832ab356228a2192c` (stray Locker: deployer EOA). |

The owner can mint any amount of every Token (`mint`, `batchMint`), redirect every future lock (`updateOwner` on a Locker), and pay out from the wallet at will. Watch `OwnershipTransferred` on all eight contracts per chain and any `Transfer` from `0x0` on a Token that is not sent by the 1sec wallet.

---

## 7. Detection invariants & gotchas

1. **Index the Locker events and the wallet transfers together.** `Lock1..4` mark EVM-to-ICP deposits; the matching value is the ERC-20 `Transfer` to `0x70ae25592209b57f62b3a3e832ab356228a2192c` in the same transaction. Users can also send tokens **directly** to the wallet with no Locker event (seen on Ethereum, Base and Arbitrum); those transfers have no ICP recipient on chain.
2. **Payouts have no 1sec event.** EVM-native: `Transfer` from the wallet. ICP-native: `Transfer` from `0x0` on a 1sec Token (a `mint` by the wallet). A monitor for exits from ICP keys on these transfers.
3. **The wallet receives large volumes of spam tokens.** In the last 50 token transfers of the wallet on Base, 33 were look-alike or airdrop tokens ("USDC" with confusable characters, unknown tokens), and on Ethereum 19 of 50. Filter by the real token address (§3, §4).
4. **Burns are the EVM-to-ICP leg for ICP-native assets.** `Burn1..4` plus `Transfer` to `0x0`. The Base sample burned ICP; Ethereum showed 2 `burn1` calls among the Token's last 50 transactions.
5. **No on-chain link key.** `data1..data4` is the encoded ICP account, not a transfer id. Join the EVM and ICP legs through the 1sec API only.
6. **`Lock*` and `Burn*` have no indexed field.** Filter by topic0 and emitter, and decode `from` and `amount` from the data.
7. **The stray Locker `0xc5ac945a0af0768929301a27d6f2a7770995faeb` on Base and Arbitrum** is a cbBTC Locker owned by the deployer EOA, while the same address is the USDT Locker on Ethereum. Key on `(chain, address)`.
8. **The Locker's `transfer(address,uint256)` has the ERC-20 `transfer` selector `0xa9059cbb`.** A call to a Locker with this selector is an owner payout, not a token transfer of the Locker.
9. **Activity is low.** In the pinned window, all Lockers emitted 0 logs on all three chains, and the only 1sec event was 2 `Burn1` on Base. A 0 in a 12-hour window does not mean the bridge is dead: Blockscout shows a USDT `lock1` on Ethereum on 2026-09-29 and a USDC `lock1` on Base on 2026-09-23.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics =====
TOPIC_ONESEC_LOCK1                = '\x85c3cf6917296ddb89c2e5316ef1cc1e23ebe9cd67c7201ec7ded85f4b1e49c5'
TOPIC_ONESEC_LOCK2                = '\xbc91e09e82371b47e6098d1c84e259e636dad3e4dd629e163e00b2b5460cfca2'
TOPIC_ONESEC_LOCK3                = '\x37746866c49223197da6c3e074cb876dcbbe30acbe87afaee535b9bfa78544bf'
TOPIC_ONESEC_LOCK4                = '\x21f77af1148e013f333d21fef9f9d5025728f4dcae8ad59101279de04f5a5fe4'
TOPIC_ONESEC_BURN1                = '\xed1db57c560d9b44b3a8cf360b26548a23a4e105692d7703066b849fc3bdefff'
TOPIC_ONESEC_BURN2                = '\xa382b8eff3dda34ba4c010e0cfa8e201251808e9cb03327816cdbf8625c5972a'
TOPIC_ONESEC_BURN3                = '\x9f1e7104038f2ab412b1929810742a156d55951346186dc8aa6a506312fa4f19'
TOPIC_ONESEC_BURN4                = '\x91ca8da2bd72ad589e2f56500dfead055a55279b60844e7b95f890afb520f35b'
TOPIC_ERC20_TRANSFER              = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_OWNERSHIP_TRANSFERRED       = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- ===== Selectors =====
SEL_ONESEC_LOCK1                  = '\x3455fccc'
SEL_ONESEC_LOCK2                  = '\x00e76bdc'
SEL_ONESEC_LOCK3                  = '\xe1a1ef50'
SEL_ONESEC_LOCK4                  = '\xcee28dff'
SEL_ONESEC_BURN1                  = '\x34c80b1e'
SEL_ONESEC_BURN2                  = '\x894b268f'
SEL_ONESEC_BURN3                  = '\xaa678ce4'
SEL_ONESEC_BURN4                  = '\x2feef60e'
SEL_ONESEC_MINT                   = '\x40c10f19'
SEL_ONESEC_BATCH_MINT             = '\xd559f05b'
SEL_ONESEC_LOCKER_BATCH_TRANSFER  = '\x1ef690c4'
SEL_ONESEC_UPDATE_OWNER           = '\x880cdc31'
-- ===== Ethereum (1) =====
ETH_ONESEC_LOCKER_USDC            = '\xae2351b15cff68b5863c6690dca58dce383bf45a'
ETH_ONESEC_LOCKER_USDT            = '\xc5ac945a0af0768929301a27d6f2a7770995faeb'
ETH_ONESEC_LOCKER_CBBTC           = '\x7744c6a83e4b43921f27d3c94a742bf9cd24c062'
ETH_ONESEC_TOKEN_ICP              = '\x00f3c42833c3170159af4e92dbb451fb3f708917'
ETH_ONESEC_TOKEN_BOB              = '\xecc5f868add75f4ff9fd00bbbde12c35ba2c9c89'
ETH_ONESEC_TOKEN_CKBTC            = '\x919a41ea07c26f0001859bc5dcb8754068718fb7'
ETH_ONESEC_TOKEN_GLDT             = '\x86856814e74456893cfc8946bedcbb472b5fa856'
ETH_ONESEC_TOKEN_CHAT             = '\xdb95092c454235e7e666c4e226dbbbcdeb499d25'
ETH_ONESEC_WALLET_EOA             = '\x70ae25592209b57f62b3a3e832ab356228a2192c'
ETH_ONESEC_DEPLOYER_EOA           = '\xb5b011282b4c522dd2a5aae20ae0582313358fd8'
-- ===== Base (8453) =====
BASE_ONESEC_LOCKER_USDC           = '\xae2351b15cff68b5863c6690dca58dce383bf45a'
BASE_ONESEC_LOCKER_CBBTC          = '\x7744c6a83e4b43921f27d3c94a742bf9cd24c062'
BASE_ONESEC_LOCKER_STRAY_CBBTC    = '\xc5ac945a0af0768929301a27d6f2a7770995faeb'
BASE_ONESEC_TOKEN_ICP             = '\x00f3c42833c3170159af4e92dbb451fb3f708917'
BASE_ONESEC_TOKEN_BOB             = '\xecc5f868add75f4ff9fd00bbbde12c35ba2c9c89'
BASE_ONESEC_TOKEN_CKBTC           = '\x919a41ea07c26f0001859bc5dcb8754068718fb7'
BASE_ONESEC_TOKEN_GLDT            = '\x86856814e74456893cfc8946bedcbb472b5fa856'
BASE_ONESEC_TOKEN_CHAT            = '\xdb95092c454235e7e666c4e226dbbbcdeb499d25'
BASE_ONESEC_WALLET_EOA            = '\x70ae25592209b57f62b3a3e832ab356228a2192c'
-- ===== Arbitrum One (42161) =====
ARB_ONESEC_LOCKER_USDC            = '\xae2351b15cff68b5863c6690dca58dce383bf45a'
ARB_ONESEC_LOCKER_CBBTC           = '\x7744c6a83e4b43921f27d3c94a742bf9cd24c062'
ARB_ONESEC_LOCKER_STRAY_CBBTC     = '\xc5ac945a0af0768929301a27d6f2a7770995faeb'
ARB_ONESEC_TOKEN_ICP              = '\x00f3c42833c3170159af4e92dbb451fb3f708917'
ARB_ONESEC_TOKEN_BOB              = '\xecc5f868add75f4ff9fd00bbbde12c35ba2c9c89'
ARB_ONESEC_TOKEN_CKBTC            = '\x919a41ea07c26f0001859bc5dcb8754068718fb7'
ARB_ONESEC_TOKEN_GLDT             = '\x86856814e74456893cfc8946bedcbb472b5fa856'
ARB_ONESEC_TOKEN_CHAT             = '\xdb95092c454235e7e666c4e226dbbbcdeb499d25'
ARB_ONESEC_WALLET_EOA             = '\x70ae25592209b57f62b3a3e832ab356228a2192c'
-- Optimism, Polygon, BNB, Avalanche, Robinhood: no 1sec contract
```

---

## 9. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified `src/Locker.sol` (Ethereum `0xae2351b15cff68b5863c6690dca58dce383bf45a`) and `src/Token.sol` (Ethereum `0x00f3c42833c3170159af4e92dbb451fb3f708917`) on Blockscout. `Lock1`, `Burn1` and ERC-20 `Transfer` confirmed in the receipts below.
- **Addresses:** token and Locker addresses from the DefiLlama 1sec bridge adapter (ICP, BOB, CHAT, GLDT) and the evidence of Locker transactions on Blockscout; the wallet from the DefiLlama TVL adapter (`LOCKER = 0x70AE25592209B57F62b3a3e832ab356228a2192C`, canister `5okwm-giaaa-aaaar-qbn6a-cai`). `eth_getCode` on all eight chains; `token()`, `owner()`, `minAmount()`, `symbol()`, `decimals()`, `totalSupply()` read live on Ethereum, Base and Arbitrum.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC** (all logs of each contract): Ethereum — Lockers 0; Token ICP 596 (`Transfer` 568, `Approval` 28, no `Burn*`); Token BOB 1 `Transfer`; other Tokens 0. Base — all three Lockers 0; Token ICP 3,254 (`Transfer` 3,069, `Approval` 183, `Burn1` 2); other Tokens 0. Arbitrum — all Lockers and Tokens 0. The positive control is the Base ICP Token (3,254 logs from the same query).
- **Sample transactions (receipts read):** Ethereum `lock1` `0x739be0aa8b03f01aea9c527d7c121c71c3819595aa9f692bb857cda3c9ca7dd6` (block 26,083,127; USDT `Transfer` user to wallet, then `Lock1` from the USDT Locker). Base `burn1` `0xa699557976402e04f2e757ac50faa2628f15349a2f705dee2f027bb1544cb637` (block 51,898,214; ICP `Transfer` to `0x0`, `Burn1`). Ethereum `mint` `0x91dcab6ba5df1158800946728e68d830bb9478aa9b446dda61e1adfd5346ce98` (block 26,090,575; sent by the wallet; ICP `Transfer` from `0x0` only). Ethereum payout `0x92680d03f7825ece11f45372923eb9a6cbcd259387b2f308bdae7e4e7a09407a` (block 25,888,837; plain USDC `transfer` from the wallet, 2,751.676332 USDC).
- **Unverified:** the canister control of the wallet's key (1sec states that the canister is NNS-controlled; this was not checked on chain); the full list of 1sec tokens beyond those above (the 1sec site returns HTTP 403 to automated reads).

Authoritative sources:
- Verified sources — [Locker (Ethereum)](https://eth.blockscout.com/address/0xae2351b15cff68b5863c6690dca58dce383bf45a) · [Token ICP (Ethereum)](https://eth.blockscout.com/address/0x00f3c42833c3170159af4e92dbb451fb3f708917).
- [DefiLlama bridges-server adapter `1sec`](https://github.com/DefiLlama/bridges-server/tree/master/src/adapters/1sec) · [DefiLlama TVL adapter `onesec`](https://github.com/DefiLlama/DefiLlama-Adapters/blob/main/projects/onesec/index.js).
- [ICP forum: "Onesec.to is live"](https://forum.dfinity.org/t/onesec-to-is-live/50995) — design notes, bridged-USDC ledger id.
- Explorers — [1sec wallet on Etherscan](https://etherscan.io/address/0x70ae25592209b57f62b3a3e832ab356228a2192c) · [Basescan](https://basescan.org/address/0x70ae25592209b57f62b3a3e832ab356228a2192c) · [Arbiscan](https://arbiscan.io/address/0x70ae25592209b57f62b3a3e832ab356228a2192c).
