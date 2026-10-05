# Layerswap — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Robinhood Chain, Arc)

**Status:** verified on 2026-09-29 against live RPC on the eight original target chains (Arc added on 2026-10-05 with the same checks), the canonical `layerswap/layerswap-depository` source (`evm/src/LayerswapDepository.sol`), the Layerswap docs and public API (`/api/v2/networks`, `/api/v2/explorer/{tx}`), and the LI.FI integration config (`lifinance/contracts` `config/layerswap.json`). Topic0s and selectors are recomputed as `keccak256(sig)`. Addresses are existence-checked with `eth_getCode`. The whitelist, owner and pause state are read with `eth_call`.
**Scope:** the Layerswap EVM surface: the **LayerswapDepository** (one immutable contract at one address on all nine chains), the two whitelisted **Layerswap wallets** that take deposits and send payouts (EOAs, one address each on all nine chains), and the paths with no Layerswap event (plain transfers, generated deposit addresses). Chains: Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10), Polygon PoS (137), BNB Smart Chain (56), Avalanche C-Chain (43114), Robinhood Chain (4663), Arc (5042). Topics and selectors are chain-agnostic. Addresses are network-specific. The TRAIN atomic-swap contracts are a separate protocol; the Layerswap docs say that TRAIN is not part of the current Layerswap integrations, so this file does not cover them.

Layerswap is a solver bridge with an off-chain order book. A user creates a **swap** in the Layerswap API. The user then sends the source asset to a Layerswap wallet. Layerswap pays the recipient on the destination chain from its own inventory. There is no destination-side contract and no on-chain settlement.

The source leg has four funding methods. (1) **Depository:** the user (or an aggregator such as LI.FI) calls `depositERC20` / `depositNative` on the LayerswapDepository. The contract forwards the funds to a whitelisted wallet in the same call and emits `Deposited`. It never holds a balance. (2) **Wallet transfer:** a plain ERC-20 `transfer` or native transfer to a Layerswap wallet, with a matching memo in the calldata. (3) **Deposit address:** Layerswap assigns a generated address to the swap, and the sender transfers to it. (4) **Gasless:** the user signs EIP-712 data and a relayer submits the deposit. Only method (1) emits a Layerswap event.

The destination leg is a plain native or ERC-20 transfer from a Layerswap wallet to the recipient. When the route swaps on the destination, the wallet sends a transaction to a DEX router, and the recipient gets the token from the router or pool. A refund is a plain transfer from the same wallet back to the refund address on the source chain. **The link key is the swap's `sequence_number`.** It is on chain only on the source side, as `Deposited.id` (a right-aligned integer in `bytes32`). The payout carries no key. The public API `GET https://api.layerswap.io/api/v2/explorer/{tx hash}` maps a deposit or payout hash to the swap id, the sequence number and both transaction hashes.

---

## 0. Contract families & versions

