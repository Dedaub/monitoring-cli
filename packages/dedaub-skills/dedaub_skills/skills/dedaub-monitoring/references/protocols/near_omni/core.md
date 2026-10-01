# NEAR Omni Bridge — Topics, Selectors, Addresses (Ethereum + Base + Arbitrum + Polygon + BNB)

**Status:** verified on 2026-09-29 against Ethereum, Base, Arbitrum, Polygon and BNB RPC (`eth_getCode`, `eth_call`, EIP-1967 slot, `eth_getLogs`), `eth_getCode` on Optimism, Avalanche and Robinhood Chain, the `Near-One/omni-bridge` repository (README address list, `evm/src/omni-bridge/contracts`, the OpenZeppelin upgrade manifests, `near/omni-types/src/lib.rs`), and Sourcify.
**Scope:** the EVM contracts of the NEAR Omni Bridge, the successor of the legacy Rainbow Bridge (the legacy contracts are in the `rainbow` doc): one `OmniBridge` UUPS proxy per chain (`OmniBridgeWormhole` on the L2s and BNB), the bridged-token implementation, and the eNEAR custom minter. NEAR is not an EVM chain; its side (`omni.bridge.near`) is not EVM-queryable. Of the eight target chains, five have a deployment: Ethereum, Base, Arbitrum One, Polygon PoS and BNB Smart Chain. Topics and selectors are chain-agnostic; addresses are network-specific.

**How it works.** A transfer out of an EVM chain is `initTransfer`: the bridge escrows the token (a native ERC-20), burns it (a bridged `BridgeToken`, or eNEAR through its custom minter) or takes the native coin, and emits `InitTransfer` with a per-chain `originNonce`. NEAR verifies it (Ethereum through a light client; Base, Arbitrum, Polygon and BNB through Wormhole, per the README) and, for the way back, the NEAR MPC service (Chain Signatures) signs a payload. Anyone then calls `finTransfer(signature, payload)` on the destination chain; the bridge checks that `ecrecover` returns `nearBridgeDerivedAddress()` (`0x22eb4d37677ed931d9de2218cece1a832a147490` on all five chains, read live), releases or mints, and emits `FinTransfer` (full signature in §1).

**The Omni chain ids** (`ChainKind`, `uint8`, from `omni-types`): Eth **0**, Near 1, Sol 2, Arb **3**, Base **4**, Bnb **5**, Btc 6, Zcash 7, Pol **8**, HyperEvm 9, Strk 10, Abs 11, Fogo 12, Aptos 13. Each bridge's `omniBridgeChainId()` returns its own id (read live: 0, 4, 3, 8, 5). Optimism, Avalanche and Robinhood Chain have no id and no deployment.

---

## 0. Contract families & versions

| Contract | Chain | Proxy | Live implementation | Notes |
|----------|-------|-------|---------------------|-------|
| **OmniBridge** | Ethereum | `0xe00c629aFaCCb0510995A2B95560E446A24c85B9` | `0x53785920165fbdf33b3f56885dbc8d12854ac414` (`OmniBridge`) | Created block 22,188,279. No Wormhole. |
| **OmniBridgeWormhole** | Base | `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` | `0xec81afc3485a425347ac03316675e58a680b283a` | Emits a Wormhole message per transfer. |
| **OmniBridgeWormhole** | Arbitrum One | `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` | `0xb9de9f72e81d1609e940fb2217f7286602064881` | Same address as Base. |
| **OmniBridgeWormhole** | Polygon PoS | `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` | `0xf353b40fc144d1c6c5bcdda712fa6de833016af9` | Same address; newer build with ERC-1155 support (`initTransfer1155`). |
| **OmniBridgeWormhole** | BNB | `0x073C8a225c8Cf9d3f9157F5C1a1DbE02407f5720` | `0x228e9013793c24bcca3b5a3216c01be24f956af6` | **Different address**; `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` on BNB is an unrelated contract (§7). |
| BridgeToken implementation | Ethereum / L2s / BNB | — | Ethereum `0xd5a0165ba4e83769aef74e0855497258ace4c88f`; Base, Arbitrum, Polygon `0xafda1b2ad1cfe85fdfd34cd87930ff56f07cdbe3`; BNB `0xcd9c538206f5eb433c8f1df763a7596d9a69d122` | `tokenImplementationAddress()`; each `DeployToken` creates an ERC-1967 proxy of it. |
| ENearProxy (eNEAR custom minter) | Ethereum | `0x150c79c8a70B1D528e95e200C6cA5Ed0421C44f7` | `0x801f5ff0266c065bf855dd2b344ef2d5ad2c323d` (`ENearProxy`) | `customMinters(eNEAR)`: eNEAR is burned and minted through it. |

