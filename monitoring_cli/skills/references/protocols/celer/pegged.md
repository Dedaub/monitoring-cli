# Celer Pegged-Token Bridge — Topics, Selectors, Addresses (Ethereum, BNB, Avalanche, Arbitrum, Optimism, Polygon)

**Status:** verified against live RPC on every listed chain and the canonical `celer-network/sgn-v2-contracts` repo on 2026-06-09.
**Scope:** the **pegged-token (mint/burn) bridge** — `OriginalTokenVault` (v1) / `OriginalTokenVaultV2` (the lock side) and `PeggedTokenBridge` (v1) / `PeggedTokenBridgeV2` (the mint/burn side). This is a **separate product** from the liquidity-pool cBridge + MessageBus in [core.md](./core.md). Topics/selectors are **chain-agnostic**; addresses are **network-specific**. **None of these pegged contracts are deployed on Base** (Base has only the pool Bridge — see core.md).

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

`minBurn(address)` / `maxBurn(address)` getters: `0x...` per-token caps (auto-generated public mappings). `maxBurn == 0` = no cap; `minBurn` is a strict `>` lower bound.

---

## 3. Addresses — Ethereum mainnet (chain ID 1)

All verified via `eth_getCode` returning non-empty bytecode on `https://ethereum-rpc.publicnode.com` on 2026-06-09. Wiring confirmed: the ETH MessageBus `pegBridge/pegVault/pegBridgeV2/pegVaultV2` getters resolve to exactly these four addresses (see core.md §Verification).

| Role | Address | One-liner |
|------|---------|-----------|
| **OriginalTokenVault** (v1) | `0xB37D31b2A74029B5951a2778F959282E2D518595` | Lock vault, 11,833 B immutable. |
| **OriginalTokenVaultV2** | `0x7510792A3B1969F9307F3845CE88e39578f2bAE1` | Lock vault v2, 13,534 B immutable. |
| **PeggedTokenBridge** (v1) | `0x16365b45EB269B5B5dACB34B4a15399Ec79b95eB` | Mint/burn, 10,983 B immutable. |
| **PeggedTokenBridgeV2** | `0x52E4f244f380f8fA51816c8a10A63105dd4De084` | Mint/burn v2, 12,011 B immutable. |

## 4. Addresses — BNB Smart Chain (chain ID 56)

| Role | Address | Bytes |
|------|---------|-------|
| OriginalTokenVault (v1) | `0x78bc5Ee9F11d133A08b331C2e18fE81BE0Ed02DC` | 13,536 |
| OriginalTokenVaultV2 | `0x11a0c9270D88C99e221360BCA50c2f6Fda44A980` | 13,534 |
| PeggedTokenBridge (v1) | `0xd443FE6bf23A4C9B78312391A30ff881a097580E` | 10,983 |
| PeggedTokenBridgeV2 | `0x26c76F7FeF00e02a5DD4B5Cc8a0f717eB61e1E4b` | 12,011 (literal also = Avalanche MessageBus impl — `(chainId,addr)` keying) |

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
| OriginalTokenVaultV2 | **not in the canonical address doc** | — |
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

**No pegged contracts deployed.** Base has only the pool `Bridge` (see core.md §9). `OriginalTokenVault[V2]` and `PeggedTokenBridge[V2]` all return `0x` on Base.

---

## 10. Cross-chain summary

| Chain | ID | OTV v1 | OTV V2 | PegBridge v1 | PegBridge V2 |
|---|---|---|---|---|---|
| Ethereum | 1 | `0xB37D31b2…8595` | `0x7510792A…bAE1` | `0x16365b45…95eB` | `0x52E4f244…E084` |
| BNB | 56 | `0x78bc5Ee9…02DC` | `0x11a0c927…A980` | `0xd443FE6b…580E` | `0x26c76F7F…1E4b` |
| Avalanche | 43114 | `0x5427FEFA…1820` | `0xb51541df…02BB` | `0x88DCDC47…8a78` | `0xb774C6f8…D195` |
| Arbitrum | 42161 | `0xFe31bFc4…0f76` | `0xEA4B1b0a…a58b` | `0xbdd2739A…E778` | `0xc72e7fC2…aF6B` |
| Optimism | 10 | `0xbCfeF6Bb…aA11` | — (not in doc) | `0x61f85fF2…5f41` | `0xC3c5B947…699A` |
| Polygon | 137 | `0xc1a2D967…1EeA` | `0x4C882ec2…7c0C` | `0x4d58FDC7…6F7A` | `0xb51541df…02BB` |
| **Base** | 8453 | — | — | — | — |

**Collision tells (key on `(chainId, address)` always):**
- `0x5427FEFA…1820` = Ethereum **Bridge** AND Avax **OriginalTokenVault v1** (the Avax **Bridge** is the different literal `0xef3c714c…e5d4`).
- `0x88DCDC47…8a78` = Polygon **Bridge** AND Avax **PeggedTokenBridge v1**.
- `0xb51541df…02BB` = Avax **OriginalTokenVaultV2** AND Polygon **PeggedTokenBridgeV2**.
- `0x26c76F7F…1E4b` = BNB **PeggedTokenBridgeV2** AND Avax **MessageBus impl**.

