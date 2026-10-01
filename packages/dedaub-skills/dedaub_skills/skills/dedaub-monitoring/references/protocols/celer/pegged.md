# Celer Pegged-Token Bridge — Topics, Selectors, Addresses (Ethereum, BNB, Avalanche, Arbitrum, Optimism, Polygon, Base)

**Status:** verified against live RPC on every listed chain and the canonical `celer-network/sgn-v2-contracts` repo on 2026-06-09. Extended on 2026-09-29: the Base `PeggedTokenBridgeV2`, the Optimism `OriginalTokenVaultV2`, the `TransferAgent` (Ethereum, BNB) from the official cBridge contract list, and the Robinhood Chain (4663) check.
**Scope:** the **pegged-token (mint/burn) bridge** — `OriginalTokenVault` (v1) / `OriginalTokenVaultV2` (the lock side), `PeggedTokenBridge` (v1) / `PeggedTokenBridgeV2` (the mint/burn side), and the `TransferAgent` front door that routes into them. This is a **separate product** from the liquidity-pool cBridge + MessageBus in [core.md](./core.md). Topics/selectors are **chain-agnostic**; addresses are **network-specific**. **Base carries only a `PeggedTokenBridgeV2`** (`0x5471ea8f739dd37E9B81Be9c5c77754D8AA953E4`: no vault and no v1 bridge). **Robinhood Chain carries no Celer contract.**

The pegged bridge runs a classic **lock-and-mint** model. On the *canonical* (original-token) chain an `OriginalTokenVault` **locks** the real token (`deposit` → emits `Deposited`); the SGN attests; on the *pegged* chain a `PeggedTokenBridge` **mints** a wrapped representation (`mint` → emits `Mint`). To go back, the user **burns** the pegged token (`burn` → emits `Burn`) and the vault **releases** the original (`withdraw` → emits `Withdrawn`). All four contracts inherit the same safeguard mixins as the pool `Bridge` (`Pauser`, `VolumeControl`, `DelayedTransfer`) and use the pool `Bridge` as their **`sigsVerifier`** (SGN signature checker).

**All four pegged contracts are non-upgradeable immutable singletons** — `eth_getCode` returns full runtime (10–14 KB) and **both EIP-1967 slots read `0x0`** on every chain. There is **no proxy, no `Upgraded` event** for these; only governance params (signers, caps, pause, delay thresholds) change.

**v1 vs v2:** v2 adds a `nonce` field for replay-uniqueness (`OriginalTokenVaultV2.Deposited` and `PeggedTokenBridgeV2.Burn` gain a trailing `uint64 nonce`) and a per-token `supplies` accounting map on the bridge (emits `SupplyUpdated`). **Both versions coexist live** on the same chains; v2 is the current default for new tokens, v1 remains for legacy pegs. **Critically, the v1 and v2 `Mint` events are byte-identical** (same 7-field signature, same topic0) and the v1/v2 `Withdrawn` events are byte-identical too — so you must disambiguate v1 vs v2 by the **emitter address**, not the topic0.

---

## 0. Contract families & versions

| Contract | Side | Adds vs prior | Proxy? | One-liner |
|----------|------|---------------|--------|-----------|
| **OriginalTokenVault** (v1) | lock (canonical chain) | — | No (immutable) | Locks original token; `deposit`→`Deposited`, `withdraw`→`Withdrawn`. |
| **OriginalTokenVaultV2** | lock | `+uint64 nonce` in `Deposited` | No | Same role; nonce-unique deposit IDs. |
| **PeggedTokenBridge** (v1) | mint/burn (pegged chain) | — | No | Mints/burns wrapped token; `mint`→`Mint`, `burn`→`Burn`. |
| **PeggedTokenBridgeV2** | mint/burn | `+uint64 nonce` in `Burn`, `supplies` map (`SupplyUpdated`), `burnFrom` | No | Current default; per-token supply cap accounting. |
| **TransferAgent** (`contracts/proxy/TransferAgent.sol`) | front door (Ethereum, BNB) | routes a user `transfer`/`transferNative` to the vault or bridge chosen by `bridgeSendType`; emits `Supplement` | No (immutable, 7,063 B) | Adds a `Supplement` event with the same `transferId` as the vault/bridge event in the same tx. |

---

## 1. Topics (chain-agnostic — `topic0 = keccak256(event signature)`)

**No params on any pegged event are `indexed`** (matching the pool Bridge) — all fields live in `data`, topics length = 1. Filter by `(address, topic0)` then ABI-decode.

### 1.1 OriginalTokenVault (v1) — lock side

| topic0 | Event |
|--------|-------|
| `0x15d2eeefbe4963b5b2178f239ddcc730dda55f1c23c22efb79ded0eb854ac789` | `Deposited(bytes32 depositId, address depositor, address token, uint256 amount, uint64 mintChainId, address mintAccount)` *(verified live on ETH)* |
| `0x296a629c5265cb4e5319803d016902eb70a9079b89655fe2b7737821ed88beeb` | `Withdrawn(bytes32 withdrawId, address receiver, address token, uint256 amount, uint64 refChainId, bytes32 refId, address burnAccount)` |
| `0x0f48d517989455cd80ed52427e80553e66f9b69fd5cee8e26bd1a1f9c364fba6` | `MinDepositUpdated(address token, uint256 amount)` |
| `0x0e5d348f9737ccc8b4cf0eea0ccf3670af071af8bea5d64664f10e700c08de72` | `MaxDepositUpdated(address token, uint256 amount)` |

### 1.2 OriginalTokenVaultV2 — lock side (note the trailing `nonce` on `Deposited`)

