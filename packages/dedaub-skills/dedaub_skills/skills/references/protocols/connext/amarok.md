# Connext Amarok — Topics, Selectors, Addresses (Ethereum, Base, BNB, Arbitrum, Optimism, Polygon)

**Status:** verified against live RPC on every listed chain and the canonical `connext/monorepo` repo on 2026-06-09.
**Scope:** the original **Connext Amarok** cross-chain bridge — a single **EIP-2535 Diamond** (`ConnextDiamond`) per chain holding all bridge logic in facets (`BridgeFacet` for `xcall`/`execute`, `RoutersFacet` for liquidity), plus the canonical token registry / xERC20 surface. Topics and selectors are chain-agnostic; addresses are network-specific. Connext rebranded to **Everclear** and Amarok bridging has effectively been superseded by the Everclear intent layer — see [core.md](core.md). The Amarok Diamond remains deployed and was still emitting `XCalled`/`execute` into **late 2025** (last `xcall`/`xcallIntoLocal` ~Aug 2025, last `execute` ~Sep 2025), now largely dormant.

Amarok is **upgradeable via the Diamond standard (EIP-2535)**, not EIP-1967: there is no single implementation slot — function selectors are routed to per-function **facet** addresses recorded in diamond storage at slot `keccak256("diamond.standard.diamond.storage")`. `eth_getCode` on the Diamond returns a small (~4.9 kB) dispatcher; reading the EIP-1967 impl slot returns `0x0` (it is NOT an EIP-1967 proxy). Each chain hosts an **independent Diamond at a different address** (no shared CREATE2 vanity), governed by a **different per-chain owner Safe**. Connext uses **Nomad/Connext "domain" IDs** (e.g. Ethereum = 6648936, the ASCII of "eth"), which differ from both chainId and from Everclear's Hyperlane domains — read `domain()` to confirm which chain a Diamond serves.

> **Not deployed on Avalanche.** No Amarok `ConnextDiamond` exists on Avalanche C-Chain (43114) at any known Connext address (`eth_getCode` = `0x`), even though Avalanche *is* a configured Connext domain (`1635148152`) in `connext/chaindata`. Of the seven requested chains, Amarok lives on **six: Ethereum, Base, BNB, Arbitrum, Optimism, Polygon**. Counterparty chains outside the seven that Amarok also connected include **Gnosis (100), Linea (59144), Mantle (5000), Metis (1088), Moonbeam (1284)** (per `connext/chaindata`).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak on 2026-06-09 from the canonical `BridgeFacet.sol`/`RoutersFacet.sol`/`DiamondCutFacet.sol` in `connext/monorepo`. `XCalled` additionally confirmed against **19 live `XCalled` logs** on the Ethereum Diamond near block `0x15c3da1` (~Aug 2025). The `TransferInfo` and `ExecuteArgs` tuples are the load-bearing detail — getting their field order wrong yields the wrong topic0.

`TransferInfo` tuple = `(uint32,uint32,uint32,address,address,bool,bytes,uint256,address,uint256,uint256,uint256,bytes32)`
`ExecuteArgs` tuple  = `(TransferInfo,address[],bytes[],address,bytes)`

### 1.1 BridgeFacet (emits all bridge activity) — facet `0x3606b0d9C84224892C7407d4e8DcFd7E9e2126A2` (ETH)