| Component | Role | Proxy? | Where |
|-----------|------|--------|-------|
| **LayerswapDepository** (v1.0.0) | Source-leg entry point. Forwards native and ERC-20 funds to a whitelisted wallet in the same call. Emits `Deposited(id, token, receiver, amount)`. `Ownable2Step` + `Pausable` + `ReentrancyGuard`. | **No** (immutable, 3,876 B, same code hash on all nine chains) | all nine chains, one address |
| **Wallet A** | Whitelisted receiver of deposits. Sends payouts and refunds. The Layerswap deposit-widget example uses it. | n/a (EOA) | all nine chains, one address |
| **Wallet B** | Second whitelisted receiver. Same roles as wallet A. The Layerswap refunds page uses it in its example. | n/a (EOA) | all nine chains, one address |
| **Depository owner** | `owner()` of the Depository on all nine chains. Can pause, edit the whitelist and transfer ownership. | n/a (EOA, no code on all nine chains) | all nine chains |
| **Generated deposit addresses** | One address per swap for the "deposit address" funding method. | n/a | not enumerable on chain |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 LayerswapDepository

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xcfccc5211684bc31ce945214025a7453ba30a1ffcc38fcb691ce742437f3f256` | `Deposited(bytes32 indexed id, address indexed token, address indexed receiver, uint256 amount)` | **Source-leg event.** `id` = the swap's `sequence_number`. `token` = `0x0000000000000000000000000000000000000000` for native. `receiver` = wallet A or wallet B. `amount` = the receiver's balance change for ERC-20 (fee-on-transfer safe), `msg.value` for native. |
| `0x4f783c179409b4127238bc9c990bc99b9a651666a0d20b51d6c42849eb88466d` | `AddressWhitelisted(address indexed addr)` | Admin. A new receiver can take deposits. |
| `0x535611fb62fa2a833988f283b779e417e996813e44046f521d76c17b5943b08c` | `AddressRemovedFromWhitelist(address indexed addr)` | Admin. |
| `0x0f036efe7678a8f6bdd40a5748c686f23fc867ced9c237c484c652a43481ba75` | `AddressUpdatedInWhitelist(address indexed oldAddr, address indexed newAddr)` | Admin. Replaces a receiver in one call. |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | Admin. Stops both deposit functions. |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | Admin. |
| `0x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700` | `OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner)` | Admin (`Ownable2Step`, step one). |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Admin (step two). |

### 1.2 Value capture (no Layerswap event)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20. Deposit: `to` = wallet A or wallet B (also in the Depository path, where the token moves user → wallet directly). Payout or refund: `from` = wallet A or wallet B. |

Native deposits to the wallets and native payouts from them emit no log. Read them from transactions (`to` / `from` = a wallet, `value > 0`). In the Depository native path, the value moves caller → Depository → wallet in an internal call.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 LayerswapDepository

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xf4371f63` | `depositERC20(bytes32 id, address token, address receiver, uint256 amount)` | `safeTransferFrom(msg.sender, receiver, amount)`, then `Deposited`. Reverts when `receiver` is not whitelisted or the contract is paused. |
| `0x80a6de92` | `depositNative(bytes32 id, address receiver)` | Payable. Emits `Deposited` with `token = 0x0000000000000000000000000000000000000000`, then forwards `msg.value` to `receiver`. |
| `0xe43252d7` | `addToWhitelist(address addr)` | `onlyOwner`. Emits `AddressWhitelisted`. |
| `0x8ab1d681` | `removeFromWhitelist(address addr)` | `onlyOwner`. Emits `AddressRemovedFromWhitelist`. |
| `0x86d11066` | `updateWhitelistedAddress(address oldAddr, address newAddr)` | `onlyOwner`. Emits `AddressUpdatedInWhitelist`. |
| `0x8456cb59` | `pause()` | `onlyOwner`. |
| `0x3f4ba83a` | `unpause()` | `onlyOwner`. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | `onlyOwner`. Starts the two-step transfer. |
| `0x79ba5097` | `acceptOwnership()` | Called by the pending owner. |
| `0x715018a6` | `renounceOwnership()` | `onlyOwner` (inherited from OpenZeppelin `Ownable`). |
| `0x6d028027` | `getWhitelistedAddresses()` | View → `address[]`. Live value on all nine chains: wallet A and wallet B. |
| `0x3af32abf` | `isWhitelisted(address addr)` | View → `bool`. |
| `0x5c975abb` | `paused()` | View → `bool`. Live value: `false` on all nine chains. |
| `0x8da5cb5b` | `owner()` | View → `address`. |
| `0xe30c3978` | `pendingOwner()` | View → `address`. |