| topic0 | Event |
|--------|-------|
| `0x28d226819e371600e26624ebc4a9a3947117ee2760209f816c789d3a99bf481b` | `Deposited(bytes32 depositId, address depositor, address token, uint256 amount, uint64 mintChainId, address mintAccount, uint64 nonce)` |
| `0x296a629c5265cb4e5319803d016902eb70a9079b89655fe2b7737821ed88beeb` | `Withdrawn(bytes32 withdrawId, address receiver, address token, uint256 amount, uint64 refChainId, bytes32 refId, address burnAccount)` **(identical topic0 to v1 — key on emitter)** |
| `0x0f48d517989455cd80ed52427e80553e66f9b69fd5cee8e26bd1a1f9c364fba6` | `MinDepositUpdated(address token, uint256 amount)` |
| `0x0e5d348f9737ccc8b4cf0eea0ccf3670af071af8bea5d64664f10e700c08de72` | `MaxDepositUpdated(address token, uint256 amount)` |

### 1.3 PeggedTokenBridge (v1) — mint/burn side

| topic0 | Event |
|--------|-------|
| `0x5bc84ecccfced5bb04bfc7f3efcdbe7f5cd21949ef146811b4d1967fe41f777a` | `Mint(bytes32 mintId, address token, address account, uint256 amount, uint64 refChainId, bytes32 refId, address depositor)` |
| `0x75f1bf55bb1de41b63a775dc7d4500f01114ee62b688a6b11d34f4692c1f3d43` | `Burn(bytes32 burnId, address token, address account, uint256 amount, address withdrawAccount)` |
| `0x3796cd0b17a8734f8da819920625598e9a18be490f686725282e5383f1d06683` | `MinBurnUpdated(address token, uint256 amount)` |
| `0xa3181379f6db47d9037efc6b6e8e3efe8c55ddb090b4f0512c152f97c4e47da5` | `MaxBurnUpdated(address token, uint256 amount)` |

### 1.4 PeggedTokenBridgeV2 — mint/burn side (note the trailing `nonce` on `Burn`)

| topic0 | Event |
|--------|-------|
| `0x5bc84ecccfced5bb04bfc7f3efcdbe7f5cd21949ef146811b4d1967fe41f777a` | `Mint(bytes32 mintId, address token, address account, uint256 amount, uint64 refChainId, bytes32 refId, address depositor)` **(identical topic0 to v1 `Mint` — key on emitter)** |
| `0x6298d7b58f235730b3b399dc5c282f15dae8b022e5fbbf89cee21fd83c8810a3` | `Burn(bytes32 burnId, address token, address account, uint256 amount, uint64 toChainId, address toAccount, uint64 nonce)` |
| `0xeb2f7272b55acd6dea98f5742868e8d2221ad82acb36b2d0cdd00150290e9499` | `SupplyUpdated(address token, uint256 supply)` |
| `0x3796cd0b17a8734f8da819920625598e9a18be490f686725282e5383f1d06683` | `MinBurnUpdated(address token, uint256 amount)` |
| `0xa3181379f6db47d9037efc6b6e8e3efe8c55ddb090b4f0512c152f97c4e47da5` | `MaxBurnUpdated(address token, uint256 amount)` |

### 1.5 Shared safeguard-mixin topics

The same `Paused`/`Unpaused`/`SignersUpdated`/`DelayPeriodUpdated`/`DelayThresholdUpdated`/`DelayedTransferAdded`/`DelayedTransferExecuted`/`EpochVolumeUpdated`/`OwnershipTransferred` topics listed in [core.md §1.2](./core.md) are emitted by these pegged contracts too. **Disambiguate by emitter address.**

| topic0 | Event |
|--------|-------|
| `0xcbcfffe5102114216a85d3aceb14ad4b81a3935b1b5c468fadf3889eb9c5dce6` | `DelayedTransferAdded(bytes32 id)` (large mint/withdraw routed through delay queue) |
| `0x3b40e5089937425d14cdd96947e5661868357e224af59bd8b24a4b8a330d4426` | `DelayedTransferExecuted(bytes32 id, address receiver, address token, uint256 amount)` |
| `0x62e78cea01bee320cd4e420270b5ea74000d11b0c9f74754ebdbfc544b05a258` / `0x5db9ee0a495bf2e6ff9c91a7834c1ba4fdd244a5e8aa4e537bd38aeae4b073aa` | `Paused(address)` / `Unpaused(address)` |
| `0x8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e0` | `OwnershipTransferred(address,address)` |

### 1.6 TransferAgent (Ethereum, BNB) — front door into the pegged contracts

`BridgeSendType` is an enum → `uint8`: `0 Null, 1 Liquidity, 2 PegDeposit, 3 PegBurn, 4 PegV2Deposit, 5 PegV2Burn, 6 PegV2BurnFrom`. `Extension` is `(uint8 Type, bytes Value)`. Both topic0s were found in the runtime bytecode of both TransferAgent addresses.

| topic0 | Event |
|--------|-------|
| `0x3f2b4c063a18045940932b9fba423a72e3b8d36e63ca462720d880f7b64504ca` | `Supplement(uint8 bridgeSendType, bytes32 transferId, address sender, bytes receiver, (uint8 Type, bytes Value)[] extensions)` — status only (the value moves in the vault/bridge event of the same tx). `transferId` = the `depositId`/`burnId` of that event; `sender` is the real user and `receiver` may be a non-EVM address. |
| `0xe85507dd8a6159a69bf9f4aa5ae1283824ec9948b7d4a03d5cb457070f312dfc` | `BridgeUpdated(uint8 bridgeSendType, address bridgeAddr)` — admin: the vault/bridge that a send type routes to changed. |

---

## 2. Function signatures (chain-agnostic — `keccak256(canonical sig)[0:4]`)