| topic0 | Event |
|--------|-------|
| `0xed8e6ba697dd65259e5ce532ac08ff06d1a3607bcec58f8f0937fe36a5666c54` | `XCalled(bytes32 indexed transferId, uint256 indexed nonce, bytes32 indexed messageHash, TransferInfo params, address asset, uint256 amount, address local, bytes messageBody)` |
| `0x0b07a8b0b083f8976b3c832b720632f49cb8ba1e7a99e1b145f51a47d3391cb7` | `Executed(bytes32 indexed transferId, address indexed to, address indexed asset, ExecuteArgs args, address local, uint256 amount, address caller)` |
| `0xb1a4ab59facaedd6d3a71da3902e0a1fa5b99750c0e20cd878334378a41cb335` | `ExternalCalldataExecuted(bytes32 indexed transferId, bool success, bytes returnData)` |
| `0xa818004004fc748e4542a84721887ca33c91a804807a31d07bdd2e844f317264` | `Reconciled(bytes32 indexed transferId, uint32 indexed originDomain, address indexed local, address[] routers, uint256[] amounts, address caller)` *(emitted by `InboxFacet`/`Reconcile`)* |
| `0xf90d3aafcedf55a0da208dd26d915e0ce1870ee9221586012487a0b366106f65` | `TransferRelayerFeesIncreased(bytes32 indexed transferId, uint256 increase, address asset, address caller)` |
| `0xb243c3cea6cd1bbfd64d5d0765f13734ca7b87fdf14e017391fe12a8891434ca` | `SlippageUpdated(bytes32 indexed transferId, uint256 slippage)` |

> The `Reconciled` topic0 was recomputed from the canonical signature; its exact arg list (`address[] routers, uint256[] amounts`) is the InboxFacet form. `XCalled`/`Executed`/`ExternalCalldataExecuted`/`TransferRelayerFeesIncreased`/`SlippageUpdated` are the BridgeFacet workhorses.

### 1.2 RoutersFacet (liquidity provider accounting) — facet `0xbe8D8AC9a44fbA6Cb7A7e02C1e6576E06C7Da72d` (ETH)

| topic0 | Event |
|--------|-------|
| `0xcc3100122c1752fe0f6bfa5503175bc53eb00b5f2d774e81efedcd2b10a6d24b` | `RouterLiquidityAdded(address indexed router, address local, bytes32 canonicalId, uint256 amount, address caller)` |
| `0x63cea637caf2479bad0e90a93268f6d8a1ad69961b1ee8112586091e09ae0ec3` | `RouterLiquidityRemoved(address indexed router, address to, address local, uint256 amount, address caller)` |

### 1.3 DiamondCutFacet / OwnershipFacet (governance)

| topic0 | Event |
|--------|-------|
| `0x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673` | `DiamondCut((address,uint8,bytes4[])[] _diamondCut, address _init, bytes _calldata)` — **watch for facet upgrades** |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address indexed previousOwner, address indexed newOwner)` |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

Selectors recomputed locally. `xcall`/`xcallIntoLocal`/`execute`/`addRouterLiquidity` confirmed **routed to a facet** via live `facetAddress(selector)` calls on the Ethereum Diamond (e.g. `facetAddress(0x63e3e7d2)` → BridgeFacet `0x3606b0d9…`).

### 2.1 BridgeFacet — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x8aac16ba` | `xcall(uint32 destination, address to, address asset, address delegate, uint256 amount, uint256 slippage, bytes callData)` | Origin entrypoint → emits `XCalled`. Routed to BridgeFacet `0x3606b0d9…`. |
| `0x91f5de79` | `xcallIntoLocal(uint32 destination, address to, address asset, address delegate, uint256 amount, uint256 slippage, bytes callData)` | Deliver local (nextAsset) on dest, no swap. |
| `0x63e3e7d2` | `execute(ExecuteArgs args)` → `bytes32` | Destination settlement (fast-liquidity router fill or slow reconciled). Emits `Executed`. **Verified routes to BridgeFacet `0x3606b0d9…`.** |
| `0x2424401f` | `bumpTransfer(bytes32 transferId)` | Top up relayer fee (native). |
| `0x59efa162` | `bumpTransfer(bytes32 transferId, address asset, uint256 amount)` | Top up relayer fee (token). |
| `0x54126711` | `forceUpdateSlippage(TransferInfo params, uint256 slippage)` | Delegate-only, dest-side slippage override. Emits `SlippageUpdated`. |

