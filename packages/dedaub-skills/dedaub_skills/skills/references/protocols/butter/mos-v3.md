# Butter Network — MAP Omnichain Service V3 (MOS V3) — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon + MAP relay)

**Status:** verified against live RPC on Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), the MAP relay chain (MAPO, 22776), and the canonical `butternetwork/butter-mos-contracts` (`evmv3/`) repo on 2026-06-09.
**Scope:** the **current** MAP Omnichain Service bridge — `Bridge` on spoke chains, `BridgeAndRelay` on the MAP relay, plus `FeeService`, `AuthorityManager`, and the relay-only `TokenRegisterV3` / `VaultTokenV3`. Topics + selectors are **chain-agnostic**; addresses are network-specific (and largely **identical across chains** by deterministic deploy — always key on `(chainId, address)`). The legacy MOS V2 bridge is documented separately in [mos-v2.md](mos-v2.md); the user-facing router layer in [router.md](router.md).

MOS V3 is the **value-transport core** of Butter Network. It is a hub-and-spoke design: every cross-chain transfer routes through the **MAP relay chain (MAPO, EVM chainId 22776)**. On a **spoke** chain the deployed implementation is `Bridge`; on the **relay** it is `BridgeAndRelay` (which additionally holds the token vaults, fee distribution, and light-client proof verification). Both inherit the same `BridgeAbstract` base, so the **core cross-chain events (`MessageOut`, `MessageIn`, `MessageRelay`) and the `swapOutToken` entrypoint are identical on every chain**.

The on-chain wiring of one transfer:

```
source spoke:  Router.swapAndBridge → Bridge.swapOutToken  → emit MessageOut   (orderId X)
MAP relay:     light-client verify  → BridgeAndRelay.messageIn → emit DepositIn/CollectFee → emit MessageRelay (orderId X)
dest spoke:    light-client verify  → Bridge.messageIn        → emit MessageIn  (orderId X) → Receiver.onReceived
```

**Single deterministic bridge address on every EVM chain:** `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` (leading-zero vanity). It is an **EIP-1967 UUPS proxy** (133-byte `ERC1967Proxy`, not an EIP-1167 minimal-proxy clone) whose implementation **differs per chain**. Governance is an OpenZeppelin **AccessManager** (`AuthorityManager`) at `0xACC31A6756B60304C03d6626fc98c062E4539CCA`, also the same on every chain.

---

## 0. Contract families & versions

| Contract | Role | Where | Proxy? |
|----------|------|-------|--------|
| **Bridge** (`Bridge.sol`) | Spoke-chain MOS endpoint. `swapOutToken` (lock/burn out), `messageIn` (verify+release). Emits `MessageOut`/`MessageIn`. | every spoke (all 7 targets) | UUPS proxy `0x0000317Bec…` |
| **BridgeAndRelay** (`BridgeAndRelay.sol`) | MAP-relay MOS endpoint. Adds vault settlement, fee split (`CollectFee`), chain registry, `relayExecute`, `messageIn`+`MessageRelay`. | MAP relay (22776) only | UUPS proxy `0x0000317Bec…` (same addr, different impl) |
| **FeeService** (`FeeService.sol`) | Per-destination-chain message/gas fee quoting (`getNativeFee`). | all chains | non-proxy (3.2 KB) |
| **AuthorityManager** (`AuthorityManager.sol`) | OZ AccessManager — role/permission registry; `restricted` modifier auth for every admin call. | all chains | non-proxy (9.9 KB) |
| **TokenRegisterV3** (`TokenRegisterV3.sol`) | Relay-side token↔vault mapping, cross-chain token map, fee config. | MAP relay only | UUPS proxy `0xe00314b0…` |
| **VaultTokenV3** (`VaultTokenV3.sol`) | ERC-20 vault share per bridged asset (usdt/usdc/eth/btc/…); accrues `DepositVault`/`WithdrawVault`. | MAP relay only | per-token (deterministic) |
| **DepositWhitelist** / **ProtocolFee** (periphery) | Relay-side deposit gating + protocol-fee accounting. | MAP relay only | non-proxy |