Outside the eight chains, the repository manifests also hold OmniBridge proxies on HyperEVM (chain 999: `0xf353b40fC144d1c6c5BCdda712fa6De833016aF9`) and Abstract (chain 2741: `0xd2490A00bDB97C1EDE4fdf207CFE2664AFB9C20D`); the README lists NEAR (`omni.bridge.near`) and Solana. These were not checked on chain.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

Emitter: the OmniBridge proxy of each chain (§0). All five implementations have the same event set (compared from their verified ABIs).

| topic0 | Event |
|--------|-------|
| `0xaa7e1f77d43faa300bc5ae8f012f0b7cf80174f4c0b1cffeab250cb4966bb88c` | `InitTransfer(address indexed sender, address indexed tokenAddress, uint64 indexed originNonce, uint128 amount, uint128 fee, uint128 nativeFee, string recipient, string message)` — **source leg**; `tokenAddress = 0x0000000000000000000000000000000000000000` means the chain's native coin; `recipient` is a string such as `near:<account>` |
| `0x149a9b4894cd196e577373565ed775a142868c352c10f7a522ff7791bdc2fc3c` | `FinTransfer(uint8 indexed originChain, uint64 indexed originNonce, address tokenAddress, uint128 amount, address recipient, string feeRecipient)` — **destination leg**; `originChain` is an Omni chain id |
| `0x2393a0dc08eb80b5f0ba3015d874227975735c401f11c6f071ef1d2ab9a60759` | `DeployToken(address indexed tokenAddress, string token, string name, string symbol, uint8 decimals, uint8 originDecimals)` — a bridged token was created for a foreign token (`token` is its NEAR id) |
| `0x1fdd96b7593a0488e57af21c82714db443eba9bf3db953c1a2a36f0f7947fe18` | `LogMetadata(address indexed tokenAddress, string name, string symbol, uint8 decimals)` — status only; registers a local token on NEAR |
| `0xf15df5e6b78b0d85bbb8b0b5beaf3816040af85e5e1e1185108c75c13598166a` | `SetMetadata(address indexed tokenAddress, string token, string name, string symbol, uint8 decimals)` — admin changed a bridged token's metadata |
| `0xab40a374bc51de372200a8bc981af8c9ecdc08dfdaef0bb6e09f88f3c616ef3d` | `Paused(address account, uint256 flags)` — **selective pause** (flags: 1 `initTransfer`, 2 `finTransfer`, 4 `deployToken`; 0 = all resumed); not the OpenZeppelin `Paused(address)` |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — UUPS upgrade |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` |
| `0x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2` | `LogMessagePublished(address indexed sender, uint64 sequence, uint32 nonce, bytes payload, uint8 consistencyLevel)` — **emitted by the Wormhole core**, not by the bridge, in every Base, Arbitrum, Polygon and BNB `initTransfer` and `finTransfer`; `sender` = the OmniBridge proxy |

Role ids: `DEFAULT_ADMIN_ROLE` `0x0000000000000000000000000000000000000000000000000000000000000000`; `PAUSABLE_ADMIN_ROLE` `0x1e1db0d9c63b4a23ec134ff71a2f56610c32f638cbff81e96e14734c4daf0b4d` (read live).

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xdeb915b8` | `initTransfer(address tokenAddress, uint128 amount, uint128 fee, uint128 nativeFee, string recipient, string message)` | `payable`; **source leg**. ERC-20: escrow or burn `amount`; `msg.value` carries `nativeFee`. Native coin: `msg.value` = `amount` + `nativeFee`, `fee` must be 0. |
| `0x79db8b39` | `initTransfer1155(address tokenAddress, uint256 tokenId, uint128 amount, uint128 fee, uint128 nativeFee, string recipient, string message)` | Polygon build only. |
| `0xea3418bb` | `finTransfer(bytes signatureData, (uint64 destinationNonce, uint8 originChain, uint64 originNonce, address tokenAddress, uint128 amount, address recipient, string feeRecipient) payload)` | `payable`; **destination leg**; anyone may submit an MPC-signed payload; replay guard `completedTransfers(destinationNonce)`. |
| `0xa89aa923` | `deployToken(bytes signatureData, (string token, string name, string symbol, uint8 decimals) metadata)` | `payable`; MPC-signed; creates a `BridgeToken` proxy; emits `DeployToken`. |
| `0x31f57d22` | `logMetadata(address tokenAddress)` | Emits `LogMetadata`. |
| `0x2f771a2a` | `completedTransfers(uint64)` | View. |
| `0x18f6f994` | `currentOriginNonce()` | View; Ethereum 6,966, Base 940, Arbitrum 22, Polygon 978, BNB 1,477 on 2026-09-29. |
| `0x81351749` | `nearBridgeDerivedAddress()` | View; the MPC signer. |
| `0x3444d4ac` | `omniBridgeChainId()` | View. |
| `0x90f3e04c` | `wormholeNonce()` | View (Wormhole builds). |
| `0x21d77c2b` | `customMinters(address)` | View; eNEAR → ENearProxy. |
| `0x70ef2947` | `setNearBridgeDerivedAddress(address nearBridgeDerivedAddress_)` | `DEFAULT_ADMIN_ROLE`; **replaces the signer: every payout depends on it**. No event. |
| `0xeb6ce61e` | `addCustomToken(string nearTokenId, address tokenAddress, address customMinter, uint8 originDecimals)` | `DEFAULT_ADMIN_ROLE`. |
| `0x5b3750ce` | `removeCustomToken(address tokenAddress)` | `DEFAULT_ADMIN_ROLE`. |
| `0x55b8ce0a` | `upgradeToken(address tokenAddress, address implementation)` | `DEFAULT_ADMIN_ROLE`; upgrades a bridged token. |
| `0x0890d80c` | `setMetadata(string token, string name, string symbol)` | `DEFAULT_ADMIN_ROLE`; emits `SetMetadata`. |
| `0xc7ecdde4` | `setWormholeAddress(address wormholeAddress, uint8 consistencyLevel)` | `DEFAULT_ADMIN_ROLE` (Wormhole builds). |
| `0x136439dd` | `pause(uint256 flags)` | `PAUSABLE_ADMIN_ROLE`; emits `Paused(address,uint256)`. |
| `0x595c6a67` | `pauseAll()` | `PAUSABLE_ADMIN_ROLE`. |
| `0xbffa777d` | `pausedFlags()` | View; 0 on all five chains on 2026-09-29. |
| `0x4f1ef286` | `upgradeToAndCall(address newImplementation, bytes data)` | UUPS; `DEFAULT_ADMIN_ROLE`. |
| `0x2f2ff15d` | `grantRole(bytes32 role, address account)` | `DEFAULT_ADMIN_ROLE`. |
| `0x91d14854` | `hasRole(bytes32 role, address account)` | View. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **OmniBridge** (proxy) | `0xe00c629aFaCCb0510995A2B95560E446A24c85B9` | Escrow of native ERC-20s and ETH; 170-byte ERC-1967 proxy. |
| OmniBridge implementation | `0x53785920165fbdf33b3f56885dbc8d12854ac414` | `OmniBridge`, 16,734 bytes. |
| Admin Safe | `0x2468603819Bf09Ed3Fb6f3EFeff24B1955f3CDE1` | `DEFAULT_ADMIN_ROLE` (granted at block 22,224,025); a Safe with threshold 3; also the admin of the legacy Rainbow contracts. |
| Deployer (EOA) | `0xD9cB077700AA4D32d30bDA5e99bb171549b5a382` | EOA (nonce 361); still holds `PAUSABLE_ADMIN_ROLE`; renounced `DEFAULT_ADMIN_ROLE` at block 22,224,038. |
| MPC signer | `0x22eb4d37677ed931d9de2218cece1a832a147490` | `nearBridgeDerivedAddress()`: a key held by the NEAR MPC network; no code, nonce 0 (it only signs). |
| ENearProxy (proxy) | `0x150c79c8a70B1D528e95e200C6cA5Ed0421C44f7` | eNEAR custom minter; implementation `0x801f5ff0266c065bf855dd2b344ef2d5ad2c323d`. |
| eNEAR token | `0x85f17cf997934a597031b2e18a9ab6ebd4b9f6a4` | The NEAR ERC-20 (24 decimals), burned and minted through the ENearProxy. |
| BridgeToken implementation | `0xd5a0165ba4e83769aef74e0855497258ace4c88f` | Template of bridged tokens. |