### 2.1 OriginalTokenVault (v1 & V2)

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x23463624` | `deposit(address _token, uint256 _amount, uint64 _mintChainId, address _mintAccount, uint64 _nonce)` | Lock original. Emits `Deposited`. (V2 uses `_nonce` for the id; v1 ignores it in the id but the selector is the same canonical 5-arg form on V2; v1's `deposit` is the 5-arg too.) |
| `0x00a95fd7` | `depositNative(uint256 _amount, uint64 _mintChainId, address _mintAccount, uint64 _nonce)` | `payable` — wrap native then lock. |
| `0xa21a9280` | `withdraw(bytes _request, bytes[] _sigs, address[] _signers, uint256[] _powers)` | Release original (SGN-signed). Emits `Withdrawn`. **Same selector as `Bridge.withdraw` (core.md) — disambiguate by contract.** |
| `0x01e64725` | `records(bytes32)` → `bool` | Replay-guard map (deposit & withdraw ids). |
| `0x457bfa2f` | `nativeWrap()` → `address` | Chain's WETH-equivalent. |

### 2.2 PeggedTokenBridge (v1) & PeggedTokenBridgeV2

| Selector | Signature | Version | Notes |
|----------|-----------|---------|-------|
| `0xf8734302` | `mint(bytes _request, bytes[] _sigs, address[] _signers, uint256[] _powers)` | v1 + v2 | Mint pegged (SGN-signed). Emits `Mint`. `mintId` derivation differs slightly v1/v2 but the selector is identical. |
| `0xde790c7e` | `burn(address _token, uint256 _amount, address _withdrawAccount, uint64 _nonce)` | **v1** | Burn pegged → withdraw original at remote vault. Emits v1 `Burn`. |
| `0xa0029301` | `burn(address _token, uint256 _amount, uint64 _toChainId, address _toAccount, uint64 _nonce)` | **v2** | Burn pegged → withdraw OR remote-mint. Emits v2 `Burn`. **Different arity/selector from v1.** |
| `0x9e422c33` | `burnFrom(address _token, uint256 _amount, uint64 _toChainId, address _toAccount, uint64 _nonce)` | v2 only | OZ `ERC20Burnable` path. Emits v2 `Burn`. |
| `0x01e64725` | `records(bytes32)` → `bool` | both | Replay-guard. |
| `0x274cee31` | `supplies(address)` → `uint256` | **v2 only** | Per-token minted supply (drives `SupplyUpdated`). Absent on v1. |

`minBurn(address)` / `maxBurn(address)` getters: per-token caps (auto-generated public mappings). `maxBurn == 0` = no cap; `minBurn` is a strict `>` lower bound.

### 2.3 TransferAgent

| Selector | Signature | Notes |
|----------|-----------|-------|
| `0x39b0070c` | `transfer(bytes _receiver, address _token, uint256 _amount, uint64 _dstChainId, uint64 _nonce, uint32 _maxSlippage, uint8 _bridgeSendType, (uint8 Type, bytes Value)[] _extensions)` | Pulls `_token` from the user and calls the routed vault/bridge; emits `Supplement`. |
| `0xc5d8ac7e` | `transferNative(bytes _receiver, uint256 _amount, uint64 _dstChainId, uint64 _nonce, uint32 _maxSlippage, uint8 _bridgeSendType, (uint8 Type, bytes Value)[] _extensions)` | `payable`; native variant (the vault wraps to WETH). Emits `Supplement`. |
| `0x65d67c33` | `bridges(uint8)` → `address` | view: routing table. Read on 2026-09-29: Ethereum `2` → OTV v1, `3` → PegBridge v1, `4` → OTV V2, `5` → PegBridge V2, `1` and `6` → `0x0`; BNB `4` → OTV V2, `5` → PegBridge V2, `1` → `0x0`. |
| `0x6701d514` | `setBridgeAddress(uint8 _bridgeSendType, address _addr)` | owner only; emits `BridgeUpdated`. |

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Wiring confirmed: the ETH MessageBus `pegBridge/pegVault/pegBridgeV2/pegVaultV2` getters resolve to exactly these four addresses (see core.md §Verification).

| Role | Address | One-liner |
|------|---------|-----------|
| **OriginalTokenVault** (v1) | `0xB37D31b2A74029B5951a2778F959282E2D518595` | Lock vault, 11,833 B immutable. |
| **OriginalTokenVaultV2** | `0x7510792A3B1969F9307F3845CE88e39578f2bAE1` | Lock vault v2, 13,534 B immutable. |
| **PeggedTokenBridge** (v1) | `0x16365b45EB269B5B5dACB34B4a15399Ec79b95eB` | Mint/burn, 10,983 B immutable. |
| **PeggedTokenBridgeV2** | `0x52E4f244f380f8fA51816c8a10A63105dd4De084` | Mint/burn v2, 12,011 B immutable. |
| TransferAgent | `0x9b274BC73940d92d0Af292Bde759cbFCCE661a0b` | Front door, 7,063 B immutable; `owner()` = `0xf380166f8490f24af32bf47d1aa217fba62b6575`; routes send types 2–5 to the four contracts above (`bridges(uint8)`). |

## 4. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | Bytes |
|------|---------|-------|
| OriginalTokenVault (v1) | `0x78bc5Ee9F11d133A08b331C2e18fE81BE0Ed02DC` | 13,536 |
| OriginalTokenVaultV2 | `0x11a0c9270D88C99e221360BCA50c2f6Fda44A980` | 13,534 |
| PeggedTokenBridge (v1) | `0xd443FE6bf23A4C9B78312391A30ff881a097580E` | 10,983 |
| PeggedTokenBridgeV2 | `0x26c76F7FeF00e02a5DD4B5Cc8a0f717eB61e1E4b` | 12,011 (literal also = Avalanche MessageBus impl — `(chainId,addr)` keying) |
| TransferAgent | `0x3d85B598B734a0E7c8c1b62B00E972e9265dA541` | 7,063 (same code hash as the Ethereum TransferAgent); routes send types 4 and 5 to OTV V2 and PegBridge V2 |

## 5. Addresses — Avalanche C-Chain (chain ID 43114)

| Role | Address | Bytes |
|------|---------|-------|
| OriginalTokenVault (v1) | `0x5427FEFA711Eff984124bFBB1AB6fbf5E3DA1820` | 13,536 (literal also = Ethereum **Bridge** — different contract per chain; the Avalanche **Bridge** is `0xef3c714c…e5d4`) |
| OriginalTokenVaultV2 | `0xb51541df05DE07be38dcfc4a80c05389A54502BB` | 13,534 (literal also = Polygon PeggedTokenBridgeV2) |
| PeggedTokenBridge (v1) | `0x88DCDC47D2f83a99CF0000FDF667A468bB958a78` | 10,983 (literal also = Polygon **Bridge**) |
| PeggedTokenBridgeV2 | `0xb774C6f82d1d5dBD36894762330809e512feD195` | 12,011 |

## 6. Addresses — Arbitrum One (chain ID 42161)

| Role | Address | Bytes |
|------|---------|-------|
| OriginalTokenVault (v1) | `0xFe31bFc4f7C9b69246a6dc0087D91a91Cb040f76` | 13,536 |
| OriginalTokenVaultV2 | `0xEA4B1b0aa3C110c55f650d28159Ce4AD43a4a58b` | 13,534 |
| PeggedTokenBridge (v1) | `0xbdd2739AE69A054895Be33A22b2D2ed71a1DE778` | 10,983 |
| PeggedTokenBridgeV2 | `0xc72e7fC220e650e93495622422F3c14fb03aAf6B` | 12,142 |

## 7. Addresses — Optimism (chain ID 10)

| Role | Address | Bytes |
|------|---------|-------|
| OriginalTokenVault (v1) | `0xbCfeF6Bb4597e724D720735d32A9249E0640aA11` | 13,536 |
| OriginalTokenVaultV2 | `0x6e380ad5D15249eF2DE576E3189fc49B5713BE4f` | 13,488 (listed in the official cBridge contract list as of 2026-09-29; bytecode carries the v2 `Deposited` and `Withdrawn` topic0s; `sigsVerifier()` = the Optimism Bridge `0x9D39Fc627A6d9d9F8C831c16995b209548cc3401`; `owner()` = `0xf380166f8490f24af32bf47d1aa217fba62b6575`) |
| PeggedTokenBridge (v1) | `0x61f85fF2a2f4289Be4bb9B72Fc7010B3142B5f41` | 10,983 |
| PeggedTokenBridgeV2 | `0xC3c5B9474273113efB74e7Da43B5AAba0Cd9699A` | 12,142 |

## 8. Addresses — Polygon PoS (chain ID 137)

| Role | Address | Bytes |
|------|---------|-------|
| OriginalTokenVault (v1) | `0xc1a2D967DfAa6A10f3461bc21864C23C1DD51EeA` | 13,536 |
| OriginalTokenVaultV2 | `0x4C882ec256823eE773B25b414d36F92ef58a7c0C` | 13,534 |
| PeggedTokenBridge (v1) | `0x4d58FDC7d0Ee9b674F49a0ADE11F26C3c9426F7A` | 10,983 |
| PeggedTokenBridgeV2 | `0xb51541df05DE07be38dcfc4a80c05389A54502BB` | 12,142 (literal also = Avalanche OriginalTokenVaultV2) |

## 9. Addresses — Base (chain ID 8453)

Base carries **one pegged contract**, listed in the official cBridge contract list ("PeggedTokenBridge V2 Contract" → Base) and verified with `eth_getCode` on 2026-09-29:

| Role | Address | Bytes |
|------|---------|-------|
| **PeggedTokenBridgeV2** | `0x5471ea8f739dd37E9B81Be9c5c77754D8AA953E4` | 12,104, immutable (EIP-1967 impl slot `0x0`). Bytecode carries `Mint`, the v2 `Burn` and `SupplyUpdated` topic0s and the `mint`/`burn`/`burnFrom`/`supplies` selectors. `sigsVerifier()` = the Base pool Bridge `0x7d43AABC515C356145049227CeE54B608342c0ad`; `owner()` = `0xf380166f8490f24af32bf47d1aa217fba62b6575`. |

**Not on Base:** `OriginalTokenVault` (v1 and V2), `PeggedTokenBridge` v1, TransferAgent, MessageBus. An earlier revision of this file said that Base had no pegged contract; this section corrects it. Activity: 0 `Mint` and 0 `Burn` in the pinned 12-hour window 2026-09-28 00:00–12:00 UTC; the Blockscout log list shows `Mint` at block 51,777,202 (tx `0xad781811fc9459810be08de48c703bbff39e8b0cef573cbde4f7c55db7557911`, a `Transfer` from `0x0` of the pegged token to the recipient) and a v2 `Burn` at block 49,663,651 (tx `0x42bafec39237a99bae3ecd351425931ff3ef3188033d79d18176af6d1911bedc`).

## 9a. Robinhood Chain (chain ID 4663) — no Celer deployment

Robinhood Chain is in neither the official cBridge contract list nor the Celer IM contract list. `eth_getCode` returned `0x` (nonce 0) on 2026-09-29 at all 24 distinct pegged-contract literals of §3–§9, at both TransferAgent literals, at the four pool-Bridge literals reused across Celer chains (`0x9B36f165baB9ebe611d491180418d8De4b8f3a1f`, `0x841ce48F9446C8E281D3F1444cB859b4A6D0738C`, `0xf5C6825015280CdfD0b56903F9F8B5A2233476F5`, `0x9Bb46D5100d2Db4608112026951c9C965b233f4D`), and at the TransferAgent literals. The pegged `Mint`/`Burn`/`Deposited`/`Withdrawn` topic0s returned 0 logs on Robinhood Chain in the pinned window.

---

## 10. Cross-chain summary

| Chain | ID | OTV v1 | OTV V2 | PegBridge v1 | PegBridge V2 | TransferAgent |
|---|---|---|---|---|---|---|
| Ethereum | 1 | `0xB37D31b2A74029B5951a2778F959282E2D518595` | `0x7510792A3B1969F9307F3845CE88e39578f2bAE1` | `0x16365b45EB269B5B5dACB34B4a15399Ec79b95eB` | `0x52E4f244f380f8fA51816c8a10A63105dd4De084` | `0x9b274BC73940d92d0Af292Bde759cbFCCE661a0b` |
| BNB | 56 | `0x78bc5Ee9F11d133A08b331C2e18fE81BE0Ed02DC` | `0x11a0c9270D88C99e221360BCA50c2f6Fda44A980` | `0xd443FE6bf23A4C9B78312391A30ff881a097580E` | `0x26c76F7FeF00e02a5DD4B5Cc8a0f717eB61e1E4b` | `0x3d85B598B734a0E7c8c1b62B00E972e9265dA541` |
| Avalanche | 43114 | `0x5427FEFA711Eff984124bFBB1AB6fbf5E3DA1820` | `0xb51541df05DE07be38dcfc4a80c05389A54502BB` | `0x88DCDC47D2f83a99CF0000FDF667A468bB958a78` | `0xb774C6f82d1d5dBD36894762330809e512feD195` | — |
| Arbitrum | 42161 | `0xFe31bFc4f7C9b69246a6dc0087D91a91Cb040f76` | `0xEA4B1b0aa3C110c55f650d28159Ce4AD43a4a58b` | `0xbdd2739AE69A054895Be33A22b2D2ed71a1DE778` | `0xc72e7fC220e650e93495622422F3c14fb03aAf6B` | — |
| Optimism | 10 | `0xbCfeF6Bb4597e724D720735d32A9249E0640aA11` | `0x6e380ad5D15249eF2DE576E3189fc49B5713BE4f` | `0x61f85fF2a2f4289Be4bb9B72Fc7010B3142B5f41` | `0xC3c5B9474273113efB74e7Da43B5AAba0Cd9699A` | — |
| Polygon | 137 | `0xc1a2D967DfAa6A10f3461bc21864C23C1DD51EeA` | `0x4C882ec256823eE773B25b414d36F92ef58a7c0C` | `0x4d58FDC7d0Ee9b674F49a0ADE11F26C3c9426F7A` | `0xb51541df05DE07be38dcfc4a80c05389A54502BB` | — |
| **Base** | 8453 | — | — | — | `0x5471ea8f739dd37E9B81Be9c5c77754D8AA953E4` | — |
| **Robinhood Chain** | 4663 | — | — | — | — | — (no Celer contract; not in the official lists) |

All present addresses re-checked with `eth_getCode` on 2026-09-29; every one has code and none is an EIP-1967 proxy.

**Collision tells (key on `(chainId, address)` always):**
- `0x5427FEFA711Eff984124bFBB1AB6fbf5E3DA1820` = Ethereum **Bridge** AND Avax **OriginalTokenVault v1** (the Avax **Bridge** is the different literal `0xef3c714c9425a8F3697A9C969Dc1af30ba82e5d4`).
- `0x88DCDC47D2f83a99CF0000FDF667A468bB958a78` = Polygon **Bridge** AND Avax **PeggedTokenBridge v1**.
- `0xb51541df05DE07be38dcfc4a80c05389A54502BB` = Avax **OriginalTokenVaultV2** AND Polygon **PeggedTokenBridgeV2**.
- `0x26c76F7FeF00e02a5DD4B5Cc8a0f717eB61e1E4b` = BNB **PeggedTokenBridgeV2** AND Avax **MessageBus impl**.
- `0x5471ea8f739dd37E9B81Be9c5c77754D8AA953E4` = Base **PeggedTokenBridgeV2**, but the same literal also has code on Arbitrum (a 1,554 B EIP-1967 proxy, impl `0x223fb0ceb2c6e5310264efe38151d7d083db91f1`) and Polygon (11,620 B). The official lists do not name those two contracts; do not treat them as a Base-style pegged bridge.

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **OriginalTokenVault / V2** | **Immutable, no proxy** | EIP-1967 impl slot `0x3608…2bbc` = `0x0`; full 11–14 KB runtime. | none (params only). |
| **PeggedTokenBridge / V2** | **Immutable, no proxy** | EIP-1967 impl slot = `0x0`; full 11–12 KB runtime (Base: 12,104 B). | none (params only). |
| **TransferAgent** (Ethereum, BNB) | **Immutable, no proxy** | EIP-1967 impl slot = `0x0`; 7,063 B runtime, same code hash on both chains. | `owner()` (Ethereum: `0xf380166f8490f24af32bf47d1aa217fba62b6575`) can re-route a send type with `setBridgeAddress` (`BridgeUpdated`). |

EIP-1967 impl slot `0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`; admin slot `0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103`. **All four pegged contracts are immutable** — there is **no `Upgraded` event** to watch; to "upgrade", Celer deploys a fresh contract and re-points the MessageBus `peg*` getters (watch `PegBridgeUpdated`/`PegVaultUpdated`/`PegBridgeV2Updated`/`PegVaultV2Updated` on the MessageBus — core.md §1.4). `sigsVerifier()` on each pegged contract returns the chain's pool `Bridge` address.

---

## 12. Detection invariants & gotchas

1. **A peg bridge = a lock/burn on chain A + a mint/withdraw on chain B**, across chains, never in one tx. Lock-mint: `Deposited`(vault, chain A) ↔ `Mint`(bridge, chain B), correlated by `depositId`/`refId`. Burn-withdraw: `Burn`(bridge, chain B) ↔ `Withdrawn`(vault, chain A), correlated by `burnId`/`refId`. The `refId`/`refChainId` fields on the destination event point back to the source event id/chain.
2. **v1 and v2 `Mint` share topic0 `0x5bc84ecc…`; v1 and v2 `Withdrawn` share topic0 `0x296a629c…`.** You cannot tell version from the topic — **key on the emitting contract address** (§10).
3. **v1 vs v2 `Burn` DO differ** — v1 `Burn` `0x75f1bf55…` (5 fields, `withdrawAccount`), v2 `Burn` `0x6298d7b5…` (7 fields, `toChainId`+`nonce`). And `Deposited` differs — v1 `0x15d2eeef…` (6 fields), v2 `0x28d22681…` (7 fields, trailing `nonce`).
4. **No event param is `indexed`** — all in `data`. Filter `(address, topic0)` then decode; you cannot topic-filter by token or account.
5. **`OriginalTokenVault.withdraw` selector `0xa21a9280` collides with `Bridge.withdraw`** (core.md). Same 4-arg `(bytes,bytes[],address[],uint256[])`. Disambiguate by contract address.
6. **Large mints/withdrawals are delayed.** Above `delayThresholds[token]`, the contract emits `DelayedTransferAdded(id)` and defers the actual `mint`/release; the payout later fires `DelayedTransferExecuted`. A `Mint`/`Withdrawn` event is still emitted, but the token movement may lag — track both.
7. **`supplies`/`SupplyUpdated` exist only on PeggedTokenBridgeV2.** It is the per-token minted-supply accountant (burn decrements, mint increments). v1 has no supply cap accounting. A sudden `SupplyUpdated` divergence from on-chain `totalSupply` is a risk signal.
8. **`maxBurn`/`maxDeposit == 0` means "no cap"**, not "zero". `minBurn`/`minDeposit` are strict `>` lower bounds.
9. **These are immutable** — no `Upgraded` event. A contract swap is signalled by the MessageBus `Peg*Updated` events, not by an in-place upgrade.
10. **Base has a PeggedTokenBridgeV2 only** (`0x5471ea8f739dd37E9B81Be9c5c77754D8AA953E4`): Base can be the mint side (`Mint`) or the burn side (v2 `Burn`) of a pegged route, never the lock side (no vault). The pegged contracts also span many out-of-scope counterparty chains (the pegged model is how Celer bridges to chains without deep liquidity).
11. **Fee-on-transfer / rebasing tokens unsupported** (vault/bridge assume 1:1 transfers) — listing such a token mis-accounts the lock/supply.
12. **A TransferAgent deposit hides the user from the vault event.** When a user enters through the TransferAgent, `Deposited.depositor` (or the `Burn` account) is the TransferAgent address, and the real user is `Supplement.sender` in the same tx. `Supplement.transferId` equals the vault/bridge id (`depositId`/`burnId`), and `Supplement.receiver` is `bytes` (a non-EVM address is possible; then `mintAccount` is `0x0`). Sample: Ethereum tx `0xfc8c58b8e3f0134185e7740aa189676142a88288d7f2ab01555c1680ba45bead` — `transferNative` with 0.5 ETH, WETH `Deposit` to OTV V2, v2 `Deposited` (depositor = TransferAgent, `mintChainId` 12360001, `mintAccount` `0x0`), then `Supplement` (`bridgeSendType` 4, same id, `sender` = the user, 32-byte `receiver`).
13. **Robinhood Chain has no Celer contract** (§9a). A pegged or pool event on chain 4663 is not a Celer event.
14. **Value legs.** Lock: ERC-20 `Transfer` user → vault (or WETH `Deposit` for native) next to `Deposited`. Mint: `Transfer` from `0x0` of the pegged token to the recipient next to `Mint`. Burn: `Transfer` from the user to `0x0` next to `Burn`. Release: `Transfer` vault → recipient next to `Withdrawn`.

---

## 13. Quick-copy detection constants (bytea-ready for PG)

```
-- ===== Topics =====
-- OriginalTokenVault v1
TOPIC_OTV_DEPOSITED_V1        = '\x15d2eeefbe4963b5b2178f239ddcc730dda55f1c23c22efb79ded0eb854ac789'
-- OriginalTokenVaultV2 (note trailing nonce)
TOPIC_OTV_DEPOSITED_V2        = '\x28d226819e371600e26624ebc4a9a3947117ee2760209f816c789d3a99bf481b'
-- Withdrawn (SAME topic0 for v1 AND v2 — key on emitter)
TOPIC_OTV_WITHDRAWN           = '\x296a629c5265cb4e5319803d016902eb70a9079b89655fe2b7737821ed88beeb'
TOPIC_OTV_MIN_DEPOSIT_UPDATED = '\x0f48d517989455cd80ed52427e80553e66f9b69fd5cee8e26bd1a1f9c364fba6'
TOPIC_OTV_MAX_DEPOSIT_UPDATED = '\x0e5d348f9737ccc8b4cf0eea0ccf3670af071af8bea5d64664f10e700c08de72'
-- PeggedTokenBridge v1 + v2 (SAME Mint topic0 — key on emitter)
TOPIC_PEG_MINT                = '\x5bc84ecccfced5bb04bfc7f3efcdbe7f5cd21949ef146811b4d1967fe41f777a'
-- Burn differs by version
TOPIC_PEG_BURN_V1             = '\x75f1bf55bb1de41b63a775dc7d4500f01114ee62b688a6b11d34f4692c1f3d43'
TOPIC_PEG_BURN_V2             = '\x6298d7b58f235730b3b399dc5c282f15dae8b022e5fbbf89cee21fd83c8810a3'
TOPIC_PEG_SUPPLY_UPDATED      = '\xeb2f7272b55acd6dea98f5742868e8d2221ad82acb36b2d0cdd00150290e9499'
TOPIC_PEG_MIN_BURN_UPDATED    = '\x3796cd0b17a8734f8da819920625598e9a18be490f686725282e5383f1d06683'
TOPIC_PEG_MAX_BURN_UPDATED    = '\xa3181379f6db47d9037efc6b6e8e3efe8c55ddb090b4f0512c152f97c4e47da5'
-- shared delay-queue
TOPIC_DELAYED_ADDED           = '\xcbcfffe5102114216a85d3aceb14ad4b81a3935b1b5c468fadf3889eb9c5dce6'
TOPIC_DELAYED_EXECUTED        = '\x3b40e5089937425d14cdd96947e5661868357e224af59bd8b24a4b8a330d4426'
-- TransferAgent (Ethereum, BNB)
TOPIC_AGENT_SUPPLEMENT        = '\x3f2b4c063a18045940932b9fba423a72e3b8d36e63ca462720d880f7b64504ca'   -- status only; transferId = vault/bridge id
TOPIC_AGENT_BRIDGE_UPDATED    = '\xe85507dd8a6159a69bf9f4aa5ae1283824ec9948b7d4a03d5cb457070f312dfc'