> **Avalanche note:** MOS V3 is **fully deployed** on Avalanche (bridge + authority + feeService all present), even though the *router* layer is only partially deployed there (see router.md).

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

All values recomputed locally with keccak256 on 2026-06-09. `MessageOut`/`MessageIn` additionally confirmed against live Ethereum + Base bridge logs (§Verification).

### 1.1 Bridge / BridgeAndRelay — core cross-chain (the workhorses) — emitter = `0x0000317Bec…`

| topic0 | Event | Where |
|--------|-------|-------|
| `0x469059a9fd182ad3741bdd67b925e15056d35262609ea83393db7e8fb5a05ab1` | `MessageOut(bytes32 indexed orderId, uint256 indexed chainAndGasLimit, bytes payload)` | **source spoke** — the outbound transfer. |
| `0x13d3a5b2d6aaada5c31b5654f99c2ab9587cf9a53ee4b2e25b6c68a8dfaa4472` | `MessageIn(bytes32 indexed orderId, uint256 indexed chainAndGasLimit, address token, uint256 amount, address to, bytes from, bytes payload, bool result, bytes reason)` | **destination spoke + relay** — value released to `to`; `result`/`reason` = exec outcome. |
| `0xf01fbdd2fdbc5c2f201d087d588789d600e38fe56427e813d9dced2cdb25bcac` | `MessageRelay(bytes32 indexed orderId, uint256 indexed chainAndGasLimit, bytes payload)` | **MAP relay only** — re-emitted toward the destination chain. |
| `0x48f234c2c5fdc7ed34779457fd485590e07604056ed028aa16e7b8a137478b26` | `MessageTransfer(address initiator, address referrer, address sender, bytes32 orderId, bytes32 transferId, address feeToken, uint256 fee)` | message-only (non-asset) transfer + fee. |
| `0x058db03136cae65e3a953afcf3307ee1e68c448c334786bdccc2a382ca72c97d` | `GasInfo(bytes32 indexed orderId, uint256 indexed executingGas, uint256 indexed executedGas)` | gas accounting on inbound execution. |

> **`chainAndGasLimit` is a packed `uint256`:** `fromChain (8 bytes) | toChain (8 bytes) | reserved (8 bytes) | gasLimit/gasUsed (8 bytes)`. Decode by shifting, not by treating it as a plain id.

### 1.2 BridgeAndRelay — relay-only (vault + fee settlement) — emitter = `0x0000317Bec…` on MAPO (22776)

| topic0 | Event |
|--------|-------|
| `0x03a171b17616c5776c3570767fa662ecee7e8c6d5ecd488b3bb9a319311f7a1e` | `CollectFee(bytes32 indexed orderId, address indexed token, uint256 isFromChain, uint256 baseFee, uint256 bridgeFee, uint256 messageFee, uint256 vaultFee, uint256 protocolFee)` |
| `0x1715d70ef1746a264496faed0d62deacc731a251670681188dbceac9ad870e31` | `DepositIn(uint256 indexed fromChain, address indexed token, bytes32 indexed orderId, bytes from, address to, uint256 amount)` |
| `0xf341246adaac6f497bc2a656f546ab9e182111d630394f0c57c710a59a2cb567` | `Withdraw(address token, address reicerver, uint256 vaultAmount, uint256 tokenAmount)` *(note: `reicerver` is the on-chain misspelling — does not change the hash)* |
| `0x6f94bb991e9abc3f3f557a46ef5c9959644fe3fb9927adea628e254f5258126a` | `RegisterChain(uint256 chainId, bytes bridge, uint8 chainType)` |
| `0x28d0e3b789c60bc4629db5d1be2252c5a8318f306119aa5f7abffd092383e083` | `SetDistributeRate(uint256 id, address to, uint256 rate)` |

