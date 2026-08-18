# Avalanche Bridge — BTC.b — Topics, Selectors, Addresses (Avalanche C-Chain only; Bitcoin + CCIP counterparties)

**Status:** verified against live Avalanche C-Chain RPC (`https://avalanche-c-chain-rpc.publicnode.com`) and all six other target-chain RPCs, the on-chain verified source (`BridgeToken` / `BridgeTokenAdapter` on Snowtrace/Routescan), and recomputed keccak256 locally, on 2026-06-09.
**Scope:** the Avalanche-side contracts that mint, burn and govern **BTC.b** (`symbol()="BTC.b"`, `name()="Bitcoin"`, 8 decimals) — the canonical wrapped-Bitcoin token of the Avalanche Bridge. Event topics and function selectors are **chain-agnostic**; addresses are network-specific. **BTC.b is a single-chain minted token: it exists ONLY on Avalanche C-Chain (43114).** The Bitcoin side is non-EVM (no contract); the modern mint/burn path is additionally wired to **Chainlink CCIP** for EVM↔EVM transfers (counterparties outside the seven target chains — see §9).

BTC.b is a non-upgradeable `BridgeToken` (ERC-20, solc 0.8.11) deployed by the original Avalanche Bridge warden EOA `0xf5163f69…`. The token itself is **immutable** (no proxy — EIP-1967 impl/admin slots both read `0x0`); its only mutable surface is a single `Roles.Role bridgeRoles` allow-list that gates `mint`. The mint authority has been **migrated exactly once** (`MigrateBridgeRole`, block 76740088) from the original warden EOA to a **`BridgeTokenAdapter`** (a Lombard-consortium-style minter behind a `TransparentUpgradeableProxy` at `0x85d1d52e…`). So today: wardens / CCIP relayers prove a deposit → the adapter (or its `MINTER_ROLE` holders) calls `BridgeToken.mint` → BTC.b is minted; a holder calls `BridgeToken.unwrap` (or burns) to redeem back to native Bitcoin or bridge out via CCIP.

> **The one fact a monitoring engineer must internalize:** BTC.b's mint event is **`Mint(address,uint256,address,uint256,bytes32,uint256)`** (topic0 `0xc5532043…`) — a **6-field, fully NON-indexed** event (the log has exactly **one topic**, topic0, and all six fields live in `data`). It is NOT the OpenZeppelin `Mint(address,uint256)`. `originChainId` (last field) is **`0`** for native-Bitcoin mints and `type(uint256).max` (all-`FF`) for the CCIP-bridged path. `originTxId` (field 5) is the **Bitcoin transaction hash** for native mints. There is **no `Burn` event** — redemptions emit `Unwrap(uint256,uint256)` (topic0 `0x37a06799…`, also non-indexed) plus an ERC-20 `Transfer` to `0x0`.

---

## 0. Contract families & versions

| Contract | Role | Proxy? | Verified name on chain |
|----------|------|--------|------------------------|
| **BTC.b token** | The ERC-20 wrapped-Bitcoin token. Holds `mint`/`unwrap`/`burn` + the `bridgeRoles` allow-list. | **No** (10 032 B immutable) | `BridgeToken` (solc 0.8.11) |
| **BridgeTokenAdapter** (minter) | Current sole holder of BTC.b's `bridgeRoles`. Consortium/Bascule-gated minter (Lombard-style: `mintV1`, `batchMint`, `RedeemRequest`, `MintProofConsumed`). Calls `BridgeToken.mint`. | **Transparent (EIP-1967)** proxy `0x85d1d52e…` → impl `0x80A23cB6…` | `BridgeTokenAdapter` (solc 0.8.24) |
| **ProxyAdmin** | Owns/upgrades the adapter proxy. | **No** (1 063 B) | `ProxyAdmin` |
| **TimelockController** | `defaultAdmin`/`owner` of the adapter **and** owner of the ProxyAdmin — root governance. | **No** (6 712 B) | `TimelockController` |
| **Consortium** | Off-chain notary set whose threshold signatures the adapter verifies before minting (`getConsortium()`). | Transparent proxy `0xdad58dfa…` | (Lombard Consortium) |
| **BasculeV2** | Deposit-attestation gate the adapter consults (`getBascule()`). | **No** (5 452 B) | `BasculeV2` |
| **BridgeTokenPool** | Chainlink-CCIP token pool (`LombardTokenPoolV2 1.6.1`) that locks/burns on send and releases/mints on receive across CCIP lanes. | **No** | `BridgeTokenPool` |