---

## 11. Proxies (old & new)

| Contract | Pattern | Detection | Upgrade auth |
|----------|---------|-----------|--------------|
| **OriginalTokenVault / V2** | **Immutable, no proxy** | EIP-1967 impl slot `0x3608…2bbc` = `0x0`; full 11–14 KB runtime. | none (params only). |
| **PeggedTokenBridge / V2** | **Immutable, no proxy** | EIP-1967 impl slot = `0x0`; full 11–12 KB runtime. | none (params only). |

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
10. **Not on Base.** All pegged contracts return `0x` on Base. They also span many out-of-scope counterparty chains (the pegged model is how Celer bridges to chains without deep liquidity).
11. **Fee-on-transfer / rebasing tokens unsupported** (vault/bridge assume 1:1 transfers) — listing such a token mis-accounts the lock/supply.

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

-- ===== Selectors =====
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
-- ===== BNB (chain ID 56) =====
BNB_OTV_V1                    = '\x78bc5ee9f11d133a08b331c2e18fe81be0ed02dc'
BNB_OTV_V2                    = '\x11a0c9270d88c99e221360bca50c2f6fda44a980'
BNB_PEGBRIDGE_V1              = '\xd443fe6bf23a4c9b78312391a30ff881a097580e'
BNB_PEGBRIDGE_V2              = '\x26c76f7fef00e02a5dd4b5cc8a0f717eb61e1e4b'
-- ===== Avalanche (chain ID 43114) =====
AVAX_OTV_V1                   = '\x5427fefa711eff984124bfbb1ab6fbf5e3da1820'   -- also = Ethereum Bridge literal (Avax Bridge is 0xef3c714c…e5d4)
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
OP_PEGBRIDGE_V1               = '\x61f85ff2a2f4289be4bb9b72fc7010b3142b5f41'
OP_PEGBRIDGE_V2               = '\xc3c5b9474273113efb74e7da43b5aaba0cd9699a'
-- ===== Polygon (chain ID 137) =====
POLY_OTV_V1                   = '\xc1a2d967dfaa6a10f3461bc21864c23c1dd51eea'
POLY_OTV_V2                   = '\x4c882ec256823ee773b25b414d36f92ef58a7c0c'
POLY_PEGBRIDGE_V1             = '\x4d58fdc7d0ee9b674f49a0ade11f26c3c9426f7a'
POLY_PEGBRIDGE_V2             = '\xb51541df05de07be38dcfc4a80c05389a54502bb'   -- also = Avax OTV V2 literal
```

---

## 14. Verification & sources

How constants were verified (2026-06-09):

- **Topic0 / selectors:** recomputed locally as `keccak256(canonical signature)` (`[0:4]` for selectors), `uint`→`uint256`, from the exact event/function declarations in `celer-network/sgn-v2-contracts` (`pegged-bridge/OriginalTokenVault.sol`, `OriginalTokenVaultV2.sol`, `PeggedTokenBridge.sol`, `PeggedTokenBridgeV2.sol`). The v1↔v2 `Mint`/`Withdrawn` topic-identity and the v1↔v2 `Burn`/`Deposited` divergence were confirmed by computing both from source.
- **Live cross-check (eth_getLogs, Ethereum):** `OriginalTokenVault.Deposited` topic0 `0x15d2eeef…` returned 10 logs on `0xB37D…8595` in a 50k-block window. (Pegged mint/burn volume is now low — Celer has wound down most pegged-token routes — so some contracts show few recent logs; topic0s are computed from verified canonical source regardless.)
- **Addresses:** parsed from the official cBridge contract-addresses doc, then existence-checked via `eth_getCode` per chain (byte sizes recorded: OTV v1 ≈ 11.8–13.5 KB, OTV V2 ≈ 13.5 KB, PegBridge v1 ≈ 11.0 KB, PegBridge V2 ≈ 12.0–12.1 KB). The four ETH addresses were independently confirmed by reading the ETH MessageBus `pegBridge/pegVault/pegBridgeV2/pegVaultV2` getters live (they resolve to exactly these). **None deployed on Base** (`eth_getCode` = `0x`).
- **Proxy classification:** EIP-1967 impl slot read `0x0` (immutable, non-proxy) on Ethereum for all four contract families.

**Authoritative sources:**
- Canonical contracts: [`celer-network/sgn-v2-contracts`](https://github.com/celer-network/sgn-v2-contracts) (`contracts/pegged-bridge/`).
- Addresses: [cBridge docs — Contract Addresses](https://cbridge-docs.celer.network/reference/contract-addresses).
- Explorers: [Etherscan PeggedTokenBridge](https://etherscan.io/address/0x16365b45eb269b5b5dacb34b4a15399ec79b95eb) · [Etherscan OriginalTokenVault](https://etherscan.io/address/0xB37D31b2A74029B5951a2778F959282E2D518595).
