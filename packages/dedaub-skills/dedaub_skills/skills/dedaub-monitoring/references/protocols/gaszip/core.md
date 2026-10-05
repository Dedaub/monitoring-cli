# Gas.zip — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche, Arc; Robinhood Chain = payouts only)

**Status:** verified on 2026-09-29 against live RPC on all eight target chains, the verified `GasZipV2` source (Ethereum, compiler 0.8.26), the canonical `gasdotzip/gas-contracts` (`src/GasZip.sol`, v1) and `gasdotzip/gas-lz-contracts` (`src/v2/GasLZV2.sol`) repos, the `gasdotzip/documentation` repo (`data/gas/inboundChains.ts`, `data/layerzero/lzConfigData.json`, the deposit code examples) and the public Gas.zip API (`https://backend.gas.zip/v2`: `chains`, `quotes`, `deposit`, `search`). Topic0s and selectors are recomputed as `keccak256(sig)`. Addresses are existence-checked with `eth_getCode`. `owner()` is read live. Extended on 2026-10-05 with Arc (5042).
**Scope:** the Gas.zip gas-refuel bridge: the **Direct Deposit** address (an EOA), the **GasZipV2** contract-deposit forwarder, the legacy **GasZip v1** contract, the **GasLZV2** LayerZero v2 refuel contract, and the **payout signers** (EOAs). Chains: Ethereum (1), Base (8453), Arbitrum One (42161), Optimism (10), Polygon PoS (137), BNB Smart Chain (56), Avalanche C-Chain (43114), Robinhood Chain (4663; destination only), Arc (5042; contract deposits and payouts, no Direct Deposit). Topics and selectors are chain-agnostic. Addresses are network-specific.

Gas.zip moves **native gas only**. The user sends native coin on one chain, and Gas.zip sends native coin on one or more destination chains, split equally. The docs say to send between $0.25 and $50 per destination chain. There is no token bridge, no lock-and-mint and no destination contract.

The source leg has three forms. (1) **Direct Deposit** (the recommended method): a native transfer to the EOA `0x391E7C679d29bD940d63be94AD22A25d25b5A604`, with calldata that names the recipient and the destination chains. It emits **no log**. (2) **Contract Deposit:** a call to `deposit` on `GasZipV2` (`0x2a37D63EAdFe4b4682a3c28C1c2cD4F109Cc2762`), which keeps the native value and emits `Deposit(from, chains, amount, to)`. Aggregators (LI.FI, Rango) use this form. (3) **LayerZero refuel:** a call to `sendDeposits` on `GasLZV2` (`0x26DA582889f59EaaE9dA1f063bE0140CD93E6a4f`), which pays LayerZero to deliver a native drop and emits `SentDeposits`.

