# Robinhood Stock Tokens — Topics, Selectors, Addresses (Robinhood Chain; Robinhood EU tokens on Arbitrum One)

**Status:** verified against live RPC on all nine target chains, Sourcify-verified source on Robinhood Chain, the Robinhood Chain docs, and the Robinhood assets API on 2026-10-30.
**Scope:** the tokenized US equities and ETFs ("Stock Tokens") that Robinhood Assets (Jersey) Limited issues on **Robinhood Chain (4663)**: the `AccessControlsRegistry` (beacon + roles + blocklist + global pause), the `StockFactory` (on-chain `uid → token` registry), the `Stock` implementation, and all 212 token proxies. §8 covers the separate, older **Robinhood EU** token family on **Arbitrum One (42161)**. Nothing of either family is deployed on Ethereum, Base, BNB, Avalanche, Optimism, Polygon PoS or Arc. Topics and selectors are chain-agnostic. Addresses are network-specific.

Each stock token is a 283 B **BeaconProxy**. The beacon address is an immutable inside the proxy bytecode, so the EIP-1967 beacon slot (`0xa3f0ad74…3d50`) holds it but the impl slot is empty. The beacon is the **`AccessControlsRegistry`** at `0xe10b6f6b…1b00`. That one contract does three jobs: it is the beacon (`implementation()`), it is the role store for **all** tokens (`hasRole`), and it holds the global **blocklist** (`isBlocked`) and the global **pause** (`paused`). A token never stores roles itself. It calls the registry on every privileged action and on every transfer.

New tokens come from the **`StockFactory`** (UUPS proxy `0x4783c67b…c046`). `deploy(bytes32 uid, string name, string symbol)` creates the BeaconProxy, calls `initialize`, and emits `Deployed(bytes32 indexed uid, address token, string name, string symbol)`. `tokenAddress(bytes32 uid)` is the **on-chain registry** that the docs mention: it returns the canonical token for a `uid`. The `uid` equals the `id` field of `GET https://api.robinhood.com/rhj/assets`.

Stock tokens are **not rebasing**. Dividends and splits change a UI multiplier (ERC-8056 "Scaled UI Amount"). `balanceOf` and `totalSupply` stay fixed. Every transfer, mint and burn emits **two** events: the ERC-20 `Transfer` and `TransferWithScaledUI(from, to, value, uiValue)`.

---

## 0. Contract families & versions

| Contract | Role | Proxy? |
|----------|------|--------|
| **AccessControlsRegistry** | Beacon for all stock tokens. Central OpenZeppelin `AccessControl` (13 roles). Global blocklist and global pause. | Not a proxy (2 332 B). `upgradeTo` changes the beacon target. |
| **StockFactory** | `deploy(uid,name,symbol)` (`TOKEN_DEPLOYER_ROLE`). `tokenAddress(uid)` registry view. `beacon()`. | UUPS (ERC-1967), upgrade by `FACTORY_UPGRADER_ROLE` |
| **Stock** (impl) | ERC-20 + EIP-2612 permit + ERC-8056 UI multiplier + per-token pause + oracle pause flag. | Implementation behind the beacon (11 614 B) |
| **Stock token** ×212 | One BeaconProxy per ticker (`TSLA`, `NVDA`, `SPY`, …). 18 decimals. | BeaconProxy (283 B, immutable beacon) |
| Unverified minter `0x13643b89…9c08` | Holds `MINTER_ROLE` and `BURNER_ROLE` since block 95.36 M. Source not published (§3.3). | ERC-1967 proxy |

The `Stock` implementation has not changed since launch. The registry emitted `Upgraded(0xb35490d6…)` at block 7 796 and again, to the same address, at block 657 134.

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

### 1.1 Stock token (emitted by each token proxy)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address indexed from, address indexed to, uint256 value)` | Mint = `from` 0x0. Burn and `adminBurn` = `to` 0x0. Raw (unscaled) amount. |
| `0x37e7f0db430edc9dd31bc66f25f8449353aa0818f503b906747dd8f286cd3802` | `TransferWithScaledUI(address indexed from, address indexed to, uint256 value, uint256 uiValue)` | Fires with **every** `Transfer` (from `_update`). `uiValue = value × uiMultiplier / 1e18` = underlying shares. |
| `0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925` | `Approval(address indexed owner, address indexed spender, uint256 value)` | |
| `0x2205df4534432b2f60654a3fdb48737ffdaf3e9edb1a498bd985bc026b15b055` | `UIMultiplierUpdated(uint256 oldMultiplier, uint256 newMultiplier, uint256 effectiveAtTimestamp)` | **Corporate action** (dividend or split). `effectiveAtTimestamp` can be in the future. |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` | Per-token pause (`TOKEN_PAUSER_ROLE`). Same topic0 as the registry-wide pause — check the emitter. |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` | |
| `0xe28b7053f432ae5400c6168140cbe15638399715519a0a39b16b505fb9fc9d9a` | `OraclePaused()` | Flag for price consumers. Does not stop transfers. |
| `0xa274116fec684497d55e11cc9516edaa8d206c8b5f84c4603e32572c37f8e6dd` | `OracleUnpaused()` | |
| `0x0030cda629fbac2efa8c01c1732f1dd9cbec41aae6ceae83906fe6c003b3a03c` | `MetaDataUpdated(string name, string symbol)` | Rename / ticker change (`METADATA_UPDATER_ROLE`). |
| `0x1cf3b03a6cf19fa2baba4df148e9dcabedea7f8a5c07840e207e5c089be95d3e` | `BeaconUpgraded(address indexed beacon)` | Fires once, in the deploy transaction. |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` | Fires once, in the deploy transaction. |
| `0x0a6387c9ea3628b88a633bb4f3b151770f70085117a15f9bf3787cda53f13d31` | `EIP712DomainChanged()` | Declared in the ABI. |

### 1.2 AccessControlsRegistry (`0xe10b6f6b…1b00`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0x75e91ce73c1d3352d8dd3610443539cd33dfe13b1de8f8caae54ec26dd0dc9cb` | `Blocked(address indexed account)` | **Blocklist add — applies to every stock token at once.** 246 events (177 distinct accounts) to block 101.8 M. |
| `0x5c272fb29e21b46870af1850afe89126704c55a7781cc100da3f733e15446c7d` | `Unblocked(address indexed account)` | 4 events (all for burn addresses `0xdead…`). |
| `0x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752` | `Paused()` | **Global pause** of all stock tokens (`PAUSER_ROLE`). One event (block 611 101). |
| `0xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933` | `Unpaused()` | Two events (blocks 610 644, 611 243). |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | **New `Stock` impl for all 212 tokens.** |
| `0x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d` | `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` | Role grant for all tokens (for example `MINTER_ROLE`). |
| `0xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b` | `RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender)` | |
| `0xbd79b86ffe0ab8e8776151514217cd7cacd52c909f66475c3af44e129f0b00ff` | `RoleAdminChanged(bytes32 indexed role, bytes32 indexed previousAdminRole, bytes32 indexed newAdminRole)` | |

### 1.3 StockFactory (`0x4783c67b…c046`)

| topic0 | Event | Notes |
|--------|-------|-------|
| `0xd9b0c6a1c0de228715ad0fa09f3259686ee84f8cc675e03ef7e47a9cdafa76d6` | `Deployed(bytes32 indexed uid, address token, string name, string symbol)` | **New stock token.** 212 events to block 101.8 M (first 19 698, last 99 358 760). Signature recovered from the topic0 and the log layout (impl source not published). |
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address indexed implementation)` | Factory UUPS upgrade. Impl `0xee351e53…ee0e` set at block 7 791, re-set at 645 152. |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64 version)` | |

### 1.4 Role hashes (`bytes32`, topic1 of `RoleGranted` / `RoleRevoked`)

