# Router Gateway & AssetBridge (Voyager) — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon)

**Status:** verified against live RPC on all seven chains and the canonical `router-protocol/router-contracts` repo (`gateway/evm/contracts/GatewayUpgradeable.sol`, `asset-bridge/evm/contracts/AssetBridgeUpgradeable.sol`) on 2026-06-09. Contract names (`GatewayUpgradeable`, `AssetBridge`) read from Routescan/Snowscan verified source.
**Scope:** the **Router Gateway** (the EVM endpoint of Router Chain's cross-chain messaging / CrossTalk, used by Nitro for settlement & refunds) and the older **AssetBridge / Voyager** mint-burn token bridge. Topics/selectors are **chain-agnostic**; addresses are network-specific. The Nitro **AssetForwarder** (the `FundsDeposited`/`FundsPaid` liquidity bridge) is in [core.md](./core.md).

The **Gateway** (`GatewayUpgradeable`) is Router Protocol's generic message rail: dApps and the Nitro AssetForwarder call `iSend` to emit a request to the Router Chain, validators sign a valset checkpoint, and `iReceive`/`iAck` deliver messages/acks back. It is a **UUPS proxy** on Ethereum/Base/BNB/Optimism/Polygon and a directly-deployed logic contract (fronted by a proxy at a different address) on Avalanche/Arbitrum — see the role table in [core.md](./core.md) §10. The **AssetBridge** (`AssetBridge`/Voyager) is the legacy token bridge (`transferToken` → `TokenTransfer`/`Execute`) that predates Nitro; it is live only on **Ethereum, Avalanche, Arbitrum**.

> **Address-collision reminder (see [core.md](./core.md) §10):** the Gateway proxy is `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` on **ETH/Base/BNB/OP**, but `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` on **Avalanche/Arbitrum** and `0x21c1E74CAaDf990E237920d5515955a024031109` on **Polygon**. The same literals are the *AssetForwarder* on other chains. Always confirm role by `currentVersion()` (Gateway) vs `depositNonce()` (forwarder).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All recomputed locally with keccak256 on 2026-06-09.

### 1.1 Gateway (`GatewayUpgradeable`)

| topic0 | Event |
|--------|-------|
| `0xfe97fc293d7232e604aad58a3d02e21ee253fa0462586ea83bf3d6a84d987a6a` | `ISendEvent(uint256 version, uint256 routeAmount, uint256 indexed eventNonce, address requestSender, string srcChainId, string destChainId, string routeRecipient, bytes requestMetadata, bytes requestPacket)` |
| `0x3bf9ad3ae3a3a7c22a8cb63b259bcf1abc195a223b499b4c8e884981d6154839` | `IReceiveEvent(uint256 indexed requestIdentifier, uint256 indexed eventNonce, string srcChainId, string destChainId, string relayerRouterAddress, string requestSender, bytes execData, bool execStatus)` |
| `0x21a2de7d1ff2cd4fe0ffece047122598d9d5ef15a7aecff28f73c7deae9d64db` | `IAckEvent(uint256 indexed eventNonce, uint256 indexed requestIdentifier, string relayerRouterAddress, string chainId, bytes data, bool success)` |
| `0x20d5dcc846f7451afb9c8dc6dbf5f2242d04549ae17eb976f19b36cb4d7e1656` | `ValsetUpdatedEvent(uint256 indexed _newValsetNonce, uint256 indexed _eventNonce, string srcChainId, address[] _validators, uint64[] _powers)` |
| `0xa61fe9500102ba95e70ba9796789006b4719448a4ebc364e6c2c943d5d63d18f` | `SetVaultEvent(address vaultAddress)` |
| `0x4fc4e10a6b18b18a9b637c4c543c7bc1d0759966d577ac6a9f4bbfaf678862f4` | `BridgeFeeUpdatedEvent(uint256 oldFeeValue, uint256 newFeeValue)` |
| `0x1ff6cbf099d2cd90494426a312eae3d52a88116b0ee9f37e074072a79a233489` | `SetDappMetadataEvent(uint256 indexed eventNonce, address dappAddress, string chainId, string feePayerAddress)` |

`ISendEvent` is the workhorse outbound topic (every cross-chain request, incl. Nitro settlement). `ValsetUpdatedEvent` is a high-signal validator-set rotation alert.

### 1.2 AssetBridge / Voyager (`AssetBridge`)

| topic0 | Event |
|--------|-------|
| `0x0a9a968c7c6cc6182a9339c64cb833f1fa34f5a5275c3e3cad13f5db1c6b82a8` | `TokenTransfer(bytes32 indexed destChainIdBytes, address indexed srcTokenAddress, uint256 srcTokenAmount, bytes recipient, uint256 partnerId, uint256 depositId)` |
| `0x220aec4438bd2c268e817da97e3b821192adc2c11dfea86d51d6ffd8bf38de6e` | `TokenTransferWithInstruction(bytes32 indexed destChainIdBytes, address indexed srcTokenAddress, uint256 srcTokenAmount, bytes recipient, uint256 partnerId, uint64 destGasLimit, bytes instruction, uint256 depositId)` |
| `0xc6cb37798db6a3c249b500abfed1b5787f96457834af95a59170a58e1874e51c` | `DepositReverted(bytes32 indexed destChainIdBytes, uint256 indexed depositNonce, address indexed sender, address srcSettlementToken, uint256 srcSettlementAmount)` |
| `0xb937c701be72296797de30f67fec8bc6c096aa6b4c1850a5e659a0dc17165d8f` | `Execute(uint8 executeType, bytes32 indexed sourceChainIdBytes, uint256 indexed depositNonce, address settlementToken, uint256 settlementAmount, address recipient)` |
| `0x2c661efd5bbbd239384997a4afc5e16ba28d1cfdf0c6fe2318ffee919ac79abf` | `ExecuteWithMessage(uint8 executeType, bytes32 indexed sourceChainIdBytes, uint256 indexed depositNonce, address settlementToken, uint256 settlementAmount, address recipient, bool flag, bytes data)` |

`TokenTransfer` = source-side deposit; `Execute` = destination-side mint/release. Linked by `(sourceChainIdBytes, depositNonce)`.

### 1.3 Proxy / upgrade & AccessControl

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` — **watch on the Gateway proxies** to catch impl rotations. |
| `0x7f26b83ff96e1f2b6a682f133852f6798a09c465da95921460cefb3847402498` | `Initialized(uint8 version)` — fires once per (re)init of a proxy. |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed,address indexed,address indexed)` |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed,address indexed,address indexed)` |

The Gateway proxies are **UUPS** (no `AdminChanged` — admin slot empty). `Upgraded(address)` is the only upgrade signal.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Gateway — verified present in the live ETH impl `0xac589f48…` (PUSH4 scan)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x7bed470a` | `iSend(uint256 version, uint256 routeAmount, string routeRecipient, string destChainId, bytes requestMetadata, bytes requestPacket)` → `uint256` | `payable`. Outbound request; emits `ISendEvent`. |
| `0x44bdf5a7` | `iReceive((address[],uint64[],uint256) currentValset, bytes[] sigs, (uint256,uint256,uint256,string,address,string,address,string,address,bytes,bool) requestPayload, string relayerRouterAddress)` | Inbound delivery; verifies valset sigs; emits `IReceiveEvent`. |
| `0x2205643a` | `iAck((address[],uint64[],uint256) currentValset, bytes[] sigs, (uint256,uint256,string,address,bytes,bool) crossChainAckPayload, string relayerRouterAddress)` | Acknowledgement delivery; emits `IAckEvent`. |
| `0x3bcced29` | `updateValset((address[],uint64[],uint256) newValset, (address[],uint64[],uint256) currentValset, bytes[] sigs)` | Validator-set rotation; emits `ValsetUpdatedEvent`. |
| `0xef15cbda` | `setDappMetadata(string feePayerAddress)` → `uint256` | `payable`. Emits `SetDappMetadataEvent`. |
| `0xea76f6d7` | `setBridgeFees(uint256 _iSendDefaultFee)` | RESOURCE_SETTER. Emits `BridgeFeeUpdatedEvent`. |
| `0x9d888e86` | `currentVersion()` → `uint256` | **Role probe — answers on a Gateway, reverts on an AssetForwarder.** ETH Gateway returns 1. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | `payable`. UUPS (DEFAULT_ADMIN). Emits `Upgraded`. |
| `0x3659cfe6` | `upgradeTo(address)` | UUPS. |
| `0x52d1902d` | `proxiableUUID()` → `bytes32` | UUPS — returns the EIP-1967 slot. |