### 2.2 RoutersFacet — router liquidity

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x54064594` | `addRouterLiquidity(uint256 amount, address local)` | Emits `RouterLiquidityAdded`. **Verified routes to RoutersFacet `0xbe8D8AC9…`.** |
| `0x2d3f9ef6` | `addRouterLiquidityFor(uint256 amount, address local, address router)` | Add on behalf of a router. |
| `0x242e8f5d` | `removeRouterLiquidity((uint32,bytes32) canonical, address to, address router)` | Emits `RouterLiquidityRemoved`. |
| `0x50919021` | `removeRouterLiquidityFor((uint32,bytes32) canonical, address to, address router, address _router)` | |
| `0x41258b5c` | `routerBalances(address router, address asset)` → `uint256` | View — per-router liquidity. |

### 2.3 DiamondCutFacet / DiamondLoupe / Ownership / views

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x1f931c1c` | `diamondCut((address,uint8,bytes4[])[] _cut, address _init, bytes _calldata)` | **Facet upgrade** — emits `DiamondCut`. |
| `0x7a0ed627` | `facets()` → `(address,bytes4[])[]` | Loupe: all facets (ETH Diamond has **13 facets**). |
| `0xcdffacc6` | `facetAddress(bytes4 selector)` → `address` | Loupe: which facet handles a selector. |
| `0xc2fb26a6` | `domain()` → `uint256` | Connext/Nomad domain ID (ETH = 6648936). |
| `0x8da5cb5b` | `owner()` → `address` | Per-chain governance Safe. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. `domain()` = **6648936**, `owner()` = `0x4d50a469fC788a3c0CDC8fd67868877dCB246625`.

| Role | Address | One-liner |
|------|---------|-----------|
| **ConnextDiamond** (EIP-2535) | `0x8898B472C54c31894e3B9bb83cEA802a5d0e63C6` | Single bridge entrypoint; emits all §1 events. 13 facets. ~4 907 B dispatcher. |
| BridgeFacet | `0x3606b0d9C84224892C7407d4e8DcFd7E9e2126A2` | Handles `xcall`/`xcallIntoLocal`/`execute`/`bumpTransfer`/`forceUpdateSlippage`. |
| RoutersFacet | `0xbe8D8AC9a44fbA6Cb7A7e02C1e6576E06C7Da72d` | `addRouterLiquidity`/`removeRouterLiquidity`. |
| Owner (governance) | `0x4d50a469fC788a3c0CDC8fd67868877dCB246625` | Diamond `owner()` (Connext multisig). |
| **CLEAR / Everclear token** (proxy) | `0x58b9cb810A68a7f3e1E4f8Cb45D1B9B3c79705E8` | ERC-20 governance token "Everclear" (symbol `CLEAR`); upgradeable, impl `0x8d9a1606b12aedd7469d154149d66e3418ef890c`. |

The 13 ETH facets (from live `facets()`): `0xe37d4f73…`, `0x3606b0d9…` (Bridge), `0x5ccd2537…`, `0x086b5a16…`, `0x7993bb17…`, `0xccb64fdf…`, `0xbe8d8ac9…` (Routers), `0x9ab5f562…`, `0x6369f971…`, `0x324c5834…`, `0x44e799f4…`, `0x3bcf4185…`, `0x49f194ea…`. Facet addresses are upgrade-mutable via `diamondCut`; **always read `facetAddress(selector)` live rather than hard-coding a facet.**

---

## 4. Addresses — Base (chain ID 8453)

Verified via `eth_getCode` on `https://base-rpc.publicnode.com`. `domain()` = **1650553709**, `owner()` = `0xf08e14FC36a874BEB16ab66100faB7fAFc3C8d54`.

| Role | Address |
|------|---------|
| **ConnextDiamond** | `0xB8448C6f7f7887D36DcA487370778e419e9ebE3F` (~4 860 B dispatcher) |
| Owner | `0xf08e14FC36a874BEB16ab66100faB7fAFc3C8d54` |