-- ===== Selectors =====
SEL_AGENT_TRANSFER            = '\x39b0070c'
SEL_AGENT_TRANSFER_NATIVE     = '\xc5d8ac7e'
SEL_AGENT_BRIDGES             = '\x65d67c33'
SEL_AGENT_SET_BRIDGE_ADDRESS  = '\x6701d514'
SEL_OTV_DEPOSIT               = '\x23463624'
SEL_OTV_DEPOSIT_NATIVE        = '\x00a95fd7'
SEL_OTV_WITHDRAW              = '\xa21a9280'   -- also Bridge.withdraw
SEL_PEG_MINT                  = '\xf8734302'
SEL_PEG_BURN_V1               = '\xde790c7e'
SEL_PEG_BURN_V2               = '\xa0029301'
SEL_PEG_BURN_FROM             = '\x9e422c33'
SEL_PEG_SUPPLIES              = '\x274cee31'
SEL_RECORDS                   = '\x01e64725'

-- ===== Proxy slots (all read 0x0 — immutable) =====
EIP1967_IMPL_SLOT             = '\x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc'
EIP1967_ADMIN_SLOT            = '\xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103'

-- ===== Ethereum (chain ID 1) =====
ETH_OTV_V1                    = '\xb37d31b2a74029b5951a2778f959282e2d518595'
ETH_OTV_V2                    = '\x7510792a3b1969f9307f3845ce88e39578f2bae1'
ETH_PEGBRIDGE_V1              = '\x16365b45eb269b5b5dacb34b4a15399ec79b95eb'
ETH_PEGBRIDGE_V2              = '\x52e4f244f380f8fa51816c8a10a63105dd4de084'
ETH_TRANSFER_AGENT            = '\x9b274bc73940d92d0af292bde759cbfcce661a0b'
-- ===== BNB (chain ID 56) =====
BNB_OTV_V1                    = '\x78bc5ee9f11d133a08b331c2e18fe81be0ed02dc'
BNB_OTV_V2                    = '\x11a0c9270d88c99e221360bca50c2f6fda44a980'
BNB_PEGBRIDGE_V1              = '\xd443fe6bf23a4c9b78312391a30ff881a097580e'
BNB_PEGBRIDGE_V2              = '\x26c76f7fef00e02a5dd4b5cc8a0f717eb61e1e4b'
BNB_TRANSFER_AGENT            = '\x3d85b598b734a0e7c8c1b62b00e972e9265da541'
-- ===== Avalanche (chain ID 43114) =====
AVAX_OTV_V1                   = '\x5427fefa711eff984124bfbb1ab6fbf5e3da1820'   -- also = Ethereum Bridge literal (Avax Bridge is 0xef3c714c9425a8f3697a9c969dc1af30ba82e5d4)
AVAX_OTV_V2                   = '\xb51541df05de07be38dcfc4a80c05389a54502bb'
AVAX_PEGBRIDGE_V1             = '\x88dcdc47d2f83a99cf0000fdf667a468bb958a78'   -- also = Polygon Bridge literal
AVAX_PEGBRIDGE_V2             = '\xb774c6f82d1d5dbd36894762330809e512fed195'
-- ===== Arbitrum (chain ID 42161) =====
ARB_OTV_V1                    = '\xfe31bfc4f7c9b69246a6dc0087d91a91cb040f76'
ARB_OTV_V2                    = '\xea4b1b0aa3c110c55f650d28159ce4ad43a4a58b'
ARB_PEGBRIDGE_V1              = '\xbdd2739ae69a054895be33a22b2d2ed71a1de778'
ARB_PEGBRIDGE_V2              = '\xc72e7fc220e650e93495622422f3c14fb03aaf6b'
-- ===== Optimism (chain ID 10) =====
OP_OTV_V1                     = '\xbcfef6bb4597e724d720735d32a9249e0640aa11'
OP_OTV_V2                     = '\x6e380ad5d15249ef2de576e3189fc49b5713be4f'
OP_PEGBRIDGE_V1               = '\x61f85ff2a2f4289be4bb9b72fc7010b3142b5f41'
OP_PEGBRIDGE_V2               = '\xc3c5b9474273113efb74e7da43b5aaba0cd9699a'
-- ===== Polygon (chain ID 137) =====
POLY_OTV_V1                   = '\xc1a2d967dfaa6a10f3461bc21864c23c1dd51eea'
POLY_OTV_V2                   = '\x4c882ec256823ee773b25b414d36f92ef58a7c0c'
POLY_PEGBRIDGE_V1             = '\x4d58fdc7d0ee9b674f49a0ade11f26c3c9426f7a'
POLY_PEGBRIDGE_V2             = '\xb51541df05de07be38dcfc4a80c05389a54502bb'   -- also = Avax OTV V2 literal
-- ===== Base (chain ID 8453) =====
BASE_PEGBRIDGE_V2             = '\x5471ea8f739dd37e9b81be9c5c77754d8aa953e4'   -- the only pegged contract on Base
-- ===== Robinhood Chain (chain ID 4663): no Celer contract; every literal above returns 0x =====
```

---

## 14. Verification & sources

How constants were verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` (`[0:4]` for selectors), `uint`→`uint256`, from the exact event/function declarations in `celer-network/sgn-v2-contracts` (`pegged-bridge/OriginalTokenVault.sol`, `OriginalTokenVaultV2.sol`, `PeggedTokenBridge.sol`, `PeggedTokenBridgeV2.sol`). The v1↔v2 `Mint`/`Withdrawn` topic-identity and the v1↔v2 `Burn`/`Deposited` divergence were confirmed by computing both from source.
- **Live cross-check (eth_getLogs, Ethereum):** `OriginalTokenVault.Deposited` topic0 `0x15d2eeef…` returned 10 logs on `0xB37D…8595` in a 50k-block window. (Pegged mint/burn volume is now low — Celer has wound down most pegged-token routes — so some contracts show few recent logs; topic0s are computed from verified canonical source regardless.)
- **Addresses:** parsed from the official cBridge contract-addresses doc, then existence-checked via `eth_getCode` per chain (byte sizes recorded: OTV v1 ≈ 11.8–13.5 KB, OTV V2 ≈ 13.5 KB, PegBridge v1 ≈ 11.0 KB, PegBridge V2 ≈ 12.0–12.1 KB). The four ETH addresses were independently confirmed by reading the ETH MessageBus `pegBridge/pegVault/pegBridgeV2/pegVaultV2` getters live (they resolve to exactly these). The 2026-06-09 revision recorded no pegged contract on Base; the 2026-09-29 check corrects that (§9: PeggedTokenBridgeV2 `0x5471ea8f739dd37E9B81Be9c5c77754D8AA953E4`).
- **Proxy classification:** EIP-1967 impl slot read `0x0` (immutable, non-proxy) on Ethereum for all four contract families.