### 2.2 AssetBridge / Voyager — verified present in the live Avax deploy `0xf0773508…` (PUSH4 scan)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x63d42ae7` | `transferToken((bytes32,address,uint256,bytes,uint256) transferPayload)` | `payable`. Lock/burn + emit `TokenTransfer`. Tuple = `TransferPayload(destChainIdBytes, srcTokenAddress, srcTokenAmount, recipient, partnerId)`. |
| `0x8121165f` | `transferTokenWithInstruction((bytes32,address,uint256,bytes,uint256), uint64 destGasLimit, bytes instruction)` | Emits `TokenTransferWithInstruction`. |
| `0x751657d7` | `swapAndTransferToken((bytes32,address[],uint256[],bytes[],uint256,uint256,bytes,uint256))` | DexSpan swap then bridge. |
| `0x07927ded` | `swapAndTransferTokenWithInstruction((bytes32,address[],uint256[],bytes[],uint256,uint256,bytes,uint256), uint64, bytes)` | |
| `0xde35f5cb` | `depositNonce()` → `uint256` | Present on AssetBridge too (shared counter name) — so distinguish AssetBridge from AssetForwarder by **`transferToken`** presence, not by `depositNonce`. |

> `stake(address,address,uint256)` (`0xbf6eac2f`) / `unstake(...)` (`0x60829f8a`) from the repo's `AssetBridgeUpgradeable` are **absent** on the deployed `0xf0773508…` (this is the earlier non-staking AssetBridge). `iReceive` (`0x1aa6485a`) and the four transfer functions are present.