CLEAR token is **NOT** at the ETH vanity on Base (`0x58b9cb81…` returns `0x`). Facets are Base-specific addresses — read `facets()` live.

## 5. Addresses — BNB Smart Chain (chain ID 56)

Verified via `eth_getCode` on `https://bsc-rpc.publicnode.com`. `domain()` = **6450786**, `owner()` = `0x9435bA7C661a0Fd477DEeD640491de8c100325A7`.

| Role | Address |
|------|---------|
| **ConnextDiamond** | `0xCd401c10afa37d641d2F594852DA94C700e4F2CE` (~4 907 B) |
| Owner | `0x9435bA7C661a0Fd477DEeD640491de8c100325A7` |
| CLEAR token (OFT) | `0x58b9cb810A68a7f3e1E4f8Cb45D1B9B3c79705E8` (present, 1 356 B proxy) |

## 6. Addresses — Arbitrum One (chain ID 42161)

Verified via `eth_getCode` on `https://arbitrum-one-rpc.publicnode.com`. `domain()` = **1634886255**, `owner()` = `0x5C711db90DEC0a5B81C626968DEa4187a7f9c1f2`.

| Role | Address |
|------|---------|
| **ConnextDiamond** | `0xEE9deC2712cCE65174B561151701Bf54b99C24C8` (~4 907 B) |
| Owner | `0x5C711db90DEC0a5B81C626968DEa4187a7f9c1f2` |
| CLEAR token (OFT) | `0x58b9cb810A68a7f3e1E4f8Cb45D1B9B3c79705E8` (present, 1 356 B proxy) |

## 7. Addresses — Optimism (chain ID 10)

Verified via `eth_getCode` on `https://optimism-rpc.publicnode.com`. `domain()` = **1869640809**, `owner()` = `0x6eCED04DDC5A7709d5877c963cEd0288Fb1C7348`.

| Role | Address |
|------|---------|
| **ConnextDiamond** | `0x8f7492DE823025b4CfaAB1D34c58963F2af5DEDA` (~4 907 B) |
| Owner | `0x6eCED04DDC5A7709d5877c963cEd0288Fb1C7348` |
| CLEAR token (OFT) | `0x58b9cb810A68a7f3e1E4f8Cb45D1B9B3c79705E8` (present, 1 356 B proxy) |

## 8. Addresses — Polygon PoS (chain ID 137)

Verified via `eth_getCode` on `https://polygon-bor-rpc.publicnode.com`. `domain()` = **1886350457**, `owner()` = `0x0970Adeb473609F91D03e9Bba85f49C445040cd7`.

| Role | Address |
|------|---------|
| **ConnextDiamond** | `0x11984dc4465481512eb5b777E44061C158CF2259` (~4 907 B) |
| Owner | `0x0970Adeb473609F91D03e9Bba85f49C445040cd7` |
| CLEAR token (OFT) | `0x58b9cb810A68a7f3e1E4f8Cb45D1B9B3c79705E8` (present, 1 356 B proxy) |

## 9. Addresses — Avalanche C-Chain (chain ID 43114)

**No Amarok ConnextDiamond.** `eth_getCode` = `0x` for every known Connext Diamond address on `https://avalanche-c-chain-rpc.publicnode.com`. Avalanche is a registered Connext domain (`1635148152`) but the Amarok core was not deployed there. CLEAR token is also absent on Avalanche.

---

## 10. Cross-chain summary