The destination leg of forms (1) and (2) is a plain native transfer from a Gas.zip payout signer to the recipient. It emits **no log**. The signer is `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` on most chains and `0x5baBE600b9fCD5fB7b66c0611bF4896D967b23A1` on Ethereum. **There is no link key on chain.** The Gas.zip API links them: `GET https://backend.gas.zip/v2/deposit/{deposit hash}` returns the payout transactions, and `GET https://backend.gas.zip/v2/search/{hash}` accepts either side. For form (3), the link is the LayerZero packet (`PacketSent` on the source, the executor's native drop on the destination).

---

## 0. Contract families & versions

| Component | Role | Proxy? | Where |
|-----------|------|--------|-------|
| **Direct Deposit** ("Direct Deposit v2") | Receives native deposits with calldata. Also the `owner()` of GasZipV2 and GasZip v1: it sweeps them with `withdraw`. | n/a (EOA) | Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche (Robinhood Chain: disabled as a source; Arc: no Direct Deposit) |
| **GasZipV2** (the docs call this method the "v1 Contract Deposit") | `deposit(uint256 chains, bytes32 to)` and `deposit(uint256 chains, address to)`. Keeps `msg.value`. Emits `Deposit`. | **No** (immutable, 1,499 B, same code on seven chains) | the seven chains above; on Arc a different 1,202 B deposit contract at `0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390` emits the same `Deposit` (§10a) |
| **GasZip** (v1, legacy) | `deposit(uint256 chains, address to)`. Emits the older `Deposit` with `address to`. | No (943 B) | Ethereum, Arbitrum, Optimism |
| **GasLZV2** | LayerZero v2 OApp. `sendDeposits` asks the LayerZero executor for a native drop on each destination. | No (9,503 B, same code on seven chains) | the seven chains above |
| **Payout signer** | Sends the native payouts. | n/a (EOA) | all eight chains and Arc |
| **Ethereum payout signer** | Sends the native payouts on Ethereum. Receives the swept deposits from the Direct Deposit EOA. | n/a (EOA) | Ethereum |

### Gas.zip short chain ids

The calldata and `Deposit.chains` use Gas.zip's own ids, not chain ids. Values from `GET https://backend.gas.zip/v2/chains` (`short`):

| Chain | Chain id | Gas.zip short id | Hex (2 bytes) | LayerZero v2 eid (GasLZV2) |
|-------|----------|------------------|---------------|----------------------------|
| Ethereum | 1 | 255 | `0x00ff` | 30101 |
| Base | 8453 | 54 | `0x0036` | 30184 |
| Arbitrum One | 42161 | 57 | `0x0039` | 30110 |
| Optimism | 10 | 55 | `0x0037` | 30111 |
| Polygon PoS | 137 | 17 | `0x0011` | 30109 |
| BNB Smart Chain | 56 | 14 | `0x000e` | 30102 |
| Avalanche C-Chain | 43114 | 15 | `0x000f` | 30106 |
| Robinhood Chain | 4663 | 526 | `0x020e` | not configured |
| Arc | 5042 | 525 | `0x020d` | not configured |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 GasZipV2 and GasZip v1 (contract deposit)

No parameter is indexed. Every field is in `data`.

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x7921786f0ead54b0a0502b86991470e5c4790dadc22242f4ff071f361e8e6c68` | `Deposit(address from, uint256 chains, uint256 amount, bytes32 to)` | **Source leg (GasZipV2).** `from` = `msg.sender` (an aggregator when one calls). `chains` = packed short ids. `amount` = `msg.value`. `to` = recipient; an EVM address is **left-aligned** (`bytes32(bytes20(to))`). |
| `0x02d7e648dd130fc184d383e55bb126ac4c9c60e8f94bf05acdf557ba2d540b47` | `Deposit(address from, uint256 chains, uint256 amount, address to)` | Source leg of the legacy GasZip v1. |

### 1.2 GasLZV2 (LayerZero refuel)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xa22a487af6300dc77db439586e8ce7028fd7f1d734efd33b287bc1e2af4cd162` | `SentDeposits(uint256[] params, address to, uint256 value, uint256 fee, address from)` | **Source leg.** Each `params[i]` = `dstEid << 224` plus the drop amount in the low 128 bits. `value` = `msg.value`, `fee` = the LayerZero fee sum. |
| `0x14af90211b59e95afdafa93c2cb547e61a4e6b0e74cfad8c3d7b6c3d48e6c29d` | `SentMessages(uint32[] eids, bytes[] messages, uint256 value, uint256 fee, address from)` | Plain LayerZero messages. No native drop. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed oldOwner, address indexed newOwner)` | Admin (Solady-style `Ownable`). |
| `0xdbf36a107da19e49527a7176a1babf963b4b0ff8cde35ee35d6cd8f1f9ac7e1d` | `OwnershipHandoverRequested(address indexed pendingOwner)` | Admin. |
| `0xfa7b8eab7da67f412cc9575ed43464468f9bfbae89d1675917346ca6d8fe3c92` | `OwnershipHandoverCanceled(address indexed pendingOwner)` | Admin. |
| `0x1ab700d4ced0c005b164c0f789fd09fcbb0156d4c2041b8a3bfbcd961cd1567f` | `PacketSent(bytes encodedPayload, bytes options, address sendLibrary)` | Emitted by the LayerZero EndpointV2 `0x1a44076050125825900e736c501f859c50fE728c` in the same transaction. The packet header carries the GUID. |

The GasZipV2 contract has no admin event. `withdraw` and `newOwner` change state without a log.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 GasZipV2 and GasZip v1

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc9630cb0` | `deposit(uint256 chains, bytes32 to)` | GasZipV2. Payable; reverts on `msg.value == 0`. The API's `contractDepositTxn` uses this form. |
| `0x6e553f65` | `deposit(uint256 chains, address to)` | GasZipV2 and GasZip v1. **Same selector as ERC-4626 `deposit(uint256 assets, address receiver)`.** Filter on `tx.to`. |
| `0x51cff8d9` | `withdraw(address token)` | Owner only. Sends the whole native (`token` = zero address) or token balance to the owner. No event. |
| `0x85952454` | `newOwner(address _owner)` | Owner only. No event. |
| `0x8da5cb5b` | `owner()` | View. Live value `0x391E7C679d29bD940d63be94AD22A25d25b5A604` for GasZipV2 (seven chains) and for GasZip v1 (Ethereum, Arbitrum, Optimism). |

