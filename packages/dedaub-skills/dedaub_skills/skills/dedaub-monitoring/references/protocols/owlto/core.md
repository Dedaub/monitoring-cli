# Owlto Finance — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Optimism + Polygon + BNB; Robinhood relay route only; NOT Avalanche)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the Sourcify-verified `Depositor` source (Ethereum `0x0e83DEd9f80e1C92549615D96842F5cB64A08762`, solc 0.8.18), Owlto's official docs page "Smart Contracts & Maker", Owlto's public bridge API (`get_all_pair_infos`, `get_build_tx`, `get_receipt`) and Owlto's open-source repositories (`owlto-finance/owlto`, `owlto-finance/owlto-frontend`, `owlto-finance/owlto-sdk`).
**Scope:** the Owlto maker bridge: the `Depositor` ("Bridge-Core") contracts, the maker EOA that receives deposits and pays out, the destination code scheme, and two newer routing contract families that the Owlto API now returns (a route into the Relay depository that emits `Bridged`, and an Across-style deposit route). Topics and selectors are chain-agnostic. Addresses are network-specific.

Owlto is a **maker bridge**. A user's funds go to an Owlto maker EOA on the source chain. Owlto's backend then pays the recipient from the same maker EOA on the destination chain with a plain transfer. There is **no on-chain link key on the payout side**: the payout is a native transfer (no log) or an ERC-20 `Transfer` from the maker. The source transaction hash is the key of Owlto's off-chain receipt API.

The destination chain is encoded by an **Owlto network code**. With the `Depositor` contract the code is the `destination` field of the `Deposit` event. With a direct transfer to the maker (the original scheme) the code is the **last four decimal digits of the transferred amount** in the token's base units.

---

## 0. Contract families & flow

| Family | Contracts | Source leg | Value movement | Status |
|--------|-----------|-----------|----------------|--------|
| **Depositor** ("Bridge-Core", official) | §4 table | `deposit(target, token, maker, amount, destination, channel)` emits `Deposit` | Native: `msg.value` forwarded to the maker in the same call. ERC-20: `transferFrom(user → maker)`. The Depositor never holds funds. | Verified source, immutable |
| **Maker EOA** (official) | `0x74F665BE90ffcd9ce9dcA68cB5875570B711CEca` | Direct native or ERC-20 transfer to the maker, with the amount code | Plain transfer | EOA |
| **Relay route** (`Bridged`) | §5 table | Selector `0x2a0b3013` (signature not published) | Native or ERC-20 is deposited into the Relay depository `0x4cd00e387622c35bddb9b4c962c136462338bc31` in the same transaction (`RelayNativeDeposit` / `depositErc20`), then `Bridged` is emitted | Unverified source, EIP-1967 proxies |
| **Across-style route** | §5 table | `deposit((address,address,address,address,uint256,uint256,bytes32,uint32,uint32,uint32,bytes),uint256,uint256,bool)` emits `DepositExecuted` | ERC-20 pulled from the user | Unverified source, EIP-1967 proxies |

Payout (all families): the maker EOA `0x74F665BE90ffcd9ce9dcA68cB5875570B711CEca` sends a plain native transfer (no log) or an ERC-20 `Transfer` to the recipient. For the Relay route the payout is made by Relay's solvers, not by the Owlto maker (see the Relay doc). There is no refund event: a failed order is refunded by Owlto off chain (unverified).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x5a62eae4bbcf3c383f506c8fbc0ffb6b54738018ddd42a887d202d95e5f01247` | `Deposit(address indexed user, address indexed token, address indexed maker, string target, uint256 amount, uint256 destination, uint256 channel, uint256 timestamp)` | Depositor. `token` = `0x0000000000000000000000000000000000000000` for native. `target` = recipient as a string (non-EVM support). `destination` = Owlto network code (§3). `channel` = referral / integrator id. |
| `0x3ee623a6483e0585c3e235f2f285eb28d08425fb61b67bae7e67e3b976567f7d` | `Bridged(address indexed user, address indexed token, uint256 amount, uint256 fee, bytes32 ref)` | Relay route. The topic0 matches this type list. The parameter names are not published (unverified). |
| `0x1054a5627e951e7fdeda387664ecb4a17707ac049d8d4ea800c87255b9b2e811` | `DepositExecuted(address,uint256,uint256,bool)` | Across-style route. Type list from a public signature database, hash-matched. Parameter names not published (unverified). |
| `0x8032066556caf3967d8fec4ad22a2d9e1e9576556b2903a0fcd5b1fd201e3477` | `RelayNativeDeposit(address,uint256,bytes32)` | Not Owlto: the Relay depository `0x4cd00e387622c35bddb9b4c962c136462338bc31`, in the same transaction as `Bridged` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20: the only log of a direct maker deposit or an ERC-20 payout |