The **original warden model** (mint called directly by an EOA holding `bridgeRoles`) and the **current adapter model** are the same `BridgeToken` contract — only the `bridgeRoles` bearer changed. There are **no version-numbered token redeploys**; hence this single `core.md`.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 BTC.b token (`BridgeToken`) — emitter `0x152b9d0F…3E50`

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xc5532043e6f3d77e1c320ff59bd4157ca9075ef59f6b55ceab6c3f7d2f78c9ca` | `Mint(address to, uint256 amount, address feeAddress, uint256 feeAmount, bytes32 originTxId, uint256 originChainId)` | **All six fields NON-indexed → log has 1 topic only.** `originChainId=0` = native Bitcoin; `=2^256-1` = CCIP path. `originTxId` = the source-chain tx (BTC txid for native). *(verified live: block 0x5381aa5 and block ~60M)* |
| `0x37a06799a3500428a773d00284aa706101f5ad94dae9ec37e1c3773aa54c3304` | `Unwrap(uint256 amount, uint256 chainId)` | Redemption / bridge-out. **Both fields non-indexed.** Paired with an ERC-20 `Transfer`→`0x0`. *(verified live)* |
| `0x871b00a4e20f8436702d0174eb87d84d7cd1dd5c34d4bb1b4e75438b3398d512` | `MigrateBridgeRole(address newBridgeRoleAddress)` | Mint authority handover. **Fired exactly once** (block 76740088 → `0x85d1d52e…`). Critical security signal. |
| `0x677e2d9a4ed9201aa86725fef875137fc53876e6b68036b974404762682bd122` | `AddSupportedChainId(uint256 chainId)` | New unwrap destination chain whitelisted. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | Standard ERC-20. Mint = `from 0x0`; burn/unwrap = `to 0x0`. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | Standard ERC-20. |

There is **no `Burn` event** and **no `Paused`/`Ownable` event** on the token — `BridgeToken` is not Pausable and not Ownable.

### 1.2 BridgeTokenAdapter (minter) — emitter `0x85d1d52e…`

The current minter is a Lombard-style AccessControl + DefaultAdminRules contract. Highest-value topics:

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x91f5c148b0f5ac9ddafe7030867f0d968adec49652c7ea760cf51fa233424b14` | `MintProofConsumed(address indexed recipient, bytes32 indexed payloadHash, bytes payload)` | A consortium-notarized mint was accepted (replay-protected by payloadHash). |
| `0x199445030f34ba18eca81d4647be9cf6943287dd1a58d150f9cf093111240bff` | `BatchMintSkipped(bytes32 payloadHash, bytes payload)` | A batch-mint entry was skipped (already consumed / invalid). |
| `0x792e146055c5e75c3931b639fa22380b6a8ad93500e091d3f326b63e84685cae` | `RedeemRequest(address fromAddress, uint256 totalAmount, uint256 amountAfterFee, uint256 redeemFee, bytes scriptPubkey)` | User requested redeem to a Bitcoin scriptPubkey (burn-side). |
| `0xa545dbdddcf62493f17ba255944610f297bfab9e7b856a748e16c20be81688ac` | `RedeemsForBtcEnabled(bool)` | Toggles whether native-BTC redemptions are open. |
| `0xcd0d4a9ad4b364951764307d0ae7b0d2ea482965b258e2e2452ef396c53b20f0` | `FeeCharged(uint256 fee, bytes userSignature)` | Mint/redeem fee taken. |
| `0x146dd8feba84cdc776f012478adc764591d6c0c9570adbc49ff09c648282a0a0` | `ConsortiumChanged(address oldVal, address newVal)` | Notary set rotated — **watch as admin/security signal**. |
| `0xa0317ebf02283589c190260fcd549e3a6de71bef31204aeb5417c07fb65c0894` | `BasculeChanged(address oldVal, address newVal)` | Attestation gate rotated. |
| `0xdd56718c8d1899f43e585ba9dd9904fbab0bfba720512545e82e0ffa6ae0f9da` | `BridgeTokenChanged(address oldVal, address newVal)` | The minted token pointer changed. |
| `0xf5f95b10b00195043307580900c3d9806c3fee7e80e71bc2d85302891605e200` | `AssetRouterChanged(address oldVal, address newVal)` | CCIP/asset-router pointer changed. |
| `0x4fc6e7a37aea21888550b60360992adb6a9b3b4da644d63e9f3a420c2d86e282` | `TreasuryAddressChanged(address oldVal, address newVal)` | Fee sink changed. |
| `0x2e7c1540076270015f38f524150bcb5d6ba9db14aca34c2e6d32e6ffad37941a` | `BurnCommissionChanged(uint64 prevValue, uint64 newValue)` | Burn fee changed. |
| `0x5fc463da23c1b063e66f9e352006a7fbe8db7223c455dc429e881a2dfe2f94f1` | `FeeChanged(uint256 oldFee, uint256 newFee)` | Mint/general fee changed. |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | `MINTER_ROLE` grants — **watch** (new minters added). |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | Minter removed. |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` | |
| `0x3377dc44241e779dd06afab5b788a35ca5f3b778836e2990bdb26a2a4b2e5ed6` | `DefaultAdminTransferScheduled(address indexed newAdmin, uint48 acceptSchedule)` | `DefaultAdminRules` 2-step admin handover begun — **root-key rotation signal**. |
| `0x8886ebfc4259abdbc16601dd8fb5678e54878f47b3c34836cfc51154a9605109` | `DefaultAdminTransferCanceled()` | |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` | `Paused(address account)` | Adapter is Pausable (the token is not). |
| `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Unpaused(address account)` | |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` | OZ initializer — fires on proxy init/re-init. |

### 1.3 BridgeTokenPool (Chainlink CCIP) — emitter `0x67927d7e…`

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xf33bc26b4413b0e7f19f1ea739fdf99098c0061f1f87d954b11f5293fad9ae10` | `LockedOrBurned(uint64 remoteChainSelector, address token, address sender, uint256 amount)` | Outbound CCIP transfer — BTC.b burned/locked on this chain. |
| `0xfc5e3a5bddc11d92c2dc20fae6f7d5eb989f056be35239f7de7e86150609abc0` | `ReleasedOrMinted(uint64 remoteChainSelector, address token, address sender, address recipient, uint256 amount)` | Inbound CCIP transfer — BTC.b released/minted to `recipient`. *(verified live in the recent mint tx)* |