### 2.2 GasLZV2

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x89a281b6` | `sendDeposits(uint256[] _depositParams, address _to)` | Payable. One LayerZero send with a native-drop option per param. Emits `SentDeposits`. |
| `0xd29e9f32` | `sendMessages(uint32[] _dstEids, bytes[] _messages)` | Payable. Emits `SentMessages`. |
| `0x94ca88aa` | `estimateFees(uint32[] _dstEids, bytes[] _messages, bytes[] _options)` | View. |
| `0xfccbe220` | `quote(uint32 _dstEid, bytes _message, bytes _options)` | View. |
| `0xf3fef3a3` | `withdraw(address token, uint256 amount)` | Owner only. |
| `0x3772df58` | `setPeers(uint32[] _remoteEids, bytes32[] _remoteAddresses)` | Owner only. |
| `0x128c9991` | `setGasLimit(uint32[] _remoteEids, uint128[] _gasLimits)` | Owner only. |
| `0x29b85fff` | `setDefaultGasLimit(uint128 _defaultGasLimit)` | Owner only. |
| `0xca5eb5e1` | `setDelegate(address _delegate)` | Owner only. Sets the LayerZero delegate. |
| `0x2b94e499` | `setUlnConfigs(address _lib, uint64 confirmations, uint32[] eids, address dvn)` | Owner only. Sets the DVN config. |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Owner only. |
| `0x25692962` | `requestOwnershipHandover()` | Two-step ownership (Solady). |
| `0xf04e283e` | `completeOwnershipHandover(address pendingOwner)` | Owner only. |

### 2.3 Direct Deposit calldata (no function)

A Direct Deposit is a native transfer to `0x391E7C679d29bD940d63be94AD22A25d25b5A604` with raw calldata, not an ABI call:

| Bytes | Meaning |
|-------|---------|
| byte 0 | Recipient type: `01` = the sender, `02` = next 20 bytes are an EVM address, `03` = next 32 bytes are an SVM or Tron address, `04` = next 32 bytes are a MOVE or Fuel address, `05` = XRP, `06` = Initia. |
| then | The recipient (for types `02`–`06`). |
| then | One 2-byte short id per destination chain, big-endian. |

Examples from the docs and the quote API: `0x010039` = "to the sender, on Arbitrum (57)". `0x0100390037` = "to the sender, on Arbitrum and Optimism". The same short ids fill `Deposit.chains`: the quote API encodes Arbitrum + Optimism as `chains` = `0x00390037` (first destination in the higher bytes). The docs' v1 example packs one-byte ids with the first destination in the lowest byte.

---

## 3. Addresses — Ethereum (chain ID 1)

All verified with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| Direct Deposit (EOA) | `0x391E7C679d29bD940d63be94AD22A25d25b5A604` | Native deposits with calldata. Owner of GasZipV2 and GasZip v1. Nonce 172,913. |
| **GasZipV2** | `0x2a37D63EAdFe4b4682a3c28C1c2cD4F109Cc2762` | Verified `GasZipV2`, 1,499 B. |
| GasZip v1 (legacy) | `0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390` | Verified `GasZip`, 943 B. Owner = the Direct Deposit EOA. |
| **GasLZV2** | `0x26DA582889f59EaaE9dA1f063bE0140CD93E6a4f` | 9,503 B. Owner `0xBC2C7144b1F8D708A0601961da6B6102f4Af286a` (EOA, nonce 29). |
| Payout signer (EOA) | `0x5baBE600b9fCD5fB7b66c0611bF4896D967b23A1` | Sends the Ethereum payouts. Nonce 1,023,352. |
| Payout signer (EOA) | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | Also pays on Ethereum, rarely. Nonce 5,540. |
| LayerZero EndpointV2 | `0x1a44076050125825900e736c501f859c50fE728c` | Emits `PacketSent` for GasLZV2 sends. |

## 4. Addresses — Base (chain ID 8453)

| Role | Address | One-liner |
|------|---------|-----------|
| Direct Deposit (EOA) | `0x391E7C679d29bD940d63be94AD22A25d25b5A604` | Nonce 259,403. |
| **GasZipV2** | `0x2a37D63EAdFe4b4682a3c28C1c2cD4F109Cc2762` | Same code as Ethereum. |
| **GasLZV2** | `0x26DA582889f59EaaE9dA1f063bE0140CD93E6a4f` | Same code. Owner EOA nonce 37. |
| Payout signer (EOA) | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | Nonce 2,391,642. |

GasZip v1 is not deployed on Base: `eth_getCode` returns `0x` at `0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390`.

## 5. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | One-liner |
|------|---------|-----------|
| Direct Deposit (EOA) | `0x391E7C679d29bD940d63be94AD22A25d25b5A604` | Nonce 152,105. |
| **GasZipV2** | `0x2a37D63EAdFe4b4682a3c28C1c2cD4F109Cc2762` | Same code. |
| GasZip v1 (legacy) | `0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390` | Same code as Ethereum. Owner = the Direct Deposit EOA. |
| **GasLZV2** | `0x26DA582889f59EaaE9dA1f063bE0140CD93E6a4f` | Same code. Owner EOA nonce 54. |
| Payout signer (EOA) | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | Nonce 1,581,277. |

## 6. Addresses — Optimism (chain ID 10)

| Role | Address | One-liner |
|------|---------|-----------|
| Direct Deposit (EOA) | `0x391E7C679d29bD940d63be94AD22A25d25b5A604` | Nonce 89,074. |
| **GasZipV2** | `0x2a37D63EAdFe4b4682a3c28C1c2cD4F109Cc2762` | Same code. |
| GasZip v1 (legacy) | `0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390` | Same code as Ethereum. Owner = the Direct Deposit EOA. |
| **GasLZV2** | `0x26DA582889f59EaaE9dA1f063bE0140CD93E6a4f` | Same code. Owner EOA nonce 36. |
| Payout signer (EOA) | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | Nonce 859,437. |

## 7. Addresses — Polygon PoS (chain ID 137)

| Role | Address | One-liner |
|------|---------|-----------|
| Direct Deposit (EOA) | `0x391E7C679d29bD940d63be94AD22A25d25b5A604` | Nonce 23,814. |
| **GasZipV2** | `0x2a37D63EAdFe4b4682a3c28C1c2cD4F109Cc2762` | Same code. |
| **GasLZV2** | `0x26DA582889f59EaaE9dA1f063bE0140CD93E6a4f` | Same code. Owner EOA nonce 39. |
| Payout signer (EOA) | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | Nonce 341,332. |

GasZip v1 is not deployed on Polygon (`eth_getCode` = `0x`).

## 8. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | One-liner |
|------|---------|-----------|
| Direct Deposit (EOA) | `0x391E7C679d29bD940d63be94AD22A25d25b5A604` | Nonce 98,236. |
| **GasZipV2** | `0x2a37D63EAdFe4b4682a3c28C1c2cD4F109Cc2762` | Same code. |
| **GasLZV2** | `0x26DA582889f59EaaE9dA1f063bE0140CD93E6a4f` | Same code. Owner EOA nonce 38. |
| Payout signer (EOA) | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | Nonce 739,226. |

GasZip v1 is not deployed on BNB (`eth_getCode` = `0x`).

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

| Role | Address | One-liner |
|------|---------|-----------|
| Direct Deposit (EOA) | `0x391E7C679d29bD940d63be94AD22A25d25b5A604` | Nonce 16,794. |
| **GasZipV2** | `0x2a37D63EAdFe4b4682a3c28C1c2cD4F109Cc2762` | Same code. |
| **GasLZV2** | `0x26DA582889f59EaaE9dA1f063bE0140CD93E6a4f` | Same code. Owner EOA nonce 44. |
| Payout signer (EOA) | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | Nonce 89,099. |

GasZip v1 is not deployed on Avalanche (`eth_getCode` = `0x`).

## 10. Addresses — Robinhood Chain (chain ID 4663): payouts only

Gas.zip pays out on Robinhood Chain but does not accept deposits there. A quote with source chain 4663 returns `{"error":"Source: Chain Disabled"}`. `eth_getCode` returns `0x` for GasZipV2 and GasLZV2 at their addresses, and the Direct Deposit EOA has nonce 0 and balance 0 there. Robinhood Chain is not in the docs' deposit-chain list.

| Role | Address | One-liner |
|------|---------|-----------|
| Payout signer (EOA) | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | Sends the Robinhood Chain payouts. Nonce 1,248. |
| Unlisted contract (unconfirmed) | `0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390` | A 1,202-byte contract. Its bytecode holds both `deposit` selectors and the `bytes32` `Deposit` topic, like GasZipV2. Its `owner()` is `0x4c968f6bEecf1906710b08e8B472b8Ba6E75F957`, not the Gas.zip owner that the same address has on Plasma and Katana (`0x391E7C679d29bD940d63be94AD22A25d25b5A604`). Not in the docs; 0 `Deposit` logs in the pinned window. Do not treat it as a Gas.zip deposit contract without confirmation. |

## 10a. Addresses — Arc (chain ID 5042)

Arc is a Gas.zip deposit chain (`/v2/chains`: `short` 525, `symbol` USDC, `inbound` true; a quote with source 5042 returns a price). The docs' `inboundChains.ts` lists Arc with `contractAddress` `0x9e22ebec84c7e4c4bd6d4ae7ff6f4d436d6d8390` and the placeholder `directAddress` `0xaAaAaAaaAaAaAaaAaAAAAAAAAaaaAaAaAaaAaaAa`, so there is **no Direct Deposit** on Arc. Verified with `eth_getCode` and `eth_call` on `https://rpc.mainnet.arc.io` on 2026-10-05.