The `Depositor` has no admin events (no owner, no proxy).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xfc180638` | `deposit(string target, address token, address maker, uint256 amount, uint256 destination, uint256 channel)` | Depositor. Payable. Emits `Deposit`. The `maker` is caller-supplied, so read it from the event. |
| `0xc09bcfbb` | `isOwltoDepositor()` | Depositor. Pure, returns `true`. A cheap on-chain tell for a Depositor deployment. |
| `0x5e3bd9e9` | `deposit((address,address,address,address,uint256,uint256,bytes32,uint32,uint32,uint32,bytes),uint256,uint256,bool)` | Across-style route. Tuple shape from a public signature database; in an API-built transaction the tuple carried depositor, recipient, input token, output token, output amount, destination chain ID, a bytes32, quote time, fill deadline, exclusivity, message, and the outer words carried input amount and fee. |
| `0xa9059cbb` | `transfer(address to, uint256 value)` | ERC-20 direct deposit to the maker, and maker ERC-20 payouts. |

The Relay-route entrypoint has selector `0x2a0b3013`. Its signature is not published and is not in public signature databases. In an API-built transaction its arguments were: token, amount, fee, the Relay depository address, a deadline, inner calldata for the depository (`depositNative(address,bytes32)` `0x49290c1c` or `depositErc20(address,address,uint256,bytes32)` `0xe8017952`), and a 65-byte signature.

---

## 3. Owlto network codes (destination encoding)

Mapped on 2026-09-29 by sending sample source transaction hashes to Owlto's official `get_receipt` API (which names the destination chain) and reading the `destination` field of the same `Deposit` logs:

| Owlto code | Chain | 4-digit amount suffix |
|-----------|-------|----------------------|
| 1 | Ethereum (1) | `0001` |
| 3 | Optimism (10) | `0003` |
| 4 | Arbitrum One (42161) | `0004` |
| 12 | Base (8453) | `0012` |
| 15 | BNB Smart Chain (56) | `0015` |
| 21 | Polygon PoS (137) | `0021` |
| — | Avalanche C-Chain (43114) | not supported (no code seen; not in the supported-network list) |
| — | Robinhood Chain (4663) | not supported by the Owlto API (no code seen) |
| 2, 6, 7, 9, 11, 13, 18, 22, 30, 41, 47, 49, 84, 88, 91, 92, 100, 102 | zkSync Era, Scroll, Linea, Taiko, Mantle, Zora, Manta, X Layer, Mode, Solana, Bob, Mint, Unichain, Ink, Soneium, Abstract, Katana, Monad | off-target |

**Amount code (direct transfers to the maker).** Owlto's open-source backend decodes a direct transfer with `getChainIdByValue`: `parseInt(value.toString().slice(-4))` is the network code. The open-source frontend builds the value as `amountInWei.slice(0, -(codeLength + 1)) + dtcCode + networkCode`, with the network code zero-padded to 4 digits and one more digit for the fee level. Example: a direct ETH transfer to Base ends in the digits `0012` (wei).

**Measured caveat.** The two `Deposit` samples (§9) had round amounts (`400000000000000` wei) and carried the code only in `destination`. In 1,000 USDC transfers to the maker on Base (blocks 40,000,001–40,406,272) no code pattern was visible in the last four digits. Treat the amount code as the legacy direct-transfer path, and prefer `Deposit.destination` when a `Deposit` event exists.

---

## 4. Addresses — Depositor and maker

All existence-checked with `eth_getCode` on 2026-09-29.

| Chain | ID | Depositor (official list / API) | Code | Notes |
|-------|----|-------------------------------|------|-------|
| Ethereum | 1 | `0x0e83DEd9f80e1C92549615D96842F5cB64A08762` | 1446 B | In the API pair list for Ethereum. Sourcify-verified `Depositor`. |
| Base | 8453 | `0xB5CeDAF172425BdeA4c186f6fCF30b367273DA19` | 1847 B | Official list and API. |
| Arbitrum One | 42161 | `0x0e83DEd9f80e1C92549615D96842F5cB64A08762` | 1446 B | Official list and API. |
| Optimism | 10 | `0x0e83DEd9f80e1C92549615D96842F5cB64A08762` | 1446 B | Official list (not in the current API pair list). |
| Polygon PoS | 137 | `0xC626845BF4E6a5802Ef774dA0B3DfC6707F015F7` | 1446 B | Official list. |
| BNB Smart Chain | 56 | `0xC626845BF4E6a5802Ef774dA0B3DfC6707F015F7` | 1446 B | Official list and API. |
| Avalanche C-Chain | 43114 | — | — | Not in the official list. `0x0e83DEd9f80e1C92549615D96842F5cB64A08762`, `0xC626845BF4E6a5802Ef774dA0B3DfC6707F015F7` and `0xB5CeDAF172425BdeA4c186f6fCF30b367273DA19` return `0x`. A third-party indexer lists `0x3F0F0E6411F859Da1A1BbF8bD6217cA93820Bb98` (2862 B on Avalanche) as an Owlto Depositor: unverified. |
| Robinhood Chain | 4663 | — | — | No Depositor: all Depositor addresses return `0x`. |

Other deployments of the same 1446-byte Depositor code: `0xC626845BF4E6a5802Ef774dA0B3DfC6707F015F7` also exists on Ethereum, Base, Arbitrum and Optimism (not the listed Depositor there, but a third-party indexer tracks it on Base). **Decoy:** `0x0e83DEd9f80e1C92549615D96842F5cB64A08762` on Polygon and BNB holds a different 2373-byte contract.

Makers:

| Role | Address | Chains (nonce on 2026-09-29) | Source |
|------|---------|-------------------------------|--------|
| **Owlto maker (EVM)** | `0x74F665BE90ffcd9ce9dcA68cB5875570B711CEca` | EOA. Ethereum 1808, Base 31149, Arbitrum 17415, Optimism 1546, Polygon 237, BNB 2472. Avalanche and Robinhood: nonce 0. | Official docs. Receiver in every sampled `Deposit` and sender of every sampled payout (§9). |
| Maker (third-party list) | `0x1f49a3fa2b5B5b61df8dE486aBb6F3b9df066d86` | EOA. Ethereum 42864, Base 222659, Arbitrum 254161, Optimism 45508, Polygon 4596, BNB 34707, Avalanche 717. Robinhood 0. | Used as the Owlto maker by a third-party bridge indexer. Not in Owlto's docs. Unverified. |
| Explorer label "Owlto Finance: Bridge" | `0x45a318273749d6eb00f5f6ca3bc7cd3de26d642a` | EOA. Ethereum 31439, Base 69581, Arbitrum 75147, Optimism 34159, Polygon 2667, BNB 6221. Avalanche and Robinhood 0. | Etherscan label only. Unverified. |

---

## 5. Addresses — routing contracts returned by the Owlto API

These contracts are the `to` of transactions built by Owlto's `get_build_tx` API, or emit the same event as those. Their source is not verified.

### 5.1 Relay route (`Bridged`)

| Chain | Contract (EIP-1967 proxy, 163 B) | Implementation | How identified |
|-------|----------------------------------|----------------|----------------|
| Ethereum | `0x2d5E0Cd9bfeA95e89CeF80fb39c050991Ac19EaF` | `0x1b7a410ecc527a4ab97693efd7850fcf088db989` | API (`ETH`, Ethereum → Base) |
| Base | `0x648bfd8bE5a30d80072dB624ad61bCB3F820d63A` | `0x5daa93b053ff8dca7f1c3965fc8e5c4fa31020ce` | API (`ETH`, Base → Arbitrum) |
| Arbitrum One | `0x949bE0e6Df9cC210BA0e4dbD90639da05437F5Ff` | `0x32180efb2afa93593febcb715e70d3f281243d0c` | API (`ETH`, Arbitrum → Base) |
| BNB Smart Chain | `0x1b7A410EcC527a4aB97693eFD7850FcF088Db989` | `0x079abf6c173dd31b4938a6d8e440ab4d76b42430` | API (`USDT`, BNB → Ethereum) |
| Robinhood Chain | `0x1b7A410EcC527a4aB97693eFD7850FcF088Db989` | `0x079abf6c173dd31b4938a6d8e440ab4d76b42430` | emits `Bridged` (5 logs in the window), same proxy and implementation code as BNB |
| Optimism | `0x1b7A410EcC527a4aB97693eFD7850FcF088Db989` | `0x079abf6c173dd31b4938a6d8e440ab4d76b42430` | same proxy and implementation code; not in the API; 0 `Bridged` in the window |
| Polygon PoS | `0x1b7A410EcC527a4aB97693eFD7850FcF088Db989` | `0x079abf6c173dd31b4938a6d8e440ab4d76b42430` | same proxy and implementation code; not in the API; 0 `Bridged` in the window |
| Avalanche C-Chain | — | — | none |

The Relay depository `0x4cd00e387622c35bddb9b4c962c136462338bc31` has code on all eight chains (8628 B).

### 5.2 Across-style route (`DepositExecuted`)

| Chain | Contract (EIP-1967 proxy, 126 B) | Implementation | How identified |
|-------|----------------------------------|----------------|----------------|
| Ethereum | `0x3C0158627F81e9a83D5E306D0078525306370f29` | `0x8bbb767dd622eba249527b1a993a11bee10c02fa` | API (`USDC`, Ethereum → Base) |
| BNB Smart Chain | `0x3C0158627F81e9a83D5E306D0078525306370f29` | `0x8bbb767dd622eba249527b1a993a11bee10c02fa` | API (`ETH` token, BNB → Base) |
| Base | `0x2338DcE713726e75141e2Bd0DBaDFDdEfC8A9d68` | `0xef54f0b486d804be9adfb5ef4da594206e948c7b` | API (`USDC`, Base → Arbitrum) |
| Arbitrum One | `0x8d7285C97D0d0C451be72F737875A98751870B97` | `0x2d5e0cd9bfea95e89cef80fb39c050991ac19eaf` | API (`USDC`, Arbitrum → Base) |
| Optimism, Polygon PoS | `0x8d7285C97D0d0C451be72F737875A98751870B97` | `0x2d5e0cd9bfea95e89cef80fb39c050991ac19eaf` | same proxy pattern; not in the API |

**Same-address trap:** `0x2d5E0Cd9bfeA95e89CeF80fb39c050991Ac19EaF` is the Relay-route proxy on Ethereum, but on Arbitrum, Optimism, Polygon and BNB it is the 6916-byte **implementation** of the Across-style proxy. On Robinhood Chain it is an unrelated 825-byte contract.

---

## 6. Cross-chain summary

| Chain | ID | Depositor | Owlto maker active | Relay route | Across-style route | Code |
|-------|----|-----------|--------------------------|-------------|--------------------|------|
| Ethereum | 1 | `0x0e83DEd9f80e1C92549615D96842F5cB64A08762` | yes | `0x2d5E0Cd9bfeA95e89CeF80fb39c050991Ac19EaF` | `0x3C0158627F81e9a83D5E306D0078525306370f29` | 1 |
| Base | 8453 | `0xB5CeDAF172425BdeA4c186f6fCF30b367273DA19` | yes | `0x648bfd8bE5a30d80072dB624ad61bCB3F820d63A` | `0x2338DcE713726e75141e2Bd0DBaDFDdEfC8A9d68` | 12 |
| Arbitrum One | 42161 | `0x0e83DEd9f80e1C92549615D96842F5cB64A08762` | yes | `0x949bE0e6Df9cC210BA0e4dbD90639da05437F5Ff` | `0x8d7285C97D0d0C451be72F737875A98751870B97` | 4 |
| Optimism | 10 | `0x0e83DEd9f80e1C92549615D96842F5cB64A08762` | yes | `0x1b7A410EcC527a4aB97693eFD7850FcF088Db989` | `0x8d7285C97D0d0C451be72F737875A98751870B97` | 3 |
| Polygon PoS | 137 | `0xC626845BF4E6a5802Ef774dA0B3DfC6707F015F7` | yes | `0x1b7A410EcC527a4aB97693eFD7850FcF088Db989` | `0x8d7285C97D0d0C451be72F737875A98751870B97` | 21 |
| BNB Smart Chain | 56 | `0xC626845BF4E6a5802Ef774dA0B3DfC6707F015F7` | yes | `0x1b7A410EcC527a4aB97693eFD7850FcF088Db989` | `0x3C0158627F81e9a83D5E306D0078525306370f29` | 15 |
| Avalanche C-Chain | 43114 | — | no (nonce 0) | — | — | — |
| Robinhood Chain | 4663 | — | no (nonce 0) | `0x1b7A410EcC527a4aB97693eFD7850FcF088Db989` | — | — |

(Owlto maker = `0x74F665BE90ffcd9ce9dcA68cB5875570B711CEca`.)

Off-target Depositors in the official list: XLayer, Bob, Mint, Taiko (`0xC626845BF4E6a5802Ef774dA0B3DfC6707F015F7`), Linea `0xF40448F38d99A2Db70de37416B22B4338A1c2Ad7`, Scroll `0x575Dbe0023d2602515a73d4f0B5Ee857E8EbA805`, zkSync Era `0x95cDd9632C924d2cb5586168Cf0Ba7640dF30598`, Morph `0x3F0F0E6411F859Da1A1BbF8bD6217cA93820Bb98`, Unichain `0xE0F6307e051E6994034792e3aD7550DcA667AEcd`, Ink `0x7CFE8Aa0d8E92CCbBDfB12b95AEB7a54ec40f0F5`, Soneium `0x0896cc10F7fa09127eE6060AD56D34D2d80306a4`. The API lists Linea at `0xA562e2510ECDACAa1DB482fd287454AD2B979fa6`. The Solana maker is `HNQqsDvuohwZnCRxmsyusxjN8DLDii2zsfxLffmqoTKW`.

---

## 7. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| Depositor (all chains) | **Immutable**, no owner | Full runtime code (1446 B or 1847 B), no EIP-1967 implementation. Source has no admin function. | none |
| Relay-route contracts | EIP-1967 proxy (163 B) | implementation slot populated (§5.1) | unverified (source not published) |
| Across-style route contracts | EIP-1967 proxy (126 B) | implementation slot populated (§5.2) | unverified |
| Maker EOAs | n/a | `eth_getCode` = `0x` | private key holder |

---

## 8. Detection invariants & gotchas

1. **No payout event and no on-chain link key.** The payout is a plain transfer from the maker EOA on the destination chain: a native transfer has no log at all. Link a deposit to its payout only through Owlto's `get_receipt` API (source hash → destination hash), or heuristically by recipient, amount and time.
2. **The destination code is in `Deposit.destination`** (data word 3), not in `topic`s. The recipient is `Deposit.target`, a string, not an address topic.
3. **The Depositor never holds funds.** A native deposit is `msg.value` forwarded to the maker in the same transaction (no log). An ERC-20 deposit is one `Transfer(user → maker)`. Watch the maker, not the Depositor balance.
4. **Direct maker deposits have no Owlto event.** Capture an ERC-20 `Transfer` with `to` = maker (or a native transfer to the maker) and decode the last four digits of the amount as the code (§3). Many transfers to the maker are dust or address-poisoning spam: drop amounts below the route minimum.
5. **The Relay route double-counts with Relay.** A `Bridged` transaction also deposits into the Relay depository `0x4cd00e387622c35bddb9b4c962c136462338bc31` (`RelayNativeDeposit` in the same transaction), so a Relay monitor sees the same value. Count it once.
6. **Same-address traps.** `0x2d5E0Cd9bfeA95e89CeF80fb39c050991Ac19EaF` is three different things on different chains (§5.2). `0x0e83DEd9f80e1C92549615D96842F5cB64A08762` is a Depositor on Ethereum, Arbitrum and Optimism, but a different contract on Polygon and BNB. Always key on `(chainId, address)`.
7. **Robinhood Chain:** only the Relay-route contract is present. There is no Depositor and the maker has nonce 0.
8. **Large-transfer trigger:** `Deposit.amount` with `token`, `Bridged.amount`, and ERC-20 `Transfer` to or from the maker. There are no admin events: the Depositor is immutable, and the routing proxies are unverified.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_OWLTO_DEPOSIT              = '\x5a62eae4bbcf3c383f506c8fbc0ffb6b54738018ddd42a887d202d95e5f01247'
TOPIC_OWLTO_BRIDGED              = '\x3ee623a6483e0585c3e235f2f285eb28d08425fb61b67bae7e67e3b976567f7d'
TOPIC_OWLTO_DEPOSIT_EXECUTED     = '\x1054a5627e951e7fdeda387664ecb4a17707ac049d8d4ea800c87255b9b2e811'
TOPIC_RELAY_NATIVE_DEPOSIT       = '\x8032066556caf3967d8fec4ad22a2d9e1e9576556b2903a0fcd5b1fd201e3477'
TOPIC_ERC20_TRANSFER             = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

-- ===== Selectors =====
SEL_DEPOSITOR_DEPOSIT            = '\xfc180638'
SEL_IS_OWLTO_DEPOSITOR           = '\xc09bcfbb'
SEL_ACROSS_STYLE_DEPOSIT         = '\x5e3bd9e9'
SEL_RELAY_ROUTE_ENTRY            = '\x2a0b3013'

-- ===== Depositor =====
ETH_DEPOSITOR                    = '\x0e83ded9f80e1c92549615d96842f5cb64a08762'
BASE_DEPOSITOR                   = '\xb5cedaf172425bdea4c186f6fcf30b367273da19'
ARB_DEPOSITOR                    = '\x0e83ded9f80e1c92549615d96842f5cb64a08762'
OP_DEPOSITOR                     = '\x0e83ded9f80e1c92549615d96842f5cb64a08762'
POLY_DEPOSITOR                   = '\xc626845bf4e6a5802ef774da0b3dfc6707f015f7'
BNB_DEPOSITOR                    = '\xc626845bf4e6a5802ef774da0b3dfc6707f015f7'
BASE_DEPOSITOR_ALT               = '\xc626845bf4e6a5802ef774da0b3dfc6707f015f7'

-- ===== Makers (EOAs; same address on every chain where active) =====
ETH_OWLTO_MAKER_EOA              = '\x74f665be90ffcd9ce9dca68cb5875570b711ceca'
BASE_OWLTO_MAKER_EOA             = '\x74f665be90ffcd9ce9dca68cb5875570b711ceca'
ETH_OWLTO_MAKER_THIRDPARTY_EOA   = '\x1f49a3fa2b5b5b61df8de486abb6f3b9df066d86'
ETH_OWLTO_LABELLED_EOA           = '\x45a318273749d6eb00f5f6ca3bc7cd3de26d642a'

-- ===== Relay route (Bridged) =====
ETH_RELAY_ROUTE                  = '\x2d5e0cd9bfea95e89cef80fb39c050991ac19eaf'
BASE_RELAY_ROUTE                 = '\x648bfd8be5a30d80072db624ad61bcb3f820d63a'
ARB_RELAY_ROUTE                  = '\x949be0e6df9cc210ba0e4dbd90639da05437f5ff'
OP_RELAY_ROUTE                   = '\x1b7a410ecc527a4ab97693efd7850fcf088db989'
POLY_RELAY_ROUTE                 = '\x1b7a410ecc527a4ab97693efd7850fcf088db989'
BNB_RELAY_ROUTE                  = '\x1b7a410ecc527a4ab97693efd7850fcf088db989'
RH_RELAY_ROUTE                   = '\x1b7a410ecc527a4ab97693efd7850fcf088db989'
ETH_RELAY_DEPOSITORY             = '\x4cd00e387622c35bddb9b4c962c136462338bc31'

-- ===== Across-style route (DepositExecuted) =====
ETH_ACROSS_STYLE_ROUTE           = '\x3c0158627f81e9a83d5e306d0078525306370f29'
BNB_ACROSS_STYLE_ROUTE           = '\x3c0158627f81e9a83d5e306d0078525306370f29'
BASE_ACROSS_STYLE_ROUTE          = '\x2338dce713726e75141e2bd0dbadfddefc8a9d68'
ARB_ACROSS_STYLE_ROUTE           = '\x8d7285c97d0d0c451be72f737875a98751870b97'
OP_ACROSS_STYLE_ROUTE            = '\x8d7285c97d0d0c451be72f737875a98751870b97'
POLY_ACROSS_STYLE_ROUTE          = '\x8d7285c97d0d0c451be72f737875a98751870b97'
-- Avalanche (43114): no Owlto contract; Robinhood (4663): Relay route only
```

