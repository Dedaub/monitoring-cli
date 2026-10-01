# Wormhole NFT Bridge — Topics, Selectors, Addresses (Ethereum, Base, Arbitrum, Optimism, Polygon, BNB, Avalanche; NOT Robinhood Chain)

**Status:** verified on 2026-09-29 against live RPC on all eight chains, the canonical `wormhole-foundation/wormhole` repo (`ethereum/contracts/nft/`) and `core/base/src/constants/contracts/nftBridge.ts` of `wormhole-foundation/wormhole-sdk-ts`. Topics and selectors recomputed as `keccak256(signature)`; addresses existence-checked with `eth_getCode`; implementations read from the EIP-1967 slot.
**Scope:** the Wormhole **NFT Bridge** (ERC-721 lock-and-mint over Wormhole messages) and its wrapped NFT contracts. It is deployed on **seven of the eight target chains; Robinhood Chain (4663) has none**. Topics and selectors are chain-agnostic; addresses are network-specific. The NFT Bridge is not on the current docs contract-address page; the SDK constants are its address source.

The NFT Bridge follows the Token Bridge model for ERC-721 tokens. An NFT keeps its origin chain. On the origin chain the bridge **locks** the NFT; on other chains it **mints** a wrapped NFT (`BridgeNFT` beacon proxy, created on the first redemption of a collection). Sending a wrapped NFT back **burns** it.

- **Source leg:** `transferNFT`. The bridge pulls the NFT (`safeTransferFrom` user → bridge), burns it if it is wrapped, and publishes a message. **The only source event is the Core's `LogMessagePublished` with `sender` = the NFT Bridge.**
- **Destination leg:** `completeTransfer`. **The NFT Bridge emits no event of its own on redemption.** The only destination logs are the ERC-721 `Transfer` (bridge → recipient for an origin NFT, `0x0` → recipient for a wrapped mint).
- **Refund, cancel, expiry:** none. A VAA never expires.

**Link key:** `(emitterChain, emitterAddress, sequence)` is on chain only on the source (`LogMessagePublished`). The destination transaction has no log with the key: join it by the `completeTransfer(bytes)` call input (the VAA carries the key), or by `(tokenAddress, tokenChain, tokenID, to)` from the payload against the ERC-721 `Transfer` on the destination.

---

## 0. Contract families

| Contract | Chains | Role | Proxy? |
|----------|--------|------|--------|
| **NFT Bridge** (`NFTBridgeEntrypoint` proxy + `NFTBridgeImplementation`) | ETH, Base, ARB, OP, POLY, BNB, AVAX | Lock / burn on send, release / mint on redeem, wrapped-collection registry. | EIP-1967 proxy, upgraded by governance VAA (`upgrade`) |
| **Wrapped NFT** (`BridgeNFT` → `NFTImplementation`) | every NFT Bridge chain | One ERC-721 per foreign collection; `mint` / `burn` are `onlyOwner` = NFT Bridge. | Beacon proxy; beacon = the NFT Bridge |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

| topic0 | Event |
|--------|-------|
| `0x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2` | `LogMessagePublished(address indexed sender, uint64 sequence, uint32 nonce, bytes payload, uint8 consistencyLevel)` — emitter = Core; **source leg when `sender` = NFT Bridge** |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 indexed tokenId)` — ERC-721 (3 indexed topics, empty data); same topic0 as ERC-20 `Transfer`. **The only destination log.** |
| `0x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49` | `ContractUpgraded(address indexed oldContract, address indexed newContract)` — admin; present in every live implementation; same topic0 as Core and Token Bridge |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — admin; emitted with `ContractUpgraded` |

**Payload of an NFT transfer** (inside `LogMessagePublished.payload`; payload starts at data byte 160): `payloadID` = 1 (byte 0), `tokenAddress` (1–32), `tokenChain` (33–34), `symbol` (35–66), `name` (67–98), `tokenID` (99–130), URI length (131), `uri` (up to 200 bytes), then `to` (bytes32) and `toChain` (uint16) as the last 34 bytes. Parse `to` and `toChain` from the end, as the contract does.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xc96616e1` | `transferNFT(address token, uint256 tokenID, uint16 recipientChain, bytes32 recipient, uint32 nonce)` | Payable (Core fee, 0 today). Source leg. Present in every live implementation. |
| `0xc6878519` | `completeTransfer(bytes encodedVm)` | Destination leg; creates the wrapped collection on first use. **No NFT Bridge event** — watch this selector. Same selector as the Token Bridge's `completeTransfer`; key by `tx.to`. |
| `0xa5799f93` | `registerChain(bytes encodedVM)` | Governance VAA. No event. |
| `0x25394645` | `upgrade(bytes encodedVM)` | Governance VAA; emits `Upgraded` + `ContractUpgraded`. **Admin.** |
| `0x178149e7` | `submitRecoverChainId(bytes encodedVM)` | Fork recovery only. |
| `0x1ff1e286` | `wrappedAsset(uint16 tokenChainId, bytes32 tokenAddress)` | View. |
| `0xad66a5f1` | `bridgeContracts(uint16 chainId_)` | View — registered peer. |
| `0xaa4efa5b` | `isTransferCompleted(bytes32 hash)` | View — replay guard. |
| `0x2f3a3d5d` | `tokenImplementation()` | View — wrapped-NFT implementation. |
| `0x3ca64826` | `splCache(uint256 tokenId)` | View — cached name / symbol of Solana-origin NFTs. |
| `0x150b7a02` | `onERC721Received(address operator, address from, uint256 tokenId, bytes data)` | ERC-721 receiver hook. |
| `0xd3fc9864` | `mint(address to, uint256 tokenId, string uri)` | Wrapped NFT; `onlyOwner` (NFT Bridge). |
| `0x42966c68` | `burn(uint256 tokenId)` | Wrapped NFT; `onlyOwner`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

