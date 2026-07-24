# USDT0 (Tether omnichain bridge) — Topics, Selectors, Addresses (Ethereum + Arbitrum + Optimism + Polygon of the 7; ~23 chains total)

**Status:** verified against Ethereum, Arbitrum One, Optimism, Polygon PoS, Base, BNB, and Avalanche live RPC, the official docs (`docs.usdt0.to`), and the canonical `Everdawn-Labs/usdt0-*` repos / OpenZeppelin audit, on 2026-06-09.
**Scope:** the on-chain bridge contracts behind the Dune **"tether"** bridge category — i.e. **USDT0**, the LayerZero-v2 OFT representation of Tether USD₮. Topics + selectors are **chain-agnostic**; addresses are network-specific. Of the seven requested chains, USDT0 is **live on Ethereum (lockbox), Arbitrum One, Optimism, and Polygon PoS**, and **NOT deployed on Base, BNB Smart Chain, or Avalanche C-Chain** (`eth_getCode` = `0x` for every USDT0 address on those three).

USDT0 is a **lock-and-mint omnichain stablecoin** built on **LayerZero v2's OFT (Omnichain Fungible Token) standard**. The canonical collateral is **native USD₮ (`0xdAC17F958D2ee523a2206206994597C13D831ec7`) locked in an Ethereum-mainnet lockbox** — the `OAdapterUpgradeable` "OFT Adapter" at `0x6C96dE32CEa08842dcc4058c14d3aaAD7Fa41dee`. On every other chain, USDT0 is a **freshly mint/burnable token** (`symbol()`/`name()` = `USD₮0`, 6-dec) paired with a sibling **OFT messenger contract** that holds the LayerZero wiring. A cross-chain transfer = `send()` on the source OFT → source token burned/locked → LayerZero relays a verified packet (DVN attests, Executor delivers) → destination OFT calls the destination token's mint → `OFTReceived`. **This is NOT a Tether-treasury EOA mint/burn**: minting/burning is performed by the OFT contracts under LayerZero messaging, not by an off-chain Tether key (the legacy native USD₮ minting is a separate, unrelated flow).

**Two distinct contracts per non-lockbox chain** (the single most important fact for indexing): an **OFT** (the LayerZero messenger; emits `OFTSent`/`OFTReceived`, owns peers/options) and a **Token** (the ERC-20 `USD₮0` users hold; emits `Transfer`/`Mint`/`Burn`). On the lockbox chain (Ethereum) these collapse into **one** `OAdapterUpgradeable` that wraps the pre-existing native USD₮. Every USDT0 contract is a **TransparentUpgradeableProxy** (EIP-1967) governed by a per-chain `ProxyAdmin`, ultimately owned by a **shared Safe `0x4DFF9b5b0143E642a3F63a5bcf2d1C328e600bf8`** (identical address on ETH/ARB/OP/Polygon).

> **XAUt0** (omnichain Tether Gold) is a sibling product on the same OFT framework (ETH OFT `0xb9c2321BB7D0Db468f570D10A424d1Cc8EFd696C`, inner `0x68749665…`). It is **not** part of the "tether"-USD bridge category and is not deployed on any of the 7 requested chains as a target — out of scope here, noted for disambiguation.

---

## 0. Contract families & versions

| Contract | Role | Lives on (of the 7) | Proxy? |
|----------|------|---------------------|--------|
| **OAdapterUpgradeable** ("OFT Adapter" / lockbox) | Wraps **pre-existing** native USD₮; `approvalRequired()=true`; on `send` it **locks** USD₮ via `transferFrom`, on receive it **unlocks**. Emits `OFTSent`/`OFTReceived`. | **Ethereum only** | EIP-1967 Transparent |
| **OUpgradeable** ("OFT") | LayerZero messenger on mint/burn chains; `approvalRequired()=false`; on `send` it **burns** the sibling Token, on receive it **mints** it. Emits `OFTSent`/`OFTReceived`. | Arbitrum, Optimism, Polygon | EIP-1967 Transparent |
| **TetherTokenOFTExtension** (Token) | The user-held `USD₮0` ERC-20 on standard chains. **ERC-7802** crosschain-mint/burn surface (`crosschainMint`/`crosschainBurn`); the OFT is its authorized bridge. | Optimism (+ most non-ETH chains) | EIP-1967 Transparent |
| **ArbitrumExtensionV2** (Token) | Arbitrum-specific `USD₮0` ERC-20. Uses **Arbitrum gateway** semantics (`bridgeMint`/`bridgeBurn`, `l1Address()`) **plus** OFT mint/burn — no ERC-7802 crosschain events. | **Arbitrum only** | EIP-1967 Transparent |
| **(native USD₮)** (Token) | On Polygon the OFT's inner token is the **pre-existing PoS-bridged native USD₮** (`0xc2132D05…`), not a USDT0-deployed token. | Polygon | (Polygon PoS proxy) |
| **MultiHop Composer** | LayerZero `lzCompose` router that chains OFT hops (e.g. A→ETH→B) in one message; calls `send` internally. | Arbitrum (of the 7) | non-proxy contract |
| **HyperCore Composer** | Bridges into Hyperliquid HyperCore; **not on any of the 7** (HyperEVM `0x80123Ab5…`). | — (HyperEVM) | — |
| **ProxyAdmin** | OpenZeppelin TransparentUpgradeableProxy admin; one per proxy family per chain. | all present chains | non-proxy |
| **Safe** | Gnosis Safe multisig that owns the ProxyAdmins + is the OFT `owner()` / LZ delegate. Same literal address on ETH/ARB/OP/Polygon. | all present chains | Safe proxy (171 B) |
| **LayerZero EndpointV2** | The shared LZ v2 endpoint all OFTs call; `0x1a44076050125825900e736c501f859c50fe728c` (same on all 4 present chains). Emits `PacketSent`/`PacketDelivered`. Not a USDT0 contract. | all 4 present | — |