| Role | Value | Gates |
|------|-------|-------|
| `DEFAULT_ADMIN_ROLE` | `0x0000000000000000000000000000000000000000000000000000000000000000` | All role admin. |
| `MINTER_ROLE` | `0x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6` | `Stock.mint` |
| `BURNER_ROLE` | `0x3c11d16cbaffd01df69ce1c404f6340ee057498f5f00246190ea54220576a848` | `Stock.burn` |
| `ADMIN_BURNER_ROLE` | `0x25e7ebc863fa4efd16243c82323b71f247c0cf439aca64c51b84a74afb738936` | `Stock.adminBurn` (ignores pause and blocklist) |
| `PAUSER_ROLE` | `0x65d7a28e3265b37a6474929f336521b332c1681b933f6cb9f3376673440d862a` | Registry global `pause` / `unpause` |
| `TOKEN_PAUSER_ROLE` | `0xe95e22ec6dbf4c911d1fae59680a3e9cb71dd35b3a1c697d232e4b01a8ff30a2` | Per-token `pause` / `unpause` |
| `ORACLE_PAUSER_ROLE` | `0x155fc2c2b00b801014447f9d3a1522625740f8e592e4c0b0bb7c5867c150aa11` | `pauseOracle` / `unpauseOracle` |
| `BLOCKER_ROLE` | `0x8f2e0057cd5e35397007bcc8f5418f73dd64cc6e4073a0276563f247c3079037` | `blockAccounts` / `unblockAccounts` |
| `MULTIPLIER_UPDATER_ROLE` | `0x7158cf42e4a4f01c5456c8d75cdbd375748d45e9db7e812f5bcd18844122b615` | `updateMultiplier` |
| `METADATA_UPDATER_ROLE` | `0x7f5260842512b02356ff92de24be96e7e1aac2e234d9371b076ac2b4cddda61e` | `setMetadata` |
| `TOKEN_DEPLOYER_ROLE` | `0x5f077d4e72bed5b3b14877559c782788e60c3fbb27bf29d3586097d8fa36bbeb` | `StockFactory.deploy` |
| `BEACON_UPGRADER_ROLE` | `0x5ab8bd28475e0dc8d5764e9ce50f85ffe2f14ec40c5b74e45f541485ad510c39` | Registry `upgradeTo` (all tokens) |
| `FACTORY_UPGRADER_ROLE` | `0xb4e5de7340a2fee2ff9be79f5ec0e8feae4b633bc8cc663711520e08f24984f8` | Factory UUPS upgrade |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Stock token

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x40c10f19` | `mint(address,uint256)` | `MINTER_ROLE`. Reverts when paused or when `to` / sender is blocked. |
| `0x9dc29fac` | `burn(address,uint256)` | `BURNER_ROLE`. Burns from any address, no allowance. Reverts when paused or blocked. |
| `0x06dd0419` | `adminBurn(address,uint256)` | `ADMIN_BURNER_ROLE`. **No pause or blocklist check.** Seizure path. |
| `0x5ffe6146` | `updateMultiplier(uint256)` | `MULTIPLIER_UPDATER_ROLE`. Effective now. Reverts when paused. |
| `0xbad60f18` | `updateMultiplier(uint256,uint256)` | Scheduled: `(newMultiplier, effectiveAt)`. |
| `0x8456cb59` | `pause()` | `TOKEN_PAUSER_ROLE`. |
| `0x3f4ba83a` | `unpause()` | `TOKEN_PAUSER_ROLE`. |
| `0x253ea980` | `pauseOracle()` | `ORACLE_PAUSER_ROLE`. |
| `0x0fab6865` | `unpauseOracle()` | `ORACLE_PAUSER_ROLE`. |
| `0x51335b50` | `setMetadata(string,string)` | `METADATA_UPDATER_ROLE`. |
| `0x812eb8b2` | `initialize(bytes32,string,string)` | Factory only, once. |
| `0xa9059cbb` | `transfer(address,uint256)` | Checks pause and blocklist (sender, recipient). |
| `0x23b872dd` | `transferFrom(address,address,uint256)` | Checks pause and blocklist (from, to, spender). |
| `0x095ea7b3` | `approve(address,uint256)` | Checks pause and blocklist. |
| `0xd505accf` | `permit(address,address,uint256,uint256,uint8,bytes32,bytes32)` | EIP-2612. EIP-712 name = token `name()`, version `"1"`. |
| `0xa60bf13d` | `uiMultiplier()` | view. 1e18 = 1.0. |
| `0xdc767007` | `newUIMultiplier()` | view. Pending value. |
| `0x97a4064f` | `effectiveAt()` | view. |
| `0x437a9958` | `balanceOfUI(address)` | view. Underlying shares. |
| `0x9bea6429` | `totalSupplyUI()` | view. |
| `0x5c975abb` | `paused()` | view. Token pause **or** registry pause. |
| `0x86c75e74` | `tokenPaused()` | view. Token pause only. |
| `0x7706ba52` | `oraclePaused()` | view. |
| `0xf514ce36` | `uid()` | view → `bytes32` asset id. |
| `0x50c09be3` | `ACCESS_CONTROLLED_REGISTRY()` | view → `0xe10b6f6b…1b00`. |
| `0xd5025625` | `terms()` | pure → `"https://robinhood.com/stocktoken/rhj"`. Good fingerprint. |

### 2.2 AccessControlsRegistry

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x6abf7081` | `blockAccounts(address[])` | `BLOCKER_ROLE`. |
| `0xfaed47fd` | `unblockAccounts(address[])` | `BLOCKER_ROLE`. |
| `0xfbac3951` | `isBlocked(address)` | view. |
| `0x8456cb59` | `pause()` | `PAUSER_ROLE`. Global. |
| `0x3f4ba83a` | `unpause()` | `PAUSER_ROLE`. |
| `0x5c975abb` | `paused()` | view. |
| `0x3659cfe6` | `upgradeTo(address)` | `BEACON_UPGRADER_ROLE`. New impl for all tokens. |
| `0x5c60da1b` | `implementation()` | view (IBeacon). |
| `0x2f2ff15d` | `grantRole(bytes32,address)` | |
| `0xd547741f` | `revokeRole(bytes32,address)` | |
| `0x36568abe` | `renounceRole(bytes32,address)` | |
| `0x91d14854` | `hasRole(bytes32,address)` | view. |

### 2.3 StockFactory (selectors read from bytecode)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb2670cc5` | `deploy(bytes32,string,string)` | `TOKEN_DEPLOYER_ROLE`. Called by `0x5516b345…e000`. |
| `0x97bb3ce9` | `tokenAddress(bytes32)` | view → token for a `uid`. Checked for all 212 tokens. |
| `0x59659e90` | `beacon()` | view. |
| `0x50c09be3` | `ACCESS_CONTROLLED_REGISTRY()` | view. |
| `0x4f1ef286` | `upgradeToAndCall(address,bytes)` | UUPS. |

---

## 3. Addresses — Robinhood Chain (chain ID 4663)

All verified with `eth_getCode` on `https://rpc.mainnet.chain.robinhood.com` on 2026-10-30.

### 3.1 Core

| Role | Address | One-liner |
|------|---------|-----------|
| **AccessControlsRegistry** (beacon) | `0xe10b6f6b275de231345c20d14ab812db62151b00` | 2 332 B. `implementation()` = Stock impl. Deployed block 7 662 by `0x074377a7…1279`. Sourcify-verified. |
| **StockFactory** (registry) | `0x4783c67b63de2b358ac5951a7d41f47a38f3c046` | 163 B ERC-1967 proxy. Impl `0xee351e53bce6aaf106428358838197c91e36ee0e` (4 926 B, not verified). |
| **Stock** (impl) | `0xb35490d6f9163de4f80d88dc75c3516eb64c5ae2` | 11 614 B. `src/Stock.sol:Stock`, solc 0.8.33, Sourcify-verified. |
| Token deployer (EOA) | `0x5516b3451d4d6c9f63353fe7bc9537477ecce000` | Holds `TOKEN_DEPLOYER_ROLE`. Sent all 212 `deploy` transactions. |