## 4. Addresses — Base (8453), Arbitrum One (42161), Polygon PoS (137), BNB Smart Chain (56)

| Chain | OmniBridge proxy | Implementation | `omniBridgeChainId()` | Wormhole core seen in receipts |
|-------|------------------|----------------|------------------------|--------------------------------|
| Base | `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` | `0xec81afc3485a425347ac03316675e58a680b283a` | 4 | `0xbebdb6C8ddC678FfA9f8748f85C815C556Dd8ac6` |
| Arbitrum One | `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` | `0xb9de9f72e81d1609e940fb2217f7286602064881` | 3 | not observed (no transfer in the window) |
| Polygon PoS | `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` | `0xf353b40fc144d1c6c5bcdda712fa6de833016af9` | 8 | `0x7A4B5a56256163F07b2C80A7cA55aBE66c4ec4d7` |
| BNB | `0x073C8a225c8Cf9d3f9157F5C1a1DbE02407f5720` | `0x228e9013793c24bcca3b5a3216c01be24f956af6` | 5 | `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B` |

The Base and Arbitrum proxies were created by the same deployer EOA as on Ethereum (Sourcify deployment records; the Polygon proxy has no Sourcify record). On Base, Arbitrum, Polygon and BNB, `DEFAULT_ADMIN_ROLE` is held by another Safe, `0xbaA031a1f625A8a50408e3D9Da338fFa245e7C39` (threshold 3, the same address on all four; `hasRole` read live). The Blockscout logs show the grant from the deployer at Base block 25,475,110 and Arbitrum block 298,852,513.