The OFT impl bytecode is the **same `OUpgradeable` build** on Arbitrum/Optimism/Polygon (≈11,769-byte impl), deployed to **different impl addresses per chain** (CREATE, not CREATE2 — impls diverge; the **proxy** addresses are vanity/per-chain too). Ethereum's impl is the `OAdapterUpgradeable` variant (≈11,665 B, with the lock/unlock branch).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-09; the OFT and token events were additionally confirmed against live `eth_getLogs` (see §11).

### 1.1 OFT / OFT Adapter (`OAdapterUpgradeable` on ETH, `OUpgradeable` elsewhere)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a` | `OFTSent(bytes32 indexed guid, uint32 dstEid, address indexed fromAddress, uint256 amountSentLD, uint256 amountReceivedLD)` | **Source-side send.** 3 topics. *(verified live: ETH adapter, ARB OFT)* |
| `0xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c` | `OFTReceived(bytes32 indexed guid, uint32 srcEid, address indexed toAddress, uint256 amountReceivedLD)` | **Destination-side receive.** *(verified live: ETH adapter, ARB OFT)* |
| `0x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b` | `PeerSet(uint32 eid, bytes32 peer)` | Trusted-remote peer set/changed — **watch for re-peering**. |
| `0xbe4864a8e820971c0247f5992e2da559595f7bf076a21cb5928d443d2a13b674` | `EnforcedOptionSet((uint32,uint16,bytes)[] _enforcedOptions)` | Per-route gas/exec options changed. |
| `0xf0be4f1e87349231d80c36b33f9e8639658eeaf474014dee15a3e6a4d4414197` | `MsgInspectorSet(address inspector)` | Optional message inspector set. |
| `0xd48d879cef83a1c0bdda516f27b13ddb1b3f8bbac1c9e1511bb2a659c2427760` | `PreCrimeSet(address preCrime)` | PreCrime simulator set. |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` | Ownable. |

`guid` is the LayerZero global message id — the **cross-chain join key** (`OFTSent.guid` on source == `OFTReceived.guid` on destination). `fromAddress`/`toAddress` are the real user; the `tx.from` is often a relayer/Executor. `amountSentLD`/`amountReceivedLD` are in local decimals (6 for USD₮); with `decimalConversionRate=1` they are equal (no dust).

### 1.2 Token — `TetherTokenOFTExtension` (Optimism + most non-ETH chains; ERC-7802)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20. Mint = from `0x0`; burn = to `0x0`. *(370 live in 5k OP blocks)* |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ERC-20. |
| `0x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885` | `Mint(address indexed to, uint256 value)` | Legacy Tether-style mint event. *(verified live on OP)* |
| `0xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5` | `Burn(address indexed from, uint256 value)` | Legacy Tether-style burn event. *(verified live on OP)* |
| `0xde22baff038e3a3e08407cbdf617deed74e869a7ba517df611e33131c6e6ea04` | `CrosschainMint(address indexed to, uint256 amount, address indexed sender)` | **ERC-7802** — fired by the OFT when crediting on receive. *(verified live on OP)* |
| `0xb90795a66650155983e242cac3e1ac1a4dc26f8ed2987f3ce416a34e00111fd4` | `CrosschainBurn(address indexed from, uint256 amount, address indexed sender)` | **ERC-7802** — fired when the OFT debits on send. *(verified live on OP)* |

**Per cross-chain leg the OP token fires BOTH a legacy `Mint`/`Burn` AND an ERC-7802 `CrosschainMint`/`CrosschainBurn`** plus a zero-address `Transfer` — three log families for one bridge action. Count any one of them, not all, to avoid triple-counting.

### 1.3 Token — `ArbitrumExtensionV2` (Arbitrum only)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` | ERC-20. Bridge mint = from `0x0`; burn = to `0x0`. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address,address,uint256)` | ERC-20. |

**The Arbitrum token has NO `Mint`/`Burn`/`CrosschainMint`/`CrosschainBurn` events** (`0f6798a5…`, `cc16f5db…`, `de22baff…`, `b90795a6…` are absent from its bytecode). On Arbitrum, detect mint/burn by the **zero-address `Transfer`** on the token, or by `OFTSent`/`OFTReceived` on the OFT. Its mint/burn entrypoints are the **Arbitrum-gateway** `bridgeMint`/`bridgeBurn` (§2.4), which the OFT calls but which themselves only emit `Transfer`.

### 1.4 Proxy / upgrade constants (all USDT0 proxies)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **watch this on every proxy to catch impl rotations.** |
| `0x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f` | `AdminChanged(address previousAdmin, address newAdmin)` |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` (OZ v4 Initializable — fires on init) |

### 1.5 LayerZero EndpointV2 (`0x1a44…728c`, the transport layer — not a USDT0 contract)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x1ab700d4ced0c005b164c0f789fd09fcbb0156d4c2041b8a3bfbcd961cd1567f` | `PacketSent(bytes encodedPayload, bytes options, address sendLibrary)` | Emitted by the Endpoint on the source chain alongside `OFTSent`. |
| `0x3cd5e48f9730b129dc7550f0fcea9c767b7be37837cd10e55eb35f734f4bca04` | `PacketDelivered((uint32,bytes32,uint64) origin, address receiver)` | Endpoint on destination on successful delivery. |
| `0x0d87345f3d1c929caba93e1c3821b54ff3512e12b66aa3cfe54b6bcbc17e59b4` | `PacketVerified((uint32,bytes32,uint64) origin, address receiver, bytes32 payloadHash)` | DVN verification recorded. |