| Role | Address | One-liner |
|------|---------|-----------|
| **Deposit contract** | `0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390` | 1,202 B, same code hash as the unlisted Robinhood contract (§10). Bytecode holds both `deposit` selectors, `withdraw`, `newOwner` and the `bytes32` `Deposit` topic0 `0x7921786f…`. `owner()` = the Gas.zip Direct Deposit EOA `0x391E7C679d29bD940d63be94AD22A25d25b5A604`. Not a proxy. 30 `Deposit` logs in the window 2026-10-04 11:56 – 2026-10-05 10:29 UTC. |
| Payout signer (EOA) | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | Sends the Arc payouts (native USDC). Nonce 1,067 on 2026-10-05 (1,060 one day earlier). |

GasZipV2 `0x2a37D63EAdFe4b4682a3c28C1c2cD4F109Cc2762` and GasLZV2 `0x26DA582889f59EaaE9dA1f063bE0140CD93E6a4f` have no code on Arc. The Direct Deposit EOA has nonce 0 and balance 0 there. Native USDC moves on Arc show as `Transfer` logs from `0xfffffffffffffffffffffffffffffffffffffffe` (seen in the sampled deposit `0x60dacdc57a4d66cdc6239cc54c7f4a20161418959ba021cec8b67ae3d0b7bda5`, sent through an aggregator).