---

## 10. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** `Deposit`, `deposit` and `isOwltoDepositor` recomputed as `keccak256(sig)` from the Sourcify-verified `Depositor.sol`. `Bridged(address,address,uint256,uint256,bytes32)` recomputed and matched to live logs (two indexed topics in the Robinhood sample). `DepositExecuted(address,uint256,uint256,bool)`, `RelayNativeDeposit(address,uint256,bytes32)` and the `0x5e3bd9e9` tuple were taken from a public signature database and recomputed. `0x2a0b3013` is unresolved.
- **Addresses:** Depositors and the maker from the official docs table, cross-checked with the API pair list (`contract_address` per source chain). Routing contracts from the `to` field of API-built transactions (`get_build_tx`, read-only) and from `Bridged` emitters. All existence-checked with `eth_getCode` on all eight chains; EIP-1967 slots read.
- **Network codes:** 30 source transaction hashes from `Deposit` logs (Ethereum, Base and Arbitrum Depositors; logs from the explorer API) were sent to the official `get_receipt` API. 28 returned a destination chain; 2 (codes 73 and 79) returned status 908 (still processing). Each code maps to one chain, with no conflict. The amount-code rule is from `src.ts/utils/chain-config.ts` (`getChainIdByValue`) of `owlto-finance/owlto` and `src/components/pages/Confirm.vue` of `owlto-finance/owlto-frontend`.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC, logs by topic from every emitter):** `Deposit`: Ethereum 1 (at `0x0e83DEd9f80e1C92549615D96842F5cB64A08762`), Base 1 (at `0xB5CeDAF172425BdeA4c186f6fCF30b367273DA19`), all other chains 0. `Bridged`: Ethereum 5, Base 37, Arbitrum 8, BNB 10, Robinhood 5, Optimism 0, Polygon 0, Avalanche 0. `DepositExecuted` at the Across-style proxies: BNB 2, Ethereum 0, Base 0, Arbitrum 0; Optimism and Polygon not measured. Native payouts from the maker have no log and were not counted.
- **Sample transactions (receipts read):** Ethereum `0x6b54a743723c09cb4b0a16833703c3c92249d00c8c6acce47cee7965b861db80` (`deposit`, 0.0004 ETH to maker `0x74F665BE90ffcd9ce9dcA68cB5875570B711CEca`, `destination` 4); its payout per `get_receipt` is Arbitrum `0xcdf47ccecee10aadc621525842c367a452d2f3fbbcb107bc84358fec5649e80d`, a 0.0001 ETH native transfer from the maker with no log. Base `0xc39afb2800d7666f09a743dcd8549b2c446c1b0173d5d3afbe680221353a1ae1` (`deposit`, `destination` 4). Payouts from the same maker confirmed on Ethereum `0x0960f41d4c5aa85c778e9f15b540069edae13c83d2f5050733f604c80497ddce`, Optimism `0x31d229e65346c16e395bdcee25e26e67b33a4255c6f868b9d374cf91df739310` and Base `0xcdff62708eed47a1449d69b485e5718ccba5679ea6c9b5cbda539b39577c8e67`. Robinhood `0xa5a4d36eb464a44b8309c71348dd10694d187b5cc0f81bb89aaf806336462a8e` (`0x2a0b3013` with 0.0874 ETH: `RelayNativeDeposit` at the Relay depository, then `Bridged`).