These are shared across **every** LayerZero OFT on the chain — filter by the USDT0 OFT as the `sender`/`receiver`, never by topic0 alone.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All selectors below verified **present** in the live impl bytecode on 2026-06-09 (PUSH4 dispatcher scan); see §11.

### 2.1 OFT / OFT Adapter (state-changing + LZ wiring)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc7c7f5b3` | `send((uint32 dstEid,bytes32 to,uint256 amountLD,uint256 minAmountLD,bytes extraOptions,bytes composeMsg,bytes oftCmd) sendParam, (uint256 nativeFee,uint256 lzTokenFee) fee, address refundAddress)` | **The bridge entrypoint.** `payable`. Emits `OFTSent`. |
| `0x3b6f743b` | `quoteSend((...) sendParam, bool payInLzToken)` | `(uint256 nativeFee, uint256 lzTokenFee)` — fee quote. |
| `0x0d35b415` | `quoteOFT((...) sendParam)` | `(OFTLimit, OFTFeeDetail[], OFTReceipt)` — amount/limit preview. |
| `0x13137d65` | `lzReceive((uint32,bytes32,uint64) origin, bytes32 guid, bytes message, address executor, bytes extraData)` | LayerZero delivery hook → mints/unlocks, emits `OFTReceived`. Callable only by the Endpoint. |
| `0x3400288b` | `setPeer(uint32 eid, bytes32 peer)` | Owner-only; emits `PeerSet`. |
| `0xb98bd070` | `setEnforcedOptions((uint32,uint16,bytes)[] enforcedOptions)` | Owner-only; emits `EnforcedOptionSet`. |
| `0x6fc1b31e` | `setMsgInspector(address inspector)` | Owner-only; emits `MsgInspectorSet`. |
| `0xd4243885` | `setPreCrime(address preCrime)` | Owner-only; emits `PreCrimeSet`. |
| `0xca5eb5e1` | `setDelegate(address delegate)` | Sets the LayerZero delegate (config authority). |
| `0xf2fde38b` | `transferOwnership(address newOwner)` | Ownable; emits `OwnershipTransferred`. |

### 2.2 OFT — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xfc0c546a` | `token()` | inner ERC-20 (ETH→USD₮ `0xdAC17F…`; ARB/OP→the sibling Token; Polygon→native USD₮ `0xc2132D…`). |
| `0x9f68b964` | `approvalRequired()` | `bool` — **`true` on Ethereum adapter (lockbox)**, `false` on ARB/OP/Polygon OFTs (burn/mint). |
| `0x857749b0` | `sharedDecimals()` | `6` (USD₮). |
| `0x963efcaa` | `decimalConversionRate()` | `1` (local decimals == shared decimals → no dust). |
| `0x156a0d0f` | `oftVersion()` | `(bytes4 interfaceId, uint64 version)` = `(0x02e49c2c, 1)`. |
| `0xbb0b6a53` | `peers(uint32 eid)` | `bytes32` trusted remote for that EID. |
| `0x5e280f11` | `endpoint()` | LayerZero EndpointV2 (`0x1a44…728c`). |
| `0x8da5cb5b` | `owner()` | the Safe `0x4DFF…00bf8`. |

### 2.3 Token — `TetherTokenOFTExtension` (ERC-7802 surface)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x18bf5077` | `crosschainMint(address to, uint256 amount)` | **ERC-7802** — called by the OFT on receive. Emits `CrosschainMint` + `Mint` + `Transfer`. |
| `0x2b8c49e3` | `crosschainBurn(address from, uint256 amount)` | **ERC-7802** — called by the OFT on send. Emits `CrosschainBurn` + `Burn` + `Transfer`. |
| `0x40c10f19` | `mint(address to, uint256 amount)` | Authorized-minter mint. |
| `0xdb006a75` | `redeem(uint256 amount)` | Tether-style redeem (burn from caller/treasury). |
| `0xa9059cbb` / `0x23b872dd` / `0x095ea7b3` | `transfer` / `transferFrom` / `approve` | ERC-20. |
| `0x313ce567` | `decimals()` | `6`. |
| `0x95d89b41` | `symbol()` | `"USD₮0"` (`name()` also `"USD₮0"`). |

### 2.4 Token — `ArbitrumExtensionV2` (Arbitrum-gateway surface)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8c2a993e` | `bridgeMint(address account, uint256 amount)` | **Arbitrum L2-gateway mint** — only emits `Transfer` (from `0x0`). |
| `0x74f4f547` | `bridgeBurn(address account, uint256 amount)` | **Arbitrum L2-gateway burn** — only emits `Transfer` (to `0x0`). |
| `0x40c10f19` | `mint(address to, uint256 amount)` | OFT/authorized-minter mint. |
| `0x9dc29fac` | `burn(address from, uint256 amount)` | OFT/authorized-minter burn. |
| `0xdb006a75` | `redeem(uint256 amount)` | Tether-style redeem. |
| `0xc2eeeebd` | `l1Address()` | the L1 USD₮ this Arbitrum token mirrors. |
| `0xa9059cbb` / `0x23b872dd` / `0x095ea7b3` | `transfer` / `transferFrom` / `approve` | ERC-20. |

**Neither token impl exposes the classic Tether `addBlackList`/`destroyBlackFunds`/`issue`/`pause`/`deprecate`** — those selectors are **absent** from both `TetherTokenOFTExtension` and `ArbitrumExtensionV2` bytecode (confirmed 2026-06-09). USDT0 tokens are *not* the legacy `TetherToken` contract; do not scan for those legacy admin selectors.