---

## 11. Cross-chain summary

| Chain | ID | Short id | Direct Deposit EOA | GasZipV2 | GasZip v1 | GasLZV2 | Payout signer | `Deposit` (V2) in window | `SentDeposits` in window |
|-------|----|----|----|----|----|----|----|----|----|
| Ethereum | 1 | 255 | ✅ | ✅ | ✅ | ✅ | `0x5baBE600b9fCD5fB7b66c0611bF4896D967b23A1` (+ `0x8C826F795466E39acbfF1BB4eEeB759609377ba1`) | 156 | 0 |
| Base | 8453 | 54 | ✅ | ✅ | — | ✅ | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | 257 | 5 |
| Arbitrum One | 42161 | 57 | ✅ | ✅ | ✅ | ✅ | same | 166 | 5 |
| Optimism | 10 | 55 | ✅ | ✅ | ✅ | ✅ | same | 52 | 0 |
| Polygon PoS | 137 | 17 | ✅ | ✅ | — | ✅ | same | 0 | 0 |
| BNB Smart Chain | 56 | 14 | ✅ | ✅ | — | ✅ | same | 375 | 0 |
| Avalanche C-Chain | 43114 | 15 | ✅ | ✅ | — | ✅ | same | 18 | 0 |
| Robinhood Chain | 4663 | 526 | source disabled | — | see §10 | — | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | 0 | — |
| Arc | 5042 | 525 | — (placeholder) | — (deposit contract `0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390`) | — | — | `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` | 30 (2026-10-04/05 window) | — |

Counts are from the pinned 12-hour window 2026-09-28 00:00–12:00 UTC (Arc: 2026-10-04 11:56 – 2026-10-05 10:29 UTC), emitter = the Gas.zip contract. Direct Deposits and payouts have no log, so the table does not count them. The Gas.zip chains API returns 194 entries (mainnets and testnets); the docs list 77 deposit chains, most of them outside the eight.

---

## 12. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **GasZipV2** | Immutable | EIP-1967 slots empty; same 1,499-byte code on seven chains; the verified source has no upgrade path. | None. The owner EOA can `withdraw` and `newOwner`. |
| **GasZip v1** | Immutable | EIP-1967 slots empty; 943 B; verified source. | None. Same owner. |
| **GasLZV2** | Immutable | EIP-1967 slots empty; same 9,503-byte code on seven chains; source has no upgrade path. | None. The owner EOA `0xBC2C7144b1F8D708A0601961da6B6102f4Af286a` controls peers, gas limits, DVN config and `withdraw`. |

All three contracts are owned by EOAs. No contract here is a proxy.

---

## 13. Detection invariants & gotchas