| Role | Address | One-liner |
|------|---------|-----------|
| **NFT Bridge** (proxy) | `0x6FFd7EdE62328b3Af38FCD61461Bbfc52F5651fE` | 680 B proxy; implementation `0x3e41904b3766f4cceb145cc53d75feb61722a96c` (17,049 B); `chainId()` = 2; `wormhole()` = Core `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B`. |

---

## 4. Addresses — the other six NFT Bridge chains

| Chain | EVM id | Wormhole id | NFT Bridge (proxy) | Proxy size | Live implementation |
|-------|--------|-------------|--------------------|-----------|---------------------|
| Ethereum | 1 | 2 | `0x6FFd7EdE62328b3Af38FCD61461Bbfc52F5651fE` | 680 B | `0x3e41904b3766f4cceb145cc53d75feb61722a96c` (17,049 B) |
| Base | 8453 | 30 | `0xDA3adC6621B2677BEf9aD26598e6939CF0D92f88` | 680 B | `0xa1915f66b5d6761a0e999f14ec29a0c4f886f574` (17,055 B) |
| Arbitrum One | 42161 | 23 | `0x3dD14D553cFD986EAC8e3bddF629d82073e188c8` | 680 B | `0x92984f4023f2b40d5b70980f383860492f02019e` (17,049 B) |
| Optimism | 10 | 24 | `0xfE8cD454b4A1CA468B57D79c0cc77Ef5B6f64585` | 680 B | `0x0b3e006a6af5126e625c0e228adf31ea494246a3` (17,049 B) |
| Polygon PoS | 137 | 5 | `0x90BBd86a6Fe93D3bc3ed6335935447E75fAb7fCf` | 729 B | `0x5c7c40c4b976aee76d829fbc922720a9621536ef` (15,725 B) |
| BNB Smart Chain | 56 | 4 | `0x5a58505a96D1dbf8dF91cB21B54419FC36e93fdE` | 729 B | `0x67965a59631e8eacda48d26fae769e516fa0bcfc` (15,725 B) |
| Avalanche C-Chain | 43114 | 6 | `0xf7B6737Ca9c4e08aE573F75A97B73D7a813f5De5` | 680 B | `0x39ac31949dd65e6ed5154442c7e7b0a75c451931` (15,725 B) |

`chainId()` and `wormhole()` returned the local Wormhole id and Core on all seven chains. Every implementation read contains `ContractUpgraded`, `transferNFT` and `completeTransfer`.

**Robinhood Chain (4663):** no NFT Bridge. No entry in `nftBridge.ts`; `eth_getCode` = `0x` at the Ethereum NFT Bridge address.

---

## 5. Cross-chain summary

| Chain | EVM id | Wormhole id | NFT Bridge | NFT messages in the window |
|-------|--------|-------------|------------|----------------------------|
| Ethereum | 1 | 2 | `0x6FFd7EdE62328b3Af38FCD61461Bbfc52F5651fE` | 0 |
| Base | 8453 | 30 | `0xDA3adC6621B2677BEf9aD26598e6939CF0D92f88` | 0 |
| Arbitrum One | 42161 | 23 | `0x3dD14D553cFD986EAC8e3bddF629d82073e188c8` | 0 |
| Optimism | 10 | 24 | `0xfE8cD454b4A1CA468B57D79c0cc77Ef5B6f64585` | 0 |
| Polygon PoS | 137 | 5 | `0x90BBd86a6Fe93D3bc3ed6335935447E75fAb7fCf` | not measured (sender split unavailable) |
| BNB Smart Chain | 56 | 4 | `0x5a58505a96D1dbf8dF91cB21B54419FC36e93fdE` | 0 |
| Avalanche C-Chain | 43114 | 6 | `0xf7B6737Ca9c4e08aE573F75A97B73D7a813f5De5` | 0 |
| **Robinhood Chain** | 4663 | 72 | ❌ `0x` | — |

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **NFT Bridge** (7 chains) | EIP-1967 proxy (`NFTBridgeEntrypoint is ERC1967Proxy`); upgrade logic in `NFTBridgeGovernance` | Implementation slot populated (§4); two proxy builds (680 B and 729 B) | Guardian governance VAA `upgrade(bytes)`, emitter chain 1, emitter `0x0000000000000000000000000000000000000000000000000000000000000004` |
| **Wrapped NFT** | `BeaconProxy`, beacon = the NFT Bridge | A bridge upgrade that changes `tokenImplementation()` upgrades every wrapped collection | Same |