### 2.5 Proxy admin (TransparentUpgradeableProxy / ProxyAdmin)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x99a88ec4` | `upgrade(address proxy, address implementation)` | OZ ProxyAdmin (v4). Emits `Upgraded` on the proxy. |
| `0x9623609d` | `upgradeAndCall(address proxy, address implementation, bytes data)` | `payable`. |
| `0xf2fde38b` | `transferOwnership(address)` | ProxyAdmin owner = the Safe. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1) — the lockbox

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. LZ EID **30101**. Wiring confirmed live: adapter `token()` = native USD₮; `approvalRequired()` = `true`; `endpoint()` = `0x1a44…728c`; `owner()` = the Safe; `peers(30110)` = ARB OFT, `peers(30109)` = Polygon OFT.

| Role | Address | One-liner |
|------|---------|-----------|
| **OFT Adapter** (proxy, lockbox) | `0x6C96dE32CEa08842dcc4058c14d3aaAD7Fa41dee` | `OAdapterUpgradeable`. Locks/unlocks native USD₮; emits `OFTSent`/`OFTReceived`. Impl slot → below. |
| OFT Adapter impl | `0xcd979b10a55fcdac23ec785ce3066c6ef8a479a4` | `OAdapterUpgradeable` implementation (read live from EIP-1967 slot). |
| OFT ProxyAdmin | `0x4de7096B2131E84Fd6b2042AD8cd9B4E43F728Fc` | OZ ProxyAdmin (admin slot of the adapter proxy). |
| **Safe** (owner / LZ delegate) | `0x4DFF9b5b0143E642a3F63a5bcf2d1C328e600bf8` | Gnosis Safe; owns ProxyAdmin + is adapter `owner()`. |
| native **USD₮** (inner token) | `0xdAC17F958D2ee523a2206206994597C13D831ec7` | The pre-existing Tether USD₮ locked as collateral. **Not a USDT0 contract.** |
| LayerZero EndpointV2 | `0x1a44076050125825900e736c501f859c50fe728c` | LZ v2 transport. **Not a USDT0 contract.** |

There is **no separate USDT0 "Token" contract on Ethereum** — the adapter wraps the existing USD₮, so users hold ordinary USD₮ on L1.

---

## 4. Addresses — Arbitrum One (chain ID 42161)

Verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com`. LZ EID **30110**. OFT `approvalRequired()` = `false` (burn/mint); `token()` = the ArbitrumExtensionV2 Token proxy; `owner()` = the Safe; `endpoint()` = `0x1a44…728c`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OFT** (proxy) | `0x14E4A1B13bf7F943c8ff7C51fb60FA964A298D92` | `OUpgradeable`. Burns/mints the Token; emits `OFTSent`/`OFTReceived`. |
| OFT impl | `0x00678fdaab0d5c91b843a22fa38e08af1bbda85e` | `OUpgradeable` implementation. |
| OFT ProxyAdmin | `0xa882c21C9df00958A958cde96f2B2Ae8FB4315B1` | (same literal as the OP OFT ProxyAdmin — key on `(chainId,addr)`). |
| **Token** (proxy, `USD₮0`) | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` | `ArbitrumExtensionV2`. ERC-20 users hold; `symbol()="USD₮0"`, 6-dec. |
| Token impl | `0x3263cd783823d04a6b9819517e0e6840d37ca3f4` | `ArbitrumExtensionV2` implementation (gateway `bridgeMint`/`bridgeBurn`). |
| Token ProxyAdmin | `0x553ec478A66BE27Ba25A6bc5dB20AEc2eD6A1B4A` | |
| **MultiHop Composer** | `0x759BA420bF1ded1765F18C2DC3Fc57A1964A2Ad1` | LZ `lzCompose` multi-hop router; calls `send` internally (non-proxy). |
| Safe | `0x4DFF9b5b0143E642a3F63a5bcf2d1C328e600bf8` | Same literal as ETH. |
| LayerZero EndpointV2 | `0x1a44076050125825900e736c501f859c50fe728c` | |

---

## 5. Addresses — Optimism (chain ID 10)

Verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`. LZ EID **30111**. OFT `token()` = the TetherTokenOFTExtension Token proxy; `approvalRequired()` = `false`.

| Role | Address | One-liner |
|------|---------|-----------|
| **OFT** (proxy) | `0xF03b4d9AC1D5d1E7c4cEf54C2A313b9fe051A0aD` | `OUpgradeable`. Burns/mints the Token. |
| OFT impl | `0xe549d79883d8d242c5efbe30c26aa2371c67a023` | `OUpgradeable` implementation. |
| OFT ProxyAdmin | `0xa882c21C9df00958A958cde96f2B2Ae8FB4315B1` | (same literal as ARB OFT ProxyAdmin). |
| **Token** (proxy, `USD₮0`) | `0x01bFF41798a0BcF287b996046Ca68b395DbC1071` | `TetherTokenOFTExtension`; ERC-7802; `symbol()="USD₮0"`, 6-dec. |
| Token impl | `0xb8ce59fc3717ada4c02eadf9682a9e934f625ebb` | `TetherTokenOFTExtension` implementation. |
| Token ProxyAdmin | `0xe7cd86e13AC4309349F30B3435a9d337750fC82D` | |
| Safe | `0x4DFF9b5b0143E642a3F63a5bcf2d1C328e600bf8` | Same literal as ETH. |
| LayerZero EndpointV2 | `0x1a44076050125825900e736c501f859c50fe728c` | |

---

## 6. Addresses — Polygon PoS (chain ID 137)

Verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com`. LZ EID **30109**. **Polygon differs from ARB/OP**: USDT0's OFT wraps the **pre-existing PoS-bridged native USD₮** rather than a freshly USDT0-deployed token. `token()` = native USD₮; `approvalRequired()` = `false` (burn/mint OFT); `peers(30101)` = the ETH adapter; the ETH adapter's `peers(30109)` = this OFT. As of 2026-06-09 the Polygon OFT had **0 `OFTSent` over 100k blocks** (recently wired / low usage) — present and peered but lightly used.

