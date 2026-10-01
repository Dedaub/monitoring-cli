# Mini Bridge (Chaineye) — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB + Avalanche; NOT Robinhood)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the official Chaineye docs ("MiniBridge API Docs", "Bridge Batch Requests"), the official open-source repository `DeFiEye/Mini-Bridge` (`public_contracts/helper.sol`, `public_contracts/gasrefill.sol`), the live bridge config `https://minibridge-conf.chaineye.tools/conf.json`, and an archived copy of that config (version `1763446511`, 2025-11-18).
**Scope:** the Mini Bridge maker EOA, its optional helper contract and its gas-refill contract. Topics and selectors are chain-agnostic. The maker and the helper use the same address on every chain.

Mini Bridge is a small-amount ETH maker bridge run by the Chaineye team. A user sends ETH **directly to one EOA**, `0x00000000000007736e2F9aA5630B8c812E1F3fc9`, on the source chain. The **last four decimal digits of the value in wei** carry the "confirm code" `8000 + destination internalId`. Chaineye's server then sends ETH from the same EOA to the user on the destination chain. On chains where ETH is not the native coin (Polygon, BNB Smart Chain, Avalanche) the user sends the chain's ERC-20 "ETH" token instead, with the same code.

There is no deposit event and no payout event in the main path. The capture is a native transfer or an ERC-20 `Transfer` to or from the maker EOA. There is no on-chain link key: Chaineye's status API (`https://minibridge-conf.chaineye.tools/<lowercase sender>.json`) matches a source transaction to its destination transaction.

**Status of the service:** the live config (version `1787551969`, 2026-08-24) lists **no chains and no routes**. The archived config of 2025-11-18 lists 46 chains and 1,669 routes. Treat the bridge as paused or retired, but keep the maker in monitors: an idle EOA can still receive funds.

---

## 0. Components & flow

| Component | Address | Role |
|-----------|---------|------|
| **Bridge maker EOA** | `0x00000000000007736e2F9aA5630B8c812E1F3fc9` | Receives deposits (native ETH, or the ERC-20 ETH token) and sends payouts. Same address on every EVM chain. |
| **MiniBridge_Helper** | `0x000000000000Bd696655814b68C2f67e399ab4e5` | Lets a contract bridge: forwards ETH or ERC-20 to the maker and emits `MiniBridge_Request`. |
| **MiniBridge_GasRefill** | `0xb20df358A62834695062d09C1B83cd3714443a35` | Payout helper on ERC-20-ETH chains: the maker calls it to send the ERC-20 ETH token plus some native gas coin to the user. |

Flow:

1. **Source:** the user sends `value = receive amount + fee + (8000 + to_id)` wei to the maker. Optional `calldata` = the destination address (EVM) when it differs from the sender. On an `evm_erc20` chain: ERC-20 `transfer(maker, value)` of the chain's ETH token, with the destination address appended to the calldata. From a contract: `Helper.transferETH(to)` with `msg.value`.
2. **Destination:** the maker sends native ETH to the user (no log), or on an `evm_erc20` chain an ERC-20 `Transfer` of the ETH token from the maker (or through `GasRefill.transfer`, which also sends native gas).
3. **Refund:** handled off chain by Chaineye (status `failed` in the API). No refund event.

---

## 1. Topics (chain-agnostic)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0xd7d82185d24c1bf51ee43dbe88a15f93315dce7326e45871c7a9b95940ba2e1d` | `MiniBridge_Request(address token, bool trusted, address from, uint256 to, uint256 amount)` | MiniBridge_Helper. `token` = `0x0000000000000000000000000000000000000000` for ETH. `to` = destination address as `uint256` (non-EVM capable). `trusted = false` from `logTransferERC20` (the server must check the ERC-20 `Transfer`). |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20 ETH token on Polygon / BNB / Avalanche: deposit (`to` = maker) and payout (`from` = maker). |

The maker itself emits nothing (it is an EOA). Native deposits and payouts have no log.

---