1. **The main deposit path has no log.** A Direct Deposit is a native transfer to `0x391E7C679d29bD940d63be94AD22A25d25b5A604`. Capture it from transactions (`to` = that EOA, `value > 0`) and decode the calldata (§2.3). A deposit with bad calldata or an amount outside the limits needs a manual refund through Gas.zip support.
2. **The payout has no log and no key.** A payout is a native transfer from `0x8C826F795466E39acbfF1BB4eEeB759609377ba1`, or from `0x5baBE600b9fCD5fB7b66c0611bF4896D967b23A1` on Ethereum. Link it through the Gas.zip API (`/v2/deposit/{hash}`, `/v2/search/{hash}`). An on-chain match by recipient, amount and time is approximate: fees and price conversion change the amount.
3. **`Deposit.to` is left-aligned.** GasZipV2 stores an EVM recipient as `bytes32(bytes20(to))`: the address is in the high 20 bytes. Decode `substring(to from 1 for 20)`, not the low 20 bytes. A non-EVM recipient fills all 32 bytes.
4. **`Deposit.chains` holds Gas.zip short ids, not chain ids.** Each id is 2 bytes (§0 table). One deposit can fund several chains; the amount is split equally.
5. **`Deposit.from` is often an aggregator.** LI.FI (`0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE`) and Rango call `deposit`. The end user is `tx.from`. Example: Ethereum deposit `0x6797de406deb83610d2465a5c68cf72a30c79aff98269ac04c3d748e4f4c3c04` has `from` = the LI.FI diamond.
6. **GasZipV2 holds the deposits until the owner sweeps them.** The Direct Deposit EOA calls `withdraw(0x0000000000000000000000000000000000000000)` (no event) and, on Ethereum, forwards the ETH to the Ethereum payout signer. A large native outflow from GasZipV2 to its owner is routine.
7. **Selector collision.** `deposit(uint256,address)` = `0x6e553f65` = the ERC-4626 vault `deposit`. Never key on the selector alone.
8. **The v1 `Deposit` topic is not unique.** In the pinned window, the only Ethereum emitter of `0x02d7e648dd130fc184d383e55bb126ac4c9c60e8f94bf05acdf557ba2d540b47` was an unrelated transparent proxy, `0xdad503f8b9d42bb7af3afc588358d30163e4416f`. GasZip v1 itself emitted 0 on Ethereum, Arbitrum and Optimism. Filter on the emitter.
9. **LayerZero refuel packs the destination in the parameter.** Per the code, `uint32(params[i] >> 224)` is the LayerZero eid and `uint128(params[i])` is the drop amount. The README says "leftmost 16 bits" for the chain and "rightmost 240 bits" for the amount; the code is the source of truth. The destination gets a LayerZero executor native drop, not a Gas.zip transfer.
10. **Robinhood Chain is destination-only.** Payouts there come from `0x8C826F795466E39acbfF1BB4eEeB759609377ba1` (nonce 1,248). A native transfer to the Direct Deposit EOA on Robinhood Chain is not a supported deposit. The same 1,202 B code at `0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390` is the official deposit contract on Arc (owner = Gas.zip) but not on Robinhood Chain (owner `0x4c968f6bEecf1906710b08e8B472b8Ba6E75F957`): check `owner()` per chain.
11. **Admin changes leave no log on GasZipV2.** `newOwner` and `withdraw` emit nothing; watch their selectors (`0x85952454`, `0x51cff8d9`). GasLZV2 ownership changes do emit `OwnershipTransferred`.
12. **Arc has no Direct Deposit.** Arc deposits are `Deposit` logs at `0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390`, not at GasZipV2. The amount is native USDC (18 decimals on chain).

---

## 14. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_GASZIPV2_DEPOSIT               = '\x7921786f0ead54b0a0502b86991470e5c4790dadc22242f4ff071f361e8e6c68'
TOPIC_GASZIP_V1_DEPOSIT              = '\x02d7e648dd130fc184d383e55bb126ac4c9c60e8f94bf05acdf557ba2d540b47'
TOPIC_GASLZ_SENT_DEPOSITS            = '\xa22a487af6300dc77db439586e8ce7028fd7f1d734efd33b287bc1e2af4cd162'
TOPIC_GASLZ_SENT_MESSAGES            = '\x14af90211b59e95afdafa93c2cb547e61a4e6b0e74cfad8c3d7b6c3d48e6c29d'
TOPIC_OWNERSHIP_TRANSFERRED          = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_LZ_PACKET_SENT                 = '\x1ab700d4ced0c005b164c0f789fd09fcbb0156d4c2041b8a3bfbcd961cd1567f'

-- ===== Selectors (chain-agnostic) =====
SEL_DEPOSIT_BYTES32                  = '\xc9630cb0'
SEL_DEPOSIT_ADDRESS                  = '\x6e553f65'   -- same as ERC-4626 deposit
SEL_GASZIP_WITHDRAW                  = '\x51cff8d9'
SEL_GASZIP_NEW_OWNER                 = '\x85952454'
SEL_SEND_DEPOSITS                    = '\x89a281b6'
SEL_SEND_MESSAGES                    = '\xd29e9f32'
SEL_GASLZ_WITHDRAW                   = '\xf3fef3a3'
SEL_GASLZ_SET_PEERS                  = '\x3772df58'
SEL_GASLZ_SET_DELEGATE               = '\xca5eb5e1'
SEL_GASLZ_SET_ULN_CONFIGS            = '\x2b94e499'