> **CCIP `remoteChainSelector` is NOT an EVM chainId** — it is a Chainlink CCIP selector (e.g. Ethereum = `5009297550715157269`). Map it via the CCIP directory, not `chainId`.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 BTC.b token (`BridgeToken`) — full external surface

All 19 selectors below were cross-checked against the live contract's PUSH4 dispatcher (`eth_getCode` on `0x152b9d0F…`).

| Selector | Signature | Returns / notes |
|----------|-----------|------------------|
| `0xa888d914` | `mint(address to, uint256 amount, address feeAddress, uint256 feeAmount, bytes32 originTxId, uint256 originChainId)` | **Bridge mint.** `require(bridgeRoles.has(msg.sender))`. Emits `Mint` + `Transfer`(0x0→to) + a fee `Transfer` if `feeAmount>0`. |
| `0x6e286671` | `unwrap(uint256 amount, uint256 chainId)` | **Redeem / bridge-out.** Burns `amount` from caller, emits `Unwrap` + `Transfer`(→0x0). |
| `0x5d9898d3` | `migrateBridgeRole(address newBridgeRoleAddress)` | `require(bridgeRoles.has(msg.sender))`; removes caller, adds new. Emits `MigrateBridgeRole`. |
| `0x66de3b36` | `addSupportedChainId(uint256 chainId)` | Whitelists an unwrap destination. Emits `AddSupportedChainId`. |
| `0x21d93090` | `chainIds(uint256)` → `bool` | Public view: is this destination chainId supported. |
| `0x42966c68` | `burn(uint256 amount)` | ERC20Burnable — caller burns own balance (no `Unwrap`). |
| `0x79cc6790` | `burnFrom(address account, uint256 amount)` | ERC20Burnable with allowance. |
| `0xa9059cbb` | `transfer(address,uint256)` → `bool` | ERC-20. |
| `0x23b872dd` | `transferFrom(address,address,uint256)` → `bool` | ERC-20. |
| `0x095ea7b3` | `approve(address,uint256)` → `bool` | ERC-20. |
| `0x39509351` | `increaseAllowance(address,uint256)` → `bool` | |
| `0xa457c2d7` | `decreaseAllowance(address,uint256)` → `bool` | |
| `0xdd62ed3e` | `allowance(address,address)` → `uint256` | |
| `0x70a08231` | `balanceOf(address)` → `uint256` | |
| `0x18160ddd` | `totalSupply()` → `uint256` | = circulating BTC.b on Avalanche (8-dec; ≈ wrapped-BTC supply). |
| `0x06fdde03` | `name()` → `string` | `"Bitcoin"`. |
| `0x95d89b41` | `symbol()` → `string` | `"BTC.b"`. |
| `0x313ce567` | `decimals()` → `uint8` | `8` (NOT 18). |

There is **no `owner()`** (`owner()` reverts), **no `mint(address,uint256)`**, **no `pause()`** on the token.

### 2.2 BridgeTokenAdapter (minter) — key selectors

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address to, uint256 amount)` | Direct mint (gated by `MINTER_ROLE`). |
| `0x8307f738` | `mintV1(bytes payload, bytes proof)` | Consortium-proof mint (single). Emits `MintProofConsumed`. |
| `0x0fd3f6e5` | `batchMintV1(bytes[] payload, bytes[] proof)` | Batch proof-mint; emits `BatchMintSkipped` per skipped entry. |
| `0x68573107` | `batchMint(address[] to, uint256[] amount)` | Batch direct mint (MINTER_ROLE). |
| `0x9dc29fac` | `burn(address from, uint256 amount)` | Burn on behalf (CCIP/redeem). |
| `0x42966c68` | `burn(uint256 amount)` | Self-burn. |
| `0xe1c88f39` | `spendDeposit(bytes payload, bytes proof)` | Consume a Bascule-attested deposit. |
| `0xd5391393` | `MINTER_ROLE()` → `bytes32` | = `0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6`. |
| `0xe63ab1e9` | `PAUSER_ROLE()` → `bytes32` | |
| `0xa217fddf` | `DEFAULT_ADMIN_ROLE()` → `bytes32` | = `0x0`. |
| `0x91d14854` | `hasRole(bytes32,address)` → `bool` | Membership check. |
| `0x2f2ff15d` | `grantRole(bytes32,address)` | DEFAULT_ADMIN-only. Emits `RoleGranted`. |
| `0xd547741f` | `revokeRole(bytes32,address)` | Emits `RoleRevoked`. |
| `0x0434ea20` | `getConsortium()` → `address` | = `0xdad58dfa…`. |
| `0xaec64aac` | `getBascule()` → `address` | = `0x10fa7a47…`. |
| `0xfe9c6aa6` | `getAssetRouter()` → `address` | = `0x9ece5fb1…`. |
| `0x3b19e84a` | `getTreasury()` → `address` | = `0xaa4bc534…` (Gnosis Safe). |
| `0x170efac3` | `changeBridgeToken(address)` | Admin. Emits `BridgeTokenChanged`. |
| `0x56712139` | `changeConsortium(address)` | Admin. Emits `ConsortiumChanged`. |
| `0x7f56945e` | `changeBascule(address)` | Admin. Emits `BasculeChanged`. |
| `0x84ef8ffc` | `defaultAdmin()` → `address` | = `0xe4b5166b…` (Timelock). |
| `0x8456cb59` / `0x3f4ba83a` | `pause()` / `unpause()` | PAUSER_ROLE. |
| `0x70723ae0` | `isRedeemsEnabled()` → `bool` | |
| `0x73cfc6b2` | `isNative()` → `bool` (pure) | |

---

## 3. Addresses — Avalanche C-Chain (chain ID 43114) — the ONLY chain with BTC.b

All verified via `eth_getCode` returning non-empty bytecode on `https://avalanche-c-chain-rpc.publicnode.com` on 2026-06-09. Role wiring confirmed live: `bridgeRoles.bearer[0x85d1d52e…]=1` (struct base slot 5), adapter `getConsortium/getBascule/getAssetRouter/getTreasury/defaultAdmin` read as below.