---

## 5. Cross-chain summary

| Chain | ID | Omni chain id | OmniBridge | Note |
|-------|----|---------------|------------|------|
| **Ethereum** | 1 | 0 | ✅ `0xe00c629aFaCCb0510995A2B95560E446A24c85B9` | Light-client verified on NEAR. |
| **Base** | 8453 | 4 | ✅ `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` | Wormhole. |
| **Arbitrum One** | 42161 | 3 | ✅ `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` | Wormhole. |
| **Polygon PoS** | 137 | 8 | ✅ `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` | Wormhole; different proxy bytecode than Base and Arbitrum. |
| **BNB Smart Chain** | 56 | 5 | ✅ `0x073C8a225c8Cf9d3f9157F5C1a1DbE02407f5720` | Wormhole. `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` on BNB is a decoy (6,430-byte unrelated contract). |
| Optimism | 10 | — | — | no deployment: `eth_getCode` = `0x` at `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989`, `0x073C8a225c8Cf9d3f9157F5C1a1DbE02407f5720` and `0xe00c629aFaCCb0510995A2B95560E446A24c85B9`; no Omni chain id; not in the README |
| Avalanche C-Chain | 43114 | — | — | same |
| Robinhood Chain | 4663 | — | — | same |

Outside the eight: NEAR (`omni.bridge.near`), Solana, and, per the repository manifests, HyperEVM and Abstract (§0).

---

