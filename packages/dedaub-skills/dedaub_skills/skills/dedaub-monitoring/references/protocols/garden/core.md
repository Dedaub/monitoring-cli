# Garden Finance — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + BNB + Robinhood + Arc; NOT Avalanche, Optimism, Polygon)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains (Arc (5042) added and activity re-checked 2026-10-05), the Garden API (`https://api.garden.finance/v2/chains` and `/v2/schemas`), the verified HTLC sources (Blockscout, Sourcify), `gardenfi/garden-sol` and `gardenfi/docs`. Topics and selectors recomputed as `keccak256(sig)`; every HTLC existence-checked with `eth_getCode` and identified with `token()` and `version()` by `eth_call`; sample receipts decoded.
**Scope:** Garden's per-asset HTLC (hashed time-lock) contracts on Ethereum (1), Base (8453), Arbitrum One (42161), BNB Smart Chain (56), Robinhood Chain (4663) and Arc (5042). Avalanche, OP Mainnet and Polygon have no Garden HTLC. The other leg of most swaps is Bitcoin (or Litecoin, Lightning, Solana, Starknet, Sui and others). Topics and selectors are chain-agnostic; addresses are network-specific.

Garden swaps between Bitcoin and other chains with **atomic swaps**. Each EVM asset has its own small, immutable HTLC contract (one `token()` per contract). A swap locks funds on both chains under the same `sha256` secret hash: the user locks on the source chain, a solver (filler) locks on the destination chain, the user claims the solver's lock by revealing the secret, and the solver uses the revealed secret to claim the user's lock. If nobody claims before the timelock, the initiator refunds. There is no pool, no bridge mint and no relayer message.

Three facts a monitor must know before indexing:

1. **The link key is the secret hash, and it is on chain on both sides.** `Initiated.secretHash` (topic2) on one chain equals the hash in the HTLC of the other chain (the Bitcoin HTLC script, or `Initiated.secretHash` on another EVM chain). The secret itself appears in `Redeemed.secret` and in the Bitcoin witness. `orderID` is per chain: `sha256(abi.encode(chainid, secretHash, initiator, redeemer, timelock, amount, htlcAddress))`.
2. **`Redeemed` pays the redeemer, who is often the solver.** On an EVM → Bitcoin swap, the EVM `Redeemed` pays the solver; the user's BTC arrives on Bitcoin. On a Bitcoin → EVM swap, the EVM `Initiated` is the solver's lock and the EVM `Redeemed` pays the user.
3. **Each token has its own HTLC, and the list changes.** Read the live list from `/v2/chains` (`assets[].htlc.address`). Old HTLCs stay deployed and can still hold or refund orders.

**Incident.** On 26–27 July 2026 an attacker inserted fake records into an independent solver's off-chain database, and that solver released about 450,000 USD of USDT into HTLCs on Ethereum, Base, Arbitrum and BNB for swaps nobody had funded. Garden stated that the HTLC contracts worked as designed, and it took its app offline for an investigation. On 2026-09-29 the API lists no USDT HTLC except on Ethereum; the latest HTLC events on the explorers are dated 2026-09-19 (Ethereum WBTC, Base cbBTC) and 2026-09-20 (Arbitrum WBTC), and the pinned window had none. On 2026-10-05 the API still marks every asset `is_active`, but there were no HTLC logs on Ethereum, Base, Arbitrum or Robinhood in the 7 days before, and none on Arc in the ~22 hours before.

---

## 0. Contract families & versions

| Family | Source | Events | Where |
|--------|--------|--------|-------|
| **HTLC v3** (`version()` = "3", solc 0.8.28; `ArbHTLC` on Arbitrum and the 9,048-byte build on Arbitrum and Robinhood) | verified on Blockscout / Sourcify; ABI also served by `/v2/schemas` | `Initiated` with **`amount` indexed**, `InitiatedWithDestinationData`, `Redeemed`, `Refunded`, `EIP712DomainChanged` | All live HTLCs (§3–§7) and several delisted ones |
| HTLC (older, solc 0.8.18, `garden-sol` `contracts/htlc/HTLC.sol` lineage) | verified on Blockscout | `Initiated` with `amount` **not** indexed (same topic0), `Redeemed`, `Refunded`; `orderID = sha256(abi.encode(secretHash, initiator))` in the repository version | Ethereum and Base `0xd8a6e3fca403d79b6ad6216b60527f51cc967d39` (USDC), Ethereum and Arbitrum `0xDC74a45e86DEdf1fF7c6dac77e0c2F082f9E4F72` (iBTC); last events 2025-10 and 2025-08 |
| HTLC (solc 0.8.28, `amount` not indexed) | Sourcify exact match | as the older family | BNB `0xd8a6e3fca403d79b6ad6216b60527f51cc967d39` (USDC) |