---

## 7. Detection invariants & gotchas

1. **No NFT Bridge event on redemption.** A monitor must key the destination on the ERC-721 `Transfer` (from the bridge, or from `0x0` at a wrapped collection) or on the `completeTransfer(bytes)` call to the NFT Bridge.
2. **`Transfer` topic0 collides with ERC-20.** ERC-721 `Transfer` has 4 topics (tokenId in `topic3`) and empty data; ERC-20 `Transfer` has 3 topics and 32 bytes of data.
3. **Address reuse across chains.** `0x5a58505a96D1dbf8dF91cB21B54419FC36e93fdE` is the **NFT Bridge on BNB** and the **Token Bridge on Polygon** (measured: 15,725 B NFT implementation on BNB, 23,716 B Token Bridge implementation on Polygon). Key on `(chain, address)`.
4. **Low activity.** No `LogMessagePublished` with `sender` = NFT Bridge was seen on six chains in the pinned window. The bridge is deployed and upgradeable, so watch `ContractUpgraded` on it.
5. **URI cap:** `encodeTransfer` rejects a `tokenURI` longer than 200 bytes, so some NFTs cannot be bridged.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_LOG_MESSAGE_PUBLISHED   = '\x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2'   -- emitter = Core; topic1 = NFT Bridge
TOPIC_TRANSFER                = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'   -- ERC-721: 4 topics
TOPIC_CONTRACT_UPGRADED       = '\x2e4cc16c100f0b55e2df82ab0b1a7e294aa9cbd01b48fbaf622683fbc0507a49'

-- ===== Selectors =====
SEL_TRANSFER_NFT              = '\xc96616e1'
SEL_COMPLETE_TRANSFER         = '\xc6878519'
SEL_NFT_UPGRADE               = '\x25394645'
SEL_NFT_REGISTER_CHAIN        = '\xa5799f93'

-- ===== NFT Bridge per chain =====
ETH_NFT_BRIDGE                = '\x6ffd7ede62328b3af38fcd61461bbfc52f5651fe'
BASE_NFT_BRIDGE               = '\xda3adc6621b2677bef9ad26598e6939cf0d92f88'
ARB_NFT_BRIDGE                = '\x3dd14d553cfd986eac8e3bddf629d82073e188c8'
OP_NFT_BRIDGE                 = '\xfe8cd454b4a1ca468b57d79c0cc77ef5b6f64585'
POLY_NFT_BRIDGE               = '\x90bbd86a6fe93d3bc3ed6335935447e75fab7fcf'
BNB_NFT_BRIDGE                = '\x5a58505a96d1dbf8df91cb21b54419fc36e93fde'
AVAX_NFT_BRIDGE               = '\xf7b6737ca9c4e08ae573f75a97b73d7a813f5de5'
-- Robinhood (4663): no NFT Bridge
```

---

## 9. Verification & sources

How every constant was verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` from `ethereum/contracts/nft/NFTBridge.sol`, `NFTBridgeGovernance.sol`, `NFTBridgeGetters.sol` and `token/NFTImplementation.sol`. Each live implementation was scanned for `ContractUpgraded` (`PUSH32`) and for `transferNFT` / `completeTransfer` (`PUSH4`).
- **Addresses:** from `nftBridge.ts` of the SDK (the docs contract-address page no longer lists the NFT Bridge); existence-checked with `eth_getCode`; implementations from the EIP-1967 slot; `chainId()` and `wormhole()` read live.
- **Activity (pinned 12-hour window 2026-09-28 00:00–12:00 UTC):** `LogMessagePublished` with `sender` = NFT Bridge: 0 on Ethereum, Base, Arbitrum, Optimism, BNB and Avalanche. Polygon: the sender split was not measured, because the Polygon log endpoint failed on the per-sender query. No sample transaction exists in the window, so the value movement above is from source.

Authoritative sources:
- [wormhole-foundation/wormhole](https://github.com/wormhole-foundation/wormhole) — `ethereum/contracts/nft/`
- [wormhole-foundation/wormhole-sdk-ts](https://github.com/wormhole-foundation/wormhole-sdk-ts) — `core/base/src/constants/contracts/nftBridge.ts`
- Explorers — [Etherscan NFT Bridge](https://etherscan.io/address/0x6ffd7ede62328b3af38fcd61461bbfc52f5651fe) · [BscScan NFT Bridge](https://bscscan.com/address/0x5a58505a96d1dbf8df91cb21b54419fc36e93fde)