### 2.2 Wallet-transfer deposit

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xa9059cbb` | `transfer(address to, uint256 value)` | ERC-20 deposit to a Layerswap wallet. The API's `call_data` appends Layerswap's matching data after the two arguments. The exact memo layout is unverified. |

---

## 3. Addresses — Ethereum (chain ID 1)

All addresses on this page were existence-checked with `eth_getCode` on 2026-09-29 (Arc on 2026-10-05). The Depository, both wallets and the owner have the same address on all nine chains.

| Role | Address | One-liner |
|------|---------|-----------|
| **LayerswapDepository** | `0xE226E4825CB215aBaFAd98fdd400583eAb6a594f` | 3,876 B, code hash `0xe2c5b091f98ff37764289b288afff06c0603e81a35cf4e55af17526838228831`. Whitelist = wallet A + wallet B. Not paused. |
| Wallet A (EOA) | `0x2Fc617E933a52713247CE25730f6695920B3befe` | Receives deposits, sends payouts and refunds. Nonce 585,510. |
| Wallet B (EOA) | `0x08b00cEEE2Fb66029B53D76110B19eeAabfd1e65` | Same roles. Nonce 55,642. |
| Depository owner (EOA) | `0xB6103502673173ab5Df6A57Ac3017Db4e16af399` | No code, nonce 0 on Ethereum. |

## 4. Addresses — Base (chain ID 8453)

| Role | Address | One-liner |
|------|---------|-----------|
| **LayerswapDepository** | `0xE226E4825CB215aBaFAd98fdd400583eAb6a594f` | Same code hash as Ethereum. Same whitelist and owner. Not paused. |
| Wallet A (EOA) | `0x2Fc617E933a52713247CE25730f6695920B3befe` | Nonce 396,421. |
| Wallet B (EOA) | `0x08b00cEEE2Fb66029B53D76110B19eeAabfd1e65` | Nonce 53,695. |
| Depository owner (EOA) | `0xB6103502673173ab5Df6A57Ac3017Db4e16af399` | No code, nonce 1. |

## 5. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| **LayerswapDepository** | `0xE226E4825CB215aBaFAd98fdd400583eAb6a594f` | Same code hash. Same whitelist and owner. Not paused. |
| Wallet A (EOA) | `0x2Fc617E933a52713247CE25730f6695920B3befe` | Nonce 556,506. |
| Wallet B (EOA) | `0x08b00cEEE2Fb66029B53D76110B19eeAabfd1e65` | Nonce 66,573. |
| Depository owner (EOA) | `0xB6103502673173ab5Df6A57Ac3017Db4e16af399` | No code, nonce 4. |

## 6. Addresses — Optimism (chain ID 10)

| Role | Address | One-liner |
|------|---------|-----------|
| **LayerswapDepository** | `0xE226E4825CB215aBaFAd98fdd400583eAb6a594f` | Same code hash. Same whitelist and owner. Not paused. |
| Wallet A (EOA) | `0x2Fc617E933a52713247CE25730f6695920B3befe` | Nonce 235,175. |
| Wallet B (EOA) | `0x08b00cEEE2Fb66029B53D76110B19eeAabfd1e65` | Nonce 36,328. |
| Depository owner (EOA) | `0xB6103502673173ab5Df6A57Ac3017Db4e16af399` | No code, nonce 0. |

## 7. Addresses — Polygon PoS (chain ID 137)

| Role | Address | One-liner |
|------|---------|-----------|
| **LayerswapDepository** | `0xE226E4825CB215aBaFAd98fdd400583eAb6a594f` | Same code hash. Same whitelist and owner. Not paused. |
| Wallet A (EOA) | `0x2Fc617E933a52713247CE25730f6695920B3befe` | Nonce 63,087. |
| Wallet B (EOA) | `0x08b00cEEE2Fb66029B53D76110B19eeAabfd1e65` | Nonce 34,463. |
| Depository owner (EOA) | `0xB6103502673173ab5Df6A57Ac3017Db4e16af399` | No code, nonce 0. |

## 8. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | One-liner |
|------|---------|-----------|
| **LayerswapDepository** | `0xE226E4825CB215aBaFAd98fdd400583eAb6a594f` | Same code hash. Same whitelist and owner. Not paused. |
| Wallet A (EOA) | `0x2Fc617E933a52713247CE25730f6695920B3befe` | Nonce 117,398. |
| Wallet B (EOA) | `0x08b00cEEE2Fb66029B53D76110B19eeAabfd1e65` | Nonce 111,478. |
| Depository owner (EOA) | `0xB6103502673173ab5Df6A57Ac3017Db4e16af399` | No code, nonce 0. |

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

| Role | Address | One-liner |
|------|---------|-----------|
| **LayerswapDepository** | `0xE226E4825CB215aBaFAd98fdd400583eAb6a594f` | Same code hash. Same whitelist and owner. Not paused. |
| Wallet A (EOA) | `0x2Fc617E933a52713247CE25730f6695920B3befe` | Nonce 23,905. |
| Wallet B (EOA) | `0x08b00cEEE2Fb66029B53D76110B19eeAabfd1e65` | Nonce 29,539. |
| Depository owner (EOA) | `0xB6103502673173ab5Df6A57Ac3017Db4e16af399` | No code, nonce 0. |

## 10. Addresses — Robinhood Chain (chain ID 4663)

Layerswap lists `ROBINHOOD_MAINNET` (chain id 4663) in its public network list, with a listing date of 2026-07-02.

| Role | Address | One-liner |
|------|---------|-----------|
| **LayerswapDepository** | `0xE226E4825CB215aBaFAd98fdd400583eAb6a594f` | Same code hash. Same whitelist and owner. Not paused. |
| Wallet A (EOA) | `0x2Fc617E933a52713247CE25730f6695920B3befe` | Nonce 41,521. |
| Wallet B (EOA) | `0x08b00cEEE2Fb66029B53D76110B19eeAabfd1e65` | Nonce 4,005. |
| Depository owner (EOA) | `0xB6103502673173ab5Df6A57Ac3017Db4e16af399` | No code, nonce 0. |

## 11. Addresses — Arc (chain ID 5042)

Layerswap lists `ARC_MAINNET` (chain id 5042) in its public network list (tokens include USDC, EURC, cirBTC, LINK). Checked on `https://rpc.mainnet.arc.io` on 2026-10-05.