Extension of 2026-09-29:

- **New addresses:** the Base PeggedTokenBridgeV2, the Optimism OriginalTokenVaultV2 and both TransferAgents come from the official cBridge contract list. Each was existence-checked with `eth_getCode`, its role confirmed by finding its event topic0s (`PUSH32`) and function selectors (`PUSH4`) in the runtime bytecode, and its wiring read with `eth_call` (`sigsVerifier()`, `owner()`, `bridges(uint8)`). EIP-1967 impl slot `0x0` on each (not proxies). TransferAgent signatures from `contracts/proxy/TransferAgent.sol` and `contracts/libraries/BridgeTransferLib.sol` (`BridgeSendType` enum → `uint8`), hashed as `keccak256(sig)`.
- **Robinhood Chain:** `eth_getCode` = `0x` (nonce 0) at every literal of this file and at the Celer pool-Bridge literals reused on other chains (§9a).
- **Activity** (`eth_getLogs`, pinned 12-hour window 2026-09-28 00:00–12:00 UTC, all emitters): v2 `Burn` — Ethereum 1 (PegBridge V2), BNB 5 (PegBridge V2), 0 on the other six. `Mint` — Ethereum 1 (PegBridge V2), BNB 9 (PegBridge V2), Avalanche 1 (PegBridge v1), 0 on the other five. v1 `Deposited` — Ethereum 2 (OTV v1), 0 elsewhere. v2 `Deposited` — Ethereum 1 (OTV V2), 0 elsewhere. `Withdrawn` and v1 `Burn` — 0 on all eight chains. `Supplement` — Ethereum 1 (TransferAgent), BNB 0 (TransferAgent, address-filtered count). Base PeggedTokenBridgeV2: 0 `Mint` / 0 `Burn` in the window (latest `Mint` at block 51,777,202 per the Blockscout log list). A 0 is a 12-hour measurement, not proof that a contract is unused.
- **Sample transactions** (`eth_getTransactionReceipt`, data decoded for the TransferAgent case): Ethereum `0xfc8c58b8e3f0134185e7740aa189676142a88288d7f2ab01555c1680ba45bead` (TransferAgent `transferNative`, §12 item 12); Ethereum `0xca3ac36f07537da53fe6196f131a98715cb24ac9a2472516d104b5e9b9c572d3` (PegBridge V2 `burn`: v2 `Burn`, then the pegged token `Transfer` user → `0x0`); Base `0xad781811fc9459810be08de48c703bbff39e8b0cef573cbde4f7c55db7557911` (`mint` from an SGN relayer: pegged token `Transfer` `0x0` → recipient, then `Mint`).
- **Source disagreements:** an earlier revision of this file said Base had no pegged contract and that the Optimism OriginalTokenVaultV2 was not in the official list; the official list of 2026-09-29 names both, and both have code.

**Authoritative sources:**
- Canonical contracts: [`celer-network/sgn-v2-contracts`](https://github.com/celer-network/sgn-v2-contracts) (`contracts/pegged-bridge/`, `contracts/proxy/TransferAgent.sol`, `contracts/libraries/BridgeTransferLib.sol`).
- Addresses: [cBridge docs — Contract Addresses](https://cbridge-docs.celer.network/reference/contract-addresses) · [Celer IM — Contract Addresses & RPC Info](https://im-docs.celer.network/developer/contract-addresses-and-rpc-info).
- Explorers: [Etherscan PeggedTokenBridge](https://etherscan.io/address/0x16365b45eb269b5b5dacb34b4a15399ec79b95eb) · [Etherscan OriginalTokenVault](https://etherscan.io/address/0xB37D31b2A74029B5951a2778F959282E2D518595) · [BaseScan PeggedTokenBridgeV2](https://basescan.org/address/0x5471ea8f739dd37e9b81be9c5c77754d8aa953e4) · [Base Blockscout log list](https://base.blockscout.com/address/0x5471ea8f739dd37e9b81be9c5c77754d8aa953e4) · [Robinhood Chain Blockscout](https://robinhoodchain.blockscout.com).