### 1.3 Bridge (spoke) admin — emitter = `0x0000317Bec…`

| topic0 | Event |
|--------|-------|
| `0x14c31aacfac9e1b12448ca6d440a799c047f0eb36ac5145aa2f18dd4796373f5` | `SetRelay(uint256 _chainId, address _relay)` |
| `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` | `Transfer(address,address,uint256)` (ERC-20 lock/mint of bridged tokens) |

### 1.4 VaultTokenV3 (relay only) — per-asset vault share

| topic0 | Event |
|--------|-------|
| `0xd12854a02fa0a0a18ec43fb173bee96f8dc9a80f8633af72baa374833949f329` | `DepositVault(address indexed token, address indexed to, uint256 vaultValue, uint256 value)` |
| `0xc3f7cb75c4b290a1a7f47394c576e48664f75b813851c4f2d196f914485f710b` | `WithdrawVault(address indexed token, address indexed to, uint256 vaultValue, uint256 value)` |
| `0x305b6563ce4afe6a5531c0feaac753c35459d1a05d26dcb572790eb9a3469836` | `UpdateVault(address indexed token, uint256 fromChain, uint256 toChain, uint256)` — distinct topic0 from `SetDistributeRate` (`0x28d0e3b7…`); the two do **not** collide. Emitter = VaultTokenV3. |

### 1.5 FeeService

| topic0 | Event |
|--------|-------|
| `0xffb40bfdfd246e95f543d08d9713c339f1d90fa9265e39b4f562f9011d7c919f` | `SetFeeReceiver(address receiver)` |

### 1.6 Proxy / access-control standards (all contracts)

| topic0 | Event |
|--------|-------|
| `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` | `Upgraded(address implementation)` — **watch on the bridge proxy** for impl rotations. |
| `0xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2` | `Initialized(uint64)` |
| `0x2f658b440c35314f52658ea8a740e05b284cdc84dc9ae01e891f21b8933e7cad` | `AuthorityUpdated(address)` (OZ AccessManaged) |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 Bridge / BridgeAndRelay — state-changing

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xb899f904` | `swapOutToken(address _initiator, address _token, bytes _to, uint256 _amount, uint256 _toChain, bytes _bridgeData)` → `bytes32 orderId` | **the bridge entrypoint** — called by a Router. Emits `MessageOut`. |
| `0x9ce638ec` | `swapOutTokenWithOrderId(address _initiator, address _token, bytes _to, uint256 _amount, uint256 _toChain, bytes32 orderId, bytes _bridgeData)` → `bytes32` | relay-only; caller restricted to `fusionReceiver`. |
| `0xfb0f97a8` | `depositToken(address _token, address _to, uint256 _amount)` → `bytes32 orderId` | deposit into the relay vault (liquidity provision); emits `DepositIn` on the relay. |
| `0xe282dcdd` | `messageIn(uint256 _chainId, uint256 _logParam, bytes32 _orderId, bytes _receiptProof)` | verify source-chain proof + execute. Emits `MessageIn`. |
| `0xf3fef3a3` | `withdraw(address _vaultToken, uint256 _vaultAmount)` | relay-only LP withdrawal; emits `Withdraw`. |
| `0xc879c6d8` | `withdrawFee(address receiver, address token)` | admin fee sweep; emits `WithdrawFee`. |
| `0x7fec8d38` | `trigger()` | pause/unpause toggle (`restricted`). |

### 2.2 Bridge / BridgeAndRelay — views

| Selector | Signature | Returns |
|----------|-----------|---------|
| `0xbf7e214f` | `authority()` | `address` — the AuthorityManager (= `0xACC31A67…`). |
| `0x5c975abb` | `paused()` | `bool`. |
| `0x5c60da1b` | `implementation()` | not on the bridge (read the EIP-1967 slot instead — see §Proxies). |

### 2.3 FeeService

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0xeef5add1` | `getNativeFee(address _token, uint256 _gasLimit, uint256 _toChain)` → `(uint256, address)` | message/gas fee quote. **Confirmed present** on the live ETH FeeService (selector accepted). |