| Role | Address | One-liner |
|------|---------|-----------|
| **OFT** (proxy) | `0x6BA10300f0DC58B7a1e4c0e41f5daBb7D7829e13` | `OUpgradeable`. Inner token = native USD₮. |
| OFT impl | `0x8412d6553a2bd1b547bc48b86c3c5d897122ae47` | `OUpgradeable` implementation (distinct impl address from ARB/OP, same build). |
| OFT ProxyAdmin | `0xa882c21C9df00958A958cde96f2B2Ae8FB4315B1` | (admin slot of OFT proxy; same literal as ARB/OP). |
| native **USD₮** (inner token) | `0xc2132D05D31c914a87C6611C10748AEb04B58e8F` | Pre-existing Polygon PoS-bridged Tether USD₮, 6-dec. **Not a USDT0-deployed token.** |
| Safe | `0x4DFF9b5b0143E642a3F63a5bcf2d1C328e600bf8` | Same literal as ETH. |
| LayerZero EndpointV2 | `0x1a44076050125825900e736c501f859c50fe728c` | |

> There is **no separate USDT0 Token proxy on Polygon** — like Ethereum, the OFT wraps the chain's native USD₮. So a "USDT0 Token contract" only exists on ARB/OP (and the other non-Polygon non-ETH chains).

---

## 7. Chains NOT among the 7 (counterparty footprint — recorded findings)

USDT0 is live on **~23 networks**; the majority are **outside the 7 requested**. The lockbox on Ethereum peers to all of them. Counterparty chains (EID, inner-token model):

- **Outside-7 with USDT0 Token+OFT:** Ink (57073, EID 30339), Berachain (80094, 30362), Unichain (130, 30320), Sei (1329, 30280), HyperEVM (999, 30367, + HyperCore Composer + HyperCore non-EVM), Rootstock (30, 30333), Flare (14, 30295), Corn (21000000, 30331), Conflux eSpace (1030, 30212), Mantle (5000, 30181), Morph (2818, 30322), XLayer (196, 30274), Hedera (295, 30316), Plasma (9745, 30383), Stable (988, 30396), MegaETH (4326, 30398), Monad (143, 30390), Tempo (4217, 30410, + `TempoOFTWrapper`).
- **Non-EVM:** HyperCore (Hyperliquid L1) via the HyperCore Composer `0x80123Ab57c9bc0C452d6c18F92A653a4ee2e7585` on HyperEVM.

These are **counterparty endpoints, not omissions** — the `OFTSent.dstEid` / `OFTReceived.srcEid` on the 4 in-scope chains will frequently reference these EIDs.

---

## 8. Cross-chain summary

| Chain | ID | LZ EID | OFT / Adapter | Token (USD₮) | model | Composer | present? |
|---|---|---|---|---|---|---|---|
| **Ethereum** | 1 | 30101 | `0x6C96dE32…41dee` (Adapter) | *(native USD₮ `0xdAC17F…`)* | **lockbox** (`approvalRequired=true`) | — | ✅ |
| **Arbitrum One** | 42161 | 30110 | `0x14E4A1B1…98D92` | `0xFd086bC7…Cbb9` (ArbitrumExtensionV2) | burn/mint, gateway | MultiHop `0x759BA420…` | ✅ |
| **Optimism** | 10 | 30111 | `0xF03b4d9A…A0aD` | `0x01bFF417…1071` (TetherTokenOFTExtension) | burn/mint, ERC-7802 | — | ✅ |
| **Polygon PoS** | 137 | 30109 | `0x6BA10300…9e13` | *(native USD₮ `0xc2132D05…`)* | burn/mint over native | — | ✅ (lightly used) |
| Base | 8453 | — | — | — | — | — | ❌ `0x` |
| BNB Smart Chain | 56 | — | — | — | — | — | ❌ `0x` |
| Avalanche C-Chain | 43114 | — | — | — | — | — | ❌ `0x` |

**Tells:** the **Safe `0x4DFF9b5b…00bf8` is the same literal on all 4 present chains**, as is the **LZ EndpointV2 `0x1a44…728c`** and the **OFT ProxyAdmin `0xa882c21C…15B1`** (ARB/OP/Polygon). The **OFT proxy addresses are per-chain (not deterministic)**, so a USDT0 address on one chain returns `0x` on another — confirmed by checking the OP/Polygon OFT addresses on Base/BNB/Avax (all `0x`). Avoid keying on address alone — key on `(chainId, address)`.

---

## 9. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **OFT Adapter** (ETH) | **EIP-1967 Transparent** | proxy ~2,739 B; impl slot `0x3608…2bbc` = `0xcd979b10…`; admin slot `0xb531…6103` = ProxyAdmin `0x4de7096B…`. | ProxyAdmin `0x4de7096B…` (owned by Safe). |
| **OFT** (ARB/OP/Polygon) | **EIP-1967 Transparent** | proxy ~2,739 B; impl slot set (ARB `0x00678fda…`, OP `0xe549d798…`, POL `0x8412d655…`); admin slot = `0xa882c21C…` (ARB/OP/POL). | ProxyAdmin `0xa882c21C…` (owned by Safe). |
| **Token** (ARB) | **EIP-1967 Transparent** | proxy ~2,141 B; impl slot = `0x3263cd78…`; admin = `0x553ec478…`. | ProxyAdmin `0x553ec478…`. |
| **Token** (OP) | **EIP-1967 Transparent** | proxy ~2,227 B; impl slot = `0xb8ce59fc…`; admin = `0xe7cd86e1…`. | ProxyAdmin `0xe7cd86e1…`. |
| **ProxyAdmin** (all) | **non-proxy** (OZ ProxyAdmin) | full contract; no impl slot. | Safe `0x4DFF…00bf8`. |
| **Safe** (all chains) | Gnosis Safe proxy (171 B) | tiny proxy delegating to the Safe singleton. | Safe owners (multisig). |
| **MultiHop Composer** (ARB) | **non-proxy** | 9,403-byte contract; no impl slot. | — (immutable). |
| native USD₮ (ETH/Polygon) | not a USDT0 contract | — | Tether. |