-- ===== Contracts (same address on the seven deposit chains) =====
ETH_GASZIPV2                         = '\x2a37d63eadfe4b4682a3c28c1c2cd4f109cc2762'
BASE_GASZIPV2                        = '\x2a37d63eadfe4b4682a3c28c1c2cd4f109cc2762'
ARB_GASZIPV2                         = '\x2a37d63eadfe4b4682a3c28c1c2cd4f109cc2762'
OP_GASZIPV2                          = '\x2a37d63eadfe4b4682a3c28c1c2cd4f109cc2762'
POLY_GASZIPV2                        = '\x2a37d63eadfe4b4682a3c28c1c2cd4f109cc2762'
BNB_GASZIPV2                         = '\x2a37d63eadfe4b4682a3c28c1c2cd4f109cc2762'
AVAX_GASZIPV2                        = '\x2a37d63eadfe4b4682a3c28c1c2cd4f109cc2762'
ETH_GASLZV2                          = '\x26da582889f59eaae9da1f063be0140cd93e6a4f'
BASE_GASLZV2                         = '\x26da582889f59eaae9da1f063be0140cd93e6a4f'
ARB_GASLZV2                          = '\x26da582889f59eaae9da1f063be0140cd93e6a4f'
OP_GASLZV2                           = '\x26da582889f59eaae9da1f063be0140cd93e6a4f'
POLY_GASLZV2                         = '\x26da582889f59eaae9da1f063be0140cd93e6a4f'
BNB_GASLZV2                          = '\x26da582889f59eaae9da1f063be0140cd93e6a4f'
AVAX_GASLZV2                         = '\x26da582889f59eaae9da1f063be0140cd93e6a4f'
ETH_GASZIP_V1                        = '\x9e22ebec84c7e4c4bd6d4ae7ff6f4d436d6d8390'
ARB_GASZIP_V1                        = '\x9e22ebec84c7e4c4bd6d4ae7ff6f4d436d6d8390'
OP_GASZIP_V1                         = '\x9e22ebec84c7e4c4bd6d4ae7ff6f4d436d6d8390'

-- ===== Direct Deposit EOA (same address on the seven deposit chains) =====
ETH_DIRECT_DEPOSIT_EOA               = '\x391e7c679d29bd940d63be94ad22a25d25b5a604'
BASE_DIRECT_DEPOSIT_EOA              = '\x391e7c679d29bd940d63be94ad22a25d25b5a604'
ARB_DIRECT_DEPOSIT_EOA               = '\x391e7c679d29bd940d63be94ad22a25d25b5a604'
OP_DIRECT_DEPOSIT_EOA                = '\x391e7c679d29bd940d63be94ad22a25d25b5a604'
POLY_DIRECT_DEPOSIT_EOA              = '\x391e7c679d29bd940d63be94ad22a25d25b5a604'
BNB_DIRECT_DEPOSIT_EOA               = '\x391e7c679d29bd940d63be94ad22a25d25b5a604'
AVAX_DIRECT_DEPOSIT_EOA              = '\x391e7c679d29bd940d63be94ad22a25d25b5a604'

-- ===== Payout signers (EOAs) =====
ETH_PAYOUT_SIGNER_EOA                = '\x5babe600b9fcd5fb7b66c0611bf4896d967b23a1'
ETH_PAYOUT_SIGNER_2_EOA              = '\x8c826f795466e39acbff1bb4eeeb759609377ba1'
BASE_PAYOUT_SIGNER_EOA               = '\x8c826f795466e39acbff1bb4eeeb759609377ba1'
ARB_PAYOUT_SIGNER_EOA                = '\x8c826f795466e39acbff1bb4eeeb759609377ba1'
OP_PAYOUT_SIGNER_EOA                 = '\x8c826f795466e39acbff1bb4eeeb759609377ba1'
POLY_PAYOUT_SIGNER_EOA               = '\x8c826f795466e39acbff1bb4eeeb759609377ba1'
BNB_PAYOUT_SIGNER_EOA                = '\x8c826f795466e39acbff1bb4eeeb759609377ba1'
AVAX_PAYOUT_SIGNER_EOA               = '\x8c826f795466e39acbff1bb4eeeb759609377ba1'
RH_PAYOUT_SIGNER_EOA                 = '\x8c826f795466e39acbff1bb4eeeb759609377ba1'
ARC_PAYOUT_SIGNER_EOA                = '\x8c826f795466e39acbff1bb4eeeb759609377ba1'

-- ===== Arc (chain ID 5042): contract deposits only =====
ARC_GASZIP_DEPOSIT_CONTRACT          = '\x9e22ebec84c7e4c4bd6d4ae7ff6f4d436d6d8390'   -- 1,202 B build; emits TOPIC_GASZIPV2_DEPOSIT