### 2.4 Proxy upgrade surface (UUPS)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x4f1ef286` | `upgradeToAndCall(address newImpl, bytes data)` | `payable`; `restricted`. Emits `Upgraded`. |
| `0x52d1902d` | `proxiableUUID()` | `bytes32` = the EIP-1967 slot. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. **The bridge, authority, and feeService addresses below are identical on every one of the seven target chains** (deterministic deploy) — only the bridge *implementation* differs (§Proxies). Chains 4–10 therefore show only divergences.

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (`Bridge`, UUPS proxy, 133 B) | `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` | Spoke MOS endpoint. Live impl `0x12bfb3b58ad02a0df40ee7186d26266c52d0109c`. Emits §1.1 events. |
| **AuthorityManager** (`AuthorityManager`, 9.9 KB) | `0xACC31A6756B60304C03d6626fc98c062E4539CCA` | OZ AccessManager — admin/role registry; not a proxy. `authority()` of every MOS contract resolves here. |
| **FeeService** (`FeeService`, 3.2 KB) | `0xfeE31a1FD7FcA0E05428ff751242e46F6D5769a6` | Per-chain fee/gas quoting; not a proxy. |

**Not deployed on Ethereum:** `BridgeAndRelay`, `TokenRegisterV3`, `VaultTokenV3`, `DepositWhitelist`, `ProtocolFee` — these are **MAP-relay-only** (§7). The Ethereum bridge runs the spoke `Bridge` impl, not `BridgeAndRelay`.

## 4. Addresses — Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137)

Verified via `eth_getCode` on each chain's publicnode RPC. **Bridge, AuthorityManager, FeeService share the exact Ethereum literals on all six** — shown once:

| Role | Address (identical on all 7 targets) |
|------|--------------------------------------|
| Bridge (proxy) | `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` |
| AuthorityManager | `0xACC31A6756B60304C03d6626fc98c062E4539CCA` |
| FeeService | `0xfeE31a1FD7FcA0E05428ff751242e46F6D5769a6` |

Per-chain **divergence is only the bridge implementation** (read live from the EIP-1967 slot):

| Chain | ID | Bridge impl (live `0x0000317Bec…` → EIP-1967 impl) | FeeService size |
|---|---|---|---|
| Ethereum | 1 | `0x12bfb3b58ad02a0df40ee7186d26266c52d0109c` | 3217 B |
| Base | 8453 | `0x862761d6d52e9e812a8c22e6e6a39e186e59a33d` | 3217 B |
| BNB | 56 | `0x62844d1e812cf17f20eaa8d49e33f5f6ba6f3e77` | 3197 B |
| Avalanche | 43114 | `0xf1d15f0e7a7d56168010cd454bd4541603bbeed4` | 3217 B |
| Arbitrum | 42161 | `0xc45c34ebdb808b5383b71ea85e8378af994d7082` | 3217 B |
| Optimism | 10 | `0x7912e89440e57352302d30730849268eb863ece4` | 3217 B |
| Polygon | 137 | `0x774444afb39a9555e9a70e60d7eb20b73f822716` | 3197 B |

All six run the spoke `Bridge` impl (not `BridgeAndRelay`). **No relay-only contracts** (`BridgeAndRelay`, `TokenRegisterV3`, `VaultTokenV3`) on any of the seven targets — those live exclusively on MAPO.

## 5. Cross-chain summary

| Chain | ID | Bridge `0x0000317Bec…` | AuthorityManager | FeeService | Relay contracts |
|---|---|---|---|---|---|
| Ethereum | 1 | ✓ (spoke `Bridge`) | ✓ | ✓ | — |
| Base | 8453 | ✓ | ✓ | ✓ | — |
| BNB | 56 | ✓ | ✓ | ✓ | — |
| Avalanche | 43114 | ✓ | ✓ | ✓ | — |
| Arbitrum | 42161 | ✓ | ✓ | ✓ | — |
| Optimism | 10 | ✓ | ✓ | ✓ | — |
| Polygon | 137 | ✓ | ✓ | ✓ | — |
| **MAP relay (MAPO)** | **22776** | ✓ (`BridgeAndRelay`) | ✓ | ✓ | TokenRegisterV3, VaultTokenV3 (×many), DepositWhitelist, ProtocolFee |