## 6. Proxies

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| OmniBridge (all five chains) | UUPS (ERC-1967) | 170-byte proxy; impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc` → §0; admin slot empty. | `DEFAULT_ADMIN_ROLE`: on Ethereum the Safe `0x2468603819Bf09Ed3Fb6f3EFeff24B1955f3CDE1`, on Base, Arbitrum, Polygon and BNB the Safe `0xbaA031a1f625A8a50408e3D9Da338fFa245e7C39` (both threshold 3). No timelock. Watch `Upgraded` and `RoleGranted` for role `0x0000000000000000000000000000000000000000000000000000000000000000`. |
| ENearProxy | UUPS (ERC-1967) | impl `0x801f5ff0266c065bf855dd2b344ef2d5ad2c323d`. | Its own admin role. |
| Bridged tokens | ERC-1967 proxies of the BridgeToken implementation | Created by `deployToken`. | `upgradeToken` on the bridge. |

---

## 7. Detection invariants & gotchas

1. **Source leg:** `initTransfer` → ERC-20 `Transfer(user → OmniBridge)` (escrow), or `Transfer(user → 0x0000000000000000000000000000000000000000)` for a bridged token, or a transfer to the ENearProxy and a burn for eNEAR; then `InitTransfer`. For a token transfer, `msg.value` is only the `nativeFee`; for the native coin (`tokenAddress` = zero), `msg.value` = `amount` + `nativeFee`.
2. **Destination leg:** a relayer calls `finTransfer` → `Transfer(OmniBridge → recipient)` (release), a mint from zero (bridged token or eNEAR), or an internal native transfer (zero token) → `FinTransfer`. The relayer, not the user, is `tx.from`.
3. **Link key: `(originChain, originNonce)`.** `InitTransfer.originNonce` (topic 3) with the source bridge's `omniBridgeChainId()` equals `FinTransfer(originChain = topic 1, originNonce = topic 2)` on the destination. A transfer that starts on NEAR carries `originChain = 1` (as in the sampled `finTransfer`s); the NEAR leg is off the EVM. `destinationNonce` (the replay guard) is in the calldata only.
4. **Wormhole duplicates on L2s and BNB.** Each `initTransfer` and `finTransfer` there also emits `LogMessagePublished` from the chain's Wormhole core with `sender` = the bridge. Do not count it as a second transfer, and do not treat it as a Wormhole token-bridge transfer.
5. **BNB address trap.** The bridge on BNB is `0x073C8a225c8Cf9d3f9157F5C1a1DbE02407f5720`. `0xd025b38762B4A4E36F0Cde483b86CB13ea00D989` exists on BNB but is a different, unverified 6,430-byte contract that is not a proxy. Key on `(chain id, address)`.
6. **Recipient strings.** `InitTransfer.recipient` is an Omni address string (`near:alice.near`, `eth:<address>`, `sol:<account>`), not an EVM address; decode the data.
7. **Drain and admin triggers.** `Upgraded`; `RoleGranted` of `DEFAULT_ADMIN_ROLE` or `PAUSABLE_ADMIN_ROLE`; `setNearBridgeDerivedAddress` (call, no event: a new signer can release everything); `addCustomToken` / `upgradeToken` / `setWormholeAddress` calls; `Paused(address,uint256)` with flag 2 (payouts halted). A `FinTransfer` whose amount exceeds the escrowed balance trend is the drain signal.
8. **Same address, different code.** Base and Arbitrum share proxy bytecode; Polygon's proxy bytecode differs and its implementation adds ERC-1155 functions. The event topics are the same on all five.
9. **Legacy contracts.** The Rainbow `ERC20Locker`, `EthCustodian` and `eNEAR` flows are separate (see the `rainbow` doc); eNEAR now moves through the Omni `ENearProxy`.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_INIT_TRANSFER              = '\xaa7e1f77d43faa300bc5ae8f012f0b7cf80174f4c0b1cffeab250cb4966bb88c'
TOPIC_FIN_TRANSFER               = '\x149a9b4894cd196e577373565ed775a142868c352c10f7a522ff7791bdc2fc3c'
TOPIC_DEPLOY_TOKEN               = '\x2393a0dc08eb80b5f0ba3015d874227975735c401f11c6f071ef1d2ab9a60759'
TOPIC_LOG_METADATA               = '\x1fdd96b7593a0488e57af21c82714db443eba9bf3db953c1a2a36f0f7947fe18'
TOPIC_SET_METADATA               = '\xf15df5e6b78b0d85bbb8b0b5beaf3816040af85e5e1e1185108c75c13598166a'
TOPIC_SELECTIVE_PAUSED           = '\xab40a374bc51de372200a8bc981af8c9ecdc08dfdaef0bb6e09f88f3c616ef3d'
TOPIC_UPGRADED                   = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ROLE_GRANTED               = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_WORMHOLE_LOG_MESSAGE       = '\x6eb224fb001ed210e379b335e35efe88672a8ce935d981a6896b27ffdf52a3b2'

-- ===== Selectors =====
SEL_INIT_TRANSFER                = '\xdeb915b8'
SEL_FIN_TRANSFER                 = '\xea3418bb'
SEL_DEPLOY_TOKEN                 = '\xa89aa923'
SEL_SET_NEAR_BRIDGE_DERIVED_ADDR = '\x70ef2947'
SEL_ADD_CUSTOM_TOKEN             = '\xeb6ce61e'
SEL_UPGRADE_TOKEN                = '\x55b8ce0a'
SEL_PAUSE                        = '\x136439dd'
SEL_PAUSE_ALL                    = '\x595c6a67'
SEL_UPGRADE_TO_AND_CALL          = '\x4f1ef286'

-- ===== Ids =====
ROLE_PAUSABLE_ADMIN              = '\x1e1db0d9c63b4a23ec134ff71a2f56610c32f638cbff81e96e14734c4daf0b4d'
-- Omni chain ids: Eth 0, Near 1, Sol 2, Arb 3, Base 4, Bnb 5, Pol 8

-- ===== Addresses =====
ETH_OMNI_BRIDGE                  = '\xe00c629afaccb0510995a2b95560e446a24c85b9'
ETH_OMNI_BRIDGE_IMPL             = '\x53785920165fbdf33b3f56885dbc8d12854ac414'
ETH_OMNI_ADMIN_SAFE              = '\x2468603819bf09ed3fb6f3efeff24b1955f3cde1'
BASE_OMNI_ADMIN_SAFE             = '\xbaa031a1f625a8a50408e3d9da338ffa245e7c39'
ARB_OMNI_ADMIN_SAFE              = '\xbaa031a1f625a8a50408e3d9da338ffa245e7c39'
POLY_OMNI_ADMIN_SAFE             = '\xbaa031a1f625a8a50408e3d9da338ffa245e7c39'
BNB_OMNI_ADMIN_SAFE              = '\xbaa031a1f625a8a50408e3d9da338ffa245e7c39'
ETH_OMNI_DEPLOYER_EOA            = '\xd9cb077700aa4d32d30bda5e99bb171549b5a382'
ETH_OMNI_MPC_SIGNER_EOA          = '\x22eb4d37677ed931d9de2218cece1a832a147490'
ETH_OMNI_ENEAR_PROXY             = '\x150c79c8a70b1d528e95e200c6ca5ed0421c44f7'
ETH_ENEAR                        = '\x85f17cf997934a597031b2e18a9ab6ebd4b9f6a4'
BASE_OMNI_BRIDGE                 = '\xd025b38762b4a4e36f0cde483b86cb13ea00d989'
ARB_OMNI_BRIDGE                  = '\xd025b38762b4a4e36f0cde483b86cb13ea00d989'
POLY_OMNI_BRIDGE                 = '\xd025b38762b4a4e36f0cde483b86cb13ea00d989'
BNB_OMNI_BRIDGE                  = '\x073c8a225c8cf9d3f9157f5c1a1dbe02407f5720'
BASE_WORMHOLE_CORE               = '\xbebdb6c8ddc678ffa9f8748f85c815c556dd8ac6'
POLY_WORMHOLE_CORE               = '\x7a4b5a56256163f07b2c80a7ca55abe66c4ec4d7'
BNB_WORMHOLE_CORE                = '\x98f3c9e6e3face36baad05fe09d375ef1464288b'
-- BNB decoy (NOT the bridge): 0xd025b38762b4a4e36f0cde483b86cb13ea00d989 on chain 56
-- Optimism, Avalanche, Robinhood: no deployment
```

