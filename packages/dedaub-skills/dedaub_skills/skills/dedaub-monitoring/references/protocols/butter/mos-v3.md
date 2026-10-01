# Butter Network — MAP Omnichain Service V3 (MOS V3) — Topics, Selectors, Addresses (Ethereum, Base, BNB, Avalanche, Arbitrum, Optimism, Polygon, Robinhood Chain + MAP relay)

**Status:** verified against live RPC on Ethereum (1), Base (8453), BNB (56), Avalanche (43114), Arbitrum One (42161), Optimism (10), Polygon PoS (137), the MAP relay chain (MAPO, 22776), and the canonical `butternetwork/butter-mos-contracts` (`evmv3/`) repo on 2026-06-09. Extended on 2026-09-29: Robinhood Chain (4663), the current bridge implementations on all eight chains, and the deprecated **OmniService v3.0** `0x000030fB6c4701389B05F124F6fFd4C862CF1eF9` (canonical `butternetwork/omniservice-contracts` repo).
**Scope:** the **current** MAP Omnichain Service bridge (v3.1) — `Bridge` on spoke chains, `BridgeAndRelay` on the MAP relay, plus `FeeService`, `AuthorityManager`, and the relay-only `TokenRegisterV3` / `VaultTokenV3` — and its deprecated message-only predecessor, OmniService v3.0 (§1.7, §2.5). Topics + selectors are **chain-agnostic**; addresses are network-specific (and largely **identical across chains** by deterministic deploy — always key on `(chainId, address)`). The legacy MOS V2 bridge is documented separately in [mos-v2.md](mos-v2.md); the user-facing router layer in [router.md](router.md).

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
| **Bridge** (`Bridge.sol`) | Spoke-chain MOS endpoint. `swapOutToken` (lock/burn out), `messageIn` (verify+release). Emits `MessageOut`/`MessageIn`. | every spoke (all 8 targets, Robinhood Chain included) | UUPS proxy `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` |
| **OmniService v3.0** (`OmniService.sol`, `butternetwork/omniservice-contracts`) | **Deprecated** message-only predecessor ("v3.0 (deprecated)" in the official list). `messageOut`/`transferOut` (source), `transferInWithIndex` (destination). Emits its own `MessageOut`/`MessageIn` shapes (§1.7). | Ethereum, BNB, Polygon of the 8 targets (the repo's `evm/deployments/deployments.json` also lists MAPO, Merlin and a zkSync literal) | UUPS proxy `0x000030fB6c4701389B05F124F6fFd4C862CF1eF9` |
| **BridgeAndRelay** (`BridgeAndRelay.sol`) | MAP-relay MOS endpoint. Adds vault settlement, fee split (`CollectFee`), chain registry, `relayExecute`, `messageIn`+`MessageRelay`. | MAP relay (22776) only | UUPS proxy `0x0000317Bec…` (same addr, different impl) |
| **FeeService** (`FeeService.sol`) | Per-destination-chain message/gas fee quoting (`getNativeFee`). | all chains | non-proxy (3.2 KB) |
| **AuthorityManager** (`AuthorityManager.sol`) | OZ AccessManager — role/permission registry; `restricted` modifier auth for every admin call. | all chains | non-proxy (9.9 KB) |
| **TokenRegisterV3** (`TokenRegisterV3.sol`) | Relay-side token↔vault mapping, cross-chain token map, fee config. | MAP relay only | UUPS proxy `0xe00314b0…` |
| **VaultTokenV3** (`VaultTokenV3.sol`) | ERC-20 vault share per bridged asset (usdt/usdc/eth/btc/…); accrues `DepositVault`/`WithdrawVault`. | MAP relay only | per-token (deterministic) |
| **DepositWhitelist** / **ProtocolFee** (periphery) | Relay-side deposit gating + protocol-fee accounting. | MAP relay only | non-proxy |

> **Avalanche note:** MOS V3 is **fully deployed** on Avalanche (bridge + authority + feeService all present), even though the *router* layer is only partially deployed there (see router.md).
>
> **Robinhood Chain note:** MOS V3 is **fully deployed** on Robinhood Chain (4663) at the same three literals (§4.1), and the official v3.1 list names it. The Robinhood bridge carried 9 `MessageOut` and 22 `MessageIn` in the pinned 12-hour window 2026-09-28 00:00–12:00 UTC.

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

### 1.7 OmniService v3.0 (deprecated, message only) — emitter = `0x000030fB6c4701389B05F124F6fFd4C862CF1eF9`

Source: `butternetwork/omniservice-contracts` `evm/contracts/interface/IMOSV3.sol`, `abstract/OmniServiceCore.sol`, `OmniService.sol`. All four topic0s were found as `PUSH32` constants in the live implementation bytecode on Ethereum and Polygon. The v3.0 events carry `fromChain`/`toChain` as indexed topics and the `orderId` in `data`, so their topic0s differ from the v3.1 `MessageOut`/`MessageIn` in §1.1.

| topic0 | Event |
|--------|-------|
| `0x66e2de40f0c0fe334b556647c99aae36be85f9975cda26f72954d14f728e7dc9` | `MessageOut(uint256 indexed fromChain, uint256 indexed toChain, bytes32 orderId, bytes fromAddrss, bytes messageData)` — **source leg** of a v3.0 message (`fromAddrss` is the on-chain spelling). |
| `0x5743fd96027a287fc1a99d67aa4269d509968bb2a86993992534af28d650f551` | `MessageIn(uint256 indexed fromChain, uint256 indexed toChain, bytes32 orderId, bytes fromAddrss, bytes messageData, bool result, bytes reason)` — **destination leg**; `result`/`reason` = execution outcome. |
| `0xdde41a7caa33988cd388dbc41c7fa34c8abdb5497d5695780a56308280ab0075` | `MessageVerified(uint256 indexed fromChain, uint256 indexed toChain, bytes32 orderId, bytes fromAddrss, bytes messageData)` — status only: proof verified and stored, execution left for later. |
| `0x48f234c2c5fdc7ed34779457fd485590e07604056ed028aa16e7b8a137478b26` | `MessageTransfer(address indexed initiator, address indexed referrer, address indexed sender, bytes32 orderId, bytes32 transferId, address feeToken, uint256 fee)` — **same topic0 as the v3.1 `MessageTransfer` (§1.1)**, but v3.0 indexes the three addresses (4 topics) while v3.1 indexes none (1 topic). Decode by emitter. |

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

### 2.5 OmniService v3.0 (deprecated)

Checked as `PUSH4` constants in the live v3.0 implementation bytecode on Ethereum. The deployed build predates the repository head: it has no `messageIn(uint256,uint256,bytes32,bytes)` and no `GasInfo` event.

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x901a66f6` | `messageOut(bytes32 _transferId, address _initiator, address _referrer, uint256 _toChain, bytes _messageData, address _feeToken)` → `bytes32` | `payable`; source entrypoint. Emits `MessageTransfer` + `MessageOut`. |
| `0xa39ed3f9` | `transferOut(uint256 _toChain, bytes _messageData, address _feeToken)` → `bytes32` | `payable`; older source entrypoint. Emits `MessageTransfer` + `MessageOut`. |
| `0x492092b1` | `transferInWithIndex(uint256 _chainId, uint256 _logIndex, bytes _receiptProof)` | destination: verify the relay-chain proof and execute. Emits `MessageIn`. |
| `0x0b281351` | `transferInVerify(uint256 _chainId, uint256 _logIndex, bytes _receiptProof)` | destination: verify and store only. Emits `MessageVerified`. |
| `0x58f8106f` | `transferInVerified(bytes32 _orderId, uint256 _fromChain, bytes _fromAddress, bytes _messageData)` | destination: execute a stored message. Emits `MessageIn`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. **The bridge, authority, and feeService addresses below are identical on every one of the seven target chains** (deterministic deploy) — only the bridge *implementation* differs (§Proxies). Chains 4–10 therefore show only divergences.

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (`Bridge`, UUPS proxy, 133 B) | `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` | Spoke MOS endpoint. Live impl `0x12bfb3b58ad02a0df40ee7186d26266c52d0109c`. Emits §1.1 events. |
| **AuthorityManager** (`AuthorityManager`, 9.9 KB) | `0xACC31A6756B60304C03d6626fc98c062E4539CCA` | OZ AccessManager — admin/role registry; not a proxy. `authority()` of every MOS contract resolves here. |
| **FeeService** (`FeeService`, 3.2 KB) | `0xfeE31a1FD7FcA0E05428ff751242e46F6D5769a6` | Per-chain fee/gas quoting; not a proxy. |
| OmniService v3.0 (deprecated; UUPS proxy, 177 B) | `0x000030fB6c4701389B05F124F6fFd4C862CF1eF9` | Message-only predecessor. Impl `0xae5369a8bcf205aefb315cea35c9f7fd8d512bf3` (20664 B); admin slot `0x0`. Last events near block 21,068,593 (Blockscout log list); 0 events in the pinned window. |

**Not deployed on Ethereum:** `BridgeAndRelay`, `TokenRegisterV3`, `VaultTokenV3`, `DepositWhitelist`, `ProtocolFee` — these are **MAP-relay-only** (§7). The Ethereum bridge runs the spoke `Bridge` impl, not `BridgeAndRelay`.

## 4. Addresses — Base (8453), BNB (56), Avalanche (43114), Arbitrum (42161), Optimism (10), Polygon (137), Robinhood Chain (4663)

Verified via `eth_getCode` on each chain's publicnode RPC (Robinhood Chain: `https://rpc.mainnet.chain.robinhood.com`; all eight chains re-checked on 2026-09-29). **Bridge, AuthorityManager, FeeService share the exact Ethereum literals on all seven** — shown once:

| Role | Address (identical on all 8 targets) |
|------|--------------------------------------|
| Bridge (proxy) | `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` |
| AuthorityManager | `0xACC31A6756B60304C03d6626fc98c062E4539CCA` |
| FeeService | `0xfeE31a1FD7FcA0E05428ff751242e46F6D5769a6` |

Per-chain **divergence is only the bridge implementation** (read live from the EIP-1967 slot on 2026-09-29):

| Chain | ID | Bridge impl (live `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` → EIP-1967 impl) | Impl size | FeeService size |
|---|---|---|---|---|
| Ethereum | 1 | `0x12bfb3b58ad02a0df40ee7186d26266c52d0109c` | 16436 B | 3217 B |
| Base | 8453 | `0x862761d6d52e9e812a8c22e6e6a39e186e59a33d` | 16436 B | 3217 B |
| BNB | 56 | `0x62844d1e812cf17f20eaa8d49e33f5f6ba6f3e77` | 16436 B | 3197 B |
| Avalanche | 43114 | `0xf1d15f0e7a7d56168010cd454bd4541603bbeed4` | 16491 B | 3217 B |
| Arbitrum | 42161 | `0xc45c34ebdb808b5383b71ea85e8378af994d7082` | 16436 B | 3217 B |
| Optimism | 10 | `0xa11293e174f33ef794f03d70daf5cc7b2c2e96b9` (was `0x7912e89440e57352302d30730849268eb863ece4` on 2026-06-09) | 16436 B | 3217 B |
| Polygon | 137 | `0x774444afb39a9555e9a70e60d7eb20b73f822716` | 16436 B | 3197 B |
| Robinhood Chain | 4663 | `0xf1d15f0e7a7d56168010cd454bd4541603bbeed4` (same literal as Avalanche, different bytecode) | 16436 B | 3217 B |

All seven run the spoke `Bridge` impl (not `BridgeAndRelay`). **No relay-only contracts** (`BridgeAndRelay`, `TokenRegisterV3`, `VaultTokenV3`) on any of the eight targets — those live exclusively on MAPO.

### 4.1 Robinhood Chain (chain ID 4663)

Listed in the official "Deployed Contracts" v3.1 table of the Butter Omnichain Service (`Robinhood`, 4663, `0x0000317Bec33Af037b5fAb2028f52d14658F6A56`). Not listed in `evmv3/deployments/deploy.json` (repository head of 2026-05-21) or on the bridge-integration "Deployed Contracts" page. Verified with `eth_getCode` on 2026-09-29.

| Role | Address | One-liner |
|------|---------|-----------|
| **Bridge** (UUPS proxy, 133 B, same code hash as every other chain) | `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` | Spoke MOS endpoint. Impl `0xf1d15f0e7a7d56168010cd454bd4541603bbeed4` (16436 B; its bytecode carries `MessageOut`, `MessageIn`, `Upgraded`, `swapOutToken`, `messageIn`, `upgradeToAndCall`); admin slot `0x0`; `authority()` = `0xACC31A6756B60304C03d6626fc98c062E4539CCA`. 9 `MessageOut` / 22 `MessageIn` in the pinned window. |
| **AuthorityManager** (9905 B, same code hash) | `0xACC31A6756B60304C03d6626fc98c062E4539CCA` | OZ AccessManager. |
| **FeeService** (3217 B, same code hash as Ethereum) | `0xfeE31a1FD7FcA0E05428ff751242e46F6D5769a6` | Fee quoting. |

**Not deployed on Robinhood Chain:** OmniService v3.0 `0x000030fB6c4701389B05F124F6fFd4C862CF1eF9` and the MOS V2 contracts (`eth_getCode` = `0x`, nonce 0). The router layer on Robinhood Chain is in [router.md](router.md) §4.1. MOS identifies Robinhood Chain by its EVM chain id 4663 inside `chainAndGasLimit` (a sampled `MessageOut` packs `fromChain` 4663, `toChain` 56).

### 4.2 OmniService v3.0 (deprecated) — per-chain presence

| Chain | `0x000030fB6c4701389B05F124F6fFd4C862CF1eF9` | Impl (EIP-1967) |
|---|---|---|
| Ethereum | ✓ 177 B proxy | `0xae5369a8bcf205aefb315cea35c9f7fd8d512bf3` (20664 B) |
| BNB | ✓ 177 B proxy | `0xae5369a8bcf205aefb315cea35c9f7fd8d512bf3` (20664 B, different code hash from Ethereum) |
| Polygon | ✓ 177 B proxy | `0x163139e57245c4327ea97cc309355d4e91eff740` (20664 B) |
| Base, Arbitrum, Optimism, Avalanche, Robinhood Chain | ✗ `eth_getCode` = `0x`, nonce 0 | — |

The official omnichain "Deployed Contracts" page lists v3.0 on Base, Optimism and Arbitrum too, but no code exists at that literal on those three chains; the repo's `deployments.json` lists this literal for Ethereum, BNB, Polygon, Merlin and MAPO (and a different literal for zkSync), which matches the chain state on the eight targets.

## 5. Cross-chain summary

| Chain | ID | Bridge `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` | AuthorityManager | FeeService | OmniService v3.0 `0x000030fB6c4701389B05F124F6fFd4C862CF1eF9` | Relay contracts |
|---|---|---|---|---|---|---|
| Ethereum | 1 | ✓ (spoke `Bridge`) | ✓ | ✓ | ✓ (deprecated) | — |
| Base | 8453 | ✓ | ✓ | ✓ | ✗ (listed in docs, no code) | — |
| BNB | 56 | ✓ | ✓ | ✓ | ✓ (deprecated) | — |
| Avalanche | 43114 | ✓ | ✓ | ✓ | ✗ | — |
| Arbitrum | 42161 | ✓ | ✓ | ✓ | ✗ (listed in docs, no code) | — |
| Optimism | 10 | ✓ | ✓ | ✓ | ✗ (listed in docs, no code) | — |
| Polygon | 137 | ✓ | ✓ | ✓ | ✓ (deprecated) | — |
| **Robinhood Chain** | **4663** | ✓ (spoke `Bridge`, impl `0xf1d15f0e7a7d56168010cd454bd4541603bbeed4`) | ✓ | ✓ | ✗ | — |
| **MAP relay (MAPO)** | **22776** | ✓ (`BridgeAndRelay`) | ✓ | ✓ | listed (not checked) | TokenRegisterV3, VaultTokenV3 (×many), DepositWhitelist, ProtocolFee |

**Vanity-address tell:** the bridge `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` has six leading hex zeros — distinctive in any tx/log scan. Same literal everywhere ⇒ **always key on `(chainId, address)`**.

**Counterparty chains outside the eight** that the bridge also services (from the repo `deploy.json` + on-chain `RegisterChain`): MAP relay (22776), zkSync Era (324), Linea, Scroll, Mantle, Blast (81457), Merlin, AINN, Conflux, Kaia/Klaytn, X Layer, Unichain, **Tron** (non-EVM address form), **NEAR** (separate Rust `map-ominichain-service`), and BTC/SOL/TON/XRP/DOGE handled as relay vault tokens.

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
| **OmniService v3.0** (`0x000030fB6c4701389B05F124F6fFd4C862CF1eF9`, deprecated) | **UUPS** | 177-byte `ERC1967Proxy`; impl slot populated (Ethereum and BNB `0xae5369a8bcf205aefb315cea35c9f7fd8d512bf3`, Polygon `0x163139e57245c4327ea97cc309355d4e91eff740`); admin slot `0x0` (read on Ethereum); impl bytecode carries `upgradeToAndCall` and `Upgraded`. | `AccessControl` roles (`MANAGER_ROLE` in source); role holders not read. |

Live impls per chain are in §4. **Read the EIP-1967 slot live — never hard-code an impl**; watch `Upgraded(address)` topic0 `0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b` on `0x0000317Bec33Af037b5fAb2028f52d14658F6A56`.

**Implementation history seen by the two checks:** Optimism moved from `0x7912e89440e57352302d30730849268eb863ece4` (2026-06-09) to `0xa11293e174f33ef794f03d70daf5cc7b2c2e96b9` (2026-09-29); the other six original chains kept the same impl address. Avalanche and Robinhood Chain use the same impl literal `0xf1d15f0e7a7d56168010cd454bd4541603bbeed4` with different bytecode (16491 B vs 16436 B), so key an impl on `(chainId, address)` too.

## 8. Detection invariants & gotchas

1. **`MessageOut` (source) and `MessageIn` (destination) are the bridge's two halves**, joined by `orderId` (bytes32, indexed topic1). A complete transfer = `MessageOut` on chain A → `MessageRelay` on MAPO → `MessageIn` on chain B. Index all three by `orderId`.
2. **`chainAndGasLimit` (indexed topic2 on MessageOut/In/Relay) is a packed uint256**, not a chain id: `fromChain<<192 | toChain<<128 | reserved<<64 | gasLimit`. Decode before using.
3. **The bridge address is the SAME literal `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` on all 8 targets + MAPO** but a different deployment each — key on `(chainId, address)`. Its leading zeros are a reliable scan tell.
4. **Per-chain implementation behind one proxy address.** Don't assume the impl is constant; spokes run `Bridge`, MAPO runs `BridgeAndRelay`. Reading code at the proxy is fine; reading the *impl* requires the EIP-1967 slot per chain.
5. **The real user is `initiator`/`from`, not `msg.sender`.** `swapOutToken` is called by a Router; `messageIn` is called by a relayer/keeper. Attribute by the event fields (`MessageIn.to`, `MessageIn.from`, `MessageTransfer.initiator`), never `tx.from`.
6. **`MessageIn.result` (bool) + `reason` (bytes)** tell you whether the destination execution succeeded. A `MessageIn` with `result=false` is a *failed* delivery (funds may be parked in the Receiver's failed-store) — treat as an alert, not a success.
7. **Vault accounting + fee split happen only on MAPO** (`CollectFee`, `DepositIn`, `DepositVault`/`WithdrawVault`). If you index only the seven targets you will **never see the fee/vault events** — they fire on chain 22776.
8. **`UpdateVault` (`0x305b6563…`, VaultTokenV3) and `SetDistributeRate` (`0x28d0e3b7…`, BridgeAndRelay) have DISTINCT topic0s** — they do **not** collide. Both are relay-only admin/accounting events; key each to its own emitter.
9. **`getNativeFee` is the fee oracle** — a transfer that underpays reverts in the router before `swapOutToken`. The fee token can be the native gas token or an ERC-20; read the `(uint256, address)` return.
10. **MOS V3 fully supersedes MOS V2.** The V2 bridge `0xfeB2b97e…` still has code on most chains but ~0 recent activity (see mos-v2.md). All current `MessageOut`/`MessageIn` traffic is on `0x0000317Bec…`.
11. **Avalanche carries the full MOS V3** (bridge + authority + feeService) despite a *partial router* footprint there — do not infer "Butter absent on Avax" from the router layer.
12. **`Withdraw` event misspells `receiver` as `reicerver`** in the source — cosmetic; the topic0 `0xf341246a…` is computed from the types, unaffected.
13. **Value movement on the spokes is lock and release.** In the source tx the bridged token moves from the router to `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` (e.g. USDT in Ethereum tx `0x7beb518ebcd3b87e6ac6a0f74f862dbc908e98e7f05fb30ef713e229af168b9c`), next to `MessageOut`. In the destination tx the bridge sends the token to `MessageIn.to` (a user, or the router-layer receiver that then swaps). `MessageIn.token` = `0x0000000000000000000000000000000000000000` means a native payout, which leaves no `Transfer` log: on Robinhood Chain the bridge burns WETH `0x0bd7d308f8e1639fab988df18a8011f41eacad73` (a `Transfer` to `0x0`) and sends ETH.
14. **Robinhood Chain carries the full MOS V3** (bridge + authority + feeService) with the same event set; MOS uses the EVM chain id 4663 in `chainAndGasLimit`. The Robinhood bridge impl literal equals the Avalanche one, but the bytecode differs.
15. **Two generations share names but not topics.** OmniService v3.0 `MessageOut`/`MessageIn` (`0x66e2de40f0c0fe334b556647c99aae36be85f9975cda26f72954d14f728e7dc9` / `0x5743fd96027a287fc1a99d67aa4269d509968bb2a86993992534af28d650f551`) index `fromChain`/`toChain` and put `orderId` in `data`; the v3.1 bridge events (`0x469059a9fd182ad3741bdd67b925e15056d35262609ea83393db7e8fb5a05ab1` / `0x13d3a5b2d6aaada5c31b5654f99c2ab9587cf9a53ee4b2e25b6c68a8dfaa4472`) index `orderId`. `MessageTransfer` has one topic0 for both, with 4 topics on v3.0 and 1 topic on v3.1. The v3.0 service emitted 0 logs on all eight chains in the pinned window.
16. **`messageIn` is sent by a relayer, not by the user.** The sampled `messageIn` transactions on Ethereum, Base and Robinhood Chain all came from EOA `0xdb61db256a30f3ef46110b8e2520aaec0db08153`. Attribute the payout to `MessageIn.to`.

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
-- OmniService v3.0 (deprecated; message only)
TOPIC_V30_MESSAGE_OUT      = '\x66e2de40f0c0fe334b556647c99aae36be85f9975cda26f72954d14f728e7dc9'
TOPIC_V30_MESSAGE_IN       = '\x5743fd96027a287fc1a99d67aa4269d509968bb2a86993992534af28d650f551'
TOPIC_V30_MESSAGE_VERIFIED = '\xdde41a7caa33988cd388dbc41c7fa34c8abdb5497d5695780a56308280ab0075'
-- (v3.0 MessageTransfer = TOPIC_MESSAGE_TRANSFER, but with 3 indexed addresses)

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
-- OmniService v3.0
SEL_V30_MESSAGE_OUT        = '\x901a66f6'
SEL_V30_TRANSFER_OUT       = '\xa39ed3f9'
SEL_V30_TRANSFER_IN_INDEX  = '\x492092b1'
SEL_V30_TRANSFER_IN_VERIFY = '\x0b281351'
SEL_V30_TRANSFER_IN_VERIFIED = '\x58f8106f'

-- ===== Proxy slots =====
EIP1967_IMPL_SLOT          = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT         = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Addresses (IDENTICAL literal on all 8 targets + MAPO; key on (chainId,addr)) =====
BUTTER_MOSV3_BRIDGE        = '\x0000317bec33af037b5fab2028f52d14658f6a56'   -- vanity leading-zero
BUTTER_MOSV3_AUTHORITY     = '\xacc31a6756b60304c03d6626fc98c062e4539cca'
BUTTER_MOSV3_FEESERVICE    = '\xfee31a1fd7fca0e05428ff751242e46f6d5769a6'
BUTTER_OMNISERVICE_V30     = '\x000030fb6c4701389b05f124f6ffd4c862cf1ef9'   -- deprecated; code on ETH, BNB, Polygon only
BUTTER_MOS_RELAYER_EOA     = '\xdb61db256a30f3ef46110b8e2520aaec0db08153'   -- messageIn sender seen on ETH, Base, Robinhood

-- ===== Robinhood Chain (chain ID 4663) =====
RH_MOSV3_BRIDGE            = '\x0000317bec33af037b5fab2028f52d14658f6a56'
RH_MOSV3_AUTHORITY         = '\xacc31a6756b60304c03d6626fc98c062e4539cca'
RH_MOSV3_FEESERVICE        = '\xfee31a1fd7fca0e05428ff751242e46f6d5769a6'

-- ===== Per-chain Bridge implementations (live 2026-06-09; re-read 2026-09-29) =====
ETH_MOSV3_BRIDGE_IMPL      = '\x12bfb3b58ad02a0df40ee7186d26266c52d0109c'
BASE_MOSV3_BRIDGE_IMPL     = '\x862761d6d52e9e812a8c22e6e6a39e186e59a33d'
BSC_MOSV3_BRIDGE_IMPL      = '\x62844d1e812cf17f20eaa8d49e33f5f6ba6f3e77'
AVAX_MOSV3_BRIDGE_IMPL     = '\xf1d15f0e7a7d56168010cd454bd4541603bbeed4'
ARB_MOSV3_BRIDGE_IMPL      = '\xc45c34ebdb808b5383b71ea85e8378af994d7082'
OP_MOSV3_BRIDGE_IMPL       = '\xa11293e174f33ef794f03d70daf5cc7b2c2e96b9'   -- current (2026-09-29)
OP_MOSV3_BRIDGE_IMPL_PREV  = '\x7912e89440e57352302d30730849268eb863ece4'   -- impl on 2026-06-09
POLY_MOSV3_BRIDGE_IMPL     = '\x774444afb39a9555e9a70e60d7eb20b73f822716'
RH_MOSV3_BRIDGE_IMPL       = '\xf1d15f0e7a7d56168010cd454bd4541603bbeed4'   -- same literal as Avalanche, different bytecode

-- ===== OmniService v3.0 implementations (deprecated) =====
ETH_OMNISERVICE_V30_IMPL   = '\xae5369a8bcf205aefb315cea35c9f7fd8d512bf3'
BNB_OMNISERVICE_V30_IMPL   = '\xae5369a8bcf205aefb315cea35c9f7fd8d512bf3'
POLY_OMNISERVICE_V30_IMPL  = '\x163139e57245c4327ea97cc309355d4e91eff740'

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

Extension of 2026-09-29:

- **Robinhood Chain:** the bridge, AuthorityManager and FeeService literals existence-checked with `eth_getCode` (same proxy code hash, same AuthorityManager code hash, same FeeService code hash as Ethereum); the EIP-1967 impl and admin slots and `authority()` read live; the impl bytecode scanned for the `MessageOut`/`MessageIn`/`Upgraded` topic0s and the `swapOutToken`/`messageIn`/`upgradeToAndCall` selectors. The official v3.1 table of the omnichain "Deployed Contracts" page lists Robinhood (4663) at `0x0000317Bec33Af037b5fAb2028f52d14658F6A56`.
- **Implementations:** the EIP-1967 slot re-read on all eight chains; only Optimism changed since 2026-06-09 (§7).
- **OmniService v3.0:** signatures from `butternetwork/omniservice-contracts` (`evm/contracts/interface/IMOSV3.sol`, `evm/contracts/abstract/OmniServiceCore.sol`, `evm/contracts/OmniService.sol`), hashed as `keccak256(sig)` and found as constants in the live implementation bytecode on Ethereum and Polygon; the Blockscout log list of the Ethereum proxy decodes `MessageOut`, `MessageIn` and `MessageTransfer` with the same field names. Presence checked with `eth_getCode` on all eight chains (§4.2).
- **Activity** (`eth_getLogs`, pinned 12-hour window 2026-09-28 00:00–12:00 UTC, emitter `0x0000317Bec33Af037b5fAb2028f52d14658F6A56` on every chain): `MessageOut` — Ethereum 48, Base 26, Arbitrum 23, Optimism 0, Polygon 77, BNB 153, Avalanche 0, Robinhood 9. `MessageIn` — Ethereum 21, Base 8, Arbitrum 12, Optimism 0, Polygon 57, BNB 211, Avalanche 0, Robinhood 22. OmniService v3.0 `MessageOut`/`MessageIn`: 0 on all eight chains. These are 12-hour counts; a 0 does not show that a chain is unused.
- **Sample transactions** (`eth_getTransactionReceipt`, `MessageIn` data decoded): Ethereum `0x5a53219d119559d174a02e3f3b24466688d8cde9e588e17b3a35c4b12f10e066` (`messageIn` by the relayer; USDC `Transfer` bridge → `MessageIn.to`; `fromChain` 22776, `toChain` 1); Robinhood `0x7fc7503851e04f57fcf2bec0b4bfca3820b21848a7415be39ac684d904875261` (`MessageOut`, `fromChain` 4663 → `toChain` 56) and `0x048dd79a5812c456d87fb53cf0c172aa1e3e3238693677c7fce6a65072d89f91` (`MessageIn` from X Layer 196, `token` = zero address, WETH burned at the bridge).
- **Source disagreements:** the bridge-integration "Deployed Contracts" page and `evmv3/deployments/deploy.json` do not list Robinhood Chain, while the omnichain page does and the chain state confirms it. The omnichain page lists OmniService v3.0 on Base, Optimism and Arbitrum, where `eth_getCode` returns `0x`. The v3.1 omnichain table omits Avalanche, where the bridge has code and the bridge-integration page lists it.

**Authoritative sources:**
- Bridge repo: <https://github.com/butternetwork/butter-mos-contracts> (`evmv3/`)
- OmniService v3.0 repo: <https://github.com/butternetwork/omniservice-contracts> (`evm/contracts/`, `evm/deployments/deployments.json`)
- Docs: <https://docs.butternetwork.io> · <https://docs.butternetwork.io/butter-omnichain-messaging-integration/deployed-omnichain-contracts> · <https://docs.butternetwork.io/butter-bridge-integration/deployed-bridge-contracts> · MAP Protocol: <https://docs.mapprotocol.io>
- Explorers: Etherscan / Basescan / BscScan / Snowscan / Arbiscan / Optimistic Etherscan / Polygonscan / <https://robinhoodchain.blockscout.com> / <https://eth.blockscout.com>; MAP relay <https://maposcan.io>