| Role | Address | One-liner |
|------|---------|-----------|
| **LayerswapDepository** | `0xE226E4825CB215aBaFAd98fdd400583eAb6a594f` | Same code hash as Ethereum. Same whitelist and owner. Not paused. EIP-1967 implementation and beacon slots empty. 7 `Deposited` logs in ~40,000 blocks (about 5.7 h) to 2026-10-05. |
| Wallet A (EOA) | `0x2Fc617E933a52713247CE25730f6695920B3befe` | Nonce 174. |
| Wallet B (EOA) | `0x08b00cEEE2Fb66029B53D76110B19eeAabfd1e65` | Nonce 67. |
| Depository owner (EOA) | `0xB6103502673173ab5Df6A57Ac3017Db4e16af399` | No code, nonce 0. |

Nonces are the wallets' transaction counts at the latest block on 2026-09-29 (Arc: 2026-10-05). They are a measure of outbound activity, not of volume.

---

## 12. Cross-chain summary

| Chain | ID | LayerswapDepository `0xE226E4825CB215aBaFAd98fdd400583eAb6a594f` | Wallet A | Wallet B | `Deposited` in the pinned window |
|-------|----|----|----|----|----|
| Ethereum | 1 | ✅ | ✅ EOA | ✅ EOA | 153 |
| Base | 8453 | ✅ | ✅ EOA | ✅ EOA | 506 |
| Arbitrum One | 42161 | ✅ | ✅ EOA | ✅ EOA | 331 |
| Optimism | 10 | ✅ | ✅ EOA | ✅ EOA | 163 |
| Polygon PoS | 137 | ✅ | ✅ EOA | ✅ EOA | 72 |
| BNB Smart Chain | 56 | ✅ | ✅ EOA | ✅ EOA | 149 |
| Avalanche C-Chain | 43114 | ✅ | ✅ EOA | ✅ EOA | 20 |
| Robinhood Chain | 4663 | ✅ | ✅ EOA | ✅ EOA | 270 |
| Arc | 5042 | ✅ | ✅ EOA | ✅ EOA | not counted (7 via `eth_getLogs` in ~5.7 h on 2026-10-05) |

Layerswap is deployed on all nine target chains. The LI.FI integration config lists the Depository at the same address on 43 networks in total (for example Abstract, Blast, Linea, Scroll, Tron, zkSync). Layerswap also serves chains that are not EVM (Solana, Starknet, TON, Bitcoin, Tron, Fuel), each with its own deposit method.

---

## 13. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **LayerswapDepository** | **Immutable** (no proxy) | EIP-1967 implementation and beacon slots are empty on all nine chains. The runtime code (3,876 B) has the same hash on all nine chains. The source has no upgrade function. | None. The owner can only pause, edit the whitelist and transfer ownership. |

There are no other contracts in this system. The wallets and the owner are EOAs.

---

## 14. Detection invariants & gotchas