---

## 3. Addresses — per chain (verified `eth_getCode` non-empty on each chain's publicnode RPC, 2026-06-09)

Role of each address is chain-dependent; the table below lists only the **Gateway** and **AssetBridge** roles (the AssetForwarder role of these same literals is in [core.md](./core.md)).

### 3.1 Ethereum mainnet (chain ID 1)
| Role | Address | Pattern |
|------|---------|---------|
| **Gateway** | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | UUPS proxy → impl `0xac589f48f94134db8671acd31f4da55ce43e318c`; admin slot empty; `currentVersion()` = 1. |
| **AssetBridge** | `0xf0773508c585246bd09bfb401aa18b72685b03f9` | Direct deploy (38,244-char). |

### 3.2 Base (chain ID 8453)
| Role | Address | Pattern |
|------|---------|---------|
| **Gateway** | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | UUPS proxy → impl `0xac589f48…`; `currentVersion()` = 1. |
| AssetBridge | — | **Not deployed** (`0xf0773508…` = `0x`). |

### 3.3 BNB Smart Chain (chain ID 56)
| Role | Address | Pattern |
|------|---------|---------|
| **Gateway** | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | UUPS proxy → impl `0xac589f48…`. |
| AssetBridge | — | **Not deployed.** |

### 3.4 Avalanche C-Chain (chain ID 43114)
| Role | Address | Pattern |
|------|---------|---------|
| **Gateway** (proxy) | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | ERC1967 proxy → impl `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973`. ⚠️ here `0xC21e4ebD…` is the Gateway, not the forwarder. |
| Gateway logic (direct) | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | The 41,526-char `GatewayUpgradeable` logic is deployed *directly* at this address on Avax (it is the impl). |
| **AssetBridge** | `0xf0773508c585246bd09bfb401aa18b72685b03f9` | Direct deploy (35,470-char); verified name `AssetBridge`. |

### 3.5 Arbitrum One (chain ID 42161)
| Role | Address | Pattern |
|------|---------|---------|
| **Gateway** (proxy) | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | ERC1967 proxy → impl `0x86dfc31d…`. |
| Gateway logic (direct) | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | 41,526-char direct logic. |
| **AssetBridge** | `0xf0773508c585246bd09bfb401aa18b72685b03f9` | Direct deploy (35,470-char). |

### 3.6 Optimism (chain ID 10)
| Role | Address | Pattern |
|------|---------|---------|
| **Gateway** | `0x86dfc31d9cb3280ee1eb1096caa9fc66299af973` | UUPS proxy → impl `0xac589f48…`. |
| AssetBridge | — | **Not deployed.** |