| Chain | ID | Nomad domain | ConnextDiamond | Owner Safe | CLEAR token |
|---|---|---|---|---|---|
| **Ethereum** | 1 | 6648936 | `0x8898B472…BE63C6` | `0x4d50a469…` | ✅ `0x58b9cb81…` (canonical) |
| **Base** | 8453 | 1650553709 | `0xB8448C6f…9ebE3F` | `0xf08e14FC…` | ❌ |
| **BNB** | 56 | 6450786 | `0xCd401c10…e4F2CE` | `0x9435bA7C…` | ✅ (OFT) |
| **Arbitrum** | 42161 | 1634886255 | `0xEE9deC27…9C24C8` | `0x5C711db9…` | ✅ (OFT) |
| **Optimism** | 10 | 1869640809 | `0x8f7492DE…5DEDA` | `0x6eCED04D…` | ✅ (OFT) |
| **Polygon** | 137 | 1886350457 | `0x11984dc4…CF2259` | `0x0970Adeb…` | ✅ (OFT) |
| **Avalanche** | 43114 | 1635148152 | ❌ `0x` | — | ❌ |

**No shared vanity address** for the Diamond — every chain's Diamond and owner Safe is distinct (unlike the Everclear Spoke, which is vanity-shared). Key on `(chainId, address)`. The **CLEAR token** is the only contract that re-uses one literal (`0x58b9cb81…`) across chains, and even that is absent on Base + Avalanche.

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **ConnextDiamond** | **Diamond (EIP-2535)** | EIP-1967 impl slot `0x3608…bbc` = `0x0`; selectors routed via diamond storage at `keccak256("diamond.standard.diamond.storage")` = `0xc8fcad8db84d3cc18b4c41d551ea0ee66dd599cde068d998e57d5e09332c131c`; `facets()`/`facetAddress()` loupe present. ~4.9 kB dispatcher bytecode. | `owner()` (per-chain Safe) via `diamondCut` → emits `DiamondCut` topic `0x8faa7087…`. |
| BridgeFacet / RoutersFacet / 11 others | **Facet (logic, no storage of its own)** | Plain logic contracts; addresses listed by `facets()`. Not independently upgradeable — replaced wholesale by `diamondCut`. | Diamond owner. |
| **CLEAR / Everclear token** | **EIP-1967 proxy** | impl slot `0x3608…bbc` = `0x8d9a1606b12aedd7469d154149d66e3418ef890c` (ETH). | Token owner. |

**The Diamond is NOT an EIP-1967 proxy** — confirmed by an empty impl slot on all six chains. To track upgrades, watch the **`DiamondCut` event** (`0x8faa7087…`), not `Upgraded`. There is no single "implementation" to read; resolve logic per selector via `facetAddress(selector)`.

---

## 12. Detection invariants & gotchas