1. **The Depository never holds funds.** `depositERC20` moves the token from the caller straight to the wallet. So the ERC-20 `Transfer` of a Depository deposit goes to wallet A or wallet B, not to the Depository. Do not look for a Depository balance.
2. **`Deposited.id` is the swap's `sequence_number`, not the swap UUID.** Example: the Ethereum deposit `0x9bef18faa4ee8990435683563d0b6075e29c2bd882102fff14ff61b2df6da7de` has `id` 17,938,734 (`0x111b92e`). The explorer API returns swap `55ed2f2f-9d7a-4cc7-b0ba-dd5207e2911e` with `metadata.sequence_number` 17,938,734.
3. **The payout has no event and no key.** A payout is a plain transfer from a wallet. Join it to a deposit through the explorer API, or approximately by recipient, token and time.
4. **Key payouts on the transaction sender, not only on `Transfer.from`.** For a route with a destination swap, the wallet sends the transaction to a DEX router. The recipient then gets the output token from the router or pool. Example: Arbitrum payout `0xf701b7b90ebd87899b4de20e3516e47cb1319a441b69ef62fda12177c0073d4f` is sent by wallet B to the Uniswap Universal Router, and the USDC comes from a pool.
5. **The wallets move value in both directions.** They receive deposits, send payouts and send refunds. A rule on "transfer to a wallet" catches deposits. A rule on "transfer from a wallet" catches payouts and refunds. A refund goes back on the source chain in the source token.
6. **Three deposit methods emit no Layerswap event.** Plain transfers to a wallet, transfers to a generated deposit address, and gasless deposits leave only token transfers (or native value). A generated deposit address is not enumerable on chain.
7. **The `Deposited` topic is not unique to Layerswap.** In the pinned window, other contracts emitted the same topic0: on Ethereum `0xc3cfc78a52bDFF4973dDaCE07E17A52F253f463d` (1 log, a different 10,127-byte contract), and on BNB `0x5c72aBc9822eC98dfDCeD995CcD2BdD2040B68C6` (10), `0xfE006acf268f944AA2D03B7B4943E1a3b57a0eFd` (5) and `0x952a26dA229c95a1ae375F6dd352B7214B105A6f` (1). Filter on the emitter.
8. **Aggregators call the Depository.** LI.FI's LayerSwap facet calls `depositERC20` / `depositNative`. Then `tx.to` is the LI.FI diamond `0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE`, and the Depository is an inner call. Smart accounts (EIP-7702 and ERC-7579) also call it from inside `execute`.
9. **Admin triggers.** `AddressWhitelisted` and `AddressUpdatedInWhitelist` add a receiver that can take all new Depository deposits: treat both as high severity. `Paused` stops the Depository only; plain transfers to the wallets still work. The owner is one EOA on all nine chains.
10. **Robinhood Chain is live.** The Depository emitted 270 `Deposited` logs there in the pinned window, and wallet A pays out there (example: `0x34506343d19acd16bdb56913a40229f66831f5d0d3b711d50d6e7765bfd34ab2`, a native transfer).

---

## 15. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_DEPOSITED                    = '\xcfccc5211684bc31ce945214025a7453ba30a1ffcc38fcb691ce742437f3f256'
TOPIC_ADDRESS_WHITELISTED          = '\x4f783c179409b4127238bc9c990bc99b9a651666a0d20b51d6c42849eb88466d'
TOPIC_ADDRESS_REMOVED_FROM_WL      = '\x535611fb62fa2a833988f283b779e417e996813e44046f521d76c17b5943b08c'
TOPIC_ADDRESS_UPDATED_IN_WL        = '\x0f036efe7678a8f6bdd40a5748c686f23fc867ced9c237c484c652a43481ba75'
TOPIC_PAUSED                       = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_UNPAUSED                     = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_OWNERSHIP_TRANSFER_STARTED   = '\x38d16b8cac22d99fc7c124b9cd0de2d3fa1faef420bfe791d8c362d765e22700'
TOPIC_OWNERSHIP_TRANSFERRED        = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_ERC20_TRANSFER               = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors (chain-agnostic) =====
SEL_DEPOSIT_ERC20                  = '\xf4371f63'
SEL_DEPOSIT_NATIVE                 = '\x80a6de92'
SEL_ADD_TO_WHITELIST               = '\xe43252d7'
SEL_REMOVE_FROM_WHITELIST          = '\x8ab1d681'
SEL_UPDATE_WHITELISTED_ADDRESS     = '\x86d11066'
SEL_PAUSE                          = '\x8456cb59'
SEL_UNPAUSE                        = '\x3f4ba83a'
SEL_TRANSFER_OWNERSHIP             = '\xf2fde38b'
SEL_ACCEPT_OWNERSHIP               = '\x79ba5097'
SEL_GET_WHITELISTED_ADDRESSES      = '\x6d028027'
SEL_ERC20_TRANSFER                 = '\xa9059cbb'