### 3.7 Polygon PoS (chain ID 137)
| Role | Address | Pattern |
|------|---------|---------|
| **Gateway** (proxy) | `0x21c1E74CAaDf990E237920d5515955a024031109` | EIP-1967 proxy → impl `0x5b97f51c9f5ca8a6ea5e44570aaa09d17c8ab824`; `currentVersion()` = 1. ⚠️ here `0x21c1E74C…` is the Gateway, not a forwarder. |
| Gateway logic (direct) | `0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9` | 41,526-char `GatewayUpgradeable` logic deployed directly. |
| AssetBridge | — | **Not deployed.** |

---

## 4. Cross-chain summary

| Chain | ID | Gateway address | Gateway pattern | AssetBridge |
|-------|----|-----------------|-----------------|-------------|
| Ethereum | 1 | `0x86dfc31d…` | UUPS proxy → `0xac589f48…` | `0xf0773508…` |
| Base | 8453 | `0x86dfc31d…` | UUPS proxy → `0xac589f48…` | — |
| BNB | 56 | `0x86dfc31d…` | UUPS proxy → `0xac589f48…` | — |
| Avalanche | 43114 | `0xC21e4ebD…` | ERC1967 proxy → `0x86dfc31d…` | `0xf0773508…` |
| Arbitrum | 42161 | `0xC21e4ebD…` | ERC1967 proxy → `0x86dfc31d…` | `0xf0773508…` |
| Optimism | 10 | `0x86dfc31d…` | UUPS proxy → `0xac589f48…` | — |
| Polygon | 137 | `0x21c1E74C…` | EIP-1967 proxy → `0x5b97f51c…` | — |

**Two distinct Gateway deployment styles.** On ETH/Base/BNB/OP the Gateway proxy lives at `0x86dfc31d…` and its UUPS impl at `0xac589f48…`. On Avax/Arb the *impl* (the same 41,526-char logic) sits at `0x86dfc31d…` and the proxy is `0xC21e4ebD…`. On Polygon the proxy is `0x21c1E74C…` (impl `0x5b97f51c…`) and the bare logic is at `0xC21e4ebD…`. **The same address literal is impl on one chain and proxy on another — key on `(chainId, address)` and read the impl slot live.**

---

## 5. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Gateway** (ETH/Base/BNB/OP) | **UUPS** (EIP-1967) | impl slot `0x3608…382bbc` populated (`0xac589f48…`); **admin slot `0xb531…6103` empty**; impl exposes `upgradeToAndCall`/`proxiableUUID`. `currentVersion()` answers. | `DEFAULT_ADMIN_ROLE` (`_authorizeUpgrade`). |
| **Gateway** (Avax/Arb) | **ERC1967 proxy** | proxy `0xC21e4ebD…`, impl slot → `0x86dfc31d…`; admin slot empty. | DEFAULT_ADMIN. |
| **Gateway** (Polygon) | **EIP-1967 proxy** | proxy `0x21c1E74C…`, impl slot → `0x5b97f51c…`. | DEFAULT_ADMIN. |
| **AssetBridge** | **Not a proxy** (direct) | impl slot empty; 35–38 KB runtime; `transferToken`/`depositNonce` answer directly. | immutable. |

EIP-1967 impl slot: `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`. EIP-1967 admin slot: `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103` (empty on all Gateway proxies → UUPS). Watch `Upgraded(address)` `0xbc7cd75a…` on each Gateway proxy.

---

## 6. Detection invariants & gotchas