1. **Amarok is legacy / dormant.** The Diamond still exists on six chains but `XCalled`/`Executed` activity tapered to ~zero through late 2025 as flow moved to the Everclear intent layer ([core.md](core.md)). Confirm liveness by scanning `XCalled` (`0xed8e6ba6…`) — recent windows return 0.
2. **EIP-2535 Diamond, not EIP-1967.** Don't read an impl slot (it's `0x0`). Track upgrades via `DiamondCut`; resolve a selector's logic via `facetAddress()`. Facet addresses are upgrade-mutable — never hard-code them.
3. **`TransferInfo`/`ExecuteArgs` tuple order is load-bearing** for the `XCalled`/`Executed`/`execute` hashes. `TransferInfo` = `(uint32,uint32,uint32,address,address,bool,bytes,uint256,address,uint256,uint256,uint256,bytes32)`; getting it wrong changes topic0/selector.
4. **`XCalled` has three indexed topics**: `transferId`, `nonce`, `messageHash`. The **`transferId`** (topic1) is the cross-chain correlation key — it matches the `transferId` indexed on the destination `Executed`.
5. **`Executed` fires on the destination** for both fast (router-fronted) and slow (reconciled) paths. The real recipient is the indexed `to` (topic1); `caller` is a relayer/router, not the user. Attribute to `to`, never `tx.from`.
6. **Connext/Nomad domain IDs ≠ chainId ≠ Everclear domain.** ETH = 6648936 ("eth"), Base = 1650553709, BNB = 6450786, etc. Read `domain()`. The `XCalled.params.destinationDomain` is a Nomad domain, not a chainId.
7. **No shared Diamond address & a different owner Safe per chain.** Key everything on `(chainId, address)`; never assume one governance key.
8. **Routers front liquidity.** `RouterLiquidityAdded`/`Removed` track LP capital; `execute` consumes router balances for fast transfers. `routerBalances(router, asset)` is the live accounting.
9. **CLEAR token is shared-address but partial.** `0x58b9cb81…` is present on ETH (canonical, upgradeable) and as an OFT on BNB/Arb/OP/Polygon, **absent on Base and Avalanche**. It is the Everclear governance token, not a bridge-wrapped asset.
10. **Not on Avalanche.** Every Amarok core address returns `0x` on Avalanche despite it being a configured domain. Record as "not deployed here."

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_XCALLED                  = '\xed8e6ba697dd65259e5ce532ac08ff06d1a3607bcec58f8f0937fe36a5666c54'
TOPIC_EXECUTED                 = '\x0b07a8b0b083f8976b3c832b720632f49cb8ba1e7a99e1b145f51a47d3391cb7'
TOPIC_EXTERNAL_CALLDATA_EXEC   = '\xb1a4ab59facaedd6d3a71da3902e0a1fa5b99750c0e20cd878334378a41cb335'
TOPIC_RECONCILED               = '\xa818004004fc748e4542a84721887ca33c91a804807a31d07bdd2e844f317264'
TOPIC_RELAYER_FEES_INCREASED   = '\xf90d3aafcedf55a0da208dd26d915e0ce1870ee9221586012487a0b366106f65'
TOPIC_SLIPPAGE_UPDATED         = '\xb243c3cea6cd1bbfd64d5d0765f13734ca7b87fdf14e017391fe12a8891434ca'
TOPIC_ROUTER_LIQUIDITY_ADDED   = '\xcc3100122c1752fe0f6bfa5503175bc53eb00b5f2d774e81efedcd2b10a6d24b'
TOPIC_ROUTER_LIQUIDITY_REMOVED = '\x63cea637caf2479bad0e90a93268f6d8a1ad69961b1ee8112586091e09ae0ec3'
TOPIC_DIAMOND_CUT              = '\x8faa70878671ccd212d20771b795c50af8fd3ff6cf27f4bde57e5d4de0aeb673'
TOPIC_OWNERSHIP_TRANSFERRED    = '\x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0'
TOPIC_PAUSED                   = '\x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752'
TOPIC_UNPAUSED                 = '\xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933'

-- ===== Selectors =====
SEL_XCALL                      = '\x8aac16ba'
SEL_XCALL_INTO_LOCAL           = '\x91f5de79'
SEL_EXECUTE                    = '\x63e3e7d2'
SEL_BUMP_TRANSFER              = '\x2424401f'
SEL_BUMP_TRANSFER_ASSET        = '\x59efa162'
SEL_FORCE_UPDATE_SLIPPAGE      = '\x54126711'
SEL_ADD_ROUTER_LIQUIDITY       = '\x54064594'
SEL_REMOVE_ROUTER_LIQUIDITY    = '\x242e8f5d'
SEL_DIAMOND_CUT                = '\x1f931c1c'
SEL_FACETS                     = '\x7a0ed627'
SEL_FACET_ADDRESS              = '\xcdffacc6'
SEL_DOMAIN                     = '\xc2fb26a6'

-- ===== Diamond storage slot =====
DIAMOND_STORAGE_SLOT           = '\xc8fcad8db84d3cc18b4c41d551ea0ee66dd599cde068d998e57d5e09332c131c'