Authoritative sources:
- Docs — [Smart Contracts & Maker](https://docs.owlto.finance/basics/smart-contracts-and-maker.md) · [Supported Networks & Tokens](https://docs.owlto.finance/basics/supported-networks-and-tokens.md) · [API overview](https://docs.owlto.finance/integration-guides/api/overview.md) · [API Q&A](https://docs.owlto.finance/integration-guides/api/q-and-a.md)
- API — `https://owlto.finance/api/bridge_api/v1/` (`get_all_pair_infos`, `get_build_tx`, `get_receipt`; schema at `https://owlto.finance/bridge_api/v1/swagger/doc.json`)
- Repositories — [owlto-finance/owlto](https://github.com/owlto-finance/owlto) · [owlto-finance/owlto-frontend](https://github.com/owlto-finance/owlto-frontend) · [owlto-finance/owlto-sdk](https://github.com/owlto-finance/owlto-sdk)
- Verified source — Sourcify `Depositor` (chain 1, `0x0e83DEd9f80e1C92549615D96842F5cB64A08762`)
- Third-party cross-check — [DefiLlama bridges-server Owlto adapter](https://github.com/DefiLlama/bridges-server/blob/master/src/adapters/owlto/index.ts)
- Explorers — [Etherscan maker](https://etherscan.io/address/0x74F665BE90ffcd9ce9dcA68cB5875570B711CEca) · [Basescan Depositor](https://basescan.org/address/0xB5CeDAF172425BdeA4c186f6fCF30b367273DA19)