The v3 contract is an initialisable template: `initialise(address token)` sets the token once (`isInitialized`), and the EIP-712 domain is name "HTLC", version "3".

**Garden chain names** (the API's `chain` field): `ethereum` (`evm:1`), `base` (`evm:8453`), `arbitrum` (`evm:42161`), `bnbchain` (`evm:56`), `robinhood` (`evm:4663`), `arc` (`evm:5042`, §7a). Outside the targets the API also lists `hypercore` (`evm:1337`), `hyperevm` (`evm:999`), `ink` (`evm:57073`), `tempo` (`evm:4217`), `bitcoin`, `lightning`, `litecoin`, `spark`, `solana` and `starknet`. Avalanche, OP Mainnet and Polygon are not listed.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Emitter = an HTLC contract (§3–§7).

| topic0 | Event | Side |
|--------|-------|------|
| `0x01b41cbd4bbcc3c5b968a04d3fbdd8c1648a39ff6d9a3929b4840cea1142bc65` | `Initiated(bytes32 indexed orderID, bytes32 indexed secretHash, uint256 indexed amount)` | **Lock** (source leg for the user; destination leg when the solver locks). The token `Transfer` funder → HTLC is in the same transaction. In the older family `amount` is in `data`, not in topic3. |
| `0x380328b26f928a9e51ec19f8e2199a2bce34db266d093d1e0104bce139ed7555` | `InitiatedWithDestinationData(bytes32 indexed orderID, bytes32 indexed secretHash, uint256 indexed amount, bytes destinationData)` | Lock with extra destination data (v3 only). Emitted **in addition to** `Initiated` by the `...destinationData` overloads. |
| `0x4c9a044220477b4e94dbb0d07ff6ff4ac30d443bef59098c4541b006954778e2` | `Redeemed(bytes32 indexed orderID, bytes32 indexed secretHash, bytes secret)` | **Claim.** Pays the stored redeemer (`token.safeTransfer(redeemer, amount)`). `secret` reveals the preimage of `secretHash`. |
| `0xfe509803c09416b28ff3d8f690c8b0c61462a892c46d5430c8fb20abe472daf0` | `Refunded(bytes32 indexed orderID)` | **Refund** to the initiator, after the timelock (`refund`) or early with the redeemer's EIP-712 consent (`instantRefund`). |
| `0x0a6387c9ea3628b88a633bb4f3b151770f70085117a15f9bf3787cda53f13d31` | `EIP712DomainChanged()` | Status only. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | The token's value leg: funder → HTLC on lock; HTLC → redeemer on claim; HTLC → initiator on refund. |

**Topic collision.** `Refunded(bytes32)` is a common signature. In the pinned window every `Refunded` log on the eight chains came from LI.FI's `InputSettlerEscrowLIFI` at `0x00fc00edbe7c003b006f870068c548940000223e` (Ethereum 6, Base 9, Arbitrum 5, BNB 16, Robinhood 4), not from Garden. Always filter on the HTLC addresses.

**Docs mismatch.** The `contracts/evm.mdx` page of `gardenfi/docs` shows `Initiated(bytes32 indexed orderID)` and `Redeemed(bytes32 indexed orderID, bytes secret)`. No deployed HTLC emits those; the verified sources and the `/v2/schemas` ABI emit the three-field events above.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x97ffc7ae` | `initiate(address redeemer, uint256 timelock, uint256 amount, bytes32 secretHash)` | Lock by `msg.sender`; `transferFrom(msg.sender, HTLC, amount)`. Emits `Initiated`. |
| `0x4ede0ab7` | `initiate(address redeemer, uint256 timelock, uint256 amount, bytes32 secretHash, bytes destinationData)` | v3. Emits `Initiated` and `InitiatedWithDestinationData`. |
| `0x13d4a787` | `initiateOnBehalf(address initiator, address redeemer, uint256 timelock, uint256 amount, bytes32 secretHash)` | `msg.sender` funds; `initiator` gets any refund. |
| `0xa66a8641` | `initiateOnBehalf(address initiator, address redeemer, uint256 timelock, uint256 amount, bytes32 secretHash, bytes destinationData)` | v3. |
| `0xd4705e9e` | `initiateWithSignature(address initiator, address redeemer, uint256 timelock, uint256 amount, bytes32 secretHash, bytes signature)` | Gasless lock with the initiator's EIP-712 signature; funds pulled from `initiator`. |
| `0xf7ff7207` | `redeem(bytes32 orderID, bytes secret)` | **Claim.** Anyone may call; pays the stored redeemer. Emits `Redeemed`. |
| `0x7249fbb6` | `refund(bytes32 orderID)` | After `initiatedAt + timelock` blocks. Pays the initiator. Emits `Refunded`. |
| `0xedaf5fac` | `instantRefund(bytes32 orderID, bytes signature)` | Early refund with the redeemer's consent. Emits `Refunded`. |
| `0x9c3f1e90` | `orders(bytes32)` | View: `(initiator, redeemer, initiatedAt, timelock, amount, fulfilledAt)`. |
| `0xfc0c546a` | `token()` | View: the HTLC's token. |
| `0x54fd4d50` | `version()` | View: "3" on v3. |
| `0x392e53cd` | `isInitialized()` | View (v3). |
| `0x9d6a890f` | `initialise(address _token)` | v3 one-time setter. |
| `0x4882a380` | `instantRefundDigest(bytes32 orderID)` | View: EIP-712 digest the redeemer signs. |

Timelocks are block counts relative to `initiatedAt` (API: Ethereum source 7,200 / destination 600; Base 43,200 / 3,600; Arbitrum 432,000 / 36,000; BNB 115,200 / 9,600; Robinhood 432,000 / 36,000; Arc 86,400 / 7,200).

---

## 3. Addresses — Ethereum (chain ID 1)

| Role | Address | Token | Notes |
|------|---------|-------|-------|
| **HTLC v3 WBTC** (API) | `0xD781a2abB3FCB9fC0D1Dd85697c237d06b75fe95` | WBTC `0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599` | 8,452 B; last events 2026-09-19. |
| **HTLC v3 cbBTC** (API) | `0xe35d025d0f0d9492db4700FE8646f7F89150eC04` | cbBTC `0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf` | Same address on Base. |
| **HTLC v3 USDC** (API) | `0x5fA58e4E89c85B8d678Ade970bD6afD4311aF17E` | USDC `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | Same address on Base and BNB (other tokens there) and on Arc (USDC, §7a). |
| **HTLC v3 USDT** (API) | `0xCF5E5e28848cFe779f7Fb711C57857Cb3b144A19` | USDT `0xdAC17F958D2ee523a2206206994597C13D831ec7` | Same address on Base and BNB (USDT, delisted there). |
| HTLC iBTC (older family) | `0xDC74a45e86DEdf1fF7c6dac77e0c2F082f9E4F72` | iBTC `0x20157dbabb84e3bbfe68c349d0d44e48ae7b5ad2` | Not in the API; last events 2025-08-25. |
| HTLC USDC (older family) | `0xd8a6e3fca403d79b6ad6216b60527f51cc967d39` | USDC | Not in the API; last events 2025-10-29. |

## 4. Addresses — Base (chain ID 8453)

| Role | Address | Token | Notes |
|------|---------|-------|-------|
| **HTLC v3 cbBTC** (API) | `0xe35d025d0f0d9492db4700FE8646f7F89150eC04` | cbBTC `0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf` | Last events 2026-09-19. |
| **HTLC v3 cbLTC** (API) | `0x7aE2D05e6fD9F12A9D4bA5C61384F4D0b90843eb` | cbLTC `0xcb17C9Db87B595717C857a08468793f5bAb6445F` | |
| **HTLC v3 USDC** (API) | `0x227A436e93AAEf856ed406713F2bc3D110A7b797` | USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | |
| HTLC v3 USDC (delisted) | `0x5fA58e4E89c85B8d678Ade970bD6afD4311aF17E` | USDC | Last events 2025-11-03. |
| HTLC v3 USDT (delisted) | `0xCF5E5e28848cFe779f7Fb711C57857Cb3b144A19` | USDT `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2` | No logs on the explorer's latest page. |
| HTLC USDC (older family) | `0xd8a6e3fca403d79b6ad6216b60527f51cc967d39` | USDC | Last events 2025-10-29. |

## 5. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | Token | Notes |
|------|---------|-------|-------|
| **HTLC v3 WBTC** (API; `ArbHTLC`) | `0xb5AE9785349186069C48794a763DB39EC756B1cF` | WBTC `0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f` | 9,048 B; last events 2026-09-20. |
| HTLC v3 USDC (delisted) | `0x227A436e93AAEf856ed406713F2bc3D110A7b797` | USDC `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | No logs on the explorer's latest page. |
| HTLC iBTC (older family) | `0xDC74a45e86DEdf1fF7c6dac77e0c2F082f9E4F72` | iBTC `0x050c24dbf1eec17babe5fc585f06116a259cc77a` | Last events 2025-08-25. |

Not Garden on Arbitrum: `0xd8a6e3fca403d79b6ad6216b60527f51cc967d39` is a verified `Multicall` (961 B).

## 6. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | Token | Notes |
|------|---------|-------|-------|
| **HTLC v3 BTCB** (API) | `0xe74784E5A45528fDEcB257477DD6bd31c8ef0761` | BTCB `0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c` | Sourcify exact match. |
| HTLC v3 USDC (delisted) | `0x5fA58e4E89c85B8d678Ade970bD6afD4311aF17E` | USDC `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` | |
| HTLC v3 USDT (delisted) | `0xCF5E5e28848cFe779f7Fb711C57857Cb3b144A19` | USDT `0x55d398326f99059fF775485246999027B3197955` | |
| HTLC USDC (0.8.28, `amount` not indexed) | `0xd8a6e3fca403d79b6ad6216b60527f51cc967d39` | USDC `0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d` | |

## 7. Addresses — Robinhood Chain (chain ID 4663)

| Role | Address | Token | Notes |
|------|---------|-------|-------|
| **HTLC v3 cbBTC** (API) | `0x147bf8d6Fa3392D2376ef5F6738F3D2931BdDb49` | cbBTC `0xCEC185eB182c47d1bA1EFc84e6959e18cd620Be4` | 9,048 B; `version()` = "3". |
| **HTLC v3 USDG** (API) | `0xd8BF1D34AE05B6F631dE898aE9F8f91e08661B59` | USDG `0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168` | 9,048 B; `version()` = "3". |

The Robinhood explorer API was behind a challenge page, so these two were identified by RPC (`token()`, `version()`), not by verified source.

## 7a. Addresses — Arc (chain ID 5042)

| Role | Address | Token | Notes |
|------|---------|-------|-------|
| **HTLC v3 USDC** (API, schema `evm:htlc_erc20`) | `0x5fA58e4E89c85B8d678Ade970bD6afD4311aF17E` | USDC `0x3600000000000000000000000000000000000000` (Arc's native-gas USDC, ERC-20 interface, 6 decimals) | 8,452 B (same size as Ethereum v3); `token()` and `version()` = "3" by `eth_call` (2026-10-05). No logs in ~160,000 blocks (~22 h) to 2026-10-05. Same address as the Ethereum USDC HTLC. |

---

## 8. Cross-chain summary

| Chain | ID | Live HTLCs (API) | Delisted / older HTLCs | Window `Initiated` / `Redeemed` / `Refunded` (Garden) |
|-------|----|------------------|------------------------|--------------------------------------------------------|
| Ethereum | 1 | WBTC, cbBTC, USDC, USDT | iBTC, USDC (older) | 0 / 0 / 0 |
| Base | 8453 | cbBTC, cbLTC, USDC | USDC, USDT (v3); USDC (older) | 0 / 0 / 0 |
| Arbitrum One | 42161 | WBTC | USDC (v3); iBTC (older) | 0 / 0 / 0 |
| BNB Smart Chain | 56 | BTCB | USDC, USDT (v3); USDC (0.8.28) | 0 / 0 / 0 |
| Robinhood Chain | 4663 | cbBTC, USDG | — | 0 / 0 / 0 |
| Arc | 5042 | USDC | — | not in the pinned window (no logs ~22 h to 2026-10-05) |
| Avalanche C-Chain | 43114 | — (`0x` at every address of this file) | — | 0 / 0 / 0 (any emitter) |
| OP Mainnet | 10 | — | — | 0 / 0 / 0 |
| Polygon PoS | 137 | — | — | 0 / 0 / 0 |

Shared addresses (`0xe35d025d0f0d9492db4700FE8646f7F89150eC04`, `0x5fA58e4E89c85B8d678Ade970bD6afD4311aF17E`, `0xCF5E5e28848cFe779f7Fb711C57857Cb3b144A19`, `0x227A436e93AAEf856ed406713F2bc3D110A7b797`, `0xd8a6e3fca403d79b6ad6216b60527f51cc967d39`) hold different code and different tokens on each chain. Read `token()` per `(chain, address)`.

---

## 9. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| All HTLCs | **Immutable**, no proxy, no owner | Full bytecode (6.4–9.0 kB); no admin function in the verified sources; v3 `initialise` works once (`isInitialized`) | None. New assets get new HTLCs. |

There is no pause and no admin event. Operational control (quotes, solvers, the app) is off chain.

---

## 10. Detection invariants & gotchas

1. **Join by `secretHash`, not by `orderID`.** `orderID` includes the chain id and the HTLC address, so it differs between the two legs. `secretHash` is equal on both legs; `Redeemed.secret` (`sha256(secret)` = `secretHash`) proves the claim. Sample: Ethereum WBTC lock `0xdc831dfb4218511ee3ee861a3ade79ffb81cd4d7449ab747b0de23088c877524` and claim `0xade66680bb0f75de7888d9f1c74d7e6618a72487ca121c94182adf0e1cca7722` share `orderID` `0xa9438abeab0e0733c9744cd09dbc0e4cfdc8a081d3b9be2154fd438cbb9e1b8b` and `secretHash` `0x47f88876168ef04e01764faa3b998107df94ecb4dd12392a50c2fc56b70e8644`.
2. **Who is who is not in the events.** Initiator and redeemer are only in storage (`orders(orderID)`) and in the calldata. Take the funder from the lock's `Transfer.from` and the payee from the claim's `Transfer.to`. Both sample transactions went through Multicall3 (`0xcA11bde05977b3631167028862be2A173976CA11`), so `tx.to` is not the HTLC.
3. **Direction decides the meaning of `Redeemed`.** EVM → BTC: the EVM redeemer is the solver. BTC → EVM: the EVM initiator is the solver and the EVM redeemer is the user. Classify by whether the initiator is a known solver.
4. **Decode `amount` per family.** v3 puts `amount` in topic3; the older families put it in `data`. The topic0 is the same.
5. **`InitiatedWithDestinationData` duplicates `Initiated`.** Count locks on `Initiated` only.
6. **`Refunded` collides.** LI.FI's escrow `0x00fc00edbe7c003b006f870068c548940000223e` emits the same topic0 on five of the eight chains. Filter on HTLC addresses.
7. **Delisted HTLCs still matter.** Orders in an old HTLC can still be redeemed or refunded. Keep every address of §3–§7a.
8. **Large-transfer and drain triggers.** `Initiated.amount` per token (topic3 in v3) and the token balance of each HTLC. A burst of solver-side `Initiated` locks followed by `Redeemed` to unknown redeemers is the pattern of the July 2026 incident (solver funds released for unfunded swaps).
9. **Quiet does not mean dead.** The window had 0 Garden events on all eight chains, but locks and claims occurred on 2026-09-19 and 2026-09-20 (still the latest on 2026-10-05).

---

## 11. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== HTLC topics =====
TOPIC_INITIATED                     = '\x01b41cbd4bbcc3c5b968a04d3fbdd8c1648a39ff6d9a3929b4840cea1142bc65'
TOPIC_INITIATED_WITH_DEST_DATA      = '\x380328b26f928a9e51ec19f8e2199a2bce34db266d093d1e0104bce139ed7555'
TOPIC_REDEEMED                      = '\x4c9a044220477b4e94dbb0d07ff6ff4ac30d443bef59098c4541b006954778e2'
TOPIC_REFUNDED                      = '\xfe509803c09416b28ff3d8f690c8b0c61462a892c46d5430c8fb20abe472daf0'
TOPIC_EIP712_DOMAIN_CHANGED         = '\x0a6387c9ea3628b88a633bb4f3b151770f70085117a15f9bf3787cda53f13d31'
TOPIC_ERC20_TRANSFER                = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors =====
SEL_INITIATE                        = '\x97ffc7ae'
SEL_INITIATE_WITH_DEST_DATA         = '\x4ede0ab7'
SEL_INITIATE_ON_BEHALF              = '\x13d4a787'
SEL_INITIATE_ON_BEHALF_DEST_DATA    = '\xa66a8641'
SEL_INITIATE_WITH_SIGNATURE         = '\xd4705e9e'
SEL_REDEEM                          = '\xf7ff7207'
SEL_REFUND                          = '\x7249fbb6'
SEL_INSTANT_REFUND                  = '\xedaf5fac'
SEL_ORDERS                          = '\x9c3f1e90'
SEL_TOKEN                           = '\xfc0c546a'

-- ===== Ethereum (1) =====
ETH_GARDEN_HTLC_WBTC                = '\xd781a2abb3fcb9fc0d1dd85697c237d06b75fe95'
ETH_GARDEN_HTLC_CBBTC               = '\xe35d025d0f0d9492db4700fe8646f7f89150ec04'
ETH_GARDEN_HTLC_USDC                = '\x5fa58e4e89c85b8d678ade970bd6afd4311af17e'
ETH_GARDEN_HTLC_USDT                = '\xcf5e5e28848cfe779f7fb711c57857cb3b144a19'
ETH_GARDEN_HTLC_IBTC_OLD            = '\xdc74a45e86dedf1ff7c6dac77e0c2f082f9e4f72'
ETH_GARDEN_HTLC_USDC_OLD            = '\xd8a6e3fca403d79b6ad6216b60527f51cc967d39'
-- ===== Base (8453) =====
BASE_GARDEN_HTLC_CBBTC              = '\xe35d025d0f0d9492db4700fe8646f7f89150ec04'
BASE_GARDEN_HTLC_CBLTC              = '\x7ae2d05e6fd9f12a9d4ba5c61384f4d0b90843eb'
BASE_GARDEN_HTLC_USDC               = '\x227a436e93aaef856ed406713f2bc3d110a7b797'
BASE_GARDEN_HTLC_USDC_DELISTED      = '\x5fa58e4e89c85b8d678ade970bd6afd4311af17e'
BASE_GARDEN_HTLC_USDT_DELISTED      = '\xcf5e5e28848cfe779f7fb711c57857cb3b144a19'
BASE_GARDEN_HTLC_USDC_OLD           = '\xd8a6e3fca403d79b6ad6216b60527f51cc967d39'
-- ===== Arbitrum One (42161) =====
ARB_GARDEN_HTLC_WBTC                = '\xb5ae9785349186069c48794a763db39ec756b1cf'
ARB_GARDEN_HTLC_USDC_DELISTED       = '\x227a436e93aaef856ed406713f2bc3d110a7b797'
ARB_GARDEN_HTLC_IBTC_OLD            = '\xdc74a45e86dedf1ff7c6dac77e0c2f082f9e4f72'
-- ===== BNB Smart Chain (56) =====
BNB_GARDEN_HTLC_BTCB                = '\xe74784e5a45528fdecb257477dd6bd31c8ef0761'
BNB_GARDEN_HTLC_USDC_DELISTED       = '\x5fa58e4e89c85b8d678ade970bd6afd4311af17e'
BNB_GARDEN_HTLC_USDT_DELISTED       = '\xcf5e5e28848cfe779f7fb711c57857cb3b144a19'
BNB_GARDEN_HTLC_USDC_OLD            = '\xd8a6e3fca403d79b6ad6216b60527f51cc967d39'
-- ===== Robinhood Chain (4663) =====
RH_GARDEN_HTLC_CBBTC                = '\x147bf8d6fa3392d2376ef5f6738f3d2931bddb49'
RH_GARDEN_HTLC_USDG                 = '\xd8bf1d34ae05b6f631de898ae9f8f91e08661b59'
-- ===== Arc (5042) =====
ARC_GARDEN_HTLC_USDC                = '\x5fa58e4e89c85b8d678ade970bd6afd4311af17e'
-- Same Refunded topic, not Garden (exclude): LI.FI InputSettlerEscrowLIFI
ETH_LIFI_INPUT_SETTLER_ESCROW       = '\x00fc00edbe7c003b006f870068c548940000223e'
-- Avalanche (43114), OP Mainnet (10), Polygon (137): no Garden HTLC
```

---

## 12. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` / `[0:4]` from the verified v3 source (`HTLC`, solc 0.8.28, `version = "3"`) and the `/v2/schemas` ABI (`evm:htlc`, `evm:htlc_erc20`). Note: the API's `evm:htlc_erc20` schema carries `NativeHTLC__` error names and payable functions, and `evm:htlc` carries the ERC-20 template; the event signatures are the same in both.
- **Addresses:** the live list from `/v2/chains`; the delisted and older HTLCs from verified explorer sources and from sweeping the same addresses on all eight chains. Each address checked with `eth_getCode` on all eight chains, then `token()` and `version()` by `eth_call` (§3–§7). The older USDC and iBTC HTLCs are verified on Blockscout (solc 0.8.18) and Sourcify (BNB, solc 0.8.28). `0xDC74a45e86DEdf1fF7c6dac77e0c2F082f9E4F72` is also the API's `hyperevm` uBTC HTLC (chain 999, outside the eight).
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, any emitter):** `Initiated`, `InitiatedWithDestinationData` and `Redeemed`: 0 on all eight chains. `Refunded`: Ethereum 6, Base 9, Arbitrum 5, BNB 16, Robinhood 4, Avalanche/OP/Polygon 0 — all from LI.FI `0x00fc00edbe7c003b006f870068c548940000223e`, none from Garden. The latest explorer logs per HTLC give the last-activity dates in §3–§5.
- **Sample receipts:** Ethereum WBTC lock `0xdc831dfb4218511ee3ee861a3ade79ffb81cd4d7449ab747b0de23088c877524` (19,555,036 sat WBTC `0x39be9e5968f5cc7d4344bff1f2bf03d0dfe2af16` → HTLC; `amount` in topic3) and claim `0xade66680bb0f75de7888d9f1c74d7e6618a72487ca121c94182adf0e1cca7722` (same amount HTLC → redeemer `0x372b6def309cd977cfdc0ef20df7576342f50aba`).
- **Unverified:** whether the Garden app is fully back online after the July 2026 incident (the latest events seen are dated 2026-09-19 and 2026-09-20); the full history of delisted HTLCs (only addresses reachable from the API, the explorer sources and the shared deterministic addresses were checked).