**Vanity-address tell:** the bridge `0x0000317Bec…` has six leading hex zeros — distinctive in any tx/log scan. Same literal everywhere ⇒ **always key on `(chainId, address)`**.

**Counterparty chains outside the seven** that the bridge also services (from the repo `deploy.json` + on-chain `RegisterChain`): MAP relay (22776), zkSync Era (324), Linea, Scroll, Mantle, Blast (81457), Merlin, AINN, Conflux, Kaia/Klaytn, X Layer, Unichain, **Tron** (non-EVM address form), **NEAR** (separate Rust `map-ominichain-service`), and BTC/SOL/TON/XRP/DOGE handled as relay vault tokens.

## 6. Addresses — MAP relay chain (MAPO, chain ID 22776)

Verified via `eth_getCode` on `https://rpc.maplabs.io` on 2026-06-09. This is **not one of the seven targets** but is the canonical L1 anchor of the whole system — recorded here as a finding. Source: `evmv3/deployments/deploy.json` key `Mapo`.

| Role | Address | One-liner |
|------|---------|-----------|
| **BridgeAndRelay** (proxy) | `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` | Same vanity address; runs the *relay* impl (vault settlement, fee split, light-client verify). |
| **TokenRegisterV3** | `0xe00314b05919156E7B16F4E89c78d2174E20E366` | Token↔vault map, cross-chain token map, fee config. |
| TokenRegisterV2 (legacy) | `0xE00219ecDbD02e102998fF208724671c4709e188` | MOS V2 register (deprecated). |
| AuthorityManager | `0xACC31A6756B60304C03d6626fc98c062E4539CCA` | Same literal as spokes. |
| FeeService | `0xfeE31a1FD7FcA0E05428ff751242e46F6D5769a6` | Same literal as spokes. |
| DepositWhitelist | `0x27172dA6b48DB586B5261ff90D6D1D5F2C1c1363` | Relay deposit gating. |
| ProtocolFee | `0xc9041777D421b5fcB272f7Cd8C66757246F1f9F1` | Protocol-fee accounting/treasury split. |
| VaultTokenV3 — usdt | `0xA91925E64731b2848a431F2418A22BEFf2efdc5d` | per-asset vault share (V2 vault gen). |
| VaultTokenV3 — usdc | `0x7dF2EBb365741c6bAb8dA70a7720c3A1708D918a` | |
| VaultTokenV3 — eth | `0xf01F35bE88b63c8c83294409f134a1D589C554F1` | |
| VaultTokenV3 — btc | `0xf7daC642E96C5Cc86d8E33aB8835323666868b18` | |
| VaultTokenV3 — mapo | `0xC9C260ca8BBb1c75690C6D8e96585346C69Ee557` | native MAPO vault share. |

> The relay also holds an older `vault` set (usdt `0x14321A7f…`, eth `0xc8b81aF9…`, usdc `0xAB51Ef1f…`, btc `0xCA188B28…`, bnb `0x2C5880D4…`, sol `0xa468f64c…`, …) — these are the original `VaultTokenV3` deployment; the `vaultV2` set above is the current one.

## 7. Proxies (old & new)

