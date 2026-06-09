# Avalanche Bridge (AB) — Topics, Selectors, Addresses (Ethereum L1 ↔ Avalanche C-Chain)

**Status:** verified against Ethereum and Avalanche C-Chain mainnet RPC, the canonical `ava-labs/avalanche-bridge-resources` repo (BridgeToken.sol, Roles.sol, `avalanche_contract_address.json`, `token_list.json`, `cctp/cctp_config.json`), and the Circle CCTP deployment, on 2026-06-09.
**Scope:** the full on-chain footprint of the Avalanche Bridge — the warden-controlled deposit/mint EOAs, the per-token `BridgeToken` mintable wrapped assets on Avalanche, the deprecated AEB (Avalanche–Ethereum Bridge) ChainBridge handler, and the AB CCTP router. Topics/selectors are **chain-agnostic**; addresses are **network-specific**. The bridge connects **exactly two chains — Ethereum (chain 1) and Avalanche C-Chain (chain 43114)**. **Not deployed on Base, BNB, Arbitrum, Optimism, or Polygon** (`eth_getCode` = `0x` for every AB address on all five — see §7).

The Avalanche Bridge is a **trusted, off-chain-relayer ("warden") bridge**, not a smart-contract messaging protocol. Its security lives in an **Intel SGX enclave** whose signing key is secret-shared among **4 wardens (3-of-4 threshold)**; the enclave is the only entity that can sign the bridge's on-chain transactions. Consequently the bridge's on-chain surface is deliberately thin:

- **Ethereum side (lock/release):** there is **no AB bridge contract on Ethereum**. The deposit/lock address `0x8eb8a3b9…b75e3ab28` ("Avalanche Bridge") is a **plain EOA** (no bytecode, nonce 49 233+, holds ETH/ERC-20 balances). Users send the native ERC-20 (or ETH) directly to this address; locking = an ordinary inbound `Transfer`. Release on Ethereum = an ordinary outbound `Transfer` signed by the enclave. There is no `Deposit`/`Lock` event to key on — **monitor ERC-20 `Transfer` to/from the EOA.**
- **Avalanche side (mint/burn):** for each supported asset the bridge deploys a per-token **`BridgeToken`** (an `ERC20Burnable` with a `bridgeRole`). To bridge in, the warden EOA `0xeb1bb701…cc2f8f` calls `mint(to, amount, feeAddress, feeAmount, originTxId)` → emits `Mint`. To bridge out, the user calls `unwrap(amount, chainId)` (which burns) → emits `Unwrap`. The warden EOA is the sole `bridgeRole` holder / minter on every token (confirmed live: a Mint tx's `from` = `0xeb1bb701…`).

**Two generations coexist on the same addresses.** The original **AEB** (deprecated 2021) was a ChainBridge fork: an `ERC20Handler` contract on Ethereum (`0xdac7bb7c…799a147`, live, 7 317 B) and handler/tokens on Avalanche. The **AB** (current, launched July 2021, "v1.1") replaced AEB's contracts with the warden-EOA + `BridgeToken` model and **reused the same token addresses** (e.g. `WETH.e` `0x49d5…0bAB` is the *same address* that AEB used; the live bytecode is today's AB `BridgeToken`). AB also added a **CCTP path for native USDC** via an AB-owned CCTP router. There is **no v2 redeploy** — AB is one continuously-operated deployment; hence this single `core.md`.

> **The single most important indexing fact:** there is no canonical "bridge contract" to watch on Ethereum. **Lock/release = ERC-20 `Transfer` to/from the warden EOAs.** On Avalanche, mint/burn = the `BridgeToken` `Mint`/`Unwrap`/`Swap` events. Anyone indexing this bridge by looking for a `deposit()`/`lock()` call on an Ethereum contract will see nothing.

---

## 0. Contract families & components