Authoritative sources:
- Garden API — [v2/chains](https://api.garden.finance/v2/chains) · [v2/schemas](https://api.garden.finance/v2/schemas)
- Repositories — [gardenfi/garden-sol](https://github.com/gardenfi/garden-sol) (`contracts/htlc/HTLC.sol`) · [gardenfi/docs](https://github.com/gardenfi/docs) (`contracts/evm.mdx`, `contracts/overview.mdx`, `changelog.mdx`)
- Explorers — [Etherscan HTLC WBTC](https://etherscan.io/address/0xd781a2abb3fcb9fc0d1dd85697c237d06b75fe95) · [Blockscout Ethereum](https://eth.blockscout.com/address/0xD781a2abB3FCB9fC0D1Dd85697c237d06b75fe95) · [Blockscout Base](https://base.blockscout.com/address/0x227A436e93AAEf856ed406713F2bc3D110A7b797) · [Blockscout Arbitrum](https://arbitrum.blockscout.com/address/0xb5AE9785349186069C48794a763DB39EC756B1cF) · [Sourcify BNB HTLC](https://sourcify.dev) · [Blockscout LI.FI escrow](https://eth.blockscout.com/address/0x00fc00edbe7c003b006f870068c548940000223e)
- Incident reports — [crypto.news](https://crypto.news/garden-finance-takes-app-offline-after-independent-solver-database-compromise/) · [GN Crypto](https://www.gncrypto.news/news/garden-finance-halts-app-450k-htlc-exploit/)