## 2. Function signatures (chain-agnostic)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4329db46` | `transferETH(uint256 to)` | Helper. Payable. Forwards `msg.value` to the maker. Emits `MiniBridge_Request(0x0, true, msg.sender, to, msg.value)`. |
| `0xb756fb69` | `transferERC20(address token, uint256 to, uint256 amount)` | Helper. Pulls `token` from the caller to the maker (balance-delta measured). Emits `MiniBridge_Request(token, true, …)`. |
| `0x7c128aef` | `logTransferERC20(address token, uint256 to, uint256 amount)` | Helper. Emits only (`trusted = false`); the caller transfers the token itself in the same transaction. |
| `0xa9059cbb` | `transfer(address to, uint256 amount)` | **Two meanings.** ERC-20 `transfer` (user deposit of the ETH token to the maker). Also `MiniBridge_GasRefill.transfer(address payable to, uint256 amount)` (payable, maker only): sends `amount` of the ETH token from the maker to `to` plus `msg.value` native gas. Disambiguate by the `to` contract. |
| `0x2a31f6b4` | `proxyCall(address target, bytes call)` | GasRefill. Maker only. Arbitrary call from the refill contract. |

---

## 3. Confirm codes (destination encoding)

`confirm code = 8000 + internalId` of the destination, in the last four digits of the value (wei, or the 18-decimal ERC-20 ETH token). A gas refill uses `8500 + internalId` and adds 0.0005 ETH. Internal ids from the archived official config:

| Chain | Chain ID | internalId | Confirm code | Gas-refill code | Chain type in the config |
|-------|----------|-----------|--------------|-----------------|--------------------------|
| Arbitrum One | 42161 | 1 | 8001 | 8501 | evm |
| Optimism | 10 | 2 | 8002 | 8502 | evm |
| Base | 8453 | 3 | 8003 | 8503 | evm |
| Ethereum | 1 | 10 | 8010 | 8510 | evm |
| Polygon PoS | 137 | 12 | 8012 | 8512 | evm_erc20 (ETH token `0x7ceb23fd6bc0add59e62ac25578270cff1b9f619`) |
| BNB Smart Chain | 56 | 18 | 8018 | 8518 | evm_erc20 (ETH token `0x2170ed0880ac9a755fd29b2688956bd959f933f8`) |
| Avalanche C-Chain | 43114 | 19 | 8019 | 8519 | evm_erc20 (ETH token `0x49d5c2bdffac6ce2bfdb6640f4f80f226bc10bab`) |
| Robinhood Chain | 4663 | — | — | — | not supported |

Off-target ids include Linea 4, zkSync Era 5, Manta 7, Scroll 8, Starknet 9, Mantle 11, Metis 20, Blast 22, Mode 23, opBNB 24, Zora 26, X Layer 29, Solana 30, BOB 31, Taiko 40, Unichain 49, Ink 52, Soneium 53, Abstract 54, Berachain 57, Sonic 58. The config also has "gasswap" ids 812 / 818 / 819 for Polygon / BNB / Avalanche (semantics not documented; unverified). All 301 routes from the seven target chains in the archived config were ETH → ETH.

Decode in SQL: `value % 10000` gives the code; `code - 8000` (or `- 8500`) gives the destination internalId. Docs example: Arbitrum → Linea for 0.01 ETH received with a 0.00045 ETH fee = `10450000000008004` wei.

---

## 4. Addresses — per chain

All existence-checked with `eth_getCode` on 2026-09-29.

| Chain | ID | Maker EOA `0x00000000000007736e2F9aA5630B8c812E1F3fc9` | Helper `0x000000000000Bd696655814b68C2f67e399ab4e5` | GasRefill `0xb20df358A62834695062d09C1B83cd3714443a35` |
|-------|----|------------------------------------------|-------------------------------------------|---------------------------------------------|
| Ethereum | 1 | EOA, nonce 24139 | 1150 B | `0x` |
| Base | 8453 | EOA, nonce 51018 | 1150 B | `0x` |
| Arbitrum One | 42161 | EOA, nonce 46261 | 1150 B | `0x` |
| Optimism | 10 | EOA, nonce 17560 | 1150 B | `0x` |
| Polygon PoS | 137 | EOA, nonce 6432 | 1150 B | 998 B |
| BNB Smart Chain | 56 | EOA, nonce 21823 | 1150 B | 998 B |
| Avalanche C-Chain | 43114 | EOA, nonce 2107 | 1150 B | 998 B |
| Robinhood Chain | 4663 | **nonce 0, no code** | `0x` | `0x` |