EIP-1967 slots: **impl** `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`, **admin** `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. All USDT0 proxies are **Transparent (admin slot populated)** — none is UUPS, none is a Beacon (beacon slot `0xa3f0ad74…3d50` empty), none is a Diamond. **Watch `Upgraded(address)` topic0 `0xbc7cd75a…2d3b`** on every OFT/Token proxy. To read the live impl: `eth_getStorageAt(proxy, 0x3608…2bbc)` — never hard-code an impl (they rotate).

---

## 10. Detection invariants & gotchas

1. **Two contracts per non-lockbox chain.** `OFTSent`/`OFTReceived` fire on the **OFT** (`0x14E4A1…`, `0xF03b4d…`, `0x6BA1…`); `Transfer`/`Mint`/`Burn`/`Crosschain*` fire on the **Token** (`0xFd086b…`, `0x01bFF4…`). They are *different addresses*. On Ethereum and Polygon there is no separate USDT0 Token — the inner token is the chain's **native USD₮**.
2. **`OFTSent.guid == OFTReceived.guid` is the cross-chain join key.** Match a send on one chain to a receive on another by `guid`, not by amount/timestamp. `srcEid`/`dstEid` are **LayerZero EIDs** (ETH 30101, ARB 30110, OP 30111, Polygon 30109), **not chain IDs**.
3. **`fromAddress`/`toAddress` in the OFT events are the real user.** `tx.from` is usually the LayerZero Executor/relayer. Attribute volume to the event fields.
4. **The OP token triple-logs each leg:** `CrosschainMint` + `Mint` + zero-address `Transfer` (receive), or `CrosschainBurn` + `Burn` + zero-address `Transfer` (send). Pick **one** event family to count, or you triple-count. `CrosschainMint`/`CrosschainBurn` carry the `sender` (the OFT) as a third indexed field — the cleanest bridge signal.
5. **Arbitrum's token has NO Mint/Burn/Crosschain events** — only `Transfer`. Detect ARB mint/burn by **zero-address `Transfer`** on `0xFd086b…`, or by the OFT's `OFTSent`/`OFTReceived`. Its mint/burn entrypoints are `bridgeMint`/`bridgeBurn` (Arbitrum-gateway naming), distinct from OP's `crosschainMint`/`crosschainBurn`.
6. **`approvalRequired()` tells you the model:** `true` (Ethereum) = lockbox, the adapter holds real USD₮ and the actual money movement is a `Transfer` on `0xdAC17F…` (USDT), not on the adapter. `false` (ARB/OP/Polygon) = burn/mint. The Ethereum adapter itself emits only `OFTSent`/`OFTReceived` — no token movement appears on the adapter address.
7. **The USDT0 tokens are NOT the legacy `TetherToken`.** `addBlackList`/`destroyBlackFunds`/`issue`/`pause`/`deprecate` selectors are **absent** from both token impls — don't scan for them. (The *native* USD₮ on ETH/Polygon does have them, but that's the inner collateral, a separate contract.)
8. **Polygon is the odd one of the four:** burn/mint OFT (`approvalRequired=false`) but wrapping the **pre-existing PoS-bridged native USD₮** (`0xc2132D05…`), not a USDT0-deployed token, and **near-zero activity** (0 `OFTSent` in 100k blocks as of 2026-06-09). Treat Polygon volume as nascent.
9. **NOT on Base, BNB, or Avalanche.** Every USDT0 address returns `0x` there (confirmed against the ETH adapter address and the OP/Polygon OFT addresses). USDT on those chains is plain bridged/native USDT, not USDT0.
10. **LayerZero `PacketSent`/`PacketDelivered` are emitted by the shared Endpoint `0x1a44…728c`**, used by *every* OFT on the chain. Filter by the USDT0 OFT as sender/receiver; never key on those topic0s alone.
11. **Most counterparties are outside the 7** (Ink, Berachain, Unichain, Sei, HyperEVM/HyperCore, Plasma, Stable, Tempo, …). An `OFTReceived` on Arbitrum with `srcEid=30339` is an Ink→Arbitrum hop — expected, not anomalous.
12. **The `MultiHop Composer` (`0x759BA420…`, Arbitrum) chains hops in one LZ message** via `lzCompose`/`send`. A single user action can produce an OFT receive **and** a re-`send` on the same chain — don't double-count the intermediate hop as net flow.
13. **Governance = the Safe `0x4DFF…00bf8`** (owns every ProxyAdmin, is every OFT `owner()` and LZ delegate). Watch `Upgraded`, `PeerSet`, `EnforcedOptionSet`, `OwnershipTransferred`, and ProxyAdmin `upgrade`/`upgradeAndCall` as the privileged-action surface.

---

## 11. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- OFT / OFT Adapter
TOPIC_OFT_SENT              = '\x85496b760a4b7f8d66384b9df21b381f5d1b1e79f229a47aaf4c232edc2fe59a'
TOPIC_OFT_RECEIVED          = '\xefed6d3500546b29533b128a29e3a94d70788727f0507505ac12eaf2e578fd9c'
TOPIC_PEER_SET              = '\x238399d427b947898edb290f5ff0f9109849b1c3ba196a42e35f00c50a54b98b'
TOPIC_ENFORCED_OPTION_SET   = '\xbe4864a8e820971c0247f5992e2da559595f7bf076a21cb5928d443d2a13b674'
TOPIC_MSG_INSPECTOR_SET     = '\xf0be4f1e87349231d80c36b33f9e8639658eeaf474014dee15a3e6a4d4414197'
TOPIC_PRECRIME_SET          = '\xd48d879cef83a1c0bdda516f27b13ddb1b3f8bbac1c9e1511bb2a659c2427760'
-- Token (TetherTokenOFTExtension / ArbitrumExtensionV2)
TOPIC_TRANSFER              = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_APPROVAL              = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
TOPIC_MINT                  = '\x0f6798a560793a54c3bcfe86a93cde1e73087d944c0ea20544137d4121396885'  -- Mint(address,uint256)
TOPIC_BURN                  = '\xcc16f5dbb4873280815c1ee09dbd06736cffcc184412cf7a71a0fdb75d397ca5'  -- Burn(address,uint256)
TOPIC_CROSSCHAIN_MINT       = '\xde22baff038e3a3e08407cbdf617deed74e869a7ba517df611e33131c6e6ea04'  -- ERC-7802
TOPIC_CROSSCHAIN_BURN       = '\xb90795a66650155983e242cac3e1ac1a4dc26f8ed2987f3ce416a34e00111fd4'  -- ERC-7802
-- Proxy / upgrade
TOPIC_UPGRADED              = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ADMIN_CHANGED         = '\x7e644d79422f17c01e4894b5f4f588d331ebfa28653d42ae832dc59e38c9798f'
TOPIC_OWNERSHIP_TRANSFERRED = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
-- LayerZero EndpointV2 (transport; shared across all OFTs)
TOPIC_LZ_PACKET_SENT        = '\x1ab700d4ced0c005b164c0f789fd09fcbb0156d4c2041b8a3bfbcd961cd1567f'
TOPIC_LZ_PACKET_DELIVERED   = '\x3cd5e48f9730b129dc7550f0fcea9c767b7be37837cd10e55eb35f734f4bca04'
TOPIC_LZ_PACKET_VERIFIED    = '\x0d87345f3d1c929caba93e1c3821b54ff3512e12b66aa3cfe54b6bcbc17e59b4'

-- ===== Selectors =====
-- OFT
SEL_SEND                    = '\xc7c7f5b3'  -- send((uint32,bytes32,uint256,uint256,bytes,bytes,bytes),(uint256,uint256),address)
SEL_QUOTE_SEND              = '\x3b6f743b'
SEL_QUOTE_OFT               = '\x0d35b415'
SEL_LZ_RECEIVE              = '\x13137d65'
SEL_SET_PEER                = '\x3400288b'
SEL_SET_ENFORCED_OPTIONS    = '\xb98bd070'
SEL_SET_DELEGATE            = '\xca5eb5e1'
SEL_TOKEN                   = '\xfc0c546a'
SEL_APPROVAL_REQUIRED       = '\x9f68b964'
SEL_SHARED_DECIMALS         = '\x857749b0'
SEL_PEERS                   = '\xbb0b6a53'
-- Token
SEL_CROSSCHAIN_MINT         = '\x18bf5077'  -- TetherTokenOFTExtension
SEL_CROSSCHAIN_BURN         = '\x2b8c49e3'  -- TetherTokenOFTExtension
SEL_BRIDGE_MINT             = '\x8c2a993e'  -- ArbitrumExtensionV2
SEL_BRIDGE_BURN             = '\x74f4f547'  -- ArbitrumExtensionV2
SEL_MINT                    = '\x40c10f19'  -- mint(address,uint256)
SEL_REDEEM                  = '\xdb006a75'  -- redeem(uint256)
SEL_L1_ADDRESS              = '\xc2eeeebd'  -- ArbitrumExtensionV2
-- ProxyAdmin
SEL_PROXY_UPGRADE           = '\x99a88ec4'
SEL_PROXY_UPGRADE_AND_CALL  = '\x9623609d'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT           = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT          = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Shared across present chains =====
USDT0_SAFE                  = '\x4dff9b5b0143e642a3f63a5bcf2d1c328e600bf8'  -- ETH/ARB/OP/Polygon (key on chainId,addr)
LZ_ENDPOINT_V2              = '\x1a44076050125825900e736c501f859c50fe728c'  -- all 4 present chains
OFT_PROXYADMIN_SHARED       = '\xa882c21c9df00958a958cde96f2b2ae8fb4315b1'  -- ARB/OP/Polygon OFT ProxyAdmin

-- ===== Ethereum (chain ID 1, EID 30101) — lockbox =====
ETH_OFT_ADAPTER             = '\x6c96de32cea08842dcc4058c14d3aaad7fa41dee'   -- impl 0xcd979b10…
ETH_OFT_ADAPTER_IMPL        = '\xcd979b10a55fcdac23ec785ce3066c6ef8a479a4'
ETH_OFT_PROXYADMIN          = '\x4de7096b2131e84fd6b2042ad8cd9b4e43f728fc'
ETH_USDT_INNER              = '\xdac17f958d2ee523a2206206994597c13d831ec7'   -- native USD₮ (collateral)

-- ===== Arbitrum One (chain ID 42161, EID 30110) =====
ARB_OFT                     = '\x14e4a1b13bf7f943c8ff7c51fb60fa964a298d92'   -- impl 0x00678fda…
ARB_OFT_IMPL                = '\x00678fdaab0d5c91b843a22fa38e08af1bbda85e'
ARB_TOKEN                   = '\xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9'   -- ArbitrumExtensionV2; impl 0x3263cd78…
ARB_TOKEN_IMPL              = '\x3263cd783823d04a6b9819517e0e6840d37ca3f4'
ARB_TOKEN_PROXYADMIN        = '\x553ec478a66be27ba25a6bc5db20aec2ed6a1b4a'
ARB_MULTIHOP_COMPOSER       = '\x759ba420bf1ded1765f18c2dc3fc57a1964a2ad1'

-- ===== Optimism (chain ID 10, EID 30111) =====
OP_OFT                      = '\xf03b4d9ac1d5d1e7c4cef54c2a313b9fe051a0ad'   -- impl 0xe549d798…
OP_OFT_IMPL                 = '\xe549d79883d8d242c5efbe30c26aa2371c67a023'
OP_TOKEN                    = '\x01bff41798a0bcf287b996046ca68b395dbc1071'   -- TetherTokenOFTExtension; impl 0xb8ce59fc…
OP_TOKEN_IMPL               = '\xb8ce59fc3717ada4c02eadf9682a9e934f625ebb'
OP_TOKEN_PROXYADMIN         = '\xe7cd86e13ac4309349f30b3435a9d337750fc82d'

-- ===== Polygon PoS (chain ID 137, EID 30109) =====
POL_OFT                     = '\x6ba10300f0dc58b7a1e4c0e41f5dabb7d7829e13'   -- impl 0x8412d655…
POL_OFT_IMPL                = '\x8412d6553a2bd1b547bc48b86c3c5d897122ae47'
POL_USDT_INNER              = '\xc2132d05d31c914a87c6611c10748aeb04b58e8f'   -- native PoS USD₮ (inner token)

-- ===== NOT deployed (eth_getCode = 0x) =====
-- Base (8453), BNB Smart Chain (56), Avalanche C-Chain (43114): no USDT0 contracts.
```