-- ===== LayerswapDepository (one address on all nine chains) =====
ETH_DEPOSITORY                     = '\xe226e4825cb215abafad98fdd400583eab6a594f'
BASE_DEPOSITORY                    = '\xe226e4825cb215abafad98fdd400583eab6a594f'
ARB_DEPOSITORY                     = '\xe226e4825cb215abafad98fdd400583eab6a594f'
OP_DEPOSITORY                      = '\xe226e4825cb215abafad98fdd400583eab6a594f'
POLY_DEPOSITORY                    = '\xe226e4825cb215abafad98fdd400583eab6a594f'
BNB_DEPOSITORY                     = '\xe226e4825cb215abafad98fdd400583eab6a594f'
AVAX_DEPOSITORY                    = '\xe226e4825cb215abafad98fdd400583eab6a594f'
RH_DEPOSITORY                      = '\xe226e4825cb215abafad98fdd400583eab6a594f'
ARC_DEPOSITORY                     = '\xe226e4825cb215abafad98fdd400583eab6a594f'

-- ===== Layerswap wallets (EOAs, one address each on all nine chains) =====
ETH_WALLET_A_EOA                   = '\x2fc617e933a52713247ce25730f6695920b3befe'
ETH_WALLET_B_EOA                   = '\x08b00ceee2fb66029b53d76110b19eeaabfd1e65'
BASE_WALLET_A_EOA                  = '\x2fc617e933a52713247ce25730f6695920b3befe'
BASE_WALLET_B_EOA                  = '\x08b00ceee2fb66029b53d76110b19eeaabfd1e65'
ARB_WALLET_A_EOA                   = '\x2fc617e933a52713247ce25730f6695920b3befe'
ARB_WALLET_B_EOA                   = '\x08b00ceee2fb66029b53d76110b19eeaabfd1e65'
OP_WALLET_A_EOA                    = '\x2fc617e933a52713247ce25730f6695920b3befe'
OP_WALLET_B_EOA                    = '\x08b00ceee2fb66029b53d76110b19eeaabfd1e65'
POLY_WALLET_A_EOA                  = '\x2fc617e933a52713247ce25730f6695920b3befe'
POLY_WALLET_B_EOA                  = '\x08b00ceee2fb66029b53d76110b19eeaabfd1e65'
BNB_WALLET_A_EOA                   = '\x2fc617e933a52713247ce25730f6695920b3befe'
BNB_WALLET_B_EOA                   = '\x08b00ceee2fb66029b53d76110b19eeaabfd1e65'
AVAX_WALLET_A_EOA                  = '\x2fc617e933a52713247ce25730f6695920b3befe'
AVAX_WALLET_B_EOA                  = '\x08b00ceee2fb66029b53d76110b19eeaabfd1e65'
RH_WALLET_A_EOA                    = '\x2fc617e933a52713247ce25730f6695920b3befe'
RH_WALLET_B_EOA                    = '\x08b00ceee2fb66029b53d76110b19eeaabfd1e65'
ARC_WALLET_A_EOA                   = '\x2fc617e933a52713247ce25730f6695920b3befe'
ARC_WALLET_B_EOA                   = '\x08b00ceee2fb66029b53d76110b19eeaabfd1e65'
-- Depository owner, the same EOA on all nine chains:
ETH_DEPOSITORY_OWNER_EOA           = '\xb6103502673173ab5df6a57ac3017db4e16af399'
```

---

## 16. Verification & sources

How the constants in this file were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `evm/src/LayerswapDepository.sol` (OpenZeppelin v5 `Ownable2Step`, `Pausable` for the inherited events). The live `Deposited` topic0 appears at the Depository on all nine chains.
- **Addresses:** the Depository address comes from the LI.FI integration config (`layerSwapDepository`, 43 networks, all nine target chains included). `eth_getCode` returns 3,876 bytes with code hash `0xe2c5b091f98ff37764289b288afff06c0603e81a35cf4e55af17526838228831` on all nine chains. `getWhitelistedAddresses()` returns wallet A and wallet B on all nine chains. `owner()` returns `0xB6103502673173ab5Df6A57Ac3017Db4e16af399` on all nine chains; that address has no code on any of them. `paused()` returns `false` on all nine chains. The Layerswap docs name both wallets (the refunds example uses wallet B; the deposit-widget example uses wallet A).
- **Link key:** the public explorer API (`GET /api/v2/explorer/{tx}`, the endpoint of the `layerswap/layerswap-explorer` app) returned swap `55ed2f2f-9d7a-4cc7-b0ba-dd5207e2911e`, `sequence_number` 17,938,734, for Ethereum deposit `0x9bef18faa4ee8990435683563d0b6075e29c2bd882102fff14ff61b2df6da7de`, whose `Deposited.id` is 17,938,734. It also returned swap `fa4b1380-1eb0-4247-9cb2-356db0fef31e` (sequence number 17,938,823) for Base deposit `0xc95e66c07ae653338ecdac4057a060fa44259c6739e29a468ff60c72d216fad9`, whose `Deposited.id` is 17,938,823 (`0x111b987`).
- **Value movement, read from receipts:** Ethereum `0x9bef18faa4ee8990435683563d0b6075e29c2bd882102fff14ff61b2df6da7de` (QNT moves from the LI.FI diamond to wallet B, then `Deposited`). Base `0xc95e66c07ae653338ecdac4057a060fa44259c6739e29a468ff60c72d216fad9` (native, `token` = zero address, `receiver` = wallet A). Robinhood Chain payout `0x34506343d19acd16bdb56913a40229f66831f5d0d3b711d50d6e7765bfd34ab2` (native transfer from wallet A, no logs). Arbitrum payout `0xf701b7b90ebd87899b4de20e3516e47cb1319a441b69ef62fda12177c0073d4f` and Ethereum payout `0xdd335f399935e11c303bb8a3438caf894504afb95c2584af12ab5dadadfc4357` (both sent by wallet B through a DEX router).
- **Activity:** `Deposited` at the Depository in the pinned 12-hour window 2026-09-28 00:00–12:00 UTC: Ethereum 153, Base 506, Arbitrum 331, Optimism 163, Polygon 72, BNB 149, Avalanche 20, Robinhood Chain 270. The Ethereum count was measured twice (with and without the emitter filter) with the same result. These counts say nothing about the plain-transfer and deposit-address paths.
- **Chain coverage:** all nine chains carry the Depository and both wallets. The Layerswap network list (`/api/v2/networks`) includes all nine chain ids.

Authoritative sources:
- [layerswap/layerswap-depository](https://github.com/layerswap/layerswap-depository) — `evm/src/LayerswapDepository.sol`, `evm/README.md`, `evm/script/DeployLayerswapDepository.s.sol`.
- [layerswap/layerswap-docs](https://github.com/layerswap/layerswap-docs) — `concepts/refunds.mdx`, `widget/deposit-widget.mdx`.
- Docs — [Fund via the Depository](https://docs.layerswap.io/api/funding/depository) · [EVM chains](https://docs.layerswap.io/api/funding/networks/evm) · [Execute deposit actions](https://docs.layerswap.io/api/funding/transfer) · [Funding methods](https://docs.layerswap.io/concepts/funding-methods) · [Gasless deposits](https://docs.layerswap.io/api/funding/gasless) · [Swap lifecycle](https://docs.layerswap.io/concepts/swap-lifecycle) · [Refunds](https://docs.layerswap.io/concepts/refunds) · [Track swaps](https://docs.layerswap.io/api/track-swaps) · [Security](https://docs.layerswap.io/concepts/security) · [Get Swap Details](https://docs.layerswap.io/api-reference/swaps/get-swap-details) (`SwapMetadataModel.sequence_number`).
- API — [networks](https://api.layerswap.io/api/v2/networks) · explorer `https://api.layerswap.io/api/v2/explorer/{tx hash}` · [layerswap/layerswap-explorer](https://github.com/layerswap/layerswap-explorer) (`lib/layerSwapApiClient.ts`).
- [lifinance/contracts `config/layerswap.json`](https://github.com/lifinance/contracts/blob/main/config/layerswap.json) — the Depository address per network.