EIP-1967 implementation slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`; beacon slot `0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50`.

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **Bridge / BridgeAndRelay** (`0x0000317Bec…`) | **UUPS** (ERC-1967 + ERC-1822) | 133-byte `ERC1967Proxy` (not an EIP-1167 minimal-proxy clone — impl is held in the ERC-1967 slot, not inlined); impl slot **populated** (per-chain impl, §4); **admin slot = 0x0**; beacon slot = 0x0. Impl exposes `upgradeToAndCall`/`proxiableUUID`/`Upgraded`. | `AuthorityManager` (`restricted` ⇒ AccessManager role), **not** an EIP-1967 admin. |
| **TokenRegisterV3** (`0xe00314b0…`, MAPO) | UUPS | impl slot populated; admin slot 0x0. | AuthorityManager. |
| **VaultTokenV3** (MAPO, per-asset) | deterministic deploy (ERC-20 vault) | full bytecode. | relay bridge / authority. |
| **FeeService** (`0xfeE31a…`) | **NOT a proxy** | 3.2 KB full contract; impl slot returns `0x0` (confirmed live on ETH). | AuthorityManager (logic-level). |
| **AuthorityManager** (`0xACC31A67…`) | **NOT a proxy** | 9.9 KB full contract; impl slot `0x0`. | self (AccessManager admin role). |

Live impls per chain are in §4. **Read the EIP-1967 slot live — never hard-code an impl**; watch `Upgraded(address)` topic0 `0xbc7cd75a…` on `0x0000317Bec…`.

## 8. Detection invariants & gotchas

1. **`MessageOut` (source) and `MessageIn` (destination) are the bridge's two halves**, joined by `orderId` (bytes32, indexed topic1). A complete transfer = `MessageOut` on chain A → `MessageRelay` on MAPO → `MessageIn` on chain B. Index all three by `orderId`.
2. **`chainAndGasLimit` (indexed topic2 on MessageOut/In/Relay) is a packed uint256**, not a chain id: `fromChain<<192 | toChain<<128 | reserved<<64 | gasLimit`. Decode before using.
3. **The bridge address is the SAME literal `0x0000317Bec…` on all 7 targets + MAPO** but a different deployment each — key on `(chainId, address)`. Its leading zeros are a reliable scan tell.
4. **Per-chain implementation behind one proxy address.** Don't assume the impl is constant; spokes run `Bridge`, MAPO runs `BridgeAndRelay`. Reading code at the proxy is fine; reading the *impl* requires the EIP-1967 slot per chain.
5. **The real user is `initiator`/`from`, not `msg.sender`.** `swapOutToken` is called by a Router; `messageIn` is called by a relayer/keeper. Attribute by the event fields (`MessageIn.to`, `MessageIn.from`, `MessageTransfer.initiator`), never `tx.from`.
6. **`MessageIn.result` (bool) + `reason` (bytes)** tell you whether the destination execution succeeded. A `MessageIn` with `result=false` is a *failed* delivery (funds may be parked in the Receiver's failed-store) — treat as an alert, not a success.
7. **Vault accounting + fee split happen only on MAPO** (`CollectFee`, `DepositIn`, `DepositVault`/`WithdrawVault`). If you index only the seven targets you will **never see the fee/vault events** — they fire on chain 22776.
8. **`UpdateVault` (`0x305b6563…`, VaultTokenV3) and `SetDistributeRate` (`0x28d0e3b7…`, BridgeAndRelay) have DISTINCT topic0s** — they do **not** collide. Both are relay-only admin/accounting events; key each to its own emitter.
9. **`getNativeFee` is the fee oracle** — a transfer that underpays reverts in the router before `swapOutToken`. The fee token can be the native gas token or an ERC-20; read the `(uint256, address)` return.
10. **MOS V3 fully supersedes MOS V2.** The V2 bridge `0xfeB2b97e…` still has code on most chains but ~0 recent activity (see mos-v2.md). All current `MessageOut`/`MessageIn` traffic is on `0x0000317Bec…`.
11. **Avalanche carries the full MOS V3** (bridge + authority + feeService) despite a *partial router* footprint there — do not infer "Butter absent on Avax" from the router layer.
12. **`Withdraw` event misspells `receiver` as `reicerver`** in the source — cosmetic; the topic0 `0xf341246a…` is computed from the types, unaffected.

## 9. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics (chain-agnostic) =====
TOPIC_MESSAGE_OUT          = '\x469059a9fd182ad3741bdd67b925e15056d35262609ea83393db7e8fb5a05ab1'
TOPIC_MESSAGE_IN           = '\x13d3a5b2d6aaada5c31b5654f99c2ab9587cf9a53ee4b2e25b6c68a8dfaa4472'
TOPIC_MESSAGE_RELAY        = '\xf01fbdd2fdbc5c2f201d087d588789d600e38fe56427e813d9dced2cdb25bcac'
TOPIC_MESSAGE_TRANSFER     = '\x48f234c2c5fdc7ed34779457fd485590e07604056ed028aa16e7b8a137478b26'
TOPIC_GAS_INFO             = '\x058db03136cae65e3a953afcf3307ee1e68c448c334786bdccc2a382ca72c97d'
TOPIC_COLLECT_FEE_RELAY    = '\x03a171b17616c5776c3570767fa662ecee7e8c6d5ecd488b3bb9a319311f7a1e'
TOPIC_DEPOSIT_IN           = '\x1715d70ef1746a264496faed0d62deacc731a251670681188dbceac9ad870e31'
TOPIC_WITHDRAW_RELAY       = '\xf341246adaac6f497bc2a656f546ab9e182111d630394f0c57c710a59a2cb567'
TOPIC_REGISTER_CHAIN       = '\x6f94bb991e9abc3f3f557a46ef5c9959644fe3fb9927adea628e254f5258126a'
TOPIC_SET_DISTRIBUTE_RATE  = '\x28d0e3b789c60bc4629db5d1be2252c5a8318f306119aa5f7abffd092383e083'
TOPIC_UPDATE_VAULT         = '\x305b6563ce4afe6a5531c0feaac753c35459d1a05d26dcb572790eb9a3469836'  -- VaultTokenV3 (distinct from SetDistributeRate)
TOPIC_DEPOSIT_VAULT        = '\xd12854a02fa0a0a18ec43fb173bee96f8dc9a80f8633af72baa374833949f329'
TOPIC_WITHDRAW_VAULT       = '\xc3f7cb75c4b290a1a7f47394c576e48664f75b813851c4f2d196f914485f710b'
TOPIC_SET_RELAY            = '\x14c31aacfac9e1b12448ca6d440a799c047f0eb36ac5145aa2f18dd4796373f5'
TOPIC_SET_FEE_RECEIVER     = '\xffb40bfdfd246e95f543d08d9713c339f1d90fa9265e39b4f562f9011d7c919f'
TOPIC_UPGRADED             = '\xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
TOPIC_INITIALIZED          = '\xc7f505b2f371ae2175ee4913f4499e1f2633a7b5936321eed1cdaeb6115181d2'
TOPIC_AUTHORITY_UPDATED    = '\x2f658b440c35314f52658ea8a740e05b284cdc84dc9ae01e891f21b8933e7cad'

-- ===== Selectors =====
SEL_SWAP_OUT_TOKEN         = '\xb899f904'
SEL_SWAP_OUT_TOKEN_ORDERID = '\x9ce638ec'
SEL_DEPOSIT_TOKEN          = '\xfb0f97a8'
SEL_MESSAGE_IN             = '\xe282dcdd'
SEL_WITHDRAW_RELAY         = '\xf3fef3a3'
SEL_WITHDRAW_FEE           = '\xc879c6d8'
SEL_TRIGGER_PAUSE          = '\x7fec8d38'
SEL_GET_NATIVE_FEE         = '\xeef5add1'
SEL_AUTHORITY              = '\xbf7e214f'
SEL_PAUSED                 = '\x5c975abb'
SEL_UPGRADE_TO_AND_CALL    = '\x4f1ef286'
SEL_PROXIABLE_UUID         = '\x52d1902d'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT          = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT         = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses (IDENTICAL literal on all 7 targets + MAPO; key on (chainId,addr)) =====
BUTTER_MOSV3_BRIDGE        = '\x0000317bec33af037b5fab2028f52d14658f6a56'   -- vanity leading-zero
BUTTER_MOSV3_AUTHORITY     = '\xacc31a6756b60304c03d6626fc98c062e4539cca'
BUTTER_MOSV3_FEESERVICE    = '\xfee31a1fd7fca0e05428ff751242e46f6d5769a6'

-- ===== Per-chain Bridge implementations (live 2026-06-09) =====
ETH_MOSV3_BRIDGE_IMPL      = '\x12bfb3b58ad02a0df40ee7186d26266c52d0109c'
BASE_MOSV3_BRIDGE_IMPL     = '\x862761d6d52e9e812a8c22e6e6a39e186e59a33d'
BSC_MOSV3_BRIDGE_IMPL      = '\x62844d1e812cf17f20eaa8d49e33f5f6ba6f3e77'
AVAX_MOSV3_BRIDGE_IMPL     = '\xf1d15f0e7a7d56168010cd454bd4541603bbeed4'
ARB_MOSV3_BRIDGE_IMPL      = '\xc45c34ebdb808b5383b71ea85e8378af994d7082'
OP_MOSV3_BRIDGE_IMPL       = '\x7912e89440e57352302d30730849268eb863ece4'
POLY_MOSV3_BRIDGE_IMPL     = '\x774444afb39a9555e9a70e60d7eb20b73f822716'

-- ===== MAP relay (MAPO, chain 22776) — NOT a target chain, anchor only =====
MAPO_TOKEN_REGISTER_V3     = '\xe00314b05919156e7b16f4e89c78d2174e20e366'
MAPO_DEPOSIT_WHITELIST     = '\x27172da6b48db586b5261ff90d6d1d5f2c1c1363'
MAPO_PROTOCOL_FEE          = '\xc9041777d421b5fcb272f7cd8c66757246f1f9f1'
```