### 3.2 Role holders (registry, live on 2026-10-30)

| Role | Holder | Type |
|------|--------|------|
| `DEFAULT_ADMIN_ROLE` | `0xd6f8378f8e440c65f8382f5f2728c78dfd55b66d` | no code |
| `MINTER_ROLE` | `0x2b94105fff37630f98e1f24811dad588fc5c3a87`, `0x13643b89b19245201b29d556edde5cf18f749c08` | no code; proxy (§3.3) |
| `BURNER_ROLE` | `0x6e40b50a40c1db42a85a0e8fe8ff7d9cbfc2d8c1`, `0x13643b89…9c08` | no code; proxy |
| `ADMIN_BURNER_ROLE` | `0x957b6de6525c63349f7619743ef1e0ad93cd74d4` | no code |
| `PAUSER_ROLE` | `0xe7bcb188254bc6ebbff63014dfed4cd4a024f22a` | no code |
| `TOKEN_PAUSER_ROLE` | `0xfccf56b674113d9c4eb0f9b3370930ced9e6ab23` | no code |
| `ORACLE_PAUSER_ROLE` | `0x7369d100c00f28e45d779ac9d4b1c7afa61e4abc` | no code |
| `BLOCKER_ROLE` | `0x913ca87347391218e5de2c17c5a0aeba8b0b28fd` | no code |
| `MULTIPLIER_UPDATER_ROLE` | `0x92905e8d0e2301ba143215b8d86d63ffd4188143` | no code |
| `METADATA_UPDATER_ROLE` | `0xcba16c2b9048af033c5b34e43dd1d47d1358524a` | no code |
| `TOKEN_DEPLOYER_ROLE` | `0x5516b3451d4d6c9f63353fe7bc9537477ecce000` | no code |
| `BEACON_UPGRADER_ROLE` | `0xcd8c6182e7c6ca3b5156d6a90a67719d7e2be094` | no code |
| `FACTORY_UPGRADER_ROLE` | `0x697e774d60c1a3769f2ed0b919aacf17be0ae553` | no code |

Derived from the full `RoleGranted` / `RoleRevoked` history of the registry. The deployer `0x074377a7…1279` revoked its own `DEFAULT_ADMIN_ROLE` and `BEACON_UPGRADER_ROLE` at blocks 8 692–8 695. A test grant of `MINTER_ROLE` to `0x…dead` (block 616 387) was revoked at block 618 536.

### 3.3 Unverified minter/burner `0x13643b89…9c08`

`0x13643b89b19245201b29d556edde5cf18f749c08` is a 163 B ERC-1967 proxy (impl `0x31e111c1cd0406ae357d5041f8459fbfb4fe9113`, 21 928 B, source not published). It was deployed at block 81 887 440 by `0x3e50d0f647489203141a3a2f981a710373ef7f96`. It received `MINTER_ROLE` (block 95 361 240) and `BURNER_ROLE` (block 95 363 462) on the registry, so it can mint and burn **every** stock token. Its bytecode selectors include `USDG()`, `custodyWallet()`, `stockConfig(address)`, `marketConfig(uint8)`, `closePosition(address,bytes32,uint256)`, `getPrice(address)`, `LIQUIDATOR_ROLE()` and `MARKET_ADMIN_ROLE()`. Its logs reference the SGOV token, which is the only asset with `replicatorEnabled: true` in the assets API. Its event signatures are unknown. The two most frequent topic0s (to block 101.8 M) are `0xf88be3e07dff19e195850c8c668d568f76ecfd90008ce39073f38bc8c732e416` (570 737 logs; topic1 = a stock token, data = two words) and `0xe3ecd87efd1b57ea2aab236e504308817f02352aff5f66653bf637e3bed9a056` (7 135 logs). Treat this contract as a privileged supply source of unconfirmed purpose.

### 3.4 Token list (212 tokens; symbol → address)

All 212 are 283 B BeaconProxies with beacon `0xe10b6f6b…1b00` (checked on every token with `eth_getCode` and `ACCESS_CONTROLLED_REGISTRY()`). For every token, `StockFactory.tokenAddress(uid())` returns the token itself. 203 tokens are in the assets API (`GET https://api.robinhood.com/rhj/assets`, all `ASSET_STATUS_ACTIVE`). Nine have a factory `Deployed` event but are not in the API (marked). Names drop the common suffix `" • Robinhood Token"`. `mult` is `uiMultiplier()` / 1e18 where it is not 1.0. On 2026-10-30 no token was paused, no oracle was paused, and no multiplier change was pending.