1. **`currentVersion()` (Gateway) vs `depositNonce()` (forwarder)/`transferToken` (AssetBridge) is the role probe.** The address literals are reused with different roles per chain (see [core.md](./core.md) §10). Never assume role from address alone.
2. **The Gateway impl `0x86dfc31d…` is the *proxy* on ETH/Base/BNB/OP but the *impl/logic* on Avax/Arb.** Reading its EIP-1967 slot gives `0xac589f48…` on the first set and `0x000…0` (it IS the logic) on Avax/Arb. Always read the impl slot live and resolve per chain.
3. **`ISendEvent` carries chain ids as `string`** (`srcChainId`/`destChainId`) and routing payloads as `bytes` — decode per Router's CrossTalk format, not as numeric ids/addresses.
4. **`ISendEvent.routeAmount > 0` means tokens were escrowed in the Gateway vault** (`SetVaultEvent` sets that vault). Most Nitro settlement `iSend`s carry `routeAmount = 0` (messaging only).
5. **AssetBridge is legacy and live only on ETH/Avax/Arb.** A "Router bridge" event on Base/BNB/OP/Polygon is the AssetForwarder (`FundsDeposited`), never AssetBridge — `0xf0773508…` returns `0x` there.
6. **AssetBridge `Execute.executeType` (uint8)** distinguishes the settlement path (mint vs release vs swap); `ExecuteWithMessage` adds a `bool flag` + `bytes data` for the post-execute handler call.
7. **Gateway is UUPS — watch `Upgraded(address)` `0xbc7cd75a…`** on each proxy for impl rotations (and `ValsetUpdatedEvent` for validator-set changes, the security-critical signal). The forwarder, by contrast, is immutable (no `Upgraded`).
8. **`SetDappMetadataEvent` / `setDappMetadata` register a fee-payer per dApp** — not a fund movement, but useful to enumerate integrators.

---

## 7. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Gateway topics =====
TOPIC_ISEND_EVENT                  = '\xfe97fc293d7232e604aad58a3d02e21ee253fa0462586ea83bf3d6a84d987a6a'
TOPIC_IRECEIVE_EVENT               = '\x3bf9ad3ae3a3a7c22a8cb63b259bcf1abc195a223b499b4c8e884981d6154839'
TOPIC_IACK_EVENT                   = '\x21a2de7d1ff2cd4fe0ffece047122598d9d5ef15a7aecff28f73c7deae9d64db'
TOPIC_VALSET_UPDATED               = '\x20d5dcc846f7451afb9c8dc6dbf5f2242d04549ae17eb976f19b36cb4d7e1656'
TOPIC_SET_VAULT                    = '\xa61fe9500102ba95e70ba9796789006b4719448a4ebc364e6c2c943d5d63d18f'
TOPIC_BRIDGE_FEE_UPDATED           = '\x4fc4e10a6b18b18a9b637c4c543c7bc1d0759966d577ac6a9f4bbfaf678862f4'
TOPIC_SET_DAPP_METADATA            = '\x1ff6cbf099d2cd90494426a312eae3d52a88116b0ee9f37e074072a79a233489'
-- ===== AssetBridge / Voyager topics =====
TOPIC_TOKEN_TRANSFER               = '\x0a9a968c7c6cc6182a9339c64cb833f1fa34f5a5275c3e3cad13f5db1c6b82a8'
TOPIC_TOKEN_TRANSFER_WITH_INSTR    = '\x220aec4438bd2c268e817da97e3b821192adc2c11dfea86d51d6ffd8bf38de6e'
TOPIC_DEPOSIT_REVERTED             = '\xc6cb37798db6a3c249b500abfed1b5787f96457834af95a59170a58e1874e51c'
TOPIC_EXECUTE                      = '\xb937c701be72296797de30f67fec8bc6c096aa6b4c1850a5e659a0dc17165d8f'
TOPIC_EXECUTE_WITH_MESSAGE         = '\x2c661efd5bbbd239384997a4afc5e16ba28d1cfdf0c6fe2318ffee919ac79abf'
-- ===== Upgrade =====
TOPIC_UPGRADED                     = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'