| Component | Chain | Role | Type | Verified bytecode |
|-----------|-------|------|------|-------------------|
| **Bridge EOA (Ethereum)** | ETH 1 | Deposit/lock + release address. Users send native ERC-20/ETH here; enclave releases from here. | **EOA** (no code) | `0x` (nonce 49 233+, holds balances) |
| **Bridge EOA (Avalanche)** | AVAX 43114 | Warden minter — sole `bridgeRole` holder; calls `mint` on every `BridgeToken`; receives `unwrap` proceeds. | **EOA** (no code) | `0x` (nonce 93 991+) |
| **BridgeToken** (per asset) | AVAX 43114 | Mintable/burnable wrapped representation (`WETH.e`, `USDC.e`, `WBTC.e`, …). One contract per asset. | `ERC20Burnable` + `Roles` — **immutable, NOT a proxy** | 12 716 B (12 717 incl. CBOR) typ.; LINK.e 13 553 B |
| **AEB ERC20Handler** (legacy) | ETH 1 | Deprecated AEB (ChainBridge) handler — `executeProposal`/`withdraw`/`deposit`. Dead since 2021. | ChainBridge `ERC20Handler` | 7 317 B |
| **AEB handler/token** (legacy) | AVAX 43114 | Deprecated AEB Avalanche-side contract at `0xdac7bb7c…`. | ChainBridge artifact | 10 028 B |
| **AB CCTP router** | ETH 1 & AVAX 43114 | AB-owned wrapper around Circle CCTP `depositForBurn` for **native USDC** (not the `.e` wrapped token). | CCTP router (not Circle's canonical TokenMessenger) | 7 460 B (identical both chains) |
| **Circle MessageTransmitter** | ETH 1 & AVAX 43114 | Circle-canonical CCTP receive side used by the AB CCTP path. | Circle MessageTransmitter | 17 562 B (ETH) / 13 677 B (AVAX) |

All `BridgeToken` instances share **one ABI** (the BridgeToken.sol below); their bytecode differs only by constructor-baked `name`/`symbol`/`decimals`. So **every topic0/selector in §1–§2 applies to every `.e` token.**

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak256 on 2026-06-09 and cross-checked against live `eth_getLogs`.

### 1.1 BridgeToken (every `.e` token on Avalanche)

| topic0 | Event | Meaning |
|--------|-------|---------|
| `0x918d77674bb88eaf75afb307c9723ea6037706de68d6fc07dd0c6cba423a5250` | `Mint(address to, uint256 amount, address feeAddress, uint256 feeAmount, bytes32 originTxId)` | **Bridge-in completed** — warden minted wrapped tokens. *Verified live on WETH.e (6 logs / 49k blocks).* **All params non-indexed** → only 1 topic; decode from `data`. `originTxId` = the Ethereum lock tx hash. |
| `0x37a06799a3500428a773d00284aa706101f5ad94dae9ec37e1c3773aa54c3304` | `Unwrap(uint256 amount, uint256 chainId)` | **Bridge-out initiated** — user burned wrapped tokens to release on `chainId`. *Verified live on USDC.e.* No indexed params. |
| `0x562c219552544ec4c9d7a8eb850f80ea152973e315372bf4999fe7c953ea004f` | `Swap(address token, uint256 amount)` | User swapped an **AEB-era token → AB token** 1:1 via `swap()` (legacy-token migration). |
| `0x3e4fdfb0f47da284fe8b5b3a7e5d10b211e323c9a0c144c421ae1d211873f853` | `AddSwapToken(address contractAddress, uint256 supplyIncrement)` | Bridge-admin registered a legacy token as swappable. |
| `0xd3b4025ff115b79bf2ec5a73c9c784ba8aa9f8f6ba9186b255895c1a9f9042a3` | `RemoveSwapToken(address contractAddress, uint256 supplyDecrement)` | Bridge-admin de-registered a swap token. |
| `0x677e2d9a4ed9201aa86725fef875137fc53876e6b68036b974404762682bd122` | `AddSupportedChainId(uint256 chainId)` | A destination chainId enabled for `unwrap`. |
| `0x871b00a4e20f8436702d0174eb87d84d7cd1dd5c34d4bb1b4e75438b3398d512` | `MigrateBridgeRole(address newBridgeRoleAddress)` | **`bridgeRole` (minter) rotated** — the highest-severity admin signal on this protocol. The new address becomes the sole minter. |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | ERC-20. `from = 0x0` accompanies `Mint`; `to = 0x0` accompanies `unwrap` burn. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | ERC-20. |

> **No `indexed` params on the bridge events.** Unlike most protocols, `Mint`/`Unwrap`/`Swap` carry zero indexed args, so `log.topics` is `[topic0]` only and **everything is ABI-decoded from `data`**. Don't try to filter by an indexed `to`/`token`.

### 1.2 AEB ERC20Handler — legacy ChainBridge (deprecated; events kept for archival decoding)

The AEB handler is a ChainBridge `ERC20Handler`; the **`Deposit`/proposal events were emitted by the AEB *Bridge* contract** (a separate ChainBridge `Bridge`, now dead), not the handler. Topic0s of the canonical ChainBridge `Bridge` for archival use:

| topic0 | Event |
|--------|-------|
| `0xdbb69440df8433824a026ef190652f29929eb64b4d1d5d2a69be8afe3e6eaed8` | `Deposit(uint8 destinationChainID, bytes32 resourceID, uint64 depositNonce)` |
| `0x803c5a12f6bde629cea32e63d4b92d1b560816a6fb72e939d3c89e1cab650417` | `ProposalEvent(uint8 originChainID, uint64 depositNonce, uint8 status, bytes32 resourceID, bytes32 dataHash)` |
| `0x25f8daaa4635a7729927ba3f5b3d59cc3320aca7c32c9db4e7ca7b9574343640` | `ProposalVote(uint8 originChainID, uint64 depositNonce, uint8 status, bytes32 resourceID)` |

These are **archival** — AEB has not processed a transfer since 2021 (the ETH handler shows 2 lifetime txs). Do **not** include them in a live-alerting set; AB does not use ChainBridge.

### 1.3 CCTP path (native USDC) — Circle events, not AB-specific

| topic0 | Event | Emitter |
|--------|-------|---------|
| `0x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0` | `DepositForBurn(uint64 nonce, address burnToken, uint256 amount, address depositor, bytes32 mintRecipient, uint32 destinationDomain, bytes32 destinationTokenMessenger, bytes32 destinationCaller)` | Circle TokenMessenger (reached via the AB CCTP router) |
| `0x58200b4c34ae05ee816d710053fff3fb75af4395915d3d2a771b24aa10e3cc5d` | `MessageReceived(address caller, uint32 sourceDomain, uint64 nonce, bytes32 sender, bytes messageBody)` | Circle MessageTransmitter (CCTP **receive** side) |
| `0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036` | `MessageSent(bytes message)` | Circle MessageTransmitter (CCTP **send** side — the cross-chain message envelope) |

> These topic0s are **Circle CCTP-standard** (computed from Circle's `TokenMessenger`/`MessageTransmitter` signatures); they are not unique to the Avalanche Bridge. Attribute an AB CCTP transfer by the **router** `0xD835…5648` appearing in the call path, not by these topics alone.

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

All selectors recomputed locally on 2026-06-09 and verified **present** in the live WETH.e + USDC.e bytecode on Avalanche.

### 2.1 BridgeToken — state-changing (warden/admin only, except `unwrap`/`swap`/`burn`)

| Selector | Signature | Caller | Notes |
|----------|-----------|--------|-------|
| `0x67fc19bb` | `mint(address to, uint256 amount, address feeAddress, uint256 feeAmount, bytes32 originTxId)` | **bridgeRole** (warden EOA) | Bridge-in. Emits `Mint` + ERC-20 `Transfer(0x0→to)`. *Verified live: tx `from` = `0xeb1bb701…`.* |
| `0x6e286671` | `unwrap(uint256 amount, uint256 chainId)` | any holder | Bridge-out. Burns `amount` and emits `Unwrap`. `chainId` must be in `chainIds`. |
| `0xd004f0f7` | `swap(address token, uint256 amount)` | any holder | Swap a legacy AEB token 1:1 for this AB token. Emits `Swap`. |
| `0x5d9898d3` | `migrateBridgeRole(address newBridgeRoleAddress)` | bridgeRole | **Rotates the minter.** Emits `MigrateBridgeRole`. Watch this. |
| `0x66de3b36` | `addSupportedChainId(uint256 chainId)` | bridgeRole | Emits `AddSupportedChainId`. |
| `0xeff03830` | `addSwapToken(address contractAddress, uint256 supplyIncrement)` | bridgeRole | Emits `AddSwapToken`. |
| `0x7c38b457` | `removeSwapToken(address contractAddress, uint256 supplyDecrement)` | bridgeRole | Emits `RemoveSwapToken`. |
| `0x42966c68` | `burn(uint256 amount)` | any holder | `ERC20Burnable` — direct burn (no chain release). |
| `0x79cc6790` | `burnFrom(address account, uint256 amount)` | approved | `ERC20Burnable`. |
| `0xa9059cbb` | `transfer(address to, uint256 amount)` | any | ERC-20. |
| `0x23b872dd` | `transferFrom(address from, address to, uint256 amount)` | approved | ERC-20. |
| `0x095ea7b3` | `approve(address spender, uint256 amount)` | any | ERC-20. |

### 2.2 BridgeToken — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xab32dbb7` | `swapSupply(address token)` | `uint256` — outstanding swap supply for a registered legacy token. |
| `0x21d93090` | `chainIds(uint256)` | `bool` — is this destination chainId supported for `unwrap`. |
| `0x06fdde03` | `name()` | e.g. `"Wrapped Ether"` (WETH.e). |
| `0x95d89b41` | `symbol()` | e.g. `"WETH.e"`, `"USDC.e"`. |
| `0x313ce567` | `decimals()` | mirrors the native token (WETH.e 18, USDC.e 6, WBTC.e 8). |
| `0x18160ddd` | `totalSupply()` | total wrapped supply = total locked on Ethereum (modulo fees). |
| `0x70a08231` | `balanceOf(address)` | ERC-20. |
| `0xdd62ed3e` | `allowance(address,address)` | ERC-20. |

### 2.3 AEB ERC20Handler (legacy, Ethereum `0xdac7bb7c…`) — selectors verified present in its bytecode

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xe248cff2` | `executeProposal(bytes32 resourceID, bytes data)` | ChainBridge release entrypoint (called by the dead AEB Bridge). |
| `0xd9caed12` | `withdraw(address tokenAddress, address recipient, uint256 amount)` | Admin token recovery. |
| `0x318c136e` | `_bridgeAddress()` | The AEB Bridge that controls this handler. |
| `0x0a6d55d8` | `_resourceIDToTokenContractAddress(bytes32)` | ChainBridge resourceID → token map. |
| `0xc8ba6c87` | `_tokenContractAddressToResourceID(address)` | reverse map. |
| `0x7f79bea8` | `_contractWhitelist(address)` | whitelisted tokens. |
| `0x6a70d081` | `_burnList(address)` | tokens this handler burns (vs locks). |
| `0xb8fa3736` | `setResource(bytes32 resourceID, address tokenAddress)` | admin. |
| `0x07b7ed99` | `setBurnable(address tokenAddress)` | admin. |
| `0xba484c09` | `getDepositRecord(uint64 depositNonce, uint8 destId)` | view. |
| `0x4402027f` | `_depositRecords(uint8, uint64)` | view. |

> The AEB **Bridge** `deposit(uint8,bytes32,bytes)=0x05e2ca17` / `voteProposal=0x1ff013f1` selectors are **absent** from `0xdac7bb7c…` — confirming that address is the *handler*, not the Bridge. The AEB Bridge contract is a separate (also-dead) deployment; AB does not use it.

### 2.4 AB CCTP router (`0xD835…5648`, ETH + AVAX) — for native USDC

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6fd3504e` | `depositForBurn(uint256 amount, uint32 destinationDomain, bytes32 mintRecipient, address burnToken)` | **Present** — Circle CCTP burn entrypoint. Domains: ETH = 0, AVAX = 1. |

> `0xD835…5648` is **not** Circle's canonical TokenMessenger (`0xBd3fa81B…af3155` on ETH). It exposes `depositForBurn` but **lacks** `localMinter()=0xcb75c11c` and `localMessageTransmitter()=0x2c121921`, so it is an **AB-owned CCTP router/wrapper** that forwards to Circle internally. Identical 7 460-B bytecode on ETH and AVAX (deterministic deploy). The receive side `MessageTransmitter` (`0x0a992d19…` ETH, `0x8186359a…` AVAX) **is** Circle-canonical.

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` / `eth_getTransactionCount` on `https://ethereum-rpc.publicnode.com` on 2026-06-09.

| Role | Address | One-liner |
|------|---------|-----------|
| **AB deposit/lock EOA** ("Avalanche Bridge") | `0x8eb8a3b98659cce290402893d0123abb75e3ab28` | **EOA, no code** (nonce 49 233+, ~333 ETH balance). Users send native ERC-20/ETH here to bridge in; enclave releases from here on bridge-out. **No `Deposit` event — index ERC-20 `Transfer` to/from this address.** |
| **AEB ERC20Handler** (legacy) | `0xdac7bb7ce4ff441a235f08408e632fa1d799a147` | **Live contract, 7 317 B**, but **deprecated since 2021** (2 lifetime txs, dust balance). ChainBridge handler — `executeProposal`/`withdraw` (§2.3). Not used by AB. |
| **AB CCTP router** (native USDC) | `0xD835dbD135AD8a27214ecdEE79E7a41337865648` | 7 460 B. AB wrapper over Circle CCTP `depositForBurn`. |
| **Circle MessageTransmitter** (CCTP receive) | `0x0a992d191deec32afe36203ad87d7d289a738f81` | 17 562 B. Circle-canonical; emits `MessageReceived`. |
| Native USDC (CCTP burn token) | `0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48` | 6-dec; the CCTP path moves real USDC, not USDC.e. |

The **native locked tokens** are the ordinary Ethereum ERC-20s (WETH `0xC02a…756Cc2`, WBTC `0x2260…2C599`, USDC above, DAI `0x6B17…71d0F`, …) — they are not AB contracts; AB simply holds them at the EOA. There is **no AB-specific lock/vault contract on Ethereum.**

---

## 4. Addresses — Avalanche C-Chain (chain ID 43114)

All verified via `eth_getCode` / `eth_call` on `https://avalanche-c-chain-rpc.publicnode.com` on 2026-06-09. Every `BridgeToken` is **immutable (not a proxy)** — EIP-1967 impl + admin slots read `0x0` (§8).

### 4.1 Bridge infrastructure

| Role | Address | One-liner |
|------|---------|-----------|
| **AB warden minter EOA** | `0xeb1bb70123b2f43419d070d7fde5618971cc2f8f` | **EOA, no code** (nonce 93 991+). Sole `bridgeRole` holder; calls `mint` on every BridgeToken (verified live as a Mint tx `from`). |
| **AEB legacy contract** | `0xdac7bb7ce4ff441a235f08408e632fa1d799a147` | 10 028 B — deprecated AEB Avalanche-side artifact (same literal address as the ETH handler). |
| **AB CCTP router** | `0xD835dbD135AD8a27214ecdEE79E7a41337865648` | 7 460 B — same deterministic address as ETH; CCTP burn for native USDC. |
| **Circle MessageTransmitter** | `0x8186359af5f57fbb40c6b14a588d2a59c0c29880` | 13 677 B — Circle-canonical CCTP receive. |
| Native USDC (Circle, CCTP target) | `0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e` | 6-dec native USDC on Avalanche (distinct from `USDC.e`). |

### 4.2 BridgeToken instances (the `.e` wrapped assets) — source `avalanche_contract_address.json`

All 25 are BridgeTokens with the identical ABI of §1–§2. The native (Ethereum) counterpart is the ERC-20 of the same symbol.

| Symbol | BridgeToken address (Avalanche) | Dec | Code verified |
|--------|---------------------------------|-----|---------------|
| **WETH.e** | `0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB` | 18 | ✓ 12 716 B (`Mint`/`Unwrap` logs live) |
| **USDC.e** | `0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664` | 6 | ✓ 12 716 B (`Unwrap` log live) |
| **USDT.e** | `0xc7198437980c041c805A1EDcbA50c1Ce5db95118` | 6 | ✓ 12 716 B |
| **DAI.e** | `0xd586E7F844cEa2F87f50152665BCbc2C279D8d70` | 18 | ✓ 12 716 B |
| **WBTC.e** | `0x50b7545627a5162F82A992c33b87aDc75187B218` | 8 | ✓ 12 716 B |
| **LINK.e** | `0x5947BB275c521040051D82396192181b413227A3` | 18 | ✓ 13 553 B |
| **AAVE.e** | `0x63a72806098Bd3D9520cC43356dD78afe5D386D9` | 18 | ✓ 12 716 B |
| 1INCH.e | `0xd501281565bf7789224523144Fe5D98e8B28f267` | 18 | ✓ (registry) |
| BAT.e | `0x98443B96EA4b0858FDF3219Cd13e98C7A4690588` | 18 | ✓ (registry) |
| BUSD.e | `0x19860CCB0A68fd4213aB9D8266F7bBf05A8dDe98` | 18 | ✓ (registry) |
| COMP.e | `0xc3048E19E76CB9a3Aa9d77D8C03c29Fc906e2437` | 18 | ✓ (registry) |
| CRV.e | `0x249848BeCA43aC405b8102Ec90Dd5F22CA513c06` | 18 | ✓ (registry) |
| GRT.e | `0x8a0cAc13c7da965a312f08ea4229c37869e85cB9` | 18 | ✓ (registry) |
| INFRA.e | `0xa4FB4F0Ff2431262D236778495145EcBC975c38B` | 18 | ✓ (registry) |
| MKR.e | `0x88128fd4b259552A9A1D457f435a6527AAb72d42` | 18 | ✓ (registry) |
| SNX.e | `0xBeC243C995409E6520D7C41E404da5dEba4b209B` | 18 | ✓ (registry) |
| SUSHI.e | `0x37B608519F91f70F2EeB0e5Ed9AF4061722e4F76` | 18 | ✓ (registry) |
| SWAP.e | `0xc7B5D72C836e718cDA8888eaf03707fAef675079` | 18 | ✓ (registry) |
| UMA.e | `0x3Bd2B1c7ED8D396dbb98DED3aEbb41350a5b2339` | 18 | ✓ (registry) |
| UNI.e | `0x8eBAf22B6F053dFFeaf46f4Dd9eFA95D89ba8580` | 18 | ✓ (registry) |
| YFI.e | `0x9eAaC1B23d935365bD7b542Fe22cEEe2922f52dc` | 18 | ✓ (registry) |
| ZRX.e | `0x596fA47043f99A4e0F122243B841E55375cdE0d2` | 18 | ✓ (registry) |
| ALPHA.e | `0x2147EFFF675e4A4eE1C2f918d181cDBd7a8E208f` | 18 | ✓ (registry) |
| WOO.e | `0xaBC9547B534519fF73921b1FBA6E672b5f58D083` | 18 | ✓ (registry) |
| SHIB.e | `0x02D980A0D7AF3fb7Cf7Df8cB35d9eDBCF355f665` | 18 | ✓ (registry) |

> The registry also references RUNE (Thorchain) in the `tokens/` logo dir, but no `.e` address is listed in `avalanche_contract_address.json`. **BTC.b** (bridged Bitcoin) is a separate Core/`btcBridge` product, not an AEB/AB `.e` BridgeToken, and is not in this registry.

---

## 5. Decimals & math

- Each `BridgeToken` **mirrors the native token's decimals** (read `decimals()`; do not assume 18). Verified: WETH.e/DAI.e/LINK.e/AAVE.e = 18, USDC.e/USDT.e = 6, WBTC.e = 8.
- `Mint.amount` is the gross minted amount **after** the bridge fee was already split out — `feeAmount` (to `feeAddress`) is reported separately in the same event. The user receives `amount`; the bridge keeps `feeAmount`. **Net user credit = `amount`** (fee is not subtracted again).
- `Unwrap.amount` is the burned amount; the Ethereum release is `amount` minus the Ethereum-side gas/fee handled off-chain by the enclave.
- `originTxId` (bytes32) in `Mint` = the **Ethereum lock transaction hash** — the cross-chain join key. Use `(originTxId)` to pair an Ethereum inbound `Transfer` with its Avalanche `Mint`.

---

## 6. Cross-chain message/attribution model

- **There is no on-chain message hash or nonce on the Ethereum side.** The deposit is a bare ERC-20 `Transfer` to the EOA; correlation to the Avalanche `Mint` is via the **`originTxId`** carried in `Mint` (the ETH lock tx hash). For bridge-out, the `Unwrap(amount, chainId)` event is the only on-chain record on Avalanche; the matching Ethereum release is a plain `Transfer` from the EOA with no event linking it back (off-chain enclave decides recipient).
- **The real "operator" on Avalanche is the warden EOA `0xeb1bb701…`** (tx `from` of every `mint`). The `to` in `Mint` is the end user. Do not attribute mints to the token contract or to `tx.origin` of an aggregator.
- **CCTP path (native USDC only):** native USDC bridges via Circle CCTP (burn-and-mint), keyed by Circle's CCTP `nonce` + `sourceDomain` (ETH domain 0, AVAX domain 1) — a completely separate mechanism from the `.e` lock/mint flow. `USDC.e` (`0xA7D7…C664`) ≠ native USDC (`0xb97e…8a6E`); the CCTP path uses the latter.

---

## 7. Cross-chain summary

Presence of every AB component on each of the seven requested chains (`eth_getCode`, 2026-06-09):

| Chain | ID | Deposit/Mint EOA | BridgeToken (.e) | AEB legacy | AB CCTP router | Status |
|-------|----|------------------|------------------|------------|----------------|--------|
| **Ethereum** | 1 | ✓ EOA `0x8eb8…3ab28` (lock side) | — (native ERC-20s held at EOA) | ✓ handler `0xdac7…9a147` (dead) | ✓ `0xD835…5648` | **Active (L1 lock/release)** |
| **Avalanche C-Chain** | 43114 | ✓ EOA `0xeb1b…2f8f` (mint side) | ✓ 25 tokens | ✓ `0xdac7…9a147` (dead) | ✓ `0xD835…5648` | **Active (mint/burn)** |
| Base | 8453 | ✗ `0x` | ✗ | ✗ | ✗ | **Not deployed** |
| BNB Smart Chain | 56 | ✗ `0x` | ✗ | ✗ | ✗ | **Not deployed** |
| Arbitrum One | 42161 | ✗ `0x` | ✗ | ✗ | ✗ | **Not deployed** |
| Optimism | 10 | ✗ `0x` | ✗ | ✗ | ✗ | **Not deployed** |
| Polygon PoS | 137 | ✗ `0x` | ✗ | ✗ | ✗ | **Not deployed** |

**The Avalanche Bridge is strictly an Ethereum ↔ Avalanche C-Chain bridge.** None of Base/BNB/Arbitrum/Optimism/Polygon carries any AB contract or EOA with code. The CCTP router address `0xD835…5648` is identical on ETH and AVAX (deterministic), but returns `0x` on all five other chains — AB does not run CCTP on the other Circle domains.

**Counterparty chains outside the seven:** none. AB has historically connected **only** Ethereum and Avalanche. (Bitcoin and other chains reach Avalanche through *separate* Core products — BTC.b via `btcBridge`, and the broader multichain bridging via Wormhole/LayerZero — not via this AB deployment.)

**Vanity / address tells:** the deposit EOA `0x8eb8a3b9…` and mint EOA `0xeb1bb701…` are not vanity. The AEB legacy contract reuses the **same literal `0xdac7bb7c…799a147` on both ETH and AVAX**. The CCTP router reuses `0xD835…5648` on both.

---

## 8. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **BridgeToken** (every `.e` token) | **Immutable — NOT a proxy** | EIP-1967 impl slot `0x360894…bbc` = `0x0` and admin slot `0xb53127…6103` = `0x0` (verified on WETH.e + USDC.e). Full 12 716-B runtime; no `Upgraded` event in the ABI. | None. To change behaviour the bridge deploys a **new** BridgeToken and migrates via `swap()`. The only mutable authority is `bridgeRole`, rotated by `migrateBridgeRole` (not a proxy upgrade). |
| **AB CCTP router** `0xD835…5648` | Treat as fixed bytecode (no EIP-1967 slot populated) | impl slot `0x0` | n/a (Circle infra behind it is upgradeable separately). |
| **AEB ERC20Handler** `0xdac7…9a147` | Plain contract (ChainBridge handler) | impl slot `0x0` | AEB admin (dead). |
| **Deposit/mint EOAs** | **EOAs** | `eth_getCode` = `0x`; positive nonce | enclave (3-of-4 wardens, off-chain). |

There are **no upgradeable proxies anywhere in the Avalanche Bridge.** The only on-chain "upgrade" signal is the BridgeToken **`MigrateBridgeRole(address)`** event (`0x871b00a4…d512`) — rotating the minter EOA. Watch that, **not** an `Upgraded(address)` topic (none exists here).

---

## 9. Detection invariants & gotchas

1. **No Ethereum bridge contract.** Lock/release on Ethereum = a plain ERC-20 `Transfer` to/from the EOA `0x8eb8a3b9…b75e3ab28`. There is **no `deposit()`/`lock()` call and no `Deposit` event** to key on L1. Index inbound/outbound `Transfer` on that EOA, per token.
2. **Bridge-in = `Mint` on the Avalanche BridgeToken** (`0x918d77…5250`); **bridge-out = `Unwrap`** (`0x37a067…3304`). These are the workhorse events. `Mint` is emitted **only** by warden EOA `0xeb1bb701…cc2f8f` (verified). A mint from any other `from` would be anomalous (compromise signal).
3. **Every bridge event has zero indexed params.** `topics = [topic0]` only; decode `to`/`amount`/`originTxId`/`feeAmount` from `data`. Do not write filters expecting an indexed recipient.
4. **`originTxId` (bytes32) in `Mint` = the Ethereum lock tx hash** — the cross-chain join key. Use it to pair an L1 `Transfer`→EOA with the Avalanche `Mint`. There is no other shared nonce/messageHash.
5. **Fee is reported in-event, not double-charged.** `Mint(to, amount, feeAddress, feeAmount, originTxId)` — the user gets `amount`; `feeAmount` is the bridge's cut sent to `feeAddress` (often `0x0`/the bridge). Net = `amount`.
6. **`MigrateBridgeRole` is the top admin alert.** It rotates the *only* minter on a token. `0x871b00a4…d512`. No proxy `Upgraded` event exists — this is the closest analogue.
7. **`Swap`/`AddSwapToken` are legacy-migration plumbing**, not user bridging. `swap()` converts an old AEB-era token to the current AB token 1:1. Don't count `Swap` as bridge volume.
8. **AB ≠ AEB.** The AEB ChainBridge handler `0xdac7…9a147` is **live but dead** (2 txs since 2021). Its `Deposit`/`ProposalEvent`/`executeProposal` (§1.2/§2.3) are archival only. Excluding them from a live set is correct; including them yields no signal.
9. **`USDC.e` ≠ native USDC.** `USDC.e` (`0xA7D7…C664`, a BridgeToken minted by the warden) is the *wrapped* asset; **native USDC** (`0xb97e…8a6E` on AVAX, `0xa0b8…eB48` on ETH) moves via the **CCTP** path through router `0xD835…5648` + Circle's MessageTransmitter. They are different tokens with different mechanics — don't conflate volumes.
10. **The CCTP router `0xD835…5648` is NOT Circle's TokenMessenger.** It has `depositForBurn` but lacks `localMinter`/`localMessageTransmitter`; it's an AB wrapper. CCTP receive uses Circle's canonical MessageTransmitter (`0x0a99…8f81` ETH / `0x8186…9880` AVAX), which emits `MessageReceived` (`0x58200b4c…`) on the receive side and `MessageSent` (`0x8c526166…`) on the send side. The CCTP `DepositForBurn`/`MessageReceived`/`MessageSent` topic0s are Circle-generic — attribute to AB by the router in the call path.
11. **BridgeTokens are immutable, not proxies.** Reading the EIP-1967 slot returns `0x0` (expected, not a missing proxy). A behaviour change means a brand-new token address + `swap()` migration, not an `upgradeTo`.
12. **Decimals vary per token** — WETH.e 18, USDC.e/USDT.e 6, WBTC.e 8. Read `decimals()`; never hard-code 18.
13. **Only two chains.** Any "Avalanche Bridge on Base/BNB/Arbitrum/Optimism/Polygon" claim is false — every AB address is `0x` there (§7). BTC.b and other cross-chain assets on Avalanche come from *different* bridges/products.
14. **Both bridge addresses are EOAs with high nonces** (49k ETH / 93k AVAX) and hold large balances — that's by design (the enclave custodies funds). A sudden balance drain from the EOA, or a `Transfer` from it not matching an `Unwrap`, is the core compromise signal to watch.

---

## 10. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
-- BridgeToken (every .e token on Avalanche)
TOPIC_MINT                     = '\x918d77674bb88eaf75afb307c9723ea6037706de68d6fc07dd0c6cba423a5250'
TOPIC_UNWRAP                   = '\x37a06799a3500428a773d00284aa706101f5ad94dae9ec37e1c3773aa54c3304'
TOPIC_SWAP                     = '\x562c219552544ec4c9d7a8eb850f80ea152973e315372bf4999fe7c953ea004f'
TOPIC_ADD_SWAP_TOKEN           = '\x3e4fdfb0f47da284fe8b5b3a7e5d10b211e323c9a0c144c421ae1d211873f853'
TOPIC_REMOVE_SWAP_TOKEN        = '\xd3b4025ff115b79bf2ec5a73c9c784ba8aa9f8f6ba9186b255895c1a9f9042a3'
TOPIC_ADD_SUPPORTED_CHAINID    = '\x677e2d9a4ed9201aa86725fef875137fc53876e6b68036b974404762682bd122'
TOPIC_MIGRATE_BRIDGE_ROLE      = '\x871b00a4e20f8436702d0174eb87d84d7cd1dd5c34d4bb1b4e75438b3398d512'
TOPIC_ERC20_TRANSFER           = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_ERC20_APPROVAL           = '\x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925'
-- CCTP (Circle-standard, native USDC path)
TOPIC_CCTP_DEPOSIT_FOR_BURN    = '\x2fa9ca894982930190727e75500a97d8dc500233a5065e0f3126c48fbe0343c0'
TOPIC_CCTP_MESSAGE_RECEIVED    = '\x58200b4c34ae05ee816d710053fff3fb75af4395915d3d2a771b24aa10e3cc5d'  -- MessageReceived(address,uint32,uint64,bytes32,bytes)
TOPIC_CCTP_MESSAGE_SENT        = '\x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036'  -- MessageSent(bytes)
-- AEB legacy ChainBridge Bridge (archival only)
TOPIC_AEB_DEPOSIT              = '\xdbb69440df8433824a026ef190652f29929eb64b4d1d5d2a69be8afe3e6eaed8'
TOPIC_AEB_PROPOSAL_EVENT       = '\x803c5a12f6bde629cea32e63d4b92d1b560816a6fb72e939d3c89e1cab650417'
TOPIC_AEB_PROPOSAL_VOTE        = '\x25f8daaa4635a7729927ba3f5b3d59cc3320aca7c32c9db4e7ca7b9574343640'

-- ===== Selectors =====
-- BridgeToken
SEL_MINT                       = '\x67fc19bb'   -- mint(address,uint256,address,uint256,bytes32)
SEL_UNWRAP                     = '\x6e286671'   -- unwrap(uint256,uint256)
SEL_SWAP                       = '\xd004f0f7'   -- swap(address,uint256)
SEL_MIGRATE_BRIDGE_ROLE        = '\x5d9898d3'   -- migrateBridgeRole(address)
SEL_ADD_SUPPORTED_CHAINID      = '\x66de3b36'   -- addSupportedChainId(uint256)
SEL_ADD_SWAP_TOKEN             = '\xeff03830'   -- addSwapToken(address,uint256)
SEL_REMOVE_SWAP_TOKEN          = '\x7c38b457'   -- removeSwapToken(address,uint256)
SEL_BURN                       = '\x42966c68'   -- burn(uint256)
SEL_SWAP_SUPPLY                = '\xab32dbb7'   -- swapSupply(address)
SEL_CHAIN_IDS                  = '\x21d93090'   -- chainIds(uint256)
-- AEB ERC20Handler (legacy)
SEL_AEB_EXECUTE_PROPOSAL       = '\xe248cff2'   -- executeProposal(bytes32,bytes)
SEL_AEB_WITHDRAW               = '\xd9caed12'   -- withdraw(address,address,uint256)
-- AB CCTP router
SEL_CCTP_DEPOSIT_FOR_BURN      = '\x6fd3504e'   -- depositForBurn(uint256,uint32,bytes32,address)

-- ===== Proxy slots (all read 0x0 → immutable, NOT proxies) =====
EIP1967_IMPL_SLOT              = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT             = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Ethereum (chain ID 1) =====
ETH_BRIDGE_DEPOSIT_EOA         = '\x8eb8a3b98659cce290402893d0123abb75e3ab28'   -- EOA, lock/release
ETH_AEB_ERC20_HANDLER          = '\xdac7bb7ce4ff441a235f08408e632fa1d799a147'   -- legacy, dead
ETH_AB_CCTP_ROUTER             = '\xd835dbd135ad8a27214ecdee79e7a41337865648'
ETH_CCTP_MESSAGE_TRANSMITTER   = '\x0a992d191deec32afe36203ad87d7d289a738f81'
ETH_USDC_NATIVE                = '\xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'

-- ===== Avalanche C-Chain (chain ID 43114) =====
AVAX_BRIDGE_MINTER_EOA         = '\xeb1bb70123b2f43419d070d7fde5618971cc2f8f'   -- EOA, sole bridgeRole/minter
AVAX_AEB_LEGACY                = '\xdac7bb7ce4ff441a235f08408e632fa1d799a147'   -- legacy, dead
AVAX_AB_CCTP_ROUTER            = '\xd835dbd135ad8a27214ecdee79e7a41337865648'
AVAX_CCTP_MESSAGE_TRANSMITTER  = '\x8186359af5f57fbb40c6b14a588d2a59c0c29880'
AVAX_USDC_NATIVE               = '\xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e'
-- BridgeTokens (.e)
AVAX_WETH_E                    = '\x49d5c2bdffac6ce2bfdb6640f4f80f226bc10bab'
AVAX_USDC_E                    = '\xa7d7079b0fead91f3e65f86e8915cb59c1a4c664'
AVAX_USDT_E                    = '\xc7198437980c041c805a1edcba50c1ce5db95118'
AVAX_DAI_E                     = '\xd586e7f844cea2f87f50152665bcbc2c279d8d70'
AVAX_WBTC_E                    = '\x50b7545627a5162f82a992c33b87adc75187b218'
AVAX_LINK_E                    = '\x5947bb275c521040051d82396192181b413227a3'
AVAX_AAVE_E                    = '\x63a72806098bd3d9520cc43356dd78afe5d386d9'
```

---

## 11. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 + selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from the canonical `BridgeToken.sol` (and the ChainBridge `Bridge`/`ERC20Handler` and Circle CCTP signatures). Cross-checked **live**: `Mint` (`0x918d77…`) confirmed in 6 logs on WETH.e (`0x49d5…0bAB`) over a 49k-block window; `Unwrap` (`0x37a067…`) confirmed on USDC.e (`0xA7D7…C664`); a Mint tx (`0xb3fa5a54…`) decoded to `from = 0xeb1bb701…`, `to = WETH.e`, selector `0x67fc19bb`. Every BridgeToken selector (`mint`/`unwrap`/`swap`/`migrateBridgeRole`/`addSwapToken`/`removeSwapToken`/`addSupportedChainId`/`swapSupply`/`chainIds`) verified **present** in both WETH.e and USDC.e runtime bytecode. AEB handler selectors (`executeProposal`/`withdraw`/`_bridgeAddress`/`_resourceIDToTokenContractAddress`/`getDepositRecord`/…) verified present in `0xdac7…9a147`'s bytecode (confirming it is the ChainBridge ERC20Handler, not the Bridge).
- **Addresses / existence:** parsed from `ava-labs/avalanche-bridge-resources` (`avalanche_contract_address.json` for the 25 `.e` tokens, `cctp/cctp_config.json` for the CCTP router + MessageTransmitters), the Avalanche Support bridge-address article, and Snowtrace/Etherscan labels. Each existence-checked via `eth_getCode`: deposit/mint addresses return `0x` (EOAs) with positive `eth_getTransactionCount`; BridgeTokens return ~12 716 B; AEB handler 7 317 B (ETH) / 10 028 B (AVAX); CCTP router 7 460 B (both). All AB addresses return `0x` on Base/BNB/Arbitrum/Optimism/Polygon (chain-absence confirmed).
- **Proxy classification:** EIP-1967 impl slot `0x360894…bbc` and admin slot `0xb53127…6103` read via `eth_getStorageAt` on WETH.e + USDC.e — both `0x0`, confirming the BridgeTokens are **immutable, not proxies**. No `Upgraded` topic exists; the only mutable authority is `bridgeRole` (rotated by `migrateBridgeRole`).
- **CCTP router identity:** `0xD835…5648` exposes `depositForBurn (0x6fd3504e)` but lacks `localMinter (0xcb75c11c)` and `localMessageTransmitter (0x2c121921)` → an AB wrapper, not Circle's canonical TokenMessenger; identical 7 460-B bytecode on ETH and AVAX.
- **Metadata (`eth_call`):** WETH.e `name() = "Wrapped Ether"`, `symbol() = "WETH.e"`, `decimals() = 18`; USDC.e `symbol() = "USDC.e"`, `decimals() = 6`; WBTC.e `decimals() = 8`; DAI.e/LINK.e/AAVE.e `decimals() = 18`.
- **Architecture (warden / 3-of-4 SGX enclave, lock-and-mint, AEB deprecation):** primary sources below.

Authoritative sources:
- Canonical repo: [`ava-labs/avalanche-bridge-resources`](https://github.com/ava-labs/avalanche-bridge-resources) — [`SmartContracts/BridgeToken.sol`](https://github.com/ava-labs/avalanche-bridge-resources/blob/main/SmartContracts/BridgeToken.sol), [`SmartContracts/Roles.sol`](https://github.com/ava-labs/avalanche-bridge-resources/blob/main/SmartContracts/Roles.sol), `avalanche_contract_address.json`, `token_list.json`, `cctp/cctp_config.json`, `SecurityAudits/v1_1` (Halborn).
- Bridge addresses: [Avalanche Support — "What is the Bridge's address on Ethereum and Avalanche?"](https://support.avax.network/en/articles/6354642-what-is-the-bridge-s-address-on-ethereum-and-avalanche) · [Avalanche Bridge FAQ](https://support.avax.network/en/articles/6092559-avalanche-bridge-faq).
- Architecture (SGX enclave, 3-of-4 wardens, AEB→AB): [Medium — "Avalanche Bridge: Secure Cross-Chain Asset Transfers Using Intel SGX"](https://medium.com/avalancheavax/avalanche-bridge-secure-cross-chain-asset-transfers-using-intel-sgx-b04f5a4c7ad1) · [LI.FI — "Avalanche Bridge — A Deep Dive"](https://li.fi/knowledge-hub/avalanche-bridge-a-deep-dive/).
- Explorers: [Etherscan — deposit EOA](https://etherscan.io/address/0x8eb8a3b98659cce290402893d0123abb75e3ab28) · [Etherscan — AEB handler](https://etherscan.io/address/0xdac7bb7ce4ff441a235f08408e632fa1d799a147) · [Snowtrace — WETH.e](https://snowtrace.io/address/0x49d5c2bdffac6ce2bfdb6640f4f80f226bc10bab).
- CCTP: [Circle CCTP docs / contract addresses](https://developers.circle.com/stablecoins/docs/cctp-getting-started).