---

## 9. Verification & sources

How the constants were verified (2026-09-29):

- **Topic0 / selectors:** recomputed as `keccak256(canonical signature)` (and `[0:4]`) from the Sourcify verified ABIs of the five live implementations (their event sets are identical; the Polygon build adds ERC-1155 functions); the pause flags, payload layout and value paths from `OmniBridge.sol` (`initTransfer`, `finTransfer`, `deployToken`); the chain ids from `near/omni-types/src/lib.rs` (`ChainKind`); `LogMessagePublished` recomputed and matched to receipts.
- **Addresses:** from the repository README (mainnet list) and the upgrade manifests (`evm/.openzeppelin/base.json`, `arbitrum-one.json`, `polygon.json`, `unknown-999.json`, `evm/.upgradable/unknown-network-2741.json`); each target-chain proxy existence-checked with `eth_getCode` and its implementation read from the EIP-1967 slot. `eth_getCode` = `0x` at the proxy addresses on Optimism, Avalanche and Robinhood Chain (§5).
- **Roles:** on Ethereum, the deployment transaction granted both roles to the deployer; `grantRole(DEFAULT_ADMIN_ROLE, 0x2468603819Bf09Ed3Fb6f3EFeff24B1955f3CDE1)` at block 22,224,025 and the deployer's `renounceRole` at block 22,224,038 (receipts read); `hasRole` confirms the Safe holds `DEFAULT_ADMIN_ROLE` and the deployer `PAUSABLE_ADMIN_ROLE`; Safe `getThreshold()` = 3. Over blocks 22,188,279–26,075,812 the Ethereum proxy emitted 3 `RoleGranted`, 1 `RoleRevoked` and 1 `Upgraded` (at deployment): the implementation has not changed since. On Base, Arbitrum, Polygon and BNB, `hasRole` for `DEFAULT_ADMIN_ROLE` is false for the Ethereum Safe and the deployer and true for `0xbaA031a1f625A8a50408e3D9Da338fFa245e7C39` (a Safe with threshold 3 on each; Polygon read with one batched call to the public `polygon.drpc.org` endpoint); the grants were found with the Base and Arbitrum Blockscout log APIs.
- **Activity, pinned 12-hour window 2026-09-28 00:00–12:00 UTC:** `InitTransfer` — Ethereum 83, Base 0, Arbitrum 0, Polygon 6, BNB 46; `FinTransfer` — Ethereum 50, Base 5, Arbitrum 0, Polygon 3, BNB 47 (all from the bridges in §5); Optimism, Avalanche, Robinhood Chain 0 for both from any emitter. Ethereum `DeployToken` 0, `LogMetadata` 0, `SetMetadata` 0, `Paused(address,uint256)` 0.
- **Sample transactions (receipts read):** Ethereum `initTransfer` `0x66d3cba6a48da2faeeca541b338c98673e1b55118f2ece82465849958f9ac630` (ERC-20 `Transfer` user → bridge, `InitTransfer` nonce 6,824, `msg.value` = native fee); Ethereum `finTransfer` `0xf6cc8bdc37e067f766506821a87d127a4546176df7968dbf2b0957bd4dad9040` (`Transfer` bridge → recipient, `FinTransfer(originChain 1)`); Base `finTransfer` `0xce2aed6c6c6ee92a8d081123df923d6c60170bd0326d71d6b91f263074fd6fd2` (mint to the recipient, Wormhole `LogMessagePublished` from the core, `FinTransfer`); Polygon `initTransfer` `0xdf34fac615d74475dfb3a31ff896f6ec1e206dbbe2888fec7035441749d4d905` (ERC-20 `Transfer` user → bridge, Wormhole message, `InitTransfer`); BNB `initTransfer` `0x143fe5ae93f5655f7e39815d56c5efd0cd5f7552592a1d9590885bdfe733db95` (ERC-20 `Transfer` user → bridge, Wormhole message from `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B`, `InitTransfer` nonce 1,352; receipt read from the BNB Chain public endpoint).