| Symbol | Address | Name | Notes |
|--------|---------|------|-------|
| AAOI | `0x521cf887e6531c6f667b5bc4d896e5d9bfe8eb2e` | Applied Optoelectronics |  |
| AAPL | `0xaf3d76f1834a1d425780943c99ea8a608f8a93f9` | Apple | mult 1.000566 |
| ABCL | `0x3139d77ace0cbaa5bdfd38bd1f1911a794af0b0e` | Abcellera Biologics |  |
| ADBE | `0x232b8ed6377be97813853b0ac104c4cda8378d1b` | Adobe |  |
| AEHR | `0x5f604fba1162193a4388a5dfa56f556f3e133cc2` | Aehr |  |
| AEIS | `0xfaf9cb261b5fcc1f404bb10cd39c5c6c1974e612` | Advanced Energy |  |
| ALAB | `0x748c32c3ca24edf31ea597db1f3d330a7a6da3dc` | Astera Labs, Inc. |  |
| AMAT | `0x36046893810a7e7fce501229d57dc3fc8c8716d0` | Applied Materials | mult 1.000045 |
| AMBA | `0x99d9d8663545151603863c5acbd6fc3218899009` | Ambarella |  |
| AMC | `0x05a3d1cd21d0c88145e82600e62e7e496e0f222b` | AMC Entertainment |  |
| AMD | `0x86923f96303d656e4aa86d9d42d1e57ad2023fdc` | AMD |  |
| AMKR | `0xdd356aa38f40a7b7076755ac854b6fbb1f0d305b` | Amkor Technology | mult 1.000867 |
| AMZN | `0x12f190a9f9d7d37a250758b26824b97ce941bf54` | Amazon |  |
| ANET | `0x28babd556b60e53663b8615036479a29c2cdd1bf` | Arista |  |
| APLD | `0xb8dbf92f9741c9ac1c32115e78581f23509916fd` | Applied Digital |  |
| APP | `0xa249baf1063af884807c1e1400aef7784836917e` | AppLovin |  |
| ARM | `0x666716999e75d2652398ff830bbc2e485946e140` | Arm Holdings plc | not in assets API; zero supply |
| ASML | `0x47f93d52cbec7c6d2cfc080e154002370a60daea` | ASML Holding NV | mult 1.000878 |
| ASTS | `0x1af6446f07eb1d97c546afc8c9544cbdf3ad5137` | AST SpaceMobile |  |
| AUR | `0x373c06c4f7bde527d7dae4ba169e42b55e393ced` | Aurora Innovation |  |
| AVAV | `0xf6290b5e7c26502e2da514c31509849718ea76a5` | AeroVironment |  |
| AVGO | `0x156e175dd063a8ce274c50654ef40e0032b3fbcf` | Broadcom | mult 1.001257 |
| AXON | `0xc27dbd474af5181c5a8777903690d8d262d12648` | Axon |  |
| AXTI | `0x141eea040c2250eec0314e336975e81f85f6585e` | AXT |  |
| BA | `0x4d21483a44bf67a86b77e3da301411880797d452` | Boeing |  |
| BABA | `0xad25ac6c84d497db898fa1e8387bf6af3532a1c4` | Alibaba |  |
| BB | `0x48e39e56acdba37b09020c0b734a613c9a2f100a` | Blackberry |  |
| BE | `0x822cc93ffd030293e9842c30bbd678f530701867` | Bloom Energy |  |
| BMNR | `0x9a7842eded60b0fe1e03eec342c82a397c821ed0` | BitMine Immersion Technologies |  |
| BND | `0x2f62fc9fabb470c690f141c28340ed832bb27020` | Vanguard Total Bond Market ETF | zero supply |
| BULL | `0xcef9027c7d6985b85f0ba431125073529a947a68` | Webull |  |
| CBRS | `0x5c90450bbb4273d7b2f17cf6917aeb237a569679` | Cerebras Systems |  |
| CCL | `0x9651342cea770ae9a2969ba2a52611523146aef9` | Carnival Corporation | mult 1.021486 |
| CEG | `0xae517a2903e68bd929dfd15be875f8369d53e94a` | Constellation Energy |  |
| CELH | `0x8cf07c5a878945185d327aaa6e33faa95f95e7bf` | Celsius |  |
| CIEN | `0x44f6d488021f8233b9416294d1fe9b1fee28382d` | Ciena |  |
| CLOV | `0x62200915e7deab1ec7f79fb246dadbb80eacddd0` | Clover Health Investments |  |
| CLS | `0xbf449977089c718c004a66c554b26b94ef3ad4de` | Celestica |  |
| CLSK | `0xcbb95bbf36099d34da091dc6fa6f49efa257cee3` | CleanSpark |  |
| COHR | `0x92f9f459f1a9a5ad266b182be7bffd1c6c666894` | Coherent |  |
| COIN | `0x6330d8c3178a418788df01a47479c0ce7ccf450b` | Coinbase |  |
| COST | `0x4ea005168d7f09a7a0ba9d1def21a479950e44c2` | Costco | mult 1.000612 |
| CRCL | `0xdf0992e440dd0be65bd8439b609d6d4366bf1cb5` | Circle Internet Group |  |
| CRDO | `0x4d67253bc223e6b0e104f1084c1fb2b669ddc41b` | Credo Technology Group |  |
| CRM | `0xd95b44124e475743a7589e68f3d74008a5536d44` | Salesforce | mult 1.001148 |
| CRWD | `0xea72ecca2d0f6bfa1394dbbcff85b52cd4233931` | CrowdStrike Holdings | mult 4.000000 |
| CRWV | `0x5f10a1c971b69e47e059e1dc91901b59b3fb49c3` | CoreWeave |  |
| CSCO | `0xf543967eebb6f1917992ef0e68de63ab07a5a0da` | Cisco Systems | mult 1.002675 |
| CTSH | `0x63d5a3b6939a33f1e75d8bcd85759858239600db` | Cognizant |  |
| CVNA | `0xa4f319104089fe321dc8093c6e707d4fe190a988` | Carvana |  |
| DDOG | `0x27c99fbde9d0d2aa4f4bfb4943f237843ddf6958` | Datadog |  |
| DELL | `0x941ae714ec6d8130c7b75d67160ca08f1e7d11dd` | Dell | mult 1.001020 |
| DIS | `0x501b1b3b79750313ad2c4cccd08586c4c17d7283` | Disney |  |
| DJT | `0x1d11f0496982706c5e14a514d4e79f2e6bde4516` | Trump Media & Technology Group |  |
| DOCN | `0xc02f12b9fe9e707079ec0d546f3050d3f6c1f8bd` | DigitalOcean |  |
| DRAM | `0x33c18e2cc8ae9ae486e785090d86b2ce632ff994` | Roundhill Memory ETF | not in assets API; zero supply |
| ELF | `0x39ec44bee4f6a116c6f9b8de566848a985c53c60` | e.l.f. Beauty |  |
| EWT | `0x1c690498150252222c275a5ced69d3a6b1f52d5e` | iShares MSCI Taiwan Capped ETF |  |
| EWY | `0x7f0abef0c07280f82c6a08ead09ded6bae2c13fc` | iShares MSCI South Korea fund |  |
| F | `0x25c288e6d899b9bc30160965ad9644c67e73be0c` | Ford Motor | mult 1.000146 |
| FICO | `0xa48f22a46c0f1c46ca7d111cb6c137c271987180` | Fair Isaac |  |
| FIG | `0x41f4267525a8aff329540ef24fd83d9044758b33` | Figma |  |
| FISV | `0x9ece29a4a2397c0a35fb5fa8ee2b9509130a98cc` | Fiserv |  |
| FIX | `0x93dbb1d2dc5d63f4abacff30485273f538df68ac` | Comfort Systems |  |
| FLNC | `0x282e87451e10fa6679bc7d76c69be44cd3fc777c` | Fluence Energy |  |
| FLY | `0x03bc731ffb162cdd7b98d3c6542bfc291126075d` | Firefly Aerospace Inc. |  |
| FTNT | `0x3fb8976980d486084b2eb4a404bd12e72823958f` | Fortinet |  |
| FUTU | `0xeb30663bdff0622ef4e4e5cbb4e975f19f33f51d` | Futu Holdings |  |
| GDX | `0xbdfa7a06458aa26b8e736e0fc87ad37c3bb8ac2e` | VanEck Gold Miners ETF |  |
| GE | `0x63b814ddbd6bf339f25fed8c36158a008d5b373e` | General Electric | mult 1.001049 |
| GEV | `0x94b8aae43a1ccc08aa64b7d1f29b4d920af4a0c9` | GE Vernova |  |
| GLD | `0xc9a981fee1f9dec688bb123ccdecc63d0debfc4e` | SPDR Gold Trust |  |
| GLW | `0x7c04e6a3368f2a1de3874f0e80d2e0a1a9915da6` | Corning |  |
| GLXY | `0x2d427692e928fa156ec22acfabafa0447c5805b7` | Galaxy Digital Inc. |  |
| GME | `0x1b0e319c6a659f002271b69db8a7df2f911c153e` | GameStop |  |
| GOOGL | `0x2e0847e8910a9732eb3fb1bb4b70a580adad4fe3` | Alphabet Class A | mult 1.000194 |
| HII | `0xeb61c0ed490a367d4e3631ccf8a74b3bfc7e775d` | Huntington Ingalls |  |
| HIMS | `0xccee82fe024c36fa15e1005ede3e9e4787e23d09` | Hims & Hers Health |  |
| HPE | `0x59dd09d4900c2e4b5f75b7c0d4e6796fcc234cb1` | HP Enterprise | mult 1.001717 |
| HWM | `0xaea445c5f3db1a462998ccc422a875a361ee5d99` | Howmet Aerospace |  |
| IBM | `0x980dcf6766fa79f5cf0c4aadb3ab477ff15a9619` | IBM |  |
| IBRX | `0x7c148f74ac7445d1f28366b7fcdc6792a9fcd0cf` | ImmunityBio, |  |
| INDA | `0xacef2e09adb47ad6abebad9ff06689e60615c2b6` | iShares MSCI India ETF |  |
| INFQ | `0xb853bc83a753342a4f8320ea680b4b1e84118d21` | Infleqtion |  |
| INOD | `0xf1953dab6fad537488d5a022361ffaa8b4c95ec6` | Innodata |  |
| INTC | `0xc72b96e0e48ecd4dc75e1e45396e26300bc39681` | Intel |  |
| INTU | `0x56d23bee5f41a7120170b0c603dae30128e460e9` | Intuit | mult 1.003227 |
| IONQ | `0x558378e000d634a36593e338ebacdd6207640efe` | IonQ |  |
| IREN | `0xf0ab0c93be6f41369d302e55db1a96b3c430212d` | IREN Limited |  |
| JBL | `0xeaf2512dfc1beac608f8794b3793cd4e02894aa6` | Jabil Inc. |  |
| JEPQ | `0x565d3ff42d7d880287e5796b4c708632be0ca098` | J.P. Morgan Exchange-Traded Fund Trust JPMorgan Nasdaq Equity Premium Income ETF | not in assets API; zero supply |
| JNJ | `0x03dfbbe0ac4e7bcdafd08ed41a400326b77d8c80` | Johnson & Johnson | mult 1.000021 |
| JOBY | `0xb334c5ce741b80b5b671f47f5c269cb193fe8e24` | Joby Aviation |  |
| JPM | `0x07c44da0848960bff894f17584db8b2f60b2409e` | JPMorgan Chase |  |
| KLAC | `0x96b933c74ecb4a0926b9210cef7b743ef46be2e9` | KLA |  |
| KSS | `0x12e3c047bf9aecaf9ddc98c05c31bfd1dd043993` | Kohls Corporation | mult 1.004610 |
| KTOS | `0x7fd06a4d81ccfa3f351394e144d5191874c31313` | Kratos Defense & Security Solutions |  |
| LHX | `0x48d60243c66437c6ac3c2495be94747aed5dfe25` | L3Harris | mult 1.004922 |
| LITE | `0x8ef20885f94e3d9bc7eb3080279188bd5ed7c08c` | Lumentum |  |
| LLY | `0x8005d266423c7ea827372c9c864491e5786600ea` | Eli Lilly | mult 1.000002 |
| LMT | `0x329fcaceb9ad6f9580dd5f643fed0646900d043c` | Lockheed | mult 1.000021 |
| LRCX | `0x57b0030166db0c31690d1a5aa167e2e26e2c29a4` | Lam Research Corp | mult 1.000733 |
| LULU | `0x4e62068525ab11fe768e29dfd00ef909b9803016` | Lululemon |  |
| LUNR | `0xa5d4968421ba94814be3b136b15cf422101ac1a3` | Intuitive Machines |  |
| MCD | `0x2fdaa4604f10f4ae7f66fa48a174bcd25b1ece20` | McDonald's |  |
| MDB | `0xddf2266b79abf0b48898959b0ed6e6adf512be74` | MongoDB |  |
| META | `0xc0d6457c16cc70d6790dd43521c899c87ce02f35` | Meta Platforms | mult 1.000541 |
| MOD | `0xc6cbad1016b38b797610c25e1dc7d95988b1f362` | Modine |  |
| MPWR | `0x52d50d0280ad1054b43f052bd70a49a212a1b128` | Monolithic Power Systems | mult 1.001003 |
| MRNA | `0x43b07d15ce533bec5476d70c22a78a1b2b662155` | Moderna |  |
| MRVL | `0x62fd0668e10d8b72339be2dcf7643001688ff13b` | Marvell Technology | mult 1.000151 |
| MSFT | `0xe93237c50d904957cf27e7b1133b510c669c2e74` | Microsoft | mult 1.000413 |
| MSTR | `0xec262a75e413fafd0df80480274532c79d42da09` | Strategy Inc. |  |
| MTSI | `0xc93f4d80e268ab922e871bd169156c3cc41894e6` | MACOM |  |
| MU | `0xff080c8ce2e5feadaca0da81314ae59d232d4afd` | Micron Technology | mult 1.000183 |
| MXL | `0x48961813349333209994750ffa89b3c5c22ec969` | MaxLinear |  |
| NASA | `0x6ddb95405db6179012bff2fff7e0f8d49cf00137` | Tema Space Innovators ETF | not in assets API; zero supply |
| NAVN | `0xf7181b63fdb858558a74ba96bc42732684cd7965` | Navan |  |
| NBIS | `0x9d9c6684f596f66a64c030b93a886d51fd4d7931` | Nebius Group |  |
| NET | `0x116f00968269b7bfbad4109ce591d6e74c0601d4` | Cloudflare, Inc. Class A common stock |  |
| NFLX | `0xe0444ef8bf4ed74f74fd73686e2ddf4c1c5591e8` | Netflix |  |
| NNE | `0xbef75684c43c4ea7bd18dd532a2244674ee8b926` | Nano Nuclear Energy |  |
| NOK | `0x25ee805ac369b6e3f8bf5764c682d34a37cb7175` | Nokia | not in assets API; zero supply |
| NOW | `0x0c3260af4b8f13a69c4c2dfb84fd667890cdfa14` | ServiceNow |  |
| NU | `0x408c14038a04f7bd235329e26d2bf569ee20e250` | Nu |  |
| NVDA | `0xd0601ce157db5bdc3162bbac2a2c8af5320d9eec` | NVIDIA | mult 1.000775 |
| NVTS | `0xbe6702d7b70315376dc48a3293f24f0982f86386` | Navitas Semiconductor |  |
| OKLO | `0x8b2f88497f15a18e9d4ffa1a8ffb8538399ae774` | Oklo |  |
| ON | `0xbbd09f72b025360fee5c928053dca6248d35be54` | ON Semiconductor |  |
| ONTO | `0x8ff63eaeee3fe54ba450c4f5538064ec5a893aef` | Onto Innovation |  |
| ORCL | `0xb0992820e760d836549ba69bc7598b4af75dee03` | Oracle | mult 1.004763 |
| OUST | `0x40e7a279850e443f582059ae5dc1c3b6563e6395` | Ouster |  |
| P | `0x1cdad396db64bda184d5182a97dd9b3c62100b7d` | Everpure |  |
| PANW | `0xb039597ed45cba7b6e2fb9e8be51802969cee5be` | Palo Alto Networks |  |
| PATH | `0xfb2664f07b6aadd29ea7a59d8859b1aeb8645cda` | UiPath |  |
| PEACH_DEFI_1 | `0xbbb6c29bcc3a1028a2b54310df73f4f7a3bcb373` | PEACH_DEFI_1 | not in assets API; zero supply |
| PENG | `0x9b23573b156b52565012f5ce02cdf60afbaa70be` | Penguin Solutions |  |
| PFE | `0x7066a64c24e4206cd62e83bf198c1e7eb361f51e` | Pfizer |  |
| PL | `0xaa4d64474c172010ab57719cb9951e6142a100d3` | Planet Labs |  |
| PLTR | `0x894e1ec2d74ffe5aef8dc8a9e84686accb964f2a` | Palantir Technologies |  |
| POET | `0xcf6b2d875361be807eafa57458c80f28521f9333` | POET Technologies |  |
| POWL | `0x237c16d66590f67b886d978acd362eaead8b18c7` | Powell Industries |  |
| PR | `0x4189f0c66ebbb0bfef1c31f763131361ef32f77c` | Permian Resources | mult 1.004478 |
| PWR | `0x9ab02ead789b6903c3c44d0ed32f9c707cdf12fd` | Quanta |  |
| PYPL | `0xa45abdc77918f7b9199b022eee400c0bc5712bd2` | PayPal |  |
| QBTS | `0xc583c60aef9dc401da72cec1b404743a93cea1cc` | D-Wave Quantum Inc. Common Stock |  |
| QCOM | `0x0f17206447090e464c277571124dd2688e48aea9` | Qualcomm | mult 1.001228 |
| QNT | `0xb7edfe2f33c1ac06830a971dfb559bde8a2a3d76` | Quantinuum Inc. Class A | not in assets API; zero supply |
| QQQ | `0xd5f3879160bc7c32ebb4dc785f8a4f505888de68` | Invesco QQQ | mult 1.000701 |
| QUBT | `0x59818904ab4ce163b3ce4ffb64f2d6ca02c434b4` | Quantum Computing |  |
| RBLX | `0xf0c4bf4c582cb3836e98394b1d4e7b7281101be8` | Roblox |  |
| RCAT | `0xfde6b5d9bb419b10c23268c74e369abff39c0460` | Red Cat |  |
| RDDT | `0x05b37fb53a299a1b874a619e1c4c404d52c36f4c` | Reddit |  |
| RDW | `0x92ef19e82bd8ff36661de838d5eae7e5cef0effe` | Redwire |  |
| RGTI | `0x284358abc07f9359f19f4b5b4ac91901be2597ba` | Rigetti Computing |  |
| RIVN | `0xb1bf26c1d20ff267a4f93550d1e0d06ac40a114b` | Rivian Automotive |  |
| RKLB | `0x3b14c39e89d60d627b42a1a4ca45b5bb45fc12e2` | Rocket Lab Corporation |  |
| RUN | `0x756bc80af765c82da966a788858d65adf14f3793` | Sunrun |  |
| RVI | `0xb02e3e1b7f68559427c2d9100566e4f3cc5b7611` | Robinhood Ventures Fund I | not in assets API; zero supply |
| SATS | `0x95052ddcd5dc25641657424a8cf04834997e1730` | EchoStar |  |
| SCHD | `0xd63abb2c13d7a8421a8017a712802053568e3c1d` | Schwab US Dividend Equity ETF | mult 1.005539 |
| SGOV | `0x92fd66527192e3e61d4ddd13322aa222de86f9b5` | iShares 0-3 Month Treasury Bond | mult 1.007187 |
| SHOP | `0xf53f66751b1eff985311b693531e3290f600c410` | Shopify |  |
| SHY | `0xbe274710bf3d9567e1b290ef6a5f9f90ca016fd8` | iShares 1-3 Year Treasury Bond ETF | mult 1.002055 |
| SIMO | `0x77e655e37f4d913fb9540e0d541d824171a60e81` | Silicon Motion |  |
| SKHY | `0x84cab63bc87912e71ad199ff14a0ba45de68fef8` | SK hynix Inc. American Depositary Shares | mult 1.000060 |
| SLS | `0x285b231728c7e4333799183df1094d775246a535` | SELLAS Life Sciences |  |
| SLV | `0x411efb0e7f985935daec3d4c3ebaea0d0ad7d89f` | iShares Silver Trust |  |
| SMCI | `0xc01aa1fecec0605b13bc84874ff7256c0f5f562a` | Super Micro Computer |  |
| SMH | `0x072f979c2cac8e1391b0162a87fee094bf8744a0` | VanEck Semiconductor ETF |  |
| SMR | `0x1eebee7f74517e0279dfb09d25b0407beec3fdd6` | NuScale Power |  |
| SNAP | `0xf6589f11bc40b669e584073f428b05562f568733` | Snap |  |
| SNDK | `0xb90a19ff0af67f7779aff50a882a9cff42446400` | Sandisk Corporation |  |
| SNOW | `0xba0cab75495255d0cb58e22b648bfed4ecd1f47e` | Snowflake |  |
| SOFI | `0x98e75885157c80992a8d41b696d8c9c6fb30a926` | SoFi Technologies |  |
| SOUN | `0x6e3dfd9f7e1649baa14d25cac18c94d62db10a54` | SoundHound AI |  |
| SOXX | `0x75742c18bc1f1c5c5f448f4c9d9c6f66dafaaa38` | iShares Semiconductor ETF | mult 1.000451 |
| SPCX | `0x4a0e65a3eccec6dbe60ae065f2e7bb85fae35eea` | Space Exploration Technologies Corp. Class A Common Stock |  |
| SPMO | `0xad622320e520de39e72d41ef07438c3fd3354875` | Invesco S&P 500 Momentum ETF | mult 1.002025 |
| SPY | `0x117cc2133c37b721f49de2a7a74833232b3b4c0c` | SPDR S&P 500 ETF Trust | mult 1.001718 |
| TE | `0xb1969f6604ca1ae7a2cd3f1827876e914594ca2d` | T1 Energy |  |
| TEAM | `0x5b97476b922f3305131b8f0b9d333172e87f4aae` | Atlassian Corporation |  |
| TEM | `0xb1cc0ec7db69cf43539119814df40071b9d61793` | Tempus AI |  |
| TER | `0x2778c5024d5ca2cdb0f8ead671ffc69963adcd9c` | Teradyne | mult 1.000648 |
| TSEM | `0x89776d4cd68193597a2fc132cfac1fde36ccea8a` | Tower Semiconductor |  |
| TSLA | `0x322f0929c4625ed5bad873c95208d54e1c003b2d` | Tesla |  |
| TSM | `0x58ffe4a942d3885baa22d7520691f611ef09e7aa` | Taiwan Semiconductor Manufacturing | mult 1.002729 |
| TTD | `0x0b5fb4031cae9163db10b169ee72685f0edc8545` | Trade Desk |  |
| TTWO | `0x5e81213613b6b86eab4c6c50d718d34359459786` | Take-Two Interactive Software |  |
| UBER | `0xbd335aa5a1693f0121a5c0ef18a080e9958da78b` | Uber |  |
| UMC | `0x0e6e67ba88e7b5d9b67636a215c76779b948de79` | United Microelectronics |  |
| UNH | `0xcf364ea52787e289de6f32077834056e3e70d6a8` | UnitedHealth | mult 1.004242 |
| UPS | `0xf23250dac154d05bb671cb0d0ebef3c635c79ce2` | UPS | mult 1.002209 |
| USAR | `0xd917b029c761d264c6a312bbbcda868658ef86a6` | USA Rare Earth |  |
| USO | `0xa30fa36db767ad9ed3f7a60fc79526fb4d56d344` | United States Oil Fund |  |
| V | `0x9bff87700337babf5099e99f322f888dafb1d551` | Visa |  |
| VICR | `0x6006ed4b2f94110851ff7509d97d034f0eed9226` | Vicor |  |
| VRT | `0xfa78c12e6488814a0262e4e802749a4a737d5fb7` | Vertiv | mult 1.000163 |
| VSAT | `0x26dcbfb34fc83cabd6990f449674efdc6097ff85` | ViaSat |  |
| VST | `0x561e2a49212b7ccf47f2744ccb83e200722fadbc` | Vistra | mult 1.001115 |
| VTI | `0x0594134df3f171a354d9c85ebd65b7a6148f6d09` | Vanguard Morningstar Total Stock Market ETF | mult 1.001751 |
| WDAY | `0x82da4646242e1d962e96e932269dc644c94a9caa` | Workday |  |
| WDC | `0xf52597345a8edf418bc4071b4a35112472277d3e` | Western Digital | mult 1.000218 |
| WEEK | `0xc93a8c440cea26d7445df01729f193b27965099f` | Roundhill Weekly T-Bill ETF | not in assets API; mult 2.006183 |
| WULF | `0x348be1a8663f15edde5cdf8a96bb69078f7ab6fd` | TeraWulf |  |
| WYFI | `0x9e7abd3c9139d14e4c86dce0e455aab7a0c2fb3e` | WhiteFiber, Inc. |  |
| XLK | `0x15cd20759ce7f3285c29a319de2d1a2e098c6f43` | State Street Technology Select Sector SPDR ETF | mult 1.000804 |
| XNDU | `0xa8eb3bccbf2017ee7cbfb652eb51cf2e1b153289` | Xanadu Quantum |  |
| XOM | `0xf9b46d3d1b22199d4d1025a9cedb540a33f1a2d5` | ExxonMobil Holdings Corporation | mult 1.001040 |
| ZETA | `0xe674c5c071821f48bb2d12cadb83617eff438f9e` | Zeta Global | zero supply |
| ZM | `0x44c4f142009036cf477ed2d09932051843137cf1` | Zoom |  |
| ZS | `0x7dc013eb55e436f30d7ed1afe4e36d6e45e3c3f7` | Zscaler |  |