---

## 12. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]`. `OFTSent`/`OFTReceived` cross-checked against **live `eth_getLogs`** — Ethereum adapter `0x6C96dE…` (252 `OFTSent` + 167 `OFTReceived` in a 7k-block window) and Arbitrum OFT `0x14E4A1…` (live `OFTSent`/`OFTReceived`). `Transfer`/`Approval`/`Mint`/`Burn`/`CrosschainMint`/`CrosschainBurn` cross-checked against the Optimism token `0x01bFF4…` (370 `Transfer`, 58 `Approval`, 5 `Mint`, 5 `CrosschainMint`, 1 `Burn`, 1 `CrosschainBurn` in a 5k-block window). All selectors existence-checked by PUSH4 (`63<sel>`) scan of live impl bytecode; event topics by PUSH32 (`7f<topic>`) scan.
- **Addresses:** parsed from the official docs (`docs.usdt0.to/technical-documentation/deployments`) and the canonical `Everdawn-Labs/usdt0-audit-reports/DEPLOYMENTS.md`, then existence-checked via `eth_getCode` (non-empty) on each chain's publicnode RPC. **Base / BNB / Avalanche** returned `0x` for the ETH adapter and the OP/Polygon OFT addresses → not deployed.
- **Wiring (`eth_call`):** adapter/OFT `token()`, `approvalRequired()` (ETH=`true`, ARB/OP/Polygon=`false`), `sharedDecimals()`=6, `decimalConversionRate()`=1, `oftVersion()`=`(0x02e49c2c,1)`, `endpoint()`=`0x1a44…728c`, `owner()`=Safe; USDT0 token `symbol()`=`name()`="USD₮0", `decimals()`=6; `peers()` cross-checked both ways (ETH `peers(30110)`=ARB OFT, `peers(30109)`=Polygon OFT; Polygon `peers(30101)`=ETH adapter).
- **Proxy impls:** read live from the EIP-1967 impl/admin slots (`eth_getStorageAt`) — all proxies are **Transparent** (admin slot populated). Impl addresses match the audit's documented `OAdapterUpgradeable` / `OUpgradeable` / `TetherTokenOFTExtension` / `ArbitrumExtensionV2`.
- **Token surface:** PUSH4 scan confirmed `TetherTokenOFTExtension` exposes ERC-7802 `crosschainMint`/`crosschainBurn`; `ArbitrumExtensionV2` exposes Arbitrum-gateway `bridgeMint`/`bridgeBurn` + `l1Address()`; **neither** exposes legacy Tether `addBlackList`/`destroyBlackFunds`/`issue`/`pause`/`deprecate`.