The helper has the same 1150-byte code on all seven chains. The three GasRefill contracts have different code hashes (each embeds its chain's ETH token as a constant). The alternate helper `0x257312be423cEB2D43683f44b101dC10dfEe3e22` (opBNB, Zora, Sonic in the config) has no code on any of the eight chains. The maker address has a vanity prefix of twelve zero digits.

---

## 5. Cross-chain summary

| Chain | ID | Maker active | Helper | GasRefill | Confirm code |
|-------|----|-------------|--------|-----------|--------------|
| Ethereum | 1 | yes | yes | — | 8010 |
| Base | 8453 | yes | yes | — | 8003 |
| Arbitrum One | 42161 | yes | yes | — | 8001 |
| Optimism | 10 | yes | yes | — | 8002 |
| Polygon PoS | 137 | yes (ERC-20 ETH) | yes | yes | 8012 |
| BNB Smart Chain | 56 | yes (ERC-20 ETH) | yes | yes | 8018 |
| Avalanche C-Chain | 43114 | yes (ERC-20 ETH) | yes | yes | 8019 |
| Robinhood Chain | 4663 | no | no | no | — |

"Maker active" = the EOA has sent transactions (nonce > 0) on that chain.

---

## 6. Proxies

None. The maker is an EOA. `MiniBridge_Helper` and `MiniBridge_GasRefill` are plain immutable contracts (source in the official repository; no owner, no upgrade path; the GasRefill entrypoints are restricted to `msg.sender == BRIDGE`, the maker EOA). There is no `Upgraded` event to watch.

---

## 7. Detection invariants & gotchas

1. **The main deposit has no log.** A native ETH transfer to `0x00000000000007736e2F9aA5630B8c812E1F3fc9` is visible only in native-transfer / trace data. Key on `to = maker` and `value % 10000` in 8001–8058 or 8501–8558.
2. **The payout has no log either** on ETH-native chains: it is a native transfer from the maker. On Polygon / BNB / Avalanche it is an ERC-20 `Transfer` of the ETH token with `from = maker`, or a `GasRefill.transfer` call by the maker.
3. **The maker both receives and pays.** Direction tells deposit from payout: `to = maker` is a deposit, `from = maker` is a payout. There is no link key; use Chaineye's status API, or match amount minus fee and time.
4. **Recipient override.** The calldata of the deposit (EVM) or the bytes appended to the ERC-20 `transfer` calldata carry the destination address. With no calldata, the recipient is the sender.
5. **The helper event is a marker, not proof, for `logTransferERC20`.** `trusted = false` means the token transfer must be checked separately.
6. **Selector collision:** `0xa9059cbb` is both ERC-20 `transfer` and `GasRefill.transfer`.
7. **Paused service.** The live config is empty since version `1787551969` (2026-08-24). Deposits sent now may not be paid out by the operator.
8. **Large-transfer trigger:** native or ERC-20 transfers to or from the maker. Archived route limits were small (for example 0.0001–0.1 ETH), so a large transfer to the maker is anomalous.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_MINIBRIDGE_REQUEST         = '\xd7d82185d24c1bf51ee43dbe88a15f93315dce7326e45871c7a9b95940ba2e1d'
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors =====
SEL_HELPER_TRANSFER_ETH          = '\x4329db46'
SEL_HELPER_TRANSFER_ERC20        = '\xb756fb69'
SEL_HELPER_LOG_TRANSFER_ERC20    = '\x7c128aef'
SEL_TRANSFER                     = '\xa9059cbb'
SEL_GASREFILL_PROXY_CALL         = '\x2a31f6b4'

-- ===== Maker EOA (same on Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche) =====
ETH_MINIBRIDGE_MAKER_EOA         = '\x00000000000007736e2f9aa5630b8c812e1f3fc9'
BASE_MINIBRIDGE_MAKER_EOA        = '\x00000000000007736e2f9aa5630b8c812e1f3fc9'
ARB_MINIBRIDGE_MAKER_EOA         = '\x00000000000007736e2f9aa5630b8c812e1f3fc9'
OP_MINIBRIDGE_MAKER_EOA          = '\x00000000000007736e2f9aa5630b8c812e1f3fc9'
POLY_MINIBRIDGE_MAKER_EOA        = '\x00000000000007736e2f9aa5630b8c812e1f3fc9'
BNB_MINIBRIDGE_MAKER_EOA         = '\x00000000000007736e2f9aa5630b8c812e1f3fc9'
AVAX_MINIBRIDGE_MAKER_EOA        = '\x00000000000007736e2f9aa5630b8c812e1f3fc9'

-- ===== Helper (same address on the seven chains) =====
ETH_MINIBRIDGE_HELPER            = '\x000000000000bd696655814b68c2f67e399ab4e5'
BASE_MINIBRIDGE_HELPER           = '\x000000000000bd696655814b68c2f67e399ab4e5'
ARB_MINIBRIDGE_HELPER            = '\x000000000000bd696655814b68c2f67e399ab4e5'
OP_MINIBRIDGE_HELPER             = '\x000000000000bd696655814b68c2f67e399ab4e5'
POLY_MINIBRIDGE_HELPER           = '\x000000000000bd696655814b68c2f67e399ab4e5'
BNB_MINIBRIDGE_HELPER            = '\x000000000000bd696655814b68c2f67e399ab4e5'
AVAX_MINIBRIDGE_HELPER           = '\x000000000000bd696655814b68c2f67e399ab4e5'

-- ===== GasRefill (ERC-20-ETH chains only) =====
POLY_MINIBRIDGE_GASREFILL        = '\xb20df358a62834695062d09c1b83cd3714443a35'
BNB_MINIBRIDGE_GASREFILL         = '\xb20df358a62834695062d09c1b83cd3714443a35'
AVAX_MINIBRIDGE_GASREFILL        = '\xb20df358a62834695062d09c1b83cd3714443a35'

-- ===== ERC-20 "ETH" token per evm_erc20 chain =====
POLY_WETH                        = '\x7ceb23fd6bc0add59e62ac25578270cff1b9f619'
BNB_ETH_TOKEN                    = '\x2170ed0880ac9a755fd29b2688956bd959f933f8'
AVAX_WETH_E                      = '\x49d5c2bdffac6ce2bfdb6640f4f80f226bc10bab'
-- Robinhood Chain (4663): not supported; the maker has nonce 0 there
```

---

## 9. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(sig)` from `public_contracts/helper.sol` and `public_contracts/gasrefill.sol` of the official repository.
- **Addresses:** the maker and the helper from the official docs and the source constants (`BRIDGE`), the GasRefill and ERC-20 ETH tokens from the archived official config. All existence-checked with `eth_getCode` on the eight chains (§4).
- **Confirm codes:** official docs (rule and Linea example) plus `internalId` values of the archived config.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):** `MiniBridge_Request` at the helper: Ethereum 0, Base 0, Arbitrum 0, Optimism 0, Polygon 0, BNB 0, Avalanche 0. ERC-20 transfers to or from the maker on Ethereum and Base: 0. Native transfers have no log and were not counted. The maker nonces in §4 show past activity on all seven chains.

Authoritative sources:
- Docs — [MiniBridge API Docs](https://docs.chaineye.tools/minibridge-api-docs) · [Bridge Batch Requests](https://docs.chaineye.tools/minibridge-api-docs/bridge-batch-requests)
- Config — [conf.json (live)](https://minibridge-conf.chaineye.tools/conf.json) · archived copy via the Internet Archive (`web.archive.org`, version `1763446511`)
- Repository — [DeFiEye/Mini-Bridge](https://github.com/DeFiEye/Mini-Bridge) (`public_contracts/helper.sol`, `public_contracts/gasrefill.sol`)
- Explorers — [Etherscan maker ("Chaineye: Mini Bridge")](https://etherscan.io/address/0x00000000000007736e2f9aa5630b8c812e1f3fc9) · [Arbiscan helper](https://arbiscan.io/address/0x000000000000Bd696655814b68C2f67e399ab4e5#code)