---

## 4. Chains with no Robinhood Chain stock tokens

`eth_getCode` returns `0x` for the registry, the factory, the `Stock` impl, TSLA, NVDA and the §3.3 minter on **Ethereum, Base, BNB, Avalanche, Arbitrum One, Optimism, Polygon PoS and Arc**. The assets API lists chain 4663 only for all 203 assets (no other `deployments[]` entry).

---

## 5. Cross-chain summary

| Chain | ID | Registry / beacon | Factory | Stock tokens |
|-------|----|-------------------|---------|--------------|
| Robinhood Chain | 4663 | `0xe10b…1b00` | `0x4783…c046` | 212 (§3.4) |
| Arbitrum One | 42161 | `0x7ba8…d2f9` (EU family, §8) | not enumerated | EU family, not enumerated |
| Ethereum · Base · BNB · Avalanche · Optimism · Polygon · Arc | — | — | — | — |

---

## 6. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Stock token** ×212 | BeaconProxy (OZ v5) with **immutable** beacon | 283 B code embeds `e10b6f6b…1b00`. EIP-1967 beacon slot = registry. Impl slot empty. | Registry `upgradeTo` (`BEACON_UPGRADER_ROLE`). One call upgrades all 212 tokens. |
| **AccessControlsRegistry** | Not a proxy | 2 332 B, impl slot empty. | Immutable code. Roles via `DEFAULT_ADMIN_ROLE`. |
| **StockFactory** | UUPS (ERC-1967) | 163 B proxy, impl slot `0xee351e53…`. | `FACTORY_UPGRADER_ROLE`. |
| **§3.3 minter** | ERC-1967 proxy | 163 B, impl slot `0x31e111c1…`. | Unknown (has `UPGRADER_ROLE()` selector). |