-- ===== Diamonds (per-chain, NO shared vanity) =====
ETH_DIAMOND   = '\x8898b472c54c31894e3b9bb83cea802a5d0e63c6'
BASE_DIAMOND  = '\xb8448c6f7f7887d36dca487370778e419e9ebe3f'
BNB_DIAMOND   = '\xcd401c10afa37d641d2f594852da94c700e4f2ce'
ARB_DIAMOND   = '\xee9dec2712cce65174b561151701bf54b99c24c8'
OP_DIAMOND    = '\x8f7492de823025b4cfaab1d34c58963f2af5deda'
POLY_DIAMOND  = '\x11984dc4465481512eb5b777e44061c158cf2259'
-- Avalanche: NOT DEPLOYED (eth_getCode = 0x)

-- ===== ETH facets (upgrade-mutable; read facets() live) =====
ETH_BRIDGE_FACET   = '\x3606b0d9c84224892c7407d4e8dcfd7e9e2126a2'
ETH_ROUTERS_FACET  = '\xbe8d8ac9a44fba6cb7a7e02c1e6576e06c7da72d'

-- ===== Owners (per chain) =====
ETH_OWNER  = '\x4d50a469fc788a3c0cdc8fd67868877dcb246625'
BASE_OWNER = '\xf08e14fc36a874beb16ab66100fab7fafc3c8d54'
BNB_OWNER  = '\x9435ba7c661a0fd477deed640491de8c100325a7'
ARB_OWNER  = '\x5c711db90dec0a5b81c626968dea4187a7f9c1f2'
OP_OWNER   = '\x6eced04ddc5a7709d5877c963ced0288fb1c7348'
POLY_OWNER = '\x0970adeb473609f91d03e9bba85f49c445040cd7'

-- ===== CLEAR / Everclear token (shared literal; absent on Base+Avax) =====
CLEAR_TOKEN = '\x58b9cb810a68a7f3e1e4f8cb45d1b9b3c79705e8'
```

---

## 14. Verification & sources

How constants were verified (2026-06-09):
- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from `BridgeFacet.sol`, `RoutersFacet.sol`, `DiamondCutFacet.sol` and `LibConnextStorage.sol` (`TransferInfo`/`ExecuteArgs`) in `connext/monorepo`. `XCalled` (`0xed8e6ba6…`) cross-checked against **19 live `XCalled` logs** on the Ethereum Diamond near block `0x15c3da1`. Selectors `xcall`/`xcallIntoLocal`/`execute`/`addRouterLiquidity` confirmed by live `facetAddress(selector)` calls resolving to the BridgeFacet/RoutersFacet.
- **Addresses + facets:** Diamond addresses from the Connext deployments registry / docs, existence-checked via `eth_getCode` on each chain's publicnode RPC. ETH facet set read live via `facets()` (13 facets). `domain()` and `owner()` read live per chain. Avalanche confirmed absent (`eth_getCode` = `0x`).
- **Proxy classification:** EIP-1967 impl slot read live on every Diamond → `0x0` (not EIP-1967); diamond standard storage slot derived as `keccak256("diamond.standard.diamond.storage")`. CLEAR token impl read from the EIP-1967 slot (`0x8d9a1606…` on ETH).
- **Chain coverage:** Connext domain table from `connext/chaindata` `crossChain.json` (lists Avalanche as a domain even though the Amarok core is absent there); counterparty chains outside the seven (Gnosis, Linea, Mantle, Metis, Moonbeam) noted from the same source.

Authoritative sources:
- Canonical repo: [`connext/monorepo`](https://github.com/connext/monorepo) — `packages/deployments/contracts` (facets, `LibConnextStorage`), `connext/chaindata` (`crossChain.json`).
- Docs: [Connext deployments](https://docs.connext.network/resources/deployments) · [Everclear docs](https://docs.everclear.org).
- Explorers: [Etherscan ConnextDiamond](https://etherscan.io/address/0x8898B472C54c31894e3B9bb83cEA802a5d0e63C6) · [Etherscan CLEAR token](https://etherscan.io/address/0x58b9cb810a68a7f3e1e4f8cb45d1b9b3c79705e8).