Authoritative sources (opened):
- [Near-One/omni-bridge](https://github.com/Near-One/omni-bridge) — `README.md` (mainnet addresses, verification per chain), `evm/src/omni-bridge/contracts/` (`OmniBridge.sol`, `OmniBridgeWormhole.sol`, `BridgeTypes.sol`, `SelectivePausableUpgradable.sol`), `evm/.openzeppelin/*.json`, `evm/.upgradable/unknown-network-2741.json`, `near/omni-types/src/lib.rs`
- Blockscout log API (role grants) — [Base](https://base.blockscout.com/api?module=logs&action=getLogs&fromBlock=24872996&toBlock=latest&address=0xd025b38762B4A4E36F0Cde483b86CB13ea00D989&topic0=0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d) · [Arbitrum](https://arbitrum.blockscout.com/api?module=logs&action=getLogs&fromBlock=294054200&toBlock=latest&address=0xd025b38762B4A4E36F0Cde483b86CB13ea00D989&topic0=0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d)
- Sourcify — [Ethereum OmniBridge impl](https://sourcify.dev/server/v2/contract/1/0x53785920165fbdf33b3f56885dbc8d12854ac414) · [Base impl](https://sourcify.dev/server/v2/contract/8453/0xec81afc3485a425347ac03316675e58a680b283a) · [Arbitrum impl](https://sourcify.dev/server/v2/contract/42161/0xb9de9f72e81d1609e940fb2217f7286602064881) · [Polygon impl](https://sourcify.dev/server/v2/contract/137/0xf353b40fc144d1c6c5bcdda712fa6de833016af9) · [BNB impl](https://sourcify.dev/server/v2/contract/56/0x228e9013793c24bcca3b5a3216c01be24f956af6) · [ENearProxy](https://sourcify.dev/server/v2/contract/1/0x150c79c8a70b1d528e95e200c6ca5ed0421c44f7)