-- ===== Gateway selectors =====
SEL_ISEND                          = '\x7bed470a'
SEL_GW_IRECEIVE                    = '\x44bdf5a7'
SEL_GW_IACK                        = '\x2205643a'
SEL_UPDATE_VALSET                  = '\x3bcced29'
SEL_SET_DAPP_METADATA              = '\xef15cbda'
SEL_SET_BRIDGE_FEES                = '\xea76f6d7'
SEL_CURRENT_VERSION                = '\x9d888e86'   -- role probe: answers on Gateway
-- ===== AssetBridge selectors =====
SEL_TRANSFER_TOKEN                 = '\x63d42ae7'
SEL_TRANSFER_TOKEN_WITH_INSTR      = '\x8121165f'
SEL_SWAP_AND_TRANSFER_TOKEN        = '\x751657d7'
SEL_SWAP_AND_TRANSFER_WITH_INSTR   = '\x07927ded'
-- ===== UUPS =====
SEL_UPGRADE_TO_AND_CALL            = '\x4f1ef286'
SEL_PROXIABLE_UUID                 = '\x52d1902d'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT                  = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT                 = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Gateway addresses (ROLE FLIPS PER CHAIN) =====
ETH_GATEWAY                        = '\x86dfc31d9cb3280ee1eb1096caa9fc66299af973'   -- ETH/Base/BNB/OP = Gateway proxy
BASE_GATEWAY                       = '\x86dfc31d9cb3280ee1eb1096caa9fc66299af973'
BNB_GATEWAY                        = '\x86dfc31d9cb3280ee1eb1096caa9fc66299af973'
OP_GATEWAY                         = '\x86dfc31d9cb3280ee1eb1096caa9fc66299af973'
ETH_GATEWAY_IMPL                   = '\xac589f48f94134db8671acd31f4da55ce43e318c'
AVAX_GATEWAY                       = '\xc21e4ebd1d92036cb467b53fe3258f219d909eb9'   -- Avax/Arb = Gateway proxy
ARB_GATEWAY                        = '\xc21e4ebd1d92036cb467b53fe3258f219d909eb9'
AVAX_ARB_GATEWAY_IMPL              = '\x86dfc31d9cb3280ee1eb1096caa9fc66299af973'
POLYGON_GATEWAY                    = '\x21c1e74caadf990e237920d5515955a024031109'   -- Polygon = Gateway proxy
POLYGON_GATEWAY_IMPL               = '\x5b97f51c9f5ca8a6ea5e44570aaa09d17c8ab824'
POLYGON_GATEWAY_LOGIC              = '\xc21e4ebd1d92036cb467b53fe3258f219d909eb9'
-- ===== AssetBridge / Voyager (ETH / Avax / Arb only) =====
ASSETBRIDGE                        = '\xf0773508c585246bd09bfb401aa18b72685b03f9'   -- ETH/Avax/Arb; absent Base/BNB/OP/Polygon
```

---

## 8. Verification & sources

How the constants were verified (2026-06-09):
- **Topic0 / selectors** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from `GatewayUpgradeable.sol`, `Utils.sol` (struct layouts for `iReceive`/`iAck`), and `AssetBridgeUpgradeable.sol` / `IAssetBridge.sol`. Gateway selectors (`iSend`/`currentVersion`/`setDappMetadata`/`updateValset`) verified present in the live ETH impl `0xac589f48…` (PUSH4 scan); AssetBridge selectors (`transferToken`/`swapAndTransferToken`/`depositNonce`) verified present in the live Avax `0xf0773508…`.
- **Addresses & roles** existence-checked via `eth_getCode`, role confirmed by `eth_call currentVersion()` (Gateway) vs `transferToken`/`depositNonce` presence (AssetBridge). Gateway proxy pattern read from the EIP-1967 impl slot (populated → proxy) and admin slot (empty → UUPS). Contract names (`GatewayUpgradeable`, `AssetBridge`) read from the Routescan `getsourcecode` API on Avalanche (43114).
- **Chain coverage:** all seven chains probed; Gateway present on all seven, AssetBridge only on ETH/Avax/Arb (Base/BNB/OP/Polygon return `0x`).

Authoritative sources:
- Canonical contracts: [`router-protocol/router-contracts`](https://github.com/router-protocol/router-contracts) — `gateway/evm/contracts/GatewayUpgradeable.sol`, `Utils.sol`, `asset-bridge/evm/contracts/AssetBridgeUpgradeable.sol`, `IAssetBridge.sol`.
- Docs: [Router CrossTalk / Message transfer](https://docs.routerprotocol.com/develop/message-transfer-via-crosstalk/) · [Nitro high-level workflow](https://docs.routerprotocol.com/develop/asset-transfer-via-nitro/high-level-workflow/).
- Explorers: [Snowscan Gateway proxy `0xC21e4ebD`](https://snowscan.xyz/address/0xC21e4ebD1d92036Cb467b53fE3258F219d909Eb9) · [Etherscan Gateway `0x86dfc31d`](https://etherscan.io/address/0x86dfc31d9cb3280ee1eb1096caa9fc66299af973) · [Snowscan AssetBridge `0xf0773508`](https://snowscan.xyz/address/0xf0773508c585246bd09bfb401aa18b72685b03f9).