Watch `Upgraded(address)` `0xbc7cd75a…2d3b` **from the registry** to catch a new `Stock` implementation. The token proxies never emit `Upgraded`.

---

## 7. Detection invariants & gotchas

1. **One registry controls 212 tokens.** A `RoleGranted(MINTER_ROLE, x)` on `0xe10b…1b00` gives `x` mint rights on every stock token. A `Blocked(x)` freezes `x` on every token. A registry `Paused()` stops every token. Monitor the registry first.
2. **`Paused()` / `Unpaused()` have one topic0 for two scopes.** The registry emits them for a global pause. A token emits them for its own pause. Check the emitter. `paused()` on a token returns true for either scope; `tokenPaused()` returns the token scope only.
3. **Each transfer emits two logs.** `Transfer` (raw amount) and `TransferWithScaledUI` (raw + UI amount). Do not double-count volume. Use `Transfer` for raw balances and `uiValue` for share-equivalent amounts.
4. **Corporate actions do not move balances.** A split or dividend emits only `UIMultiplierUpdated` on the token. No `Transfer` fires. Underlying shares = raw × `uiMultiplier()` / 1e18. Chainlink feeds already include the multiplier. 50 of 212 tokens had a multiplier above 1.0 on 2026-10-30 (dividends).
5. **Scheduled multipliers.** `updateMultiplier(uint256,uint256)` sets a future `effectiveAt`. The event fires at scheduling time, not at the effective time. `uiMultiplier()` switches silently when `block.timestamp ≥ effectiveAt`.
6. **`adminBurn` skips pause and blocklist.** It is the seizure path (`ADMIN_BURNER_ROLE`). It emits only `Transfer(from → 0x0)` + `TransferWithScaledUI`. Attribute a burn to `adminBurn` with the `0x06dd0419` selector, not by the event.
7. **`burn(address,uint256)` needs no allowance.** `BURNER_ROLE` can burn from any non-blocked holder.
8. **The blocklist is in the registry, not in the token.** A token emits no event when an account is blocked. Use `Blocked` / `Unblocked` on the registry. The registry emitted 246 `Blocked` events for 177 distinct accounts: 244 in blocks 43 543–44 953, then one at 51 003 and one at 495 713. On 2026-10-30, `isBlocked` was true for 175 of them (the two burn addresses `0x…dead` were unblocked).
9. **New tokens:** index `Deployed` on the factory. The `uid` is the stable asset id; ticker and name can change through `MetaDataUpdated`. Use `tokenAddress(uid)` to resolve the canonical token.
10. **Not every deployed token is listed.** Nine factory tokens are absent from the assets API (`WEEK`, `ARM`, `NASA`, `RVI`, `NOK`, `DRAM`, `QNT`, `JEPQ`, `PEACH_DEFI_1`). Eight of them had zero supply. Do not treat API absence as "not a Robinhood token".
11. **Fingerprint:** `terms()` returns `"https://robinhood.com/stocktoken/rhj"` and `ACCESS_CONTROLLED_REGISTRY()` returns `0xe10b…1b00`. A token with the same symbol but other answers is not canonical.
12. **The EU tokens on Arbitrum are a different model** (rebasing shares, other registry). Do not reuse §1 topics for them without checking (§8).