| Role | Address | Bytecode | One-liner |
|------|---------|----------|-----------|
| **BTC.b token** (`BridgeToken`) | `0x152b9d0FdC40C096757F570A51E494bd4b943E50` | 10 032 B, **not a proxy** | The ERC-20. `name="Bitcoin"`, `symbol="BTC.b"`, `decimals=8`. Sole minter = the adapter (its `bridgeRoles` bearer). |
| **BridgeTokenAdapter (minter)** | `0x85d1d52e11290f174444d21c2a167bedbe36e4d2` | 1 159 B `TransparentUpgradeableProxy` → impl `0x80A23cB6eCEDa270889Eb165C41f55bcd300053c` (11 969 B) | Holds BTC.b's `bridgeRoles`. Consortium/Bascule-gated mint; redeem-to-BTC. |
| **ProxyAdmin** (adapter) | `0x813dd65fc4db761d0cc1799a769dcb1e9518b1b7` | 1 063 B | Upgrades the adapter proxy. `owner()` = the Timelock. |
| **TimelockController** (root gov) | `0xe4b5166b1d60c2208a934176522461c470a37d56` | 6 712 B | Adapter `defaultAdmin`/`owner` **and** ProxyAdmin owner. Governs everything. |
| **Consortium** | `0xdad58dfa5c1a7a34419afdbe1f0d610efeea95e4` | `TransparentUpgradeableProxy` | Notary set; threshold sigs verified on `mintV1`. |
| **BasculeV2** | `0x10fa7a47b65d5b631eed401ec6780337a13223ad` | 5 452 B `BasculeV2` | Deposit-attestation gate. |
| **AssetRouter** (MINTER_ROLE) | `0x9ece5fb1ab62d9075c4ec814b321e24d8ea021ac` | 1 159 B proxy | Holds adapter `MINTER_ROLE`; routes CCIP/native mints. |
| **CCIP-path minter** (MINTER_ROLE) | `0x451c54981c7da5d95901b770c540547cf5fe0a2d` | 1 159 B proxy | Currently `hasRole(MINTER_ROLE)=true`; mints on inbound CCIP. |
| **Treasury** (fee sink) | `0xaa4bc534bc7be0e28a0686ab6910a9b21dfdc2b1` | 171 B `GnosisSafeProxy` | Adapter `getTreasury()` fee sink. Does **NOT** hold MINTER_ROLE (`hasRole=0` live). |
| **BridgeTokenPool** (CCIP) | `0x67927d7ea19f9a1053f4f5bbdf827ed9870f1a1b` | `LombardTokenPoolV2 1.6.1` | CCIP token pool: `LockedOrBurned`/`ReleasedOrMinted`. |
| **EVM2EVMOffRamp** (CCIP) | `0xe5f21f43937199d4d57876a83077b3923f68eb76` | 24 385 B `EVM2EVMOffRamp 1.5.0` | Chainlink CCIP off-ramp that drives the inbound mint. |
| Original warden EOA (deployer; **role removed**) | `0xf5163f69f97b221d50347dd79382f11c6401f1a1` | EOA | Deployed BTC.b and was the original `bridgeRoles` bearer; migrated out at block 76740088. **`bearer=0` now.** |
| Original fee collector (warden era) | `0x6283184a580ec470fed64f75a20edfe4917f9ffe` | EOA | The `feeAddress` in pre-migration `Mint` events. |

> **MINTER_ROLE on the adapter** is held by **two** addresses (verified live `hasRole=1`): AssetRouter `0x9ece5fb1…` and CCIP minter `0x451c5498…`. The Treasury Safe `0xaa4bc534…` does **NOT** hold MINTER_ROLE (`hasRole=0`) — it is only the `getTreasury()` fee sink. The adapter proxy itself does **not** hold MINTER_ROLE either; it holds BTC.b's lower-level `bridgeRoles`. Membership is mutable — granted/revoked via `RoleGranted`/`RoleRevoked`, so monitor those.

---

## 4. Addresses — the other six target chains: BTC.b is NOT deployed

Verified via `eth_getCode` = `0x` (empty) on 2026-06-09 for the BTC.b token **and** the adapter/ProxyAdmin on **all six** non-Avalanche target chains. BTC.b is intentionally single-chain.