-- ===== Owners and infrastructure =====
ETH_GASLZV2_OWNER_EOA                = '\xbc2c7144b1f8d708a0601961da6b6102f4af286a'   -- same EOA on all seven chains
ETH_LZ_ENDPOINT_V2                   = '\x1a44076050125825900e736c501f859c50fe728c'
```

---

## 15. Verification & sources

How the constants in this file were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from the verified `GasZipV2` source (Ethereum, verified 2024-09-26), `gas-contracts/src/GasZip.sol` (v1; also verified on Ethereum as `GasZip`), `gas-lz-contracts/src/v2/GasLZV2.sol`, `OptimizedOApp.sol` and `Ownable.sol`. The live `Deposit` topic0 appears at GasZipV2 on six of the seven deposit chains, and `SentDeposits` at GasLZV2 on Base and Arbitrum.
- **Addresses:** the Direct Deposit and GasZipV2 addresses come from `data/gas/inboundChains.ts` (the same two addresses for all seven target deposit chains). GasLZV2 comes from `data/layerzero/lzConfigData.json` (the same address and the LayerZero eids for the seven chains). The GasZip v1 address comes from the docs' contract-deposit example and is verified as `GasZip` on Ethereum. The payout signers come from the Gas.zip API: `/v2/deposit/0x6797de406deb83610d2465a5c68cf72a30c79aff98269ac04c3d748e4f4c3c04` returns the Base payout `0x1552599e6fcebef44c0caf6753d4957ab53881036b087065bad68c626d51a8c4` with `signer` = `0x8C826F795466E39acbfF1BB4eEeB759609377ba1`, and `/v2/search/0xb52ebe246d1b688a91476659beb5d4076cb359cdfce9208bca0c1eaadb24f90a` returns an Ethereum payout with `signer` = `0x5baBE600b9fCD5fB7b66c0611bF4896D967b23A1`. `owner()` of GasZipV2 (seven chains) and of GasZip v1 (Ethereum, Arbitrum, Optimism) returns the Direct Deposit EOA. `owner()` of GasLZV2 returns `0xBC2C7144b1F8D708A0601961da6B6102f4Af286a` on all seven chains; it has no code on any of them. The short ids come from `/v2/chains`.
- **Encoding:** the quote API returned `calldata` `0x0100390037` and a `contractDepositTxn` with `chains` = `0x00390037` for Base → Arbitrum + Optimism, and `0x01020e` for Base → Robinhood Chain.
- **Value movement, read from receipts:** Ethereum deposit `0x6797de406deb83610d2465a5c68cf72a30c79aff98269ac04c3d748e4f4c3c04` (LI.FI → GasZipV2, `Deposit` with 128 bytes of data); Base payout `0x1552599e6fcebef44c0caf6753d4957ab53881036b087065bad68c626d51a8c4` (native from `0x8C826F795466E39acbfF1BB4eEeB759609377ba1`, no logs); Ethereum payout `0xb52ebe246d1b688a91476659beb5d4076cb359cdfce9208bca0c1eaadb24f90a` (native from `0x5baBE600b9fCD5fB7b66c0611bF4896D967b23A1`, no logs); Base refuel `0x05d2002c001119b8d12611c027e86f0eab099865cdbfe2bbaf09c5e8fba38f59` (`sendDeposits`, EndpointV2 `PacketSent`, then `SentDeposits`).
- **Activity:** see §11. The Ethereum `Deposit` count (156) was measured twice with the same result. Nonces are transaction counts at the latest block on 2026-09-29.
- **Chain coverage:** the seven chains other than Robinhood Chain carry all current contracts. Robinhood Chain is destination-only (API refusal, empty contract addresses, payout signer active; re-checked 2026-10-05: `/v2/chains` shows `inbound` true for 4663, but a quote with source 4663 still returns `Source: Chain Disabled`). Arc (2026-10-05): `inboundChains.ts` entry, `/v2/chains`, a priced quote from source 5042, `eth_getCode` / `owner()` / bytecode scan of the deposit contract, `eth_getLogs` count, payout-signer nonce.

Authoritative sources:
- [gasdotzip/gas-contracts](https://github.com/gasdotzip/gas-contracts) — `src/GasZip.sol`, `script/Deploy.s.sol`, `README.md`.
- [gasdotzip/gas-lz-contracts](https://github.com/gasdotzip/gas-lz-contracts) — `src/v2/GasLZV2.sol`, `src/v2/OptimizedOApp.sol`, `src/v2/Ownable.sol`, `README.md`.
- [gasdotzip/documentation](https://github.com/gasdotzip/documentation) — `data/gas/inboundChains.ts`, `data/layerzero/lzConfigData.json`, `docs/pages/gas/overview.mdx`, `docs/pages/gas/code-examples/evm-deposit/direct-forwarder.mdx`, `docs/pages/gas/code-examples/evm-deposit/contract-forwarder.mdx`, `docs/pages/gas/api/*.mdx`.
- Docs site — [dev.gas.zip](https://dev.gas.zip/).
- API — [chains](https://backend.gas.zip/v2/chains) · `https://backend.gas.zip/v2/quotes/{chain}/{wei}/{chains}` · `https://backend.gas.zip/v2/deposit/{hash}` · `https://backend.gas.zip/v2/search/{hash}`.
- Verified source — [GasZipV2 on Blockscout](https://eth.blockscout.com/address/0x2a37D63EAdFe4b4682a3c28C1c2cD4F109Cc2762) · [GasZip v1 on Blockscout](https://eth.blockscout.com/address/0x9E22ebeC84c7e4C4bD6D4aE7FF6f4D436D6D8390).