---

## 8. Robinhood EU stock tokens on Arbitrum One (chain ID 42161) — separate family

Robinhood Europe launched stock tokens on Arbitrum One in 2025. These are **not** the Robinhood Chain tokens. They use the same design idea (a central access-control registry that is also the beacon) but an **older, share-based** token implementation. Neither the registry nor any Robinhood Chain address exists on Arbitrum.

| Role | Address | One-liner |
|------|---------|-----------|
| **EU AccessControlsRegistry** (beacon) | `0x7ba834024816fa5de620def31d03d12e6f20d2f9` | 2 436 B. Same selector set as the Robinhood Chain registry (`blockAccounts`, `isBlocked`, `pause`, `upgradeTo`, `implementation`, AccessControl). |
| **EU stock impl** | `0xa28662e327a78e516377c5499e01c2a71181690e` | 12 602 B. Not source-verified. Share model: `multiplier()`, `sharesOf`, `totalShares`, `mintShares`, `burnShares`, `transferShares`, `balanceToShares`, `sharesToBalance`, `updateMultiplier(uint256)`, `burn(uint256)`. |
| AAPL (example) | `0x012c768e5162d5ed965d45935634efce705a57ac` | 295 B BeaconProxy. `name()` "Apple", 18 dec. `ACCESS_CONTROLLED_REGISTRY()` = `0x7ba8…d2f9`. |
| SPY (example) | `0x95a1335e5acb6b0da544cf58c04c2d57cf028d80` | 295 B BeaconProxy. |
| Holder wallet | `0x44c7c4ab4757aa49b50a8082cb1649c51ef7bc43` | Moved 489 distinct EU tokens in the last 400 000 Arbitrum blocks. |

Differences that matter for monitoring: EU names have no `" • Robinhood Token"` suffix; balances are **rebasing** (`balanceOf = shares × multiplier`); press reports describe an allow-list on transfers. The EU token list (several thousand contracts by press counts) and the EU factory were **not enumerated**. The EU event set was not verified from source; recompute topic0s from a verified ABI before you alert on it.