## 10. Verification & sources

How every constant was verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` / `[0:4]` from the verified source in `butternetwork/butter-mos-contracts/evmv3/contracts/` (`Bridge.sol`, `BridgeAndRelay.sol`, `abstract/BridgeAbstract.sol`, `FeeService.sol`, `VaultTokenV3.sol`, `interface/IButterBridgeV3.sol`). `MessageOut` (`0x469059a9…`) and `MessageIn` (`0x13d3a5b2…`) cross-checked against **live `eth_getLogs`** on the Ethereum bridge `0x0000317Bec…` (1909 `MessageOut` + 306 `MessageIn` in a 49k-block window ending block 25,279,374; first tx `0x6477b1e1…`) and on the Base bridge (16 `MessageOut` in a 9k-block window).
- **Addresses:** parsed from `evmv3/deployments/deploy.json` and existence-checked via `eth_getCode` (non-empty) on all seven target RPCs + MAPO. Bridge/authority/feeService confirmed present on every target; the bridge proxy is 133 B everywhere.
- **Proxy classification:** EIP-1967 impl slot read live via `eth_getStorageAt` on `0x0000317Bec…` for all seven chains (per-chain impl recorded in §4) — impl slot populated, admin slot `0x0`, beacon slot `0x0` ⇒ UUPS. FeeService + AuthorityManager impl slots read `0x0` ⇒ not proxies.
- **Function reachability:** `getNativeFee` (sel `0xeef5add1`) `eth_call`-probed on the ETH FeeService — selector accepted (logic revert, not dispatch miss). `authority()` on the bridge returned `0xacc31a67…`, matching the registry AuthorityManager.

**Authoritative sources:**
- Bridge repo: <https://github.com/butternetwork/butter-mos-contracts> (`evmv3/`)
- Docs: <https://docs.butternetwork.io> · MAP Protocol: <https://docs.mapprotocol.io>
- Explorers: Etherscan / Basescan / BscScan / Snowscan / Arbiscan / Optimistic Etherscan / Polygonscan; MAP relay <https://maposcan.io>