| Chain | ID | RPC | BTC.b token `0x152b9d0F…` | Adapter proxy `0x85d1d52e…` | ProxyAdmin `0x813dd65f…` |
|---|---|---|---|---|---|
| Ethereum | 1 | ethereum-rpc.publicnode.com | `0x` (none) | `0x` (none) | `0x` (none) |
| Base | 8453 | base-rpc.publicnode.com | `0x` (none) | `0x` (none) | `0x` (none) |
| BNB Smart Chain | 56 | bsc-rpc.publicnode.com | `0x` (none) | `0x` (none) | `0x` (none) |
| Arbitrum One | 42161 | arbitrum-one-rpc.publicnode.com | `0x` (none) | `0x` (none) | `0x` (none) |
| Optimism | 10 | optimism-rpc.publicnode.com | `0x` (none) | `0x` (none) | `0x` (none) |
| Polygon PoS | 137 | polygon-bor-rpc.publicnode.com | `0x` (none) | `0x` (none) | `0x` (none) |

> **Address-collision decoy:** the adapter **implementation** address `0x80A23cB6eCEDa270889Eb165C41f55bcd300053c` returns bytecode on **Ethereum (21 693 B)** and **BNB (12 678 B)** too — but those are **unrelated** contracts at the same address (on Ethereum it is verified as **`LBTC`**, Lombard's Liquid Bitcoin token; same Lombard codebase, solc 0.8.24, different deployment). This is NOT a BTC.b deployment. The only BTC.b-relevant code at `0x80A23cB6…` is the **`BridgeTokenAdapter` on Avalanche**. Always key on `(chainId, address)` and check the verified contract name.

---

## 5. Cross-chain summary

| Chain | ID | BTC.b token | Adapter (minter) | Verdict |
|---|---|---|---|---|
| **Avalanche C-Chain** | 43114 | ✅ `0x152b9d0F…3E50` (10 032 B) | ✅ `0x85d1d52e…` → `0x80A23cB6…` | **Full deployment** |
| Ethereum | 1 | ❌ `0x` | ❌ (but `0x80A23cB6…` = `LBTC` decoy) | Not deployed |
| Base | 8453 | ❌ `0x` | ❌ `0x` | Not deployed |
| BNB | 56 | ❌ `0x` | ❌ (`0x80A23cB6…` unverified decoy) | Not deployed |
| Arbitrum One | 42161 | ❌ `0x` | ❌ `0x` | Not deployed |
| Optimism | 10 | ❌ `0x` | ❌ `0x` | Not deployed |
| Polygon PoS | 137 | ❌ `0x` | ❌ `0x` | Not deployed |

**Counterparty chains (outside the seven — findings, not omissions):**
- **Bitcoin (non-EVM)** — the native source/sink. Mints carry the BTC txid in `Mint.originTxId`; redemptions emit `RedeemRequest` with a Bitcoin `scriptPubkey`. `originChainId=0` in `Mint` denotes the native-Bitcoin path.
- **Chainlink CCIP lanes** — BTC.b additionally moves EVM↔EVM via the `BridgeTokenPool` / `EVM2EVMOffRamp 1.5.0`. CCIP path mints carry `originChainId = 2^256-1` and a `remoteChainSelector` (a CCIP selector, NOT an EVM chainId). The set of connected CCIP chains is configured on the pool, not on BTC.b, and may include chains beyond the seven targets.

**Vanity tell:** the BTC.b token address `0x152b9d0F…` is not a vanity address. The adapter impl `0x80A23cB6…` deliberately collides with Lombard `LBTC` on Ethereum (shared codebase), which is the main look-alike trap.

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **BTC.b token** (`BridgeToken`) | **Immutable — not a proxy** | 10 032 B full contract; EIP-1967 impl slot `0x360894…bbc` = `0x0`, admin slot `0xb53127…6103` = `0x0` (both read live). No `upgradeTo`/`proxiableUUID`. | None. Only mutable state = the `bridgeRoles` allow-list (changed via `migrateBridgeRole`). |
| **BridgeTokenAdapter** | **Transparent proxy (EIP-1967)** | Proxy `0x85d1d52e…`: impl slot = `0x…80a23cb6eceda270889eb165c41f55bcd300053c`; admin slot = `0x…813dd65fc4db761d0cc1799a769dcb1e9518b1b7` (the ProxyAdmin). Impl `0x80A23cB6…` exposes AccessControl + DefaultAdminRules. | `ProxyAdmin` `0x813dd65f…`, owned by the Timelock `0xe4b5166b…`. Watch `Upgraded(address)` topic0 `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` on the proxy. |
| **Consortium** | Transparent proxy | impl slot populated (`0x…12364c9d…`); admin via ProxyAdmin. | Timelock. |
| **ProxyAdmin / TimelockController / BasculeV2** | **Not proxies** | Full bytecode; EIP-1967 impl slot = `0x0`. | n/a. |

**EIP-1967 slots:** impl `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. Read with `eth_getStorageAt`.

> The **token is immutable; the minter is upgradeable.** To track the live minter logic, read the proxy's impl slot and watch its `Upgraded`. To track who can mint, watch the token's `MigrateBridgeRole` AND the adapter's `RoleGranted/RoleRevoked(MINTER_ROLE)`.

---

## 7. Detection invariants & gotchas

1. **`Mint` is a 6-field, fully NON-indexed event.** topic0 `0xc5532043…`; the log has **exactly one topic**. All of `to, amount, feeAddress, feeAmount, originTxId, originChainId` are in `data` (6×32 bytes). Decode positionally — do **not** expect indexed `to`. It is **not** OZ `Mint(address,uint256)` (`0x0f6798a5…`).
2. **`originChainId` distinguishes the mint path.** `0` = native Bitcoin (then `originTxId` = the BTC txid, `feeAddress` = a real warden fee EOA). `2^256-1` (all `FF`) = the **CCIP** path (then `feeAddress`/`feeAmount`/`originTxId` are typically zero, and a paired `ReleasedOrMinted` fires on the `BridgeTokenPool`).
3. **Redemptions are `Unwrap(uint256,uint256)`, not `Burn`.** topic0 `0x37a06799…`, both fields non-indexed; the **caller is `tx.from`/the `Transfer→0x0` sender**, not encoded in the event. `BridgeToken` has no `Burn` event despite having `burn`/`burnFrom`. Pair `Unwrap` with the ERC-20 `Transfer(holder → 0x0)` to attribute the redeemer and amount.
4. **Mint authority migrated once (`MigrateBridgeRole`, block 76740088).** The original warden EOA `0xf5163f69…` is no longer a minter (`bearer=0`). The **only** current `bridgeRoles` bearer is the adapter `0x85d1d52e…`. Any future `MigrateBridgeRole` is a top-tier security alert.
5. **The real "minter" is two layers.** BTC.b's `bridgeRoles` → the adapter. The adapter's `MINTER_ROLE` → AssetRouter `0x9ece5fb1…` and CCIP minter `0x451c5498…` (Treasury Safe `0xaa4bc534…` does **NOT** hold MINTER_ROLE — it is only the fee sink). A user-visible BTC.b mint is triggered by one of those minters calling `adapter.mint*` → `BridgeToken.mint`. Attribute by the BTC.b `Mint.to`, not by `tx.from`.
6. **8 decimals, not 18.** BTC.b mirrors Bitcoin's 8-dec precision. A "1.0 BTC.b" amount is `100000000`, not `1e18`. `totalSupply()` ≈ wrapped-BTC reserves.
7. **`Transfer` from/to `0x0` is the mint/burn tell**, but the same address also receives **fee** transfers on native mints (`feeAddress` gets a second `Transfer` when `feeAmount>0`). Don't double-count the fee transfer as a user mint.
8. **The token is NOT Ownable and NOT Pausable.** `owner()` reverts; there is no `pause()`/`Paused` on `0x152b9d0F…`. The Pausable/AccessControl surface lives on the **adapter** `0x85d1d52e…`. If a "BTC.b paused" alert is needed, watch the adapter's `Paused`/`Unpaused`.
9. **Address-collision decoy `0x80A23cB6…`.** That adapter-impl address also hosts unrelated code on Ethereum (verified **`LBTC`**) and BNB. Seeing bytecode there does **not** mean BTC.b is on those chains — only the Avalanche `0x152b9d0F…` token + `0x85d1d52e…` proxy constitute BTC.b. Key on `(chainId, address)` and verify the contract name.
10. **CCIP `remoteChainSelector` ≠ EVM chainId.** On `BridgeTokenPool.LockedOrBurned`/`ReleasedOrMinted`, the `uint64` is a Chainlink CCIP chain selector. Translate via the CCIP directory before attributing a counterparty chain.
11. **Governance root = a Timelock + Gnosis Safe.** `TimelockController` `0xe4b5166b…` is the adapter `defaultAdmin` and ProxyAdmin owner; the fee/treasury sink is a Gnosis Safe `0xaa4bc534…`. Admin actions (consortium rotation, upgrades, role grants) originate there and surface as `ConsortiumChanged`/`Upgraded`/`RoleGranted`/`DefaultAdminTransferScheduled`.
12. **`AddSupportedChainId` (token) lists unwrap destinations**; `chainIds(uint256)` is the public view. An `Unwrap(amount, chainId)` to a non-supported chainId would revert, so the supported-set + `AddSupportedChainId` define valid bridge-out targets.

---

## 8. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- BTC.b token (BridgeToken)
TOPIC_BTCB_MINT                 = '\xc5532043e6f3d77e1c320ff59bd4157ca9075ef59f6b55ceab6c3f7d2f78c9ca'  -- Mint(address,uint256,address,uint256,bytes32,uint256) NON-indexed
TOPIC_BTCB_UNWRAP               = '\x37a06799a3500428a773d00284aa706101f5ad94dae9ec37e1c3773aa54c3304'  -- Unwrap(uint256,uint256)
TOPIC_BTCB_MIGRATE_BRIDGE_ROLE  = '\x871b00a4e20f8436702d0174eb87d84d7cd1dd5c34d4bb1b4e75438b3398d512'  -- MigrateBridgeRole(address)
TOPIC_BTCB_ADD_SUPPORTED_CHAIN  = '\x677e2d9a4ed9201aa86725fef875137fc53876e6b68036b974404762682bd122'  -- AddSupportedChainId(uint256)
TOPIC_TRANSFER                  = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'  -- Transfer(address,address,uint256)
TOPIC_APPROVAL                  = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'  -- Approval(address,address,uint256)
-- BridgeTokenAdapter (minter)
TOPIC_MINT_PROOF_CONSUMED       = '\x91f5c148b0f5ac9ddafe7030867f0d968adec49652c7ea760cf51fa233424b14'
TOPIC_BATCH_MINT_SKIPPED        = '\x199445030f34ba18eca81d4647be9cf6943287dd1a58d150f9cf093111240bff'
TOPIC_REDEEM_REQUEST            = '\x792e146055c5e75c3931b639fa22380b6a8ad93500e091d3f326b63e84685cae'
TOPIC_CONSORTIUM_CHANGED        = '\x146dd8feba84cdc776f012478adc764591d6c0c9570adbc49ff09c648282a0a0'
TOPIC_BASCULE_CHANGED           = '\xa0317ebf02283589c190260fcd549e3a6de71bef31204aeb5417c07fb65c0894'
TOPIC_BRIDGE_TOKEN_CHANGED      = '\xdd56718c8d1899f43e585ba9dd9904fbab0bfba720512545e82e0ffa6ae0f9da'
TOPIC_ASSET_ROUTER_CHANGED      = '\xf5f95b10b00195043307580900c3d9806c3fee7e80e71bc2d85302891605e200'
TOPIC_TREASURY_CHANGED          = '\x4fc6e7a37aea21888550b60360992adb6a9b3b4da644d63e9f3a420c2d86e282'
TOPIC_ROLE_GRANTED              = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED              = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
TOPIC_DEFAULT_ADMIN_SCHEDULED   = '\x3377dc44241e779dd06afab5b788a35ca5f3b778836e2990bdb26a2a4b2e5ed6'
TOPIC_ADAPTER_PAUSED            = '\x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258'
TOPIC_ADAPTER_UNPAUSED          = '\x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa'
TOPIC_UPGRADED                  = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'  -- Upgraded(address) on adapter proxy
-- BridgeTokenPool (CCIP)
TOPIC_CCIP_LOCKED_OR_BURNED     = '\xf33bc26b4413b0e7f19f1ea739fdf99098c0061f1f87d954b11f5293fad9ae10'
TOPIC_CCIP_RELEASED_OR_MINTED   = '\xfc5e3a5bddc11d92c2dc20fae6f7d5eb989f056be35239f7de7e86150609abc0'

-- ===== Selectors =====
-- BTC.b token
SEL_BTCB_MINT                   = '\xa888d914'  -- mint(address,uint256,address,uint256,bytes32,uint256)
SEL_BTCB_UNWRAP                 = '\x6e286671'  -- unwrap(uint256,uint256)
SEL_BTCB_MIGRATE_BRIDGE_ROLE    = '\x5d9898d3'  -- migrateBridgeRole(address)
SEL_BTCB_ADD_SUPPORTED_CHAIN    = '\x66de3b36'  -- addSupportedChainId(uint256)
SEL_BTCB_CHAIN_IDS              = '\x21d93090'  -- chainIds(uint256) view
SEL_BTCB_BURN                   = '\x42966c68'  -- burn(uint256)
SEL_BTCB_BURN_FROM              = '\x79cc6790'  -- burnFrom(address,uint256)
SEL_TRANSFER                    = '\xa9059cbb'
SEL_TRANSFER_FROM               = '\x23b872dd'
-- BridgeTokenAdapter
SEL_ADAPTER_MINT                = '\x40c10f19'  -- mint(address,uint256)
SEL_ADAPTER_MINT_V1             = '\x8307f738'  -- mintV1(bytes,bytes)
SEL_ADAPTER_BATCH_MINT_V1       = '\x0fd3f6e5'  -- batchMintV1(bytes[],bytes[])
SEL_ADAPTER_BATCH_MINT          = '\x68573107'  -- batchMint(address[],uint256[])
SEL_ADAPTER_SPEND_DEPOSIT       = '\xe1c88f39'  -- spendDeposit(bytes,bytes)
SEL_ADAPTER_GRANT_ROLE          = '\x2f2ff15d'
SEL_ADAPTER_REVOKE_ROLE         = '\xd547741f'
SEL_ADAPTER_CHANGE_CONSORTIUM   = '\x56712139'
SEL_ADAPTER_CHANGE_BRIDGE_TOKEN = '\x170efac3'
SEL_ADAPTER_PAUSE               = '\x8456cb59'

-- ===== Proxy slots & roles =====
EIP1967_IMPL_SLOT               = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT              = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'
ADAPTER_MINTER_ROLE             = '\x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6'

-- ===== Avalanche C-Chain (chain ID 43114) — the ONLY chain with BTC.b =====
AVAX_BTCB_TOKEN                 = '\x152b9d0fdc40c096757f570a51e494bd4b943e50'  -- BridgeToken, 8 dec, immutable
AVAX_BRIDGE_ADAPTER_PROXY       = '\x85d1d52e11290f174444d21c2a167bedbe36e4d2'  -- minter; impl 0x80a23cb6...
AVAX_BRIDGE_ADAPTER_IMPL        = '\x80a23cb6eceda270889eb165c41f55bcd300053c'  -- BridgeTokenAdapter (== LBTC on ETH: decoy)
AVAX_ADAPTER_PROXY_ADMIN        = '\x813dd65fc4db761d0cc1799a769dcb1e9518b1b7'
AVAX_TIMELOCK_GOV               = '\xe4b5166b1d60c2208a934176522461c470a37d56'  -- adapter defaultAdmin + ProxyAdmin owner
AVAX_CONSORTIUM                 = '\xdad58dfa5c1a7a34419afdbe1f0d610efeea95e4'
AVAX_BASCULE_V2                 = '\x10fa7a47b65d5b631eed401ec6780337a13223ad'
AVAX_ASSET_ROUTER               = '\x9ece5fb1ab62d9075c4ec814b321e24d8ea021ac'  -- MINTER_ROLE
AVAX_CCIP_PATH_MINTER           = '\x451c54981c7da5d95901b770c540547cf5fe0a2d'  -- MINTER_ROLE
AVAX_TREASURY_SAFE              = '\xaa4bc534bc7be0e28a0686ab6910a9b21dfdc2b1'  -- fee sink (Gnosis Safe); NOT a MINTER_ROLE holder
AVAX_CCIP_TOKEN_POOL            = '\x67927d7ea19f9a1053f4f5bbdf827ed9870f1a1b'  -- LombardTokenPoolV2 1.6.1
AVAX_CCIP_OFFRAMP               = '\xe5f21f43937199d4d57876a83077b3923f68eb76'  -- EVM2EVMOffRamp 1.5.0
AVAX_ORIG_WARDEN_DEPLOYER       = '\xf5163f69f97b221d50347dd79382f11c6401f1a1'  -- original bridgeRole, REMOVED (bearer=0)
AVAX_ORIG_FEE_COLLECTOR         = '\x6283184a580ec470fed64f75a20edfe4917f9ffe'  -- warden-era Mint.feeAddress (EOA)
-- NOTE: BTC.b token + adapter + ProxyAdmin return 0x on ETH/Base/BNB/Arbitrum/Optimism/Polygon.
```

---

## 9. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` (full 32 bytes for topics, `[0:4]` for selectors) from the on-chain-verified `BridgeToken`, `BridgeTokenAdapter`, and `BridgeTokenPool` ABIs. Every BTC.b selector was additionally cross-checked against the live contract's `PUSH4` dispatcher (`eth_getCode` on `0x152b9d0F…` → 19 selectors, all accounted for). `Mint` (`0xc5532043…`), `Unwrap` (`0x37a06799…`) and `MigrateBridgeRole` (`0x871b00a4…`) topic0s were confirmed against **live `eth_getLogs`**: native-mint pattern at block ~60,000,000 (`feeAddress=0x6283184a…`, `originChainId=0`, real BTC `originTxId`) and the CCIP-mint pattern at block 87,562,725 (`originChainId=2^256-1`, paired `ReleasedOrMinted` on the pool). `MigrateBridgeRole` returned exactly **one** event (block 76,740,088 → `0x85d1d52e…`).
- **Addresses & bytecode:** `eth_getCode` on each of the seven target-chain publicnode RPCs. BTC.b token (10 032 B), adapter proxy (1 159 B), ProxyAdmin (1 063 B) exist **only on Avalanche 43114**; all three return `0x` on Ethereum/Base/BNB/Arbitrum/Optimism/Polygon. The adapter-impl address `0x80A23cB6…` was checked on every chain — it is `LBTC` (verified) on Ethereum and an unrelated contract on BNB (the documented decoy).
- **Mint-authority graph:** the token's `Roles.Role bridgeRoles` was located at struct base slot **5** (`_balances`=0, `_allowances`=1, `_totalSupply`=2, `_name`=3, `_symbol`=4, then the role struct), and `bearer[addr]` read via `keccak256(addr ‖ 5)` — confirming `bearer[0x85d1d52e…]=1` and `bearer[0xf5163f69…]=0` (old warden removed). Adapter `MINTER_ROLE` (`0x9f2df0fe…`) membership confirmed via live `hasRole`: AssetRouter and CCIP minter = true; Treasury Safe = **false** (fee sink only).
- **Proxy classification:** EIP-1967 impl/admin slots read live. BTC.b token = both `0x0` → immutable. Adapter proxy impl slot = `0x…80a23cb6…`, admin slot = `0x…813dd65f…` (ProxyAdmin) → Transparent. ProxyAdmin owner and adapter `defaultAdmin` both read `0xe4b5166b…` (TimelockController).
- **Contract names / versions:** verified-source `ContractName` via the Avalanche explorer API (`BridgeToken` solc 0.8.11; `BridgeTokenAdapter` / `LBTC` solc 0.8.24; `BasculeV2`; `EVM2EVMOffRamp 1.5.0` and `LombardTokenPoolV2 1.6.1` via `typeAndVersion()`).

**Authoritative sources:**
- Snowtrace / Routescan explorer — BTC.b token `0x152b9d0FdC40C096757F570A51E494bd4b943E50` (verified `BridgeToken` source) and the `BridgeTokenAdapter` impl `0x80A23cB6eCEDa270889Eb165C41f55bcd300053c`.
- Avalanche Bridge documentation (BTC.b launch; warden/intermediary model).
- Chainlink CCIP documentation & directory (chain selectors; `EVM2EVMOffRamp`, token-pool `typeAndVersion`).
- Lombard documentation/repos (Consortium, Bascule, `LBTC`/`BridgeTokenAdapter` codebase shared with the same impl address on Ethereum).
- Live RPC: `https://avalanche-c-chain-rpc.publicnode.com` (+ the six other target-chain publicnode endpoints) for `eth_getCode` / `eth_getStorageAt` / `eth_getLogs` / `eth_call`.