Authoritative sources:
- USDT0 docs — [Deployments](https://docs.usdt0.to/technical-documentation/deployments) · [Developer Guide](https://docs.usdt0.to/technical-documentation/developer/) · [docs home](https://docs.usdt0.to/)
- Canonical repos — [`Everdawn-Labs/usdt0-audit-reports` (DEPLOYMENTS.md)](https://github.com/Everdawn-Labs/usdt0-audit-reports/blob/main/DEPLOYMENTS.md) · `Everdawn-Labs/usdt0-oft-contracts` · `Everdawn-Labs/usdt0-tether-contracts-hardhat`
- Audit — [OpenZeppelin USDT0 audit](https://www.openzeppelin.com/news/usdt0-audit) · [ERC-7802 upgrade audit](https://www.openzeppelin.com/news/everdawn-usdt0-erc-7802-upgrade-audit)
- LayerZero — [OFT standard](https://docs.layerzero.network/v2/home/token-standards/oft-standard) · EndpointV2 `0x1a44076050125825900e736c501f859c50fe728c`
- Explorers: [Etherscan adapter](https://etherscan.io/address/0x6C96dE32CEa08842dcc4058c14d3aaAD7Fa41dee) · [Arbiscan OFT](https://arbiscan.io/address/0x14E4A1B13bf7F943c8ff7C51fb60FA964A298D92) · [Optimistic Etherscan token](https://optimistic.etherscan.io/address/0x01bFF41798a0BcF287b996046Ca68b395DbC1071) · [Polygonscan OFT](https://polygonscan.com/address/0x6BA10300f0DC58B7a1e4c0e41f5daBb7D7829e13)