---

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_TRANSFER                    = '\xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
TOPIC_TRANSFER_WITH_SCALED_UI     = '\x37e7f0db430edc9dd31bc66f25f8449353aa0818f503b906747dd8f286cd3802'
TOPIC_UI_MULTIPLIER_UPDATED       = '\x2205df4534432b2f60654a3fdb48737ffdaf3e9edb1a498bd985bc026b15b055'
TOPIC_PAUSED                      = '\x9e87fac88ff661f02d44f95383c817fece4bce600a3dab7a54406878b965e752'
TOPIC_UNPAUSED                    = '\xa45f47fdea8a1efdd9029a5691c7f759c32b7c698632b563573e155625d16933'
TOPIC_ORACLE_PAUSED               = '\xe28b7053f432ae5400c6168140cbe15638399715519a0a39b16b505fb9fc9d9a'
TOPIC_ORACLE_UNPAUSED             = '\xa274116fec684497d55e11cc9516edaa8d206c8b5f84c4603e32572c37f8e6dd'
TOPIC_METADATA_UPDATED            = '\x0030cda629fbac2efa8c01c1732f1dd9cbec41aae6ceae83906fe6c003b3a03c'
TOPIC_BLOCKED                     = '\x75e91ce73c1d3352d8dd3610443539cd33dfe13b1de8f8caae54ec26dd0dc9cb'
TOPIC_UNBLOCKED                   = '\x5c272fb29e21b46870af1850afe89126704c55a7781cc100da3f733e15446c7d'
TOPIC_UPGRADED                    = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_ROLE_GRANTED                = '\x2f8788117e7eff1d82e926ec794901d17c78024a50270940304540a733656f0d'
TOPIC_ROLE_REVOKED                = '\xf6391f5c32d9c69d2a47ea670b442974b53935d1edc7fd64eb21e047a839171b'
TOPIC_STOCK_DEPLOYED              = '\xd9b0c6a1c0de228715ad0fa09f3259686ee84f8cc675e03ef7e47a9cdafa76d6'
-- ===== Role hashes =====
ROLE_MINTER                       = '\x9f2df0fed2c77648de5860a4cc508cd0818c85b8b8a1ab4ceeef8d981c8956a6'
ROLE_BURNER                       = '\x3c11d16cbaffd01df69ce1c404f6340ee057498f5f00246190ea54220576a848'
ROLE_ADMIN_BURNER                 = '\x25e7ebc863fa4efd16243c82323b71f247c0cf439aca64c51b84a74afb738936'
ROLE_PAUSER                       = '\x65d7a28e3265b37a6474929f336521b332c1681b933f6cb9f3376673440d862a'
ROLE_TOKEN_PAUSER                 = '\xe95e22ec6dbf4c911d1fae59680a3e9cb71dd35b3a1c697d232e4b01a8ff30a2'
ROLE_BLOCKER                      = '\x8f2e0057cd5e35397007bcc8f5418f73dd64cc6e4073a0276563f247c3079037'
ROLE_MULTIPLIER_UPDATER           = '\x7158cf42e4a4f01c5456c8d75cdbd375748d45e9db7e812f5bcd18844122b615'
ROLE_BEACON_UPGRADER              = '\x5ab8bd28475e0dc8d5764e9ce50f85ffe2f14ec40c5b74e45f541485ad510c39'
ROLE_TOKEN_DEPLOYER               = '\x5f077d4e72bed5b3b14877559c782788e60c3fbb27bf29d3586097d8fa36bbeb'
-- ===== Selectors (chain-agnostic) =====
SEL_MINT                          = '\x40c10f19'
SEL_BURN                          = '\x9dc29fac'
SEL_ADMIN_BURN                    = '\x06dd0419'
SEL_UPDATE_MULTIPLIER             = '\x5ffe6146'
SEL_UPDATE_MULTIPLIER_SCHEDULED   = '\xbad60f18'
SEL_PAUSE                         = '\x8456cb59'
SEL_UNPAUSE                       = '\x3f4ba83a'
SEL_PAUSE_ORACLE                  = '\x253ea980'
SEL_SET_METADATA                  = '\x51335b50'
SEL_BLOCK_ACCOUNTS                = '\x6abf7081'
SEL_UNBLOCK_ACCOUNTS              = '\xfaed47fd'
SEL_REGISTRY_UPGRADE_TO           = '\x3659cfe6'
SEL_FACTORY_DEPLOY                = '\xb2670cc5'
SEL_FACTORY_TOKEN_ADDRESS         = '\x97bb3ce9'
SEL_UI_MULTIPLIER                 = '\xa60bf13d'
-- ===== Addresses (network-specific) =====
RH_STOCK_REGISTRY                 = '\xe10b6f6b275de231345c20d14ab812db62151b00'
RH_STOCK_FACTORY                  = '\x4783c67b63de2b358ac5951a7d41f47a38f3c046'
RH_STOCK_IMPL                     = '\xb35490d6f9163de4f80d88dc75c3516eb64c5ae2'
RH_STOCK_DEPLOYER                 = '\x5516b3451d4d6c9f63353fe7bc9537477ecce000'
RH_STOCK_MINTER_UNVERIFIED        = '\x13643b89b19245201b29d556edde5cf18f749c08'
RH_TSLA                           = '\x322f0929c4625ed5bad873c95208d54e1c003b2d'
RH_NVDA                           = '\xd0601ce157db5bdc3162bbac2a2c8af5320d9eec'
RH_AAPL                           = '\xaf3d76f1834a1d425780943c99ea8a608f8a93f9'
RH_SGOV                           = '\x92fd66527192e3e61d4ddd13322aa222de86f9b5'
ARB_EU_STOCK_REGISTRY             = '\x7ba834024816fa5de620def31d03d12e6f20d2f9'
ARB_EU_STOCK_IMPL                 = '\xa28662e327a78e516377c5499e01c2a71181690e'
-- All 212 token addresses: §3.4. Membership test: ACCESS_CONTROLLED_REGISTRY() = RH_STOCK_REGISTRY.
```

---

## 10. Verification & sources

How constants in this doc were verified (2026-10-30):

- **Topic0 / selectors:** recomputed locally as `keccak256(signature)` from the Sourcify-verified ABIs of `Stock` (`0xb35490d6…`) and `AccessControlsRegistry` (`0xe10b6f6b…`). Role hashes match `src/Roles.sol`. The factory has no published source: its selectors were read from runtime bytecode (`PUSH4` scan) and matched to known signatures. The `Deployed` signature was recovered by hashing candidates against the observed topic0 `0xd9b0c6a1…` and checked against the log layout (indexed `uid`, then `address`, `string`, `string`).
- **Live logs:** the full registry history (blocks 0–101 806 697) gave 246 `Blocked`, 4 `Unblocked`, 1 `Paused`, 2 `Unpaused`, 2 `Upgraded`, 18 `RoleGranted`, 3 `RoleRevoked`. The full factory history gave 212 `Deployed` and 2 `Upgraded`. `Initialized` and `BeaconUpgraded` were seen in the TSLA deploy transaction `0xc4c1c585…80a8` (block 34 767). `UIMultiplierUpdated` was seen on AAPL at block 36 345 344 (old 1e18, new 1.000566e18, `effectiveAt` 1 786 720 366, a scheduled dividend adjustment). A chain-wide back-fill of `UIMultiplierUpdated`, `MetaDataUpdated` and `OraclePaused` was not completed (RPC rate limits); per-token state was read live instead.
- **Addresses:** token list from the factory `Deployed` events and from `GET https://api.robinhood.com/rhj/assets` (203 assets). For all 212 tokens: `eth_getCode` (283 B), `ACCESS_CONTROLLED_REGISTRY()`, `tokenAddress(uid())`, `symbol()`, `name()`, `totalSupply()`, `uiMultiplier()`, `newUIMultiplier()`, `effectiveAt()`, `tokenPaused()` and `oraclePaused()` were read live.
- **Proxies:** EIP-1967 impl, admin and beacon slots read live on the tokens, the factory and the minter.
- **Chain coverage:** core addresses return `0x` on the other eight chains. The Arbitrum EU family was found from the transfers of the EU holder wallet and read live (§8).

Authoritative sources:
- [Robinhood Chain docs — Stock Tokens](https://docs.robinhood.com/chain/stock-tokens) · [Building with Stock Tokens](https://docs.robinhood.com/chain/building-with-stock-tokens) · [Stock Token APIs](https://docs.robinhood.com/chain/stock-token-apis) · [Token Contracts](https://docs.robinhood.com/chain/contracts).
- Robinhood assets API: `https://api.robinhood.com/rhj/assets`.
- Sourcify: `https://sourcify.dev/server/v2/contract/4663/0xb35490d6f9163de4f80d88dc75c3516eb64c5ae2` · `https://sourcify.dev/server/v2/contract/4663/0xe10b6f6b275de231345c20d14ab812db62151b00`.
- Explorers: [Robinhood Chain Blockscout](https://robinhoodchain.blockscout.com/address/0xe10b6f6b275de231345c20d14ab812db62151b00) · [Arbiscan (EU registry)](https://arbiscan.io/address/0x7ba834024816fa5de620def31d03d12e6f20d2f9).
- Press on the EU family: [The Block — 213 tokenized stock contracts on Arbitrum](https://www.theblock.co/post/360783/robinhood-pays-5-in-transaction-fees-to-deploy-213-tokenized-stock-contracts-on-arbitrum).
